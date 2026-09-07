"""Fail-closed wrapper for the covenant-terms compile step (packet B-F09-5).

RULING BLOCKER-1 (elevated finding): .github/workflows/daily.yml runs this
script's main() immediately before the fail-closed health gate step, with no
`continue-on-error`. A producer bug there must never crash the daily job
before the health gate can even run (F13 alarm-bus law) -- main() must catch
ANY producer exception, record a typed covenant_extraction:{state: failed,
reason} marker that evaluate_health() reads on the very next step, and still
exit 0. These tests monkeypatch compile_from_disk() itself (never touching a
real source store/R2) to prove main()'s wrapper, independent of the producer
internals already covered by tests/test_covenant_terms.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import scripts.compile_capital_structure_covenant_terms as compile_script
from engine.capital_structure import covenant_terms as ct
from engine.capital_structure.ingestion_health import (
    COVENANT_EXTRACTION_FAILURE_FILENAME,
    covenant_extraction_coverage,
    evaluate_health,
    health_exit_code,
)
from engine.capital_structure.source_ledger_io import encode_source_ledger, source_ledger_path

FIXTURES = Path(__file__).parent / "fixtures" / "capital_structure"


def _real_manifest() -> dict:
    return json.loads((FIXTURES / "covenant_manifest_ledger.json").read_text())


def _real_direct_observations() -> list[dict]:
    """The two real direct observations from the committed Corsair fixture
    (tests/test_covenant_terms.py's own evidence) -- used here only as
    realistic, current-contract-valid records to mutate into a PRIOR-shape
    row for the quarantine tests below."""
    manifest = _real_manifest()
    text = (FIXTURES / "covenant_credit_agreement_submission.txt").read_text(encoding="utf-8")
    observations = ct.compile_observations(manifest, text, generated_at="2026-09-06T00:00:00Z")
    return [o for o in observations if o["state"]["disposition"] == "direct"]


def test_main_never_propagates_a_producer_exception_and_marks_the_health_artifact(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(compile_script, "_data_root", lambda: tmp_path)

    def _boom(root=None, *, generated_at=None, source_store=None):
        raise RuntimeError("malformed fixture: unbound _seq")

    monkeypatch.setattr(compile_script, "compile_from_disk", _boom)

    exit_code = compile_script.main([])

    assert exit_code == 0  # NEVER a non-zero exit on a producer bug
    marker_path = tmp_path / COVENANT_EXTRACTION_FAILURE_FILENAME
    assert marker_path.exists()
    marker = json.loads(marker_path.read_text())
    assert marker["state"] == "failed"
    assert "RuntimeError" in marker["reason"]
    assert "unbound _seq" in marker["reason"]
    assert marker["failed_at"]

    # the failure marker is exactly what evaluate_health() feeds into the
    # non-gating covenant_extraction census -- confirm the composed state.
    coverage = covenant_extraction_coverage([], [], failure=marker)
    assert coverage["state"] == "failed"
    assert coverage["reason"] == marker["reason"]
    assert coverage["observations"] == 0


def test_main_clears_a_stale_failure_marker_once_the_producer_recovers(tmp_path, monkeypatch):
    monkeypatch.setattr(compile_script, "_data_root", lambda: tmp_path)
    marker_path = tmp_path / COVENANT_EXTRACTION_FAILURE_FILENAME
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(json.dumps({"state": "failed", "reason": "stale", "failed_at": "x"}))

    monkeypatch.setattr(
        compile_script, "compile_from_disk",
        lambda root=None, *, generated_at=None, source_store=None: {
            "status": "ok", "schema": compile_script.COVENANT_TERM_SCHEMA,
            "eligible_manifests": 0, "deferred": 0, "observations": 0, "path": str(tmp_path),
        },
    )

    exit_code = compile_script.main([])

    assert exit_code == 0
    assert not marker_path.exists()  # a healed run clears the prior crash's marker


def test_main_never_propagates_when_clearing_a_stale_failure_marker_fails(tmp_path, monkeypatch):
    """RED-first for Minor-1 (round-4 review): `_clear_failure_marker(root)`
    used to sit OUTSIDE the try/except the round-3 Major-3 fix built, so an
    OSError/PermissionError from `path.unlink()` on an otherwise-successful
    run (the producer worked; only clearing the STALE marker failed) still
    propagated straight out of main() -- contradicting main()'s own
    docstring ('Never propagates an exception with a non-zero exit')."""
    monkeypatch.setattr(compile_script, "_data_root", lambda: tmp_path)
    monkeypatch.setattr(
        compile_script, "compile_from_disk",
        lambda root=None, *, generated_at=None, source_store=None: {
            "status": "ok", "schema": compile_script.COVENANT_TERM_SCHEMA,
            "eligible_manifests": 0, "deferred": 0, "observations": 0,
            "quarantined": 0, "quarantined_rows": [], "path": str(tmp_path),
        },
    )

    def _boom_clear(root):
        raise PermissionError("no permission to remove stale marker")

    monkeypatch.setattr(compile_script, "_clear_failure_marker", _boom_clear)

    exit_code = compile_script.main([])

    assert exit_code == 0  # NEVER a non-zero exit, even when clearing a stale marker fails
    marker_path = tmp_path / COVENANT_EXTRACTION_FAILURE_FILENAME
    marker = json.loads(marker_path.read_text())
    assert marker["state"] == "failed"
    assert "PermissionError" in marker["reason"]
    assert "no permission to remove stale marker" in marker["reason"]


def test_load_existing_observations_quarantines_a_row_that_fails_the_current_contract(tmp_path):
    """RED-first for Minor-2 (round-4 review, ruling): a historical ledger
    row written under a PRIOR contract shape must be quarantined -- excluded
    from the compiled set and reported with a reason -- never fatal. The
    contract is expected to evolve (this very PR changed evidence.
    publication's shape, added a required period_start, and fixed the
    relationships/version id patterns); a schema edit must never turn every
    future nightly run into a hard outage over rows written under a prior
    shape. Simulated here by dropping `document.document_type`, the exact
    field the round-3 fix newly required."""
    direct = _real_direct_observations()
    assert len(direct) >= 2
    valid = direct[0]
    stale_shape = json.loads(json.dumps(direct[1]))
    del stale_shape["document"]["document_type"]

    schema = compile_script._load_contract("capital_structure_covenant_term_observation.schema.json")
    frame = compile_script._to_frame([valid, stale_shape])
    ledger_path = tmp_path / "covenant_term_observations.parquet"
    frame.to_parquet(ledger_path, index=False)

    observations, quarantined = compile_script._load_existing_observations(ledger_path, schema)

    assert [o["observation_id"] for o in observations] == [valid["observation_id"]]
    assert len(quarantined) == 1
    assert quarantined[0]["observation_id"] == stale_shape["observation_id"]
    assert "document_type" in quarantined[0]["reason"]


def test_compile_from_disk_quarantines_a_prior_shape_row_and_reports_it_in_the_receipt(
    tmp_path, monkeypatch,
):
    """Integration path (Minor-2): a real prior nightly run left one
    CURRENT-shape row and one PRIOR-shape row on disk. compile_from_disk()
    must not raise, must drop the prior-shape row from what it re-persists,
    and must report it (count + reason) in the run receipt -- never
    silently and never fatal.

    The source-MANIFEST side of the pipeline (identity/content-binding) is
    stubbed out here -- the fixture manifest is a lightweight one built for
    engine.capital_structure.covenant_terms's own tests and was never meant
    to satisfy the full source_manifest contract's id grammar. That side is
    irrelevant to Minor-2 and already covered elsewhere; the real
    covenant-term OBSERVATION contract (what _load_existing_observations /
    _validate_observation_lineage validate the quarantine behavior against)
    is left completely real.
    """
    direct = _real_direct_observations()
    valid = direct[0]
    stale_shape = json.loads(json.dumps(direct[1]))
    del stale_shape["document"]["document_type"]

    frame = compile_script._to_frame([valid, stale_shape])
    ledger_path = tmp_path / "covenant_term_observations.parquet"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(ledger_path, index=False)
    # the still-valid row's source manifest must be present so
    # _validate_observation_lineage (an unrelated, already-covered check) has
    # something to bind it against.
    manifest_path = source_ledger_path(tmp_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(encode_source_ledger([_real_manifest()]))

    real_load_contract = compile_script._load_contract

    def _load_contract_stub(name):
        if name == "capital_structure_source_manifest.schema.json":
            return {}  # permissive: manifest-identity shape is out of scope here
        return real_load_contract(name)

    monkeypatch.setattr(compile_script, "_load_contract", _load_contract_stub)
    monkeypatch.setattr(compile_script, "validate_manifest_content_binding", lambda manifest: None)
    monkeypatch.setattr(compile_script, "validate_manifest_ledger", lambda manifests: None)

    result = compile_script.compile_from_disk(
        root=tmp_path, generated_at="2026-09-08T00:00:00Z", source_store={},
    )

    assert result["status"] == "ok"
    assert result["quarantined"] == 1
    assert result["quarantined_rows"][0]["observation_id"] == stale_shape["observation_id"]
    assert result["observations"] == 1  # only the still-valid row is re-persisted

    persisted = pd.read_parquet(ledger_path)
    assert persisted["observation_id"].tolist() == [valid["observation_id"]]


def test_covenant_extraction_coverage_reports_failed_state_with_a_reason():
    failed = covenant_extraction_coverage([], [], failure={"reason": "ValueError: boom"})
    assert failed == {
        "eligible_exhibits": 0,
        "covered_manifests": 0,
        "observations": 0,
        "issuers_covered": 0,
        "unavailable_terms": 0,
        "state": "failed",
        "reason": "ValueError: boom",
    }


def test_covenant_extraction_coverage_without_failure_is_unaffected():
    # No `failure` kwarg at all: behaves exactly as before (Blocker 1 in the
    # PRIOR review round -- flat-row shape, "uncovered" when there is nothing).
    uncovered = covenant_extraction_coverage([], [])
    assert uncovered["state"] == "uncovered"
    assert "reason" not in uncovered


def test_evaluate_health_reports_covenant_extraction_failed_without_a_nonzero_exit(tmp_path):
    """Full integration path a reviewer would actually run: a REAL failure
    marker file on disk (as main() would have written it), read back through
    evaluate_health() exactly as scripts/check_capital_structure_health.py
    calls it, with health_exit_code() proving the OTHER (real) gate stays
    unaffected by a covenant-producer crash."""
    marker_path = tmp_path / COVENANT_EXTRACTION_FAILURE_FILENAME
    marker_path.write_text(json.dumps({
        "state": "failed",
        "reason": "UnboundLocalError: cannot access local variable '_seq'",
        "failed_at": "2026-09-06T00:00:00Z",
    }))

    record = evaluate_health(tmp_path)

    assert record["covenant_extraction"]["state"] == "failed"
    assert "_seq" in record["covenant_extraction"]["reason"]
    # covenant_extraction is context-only (never a gate): an empty root with
    # no selected filings is a legitimate "no_new_work" verdict, not "fail".
    assert record["verdict"] != "fail"
    assert health_exit_code(record) == 0
