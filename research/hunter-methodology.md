# How Successful Bug-Bounty Hunters Actually Find Bugs

Research synthesis, compiled 2026-09-17. Sources are primary where possible (hunter talks/blogs,
platform docs, academic surveys). Each claim is tagged:

- **[data]** — from platform documentation or a study/survey
- **[consensus]** — repeated independently by several named practitioners
- **[opinion]** — one practitioner's view, or an SEO/listicle-grade source; treat as hypothesis

**Headline honesty note up front.** There is no public dataset that measures *why one hunter finds
on a program and another does not*. Every "top hunters spend X% on recon" number below is
self-reported or anecdotal, and the numbers contradict each other. This document separates what is
verifiable (platform mechanics, triage states, VRT) from what is craft lore. The craft lore is still
useful — it is just not evidence.

---

## 0. Sources

Primary / high-confidence:

1. Jason Haddix — *The Bug Hunter's Methodology v4.01: Recon Edition* (NahamCon 2020) — https://www.youtube.com/watch?v=p4JgIu1mceI · notes: https://www.trickster.dev/post/notes-on-tbhm-v4-recon-edition/
2. Jason Haddix — *Recon Like an Adversary* (IWCON 2023) — https://www.youtube.com/watch?v=nGs8pWIj5k4
3. Bugcrowd (Andrew Pratt) — *Why you aren't finding bugs* (2024) — https://www.bugcrowd.com/blog/why-you-arent-finding-bugs/
4. Bugcrowd — *Vulnerability Rating Taxonomy (VRT)* — https://github.com/bugcrowd/vulnerability-rating-taxonomy · https://bugcrowd.com/vulnerability-rating-taxonomy/1.5
5. Frans Rosén — *Live Hacking like a MVH* — https://speakerdeck.com/fransrosen/live-hacking-like-a-mvh-a-walkthrough-on-methodology-and-strategies-to-win-big
6. Frans Rosén — *A methodology using fuzzing and info disclosure* — https://speakerdeck.com/fransrosen/a-methodology-using-fuzzing-and-info-disclosure
7. Frans Rosén — AMA — https://bugbountyforum.com/blog/ama/fransrosen/
8. Ben Sadeghipour (NahamSec) — AMA — https://bugbountyforum.com/blog/ama/nahamsec/
9. NahamSec — *500k/yr as Full-Time Bug Hunter* (Critical Thinking Ep. 53) — https://www.criticalthinkingpodcast.io/500kyr-as-full-time-bug-hunter-content-creator-nahamsec/
10. Sam Curry (zlz) — HackerOne Hacker Spotlight — https://www.hackerone.com/blog/hacker-spotlight-interview-zlz
11. Sam Curry — *We Hacked Apple for 3 Months* — https://samcurry.net/hacking-apple
12. Sam Curry — *Don't Force Yourself to Become a Bug Bounty Hunter* — https://samcurry.net/dont-force-yourself-to-become-a-bug-bounty-hunter/
13. *Motivation and Methodology with Sam Curry* (Critical Thinking Ep. 65) — https://blog.criticalthinkingpodcast.io/p/motivation-and-methodology-with-sam-curry
14. HackerOne — *Quality Reports* — https://docs.hackerone.com/en/articles/8475116-quality-reports
15. HackerOne — *The View from the Other Side: A Security Analyst's Perspective on Triage* — https://www.hackerone.com/blog/view-other-side-security-analysts-perspective-bug-bounty-triage
16. HackerOne — *There and Hack Again: A Triager's View on Quality Reports* — https://h1.community/blog/there-amp-hack-again-a-triagers-view-on-quality-reports/
17. HackerOne — *Report States* — https://docs.hackerone.com/en/articles/8475030-report-states
18. HackerOne — *Agentic Duplicate Detection* — https://docs.hackerone.com/en/articles/13703106-agentic-duplicate-detection
19. HackerOne — *Bug Bounty Reports: How Do They Work?* — https://www.hackerone.com/blog/bug-bounty-reports-how-do-they-work
20. Intigriti — *Bug Bounty Starter Kit* — https://www.intigriti.com/bug-bounty-starter-kit · PDF: https://www.intigriti.com/resources/1781605282-bug-bounty-starter-kit.pdf
21. Intigriti — *7 Tips for bug bounty beginners* (2024) — https://www.intigriti.com/researchers/blog/hacking-tools/7-tips-for-bug-bounty-beginners
22. Intigriti — *How to write and submit a good report* — https://kb.intigriti.com/en/articles/5379086-how-to-write-and-submit-a-good-report
23. Akgül et al. — *The Hackers' Viewpoint* (USENIX/WSIW 2020) — https://www2.cs.uh.edu/~gnawali/papers/bugbounty-wsiw20.pdf · extended: arXiv 2301.04781
24. Intigriti — *Ethical Hacker Insights Report 2024* — PDF: https://www.intigriti.com/resources/1781187234-intigriti-ethical-hacker-insights-report-2024.pdf
25. OWASP — *WSTG: Business Logic Testing* — https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/00-Introduction_to_Business_Logic
26. Bittau et al. — *Hacking Blind* (IEEE S&P 2014, BROP) — http://www.scs.stanford.edu/brop/bittau-brop.pdf
27. The Bug Bounty Playbook — https://bugbounty.info/ (Methodology / Time-Boxing / Report Writing)
28. Krishna Kumar (xalgord) — *Why You Are Failing at Bug Bounty Hunting* — https://xalgord.medium.com/why-you-are-failing-at-bug-bounty-hunting-and-the-blueprint-to-fix-it-e5a904ae63fa

Use lower-confidence / label-[opinion] sources: R.H. Rizvi, "coverage problem" Medium post; GraySentinel Medium; securityelites.com; nhimg.org / securityboulevard multi-user DAST pieces (these are vendor marketing with a few real citations).

---

## 1. The methodology consensus

Across Haddix, Rosén, NahamSec, Curry, Bugcrowd and Intigriti, the same skeleton appears:

1. **Read the scope and RoE twice.** Intigriti's starter kit calls reading scope "the difference
   between a new payout and a rejected report"; HackerOne's own report guide says the #1 avoidable
   failure is spending a week on out-of-scope assets. [20][19][consensus]
2. **Recon / attack-surface discovery.** Haddix's recon edition is explicitly breadth-first:
   assets → subdomains → live hosts → ports → tech fingerprint → content/param discovery, with ASN
   and certificate-transparency work as the seed. He warns *not* to automate the ASN step and to
   run recon in two phases (the "lossy" tools while you are already testing). [1][2]
3. **Map the application and understand intended behavior before payloads.** NahamSec: "I like to
   first understand the purpose of the app and how things work... use the app as a regular user."
   Bugcrowd: know the app "more than some of the developers do." [8][3]
4. **Enumerate parameters and endpoints from JS and history, not just brute force.** Rosén: extract
   API endpoints from JS, build *context-specific* wordlists per program, then "fuzz, fuzz, fuzz" —
   all HTTP methods, with/without IDs, with/without trailing slash, with/without extensions.
   NahamSec automates JS recon so he doesn't read "hundreds of lines of messy JS." [6][8]
5. **Test, verify, and only then report.** Plane of what *should* happen vs what happens; prove the
   boundary; write it up. [consensus]

Rosén's "secondary context" insight (via Curry) is the most concrete advanced pattern in this
corpus: same-origin `/api` routes that proxy to an internal service, where user input is smuggled
into the backend request. It explains a large class of modern bugs (path traversal / SSRF / auth
bypass through a proxy) and is found by fuzzing what the *front* does when you feed it `"`, `%00`,
`#`, `..`. [13]

**What "hacking blind" means here — a correction.** The canonical *Hacking Blind* paper (Bittau et
al., 2014) is **Blind ROP**: building a memory-corruption exploit with no copy of the target binary
by using crash/no-crash as a 1-bit oracle. It is a legitimate, cited methodology and the "crash/no
crash oracle" idea generalizes — but it is *binary exploitation*, not web bug bounty. [26] For web,
"blind" usually means either (a) black-box testing with no source, or (b) the second-account
differential test below. Nobody in the practitioner corpus uses "hacking blind" to mean a web
methodology; do not let the name mislead you.

---

## 2. Recon vs testing ratio — what the numbers actually say

There is **no authoritative ratio**. The self-reported figures disagree, which is itself the
finding:

| Source | Recon/OSINT | Testing/analysis | Reporting |
|---|---|---|---|
| bugbounty.info "Time-Boxed Hunting" [27] | 20–30% | 40–50% asset investigation + 20–30% deep dive | 10–15% |
| Chintan Gurjar case study [opinion] | 30% OSINT+recon, 20% surface mapping | 30% hypothesis testing + 15% chaining | 5% |
| Practitioner post "how I cut recon 70%" [opinion] | ~80% (before) → 90 min boxed | 30–60 min → 2–3 h | — |
| AI-co-pilot architecture posts [opinion] | calls it "the tedious 80%" | "the 20% that matters" | — |

Read the table as a *distribution of beliefs*, not data. What is consistent:

- **Recon is a means, not the job.** Every serious source warns that endless enumeration is a
  procrastination trap. The "recon-only loop" — collect, then think "there might be more", collect
  again, test nothing — is named explicitly. [3][27][opinion]
- **Read the output, don't just generate it.** Multiple sources converge on the idea that the
  bottleneck is *surface analysis* (reading JS, headers, error messages, CSP, sitemaps to form
  hypotheses), not more enumeration sources. [opinion, but repeated]
- **Time-boxing is the common fix.** bugbounty.info publishes a phase allocation table precisely
  because hunters default to spending 80% on recon. [27]
- **Automation runs in the background while you test manually.** Haddix runs "phase two" lossy recon
  *while* he is already pentesting a live host. NahamSec: automate recon and alert to Discord, then
  spend your time on manual work. [2][9]

**On JS/parameter mining specifically:** this is where the practitioner consensus is strongest and
most actionable. Rosén's entire Bsides talk is about locating APIs/microservices, extracting every
endpoint from JS, adding "other strings" and building per-program wordlists. [6] The Apple
engagement is the same pattern at scale: enumerate ~10,000 hosts under `apple.com` plus 17.0.0.0/8,
fingerprint, directory-brute-force the interesting ones, then go deep. [11]

**Business-logic understanding** is treated as the highest-leverage "recon" of all because it
cannot be scanned. OWASP WSTG says logic flaws "rely upon the skills and creativity of the
penetration tester," are "usually one of the hardest to detect," and are "usually one of the most
detrimental." Bugcrowd: complexity of user-submitted data handling is "your best bet." [25][3]

---

## 3. Behavioral differences that separate finders from non-finders

These are the recurring structural/behavioral differences in the corpus. None is proven causal, but
they are stated independently by people with large track records.

1. **Target choice and level-matching.** Beginners pick hardened, high-profile programs (Uber,
   PayPal) and find nothing. The recommended path is a *fresh or neglected surface*: new programs,
   recently expanded scope, acquisitions, VDPs (no payout → less competition). [28][20]
   Rosén's program-lifecycle model is the sharpest: (a) right at launch = lots of simultaneous
   hunters and dupes, you must be fast or thorough; (b) mature = minefield of dupes or hard;
   (c) 6–18 months in = attention has moved on but the company keeps shipping code, so there is a
   lot nobody has looked at. He deliberately revisits old programs. [7]
   Curry: picks based on what has paid historically and what the scope page calls high-impact. [10]

2. **Depth vs breadth is a false dichotomy — the real variable is *untested surface*.** Curry
   works **one program at a time** because he "loves digging deep." [10] NahamSec's own post-mortem
   of his best years: it was "just niching down in one single program," being first to an asset or
   functionality — including assets everyone knew about but nobody had actually tested. [9]
   Bugcrowd and Intigriti both say stay on a target for *weeks to a month* before switching, and
   warn that subdomain-hopping is the same mistake. [3][21] The consensus is: depth on a chosen
   target, but route that depth into *fresh* surface.

3. **Actually using the product.** NahamSec starts by using the app as a normal user to learn
   purpose and functionality. Bugcrowd describes knowing the app better than the developers — spot
   a feature flag, wait for it to go live, be first to test it; read the changelog; note a new
   permission role and immediately try the privilege-escalation pattern that worked on the last
   role. Iron Software's program literally instructs hunters to start a trial. [8][3]

4. **Notes, leads, and a "second pile."** Rosén: a directory per target with a text file always
   open; comments/snippets/URLs; keep **valid vulns separate from "interesting behaviour"** because
   the latter is what you chain later. Burp history is "golden — save it, search it." Curry's
   podcast segment on "mindmaps, note-taking and intuition" is the same idea. [5][13]
   This is a genuine differentiator: non-finders test and forget. Finders keep a backlog of
   anomalies that combine into a critical later.

5. **Following anomalies instead of confirming a payload.** NahamSec: put one polyglot in each
   field and "over-analyze the shit out of it" before moving on. Rosén: mark requests that "respond
   funky" and revisit later. The trigger for depth is unexpected behavior, not a scanner hit. [9][7]

6. **Chaining and second-order thinking.** Recurring theme: a medium plus a medium becomes a
   critical. xalgord's canonical example: open redirect alone = $0, open redirect → OAuth token
   theft → account takeover = thousands. [28] The playbook states it as a rule: "every time you
   find something, ask what it lets you reach next." [27]

7. **Pattern recognition / "gut feeling."** NahamSec: "99% of bug bounty is pattern recognition —
   you identify a pattern of mistakes with a particular company and exploit the shit out of it."
   Curry's ISP/Tesla work came from recognizing the same architectural anti-pattern across targets.
   [9][13] This is built by reps, which is why VDPs and smaller programs are recommended as
   training. [28]

8. **Persistence framed as enjoyment, not discipline.** Curry's essay is blunt: nearly every
   successful hunter he knows loves the work; forcing yourself through a routine you hate does not
   produce the reps. Every "consistency" tip from Intigriti/Bugcrowd is the softer version of this.
   [12][3][21]

9. **Collaboration.** Apple was a 5-person team. NahamSec credits working with friends for seeing
   how others approach the same program. Bugcrowd names community/meetups as a differentiator.
   [11][8][3]

10. **Willingness to submit — and to accept the answer.** Intigriti: self-doubt causes people to sit
    on valid findings (which also raises dupe risk). [21] Conversely, triagers describe arguments
    over severity and repeated submissions as "poor form." [15]

---

## 4. The role of accounts / access

This is the difference between "I can read the docs" and "I can test the thing." Strongest concrete
evidence:

- **Two-account differential testing is the only reliable way to find broken access control.**
  BOLA/BFLA is OWASP API #1, and multi-user DAST vendors and QA guides all say a single-session
  scanner structurally cannot prove object-level authorization — you need two identities and the
  same request replayed as the wrong principal, checking for denial *and no leakage*. [opinion
  sources, but the mechanism is uncontroversial and matches OWASP]
- **HackerOne recorded on average >6 multi-user vulnerability reports per month in 2024**, and high
  payouts correlate with permission bypass / privilege escalation. (Vendor-cited figure; treat the
  exact number with caution, but the direction is consistent with BOLA being the top API risk.)
- **Multi-role testing finds bugs that are effectively invisible otherwise.** A documented
  (redacted) assessment weighted ~75–80% of effort to authorization logic with 3 credentialed roles
  and found a critical cross-tenant object access plus a critical BFLA. GuidePoint's case: a
  customer-level account could reach an employee endpoint only because they tested multiple roles.
- **Enterprise/paid access matters a lot.** Rosén's Live Hacking talk lists "Enterprise access to
  products" as a hallmark of events, and says to confirm "upgrades to enterprise accounts if
  promised" during scoping. His $20k bug came from trying all 80 integrations and reading how each
  worked — high-effort, high-threshold testing on functionality most hunters skip. [5]
- **The provider-tenant boundary is where the money is.** In multi-tenant SaaS a valid account is
  often all you need; the failure is not auth bypass but *tenant-context propagation* after auth
  (cache keys missing `tenant_id`, exports losing tenant context, search indexes not partitioned).

**Honest caveat:** there is little *quantitative* evidence linking "hunters who have enterprise
access" to "hunters who find more." The best evidence is architectural (authorization bugs require
multiple identities to demonstrate) and anecdotal (Rosén/Curry event scopes). Provisioning paid
tiers and a second tenant is therefore a **go/no-go gate for anything authorization-shaped**, not a
generic productivity booster. If the scope promises enterprise upgrades and does not deliver them,
the authorization surface is unreachable — treat that as blocked, not as a reason to keep poking the
public pages.

---

## 5. Named failure modes

| Failure mode | Who names it | Core point |
|---|---|---|
| **Scanning instead of thinking** | Bugcrowd [3], Intigriti [20], xalgord [28], XSS Rat (quoted) | Running the same default tools as 50k others → dupes/informational. "Fingerprint before you scan." |
| **Recon-only loop / burnout** | Bugcrowd [3], NahamSec [9], bugbounty.info [27] | Collecting data feels productive; it is not. NahamSec: "when you're doing these no-vulnerability practices every week, what you practice is what becomes your reality." |
| **Chasing severity / ignoring impact** | xalgord [28], HackerOne [15][16], playbook [27] | Reporting missing headers, internal IPs, version banners, non-sensitive keys. "Stop reporting the presence of a vulnerability; report the consequence." |
| **Not reading docs / not reading scope** | HackerOne [19], Intigriti [20], Bugcrowd VRT [4] | A week on out-of-scope assets. Logic bugs require a model of intended behavior built from docs. |
| **Not using the app** | NahamSec [8], Bugcrowd [3] | If you don't understand the workflow you cannot break it; scanners cannot find logic flaws. |
| **Giving up too early** | Bugcrowd [3], Intigriti [21] | Bugcrowd: 3 days is not enough; Intigriti: stay on a target weeks–a month. |
| **Giving up too late / sunk cost** | Rosén [7], NahamSec [9] | The opposite error: "when do you give up? when do you stop?" Rosén's program-lifecycle model is the decision aid. NahamSec automated and moved on when a lane stopped producing. |
| **Duplicates / racing the crowd** | HackerOne [18], Rizvi [opinion] | Launch-week programs and "fresh feature" announcements draw everyone. HackerOne's own model now uses semantic + technical fingerprinting to call a dupe. Practical mitigation: be first, or be deeper, or pick the neglected stage of a program's life. |
| **Tutorial black hole** | Bugcrowd [3], Intigriti [20] | Lab reps ≠ real-app complexity; the fix is an explicit, sliding learning:hunting ratio (start 70/30, reduce 10% every 2–3 months). |
| **Automation before fundamentals** | Bugcrowd [3], NahamSec [via Phillip Wylie interview], xalgord [28] | "Automation should come after mastering manual exploitation." You cannot automate what you don't understand. |
| **Self-doubt / not submitting** | Intigriti [21] | Valid findings sitting in a notebook. |

Two failures deserve special emphasis because they are the ones top hunters explicitly invert:

- **Dupe you treat as failure vs signal.** A duplicate proves your recon located real attack
  surface and your severity read was roughly right — the missed variable was timing. The productive
  response is "find the adjacent instance," not "move to a harder target." [opinion, but sound]
- **Not writing things down.** The most repeated operational habit in the corpus is note-keeping and
  a separate leads pile. It is boring and it is what enables chaining.

---

## 6. What makes a report valid/accepted vs closed

From triager-facing material (HackerOne docs/blogs, Intigriti KB, Bugcrowd VRT):

**The triage funnel.** On a managed program, reports are first validated and sorted into
Informative / Duplicate / Not Applicable; only valid ones go to the customer team. [15] Closed
states on HackerOne: **Resolved** (valid, fixed — reputation +2 for the original), **Informative**
(valid info, no action — 0), **Not Applicable** (out of scope / excluded / known — −5), **Duplicate**
(already reported or same root cause; can be added to the original). A triaged bug can *still* be
closed Informative/Duplicate after further review. [17]

**Acceptance criteria — the three things every good report must cover:** reproduction steps,
exploitability, and impact. [19] Triagers add: select the correct asset (avoids out-of-scope), a
succinct summary up front, exact URLs and parameters, account state/role required, and the CVSS
reasoning. [14][16]

**Concrete triager asks:**
- Numbered repro steps an outsider can follow; if they can't reproduce in ~10 minutes, it gets
  deferred. Exact URLs, not "go to settings"; exact payloads; one action per step. [14][16][27]
- Text URLs, not screenshots of URLs, so they can copy-paste and dupe-check. [15]
- A working PoC in the target's intended configuration; never unverified or AI-generated payloads.
  [20]
- **Impact in business terms.** HackerOne: think from the security team's shoes — healthcare →
  patient data; PCI → card data. Don't inflate; that sours the relationship. [19]
- Self-assess severity with CVSS before submitting; over-rating delays triage. [16][20][4]
- No giant unsnipped command output; keep it tidy. [15]
- For setup-heavy bugs (mobile, games, multi-step), a short (<2–3 min) video PoC. [15][27]

**Why valid reports get closed anyway:**
- **Informative/known**: the program already knew, a fix was in the pipeline, or it was an accepted
  risk. Mitigation: keep the PoC so it can be re-evaluated. [17][15]
- **Not Applicable**: asset or vuln class not in scope; excluded classes; the program's VRT scope
  rules may explicitly mark a class out. Read the VRT note on the program. [16][4]
- **Duplicate**: same root cause/extraction. HackerOne's own docs state the distinction that matters:
  *same vulnerability type on a different endpoint is NOT a duplicate* (e.g., SQLi on `/api/users`
  vs `/api/orders`); same type + same target + same method + same root cause = duplicate. Use this
  to argue when you genuinely are not a dupe, and to understand when you are. [18]

**The report is half the work.** The playbook line is the honest summary: "A bad report on a valid
finding gets triaged slowly, downgraded, or ignored... critical bugs get marked informational
because the researcher couldn't explain impact." [27]

---

## 7. Blunt: the 5 things that most determine whether you find a bug

Ordered by how much I believe they move the needle, with the evidence status.

1. **Whether you are on *untested* surface at all.** This subsumes target choice, program
   lifecycle, and fresh-feature timing. A weak hunter on a neglected subdomain/acquisition/new
   feature beats a strong hunter on a hammered login page. Sources: Rosén lifecycle model [7],
   NahamSec "first to an asset or functionality" [9], Bugcrowd "corners" [3], Apple recon [11].
   *(Consensus; the single most repeated claim.)*

2. **Whether you actually understand the product's intended behavior.** Authorization and
   business-logic bugs — the highest-payout classes — cannot be found by pattern-matching payloads.
   You need a model of what the workflow assumes and then violate it. Sources: OWASP WSTG [25],
   Bugcrowd [3], NahamSec [8], every business-logic writeup. *(Consensus; mechanism is solid.)*

3. **Whether you have the access required to reach the bug-bearing surface.** One account cannot
   demonstrate BOLA/BFLA; paid/enterprise tiers and a second tenant are prerequisites, not
   nice-to-haves. Sources: Rosén [5], multi-user DAST/authorization material, HackerOne multi-user
   report volume. *(Strong architectural argument; weak quantitative data on hunter outcomes.)*

4. **Whether you keep a leads pile and chain instead of stopping at the first finding.** The
   medium→critical upgrade is the documented difference between a $200 and a $$$ report. Sources:
   Rosén "interesting behaviour" pile [5], xalgord open-redirect→ATO [28], playbook chain-thinking
   [27], Apple SSRF-to-RCE chains [11]. *(Consensus; anecdotal but frequent and detailed.)*

5. **Whether you generate reps against feedback instead of forcing a routine.** VDPs/small programs
   → pattern recognition → faster anomaly spotting and faster impact judgement. Consistent
   submission and correct scope/impact reading are learned from triage outcomes. Sources: Curry on
   passion [12], xalgord on level-matching [28], Bugcrowd learning:hunting ratio [3], Intigriti on
   persistence [21]. *(Consensus; this is the "why the same program treats hunters differently"
   answer — the finders have more accumulated pattern recognition and lose less time on
   non-issues.)*

**What is *not* in the top five, despite the marketing:** tooling, scanning volume, and recon
automation. Every primary source treats these as table stakes or as a trap. NahamSec, who built a
reputation on recon, states plainly that recon alone "doesn't translate to money" and that his money
came from finding good bugs, not from automation. [9]

---

## 8. What this means for the offsec-agent kit

Direct implications for our own methodology (`AGENTS.md`, `prompts/attack-loop.md`):

1. The **coverage-map + crown-jewel gate** is well-founded: untested surface and access-level
   coverage are the top two factors. Keep enforcing "no new enumeration until the high-impact
   endpoint is tested authed or explicitly skipped."
2. The **`needs_session_B` state** is essential, not optional — it is the operational encoding of
   finding category #3. Provisioning a second account/tenant should be treated as a hard gate before
   authorization-shaped work, as the kit already says.
3. The **leads/observations pile** should be first-class. Consider a `leads.jsonl` alongside
   `findings.jsonl` for "interesting behavior not yet exploitable" — that is how chains get built.
   (Currently `log.jsonl` covers this implicitly; making it explicit matches Rosén's practice.)
4. **Report quality is a finding-multiplier.** The triage sections map cleanly onto
   `prompts/report.md`; the "same type, different endpoint ≠ duplicate" rule and the business-impact
   framing are worth encoding explicitly.
5. The kit's insistence on **validity over severity** aligns with every primary source here.

**Open gap in the literature (honest):** there is no study comparing hunters on the *same* program
that isolates causation. The claim "finders use untested surface" is consistent, widely repeated,
and mechanistically plausible, but it is inference from practitioners, not measured. Our
`LEARNINGS.md` is the right place to test it empirically on our own engagements.
