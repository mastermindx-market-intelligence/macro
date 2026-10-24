"""Native owner composition and bounded-read authority controls."""
import pytest

from engine.institutional_census import research_context as consumer
from tests.test_institutional_census_k3e_projection import (
    _world, FILER_CIK, ACCESSION, REPORT_PERIOD, DECISION_CUTOFF,
)
from tests.test_institutional_research_api import world, HEADERS, PATH
import app.institutional_research as api


def test_native_reporting_facts_compose_without_economic_promotion(tmp_path, monkeypatch):
    store, generation = _world(tmp_path)
    monkeypatch.setattr(consumer, "build_institutional_13f_store", lambda: store)
    result = consumer.read_reported_holding_context(
        filer_cik=FILER_CIK, report_period=REPORT_PERIOD, accession=ACCESSION,
        infotable_sk=7, decision_cutoff=DECISION_CUTOFF, generation_id=generation.generation_id,
    )
    assert result["state"] == "AVAILABLE_UNQUALIFIED"
    context = result["context"]
    assert context["schema"] == "institutional_13f.reported_holding_accession_context.v1"
    assert context["generation"]["validation_scope"]["whole_generation_verified"] is False
    assert context["generation"]["generation_id"] == generation.generation_id
    assert context["generation"]["current_generation_id"] is None
    assert context["generation"]["pointer"]["state"] == "not_read"
    assert context["generation"]["superseded"] is None
    assert context["filing"]["retained_at"] == "2026-05-15T20:32:00Z"
    assert context["holding"]["row_hash"] == "b" * 64
    assert context["holding"]["infotable_sk"] == "7"
    assert context["reporting_structure"]["other_manager_count"] == 0
    assert context["k3e_admissible"] is False
    assert context["holding"]["normalized_quantity"] is None
    bindings = result["semantic_bindings"]
    assert bindings["reporting_entity"]["state"] == "OWNER_VERIFIED"
    assert bindings["reporting_entity"]["source_receipt_id"] == context["filing"]["source_receipt_id"]
    assert bindings["security"]["reported_cusip"] == "037833100"
    assert bindings["security"]["canonical_security_id"] is None
    assert bindings["economic_vehicle"]["vehicle_class"] is None
    assert bindings["strategy"]["decision_mode"] is None
    assert result["authority"] and not any(result["authority"].values())
    assert result["persistence"] == "none"


def test_prepublication_cutoff_is_unavailable_not_empty_ownership(tmp_path, monkeypatch):
    store, generation = _world(tmp_path)
    monkeypatch.setattr(consumer, "build_institutional_13f_store", lambda: store)
    result = consumer.read_reported_holding_context(
        filer_cik=FILER_CIK, report_period=REPORT_PERIOD, accession=ACCESSION,
        infotable_sk=7, decision_cutoff="2026-05-15T00:00:00Z", generation_id=generation.generation_id,
    )
    assert result["state"] == "UNAVAILABLE"
    assert result["context"]["refusals"] == ["GENERATION_NOT_AVAILABLE_AT_CUTOFF"]
    assert result["context"]["holding"] is None
    assert result["semantic_bindings"]["reporting_entity"]["state"] == "UNAVAILABLE"
    assert not any(result["authority"].values())


def test_entitled_http_consumer_uses_the_real_native_projection(world, tmp_path, monkeypatch):
    _, client, calls = world
    store, generation = _world(tmp_path)
    monkeypatch.setattr(consumer, "build_institutional_13f_store", lambda: store)
    monkeypatch.setattr(api, "_read_holding_context", consumer.read_reported_holding_context)
    response = client.post(PATH, headers=HEADERS, json={
        "filer_cik": FILER_CIK, "report_period": REPORT_PERIOD, "accession": ACCESSION,
        "infotable_sk": "7", "decision_cutoff": DECISION_CUTOFF,
        "generation_id": generation.generation_id,
    })
    assert response.status_code == 200
    result = response.json()
    assert [x[0] for x in calls] == ["auth", "entitlement"]
    assert result["context"]["holding"]["row_hash"] == "b" * 64
    assert result["semantic_bindings"]["reporting_entity"]["state"] == "OWNER_VERIFIED"
    assert result["semantic_bindings"]["economic_vehicle"]["state"] == "UNRESOLVED"
    assert not any(result["authority"].values())
    assert response.headers["cache-control"] == "private, no-store"


def test_missing_dedicated_store_configuration_has_no_fallback(monkeypatch):
    names = ["INSTITUTIONAL_13F_R2_ENDPOINT", "INSTITUTIONAL_13F_R2_ACCESS_KEY_ID",
             "INSTITUTIONAL_13F_R2_SECRET_ACCESS_KEY", "INSTITUTIONAL_13F_R2_BUCKET"]
    for name in names:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("R2_ENDPOINT", "https://generic.invalid")
    with pytest.raises(Exception, match="dedicated institutional"):
        consumer.read_reported_holding_context()


def test_busy_native_reader_does_not_construct_another_store(monkeypatch):
    def forbidden():
        raise AssertionError("second store must not open")
    monkeypatch.setattr(consumer, "build_institutional_13f_store", forbidden)
    consumer._READ_SLOT.acquire()
    try:
        with pytest.raises(consumer.ResearchContextUnavailable, match="busy"):
            consumer.read_reported_holding_context()
    finally:
        consumer._READ_SLOT.release()


def test_budget_caps_before_buffering_and_has_no_write_or_unbounded_read(monkeypatch):
    limits = []
    class Store:
        def get_bytes_strict_bounded(self, key, maximum_bytes):
            limits.append(maximum_bytes)
            return b"a" * maximum_bytes
    monkeypatch.setattr(consumer, "MAX_READ_BYTES", 8)
    read = consumer._ReadOnlyBudget(Store())
    assert read.get_bytes_strict_bounded("owned", 1024) == b"a" * 8
    assert limits == [8]
    with pytest.raises(consumer.ResearchContextUnavailable, match="byte budget"):
        read.get_bytes_strict_bounded("owned", 1024)
    with pytest.raises(consumer.ResearchContextUnavailable, match="non-read"):
        read.put_bytes("owned", b"must-not-write")
    with pytest.raises(consumer.ResearchContextUnavailable, match="unbounded"):
        read.get_bytes_strict("owned")


def test_ignored_owner_bound_is_refused():
    class Store:
        def get_bytes_strict_bounded(self, *_):
            return b"x" * 9
    with pytest.raises(consumer.ResearchContextUnavailable, match="read bound"):
        consumer._ReadOnlyBudget(Store()).get_bytes_strict_bounded("owned", 8)


def test_interactive_call_bound_refuses_without_partial_context(tmp_path, monkeypatch):
    store, generation = _world(tmp_path)
    monkeypatch.setattr(consumer, "MAX_READ_CALLS", 0)
    monkeypatch.setattr(consumer, "build_institutional_13f_store", lambda: store)
    with pytest.raises(consumer.ResearchContextUnavailable, match="budget"):
        consumer.read_reported_holding_context(
            filer_cik=FILER_CIK, report_period=REPORT_PERIOD, accession=ACCESSION,
            infotable_sk=7, decision_cutoff=DECISION_CUTOFF, generation_id=generation.generation_id,
        )


def test_large_native_row_identity_is_text_without_mutating_owner_output():
    native = {"authority": "descriptive_context_only", "k3e_admissible": False,
              "financial_influence": False, "state": "AVAILABLE_UNQUALIFIED", "valid": True,
              "holding": {"infotable_sk": 4611686018427387905}}
    result = consumer._compose_context(native)
    assert result["context"]["holding"]["infotable_sk"] == "4611686018427387905"
    assert native["holding"]["infotable_sk"] == 4611686018427387905


def test_cooperative_time_limit_keeps_read_slot_until_owner_returns(tmp_path, monkeypatch):
    store, generation = _world(tmp_path)
    monkeypatch.setattr(consumer, "build_institutional_13f_store", lambda: store)
    ticks = iter([0, 31])
    monkeypatch.setattr(consumer, "monotonic", lambda: next(ticks, 31))
    with pytest.raises(consumer.ResearchContextUnavailable, match="budget"):
        consumer.read_reported_holding_context(
            filer_cik=FILER_CIK, report_period=REPORT_PERIOD, accession=ACCESSION,
            infotable_sk=7, decision_cutoff=DECISION_CUTOFF, generation_id=generation.generation_id,
        )
    assert consumer._READ_SLOT.acquire(blocking=False)
    consumer._READ_SLOT.release()


@pytest.mark.parametrize("change", [{"authority": "positive"}, {"k3e_admissible": True},
                                   {"financial_influence": True}, {"state": "PILOT_COMPILED"}])
def test_unreviewed_native_authority_change_fails_closed(change):
    native = {"authority": "descriptive_context_only", "k3e_admissible": False,
              "financial_influence": False, "state": "UNAVAILABLE", "valid": False}
    with pytest.raises(consumer.ResearchContextUnavailable):
        consumer._compose_context({**native, **change})


@pytest.mark.parametrize('change', [
    {'canonical_security': {'state': 'ACCEPTED'}},
    {'valid': False, 'state': 'AVAILABLE_UNQUALIFIED'},
    {'holding': {'infotable_sk': True}},
    {'holding': {'infotable_sk': 4611686018427387905.0}},
    {'holding': {'infotable_sk': 2**63}},
])
def test_contract_drift_cannot_silently_expand_private_consumer(change):
    native = {'authority': 'descriptive_context_only', 'k3e_admissible': False,
              'financial_influence': False, 'state': 'AVAILABLE_UNQUALIFIED',
              'valid': True, 'holding': {'infotable_sk': 7}}
    with pytest.raises(consumer.ResearchContextUnavailable):
        consumer._compose_context({**native, **change})


def test_shared_authority_constant_drift_cannot_promote_consumer(monkeypatch):
    monkeypatch.setattr(consumer, 'ALL_FALSE_AUTHORITY', {'can_rank': True})
    with pytest.raises(consumer.ResearchContextUnavailable):
        consumer._compose_context({'authority': 'descriptive_context_only',
            'k3e_admissible': False, 'financial_influence': False, 'state': 'UNAVAILABLE'})


def test_swallowed_forbidden_owner_operation_still_exhausts_lane():
    read = consumer._ReadOnlyBudget(object())
    with pytest.raises(consumer.ResearchContextUnavailable):
        read.put_bytes('must-not-write', b'')
    assert read.exhausted


def test_scoped_consumer_keeps_amendment_lineage_and_pinned_original(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from tests.test_institutional_census_k3e_projection import (
        _publish_amendment_generation, AMEND_ACCESSION,
    )
    store, original = _world(tmp_path)
    filing = dict(original.filings[0])
    amended = _publish_amendment_generation(store, filing_orig=filing,
        holding_orig=dict(original.holdings[0]), raw_orig=SimpleNamespace(
            receipt_id=filing['source_receipt_id'],
            raw_object=SimpleNamespace(sha256=filing['raw_sha256'])))
    monkeypatch.setattr(consumer, 'build_institutional_13f_store', lambda: store)
    common = dict(filer_cik=FILER_CIK, report_period=REPORT_PERIOD,
                  infotable_sk=7, decision_cutoff='2026-05-22T00:00:00Z')
    pinned = consumer.read_reported_holding_context(**common,
        accession=ACCESSION, generation_id=original.generation_id)
    assert pinned['context']['holding']['quantity']['value'] == '125000'
    stale_row = consumer.read_reported_holding_context(**common,
        accession=ACCESSION, generation_id=amended.generation_id)
    assert stale_row['state'] == 'UNAVAILABLE'
    assert stale_row['context']['refusals'] == ['FILING_ACCESSION_NOT_EFFECTIVE_AT_CUTOFF']
    assert stale_row['context']['holding'] is None
    current = consumer.read_reported_holding_context(**common,
        accession=AMEND_ACCESSION, generation_id=amended.generation_id)
    assert current['context']['holding']['quantity']['value'] == '999999'
    assert current['context']['filing']['amends_accession'] == ACCESSION
    assert not any(current['authority'].values())


def test_selected_catalog_row_still_requires_actual_raw_receipt_binding(tmp_path, monkeypatch):
    store, generation = _world(tmp_path, raw_sha_override='f' * 64)
    monkeypatch.setattr(consumer, 'build_institutional_13f_store', lambda: store)
    result = consumer.read_reported_holding_context(filer_cik=FILER_CIK,
        report_period=REPORT_PERIOD, accession=ACCESSION, infotable_sk=7,
        decision_cutoff=DECISION_CUTOFF, generation_id=generation.generation_id)
    assert result['state'] == 'REFUSED'
    assert result['context']['refusals'] == ['SOURCE_RECEIPT_MISMATCH']
    assert result['context']['holding'] is None
    assert result['semantic_bindings']['reporting_entity']['state'] == 'UNAVAILABLE'
