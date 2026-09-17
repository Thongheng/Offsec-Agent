# Prompt: Using Burp MCP (`tools/burp_mcp.py`)

Reference for driving Burp Suite through the local MCP server. Verified against the
server source (`/Users/thonghengheu/Coding/burp-mcp-server`, Tools.kt) and live use.

## Running it

```bash
python3 tools/burp_mcp.py tools                # list available Burp tools
python3 tools/burp_mcp.py call <tool> '<json args>'
python3 tools/burp_mcp.py history              # in-scope proxy history → proxy-history.jsonl
python3 tools/burp_mcp.py history --all        # full history, no scope filter
```

Requires Burp running with the MCP Server extension enabled (port 9876). Each invocation
opens its own MCP session — that's fine.

## Approval prompts (first use — the human must click in Burp)

- **History/Organizer reads**: Burp pops `Allow Once / Always Allow <type> / Deny`.
  Recommend the human picks "Always Allow HTTP history" for the engagement.
- **HTTP request sends**: first request to each host pops
  `Allow Once / Always Allow Host / Always Allow Host:Port / Deny`.
  Auto-approve targets persist in Burp config.
- Config-editing tools are gated behind a checkbox in Burp's MCP tab.

## Tool catalog (28 tools, grouped)

**Send requests** (the attack primitives):
- `send_http1_request` — args: `content` (raw HTTP request), `targetHostname`, `targetPort`, `usesHttps`. ALL FOUR REQUIRED (omit target fields → error).
- `send_http2_request` — args: `pseudoHeaders` (map incl. `:method` `:path` `:authority`), `headers` (map), `requestBody`, + target fields. Do NOT pass headers in the body.
- `create_repeater_tab` / `create_repeater_tab_http2` — same inputs + optional `tabName`; creates a visible Repeater tab so the human can watch/edit.
- `send_to_intruder` — for the human's manual fuzzing; don't use for agent loops.

**Read history** (the attack-surface feed):
- `get_proxy_http_history` — pagination is `count` + `offset` (NOT page/number). Filters: `newestFirst`, `inScopeOnly`, `hosts[]`, `methods[]`, `statusCodes[]`, `excludeExtensions[]`, `mimeTypes[]`, `highlightColor`, `hasHighlight`, `editedOnly`. Response may start with a `[Total: N | Returned: N | ...]` metadata header — skip it.
- `get_proxy_http_history_regex` — regex over raw request+response content, same filters + `caseInsensitive`. Use for "find every request mentioning X".
- `get_proxy_history_count` — total items (call before paginating).
- Organizer: `get_organizer_items` / `get_organizer_items_regex` / `get_organizer_count` — the HUMAN's saved/annotated requests. Always check Organizer: what the human bookmarked is what they found interesting.
- WebSocket: `get_proxy_websocket_history` (+count/regex).

**OOB (Collaborator, Burp Pro)**:
- `generate_collaborator_payload` — payload URL for out-of-band tests (SSRF, blind XSS).
- `get_collaborator_interactions` — poll for DNS/HTTP/SMTP callbacks. Essential for blind-XSS/SSRF confirmation.

**Config & control**:
- `get_scanner_issues` / `get_scanner_issue_count` (Pro) — scanner findings.
- `output_project_options` / `set_project_options`, `output_user_options` / `set_user_options` — config read/merge (JSON, top-level `project_options`/`user_options`).
- `set_task_execution_engine_state`, `set_proxy_intercept_state`, `get/set_active_editor_contents`.
- Utilities: `url_encode/decode`, `base64_encode/decode`, `generate_random_string`.

## Gotchas (all hit live)

1. **Pagination is `count`/`offset`** — the page/number style silently fails. hacktivity of history may return fewer rows than requested; loop on offset until empty.
2. **Responses are wrapped** in `HttpRequestResponse{httpRequest=..., httpResponse=..., messageAnnotations=...}` sometimes — use `unwrap_response()` from this module to get (headers, body).
3. **Duplicate Content-Length headers → Cloudflare 400.** When building requests, set Content-Length exactly once.
4. **SSE parsing**: server sends `event: endpoint` then `event: message` (or bare `data:`) — see the client's pump. Chunked transfer decoding is handled.
5. **The server normalizes literal `\r\n` escapes in the request prelude** — but bodies stay verbatim, so don't rely on it for bodies.
6. **Approvals**: the human must approve hosts/data-access in the Burp UI. If a call seems to hang, a dialog is probably waiting in Burp.
7. In-scope discipline: prefer `hosts` filters from `scope.yaml` when pulling history; requests via `send_http*` are the human's responsibility to approve — only request in-scope hosts.

## Hunt-loop usage patterns

- **Surface feed**: `history` command → `proxy-history.jsonl` → attack loop reads it.
- **Targeted search**: `get_proxy_http_history_regex` with `hosts` + regex for a parameter name or marker — fastest way to find every request touching a feature.
- **Role matrix**: pull A-session and B-session history separately (filter by nothing — jars are separate in Burp's history), diff the endpoint sets.
- **OOB confirmation**: `generate_collaborator_payload` → embed in a PoC → `get_collaborator_interactions` for callback proof.
