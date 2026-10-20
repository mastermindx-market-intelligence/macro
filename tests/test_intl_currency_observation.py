"""Currency value, calendar windows, source identity and independent engine clocks."""
from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import json

import pandas as pd
import pytest

from lib import config
from lib.intl_country_assessment import build_country_assessments
from lib.intl_currency_observation import (
    SPECS, build_currency_observation, captured_source_context,
    currency_observation_view, incumbent_source_context, reference_date,
)

TODAY = date(2026, 10, 20)


def context(cc="KR"):
    spec = SPECS[cc]
    return incumbent_source_context(cc, {"fx": spec[1], "fx_invert": spec[2] == "local_per_USD"})


def observation(cc="KR", start=100.0, end=80.0, *, end_date="2026-10-19",
                start_date="2026-07-17", source=None, extra=()):
    return build_currency_observation(
        cc, [(start_date, start), (end_date, end), *extra],
        today=TODAY, source=source if source is not None else context(cc))


def signed(raw):
    raw = deepcopy(raw)
    payload = {k: v for k, v in raw.items() if k != "evidence_sha256"}
    raw["evidence_sha256"] = sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode()).hexdigest()
    return raw


@pytest.mark.parametrize("cc,start,end", [("KR", 100, 80), ("AU", 0.8, 1.0)])
def test_same_currency_appreciation_under_opposite_quote_conventions(cc, start, end):
    raw = observation(cc, start, end)
    assert raw["value"] == pytest.approx(25.0)
    view = currency_observation_view(raw, cc, today=TODAY)
    assert view["available"] and view["value"] == pytest.approx(25.0)
    assert view["start_date"] == "2026-07-17"
    assert view["reference_target"] == "2026-07-19"
    assert view["end_date"] == "2026-10-19"


def test_inverse_quote_depreciation_is_exact_reciprocal():
    raw = observation("KR", 25, 30)
    assert raw["value"] == pytest.approx(-16.66666666666667)
    assert raw["value"] != pytest.approx(-20.0)


@pytest.mark.parametrize("end,expected", [
    (date(2026, 5, 31), date(2026, 2, 28)),
    (date(2024, 5, 31), date(2024, 2, 29)),
    (date(2026, 1, 31), date(2025, 10, 31)),
    (date(2026, 12, 31), date(2026, 9, 30)),
])
def test_calendar_window_clamps_month_ends(end, expected):
    assert reference_date(end) == expected


@pytest.mark.parametrize("gap,available", [(0, True), (7, True), (8, False)])
def test_calendar_anchor_requires_an_actual_close_no_more_than_seven_days_before(gap, available):
    raw = observation(start_date=(date(2026, 7, 19) - timedelta(days=gap)).isoformat())
    assert (raw["status"] == "available") is available
    if not available:
        assert raw["reason"] == "reference_too_distant"


def test_latest_observation_on_or_before_calendar_anchor_is_used():
    raw = observation(extra=[("2026-07-16", 200), ("2026-07-20", 500)])
    assert raw["start"] == {"date": "2026-07-17", "quote": 100.0}


@pytest.mark.parametrize("age,quality", [(1, "current"), (4, "current"), (5, "dated"), (14, "dated"), (15, "missing")])
def test_end_clock_has_explicit_current_dated_and_withheld_states(age, quality):
    end = TODAY - timedelta(days=age)
    raw = observation(end_date=end.isoformat(), start_date=reference_date(end).isoformat())
    view = currency_observation_view(raw, "KR", today=TODAY)
    assert view["quality"] == quality
    assert view["available"] is (age <= 14)


def test_unfinished_same_day_and_future_bars_do_not_displace_completed_observation():
    raw = observation(extra=[("2026-10-20", 5), ("2026-10-21", 6)])
    assert raw["end"]["date"] == "2026-10-19"
    assert raw["value"] == pytest.approx(25.0)


def test_duplicate_identical_quotes_collapse_but_selected_conflicts_withhold():
    assert observation(extra=[("2026-10-19", 80)])["status"] == "available"
    assert observation(extra=[("2026-10-19", 81)])["reason"] == "conflicting_observation"
    assert observation(extra=[("2026-07-17", 101)])["reason"] == "conflicting_observation"
    assert observation(extra=[("2026-07-16", 30), ("2026-07-16", 40)])["status"] == "available"


@pytest.mark.parametrize("value", [True, False, 0, -1, float("nan"), float("inf"), float("-inf"), 10**500, "80", None])
def test_invalid_quote_is_never_used(value):
    raw = observation(end=value)
    assert raw["status"] == "unavailable"


@pytest.mark.parametrize("observations", [None, {}, 1, "bad", [None, [], ["20261019", 80], ["invalid", 5]]])
def test_bad_series_withholds_without_escaping(observations):
    raw = build_currency_observation("KR", observations, today=TODAY, source=context())
    assert raw["status"] == "unavailable"


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), 10**500, None])
def test_malformed_serialized_return_withholds_without_exception(value):
    raw = observation()
    raw["value"] = value
    assert not currency_observation_view(raw, "KR", today=TODAY)["available"]


@pytest.mark.parametrize("key,value", [
    ("cc", "JP"), ("currency", "JPY"), ("counter_currency", "EUR"),
    ("ticker", "USDJPY=X"), ("quote_convention", "USD_per_local"),
    ("method", "pct_change_63"), ("unit", "index"), ("same_day_policy", "include"),
    ("reference_target", "2026-07-20"),
])
def test_rehashed_but_wrong_identity_or_method_stays_withheld(key, value):
    raw = observation()
    raw[key] = value
    assert not currency_observation_view(signed(raw), "KR", today=TODAY)["available"]


def test_digest_and_endpoint_arithmetic_are_both_verified():
    raw = observation()
    raw["value"] += 1
    assert not currency_observation_view(raw, "KR", today=TODAY)["available"]
    assert not currency_observation_view(signed(raw), "KR", today=TODAY)["available"]
    raw = observation()
    raw["evidence_sha256"] = "0" * 64
    assert not currency_observation_view(raw, "KR", today=TODAY)["available"]


@pytest.mark.parametrize("key,value", [
    ("provider", "Different feed"), ("collector", "other"), ("price_field", "adjusted_close"),
    ("source_url", "https://example.com/rates"), ("retrieved_at", "2026-10-20T00:00:00Z"),
])
def test_configured_store_never_claims_an_unrecorded_retrieval_or_other_feed(key, value):
    source = context()
    source[key] = value
    assert observation(source=source)["reason"] == "source_unavailable"


def test_captured_response_preserves_real_receipt_and_registered_provider_alias():
    source = captured_source_context(
        "JP", retrieved_at="2026-10-20T03:41:08.547672+00:00",
        response_sha256="c" * 64, provider_symbol="JPY=X")
    raw = observation("JP", source=source)
    assert raw["status"] == "available"
    view = currency_observation_view(raw, "JP", today=TODAY)
    assert view["retrieved_at"] == source["retrieved_at"]
    assert view["source_url"] == "https://finance.yahoo.com/quote/JPY%3DX/history/"


@pytest.mark.parametrize("changes", [
    {"retrieved_at": "2026-10-20T12:00:00"},
    {"retrieved_at": "2026-10-20T23:30:00-02:00"},
    {"retrieved_at": "0001-01-01T00:00:00+01:00"},
    {"response_sha256": "not-a-hash"},
    {"provider_symbol": "AUDUSD=X"},
    {"dataset_url": "https://example.com/rates"},
])
def test_captured_source_requires_aware_nonfuture_utc_receipt_and_correct_identity(changes):
    source = captured_source_context("JP", retrieved_at="2026-10-20T03:41:08Z",
                                     response_sha256="c" * 64, provider_symbol="JPY=X")
    source.update(changes)
    assert observation("JP", source=source)["reason"] == "source_unavailable"


def test_currency_registry_matches_actual_incumbent_country_config():
    countries = config.load()["intl"]["countries"]
    assert set(SPECS) == set(countries)
    for cc in SPECS:
        assert incumbent_source_context(cc, countries[cc]) is not None
    assert incumbent_source_context("KR", {"fx": "USDKRW=X", "fx_invert": False}) is None


def test_assessment_uses_currency_clock_without_refreshing_stale_equity():
    rec = {"cc": "KR", "date": "2026-10-20",
           "macro": {"fx_strength_3m": -99}, "macro_asof": {"fx_strength_3m": "2026-10-20"},
           "equity": {"as_of": "2026-07-01", "above_50d": True, "above_200d": True,
                      "trend_200d_complete": True, "off_52w_high": -2},
           "currency_observation": observation()}
    before = deepcopy(rec)
    result = build_country_assessments({"records": [rec]}, today=TODAY)["countries"][0]["market"]
    assert result["state"] == "unknown" and result["drawdown"] is None
    assert result["fx_3m"] == pytest.approx(25.0) and result["fx_as_of"] == "2026-10-19"
    assert rec == before
    rec["currency_observation"]["end"]["date"] = "2026-07-01"
    assert build_country_assessments({"records": [rec]}, today=TODAY)["countries"][0]["market"]["fx_3m"] is None


def test_normal_record_bridge_preserves_legacy_macro_regime_and_history(monkeypatch):
    from engine import intl_run
    dates = pd.to_datetime(["2026-07-17", "2026-10-15", "2026-10-19", "2026-10-20"])
    closes = pd.DataFrame({"USDKRW=X": [100.0, 90.0, 80.0, 5.0]}, index=dates)
    regime = pd.DataFrame({
        "quad": ["Q1"], "quad_name": ["Expansion"], "growth_score": [1.0],
        "inflation_score": [0.5], "regime_confidence": [0.8], "liquidity": ["neutral"],
        "recession_score": [10.0], "growth_n_components": [2], "inflation_n_components": [2],
        "c_fx": [55.0],
    }, index=pd.to_datetime(["2026-10-15"]))
    monkeypatch.setattr(intl_run.intl_inputs, "country_frame", lambda *args: regime)
    monkeypatch.setattr(intl_run, "classify", lambda value: value)
    monkeypatch.setattr(intl_run, "component_evidence_at", lambda *args: {"preserved": True})
    monkeypatch.setattr(intl_run.intl_inputs, "latest_macro_snapshot",
                        lambda *args: {"fx_strength_3m": -99, "cpi_yoy": 2.0, "gdp_yoy": 1.0})
    monkeypatch.setattr(intl_run.intl_inputs, "macro_freshness", lambda *args: {})
    before_closes = closes.copy(deep=True)
    old, old_history = intl_run.country_record("KR", closes, pd.DataFrame(), {})
    new, new_history = intl_run.country_record("KR", closes, pd.DataFrame(), {},
                                              today=TODAY, fx_source=context())
    currency = new.pop("currency_observation")
    assert new == old
    assert new["macro"]["fx_strength_3m"] == -99
    assert new["macro_asof"]["fx_strength_3m"] == "2026-10-15"
    assert currency == observation(extra=[("2026-10-15", 90), ("2026-10-20", 5)])
    assert currency["end"]["date"] == "2026-10-19"
    pd.testing.assert_frame_equal(old_history, new_history)
    pd.testing.assert_frame_equal(closes, before_closes)


def test_captured_intraday_quote_never_matures_merely_by_replaying_later():
    source = captured_source_context("KR", retrieved_at="2026-10-20T03:44:44Z",
                                     response_sha256="d" * 64, provider_symbol="USDKRW=X")
    observations = [("2026-07-17", 100), ("2026-07-20", 99),
                    ("2026-10-19", 80), ("2026-10-20", 5)]
    first = build_currency_observation("KR", observations, today=TODAY, source=source)
    later = build_currency_observation("KR", observations, today=TODAY + timedelta(days=1), source=source)
    assert first == later
    assert later["end"]["date"] == "2026-10-19"


def test_rehashed_captured_endpoint_cannot_follow_the_capture_day():
    later = TODAY + timedelta(days=1)
    raw = build_currency_observation("KR", [("2026-07-20", 100), ("2026-10-20", 80)],
                                     today=later, source=context())
    raw["source"] = captured_source_context(
        "KR", retrieved_at="2026-10-20T03:44:44Z",
        response_sha256="d" * 64, provider_symbol="USDKRW=X")
    assert not currency_observation_view(signed(raw), "KR", today=later)["available"]


def test_capture_receipt_before_the_observation_cannot_support_it():
    raw = observation()
    raw["source"] = captured_source_context(
        "KR", retrieved_at="2026-10-18T03:44:44Z",
        response_sha256="d" * 64, provider_symbol="USDKRW=X")
    assert not currency_observation_view(signed(raw), "KR", today=TODAY)["available"]


def test_assessment_default_evaluation_day_uses_the_engine_utc_clock(monkeypatch):
    from datetime import datetime, timezone
    from lib import intl_country_assessment
    class Clock:
        @staticmethod
        def now(tz):
            assert tz is timezone.utc
            return datetime(2031, 1, 2, 0, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(intl_country_assessment, "datetime", Clock)
    assert intl_country_assessment.build_country_assessments(
        {"records": []})["evaluated_at"] == "2031-01-02"


@pytest.mark.parametrize("cc", list(SPECS))
def test_retained_seven_currency_histories_match_independent_decimal_endpoints(cc):
    from pathlib import Path
    fixture = json.loads((Path(__file__).resolve().parents[1] /
        "tests/fixtures/intl_currency_observations_20261020.json").read_text())
    case = next(case for case in fixture["cases"] if case["cc"] == cc)
    raw = build_currency_observation(cc, case["observations"], today=TODAY, source=case["source"])
    expected = case["expected"]
    assert raw["start"] == expected["start"] and raw["end"] == expected["end"]
    assert raw["reference_target"] == expected["reference_target"]
    assert raw["value"] == pytest.approx(float(expected["value_decimal"]), abs=1e-12)
    assert f'{raw["value"]:+.2f}%' == expected["display_percent"]
    round_trip = currency_observation_view(json.loads(json.dumps(raw)), cc, today=TODAY)
    assert round_trip["available"] and round_trip["quality"] == "current"


@pytest.mark.parametrize("evaluated,quality,shown", [
    (TODAY, "current", "+25.00%"),
    (date(2026, 10, 25), "dated", "+25.00%"),
    (date(2026, 11, 3), "missing", "—"),
])
def test_rendered_currency_cell_keeps_its_own_clock_and_withholds_stale_values(evaluated, quality, shown):
    from pathlib import Path
    import re
    from jinja2 import Environment, FileSystemLoader
    from engine import i18n
    rec = {"cc": "KR", "macro": {"fx_strength_3m": 999},
           "macro_asof": {"fx_strength_3m": evaluated.isoformat()},
           "equity": {"as_of": "2026-10-15"},
           "currency_observation": observation()}
    assessment = build_country_assessments({"records": [rec]}, today=evaluated)
    env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parents[1]/"templates"))
    env.globals.update(t=i18n.t, td=i18n.td, tr=i18n.tr)
    html = env.get_template("intl_country_cockpit.html.j2").render(intl_analysis=assessment)
    cell = re.search(r'<div class="imc-fx-read".*?</div>', html, re.S).group()
    ledger = re.search(r'<tr class="imc-currency-ledger".*?</tr>', html, re.S).group()
    assert f'data-fx-quality="{quality}"' in cell and shown in cell
    assert "vs USD · 3 months" in cell and "兑美元 · 3个月" in cell
    assert "Equity observations" in html and "股市观测" in html
    if quality == "missing":
        assert "2026-10-19" not in cell and "href=" not in ledger
        assert "Observation unavailable" in cell
    else:
        assert "2026-10-19" in cell and "2026-10-15" not in cell
        assert "2026-07-17" in ledger and "2026-10-19" in ledger
        assert "https://finance.yahoo.com/quote/USDKRW%3DX/history/" in ledger
        assert "Quoted rates" in html and "Reference date" in html
        assert ("Dated · " in cell) is (quality == "dated")


@pytest.mark.parametrize("cc", [None, [], {}])
def test_malformed_country_identity_is_withheld(cc):
    assert incumbent_source_context(cc, {}) is None
    assert build_currency_observation(cc, [], today=TODAY, source={})["status"] == "unavailable"
    assert not currency_observation_view({}, cc, today=TODAY)["available"]
