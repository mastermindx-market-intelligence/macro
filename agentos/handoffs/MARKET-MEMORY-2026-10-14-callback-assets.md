---
workstream: "WS:MARKET-MEMORY-W2C"
session: claude/ssd-market-memory-oauth-callback-01a1333c-2482aa4f7ed5b106
model: codex
ended_because: ci_handoff
mission: Deliver the original Market Memory program and its real customer workflow.
state_before: Real OAuth returned without the exact source because its intent script received pre-session HTTP401.
changed:
  - path: config/site_access.yml
    what: Declare three UI-only Market Memory assets public using the existing canonical policy.
  - path: app/deploy/Caddyfile
    what: Keep all four registration and cache matchers in sync for those three exact assets.
verified:
  - claim: The missing callback-asset boundary is reproduced and repaired locally.
    command: python3 -m pytest tests/test_site_access_boundary.py -k 'market_memory_callback_assets or caddy_public_boundary or immutable_cache_list' -q
    result: Initial regression failed; repaired3passed. Adjacent registration, saved API, catalog and upstream boundary checks89passed.
unverified:
  - claim: The actual Google return preserves every exact source field.
    what_would_verify: Protected merge, installed edge policy and a real same-account OAuth return with all nine fields equal.
unresolved:
  - Brain synthesis provider refresh401 is separate; do not retry or switch credentials/providers.
  - Original four Fabric recovery operations and A0 controller keep their same carriers.
next_actions:
  - Complete protected CI and merge; verify installed policy and actual OAuth journey.
do_not_redo:
  - Preserve accepted August ABSTAINED and STOPPED results and frozen E0 membership109.
danger_areas:
  - UI asset availability never grants evidence API access, study admission or source rights.
prs: [6528, 9300]
---

Real evidence is retained under /Volumes/Mastermind/evidence/market-memory-20261012-01a1333c/integration/.
