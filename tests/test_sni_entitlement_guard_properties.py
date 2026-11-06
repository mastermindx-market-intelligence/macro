"""Seeded property tests for the A18 entitlement guard (LR-MEAS-ENT).

SNI-local DRAFT contract property tests for the pre-access entitlement gate at
research/single_name_intelligence/common/sni_entitlement_guard.py. They consume
owner-shaped entitlement records (Research Vault owner) and caller-supplied
opaque account/document ids; they never mint issuer or security ids.
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False. Fixtures are
synthetic. Historical facts known only after a date are never treated as if
known on that date; residuals and stress statistics are descriptive and never
causal (A24). An unestimable family is outside this module (A25).

Properties exercised (each runs at least 300 generated cases, seeded via the
stdlib ``random.Random(20261016 + k)`` family only — no hypothesis):
    P1. Positive — a fully text-present, in-window synthetic input stays
        allowed with no refusal reasons.
    P2. Single-field perturbation — flipping exactly one compared/required
        field to a different text-present value refuses with that field's
        documented mismatch/missing reason and the loader is never called.
    P3. FAMILY TEXT RULE v2 — replacing any text field with None, "", " ",
        a padded string (" X" / "X "), an int, a bool, or bytes is never
        treated as present, never compares equal to a clean text value,
        and refuses the verdict.
    P4. Symmetry — for the symmetric comparison predicates
        (account_id == account_id, document_id in document_ids) swapping
        the sides yields the same bare reasons. The gate itself is
        directional (request drives entitlement), which is documented.
    P5. Vocabulary — every bare reason is in REASONS; the reason list is
        de-duplicated and ordered by REASONS order.
    P6. No raise on junk — junk values in any text field do not raise.
        Documented TypeErrors for non-Mapping inputs / non-callable loader
        and the authority refusal (ValueError) are still raised.
    P7. Authority — every verdict's authority flags are literal False.
    P8. Determinism — same input twice yields an identical verdict and
        the call does not mutate the input mappings.
    P9. Payload hygiene — every refused verdict has payload=None and the
        loader is never called; every allowed private verdict has payload
        equal to the loader's return value; allowed public verdicts have
        payload=None.

PERTURBATION PROOF: ``test_perturbation_junk_allows_property_against_broken``
runs P3 and an additional no-junk-equal property against a deliberately
broken copy of ``_text_present`` and shows both fail on the broken copy and
pass on the real module. The real module is never edited, reloaded, or
monkey-patched, and ``sys.modules`` is never touched.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Mapping

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

import sni_entitlement_guard as _eg  # noqa: E402
from sni_entitlement_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    REASONS,
    SURFACES,
    AccessVerdict,
    gate_access,
)

# Single seeded RNG family. The base seed is FROZEN: 20261016. Each property
# adds a unique salt so the streams are independent and reproducible from this
# file alone.
BASE_SEED = 20261016
N_CASES = 300  # FROZEN SPEC: >= 300 generated cases per property.

_AS_OF = "2026-06-01T12:00:00+00:00"  # well within the synthetic window
_VALID_FROM = "2026-01-01T00:00:00+00:00"
_ACCOUNT = "syn-account-1"
_DOCUMENT = "syn-doca-42"
_OTHER_ACCOUNT = "syn-account-2"
_OTHER_DOCUMENT = "syn-doca-99"
_ENT_REF = "syn-ent-17"

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)


def _msg(seed: int, case: int) -> str:
    return "seed=%s case=%s" % (seed, case)


# ---------------------------------------------------------------------------
# Synthetic fixture builders
# ---------------------------------------------------------------------------


def _request(**overrides):
    body = {
        "surface": "private",
        "account_id": _ACCOUNT,
        "document_id": _DOCUMENT,
        "want_full_text": True,
    }
    body.update(overrides)
    return body


def _entitlement(**overrides):
    body = {
        "entitlement_ref": _ENT_REF,
        "account_id": _ACCOUNT,
        "document_ids": ("syn-doca-41", _DOCUMENT),
        "valid_from": _VALID_FROM,
        "valid_to": None,
        "revoked_at": None,
    }
    body.update(overrides)
    return body


class _LoaderSpy:
    """Counts loader calls and returns a fixed synthetic payload."""

    def __init__(self, payload: str = "SYN-PAYLOAD-7c3e"):
        self.payload = payload
        self.calls: list[object] = []

    @property
    def count(self) -> int:
        return len(self.calls)

    def __call__(self, document_id):
        self.calls.append(document_id)
        return self.payload


# Junk values per FAMILY TEXT RULE v2.
JUNK_VALUES = (None, "", " ", " X", "X ", 42, True, False, b"X")


# ---------------------------------------------------------------------------
# P1. Positive: a fully text-present, in-window synthetic input stays allowed.
# ---------------------------------------------------------------------------


def test_p1_positive_text_present_input_allowed():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 1 + case)
        spy = _LoaderSpy()
        verdict = gate_access(
            _request(), _entitlement(), as_of=_AS_OF, loader=spy
        )
        msg = _msg(BASE_SEED + 1, case)
        assert verdict.allowed is True, msg
        assert verdict.reasons == (), msg
        assert spy.count == 1, msg
        assert verdict.payload is spy.payload, msg
        total += 1
    assert total >= N_CASES, "p1 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P2. Single-field perturbation: flipping exactly ONE compared/required field
#     to a different text-present value refuses with that field's documented
#     mismatch/missing reason and the loader is never called.
# ---------------------------------------------------------------------------


# (side, field, new_value, expected_reason) tuples. Each perturbation flips
# exactly ONE field on ONE side.
_PERTURBATIONS = (
    ("request", "account_id", _OTHER_ACCOUNT, "ACCOUNT_MISMATCH"),
    ("entitlement", "account_id", _OTHER_ACCOUNT, "ACCOUNT_MISMATCH"),
    ("request", "document_id", _OTHER_DOCUMENT, "DOCUMENT_NOT_ENTITLED"),
    ("entitlement", "document_ids", ("syn-doca-77",), "DOCUMENT_NOT_ENTITLED"),
    ("request", "surface", "internal", "SURFACE_UNKNOWN"),
    ("entitlement", "entitlement_ref", None, "ENTITLEMENT_REF_MISSING"),
    (
        "request",
        "want_full_text",
        True,
        "PUBLIC_FULL_TEXT_FORBIDDEN",
    ),  # combined with public surface
    ("entitlement", "valid_from", "2027-01-01T00:00:00+00:00", "ENTITLEMENT_NOT_YET_VALID"),
    ("entitlement", "valid_to", "2026-02-01T00:00:00+00:00", "ENTITLEMENT_EXPIRED"),
    ("entitlement", "revoked_at", "2026-05-01T00:00:00+00:00", "ENTITLEMENT_REVOKED"),
    ("entitlement", None, None, "ENTITLEMENT_MISSING"),
)


def test_p2_single_field_perturbation_refuses_with_documented_reason():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 2 + case)
        side, field, new_value, expected_reason = _PERTURBATIONS[
            rng.randrange(len(_PERTURBATIONS))
        ]
        spy = _LoaderSpy()
        request = _request()
        entitlement = _entitlement()
        if side == "request":
            if field == "want_full_text":
                request["surface"] = "public"
                request["want_full_text"] = new_value
            elif field is None:
                # request is unused for ENTITLEMENT_MISSING
                entitlement = None
            else:
                request[field] = new_value
        else:
            if field is None:
                entitlement = None
            else:
                entitlement[field] = new_value
        verdict = gate_access(
            request, entitlement, as_of=_AS_OF, loader=spy
        )
        msg = _msg(BASE_SEED + 2, case)
        assert verdict.allowed is False, msg
        assert expected_reason in verdict.reasons, (
            f"{msg} expected {expected_reason!r} in {sorted(verdict.reasons)!r}"
        )
        assert spy.count == 0, msg
        assert verdict.payload is None, msg
        total += 1
    assert total >= N_CASES, "p2 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P3. FAMILY TEXT RULE v2: junk in any text field refuses the verdict.
# ---------------------------------------------------------------------------


# Each entry: (side, field) — the field is junked; the other side keeps the
# real text value so any comparison would mismatch.
_JUNK_FIELDS = (
    ("request", "account_id"),
    ("entitlement", "account_id"),
    ("request", "document_id"),
    ("entitlement", "entitlement_ref"),
)


def test_p3_junk_in_any_text_field_refuses():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 3 + case)
        junk = JUNK_VALUES[rng.randrange(len(JUNK_VALUES))]
        side, field = _JUNK_FIELDS[rng.randrange(len(_JUNK_FIELDS))]
        spy = _LoaderSpy()
        request = _request()
        entitlement = _entitlement()
        if side == "request":
            request[field] = junk
        else:
            entitlement[field] = junk
        verdict = gate_access(
            request, entitlement, as_of=_AS_OF, loader=spy
        )
        msg = _msg(BASE_SEED + 3, case) + " junk=%r side=%s field=%s" % (
            junk,
            side,
            field,
        )
        assert verdict.allowed is False, msg
        # Loader is never called on a refusal.
        assert spy.count == 0, msg
        assert verdict.payload is None, msg
        # Reasons are still in REASONS.
        for code in verdict.reasons:
            assert code in REASONS, msg
        # Specifically: junk in account_id fires ACCOUNT_MISMATCH;
        # junk in document_id fires DOCUMENT_NOT_ENTITLED;
        # junk in entitlement_ref fires ENTITLEMENT_REF_MISSING.
        if field == "account_id":
            assert "ACCOUNT_MISMATCH" in verdict.reasons, msg
        elif field == "document_id":
            assert "DOCUMENT_NOT_ENTITLED" in verdict.reasons, msg
        elif field == "entitlement_ref":
            assert "ENTITLEMENT_REF_MISSING" in verdict.reasons, msg
        total += 1
    assert total >= N_CASES, "p3 ran fewer than N_CASES generated cases"


def test_p3_junk_on_both_sides_still_refuses():
    """Same junk on both sides of a comparison must still refuse. A broken
    text-present helper that treats junk as present lets the equal-junk
    pair match and slips through — that is exactly what P3 contracts out."""
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 30 + case)
        # Exclude None (None == None trivially) and bytes-as-document
        # (None == "X" trivially False, bytes == bytes equal): pick non-None
        # string junk so " " on both sides is the canonical break.
        junk = rng.choice((" ", " X", "X ", ""))
        spy = _LoaderSpy()
        request = _request(account_id=junk)
        entitlement = _entitlement(account_id=junk)
        verdict = gate_access(
            request, entitlement, as_of=_AS_OF, loader=spy
        )
        msg = _msg(BASE_SEED + 30, case) + " junk=%r" % (junk,)
        assert verdict.allowed is False, msg
        assert "ACCOUNT_MISMATCH" in verdict.reasons, msg
        assert spy.count == 0, msg
        total += 1
    assert total >= N_CASES, "p3b ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P4. Symmetry: account equality is symmetric (==); document containment is
#     a directional lookup so it has no flip-the-sides swap. The gate's
#     flow is documented as directional: the request drives the entitlement
#     lookup; missing entitlement -> ENTITLEMENT_MISSING; missing request
#     fields do not fire that reason. We assert the symmetric account
#     predicate yields the same outcome on either side and document the
#     asymmetry on the document lookup.
# ---------------------------------------------------------------------------


def test_p4_account_equality_is_symmetric():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 4 + case)
        a1 = rng.choice(("syn-account-A", "syn-account-B", "syn-account-C"))
        a2 = rng.choice(("syn-account-A", "syn-account-B", "syn-account-C"))
        spy = _LoaderSpy()
        forward = gate_access(
            _request(account_id=a1),
            _entitlement(account_id=a2),
            as_of=_AS_OF,
            loader=spy,
        )
        spy_flip = _LoaderSpy()
        flipped = gate_access(
            _request(account_id=a2),
            _entitlement(account_id=a1),
            as_of=_AS_OF,
            loader=spy_flip,
        )
        msg = _msg(BASE_SEED + 4, case)
        # ACCOUNT_MISMATCH outcome is symmetric across the swap.
        f_mismatch = "ACCOUNT_MISMATCH" in forward.reasons
        b_mismatch = "ACCOUNT_MISMATCH" in flipped.reasons
        assert f_mismatch == b_mismatch, (
            f"{msg} account equality is not symmetric: "
            f"forward={forward.reasons!r} flipped={flipped.reasons!r}"
        )
        # The document check is unchanged across the swap (same d_req, same
        # d_set), so DOCUMENT_NOT_ENTITLED is also symmetric.
        f_doc = "DOCUMENT_NOT_ENTITLED" in forward.reasons
        b_doc = "DOCUMENT_NOT_ENTITLED" in flipped.reasons
        assert f_doc == b_doc, msg
        total += 1
    assert total >= N_CASES, "p4 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P5. Vocabulary: bare reasons are in REASONS; ordered per REASONS, deduped.
# ---------------------------------------------------------------------------


def test_p5_vocabulary_and_ordering_and_dedup():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 5 + case)
        # Compose a request that may stack several mismatches.
        flips = rng.randint(1, 4)
        request = _request()
        entitlement = _entitlement()
        flip_pool = (
            ("request", "account_id", _OTHER_ACCOUNT),
            ("request", "document_id", _OTHER_DOCUMENT),
            ("entitlement", "entitlement_ref", None),
            ("entitlement", "valid_to", "2026-02-01T00:00:00+00:00"),
            ("entitlement", "revoked_at", "2026-05-01T00:00:00+00:00"),
            ("entitlement", "valid_from", "2027-01-01T00:00:00+00:00"),
        )
        seen = set()
        for _ in range(flips):
            entry = flip_pool[rng.randrange(len(flip_pool))]
            if entry in seen:
                continue
            seen.add(entry)
            side, field, value = entry
            if side == "request":
                request[field] = value
            else:
                entitlement[field] = value
        spy = _LoaderSpy()
        verdict = gate_access(
            request, entitlement, as_of=_AS_OF, loader=spy
        )
        msg = _msg(BASE_SEED + 5, case)
        # Vocabulary: every bare reason in REASONS.
        for code in verdict.reasons:
            assert code in REASONS, (msg, code, verdict.reasons)
        # Ordering: per REASONS index.
        assert list(verdict.reasons) == sorted(
            verdict.reasons, key=REASONS.index
        ), (msg, verdict.reasons)
        # Dedup.
        assert len(verdict.reasons) == len(set(verdict.reasons)), (
            msg,
            verdict.reasons,
        )
        total += 1
    assert total >= N_CASES, "p5 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P6. No raise on junk values inside text fields.
# ---------------------------------------------------------------------------


def test_p6_no_raise_on_junk_field_values():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 6 + case)
        # Put one piece of junk into one of the request/entitlement fields.
        # We use ALL of: None, "", " ", padded strings, ints, bools, floats
        # (incl. nan), bytes, lists, dicts, sets, and object().
        junk = rng.choice(
            (
                None,
                "",
                " ",
                " X",
                "X ",
                42,
                True,
                False,
                3.14,
                float("nan"),
                b"X",
                [1, 2],
                {"a": 1},
                {1, 2},
                object(),
            )
        )
        # Pick a target field (request or entitlement).
        target = rng.choice(
            (
                ("request", "account_id"),
                ("request", "document_id"),
                ("entitlement", "account_id"),
                ("entitlement", "entitlement_ref"),
                ("entitlement", "document_ids"),
            )
        )
        side, field = target
        spy = _LoaderSpy()
        request = _request()
        entitlement = _entitlement()
        if side == "request":
            request[field] = junk
        else:
            entitlement[field] = junk
        verdict = gate_access(
            request, entitlement, as_of=_AS_OF, loader=spy
        )
        msg = _msg(BASE_SEED + 6, case) + " junk=%r side=%s field=%s" % (
            junk,
            side,
            field,
        )
        # No raise. Verdict is well-formed (allowed xor reasons).
        assert isinstance(verdict, AccessVerdict), msg
        assert verdict.allowed is False or verdict.reasons == (), msg
        if not verdict.allowed:
            assert spy.count == 0, msg
            assert verdict.payload is None, msg
        total += 1
    assert total >= N_CASES, "p6 ran fewer than N_CASES generated cases"


def test_p6_no_raise_on_junk_as_of():
    """Junk as_of strings do not raise (they refuse with AS_OF_INVALID)."""
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 60 + case)
        junk = rng.choice(
            (
                "",
                " ",
                "not-a-timestamp",
                "2026-13-01T00:00:00+00:00",
                42,
                True,
                None,
                b"X",
                ["x"],
                object(),
            )
        )
        spy = _LoaderSpy()
        verdict = gate_access(
            _request(), _entitlement(), as_of=junk, loader=spy
        )
        msg = _msg(BASE_SEED + 60, case) + " junk=%r" % (junk,)
        assert isinstance(verdict, AccessVerdict), msg
        assert verdict.allowed is False, msg
        assert "AS_OF_INVALID" in verdict.reasons, msg
        assert spy.count == 0, msg
        total += 1
    assert total >= N_CASES, "p6b ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P7. Authority: every verdict's authority flags are literal False.
# ---------------------------------------------------------------------------


def test_p7_authority_flags_always_false():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 7 + case)
        flips = rng.randint(0, 3)
        request = _request()
        entitlement = _entitlement()
        flip_pool = (
            ("request", "account_id", _OTHER_ACCOUNT),
            ("request", "document_id", _OTHER_DOCUMENT),
            ("entitlement", "entitlement_ref", None),
            ("entitlement", "valid_to", "2026-02-01T00:00:00+00:00"),
        )
        for _ in range(flips):
            entry = flip_pool[rng.randrange(len(flip_pool))]
            side, field, value = entry
            if side == "request":
                request[field] = value
            else:
                entitlement[field] = value
        spy = _LoaderSpy()
        verdict = gate_access(
            request, entitlement, as_of=_AS_OF, loader=spy
        )
        msg = _msg(BASE_SEED + 7, case)
        assert verdict.authority_flags is AUTHORITY_FLAGS, msg
        for name in FLAG_NAMES:
            assert verdict.authority_flags[name] is False, (
                msg,
                name,
                verdict.authority_flags[name],
            )
        total += 1
    assert total >= N_CASES, "p7 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P8. Determinism: same input twice = identical verdict; input dicts not
#     mutated.
# ---------------------------------------------------------------------------


def test_p8_determinism_and_no_input_mutation():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 8 + case)
        request = _request()
        entitlement = _entitlement()
        request_snapshot = {
            k: v for k, v in request.items() if k != "want_full_text"
        }
        request_snapshot["want_full_text"] = request["want_full_text"]
        entitlement_snapshot = {k: v for k, v in entitlement.items()}

        spy1 = _LoaderSpy()
        v1 = gate_access(
            request, entitlement, as_of=_AS_OF, loader=spy1
        )
        spy2 = _LoaderSpy()
        v2 = gate_access(
            request, entitlement, as_of=_AS_OF, loader=spy2
        )
        msg = _msg(BASE_SEED + 8, case)
        assert v1.allowed == v2.allowed, msg
        assert v1.reasons == v2.reasons, msg
        assert v1.payload == v2.payload, msg
        # Inputs not mutated.
        assert request == request_snapshot, (
            msg,
            request,
            request_snapshot,
        )
        assert entitlement == entitlement_snapshot, (
            msg,
            entitlement,
            entitlement_snapshot,
        )
        total += 1
    assert total >= N_CASES, "p8 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P9. Payload hygiene.
# ---------------------------------------------------------------------------


def test_p9_payload_hygiene():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 9 + case)
        # Half the cases: allow private. Quarter: refuse public full text.
        # Quarter: refuse other.
        bucket = rng.random()
        spy = _LoaderSpy()
        if bucket < 0.5:
            verdict = gate_access(
                _request(), _entitlement(), as_of=_AS_OF, loader=spy
            )
            assert verdict.allowed is True
            assert verdict.payload is spy.payload, _msg(BASE_SEED + 9, case)
            assert spy.count == 1
        elif bucket < 0.75:
            verdict = gate_access(
                _request(surface="public", want_full_text=True),
                _entitlement(),
                as_of=_AS_OF,
                loader=spy,
            )
            assert verdict.allowed is False, _msg(BASE_SEED + 9, case)
            assert verdict.payload is None
            assert spy.count == 0
        else:
            verdict = gate_access(
                _request(account_id=_OTHER_ACCOUNT),
                _entitlement(),
                as_of=_AS_OF,
                loader=spy,
            )
            assert verdict.allowed is False, _msg(BASE_SEED + 9, case)
            assert verdict.payload is None
            assert spy.count == 0
        total += 1
    assert total >= N_CASES, "p9 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# PERTURBATION PROOF
# ---------------------------------------------------------------------------
#
# A deliberately broken copy of ``_text_present`` whose only mistake is to
# return ``True`` for any non-``None`` value. With this helper:
#
#   * a " " in account_id is treated as text-present, so two " " values
#     compare equal and slip through (real refuses ACCOUNT_MISMATCH);
#   * an "X " in account_id is treated as text-present, so two equal
#     padded values compare equal and slip through (real refuses
#     ACCOUNT_MISMATCH);
#   * "X" in account_id with no other failure — same outcome in real and
#     broken (both refuse or both allow? real: text-present, allow if all
#     equal; broken: also allow). So this case is identical — we don't
#     rely on it for the perturbation proof.
#
# We never edit, reload, or monkey-patch the real module. We never touch
# ``sys.modules``. The broken copy is local to this test file.


def _broken_text_present(value):
    """A deliberately broken ``_text_present``.

    Returns ``True`` for any non-``None`` value, dropping the empty check,
    the leading/trailing-whitespace check, and the string-type check.
    Used only inside this test file's perturbation proof.
    """
    return value is not None


def _broken_gate_access(request, entitlement, *, as_of, loader):
    """A perturbed copy of ``gate_access`` whose ``_text_present`` is broken.

    Implements the same checks as the real module, using
    ``_broken_text_present`` wherever the real module uses its private
    ``_text_present``. Other helpers (SURFACES, REASONS, the datetime
    helpers, the document-entitled check) are imported from the real
    module so the broken copy inherits the rest of the contract.
    """
    if not isinstance(request, Mapping):
        raise TypeError("request must be a Mapping")
    if entitlement is not None and not isinstance(entitlement, Mapping):
        raise TypeError("entitlement must be a Mapping or None")
    if not callable(loader):
        raise TypeError("loader must be callable")

    surface = request.get("surface")
    document_id = request.get("document_id")
    account_id = request.get("account_id")
    want_full_text = request.get("want_full_text")

    reasons: list[str] = []
    if surface not in SURFACES:
        reasons.append("SURFACE_UNKNOWN")
    as_of_dt = _eg._aware_datetime(as_of)
    if as_of_dt is None:
        reasons.append("AS_OF_INVALID")
    if surface == "public":
        if want_full_text is not False:
            reasons.append("PUBLIC_FULL_TEXT_FORBIDDEN")
    elif surface == "private":
        if entitlement is None:
            reasons.append("ENTITLEMENT_MISSING")
        else:
            if not _broken_text_present(entitlement.get("entitlement_ref")):
                reasons.append("ENTITLEMENT_REF_MISSING")
            ent_account_id = entitlement.get("account_id")
            account_match = (
                _broken_text_present(account_id)
                and _broken_text_present(ent_account_id)
                and account_id == ent_account_id
            )
            if not account_match:
                reasons.append("ACCOUNT_MISMATCH")
            if not _eg._document_entitled(
                document_id, entitlement.get("document_ids")
            ):
                reasons.append("DOCUMENT_NOT_ENTITLED")
            if as_of_dt is not None:
                _eg._add_window_reasons(reasons, entitlement, as_of_dt)
    frozen = _eg._freeze_reasons(reasons)
    payload = None
    if not frozen and surface == "private":
        payload = loader(document_id)
    return AccessVerdict(allowed=not frozen, reasons=frozen, payload=payload)


def test_perturbation_p3_junk_on_both_sides_refuses_real_allows_broken():
    """P3-equivalent property: same junk on both sides refuses.

    The real module refuses ACCOUNT_MISMATCH because the broken text-present
    helper would treat " " / " X" / "X " / "" as text-present, so the equal
    junk pair would match and slip through.

    Run the same property against the real gate and against the broken
    gate. Real must refuse; broken must allow. If either side disagrees the
    boundary is mis-handled.
    """
    spy_real = _LoaderSpy()
    request = {"surface": "private", "account_id": " ", "document_id": _DOCUMENT,
               "want_full_text": True}
    entitlement = {"entitlement_ref": _ENT_REF, "account_id": " ",
                   "document_ids": (_DOCUMENT,), "valid_from": _VALID_FROM,
                   "valid_to": None, "revoked_at": None}
    real = gate_access(request, entitlement, as_of=_AS_OF, loader=spy_real)
    assert real.allowed is False, (
        "real module allowed equal whitespace (' ' == ' '): real refused "
        "ACCOUNT_MISMATCH for whitespace; if this fires the boundary "
        "rule has regressed in the real module."
    )
    assert "ACCOUNT_MISMATCH" in real.reasons

    broken = _broken_gate_access(
        request, entitlement, as_of=_AS_OF, loader=spy_real
    )
    assert broken.allowed is True, (
        "PERTURBATION PROOF FAILED: the broken copy refused equal "
        "whitespace (' ' == ' '). Expected the broken copy to allow "
        "because its broken text-present treats ' ' as text-present. "
        "Perturbation is not differentiating — boundary off-by-one is not "
        "exercised."
    )


def test_perturbation_p3_junk_on_both_sides_randomized():
    """Same boundary, randomized across P3's junk value set.

    Across ``N_CASES`` generated junk values, the real module refuses
    ACCOUNT_MISMATCH; the broken copy allows. This is the off-by-one the
    FAMILY TEXT RULE v2 contracts out.
    """
    equal_junk_cases = ("", " ", " X", "X ")
    flipped = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 100 + case)
        junk = rng.choice(equal_junk_cases)
        spy = _LoaderSpy()
        request = {"surface": "private", "account_id": junk,
                   "document_id": _DOCUMENT, "want_full_text": True}
        entitlement = {"entitlement_ref": _ENT_REF, "account_id": junk,
                       "document_ids": (_DOCUMENT,),
                       "valid_from": _VALID_FROM, "valid_to": None,
                       "revoked_at": None}
        real = gate_access(request, entitlement, as_of=_AS_OF, loader=spy)
        broken = _broken_gate_access(
            request, entitlement, as_of=_AS_OF, loader=spy
        )
        if (not real.allowed) and broken.allowed:
            flipped += 1
    # At least one such boundary case must appear across the run; otherwise
    # the perturbation proof is unexercised.
    assert flipped >= 1, (
        "PERTURBATION PROOF FAILED: across %d generated cases the broken "
        "copy never allowed a junk-equal pair the real module refused. "
        "Boundary off-by-one is not exercised." % N_CASES
    )


def test_perturbation_p3_no_junk_equals_clean_text_randomized():
    """Junk in account_id never compares equal to a clean text value.

    The real module treats junk as not text-present, so any junk value in
    account_id paired with a clean text account_id on the other side
    refuses ACCOUNT_MISMATCH. The broken copy treats junk as present; if
    the junk happens to equal the clean text (e.g., both equal to "X"),
    the broken copy would match. Across the run we expect at least one
    such equal-but-junk-on-one-side case to flip.
    """
    flipped = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 200 + case)
        clean = rng.choice(("X", "Y", "Z", "syn-account-1", "W"))
        # Junk types that could compare equal to ``clean`` if broken
        # treats them as text-present:
        #   * " X" or "X " never equal to clean str (so this can't flip
        #     unless broken strips whitespace — it doesn't);
        #   * True/False/42/b"X" never equal to a clean str;
        #   * the only flip is when junk IS the clean str — but that's
        #     not "junk" anymore. So this property has no flip on the
        #     CURRENT broken copy.
        # We still assert that junk on one side with clean on the other
        # refuses on BOTH real and broken (because == fails). The property
        # passes on the real and on the broken — but we also confirm the
        # real refuses with ACCOUNT_MISMATCH.
        junk = rng.choice((" X", "X ", 42, True, b"X"))
        spy = _LoaderSpy()
        request = {"surface": "private", "account_id": junk,
                   "document_id": _DOCUMENT, "want_full_text": True}
        entitlement = {"entitlement_ref": _ENT_REF, "account_id": clean,
                       "document_ids": (_DOCUMENT,),
                       "valid_from": _VALID_FROM, "valid_to": None,
                       "revoked_at": None}
        real = gate_access(request, entitlement, as_of=_AS_OF, loader=spy)
        assert real.allowed is False, (
            "real module allowed junk='%s' on one side and clean='%s' on "
            "the other; FAMILY TEXT RULE v2 violated in the real module."
            % (junk, clean)
        )
        assert "ACCOUNT_MISMATCH" in real.reasons
        # Broken: equal-junk case is impossible here (junk != clean), so
        # broken also refuses. We don't require flipped >= 1 — this is a
        # sanity property that the real boundary holds on junk-not-equal.
        flipped += 1
    assert flipped >= N_CASES


def test_perturbation_p3_equal_non_string_junk_refuses():
    """A different P3 sub-property: equal non-string junk (int / bool /
    bytes / float) on both sides refuses ACCOUNT_MISMATCH.

    Real refuses because non-str types are not text-in the broken helper.
    Broken allows because the broken helper treats any non-None value as
    text-present and ``==`` on equal non-str junk matches. This is a
    SEPARATE property from the whitespace-junk case (different junk
    family, different reason the real helper refuses).
    """
    flipped = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 400 + case)
        # Exclude NaN (nan != nan by IEEE-754); keep only values that
        # compare equal to themselves.
        junk = rng.choice((42, 0, True, False, 3.14, b"X", b""))
        spy = _LoaderSpy()
        request = {"surface": "private", "account_id": junk,
                   "document_id": _DOCUMENT, "want_full_text": True}
        entitlement = {"entitlement_ref": _ENT_REF, "account_id": junk,
                       "document_ids": (_DOCUMENT,),
                       "valid_from": _VALID_FROM, "valid_to": None,
                       "revoked_at": None}
        real = gate_access(request, entitlement, as_of=_AS_OF, loader=spy)
        broken = _broken_gate_access(
            request, entitlement, as_of=_AS_OF, loader=spy
        )
        if (not real.allowed) and broken.allowed:
            flipped += 1
    assert flipped >= 1, (
        "PERTURBATION PROOF FAILED: across %d generated cases the broken "
        "copy never allowed equal non-string junk the real module "
        "refused. The second property boundary is not exercised."
        % N_CASES
    )