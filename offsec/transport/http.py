"""Scope-enforced HTTP transport.

One request function used by every discovery module and PoC. It:
  - fails closed on scope (checks the host actually connected to),
  - rate-limits to `roe.max_requests_per_second`,
  - never follows redirects silently (SSRF/redirect analysis needs the 3xx),
  - returns a small Response object.
"""
from __future__ import annotations

import http.client
import ssl
import time
import urllib.parse
from dataclasses import dataclass, field

from .. import config
from ..gates import scope

_last_send = [0.0]


@dataclass
class Response:
    status: int
    headers: dict = field(default_factory=dict)
    body: bytes = b""
    elapsed: float = 0.0
    url: str = ""

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", "replace")

    @property
    def length(self) -> int:
        return len(self.body)


class ScopeBlocked(RuntimeError):
    pass


def _rate_limit() -> None:
    rps = 2.0
    try:
        cfg = scope.load_scope()
        rps = float((cfg.get("roe") or {}).get("max_requests_per_second") or rps)
    except Exception:
        pass
    if rps <= 0:
        rps = 5.0
    wait = max(0.0, (1.0 / rps) - (time.time() - _last_send[0]))
    if wait:
        time.sleep(wait)
    _last_send[0] = time.time()


def request(method: str, url: str, headers: dict | None = None, body: bytes | None = None,
            timeout: int = 15, enforce_scope: bool = True) -> Response:
    parts = urllib.parse.urlsplit(url if "://" in url else "https://" + url)
    host = parts.hostname or ""
    if enforce_scope:
        ok, verdicts = scope.check([host])
        if not ok:
            raise ScopeBlocked(f"{host} denied: {verdicts[0].get('reasons')}")
    tls = parts.scheme != "http"
    port = parts.port or (443 if tls else 80)
    path = (parts.path or "/") + (("?" + parts.query) if parts.query else "")
    _rate_limit()
    conn_cls = http.client.HTTPSConnection if tls else http.client.HTTPConnection
    ctx = ssl.create_default_context()
    conn = conn_cls(parts.hostname, port, timeout=timeout, context=ctx) if tls else conn_cls(parts.hostname, port, timeout=timeout)
    hdrs = dict(headers or {})
    hdrs.setdefault("Host", parts.netloc)
    t0 = time.time()
    conn.request(method, path, body=body, headers=hdrs)
    r = conn.getresponse()
    data = r.read(256 * 1024)
    elapsed = time.time() - t0
    resp = Response(status=r.status, headers={k.lower(): v for k, v in r.getheaders()},
                    body=data, elapsed=elapsed, url=url)
    conn.close()
    return resp
