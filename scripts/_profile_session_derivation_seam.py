"""Synthetic moderate-scale profile/counter artifact for the session-derivation seam.

This is a one-shot instrumented benchmark — no flaky timing, no licensed data.
It counts how often :func:`normalize_price_bars` runs across a synthetic
episode fleet that mirrors the natural failure's shape (N episodes × H horizons
per prepared ticker). Two passes are recorded:

  * ``raw``  — every derive_session_outcome invocation renormalizes from the
    raw frame. This is the original head's behaviour.
  * ``prep`` — every derive_session_outcome invocation receives a per-run
    ``_PreparedPriceBars`` built once per ticker. The factory's single
    :func:`normalize_price_bars` call is the only normalization.

The output is a deterministic, human-readable counter artifact committed to
the PR body.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from engine.options_signal_episode import (
    SESSION_HORIZONS,
    derive_session_outcome,
    normalize_price_bars,
    prepare_price_bars,
)
from engine.session_digest import session_window_et
from lib import nyse_calendar


TICKERS: tuple[str, ...] = (
    "T01", "T02", "T03", "T04", "T05",
    "T06", "T07", "T08", "T09", "T10",
    "T11", "T12", "T13", "T14", "T15",
    "T16", "T17", "T18", "T19", "T20",
)
EPISODES_PER_TICKER = 16  # 20 tickers × 16 episodes = 320 episodes total
HORIZONS = tuple(SESSION_HORIZONS)
SESSION_DATE = "2026-07-02"
BAR_SECONDS = 1800


def _bars_for(ticker: str, base_value: float = 100.0) -> pd.DataFrame:
    session = datetime.fromisoformat(SESSION_DATE).date()
    target = nyse_calendar.session_n_forward(session, max(SESSION_HORIZONS.values()))
    assert target is not None
    sessions = nyse_calendar.sessions_between(session, target)
    stamps: list[pd.Timestamp] = []
    for session in sessions:
        open_et, close_et = session_window_et(session)
        stamps.extend(pd.date_range(
            open_et.astimezone(timezone.utc),
            close_et.astimezone(timezone.utc) - timedelta(seconds=BAR_SECONDS),
            freq=pd.Timedelta(seconds=BAR_SECONDS),
        ))
    values = [base_value + index * 0.05 for index in range(len(stamps))]
    return pd.DataFrame(
        {
            "open": values,
            "high": [value + 1.0 for value in values],
            "low": [value - 1.0 for value in values],
            "close": [value + 0.25 for value in values],
        },
        index=pd.DatetimeIndex(stamps),
    )


def _episode_payload(ticker: str, ep_index: int) -> dict:
    # available_at is placed at 14:31 UTC (~10:31 ET), inside the NYSE RTH,
    # so each derived session measurement matures only after the computed_at
    # horizon is well past the available anchor. The episode payload mirrors
    # the schema-strict shape the engine validates downstream.
    session = datetime.fromisoformat(SESSION_DATE).date()
    available = datetime(session.year, session.month, session.day, 14, 31, tzinfo=timezone.utc)
    available = available + timedelta(minutes=ep_index)
    observed_at = available
    source_event_id = f"profile-{ticker}-{ep_index:03d}"
    # The schema requires ``osep_<24-hex>``; re-use the engine's stable-id
    # helper so this synthetic fixture is indistinguishable from real episodes.
    from engine.options_signal_episode import _episode_id
    episode_id = _episode_id("profile", source_event_id)
    return {
        "schema": "options.signal_episode/v1",
        "episode_id": episode_id,
        "source": "profile",
        "source_event_id": source_event_id,
        "event_time": observed_at.isoformat().replace("+00:00", "Z"),
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
        "decision_at": observed_at.isoformat().replace("+00:00", "Z"),
        "available_at": observed_at.isoformat().replace("+00:00", "Z"),
        "published_at": None,
        "anchor_strategy": "durable_available_at",
        "session_date": session.isoformat(),
        "ticker": ticker,
        "contract": {
            "right": "C",
            "expiration": "2026-07-17",
            "strike": 105.0,
        },
        "decision": {
            "disposition": "watch",
            "reason": "profile",
            "underlying_direction": "none",
            "option_action": "none",
            "authority": {
                "may_originate": False,
                "may_rank": False,
                "may_gate": False,
                "may_size": False,
                "may_escalate": False,
                "may_trade": False,
                "may_publish_pick": False,
                "may_train_prophet": False,
            },
        },
        "feature_snapshot": {
            "premium_usd": 50_000.0,
            "selection_rule": "premium_floor/v1",
            "selection_floor_usd": 25_000,
            "selection_root_class": "single_name",
            "contracts": 200,
            "avg_option_trade_price": 2.5,
            "flow_side": "~buy",
            "dte": 15,
            "moneyness_bucket": "atm",
            "vol_gt_prior_oi": True,
            "repeated": True,
            "swept": False,
        },
        "provenance": {
            "source_schema": "live_flow.event_stage/v1",
            "source_artifact": f"live_flow/events/{SESSION_DATE}.jsonl",
            "source_snapshot_asof": observed_at.isoformat().replace("+00:00", "Z"),
            "feature_cutoff": observed_at.isoformat().replace("+00:00", "Z"),
            "signing_source": "tape",
            "oi_vintage": "2026-07-01",
            "oi_vintage_rule": "latest_available_chain_before_session",
        },
        "quality": {
            "availability_exact": True,
            "trade_direction_reliability": "soft",
            "option_quote_outcome_eligible": False,
            "source_baseline": "floor",
        },
    }


def _receipt(episode: dict, ticker: str, frame: pd.DataFrame) -> dict:
    from engine.options_signal_episode import PRICE_BASIS, PRICE_RECEIPT_SCHEMA, TIMESTAMP_BASIS

    session = datetime.fromisoformat(episode["session_date"]).date()
    target = nyse_calendar.session_n_forward(session, max(SESSION_HORIZONS.values()))
    assert target is not None
    target_time = session_window_et(target)[1].astimezone(timezone.utc)
    source_available = target_time + timedelta(minutes=15)
    index = pd.to_datetime(frame.index, utc=True)
    return {
        "schema": PRICE_RECEIPT_SCHEMA,
        "ticker": ticker,
        "source_file": f"profile/{ticker}.parquet",
        "source_file_sha256": "0" * 64,
        "source_available_at": source_available.isoformat().replace("+00:00", "Z"),
        "bar_seconds": BAR_SECONDS,
        "vendor_delay_minutes": 15,
        "adjusted": True,
        "price_basis": PRICE_BASIS,
        "timestamp_basis": TIMESTAMP_BASIS,
        "row_count": len(frame),
        "first_time": index.min().to_pydatetime().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "last_time": index.max().to_pydatetime().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _counter_pass(label: str, *, use_prepared: bool) -> dict:
    counts = {"normalize_calls": 0, "derive_calls": 0}

    original_normalize = normalize_price_bars
    from engine import options_signal_episode as engine_mod

    def counting(frame):
        counts["normalize_calls"] += 1
        return original_normalize(frame)

    engine_mod.normalize_price_bars = counting
    # prepare_price_bars looks up normalize_price_bars via module globals.
    engine_mod.prepare_price_bars.__globals__["normalize_price_bars"] = counting

    try:
        for ticker in TICKERS:
            frame = _bars_for(ticker)
            receipt = None
            prepared = None
            if use_prepared:
                prepared = prepare_price_bars(frame, ticker=ticker)
            else:
                # Original head: every derive_session_outcome renormalizes
                # from the raw frame. We rebuild the prepared wrapper only to
                # keep the receipt validation off the critical path; the
                # derive call still passes the raw frame.
                prepared = None
            for ep_index in range(EPISODES_PER_TICKER):
                episode = _episode_payload(ticker, ep_index)
                if receipt is None:
                    receipt = _receipt(episode, ticker, frame)
                available = datetime.fromisoformat(
                    episode["available_at"].replace("Z", "+00:00")
                ).astimezone(timezone.utc)
                computed_at = (
                    datetime.fromisoformat(SESSION_DATE).date()
                    and (available + timedelta(days=30))
                )
                kwargs = {
                    "computed_at": computed_at,
                    "price_source": receipt["source_file"],
                    "bar_seconds": BAR_SECONDS,
                    "price_delay_minutes": 15,
                    "price_receipt": receipt,
                }
                if use_prepared:
                    kwargs["prepared_bars"] = prepared
                for horizon in HORIZONS:
                    row = derive_session_outcome(episode, horizon, frame, **kwargs)
                    counts["derive_calls"] += 1
                    assert row["status"] in {"complete", "pending"}, row
    finally:
        engine_mod.normalize_price_bars = original_normalize
        engine_mod.prepare_price_bars.__globals__["normalize_price_bars"] = original_normalize

    return {
        "label": label,
        "use_prepared": use_prepared,
        "tickers": len(TICKERS),
        "episodes_per_ticker": EPISODES_PER_TICKER,
        "horizons": list(HORIZONS),
        "normalize_calls": counts["normalize_calls"],
        "derive_calls": counts["derive_calls"],
    }


def main() -> int:
    raw = _counter_pass("raw-baseline", use_prepared=False)
    prep = _counter_pass("prepared-seam", use_prepared=True)
    expected_raw = raw["tickers"] * raw["episodes_per_ticker"] * len(raw["horizons"])
    expected_prep = prep["tickers"] * 1  # one normalize per ticker
    artifact = {
        "schema": "options.session_derivation_seam_profile/v1",
        "session_date": SESSION_DATE,
        "bar_seconds": BAR_SECONDS,
        "passes": [raw, prep],
        "expected": {
            "raw_normalize_calls": expected_raw,
            "prepared_normalize_calls": expected_prep,
            "raw_derive_calls": expected_raw,
            "prepared_derive_calls": expected_raw,
        },
    }
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())