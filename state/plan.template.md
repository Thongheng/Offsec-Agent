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

## Gate 2 — Findability  (a prioritization, NOT a filter)
- Fresh / under-tested surface (new assets, new features, few reports): ...
- Maturity/crowding shapes WHERE to look first — it never disqualifies a target, and severity is
  never a reason to skip surface.

## Gate 3 — Edge  (optional)
- ...

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
