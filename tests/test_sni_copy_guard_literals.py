"""A14/A30 SNI literal copy-guard tests (JSON values, Python constants).

SNI-local DRAFT contract tests. They extend the sni_copy_guard test family
to JSON string values and Python string constants, reusing the existing
guard rules by import. They never mint issuer or security ids (Stock
Identity / Data OS owns those opaque strings). HISTORICAL-DESCRIPTIVE only:
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False. Fixtures are
synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path. The scanner is a lexical copy check.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPTANCE = REPO / "research" / "single_name_intelligence" / "acceptance"
SNI_ROOT = REPO / "research" / "single_name_intelligence"
sys.path.insert(0, str(ACCEPTANCE))

import sni_copy_guard_literals as guard  # noqa: E402

# Wording the existing sni_copy_guard tables already reject (do not widen).
A14_SENTENCE = "Southbound holdings show smart money inflows."
A30_SENTENCE = "The retired factor predicts returns."
A30_SENTENCE_2 = "A NO-GO screen stays predictive."
CLEAN_SENTENCE = "The holdings table lists reported share counts."

# Frozen pin over the committed SNI tree: scan_tree over
# research/single_name_intelligence/ returned ZERO findings at commit time
# (runs/ is skipped by design; markdown is the other guard's scope). Empty
# is a real observation, not a placeholder: a later edit that introduces
# live-flow/intent or failed-state/forecast-success wording into a JSON
# value or Python constant under the tree MUST change this pin consciously
# (either fix the wording or pin the new finding here).
PINNED_FINDINGS: tuple[tuple[str, str], ...] = ()


# --- authority T3 ---------------------------------------------------------


def test_authority_flags_all_literal_false() -> None:
    assert set(guard.AUTHORITY_FLAGS) == {
        "rank_authority",
        "gate_authority",
        "size_authority",
        "signal_authority",
        "escalation_authority",
        "trade_authority",
    }
    assert all(value is False for value in guard.AUTHORITY_FLAGS.values())


def test_authority_flags_mapping_is_frozen() -> None:
    with pytest.raises(TypeError):
        guard.AUTHORITY_FLAGS["rank_authority"] = True  # type: ignore[index]


def test_refuse_nonfalse_authority_raises_on_any_true_flag() -> None:
    for name in guard.AUTHORITY_FLAGS:
        with pytest.raises(ValueError):
            guard.refuse_nonfalse_authority({name: True})


def test_refuse_nonfalse_authority_accepts_false_and_none() -> None:
    guard.refuse_nonfalse_authority(None)
    guard.refuse_nonfalse_authority({name: False for name in guard.AUTHORITY_FLAGS})
    with pytest.raises(ValueError):
        guard.refuse_nonfalse_authority("not-a-mapping")  # type: ignore[arg-type]


# --- json_strings ---------------------------------------------------------


def test_json_strings_root_string() -> None:
    assert guard.json_strings("just text") == (("$", "just text"),)


def test_json_strings_flat_dict_sorted_keys() -> None:
    obj = {"b": "two", "a": "one", "c": 3}
    assert guard.json_strings(obj) == (("$.a", "one"), ("$.b", "two"))


def test_json_strings_nested_paths() -> None:
    obj = {"store": {"book": {"title": "T", "tags": ["x", "y"]}}}
    assert guard.json_strings(obj) == (
        ("$.store.book.tags[0]", "x"),
        ("$.store.book.tags[1]", "y"),
        ("$.store.book.title", "T"),
    )


def test_json_strings_list_indices_in_order() -> None:
    obj = ["c", "a", "b"]
    assert guard.json_strings(obj) == (
        ("$[0]", "c"),
        ("$[1]", "a"),
        ("$[2]", "b"),
    )


def test_json_strings_values_not_keys() -> None:
    obj = {"holdings": 1}
    assert guard.json_strings(obj) == ()


def test_json_strings_non_string_scalars_ignored() -> None:
    obj = {"i": 7, "f": 1.5, "t": True, "n": None, "s": "keep"}
    assert guard.json_strings(obj) == (("$.s", "keep"),)


def test_json_strings_bracket_key_for_odd_keys() -> None:
    obj = {"odd key.d": "v", "9lead": "w"}
    assert guard.json_strings(obj) == (("$['9lead']", "w"), ("$['odd key.d']", "v"))


# --- python_strings -------------------------------------------------------


def test_python_strings_simple_constants_with_lineno() -> None:
    source = 'A = "one"\nB = 2\nC = "two"\n'
    assert guard.python_strings(source) == ((1, "one"), (3, "two"))


def test_python_strings_excludes_module_docstring() -> None:
    source = '"""Module doc mentioning holdings and inflows."""\nA = "keep"\n'
    assert guard.python_strings(source) == ((2, "keep"),)


def test_python_strings_excludes_function_docstring() -> None:
    source = (
        "def f():\n"
        '    """Docstring with holdings inflows."""\n'
        '    return "keep"\n'
    )
    assert guard.python_strings(source) == ((3, "keep"),)


def test_python_strings_excludes_class_docstring() -> None:
    source = "class C:\n    \"\"\"Class doc holdings inflows.\"\"\"\n    X = \"keep\"\n"
    assert guard.python_strings(source) == ((3, "keep"),)


def test_python_strings_excludes_dunder_main_block() -> None:
    source = (
        'TOP = "keep"\n'
        "if __name__ == \"__main__\":\n"
        '    HIDDEN = "holdings inflows"\n'
        '    ALSO = "retired predicts"\n'
    )
    assert guard.python_strings(source) == ((1, "keep"),)


def test_python_strings_dunder_main_reversed_operand_order() -> None:
    source = 'if "__main__" == __name__:\n    HIDDEN = "holdings inflows"\n'
    assert guard.python_strings(source) == ()


def test_python_strings_includes_fstring_constant_segments_only() -> None:
    source = 'S = f"prefix {name} suffix"\n'
    assert guard.python_strings(source) == ((1, "prefix "), (1, " suffix"))


def test_python_strings_deterministic_order() -> None:
    source = 'B = "b"\nA = "a"\nC = "c"\n'
    first = guard.python_strings(source)
    assert first == ((1, "b"), (2, "a"), (3, "c"))
    assert guard.python_strings(source) == first


# --- scan_text_items ------------------------------------------------------


def test_scan_text_items_a14_fires_with_excerpt() -> None:
    findings = guard.scan_text_items(
        (("app#$.note", A14_SENTENCE),), rules=guard.DEFAULT_RULES
    )
    assert len(findings) == 1
    hit = findings[0]
    assert hit.location == "app#$.note"
    assert hit.rule_id == "A14"
    assert hit.excerpt == A14_SENTENCE
    with pytest.raises(dataclasses.FrozenInstanceError):
        hit.excerpt = "mutated"  # type: ignore[misc]


def test_scan_text_items_a30_fires() -> None:
    findings = guard.scan_text_items(
        (("m.py:4", A30_SENTENCE),), rules=guard.DEFAULT_RULES
    )
    assert [(f.location, f.rule_id) for f in findings] == [("m.py:4", "A30")]


def test_scan_text_items_clean_text_returns_empty() -> None:
    assert guard.scan_text_items((("x", CLEAN_SENTENCE),), rules=guard.DEFAULT_RULES) == ()


def test_scan_text_items_rule_order_a14_before_a30() -> None:
    both = "Holdings inflows, and the retired factor predicts returns."
    findings = guard.scan_text_items((("z", both),), rules=guard.DEFAULT_RULES)
    assert [f.rule_id for f in findings] == ["A14", "A30"]


def test_scan_text_items_excerpt_collapsed_and_capped() -> None:
    long_text = "word " * 40 + A14_SENTENCE
    findings = guard.scan_text_items((("z", long_text),), rules=guard.DEFAULT_RULES)
    assert len(findings) == 1
    assert len(findings[0].excerpt) <= 80
    assert findings[0].excerpt.startswith("word word")


# --- scan_tree on synthetic tmp trees --------------------------------------


def test_scan_tree_synthetic_json_a14(tmp_path: Path) -> None:
    (tmp_path / "app.json").write_text(
        json.dumps({"note": A14_SENTENCE, "safe": CLEAN_SENTENCE}), encoding="utf-8"
    )
    findings = guard.scan_tree(tmp_path)
    assert [(f.location, f.rule_id) for f in findings] == [("app.json#$.note", "A14")]


def test_scan_tree_synthetic_python_constants(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text(
        '"""Doc holdings inflows."""\n'
        f'NOTE = "{A14_SENTENCE}"\n'
        f'WARN = "{A30_SENTENCE_2}"\n'
        'if __name__ == "__main__":\n    HIDDEN = "main holdings inflows"\n',
        encoding="utf-8",
    )
    findings = guard.scan_tree(tmp_path)
    assert [(f.location, f.rule_id) for f in findings] == [
        ("m.py:2", "A14"),
        ("m.py:3", "A30"),
    ]


def test_scan_tree_clean_tree_empty(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text(json.dumps({"k": CLEAN_SENTENCE}), encoding="utf-8")
    (tmp_path / "b.py").write_text(f'SAFE = "{CLEAN_SENTENCE}"\n', encoding="utf-8")
    assert guard.scan_tree(tmp_path) == ()


def test_scan_tree_skips_runs_directory(tmp_path: Path) -> None:
    sealed = tmp_path / "runs" / "s1"
    sealed.mkdir(parents=True)
    sealed.joinpath("sealed.json").write_text(
        json.dumps({"k": A14_SENTENCE}), encoding="utf-8"
    )
    assert guard.scan_tree(tmp_path) == ()


def test_scan_tree_skips_tests_fixtures_directory(tmp_path: Path) -> None:
    fixtures = tmp_path / "tests" / "fixtures"
    fixtures.mkdir(parents=True)
    fixtures.joinpath("adversarial.py").write_text(f'X = "{A14_SENTENCE}"\n', encoding="utf-8")
    assert guard.scan_tree(tmp_path) == ()


def test_scan_tree_sorted_path_order(tmp_path: Path) -> None:
    (tmp_path / "b.json").write_text(json.dumps({"k": A14_SENTENCE}), encoding="utf-8")
    (tmp_path / "a.py").write_text(f'K = "{A14_SENTENCE}"\n', encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    sub.joinpath("c.json").write_text(json.dumps({"k": A14_SENTENCE}), encoding="utf-8")
    locations = [f.location for f in guard.scan_tree(tmp_path)]
    assert locations == sorted(locations)
    assert locations == ["a.py:1", "b.json#$.k", "sub/c.json#$.k"]


def test_scan_tree_skips_unparseable_files(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "broken.py").write_text("def (:\n", encoding="utf-8")
    (tmp_path / "good.py").write_text(f'K = "{A14_SENTENCE}"\n', encoding="utf-8")
    assert [(f.location, f.rule_id) for f in guard.scan_tree(tmp_path)] == [("good.py:1", "A14")]


# --- pin over the committed SNI tree ---------------------------------------


def test_pin_sni_tree_findings_frozen() -> None:
    findings = guard.scan_tree(SNI_ROOT)
    observed = tuple(sorted((f.location, f.rule_id) for f in findings))
    assert observed == PINNED_FINDINGS, (
        "The SNI literal copy pin changed: new wording under "
        "research/single_name_intelligence/ (JSON value or Python constant) "
        "must be fixed consciously or re-pinned in PINNED_FINDINGS"
    )


# --- static scan T4 --------------------------------------------------------


def test_static_scan_module_has_no_ticker_literals() -> None:
    source = (ACCEPTANCE / "sni_copy_guard_literals.py").read_text(encoding="utf-8")
    for ticker in ("0700", "9988", "3690", "BABA", "TCEHY", "0700.HK"):
        assert ticker not in source


def test_static_scan_module_no_writes_no_wall_clock() -> None:
    source = (ACCEPTANCE / "sni_copy_guard_literals.py").read_text(encoding="utf-8")
    assert "write_text" not in source
    assert "open(" not in source
    for clock in ("import time", "datetime", "perf_counter", "monotonic"):
        assert clock not in source
