#!/usr/bin/env python3
"""Smoke test for the v2 core: derive correctness, feature-slice gates, phase gates.

Run: python3 tests/smoke.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from offsec import cli, config, derive, events, machine  # noqa: E402
from offsec.gates import scope  # noqa: E402
from offsec.yieldmodel import shapes  # noqa: E402
from offsec.discover import seam  # noqa: E402

FAILS = []


def check(label, cond):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILS.append(label)


def setup(tmp: str):
    os.environ["OFFSEC_TARGET"] = tmp
    (Path(tmp) / "pocs").mkdir(exist_ok=True)
    config.save_target(dict(config.DEFAULT_TARGET_YAML))
    (Path(tmp) / "scope.yaml").write_text(
        "engagement: t\nauthorization:\n  type: bug-bounty\n  reference: x\n  authorized_by: y\n"
        "  valid_until: ''\nin_scope:\n  hostnames: [app.t.test]\noff_limits:\n  hostnames: []\n"
        "test_infrastructure:\n  hostnames: ['*.oastify.com']\nroe:\n  max_requests_per_second: 2\n")


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="offsec-smoke-")
    try:
        setup(tmp)
        print("derive / crown openness")
        events.append("observe", element="GET /a", cls="crown-jewel", feature="F1", worth="high")
        v = derive.replay()
        check("observed crown element is open", derive.summary(v)["open_crown_cells"] == 1)
        events.append("attempt", element="GET /a", result="not-vulnerable", context="other",
                      cls="authz", feature="F1", ref=None)
        v = derive.replay()
        check("tested crown element is closed", derive.summary(v)["open_crown_cells"] == 0)
        check("closeout earned after crown closed",
              derive.exhaustion_gaps(v) == [])

        events.append("observe", element="GET /b", cls="crown-jewel", feature="F1", worth="high")
        v = derive.replay()
        check("new observed crown reopens the gap", derive.summary(v)["open_crown_cells"] == 1)

        print("frontier lifecycle")
        events.append("hypothesis", element="GET /b", hypothesis="h", feature="F1", cls="authz")
        events.append("attempt", element="GET /b", result="not-vulnerable", context="other",
                      cls="authz", feature="F1", ref="W-0001")
        v = derive.replay()
        check("hypothesis closed by referenced attempt",
              all(i["state"] != "new" for i in v["frontier"]))
        events.append("signal", element="GET /c", why="odd 200")
        v = derive.replay()
        check("unreferenced signal becomes an open lead item",
              any(i["state"] == "lead" for i in v["frontier"]))
        check("open frontier blocks closeout", derive.exhaustion_gaps(v) != [])
        events.append("lead", target="chain candidate", observation="odd invite state")
        v = derive.replay()
        check("lead event starts open", any(i["state"] == "open" for i in v["leads"]))
        rc = cli.main(["lead", "--resolve", "L-0001", "--result", "killed",
                       "--evidence", "no boundary crossed"])
        v = derive.replay()
        check("lead resolution closes lead", rc == 0
              and all(i["state"] != "open" for i in v["leads"]))

        print("feature-slice gate")
        machine.feature_add(None, "F1", "sharing")
        ok, reasons = machine.slice_set(None, "F1", "verify")
        check("verify blocked before earlier steps", not ok)
        for s in ("map", "model", "seed", "hunt"):
            machine.slice_set(None, "F1", s)
        # a crown element under F1 with no attempt must still block verify
        events.append("observe", element="GET /d", cls="crown-jewel", feature="F1", worth="high")
        ok, reasons = machine.slice_set(None, "F1", "verify")
        check("verify blocked by open crown element", not ok)

        print("phase gates")
        ok, nxt, reasons = machine.can_advance(None)
        ok2, verdicts = scope.check(["app.t.test"])
        check("authorize->select allowed with valid scope", ok and nxt == "select")
        check("scope allows in-scope host", ok2 and verdicts[0]["allowed"])
        ok3, v3 = scope.check(["evil.example"])
        check("scope blocks out-of-scope host", not ok3)

        print("shape match holds accepted shapes over generic exclusions")
        m = shapes.match({"title": "files shared via public link ignore policy", "class": "authz"},
                         None, ["existence-oracle"])
        # no corpus recorded in this temp run -> strengthen/kill; corpus check is covered in repo
        check("shape matcher returns a decision", m["decision"] in ("hold", "kill", "strengthen"))

        d = seam.diff("POST /x HTTP/1.1\nHost: a\nX-Csrf-Token: t\n\n{\"role\":\"viewer\"}",
                      "POST /x HTTP/1.1\nHost: a\n\n{}")
        check("seam flags client-only header", any("csrf" in f for f in d["seam_flags"]))
        check("seam flags missing role body field", any("role" in f for f in d["seam_flags"]))

        print("verified evidence gate")
        rc = cli.main(["evidence", "--title", "unreplayed", "--verified", "--impact", "x"])
        last = events.tail(1)[0]
        check("verified evidence without validator is rejected", rc == 1)
        check("rejected verified evidence records as candidate", last["kind"] == "evidence"
              and last["verified"] is False)
        rc = cli.main(["evidence", "--title", "replayed", "--verified", "--validator-ok",
                       "--impact", "x"])
        last = events.tail(1)[0]
        check("validator-ok allows verified evidence", rc == 0 and last["verified"] is True
              and last["validator"] == "validator_ok")
        (Path(tmp) / "pocs" / "F-0001.poc.md").write_text("---\nname: smoke\n---\n")
        rc = cli.main(["evidence", "--title", "poc bundle", "--verified",
                       "--poc", "pocs/F-0001.poc.md", "--impact", "x"])
        last = events.tail(1)[0]
        check("poc bundle alone does not allow verified evidence", rc == 1
              and last["verified"] is False)

        print("kill-test portfolio gate")
        machine.feature_add(None, "F2", "billing")
        machine.set_kill_test(None, "a", "hit", "enabled shape")
        machine.set_yield(None, 1, 1, 2, "small but real")
        t = config.load_target()
        t["phase"] = "select"
        config.save_target(t)
        ok, nxt, reasons = machine.can_advance(None)
        check("one kill test blocks select gate without override", not ok
              and any("kill_test" in r for r in reasons))
        machine.set_kill_test(None, "b", "partial", "signup only")
        machine.set_kill_test(None, "c", "miss", "tier gated")
        ok, nxt, reasons = machine.can_advance(None)
        check("three kill tests allow select gate", ok and nxt == "provision")
    finally:
        os.environ.pop("OFFSEC_TARGET", None)
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
