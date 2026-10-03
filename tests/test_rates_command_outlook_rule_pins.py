"""Recompute the producer rule pins cited by `tests/test_rates_command_outlook_readings.py`.

A pin locks the UTF-8 source of one top-level function, one top-level assignment,
or one dotted key in ``config.yml`` to a sha256, so the test reading the
version-2 mapping fails when any of those moves and the reviewer has not
recorded a fresh review entry in ``config/regime_outlook_rule_pins.json``.
Nothing in this file imports ``engine``; it parses each producer with ``ast``
and hashes the named node's source text by line range.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = REPO_ROOT / "config" / "regime_outlook_rule_pins.json"
MAPPING_PATH = REPO_ROOT / "config" / "regime_outlook_mapping_v2.json"
CONFIG_YML_PATH = REPO_ROOT / "config.yml"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load_pins() -> dict:
    return json.loads(PIN_PATH.read_text(encoding="utf-8"))


def _load_mapping() -> dict:
    return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))


def _node_lines(path: Path, lineno: int, end_lineno: int) -> list[str]:
    lines = path.read_text(encoding="utf-8").split("\n")
    return lines[lineno - 1 : end_lineno]


def _find_function_node(tree: ast.Module, name: str):
    return [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]


def _find_constant_node(tree: ast.Module, name: str):
    out = []
    for n in tree.body:
        if not isinstance(n, ast.Assign):
            continue
        for t in n.targets:
            if isinstance(t, ast.Name) and t.id == name:
                out.append(n)
    return out


def node_sha256(path: Path, name: str, kind: str) -> str:
    """Hash the named top-level node in ``path``.

    ``kind`` is ``"function"`` (an ``ast.FunctionDef``) or ``"constant"``
    (an ``ast.Assign`` with a single ``ast.Name`` target). Raises
    ``AssertionError`` naming the file and node when the count is not exactly
    one — that is the contract R-1 promise.
    """
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    if kind == "function":
        nodes = _find_function_node(tree, name)
    elif kind == "constant":
        nodes = _find_constant_node(tree, name)
    else:
        raise AssertionError(f"{path}: unknown kind {kind!r}")
    assert len(nodes) == 1, f"{path}: expected exactly one {kind} named {name!r}, found {len(nodes)}"
    node = nodes[0]
    lines = _node_lines(path, node.lineno, node.end_lineno)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def config_value(doc: object, key: list[str]) -> tuple[bool, object]:
    """Walk ``doc`` by ``key``; return ``(present, value)``.

    ``present`` is False and ``value`` is None if any step is missing.
    """
    cur = doc
    for step in key:
        if not isinstance(cur, dict) or step not in cur:
            return False, None
        cur = cur[step]
    return True, cur


def review_problems(review: object, pin_names: set[str]) -> list[str]:
    """Return a list of plain sentences describing problems with ``review``."""
    problems: list[str] = []
    if not isinstance(review, dict):
        problems.append("review is not a dict")
        return problems
    if "date" not in review or not isinstance(review["date"], str) or not _DATE_RE.match(review["date"]):
        problems.append(f"date {review.get('date')!r} does not match YYYY-MM-DD")
    if "reviewer" not in review or not isinstance(review["reviewer"], str) or not review["reviewer"]:
        problems.append("reviewer is missing or empty")
    if "finding" not in review or not isinstance(review["finding"], str) or not review["finding"]:
        problems.append("finding is missing or empty")
    changed = review.get("changed")
    if not isinstance(changed, list) or not changed:
        problems.append("changed is missing or empty")
    else:
        for entry in changed:
            if not isinstance(entry, str):
                problems.append(f"changed entry {entry!r} is not a string")
            elif entry not in pin_names:
                problems.append(f"changed entry {entry!r} is not a known pin name")
    return problems


# --- P1 ----------------------------------------------------------------------


def test_schema_and_mapping_link():
    pins = _load_pins()
    mapping = _load_mapping()
    assert pins["schema"] == "regime_outlook_rule_pins.v1"
    assert pins["mapping_version"] == mapping["mapping_version"]
    assert pins["pin_commit"] == mapping["producer_pin"]


# --- P2 / P3 -----------------------------------------------------------------


def _pin_names_for_functions(pins: dict) -> Iterable[tuple[str, dict]]:
    for entry in pins["functions"]:
        yield entry["name"], entry


@pytest.mark.parametrize(
    "entry",
    _load_pins()["functions"],
    ids=lambda e: f"{e['file']}:{e['name']}",
)
def test_function_pin_matches_source(entry):
    pins = _load_pins()
    file = entry["file"]
    name = entry["name"]
    actual = node_sha256(REPO_ROOT / file, name, "function")
    assert actual == entry["sha256"], (
        f"{file}:{name} changed since the pin. Re-read the rows it decides "
        f"({', '.join(entry['decides'])}) under contract rule R-E and record "
        f"the review in the pin file's reviews list. Never paste a new hash "
        f"without a review entry."
    )


@pytest.mark.parametrize(
    "entry",
    _load_pins()["constants"],
    ids=lambda e: f"{e['file']}:{e['name']}",
)
def test_constant_pin_matches_source(entry):
    file = entry["file"]
    name = entry["name"]
    actual = node_sha256(REPO_ROOT / file, name, "constant")
    assert actual == entry["sha256"], (
        f"{file}:{name} changed since the pin. Re-read the rows it decides "
        f"({', '.join(entry['decides'])}) under contract rule R-E and record "
        f"the review in the pin file's reviews list. Never paste a new hash "
        f"without a review entry."
    )


# --- P4 ----------------------------------------------------------------------


def _dotted(entry: dict) -> str:
    return ".".join(entry["key"])


@pytest.mark.parametrize(
    "entry",
    _load_pins()["config_values"],
    ids=_dotted,
)
def test_config_value_pin_matches(entry):
    file = entry["file"]
    dotted = _dotted(entry)
    raw = (REPO_ROOT / file).read_text(encoding="utf-8")
    doc = yaml.safe_load(raw)
    present, value = config_value(doc, entry["key"])
    assert present == entry["present"], (
        f"config value {dotted} changed since the pin. Re-read the rows it "
        f"decides ({', '.join(entry['decides'])}) under contract rule R-E and "
        f"record the review in the pin file's reviews list. Never paste a "
        f"new value without a review entry."
    )
    if entry["present"]:
        assert value == entry["value"] and type(value) is type(entry["value"]), (
            f"config value {dotted} changed since the pin. Re-read the rows "
            f"it decides ({', '.join(entry['decides'])}) under contract rule "
            f"R-E and record the review in the pin file's reviews list. Never "
            f"paste a new value without a review entry."
        )


# --- P5 ----------------------------------------------------------------------


def _all_decides(pins: dict) -> set[str]:
    out: set[str] = set()
    for section in ("functions", "constants", "config_values"):
        for entry in pins[section]:
            for row in entry["decides"]:
                out.add(row)
    return out


def test_decides_are_field_ids():
    pins = _load_pins()
    mapping = _load_mapping()
    field_ids = {f["field_id"] for f in mapping["fields"]}
    decided = _all_decides(pins)
    assert decided.issubset(field_ids), (
        f"decides entries not present as mapping field_id: "
        f"{sorted(decided - field_ids)}"
    )
    functions_decided = set()
    for entry in pins["functions"]:
        for row in entry["decides"]:
            functions_decided.add(row)
    missing = field_ids - functions_decided
    assert not missing, f"mapping field_id not decided by any function: {sorted(missing)}"


# --- P6 ----------------------------------------------------------------------


def _all_pin_names(pins: dict) -> set[str]:
    names: set[str] = set()
    for entry in pins["functions"]:
        names.add(f"{entry['file']}:{entry['name']}")
    for entry in pins["constants"]:
        names.add(f"{entry['file']}:{entry['name']}")
    for entry in pins["config_values"]:
        names.add(f"config.yml:{'.'.join(entry['key'])}")
    return names


def test_review_problems_synthetic():
    pins = _load_pins()
    pin_names = _all_pin_names(pins)
    sample_pin = next(iter(pin_names))

    valid = {
        "date": "2026-10-03",
        "reviewer": "qa",
        "finding": "ok",
        "changed": [sample_pin],
    }
    assert review_problems(valid, pin_names) == []

    no_finding = {**valid, "finding": ""}
    assert any("finding" in p for p in review_problems(no_finding, pin_names))

    empty_changed = {**valid, "changed": []}
    assert any("changed" in p for p in review_problems(empty_changed, pin_names))

    unknown_pin = {**valid, "changed": ["nonexistent:ghost"]}
    assert any("not a known pin" in p for p in review_problems(unknown_pin, pin_names))

    bad_type = "not a dict"
    assert any("not a dict" in p for p in review_problems(bad_type, pin_names))


def test_real_reviews_are_well_formed():
    pins = _load_pins()
    pin_names = _all_pin_names(pins)
    for i, review in enumerate(pins["reviews"]):
        problems = review_problems(review, pin_names)
        assert not problems, f"reviews[{i}] problems: {problems}"


# --- P7 ----------------------------------------------------------------------


def test_no_duplicate_pins():
    pins = _load_pins()
    func_keys = [(e["file"], e["name"]) for e in pins["functions"]]
    const_keys = [(e["file"], e["name"]) for e in pins["constants"]]
    cfg_keys = [tuple(e["key"]) for e in pins["config_values"]]
    assert len(set(func_keys)) == len(func_keys), "duplicate function pins"
    assert len(set(const_keys)) == len(const_keys), "duplicate constant pins"
    assert len(set(cfg_keys)) == len(cfg_keys), "duplicate config value pins"


# --- P8 ----------------------------------------------------------------------


def test_helper_detects_change_only(tmp_path):
    pins = _load_pins()
    src = REPO_ROOT / "engine" / "fed_path.py"
    original = src.read_text(encoding="utf-8")
    try:
        # (a) constant text change -> hash changes
        changed = original.replace("_QUARTER = 0.25", "_QUARTER = 0.50", 1)
        copy_a = tmp_path / "fed_path_a.py"
        copy_a.write_text(changed, encoding="utf-8")
        pin = next(e for e in pins["constants"] if e["name"] == "_QUARTER")
        new_hash = node_sha256(copy_a, "_QUARTER", "constant")
        assert new_hash != pin["sha256"]

        # (b) comment at the top of a fresh copy -> function hash unchanged
        commented = "# note\n" + original
        copy_b = tmp_path / "fed_path_b.py"
        copy_b.write_text(commented, encoding="utf-8")
        pin_compute = next(e for e in pins["functions"] if e["name"] == "compute")
        assert node_sha256(copy_b, "compute", "function") == pin_compute["sha256"]

        # (c) a second top-level def with the same name -> raises
        doubled = original + "\n\ndef compute():\n    pass\n"
        copy_c = tmp_path / "fed_path_c.py"
        copy_c.write_text(doubled, encoding="utf-8")
        with pytest.raises(AssertionError):
            node_sha256(copy_c, "compute", "function")
    finally:
        # nothing to restore — we wrote copies under tmp_path; src was never modified.
        del original


# --- P9 ----------------------------------------------------------------------


def test_no_engine_import():
    src = Path(__file__).read_text(encoding="utf-8")
    for line in src.splitlines():
        stripped = line.lstrip()
        assert not re.match(r"^(from|import)\s+engine\b", stripped), (
            f"this test must not import engine: {line!r}"
        )