# Reference — WAF-protected targets

Load when requests return block pages, challenges, or 403s that don't correlate with
payload content — or before testing a known WAF-fronted target.

## Step 0 — one differential probe
Benign `GET /` vs an obviously malicious payload side by side:
- both blocked → **bot management** (TLS/HTTP2 fingerprint): escalate the client (Step 1).
- benign passes, payload blocked → **signature detection**: mutate the payload (Step 2).
- neither → no WAF in front; test normally.

## Step 1 — bot management: escalate the CLIENT
1. **`curl_cffi`** — `from curl_cffi import requests; requests.get(url, impersonate="chrome124")`.
   Chrome-accurate TLS (JA3/JA4) + HTTP/2 fingerprint from the CLI. Pin a versioned preset.
2. **Browser bootstrap** — pass the challenge once, export cookies + exact UA, then replay via
   the transport. Watch for IP-bound tickets; keep the same IP.
3. **Full browser automation** — last resort, only for JS-computed params.

## Step 2 — signature detection: mutate the payload
1. Fingerprint the engine (headers/cookies already in the surface feed; wafw00f only if ambiguous).
2. Order: **obfuscation** (case, `/**/`, encoding chains, backend syntax variants) →
   **parsing discrepancies** (JSON vs form WAF view, parameter pollution, malformed chunked) →
   **structural** (CDN cache-key). Request smuggling is largely patched at the edge and often
   N/A'd — only with a specific desync reason. Origin-IP access is a LAST resort and usually out
   of scope (hostname scopes; programs prohibit it) — confirm policy first.
3. **Verification gate**: a bypass is real only when the **backend confirms execution**
   (differential / time delay / OOB callback) while the WAF did not block. A WAF-served cache
   page returning 200 is not a bypass.

## WAF-aware active scanning
1. **Pre-flight (passive)**: identify the WAF from headers already captured — zero extra
   requests. A host fronting a third-party SaaS (Statuspage `*.stspg-customer.com`, Webflow,
   Mintlify) is a vendor host, not the program's code — log it, do not fuzz it.
2. Route through Burp if you want visibility; `-ac` auto-calibrate; match on status+size, never
   status alone.
3. **Rate is the control**: `ffuf -rate <roe.max_requests_per_second>`. Threads ≠ RPS. One scan
   at a time. Start small, escalate only if clean.
4. Stop conditions: a 429 means slow down; a sustained sweep of 429/403/challenge pages → abort,
   log, cool down. Passive discovery (JS extraction, wayback/gau) is always WAF-safe — prefer it.
5. Verify every discovery with one handcrafted request before it joins the surface.
