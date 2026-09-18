"""Outlier harvester.

The anti-"uniform denial = hardened" rule. Fire a family of requests that are
expected to behave identically, then surface the ones that deviate — the one
endpoint whose authz/filter is missing is the bug the uniform sweep hides.
"""
from __future__ import annotations

from collections import Counter


def _sig(resp) -> str:
    ctype = (resp.headers.get("content-type") or "").split(";")[0].strip()
    bucket = "small" if resp.length < 200 else "med" if resp.length < 2000 else "large"
    return f"{resp.status // 100}xx|{bucket}|{ctype}"


def run(probe, spec: dict) -> list[dict]:
    """spec = {"requests": [{label, method, url, headers?, body?}], "note": ...}"""
    rows = []
    for req in spec.get("requests", []):
        try:
            resp = probe(req.get("method", "GET"), req["url"], req.get("headers"), req.get("body"))
            rows.append({"label": req.get("label", req["url"]), "url": req["url"],
                         "status": resp.status, "length": resp.length,
                         "elapsed": round(resp.elapsed, 3), "sig": _sig(resp),
                         "ctype": resp.headers.get("content-type", "")})
        except Exception as e:  # probe failures are data, not crashes
            rows.append({"label": req.get("label", req["url"]), "url": req["url"],
                         "status": None, "error": str(e), "sig": "error"})
    sigs = [r["sig"] for r in rows if r.get("sig") != "error"]
    if not sigs:
        return rows
    modal, count = Counter(sigs).most_common(1)[0]
    for r in rows:
        r["outlier"] = r.get("sig") != "error" and r["sig"] != modal
        r["note"] = "differs from the family baseline" if r.get("outlier") else ""
    return rows
