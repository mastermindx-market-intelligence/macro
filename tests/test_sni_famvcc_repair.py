"""FAMVCC round-1 repair tests for X8C defects 08/10/11/12/13/14.

Closes the following X8C findings on the SNI view-state /
correction-lineage / share-class duplicate / three-clock DRAFT guards:

  * X8C-08 — _IDENTITY_REASONS axis alignment (static invariant; PIN).
  * X8C-10 — view-state `check_view_transition` docstring pins the seat
    ruling on `change` as a PERMITTED axis (not an exclusive intent
    marker); docstring-only edit, runtime behaviour unchanged.
  * X8C-11 — view-state text fields (issuer_id, counter_id, lens, as_of)
    follow the FAMILY TEXT RULE; non-text values -> FIELD_MISSING.
  * X8C-12 — correction-lineage record_id / version_id /
    supersedes_version_id follow the FAMILY TEXT RULE;
    non-text values -> RECORD_FIELD_INVALID; unhashable values never raise.
  * X8C-13 — share-class duplicate security_id / issuer_id /
    member.owner_ref / pair_id / pair.owner_ref follow the FAMILY
    TEXT RULE; unhashable security_id/issuer_id never raise.
  * X8C-14 — three-clock record values, field-map keys, and kind labels
    follow the FAMILY TEXT RULE; non-text values -> the refusal reason
    the module already emits for a blank value of that field.

Per ROOM LAW and PROGRAM LAW: nothing here feeds a ranker, gate, sizer,
signal, escalation, or trade path. Identity ids are caller-supplied
opaque strings; this file never mints issuer or security ids.
Fixtures are synthetic. ``rank_authority``, ``gate_authority``,
``size_authority``, ``signal_authority``, ``escalation_authority`` and
``trade_authority`` stay literal False.

One test function per closed numbered defect, named
``test_r1_<nn>_<slug>`` where ``<nn>`` is the defect number.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
COMMON = ROOT / "research" / "single_name_intelligence" / "common"
sys.path.insert(0, str(COMMON))

from sni_view_state_guard import (  # noqa: E402
    AXES,
    REASONS,
    _IDENTITY_REASONS,
    check_view_transition,
)
from sni_correction_lineage_guard import (  # noqa: E402
    REASONS as LINEAGE_REASONS,
    check_lineage,
)
from sni_class_duplicate_guard import (  # noqa: E402
    check_class_duplicates,
)
from sni_three_clock_guard import (  # noqa: E402
    REASONS as CLOCK_REASONS,
    classify_clocks,
)


# ---------------------------------------------------------------------------
# X8C-08 — view-state _IDENTITY_REASONS axis alignment (PIN: passes on base).
# ---------------------------------------------------------------------------


def test_r1_08_view_state_identity_reasons_aligned():
    """Every axis in ``_IDENTITY_REASONS`` must be in ``AXES``, every reason
    code in ``REASONS``, and no axis may be repeated. The seat ruling
    forbids a refactor that grows either tuple out of step with the other.
    """
    axes_seen: list[str] = []
    for axis, code in _IDENTITY_REASONS:
        assert axis in AXES, (
            f"_IDENTITY_REASONS axis {axis!r} is not in AXES"
        )
        assert code in REASONS, (
            f"_IDENTITY_REASONS code {code!r} is not in REASONS"
        )
        axes_seen.append(axis)
    assert len(axes_seen) == len(set(axes_seen)), (
        f"_IDENTITY_REASONS has duplicate axis: {axes_seen}"
    )


# ---------------------------------------------------------------------------
# X8C-10 — view-state docstring pins the seat ruling on `change`.
# ---------------------------------------------------------------------------


def test_r1_10_view_state_change_documents_seat_ruling():
    """The SEAT RULING pins the contract: ``change`` names a PERMITTED axis,
    not an exclusive intent marker; declaring an axis that did not change
    is ALLOWED. The ``check_view_transition`` docstring must state this
    contract verbatim so the contract is inspectable, not just inferred
    from runtime output. Runtime behaviour is unchanged (docstring-only
    edit), so the pin is on the docstring text itself.
    """
    source = inspect.getsource(check_view_transition)
    assert "PERMITTED axis" in source, (
        "check_view_transition docstring must say `change` names a "
        "PERMITTED axis (seat ruling X8C-10)"
    )
    assert "not an exclusive intent marker" in source, (
        "check_view_transition docstring must negate the exclusive-intent "
        "reading (seat ruling X8C-10)"
    )
    assert "declaring an axis that did not change is ALLOWED" in source, (
        "check_view_transition docstring must state the "
        "allow-on-zero-change rule (seat ruling X8C-10)"
    )


# ---------------------------------------------------------------------------
# X8C-11 — view-state text fields follow the FAMILY TEXT RULE.
# ---------------------------------------------------------------------------


def _view_state_kwargs(**overrides):
    body = {
        "issuer_id": "SYN-ISSUER-1",
        "counter_id": "SYN-CTR-A",
        "lens": "SYN-LENS-1",
        "as_of": "2026-10-13T08:00:00+00:00",
        "lang": "en",
        "viewport": "desktop",
    }
    body.update(overrides)
    return body


def test_r1_11_view_state_text_fields_follow_family_rule():
    """Whitespace and non-string issuer_id / counter_id / lens / as_of
    values are refused with FIELD_MISSING (the reason the module already
    emits for a blank value of those fields). ``1`` and ``True`` never
    compare equal across views. Padded values (leading or trailing
    whitespace) are ABSENT under the FAMILY TEXT RULE v2 seat ruling;
    see the ``_padded_`` tests below.
    """
    # --- whitespace string on issuer_id ----------------------------------
    before = _view_state_kwargs()
    after = _view_state_kwargs(issuer_id="  ")
    verdict = check_view_transition(before, after, change=None)
    assert verdict.allowed is False
    assert "FIELD_MISSING" in verdict.reasons

    # --- non-string int on lens ------------------------------------------
    before = _view_state_kwargs()
    after = _view_state_kwargs(lens=1)
    verdict = check_view_transition(before, after, change=None)
    assert verdict.allowed is False
    assert "FIELD_MISSING" in verdict.reasons

    # --- non-string dict on as_of (unhashable path) -----------------------
    before = _view_state_kwargs()
    after = _view_state_kwargs(as_of={"nested": "x"})
    verdict = check_view_transition(before, after, change=None)
    assert verdict.allowed is False
    assert "FIELD_MISSING" in verdict.reasons

    # --- 1 and True never compare equal ----------------------------------
    before = _view_state_kwargs(issuer_id=1)
    after = _view_state_kwargs(issuer_id=True)
    verdict = check_view_transition(before, after, change="issuer_id")
    assert verdict.allowed is False
    assert "FIELD_MISSING" in verdict.reasons


# ---------------------------------------------------------------------------
# X8C-12 — correction-lineage text fields follow the FAMILY TEXT RULE.
# ---------------------------------------------------------------------------


def _lineage_record(**overrides):
    body = {
        "record_id": "SYN-REC-1",
        "version_id": "SYN-VID-1",
        "version": 1,
        "supersedes_version_id": None,
        "content_sha256": "0" * 64,
        "recorded_at": "2026-01-11T09:00:00+00:00",
    }
    body.update(overrides)
    return body


def test_r1_12_correction_lineage_text_fields_follow_family_rule():
    """Whitespace and non-string record_id / version_id /
    supersedes_version_id values are refused with RECORD_FIELD_INVALID.
    An unhashable record_id / version_id is ABSENT and never raises.
    Padded values (leading or trailing
    whitespace) are ABSENT under the FAMILY TEXT RULE v2 seat ruling;
    see the ``_padded_`` tests below.
    """
    # --- whitespace string on record_id ----------------------------------
    record = _lineage_record(record_id="  ")
    verdict = check_lineage((), (record,))
    assert verdict.allowed is False
    assert "RECORD_FIELD_INVALID" in verdict.reasons

    # --- non-string int on record_id -------------------------------------
    record = _lineage_record(record_id=1)
    verdict = check_lineage((), (record,))
    assert verdict.allowed is False
    assert "RECORD_FIELD_INVALID" in verdict.reasons

    # --- non-string int on supersedes_version_id --------------------------
    prior = _lineage_record(version_id="SYN-VID-1", version=1)
    proposed = _lineage_record(
        version_id="SYN-VID-2", version=2, supersedes_version_id=42
    )
    verdict = check_lineage((prior,), (prior, proposed))
    assert verdict.allowed is False
    assert "RECORD_FIELD_INVALID" in verdict.reasons

    # --- unhashable record_id never raises --------------------------------
    record = _lineage_record(record_id={"a": "b"})
    verdict = check_lineage((), (record,))
    assert verdict.allowed is False
    assert "RECORD_FIELD_INVALID" in verdict.reasons

    # --- unhashable version_id never raises -------------------------------
    record = _lineage_record(version_id=[1, 2])
    verdict = check_lineage((), (record,))
    assert verdict.allowed is False
    assert "RECORD_FIELD_INVALID" in verdict.reasons


# ---------------------------------------------------------------------------
# X8C-13 — share-class duplicate text fields follow the FAMILY TEXT RULE.
# ---------------------------------------------------------------------------


def _dup_member(**overrides):
    body = {
        "security_id": "SYN-SEC-A",
        "issuer_id": "SYN-ISSUER-1",
        "owner_ref": "SYN-OWNER-X",
    }
    body.update(overrides)
    return body


def _dup_pair(**overrides):
    body = {
        "pair_id": "SYN-PAIR-1",
        "issuer_id": "SYN-ISSUER-1",
        "security_ids": ("SYN-SEC-A", "SYN-SEC-B"),
        "primary_security_id": "SYN-SEC-A",
        "dedup": True,
        "owner_ref": "SYN-OWNER-X",
    }
    body.update(overrides)
    return body


def test_r1_13_class_duplicate_text_fields_follow_family_rule():
    """Whitespace and non-string security_id / issuer_id /
    member.owner_ref / pair_id / pair.owner_ref values are refused with
    SECURITY_ID_MISSING / ISSUER_ID_MISSING / MEMBER_UNSOURCED /
    PAIR_UNSOURCED. An unhashable security_id or issuer_id is ABSENT
    and never raises (no set/dict insertion of an unchecked value).
    Padded values (leading or trailing
    whitespace) are ABSENT under the FAMILY TEXT RULE v2 seat ruling;
    see the ``_padded_`` tests below.
    """
    # --- whitespace string on security_id --------------------------------
    pack = [_dup_member(security_id="  ")]
    verdict = check_class_duplicates(pack, share_class_pairs=[])
    assert verdict.allowed is False
    assert "SECURITY_ID_MISSING" in verdict.reasons

    # --- non-string int on member.owner_ref ------------------------------
    pack = [_dup_member(owner_ref=1)]
    verdict = check_class_duplicates(pack, share_class_pairs=[])
    assert verdict.allowed is False
    assert "MEMBER_UNSOURCED" in verdict.reasons

    # --- unhashable security_id never raises -----------------------------
    pack = [_dup_member(security_id={"k": "v"})]
    verdict = check_class_duplicates(pack, share_class_pairs=[])
    assert verdict.allowed is False
    assert "SECURITY_ID_MISSING" in verdict.reasons

    # --- unhashable issuer_id never raises -------------------------------
    pack = [_dup_member(issuer_id={"k": "v"})]
    verdict = check_class_duplicates(pack, share_class_pairs=[])
    assert verdict.allowed is False
    assert "ISSUER_ID_MISSING" in verdict.reasons

    # --- non-string int on pair_id ----------------------------------------
    pack = [_dup_member(), _dup_member(security_id="SYN-SEC-B")]
    pair = _dup_pair(pair_id=1)
    verdict = check_class_duplicates(pack, share_class_pairs=[pair])
    assert verdict.allowed is False
    assert "PAIR_UNSOURCED" in verdict.reasons

    # --- non-string int on pair.owner_ref ---------------------------------
    pack = [_dup_member(), _dup_member(security_id="SYN-SEC-B")]
    pair = _dup_pair(owner_ref=1)
    verdict = check_class_duplicates(pack, share_class_pairs=[pair])
    assert verdict.allowed is False
    assert "PAIR_UNSOURCED" in verdict.reasons


# ---------------------------------------------------------------------------
# X8C-14 — three-clock text fields follow the FAMILY TEXT RULE.
# ---------------------------------------------------------------------------


def _three_clock_field_map():
    return {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }


def _three_clock_record():
    return {
        "period_end": "2026-06-30",
        "filed_at": "2026-07-15T08:30:00+00:00",
        "ingested_at": "2026-07-15T17:00:00+00:00",
    }


def test_r1_14_three_clock_text_fields_follow_family_rule():
    """Whitespace record values, non-text field-map keys, and the three
    value classes for kind labels are refused with the reason the module
    already emits for a blank value of that field (ECONOMIC_MISSING /
    PUBLICATION_MISSING / OWNER_KNOWN_MISSING / KIND_UNKNOWN). Padded
    field-map keys and kind labels are ABSENT under the FAMILY TEXT RULE
    v2 seat ruling. Padded and non-str record values keep the existing
    pins: they fail ``_coerce_field_value`` and refuse with
    ``TIMESTAMP_INVALID``, which is also a refusal.
    """
    # --- whitespace string on a clock record value ------------------------
    record = _three_clock_record()
    record["period_end"] = "  "
    verdict = classify_clocks(record, _three_clock_field_map(), kind="actual")
    assert verdict.allowed is False
    assert "ECONOMIC_MISSING" in verdict.reasons

    # --- non-string int field-map key is ABSENT (no override path) ----------------
    field_map = {
        1: "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = _three_clock_record()
    record[1] = "2026-06-30"
    verdict = classify_clocks(record, field_map, kind="actual")
    assert verdict.allowed is False
    # A non-text field-map key is ABSENT; the corresponding clock is MISSING.
    assert "ECONOMIC_MISSING" in verdict.reasons

    # --- whitespace string kind ------------------------------------------
    verdict = classify_clocks(
        _three_clock_record(), _three_clock_field_map(), kind="  "
    )
    assert verdict.allowed is False
    assert "KIND_UNKNOWN" in verdict.reasons

    # --- non-string int kind ----------------------------------------------
    verdict = classify_clocks(
        _three_clock_record(), _three_clock_field_map(), kind=1
    )
    assert verdict.allowed is False
    assert "KIND_UNKNOWN" in verdict.reasons

    # --- padded string kind ----------------------------------------------
    verdict = classify_clocks(
        _three_clock_record(), _three_clock_field_map(), kind=" actual "
    )
    assert verdict.allowed is False
    assert "KIND_UNKNOWN" in verdict.reasons


# ---------------------------------------------------------------------------
# FAMILY TEXT RULE v2 (seat ruling): padded text is ABSENT in all four guards.
# ---------------------------------------------------------------------------

_PADDED = ("SYN-ID ", " SYN-ID", "\tSYN-ID", "SYN-ID\n", "SYN-ID\u3000")


def test_r1_11_view_state_padded_text_is_absent():
    for axis in ("issuer_id", "counter_id", "lens", "as_of"):
        for value in _PADDED:
            before = _view_state_kwargs()
            after = _view_state_kwargs(**{axis: value})
            verdict = check_view_transition(before, after, change=None)
            assert verdict.allowed is False, (axis, value)
            assert verdict.reasons == ("FIELD_MISSING",), (axis, value)
            assert verdict.changed_axes == (), (axis, value)
    # The same padded id on both sides is still ABSENT, not "unchanged".
    before = _view_state_kwargs(issuer_id="SYN-ISSUER-1 ")
    after = _view_state_kwargs(issuer_id="SYN-ISSUER-1 ")
    verdict = check_view_transition(before, after, change=None)
    assert verdict.allowed is False
    assert verdict.reasons == ("FIELD_MISSING",)


def test_r1_12_correction_lineage_padded_text_is_absent():
    for field in ("record_id", "version_id"):
        for value in _PADDED:
            record = _lineage_record(**{field: value})
            verdict = check_lineage((), (record,))
            assert verdict.allowed is False, (field, value)
            assert "RECORD_FIELD_INVALID" in verdict.reasons, (field, value)
    prior = _lineage_record(version_id="SYN-VID-1", version=1)
    for value in ("SYN-VID-1 ", " SYN-VID-1"):
        proposed = _lineage_record(
            version_id="SYN-VID-2", version=2, supersedes_version_id=value
        )
        verdict = check_lineage((prior,), (prior, proposed))
        assert verdict.allowed is False, value
        assert "RECORD_FIELD_INVALID" in verdict.reasons, value


def test_r1_13_class_duplicate_padded_text_is_absent():
    for field, reason in (
        ("security_id", "SECURITY_ID_MISSING"),
        ("issuer_id", "ISSUER_ID_MISSING"),
        ("owner_ref", "MEMBER_UNSOURCED"),
    ):
        for value in _PADDED:
            pack = [_dup_member(**{field: value})]
            verdict = check_class_duplicates(pack, share_class_pairs=[])
            assert verdict.allowed is False, (field, value)
            assert reason in verdict.reasons, (field, value)
    for field in ("pair_id", "owner_ref"):
        for value in _PADDED:
            pack = [_dup_member(), _dup_member(security_id="SYN-SEC-B")]
            pair = _dup_pair(**{field: value})
            verdict = check_class_duplicates(pack, share_class_pairs=[pair])
            assert verdict.allowed is False, (field, value)
            assert "PAIR_UNSOURCED" in verdict.reasons, (field, value)


def test_r1_14_three_clock_padded_keys_and_kind_are_absent():
    for value in (" period_end", "period_end ", "period_end\t"):
        field_map = _three_clock_field_map()
        del field_map["period_end"]
        field_map[value] = "ECONOMIC"
        record = _three_clock_record()
        record[value] = record.pop("period_end")
        verdict = classify_clocks(record, field_map, kind="actual")
        assert verdict.allowed is False, value
        assert "ECONOMIC_MISSING" in verdict.reasons, value
    for kind in ("actual ", " actual", "actual\n"):
        verdict = classify_clocks(
            _three_clock_record(), _three_clock_field_map(), kind=kind
        )
        assert verdict.allowed is False, kind
        assert "KIND_UNKNOWN" in verdict.reasons, kind
