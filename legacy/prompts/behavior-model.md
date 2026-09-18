# Prompt: Product walkthrough & behavior model — Stage 4

Purpose: build a model of **intended behavior** before firing any class probe. Authorization and
business-logic bugs — the highest-yield classes — **cannot** be found by pattern-matching payloads;
you must know what the feature is *supposed* to do, then violate it (OWASP WSTG; Bugcrowd; every
logic writeup). This is the stage that turns "baseline" from a status code into understanding.

## Do this (per focus feature from `plan.md` §Focus)

1. **Read the docs.** The documented workflow, permissions, roles, states, limits, and edge cases.
   Record the doc URL. Ten minutes of docs beats hours of blind probing — and deviations from the
   documented behavior ARE the candidate bugs.
2. **Use the feature like a real user, through the UI.** Create, share, invite, upload, configure,
   revoke, delete — with the account(s) from `environment.md`. Do **not** drive it only through an
   API key: the accepted logic bugs live at the **UI-vs-API seam** — states the UI enforces that the
   API skips, values the UI computes that the API merely trusts. (files-bbp lost exactly this seam
   by pivoting to an API key for transport.)
3. **Write the intended-behavior model.** For each feature: who can do *what*, to *what object*,
   under which role / tenant / permission, in which state. List the **invariants** the feature
   asserts — "one redemption", "owner-only", "expires at X", "≤N free items", "source must be
   readable by the actor". Invariants are the targets for logic/race work.
4. **Note the UI/API seam.** Fields the UI sets that the API would accept from you; states the UI
   cannot reach but the API can; validation done client-side only; parameters the UI never sends.
   (Rosén's "secondary context": same-origin `/api` routes that proxy to an internal service.)
5. **Baseline the feature's endpoints** into `coverage-map.jsonl` at `observed` — status, shape,
   permissions, and a `focus_feature` tag — so a later deviation has something to deviate *from*.

## Rule

**No class probe fires on an element still without a baseline/model.** "Normal" must exist before
"abnormal" means anything (`LEARNINGS.md` L-7). A feature you have only `GET`-ed is not modeled.

## Artifact

`targets/<t>/behavior-model.md`: per focus feature — doc URLs, the UI actions performed and with
which identity, the intended behavior + invariants, and the UI/API seam notes. The coverage rows for
that feature set `focus_feature` accordingly.

## Why this is load-bearing

Recon tells you a route exists. The behavior model tells you what it *promises*. The gap between
the promise and the implementation is where valid authz/logic/race bugs are found, and it is the one
thing a scanner structurally cannot see.
