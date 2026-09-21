"""Token-bucket pacing (trickle._refill_tokens) — spread the daily rolling-cap
budget smoothly across the day instead of bursting it in minutes (which would
exhaust the 24h window and starve later-arriving new posts, e.g. the 17-19 ET
US-close bump). Pure function; no network."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from marketdesk_extractor import trickle

NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)
RATE = 70 / 86400.0  # cap/24h => ~1 token per ~1234s (~20.5 min)


def test_fresh_account_starts_with_a_full_bucket():
    # last_refill=None -> a just-opened account may catch an initial burst
    assert trickle._refill_tokens(0.0, None, NOW, burst=10, refill_per_sec=RATE) == 10.0


def test_no_elapsed_time_no_refill():
    assert trickle._refill_tokens(3.0, NOW, NOW, burst=10, refill_per_sec=RATE) == 3.0


def test_accrues_one_token_per_pace_interval():
    later = NOW + timedelta(seconds=1234)  # ~cap/24h interval
    got = trickle._refill_tokens(0.0, NOW, later, burst=10, refill_per_sec=RATE)
    assert 0.99 <= got <= 1.01


def test_never_exceeds_burst_capacity():
    later = NOW + timedelta(hours=48)  # far more than enough to overflow
    assert trickle._refill_tokens(5.0, NOW, later, burst=10, refill_per_sec=RATE) == 10.0


def test_partial_accrual_adds_to_existing():
    later = NOW + timedelta(seconds=617)  # ~half an interval
    got = trickle._refill_tokens(2.0, NOW, later, burst=10, refill_per_sec=RATE)
    assert 2.4 <= got <= 2.6  # 2.0 + ~0.5
