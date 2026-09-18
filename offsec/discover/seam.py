"""UI-vs-API seam differ.

Accepted logic bugs often live where the UI's captured request differs from the
request the API accepts — a client-side-only restriction, an extra trusted field,
or a parameter the UI sets but the server does not enforce. Pure function: feed it
the captured request and your synthesized/JS-derived request.
"""
from __future__ import annotations

import re


def _parse(raw: str):
    if "\r\n\r\n" in raw:
        head, _, body = raw.partition("\r\n\r\n")
    else:
        head, _, body = raw.partition("\n\n")
    lines = head.replace("\r\n", "\n").split("\n")
    first = lines[0] if lines else ""
    headers = {}
    for ln in lines[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return first.strip(), headers, body.strip()


def diff(captured: str, synthesized: str) -> dict:
    cap_line, cap_h, cap_b = _parse(captured)
    syn_line, syn_h, syn_b = _parse(synthesized)
    only_cap = {k: v for k, v in cap_h.items() if k not in syn_h}
    only_syn = {k: v for k, v in syn_h.items() if k not in cap_h}
    changed = {k: {"captured": cap_h[k], "synthesized": syn_h[k]}
               for k in cap_h.keys() & syn_h.keys() if cap_h[k] != syn_h[k]}
    body_fields = {}
    if cap_b or syn_b:
        ck = set(re.findall(r'"(\w+)"\s*:', cap_b)) | set(re.findall(r"[?&]?(\w+)=", cap_b))
        sk = set(re.findall(r'"(\w+)"\s*:', syn_b)) | set(re.findall(r"[?&]?(\w+)=", syn_b))
        body_fields = {"only_captured": sorted(ck - sk), "only_synthesized": sorted(sk - ck)}
    return {"request_line": {"captured": cap_line, "synthesized": syn_line},
            "headers_only_captured": only_cap, "headers_only_synthesized": only_syn,
            "headers_changed": changed, "body_fields": body_fields,
            "seam_flags": _flags(only_cap, changed, body_fields)}


def _flags(only_cap, changed, body_fields) -> list[str]:
    flags = []
    for k in only_cap:
        if k in ("x-requested-with", "x-csrf-token", "x-request-token", "origin", "referer"):
            flags.append(f"client-only header {k!r} — test whether the server enforces it")
    for k in changed:
        flags.append(f"header {k!r} differs — possible client-side-only constraint")
    for f in body_fields.get("only_captured", []):
        if any(t in f.lower() for t in ("role", "perm", "access", "admin", "owner", "tenant", "scope")):
            flags.append(f"captured body field {f!r} missing from synthesized request — server may not require it")
    return flags
