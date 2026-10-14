"""C19 WP11 acceptance pins (MAS-263): the MRI release_forecast.v2 reader and the
expectation read, exactly as already shipped. Hermetic: tmp_path fixtures, fixed
`today`, no data/ reads, no network. No production code is exercised beyond
engine.event_window._read_mri_surprise_dispersion and
engine.release_market_context.compute_expectation_read.

N1 legacy payloads are refused outright; N2 nearest-future element with an exact
release-type match; N3 the mixed nowcast/market median is a labelled expectation
median with its sources, never a street consensus; N5 sigma_surprise comes only
from surprise_skew.sigma, with no revision-field substitute and no fallback."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from engine import event_window as ew
from engine.release_market_context import compute_expectation_read

_TODAY = date(2026, 10, 12)
_ASOF = "2026-10-11T22:05:00Z"


def _write(tmp_path, payload, name="release_forecast.json"):
    p = tmp_path / name
    p.write_text(json.dumps(payload))
    return p


def _v2(upcoming):
    return {"schema": "release_forecast.v2", "asof": _ASOF, "upcoming": upcoming}


def _el(release_type, release_date, sigma=0.5, **extra):
    el = {
        "release_type": release_type,
        "period": "2026-09",
        "release_date": release_date,
        "surprise_skew": {"sigma": sigma, "sigma_scale_pp": 0.2, "tag": "inline"},
    }
    el.update(extra)
    return el


# ---------------------------------------------------------------- N1
@pytest.mark.parametrize(
    "payload",
    [
        {"CPI": {"surprise_skew": {"sigma": 0.3}, "asof": "2026-10-09"}},
        {"schema": "release_forecast.v1", "asof": _ASOF,
         "upcoming": [_el("cpi_headline", "2026-10-20")]},
        {"schema": "release_forecast.v2", "asof": _ASOF,
         "upcoming": {"cpi_headline": _el("cpi_headline", "2026-10-20")}},
        [_el("cpi_headline", "2026-10-20")],
    ],
    ids=["legacy-uppercase-keys", "v1-schema", "upcoming-not-a-list", "bare-list"],
)
def test_n1_non_v2_envelope_is_refused_outright(tmp_path, payload):
    p = _write(tmp_path, payload)
    assert ew._read_mri_surprise_dispersion("CPI", today=_TODAY, paths=[p]) is None


# ---------------------------------------------------------------- N2
def test_n2_nearest_future_exact_type_element_wins(tmp_path):
    p = _write(tmp_path, _v2([
        _el("cpi_headline", "2026-10-01", sigma=9.0),   # past: skipped
        _el("cpi_core", "2026-10-14", sigma=8.0),       # nearer, wrong type: skipped
        _el("cpi_headline", "2026-11-13", sigma=7.0),   # later future
        _el("cpi_headline", None, sigma=6.0),           # undated: skipped
        _el("cpi_headline", "not-a-date", sigma=5.0),   # unparseable: skipped
        _el("cpi_headline", "2026-10-20", sigma=1.5),   # nearest future, exact type
    ]))
    r = ew._read_mri_surprise_dispersion("CPI", today=_TODAY, paths=[p])
    assert r is not None
    assert r["release_date"] == "2026-10-20"
    assert r["forecast_release_type"] == "cpi_headline"
    assert r["sigma_surprise"] == pytest.approx(1.5)
    assert r["release_type"] == "CPI"


def test_n2_release_type_match_is_exact_never_prefix(tmp_path):
    p = _write(tmp_path, _v2([_el("cpi_core", "2026-10-14", sigma=-0.17)]))
    assert ew._read_mri_surprise_dispersion("CPI", today=_TODAY, paths=[p]) is None
    r = ew._read_mri_surprise_dispersion("cpi_core", today=_TODAY, paths=[p])
    assert r is not None
    assert r["forecast_release_type"] == "cpi_core"
    assert r["sigma_surprise"] == pytest.approx(-0.17)


def test_n2_release_dated_today_counts_as_upcoming(tmp_path):
    p = _write(tmp_path, _v2([_el("nfp", "2026-10-12", sigma=0.25)]))
    r = ew._read_mri_surprise_dispersion("NFP", today=_TODAY, paths=[p])
    assert r is not None and r["release_date"] == "2026-10-12"


# ---------------------------------------------------------------- N3
def test_n3_mixed_expectation_is_a_labelled_median_not_street_consensus():
    read = compute_expectation_read(
        0.3,
        {"cleveland_nowcast": 0.2, "kalshi": 0.4, "naive_prior": 9.9, "trailing_3m": -9.9},
        0.4,
    )
    assert read is not None
    assert set(read) == {"tag", "delta_pp", "standardized", "expectation_median",
                         "sources", "n_sources"}
    assert read["sources"] == ["cleveland_nowcast", "kalshi"]
    assert read["n_sources"] == 2
    assert read["expectation_median"] == pytest.approx(0.3)
    assert "consensus" not in json.dumps(read).lower()


def test_n3_trend_benchmarks_alone_produce_no_expectation_read():
    assert compute_expectation_read(
        0.3, {"naive_prior": 0.1, "trailing_3m": 0.2, "ar_model": 0.3}, 0.4) is None


def test_n3_reader_passes_expectation_read_through_without_relabelling(tmp_path):
    er = compute_expectation_read(0.3, {"cleveland_nowcast": 0.2, "polymarket": 0.25}, 0.4)
    p = _write(tmp_path, _v2([_el("cpi_headline", "2026-10-20", expectation_read=er)]))
    r = ew._read_mri_surprise_dispersion("CPI", today=_TODAY, paths=[p])
    assert r is not None
    assert r["expectation_read"] == er
    assert not [k for k in r if "consensus" in k.lower()]


# ---------------------------------------------------------------- N5
def test_n5_sigma_surprise_comes_only_from_surprise_skew_sigma(tmp_path):
    p = _write(tmp_path, _v2([_el(
        "cpi_headline", "2026-10-20", sigma=1.25,
        revision_pp=0.5, revision_surprise=2.0, revision_sigma=3.0,
    )]))
    r = ew._read_mri_surprise_dispersion("CPI", today=_TODAY, paths=[p])
    assert r is not None
    assert r["sigma_surprise"] == pytest.approx(1.25)
    assert r["available"] is True
    assert not [k for k in r if "revision" in k.lower()]


def test_n5_missing_sigma_has_no_fallback(tmp_path):
    el = _el("cpi_headline", "2026-10-20", revision_pp=0.5, revision_surprise=2.0)
    el["surprise_skew"] = {"sigma_scale_pp": 0.2, "tag": "inline"}
    p = _write(tmp_path, _v2([el]))
    r = ew._read_mri_surprise_dispersion("CPI", today=_TODAY, paths=[p])
    assert r is not None
    assert r["sigma_surprise"] is None
    assert r["available"] is False
    assert r["sigma_scale_pp"] == pytest.approx(0.2)

# ---------------------------------------------------------------- N4 (vintage gate)
_NOW = datetime(2026, 10, 12, 14, 0, tzinfo=timezone.utc)


def _v2_asof(asof, upcoming=None, drop_asof=False):
    payload = {"schema": "release_forecast.v2", "asof": asof,
               "upcoming": upcoming if upcoming is not None else [_el("cpi_headline", "2026-10-20")]}
    if drop_asof:
        del payload["asof"]
    return payload


@pytest.mark.parametrize("asof", ["2026-10-11T22:05:00Z", "2026-10-12T14:00:00Z", "2026-10-12T22:00:00+08:00"])
def test_n4_instant_asof_at_or_before_now_is_admitted(tmp_path, asof):
    p = _write(tmp_path, _v2_asof(asof))
    r = ew._read_mri_surprise_dispersion("CPI", today=_TODAY, paths=[p], now=_NOW)
    assert r is not None
    assert r["asof_precision"] == "instant"
    assert r["consumed_asof"] == asof


@pytest.mark.parametrize("asof", ["2026-10-12T14:00:01Z", "2026-10-12T23:00:00+08:00"])
def test_n4_instant_asof_after_now_is_refused(tmp_path, asof):
    p = _write(tmp_path, _v2_asof(asof))
    assert ew._read_mri_surprise_dispersion("CPI", today=_TODAY, paths=[p], now=_NOW) is None


def test_n4_date_only_asof_same_day_is_refused(tmp_path):
    p = _write(tmp_path, _v2_asof("2026-10-12"))
    assert ew._read_mri_surprise_dispersion("CPI", today=_TODAY, paths=[p], now=_NOW) is None


def test_n4_date_only_asof_prior_day_is_admitted(tmp_path):
    p = _write(tmp_path, _v2_asof("2026-10-11"))
    r = ew._read_mri_surprise_dispersion("CPI", today=_TODAY, paths=[p], now=_NOW)
    assert r is not None
    assert r["asof_precision"] == "date"
    assert r["consumed_asof"] == "2026-10-11"


@pytest.mark.parametrize(
    "asof,drop",
    [(None, True), (None, False), ("", False), ("not-a-date", False), ("2026-10-11T22:05:00", False), (20261011, False)],
    ids=["key-absent", "null", "empty", "unparseable", "naive-instant", "non-string"],
)
def test_n4_missing_or_unusable_asof_is_refused(tmp_path, asof, drop):
    p = _write(tmp_path, _v2_asof(asof, drop_asof=drop))
    assert ew._read_mri_surprise_dispersion("CPI", today=_TODAY, paths=[p], now=_NOW) is None


def test_n4_now_kwarg_sets_the_consumption_instant(tmp_path):
    p = _write(tmp_path, _v2_asof("2026-10-12T10:00:00Z"))
    day = date(2026, 10, 12)
    before = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)
    after = datetime(2026, 10, 12, 11, 0, tzinfo=timezone.utc)
    assert ew._read_mri_surprise_dispersion("CPI", today=day, paths=[p], now=before) is None
    r = ew._read_mri_surprise_dispersion("CPI", today=day, paths=[p], now=after)
    assert r is not None and r["asof_precision"] == "instant"
    assert ew._read_mri_surprise_dispersion("CPI", today=day, paths=[p], now=datetime(2026, 10, 12, 11, 0)) is None
