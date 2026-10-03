"""The regime outlook verdict mapping is consistent, pinned and equal to its contract.

``config/regime_outlook_mapping_v2.json`` is an authored display-research
vocabulary (never tested against outcomes; no rank, gate or forecast). These
tests keep three promises about it:

* it obeys its own rules (``lint_mapping``), and each rule is shown to bite;
* its reading table is pinned by hash, so a silent edit cannot keep the name
  ``VERDICT_MAPPING_V2``;
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

# A change to artifacts, fields, paths, families or retired ids is a new
# mapping version: add `regime_outlook_mapping_v2.json` beside this one,
# never re-pin this hash.
READING_TABLE_SHA256 = "588f55df2e48edb3cc1c22459c51d218d039f311fe3e6ddea424d1687887181e"

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
    assert mapping["mapping_version"] == rco.MAPPING_VERSION == "VERDICT_MAPPING_V2"
    assert mapping["tier"] == "display_research"
    assert (REPO / mapping["contract"]) == CONTRACT
    assert CONTRACT.is_file()
    assert f"revision {mapping['contract_revision']}" in CONTRACT.read_text(encoding="utf-8")[:4000].lower()


def test_reading_table_hash_is_pinned(mapping: dict) -> None:
    assert rco.reading_table_sha256(mapping) == READING_TABLE_SHA256, (
        "the reading table changed: that is a new mapping version, not an edit to this one"
    )


def test_reading_table_hash_covers_the_artifact_list(mapping: dict) -> None:
    """Changing which artifact letter a field reads also changes the pin."""
    moved = copy.deepcopy(mapping)
    base = rco.reading_table_sha256(mapping)
    moved["artifacts"]["T"] = "data/treasury/curve_observation.json"
    assert rco.reading_table_sha256(moved) != base


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
    other.write_text('{"mapping_version": "VERDICT_MAPPING_V1"}', encoding="utf-8")
    with pytest.raises(ValueError, match="VERDICT_MAPPING_V1"):
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
    # LH-1 mirrors DS-1 on L.state today; move BROKEN onto LH-1's fits so the
    # two rows are no longer the same row nor its mirror, without adding a
    # token that would put L1 first. The error names DS-1 because it sits
    # later in file order than LH-1.
    _row(m, "LH-1")["fits"] = ["INTACT", "BROKEN"]
    _row(m, "LH-1")["does_not_fit"] = ["CRACKING"]
    return "DS-1: neither identical to nor a mirror of LH-1"


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


def _m_token_in_two_columns(m: dict) -> str:
    # L1 — duplicate a 'fits' token into 'does_not_fit' of the same row
    row = _row(m, "OD-1")
    copied = row["fits"][0]
    row["does_not_fit"] = [copied, *row["does_not_fit"]]
    return f"OD-1: token {copied!r} is in two columns"


def _m_owner_token_in_no_column(m: dict) -> str:
    # L2 — drop a side token from a row's column so an owner token is in no
    # column. Use TP-1 which is the only row on the 10y turn_watch field, so
    # the identical-or-mirror rule cannot fire first.
    row = _row(m, "TP-1")
    dropped = "extreme_high_watch"
    row["does_not_fit"] = [t for t in row["does_not_fit"] if t != dropped]
    return f"TP-1: owner token {dropped!r} is in no column"


def _m_statement_id_shared_across_fields(m: dict) -> str:
    # L3-i across fields — give a later read row the statement_id of an
    # earlier read row on a different field. TP-1 sits later in file order
    # than OD-1, so TP-1 is the later row and OD-1 the earlier.
    earlier = _row(m, "OD-1")  # field T.state.inflation.direction
    later = _row(m, "TP-1")  # field T.yield_momentum.series.10y.turn_watch
    later["statement_id"] = earlier["statement_id"]
    return (
        f"{later['condition_id']}: statement_id identity disagrees with row identity "
        f"vs {earlier['condition_id']}"
    )


def _m_open_statement_id_reused_by_a_read_row(m: dict) -> str:
    # L3-ii — give a read row the statement_id of an open row. The error
    # names the open row whose statement_id was reused.
    open_row = _row(m, "OD-8")
    read_row = _row(m, "TP-1")
    read_row["statement_id"] = open_row["statement_id"]
    return f"{open_row['condition_id']}: statement_id of an open row is reused"


def _m_numeric_row_malformed(m: dict) -> str:
    # L4 malformed — change RI-6's `op` to an unsupported token
    row = _row(m, "RI-6")
    row["does_not_fit"][0]["op"] = "lt"
    return "RI-6: numeric row has a malformed entry"


def _m_numeric_row_does_not_partition(m: dict) -> str:
    # L4 partition — RI-6's `ge 1` -> `ge 2` so 1 is no longer covered by an eq
    row = _row(m, "RI-6")
    row["does_not_fit"][0]["value"] = 2
    return "RI-6: numeric row does not partition the integers"


def _m_two_rows_read_a_turn_watch(m: dict) -> str:
    # L5 — add a second read row for the 10y turn_watch field. Deep-copy TP-1
    # and append a fresh condition_id to a different path than technical_pause
    field_id = "T.yield_momentum.series.10y.turn_watch"
    source = _row(m, "TP-1")
    new_condition = copy.deepcopy(source)
    new_condition["condition_id"] = "LP-8"
    new_condition["statement_id"] = "long_end_turn_also_forming"
    # append to long_end_premium_shock path
    for path in m["paths"]:
        if path["path_id"] == "long_end_premium_shock":
            path["conditions"].append(new_condition)
            break
    return f"{field_id}: more than one row reads a turn watch"


def _m_guard_kind_outside_list(m: dict) -> str:
    # L6 kind — T.state.inflation.direction's guard kind is not in the closed list
    field_id = "T.state.inflation.direction"
    _field(m, field_id)["guard"]["kind"] = "always_admit"
    return f"{field_id}: guard kind 'always_admit' is not in the closed list"


def _m_guard_default_token_not_owner(m: dict) -> str:
    # L6 default token — T.state.inflation.direction's default_token is not
    # one of its owner tokens
    field_id = "T.state.inflation.direction"
    _field(m, field_id)["guard"]["default_token"] = "falling"
    return f"{field_id}: guard default token is not an owner token"


def _m_guard_missing_token_not_owner(m: dict) -> str:
    # L6 missing token — R.liquidity_quality.label's missing_token is not
    # one of its owner tokens
    field_id = "R.liquidity_quality.label"
    _field(m, field_id)["guard"]["missing_token"] = "tight"
    return f"{field_id}: guard missing token is not an owner token"


def _m_rationale_is_whitespace(m: dict) -> str:
    # L7 — whitespace-only rationale
    _row(m, "OD-1")["rationale"] = "   \t  "
    return "OD-1: no rationale"


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
    _m_token_in_two_columns,
    _m_owner_token_in_no_column,
    _m_statement_id_shared_across_fields,
    _m_open_statement_id_reused_by_a_read_row,
    _m_numeric_row_malformed,
    _m_numeric_row_does_not_partition,
    _m_two_rows_read_a_turn_watch,
    _m_guard_kind_outside_list,
    _m_guard_default_token_not_owner,
    _m_guard_missing_token_not_owner,
    _m_rationale_is_whitespace,
)


@pytest.mark.parametrize("mutate", MUTANTS, ids=lambda f: f.__name__[3:])
def test_lint_names_each_broken_rule(mapping: dict, mutate) -> None:
    broken = copy.deepcopy(mapping)
    expected = mutate(broken)
    errors = rco.lint_mapping(broken)
    assert any(error.startswith(expected) for error in errors), errors
    assert rco.lint_mapping(mapping) == [], "the mutation leaked into the loaded mapping"


# --------------------------------------------------------------------------
# round-3 repair tests (R1–R5)
# --------------------------------------------------------------------------


def _m_ds3_statement_id_mismatch(m: dict) -> None:
    # R1 — DS-3 (financial_conditions_tight) shares its (field_id, row_key)
    # with GD-4 (also financial_conditions_tight) but the prior implementation
    # only compared DS-3 to the first read row on its field, never to GD-4.
    _row(m, "DS-3")["statement_id"] = "zzz"


def test_l3_catches_same_row_under_a_different_statement_id(mapping: dict) -> None:
    """R1(a) — two read rows that are the same row must share a statement_id."""
    broken = copy.deepcopy(mapping)
    _m_ds3_statement_id_mismatch(broken)
    errors = rco.lint_mapping(broken)
    assert any(
        error.startswith("DS-3: statement_id identity disagrees")
        for error in errors
    ), errors


def _retarget_breakeven_trend_row(m: dict, source_id: str) -> dict:
    """Return a deep-copy of an existing categorical row, retargeted to
    ``T.breakeven_decomp.trend``. Per the R2 fallback the rule allows, we
    retarget by carrying the source's family, statement_id, and a row_key
    built from the target field's three non-missing tokens so the row is
    legal end-to-end: family matches, statement_id is unique on the new
    field, the new field's row_key is unique, and the three non-missing
    tokens cover the field except for the owner's missing token ('n/a')."""
    src = _row(m, source_id)
    new = copy.deepcopy(src)
    new["field_id"] = "T.breakeven_decomp.trend"
    new["evidence_family_id"] = "treasury_curve"
    new["statement_id"] = "breakeven_trend_test_only"
    new["fits"] = ["uptrend"]
    new["does_not_fit"] = ["downtrend"]
    new["not_discriminating"] = ["choppy"]
    new["open_reason"] = None
    return new


def test_l2_does_not_demand_owners_missing_token(mapping: dict) -> None:
    """R2(a) — L2 does not demand the owner's missing token in a column.

    The R2 fallback is taken: rather than author a brand-new legal row from
    scratch, an existing categorical row is retargeted to
    ``T.breakeven_decomp.trend`` with the three non-missing tokens covered
    and 'n/a' deliberately omitted. Lint must not report 'n/a' or
    "is in no column" for this row.
    """
    broken = copy.deepcopy(mapping)
    for path in broken["paths"]:
        for idx, condition in enumerate(path["conditions"]):
            if condition["condition_id"] == "SC-3":
                path["conditions"][idx] = _retarget_breakeven_trend_row(broken, "SC-3")
                break
    errors = rco.lint_mapping(broken)
    sc3_errors = [e for e in errors if e.startswith("SC-3:")]
    assert not any("'n/a'" in e for e in sc3_errors), sc3_errors
    assert not any("is in no column" in e for e in sc3_errors), sc3_errors


def test_l2_rejects_owners_missing_token_in_a_column(mapping: dict) -> None:
    """R2(b) — if the owner's missing token appears in any column, lint fires."""
    broken = copy.deepcopy(mapping)
    for path in broken["paths"]:
        for idx, condition in enumerate(path["conditions"]):
            if condition["condition_id"] == "SC-3":
                path["conditions"][idx] = _retarget_breakeven_trend_row(broken, "SC-3")
                path["conditions"][idx]["fits"] = ["uptrend", "n/a"]
                break
    errors = rco.lint_mapping(broken)
    assert any(
        "is the owner's missing token and is in a column" in e
        and e.startswith("SC-3:")
        for e in errors
    ), errors


def _m_no_guard(m: dict) -> None:
    _field(m, "T.state.rates.direction").pop("guard", None)


def _m_turn_watch_status_required_stale(m: dict) -> None:
    _field(m, "T.yield_momentum.series.10y.turn_watch")["guard"]["status_required"] = "stale"


def _m_credit_stress_admit_true_when_tweaked(m: dict) -> None:
    _field(m, "R.liquidity_quality.stress_overlay.confirming_stress")["guard"]["admit_true_when"] = (
        "hy_oas_z >= 1.00 or nfci > 0"
    )


def _m_turn_watch_status_path_on_another_series(m: dict) -> None:
    # 2y field — status_path pointed at the 2y series, which is the same
    # series as the field itself. R3 says: status_path must start with
    # field["path"][:-1], so the 2y → 2y path is fine; redirect to 5y.
    _field(m, "T.yield_momentum.series.10y.turn_watch")["guard"]["status_path"] = [
        "yield_momentum", "series", "5y", "status",
    ]


def _m_default_token_deleted(m: dict) -> None:
    _field(m, "T.state.rates.direction")["guard"].pop("default_token")


_L6_MUTANTS = (
    (_m_no_guard, "T.state.rates.direction: no guard"),
    (
        _m_turn_watch_status_required_stale,
        "T.yield_momentum.series.10y.turn_watch: guard status_required is not the frozen value",
    ),
    (
        _m_credit_stress_admit_true_when_tweaked,
        "R.liquidity_quality.stress_overlay.confirming_stress: guard admit_true_when is not the frozen value",
    ),
    (
        _m_turn_watch_status_path_on_another_series,
        "T.yield_momentum.series.10y.turn_watch: guard names another series",
    ),
)


@pytest.mark.parametrize("mutate, expected", _L6_MUTANTS, ids=lambda v: v.__name__[3:] if callable(v) else v)
def test_l6_names_each_frozen_violation(mapping: dict, mutate, expected) -> None:
    """R3 — every guard mutates to a single named error."""
    broken = copy.deepcopy(mapping)
    mutate(broken)
    errors = rco.lint_mapping(broken)
    assert any(e == expected or e.startswith(expected) for e in errors), errors
    assert rco.lint_mapping(mapping) == [], "the mutation leaked into the loaded mapping"


def test_l6_missing_default_token_is_a_keyset_failure(mapping: dict) -> None:
    """R3 — a guard missing ``default_token`` is a keyset failure, not a KeyError."""
    broken = copy.deepcopy(mapping)
    _m_default_token_deleted(broken)
    try:
        errors = rco.lint_mapping(broken)
    except KeyError as exc:
        pytest.fail(f"lint_mapping raised KeyError instead of reporting: {exc}")
    assert any(
        e == "T.state.rates.direction: guard keys do not match its kind" for e in errors
    ), errors


def _m_l1_repeated_in_a_column(m: dict) -> None:
    # OD-1's fits = ['cooling']. Put 'cooling' twice in the same column.
    _row(m, "OD-1")["fits"] = ["cooling", "cooling"]


def _m_l4_le_and_ge_in_same_column(m: dict) -> None:
    # RI-6 reads B.fed_path.implied_cuts_12m: le in does_not_fit (-1) and
    # ge in fits (1). Move ge to does_not_fit so le and ge share a column.
    _row(m, "RI-6")["fits"] = [{"op": "ge", "value": 1}, {"op": "eq", "value": 0}]
    _row(m, "RI-6")["does_not_fit"] = [{"op": "le", "value": -1}]


@pytest.mark.parametrize(
    "mutate, expected",
    (
        (
            _m_l1_repeated_in_a_column,
            "OD-1: token 'cooling' is repeated in a column",
        ),
        (
            _m_l4_le_and_ge_in_same_column,
            "RI-6: numeric row does not partition the integers",
        ),
    ),
    ids=lambda v: v.__name__[3:] if callable(v) else v,
)
def test_r5_nits_each_fire(mapping: dict, mutate, expected) -> None:
    """R5 — three small lint sharpenings."""
    broken = copy.deepcopy(mapping)
    mutate(broken)
    errors = rco.lint_mapping(broken)
    assert any(e.startswith(expected) for e in errors), errors
    assert rco.lint_mapping(mapping) == [], "the mutation leaked into the loaded mapping"


def test_l2_not_discriminating_is_order_insensitive(mapping: dict) -> None:
    """R5(c) — ``not_discriminating`` and the field's middle tokens compare
    by their sorted json.dumps texts, so a row that reorders the middle
    tokens stays clean.

    Deviation: the spec named ``T.state.inflation.direction`` (read by OD-1
    and RI-1) but every row on that field has exactly one fit and one
    does-not-fit token, so moving either side token to middle empties one
    column and trips L1's "a read row needs both a fitting and a not-fitting
    side" check. ``L.state`` (read by LH-1 and DS-1) has each row with two
    tokens on one side (LH-1's does_not_fit=['CRACKING','BROKEN']; DS-1's
    fits=['CRACKING','BROKEN']), so moving ``CRACKING`` to middle leaves
    the other side non-empty on both rows. The test exercises one moved
    token giving a one-token middle; reverse-of-one is itself, so (i)
    passes by symmetry. Constructing a two-token middle on any field
    without L1 firing is impossible in this mapping.
    """
    broken = copy.deepcopy(mapping)

    # (i) move ``CRACKING`` from each row's multi-token side to middle.
    # The field gains it; LH-1's does_not_fit and DS-1's fits keep the
    # other token, so both rows stay non-empty on both sides.
    l_state = _field(broken, "L.state")
    l_state["middle_tokens"] = ["CRACKING"]
    for path in broken["paths"]:
        for condition in path["conditions"]:
            if condition["field_id"] != "L.state":
                continue
            if "CRACKING" in condition["does_not_fit"]:
                condition["does_not_fit"] = [
                    t for t in condition["does_not_fit"] if t != "CRACKING"
                ]
            if "CRACKING" in condition["fits"]:
                condition["fits"] = [t for t in condition["fits"] if t != "CRACKING"]
            # the field's middle has one element; reverse-of-one is itself,
            # so the order-insensitive comparison stays clean.
            condition["not_discriminating"] = list(reversed(l_state["middle_tokens"]))

    # Mirror invariant: LH-1 and DS-1 must still swap sides with the same
    # middle; otherwise the per-field pairwise check would fire and
    # mask the order test. Confirm both rows still author the moved token
    # in the same middle column.
    lh1 = _row(broken, "LH-1")
    ds1 = _row(broken, "DS-1")
    assert lh1["not_discriminating"] == ["CRACKING"], lh1
    assert ds1["not_discriminating"] == ["CRACKING"], ds1

    errors_clean = rco.lint_mapping(broken)
    assert all(
        not e.startswith("LH-1:") and not e.startswith("DS-1:") for e in errors_clean
    ), errors_clean

    # (ii) drop ``CRACKING`` from DS-1's middle. The field's middle still
    # has it, so the L1 order-insensitive comparison fires for DS-1.
    broken2 = copy.deepcopy(broken)
    _row(broken2, "DS-1")["not_discriminating"] = []
    errors = rco.lint_mapping(broken2)
    assert any(
        e.startswith("DS-1:") and "is not the field's middle" in e for e in errors
    ), errors


# --------------------------------------------------------------------------
# round-4 lint sharpenings (R1–R3)
# --------------------------------------------------------------------------


def _t1_guard_as_str(m: dict) -> None:
    _field(m, "T.state.rates.direction")["guard"] = "x"


def _t1_guard_as_none(m: dict) -> None:
    _field(m, "T.state.rates.direction")["guard"] = None


def _t1_guard_as_list(m: dict) -> None:
    _field(m, "T.state.rates.direction")["guard"] = []


def _t1_missing_token_deleted(m: dict) -> None:
    _field(m, "T.breakeven_decomp.trend")["guard"].pop("missing_token")


_T1_CASES = (
    (_t1_guard_as_str, "T.state.rates.direction: no guard"),
    (_t1_guard_as_none, "T.state.rates.direction: no guard"),
    (_t1_guard_as_list, "T.state.rates.direction: no guard"),
    (
        _t1_missing_token_deleted,
        "T.breakeven_decomp.trend: guard keys do not match its kind",
    ),
)


@pytest.mark.parametrize(
    "mutate, expected",
    _T1_CASES,
    ids=lambda v: v.__name__[3:] if callable(v) else v,
)
def test_l1_lint_survives_a_malformed_guard(mapping: dict, mutate, expected) -> None:
    """R1 — lint never raises on a malformed guard, and a missing
    ``missing_token`` key is reported as a keyset failure, not a KeyError."""
    broken = copy.deepcopy(mapping)
    mutate(broken)
    try:
        errors = rco.lint_mapping(broken)
    except (AttributeError, KeyError, TypeError) as exc:
        pytest.fail(f"lint_mapping raised {type(exc).__name__} instead of reporting: {exc}")
    assert isinstance(errors, list)
    assert expected in errors, errors
    assert rco.lint_mapping(mapping) == [], "the mutation leaked into the loaded mapping"


def _m_r2_hy_oas_z_path_outside_block(m: dict) -> None:
    _field(
        m, "R.liquidity_quality.stress_overlay.confirming_stress"
    )["guard"]["hy_oas_z_path"] = ["conditions", "x"]


def _m_r2_degraded_path_other_component(m: dict) -> None:
    _field(m, "M.components.breadth.tone")["guard"]["degraded_path"] = [
        "components", {"key": "leadership"}, "degraded",
    ]


def _m_r2_needs_outside_block(m: dict) -> None:
    _field(m, "R.conditions.labor_nowcast.read")["guard"]["needs"][0] = [
        "state", "rates", "real_10y_chg_63d_bp",
    ]


def _m_r2_copy_artifact_same_as_field(m: dict) -> None:
    _field(m, "L.state")["guard"]["copy_artifact"] = "L"


def _m_r2_copy_artifact_not_in_artifacts(m: dict) -> None:
    _field(m, "L.state")["guard"]["copy_artifact"] = "Z"


_R2_CASES = (
    (
        _m_r2_hy_oas_z_path_outside_block,
        "R.liquidity_quality.stress_overlay.confirming_stress: guard "
        "hy_oas_z_path leaves the field's own block",
    ),
    (
        _m_r2_degraded_path_other_component,
        "M.components.breadth.tone: guard degraded_path leaves the field's own block",
    ),
    (
        _m_r2_needs_outside_block,
        "R.conditions.labor_nowcast.read: guard needs leaves the field's own block",
    ),
    (
        _m_r2_copy_artifact_same_as_field,
        "L.state: guard copy_artifact is not another listed artifact",
    ),
    (
        _m_r2_copy_artifact_not_in_artifacts,
        "L.state: guard copy_artifact is not another listed artifact",
    ),
)


@pytest.mark.parametrize(
    "mutate, expected",
    _R2_CASES,
    ids=lambda v: v.__name__[3:] if callable(v) else v,
)
def test_l6_guard_paths_stay_inside_the_fields_owner_block(
    mapping: dict, mutate, expected
) -> None:
    """R2 — every guard path stays inside the field's own owner block, and
    a same-run-owner-copy guard names another listed artifact."""
    broken = copy.deepcopy(mapping)
    mutate(broken)
    errors = rco.lint_mapping(broken)
    assert expected in errors, errors
    assert rco.lint_mapping(mapping) == [], "the mutation leaked into the loaded mapping"


def _m_r3_le_in_middle(m: dict) -> None:
    """RI-6 reads B.fed_path.implied_cuts_12m: le in fits (-1), ge in
    does_not_fit (1), eq in not_discriminating (0). Move ``le`` into
    ``not_discriminating`` and ``eq`` into ``fits`` so the single ``le``
    ends up on the middle column. The existing message must fire."""
    row = _row(m, "RI-6")
    row["fits"] = [{"op": "eq", "value": 0}]
    row["does_not_fit"] = [{"op": "ge", "value": 1}]
    row["not_discriminating"] = [{"op": "le", "value": -1}]


def test_l4_extremes_stay_in_the_sides(mapping: dict) -> None:
    """R3 — the single ``le`` and the single ``ge`` of a numeric row must
    each sit in ``fits`` or ``does_not_fit``; the middle column may only
    carry ``eq`` values."""
    broken = copy.deepcopy(mapping)
    _m_r3_le_in_middle(broken)
    errors = rco.lint_mapping(broken)
    assert "RI-6: numeric row does not partition the integers" in errors, errors
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
    """The contract abbreviates a path; its artifact letter and the path it writes must be the end of the mapping field's path."""
    tables = _contract_tables()
    documented = {row["condition_id"]: row for rows in tables.values() for row in rows}
    for condition in _conditions(mapping):
        if condition["field_id"] is None:
            continue
        cell = documented[condition["condition_id"]]["field_cell"]
        field = _field(mapping, condition["field_id"])
        artifact, candidates = _parse_field_cell(cell)
        assert artifact == field["artifact"], (condition["condition_id"], cell)
        field_path = field["path"]
        assert any(candidate == field_path[-len(candidate):] for candidate in candidates), (
            condition["condition_id"],
            cell,
            field_path,
            candidates,
        )


# --------------------------------------------------------------------------
# parity tests against the contract's A.0 and A.1 tables (R3(d))
# --------------------------------------------------------------------------


def _split_a1_section() -> tuple[int, int]:
    lines = CONTRACT.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("### A.1 "))
    end = next(i for i, line in enumerate(lines) if line.startswith("### A.2 "))
    return start, end


def _contract_a0_families() -> list[tuple[str, str]]:
    """Return [(family_id, coverage), ...] in document order from A.0."""
    lines = CONTRACT.read_text(encoding="utf-8").splitlines()
    a0_start = next(i for i, line in enumerate(lines) if line.startswith("### A.0 "))
    a1_start = next(i for i, line in enumerate(lines) if line.startswith("### A.1 "))
    body = " ".join(lines[a0_start + 1:a1_start])
    sections = []
    for label, coverage in (
        ("With at least one admitted field:", "admitted"),
        ("With evidence but no admitted reading:", "evidence_only"),
        ("With no audited owner field:", "no_owner"),
    ):
        idx = body.find(label)
        assert idx != -1, label
        after = body[idx + len(label):]
        # take text up to the next full stop
        stop = after.find(".")
        text = after if stop == -1 else after[:stop]
        sections.append((text, coverage))
    families: list[tuple[str, str]] = []
    for text, coverage in sections:
        for fid in _TICKED.findall(text):
            families.append((fid, coverage))
    return families


def test_contract_family_list_equals_the_mapping(mapping: dict) -> None:
    families = _contract_a0_families()
    assert len(families) == 22
    expected = [(f["evidence_family_id"], f["coverage"]) for f in mapping["families"]]
    assert families == expected


def _parse_field_cell(cell: str) -> tuple[str, list]:
    """Parse the Field cell of an A.1 row into (artifact, path)."""
    artifact = cell.split(" ", 1)[0]
    backticked = _TICKED.findall(cell)
    assert backticked, cell
    path_text = backticked[0]

    # If <tenor> appears, expand once per tenor in the parenthesised list
    # that follows the backticked item.
    if "<tenor>" in path_text:
        # find "(...)" following the closing backtick
        after_tick = cell.split("`", 2)[2]
        tenors_match = re.search(r"\(([^)]+)\)", after_tick)
        assert tenors_match, cell
        tenors = [t.strip() for t in tenors_match.group(1).split(",")]
        paths = []
        for tenor in tenors:
            expanded = path_text.replace("<tenor>", tenor)
            paths.append(_split_path(expanded))
        return artifact, paths

    return artifact, [_split_path(path_text)]


def _split_path(text: str) -> list:
    """Split a dotted path, expanding ``name[key=value]`` and ``name[value]`` segments.

    A ``[value]`` shorthand is treated as ``[key=value]`` with the literal key
    name ``"key"``; the A.4 tables drop the ``key=`` part of the bracket
    notation that the A.1 tables spell out, and both must parse to the same
    dict-segment list.
    """
    parts: list = []
    for segment in text.split("."):
        kv = re.match(
            r"^([A-Za-z_][A-Za-z0-9_]*)\[([A-Za-z_][A-Za-z0-9_]*)=([A-Za-z_][A-Za-z0-9_]*)\]$",
            segment,
        )
        if kv:
            parts.append(kv.group(1))
            parts.append({kv.group(2): kv.group(3)})
            continue
        bare = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\[([A-Za-z_][A-Za-z0-9_]*)\]$", segment)
        if bare:
            parts.append(bare.group(1))
            parts.append({"key": bare.group(2)})
            continue
        parts.append(segment)
    return parts


def _parse_tokens_cell(cell: str):
    """Parse the Tokens cell of an A.1 row.

    Returns a dict for the integer contract token (``{"type": "integer"}``)
    and a list otherwise.
    """
    if re.search(r"\binteger\b", cell):
        return {"type": "integer"}
    out: list = []
    for match in re.finditer(r"`([^`]+)`|\b(true|false|null)\b", cell):
        if match.group(1) is not None:
            out.append(match.group(1))
        else:
            word = match.group(2)
            if word == "null":
                out.append(None)
            else:
                out.append(word == "true")
    return out


def _parse_middle_cell(cell: str) -> list:
    """Parse the Middle cell of an A.1 row."""
    cell = cell.strip()
    if cell.startswith("none"):
        return []
    ticked = _TICKED.findall(cell)
    if ticked:
        token = ticked[0]
        if token == "null":
            return [None]
        try:
            return [{"op": "eq", "value": int(token)}]
        except ValueError:
            return [token]
    # no backticked token
    return []


def _parse_class_cell(cell: str) -> str:
    """Parse the Class cell of an A.1 row: first word without a trailing comma."""
    first = cell.split()[0]
    return first.rstrip(",")


def _parse_family_cell(cell: str) -> str:
    """Parse the Family cell of an A.1 row: the backticked id."""
    ticked = _TICKED.findall(cell)
    assert ticked, cell
    return ticked[0]


_A1_ROW = re.compile(r"^\| [A-Z] ")


def _contract_a1_fields() -> list[dict]:
    """Parse every A.1 row into a flat list of dicts (one per tenor expansion)."""
    lines = CONTRACT.read_text(encoding="utf-8").splitlines()
    start, end = _split_a1_section()
    rows: list[dict] = []
    for line in lines[start + 1:end]:
        if not _A1_ROW.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        assert len(cells) == 8, line
        _field_cell, _tokens_cell, middle_cell, *_, family_cell = (cells[0], cells[1], cells[2], cells[3], cells[4], cells[5], cells[6], cells[7])
        # re-parse in canonical order
        field_cell = cells[0]
        tokens_cell = cells[1]
        middle_cell = cells[2]
        class_cell = cells[3]
        family_cell = cells[7]

        artifact, paths = _parse_field_cell(field_cell)
        tokens = _parse_tokens_cell(tokens_cell)
        middle = _parse_middle_cell(middle_cell)
        verdict_class = _parse_class_cell(class_cell)
        family_id = _parse_family_cell(family_cell)

        if len(paths) > 1:
            # tenor expansion — one entry per tenor, all sharing the other cells
            for path in paths:
                rows.append(
                    {
                        "artifact": artifact,
                        "path": path,
                        "tokens": tokens,
                        "middle_tokens": middle,
                        "verdict_class": verdict_class,
                        "evidence_family_id": family_id,
                    }
                )
        else:
            rows.append(
                {
                    "artifact": artifact,
                    "path": paths[0],
                    "tokens": tokens,
                    "middle_tokens": middle,
                    "verdict_class": verdict_class,
                    "evidence_family_id": family_id,
                }
            )
    return rows


def test_contract_field_table_equals_the_mapping(mapping: dict) -> None:
    rows = _contract_a1_fields()
    assert len(rows) == 21
    expected = [{k: f[k] for k in ("artifact", "path", "tokens", "middle_tokens", "verdict_class", "evidence_family_id")} for f in mapping["fields"]]
    assert rows == expected