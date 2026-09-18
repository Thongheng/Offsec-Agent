"""Scope gate — fail-closed authorization check (ported from tools/scope_check.py).

A target passes if it matches in_scope OR test_infrastructure (hosts you control that
are contacted while testing in-scope targets) AND does not match off_limits, which is
an absolute override. A scoped hostname resolving to an off-limits IP is blocked.
No scope file, malformed scope, or unparseable target => BLOCK.
"""
from __future__ import annotations

import ipaddress
import socket
from datetime import date
from urllib.parse import urlsplit

from .. import config


def load_scope(path: str | None = None) -> dict:
    try:
        import yaml
    except ImportError:
        raise RuntimeError("PyYAML required (pip install pyyaml)")
    p = path or str(config.scope_path())
    try:
        cfg = yaml.safe_load(open(p))
    except FileNotFoundError:
        raise FileNotFoundError(f"scope file not found: {p}")
    if not isinstance(cfg, dict):
        raise ValueError("scope file is not a mapping")
    for key in ("engagement", "authorization", "in_scope", "off_limits", "roe"):
        if key not in cfg:
            raise ValueError(f"scope file missing required key: {key}")
    auth = cfg.get("authorization") or {}
    if not auth.get("reference") or not auth.get("authorized_by"):
        raise ValueError("authorization record incomplete (reference/authorized_by)")
    if auth.get("valid_until"):
        y, m, d = (int(x) for x in str(auth["valid_until"]).split("-"))
        if date.today() > date(y, m, d):
            raise ValueError("authorization expired (valid_until passed)")
    if not (cfg["in_scope"].get("hostnames") or cfg["in_scope"].get("ips") or cfg["in_scope"].get("cidrs")):
        raise ValueError("in_scope is empty — nothing is authorized")
    return cfg


def hostname_matches(pattern: str, host: str) -> bool:
    pattern = pattern.lower().strip()
    host = host.lower().strip()
    if pattern == host:
        return True
    if pattern.startswith("*."):
        suffix = pattern[1:]
        return host.endswith(suffix) and host != suffix.lstrip(".")
    return False


def ip_in_scope(ip: str, entries: list | None, cidrs: list | None) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for e in entries or []:
        if str(addr) == str(e).strip():
            return True
    for c in cidrs or []:
        try:
            if addr in ipaddress.ip_network(c, strict=False):
                return True
        except ValueError:
            continue
    return False


def parse_target(target: str) -> tuple[str, str]:
    t = target.strip()
    if "://" in t:
        t = urlsplit(t).hostname or ""
    else:
        t = t.split("/")[0]
        if t.count(":") == 1:
            t = t.rsplit(":", 1)[0]
    t = t.strip("[]")
    if not t:
        raise ValueError(f"cannot parse target: {target!r}")
    try:
        ipaddress.ip_address(t)
        return ("ip", t)
    except ValueError:
        return ("hostname", t)


def resolve(host: str) -> list[str]:
    try:
        return sorted({i[4][0] for i in socket.getaddrinfo(host, None)})
    except OSError:
        return []


def check_target(cfg: dict, target: str) -> dict:
    in_scope = cfg["in_scope"]
    off = cfg.get("off_limits") or {}
    test_infra = cfg.get("test_infrastructure") or {}
    kind, value = parse_target(target)
    res = {"target": target, "kind": kind, "value": value, "allowed": False, "reasons": []}

    if kind == "ip":
        if ip_in_scope(value, off.get("ips"), off.get("cidrs")):
            res["reasons"].append("matches off_limits")
            return res
        if ip_in_scope(value, test_infra.get("ips"), test_infra.get("cidrs")):
            res["allowed"] = True
            res["reasons"].append("ip in test_infrastructure")
            return res
        if ip_in_scope(value, in_scope.get("ips"), in_scope.get("cidrs")):
            res["allowed"] = True
            res["reasons"].append("ip in scope")
        else:
            res["reasons"].append("ip not in scope")
        return res

    if any(hostname_matches(p, value) for p in off.get("hostnames") or []):
        res["reasons"].append("hostname matches off_limits")
        return res
    if any(hostname_matches(p, value) for p in test_infra.get("hostnames") or []):
        res["allowed"] = True
        res["reasons"].append("hostname in test_infrastructure")
        return res
    if not any(hostname_matches(p, value) for p in in_scope.get("hostnames") or []):
        res["reasons"].append("hostname not in scope")
        return res
    res["reasons"].append("hostname in scope")

    ips = resolve(value)
    res["resolved_ips"] = ips
    if not ips:
        res["reasons"].append("DNS resolution failed — allowed on hostname match only")
    declared = bool(in_scope.get("ips") or in_scope.get("cidrs"))
    for ip in ips:
        if ip_in_scope(ip, off.get("ips"), off.get("cidrs")):
            res["reasons"].append(f"resolved IP {ip} matches off_limits")
            return res
        if declared and not ip_in_scope(ip, in_scope.get("ips"), in_scope.get("cidrs")):
            res["reasons"].append(f"resolved IP {ip} not in declared scope IPs — possible rebinding")
            return res
    res["allowed"] = True
    return res


def check(targets: list[str], scope_file: str | None = None) -> tuple[bool, list[dict]]:
    """Fail-closed: returns (all_allowed, verdicts). Raises nothing."""
    try:
        cfg = load_scope(scope_file)
    except Exception as e:
        return False, [{"target": t, "allowed": False, "reasons": [f"FAIL-CLOSED: {e}"]} for t in targets]
    verdicts = [check_target(cfg, t) for t in targets]
    return all(v["allowed"] for v in verdicts), verdicts
