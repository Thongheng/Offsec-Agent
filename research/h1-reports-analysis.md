# Where valid bugs live, and how they were actually found
### An evidence-based study of `reddelexc/hackerone-reports`

**Source:** `git clone --depth 1 https://github.com/reddelexc/hackerone-reports` (cloned 2026-09-17)
**Primary data:** `data.csv` — 14,972 disclosed HackerOne reports, columns `program, title, link, upvotes, bounty, vuln_type`.
**Method:** all analysis done locally (Python/csv). HackerOne report *pages* require JavaScript and are not fetchable headlessly, **but `https://hackerone.com/reports/<id>.json` is anonymously readable via `curl`** — I used it to pull 36 report bodies/summaries across classes to verify the discovery step directly. Where I quote a "how it was found" step, it is from that JSON, not inferred from the title. All headline numbers below are computed from `data.csv`; the cross-class sample is 36 reports and is labelled as a sample.

---

## 1. Corpus overview — what this actually is (and its biases)

- **14,972 reports, 428 distinct programs, report IDs 110 → 3,993,973** (essentially the full history of publicly *disclosed* HackerOne reports through the crawl date). 21.5% carry a non-zero bounty field (n=3,216; total recorded $4.9M, median paid $500, max $50,000).
- Organization: a flat `data.csv` (facts), plus generated ranking docs in `docs/` — `tops_100/` (upvoted, paid), `tops_by_bug_type/` (28 hand-tagged classes), `tops_by_program/` (50+ programs). The scripts (`fetcher.py`, `uniquer.py`, `filler.py`, `rater.py`) show the data is **scraped from Hacktivity**, then class-tagged by regex on titles. So `vuln_type` is a *title-keyword tag*, not the reporter's or triager's official weakness — treat it as a lossy label.

**Four biases to hold onto before reading any count:**

1. **Disclosure-weighted, not submission-weighted.** It only contains reports the program *chose to disclose publicly*. Heavy-disclosing programs dominate: Mail.ru (896), U.S. DoD (884), Internet Bug Bounty (794), HackerOne (604), Nextcloud (586), curl (568), Shopify (466). Their bug mixes skew the global mix.
2. **`bounty` is incomplete.** $4.9M recorded vs. HackerOne's publicly stated total is off by ~2 orders of magnitude, so the field is populated only for some rows. Use it for *relative* comparison, never as a true total.
3. **11.3% of rows are untagged** (`vuln_type` blank) and another ~5% land in catch-all tags ("Violation of Secure Design Principles", "Improper Access Control - Generic"). Keyword tags both over- and under-count.
4. **Memory-safety reports are inflated by IBB/curl/Node.js**, and "GraphQL" reports are inflated by HackerOne's own program. Adjust mentally.

---

## 2. Class frequency

### 2a. Exact `vuln_type` tags (top 18 of 212 tags)

| Rank | Tag | n | share |
|---:|---|---:|---:|
| 1 | *(untagged)* | 1,686 | 11.3% |
| 2 | Information Disclosure | 1,439 | 9.6% |
| 3 | XSS – Generic | 984 | 6.6% |
| 4 | Violation of Secure Design Principles | 803 | 5.4% |
| 5 | Improper Authentication – Generic | 779 | 5.2% |
| 6 | Improper Access Control – Generic | 747 | 5.0% |
| 7 | XSS – Reflected | 659 | 4.4% |
| 8 | XSS – Stored | 641 | 4.3% |
| 9 | Uncontrolled Resource Consumption | 511 | 3.4% |
| 10 | CSRF | 511 | 3.4% |
| 11 | Privilege Escalation | 454 | 3.0% |
| 12 | Business Logic Errors | 386 | 2.6% |
| 13 | IDOR | 357 | 2.4% |
| 14 | Open Redirect | 342 | 2.3% |
| 15 | Code Injection | 341 | 2.3% |
| 16 | Memory Corruption – Generic | 319 | 2.1% |
| 17 | SQL Injection | 307 | 2.1% |
| 18 | SSRF | 288 | 1.9% |

XSS in all three variants = **2,284 reports (15.2%)** — the single largest coherent class, but the biggest *payout* classes are elsewhere.

### 2b. Collapsed families (more honest than the 212 tags)

| Family | n | share | % paid | recorded $ |
|---|---:|---:|---:|---:|
| Auth / Access Control (access control, authn, IDOR, privesc, OAuth) | 2,608 | 17.4% | 23% | $940k |
| XSS (all) | 2,481 | 16.6% | 21% | $535k |
| Info / Config / Crypto | 2,197 | 14.7% | 18% | $456k |
| Memory / RCE / Injection (cmdi, code inj, overflows, deser, SQLi) | 2,071 | 13.8% | 28% | **$1.26M** |
| *(untagged)* | 1,686 | 11.3% | 23% | $628k |
| Logic / DoS / Race | 1,325 | 8.8% | 15% | $208k |
| SSRF / File (path traversal, XXE, LFI) | 1,106 | 7.4% | 21% | $384k |
| Redirect / Cache / Smuggling | 618 | 4.1% | 18% | $140k |
| SQLi alone | 309 | 2.1% | 26% | $174k |

**Reading:** volume leader is auth+access-control (17.4%), but **money concentration is in code-execution/memory/injection** ($1.26M on 13.8% of reports, 28% paid rate) and in the access-control family for avg-paid ($2,045/report on Uncontrolled Resource Consumption, avg $4,484 for Command Injection, $3,860 for Request Smuggling, $6,636 for OS Command Injection). Classic XSS is high-volume/low-yield (avg ~$720–1,381, weakest paid rate). **Valid-but-cheap ≠ worthless; but if you optimize expected value, authorization/logic + exec-class beats reflected XSS.**

---

## 3. Discovery-method patterns per top class (core section)

Derived from 36 fetched report bodies (`.json`) plus the curated top-N title lists. For each class: *what the hunter controlled*, *the trigger*, and a cited real report.

### 3.1 Auth / Account Takeover / Improper Authentication (largest family)
**How found:** take a normal auth flow (login, OTP, password reset, email change, social login) and **deviate from the intended value or order** — swap an ID, replay a token, send a duplicated/empty field, or skip a step.
- **Object/ID substitution in an auth call** — `921780` Snapchat: "any user can login as other user with otp/logout & otp/login" — the `/scauth/otp/droid/logout` request carried `user_id`; substituting the victim's ID logs you in as them. Same pattern: `810880` Helium 2FA linking (`/api/2fa/verify` trusted a bare `user_id`, no session binding).
- **Password-reset parameter abuse** — `2293343` GitLab ($35k): submit the reset form, convert body to JSON, and send `"user":{"email":["victim@x","attacker@x"]}` — the server mailed the reset link to *both*, 0-click ATO. `143717` Uber: `/rt/users/passwordless-signup` let you change *any* user's password knowing only a phone number.
- **Response/logic manipulation** — `2831902` Remitly 0-click; `1994227` IBM "response manipulation … register … 0-click ATO".
- **Signature/claim not really checked** — `1760403` Linktree "improper validation of jwt signature"; Mars 0-click via timed forgot-password (single-packet).
**Recurring shape:** single-request anomaly or 2-step deviation; not a scanner finding.

### 3.2 Improper Access Control / IDOR / Broken Object-Level Authz
**How found:** use the feature normally on your own object, then **replace the identifier** (numeric id, UUID, GraphQL global id, or a "copy/move/import" source reference) with another tenant's/user's.
- `415081` PayPal ($10.5k): add secondary users to *other* businesses via `/businessmanage/users/api/v1/users`. `1819832` Snapchat ($15k): `DeleteStorySnaps` mutation took arbitrary post ids. `984965` TikTok: cross-tenant GraphQL `AddRulesToPixelEvents`. `391217` Valve ($20k): `/partnercdkeys/assignkeys/` returned other games' CD keys.
- **The highest-value variant is cross-tenant/import**: `743953`/`767770` GitLab "Steal private objects of other projects via project import"; `981472` Shopify undocumented `fileCopy` GraphQL let a no-permission staffer copy another store's files; `446585` GitLab "Exfiltrate and mutate repository and project data through injected templated service" ($11k).
**Recurring shape:** one request, one changed id; verified by reading another principal's data. Requires **two accounts / two tenants** — provisioning is the gate.

### 3.3 XSS (Stored > Generic > Reflected)
**How found:** inject into a field that is later rendered to *a different user or an internal panel* (blind XSS), often via **markdown/URL-scheme handling** rather than raw `<script>`.
- `526325` GitLab stored XSS: page slug set to `javascript:` + markdown link `[XSS](.alert(1);)` executes on click. `488147` PayPal stored-XSS-via-cache-poisoning; `510152` the follow-up bypass. Blind XSS into internal panels: `805796`/"Blind XSS on image upload" (CS Money), `357`-class reports into support/admin tooling.
**Recurring shape:** needs a *sink the victim views* — stored/blind beats reflected for impact; "self-XSS + clickjacking" chains appear when the sink is the attacker's own session.

### 3.4 SSRF / File-read / Path Traversal
**How found:** find a parameter the server fetches (URL, webhook, import `remote_*`, avatar-from-URL, PDF/screenshot renderer, XML entity) or a filename it concatenates; point it at your Collaborator first, then at metadata/internal.
- `1864188` EXNESS GraphQL `allTicks(source=<url>)`; `341876` Shopify "SSRF in Exchange leads to ROOT access in all instances" (Liquid template → GCP metadata); `885975` Lyft expense-report; `3165242` Lichess game export `players` param → arbitrary URL; `2262382` HackerOne SSRF via Analytics Reports ($25k).
- File-read: `827052` GitLab arbitrary file read via `UploadsRewriter` when moving an issue; `1439593` bulk-imports UploadsPipeline ($29k); `658013` Git **flag injection** via `ref=` in the Search API (`--output=/tmp/file`), escalating overwrite → RCE.
**Recurring shape:** OOB verification (Collaborator) is the discovery tool; the skill is **finding the fetch**, then chaining to metadata/creds.

### 3.5 Business Logic / Race Conditions
**How found:** perform the legitimate action and **repeat it concurrently, or violate an implicit premise** (negative quantity, redeem twice, cancel one of N parallel requests, skip a state).
- `759247` Reverb gift-card race (Turbo Intruder, redeem N times for free money); `3104355` "Race Condition in Folder Creation Allows Bypassing Folder Limit"; `2598548` HackerOne 2FA race; `3020733` Malwarebytes email-verification bypass via two parallel requests; `321` Coinbase "Double Payout via PayPal"; `794064`/"Fee discounts can be redeemed many times" (Stripe); `267` Semrush negative-quantity pricing.
**Recurring shape:** no payload strings at all — it is a *timing/state assertion*; discovery = reading the feature's intended invariant ("one redemption, one payout, ≤N free items") and attacking that invariant. Underweighted by tools; overweighted by payout-per-effort.

### 3.6 CSRF
**How found:** find a state-changing endpoint with weak/absent token validation or no `SameSite`, then chain to ATO.
- `419891` Khan Academy "CSRF on API endpoint allows account takeovers"; `463330` Rockstar linked-account CSRF → ATO; `604120` "Chaining Bugs: Leakage of CSRF token → Stored XSS → ATO". Token-fixation variants: `308394`.
**Recurring shape:** usually *not* accepted alone when it's a trivial settings toggle; accepted as ATO/impact chain.

### 3.7 HTTP Request Smuggling / Web Cache Poisoning/Deception
**How found:** front-end/back-end disagreement (`Content-Length` vs `Transfer-Encoding`, HTTP/2 downgrade) or cache-key mismatch (unkeyed header, `X-Forwarded-Host`, path suffix).
- `737140` Slack "Mass account takeovers using HTTP Request Smuggling on slackb.com to steal session cookies"; `488147`/`622122` PayPal cache poisoning → stored XSS / DoS ($18.9k / $9.7k); `492841` Postmates cache poisoning → user info.
**Recurring shape:** specialist, low-frequency, high-severity; discovery is *deliberate*, tool-assisted, on a specific CDN/proxy.

### 3.8 GraphQL
**How found:** enumerate the schema/mutations and **ask for fields the UI never requests**, or call mutations with another object's global id.
- `489146` "Confidential data of users … accessible via GraphQL" (queried `email`, backup codes, `totp_enabled` directly); `792927` "Email address of any user can be queried on Report Invitation GraphQL type when username is known"; `981472`/`984965` undocumented mutations. Introspection on (`1132803`) is low-value alone.
**Recurring shape:** a *query-shape* attack — the bug is that a field is exposed/resolver lacks authz, not an injection.

### 3.9 SQL Injection / Command Injection / RCE
**How found:** classic param/header injection (`297478` GSA SQLi via **User-Agent**, time-based `868436` Mail.ru city-mobil), plus two modern dominant variants: **argument/flag injection** into shelled-out tools (`658013` Git `ref=`, `403417`/`422944` ImageMagick/Ghostscript on uploads, `777` GitLab git-flag injection) and **supply-chain/misconfig RCE** (`925585` PayPal "RCE via npm misconfig — installing internal libraries from the public registry", $30k; `1679624` GitLab RCE via Github import, $33.5k).
**Recurring shape:** a payload is required, but the *repeatable* wins are file-upload→parser and import/source-control features, not blind `sqlmap` runs.

### 3.10 MFA/2FA bypass
**How found:** submit **empty/blank** code (`897385` Glassdoor "2FA bypass by sending blank code"), **skip enrolment verification** (enable 2FA without verifying email — repeated at Moneybird, XVIDEOS, Cloudflare), **reuse** OTP, leave pre-MFA sessions valid, or race the reset (`2598548`).
**Recurring shape:** tiny logic assertions; extremely repeatable across targets; the *same bug* recurs program after program.

---

## 4. Asset / feature concentration

Across the class titles and the fetched bodies, valid bugs cluster on a small set of feature types:

1. **Auth/identity flows** — login, OTP/SMS, password reset, email-change, magic links, social/OAuth callbacks, SSO/SAML. This is the densest source of Critical/high-impact findings, and where "deviate from intended" pays most.
2. **Object endpoints & REST/GraphQL APIs** — anything with an `id`, `uuid`, `*_id`, or GraphQL node id; cross-tenant and "import/move/copy" operations are the premium variant.
3. **Server-side fetchers** — webhooks, URL importers, screenshot/PDF renderers, link previewers (SSRF/file-read).
4. **File handling** — uploads, avatars, image/PDF processing (ImageMagick/Ghostscript/ExifTool), archive unzip (Zip Slip), S3/Cloudinary keys (RCE + file read).
5. **Payments / loyalty / coupons / gift cards / credits** — race conditions and business-logic value manipulation.
6. **Cache/CDN edge** — cache poisoning/deception, request smuggling (high severity, narrow input surface).
7. **CI/source-control & package registries** — import pipelines, git flags, dependency-confusion (`925585`), which produce the largest single bounties in the corpus.

**Concentration by program:** the top 20 programs by recorded bounty hold most of the money — GitLab ($594k/257), Internet Bug Bounty ($560k/794), Mail.ru ($391k/896), HackerOne ($316k/604), Shopify ($279k/466), GitHub Security Lab ($268k/217), shopify-scripts ($251k/161), Uber ($249k/239), Valve ($154k/82), PlayStation ($122k/20). Only **160 of 428 programs** have ≥1 paid report. **Deep, not wide:** elite output concentrates in a handful of programs with mature features and generous payouts.

**Shape of accepted reports:** the majority are a **single anomaly** (one changed id, one blank field, one duplicated request), but the *highest-scored* and best-remembered ones are **chains**: `2293343` (JSON injection → reset mail → ATO), `791775` ("Email Confirmation Bypass … Leads to Full Privilege Escalation … via SSO", 1917 upvotes), `737140` (smuggling → session theft → mass ATO), `341876` (Liquid → SSRF → GCP metadata → root), `827052` (traversal → file read). Injection-class findings are usually single-request; **authz/logic findings dominate the chain tier.**

---

## 5. Blunt, actionable conclusions

1. **Spend the most time on authorization, not injection.** Auth+access-control is the largest family (17.4%) and owns the highest-impact chains. The repeatable primitive is dead simple: *use the feature, then change the id/tenant and see if the server still obeys.* (IDOR 2.4%, Improper Access Control 5.0%, Privilege Escalation 3.0%.)
2. **The premium move is the "import/move/copy/transfer" operation.** Nearly every top-paid GitLab/Shopify finding is a cross-tenant bug hiding in an import or copy feature (`743953`, `767770`, `446585`, `981472`, `827052`, `1439593`). When you see "import from URL/repo," assume authz is missing on the *source*.
3. **Password-reset / email-change / OTP flows are the highest-yield real estate for a small hunter.** They require no exotic tooling, they chain straight to Critical ATO, and the *same classes recur across programs* — blank-code 2FA bypass, reset-link sent to a second email, unvalidated `redirect_uri`, pre-MFA sessions surviving 2FA. Test these first on every new target.
4. **Race conditions and business-logic value bugs are under-exploited and pay well per unit effort.** `759247`, `321`, `265`, `3104355`, `2598548`. They need Turbo Intruder + a clear statement of the feature's intended invariant ("one redemption," "≤N free items," "one payout"), not a payload.
5. **SSRF/file-read discovery = hunt for the fetch, verify OOB.** Every SSRF report starts with pointing a server-side URL parameter at Burp Collaborator (`1864188`, `341876`, `3165242`). If an asset renders a URL/image/PDF, or imports from a URL, that's your first test.
6. **Treat GraphQL as a query-shape/authz problem, not a schema problem.** Introspection alone is noise (`1132803`); the money is asking for fields/mutations the UI doesn't use and swapping node ids (`489146`, `792927`, `981472`, `984965`). Enumerate every mutation and check what it trusts.
7. **For exec/RCE, favor parsers and pipelines over blind SQLi.** The reliable modern RCEs are file-upload→ImageMagick/Ghostscript/ExifTool (`403417`, `422944`, `1154542`), git-flag/argument injection (`658013`), and import/dependency-path abuse (`925585`, `1679624`). SQLi still pays but is high-competition and often out-of-scope/low-severity now.
8. **"Finding" looks like a boundary you crossed with a second identity, demonstrated.** The accepted-report shape is: a concrete request, a value you controlled differently, and a response proving you read/wrote/executed something you shouldn't have. A reflected marker or a `200` is not a finding — you need the boundary crossing (see rules 2–4 in `AGENTS.md`).
9. **Go deep on few programs.** 428 programs disclose, but 160 pay and ~20 pay most of the money; a mature program like GitLab/Shopify/HackerOne rewards learning one codebase deeply (undocumented mutations, import internals) far more than shallow scans of many targets.
10. **Do not chase reflected XSS or info-disclosure noise for bounty.** They are the volume leaders (XSS 16.6%, Info Disclosure 9.6%) but the weakest payers (~$720–1,381 avg paid, ~18–21% paid rate). Unless it chains to ATO or account data, it's a low-value use of a session.

---

## 6. Skepticism & limits of this data

- **`vuln_type` is regex-derived from titles** (per `rater.py`), so per-class counts are approximations; several classes overlap and 11.3% are untagged. Treat shares as ±, not exact.
- **`bounty` is incomplete** (only 21.5% of rows, $4.9M total), so "money" rankings are directional. The top-paid insights are corroborated by the curated `TOP100PAID.md`, not by the raw sum alone.
- **The corpus is disclosure-biased**, so it measures *what gets disclosed*, which over-represents programs with permissive disclosure (Mail.ru, DoD, IBB, curl, Nextcloud) and mature programs (GitLab, Shopify, HackerOne). It is **not** a random sample of all submissions and cannot support claims like "x% of all bugs are X."
- **The cross-class discovery-method sample is n=36.** Patterns are strongly consistent across the curated top-N lists and the fetched bodies, but per-class discovery-step claims are qualitative, not statistically estimated.
- **No severity field in `data.csv`**, so "critical/high" statements rely on the `.json` sample and the curated lists.
- HackerOne report HTML pages are JS-gated and were not fetchable; the anonymous `.json` endpoint was used instead. Any title-only inference in this document is marked as such.
