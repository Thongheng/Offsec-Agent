# Engagement plan — <target>

Contract for this engagement. See `prompts/targeting.md`. No hunt loop starts until Stage 2
(`environment.md`) passes. The correct outcome is chosen **before** hunting, not after.

budget:        <N sessions>
abandon_when:  <unreachable surface OR reachable surface genuinely exhausted — NEVER "low payout">

## Gate 1 — Reachability of the bug-bearing surface  (the hard gate)
- Accepted bug shapes (from `h1.py hacktivity` TITLES): ...
- Feature / tier those require: ...
- Our access (account/tier/tenant): ...
- Verdict: reachable / unreachable / partial

## Gate 2 — Product-shape match  (a prioritization, NOT a filter)
- Which product features carry the accepted shapes (multi-tenant objects, URL fetchers, upload/parse,
  auth/SSO, sharing/collab)? ...
- Fresh / under-tested surface (new assets, new features): ...

## Gate 3 — Yield / edge  (a GATE; reject if none)
- Lifecycle window: launch / mature-crowded / neglected-but-shipping
- Fresh surface or edge we are betting on: ...
- Verdict: take / depth-only(reason) / REJECT (no edge + mature + no fresh surface)
- Kill test (≤1h): reached one accepted-shape feature on a usable tier? yes/no -> evidence

## Focus features  (own 1–3; derived from the accepted shapes)
1. ...
2. ...

## Provisioning checklist  -> see `environment.md`
- [ ] account A (attacker)   - [ ] account B (victim/other tenant)   - [ ] lower-priv role
- [ ] feature tier that enables the focus features
- [ ] seeded objects for each crown-jewel type
- [ ] `test_infrastructure` dependencies listed in `scope.yaml`

## Class eligibility matrix  (from `python3 tools/h1.py rules <handle>`; fill BEFORE testing)
Only eligible classes are tested. Excluded classes are chain-or-kill, never reported standalone.

| class | asset | bounty+submit? | excluded? | test-env ok? | verdict |
|-------|-------|----------------|-----------|--------------|---------|
|  |  |  |  |  | test / chain-only / skip |

Encoded in `scope.yaml -> program_rules` (excluded_classes, chained_only_classes, test_environment).

## Outcome
`hunt` / `provision-then-hunt` / `abandoned(reason)` — decide here, before Stage 3.
