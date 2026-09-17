# Prompt: Target selection & go/no-go

Load this BEFORE an engagement — when choosing a program, or deciding whether to keep hunting.
The objective is a **valid bug**: reproducible, in-scope, not on the program's excluded list.
Severity and payout are **not** the goal and must **not** filter what you test — a Low or Medium
valid finding is a success. This prompt is the decision layer; `prompts/attack-loop.md` executes it.

**Keep it fast.** This is a checklist, not a document — minutes to an hour. Decide (hunt /
provision-then-hunt / abandon), write `plan.md`, and go. The value of a session is in tests fired,
not in plans written; do not re-litigate the plan once it exists.

## The gates (in priority order)

**Gate 1 — Reachability of the bug-bearing surface (the hard one).** Identify where this
program's *accepted* bugs live, then confirm you can reach those features **at the right tier,
with the right accounts and seeded data**. Read the disclosed-report titles — they are the
program's accepted taste. If the accepted bugs are all in features your account cannot enable,
the surface is **unreachable**: provision to reach it, or explicitly scope to the free-accessible
surface and say so. (files-bbp: accepted bugs = sharing/permission access control; our account
was an UNPAID TRIAL that disabled sharing. Reachability was the binding constraint — not the
program being "too hard" or "low EV".)

**Gate 2 — Where is a valid bug most findable? (a prioritization, NOT a filter).** Weight
new / under-tested surface over big picked-over surface: newly added assets and features,
functions with few or no prior reports, recently changed behavior. A mature, crowded, hardened
program is **not disqualified** — it can still hold valid Low findings (files-bbp itself accepted
a Medium "existence oracle"). Use this to choose *where to look first*. **Never use it to skip
surface, and never let it be an expected-dollar-value calculation.**

**Gate 3 — Your edge (helps, optional).** Familiarity, access, or patience that lets you go where
others don't. No edge means lean harder on Gate 1 reachability and honest breadth — not that you
should walk away.

## Severity is not a gate (explicit, per the operating contract)

- The success condition is a **valid bug** — reproduced, in-scope, not on the excluded list.
- Do **not** discard, deprioritize, or fail to report a finding because it is Low/Medium or pays
  little.
- The only filters that apply are: **reachable · real · in scope · not excluded.** Anything that
  passes all four gets reported. Payout is context, never a reason to withhold or skip.

## Class eligibility gate — check the PROGRAM, per asset and per class, BEFORE testing

A class is only worth firing if the **program would accept it on that asset**. This is checked
*before* tests, not after: an afternoon spent proving a class the program excludes is a loss even
if the bug is real. Run `python3 tools/h1.py rules <handle>` (per-asset eligibility + FULL policy)
and confirm **all four**:

1. **Asset eligible** — `eligible_for_bounty` **AND** `eligible_for_submission` (they differ);
   an explicit `out`/non-eligible asset overrides a wildcard.
2. **Class not excluded** — the policy's excluded-vulnerability-class list (missing headers,
   self-XSS, rate-limit-only, SPF/DMARC, …). Excluded ⇒ **chain-or-kill only**, never a standalone
   report.
3. **Inside the test environment** — the policy's required env (testnet/dev vs mainnet/prod,
   own-trial-only, no automation, etc.).
4. **Within `max_severity` and any partial-scope instruction** (path/file/tier carve-outs).

**Encode it**: fill `scope.yaml` → `program_rules` (`excluded_classes`, `chained_only_classes`,
`test_environment`, `max_severity`, `asset_eligibility_notes`) and the `plan.md` eligibility matrix.
The test queue is drawn from eligible classes only. Reading the *summary* is not enough — read the
**FULL** policy (`AGENTS.md` L-3: truncated scope hid eligibility flags and partial scope).

## Disclosed-shape analysis (cheap and decisive — do it every time)

`python3 tools/h1.py hacktivity 'team_handle:"<h>"'` → read the **titles**, not the count.
Extract each bug's *shape*: "access control on files shared via X", "CSRF on a settings
endpoint", "folder-path existence oracle via response". Then:
1. Replicate the shape on the exact feature that paid.
2. Check its **siblings / adjacent features** for the same shape — a program that accepted once
   for a shape frequently accepts again on another instance.

This is the single cheapest high-probability play available, and it is about *validity*, not
payout. (files-bbp disclosed 3/3 feature-logic shapes; we noted them and then ran class sweeps
instead.)

## Environment-first: provisioning is a go/no-go gate, not a late hurdle

Before hunting, list what you need to reach the bug-bearing surface — the feature tier/plan that
unblocks it, a second tenant/session, and the seeded objects for each crown-jewel resource — and
resolve each one (provision, ask the human for the one thing only they can do, or record a named
blocker). A core product feature you cannot reach means the surface is out of reach. Do not
discover this at hour six (`LEARNINGS.md` L-8).

## Abandon rule (the most expensive habit is sunk cost)

Give every target a **fixed budget** (e.g. 1–2 sessions). The trigger to abandon is
**unreachable surface, or reachable surface genuinely exhausted** — *never* "the payout is
low." When the budget expires with no live candidate, write the honest close and switch targets.
Do not "finish exploring" a surface you cannot reach; equally, do not skip a reachable surface
because it looks low-value.

## Output

Write `targets/<t>/plan.md` (template: `state/plan.template.md`) — the engagement **contract**:
- the gates with evidence,
- the accepted bug **shapes** (from `hacktivity` titles),
- the chosen **focus feature(s)** to own (1–3),
- the provisioning checklist (→ `environment.md`, Stage 2),
- **`budget:`** (e.g. `2 sessions`) and **`abandon_when:`** (unreachable surface OR reachable
  surface genuinely exhausted — never "low payout"),
- the **outcome**: `hunt` / `provision-then-hunt` / `abandoned(reason)`.

An `abandoned` outcome is a first-class result, recorded in `log.jsonl` — not a session that
limps on. The attack loop executes this plan; `LEARNINGS.md` records how the decision held up.
