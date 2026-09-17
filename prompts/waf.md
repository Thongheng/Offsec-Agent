# Prompt: WAF-protected targets

Load this when requests to the target return block pages, challenges, or 403s that don't
correlate with payload content — or before testing a target known to sit behind a WAF.
Everything here is CLI-native; the browser is a session-bootstrap tool, not a testing tool.

## Step 0 — Decide which problem you have (one differential probe)

Send a benign request (`GET /`) and a probe with an obviously malicious payload side by side.

- **Both blocked / both get challenge pages** → Problem 1: bot management (TLS/HTTP2
  fingerprinting). Payload tricks are irrelevant; go to Step 1.
- **Benign passes, payload blocked** → Problem 2: signature/payload detection. Go to Step 2.
- **Neither blocked** → no WAF between you and the origin (or none configured); test normally.

## Step 1 — Bot management: escalate the CLIENT, not the payload

Ladder, cheapest first:

1. **`curl_cffi`** (python: `pip install curl_cffi`, `from curl_cffi import requests;
   requests.get(url, impersonate="chrome124")`) — Chrome-accurate TLS (JA3/JA4) + HTTP/2
   fingerprint from the CLI. Defeats most Cloudflare/Akamai bot layers without a browser.
   Pin a versioned preset (`chrome124`, `safari17_0`, ...) — a bare `"chrome"` is not a
   documented preset and typically raises.
2. **Browser session bootstrap**: open the target once (human's browser or headless
   Playwright), pass the challenge, export cookies + the exact User-Agent, then replay via
   CLI: `python3 tools/poc_replay.py poc.md --var COOKIE=... --var UA=...`. The browser earns
   the ticket; the CLI does the testing. Watch for the ticket being IP-bound — keep testing
   from the same IP.
3. **Full browser automation** — last resort, only for JS-computed params (tokens the page
   derives in the browser) or genuine DOM checks. Slow; never for payload matrices.

## Step 2 — Signature detection: mutate the payload (fingerprint → adapt → verify)

1. **Fingerprint the engine**: wafw00f, blocking-page text, header/cookie tells (cf-ray,
   x-sucuri-id, Akamai cookies). Known engine → try its known bypass classes first.
2. **Technique order**:
   - **Obfuscation** — case mangling, `/**/` comment insertion, whitespace/encoding chains
     (double-URL, unicode, overlong UTF-8), syntax variants for the backend language. Usually
     the cheapest first move and the most likely to work on modern WAFs.
   - **Parsing discrepancies** — make the WAF and origin disagree about where the payload is:
     JSON content-type abuse (form-encoded WAF view vs JSON backend parse), HTTP parameter
     pollution, malformed chunked encoding. (Request smuggling (TE.CL/CL.TE) is largely
     patched at CDN edges now and often N/A'd by triage — try it only when you have a specific
     reason to expect a desync, not as a default.)
   - **Structural** — CDN cache-key behavior. Origin-IP discovery is a LAST resort and often
     OUT OF SCOPE: scope is usually hostname-based, and many programs prohibit direct-origin
     access. Confirm the policy allows it before touching an origin IP.
3. **Verification gate (non-negotiable)**: a bypass is real only when the **backend confirms
   execution** — differential response, time-based delay, or OOB callback — *while the WAF
   didn't block*. A 200 from a WAF-served cache page is not a bypass. Log both sides of the
   differential as evidence (`log.jsonl` / finding evidence), same marker rules as any PoC.

## WAF-aware active scanning (dir fuzz, param mining)

Fuzzing a WAF-fronted target naively = banned IP + garbage results (every probe returns the
WAF interstitial with 200, "discovering" nothing). Rules:

1. **Pre-flight (always, PASSIVE)**: identify the WAF from headers already in
   `proxy-history.jsonl` — zero extra requests: `Server: cloudflare`/`CF-Ray`/`cf-*`
   (Cloudflare), `__cf_bm` cookie (CF Bot Management), `X-Akamai-*`/`dtCookie` (Akamai),
   `x-sucuri-id`, etc. Only if headers are ambiguous AND the decision matters, use wafw00f.
   Re-check `roe.notes` for scanner bans → banned program skips ffuf entirely (handcrafted
   low-volume paths or passive discovery only).
2. **Route through Burp**: `ffuf -x http://127.0.0.1:8080 ...` — traffic inherits Burp's
   TLS/HTTP stack, lands in proxy history (you SEE blocks immediately), and respects
   Burp's upstream-proxy config if one is set.
3. **Calibrate or get poisoned**: `-ac` (auto-calibration) so default/WAF responses are
   filtered; match on status+size signatures, never status alone.
4. **RATE IS THE CONTROL**: `-rate` must never exceed the engagement's RoE cap —
   `ffuf -rate <roe.max_requests_per_second>` (read it from scope.yaml; default 5).
   Threads ≠ RPS — never tune by threads. One active scan at a time. Start small
   (raft-small), escalate wordlist size only if clean.
5. **Stop conditions**: a 429 means SLOW DOWN, not stop — back off (and reduce rate), then
   continue; a sustained sweep of 429s, a sweep of 403s, or the challenge-page signature in
   results → abort, log the block in log.jsonl, cool down ≥10 min, then handcrafted probes
   or passive-only for that host. (Some APIs 429 routinely under normal load — judge by the
   pattern, not a single response.)
6. **Verify discoveries by replay**: every "found" path is confirmed with ONE handcrafted
   request before it joins the attack surface — a WAF interstitial is not a directory.
7. Passive discovery (JS endpoint extraction from proxy history, wayback/gau) touches no
   target and is always WAF-safe — prefer it first on bot-managed hosts.

## Notes

- Respect `roe.high_volume_probing`: WAF adaptation means many requests; matrices >20 go
  through the gate. Benign-vs-payload differentials (2 requests) are always fine.
- Keep per-request mutations in the PoC bundle as raw HTTP — the whole ladder replays.
- If every request from every client is blocked and the program RoE allows it, ask the human
  about allowed testing windows / whitelisting before giving up.
