#!/usr/bin/env python3
"""poc_replay.py — replay raw-HTTP PoC bundles from the findings ledger.

A PoC bundle is a markdown file:

    ---
    target: {{HOST}}              # host[:port]; {{TOKEN}} etc. templated from --var
    name: jwt-alg-confusion-poc
    ---
    ```http
    POST /api/login HTTP/1.1
    Host: {{HOST}}
    Content-Type: application/json

    {"user":"admin","alg":"HS256"}
    ```

Placeholders `{{NAME}}` are substituted from --var NAME=value. The target must pass
state/scope.yaml (authoritative check — the hook is best-effort for Bash one-liners).
Requests are rate-limited per the scope RoE (max_requests_per_second).

Every send is appended to `requests.jsonl` in the engagement folder (ts, method, host,
path, status, bundle) so RoE rate compliance is auditable after the fact — no headers or
bodies, so no credentials are written.

Usage:
  python3 -m offsec.verify.poc poc.md --dry-run          # show scope check + request, send nothing
  python3 -m offsec.verify.poc poc.md --var HOST=app.internal --var TOKEN=abc
  python3 -m offsec.verify.poc poc.md --quiet --var ...  # status + body only (skip CSP header flood)
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import ssl
import sys
import time
import urllib.parse

from .. import config  # noqa: E402
from ..gates import scope as _scope  # noqa: E402


def parse_bundle(path: str) -> tuple[dict, str]:
    text = open(path).read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        text = text[m.end():]
    hm = re.search(r"```http\n(.*?)```", text, re.S)
    if not hm:
        raise ValueError("no ```http block in bundle")
    return meta, hm.group(1).strip()


def parse_raw_request(raw: str) -> tuple[str, str, str, bytes, list[tuple[str, str]]]:
    """Parse a raw HTTP request. Handles CRLF (paste-from-Burp) and LF equally.
    Returns (method, host, path, body, headers) with the Host header PRESERVED in
    `headers` so the exact vhost is sent — not silently rewritten by http.client."""
    if "\r\n\r\n" in raw:
        head, _, body = raw.partition("\r\n\r\n")
    else:
        head, _, body = raw.partition("\n\n")
    lines = head.replace("\r\n", "\n").split("\n")
    if not lines or not lines[0].strip():
        raise ValueError("empty request line")
    parts = lines[0].split(" ", 2)
    if len(parts) < 2:
        raise ValueError(f"malformed request line: {lines[0]!r}")
    method, path = parts[0], parts[1]
    headers: list[tuple[str, str]] = []
    host = ""
    for ln in lines[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            k = k.strip()
            v = v.strip()
            headers.append((k, v))
            if k.lower() == "host":
                host = v
    if not host:
        raise ValueError("no Host header in raw request")
    return method, host, path, body.encode(), headers


def host_of(value: str) -> str:
    """Extract the bare hostname from a Host header value (drops :port)."""
    v = value.strip()
    if v.startswith("["):  # IPv6 literal
        return v[1:v.index("]")] if "]" in v else v
    return v.split(":")[0] or v


def rate_limit_wait(scope_cfg: dict) -> None:
    rps = float((scope_cfg.get("roe") or {}).get("max_requests_per_second") or 5)
    if rps <= 0:
        rps = 5  # fail-safe: a misconfigured 0 must not mean "unlimited"
    lock = os.path.join(str(config.target_dir()), ".lastrun")
    now = time.time()
    try:
        last = float(open(lock).read().strip())
    except Exception:
        last = 0.0
    wait = max(0.0, (1.0 / rps) - (now - last))
    if wait:
        time.sleep(wait)
    with open(lock, "w") as f:
        f.write(str(time.time()))


def record_request(meta: dict, method: str, host: str, path: str,
                   status: int | None, error: str | None = None) -> None:
    """Append one telemetry line per send so RoE rate compliance is auditable.

    Written to `requests.jsonl` in the engagement folder: ts, method, host, path,
    status, bundle name. Never contains headers/bodies, so no credentials land here.
    """
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "method": method,
        "host": host,
        "path": path,
        "status": status,
        "bundle": meta.get("name") or meta.get("finding") or None,
    }
    if error:
        row["error"] = error
    try:
        with open(os.path.join(str(config.target_dir()), "requests.jsonl"), "a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass  # telemetry must never break a send


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress request echo and response headers (print status + body only)")
    ap.add_argument("--var", action="append", default=[], help="NAME=value")
    args = ap.parse_args()

    vars_ = dict(v.split("=", 1) for v in args.var)
    meta, raw = parse_bundle(args.bundle)

    # substitute placeholders
    for k, v in vars_.items():
        raw = raw.replace("{{%s}}" % k, v)
        for mk, mv in list(meta.items()):
            meta[mk] = mv.replace("{{%s}}" % k, v)
    unresolved = sorted(set(re.findall(r"\{\{(\w+)\}\}", raw + json.dumps(meta))))
    if unresolved:
        print(f"unresolved placeholders: {unresolved} (pass --var {unresolved[0]}=...)")
        return 2

    target = meta.get("target") or ""
    if not target:
        print("bundle has no target in frontmatter")
        return 2

    try:
        method, host, path, body, headers = parse_raw_request(raw)
    except ValueError as e:
        print(f"cannot parse request: {e}")
        return 2

    # Authoritative scope check. Check BOTH the frontmatter target AND the host
    # actually connected to (the Host header) — a bundle whose target and Host
    # differ must not be able to reach an unscoped host.
    try:
        cfg = _scope.load_scope(str(config.scope_path()))
    except Exception as e:
        print(f"FAIL-CLOSED: {e}")
        return 2
    verdicts = [_scope.check_target(cfg, t) for t in {target, host_of(host)}]
    for v in verdicts:
        print("scope check:", json.dumps(v))
    if not all(v["allowed"] for v in verdicts):
        print("BLOCKED by scope.")
        return 1

    if not args.quiet:
        print(f"\n--- request ({method} {host}{path}) ---\n{raw}\n")

    if args.dry_run:
        print("dry-run: nothing sent.")
        return 0

    rate_limit_wait(cfg)
    parsed = urllib.parse.urlsplit("//" + host)
    hostname = parsed.hostname
    port = parsed.port
    tls_meta = meta.get("tls", "").lower()
    if tls_meta in ("1", "true", "yes"):
        use_tls = True
    elif tls_meta in ("0", "false", "no"):
        use_tls = False
    elif port == 80:
        use_tls = False
    elif port == 443 or port is None:
        use_tls = True
    else:
        print(f"ambiguous scheme for port {port}: set `tls: true` or `tls: false` in the bundle frontmatter")
        return 2
    port = port or (443 if use_tls else 80)
    conn_cls = http.client.HTTPSConnection if use_tls else http.client.HTTPConnection
    try:
        conn = conn_cls(hostname, port, timeout=15)
        conn.request(method, path, body=body if body else None,
                     headers=dict(headers), encode_chunked=False)
        resp = conn.getresponse()
        data = resp.read(64 * 1024)
        record_request(meta, method, host_of(host), path, resp.status)
        print(f"--- response ---\nHTTP/1.1 {resp.status} {resp.reason}")
        if not args.quiet:
            for k, v in resp.getheaders():
                print(f"{k}: {v}")
            print()
        try:
            print(data.decode("utf-8", "replace"))
        except Exception:
            print(repr(data))
    except Exception as e:
        record_request(meta, method, host_of(host), path, None, error=str(e))
        print(f"request failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
