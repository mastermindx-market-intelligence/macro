---
workstream: WS:GREY-DEER-RISK-INTELLIGENCE
session: cursor-6685-canonical-regen-20260908
model: local
ended_because: blocked
prs:
- 6685
mission: >
  Honor Sol HOLD 5580065094 on the 20edb97 integrated head and supply the
  missing canonical builder/asset-processing receipt for site/macro.html
  without redesigning the accepted compact-risk rail.
state_before: >
  PR 6685 was DRAFT/HOLD after Sol converted it. merge-on-green was already
  disarmed. The 20edb97 merge had changed site/macro.html by conflict splice;
  no current-candidate render receipt existed.
changed:
- path: site/macro.html
  what: Canonical macro-target rewrite through build_site.write_page, then normal
    externalize + optimize. Compact public Risk context rail preserved.
- path: mockups/refs/grey-deer-compact/sol-20260908/
  what: Current-candidate receipts, browser/live/settled fixtures, and identities.
verified:
- claim: Real builder wrote the macro target, then official asset processing produced the final page.
  command: python3 mockups/refs/grey-deer-compact/sol-20260906/build_macro_target.py; python3 mockups/refs/grey-deer-compact/sol-20260908/postprocess_macro_target.py
  result: Raw SHA256 1490abc9…; final SHA256 057628471cac5296d781a8e711ecc9ad9a53839cd34d3d047ada7318fb8e5cf7 / blob 40ce682d4c95ed5dc14b7bc0b06140413ae5c863. Not a full-site success.
- claim: Owning and adjacent suites pass on the regenerated page.
  command: python3 -m pytest tests/test_risk_envelope_presentation.py tests/test_risk_envelope.py tests/test_live_risk_envelope.py tests/test_risk_state_live_session_floor.py tests/test_synapse_read_gate.py tests/test_horizon_firewall.py tests/test_delivery_waterfall.py tests/test_pricing_power_monitor.py -q
  result: 302 passed, 0 skipped.
- claim: Anonymous public explanation and member boundary hold across the required matrix.
  command: python3 mockups/refs/grey-deer-compact/sol-20260908/verify_browser.py; python3 mockups/refs/grey-deer-compact/sol-20260908/verify_live_context.py; python3 mockups/refs/grey-deer-compact/sol-20260908/verify_settled_states.py
  result: 12/12 page cases, 7/7 live fixtures, 16/16 settled fixtures PASS. Local, not production.
unverified:
- claim: Sol releases this new semantic head and current-base hosted CI concludes clean.
  what_would_verify: Explicit Sol release of the new head plus concluded binding checks.
- claim: Production users see the compact rail.
  what_would_verify: Normal publication after release, then a live production browser receipt.
unresolved:
- HOLD-FOR-SOL remains until Sol releases the new head. Do not merge or arm merge-on-green.
- A push of this regeneration starts a new natural CI run; it does not prove the spliced 20edb97 page.
next_actions:
- Push the regenerated site/macro.html plus sol-20260908 receipts on the existing branch only.
- Post one exact-carrier RESULT / HOLD-FOR-SOL on PR 6685 naming the new head, SHA256, and local proof.
- Leave the PR DRAFT with no merge-on-green and no native auto-merge until explicit Sol release of the new head.
- Watch the natural current-head CI; do not cancel, rerun, or dispatch over an in-flight run.
do_not_redo:
- Stay on PR 6685 / claude/gd-compact-risk-context-20260830. No replacement PR.
- Do not restore the Three Reads panel, hide nulls, or hide the settled clock.
- Do not cancel the forbidden production lanes or arm merge-on-green under the hold.
danger_areas:
- The builder writes other pages before the macro-target stop. Restore them; never
  describe the harness exit as a successful full-site build.
- Historical September 6 SHA256 b63e24b1… is not this artifact.
---
