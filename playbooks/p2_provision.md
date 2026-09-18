# P2 — Provision (feature enablement, not login)

Stage 2 passes only when the **bug-bearing features are enabled at the accepted-bug
shape** — verified by a real call, not a flag (LEARNINGS L-16). "I can log in / the API
answers" is not enough. "I created a collaboration and observed it as the other
identity" is.

## Checklist
- [ ] Identity A (attacker) + Identity B (victim/other tenant), live.
- [ ] API/developer credentials unlocked where the program exposes them (OAuth app,
      API key) — do this **first hour**, not at 80% (L-16).
- [ ] For each focus feature, run a **shape probe** and record it:

```
offsec probe --feature F1 --shape "create a collaboration and read it as B" --result enabled --evidence "collab id X seen by B"
# result: enabled | disabled | no_op | error
```

- [ ] Human-only dependencies tracked explicitly, with an owner:

```
offsec dependency --what "paid tier enabling sharing" --owner human
offsec dependency --resolve "paid tier enabling sharing"
```

- [ ] Seed >=1 object per crown-jewel type and exercise the lifecycle (create -> read as
      other -> update -> delete -> side effects). An empty collection is `observed`,
      never covered.
- [ ] For authz features, run an optional role-observation pass before attacking:
      owner/member/viewer/outsider allowed actions become the control matrix.

Gate `provision -> hunt`: `offsec advance` passes only when **every** focus feature's
probe is `enabled` and no dependency is unresolved. A focus feature that is `disabled`
or a silent `no_op` means **abandon** (or an explicit, stated scope downgrade) — never a
long sweep of the remainder.
