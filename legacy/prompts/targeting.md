# Prompt: Target selection & go/no-go

Load this BEFORE an engagement — when choosing a program, or deciding whether to keep hunting.
The objective is a **valid bug**: reproducible, in-scope, not on the program's excluded list.
Severity and payout are **not** the goal and must **not** filter what you test — a Low or Medium
valid finding is a success. This prompt is the decision layer; `prompts/attack-loop.md` executes it.

**Keep it fast.** This is a checklist, not a document — minutes to an hour. Decide (hunt /
provision-then-hunt / abandon), write `plan.md`, and go. The value of a session is in tests fired,
not in plans written; do not re-litigate the plan once it exists.

**Probe before you commit — portfolio, not single-shot.** Do not marry the first reachable program.
Run a **≤1-hour kill test** on 3–5 candidates: `h1.py pick` for the facts, then for the top ones do a
fast reachability+enablement check — *can we sign up, and can we reach ONE accepted-shape feature on a
usable tier?* Commit to the candidate that shows **fresh surface, an edge, or a first signal** — not
merely the most reachable one. (Box: gating was discovered *after* committing a full engagement;
the kill test catches it in an hour — `LEARNINGS.md` L-17.)

## The gates (in priority order)

**Gate 1 — Reachability of the bug-bearing surface (the hard one).** Identify where this
program's *accepted* bugs live, then confirm you can reach those features **at the right tier,
with the right accounts and seeded data** — and, critically, that the feature is **enabled, not
merely available**: verify with a real call, because a flag can lie and an endpoint can `200`
while doing nothing (`LEARNINGS.md` L-16). If the accepted bugs are all in features your account
cannot enable, the surface is **unreachable**: provision to reach it, or explicitly scope to the
free-accessible surface and say so. (files-bbp: accepted bugs = sharing/permission access control; our account
was an UNPAID TRIAL that disabled sharing. Reachability was the binding constraint — not the
program being "too hard" or "low EV".)

**Gate 2 — Does the product's *shape* match classes you can test?** Some surfaces are inert
(marketing pages) and some are dense with the classes programs actually accept: multi-tenant data
models → authz/BOLA/BFLA; URL fetchers → SSRF; file upload/parsers → file bugs; auth/SSO flows →
account takeover. Choose targets whose **product nature** puts those classes in reach, then go to
the features that carry them. This is a property of the *product*, not of the program's paperwork.

**Do not rank programs on policy metrics.** Disclosed-report counts, excluded-class lists, and
payout figures describe the program's **policy**, not the opportunity — some programs never
disclose, exclusion lists are boilerplate, bounties are frequently private. They are **facts to
read, never a score** (`h1.py pick` prints them as facts for exactly this reason). A "quiet"
program may simply hide reports; a "crowded" open-source project discloses by culture. Freshness,
maturity, attention and edge are **product facts and live in Gate 3** — policy counts do not.

**Keep payout out of the rationale entirely.** A large advertised bounty — or a leaked payout
amount — must **not** appear in *why* you chose a target. Big numbers buy attention (crowds) and
bias you toward mature, heavily-hunted programs; if money is swaying the pick, that is the bias, not
the signal. Payout may be *noted* as context after selection; it never *is* the selection.

**Gate 3 — Yield: is there plausibly an *unfound* bug for YOU here? (a gate, not a shrug).**
Gates 1–2 say the bug *could* be reachable and the shape *fits*; they say nothing about whether one
is **still there for you**. On a mature, heavily-tested program with no fresh surface and no edge, the
expected yield of generic testing is ≈ 0 — which is exactly how three engagements (files-bbp,
moneybird, box_private) produced nothing (`LEARNINGS.md` L-17). Yield comes from **product/competition
facts, not policy**:

- **Fresh / under-tested surface** — recently added assets or features, a fast-shipping team, a
  changelog of new functionality. New code is where bugs are (`h1.py pick` → `newest-asset`).
- **Bug density** — younger / smaller products are less hardened than famous ones; broad-and-shallow
  surface beats one deep surface that a thousand people already swept.
- **Attention / competition** — a household-name product is picked over constantly; a niche one is
  not. This is *attention*, not disclosed-count (some programs simply hide reports — L-15).
- **Your edge** — a skill, an integration, private access, or an unusual surface you can reach that
  others will not.

**No edge + mature product + no fresh surface ⇒ REJECT** — or commit to *depth-only* with a stated
reason. "No edge, so try harder on the same surface" is how sessions die.

Boundary (do not over-correct): this is **not** a licence to rank on policy metrics. Disclosed
counts, exclusion lists and payout remain **facts, never scores** (L-15). Freshness, maturity,
attention and edge are *product* facts and are legitimate yield inputs.

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

**When a program hides report titles** the shapes are unavailable — that is *not* "no intel"
(Box: 50 disclosed reports, every title null). Derive the accepted taste from (a) the program's own
**focus-area list** and (b) the product's **feature set** (the JS/route inventory `recon`
produces), then **intersect it with the features that are actually enabled** (Stage 2). That
intersection *is* the huntable surface, and its size is the honest ceiling — write it into `plan.md`
before hunting. A small intersection (the headline focus is tier-gated / a silent no-op) means a
scope downgrade or `abandoned`, **not** a long sweep of the remainder (`LEARNINGS.md` L-16).

## Environment-first: provisioning is a go/no-go gate, not a late hurdle

Before hunting, list what you need to reach the bug-bearing surface — the feature tier/plan that
unblocks it, a second tenant/session, and the seeded objects for each crown-jewel resource — and
resolve each one (provision, ask the human for the one thing only they can do, or record a named
blocker). A core product feature you cannot reach means the surface is out of reach. Do not
discover this at hour six (`LEARNINGS.md` L-8).

## Program lifecycle — where in the window are you?

Your edge depends on *when* you arrive (this shapes *how* to hunt — and, with Gate 3, **whether** to
take the target at all):

- **Launch / fresh scope (first ~days).** Surface is uncovered; speed wins. Sweep the obvious
  authz/IDOR/injection on primary objects fast, bank findings, don't over-invest in one chain.
- **Mature / crowded (months in, many reports).** The easy surface is gone. Do **not** compete on
  surface bugs — they're already found. Pivot to **multi-step logic, role/tenant interactions,
  import/move/copy authz, race/state invariants, and chains**. Depth is the only moat here, and it
  is also the anti-duplicate play. **If you cannot commit to that depth (no time, no edge), this
  window is a REJECT — not a target to sweep** (L-17).
- **Neglected-but-shipping (6–18 months, attention moved on).** New features keep landing with
  fewer eyes on them; watch the changelog/scope diffs and be first on **new** functionality.

Fresh/under-tested surface beats big surface, always. Record which window you're in in `plan.md` —
it decides whether the session optimises for speed or depth (or whether you take it at all).

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
- the **yield assessment** (Gate 3): the lifecycle window (launch / mature / neglected-but-shipping),
  the fresh surface or the edge you are betting on, and whether it justifies taking the target at all,
- the **kill-test result** (did you reach one accepted-shape feature on a usable tier, ≤1h?),
- **`budget:`** (e.g. `2 sessions`) and **`abandon_when:`** (unreachable surface OR reachable
  surface genuinely exhausted — never "low payout"),
- the **outcome**: `hunt` / `provision-then-hunt` / `abandoned(reason)`.

An `abandoned` outcome is a first-class result, recorded in `log.jsonl` — not a session that
limps on. The attack loop executes this plan; `LEARNINGS.md` records how the decision held up.
