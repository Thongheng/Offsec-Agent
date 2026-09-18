"""Append-only event log — the single source of truth (invariant I1).

Every action is one typed event. Nothing else is hand-edited; `derive.py`
rebuilds coverage/frontier/findings/leads/features from this log.

Event kinds
-----------
  observe      register an element on the surface        -> coverage row `observed`
  hypothesis   a testable claim about an element          -> frontier item `new`
  attempt      the experiment + result                    -> coverage state, frontier state
  signal       an anomaly worth depth                     -> frontier item `lead`
  lead         an unresolved chain candidate              -> leads entry
  evidence     a candidate/verified finding               -> findings entry
  decision     a reasoning step / branch                  -> decision log
  probe        feature-enablement result at the shape     -> feature matrix
  budget       consume/set budget counters
  phase        engagement phase transition (written by machine.py)

Event shape (all fields optional unless noted):
  {"eid": "E-0007", "ts": "...", "kind": "attempt", "element": "...",
   "context": "other", "class": "authz", "feature": "F1", "ref": "W-0003",
   "result": "not-vulnerable", "evidence": "...", "notes": "..."}
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import config

KINDS = {
    "observe", "hypothesis", "attempt", "signal", "lead",
    "evidence", "decision", "probe", "budget", "phase",
}

# attempt result -> coverage state
RESULT_TO_STATE = {
    "not-vulnerable": "tested_clean",
    "clean": "tested_clean",
    "tested_clean": "tested_clean",
    "worked": "signal",
    "signal": "signal",
    "info-found": "signal",
    "blocked": "blocked",
    "needs_B": "needs_session_B",
    "needs_session_B": "needs_session_B",
    "excluded": "excluded",
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read(name: str | None = None) -> list[dict]:
    path = config.events_path(name)
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _next_eid(rows: list[dict]) -> str:
    n = 0
    for r in rows:
        eid = str(r.get("eid", ""))
        if eid.startswith("E-"):
            try:
                n = max(n, int(eid[2:]))
            except ValueError:
                pass
    return f"E-{n + 1:04d}"


def append(kind: str, name: str | None = None, **fields) -> dict:
    """Append one event and return it. Fails loudly on an unknown kind."""
    if kind not in KINDS:
        raise ValueError(f"unknown event kind {kind!r}; expected one of {sorted(KINDS)}")
    path = config.events_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = read(name)
    ev = {"eid": _next_eid(rows), "ts": _now(), "kind": kind}
    ev.update({k: v for k, v in fields.items() if v is not None})
    with open(path, "a") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return ev


def tail(n: int = 10, name: str | None = None) -> list[dict]:
    return read(name)[-n:]
