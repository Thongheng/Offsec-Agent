# Prompt: Low-hanging fruit battery (cheap, broad, run EARLY)

Purpose: harvest the valid bugs that are **cheap to find**, before and alongside deep feature work.
Validity, not severity, is the bar — a valid Low/Medium is a win. These classes are the *volume
leaders* in the disclosed corpus (XSS 16.6%, info disclosure 9.6%): accepted, just underpaid. The
corpus advice "don't chase reflected XSS for payout" is about **specializing**, not about skipping
a cheap pass — a reflected XSS on an in-scope, non-excluded endpoint is still a valid bug.

A hunt has **two modes**:
- **BREADTH** — this battery. Cheap, bounded, run first.
- **DEPTH** — the focus features (`prompts/attack-loop.md`, behavior model).

Do breadth first; it costs little and often lands a valid finding before you invest in depth.

## Rules
1. **Eligibility filter first.** Pull the program's excluded-class list (`scope.yaml` → `roe.notes`
   / policy). Common exclusions: **open redirect alone, self-XSS, missing headers / cookie flags,
   version-banner disclosure, clickjacking without impact, rate-limit-only**. A candidate in an
   excluded class is **chain-or-kill**: one attempt at the named impact, else log `not-vulnerable`
   and move on (`attack-loop.md`). Do not report excluded classes.
2. **Bounded, not a scan.** One probe per observable param/endpoint, log, move on. No heavy payload
   fuzzing. This is a sprint, not a scan — time-box it.
3. **Signal-gated depth.** Every LHF surface gets one *cheap* probe and a terminal outcome. If there
   is **no signal**, close it — `frontier.py set <id> --state tested_clean` — and move on. Never dig
   on a hunch. If there **is** a signal (a reflection, a differential, an odd status/body/timing, a
   leaked error), promote it — `frontier.py signal <id> "..."` — and spend the depth budget there.
   Depth is earned by evidence.
4. **A hit still needs boundary-crossing proof.** A reflection is not XSS until it executes in a
   real browser context with escaping bypassed (`prompts/write-poc.md`). A `200` is not a leak.
5. **A negative battery is ONE result, not coverage.** On a hardened/mature target the whole battery
   can come back negative in an hour — that is expected, and it is fine, but it is **one cell**
   (anonymous/reflected classes) of the attacker-context × class × feature matrix, not "the target is
   clean". When the battery saturates with zero signals, do **not** re-run it with more payloads:
   escalate to the featured/stateful cells or state the ceiling plainly in the summary. box_private
   produced ~23 consecutive negatives across the cheap classes; the discipline failure was treating
   that as progress (`LEARNINGS.md` L-16).

## The battery (ordered by cheapness × acceptance)
1. **Reflected / HTML injection** — for each reflected param, inject a unique marker
   (`zzq9f3a"><'`), find the reflection, determine context (HTML / attribute / JS string / URL) and
   whether `<` `"` `'` are encoded. HTML injection is valid if it actually renders; XSS if a
   payload executes. Check error pages, search, redirect messages, 404 pages.
2. **Stored / second-order / blind XSS** — inputs rendered to another user or an admin panel:
   names, filenames, comments, labels, profile fields, support tickets. Fire a marker + a blind
   payload (Burp Collaborator) and check the sink.
3. **Open redirect** — params `redirect, next, url, return, continue, dest, callback, target, r, u,
   to, link, goto`. Try `//evil`, `/\evil`, `https:evil`, `https://evil`, `/%09/evil`, userinfo/host
   confusion. **Chain-or-kill** per policy (an open redirect that reaches a token-steal/ATO path is
   the report; the redirect alone usually isn't).
4. **Sensitive info disclosure** — verbose errors / stack traces; **API responses carrying fields
   the UI never shows** (compare UI vs API); debug endpoints; exposed `.git/`, `.env`, `.svn/`,
   `*.bak`/`*.old`, source maps; directory listing; scheduled exports. **Existence oracles** (valid
   vs invalid id/path response diff) are an *accepted* shape on some programs — Files.com paid one
   for folder-path existence — so test them but read the exclusions.
5. **CORS** — `Origin: https://evil.com` on authed endpoints: is it reflected in
   `Access-Control-Allow-Origin`, with `Allow-Credentials: true`?
6. **IDOR (cheap)** — swap every id / uuid / email / tenant param for a neighbor; check both
   "denied" **and** "did any data leak" (a 200 with an empty body is different from a 403).
7. **CSRF** — state-changing endpoints: is there a token, is it validated server-side, is it bound
   to the session? Usually accepted as an ATO/impact chain, not alone.
8. **Cache / header edge** — unkeyed headers (`X-Forwarded-Host`, `X-Forwarded-Scheme`), cache
   deception via extension suffix, weird custom headers (`X-Files-Safe-To-Cache`-style).
9. **Forced browsing / exposed files** — `.git/config`, `/server-status`, `/phpinfo.php`, `/swagger`,
   `/actuator`, `/api/docs`, backup/config paths.

## Output
Log **every** attempt in `log.jsonl` (result + evidence). Each probe is a **frontier item**:
`frontier.py add --element "..." --hypothesis "..." --budget cheap` up front, then
`frontier.py set <id> --state tested_clean|excluded|needs_B|blocked` (or `signal` it) when the
result is in — and write the element's `coverage-map.jsonl` row in the same step. Boundaries
crossed → `findings.jsonl` (`verified: true`) or `leads.jsonl` (chain candidates). A cheap pass is
not an excuse to leave the frontier or the map stale.
