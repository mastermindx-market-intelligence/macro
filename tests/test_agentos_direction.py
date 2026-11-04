"""Focused pytest suite for the agentos_direction owner content contract."""

from __future__ import annotations

import copy
import datetime
import json

import pytest

from scripts.agentos_direction import (
    DEC_PATH_TEMPLATE,
    OUTPUT_BUDGET_BYTES,
    SCHEMA,
    VALID_CODES,
    WS_PATH_TEMPLATE,
    DirectionError,
    project_direction,
    validate_declaration,
)

REPOSITORY = "mastermindx-market-intelligence/macro"
COMMIT = "a1b2c3d4" * 5  # 40 lowercase hex
DIGEST = "0f1e2d3c4b5a69788796a5b4c3d2e1f0" * 2  # 64 lowercase hex
WS = "WS:MARKET-INTEL-REFIT"
WS_KEY = WS[3:]


def refs(count):
    return ["DEC:DIR-%04d" % i for i in range(1, count + 1)]


def ws_source(**over):
    source = {
        "repository": REPOSITORY,
        "commit": COMMIT,
        "path": WS_PATH_TEMPLATE.format(key=WS_KEY),
        "content_sha256": DIGEST,
    }
    source.update(over)
    return source


def dec_source(ref, **over):
    source = {
        "repository": REPOSITORY,
        "commit": COMMIT,
        "path": DEC_PATH_TEMPLATE.format(key=ref[4:]),
        "content_sha256": DIGEST,
    }
    source.update(over)
    return source


def declaration(predecessor=None, work_ref=WS, schema=SCHEMA, state="ACCEPTED"):
    return {
        "schema": schema,
        "state": state,
        "work_ref": work_ref,
        "predecessor": predecessor,
    }


def dec_record(
    ref,
    predecessor=None,
    decided_at="2026-01-05",
    superseded_by=None,
    supersedes=True,
    work_ref=WS,
    extra=None,
):
    record = {
        "key": ref[4:],
        "answer": "Answer for " + ref,
        "rationale": "Rationale for " + ref,
        "decided_by": "Macro Owner Group",
        "decided_at": decided_at,
        "direction": declaration(predecessor, work_ref=work_ref),
        "affects": [WS],
    }
    if supersedes and predecessor is not None:
        record["supersedes"] = [predecessor]
    if superseded_by is not None:
        record["superseded_by"] = superseded_by
    if extra:
        record.update(extra)
    return record


def entry(ref, source_override=None, **kwargs):
    record = dec_record(ref, **kwargs)
    source = source_override or dec_source(ref)
    return {"record": record, "source": source}


def build_chain(count, dates=None):
    chain_refs = refs(count)
    decisions = {}
    for index, ref in enumerate(chain_refs):
        predecessor = chain_refs[index + 1] if index + 1 < count else None
        superseded_by = chain_refs[index - 1] if index > 0 else None
        decided_at = dates[index] if dates else "2026-01-%02d" % (10 - index)
        decisions[ref] = entry(
            ref,
            predecessor=predecessor,
            superseded_by=superseded_by,
            decided_at=decided_at,
        )
    return decisions, chain_refs


def workstream(accepted=None, key=WS_KEY, extra=None):
    record = {
        "key": key,
        "objective": "Ship the market intelligence refit",
        "status": "OPEN",
        "decisions": ["DEC:SOMETHING-ELSE", *([accepted] if accepted is not None else [])],
    }
    if accepted is not None:
        record["accepted_direction"] = accepted
    if extra:
        record.update(extra)
    return record


def project(decisions, accepted, *, ws=None, source=None, max_revisions=8, work_ref=WS):
    return project_direction(
        work_ref=work_ref,
        workstream=ws if ws is not None else workstream(accepted),
        workstream_source=source if source is not None else ws_source(),
        decisions=decisions,
        max_revisions=max_revisions,
    )


def expect_code(action, code):
    with pytest.raises(DirectionError) as excinfo:
        action()
    assert excinfo.value.code == code
    assert str(excinfo.value) == code
    assert excinfo.value.code in VALID_CODES
    return excinfo.value


# ---------------------------------------------------------------- declarations


def test_validate_declaration_returns_detached_mapping():
    value = declaration("DEC:PRED-ONE")
    result = validate_declaration(value, work_ref=WS, decision_ref="DEC:CURR-ONE")
    assert result == value
    result["predecessor"] = "DEC:MUTATED"
    result["schema"] = "mutated"
    assert value["predecessor"] == "DEC:PRED-ONE"
    assert value["schema"] == SCHEMA


def test_validate_declaration_null_predecessor_ok():
    result = validate_declaration(declaration(None), work_ref=WS, decision_ref="DEC:FIRST-ONE")
    assert result["predecessor"] is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update({"surplus": True}),
        lambda d: d.pop("state"),
        lambda d: d.update({"state": False}),
        lambda d: d.update({"predecessor": False}),
        lambda d: d.update({"state": "REJECTED"}),
        lambda d: d.update({"schema": "project_plan_adoption.v1"}),
        lambda d: d.update({"work_ref": "WS:OTHER-REFIT"}),
        lambda d: d.update({"predecessor": "DEC:CURR-ONE"}),
        lambda d: d.update({"predecessor": "DIR-0001"}),
        lambda d: d.update({"predecessor": "dec:pred-one"}),
    ],
)
def test_validate_declaration_invalid_raises_closed_code(mutate):
    value = declaration("DEC:PRED-ONE")
    mutate(value)
    expect_code(
        lambda: validate_declaration(value, work_ref=WS, decision_ref="DEC:CURR-ONE"),
        "INVALID_DIRECTION",
    )


def test_validate_declaration_generic_adoption_not_accepted():
    value = declaration(None, schema="project_plan_adoption.v1")
    expect_code(
        lambda: validate_declaration(value, work_ref=WS, decision_ref="DEC:FIRST-ONE"),
        "INVALID_DIRECTION",
    )


def test_validate_declaration_rejects_subclass_and_non_dict():
    class ShadowDict(dict):
        pass

    expect_code(
        lambda: validate_declaration(
            ShadowDict(declaration(None)), work_ref=WS, decision_ref="DEC:FIRST-ONE"
        ),
        "INVALID_DIRECTION",
    )
    expect_code(
        lambda: validate_declaration([("schema", SCHEMA)], work_ref=WS, decision_ref="DEC:FIRST-ONE"),
        "INVALID_DIRECTION",
    )
    expect_code(
        lambda: validate_declaration(declaration(None), work_ref="WS:no", decision_ref="DEC:FIRST-ONE"),
        "INVALID_DIRECTION",
    )
    expect_code(
        lambda: validate_declaration(declaration(None), work_ref=WS, decision_ref="NOT-A-DEC"),
        "INVALID_DIRECTION",
    )


# ------------------------------------------------------------------ acceptance


def test_valid_single_row_shape_and_day_precision():
    decisions, chain_refs = build_chain(1)
    payload = project(decisions, chain_refs[0])
    assert set(payload) == {"work_ref", "workstream_source", "current", "history"}
    assert set(payload["history"]) == {"revisions", "has_more", "total_count"}
    row = payload["current"]
    assert set(row) == {
        "decision_ref",
        "answer",
        "rationale",
        "decided_by",
        "decided_at",
        "date_precision",
        "predecessor",
        "source",
    }
    assert row["decision_ref"] == chain_refs[0]
    assert row["predecessor"] is None
    assert row["date_precision"] == "DAY"
    assert payload["history"] == {"revisions": [], "has_more": False, "total_count": 1}
    assert payload["workstream_source"] == ws_source()
    assert set(payload["workstream_source"]) == {"repository", "commit", "path", "content_sha256"}


def test_chain_order_follows_explicit_predecessors_not_dates():
    # Same-day and reverse-dated rows must never be re-elected or reordered.
    decisions, chain_refs = build_chain(3, dates=["2026-01-05", "2026-01-05", "2026-01-09"])
    payload = project(decisions, chain_refs[0])
    assert payload["current"]["decision_ref"] == chain_refs[0]
    revisions = payload["history"]["revisions"]
    assert [r["decision_ref"] for r in revisions] == [chain_refs[1], chain_refs[2]]
    assert payload["history"]["total_count"] == 3
    assert payload["history"]["has_more"] is False
    # Dates are projected verbatim as captured facts.
    assert [r["decided_at"] for r in revisions] == ["2026-01-05", "2026-01-09"]


def test_date_object_converts_to_exact_iso_and_day_precision():
    decisions, chain_refs = build_chain(1)
    ref = chain_refs[0]
    decisions[ref]["record"]["decided_at"] = datetime.date(2026, 2, 3)
    payload = project(decisions, ref)
    assert payload["current"]["decided_at"] == "2026-02-03"
    assert payload["current"]["date_precision"] == "DAY"


def test_datetime_object_is_not_a_date_only_value():
    decisions, chain_refs = build_chain(1)
    decisions[chain_refs[0]]["record"]["decided_at"] = datetime.datetime(2026, 2, 3, 9, 30)
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_DIRECTION")


def test_non_canonical_date_string_rejected():
    decisions, chain_refs = build_chain(1)
    decisions[chain_refs[0]]["record"]["decided_at"] = "2026-2-3"
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_DIRECTION")


def test_text_bounds_enforced():
    decisions, chain_refs = build_chain(1)
    ref = chain_refs[0]
    for field, limit in (("answer", 4096), ("rationale", 4096), ("decided_by", 256)):
        decisions[ref]["record"][field] = "x" * (limit + 1)
        expect_code(lambda: project(decisions, ref), "INVALID_DIRECTION")
        decisions[ref]["record"][field] = ""
        expect_code(lambda: project(decisions, ref), "INVALID_DIRECTION")
        decisions[ref]["record"][field] = "x" * limit
        payload = project(decisions, ref)
        assert len(payload["current"][field]) == limit
        decisions[ref]["record"][field] = "Value for " + ref


def test_record_key_must_match_ref():
    decisions, chain_refs = build_chain(1)
    decisions[chain_refs[0]]["record"]["key"] = "DEC:OTHER-KEY"
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_DIRECTION")


def test_affects_must_include_exact_workstream():
    decisions, chain_refs = build_chain(1)
    decisions[chain_refs[0]]["record"]["affects"] = ["WS:OTHER-REFIT"]
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_DIRECTION")
    decisions[chain_refs[0]]["record"]["affects"] = "WS:MARKET-INTEL-REFIT"
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_DIRECTION")


# --------------------------------------------------------------- NOT_DECLARED


def test_objective_only_workstream_is_not_declared():
    ws = workstream(None)
    ws["objective"] = "objective text"
    ws["decisions"] = [{"ref": "DEC:DIR-0001", "verdict": "go"}]
    ws["status"] = "OPEN"
    decisions, chain_refs = build_chain(1)
    expect_code(lambda: project(decisions, None, ws=ws), "NOT_DECLARED")


def test_malformed_present_pointer_is_invalid_not_absent():
    decisions, chain_refs = build_chain(1)
    expect_code(
        lambda: project(decisions, None, ws=workstream("DIR-0001")), "INVALID_DIRECTION"
    )
    expect_code(
        lambda: project(decisions, None, ws=workstream(chain_refs[0].lower())), "INVALID_DIRECTION"
    )


def test_generic_decision_or_plan_adoption_never_counts_as_accepted():
    decisions, chain_refs = build_chain(1)
    ws = workstream(None)
    ws["project_plan_adoption"] = chain_refs[0]
    ws["accepted_decision"] = chain_refs[0]
    expect_code(lambda: project(decisions, None, ws=ws), "NOT_DECLARED")


# ---------------------------------------------------------------- source shape


def test_workstream_source_shape_validated_even_with_empty_chain():
    decisions, chain_refs = build_chain(1)
    expect_code(
        lambda: project(decisions, chain_refs[0], source=ws_source(commit="ZZ")),
        "INVALID_SOURCE",
    )
    expect_code(
        lambda: project(
            decisions, chain_refs[0], source=ws_source(path="elsewhere/direction.md")
        ),
        "INVALID_SOURCE",
    )
    expect_code(
        lambda: project(
            decisions, chain_refs[0], source=ws_source(content_sha256=DIGEST.upper())
        ),
        "INVALID_SOURCE",
    )
    bad = ws_source()
    bad.pop("repository")
    expect_code(lambda: project(decisions, chain_refs[0], source=bad), "INVALID_SOURCE")
    bad = ws_source()
    bad["surplus"] = 1
    expect_code(lambda: project(decisions, chain_refs[0], source=bad), "INVALID_SOURCE")
    expect_code(
        lambda: project(decisions, chain_refs[0], source="not-a-mapping"),
        "INVALID_SOURCE",
    )


def test_row_source_commit_must_match_single_captured_revision():
    decisions, chain_refs = build_chain(2)
    decisions[chain_refs[1]] = entry(
        chain_refs[1],
        predecessor=None,
        superseded_by=chain_refs[0],
        source_override=dec_source(chain_refs[1], commit="b" * 40),
    )
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_SOURCE")


def test_row_caller_path_and_cross_path_rejected():
    decisions, chain_refs = build_chain(1)
    decisions[chain_refs[0]]["source"] = dec_source(
        chain_refs[0], path="../" + DEC_PATH_TEMPLATE.format(key=chain_refs[0][4:])
    )
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_SOURCE")
    decisions[chain_refs[0]]["source"] = dec_source(
        chain_refs[0], path=WS_PATH_TEMPLATE.format(key=WS_KEY)
    )
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_SOURCE")
    decisions[chain_refs[0]]["source"] = dec_source(
        chain_refs[0], path=DEC_PATH_TEMPLATE.format(key="DIR-9999")
    )
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_SOURCE")


def test_repository_must_be_the_closed_macro_repository():
    decisions, chain_refs = build_chain(1)
    decisions[chain_refs[0]]["source"] = dec_source(
        chain_refs[0], repository="other-org/other-repo"
    )
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_SOURCE")


# -------------------------------------------------------------------- lineage


def test_broken_reciprocal_superseded_by_rejected():
    decisions, chain_refs = build_chain(2)
    decisions[chain_refs[1]]["record"].pop("superseded_by")
    expect_code(lambda: project(decisions, chain_refs[0]), "LINEAGE_CONFLICT")
    decisions[chain_refs[1]] = entry(
        chain_refs[1],
        predecessor=None,
        superseded_by="DEC:UNRELATED",
    )
    expect_code(lambda: project(decisions, chain_refs[0]), "LINEAGE_CONFLICT")


def test_extra_predecessor_branch_rejected():
    decisions, chain_refs = build_chain(2)
    decisions[chain_refs[0]]["record"]["supersedes"] = [chain_refs[1], "DEC:DIR-0003"]
    expect_code(lambda: project(decisions, chain_refs[0]), "LINEAGE_CONFLICT")


def test_missing_reciprocal_supersedes_rejected():
    decisions, chain_refs = build_chain(2)
    decisions[chain_refs[0]]["record"].pop("supersedes")
    expect_code(lambda: project(decisions, chain_refs[0]), "LINEAGE_CONFLICT")


def test_oldest_row_with_nonempty_supersedes_rejected():
    decisions, chain_refs = build_chain(2)
    decisions[chain_refs[1]]["record"]["supersedes"] = ["DEC:DIR-0003"]
    expect_code(lambda: project(decisions, chain_refs[0]), "LINEAGE_CONFLICT")


def test_current_row_must_not_be_superseded():
    decisions, chain_refs = build_chain(1)
    decisions[chain_refs[0]]["record"]["superseded_by"] = "DEC:DIR-0002"
    expect_code(lambda: project(decisions, chain_refs[0]), "LINEAGE_CONFLICT")


def test_cycle_rejected():
    newer, older = refs(2)
    decisions = {
        newer: entry(newer, predecessor=older, superseded_by=None),
        older: entry(older, predecessor=newer, superseded_by=newer),
    }
    expect_code(lambda: project(decisions, newer), "LINEAGE_CONFLICT")


def test_self_predecessor_rejected():
    decisions, chain_refs = build_chain(1)
    decisions[chain_refs[0]] = entry(
        chain_refs[0], predecessor=chain_refs[0], superseded_by=None
    )
    with pytest.raises(DirectionError) as excinfo:
        project(decisions, chain_refs[0])
    assert excinfo.value.code in {"LINEAGE_CONFLICT", "INVALID_DIRECTION"}


def test_missing_predecessor_rejected():
    decisions, chain_refs = build_chain(1)
    expect_code(lambda: project(decisions, "DEC:ABSENT-REF"), "LINEAGE_INCOMPLETE")


def test_cross_ws_direction_rejected():
    decisions, chain_refs = build_chain(1)
    decisions[chain_refs[0]] = entry(
        chain_refs[0], predecessor=None, work_ref="WS:OTHER-REFIT", superseded_by=None
    )
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_DIRECTION")


def test_row_declaring_generic_adoption_rejected():
    decisions, chain_refs = build_chain(1)
    ref = chain_refs[0]
    record = dec_record(ref, predecessor=None)
    record["direction"] = declaration(None, schema="project_plan_adoption.v1")
    decisions[ref] = {"record": record, "source": dec_source(ref)}
    expect_code(lambda: project(decisions, ref), "INVALID_DIRECTION")


# -------------------------------------------------------------------- bounding


def test_eight_of_nine_bounded_unknown_total():
    decisions, chain_refs = build_chain(9)
    decisions[chain_refs[8]]["record"]["answer"] = "NINTH-ROW-ONLY-MARKER"
    payload = project(decisions, chain_refs[0], max_revisions=8)
    history = payload["history"]
    assert history["has_more"] is True
    assert history["total_count"] is None
    assert len(history["revisions"]) == 7
    assert payload["current"]["decision_ref"] == chain_refs[0]
    assert history["revisions"][0]["decision_ref"] == chain_refs[1]
    assert history["revisions"][-1]["decision_ref"] == chain_refs[7]
    blob = json.dumps(payload)
    # The bounded walk keeps the 8th row's explicit pointer but never loads row 9.
    assert history["revisions"][-1]["predecessor"] == chain_refs[8]
    assert "NINTH-ROW-ONLY-MARKER" not in blob
    assert "agentos/decisions/DEC-DIR-0009.md" not in blob


def test_limit_reached_with_finished_chain_reports_total():
    decisions, chain_refs = build_chain(8)
    payload = project(decisions, chain_refs[0], max_revisions=8)
    assert payload["history"]["has_more"] is False
    assert payload["history"]["total_count"] == 8
    assert payload["history"]["revisions"][0]["decision_ref"] == chain_refs[1]
    assert len(payload["history"]["revisions"]) == 7


def test_single_row_bound_with_predecessor_present():
    decisions, chain_refs = build_chain(3)
    payload = project(decisions, chain_refs[0], max_revisions=1)
    assert payload["current"]["decision_ref"] == chain_refs[0]
    assert payload["history"]["revisions"] == []
    assert payload["history"]["has_more"] is True
    assert payload["history"]["total_count"] is None


@pytest.mark.parametrize("bad", [0, 9, True, False, "3", 2.0, None])
def test_max_revisions_bounds(bad):
    decisions, chain_refs = build_chain(1)
    expect_code(
        lambda: project_direction(
            work_ref=WS,
            workstream=workstream(chain_refs[0]),
            workstream_source=ws_source(),
            decisions=decisions,
            max_revisions=bad,
        ),
        "INVALID_DIRECTION",
    )


def test_decision_entry_cap():
    over = {"DEC:N%03d" % i: {"record": {}, "source": {}} for i in range(129)}
    expect_code(lambda: project(over, "DEC:N000"), "INVALID_DIRECTION")


def test_offchain_and_malformed_entries_rejected():
    decisions, chain_refs = build_chain(1)
    decisions["DIR-0002"] = decisions[chain_refs[0]]
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_DIRECTION")
    decisions, chain_refs = build_chain(1)
    decisions[chain_refs[0]] = {"record": decisions[chain_refs[0]]["record"]}
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_DIRECTION")
    decisions, chain_refs = build_chain(1)
    decisions[chain_refs[0]]["record"] = ["not", "a", "mapping"]
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_DIRECTION")


def test_workstream_key_must_match_work_ref():
    decisions, chain_refs = build_chain(1)
    expect_code(
        lambda: project(decisions, chain_refs[0], ws=workstream(chain_refs[0], key="WS:OTHER-REFIT")),
        "INVALID_DIRECTION",
    )
    expect_code(
        lambda: project_direction(
            work_ref=WS,
            workstream="not-a-mapping",
            workstream_source=ws_source(),
            decisions=decisions,
        ),
        "INVALID_DIRECTION",
    )
    expect_code(
        lambda: project_direction(
            work_ref="WS:no",
            workstream=workstream("DEC:DIR-0001"),
            workstream_source=ws_source(),
            decisions=decisions,
        ),
        "INVALID_DIRECTION",
    )


# -------------------------------------------------------------- projection box


def test_secret_raw_body_evidence_and_questions_are_not_projected():
    decisions, chain_refs = build_chain(2)
    decisions[chain_refs[0]]["record"]["raw_body"] = "SECRET-RAW-BODY"
    decisions[chain_refs[0]]["record"]["evidence"] = ["/evidence/secret-path.md"]
    decisions[chain_refs[0]]["record"]["questions"] = "what about pricing?"
    decisions[chain_refs[1]]["record"]["raw_body"] = "SECRET-PRIOR-BODY"
    payload = project(decisions, chain_refs[0])
    blob = json.dumps(payload)
    assert "SECRET-RAW-BODY" not in blob
    assert "SECRET-PRIOR-BODY" not in blob
    assert "evidence" not in blob
    assert "questions" not in blob
    for row in [payload["current"], *payload["history"]["revisions"]]:
        assert set(row) == {
            "decision_ref",
            "answer",
            "rationale",
            "decided_by",
            "decided_at",
            "date_precision",
            "predecessor",
            "source",
        }


def test_outputs_are_detached_from_inputs_and_calls():
    decisions, chain_refs = build_chain(2)
    ws = workstream(chain_refs[0])
    source = ws_source()
    snapshot = copy.deepcopy((decisions, ws, source))
    first = project(decisions, chain_refs[0], ws=ws, source=source)
    first["current"]["answer"] = "MUTATED"
    first["current"]["source"]["commit"] = "MUTATED"
    first["history"]["revisions"].clear()
    first["workstream_source"]["path"] = "MUTATED"
    assert (decisions, ws, source) == snapshot
    second = project(decisions, chain_refs[0], ws=ws, source=source)
    assert second["current"]["answer"].startswith("Answer for ")
    assert second["current"]["source"]["commit"] == COMMIT
    assert len(second["history"]["revisions"]) == 1
    assert second["workstream_source"] == ws_source()


def test_over_budget_payload_is_never_truncated():
    decisions, chain_refs = build_chain(8)
    for ref in chain_refs:
        decisions[ref]["record"]["answer"] = "x" * 4096
        decisions[ref]["record"]["rationale"] = "y" * 4096
    error = expect_code(
        lambda: project(decisions, chain_refs[0], max_revisions=8), "CONTENT_OVER_BUDGET"
    )
    assert str(error) == "CONTENT_OVER_BUDGET"
    # A comfortably bounded payload still serializes under the same budget.
    decisions[chain_refs[0]]["record"]["answer"] = "Answer for " + chain_refs[0]
    payload = project(decisions, chain_refs[0], max_revisions=8)
    assert len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) <= OUTPUT_BUDGET_BYTES


def test_error_type_is_valueerror_without_data_echo():
    error = expect_code(lambda: project({}, "DEC:ABSENT-REF"), "LINEAGE_INCOMPLETE")
    assert isinstance(error, ValueError)
    assert "ABSENT" not in error.args[0] or error.args[0] == "LINEAGE_INCOMPLETE"
    assert error.args[0] == error.code
    assert len(error.args) == 1


def test_workstream_records_without_direction_records_stay_not_declared():
    ws = {
        "key": WS_KEY,
        "objective": "obj",
        "status": "OPEN",
        "decisions": ["DEC:DIR-0001"],
        "project_plan_adoption": {"decision": "DEC:DIR-0001"},
    }
    decisions, chain_refs = build_chain(1)
    expect_code(lambda: project(decisions, chain_refs[0], ws=ws), "NOT_DECLARED")


def test_actual_canonical_owner_keys_and_paths_are_not_prefixed_record_keys():
    decisions, chain_refs = build_chain(1)
    value = project(decisions, chain_refs[0])
    assert value["workstream_source"]["path"] == "agentos/workstreams/WS-MARKET-INTEL-REFIT.md"
    assert value["current"]["source"]["path"] == "agentos/decisions/DEC-DIR-0001.md"
    assert decisions[chain_refs[0]]["record"]["key"] == "DIR-0001"


def test_visible_cycle_at_eighth_row_is_not_mislabelled_truncated_history():
    decisions, chain_refs = build_chain(8)
    last = decisions[chain_refs[-1]]["record"]
    last["direction"]["predecessor"] = chain_refs[0]
    last["supersedes"] = [chain_refs[0]]
    expect_code(lambda: project(decisions, chain_refs[0]), "LINEAGE_CONFLICT")


def test_utf8_byte_bounds_blank_text_and_mixed_adoption_are_rejected():
    for field, text in (("answer", " "), ("rationale", "中" * 1400), ("decided_by", "中" * 86)):
        decisions, chain_refs = build_chain(1)
        decisions[chain_refs[0]]["record"][field] = text
        expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_DIRECTION")
    decisions, chain_refs = build_chain(1)
    decisions[chain_refs[0]]["record"]["project_plan_adoption"] = {}
    expect_code(lambda: project(decisions, chain_refs[0]), "INVALID_DIRECTION")
