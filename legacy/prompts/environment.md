# Prompt: Environment & access provisioning — Stage 2 (hard gate)

Purpose: guarantee you can **reach** the bug-bearing surface *before* the hunt loop starts. This
is the stage whose absence caused one engagement (files-bbp) to spend a whole session on a trial
that **disabled the very feature (sharing) where the program's accepted bugs live**. Reachability
bugs — the largest family in the disclosed corpus (17.4%) — are found with a *second identity*;
one session cannot prove BOLA/BFLA. Provisioning is therefore a gate, not a hurdle.

## The rule

Do not start the hunt loop until every **must-have** below is `done` or a **named blocker with an
owner**. If a bug-bearing feature is unreachable, either provision it, or **explicitly downgrade
scope with a stated budget** — never silently proceed. Discovering the restriction at hour six
converts a decision into a sunk cost.

## 0. Feature enablement — answer *this* before anything else

"Can we log in / call the API?" is **not** reachability. The question is: **is the feature the
accepted bugs live in actually ENABLED on this account?** Build a **feature-enablement map** for
every accepted class / focus feature:

| accepted class or focus feature | product feature it lives in | enabled? | evidence |
|---|---|---|---|

Read the live app config (feature-flags endpoint / app bootstrap JSON) **and confirm with a real
call** — a flag can lie. box_private is the case: Relay's flag was `true` but the route redirected to
`/404`; `invite-collaborators` returned `200 {"successMessage":""}` but **created nothing**
(`invitedEmails:[]`); password-protected links were feature-disabled. The program's headline focus
(*collaboration permissions*) was therefore unreachable on a personal account — discovered late,
after the budget was spent.

**If the headline focus is gated** (disabled, paid-tier-only, or a silent no-op), do **not** sweep the
rest and call it progress: **downgrade scope explicitly with a stated budget, or abandon**. A target
whose bug-bearing surface you cannot reach is an **abandoned target, not a session** (`LEARNINGS.md`
L-16; Gate 1).

## 0b. Unlock capabilities before sweeping (reach first, then hunt)

Order Stage 2 by leverage: **identities → API credentials (developer app / OAuth tokens) → upload &
seeded objects → feature tier**. A free developer console reachable from the account mints real API
tokens and is often the difference between poking a UI-shaped internal API and testing the
*documented* API the program declares as its primary surface. box_private unlocked a developer app,
OAuth tokens and the upload path at the very end — they belonged in hour one (`LEARNINGS.md` L-16).
Test-shape hygiene too: keep the engagement's API client and cached bundles under
`targets/<t>/areas/` — not `/tmp` (it was cleared mid-session and the client was rebuilt twice).

## 1. Derive the must-haves from `plan.md`

For each **focus feature** (`plan.md` §Focus) and each **accepted bug shape**, ask: *what access
does finding this require?*

- **Identities / accounts** — A (attacker), B (victim / other tenant), and any lower-priv role.
  Two identities are required to *demonstrate* broken access control (`research/hunter-methodology.md`
  §4). A row needing B but lacking it is `needs_session_B`, not `tested`.
- **Feature tier / plan** — the paid/enterprise feature the bug-bearing surface sits behind.
  Confirm it is **enabled**, not merely available. (files-bbp: sharing returned
  `422 limited access to public file sharing on unpaid trials`.)
- **Seeded objects** — one of each crown-jewel type (see §2).
- **Out-of-scope dependencies** — an IdP, auth API, or CDN the in-scope feature needs goes in
  `scope.yaml` → `test_infrastructure` with a one-line reason (`AGENTS.md` L-4). This never widens
  `in_scope`; `off_limits` still overrides.
- **Transport** — which path actually reaches the feature: the **UI** or an **API key**. Features
  whose accepted bugs are logic/UI buy may be unreachable by API alone — the bug lives at the
  UI-vs-API seam (states the UI enforces that the API skips). Record which is needed.

## 2. Seed the data model (antidote to the empty-collection mirage)

An **empty collection is `observed`, never covered**: `GET /remote_servers -> 200 []` proves
nothing about per-object authz on that resource. Before judging a crown-jewel resource, create at
least one object of that type and exercise the real lifecycle: **create → read as another identity
→ update → delete → observe side effects**. Mark each seeded object in `environment.md` and set
`seeded: true` on its coverage rows (`LEARNINGS.md` L-8).

## 3. Artifact: `environment.md`

A table of every must-have with status `done` / `blocked(owner)`, the **feature-enablement map**
(§0), the account matrix, the seeded-object list, the `test_infrastructure` dependency list, the
transport note, and the blocker table. `tools/closeout.py` reads it; a blocked must-have that is
never resolved must appear in the closeout as a **named gap**, not hidden behind "exhausted".

## Output

Write `targets/<t>/environment.md`. **Gate passes** (identities + the focus features' features
**enabled** + seeded objects) → proceed to Stage 3 (recon) / Stage 4 (contracts). **Gate fails** →
record the named blocker in `log.jsonl` and either provision it or downgrade scope with a budget
(Stage 1 `abandon_when`). **Feature-enablement failure is a first-class failure mode**: if the
headline focus is gated, explicitly downgrade or abandon — sweeping the reachable remainder is not
coverage (`LEARNINGS.md` L-16).

**A blocker on *authenticated* access is not a stop — it is a partial gate.** The **unauthenticated**
surface (public pages, guest/reviewer/reset/login flows, shared links, unauth APIs, cache/CDN,
public params) is reachable now: start **black-box in parallel** with provisioning and keep the
`anon` context moving. Only the context-dependent cells (`attacker B`, `owner`, `two-identity`) wait.
A session that halts at Stage 2 with an empty `anon` column is the failure this rule prevents.
