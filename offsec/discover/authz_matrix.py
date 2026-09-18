"""Authorization matrix runner.

Fires the same operations as two (or more) identities across a set of objects
and flags the cells where a *denied* context gets what the owner context gets.
This is the two-identity BOLA/BFLA/role matrix the old kit described but rarely ran.
"""
from __future__ import annotations


def run(probe, spec: dict) -> list[dict]:
    """spec = {
      "baseline": {label, headers},
      "contexts": [{label, headers}],
      "cells": [{element, method, url, body?, success_statuses?}]
    }"""
    baseline = spec["baseline"]
    contexts = spec.get("contexts", [])
    out: list[dict] = []
    for cell in spec.get("cells", []):
        base_status = _fire(probe, baseline, cell)
        row = {"element": cell.get("element", cell["url"]), "url": cell["url"],
               "baseline": base_status, "contexts": {}}
        for ctx in contexts:
            st = _fire(probe, ctx, cell)
            granted = _granted(st, cell)
            expected = cell.get("expect", "deny")
            flaw = (expected == "deny" and granted and _granted(base_status, cell))
            row["contexts"][ctx["label"]] = {"status": st, "granted": granted, "flaw": flaw}
            if flaw:
                row["flaw"] = True
        out.append(row)
    return out


def _fire(probe, identity: dict, cell: dict):
    try:
        r = probe(cell.get("method", "GET"), cell["url"],
                  identity.get("headers"), cell.get("body"))
        return r.status
    except Exception:
        return None


def _granted(status, cell: dict) -> bool:
    if status is None:
        return False
    ok = cell.get("success_statuses") or [200, 201, 202, 204]
    return status in ok
