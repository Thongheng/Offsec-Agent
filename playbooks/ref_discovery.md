# Reference — discovery engine

Runnable techniques over a JSON spec. All sends go through the scope-enforced transport
and are rate-limited to `roe.max_requests_per_second`.

## outlier — the anti-"uniform = hardened" tool
Fire a family of requests expected to behave identically; flag the deviators. Use it
after a sweep: a uniform denial is not a hardening verdict, it is the signal to find the
exception (LEARNINGS L-16).

```json
{"requests": [
  {"label": "item-A", "method": "GET", "url": "https://app.box.com/app-api/item/d_1"},
  {"label": "item-B", "method": "GET", "url": "https://app.box.com/app-api/item/d_2"}
]}
```
```
offsec run outlier --spec spec.json
```

## authz_matrix — two identities across objects
Flags cells where a denied context gets what the owner got.

```json
{"baseline": {"label": "owner", "headers": {"Cookie": "z=B"}},
 "contexts": [{"label": "other", "headers": {"Cookie": "z=A"}}],
 "cells": [{"element": "item", "url": "https://.../item/d_1", "expect": "deny"}]}
```
```
offsec run authz_matrix --spec spec.json
```

## lifecycle — create -> read-as-other -> update -> delete -> side effects
The premium authz shape (move/copy, share/unshare, ownership transfer, trash/restore).
```json
{"steps": [
  {"name": "create", "method": "POST", "url": "...", "headers": {"Cookie": "z=B"}, "body": "{}", "expect": {"should": "succeed"}},
  {"name": "read-as-other", "method": "GET", "url": "...", "headers": {"Cookie": "z=A"}, "expect": {"should": "fail"}}
]}
```
```
offsec run lifecycle --spec spec.json
```

## seam — UI vs API (pure, no network)
```
offsec run seam --spec seam.json      # {"captured": "...", "synthesized": "..."}
```
Flags client-only headers/fields and body fields the server may not require.

## Reading the output
- `outlier: true` — investigate first.
- `authz_matrix` `flaw: true` — a denied context succeeded where the owner did.
- `lifecycle` `deviation: true` — the step did not behave as the intended contract.
- `seam_flags` — each is a hypothesis: test whether the server enforces it.
