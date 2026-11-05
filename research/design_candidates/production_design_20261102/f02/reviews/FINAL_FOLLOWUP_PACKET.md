# Narrow follow-up after the candidate 2 repair review

This pass addresses exactly two new minor findings from the frozen repair review:

- **PRC-010:** Options cells bypassed the advertised density token. The source now uses `height:var(--row)` for desktop cells and `height:max(52px,var(--row))` for phone cells. The Comfortable phone token is 64px. Desktop policy is 40/52px; narrow Options policy is at least 52/64px. Intrinsic content may make cells taller, so these declarations are not measured rendered heights. The SYSTEM_CONTRACT spacing paragraph matches the repaired policy.
- **VTC-007:** The narrow static table lacked an initial cue that additional columns existed. A concise horizontal-scroll/coverage hint is placed before the first row in the 390px English and Chinese frames and the combined mobile plate. Table/row/inspector geometry is retained.

The candidate 2 repair commit `1253a647d193e1eacd1eb6f523a7a031529d2150` and its 53-file manifest remain immutable historical evidence. The current set has its own exact manifest and commit. Neither original first-pass, rationale-pass nor repair-pass review is rewritten.

Review only the changed source/drawing surface and its precise binding. Product review should determine whether PRC-010 is resolved as a source policy, leaving real density rendering and all PRC-007/runtime/integration requirements open. Taste review should determine whether VTC-007 is resolved in the static frames and whether the hint overlaps adjacent content. No broad re-audit, browser bypass, Paper edit or new service operation is requested.

Return a separate final-followup report with UTC freeze, exact current set hash and scoped finding disposition. Keep the adoption verdict and mandatory remaining gates explicit.
