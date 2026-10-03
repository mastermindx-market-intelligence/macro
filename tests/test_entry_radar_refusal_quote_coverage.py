"""Refusal health must report how many quotes were loaded, not a fixed zero."""
from __future__ import annotations

from datetime import date, datetime, timezone

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
