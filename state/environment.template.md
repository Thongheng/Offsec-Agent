# Environment & access — <target>

Stage 2 hard gate (`prompts/environment.md`). No hunt loop until every must-have is `done` or a
**named blocker with an owner**. A blocker that is never resolved appears in the closeout as a
**named gap**, not hidden behind "exhausted".

## Account matrix
| id | role | site / tenant | credentials ref | notes |
|----|------|---------------|-----------------|-------|
| A  | attacker |  |  |  |
| B  | victim / other tenant |  |  | `needs_session_B` rows depend on this |
|    | lower-priv role |  |  |  |

## Feature tier
| focus feature | tier/plan required | actually enabled? | notes |
|---------------|--------------------|-------------------|-------|
|  |  |  |  |

## Seeded objects  (one per crown-jewel type; lifecycle: create -> read-as-other -> update -> delete)
| resource | created? | id / path | lifecycle exercised |
|----------|----------|-----------|--------------------|
|  |  |  |  |

## Out-of-scope dependencies  (`scope.yaml` -> test_infrastructure)
| host | why (which in-scope feature needs it) |
|------|---------------------------------------|
|  |  |

## Transport
- **UI path** (preserves the UI/API seam) used for: ...
- **API key** (endpoint coverage) used for: ...

## Blockers
| must-have | status | owner | ETA |
|-----------|--------|-------|-----|
|  |  |  |  |
