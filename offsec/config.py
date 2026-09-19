"""Target resolution and on-disk layout for offsec-agent v2.

Layout per target:
    targets/<name>/
        target.yaml      # human spec: scope refs, features, budget, phase
        scope.yaml       # authorized scope (approved by a human)
        events.jsonl     # SINGLE SOURCE OF TRUTH (append-only)
        derived/         # GENERATED from events.jsonl — never hand-edit
        contracts/       # request contracts mined from JS
        areas/           # recon artifacts, client helpers, captured runs
        pocs/
        reports/

Resolution order:
  1. $OFFSEC_TARGET (name under targets/, or absolute path)
  2. targets/.current pointer
Fail-closed: a missing/invalid target raises EngagementNotFoundError with a fix.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - surfaced to the user by callers
    yaml = None  # type: ignore[assignment]

REPO = Path(__file__).resolve().parent.parent
TARGETS = REPO / "targets"


class EngagementNotFoundError(RuntimeError):
    """Raised when the configured target folder does not exist."""


def _sanitize(name: str) -> str:
    n = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.strip().lower()).strip("-.")
    if not n or n in (".", ".."):
        raise ValueError(f"invalid target name: {name!r}")
    return n


def current_name() -> str | None:
    ptr = TARGETS / ".current"
    if not ptr.exists():
        return None
    name = ptr.read_text().strip()
    return name or None


def set_current(name: str) -> None:
    TARGETS.mkdir(parents=True, exist_ok=True)
    (TARGETS / ".current").write_text(_sanitize(name) + "\n")


def target_dir(name: str | None = None) -> Path:
    """Resolve a target directory. Raises EngagementNotFoundError if it does not exist."""
    env = os.environ.get("OFFSEC_TARGET")
    if name is None and env:
        name = env
    if name is None:
        name = current_name()
    if name is None:
        raise EngagementNotFoundError(
            "no target selected — run: offsec new <name>  (or offsec use <name>)"
        )
    p = Path(name)
    root = p if p.is_absolute() else TARGETS / _sanitize(name)
    if not root.is_dir():
        raise EngagementNotFoundError(
            f"target '{root.name}' does not exist — create it with: offsec new {root.name}; "
            f"or select another with: offsec use <name>"
        )
    return root


# ---- per-target paths -------------------------------------------------------

def scope_path(name: str | None = None) -> Path:
    return target_dir(name) / "scope.yaml"


def events_path(name: str | None = None) -> Path:
    return target_dir(name) / "events.jsonl"


def target_yaml_path(name: str | None = None) -> Path:
    return target_dir(name) / "target.yaml"


def derived_dir(name: str | None = None) -> Path:
    return target_dir(name) / "derived"


def ensure_layout(name: str | None = None) -> Path:
    root = target_dir(name)
    for sub in ("derived", "contracts", "areas", "pocs", "reports"):
        (root / sub).mkdir(exist_ok=True)
    (root / "events.jsonl").touch(exist_ok=True)
    return root


# ---- target.yaml ------------------------------------------------------------

DEFAULT_TARGET_YAML: dict = {
    "schema": 2,
    "phase": "authorize",
    "outcome": None,
    "program": None,
    "budget": {"sessions": 2, "sessions_used": 0, "requests": 2000, "requests_used": 0},
    "dependencies": [],
    "features": {},
    "kill_test": None,
    "kill_tests": [],
    "kill_test_override": None,
    "yield": None,
}


def load_target(name: str | None = None) -> dict:
    path = target_yaml_path(name)
    if not path.exists():
        return dict(DEFAULT_TARGET_YAML)
    if yaml is None:
        raise RuntimeError("PyYAML required (pip install pyyaml)")
    data = yaml.safe_load(path.read_text()) or {}
    merged = dict(DEFAULT_TARGET_YAML)
    merged.update(data)
    return merged


def save_target(data: dict, name: str | None = None) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML required (pip install pyyaml)")
    path = target_yaml_path(name)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def new_target(name: str) -> Path:
    """Create targets/<name>/ scaffold and point .current at it."""
    n = _sanitize(name)
    root = TARGETS / n
    if root.exists():
        raise FileExistsError(f"target already exists: {root}")
    for sub in ("derived", "contracts", "areas", "pocs", "reports"):
        (root / sub).mkdir(parents=True)
    (root / "events.jsonl").touch()
    example = REPO / "state" / "scope.example.yaml"
    if example.exists():
        (root / "scope.proposed.yaml").write_text(example.read_text())
    save_target(dict(DEFAULT_TARGET_YAML), n)
    set_current(n)
    return root
