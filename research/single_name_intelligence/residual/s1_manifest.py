"""s1_manifest.py — outcome-free rolling-anchor membership manifests (SL §5, D4, D5).

The builder reads ONLY market calendars and the subjects' index dates. It never
opens a price/volume column: D5 seals membership before any outcome exists, and
a test spies on the loader to enforce that.

Split vocabulary (D2, D5): TRAIN | TUNE | QUARANTINE | PURGED_TRAIN |
PURGED_TUNE | ABSTAIN_RESOLVER_NONE | ABSTAIN_FILL_MISMATCH.

Row schema (one canonical JSONL per (protocol, subject, h), sorted by
(horizon, episode_key)):
  {protocol_id, version, horizon, episode_key, issuer_key, counter,
   security_id, unit, anchor_session_date, coverage_date, split}
"""
from __future__ import annotations

import hashlib
import json
from bisect import bisect_right
from datetime import date, timedelta

from engine.qledger import (MARKET_HK, MARKET_US, resolve_horizon_window)

# SL §2 split boundaries (immutable; A23).
TRAIN_END = date(2024, 1, 1)    # TRAIN: s <  2024-01-01
TUNE_END = date(2026, 10, 1)    # TUNE:  2024-01-01 <= s < 2026-10-01; QUARANTINE: s >= TUNE_END

MIN_HISTORY_BARS = 252          # D4: first anchor needs 252 subject bars <= D(s)

SPLIT_VOCAB = ("TRAIN", "TUNE", "QUARANTINE", "PURGED_TRAIN", "PURGED_TUNE",
               "ABSTAIN_RESOLVER_NONE", "ABSTAIN_FILL_MISMATCH")

# Bounded session walk: mirrors engine.qledger._MAX_CLOSED_STRETCH_DAYS so a
# broken calendar fails closed instead of spinning.
_MAX_WALK_DAYS = 3 * 400 + 60


def episode_key_for(issuer_key: str, anchor: date, counter: str) -> str:
    """sha256 of `issuer_key|rolling_anchor|<s iso>|<counter>` (SL §1 non-event key)."""
    raw = f"{issuer_key}|rolling_anchor|{anchor.isoformat()}|{counter}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_session_fn(market: str):
    from engine.qledger import CLOCK_CALENDARS
    cal = CLOCK_CALENDARS[market]
    if market not in (MARKET_US, MARKET_HK):
        raise ValueError(f"lane supports MARKET_US/MARKET_HK only, got {market!r}")
    return cal.is_session


def last_session_before(is_session, d: date) -> date:
    """D(s): the last session STRICTLY before d on the same calendar."""
    c = d - timedelta(days=1)
    for _ in range(_MAX_WALK_DAYS):
        if is_session(c):
            return c
        c -= timedelta(days=1)
    raise RuntimeError(f"no session found before {d} within the walk bound")


def session_n_back(is_session, d: date, n: int) -> date:
    """The session exactly n sessions before session d (d itself not counted)."""
    c = d
    seen = 0
    for _ in range(_MAX_WALK_DAYS):
        c -= timedelta(days=1)
        if is_session(c):
            seen += 1
            if seen == n:
                return c
    raise RuntimeError(f"cannot reach {n} sessions back from {d}")


def session_n_forward(is_session, d: date, n: int) -> date | None:
    """The session exactly n sessions after session d (d not counted); None if
    unreachable inside the walk bound. Mirrors the qledger rule that the walk is
    bounded rather than open-ended so a broken calendar fails closed."""
    if not is_session(d):
        return None
    c = d
    seen = 0
    for _ in range(_MAX_WALK_DAYS):
        c += timedelta(days=1)
        if is_session(c):
            seen += 1
            if seen == n:
                return c
    return None


def first_session_strictly_after(is_session, d: date) -> date | None:
    return session_n_forward_on_non_session(is_session, d, 1)


def session_n_forward_on_non_session(is_session, d: date, n: int) -> date | None:
    """First session >= n sessions after `d` where d may be a non-session."""
    c = d
    seen = 0
    for _ in range(_MAX_WALK_DAYS):
        c += timedelta(days=1)
        if is_session(c):
            seen += 1
            if seen == n:
                return c
    return None


def first_anchor(is_session, subject_dates: list[date], cal_floor: date) -> date | None:
    """D4: the first session s on the subject's calendar with >= 252 subject
    bars on or before D(s). The scan starts at the 252nd subject bar — NOT at
    the clock's support floor — so anchors the resolver cannot reach (e.g. HK
    pre-2014) enter the grid and are listed as ABSTAIN_RESOLVER_NONE rather
    than silently skipped."""
    if len(subject_dates) < MIN_HISTORY_BARS:
        return None
    b252 = subject_dates[MIN_HISTORY_BARS - 1]          # the 252nd bar
    s = b252 + timedelta(days=1)
    for _ in range(_MAX_WALK_DAYS):
        if is_session(s):
            d_s = last_session_before(is_session, s)
            n = bisect_right(subject_dates, d_s)
            if n >= MIN_HISTORY_BARS:
                return s
        s += timedelta(days=1)
    return None


def time_split(s: date) -> str:
    """SL §2 time-axis label for an anchor session (before the purge flag)."""
    if s < TRAIN_END:
        return "TRAIN"
    if s < TUNE_END:
        return "TUNE"
    return "QUARANTINE"


def label_unit(s: date, coverage: date | None) -> str:
    """D2: time split, then the per-h purge (purge keeps the unit visible and
    never moves it to another split)."""
    base = time_split(s)
    if base == "TRAIN" and coverage is not None and coverage >= TRAIN_END:
        return "PURGED_TRAIN"
    if base == "TUNE" and coverage is not None and coverage >= TUNE_END:
        return "PURGED_TUNE"
    return base


def rolling_grid(is_session, subject_dates: list[date], h: int, cal_floor: date,
                 last_bar: date) -> list[date]:
    """D4 greedy non-overlapping grid: first anchor, then one anchor every
    h+1 sessions, capped at the subject's last input bar."""
    s = first_anchor(is_session, subject_dates, cal_floor)
    if s is None or s > last_bar:
        return []
    out = [s]
    step = h + 1
    while True:
        nxt = session_n_forward(is_session, s, step)
        if nxt is None or nxt > last_bar:
            return out
        out.append(nxt)
        s = nxt


def build_rows(protocol_id: str, issuer_key: str, counter: str, security_id: str,
               market: str, h: int, subject_dates: list[date],
               last_bar: date) -> list[dict]:
    """One manifest's rows (outcome-free): resolve, split, purge, abstain."""
    from engine.qledger import CLOCK_MARKET_SUPPORT
    is_session = is_session_fn(market)
    cal_floor = CLOCK_MARKET_SUPPORT[market][0]
    rows: list[dict] = []
    for s in rolling_grid(is_session, subject_dates, h, cal_floor, last_bar):
        w = resolve_horizon_window(s - timedelta(days=1), h, "trading_days", market)
        if w is None:
            split, coverage = "ABSTAIN_RESOLVER_NONE", None
        elif w.fill_date != s:
            split, coverage = "ABSTAIN_FILL_MISMATCH", w.coverage_date
        else:
            split, coverage = label_unit(s, w.coverage_date), w.coverage_date
        rows.append({
            "protocol_id": protocol_id,
            "version": "v1",
            "horizon": h,
            "episode_key": episode_key_for(issuer_key, s, counter),
            "issuer_key": issuer_key,
            "counter": counter,
            "security_id": security_id,
            "unit": "rolling_anchor",
            "anchor_session_date": s.isoformat(),
            "coverage_date": coverage.isoformat() if coverage is not None else None,
            "split": split,
        })
    return rows


def canonical_line(row: dict) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def manifest_bytes(rows: list[dict]) -> bytes:
    """Rows sorted by (horizon, episode_key), canonical JSONL (D5)."""
    ordered = sorted(rows, key=lambda r: (r["horizon"], r["episode_key"]))
    return "".join(canonical_line(r) for r in ordered).encode("utf-8")


def split_digests(rows: list[dict]) -> dict[str, dict]:
    """membership_sha256 per split = sha256 of that split's lines, in the
    manifest's canonical order (D5)."""
    ordered = sorted(rows, key=lambda r: (r["horizon"], r["episode_key"]))
    by_split: dict[str, list[str]] = {}
    for r in ordered:
        by_split.setdefault(r["split"], []).append(canonical_line(r))
    return {sp: {"count": len(lines),
                 "membership_sha256": hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()}
            for sp, lines in sorted(by_split.items())}
