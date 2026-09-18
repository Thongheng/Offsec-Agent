# P6 — Report

Inputs: derived views (`offsec derive` -> `derived/findings.json`, `derived/coverage.json`),
PoC bundles in `pocs/`, accepted shapes. Only `verified: true` leaves the ledger.

**Branch A — bug bounty.** The triager is your reader:
- In scope, bounty+submission eligible, class not excluded.
- Non-duplicate: check `offsec shapes list --handle <h>` and disclosed hacktivity. Same class
  on a *different* endpoint is not a duplicate — state the differentiator.
- Verified PoC (boundary crossed + controls) + one-paragraph impact in the program's terms +
  5-minute reproduction steps.
- A valid Low/Medium **is submitted**; excluded-class noise is not.

**Branch B — pentest.** Completeness is the deliverable: exec summary, all findings
critical→informational, mandatory coverage statement (from derived coverage), methodology +
limitations, retest guidance.

**Both:** no credentials/tokens in the report; reference the credential store. Write
`reports/report.md`; for bounty, also draft the submission text blocks.
