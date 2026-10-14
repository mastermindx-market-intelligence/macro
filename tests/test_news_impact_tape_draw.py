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
