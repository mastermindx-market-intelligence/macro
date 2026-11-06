"""Refusal health must report how many quotes were loaded, not a fixed zero."""
from __future__ import annotations

import ast
from datetime import date, datetime, timezone
from pathlib import Path

from engine.entry_radar import live_eval as le

NOW = datetime(2026, 8, 14, 14, 30, tzinfo=timezone.utc)
PROBE = tuple(f"T{i:02d}" for i in range(12))


def _refusal(quotes_meta):
    _, health = le._refusal_payload(
        state="refused",
        reasons=("synthetic",),
        now=NOW,
        session=date(2026, 8, 14),
        pack=None,
        tickers=PROBE,
        state_dir=None,
        config=le.LiveEvalConfig(),
        quotes_meta=quotes_meta,
        ledger=None,
    )
    return health


def test_refusal_reports_loaded_quotes():
    book = {t: {"last": 1.0} for t in PROBE[:10]}
    health = _refusal({"asof": "2026-08-14T14:29:00Z", "quotes": book})
    assert health["inputs"]["quotes"]["coverage"] == "10/12"


def test_refusal_without_quotes_reports_zero():
    assert _refusal(None)["inputs"]["quotes"]["coverage"] == "0/12"
    assert _refusal({"asof": "2026-08-14T14:29:00Z"})["inputs"]["quotes"]["coverage"] == "0/12"


def test_loaded_quote_count_never_raises():
    assert le._loaded_quote_count([], PROBE) == 0
    assert le._loaded_quote_count("bad", PROBE) == 0


def test_loaded_quote_count_ignores_empty_rows():
    book = {"T00": {"last": 1.0}, "T01": None, "T02": 5}
    assert le._loaded_quote_count({"quotes": book}, PROBE[:3]) == 1


def test_failure_payload_reports_loaded_quotes():
    book = {t: {"last": 1.0} for t in PROBE[:2]}
    _, health = le.failure_payload(
        now=NOW,
        pack=None,
        tickers=PROBE[:3],
        quotes={"asof": "2026-08-14T14:29:00Z", "quotes": book},
        error=RuntimeError("boom"),
    )
    assert health["inputs"]["quotes"]["coverage"] == "2/3"


def test_entrypoint_passes_quotes_to_the_failed_receipt():
    src = ast.parse(
        (Path(__file__).resolve().parents[1] / "scripts/entry_radar_live.py").read_text(
            encoding="utf-8"
        )
    )
    calls = [
        node
        for node in ast.walk(src)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "failure_payload"
    ]
    assert calls
    for call in calls:
        kw = {k.arg for k in call.keywords if k.arg}
        assert "quotes" in kw
