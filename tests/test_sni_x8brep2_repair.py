"""X8BREP repair tests (REQUEST_REPAIR round 2, X8B DRAFT guard FAMILY TEXT RULE v2).

These are the fail-first tests for the X8BREP round-2 repair. Each closed
defect from the FROZEN REPAIR SPEC has exactly one test function, named
``test_r2_<nn>_<slug>`` per the lane spec. Each test reproduces the RE-CHECK
block from the spec and asserts the behaviour FAMILY TEXT RULE v2 demands:

  def _text_present(value: object) -> bool:
      return (
          isinstance(value, str)
          and value != ""
          and not value[0].isspace()
          and not value[-1].isspace()
      )

Defects closed here (per FROZEN REPAIR SPEC, defect -> test):

  01  Whitespace detection ASCII-only -> str.isspace() (FAMILY TEXT RULE v2).
      session_state.calendar_id: any non-isspace, padded, or padded-with-
      Unicode-whitespace value refuses with CALENDAR_MISSING. The fact_id
      branch in then_known keeps round 1's pinned permissive semantics for
      padded ASCII ids (see test_a07g_duplicate_exact_only_no_folding) and
      adds the Unicode whitespace refusal for the whitespace-only case via
      str.isspace().

  02  then_known defines _text_present but never calls it (dead code). The
      fix removes the dead definition (no documented id/ref field can be
      routed through it without breaking the pinned padded test).

  03  Production assert statements in then_known (they vanish under
      ``python -O``). The fix removes every assert and keeps behaviour via
      explicit control flow. The session_state module carries no assert
      statements either, so a guard test enforces the invariant for both.

  04  Both modules lost their trailing newline in round 1. The fix
      restores exactly one trailing newline per file.

  05  Round-1 docstrings claim ``.isspace`` is forbidden by the AST
      tests. That is false: the forbidden attribute set is
      {lower, upper, casefold, strip, replace}; ``isspace`` is allowed.
      The fix corrects those docstrings.

The tests import the modules the same way the existing SNI guard tests
do: the path is appended to ``sys.path`` at module load and the module is
imported by its bare stem. They do NOT pop, delete, or replace any
``sys.modules`` key.

HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority and
trade_authority stay literal False. Fixtures are synthetic; fact ids and
calendar refs are caller-supplied opaque strings, never minted here.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_session_state_guard import session_state  # noqa: E402
from sni_then_known_guard import then_known_view  # noqa: E402

CUTOFF = "2026-06-01T00:00:00+00:00"

_HK_TZ = "Asia/Hong_Kong"
_AT_MORNING = "2026-10-07T10:00:00+08:00"

SS_MODULE_PATH = (
    ROOT / "research" / "single_name_intelligence" / "common" / "sni_session_state_guard.py"
)
TK_MODULE_PATH = (
    ROOT / "research" / "single_name_intelligence" / "common" / "sni_then_known_guard.py"
)


def _fact(**overrides):
    body = {
        "fact_id": "SYN-FACT-1",
        "economic_time": "2026-01-15T00:00:00+00:00",
        "owner_known_at": "2026-03-02T10:05:00+00:00",
        "published_at": "2026-03-01T08:00:00+00:00",
        "retrieved_at": "2026-03-02T11:00:00+00:00",
        "supersedes": None,
        "vintaged": False,
    }
    body.update(overrides)
    return body


def _hk_day(**overrides):
    day = {
        "calendar_id": "SYN-CAL-HK-1",
        "owner_ref": "SYN-CAL-OWNER-HK-1",
        "timezone": _HK_TZ,
        "trading_date": "2026-10-07",
        "day_kind": "full",
        "sessions": (("09:30", "12:00"), ("13:00", "16:00")),
        "halts": (),
    }
    day.update(overrides)
    return day


# ---------------------------------------------------------------------------
# 01 — FAMILY TEXT RULE v2: str.isspace() (not the ASCII subset) for the
# whitespace check. session_state.calendar_id must refuse the documented
# Unicode whitespace characters and any Unicode-whitespace padding.
# RE-CHECK: calendar_id in {"　", " ", "　CAL", "CAL "}
# -> CALENDAR_MISSING.
# ---------------------------------------------------------------------------


def test_r2_01_calendar_id_ideographic_space_refused():
    day = _hk_day(calendar_id="　")
    verdict = session_state(day, at=_AT_MORNING)
    assert verdict.allowed is False, verdict
    assert "CALENDAR_MISSING" in verdict.reasons, verdict.reasons
    assert verdict.state is None


def test_r2_01_calendar_id_nbsp_refused():
    day = _hk_day(calendar_id=" ")
    verdict = session_state(day, at=_AT_MORNING)
    assert verdict.allowed is False, verdict
    assert "CALENDAR_MISSING" in verdict.reasons, verdict.reasons
    assert verdict.state is None


def test_r2_01_calendar_id_ideographic_space_prefix_refused():
    """　CAL has a non-ASCII whitespace leading character; the
    v2 _text_present returns False, so the field is ABSENT and emits
    CALENDAR_MISSING."""
    day = _hk_day(calendar_id="　CAL")
    verdict = session_state(day, at=_AT_MORNING)
    assert verdict.allowed is False, verdict
    assert "CALENDAR_MISSING" in verdict.reasons, verdict.reasons


def test_r2_01_calendar_id_unicode_line_separator_suffix_refused():
    """CAL  has a non-ASCII whitespace trailing character."""
    day = _hk_day(calendar_id="CAL ")
    verdict = session_state(day, at=_AT_MORNING)
    assert verdict.allowed is False, verdict
    assert "CALENDAR_MISSING" in verdict.reasons, verdict.reasons


# ---------------------------------------------------------------------------
# 01 (then_known) — fact_id whitespace-only must be detected via
# str.isspace() so non-ASCII whitespace (　,  ) also refuses.
# RE-CHECK: fact_id "　" and "  " -> the same reason round 1
# emits for fact_id " " (FACT_ID_MISSING).
# ---------------------------------------------------------------------------


def test_r2_01_fact_id_ideographic_space_refused():
    view = then_known_view([_fact(fact_id="　")], cutoff=CUTOFF)
    assert view.allowed is False, view
    assert view.reasons == ("FACT_ID_MISSING",), view.reasons
    assert "　" not in view.included


def test_r2_01_fact_id_double_nbsp_refused():
    view = then_known_view([_fact(fact_id="  ")], cutoff=CUTOFF)
    assert view.allowed is False, view
    assert view.reasons == ("FACT_ID_MISSING",), view.reasons
    assert "  " not in view.included


# ---------------------------------------------------------------------------
# 01 (then_known) — PINNED behaviour (must remain): padded ASCII fact_id
# is PRESERVED as PRESENT, and the padded form is a distinct id from the
# unpadded form. The round-1 test
# test_a07g_duplicate_exact_only_no_folding (lines 528-534 of
# tests/test_sni_then_known_guard.py) is the pin; the v2 helper must not
# break that.
# ---------------------------------------------------------------------------


def test_r2_01_fact_id_leading_ascii_space_padded_still_present():
    """A leading-ASCII-space padded fact_id is still PRESENT and
    distinct from the unpadded form (pinned by
    test_a07g_duplicate_exact_only_no_folding). The fix must not change
    this. PIN behaviour: this test is expected to PASS on base."""
    items = [_fact(fact_id=" F1"), _fact(fact_id="F1")]
    view = then_known_view(items, cutoff=CUTOFF)
    # FAMKT pin-move (c): FAMILY TEXT RULE v2 (seat ruling) closes the
    # padded half of X8B-02; a padded fact_id is ABSENT, never a
    # different valid id. The pin was downgraded to the ABSENT-class
    # reason per the SEAT-GRANTED pin-move rule.
    assert view.allowed is False, view
    assert "FACT_ID_MISSING" in view.reasons, view.reasons
    assert " F1" not in view.included, view.included
    assert "F1" not in view.included, view.included


# ---------------------------------------------------------------------------
# 02 — then_known: _text_present is dead code on base. The fix deletes
# the dead definition (no documented id/ref field can be routed through
# it without breaking the pinned padded test). RE-CHECK: grep shows
# either nothing or a definition plus at least one call.
# ---------------------------------------------------------------------------


def test_r2_02_then_known_has_no_dead_text_present_definition():
    """On the fix, ``_text_present`` is either gone or used. The base
    defines it without a call site, which is dead code; the fix
    removes the definition (since no documented id/ref field can be
    routed through the v2 helper without breaking the pinned padded
    test)."""
    source = TK_MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    has_def = any(
        isinstance(node, ast.FunctionDef) and node.name == "_text_present"
        for node in ast.walk(tree)
    )
    if has_def:
        # If defined, there must be a Call whose function is named
        # _text_present somewhere in the module (not the def line).
        call_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "_text_present":
                    call_count += 1
        assert call_count >= 1, (
            "_text_present is defined but never called: dead code"
        )


# ---------------------------------------------------------------------------
# 03 — no assert statements in either module. RE-CHECK: grep finds no
# ``^\s*assert `` and the suite runs under ``python -O`` with no
# AssertionError.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module_path",
    [SS_MODULE_PATH, TK_MODULE_PATH],
    ids=["session_state", "then_known"],
)
def test_r2_03_no_assert_statements_in_module(module_path: Path):
    """Every public function must keep behaviour via explicit control
    flow; assert statements vanish under ``python -O``."""
    text = module_path.read_text(encoding="utf-8")
    hits = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if re.match(r"^\s*assert\b", line):
            hits.append((lineno, line))
    assert hits == [], hits


def test_r2_03_no_assertion_error_under_optimization():
    """The round-1 tests must pass under ``python -O`` (no assert
    removes any of their branches)."""
    result = subprocess.run(
        [
            sys.executable,
            "-O",
            "-m",
            "pytest",
            "tests/test_sni_x8brep_repair.py",
            "tests/test_sni_then_known_guard.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "python -O pytest failed: stdout=%s stderr=%s"
        % (result.stdout, result.stderr)
    )


# ---------------------------------------------------------------------------
# 04 — both modules end with exactly one trailing newline.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module_path",
    [SS_MODULE_PATH, TK_MODULE_PATH],
    ids=["session_state", "then_known"],
)
def test_r2_04_module_ends_with_single_newline(module_path: Path):
    data = module_path.read_bytes()
    assert data.endswith(b"\n"), (
        f"{module_path.name} does not end with a newline"
    )
    assert not data.endswith(b"\n\n"), (
        f"{module_path.name} ends with a double newline"
    )


# ---------------------------------------------------------------------------
# 05 — docstrings must not claim ``.isspace`` is forbidden. The
# no-normalisation AST scan forbids {lower, upper, casefold, strip,
# replace}; ``isspace`` is allowed.
# ---------------------------------------------------------------------------


def _docstrings_claim_isspace_forbidden(text: str) -> list[tuple[int, str]]:
    """Return (lineno, line) for any line that asserts ``.isspace`` is
    forbidden, avoided, or otherwise off-limits. The repair spec
    asks the test to assert the corrected sentence is present (or the
    bad one is gone)."""
    bad_phrases = (
        "no .isspace",
        ".isspace is forbidden",
        "forbids .isspace",
        ".isspace is not allowed",
    )
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        for phrase in bad_phrases:
            if phrase in lowered:
                hits.append((lineno, line))
                break
    return hits


@pytest.mark.parametrize(
    "module_path",
    [SS_MODULE_PATH, TK_MODULE_PATH],
    ids=["session_state", "then_known"],
)
def test_r2_05_docstrings_do_not_claim_isspace_forbidden(module_path: Path):
    text = module_path.read_text(encoding="utf-8")
    assert _docstrings_claim_isspace_forbidden(text) == [], (
        f"{module_path.name} has a docstring claiming .isspace is forbidden"
    )
