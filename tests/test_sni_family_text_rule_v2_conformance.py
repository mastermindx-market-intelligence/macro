"""FAMIR round 1 — family-wide conformance test for FAMILY TEXT RULE v2.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer or security ids.
Every authority flag stays literal False. Fixtures are synthetic and live
only inside this file. Nothing here feeds a ranker, gate, sizer, signal,
escalation, or trade path.

This file is the FAMILY TEXT RULE v2 conformance test. It pins every
``_text_present`` helper in the SNI guard family to a single truth table
and a single call shape:

  * a string that begins or ends with whitespace is ABSENT, exactly like
    a whitespace-only or empty string;
  * the helper calls NO normalisation method (``.strip()`` /
    ``.lower()`` / ``.upper()`` / ``.casefold()`` / ``.replace()``);
  * the helper's only calls are ``isinstance`` and ``.isspace()``;
  * the helper never raises for unhashable values: presence is tested
    BEFORE any set / dict membership, ``set.add``, or dict key use.

This test does not edit any production source. It is read-only with
respect to every guard module. A guard that genuinely violates the rule
must be repaired by its own lane; this test only pins the rule and the
truth table.

The 13 stems in scope are documented in
``research/single_name_intelligence/common/``. The kpi_missingness and
then_known guards are explicitly out of scope here; a sibling lane is
adding their helpers in parallel and this test asserts only the SUBSET
direction so the sibling landing first never breaks it.
"""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest

# REPO is the worktree root, resolved relative to THIS file.
TESTS_DIR = Path(__file__).resolve().parent
REPO = TESTS_DIR.parent
COMMON_DIR = REPO / "research" / "single_name_intelligence" / "common"

# The existing guard tests insert the common dir on sys.path with the same
# pattern. Match the idiom so importlib.import_module resolves the modules
# the way the rest of the test suite does.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

EXPECTED_HELPER_STEMS: tuple[str, ...] = (
    "sni_ads_ratio_guard",
    "sni_class_duplicate_guard",
    "sni_comparison_guard",
    "sni_correction_lineage_guard",
    "sni_counter_relation_guard",
    "sni_denominator_guard",
    "sni_entitlement_guard",
    "sni_identity_binding_guard",
    "sni_join_guard",
    "sni_release_evidence_guard",
    "sni_session_state_guard",
    "sni_three_clock_guard",
    "sni_view_state_guard",
)

KNOWN_HELPERLESS_STEMS: frozenset[str] = frozenset(
    {"sni_kpi_missingness_guard", "sni_then_known_guard"}
)


def _canonical_text_present(value: object) -> bool:
    """FAMILY TEXT RULE v2 canonical body.

    Identical to ``sni_view_state_guard._text_present``. Defined locally
    so this test never depends on any other module's body to assert
    itself.
    """
    return (
        isinstance(value, str)
        and value != ""
        and not value[0].isspace()
        and not value[-1].isspace()
    )


# ---------------------------------------------------------------------------
# (a) census: every expected stem defines a top-level _text_present
# ---------------------------------------------------------------------------


def _collect_helper_stems() -> set[str]:
    """Parse every ``sni_*_guard.py`` in the common dir and collect the
    stems that define a top-level ``_text_present`` function."""
    stems: set[str] = set()
    for path in sorted(COMMON_DIR.glob("sni_*_guard.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "_text_present":
                stems.add(path.stem)
                break
    return stems


def test_r1_01_family_helper_census():
    """FAMILY TEXT RULE v2: every guard in the expected census defines a
    top-level ``_text_present`` helper. The collected set is a SUPERSET of
    the 13 stems listed in this lane's frozen spec; new helpers are
    allowed to join the family without breaking this test."""
    collected = _collect_helper_stems()
    expected = set(EXPECTED_HELPER_STEMS)
    missing = expected - collected
    assert not missing, (
        "expected _text_present helper missing in: " + ", ".join(sorted(missing))
    )


# ---------------------------------------------------------------------------
# (b) truth table: every helper matches the canonical v2 body
# ---------------------------------------------------------------------------


_TRUTH_TABLE_VALUES: tuple[object, ...] = (
    "ID",
    "I D",
    "",
    " ",
    "ID ",
    " ID",
    "\tID",
    "ID　",
    "\u0085ID",
    "\n",
    None,
    1,
    0,
    True,
    False,
    1.0,
    b"id",
    ["id"],
    ("id",),
    {"id": 1},
    object(),
)


_TRUTH_TABLE_TRUE_VALUES: frozenset[object] = frozenset({"ID", "I D"})


def test_r1_02_family_truth_table():
    """FAMILY TEXT RULE v2: every helper in the family returns the same
    result as the canonical v2 body on the documented truth table. Only
    ``"ID"`` and ``"I D"`` are present; every other value is absent."""
    canonical = _canonical_text_present
    for stem in EXPECTED_HELPER_STEMS:
        mod = importlib.import_module(stem)
        for value in _TRUTH_TABLE_VALUES:
            assert mod._text_present(value) is canonical(value), (
                stem,
                value,
                mod._text_present(value),
                canonical(value),
            )
        # The truth table is exactly these two present values.
        present = [v for v in _TRUTH_TABLE_VALUES if mod._text_present(v) is True]
        assert frozenset(present) == _TRUTH_TABLE_TRUE_VALUES, (
            stem,
            present,
        )


# ---------------------------------------------------------------------------
# (c) call shape: every helper's only calls are isinstance / .isspace
# ---------------------------------------------------------------------------


def _helper_call_shape_failures(stem: str) -> list[tuple[str, ast.Call]]:
    """Return a list of (description, call_node) pairs for any call in
    ``_text_present`` that is not an ``isinstance`` Name call or a
    ``.isspace`` Attribute call."""
    path = COMMON_DIR / f"{stem}.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    bodies = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_text_present"
    ]
    if not bodies:
        return []
    helper = bodies[0]
    failures: list[tuple[str, ast.Call]] = []
    for call in ast.walk(helper):
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        if isinstance(func, ast.Name) and func.id == "isinstance":
            continue
        if isinstance(func, ast.Attribute) and func.attr == "isspace":
            continue
        if isinstance(func, ast.Name):
            failures.append((f"{stem}: call to Name {func.id!r}", call))
        elif isinstance(func, ast.Attribute):
            failures.append(
                (f"{stem}: call to .{func.attr!r} attribute", call)
            )
        else:
            failures.append((f"{stem}: call of unsupported shape", call))
    return failures


def test_r1_03_family_helper_call_shape():
    """FAMILY TEXT RULE v2: the only attribute call inside ``_text_present``
    is ``.isspace()``; the only Name call is ``isinstance``. Any other
    call (notably ``.strip()``) breaks this test. The message names the
    module and the call so a v1 body is unambiguous on the diff."""
    collected = _collect_helper_stems()
    all_failures: list[tuple[str, ast.Call]] = []
    for stem in sorted(collected):
        all_failures.extend(_helper_call_shape_failures(stem))
    if all_failures:
        msg = "\n".join(desc for desc, _ in all_failures)
        pytest.fail("FAMILY TEXT RULE v2 call-shape violations:\n" + msg)


# ---------------------------------------------------------------------------
# (d) helperless guards are a known subset
# ---------------------------------------------------------------------------


def test_r1_04_helperless_guards_are_known():
    """FAMILY TEXT RULE v2: any ``sni_*_guard.py`` that does NOT define
    ``_text_present`` is in the known helperless set. A sibling lane is
    adding helpers to ``sni_kpi_missingness_guard`` and
    ``sni_then_known_guard`` in parallel; this test only asserts the
    subset direction so that lane landing first never breaks it."""
    all_stems = {p.stem for p in COMMON_DIR.glob("sni_*_guard.py")}
    helper_stems = _collect_helper_stems()
    helperless = all_stems - helper_stems
    unknown = helperless - KNOWN_HELPERLESS_STEMS
    assert not unknown, (
        "unknown helperless guard(s): " + ", ".join(sorted(unknown))
    )
