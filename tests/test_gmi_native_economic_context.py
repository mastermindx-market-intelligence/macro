"""Native-reader composition tests; synthetic authority never admits real data."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest

from engine.company_intelligence import issuer_disclosures as native
from engine.theme_graph import economic_context as context
from tests.test_company_issuer_disclosures import sample, publish


@pytest.fixture
def ready(sample):
    sample[-2].admission = replace(sample[-2].admission, allowed_fields=context.REQUIRED_FIELDS)
    publish(sample)
    sample[-2].calls = 0
    sample[-1].reads = 0
    return sample


def read(value, **overrides):
    return context.read_economic_context(overrides.get("store", value[-1]),
        overrides.get("authority", value[-2]), overrides.get("request", value[3]),
        expected_admission=overrides.get("expected_admission"))


def assert_refusal(result, code=None):
    assert result == {"schema": context.SCHEMA, "status": "unavailable",
        "reason": result["reason"] if code is None else code,
        "context": None, "authority": "context_only"}
    assert "reference" not in json.dumps(result) and "generation" not in json.dumps(result)


def test_real_reader_projection_preserves_native_grain_without_writes(ready):
    body, edition, fact, request, authority, store = ready
    saved = deepcopy(store.objects); writes = store.writes
    result = read(ready)
    assert result["status"] == "available" and result["authority"] == "context_only"
    c = result["context"]
    assert c["relationship"] == {k: fact[k] for k in (
        "kind", "lifecycle", "subject_id", "object_id", "product", "platform", "amount", "economic_share")}
    assert c["provenance"] == {"fact_id": fact["fact_id"], "revision": 1,
        "reference": authority.admission.reference.payload(), "edition": authority.admission.edition.payload(),
        "generation": authority.admission.generation}
    assert store.objects == saved and store.writes == writes
    assert authority.calls == 3  # composing preflight + reader preflight and post-read recheck
    assert body.decode() not in json.dumps(result)
    assert "span" not in json.dumps(result) and "review_revision" not in json.dumps(result)


def test_no_implicit_supplier_edge_hypothesis_forecast_or_magnitude(ready):
    c = read(ready)["context"]
    assert c["mapping"] == {"state": "native_fact_context_only", "legacy_theme_graph_edge": None,
        "propagation_hypothesis": None, "reason": "PLANNED_INTEGRATION_MAPPING_NOT_ADOPTED"}
    assert all(v is False for v in c["limitations"].values())
    assert c["limitations"]["current_plan_established"] is False
    assert c["relationship"]["amount"] is None and c["relationship"]["economic_share"] is None
    assert c["relationship"]["lifecycle"] == "planned"
    assert "supplier" not in c["relationship"] and "confidence" not in c


def test_no_fact_clock_replaced_by_publication_or_generation(ready):
    result = read(ready)["context"]["timing"]
    assert result == {"source_published_date": "2026-01-02", "source_published_at": None,
        "publication_precision": "date", "edition_known_at": "2026-01-03T10:00:00Z",
        "fact_known_at": "2026-01-03T10:01:00Z", "identity_mode": "current",
        "query_mode": "current", "query_as_of": None}
    ready[-2].admission = replace(ready[-2].admission, generation="later-generation")
    assert read(ready)["context"]["timing"] == result


@pytest.mark.parametrize("field", sorted(context.REQUIRED_FIELDS))
def test_all_needed_fields_are_granted_before_any_artifact_read(ready, field):
    ready[-2].admission = replace(ready[-2].admission,
        allowed_fields=context.REQUIRED_FIELDS - {field})
    r = read(ready)
    expected = "FIELD_GRANT_INVALID" if field in {"fact_id", "kind", "lifecycle"} else "PROJECTION_FIELDS_NOT_ADMITTED"
    assert_refusal(r, expected)
    assert ready[-1].reads == 0


def test_owner_denial_precedes_private_io(ready):
    ready[-2].deny = True
    assert_refusal(read(ready), "SOURCE_NOT_ADMITTED")
    assert ready[-1].reads == 0


def test_owner_exception_is_sanitized(ready):
    class BrokenOwner:
        def resolve(self, request):
            raise RuntimeError("private secret detail")
    assert_refusal(read(ready, authority=BrokenOwner()), "OWNER_RESOLUTION_UNAVAILABLE")
    assert ready[-1].reads == 0


@pytest.mark.parametrize("mode", ["purpose", "audience", "fact_id"])
def test_caller_cannot_relabel_approved_request(ready, mode):
    req = replace(ready[3], **{mode: "different-request"})
    assert_refusal(read(ready, request=req), "ADMISSION_REQUEST_MISMATCH")
    assert ready[-1].reads == 0


def test_arbitrary_dict_is_not_an_authorized_request(ready):
    assert_refusal(read(ready, request={"fact_id": ready[2]["fact_id"]}), "REQUEST_INVALID")
    assert ready[-1].reads == 0 and ready[-2].calls == 0


def test_date_only_native_fact_is_not_historical_permission(ready):
    request = replace(ready[3], mode="historical", as_of="2026-09-01T12:00:00Z")
    ready[-2].admission = replace(ready[-2].admission, request=request)
    assert_refusal(read(ready, request=request), "HISTORICAL_BINDING_UNAVAILABLE")
    assert ready[-1].reads == 0


def test_later_knowability_never_enters_an_earlier_query(ready):
    request = replace(ready[3], mode="historical", as_of="2026-01-02T12:00:00Z")
    ready[-2].admission = replace(ready[-2].admission, request=request)
    assert_refusal(read(ready, request=request), "FUTURE_KNOWLEDGE")
    assert ready[-1].reads == 0


@pytest.mark.parametrize("when", [2, 3])
def test_generation_change_prevents_stale_positive(ready, when):
    ready[-2].change_at = when
    result = read(ready)
    assert_refusal(result, "ADMISSION_CHANGED")
    if when == 2:
        assert ready[-1].reads == 0


def test_missing_fact_has_no_cached_positive(ready):
    assert read(ready)["status"] == "available"
    store = ready[-1]
    key = "company_intelligence/issuer_disclosures/v1/facts/" + ready[-2].admission.reference.sha256 + ".json"
    del store.objects[key]
    assert_refusal(read(ready), "PRIVATE_OBJECT_ABSENT")


def test_corrupt_native_fact_does_not_project(ready):
    store = ready[-1]
    key = "company_intelligence/issuer_disclosures/v1/facts/" + ready[-2].admission.reference.sha256 + ".json"
    store.objects[key] = b"corrupt"
    assert_refusal(read(ready), "PRIVATE_OBJECT_MISMATCH")


def test_revision_binding_is_required(ready):
    store = ready[-1]
    for key in list(store.objects):
        if "/revisions/facts/" in key:
            del store.objects[key]
    assert_refusal(read(ready), "REVISION_BINDING_ABSENT")


def test_no_writer_capability_is_needed(ready):
    backing = ready[-1]
    class ReadOnlyStore:
        def get_bytes_strict_bounded(self, *args, **kwargs):
            return backing.get_bytes_strict_bounded(*args, **kwargs)
        def get_bytes_strict_bounded_versioned(self, *args, **kwargs):
            return backing.get_bytes_strict_bounded_versioned(*args, **kwargs)
    writes = backing.writes
    assert read(ready, store=ReadOnlyStore())["status"] == "available"
    assert backing.writes == writes


def test_outputs_are_fresh_copies_with_deterministic_content(ready):
    first = read(ready); second = read(ready)
    assert first == second and first is not second
    first["context"]["provenance"]["reference"]["sha256"] = "0" * 64
    first["context"]["relationship"]["product"] = "edited"
    assert read(ready) == second


@pytest.mark.parametrize("change", ["schema", "generation", "reference", "kind", "lifecycle", "amount", "timing"])
def test_reader_contract_drift_is_not_silently_coerced(ready, monkeypatch, change):
    selected = native.read_disclosure(ready[-1], ready[-2], ready[3])
    if change in {"schema", "generation"}:
        selected[change] = "unsupported"
    elif change == "reference":
        selected[change] = {"sha256": "0" * 64}
    elif change == "timing":
        selected["source_timing"].pop("published_at")
    else:
        selected["fact"][change] = 49 if change == "amount" else "unsupported"
    monkeypatch.setattr(context.native, "read_disclosure", lambda *args, **kwargs: selected)
    assert_refusal(read(ready), "ECONOMIC_SPECIES_NOT_MAPPED" if change in {"kind", "lifecycle", "amount"}
        else "NATIVE_PROJECTION_CONTRACT_MISMATCH")


def test_current_committed_c01_grain_is_preserved_in_synthetic_store(ready):
    # Uses already committed fact metadata, NOT production source capture, store or entitlement.
    from pathlib import Path
    spec = json.loads((Path(__file__).resolve().parents[1] /
        "research/theme_graph/issuer_disclosures_20261011/C01_NATIVE_OWNER.json").read_text())
    edition, fact = spec["edition"], spec["fact"]
    er, fr = native.validate_edition(edition), native.validate_fact(fact)
    req = replace(ready[3], fact_id=fact["fact_id"])
    owner = ready[-2]
    owner.admission = replace(owner.admission, request=req, reference=fr, edition=er,
        known_at=fact["known_at"], publication_precision=edition["publication_precision"])
    store = ready[-1]
    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    for family, value, ref, identity in [("editions", edition, er, edition["disclosure_id"]),
                                        ("facts", fact, fr, fact["fact_id"])]:
        store.objects[f"company_intelligence/issuer_disclosures/v1/{family}/{ref.sha256}.json"] = canonical(value)
        key = hashlib.sha256(identity.encode()).hexdigest()
        store.objects[f"company_intelligence/issuer_disclosures/v1/revisions/{family}/{key}/1.json"] = canonical(
            {"schema": "company_intelligence.disclosure_revision_binding/v1", "reference": ref.payload()})
    result = read(ready, request=req)
    assert result["status"] == "available"
    projected = result["context"]
    assert projected["provenance"]["reference"] == spec["correction_decision"]["fact"]
    assert projected["relationship"]["subject_id"] == "ISS:US-XNAS-MU"
    assert projected["relationship"]["object_id"] == "ISS:US-XNAS-NVDA"
    assert projected["relationship"]["lifecycle"] == "planned"
    assert projected["timing"]["source_published_date"] == "2024-02-26"
    assert projected["timing"]["fact_known_at"] == fact["known_at"]
    assert projected["mapping"]["legacy_theme_graph_edge"] is None


def test_corrected_native_revision_is_read_without_rewriting_prior(ready):
    body, edition, fact, request, authority, store = ready
    previous = deepcopy(store.objects)
    old = read(ready)
    prior_e, prior_f = native.validate_edition(edition), native.validate_fact(fact)
    edition.update(revision=2, previous=prior_e.payload(), published_date="2026-01-03",
                   known_at="2026-01-03T11:00:00Z")
    eref = native.validate_edition(edition)
    fact.update(revision=2, previous=prior_f.payload(), edition=eref.payload(),
                known_at="2026-01-03T11:01:00Z", product="Corrected synthetic memory")
    authority.admission = replace(authority.admission, reference=native.validate_fact(fact),
        edition=eref, known_at=fact["known_at"], generation="corrected-generation")
    publish(ready)
    result = read(ready)["context"]
    assert result["provenance"]["revision"] == 2
    assert result["provenance"]["reference"] != old["context"]["provenance"]["reference"]
    assert result["timing"]["edition_known_at"] == edition["known_at"]
    assert result["timing"]["fact_known_at"] == fact["known_at"]
    assert all(store.objects[k] == v for k, v in previous.items())


def test_subject_binding_mismatch_is_preserved(ready):
    authority = ready[-2]
    authority.admission = replace(authority.admission,
        subject_binding=native.SubjectIdentityBinding("cik:0000000003", "0000000003",
            "fixture:identity", "a"*64, 100, "b"*64))
    assert_refusal(read(ready), "SUBJECT_IDENTITY_MISMATCH")


def test_source_fields_outside_native_grant_never_enter_projection(ready):
    ready[-2].admission = replace(ready[-2].admission,
        allowed_fields=context.REQUIRED_FIELDS | {"span"})
    assert_refusal(read(ready), "FIELD_GRANT_INVALID")
    assert ready[-1].reads == 0


def test_store_failure_has_no_raw_message_or_fallback(ready):
    class BrokenStore:
        def get_bytes_strict_bounded(self, *args, **kwargs):
            raise OSError("private store path /secret and provider detail")
    assert_refusal(read(ready, store=BrokenStore()), "PRIVATE_READ_UNAVAILABLE")


def test_native_error_codes_cannot_inject_unbounded_output(ready, monkeypatch):
    monkeypatch.setattr(context.native, "preflight", lambda *args: (_ for _ in ()).throw(
        native.DisclosureError("untrusted exception text /path")))
    assert_refusal(read(ready), "NATIVE_DISCLOSURE_UNAVAILABLE")


def test_existing_admission_pin_avoids_only_extra_composing_lookup(ready):
    pin = ready[-2].admission
    result = read(ready, expected_admission=pin)
    assert result["status"] == "available"
    assert ready[-2].calls == 2  # both actual native read-time checks still occur


def test_existing_pin_cannot_override_owner_revocation(ready):
    pin = ready[-2].admission
    ready[-2].deny = True
    assert_refusal(read(ready, expected_admission=pin), "SOURCE_NOT_ADMITTED")
    assert ready[-1].reads == 0


def test_existing_pin_cannot_override_new_generation(ready):
    pin = ready[-2].admission
    ready[-2].admission = replace(pin, generation="changed-after-composing-preflight")
    assert_refusal(read(ready, expected_admission=pin), "ADMISSION_CHANGED")
    assert ready[-1].reads == 0


def test_arbitrary_admission_dictionary_never_reaches_owner_or_store(ready):
    assert_refusal(read(ready, expected_admission={"generation": "fake"}), "ADMISSION_INVALID")
    assert ready[-1].reads == 0 and ready[-2].calls == 0


def test_pin_has_own_field_restriction_before_reads(ready):
    pin = replace(ready[-2].admission, allowed_fields=context.REQUIRED_FIELDS - {"product"})
    assert_refusal(read(ready, expected_admission=pin), "PROJECTION_FIELDS_NOT_ADMITTED")
    assert ready[-1].reads == 0 and ready[-2].calls == 0


def test_qualified_usage_is_carried_but_not_reflected_on_refusal(ready):
    assert read(ready)["context"]["usage"] == {
        "purpose": ready[3].purpose, "audience": ready[3].audience}
    ready[-2].deny = True
    result = read(ready)
    assert_refusal(result, "SOURCE_NOT_ADMITTED")
    assert ready[3].audience not in json.dumps(result)


@pytest.fixture
def qualified_local_owner(tmp_path):
    # Reuse the native owner's own synthetic publication harness. No live
    # state, source acquisition, actual permission grant or C01 republish.
    from tests.test_company_disclosure_owner import case, publish as publish_generation
    value = case.__wrapped__(tmp_path)
    result = publish_generation(value)
    assert result["status"] == "COMMITTED_OBSERVED"
    return value, result


def test_actual_native_owner_and_readonly_store_path(qualified_local_owner):
    from engine.company_intelligence import issuer_disclosure_owner as owner
    from tests.test_company_disclosure_owner import request
    value, published = qualified_local_owner
    source, state, artifacts, *_ = value
    frozen = {str(p): p.read_bytes() for root in (state.root, artifacts.root)
              for p in root.rglob("*") if p.is_file()}
    actual_owner = owner.CurrentDisclosureOwner(source, owner.ReadOnlyLocalObjects(state.root))
    readonly = owner.ReadOnlyLocalObjects(artifacts.root)
    result = context.read_economic_context(readonly, actual_owner, request(value))
    assert result["status"] == "available"
    c = result["context"]
    assert c["provenance"]["generation"] == published["generation"]
    assert c["relationship"]["kind"] == "product_integration"
    assert c["relationship"]["lifecycle"] == "planned"
    assert c["usage"] == {"purpose": owner.PURPOSE, "audience": owner.AUDIENCE}
    assert c["timing"]["source_published_date"] == "2024-02-26"
    assert c["mapping"]["legacy_theme_graph_edge"] is None
    assert not hasattr(readonly, "put_bytes_strict_conditional")
    assert frozen == {str(p): p.read_bytes() for root in (state.root, artifacts.root)
                       for p in root.rglob("*") if p.is_file()}


def test_actual_native_owner_revocation_prevents_any_fact_read(qualified_local_owner):
    from engine.company_intelligence import issuer_disclosure_owner as owner
    from tests.test_company_disclosure_owner import request
    value, _ = qualified_local_owner
    source, state, *_ = value
    source.value = replace(source.value, ruling_revision="0"*64)
    actual_owner = owner.CurrentDisclosureOwner(source, owner.ReadOnlyLocalObjects(state.root))
    class NoArtifactRead:
        reads = 0
        def get_bytes_strict_bounded(self, *args, **kwargs):
            self.reads += 1
            raise AssertionError("artifact access after revoked native metadata")
    store = NoArtifactRead()
    assert_refusal(context.read_economic_context(store, actual_owner, request(value)))
    assert store.reads == 0


def test_actual_native_owner_rejects_historical_route_before_source_lookup(qualified_local_owner):
    from engine.company_intelligence import issuer_disclosure_owner as owner
    from tests.test_company_disclosure_owner import request
    value, _ = qualified_local_owner
    source, state, artifacts, *_ = value
    actual_owner = owner.CurrentDisclosureOwner(source, owner.ReadOnlyLocalObjects(state.root))
    source.calls = 0
    historical = request(value, mode="historical", as_of="2026-09-01T12:00:00Z")
    result = context.read_economic_context(owner.ReadOnlyLocalObjects(artifacts.root), actual_owner, historical)
    assert_refusal(result, "SOURCE_NOT_ADMITTED")
    assert source.calls == 0
