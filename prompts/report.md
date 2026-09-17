# Prompt: Report

Load this when submitting. The report you write depends on `scope.yaml →
reporting.engagement_type`. **Read that field first — the two types have opposite bars.**

Inputs: `state/findings.jsonl` (verified findings only — anything `verified: false` is a
candidate, not a finding), `log.jsonl` (every attempt + result — the coverage record),
`proxy-history.jsonl` (the full observed surface), PoC bundles in `pocs/`.

## Branch A — bug bounty (`engagement_type: bug-bounty`)

Hunting is the same instinct for both modes — every bug found, low-hanging included. The
difference is two-fold: what goes in the report, **and** that a bounty hunt should have aimed
at eligible, non-duplicate, in-scope surface from the start (see the duplicate & eligibility
gate in `prompts/attack-loop.md`). The platform triager is your reader:

- **In-scope**: the vulnerable asset must be inside the program's bounty-eligible scope.
  An out-of-scope-asset finding is not submitted — at most a courtesy note if the policy
  allows. (This differs from pentest: in bounty, scope defines what's worth money.)
- **Bounty-eligible classes**: check the program's policy — many exclude SPF/DMARC, missing
  security headers, self-XSS, rate-limit-without-impact, "best practice" nits. If the class is
  excluded, do not submit.
- **Non-duplicate**: check disclosed hacktivity for the class+asset before writing up. If it's
  already public, at most it's a variant worth one line — don't burn a submission on a known bug.
  Nuance (HackerOne's own rule): **same vuln type on a *different* endpoint is NOT a duplicate**;
  same type + same endpoint + same root cause is. A finding that merely shares a class with a
  disclosed bug is still submittable — state the differentiator.
- **Verified with impact**: reproduced PoC (from the poc bundle) demonstrating the boundary
  crossed + a one-paragraph impact statement in the program's terms ("attacker with account X
  can access tenant Y's data"), severity estimate, and clean reproduction steps (5-minute bar).

**A valid Low-severity bug IS submitted.** Validity, not severity, is the bar: a reproduced,
in-scope, non-excluded finding of any severity goes in. What is **not** submitted is non-bug
noise — missing headers/cookie flags, version banners, internal IPs, self-XSS, rate-limit-without-
impact, and the program's excluded classes. Those stay as notes in `log.jsonl`. Don't confuse
"low severity" (submit) with "not a bug / excluded" (don't).

## Branch B — pentest (`engagement_type: pentest`)

The client's security team is your reader and **completeness is the deliverable**. Report:

1. **Executive summary** — business language, risk-ranked.
2. **All findings**, critical → informational: every finding that matters to the client's
   defense gets written up — including informational/hardening observations (missing headers,
   verbose errors, weak session timeouts) that a bounty program would reject. Use the
   configured `severity_scale`. Each finding: description, affected asset, impact, PoC
   (replayable bundle), remediation, references.
3. **Coverage statement** (mandatory): from `log.jsonl` + `proxy-history.jsonl` — what was tested, what
   was out of scope, what was blocked, what was skipped and why. Un-audited areas are named,
   not hidden.
4. **Methodology + limitations**: attacker model used, testing windows, accounts used
   (reference only — no credentials in the report).
5. **Retest guidance**: what to fix first, what a retest will cover.

## Common rules (both types)

- Only `verified: true` findings leave the ledger. No exceptions — this is the anti-slop gate.
- Every PoC is a replayable raw-HTTP bundle (`prompts/write-poc.md` format), never a
  description of a request.
- No credentials, tokens, or client secrets in the report — reference the credential store.
- Write the report file to `report.md` (in the target folder) (bounty: also draft the per-report submission
  text blocks the human can paste into the platform form).
