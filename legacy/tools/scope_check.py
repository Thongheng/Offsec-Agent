#!/usr/bin/env python3
"""scope_check.py — fail-closed scope gate for offsec-agent.

Checks one or more targets (URL, host:port, hostname, or IP) against
state/scope.yaml. A target passes if it matches in_scope OR
test_infrastructure (same hostname/wildcard/IP matching; test_infrastructure
holds hosts YOU control that are contacted while testing in-scope targets —
Burp Collaborator, your VPS, webhook receivers) — in both cases AND does not
match off_limits, which is an absolute override over both lists. A scoped
hostname that resolves to an out-of-scope or off-limits IP is blocked
(DNS-rebinding / shared-IP guard).

Fail-closed: no scope file, malformed scope, or unparseable target => BLOCK.

Usage:
  python3 tools/scope_check.py TARGET [TARGET...]
  python3 tools/scope_check.py --scope state/scope.yaml https://app.example.com/api

Exit codes: 0 = all in scope, 1 = at least one blocked, 2 = fail-closed error.
Output: JSON verdicts, one per line.
"""
from __future__ import annotations

import ipaddress
import json
import os
import socket
import sys
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engagement import scope_file  # noqa: E402


def default_scope() -> str:
    return str(scope_file())


def load_scope(path: str) -> dict:
    """Load and minimally validate the scope config. Raises on problems."""
    try:
        import yaml
    except ImportError:
        raise RuntimeError("PyYAML required (pip install pyyaml)")
    if not os.path.exists(path):
        raise FileNotFoundError(f"scope file not found: {path}")
    with open(path) as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError("scope file is not a mapping")
    for key in ("engagement", "authorization", "in_scope", "off_limits", "roe"):
        if key not in cfg:
            raise ValueError(f"scope file missing required key: {key}")
    auth = cfg.get("authorization") or {}
    if not auth.get("reference") or not auth.get("authorized_by"):
        raise ValueError("authorization record incomplete (reference/authorized_by)")
    if auth.get("valid_until"):
        from datetime import date
        y, m, d = (int(x) for x in str(auth["valid_until"]).split("-"))
        if date.today() > date(y, m, d):
            raise ValueError("authorization expired (valid_until passed)")
    if not cfg["in_scope"].get("hostnames") and not cfg["in_scope"].get("ips") and not cfg["in_scope"].get("cidrs"):
        raise ValueError("in_scope is empty — nothing is authorized")
    return cfg


def hostname_matches(pattern: str, host: str) -> bool:
    """Wildcard-supporting hostname match: exact match, or '*.foo.com' suffix form."""
    pattern = pattern.lower().strip()
    host = host.lower().strip()
    if pattern == host:
        return True
    if pattern.startswith("*."):
        suffix = pattern[1:]  # ".foo.com"
        return host.endswith(suffix) and host != suffix.lstrip(".")
    return False


def ip_in_scope(ip: str, entries: list, cidrs: list) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for e in entries or []:
        if str(addr) == str(e).strip():
            return True
    for c in cidrs or []:
        try:
            if addr in ipaddress.ip_network(c, strict=False):
                return True
        except ValueError:
            continue
    return False


def parse_target(target: str) -> tuple[str, str]:
    """Return (kind, value) where kind in {hostname, ip}. Accepts URLs, host:port, bare hosts."""
    t = target.strip()
    if "://" in t:
        t = urlsplit(t).hostname or ""
    else:
        # strip path/port for bare targets
        t = t.split("/")[0]
        if t.count(":") == 1:  # host:port (not IPv6 literal — those come as URLs or bare)
            t = t.rsplit(":", 1)[0]
    t = t.strip("[]")
    if not t:
        raise ValueError(f"cannot parse target: {target!r}")
    try:
        ipaddress.ip_address(t)
        return ("ip", t)
    except ValueError:
        return ("hostname", t)


def resolve(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return []
    return sorted({i[4][0] for i in infos})


def check_target(cfg: dict, target: str) -> dict:
    in_scope = cfg["in_scope"]
    off = cfg.get("off_limits") or {}
    test_infra = cfg.get("test_infrastructure") or {}
    kind, value = parse_target(target)
    result = {"target": target, "kind": kind, "value": value, "allowed": False, "reasons": []}

    if kind == "ip":
        if ip_in_scope(value, off.get("ips"), off.get("cidrs")):
            result["reasons"].append("matches off_limits")
            return result
        if ip_in_scope(value, test_infra.get("ips"), test_infra.get("cidrs")):
            result["allowed"] = True
            result["reasons"].append("ip in test_infrastructure")
            return result
        if ip_in_scope(value, in_scope.get("ips"), in_scope.get("cidrs")):
            result["allowed"] = True
            result["reasons"].append("ip in scope")
        else:
            result["reasons"].append("ip not in scope")
        return result

    # hostname
    if any(hostname_matches(p, value) for p in off.get("hostnames") or []):
        result["reasons"].append("hostname matches off_limits")
        return result
    # test_infrastructure: hosts YOU control (Burp Collaborator, VPS, webhook
    # receivers) — allowed without being listed in in_scope (off_limits above
    # is still the absolute override).
    if any(hostname_matches(p, value) for p in test_infra.get("hostnames") or []):
        result["allowed"] = True
        result["reasons"].append("hostname in test_infrastructure")
        return result
    if not any(hostname_matches(p, value) for p in in_scope.get("hostnames") or []):
        result["reasons"].append("hostname not in scope")
        return result
    result["reasons"].append("hostname in scope")

    # DNS-rebinding / shared-IP guard: resolved IPs must not be off-limits;
    # if explicit scope IPs/CIDRs are declared, resolved IPs must match them.
    ips = resolve(value)
    result["resolved_ips"] = ips
    if not ips:
        result["reasons"].append("DNS resolution failed — allowed on hostname match only")
    declared = bool(in_scope.get("ips") or in_scope.get("cidrs"))
    for ip in ips:
        if ip_in_scope(ip, off.get("ips"), off.get("cidrs")):
            result["reasons"].append(f"resolved IP {ip} matches off_limits")
            return result
        if declared and not ip_in_scope(ip, in_scope.get("ips"), in_scope.get("cidrs")):
            result["reasons"].append(f"resolved IP {ip} not in declared scope IPs — possible rebinding/shared IP")
            return result
    result["allowed"] = True
    return result


def main() -> int:
    args = sys.argv[1:]
    scope_path = None
    targets: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--scope":
            scope_path = args[i + 1]
            i += 2
            continue
        targets.append(args[i])
        i += 1

    def fail(code: int, msg: str) -> int:
        print(json.dumps({"error": msg, "allowed": False}), file=sys.stderr)
        return code

    # Resolve the engagement scope file. A stale targets/.current must surface
    # as the recovery message below — clean exit 2, never a traceback.
    try:
        scope_path = str(scope_file()) if scope_path is None else scope_path
    except Exception as e:
        return fail(2, f"FAIL-CLOSED: {e}")

    try:
        cfg = load_scope(scope_path)
    except Exception as e:  # fail-closed on any scope problem
        return fail(2, f"FAIL-CLOSED: {e}")

    if not targets:
        return fail(2, "FAIL-CLOSED: no targets given")

    verdicts = [check_target(cfg, t) for t in targets]
    for v in verdicts:
        print(json.dumps(v))
    return 0 if all(v["allowed"] for v in verdicts) else 1


if __name__ == "__main__":
    sys.exit(main())
