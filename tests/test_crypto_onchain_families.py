"""On-chain valuation families: MVRV/NUPL are one family; clocks and units.

The family table lives here, not in engine. Engine fixes are patches under
research/crypto_science/patches/. No network and no data/ reads.
"""
from __future__ import annotations

import inspect
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from collectors.bgeo import BgeoAdapter
from collectors.coinmetrics import CoinMetricsAdapter
from engine import btc_cycle_thesis
from engine import btc_inputs
from engine import btc_signals as S
from lib import store

# Pinned pairing. MVRV and NUPL share F-MVRV because load_all sets
# nupl = 1 - 1/mvrv. SOPR is a different family. Vote aliases cover
# market_extreme's current columns ("nupl", "z") and the patched name.
FAMILY_TABLE: dict[str, dict] = {
    "F-MVRV": {
        "members": (
            "mvrv", "nupl", "realized_cap", "mvrv_z", "mvrv_z_pctile",
            "valuation_state", "realized_price",
        ),
        "vote_names": ("nupl", "z", "mvrv_z", "mvrv_family"),
    },
    "F-SOPR": {
        "members": (
            "sopr", "sth_sopr", "lth_sopr", "sth_lth_sopr_spread",
            "holder_state", "sopr_momentum", "sopr_stress",
        ),
        "vote_names": ("sopr",),
    },
    "F-STH-COST": {
        "members": (
            "sth_realized_price", "sth_cost_basis", "sth_cb_ratio",
            "sth_realized_premium",
        ),
        "vote_names": ("sth_cost_basis",),
    },
    "F-SUPPLY-IN-PROFIT": {
        "members": ("supply_in_profit", "supply", "supply_in_profit_pct"),
        "vote_names": ("sip",),
    },
    "F-SENTIMENT-FG": {
        "members": ("fear_greed",),
        "vote_names": ("fg",),
    },
}

_UNAVAILABLE = "unavailable"


def family_of(metric: str) -> str:
    for fid, spec in FAMILY_TABLE.items():
        if metric in spec["members"] or metric in spec.get("vote_names", ()):
            return fid
    raise KeyError(metric)


def independent_confirmation_count(metrics: list[str]) -> int:
    """Count information families, not raw series or vote columns."""
    return len({family_of(m) for m in metrics})


def family_regime(metrics: list[str], *, side: str, min_families: int) -> str:
    """min_families counts families. One family cannot meet a floor of 2."""
    n = independent_confirmation_count(metrics)
    if side in ("capitulation", "euphoria") and n >= min_families:
        return side
    return "normal"


def qualify_observation(
    value,
    *,
    unit: str | None,
    expected_unit: str,
    denominator,
    definition_id: str | None,
    expected_definition: str,
) -> dict:
    """SPEC OF RECORD for a later engine helper, not current engine behavior.

    A broken unit, definition, or denominator has no number.
    """
    if unit != expected_unit:
        return {"state": _UNAVAILABLE, "reason": "unit_change", "value": None}
    if definition_id != expected_definition:
        return {"state": _UNAVAILABLE, "reason": "metric_definition_change", "value": None}
    if _bad_denominator(denominator):
        return {"state": _UNAVAILABLE, "reason": "unavailable_denominator", "value": None}
    if value is None or isinstance(value, bool):
        return {"state": _UNAVAILABLE, "reason": "value_unavailable", "value": None}
    try:
        number = float(value)
    except (TypeError, ValueError):
        return {"state": _UNAVAILABLE, "reason": "value_unavailable", "value": None}
    if not math.isfinite(number):
        return {"state": _UNAVAILABLE, "reason": "value_unavailable", "value": None}
    return {"state": "observed", "reason": None, "value": number}


def qualify_fraction(value, **kwargs) -> dict:
    """SPEC OF RECORD for a later engine helper, not current engine behavior.

    A supply share outside [0, 1] is a broken definition, not a clipped 0 or 1.
    """
    found = qualify_observation(value, **kwargs)
    if found["state"] != "observed":
        return found
    if not 0.0 <= found["value"] <= 1.0:
        return {"state": _UNAVAILABLE, "reason": "metric_definition_change", "value": None}
    return found


def _bad_denominator(denominator) -> bool:
    if denominator is None or isinstance(denominator, bool):
        return True
    try:
        number = float(denominator)
    except (TypeError, ValueError):
        return True
    return (not math.isfinite(number)) or number <= 0.0


def read_at_knowledge_cutoff(rows: list[dict], cutoff: str) -> dict:
    """SPEC OF RECORD for a later engine helper, not current engine behavior.

    Value known at cutoff. No received_at => reconstruction unavailable.
    A later receipt is not readable at an earlier cutoff. The bar date is not
    a substitute clock.
    """
    if not rows or any(not r.get("received_at") for r in rows):
        return {
            "state": _UNAVAILABLE,
            "reason": "historical_reconstruction_unavailable",
            "value": None,
        }
    cut = pd.Timestamp(cutoff)
    if cut.tz is None:
        return {
            "state": _UNAVAILABLE,
            "reason": "historical_reconstruction_unavailable",
            "value": None,
        }
    cut = cut.tz_convert("UTC")
    known: list[tuple[pd.Timestamp, object]] = []
    for row in rows:
        received = pd.Timestamp(row["received_at"])
        if received.tz is None:
            return {
                "state": _UNAVAILABLE,
                "reason": "historical_reconstruction_unavailable",
                "value": None,
            }
        received = received.tz_convert("UTC")
        if received <= cut:
            known.append((received, row["value"]))
    if not known:
        return {"state": _UNAVAILABLE, "reason": "not_yet_received", "value": None}
    known.sort(key=lambda item: item[0])
    return {"state": "observed", "reason": None, "value": known[-1][1]}


def test_family_table_importable_and_pins_mvrv_nupl() -> None:
    import tests.test_crypto_onchain_families as mod

    assert mod.FAMILY_TABLE["F-MVRV"]["members"]
    assert mod.family_of("mvrv") == mod.family_of("nupl") == "F-MVRV"
    assert mod.family_of("mvrv_z") == mod.family_of("z") == mod.family_of("mvrv_family") == "F-MVRV"
    assert mod.family_of("realized_cap") == mod.family_of("realized_price") == "F-MVRV"
    assert mod.family_of("sopr") == mod.family_of("sth_sopr") == mod.family_of("lth_sopr") == "F-SOPR"
    assert mod.family_of("sopr") != mod.family_of("mvrv")
    assert mod.family_of("sth_realized_price") == "F-STH-COST"
    assert mod.independent_confirmation_count(["mvrv", "nupl", "mvrv_z", "z"]) == 1
    assert mod.independent_confirmation_count(["mvrv", "nupl", "sopr"]) == 2
    assert mod.independent_confirmation_count(["nupl", "z", "sip", "fg"]) == 3


def test_one_mvrv_family_cannot_satisfy_two_confirmations() -> None:
    assert family_regime(["nupl", "mvrv_z"], side="capitulation", min_families=2) == "normal"
    assert family_regime(
        ["nupl", "mvrv_z", "sopr"], side="capitulation", min_families=2,
    ) == "capitulation"
    assert family_regime(["sopr"], side="euphoria", min_families=2) == "normal"


def _days(*days: str) -> list[str]:
    return list(days)


def _put(root: Path, group: str, name: str, values: list[float], days: list[str]) -> None:
    frame = pd.DataFrame({name: values}, index=pd.to_datetime(days))
    path = root / group / f"{name}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)


def _seed_price(root: Path) -> None:
    frame = pd.DataFrame(
        {
            "open": [100.0],
            "high": [100.0],
            "low": [100.0],
            "close": [100.0],
            "volume": [1.0],
        },
        index=pd.to_datetime(["2024-01-01"]),
    )
    path = root / "coinbase" / "btc_daily.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Store reads hit a temp tree. load_all never sees the repo data/ dir."""
    monkeypatch.setattr(store.config, "data_dir", lambda: tmp_path)
    _seed_price(tmp_path)
    return tmp_path


def _assert_unavailable(series: pd.Series) -> None:
    """NaN, never ±inf, 0, or 1."""
    assert series is not None and len(series) > 0
    values = [series.iloc[i] for i in range(len(series))]
    assert all(pd.isna(v) for v in values)
    for value in values:
        assert value != 0 and value != 1
        assert not (isinstance(value, float) and math.isinf(value))


_INPUTS_DEFECT = (
    "DEFECT: non-positive or non-finite denominators become inf, 0, or 1; "
    "fixed by research/crypto_science/patches/cx-t11-20261012__btc_inputs.py.patch "
    "- remove marker when applying"
)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "DEFECT: market_extreme counts NUPL and MVRV-Z as two votes; "
        "fixed by research/crypto_science/patches/cx-t11-20261012__btc_signals.py.patch "
        "- remove this marker in the same commit that applies the patch"
    ),
)
def test_market_extreme_still_runs_and_vote_names_are_one_family() -> None:
    """One F-MVRV family cannot satisfy min_votes of 2.

    Unpatched engine returns capitulation for this fixture. The strict xfail
    marks that defect until the signals patch is applied.
    """
    idx = pd.date_range("2021-01-01", periods=12, freq="D")
    inputs = {
        "price": pd.DataFrame({"close": np.full(12, 100.0)}, index=idx),
        "nupl": pd.Series(-0.3, index=idx),
    }
    val = pd.DataFrame({"mvrv_z": np.full(12, -1.0)}, index=idx)
    cfg = {
        "min_votes": 2,
        "nupl_capitulation": 0.0,
        "nupl_euphoria": 0.65,
        "z_under": 0.0,
        "z_over": 3.5,
    }
    out = S.market_extreme(inputs, val, cfg)
    assert {"extreme_score", "market_extreme"} <= set(out.columns)
    assert out["market_extreme"].iloc[-1] == "normal"
    assert set(out["market_extreme"]) == {"normal"}
    src = inspect.getsource(S.market_extreme)
    names = []
    if 'capit["nupl"]' in src or 'capit["mvrv_family"]' in src:
        names.append("nupl" if 'capit["nupl"]' in src else "mvrv_family")
    if 'capit["z"]' in src:
        names.append("z")
    elif 'capit["mvrv_family"]' in src and "mvrv_family" not in names:
        names.append("mvrv_family")
    assert names
    assert independent_confirmation_count(names) == 1


def test_mvrv_family_plus_supply_in_profit_is_capitulation() -> None:
    """NUPL + MVRV-Z plus supply-in-profit is capitulation on both trees."""
    idx = pd.date_range("2021-01-01", periods=12, freq="D")
    inputs = {
        "price": pd.DataFrame({"close": np.full(12, 100.0)}, index=idx),
        "nupl": pd.Series(-0.3, index=idx),
        "supply_in_profit_pct": pd.Series(0.2, index=idx),
    }
    val = pd.DataFrame({"mvrv_z": np.full(12, -1.0)}, index=idx)
    cfg = {
        "min_votes": 2,
        "nupl_capitulation": 0.0,
        "nupl_euphoria": 0.65,
        "z_under": 0.0,
        "z_over": 3.5,
        "sip_capitulation": 0.4,
        "sip_euphoria": 0.95,
    }
    out = S.market_extreme(inputs, val, cfg)
    assert out["market_extreme"].iloc[-1] == "capitulation"
    assert set(out["market_extreme"]) == {"capitulation"}


@pytest.mark.xfail(strict=True, reason=_INPUTS_DEFECT)
def test_mvrv_zero_derived_identity_is_unavailable(root: Path) -> None:
    """mvrv == 0 leaves realized_cap and nupl unavailable."""
    days = _days("2024-01-01")
    _put(root, "coinmetrics", "mcap_usd", [100.0], days)
    _put(root, "coinmetrics", "mvrv", [0.0], days)
    out = btc_inputs.load_all()
    _assert_unavailable(out["realized_cap"])
    _assert_unavailable(out["nupl"])


@pytest.mark.xfail(strict=True, reason=_INPUTS_DEFECT)
def test_mvrv_nonfinite_derived_identity_is_unavailable(root: Path) -> None:
    """Non-finite mvrv leaves realized_cap and nupl unavailable, never 0 or 1."""
    days = _days("2024-01-01", "2024-01-02")
    _put(root, "coinmetrics", "mcap_usd", [100.0, 100.0], days)
    _put(root, "coinmetrics", "mvrv", [float("inf"), float("-inf")], days)
    out = btc_inputs.load_all()
    _assert_unavailable(out["realized_cap"])
    _assert_unavailable(out["nupl"])


@pytest.mark.xfail(strict=True, reason=_INPUTS_DEFECT)
def test_nonpositive_stablecoin_denominator_ssr_is_unavailable(root: Path) -> None:
    """Stablecoin denominator <= 0 or non-finite leaves ssr unavailable."""
    days = _days("2024-01-01", "2024-01-02", "2024-01-03")
    _put(root, "coinmetrics", "mcap_usd", [100.0, 100.0, 100.0], days)
    _put(root, "coinmetrics", "mvrv", [2.0, 2.0, 2.0], days)
    _put(root, "defillama", "stablecoins", [0.0, -5.0, float("inf")], days)
    out = btc_inputs.load_all()
    _assert_unavailable(out["ssr"])


@pytest.mark.xfail(strict=True, reason=_INPUTS_DEFECT)
def test_nonpositive_supply_denominator_share_is_unavailable(root: Path) -> None:
    """Supply denominator <= 0 or non-finite leaves the share unavailable, never 0 or 1."""
    days = _days("2024-01-01", "2024-01-02", "2024-01-03")
    _put(root, "bgeo", "supply_in_profit", [100.0, 100.0, 100.0], days)
    _put(root, "coinmetrics", "supply", [0.0, -10.0, float("inf")], days)
    out = btc_inputs.load_all()
    _assert_unavailable(out["supply_in_profit_pct"])


def test_nan_parents_stay_unavailable(root: Path) -> None:
    """A NaN parent is already unavailable on the unpatched tree and stays unavailable."""
    days = _days("2024-01-01")
    _put(root, "coinmetrics", "mcap_usd", [100.0], days)
    _put(root, "coinmetrics", "mvrv", [float("nan")], days)
    _put(root, "defillama", "stablecoins", [float("nan")], days)
    _put(root, "bgeo", "supply_in_profit", [100.0], days)
    _put(root, "coinmetrics", "supply", [float("nan")], days)
    out = btc_inputs.load_all()
    _assert_unavailable(out["realized_cap"])
    _assert_unavailable(out["nupl"])
    _assert_unavailable(out["ssr"])
    _assert_unavailable(out["supply_in_profit_pct"])


def test_finite_positive_denominators_keep_the_identity(root: Path) -> None:
    """Honest parents keep the D41 numbers on both trees."""
    days = _days("2024-01-01")
    _put(root, "coinmetrics", "mcap_usd", [100.0], days)
    _put(root, "coinmetrics", "mvrv", [2.0], days)
    _put(root, "defillama", "stablecoins", [10.0], days)
    _put(root, "bgeo", "supply_in_profit", [50.0], days)
    _put(root, "coinmetrics", "supply", [200.0], days)
    out = btc_inputs.load_all()
    assert float(out["realized_cap"].iloc[-1]) == pytest.approx(50.0)
    assert float(out["nupl"].iloc[-1]) == pytest.approx(0.5)
    assert float(out["ssr"].iloc[-1]) == pytest.approx(10.0)
    assert float(out["supply_in_profit_pct"].iloc[-1]) == pytest.approx(0.25)


def test_cycle_thesis_reads_no_onchain_valuation_family() -> None:
    src = inspect.getsource(btc_cycle_thesis).lower()
    for token in ("mvrv", "nupl", "sopr", "realized_price", "coinmetrics"):
        assert token not in src


def test_valuation_readers_carry_no_knowledge_field() -> None:
    for fn in (btc_inputs._col, btc_inputs.load_all, CoinMetricsAdapter.fetch):
        src = inspect.getsource(fn)
        assert "received_at" not in src
        assert "knowledge_time" not in src
    bgeo_src = inspect.getsource(BgeoAdapter._fetch_metric)
    assert bgeo_src.count("record_response") == 1
    assert 'endpoint == "funding-rate"' in bgeo_src
    assert "unixTs" in bgeo_src


def test_response_evidence_sources_omit_valuation_metrics() -> None:
    from collectors import _crypto_observations as obs

    covered = set(obs.SOURCES)
    assert "bgeo_funding" in covered
    for name in (
        "mvrv", "nupl", "sopr", "sth_sopr", "lth_sopr",
        "realized_price", "sth_realized_price", "supply_in_profit",
    ):
        assert name not in covered


def test_coinmetrics_frame_has_no_knowledge_time(monkeypatch) -> None:
    payload = {
        "data": [{
            "time": "2024-01-01T00:00:00.000000000Z",
            "CapMVRVCur": "1.80",
            "CapMrktCurUSD": "800000000000",
        }],
    }

    class _Resp:
        def json(self):
            return payload

    adapter = CoinMetricsAdapter()
    monkeypatch.setattr(adapter, "http_get", lambda *args, **kwargs: _Resp())
    out = adapter.fetch(full_history=True)
    frame = out["mvrv"]
    assert list(frame.columns) == ["mvrv"]
    assert "received_at" not in frame.columns
    assert "received_at" not in frame.attrs
    assert frame.iloc[0, 0] == pytest.approx(1.80)


def test_bgeo_sopr_revision_has_no_earlier_cutoff(monkeypatch) -> None:
    from collectors import bgeo

    bodies = [
        [{"d": "2024-06-01T00:00:00Z", "unixTs": "1", "sopr": "1.50"}],
        [{"d": "2024-06-01T00:00:00Z", "unixTs": "2", "sopr": "0.80"}],
    ]

    class _Resp:
        status_code = 200
        headers: dict = {}

        def __init__(self, rows):
            self._rows = rows

        def json(self):
            return self._rows

        def raise_for_status(self):
            return None

    monkeypatch.setattr(bgeo.time, "sleep", lambda *args, **kwargs: None)
    monkeypatch.setattr(bgeo.requests, "get", lambda *args, **kwargs: _Resp(bodies.pop(0)))
    adapter = bgeo.BgeoAdapter()
    first = adapter._fetch_metric("sopr", "sopr", "2024-06-01")
    second = adapter._fetch_metric("sopr", "sopr", "2024-06-01")
    assert list(first.columns) == ["sopr"]
    assert "received_at" not in second.columns
    assert "unixTs" not in second.columns
    assert "received_at" not in second.attrs
    assert first.iloc[0, 0] == pytest.approx(1.50)
    assert second.iloc[0, 0] == pytest.approx(0.80)
    blocked = read_at_knowledge_cutoff(
        [
            {"date": "2024-06-01", "value": float(first.iloc[0, 0]), "received_at": None},
            {"date": "2024-06-01", "value": float(second.iloc[0, 0]), "received_at": None},
        ],
        "2024-06-03T00:00:00Z",
    )
    assert blocked["state"] == "unavailable"
    assert blocked["reason"] == "historical_reconstruction_unavailable"
    assert blocked["value"] is None


# ---------------------------------------------------------------------------
# SPEC OF RECORD for a later engine helper, not engine behavior.
# qualify_observation, qualify_fraction, and read_at_knowledge_cutoff are
# defined in this module. These tests do not exercise engine/btc_inputs.py
# or engine/btc_signals.py.
# ---------------------------------------------------------------------------


def test_later_revision_is_invisible_before_its_receipt() -> None:
    """SPEC OF RECORD for a later engine helper, not engine behavior."""
    rows = [
        {"date": "2024-06-01", "value": 1.5, "received_at": "2024-06-02T00:00:00Z"},
        {"date": "2024-06-01", "value": 0.8, "received_at": "2024-06-10T00:00:00Z"},
    ]
    early = read_at_knowledge_cutoff(rows, "2024-06-03T00:00:00Z")
    assert early == {"state": "observed", "reason": None, "value": 1.5}
    late = read_at_knowledge_cutoff(rows, "2024-06-10T00:00:00Z")
    assert late["value"] == 0.8
    before = read_at_knowledge_cutoff(rows, "2024-06-01T12:00:00Z")
    assert before["state"] == "unavailable"
    assert before["reason"] == "not_yet_received"
    assert before["value"] is None


def test_missing_clock_blocks_reconstruction_of_a_revised_print() -> None:
    """SPEC OF RECORD for a later engine helper, not engine behavior."""
    rows = [
        {"date": "2024-06-01", "value": 1.5, "received_at": None},
        {"date": "2024-06-01", "value": 0.8, "received_at": "2024-06-10T00:00:00Z"},
    ]
    out = read_at_knowledge_cutoff(rows, "2024-06-11T00:00:00Z")
    assert out["state"] == "unavailable"
    assert out["reason"] == "historical_reconstruction_unavailable"
    assert out["value"] is None
    assert out["value"] != 0.8


def test_unit_change_is_unavailable_not_a_number() -> None:
    """SPEC OF RECORD for a later engine helper, not engine behavior."""
    found = qualify_observation(
        1.8, unit="USD", expected_unit="ratio", denominator=1.0,
        definition_id="CapMVRVCur", expected_definition="CapMVRVCur",
    )
    assert found == {"state": "unavailable", "reason": "unit_change", "value": None}


def test_definition_change_drops_the_number() -> None:
    """SPEC OF RECORD for a later engine helper, not engine behavior."""
    found = qualify_observation(
        1.8, unit="ratio", expected_unit="ratio", denominator=1.0,
        definition_id="CapMVRVFF", expected_definition="CapMVRVCur",
    )
    assert found == {
        "state": "unavailable", "reason": "metric_definition_change", "value": None,
    }


def test_bad_denominator_is_unavailable_not_inf_or_one() -> None:
    """SPEC OF RECORD for a later engine helper, not engine behavior."""
    for denominator in (None, 0, 0.0, float("nan"), float("inf"), -1.0):
        found = qualify_fraction(
            100.0, unit="BTC", expected_unit="BTC", denominator=denominator,
            definition_id="sip/supply", expected_definition="sip/supply",
        )
        assert found["state"] == "unavailable"
        assert found["reason"] == "unavailable_denominator"
        assert found["value"] is None


def test_fraction_outside_unit_interval_is_unavailable_not_clipped() -> None:
    """SPEC OF RECORD for a later engine helper, not engine behavior."""
    found = qualify_fraction(
        2.0, unit="BTC", expected_unit="BTC", denominator=1.0,
        definition_id="sip/supply", expected_definition="sip/supply",
    )
    assert found["state"] == "unavailable"
    assert found["reason"] == "metric_definition_change"
    assert found["value"] is None
    assert found["value"] != 1.0


def test_missing_value_is_unavailable_not_zero() -> None:
    """SPEC OF RECORD for a later engine helper, not engine behavior."""
    found = qualify_observation(
        None, unit="ratio", expected_unit="ratio", denominator=1.0,
        definition_id="CapMVRVCur", expected_definition="CapMVRVCur",
    )
    assert found == {"state": "unavailable", "reason": "value_unavailable", "value": None}
    assert found["value"] != 0


def test_finite_matching_observation_keeps_its_number() -> None:
    """SPEC OF RECORD for a later engine helper, not engine behavior."""
    found = qualify_fraction(
        0.42, unit="BTC", expected_unit="BTC", denominator=19_000_000.0,
        definition_id="sip/supply", expected_definition="sip/supply",
    )
    assert found["state"] == "observed"
    assert found["value"] == pytest.approx(0.42)
