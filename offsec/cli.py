"""offsec — single command surface for the gate-enforced workflow.

    python3 -m offsec <command>      (or the `offsec` console script after pip install)

Design: the event log is the truth; commands append events and, where relevant,
advance the machine. Derived views are rebuilt on demand.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import config, derive, events, machine
from .gates import scope
from . import discover
from .transport import http as transport_http
from .yieldmodel import shapes as yield_shapes


def _targetless(fn):
    """Wrap a command so EngagementNotFoundError prints a clean fix, not a traceback."""
    def wrapper(args):
        try:
            return fn(args)
        except config.EngagementNotFoundError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    return wrapper


# ---- commands ---------------------------------------------------------------

def cmd_new(a) -> int:
    root = config.new_target(a.name)
    print(f"created {root} (phase=authorize); next: write scope.yaml, then `offsec status`")
    return 0


def cmd_use(a) -> int:
    config.set_current(a.name)
    print(f"current target: {config.target_dir(a.name).name}")
    return 0


@_targetless
def cmd_status(a) -> int:
    s = machine.status()
    print(json.dumps(s, indent=1))
    try:
        derive.derive()
    except Exception:
        pass
    return 0


@_targetless
def cmd_observe(a) -> int:
    ev = events.append("observe", element=a.element, context=a.context, cls=a.cls,
                       feature=a.feature, worth=a.worth, evidence=a.evidence)
    print(json.dumps(ev))
    return 0


@_targetless
def cmd_hypothesis(a) -> int:
    ev = events.append("hypothesis", element=a.element, hypothesis=a.hypothesis,
                       context=a.context, **{"class": a.cls}, feature=a.feature,
                       priority=a.priority, budget=a.budget, derived_from=a.derived_from)
    print(json.dumps(ev))
    return 0


@_targetless
def cmd_attempt(a) -> int:
    ev = events.append("attempt", element=a.element, result=a.result, context=a.context,
                       **{"class": a.cls}, feature=a.feature, ref=a.ref,
                       evidence=a.evidence, notes=a.note)
    ok, reasons = machine.budget_consume(None, requests=max(0, a.requests))
    print(json.dumps(ev))
    if not ok:
        print("budget:", "; ".join(reasons), file=sys.stderr)
    return 0


@_targetless
def cmd_signal(a) -> int:
    ev = events.append("signal", ref=a.ref, element=a.element, why=a.why,
                       feature=a.feature, **{"class": a.cls}, evidence=a.evidence)
    print(json.dumps(ev))
    return 0


@_targetless
def cmd_lead(a) -> int:
    if a.resolve:
        ev = events.append("decision", target=f"lead:{a.resolve}", hypothesis="resolve lead",
                           result=a.result, evidence=a.evidence, notes=a.note)
        print(json.dumps(ev))
        return 0
    if not a.target or not a.observation:
        print("error: lead requires --target and --observation unless --resolve is used",
              file=sys.stderr)
        return 2
    ev = events.append("lead", target=a.target, observation=a.observation, why=a.why,
                       follow_up=a.follow_up, feature=a.feature)
    print(json.dumps(ev))
    return 0


@_targetless
def cmd_evidence(a) -> int:
    verified = bool(a.verified)
    validator_reason = None
    if verified:
        validator_ok = bool(a.validator_ok)
        override_ok = bool(a.human_override)
        if not (validator_ok or override_ok):
            print("BLOCKED: --verified requires --validator-ok or "
                  "--human-override with a reason. "
                  "Recording candidate evidence instead.", file=sys.stderr)
            verified = False
        elif validator_ok:
            validator_reason = "validator_ok"
        else:
            validator_reason = "human_override"

    ev = events.append("evidence", title=a.title, **{"class": a.cls}, severity=a.severity,
                       verified=verified, impact=a.impact, poc=a.poc,
                       shape_ref=a.shape_ref, validator=validator_reason,
                       human_override=a.human_override)
    print(json.dumps(ev))
    return 0 if verified == bool(a.verified) else 1


@_targetless
def cmd_decide(a) -> int:
    ev = events.append("decision", target=a.target, hypothesis=a.summary, result=a.result,
                       ref=a.ref, evidence=a.evidence, notes=a.note)
    print(json.dumps(ev))
    return 0


@_targetless
def cmd_probe(a) -> int:
    ev = events.append("probe", feature=a.feature, shape=a.shape, result=a.result,
                       evidence=a.evidence)
    print(json.dumps(ev))
    return 0


@_targetless
def cmd_feature(a) -> int:
    machine.feature_add(None, a.fid, a.name)
    print(f"feature {a.fid}: {a.name}")
    return 0


@_targetless
def cmd_slice(a) -> int:
    ok, reasons = machine.slice_set(None, a.fid, a.step, done=not a.undo)
    if not ok:
        print("BLOCKED:", "; ".join(reasons), file=sys.stderr)
        return 1
    print(f"{a.fid} slice.{a.step} = {not a.undo}")
    return 0


@_targetless
def cmd_advance(a) -> int:
    ok, nxt, reasons = machine.advance()
    if not ok:
        print(f"gate not passed for -> {nxt}:")
        for r in reasons:
            print(f"  - {r}")
        return 1
    print(f"phase -> {nxt}")
    derive.derive()
    return 0


@_targetless
def cmd_abandon(a) -> int:
    machine.abandon(reason=a.reason)
    print("engagement abandoned")
    return 0


@_targetless
def cmd_derive(a) -> int:
    derive.derive()
    print(json.dumps(derive.summary(), indent=1))
    return 0


@_targetless
def cmd_killtest(a) -> int:
    machine.set_kill_test(None, a.candidate, a.result, a.evidence or "",
                          a.override_reason or "")
    print(f"kill test: {a.candidate} -> {a.result}")
    return 0


@_targetless
def cmd_yield(a) -> int:
    machine.set_yield(None, a.shapes, a.enabled, a.contexts, a.notes or "")
    print(f"yield: {a.shapes} shapes x {a.enabled} enabled x {a.contexts} contexts "
          f"= {a.shapes * a.enabled * a.contexts} cells")
    return 0


@_targetless
def cmd_dependency(a) -> int:
    if a.resolve:
        ok = machine.resolve_dependency(None, a.resolve)
        print("resolved" if ok else "not found")
        return 0 if ok else 1
    machine.add_dependency(None, a.what, a.owner)
    print(f"dependency recorded: {a.what} (owner={a.owner})")
    return 0


@_targetless
def cmd_run(a) -> int:
    spec = json.load(open(a.spec))
    if a.module == "seam":
        result = discover.PURE["seam"](spec["captured"], spec["synthesized"])
    else:
        fn = discover.MODULES.get(a.module)
        if not fn:
            print(f"unknown module {a.module}; choose from {sorted(discover.MODULES)}", file=sys.stderr)
            return 2

        def probe(method, url, headers=None, body=None):
            return transport_http.request(method, url, headers, body)

        result = fn(probe, spec)
    print(json.dumps(result, indent=1))
    return 0


@_targetless
def cmd_shapes(a) -> int:
    if a.shapes_cmd == "add":
        yield_shapes.add(a.handle, a.shape, a.cls or "", a.amount or "", a.title or "")
        print("shape recorded")
        return 0
    if a.shapes_cmd == "list":
        rows = yield_shapes.load()
        if a.handle:
            rows = [r for r in rows if r.get("program") == a.handle]
        for r in rows:
            print(f"{r.get('program'):16s} {r.get('class',''):14s} {r.get('amount',''):6s} {r.get('shape','')}")
        print(f"-- {len(rows)} shape(s)")
        return 0
    # match
    candidate = json.load(open(a.candidate)) if a.candidate else {"title": a.title or "", "class": a.cls or ""}
    excl = [e for e in (a.excluded or "").split(",") if e]
    print(json.dumps(yield_shapes.match(candidate, a.handle, excl), indent=1))
    return 0


@_targetless
def cmd_frontier(a) -> int:
    items = derive.replay()["frontier"]
    if a.open:
        items = [i for i in items if i.get("state") in derive.OPEN_FRONTIER]
    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda i: (order.get(i.get("priority"), 1), i.get("id", "")))
    for i in items:
        print(f"[{str(i.get('state')):12s}] {i.get('id'):6s} {i.get('priority','?'):6s} "
              f"{str(i.get('element',''))[:56]}")
    print(f"-- {len(items)} item(s)")
    return 0


@_targetless
def cmd_next(a) -> int:
    items = [i for i in derive.replay()["frontier"] if i.get("state") in derive.OPEN_FRONTIER]
    if not items:
        print("frontier triaged: no open items")
        return 0
    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda i: (order.get(i.get("priority"), 1), i.get("id", "")))
    print(json.dumps(items[0], indent=1))
    return 0


@_targetless
def cmd_closeout(a) -> int:
    derive.derive()
    gaps = derive.exhaustion_gaps()
    if gaps:
        print("VERDICT: NOT EARNED — do not close as exhausted:")
        for g in gaps:
            print(f"  - {g}")
        return 1
    print("VERDICT: EARNED — every crown cell tested/excluded, no open frontier or leads.")
    return 0


@_targetless
def cmd_budget(a) -> int:
    if a.consume_session or a.consume_requests:
        ok, reasons = machine.budget_consume(None, sessions=1 if a.consume_session else 0,
                                             requests=a.consume_requests)
        for r in reasons:
            print("WARN:", r, file=sys.stderr)
    print(json.dumps(config.load_target().get("budget"), indent=1))
    return 0


@_targetless
def cmd_scope(a) -> int:
    ok, verdicts = scope.check(a.targets, a.scope)
    for v in verdicts:
        print(json.dumps(v))
    return 0 if ok else 1


@_targetless
def cmd_events(a) -> int:
    for ev in events.tail(a.tail):
        print(json.dumps(ev))
    return 0


# ---- parser -----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="offsec", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("new"); s.add_argument("name"); s.set_defaults(fn=cmd_new)
    s = sub.add_parser("use"); s.add_argument("name"); s.set_defaults(fn=cmd_use)
    s = sub.add_parser("status"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("derive"); s.set_defaults(fn=cmd_derive)
    s = sub.add_parser("closeout"); s.set_defaults(fn=cmd_closeout)
    s = sub.add_parser("advance"); s.set_defaults(fn=cmd_advance)
    s = sub.add_parser("abandon"); s.add_argument("--reason", default=""); s.set_defaults(fn=cmd_abandon)
    s = sub.add_parser("killtest")
    s.add_argument("--candidate", required=True)
    s.add_argument("--result", required=True, choices=["hit", "miss", "partial"])
    s.add_argument("--evidence", default=None)
    s.add_argument("--override-reason", default=None,
                   help="reason fewer than 3 portfolio kill tests are acceptable")
    s.set_defaults(fn=cmd_killtest)
    s = sub.add_parser("yield")
    s.add_argument("--shapes", type=int, required=True)
    s.add_argument("--enabled", type=int, required=True)
    s.add_argument("--contexts", type=int, required=True)
    s.add_argument("--notes", default=None)
    s.set_defaults(fn=cmd_yield)
    s = sub.add_parser("dependency")
    s.add_argument("--what", default=None)
    s.add_argument("--owner", default="human")
    s.add_argument("--resolve", default=None)
    s.set_defaults(fn=cmd_dependency)
    s = sub.add_parser("run")
    s.add_argument("module", choices=["outlier", "authz_matrix", "lifecycle", "seam"])
    s.add_argument("--spec", required=True)
    s.set_defaults(fn=cmd_run)
    s = sub.add_parser("shapes")
    sh = s.add_subparsers(dest="shapes_cmd", required=True)
    sha = sh.add_parser("add")
    sha.add_argument("--handle", required=True); sha.add_argument("--shape", required=True)
    sha.add_argument("--class", dest="cls", default=None); sha.add_argument("--amount", default=None)
    sha.add_argument("--title", default=None); sha.set_defaults(fn=cmd_shapes)
    shl = sh.add_parser("list"); shl.add_argument("--handle", default=None); shl.set_defaults(fn=cmd_shapes)
    shm = sh.add_parser("match")
    shm.add_argument("--handle", default=None); shm.add_argument("--candidate", default=None)
    shm.add_argument("--title", default=None); shm.add_argument("--class", dest="cls", default=None)
    shm.add_argument("--excluded", default=None); shm.set_defaults(fn=cmd_shapes)
    s = sub.add_parser("next"); s.set_defaults(fn=cmd_next)
    s = sub.add_parser("frontier"); s.add_argument("--open", action="store_true"); s.set_defaults(fn=cmd_frontier)
    s = sub.add_parser("budget")
    s.add_argument("--consume-session", action="store_true")
    s.add_argument("--consume-requests", type=int, default=0)
    s.set_defaults(fn=cmd_budget)
    s = sub.add_parser("events"); s.add_argument("--tail", type=int, default=10); s.set_defaults(fn=cmd_events)

    s = sub.add_parser("observe")
    s.add_argument("--element", required=True)
    s.add_argument("--context", default=None)
    s.add_argument("--class", dest="cls", default=None)
    s.add_argument("--feature", default=None)
    s.add_argument("--worth", default=None)
    s.add_argument("--evidence", default=None)
    s.set_defaults(fn=cmd_observe)

    s = sub.add_parser("hypothesis")
    s.add_argument("--element", required=True)
    s.add_argument("--hypothesis", required=True)
    s.add_argument("--context", default=None)
    s.add_argument("--class", dest="cls", default=None)
    s.add_argument("--feature", default=None)
    s.add_argument("--priority", choices=["high", "medium", "low"], default="medium")
    s.add_argument("--budget", choices=["cheap", "depth"], default="cheap")
    s.add_argument("--derived-from", dest="derived_from", default=None)
    s.set_defaults(fn=cmd_hypothesis)

    s = sub.add_parser("attempt")
    s.add_argument("--element", required=True)
    s.add_argument("--result", required=True,
                   choices=["not-vulnerable", "worked", "info-found", "blocked",
                            "needs_B", "excluded", "clean"])
    s.add_argument("--context", default=None)
    s.add_argument("--class", dest="cls", default=None)
    s.add_argument("--feature", default=None)
    s.add_argument("--ref", default=None)
    s.add_argument("--evidence", default=None)
    s.add_argument("--note", default=None)
    s.add_argument("--requests", type=int, default=1)
    s.set_defaults(fn=cmd_attempt)

    s = sub.add_parser("signal")
    s.add_argument("--why", required=True)
    s.add_argument("--ref", default=None)
    s.add_argument("--element", default=None)
    s.add_argument("--feature", default=None)
    s.add_argument("--class", dest="cls", default=None)
    s.add_argument("--evidence", default=None)
    s.set_defaults(fn=cmd_signal)

    s = sub.add_parser("lead")
    s.add_argument("--target", default=None)
    s.add_argument("--observation", default=None)
    s.add_argument("--why", default=None)
    s.add_argument("--follow-up", dest="follow_up", default=None)
    s.add_argument("--feature", default=None)
    s.add_argument("--resolve", default=None, help="lead id to resolve, e.g. L-0001")
    s.add_argument("--result", default="killed",
                   choices=["killed", "chained", "verified", "duplicate"])
    s.add_argument("--evidence", default=None)
    s.add_argument("--note", default=None)
    s.set_defaults(fn=cmd_lead)

    s = sub.add_parser("evidence")
    s.add_argument("--title", required=True)
    s.add_argument("--class", dest="cls", default=None)
    s.add_argument("--severity", default=None)
    s.add_argument("--verified", action="store_true")
    s.add_argument("--candidate", action="store_true")
    s.add_argument("--impact", default=None)
    s.add_argument("--poc", default=None)
    s.add_argument("--validator-ok", action="store_true",
                   help="assert that python -m offsec.verify.poc or an equivalent replay exited 0")
    s.add_argument("--human-override", default=None,
                   help="human-reviewed reason to mark verified without deterministic replay")
    s.add_argument("--shape-ref", dest="shape_ref", default=None)
    s.set_defaults(fn=cmd_evidence)

    s = sub.add_parser("decide")
    s.add_argument("--summary", required=True)
    s.add_argument("--result", default="info-found")
    s.add_argument("--target", default=None)
    s.add_argument("--ref", default=None)
    s.add_argument("--evidence", default=None)
    s.add_argument("--note", default=None)
    s.set_defaults(fn=cmd_decide)

    s = sub.add_parser("probe")
    s.add_argument("--feature", required=True)
    s.add_argument("--shape", required=True)
    s.add_argument("--result", required=True, choices=["enabled", "disabled", "no_op", "error"])
    s.add_argument("--evidence", default=None)
    s.set_defaults(fn=cmd_probe)

    s = sub.add_parser("feature")
    fs = s.add_subparsers(dest="feature_cmd", required=True)
    fa = fs.add_parser("add"); fa.add_argument("fid"); fa.add_argument("--name", required=True)
    fa.set_defaults(fn=cmd_feature)

    s = sub.add_parser("slice")
    s.add_argument("fid")
    s.add_argument("step", choices=machine.SLICE_STEPS)
    s.add_argument("--undo", action="store_true")
    s.set_defaults(fn=cmd_slice)

    s = sub.add_parser("scope")
    s.add_argument("targets", nargs="+")
    s.add_argument("--scope", default=None)
    s.set_defaults(fn=cmd_scope)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
