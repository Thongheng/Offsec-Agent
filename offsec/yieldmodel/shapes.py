"""Yield engine: accepted-shape registry + hold/kill decisions (invariant I3).

The program's *accepted shapes* are the strongest signal of what it pays for.
Before killing a candidate on a generic excluded-class rule, compare it to the
accepted corpus — a shape the program accepted before is a HOLD, not a kill
(the files-bbp F-files-1 lesson).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SHAPES_PATH = Path(__file__).resolve().parent.parent.parent / "knowledge" / "accepted_shapes.jsonl"

_STOP = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "via", "with",
         "is", "are", "bug", "issue", "access", "control"}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in _STOP and len(t) > 2}


def load() -> list[dict]:
    if not SHAPES_PATH.exists():
        return []
    out = []
    for line in SHAPES_PATH.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def add(handle: str, shape: str, cls: str = "", amount: str = "", title: str = "") -> None:
    SHAPES_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {"program": handle, "shape": shape, "class": cls, "amount": amount, "title": title}
    with open(SHAPES_PATH, "a") as f:
        f.write(json.dumps(row) + "\n")


def match(candidate: dict, handle: str | None = None, excluded: list[str] | None = None) -> dict:
    """Return {decision, matched, reason} for a candidate finding.

    decision: 'hold' (resembles an accepted shape -> strengthen + report),
              'kill' (fits only a generic excluded class -> chain-or-kill),
              'strengthen' (not enough signal; gather evidence).
    """
    cand_tokens = _tokens(candidate.get("title", "")) | _tokens(candidate.get("class", "")) | \
        _tokens(" ".join(candidate.get("observations", [])))
    corpus = load()
    if handle:
        corpus = [r for r in corpus if r.get("program") == handle]
    matched = []
    for row in corpus:
        overlap = cand_tokens & (_tokens(row.get("shape", "")) | _tokens(row.get("title", "")) |
                                 _tokens(row.get("class", "")))
        if len(overlap) >= 2:
            matched.append({"shape": row.get("shape"), "amount": row.get("amount"),
                            "overlap": sorted(overlap)})
    if matched:
        return {"decision": "hold", "matched": matched,
                "reason": "resembles accepted shape(s) — HOLD and strengthen, do not kill on a generic exclusion"}
    excl = {e.lower() for e in (excluded or [])}
    if excl and any(e in (candidate.get("class", "").lower()) for e in excl):
        return {"decision": "kill", "matched": [],
                "reason": "only matches a generic excluded class and no accepted shape — chain-or-kill"}
    return {"decision": "strengthen", "matched": [],
            "reason": "no accepted-shape match — gather a boundary-crossing proof or kill with a reason"}
