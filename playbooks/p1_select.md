# P1 — Select (yield first)

The single biggest cause of zero findings was picking mature, hardened, heavily-swept
targets with no edge (LEARNINGS L-17). Selection is a **yield** decision, not a
reachability decision.

**Portfolio, not single-shot.** Run a <=1h kill test on 3-5 candidates:
- can you sign up / log in?
- can you reach **one accepted-shape feature on a usable tier** — at the shape, not just
  a page that loads?

**Record each kill test and the yield assessment** so the gate can check them:

```
offsec killtest --candidate <h> --result hit|miss|partial --evidence "..."
offsec yield --shapes <#accepted shapes> --enabled <#reachable features> --contexts <#> --notes "..."
```

The select gate expects 3-5 candidate kill tests. If the engagement is a private
single-target pentest or fewer candidates are legitimately available, record the
reason explicitly:

```
offsec killtest --candidate <h> --result hit --evidence "..." --override-reason "private engagement has one authorized target"
```

`huntable_cells = shapes x enabled x contexts`. A small intersection means a scope
downgrade or `abandoned` — not a long sweep of the remainder.

**Yield inputs are product facts, never policy metrics:** fresh/under-tested surface,
bug density (young > famous), attention (niche > household-name), your edge. Never rank
on disclosed counts, exclusion lists, or payout.

**Focus features (1-3) are chosen here**, from the accepted shapes:

```
offsec feature add F1 --name "sharing/collaboration permissions"
```

Gate `select -> provision`: `offsec advance` passes only when 1-3 features exist,
3+ kill tests are recorded (or an override reason exists), and a yield assessment
is recorded.
