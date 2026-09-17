#!/usr/bin/env python3
"""new_target.py — create/switch a per-target engagement folder.

Usage:
  python3 tools/new_target.py a.com        # create targets/a.com/ and make it current
  python3 tools/new_target.py --list       # list targets, mark current
  python3 tools/new_target.py --use b.com  # switch current target

One folder per PROGRAM (name it after the program, not the bug). Each contains: scope.proposed.yaml (draft you approve with
`mv scope.proposed.yaml scope.yaml` inside it), findings.jsonl, log.jsonl, pocs/, areas/, runs/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engagement import REPO, new_target  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?", help="program name, e.g. payway, agoda (not the vulnerability)")
    ap.add_argument("--use", dest="use", metavar="NAME", help="switch to existing target")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    tdir = REPO / "targets"
    if args.list or (not args.name and not args.use):
        # Read .current directly: listing/switching must work even when .current
        # points at a target folder that no longer exists (that's the recovery path).
        cur = (tdir / ".current").read_text().strip() if (tdir / ".current").exists() else "(none)"
        print(f"current: {cur}\ntargets:")
        if tdir.exists():
            for p in sorted(tdir.iterdir()):
                if p.is_dir() and not p.name.startswith("."):
                    mark = " ←" if p.name == cur else ""
                    print(f"  {p.name}{mark}")
        return 0

    if args.use:
        root = tdir / args.use
        if not root.is_dir():
            print(f"no such target: {root}")
            return 2
        (tdir / ".current").write_text(args.use + "\n")
        print(f"current target: {args.use}")
        return 0

    root = new_target(args.name)
    print(f"created {root} (now current)")
    print("next: tell the agent about this target in plain language and it will draft")
    print(f"  {root}/scope.proposed.yaml — approve with:")
    print(f"  mv {root}/scope.proposed.yaml {root}/scope.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
