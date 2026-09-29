---
workstream: WS:GREY-DEER-RISK-INTELLIGENCE
session: claude/gd6a-us-shadow-intake-20260928
model: sol
prs:
- 8141
ended_because: ci_handoff
mission: Implement explicit named new-long restriction in native Prophet origination;
  preserve research and existing-position semantics. MISSION_COMPLETE:false; no production
  activation.
state_before: Zero-policy shadow was connected, but native origination had no explicit
  parameter for a named authorized market restriction.
changed:
- path: engine/prophet_market_eligibility.py
  what: Immutable internal individually pinned rule read; no grants or production
    config.
- path: engine/prophet_bridge.py
  what: Enforce named deny/unavailable disposition after admission/duplicates and
    before plan construction; disclose suppression count and reasons.
- path: tests/test_prophet_market_eligibility.py
  what: 19 named-policy and actual-native-origination tests in the already registered
    suite.
- path: research/grey_deer/GD6A_NAMED_POLICY_CONSUMPTION_2026-09-29.md
  what: Proof, trusted-source prerequisites, explicit nonactivation and remaining
    builder/alert contract.
verified:
- claim: Actual native origination enforces broad/scoped restrictions without changing
    the source board.
  command: python3.12 -m pytest tests/test_prophet_market_eligibility.py tests/test_prophet_market_eligibility_native.py
    -q
  result: 88passed/61subtests; two control plans become zero under named broad restriction;
    scoped control plan unchanged. Pass log b9600fa81e6bc60d83cbb1971930fc74b5e603383cbd0b3c53f0f607e2db2b3a.
- claim: The native enforcement test catches removal of the deny condition.
  command: python3 release-r10/qualify_policy_seam.py
  result: Intentional assertion failure, then original restored; no production action.
unverified:
- claim: Production caller and all-channel adoption.
  what_would_verify: Accepted rule/grant source; builder/index/alarm balance update;
    actual API/UI/buy-send enforcement; preserved research and ordinary refresh.
- claim: New source release.
  what_would_verify: Concluded applicable new-head CI, permitted current-base qualification
    and explicit release acceptance.
unresolved:
- Ordinary builder does not supply the new arguments; no live policy was installed.
- The new suppression category must be propagated before adoption; no legacy-balance
  bypass.
- Current-base comparison and separate builder/test-helper reads were refused; no
  repeat or proxy.
next_actions:
- Qualify this changed head, then complete existing builder/index/notification adoption
  under actual accepted rule/grant source.
- Retain zero live-policy claims until actual channel and ordinary-refresh proof.
- Do not expand into further adjacent integrity cleanup.
do_not_redo:
- Do not recreate GD-6A or add a second risk policy, identity, registry, collector,
  ledger or publisher.
- Do not repeat CI registration; it landed in69601edd13829d6a32a5a51ffa07e781ff314ef3.
- Reuse unchanged source tests appropriately; preserve GD-2/GD-3 and merged B4 source-session
  proofs.
- Preserve H1/Cycle, Seat B's source custody and the original CEO's UI release.
danger_areas:
- ELIGIBLE remains a zero-policy shadow observation, not buy permission; all eight
  action flags stay false.
- A fresh summary does not qualify an undated optional contributor. Missing evidence
  cannot erase research or invent liquidation.
- Descriptor checks cover the opened regular file; independent owner hashes, source
  scope and validity remain mandatory.
- No status-read denial, readonly ingress or new chat transfers custody or authorizes
  a proxy retry.
---

# R10 native enforcement seam

Source implementation only; MISSION_COMPLETE:false. No new registry, grant, worker or trade.
