"""Real trusted-writer fixtures driving the saved-output wrapper end to end.

All captures below are synthetic local fixtures honestly produced by the real
trusted writer/reader over a temporary store (tests.test_market_memory_retained_context_cohort);
they are not production records.  The wrapper must disclose the unchanged
original packet and receipt plus the authorized five-field feature projection, and must refuse
bootstrap, revocation, identity, bound, and tamper failures without any
recomputation from the current regime.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.neuralweb import market_memory as mm
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_projection as projection
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_retained_saved as saved
from engine.neuralweb import market_memory_retained_use as use
from engine.neuralweb import market_memory_trusted as trusted
from tests.test_market_memory_retained_context_cohort import capture, owner, CUTOFF

ROOT = Path(__file__).resolve().parents[1]


class Env:
    def __init__(self, root, reader, pin, captures):
        self.root, self.reader, self.pin = root, reader, pin
        self.old, self.query, self.future = captures
        self.subject = self.query.packet["subject"]["subject_id"]
        self.spec = {
            "user_id": "member",
            "generation_id": pin.generation_id,
            "generation_sha256": pin.generation_sha256,
            "query_id": self.query.capture_receipt["query_id"],
            "context_id": self.query.packet["context_id"],
            "capture_id": self.query.capture_receipt["capture_id"],
            "subject_id": self.subject,
            "query_cutoff": CUTOFF,
        }


def _registration_path(root: Path) -> Path:
    return root / use.REGISTRATION


def _rewrite_registration(root: Path, change) -> None:
    path = _registration_path(root)
    value = json.loads(path.read_text())
    change(value)
    path.write_text(json.dumps(value))


@pytest.fixture
def env(tmp_path, monkeypatch):
    old = capture(tmp_path, monkeypatch, session="2026-08-01", growth=0.1)
    query = capture(tmp_path, monkeypatch, session="2026-08-13", growth=0.2)
    future = capture(tmp_path, monkeypatch, session="2026-08-21", growth=0.2)
    reader, pin = owner(tmp_path)
    for rel in (use.REGISTRATION, use.AUTHORITY_RECORD):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / rel).read_bytes())
    _rewrite_registration(tmp_path, lambda value: value.update(store_id=pin.store_id))
    monkeypatch.setenv("MARKET_MEMORY_TRUSTED_STORE_DIR", str(reader.root))
    monkeypatch.setattr(use, "_enforce_current_site_user",
                        lambda uid: None if uid == "member"
                        else (_ for _ in ()).throw(use.RetainedUseError("current_site_entitlement_required")))
    return Env(tmp_path, reader, pin, (old, query, future))


def read_saved(env, **changes):
    return saved.read_retained_saved(env.root, **{**env.spec, **changes})


def forbid_recomputation(monkeypatch):
    monkeypatch.setattr(projection, "build_macro_regime_snapshot",
                        lambda *a, **k: pytest.fail("recomputed regime projection"))
    monkeypatch.setattr(trusted, "build_trusted_packet",
                        lambda *a, **k: pytest.fail("recomputed trusted packet"))
    monkeypatch.setattr(trusted, "capture_trusted_regime_context",
                        lambda *a, **k: pytest.fail("recomputed capture"))
    if hasattr(mm, "macro_context"):
        monkeypatch.setattr(mm, "macro_context",
                            lambda *a, **k: pytest.fail("recomputed fallback"))


def test_saved_output_is_unchanged_original_with_real_five_field_state(env, monkeypatch):
    forbid_recomputation(monkeypatch)
    capability = read_saved(env)
    assert isinstance(capability, saved.SavedOutputCapability)
    # No server-user identity and no raw/private evidence in the sealed body.
    assert b"member" not in capability.request + capability.owner
    assert b"raw_source" not in capability.request + capability.owner
    value = saved.disclose_retained_saved(capability)
    assert value["schema"] == saved.SCHEMA
    assert value["mode"] == "retained_actual_output"
    assert value["status"] == "AVAILABLE"
    assert value["context"] == env.query.packet
    assert value["capture_receipt"] == env.query.capture_receipt
    feature = env.reader.read_macro_feature_from_pinned_generation(
        env.pin, query_id=env.spec["query_id"])
    assert value["feature_projection"]["state"] == {key:feature["state"][key] for key in use.FIELDS}
    assert value["feature_projection"]["original_feature_ref"] == env.query.capture_receipt["feature_snapshot"]
    assert value["feature_projection"]["schema"] == "market_memory.saved_house_feature_projection.v1"
    assert "feature_snapshot" not in value
    assert len(value["source_facts"]) == 5
    assert {fact["field"] for fact in value["source_facts"]} == set(use.FIELDS)
    for fact in value["source_facts"]:
        assert fact["value"] == feature["state"][fact["field"]]
        assert fact["citation"]["source_sha256"] == env.query.capture_receipt["feature_snapshot"]["content_sha256"]
        assert fact["citation"]["source_bytes"] == env.query.capture_receipt["feature_snapshot"]["content_bytes"]
    assert set(value["feature_projection"]) == {"schema", "as_of", "transform_version", "source_artifact", "state", "original_feature_ref"}
    state = value["feature_projection"]["state"]
    assert {name: state[name] for name in use.FIELDS} == {
        "growth_score": 0.2, "inflation_score": 0.4, "quad": "Q2",
        "liquidity_overlay": "contracting", "cycle_tag": "late"}
    receipt = env.query.capture_receipt
    assert value["exact_refs"] == {
        "packet": {"sha256": receipt["packet_sha256"], "bytes": receipt["packet_bytes"]},
        "feature": {"snapshot_id": receipt["feature_snapshot"]["snapshot_id"],
                    "sha256": receipt["feature_snapshot"]["content_sha256"],
                    "bytes": receipt["feature_snapshot"]["content_bytes"]},
        "source": {"raw_sha256": receipt["source_evidence"]["raw_source_sha256"],
                   "raw_bytes": receipt["source_evidence"]["raw_source_bytes"]}}
    clocks = value["clocks"]
    assert clocks["captured_at"] == receipt["captured_at"]
    assert clocks["raw_source_built_at"] == receipt["source_evidence"]["raw_source_built_at"]
    assert clocks["raw_source_observed_at"] == receipt["source_evidence"]["raw_source_observed_at"]
    assert clocks["feature_as_of"] == feature["as_of"]
    for key in ("event_time", "as_known_at", "knowledge_cutoff"):
        assert clocks[key] == receipt["clocks"][key]
    earliest = max(clocks.values(), key=cohort.utc_instant)
    assert value["earliest_supported_cutoff"] == earliest
    assert cohort.utc_instant(earliest) <= cohort.utc_instant(CUTOFF)
    assert value["selection"] == {
        "query_id": env.spec["query_id"], "context_id": env.spec["context_id"],
        "capture_id": env.spec["capture_id"], "subject_id": env.subject,
        "instrument_id": env.query.packet["subject"]["instrument_id"],
        "query_cutoff": CUTOFF}
    assert value["generation"] == {
        "store_id": env.pin.store_id, "generation_id": env.pin.generation_id,
        "generation_sha256": env.pin.generation_sha256,
        "profile": trusted.TRUSTED_STORE_PROFILE}
    # The named policy mode is only the authorization scope; the saved evidence
    # mode is separate and no outcome is attached.
    assert value["source_use"]["mode"] == "current_contextual_support"
    assert value["source_use"]["status"] == "ADMITTED_FOR_NAMED_PURPOSES"
    assert value["mode"] != value["source_use"]["mode"]
    assert value["outcomes"] == {"status": "NOT_ATTACHED"}
    assert value["evidence_policy"] == receipt["evidence_policy"]
    assert len(cohort.canonical(value)) <= saved.MAX_ENVELOPE_BYTES
    assert not any("user_id" in key or "token" in key for key in value)


@pytest.mark.parametrize("changes", [
    {"subject_id": "mmsecurity_" + "f" * 64},
    {"generation_sha256": "f" * 63},
    {"query_id": "mmquery_Z" + "f" * 63},
    {"context_id": "f" * 64},
    {"capture_id": "mmcapture_Z" + "f" * 63},
    {"query_cutoff": "2026-08-20"},
    {"query_cutoff": True},
    {"query_cutoff": "2026-08-33T00:00:00Z"},
])
def test_bad_request_inputs_are_refused_before_any_owner_byte(env, monkeypatch, changes):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid request constructed a trusted reader")
    monkeypatch.setattr(trusted, "TrustedFileAsKnownAtReader", forbidden)
    with pytest.raises((pit.MarketMemoryQueryError, use.RetainedUseError,
                        pit.MarketMemoryContextNotFound)):
        read_saved(env, **changes)


def test_unauthenticated_site_user_is_refused_before_owner(env, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("unauthenticated request constructed a trusted reader")
    monkeypatch.setattr(trusted, "TrustedFileAsKnownAtReader", forbidden)
    with pytest.raises(use.RetainedUseError):
        read_saved(env, user_id="admin")
    with pytest.raises(use.RetainedUseError):
        read_saved(env, user_id="")


def test_disabled_source_record_is_refused_before_owner(env, monkeypatch):
    _rewrite_registration(env.root, lambda value: value.update(enabled=False))
    def forbidden(*args, **kwargs):
        pytest.fail("disabled source record still constructed a trusted reader")
    monkeypatch.setattr(trusted, "TrustedFileAsKnownAtReader", forbidden)
    with pytest.raises(use.RetainedUseError):
        read_saved(env)


def test_registered_store_mismatch_is_refused_before_full_pin(env, monkeypatch):
    _rewrite_registration(env.root,
                          lambda value: value.update(store_id="mmstore_" + "e" * 64))
    def forbidden(*args, **kwargs):
        pytest.fail("wrong store walked the full generation ancestry")
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_generation",
                        forbidden)
    with pytest.raises(pit.MarketMemoryStoreError):
        read_saved(env)


def test_second_registered_subject_is_refused(env):
    _rewrite_registration(env.root, lambda value: value["allowed_subject_ids"].append(
        "mmsecurity_" + "e" * 64))
    with pytest.raises(use.RetainedUseError):
        read_saved(env)


def test_exact_generation_query_context_capture_mismatch_is_not_found(env):
    with pytest.raises(pit.MarketMemoryContextNotFound):
        read_saved(env, generation_sha256="f" * 64)
    with pytest.raises(pit.MarketMemoryContextNotFound):
        read_saved(env, query_id="mmquery_" + "f" * 64)
    with pytest.raises(pit.MarketMemoryContextNotFound):
        read_saved(env, context_id=env.future.packet["context_id"])
    with pytest.raises(pit.MarketMemoryContextNotFound):
        read_saved(env, capture_id=env.future.capture_receipt["capture_id"])
    # The later capture is still exactly selectable when the cutoff supports it:
    # selection is exact, never latest/nearest.
    later = saved.disclose_retained_saved(read_saved(
        env, query_cutoff="2026-08-22T00:00:00Z",
        query_id=env.future.capture_receipt["query_id"],
        context_id=env.future.packet["context_id"],
        capture_id=env.future.capture_receipt["capture_id"]))
    assert later["selection"]["capture_id"] == env.future.capture_receipt["capture_id"]
    assert later["context"] == env.future.packet


def test_query_cutoff_before_actual_clocks_is_a_pit_query_error(env):
    with pytest.raises(pit.MarketMemoryQueryError):
        read_saved(env, query_cutoff="2026-08-13T09:00:00Z")
    value = saved.disclose_retained_saved(read_saved(env))
    assert cohort.utc_instant(value["earliest_supported_cutoff"]) <= cohort.utc_instant(CUTOFF)


def test_all_source_revocation_blocks_projection_and_held_disclosure(env, monkeypatch):
    receipt = env.query.capture_receipt
    _rewrite_registration(env.root, lambda value: value.update(
        revoked_source_receipt_ids=list(receipt["source_receipt_ids"])))
    def forbidden(*args, **kwargs):
        pytest.fail("revoked-source payload was projected")
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader,
                        "read_pinned_capture_projections", forbidden)
    with pytest.raises(PermissionError):
        read_saved(env)


def test_capture_revocation_blocks_before_projection(env, monkeypatch):
    _rewrite_registration(env.root, lambda value: value.update(
        revoked_capture_ids=[env.spec["capture_id"]]))
    def forbidden(*args, **kwargs):
        pytest.fail("revoked capture payload was projected")
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader,
                        "read_pinned_capture_projections", forbidden)
    with pytest.raises(PermissionError):
        read_saved(env)


def test_held_capability_denies_after_registration_change(env, monkeypatch):
    capability = read_saved(env)
    _rewrite_registration(env.root, lambda value: value.update(enabled=False))
    with pytest.raises(PermissionError):
        saved.disclose_retained_saved(capability)
    _rewrite_registration(env.root, lambda value: value.update(enabled=True))
    capability = read_saved(env)
    _rewrite_registration(env.root, lambda value: value.update(
        revoked_source_receipt_ids=list(env.query.capture_receipt["source_receipt_ids"])))
    with pytest.raises(PermissionError):
        saved.disclose_retained_saved(capability)


def test_held_capability_denies_after_entitlement_change(env, monkeypatch):
    capability = read_saved(env)
    monkeypatch.setattr(use, "_enforce_current_site_user",
                        lambda uid: (_ for _ in ()).throw(
                            use.RetainedUseError("current_site_entitlement_required")))
    with pytest.raises(PermissionError):
        saved.disclose_retained_saved(capability)


def test_forged_or_foreign_capability_is_refused(env):
    capability = read_saved(env)
    value = saved.disclose_retained_saved(capability)
    with pytest.raises(saved.RetainedSavedOutputError):
        saved.disclose_retained_saved({})
    with pytest.raises(saved.RetainedSavedOutputError):
        saved.disclose_retained_saved(value)
    with pytest.raises(saved.RetainedSavedOutputError):
        saved.SavedOutputCapability(b"{}", b"{}", (), "0" * 64, object(), object(), ())
    with pytest.raises(saved.RetainedSavedOutputError):
        saved.SavedOutputCapability(capability.request, capability.owner,
                                    capability.resources, "0" * 64,
                                    capability.grant, capability.reader,
                                    capability.originals)


def test_owner_read_budget_and_envelope_bound_refuse_without_truncation(env, monkeypatch):
    with pit.bounded_owner_reads(maximum_bytes=10):
        with pytest.raises(pit.OwnerReadBudgetError):
            read_saved(env)
    capability = read_saved(env)
    value = saved.disclose_retained_saved(capability)
    size = len(cohort.canonical(value))
    assert size < saved.MAX_ENVELOPE_BYTES
    monkeypatch.setattr(saved, "MAX_ENVELOPE_BYTES", size - 1)
    with pytest.raises(pit.MarketMemoryStoreError):
        saved.disclose_retained_saved(read_saved(env))


def test_mutated_envelope_cannot_affect_future_disclosure(env, monkeypatch):
    forbid_recomputation(monkeypatch)
    capability = read_saved(env)
    first = saved.disclose_retained_saved(capability)
    first["context"]["clocks"]["event_time"] = "1999-01-01T00:00:00Z"
    first["exact_refs"]["packet"]["sha256"] = "f" * 64
    first["feature_projection"]["state"]["growth_score"] = 9.9
    second = saved.disclose_retained_saved(capability)
    assert second == saved.disclose_retained_saved(capability)
    assert second["context"] == env.query.packet
    assert second["exact_refs"]["packet"]["sha256"] == env.query.capture_receipt["packet_sha256"]
    assert second["feature_projection"]["state"]["growth_score"] == 0.2


def test_store_side_rewrite_after_read_is_caught_at_disclosure(env):
    capability = read_saved(env)
    digest = env.query.capture_receipt["packet_sha256"]
    packet_path = env.reader.root / "objects" / digest[:2] / f"{digest}.json"
    body = packet_path.read_bytes()
    packet_path.write_bytes(body[:-1] + b"x")
    with pytest.raises(pit.MarketMemoryStoreError):
        saved.disclose_retained_saved(capability)


def test_saved_read_is_idempotent_and_detached(env):
    first = saved.disclose_retained_saved(read_saved(env))
    second = saved.disclose_retained_saved(read_saved(env))
    assert first == second
    first["selection"]["subject_id"] = "mmsecurity_" + "f" * 64
    assert saved.disclose_retained_saved(read_saved(env))["selection"]["subject_id"] == env.subject


def test_final_disclosure_rechecks_source_revocation_after_owner_io(env, monkeypatch):
    cap = read_saved(env)
    original = trusted.TrustedFileAsKnownAtReader.read_pinned_capture_projections
    def revoke_after_projection(reader, *args, **kwargs):
        result = original(reader, *args, **kwargs)
        _rewrite_registration(env.root, lambda value: value.update(
            revoked_source_receipt_ids=list(env.query.capture_receipt['source_receipt_ids'])))
        return result
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, 'read_pinned_capture_projections', revoke_after_projection)
    with pytest.raises(use.RetainedUseError):
        saved.disclose_retained_saved(cap)


def test_capability_binds_mutable_resource_and_original_bytes_before_reads(env, monkeypatch):
    for target in ('resources', 'originals', 'grant'):
        cap = read_saved(env)
        if target == 'resources':
            cap.resources[0]['source_receipt_ids'] = []
        elif target == 'originals':
            cap.originals[1]['context_id'] = 'mmctx_' + '0' * 64
        else:
            cap.grant.user_id = 'another_member'
        with monkeypatch.context() as patch:
            patch.setattr(trusted.TrustedFileAsKnownAtReader, 'read_pinned_generation',
                          lambda *a, **k: pytest.fail('forged capability reached owner I/O'))
            with pytest.raises(saved.RetainedSavedOutputError):
                saved.disclose_retained_saved(cap)


def test_capability_constructor_is_owner_only(env):
    cap = read_saved(env)
    fields = {key: value for key, value in cap.__dict__.items() if key != '_token'}
    with pytest.raises(saved.RetainedSavedOutputError):
        saved.SavedOutputCapability(**fields)
