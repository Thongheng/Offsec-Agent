"""Derive all status views from the append-only event log (invariant I1).

Nothing here is hand-edited. `derive()` replays events and writes
`derived/{coverage,frontier,findings,leads,features,summary}.json`.

Coverage model
--------------
  elements   registry from `observe` events: an element plus its worth/crown flag
  cells      test cells from `attempt` events: (element, context, class, feature)

A crown element is OPEN until it has at least one terminal attempt cell and no
unresolved signal. `observed` (never attempted) is a named gap, never coverage.
"""
from __future__ import annotations

import json

from . import config, events

CLOSED_COVERAGE = {"unauth_tested", "authed_tested", "needs_session_B", "blocked",
                   "excluded", "tested_clean", "tested"}
OPEN_FRONTIER = {"new", "in_progress", "lead"}
CROWN_CLASSES = {"crown-jewel", "crown"}


def _crown(worth, cls) -> bool:
    return worth == "high" or cls in CROWN_CLASSES


def _key(row: dict) -> str:
    return "|".join((row.get("element", ""), row.get("context", ""),
                     row.get("feature", ""), row.get("class", "")))


def replay(name: str | None = None) -> dict:
    rows = events.read(name)
    elements: dict[str, dict] = {}
    cells: dict[str, dict] = {}
    frontier: dict[str, dict] = {}
    leads: list[dict] = []
    findings: list[dict] = []
    features: dict[str, dict] = {}
    decisions: list[dict] = []
    phases: list[dict] = []
    fnum = lnum = wnum = 0

    def reg(el: str, worth=None, cls=None, feature=None) -> None:
        if not el:
            return
        e = elements.setdefault(el, {"element": el, "worth": None, "crown": False, "feature": None})
        if worth:
            e["worth"] = worth
        if feature:
            e["feature"] = feature
        if cls:
            e["class"] = cls
        e["crown"] = _crown(e.get("worth"), e.get("class"))

    for ev in rows:
        kind = ev.get("kind")
        if kind == "observe":
            el = ev.get("element", "")
            reg(el, ev.get("worth"), ev.get("cls"), ev.get("feature"))
            cells.setdefault(_key({"element": el, "context": "", "feature": ev.get("feature", ""),
                                   "class": ev.get("cls", "")}),
                             {"element": el, "context": "", "feature": ev.get("feature", ""),
                              "class": ev.get("cls", ""), "state": "observed", "result": None,
                              "evidence": ev.get("evidence"), "ts": ev.get("ts")})
        elif kind == "attempt":
            el = ev.get("element", "")
            reg(el, ev.get("worth"), ev.get("cls") if ev.get("cls") in CROWN_CLASSES else None,
                ev.get("feature"))
            row = {
                "element": el, "context": ev.get("context", ""),
                "feature": ev.get("feature", ""), "class": ev.get("cls", ""),
                "state": events.RESULT_TO_STATE.get(ev.get("result", ""), "tested"),
                "result": ev.get("result"), "evidence": ev.get("evidence"), "ts": ev.get("ts"),
            }
            cells[_key(row)] = row
            ref = ev.get("ref")
            if ref and ref in frontier:
                frontier[ref].update({
                    "state": "lead" if row["state"] == "signal" else _frontier_state(row["state"]),
                    "evidence": ev.get("evidence"), "updated": ev.get("ts")})
        elif kind == "hypothesis":
            wnum += 1
            wid = ev.get("id") or f"W-{wnum:04d}"
            frontier[wid] = {
                "id": wid, "element": ev.get("element", ""), "hypothesis": ev.get("hypothesis", ""),
                "feature": ev.get("feature", ""), "class": ev.get("class", ""),
                "priority": ev.get("priority", "medium"), "budget": ev.get("budget", "cheap"),
                "state": "new", "signal": None, "evidence": None,
                "derived_from": ev.get("derived_from"), "ts": ev.get("ts"), "updated": ev.get("ts")}
        elif kind == "signal":
            ref = ev.get("ref")
            if ref and ref in frontier:
                frontier[ref].update({"state": "lead", "signal": ev.get("why"),
                                      "evidence": ev.get("evidence"), "updated": ev.get("ts")})
            else:
                wnum += 1
                wid = f"W-{wnum:04d}"
                frontier[wid] = {
                    "id": wid, "element": ev.get("element", ""), "hypothesis": ev.get("why", ""),
                    "feature": ev.get("feature", ""), "class": ev.get("class", ""),
                    "priority": ev.get("priority", "high"), "budget": "depth", "state": "lead",
                    "signal": ev.get("why"), "evidence": ev.get("evidence"),
                    "derived_from": ev.get("derived_from"), "ts": ev.get("ts"), "updated": ev.get("ts")}
        elif kind == "lead":
            lnum += 1
            leads.append({"id": ev.get("id") or f"L-{lnum:04d}", "target": ev.get("target", ""),
                          "observation": ev.get("observation", ""), "why": ev.get("why", ""),
                          "state": "open", "follow_up": ev.get("follow_up", ""),
                          "feature": ev.get("feature", ""), "resolution": None, "ts": ev.get("ts")})
        elif kind == "evidence":
            fnum += 1
            findings.append({"id": ev.get("id") or f"F-{fnum:04d}",
                             "title": ev.get("title") or ev.get("finding", ""),
                             "class": ev.get("class", ""), "severity": ev.get("severity", ""),
                             "verified": bool(ev.get("verified")), "impact": ev.get("impact", ""),
                             "poc": ev.get("poc", ""), "shape_ref": ev.get("shape_ref"),
                             "ts": ev.get("ts")})
        elif kind == "probe":
            features[ev.get("feature", "")] = {
                "feature": ev.get("feature", ""), "shape": ev.get("shape", ""),
                "result": ev.get("result"), "evidence": ev.get("evidence"), "ts": ev.get("ts")}
        elif kind == "decision":
            ref = ev.get("ref")
            if ref and ref in frontier and ev.get("result") in ("killed", "duplicate", "excluded"):
                frontier[ref].update({"state": ev["result"], "evidence": ev.get("evidence"),
                                      "updated": ev.get("ts")})
            decisions.append(ev)
        elif kind == "phase":
            phases.append(ev)

    # propagate crown status from the element registry to every cell
    for row in cells.values():
        el = elements.get(row["element"])
        if el and el.get("crown"):
            row["worth"] = "high"
    return {"elements": list(elements.values()), "coverage": list(cells.values()),
            "frontier": list(frontier.values()), "leads": leads, "findings": findings,
            "features": list(features.values()), "decisions": decisions, "phases": phases}


def _frontier_state(coverage_state: str) -> str:
    if coverage_state == "tested_clean":
        return "tested_clean"
    if coverage_state in ("needs_session_B", "blocked", "excluded"):
        return coverage_state
    return "in_progress"


def _is_crown(row: dict) -> bool:
    return row.get("worth") == "high" or row.get("class") in CROWN_CLASSES


def open_crown_elements(views: dict, feature: str | None = None) -> list[dict]:
    """Crown elements that are not yet resolved.

    Resolved = at least one attempt cell AND no cell in an unresolved `signal` state.
    An `observed`-only crown element is a named gap.
    """
    out: list[dict] = []
    cells = views["coverage"]
    for el in views["elements"]:
        if not el.get("crown"):
            continue
        if feature and el.get("feature") != feature:
            continue
        attempts = [c for c in cells if c["element"] == el["element"] and c["state"] != "observed"]
        if not attempts:
            out.append({**el, "reason": "observed (never tested)"})
        elif any(c["state"] == "signal" for c in attempts):
            out.append({**el, "reason": "unresolved signal"})
    return out


def summary(views: dict | None = None) -> dict:
    views = views or replay()
    cov = views["coverage"]
    open_crown = open_crown_elements(views)
    return {
        "coverage_rows": len(cov),
        "coverage_by_state": _count(cov, "state"),
        "crown_elements": len([e for e in views["elements"] if e.get("crown")]),
        "open_crown_cells": len(open_crown),
        "open_crown_elements": [e["element"] for e in open_crown][:30],
        "frontier_total": len(views["frontier"]),
        "frontier_open": [r for r in views["frontier"] if r.get("state") in OPEN_FRONTIER],
        "leads_total": len(views["leads"]),
        "leads_open": [r for r in views["leads"] if r.get("state", "open") == "open"],
        "findings": len(views["findings"]),
        "findings_verified": [r for r in views["findings"] if r.get("verified")],
        "features": {r["feature"]: r.get("result") for r in views["features"]},
    }


def exhaustion_gaps(views: dict | None = None) -> list[str]:
    """Reasons a no-finding close would be unearned. Empty == earned."""
    s = summary(views)
    gaps: list[str] = []
    if s["open_crown_cells"]:
        gaps.append(f"{s['open_crown_cells']} open crown-jewel element(s)")
    if s["frontier_open"]:
        gaps.append(f"{len(s['frontier_open'])} open frontier item(s)")
    if s["leads_open"]:
        gaps.append(f"{len(s['leads_open'])} open lead(s)")
    return gaps


def _count(rows: list[dict], field: str) -> dict:
    out: dict[str, int] = {}
    for r in rows:
        out[str(r.get(field))] = out.get(str(r.get(field)), 0) + 1
    return out


def derive(name: str | None = None) -> dict:
    views = replay(name)
    out = config.derived_dir(name)
    out.mkdir(parents=True, exist_ok=True)
    (out / "coverage.json").write_text(json.dumps(views["coverage"], indent=1))
    (out / "elements.json").write_text(json.dumps(views["elements"], indent=1))
    (out / "frontier.json").write_text(json.dumps(views["frontier"], indent=1))
    (out / "findings.json").write_text(json.dumps(views["findings"], indent=1))
    (out / "leads.json").write_text(json.dumps(views["leads"], indent=1))
    (out / "features.json").write_text(json.dumps(views["features"], indent=1))
    (out / "summary.json").write_text(json.dumps(summary(views), indent=1))
    return views
