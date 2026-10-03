"""Regime outlook readings — what a set of owner files reads as (display research).

``engine/rates_command_outlook.py`` turns the owner verdicts named by the
mapping into one of four words per path condition — fits, does not fit, not
discriminating, unknown — and rolls them up by evidence family inside each
path. These tests hold that reader to three things written before it was:

* the contract's own worked example at the producer pin (Appendix A.6);
* a recorded set of owner files at that pin, and what each of some sixty
  changed or broken inputs must read as
  (``tests/fixtures/regime_outlook/readings_golden_v1.json``, produced by a
  separate evaluator, never by the module under test);
* the contract's closed word lists.

A reading says which word an owner published. It is not a forecast, a rank or
a score, and nothing here compares one path with another.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from engine import rates_command_outlook as rco  # noqa: E402

GOLDEN_PATH = REPO / "tests" / "fixtures" / "regime_outlook" / "readings_golden_v1.json"
GOLDEN_SHA256 = "84482555dcafe8e1e677acbd04232b6cf069f7cb3e2e8b9ca02feed05db9e072"
CONTRACT_PATH = (
    REPO / "research" / "macro_regime_intelligence" / "STATE_PATH_AND_SCIENCE_CONTRACT_2026-10-03.md"
)

GOLDEN = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
MAPPING = rco.load_mapping()
CASES = {case["name"]: case for case in GOLDEN["cases"]}

ADMISSION_ISSUES = {
    "missing",
    "owner_default_on_missing",
    "contains_sign_only_leg",
    "owner_sign_inconsistent",
    "owner_did_not_write",
    "partial",
    "malformed",
}
UNREADABLE_STATUSES = ("missing", "unknown_date", "future_dated", "stale", "partial")


def _selected(item, selector):
    return isinstance(item, dict) and all(item.get(key) == value for key, value in selector.items())


def _edited(base, edits):
    """A copy of the recorded owner files with one case's edits applied."""
    docs = copy.deepcopy(base)
    for edit in edits:
        if edit["op"] == "drop_artifact":
            docs[edit["artifact"]] = None
            continue
        node = docs[edit["artifact"]]
        *parents, last = edit["path"]
        for segment in parents:
            if isinstance(segment, dict):
                (node,) = [item for item in node if _selected(item, segment)]
            else:
                node = node[segment]
        if edit["op"] == "set":
            node[last] = edit["value"]
        elif isinstance(last, dict):
            node[:] = [item for item in node if not _selected(item, last)]
        else:
            del node[last]
    return docs


def _observed(docs, unreadable=None):
    paths = rco.read_paths(MAPPING, docs, unreadable=unreadable or None)
    return {
        "fields": rco.admit_fields(MAPPING, docs),
        "conditions": {
            condition["condition_id"]: [condition["reading"], condition["reason"]]
            for path in paths
            for condition in path["conditions"]
        },
        "family_readings": {
            path["path_id"]: {row["evidence_family_id"]: row["reading"] for row in path["family_readings"]}
            for path in paths
        },
    }


def _expected(case):
    expected = copy.deepcopy(GOLDEN["pin"])
    for key, changed in case["changes"].items():
        expected[key].update(changed)
    return expected


# --- the recorded file is the reviewed one, and belongs to this mapping --------


def test_golden_file_is_the_reviewed_one():
    assert hashlib.sha256(GOLDEN_PATH.read_bytes()).hexdigest() == GOLDEN_SHA256


def test_golden_belongs_to_this_reading_table():
    assert GOLDEN["mapping_version"] == rco.MAPPING_VERSION
    assert GOLDEN["producer_pin"] == MAPPING["producer_pin"]
    assert GOLDEN["reading_table_sha256"] == rco.reading_table_sha256(MAPPING)


# --- readings at the pin ------------------------------------------------------


def test_readings_at_the_pin_equal_the_recorded_ones():
    assert _observed(GOLDEN["base"]) == GOLDEN["pin"]


def _worked_example():
    """Appendix A.6 as {condition: reading} and {path: {family: reading}}."""
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    section = text[text.index("### A.6 ") :]
    words = "fits|does_not_fit|not_discriminating|unknown|mixed"
    order = {path["path_id"]: [c["condition_id"] for c in path["conditions"]] for path in MAPPING["paths"]}
    conditions, families = {}, {}
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or not cells[0].startswith("`"):
            continue
        path_id = cells[0].strip("`")
        ids = order[path_id]
        for part in re.sub(r"\([^()]*\)", "", cells[1]).split(";"):
            word = re.search(rf"\b({words})\b", part).group(1)
            span = re.search(r"([A-Z]{2}-\d) to ([A-Z]{2}-\d)", part)
            if span:
                named = ids[ids.index(span.group(1)) : ids.index(span.group(2)) + 1]
            else:
                named = re.findall(r"[A-Z]{2}-\d", part)
            for condition_id in named:
                conditions[condition_id] = word
        families[path_id] = {}
        for part in cells[2].split(";"):
            word = re.search(rf"\b({words})\b\s*$", part.strip()).group(1)
            for family in re.findall(r"`([a-z_]+)`", part):
                families[path_id][family] = word
    return conditions, families


def test_worked_example_parses_to_every_condition_and_path():
    conditions, families = _worked_example()
    assert len(conditions) == 50
    assert list(families) == [path["path_id"] for path in MAPPING["paths"]]


def test_readings_at_the_pin_equal_the_contract_s_worked_example():
    conditions, families = _worked_example()
    observed = _observed(GOLDEN["base"])
    assert {key: value[0] for key, value in observed["conditions"].items()} == conditions
    assert observed["family_readings"] == families


# --- changed and broken inputs -------------------------------------------------


@pytest.mark.parametrize("name", sorted(CASES))
def test_a_changed_or_broken_input_reads_as_recorded(name):
    case = CASES[name]
    observed = _observed(_edited(GOLDEN["base"], case["edits"]), case["unreadable"])
    expected = _expected(case)
    for key in ("fields", "conditions", "family_readings"):
        differing = {
            item: (observed[key].get(item), expected[key][item])
            for item in expected[key]
            if observed[key].get(item) != expected[key][item]
        }
        assert not differing, f"{name}: {key} (observed, expected) {differing}"
        assert set(observed[key]) == set(expected[key])


def test_the_recorded_cases_exercise_every_guard_and_every_issue():
    guards = {field["field_id"]: field["guard"]["kind"] for field in MAPPING["fields"]}
    refused_guards, issues = set(), set()
    for case in GOLDEN["cases"]:
        for field_id, admission in case["changes"]["fields"].items():
            if not admission["admitted"]:
                refused_guards.add(guards[field_id])
                issues.add(admission["issue"])
    assert refused_guards == set(guards.values())
    assert issues == ADMISSION_ISSUES


# --- shape: fixed order, closed words, no totals --------------------------------


def test_paths_and_conditions_keep_the_mapping_s_order_and_carry_nothing_else():
    paths = rco.read_paths(MAPPING, GOLDEN["base"])
    assert [path["path_id"] for path in paths] == [path["path_id"] for path in MAPPING["paths"]]
    for path, authored in zip(paths, MAPPING["paths"]):
        assert set(path) == {"path_id", "family", "conditions", "family_readings"}
        assert path["family"] == authored["family"]
        assert [
            (c["condition_id"], c["statement_id"], c["field_id"]) for c in path["conditions"]
        ] == [(c["condition_id"], c["statement_id"], c["field_id"]) for c in authored["conditions"]]
        for condition in path["conditions"]:
            assert set(condition) == {"condition_id", "statement_id", "field_id", "reading", "reason"}
        first_seen = list(dict.fromkeys(c["evidence_family_id"] for c in authored["conditions"]))
        assert [row["evidence_family_id"] for row in path["family_readings"]] == first_seen
        for row in path["family_readings"]:
            assert set(row) == {"evidence_family_id", "reading"}


def _every_run():
    yield "pin", _observed(GOLDEN["base"])
    for name, case in CASES.items():
        yield name, _observed(_edited(GOLDEN["base"], case["edits"]), case["unreadable"])


def test_a_reason_is_given_exactly_when_a_reading_is_unknown():
    for name, observed in _every_run():
        for condition_id, (reading, reason) in observed["conditions"].items():
            assert reading in rco.READINGS, (name, condition_id)
            assert (reason is None) == (reading != "unknown"), (name, condition_id, reading, reason)
            assert reason is None or reason in rco.READING_REASONS, (name, condition_id, reason)
        for path_id, families in observed["family_readings"].items():
            assert set(families.values()) <= set(rco.FAMILY_READINGS), (name, path_id)
        for field_id, admission in observed["fields"].items():
            assert set(admission) == {"admitted", "token", "issue"}, (name, field_id)
            assert (admission["issue"] is None) == admission["admitted"], (name, field_id)
            assert admission["admitted"] or admission["token"] is None, (name, field_id)


def test_reasons_are_the_contract_s_words_and_no_others():
    assert tuple(rco.UNREADABLE_STATUSES) == UNREADABLE_STATUSES
    assert set(rco.READING_REASONS) == set(rco.OPEN_REASONS) | ADMISSION_ISSUES | set(UNREADABLE_STATUSES)
    assert len(set(rco.READING_REASONS)) == len(rco.READING_REASONS)
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    section = text[text.index("## 4. Clocks and statuses") : text.index("## 5. ")]
    for word in rco.READING_REASONS:
        assert f"`{word}`" in section, word


# --- the family roll-up (contract rule R-D) -----------------------------------


@pytest.mark.parametrize(
    "readings, expected",
    [
        (["fits"], "fits"),
        (["fits", "fits"], "fits"),
        (["does_not_fit", "unknown"], "does_not_fit"),
        (["fits", "not_discriminating", "unknown"], "fits"),
        (["fits", "does_not_fit"], "mixed"),
        (["does_not_fit", "fits", "fits"], "mixed"),
        (["not_discriminating"], "not_discriminating"),
        (["unknown", "not_discriminating"], "not_discriminating"),
        (["unknown"], "unknown"),
        (["unknown", "unknown"], "unknown"),
        ([], "unknown"),
    ],
)
def test_family_roll_up(readings, expected):
    assert rco.roll_up(readings) == expected


def test_roll_up_refuses_a_word_outside_the_list():
    with pytest.raises(ValueError):
        rco.roll_up(["fits", "supports"])


# --- inputs: untouched, absent, wrong shape, unreadable -----------------------


def test_inputs_are_left_untouched():
    docs = copy.deepcopy(GOLDEN["base"])
    mapping = copy.deepcopy(MAPPING)
    rco.admit_fields(mapping, docs)
    rco.read_paths(mapping, docs, unreadable={"L.state": "stale"})
    assert docs == GOLDEN["base"]
    assert mapping == MAPPING


@pytest.mark.parametrize("artifact", sorted(MAPPING["artifacts"]))
@pytest.mark.parametrize("wrong", [[], "text", 3, True])
def test_an_absent_or_wrong_shaped_file_reads_as_missing(artifact, wrong):
    dropped = copy.deepcopy(GOLDEN["base"])
    dropped[artifact] = None
    expected = _observed(dropped)

    without_key = copy.deepcopy(GOLDEN["base"])
    del without_key[artifact]
    assert _observed(without_key) == expected

    misshapen = copy.deepcopy(GOLDEN["base"])
    misshapen[artifact] = wrong
    assert _observed(misshapen) == expected


READ_FIELDS = sorted(
    {c["field_id"] for path in MAPPING["paths"] for c in path["conditions"] if c["field_id"]}
)


@pytest.mark.parametrize("field_id", READ_FIELDS)
@pytest.mark.parametrize("status", UNREADABLE_STATUSES)
def test_an_unreadable_field_is_unknown_wherever_it_is_read(field_id, status):
    pin = GOLDEN["pin"]["conditions"]
    observed = _observed(GOLDEN["base"], {field_id: status})["conditions"]
    uses = {
        c["condition_id"] for path in MAPPING["paths"] for c in path["conditions"] if c["field_id"] == field_id
    }
    assert uses
    for condition_id, value in observed.items():
        if condition_id in uses:
            assert value == ["unknown", status], condition_id
        else:
            assert value == pin[condition_id], condition_id


def test_unreadable_does_not_change_what_the_owner_published():
    assert rco.admit_fields(MAPPING, GOLDEN["base"]) == GOLDEN["pin"]["fields"]
    observed = _observed(GOLDEN["base"], {"L.state": "stale"})
    assert observed["fields"] == GOLDEN["pin"]["fields"]


@pytest.mark.parametrize(
    "unreadable",
    [
        {"T.no.such.field": "stale"},
        {"L.state": "available"},
        {"L.state": "old"},
        {"L.state": None},
    ],
)
def test_unreadable_refuses_a_field_or_status_it_does_not_know(unreadable):
    with pytest.raises(ValueError):
        rco.read_paths(MAPPING, GOLDEN["base"], unreadable=unreadable)
