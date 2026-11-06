"""Adversarial property tests for SNI S2 event-response modules.

Pins leakage-critical invariants claimed by s2_clocklaw, s2_splits, s2_collapse
and s2_selection (docstrings + IL/SL companions). Synthetic fixtures only;
identity keys are opaque caller-supplied strings. Descriptive research pins:
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay false and are never set here.
"""
from __future__ import annotations

import json
import random
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from s2_clocklaw import (  # noqa: E402
    CLOCK_CALENDARS,
    MARKET_HK,
    MARKET_US,
    first_session_after,
    first_session_after_disclosure_date,
    session_dates,
    session_part,
    to_utc,
)
from s2_collapse import (  # noqa: E402
    Episode,
    EventRecord,
    run_collapse,
    step1_counter_collapse,
    step2_dedup,
)
from s2_seal import CLASSIFICATION_TABLE, GRADE_HORIZONS  # noqa: E402
from s2_selection import classify_category, split_tokens  # noqa: E402
from s2_splits import (  # noqa: E402
    build_membership,
    canonical_line,
    episode_key,
    purge_flag,
    split_label,
    window_last_session,
)

N_CASES = 60
UTC = timezone.utc
_REGULAR_OPEN = time(9, 30)
_SESSION_END = time(16, 0)
_HK_BREAK = (time(12, 0), time(13, 0))
_TZ = {MARKET_US: ZoneInfo("America/New_York"), MARKET_HK: ZoneInfo("Asia/Hong_Kong")}
_SESSION_PARTS = ("pre_open", "in_session", "midday_break", "after_close")
# s2_splits docstring (SL §2): TRAIN s < 2024-01-01; TUNE until 2026-10-01; else QUARANTINE.
_TUNE_START = date(2024, 1, 1)
_QUARANTINE_START = date(2026, 10, 1)
_DOC_FAMILIES = {"results", "capital_action", "regulatory_material", "UNCLASSIFIED"}
_ADMISSIBLE = ("CRAWL_BOUNDED", "PUBLISHER_STATED", "DISCLOSURE_DATE")
_FAMILIES = ("results", "capital_action", "regulatory_material")
_ISSUERS = ("alibaba", "tencent", "issuer-x")

_US_SESSIONS = session_dates(CLOCK_CALENDARS[MARKET_US])
_HK_SESSIONS = session_dates(CLOCK_CALENDARS[MARKET_HK])
_US_SESSION_DATES = [date.fromisoformat(s) for s in _US_SESSIONS]
_SAFE_US = [d for d in _US_SESSION_DATES if date(2020, 1, 2) <= d <= date(2026, 6, 30)]
_SAFE_US_ISO = [d.isoformat() for d in _SAFE_US]
_SAFE_HK_ISO = [
    s for s in _HK_SESSIONS
    if date(2020, 1, 2) <= date.fromisoformat(s) <= date(2026, 6, 30)
]


def _open_utc(session: date, market: str) -> datetime:
    local = datetime(session.year, session.month, session.day, 9, 30, tzinfo=_TZ[market])
    return local.astimezone(UTC)


def _prev_session(session: date, market: str) -> date | None:
    cal = CLOCK_CALENDARS[market]
    d = session - timedelta(days=1)
    floor = date(2019, 1, 1)
    while d >= floor:
        if cal.is_session(d):
            return d
        d -= timedelta(days=1)
    return None


def _rand_utc(rng: random.Random, start: datetime, span_seconds: int) -> datetime:
    return start + timedelta(seconds=rng.randint(0, span_seconds),
                             microseconds=rng.randint(0, 999999))


def _hth_session_after(s: date, h: int, cal) -> date:
    """Last session of s..s+h inclusive when s is itself a session and h >= 1."""
    n = 0
    d = s
    while n < h:
        d += timedelta(days=1)
        if cal.is_session(d):
            n += 1
    return d


def _event_sig(e: EventRecord) -> tuple:
    return (e.issuer_key, e.family, e.t_avail_utc, e.evidence_pointer,
            e.s_us, e.s_hk, tuple(e.member_ids), e.programme,
            tuple(e.member_families))


def _episode_sig(ep: Episode) -> tuple:
    return (_event_sig(ep.opener), ep.horizon,
            tuple(_event_sig(a) for a in ep.absorbed))


def _synth_row(rng: random.Random, i: int, **kw) -> dict:
    issuer = kw.get("issuer_key", rng.choice(_ISSUERS))
    family = kw.get("family", rng.choice(_FAMILIES))
    t = kw.get("t_avail_utc")
    if t is None:
        t = (datetime(2022, 6, 1, tzinfo=UTC) + timedelta(hours=rng.randint(0, 8000))).isoformat()
    quality = kw.get("t_avail_quality", rng.choice(
        _ADMISSIBLE + ("EVENT_DATE", "SNAPSHOT_DATE", "CORRUPTED")))
    disp = kw.get("disposition", "SELECTED")
    reason = kw.get("listed_exclusion_reason")
    if disp == "EXCLUDED_AND_LISTED" and reason is None:
        reason = "synthetic_named_exclusion"
    return {
        "id": kw.get("id", f"syn-{i}"),
        "issuer_key": issuer,
        "family": family,
        "t_avail_utc": t,
        "t_avail_quality": quality,
        "s_us": kw.get("s_us", rng.choice(_SAFE_US_ISO)),
        "s_hk": kw.get("s_hk", rng.choice(_SAFE_HK_ISO)),
        "evidence_pointer": kw.get("evidence_pointer", f"synthetic#{i}"),
        "disposition": disp,
        "listed_exclusion_reason": reason,
    }


def _dummy_episode(i: int, s_us: str, s_hk: str, issuer: str = "alibaba",
                   family: str = "results", extra_family: str | None = None) -> Episode:
    fams = [family] if extra_family is None else [family, extra_family]
    rec = EventRecord(
        issuer_key=issuer,
        family=family,
        t_avail_utc=f"2023-06-15T{i % 10:02d}:00:00+00:00",
        evidence_pointer=f"synthetic#ep{i}",
        s_us=s_us,
        s_hk=s_hk,
        member_ids=[f"syn-m{i}"],
        member_families=fams,
    )
    return Episode(opener=rec, horizon=5)


# ---------------------------------------------------------------------------
# 1. clock law no-look-ahead
# ---------------------------------------------------------------------------

def test_first_session_after_no_lookahead_calendar_member_monotone() -> None:
    """s(c) is the first session whose regular open is strictly after t_avail.

    Same-day only when that day is a session and local time is strictly before
    09:30; otherwise the next session. Result is on the market calendar and
    monotone non-decreasing in t.
    """
    rng = random.Random(101)
    start = datetime(2020, 2, 1, tzinfo=UTC)
    span = int(6.2 * 365 * 24 * 3600)
    for market in (MARKET_US, MARKET_HK):
        cal = CLOCK_CALENDARS[market]
        stamps: list[tuple[datetime, date]] = []
        for _ in range(N_CASES):
            t = _rand_utc(rng, start, span)
            s = first_session_after(t, market)
            assert cal.is_session(s)
            open_s = _open_utc(s, market)
            assert open_s > t
            prev = _prev_session(s, market)
            if prev is not None:
                assert _open_utc(prev, market) <= t
            local = t.astimezone(_TZ[market])
            if cal.is_session(local.date()) and local.time() < _REGULAR_OPEN:
                assert s == local.date()
            else:
                assert s > local.date()
            stamps.append((t, s))
        stamps.sort(key=lambda p: p[0])
        for (_, s1), (_, s2) in zip(stamps, stamps[1:]):
            assert s1 <= s2
        for _ in range(N_CASES):
            t1 = _rand_utc(rng, start, span)
            t2 = t1 + timedelta(seconds=rng.randint(0, 10 * 24 * 3600))
            assert first_session_after(t1, market) <= first_session_after(t2, market)


# ---------------------------------------------------------------------------
# 2. disclosure-date clock + to_utc DST
# ---------------------------------------------------------------------------

def test_first_session_after_disclosure_date_strictly_after() -> None:
    """DISCLOSURE_DATE maps to the first session strictly after the calendar date."""
    rng = random.Random(202)
    for market in (MARKET_US, MARKET_HK):
        cal = CLOCK_CALENDARS[market]
        for _ in range(N_CASES):
            d = date(2020, 1, 1) + timedelta(days=rng.randint(0, 2200))
            s = first_session_after_disclosure_date(d, market)
            assert s > d
            assert cal.is_session(s)
            prev = _prev_session(s, market)
            if prev is None:
                continue
            assert prev <= d


def test_to_utc_dst_summer_and_winter_per_market() -> None:
    """to_utc attaches the publisher zone then converts to UTC; NY DST offsets differ."""
    rng = random.Random(303)
    # Fixed summer + winter pins per market (module zones).
    pins = [
        ("America/New_York", datetime(2024, 1, 10, 9, 30), datetime(2024, 1, 10, 14, 30, tzinfo=UTC)),
        ("America/New_York", datetime(2024, 7, 10, 9, 30), datetime(2024, 7, 10, 13, 30, tzinfo=UTC)),
        ("Asia/Hong_Kong", datetime(2024, 1, 10, 9, 30), datetime(2024, 1, 10, 1, 30, tzinfo=UTC)),
        ("Asia/Hong_Kong", datetime(2024, 7, 10, 9, 30), datetime(2024, 7, 10, 1, 30, tzinfo=UTC)),
        # Either side of the 2024 US DST boundaries (non-gap, non-fold wall times).
        ("America/New_York", datetime(2024, 3, 10, 1, 30), datetime(2024, 3, 10, 6, 30, tzinfo=UTC)),
        ("America/New_York", datetime(2024, 3, 10, 3, 30), datetime(2024, 3, 10, 7, 30, tzinfo=UTC)),
        ("America/New_York", datetime(2024, 11, 3, 0, 30), datetime(2024, 11, 3, 4, 30, tzinfo=UTC)),
        ("America/New_York", datetime(2024, 11, 3, 3, 30), datetime(2024, 11, 3, 8, 30, tzinfo=UTC)),
    ]
    for tz_name, naive, expected in pins:
        got = to_utc(naive, tz_name)
        assert got.utcoffset() == timedelta(0)
        assert got == expected

    ny_winter_off = timedelta(hours=5)   # EST
    ny_summer_off = timedelta(hours=4)   # EDT
    hk_off = timedelta(hours=8)          # HKT, no DST
    for i in range(N_CASES):
        hour = rng.randint(0, 23)
        minute = rng.randint(0, 59)
        second = rng.randint(0, 59)
        if i % 2 == 0:
            # US winter (January) vs summer (July)
            if i % 4 == 0:
                naive = datetime(2020 + (i % 6), 1, rng.randint(5, 25), hour, minute, second)
                expect = datetime(naive.year, naive.month, naive.day,
                                  hour, minute, second, tzinfo=UTC) + ny_winter_off
                tz_name = "America/New_York"
            else:
                naive = datetime(2020 + (i % 6), 7, rng.randint(5, 25), hour, minute, second)
                expect = datetime(naive.year, naive.month, naive.day,
                                  hour, minute, second, tzinfo=UTC) + ny_summer_off
                tz_name = "America/New_York"
        else:
            month = 1 if i % 4 == 1 else 7
            naive = datetime(2020 + (i % 6), month, rng.randint(5, 25), hour, minute, second)
            expect = datetime(naive.year, naive.month, naive.day,
                              hour, minute, second, tzinfo=UTC) - hk_off
            tz_name = "Asia/Hong_Kong"
        got = to_utc(naive, tz_name)
        assert got.utcoffset() == timedelta(0)
        assert got == expect


# ---------------------------------------------------------------------------
# 3. session_part totality and monotone day sequence
# ---------------------------------------------------------------------------

def _part_rank(part: str, t_local: time, market: str) -> int:
    """Position of this instant in the documented through-day sequence."""
    if market == MARKET_US:
        if part == "pre_open":
            return 0
        if part == "in_session":
            return 1
        return 2  # after_close
    # HK: pre_open | in_session | midday_break | in_session | after_close
    if part == "pre_open":
        return 0
    if part == "midday_break":
        return 2
    if part == "after_close":
        return 4
    if t_local < _HK_BREAK[0]:
        return 1
    return 3


def test_session_part_total_and_monotone_through_day() -> None:
    """Every local instant maps to exactly one documented part; ranks do not recede."""
    rng = random.Random(404)
    start = datetime(2020, 1, 1, tzinfo=UTC)
    span = int(6.5 * 365 * 24 * 3600)
    for _ in range(N_CASES):
        t = _rand_utc(rng, start, span)
        for market in (MARKET_US, MARKET_HK):
            part = session_part(t, market)
            assert part in _SESSION_PARTS
            if market == MARKET_US:
                assert part != "midday_break"

    for _ in range(N_CASES):
        y = rng.randint(2020, 2026)
        m = rng.randint(1, 12)
        d = rng.randint(1, 28)
        market = rng.choice((MARKET_US, MARKET_HK))
        last_rank = -1
        last_part = None
        for minute in range(0, 24 * 60, 3):
            local = datetime(y, m, d, minute // 60, minute % 60, tzinfo=_TZ[market])
            part = session_part(local.astimezone(UTC), market)
            assert part in _SESSION_PARTS
            rank = _part_rank(part, local.time(), market)
            assert rank >= last_rank
            last_rank = rank
            last_part = part
        assert last_part == "after_close"

    # Boundary instants on a non-DST midsummer day.
    for market, expected in (
        (MARKET_US, [
            (time(0, 0), "pre_open"),
            (time(9, 29, 59, 999999), "pre_open"),
            (time(9, 30), "in_session"),
            (time(12, 30), "in_session"),
            (time(15, 59, 59), "in_session"),
            (time(16, 0), "after_close"),
        ]),
        (MARKET_HK, [
            (time(0, 0), "pre_open"),
            (time(9, 29, 59, 999999), "pre_open"),
            (time(9, 30), "in_session"),
            (time(11, 59, 59), "in_session"),
            (time(12, 0), "midday_break"),
            (time(12, 59, 59), "midday_break"),
            (time(13, 0), "in_session"),
            (time(15, 59, 59), "in_session"),
            (time(16, 0), "after_close"),
        ]),
    ):
        for tm, want in expected:
            local = datetime(2024, 7, 10, tm.hour, tm.minute, tm.second, tm.microsecond,
                             tzinfo=_TZ[market])
            assert session_part(local.astimezone(UTC), market) == want


# ---------------------------------------------------------------------------
# 4. splits: label, purge, window
# ---------------------------------------------------------------------------

def test_split_label_step_function_partition() -> None:
    """split_label is a partition of dates and monotone across TRAIN/TUNE/QUARANTINE."""
    rng = random.Random(505)
    order = {"TRAIN": 0, "TUNE": 1, "QUARANTINE": 2}
    seen = {date(2023, 12, 31): "TRAIN", date(2024, 1, 1): "TUNE",
            date(2026, 9, 30): "TUNE", date(2026, 10, 1): "QUARANTINE"}
    for d, want in seen.items():
        assert split_label(d) == want
    prev_rank = -1
    prev_date = date(2018, 1, 1)
    for i in range(N_CASES * 4):
        d = date(2019, 1, 1) + timedelta(days=rng.randint(0, 9 * 365))
        lab = split_label(d)
        assert lab in order
        if d < _TUNE_START:
            assert lab == "TRAIN"
        elif d < _QUARANTINE_START:
            assert lab == "TUNE"
        else:
            assert lab == "QUARANTINE"
        if d >= prev_date:
            assert order[lab] >= prev_rank or d == prev_date
        prev_date, prev_rank = d, order[lab]
    # Dedicated monotone walk of shuffled-then-sorted dates.
    dates = [date(2019, 1, 1) + timedelta(days=rng.randint(0, 3200)) for _ in range(N_CASES)]
    dates.sort()
    ranks = [order[split_label(d)] for d in dates]
    assert ranks == sorted(ranks)


def test_purge_flag_true_when_window_crosses_split_boundary() -> None:
    """TRAIN purges when coverage >= 2024-01-01; TUNE when coverage >= 2026-10-01."""
    rng = random.Random(606)
    cal = CLOCK_CALENDARS[MARKET_US]
    # Mix interior sessions with dates near both boundaries so True fires.
    near = [d for d in _US_SESSION_DATES
            if d in (date(2023, 10, 2), date(2023, 12, 20), date(2023, 12, 29),
                     date(2026, 7, 1), date(2026, 9, 1), date(2026, 9, 15))]
    pool = list(_SAFE_US)
    for _ in range(N_CASES):
        s = rng.choice(pool if rng.random() < 0.7 else (near or pool))
        h = rng.choice(tuple(GRADE_HORIZONS))
        split = split_label(s)
        coverage = window_last_session(s, h)
        got = purge_flag(split, coverage)
        expect = False
        if coverage is not None:
            if split == "TRAIN" and coverage >= _TUNE_START:
                expect = True
            elif split == "TUNE" and coverage >= _QUARANTINE_START:
                expect = True
        assert got is expect
        if split == "QUARANTINE":
            assert got is False
        if coverage is None:
            assert got is False
        # Documented crossing: last session of W_h on/after the next-split start.
        if cal.is_session(s) and coverage is not None:
            last = _hth_session_after(s, h, cal)
            assert coverage == last
            if split == "TRAIN" and last >= _TUNE_START:
                assert got is True
            if split == "TUNE" and last >= _QUARANTINE_START:
                assert got is True


def test_window_last_session_ge_s_and_grows_with_h() -> None:
    """For grade horizons, last session of W_h is >= s and non-decreasing in h."""
    rng = random.Random(707)
    cal = CLOCK_CALENDARS[MARKET_US]
    for _ in range(N_CASES):
        s = rng.choice(_SAFE_US)
        prev = None
        for h in GRADE_HORIZONS:
            w = window_last_session(s, h)
            assert w is not None
            assert w >= s
            assert w == _hth_session_after(s, h, cal)
            if prev is not None:
                assert w > prev
            prev = w
        # Adjacent positive h grows (h=0 is a documented FINDING: returns None).
        h1 = rng.randint(1, 20)
        h2 = rng.randint(h1, 40)
        w1 = window_last_session(s, h1)
        w2 = window_last_session(s, h2)
        assert w1 is not None and w2 is not None
        assert w1 >= s and w2 >= s
        assert w2 >= w1


# ---------------------------------------------------------------------------
# 5. episode_key / canonical_line / build_membership
# ---------------------------------------------------------------------------

def test_episode_key_and_canonical_line_deterministic_order_invariant() -> None:
    """episode_key is a pure function; canonical_line sorts keys so insertion order drops."""
    rng = random.Random(808)
    for i in range(N_CASES):
        issuer = rng.choice(_ISSUERS)
        fam = rng.choice(_FAMILIES)
        t = f"2023-0{1 + (i % 9)}-1{i % 9}T{i % 24:02d}:{(i * 3) % 60:02d}:00+00:00"
        ptr = f"synthetic#{i}-{rng.randint(0, 10**6)}"
        k1 = episode_key(issuer, fam, t, ptr)
        k2 = episode_key(issuer, fam, t, ptr)
        assert k1 == k2
        assert len(k1) == 64
        assert k1 != episode_key(issuer, fam, t, ptr + "-x")

        flags = {"purged": bool(i % 2), "confounded": bool(i % 3),
                 "absorbed_count": i % 5, "census_only": False,
                 "member_ids": [f"syn-{j}" for j in range(i % 4)]}
        obj_a = {"protocol_id": "P04", "horizon": 5, "episode_key": k1,
                 "split": "TRAIN", "flags": dict(flags), "z": i, "a": "x"}
        items = list(obj_a.items())
        rng.shuffle(items)
        obj_b = dict(items)
        flag_items = list(flags.items())
        rng.shuffle(flag_items)
        obj_b["flags"] = dict(flag_items)
        line_a = canonical_line(obj_a)
        line_b = canonical_line(obj_b)
        assert line_a == line_b
        assert line_a.endswith("\n")
        assert json.loads(line_a) == json.loads(line_b)


def test_build_membership_invariant_to_episode_order() -> None:
    """Manifest lines, sha table and counts do not depend on input episode order."""
    rng = random.Random(909)
    for i in range(N_CASES):
        n = rng.randint(2, 8)
        idxs = rng.sample(range(len(_SAFE_US_ISO) - 10), n)
        episodes = [
            _dummy_episode(
                j + i * 10,
                s_us=_SAFE_US_ISO[idxs[j]],
                s_hk=_SAFE_HK_ISO[idxs[j] % len(_SAFE_HK_ISO)],
                issuer=rng.choice(_ISSUERS),
                family=rng.choice(_FAMILIES),
                extra_family=(rng.choice(_FAMILIES) if rng.random() < 0.3 else None),
            )
            for j in range(n)
        ]
        n_co = rng.randint(0, 3)
        census = [
            _dummy_episode(
                1000 + j + i * 10,
                s_us=_SAFE_US_ISO[(idxs[0] + 3 + j) % len(_SAFE_US_ISO)],
                s_hk=_SAFE_HK_ISO[(idxs[0] + 3 + j) % len(_SAFE_HK_ISO)],
                issuer="issuer-y",
                family="results",
            )
            for j in range(n_co)
        ]
        by_h = {h: list(episodes) for h in GRADE_HORIZONS}
        co_h = {h: list(census) for h in GRADE_HORIZONS} if census else None
        lines1, sha1, c1 = build_membership("P04", by_h, co_h)
        rng.shuffle(episodes)
        rng.shuffle(census)
        by_h2 = {h: list(episodes) for h in GRADE_HORIZONS}
        co_h2 = {h: list(census) for h in GRADE_HORIZONS} if census else None
        lines2, sha2, c2 = build_membership("P04", by_h2, co_h2)
        assert lines1 == lines2
        assert sha1 == sha2
        assert c1 == c2
        assert all(ln.endswith("\n") for ln in lines1)


# ---------------------------------------------------------------------------
# 6. collapse: determinism, permutation, idempotence, conservation
# ---------------------------------------------------------------------------

def test_run_collapse_deterministic_and_row_permutation_of_events() -> None:
    """Same rows twice match fully; permuting rows leaves events/episodes unchanged.

    step0 exclusions follow input order (the exclusion list is not sorted).
    """
    rng = random.Random(111)
    horizons = tuple(GRADE_HORIZONS)
    for case in range(N_CASES):
        n = rng.randint(2, 10)
        rows = [_synth_row(rng, i) for i in range(n)]
        programmes: list[dict] = []
        kept_ids = [
            r["id"] for r in rows
            if r["t_avail_quality"] in _ADMISSIBLE
            and not (r["disposition"] == "EXCLUDED_AND_LISTED" and r["listed_exclusion_reason"])
        ]
        if len(kept_ids) >= 2 and rng.random() < 0.4:
            programmes = [{"key": "prog-syn", "member_ids": list(kept_ids[:2])}]
        event_exclusions = []
        if rng.random() < 0.3:
            event_exclusions = [{
                "match": {"family": rng.choice(_FAMILIES)},
                "reason": "synthetic_coverage_gap",
                "family_scope": "results",
            }]
        a = run_collapse(rows, programmes, _US_SESSIONS, _HK_SESSIONS,
                         horizons, event_exclusions)
        b = run_collapse(list(rows), list(programmes), _US_SESSIONS, _HK_SESSIONS,
                         horizons, event_exclusions)
        assert [_event_sig(e) for e in a["events"]] == [_event_sig(e) for e in b["events"]]
        assert [ (e.id, e.reason, e.step) for e in a["exclusions"] ] == [
            (e.id, e.reason, e.step) for e in b["exclusions"]
        ]
        for h in horizons:
            assert [_episode_sig(ep) for ep in a["per_h"][h]["episodes"]] == [
                _episode_sig(ep) for ep in b["per_h"][h]["episodes"]
            ]
        perm = list(rows)
        rng.shuffle(perm)
        c = run_collapse(perm, programmes, _US_SESSIONS, _HK_SESSIONS,
                         horizons, event_exclusions)
        assert [_event_sig(e) for e in a["events"]] == [_event_sig(e) for e in c["events"]]
        assert {e.id for e in a["exclusions"]} == {e.id for e in c["exclusions"]}
        for h in horizons:
            assert [_episode_sig(ep) for ep in a["per_h"][h]["episodes"]] == [
                _episode_sig(ep) for ep in c["per_h"][h]["episodes"]
            ]


def test_step1_and_step2_idempotent_on_own_output() -> None:
    """Regrouping step1 groups is identity; step2 without programmes does not re-merge."""
    rng = random.Random(222)
    for _ in range(N_CASES):
        rows = [_synth_row(rng, i, t_avail_quality="PUBLISHER_STATED",
                           disposition="SELECTED") for i in range(rng.randint(1, 10))]
        g1 = step1_counter_collapse(rows)
        flat = [r for rs in g1.values() for r in rs]
        assert {r["id"] for r in flat} == {r["id"] for r in rows}
        g2 = step1_counter_collapse(flat)
        ids1 = {k: [r["id"] for r in v] for k, v in g1.items()}
        ids2 = {k: [r["id"] for r in v] for k, v in g2.items()}
        assert ids1 == ids2

        evs, excluded = step2_dedup(rows, [])
        assert excluded == []
        rows2 = [{
            "id": e.member_ids[0],
            "issuer_key": e.issuer_key,
            "family": e.family,
            "t_avail_utc": e.t_avail_utc,
            "evidence_pointer": e.evidence_pointer,
            "s_us": e.s_us,
            "s_hk": e.s_hk,
        } for e in evs]
        evs2, excluded2 = step2_dedup(rows2, [])
        assert excluded2 == []
        keys1 = sorted((e.issuer_key, e.family, e.s_us, e.s_hk) for e in evs)
        keys2 = sorted((e.issuer_key, e.family, e.s_us, e.s_hk) for e in evs2)
        assert len(evs) == len(evs2)
        assert keys1 == keys2
        again, _ = step2_dedup(rows, [])
        assert [_event_sig(e) for e in evs] == [_event_sig(e) for e in again]


def _covered_ids(out: dict, h: int) -> dict[str, str]:
    """Map each visible id -> 'exclusion' | 'episode'."""
    place: dict[str, str] = {}
    for ex in out["exclusions"]:
        for part in ex.id.split(","):
            place[part] = "exclusion"
    for ep in out["per_h"][h]["episodes"]:
        ids = list(ep.opener.member_ids)
        for ab in ep.absorbed:
            ids.extend(ab.member_ids)
        for i in ids:
            assert i not in place or place[i] != "exclusion"
            place[i] = "episode"
    return place


def test_run_collapse_row_conservation() -> None:
    """Every input id lands in exactly one episode (any h) or exactly one exclusion."""
    rng = random.Random(333)
    horizons = tuple(GRADE_HORIZONS)
    for _ in range(N_CASES):
        n = rng.randint(2, 12)
        rows = []
        for i in range(n):
            disp = "SELECTED"
            reason = None
            quality = rng.choice(_ADMISSIBLE + ("EVENT_DATE", "CORRUPTED"))
            if rng.random() < 0.2:
                disp = "EXCLUDED_AND_LISTED"
                reason = "synthetic_named_exclusion"
            rows.append(_synth_row(rng, i, disposition=disp,
                                   listed_exclusion_reason=reason,
                                   t_avail_quality=quality))
        programmes: list[dict] = []
        kept = [
            r["id"] for r in rows
            if not (r["disposition"] == "EXCLUDED_AND_LISTED" and r["listed_exclusion_reason"])
            and r["t_avail_quality"] in _ADMISSIBLE
        ]
        if len(kept) >= 2 and rng.random() < 0.45:
            programmes = [{"key": "prog-syn", "member_ids": kept[:2]}]
        event_exclusions = []
        if rng.random() < 0.35:
            event_exclusions = [{
                "match": {"family": "results"},
                "reason": "synthetic_coverage_gap",
                "family_scope": "results",
            }]
        out = run_collapse(rows, programmes, _US_SESSIONS, _HK_SESSIONS,
                           horizons, event_exclusions)
        input_ids = [r["id"] for r in rows]
        for h in horizons:
            place = _covered_ids(out, h)
            for rid in input_ids:
                assert rid in place
            # Surviving events partition into episodes at each h (IL §3 step 4).
            ev_ids = []
            for e in out["events"]:
                ev_ids.extend(e.member_ids)
            ep_ids = []
            for ep in out["per_h"][h]["episodes"]:
                ep_ids.extend(ep.opener.member_ids)
                for ab in ep.absorbed:
                    ep_ids.extend(ab.member_ids)
            assert sorted(ev_ids) == sorted(ep_ids)


# ---------------------------------------------------------------------------
# 7. selection: split_tokens + classify_category
# ---------------------------------------------------------------------------

def test_split_tokens_idempotent_on_joined_output() -> None:
    """'<br/>'-split, stripped, order-preserving; join then split is identity.

    Empty tokens and None-join are FINDINGS (not asserted here).
    """
    rng = random.Random(444)
    alphabet = "0123456789ABCDEF"
    for _ in range(N_CASES):
        n = rng.randint(1, 6)
        tokens = []
        for _j in range(n):
            pad_l = " " * rng.randint(0, 2)
            pad_r = " " * rng.randint(0, 2)
            body = "".join(rng.choice(alphabet) for _k in range(rng.randint(1, 6)))
            tokens.append(body)
            # source strips each token; the stripped values are the contract.
        raw_parts = [
            (" " * rng.randint(0, 2)) + tok + (" " * rng.randint(0, 2))
            for tok in tokens
        ]
        cell = "<br/>".join(raw_parts)
        got = split_tokens(cell)
        assert got == tokens
        assert all(tok != "" for tok in got)
        assert split_tokens("<br/>".join(got)) == got
    assert split_tokens(None) == []


def test_classify_category_total_over_strings() -> None:
    """classify_category returns a documented class for every string and does not raise."""
    rng = random.Random(555)
    table_keys = list(CLASSIFICATION_TABLE)
    documented = _DOC_FAMILIES | set(CLASSIFICATION_TABLE.values())
    for k, v in CLASSIFICATION_TABLE.items():
        assert classify_category(k) == v
        assert classify_category(f"  {k}  ") == v
    for _ in range(N_CASES):
        if rng.random() < 0.25 and table_keys:
            s = rng.choice(table_keys)
        else:
            n = rng.randint(0, 24)
            alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFG0123456789 *_-/."
            s = "".join(rng.choice(alphabet) for _j in range(n))
        got = classify_category(s)
        assert got in documented
    for s in ("", "nope", "RESULTS", "Final_Results", "regulatory", "  "):
        assert classify_category(s) in documented
