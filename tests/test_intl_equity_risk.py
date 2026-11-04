"""International equity-risk tests (engine/intl_equity_risk.py) — DISPLAY-ONLY
drawdown-risk gauge + own-history extension grade, injected synthetic indices."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import intl_equity_risk as er  # noqa: E402
from lib.intl_country_inputs import validate_equity_evidence
from lib.intl_country_assessment import _market


def _matrix(n: int = 500) -> pd.DataFrame:
    idx = pd.bdate_range("2014-01-01", periods=n)
    rng = np.random.default_rng(7)
    # AA: steady uptrend near highs; BB: deep drawdown / below trend
    aa = 100 * np.cumprod(1 + rng.normal(0.0006, 0.008, n))
    bb = 100 * np.cumprod(1 + rng.normal(0.0006, 0.012, n))
    bb[-60:] = bb[-60] * np.linspace(1.0, 0.72, 60)        # -28% recent drawdown
    return pd.DataFrame({"AA": aa, "BB": bb}, index=idx)


def test_bands_and_bounds():
    out = er.equity_risk_all(_matrix())
    assert set(out) == {"AA", "BB"}
    for cc, r in out.items():
        assert 0 <= r["drawdown_risk"] <= 100
        assert r["drawdown_band"] in {"low", "watch", "elevated", "n/a"}
        assert r["ext_grade"] in {"intrend", "steady", "stretched", "parabolic", "na"}
        assert isinstance(r["bubble_flag"], bool)


def test_drawdown_market_scores_higher():
    out = er.equity_risk_all(_matrix())
    assert out["BB"]["drawdown_risk"] > out["AA"]["drawdown_risk"]
    assert out["BB"]["off_52w_high"] < out["AA"]["off_52w_high"]


def test_empty_matrix():
    assert er.equity_risk_all(pd.DataFrame()) == {}


def test_band_helper():
    assert er._band(None) == "n/a"
    assert er._band(10) == "low"
    assert er._band(45) == "watch"
    assert er._band(80) == "elevated"


_EQUITY_TEST_DAY = date(2026, 10, 15)


def _evidence_case(monkeypatch, *, n=300, values=None):
    if values is None:
        x = np.arange(n, dtype=float)
        values = 100.0 + x * 0.2 + np.sin(x / 4.0) * 3.0
    matrix = pd.DataFrame({"JP": values}, index=pd.bdate_range(end=_EQUITY_TEST_DAY, periods=n))
    monkeypatch.setattr(er.intl_inputs, "countries", lambda: {"JP": {"index": "^N225"}})
    monkeypatch.setattr(er, "index_matrix", lambda: matrix)
    return er.equity_risk_all()["JP"], matrix


def test_equity_canonical_identity_is_additive_and_never_applied_to_custom_matrices(monkeypatch):
    canonical, matrix = _evidence_case(monkeypatch)
    custom = er.equity_risk_all(matrix)["JP"]
    assert canonical["observation_evidence"]["source"]["symbol"] == "^N225"
    assert custom["observation_evidence"] is None
    assert {k: v for k, v in canonical.items() if k != "observation_evidence"} == {
        k: v for k, v in custom.items() if k != "observation_evidence"}
    monkeypatch.setattr(er.intl_inputs, "countries", lambda: {"JP": {"index": "^FTSE"}})
    assert er.equity_risk_all()["JP"]["observation_evidence"] is None


@pytest.mark.parametrize("n", [60, 99, 100, 199, 200, 252, 300])
def test_equity_evidence_exposes_actual_window_boundaries_and_partial_means(monkeypatch, n):
    equity, matrix = _evidence_case(monkeypatch, n=n)
    evidence = validate_equity_evidence(equity, "JP", today=_EQUITY_TEST_DAY)
    assert evidence is not None
    for key, target in (("mean_50", 50), ("mean_200", 200), ("recent_high", 252)):
        selected = matrix["JP"].iloc[-target:]
        window = evidence[key]
        assert window["observations"] == len(selected)
        assert window["start"] == selected.index[0].date().isoformat()
        assert window["end"] == selected.index[-1].date().isoformat()
    assert evidence["trend_200d_complete"] is (n >= 200)
    if n < 100:
        assert evidence["mean_200"]["value"] is None and evidence["above_200d"] is None
    else:
        assert evidence["mean_200"]["value"] == pytest.approx(matrix["JP"].iloc[-200:].mean())
    market = _market({"cc": "JP", "equity": equity}, _EQUITY_TEST_DAY)
    if n < 200:
        assert market["state"] == "unknown" and market["above_200d"] is None
        assert market["equity_evidence"] is not None


@pytest.mark.parametrize("bad_kind", ["duplicate", "midday", "timezone", "zero", "boolean"])
def test_equity_evidence_refuses_ambiguous_raw_dates_and_invalid_prices(monkeypatch, bad_kind):
    _, matrix = _evidence_case(monkeypatch)
    invalid = matrix.copy()
    if bad_kind == "duplicate":
        labels = list(invalid.index)
        labels[-1] = labels[-2]
        invalid.index = pd.DatetimeIndex(labels)
    elif bad_kind == "midday":
        labels = list(invalid.index)
        labels[-1] += pd.Timedelta(hours=12)
        invalid.index = pd.DatetimeIndex(labels)
    elif bad_kind == "timezone":
        invalid.index = invalid.index.tz_localize("UTC")
    elif bad_kind == "boolean":
        invalid = invalid.astype(bool)
    else:
        # Invalid source data outside the displayed trailing 252 must not be laundered.
        invalid.iloc[0, 0] = 0.0
    assert not er._valid_equity_source_series(invalid["JP"])


@pytest.mark.parametrize("path,value", [
    (("source", "symbol"), "^FTSE"),
    (("source", "source_url"), "https://example.com/index"),
    (("source", "auto_adjust"), 1),
    (("source", "date_basis"), "confirmed_final_close"),
    (("mean_50", "method"), "exponential_mean"),
    (("mean_50", "observations"), 49),
    (("mean_50", "observations"), True),
    (("mean_50", "start"), "2026-01-01"),
    (("mean_50", "end"), "2026-10-14"),
    (("mean_50", "value"), 1.0),
    (("mean_200", "minimum_observations"), 1),
    (("recent_high", "tie_policy"), "earliest"),
    (("recent_high", "high_date"), "2026-01-01"),
])
def test_equity_evidence_rejects_inconsistent_identity_or_arithmetic(monkeypatch, path, value):
    equity, _ = _evidence_case(monkeypatch)
    changed = deepcopy(equity)
    node = changed["observation_evidence"]
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    assert validate_equity_evidence(changed, "JP", today=_EQUITY_TEST_DAY) is None


def test_equity_evidence_binds_legacy_flags_drawdown_and_ordered_rows(monkeypatch):
    equity, _ = _evidence_case(monkeypatch)
    for key, value in (("above_50d", not equity["above_50d"]),
                       ("off_52w_high", equity["off_52w_high"] - 1),
                       ("price", equity["price"] + 0.01)):
        changed = deepcopy(equity)
        changed[key] = value
        assert validate_equity_evidence(changed, "JP", today=_EQUITY_TEST_DAY) is None
    changed = deepcopy(equity)
    rows = changed["observation_evidence"]["rows"]
    rows[0], rows[1] = rows[1], rows[0]
    assert validate_equity_evidence(changed, "JP", today=_EQUITY_TEST_DAY) is None


def test_equity_tied_high_uses_latest_actual_date_and_equality_is_not_above(monkeypatch):
    values = np.full(300, 100.0)
    values[-100] = values[-10] = 200.0
    equity, matrix = _evidence_case(monkeypatch, values=values)
    evidence = validate_equity_evidence(equity, "JP", today=_EQUITY_TEST_DAY)
    assert evidence["recent_high"]["high_date"] == matrix.index[-10].date().isoformat()
    assert evidence["drawdown_pct"] == -50.0
    flat, _ = _evidence_case(monkeypatch, values=np.full(300, 100.0))
    evidence = validate_equity_evidence(flat, "JP", today=_EQUITY_TEST_DAY)
    assert evidence["latest_close"] == evidence["mean_50"]["value"] == evidence["mean_200"]["value"]
    assert evidence["above_50d"] is False and evidence["above_200d"] is False
    assert evidence["drawdown_pct"] == 0.0


def test_equity_comparisons_use_unrounded_source_levels(monkeypatch):
    values = np.full(300, 100.001)
    values[-1] = 100.002
    equity, _ = _evidence_case(monkeypatch, values=values)
    evidence = validate_equity_evidence(equity, "JP", today=_EQUITY_TEST_DAY)
    assert equity["price"] == round(evidence["mean_50"]["value"], 2) == 100.0
    assert evidence["above_50d"] is True and evidence["above_200d"] is True


def test_equity_retains_dated_evidence_without_borrowing_page_or_acquisition_clocks(monkeypatch):
    equity, _ = _evidence_case(monkeypatch)
    evidence = validate_equity_evidence(equity, "JP", today=_EQUITY_TEST_DAY)
    assert evidence is not None and evidence["retrieved_at"] is None
    assert evidence["vintage_custody"] == "not_recorded" and evidence["session_finality"] == "not_verified"
    assert validate_equity_evidence(equity, "JP", today=_EQUITY_TEST_DAY - timedelta(days=1)) is None
    monthly = deepcopy(equity)
    monthly["as_of"] = monthly["observation_evidence"]["as_of"] = "2026-10"
    assert validate_equity_evidence(monthly, "JP", today=date(2026, 11, 1)) is None
    market = _market({"cc": "JP", "equity": equity}, _EQUITY_TEST_DAY + timedelta(days=30))
    assert market["current"] is False and market["state"] == "unknown"
    assert market["drawdown"] is None and market["equity_evidence"]["as_of"] == "2026-10-15"
    equity.pop("observation_evidence")
    market = _market({"cc": "JP", "date": "2026-10-15", "equity": equity}, _EQUITY_TEST_DAY)
    assert market["current"] is False and market["as_of"] is None
    assert market["equity_evidence"] is None


def test_canonical_equity_evidence_keeps_each_markets_own_last_observation(monkeypatch):
    _, matrix = _evidence_case(monkeypatch)
    matrix["KR"] = matrix["JP"]
    matrix.loc[matrix.index[-1], "KR"] = np.nan
    monkeypatch.setattr(er.intl_inputs, "countries",
                        lambda: {"JP": {"index": "^N225"}, "KR": {"index": "^KS11"}})
    out = er.equity_risk_all()
    jp = validate_equity_evidence(out["JP"], "JP", today=_EQUITY_TEST_DAY)
    kr = validate_equity_evidence(out["KR"], "KR", today=_EQUITY_TEST_DAY)
    assert jp["as_of"] == matrix.index[-1].date().isoformat()
    assert kr["as_of"] == matrix.index[-2].date().isoformat()
    assert kr["recent_high"]["start"] == matrix.index[-253].date().isoformat()
