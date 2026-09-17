#!/usr/bin/env python3
"""closeout.py — decide whether an "exhausted" / "no finding" close is EARNED.

Enforces LEARNINGS L-8/L-9: a no-finding close is only truthful when every crown-jewel endpoint
is `authed_tested` / `needs_session_B` / `excluded` AND there are no `open` leads. It refuses the
false "web surface exhausted" that files-bbp recorded while its own coverage map showed 114 rows
`observed`, 0 `authed_tested`, and 50 high-worth crown-jewels untested.

Exit codes:  0 = earned exhausted   1 = gaps remain (not earned)   2 = no ledger / bad path

Usage:
  python3 tools/closeout.py [--target <name>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import engagement

CLOSED_STATES = {"authed_tested", "needs_session_B", "excluded"}


def load_jsonl(path: Path) -> list[dict]:
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
        if isinstance(obj, dict) and "schema" in obj:  # schema/header row
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def is_crown(row: dict) -> bool:
    return row.get("class") == "crown-jewel" or row.get("worth") == "high"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", help="target name under targets/ (else uses .current)")
    args = ap.parse_args()
    if args.target:
        os.environ["OFFSEC_TARGET"] = args.target

    root = engagement.engagement_root()
    cov_path = root / "coverage-map.jsonl"
    if not cov_path.exists():
        print(f"no coverage-map.jsonl in {root} — nothing to reconcile")
        return 2

    cov = load_jsonl(cov_path)
    leads = load_jsonl(root / "leads.jsonl")

    crown = [r for r in cov if is_crown(r)]
    closed_crown = [r for r in crown if r.get("state") in CLOSED_STATES]
    open_crown = [r for r in crown if r.get("state") not in CLOSED_STATES]
    other_observed = [r for r in cov if r.get("state") == "observed" and not is_crown(r)]
    open_leads = [r for r in leads if r.get("state", "open") == "open"]

    print(f"target:                 {root.name}")
    print(f"coverage rows:          {len(cov)}")
    print(f"crown-jewel/high-worth: {len(crown)}")
    print(f"  closed (tested/excl): {len(closed_crown)}")
    print(f"  OPEN crown-jewels:    {len(open_crown)}")
    print(f"observed (non-crown):   {len(other_observed)}")
    print(f"open leads:             {len(open_leads)}")

    if open_crown or open_leads:
        print('\nVERDICT: NOT EARNED — do not close as "exhausted" / "no finding".')
        if open_crown:
            print(f"\n{len(open_crown)} crown-jewel endpoint(s) still open:")
            for r in open_crown[:30]:
                print(f"  - [{str(r.get('state','?')):14s}] {str(r.get('endpoint','?'))}")
            if len(open_crown) > 30:
                print(f"  ... and {len(open_crown) - 30} more")
        if open_leads:
            print(f"\n{len(open_leads)} open lead(s):")
            for r in open_leads[:30]:
                print(f"  - {str(r.get('id','?')):8s} {str(r.get('target',''))[:72]}")
            if len(open_leads) > 30:
                print(f"  ... and {len(open_leads) - 30} more")
        print("\nHonest close instead: state the counts above + the blocking reason "
              "(see plan.md budget / environment.md blockers).")
        return 1

    print("\nVERDICT: EARNED — every crown-jewel is tested/excluded and no leads are open.")
    if other_observed:
        print(f"(note: {len(other_observed)} non-crown `observed` rows remain; list them in the "
              "summary as known-unexplored, they do not block the exhausted claim.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
