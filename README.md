# offsec-agent v2

A structured, gate-enforced assistant for finding real bugs on bug-bounty and pentest
targets. The workflow is a **two-tier machine** over a **single append-only event log**;
all status is derived, never hand-edited.

```
Tier 1: authorize -> select -> provision -> [feature loop] -> close -> report -> done
Tier 2: per focus feature:  map -> model -> seed -> hunt -> verify
```

## Why v2

v1 optimized *honesty* (coverage, closeout) and treated *yield* as prose, with a
hand-maintained ledger that drifted. v2 makes four invariants structural:

1. **One event log per target; all status derived** — kills coverage drift.
2. **Machine-enforced gates + per-feature slices** — kills ignored pipeline order.
3. **Yield computed** (`accepted-shapes × enabled-features × reachable-contexts`) — kills
   hardening-blind target selection and late-discovered feature gating.
4. **Runnable discovery modules** (`outlier`, `authz_matrix`, `lifecycle`, `seam`) — turns
   "uniform denial = hardened" into "find the exception".

## Quickstart

```sh
python3 -m offsec new mytarget          # create targets/mytarget, select it
# write/approve scope.yaml (H1: python3 -m offsec.h1 init <handle>)
python3 -m offsec status                # current gate + blockers
python3 -m offsec advance               # pass a gate (refuses until its conditions hold)
python3 -m offsec feature add F1 --name "sharing/permissions"
python3 -m offsec probe --feature F1 --shape "create collab + read as B" --result enabled
python3 -m offsec slice F1 map          # map -> model -> seed -> hunt -> verify
python3 -m offsec observe --element "GET /api/x" --class crown-jewel --feature F1 --worth high
python3 -m offsec hypothesis --element "GET /api/x" --hypothesis "reads other tenant" --feature F1 --class authz
python3 -m offsec attempt --element "GET /api/x" --result not-vulnerable --context other --class authz --ref W-0001
python3 -m offsec next                  # worklist (read from disk)
python3 -m offsec run outlier --spec spec.json
python3 -m offsec closeout              # earned exhaustion
```

`pip install -e .` gives the `offsec` console script.

## Layout

```
offsec/            the package (CLI, machine, events, derive, gates, yield, discover, transport)
playbooks/         phase priors (p0..p6 + ref_discovery/ref_transport/ref_waf)
knowledge/         LEARNINGS.md (causal memory) + accepted_shapes.jsonl
schemas/           JSON schemas for events/artifacts
targets/<name>/    target.yaml, scope.yaml, events.jsonl (truth), derived/, contracts/, pocs/, reports/
legacy/            v1 tools/ and prompts/, retained for reference
tests/smoke.py     core behavior lock-in
```

## Tests

```sh
python3 tests/smoke.py
```
