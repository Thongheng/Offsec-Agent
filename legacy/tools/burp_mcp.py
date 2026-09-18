"""burp_mcp.py — minimal MCP client over SSE for the local Burp MCP server.

Implements just enough of MCP: SSE handshake -> endpoint discovery -> JSON-RPC
initialize -> tools/list -> tools/call. Synchronous, one command per invocation
(each run re-handshakes; Burp's server allows multiple sessions).

Usage:
  python3 tools/burp_mcp.py tools
  python3 tools/burp_mcp.py call <tool_name> '{"json": "args"}'
  python3 tools/burp_mcp.py history [--all]   # proxy history -> <engagement>/proxy-history.jsonl
"""
import base64, json, os, re, socket, sys, threading, queue, urllib.request
from urllib.parse import urlsplit

MCP_URL = "http://127.0.0.1:9876/"


class SseMcp:
    def __init__(self, base=MCP_URL):
        self.base = base
        self.endpoint_q = queue.Queue()
        self.msg_q = queue.Queue()
        self.session_events = None
        self._open_stream()

    def _open_stream(self):
        sp = urlsplit(self.base)
        self.sock = socket.create_connection((sp.hostname, sp.port or 80), timeout=60)
        req = (f"GET {sp.path or '/'} HTTP/1.1\r\nHost: {sp.hostname}\r\n"
               f"Accept: text/event-stream\r\nConnection: keep-alive\r\n\r\n")
        self.sock.sendall(req.encode())
        self.rfile = self.sock.makefile("rb")
        # response headers (note Transfer-Encoding: chunked — Burp uses it)
        status = self.rfile.readline().decode()
        self.chunked = False
        while True:
            line = self.rfile.readline().decode("utf-8", "replace").rstrip("\r\n")
            if line == "":
                break
            if "chunked" in line.lower():
                self.chunked = True
        if " 200" not in status:
            raise RuntimeError(f"SSE handshake failed: {status.strip()}")
        def http_bytes():
            """Yield the response BODY bytes, decoding chunked transfer coding."""
            if not self.chunked:
                while True:
                    b = self.rfile.read(1)
                    if not b:
                        return
                    yield b
            while True:  # de-chunk: <hex size>\r\n <size bytes> \r\n ... 0\r\n
                sizeline = self.rfile.readline()
                if not sizeline:
                    return
                s = sizeline.strip()
                if not s:
                    continue
                try:
                    size = int(s.split(b";")[0], 16)
                except ValueError:
                    continue
                if size == 0:
                    return
                remaining = size
                while remaining:
                    b = self.rfile.read(min(remaining, 4096))
                    if not b:
                        return
                    remaining -= len(b)
                    yield b
                self.rfile.read(2)  # CRLF after each chunk

        def pump():
            event, data = None, []
            buf = b""
            for b in http_bytes():
                buf += b
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    line = raw.decode("utf-8", "replace").rstrip("\r")
                    if line.startswith("event:"):
                        event = line[6:].strip()
                    elif line.startswith("data:"):
                        data.append(line[5:].strip())
                    elif line == "" and data:
                        payload = "\n".join(data)
                        if event == "endpoint":
                            self.endpoint_q.put(payload)
                        elif event in (None, "message"):
                            try:
                                self.msg_q.put(json.loads(payload))
                            except json.JSONDecodeError:
                                pass
                        event, data = None, []
        threading.Thread(target=pump, daemon=True).start()
        self.endpoint = self.endpoint_q.get(timeout=10)
        self.post_url = self.base.rstrip("/") + self.endpoint

    def _post(self, payload):
        req = urllib.request.Request(self.post_url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Accept": "application/json, text/event-stream"})
        urllib.request.urlopen(req, timeout=10).read()

    def rpc(self, method, params=None, id_=1, wait=True, timeout=20):
        msg = {"jsonrpc": "2.0", "id": id_, "method": method}
        if params is not None:
            msg["params"] = params
        self._post(msg)
        if not wait:
            return None
        while True:
            m = self.msg_q.get(timeout=timeout)
            if m.get("id") == id_:
                return m

    def initialize(self):
        self.rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "offsec-agent", "version": "1.0"},
        }, id_=0)
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def tools_list(self):
        r = self.rpc("tools/list", {}, id_=1)
        return [(t["name"], (t.get("description") or "")[:100]) for t in r.get("result", {}).get("tools", [])]

    def tools_call(self, name, arguments):
        r = self.rpc("tools/call", {"name": name, "arguments": arguments}, id_=2, timeout=60)
        return r.get("result", r)


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    cmd = sys.argv[1]
    if cmd == "history":
        from engagement import engagement_root
        in_scope = "--all" not in sys.argv[2:]
        cmd_history(str(engagement_root()), in_scope_only=in_scope)
        return 0
    mcp = SseMcp()
    mcp.initialize()
    if cmd == "tools":
        for name, desc in mcp.tools_list():
            print(f"{name:45s} {desc}")
    elif cmd == "call":
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        out = mcp.tools_call(sys.argv[2], args)
        print(json.dumps(out, indent=2)[:6000])
    return 0


def unwrap_response(text: str) -> tuple[str, str]:
    """Normalize the varying tool-result formats to (headers, body).
    Handles: raw HTTP text, and the Java 'HttpRequestResponse{httpRequest=..., httpResponse=..., messageAnnotations=...}' repr."""
    if "httpResponse=HTTP/" in text:
        i = text.find("httpResponse=") + len("httpResponse=")
        rest = text[i:]
        head, sep, body = rest.partition("\r\n\r\n")
        if sep:
            # body ends before ', messageAnnotations=' at top level — take until last occurrence
            j = body.rfind(", messageAnnotations=")
            if j != -1:
                body = body[:j]
            return head, body.rstrip("}")
        return rest, ""
    head, sep, body = text.partition("\r\n\r\n")
    if sep:
        return head, body
    return "", text


# ── history extraction ────────────────────────────────────────────────────────

def normalize_history_entry(item: dict) -> dict | None:
    """Normalize one proxy-history entry to the attack-surface feed format.
    Tolerant to response-shape variations; validated on first live run."""
    def g(*keys):
        for k in keys:
            v = item.get(k)
            if v is not None:
                return v
        return None
    req = item.get("request") or {}
    resp = item.get("response") or {}
    if isinstance(req, str):  # raw request text form
        first = req.split("\r\n")[0].split("\n")[0]
        parts = first.split(" ")
        method, path = (parts[0], parts[1]) if len(parts) >= 2 else ("?", "?")
        host_m = re.search(r"Host: ([^\r\n]+)", req)
        host = host_m.group(1).strip() if host_m else "?"
        status = re.search(r"HTTP/[\d.]+ (\d+)", item.get("response", "") if isinstance(item.get("response"), str) else "")
        return {"method": method, "host": host, "path": path,
                "status": status.group(1) if status else None,
                "request": req, "response": item.get("response")}
    url = g("url", "host") or "?"
    method = g("method") or "?"
    path = url.split("?")[0]
    sp = urlsplit(url if "://" in url else "//" + url)
    entry = {"method": method,
             "host": sp.hostname or url,
             "path": sp.path or "/",
             "query": sp.query or None,
             "status": g("status", "status_code", "responseStatusCode"),
             "request": req if isinstance(req, dict) else None,
             "response": resp if isinstance(resp, dict) else None}
    # parse query params into a list
    if entry["query"]:
        entry["params"] = [q.split("=")[0] for q in entry["query"].split("&") if q]
    if not item.get("url") and isinstance(req, dict):
        entry["params"] = list((req.get("query") or {}).keys()) or None
    return entry


def _decode_concatenated(text: str) -> list | None:
    """Decode one-or-more whitespace-separated JSON values (Burp's history tool
    returns the metadata header line followed by newline-concatenated objects,
    not a JSON array). Returns None if the text is not clean JSON values."""
    dec = json.JSONDecoder()
    items, i, n = [], 0, len(text)
    while i < n:
        while i < n and text[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        try:
            obj, i = dec.raw_decode(text, i)
        except json.JSONDecodeError:
            return None
        items.append(obj)
    return items


def _parse_history_items(text: str) -> list | None:
    """Extract history items from a tool response. Handles the optional
    '[Total: N | Returned: N | ...]' metadata header, a JSON array, and the
    newline-concatenated JSON-object stream Burp actually returns."""
    text = text.strip()
    # Burp returns a plain human sentence when nothing matches (not an error).
    if re.match(r"(?i)^no items? found", text):
        return []
    if text.startswith("["):
        nl = text.find("\n")
        head = text if nl == -1 else text[:nl]
        if re.match(r"^\[\s*Total:", head):
            text = text[nl + 1:].strip() if nl != -1 else ""
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = _decode_concatenated(text)
        if parsed is None:
            return None
    if isinstance(parsed, list):
        return parsed
    return parsed.get("data") or parsed.get("items") or parsed.get("history")


# Static/non-testable extensions dropped from the surface feed (unexploitable noise:
# images, fonts, scripts, media, PDFs). Requests to these are almost never the bug.
STATIC_EXT = {"js", "css", "png", "jpg", "jpeg", "gif", "svg", "ico", "woff", "woff2",
              "ttf", "otf", "eot", "map", "webp", "avif", "bmp", "mp4", "webm", "mov",
              "mp3", "wav", "ogg", "pdf", "zip", "gz"}


def _path_ext(path: str) -> str:
    last = (path or "").rsplit("/", 1)[-1]
    return last.rsplit(".", 1)[-1].lower() if "." in last else ""


def _host_allowed(cfg: dict, host: str) -> bool:
    try:
        from scope_check import check_target
        return bool(check_target(cfg, host).get("allowed"))
    except Exception:
        return False


def cmd_history(eng_dir: str, in_scope_only: bool = True) -> None:
    """Pull proxy history into <eng>/proxy-history.jsonl (the attack-surface feed).
    Pagination is count/offset (page/number silently fails). Empty history is valid.

    Smart filter (default; disable with --all): Burp's OWN target scope is often unset,
    so we fetch everything and apply OUR authoritative scope.yaml instead — dropping
    out-of-scope hosts (analytics/telemetry/third-party) and static-asset extensions."""
    mcp = SseMcp(); mcp.initialize()
    out_path = os.path.join(eng_dir, "proxy-history.jsonl")
    cfg = None
    if in_scope_only:
        try:
            from scope_check import load_scope
            from engagement import scope_file
            cfg = load_scope(str(scope_file()))
            print("filter: scope.yaml + static-extension drop (use --all for raw history)")
        except Exception as e:
            print(f"scope filter unavailable ({e}); writing unfiltered history")
    count, offset, seen, written, skipped = 100, 0, set(), 0, 0
    with open(out_path, "w") as f:
        while True:
            r = mcp.rpc("tools/call", {"name": "get_proxy_http_history",
                "arguments": {"count": count, "offset": offset, "inScopeOnly": False,
                              "newestFirst": False, "maxItemLength": 200000}},
                id_=offset + 100, timeout=120)
            res = r.get("result", {})
            if res.get("isError"):
                print(f"tool error: {json.dumps(res)[:200]}"); break
            text = "\n".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
            items = _parse_history_items(text)
            if items is None:
                print(f"offset {offset}: unparseable response ({len(text)} chars) — parser needs a fix for this format")
                print(text[:600])
                break
            if not items:
                break
            new = 0
            for it in items:
                key = json.dumps(it, sort_keys=True)[:300]
                if key in seen:
                    continue
                seen.add(key)
                e = normalize_history_entry(it)
                if not e:
                    continue
                if cfg is not None:
                    if not _host_allowed(cfg, e.get("host") or ""):
                        skipped += 1
                        continue
                    if _path_ext(e.get("path") or "") in STATIC_EXT:
                        skipped += 1
                        continue
                f.write(json.dumps(e) + "\n")
                written += 1
                new += 1
            print(f"offset {offset}: {len(items)} entries ({new} kept)")
            if len(items) < count:
                break
            offset += count
    tail = f", {skipped} filtered (out-of-scope/static)" if cfg is not None else ""
    print(f"\nwritten: {written} entries -> {out_path}{tail}")
    print("next: the attack loop reads this file as the attack surface.")


if __name__ == "__main__":
    sys.exit(main())
