#!/usr/bin/env python3
"""h1.py — HackerOne API for program discovery, scope, and payout intel.

Credentials (env vars, NEVER stored in this repo):
  export H1_USERNAME=<API identifier>     # HackerOne → Settings → API Token
  export H1_TOKEN=<API token>

Usage:
  python3 tools/h1.py programs [--mine]            # list programs (handle, bounties?, state)
  python3 tools/h1.py program <handle>             # details: policy, submission state, offers
  python3 tools/h1.py scope <handle>               # structured scope table
  python3 tools/h1.py rules <handle>               # scope eligibility + FULL policy (per-class gate)
  python3 tools/h1.py init <handle>                # scope → targets/<current>/scope.proposed.yaml
  python3 tools/h1.py hacktivity "team_handle:\"acme\""   # disclosed reports + payouts
  python3 tools/h1.py pick h1 h2 h3                # compare candidates (reliable signals)
  python3 tools/h1.py reports                      # your reports
  python3 tools/h1.py earnings                     # your bounty history

Picking a program (run in this order):
  1. programs                        → candidates with offers_bounties=true, open_scope
  2. program <handle>                → read policy: automation rules, RoE, exclusions,
                                       and whether a bounty TABLE ($) is published
  3. hacktivity 'team_handle:"<handle>"'  → recent disclosures per team (activity signal)
  4. init <handle>                   → draft scope, human approves with mv

HACKTIVITY RULES (empirically verified):
  - Combine filters ONLY with explicit uppercase AND: team_handle:"x" AND total_awarded_amount:>0.
    A bare SPACE between clauses acts as OR (silently returns unrelated teams) — classic trap.
  - team_handle is undocumented but works; the documented `team` field returns empty.
  - Searchable: team_handle, team, severity_rating, substate, disclosed, disclosed_at,
    total_awarded_amount, cwe, cve_ids, reporter, asset_type, has_collaboration, title (free text).
    NOT searchable: has_bounty, severity, state, submitted_at, votes.
  - Bounty amounts CURRENTLY leak on UNDISCLOSED reports (null title, real amount) —
    undocumented behavior, may change (cf. H1 reports #2310620/#2011431).
  - INTERPRETATION RULE: paid disclosures = PROOF of paying (positive signal).
    ZERO paid disclosures = NO EVIDENCE either way — programs can keep reports fully
    private, pay outside H1, or H1 may honor hiding. Never eliminate a program on absence.
  - page[size] accepts up to 100, but hacktivity returns max 50 rows per page (verified).
    Invalid fields return a helpful 400 "not searchable".
  - hacktivity is PUBLIC (works without credentials); all other /hackers/* endpoints 401.

PROGRAM-SELECTION SIGNALS (reliable → misleading):
  reliable: offers_bounties, fast_payments, gold_standard_safe_harbor, triage_active,
    open_scope (all API flags) · paid-disclosure count + amounts via the AND query ·
    bounty TABLE in policy markdown (if published)
  misleading: upvotes, "resolved" without amounts (could be paid-privately or rep-only),
    disclosure volume (programs choose visibility), bounty-table max figures (marketing),
    absence of paid disclosures (absence is not evidence — see above)
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
API = "https://api.hackerone.com/v1"


def _load_dotenv() -> None:
    """Fallback credential source: <repo>/.env (gitignored). Real env vars win."""
    env_file = os.path.join(REPO, ".env")
    if not os.path.exists(env_file):
        return
    for line in open(env_file):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def creds() -> tuple[str, str]:
    _load_dotenv()
    u, t = os.environ.get("H1_USERNAME"), os.environ.get("H1_TOKEN")
    if not u or not t:
        sys.exit("set H1_USERNAME and H1_TOKEN (HackerOne → Settings → API Token); "
                 "export them in your shell — never store them in this repo")
    return u, t


def get(path: str, params: str = "") -> dict:
    u, t = creds()
    b64 = base64.b64encode(f"{u}:{t}".encode()).decode()
    url = f"{API}{path}" + (f"?{params}" if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {b64}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        sys.exit(f"H1 API {e.code}: {body}")


def paginate(path: str, params: str = "", pages: int = 5) -> list[dict]:
    out, page = [], 1
    while page <= pages:
        sep = "&" if params else ""
        data = get(path, f"{params}{sep}page[number]={page}&page[size]=100")
        batch = data.get("data", [])
        out += batch
        if not data.get("links", {}).get("next"):
            break
        page += 1
    return out


def attr(rel: dict) -> dict:
    return rel.get("attributes", {})


def cmd_programs(mine_only: bool) -> None:
    # /hackers/programs lists all public programs; there is no "mine" variant in the
    # API used here, so --mine currently returns the same list (flagged as a limitation).
    rows = paginate("/hackers/programs")
    if mine_only:
        print("(--mine: this H1 API exposes only the public program list; no filtering applied)\n")
    for r in rows:
        a = attr(r)
        if a.get("submission_state") not in ("open", "public"):  # skip closed
            continue
        handle = a.get("handle", "?")
        bounty = "bounty" if a.get("offers_bounties") else "kudos"
        scope = "open-scope" if a.get("open_scope") else "scoped"
        print(f"{handle:30s} {bounty:6s} {scope:10s} state={a.get('submission_state')}")
    print(f"\n{len(rows)} program(s) (first 5 pages). Detail: python3 tools/h1.py program <handle>")


def cmd_program(handle: str) -> None:
    d = get(f"/hackers/programs/{handle}")
    a = d.get("attributes") or attr(d.get("data", {}))  # single-program responses are UNWRAPPED
    print(f"handle:            {a.get('handle')}")
    print(f"name:              {a.get('name')}")
    print(f"offers bounties:   {a.get('offers_bounties')}")
    print(f"submission state:  {a.get('submission_state')}")
    print(f"open scope:        {a.get('open_scope')}")
    print(f"reports required:  {a.get('reports_required_for_bounty')}")
    print(f"triage active:     {a.get('triage_active')}   fast payments: {a.get('fast_payments')}   "
          f"safe harbor: {a.get('gold_standard_safe_harbor')}")
    policy = (a.get("policy") or "").strip()
    print(f"\n--- policy (FULL, {len(policy)} chars — READ IT: test env, excluded vuln classes, RoE) ---")
    print(policy or "(no policy text)")


def cmd_rules(handle: str) -> None:
    """One-shot program-detail audit: per-asset eligibility + the FULL policy.

    Run this BEFORE planning any tests. A class is only worth testing when the asset is
    eligible_for_bounty AND eligible_for_submission, the class is NOT on the excluded list,
    the target is inside the stated test environment, and it is within max_severity. Encode
    the result in scope.yaml -> program_rules so tests are gated per class, not fired blind.
    """
    print(f"===== {handle}: asset eligibility =====\n")
    cmd_scope(handle)
    print(f"\n\n===== {handle}: full program policy (READ for excluded vuln classes + test env) =====\n")
    cmd_program(handle)
    print("\n\n===== per-class eligibility gate =====")
    print("Before testing any class, confirm ALL of:")
    print("  1. the ASSET is eligible_for_bounty AND eligible_for_submission (not just one);")
    print("  2. the CLASS is not in the policy's excluded-vulnerability-class list;")
    print("  3. the target is inside the stated TEST ENVIRONMENT (testnet / own trial / etc.);")
    print("  4. the finding is within max_severity and any partial-scope instruction.")
    print("Record accepted/excluded classes in scope.yaml -> program_rules. Only fire classes that")
    print("pass; excluded classes are chain-or-kill, never reported standalone.")


def cmd_scope(handle: str) -> None:
    """Full structured-scope audit: eligibility (BOUNTY and SUBMISSION are distinct!),
    max_severity, and the FULL per-asset instruction (partial scope, tier, notes).
    Never truncate the instruction — it often carries the real scope boundary."""
    import textwrap
    rows = paginate(f"/hackers/programs/{handle}/structured_scopes")
    for r in rows:
        a = attr(r)
        b = "bounty" if a.get("eligible_for_bounty") else "NO-BOUNTY"
        s = "submit" if a.get("eligible_for_submission") else "NO-SUBMIT"
        print(f"{a.get('asset_type','?'):11s} {a.get('asset_identifier','?')}")
        print(f"            eligibility: {b} / {s}   max_severity: {a.get('max_severity') or '-'}")
        instr = (a.get("instruction") or "").strip()
        if instr:
            for i, line in enumerate(textwrap.wrap(instr, 100)):
                print(f"            {'instruction: ' if i == 0 else '             '}{line}")
    eligible = sum(1 for r in rows if attr(r).get("eligible_for_submission"))
    print(f"\n{len(rows)} asset(s): {eligible} eligible_for_submission, {len(rows) - eligible} NOT")
    print("reminder: read the FULL policy too (test env, excluded vuln classes, automation rules):")
    print(f"  python3 tools/h1.py program {handle}")


def normalize_host(asset: str) -> str:
    """Reduce an asset identifier to a bare hostname. Handles full URLs
    (https://app.example.com/path -> app.example.com), host:port, and wildcards."""
    a = asset.strip().lower()
    if "://" in a:
        from urllib.parse import urlsplit
        a = urlsplit(a).hostname or ""
    else:
        a = a.split("/")[0]
        if a.startswith("["):  # IPv6 literal
            a = a[1:a.index("]")] if "]" in a else a
        elif a.count(":") == 1:
            a = a.split(":")[0]
    return a.strip().strip(".")


def to_yaml(data: dict, handle: str, name: str) -> str:
    in_scope, oos = [], []
    for rel in data.get("data", []):
        a = rel.get("attributes", {})
        asset = a.get("asset_identifier", "")
        if a.get("asset_type") not in ("URL", "WILDCARD", "DOMAIN"):
            continue
        host = normalize_host(asset)
        if not host:
            continue
        instr = (a.get("instruction") or "").strip()
        (in_scope if a.get("eligible_for_bounty", True) else oos).append((host, instr))
    lines = [f'engagement: "{name}"', "", "authorization:", "  type: bug-bounty",
             f'  reference: "https://hackerone.com/{handle}"',
             '  authorized_by: "HackerOne program policy"', '  valid_until: ""', "",
             "in_scope:", "  hostnames:"]
    lines += [f'    - "{h}"' + (f"   # {i}" if i else "") for h, i in in_scope]
    lines += ["  ips: []", "  cidrs: []", "", "off_limits:", "  hostnames:"]
    lines += [f'    - "{h}"' + (f"   # {i}" if i else "") for h, i in oos]
    lines += ["  ips: []", "  cidrs: []", "", "roe:",
              "  max_network_commands_per_minute: 30", "  max_requests_per_second: 5",
              "  allowed_windows: []", '  notes: ""', "",
              "program_rules:",
              "  # Per-CLASS eligibility gate — fill from `python3 tools/h1.py rules <handle>`.",
              "  # No class is tested unless it passes here (asset eligible + class not excluded).",
              "  asset_eligibility_notes: \"\"   # eligible_for_bounty AND eligible_for_submission; partial scope",
              "  excluded_classes: []           # classes the program will NOT accept",
              "  chained_only_classes: []       # valid only WITH a named impact (open redirect, self-XSS, ...)",
              "  test_environment: \"\"           # e.g. 'testnet only', 'own trial only'",
              "  max_severity: \"\"", "",
              "reporting:",
              "  engagement_type: bug-bounty", "  include_informational: false",
              "  severity_scale: cvss", "", "test_accounts:", '  credentials_ref: ""',
              '  provisioning_notes: ""', "", "recon:", '  enum_output_dir: ""']
    return "\n".join(lines) + "\n"


def cmd_init(handle: str) -> None:
    from engagement import engagement_root
    data = get(f"/hackers/programs/{handle}/structured_scopes")
    yaml_text = to_yaml(data, handle, f"{handle}-bugbounty")
    draft = os.path.join(str(engagement_root()), "scope.proposed.yaml")
    with open(draft, "w") as f:
        f.write(yaml_text)
    print(f"draft written: {draft}")
    print("fill roe.notes from the program policy, then approve with:")
    print(f"  mv {draft} " + os.path.join(str(engagement_root()), "scope.yaml"))


def cmd_hacktivity(query: str) -> None:
    from urllib.parse import quote
    rows = paginate("/hackers/hacktivity", f"queryString={quote(query)}")
    for r in rows:
        a = attr(r)
        prog = (r.get("relationships", {}).get("program", {}).get("data", {}).get("attributes", {}) or {})
        team = prog.get("handle", "?")
        bounties = a.get("total_awarded_amount") or 0
        print(f"${bounties:>8} {a.get('severity_rating') or '-':8s} {a.get('substate') or '':12s} "
              f"team={team:14s} {str(a.get('title',''))[:65]}")
    print(f"\n{len(rows)} disclosed report(s) for query: {query}")


def cmd_pick(handles: list[str]) -> None:
    """Decision support: reliable signals + paid-disclosure counts per candidate.

    Read alongside prompts/targeting.md. The disclosed-SHAPE lines are the important output —
    they are the program's accepted taste; replicate a shape on its feature/siblings. Payout
    columns are CONTEXT ONLY: severity/payout never filter what you test, and no column here
    tells you whether you can REACH the bug-bearing surface (Gate 1) — that is an environment
    question, settle it before hunting.
    """
    from urllib.parse import quote
    print(f"{'handle':16s} {'bounty':6s} {'fast$':5s} {'GSSH':4s} {'triage':6s} {'paid':>5s} {'disc':>5s} {'top payouts'}")
    for h in handles:
        a = get(f"/hackers/programs/{h}").get("attributes", {})
        try:
            d = get("/hackers/hacktivity", f"queryString={urllib.parse.quote(f'team_handle:\"{h}\" AND total_awarded_amount:>0')}&page[size]=100")
            paid = d.get("data", [])
            amts = sorted([r["attributes"].get("total_awarded_amount") or 0 for r in paid], reverse=True)
        except SystemExit:
            paid, amts = [], []
        try:
            alld = get("/hackers/hacktivity", f"queryString={urllib.parse.quote(f'team_handle:\"{h}\"')}&page[size]=100")
            titles = [(r["attributes"].get("title") or "").strip() for r in alld.get("data", [])]
        except SystemExit:
            titles = []
        print(f"{h:16s} {str(a.get('offers_bounties')):6s} {str(a.get('fast_payments')):5s} "
              f"{str(a.get('gold_standard_safe_harbor')):4s} {str(a.get('triage_active')):6s} "
              f"{len(amts):>5d} {len(titles):>5d} {amts[:3]}")
        # disclosed SHAPES (accepted taste) — read these before choosing a focus feature
        for t in titles[:3]:
            print(f"{'':16s}   ↳ {t[:96]}")


def cmd_reports() -> None:
    rows = paginate("/hackers/me/reports")
    for r in rows:
        a = attr(r)
        print(f"[{a.get('state','?'):10s}] {str(a.get('title',''))[:75]}  ({r.get('id','')})")
    print(f"\n{len(rows)} report(s)")


def cmd_earnings() -> None:
    rows = paginate("/hackers/payments/earnings")
    total = 0
    for r in rows:
        a = attr(r)
        amt = (a.get("amount") or 0) / 100 if isinstance(a.get("amount"), int) else a.get("amount") or 0
        total += float(amt)
        print(f"{a.get('awarded_at','?'):12s} ${amt:>10} {str(a.get('status',''))[:12]}")
    print(f"\n{len(rows)} earnings record(s), total ${total:.2f}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd, *rest = sys.argv[1:]
    if cmd == "programs":
        cmd_programs("--mine" in rest)
    elif cmd == "program" and rest:
        cmd_program(rest[0])
    elif cmd == "scope" and rest:
        cmd_scope(rest[0])
    elif cmd == "rules" and rest:
        cmd_rules(rest[0])
    elif cmd == "init" and rest:
        cmd_init(rest[0])
    elif cmd == "hacktivity" and rest:
        cmd_hacktivity(" ".join(rest))
    elif cmd == "pick" and rest:
        cmd_pick(rest)
    elif cmd == "reports":
        cmd_reports()
    elif cmd == "earnings":
        cmd_earnings()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
