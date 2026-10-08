"""Regression proof for the Flow Leaders canonical ThetaData T2a cutover.

Synthetic parquet fixtures only. No provider calls, live M1 store, collectors,
legacy Polygon entitlement or publication side effects.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from lib.nyse_calendar import last_session_on_or_before
from scripts.flow_leaders_theta_tape import MIN_UNIVERSE_COVERAGE, load_tape_cohort


def _recent_session() -> str:
    # A completed NYSE session even when tests run on weekends or before close.
    return last_session_on_or_before(datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()


def _write_tape(
    data_root: Path,
    ticker: str,
    *,
    session: str,
    root: str | None = None,
    signing_source: str = "tape",
    trades: int = 20,
    invalid_units: bool = False,
    duplicate: bool = False,
):
    d = data_root / "tape_flow" / "daily"
    d.mkdir(parents=True, exist_ok=True)
    row = {
        "date": session,
        "root": root or ticker,
        "signing_source": signing_source,
        "n_trades": trades,
        "net_signed_premium": 200_000.0,
        "gross_premium": (0.5 if invalid_units else 1_000_000.0),
        "zerodte_share": 0.2,
        "dte_1_7d_net_premium": 50_000.0,
        "dte_8_30d_net_premium": 40_000.0,
        "dte_31_90d_net_premium": 30_000.0,
        "dte_90p_net_premium": 20_000.0,
    }
    pd.DataFrame([row, row] if duplicate else [row]).to_parquet(d / f"{ticker}.parquet", index=False)


def test_tape_units_signing_and_source_session(tmp_path):
    session = _recent_session()
    _write_tape(tmp_path, "AMD", session=session)
    _write_tape(tmp_path, "AAPL", session=session)
    cohort = load_tape_cohort(tmp_path, ["AMD", "AAPL"])
    assert cohort.coverage_ratio == 1.0
    assert cohort.coverage_ready and MIN_UNIVERSE_COVERAGE == 0.90
    assert cohort.latest_session == session
    assert cohort.current_roots == 2
    amd = cohort.summaries["AMD"]
    assert amd.index[-1].date().isoformat() == session
    assert amd["net_premium_mn"].iloc[-1] == pytest.approx(0.20)
    assert amd["premium_mn"].iloc[-1] == pytest.approx(1.0)
    assert amd["zerodte_share"].iloc[-1] == pytest.approx(0.2)
    # These are per-session *signed premium USD*, not unsuffixed legacy buckets.
    assert amd["net_premium_ex0dte_mn"].iloc[-1] == pytest.approx(0.14)


@pytest.mark.parametrize("variant", ["wrong_root", "wrong_signer", "no_trades", "invalid_money", "duplicate"])
def test_tape_qualification_refuses_invalid_source(tmp_path, variant):
    kwargs = {
        "wrong_root": {"root": "MSFT"},
        "wrong_signer": {"signing_source": "minute_tick"},
        "no_trades": {"trades": 0},
        "invalid_money": {"invalid_units": True},
        "duplicate": {"duplicate": True},
    }[variant]
    _write_tape(tmp_path, "AMD", session=_recent_session(), **kwargs)
    cohort = load_tape_cohort(tmp_path, ["AMD"])
    assert cohort.summaries == {}
    assert cohort.current_roots == 0
    assert not cohort.coverage_ready


def test_tape_cohort_refuses_one_root_claiming_broad_market(tmp_path):
    session = _recent_session()
    _write_tape(tmp_path, "AMD", session=session)
    cohort = load_tape_cohort(tmp_path, ["AMD", "MSFT", "NVDA", "AAPL"])
    assert cohort.latest_session == session
    assert cohort.current_roots == 1
    assert cohort.expected_roots == 4
    assert cohort.coverage_ratio == pytest.approx(0.25)
    assert not cohort.coverage_ready


def test_cohort_uses_latest_widely_represented_session_not_one_outlier(tmp_path):
    recent = _recent_session()
    older = last_session_on_or_before(
        pd.Timestamp(recent).date() - timedelta(days=1)
    ).isoformat()
    _write_tape(tmp_path, "AMD", session=older)
    _write_tape(tmp_path, "MSFT", session=older)
    _write_tape(tmp_path, "AAPL", session=recent)
    cohort = load_tape_cohort(tmp_path, ["AMD", "MSFT", "AAPL"])
    assert cohort.latest_session == older
    assert cohort.current_roots == 2
    assert set(cohort.summaries) == {"AMD", "MSFT"}
    assert not cohort.coverage_ready


def test_canonical_source_overrides_archived_massive_and_disables_signal_fire(tmp_path, monkeypatch):
    import engine.options_universe as options_universe
    from scripts import build_flow_leaders as builder

    session = _recent_session()
    for ticker in ("AMD", "AAPL", "MSFT"):
        _write_tape(tmp_path / "data", ticker, session=session)
    monkeypatch.setattr(options_universe, "gex_symbols", lambda: ["AMD", "AAPL", "MSFT"])

    def retired_source_used(*_args, **_kwargs):
        pytest.fail("retired Massive/Polygon options source used for a ThetaData session")

    monkeypatch.setattr(builder, "_load_all_summaries", retired_source_used)
    monkeypatch.setattr(builder, "_load_two_chain_days", retired_source_used)
    monkeypatch.setattr(builder, "_load_options_entry", retired_source_used)
    payload = builder.build(
        data_root=tmp_path / "data",
        site_root=tmp_path / "site",
        tpl_root=Path(builder.__file__).resolve().parent.parent / "templates",
    )
    assert payload["source_family"] == "thetadata_t2a_tape"
    assert payload["session_date"] == session
    assert payload["source_age_stale"] is False
    assert payload["stale"] is False
    assert payload["signal_policy"] == "research_only"
    assert payload["coverage"]["n_current_roots"] == 3
    assert payload["coverage"]["n_expected_roots"] == 3
    assert payload["board_a"]
    assert all(r["fire_a"] is False and r["fire_b"] is False for r in payload["board_a"])
    assert all(r["oi_confirmed"] is None and r["gamma_regime"] is None for r in payload["board_a"])


def test_incomplete_theta_session_stays_unavailable(tmp_path, monkeypatch):
    import engine.options_universe as options_universe
    from scripts import build_flow_leaders as builder

    session = _recent_session()
    _write_tape(tmp_path / "data", "AMD", session=session)
    monkeypatch.setattr(options_universe, "gex_symbols", lambda: ["AMD", "MSFT", "AAPL", "NVDA"])
    payload = builder.build(
        data_root=tmp_path / "data",
        site_root=tmp_path / "site",
        tpl_root=Path(builder.__file__).resolve().parent.parent / "templates",
    )
    assert payload["session_date"] == session
    assert payload["source_age_stale"] is False
    assert payload["stale"] is True
    assert payload["stale_reason"] == "insufficient_same_session_coverage"
    assert payload["coverage"]["n_current_roots"] == 1
    assert payload["coverage"]["n_expected_roots"] == 4


def test_retired_legacy_remains_stale_even_if_its_clock_is_recent(tmp_path):
    from scripts import build_flow_leaders as builder

    # Explicit negative contract: a legacy byte file dated today cannot become
    # a prospectively qualified board merely by advancing its date.
    d = tmp_path / "data" / "options_flow"
    d.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({
        "net_premium_mn": [1.5],
        "premium_mn": [4.0],
        "zerodte_share": [0.2],
    }, index=pd.DatetimeIndex([_recent_session()]))
    df.to_parquet(d / "summary_AMD.parquet")
    payload = builder.build(
        data_root=tmp_path / "data",
        site_root=tmp_path / "site",
        tpl_root=Path(builder.__file__).resolve().parent.parent / "templates",
    )
    assert payload["source_family"] == "legacy_options_flow_archive"
    assert payload["stale"] is True
    assert payload["stale_reason"] == "legacy_options_source_retired"
