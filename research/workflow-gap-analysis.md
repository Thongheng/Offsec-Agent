# Workflow gap analysis — offsec-agent vs how bug bounty actually works

Audit date: 2026-09-17. Scope of audit: the whole kit as encoded (`AGENTS.md`, `prompts/*`,
`tools/*`, `state/*`, `.opencode/skills/offsec/SKILL.md`) plus the completed `targets/files-bbp/`
engagement, used as the case study (a full session that found nothing).

The kit has a strong *technique* layer (attack-loop, waf, write-poc, scope gate, Burp transport) and,
since the files-bbp retro, a *decision* layer (`prompts/targeting.md`, LEARNINGS L-8/L-9/L-10). The
gap is not missing ideas — it is **order, wiring, and artifacts**: the decision and provisioning
stages exist as prose bullets that the workflow does not force you to execute, produce an artifact
for, or pass before the technique stages begin. files-bbp is the proof: the correct conclusion
(`plan.md`) was written *after* the session, and the false conclusion ("web surface exhausted") was
recorded *during* it.

---

## 1. The workflow the kit actually encodes

Reading the prompts as an instruction processor (not as intent), the order of operations is:

1. **Resolve target** — `targets/.current`, else `new_target.py`; `SKILL.md` step 2.
2. **Scope bootstrap** — `h1.py init` → `scope.proposed.yaml`; human approves with `mv scope.yaml`.
   `AGENTS.md` "Scope bootstrap".
3. **H1 scope audit** — `h1.py scope` + `program` + `hacktivity`; encode eligibility, exclusions,
   test env, RoE into `scope.yaml`. `AGENTS.md` "H1 scope audit". (This part is genuinely good.)
4. **Recon** — `prompts/recon.md`: consume subdomain enum output, tier hosts, dirsearch Tier A.
   Output `attack-surface.md`.
5. **Capture** — human browses the app through Burp; `tools/burp_mcp.py history` →
   `proxy-history.jsonl`.
6. **Hunt loop** — `prompts/attack-loop.md`: build per-element surface map, baseline, pick an
   untested element, class menu, crown-jewel gate, verify-or-discard, leads, session end.
7. **PoC** — `prompts/write-poc.md` + `poc_replay.py`.
8. **Report** — `prompts/report.md`.

The decision layer (`prompts/targeting.md`) and the provisioning gate are **not stages 0/0b** in this
sequence. They are:
- `targeting.md`, reachable only from the `SKILL.md` routing row *"find a program / what should I
  hunt"* — i.e. loaded when *choosing* a program, not when *starting* one.
- a `## Before the loop (once per engagement)` bullet inside `attack-loop.md` ("Pre-flight
  provisioning gate"), plus a section in `targeting.md`.

Both are advisory text. Neither produces an artifact, neither has an exit condition checked in code,
and neither is referenced by the skill's routing table for the words "start", "hunt", or "attack".
`AGENTS.md` step 1b does call provisioning "a go/no-go gate", but it is the only place, and it is a
prose contract the workflow can (and did) skip.

---

## 2. What that workflow caused in files-bbp (evidence)

Timeline reconstructed from `targets/files-bbp/log.jsonl` (59 lines) and mtimes:

| time | action | stage |
|---|---|---|
| 07:35 | JS bundle extraction; app surface; secret scan; scope notes | recon |
| 07:37 | unauth `settings/domain.json` (candidate F-files-1); REST 401 wall | unauth class probe |
| 07:38 | "needs a trial site" decision (blocked), note to provision A/B | *provisioning deferred* |
| 07:45 | `subfinder -d files.com` → **2734 subdomains** on a program whose policy authorizes only listed assets | recon |
| 07:49 | dirsearch `app.files.com` — useless (SPA catch-all), noted | recon |
| 07:50 | source-map probe | recon |
| 07:55 | login error differential | class probe |
| 08:05 | F-files-1 skeptic review → hold | decision |
| 08:33 | open-redirect attempt | class probe |
| 08:36 | transport recon: browser session non-replayable | transport |
| 08:40 | Burp history pulled (trial A); token lead logged | capture |
| 08:41 | API key provisioned → Basic auth works | *access, mid-session* |
| 08:43–08:47 | SSRF (webhook), path traversal, CORS, SDK | class sweeps |
| 08:53–09:00 | Share-Link control matrix (password/max_uses/require_registration) | **feature depth (the one good slice)** |
| 09:03–09:16 | info-leak, stored XSS, IDOR, privesc, domains, BFLA sweeps | class sweeps |
| 09:16 | "hidden surface" list: TransformScript, zip-slip, cache, subdomain reuse, CSRF… | ideas, mostly not fired |
| 09:20–09:58 | transform/zip, download XSS, public hosting, write-share, workspace isolation | feature probes |
| 09:58 | second trial site blocked (CAPTCHA) | *provisioning blocker, hour 2.5* |
| 15:36 | `coverage-map.jsonl` last written — baseline rows, never re-stated | coverage |
| 17:10 | `leads.jsonl` **created retroactively** (10 leads) | leads, too late |
| ~15:00 | log final: *"Web surface exhausted… No eligible finding."* | **false close** |

Quantitative proof of the failure (`coverage-map.jsonl`, 126 rows):

- **114 `observed`, 7 `unauth_tested`, 5 `needs_session_B`, 0 `authed_tested`** — matching L-8.
- 50 of the `observed` rows are `worth: high` crown-jewels (`remote_servers`, `syncs`,
  `siem_http_destinations`, `secrets`, `permissions`, `snapshots`, `user_lifecycle_rules`,
  `share_groups`, …), every one returning `200, 2B` (empty array) because the trial never seeded the
  data model.
- `findings.jsonl` = 0 bytes (correct: verify-or-discard held).
- 10 real leads existed at close, all `open`, none worked (CSRF — a *disclosed, payable* class for
  this program — never fired).

So the workflow caused the agent to: do solid recon, fire **28 classes once each** against the free
tier, produce a genuinely disciplined `log.jsonl`, and then close with a coverage claim the coverage
map contradicted. It **failed to cause**: the reachability/decision pass, the provisioning of the
feature tier and second tenant *before* hunting, seeding the data model, staying on one feature, and
working the leads to closure.

The root causes are structural, not behavioral:
- The accepted bugs (3/3 disclosed) were **sharing/permission feature-logic** shapes; the account was
  an **unpaid trial that disabled sharing** (bundle create → 422). Reachability failed at
  authorization-feature level and was only diagnosed at the end (`plan.md`).
- The agent moved from the UI to an **API key** for transport (because the browser session was
  non-replayable) — correct for REST coverage, but it removed the *UI-vs-API seam* where the
  accepted bugs live (`prompts/attack-loop.md` itself names this seam as where accepted logic bugs
  are).
- The coverage map was populated as a **baseline artifact** ("`retest_when`: after baseline reasoning
  pass"), then never updated at test time — the opposite of the AGENTS.md rule.
- "Exhausted" was asserted from `log.jsonl` **test entries**, not from `coverage-map.jsonl` **state**.

---

## 3. A correct bug-bounty workflow

Synthesised from `research/hunter-methodology.md` (Haddix, Rosén, NahamSec, Curry, Bugcrowd,
HackerOne triage docs) and the kit's own retro findings. The ordering that matters:

```
0 Authorization & scope          (hard gate, human-approved)
1 Target selection / go-no-go    (DECISION: reachable? findable? edge? budget?)   -> plan.md
2 Environment & access gate      (accounts A/B, feature tier, seeded objects, deps)-> environment.md
3 Surface discovery (recon)      (passive-first, scoped, fresh-surface-first)      -> attack-surface.md
4 Product walkthrough + docs     (use it like a user; intended behavior; UI/API seam)-> behavior-model.md
5 Focus-feature selection        (own 1-3 features where accepted bugs live)       -> plan.md §focus
6 Seed the data model            (one object per crown-jewel type)                 -> seed log
7 Feature-driven hunt            (crown-jewel gate, sibling propagation, A/B matrix)
8 Leads / chain pile             (anomalies are queued work, worked to closure)
9 Verification                   (boundary-crossing PoC with controls)
10 Coverage reconciliation       (earned "exhausted" or named gaps)                -> closeout
11 Reporting
```

The three load-bearing inversions vs the kit's current order:

- **Decision before technique.** Reachability and accepted-bug *shape* are known before the first
  request (from the program's own disclosed titles and policy), so they cost nothing to settle first.
  The kit settles them last.
- **Provisioning is a gate, not a hurdle.** Two-account differential testing is the *only* reliable
  way to prove BOLA/BFLA (hunter-methodology §4); a paid tier is a prerequisite for anything
  authorization-shaped on this class of target. Discovering the trial restriction at hour six
  converts a decision into a sunk cost.
- **Baseline → behavior model → feature depth**, not baseline → class sweeps. Authz and logic bugs
  are the highest-payout classes and cannot be found by pattern-matching payloads; they need a model
  of intended behaviour (docs + UI) that the class menu cannot supply.

---

## 4. Gap table

| # | Stage | Kit today | Correct | Gap |
|---|---|---|---|---|
| 0 | Authorization / scope | Strong: `scope_check.py` (fail-closed), `scope_hook.py`, `AGENTS.md` H1 audit, `scope.yaml` | Human-approved scope + RoE + encoded exclusions | Minor: hook "not wired in this repo" (noted); else fine |
| 1 | **Target selection / go-no-go** | `prompts/targeting.md` (72 lines), `h1.py pick/hacktivity`; loaded only on "find a program"; `plan.md` written *retroactively* in files-bbp | Mandatory stage before every engagement; gates with evidence; **budget + abandon rule enforced**; output = `plan.md` as engagement contract | **Not wired** into SKILL routing or AGENTS as a pipeline step; no budget artifact; no machine-readable go/no-go; abandoned-target outcome not recorded as such |
| 2 | **Environment / access provisioning** | One "pre-flight" bullet in `attack-loop.md` + a section in `targeting.md`; discovered late in files-bbp | Standalone **gate**: A + B accounts, feature tier, seeded-object list, `test_infrastructure` deps, named blockers; **no hunting until pass or explicit scoped downgrade**; artifact `environment.md` | **Biggest gap.** No prompt, no artifact, no exit condition. Empty-collection mirage and late CAPTCHA blocker are direct consequences |
| 3 | Surface discovery | `prompts/recon.md` (good: host tiering, SaaS-CNAME pre-flight, rate) ; `burp_mcp.py history` | Passive-first, scope-aware; fresh surface first (disclosed-shape-driven) | files-bbp ran `subfinder -d files.com` (2734 subs) on a listed-assets-only program; ran dirsearch on a SPA catch-all; the **fresh asset** (`*.hosted-by-files.com`, 0 reports) tested once, late. No "narrow-scope ⇒ skip broad enum" branch |
| 4 | **Product walkthrough + behavior model** | "Use the product like a user" bullet inside `attack-loop.md`; baseline GETs recorded in `coverage-map.jsonl` | Named stage: real UI session, docs read, intended-behaviour model, UI/API seam, feature inventory → `behavior-model.md`; baseline is its output | No artifact; no docs-reading stage; transport pivoted to API key, losing the UI seam where accepted bugs live |
| 5 | Focus-feature selection | "Own one feature" prose in attack-loop/targeting | Plan names 1–3 focus features from disclosed shapes; coverage tracks feature slices | No `focus_feature` field anywhere; `coverage-map` rows are endpoint×class, not features |
| 6 | Seed the data model | L-8 rule ("empty collection is `observed`, never covered") | Create ≥1 object per crown-jewel type before judging authz | No seed script/template; 50 high-worth rows sat on `200 []` |
| 7 | **Hunt loop direction** | `attack-loop.md` is strong (crown-jewel gate, sibling propagation, chain pile) | Feature-driven depth over the 1–3 focus features | In practice the loop ran **class sweeps** (batches `info`/`xss`/`idor`/`priv` in `probe.py`); one feature (bundles) got real depth. Tooling biases class sweeps |
| 8 | Leads / anomaly capture | `state/leads.example.jsonl` + `leads.jsonl` added **after** files-bbp; session-end "zero open leads" rule | First-class, updated *during* the loop; anomalies queued as work | Created retroactively; no tooling, no mid-loop enforcement; 10 leads open at the false close |
| 9 | Verification | Strong: `write-poc.md` controls, `poc_replay.py` scope-check + rate, marker rules | Boundary-crossing proof with controls | Fine. (Only weakness: `poc_replay.py` records to `requests.jsonl` but nothing consumes it) |
| 10 | **Coverage reconciliation / closeout** | `attack-loop.md` "Session end" rules; `engagement.py` scaffolds ledgers | Computed, enforced "earned exhausted"; explicit named gaps | No tool; map updated as baseline only; states lack `blocked`/`exhausted`; files-bbp logged a **false "exhausted"** then corrected it in a retro |
| 11 | Reporting | Strong: `report.md` (bounty vs pentest branches) | — | Minor: duplicate rule ("same type, different endpoint ≠ dupe") from hunter-methodology §6 not encoded |

---

## 5. The seven specific assessments

**(a) Decision layer before hunting?** Partially, and not enforced. `prompts/targeting.md` is a good
design (three gates, disclosed-shape analysis, severity-is-not-a-gate) but it was written *after*
files-bbp and is reachable only via the skill's "find a program" row. `AGENTS.md` step 1b mentions it,
but the operating contract's numbered sequence still starts at scope → hunt. `plan.md` was authored
retroactively. **Verdict: exists, unwired, unenforced, no artifact contract.**

**(b) Environment/access provisioning: gate or afterthought?** Afterthought. It is one bullet under
"Before the loop" and one section in targeting. No artifact, no pass/fail, no blocker registry, no
"stop hunting until resolved". files-bbp discovered the unpaid-trial sharing restriction and the
missing second tenant *during* the session and closed on them. **Verdict: afterthought — the single
largest structural gap.**

**(c) Feature depth or class sweeps?** Class sweeps in practice, despite the prompts. files-bbp fired
28 classes once each; the surface map (`areas/attack-surface.md`) is an excellent catalog but was used
as a class target list; only the Share-Link matrix (logs 27–32) achieved feature depth. The
`coverage-map` schema (endpoint × class) and the batch-oriented `probe.py` both bias sweeps.
**Verdict: the prompts now say depth; the artifacts and tooling still say breadth.**

**(d) Force using the product like a user?** No. The prompt says to, but there is no walkthrough
stage, no UI-action artifact, and no seam tracking. In files-bbp the browser session was
non-replayable, so the agent switched to an API key and drove REST directly — losing exactly the
UI-vs-API seam the prompt calls the home of accepted logic bugs. **Verdict: intent present, mechanism
absent.**

**(e) Leads/anomaly capture?** Now exists (`leads.jsonl`, `leads.example.jsonl`, L-8), but it was
created *after* the engagement from dropped notes. During the session, anomalies (`loginFromToken`
predictability, ignored `bundle_code`, `X-Files-Safe-To-Cache`, webhook CRLF, subdomain reuse, CSRF)
were logged as prose and abandoned. **Verdict: captured, but too late and not enforced.**

**(f) Coverage reconciliation + honest "exhausted"?** The rules are now excellent (attack-loop
"Session end"); there is no tooling, and the map is treated as a baseline rather than a live coverage
claim. files-bbp recorded "Web surface exhausted" while the map showed 114 `observed` / 0
`authed_tested` and 50 crown-jewels untested. **Verdict: rule present, no enforcement, false claim
was made.**

**(g) Target-selection / recon quality?** Targeting gates are well-designed but late and unwired.
Recon over-enumerated a narrow-scope, listed-assets-only program (2734 subdomains) and under-weighted
the one genuinely fresh asset (0 reports). Docs/intended-behaviour reading happened piecemeal and was
used defensively (to disprove F-files-1) rather than as a hunting driver. **Verdict: sound in design,
mis-ordered and undisciplined in execution.**

---

## 6. Proposed ordered pipeline (gates + artifacts)

Each stage names: **gate** (what must be true to proceed), **artifact** (what it writes), **existing
mapping**, **missing**.

### Stage 0 — Authorization & scope (hard gate)
- **Gate:** human-approved `scope.yaml`; `scope_check.py` passes for every host; RoE caps encoded.
- **Artifact:** `scope.yaml`.
- **Existing:** `AGENTS.md` H1 audit, `tools/h1.py`, `tools/scope_check.py`, `scope_hook.py`.
- **Missing:** nothing structural (optional: wire `scope_hook.py` in `.opencode`).

### Stage 1 — Target selection / go-no-go (decision gate)
- **Gate:** Gate 1 reachability, Gate 2 findability, Gate 3 edge (`prompts/targeting.md`); **budget
  assigned**; outcome is one of `hunt` / `provision-then-hunt` / `abandon`.
- **Artifact:** `plan.md` (gates with evidence, accepted bug **shapes**, focus features, provisioning
  checklist, budget + abandon condition).
- **Existing:** `prompts/targeting.md`, `h1.py hacktivity/pick`, `AGENTS.md` step 1b.
- **Missing:** mandatory wiring (SKILL routing + AGENTS pipeline); a `budget:`/`abandon_when:` field;
  recording `abandoned` as a first-class outcome.

### Stage 2 — Environment & access provisioning (hard gate) **← new stage**
- **Gate:** every `must-have` in the checklist resolved to `done` or a *named blocker with an owner*.
  If a bug-bearing feature is unreachable, either provision or **explicitly downgrade scope with a
  stated budget** — never silently proceed.
- **Artifact:** `environment.md` — accounts (A / B / low-priv), feature tier/plan, seeded-object list
  per crown-jewel type, `test_infrastructure` dependencies, blocker table.
- **Existing:** `scope.yaml` `test_accounts` / `test_infrastructure`, L-4, `AGENTS.md` step 6.
- **Missing:** `prompts/environment.md`; `environment.md` scaffold in `engagement.py`; a
  `provisioning` check in the closeout.

### Stage 3 — Surface discovery (recon)
- **Gate (passive-first):** captured traffic accounted for; enum scope equals authorized scope.
- **Artifact:** `attack-surface.md`, `proxy-history.jsonl`.
- **Existing:** `prompts/recon.md`, `tools/burp_mcp.py history`.
- **Missing:** a narrow-scope branch ("listed assets only ⇒ no domain-wide subdomain enum"); fresh-
  surface prioritization driven by disclosed shapes; the fresh asset must be Tier A by default.

### Stage 4 — Product walkthrough + behaviour model
- **Gate:** each focus feature has been used through a real UI session; docs read; intended behaviour
  recorded; UI/API seam noted. **No class probe may fire on an element still without a baseline.**
- **Artifact:** `behavior-model.md` (per-feature intended behaviour + doc URL, UI actions, observable
  states the API skips) + `coverage-map.jsonl` rows at `observed`.
- **Existing:** `attack-loop.md` "Use the product like a user" / "Baseline first".
- **Missing:** the prompt/artifact; a transport guidance note that UI-seam bugs require the UI path.

### Stage 5 — Focus-feature selection
- **Gate:** ≥1 and ≤3 focus features chosen from the disclosed shapes; explicitly stated in `plan.md`.
- **Artifact:** `plan.md` §Focus, and a `focus_feature` field on every `coverage-map` row.
- **Existing:** `attack-loop.md` "Own one feature".
- **Missing:** schema field + plan section; nothing links disclosed shape → chosen feature → coverage.

### Stage 6 — Seed the data model
- **Gate:** ≥1 object exists for every crown-jewel type; lifecycle exercised (create → read-as-other →
  update → delete).
- **Artifact:** seed log; `coverage-map` rows carry `seeded: true/false`.
- **Existing:** L-8 rule.
- **Missing:** `prompts/seed-data.md` or `tools/seed.py`; `seeded` field.

### Stage 7 — Feature-driven hunt loop
- **Gate (crown-jewel):** no new enumeration slice while any crown-jewel endpoint is `observed`.
- **Artifact:** `log.jsonl`, `coverage-map.jsonl` updated **at test time**; `findings.jsonl`
  candidates.
- **Existing:** `prompts/attack-loop.md` (strong), `probe.py`, `poc_replay.py`, `burp_mcp.py`.
- **Missing:** coverage rows updated at test time is a rule, not a mechanism; require a
  `coverage-map` write per test (e.g. `probe.py` emits coverage rows).

### Stage 8 — Leads / chain pile
- **Gate:** anomalies appended to `leads.jsonl` **as they are seen**; `open` leads are queued work.
- **Artifact:** `leads.jsonl`.
- **Existing:** `state/leads.example.jsonl`, L-8 rule, attack-loop "Leads backlog".
- **Missing:** enforcement/tooling — a `tools/leads.py` add/close helper; a mid-loop reminder hook.

### Stage 9 — Verification
- **Gate:** boundary-crossing proof with positive + negative controls; marker ≠ proof.
- **Artifact:** `pocs/<F-...>.poc.md`, `findings.jsonl` (`verified: true/false`), `log.jsonl`.
- **Existing:** `prompts/write-poc.md`, `poc_replay.py`, schema. **Adequate.**

### Stage 10 — Coverage reconciliation & closeout
- **Gate:** "exhausted" only if **zero crown-jewel rows at `observed`** and **zero open leads**;
  otherwise emit named gaps.
- **Artifact:** closeout summary; `report.md` coverage statement.
- **Existing:** `attack-loop.md` "Session end".
- **Missing:** `tools/closeout.py` that computes this from the ledgers and refuses a false
  "exhausted"; coverage state vocabulary needs `blocked`; `plan.md` budget consumed.

### Stage 11 — Reporting
- **Gate:** only `verified: true` leaves the ledger; bounty vs pentest branch.
- **Artifact:** `report.md`.
- **Existing:** `prompts/report.md`. **Adequate** (add the non-duplicate rule).

---

## 7. Prioritized, file-level changes

### P0 — make the decision + provisioning stages real (order fix)

1. **`prompts/environment.md` (NEW).** The provisioning stage: derive must-haves from `plan.md`
   focus features; resolve to done / named blocker; produce `environment.md`; hard rule "do not start
   the hunt loop until pass or explicit scoped downgrade". Model it on `targeting.md`'s structure.
2. **`AGENTS.md`.** Replace the step-1b prose bullet with an explicit numbered pipeline (0→10) in
   "Operating contract"; make `plan.md` and `environment.md` required artifacts; state the
   provisioning gate as a hard gate alongside scope and evidence integrity. Add
   `prompts/environment.md` and the pipeline to "Where things live".
3. **`.opencode/skills/offsec/SKILL.md`.** Change routing so `targeting.md` + `environment.md` load on
   "start", "hunt", and "attack" — not only on "find a program". Add a one-line pipeline order to
   step 3.
4. **`prompts/attack-loop.md`.** Move the "Pre-flight provisioning gate" bullet out of the loop into
   Stage 2 and replace it with a pointer to `environment.md`. Make coverage-map updates at test time
   explicit ("every fired test writes/updates its row"), and add a `focus_feature` requirement.
5. **`prompts/targeting.md`.** Add `budget:` and `abandon_when:` to the required `plan.md` output;
   add the explicit `abandoned target` outcome; link disclosed shapes → chosen focus features.

### P1 — enforce coverage, leads, and closeout (mechanism fix)

6. **`tools/closeout.py` (NEW).** Read `coverage-map.jsonl` + `leads.jsonl` + `plan.md`; print
   earnable verdict; exit non-zero and list named gaps if any crown-jewel is `observed` or any lead is
   `open`; print budget consumed. This is the enforcement L-8 lacks.
7. **`state/coverage-map.example.jsonl` + `state/findings.example.jsonl`.** Add `focus_feature` and
   `seeded` fields to coverage; extend `state` vocabulary with `blocked` (and document `exhausted`
   as a closeout verdict, not a row state). Add the UI/API `access_level` note.
8. **`tools/engagement.py`.** Scaffold `plan.md` and `environment.md` templates (not just empty
   ledgers) in `new_target()`; keep `leads.jsonl` (already added). Optional: a `budget` field written
   into `.current` metadata or `plan.md`.
9. **`tools/leads.py` (NEW).** `add` / `list` / `close` helpers so an anomaly is one command from
   capture to resolution; call it from the loop.
10. **`prompts/seed-data.md` (NEW, or fold into environment.md).** Create one object per crown-jewel
    type and exercise the lifecycle before judging authz; the explicit antidote to the `200 []` mirage.
11. **`prompts/behavior-model.md` (NEW).** The product-walkthrough stage (Stage 4): required UI
    actions, docs refs, intended behaviour, UI/API seam — the artifact that makes "own one feature"
    executable.

### P2 — recon precision, transport, reporting

12. **`prompts/recon.md`.** Add a narrow-scope branch: when the policy authorizes only listed assets
    (no wildcard), skip domain-wide subdomain enumeration; make fresh/recent assets Tier A by default;
    verify every discovered path with one handcrafted request *before* it enters the surface map
    (already in `waf.md`, echo here).
13. **`prompts/attack-loop.md` / `prompts/waf.md`.** Transport note: API-key/Burp-REST testing is for
    endpoint coverage; features whose accepted bugs are UI/logic must still be driven through the UI
    to preserve the seam (files-bbp lost it).
14. **`prompts/report.md`.** Encode the HackerOne duplicate rule from `research/hunter-methodology.md`
    §6: same type + same endpoint + same root cause = duplicate; same type on a different endpoint ≠
    duplicate.
15. **`tools/probe.py` (target-local).** Generalise and ship a version that emits `coverage-map.jsonl`
    rows (host, endpoint, class, focus_feature, state, evidence_ref) per test, so coverage is updated
    at test time by construction, and so `probe.py` stops being a class-sweep enabler. (Keep it
    engagement-scoped; don't hard-code a host.)
16. **`LEARNINGS.md`.** After the next engagement, record the pipeline change (L-11) — did forcing
    Stage 1–2 before Stage 3 prevent a mistargeted session?

### Sequencing rationale

P0 changes only prose and routing; they are cheap and fix the order (the files-bbp failure mode: the
decision/provisioning stages ran last or never). P1 adds the mechanisms that make P0 stick (a false
"exhausted" is only impossible if `closeout.py` refuses it, and the empty-collection mirage is only
impossible if seeding is a gate). P2 sharpens recon and reporting but changes no ordering.

---

## Appendix — evidence index

- False close: `targets/files-bbp/log.jsonl` line 56; correction line 57.
- Coverage gap: `targets/files-bbp/coverage-map.jsonl` (126 rows; 114 `observed`, 0 `authed_tested`).
- Retro decision layer: `targets/files-bbp/plan.md` (Gate 1 FAIL, written retroactively).
- Dropped leads: `targets/files-bbp/leads.jsonl` (10 rows, created 17:10).
- Class-sweep bias: `targets/files-bbp/areas/probe.py` batches `info`/`xss`/`idor`/`priv`; log
  08:43–09:16.
- The one feature-depth slice: log 08:53–09:00 (Share-Link control matrix).
- Over-broad recon on a listed-assets-only program: log 07:45 (2734 subdomains).
- UI-seam lost to API key: log 08:36–08:41.
- Tier/tenant blockers discovered late: log 07:38, 09:58.
- Rules that already exist and only need enforcement/wiring: `AGENTS.md` steps 1b/3/4;
  `prompts/attack-loop.md` "Before the loop", "Crown-jewel gate", "Leads backlog", "Session end";
  `prompts/targeting.md`; LEARNINGS L-7/L-8/L-9/L-10.
