"""C19 WP11 acceptance pins (MAS-263): the MRI release_forecast.v2 reader and the
expectation read, exactly as already shipped. Hermetic: tmp_path fixtures, fixed
`today`, no data/ reads, no network. No production code is exercised beyond
engine.event_window._read_mri_surprise_dispersion and
engine.release_market_context.compute_expectation_read and get_reaction_sensitivity.

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


# ---------------------------------------------------------------------------
# RIC #7965: hermetic pooled-regime reaction reader acceptance pins.
# Keep the existing full release-market-context suite's nightly data-gate copy;
# this exact nine-case block also executes in the incumbent MRI code gate.
# ---------------------------------------------------------------------------

from pathlib import Path
from engine.release_market_context import _ERA_LABEL, get_reaction_sensitivity


def _make_playbook(tmp_path: Path, cells: list[dict]) -> Path:
    p = tmp_path / "research" / "release_playbook" / "results" / "playbook_v1.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cells))
    return p


def _base_cells() -> list[dict]:
    """Minimal set of 2021plus h1 cells for cpi: hot/cold × dgs10_bp/spy_pct."""
    return [
        {"release": "cpi", "bucket": "hot",  "outcome": "dgs10_bp", "horizon": "h1",
         "era": _ERA_LABEL, "regime": None, "n": 20, "mean": 3.2,  "median": 2.0, "ci_lo": -0.85, "ci_hi": 8.3},
        {"release": "cpi", "bucket": "cold", "outcome": "dgs10_bp", "horizon": "h1",
         "era": _ERA_LABEL, "regime": None, "n": 20, "mean": -4.1, "median": -3.0,"ci_lo": -9.0,  "ci_hi": 0.5},
        {"release": "cpi", "bucket": "hot",  "outcome": "spy_pct",  "horizon": "h1",
         "era": _ERA_LABEL, "regime": None, "n": 21, "mean": -0.40,"median": -0.05,"ci_lo": -1.28, "ci_hi": 0.29},
        {"release": "cpi", "bucket": "cold", "outcome": "spy_pct",  "horizon": "h1",
         "era": _ERA_LABEL, "regime": None, "n": 21, "mean": 0.55, "median": 0.4,  "ci_lo": -0.1,  "ci_hi": 1.4},
    ]


class TestReactionSensitivity:
    def test_null_when_playbook_missing(self, tmp_path: Path):
        """Returns None when playbook file doesn't exist."""
        p = tmp_path / "research" / "release_playbook" / "results" / "playbook_v1.json"
        result = get_reaction_sensitivity("cpi_headline", p, current_regime="Q1")
        assert result is None

    def test_null_for_claims_release(self, tmp_path: Path):
        """Claims release type → None (no playbook family)."""
        cells = _base_cells()
        p = _make_playbook(tmp_path, cells)
        result = get_reaction_sensitivity("claims", p, current_regime="Q1")
        assert result is None

    def test_picks_2021plus_cells(self, tmp_path: Path):
        """Uses 2021plus era cells and returns correct mean values."""
        cells = _base_cells()
        p = _make_playbook(tmp_path, cells)
        result = get_reaction_sensitivity("cpi_headline", p, current_regime=None)
        assert result is not None
        assert result["era_basis"] == _ERA_LABEL
        assert result["dgs10_h1_hot_bp"] == pytest.approx(3.2, abs=1e-4)
        assert result["dgs10_h1_cold_bp"] == pytest.approx(-4.1, abs=1e-4)
        assert result["spy_h1_hot_pct"] == pytest.approx(-0.40, abs=1e-4)
        assert result["spy_h1_cold_pct"] == pytest.approx(0.55, abs=1e-4)

    def test_prefers_pooled_regime_cell_when_n_ge_threshold(self, tmp_path: Path):
        """Preregistered regime cells are era=all and beat the era-level fallback."""
        cells = _base_cells() + [
            # Regime-conditioned Q1 table is pooled across eras by the frozen playbook.
            {"release": "cpi", "bucket": "hot", "outcome": "dgs10_bp", "horizon": "h1",
             "era": "all", "regime": "Q1", "n": 10, "mean": 7.77, "median": 6.0,
             "ci_lo": 2.0, "ci_hi": 12.0},
        ]
        p = _make_playbook(tmp_path, cells)
        result = get_reaction_sensitivity("cpi_headline", p, current_regime="Q1")
        assert result is not None
        assert result["regime_cells_used"] is True
        assert result["regime_requested"] == "Q1"
        assert result["regime_basis"] == "all"
        assert result["regime_labels_revision_optimistic"] is True
        # The pooled Q1-conditioned cell should be used for hot dgs10.
        assert result["dgs10_h1_hot_bp"] == pytest.approx(7.77, abs=1e-4)
        hot_evidence = result["evidence"]["dgs10_h1_hot"]
        assert hot_evidence == {
            "n": 10,
            "mean": 7.77,
            "median": 6.0,
            "ci_lo": 2.0,
            "ci_hi": 12.0,
            "era": "all",
            "regime": "Q1",
            "revision_optimistic": True,
        }
        # Cold dgs10 falls back to 2021plus era-level (no qualified Q1 cold cell).
        assert result["dgs10_h1_cold_bp"] == pytest.approx(-4.1, abs=1e-4)
        cold_evidence = result["evidence"]["dgs10_h1_cold"]
        assert cold_evidence["n"] == 20
        assert cold_evidence["era"] == _ERA_LABEL
        assert cold_evidence["regime"] is None
        assert cold_evidence["revision_optimistic"] is False
        assert "revision_optimistic" in result["note"]

    def test_falls_back_when_regime_n_below_threshold(self, tmp_path: Path):
        """Regime-conditioned cell with n<8 is NOT used; falls back to era-level."""
        cells = _base_cells() + [
            # n=5 < _REGIME_MIN_N — should be ignored
            {"release": "cpi", "bucket": "hot", "outcome": "dgs10_bp", "horizon": "h1",
             "era": "all", "regime": "Q1", "n": 5, "mean": 99.0, "median": 99.0,
             "ci_lo": 0.0, "ci_hi": 99.0},
        ]
        p = _make_playbook(tmp_path, cells)
        result = get_reaction_sensitivity("cpi_headline", p, current_regime="Q1")
        assert result is not None
        assert result["regime_cells_used"] is False
        assert result["regime_requested"] == "Q1"
        assert result["regime_basis"] is None
        assert result["regime_labels_revision_optimistic"] is False
        assert result["dgs10_h1_hot_bp"] == pytest.approx(3.2, abs=1e-4)  # era-level
        assert result["evidence"]["dgs10_h1_hot"]["era"] == _ERA_LABEL
        assert result["evidence"]["dgs10_h1_hot"]["regime"] is None
        assert result["evidence"]["dgs10_h1_hot"]["revision_optimistic"] is False

    def test_nfp_family_mapped_correctly(self, tmp_path: Path):
        """nfp release type maps to 'nfp' playbook family."""
        cells = [
            {"release": "nfp", "bucket": "hot",  "outcome": "dgs10_bp", "horizon": "h1",
             "era": _ERA_LABEL, "regime": None, "n": 15, "mean": 5.1, "median": 4.0, "ci_lo": 1.0, "ci_hi": 9.0},
            {"release": "nfp", "bucket": "cold", "outcome": "dgs10_bp", "horizon": "h1",
             "era": _ERA_LABEL, "regime": None, "n": 15, "mean": -3.2,"median": -2.0,"ci_lo": -7.0, "ci_hi": 0.5},
            {"release": "nfp", "bucket": "hot",  "outcome": "spy_pct",  "horizon": "h1",
             "era": _ERA_LABEL, "regime": None, "n": 15, "mean": 0.3,  "median": 0.2, "ci_lo": -0.5, "ci_hi": 1.2},
            {"release": "nfp", "bucket": "cold", "outcome": "spy_pct",  "horizon": "h1",
             "era": _ERA_LABEL, "regime": None, "n": 15, "mean": -0.8, "median": -0.7,"ci_lo": -2.0, "ci_hi": 0.3},
        ]
        p = _make_playbook(tmp_path, cells)
        result = get_reaction_sensitivity("nfp", p, current_regime=None)
        assert result is not None
        assert result["dgs10_h1_hot_bp"] == pytest.approx(5.1, abs=1e-4)

    def test_output_structure_complete(self, tmp_path: Path):
        """Result has all required keys."""
        cells = _base_cells()
        p = _make_playbook(tmp_path, cells)
        result = get_reaction_sensitivity("cpi_headline", p)
        assert result is not None
        required = {
            "dgs10_h1_hot_bp", "dgs10_h1_cold_bp",
            "spy_h1_hot_pct", "spy_h1_cold_pct",
            "era_basis", "regime_requested", "regime_basis", "regime_cells_used",
            "regime_labels_revision_optimistic", "evidence", "note",
        }
        assert required.issubset(result.keys())

    def test_regime_cells_used_false_by_default(self, tmp_path: Path):
        """Without regime-conditioned cells, regime_cells_used is False."""
        cells = _base_cells()
        p = _make_playbook(tmp_path, cells)
        result = get_reaction_sensitivity("cpi_headline", p, current_regime="Q2")
        assert result is not None
        assert result["regime_cells_used"] is False
        assert result["regime_requested"] == "Q2"
        assert result["regime_basis"] is None
        assert result["regime_labels_revision_optimistic"] is False
        assert result["evidence"]["dgs10_h1_hot"]["n"] == 20
        assert result["evidence"]["dgs10_h1_hot"]["era"] == _ERA_LABEL
        assert result["evidence"]["dgs10_h1_hot"]["regime"] is None

    def test_fail_open_on_bad_json(self, tmp_path: Path):
        """Corrupt JSON → returns None without raising."""
        p = tmp_path / "research" / "release_playbook" / "results" / "playbook_v1.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("NOT VALID JSON {{{")
        result = get_reaction_sensitivity("cpi_headline", p)
        assert result is None

