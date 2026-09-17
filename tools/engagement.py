#!/usr/bin/env python3
"""engagement.py — shared per-target directory resolution for all offsec-agent tools.

Engagement root resolution order:
  1. $OFFSEC_TARGET env var (a name under targets/, or an absolute path)
  2. targets/.current pointer file (written by tools/new_target.py)
  3. repo state/  (legacy single-engagement mode)

Every per-engagement file (scope.yaml, proxy-history.jsonl, findings.jsonl,
pocs/, areas/, runs/) lives under the engagement root.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _sanitize(name: str) -> str:
    n = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.strip().lower()).strip("-.")
    if not n or n in (".", ".."):
        raise ValueError(f"invalid target name: {name!r}")
    return n


class EngagementNotFoundError(RuntimeError):
    """Raised when the configured current target folder does not exist."""


def engagement_root() -> Path:
    env = os.environ.get("OFFSEC_TARGET")
    if env:
        p = Path(env)
        root = p if p.is_absolute() else REPO / "targets" / env
    else:
        current = REPO / "targets" / ".current"
        if not current.exists():
            return REPO / "state"
        name = current.read_text().strip()
        if not name:
            return REPO / "state"
        root = REPO / "targets" / _sanitize(name)
    if not root.is_dir():
        raise EngagementNotFoundError(
            f"current target '{root.name}' does not exist — fix with: "
            f"python3 tools/new_target.py --use {root.name} (or delete targets/.current)")
    return root


def scope_file() -> Path:
    return engagement_root() / "scope.yaml"


def new_target(name: str) -> Path:
    """Create targets/<name>/ scaffold and point .current at it."""
    n = _sanitize(name)
    root = REPO / "targets" / n
    if root.exists():
        raise FileExistsError(f"target already exists: {root}")
    (root / "pocs").mkdir(parents=True)
    (root / "areas").mkdir()
    example = REPO / "state" / "scope.example.yaml"
    if example.exists():
        (root / "scope.proposed.yaml").write_text(example.read_text())
    for ledger in ("findings", "log", "coverage-map", "leads"):
        (root / f"{ledger}.jsonl").touch()
    # required pipeline artifacts (Stage 1 plan / Stage 2 environment)
    for tmpl, out in (("plan.template.md", "plan.md"),
                      ("environment.template.md", "environment.md")):
        t = REPO / "state" / tmpl
        if t.exists():
            (root / out).write_text(t.read_text())
    (REPO / "targets" / ".current").write_text(n + "\n")
    return root
