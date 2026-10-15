"""Hermetic tests for engine/news_impact/tape_draw.py (lane W2_D1a).

Builds tiny synthetic parquet files in tmp_path. The test ledger is:
    {"note": "t", "tickers": {"AAPL": 320193, "JPM": 19617, "MSFT": 789019, "F": 37996}}
``low_value=lambda title, domain="": "advertorial" in title.lower()`` is
injected everywhere except the one default-predicate test.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.news_impact import tape_draw as TD
from engine.news_impact.issuer import load_ledger
from engine.news_impact.sampler import (
    CELLS,
    MANIFEST_SCHEMA,
    Case,
    TEMPLATES,
    Candidate,
    SamplePlan,
    build_manifest,
    draw_sample,
)

UTC = timezone.utc


# ----------------------------------------------------------------- fixtures


def _low_value():
    return lambda title, domain="": "advertorial" in (title or "").lower()


def _write_tape_parquet(path, rows):
    pd = pytest.importorskip("pandas", reason="pandas not importable on this host")
    try:
        frame = pd.DataFrame(rows)
        frame.to_parquet(path)
    except Exception as exc:
        pytest.skip(f"parquet engine unavailable on this host: {exc}")


def _write_event_log_parquet(path, rows):
    pd = pytest.importorskip("pandas", reason="pandas not importable on this host")
    try:
        frame = pd.DataFrame(rows)
        frame.to_parquet(path)
    except Exception as exc:
        pytest.skip(f"parquet engine unavailable on this host: {exc}")


def _write_reject_parquet(path, rows):
    pd = pytest.importorskip("pandas", reason="pandas not importable on this host")
    try:
        frame = pd.DataFrame(rows)
        frame.to_parquet(path)
    except Exception as exc:
        pytest.skip(f"parquet engine unavailable on this host: {exc}")


def _write_ledger(path):
    path.write_text(
        json.dumps(
            {
                "note": "t",
                "tickers": {
                    "AAPL": 320193,
                    "JPM": 19617,
                    "MSFT": 789019,
                    "F": 37996,
                },
            }
        )
    )


def _row(
    item_id,
    title,
    seendate,
    *,
    lang="en",
    source="reuters",
    source_tier=1,
    url="https://example.com/x",
    event_key="",
    entities="AAPL",
    body_sha256="",
    desk="financial_news",
    timestamp_quality="PUBLISHER_STATED",
    _crawled_at=None,
    themes="",
    importance_raw=1.0,
):
    if _crawled_at is None:
        _crawled_at = seendate
    return {
        "item_id": item_id,
        "event_key": event_key,
        "desk": desk,
        "source": source,
        "source_tier": source_tier,
        "lang": lang,
        "url": url,
        "title": title,
        "body_sha256": body_sha256,
        "seendate": seendate,
        "_crawled_at": _crawled_at,
        "timestamp_quality": timestamp_quality,
        "entities": entities,
        "themes": themes,
        "importance_raw": importance_raw,
    }


def _aware(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _el_row(event_id, event_type, tickers, title="Some title", seendate=None, domain="cnbc.com"):
    if seendate is None:
        seendate = "2026-09-01T00:00:00+00:00"
    return {
        "event_id": event_id,
        "first_seen_utc": seendate,
        "seendate": seendate,
        "title": title,
        "domain": domain,
        "source_tier": "tier1",
        "event_type": event_type,
        "direction": "bullish",
        "centrality": "primary",
        "tickers": tickers,
        "theme": "x",
        "novelty_z": 0.0,
    }


def _rej_row(event_id, title="Reject", reason="stock_pick_roundup", tickers="[]", seendate=""):
    return {
        "event_id": event_id,
        "first_seen_utc": seendate,
        "seendate": seendate,
        "title": title,
        "domain": "yahoo.com",
        "feed": "macro",
        "reason": reason,
        "tickers": tickers,
    }


# ----------------------------------------------------------------- T1 family/cell precedence


def test_family_and_template_precedence():
    t1_and_t2 = "Apple announces stock buyback and raises guidance"
    t2_and_t3 = "Microsoft raises guidance and partners with Google"
    assert TD.template_of(TD.family_hits(t1_and_t2)) == "T1"
    assert TD.template_of(TD.family_hits(t2_and_t3)) == "T2"


def test_proxy_cell_precedence_neg_amb_noc_positive():
    assert TD.proxy_cell_of("Should you buy Apple stock?") == "negative"
    assert TD.proxy_cell_of("Apple considers buying Google") == "ambiguous"
    assert TD.proxy_cell_of(
        "Apple declares a regular quarterly cash dividend"
    ) == "no_change"
    assert TD.proxy_cell_of("Apple announces stock buyback") == "positive"


def test_no_family_returns_none():
    assert TD.template_of(TD.family_hits("Apple reports earnings today")) is None


# ----------------------------------------------------------------- T2 funnel


def test_funnel_one_row_per_stage(tmp_path):
    tape_rows = [
        _row("a1", "blank seendate", "", source="x"),  # dropped by load_tape (blank)
        _row("a2", "old story", "2020-01-01T00:00:00+00:00", source="x"),
        _row("a3", "deutsche headline", "2026-08-01T00:00:00+00:00", lang="de", source="x"),
        _row("a4", "Buy this advertorial now", "2026-08-02T00:00:00+00:00", source="x"),
        _row(
            "a5",
            "Apple reports earnings today",
            "2026-08-03T00:00:00+00:00",
            source="x",
        ),
        _row(
            "a6",
            "Apple announces stock buyback",
            "2026-08-04T00:00:00+00:00",
            source="x",
        ),
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)

    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    ledger = load_ledger(str(ledger_path))

    from engine.news_impact.sampler import load_tape

    dropped = {}
    wide_rows = load_tape(
        str(tape_path),
        window_start=date(1970, 1, 1),
        window_end=date(2100, 12, 31),
        dropped=dropped,
    )
    total_rows = len(wide_rows) + int(sum(dropped.values()))
    assert total_rows == 6

    ws = date(2026, 7, 1)
    we = date(2026, 10, 11)
    build = TD.build_candidates(
        wide_rows,
        window_start=ws,
        window_end=we,
        event_log_rows=[],
        reject_rows=[],
        ledger=ledger,
        low_value=_low_value(),
        dropped=dropped,
        total_rows=total_rows,
    )

    funnel = build.report["funnel"]
    assert funnel["seendate_dropped"] == 1
    assert funnel["outside_window"] == 1
    assert funnel["non_english"] == 1
    assert funnel["low_value"] == 1
    assert funnel["no_family"] == 1
    assert funnel["candidate"] == 1
    assert funnel["total"] == 6
    assert sum(
        funnel[k]
        for k in (
            "seendate_dropped",
            "outside_window",
            "non_english",
            "low_value",
            "no_family",
            "candidate",
        )
    ) == 6


# ----------------------------------------------------------------- T3 window


def test_default_window_is_90_days_inclusive(tmp_path):
    tape_rows = [
        _row("w1", "x", "2026-05-01T00:00:00+00:00"),
        _row("w2", "y", "2026-09-30T00:00:00+00:00"),
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    from engine.news_impact.sampler import load_tape

    rows = load_tape(
        str(tape_path),
        window_start=date(1970, 1, 1),
        window_end=date(2100, 12, 31),
    )
    ws, we = TD.default_window(rows)
    assert we == date(2026, 9, 30)
    assert ws == date(2026, 9, 30) - timedelta(days=89)
    assert (we - ws).days == 89


def test_window_overrides_end_only_start_only_and_both(tmp_path):
    tape_rows = [
        _row("w1", "x", "2026-09-30T00:00:00+00:00"),
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    from engine.news_impact.sampler import load_tape

    rows = load_tape(
        str(tape_path),
        window_start=date(1970, 1, 1),
        window_end=date(2100, 12, 31),
    )

    # end-only: keeps default end (max seendate)
    ws, we = TD._resolve_run_window(rows, None, None)
    assert we == date(2026, 9, 30)
    assert ws == date(2026, 9, 30) - timedelta(days=89)

    # end-only: window_start given keeps the default end
    ws, we = TD._resolve_run_window(rows, date(2026, 1, 1), None)
    assert we == date(2026, 9, 30)
    assert ws == date(2026, 1, 1)

    # start-only: window_end given recomputes the start from it
    ws, we = TD._resolve_run_window(rows, None, date(2026, 9, 30))
    assert we == date(2026, 9, 30)
    assert ws == date(2026, 9, 30) - timedelta(days=89)

    # both given
    ws, we = TD._resolve_run_window(rows, date(2026, 8, 1), date(2026, 9, 1))
    assert (ws, we) == (date(2026, 8, 1), date(2026, 9, 1))


def test_window_start_after_end_raises(tmp_path):
    tape_rows = [_row("w1", "x", "2026-09-30T00:00:00+00:00")]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    from engine.news_impact.sampler import load_tape

    rows = load_tape(
        str(tape_path),
        window_start=date(1970, 1, 1),
        window_end=date(2100, 12, 31),
    )
    with pytest.raises(TD.TapeDrawError):
        TD._resolve_run_window(rows, date(2026, 10, 1), date(2026, 9, 1))


# ----------------------------------------------------------------- T4 event_log feeder


def test_event_log_feeder_overrides_template_and_uses_tickers(tmp_path):
    tape_rows = [
        _row(
            "e1",
            "JPMorgan declares something",
            "2026-08-01T00:00:00+00:00",
            entities="",
        ),
        _row(
            "e2",
            "Microsoft raises guidance today",
            "2026-08-02T00:00:00+00:00",
            entities="",
        ),
        _row(
            "e3",
            "Apple stock buyback today",
            "2026-08-03T00:00:00+00:00",
            entities="",
        ),
        _row(
            "e4",
            "JPMorgan declares a regular quarterly cash dividend",
            "2026-08-04T00:00:00+00:00",
            entities="",
        ),
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    event_log = [
        _el_row("e1", "buyback", '["JPM"]'),
        _el_row("e2", "earnings_result", '["MSFT"]'),
        _el_row("e3", "earnings_result", '["AAPL"]'),
        _el_row("e4", "dividend_change", '["JPM"]'),
    ]
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, event_log)
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, [])

    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)

    from engine.news_impact.sampler import load_tape

    wide_rows = load_tape(
        str(tape_path),
        window_start=date(1970, 1, 1),
        window_end=date(2100, 12, 31),
    )
    ledger = load_ledger(str(ledger_path))
    build = TD.build_candidates(
        wide_rows,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
        event_log_rows=event_log,
        reject_rows=[],
        ledger=ledger,
        low_value=_low_value(),
        dropped={},
        total_rows=len(wide_rows),
    )
    by_id = {c.item_id: c for c in build.candidates}
    by_meta = {m["item_id"]: m for m in build.meta}
    assert by_id["e1"].template == "T1"
    assert by_id["e1"].proxy_cell == "positive"
    assert by_meta["e1"]["feeder"] == "event_log"
    assert by_meta["e1"]["event_type"] == "buyback"
    assert by_id["e1"].issuer == "cik:0000019617"

    # unmapped event_type "earnings_result" falls through to regex
    assert by_meta["e2"]["feeder"] == "regex"
    assert by_meta["e3"]["feeder"] == "regex"

    # no_change when NOC matches
    assert by_id["e4"].proxy_cell == "no_change"
    assert by_meta["e4"]["feeder"] == "event_log"


# ----------------------------------------------------------------- T5 reject feeder


def test_reject_feeder_negative_and_bypasses_low_value(tmp_path):
    tape_rows = [
        _row(
            "r1",
            "Apple stock buyback advertorial thing here",
            "2026-08-01T00:00:00+00:00",
            source="x",
        ),
        _row(
            "r2",
            "Apple stock buyback real news",
            "2026-08-02T00:00:00+00:00",
            source="x",
        ),
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    reject = [
        _rej_row("r1", title="Apple stock buyback advertorial thing here"),
        _rej_row("r2", title="Apple stock buyback real news"),
        _rej_row("not_on_tape", title="Apple stock buyback something"),
    ]
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, reject)
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, [])
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)

    result = TD.run_draw(
        str(tape_path),
        str(el_path),
        str(rej_path),
        str(ledger_path),
        seed=20261014,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
        low_value=_low_value(),
    )
    by_meta = {m["item_id"]: m for m in result.meta}
    # r1 is reject-routed, the title contains "advertorial" so it would
    # normally be filtered by the injected low_value, but reject bypasses
    assert by_meta["r1"]["feeder"] == "reject"
    assert by_meta["r1"]["proxy_cell"] == "negative"
    # r2 is also reject-routed, also negative
    assert by_meta["r2"]["feeder"] == "reject"
    # reject row not on tape is counted
    assert result.report["feeders"]["reject_not_on_tape"] == 1


def test_reject_with_no_family_counts_as_no_family(tmp_path):
    tape_rows = [
        _row("n1", "Apple just made an announcement today", "2026-08-01T00:00:00+00:00"),
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    reject = [_rej_row("n1", title="Apple just made an announcement today")]
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, reject)
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, [])
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    result = TD.run_draw(
        str(tape_path),
        str(el_path),
        str(rej_path),
        str(ledger_path),
        seed=20261014,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
        low_value=_low_value(),
    )
    assert result.report["funnel"]["no_family"] == 1
    assert result.report["funnel"]["candidate"] == 0


def test_event_log_wins_over_reject(tmp_path):
    tape_rows = [
        _row("x1", "Apple declares something", "2026-08-01T00:00:00+00:00", entities=""),
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    event_log = [_el_row("x1", "buyback", '["AAPL"]')]
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, event_log)
    reject = [_rej_row("x1")]
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, reject)
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    result = TD.run_draw(
        str(tape_path),
        str(el_path),
        str(rej_path),
        str(ledger_path),
        seed=20261014,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
        low_value=_low_value(),
    )
    by_meta = {m["item_id"]: m for m in result.meta}
    assert by_meta["x1"]["feeder"] == "event_log"


# ----------------------------------------------------------------- T6 issuer


def test_issuer_resolution_paths(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    ledger = load_ledger(str(ledger_path))

    assert TD._resolve_entities(
        ["AAPL"], "Apple", date(2026, 9, 1), ledger
    )[0] == "cik:0000320193"

    issuer, ticker, ciks, pv = TD._resolve_entities(
        ["JPMpC"], "JPM", date(2026, 9, 1), ledger
    )
    assert issuer == "cik:0000019617"
    assert ticker == "JPM"
    assert pv == 1

    issuer, _, _, _ = TD._resolve_entities(
        ["ZZZZ"], "Z", date(2026, 9, 1), ledger
    )
    assert issuer == "unresolved:unknown_ticker"

    issuer, _, _, _ = TD._resolve_entities(
        ["AAPL", "F"], "X", date(2026, 9, 1), ledger
    )
    assert issuer == "cik:0000320193"

    issuer, ticker, _, _ = TD._resolve_entities(
        ["F"], "Ford", date(2026, 9, 1), ledger
    )
    assert issuer == "cik:0000037996"
    assert ticker == "F"

    issuer, ticker, _, _ = TD._resolve_entities(
        [], "Empty", date(2026, 9, 1), ledger
    )
    assert issuer == "unresolved:no_mention"
    assert ticker is None


# ----------------------------------------------------------------- T7 tags


def test_indirect_transfer_tag(tmp_path):
    tape_rows = [
        _row(
            "i1",
            "JPMorgan stock buyback announced",
            "2026-08-01T00:00:00+00:00",
            entities="JPM,MSFT",
        ),
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, [])
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, [])
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    from engine.news_impact.sampler import load_tape

    wide_rows = load_tape(
        str(tape_path),
        window_start=date(1970, 1, 1),
        window_end=date(2100, 12, 31),
    )
    ledger = load_ledger(str(ledger_path))
    build = TD.build_candidates(
        wide_rows,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
        event_log_rows=[],
        reject_rows=[],
        ledger=ledger,
        low_value=_low_value(),
        dropped={},
        total_rows=len(wide_rows),
    )
    assert "indirect_transfer" in build.candidates[0].tags
    assert build.report["tags"]["indirect_transfer"] == 1


def test_near_duplicate_tag_inclusive_bounds(tmp_path):
    rows = []
    for i in range(3):
        rows.append(
            _row(
                f"d{i}",
                f"JPMorgan stock buyback thing {i}",
                f"2026-08-0{i+1}T00:00:00+00:00",
                event_key="ev_dup",
                entities="JPM",
            )
        )
    for i in range(6):
        rows.append(
            _row(
                f"s{i}",
                f"JPMorgan stock buyback big {i}",
                f"2026-08-1{i+1}T00:00:00+00:00",
                event_key="ev_six",
                entities="JPM",
            )
        )
    rows.append(
        _row(
            "x1",
            "JPMorgan stock buyback alone",
            "2026-08-20T00:00:00+00:00",
            event_key="ev_one",
            entities="JPM",
        )
    )
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, rows)
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, [])
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, [])
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    from engine.news_impact.sampler import load_tape

    wide_rows = load_tape(
        str(tape_path),
        window_start=date(1970, 1, 1),
        window_end=date(2100, 12, 31),
    )
    ledger = load_ledger(str(ledger_path))
    build = TD.build_candidates(
        wide_rows,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
        event_log_rows=[],
        reject_rows=[],
        ledger=ledger,
        low_value=_low_value(),
        dropped={},
        total_rows=len(wide_rows),
    )
    nd = {c.item_id: "near_duplicate" in c.tags for c in build.candidates}
    # 3 in-window -> tagged
    for i in range(3):
        assert nd[f"d{i}"]
    # 6 -> NOT tagged
    for i in range(6):
        assert not nd[f"s{i}"]
    # 1 -> NOT tagged
    assert not nd["x1"]


# ----------------------------------------------------------------- T8 holdout


def test_holdout_chain_and_event_key(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    from engine.news_impact.sampler import load_tape
    from hashlib import sha256

    base = datetime(2026, 8, 1, 12, tzinfo=UTC)

    # --- Scenario A: chain 0,2,4 -> one group
    rows_a = [
        _row(
            "a1",
            "JPMorgan stock buyback",
            base.isoformat(),
            entities="JPM",
        ),
        _row(
            "a2",
            "JPMorgan stock buyback",
            (base + timedelta(days=2)).isoformat(),
            entities="JPM",
        ),
        _row(
            "a3",
            "JPMorgan stock buyback",
            (base + timedelta(days=4)).isoformat(),
            entities="JPM",
        ),
    ]
    tape_path = tmp_path / "items_a.parquet"
    _write_tape_parquet(tape_path, rows_a)
    wide_rows = load_tape(
        str(tape_path),
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 30),
    )
    ledger = load_ledger(str(ledger_path))
    build_a = TD.build_candidates(
        wide_rows,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 30),
        event_log_rows=[],
        reject_rows=[],
        ledger=ledger,
        low_value=_low_value(),
        dropped={},
        total_rows=len(wide_rows),
    )
    by_id_a = {c.item_id: c.event_key for c in build_a.candidates}
    assert by_id_a["a1"] == by_id_a["a2"] == by_id_a["a3"]
    # key format
    for k in by_id_a.values():
        assert re.fullmatch(r"^hg:[0-9a-f]{16}$", k), k
    # sha256 formula
    expected_a = "hg:" + sha256(
        "\n".join(sorted(["a1", "a2", "a3"])).encode()
    ).hexdigest()[:16]
    assert by_id_a["a1"] == expected_a

    # --- Scenario B: gap 3 -> two groups
    rows_b = [
        _row(
            "b1",
            "JPMorgan stock buyback",
            base.isoformat(),
            entities="JPM",
        ),
        _row(
            "b2",
            "JPMorgan stock buyback",
            (base + timedelta(days=3)).isoformat(),
            entities="JPM",
        ),
    ]
    tape_path = tmp_path / "items_b.parquet"
    _write_tape_parquet(tape_path, rows_b)
    wide_rows = load_tape(
        str(tape_path),
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 30),
    )
    build_b = TD.build_candidates(
        wide_rows,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 30),
        event_log_rows=[],
        reject_rows=[],
        ledger=ledger,
        low_value=_low_value(),
        dropped={},
        total_rows=len(wide_rows),
    )
    by_id_b = {c.item_id: c.event_key for c in build_b.candidates}
    assert by_id_b["b1"] != by_id_b["b2"]

    # --- Scenario C: shared event_key joins different issuers
    rows_c = [
        _row(
            "c1",
            "JPMorgan stock buyback",
            base.isoformat(),
            entities="JPM",
            event_key="ev_x",
        ),
        _row(
            "c2",
            "Ford stock buyback",
            (base + timedelta(days=1)).isoformat(),
            entities="F",
            event_key="ev_x",
        ),
    ]
    tape_path = tmp_path / "items_c.parquet"
    _write_tape_parquet(tape_path, rows_c)
    wide_rows = load_tape(
        str(tape_path),
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 30),
    )
    build_c = TD.build_candidates(
        wide_rows,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 30),
        event_log_rows=[],
        reject_rows=[],
        ledger=ledger,
        low_value=_low_value(),
        dropped={},
        total_rows=len(wide_rows),
    )
    by_id_c = {c.item_id: c.event_key for c in build_c.candidates}
    cand_by_id = {c.item_id: c for c in build_c.candidates}
    assert by_id_c["c1"] == by_id_c["c2"]
    assert cand_by_id["c1"].issuer != cand_by_id["c2"].issuer


# ----------------------------------------------------------------- T9 determinism / manifest


def test_run_draw_is_deterministic_and_manifest_validates(tmp_path):
    tape_rows = [
        _row(
            f"d{i}",
            f"Apple stock buyback news {i}",
            f"2026-08-{(i % 28) + 1:02d}T00:00:00+00:00",
        )
        for i in range(20)
    ] + [
        _row(
            "m1",
            "Microsoft announces stock buyback today",
            "2026-08-10T00:00:00+00:00",
            entities="MSFT",
        ),
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, [])
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, [])
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)

    r1 = TD.run_draw(
        str(tape_path),
        str(el_path),
        str(rej_path),
        str(ledger_path),
        seed=20261014,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
        low_value=_low_value(),
    )
    r2 = TD.run_draw(
        str(tape_path),
        str(el_path),
        str(rej_path),
        str(ledger_path),
        seed=20261014,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
        low_value=_low_value(),
    )
    assert [c.to_dict() for c in r1.draw.cases] == [c.to_dict() for c in r2.draw.cases]
    assert r1.manifest["manifest_sha256"] == r2.manifest["manifest_sha256"]
    # the rebuilt manifest carries the funnel low_value and outside_window
    assert r1.manifest["counters"]["low_value"] == r1.report["funnel"]["low_value"]
    # validate against MANIFEST_SCHEMA
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        pytest.skip("jsonschema not importable on this host")
    Draft202012Validator.check_schema(MANIFEST_SCHEMA)
    Draft202012Validator(MANIFEST_SCHEMA).validate(r1.manifest)


# ----------------------------------------------------------------- T10 rights


def test_rights_allow_and_source_class(tmp_path):
    tape_rows = [
        _row(
            f"r{i}",
            f"Apple stock buyback item {i}",
            f"2026-08-{(i % 28) + 1:02d}T00:00:00+00:00",
        )
        for i in range(5)
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, [])
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, [])
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    result = TD.run_draw(
        str(tape_path),
        str(el_path),
        str(rej_path),
        str(ledger_path),
        seed=20261014,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
        low_value=_low_value(),
    )
    # every candidate's source is the body source class
    for c in result.draw.cases:
        assert c.issuer  # ensures we have resolved cands
    for c in result.draw.cases:
        assert True  # c is a Case, not a Candidate; use the meta
    # The Candidate has source, but Draw.cases is Case. We re-derive from
    # build_candidates meta.
    for meta in result.meta:
        # meta is the per-candidate dict; source is on the Candidate
        pass
    # All candidates have source = BODY_SOURCE_CLASS
    from engine.news_impact.sampler import load_tape

    wide_rows = load_tape(
        str(tape_path),
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
    )
    ledger = load_ledger(str(ledger_path))
    build = TD.build_candidates(
        wide_rows,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
        event_log_rows=[],
        reject_rows=[],
        ledger=ledger,
        low_value=_low_value(),
        dropped={},
        total_rows=len(wide_rows),
    )
    for cand in build.candidates:
        assert cand.source == TD.BODY_SOURCE_CLASS

    # rights_allow: refuses anything except BODY_SOURCE_CLASS
    assert TD._rights_allow(TD.BODY_SOURCE_CLASS) is True
    assert TD._rights_allow("vendor:x") is False
    assert TD._rights_allow("reuters") is False


# ----------------------------------------------------------------- T11 attach_body_accounting


def test_attach_body_accounting_basic(tmp_path):
    # Build a draw to get real cases
    tape_rows = [
        _row(
            f"b{i}",
            f"Apple stock buyback item {i}",
            f"2026-08-{(i % 28) + 1:02d}T00:00:00+00:00",
        )
        for i in range(5)
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, [])
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, [])
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    result = TD.run_draw(
        str(tape_path),
        str(el_path),
        str(rej_path),
        str(ledger_path),
        seed=20261014,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
        low_value=_low_value(),
    )
    # status_map: half available, half unavailable
    status_map = {}
    for i, case in enumerate(result.draw.cases):
        if i % 2 == 0:
            status_map[case.item_id] = "available"
        else:
            status_map[case.item_id] = "body_unavailable:no_8k_match"

    report = dict(result.report)
    snapshot = copy.deepcopy(report)
    status_snapshot = dict(status_map)
    new_report = TD.attach_body_accounting(report, status_map, result.draw.cases)
    assert new_report is not report
    assert "body" in new_report
    assert "body_totals" in new_report
    # every (template, cell) pair present
    for t in TEMPLATES:
        for c in CELLS:
            assert t in new_report["body"]
            assert c in new_report["body"][t]
            assert {"drawn", "available", "body_unavailable", "reasons"} <= set(
                new_report["body"][t][c]
            )
    # input not mutated
    assert report == snapshot
    assert status_map == status_snapshot
    # totals
    assert new_report["body_totals"]["drawn"] == len(result.draw.cases)
    assert (
        new_report["body_totals"]["available"]
        + new_report["body_totals"]["body_unavailable"]
        == len(result.draw.cases)
    )


def test_attach_body_accounting_errors(tmp_path):
    tape_rows = [
        _row(
            f"e{i}",
            f"Apple stock buyback item {i}",
            f"2026-08-{(i % 28) + 1:02d}T00:00:00+00:00",
        )
        for i in range(3)
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, [])
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, [])
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    result = TD.run_draw(
        str(tape_path),
        str(el_path),
        str(rej_path),
        str(ledger_path),
        seed=20261014,
        window_start=date(2026, 7, 1),
        window_end=date(2026, 9, 1),
        low_value=_low_value(),
    )

    # missing item
    bad_map = {case.item_id: "available" for case in result.draw.cases}
    if result.draw.cases:
        bad_map.pop(result.draw.cases[0].item_id)
        with pytest.raises(TD.TapeDrawError, match="missing"):
            TD.attach_body_accounting({}, bad_map, result.draw.cases)

    # extra item
    bad_map2 = {case.item_id: "available" for case in result.draw.cases}
    bad_map2["extra_xxx"] = "available"
    with pytest.raises(TD.TapeDrawError, match="extra"):
        TD.attach_body_accounting({}, bad_map2, result.draw.cases)

    # malformed status
    bad_map3 = {case.item_id: "available" for case in result.draw.cases}
    if result.draw.cases:
        bad_map3[result.draw.cases[0].item_id] = "weird!@#"
        with pytest.raises(TD.TapeDrawError, match="malformed"):
            TD.attach_body_accounting({}, bad_map3, result.draw.cases)


# ----------------------------------------------------------------- T12 source hygiene


def test_no_clock_reads_or_network_in_source():
    text = Path(TD.__file__).read_text()
    forbidden = [
        "datetime.now",
        "utcnow",
        "date.today",
        "time.time(",
        "import requests",
        "urllib",
    ]
    for needle in forbidden:
        assert needle not in text, f"forbidden source fragment: {needle!r}"


# ----------------------------------------------------------------- T13 CLI


def test_cli_writes_files_and_returns_0(tmp_path):
    tape_rows = [
        _row(
            f"c{i}",
            f"Apple stock buyback item {i}",
            f"2026-08-{(i % 28) + 1:02d}T00:00:00+00:00",
        )
        for i in range(5)
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, [])
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, [])
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    out_dir = tmp_path / "out"
    rc = TD.main(
        [
            "--tape",
            str(tape_path),
            "--event-log",
            str(el_path),
            "--reject-sample",
            str(rej_path),
            "--ledger",
            str(ledger_path),
            "--seed",
            "20261014",
            "--out",
            str(out_dir),
        ],
        low_value=_low_value(),
    )
    assert rc == 0
    assert (out_dir / "cases.jsonl").exists()
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "candidates_meta.jsonl").exists()
    assert (out_dir / "draw_report.json").exists()
    # cases.jsonl lines parse
    for line in (out_dir / "cases.jsonl").read_text().splitlines():
        if line.strip():
            obj = json.loads(line)
            assert "item_id" in obj
    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert "manifest_sha256" in manifest


def test_cli_returns_2_on_bad_window(tmp_path):
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, [])
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, [])
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, [])
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    out_dir = tmp_path / "out"
    rc = TD.main(
        [
            "--tape",
            str(tape_path),
            "--event-log",
            str(el_path),
            "--reject-sample",
            str(rej_path),
            "--ledger",
            str(ledger_path),
            "--seed",
            "20261014",
            "--out",
            str(out_dir),
            "--window-start",
            "2026-10-15",
            "--window-end",
            "2026-10-01",
        ],
        low_value=_low_value(),
    )
    assert rc == 2


# ----------------------------------------------------------------- T14 default predicate


def test_default_low_value_uses_news_common(monkeypatch):
    try:
        import engine.news_common  # noqa: F401
    except ImportError:
        pytest.skip("engine.news_common not importable on this host")
    called = {"count": 0}

    def fake_is_low_value(title, domain="", author=""):
        called["count"] += 1
        return False

    monkeypatch.setattr(
        "engine.news_common.is_low_value", fake_is_low_value
    )
    low = TD._make_default_low_value()
    assert low("any title", domain="example.com") is False
    assert called["count"] == 1


# ----------------------------------------------------------------- T15 body-available frame


def _frame_inputs(tmp_path, n=6):
    tape_rows = [
        _row(
            f"f{i}",
            f"Ford stock buyback item {i}",
            f"2026-08-{(i % 28) + 1:02d}T00:00:00+00:00",
            entities="F",
        )
        for i in range(n)
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, [])
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, [])
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(ledger_path)
    return tape_path, el_path, rej_path, ledger_path


def _cli(paths, out_dir, *extra):
    tape_path, el_path, rej_path, ledger_path = paths
    return TD.main(
        [
            "--tape", str(tape_path),
            "--event-log", str(el_path),
            "--reject-sample", str(rej_path),
            "--ledger", str(ledger_path),
            "--seed", "20261014",
            "--out", str(out_dir),
            *extra,
        ],
        low_value=_low_value(),
    )


def test_candidates_out_dumps_full_pool_with_seendate(tmp_path):
    paths = _frame_inputs(tmp_path)
    cand_path = tmp_path / "candidates.jsonl"
    assert _cli(paths, tmp_path / "out", "--candidates-out", str(cand_path)) == 0
    rows = [json.loads(l) for l in cand_path.read_text().splitlines() if l.strip()]
    report = json.loads((tmp_path / "out" / "draw_report.json").read_text())
    assert report["frame"] == {"kind": "full_pool"}
    assert len(rows) >= 1
    assert [r["item_id"] for r in rows] == sorted(r["item_id"] for r in rows)
    for r in rows:
        assert r["seendate"].endswith("Z")
        assert set(r) == {
            "item_id", "issuer", "ticker", "template", "proxy_cell", "seendate",
            "source", "source_sha256", "event_key", "tags", "title",
        }
    drawn = {json.loads(l)["item_id"] for l in (tmp_path / "out" / "cases.jsonl").read_text().splitlines() if l.strip()}
    assert drawn <= {r["item_id"] for r in rows}


def test_body_frame_restricts_draw_and_records_frame(tmp_path):
    paths = _frame_inputs(tmp_path)
    cand_path = tmp_path / "candidates.jsonl"
    assert _cli(paths, tmp_path / "full", "--candidates-out", str(cand_path)) == 0
    ids = [json.loads(l)["item_id"] for l in cand_path.read_text().splitlines() if l.strip()]
    assert len(ids) >= 2
    keep = set(ids[: len(ids) // 2])
    status = {i: ("available" if i in keep else "body_unavailable:no_qualifying_8k") for i in ids}
    sm_path = tmp_path / "status_map.json"
    sm_path.write_text(json.dumps(status, sort_keys=True))
    assert _cli(paths, tmp_path / "framed", "--body-frame", str(sm_path)) == 0
    drawn = {json.loads(l)["item_id"] for l in (tmp_path / "framed" / "cases.jsonl").read_text().splitlines() if l.strip()}
    assert drawn and drawn <= keep
    frame = json.loads((tmp_path / "framed" / "draw_report.json").read_text())["frame"]
    assert frame["kind"] == "body_available"
    assert frame["n_candidates_pre_frame"] == len(ids)
    assert frame["n_candidates_in_frame"] == len(keep)
    assert frame["excluded_reasons"] == {"no_qualifying_8k": len(ids) - len(keep)}
    assert frame["n_status_entries_outside_pool"] == 0
    assert sum(sum(v.values()) for v in frame["frame_cells"].values()) == len(keep)
    import hashlib
    assert frame["status_map_sha256"] == hashlib.sha256(sm_path.read_bytes()).hexdigest()


def test_body_frame_replays_byte_identically(tmp_path):
    paths = _frame_inputs(tmp_path)
    cand_path = tmp_path / "candidates.jsonl"
    assert _cli(paths, tmp_path / "full", "--candidates-out", str(cand_path)) == 0
    ids = [json.loads(l)["item_id"] for l in cand_path.read_text().splitlines() if l.strip()]
    sm_path = tmp_path / "status_map.json"
    sm_path.write_text(json.dumps({i: "available" for i in ids}))
    assert _cli(paths, tmp_path / "a", "--body-frame", str(sm_path)) == 0
    assert _cli(paths, tmp_path / "b", "--body-frame", str(sm_path)) == 0
    for name in ("cases.jsonl", "manifest.json", "draw_report.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    # an all-available frame draws exactly what the unframed draw draws
    assert (tmp_path / "a" / "cases.jsonl").read_bytes() == (tmp_path / "full" / "cases.jsonl").read_bytes()


def test_body_frame_missing_candidate_fails_closed(tmp_path):
    paths = _frame_inputs(tmp_path)
    cand_path = tmp_path / "candidates.jsonl"
    assert _cli(paths, tmp_path / "full", "--candidates-out", str(cand_path)) == 0
    ids = [json.loads(l)["item_id"] for l in cand_path.read_text().splitlines() if l.strip()]
    sm_path = tmp_path / "status_map.json"
    sm_path.write_text(json.dumps({i: "available" for i in ids[1:]} | {"zz-outside": "available"}))
    assert _cli(paths, tmp_path / "framed", "--body-frame", str(sm_path)) == 2


@pytest.mark.parametrize(
    "payload",
    ['{"x": "maybe"}', '{"x": "body_unavailable:"}', "[]", "{}", "not json"],
)
def test_body_frame_malformed_status_map_fails_closed(tmp_path, payload):
    sm_path = tmp_path / "status_map.json"
    sm_path.write_text(payload)
    with pytest.raises(TD.TapeDrawError):
        TD.load_body_frame(str(sm_path))


# ----------------------------------------------------------------- routing gates
# DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES. Every headline, company name and filing
# sentence below is synthetic (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE).

from engine.news_impact import routing_gates as RG

_ZNTX_COVER = (
    "FORM 8-K CURRENT REPORT Date of Report (Date of earliest event reported): "
    "October 1, 2026 ZENTRIX ROBOTICS, INC. (Exact name of registrant as specified "
    "in its charter) "
)
_FORDHAM_COVER = (
    "FORM 8-K CURRENT REPORT Date of Report (Date of earliest event reported): "
    "October 1, 2026 FORDHAM MOTORS COMPANY (Exact name of registrant as specified "
    "in its charter) "
)
_DIVIDEND = "Item 8.01 Other Events. The Board of Directors declared a quarterly cash dividend payable to holders of record."
_SPECIAL = "Item 8.01 Other Events. The Board of Directors declared a special cash dividend payable to holders of record."
_RESIGN = "Item 5.02 Departure of Directors. A director resigned from the Board."
_COLLAB = "Item 1.01 Entry into a Material Definitive Agreement. The Company entered into a strategic collaboration agreement for warehouse automation."
_GUIDE = "Item 7.01 Regulation FD Disclosure. The Company raised its full-year guidance."


def _gdoc(text, items=("8.01",), doc_type="8-K", cover=_ZNTX_COVER):
    return RG.GateDocument(doc_type, tuple(items), cover + text)


def _status(title, template, ticker, docs):
    return RG.classify(title, template, ticker, docs).status()


@pytest.mark.parametrize(
    "title, code",
    [
        ("Industrial Robot Market Size Report 2026-2032", "g1_market_report"),
        ("ZNTX Stock Quote and News", "g1_quote_page"),
        ("SHAREHOLDER ALERT: Investors in Zentrix Robotics urged to contact the firm", "g1_solicitation"),
        ("3 Robotics Stocks to Buy Before Year End", "g1_commentary"),
        ("Zentrix Robotics declares quarterly dividend", None),
    ],
)
def test_g1_non_event_headlines(title, code):
    assert RG.non_event_code(title) == code


def test_g1_precedes_the_issuer_and_body_gates():
    # the quote page names the ticker and the body carries T1 language; G1 still decides
    assert _status("ZNTX Stock Quote and News", "T1", "ZNTX", [_gdoc(_DIVIDEND)]) == "gated_out:g1_quote_page"


def test_issuer_event_with_matching_filing_is_gated_in():
    verdict = RG.classify("Zentrix Robotics declares quarterly dividend", "T1", "ZNTX", [_gdoc(_DIVIDEND)])
    assert verdict.gated_in and verdict.gate is None and verdict.status() == RG.GATED_IN


def test_no_documents_is_no_body_and_bad_inputs_raise():
    verdict = RG.classify("Zentrix Robotics declares quarterly dividend", "T1", "ZNTX", [])
    assert verdict.status() == "gated_out:no_body" and verdict.gate == "G0"
    with pytest.raises(RG.RoutingGateError):
        RG.classify("Zentrix Robotics declares quarterly dividend", "T9", "ZNTX", [_gdoc(_DIVIDEND)])
    for bad in ("", None):
        with pytest.raises(RG.RoutingGateError):
            RG.classify("Zentrix Robotics declares quarterly dividend", "T1", bad, [_gdoc(_DIVIDEND)])


def test_g2_one_letter_ticker_needs_name_or_cashtag():
    docs = [_gdoc(_DIVIDEND, cover=_FORDHAM_COVER)]
    assert _status("Automaker declares quarterly dividend", "T1", "F", docs) == "gated_out:g2_ambiguous_ticker"
    assert _status("F declares quarterly dividend", "T1", "F", docs) == "gated_out:g2_ambiguous_ticker"
    assert _status("Fordham Motors declares quarterly dividend", "T1", "F", docs) == RG.GATED_IN
    assert _status("$F declares quarterly dividend", "T1", "F", docs) == RG.GATED_IN


def test_g2_unnamed_issuer_needs_filing_coverage():
    docs = [_gdoc(_SPECIAL)]
    # 5 of 6 content tokens appear in the filing
    assert _status("Board declares special dividend payable to holders", "T1", "ZNTX", docs) == RG.GATED_IN
    # 2 of 6 content tokens appear in the filing
    assert _status("Board declares special payout amid robot boom", "T1", "ZNTX", docs) == "gated_out:g2_issuer_absent"
    # fully covered, but under COVERAGE_MIN_TOKENS content tokens
    assert RG.headline_coverage("Dividend declared", RG._word_set(_SPECIAL))[0] < RG.COVERAGE_MIN_TOKENS
    assert _status("Dividend declared", "T1", "ZNTX", docs) == "gated_out:g2_issuer_absent"


def test_g2_headline_led_by_another_company_is_not_about_the_issuer():
    title = "Brightwell Systems picks Zentrix Robotics for warehouse partnership"
    assert _status(title, "T3", "ZNTX", [_gdoc(_COLLAB)]) == "gated_out:g2_issuer_not_subject"
    # the lead company appears in the filing: the filing reports the same event
    with_counterparty = _COLLAB.replace("agreement for", "agreement with Brightwell Systems for")
    assert _status(title, "T3", "ZNTX", [_gdoc(with_counterparty)]) == RG.GATED_IN
    # an exempt lead word is never another company
    assert _status("Analysts praise Zentrix Robotics warehouse partnership", "T3", "ZNTX", [_gdoc(_COLLAB)]) == RG.GATED_IN


def test_g2_dateline_prefix_is_stripped_before_the_subject_test():
    title = "Market Wrap: Zentrix Robotics declares quarterly dividend"
    names = RG.registrant_tokens([_gdoc(_DIVIDEND)])
    assert RG.issuer_mention_index(title, "ZNTX", names) == 2  # "Market" would lead unstripped
    assert _status(title, "T1", "ZNTX", [_gdoc(_DIVIDEND)]) == RG.GATED_IN


def test_g3_filing_must_carry_the_template_language():
    assert (
        _status("Zentrix Robotics declares quarterly dividend", "T1", "ZNTX", [_gdoc(_RESIGN, items=("5.02",))])
        == "gated_out:g3_no_family_language"
    )


def test_g3_results_headline_needs_an_item_202_filing():
    title = "Zentrix Robotics beats estimates, raises guidance"
    assert _status(title, "T2", "ZNTX", [_gdoc(_GUIDE, items=("7.01",))]) == "gated_out:g3_results_without_202"
    assert _status(title, "T2", "ZNTX", [_gdoc(_GUIDE, items=("2.02", "9.01"))]) == RG.GATED_IN


@pytest.mark.parametrize(
    "title, ticker, expected",
    [
        ("Shares of $F rise", "F", True),
        ("F declares dividend", "F", False),
        ("Chipmaker (AI) wins order", "AI", True),
        ("AI chip demand lifts orders", "AI", False),
        ("ZNTX declares dividend", "ZNTX", True),
        ("NASDAQ: ZNTX declares dividend", "ZNTX", True),
        ("ZNTXS declares dividend", "ZNTX", False),
        ("zntx declares dividend", "ZNTX", False),
    ],
)
def test_ticker_mention_forms(title, ticker, expected):
    assert RG._ticker_mentioned(title, ticker) is expected


def test_registrant_tokens_read_only_8k_cover_pages():
    other = "OTHERCO HOLDINGS (Exact name of registrant as specified in its charter) "
    assert RG.registrant_tokens([RG.GateDocument("EX-99.1", ("8.01",), other + _DIVIDEND)]) == frozenset()
    assert RG.registrant_tokens([_gdoc(_DIVIDEND)]) == {"zentrix", "robotics"}
    assert RG.registrant_tokens([_gdoc(_DIVIDEND, doc_type="8-k")]) == {"zentrix", "robotics"}


def test_every_gate_code_is_a_valid_gate_status():
    assert RG.STATUS_RE is TD.GATE_STATUS_RE
    assert RG.STATUS_RE.match(RG.GATED_IN)
    for code, gate in RG.CODES.items():
        assert RG.STATUS_RE.match(f"gated_out:{code}"), code
        assert gate in {"G0", "G1", "G2", "G3"}


def _gate_inputs(tmp_path):
    """Synthetic candidates, bodies.jsonl and texts/ in the edgar_body layout."""
    import hashlib

    texts = tmp_path / "texts"
    texts.mkdir()

    def body(item_id, text, items=("8.01",), status="available", doc_status="available"):
        sha = hashlib.sha256(text.encode()).hexdigest()
        (texts / f"{sha}.txt").write_text(text)
        return {
            "item_id": item_id,
            "status": status,
            "filings": [
                {
                    "items": list(items),
                    "documents": [{"status": doc_status, "doc_type": "8-K", "text_sha256": sha}],
                }
            ],
        }

    candidates = [
        {"item_id": "c3", "title": "Zentrix Robotics declares quarterly dividend", "template": "T1", "ticker": "ZNTX"},
        {"item_id": "c1", "title": "Board declares special payout amid robot boom", "template": "T1", "ticker": "ZNTX"},
        {"item_id": "c2", "title": "Zentrix Robotics declares quarterly dividend", "template": "T1", "ticker": None},
        {"item_id": "c4", "title": "Zentrix Robotics declares quarterly dividend", "template": "T1", "ticker": "ZNTX"},
        {"item_id": "c5", "title": "Zentrix Robotics declares quarterly dividend", "template": "T1", "ticker": "ZNTX"},
    ]
    bodies = [
        body("c3", _ZNTX_COVER + _DIVIDEND),
        body("c1", _ZNTX_COVER + _SPECIAL),
        body("c2", _ZNTX_COVER + _DIVIDEND, status="body_unavailable:no_qualifying_8k"),
        body("c4", _ZNTX_COVER + _DIVIDEND, doc_status="fetch_failed"),
        # c5 has no bodies row at all
    ]
    return candidates, bodies, texts


def test_build_gate_map_statuses_and_no_body_paths(tmp_path):
    candidates, bodies, texts = _gate_inputs(tmp_path)
    gate_map = RG.build_gate_map(candidates, {b["item_id"]: b for b in bodies}, texts)
    assert list(gate_map) == ["c1", "c2", "c3", "c4", "c5"]
    assert gate_map == {
        "c1": "gated_out:g2_issuer_absent",
        "c2": "gated_out:no_body",  # unavailable body; the missing ticker is never read
        "c3": "gated_in",
        "c4": "gated_out:no_body",  # no available document
        "c5": "gated_out:no_body",  # no bodies row
    }


def test_build_gate_map_fails_closed(tmp_path):
    candidates, bodies, texts = _gate_inputs(tmp_path)
    by_id = {b["item_id"]: b for b in bodies}
    with pytest.raises(RG.RoutingGateError):
        RG.build_gate_map(candidates + [candidates[0]], by_id, texts)
    for f in texts.iterdir():
        f.unlink()
    with pytest.raises(RG.RoutingGateError):
        RG.build_gate_map(candidates, by_id, texts)


def test_routing_gates_cli_writes_ids_and_codes_only(tmp_path):
    import hashlib

    candidates, bodies, texts = _gate_inputs(tmp_path)
    cand_path = tmp_path / "candidates.jsonl"
    cand_path.write_text("".join(json.dumps(c) + "\n" for c in candidates))
    bodies_path = tmp_path / "bodies.jsonl"
    bodies_path.write_text("".join(json.dumps(b) + "\n" for b in bodies))
    out, report = tmp_path / "gate_map.json", tmp_path / "gate_report.json"
    argv = ["--candidates", str(cand_path), "--bodies", str(bodies_path), "--texts", str(texts),
            "--out", str(out), "--report", str(report)]
    assert RG.main(argv) == 0
    gate_map = json.loads(out.read_text())
    assert set(gate_map) == {c["item_id"] for c in candidates}
    summary = json.loads(report.read_text())
    assert summary["gates_version"] == RG.GATES_VERSION
    assert summary["n_candidates"] == 5 and summary["n_gated_in"] == 1
    assert summary["gate_map_sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert summary["bodies_sha256"] == hashlib.sha256(bodies_path.read_bytes()).hexdigest()
    for path in (out, report):
        blob = path.read_bytes().lower()
        for word in (b"zentrix", b"robotics", b"dividend", b"payout"):
            assert word not in blob
    cand_path.write_text("not json\n")
    assert RG.main(argv) == 2
    cand_path.write_text(json.dumps({"item_id": "c3", "title": "x", "ticker": "ZNTX"}) + "\n")
    assert RG.main(argv) == 2  # an available body with no template is a KeyError, not a verdict


def _gate_frame_setup(tmp_path):
    paths = _frame_inputs(tmp_path)
    cand_path = tmp_path / "candidates.jsonl"
    assert _cli(paths, tmp_path / "full", "--candidates-out", str(cand_path)) == 0
    ids = [json.loads(l)["item_id"] for l in cand_path.read_text().splitlines() if l.strip()]
    assert len(ids) >= 2
    sm_path = tmp_path / "status_map.json"
    sm_path.write_text(json.dumps({i: "available" for i in ids}, sort_keys=True))
    assert _cli(paths, tmp_path / "bodied", "--body-frame", str(sm_path)) == 0
    return paths, ids, sm_path


def test_gate_frame_restricts_draw_and_records_gates(tmp_path):
    import hashlib

    paths, ids, sm_path = _gate_frame_setup(tmp_path)
    keep = set(ids[: len(ids) // 2])
    gm_path = tmp_path / "gate_map.json"
    gm_path.write_text(json.dumps({i: ("gated_in" if i in keep else "gated_out:g2_issuer_absent") for i in ids}))
    assert _cli(paths, tmp_path / "gated", "--body-frame", str(sm_path), "--gate-frame", str(gm_path)) == 0
    drawn = {json.loads(l)["item_id"] for l in (tmp_path / "gated" / "cases.jsonl").read_text().splitlines() if l.strip()}
    assert drawn and drawn <= keep
    report = json.loads((tmp_path / "gated" / "draw_report.json").read_text())
    assert report["frame"]["kind"] == "body_available"
    gate = report["gate_frame"]
    assert gate["kind"] == "routing_gates"
    assert gate["gate_map_sha256"] == hashlib.sha256(gm_path.read_bytes()).hexdigest()
    assert gate["n_gate_entries"] == len(ids)
    assert gate["n_candidates_pre_gate"] == len(ids)
    assert gate["n_candidates_gated_in"] == len(keep)
    assert gate["excluded_codes"] == {"g2_issuer_absent": len(ids) - len(keep)}
    assert sum(sum(v.values()) for v in gate["gated_cells"].values()) == len(keep)
    # without a gate frame the report carries no gate record
    assert "gate_frame" not in json.loads((tmp_path / "bodied" / "draw_report.json").read_text())


def test_gate_frame_all_gated_in_draws_the_body_framed_cases_and_replays(tmp_path):
    paths, ids, sm_path = _gate_frame_setup(tmp_path)
    gm_path = tmp_path / "gate_map.json"
    gm_path.write_text(json.dumps({i: "gated_in" for i in ids}))
    for name in ("a", "b"):
        assert _cli(paths, tmp_path / name, "--body-frame", str(sm_path), "--gate-frame", str(gm_path)) == 0
    for name in ("cases.jsonl", "manifest.json", "draw_report.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    assert (tmp_path / "a" / "cases.jsonl").read_bytes() == (tmp_path / "bodied" / "cases.jsonl").read_bytes()


def test_gate_frame_requires_body_frame(tmp_path, capsys):
    paths, ids, _ = _gate_frame_setup(tmp_path)
    gm_path = tmp_path / "gate_map.json"
    gm_path.write_text(json.dumps({i: "gated_in" for i in ids}))
    capsys.readouterr()
    assert _cli(paths, tmp_path / "gated", "--gate-frame", str(gm_path)) == 2
    assert "requires body_frame" in capsys.readouterr().err


def test_gate_frame_must_cover_the_pool_with_body_consistent_statuses(tmp_path):
    paths, ids, sm_path = _gate_frame_setup(tmp_path)
    gm_path = tmp_path / "gate_map.json"
    gm_path.write_text(json.dumps({i: "gated_in" for i in ids[1:]} | {"zz-outside": "gated_in"}))
    assert _cli(paths, tmp_path / "missing", "--body-frame", str(sm_path), "--gate-frame", str(gm_path)) == 2
    gm_path.write_text(json.dumps({i: "gated_in" for i in ids} | {ids[0]: "gated_out:no_body"}))
    assert _cli(paths, tmp_path / "stale", "--body-frame", str(sm_path), "--gate-frame", str(gm_path)) == 2


@pytest.mark.parametrize(
    "payload",
    ['{"x": "maybe"}', '{"x": "gated_out:"}', '{"x": "gated_out:G2"}', "[]", "{}", "not json"],
)
def test_gate_frame_malformed_map_fails_closed(tmp_path, payload):
    gm_path = tmp_path / "gate_map.json"
    gm_path.write_text(payload)
    with pytest.raises(TD.TapeDrawError):
        TD.load_gate_frame(str(gm_path))


def test_routing_gates_source_has_no_clock_network_or_proxy_cell_read():
    text = Path(RG.__file__).read_text()
    for needle in ("datetime.now", "utcnow", "date.today", "time.time(", "import requests", "urllib",
                   '"proxy_cell"', "'proxy_cell'"):
        assert needle not in text, f"forbidden source fragment: {needle!r}"


# --- routing gates 2 (DEC:NEWS-IMPACT-ROUTING-GATES-1-MISS-PATH item 3) ---------------
# Synthetic headlines and filing text only: no real issuer, no headline from the w2 pool,
# no dollar figure (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE).

from engine.news_impact import routing_gates_2 as RG2


def _status2(title, template, ticker, docs):
    return RG2.classify(title, template, ticker, docs).status()


@pytest.mark.parametrize(
    "title,code",
    [
        ("Nasdaq and S&P 500 edge higher as robot stocks rally", "g1_market_report"),
        ("Stocks, futures slip as investors weigh rate path", "g1_market_report"),
        ("Analyst Opinions on Zentrix Robotics", "g1_quote_page"),
        ("Investors Who Lost Money on Zentrix Robotics Should Contact the Firm", "g1_solicitation"),
        ("Law firm announces investigation on behalf of Zentrix Robotics shareholders", "g1_solicitation"),
    ],
)
def test_gates2_g1_widenings_catch_shapes_gates1_missed(title, code):
    assert RG.non_event_code(title) is None  # the widening, not the gates-1 rule, catches it
    assert RG2.non_event_code(title) == code
    assert _status2(title, "T1", "ZNTX", [_gdoc(_DIVIDEND)]) == f"gated_out:{code}"


@pytest.mark.parametrize(
    "title",
    [
        "Zentrix Robotics declares quarterly dividend",
        "Zentrix Robotics declares special dividend: here's what investors need to know",
    ],
)
def test_gates2_event_headlines_pass_g1(title):
    assert RG2.non_event_code(title) is None
    assert _status2(title, "T1", "ZNTX", [_gdoc(_DIVIDEND)]) == "gated_in"


def test_gates2_keeps_every_gates1_non_event_code():
    for title in (
        "Industrial Robot Market Size Report 2026-2032",
        "ZNTX Stock Quote and News",
        "SHAREHOLDER ALERT: Investors in Zentrix Robotics urged to contact the firm",
        "3 Robotics Stocks to Buy Before Year End",
    ):
        assert RG2.non_event_code(title) == RG.non_event_code(title) is not None


def test_gates2_t1_offering_needs_a_capital_sense():
    title = "Zentrix Robotics expands its service offering for warehouses"
    product = _gdoc("Item 8.01 Other Events. The Company announced a new service offering for warehouse customers.")
    assert _status(title, "T1", "ZNTX", [product]) == "gated_in"  # gates-1 reads the family word only
    assert _status2(title, "T1", "ZNTX", [product]) == "gated_out:g3_template_sense"
    capital = _gdoc(
        "Item 8.01 Other Events. The Company entered into an underwriting agreement for a public offering of common stock."
    )
    assert _status2(title, "T1", "ZNTX", [capital]) == "gated_in"
    assert _status2("Zentrix Robotics prices public offering of common stock", "T1", "ZNTX", [product]) == "gated_in"


def test_gates2_t1_share_sale_reads_a_trading_plan_as_the_event():
    body = _gdoc(
        "Item 8.01 Other Events. The founder adopted a Rule 10b5-1 trading plan for a share sale of company stock."
    )
    assert _status2("Zentrix Robotics founder plans share sale", "T1", "ZNTX", [body]) == "gated_in"


@pytest.mark.parametrize(
    "title",
    [
        "Zentrix Robotics unveils fleet performance for August",
        "Zentrix Robotics launches proxy fight",
        "Zentrix Robotics enters equity distribution agreement",
    ],
)
def test_gates2_t3_template_sense(title):
    docs = [_gdoc(_COLLAB, items=("1.01",))]
    assert _status(title, "T3", "ZNTX", docs) == "gated_in"
    assert _status2(title, "T3", "ZNTX", docs) == "gated_out:g3_template_sense"


def test_gates2_t3_product_launch_is_gated_in():
    docs = [_gdoc("Item 8.01 Other Events. The Company launched a new warehouse robot, now available to customers.")]
    assert _status2("Zentrix Robotics launches new warehouse robot", "T3", "ZNTX", docs) == "gated_in"


def test_gates2_t3_results_only_filing_is_an_event_mismatch():
    title = "Zentrix Robotics launches new warehouse robot"
    docs = [
        _gdoc(
            "Item 2.02 Results of Operations. The Company reported quarterly results and launched a new warehouse robot.",
            items=("2.02", "9.01"),
        )
    ]
    assert _status(title, "T3", "ZNTX", docs) == "gated_in"
    assert _status2(title, "T3", "ZNTX", docs) == "gated_out:g3_event_mismatch"


def test_gates2_body_must_report_the_headline_event():
    title = "Zentrix Robotics announces share buyback"
    docs = [_gdoc(_DIVIDEND)]
    assert _status(title, "T1", "ZNTX", docs) == "gated_in"  # a dividend body carries T1 language
    assert _status2(title, "T1", "ZNTX", docs) == "gated_out:g3_event_mismatch"
    buyback = _gdoc("Item 8.01 Other Events. The Board of Directors authorized a share repurchase program.")
    assert _status2(title, "T1", "ZNTX", [buyback]) == "gated_in"


def test_gates2_t2_guidance_relaxation_needs_item_202():
    title = "Zentrix Robotics lifts outlook"
    furnished = "Item 2.02 Results of Operations. The Company furnished a press release as Exhibit 99.1."
    with_202 = [_gdoc(furnished, items=("2.02",))]
    assert _status(title, "T2", "ZNTX", with_202) == "gated_out:g3_no_family_language"
    assert _status2(title, "T2", "ZNTX", with_202) == "gated_in"
    assert _status2("Zentrix Robotics beats estimates and lifts outlook", "T2", "ZNTX", with_202) == "gated_in"
    regfd = [_gdoc("Item 7.01 Regulation FD Disclosure. The Company furnished a presentation.", items=("7.01",))]
    assert _status2(title, "T2", "ZNTX", regfd) == "gated_out:g3_no_family_language"


def test_gates2_t2_results_headline_still_needs_item_202():
    docs = [_gdoc("Item 1.01 Entry into a Material Definitive Agreement. The Company signed a supply arrangement.", items=("1.01",))]
    title = "Zentrix Robotics beats estimates on warehouse contract"
    assert _status2(title, "T2", "ZNTX", docs) == "gated_out:g3_results_without_202"


def test_gates2_t2_contract_relaxation_needs_item_101():
    title = "Zentrix Robotics wins warehouse contract"
    text = (
        "Item 1.01 Entry into a Material Definitive Agreement. "
        "The Company entered into a supply arrangement with a logistics customer."
    )
    assert _status(title, "T2", "ZNTX", [_gdoc(text, items=("1.01",))]) == "gated_out:g3_no_family_language"
    assert _status2(title, "T2", "ZNTX", [_gdoc(text, items=("1.01",))]) == "gated_in"
    assert _status2(title, "T2", "ZNTX", [_gdoc(text, items=("8.01",))]) == "gated_out:g3_no_family_language"


def test_gates2_keeps_gates1_issuer_guard():
    docs = [_gdoc(_DIVIDEND, cover=_FORDHAM_COVER)]
    assert _status2("Zentrix Robotics declares quarterly dividend", "T1", "ZNTX", docs) == _status(
        "Zentrix Robotics declares quarterly dividend", "T1", "ZNTX", docs
    )
    assert _status2("Zentrix Robotics declares quarterly dividend", "T1", "ZNTX", docs).startswith("gated_out:g2_")


def test_gates2_versions_and_codes_are_separate():
    assert RG.GATES_VERSION == "ni-routing-gates-1"
    assert RG2.GATES_VERSION == "ni-routing-gates-2"
    assert set(RG.CODES) < set(RG2.CODES)
    assert set(RG2.CODES) - set(RG.CODES) == {"g3_template_sense", "g3_event_mismatch"}
    assert all(RG2.CODES[c] == g for c, g in RG.CODES.items())


def test_gates2_every_code_is_a_valid_gate_status():
    assert RG2.STATUS_RE is TD.GATE_STATUS_RE
    assert RG2.STATUS_RE.fullmatch(RG2.GATED_IN)
    for code, gate in RG2.CODES.items():
        assert RG2.STATUS_RE.fullmatch(f"gated_out:{code}")
        assert gate in {"G0", "G1", "G2", "G3"}
        verdict = RG2.GateVerdict(code)
        assert not verdict.gated_in and verdict.gate == gate and verdict.status() == f"gated_out:{code}"
    assert RG2.GateVerdict(None).gated_in and RG2.GateVerdict(None).status() == RG2.GATED_IN


def test_gates2_no_documents_is_no_body_and_bad_inputs_raise():
    assert _status2("Zentrix Robotics declares quarterly dividend", "T1", "ZNTX", []) == "gated_out:no_body"
    with pytest.raises(RG2.RoutingGateError):
        RG2.classify("Zentrix Robotics declares quarterly dividend", "T9", "ZNTX", [_gdoc(_DIVIDEND)])
    for ticker in (None, ""):
        with pytest.raises(RG2.RoutingGateError):
            RG2.classify("Zentrix Robotics declares quarterly dividend", "T1", ticker, [_gdoc(_DIVIDEND)])


def test_gates2_build_gate_map_and_cli_write_ids_and_codes_only(tmp_path):
    import hashlib

    candidates, bodies, texts = _gate_inputs(tmp_path)
    by_id = {b["item_id"]: b for b in bodies}
    assert RG2.build_gate_map(candidates, by_id, texts) == RG.build_gate_map(candidates, by_id, texts)
    with pytest.raises(RG2.RoutingGateError):
        RG2.build_gate_map(candidates + [candidates[0]], by_id, texts)
    cand_path = tmp_path / "candidates.jsonl"
    cand_path.write_text("".join(json.dumps(c) + "\n" for c in candidates))
    bodies_path = tmp_path / "bodies.jsonl"
    bodies_path.write_text("".join(json.dumps(b) + "\n" for b in bodies))
    out, report = tmp_path / "gate_map.json", tmp_path / "gate_report.json"
    argv = ["--candidates", str(cand_path), "--bodies", str(bodies_path), "--texts", str(texts),
            "--out", str(out), "--report", str(report)]
    assert RG2.main(argv) == 0
    summary = json.loads(report.read_text())
    assert summary["gates_version"] == "ni-routing-gates-2"
    assert summary["n_candidates"] == 5 and summary["n_gated_in"] == 1
    assert summary["gate_map_sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert summary["candidates_sha256"] == hashlib.sha256(cand_path.read_bytes()).hexdigest()
    for path in (out, report):
        blob = path.read_bytes().lower()
        for word in (b"zentrix", b"robotics", b"dividend", b"payout"):
            assert word not in blob
    cand_path.write_text("not json\n")
    assert RG2.main(argv) == 2
    cand_path.write_text(json.dumps({"item_id": "c3", "title": "x", "ticker": "ZNTX"}) + "\n")
    assert RG2.main(argv) == 2


def test_gates2_source_has_no_clock_network_or_proxy_cell_read():
    text = Path(RG2.__file__).read_text()
    for needle in ("datetime.now", "utcnow", "date.today", "time.time(", "import requests", "urllib",
                   '"proxy_cell"', "'proxy_cell'"):
        assert needle not in text, f"forbidden source fragment: {needle!r}"


# ----------------------------------------------------------- fallback ledger


def _write_fallback_pair(tmp_path):
    primary = tmp_path / "ledger.json"
    primary.write_text(json.dumps({"note": "p", "tickers": {"F": 37996, "DUP": [111, 222]}}))
    fallback = tmp_path / "fallback.json"
    fallback.write_text(
        json.dumps({"note": "fb", "tickers": {"F": 99999, "DUP": 333, "NEWT": 444, "BRK.B": 1067983}})
    )
    return primary, fallback


def test_fill_only_ledger_keeps_primary_entries_and_refusals(tmp_path):
    primary_path, fallback_path = _write_fallback_pair(tmp_path)
    primary, fallback = load_ledger(str(primary_path)), load_ledger(str(fallback_path))
    combined = TD.fill_only_ledger(primary, fallback)
    assert sorted(combined) == ["BRK-B", "DUP", "F", "NEWT"]
    assert combined["F"] == primary["F"] and combined["DUP"] == primary["DUP"]
    assert combined["NEWT"] == fallback["NEWT"]
    assert combined.has_validity_dates is False
    asof = date(2026, 9, 1)
    assert TD._resolve_entities(["F"], "Ford", asof, combined)[0] == "cik:0000037996"
    assert TD._resolve_entities(["DUP"], "Dup", asof, combined)[0] == "unresolved:ambiguous_ticker"
    assert TD._resolve_entities(["NEWT"], "Newt", asof, combined)[0] == "cik:0000000444"
    assert TD._resolve_entities(["BRK.B"], "Brk", asof, combined)[:2] == ("cik:0001067983", "BRK-B")
    with pytest.raises(TD.TapeDrawError):
        TD.fill_only_ledger({"F": ()}, fallback)
    with pytest.raises(TD.TapeDrawError):
        TD.fill_only_ledger(primary, None)


def _fallback_inputs(tmp_path):
    tickers = ["F", "F", "NEWT", "NEWT", "DUP", "ZZZZ", "BRK.B"]
    tape_rows = [
        _row(
            f"fb{i}",
            f"Company {t.lower()} stock buyback item {i}",
            f"2026-08-{i + 1:02d}T00:00:00+00:00",
            entities=t,
        )
        for i, t in enumerate(tickers)
    ]
    tape_path = tmp_path / "items.parquet"
    _write_tape_parquet(tape_path, tape_rows)
    el_path = tmp_path / "event_log.parquet"
    _write_event_log_parquet(el_path, [])
    rej_path = tmp_path / "reject.parquet"
    _write_reject_parquet(rej_path, [])
    primary, fallback = _write_fallback_pair(tmp_path)
    return (tape_path, el_path, rej_path, primary), fallback


def _jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def test_fallback_ledger_off_leaves_every_output_unchanged(tmp_path):
    paths, _ = _fallback_inputs(tmp_path)
    assert _cli(paths, tmp_path / "a", "--candidates-out", str(tmp_path / "a.jsonl")) == 0
    report = json.loads((tmp_path / "a" / "draw_report.json").read_text())
    assert "fallback_ledger" not in report
    assert "fallback_resolved" not in report["issuers"]
    assert all("issuer_ledger" not in m for m in _jsonl(tmp_path / "a" / "candidates_meta.jsonl"))
    assert _cli(paths, tmp_path / "b", "--candidates-out", str(tmp_path / "b.jsonl")) == 0
    for name in ("cases.jsonl", "manifest.json", "draw_report.json", "candidates_meta.jsonl"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_fallback_ledger_fills_only_rows_the_primary_leaves_unresolved(tmp_path):
    import hashlib

    paths, fallback = _fallback_inputs(tmp_path)
    assert _cli(paths, tmp_path / "off", "--candidates-out", str(tmp_path / "off.jsonl")) == 0
    assert _cli(
        paths, tmp_path / "on", "--candidates-out", str(tmp_path / "on.jsonl"),
        "--fallback-ledger", str(fallback),
    ) == 0
    off = {r["item_id"]: r for r in _jsonl(tmp_path / "off.jsonl")}
    on = {r["item_id"]: r for r in _jsonl(tmp_path / "on.jsonl")}
    assert set(off) == set(on) and len(on) == 7

    # rows the primary resolves keep their issuer and ticker exactly
    for item_id, row in off.items():
        if not row["issuer"].startswith("unresolved:"):
            assert on[item_id]["issuer"] == row["issuer"]
            assert on[item_id]["ticker"] == row["ticker"]
            assert on[item_id]["tags"] == row["tags"]

    by_ticker = {}
    for i, t in enumerate(["F", "F", "NEWT", "NEWT", "DUP", "ZZZZ", "BRK.B"]):
        by_ticker.setdefault(t, []).append(f"fb{i}")
    for i in by_ticker["NEWT"]:
        assert off[i]["issuer"] == "unresolved:unknown_ticker"
        assert on[i]["issuer"] == "cik:0000000444"
    assert on[by_ticker["BRK.B"][0]]["issuer"] == "cik:0001067983"
    # a primary refusal stands: the fallback never overrides an ambiguous primary key
    assert on[by_ticker["DUP"][0]]["issuer"] == "unresolved:ambiguous_ticker"
    assert on[by_ticker["ZZZZ"][0]]["issuer"] == "unresolved:unknown_ticker"

    r_off = json.loads((tmp_path / "off" / "draw_report.json").read_text())
    r_on = json.loads((tmp_path / "on" / "draw_report.json").read_text())
    assert r_on["issuers"]["fallback_resolved"] == 3
    assert r_on["issuers"]["resolved"] == r_off["issuers"]["resolved"] + 3
    assert r_on["issuers"]["unresolved"] == r_off["issuers"]["unresolved"] - 3
    assert r_on["issuers"]["unresolved_by_reason"]["ambiguous_ticker"] == 1
    assert r_on["fallback_ledger"] == {
        "tickers": 4,
        "fill_only_tickers": 2,
        "primary_tickers": 2,
        "sha256": hashlib.sha256(fallback.read_bytes()).hexdigest(),
    }
    ledgers = {m["item_id"]: m["issuer_ledger"] for m in _jsonl(tmp_path / "on" / "candidates_meta.jsonl")}
    for i in by_ticker["F"]:
        assert ledgers[i] == "primary"
    for i in by_ticker["NEWT"] + by_ticker["BRK.B"]:
        assert ledgers[i] == "fallback"
    for i in by_ticker["DUP"] + by_ticker["ZZZZ"]:
        assert ledgers[i] is None

    # the on run replays byte-identically, from a byte-copy of the fallback ledger at
    # another path: inputs are recorded by sha256, never by path
    moved = tmp_path / "elsewhere" / "fb_copy.json"
    moved.parent.mkdir()
    moved.write_bytes(fallback.read_bytes())
    assert _cli(paths, tmp_path / "on2", "--fallback-ledger", str(moved)) == 0
    for name in ("cases.jsonl", "manifest.json", "draw_report.json", "candidates_meta.jsonl"):
        assert (tmp_path / "on" / name).read_bytes() == (tmp_path / "on2" / name).read_bytes()


def test_fallback_ledger_malformed_file_fails_before_any_output(tmp_path):
    from engine.news_impact.issuer import LedgerError

    paths, fallback = _fallback_inputs(tmp_path)
    fallback.write_text('{"note": "no tickers"}')
    with pytest.raises(LedgerError):
        _cli(paths, tmp_path / "out", "--fallback-ledger", str(fallback))
    assert not (tmp_path / "out" / "cases.jsonl").exists()
