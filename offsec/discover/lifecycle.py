"""Object-lifecycle runner.

Exercises create -> read-as-other -> update-as-other -> delete-as-other ->
side-effects on one object, which is where per-object authz and ownership bugs
live (the premium "import/move/copy" shape from the research, operationalized).
"""
from __future__ import annotations


def run(probe, spec: dict) -> list[dict]:
    """spec = {"steps": [{name, method, url, headers?, body?, expect?}]}"""
    out: list[dict] = []
    for step in spec.get("steps", []):
        entry = {"step": step.get("name", step.get("url")), "url": step["url"],
                 "method": step.get("method", "GET"), "expect": step.get("expect")}
        try:
            r = probe(step.get("method", "GET"), step["url"], step.get("headers"), step.get("body"))
            entry.update({"status": r.status, "length": r.length})
            entry["deviation"] = _deviates(r.status, step.get("expect"))
        except Exception as e:
            entry.update({"status": None, "error": str(e)})
        out.append(entry)
    return out


def _deviates(status: int, expect) -> bool:
    if status is None or not expect:
        return False
    ok = expect.get("success_statuses") or [200, 201, 202, 204, 302]
    if expect.get("should") == "succeed":
        return status not in ok
    if expect.get("should") == "fail":
        return status in ok
    return False
