"""Synthetic-only EVAL-1 receipt projection and non-executable runner boundary."""
import ast
import copy
import hashlib
import json
from pathlib import Path

import pytest

from engine import k3e_eval1_source_adapter as adapter


ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


@pytest.fixture(scope="module")
def artifacts():
    # Only the four existing SOURCE documents, never data/, a provider or outcomes.
    return {p: (ROOT / p).read_bytes() for p in adapter.CONTRACT_BLOBS}


def row():
    result = {"issuer_ref": "SYNTHETIC:ONE", "metric": "EPS", "fiscal_period": "2027Q1",
              "cutoff_session": "2026-10-07", "decision_cutoff": "2026-10-07T13:30:00Z",
              "provider": "synthetic", "ticker_compat": "SYN", "horizon_label_raw": "+1q"}
    query = {k: result[k] for k in ("provider", "ticker_compat", "metric", "horizon_label_raw")}
    query["as_of"] = result["decision_cutoff"]
    source = {"source_revision": "a" * 40,
              "inputs": {p: {"sha256": "b" * 64, "git_blob_id": "c" * 40}
                         for p in adapter.INPUT_PATHS}}
    payload = {"schema": "k3e.declared_capture_inspection.v1", "query": query, "source": source,
               "normalized_baseline": {"rights_state": "RIGHTS_BLOCKED"},
               "denominators": {"capture_clock_bounded_relevant_records": 10,
                                "true_missing_records": 3,
                                "invalid_or_inconsistent_excluded_records": 4,
                                "identity_unresolved_records": 6,
                                "valid_captured_records": 6},
               "latest_captured_snapshot": {"private_raw_body": "DO_NOT_RETURN_SYNTHETIC_BODY"}}
    payload["query_identity"] = digest({k: payload[k] for k in ("schema", "query", "source")})
    result["exp1_receipt"] = {"emitter": dict(adapter.EMITTER), "semantic_payload": payload,
                              "semantic_digest": digest(payload)}
    return result


def seal(receipt):
    receipt["semantic_digest"] = digest(receipt["semantic_payload"])


def project(artifacts, rows=None):
    return adapter.prepare_source_rows([row()] if rows is None else rows, frozen_artifacts=artifacts)


def test_frozen_trial_and_exact_three_unprocessed_features(artifacts):
    result = project(artifacts)
    identity = json.loads(artifacts[adapter.CONTRACT_DIR + "eval1_challenger_trial_identity.v1.json"])
    assert len(identity["elements"]) == 7
    assert result["feature_names"] == [f["name"] for f in identity["elements"]["feature_set"]["value"]["features"]]
    assert result["horizon"] == {"sessions": 21, "calendar": "NYSE"}
    assert result["target"] == identity["elements"]["target"]["value"]["target_id"]
    out = result["rows"][0]
    assert out["features"] == {"rights_blocked_state": 1.0, "true_missing_share": 0.3,
                                "invalid_or_inconsistent_excluded_share": 0.4}
    assert set(out["feature_denominators"].values()) == {10}
    assert out["projection_status"] == "STRUCTURALLY_COMPATIBLE_UNTRUSTED"
    assert result["source_binding_status"] == "EXACT_SOURCE_BYTES_ONLY"
    assert "DO_NOT_RETURN_SYNTHETIC_BODY" not in json.dumps(result)


def test_rights_identity_correction_and_missing_rows_stay_in_total(artifacts):
    items = [row() for _ in range(5)]
    for i, item in enumerate(items):
        item["issuer_ref"] = f"SYNTHETIC:{i}"
    del items[1]["exp1_receipt"]
    items[2]["issuer_ref"] = None
    # Correction and unresolved identity diagnostics do not change the total,
    # select a last-supported snapshot, or invent a correction feature.
    items[3]["exp1_receipt"]["semantic_payload"]["correction_state"] = "REPLACED"
    seal(items[3]["exp1_receipt"])
    out = project(artifacts, items)
    assert len(out["rows"]) == 5
    assert out["denominators"] == {"declared_decision_rows": 5, "structurally_projected_rows": 3,
                                   "unavailable_rows": 2, "eligible_for_execution_rows": 0}
    for i in (0, 3, 4):
        assert set(out["rows"][i]["feature_denominators"].values()) == {10}
    assert all(v is None for v in out["rows"][1]["features"].values())
    assert all(v is None for v in out["rows"][2]["features"].values())
    assert all(not r["eligible_for_execution"] for r in out["rows"])


def test_empty_emitter_denominator_does_not_zero_fill_missing_shares(artifacts):
    item = row()
    payload = item["exp1_receipt"]["semantic_payload"]
    payload["denominators"].update(capture_clock_bounded_relevant_records=0,
                                  true_missing_records=0, invalid_or_inconsistent_excluded_records=0)
    payload["normalized_baseline"]["rights_state"] = "UNKNOWN"
    seal(item["exp1_receipt"])
    out = project(artifacts, [item])["rows"][0]
    # Frozen indicator transform explicitly maps UNKNOWN to 0, never a rights grant.
    assert out["features"] == dict(zip(adapter.FEATURES, (0.0, None, None)))
    assert out["eligible_for_execution"] is False
    assert "RIGHTS_ADMISSION_UNVERIFIED" in out["qualification_gaps"]


@pytest.mark.parametrize("change", ["later_cutoff", "earlier_cutoff", "other_ticker", "other_metric"])
def test_exact_cutoff_and_node_no_latest_or_future_backfill(artifacts, change):
    item = row()
    query = item["exp1_receipt"]["semantic_payload"]["query"]
    if change == "later_cutoff": query["as_of"] = "2026-10-08T13:30:00Z"
    if change == "earlier_cutoff": query["as_of"] = "2026-10-06T13:30:00Z"
    if change == "other_ticker": query["ticker_compat"] = "OTHER"
    if change == "other_metric": query["metric"] = "revenue"
    seal(item["exp1_receipt"])
    out = project(artifacts, [item])
    assert out["rows"][0]["refusals"] == ["EXACT_ROW_CUTOFF_QUERY_REQUIRED"]
    assert out["denominators"]["declared_decision_rows"] == 1
    assert all(v is None for v in out["rows"][0]["features"].values())


def test_duplicate_generations_are_both_withheld_not_latest_selected(artifacts):
    first, later = row(), row()
    later["exp1_receipt"]["semantic_payload"]["source"]["source_revision"] = "d" * 40
    # Even an invalid later receipt cannot silently erase the older denominator row.
    out = project(artifacts, [first, later])
    assert out["denominators"]["declared_decision_rows"] == 2
    assert out["denominators"]["unavailable_rows"] == 2
    for item in out["rows"]:
        assert item["refusals"] == ["DUPLICATE_TRIAL_ROW_GENERATIONS"]
        assert all(v is None for v in item["features"].values())


@pytest.mark.parametrize("change,reason", [
    ("current_emitter", "FROZEN_EMITTER_IDENTITY_MISMATCH"),
    ("moving_revision", "IMMUTABLE_SOURCE_PINS_REQUIRED"),
    ("missing_attempt_pin", "PAIRED_INPUT_PINS_REQUIRED"),
    ("tampered_digest", "EXP1_SEMANTIC_DIGEST_MISMATCH"),
    ("query_identity", "EXP1_QUERY_IDENTITY_MISMATCH"),
    ("bad_rights", "INVALID_FROZEN_RIGHTS_STATE"),
    ("negative_total", "INVALID_FEATURE_DENOMINATORS"),
    ("missing_count", "INVALID_FEATURE_DENOMINATORS"),
    ("bool_count", "INVALID_FEATURE_DENOMINATORS"),
    ("over_total", "INVALID_FEATURE_DENOMINATORS"),
    ("false_alias_marker", "INVALID_ALIAS_PIN"),
])
def test_structural_refusals_preserve_row_denominator(artifacts, change, reason):
    item = row()
    receipt, payload = item["exp1_receipt"], item["exp1_receipt"]["semantic_payload"]
    if change == "current_emitter": receipt["emitter"]["blob"] = "9aa555e923353f604c663706784012aae95145bb"
    if change == "moving_revision": payload["source"]["source_revision"] = "main"
    if change == "missing_attempt_pin": del payload["source"]["inputs"][adapter.INPUT_PATHS[1]]
    if change == "query_identity": payload["query_identity"] = "0" * 64
    if change == "bad_rights": payload["normalized_baseline"]["rights_state"] = "APPROVED"
    if change == "negative_total": payload["denominators"]["capture_clock_bounded_relevant_records"] = -1
    if change == "missing_count": del payload["denominators"]["true_missing_records"]
    if change == "bool_count": payload["denominators"]["true_missing_records"] = True
    if change == "over_total": payload["denominators"]["true_missing_records"] = 11
    if change == "false_alias_marker": payload["source"]["inputs"][adapter.ALIAS_PATH] = {"absent_at_revision": 1}
    seal(receipt)
    if change == "tampered_digest": receipt["semantic_digest"] = "0" * 64
    out = project(artifacts, [item])
    assert out["rows"][0]["refusals"] == [reason]
    assert out["denominators"]["declared_decision_rows"] == 1


@pytest.mark.parametrize("cutoff", [None, "2026-10-07T13:30:00", "2026-10-07T13:30:00+01:00", "tomorrow"])
def test_invalid_cutoff_stays_in_population(artifacts, cutoff):
    item = row()
    item["decision_cutoff"] = cutoff
    out = project(artifacts, [item])
    assert out["denominators"]["unavailable_rows"] == 1
    assert out["denominators"]["declared_decision_rows"] == 1


@pytest.mark.parametrize("changed", [None, "trial", "acceptance", "activation", "registration"])
def test_missing_or_changed_frozen_bytes_refuse_all_rows_without_new_trial(artifacts, changed):
    bad = dict(artifacts)
    if changed is None:
        bad = {}
    else:
        suffix = {"trial": "eval1_challenger_trial_identity.v1.json",
                  "acceptance": "eval1_owner_acceptance.v1.json",
                  "activation": "eval1_activation_receipt.v1.json",
                  "registration": "eval1_preregistration.v1.json"}[changed]
        bad[adapter.CONTRACT_DIR + suffix] += b" "
    out = project(bad)
    assert out["source_binding_status"] == "UNAVAILABLE"
    assert out["denominators"]["declared_decision_rows"] == 1
    assert out["denominators"]["eligible_for_execution_rows"] == 0


def test_forged_admission_and_future_vintage_never_become_provenance_or_execution(artifacts):
    item = row()
    item.update(outcome_access_allowed=True, admission_verified=True, labels=["UP"],
                eligible_for_execution=True, rights_granted=True, outcome_reader="DO_NOT_RETURN")
    item["exp1_receipt"].update(producer_verified=True, rights_granted=True)
    # A hash-shaped source revision has no temporal authenticity. Disclose that
    # gap even for an internally consistent, claimed post-cutoff source vintage.
    item["exp1_receipt"]["semantic_payload"]["claimed_source_created_at"] = "2099-01-01T00:00:00Z"
    seal(item["exp1_receipt"])
    out = project(artifacts, [item])
    assert out["rows"][0]["projection_status"] == "STRUCTURALLY_COMPATIBLE_UNTRUSTED"
    assert out["outcome_access_allowed"] is False
    assert out["rows"][0]["eligible_for_execution"] is False
    assert set(out["rows"][0]["qualification_gaps"]) == set(adapter.GAPS)
    assert "DO_NOT_RETURN" not in json.dumps(out)
    assert adapter.run_eval1(outcome_access_allowed=True)["status"] == "REFUSED"


@pytest.mark.parametrize("flag", [False, True, None, "true", {"admission": "qualified"}])
def test_refusal_runner_never_enables_effects(flag):
    result = adapter.run_eval1(outcome_access_allowed=flag)
    assert result["status"] == "REFUSED"
    assert result["reason"] == "SOURCE_ONLY_EXECUTION_DISABLED"
    assert result["execution_started"] is False
    assert result["outcome_access_allowed"] is False


def test_no_reader_callback_or_implicit_flag_coercion():
    class Bomb:
        def __bool__(self):
            raise AssertionError("must not interpret a permission object")
    assert adapter.run_eval1(outcome_access_allowed=Bomb())["status"] == "REFUSED"
    with pytest.raises(TypeError):
        adapter.run_eval1(outcome_reader=lambda: pytest.fail("outcome reader invoked"))


def test_no_io_and_no_mutation_even_with_forged_admission(artifacts, monkeypatch):
    import builtins
    import socket
    import subprocess

    items = [row()]
    before = copy.deepcopy(items)
    def prohibited(*args, **kwargs):
        pytest.fail("source projection attempted an I/O effect")
    monkeypatch.setattr(builtins, "open", prohibited)
    monkeypatch.setattr(Path, "read_bytes", prohibited)
    monkeypatch.setattr(Path, "read_text", prohibited)
    monkeypatch.setattr(socket, "socket", prohibited)
    monkeypatch.setattr(subprocess, "run", prohibited)
    monkeypatch.setattr(subprocess, "Popen", prohibited)
    assert project(artifacts, items)["denominators"]["eligible_for_execution_rows"] == 0
    assert adapter.run_eval1(outcome_access_allowed=True)["status"] == "REFUSED"
    assert items == before


def test_source_has_no_loader_label_model_or_provider_dependency():
    tree = ast.parse((ROOT / "engine/k3e_eval1_source_adapter.py").read_text())
    imports = {n.module if isinstance(n, ast.ImportFrom) else a.name
               for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
               for a in (n.names if isinstance(n, ast.Import) else [None])}
    assert imports == {"collections", "datetime", "hashlib", "json", "re"}
    forbidden = {"open", "exec", "eval", "__import__", "t1_label", "fit", "read_parquet", "read_csv"}
    assert not {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} & forbidden
