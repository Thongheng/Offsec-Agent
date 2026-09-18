# Playbooks — the phase model

`offsec` is a two-tier machine. Tier 1 (engagement gates) run once; Tier 2
(feature slices) is where the actual hunting happens, one focus feature at a time.

```
Tier 1:  authorize -> select -> provision -> [feature loop] -> close -> report -> done
                                             (terminal: abandoned)
Tier 2:  for each focus feature F:
             map F -> model F -> seed F -> hunt F -> verify F
         then, and only then, the next feature.
```

Do not map all features then test all features — that waterfall produced
"91 endpoints swept with one strategy = one cell" (LEARNINGS L-16). Do not open a
new feature while the current one has an open crown element. The CLI enforces both.

## Commands

| What | Command |
|---|---|
| New/select target | `python3 -m offsec new <name>` · `use <name>` |
| Phase status + blockers | `offsec status` |
| Advance a gate | `offsec advance` |
| Select-gate records | `offsec killtest ...` · `offsec yield ...` |
| Provision records | `offsec feature add F1 --name ...` · `offsec probe ...` · `offsec dependency ...` |
| Feature slice | `offsec slice F1 map|model|seed|hunt|verify` |
| Work the loop | `offsec observe` · `hypothesis` · `attempt` · `signal` · `lead` · `evidence` |
| Discovery engine | `offsec run outlier|authz_matrix|lifecycle --spec spec.json` · `offsec run seam --spec ...` |
| Accepted shapes | `offsec shapes add|list|match` |
| Views / gates | `offsec derive` · `frontier --open` · `next` · `closeout` |
| H1 adapter | `python3 -m offsec.h1 scope|rules|hacktivity|pick ...` |

## Ground rules (hard)

- **Scope gate** fails closed: `offsec scope <host...>` and every `transport`
  send check the host actually connected to.
- **Evidence gate**: a 200 or a reflected marker is not a finding. A finding needs
  a boundary crossed, reproducibly, with controls (`p4_verify.md`).
- **Feature-enablement gate**: you cannot start `hunt` until every focus feature
  is `enabled` *at the accepted-bug shape* (a real call that does the thing), not
  merely reachable (`p2_provision.md`).
- **Close gate**: `offsec closeout` must exit 0 (no open crown elements, no open
  frontier, no open leads), or the close names the gaps.

## Reading order

1. `p0_authorize.md` → `p1_select.md` → `p2_provision.md` (engagement gates)
2. `p3_feature_slice.md` (the loop) with `ref_discovery.md` and `ref_transport.md`
3. `p4_verify.md` → `p5_close.md` → `p6_report.md`
