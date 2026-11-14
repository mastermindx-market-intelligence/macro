---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: claude/codex-limits-viewer-20261003-sol-001
model: sol
ended_because: ci_handoff
mission: >
  Make the existing Codex admin view accurately display provider window duration,
  actual reset deadlines and permission evidence without inventing execution authority.
state_before: >
  The renderer labelled all primary windows as five-hour and all secondary windows
  as weekly, hid over-100 measurements and omitted provider permission and timestamps.
changed:
  - path: admin/static/app.js
    what: Only the existing Codex usage-render block changes; controls, other panels and requests remain unchanged.
  - path: tests/test_admin_codex.py
    what: Execute the actual shipped renderer with the existing backend projection and synthetic data in Node VM.
verified:
  - claim: New tests discriminate the original misleading display.
    command: pytest --noconftest tests/test_admin_codex.py -k TestCodexUsageRenderer
    result: All twelve new cases failed on original production source before implementation.
  - claim: Actual renderer and existing backend projection preserve native meaning.
    command: pytest tests/test_admin_codex.py with normal repository setup and isolated basetemp
    result: 67 passed; includes the twelve actual-renderer cases. Fake API observes exactly one read and refuses modifying calls.
  - claim: No production function outside the Codex usage block changed.
    command: Compare exact source prefix and suffix around the existing Usage and Run-now markers; node --check; git diff --check.
    result: Prefix and suffix identical; JavaScript syntax and whitespace pass.
unverified:
  - claim: The current code is browser-qualified and deployed on the authenticated live admin route.
    what_would_verify: Exact-head review and hosted gates, browser layout/interaction evidence and existing authorized deployment with real account observations.
unresolved:
  - Full all-account identity/enrollment and reset execution remain with existing Provider Control and Executive owners.
  - Source review and hosted code-gate execution remain pending; no source release or live adoption is asserted.
  - Local browser CLI preflight was unavailable and one container npm lookup timed out with EAI_AGAIN; no process remained. This is not a host permission denial.
next_actions:
  - Publish the original source branch, independently review the usage-only delta and verify exact-head checks before release.
  - Verify browser presentation on an isolated fixture without using account credentials or modifying controls.
  - Preserve original8255 formal-review and8311 source/release obligations; no gate is waived by this display repair.
do_not_redo:
  - Do not infer short versus weekly windows from primary versus secondary position.
  - Do not clamp displayed over-100 usage or claim that a passed timestamp automatically grants new quota.
  - Do not replay held7116, denied consumer-bridge/CI-manifest actions or original633 effects.
danger_areas:
  - This remains the existing single-lane viewer, not an authenticated all-account dashboard or a global quota controller.
  - Reset countdowns are render-time views of provider deadlines, not a new scheduler, background timer or banked-credit ledger.
---

Source base92856b75808a4935bf23163e922bd304ac93e4dd; protected Mastermind
procedure3959aad974f15760ad7a53ab2d7a7ddfcd864ae2. Current outer Chairman
continuation includes the original limits-viewer outcome. Source isolation is the
existing Macro .claude/worktrees convention; no shared checkout was changed.
The Sol model label is organizational role, not served-model attestation.

Bounded current PR census found no Codex usage-renderer modifier. Older7992 also
touches app.js but only overview/system disk presentation; its actual patch is
outside this function and it retains its own source. No old branch was reclaimed.
The complete first200-PR census and large-PR checks are bounded evidence, not a
claim that all historical open PRs or every worktree were scanned.

Unknown duration is labelled unknown. Reset dates and observation timestamps use
UTC; elapsed deadlines require fresh data, not assumed full capacity. Provider
false/null/absent/true states stay distinct and never grant execution. Over-100
numeric labels remain exact while only bar geometry is clamped. Invalid numeric
and timestamp values are not rendered as healthy capacity or unescaped HTML.
Only the existing usage fragment changes; mode/run controls and all other panels
remain byte-identical.

Evidence: /Volumes/Mastermind/evidence/codex-limits-viewer-20261003-sol-001.
The first complete-suite attempt exposed only a missing app package in the sparse
checkout; adding existing app/lib source repaired that harness without code or
test changes. The original failing log is retained. Parent mission is incomplete.
