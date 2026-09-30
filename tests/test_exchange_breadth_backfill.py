from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from engine.exchange_breadth import UNIVERSE_ALL_ISSUES, UNIVERSE_OPERATING
from lib.nyse_calendar import is_session
from scripts.backfill_exchange_breadth import (
    DEFAULT_RECENT_SESSIONS,
    BackfillRefused,
    GroupedDailyPriceClient,
    SessionAcceptance,
    enumerate_backfill_sessions,
    grouped_session_maps_to_history,
    run_backfill,
)

END = date(2026, 1, 9)
NOW = datetime(2026, 1, 9, 23, 0, tzinfo=timezone.utc)


def _accept(session: date) -> SessionAcceptance:
    return SessionAcceptance(
        session=session,
        roster_reconciled=True,
        price_reconciled=True,
        published=True,
        source="fixture",
        receipt={"accepted_session": session.isoformat()},
    )


def test_default_recent_seed_is_270_completed_xnys_sessions() -> None:
    sessions = enumerate_backfill_sessions(end=END, now=NOW)

    assert DEFAULT_RECENT_SESSIONS >= 270
    assert len(sessions) == DEFAULT_RECENT_SESSIONS
    assert sessions[-1] == END
    assert sessions == sorted(sessions)
    assert len(set(sessions)) == len(sessions)
    assert all(is_session(session) for session in sessions)


def test_explicit_range_uses_reviewed_xnys_calendar() -> None:
    sessions = enumerate_backfill_sessions(
        start=date(2026, 1, 1), end=date(2026, 1, 12), now=NOW
    )

    assert sessions == [
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
        date(2026, 1, 7),
        date(2026, 1, 8),
        date(2026, 1, 9),
    ]


def test_completed_sessions_are_skipped_and_bounded_run_reports_remaining(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "exchange_breadth.backfill.v1",
                "completed_sessions": ["2026-01-05"],
                "sessions": {"2026-01-05": {"source": "fixture"}},
            }
        )
    )
    sessions = [date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7)]
    calls: list[date] = []

    def processor(session: date) -> SessionAcceptance:
        calls.append(session)
        return _accept(session)

    report = run_backfill(
        sessions,
        processor=processor,
        state_path=state_path,
        max_sessions=1,
        resume=True,
    )

    assert calls == [date(2026, 1, 6)]
    assert report.processed_sessions == (date(2026, 1, 6),)
    assert report.remaining_sessions == (date(2026, 1, 7),)
    assert report.completed_total == 2
    state = json.loads(state_path.read_text())
    assert state["completed_sessions"] == ["2026-01-05", "2026-01-06"]


def test_partial_or_failed_session_remains_pending_and_checkpoint_does_not_advance(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "exchange_breadth.backfill.v1",
                "completed_sessions": ["2026-01-05"],
                "sessions": {"2026-01-05": {"source": "fixture"}},
            }
        )
    )
    before = state_path.read_bytes()

    def partial(session: date) -> SessionAcceptance:
        return SessionAcceptance(
            session=session,
            roster_reconciled=True,
            price_reconciled=False,
            published=False,
            source="fixture",
            receipt={"accepted_session": session.isoformat()},
        )

    with pytest.raises(BackfillRefused, match="price evidence"):
        run_backfill(
            [date(2026, 1, 6)],
            processor=partial,
            state_path=state_path,
            resume=True,
        )

    assert state_path.read_bytes() == before


def test_checkpoint_only_advances_after_published_generation(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"

    def unpublished(session: date) -> SessionAcceptance:
        return SessionAcceptance(
            session=session,
            roster_reconciled=True,
            price_reconciled=True,
            published=False,
            source="fixture",
            receipt={"accepted_session": session.isoformat()},
        )

    with pytest.raises(BackfillRefused, match="published generation"):
        run_backfill(
            [date(2026, 1, 5)],
            processor=unpublished,
            state_path=state_path,
        )

    assert not state_path.exists()


def test_rerun_is_idempotent(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    sessions = [date(2026, 1, 5), date(2026, 1, 6)]
    calls: list[date] = []

    def processor(session: date) -> SessionAcceptance:
        calls.append(session)
        return _accept(session)

    first = run_backfill(sessions, processor=processor, state_path=state_path)
    second = run_backfill(sessions, processor=processor, state_path=state_path)

    assert first.processed_sessions == tuple(sessions)
    assert second.processed_sessions == ()
    assert second.remaining_sessions == ()
    assert calls == sessions
    assert second.completed_total == 2


def test_dry_run_neither_calls_processor_nor_writes_state(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    called = False

    def processor(_session: date) -> SessionAcceptance:
        nonlocal called
        called = True
        raise AssertionError("dry-run must not process sessions")

    report = run_backfill(
        [date(2026, 1, 5), date(2026, 1, 6)],
        processor=processor,
        state_path=state_path,
        dry_run=True,
    )

    assert not called
    assert not state_path.exists()
    assert report.processed_sessions == ()
    assert report.remaining_sessions == (
        date(2026, 1, 5),
        date(2026, 1, 6),
    )


def test_grouped_daily_fetch_is_raw_finalized_and_mockable() -> None:
    calls: list[tuple[str, dict]] = []

    def request_json(url: str, params: dict) -> dict:
        calls.append((url, dict(params)))
        return {
            "status": "OK",
            "queryCount": 3,
            "resultsCount": 3,
            "results": [
                {"T": "AAA", "c": 100.0},
                {"T": "BBB", "c": 50.0},
                {"T": "ZZZ", "c": 9.0},
            ],
        }

    client = GroupedDailyPriceClient(
        api_key="secret-key",
        base_url="https://api.example.test",
        request_json=request_json,
    )
    evidence = client.fetch(END, {"AAA", "BBB"})

    assert evidence.finalized is True
    assert evidence.source == "massive_grouped"
    assert evidence.closes == {"AAA": 100.0, "BBB": 50.0}
    assert evidence.wanted_n == 2
    assert evidence.matched_n == 2
    assert calls == [
        (
            "https://api.example.test/v2/aggs/grouped/locale/us/market/stocks/2026-01-09",
            {
                "adjusted": "false",
                "include_otc": "false",
                "apiKey": "secret-key",
            },
        )
    ]
    assert "secret-key" not in json.dumps(evidence.receipt)


def test_grouped_daily_refuses_partial_price_evidence() -> None:
    client = GroupedDailyPriceClient(
        api_key="key",
        base_url="https://api.example.test",
        request_json=lambda _url, _params: {
            "status": "OK",
            "queryCount": 1,
            "resultsCount": 1,
            "results": [{"T": "AAA", "c": 100.0}],
        },
    )

    with pytest.raises(BackfillRefused, match="coverage"):
        client.fetch(END, {"AAA", "BBB"}, min_coverage=1.0)


def test_recent_r2_and_grouped_daily_paths_have_split_metric_parity() -> None:
    sessions = [date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7)]
    grouped = {
        sessions[0]: {"AAA": 100.0, "BBB": 50.0},
        sessions[1]: {"AAA": 50.0, "BBB": 51.0},
        sessions[2]: {"AAA": 52.0, "BBB": 52.0},
    }
    grouped_history = grouped_session_maps_to_history(grouped)
    r2_history = {
        "AAA": pd.Series(
            [100.0, 50.0, 52.0], index=pd.DatetimeIndex(sessions), name="AAA"
        ),
        "BBB": pd.Series(
            [50.0, 51.0, 52.0], index=pd.DatetimeIndex(sessions), name="BBB"
        ),
    }
    for ticker in r2_history:
        pd.testing.assert_series_equal(grouped_history[ticker], r2_history[ticker])

    intervals = pd.DataFrame(
        [
            {
                "universe_key": universe,
                "entity_key": f"SEC:{ticker}",
                "security_id": f"SEC:{ticker}",
                "share_class_figi": None,
                "composite_figi": None,
                "ticker": ticker,
                "name": ticker,
                "ticker_type": "CS",
                "primary_exchange": "XNYS",
                "currency": "usd",
                "valid_from_session": pd.Timestamp(sessions[0]),
                "valid_to_session": pd.Timestamp(sessions[-1]),
                "source": "fixture",
                "source_rules_version": "exchange_breadth.xnys.v1",
            }
            for universe in (UNIVERSE_OPERATING, UNIVERSE_ALL_ISSUES)
            for ticker in ("AAA", "BBB")
        ]
    )
    splits = pd.DataFrame(
        [
            {
                "entity_key": "SEC:AAA",
                "execution_date": pd.Timestamp(sessions[1]),
                "split_from": 1.0,
                "split_to": 2.0,
                "adjustment_type": "forward_split",
            }
        ]
    )

    from scripts.backfill_exchange_breadth import compute_backfill_frames

    counts = {
        UNIVERSE_OPERATING: {"listed_n": 2, "resolved_identity_n": 2},
        UNIVERSE_ALL_ISSUES: {"listed_n": 2, "resolved_identity_n": 2},
    }
    grouped_frames = compute_backfill_frames(
        intervals=intervals,
        splits=splits,
        prices=grouped_history,
        observation_session=sessions[-1],
        state={},
        counts=counts,
    )
    r2_frames = compute_backfill_frames(
        intervals=intervals,
        splits=splits,
        prices=r2_history,
        observation_session=sessions[-1],
        state={},
        counts=counts,
    )

    for universe in (UNIVERSE_OPERATING, UNIVERSE_ALL_ISSUES):
        pd.testing.assert_frame_equal(grouped_frames[universe], r2_frames[universe])


def test_real_session_processor_publishes_checkpointed_history(tmp_path: Path) -> None:
    from collectors.exchange_breadth import PageBundle
    from scripts.backfill_exchange_breadth import ExchangeBreadthSessionProcessor

    sessions = [date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7)]
    reference = tmp_path / "reference"
    reference.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "vendor": "massive",
                "vendor_symbol": "AAA",
                "security_id": "SEC:AAA",
                "valid_from": None,
                "valid_to": None,
            },
            {
                "vendor": "massive",
                "vendor_symbol": "BBB",
                "security_id": "SEC:BBB",
                "valid_from": None,
                "valid_to": None,
            },
        ]
    ).to_parquet(reference / "vendor_aliases.parquet", index=False)

    roster_rows = (
        {
            "ticker": "AAA",
            "name": "AAA Corp",
            "market": "stocks",
            "locale": "us",
            "primary_exchange": "XNYS",
            "type": "CS",
            "active": True,
            "currency_name": "usd",
            "share_class_figi": None,
            "composite_figi": None,
        },
        {
            "ticker": "BBB",
            "name": "BBB Corp",
            "market": "stocks",
            "locale": "us",
            "primary_exchange": "XNYS",
            "type": "CS",
            "active": True,
            "currency_name": "usd",
            "share_class_figi": None,
            "composite_figi": None,
        },
    )

    class ReferenceClient:
        def fetch_roster(self, session: date, *, min_rows: int) -> PageBundle:
            assert min_rows == 2
            return PageBundle(
                rows=roster_rows,
                receipt={
                    "requested_session": session.isoformat(),
                    "request_ids": [f"roster-{session}"],
                    "row_count": 2,
                },
            )

        def fetch_splits(self, start: date, end: date) -> PageBundle:
            assert start == sessions[0]
            assert end == sessions[-1]
            return PageBundle(
                rows=(),
                receipt={
                    "execution_date_gte": start.isoformat(),
                    "execution_date_lte": end.isoformat(),
                    "request_ids": ["splits-quiet"],
                    "row_count": 0,
                },
            )

    price_frames = {
        "AAA": pd.DataFrame(
            {"close": [100.0, 101.0, 102.0]},
            index=pd.DatetimeIndex(sessions, name="date"),
        ),
        "BBB": pd.DataFrame(
            {"close": [50.0, 49.0, 51.0]},
            index=pd.DatetimeIndex(sessions, name="date"),
        ),
    }

    processor = ExchangeBreadthSessionProcessor(
        target_sessions=sessions,
        reference_client=ReferenceClient(),
        grouped_client=None,
        data_root=tmp_path,
        r2_first_session=sessions[0],
        r2_last_session=sessions[-1],
        price_loader=lambda ticker: price_frames.get(ticker, pd.DataFrame()),
        min_roster_rows=2,
        min_operating_rows=2,
        min_identity_coverage=1.0,
        min_price_coverage=1.0,
    )
    state_path = tmp_path / "exchange_breadth" / "_backfill_state.json"
    report = run_backfill(
        sessions,
        processor=processor,
        state_path=state_path,
        max_sessions=2,
        resume=True,
    )

    assert report.processed_sessions == tuple(sessions[:2])
    assert report.remaining_sessions == (sessions[2],)
    output = tmp_path / "exchange_breadth"
    assert (output / "nyse_operating.parquet").exists()
    assert (output / "nyse_all_issues.parquet").exists()
    intervals = pd.read_parquet(output / "universe_intervals.parquet")
    assert set(intervals["entity_key"]) == {"SEC:AAA", "SEC:BBB"}
    assert pd.Timestamp(intervals["valid_to_session"].max()).date() == sessions[1]
    main_state = json.loads((output / "_state.json").read_text())
    assert main_state["last_observed_session"] == sessions[1].isoformat()
    assert main_state["accepted_sessions"] == [
        sessions[0].isoformat(),
        sessions[1].isoformat(),
    ]
    receipt = json.loads((output / "_receipt.json").read_text())
    assert receipt["accepted_session"] == sessions[1].isoformat()
    assert receipt["backfill"]["price_source"] == "massive_stock_day_r2"
    assert receipt["universes"][UNIVERSE_OPERATING]["priced_n"] == 2
    assert receipt["universes"][UNIVERSE_ALL_ISSUES]["priced_n"] == 2


def test_real_processor_refuses_out_of_order_backfill(tmp_path: Path) -> None:
    from collectors.exchange_breadth import PageBundle
    from scripts.backfill_exchange_breadth import ExchangeBreadthSessionProcessor

    output = tmp_path / "exchange_breadth"
    output.mkdir(parents=True)
    (output / "_state.json").write_text(
        json.dumps(
            {
                "schema_version": "exchange_breadth.collector.v1",
                "source_rules_version": "exchange_breadth.xnys.v1",
                "last_observed_session": "2026-01-07",
                "accepted_sessions": ["2026-01-07"],
                "session_counts": {},
            }
        )
    )

    class ReferenceClient:
        def fetch_roster(self, session: date, *, min_rows: int) -> PageBundle:
            raise AssertionError("out-of-order gate must fire before source access")

        def fetch_splits(self, start: date, end: date) -> PageBundle:
            return PageBundle(rows=(), receipt={})

    with pytest.raises(BackfillRefused, match="out of order"):
        ExchangeBreadthSessionProcessor(
            target_sessions=[date(2026, 1, 5)],
            reference_client=ReferenceClient(),
            grouped_client=None,
            data_root=tmp_path,
            r2_first_session=date(2026, 1, 5),
            r2_last_session=date(2026, 1, 7),
            price_loader=lambda _ticker: pd.DataFrame(),
            min_roster_rows=1,
            min_operating_rows=1,
            min_identity_coverage=0.0,
            min_price_coverage=0.0,
        )


def test_backfill_workflow_has_bounded_exchange_breadth_lane() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "backfill.yml").read_text()

    assert "breadth_recent_sessions" in workflow
    assert "breadth_max_sessions" in workflow
    assert (
        "python -m scripts.fetch_r2 --dirs massive_stock_day --workers 24" in workflow
    )
    assert "python -m scripts.backfill_exchange_breadth" in workflow
    assert "--recent-sessions" in workflow
    assert "--max-sessions" in workflow
    assert "only == 'exchange_breadth'" in workflow
    assert "git add data/exchange_breadth/" in workflow
    assert (
        "only != 'gold_china_basis' && github.event.inputs.only != 'exchange_breadth'"
        in workflow
    )


def test_promoted_session_reconciles_missing_backfill_checkpoint_without_refetch(
    tmp_path: Path,
) -> None:
    from scripts.backfill_exchange_breadth import ExchangeBreadthSessionProcessor

    session = date(2026, 1, 5)
    output = tmp_path / "exchange_breadth"
    output.mkdir(parents=True)
    state = {
        "schema_version": "exchange_breadth.collector.v1",
        "source_rules_version": "exchange_breadth.xnys.v1",
        "last_observed_session": session.isoformat(),
        "accepted_sessions": [session.isoformat()],
        "session_counts": {
            session.isoformat(): {
                UNIVERSE_OPERATING: {
                    "listed_n": 2,
                    "resolved_identity_n": 2,
                    "priced_n": 2,
                },
                UNIVERSE_ALL_ISSUES: {
                    "listed_n": 2,
                    "resolved_identity_n": 2,
                    "priced_n": 2,
                },
            }
        },
    }
    (output / "_state.json").write_text(json.dumps(state))
    (output / "_receipt.json").write_text(
        json.dumps(
            {
                "accepted": True,
                "accepted_session": session.isoformat(),
                "authority": "display_research_context_only",
            }
        )
    )
    frame = pd.DataFrame(
        {"listed_n": [2], "priced_n": [2], "adv": [1], "dec": [1]},
        index=pd.DatetimeIndex([pd.Timestamp(session)], name="session"),
    )
    frame.to_parquet(output / "nyse_operating.parquet")
    frame.to_parquet(output / "nyse_all_issues.parquet")

    processor = object.__new__(ExchangeBreadthSessionProcessor)
    processor.state = state
    processor.output_dir = output
    processor.target_set = {session}
    processor.reference_client = object()
    checkpoint = output / "_backfill_state.json"

    report = run_backfill(
        [session],
        processor=processor,
        state_path=checkpoint,
        resume=True,
    )

    assert report.processed_sessions == (session,)
    assert report.remaining_sessions == ()
    persisted = json.loads(checkpoint.read_text())
    assert persisted["completed_sessions"] == [session.isoformat()]
    assert persisted["sessions"][session.isoformat()]["source"] == (
        "accepted_generation_reconciliation"
    )
    assert (
        persisted["sessions"][session.isoformat()]["receipt"][
            "reconciled_existing_generation"
        ]
        is True
    )


def test_completed_cli_rerun_needs_no_vendor_key_or_source_access(
    tmp_path: Path, capsys
) -> None:
    from scripts.backfill_exchange_breadth import main

    sessions = [date(2026, 1, 5), date(2026, 1, 6)]
    state_path = tmp_path / "backfill-state.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "exchange_breadth.backfill.v1",
                "completed_sessions": [session.isoformat() for session in sessions],
                "sessions": {
                    session.isoformat(): {"source": "fixture"} for session in sessions
                },
            }
        )
    )

    rc = main(
        [
            "--start",
            sessions[0].isoformat(),
            "--end",
            sessions[-1].isoformat(),
            "--state-path",
            str(state_path),
            "--resume",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["processed_sessions"] == []
    assert payload["remaining_sessions"] == []
    assert payload["completed_total"] == 2


def test_grouped_daily_preserves_case_and_punctuation_exact_vendor_keys() -> None:
    client = GroupedDailyPriceClient(
        api_key="k",
        base_url="https://api.example.test",
        request_json=lambda _url, _params: {
            "status": "OK",
            "queryCount": 3,
            "resultsCount": 3,
            "results": [
                {"T": "TPC", "c": 94.67},
                {"T": "TpC", "c": 16.98},
                {"T": "BRK.B", "c": 500.0},
            ],
        },
    )

    evidence = client.fetch(
        END,
        {"TPC", "TpC", "BRK.B"},
        min_coverage=1.0,
    )

    assert evidence.closes == {
        "TPC": 94.67,
        "TpC": 16.98,
        "BRK.B": 500.0,
    }
