---
key: THE-7958-EXEMPLAR-DEPENDS-ON-THE-GATE-INVENTORY
claim: "tests/test_merge_on_green.py's incident-7958 exemplar asserts that its fixture owns NO path-filtered gate; any new ci.yml trigger that covers the fixture's paths breaks the test BY DESIGN and the test says to re-exemplar rather than widen."
falsifier: "`python3 -m pytest tests/test_merge_on_green.py -k incident_7958 -q` passing while a fixture path is covered by a ci.yml `paths:` glob (check with `git grep -n agentos/handoffs .github/workflows/ci.yml`)."
so_what: "When adding a path-filtered gate, check the 7958 fixture first; if it collides, re-point the fixture at genuinely ungated files (handoff-only, as R4 #8287 cb6656f0 did) and keep the trigger."
kind: landmine
verified_at: 2026-10-02
verified_by: "#8287 R3 ci-pack-0 red on test_incident_7958_* after the mockups/evidence/** trigger landed; R4 head cb6656f0369c re-exemplared to two agentos/handoffs files (+14/-7) and the pack greened"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "tests/test_merge_on_green.py"
  - ".github/workflows/ci.yml"
confidence: verified
---

The exemplar guards a real property (records-only PRs run no pack gates). Keeping it honest costs one fixture edit per new gate; whitelisting would make it vacuous.
