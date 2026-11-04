"""Actual canonical Agent OS parser + inert fixed-publisher recipes."""
import copy
import hashlib
from pathlib import Path

import pytest

from scripts import agentos
from scripts import agentos_direction_acceptance as recipe

COMMIT = "a" * 40
WORK = "WS:DIRECTION-TEST"
PATH = "agentos/workstreams/WS-DIRECTION-TEST.md"
RAW = b"""---
key: DIRECTION-TEST
title: A source-bound programme
objective: Complete the real requested journey.
status: active
program: executive-os
repos: [macro, mastermind]
owner: astra-meta-ceo
class: build
blast_radius: user_facing
ambiguity: scoped
waves:
  - id: ONE
    title: Deliver the journey
    status: in_progress
next_action: Preserve the existing acceptance obligations.
---
\nRetained body bytes and context.\n
"""


def source(path, raw):
    return {"repository": "mastermindx-market-intelligence/macro", "commit": COMMIT,
            "path": path, "content_sha256": hashlib.sha256(raw).hexdigest()}


def request():
    return {"schema": recipe.REQUEST_SCHEMA, "request_id": "direction-test-1", "expected_commit": COMMIT,
            "work_ref": WORK, "expected_predecessor": None, "decision": {
            "key": "FIRST-DIRECTION", "question": "What outcome is accepted as the current Direction?",
            "answer": "Complete the original journey and its interrupted cases.",
            "rationale": "The delegated principal explicitly decided this outcome today.",
            "alternatives": [{"option": "Treat authored plan revisions as accepted Direction", "why_not": "Those are different owner facts."}],
            "evidence": ["Inert test fixture, never a production decision."], "confidence": "high", "reversibility": "easy"}}


def compile(value=None, **overrides):
    args = dict(captured_commit=COMMIT, workstream_bytes=RAW, workstream_source=source(PATH, RAW),
                new_decision_absent=True, permission_binding_digest="c" * 64,
                decision_actor="test-principal", decision_date="2026-11-04")
    args.update(overrides)
    return recipe.compile_acceptance(value or request(), **args)


def parse(text):
    class Captured:
        def read_text(self, *, encoding):
            assert encoding == "utf-8"
            return text
    return agentos.parse_record(Captured())


def test_initial_recipe_preserves_all_other_canonical_fields_and_body():
    result = compile()
    assert result["state"] == "DRAFT_ONLY"
    assert result["operation_id"].startswith("mmos-direction-accept-") and len(result["operation_id"]) == 62
    ws_image, dec_image = result["postimages"]
    assert ws_image["path"] == PATH and ws_image["expected_sha256"] == source(PATH, RAW)["content_sha256"]
    before, before_body = parse(RAW.decode())
    after, after_body = parse(ws_image["content_utf8"])
    assert after.pop("accepted_direction") == "DEC:FIRST-DIRECTION"
    assert after.pop("decisions") == ["DEC:FIRST-DIRECTION"]
    assert after == before and after_body == before_body
    dec, _ = parse(dec_image["content_utf8"])
    assert dec_image["expected_sha256"] is None
    assert dec["direction"] == {"schema": "agentos.direction_acceptance.v1", "state": "ACCEPTED", "work_ref": WORK, "predecessor": None}
    assert dec["affects"] == [WORK] and "supersedes" not in dec and "superseded_by" not in dec
    assert not any(p.hard for p in agentos.check_decision(dec, Path(dec_image["path"])))
    assert "Runtime authorization remain separate" not in dec["answer"]


def test_replacement_changes_only_pointer_index_and_reciprocal_predecessor():
    first = compile()
    old_ws, old_dec = [p["content_utf8"].encode() for p in first["postimages"]]
    old_path = first["postimages"][1]["path"]
    req = request(); req["request_id"] = "direction-test-2"; req["decision"]["key"] = "SECOND-DIRECTION"
    req["decision"]["answer"] = "A real explicit correction."; req["expected_predecessor"] = "DEC:FIRST-DIRECTION"
    result = compile(req, workstream_bytes=old_ws, workstream_source=source(PATH, old_ws),
                     predecessor_bytes=old_dec, predecessor_source=source(old_path, old_dec))
    assert len(result["postimages"]) == 3
    current, _ = parse(result["postimages"][1]["content_utf8"])
    previous, body = parse(result["postimages"][2]["content_utf8"])
    original, original_body = parse(old_dec.decode())
    assert current["supersedes"] == ["DEC:FIRST-DIRECTION"] and current["direction"]["predecessor"] == "DEC:FIRST-DIRECTION"
    assert previous.pop("superseded_by") == "DEC:SECOND-DIRECTION"
    assert previous == original and body == original_body


def test_existing_original_operation_only_reconciles_without_source_recompile():
    first = compile()
    old = {k: first[k] for k in ("operation_id", "request_id", "request_sha256")}
    result = compile(original_operation=old, workstream_bytes=None, workstream_source=None, new_decision_absent=False)
    assert result["state"] == "READ_ONLY_RECONCILIATION" and result["postimages"] == []
    req = request(); req["decision"]["answer"] = "A different payload under the same ID"
    with pytest.raises(recipe.DirectionRecipeError, match="^CONFLICT$"):
        compile(req, original_operation=old)
    with pytest.raises(recipe.DirectionRecipeError, match="^CONFLICT$"):
        compile(original_operation=old, decision_actor="another-principal")
    with pytest.raises(recipe.DirectionRecipeError, match="^CONFLICT$"):
        compile(original_operation=old, permission_binding_digest="d" * 64)


@pytest.mark.parametrize("change,code", [
    ("commit", "STALE_SOURCE"), ("digest", "INVALID_SOURCE"), ("path", "INVALID_SOURCE"),
    ("missing_predecessor", "STALE_PREDECESSOR"), ("exists", "DECISION_EXISTS"),
    ("date", "INVALID_DIRECTION"), ("time", "INVALID_DIRECTION"), ("runtime", "INVALID_REQUEST"),
    ("permission", "INVALID_REQUEST"), ("same_ref", "INVALID_DIRECTION"), ("actor_spoof", "INVALID_REQUEST"),
])
def test_exact_source_and_authoring_negative_cases(change, code):
    req = request(); args = {}
    if change == "commit": req["expected_commit"] = "b" * 40
    if change in ("digest", "path"):
        wrong = source(PATH, RAW); wrong["content_sha256" if change == "digest" else "path"] = "b" * 64 if change == "digest" else "agentos/workstreams/WS-OTHER.md"
        args["workstream_source"] = wrong
    if change == "missing_predecessor": req["expected_predecessor"] = "DEC:ABSENT"
    if change == "exists": args["new_decision_absent"] = False
    if change == "date": args["decision_date"] = "2026-02-30"
    if change == "time": args["decision_date"] = "2026-11-04T01:02:03Z"
    if change == "runtime": req["decision"]["runtime_grant"] = True
    if change == "permission": args["permission_binding_digest"] = "permission=true"
    if change == "same_ref": req["expected_predecessor"] = "DEC:FIRST-DIRECTION"
    if change == "actor_spoof": req["decision"]["decided_by"] = "chairman"
    with pytest.raises(recipe.DirectionRecipeError) as caught:
        compile(req, **args)
    assert caught.value.code == code and str(caught.value) == code


def test_inert_compiler_never_opens_or_writes_source_and_detaches_input(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Draft compiler performed I/O")
    req = request(); saved = copy.deepcopy(req)
    # Canonical checker may query sibling existence for optional references;
    # this fixture has no such authored references and opens no source.
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    result = compile(req)
    assert req == saved
    req["decision"]["answer"] = "mutated"
    assert "mutated" not in result["postimages"][1]["content_utf8"]
