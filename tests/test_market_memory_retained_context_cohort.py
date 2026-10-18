"""Real trusted owner corpus fixtures and hostile cohort qualification cases."""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_identity as identity
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_projection as projection
from engine.neuralweb import market_memory_trusted as trusted
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from tests.test_market_memory_trusted import _raw_regime, DEPLOYED_COMMIT
from tests.test_market_memory_episode_features import Policy

CUTOFF = "2026-08-20T12:00:00Z"


def capture(tmp_path, monkeypatch, *, session="2026-08-10", growth=0.133,
            seconds=0, liquidity="contracting", cycle="late"):
    built = datetime.combine(date.fromisoformat(session), datetime.min.time(),
                             tzinfo=timezone.utc) + timedelta(hours=10, seconds=seconds)
    raw = _raw_regime(growth_score=growth)
    raw.update({"date": session, "asof": session, "liquidity_overlay": liquidity, "cycle_tag": cycle})
    raw["freshness"].update({"asof": session, "built_at": built.isoformat().replace("+00:00", "Z")})
    body = (json.dumps(raw, sort_keys=True) + "\n").encode()
    source = tmp_path / "fixture-house-output.json"
    source.write_bytes(body)
    monkeypatch.setattr(projection, "_utc_now", lambda: built + timedelta(seconds=1))
    snapshot = projection.build_macro_regime_snapshot(source)
    monkeypatch.setattr(identity, "_utc_now", lambda: built + timedelta(seconds=2))
    evidence = identity.build_current_spy_identity()
    monkeypatch.setattr(trusted, "_utc_now", lambda: built + timedelta(seconds=3))
    return trusted.capture_trusted_regime_context(
        tmp_path / "public" / "trusted-v1", tmp_path / "private",
        snapshot=snapshot, identity_evidence=evidence,
        raw_source_body=body, deployed_commit=DEPLOYED_COMMIT,
    )


def owner(tmp_path):
    reader = trusted.TrustedFileAsKnownAtReader(tmp_path / "public" / "trusted-v1")
    return reader, reader.read_pinned_generation()


def load(reader, pin, stored, *, cutoff=CUTOFF, policy=None):
    return cohort.read_retained_context_cohort(
        reader, pin, subject_id=stored.packet["subject"]["subject_id"],
        query_cutoff=cutoff, policy=Policy() if policy is None else policy,
    )


def test_complete_pinned_generation_with_revisions_and_future(tmp_path, monkeypatch):
    first = capture(tmp_path, monkeypatch)
    later = capture(tmp_path, monkeypatch, growth=0.5, seconds=60)
    future = capture(tmp_path, monkeypatch, session="2026-08-21")
    reader, pin = owner(tmp_path)
    capability = load(reader, pin, first)
    value = cohort.disclose_retained_context_cohort(capability, policy=Policy())
    assert value["expected_capture_count"] == 3
    assert sum(value["counts"].values()) == 3
    rows = {row["context_id"]: row for row in value["rows"]}
    assert rows[first.packet["context_id"]]["status"] == "representative"
    assert rows[later.packet["context_id"]]["status"] == "revision_sibling"
    assert rows[future.packet["context_id"]]["status"] == "future_capture"
    assert value["scheduled_opportunity_coverage"] == "unknown"
    assert not value["fit_eligible"] and not value["component_source_receipts_authenticated"]
    assert value["owner"]["generation_id"] == pin.generation_id


def test_earliest_unknown_revision_is_fixed_before_quality_filter(tmp_path, monkeypatch):
    first = capture(tmp_path, monkeypatch, liquidity="unknown")
    later = capture(tmp_path, monkeypatch, growth=0.5, seconds=60)
    reader, pin = owner(tmp_path)
    value = cohort.disclose_retained_context_cohort(load(reader, pin, first), policy=Policy())
    rows = {row["context_id"]: row for row in value["rows"]}
    assert rows[first.packet["context_id"]]["status"] == "representative_coordinates_unavailable"
    assert rows[later.packet["context_id"]]["status"] == "revision_sibling"


def test_later_generation_additions_leave_old_pinned_membership_unchanged(tmp_path, monkeypatch):
    first = capture(tmp_path, monkeypatch)
    reader, original = owner(tmp_path)
    before = cohort.disclose_retained_context_cohort(load(reader, original, first), policy=Policy())
    capture(tmp_path, monkeypatch, session="2026-08-11", growth=0.5)
    after = cohort.disclose_retained_context_cohort(load(reader, original, first), policy=Policy())
    assert before == after
    assert before["expected_capture_count"] == 1


@pytest.mark.parametrize("action", ["read_retained_macro_cohort", "verify_retained_macro_retention",
                                     "use_retained_house_output_cohort_for_contextual_comparison"])
def test_named_rights_before_owner_read(tmp_path, monkeypatch, action):
    first = capture(tmp_path, monkeypatch)
    reader, pin = owner(tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("private owner read before rights")
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_projections", forbidden)
    with pytest.raises(cohort.RetainedContextAccessError):
        load(reader, pin, first, policy=Policy({action}))


def test_disclosure_revocation_and_raw_json_never_authorize(tmp_path, monkeypatch):
    first = capture(tmp_path, monkeypatch)
    reader, pin = owner(tmp_path)
    capability = load(reader, pin, first)
    raw = cohort.disclose_retained_context_cohort(capability, policy=Policy())
    with pytest.raises(cohort.RetainedContextCohortError, match="capability_required"):
        cohort.disclose_retained_context_cohort(raw, policy=Policy())
    with pytest.raises(cohort.RetainedContextCohortError, match="capability_required"):
        cohort.RetainedContextCohortCapability(b"{}", b"{}", ())
    raw["rows"].clear()
    assert cohort.disclose_retained_context_cohort(capability, policy=Policy())["rows"]
    with pytest.raises(cohort.RetainedContextAccessError):
        cohort.disclose_retained_context_cohort(capability, policy=Policy({"disclose_retained_macro_cohort"}))


def test_forged_exact_pin_and_oversized_whole_cohort_refused(tmp_path, monkeypatch):
    first = capture(tmp_path, monkeypatch)
    reader, pin = owner(tmp_path)
    with pytest.raises(cohort.RetainedContextCohortError):
        load(reader, replace(pin, generation_sha256="f" * 64), first)
    monkeypatch.setattr(cohort, "MAX_CAPTURES", 0)
    with pytest.raises(cohort.RetainedContextCohortError, match="whole_generation"):
        load(reader, pin, first)


def test_corrupt_original_bytes_and_aggregate_bound_refused(tmp_path, monkeypatch):
    first = capture(tmp_path, monkeypatch)
    reader, pin = owner(tmp_path)
    monkeypatch.setattr(cohort, "MAX_OWNER_BYTES", 1)
    with pytest.raises(cohort.RetainedContextCohortError, match="aggregate_owner"):
        load(reader, pin, first)
    monkeypatch.setattr(cohort, "MAX_OWNER_BYTES", 64 * 1024 * 1024)
    receipt_path = next(reader.root.rglob(first.capture_receipt["query_id"] + ".json"))
    raw = json.loads(receipt_path.read_bytes())
    raw["packet_sha256"] = "f" * 64
    receipt_path.write_text(json.dumps(raw))
    with pytest.raises(cohort.RetainedContextCohortError):
        load(reader, pin, first)


@pytest.mark.parametrize("clock", [True, False, float("nan"), "not-utc", "2026-08-33T00:00:00Z"])
def test_nonfinite_bool_invalid_clock_refused(clock):
    with pytest.raises(cohort.RetainedContextCohortError):
        cohort.utc_instant(clock)


def test_other_subject_remains_in_complete_denominator(tmp_path, monkeypatch):
    first = capture(tmp_path, monkeypatch)
    reader, pin = owner(tmp_path)
    value = cohort.disclose_retained_context_cohort(cohort.read_retained_context_cohort(
        reader, pin, subject_id="mmsecurity_" + "f" * 64,
        query_cutoff=CUTOFF, policy=Policy()), policy=Policy())
    assert value["expected_capture_count"] == 1
    assert value["counts"] == {"other_subject": 1}



def test_aggregate_bound_is_checked_before_packet_projection_reads(tmp_path, monkeypatch):
    first = capture(tmp_path, monkeypatch)
    reader, pin = owner(tmp_path)
    monkeypatch.setattr(cohort, "MAX_OWNER_BYTES", 1)
    def forbidden(*args, **kwargs):
        pytest.fail("oversized whole cohort payload was read")
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_projections", forbidden)
    with pytest.raises(cohort.RetainedContextCohortError, match="aggregate_owner"):
        load(reader, pin, first)


def test_requested_subject_permission_never_authorizes_other_subject_payload(tmp_path, monkeypatch):
    first = capture(tmp_path, monkeypatch)
    reader, pin = owner(tmp_path)
    requested = "mmsecurity_" + "f" * 64
    actual = first.packet["subject"]["subject_id"]
    class RequestedSubjectOnly(Policy):
        def check(self, action, resource):
            if resource.get("subject_id") == actual:
                raise PermissionError("actual source subject not authorized")
            return super().check(action, resource)
    def forbidden(*args, **kwargs):
        pytest.fail("other-subject payload read before actual-subject authorization")
    monkeypatch.setattr(reader, "read_pinned_capture_projections", forbidden)
    with pytest.raises(cohort.RetainedContextAccessError):
        cohort.read_retained_context_cohort(reader, pin, subject_id=requested,
            query_cutoff=CUTOFF, policy=RequestedSubjectOnly())


def test_metadata_permission_precedes_private_receipt_read(tmp_path, monkeypatch):
    first = capture(tmp_path, monkeypatch)
    reader, pin = owner(tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("private receipt read before exact-capture metadata permission")
    monkeypatch.setattr(reader, "read_pinned_capture_receipt", forbidden)
    with pytest.raises(cohort.RetainedContextAccessError):
        load(reader, pin, first, policy=Policy({"read_retained_macro_capture_metadata"}))


def test_cached_other_subject_disclosure_rechecks_actual_subject(tmp_path, monkeypatch):
    first = capture(tmp_path, monkeypatch)
    reader, pin = owner(tmp_path)
    requested = "mmsecurity_" + "f" * 64
    actual = first.packet["subject"]["subject_id"]
    capability = cohort.read_retained_context_cohort(reader, pin, subject_id=requested,
        query_cutoff=CUTOFF, policy=Policy())
    class RevokedActualSubject(Policy):
        def check(self, action, resource):
            if resource.get("subject_id") == actual:
                assert resource["requested_subject_id"] == requested
                raise PermissionError("actual-subject rights revoked")
            return super().check(action, resource)
    with pytest.raises(cohort.RetainedContextAccessError):
        cohort.disclose_retained_context_cohort(capability, policy=RevokedActualSubject())


def test_per_capture_disclosure_is_separate_from_cohort_and_comparison(tmp_path, monkeypatch):
    first = capture(tmp_path, monkeypatch)
    reader, pin = owner(tmp_path)
    capability = load(reader, pin, first)
    with pytest.raises(cohort.RetainedContextAccessError):
        cohort.disclose_retained_context_cohort(capability,
            policy=Policy({"disclose_retained_macro_capture"}))


@pytest.mark.parametrize("cached", [False, True])
def test_exact_source_receipt_rights_precede_payload_and_cached_disclosure(tmp_path, monkeypatch, cached):
    first = capture(tmp_path, monkeypatch)
    reader, pin = owner(tmp_path)
    source = first.capture_receipt["source_receipt_ids"][0]
    capability = load(reader, pin, first) if cached else None
    class RestrictedSource(Policy):
        def check(self, action, resource):
            if source in resource.get("source_receipt_ids", []):
                raise PermissionError("source receipt usage revoked")
            return super().check(action, resource)
    def forbidden(*args, **kwargs):
        pytest.fail("restricted-source payload read")
    monkeypatch.setattr(reader, "read_pinned_capture_projections", forbidden)
    with pytest.raises(cohort.RetainedContextAccessError):
        if cached:
            cohort.disclose_retained_context_cohort(capability, policy=RestrictedSource())
        else:
            load(reader, pin, first, policy=RestrictedSource())
