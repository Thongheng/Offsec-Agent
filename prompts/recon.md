# Prompt: Recon / attack-surface inventory

Load this when the target is live (bug bounty or pentest) and you need an attack-surface
inventory. Its output feeds the attack loop (`prompts/attack-loop.md`) as prioritized attack
targets.

First read `state/scope.yaml` → `recon.enum_output_dir` and `reporting.engagement_type`, then
take the matching branch. **Everything you touch must be inside `in_scope` — the scope gate is
enforced in code; if a command is blocked, report it and move on, never work around it.**
Before enumerating a bug-bounty target, confirm the H1 scope was audited and encoded
(`AGENTS.md` → "H1 scope audit"). Live/browsed ≠ eligible: recon routinely surfaces hosts
that are explicitly `out` (they override a wildcard) — drop them from the inventory.

## Branch A — bug bounty (broad surface)

**Scope-shape first.** Read the policy's scope form before enumerating:
- **Listed-assets-only / narrow scope** (no wildcard, e.g. "only these hosts, and only your own
  trial"): do **not** run domain-wide subdomain enumeration — it discovers hosts you are not
  authorized to test and burns RoE budget for nothing (files-bbp ran `subfinder -d files.com` →
  2734 unauthorized customer subdomains on a listed-assets program). Enumerate only the listed
  hosts.
- **Fresh/under-tested assets are Tier A by default.** A host or feature added recently (scope
  diff, changelog, "new" marker) with few or no prior reports is the highest-yield surface — put
  it at the front even if it looks uninteresting.

If `recon.enum_output_dir` points at a completed recon run (your Enum tool layout), consume it
instead of re-enumerating — the human already spent that time:

1. Read `live_web_clean.jsonl` — each line: `{url, host, title, final_url, ...}` — this is the
   deduplicated live-host inventory.
2. Read `subfinder.txt` for the full subdomain set (compare against live hosts: which
   subdomains exist but are dead? — those are potential takeover material, note them as a
   area candidate).
3. The Enum gallery is the HUMAN's visual triage layer — never re-describe every host.
   Every JSONL row carries `screenshot_path_rel` (browser screenshot of that host) and
   `duplicate_content_of` / `browser_redirect_duplicate_of` (clone groups). When proposing
   Tier A hosts, cite the screenshot path so the human can see what you saw. Offer to start
   the viewer for them: `python3 <enum_dir>/subdomain_recon.py serve <enum_output_dir>`
   (serves gallery.html on http://localhost:7171) — the human eyeballs screenshots while
   you work the metadata.
4. **Tier the hosts — never deep-dive during triage.** Work ONLY from the JSONL metadata
   (host, title, status, content group) — the whole 100-host file is a few thousand tokens,
   which is the point: the LLM triages fingerprints, never the pile.
   - **Tier A (propose as attack targets):** login/auth portals, API hosts, admin panels,
     staging/dev/test-named hosts, unusual frameworks, anything non-standard.
   - **Tier B (uncertain):** ambiguous titles, old-tech signals. ONE cheap benign probe
     (fingerprint GET) each, batched within RoE caps — never a scan.
   - **Tier C (one line each, no probing):** marketing pages, parked domains, redirects,
     hosts fronting a recognized third-party SaaS product (Statuspage, Webflow, Mintlify,
     Zendesk, ... — identify by the CNAME target and Server header), same-content-hash clones
     (your Enum already grouped these). Record the vendor in one line; do not fuzz it — a bug
     there belongs to the vendor and is N/A for the program.
   Tiering is a HYPOTHESIS from metadata — boring titles can hide old apps; that's what
   Tier B probes resolve, not guesses.
5. **Directory search on Tier A hosts ONLY** (custom apps, auth portals, APIs — never
   Tier C marketing/parked/vendor-SaaS, never scanner-banned programs). Pre-flight each host:
   if its CNAME resolves to a known SaaS suffix (e.g. `*.stspg-customer.com`,
   `cdn.webflow.com`, `cname.mintlify.builders`) or its responses carry a third-party product
   banner, skip it and log a recon note — a 7,000-request scan to confirm "vendor product,
   N/A" is pure waste.
   ```
   ffuf -w <SecLists>/Discovery/Web-Content/raft-small-words.txt \
        -u https://<tier-a-host>/FUZZ -x http://127.0.0.1:8080 -ac \
        -rate <roe.max_requests_per_second> -t 10 \
        -e <stack extensions: .php, .json, .bak ...> -o ffuf-<host>.json
   ```
   - WAF identified passively already (headers) → apply `prompts/waf.md` scanning rules:
     rate = RoE cap; a 429 means back off and slow down (not a blanket abort); challenge
     signature = passive-only for that host.
   - Escalate wordlist (raft-large → raft-medium) ONLY if small comes back clean.
   - Extensions from the stack fingerprint (php/java/node), not a fixed list.
   - Volume gate: roe.high_volume_probing applies (ask → propose first).
   - **Filter before feeding forward**: drop 404s, drop WAF-interstitial matches, keep
     200/301/302/401/403 with unique sizes — each kept path joins the attack surface
     (`attack-surface.md` + proxy-history feed) as an attack target.
6. Write the shortlist: Tier A hosts + their discovered paths with one-line rationale
   each, ranked. The human approves/adjusts — that approval is the ONLY manual step.

If there is no enum output, ask the human whether to run their Enum tool first (preferred —
it's their established pipeline) or fall back to a minimal inline pass (subfinder → httpx),
respecting RoE caps.

## Branch B — pentest (narrow scope, usually 1–few URLs)

Skip subdomain enumeration entirely. For each in-scope URL:

1. Crawl/light-fuzz to map the app: endpoints, parameters, auth flows, API surface
   (Burp proxy history is the primary source if wired; else targeted requests within RoE).
2. Fingerprint the stack (framework, auth lib, version banners).
3. Note auth requirements and which areas need test accounts (see `test_accounts`).

## Both branches — output

Write `state/attack-surface.md`: inventory table (host/endpoint → tech → auth → notes),
interesting-material ranking, dead-host/takeover candidates (bounty), and the top question
marks that need the human's business context. Keep it compact — this is input for the threat
model, not a report. Then hand the shortlist to the human and start the attack loop
(`prompts/attack-loop.md`) on the approved targets.
