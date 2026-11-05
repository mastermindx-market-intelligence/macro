"""API parity for the private issuer economic-context route (WS:GMI-THEME-GRAPH lane c).

#9423 merged ``GET /api/company-intelligence/private/issuers/{id}/economic-context``
and its readers. These tests pin what its own suite leaves open:

* the route body equals the native reader byte for byte on the real C01 grain;
* C01, the accepted publication, is the only positive, and its relationship
  fields equal the committed spec rather than a fixture copy;
* the selection, fact and economic-context routes agree on generation and on the
  fact and edition references, as F04 composition requires
  (PRIVATE_CONSUMER_CONTRACT.md, "Issuer selection for F04 composition");
* the counterparty issuer is never handed C01 as an implied positive;
* every non-C01 species, and every other refusal reason, collapses into one
  reason-invariant transport envelope;
* the economic-context route serves the same private transport headers as the
  sibling private routes that the Terminal already consumes.

Tests only. No network, credential, production endpoint or Terminal render is
exercised; Terminal parity here is limited to the HTTP transport contract.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from app import company_disclosures as api
from engine.company_intelligence import issuer_disclosure_owner as owner
from engine.theme_graph import issuer_economic_context as consumer
from tests.test_company_issuer_disclosures import sample  # noqa: F401  (fixture used by boundary)
from tests.test_company_disclosure_owner import case, publish  # noqa: F401  (fixture)
from tests.test_company_disclosures_api import boundary, private_headers  # noqa: F401  (fixture)

BASE = "/api/company-intelligence/private"
AUTH = {"Authorization": "Bearer synthetic-token"}
C01_SPEC = Path(__file__).resolve().parents[1] / (
    "research/theme_graph/issuer_disclosures_20261011/C01_NATIVE_OWNER.json")
REFUSAL = {"schema": api.ERROR_SCHEMA, "code": "PRIVATE_SOURCE_UNAVAILABLE",
           "automatic_retry_permitted": False}
RELATIONSHIP_FIELDS = ("kind", "lifecycle", "subject_id", "object_id", "product",
                       "platform", "amount", "economic_share")


def committed_c01() -> dict:
    """The committed C01 spec bytes, independent of the publication fixture."""
    assert Path(owner.SPEC_PATH).resolve() == C01_SPEC.resolve()
    return json.loads(C01_SPEC.read_bytes())


@pytest.fixture
def c01(boundary, case):
    """Install the real current owner over read-only artifacts of one publication."""
    published = publish(case)
    source, state, artifacts, *_ = case
    current = owner.CurrentDisclosureOwner(source, owner.ReadOnlyLocalObjects(state.root))

    def factory():
        return owner.ReadOnlyLocalObjects(artifacts.root)

    client = boundary[0]
    client.app.state.company_disclosure_reader = api.PrivateDisclosureReader(current, factory, current)
    issuer = source.value.spec["fact"]["subject_id"]
    roots = (state.root, artifacts.root)
    return client, source, current, factory, issuer, published, roots


def snapshot(roots) -> dict:
    return {p: p.read_bytes() for root in roots for p in root.rglob("*") if p.is_file()}


def economic(client, issuer):
    return client.get(f"{BASE}/issuers/{issuer}/economic-context", headers=AUTH)


def direct(current, factory, issuer) -> dict:
    return consumer.read_issuer_economic_context(
        current, current, factory, issuer, purpose=api.PURPOSE, audience=api.AUDIENCE)


def refused(response) -> bytes:
    assert response.status_code == 503, response.text
    private_headers(response)
    assert response.json() == REFUSAL
    return response.content


def test_route_body_is_the_native_reader_result_without_writes(c01):
    client, _, current, factory, issuer, published, roots = c01
    before = snapshot(roots)
    response = economic(client, issuer)
    assert response.status_code == 200, response.text
    private_headers(response)
    expected = direct(current, factory, issuer)
    assert expected["status"] == "available"
    assert response.json() == json.loads(json.dumps(expected))
    assert response.json()["context"]["generation"] == published["generation"]
    assert snapshot(roots) == before


def test_c01_is_the_sole_positive_and_matches_the_committed_spec(c01):
    client, source, _, _, issuer, _, _ = c01
    spec = committed_c01()
    fact = spec["fact"]
    assert issuer == fact["subject_id"] == "ISS:US-XNAS-MU"
    body = economic(client, issuer).json()
    assert body["schema"] == consumer.SCHEMA
    assert body["authority"] == "context_only" and body["reason"] is None
    context = body["context"]
    assert context["issuer_role"] == "subject_disclosing_company"
    assert context["issuer_binding"]["issuer_id"] == fact["subject_id"]
    assert context["coverage"]["selected_count"] == 1
    assert context["coverage"]["global_relationship_coverage_established"] is False
    assert context["usage"] == {"purpose": api.PURPOSE, "audience": api.AUDIENCE}
    [row] = context["relationships"]
    assert row["relationship"] == {k: fact[k] for k in RELATIONSHIP_FIELDS}
    assert row["relationship"]["object_id"] == "ISS:US-XNAS-NVDA"
    assert row["relationship"]["amount"] is None and row["relationship"]["economic_share"] is None
    assert row["provenance"]["fact_id"] == fact["fact_id"]
    assert row["provenance"]["revision"] == fact["revision"]
    assert row["provenance"]["reference"] == source.value.spec["correction_decision"]["fact"]
    assert row["timing"]["source_published_date"] == spec["edition"]["published_date"] == "2024-02-26"
    assert row["timing"]["publication_precision"] == spec["edition"]["publication_precision"]
    assert row["timing"]["fact_known_at"] == fact["known_at"]
    assert row["timing"]["identity_mode"] == "current"
    assert row["mapping"]["legacy_theme_graph_edge"] is None
    assert row["mapping"]["propagation_hypothesis"] is None
    assert row["limitations"] and not any(row["limitations"].values())


def test_selection_fact_and_economic_routes_agree_on_one_publication(c01):
    client, _, _, _, issuer, published, _ = c01
    fact_id = committed_c01()["fact"]["fact_id"]
    selected = client.get(f"{BASE}/issuers/{issuer}/product-integrations", headers=AUTH)
    read = client.get(f"{BASE}/product-integrations/{fact_id}", headers=AUTH)
    context = economic(client, issuer)
    for response in (selected, read, context):
        assert response.status_code == 200, response.text
    selected, read, context = selected.json(), read.json(), context.json()["context"]
    [selection_row] = selected["selections"]
    [row] = context["relationships"]
    provenance = row["provenance"]
    assert selection_row["fact_id"] == read["fact"]["fact_id"] == provenance["fact_id"] == fact_id
    generations = {selected["generation"], read["generation"], context["generation"],
                   provenance["generation"], published["generation"]}
    assert len(generations) == 1
    assert selection_row["fact_reference"] == read["reference"] == provenance["reference"]
    assert selection_row["edition_reference"] == read["edition"] == provenance["edition"]
    assert selection_row["kind"] == row["relationship"]["kind"]
    assert selection_row["lifecycle"] == row["relationship"]["lifecycle"]
    assert selected["issuer_binding"] == context["issuer_binding"]


def test_counterparty_issuer_is_not_an_implied_positive(c01):
    client, _, current, factory, _, _, _ = c01
    fact = committed_c01()["fact"]
    counterparty = fact["object_id"]
    response = economic(client, counterparty)
    assert fact["fact_id"] not in response.text
    reader = direct(current, factory, counterparty)
    assert fact["fact_id"] not in json.dumps(reader)
    # Pinned merged behaviour: the C01 owner holds no current selection for the
    # object issuer, so the reader is unavailable rather than an empty positive
    # and the route serves the stable refusal, not a mirrored relationship.
    assert reader == consumer._unavailable("SELECTION_UNAVAILABLE")
    refused(response)


def mutate_selected(monkeypatch, change):
    original = consumer.selection.read_issuer_disclosure_bundle

    def wrapped(*args, **kwargs):
        bundle = original(*args, **kwargs)
        first, *rest = bundle.disclosures
        payload = deepcopy(first.payload)
        change(payload)
        return replace(bundle, disclosures=(replace(first, payload=payload), *rest))

    monkeypatch.setattr(consumer.selection, "read_issuer_disclosure_bundle", wrapped)


@pytest.mark.parametrize("field,value", [
    ("lifecycle", "current"),
    ("kind", "supply_agreement"),
    ("amount", 49),
    ("economic_share", 0.1),
])
def test_every_non_c01_species_is_a_refusal(c01, monkeypatch, field, value):
    client, _, current, factory, issuer, _, _ = c01
    mutate_selected(monkeypatch, lambda payload: payload["fact"].__setitem__(field, value))
    reader = direct(current, factory, issuer)
    assert reader["status"] == "unavailable"
    assert reader["reason"] == "ECONOMIC_SPECIES_NOT_MAPPED"
    assert reader["context"] is None
    refused(economic(client, issuer))


def test_refusal_envelope_is_invariant_to_the_reason(c01, monkeypatch):
    client, source, current, factory, issuer, _, _ = c01
    reasons, bodies, headers = set(), set(), set()

    def observe():
        reader = direct(current, factory, issuer)
        assert reader["status"] == "unavailable" and reader["context"] is None
        reasons.add(reader["reason"])
        response = economic(client, issuer)
        bodies.add(refused(response))
        headers.add(tuple(response.headers.get(k) for k in api._HEADERS))

    with monkeypatch.context() as patch:
        mutate_selected(patch, lambda payload: payload["fact"].__setitem__("lifecycle", "current"))
        observe()
    with monkeypatch.context() as patch:
        mutate_selected(patch, lambda payload: payload.__setitem__("generation", "0" * 64))
        observe()
    def broken():
        raise OSError("store offline")

    # Starlette State stores attributes outside __dict__. Restore through its
    # public interface: pytest 9.2 setattr undo otherwise removes this reader.
    original_reader = client.app.state.company_disclosure_reader
    try:
        client.app.state.company_disclosure_reader = api.PrivateDisclosureReader(current, broken, current)
        reasons.add(direct(current, broken, issuer)["reason"])
        bodies.add(refused(economic(client, issuer)))
    finally:
        client.app.state.company_disclosure_reader = original_reader
    assert client.app.state.company_disclosure_reader is original_reader
    revoked = replace(source.value, ruling_revision="0" * 64)
    original, source.value = source.value, revoked
    try:
        observe()
    finally:
        source.value = original
    bodies.add(refused(economic(client, committed_c01()["fact"]["object_id"])))
    assert reasons == {"ECONOMIC_SPECIES_NOT_MAPPED", "NATIVE_PROJECTION_CONTRACT_MISMATCH",
                       "PRIVATE_STORE_UNAVAILABLE", "SELECTION_UNAVAILABLE"}
    assert len(bodies) == 1 and len(headers) == 1
    assert economic(client, issuer).status_code == 200


def test_transport_headers_match_the_sibling_private_routes(c01):
    client, _, _, _, issuer, _, _ = c01
    fact_id = committed_c01()["fact"]["fact_id"]
    responses = [
        economic(client, issuer),
        client.get(f"{BASE}/issuers/{issuer}/product-integrations", headers=AUTH),
        client.get(f"{BASE}/product-integrations/{fact_id}", headers=AUTH),
    ]
    for response in responses:
        assert response.status_code == 200, response.text
        private_headers(response)
        assert response.headers["content-type"].startswith("application/json")
    for key in api._HEADERS:
        assert len({response.headers.get(key) for response in responses}) == 1, key
        assert responses[0].headers.get(key) == api._HEADERS[key]
