"""Live Entry Radar PR-3 (W3) — the detector registry.

WHAT THIS PINS
--------------
Five challengers acquire real specs at W3 and ``F1_FUSION`` does not.  Three
properties keep that honest:

**Identity is frozen.**  Each ``spec_hash`` is pinned as a literal, so a spec
edit breaks this file on purpose — a detector whose constants moved silently is a
detector whose past results are no longer attributable to it.

**The hash covers EVERYTHING that decides a fire (PIT-19).**  Mutating any single
key of any spec block must move its hash.  Written as a mutation sweep rather than
an assertion about the current value, because the failure it guards is a future
``spec_hash`` computed over a convenient SUBSET — which would pass every
equality test in this file while making the identity meaningless.

**The registry cannot drift from the code (registry-vs-implementation).**  Each
registered hash IS the implementing module's own ``*_spec_hash()``, and the check
iterates the REGISTRY so a detector added without wiring its hash fails loudly.

Nothing here reads ``data/``, ``site/`` or the network.
"""
from __future__ import annotations

import copy

import pytest

from engine.entry_radar.c5_adapter import C5_DETECTOR_ID, C5_SPEC, c5_spec_hash
from engine.entry_radar.challengers import (
    C1_DETECTOR_ID,
    C1_SPEC,
    C2_DETECTOR_ID,
    C2_PRIMARY_VARIANT,
    C2_SPEC,
    C2_VARIANTS,
    C4_DETECTOR_ID,
    C4_SPEC,
    c1_spec_hash,
    c2_spec_hash,
    c4_spec_hash,
)
from engine.entry_radar.detectors import (
    DETECTORS,
    RESERVED_DETECTOR_IDS,
    STRATIFICATION_ONLY,
    DetectorError,
    DetectorSpec,
    NotYetSpecified,
    assert_registry_matches_implementations,
    get_spec,
)
from engine.entry_radar.entry_events import (
    RADAR_1D_TURN_SUBTYPES,
    RADAR_NATIVE_SUBTYPES,
    sha16,
)
from engine.entry_radar.four_hour import C3_DETECTOR_ID, C3_SPEC, c3_spec_hash
from engine.entry_radar.g0_adapter import G0_DETECTOR_ID, g0_spec_hash

#: FROZEN literals.  Editing any value inside a spec block changes these and
#: breaks this test ON PURPOSE (the W2 precedent, `test_entry_radar_w2_guards.py`).
FROZEN_SPEC_HASHES = {
    "G0_GREY_DOT@1": "9be89a8acc8b905c",
    # TRUTH CHANGE, 2026-08-14 adversarial review: W3-4 moved four firing-relevant
    # constants INTO the spec blocks by value (ATR window, minute-knowability
    # offset, the three §10 re-arm numbers), W3-2 added C3's arm-expiry constant,
    # and W3-1/W3-5/W3-13 stated the basis, freshness and non-positive-ATR
    # refusals.  Those are spec CHANGES, so the hashes move — which is the
    # mechanism working, not a golden regenerated to hide a failure.  Lawful
    # because no result has ever been attributed to the old values: nothing has
    # shipped from this branch.
    "C1_1D_LIVE_WASHOUT@1": "f0bbd6cf3a6e2339",
    "C2_1D_TURN@1": "d8ba60a25cfa7400",
    "C3_1D_4H_RECOVERY@1": "d54dc1e55c4261c8",
    "C4_MTF_TURN@1": "dce21ac680233ee2",
    "C5_BOTTOM_WATCH@1": "13dec66345a0376c",
}

SPEC_BLOCKS = {
    C1_DETECTOR_ID: C1_SPEC,
    C2_DETECTOR_ID: C2_SPEC,
    C3_DETECTOR_ID: C3_SPEC,
    C4_DETECTOR_ID: C4_SPEC,
    C5_DETECTOR_ID: C5_SPEC,
}

IMPLEMENTATION_HASHES = {
    G0_DETECTOR_ID: g0_spec_hash,
    C1_DETECTOR_ID: c1_spec_hash,
    C2_DETECTOR_ID: c2_spec_hash,
    C3_DETECTOR_ID: c3_spec_hash,
    C4_DETECTOR_ID: c4_spec_hash,
    C5_DETECTOR_ID: c5_spec_hash,
}

#: The §18 A5 material each spec MUST name.  Without this a spec could keep a
#: stable hash while quietly dropping the constant the amendment turns on — the
#: hash would still be "sensitive to every key it has", just not to the one that
#: left.
REQUIRED_SPEC_KEYS = {
    C1_DETECTOR_ID: ("arm_condition", "oversold_threshold", "promotion_rule",
                     "candidates_per_episode", "depth_requirement", "sampling_law",
                     "interval_minutes", "minute_knowability",
                     "provisional_close_rule", "confirmed_history", "indicator_core",
                     # W3-4 / W3-1 / W3-5
                     "minute_bar_seconds", "rearm_law", "price_basis_law",
                     "freshness_law"),
    C2_DETECTOR_ID: ("variants", "variant_count", "primary_variant",
                     "combination_rule", "rebound_atr_multiple", "rebound_low_law",
                     "atr_law", "basis_law", "eligibility",
                     "current_oversold_requirement", "pre_arm_rule", "indicator_core",
                     # W3-4 / W3-8 / W3-1 / W3-5
                     "sampling", "pre_arm_encoding", "price_basis_law",
                     "freshness_law"),
    C3_DETECTOR_ID: ("daily_condition", "daily_knowability", "arm_rule", "turn_rule",
                     "turn_primitive", "grid_anchor", "grid_nominal_minutes",
                     "grid_key", "grid_effective_end", "grid_early_close",
                     "bucket_confirmation", "partial_bucket", "warm_up",
                     "extended_hours", "indicator_core",
                     # W3-2 / W3-5 / W3-11
                     "arm_expiry_sessions", "arm_expiry_rule", "freshness_law",
                     "empty_bucket_law"),
    C4_DETECTOR_ID: ("role", "can_fire", "firing_fence", "base_population", "anchor",
                     "anchor_era", "anchor_rejected", "grains", "turn_primitive",
                     "recent_os", "recent_os_window", "recovery_count",
                     "confirmed_bar_law", "indicator_core"),
    C5_DETECTOR_ID: ("upstream_pin", "constants", "formula_drawdown",
                     "formula_monthly_dwell", "formula_recent_os", "formula_washed",
                     "formula_blocked_trigger", "candidate_population", "precedence",
                     "knowability", "mutation_law"),
}


def _mutate(value):
    """One minimal, type-appropriate change to a spec value."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return value + 1
    if isinstance(value, str):
        return value + " (mutated)"
    if isinstance(value, list):
        return list(value) + ["mutated"]
    if isinstance(value, dict):
        return {**value, "__mutated__": True}
    return "mutated"


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

def test_the_six_detectors_are_registered_and_f1_is_not():
    assert sorted(DETECTORS) == sorted(FROZEN_SPEC_HASHES)
    assert "F1_FUSION" not in DETECTORS


@pytest.mark.parametrize("detector_id", sorted(FROZEN_SPEC_HASHES))
def test_spec_hash_is_frozen_and_stable_within_a_run(detector_id):
    record = DETECTORS[detector_id]
    assert record.spec_hash == FROZEN_SPEC_HASHES[detector_id]
    assert record.spec_hash == record.spec_hash, "hash must not vary within a run"


@pytest.mark.parametrize("detector_id", sorted(IMPLEMENTATION_HASHES))
def test_registry_hash_is_the_implementation_hash(detector_id):
    """The registry may not become a second source of truth for an identity."""
    assert DETECTORS[detector_id].spec_hash == IMPLEMENTATION_HASHES[detector_id]()


def test_registry_implementation_check_iterates_the_registry():
    assert_registry_matches_implementations()


def test_MUTATION_a_registered_detector_with_no_implementation_hash_is_caught():
    """Control for the check above: it must fail on the gap it exists to find."""
    from engine.entry_radar import detectors as module

    original = dict(module.IMPLEMENTATION_HASHES)
    try:
        module.IMPLEMENTATION_HASHES.pop(C4_DETECTOR_ID)
        with pytest.raises(DetectorError, match="names no implementing"):
            module.assert_registry_matches_implementations()
    finally:
        module.IMPLEMENTATION_HASHES.clear()
        module.IMPLEMENTATION_HASHES.update(original)
    assert_registry_matches_implementations()


# ---------------------------------------------------------------------------
# PIT-19 — the hash covers every firing-relevant key
# ---------------------------------------------------------------------------

def _spec_key_cases():
    for detector_id, spec in sorted(SPEC_BLOCKS.items()):
        for key in sorted(spec):
            yield pytest.param(detector_id, key, id=f"{detector_id}:{key}")


@pytest.mark.parametrize("detector_id,key", list(_spec_key_cases()))
def test_PIT19_changing_any_single_spec_key_moves_the_spec_hash(detector_id, key):
    """Every key in every spec block is load-bearing for the identity.

    A ``spec_hash`` that ignored a key would let that constant change without the
    detector's identity changing — and every result attributed to the old hash
    would silently absorb the new behaviour.
    """
    spec = SPEC_BLOCKS[detector_id]
    baseline = sha16(spec)
    mutated = copy.deepcopy(spec)
    mutated[key] = _mutate(mutated[key])
    assert sha16(mutated) != baseline, f"{detector_id}.{key} does not reach the hash"
    record = DETECTORS[detector_id]
    moved = DetectorSpec(detector_id=record.detector_id, version=record.version,
                         grain=record.grain, bar_family=record.bar_family,
                         spec=mutated)
    assert moved.spec_hash != record.spec_hash


@pytest.mark.parametrize("detector_id", sorted(SPEC_BLOCKS))
def test_PIT19_adding_a_key_moves_the_hash_and_key_order_does_not(detector_id):
    spec = SPEC_BLOCKS[detector_id]
    assert sha16({**spec, "__new__": 1}) != sha16(spec)
    reordered = {k: spec[k] for k in reversed(list(spec))}
    assert sha16(reordered) == sha16(spec), "canonical JSON must sort keys"


@pytest.mark.parametrize("detector_id,keys", sorted(REQUIRED_SPEC_KEYS.items()))
def test_spec_blocks_name_the_A5_material(detector_id, keys):
    """A stable hash over a spec that DROPPED a constant is still a wrong identity."""
    missing = [k for k in keys if k not in SPEC_BLOCKS[detector_id]]
    assert missing == [], f"{detector_id} spec is missing {missing}"


# ---------------------------------------------------------------------------
# PIT-20 — F1 stays unspecified
# ---------------------------------------------------------------------------

def test_PIT20_f1_fusion_is_the_only_reserved_id_and_refuses_a_spec():
    assert RESERVED_DETECTOR_IDS == ("F1_FUSION",)
    with pytest.raises(NotYetSpecified, match="F1 is NOT in"):
        get_spec("F1_FUSION")


def test_PIT20_an_unknown_detector_is_a_different_refusal_from_a_reserved_one():
    with pytest.raises(DetectorError) as unknown:
        get_spec("C9_NOT_A_DETECTOR")
    assert "unknown detector_id" in str(unknown.value)
    assert not isinstance(unknown.value, NotYetSpecified)


def test_a_spec_with_no_constants_is_refused_outright():
    with pytest.raises(DetectorError, match="must be RESERVED"):
        DetectorSpec(detector_id="C9_EMPTY", version=1, grain="x", bar_family="y",
                     spec={})


# ---------------------------------------------------------------------------
# the six C2 variants have exactly one source
# ---------------------------------------------------------------------------

def test_the_c2_variant_enum_has_one_source_and_six_members():
    assert C2_VARIANTS == RADAR_1D_TURN_SUBTYPES
    assert len(C2_VARIANTS) == 6
    assert set(C2_SPEC["variants"]) == set(C2_VARIANTS)
    assert C2_SPEC["variant_count"] == 6
    assert C2_SPEC["primary_variant"] == C2_PRIMARY_VARIANT == "c2a_kd_cross"
    assert set(RADAR_NATIVE_SUBTYPES["radar_1d_turn"]) == set(C2_VARIANTS)


def test_c4_is_registered_stratification_only_and_declares_it_cannot_fire():
    assert STRATIFICATION_ONLY == (C4_DETECTOR_ID,)
    assert DETECTORS[C4_DETECTOR_ID].spec["role"] == "stratification_only"
    assert DETECTORS[C4_DETECTOR_ID].spec["can_fire"] is False
    assert "radar_mtf_turn" not in RADAR_NATIVE_SUBTYPES
    assert len(RADAR_NATIVE_SUBTYPES) == 3


# ---------------------------------------------------------------------------
# 2026-08-14 adversarial-review regressions (W3-10, W3-13)
# ---------------------------------------------------------------------------

def test_W3_13_the_c2f_spec_states_the_non_positive_ATR_refusal():
    """W3-13: the guard was implemented and unstated.  A spec that omits a
    refusal the code performs is a spec a reader cannot reason from — and the
    omission is invisible, because the hash covers what IS written.
    """
    formula = C2_SPEC["variants"]["c2f_rebound_atr"]
    assert "non-positive" in formula and "unavailable" in formula
    assert "never a trivial pass" in formula


def test_W3_10_the_run_helpers_state_that_their_episodes_are_not_a_ledger():
    """W3-10 (docstring-only ruling): a per-path trace is not a §10 ledger, and
    the §10 clocks belong to PR-4/PR-5.  Pinned so the statement cannot quietly
    disappear and leave a reader assuming the ledger is here.
    """
    from engine.entry_radar import challengers as ch

    for func in (ch.run_c1, ch.run_c2):
        doc = func.__doc__ or ""
        assert "NOT" in doc or "not a" in doc.lower()
        assert "PR-4" in doc or "PR-5" in doc
    assert "rearm_eligible" in (ch.run_c1.__doc__ or "")
    assert callable(ch.rearm_eligible)


# TTI R1-B v4 pure construction: synthetic only; no registry or market reads.
def _ttib_config():
    from pathlib import Path
    return (Path(__file__).resolve().parents[1] /
            'research/species/tti_r1b/config_v4.json').read_bytes()


def _ttib_frame(tail='reclaim', session=None):
    from datetime import date
    import pandas as pd
    from engine.session_digest import session_window_et
    session = session or date(2026, 9, 17)
    start, _ = session_window_et(session)
    rows = [[100, 100.2, 99, 99.4, 100],
            [99.4, 99.5, 98.8, 99, 100],
            [99, 99.1, 98.6, 98.98, 100]]
    if tail == 'reclaim':
        rows += [[98.98, 99.1, 98.55, 98.95, 100],
                 [98.95, 99.2, 98.8, 99.1, 100],
                 [99.1, 99.5, 99, 99.4, 100]]
    elif tail == 'continue':
        rows += [[98.6, 98.7, 97.9, 98, 100],
                 [98, 99.1, 97.8, 98.95, 100],
                 [98.95, 99.3, 98.8, 99.2, 100]]
    else:
        rows += [[98.7, 98.8, 98.6, 98.7, 100]] * 3
    return pd.DataFrame(rows, index=pd.date_range(start, periods=len(rows), freq='5min'),
                        columns=['open', 'high', 'low', 'close', 'volume'])


def _ttib_run(frame=None, *, minute=600, **kwargs):
    from datetime import date, timedelta
    from engine.entry_radar.tactical_exhaustion import construct_session
    from engine.session_digest import session_window_et
    from lib.nyse_calendar import session_n_back
    day = kwargs.pop('session', date(2026, 9, 17))
    start, _ = session_window_et(day)
    base = dict(symbol='AMD', session=day, prior_session=session_n_back(day, 1),
                prior_close=100.0, prior_atr=2.0, asof=start+timedelta(minutes=minute-570),
                config_bytes=_ttib_config(), price_basis='adjusted')
    base.update(kwargs)
    return construct_session(_ttib_frame(session=day) if frame is None else frame, **base)


def test_TTIB_frozen_rules_have_an_executable_constructor():
    import importlib.util
    assert importlib.util.find_spec('engine.entry_radar.tactical_exhaustion') is not None


def test_TTIB_completed_candidate_and_full_latency_are_distinct():
    r = _ttib_run(minute=585)
    assert [e['selector'] for e in r['events']] == ['BASE_FRESH_LOW', 'EXHAUSTION_FORMING']
    e = r['events'][0]
    assert e['candidate_at'].endswith('13:45:00+00:00')
    assert e['decision_at'] == e['candidate_at']
    assert e['entry_reference_at'].endswith('13:50:00+00:00')
    assert 'entry_price' not in e
    assert e['candidate_low'] == 98.6
    assert e['reclaim_level'] == 98.8
    assert e['continuation_level'] == pytest.approx(98.1)


def test_TTIB_reclaim_is_confirmed_later_and_preserves_two_low_anchors():
    r = _ttib_run(minute=590)
    e = next(e for e in r['events'] if e['selector'] == 'EXHAUSTION_RECLAIM')
    assert e['candidate_at'].endswith('13:45:00+00:00')
    assert e['decision_at'].endswith('13:50:00+00:00')
    assert e['entry_reference_at'].endswith('13:55:00+00:00')
    assert e['confirmation_delay_bars'] == 1
    assert e['candidate_low'] == 98.6 and e['episode_low'] == 98.55
    assert len(r['control_census']) == 1


def test_TTIB_continuation_wins_before_a_later_reclaim():
    r = _ttib_run(_ttib_frame('continue'))
    assert r['anchors'][0]['race'] == 'CONTINUATION'
    first = r['anchors'][0]['anchor_id']
    assert not any(e['selector'] == 'EXHAUSTION_RECLAIM' and e['anchor_id'] == first
                   for e in r['events'])
    assert any(e['selector'] == 'CONTINUATION_RISK' for e in r['events'])


def test_TTIB_unresolved_race_expires_after_exactly_three_completed_bars():
    frame = _ttib_frame('expire')
    assert _ttib_run(frame, minute=595)['anchors'][0]['race'] == 'PENDING'
    r = _ttib_run(frame, minute=600)
    assert r['anchors'][0]['race'] == 'EXPIRED'
    assert all(e['selector'] in ('BASE_FRESH_LOW', 'EXHAUSTION_FORMING') for e in r['events'])


def test_TTIB_equal_low_does_not_create_a_new_candidate():
    f = _ttib_frame(); f.iloc[2, f.columns.get_loc('low')] = 98.8
    assert _ttib_run(f, minute=585)['events'] == []


@pytest.mark.parametrize('field,value', [('volume', 0), ('volume', -1), ('close', float('nan')),
                                          ('high', 98.0)])
def test_TTIB_bad_candidate_is_not_a_measured_signal(field, value):
    f = _ttib_frame(); f.iloc[2, f.columns.get_loc(field)] = value
    r = _ttib_run(f, minute=585)
    assert r['events'] == [] and r['diagnostics']


def test_TTIB_zero_volume_confirmation_preserves_forming_but_censors_race():
    f = _ttib_frame(); f.iloc[3, f.columns.get_loc('volume')] = 0
    r = _ttib_run(f, minute=590)
    assert r['anchors'][0]['race'] == 'UNAVAILABLE'
    assert len(r['events']) == 2


def test_TTIB_no_future_bar_can_modify_decision_prefix():
    import pandas as pd
    f = _ttib_frame(); expected = _ttib_run(f, minute=585)
    f.iloc[3:, :] = float('nan')
    f = pd.concat([f, f.iloc[5:6]])
    assert _ttib_run(f, minute=585) == expected


def test_TTIB_bad_later_bar_never_erases_an_earlier_confirmation():
    f = _ttib_frame(); before = _ttib_run(f, minute=590)['events']
    f.iloc[4, f.columns.get_loc('low')] = float('nan')
    assert _ttib_run(f, minute=600)['events'] == before


def test_TTIB_missing_confirmation_bar_is_not_skipped_for_a_later_reclaim():
    f = _ttib_frame(); r = _ttib_run(f.drop(f.index[3]))
    assert r['anchors'][0]['race'] == 'UNAVAILABLE'
    assert not any(e['selector'] == 'EXHAUSTION_RECLAIM' for e in r['events'])


def test_TTIB_control_census_does_not_depend_on_future_family_label():
    a = _ttib_run(_ttib_frame('reclaim'), minute=585)['control_census']
    b = _ttib_run(_ttib_frame('continue'), minute=585)['control_census']
    assert a == b and a


@pytest.mark.parametrize('override', [dict(prior_atr=0), dict(prior_close=float('nan')),
                                       dict(price_basis='raw')])
def test_TTIB_bad_prior_inputs_refuse_the_session(override):
    r = _ttib_run(**override)
    assert r['availability'] == 'UNAVAILABLE' and r['events'] == []


def test_TTIB_stale_prior_session_is_unavailable():
    from datetime import date
    assert _ttib_run(prior_session=date(2026, 9, 14))['availability'] == 'UNAVAILABLE'


def test_TTIB_early_close_does_not_become_a_normal_day():
    from datetime import date
    assert _ttib_run(session=date(2026, 11, 27))['availability'] == 'UNAVAILABLE'


def test_TTIB_recipe_cannot_be_retuned_or_rename_authority():
    import json
    c = json.loads(_ttib_config()); c['base_displacement_atr_min'] = 0.1
    with pytest.raises(ValueError, match='config identity'):
        _ttib_run(config_bytes=json.dumps(c).encode())
    r = _ttib_run()
    assert r['authority'] == 'research_construction_only'
    assert r['historical_availability_proven'] is False
    assert r['market_outcomes_computed'] is False
    assert r['may_alert'] is False and r['may_trade'] is False


def test_TTIB_later_anchor_can_confirm_first_and_unqualified_anchor_consumes_nothing():
    f = _ttib_frame()
    f.iloc[2] = [99, 99.1, 98.6, 98.65, 100]
    f.iloc[3] = [98.65, 98.8, 98.5, 98.75, 100]
    f.iloc[4] = [98.75, 98.79, 98.6, 98.7, 100]
    f.iloc[5] = [98.7, 99, 98.65, 98.9, 100]
    r = _ttib_run(f)
    forming = next(e for e in r['events'] if e['selector'] == 'EXHAUSTION_FORMING')
    reclaim = next(e for e in r['events'] if e['selector'] == 'RECLAIM_ONLY')
    assert forming['candidate_at'].endswith('13:50:00+00:00')
    assert reclaim['candidate_at'] == forming['candidate_at']
    assert reclaim['decision_at'].endswith('13:55:00+00:00')
    assert len([e for e in r['events'] if e['selector'] == 'RECLAIM_ONLY']) == 1
    assert any(e['selector'] == 'EXHAUSTION_RECLAIM' for e in r['events'])


def test_TTIB_race_cannot_read_a_candle_one_second_before_completion():
    from datetime import timedelta
    f = _ttib_frame()
    r = _ttib_run(f, asof=f.index[4].to_pydatetime()-timedelta(seconds=1))
    assert r['anchors'][0]['race'] == 'PENDING'
    assert len(r['events']) == 2


def test_TTIB_duplicate_later_row_preserves_earlier_events_and_censors_pending():
    import pandas as pd
    f = _ttib_frame(); before = _ttib_run(f, minute=590)['events']
    duplicate = pd.concat([f.iloc[:5], f.iloc[4:5], f.iloc[5:]])
    r = _ttib_run(duplicate)
    assert r['events'] == before
    assert any(d['reason'] == 'duplicate_bar' for d in r['diagnostics'])


def test_TTIB_zero_range_candidate_is_unavailable():
    f = _ttib_frame(); f.iloc[2] = [98.6, 98.6, 98.6, 98.6, 100]
    r = _ttib_run(f, minute=585)
    assert not r['events']
    assert any(d['reason'] == 'zero_range_candidate' for d in r['diagnostics'])


def test_TTIB_timezone_conversion_preserves_event_times_and_fractional_volume():
    f = _ttib_frame(); expected = _ttib_run(f)['events']
    f.index = f.index.tz_convert('Asia/Tokyo'); f['volume'] = 0.125
    assert _ttib_run(f)['events'] == expected


def test_TTIB_premarket_does_not_enter_regular_session_running_low():
    import pandas as pd
    from datetime import timedelta
    f = _ttib_frame(); early = f.iloc[:1].copy()
    early.index = early.index - timedelta(hours=2)
    early.iloc[0] = [95, 96, 90, 95, 100]
    assert _ttib_run(pd.concat([early, f]))['events'] == _ttib_run(f)['events']


def test_TTIB_market_holiday_has_no_regular_session_candidates():
    from datetime import date
    r = _ttib_run(session=date(2026, 12, 25))
    assert r['reason'] == 'not_trading_session' and not r['events']


def test_TTIB_control_census_keeps_a_later_time_bin_without_extra_selector_fires():
    import pandas as pd
    f = _ttib_frame('expire')
    # Preserve the frozen >=0.20 ATR impulse at the later candidate.
    f.iloc[4] = [99.1, 99.2, 98.6, 98.7, 100]
    extension = pd.DataFrame([[98.7, 98.85, 98.58, 98.8, 100]],
              index=[f.index[-1] + pd.Timedelta(minutes=5)], columns=f.columns)
    r = _ttib_run(pd.concat([f, extension]), minute=605)
    assert len(r['control_census']) == 2
    assert len([e for e in r['events'] if e['selector'] == 'BASE_FRESH_LOW']) == 1


def test_TTIB_explanation_cli_is_synthetic_only_and_no_market_input_option():
    import json, subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    script = root/'scripts/research/terminal_tactical_r1b_preview.py'
    assert script.is_file(), 'synthetic replay consumer not implemented'
    p = subprocess.run([sys.executable, str(script), '--format', 'json'],
                       cwd=root, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    report = json.loads(p.stdout)
    assert report['evidence_class'] == 'SYNTHETIC_ONLY'
    assert report['market_data_read'] is False and report['outcomes_computed'] is False
    assert len(report['examples']) == 3
    states = [e['construction']['anchors'][0]['race'] for e in report['examples']]
    assert states == ['RECLAIM', 'CONTINUATION', 'EXPIRED']
    denied = subprocess.run([sys.executable, str(script), '--input-dir', '/tmp'],
                            cwd=root, capture_output=True, text=True, timeout=30)
    assert denied.returncode != 0


def test_TTIB_markdown_explanation_names_confirmation_and_limits():
    import subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    p = subprocess.run([sys.executable, str(root/'scripts/research/terminal_tactical_r1b_preview.py'),
                        '--format', 'markdown'], cwd=root, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    assert 'SYNTHETIC' in p.stdout and 'not market data' in p.stdout
    assert 'Candidate' in p.stdout and 'Confirmation' in p.stdout and 'Earliest entry' in p.stdout
    assert 'No edge or probability' in p.stdout


def test_TTIB_displacement_is_a_condition_not_a_visual_low_guess():
    r = _ttib_run(minute=585, prior_close=99.5)
    assert r['events'] == []  # (99.5 - 98.6) / 2 < frozen 0.50


def test_TTIB_small_recent_impulse_does_not_qualify_even_after_prior_weakness():
    f = _ttib_frame()
    f.iloc[0] = [98.9, 99, 98.65, 98.8, 100]
    f.iloc[1] = [98.8, 98.9, 98.64, 98.7, 100]
    f.iloc[2] = [98.7, 98.9, 98.6, 98.85, 100]
    assert _ttib_run(f, minute=585)['events'] == []


def test_TTIB_prior_zero_volume_low_is_not_a_session_extreme():
    import pandas as pd
    f = _ttib_frame(); extra = f.iloc[:1].copy()
    # Insert a zero-volume low at 09:30; shift the real three-bar impulse later.
    f.index = f.index + pd.Timedelta(minutes=5)
    extra.iloc[0] = [90, 91, 80, 90, 0]
    r = _ttib_run(pd.concat([extra, f]), minute=590)
    assert r['events'][0]['candidate_low'] == 98.6
    assert r['events'][0]['reclaim_level'] == 98.8


def test_TTIB_unordered_later_input_cannot_erase_earlier_events():
    import pandas as pd
    f = _ttib_frame(); before = _ttib_run(f, minute=590)['events']
    bad = pd.concat([f.iloc[:4], f.iloc[5:6], f.iloc[4:5]])
    r = _ttib_run(bad)
    assert r['events'] == before
    assert any(d['reason'] == 'off_grid_or_unordered_bar' for d in r['diagnostics'])


def test_TTIB_off_grid_bar_is_not_rounded_into_a_causal_candidate():
    import pandas as pd
    f = _ttib_frame(); index = list(f.index)
    index[2] += pd.Timedelta(seconds=1); f.index = pd.DatetimeIndex(index)
    assert _ttib_run(f, minute=590)['events'] == []


def test_TTIB_constructor_has_no_empirical_io_or_production_event_writer():
    import ast
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1]/'engine/entry_radar/tactical_exhaustion.py').read_text()
    tree = ast.parse(source)
    allowed = {'__future__', 'bisect', 'datetime', 'hashlib', 'json', 'math', 'numbers',
               'pandas', 'engine.session_digest', 'lib.nyse_calendar'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(n.name in allowed for n in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module in allowed
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', '')
            assert name not in {'open', 'read_csv', 'read_parquet', 'read_json', 'read_bytes',
                                'write_text', 'write_bytes', 'register_trial', 'build_radar_native_event'}


def test_TTIB_absent_data_is_unavailable_not_an_available_no_signal_report():
    r = _ttib_run(_ttib_frame().iloc[:0])
    assert r['availability'] == 'UNAVAILABLE'
    assert r['reason'] == 'no_usable_completed_bars'
    assert r['events'] == []


def test_TTIB_late_input_gap_is_partial_without_erasing_valid_earlier_events():
    f = _ttib_frame(); events = _ttib_run(f, minute=590)['events']
    r = _ttib_run(f.drop(f.index[4]))
    assert r['availability'] == 'PARTIAL'
    assert r['events'] == events


def test_TTIB_before_first_bar_close_is_pending_not_a_measured_no_signal():
    r = _ttib_run(minute=572)
    assert r['availability'] == 'PENDING'
    assert r['reason'] == 'no_completed_regular_bar_yet'


# ---------------------------------------------------------------------------
# TTI R1-B v4 matched-control selection — synthetic-only, no outcomes
# ---------------------------------------------------------------------------

def _ttib_control_row(session: str, *, symbol='AMD', candidate_at=None, clock_bin=19,
                      displacement_bucket=0, qqq_sign=1, anchor_id=None, **extra):
    if candidate_at is None:
        candidate_at = f'{session}T13:45:00+00:00'
    row = {
        'anchor_id': anchor_id or f'{symbol}:{session}:synthetic',
        'candidate_at': candidate_at,
        'symbol': symbol,
        'session': session,
        'clock_bin': clock_bin,
        'displacement_bucket': displacement_bucket,
        'displacement_atr': 0.6,
        'qqq_open_to_decision_sign': qqq_sign,
        'future_family_labels_used': False,
    }
    row.update(extra)
    return row


def _ttib_selected_reclaim():
    r = _ttib_run(minute=590)
    return next(e for e in r['events'] if e['selector'] == 'EXHAUSTION_RECLAIM')


def test_TTIB_match_controls_requires_exact_frozen_covariates_and_excludes_selected_date():
    from engine.entry_radar.tactical_exhaustion import match_controls
    selected = _ttib_selected_reclaim()
    # Eleven lawful late-partition controls, one on selected date (must be excluded),
    # plus one decoy for every frozen matching covariate.
    dates = ['2026-07-13','2026-07-14','2026-07-15','2026-07-16','2026-07-17',
             '2026-07-20','2026-07-21','2026-07-22','2026-07-23','2026-07-24']
    rows = [_ttib_control_row(d) for d in dates]
    rows += [
        _ttib_control_row('2026-09-17', anchor_id='same-date'),
        _ttib_control_row('2026-07-27', symbol='NVDA', anchor_id='wrong-ticker'),
        _ttib_control_row('2026-06-30', anchor_id='wrong-partition'),
        _ttib_control_row('2026-07-28', clock_bin=20, anchor_id='wrong-bin'),
        _ttib_control_row('2026-07-29', displacement_bucket=1, anchor_id='wrong-displacement'),
        _ttib_control_row('2026-07-30', qqq_sign=-1, anchor_id='wrong-market'),
    ]
    got = match_controls(selected, selected_symbol='AMD', selected_session='2026-09-17',
                         selected_qqq_sign=1, control_census=rows,
                         config_bytes=_ttib_config())
    assert got['availability'] == 'AVAILABLE'
    assert got['matched_count'] == 10
    assert got['required_min_rows'] == 10
    assert {c['session'] for c in got['matched_controls']} == set(dates)
    assert got['selected']['clock_bin'] == 19
    assert got['selected']['displacement_bucket'] == 0
    assert got['selected']['partition'] == 'late'
    assert got['selected']['qqq_open_to_decision_sign'] == 1
    assert got['authority'] == 'research_matching_only'
    assert got['market_outcomes_computed'] is False


def test_TTIB_match_controls_applies_same_confirmation_delay_plus_processing_latency():
    from datetime import datetime, timedelta
    from engine.entry_radar.tactical_exhaustion import match_controls
    selected = _ttib_selected_reclaim()
    rows = [_ttib_control_row(f'2026-07-{13+i:02d}') for i in range(10)]
    got = match_controls(selected, selected_symbol='AMD', selected_session='2026-09-17',
                         selected_qqq_sign=1, control_census=rows,
                         config_bytes=_ttib_config())
    assert selected['confirmation_delay_bars'] == 1
    assert got['selected']['processing_latency_minutes'] == 5
    for c in got['matched_controls']:
        candidate = datetime.fromisoformat(c['candidate_at'])
        entry = datetime.fromisoformat(c['entry_reference_at'])
        assert entry - candidate == timedelta(minutes=10)
        assert c['confirmation_delay_bars'] == 1
        assert c['processing_latency_minutes'] == 5
        assert c['entry_reference_state'] == 'scheduled_clock_only_not_a_fill'


def test_TTIB_match_controls_below_floor_is_no_control_without_widening_fallback():
    from engine.entry_radar.tactical_exhaustion import match_controls
    selected = _ttib_selected_reclaim()
    rows = [_ttib_control_row(f'2026-07-{13+i:02d}') for i in range(9)]
    # Many near misses must not be borrowed to rescue the floor.
    rows += [_ttib_control_row(f'2026-08-{i:02d}', clock_bin=20, anchor_id=f'near-{i}')
             for i in range(1, 13)]
    got = match_controls(selected, selected_symbol='AMD', selected_session='2026-09-17',
                         selected_qqq_sign=1, control_census=rows,
                         config_bytes=_ttib_config())
    assert got['availability'] == 'NO_CONTROL'
    assert got['matched_count'] == 9
    assert got['matched_controls'] == []
    assert got['fallback_used'] is False
    assert got['reason'] == 'matched_control_floor_not_met'


def test_TTIB_match_controls_never_conditions_on_future_family_labels():
    from engine.entry_radar.tactical_exhaustion import match_controls
    selected = _ttib_selected_reclaim()
    base = [_ttib_control_row(f'2026-07-{13+i:02d}') for i in range(10)]
    labelled = [dict(row, selector='CONTINUATION_RISK', later_family='RECLAIM_ONLY',
                     future_family_labels_used=True) for row in base]
    a = match_controls(selected, selected_symbol='AMD', selected_session='2026-09-17',
                       selected_qqq_sign=1, control_census=base, config_bytes=_ttib_config())
    b = match_controls(selected, selected_symbol='AMD', selected_session='2026-09-17',
                       selected_qqq_sign=1, control_census=labelled, config_bytes=_ttib_config())
    assert a['matched_controls'] == b['matched_controls']
    assert all('selector' not in c and 'later_family' not in c for c in b['matched_controls'])


def test_TTIB_match_controls_deduplicates_identity_and_is_input_order_deterministic():
    from engine.entry_radar.tactical_exhaustion import match_controls
    selected = _ttib_selected_reclaim()
    rows = [_ttib_control_row(f'2026-07-{13+i:02d}', anchor_id=f'a-{i}') for i in range(10)]
    rows += [dict(rows[0]), dict(rows[1])]
    a = match_controls(selected, selected_symbol='AMD', selected_session='2026-09-17',
                       selected_qqq_sign=1, control_census=rows, config_bytes=_ttib_config())
    b = match_controls(selected, selected_symbol='AMD', selected_session='2026-09-17',
                       selected_qqq_sign=1, control_census=list(reversed(rows)),
                       config_bytes=_ttib_config())
    assert a['matched_count'] == 10
    assert a['matched_controls'] == b['matched_controls']
    assert a['excluded_counts']['duplicate_identity'] == 2


def test_TTIB_match_controls_rejects_malformed_selected_or_market_sign_and_does_not_read_outcomes():
    from engine.entry_radar.tactical_exhaustion import match_controls
    import inspect
    selected = _ttib_selected_reclaim()
    rows = [_ttib_control_row(f'2026-07-{13+i:02d}') for i in range(10)]
    with pytest.raises(ValueError, match='selected event'):
        match_controls({}, selected_symbol='AMD', selected_session='2026-09-17',
                       selected_qqq_sign=1, control_census=rows, config_bytes=_ttib_config())
    with pytest.raises(ValueError, match='QQQ sign'):
        match_controls(selected, selected_symbol='AMD', selected_session='2026-09-17',
                       selected_qqq_sign=2, control_census=rows, config_bytes=_ttib_config())
    source = inspect.getsource(match_controls)
    assert 'return' in source
    for forbidden in ('net_beta_residual', 'mfe', 'mae', 'target_first', 'adverse_first'):
        assert forbidden not in source.lower()


def test_TTIB_synthetic_preview_consumes_frozen_matched_control_selector():
    import json, subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    script = root/'scripts/research/terminal_tactical_r1b_preview.py'
    p = subprocess.run([sys.executable, str(script), '--format', 'json'],
                       cwd=root, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    report = json.loads(p.stdout)
    matching = report['matching']
    assert matching['selected_selector'] == 'EXHAUSTION_RECLAIM'
    assert matching['available']['availability'] == 'AVAILABLE'
    assert matching['available']['matched_count'] == 10
    assert matching['available']['fallback_used'] is False
    assert matching['no_control']['availability'] == 'NO_CONTROL'
    assert matching['no_control']['matched_count'] == 9
    assert matching['no_control']['matched_controls'] == []
    assert matching['no_control']['fallback_used'] is False
    assert matching['available']['market_outcomes_computed'] is False
    assert report['market_data_read'] is False and report['outcomes_computed'] is False


def test_TTIB_synthetic_preview_markdown_explains_exact_matching_and_no_fallback():
    import subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    script = root/'scripts/research/terminal_tactical_r1b_preview.py'
    p = subprocess.run([sys.executable, str(script), '--format', 'markdown'],
                       cwd=root, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    assert 'Matched-control demonstration' in p.stdout
    assert '10' in p.stdout and 'NO_CONTROL' in p.stdout
    assert 'no widening fallback' in p.stdout.lower()
    assert 'same ticker' in p.stdout.lower() and 'qqq' in p.stdout.lower()


# ---------------------------------------------------------------------------
# TTI R1-B v4 prior-only normalization — synthetic daily inputs only
# ---------------------------------------------------------------------------

def _ttib_daily_frames(session, *, beta_multiple=2.0, n_prior=70, add_current=False):
    import pandas as pd
    from lib.nyse_calendar import session_n_back
    days = [session_n_back(session, n) for n in range(n_prior, 0, -1)]
    q = 100.0
    s = 80.0
    q_closes, s_closes = [], []
    for i, _day in enumerate(days):
        r = (0.001 + (i % 7) * 0.0004) * (1 if i % 2 == 0 else -1)
        q *= 1.0 + r
        s *= 1.0 + beta_multiple * r
        q_closes.append(q)
        s_closes.append(s)
    stock = pd.DataFrame({
        'high': [x + 1.0 for x in s_closes],
        'low': [x - 1.0 for x in s_closes],
        'close': s_closes,
    }, index=pd.DatetimeIndex(days))
    qqq = pd.DataFrame({'close': q_closes}, index=pd.DatetimeIndex(days))
    if add_current:
        stock.loc[pd.Timestamp(session)] = [9999.0, 0.01, 7777.0]
        qqq.loc[pd.Timestamp(session)] = [0.02]
    return stock.sort_index(), qqq.sort_index()


def test_TTIB_prior_normalization_uses_only_complete_prior_sessions_and_excludes_current_day():
    from datetime import date
    import pandas as pd
    from engine.entry_radar.tactical_exhaustion import build_prior_normalization
    day = date(2026, 9, 17)
    stock, qqq = _ttib_daily_frames(day, add_current=True)
    with_current = build_prior_normalization(stock, qqq, session=day,
                                              config_bytes=_ttib_config())
    without_current = build_prior_normalization(stock.drop(pd.Timestamp(day)),
                                                 qqq.drop(pd.Timestamp(day)), session=day,
                                                 config_bytes=_ttib_config())
    assert with_current == without_current
    assert with_current['availability'] == 'AVAILABLE'
    assert with_current['prior_session'] == '2026-09-16'
    assert with_current['atr_sessions'] == 20
    assert with_current['beta_pairs'] == 60
    assert with_current['beta_available'] is True
    assert with_current['historical_availability_proven'] is False
    assert with_current['market_outcomes_computed'] is False
    assert with_current['authority'] == 'research_normalization_only'


def test_TTIB_prior_normalization_beta_matches_known_synthetic_relationship_and_clip():
    from datetime import date
    from engine.entry_radar.tactical_exhaustion import build_prior_normalization
    day = date(2026, 9, 17)
    stock2, qqq = _ttib_daily_frames(day, beta_multiple=2.0)
    got2 = build_prior_normalization(stock2, qqq, session=day, config_bytes=_ttib_config())
    assert got2['beta'] == pytest.approx(2.0, rel=2e-3)
    stock4, qqq4 = _ttib_daily_frames(day, beta_multiple=4.0)
    got4 = build_prior_normalization(stock4, qqq4, session=day, config_bytes=_ttib_config())
    assert got4['beta_raw'] > 3.0
    assert got4['beta'] == 3.0


def test_TTIB_prior_normalization_requires_all_twenty_atr_sessions_but_beta_can_use_valid_pairs():
    from datetime import date
    import pandas as pd
    from engine.entry_radar.tactical_exhaustion import build_prior_normalization
    from lib.nyse_calendar import session_n_back
    day = date(2026, 9, 17)
    stock, qqq = _ttib_daily_frames(day)
    missing_atr = session_n_back(day, 7)
    got = build_prior_normalization(stock.drop(pd.Timestamp(missing_atr)), qqq,
                                    session=day, config_bytes=_ttib_config())
    assert got['availability'] == 'UNAVAILABLE'
    assert got['reason'] == 'incomplete_prior_atr_window'
    assert got['beta_available'] is True
    assert got['beta_pairs'] >= 40


def test_TTIB_prior_normalization_beta_below_minimum_is_explicit_not_fabricated():
    from datetime import date
    from engine.entry_radar.tactical_exhaustion import build_prior_normalization
    day = date(2026, 9, 17)
    stock, qqq = _ttib_daily_frames(day)
    # Keep enough recent stock history for ATR, but too few benchmark observations for beta.
    qqq = qqq.iloc[-35:]
    got = build_prior_normalization(stock, qqq, session=day, config_bytes=_ttib_config())
    assert got['availability'] == 'AVAILABLE'
    assert got['prior_atr'] > 0
    assert got['beta_available'] is False
    assert got['beta'] is None
    assert got['beta_reason'] == 'insufficient_prior_beta_pairs'
    assert got['beta_pairs'] < 40


def test_TTIB_prior_normalization_refuses_duplicate_or_unordered_daily_identity():
    from datetime import date
    import pandas as pd
    from engine.entry_radar.tactical_exhaustion import build_prior_normalization
    day = date(2026, 9, 17)
    stock, qqq = _ttib_daily_frames(day)
    dup = pd.concat([stock, stock.iloc[-1:]])
    with pytest.raises(ValueError, match='duplicate'):
        build_prior_normalization(dup, qqq, session=day, config_bytes=_ttib_config())
    unordered = stock.iloc[::-1]
    with pytest.raises(ValueError, match='ordered'):
        build_prior_normalization(unordered, qqq, session=day, config_bytes=_ttib_config())


def test_TTIB_prior_normalization_rejects_wrong_basis_and_config_retargeting():
    from datetime import date
    import json
    from engine.entry_radar.tactical_exhaustion import build_prior_normalization
    day = date(2026, 9, 17)
    stock, qqq = _ttib_daily_frames(day)
    got = build_prior_normalization(stock, qqq, session=day, config_bytes=_ttib_config(),
                                    price_basis='raw')
    assert got['availability'] == 'UNAVAILABLE'
    assert got['reason'] == 'price_basis_mismatch'
    cfg = json.loads(_ttib_config()); cfg['atr_lookback_sessions'] = 5
    with pytest.raises(ValueError, match='config identity'):
        build_prior_normalization(stock, qqq, session=day,
                                  config_bytes=json.dumps(cfg).encode())


def test_TTIB_synthetic_preview_derives_prior_normalization_and_feeds_constructor():
    import json, subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    script = root/'scripts/research/terminal_tactical_r1b_preview.py'
    p = subprocess.run([sys.executable, str(script), '--format', 'json'],
                       cwd=root, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    report = json.loads(p.stdout)
    norm = report['normalization']
    assert norm['availability'] == 'AVAILABLE'
    assert norm['atr_sessions'] == 20
    assert norm['prior_atr'] == pytest.approx(2.0, rel=1e-6)
    assert norm['beta_available'] is True
    assert norm['beta'] == pytest.approx(2.0, rel=2e-3)
    assert norm['market_outcomes_computed'] is False
    for example in report['examples']:
        events = example['construction']['events']
        assert events
        assert all(e['prior_atr'] == pytest.approx(norm['prior_atr']) for e in events)
        assert all(e['previous_regular_close'] == pytest.approx(norm['prior_close']) for e in events)
    assert report['market_data_read'] is False and report['outcomes_computed'] is False


def test_TTIB_synthetic_preview_markdown_discloses_prior_only_atr_and_beta():
    import subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    script = root/'scripts/research/terminal_tactical_r1b_preview.py'
    p = subprocess.run([sys.executable, str(script), '--format', 'markdown'],
                       cwd=root, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    lower = p.stdout.lower()
    assert 'prior-only normalization' in lower
    assert 'atr20' in lower
    assert 'beta' in lower
    assert 'synthetic only' in lower
