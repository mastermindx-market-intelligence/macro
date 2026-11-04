"""Existing native Agent OS owner validates optional accepted Direction facts."""
import copy
import datetime as dt
from pathlib import Path

import pytest
from scripts import agentos


def decision():
    return {"key": "DIRECTION-ONE", "question": "Which Direction is accepted?", "answer": "Complete the original journey.",
            "rationale": "The delegated principal explicitly decided this outcome.",
            "alternatives": [{"option": "Infer from objective", "why_not": "Different source fact"}],
            "evidence": ["Inert fixture"], "affects": ["WS:DIRECTION-TEST"], "confidence": "high", "reversibility": "easy",
            "decided_by": "fixture-principal", "decided_at": "2026-11-04", "direction": {
            "schema": "agentos.direction_acceptance.v1", "state": "ACCEPTED", "work_ref": "WS:DIRECTION-TEST", "predecessor": None}}


def workstream():
    return {"key": "DIRECTION-TEST", "title": "A programme", "objective": "A complete real journey", "status": "active",
            "program": "executive-os", "repos": ["macro"], "owner": "ceo", "class": "build", "blast_radius": "user_facing",
            "ambiguity": "scoped", "waves": [{"id": "ONE", "title": "Deliver", "status": "in_progress"}],
            "next_action": "Deliver the original journey.", "decisions": ["DEC:DIRECTION-ONE"], "accepted_direction": "DEC:DIRECTION-ONE"}


def check_dec(rec):
    return agentos.check_decision(rec, Path("agentos/decisions/DEC-DIRECTION-ONE.md"))


def test_exact_optional_declaration_and_day_precision_are_native_owner_facts():
    assert not any(p.hard for p in check_dec(decision()))
    rec = decision(); rec["decided_at"] = dt.date(2026, 11, 4)
    assert not any(p.hard for p in check_dec(rec))
    assert not any(p.hard for p in agentos.check_workstream(workstream(), Path("agentos/workstreams/WS-DIRECTION-TEST.md"), None))


@pytest.mark.parametrize("change", ["extra", "scope", "predecessor_missing", "self", "supersedes_extra", "date_time", "date_invalid", "datetime_object", "affects", "empty_answer", "state", "schema", "plan_adoption"])
def test_malformed_or_cross_owner_declaration_is_not_a_direction(change):
    rec = decision()
    if change == "extra": rec["direction"]["runtime_grant"] = True
    if change == "scope": rec["direction"]["work_ref"] = "WS:OTHER"
    if change == "predecessor_missing": rec["direction"].pop("predecessor")
    if change == "self": rec["direction"]["predecessor"] = "DEC:DIRECTION-ONE"
    if change == "supersedes_extra": rec["supersedes"] = ["DEC:OTHER"]
    if change == "date_time": rec["decided_at"] = "2026-11-04T00:00:00Z"
    if change == "date_invalid": rec["decided_at"] = "2026-02-30"
    if change == "datetime_object": rec["decided_at"] = dt.datetime(2026, 11, 4)
    if change == "affects": rec["affects"] = ["WS:OTHER"]
    if change == "empty_answer": rec["answer"] = " "
    if change == "state": rec["direction"]["state"] = "PROPOSED"
    if change == "schema": rec["direction"]["schema"] = "agentos.project_plan_adoption.v1"
    if change == "plan_adoption": rec["project_plan_adoption"] = {}
    assert any(p.hard and p.rule == "bad-direction" for p in check_dec(rec))


@pytest.mark.parametrize("value,indexed", [(None, True), ("DEC:../private", True), ("DEC:DIRECTION-ONE", False)])
def test_pointer_is_explicit_canonical_and_also_in_existing_decision_index(value, indexed):
    rec = workstream(); rec["accepted_direction"] = value
    if not indexed: rec["decisions"] = []
    problems = agentos.check_workstream(rec, Path("agentos/workstreams/WS-DIRECTION-TEST.md"), None)
    assert any(p.hard and p.rule == "bad-direction" for p in problems)


def test_legacy_records_remain_unchanged_and_do_not_load_new_helper(monkeypatch):
    old = decision(); old.pop("direction"); old["decided_at"] = "2026-11-04T00:00:00Z"
    ws = workstream(); ws.pop("accepted_direction")
    before = copy.deepcopy((old, ws))
    def forbidden(*args, **kwargs):
        pytest.fail("Optional Direction validation tried to acquire a helper/source")
    monkeypatch.setattr(Path, "open", forbidden)
    assert not any(p.hard for p in check_dec(old))
    assert not any(p.hard for p in agentos.check_workstream(ws, Path("agentos/workstreams/WS-DIRECTION-TEST.md"), None))
    # The new typed Direction also remains readable by the old installed
    # brief capture containing agentos.py but no separate Direction helper.
    assert not any(p.hard for p in check_dec(decision()))
    assert (old, ws) == before
