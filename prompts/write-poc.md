# Prompt: PoC bundle generation

Produce one bundle per verified finding. The bar (from the triage-side literature): **a
triager must reproduce the vulnerability in 5 minutes, without talking to you.** Raw
replayable HTTP — not Python scripts that don't run.

Bundle format (save as `state/pocs/<FINDING-ID>.poc.md`):

    ---
    target: {{HOST}}            # host[:port]; also the scope-check target
    name: <short-slug>
    tls: true                   # if HTTPS
    finding: F-xxx
    ---

    ```http
    POST /api/v1/reset HTTP/1.1
    Host: {{HOST}}
    Content-Type: application/json
    Authorization: Bearer {{VICTIM_TOKEN}}

    {"email":"{{VICTIM_EMAIL}}"}
    ```

Rules:

1. **Placeholders** `{{NAME}}` for everything environment-specific (hosts, tokens, emails).
   `tools/poc_replay.py --var HOST=... --var TOKEN=...` substitutes them. Secrets come from
   the test-account store referenced in `state/scope.yaml` — never inline them.
2. **Minimal request**: the smallest request that demonstrates impact. Drop noise headers.
3. **Harmless by default**: payloads must demonstrate the impact without destroying data
   (read/flag values, not deletes). No exfil to third-party hosts; use the engagement's
   designated callback endpoint if OOB is needed.
4. **Verification — demonstrate the boundary, not just success.** Embed a unique token
   `poc-<finding-id>-<random4>` (e.g. `poc-F-012-k3f9`) in the payload as a **correlation
   token** that ties evidence to this finding. But the marker is not the proof, and a `200`
   is not the proof. The proof is that the **actual security boundary was crossed**,
   reproducibly, with the controls that make the result meaningful:

   - **Positive control** — the legitimate principal can do the thing (proves the object is
     real and the id/request is correct; rules out "denied for everyone").
   - **Negative control** — the attacker principal is denied on the normal path or with a
     non-owned id (proves a boundary exists, so a success is meaningful — *mandatory for any
     access-control finding*).
   - **Data/effect provenance** — the attacker receives data **provably owned by the other
     principal** (their unique value/PII or a planted marker), or the effect lands on their
     resource — not merely an HTTP 200.

   Examples (illustrations of the principle, not a closed list):

   | bug class | evidence that makes `verified: true` legitimate |
   |---|---|
   | reflected XSS / SQLi / open redirect | marker reflected in response body, SQL error, or `Location` header |
   | SSRF / OOB | marker observed in the callback (collab subdomain/param carries the token) |
   | IDOR / BOLA | positive control (owner reads it) + negative control (attacker denied on non-owned id) + attacker receives **victim-owned data** — cross-account vs cross-tenant stated explicitly |
   | privilege escalation / BFLA | low-priv role performs a privileged action or read (state change or privileged data), with the role differential shown |
   | business logic | before/after **state delta** (balance, entitlement, count) with the step omitted/reordered/replayed |
   | race condition | reproducible outcome across N concurrent sends, with the sequential control failing |
   | cache poisoning / deception | poisoned content served to a **second, clean client/session** |

   Store the proof with the ledger entry: `evidence.request` (raw request(s) sent) +
   `evidence.response_excerpt` (the part showing the marker **and** the boundary crossing,
   including the control result) — see `state/findings.example.jsonl`. No stored evidence
   meeting this bar → the finding stays `verified: false` (a candidate), however convincing
   it looks. A reflected marker alone — without the boundary shown — is a candidate.
5. **Expected evidence**: after the ```http block, add a fenced block describing exactly what
   response proves the bug (status, body marker, differential, timing) — the triager checks
   against this.
6. **Sanity**: run `python3 tools/poc_replay.py <bundle> --dry-run --var ...` before handing
   over — it validates the scope check, placeholders, and request parse. Then hand the raw
   request to the human for confirmation in Burp Repeater (the verification gate).
