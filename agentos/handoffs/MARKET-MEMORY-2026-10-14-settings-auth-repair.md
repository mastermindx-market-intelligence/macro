---
workstream: "WS:MARKET-MEMORY-W2C"
session: claude/ssd-market-memory-oauth-entry-repair-01a1333c-da70fc3e9127bec5
model: codex
ended_because: ci_handoff
mission: Complete the original Market Memory program including exact-source browser and authentication journeys.
state_before: Actual Google callback from Settings restored an older SPY capsule and lost all nine exact source keys.
changed:
  - path: templates/market_memory_retained.js
    what: Bind saved responses to the exact packet digest, permitting gzip/zstd suffixes only when matching actual Content-Encoding.
  - path: templates/theme.js
    what: Capture current valid Market Memory intent before every global onboarding entry and reject ambiguous stale-intent reuse.
verified:
  - claim: The regression is discriminated and repaired for both loaded and lazy sign-in paths.
    command: node --test tests/js/market_memory_auth_return.test.cjs
    result: Baseline17pass5fail; repair22pass0fail. Includes lazy error, timeout and duplicate reference refusal.
  - claim: Affected page and asset contracts are preserved.
    command: python3 -m pytest tests/test_build_market_memory_page.py tests/test_site_assets.py -q
    result: 32passed.
unverified:
  - claim: Actual Google return preserves the exact saved source after release.
    what_would_verify: Installed repaired bytes and actual provider return preserving all nine keys and opening the source.
unresolved:
  - Actual saved response now returns200, but compression-suffixed ETag fails the released frontend binding; this carrier also repairs that exact contract.
  - Independent read diagnostics proceed in PR9298; no live latency resolution is inferred.
next_actions:
  - Complete protected merge and installed-byte verification, then repeat the actual provider journey.
  - Continue original28task49case program; preserve research admission and original Fabric recovery carriers.
do_not_redo:
  - Preserve prior accepted issuer intent behavior and accepted August study outcomes.
danger_areas:
  - Synthetic callback and fixture browser tests do not replace actual authenticated provider proof.
prs: [6528, 9228, 9281, 9295, 9298, 9300]
---

See research/MARKET_MEMORY_SETTINGS_AUTH_REPAIR_2026-10-14.md.
