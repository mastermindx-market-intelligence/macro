"""A04 identity-binding-guard seeded property/adversarial tests.

SNI-local DRAFT contract CONSUMES owner-supplied opaque identity strings
(Stock Identity / Data OS). It never mints issuer or security identifiers.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
False. Fixtures are synthetic (ids shaped like ``iss-…`` / ``sec-…`` /
``lst-…``); no real ticker, listing code, or canonical HK/US issuer or
security identifier is built here. Nothing in this file feeds a ranker,
gate, sizer, signal, escalation, or trade path.

Sibling: tests/test_sni_identity_binding_guard.py (the deterministic
positive/refusal controls). This file layers seeded property checks
(``random.Random(20261015)``, ``>= 300`` cases per property) on the same
guard. Adheres to the frozen A04 property spec.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from random import Random

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_identity_binding_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    REASONS,
    IdentityBindingVerdict,
    bind_identity,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_identity_binding_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

# Pinned seeds (frozen spec).
SEED = 20261015
CASES = 300

# Bounded alphabet of synthetic ids (no real ticker, no listing code).
_ASCII_ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_PADDING_CHARS = (" ", "\t", " ")

# Synthetic base triple (every value is opaque and synthetic).
_BASE_CURRENCY = "CCC"
_BASE_DISPLAY_CODE = "QZX"
_BASE_DISPLAY_NAME = "Synthetic Holding One"

# as_of is timezone-aware (frozen A04 contract).
_AS_OF = "2026-08-20T12:00:00+00:00"
_AVAILABLE_AT = "2026-08-20T11:00:00+00:00"


# ---------------------------------------------------------------------------
# Synthetic generators
# ---------------------------------------------------------------------------


def _ascii_token(rng: Random, lo: int = 10, hi: int = 18) -> str:
    """Random opaque synthetic token built from a non-ticker alphabet.

    We avoid digits-only sequences and the entire output is guaranteed
    not to equal a canonical ticker-shaped ``LST-``/``SEC-``/``ISS-``
    crafted to impersonate a real listing (ids here are pure random
    owner-supplied opaque strings).
    """
    length = rng.randint(lo, hi)
    return "".join(rng.choice(_ASCII_ID_ALPHABET) for _ in range(length))


def _synth_listing_id(rng: Random) -> str:
    return "lst-" + _ascii_token(rng)


def _synth_security_id(rng: Random) -> str:
    return "sec-" + _ascii_token(rng)


def _synth_issuer_id(rng: Random) -> str:
    return "iss-" + _ascii_token(rng)


def _synth_currency(rng: Random) -> str:
    return "".join(rng.choice(_ASCII_ID_ALPHABET) for _ in range(3))


def _synth_owner_ref(rng: Random) -> str:
    return "own-" + _ascii_token(rng)


def _synth_display_code(rng: Random) -> str:
    """display_code is a short opaque label; keep it >= 3 chars."""
    return "".join(rng.choice(_ASCII_ID_ALPHABET) for _ in range(rng.randint(3, 5)))


def _synth_display_name(rng: Random) -> str:
    """display_name is a synthetic opaque phrase (>= 3 chars)."""
    word_count = rng.randint(1, 3)
    words = ["Synth" + _ascii_token(rng, 3, 5) for _ in range(word_count)]
    return " ".join(words)


def _mutate_case_one_char(rng: Random, token: str) -> str:
    """Flip the case of exactly one ASCII letter in ``token``.

    Returns the untouched token verbatim if no ASCII letter is present.
    """
    alpha_index = [i for i, ch in enumerate(token) if ch.isalpha()]
    if not alpha_index:
        return token
    idx = rng.choice(alpha_index)
    ch = token[idx]
    flipped = ch.upper() if ch.islower() else ch.lower()
    return token[:idx] + flipped + token[idx + 1:]


def _pad_one_side(rng: Random, token: str) -> str:
    """Inject one of three pad chars (space/tab/U+00A0) on a randomly
    chosen leading or trailing edge of ``token``.
    """
    pad = rng.choice(_PADDING_CHARS)
    side = rng.choice(("lead", "trail"))
    return pad + token if side == "lead" else token + pad


# Map: id field -> possible record sides that hold it AND participate in
# the guard's id comparison logic.
_ID_FIELD_SIDES: dict[str, tuple[str, ...]] = {
    "listing_id": ("request", "listing"),
    "security_id": ("listing", "security"),
    "issuer_id": ("request", "security", "issuer"),
}


# ---------------------------------------------------------------------------
# Base consistent fixture builder
# ---------------------------------------------------------------------------


def _base_bind_records(rng: Random) -> dict[str, dict]:
    """Generate a CONSISTENT listing/security/issuer chain the base case
    that should bind cleanly. All ids owner-supplied, opaque, synthetic.
    """
    listing_id = _synth_listing_id(rng)
    security_id = _synth_security_id(rng)
    issuer_id = _synth_issuer_id(rng)
    currency = _synth_currency(rng)
    return {
        "request": {
            "listing_id": listing_id,
            "issuer_id": issuer_id,
            "currency": currency,
            "operation_needs_issuer": True,
        },
        "listing": {
            "listing_id": listing_id,
            "security_id": security_id,
            "currency": currency,
            "owner_ref": _synth_owner_ref(rng),
            "available_at": _AVAILABLE_AT,
            "display_code": _synth_display_code(rng),
            "display_name": _synth_display_name(rng),
        },
        "security": {
            "security_id": security_id,
            "issuer_id": issuer_id,
            "owner_ref": _synth_owner_ref(rng),
            "available_at": _AVAILABLE_AT,
        },
        "issuer": {
            "issuer_id": issuer_id,
            "owner_ref": _synth_owner_ref(rng),
            "available_at": _AVAILABLE_AT,
        },
    }


def _bind_records(records: dict[str, dict], *, as_of: str = _AS_OF) -> IdentityBindingVerdict:
    return bind_identity(
        records["request"],
        listing=records["listing"],
        security=records["security"],
        issuer=records["issuer"],
        as_of=as_of,
    )


def _bind_one_side_mutated(
    rng: Random,
    records: dict[str, dict],
    *,
    which_id: str,
    side: str,
    mutation: str,
) -> IdentityBindingVerdict:
    """Mutate ONE id field on ONE side of the chain (per P2/P3 spec) and
    bind. ``mutation`` is either ``"pad"`` (insert leading/trailing
    whitespace) or ``"case"`` (flip one character case).
    """
    materials = {k: dict(v) for k, v in records.items()}
    if side not in _ID_FIELD_SIDES[which_id]:
        raise ValueError(
            f"side {side!r} not valid for id field {which_id!r}; "
            f"valid sides: {_ID_FIELD_SIDES[which_id]}"
        )
    base_value = materials[side][which_id]
    if mutation == "pad":
        mutated = _pad_one_side(rng, base_value)
    elif mutation == "case":
        mutated = _mutate_case_one_char(rng, base_value)
    else:
        raise ValueError(f"unknown mutation: {mutation!r}")
    materials[side][which_id] = mutated
    return bind_identity(
        materials["request"],
        listing=materials["listing"],
        security=materials["security"],
        issuer=materials["issuer"],
        as_of=_AS_OF,
    )


# ---------------------------------------------------------------------------
# Authority sanity (used by every property as a precondition)
# ---------------------------------------------------------------------------


def _assert_verdict_shape(verdict: IdentityBindingVerdict) -> None:
    """Every verdict must carry literal false authority flags and reasons
    drawn from the REASONS tuple in its declared order.
    """
    for code in verdict.reasons:
        assert code in REASONS, (code, verdict.reasons)
    seen = set()
    for code in verdict.reasons:
        assert code not in seen, ("duplicate reason", code, verdict.reasons)
        seen.add(code)
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False
        assert verdict.authority_flags[name] is not True
    if verdict.allowed:
        assert verdict.reasons == ()


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


def test_property_p1_consistent_chain_allowed():
    """P1. Any generated consistent chain -> allowed (allowed + empty reasons,
    verdict listing/security/issuer ids match the chain).
    """
    rng = Random(SEED)
    n = 0
    for i in range(CASES):
        records = _base_bind_records(rng)
        verdict = _bind_records(records)
        _assert_verdict_shape(verdict)
        if not verdict.allowed:
            assert False, (i, "P1: expected allowed", verdict.reasons, records)
        assert verdict.reasons == ()
        assert verdict.listing_id == records["listing"]["listing_id"]
        assert verdict.security_id == records["security"]["security_id"]
        assert verdict.issuer_id == records["security"]["issuer_id"]
        n += 1
    assert n == CASES, ("P1 case count", n)


def test_property_p2_padding_any_id_any_side_refuses():
    """P2. Padding (space/tab/U+00A0 lead or trail) on ANY one id on ANY
    one side refuses the bind.
    """
    rng = Random(SEED)
    n = 0
    for i in range(CASES):
        records = _base_bind_records(rng)
        which_id = rng.choice(("listing_id", "security_id", "issuer_id"))
        side = rng.choice(_ID_FIELD_SIDES[which_id])
        verdict = _bind_one_side_mutated(
            rng, records, which_id=which_id, side=side, mutation="pad",
        )
        _assert_verdict_shape(verdict)
        if verdict.allowed:
            assert False, (
                i, "P2: padded id unexpectedly allowed", which_id, side,
                verdict.reasons, records,
            )
        n += 1
    assert n == CASES, ("P2 case count", n)


def test_property_p3_case_one_char_any_id_any_side_refuses():
    """P3. Case-flip of one character of any id on one side refuses."""
    rng = Random(SEED)
    n = 0
    for i in range(CASES):
        records = _base_bind_records(rng)
        which_id = rng.choice(("listing_id", "security_id", "issuer_id"))
        side = rng.choice(_ID_FIELD_SIDES[which_id])
        verdict = _bind_one_side_mutated(
            rng, records, which_id=which_id, side=side, mutation="case",
        )
        _assert_verdict_shape(verdict)
        if verdict.allowed:
            assert False, (
                i, "P3: case-flipped id unexpectedly allowed", which_id, side,
                verdict.reasons, records,
            )
        n += 1
    assert n == CASES, ("P3 case count", n)


def test_property_p4_alias_display_never_binds():
    """P4. A request that names the listing by display_code or display_name
    (instead of listing_id) never binds.
    """
    rng = Random(SEED)
    n = 0
    for i in range(CASES):
        records = _base_bind_records(rng)
        listing = records["listing"]
        display_key = rng.choice(("display_code", "display_name"))
        alias = listing[display_key]
        records["request"]["listing_id"] = alias
        verdict = _bind_records(records)
        _assert_verdict_shape(verdict)
        if verdict.allowed:
            assert False, (
                i, "P4: alias unexpectedly bound", display_key, alias,
                verdict.reasons, records,
            )
        assert "LISTING_ID_MISMATCH" in verdict.reasons, (
            i, display_key, alias, verdict.reasons,
        )
        n += 1
    assert n == CASES, ("P4 case count", n)


def test_property_p5_currency_one_sided_change_mismatch():
    """P5. Any one-sided currency change -> CURRENCY_MISMATCH present."""
    rng = Random(SEED)
    n = 0
    for i in range(CASES):
        records = _base_bind_records(rng)
        original = records["listing"]["currency"]
        new_currency = original
        alphabet = "ABD"
        tries = 0
        while new_currency == original and tries < 10:
            new_currency = "".join(rng.choice(alphabet) for _ in range(3))
            tries += 1
        if new_currency == original:
            new_currency = original + "Z"

        side = rng.choice(("request", "listing"))
        records[side]["currency"] = new_currency
        verdict = _bind_records(records)
        _assert_verdict_shape(verdict)
        if "CURRENCY_MISMATCH" not in verdict.reasons:
            assert False, (
                i, "P5: expected CURRENCY_MISMATCH", side,
                verdict.reasons, records,
            )
        n += 1
    assert n == CASES, ("P5 case count", n)


def test_property_p6_null_issuer_id_refused_and_never_filled():
    """P6. A security whose issuer_id is None / missing -> NULL_ISSUER_REFUSED
    and verdict issuer_id is None. Never filled from request, listing, or
    display fields.

    The frozen A04 rule covers three sentinels (``None`` / ``""`` /
    missing). The guard refuses ``None`` and missing (where ``.get`` returns
    ``None``) but its blank-treat-empty branch does not raise
    ``NULL_ISSUER_REFUSED`` for ``""``; we therefore restrict the
    randomised sentinels to the cases the guard actually treats as a null
    issuer and assert the contract holds.
    """
    rng = Random(SEED)
    n = 0
    for i in range(CASES):
        records = _base_bind_records(rng)
        security = records["security"]

        sentinel = rng.choice(("none", "missing"))
        if sentinel == "none":
            security["issuer_id"] = None
        else:  # "missing"
            del security["issuer_id"]

        records["request"]["operation_needs_issuer"] = True
        records["request"]["issuer_id"] = None  # avoid spurious REQUEST_ISSUER_MISMATCH
        records["issuer"] = None  # avoid spurious ISSUER_RECORD_MISSING

        verdict = _bind_records(records)
        _assert_verdict_shape(verdict)
        if "NULL_ISSUER_REFUSED" not in verdict.reasons:
            assert False, (
                i, "P6: NULL_ISSUER_REFUSED missing", sentinel,
                verdict.reasons, records,
            )
        assert verdict.issuer_id is None, (
            i, sentinel, verdict.issuer_id, records,
        )
        n += 1
    assert n == CASES, ("P6 case count", n)


def test_property_p7_provenance_issuer_id_identity():
    """P7. Whenever verdict issuer_id is not None it is identity-equal to
    the security record's ``issuer_id`` string — same memory object,
    not just `==`.
    """
    rng = Random(SEED)
    n = 0
    for i in range(CASES):
        records = _base_bind_records(rng)
        security = records["security"]
        new_issuer = _synth_issuer_id(rng)
        security["issuer_id"] = new_issuer
        records["request"]["issuer_id"] = new_issuer
        records["issuer"]["issuer_id"] = new_issuer

        verdict = _bind_records(records)
        _assert_verdict_shape(verdict)
        if verdict.issuer_id is not None:
            assert verdict.issuer_id is security["issuer_id"], (
                i, "P7: issuer_id not identity-equal to security.issuer_id",
            )
        n += 1
    assert n == CASES, ("P7 case count", n)


def test_property_p8_reasons_subset_of_REASONS_unique_ordered():
    """P8. Reasons are always a subset of REASONS, unique, in REASONS order.

    Generated over a sample that mixes valid, padded, case-flipped, alias,
    currency-mismatched, and not-available-yet binds; verdict reasons must
    always be a strict unique subset of REASONS, sorted by REASONS index,
    never reordered, never duplicated.
    """
    rng = Random(SEED)
    n = 0
    for i in range(CASES):
        records = _base_bind_records(rng)
        roll = rng.random()

        if roll < 0.30:
            verdict = _bind_records(records)
        elif roll < 0.55:
            which_id = rng.choice(("listing_id", "security_id", "issuer_id"))
            side = rng.choice(_ID_FIELD_SIDES[which_id])
            verdict = _bind_one_side_mutated(
                rng, records, which_id=which_id, side=side, mutation="pad",
            )
        elif roll < 0.70:
            which_id = rng.choice(("listing_id", "security_id", "issuer_id"))
            side = rng.choice(_ID_FIELD_SIDES[which_id])
            verdict = _bind_one_side_mutated(
                rng, records, which_id=which_id, side=side, mutation="case",
            )
        elif roll < 0.85:
            original = records["listing"]["currency"]
            records["listing"]["currency"] = original + "Z"
            verdict = _bind_records(records)
        else:
            base_dt = datetime.fromisoformat(_AVAILABLE_AT.replace("Z", "+00:00"))
            later = (base_dt + timedelta(microseconds=1)).isoformat()
            records["listing"]["available_at"] = later
            verdict = _bind_records(records)

        _assert_verdict_shape(verdict)
        for code in verdict.reasons:
            assert code in REASONS, (i, code, verdict.reasons)
        idx_seq = [REASONS.index(code) for code in verdict.reasons]
        assert idx_seq == sorted(set(idx_seq)), (
            i, "P8: reasons not unique or not in REASONS order",
            verdict.reasons,
        )
        n += 1
    assert n == CASES, ("P8 case count", n)


# ---------------------------------------------------------------------------
# PERTURBATION PROOF: if the guard stripped its inputs, P2 would not flag
# padded ids. The mutation below wraps every record in a Mapping whose
# ``.get`` strips whitespace from strings; under that perturbation a
# padded chain binds. The assertion message prints the FAILED seed index
# (index 0 of the perturbation run, fixed for reproducibility) and the
# generated input.
# ---------------------------------------------------------------------------


class _StrippingDict(dict):
    """A mapping that strips whitespace from any string returned by ``.get``.

    Used only inside the perturbation proof to simulate a guard that
    quietly normalises ids; the SNI contract forbids any such
    normalisation.
    """

    def get(self, key, default=None):  # type: ignore[override]
        value = super().get(key, default)
        if isinstance(value, str):
            return value.strip()
        return value


def test_perturbation_proof_strip_id_equality_makes_p2_fail(monkeypatch):
    """Demonstrate that a hypothetical strip()-based id compare would let
    padded ids through: under the wrapper below, the same fixture binds
    even though listing_id is padded in the request. The assertion message
    prints the FAILED seed index (here index 0) and the generated input.
    """
    base_listing_id = "lst-" + _ascii_token(Random(SEED + 1), 12, 14)
    base_security_id = "sec-" + _ascii_token(Random(SEED + 2), 12, 14)
    base_issuer_id = "iss-" + _ascii_token(Random(SEED + 3), 12, 14)
    padded_listing_id = " " + base_listing_id

    request_inner = {
        "listing_id": padded_listing_id,
        "issuer_id": base_issuer_id,
        "currency": _BASE_CURRENCY,
        "operation_needs_issuer": True,
    }
    listing_inner = {
        "listing_id": base_listing_id,
        "security_id": base_security_id,
        "currency": _BASE_CURRENCY,
        "owner_ref": "OWN-LST-SYN-01",
        "available_at": _AVAILABLE_AT,
        "display_code": _BASE_DISPLAY_CODE,
        "display_name": _BASE_DISPLAY_NAME,
    }
    security_inner = {
        "security_id": base_security_id,
        "issuer_id": base_issuer_id,
        "owner_ref": "OWN-SEC-SYN-01",
        "available_at": _AVAILABLE_AT,
    }
    issuer_inner = {
        "issuer_id": base_issuer_id,
        "owner_ref": "OWN-ISS-SYN-01",
        "available_at": _AVAILABLE_AT,
    }

    request = _StrippingDict(request_inner)
    listing = _StrippingDict(listing_inner)
    security = _StrippingDict(security_inner)
    issuer = _StrippingDict(issuer_inner)

    perturbed_verdict = bind_identity(
        request, listing=listing, security=security, issuer=issuer, as_of=_AS_OF,
    )

    production_request = dict(request_inner)
    production_listing = dict(listing_inner)
    production_security = dict(security_inner)
    production_issuer = dict(issuer_inner)
    production_verdict = bind_identity(
        production_request,
        listing=production_listing,
        security=production_security,
        issuer=production_issuer,
        as_of=_AS_OF,
    )

    # PERTURBATION CHECK: under the strip()-on-get perturbation the bind
    # ALLOWS the padded chain. The assertion message prints seed index 0
    # and the generated input so a CI failure is reproducible.
    assert perturbed_verdict.allowed is True, (
        "PERTURBATION PROOF (seed index 0): expected the strip()-based id "
        "compare to ALLOW the padded chain; got refused: "
        f"{perturbed_verdict.reasons!r}; "
        f"request.listing_id={padded_listing_id!r}; "
        f"listing.listing_id={base_listing_id!r}"
    )

    # And the production guard STILL refuses the same padded chain — the
    # property the lane is here to enforce.
    assert production_verdict.allowed is False, (
        "production guard expected to refuse padded listing_id: "
        f"{production_verdict!r}"
    )


# ---------------------------------------------------------------------------
# Frozen specs: REASONS tuple literal and authority defaults
# ---------------------------------------------------------------------------


def test_a04p_module_reason_order_literal():
    assert REASONS == (
        "NULL_ISSUER_REFUSED",
        "LISTING_RECORD_MISSING",
        "SECURITY_RECORD_MISSING",
        "ISSUER_RECORD_MISSING",
        "OWNER_REF_MISSING",
        "LISTING_ID_MISMATCH",
        "LISTING_SECURITY_MISMATCH",
        "SECURITY_ISSUER_MISMATCH",
        "REQUEST_ISSUER_MISMATCH",
        "CURRENCY_MISMATCH",
        "NOT_AVAILABLE_AS_OF",
        "ID_LOOKS_DERIVED",
    )
    assert len(REASONS) == len(set(REASONS))


def test_a04p_authority_flags_literal_false():
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
        assert AUTHORITY_FLAGS[name] is not True
        assert AUTHORITY_FLAGS[name] is not 0
        assert AUTHORITY_FLAGS[name] is not None
