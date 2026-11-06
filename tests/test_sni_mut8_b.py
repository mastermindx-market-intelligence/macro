"""M8B mutation sweep — targeted killing tests for SNI DRAFT guard modules.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings and view-state / lineage mappings from the product page state owner
and the qledger/Evaluation owner; they never mint issuer or security ids.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.

Each test names the specific survivor (file:line, original -> mutated) it
kills; docstrings record the mutant so the kill is reproducible.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_view_state_guard import (  # noqa: E402
    ViewTransitionVerdict,
    persist_across,
    refuse_nonfalse_authority,
)
from sni_correction_lineage_guard import (  # noqa: E402
    LineageVerdict,
    _as_mapping,
    check_lineage,
)


# ---------------------------------------------------------------------------
# view_state_guard killing tests
# ---------------------------------------------------------------------------


def test_m8b_view_state_verdict_reasons_freeze_order_1():
    """Mutant: sni_view_state_guard.py:119 object.__setattr__(self, "reasons", frozen)
    -> object.__setattr__(self, "reasonsX", frozen).

    Original code freezes self.reasons to REASONS order in __post_init__ via
    object.__setattr__ (so the frozen tuple replaces the caller-supplied
    list/tuple). With the mutation the setattr targets a different key, so
    the caller-supplied reasons stay on the instance. A test that passes
    reasons in REVERSE order and asserts the post-freeze order kills this.
    """
    verdict = ViewTransitionVerdict(
        allowed=True,
        reasons=("AS_OF_CHANGED", "FIELD_MISSING"),
        changed_axes=("as_of",),
    )
    assert verdict.reasons == ("FIELD_MISSING", "AS_OF_CHANGED")


def test_m8b_view_state_refuse_authority_error_message_2():
    """Mutant: sni_view_state_guard.py:93
    "; every authority flag must be literal False" -> "; every authority flag must be literal FalseX"
    AND/OR sni_view_state_guard.py:103 "] is " -> "] is X".

    Either mutation changes the exact f-string that the guard raises when a
    caller passes a non-False authority flag. A test asserting the exact
    original message text kills both.
    """
    with pytest.raises(ValueError) as excinfo:
        refuse_nonfalse_authority({"rank_authority": True})
    assert str(excinfo.value) == (
        "authority_flags['rank_authority'] is True; "
        "every authority flag must be literal False"
    )


def test_m8b_view_state_persist_across_error_message_3():
    """Mutant: sni_view_state_guard.py:276
    "before must be a Mapping" -> "before must be a MappingX".

    The TypeError text changes; a test asserting the exact original text
    kills the mutation.
    """
    with pytest.raises(TypeError) as excinfo:
        persist_across("not-a-mapping", lang="en")
    assert str(excinfo.value) == "before must be a Mapping"


# ---------------------------------------------------------------------------
# correction_lineage_guard killing tests
# ---------------------------------------------------------------------------


def test_m8b_lineage_verdict_reasons_freeze_order_4():
    """Mutant: sni_correction_lineage_guard.py:109
    object.__setattr__(self, "reasons", frozen)
    -> object.__setattr__(self, "reasonsX", frozen).

    Same shape as the view_state freeze: a call passing reasons out of
    REASONS order must see the frozen REASONS-order tuple on the instance.
    With the mutated key, the input tuple is left in place.
    """
    verdict = LineageVerdict(
        allowed=True,
        reasons=("SUPERSEDES_MISMATCH", "FORK"),
        appended=(),
    )
    assert verdict.reasons == ("FORK", "SUPERSEDES_MISMATCH")


def test_m8b_lineage_verdict_allowed_override_5():
    """Mutant: sni_correction_lineage_guard.py:110
    object.__setattr__(self, "allowed", not frozen)
    -> object.__setattr__(self, "allowedX", not frozen).

    The guard's __post_init__ coerces `allowed` to `not frozen`. If the
    setattr targets a different key, the caller-supplied `allowed=True`
    stays. A direct verdict construction with non-empty reasons and a
    `True` allowed input must observe `allowed is False`.
    """
    verdict = LineageVerdict(
        allowed=True,
        reasons=("FORK",),
        appended=(),
    )
    assert verdict.allowed is False


def test_m8b_lineage_as_mapping_error_message_6():
    """Mutant: sni_correction_lineage_guard.py:196
    "version record must be a Mapping" -> "version record must be a MappingX".

    The TypeError text from _as_mapping (and therefore check_lineage's
    record validation) changes. A test asserting the exact original text
    kills the mutation.
    """
    with pytest.raises(TypeError) as excinfo:
        _as_mapping("not-a-mapping")
    assert str(excinfo.value) == "version record must be a Mapping"


# ---------------------------------------------------------------------------
# Smoke: a positive control so a non-mutation build still has green tests
# ---------------------------------------------------------------------------


def test_m8b_view_state_positive_control_no_mutation():
    """A minimal, un-mutated positive control. Confirms the test file is
    usable on the un-mutated production code: an allowed verdict has
    empty reasons and a refused verdict has a non-empty reasons tuple.
    """
    base = {
        "issuer_id": "SYN-ISSUER-1",
        "counter_id": "SYN-COUNTER-1",
        "lens": "spot",
        "as_of": "2024-01-01",
        "lang": "en",
        "viewport": "desktop",
    }
    verdict_allowed = ViewTransitionVerdict(
        allowed=True,
        reasons=(),
        changed_axes=(),
    )
    assert verdict_allowed.allowed is True
    assert verdict_allowed.reasons == ()

    verdict_refused = ViewTransitionVerdict(
        allowed=True,
        reasons=("FIELD_MISSING",),
        changed_axes=(),
    )
    assert verdict_refused.allowed is False
    assert verdict_refused.reasons == ("FIELD_MISSING",)
    assert verdict_refused.allowed is False

    # And a minimal lineage control: an empty lineage is allowed.
    empty_lineage = LineageVerdict(
        allowed=True,
        reasons=(),
        appended=(),
    )
    assert empty_lineage.allowed is True
    assert empty_lineage.reasons == ()
    assert empty_lineage.appended == ()


def test_m8b_lineage_check_lineage_smoke():
    """A non-mutated positive control for check_lineage. Empty prior with
    a single valid record is allowed and the new version_id is appended.
    """
    record = {
        "record_id": "SYN-REC-1",
        "version_id": "SYN-VID-1",
        "version": 1,
        "supersedes_version_id": None,
        "content_sha256": "01" * 32,
        "recorded_at": "2024-01-01T09:00:00+00:00",
    }
    verdict = check_lineage((), (record,))
    assert verdict.allowed is True
    assert verdict.appended == ("SYN-VID-1",)
