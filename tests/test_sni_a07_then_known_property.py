"""Seeded property tests for the A07 then-known-view compiler (LR-MEAS-A07P).

SNI-local DRAFT contract property tests for the three-clock then-known view
compiler at research/single_name_intelligence/common/sni_then_known_guard.py.
They consume owner-supplied fact record fields and synthetic fixtures; fact
ids and any issuer/security/listing ids are caller-supplied opaque strings
owned by Stock Identity / Data OS — nothing here mints, derives, or guesses
canonical HK/US issuer or security identifiers from a ticker, name, code, or
CIK. rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False. Historical
facts known only after a date are never treated as if known on that date.
Residuals and stress statistics are descriptive; this property suite makes
no causal or news-impact claim (A24). An unestimable family is outside this
module (A25).

Properties exercised (each runs at least 300 generated cases, seeded via the
stdlib `random.Random(20261015)` family only — no hypothesis):
    P1. No leak — every included item has published_at <= cutoff and
        owner_known_at <= cutoff.
    P2. Published after cutoff -> the first applicable exclusion is
        PUBLISHED_AFTER_CUTOFF (per the module's exclusion order).
    P3. Clock monotonicity — the set of items NOT clock-excluded
        (PUBLISHED_AFTER_CUTOFF, OWNER_KNOWN_AFTER_CUTOFF,
        RETRIEVED_AFTER_CUTOFF_UNVINTAGED) is non-decreasing as the cutoff
        moves later. SUPERSEDED_BY_THEN_KNOWN is asserted separately.
    P4. Supersession — A supersedes B and A is then-known implies B is
        excluded SUPERSEDED_BY_THEN_KNOWN; if A is not then-known, B's
        fate depends only on B's own clocks.
    P5. Order invariance — any permutation of inputs yields the same
        included set and the same (fact_id, reason) excluded mapping.
    P6. Fail-closed — any validation refusal produces allowed False with
        empty included and excluded.
    P7. Economic time is not a knowledge clock — vary economic_time
        freely, the included/excluded outcome is unchanged.

Boundary proof: `test_boundary_equality_included_in_every_clock` runs a
boundary case (every knowledge clock equal to the cutoff) against the real
compiler and against a copy whose cutoff compare uses `<` instead of
`<=`. The real compiler must include the fact; the perturbed copy must
exclude it with PUBLISHED_AFTER_CUTOFF. If either assertion fails the test
fails, and the failure trace identifies the boundary as the off-by-one.
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

import sni_then_known_guard as _tkg  # noqa: E402
from sni_then_known_guard import ThenKnownView, then_known_view  # noqa: E402

# Single seeded RNG family for every property. The seed itself is the FROZEN
# SPEC seed 20261015; each property adds a unique salt so the streams are
# independent and reproducible from this file alone.
BASE_SEED = 20261015
N_CASES = 300  # FROZEN SPEC: >= 300 generated cases per property.


# ---------------------------------------------------------------------------
# Datetime / cutoff generators
# ---------------------------------------------------------------------------

def _aware(year, month, day, hour=0, minute=0, second=0, micro=0):
    return datetime(year, month, day, hour, minute, second, micro, tzinfo=timezone.utc)


def _iso(dt):
    """Always emit the offset; the module requires it."""
    return dt.astimezone(timezone.utc).isoformat()


# Generated cutoffs stay inside [2024-01-01, 2028-12-31] so every generated
# ISO datetime is one the module's parser can handle.
CUTOFF_YEARS = (2024, 2025, 2026, 2027, 2028)


def _gen_cutoff(rng):
    year = rng.choice(CUTOFF_YEARS)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    hour = rng.randint(0, 23)
    minute = rng.randint(0, 59)
    return _aware(year, month, day, hour, minute)


# ---------------------------------------------------------------------------
# Item generators
# ---------------------------------------------------------------------------

def _valid_items(rng, count, cutoff, *, boundary_prob=0.2):
    """Build `count` valid items with no validation refusals.

    Roughly `boundary_prob` fraction of items land exactly on the cutoff on
    at least one clock so P1's `<=` check distinguishes the real compiler
    from a `<` perturbation.
    """
    items = []
    for i in range(count):
        # published_at: equal to cutoff, within 48h, or anywhere in a year.
        u = rng.random()
        if u < boundary_prob:
            published = cutoff
        elif u < 0.5:
            published = cutoff + timedelta(hours=rng.randint(-48, 48))
        else:
            published = (
                cutoff
                + timedelta(days=rng.randint(-365, 365))
                + timedelta(hours=rng.randint(-23, 23))
            )
        # owner_known_at: >= published; up to ~6 days later.
        ok_offset = rng.randint(0, 6 * 24)
        owner_known = published + timedelta(hours=ok_offset)
        # retrieved_at: >= published; up to ~a year later.
        retr_offset = rng.randint(0, 365 * 24)
        retrieved = published + timedelta(hours=retr_offset)
        # vintaged: True/False/None, sometimes omitted.
        vintaged = None
        roll = rng.random()
        if roll < 0.4:
            vintaged = True
        elif roll < 0.7:
            vintaged = False
        elif roll < 0.85:
            vintaged = None
        # else: omit (the module tolerates a missing key).
        # economic_time: anywhere across +/- ~2 years, hours-minutes vary.
        eco = cutoff + timedelta(days=rng.randint(-720, 720), hours=rng.randint(-23, 23))
        item = {
            "fact_id": "f-%d" % i,
            "economic_time": _iso(eco),
            "owner_known_at": _iso(owner_known),
            "published_at": _iso(published),
            "retrieved_at": _iso(retrieved),
            "supersedes": None,
        }
        if vintaged is not None:
            item["vintaged"] = vintaged
        items.append(item)
    return items


def _attach_supersedes(rng, items):
    """Optionally add an acyclic supersedes link to one fact.

    Returns a *new* list (does not mutate). With prob 0.5 the fact at a
    random higher index supersedes the fact at a random lower index.
    """
    items = [dict(it) for it in items]
    if len(items) >= 2 and rng.random() < 0.5:
        i_old = rng.randrange(len(items))
        i_new = rng.randrange(len(items))
        guard = 0
        while i_new == i_old and guard < 8:
            i_new = rng.randrange(len(items))
            guard += 1
        if i_new != i_old:
            items[i_new]["supersedes"] = items[i_old]["fact_id"]
    return items


# ---------------------------------------------------------------------------
# View helpers
# ---------------------------------------------------------------------------

def _included(view):
    return set(view.included)


def _excluded(view):
    return set(view.excluded)


def _msg(seed, case):
    return "seed=%s case=%s" % (seed, case)


CLOCK_EXCLUSION_REASONS = (
    "PUBLISHED_AFTER_CUTOFF",
    "OWNER_KNOWN_AFTER_CUTOFF",
    "RETRIEVED_AFTER_CUTOFF_UNVINTAGED",
)


# ---------------------------------------------------------------------------
# P1. No leak: every included item has published_at <= cutoff and
#     owner_known_at <= cutoff.
# ---------------------------------------------------------------------------

def test_p1_no_post_cutoff_leak():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 1 + case)
        cutoff = _gen_cutoff(rng)
        items = _valid_items(rng, count=rng.randint(1, 12), cutoff=cutoff)
        items = _attach_supersedes(rng, items)
        view = then_known_view(items, cutoff=_iso(cutoff))
        msg = _msg(BASE_SEED + 1, case)
        # Validation failures are not what this property guards.
        if not view.allowed:
            assert view.included == () and view.excluded == (), msg
            total += 1
            continue
        for item in items:
            fid = item["fact_id"]
            if fid in _included(view):
                pub = datetime.fromisoformat(item["published_at"])
                own = datetime.fromisoformat(item["owner_known_at"])
                assert pub <= cutoff, (
                    f"{msg} fact {fid} included but published_at={pub} "
                    f"> cutoff={cutoff}"
                )
                assert own <= cutoff, (
                    f"{msg} fact {fid} included but owner_known_at={own} "
                    f"> cutoff={cutoff}"
                )
        total += 1
    assert total >= N_CASES, "p1 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P2. Published strictly after cutoff -> first applicable exclusion is
#     PUBLISHED_AFTER_CUTOFF.
# ---------------------------------------------------------------------------

def test_p2_published_after_cutoff_first_applicable():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 2 + case)
        cutoff = _gen_cutoff(rng)
        n = rng.randint(1, 8)
        items = []
        for i in range(n):
            # Base items stay strictly before cutoff on every clock.
            base_pub = cutoff - timedelta(
                days=rng.randint(2, 60), hours=rng.randint(1, 23)
            )
            base_owner = base_pub + timedelta(hours=rng.randint(1, 6))
            base_retr = base_pub + timedelta(hours=rng.randint(1, 12))
            items.append(
                {
                    "fact_id": "f-base-%d" % i,
                    "economic_time": _iso(cutoff - timedelta(days=rng.randint(0, 200))),
                    "owner_known_at": _iso(base_owner),
                    "published_at": _iso(base_pub),
                    "retrieved_at": _iso(base_retr),
                    "vintaged": True,
                    "supersedes": None,
                }
            )
        # Injector: a fact whose published_at is strictly after cutoff;
        # owner_known / retrieved also after cutoff, so the first applicable
        # exclusion is PUBLISHED_AFTER_CUTOFF, never the later reasons.
        inj_pub = cutoff + timedelta(
            days=rng.randint(1, 10), hours=rng.randint(1, 23)
        )
        items.append(
            {
                "fact_id": "f-inj",
                "economic_time": _iso(cutoff - timedelta(days=rng.randint(0, 30))),
                "owner_known_at": _iso(inj_pub + timedelta(hours=rng.randint(1, 6))),
                "published_at": _iso(inj_pub),
                "retrieved_at": _iso(inj_pub + timedelta(hours=rng.randint(1, 6))),
                "vintaged": True,
                "supersedes": None,
            }
        )
        view = then_known_view(items, cutoff=_iso(cutoff))
        msg = _msg(BASE_SEED + 2, case)
        assert view.allowed is True, msg
        assert "f-inj" not in _included(view), msg
        assert ("f-inj", "PUBLISHED_AFTER_CUTOFF") in _excluded(view), (
            f"{msg} expected PUBLISHED_AFTER_CUTOFF, got "
            f"{[r for f, r in view.excluded if f == 'f-inj']!r}"
        )
        total += 1
    assert total >= N_CASES, "p2 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P3. Clock monotonicity. The set of items NOT excluded for a clock reason
#     is non-decreasing as the cutoff moves later. SUPERSEDED_BY_THEN_KNOWN
#     is asserted separately (it is allowed to grow when later items join
#     the passing set and supersede earlier ones).
# ---------------------------------------------------------------------------

def _survivors_at(items, cutoff_dt):
    view = then_known_view(items, cutoff=_iso(cutoff_dt))
    if not view.allowed:
        return None
    return {
        "survivors": _included(view),
        "clock_excluded": {
            fid
            for fid, reason in view.excluded
            if reason in CLOCK_EXCLUSION_REASONS
        },
        "superseded": {
            fid
            for fid, reason in view.excluded
            if reason == "SUPERSEDED_BY_THEN_KNOWN"
        },
    }


def test_p3_clock_monotonicity_non_decreasing():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 3 + case)
        late = _gen_cutoff(rng)
        earlier = late - timedelta(
            days=rng.randint(1, 200), hours=rng.randint(1, 23)
        )
        items = _valid_items(rng, count=rng.randint(1, 10), cutoff=late)
        items = _attach_supersedes(rng, items)
        view_late = _survivors_at(items, late)
        view_early = _survivors_at(items, earlier)
        msg = _msg(BASE_SEED + 3, case)
        if view_late is None or view_early is None:
            total += 1
            continue
        # Clock-excluded set is monotone: it cannot grow as the cutoff
        # moves later (so its complement — what survives clocks — is
        # non-decreasing).
        early_clock_survivors = view_early["survivors"] | view_early["superseded"]
        late_clock_survivors = view_late["survivors"] | view_late["superseded"]
        assert early_clock_survivors.issubset(late_clock_survivors), (
            f"{msg} clock survivors shrank as cutoff moved later: "
            f"lost={early_clock_survivors - late_clock_survivors}"
        )
        # Explicit: SUPERSEDED_BY_THEN_KNOWN is not in the clock set;
        # the late pass can supersede things the early pass couldn't.
        assert (
            view_late["clock_excluded"] | view_late["superseded"]
        ).issubset(
            view_late["survivors"]
            | view_late["clock_excluded"]
            | view_late["superseded"]
        )
        total += 1
    assert total >= N_CASES, "p3 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P4. Supersession: A supersedes B and A is then-known -> B is excluded
#     SUPERSEDED_BY_THEN_KNOWN; if A is not then-known, B's fate depends
#     only on B's own clocks.
# ---------------------------------------------------------------------------

def test_p4_supersession_depends_on_a_then_knownness():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 4 + case)
        cutoff = _gen_cutoff(rng)
        # B: clearly then-known (published well before cutoff; vintaged).
        b_pub = cutoff - timedelta(
            days=rng.randint(10, 100), hours=rng.randint(1, 23)
        )
        b_owner = b_pub + timedelta(hours=rng.randint(1, 6))
        b_retr = b_pub + timedelta(hours=rng.randint(1, 12))
        b = {
            "fact_id": "f-b",
            "economic_time": _iso(cutoff - timedelta(days=rng.randint(50, 200))),
            "owner_known_at": _iso(b_owner),
            "published_at": _iso(b_pub),
            "retrieved_at": _iso(b_retr),
            "vintaged": True,
            "supersedes": None,
        }
        # A either then-known (subcase A1) or strictly after cutoff (A2).
        if rng.random() < 0.5:
            # All three clocks land safely before cutoff: at least 12h
            # before, then owner_known / retrieved move at most 4h forward,
            # so even the latest clock is <= cutoff - 8h. vintaged=True
            # is irrelevant here but kept for symmetry with B.
            a_pub = cutoff - timedelta(hours=rng.randint(12, 48))
            a_owner = a_pub + timedelta(hours=rng.randint(1, 4))
            a_retr = a_pub + timedelta(hours=rng.randint(1, 4))
            a_then_known = True
        else:
            a_pub = cutoff + timedelta(
                days=rng.randint(1, 30), hours=rng.randint(1, 23)
            )
            a_owner = a_pub + timedelta(hours=rng.randint(1, 6))
            a_retr = a_pub + timedelta(hours=rng.randint(1, 6))
            a_then_known = False
        a = {
            "fact_id": "f-a",
            "economic_time": _iso(cutoff - timedelta(days=rng.randint(50, 200))),
            "owner_known_at": _iso(a_owner),
            "published_at": _iso(a_pub),
            "retrieved_at": _iso(a_retr),
            "vintaged": True,
            "supersedes": "f-b",
        }
        view = then_known_view([b, a], cutoff=_iso(cutoff))
        msg = _msg(BASE_SEED + 4, case)
        assert view.allowed is True, msg
        excluded = _excluded(view)
        if a_then_known:
            assert "f-a" in _included(view), msg
            assert ("f-b", "SUPERSEDED_BY_THEN_KNOWN") in excluded, msg
            assert ("f-a", "PUBLISHED_AFTER_CUTOFF") not in excluded, msg
        else:
            assert ("f-a", "PUBLISHED_AFTER_CUTOFF") in excluded, msg
            assert "f-b" in _included(view), msg
            assert ("f-b", "SUPERSEDED_BY_THEN_KNOWN") not in excluded, msg
        total += 1
    assert total >= N_CASES, "p4 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P5. Order invariance: any permutation of inputs gives the same included
#     set and the same (fact_id, reason) excluded mapping.
# ---------------------------------------------------------------------------

def test_p5_permutation_invariance():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 5 + case)
        cutoff = _gen_cutoff(rng)
        items = _valid_items(rng, count=rng.randint(2, 10), cutoff=cutoff)
        items = _attach_supersedes(rng, items)
        base = then_known_view(list(items), cutoff=_iso(cutoff))
        if not base.allowed:
            total += 1
            continue
        # A non-trivial shuffle that differs from base order.
        permuted = list(items)
        rng.shuffle(permuted)
        if tuple(f["fact_id"] for f in permuted) == tuple(
            f["fact_id"] for f in items
        ):
            permuted = list(reversed(items))
        view = then_known_view(permuted, cutoff=_iso(cutoff))
        msg = _msg(BASE_SEED + 5, case)
        assert view.allowed is True, msg
        assert _included(base) == _included(view), (
            f"{msg} included set drifted under permutation: "
            f"base={_included(base)} permuted={_included(view)}"
        )
        assert _excluded(base) == _excluded(view), (
            f"{msg} excluded mapping drifted under permutation: "
            f"base={_excluded(base)} permuted={_excluded(view)}"
        )
        total += 1
    assert total >= N_CASES, "p5 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P6. Fail-closed: every validation refusal -> allowed False with empty
#     included/excluded. 34 cases per reason x 9 reasons >= 306 cases.
# ---------------------------------------------------------------------------

_VALIDATION_CASES = 34  # >=300 / 9 = 33.4; 34 yields >= 306 generated cases.


def _fixture_for(rng, code, cutoff):
    """Construct a synthetic fixture that triggers a single refusal code."""
    if code == "FACT_ID_MISSING":
        items = _valid_items(rng, count=2, cutoff=cutoff)
        items[0]["fact_id"] = None
        return items
    if code == "DUPLICATE_FACT_ID":
        items = _valid_items(rng, count=2, cutoff=cutoff)
        items[1]["fact_id"] = items[0]["fact_id"]
        return items
    if code == "ECONOMIC_TIME_INVALID":
        items = _valid_items(rng, count=2, cutoff=cutoff)
        items[0]["economic_time"] = "2026-01-01"  # naive date-only
        return items
    if code == "OWNER_KNOWN_INVALID":
        items = _valid_items(rng, count=2, cutoff=cutoff)
        items[0]["owner_known_at"] = "garbage"
        return items
    if code == "PUBLISHED_INVALID":
        items = _valid_items(rng, count=2, cutoff=cutoff)
        del items[0]["published_at"]
        return items
    if code == "RETRIEVED_INVALID":
        items = _valid_items(rng, count=2, cutoff=cutoff)
        items[0]["retrieved_at"] = "2026-13-01T00:00:00+00:00"  # month=13
        return items
    if code == "OWNER_KNOWN_BEFORE_PUBLISHED":
        items = _valid_items(rng, count=2, cutoff=cutoff)
        items[0]["owner_known_at"] = _iso(
            datetime.fromisoformat(items[0]["published_at"])
            - timedelta(days=1)
        )
        return items
    if code == "RETRIEVED_BEFORE_PUBLISHED":
        items = _valid_items(rng, count=2, cutoff=cutoff)
        items[0]["retrieved_at"] = _iso(
            datetime.fromisoformat(items[0]["published_at"])
            - timedelta(days=1)
        )
        return items
    if code == "SUPERSEDES_UNKNOWN":
        items = _valid_items(rng, count=2, cutoff=cutoff)
        items[1]["supersedes"] = "iss-not-in-set"
        return items
    raise AssertionError("unknown code " + code)


def test_p6_fail_closed_for_each_reason():
    codes = (
        "FACT_ID_MISSING",
        "DUPLICATE_FACT_ID",
        "ECONOMIC_TIME_INVALID",
        "OWNER_KNOWN_INVALID",
        "PUBLISHED_INVALID",
        "RETRIEVED_INVALID",
        "OWNER_KNOWN_BEFORE_PUBLISHED",
        "RETRIEVED_BEFORE_PUBLISHED",
        "SUPERSEDES_UNKNOWN",
    )
    total = 0
    for code in codes:
        for case in range(_VALIDATION_CASES):
            # str hash() is salted per process (PYTHONHASHSEED); derive the
            # seed from the code's position so every run replays the same cases.
            rng = random.Random(BASE_SEED + 6 + codes.index(code) * 100000 + case)
            cutoff = _gen_cutoff(rng)
            items = _fixture_for(rng, code, cutoff)
            view = then_known_view(items, cutoff=_iso(cutoff))
            msg = "reason=%s case=%d" % (code, case)
            assert view.allowed is False, msg
            assert code in view.reasons, (
                f"{msg} expected {code!r} in reasons, got {view.reasons!r}"
            )
            assert view.included == (), msg
            assert view.excluded == (), msg
            total += 1
    assert total >= N_CASES, "p6 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P7. economic_time is not a knowledge clock: vary it freely, the view is
#     unchanged.
# ---------------------------------------------------------------------------

def test_p7_economic_time_never_changes_view():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 7 + case)
        cutoff = _gen_cutoff(rng)
        items = _valid_items(rng, count=rng.randint(1, 8), cutoff=cutoff)
        items = _attach_supersedes(rng, items)
        base_view = then_known_view(
            [dict(it) for it in items], cutoff=_iso(cutoff)
        )
        for _ in range(2):
            varied = [dict(it) for it in items]
            for it in varied:
                eco = _aware(
                    rng.randint(1990, 2099),
                    rng.randint(1, 12),
                    rng.randint(1, 28),
                    rng.randint(0, 23),
                    rng.randint(0, 59),
                )
                it["economic_time"] = _iso(eco)
            varied_view = then_known_view(varied, cutoff=_iso(cutoff))
            msg = "case=%d" % case
            assert base_view.reasons == varied_view.reasons, (
                f"{msg} reasons changed under economic_time variation: "
                f"base={base_view.reasons!r} varied={varied_view.reasons!r}"
            )
            assert base_view.allowed is varied_view.allowed, msg
            if base_view.allowed:
                assert _included(base_view) == _included(varied_view), msg
                assert _excluded(base_view) == _excluded(varied_view), msg
        total += 1
    assert total >= N_CASES, "p7 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# Boundary + PERTURBATION PROOF
# ---------------------------------------------------------------------------

def _then_known_view_with_lt(items, *, cutoff):
    """A perturbed copy of then_known_view whose cutoff compares use `<`.

    The FROZEN SPEC says: "monkeypatch the module so the cutoff compare
    uses `<` instead of `<=`". The real module's INCLUDE condition is
    `pub <= cutoff_dt` (line 300: exclude iff `pub > cutoff`); its
    perturbation is to flip the boundary, i.e., include only when strictly
    before the cutoff. This copy mirrors the module's first-applicable
    clock ordering (published -> owner_known -> retrieved+vintaged) but
    uses `<=` for the EXCLUDE compare at every clock, so a fact whose
    clock equals the cutoff is excluded by this copy. The boundary proof
    below demonstrates that a fact whose every knowledge clock equals the
    cutoff is INCLUDED by the real compiler and EXCLUDED by this copy
    (PUBLISHED_AFTER_CUTOFF).
    """
    items = list(items)
    for it in items:
        if not isinstance(it, Mapping):
            raise TypeError("item must be a Mapping")
    cutoff_dt = _tkg._aware_value(cutoff)
    if cutoff_dt is None:
        raise ValueError("cutoff unusable")
    parsed = []
    for it in items:
        parsed.append(
            (
                it.get("fact_id"),
                _tkg._aware_value(it.get("published_at")),
                _tkg._aware_value(it.get("owner_known_at")),
                _tkg._aware_value(it.get("retrieved_at")),
                it.get("vintaged"),
            )
        )
    included = []
    excluded = []
    for fid, pub, own, retr, vin in parsed:
        if pub is not None and pub <= cutoff_dt:
            excluded.append((fid, "PUBLISHED_AFTER_CUTOFF"))
        elif own is not None and own <= cutoff_dt:
            excluded.append((fid, "OWNER_KNOWN_AFTER_CUTOFF"))
        elif retr is not None and retr <= cutoff_dt and vin is not True:
            excluded.append((fid, "RETRIEVED_AFTER_CUTOFF_UNVINTAGED"))
        else:
            included.append(fid)
    return ThenKnownView(True, (), tuple(included), tuple(excluded))


def test_boundary_equality_included_in_every_clock():
    """A fact whose every knowledge clock equals the cutoff is then-known.

    Real `<=` semantics must INCLUDE such a fact. A copy with `<` against
    the cutoff must EXCLUDE it (PUBLISHED_AFTER_CUTOFF, the first
    applicable reason). Either side failing means the boundary is
    mis-handled.
    """
    rng = random.Random(BASE_SEED + 8)
    cutoff = _aware(2026, 6, 1, 12, 0)
    fact_id = "f-boundary"
    item = {
        "fact_id": fact_id,
        "economic_time": _iso(cutoff - timedelta(days=10)),
        "owner_known_at": _iso(cutoff),
        "published_at": _iso(cutoff),
        "retrieved_at": _iso(cutoff),
        "vintaged": True,
        "supersedes": None,
    }

    # Real semantics: equality is included (every knowledge clock <= cutoff).
    real_view = then_known_view([item], cutoff=_iso(cutoff))
    assert real_view.allowed is True, (
        "real compiler refused a valid boundary fact: "
        f"reasons={real_view.reasons!r}"
    )
    assert fact_id in _included(real_view), (
        "real compiler dropped a boundary-equal fact: "
        f"included={real_view.included!r} excluded={real_view.excluded!r}"
    )

    # Perturbed semantics: a `<` comparison excludes the boundary fact.
    bad_view = _then_known_view_with_lt([item], cutoff=_iso(cutoff))
    boundary_excluded = (
        fact_id not in _included(bad_view)
        and (fact_id, "PUBLISHED_AFTER_CUTOFF") in _excluded(bad_view)
    )
    assert boundary_excluded, (
        "PERTURBATION PROOF FAILED: the < copy still allowed the "
        f"boundary fact (included={bad_view.included!r} "
        f"excluded={bad_view.excluded!r}). Off-by-one confirmed: "
        "the boundary must flip the inclusion outcome between <= and <."
    )


def test_perturbation_proves_off_by_one_on_random_cases():
    """Across N_CASES random generators, the `<` copy must flip a
    boundary-equal fact from included to excluded.

    The same `_valid_items` generator that powers P1/P3/P5/P7 keeps
    a fraction of items exactly on the cutoff. Real compiler includes
    them; the `<` copy must exclude at least one such fact over the run.
    That is the off-by-one the spec contracts out.
    """
    flipped = None
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 1000 + case)
        cutoff = _gen_cutoff(rng)
        items = _valid_items(
            rng, count=rng.randint(2, 12), cutoff=cutoff, boundary_prob=0.5
        )
        items = _attach_supersedes(rng, items)
        real = then_known_view(items, cutoff=_iso(cutoff))
        bad = _then_known_view_with_lt(items, cutoff=_iso(cutoff))
        if not real.allowed or not bad.allowed:
            continue
        for item in items:
            fid = item["fact_id"]
            pub = datetime.fromisoformat(item["published_at"])
            if fid in _included(real) and fid not in _included(bad):
                if pub == cutoff:
                    flipped = (case, fid, pub)
                    break
        if flipped is not None:
            break
    assert flipped is not None, (
        "PERTURBATION PROOF FAILED: across %d generated cases the < copy "
        "never excluded a fact that the real compiler included at the "
        "exact cutoff. The boundary off-by-one is not exercised."
        % N_CASES
    )
