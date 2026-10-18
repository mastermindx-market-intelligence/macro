"""FIF A21 — filing observation state: vocabulary mapping, records, freshness.

The incumbent vocabularies are imported FROM THE SOURCE MODULES here on
purpose, so any future edit to Wave-2 ``OBSERVATION_OUTCOMES`` or FF-1
``REASON_CODES`` fails this suite until the mapping table is extended —
vocabulary drift must break closed, not silently pass an unmapped code.
"""
from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from collectors.fundamental_forensics_acquisition import OBSERVATION_OUTCOMES
from engine.fundamental_forensics import filing_observation_state as fos
from engine.fundamental_forensics.broad_sec_store import REASON_CODES
from engine.fundamental_forensics.filing_observation_state import (
    BROAD_SEC_REASON_STATE,
    FILING_OBSERVATION_SCHEMA,
    FRESHNESS,
    GENERATION_KINDS,
    OBSERVATION_STATES,
    SUCCESSFUL_CHECK_STATES,
    WAVE2_OUTCOME_MAP,
    classify_broad_sec_observation,
    classify_wave2_outcome,
    freshness,
    mark_published,
    observe,
)

MODULE_PATH = Path(fos.__file__)
CIK = "320193"
ACCESSION = "0000320193-25-000123"
T1 = "2026-08-01T12:00:00Z"
T2 = "2026-08-02T12:00:00Z"
T3 = "2026-08-03T12:00:00Z"


# ---------------------------------------------------------------- vocabulary


def test_wave2_vocabulary_is_mapped_total_and_exact():
    assert set(WAVE2_OUTCOME_MAP) == set(OBSERVATION_OUTCOMES)
    for outcome, state in WAVE2_OUTCOME_MAP.items():
        if state is not None:
            assert state in OBSERVATION_STATES
            assert classify_wave2_outcome(outcome) == state


def test_broad_sec_reason_vocabulary_is_mapped_total_and_exact():
    assert set(BROAD_SEC_REASON_STATE) == set(REASON_CODES)
    states_used = set(BROAD_SEC_REASON_STATE.values())
    assert states_used <= {"source_outage", "budget_exhausted", "check_failed"}
    for reason, state in BROAD_SEC_REASON_STATE.items():
        assert classify_broad_sec_observation("failed", reason_code=reason) == state


def test_observation_state_constants():
    assert OBSERVATION_STATES == (
        "new_filing",
        "new_content",
        "checked_no_change",
        "index_quiet",
        "source_outage",
        "absent_at_source",
        "budget_exhausted",
        "check_failed",
        "not_applicable",
    )
    assert SUCCESSFUL_CHECK_STATES == frozenset(
        {"new_filing", "new_content", "checked_no_change", "absent_at_source"}
    )
    assert "index_quiet" not in SUCCESSFUL_CHECK_STATES
    assert FRESHNESS == ("current", "stale", "never_checked")
    assert GENERATION_KINDS == ("disclosure_bundle", "source_snapshot", "issuer_manifest")
    assert FILING_OBSERVATION_SCHEMA == "fundamental_forensics.filing_observation_state/v1"


def test_missing_outcome_requires_a_known_cause():
    assert classify_wave2_outcome("missing", missing_cause="http_404") == "absent_at_source"
    assert classify_wave2_outcome("missing", missing_cause="byte_budget") == "budget_exhausted"
    assert classify_wave2_outcome("missing", missing_cause="transient_exhausted") == "source_outage"
    # The three late/out-of-source conditions are DISTINCT states.
    with pytest.raises(fos.FilingObservationError) as err:
        classify_wave2_outcome("missing")
    assert err.value.code == "missing_cause_required"
    with pytest.raises(fos.FilingObservationError) as err:
        classify_wave2_outcome("missing", missing_cause="whatever")
    assert err.value.code == "missing_cause_required"


def test_unknown_outcomes_and_reasons_refuse():
    with pytest.raises(fos.FilingObservationError) as err:
        classify_wave2_outcome("delayed")
    assert err.value.code == "unknown_outcome"
    with pytest.raises(fos.FilingObservationError) as err:
        classify_broad_sec_observation("postponed")
    assert err.value.code == "unknown_outcome"
    with pytest.raises(fos.FilingObservationError) as err:
        classify_broad_sec_observation("failed")
    assert err.value.code == "reason_code_required"
    with pytest.raises(fos.FilingObservationError) as err:
        classify_broad_sec_observation("failed", reason_code="not_a_code")
    assert err.value.code == "unknown_reason_code"


def test_broad_sec_observed_rules_follow_the_source():
    # Index quiet is NOT a byte-level check (broad_sec_store.py:3510-3517).
    assert classify_broad_sec_observation("observed_no_relevant_change") == "index_quiet"
    # Submissions fetched, SHA matched, prior manifest reused (3769-3782).
    assert (
        classify_broad_sec_observation("observed", submissions_unchanged=True, new_accessions=())
        == "checked_no_change"
    )
    # New accessions among the fetched Submissions.
    assert (
        classify_broad_sec_observation(
            "observed", submissions_unchanged=False, new_accessions=("0000320193-25-000124",)
        )
        == "new_filing"
    )
    # A fresh manifest was forced without new accessions: content changed.
    assert (
        classify_broad_sec_observation("observed", submissions_unchanged=False, new_accessions=[])
        == "new_content"
    )
    # Fail closed when the row carries neither kind of evidence.
    with pytest.raises(fos.FilingObservationError) as err:
        classify_broad_sec_observation("observed")
    assert err.value.code == "observation_evidence_required"


# ------------------------------------------------------------------- observe


def test_observe_builds_record_and_advances_only_on_successful_checks():
    record = observe(issuer_cik=CIK, accession=ACCESSION, state="new_filing", checked_at=T1)
    assert record["schema"] == FILING_OBSERVATION_SCHEMA
    assert record["record_id"].startswith("ffobs_") and len(record["record_id"]) == 38
    assert record["issuer_cik"] == "0000320193"  # 10-digit zero-padded canonical form
    assert record["accession"] == ACCESSION
    assert record["last_checked_at"] == T1
    assert record["last_successful_check_at"] == T1  # new_filing is a successful check
    assert record["publication"] is None

    # index_quiet NEVER refreshes the successful check.
    quiet = observe(
        issuer_cik=CIK, accession=ACCESSION, state="index_quiet", checked_at=T2, prior=record
    )
    assert quiet["last_checked_at"] == T2
    assert quiet["last_successful_check_at"] == T1

    # Neither do outage, budget or failure states.
    for state in ("source_outage", "budget_exhausted", "check_failed", "not_applicable"):
        row = observe(
            issuer_cik=CIK, accession=ACCESSION, state=state, checked_at=T3, prior=quiet
        )
        assert row["last_checked_at"] == T3
        assert row["last_successful_check_at"] == T1

    # A later successful check DOES advance it.
    ok = observe(
        issuer_cik=CIK, accession=ACCESSION, state="checked_no_change", checked_at="2026-08-04T12:00:00Z", prior=quiet
    )
    assert ok["last_successful_check_at"] == "2026-08-04T12:00:00Z"


def test_observe_cik_normalization_and_record_id_stability():
    padded = observe(issuer_cik="0000320193", accession=ACCESSION, state="index_quiet", checked_at=T1)
    assert padded["issuer_cik"] == "0000320193"
    assert observe(issuer_cik=320193, accession=ACCESSION, state="index_quiet", checked_at=T2)[
        "record_id"
    ] == padded["record_id"]
    # record_id is independent of every clock, state, prior and publication.
    later = observe(
        issuer_cik="0000320193", accession=ACCESSION, state="new_content", checked_at=T3, prior=padded
    )
    assert later["record_id"] == padded["record_id"]
    published = mark_published(
        later, generation_kind="issuer_manifest", generation_id="ffsecim_" + "a" * 64, published_at=T3
    )
    again = observe(
        issuer_cik="0000320193",
        accession=ACCESSION,
        state="checked_no_change",
        checked_at="2026-08-05T12:00:00Z",
        prior=published,
    )
    assert again["record_id"] == padded["record_id"]
    # Accession participates; a different filing is a different record.
    other = observe(issuer_cik="0000320193", accession="0000320193-25-000124", state="index_quiet", checked_at=T1)
    assert other["record_id"] != padded["record_id"]
    # Index-level rows (accession None) are their own record.
    index_row = observe(issuer_cik="0000320193", accession=None, state="index_quiet", checked_at=T1)
    assert index_row["record_id"] != padded["record_id"]
    with pytest.raises(fos.FilingObservationError) as err:
        observe(issuer_cik="12345678901", accession=None, state="index_quiet", checked_at=T1)
    assert err.value.code == "invalid_issuer_cik"


def test_observe_duplicate_delivery_is_idempotent():
    record = observe(issuer_cik=CIK, accession=ACCESSION, state="checked_no_change", checked_at=T1)
    duplicate = observe(
        issuer_cik=CIK, accession=ACCESSION, state="checked_no_change", checked_at=T1, prior=record
    )
    assert duplicate == record
    # A different timestamp form (+00:00) at the same instant is still the
    # same delivery.
    assert observe(
        issuer_cik=CIK,
        accession=ACCESSION,
        state="checked_no_change",
        checked_at="2026-08-01T12:00:00+00:00",
        prior=record,
    ) == record


def test_observe_refuses_regression_and_conflicts():
    record = observe(issuer_cik=CIK, accession=ACCESSION, state="checked_no_change", checked_at=T2)
    with pytest.raises(fos.FilingObservationError) as err:
        observe(issuer_cik=CIK, accession=ACCESSION, state="checked_no_change", checked_at=T1, prior=record)
    assert err.value.code == "clock_regression"
    with pytest.raises(fos.FilingObservationError) as err:
        observe(issuer_cik=CIK, accession=ACCESSION, state="source_outage", checked_at=T2, prior=record)
    assert err.value.code == "conflicting_duplicate"
    # Prior for a different record refuses to bind.
    stranger = observe(issuer_cik="0000000002", accession=ACCESSION, state="index_quiet", checked_at=T1)
    with pytest.raises(fos.FilingObservationError) as err:
        observe(issuer_cik=CIK, accession=ACCESSION, state="index_quiet", checked_at=T3, prior=stranger)
    assert err.value.code == "record_mismatch"


def test_observe_validates_state_and_timestamps():
    with pytest.raises(fos.FilingObservationError) as err:
        observe(issuer_cik=CIK, accession=ACCESSION, state="published", checked_at=T1)
    assert err.value.code == "unknown_state"
    for bad in ("2026-08-01 12:00:00Z", "2026-08-01T12:00:00", "2026-08-01T12:00:00+02:00", 12):
        with pytest.raises(fos.FilingObservationError) as err:
            observe(issuer_cik=CIK, accession=ACCESSION, state="index_quiet", checked_at=bad)
        assert err.value.code == "malformed_timestamp"


# ------------------------------------------------------------ mark_published


def test_mark_published_requires_successful_check_and_is_monotone():
    outage = observe(issuer_cik=CIK, accession=ACCESSION, state="source_outage", checked_at=T1)
    with pytest.raises(fos.FilingObservationError) as err:
        mark_published(
            outage, generation_kind="disclosure_bundle", generation_id="b1", published_at=T2
        )
    assert err.value.code == "publish_without_successful_check"

    ok = observe(issuer_cik=CIK, accession=ACCESSION, state="checked_no_change", checked_at=T1)
    first = mark_published(
        ok, generation_kind="disclosure_bundle", generation_id="b1", published_at=T2
    )
    assert first["publication"] == {
        "generation_kind": "disclosure_bundle",
        "generation_id": "b1",
        "published_at": T2,
    }
    # Identical republish is idempotent: equal record, byte for byte.
    assert (
        mark_published(first, generation_kind="disclosure_bundle", generation_id="b1", published_at=T2)
        == first
    )
    # An older publication cannot rewind a newer one.
    with pytest.raises(fos.FilingObservationError) as err:
        mark_published(first, generation_kind="disclosure_bundle", generation_id="b1", published_at=T1)
    assert err.value.code == "publication_regression"
    # A later publication advances.
    later = mark_published(
        first, generation_kind="source_snapshot", generation_id="s1", published_at=T3
    )
    assert later["publication"]["generation_id"] == "s1"
    with pytest.raises(fos.FilingObservationError) as err:
        mark_published(ok, generation_kind="website", generation_id="b1", published_at=T2)
    assert err.value.code == "unknown_generation_kind"
    with pytest.raises(fos.FilingObservationError) as err:
        mark_published(ok, generation_kind="disclosure_bundle", generation_id="  ", published_at=T2)
    assert err.value.code == "invalid_generation_id"


# ----------------------------------------------------------------- freshness


def test_freshness_classifies_around_the_sla_boundary():
    ok = observe(issuer_cik=CIK, accession=ACCESSION, state="checked_no_change", checked_at=T1)
    sla = fos.FRESHNESS_BUDGET_SECONDS
    exactly_sla = "2026-08-05T12:00:00Z"  # T1 + 4 days
    assert freshness(ok, as_of=exactly_sla) == "current"  # not yet > SLA
    assert freshness(ok, as_of="2026-08-05T12:00:01Z") == "stale"
    assert freshness(ok, as_of=T1, sla_seconds=60) == "current"
    assert freshness(ok, as_of="2026-08-01T12:01:00Z", sla_seconds=60) == "current"
    assert freshness(ok, as_of="2026-08-01T12:01:01Z", sla_seconds=60) == "stale"
    # No successful check can never be "fresh".
    outage = observe(issuer_cik=CIK, accession=ACCESSION, state="source_outage", checked_at=T2)
    assert freshness(outage, as_of=T2) == "never_checked"
    quiet = observe(issuer_cik=CIK, accession=None, state="index_quiet", checked_at=T2)
    assert freshness(quiet, as_of=T2) == "never_checked"
    # as_of before the successful check is a clock-order violation, not fresh.
    with pytest.raises(fos.FilingObservationError) as err:
        freshness(ok, as_of="2026-07-31T12:00:00Z")
    assert err.value.code == "clock_order_violation"
    with pytest.raises(fos.FilingObservationError) as err:
        freshness(ok, as_of="not-a-time")
    assert err.value.code == "malformed_timestamp"


# ------------------------------------------------------------------ purity


def test_no_function_mutates_its_input():
    ok = observe(issuer_cik=CIK, accession=ACCESSION, state="checked_no_change", checked_at=T1)
    snapshot = copy.deepcopy(ok)
    observe(issuer_cik=CIK, accession=ACCESSION, state="source_outage", checked_at=T2, prior=ok)
    observe(issuer_cik=CIK, accession=ACCESSION, state="checked_no_change", checked_at=T2, prior=ok)
    mark_published(ok, generation_kind="issuer_manifest", generation_id="m1", published_at=T2)
    freshness(ok, as_of=T2)
    classify_wave2_outcome("missing", missing_cause="http_404")
    classify_broad_sec_observation("failed", reason_code="sec_429_exhausted")
    assert ok == snapshot


# ------------------------------------------------------- module hygiene (AST)


def test_module_reads_no_clock_and_imports_no_collectors_or_scripts():
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_calls = {"now", "utcnow", "time", "today"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in forbidden_calls:
                raise AssertionError(f"clock read in module: {ast.dump(func)}")
            if isinstance(func, ast.Name) and func.id in forbidden_calls:
                raise AssertionError(f"clock read in module: {func.id}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(("collectors", "scripts")), alias.name
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith(("collectors", "scripts")), node.module
    # The health import is the one permitted engine dependency (SLA constant).
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "from engine.fundamental_forensics.health import FRESHNESS_BUDGET_SECONDS" in source
