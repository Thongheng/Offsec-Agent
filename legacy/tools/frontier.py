#!/usr/bin/env python3
"""frontier.py — the worklist (pipeline Stage 7's spine).

The agent's memory for "what is left to test" lives HERE, not in the model's context.
Read the frontier at the start of every iteration; take the top `new` item; test it;
record the outcome; append anything the result DERIVED. Compaction can then throw away
the conversation without losing coverage — the state is re-derived from this file.

Work item = element x hypothesis. States:
  OPEN     : new | in_progress | lead            (lead = a signal was seen; needs depth)
  TERMINAL : tested_clean | verified | excluded | needs_B | blocked | duplicate

`tools/closeout.py` refuses an "exhausted" close while any OPEN item remains.

Usage:
  python3 tools/frontier.py add --element "POST /api/x" --hypothesis "IDOR via id" \
      [--source "attack-surface.md"] [--priority high|medium|low] [--budget cheap|depth] \
      [--derived-from W-003] [--focus sharing] [--notes "..."] [--target-name <t>]
  python3 tools/frontier.py next [--mark]          # top `new` item (--mark sets in_progress)
  python3 tools/frontier.py set <id> --state <state> [--signal "..."] [--evidence "..."]
  python3 tools/frontier.py signal <id> "what was odd"   # promote new/in_progress -> lead
  python3 tools/frontier.py list [--state <state>] [--open]
  python3 tools/frontier.py stats
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

import engagement

OPEN_STATES = ("new", "in_progress", "lead")
TERMINAL_STATES = ("tested_clean", "verified", "excluded", "needs_B", "blocked", "duplicate")
ALL_STATES = OPEN_STATES + TERMINAL_STATES
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _path(target: str | None):
    if target:
        os.environ["OFFSEC_TARGET"] = target
    return engagement.engagement_root() / "frontier.jsonl"


def _load(path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "schema" not in obj:
            rows.append(obj)
    return rows


def _write(path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def _next_id(rows: list[dict]) -> str:
    n = 0
    for r in rows:
        rid = str(r.get("id", ""))
        if rid.startswith("W-"):
            try:
                n = max(n, int(rid[2:]))
            except ValueError:
                pass
    return f"W-{n + 1:03d}"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sort_key(r: dict):
    return (PRIORITY_RANK.get(str(r.get("priority", "medium")), 1),
            str(r.get("ts", "")))


def cmd_add(a) -> int:
    path = _path(a.target_name)
    rows = _load(path)
    for r in rows:  # dedupe on element x hypothesis
        if r.get("element") == a.element and r.get("hypothesis") == a.hypothesis:
            print(f"exists {r.get('id')} ({r.get('state')}) -> {path}")
            return 0
    item = {
        "id": _next_id(rows),
        "ts": _now(),
        "element": a.element,
        "hypothesis": a.hypothesis,
        "source": a.source,
        "priority": a.priority,
        "budget": a.budget,
        "focus_feature": a.focus,
        "state": "new",
        "signal": None,
        "evidence": None,
        "derived_from": a.derived_from,
        "notes": a.notes,
    }
    rows.append(item)
    _write(path, rows)
    print(f"added {item['id']} [{a.priority}] -> {path}")
    return 0


def cmd_next(a) -> int:
    path = _path(a.target_name)
    rows = _load(path)
    new = [r for r in rows if r.get("state") == "new"]
    if not new:
        print("no `new` items (frontier triaged)")
        return 0
    new.sort(key=_sort_key)
    top = new[0]
    if a.mark:
        for r in rows:
            if r.get("id") == top["id"]:
                r["state"] = "in_progress"
                r["updated"] = _now()
        _write(path, rows)
    print(f"{top['id']} [{top.get('priority')}] {top.get('element')}")
    print(f"   hypothesis: {top.get('hypothesis')}")
    if top.get("focus_feature"):
        print(f"   focus: {top.get('focus_feature')}   budget: {top.get('budget')}")
    if top.get("derived_from"):
        print(f"   derived_from: {top.get('derived_from')}")
    return 0


def cmd_set(a) -> int:
    path = _path(a.target_name)
    rows = _load(path)
    hit = None
    for r in rows:
        if str(r.get("id")) == a.id:
            hit = r
    if hit is None:
        print(f"no item {a.id}", file=sys.stderr)
        return 1
    if a.state not in ALL_STATES:
        print(f"bad state {a.state}; one of {', '.join(ALL_STATES)}", file=sys.stderr)
        return 1
    hit["state"] = a.state
    if a.signal is not None:
        hit["signal"] = a.signal
    if a.evidence is not None:
        hit["evidence"] = a.evidence
    hit["updated"] = _now()
    _write(path, rows)
    print(f"{a.id} -> {a.state}")
    return 0


def cmd_signal(a) -> int:
    path = _path(a.target_name)
    rows = _load(path)
    hit = None
    for r in rows:
        if str(r.get("id")) == a.id:
            hit = r
    if hit is None:
        print(f"no item {a.id}", file=sys.stderr)
        return 1
    hit["signal"] = a.description
    hit["state"] = "lead"
    hit["updated"] = _now()
    _write(path, rows)
    print(f"{a.id} -> lead (signal recorded)")
    return 0


def cmd_list(a) -> int:
    rows = _load(_path(a.target_name))
    if a.open:
        rows = [r for r in rows if r.get("state") in OPEN_STATES]
    elif a.state:
        rows = [r for r in rows if r.get("state") == a.state]
    rows.sort(key=_sort_key)
    for r in rows:
        print(f"[{str(r.get('state')):12s}] {str(r.get('id')):6s} "
              f"{str(r.get('priority')):6s} {str(r.get('element'))[:48]:48s} "
              f"{str(r.get('hypothesis'))[:36]}")
    print(f"\n{len(rows)} item(s)")
    return 0


def cmd_stats(a) -> int:
    rows = _load(_path(a.target_name))
    counts: dict[str, int] = {}
    for r in rows:
        counts[str(r.get("state"))] = counts.get(str(r.get("state")), 0) + 1
    order = ["new", "in_progress", "lead"] + list(TERMINAL_STATES)
    for s in order:
        if counts.get(s):
            print(f"  {s:14s} {counts[s]}")
    opens = sum(counts.get(s, 0) for s in OPEN_STATES)
    print(f"total {len(rows)}  |  OPEN {opens}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-name", dest="target_name",
                    help="engagement under targets/ (else .current)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add")
    p.add_argument("--element", required=True, help="METHOD /path (normalize ids to {id})")
    p.add_argument("--hypothesis", required=True, help="the class/idea to test here")
    p.add_argument("--source", default=None, help="where it came from (recon/history/anomaly)")
    p.add_argument("--priority", default="medium", choices=["high", "medium", "low"])
    p.add_argument("--budget", default="cheap", choices=["cheap", "depth"])
    p.add_argument("--derived-from", dest="derived_from", default=None, help="parent item id")
    p.add_argument("--focus", default=None, help="plan.md focus feature")
    p.add_argument("--notes", default=None)
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("next")
    p.add_argument("--mark", action="store_true", help="set the top item to in_progress")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("set")
    p.add_argument("id")
    p.add_argument("--state", required=True, choices=list(ALL_STATES))
    p.add_argument("--signal", default=None)
    p.add_argument("--evidence", default=None)
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("signal")
    p.add_argument("id")
    p.add_argument("description")
    p.set_defaults(func=cmd_signal)

    p = sub.add_parser("list")
    p.add_argument("--state", default=None, choices=list(ALL_STATES))
    p.add_argument("--open", action="store_true", help="only open items")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("stats")
    p.set_defaults(func=cmd_stats)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
