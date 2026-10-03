"""The regime outlook verdict mapping is consistent, pinned and equal to its contract.

``config/regime_outlook_mapping_v1.json`` is an authored display-research
vocabulary (never tested against outcomes; no rank, gate or forecast). These
tests keep three promises about it:

* it obeys its own rules (``lint_mapping``), and each rule is shown to bite;
* its reading table is pinned by hash, so a silent edit cannot keep the name
  ``VERDICT_MAPPING_V1``;
* it says exactly what the contract's condition tables say.
"""

from __future__ import annotations

import copy
import hashlib
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from engine import rates_command_outlook as rco  # noqa: E402

CONTRACT = REPO / "research" / "macro_regime_intelligence" / "STATE_PATH_AND_SCIENCE_CONTRACT_2026-10-03.md"

# A change to fields, paths, families or retired ids is a new mapping version:
# add `regime_outlook_mapping_v2.json` beside this one, never re-pin this hash.
READING_TABLE_SHA256 = "5d9a168a09b32387eb0b5642ff4246a4a8c49b02a6c9cabd5dae99efae65c642"

PATH_IDS = (
    "orderly_disinflation",
    "growth_deterioration",
    "renewed_inflation_pressure",
    "long_end_premium_shock",
    "technical_pause",
    "continued_selective_concentration",
    "genuine_broadening",
    "internal_leadership_handoff",
    "deterioration_spreading_to_leaders",
)


@pytest.fixture()
def mapping() -> dict:
    return rco.load_mapping()


def _conditions(mapping: dict) -> list[dict]:
    return [c for p in mapping["paths"] for c in p["conditions"]]


def _row(mapping: dict, condition_id: str) -> dict:
    return next(c for c in _conditions(mapping) if c["condition_id"] == condition_id)


def _field(mapping: dict, field_id: str) -> dict:
    return next(f for f in mapping["fields"] if f["field_id"] == field_id)


# --------------------------------------------------------------------------
# identity and pin
# --------------------------------------------------------------------------


def test_mapping_names_its_version_tier_and_contract(mapping: dict) -> None:
    assert mapping["mapping_version"] == rco.MAPPING_VERSION == "VERDICT_MAPPING_V1"
    assert mapping["tier"] == "display_research"
    assert (REPO / mapping["contract"]) == CONTRACT
    assert CONTRACT.is_file()
    assert f"revision {mapping['contract_revision']}" in CONTRACT.read_text(encoding="utf-8")[:4000].lower()


def test_reading_table_hash_is_pinned(mapping: dict) -> None:
    assert rco.reading_table_sha256(mapping) == READING_TABLE_SHA256, (
        "the reading table changed: that is a new mapping version, not an edit to this one"
    )


def test_reading_table_hash_ignores_notes_but_not_tokens(mapping: dict) -> None:
    noted = copy.deepcopy(mapping)
    noted["note"] = "reworded"
    noted["evidence_only"][0]["note"] = "reworded"
    assert rco.reading_table_sha256(noted) == READING_TABLE_SHA256

    moved = copy.deepcopy(mapping)
    row = _row(moved, "OD-1")
    row["fits"], row["does_not_fit"] = row["does_not_fit"], row["fits"]
    assert rco.reading_table_sha256(moved) != READING_TABLE_SHA256


def test_file_hash_is_the_hash_of_the_bytes_on_disk() -> None:
    assert rco.mapping_sha256() == hashlib.sha256(rco.MAPPING_PATH.read_bytes()).hexdigest()


def test_load_refuses_a_file_naming_another_version(tmp_path: Path) -> None:
    other = tmp_path / "mapping.json"
    other.write_text('{"mapping_version": "VERDICT_MAPPING_V2"}', encoding="utf-8")
    with pytest.raises(ValueError, match="VERDICT_MAPPING_V2"):
        rco.load_mapping(other)


# --------------------------------------------------------------------------
# closed vocabularies and shape
# --------------------------------------------------------------------------


def test_paths_and_condition_counts_are_the_contract_s(mapping: dict) -> None:
    assert tuple(p["path_id"] for p in mapping["paths"]) == PATH_IDS
    conditions = _conditions(mapping)
    assert len(conditions) == 50
    assert sum(1 for c in conditions if c["field_id"] is not None) == 26
    assert len({c["condition_id"] for c in conditions}) == 50
    assert set(mapping["retired_condition_ids"]) == {"OD-6", "LP-3", "TP-2", "TP-3"}


def test_no_path_can_be_read_from_one_family_alone(mapping: dict) -> None:
    """Every path keeps at least one open row: none is fully decided by its read rows."""
    for path in mapping["paths"]:
        assert any(c["field_id"] is None for c in path["conditions"]), path["path_id"]


def test_mapping_lints_clean(mapping: dict) -> None:
    assert rco.lint_mapping(mapping) == []


# --------------------------------------------------------------------------
# each lint rule bites
# --------------------------------------------------------------------------


def _m_retired_id(m: dict) -> str:
    _row(m, "OD-1")["condition_id"] = "OD-6"
    return "OD-6: duplicate or retired id"


def _m_duplicate_id(m: dict) -> str:
    _row(m, "OD-2")["condition_id"] = "OD-1"
    return "OD-1: duplicate or retired id"


def _m_unknown_family(m: dict) -> str:
    _row(m, "OD-8")["evidence_family_id"] = "not_a_family"
    return "OD-8: family not in A.0"


def _m_family_differs_from_field(m: dict) -> str:
    _row(m, "OD-1")["evidence_family_id"] = "labour"
    return "OD-1: family differs from its field's"


def _m_no_rationale(m: dict) -> str:
    _row(m, "OD-1")["rationale"] = ""
    return "OD-1: no rationale"


def _m_middle_moved_into_a_side(m: dict) -> str:
    row = _row(m, "OD-1")
    row["fits"] = ["cooling", "steady"]
    row["not_discriminating"] = []
    return "OD-1: not_discriminating [] is not the field's middle ['steady']"


def _m_token_the_owner_never_publishes(m: dict) -> str:
    _row(m, "OD-1")["fits"] = ["falling"]
    return "OD-1: 'falling' not an owner token"


def _m_one_field_read_two_inconsistent_ways(m: dict) -> str:
    # RI-1 mirrors OD-1 today; make it disagree on what the not-fitting side is
    _row(m, "RI-1")["does_not_fit"] = ["steady"]
    return "RI-1: neither identical to nor a mirror of OD-1"


def _m_same_row_under_another_statement(m: dict) -> str:
    # SC-2 is the same row as OD-4; a different statement id would double-count it
    _row(m, "SC-2")["statement_id"] = "credit_calm"
    return "SC-2: statement_id identity disagrees with row identity vs OD-4"


def _m_mirror_under_the_same_statement(m: dict) -> str:
    _row(m, "RI-1")["statement_id"] = _row(m, "OD-1")["statement_id"]
    return "RI-1: statement_id identity disagrees with row identity vs OD-1"


def _m_open_row_authors_a_token(m: dict) -> str:
    _row(m, "OD-8")["fits"] = ["anything"]
    return "OD-8: open row authors a token or lacks a reason"


def _m_open_row_without_a_reason(m: dict) -> str:
    _row(m, "OD-8")["open_reason"] = None
    return "OD-8: open row authors a token or lacks a reason"


def _m_read_row_with_one_side_only(m: dict) -> str:
    _row(m, "TP-1")["does_not_fit"] = []
    return "TP-1: a read row needs both a fitting and a not-fitting side"


def _m_field_not_admitted(m: dict) -> str:
    _row(m, "OD-1")["field_id"] = "T.state.inflation.level"
    return "OD-1: field 'T.state.inflation.level' is not admitted"


def _m_verdict_class_outside_the_list(m: dict) -> str:
    _field(m, "T.state.inflation.direction")["verdict_class"] = "ranked"
    return "T.state.inflation.direction: verdict_class 'ranked' is not in the closed list"


def _m_clock_semantics_outside_the_list(m: dict) -> str:
    _field(m, "T.state.inflation.direction")["clock"]["semantics"] = "build_time"
    return "T.state.inflation.direction: clock semantics 'build_time' is not in the closed list"


def _m_reading_list_gains_a_word(m: dict) -> str:
    m["readings"] = [*m["readings"], "leaning"]
    return "readings differ from the closed list"


MUTANTS = (
    _m_retired_id,
    _m_duplicate_id,
    _m_unknown_family,
    _m_family_differs_from_field,
    _m_no_rationale,
    _m_middle_moved_into_a_side,
    _m_token_the_owner_never_publishes,
    _m_one_field_read_two_inconsistent_ways,
    _m_same_row_under_another_statement,
    _m_mirror_under_the_same_statement,
    _m_open_row_authors_a_token,
    _m_open_row_without_a_reason,
    _m_read_row_with_one_side_only,
    _m_field_not_admitted,
    _m_verdict_class_outside_the_list,
    _m_clock_semantics_outside_the_list,
    _m_reading_list_gains_a_word,
)


@pytest.mark.parametrize("mutate", MUTANTS, ids=lambda f: f.__name__[3:])
def test_lint_names_each_broken_rule(mapping: dict, mutate) -> None:
    broken = copy.deepcopy(mapping)
    expected = mutate(broken)
    errors = rco.lint_mapping(broken)
    assert any(error.startswith(expected) for error in errors), errors
    assert rco.lint_mapping(mapping) == [], "the mutation leaked into the loaded mapping"


# --------------------------------------------------------------------------
# the file says what the contract's tables say
# --------------------------------------------------------------------------

_PATH_HEADER = re.compile(r"^\*\*`([a-z_]+)`\*\*$")
_ROW = re.compile(r"^\| ([A-Z]{2}-\d+) \|")
_TICKED = re.compile(r"`([^`]+)`")


def _tokens(cell: str) -> list:
    """One fits / does_not_fit / not_discriminating cell of an A.4 table."""
    cell = cell.strip()
    if cell.startswith("—"):
        return []
    if cell.startswith("null"):
        return [None]
    ticked = _TICKED.findall(cell)
    if ticked:
        return ticked
    if cell in ("true", "false"):
        return [cell == "true"]
    number = cell.replace("−", "-")  # the contract writes a typographic minus
    if number.startswith("≤"):
        return [{"op": "le", "value": int(number[1:])}]
    if number.startswith("≥"):
        return [{"op": "ge", "value": int(number[1:])}]
    return [{"op": "eq", "value": int(number)}]


def _contract_tables() -> dict[str, list[dict]]:
    lines = CONTRACT.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("### A.4 "))
    end = next(i for i, line in enumerate(lines) if line.startswith("### A.5 "))
    tables: dict[str, list[dict]] = {}
    current = None
    for line in lines[start:end]:
        header = _PATH_HEADER.match(line.strip())
        if header:
            current = header.group(1)
            tables[current] = []
            continue
        if not _ROW.match(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        assert len(cells) == 8, line
        condition_id, statement, field, fits, does_not_fit, middle, family, _why = cells
        row = {
            "condition_id": condition_id,
            "statement_en": statement,
            "field_cell": field,
            "evidence_family_id": family.strip("`"),
        }
        if middle.startswith("`unknown`"):
            row.update(open_reason=_TICKED.findall(middle)[-1], fits=[], does_not_fit=[], not_discriminating=[])
            assert fits.startswith("—") and does_not_fit.startswith("—"), line
        else:
            row.update(
                open_reason=None,
                fits=_tokens(fits),
                does_not_fit=_tokens(does_not_fit),
                not_discriminating=_tokens(middle),
            )
        tables[current].append(row)
    return tables


def test_contract_tables_parse_to_nine_paths_and_fifty_rows() -> None:
    tables = _contract_tables()
    assert tuple(tables) == PATH_IDS
    assert sum(len(rows) for rows in tables.values()) == 50


def test_every_condition_equals_its_contract_row(mapping: dict) -> None:
    tables = _contract_tables()
    for path in mapping["paths"]:
        documented = tables[path["path_id"]]
        assert [c["condition_id"] for c in path["conditions"]] == [r["condition_id"] for r in documented]
        for condition, row in zip(path["conditions"], documented):
            where = condition["condition_id"]
            for key in ("statement_en", "evidence_family_id", "open_reason", "fits", "does_not_fit", "not_discriminating"):
                assert condition[key] == row[key], (where, key, condition[key], row[key])
            assert (condition["field_id"] is None) == (row["open_reason"] is not None), where


def test_every_read_row_points_at_the_field_the_contract_names(mapping: dict) -> None:
    """The contract abbreviates a path; its artifact letter and last segment must still match."""
    tables = _contract_tables()
    documented = {row["condition_id"]: row for rows in tables.values() for row in rows}
    for condition in _conditions(mapping):
        if condition["field_id"] is None:
            continue
        cell = documented[condition["condition_id"]]["field_cell"]
        field = _field(mapping, condition["field_id"])
        assert cell.split(" ", 1)[0] == field["artifact"], (condition["condition_id"], cell)
        last = field["path"][-1]
        assert isinstance(last, str)
        assert _TICKED.findall(cell)[0].split(".")[-1] == last, (condition["condition_id"], cell, field["path"])
