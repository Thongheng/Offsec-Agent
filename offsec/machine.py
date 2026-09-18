"""Engagement gates + per-feature slice pipeline (invariant I2).

Two tiers:
  Tier 1  engagement phases: authorize -> select -> provision -> hunt -> close -> report -> done
          (terminal: abandoned). Each transition is machine-validated.
  Tier 2  feature slices:   map -> model -> seed -> hunt -> verify, per focus feature.
          Feature slices run inside the `hunt` phase; you finish one feature before
          opening the next (the crown-jewel gate, now per feature).
"""
from __future__ import annotations

from . import config, derive, events
from .gates import scope

ENGAGEMENT_PHASES = ["authorize", "select", "provision", "hunt", "close", "report", "done"]
SLICE_STEPS = ["map", "model", "seed", "hunt", "verify"]
TERMINAL = {"abandoned", "done"}
MAX_FEATURES = 3


# ---- phase ------------------------------------------------------------------

def current_phase(name: str | None = None) -> str:
    return str(config.load_target(name).get("phase") or "authorize")


def can_advance(name: str | None = None) -> tuple[bool, str, list[str]]:
    """Return (ok, next_phase, reasons_blocking)."""
    cur = current_phase(name)
    if cur in TERMINAL:
        return False, cur, [f"engagement is terminal ({cur})"]
    try:
        i = ENGAGEMENT_PHASES.index(cur)
    except ValueError:
        return False, cur, [f"unknown phase {cur!r}"]
    if i + 1 >= len(ENGAGEMENT_PHASES):
        return False, cur, ["already at final phase"]
    nxt = ENGAGEMENT_PHASES[i + 1]
    ok, reasons = _gate(cur, nxt, name)
    return ok, nxt, reasons


def advance(name: str | None = None) -> tuple[bool, str, list[str]]:
    ok, nxt, reasons = can_advance(name)
    if ok:
        t = config.load_target(name)
        prev = t.get("phase")
        t["phase"] = nxt
        if nxt == "done":
            t["outcome"] = t.get("outcome") or "done"
        config.save_target(t, name)
        events.append("phase", name, **{"from": prev, "to": nxt})
    return ok, nxt, reasons


def abandon(name: str | None = None, reason: str = "") -> None:
    t = config.load_target(name)
    prev = t.get("phase")
    t["phase"] = "abandoned"
    t["outcome"] = f"abandoned: {reason}" if reason else "abandoned"
    config.save_target(t, name)
    events.append("phase", name, **{"from": prev, "to": "abandoned"}, reason=reason)
    events.append("decision", name, target="engagement", hypothesis="abandon",
                  result="abandoned", notes=reason)


def _gate(cur: str, nxt: str, name: str | None) -> tuple[bool, list[str]]:
    if (cur, nxt) == ("authorize", "select"):
        try:
            scope.load_scope()  # raises if missing/invalid/expired
            return True, []
        except Exception as e:
            return False, [f"scope gate failed: {e}"]
    if (cur, nxt) == ("select", "provision"):
        t = config.load_target(name)
        r: list[str] = []
        feats = t.get("features") or {}
        if not feats:
            r.append("no focus features selected (1-3 required)")
        if len(feats) > MAX_FEATURES:
            r.append(f"{len(feats)} features > {MAX_FEATURES} — narrow to the accepted shapes")
        if not t.get("kill_test"):
            r.append("no kill_test recorded (reach one accepted-shape feature on a usable tier, <=1h)")
        if not t.get("yield"):
            r.append("no yield assessment recorded (accepted-shapes x enabled-features x contexts)")
        return (not r), r
    if (cur, nxt) == ("provision", "hunt"):
        t = config.load_target(name)
        probes = {p["feature"]: p.get("result") for p in derive.replay(name)["features"]}
        r = []
        for fid in (t.get("features") or {}):
            res = probes.get(fid)
            if res is None:
                r.append(f"{fid}: no enablement probe (run: offsec probe --feature {fid} --shape ...)")
            elif res != "enabled":
                r.append(f"{fid}: focus feature is {res} at the shape — provision or ABANDON")
        deps = [d for d in (t.get("dependencies") or []) if not d.get("done")]
        if deps:
            r.append(f"{len(deps)} unresolved human dependency(ies): " +
                     ", ".join(d.get("what", "?") for d in deps))
        return (not r), r
    if (cur, nxt) == ("hunt", "close"):
        t = config.load_target(name)
        r = []
        for fid, f in (t.get("features") or {}).items():
            sl = f.get("slice") or {}
            missing = [s for s in SLICE_STEPS if not sl.get(s)]
            if missing:
                r.append(f"{fid} unfinished slice steps: {', '.join(missing)}")
        return (not r), r
    return True, []


# ---- feature slices ---------------------------------------------------------

def feature_add(name: str | None, fid: str, feature_name: str) -> None:
    t = config.load_target(name)
    feats = t.setdefault("features", {})
    if fid not in feats and len(feats) >= MAX_FEATURES:
        raise ValueError(f"already {MAX_FEATURES} features — remove one before adding {fid}")
    feats.setdefault(fid, {})
    feats[fid]["name"] = feature_name
    if fid not in feats or "slice" not in feats[fid]:
        feats[fid]["slice"] = {s: False for s in SLICE_STEPS}
    config.save_target(t, name)
    events.append("decision", name, target=f"feature:{fid}", hypothesis=feature_name,
                  result="selected", notes="focus feature added")


def slice_set(name: str | None, fid: str, step: str, done: bool = True) -> tuple[bool, list[str]]:
    if step not in SLICE_STEPS:
        return False, [f"unknown slice step {step!r}"]
    t = config.load_target(name)
    feats = t.get("features") or {}
    if fid not in feats:
        return False, [f"unknown feature {fid}"]
    sl = feats[fid].setdefault("slice", {s: False for s in SLICE_STEPS})
    reasons: list[str] = []
    idx = SLICE_STEPS.index(step)
    if done:
        missing = [s for s in SLICE_STEPS[:idx] if not sl.get(s)]
        if missing:
            reasons.append(f"cannot start {step}: earlier slice steps incomplete: {', '.join(missing)}")
        # opening a new feature requires the previous focus feature to be verified
        order = list(feats)
        if step == "map" and order.index(fid) > 0:
            prev = order[order.index(fid) - 1]
            if not (feats.get(prev, {}).get("slice") or {}).get("verify"):
                reasons.append(f"cannot start {fid}: previous feature {prev} is not verified")
        # verify requires zero open crown cells for this feature
        if step == "verify":
            open_crown = derive.open_crown_elements(derive.replay(name), feature=fid)
            if open_crown:
                reasons.append(f"cannot verify {fid}: {len(open_crown)} open crown element(s): " +
                               ", ".join(str(r.get("element")) for r in open_crown[:8]))
    if reasons:
        return False, reasons
    sl[step] = done
    config.save_target(t, name)
    events.append("decision", name, target=f"slice:{fid}", hypothesis=f"{step}={done}",
                  result="worked", notes=f"feature slice {step} set to {done}")
    return True, []


# ---- select records ---------------------------------------------------------

def set_kill_test(name: str | None, candidate: str, result: str, evidence: str = "") -> None:
    t = config.load_target(name)
    t["kill_test"] = {"candidate": candidate, "result": result, "evidence": evidence}
    config.save_target(t, name)
    events.append("decision", name, target=f"killtest:{candidate}", hypothesis="reach one accepted-shape feature <=1h",
                  result=result, evidence=evidence, notes="portfolio kill test")


def set_yield(name: str | None, shapes: int, enabled: int, contexts: int, notes: str = "") -> None:
    t = config.load_target(name)
    t["yield"] = {"accepted_shapes": shapes, "enabled_features": enabled,
                  "reachable_contexts": contexts, "huntable_cells": shapes * enabled * contexts,
                  "notes": notes}
    config.save_target(t, name)
    events.append("decision", name, target="yield", hypothesis="accepted-shapes x enabled-features x contexts",
                  result="assessed", notes=notes)


def add_dependency(name: str | None, what: str, owner: str = "human") -> None:
    t = config.load_target(name)
    deps = t.setdefault("dependencies", [])
    deps.append({"what": what, "owner": owner, "done": False})
    config.save_target(t, name)
    events.append("decision", name, target=f"dependency:{what}", hypothesis=what,
                  result="blocked", notes=f"owner={owner}")


def resolve_dependency(name: str | None, what: str) -> bool:
    t = config.load_target(name)
    for d in t.get("dependencies", []):
        if d.get("what") == what:
            d["done"] = True
            config.save_target(t, name)
            events.append("decision", name, target=f"dependency:{what}", hypothesis=what,
                          result="worked", notes="resolved")
            return True
    return False


# ---- budget -----------------------------------------------------------------

def budget_consume(name: str | None, sessions: int = 0, requests: int = 0) -> tuple[bool, list[str]]:
    t = config.load_target(name)
    b = t.setdefault("budget", {})
    b["sessions_used"] = int(b.get("sessions_used", 0)) + sessions
    b["requests_used"] = int(b.get("requests_used", 0)) + requests
    config.save_target(t, name)
    reasons: list[str] = []
    if int(b.get("sessions", 0)) and b["sessions_used"] > int(b["sessions"]):
        reasons.append(f"session budget exhausted ({b['sessions_used']}/{b['sessions']}) — close or abandon")
    if int(b.get("requests", 0)) and b["requests_used"] > int(b["requests"]):
        reasons.append(f"request budget exhausted ({b['requests_used']}/{b['requests']}) — close or abandon")
    return (not reasons), reasons


# ---- status -----------------------------------------------------------------

def status(name: str | None = None) -> dict:
    views = derive.replay(name)
    s = derive.summary(views)
    t = config.load_target(name)
    ok, nxt, reasons = can_advance(name)
    return {
        "target": (config.target_dir(name).name),
        "phase": t.get("phase"),
        "outcome": t.get("outcome"),
        "next_phase": nxt,
        "next_gate_ok": ok,
        "next_gate_blockers": reasons,
        "budget": t.get("budget"),
        "features": {k: (v.get("slice") or {}) for k, v in (t.get("features") or {}).items()},
        "feature_probes": s["features"],
        "summary": {
            "coverage_rows": s["coverage_rows"],
            "coverage_by_state": s["coverage_by_state"],
            "open_crown_cells": s["open_crown_cells"],
            "frontier_open": len(s["frontier_open"]),
            "leads_open": len(s["leads_open"]),
            "findings": s["findings"],
            "findings_verified": len(s["findings_verified"]),
        },
    }
