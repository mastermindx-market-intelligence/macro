"""IM15 contract checks: robust dislocation receipts over qualified IM12 rows."""
from __future__ import annotations

import ast
import hashlib
import json
import random
import re
import statistics
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from engine import intl_inputs
from engine.intl_global_observation import build_observation, check_clocks
from engine.intl_global_observation import ObservationError
from engine.intl_global_dislocation import (
    ATTENTION_LABELS,
    ATTENTION_MODIFIED_Z,
    COMPARISON_MODES,
    CONTRACT_VERSION,
    DECLARED_NOT_IMPLEMENTED,
    DIRECTIONS,
    DISLOCATION_ABSTAIN_REASONS,
    DislocationError,
    EXCLUSION_REASONS,
    INTERPRETATION_LIMITS,
    KINDS,
    MIN_PEERS,
    MIN_REFERENCE_OBSERVATIONS,
    MODIFIED_Z_CONSTANT,
    PEER_RULES,
    STATES,
    THRESHOLD_RATIONALE,
    VOL_BLOCK_WINDOWS,
    VOL_HORIZON,
    dislocation_own_history,
    dislocation_peer_divergence,
    modified_z,
    rank_counts,
    region_of,
    robust_location,
    subject_value,
)
from engine.intl_global_universe import load_universe
from engine.intl_performance_records import build_return_records
from lib.intl_eod_publication import build_eod_inputs
from lib.intl_global_observation_adapter import observations_from_qualification

RIGHTS = {"decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
          "scope": "intl-index-fx-eod-user-facing-v1"}
INCUMBENT = {"quality": "qualified", "reason": None,
             "decision_ref": "derived-evaluation:sha256:abc"}
EVIDENCE = "saved-parquet:sha256:one|saved-parquet:sha256:two"
COMPUTED_AT = "2026-10-09T20:30:00+00:00"
BASE_END = date(2026, 10, 7)


def _month(k: int) -> date:
    """Window endpoint E(k): BASE_END shifted back k months (day 7 always)."""
    total = BASE_END.year * 12 + BASE_END.month - 1 - k
    return date(total // 12, total % 12 + 1, BASE_END.day)


def _offset(market_id: str) -> int:
    return (ord(market_id[0]) + ord(market_id[-1])) % 7


def _local_value(market_id: str, k: int, shift: float = 0.0) -> float:
    return ((7 * k + _offset(market_id)) % 13 - 6) * 0.8 + shift


def _fx_value(market_id: str, k: int) -> float:
    return ((5 * k + _offset(market_id)) % 7 - 3) * 0.5


def _identity(market_id: str = "JP", k: int = 0, *, tag: str = "", **overrides) -> dict:
    identity = {
        "universe_id": market_id, "market_id": market_id,
        "index_id": f"^T{market_id}", "fx_id": f"{market_id}FX=X",
        "horizon": "1m", "currency_basis": "usd_unhedged", "return_basis": "price",
        "window_start": f"{_month(k + 1)}T00:00:00",
        "window_end": f"{_month(k)}T00:00:00",
        "source_content_sha256": hashlib.sha256(
            f"{market_id}:{k}:{tag}".encode()).hexdigest(),
    }
    identity.update(overrides)
    return identity


def _clocks(k: int, *, late: bool = False) -> dict:
    if late:
        stamp = "2026-10-10T15:00:00+00:00"
    else:
        stamp = f"{_month(k) + timedelta(days=2)}T15:00:00+00:00"
    return {
        "observation": {"at": f"{_month(k)}T00:00:00", "precision": "session_date"},
        "source_publication": {"at": stamp, "precision": "exact"},
        "ingestion": {"at": stamp, "precision": "exact"},
        "computation": {"at": stamp, "precision": "exact"},
    }


def _observation(market_id: str = "JP", k: int = 0, *, shift: float = 0.0,
                 tag: str = "", late: bool = False, horizon: str = "1m",
                 currency_basis: str = "usd_unhedged", values: dict | None = None,
                 rights: dict | None | str = "default", window=None,
                 local: float | None = None, fx: float | None = None) -> dict:
    if values is None:
        local_pct = _local_value(market_id, k, shift) if local is None else local
        fx_pct = _fx_value(market_id, k) if fx is None else fx
        usd_pct = ((1.0 + local_pct / 100.0) * (1.0 + fx_pct / 100.0) - 1.0) * 100.0
        values = {"local_pct": local_pct, "usd_pct": usd_pct, "fx_pct": fx_pct}
    identity = _identity(market_id, k, tag=tag, horizon=horizon,
                         currency_basis=currency_basis)
    if window is not None:
        identity["window_start"], identity["window_end"] = window
    return build_observation(
        identity=identity, clocks=_clocks(k, late=late), values=values,
        rights=dict(RIGHTS) if rights == "default" else rights,
        incumbent=dict(INCUMBENT), evidence_ref=EVIDENCE)


def _references(market_id: str = "JP", count: int = 24, start: int = 1) -> list[dict]:
    return [_observation(market_id, k) for k in range(start, start + count)]


OUTPUT_KEYS = {"contract_version", "dislocation_id", "kind", "comparison_mode",
               "peer_rule", "subject", "clocks", "state", "abstain_reasons",
               "evidence", "references", "thresholds", "threshold_rationale",
               "interpretation_limits", "rights"}
SUBJECT_KEYS = {"observation_id", "universe_id", "market_id", "horizon",
                "currency_basis", "return_basis", "window_start", "window_end",
                "state", "abstain_reasons", "decomposition"}
EVIDENCE_KEYS = {"statistic", "subject_value", "center", "mad", "modified_z",
                 "attention", "direction", "rank"}
REFERENCE_KEYS = {"offered", "used", "used_windows", "used_observation_ids",
                  "subject_block_ids", "excluded_by_reason"}
THRESHOLD_KEYS = {"modified_z_constant", "attention_modified_z",
                  "min_reference_observations", "min_peers", "vol_block_windows"}
FORBIDDEN_WORDS = {"cheap", "expensive", "bottom", "entry", "buy", "sell",
                   "oversold", "overbought", "undervalued", "overvalued",
                   "bargain", "opportunity"}


def _invariant(receipt: dict) -> None:
    refs = receipt["references"]
    assert refs["offered"] == refs["used_windows"] + len(refs["subject_block_ids"]) + sum(
        refs["excluded_by_reason"].values())
    assert set(refs["excluded_by_reason"]) == set(EXCLUSION_REASONS)


# 1 rationale pins -------------------------------------------------------------

def test_threshold_rationales_are_pinned():
    assert MODIFIED_Z_CONSTANT == round(statistics.NormalDist().inv_cdf(0.75), 4)
    assert ATTENTION_MODIFIED_Z == 3.5
    joined = json.dumps(THRESHOLD_RATIONALE)
    assert "Iglewicz" in joined and "1.3.5.17" in joined
    rng = random.Random(20261021)
    draws = [rng.gauss(0.0, 1.0) for _ in range(2000)]
    center, mad = robust_location(draws)
    share = sum(abs(modified_z(x, center, mad)) > ATTENTION_MODIFIED_Z
                for x in draws) / len(draws)
    assert share < 0.01
    assert MIN_REFERENCE_OBSERVATIONS == min(
        n for n in range(1, 100) if 1 / (n + 1) < 0.05)
    for n in range(1, 11):
        values = list(range(1, n + 1))
        values[-1] = 1e9
        if statistics.median(values) in range(1, n + 1):
            break
    assert MIN_PEERS == n
    assert VOL_BLOCK_WINDOWS == 3


def test_horizon_pin_matches_incumbent_performance_config():
    from engine.intl_performance import _pcfg
    horizons = _pcfg()["horizons_d"]
    assert VOL_BLOCK_WINDOWS == horizons["3m"] // horizons["1m"]
    assert VOL_HORIZON == "1m"


def test_module_vocabularies_are_frozen():
    assert CONTRACT_VERSION == "intl-global-dislocation-v1"
    assert KINDS == ("own_history_return", "own_history_fx", "own_history_volatility",
                     "peer_divergence_return", "peer_divergence_fx")
    assert DECLARED_NOT_IMPLEMENTED == ("factor_residual", "cross_asset",
                                        "instrument", "peer_divergence_volatility")
    assert COMPARISON_MODES == ("own_history", "cross_section_today")
    assert PEER_RULES == ("same_universe_region", "all_qualified")
    assert STATES == ("qualified", "abstain")
    assert ATTENTION_LABELS == ("outside_reference_range", "within_reference_range")
    assert DIRECTIONS == ("above", "below", "at_center")
    assert EXCLUSION_REASONS == (
        "not_qualified", "market_mismatch", "subject_market", "horizon_mismatch",
        "window_end_mismatch", "not_point_in_time", "fx_leg_unavailable",
        "outside_peer_group", "window_overlap", "duplicate_window",
        "block_not_contiguous")
    assert DISLOCATION_ABSTAIN_REASONS == frozenset({
        "subject_not_qualified", "subject_fx_leg_unavailable",
        "insufficient_reference_history", "insufficient_peers",
        "dispersion_degenerate", "subject_block_incomplete",
        "peer_group_unresolved", "clock_missing", "clock_order_violation"})
    assert set(THRESHOLD_RATIONALE) == THRESHOLD_KEYS
    assert len(INTERPRETATION_LIMITS) == 4
    assert isinstance(DislocationError("x"), ValueError)


def test_helper_contracts():
    values = [1.0, 2.0, 3.0, 4.0, 100.0]
    center, mad = robust_location(values)
    assert center == statistics.median(values) == 3.0
    assert mad == statistics.median([abs(x - 3.0) for x in values]) == 1.0
    assert modified_z(9.0, 3.0, 1.0) == pytest.approx(MODIFIED_Z_CONSTANT * 6.0)
    with pytest.raises(DislocationError):
        robust_location([])
    with pytest.raises(DislocationError):
        modified_z(9.0, 3.0, 0.0)
    assert rank_counts(2.0, [1.0, 2.0, 2.0, 3.0]) == {"below": 1, "equal": 2,
                                                      "above": 1, "n": 4}
    universe = load_universe()
    assert region_of("JP", universe) == "asia_pacific"
    assert region_of("EZ", universe) == "europe"
    assert region_of("XX", universe) is None
    split = deepcopy(universe)
    split["aggregates"]["EZ"]["members"] = ["JP", "GB"]
    assert region_of("EZ", split) is None
    stripped = deepcopy(universe)
    stripped["jurisdictions"]["JP"].pop("region")
    assert region_of("JP", stripped) is None
    observation = _observation()
    assert subject_value(observation, "own_history_return") == observation["value"]["pct"]
    assert subject_value(observation, "own_history_fx") == \
        observation["decomposition"]["fx_pct"]


# 2 own_history_return qualified ------------------------------------------------

def test_own_history_return_extreme_and_ordinary_subjects():
    references = _references()
    extreme = dislocation_own_history(
        _observation("JP", 0, shift=44.8), references,
        kind="own_history_return", computed_at=COMPUTED_AT)
    assert extreme["state"] == "qualified"
    assert extreme["abstain_reasons"] == []
    assert extreme["comparison_mode"] == "own_history"
    assert extreme["peer_rule"] is None
    assert set(extreme) == OUTPUT_KEYS
    assert set(extreme["subject"]) == SUBJECT_KEYS
    assert set(extreme["evidence"]) == EVIDENCE_KEYS
    assert set(extreme["references"]) == REFERENCE_KEYS
    assert set(extreme["thresholds"]) == THRESHOLD_KEYS
    assert extreme["evidence"]["attention"] == "outside_reference_range"
    assert extreme["evidence"]["direction"] == "above"
    assert extreme["evidence"]["rank"] == {"below": 24, "equal": 0, "above": 0, "n": 24}
    assert extreme["references"]["used"] == 24
    assert extreme["references"]["used_windows"] == 24
    assert extreme["references"]["subject_block_ids"] == []
    assert extreme["thresholds"]["min_reference_observations"] == \
        MIN_REFERENCE_OBSERVATIONS
    assert extreme["thresholds"]["min_peers"] is None
    assert extreme["thresholds"]["vol_block_windows"] is None
    hand = [obs["value"]["pct"] for obs in references]
    center = statistics.median(hand)
    mad = statistics.median([abs(x - center) for x in hand])
    subject = _observation("JP", 0, shift=44.8)
    assert extreme["evidence"]["subject_value"] == subject["value"]["pct"]
    assert extreme["evidence"]["center"] == pytest.approx(center, abs=1e-12)
    assert extreme["evidence"]["mad"] == pytest.approx(mad, abs=1e-12)
    assert extreme["evidence"]["modified_z"] == pytest.approx(
        MODIFIED_Z_CONSTANT * (subject["value"]["pct"] - center) / mad, abs=1e-12)
    _invariant(extreme)
    ordinary = dislocation_own_history(
        _observation("JP", 0), references, kind="own_history_return",
        computed_at=COMPUTED_AT)
    assert ordinary["state"] == "qualified"
    assert ordinary["evidence"]["attention"] == "within_reference_range"
    assert ordinary["evidence"]["rank"]["n"] == 24
    _invariant(ordinary)


# 3 insufficient references ------------------------------------------------------

def test_attention_rule_is_strictly_above_3_5():
    # A modified z inside [3.0, 3.5) must stay within the reference range:
    # the published rule fires only strictly above 3.5.
    def flat(k, local_pct):
        return _observation("JP", k, currency_basis="local",
                            values={"local_pct": local_pct, "usd_pct": None,
                                    "fx_pct": None})

    history = [flat(k, 3.2 if k % 2 else -3.2) for k in range(1, 25)]
    subject = flat(0, 15.0)
    receipt = dislocation_own_history(subject, history, kind="own_history_return",
                                      computed_at=COMPUTED_AT)
    assert receipt["state"] == "qualified"
    assert receipt["evidence"]["center"] == 0.0
    assert receipt["evidence"]["mad"] == 3.2
    assert 3.0 <= abs(receipt["evidence"]["modified_z"]) < 3.5
    assert receipt["evidence"]["attention"] == "within_reference_range"


def test_own_history_short_history_abstains_with_all_none_evidence():
    receipt = dislocation_own_history(
        _observation("JP", 0), _references(count=19),
        kind="own_history_return", computed_at=COMPUTED_AT)
    assert receipt["state"] == "abstain"
    assert receipt["abstain_reasons"] == ["insufficient_reference_history"]
    for key in ("subject_value", "center", "mad", "modified_z", "attention",
                "direction", "rank"):
        assert receipt["evidence"][key] is None
    assert receipt["evidence"]["statistic"] == "modified_z"
    assert receipt["references"]["used"] == 19
    assert receipt["references"]["used_windows"] == 19
    _invariant(receipt)


# 4 missing-data non-improvement -------------------------------------------------

def test_abstained_subject_never_gets_an_attention_label():
    subject = _observation("JP", 0, shift=44.8, rights=None)
    assert subject["state"] == "abstain"
    receipt = dislocation_own_history(
        subject, _references(), kind="own_history_return", computed_at=COMPUTED_AT)
    assert receipt["state"] == "abstain"
    assert "subject_not_qualified" in receipt["abstain_reasons"]
    assert "rights_unconfirmed" in receipt["subject"]["abstain_reasons"]
    assert receipt["evidence"]["attention"] is None
    _invariant(receipt)


def test_withdrawing_a_reference_never_improves_a_result():
    subject = _observation("JP", 0, shift=44.8)
    history = _references(count=20)
    before = dislocation_own_history(subject, history, kind="own_history_return",
                                     computed_at=COMPUTED_AT)
    assert before["state"] == "qualified"
    withheld = deepcopy(history)
    withheld[0] = build_observation(
        identity=deepcopy(withheld[0]["identity"]),
        clocks=deepcopy(withheld[0]["clocks"]),
        values={"local_pct": 1.0, "usd_pct": 1.0, "fx_pct": 0.0},
        rights=None, incumbent=dict(INCUMBENT), evidence_ref=EVIDENCE)
    assert withheld[0]["state"] == "abstain"
    after = dislocation_own_history(subject, withheld, kind="own_history_return",
                                    computed_at=COMPUTED_AT)
    assert after["state"] == "abstain"
    assert "insufficient_reference_history" in after["abstain_reasons"]
    assert after["references"]["used"] == 19
    assert after["references"]["excluded_by_reason"]["not_qualified"] == 1
    _invariant(after)


# 5 exclusions --------------------------------------------------------------------

def test_own_history_exclusions_are_counted_and_change_nothing():
    references = _references()
    duplicate_value = references[4]["value"]["pct"]
    duplicate = _observation(
        "JP", 5, tag="dup", local=duplicate_value)
    overlap = _observation(
        "JP", 0, tag="ovl",
        window=(f"{_month(2)}T00:00:00", f"{date(2026, 9, 27)}T00:00:00"))
    junk = references + [
        _observation("KR", 1),                                # market_mismatch
        _observation("JP", 1, horizon="3m",
                     window=(f"{_month(5)}T00:00:00", f"{_month(1)}T00:00:00")),
        overlap,                                              # window_overlap
        duplicate,                                            # duplicate_window
        _observation("JP", 25, rights=None),                  # not_qualified
        _observation("JP", 26, late=True),                    # not_point_in_time
    ]
    subject = _observation("JP", 0, shift=44.8)
    clean = dislocation_own_history(subject, references, kind="own_history_return",
                                    computed_at=COMPUTED_AT)
    receipt = dislocation_own_history(subject, junk, kind="own_history_return",
                                      computed_at=COMPUTED_AT)
    assert receipt["references"]["offered"] == 30
    assert receipt["references"]["used"] == 24
    excluded = receipt["references"]["excluded_by_reason"]
    assert excluded["market_mismatch"] == 1
    assert excluded["horizon_mismatch"] == 1
    assert excluded["window_overlap"] == 1
    assert excluded["duplicate_window"] == 1
    assert excluded["not_qualified"] == 1
    assert excluded["not_point_in_time"] == 1
    assert receipt["evidence"] == clean["evidence"]
    assert receipt["dislocation_id"] == clean["dislocation_id"]
    _invariant(receipt)


# 6 point-in-time replay ----------------------------------------------------------

def test_point_in_time_replay_equals_the_filtered_list():
    subject = _observation("JP", 0, shift=44.8)
    history = _references() + [_observation("JP", 25, late=True),
                               _observation("JP", 26, late=True)]
    replayed = dislocation_own_history(subject, history,
                                       kind="own_history_return",
                                       computed_at=COMPUTED_AT)
    filtered = [obs for obs in history
                if not obs["clocks"]["ingestion"]["at"] > "2026-10-09T20:30:00+00:00"]
    assert len(filtered) == 24
    expected = dislocation_own_history(subject, filtered, kind="own_history_return",
                                       computed_at=COMPUTED_AT)
    assert replayed["dislocation_id"] == expected["dislocation_id"]
    assert replayed["evidence"] == expected["evidence"]
    assert replayed["references"]["excluded_by_reason"]["not_point_in_time"] == 2
    _invariant(replayed)


# 7 determinism -------------------------------------------------------------------

def test_determinism_and_computed_at_invariance():
    subject = _observation("JP", 0, shift=44.8)
    history = _references()
    shuffled = list(reversed(history))
    first = dislocation_own_history(subject, history, kind="own_history_return",
                                    computed_at=COMPUTED_AT)
    second = dislocation_own_history(subject, shuffled, kind="own_history_return",
                                     computed_at=COMPUTED_AT)
    assert first == second
    later = dislocation_own_history(subject, history, kind="own_history_return",
                                    computed_at="2026-10-09T21:00:00+00:00")
    assert later["dislocation_id"] == first["dislocation_id"]
    assert later["clocks"]["computation"] == {
        "at": "2026-10-09T21:00:00+00:00", "precision": "exact"}


# 8 dispersion degenerate ----------------------------------------------------------

def test_identical_references_abstain_dispersion_degenerate():
    flat = [_observation("JP", k, local=1.0, fx=0.5) for k in range(1, 25)]
    assert len({obs["value"]["pct"] for obs in flat}) == 1
    receipt = dislocation_own_history(
        _observation("JP", 0, local=1.0, fx=0.5), flat, kind="own_history_return",
        computed_at=COMPUTED_AT)
    assert receipt["state"] == "abstain"
    assert receipt["abstain_reasons"] == ["dispersion_degenerate"]
    assert receipt["references"]["used"] == 24
    _invariant(receipt)


# 9 fx kinds -----------------------------------------------------------------------

def test_own_history_fx_uses_the_fx_leg():
    subject = _observation("JP", 0, shift=44.8)
    history = _references()
    receipt = dislocation_own_history(subject, history, kind="own_history_fx",
                                      computed_at=COMPUTED_AT)
    assert receipt["state"] == "qualified"
    assert receipt["evidence"]["subject_value"] == \
        subject["decomposition"]["fx_pct"]
    hand = [obs["decomposition"]["fx_pct"] for obs in history]
    center = statistics.median(hand)
    mad = statistics.median([abs(x - center) for x in hand])
    assert receipt["evidence"]["modified_z"] == pytest.approx(
        MODIFIED_Z_CONSTANT * (subject["decomposition"]["fx_pct"] - center) / mad,
        abs=1e-12)
    _invariant(receipt)


def test_local_subject_without_decomposition_abstains_only_for_fx():
    subject = _observation(
        "JP", 0, currency_basis="local",
        values={"local_pct": 5.0, "usd_pct": None, "fx_pct": None})
    assert subject["state"] == "qualified"
    assert subject["decomposition"] is None
    history = [_observation("JP", k, currency_basis="local") for k in range(1, 25)]
    fx = dislocation_own_history(subject, history, kind="own_history_fx",
                                 computed_at=COMPUTED_AT)
    assert fx["state"] == "abstain"
    assert "subject_fx_leg_unavailable" in fx["abstain_reasons"]
    assert fx["evidence"]["attention"] is None
    ret = dislocation_own_history(subject, history, kind="own_history_return",
                                  computed_at=COMPUTED_AT)
    assert ret["state"] == "qualified"
    assert ret["subject"]["decomposition"] is None
    assert ret["evidence"]["subject_value"] == 5.0
    _invariant(fx)
    _invariant(ret)


# 10 volatility blocks -------------------------------------------------------------

def test_own_history_volatility_blocks_and_failures():
    subject = _observation("JP", 0)
    predecessors = [_observation("JP", 1), _observation("JP", 2)]
    history = predecessors + _references(count=60, start=3)
    receipt = dislocation_own_history(
        subject, history, kind="own_history_volatility", computed_at=COMPUTED_AT)
    assert receipt["state"] == "qualified"
    assert receipt["references"]["used"] == 20
    assert receipt["references"]["used_windows"] == 60
    assert receipt["references"]["subject_block_ids"] == sorted(
        obs["observation_id"] for obs in predecessors)
    assert receipt["thresholds"]["vol_block_windows"] == VOL_BLOCK_WINDOWS
    assert receipt["thresholds"]["min_reference_observations"] == \
        MIN_REFERENCE_OBSERVATIONS

    def rms(window_values):
        return (sum(v * v for v in window_values) / len(window_values)) ** 0.5

    subject_rms = rms([subject["value"]["pct"]]
                      + [obs["value"]["pct"] for obs in predecessors])
    # Reference keepers are newest -> oldest (k = 3..62); blocks of three.
    reference_obs = {obs["observation_id"]: obs for obs in history[2:]}
    ordered = sorted(history[2:], key=lambda obs: obs["identity"]["window_end"],
                     reverse=True)
    block_rms = [rms([obs["value"]["pct"] for obs in ordered[i:i + 3]])
                 for i in range(0, len(ordered), 3)]
    assert len(block_rms) == 20
    assert len(reference_obs) == 60
    assert receipt["evidence"]["subject_value"] == pytest.approx(subject_rms, abs=1e-12)
    assert receipt["evidence"]["center"] == pytest.approx(
        statistics.median(block_rms), abs=1e-12)
    assert receipt["references"]["used_observation_ids"] == sorted(
        obs["observation_id"] for obs in history[2:])
    _invariant(receipt)

    gapped = predecessors + [_observation("JP", k) for k in range(3, 63)
                             if k != 10]
    broken = dislocation_own_history(
        subject, gapped, kind="own_history_volatility", computed_at=COMPUTED_AT)
    assert broken["references"]["used"] < 20
    assert broken["references"]["used_windows"] == broken["references"]["used"] * 3
    assert broken["references"]["excluded_by_reason"]["block_not_contiguous"] == 2
    assert "insufficient_reference_history" in broken["abstain_reasons"]
    _invariant(broken)

    # The subject's immediate predecessor (window 1) is absent, so window 2
    # never chains onto the subject and the block stays incomplete.
    short_block = [_observation("JP", 2)] + _references(count=60, start=3)
    incomplete = dislocation_own_history(
        subject, short_block, kind="own_history_volatility", computed_at=COMPUTED_AT)
    assert incomplete["state"] == "abstain"
    assert "subject_block_incomplete" in incomplete["abstain_reasons"]
    assert incomplete["references"]["subject_block_ids"] == []
    assert incomplete["references"]["used"] == 20
    assert incomplete["references"]["excluded_by_reason"]["block_not_contiguous"] == 1
    _invariant(incomplete)

    with pytest.raises(DislocationError, match="volatility_horizon"):
        dislocation_own_history(
            _observation("JP", 0, horizon="3m"), predecessors + _references(count=60, start=3),
            kind="own_history_volatility", computed_at=COMPUTED_AT)


# 11 real incumbent chain peer divergence -----------------------------------------

EVALUATED = "2026-10-09T20:30:00+00:00"
GRANT = {
    "status": "confirmed",
    "scope": "intl-index-fx-eod-user-facing-v1",
    "decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
}


def _setup(tmp_path, *, omit=None):
    # Synthetic frame + stored witnesses shaped exactly like the incumbent
    # EOD publication suite: the last completed bar is 2026-10-07 and the
    # collector receipt is 2026-10-09T15:00Z, two full days later.
    dates = pd.bdate_range(end="2026-10-07", periods=280)
    series = []
    for cc, market in intl_inputs.countries().items():
        for symbol in (market["index"], market["fx"]):
            if symbol not in series:
                series.append(symbol)
    cols = {}
    for slot, symbol in enumerate(series):
        if symbol == omit:
            continue
        value = [float(100 + slot * 4 + 0.125 * i) for i in range(len(dates))]
        cols[symbol] = pd.Series(value, index=dates)
        path = tmp_path / "intl" / (
            symbol.replace("^", "_").replace("=", "_").replace("/", "_") + ".parquet")
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"close": value}, index=dates).to_parquet(path)
    frame = pd.DataFrame(cols).sort_index()
    status = {"sources": {"intl_prices": {
        "source": "intl_prices", "status": "ok",
        "checked_at": "2026-10-09T15:00:00+00:00",
        "last_date": "2026-10-07",
    }}}
    (tmp_path / "run_status.json").write_text(json.dumps(status), encoding="utf-8")
    return frame, series


def _chain(tmp_path, *, omit=None):
    """build_eod_inputs then the exact workspace-overview owner assembly."""
    frame, series = _setup(tmp_path, omit=omit)
    result = build_eod_inputs(frame, data_root=tmp_path, evaluated_at=EVALUATED, rights=GRANT)
    assert result is not None
    selected, inputs = result
    pending = intl_inputs.source_snapshot(
        selected, source_reference="intl-supplied-close:pending",
        adjustment_bases=inputs["adjustment_bases"])
    source_reference = "intl-supplied-close:sha256:" + pending["content_sha256"]
    snapshot = intl_inputs.source_snapshot(
        selected, source_reference=source_reference,
        adjustment_bases=inputs["adjustment_bases"])
    records = build_return_records(
        selected, market_ids=list(intl_inputs.countries()),
        source_reference=source_reference)
    qualifications = {}
    for basis in ("local", "usd_unhedged"):
        qualifications[basis] = intl_inputs.qualify_return_records(
            records, snapshot=snapshot,
            source_evidence=inputs["source_evidence"],
            disclosure_decisions=inputs["disclosure_decisions"],
            policy_id=inputs["policy_id"], currency_basis=basis)
    run_status = json.loads((tmp_path / "run_status.json").read_text(encoding="utf-8"))
    return {
        "series": series, "selected": selected, "inputs": inputs,
        "records": records, "qualifications": qualifications,
        "run_status_source": run_status["sources"]["intl_prices"],
    }


def _observations(chain, basis):
    return observations_from_qualification(
        chain["records"], chain["qualifications"][basis], closes=chain["selected"],
        source_evidence=chain["inputs"]["source_evidence"],
        run_status_source=chain["run_status_source"], evaluated_at=EVALUATED,
        rights=GRANT, currency_basis=basis)


def _by_market(observations, horizon="1m"):
    return {obs["identity"]["market_id"]: obs for obs in observations
            if obs["identity"]["horizon"] == horizon}


def test_peer_divergence_all_qualified_on_real_chain(tmp_path):
    chain = _chain(tmp_path)
    observations = _observations(chain, "usd_unhedged")
    subject = _by_market(observations)["JP"]
    receipt = dislocation_peer_divergence(
        subject, observations, kind="peer_divergence_return", computed_at=EVALUATED,
        peer_rule="all_qualified")
    universe = load_universe()
    expected_peers = {mid for mid in _by_market(observations)
                      if mid != subject["identity"]["market_id"]}
    assert len(expected_peers) == 6
    assert receipt["references"]["used"] == 6
    assert receipt["references"]["excluded_by_reason"]["horizon_mismatch"] == 24
    assert receipt["references"]["excluded_by_reason"]["subject_market"] == 4
    assert receipt["references"]["offered"] == 34
    peer_values = [obs["value"]["pct"] for obs in observations
                   if obs["identity"]["market_id"] in expected_peers
                   and obs["identity"]["horizon"] == "1m"]
    center, mad = robust_location(peer_values)
    assert receipt["state"] == ("qualified"
                                if len(peer_values) >= MIN_PEERS and mad > 0
                                else "abstain")
    assert receipt["rights"] == subject["rights"]
    assert receipt["comparison_mode"] == "cross_section_today"
    assert receipt["peer_rule"] == "all_qualified"
    assert check_clocks(receipt["clocks"]) is None
    assert receipt["clocks"]["observation"] == subject["clocks"]["observation"]
    assert receipt["clocks"]["source_publication"] == \
        subject["clocks"]["source_publication"]
    assert receipt["clocks"]["ingestion"] == subject["clocks"]["ingestion"]
    _invariant(receipt)
    assert region_of("EZ", universe) == "europe"


def test_peer_divergence_same_region_on_real_chain(tmp_path):
    chain = _chain(tmp_path)
    observations = _observations(chain, "usd_unhedged")
    universe = load_universe()
    japan_region = region_of("JP", universe)
    asia = {mid for mid, obs in _by_market(observations).items()
            if mid != "JP" and region_of(obs["identity"]["universe_id"], universe)
            == japan_region}
    subject = _by_market(observations)["JP"]
    receipt = dislocation_peer_divergence(
        subject, observations, kind="peer_divergence_return", computed_at=EVALUATED,
        peer_rule="same_universe_region")
    used_markets = {mid for mid, obs in _by_market(observations).items()
                    if obs["observation_id"] in
                    set(receipt["references"]["used_observation_ids"])}
    assert used_markets == asia
    assert receipt["references"]["excluded_by_reason"]["outside_peer_group"] == 2
    assert receipt["references"]["used"] == len(asia) >= MIN_PEERS
    _invariant(receipt)

    britain = dislocation_peer_divergence(
        _by_market(observations)["GB"], observations, kind="peer_divergence_return",
        computed_at=EVALUATED, peer_rule="same_universe_region")
    assert "insufficient_peers" in britain["abstain_reasons"]
    assert britain["references"]["used"] == 1
    _invariant(britain)

    fx = dislocation_peer_divergence(
        subject, observations, kind="peer_divergence_fx", computed_at=EVALUATED,
        peer_rule="all_qualified")
    assert fx["state"] == receipt["state"]
    assert fx["evidence"]["subject_value"] == subject["decomposition"]["fx_pct"]
    assert fx["references"]["used"] == 6
    _invariant(fx)


# 12 peer group unresolved ---------------------------------------------------------

def test_peer_group_unresolved_when_subject_region_is_missing(tmp_path):
    chain = _chain(tmp_path)
    observations = _observations(chain, "usd_unhedged")
    subject = _by_market(observations)["JP"]
    universe = deepcopy(load_universe())
    universe["jurisdictions"]["JP"].pop("region")
    receipt = dislocation_peer_divergence(
        subject, observations, kind="peer_divergence_return", computed_at=EVALUATED,
        peer_rule="same_universe_region", universe=universe)
    assert receipt["state"] == "abstain"
    assert "peer_group_unresolved" in receipt["abstain_reasons"]
    assert receipt["references"]["used"] == 0
    assert receipt["references"]["excluded_by_reason"]["outside_peer_group"] == 6
    _invariant(receipt)


# 13 mixed basis -------------------------------------------------------------------

def test_mixed_basis_raises_observation_error():
    usd_subject = _observation("JP", 0, shift=44.8)
    local_in_history = [_observation("KR", k, currency_basis="local")
                        for k in range(1, 25)]
    with pytest.raises(ObservationError):
        dislocation_own_history(usd_subject, local_in_history,
                                kind="own_history_return", computed_at=COMPUTED_AT)
    usd_peer = [_observation("KR", 0)]
    local_peer = [_observation("GB", 0, currency_basis="local")]
    with pytest.raises(ObservationError):
        dislocation_peer_divergence(usd_subject, usd_peer + local_peer,
                                    kind="peer_divergence_return",
                                    computed_at=COMPUTED_AT)


# 14 kind validation ---------------------------------------------------------------

def test_kind_validation_closes_the_ladder():
    subject = _observation("JP", 0)
    history = _references()
    for kind in DECLARED_NOT_IMPLEMENTED:
        with pytest.raises(DislocationError, match="kind_not_implemented"):
            dislocation_own_history(subject, history, kind=kind,
                                    computed_at=COMPUTED_AT)
        with pytest.raises(DislocationError, match="kind_not_implemented"):
            dislocation_peer_divergence(subject, history, kind=kind,
                                        computed_at=COMPUTED_AT)
    with pytest.raises(DislocationError):
        dislocation_own_history(subject, history, kind="no_such_kind",
                                computed_at=COMPUTED_AT)
    with pytest.raises(DislocationError):
        dislocation_peer_divergence(subject, history, kind="no_such_kind",
                                    computed_at=COMPUTED_AT)
    try:
        dislocation_own_history(subject, history, kind="no_such_kind",
                                computed_at=COMPUTED_AT)
    except DislocationError as error:
        assert isinstance(error, ValueError)
    with pytest.raises(DislocationError):
        dislocation_peer_divergence(subject, history, kind="own_history_return",
                                    computed_at=COMPUTED_AT)
    with pytest.raises(DislocationError):
        dislocation_own_history(subject, history, kind="peer_divergence_return",
                                computed_at=COMPUTED_AT)
    with pytest.raises(DislocationError):
        dislocation_peer_divergence(subject, history, kind="peer_divergence_return",
                                    computed_at=COMPUTED_AT, peer_rule="nearest")


# 15 forbidden lexicon ---------------------------------------------------------------

def test_no_trading_language_in_any_receipt():
    qualified = dislocation_own_history(
        _observation("JP", 0, shift=44.8), _references(), kind="own_history_return",
        computed_at=COMPUTED_AT)
    abstained = dislocation_own_history(
        _observation("JP", 0, shift=44.8), _references(count=3),
        kind="own_history_return", computed_at=COMPUTED_AT)
    volatile = dislocation_own_history(
        _observation("JP", 0), [_observation("JP", k) for k in (1, 2)] +
        _references(count=60, start=3), kind="own_history_volatility",
        computed_at=COMPUTED_AT)
    for receipt in (qualified, abstained, volatile):
        lowered = json.dumps(receipt).lower()
        for word in FORBIDDEN_WORDS:
            assert not re.search(rf"\b{word}\b", lowered), word


# 16 closed vocabularies and invariance ----------------------------------------------

def test_outputs_stay_closed_and_inputs_untouched():
    subject = _observation("JP", 0, shift=44.8)
    history = _references()
    subject_before, history_before = deepcopy(subject), deepcopy(history)
    universe_bytes = (Path(__file__).resolve().parents[1]
                      / "config" / "intl_global_universe_v1.json").read_bytes()
    digest_before = hashlib.sha256(universe_bytes).hexdigest()
    receipts = [
        dislocation_own_history(subject, history, kind="own_history_return",
                                computed_at=COMPUTED_AT),
        dislocation_own_history(subject, history, kind="own_history_fx",
                                computed_at=COMPUTED_AT),
        dislocation_own_history(_observation("JP", 0), _references(count=5),
                                kind="own_history_return", computed_at=COMPUTED_AT),
        dislocation_peer_divergence(subject, [_observation(mid, 0) for mid in
                                              ("KR", "TW", "IN", "AU", "GB", "EZ")],
                                    kind="peer_divergence_return",
                                    computed_at=COMPUTED_AT,
                                    peer_rule="same_universe_region"),
    ]
    for receipt in receipts:
        assert set(receipt["abstain_reasons"]) <= DISLOCATION_ABSTAIN_REASONS
        assert receipt["state"] in STATES
        assert receipt["evidence"]["attention"] in ATTENTION_LABELS or \
            receipt["evidence"]["attention"] is None
        assert receipt["evidence"]["direction"] in DIRECTIONS or \
            receipt["evidence"]["direction"] is None
        _invariant(receipt)
    assert subject == subject_before
    assert history == history_before
    universe_after = (Path(__file__).resolve().parents[1]
                      / "config" / "intl_global_universe_v1.json").read_bytes()
    assert hashlib.sha256(universe_after).hexdigest() == digest_before


def test_import_surface_is_contract_only():
    source = (Path(__file__).resolve().parents[1]
              / "engine" / "intl_global_dislocation.py").read_text()
    roots = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots.add(node.module)
    allowed = {"copy", "hashlib", "json", "math", "statistics", "datetime",
               "engine.intl_global_observation", "engine.intl_global_universe"}
    assert roots <= allowed, sorted(roots - allowed)
    assert not any(root.startswith("engine.contagion") for root in roots)
    assert "pandas" not in roots and "numpy" not in roots


# 17 review round 1: pinned window-end exclusion and lowest-id tie rules ------------


def test_peer_with_different_window_end_is_excluded():
    # A peer whose window_end date differs from the subject's is excluded
    # window_end_mismatch and changes nothing else in the receipt.
    subject = _observation("JP", 0)
    peers = [_observation(mid, 0, shift=shift) for mid, shift in
             (("KR", 0.0), ("TW", 0.7), ("IN", 1.9), ("AU", -1.3))]
    clean = dislocation_peer_divergence(
        subject, peers, kind="peer_divergence_return", computed_at=COMPUTED_AT,
        peer_rule="all_qualified")
    assert clean["state"] == "qualified"
    _invariant(clean)
    extra = _observation("GB", 1)  # window_end one month earlier
    assert extra["identity"]["window_end"] != subject["identity"]["window_end"]
    assert extra["observation_id"] not in {
        peer["observation_id"] for peer in peers}
    extended = dislocation_peer_divergence(
        subject, peers + [extra], kind="peer_divergence_return",
        computed_at=COMPUTED_AT, peer_rule="all_qualified")
    excluded = extended["references"]["excluded_by_reason"]
    assert excluded["window_end_mismatch"] == 1
    assert extra["observation_id"] not in \
        extended["references"]["used_observation_ids"]
    assert extended["references"]["used_observation_ids"] == \
        clean["references"]["used_observation_ids"]
    assert extended["references"]["used"] == clean["references"]["used"]
    assert extended["evidence"] == clean["evidence"]
    assert extended["dislocation_id"] == clean["dislocation_id"]
    _invariant(extended)


def test_duplicate_peer_keeps_the_lowest_observation_id():
    subject = _observation("JP", 0)
    peers = [_observation(mid, 0, shift=shift) for mid, shift in
             (("TW", 0.7), ("IN", 1.9), ("AU", -1.3))]
    first = _observation("KR", 0, tag="a", shift=0.0)
    second = _observation("KR", 0, tag="b", shift=2.5)
    assert first["observation_id"] != second["observation_id"]
    low, high = sorted([first["observation_id"], second["observation_id"]])
    receipt = dislocation_peer_divergence(
        subject, peers + [first, second], kind="peer_divergence_return",
        computed_at=COMPUTED_AT, peer_rule="all_qualified")
    assert low in receipt["references"]["used_observation_ids"]
    assert high not in receipt["references"]["used_observation_ids"]
    assert receipt["references"]["excluded_by_reason"]["duplicate_window"] == 1
    _invariant(receipt)


def test_volatility_subject_block_tie_keeps_the_lowest_observation_id():
    subject = _observation("JP", 0)
    predecessors = [_observation("JP", 1), _observation("JP", 2)]
    duplicate = _observation("JP", 1, tag="dup")
    assert duplicate["observation_id"] != predecessors[0]["observation_id"]
    low, high = sorted([predecessors[0]["observation_id"],
                        duplicate["observation_id"]])
    history = predecessors + [duplicate] + _references(count=60, start=3)
    receipt = dislocation_own_history(
        subject, history, kind="own_history_volatility",
        computed_at=COMPUTED_AT)
    assert receipt["state"] == "qualified"
    assert low in receipt["references"]["subject_block_ids"]
    assert high not in receipt["references"]["subject_block_ids"]
    excluded = receipt["references"]["excluded_by_reason"]
    # The leftover duplicate is counted under exactly one reason: its
    # (window_start, window_end) pair re-enters the protected subject block.
    assert excluded["duplicate_window"] == 1
    assert sum(excluded.values()) == 1
    _invariant(receipt)
