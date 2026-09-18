# P5 — Close

"Exhausted" is a coverage claim and must be **earned from derived state**, not asserted
from the log (LEARNINGS L-8).

```
offsec closeout
```

It exits 0 only when all hold:
- zero open crown elements (every crown element has a terminal attempt cell and no
  unresolved signal) — an `observed`-only crown element is a named gap;
- zero open frontier items (`new`/`in_progress`/`lead`);
- zero open leads.

If it exits 1, the honest close is: **"N crown elements untested, M frontier items open,
K leads open, blocked by <reason>"** — never "exhausted".

```
offsec advance          # hunt -> close, then close -> report, then report -> done
offsec abandon --reason "focus features tier-gated; named gaps ..."
```

An abandoned target with a named reason is a first-class result. A session that limps on a
hardened/gated surface is the failure this gate exists to prevent.
