---
key: RRU-RANK-COMPARISON-NEEDS-REFERENCE-COMPOSITION
claim: >
  Complete derived-input membership in the latest 30 ranked observations does
  not establish comparable membership in their trailing 504-observation rank
  reference populations. The prior composition candidate allowed that false
  comparison across all ten international profiles in controlled synthetic cases.
falsifier: >
  Run python3 research/grey_deer/RRU_REFERENCE_WINDOW_TESTS_2026_09_09.py against
  candidate head92193b4 versus the amended helper. If inside-reference missing
  members and all-null dates do not distinguish the flags while outside-window
  controls remain allowed, the claimed mechanism or repair is not established.
so_what: >
  Preserve the existing 30-observation recovery comparison, but qualify its
  reference union using the canonical finite-raw-observation rank window.
  Keep current coverage, reference coverage, feed freshness and calibration separate.
kind: landmine
verified_at: 2026-09-09
verified_by: >
  research/grey_deer/RRU_REFERENCE_WINDOW_RED_2026_09_09.txt;
  research/grey_deer/RRU_REFERENCE_WINDOW_GREEN_2026_09_09.txt;
  engine/risk_radar_intl.py:_pct and engine/indicators.py:pct_rank_window at eb9e919.
scope: ["WS:GREY-DEER-RISK-INTELLIGENCE", "engine/risk_radar_intl.py", "engine/risk_radar_recovery.py"]
confidence: verified
---

The original 30-case suite produced20 expected assertion failures and10 controls.
The amended in-memory helper produced30/30 passes and preserved actual source bytes.
Those cases execute the actual producer, projection and existing unavailable-recovery
rendering with synthetic inputs. They are not ten historical market validations.

An attempted extra exact-adjacent-boundary test edit/run was platform-blocked. Direct
read found the original three-case-per-profile test unchanged; no retry followed.
No 50-case, exact-adjacent-boundary or required-reference-count assertion proof is claimed.
The receipts report the new counts; independent off-by-one and raw-feed-vintage review
remain owed. Production, calibration and the two construction-authority gaps are unchanged.
