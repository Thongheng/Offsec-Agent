#!/usr/bin/env python3
"""leads.py — first-class leads / chain pile (pipeline Stage 8).

An anomaly is queued work, not a note. This is the operational form of Rosén's "interesting
behaviour" pile: valid vulns stay separate from *soon-to-combine* behaviour, and the session
cannot be closed while leads are `open` (see LEARNINGS L-8, tools/closeout.py).

Usage:
  python3 tools/leads.py add --target "GET /x?y=" --observation "..." [--why "..."] \
      [--follow-up "..."] [--slice FEATURE] [--evidence "log.jsonl ..."] [--target-name <t>]
  python3 tools/leads.py list [--open] [--target-name <t>]
  python3 tools/leads.py close <id> --resolution "..." [--state killed|worked] [--target-name <t>]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

import engagement


def _path(target: str | None):
    if target:
        os.environ["OFFSEC_TARGET"] = target
    return engagement.engagement_root() / "leads.jsonl"


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
        if rid.startswith("L-"):
            try:
                n = max(n, int(rid[2:]))
            except ValueError:
                pass
    return f"L-{n + 1:03d}"


def cmd_add(a) -> int:
    path = _path(a.target_name)
    rows = _load(path)
    lead = {
        "id": _next_id(rows),
        "ts": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "slice_id": a.slice,
        "target": a.target,
        "observation": a.observation,
        "why": a.why,
        "state": "open",
        "follow_up": a.follow_up,
        "resolution": None,
        "evidence_ref": a.evidence,
    }
    rows.append(lead)
    _write(path, rows)
    print(f"added {lead['id']} -> {path}")
    return 0


def cmd_list(a) -> int:
    rows = _load(_path(a.target_name))
    if a.open:
        rows = [r for r in rows if r.get("state", "open") == "open"]
    for r in rows:
        print(f"[{str(r.get('state','open')):6s}] {str(r.get('id','?')):8s} "
              f"{str(r.get('target',''))[:64]}")
    print(f"\n{len(rows)} lead(s)")
    return 0


def cmd_close(a) -> int:
    path = _path(a.target_name)
    rows = _load(path)
    hit = False
    for r in rows:
        if str(r.get("id")) == a.id:
            r["state"] = a.state
            r["resolution"] = a.resolution
            r["resolved_ts"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            hit = True
    if not hit:
        print(f"no lead with id {a.id}", file=sys.stderr)
        return 1
    _write(path, rows)
    print(f"closed {a.id} as {a.state}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-name", dest="target_name",
                    help="engagement under targets/ (else .current)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add")
    p.add_argument("--target", required=True, help="the exact element: endpoint/param/header")
    p.add_argument("--observation", required=True, help="what was seen that does not make sense")
    p.add_argument("--why", default=None, help="impact if the anomaly is real")
    p.add_argument("--follow-up", dest="follow_up", default=None, help="next attempt to resolve it")
    p.add_argument("--slice", default=None, help="feature/area label")
    p.add_argument("--evidence", default=None, help="pointer to log/pocs")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list")
    p.add_argument("--open", action="store_true", help="only open leads")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("close")
    p.add_argument("id")
    p.add_argument("--resolution", required=True)
    p.add_argument("--state", default="worked", choices=["worked", "killed"])
    p.set_defaults(func=cmd_close)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
