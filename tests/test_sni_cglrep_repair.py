"""CGLREP repair tests for X8B-08, X8B-09, X8B-10 in the SNI literal scanner.

These tests pin the defects closed by the X8B-GUARD-REPAIR round 1. They
do not edit the existing tests in tests/test_sni_copy_guard_literals.py
and never pop, delete, or replace a sys.modules key. The module is
imported the same way the existing test file for the module does
(REPO/.../acceptance is added to sys.path, then `import
sni_copy_guard_literals as guard`).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPTANCE = REPO / "research" / "single_name_intelligence" / "acceptance"
sys.path.insert(0, str(ACCEPTANCE))

import sni_copy_guard_literals as guard  # noqa: E402

# Same wording the existing test file uses (no widening).
A14_SENTENCE = "Southbound holdings show smart money inflows."


# --- X8B-08: scan_tree never follows symlinks ----------------------------


def test_r1_08_scan_tree_skips_symlinked_file_and_dir(tmp_path: Path) -> None:
    """A symlinked file and a symlinked directory are not followed.

    Setup: one real file containing a forbidden literal, a symlink to that
    file, and a symlinked directory pointing at the root. Only the real
    file's finding should be reported.
    """
    target = tmp_path / "target.json"
    target.write_text(json.dumps({"k": A14_SENTENCE}), encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    linkdir = tmp_path / "linkdir"
    linkdir.symlink_to(tmp_path)

    observed = tuple(f.location for f in guard.scan_tree(tmp_path))
    assert observed == ("target.json#$.k",)


def test_r1_08_scan_tree_docstring_documents_symlink_skip() -> None:
    """The scan_tree docstring states that symlinks are skipped."""
    doc = guard.scan_tree.__doc__ or ""
    assert "symlink" in doc.lower()


# --- X8B-09: json_strings tolerates circular input -----------------------


def test_r1_09_json_strings_circular_dict_no_recursion_error() -> None:
    """A dict that contains itself yields no RecursionError."""
    circ: dict = {}
    circ["self"] = circ

    result = guard.json_strings(circ)
    assert isinstance(result, tuple)


def test_r1_09_json_strings_circular_list_no_recursion_error() -> None:
    """A list that contains itself yields no RecursionError."""
    lst: list = []
    lst.append(lst)

    result = guard.json_strings(lst)
    assert isinstance(result, tuple)


# --- X8B-10: json_strings skips non-str dict keys ------------------------


def test_r1_10_json_strings_skips_non_str_dict_keys() -> None:
    """Non-str dict keys do not raise; their values are still walked.

    RE-CHECK: {1: "x", "k": "y"} yields "x" and "y" without raising and
    without yielding 1.
    """
    result = guard.json_strings({1: "x", "k": "y"})
    values = tuple(v for _, v in result)
    assert "x" in values
    assert "y" in values
    assert 1 not in values