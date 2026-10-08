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


def test_theta_tape_context_row_is_exact_session_and_root(tmp_path):
    from scripts.build_flow_leaders import _load_tape_row

    session = _recent_session()
    prior = last_session_on_or_before(
        pd.Timestamp(session).date() - timedelta(days=1)
    ).isoformat()
    _write_tape(tmp_path, "AMD", session=prior)
    p = tmp_path / "tape_flow" / "daily" / "AMD.parquet"
    previous = pd.read_parquet(p)
    current = previous.copy()
    current["date"] = session
    current["n_trades"] = 111
    # The later session occupies the earlier row position; index sorting
    # alone is NOT a valid date selection for T2a RangeIndex parquets.
    pd.concat([current, previous], ignore_index=True).to_parquet(p, index=False)

    row = _load_tape_row("AMD", tmp_path, session)
    assert row is not None and row["date"] == session
    assert row["n_trades"] == 111
    assert _load_tape_row("AMD", tmp_path, "2025-01-01") is None

    mixed = pd.read_parquet(p)
    mixed.loc[0, "root"] = "MSFT"
    mixed.to_parquet(p, index=False)
    assert _load_tape_row("AMD", tmp_path, session) is None


def test_sparse_tape_history_is_not_five_recurrence_sessions(tmp_path, monkeypatch):
    import engine.options_universe as options_universe
    from scripts import build_flow_leaders as builder

    current = _recent_session()
    past = []
    cursor = pd.Timestamp(current).date()
    for _ in range(5):
        cursor = last_session_on_or_before(cursor - timedelta(days=1))
        past.append(cursor.isoformat())
    for ticker in ("AMD", "AAPL", "MSFT"):
        _write_tape(tmp_path / "data", ticker, session=current)
    # One of three names has five extra older sessions. Those sessions do not
    # have a valid 90%-of-universe top-20 ranking denominator.
    p = tmp_path / "data" / "tape_flow" / "daily" / "AMD.parquet"
    recent = pd.read_parquet(p)
    old = pd.concat([recent.assign(date=d) for d in past], ignore_index=True)
    pd.concat([old, recent], ignore_index=True).to_parquet(p, index=False)
    monkeypatch.setattr(options_universe, "gex_symbols", lambda: ["AMD", "AAPL", "MSFT"])

    payload = builder.build(
        data_root=tmp_path / "data", site_root=tmp_path / "site",
        tpl_root=Path(builder.__file__).resolve().parent.parent / "templates",
    )
    assert payload["stale"] is False
    assert payload["coverage"]["n_current_roots"] == 3
    assert payload["coverage"]["n_flow_sessions"] == 1
    assert payload["cold_start"] is True
    assert all(row["recurrence_count"] is None for row in payload["board_a"])
    assert all(row["A1_flow_recur"] is None for row in payload["board_a"])


def test_missing_intermediate_nyse_day_breaks_recurrence_window(tmp_path, monkeypatch):
    import engine.options_universe as options_universe
    from scripts import build_flow_leaders as builder

    current = _recent_session()
    past = []
    cursor = pd.Timestamp(current).date()
    for _ in range(5):
        cursor = last_session_on_or_before(cursor - timedelta(days=1))
        past.append(cursor.isoformat())
    # Current, -1, -2, -4, -5 -> five observed days but only
    # three contiguous NYSE sessions. No five-session recurrence.
    sessions = [current, past[0], past[1], past[3], past[4]]
    for ticker in ("AMD", "AAPL", "MSFT"):
        _write_tape(tmp_path / "data", ticker, session=current)
        p = tmp_path / "data" / "tape_flow" / "daily" / f"{ticker}.parquet"
        row = pd.read_parquet(p)
        pd.concat([row.assign(date=d) for d in sessions],
                  ignore_index=True).to_parquet(p, index=False)
    monkeypatch.setattr(options_universe, "gex_symbols", lambda: ["AMD", "AAPL", "MSFT"])
    payload = builder.build(
        data_root=tmp_path / "data", site_root=tmp_path / "site",
        tpl_root=Path(builder.__file__).resolve().parent.parent / "templates",
    )
    assert payload["stale"] is False
    assert payload["coverage"]["n_flow_sessions"] == 3
    assert payload["cold_start"] is True
    assert all(row["recurrence_count"] is None for row in payload["board_a"])


def test_washout_does_not_splice_nonconsecutive_thetadata_sessions():
    from engine.flow_leaders import flow_inflect
    from scripts.build_flow_leaders import _theta_calendar_net_history

    current = _recent_session()
    prior = []
    cursor = pd.Timestamp(current).date()
    for _ in range(4):
        cursor = last_session_on_or_before(cursor - timedelta(days=1))
        prior.append(cursor.isoformat())

    # Without calendar reindexing the four OBSERVED rows read [-,-,-,+]
    # and falsely look like a valid fresh inflection.
    obs = pd.DataFrame(
        {"net_premium_mn": [-2.0, -2.0, -2.0, 3.0]},
        index=pd.DatetimeIndex([prior[3], prior[2], prior[0], current]),
    )
    assert flow_inflect(obs["net_premium_mn"])["inflected"] is True

    aligned = _theta_calendar_net_history(obs)
    missing_session = pd.Timestamp(prior[1])
    assert pd.isna(aligned.loc[missing_session])
    assert flow_inflect(aligned)["inflected"] is False
