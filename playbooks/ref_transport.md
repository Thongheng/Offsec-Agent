# Reference — transport

Two transports; pick by purpose, do not route everything through one.

- **Burp** (`offsec/transport/burp.py`, `python3 -m offsec.transport.burp`, MCP at
  `127.0.0.1:9876`) — browser-originated or
  human-visible traffic: refresh the surface feed, replay captured requests, anything the
  human should watch in Repeater. Agent `send_*` calls do NOT populate Proxy history
  (LEARNINGS L-6); set scope in OUR tool, not Burp's.
- **Script / transport** (`offsec/transport/http.py`, and the discovery engine) —
  handcrafted probes, recon sweeps, volume. One process, no MCP round-trip per request,
  and a TLS fingerprint that is not Burp's (which bot management challenges).

Every `transport` send enforces the scope gate on the host actually connected to and
rate-limits to `roe.max_requests_per_second`. Redirects are not followed silently — the
3xx is often the evidence (SSRF, open redirect, signed-URL analysis).

**Get the contract from the JS, not the clicks.** Read the call-sites in bundles to
recover method/path/body/params/headers/GraphQL `operationName`, then synthesize the request.
Use a browser only when a request genuinely cannot be derived — and then capture the real
request from Burp history rather than replaying DOM interactions (LEARNINGS L-16).
