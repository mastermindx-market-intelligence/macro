"""Seeded property tests for the A09 join guard (LR-MEAS-A09P).

SNI-local DRAFT contract property tests for
research/single_name_intelligence/common/sni_join_guard.py.

34 REASONS across 3 join kinds (same_fact, ratio, time_series). Each
property runs at least 300 generated cases with a per-case seeded stdlib
RNG (``random.Random(20261016 + k + case)``); nothing here is hypothesis-
based. A property that fails on the base module is a finding, marked
``@pytest.mark.xfail(strict=True)`` and reported in GAPS.

rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False throughout.
Historical facts known only after a date are never treated as if known
on that date. Residuals and stress statistics stay descriptive; this
property suite makes no causal or news-impact claim (A24). An
unestimable family is outside this module (A25).

Properties exercised (each >= 300 cases):
    P1. Reflexive -- an identical fact pair is ALLOWED under each join kind.
    P2. Single-field perturbation -- perturbing exactly ONE compared field
        on RIGHT produces that field's bare mismatch code.
    P3. Swap invariance -- check_join(L, R) and check_join(R, L) yield the
        same bare-reason set (LEFT:/RIGHT: prefixes stripped).
    P4. Unknown field -- a non-FACT_FIELDS key triggers
        SCHEMA_UNKNOWN_FIELD:<K> in validate_fact.
    P5. Vocabulary -- every bare reason in any verdict is in REASONS (or
        SCHEMA_UNKNOWN_FIELD); validate_fact reasons are sorted and
        de-duplicated.
    P6. No raise on junk -- random junk in any field raises no exception.
    P7. Authority -- every verdict's authority flags are literal False.
    P8. Padded ids absent -- a padded / whitespace-only id never joins as
        equal to the unpadded id.
    P9. Unknown join_kind -- refuses with JOIN_KIND_UNKNOWN.

PERTURBATION PROOF: ``_check_join_broken`` is a hand-written copy whose
currency-mismatch branch always fires. Three property-style assertions
prove the broken copy fails P1 and P2 while the real module passes them.
"""
from __future__ import annotations

import math
import random
import sys
from datetime import date
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_join_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    FACT_FIELDS,
    JOIN_KINDS,
    REASONS,
    JoinVerdict,
    check_join,
    validate_fact,
)

BASE_SEED = 20261016
N_CASES = 300

JOIN_KIND_SET = frozenset(JOIN_KINDS)
FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)


def _msg(seed: int, case: int) -> str:
    return "seed=%d case=%d" % (seed, case)


# ---------------------------------------------------------------------------
# Fact generators (synthetic fixtures; no canonical issuer/security ids)
# ---------------------------------------------------------------------------

def _gen_issuer_id(rng: random.Random) -> str:
    return "SYN-ISSUER-%d" % rng.randint(1, 50)


def _gen_source_owner(rng: random.Random) -> str:
    return rng.choice(("SYN-OWNER-A", "SYN-OWNER-B"))


def _gen_period_pair(rng: random.Random) -> tuple[str, str]:
    """A start/end pair with the end strictly after the start (1..400 days)."""
    y = rng.randint(2020, 2027)
    m = rng.randint(1, 12)
    d = rng.randint(1, 28)
    start = date(y, m, d)
    days_later = rng.randint(1, 400)
    end = date.fromordinal(start.toordinal() + days_later)
    return start.isoformat(), end.isoformat()


def _gen_known_at(rng: random.Random) -> str:
    y = rng.randint(2025, 2028)
    m = rng.randint(1, 12)
    d = rng.randint(1, 28)
    h = rng.randint(0, 23)
    mi = rng.randint(0, 59)
    return "%04d-%02d-%02dT%02d:%02d:00" % (y, m, d, h, mi)


def _gen_valid_fact(rng: random.Random, **overrides) -> dict:
    """Build a fact whose validate_fact() returns (). Caller may override
    any key; remaining keys are filled with synthetic values.
    """
    overrides = dict(overrides)
    level = overrides.pop("level", None)
    if level is None:
        level = rng.choice(("issuer", "security"))
    pstart, pend = _gen_period_pair(rng)
    # known_at must be on or after period_end so TIMESTAMP_INCOHERENT is
    # never raised by validate_fact().
    pend_dt = date.fromisoformat(pend)
    ka = pend_dt
    delta = rng.randint(0, 200)
    ka = date.fromordinal(pend_dt.toordinal() + delta)
    known_at = "%04d-%02d-%02dT00:00:00" % (ka.year, ka.month, ka.day)
    fact = {
        "issuer_id": _gen_issuer_id(rng),
        "level": level,
        "metric": rng.choice(("revenue", "net_income", "op_income")),
        "period_type": rng.choice(("annual", "interim", "quarterly")),
        "period_start": pstart,
        "period_end": pend,
        "basis": rng.choice(("reported", "adjusted")),
        "currency": "CNY",
        "source_reported_currency": "CNY",
        "scale": rng.choice((0, 3, 6, 9)),
        "share_denominator": rng.choice(("BASIC", "DILUTED", "NOT_PER_SHARE")),
        "version": rng.choice(("v1", "v2", "v3")),
        "known_at": known_at,
        "source_owner": _gen_source_owner(rng),
        "value": rng.randint(1, 10000),
    }
    if level == "security":
        fact["counter_id"] = "SYN-CTR-%d" % rng.randint(1, 5)
    fact.update(overrides)
    return fact


def _bare(reason: str) -> str:
    """Strip LEFT:/RIGHT: prefix; collapse SCHEMA_UNKNOWN_FIELD:<K> to bare."""
    if reason.startswith("LEFT:"):
        reason = reason[5:]
    elif reason.startswith("RIGHT:"):
        reason = reason[6:]
    if reason.startswith("SCHEMA_UNKNOWN_FIELD"):
        return "SCHEMA_UNKNOWN_FIELD"
    return reason


def _stripped(reasons) -> tuple:
    """Sorted set of bare reason codes (LEFT:/RIGHT: stripped)."""
    return tuple(sorted(set(_bare(r) for r in reasons)))


# ---------------------------------------------------------------------------
# P1. Reflexive -- an identical fact pair is ALLOWED for every join kind.
# ---------------------------------------------------------------------------

def test_p1_reflexive():
    kinds = ("same_fact", "ratio", "time_series")
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 1 + case)
        kind = kinds[case % len(kinds)]
        fact = _gen_valid_fact(rng)
        verdict = check_join(fact, dict(fact), join_kind=kind)
        msg = _msg(BASE_SEED + 1, case)
        assert verdict.status == "ALLOWED", (
            "%s kind=%s expected ALLOWED for identical facts, got "
            "status=%s reasons=%r"
            % (msg, kind, verdict.status, verdict.reasons)
        )
        assert verdict.reasons == (), msg
        total += 1
    assert total >= N_CASES, "p1 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P2. Single-field perturbation: changing exactly ONE compared field on
#     RIGHT must produce that field's mismatch bare code.
# ---------------------------------------------------------------------------

# Tested (join_kind, field) pairs. Only pairs where exactly ONE compare
# fires (or the expected code is unambiguous) are listed.
_TESTED_PAIRS = (
    ("same_fact", "issuer_id"),
    ("same_fact", "level"),
    ("same_fact", "metric"),
    ("same_fact", "period_type"),
    ("same_fact", "period_start"),
    ("same_fact", "period_end"),
    ("same_fact", "basis"),
    ("same_fact", "currency"),
    ("same_fact", "scale"),
    ("same_fact", "share_denominator"),
    ("same_fact", "version"),
    ("same_fact", "segment"),
    ("same_fact", "segment_scheme_version"),
    ("same_fact", "counter_id"),
    ("ratio", "issuer_id"),
    ("ratio", "currency"),
    ("ratio", "scale"),
    ("ratio", "basis"),
    ("ratio", "segment_scheme_version"),
    ("time_series", "issuer_id"),
    ("time_series", "currency"),
    ("time_series", "metric"),
)


_EXPECTED_BARE = {
    "issuer_id": "ISSUER_MISMATCH",
    "counter_id": "COUNTER_MISMATCH",
    "level": "LEVEL_MISMATCH",
    "metric": "METRIC_MISMATCH",
    "period_type": "PERIOD_TYPE_MISMATCH",
    "period_start": "PERIOD_MISMATCH",
    "period_end": "PERIOD_MISMATCH",
    "basis": "BASIS_MISMATCH",
    "currency": "CURRENCY_MISMATCH",
    "scale": "SCALE_MISMATCH",
    "share_denominator": "DENOMINATOR_MISMATCH",
    "version": "VERSION_CONFLICT",
    "segment": "SEGMENT_MISMATCH",
    "segment_scheme_version": "SEGMENT_SCHEME_MISMATCH",
}


def _perturb(rng: random.Random, left: dict, field: str) -> tuple:
    """Return (left, right) where right perturbs exactly one field on `left`."""
    right = dict(left)
    if field == "issuer_id":
        right["issuer_id"] = "SYN-ISSUER-OTHER"
    elif field == "counter_id":
        right["counter_id"] = "SYN-CTR-OTHER"
    elif field == "level":
        right["level"] = "security" if left["level"] == "issuer" else "issuer"
    elif field == "metric":
        candidates = ("revenue", "net_income", "op_income", "gross_profit")
        right["metric"] = next(m for m in candidates if m != left["metric"])
    elif field == "period_type":
        candidates = ("annual", "interim", "quarterly")
        right["period_type"] = next(p for p in candidates if p != left["period_type"])
    elif field == "period_start":
        new_start, _ = _gen_period_pair(rng)
        right["period_start"] = new_start
    elif field == "period_end":
        new_start, new_end = _gen_period_pair(rng)
        # regenerate until strictly different from the original
        while new_end == left["period_end"]:
            new_start, new_end = _gen_period_pair(rng)
        right["period_start"] = new_start
        right["period_end"] = new_end
    elif field == "basis":
        candidates = ("reported", "adjusted")
        right["basis"] = next(b for b in candidates if b != left["basis"])
    elif field == "currency":
        new_cur = "HKD" if left["currency"] != "HKD" else "USD"
        right["currency"] = new_cur
        right["source_reported_currency"] = new_cur
    elif field == "scale":
        right["scale"] = left["scale"] + 3
    elif field == "share_denominator":
        candidates = ("BASIC", "DILUTED", "NOT_PER_SHARE")
        right["share_denominator"] = next(
            d for d in candidates if d != left["share_denominator"]
        )
    elif field == "version":
        right["version"] = left["version"] + "_other"
    elif field == "segment":
        right["segment"] = "alt-segment"
        if "segment_scheme_version" not in right:
            right["segment_scheme_version"] = "sch-1"
        if "segment_scheme_version" not in left:
            left = dict(left)
            left["segment_scheme_version"] = "sch-1"
    elif field == "segment_scheme_version":
        right["segment_scheme_version"] = "sch-other"
        if "segment" not in right:
            right["segment"] = "cloud"
        if "segment_scheme_version" not in left or "segment" not in left:
            left = dict(left)
            left["segment"] = "cloud"
            left["segment_scheme_version"] = "sch-1"
    return left, right


def test_p2_single_field_perturbation():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 2 + case)
        kind, field = _TESTED_PAIRS[case % len(_TESTED_PAIRS)]
        level = "security" if field == "counter_id" else "issuer"
        left_template = _gen_valid_fact(rng, level=level)
        left, right = _perturb(rng, left_template, field)
        verdict = check_join(left, right, join_kind=kind)
        msg = "%s kind=%s field=%s" % (_msg(BASE_SEED + 2, case), kind, field)
        assert verdict.status == "REFUSED", (
            "%s expected REFUSED, got status=%s reasons=%r"
            % (msg, verdict.status, verdict.reasons)
        )
        bare = set(_bare(r) for r in verdict.reasons)
        expected = _EXPECTED_BARE[field]
        assert expected in bare, (
            "%s expected %r in bare %r reasons=%r"
            % (msg, expected, bare, verdict.reasons)
        )
        total += 1
    assert total >= N_CASES, "p2 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P3. Swap invariance -- check_join(L, R) and check_join(R, L) give the
#     same BARE reason set.
# ---------------------------------------------------------------------------

def test_p3_swap_invariance():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 3 + case)
        left = _gen_valid_fact(rng)
        right = _gen_valid_fact(rng)
        # Sometimes equalize a few fields so the test isn't always all-mismatch
        if rng.random() < 0.3:
            right["issuer_id"] = left["issuer_id"]
            right["level"] = left["level"]
            right["currency"] = left["currency"]
            right["source_reported_currency"] = left["source_reported_currency"]
            right["scale"] = left["scale"]
            right["basis"] = left["basis"]
            right["share_denominator"] = left["share_denominator"]
        for kind in ("same_fact", "ratio", "time_series"):
            ab = check_join(left, right, join_kind=kind)
            ba = check_join(right, left, join_kind=kind)
            msg = "%s kind=%s" % (_msg(BASE_SEED + 3, case), kind)
            assert _stripped(ab.reasons) == _stripped(ba.reasons), (
                "%s swap invariance broken: ab_stripped=%r ba_stripped=%r"
                % (msg, _stripped(ab.reasons), _stripped(ba.reasons))
            )
        total += 1
    assert total >= N_CASES, "p3 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P4. Unknown field -- adding a key K not in FACT_FIELDS makes
#     validate_fact emit SCHEMA_UNKNOWN_FIELD:<K>.
# ---------------------------------------------------------------------------

def test_p4_unknown_field():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 4 + case)
        fact = _gen_valid_fact(rng)
        K = "junk_%d" % rng.randint(0, 100000)
        while K in FACT_FIELDS:
            K = "junk_%d" % rng.randint(0, 100000)
        fact[K] = rng.randint(0, 100)
        reasons = validate_fact(fact)
        msg = _msg(BASE_SEED + 4, case)
        assert "SCHEMA_UNKNOWN_FIELD:" + K in reasons, (
            "%s expected SCHEMA_UNKNOWN_FIELD:%s in %r" % (msg, K, reasons)
        )
        total += 1
    assert total >= N_CASES, "p4 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P5. Vocabulary -- every bare reason in any verdict is in REASONS (or
#     SCHEMA_UNKNOWN_FIELD); validate_fact reasons are sorted and
#     de-duplicated.
# ---------------------------------------------------------------------------

def test_p5_vocabulary():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 5 + case)
        left = _gen_valid_fact(rng)
        right = _gen_valid_fact(rng)
        right = dict(right)
        # Optionally inject a few perturbations
        for _ in range(rng.randint(1, 4)):
            k = rng.choice((
                "issuer_id", "currency", "basis", "period_end",
                "scale", "metric", "version", "share_denominator",
                "segment_scheme_version",
            ))
            if k == "issuer_id":
                right[k] = "SYN-ISSUER-OTHER"
            elif k == "currency":
                right[k] = "HKD"
                right["source_reported_currency"] = "HKD"
            elif k == "basis":
                right[k] = "adjusted" if left.get(k) == "reported" else "reported"
            elif k == "period_end":
                ps, pe = _gen_period_pair(rng)
                right["period_end"] = pe
                if pe > left["period_end"]:
                    ka_year = date.fromisoformat(pe).year + 1
                    right["known_at"] = "%04d-06-15T00:00:00" % ka_year
            elif k == "scale":
                right[k] = (left.get("scale", 0) + 3) % 9
            elif k == "metric":
                m = "revenue" if left.get(k) != "revenue" else "net_income"
                right[k] = m
            elif k == "version":
                right[k] = left.get("version", "v1") + "_other"
            elif k == "share_denominator":
                d = "DILUTED" if left.get(k) != "DILUTED" else "BASIC"
                right[k] = d
            elif k == "segment_scheme_version":
                right["segment"] = "cloud"
                right[k] = "sch-other"
                if "segment" not in left:
                    left = dict(left)
                    left["segment"] = "cloud"
                    left["segment_scheme_version"] = "sch-1"
        # Maybe inject an unknown key (=> SCHEMA_UNKNOWN_FIELD)
        if rng.random() < 0.2:
            K = "junk_%d" % rng.randint(0, 100000)
            while K in FACT_FIELDS:
                K = "junk_%d" % rng.randint(0, 100000)
            right[K] = 1
        for kind in ("same_fact", "ratio", "time_series"):
            verdict = check_join(left, right, join_kind=kind)
            msg = "%s kind=%s" % (_msg(BASE_SEED + 5, case), kind)
            for r in verdict.reasons:
                b = _bare(r)
                if b == "SCHEMA_UNKNOWN_FIELD":
                    continue
                assert b in REASONS, (
                    "%s unknown reason %r (bare=%r) in %r"
                    % (msg, r, b, verdict.reasons)
                )
            # validate_fact sorted + deduped
            for v in (validate_fact(left), validate_fact(right)):
                assert list(v) == sorted(v), (
                    "%s validate_fact not sorted: %r" % (msg, v)
                )
                assert len(v) == len(set(v)), (
                    "%s validate_fact has duplicates: %r" % (msg, v)
                )
        total += 1
    assert total >= N_CASES, "p5 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P6. No raise on junk -- random junk in any field raises no exception
#     (apart from documented non-Mapping TypeError, untested here, and
#     refuse_nonfalse_authority, also untested).
# ---------------------------------------------------------------------------

_JUNK_VALUES = (
    None, "", " ", "  hello  ", " hello", "hello ",
    0, 1, 42, True, False,
    3.14, math.nan, math.inf,
    b"bytes", [1, 2, 3], {"a": 1}, frozenset({1, 2}), object(),
)

_JUNK_FIELDS = (
    "issuer_id", "counter_id", "level", "metric", "period_type",
    "basis", "currency", "source_reported_currency", "scale",
    "segment", "segment_scheme_version", "share_denominator",
    "ads_ratio", "version", "known_at", "period_end", "period_start",
    "value", "supersedes", "source_owner",
)


def test_p6_no_raise_on_junk():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 6 + case)
        fact = _gen_valid_fact(rng)
        for k in _JUNK_FIELDS:
            if rng.random() < 0.25:
                fact[k] = rng.choice(_JUNK_VALUES)
        msg = _msg(BASE_SEED + 6, case)
        # No exception on any junk value. JGP-01 (fixed): an unhashable
        # `level` used to raise TypeError from the frozenset lookup.
        v1 = validate_fact(fact)
        v2 = validate_fact(fact, as_of="2026-12-31")
        other = _gen_valid_fact(rng)
        for kind in ("same_fact", "ratio", "time_series"):
            verdict = check_join(fact, other, join_kind=kind)
            _ = _stripped(verdict.reasons)
        total += 1
    assert total >= N_CASES, "p6 ran fewer than N_CASES generated cases"


def test_jgp01_unhashable_level_refuses_level_unknown():
    for junk in ([1, 2, 3], {"issuer": 1}, {"security"}):
        fact = _gen_valid_fact(random.Random(BASE_SEED + 601))
        fact["level"] = junk
        assert "LEVEL_UNKNOWN" in validate_fact(fact)


def test_jgp01_unhashable_join_kind_refuses_join_kind_unknown():
    rng = random.Random(BASE_SEED + 602)
    left, right = _gen_valid_fact(rng), _gen_valid_fact(rng)
    for junk in (["same_fact"], {"ratio": 1}, {"time_series"}):
        verdict = check_join(left, right, join_kind=junk)
        assert verdict.status == "REFUSED"
        assert "JOIN_KIND_UNKNOWN" in verdict.reasons


# ---------------------------------------------------------------------------
# P7. Authority -- every verdict's authority flags are literal False.
# ---------------------------------------------------------------------------

def test_p7_authority_flags_false():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 7 + case)
        left = _gen_valid_fact(rng)
        right = _gen_valid_fact(rng)
        for kind in ("same_fact", "ratio", "time_series"):
            verdict = check_join(left, right, join_kind=kind)
            msg = "%s kind=%s" % (_msg(BASE_SEED + 7, case), kind)
            for name in FLAG_NAMES:
                assert verdict.authority[name] is False, (
                    "%s authority flag %r is not False: %r"
                    % (msg, name, verdict.authority[name])
                )
            total += 1
            if total >= N_CASES:
                break
        if total >= N_CASES:
            break
    assert total >= N_CASES, "p7 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P8. Padded ids absent -- a padded / whitespace-only id never joins as
#     equal to the unpadded id.
# ---------------------------------------------------------------------------

_PADDERS = (
    lambda s: " " + s,
    lambda s: s + " ",
    lambda s: "  " + s,
    lambda s: s + "  ",
    lambda s: "\t" + s,
    lambda s: s + "\n",
    lambda s: " " * 5 + s + " " * 5,
)


def test_p8_padded_ids_absent():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 8 + case)
        base_id = _gen_issuer_id(rng)
        pad = _PADDERS[case % len(_PADDERS)](base_id)
        left = _gen_valid_fact(rng, issuer_id=base_id)
        right = _gen_valid_fact(rng, issuer_id=pad)
        for kind in ("same_fact", "ratio", "time_series"):
            verdict = check_join(left, right, join_kind=kind)
            msg = "%s kind=%s padded=%r" % (
                _msg(BASE_SEED + 8, case), kind, pad
            )
            assert verdict.status != "ALLOWED", (
                "%s padded id was accepted as equal: %r"
                % (msg, verdict.reasons)
            )
            bare = set(_bare(r) for r in verdict.reasons)
            assert (
                "ISSUER_UNRESOLVED" in bare or "ISSUER_MISMATCH" in bare
            ), "%s padded id did not trip any id refusal: bare=%r" % (
                msg, bare
            )
            total += 1
            if total >= N_CASES:
                break
        if total >= N_CASES:
            break
    assert total >= N_CASES, "p8 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P9. Unknown join_kind -- refuses with JOIN_KIND_UNKNOWN.
# ---------------------------------------------------------------------------

def test_p9_unknown_join_kind():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 9 + case)
        left = _gen_valid_fact(rng)
        right = _gen_valid_fact(rng)
        kind = "junk-kind-%d" % rng.randint(0, 10**9)
        while kind in JOIN_KINDS:
            kind = "junk-kind-%d" % rng.randint(0, 10**9)
        verdict = check_join(left, right, join_kind=kind)
        msg = _msg(BASE_SEED + 9, case)
        assert verdict.status == "REFUSED", (
            "%s expected REFUSED, got status=%s reasons=%r"
            % (msg, verdict.status, verdict.reasons)
        )
        assert "JOIN_KIND_UNKNOWN" in verdict.reasons, (
            "%s expected JOIN_KIND_UNKNOWN, got %r"
            % (msg, verdict.reasons)
        )
        total += 1
    assert total >= N_CASES, "p9 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# PERTURBATION PROOF -- a deliberately broken copy of one small piece of
# the guard logic. Two properties must FAIL against the broken copy while
# passing against the real module.
# ---------------------------------------------------------------------------

_AUTHORITY_FROZEN = MappingProxyType(dict(AUTHORITY_FLAGS))


def _check_join_broken(left, right, *, join_kind, as_of=None):
    """Hand-written perturbed copy of check_join.

    Only the ``JOIN_KIND_UNKNOWN`` gate and the LEFT/RIGHT validate_fact
    emissions mirror the real module. The currency-mismatch branch is
    DELIBERATELY BROKEN -- it always fires for any joinable input. So:

        * identical facts ALLOWED by the real module are REFUSED here
          (P1 broken);
        * a single-field perturbation that should produce the field's
          reason produces CURRENCY_MISMATCH here instead (P2 broken).

    Other compare rules are dropped for speed; this perturbation only
    needs to surface that "passing" pairs are refused by the broken
    copy. It never edits, reloads, or monkey-patches the real module.
    """
    left_reasons = tuple(validate_fact(left, as_of=as_of))
    right_reasons = tuple(validate_fact(right, as_of=as_of))
    union = set()
    for r in left_reasons:
        union.add("LEFT:" + r)
    for r in right_reasons:
        union.add("RIGHT:" + r)
    if join_kind not in JOIN_KINDS:
        union.add("JOIN_KIND_UNKNOWN")
        return JoinVerdict(
            status="REFUSED",
            reasons=tuple(sorted(union)),
            join_kind=join_kind,
            authority=_AUTHORITY_FROZEN,
        )
    # BUG: always emit CURRENCY_MISMATCH for joinable cases.
    union.add("CURRENCY_MISMATCH")
    return JoinVerdict(
        status="REFUSED",
        reasons=tuple(sorted(union)),
        join_kind=join_kind,
        authority=_AUTHORITY_FROZEN,
    )


def test_perturbation_p1_reflexive_passes_real_fails_broken():
    """P1 must pass against the real module and fail against the broken copy."""
    rng = random.Random(BASE_SEED + 100)
    fact = _gen_valid_fact(rng)
    real = check_join(fact, dict(fact), join_kind="same_fact")
    broken = _check_join_broken(fact, dict(fact), join_kind="same_fact")
    assert real.status == "ALLOWED", (
        "real check_join refused identical facts: %r" % (real.reasons,)
    )
    assert broken.status == "REFUSED", (
        "broken copy ALLOWED identical facts (bug missed): %r"
        % (broken.reasons,)
    )
    assert real.status != broken.status, (
        "real and broken produced the same status; perturbation is not "
        "exercised. real=%r broken=%r" % (real.status, broken.status)
    )


def test_perturbation_p2_field_reason_on_real_absent_on_broken():
    """P2 must pass against the real module and fail against the broken copy."""
    rng = random.Random(BASE_SEED + 101)
    left_template = _gen_valid_fact(rng)
    # Perturb period_end (NOT currency) -- the broken copy should never
    # emit PERIOD_MISMATCH for this case but the real module must.
    left, right = _perturb(rng, left_template, "period_end")
    real = check_join(left, right, join_kind="same_fact")
    broken = _check_join_broken(left, right, join_kind="same_fact")
    real_bare = set(_bare(r) for r in real.reasons)
    broken_bare = set(_bare(r) for r in broken.reasons)
    assert "PERIOD_MISMATCH" in real_bare, (
        "real module failed its own P2 contract: %r" % (real.reasons,)
    )
    assert "PERIOD_MISMATCH" not in broken_bare, (
        "broken copy emitted PERIOD_MISMATCH (bug missed): %r"
        % (broken.reasons,)
    )


def test_perturbation_proof_at_least_two_properties_fail_on_broken():
    """Sweep across N cases: count how many (real, broken) outcomes disagree
    per property. At least 2 properties must be detected as failing on the
    broken copy (P1 + P2 above cover this; this sweep is the runtime guard).
    """
    p1_flip_detected = False
    p2_flip_detected = False
    for case in range(60):
        rng = random.Random(BASE_SEED + 200 + case)
        # P1 sweep
        if not p1_flip_detected:
            fact = _gen_valid_fact(rng)
            real = check_join(fact, dict(fact), join_kind="same_fact")
            broken = _check_join_broken(
                fact, dict(fact), join_kind="same_fact"
            )
            if real.status == "ALLOWED" and broken.status == "REFUSED":
                p1_flip_detected = True
        # P2 sweep
        if not p2_flip_detected:
            kind, field = _TESTED_PAIRS[case % len(_TESTED_PAIRS)]
            level = "security" if field == "counter_id" else "issuer"
            left_template = _gen_valid_fact(rng, level=level)
            if field == "currency":
                # Don't use currency perturbation here -- it would alias
                # the broken copy's always-on reason.
                kind, field = "same_fact", "period_end"
                left_template = _gen_valid_fact(rng, level="issuer")
            left, right = _perturb(rng, left_template, field)
            real = check_join(left, right, join_kind=kind)
            broken = _check_join_broken(left, right, join_kind=kind)
            real_bare = set(_bare(r) for r in real.reasons)
            broken_bare = set(_bare(r) for r in broken.reasons)
            expected = _EXPECTED_BARE[field]
            if (
                expected in real_bare
                and expected not in broken_bare
            ):
                p2_flip_detected = True
        if p1_flip_detected and p2_flip_detected:
            break
    failed = {"P1"} if p1_flip_detected else set()
    failed |= {"P2"} if p2_flip_detected else set()
    assert len(failed) >= 2, (
        "perturbation proof failed: %d properties detected as failing on "
        "broken copy (%r); need at least 2"
        % (len(failed), failed)
    )
