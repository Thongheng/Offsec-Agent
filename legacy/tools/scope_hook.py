#!/usr/bin/env python3
"""scope_hook.py — drift guardrail for offsec-agent (PreToolUse hook).

HONEST POSITIONING: this hook catches the model *drifting* (forgetting RoE
mid-session, writing to scope files). It is best-effort text scanning, NOT an
adversary-proof wall. What is authoritative: tools/scope_check.py decides the
scope question, and tools/poc_replay.py scope-checks the host it actually
connects to before sending. This hook is a convenience layer in front of those.

IMPORTANT: this hook only runs if a client wires it as a PreToolUse hook. If no
settings.json references it, none of this is active — never treat the guardrails
below as guarantees.

What it enforces (all cheap, all understandable):
  1. Write/Edit: scope.yaml / scope.example.yaml are human-owned. The agent
     may draft scope.proposed.yaml. Unlock: .scope-unlocked (repo or target
     level) — human-controlled; the agent can never touch the marker itself.
     All basename compares are case-insensitive (the FS is, on macOS).
  2. Network commands: CONNECTION targets are scope-checked — URL in
     authority position, Host: headers, tool target args (-u/--url/--host/...,
     targetHostname for Burp MCP), bare IPs in tool position. URLs inside
     payloads (?returnurl=https://x, -d/--data bodies) are DATA, not
     destinations. test_infrastructure hosts (your Collaborator/VPS) are
     allowed. off_limits overrides everything. Missing scope file = blocked.
     Network-capable with no determinable target = blocked, unless a
     `# scope-ok: host1, host2` comment lists the targets (escape hatch that
     keeps file-driven scanners usable with one line of effort).
  3. High-volume request loops (seq 1 N / {1..N}, N > 20) route through
     roe.high_volume_probing (ask|allow|deny). This only catches those literal
     shell forms — python/xargs/while loops are NOT detected; the real
     proportionality control is the human conversation plus the RoE cap.
  4. RoE: allowed_windows (HH:MM, no midnight crossing) checked first; the
     coarse max_network_commands_per_minute counter increments only AFTER the
     scope verdict passes — blocked attempts don't consume budget.
     (max_requests_per_second is enforced by tools/poc_replay.py, not here.)

Exit 0 = allow, 2 = block (stderr is shown to the agent).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
try:
    from engagement import engagement_root
    ENG_ROOT = str(engagement_root())
except RuntimeError as e:  # stale/broken current target — fail with the fix, not a traceback
    ENG_ROOT = None
    ENG_ERROR = str(e)

SCOPE_CHECK = os.path.join(REPO, "tools", "scope_check.py")
SCOPE_FILE = os.path.join(ENG_ROOT, "scope.yaml") if ENG_ROOT else ""
RATE_FILE = os.path.join(ENG_ROOT, ".ratelimit.json") if ENG_ROOT else ""

NETWORK_TOOLS = {
    "curl", "wget", "nc", "ncat", "netcat", "ssh", "telnet", "ping", "dig",
    "host", "nslookup", "nmap", "httpx", "ffuf", "nuclei", "sqlmap", "gobuster",
    "dirsearch", "subfinder", "amass", "masscan", "rustscan", "whatweb", "wafw00f",
}
URL_RE = re.compile(r"https?://[^\s'\"<>`\\)]+")
IPV4_RE = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")
SCOPE_BASENAMES = {"scope.yaml", "scope.example.yaml"}
BODY_FLAGS = {"-d", "--data", "--data-raw", "--data-ascii", "--data-binary",
              "--data-urlencode", "-F", "--form", "--form-string"}
TARGET_FLAGS = {"-u", "--url", "--host", "-t", "--target", "--url="}


def block(msg: str) -> int:
    print(f"[scope_hook] {msg}", file=sys.stderr)
    return 2


def is_unlocked() -> bool:
    return (os.path.exists(os.path.join(REPO, ".scope-unlocked"))
            or (ENG_ROOT and os.path.exists(os.path.join(ENG_ROOT, ".scope-unlocked"))))


def basename_ok(base: str) -> bool:
    return base.lower() in SCOPE_BASENAMES


def guard_write(ti: dict) -> int:
    path = str(ti.get("file_path") or ti.get("notebook_path") or "")
    base = os.path.basename(path)
    if base.lower() == ".scope-unlocked":
        return block("the unlock marker is human-controlled; the agent may not create or remove it")
    if basename_ok(base) and not is_unlocked():
        return block(f"scope configs are human-owned; agent may not write {path}. "
                     "Fast paths: draft scope.proposed.yaml (always allowed), or ask the "
                     "human to `touch .scope-unlocked`, then edit scope.yaml directly.")
    return 0


def is_burp_tool(tool: str) -> bool:
    """True for the Burp MCP tools regardless of the configured server name.
    Clients name the server differently (burp, burpsuite, ...) — matching the
    prefix exactly would silently disable the scope check on the main primitive."""
    return tool.startswith("mcp__") and "burp" in tool.split("__")[1].lower()


def connection_targets(text: str, tool: str) -> tuple[list[str], bool]:
    """Extract connection targets; returns (targets, saw_network_tool).
    Payload URLs (after ?&= or in -d/--data bodies) are not destinations."""
    targets: list[str] = []
    tokens = text.split()
    net_word = False
    for i, tok in enumerate(tokens):
        bare = tok.strip("\"'")
        if bare in NETWORK_TOOLS:
            net_word = True
        prev = tokens[i - 1].strip("\"'") if i else ""
        if prev in BODY_FLAGS:
            continue  # this whole token is request-body data
        in_target = prev in TARGET_FLAGS
        for m in URL_RE.finditer(tok):
            before = tok[m.start() - 1] if m.start() else ""
            if m.start() == 0 or before not in "?&=":
                targets.append(m.group(0))
        if IPV4_RE.fullmatch(bare) and (in_target or (net_word and i and not prev.startswith("-"))):
            targets.append(bare)
    for hm in re.finditer(r"(?im)^\s*host:\s*(\S+)", text):
        targets.append(hm.group(1))
    if is_burp_tool(tool):
        targets += re.findall(r'"targetHostname":\s*"([^"]+)"', text)
    seen, out = set(), []
    for t in targets:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out, net_word


def scope_ok_hosts(text: str) -> list[str]:
    m = re.search(r"(?im)#\s*scope-ok:\s*(.+)", text)
    return [h.strip() for h in m.group(1).split(",") if h.strip()] if m else []


def high_volume(cmd: str, tool: str) -> tuple[bool, str]:
    """Request-loop constructs route through roe.high_volume_probing."""
    if tool != "Bash":
        return False, ""
    n = 0
    for m in re.finditer(r"seq\s+\S+\s+(\d+)|\{1\.\.(\d+)\}", cmd):
        n = max(n, int(m.group(1) or m.group(2) or 0))
    if n <= 20:
        return False, ""
    try:
        import yaml
        with open(SCOPE_FILE) as f:
            mode = str(((yaml.safe_load(f) or {}).get("roe") or {}).get("high_volume_probing") or "ask")
    except Exception:
        mode = "ask"
    if mode == "allow":
        return False, ""
    return True, (f"high-volume loop detected ({n} iterations) — roe.high_volume_probing={mode!r}: "
                  "propose the volume and expected impact (lockout/ban risk) to the human first, "
                  "or ask them to set high_volume_probing: allow in scope.yaml.")


def windows_ok() -> tuple[bool, str]:
    try:
        import yaml
        with open(SCOPE_FILE) as f:
            cfg = yaml.safe_load(f) or {}
        windows = (cfg.get("roe") or {}).get("allowed_windows") or []
    except Exception as e:
        return False, f"cannot read RoE from scope.yaml: {e}"
    if not windows:
        return True, ""
    now = datetime.now()
    mins = now.hour * 60 + now.minute

    def to_min(hhmm: str) -> int:
        h, m = hhmm.strip().split(":")
        return int(h) * 60 + int(m)

    for w in windows:
        try:
            a, b = (to_min(x) for x in str(w).split("-", 1))
            if a <= mins <= b:
                return True, ""
        except (ValueError, IndexError):
            continue
    return False, f"outside allowed testing windows {windows} (now {now:%H:%M})"


def rate_ok() -> tuple[bool, str]:
    try:
        import yaml
        with open(SCOPE_FILE) as f:
            cfg = yaml.safe_load(f) or {}
        cap = int((cfg.get("roe") or {}).get("max_network_commands_per_minute") or 30)
    except Exception as e:
        return False, f"cannot read RoE from scope.yaml: {e}"
    try:
        with open(RATE_FILE) as f:
            st = json.load(f)
    except Exception:
        st = {"t": time.time(), "n": 0}
    if time.time() - st.get("t", 0) > 60:
        st = {"t": time.time(), "n": 0}
    st["n"] = int(st.get("n", 0)) + 1
    with open(RATE_FILE, "w") as f:
        json.dump(st, f)
    if st["n"] > cap:
        return False, (f"coarse command throttle hit ({cap}/min, roe.max_network_commands_per_minute). "
                       "If this blocks legitimate work, ask the human to raise the cap in scope.yaml.")
    return True, ""


def scope_verdict(targets: list[str]) -> tuple[bool, str]:
    try:
        p = subprocess.run([sys.executable, SCOPE_CHECK, "--scope", SCOPE_FILE, *targets],
                           capture_output=True, text=True, timeout=30)
    except Exception as e:
        return False, f"scope check failed to run: {e}"
    if p.returncode == 2:
        return False, f"FAIL-CLOSED: {p.stderr.strip()}"
    if p.returncode != 0:
        bad = []
        for line in p.stdout.splitlines():
            try:
                v = json.loads(line)
                if not v.get("allowed"):
                    bad.append(f"{v['target']}: {', '.join(v['reasons'])}")
            except json.JSONDecodeError:
                pass
        return False, f"BLOCKED by scope: {'; '.join(bad) or p.stdout.strip()}"
    return True, ""


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception as e:
        return block(f"fail-closed: cannot parse hook input: {e}")
    tool = event.get("tool_name", "")
    ti = event.get("tool_input", {}) or {}

    if tool in ("Write", "Edit", "NotebookEdit"):
        return guard_write(ti)

    if tool == "Bash":
        text = str(ti.get("command", ""))
    elif tool == "WebFetch":
        text = str(ti.get("url", ""))
    elif tool.startswith("mcp__"):
        text = json.dumps(ti)
    else:
        return 0

    # stale/missing current target: block anything target-facing with the fix, not a traceback
    if not ENG_ROOT and (URL_RE.search(text) or is_burp_tool(tool)):
        return block(ENG_ERROR)

    targets, net_word = connection_targets(text, tool)
    if not targets and not net_word and not URL_RE.search(text):
        return 0  # local-only command

    blocked, msg = high_volume(text, tool)
    if blocked:
        return block(msg)

    if targets:
        ok, why = scope_verdict(targets + scope_ok_hosts(text))
        if not ok:
            return block(why)
    else:
        return block("network command with no inline target — inline the target(s), or add a "
                     "comment '# scope-ok: host1, host2' listing them and re-run")

    ok, why = windows_ok()
    if not ok:
        return block(why)
    ok, why = rate_ok()
    if not ok:
        return block(why)
    return 0


if __name__ == "__main__":
    sys.exit(main())
