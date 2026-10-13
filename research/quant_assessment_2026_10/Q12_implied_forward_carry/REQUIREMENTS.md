# Q12 acceptance requirements — traceability

Module: `engine/options_parity_forward_interval.py` (RESEARCH_ONLY = True, VERDICT =
"INSUFFICIENT_DATA"). Tests: `tests/test_options_parity_forward_interval.py`. All tests are
hermetic, use synthetic integer clocks and read no files.

| # | Requirement | Implementation | Tests |
|---|---|---|---|
| req1 | Pair identity includes deliverable/settlement | `IDENTITY_FIELDS` = underlying, expiry, strike, deliverable, multiplier, settlement, exercise, deliverable_standard. `check_pair` names each mismatched field. A nonstandard (OCC-adjusted) deliverable returns unavailable. | `test_req1_pair_identity_includes_deliverable_and_settlement` (6 params), `test_req1_nonstandard_deliverable_is_unavailable` |
| req2 | European synthetic controls recover the known interval | `pair_forward_interval` = [K+(C_bid−P_ask)/D, K+(C_ask−P_bid)/D] over a D band. It recovers [100.83673469387755, 101.16326530612245] at D = 0.98, F = 101. | `test_req2_european_synthetic_control_recovers_interval`, `test_req2_multi_strike_intersection_contains_truth_and_discount_band_widens`, `test_dband_point_band_equals_plain_intersection` |
| req3 | Crossed/stale/async quotes cannot manufacture precision | Pairs that are crossed, locked, stale, future-stamped, asynchronous, non-finite or bad-priced are rejected with named reasons, before any interval is formed. | `test_req3_crossed_quote_rejected`, `test_req3_locked_stale_async_future_rejected`, `test_req3_bad_pair_cannot_narrow_a_good_estimate` (5 params: stale, future, async, crossed, locked) |
| req4 | Incompatible intervals are reported, not averaged | `combine_intervals` intersects conservatively: every pair must hold at ONE common D in the band (exact union over D of per-D intersections, PREREG_AMENDMENT.md A1). An empty set returns status incompatible, lo/hi None, the conflicting strikes and a max-overlap count. Mixed identity groups are never combined. This is not a robust consensus; one mispriced valid pair yields incompatible. | `test_req4_incompatible_intervals_reported_not_averaged`, `test_req4_mixed_groups_are_not_combined`, `test_dband_pairs_need_a_common_discount_factor`, `test_dband_exact_matches_brute_force_grid` (24 seeds) |
| req5 | American applicability and dividend/borrow limits are explicit | `applicability` returns no parity equality for American exercise (Q02 owns the adjustment). `american_spot_bounds` gives bounds only with a dividend PV upper bound AND borrow declared negligible. `implied_net_carry_interval` returns joint r−q−borrow only. | `test_req5_american_has_no_parity_forward`, `test_req5_american_bounds_need_dividend_and_borrow`, `test_req5_carry_is_joint_only` |
| req6 | No relabeling as arbitrage or spot prediction | `ForwardEstimate` is frozen. Its label, `not_executable_arbitrage`, `not_spot_forecast` and `carry_identification` are init=False constants. It has no profit/signal/predict/target fields. | `test_req6_no_relabel_as_arbitrage_or_spot_prediction` |
| — | Bounded inputs | D band within [0.5, 1.5], at most 20,000 legs, prices finite and ≤ 1e7 | `test_bounded_inputs` |
| — | No silent activation | RESEARCH_ONLY is True. The docstring starts "RESEARCH REFERENCE — NOT WIRED" and states INSUFFICIENT_DATA. There are no register/schedule/publish/run entry points and no I/O modules bound. The public callable surface is pinned to an exact allowlist. Nothing imports the module. | `test_no_silent_activation` |

Focused run: `PYTHONPATH=…/Q12 PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -m pytest
…/Q12/tests/test_options_parity_forward_interval.py --rootdir …/Q12 --noconftest -p no:cacheprovider -q`
gave 50 passed, exit 0.

Falsifier (PREREG §9): if qualified pairs cannot identify a stable forward within
quote/carry uncertainty, the method returns bounds or unavailable. It is enforced
structurally by the incompatible and unavailable statuses. Empirically it is untested
because of INSUFFICIENT_DATA.
