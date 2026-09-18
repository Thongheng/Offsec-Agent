# P4 — Verify

The bar: a triager reproduces it in 5 minutes without talking to you, and the **actual
security boundary** was crossed — not merely a request that succeeded.

Record a candidate as soon as you see it, then promote it only when verified:

```
offsec evidence --title "..." --class ... --candidate --impact "..."       # candidate
python3 -m offsec.verify.poc pocs/F-0001.poc.md --var HOST=...             # replay gate
offsec evidence --title "..." --class ... --verified --poc pocs/F-0001.poc.md --impact "..."  # verified
offsec shapes match --handle <h> --title "..." --class ...
```

The checklist below is mandatory, and promotion to `verified: true` is blocked in
the CLI until replay succeeds, an existing PoC bundle is supplied, or a human
override reason is recorded:

```
offsec evidence --title "..." --verified --validator-ok --impact "..."
offsec evidence --title "..." --verified --human-override "live triager reproduced from attached Burp project"
```

Without one of those validation paths, `offsec evidence --verified` is rejected
and recorded as a candidate.

## PoC bundle (`pocs/<F-ID>.poc.md`)
```
---
target: {{HOST}}          # host[:port]; also the scope-check target
name: <short-slug>
tls: true
finding: F-0001
---
```http
POST /api/v1/reset HTTP/1.1
Host: {{HOST}}
Content-Type: application/json
Authorization: Bearer {{VICTIM_TOKEN}}

{"email":"{{VICTIM_EMAIL}}"}
```
```
- Placeholders `{{NAME}}` for hosts/tokens/emails; **never** inline a live session cookie
  or token. Replay with `python3 -m offsec.verify.poc <bundle> --var ...` (or Burp Repeater).
- Minimal request; harmless payloads; no third-party exfiltration (use the engagement's
  callback).

## Verify checklist (every line YES, else it stays a candidate)
- [ ] Reproduced by the exact bundle, ~3x.
- [ ] **Positive control** passes (the legitimate principal can do it; object/id is real).
- [ ] **Negative control** fails (attacker denied on the normal path / non-owned id) —
      mandatory for any access-control finding.
- [ ] **Provenance**: attacker received data/effect provably owned by the other principal
      (their unique value / planted marker) or a concrete state delta — not a 200.
- [ ] Not explained by caching, your own session, the WAF, or a stale value.
- [ ] Eligible: in scope, class not excluded — else it is **chain-or-kill**, never standalone.
- [ ] Novelty: not documented/disclosed, or the differentiator is stated (same class on a
      different endpoint is not a duplicate).
- [ ] Impact stated in the program's terms.

**Before killing a candidate on an "excluded class"**, run `offsec shapes match`. If it
resembles a shape the program accepted before, it is a **HOLD** — strengthen and report,
do not kill on the generic exclusion (LEARNINGS: the files-bbp existence-oracle).
