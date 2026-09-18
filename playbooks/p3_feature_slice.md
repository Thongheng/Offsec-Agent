# P3 — The feature slice (this is the hunt)

The unit of work is one focus feature, end to end. Finish it before opening the next.
The CLI enforces the order (`offsec slice F1 <step>`).

```
map F -> model F -> seed F -> hunt F -> verify F
```

## map F
Get the feature's real request contracts from the **JS bundles**, not by clicking
(LEARNINGS L-16). Register every element you will test:

```
offsec observe --element "GET /app-api/item/{id}/collaborators" --feature F1 --class crown-jewel --worth high
```

## model F
State, for the feature: what it is meant to do (docs/UI), its invariants, the contexts
that matter (`anon`, `owner`, `other`, `two_identity`, `shared_holder`), and the
**UI-vs-API seam** (capture the UI request; compare to your synthesized one).

## seed F
Create the objects and identities the feature needs. No empty-collection verdicts.

## hunt F
1. **Breadth battery first** (cheap, capped): reflected/stored XSS, HTML injection,
   open redirect, sensitive-info disclosure, cheap IDOR/CSRF/CORS, exposed files.
   Excluded classes are chain-or-kill. Time-box it; do not let it become the session.
2. **Then the discovery engine** (`ref_discovery.md`): outlier harvester, authz matrix,
   lifecycle, seam. Fire the experiment that tests your reasoning — not a shotgun.
3. **Signal-gated depth.** One cheap probe per element; no signal -> `tested_clean`,
   move on. A signal -> `offsec signal --ref W-xxxx --why ...` and spend depth.
4. **Record at test time** (one command writes coverage + frontier together):

```
offsec attempt --element "..." --result not-vulnerable|worked|blocked|needs_B|excluded \
  --context other --class authz --feature F1 --ref W-0001 --evidence "A->B 404; B->own 200"
```

5. **Stop firing a saturated family.** A full cheap pass over one class family with zero
   signals is ONE result. Escalate to the highest-complexity reachable cell (multi-step,
   state machine, race, two-identity role change, import/move/copy, the seam) or abandon
   with a named reason — do not sweep the remainder.

## verify F
```
offsec slice F1 verify
```
Blocks while any crown element for F1 is `observed` or carries an unresolved signal
(LEARNINGS L-8). Then move to the next feature.

## Anomalies are work, not notes
Every weird response, ignored parameter, odd token/header -> `offsec signal` or
`offsec lead` immediately. They are chain candidates; accepted reports are often chains.
