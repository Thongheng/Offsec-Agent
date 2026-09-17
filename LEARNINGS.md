# Methodology learnings

Lessons from real engagements that change how the kit works. Entries here are promoted
into `prompts/*.md` and `AGENTS.md` as they're validated. Newest first.

## L-13 (2026-09-17) — confirm a class is an accepted bounty on THAT program BEFORE testing it, not after

**What happened:** review feedback — a session must not spend effort proving a class the program
will not accept. The kit had eligibility rules (`AGENTS.md` → "H1 scope audit"; the two flags;
excluded classes) but they lived as a *scope-audit* step, not as a gate attached to **each class
you test**, and the machine-readable form was scattered across `roe.notes`/prose. So a class could
still be fired that the policy excludes (open redirect alone, self-XSS, missing headers,
rate-limit-only) — or tested on an asset that is `eligible_for_submission` but **not**
`eligible_for_bounty`. Effort spent there is a loss even when the bug is real.

**Rule (now implemented):**
1. **`python3 tools/h1.py rules <handle>`** is the one-shot program-detail check: per-asset
   eligibility **plus the FULL policy**. Run it before planning any tests (summary views hide it —
   L-3).
2. **Per-class eligibility is a gate.** Fire a class only if: the *asset* is eligible for **both**
   bounty and submission, the *class* is not on the policy's excluded list, the target is inside the
   required **test environment**, and it is within `max_severity`/partial scope.
3. **Encode it**: `scope.yaml → program_rules` (`excluded_classes`, `chained_only_classes`,
   `test_environment`, `max_severity`, `asset_eligibility_notes`) and the `plan.md` eligibility
   matrix. The **test queue is drawn from eligible classes only**.
4. **Excluded classes are chain-or-kill only** — one attempt at the named impact, else log and move
   on; never a standalone report. (Observing is always free; the gate governs what you spend
   proving and reporting.)

## L-12 (2026-09-17) — don't over-correct into depth/planning: keep a cheap breadth pass, and time-box the decision layer

**What happened:** after L-8/L-9/L-10 pushed toward coverage, provisioning and feature depth, the
workflow risked over-correcting in two ways. (1) The **cheap, high-volume valid-bug classes**
(reflected/stored XSS, HTML injection, open redirect, sensitive-info disclosure, cheap
IDOR/CSRF/CORS, exposed files) had **no explicit home** — yet the disclosed corpus shows they are
the volume leaders (XSS 16.6%, info disclosure 9.6%) and they *are* accepted, just underpaid. The
corpus line "don't chase reflected XSS for payout" is about not *specializing*, not about skipping a
cheap pass; a reflected XSS on an in-scope, non-excluded endpoint is a valid bug (validity, not
severity). (2) The decision/provisioning stage added in L-9 could turn into a **planning loop** —
spending the session on process and questions instead of tests.

**Rule (now implemented):**
1. **A hunt has two modes — BREADTH then DEPTH.** Run the **low-hanging-fruit battery**
   (`prompts/low-hanging-fruit.md`) first: cheap, bounded, eligibility-filtered. It lands valid
   Low/Medium findings that depth-only hunting misses. Then invest in the focus features.
2. **Low severity is not "don't test".** XSS / HTMLi / open redirect / info disclosure are valid if
   in-scope and not excluded. Eligibility-filter them, **chain-or-kill** the excluded ones
   (open redirect alone, self-XSS, missing headers), and **count the rest**.
3. **Time-box the decision layer** (`AGENTS.md` §1c): Stages 1–2 are minutes-to-an-hour, not a
   document or a back-and-forth. Once `plan.md`/`environment.md` exist, **hunt**. Default to the
   next reversible action + a logged assumption; ask the human only when a hard gate blocks or only
   they can act. Planning that never ends is its own failure mode.

## L-11 (2026-09-17, files-bbp post-mortem) — the kit was technique-heavy and order-light; the fix is a gated pipeline, enforced in code

**What happened:** three studies dissected why files-bbp found nothing despite disciplined logging
(`research/h1-reports-analysis.md` — 14,972 disclosed reports; `research/hunter-methodology.md` —
practitioner methodology; `research/workflow-gap-analysis.md` — the kit audit). Findings:

- **The corpus is dominated by authorization/access-control (17.4%)**, and its discovery method is
  dead simple — *use the feature, change the id/tenant* — but it **requires two identities**
  (provisioning). Premium variant: **import/move/copy** operations. Highest-yield real estate for a
  small hunter: **password-reset / email-change / OTP/2FA flows** and **object endpoints**. "Finding"
  = a boundary crossed with a second identity, demonstrated — not a marker or a 200.
- **Hunters find because they sit on *untested* surface, understand *intended* behavior, have the
  *access*, keep a *leads pile*, and chain.** Not because of tooling or scan volume.
- **The kit's order was wrong.** Target selection and environment provisioning were prose bullets
  executed last or never; the coverage map was a baseline artifact never updated at test time; and
  "exhausted" was asserted from `log.jsonl` rather than earned from `coverage-map.jsonl` (114
  `observed`, 0 `authed_tested`, 50 high-worth crown-jewels open — L-8).

**Rule (now implemented — the pipeline is in `AGENTS.md` → "The pipeline"):**
1. Explicit gated order: **0 scope → 1 targeting/`plan.md` → 2 environment/`environment.md` → 3
   recon → 4 `behavior-model.md` → 5 focus → 6 seed → 7 hunt → 8 leads → 9 verify → 10 closeout →
   11 report.** Stages **2** (reachability) and **10** (earned-exhausted) are hard gates alongside
   scope and evidence integrity.
2. Provisioning is a **stage** (`prompts/environment.md`): accounts A + B, the feature tier the
   accepted bugs live behind, seeded objects, `test_infrastructure` deps — no hunt until it passes
   or a blocker is named and scope is explicitly downgraded.
3. The **behavior model** (`prompts/behavior-model.md`) is required before class probes: use the
   feature in the UI, record intended behavior + invariants + the UI/API seam.
4. **Enforcement is code, not prose:** `tools/closeout.py` refuses an unearned "exhausted";
   `tools/leads.py` makes the chain pile first-class; coverage rows carry `focus_feature`/`seeded`
   and are written **at test time**.
5. **Discovery priorities** (from the corpus): authorization before injection; test reset/email/OTP
   flows first on every target; import/move/copy = premium authz; SSRF = find the fetch, verify OOB;
   logic/race = attack the feature's stated invariant; GraphQL = query-shape/authz, not introspection.

## L-10 (2026-09-17, files-bbp engagement) — validity is the bar, not payout; severity must never filter target choice or test priority

**What happened:** reviewing the files-bbp null session, the targeting gate that was written to
replace the missing decision layer (L-9) framed its second gate around **expected payout** —
"crowded + mature + hardened = low EV no matter how large the payout." That is the wrong filter.
The objective is a **valid bug**, not a valuable one: the disclosed set that defines this
program's accepted taste includes a **Medium "existence oracle" and a $600 access-control bug** —
low-to-moderate findings accepted on a mature, hardened program. A gate that discourages hunting
hard targets, or deprioritizes low-severity surface, throws away exactly the class of findings
that actually gets accepted. `AGENTS.md` already says "optimize for discovery depth and breadth,
not submission odds" — the targeting gate contradicted it.

**Rule (now `AGENTS.md` → hard rules; `prompts/targeting.md`; `prompts/attack-loop.md`):**
1. **The success condition is a bug that is reachable, real, in scope, and not excluded.**
   Severity and payout are context, never gates. A Low or Medium valid finding is a win.
2. **Never deprioritize, discard, or withhold a finding because it is low severity or pays
   little.** The only reasons to drop a real, reachable, in-scope behavior are the program's
   excluded list and "working as designed" (docs to back it) — not severity.
3. **Target selection optimizes for *findability* (reachable, under-tested surface), not for
   expected value.** Gate 2 of `prompts/targeting.md` is a prioritization, never a
   disqualifier; a hardened program is still huntable (it may hold valid Low findings). The
   abandon trigger is *unreachable or exhausted surface*, not "low payout."
4. `h1.py pick` payout columns are context only; the disclosed **shapes** are the actionable
   output.

## L-9 (2026-09-17, files-bbp engagement) — bounty outcomes are decided before the first request; we optimized technique and skipped the decision layer

**What happened:** files-bbp closed with no finding on a target carrying three disqualifying
properties, all visible up front: (1) the program's *accepted* bugs (3/3 disclosed) live in the
sharing/permission model, and our test account was an **unpaid trial that disabled sharing** — we
could not reach the bug-bearing surface; (2) the target is mature and crowded (117 reports on
`*.files.com`, a security team that empirically blocked every SSRF bypass family we threw); (3) we
had no edge. Twenty-eight bug classes were fired once each against the free, already-hardened
surface. The kit had a rich technique layer (`attack-loop`, `waf`, `write-poc`) and **no decision
layer**, so the session did the part that matters least.

**Rule (now `prompts/targeting.md` + `AGENTS.md` → "Operating contract"):**
1. **Three gates before hunting.** *Reachability* (can you reach the accepted-bug surface at the
   right tier, with the right accounts and seeded data?), *marginal-report probability* (new
   surface beats big surface; crowded + mature + hardened = low EV regardless of payout), *edge*
   (why you). Fail any → do not hunt, or explicitly downgrade with a stated budget.
2. **Read disclosed *titles*, not counts** — they are the program's accepted taste and hand you
   the exact bug *shape* to replicate on that feature and its siblings.
3. **Environment-first.** Provisioning (paid tier, second tenant, seeded objects) is a go/no-go
   gate, not a late hurdle — a core feature you cannot reach makes the target a trap.
4. **Abandon on budget.** Fixed budget per target; when it expires with no candidate, write the
   honest close and switch targets. Sunk cost is the most expensive bug-bounty habit.

## L-8 (2026-09-17, files-bbp engagement) — "exhausted" is a coverage claim; the coverage map has to prove it

**What happened:** the session closed with "web surface exhausted, no eligible finding." The
`log.jsonl` was genuinely disciplined (56 entries, verify-or-discard held, `findings.jsonl`
correctly empty). But `coverage-map.jsonl` told the opposite story: of 126 rows, **114 sat at
`observed`, 7 were `unauth_tested`, 5 `needs_session_B`, and 0 were `authed_tested`** — 50 of
the `observed` rows were `worth: high` crown-jewels (`remote_servers`, `syncs`,
`siem_http_destinations`, `secrets`, `permissions`, `snapshots`, `user_lifecycle_rules`,
`share_groups`, ...). The prompt's own session-end rule (`attack-loop.md` → "Session end":
reconcile `coverage-map.jsonl`; every crown-jewel must be `authed_tested` / `needs_session_B` /
`excluded`) was never enforced. "Exhausted" was asserted from the log's *test* entries, not from
the map's *state* — and the map said the opposite. Three mechanisms produced the gap:

1. **Empty-collection testing is a mirage.** Almost every collection returned `200, 2B` (empty
   array) because the trial had no objects of that type. `GET /remote_servers -> 200 []` proves
   nothing about per-object authz on the resource; the row sat at `observed` and was treated as
   covered. The engagement never seeded the data model (created a remote_server, a sync, a
   siem_destination, an automation, a user_request) before reasoning about it.
2. **Leads generated, then dropped.** Real anomalies/leads were logged mid-session and never
   queued: `loginFromToken?token=@tok-…` predictability, the server ignoring `bundle_code`
   (line 31), `X-Files-Safe-To-Cache` cache-deception + webhook CRLF (line 44), custom-domain /
   subdomain release-reuse. The one place depth happened — the Share Link control matrix
   (password / max_uses / require_registration / registration-code scoping, logs 27–32) — proves
   the workflow *can* cover a feature; it just happened once. CSRF (a disclosed, payable class
   for this program) was named repeatedly as "next" and never fired.
3. **Provisioning prerequisites surfaced as blockers at the end, not as a plan at the start.**
   "Need a paid plan for SSO/partners", "need a 2nd tenant for cross-tenant", "need an
   admin-seeded data set" — all discovered late and turned into dead ends, when they are
   up-front environment decisions.

**Rule (now in `prompts/attack-loop.md`):**
1. **Pre-flight provisioning gate** (before the loop): list what the high-value classes REQUIRE
   — feature tier/paid plan, a second tenant/session, seeded objects of each crown-jewel type —
   and resolve those before hunting. An unresolved prerequisite is a *named blocker*, not a
   late-session discovery.
2. **Seed the data model.** An empty collection is `observed`, never covered. Create at least
   one of each object *before* testing its authz/state changes; a `200 []` baseline is not
   evidence of hardening.
3. **Leads are a ledger, not a note.** Every anomaly/lead goes to `leads.jsonl` and is worked,
   chained, or explicitly killed with a reason before the session can be called done. The count
   of open leads bounds the "exhausted" claim.
4. **"Exhausted" must be earned from coverage-map state, not the log.** A `no-finding` /
   `exhausted` verdict requires **zero crown-jewel rows at `observed` and zero open leads**.
   Update coverage rows at test time — they are the coverage claim, not a baseline artifact.

## L-7 (2026-09-17, files-bbp engagement) — map the surface as TEST CASES before hunting; class-first probing is not methodology

**What happened:** once authenticated (API key), the session went straight to class-first exploitation —
SSRF (`webhook_tests`), then path traversal, then CORS — firing high-severity hypotheses at resources it
had never observed. All came back clean, and the real gap became obvious: there was **no per-element
surface map**. The artifact produced was a *class matrix over resource names* (groups of endpoints × bug
classes), which reads like a target list and is used like one. It records what COULD break, never what
each element IS or what "normal" looks like, so nothing forces observation and there is no baseline to
call a deviation against.

**Rule (now in `prompts/attack-loop.md`):**
1. The attack surface is a **catalog of test cases**, not a bug list. Every element gets a row:
   *intended behavior · controllable inputs · access level · specific checks · state*. The checks are
   hypotheses to CONFIRM, not exploits to fire.
2. **Baseline before hunt.** Exercise the read-only surface first and record observed behavior
   (status, shape, permissions) in `coverage-map.jsonl`. "Normal" must exist before "abnormal" means
   anything. Do not open a class-based probe on an element still at `observed` with no baseline.
3. Hunt **feature/behavior-driven**: a deviation from the documented/observed baseline IS the
   candidate. The class list is a lens for explaining a deviation, never the driver of what to test next.
4. Do not jump to high-severity classes early; breadth of *checked* surface beats depth of *guessed*
   exploits. High-impact classes are earned by a baseline that makes the boundary meaningful.

## L-6 (2026-09-17, files-bbp engagement) — Burp MCP history: set the scope in OUR tool, not Burp's; `send_*` bypasses history

**What happened:** `burp_mcp.py history` returned 0 with "unparseable response (25 chars)" —
Burp's reply was the literal sentence `No items found (total: 0)`, which the parser treated as
a parse failure. Root cause was two-fold: (1) Burp's own Target scope was empty, so
`inScopeOnly=True` matched nothing; (2) Burp MCP `send_http1/2_request` issues requests through
the HTTP tool, NOT the Proxy listener — so agent-sent traffic never lands in Proxy history.

**Rule (now in `tools/burp_mcp.py`):**
1. `_parse_history_items` treats "No items found" as empty (not an error).
2. `history` fetches the FULL history from Burp and applies **our `scope.yaml`** as the filter
   (authoritative), dropping out-of-scope hosts (analytics/telemetry/third-party) and
   static-asset extensions. Use `--all` for raw output. Don't rely on Burp's Target scope.
3. The surface feed comes from the HUMAN's Burp-proxied browser; agent `send_*` calls are for
   evidence/verification and do NOT populate `proxy-history.jsonl`. Keep the JS-route inventory
   as the surface source when driving the loop through MCP.

## L-5 (2026-09-17, arc-bbp engagement) — mapping a high-impact endpoint is not testing it; the authed surface is the engagement

**What happened:** After ~4h of recon the engagement had correctly identified the two
high-value surfaces: `studio.arc.io`'s sandbox/AI/secrets APIs (`entity-secret`, `github-*`,
`sandbox-file-{write,delete}`, `sandbox-terminal`/`dev-server-restart`, `/api/chat`,
`template-load`) and `onramp.arc.io`'s bank/KYC APIs. It had a live second studio account
(A/B) in hand after log line 43. It then used that account for a single read-only IDOR sweep
of `appId`/`sandboxId`/`threadId` and stopped. `findings.jsonl` ended empty. Separately,
~7,238 dirsearch requests went to `status.arc.io` (Atlassian Statuspage) and a Webflow
marketing site — hosts the agent itself concluded were third-party and N/A.

**Rule:**
1. Once an endpoint is classified high-impact (secret read, code/command execution,
   cross-tenant write, SSRF, payments/KYC), you may not open a new enumeration slice until it
   has been tested with a valid session — or explicitly skipped in `log.jsonl` with a reason.
   Mapping ≠ testing: a route inventory is recon, not coverage.
2. A second account is not "IDOR once." Convert it into a cross-tenant test matrix over every
   state-changing and secret-bearing endpoint before moving on.
3. Pre-flight every directory/content fuzz: if the host is a recognized SaaS CNAME
   (`*.stspg-customer.com`, `cdn.webflow.com`, `cname.mintlify.builders`) or already judged
   third-party, skip it and log a recon note. Do not spend thousands of requests confirming
   "vendor product, N/A."
4. Maintain `coverage-map.jsonl` (observed / unauth_tested / authed_tested / needs_session_B /
   excluded) so "never tested" is visible instead of implied.

## L-4 (2026-09-17, arc-bbp engagement) — an in-scope app's out-of-scope IdP is a test_infrastructure entry, not a blocker

**What happened:** `studio.arc.io` (in scope) authenticates via Circle's Okta IdP on
`login.circle.com` (NOT in `*.arc.io`). The scope gate denied the IdP, so authenticated
testing stalled. The workaround — the human pasting the ~3.5 KB `__session` cookie so the
agent could re-type it — failed once because a single mistyped byte corrupts the base64/
HMAC and the server returns 401. Then the user had to be asked again.

**Rule (now in `AGENTS.md` → "H1 scope audit"):**
1. A target-owned auth/identity dependency required to exercise an IN-SCOPE feature (IdP,
   OAuth provider, the auth API the app proxies) belongs in `test_infrastructure.hostnames`
   with a one-line reason — the gate then allows the minimal interactions needed, and
   `off_limits` still overrides. This is a *dependency* list, never a widening of `in_scope`.
2. Login automation is allowed only against a listed IdP, only with the engagement's OWN
   test accounts, and only to obtain a session for in-scope testing.
3. Never hand-transcribe long tokens/cookies. Read exact bytes from Burp (Active
   Editor/Repeater) or capture them programmatically (e.g. perform the OAuth/OIDC code
   exchange in the tool instead of copying the resulting cookie).
4. If a needed dependency is not yet listed, the fix is to add it (human-authorized), not
   to stall — surface it as a one-line scope update and continue.

## L-3 (2026-09-17, arc-bbp engagement) — the summarized H1 scope hid eligibility and partial scope

**What happened:** the first scope read used `h1.py scope`'s summary line, which printed only
bounty-eligibility and truncated each `instruction` to 60 chars. That hid three things that
matter: (1) `eligible_for_submission` is a **separate** flag from `eligible_for_bounty`;
(2) three assets (`community/explorer/help.arc.io`) were `NO-BOUNTY / NO-SUBMIT` and had been
added to the scope on 2026-09-16 — so they **override the `*.arc.io` wildcard**, and the
human's recon had already browsed explorer (140 reqs) and help (39); (3) `malachite`'s
instruction was **partial scope** ("only code/crates minus the starknet and test folders").
Separately, `h1.py program` truncated the policy at 3,000 chars, cutting off the Test Plan
(testnet-only) and the excluded-classes list.

**Rule (now enforced):**
1. `h1.py scope` prints both eligibility flags, `max_severity`, and the FULL instruction;
   `h1.py program` prints the WHOLE policy. Never audit from a truncated view.
2. An explicit non-eligible asset always overrides a wildcard — check it against recon
   before attacking (live/browsed ≠ eligible).
3. Encode exclusions/test-env/rate rules into `scope.yaml` (off_limits + roe.notes), not prose.
4. Follow `AGENTS.md` → "H1 scope audit" steps 1–5 every program, every time.

## L-2 (2026-09-17, arc-bbp engagement) — burp_mcp.py history parser broke on the real response shape

**What happened:** `python3 tools/burp_mcp.py history` wrote 0 entries despite 555 items in
Burp, printing "unparseable response (447806 chars)". Root cause: Burp's
`get_proxy_http_history` tool returns a `[Total: N | Returned: N | Offset: N | Next offset: N]`
metadata line followed by **newline-concatenated JSON objects**, not a single JSON array.
`_parse_history_items` stripped the header then called `json.loads`, which fails on the
concatenated stream.

**Fix (in tools/burp_mcp.py):** added `_decode_concatenated()` which uses
`json.JSONDecoder().raw_decode` in a loop to consume whitespace-separated JSON values, and
route the `json.JSONDecodeError` fallback through it. Verified: 373 unique in-scope entries
captured.

**Rule:** when a tool result is "unparseable", inspect the *actual* shape (header + N
objects vs array) before assuming a size limit. Also: the MCP tools can be called directly
as a fallback when the python client is broken — but fixing the client keeps the attack
surface in the file the loop expects.

## L-1 (2026-09-07, basecamp engagement) — The threat-model menu is a starting point, never a cap

**What happened:** audit plans were built from the initial ≤5-class threat-model menu, and
testing followed the menu. Real targets reveal hypotheses *during* testing — a redirect
parameter here, a user-input sink there — that the menu never listed.

**Rule (now in attack-loop.md):**
1. The menu seeds the hunt; it does not bound it.
2. Every observed flow, parameter, and request body gets its own class check at the moment
   it's observed — open redirect params, reflection/XSS sinks, upload handling, IDOR-shaped
   ids — regardless of menu membership. Low-hanging fruit is always in scope.
3. New classes discovered this way are logged as decisions and folded back into the
   engagement's threat model.
4. When a rule in these prompts fails or underperforms in practice, record it here and
   update the prompt — the methodology is versioned by use, not by fiat.
