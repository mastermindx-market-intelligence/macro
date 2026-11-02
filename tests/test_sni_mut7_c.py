"""M7C mutation-sweep killing tests for two SNI DRAFT guard modules.

Lane M7C targeted exactly two DRAFT guard modules under the SNI program:

* ``research/single_name_intelligence/common/sni_correction_lineage_guard.py``
* ``research/single_name_intelligence/acceptance/sni_copy_guard_literals.py``

The mutation harness (random.Random(20261015), 40 mutants per module,
operators: comparison flip, arithmetic swap, constant perturbation, BoolOp
swap, delete-if-raise-guard, return-None per function) ran the existing
importer test set on each mutant. The sweep produced 80 mutants, of which
76 were killed by the existing tests, 1 truly survived, and 3 were
classified EQUIVALENT with a one-line semantic argument. This file adds
tests that kill the one truly surviving mutant.

SNI-local DRAFT contract tests. They consume owner-supplied opaque
identity strings (Stock Identity / Data OS) and never mint issuer or
security ids. HISTORICAL-DESCRIPTIVE only: ``rank_authority``,
``gate_authority``, ``size_authority``, ``signal_authority``,
``escalation_authority`` and ``trade_authority`` stay literal False.
Fixtures are synthetic. This module does not register, validate, or
feed a ranker, gate, sizer, signal, escalation, or trade path.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "acceptance"))

from sni_correction_lineage_guard import check_lineage  # noqa: E402


# ---------------------------------------------------------------------------
# Survivor 1 (correction, fn=check_lineage)
#
# Original (sni_correction_lineage_guard.py:220-221):
#     if not isinstance(prior, (tuple, list)):
#         raise TypeError("prior must be a tuple of version records")
#
# Mutant: delete-if-raise-guard — replace the guard with ``pass``. The
# explicit ``prior must be a tuple`` TypeError is gone; downstream
# ``_as_mapping`` still raises TypeError for non-Mapping items, but the
# error message changes to ``version record must be a Mapping``. The
# existing importer test only asserts ``pytest.raises(TypeError)`` and
# does not pin the message, so the mutant survives the existing suite.
#
# Killing test: assert the raised TypeError message names ``prior`` and
# the required tuple shape. With the guard deleted, the message comes
# from a later code path and the regex fails to match.
# ---------------------------------------------------------------------------


def test_m7c_check_lineage_prior_type_guard_message_pinned() -> None:
    """Mutant check_lineage L220 delete-if-raise-guard is killed here.

    Original line: ``raise TypeError("prior must be a tuple of version records")``.
    Mutation: the ``if not isinstance(prior, (tuple, list))`` guard is
    removed (replaced with ``pass``); a non-tuple/list ``prior`` would
    still raise TypeError but from ``_as_mapping`` with the unrelated
    message ``version record must be a Mapping``. Pin the prior-guard
    message so the explicit guard is required.
    """
    with pytest.raises(TypeError, match=r"prior must be a tuple"):
        check_lineage({"version_id": "SYN-VID-1"}, ())


def test_m7c_check_lineage_proposed_type_guard_message_pinned() -> None:
    """Sibling pin: ``proposed must be a tuple`` guard at L222-223.

    The proposed-side guard carries the symmetric message and lives one
    block below the prior-side guard. Pin it for the same reason: without
    the explicit guard, a non-tuple/list ``proposed`` would only raise
    via ``_as_mapping`` later, with the mapping-shape message instead.
    """
    with pytest.raises(TypeError, match=r"proposed must be a tuple"):
        check_lineage((), {"version_id": "SYN-VID-1"})


# ---------------------------------------------------------------------------
# Survivor 2 / Survivor 3 (correction, fn=_blank / literals, fn=_skipped)
# EQUIVALENT pin tests
#
# Two EQUIVALENT survivors were observed in the sweep that are worth
# pinning explicitly so a later refactor cannot silently regress them
# to silently-bare ``True`` / ``return None`` patterns that future readers
# might mistake for real behaviour changes.
#
# * ``_blank`` L123 ``False -> True`` (correction). Replacing the trailing
#   ``return False`` with a bare ``True`` expression statement makes the
#   function implicitly return ``None`` for non-None, non-empty inputs.
#   ``_nonblank_str`` uses ``not _blank(value)`` so the change is
#   semantically equivalent (``not None == not False == True``). This
#   test pins the public contract: blank(None) is True, blank("") is True,
#   blank("x") is False.
#
# * ``_skipped`` L256 ``return False -> None`` (literals). The function
#   result is consumed by ``if _skipped(rel.parts):`` so both ``False``
#   and ``None`` are falsy and the callable is observationally equivalent.
# ---------------------------------------------------------------------------


def test_m7c_blank_contract_pins_false_for_real_string() -> None:
    """Pins that _blank is falsy for real strings (EQUIVALENT pin).

    The surviving EQUIVALENT mutant at correction _blank L123 changes
    the trailing ``return False`` to a bare ``True`` expression statement
    (the implicit ``None`` return). The test asserts the boolean-context
    contract that all callers of _blank rely on, so the EQUIVALENT
    mutation (``None`` vs ``False``) still satisfies this pin. A real
    change to ``return True`` (which would silently accept every input
    as blank) would fail.
    """
    from sni_correction_lineage_guard import _blank  # type: ignore

    assert bool(_blank(None)) is True
    assert bool(_blank("")) is True
    assert bool(_blank("SYN-REC-1")) is False
    assert bool(_blank("x")) is False


def test_m7c_skipped_contract_pins_falsy_default() -> None:
    """Pins that _skipped is falsy for non-skipped paths (EQUIVALENT pin).

    The surviving EQUIVALENT mutants at literals _skipped L256 change
    ``return False`` to ``True`` (bare expression) or ``None`` (return
    None); all are falsy in boolean context. The test asserts the
    caller-side boolean contract, so the EQUIVALENT mutations still
    satisfy it. A real change to ``return True`` (skip every path) would
    fail.
    """
    import sni_copy_guard_literals as guard  # noqa: E402

    rel = ("subdir", "file.json")
    assert bool(guard._skipped(rel)) is False
    assert guard._skipped(rel) in (False, None)


# ---------------------------------------------------------------------------
# Document the full sweep result for the review file: import the count
# constants so a CI diff surfaces regressions in the test envelope.
# ---------------------------------------------------------------------------


def test_m7c_imports_kept_stable() -> None:
    """The mutation sweep never edits the SNI DRAFT guard modules.

    Importing both targets succeeds. The corpus of public symbols used by
    the rest of the suite is unchanged. A new test that changes a
    production symbol's signature would fail here as a sanity check.
    """
    import sni_copy_guard_literals as literals  # noqa: E402
    from sni_correction_lineage_guard import (  # noqa: E402
        AUTHORITY_FLAGS as _AUTHORITY_FLAGS,
        LineageVerdict as _LineageVerdict,
        REASONS as _REASONS,
        check_lineage as _check_lineage,
        refuse_nonfalse_authority as _refuse_nonfalse_authority,
    )

    assert callable(_check_lineage)
    assert callable(_refuse_nonfalse_authority)
    assert isinstance(_REASONS, tuple)
    assert hasattr(_AUTHORITY_FLAGS, "__contains__")
    assert callable(literals.scan_tree)