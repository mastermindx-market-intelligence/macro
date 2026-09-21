"""China freshness contracts: one binding core check + advisory Tushare checks.

Two planes share this module because both are calendar-anchored China freshness
questions, but their authority differs:

* ``check_china_search_core`` is BINDING for ``scripts.collect --group asia``.
  ``data/china_search/closes.parquet`` feeds the China basket library and
  Mastermind AI regional grounding, so a store behind the latest COMPLETED
  mainland session must stop publication before mixed-vintage artifacts ship.
* ``run`` is the older ADVISORY Tushare-flow tripwire. The token-gated flow
  stores are useful context but not a required publication plane, so a cold feed
  emits a warning and the lane continues.

WHY THE ADVISORY EXISTS. ``collectors/tushare_client.py`` returns ``None`` — never
raises — for no token, endpoint error, access denied, exhausted credits, or an
empty response. Its callers omit the leg rather than fabricate a zero, and the
multi-source collector normally degrades per source. Those individually-correct
decisions let ``flow_hist.parquet`` and ``moneyflow.parquet`` freeze at
2026-07-24 while pages kept rendering them through 2026-08-06.

Both checks are anchored to an exchange clock rather than to the store itself: a
frozen store is perfectly self-consistent. The required broad close plane uses
``lib.cn_calendar`` exactly. The legacy Tushare flow check retains its historical
HKEX proxy and three-session advisory budget; HKEX differs from mainland Golden
Week, but an occasional warning is cheaper than another silent multiweek freeze.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from lib import cn_calendar, config, hk_calendar  # noqa: E402

# The token-gated stores, and the collector that fills each — named so the
# annotation tells the operator which leg to look at, not just "something is old".
STORES: tuple[tuple[str, str], ...] = (
    ("tushare/flow_hist.parquet", "tushare_moneyflow / tushare_history"),
    ("tushare/moneyflow.parquet", "tushare_moneyflow"),
)

# Sessions behind the expected last close before we say anything. 3 absorbs a
# long weekend plus one public holiday and the collector's own once-a-day cadence
# (asia-close gates every slot after the day's first real run to a no-op), so a
# healthy plane never trips it.
MAX_SESSIONS_BEHIND = 3


def _latest_date(rel: str) -> str | None:
    """Newest trade date in a store, or None when it is absent/unreadable/empty."""
    p = config.data_dir() / rel
    if not p.exists():
        return None
    try:
        import pandas as pd

        df = pd.read_parquet(p)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    for col in ("date", "trade_date", "asof", "as_of", "dt"):
        if col in df.columns:
            stamp = pd.to_datetime(df[col].astype(str), errors="coerce").max()
            if stamp is None or pd.isna(stamp):
                return None
            if getattr(stamp, "tzinfo", None) is not None:
                stamp = stamp.tz_localize(None)
            return stamp.date().isoformat()

    # Wide price panels (including china_search/closes.parquet) carry sessions
    # on the index rather than in a date column. A numeric RangeIndex is not a
    # session axis; pandas would otherwise coerce it to meaningless 1970 epochs.
    if isinstance(df.index, pd.RangeIndex):
        return None
    # Drop the timezone LABEL without
    # converting the instant: an Asia/Shanghai midnight is still that local
    # session date, not the prior UTC date.
    idx = pd.to_datetime(df.index, errors="coerce")
    idx = idx[~pd.isna(idx)]
    if len(idx) == 0:
        return None
    stamp = idx.max()
    if getattr(stamp, "tzinfo", None) is not None:
        stamp = stamp.tz_localize(None)
    return stamp.date().isoformat()


def sessions_between(newest: str, expected: date) -> int:
    """HKEX sessions strictly after `newest` up to and including `expected`."""
    try:
        d = datetime.strptime(newest, "%Y-%m-%d").date()
    except ValueError:
        return 10_000
    n = 0
    while d < expected and n < 10_000:
        d += timedelta(days=1)
        if hk_calendar.is_session(d):
            n += 1
    return n


def evaluate(newest: str | None, expected: date) -> tuple[str, int]:
    """('fresh'|'stale'|'absent', sessions_behind)."""
    if newest is None:
        return "absent", -1
    behind = sessions_between(newest, expected)
    return ("stale" if behind > MAX_SESSIONS_BEHIND else "fresh"), behind


CHINA_SEARCH_STORE = "china_search/closes.parquet"


def check_china_search_core(now: datetime | None = None) -> int:
    """Binding health check for the broad A-share close plane.

    Unlike the token-gated Tushare flow stores below, this store is a required
    input to the China basket library and Mastermind AI's regional grounding.
    ``scripts.collect --group asia`` calls this only after every adapter and
    post-collect task has had its turn, then returns this non-zero result before
    the workflow can commit or build mixed-vintage China artifacts.

    Returns 0 when current (or explicitly ahead of the completed-session clock)
    and 3 when absent, unreadable, or missing one or more completed sessions.
    """
    if now is not None:
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        else:
            now = now.astimezone(timezone.utc)
    expected = cn_calendar.expected_last_session(now)
    newest = _latest_date(CHINA_SEARCH_STORE)
    if newest is None:
        print(
            "::error title=China core price store absent::"
            f"{CHINA_SEARCH_STORE} has no readable session; expected mainland "
            f"session {expected}. The china_universe close plane is required "
            "before downstream China builders may publish.",
            flush=True,
        )
        return 3
    try:
        latest = datetime.strptime(newest, "%Y-%m-%d").date()
    except ValueError:
        print(
            "::error title=China core price store unreadable::"
            f"{CHINA_SEARCH_STORE} latest date {newest!r} is not ISO-8601; "
            f"expected mainland session {expected}.",
            flush=True,
        )
        return 3
    if latest > expected:
        print(
            "::warning title=China core price store ahead of exchange clock::"
            f"store={latest}; latest completed mainland session={expected}. "
            "Proceeding because a newer store cannot represent missing completed sessions; "
            "inspect the producer clock if this persists.",
            flush=True,
        )
        return 0
    behind = cn_calendar.sessions_between(latest, expected)
    if behind > 0:
        print(
            "::error title=China core price store stale::"
            f"store={latest}; expected mainland session {expected}; "
            f"{behind} session{'s' if behind != 1 else ''} behind; "
            "filled by china_universe. Refusing mixed-vintage China publication.",
            flush=True,
        )
        return 3
    print(
        f"china_search core freshness OK: {CHINA_SEARCH_STORE} at {latest} "
        f"(expected mainland session {expected})",
        flush=True,
    )
    return 0


def run(now: datetime | None = None) -> int:
    expected = hk_calendar.expected_last_session(now)
    bad: list[str] = []
    for rel, owner in STORES:
        newest = _latest_date(rel)
        status, behind = evaluate(newest, expected)
        if status == "fresh":
            print(f"tushare freshness OK: {rel} at {newest} ({behind} session(s) behind {expected})")
            continue
        bad.append(
            f"{rel} at {newest or 'ABSENT'} — {'no readable rows' if behind < 0 else str(behind) + ' sessions'} "
            f"behind expected {expected} (filled by {owner})"
        )
    if not bad:
        return 0
    # Bare print, line-start, flushed: a logger would prefix the line and GitHub
    # would silently drop the annotation (tests/test_gh_annotation_line_start.py).
    print(
        "::warning title=tushare plane cold::"
        + "; ".join(bad)
        + ". The Tushare client returns None and never raises, so the collect step stays green "
        "and pages keep rendering the old as-of date. Check TUSHARE_TOKEN is set and the "
        "membership/积分 tier still covers moneyflow_dc (5000积分).",
        flush=True,
    )
    return 0  # advisory: never red the collection lane over one gated source


def selftest() -> int:
    exp = date(2026, 8, 6)  # a Thursday, HKEX session
    checks = [
        (evaluate(None, exp)[0] == "absent", "a missing store must read absent"),
        (evaluate("2026-08-05", exp)[0] == "fresh", "yesterday must be fresh"),
        (evaluate("2026-07-24", exp)[0] == "stale", "the 2026-07-24 freeze must be stale"),
        # The bug this guard exists for: a self-relative check would call a frozen
        # store fresh because it equals its own newest row. Anchoring to the
        # calendar is what makes the 13-day gap visible.
        (sessions_between("2026-07-24", exp) > MAX_SESSIONS_BEHIND,
         "the real incident must exceed the threshold"),
        (sessions_between("2026-08-06", exp) == 0, "same day is zero sessions behind"),
        (evaluate("not-a-date", exp)[0] == "stale", "an unparseable date must not read fresh"),
    ]
    bad = [m for ok, m in checks if not ok]
    for m in bad:
        print(f"selftest FAIL: {m}")
    print("check_tushare_freshness selftest: " + ("OK" if not bad else f"{len(bad)} failure(s)"))
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true", help="run calendar/threshold pins and exit")
    a = ap.parse_args(argv)
    return selftest() if a.selftest else run()


if __name__ == "__main__":
    raise SystemExit(main())
