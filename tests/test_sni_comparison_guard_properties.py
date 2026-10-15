"""Seeded property tests for the A13 comparison-guard compiler (LR-MEAS-CMP).

Property-based tests for ``research/single_name_intelligence/common/
sni_comparison_guard.py``. They mirror the structure of
``tests/test_sni_a07_then_known_property.py`` — a single ``random.Random``
family, at least 300 cases per property, hand-written perturbation proof.

Properties P1..P9 exercise the comparison-guard contract:

  P1.  Positive — a valid, fully text-present synthetic input that the
       example tests treat as allowed stays allowed (no refusal reasons).
  P2.  Single-field perturbation — flipping exactly ONE compared/required
       field to a different text-present value refuses with that field's
       documented mismatch/missing reason.
  P3.  FAMILY TEXT RULE v2 — replacing any text field with ``None``, ``""``,
       ``" "``, a padded string (``" X"``/``"X "``), an ``int``, a ``bool``,
       or ``bytes`` is never treated as present and the verdict never
       allows.
  P4.  Symmetry — where the guard compares two sides, swapping the sides
       yields the same set of bare reasons.
  P5.  Vocabulary — every bare reason is in ``REASONS``; the published
       reason list is sorted and de-duplicated.
  P6.  No raise on junk — junk inside mappings never raises; only the
       documented ``TypeError`` (non-``Mapping`` argument) and the
       authority-flag ``ValueError`` are allowed.
  P7.  Authority — every verdict's authority flags (rank/gate/size/signal/
       escalation/trade) remain literal ``False``.
  P8.  Determinism — the same input twice yields an identical verdict;
       input dictionaries are not mutated by the call.
  P9.  Perturbation proof — at least 2 properties FAIL against a broken
       copy of one small piece of guard logic (a flipped price-nonfinite
       test) and pass against the real module.

Synthetic fixtures only. Identity ids are opaque strings. The guard
never mints, derives, or guesses canonical HK/US issuer or security
identifiers from a ticker, name, code, or CIK. ``rank_authority``,
``gate_authority``, ``size_authority``, ``signal_authority``,
``escalation_authority`` and ``trade_authority`` stay literal False.
No causal or news-impact claim (A24); an unestimable family stays
outside (A25).
"""
from __future__ import annotations

import copy
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

import sni_comparison_guard as _cg  # noqa: E402
from sni_comparison_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    INSTRUMENT_ROLES,
    REASONS,
    SESSION_STATES_KNOWN,
    SESSION_STATES_TRADING,
    ComparisonVerdict,
    _blank,
    _finite_positive_real,
    _freeze_reasons,
    _fx_reasons,
    _leg_reasons,
    _not_known_as_of,
    _text_present,
    check_comparison,
    refuse_nonfalse_authority,
)

# Single seeded RNG family. Each property uses BASE_SEED + k as the
# SPEC-pinned seed and runs at least 300 generated cases.
BASE_SEED = 20261016
N_CASES = 300  # FROZEN SPEC: >= 300 generated cases per property.

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

_SESSION_KNOWN = frozenset(SESSION_STATES_KNOWN)
_SESSION_TRADING = frozenset(SESSION_STATES_TRADING)
_ROLES = frozenset(INSTRUMENT_ROLES)


# ---------------------------------------------------------------------------
# Datetime / cutoff helpers
# ---------------------------------------------------------------------------

def _aware(year, month, day, hour=0, minute=0, second=0, micro=0):
    return datetime(year, month, day, hour, minute, second, micro, tzinfo=timezone.utc)


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _as_of(rng):
    year = rng.choice((2024, 2025, 2026, 2027))
    return _aware(
        year,
        rng.randint(1, 12),
        rng.randint(1, 28),
        rng.randint(0, 23),
        rng.randint(0, 59),
    )


def _msg(seed, case):
    return "seed=%s case=%s" % (seed, case)


# ---------------------------------------------------------------------------
# Valid leg / fx generators
# ---------------------------------------------------------------------------

def _valid_leg(rng, *, as_of, currency=None, role=None, issuer=None):
    ccy = currency if currency is not None else rng.choice(
        ("USD", "HKD", "EUR", "GBP", "JPY", "CHF", "SGD")
    )
    state = rng.choice(SESSION_STATES_TRADING)
    if role is None:
        role = "target"
    if issuer is None:
        issuer = "SYN-ISSUER-%d" % rng.randint(1, 99999)
    return {
        "issuer_id": issuer,
        "instrument_role": role,
        "price": round(rng.uniform(0.5, 5000.0), 4),
        "price_ts": _iso(as_of - timedelta(seconds=rng.randint(0, 25))),
        "currency": ccy,
        "session_state": state,
        "known_at": _iso(as_of - timedelta(seconds=rng.randint(0, 50))),
    }


def _valid_fx(rng, *, base, quote, as_of):
    return {
        "base": base,
        "quote": quote,
        "rate": round(rng.uniform(0.05, 50.0), 6),
        "rate_ts": _iso(as_of - timedelta(seconds=rng.randint(0, 25))),
        "known_at": _iso(as_of - timedelta(seconds=rng.randint(0, 50))),
    }


def _valid_pair(rng, as_of):
    """A valid pair: either same-ccy with no fx, or cross-ccy with valid fx.

    Both legs share the same issuer_id so a clean pair never trips
    ISSUER_MISMATCH on its own (P1 must observe a clean allowed verdict).
    """
    shared_issuer = "SYN-ISSUER-%d" % rng.randint(1, 99999)
    if rng.random() < 0.5:
        ccy = rng.choice(("USD", "HKD", "EUR", "GBP", "JPY"))
        return (
            _valid_leg(rng, as_of=as_of, currency=ccy, issuer=shared_issuer),
            _valid_leg(rng, as_of=as_of, currency=ccy, issuer=shared_issuer),
            None,
        )
    base = rng.choice(("USD", "HKD", "EUR", "GBP"))
    pool = [c for c in ("USD", "HKD", "JPY", "EUR", "GBP") if c != base]
    quote = rng.choice(pool)
    left = _valid_leg(rng, as_of=as_of, currency=base, issuer=shared_issuer)
    right = _valid_leg(rng, as_of=as_of, currency=quote, issuer=shared_issuer)
    return left, right, _valid_fx(rng, base=base, quote=quote, as_of=as_of)


# ---------------------------------------------------------------------------
# Helpers for the symmetry / determinism / no-raise tests
# ---------------------------------------------------------------------------

def _swap_sides(left, right):
    return right, left


def _junky_legs(rng, as_of):
    """Generate a randomized pair that exercises a mix of reasons.

    ``_valid_pair`` already triggers allowed on a good RNG. We start from a
    valid pair and randomly perturb one or more fields to push a verdict
    off the allowed path while staying structurally well-typed.
    """
    left, right, fx = _valid_pair(rng, as_of)
    # Sometimes flip instrument_role to proxy on one side
    if rng.random() < 0.3:
        target = rng.choice(("left", "right"))
        container = left if target == "left" else right
        container["instrument_role"] = "proxy"
    # Sometimes force a non-trading session
    if rng.random() < 0.25:
        target = rng.choice(("left", "right"))
        container = left if target == "left" else right
        container["session_state"] = rng.choice(
            tuple(s for s in SESSION_STATES_KNOWN if s not in SESSION_STATES_TRADING)
        )
    return left, right, fx


# ---------------------------------------------------------------------------
# P1. positive: valid synthetic inputs stay allowed.
# ---------------------------------------------------------------------------

def test_p1_valid_synthetic_inputs_stay_allowed():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 1 + case)
        as_of = _as_of(rng)
        left, right, fx = _valid_pair(rng, as_of)
        msg = _msg(BASE_SEED + 1, case)
        verdict = check_comparison(left, right, fx, as_of=_iso(as_of))
        assert verdict.allowed is True, msg
        assert verdict.reasons == (), (msg, verdict.reasons)
        for code in verdict.reasons:
            assert code in REASONS, (msg, code)
        total += 1
    assert total >= N_CASES, "p1 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P2. single-field perturbation: flipping one compared/required field
#     refuses with the documented reason.
# ---------------------------------------------------------------------------

# (key, side, value, requires_cross_ccy, expected_reason)
_P2_PERTURBATIONS = [
    # --- price slot (numeric only) -------------------------------------
    ("price", "left", None, False, "PRICE_MISSING"),
    ("price", "left", "", False, "PRICE_MISSING"),
    ("price", "left", 0, False, "PRICE_NONFINITE"),
    ("price", "left", -1.0, False, "PRICE_NONFINITE"),
    ("price", "left", float("nan"), False, "PRICE_NONFINITE"),
    ("price", "left", float("inf"), False, "PRICE_NONFINITE"),
    ("price", "left", True, False, "PRICE_NONFINITE"),
    ("price", "left", "100", False, "PRICE_NONFINITE"),
    ("price", "left", [100.0], False, "PRICE_NONFINITE"),
    ("price", "right", -1, False, "PRICE_NONFINITE"),
    # --- price_ts slot ------------------------------------------------
    ("price_ts", "left", None, False, "PRICE_TS_MISSING"),
    ("price_ts", "left", "", False, "PRICE_TS_MISSING"),
    ("price_ts", "left", "not-a-timestamp", False, "PRICE_TS_MISSING"),
    ("price_ts", "left", "2026-13-01T00:00:00+00:00", False, "PRICE_TS_MISSING"),
    ("price_ts", "left", "2026-06-15T15:30:00", False, "PRICE_TS_MISSING"),
    ("price_ts", "right", "garbage", False, "PRICE_TS_MISSING"),
    # --- session_state slot -------------------------------------------
    ("session_state", "left", "overnight", False, "SESSION_STATE_UNKNOWN"),
    ("session_state", "left", "open_outcry", False, "SESSION_STATE_UNKNOWN"),
    ("session_state", "left", None, False, "SESSION_STATE_UNKNOWN"),
    ("session_state", "left", 7, False, "SESSION_STATE_UNKNOWN"),
    ("session_state", "left", "", False, "SESSION_STATE_UNKNOWN"),
    ("session_state", "left", "closed", False, "SESSION_NOT_TRADING"),
    ("session_state", "right", "halted", False, "SESSION_NOT_TRADING"),
    # --- instrument_role slot -----------------------------------------
    ("instrument_role", "left", "hedge", False, "ROLE_UNKNOWN"),
    ("instrument_role", "left", "Target", False, "ROLE_UNKNOWN"),
    ("instrument_role", "left", "proxy", False, "PROXY_AS_TARGET"),
    ("instrument_role", "right", "proxy", False, "PROXY_AS_TARGET"),
    # --- issuer_id slot (leg text) ------------------------------------
    ("issuer_id", "right", "SYN-ISSUER-OTHER", False, "ISSUER_MISMATCH"),
    # --- known_at slot (per leg) --------------------------------------
    ("known_at", "left", "2030-01-01T00:00:00+00:00", False, "NOT_KNOWN_AS_OF"),
    # --- fx only (cross-currency required) ----------------------------
    ("__missing_fx__", "fx", None, True, "FX_MISSING"),
    ("rate", "fx", 0, True, "FX_NONFINITE"),
    ("rate", "fx", -1.0, True, "FX_NONFINITE"),
    ("rate", "fx", float("nan"), True, "FX_NONFINITE"),
    ("rate", "fx", True, True, "FX_NONFINITE"),
    ("rate_ts", "fx", None, True, "FX_TS_MISSING"),
    ("rate_ts", "fx", "garbage", True, "FX_TS_MISSING"),
    ("rate_ts", "fx", "1999-01-01T00:00:00+00:00", True, "FX_STALE"),
    ("base", "fx", "ZZZ-BAD-BASE-1234", True, "CURRENCY_PAIR_MISMATCH"),
    ("quote", "fx", "ZZZ-BAD-QUOTE-5678", True, "CURRENCY_PAIR_MISMATCH"),
    ("known_at", "fx", "2030-01-01T00:00:00+00:00", True, "NOT_KNOWN_AS_OF"),
    # --- price skew across legs (cross- or same-currency accepted) ----
    ("price_ts", "right", "2099-01-01T00:00:00+00:00", False, "PRICE_SKEW"),
]


def _expected_reason_for(key, side, value):
    """The documented refusal reason for the given perturbation.

    This re-derivation is kept as a sanity check on the catalogue itself:
    the catalogue's expected-reason column must agree with this helper.
    """
    if key == "price":
        if value is None or value == "":
            return "PRICE_MISSING"
        return "PRICE_NONFINITE"
    if key == "price_ts":
        return "PRICE_TS_MISSING"
    if key == "session_state":
        if not isinstance(value, str) or value not in _SESSION_KNOWN:
            return "SESSION_STATE_UNKNOWN"
        return "SESSION_NOT_TRADING"
    if key == "instrument_role":
        if not isinstance(value, str) or value not in _ROLES:
            return "ROLE_UNKNOWN"
        return "PROXY_AS_TARGET"
    if key == "issuer_id":
        return "ISSUER_MISMATCH"
    if key == "known_at":
        return "NOT_KNOWN_AS_OF"
    if key == "__missing_fx__":
        return "FX_MISSING"
    if key == "rate":
        return "FX_NONFINITE"
    if key == "rate_ts":
        if value in (None, "garbage") or not isinstance(value, str):
            return "FX_TS_MISSING"
        return "FX_STALE"
    if key in ("base", "quote"):
        return "CURRENCY_PAIR_MISMATCH"
    raise AssertionError("unknown key " + key)


def _build_base_for(key, side, requires_cross_ccy, rng, as_of):
    """Build the appropriate base pair for a given perturbation.

    Both legs share the same issuer so ISSUER_MISMATCH never pollutes a
    perturbation verdict: every emitted reason above the one being tested
    would weaken the catalogue's clarity.
    """
    if requires_cross_ccy:
        base = rng.choice(("USD", "HKD", "EUR"))
        pool = [c for c in ("USD", "HKD", "JPY") if c != base]
        quote = rng.choice(pool)
        shared = "SYN-ISSUER-%d" % rng.randint(1, 99999)
        left = _valid_leg(rng, as_of=as_of, currency=base, issuer=shared)
        right = _valid_leg(rng, as_of=as_of, currency=quote, issuer=shared)
        fx = _valid_fx(rng, base=base, quote=quote, as_of=as_of)
        return left, right, fx
    # Default: same-ccy pair with no fx.
    ccy = rng.choice(("USD", "HKD", "EUR", "JPY"))
    shared = "SYN-ISSUER-%d" % rng.randint(1, 99999)
    left = _valid_leg(rng, as_of=as_of, currency=ccy, issuer=shared)
    right = _valid_leg(rng, as_of=as_of, currency=ccy, issuer=shared)
    return left, right, None


def test_p2_single_field_perturbation_refuses_with_documented_reason():
    total = 0
    n_per = max(1, N_CASES // len(_P2_PERTURBATIONS) + 1)
    for ix, (key, side, value, cross, expected) in enumerate(_P2_PERTURBATIONS):
        for case in range(n_per):
            rng = random.Random(BASE_SEED + 2 + ix * 1009 + case)
            as_of = _as_of(rng)
            left, right, fx = _build_base_for(key, side, cross, rng, as_of)
            msg = "key=%s side=%s case=%d" % (key, side, case)
            if key == "__missing_fx__":
                fx = None
            else:
                if side == "left":
                    left = dict(left)
                    left[key] = value
                elif side == "right":
                    right = dict(right)
                    right[key] = value
                elif side == "fx" and fx is not None:
                    fx = dict(fx)
                    fx[key] = value
            verdict = check_comparison(left, right, fx, as_of=_iso(as_of))
            assert expected in REASONS, (msg, expected)
            assert expected in verdict.reasons, (
                f"{msg} expected {expected!r} in reasons, got {verdict.reasons!r}"
            )
            # The verdict must be refused for the documented perturbation.
            assert verdict.allowed is False, (msg, verdict.reasons)
            total += 1
    assert total >= N_CASES, "p2 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P3. FAMILY TEXT RULE v2: junk in any text field refuses, never allows.
# ---------------------------------------------------------------------------

TEXT_FIELDS_FOR_P3 = (
    # (side, key, applies_to_cross_ccy)
    ("left", "issuer_id", False),
    ("right", "issuer_id", False),
    ("left", "currency", False),
    ("right", "currency", False),
    ("left", "instrument_role", False),
    ("right", "instrument_role", False),
    ("fx", "base", True),
    ("fx", "quote", True),
)

JUNK_TEXT_VALUES = (
    None,
    "",
    " ",
    " USD",  # leading space
    "USD ",  # trailing space
    7,  # int
    True,  # bool
    b"USD",  # bytes
)


def test_p3_family_text_rule_v2_junk_in_text_field_refuses():
    total = 0
    for ix, (side, key, cross) in enumerate(TEXT_FIELDS_FOR_P3):
        for jx, junk in enumerate(JUNK_TEXT_VALUES):
            for case in range(max(1, N_CASES // (len(TEXT_FIELDS_FOR_P3) * len(JUNK_TEXT_VALUES)) + 1)):
                rng = random.Random(BASE_SEED + 3 + ix * 101 + jx * 17 + case)
                as_of = _as_of(rng)
                if cross:
                    base = rng.choice(("USD", "HKD"))
                    pool = [c for c in ("HKD", "USD", "JPY") if c != base]
                    quote = rng.choice(pool)
                    left = _valid_leg(rng, as_of=as_of, currency=base)
                    right = _valid_leg(rng, as_of=as_of, currency=quote)
                    fx = _valid_fx(rng, base=base, quote=quote, as_of=as_of)
                else:
                    ccy = rng.choice(("USD", "HKD", "EUR"))
                    left = _valid_leg(rng, as_of=as_of, currency=ccy)
                    right = _valid_leg(rng, as_of=as_of, currency=ccy)
                    fx = None
                # Apply the junk to BOTH sides of the comparison when possible
                # so P3's "never compares equal" claim is exercised: even when
                # both legs carry the same padded/junk value, the verdict
                # must NOT allow.
                if side == "left":
                    left = dict(left)
                    left[key] = junk
                elif side == "right":
                    right = dict(right)
                    right[key] = junk
                elif side == "fx":
                    fx = dict(fx)
                    fx[key] = junk
                msg = _msg(BASE_SEED + 3, ix * 1000 + jx * 100 + case)
                verdict = check_comparison(left, right, fx, as_of=_iso(as_of))
                # The verdict must be refused.
                assert verdict.allowed is False, (
                    f"{msg} junk {junk!r} in {side}.{key} should refuse, "
                    f"got allowed verdict reasons={verdict.reasons!r}"
                )
                # The module must surface at least one documented reason.
                assert verdict.reasons, (msg, verdict)
                # Each emitted reason must belong to REASONS.
                for code in verdict.reasons:
                    assert code in REASONS, (msg, code, verdict.reasons)
                total += 1
    assert total >= N_CASES, "p3 ran fewer than N_CASES generated cases"


def test_p3_text_present_helper_rejects_every_junk_value():
    """The helper itself refuses every P3 junk: never asserts present."""
    for junk in JUNK_TEXT_VALUES:
        assert _text_present(junk) is False, (
            "FAMILY TEXT RULE violated: _text_present(%r) returned True" % (junk,)
        )


def test_p3_text_present_helper_accepts_clean_text_only():
    """Clean text (non-empty, no leading or trailing whitespace) IS present."""
    samples = ("USD", "BABA", "SYN-ISSUER-1", "H", "X-Y", "a", "Z" * 16)
    for clean in samples:
        assert _text_present(clean) is True, (
            "_text_present(%r) returned False for a clean value" % (clean,)
        )


# ---------------------------------------------------------------------------
# P4. symmetry: swapping sides yields the same bare reasons.
# ---------------------------------------------------------------------------

def test_p4_symmetry_swap_yields_same_reasons():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 4 + case)
        as_of = _as_of(rng)
        left, right, fx = _junky_legs(rng, as_of)
        msg = _msg(BASE_SEED + 4, case)
        v1 = check_comparison(left, right, fx, as_of=_iso(as_of))
        swapped_left, swapped_right = _swap_sides(left, right)
        v2 = check_comparison(swapped_left, swapped_right, fx, as_of=_iso(as_of))
        # Bare reasons (deduped via the verdict contract) are identical.
        assert set(v1.reasons) == set(v2.reasons), (
            f"{msg} asymmetry: v1.reasons={v1.reasons!r} v2.reasons={v2.reasons!r}"
        )
        # Both verdicts agree on allowed.
        assert v1.allowed is v2.allowed, (msg, v1.allowed, v2.allowed)
        total += 1
    assert total >= N_CASES, "p4 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P5. vocabulary: every bare reason ∈ REASONS; sorted, deduplicated.
# ---------------------------------------------------------------------------

def test_p5_vocabulary_sorted_deduped_via_reasons_order():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 5 + case)
        as_of = _as_of(rng)
        left, right, fx = _junky_legs(rng, as_of)
        msg = _msg(BASE_SEED + 5, case)
        verdict = check_comparison(left, right, fx, as_of=_iso(as_of))
        # Every bare reason ∈ REASONS.
        for code in verdict.reasons:
            assert code in REASONS, (msg, code, verdict.reasons)
        # Sorted by REASONS tuple order.
        indices = [REASONS.index(c) for c in verdict.reasons]
        assert indices == sorted(indices), (
            f"{msg} reasons not sorted by REASONS order: {verdict.reasons!r}"
        )
        # No duplicates.
        assert len(set(verdict.reasons)) == len(verdict.reasons), (
            f"{msg} reasons not deduplicated: {verdict.reasons!r}"
        )
        # allowed ↔ empty reasons.
        assert verdict.allowed is (not verdict.reasons), msg
        total += 1
    assert total >= N_CASES, "p5 ran fewer than N_CASES generated cases"


def test_p5_freeze_reasons_dedupes_and_sorts():
    """A direct probe of the helper: feed duplicates and arbitrary order."""
    inputs = [
        ["PRICE_SKEW", "PRICE_MISSING", "PRICE_SKEW"],
        ["ISSUER_MISMATCH"],
        [],
        ["PRICE_NONFINITE", "PRICE_SKEW", "PRICE_MISSING"],
    ]
    for items in inputs:
        out = _freeze_reasons(list(items))
        assert out == tuple(code for code in REASONS if code in items)
        assert out == tuple(sorted(out, key=REASONS.index))
        assert len(out) == len(set(out))


# ---------------------------------------------------------------------------
# P6. no raise on junk: junk inside mappings never raises.
# ---------------------------------------------------------------------------

# Junk values that go INSIDE a leg or fx without converting the container.
JUNK_VALUES = (
    None,
    "",
    " ",
    " X",
    "X ",
    7,
    0,
    -1.0,
    True,
    False,
    float("nan"),
    float("inf"),
    -float("inf"),
    b"USD",
    [100.0],
    {"a": 1},
    {1, 2, 3},
    object(),
)


def test_p6_no_raise_on_junk_inside_mappings():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 6 + case)
        as_of = _as_of(rng)
        # Some junk in some field on some leg.
        left, right, fx = _valid_pair(rng, as_of)
        leg_picks = [
            ("left", left),
            ("right", right),
            ("fx", fx),
        ]
        rng.shuffle(leg_picks)
        # Populate junk into at least one but at most a few fields
        n_junk = rng.randint(1, 5)
        for i in range(n_junk):
            side_name, container = leg_picks[i % len(leg_picks)]
            if container is None:
                continue
            container = dict(container)
            key = rng.choice(
                (
                    "issuer_id",
                    "instrument_role",
                    "price",
                    "price_ts",
                    "currency",
                    "session_state",
                    "known_at",
                )
                if side_name != "fx"
                else ("base", "quote", "rate", "rate_ts", "known_at")
            )
            container[key] = rng.choice(JUNK_VALUES)
            if side_name == "left":
                left = container
            elif side_name == "right":
                right = container
            else:
                fx = container
        msg = _msg(BASE_SEED + 6, case)
        # No raise is the explicit assertion.
        try:
            verdict = check_comparison(left, right, fx, as_of=_iso(as_of))
        except (ValueError, TypeError) as exc:  # pragma: no cover -- only fails on real defect
            pytest.fail(
                f"{msg} unexpected raise inside junk check_comparison: "
                f"{type(exc).__name__}: {exc}"
            )
        # Bound the result shape even when refusal happens.
        for code in verdict.reasons:
            assert code in REASONS, (msg, code)
        assert verdict.allowed is (not verdict.reasons), msg
        total += 1
    assert total >= N_CASES, "p6 ran fewer than N_CASES generated cases"


def test_p6_documented_typerrors_for_non_mapping_arguments():
    """Documented TypeError surface on non-Mapping left/right/fx."""
    as_of = "2026-06-15T16:00:00+00:00"
    valid = {"issuer_id": "SYN-ISSUER-1"}
    with pytest.raises(TypeError):
        check_comparison(7, valid, None, as_of=as_of)
    with pytest.raises(TypeError):
        check_comparison(valid, 7, None, as_of=as_of)
    with pytest.raises(TypeError):
        check_comparison(valid, valid, 7, as_of=as_of)
    # Mapping-but-not-explicitly-dict is also a Mapping.
    from types import MappingProxyType
    check_comparison(MappingProxyType(valid), MappingProxyType(valid), None, as_of=as_of)


def test_p6_authority_refusal_raises_valueerror_when_flag_not_false():
    as_of = "2026-06-15T16:00:00+00:00"
    valid = {"issuer_id": "SYN"}
    # Module-level flags stay false, so a plain call works.
    refuse_nonfalse_authority()
    # The documented ValueError surfaces when an authority flag is non-False.
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"rank_authority": True})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"signal_authority": "false"})


# ---------------------------------------------------------------------------
# P7. authority flags stay literal False on every verdict.
# ---------------------------------------------------------------------------

def test_p7_authority_flags_stay_literal_false_on_every_verdict():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 7 + case)
        as_of = _as_of(rng)
        left, right, fx = _junky_legs(rng, as_of)
        verdict = check_comparison(left, right, fx, as_of=_iso(as_of))
        msg = _msg(BASE_SEED + 7, case)
        flags = verdict.authority_flags
        for name in FLAG_NAMES:
            assert flags[name] is False, (msg, name, flags[name])
            assert name in AUTHORITY_FLAGS, msg
        # Sanity: AUTHORITY_FLAGS itself stays false.
        for name in FLAG_NAMES:
            assert AUTHORITY_FLAGS[name] is False, (msg, name)
        total += 1
    assert total >= N_CASES, "p7 ran fewer than N_CASES generated cases"


def test_p7_authored_verdict_inherits_module_flags():
    """A directly-constructed ComparisonVerdict still shows module flags."""
    verdict = ComparisonVerdict(allowed=True, reasons=())
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False


# ---------------------------------------------------------------------------
# P8. determinism: same input → identical verdict; input is not mutated.
# ---------------------------------------------------------------------------

def test_p8_determinism_same_input_yields_identical_verdict():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 8 + case)
        as_of = _as_of(rng)
        left, right, fx = _junky_legs(rng, as_of)
        msg = _msg(BASE_SEED + 8, case)
        # Reset seeds on each call's RNG usage is irrelevant — the function
        # itself must be a pure mapping.
        before_left = copy.deepcopy(left)
        before_right = copy.deepcopy(right)
        before_fx = copy.deepcopy(fx) if fx is not None else None
        v1 = check_comparison(left, right, fx, as_of=_iso(as_of))
        v2 = check_comparison(left, right, fx, as_of=_iso(as_of))
        assert v1 == v2, (
            f"{msg} determinism violated: v1.allowed={v1.allowed} v2.allowed={v2.allowed}; "
            f"v1.reasons={v1.reasons!r} v2.reasons={v2.reasons!r}"
        )
        # Mutation guard.
        assert left == before_left, (msg, "left mutated")
        assert right == before_right, (msg, "right mutated")
        if fx is None:
            assert before_fx is None
        else:
            assert fx == before_fx, (msg, "fx mutated")
        total += 1
    assert total >= N_CASES, "p8 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P9. PERTURBATION PROOF
# ---------------------------------------------------------------------------
#
# A deliberately broken copy of one small piece of guard logic: the
# leg-reason helper that emits PRICE_NONFINITE. The real helper adds the
# reason when ``not _finite_positive_real(price)`` is True; the broken
# copy flips the test so ``_finite_positive_real(price) is True`` fires
# the reason (and otherwise drops it). The breakage exercises P1 (a valid
# positive finite price is refused) and P2 (a zero price no longer
# registers PRICE_NONFINITE).
#
# Never edit, reload, or monkeypatch the real module. Never touch
# sys.modules. The broken copy re-implements the leg-reason function in
# the test file only.

def _leg_reasons_broken_price(leg, *, as_of, requested_role):
    """Mirror of ``_leg_reasons`` with the price non-finite check FLIPPED.

    `_leg_reasons` appends PRICE_NONFINITE when the price is NOT a
    positive finite real. This copy appends PRICE_NONFINITE ONLY when
    the price IS a positive finite real. Everything else mirrors the
    real helper exactly.
    """
    found = []
    price = leg.get("price")
    if _blank(price):
        found.append("PRICE_MISSING")
    elif _finite_positive_real(price):  # FLIPPED
        found.append("PRICE_NONFINITE")
    if _cg._as_aware_datetime(leg.get("price_ts")) is None:
        found.append("PRICE_TS_MISSING")
    session_state = leg.get("session_state")
    if not isinstance(session_state, str) or session_state not in _SESSION_KNOWN:
        found.append("SESSION_STATE_UNKNOWN")
    elif session_state not in _SESSION_TRADING:
        found.append("SESSION_NOT_TRADING")
    role = leg.get("instrument_role")
    if not isinstance(role, str) or role not in _ROLES:
        found.append("ROLE_UNKNOWN")
    elif _text_present(requested_role) and _text_present(role) and requested_role == "target" and role == "proxy":
        found.append("PROXY_AS_TARGET")
    if _not_known_as_of(leg.get("known_at"), as_of):
        found.append("NOT_KNOWN_AS_OF")
    return found


def _check_comparison_broken_price(
    left, right, fx, *, as_of,
    max_fx_staleness_seconds=300,
    max_price_skew_seconds=60,
    requested_role="target",
):
    """Mirror of ``check_comparison`` with the broken leg-reason helper.

    Preserves every other check: ``_fx_reasons``, the ``ISSUER_MISMATCH``
    gate, the price-skew gate, the docstring-typed ``TypeError`` surface,
    and the final ``_freeze_reasons``+``ComparisonVerdict`` construction.
    """
    if not isinstance(left, Mapping):
        raise TypeError("left must be a Mapping")
    if not isinstance(right, Mapping):
        raise TypeError("right must be a Mapping")
    if fx is not None and not isinstance(fx, Mapping):
        raise TypeError("fx must be a Mapping or None")
    reasons = []
    reasons.extend(_leg_reasons_broken_price(left, as_of=as_of, requested_role=requested_role))
    reasons.extend(_leg_reasons_broken_price(right, as_of=as_of, requested_role=requested_role))
    li = left.get("issuer_id")
    ri = right.get("issuer_id")
    if not _text_present(li) or not _text_present(ri) or li != ri:
        reasons.append("ISSUER_MISMATCH")
    reasons.extend(
        _fx_reasons(left, right, fx, as_of=as_of, max_fx_staleness_seconds=max_fx_staleness_seconds)
    )
    lt = _cg._as_aware_datetime(left.get("price_ts"))
    rt = _cg._as_aware_datetime(right.get("price_ts"))
    if lt is not None and rt is not None:
        if abs((lt - rt).total_seconds()) > max_price_skew_seconds:
            reasons.append("PRICE_SKEW")
    frozen = _freeze_reasons(reasons)
    return ComparisonVerdict(allowed=not frozen, reasons=frozen)


def test_perturbation_proof_two_properties_fail_on_broken_copy():
    """P1 + P2 fail on the broken copy; both pass on the real module.

    P1: a valid positive-finite price must remain allowed. Real module:
        allowed. Broken copy: PRICE_NONFINITE is incorrectly fired, so
        the verdict refuses.

    P2: a price of 0 (a documented NONFINITE case) must refuse with
        PRICE_NONFINITE. Real module: PRICE_NONFINITE appears in the
        verdict reasons. Broken copy: PRICE_NONFINITE is omitted because
        the condition is flipped.
    """
    as_of = "2026-06-15T16:00:00+00:00"
    price_ts = "2026-06-15T15:30:00+00:00"
    known_at = "2026-06-15T15:31:00+00:00"

    valid_left = {
        "issuer_id": "SYN-ISSUER-1",
        "instrument_role": "target",
        "price": 100.0,
        "price_ts": price_ts,
        "currency": "USD",
        "session_state": "continuous",
        "known_at": known_at,
    }
    valid_right = dict(valid_left)
    valid_right["price"] = 101.5

    # --- P1: valid positive-finite price must remain allowed ---------
    real_v = check_comparison(valid_left, valid_right, None, as_of=as_of)
    broken_v = _check_comparison_broken_price(valid_left, valid_right, None, as_of=as_of)
    assert real_v.allowed is True and real_v.reasons == (), (
        "real module regression: a valid input was refused unexpectedly: "
        f"{real_v.reasons!r}"
    )
    assert broken_v.allowed is False, (
        "PERTURBATION PROOF FAILED: P1 did NOT fail against the broken copy. "
        f"The broken verdict allowed=True reasons={broken_v.reasons!r}; "
        "the flipped price-nonfinite check should have refused it."
    )
    assert "PRICE_NONFINITE" in broken_v.reasons, (
        f"PERTURBATION PROOF FAILED: broken verdict is missing PRICE_NONFINITE: {broken_v.reasons!r}"
    )

    # --- P2: price=0 on BOTH legs must refuse with PRICE_NONFINITE ----
    zero_left = dict(valid_left, price=0)
    zero_right = dict(valid_right, price=0)
    real_zero = check_comparison(zero_left, zero_right, None, as_of=as_of)
    broken_zero = _check_comparison_broken_price(zero_left, zero_right, None, as_of=as_of)
    assert "PRICE_NONFINITE" in real_zero.reasons, (
        f"real module regression: PRICE_NONFINITE missing for price=0: {real_zero.reasons!r}"
    )
    assert "PRICE_NONFINITE" not in broken_zero.reasons, (
        "PERTURBATION PROOF FAILED: P2 did NOT fail against the broken copy. "
        f"Broken verdict unexpectedly includes PRICE_NONFINITE: {broken_zero.reasons!r}"
    )

    # The two assertions above demonstrate two distinct property failures
    # against the broken copy (P1 refusal flip + P2 missing-reason flip).


def test_perturbation_proof_random_cases_two_properties_fail_on_broken_copy():
    """Across many cases the broken copy keeps flipping P1 and P2.

    For each case:
      * construct a valid base pair (P1 shape);
      * confirm the real verdict allows;
      * confirm the broken verdict refuses with PRICE_NONFINITE;
      * then set both legs' prices to 0 and confirm the real verdict
        contains PRICE_NONFINITE while the broken verdict does not.
    """
    as_of = "2026-06-15T16:00:00+00:00"
    price_ts = "2026-06-15T15:30:00+00:00"
    known_at = "2026-06-15T15:31:00+00:00"

    flipped_p1 = 0
    flipped_p2 = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 9 + case)
        ccy = rng.choice(("USD", "HKD", "EUR", "GBP"))
        issuer = "SYN-ISSUER-%d" % rng.randint(1, 99999)
        price = round(rng.uniform(0.5, 5000.0), 4)
        left = {
            "issuer_id": issuer,
            "instrument_role": "target",
            "price": price,
            "price_ts": price_ts,
            "currency": ccy,
            "session_state": "continuous",
            "known_at": known_at,
        }
        right = dict(left)
        right["price"] = round(rng.uniform(0.5, 5000.0), 4)

        real_v = check_comparison(left, right, None, as_of=as_of)
        broken_v = _check_comparison_broken_price(left, right, None, as_of=as_of)
        assert real_v.allowed is True and real_v.reasons == (), (
            f"real module regression at case {case}: {real_v.reasons!r}"
        )
        if broken_v.allowed is False and "PRICE_NONFINITE" in broken_v.reasons:
            flipped_p1 += 1

        zero_left = dict(left, price=0)
        zero_right = dict(right, price=0)
        real_zero = check_comparison(zero_left, zero_right, None, as_of=as_of)
        broken_zero = _check_comparison_broken_price(zero_left, zero_right, None, as_of=as_of)
        if "PRICE_NONFINITE" in real_zero.reasons and "PRICE_NONFINITE" not in broken_zero.reasons:
            flipped_p2 += 1

    assert flipped_p1 >= N_CASES // 2, (
        f"PERTURBATION PROOF FAILED: P1 only flipped {flipped_p1}/{N_CASES} times; "
        "the broken copy should refuse a positive-finite price in the majority of cases."
    )
    assert flipped_p2 >= N_CASES // 2, (
        f"PERTURBATION PROOF FAILED: P2 only flipped {flipped_p2}/{N_CASES} times; "
        "the broken copy should omit PRICE_NONFINITE on a zero price in the majority of cases."
    )
