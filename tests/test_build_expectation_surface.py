"""Contract tests for scripts/build_expectation_surface.py (Expectation Surface page).

Everything here runs on synthetic parquet fixtures inside tmp_path — no network,
no real data/ artifacts, no LLM. The builder is pointed at a fake repo root with
the real templates/ symlinked in (same shape as tests/test_builder_shim_writes.py)
and must return a summary dict, write site/expectation_surface/{summary.json,
tickers/index.json, tickers/<T>.json} plus site/expectation_surface.html through
lib.pages.write_page, and never touch data/.

The frozen JSON contract lives in
research/alpha_intelligence/expectation_market_dynamics/EXPECTATION_SURFACE_PAGE_CONTRACT_2026-10-21.md
and every frozen key is asserted here.

Run: python3 -m pytest tests/test_build_expectation_surface.py -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent

S1, S2, S3 = "S1", "S2", "S3"
AT = {S1: "2026-01-01T00:00:00Z", S2: "2026-01-02T00:00:00Z", S3: "2026-01-03T00:00:00Z"}
SYS_AT = {S1: "2026-01-01T12:00:00Z", S2: "2026-01-02T12:00:00Z", S3: "2026-01-03T12:00:00Z"}

_OBS_COLS = [
    "observation_id", "collection_session_id", "attempt_id", "provider",
    "ticker_compat", "metric", "horizon_label_raw", "period_end",
    "observation_type", "value", "missingness_reason",
    "provider_observed_at", "system_observed_at",
]
_ATT_COLS = ["attempt_id", "collection_session_id", "attempted_at", "status"]
_AL_COLS = ["vendor", "vendor_symbol", "security_id", "valid_from"]


def _obs(sid: str, ticker: str, *, metric: str = "EPS", horizon: str = "0q",
         otype: str = "average", value=None, period_end="2026-12-31",
         missing=None) -> dict:
    return {
        "observation_id": f"o-{ticker}-{metric}-{horizon}-{otype}-{sid}",
        "collection_session_id": sid,
        "attempt_id": f"a-{sid}",
        "provider": "yfinance",
        "ticker_compat": ticker,
        "metric": metric,
        "horizon_label_raw": horizon,
        "period_end": period_end,
        "observation_type": otype,
        "value": value,
        "missingness_reason": missing,
        "provider_observed_at": AT[sid],
        "system_observed_at": SYS_AT[sid],
    }


def _att(sid: str) -> dict:
    return {"attempt_id": f"a-{sid}", "collection_session_id": sid,
            "attempted_at": AT[sid], "status": "ok"}


def _main_obs_rows() -> list[dict]:
    """3 sessions x 2 metrics, hand-computed so breadth/movers arithmetic is exact.

    EPS/0q averages:  AAA 100,102,101 · BBB 50,50,50 · CCC 10,11,11 · DDD -,20,21
                      EEE -,30,(missing in S3: UNESTIMABLE)
    revenue/0q avgs:  AAA 1000,990,990 · BBB -,500,505
    covering_analyst_count at S3: AAA 12, BBB 5, DDD 7.
    AAA S3 also carries median/high/low so a ticker-file point has non-null fields.
    """
    rows: list[dict] = []
    rows += [_obs(S1, "AAA", value=100.0), _obs(S2, "AAA", value=102.0), _obs(S3, "AAA", value=101.0)]
    rows += [_obs(S1, "BBB", value=50.0), _obs(S2, "BBB", value=50.0), _obs(S3, "BBB", value=50.0)]
    rows += [_obs(S1, "CCC", value=10.0), _obs(S2, "CCC", value=11.0), _obs(S3, "CCC", value=11.0)]
    rows += [_obs(S2, "DDD", value=20.0), _obs(S3, "DDD", value=21.0)]
    rows += [_obs(S2, "EEE", value=30.0),
             _obs(S3, "EEE", value=None, missing="UNESTIMABLE")]
    rows += [_obs(S1, "AAA", metric="revenue", value=1000.0),
             _obs(S2, "AAA", metric="revenue", value=1010.0),
             _obs(S3, "AAA", metric="revenue", value=990.0)]
    rows += [_obs(S2, "BBB", metric="revenue", value=500.0),
             _obs(S3, "BBB", metric="revenue", value=505.0)]
    rows += [_obs(S3, "AAA", otype="covering_analyst_count", value=12.0),
             _obs(S3, "BBB", otype="covering_analyst_count", value=5.0),
             _obs(S3, "DDD", otype="covering_analyst_count", value=7.0)]
    rows += [_obs(S3, "AAA", otype="median", value=100.5),
             _obs(S3, "AAA", otype="high", value=105.0),
             _obs(S3, "AAA", otype="low", value=98.0)]
    return rows


_MAIN_ALIASES = [
    {"vendor": "store", "vendor_symbol": "AAA", "security_id": "SEC1", "valid_from": "2020-01-01"},
    {"vendor": "store", "vendor_symbol": "BBB", "security_id": "SEC2", "valid_from": None},
    {"vendor": "yahoo", "vendor_symbol": "DDD", "security_id": "SEC9", "valid_from": "2020-01-01"},
]


def _write_fixture(root: Path, obs_rows: list[dict], *, att_rows=None,
                   alias_rows=None) -> Path:
    """Fake repo root: data parquets + real templates/ symlink. Missing parquet
    args are written anyway unless the caller passes a sentinel-free None AND
    sets omit_* kwargs — simpler: helpers below delete what they want absent."""
    import pandas as pd

    rev = root / "data" / "revisions"
    ref = root / "data" / "reference"
    rev.mkdir(parents=True, exist_ok=True)
    ref.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(obs_rows, columns=_OBS_COLS).to_parquet(rev / "expectation_observations.parquet")
    if att_rows is None:
        att_rows = [_att(s) for s in (S1, S2, S3)]
    pd.DataFrame(att_rows, columns=_ATT_COLS).to_parquet(rev / "expectation_attempts.parquet")
    if alias_rows is None:
        alias_rows = _MAIN_ALIASES
    pd.DataFrame(alias_rows, columns=_AL_COLS).to_parquet(ref / "vendor_aliases.parquet")
    (root / "templates").symlink_to(ROOT / "templates")
    return root


@pytest.fixture()
def fake_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "site").mkdir(parents=True)
    _write_fixture(root, _main_obs_rows())
    return root


def _build(root: Path, **kw):
    from scripts.build_expectation_surface import build
    return build(write=True, root=root, **kw)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Frozen contract keys
# ---------------------------------------------------------------------------

def test_summary_carries_every_frozen_key(fake_root: Path):
    s = _build(fake_root)
    assert set(s) == {"schema", "rendered_at", "financial_influence", "k3e_admissible",
                      "state", "reasons", "source", "identity", "census", "breadth",
                      "movers", "exclusions"}
    assert set(s["source"]) == {"observations_path", "observations_blob_sha1",
                                "source_revision", "latest_session", "prior_session"}
    assert set(s["source"]["latest_session"]) == {"id", "at"}
    assert set(s["identity"]) == {"state", "resolved", "unresolved", "undated_aliases"}
    assert set(s["census"]) == {"observations", "securities", "metrics", "horizons",
                                "sessions", "span", "analysts_median"}
    assert set(s["census"]["span"]) == {"first", "last"}
    assert set(s["exclusions"]) == {"rollover", "missingness", "zero_prior"}
    for row in s["breadth"]:
        assert set(row) == {"session_id", "at", "metric", "up", "down", "flat"}
    for metric in ("EPS", "revenue"):
        for item in s["movers"][metric]["up"] + s["movers"][metric]["down"]:
            assert set(item) == {"ticker", "horizon", "period_end", "prior", "latest",
                                 "pct_change", "analysts", "prior_at", "latest_at"}


def test_index_and_ticker_file_contract_keys(fake_root: Path):
    _build(fake_root)
    base = fake_root / "site" / "expectation_surface"
    index = _read_json(base / "tickers" / "index.json")
    assert isinstance(index, list) and index
    for entry in index:
        assert set(entry) == {"ticker", "sessions", "latest_at", "identity_status"}
    assert [e["ticker"] for e in index] == ["AAA", "BBB", "CCC", "DDD", "EEE"]
    tf = _read_json(base / "tickers" / "AAA.json")
    assert set(tf) == {"ticker", "identity_status", "financial_influence",
                       "k3e_admissible", "series"}
    for metric, horizons in tf["series"].items():
        for horizon, points in horizons.items():
            for p in points:
                assert set(p) == {"at", "period_end", "average", "median", "high",
                                  "low", "analysts"}
    assert tf["series"]["EPS"]["0q"][2] == {
        "at": AT[S3], "period_end": "2026-12-31", "average": 101.0, "median": 100.5,
        "high": 105.0, "low": 98.0, "analysts": 12.0,
    }
    assert [p["at"] for p in tf["series"]["EPS"]["0q"]] == [AT[S1], AT[S2], AT[S3]]
    assert tf["series"]["revenue"]["0q"][0]["average"] == 1000.0
    assert tf["series"]["EPS"]["0q"][0]["analysts"] is None


# ---------------------------------------------------------------------------
# Breadth arithmetic (hand-computed)
# ---------------------------------------------------------------------------

def test_breadth_three_sessions_two_metrics(fake_root: Path):
    s = _build(fake_root)
    # Sessions with no comparable pair (S1) are omitted; ordered by at then metric.
    assert s["breadth"] == [
        {"session_id": S2, "at": AT[S2], "metric": "EPS", "up": 2, "down": 0, "flat": 1},
        {"session_id": S2, "at": AT[S2], "metric": "revenue", "up": 1, "down": 0, "flat": 0},
        {"session_id": S3, "at": AT[S3], "metric": "EPS", "up": 1, "down": 1, "flat": 2},
        {"session_id": S3, "at": AT[S3], "metric": "revenue", "up": 1, "down": 1, "flat": 0},
    ]


# ---------------------------------------------------------------------------
# Movers arithmetic + exclusions
# ---------------------------------------------------------------------------

def test_movers_arithmetic_and_fields(fake_root: Path):
    s = _build(fake_root)
    eps = s["movers"]["EPS"]
    assert [(i["ticker"], i["pct_change"]) for i in eps["up"]] == [("DDD", 0.05)]
    assert [(i["ticker"], i["pct_change"]) for i in eps["down"]] == [("AAA", -0.009804)]
    aaa_down = eps["down"][0]
    assert aaa_down["prior"] == 102.0 and aaa_down["latest"] == 101.0
    assert aaa_down["prior_at"] == AT[S2] and aaa_down["latest_at"] == AT[S3]
    assert aaa_down["horizon"] == "0q" and aaa_down["period_end"] == "2026-12-31"
    assert aaa_down["analysts"] == 12.0
    rev = s["movers"]["revenue"]
    assert [(i["ticker"], i["pct_change"]) for i in rev["up"]] == [("BBB", 0.01)]
    assert [(i["ticker"], i["pct_change"]) for i in rev["down"]] == [("AAA", -0.019802)]
    assert rev["up"][0]["analysts"] is None  # no covering_analyst_count rows for revenue
    assert s["source"]["latest_session"] == {"id": S3, "at": AT[S3]}
    assert s["source"]["prior_session"] == {"id": S2, "at": AT[S2]}


def test_movers_tie_break_by_ticker(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "site").mkdir(parents=True)
    rows = []
    for t in ("TA", "TB"):                       # identical pct +0.1 → TA before TB
        rows += [_obs(S2, t, value=10.0), _obs(S3, t, value=11.0)]
    rows += [_obs(S2, "ZT", value=10.0), _obs(S3, "ZT", value=5.0)]   # most negative
    _write_fixture(root, rows)
    s = _build(root)
    assert [i["ticker"] for i in s["movers"]["EPS"]["up"]] == ["TA", "TB"]
    assert [i["ticker"] for i in s["movers"]["EPS"]["down"]] == ["ZT"]


def test_movers_top_n_cut(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "site").mkdir(parents=True)
    rows = []
    for i in range(1, 31):                       # T01..T30, pct = i/100
        t = f"T{i:02d}"
        rows += [_obs(S2, t, value=100.0), _obs(S3, t, value=100.0 + i)]
    _write_fixture(root, rows)
    s = _build(root)
    up = s["movers"]["EPS"]["up"]
    assert len(up) == 25
    assert up[0]["ticker"] == "T30" and up[-1]["ticker"] == "T06"
    assert all(i["ticker"] != "T05" for i in up)


def test_movers_exclude_missingness_zero_prior_and_count_rollover(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "site").mkdir(parents=True)
    rows = [
        # MI: latest-session average row is missing → never enters movers.
        _obs(S2, "MI", value=50.0),
        _obs(S3, "MI", value=None, missing="UNESTIMABLE"),
        # ZP: prior == 0 → excluded from movers, counted in exclusions.zero_prior.
        _obs(S2, "ZP", value=0.0), _obs(S3, "ZP", value=5.0),
        # RO: period_end changes between the pair → rollover, excluded and counted.
        _obs(S2, "RO", value=100.0, period_end="2026-12-31"),
        _obs(S3, "RO", value=110.0, period_end="2027-03-31"),
    ]
    _write_fixture(root, rows)
    s = _build(root)
    movers_tickers = {i["ticker"] for i in s["movers"]["EPS"]["up"] + s["movers"]["EPS"]["down"]}
    assert "MI" not in movers_tickers and "ZP" not in movers_tickers and "RO" not in movers_tickers
    assert s["exclusions"]["missingness"] == 1
    assert s["exclusions"]["zero_prior"] == 1
    assert s["exclusions"]["rollover"] == 1
    # The rollover pair must not surface as breadth either: the only comparable
    # pair left is ZP's S2→S3 (+5), which breadth counts even though movers
    # excludes it for the zero prior.
    assert s["breadth"] == [
        {"session_id": S3, "at": AT[S3], "metric": "EPS", "up": 1, "down": 0, "flat": 0},
    ]


# ---------------------------------------------------------------------------
# Honest-state: OFFLINE
# ---------------------------------------------------------------------------

def test_offline_when_observations_missing(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "site").mkdir(parents=True)
    _write_fixture(root, [])
    (root / "data" / "revisions" / "expectation_observations.parquet").unlink()
    s = _build(root)
    assert s["state"] == "OFFLINE"
    assert s["reasons"]
    assert s["census"]["observations"] == 0 and s["census"]["securities"] == 0
    assert s["census"]["metrics"] == [] and s["census"]["horizons"] == []
    assert s["breadth"] == []
    assert s["movers"] == {"EPS": {"up": [], "down": []}, "revenue": {"up": [], "down": []}}
    assert (root / "site" / "expectation_surface" / "tickers" / "index.json").read_text() == "[]"
    stray = [p.name for p in (root / "site" / "expectation_surface" / "tickers").glob("*.json")
             if p.name != "index.json"]
    assert not stray
    html = (root / "site" / "expectation_surface.html").read_text(encoding="utf-8")
    assert 'role="status"' in html
    for reason in s["reasons"]:
        assert reason in html


# ---------------------------------------------------------------------------
# Reserved controls
# ---------------------------------------------------------------------------

def test_reserved_flags_false_everywhere(fake_root: Path):
    s = _build(fake_root)
    assert s["financial_influence"] is False and s["k3e_admissible"] is False
    base = fake_root / "site" / "expectation_surface" / "tickers"
    for tf in base.glob("*.json"):
        if tf.name == "index.json":
            continue
        d = _read_json(tf)
        assert d["financial_influence"] is False and d["k3e_admissible"] is False
    assert s["identity"]["state"] == "COMPLETE_DEGRADED"


# ---------------------------------------------------------------------------
# Identity counts (computed, never hardcoded)
# ---------------------------------------------------------------------------

def test_identity_counts_from_aliases(fake_root: Path):
    s = _build(fake_root)
    assert s["identity"] == {"state": "COMPLETE_DEGRADED", "resolved": 2,
                             "unresolved": 3, "undated_aliases": 1}
    base = fake_root / "site" / "expectation_surface" / "tickers"
    index = {e["ticker"]: e["identity_status"] for e in _read_json(base / "index.json")}
    assert index == {"AAA": "resolved", "BBB": "undated", "CCC": "unresolved",
                     "DDD": "unresolved", "EEE": "unresolved"}


def test_identity_unknown_when_aliases_missing(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "site").mkdir(parents=True)
    _write_fixture(root, _main_obs_rows()[:6])
    (root / "data" / "reference" / "vendor_aliases.parquet").unlink()
    s = _build(root)
    assert all(e["identity_status"] == "unknown"
               for e in _read_json(root / "site" / "expectation_surface" / "tickers" / "index.json"))
    assert any("aliases" in r for r in s["reasons"])


def test_session_clock_falls_back_to_system_observed_at(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "site").mkdir(parents=True)
    _write_fixture(root, _main_obs_rows()[:6])
    (root / "data" / "revisions" / "expectation_attempts.parquet").unlink()
    s = _build(root)
    assert any("attempts_unavailable" in r for r in s["reasons"])
    assert s["source"]["latest_session"]["at"] == SYS_AT[S3]
    idx = _read_json(root / "site" / "expectation_surface" / "tickers" / "index.json")
    assert idx[0]["latest_at"] == SYS_AT[S3]


def test_unsafe_ticker_skipped_with_reason(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "site").mkdir(parents=True)
    _write_fixture(root, [_obs(S1, "AA$A", value=1.0), _obs(S2, "AA$A", value=2.0),
                          _obs(S1, "AAA", value=1.0), _obs(S2, "AAA", value=1.0)])
    s = _build(root)
    assert not (root / "site" / "expectation_surface" / "tickers" / "AA$A.json").exists()
    assert any(r.startswith("ticker_skipped_unsafe_filename: 1 tickers") for r in s["reasons"])
    idx = _read_json(root / "site" / "expectation_surface" / "tickers" / "index.json")
    assert [e["ticker"] for e in idx] == ["AA$A", "AAA"]  # index is complete; only the file is gated


# ---------------------------------------------------------------------------
# Page + write path + hygiene
# ---------------------------------------------------------------------------

def test_template_has_six_ids_in_order_and_four_chips(fake_root: Path):
    _build(fake_root)
    src = (ROOT / "templates" / "expectation_surface.html.j2").read_text(encoding="utf-8")
    ids = ["es-hero", "es-census", "es-breadth", "es-movers", "es-explorer", "es-method"]
    pos = [src.index(f'id="{i}"') for i in ids]
    assert pos == sorted(pos)
    assert "<style" not in src and "style=" not in src
    html = (fake_root / "site" / "expectation_surface.html").read_text(encoding="utf-8")
    for chip in ("Descriptive · not a signal", "仅描述 · 非信号",
                 "Identity COMPLETE_DEGRADED", "Source snapshot ", "Rendered "):
        assert chip in html


def test_page_written_through_write_page(fake_root: Path, monkeypatch):
    import scripts.build_expectation_surface as es
    calls: list[Path] = []
    real = es.write_page

    def spy(path, html, **kw):
        calls.append(Path(path))
        return real(path, html, **kw)

    monkeypatch.setattr(es, "write_page", spy)
    es.build(write=True, root=fake_root)
    assert len(calls) == 1
    assert calls[0].name == "expectation_surface.html"


def test_builder_never_writes_under_data(fake_root: Path):
    def snap(root: Path):
        return sorted((p, p.stat().st_size, p.stat().st_mtime_ns)
                      for p in (root / "data").rglob("*") if p.is_file())
    before = snap(fake_root)
    _build(fake_root)
    assert snap(fake_root) == before


def test_fixture_build_finishes_well_under_budget(fake_root: Path):
    t0 = time.perf_counter()
    _build(fake_root)
    assert time.perf_counter() - t0 < 10.0


# ---------------------------------------------------------------------------
# Census + hygiene details
# ---------------------------------------------------------------------------

def test_census_values(fake_root: Path):
    s = _build(fake_root)
    c = s["census"]
    assert c["observations"] == len(_main_obs_rows())
    assert c["securities"] == 5
    assert c["metrics"] == ["EPS", "revenue"]
    assert c["horizons"] == ["0q"]
    assert c["sessions"] == 3
    assert c["span"] == {"first": AT[S1], "last": AT[S3]}
    # covering_analyst_count at each key's latest session: 12, 5, 7 → median 7.0
    assert c["analysts_median"] == 7.0
    assert s["schema"] == "expectation_surface.page.v1"
    assert s["state"] == "LIVE"
    assert s["source"]["observations_path"] == "data/revisions/expectation_observations.parquet"
    assert s["source"]["observations_blob_sha1"]
    assert len(s["source"]["observations_blob_sha1"]) == 40
    assert json.dumps(s, ensure_ascii=False, sort_keys=False, allow_nan=False)  # NaN-free
