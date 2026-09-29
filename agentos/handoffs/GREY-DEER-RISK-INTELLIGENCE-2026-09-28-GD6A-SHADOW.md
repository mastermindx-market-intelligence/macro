---
workstream: WS:GREY-DEER-RISK-INTELLIGENCE
session: claude/gd6a-us-shadow-intake-20260928
model: sol
prs:
- 8141
ended_because: ci_handoff
mission: Bind named new-long restrictions into the native candidate-card presentation.
  MISSION_COMPLETE:false; no production resolver, page-loop or delivery adoption.
state_before: R11 published the dispositions but the shared card had no separate effective
  restriction presentation.
changed:
- path: engine/prophet_market_eligibility.py
  what: Source-bound serializable card-context helper; no new endpoint or grant.
- path: templates/_prophet_card.html.j2
  what: Read the explicit context, replace Buy with paused/unavailable, retain research
    and reference levels.
- path: tests/test_prophet_market_eligibility.py
  what: 18 native-template and bound-context cases in existing selected file.
- path: research/grey_deer/GD6A_BOUND_CANDIDATE_CARD_2026-09-29.md
  what: Actual consumer proof, precise refused lanes and remaining page/send integration.
verified:
- claim: Source-bound native rendering distinguishes paused from unavailable and retains
    research context.
  command: python3.12 -m pytest tests/test_prophet_market_eligibility.py tests/test_prophet_market_eligibility_native.py
    tests/test_prophet_market_eligibility_publication.py tests/test_prophet_bridge.py
    -q
  result: 266 passed/79 subtests; 18 new card cases; no real grants or notifications.
    log 5f9988af6c55efb413bcaf8a096455d752d071b7fd414b1cb5a3147c37ec14fa.
- claim: The new shared-renderer connection is discriminating.
  command: python3 release-r12/verify_render_connection.py
  result: Disconnecting only policy consumption raises the intended assertion; source
    restored.
unverified:
- claim: Existing page/API/hydration/notification callers use the bound helper.
  what_would_verify: Permitted native-source adoption plus current-board rendered/API
    receipt and send-time permission proof.
- claim: Current source release and arbitrary untrusted-template-context hardening.
  what_would_verify: Exact new-head/current-base CI, genuine blocked-action recovery,
    stronger validation where required and actual ordinary refresh.
unresolved:
- The delivery-drain helper inspection and page-loop/render-helper inspection were
  refused before dispatch; no split/retry/proxy.
- The extra defensive-shape and old-render comparison operation was refused and not
  applied; only native-helper-generated context is supported.
- Production policy grant/source, caller adoption, independent alarm and live delivery
  proof remain absent.
next_actions:
- Consume new-head CI and preserve the original carrier.
- After genuine permission recovery, connect the actual page/API loop to the bound
  view and prove current-board output.
- Finish the existing delayed-buy sender permission check without changing effect-unknown
  ownership.
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

# R12 native card consumer

MISSION_COMPLETE:false. Source only, not production activation or automatic continuation.
