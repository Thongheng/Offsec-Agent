# How To Use This Setup

This kit is for one thin loop: portfolio -> kill-test -> one enabled feature ->
hunt -> replay -> honest closeout. Do not start from only a HackerOne handle.

## First Prompt To Start Hunting

Paste this into a fresh agent session from the repo root:

```text
Use the offsec workflow. I want to hunt <shape/class>, for example collaboration
authz or catalog/name-field stored XSS. Build a 3-5 candidate portfolio first.
For each candidate, check eligibility/policy, define the <=1h kill-test, and do
not open a hunt until one target has an enabled accepted-shape feature.
```

If you already have candidate handles:

```text
Use the offsec workflow. Candidate handles: <a>, <b>, <c>. Shape: <bug shape>.
Run/guide the kill-test plan, record killtest + yield, then recommend one target
and 1 focus feature. Do not hunt yet.
```

## One-Time Setup

```bash
cd /Users/thonghengheu/OffSec/RnD/offsec-agent
python3 -m pip install -e .
python3 tests/smoke.py
```

Use Burp or Caido with MCP for interactive traffic. The CLI is the memory and
gatekeeper; MCP is the eyes during the hunt.

## Start A Bounty

### 1. Create/select the target workspace

```bash
python3 -m offsec new <target-name>
python3 -m offsec use <target-name>
```

For HackerOne, draft scope and audit policy:

```bash
python3 -m offsec.h1 rules <handle>
python3 -m offsec.h1 init <handle>
```

Review `scope.proposed.yaml`, encode policy restrictions, then approve it:

```bash
mv targets/<target-name>/scope.proposed.yaml targets/<target-name>/scope.yaml
python3 -m offsec status
python3 -m offsec advance
```

### 2. Select with a real portfolio

Run 3-5 <=1h kill tests. Each asks: can you sign up/log in, and can you reach
one accepted-shape feature on a usable tier?

```bash
python3 -m offsec killtest --candidate <handle-a> --result hit --evidence "reached project invite as free user"
python3 -m offsec killtest --candidate <handle-b> --result partial --evidence "signup ok; sharing paid-tier"
python3 -m offsec killtest --candidate <handle-c> --result miss --evidence "no usable tenant"
```

If this is a private one-target pentest, record why fewer candidates are allowed:

```bash
python3 -m offsec killtest --candidate <handle> --result hit --evidence "authorized private target" --override-reason "single authorized target"
```

Record yield and choose 1-3 focus features:

```bash
python3 -m offsec yield --shapes 1 --enabled 1 --contexts 2 --notes "sharing authz reachable with A/B"
python3 -m offsec feature add F1 --name "project sharing permissions"
python3 -m offsec advance
```

### 3. Provision until the feature is enabled

Create identities A and B, seed objects, and prove the feature works at the
accepted-bug shape.

```bash
python3 -m offsec probe --feature F1 --shape "A shares project; B can observe invite/project" --result enabled --evidence "project p123 shared to B; B sees marker M123"
python3 -m offsec advance
```

If a human action blocks you:

```bash
python3 -m offsec dependency --what "paid tier for collaboration" --owner human
python3 -m offsec dependency --resolve "paid tier for collaboration"
```

If the focus feature is disabled or no-op, abandon or explicitly downgrade scope.
Do not sweep random endpoints to compensate.

### 4. Hunt one enabled feature

Use the product as A/B, watch MCP traffic, and record truth in the event log.

```bash
python3 -m offsec observe --element "GET /api/projects/{id}" --feature F1 --class crown-jewel --worth high
python3 -m offsec hypothesis --element "GET /api/projects/{id}" --feature F1 --class authz --hypothesis "B can read A project by id" --priority high
python3 -m offsec next
python3 -m offsec attempt --element "GET /api/projects/{id}" --result not-vulnerable --context other --class authz --feature F1 --ref W-0001 --evidence "B->A id 403; B->own id 200"
```

Signals and leads:

```bash
python3 -m offsec signal --ref W-0002 --why "B gets 200 after invite revoke" --feature F1 --class authz --evidence "revoked invite still reads marker M123"
python3 -m offsec lead --target "revoked invite lifecycle" --observation "read survives revoke" --why "possible lifecycle authz chain" --feature F1
python3 -m offsec lead --resolve L-0001 --result killed --evidence "state cleared after cache wait; no boundary crossed"
```

After a cheap pass with no signal, pivot to a higher-complexity reachable cell
such as lifecycle, role change, race, import/move/copy, or abandon.

### 5. Verify before marking verified

Record candidates early:

```bash
python3 -m offsec evidence --title "Revoked project invite can still read project marker" --class authz --candidate --impact "B can read A-owned project after revoke"
```

Replay the PoC, then mark verified only after replay succeeds:

```bash
python3 -m offsec.verify.poc pocs/F-0001.poc.md --var HOST=app.example.com --var TOKEN_A=... --var TOKEN_B=...
python3 -m offsec evidence --title "Revoked project invite can still read project marker" --class authz --verified --validator-ok --poc pocs/F-0001.poc.md --impact "B can read A-owned project after revoke"
```

Human override is allowed only with a reason:

```bash
python3 -m offsec evidence --title "..." --verified --human-override "triager reproduced live from attached Burp project"
```

A PoC file existing on disk is not enough.

### 6. Close honestly

```bash
python3 -m offsec frontier --open
python3 -m offsec closeout
```

If closeout refuses, either finish the open frontier/leads or abandon with a
named reason:

```bash
python3 -m offsec abandon --reason "focus feature gated after free-tier probe"
```

## Daily Operating Rules

- Start with a portfolio, not a handle.
- Hunt one enabled feature at a time.
- Use product state first; use MCP history to extract real requests.
- Record every attempt when you interpret it, not later.
- Resolve leads; do not leave a pile of vague chain ideas.
- Verified means replay passed or a human override is recorded.
- Success is a valid reproducible bug, or an honest abandon that teaches the next
  target choice.
