---
name: offsec
description: Entry point for offensive-security work: bug bounty selection, provisioning, vulnerability hunting, PoC verification, closeout, and reporting.
---

# /offsec

OFFSEC_HOME defaults to `~/OffSec/RnD/offsec-agent`; override with `OFFSEC_HOME`.
Run commands from that root as `python3 -m offsec <command>` or use the installed
`offsec` console script.

## Always Load

Read `<OFFSEC_HOME>/AGENTS.md`, then only the playbook for the current phase.
Use `python3 -m offsec status` to learn the phase and blockers.

If the user gives only a HackerOne handle and says "go", run kill-test and
provision first. Do not enter the hunt loop.

## Routing

| User intent | Action |
|---|---|
| find a program / what should I hunt | Read `playbooks/p1_select.md`. Build a 3-5 candidate portfolio, run `python3 -m offsec.h1 rules <handle>` for eligibility, record `offsec killtest` and `offsec yield`. Do not open a hunt. |
| authorize / scope | Read `playbooks/p0_authorize.md`. Draft scope with `python3 -m offsec.h1 init <handle>` if needed; a human approves `scope.yaml`. |
| start / provision | Read `playbooks/p2_provision.md`. Create accounts A+B, seed objects, resolve dependencies, and `offsec probe` each focus feature until enabled. Block hunt until provision passes. |
| hunt / attack / find bugs | First confirm `status` shows provision passed and the feature probe is `enabled`. Then read `playbooks/p3_feature_slice.md`; use native Burp/Caido MCP for interactive traffic, `offsec next` for the worklist, and `offsec attempt` / `signal` / `lead` to record. |
| verify / PoC | Read `playbooks/p4_verify.md`. Run `python3 -m offsec.verify.poc <bundle>` or equivalent replay before `offsec evidence --verified`; otherwise record a candidate. |
| worklist / what's left | `python3 -m offsec frontier --open` and `python3 -m offsec next`; read from disk, not memory. |
| close | `python3 -m offsec closeout`; do not claim exhausted if it refuses. |
| report / submit | Read `playbooks/p6_report.md`; report only verified findings. |
| WAF / transport / discovery reference | Load only the needed `playbooks/ref_*.md`. |
| manual pasted request/response | Analyze only: verdict, likely class, controls, and next moves. No ledger ceremony unless the user asks to attach it to an active target. |

## Rules

- Scope, feature enablement, validation, and closeout gates do not bend.
- One enabled focus feature at a time.
- Discovery modules are optional tools for a concrete hypothesis, not the default
  hunt path.
- `legacy/` is archive material and is not loaded for normal work.
