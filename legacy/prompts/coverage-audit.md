# Prompt: Coverage audit (fresh-eyes reviewer)

Use this to spawn an **independent audit** — ideally as a subagent with a **fresh context** that
sees only the artifacts, not the hunting conversation. The hunter that missed something cannot
see that it missed it: the same context that went blind will not notice the blindness. A new
reader with the ledgers in hand catches what focus dropped.

This is **audit, not hunt**. It fires no requests against the target. It reads state and reasons.

## Read only these (no proxy, no target)
- `plan.md` — the intended gates, focus features, budget.
- `environment.md` — accounts, seeded objects, blockers.
- `behavior-model.md` — intended behavior per focus feature.
- `frontier.jsonl` — the worklist (what is still OPEN).
- `coverage-map.jsonl` — per-element state.
- `leads.jsonl` — anomalies / chain candidates.
- `log.jsonl` — what was actually attempted and its result.
- `findings.jsonl` — verified / candidate findings.

## What to look for (report each as a gap, with evidence)
1. **Un-terminated surface**: elements still `observed`, crown-jewels not `authed_tested` /
   `needs_B` / `blocked` / `excluded`. List them.
2. **Frontier integrity**: OPEN items never worked; items marked terminal without an
   `evidence` pointer; duplicate `(element × hypothesis)` pairs; hypotheses that were named but
   never seeded (a class in the docs but not in the frontier).
3. **Un-followed anomalies**: log entries whose `result` is `info-found` / `anomaly` /
   `inconclusive` that produced **no** frontier item or lead. These are the silent drops.
4. **Findings not chained**: any `findings.jsonl` or `leads.jsonl` entry where the obvious
   "what does this let me reach next?" question was never asked.
5. **Single-attempt verdicts**: a class dismissed on ONE attempt where the response was not
   interpreted, or where siblings were never tested (a class cleared on one endpoint is not
   cleared on its twins).
6. **Baseline gaps**: focus features in `plan.md` with no `behavior-model.md` entry, or elements
   probed before being observed/baselined.
7. **Coverage claims vs. ledger**: does any "exhausted" / "done" claim in the log contradict the
   counts in `frontier.jsonl` / `coverage-map.jsonl` / `leads.jsonl`?

## Output
A short report (in the session reply; optionally `areas/audit-<date>.md`) with:
- **Named gaps**, each with the artifact line it comes from.
- **Recommended frontier items** — literal commands:
  `python3 tools/frontier.py add --element "..." --hypothesis "..." --source "audit" --priority high`
- **Chain candidates** — for each finding/lead, the next test its existence enables.

Do not soften. The job is to find what was skipped — a clean audit that finds nothing is
acceptable only if every element genuinely has a terminal state and every anomaly was worked.

## Feeding back
The audit produces **work**, not opinions: every recommended item is added to `frontier.jsonl`
and then goes through the normal loop. Re-run the audit after a large batch of frontier work, or
whenever the frontier looks "too clean" for how much surface existed.
