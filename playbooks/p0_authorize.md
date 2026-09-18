# P0 — Authorize

Goal: an approved, machine-readable scope. Nothing target-facing happens before this.

1. New target: `python3 -m offsec new <name>` (sets `targets/.current`).
2. If HackerOne: `python3 -m offsec.h1 scope <handle>`, `program <handle>`, `rules <handle>`,
   `hacktivity 'team_handle:"<handle>"'`. Audit the FULL policy, not the summary:
   per-asset `eligible_for_bounty` AND `eligible_for_submission`, `max_severity`,
   the full `instruction`, required test environment, excluded classes.
3. `python3 -m offsec.h1 init <handle>` drafts `scope.proposed.yaml`. Fill `roe.notes`
   and `program_rules` from the policy. A human approves: `mv scope.proposed.yaml scope.yaml`.
4. Encode all restrictions in `scope.yaml`: explicit `out` assets override wildcards;
   test-env / excluded classes / rate caps / per-class eligibility go in `program_rules`.
5. Record accepted shapes as you learn them: `offsec shapes add --handle <h> --shape "..." --class ...`.

Gate `authorize -> select`: `offsec advance` passes only when `scope.yaml` exists,
loads, is unexpired, and has a non-empty `in_scope`.
