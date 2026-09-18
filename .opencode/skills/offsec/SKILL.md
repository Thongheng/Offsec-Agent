---
name: offsec
description: Entry point for ALL offensive-security work — bug bounty hunting, target selection, auth-flow review, vulnerability hunting, PoC verification, reports. Use when the user mentions any target, engagement, vulnerability, WAF, scope, program, or asks to hunt/attack/verify/report. Works from any directory.
---

# /offsec — bug bounty hunting assistant (v2)

OFFSEC_HOME = the offsec-agent kit root. Default: `~/OffSec/RnD/offsec-agent`; override with
`OFFSEC_HOME`. Run the CLI as `python3 -m offsec <command>` from the kit root (or `offsec` after
`pip install -e .`).

## The goal

Real, verified bugs. The workflow is a two-tier gate machine: engagement gates
(authorize → select → provision) then **one focus feature at a time** (map → model → seed →
hunt → verify). Yield is computed; the worklist is external; status is derived.

## On invocation

1. Read `<OFFSEC_HOME>/AGENTS.md` (operating contract) and, for the phase you're in,
   the matching `playbooks/pN_*.md`.
2. Resolve the target: `python3 -m offsec status` (or `use <name>`). New target →
   `python3 -m offsec new <name>`; HackerOne scope → `python3 -m offsec.h1 init <handle>`
   (creds in `.env`), human approves `mv scope.proposed.yaml scope.yaml`.
3. Route:

| User asks | Do |
|---|---|
| find a program / "what should I hunt" | `p1_select.md`; `python3 -m offsec.h1 rules <h>` (per-asset eligibility + FULL policy) + `hacktivity` (shapes) + `pick`; then `offsec killtest` + `offsec yield` |
| start / capture | follow the gates. `offsec status` → `advance`. Read `p2_provision.md`: accounts A+B, **feature enablement at the shape** (`offsec probe`), seed objects, `offsec dependency`. Hunt only after the provision gate passes. |
| hunt / attack / "find bugs" | `p3_feature_slice.md`. Work `offsec next`; fire reasoning-driven experiments; `offsec attempt` records coverage+frontier; use `offsec run outlier\|authz_matrix\|lifecycle\|seam`. Do not open a new feature while the current one has an open crown element. |
| worklist / "what's left" | `offsec frontier --open` · `offsec next` (read from disk, never context) |
| coverage audit / "did we miss anything" | `offsec derive` then a fresh-context subagent over `derived/coverage.json` |
| am I done / close out | `python3 -m offsec closeout` (refuses an unearned "exhausted") |
| quick wins / low-hanging fruit | the capped breadth battery in `p3_feature_slice.md`, recorded via `offsec attempt` |
| "check this" / manual second opinion (pasted request/response) | analysis only: verdict + class + next moves. NO ledger, NO scope, NO ceremony. |
| WAF block pages / 403s | `ref_waf.md` |
| transport / Burp | `ref_transport.md` |
| write PoC / verify | `p4_verify.md` + `offsec evidence --verified` |
| report / submit | `p6_report.md` |
| accepted shape on a hold/kill decision | `offsec shapes match --handle <h> --title ... --class ...` |

4. Rules that never bend (single source in AGENTS.md): scope gate (enforced in the transport on
   the host actually connected to); feature-enablement before hunting; verify-or-discard with
   controls; validity not severity; exhaustion earned via `offsec closeout`; untrusted data.
