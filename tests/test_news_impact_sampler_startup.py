"""Pins the sampler's share-cap STARTUP behaviour as registered (ni-sampler-1).

`_share_ok(used, total, cap)` admits one more counted item only when
(used + 1) / (total + 1) <= cap, evaluated at ADMISSION time over the counter
so far. With an empty counter the first counted item is therefore refused
until enough uncounted items precede it: ceil(1/cap) - 1 of them. The
registered gated_v2 and gated_v3 draws were produced WITH this behaviour,
so these tests pin it; they are not an endorsement, and any change is a
new sampler version plus a new draw (never a redraw of a registered one).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256

import pytest

from engine.news_impact import sampler as S

UTC = timezone.utc
WIN_START = date(2026, 7, 13)
WIN_END = date(2026, 10, 11)
TAPE_SHA = "ab" * 32


def iso(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 8, day, hour, tzinfo=UTC)


def cik(n: int) -> str:
    return f"cik:{n:010d}"


def cand(item_id: str, *, issuer: str, ticker: str | None = None, seendate: datetime) -> S.Candidate:
    return S.Candidate(
        item_id=item_id,
        issuer=issuer,
        ticker=ticker,
        template="T1",
        proxy_cell="positive",
        seendate=seendate,
        source="reuters",
        source_sha256=sha256(item_id.encode()).hexdigest(),
        event_key=None,
        tags=frozenset(),
        title="",
    )


def plan(**kw) -> S.SamplePlan:
    base = dict(seed=20261012, window_start=WIN_START, window_end=WIN_END, tape_sha256=TAPE_SHA)
    base.update(kw)
    return S.SamplePlan(**base)


def hash_order(seed: int, ids: list[str]) -> list[str]:
    return sorted(ids, key=lambda i: sha256(f"{seed}:{i}".encode()).hexdigest())


def find_id_with_rank(seed: int, target: str, others: list[str], rank: int) -> str:
    for n in range(5000):
        candidate = f"{target}{n:04d}"
        if hash_order(seed, others + [candidate]).index(candidate) == rank:
            return candidate
    raise AssertionError("no id found for the wanted hash rank")


@pytest.mark.parametrize(
    ("used", "total", "cap", "expected"),
    [
        (0, 0, 0.25, False),   # empty counter: the first counted item is refused
        (0, 2, 0.25, False),   # 1/3 > 0.25
        (0, 3, 0.25, True),    # 1/4 == 0.25 exactly: admitted
        (0, 8, 0.10, False),   # 1/9 > 0.10
        (0, 9, 0.10, True),    # 1/10 == 0.10 exactly: admitted
        (19, 199, 0.10, True),  # 20/200 == 0.10 exactly (integer scale, no float noise)
        (20, 200, 0.10, False),  # 21/201 > 0.10
        (56, 99, 0.57, True),   # 57/100 == 0.57 exactly (a naive float compare says False)
    ],
)
def test_share_ok_boundaries_as_registered(used, total, cap, expected):
    assert S._share_ok(used, total, cap) is expected


def test_share_scale_frozen():
    assert S._SHARE_SCALE == 1_000_000


def test_startup_refuses_first_counted_item_until_enough_uncounted_precede_it():
    # cap 0.25 -> the first mega-cap is admitted only once 3 uncounted items are in.
    assert [S._share_ok(0, t, 0.25) for t in range(5)] == [False, False, False, True, True]
    # cap 0.10 -> 9 uncounted items first.
    assert [S._share_ok(0, t, 0.10) for t in range(11)] == [False] * 9 + [True, True]


def test_megacap_first_in_hash_order_is_skipped_even_when_final_share_would_fit():
    # cap 0.25, target 4: the final share 1/4 == 0.25 would satisfy the cap, but the
    # rule is evaluated at admission over the counter so far; first in hash order the
    # mega-cap meets an empty counter, is refused, and is never revisited.
    others = [f"n{i:02d}" for i in range(6)]
    mega_id = find_id_with_rank(20261012, "mega", others, 0)
    cands = [cand(i, issuer=cik(100 + int(i[1:])), seendate=iso(1)) for i in others]
    cands.append(cand(mega_id, issuer=cik(999), ticker="NVDA", seendate=iso(1)))
    p = plan(cell_targets={"positive": 4, "negative": 0, "ambiguous": 0, "no_change": 0}, megacap_share_cap=0.25)
    d = S.draw_sample(cands, p, rights_allow=lambda s: True)
    assert mega_id not in {c.item_id for c in d.cases}
    assert d.manifest["cells"]["T1"]["positive"]["drawn"] == 4
    assert d.manifest["megacap_share"]["T1"] == 0.0


def test_megacap_last_in_hash_order_is_admitted_at_the_same_final_share():
    # Same pool, same cap, same target: with the mega-cap LAST in hash order it meets
    # a counter of 3 uncounted items and 1/4 <= 0.25 admits it. Order, not share, decides.
    others = [f"n{i:02d}" for i in range(3)]
    mega_id = find_id_with_rank(20261012, "mega", others, 3)
    cands = [cand(i, issuer=cik(100 + int(i[1:])), seendate=iso(1)) for i in others]
    cands.append(cand(mega_id, issuer=cik(999), ticker="NVDA", seendate=iso(1)))
    p = plan(cell_targets={"positive": 4, "negative": 0, "ambiguous": 0, "no_change": 0}, megacap_share_cap=0.25)
    d = S.draw_sample(cands, p, rights_allow=lambda s: True)
    assert mega_id in {c.item_id for c in d.cases}
    assert d.manifest["megacap_share"]["T1"] == pytest.approx(0.25)
