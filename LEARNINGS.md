# Methodology learnings

Lessons from real engagements that change how the kit works. Entries here are promoted
into `prompts/*.md` and `AGENTS.md` as they're validated. Newest first.

## L-1 (2026-09-07, basecamp engagement) — The threat-model menu is a starting point, never a cap

**What happened:** audit plans were built from the initial ≤5-class threat-model menu, and
testing followed the menu. Real targets reveal hypotheses *during* testing — a redirect
parameter here, a user-input sink there — that the menu never listed.

**Rule (now in attack-loop.md):**
1. The menu seeds the hunt; it does not bound it.
2. Every observed flow, parameter, and request body gets its own class check at the moment
   it's observed — open redirect params, reflection/XSS sinks, upload handling, IDOR-shaped
   ids — regardless of menu membership. Low-hanging fruit is always in scope.
3. New classes discovered this way are logged as decisions and folded back into the
   engagement's threat model.
4. When a rule in these prompts fails or underperforms in practice, record it here and
   update the prompt — the methodology is versioned by use, not by fiat.
