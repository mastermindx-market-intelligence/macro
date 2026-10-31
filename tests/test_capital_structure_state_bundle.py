"""SPEC_U1_API gates 1-11: the Capital Structure state bundle producer.

Two fixture families, both reused BY IMPORT and never re-implemented:

* the REAL disk path (``_compiled_root`` + the projection builder + this lane's
  script) for the publication gates 5, 6 and 7 and one end-to-end assertion in
  gate 1;
* an in-memory verified generation hand-built from the lifecycle suite's own
  ``_event``/``_edge`` factories and the integration suite's S-1 scenario, for
  the engine gates 1-4 and 8-11.

No digest, id or count is hard-coded: every expectation is derived from the
fixtures, the rule pack or the frozen contract constants.
"""
from __future__ import annotations

from dataclasses import replace
import json

import pytest

from engine.capital_structure import projection as projection_module
from engine.capital_structure import state_bundle as state_bundle_module
from engine.capital_structure.issuer_state_contracts import (
    AUTHORITY,
    INHERITED_UNAVAILABLE_CAPABILITIES,
    STATE_CONTRACT_VERSION,
    CapitalInputs,
    ContractViolation,
    sha256_of,
)
from engine.capital_structure.registration_integration import (
    integrate_registration_paths,
)
from engine.capital_structure.rule_applicability import load_rule_applicability_pack
from engine.capital_structure.state_bundle import (
    STATE_BUNDLE_IMPLEMENTATION_DIGEST,
    STATE_BUNDLE_SCHEMA,
    STATE_BUNDLE_VERSION,
    build_capital_inputs,
    build_state_bundle,
    coverage_for,
    inputs_for_issuer,
    issuer_inputs,
    not_yet_observed,
    state_from_record,
    then_known_state,
    validate_state_bundle,
)
from engine.capital_structure.verified_projection_generation import (
    VerifiedProjectionGeneration,
)
import scripts.build_capital_structure_projection as projection_builder
import scripts.build_capital_structure_state as state_builder
from tests.test_build_capital_structure_projection import _compiled_root, _manifest
from tests.test_capital_structure_registration_integration import (
    AS_OF,
    GENERATED_AT,
    _s1_filed_amended_effective_withdrawn,
)
from tests.test_capital_structure_registration_lifecycle import _edge, _event


ISSUER_ONE = "sec:cik:0000000001"
ISSUER_TWO = "sec:cik:0000000002"
#: Between the fixture's 2nd (2026-08-03T12:00:00Z) and 3rd (2026-08-04T18:00:00Z)
#: house-knowledge clocks, so the EFFECT notice is genuinely not yet observed.
CUTOFF = "2026-08-04T00:00:00Z"
HEALTH = {"horizon": {"target_sla_hours": 24}}
S3_ROUTE_PREFIX = "form_s3.I.B."
DISK_PROJECTION_AT = "2026-08-02T13:00:00Z"
DISK_STATE_AT = "2026-08-02T14:00:00Z"
DISK_STATE_AT_LATER = "2026-08-02T15:00:00Z"


@pytest.fixture(scope="module")
def pack():
    return load_rule_applicability_pack()


# ---------------------------------------------------------------------------
# In-memory verified generation (fixture family b)
# ---------------------------------------------------------------------------


def _telemetry(events, edges, *, status="ok", extra=None):
    """The telemetry key set ``read_verified_projection_generation`` guarantees."""
    throughput = dict(extra or {})
    return {
        "status": status,
        "as_of": AS_OF,
        "generation_id": "generation:cs:"
        + sha256_of(
            {"events": events, "edges": edges, "status": status, "extra": throughput}
        )[:24],
        "artifact_hashes": {
            "event_versions": sha256_of(list(events)),
            "event_edges": sha256_of(list(edges)),
            "review_queue": sha256_of([]),
        },
        "source_ledger_receipt": None,
        "coverage_claim": None,
        "known_exclusions": [],
        **throughput,
    }


def _generation(events, edges, *, status="ok", extra=None):
    return VerifiedProjectionGeneration(
        tuple(events), tuple(edges), (), _telemetry(events, edges, status=status, extra=extra)
    )


def _projection(generation, issuer_ids):
    """A minimal served projection whose generation_id still digests its body."""
    telemetry = generation.telemetry
    body = {
        "as_of": telemetry["as_of"],
        "source_receipt": {
            "generation_id": telemetry["generation_id"],
            "as_of": telemetry["as_of"],
            "artifact_hashes": telemetry["artifact_hashes"],
        },
        "records": [{"issuer_id": issuer_id} for issuer_id in sorted(set(issuer_ids))],
    }
    return {**body, "generation_id": projection_module._stable_id("projection:cs:", body)}


def _built(
    events,
    edges,
    issuer_ids,
    *,
    rule_pack,
    generated_at=GENERATED_AT,
    as_of=AS_OF,
    manifests=(),
    health=None,
    status="ok",
    extra=None,
):
    generation = _generation(events, edges, status=status, extra=extra)
    projection = _projection(generation, issuer_ids)
    bundle = build_state_bundle(
        generation=generation,
        projection=projection,
        health=HEALTH if health is None else health,
        rule_pack=rule_pack,
        as_of=as_of,
        generated_at=generated_at,
        projection_sha256=sha256_of(projection),
        source_manifests=tuple(manifests),
    )
    validate_state_bundle(bundle)
    return generation, projection, bundle


def _two_issuer_rows():
    """The integration suite's S-1 scenario plus a shelf filing for a second issuer."""
    events, edges = _s1_filed_amended_effective_withdrawn()
    shelf = _event(
        51,
        "S-3",
        accepted_at="2026-08-01T10:00:00Z",
        seen_at="2026-08-01T20:00:00Z",
        issuer_id=ISSUER_TWO,
        cik="2",
        ticker="XYZ",
        file_number="333-777",
    )
    return [*events, shelf], list(edges)


def _state_record(bundle, issuer_id):
    return next(
        row
        for row in bundle["issuers"]
        if row["request"]["issuer_id"] == issuer_id
    )


def _family_record(bundle, issuer_id):
    return _state_record(bundle, issuer_id)["families"][0]


def _whole_inputs(generation, projection):
    return build_capital_inputs(
        generation, projection, projection_sha256=sha256_of(projection)
    )


def _evidence_keys_of(bundle):
    return {
        key
        for index in bundle["issuer_index"].values()
        for keys in index["path_evidence"].values()
        for key in keys
    }


def _disk_bundle(tmp_path):
    """One good projection build followed by one good state build, on real disk."""
    root = _compiled_root(tmp_path)
    projection_builder.build_from_disk(
        root=root,
        canonical_path=root / "projection.json",
        public_path=tmp_path / "site" / "latest.json",
        generated_at=DISK_PROJECTION_AT,
    )
    summary = state_builder.build_from_disk(root=root, generated_at=DISK_STATE_AT)
    return root, summary


def _rewrite_json(path, mutate):
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Gate 1 — one generation, one state per issuer
# ---------------------------------------------------------------------------


def test_u1_bundle_is_one_generation_with_one_state_per_issuer(pack, tmp_path):
    events, edges = _two_issuer_rows()
    generation, projection, bundle = _built(
        events, edges, [ISSUER_ONE, ISSUER_TWO], rule_pack=pack
    )
    validate_state_bundle(bundle)

    assert [row["request"]["issuer_id"] for row in bundle["issuers"]] == [
        ISSUER_ONE,
        ISSUER_TWO,
    ]
    assert bundle["generation_id"].startswith("state_bundle:cs:")
    generations = [row["request"]["input_generations"] for row in bundle["issuers"]]
    for generations_row in generations:
        assert generations_row == bundle["input_generations"]
    assert generations[0] == generations[1]
    assert {row["as_of"] for row in bundle["issuers"]} == {bundle["as_of"]}
    assert {row["projection_generation_id"] for row in bundle["issuers"]} == {
        bundle["projection_generation_id"]
    }
    assert bundle["projection_generation_id"] == projection["generation_id"]
    state_ids = [row["state_id"] for row in bundle["issuers"]]
    assert len(set(state_ids)) == len(state_ids)
    assert set(bundle["input_generations"][0]) == {
        "input_family",
        "schema",
        "support",
        "generation_id",
        "artifact_sha256",
        "as_of",
    }
    assert [row["input_family"] for row in bundle["input_generations"]] == [
        "events",
        "event_edges",
        "event_projection",
    ]

    again = _built(events, edges, [ISSUER_ONE, ISSUER_TWO], rule_pack=pack)[2]
    assert json.dumps(again, sort_keys=True) == json.dumps(bundle, sort_keys=True)
    assert generation.telemetry["generation_id"] == bundle["input_generations"][0][
        "generation_id"
    ]

    # The same law end to end, on the real disk path.
    root, summary = _disk_bundle(tmp_path)
    published = json.loads((root / "state_bundle.json").read_text(encoding="utf-8"))
    validate_state_bundle(published)
    assert published["generation_id"] == summary["generation_id"]
    assert published["issuers"], "the served projection covers at least one issuer"
    assert len({row["state_id"] for row in published["issuers"]}) == len(published["issuers"])
    for row in published["issuers"]:
        assert row["request"]["input_generations"] == published["input_generations"]
        assert row["as_of"] == published["as_of"]
        assert row["projection_generation_id"] == published["projection_generation_id"]


# ---------------------------------------------------------------------------
# Gate 2 — the registration family is integrated from the verified generation
# ---------------------------------------------------------------------------


def test_u1_registration_family_is_integrated_from_the_verified_generation(pack):
    events, edges = _two_issuer_rows()
    generation, projection, bundle = _built(
        events, edges, [ISSUER_ONE, ISSUER_TWO], rule_pack=pack
    )
    whole = _whole_inputs(generation, projection)

    for issuer_id in (ISSUER_ONE, ISSUER_TWO):
        inputs = inputs_for_issuer(whole, issuer_id)
        reg = integrate_registration_paths(
            inputs, as_of=AS_OF, generated_at=GENERATED_AT, rule_pack=pack
        )
        record = _state_record(bundle, issuer_id)
        assert record["families"][0] == reg.family_state().as_record()
        assert record["receipt"]["input_digest"] == inputs.input_digest
        assert record["receipt"]["rule_digest"] == reg.receipt.rule_digest
        assert record["receipt"]["implementation_digest"] == (
            STATE_BUNDLE_IMPLEMENTATION_DIGEST
        )
        assert bundle["issuer_index"][issuer_id]["registration_receipt"] == (
            reg.receipt.as_record()
        )
        assert bundle["issuer_index"][issuer_id]["event_count"] == len(inputs.events)
        assert bundle["issuer_index"][issuer_id]["edge_count"] == len(inputs.edges)

        rederived = issuer_inputs(bundle, generation, issuer_id)
        assert rederived.input_digest == record["receipt"]["input_digest"]
        assert rederived.bindings == whole.bindings
        assert [event["event_id"] for event in rederived.events] == [
            event["event_id"] for event in inputs.events
        ]

    # Drop a row of ISSUER_ONE (the last row belongs to the other issuer, so
    # dropping it must NOT disturb this issuer's published digest).
    shrunk = VerifiedProjectionGeneration(
        generation.events[1:], generation.edges, generation.reviews, generation.telemetry
    )
    assert issuer_inputs(bundle, shrunk, ISSUER_TWO).input_digest == (
        _state_record(bundle, ISSUER_TWO)["receipt"]["input_digest"]
    )
    with pytest.raises(ContractViolation, match="does not bind the published inputs"):
        issuer_inputs(bundle, shrunk, ISSUER_ONE)
    with pytest.raises(ContractViolation, match="issuer not covered"):
        issuer_inputs(bundle, generation, "sec:cik:0000000009")
    moved = VerifiedProjectionGeneration(
        generation.events,
        generation.edges,
        generation.reviews,
        {**generation.telemetry, "generation_id": "generation:cs:" + "b" * 24},
    )
    with pytest.raises(ContractViolation, match="state generation does not bind"):
        issuer_inputs(bundle, moved, ISSUER_ONE)


# ---------------------------------------------------------------------------
# Gate 3 — registration support is never "supported"
# ---------------------------------------------------------------------------


def test_u1_registration_support_is_never_supported(pack):
    events, edges = _two_issuer_rows()
    generation, projection, bundle = _built(
        events, edges, [ISSUER_ONE, ISSUER_TWO], rule_pack=pack
    )
    whole = _whole_inputs(generation, projection)
    for issuer_id in (ISSUER_ONE, ISSUER_TWO):
        provenance = _family_record(bundle, issuer_id)["provenance"]
        assert provenance["support"] in {"partial", "unavailable"}
        assert provenance["support"] != "supported"
        assert len(provenance["support_limits"]) > 0
        assert inputs_for_issuer(whole, issuer_id).events

    # An issuer the projection covers but the ledger never saw.
    silent_generation, silent_projection, silent_bundle = _built(
        events, edges, [ISSUER_ONE, "sec:cik:0000000003"], rule_pack=pack
    )
    silent = _family_record(silent_bundle, "sec:cik:0000000003")["provenance"]
    assert silent["support"] in {"partial", "unavailable"}
    assert silent["support"] != "supported"
    assert len(silent["support_limits"]) > 0
    assert silent_generation.telemetry["generation_id"]
    assert silent_projection["records"]

    assert bundle["coverage"]["families"]["registration"]["support"] != "supported"
    assert bundle["coverage"]["families"]["registration"]["support"] in {
        "partial",
        "unavailable",
    }
    for index in bundle["issuer_index"].values():
        assert index["coverage"]["registration"]["support"] in {"partial", "unavailable"}


# ---------------------------------------------------------------------------
# Gate 4 — every inherited capability stays unavailable without a proof (A06)
# ---------------------------------------------------------------------------


def test_u1_every_inherited_capability_stays_unavailable_without_a_proof(pack):
    events, edges = _two_issuer_rows()
    generation, projection, bundle = _built(
        events, edges, [ISSUER_ONE, ISSUER_TWO], rule_pack=pack
    )
    expected = sorted(INHERITED_UNAVAILABLE_CAPABILITIES)
    assert bundle["unavailable"] == expected
    assert bundle["capabilities_proven"] == []
    for issuer_id in (ISSUER_ONE, ISSUER_TWO):
        record = _state_record(bundle, issuer_id)
        assert record["unavailable"] == expected
        assert record["capabilities_proven"] == []

    whole = _whole_inputs(generation, projection)
    inputs = inputs_for_issuer(whole, ISSUER_ONE)
    state, _ = state_bundle_module.issuer_state(
        inputs,
        issuer_id=ISSUER_ONE,
        as_of=AS_OF,
        generated_at=GENERATED_AT,
        rule_pack=pack,
        projection_generation_id=projection["generation_id"],
    )
    with pytest.raises(ContractViolation, match="without a capability proof"):
        replace(state, unavailable=tuple(expected[1:]))

    dropped_bundle = json.loads(json.dumps(bundle))
    dropped_bundle["unavailable"] = expected[1:]
    with pytest.raises(ContractViolation):
        validate_state_bundle(dropped_bundle)

    dropped_issuer = json.loads(json.dumps(bundle))
    dropped_issuer["issuers"][0]["unavailable"] = expected[1:]
    with pytest.raises(ContractViolation):
        validate_state_bundle(dropped_issuer)

    proven = json.loads(json.dumps(bundle))
    proven["capabilities_proven"] = [{"capability": expected[0]}]
    with pytest.raises(ContractViolation):
        validate_state_bundle(proven)


# ---------------------------------------------------------------------------
# Gate 5 — a projection mismatch withholds the WHOLE bundle (A05/A06)
# ---------------------------------------------------------------------------


def test_u1_projection_generation_mismatch_withholds_the_whole_bundle(tmp_path, capsys):
    root, _ = _disk_bundle(tmp_path)
    target = root / "state_bundle.json"
    served = root / "projection.json"
    before = target.read_bytes()
    good_projection = served.read_bytes()

    _rewrite_json(
        served,
        lambda value: value["source_receipt"].update(
            {"generation_id": "generation:cs:" + "e" * 24}
        ),
    )
    with pytest.raises(ValueError, match="served projection"):
        state_builder.build_from_disk(root=root, generated_at=DISK_STATE_AT_LATER)
    assert target.read_bytes() == before
    assert state_builder.main(
        ["--root", str(root), "--generated-at", DISK_STATE_AT_LATER]
    ) != 0
    refused = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert refused["status"] == "refused"
    assert "served projection" in refused["reason"]
    assert target.read_bytes() == before

    # A projection whose own body no longer digests to its generation_id.
    served.write_bytes(good_projection)
    _rewrite_json(
        served, lambda value: value.update({"generation_id": "projection:cs:" + "f" * 24})
    )
    with pytest.raises(ValueError, match="served projection"):
        state_builder.build_from_disk(root=root, generated_at=DISK_STATE_AT_LATER)
    assert target.read_bytes() == before
    assert not list(root.glob(".state_bundle.json.*.tmp"))

    # No served projection at all is the same refusal, never an empty bundle.
    served.write_bytes(good_projection)
    served.unlink()
    with pytest.raises(ValueError, match="served projection"):
        state_builder.build_from_disk(root=root, generated_at=DISK_STATE_AT_LATER)
    assert target.read_bytes() == before
    assert not list(root.glob(".state_bundle.json.*.tmp"))


# ---------------------------------------------------------------------------
# Gate 6 — the health horizon must bind the generation
# ---------------------------------------------------------------------------


def test_u1_health_horizon_must_bind_the_generation(tmp_path):
    assert state_builder._read_bound_health is projection_builder._read_bound_health
    root, _ = _disk_bundle(tmp_path)
    target = root / "state_bundle.json"
    before = target.read_bytes()

    _rewrite_json(
        root / "health.json",
        lambda value: value["horizon"].update(
            {"compiler_generation_id": "generation:cs:" + "d" * 24}
        ),
    )
    with pytest.raises(ValueError, match="does not bind verified generation"):
        state_builder.build_from_disk(root=root, generated_at=DISK_STATE_AT_LATER)
    assert target.read_bytes() == before
    assert not list(root.glob(".state_bundle.json.*.tmp"))


# ---------------------------------------------------------------------------
# Gate 7 — publication is atomic and the last good bundle survives
# ---------------------------------------------------------------------------


def test_u1_publish_is_atomic_and_last_good_survives_a_failed_build(tmp_path, monkeypatch):
    assert state_builder._atomic_write_one is projection_builder._atomic_write_one
    root, summary = _disk_bundle(tmp_path)
    target = root / "state_bundle.json"
    before = target.read_bytes()
    assert summary["out_path"] == str(target)
    assert summary["byte_length"] == len(before)

    def explode(*args, **kwargs):
        raise OSError("rename denied")

    monkeypatch.setattr(projection_builder.os, "replace", explode)
    with pytest.raises(OSError):
        state_builder.build_from_disk(root=root, generated_at=DISK_STATE_AT_LATER)
    assert target.read_bytes() == before
    assert not list(root.glob(".state_bundle.json.*.tmp"))
    monkeypatch.undo()

    def refuse(*args, **kwargs):
        raise ContractViolation("state bundle withheld")

    monkeypatch.setattr(state_builder, "validate_state_bundle", refuse)
    with pytest.raises(ContractViolation):
        state_builder.build_from_disk(root=root, generated_at=DISK_STATE_AT_LATER)
    assert target.read_bytes() == before
    assert not list(root.glob(".state_bundle.json.*.tmp"))
    monkeypatch.undo()

    again = state_builder.build_from_disk(root=root, generated_at=DISK_STATE_AT_LATER)
    assert again["generation_id"] == summary["generation_id"]
    assert target.read_bytes() != before
    validate_state_bundle(json.loads(target.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Gate 8 — three horizons stay independent (A03)
# ---------------------------------------------------------------------------


def test_u1_three_horizons_stay_independent(pack):
    events, edges = _two_issuer_rows()
    _, _, bundle = _built(events, edges, [ISSUER_ONE, ISSUER_TWO], rule_pack=pack)
    horizons = bundle["horizons"]
    assert set(horizons) == {
        "source_observation_horizon",
        "material_filing_horizon",
        "generation_age_seconds",
        "freshness_sla_hours",
    }
    assert horizons["source_observation_horizon"] == max(
        event["point_in_time"]["available_at"] for event in events
    )
    assert horizons["material_filing_horizon"] == max(
        event["filing"]["filing_date"] for event in events
    )
    age = horizons["generation_age_seconds"]
    assert isinstance(age, int) and not isinstance(age, bool)
    assert age == (6 * 60 * 60)
    assert horizons["freshness_sla_hours"] == HEALTH["horizon"]["target_sla_hours"]
    assert horizons["source_observation_horizon"] != horizons["material_filing_horizon"]

    degraded = _built(
        events,
        edges,
        [ISSUER_ONE, ISSUER_TWO],
        rule_pack=pack,
        status="degraded",
        extra={
            "throughput": {"events_per_second": 12, "sessions": 3},
            "counts": {"event_versions": len(events), "event_edges": len(edges)},
        },
    )[2]
    assert degraded["horizons"] == horizons
    assert degraded["generation_id"] != bundle["generation_id"]

    empty = _built([], [], [], rule_pack=pack)[2]
    assert empty["horizons"]["source_observation_horizon"] is None
    assert empty["horizons"]["material_filing_horizon"] is None
    assert empty["horizons"]["generation_age_seconds"] == (6 * 60 * 60)
    assert empty["coverage"]["issuer_count"] == 0


# ---------------------------------------------------------------------------
# Gate 9 — the then-known view filters on system available_at
# ---------------------------------------------------------------------------


def test_u1_then_known_view_filters_on_system_available_at_and_keeps_generation_id(pack):
    events, edges = _two_issuer_rows()
    generation, projection, bundle = _built(
        events, edges, [ISSUER_ONE, ISSUER_TWO], rule_pack=pack
    )
    published = json.dumps(bundle, sort_keys=True)
    current = _state_record(bundle, ISSUER_ONE)
    whole = _whole_inputs(generation, projection)
    inputs = inputs_for_issuer(whole, ISSUER_ONE)

    derived = then_known_state(current, inputs, cutoff=CUTOFF, rule_pack=pack)
    record = derived.as_record()
    assert record["request"]["view_mode"] == "then_known"
    assert record["as_of"] == CUTOFF
    assert record["request"]["input_generations"] == current["request"]["input_generations"]
    assert record["projection_generation_id"] == current["projection_generation_id"]
    assert record["state_id"] != current["state_id"]
    assert record["unavailable"] == sorted(INHERITED_UNAVAILABLE_CAPABILITIES)

    surviving = [
        event
        for event in inputs.events
        if event["point_in_time"]["available_at"] <= CUTOFF
    ]
    assert [event["event_id"] for event in surviving] == [
        event["event_id"] for event in events[:2]
    ]
    surviving_ids = {event["event_id"] for event in surviving}
    expected_inputs = CapitalInputs(
        bindings=inputs.bindings,
        events=tuple(surviving),
        edges=tuple(
            edge
            for edge in inputs.edges
            if edge["from_event_id"] in surviving_ids
            and edge["to_event_id"] in surviving_ids
        ),
    )
    expected = integrate_registration_paths(
        expected_inputs, as_of=CUTOFF, generated_at=GENERATED_AT, rule_pack=pack
    )
    assert derived.family("registration").as_record() == expected.family_state().as_record()
    assert record["receipt"]["input_digest"] == expected_inputs.input_digest
    assert record["receipt"]["input_digest"] != current["receipt"]["input_digest"]
    assert [row["path_id"] for row in record["families"][0]["records"]] != [
        row["path_id"] for row in current["families"][0]["records"]
    ]

    # The derivation is read-only: the published bundle is byte-identical.
    assert json.dumps(bundle, sort_keys=True) == published
    assert bundle["generation_id"] == json.loads(published)["generation_id"]
    assert then_known_state(
        current, inputs, cutoff=CUTOFF, rule_pack=pack
    ).as_record() == record

    with pytest.raises(ValueError, match="cannot exceed the published as_of"):
        then_known_state(
            current, inputs, cutoff="2026-10-15T00:00:00Z", rule_pack=pack
        )


# ---------------------------------------------------------------------------
# Gate 10 — nothing available after the cutoff is "unknown at date"
# ---------------------------------------------------------------------------


def test_u1_then_known_shows_nothing_available_after_the_cutoff(pack):
    events, edges = _s1_filed_amended_effective_withdrawn()
    late_shelf = _event(
        61,
        "S-3",
        accepted_at="2026-09-01T10:00:00Z",
        seen_at="2026-09-02T00:00:00Z",
        file_number="333-999",
    )
    rows = [*events, late_shelf]
    generation, projection, bundle = _built(rows, edges, [ISSUER_ONE], rule_pack=pack)
    current = _state_record(bundle, ISSUER_ONE)
    whole = _whole_inputs(generation, projection)
    inputs = inputs_for_issuer(whole, ISSUER_ONE)

    paths = {row["lifecycle_id"]: row for row in current["families"][0]["records"]}
    assert len(paths) == 2
    late_path = next(
        row for row in paths.values() if row["origin"]["event_id"] == late_shelf["event_id"]
    )
    s1_path = next(row for row in paths.values() if row is not late_path)

    derived = then_known_state(current, inputs, cutoff=CUTOFF, rule_pack=pack)
    derived_ids = {
        row["lifecycle_id"] for row in derived.family("registration").records
    }
    assert s1_path["lifecycle_id"] in derived_ids
    assert late_path["lifecycle_id"] not in derived_ids

    missing = not_yet_observed(current, derived, inputs)
    assert [row["lifecycle_id"] for row in missing] == [late_path["lifecycle_id"]]
    entry = missing[0]
    assert entry["status"] == "unknown_at_date"
    assert entry["path_id"] == late_path["path_id"]
    assert entry["first_available_at"] == late_shelf["point_in_time"]["available_at"]
    assert entry["first_available_at"] > CUTOFF
    assert set(entry) == {
        "path_id",
        "lifecycle_id",
        "first_available_at",
        "status",
    }
    assert not_yet_observed(current, derived.as_record(), inputs) == missing

    # Before ANY of them was observed, both lifecycles are unknown at date.
    early = then_known_state(current, inputs, cutoff="2026-07-01T00:00:00Z", rule_pack=pack)
    assert early.family("registration").records == ()
    nothing_yet = not_yet_observed(current, early, inputs)
    assert sorted(row["lifecycle_id"] for row in nothing_yet) == sorted(paths)
    assert all(row["status"] == "unknown_at_date" for row in nothing_yet)
    assert [row["first_available_at"] for row in nothing_yet] == sorted(
        row["first_available_at"] for row in nothing_yet
    )


# ---------------------------------------------------------------------------
# Gate 11 — the coverage denominator is explicit (A33)
# ---------------------------------------------------------------------------


def test_u1_coverage_denominator_is_explicit(pack):
    events, edges = _two_issuer_rows()
    generation, projection, bundle = _built(
        events, edges, [ISSUER_ONE, ISSUER_TWO], rule_pack=pack
    )
    routes = sorted(rule_id for rule_id in pack.rules if rule_id.startswith(S3_ROUTE_PREFIX))
    assert len(routes) > 1, "the pack must declare more than one shelf route"

    whole = _whole_inputs(generation, projection)
    shelf_inputs = inputs_for_issuer(whole, ISSUER_TWO)
    shelf = integrate_registration_paths(
        shelf_inputs, as_of=AS_OF, generated_at=GENERATED_AT, rule_pack=pack
    ).family_state()
    coverage = coverage_for(shelf, rule_pack=pack)
    assert coverage["total"] == len(routes)
    assert coverage["routes"] == routes
    assert coverage["examined"] == 0
    assert coverage["no_active_path"] is False
    assert "eligibility_route_not_evaluated" in coverage["unexamined_reason_codes"]
    for code in shelf.provenance.support_limits:
        assert code in coverage["unexamined_reason_codes"]
    assert coverage["unexamined_reason_codes"] == sorted(
        set(coverage["unexamined_reason_codes"])
    )

    ineligible = {rule_id: "ineligible" for rule_id in routes}
    closed = coverage_for(shelf, rule_pack=pack, route_verdicts=ineligible)
    assert closed["examined"] == closed["total"] == len(routes)
    assert closed["no_active_path"] is True
    assert "eligibility_route_not_evaluated" not in closed["unexamined_reason_codes"]

    one_eligible = dict(ineligible)
    one_eligible[routes[0]] = "eligible"
    assert coverage_for(shelf, rule_pack=pack, route_verdicts=one_eligible)[
        "no_active_path"
    ] is False

    subset = {routes[0]: "ineligible"}
    partial = coverage_for(shelf, rule_pack=pack, route_verdicts=subset)
    assert partial["examined"] == 1 < partial["total"]
    assert partial["no_active_path"] is False
    assert "eligibility_route_not_evaluated" in partial["unexamined_reason_codes"]

    deferred = coverage_for(
        shelf, rule_pack=pack, deferred=({"reason": "missing_file_number"},)
    )
    assert "deferred:missing_file_number" in deferred["unexamined_reason_codes"]

    s1_inputs = inputs_for_issuer(whole, ISSUER_ONE)
    s1 = integrate_registration_paths(
        s1_inputs, as_of=AS_OF, generated_at=GENERATED_AT, rule_pack=pack
    ).family_state()
    non_shelf = coverage_for(s1, rule_pack=pack)
    assert non_shelf["total"] == 0
    assert non_shelf["routes"] == []
    assert non_shelf["examined"] == 0
    assert non_shelf["no_active_path"] is False
    assert "no_shelf_form_family_observed" in non_shelf["unexamined_reason_codes"]

    index = bundle["issuer_index"][ISSUER_TWO]["coverage"]["registration"]
    assert index["total"] == len(routes)
    assert index["examined"] == 0
    assert index["no_active_path"] is False
    family_coverage = bundle["coverage"]["families"]["registration"]
    assert set(family_coverage) == {
        "support",
        "examined",
        "total",
        "unexamined_reason_codes",
    }
    assert family_coverage["total"] == len(routes)
    assert family_coverage["examined"] == 0
    assert "no_shelf_form_family_observed" in family_coverage["unexamined_reason_codes"]
    assert "eligibility_route_not_evaluated" in family_coverage["unexamined_reason_codes"]


# ---------------------------------------------------------------------------
# Supporting gates: evidence index, round trip, tickers, refusals
# ---------------------------------------------------------------------------


def test_u1_evidence_index_publishes_accession_specific_anchors_only(pack):
    events, edges = _s1_filed_amended_effective_withdrawn()
    _, _, unresolved = _built(events, edges, [ISSUER_ONE], rule_pack=pack)
    keys = _evidence_keys_of(unresolved)
    assert keys and set(unresolved["evidence_index"]) == keys
    for key, entry in unresolved["evidence_index"].items():
        assert key == f"{entry['manifest_id']}/{entry['span_id']}"
        assert entry["anchor"] is None
        assert entry["reason"] == "manifest_unresolved"
        assert entry["grade"] == "unknown"
        assert entry["ledger_text_sha256"] is None
        assert entry["document"] == {"sequence": None, "filename": None}
        assert "excerpt" not in entry
        assert set(entry) == {
            "manifest_id",
            "span_id",
            "text_sha256",
            "ledger_text_sha256",
            "filing",
            "document",
            "anchor",
            "reason",
            "grade",
            "issuer_id",
            "event_ids",
            "path_ids",
            "available_at",
        }
        assert entry["issuer_id"] == ISSUER_ONE
        assert entry["filing"]["filed_at"]
        assert entry["available_at"]["system"]
        assert entry["text_sha256"]

    first = events[0]["evidence"][0]
    row = _manifest(role="primary")
    resolved_row = {
        **row,
        "manifest_id": first["manifest_id"],
        "spans": [{**row["spans"][0], "span_id": first["span_id"]}],
    }
    _, _, resolved = _built(
        events, edges, [ISSUER_ONE], rule_pack=pack, manifests=[resolved_row]
    )
    entry = resolved["evidence_index"][f"{first['manifest_id']}/{first['span_id']}"]
    assert entry["anchor"] == resolved_row["document"]["canonical_url"]
    assert entry["anchor"].startswith("https://")
    assert "/Archives/" in entry["anchor"]
    assert resolved_row["filing"]["accession"] in entry["anchor"]
    assert entry["reason"] is None
    assert entry["grade"] == resolved_row["rights"]["redistribution_class"]
    assert entry["ledger_text_sha256"] == resolved_row["spans"][0]["text_sha256"]
    assert entry["document"] == {
        "sequence": resolved_row["document"]["sequence"],
        "filename": resolved_row["document"]["document_name"],
    }
    assert entry["filing"] == {
        "accession": resolved_row["filing"]["accession"],
        "form": resolved_row["filing"]["form"],
        "filed_at": resolved_row["filing"]["filing_date"],
    }
    assert entry["event_ids"] == [events[0]["event_id"]]
    # The other cited manifests are still absent from the ledger and still kept.
    kept = [key for key, value in resolved["evidence_index"].items() if value["anchor"] is None]
    assert kept and all(
        resolved["evidence_index"][key]["reason"] == "manifest_unresolved" for key in kept
    )

    origin = resolved_row["document"]["canonical_url"].split("/Archives/")[0] + "/"
    generic_row = {
        **resolved_row,
        "document": {**resolved_row["document"], "canonical_url": origin},
    }
    _, _, generic = _built(
        events, edges, [ISSUER_ONE], rule_pack=pack, manifests=[generic_row]
    )
    generic_entry = generic["evidence_index"][
        f"{first['manifest_id']}/{first['span_id']}"
    ]
    assert generic_entry["anchor"] is None
    assert generic_entry["reason"] == "anchor_not_accession_specific"
    assert generic_entry["grade"] == resolved_row["rights"]["redistribution_class"]
    assert generic_entry["filing"]["accession"] == resolved_row["filing"]["accession"]
    for value in generic["evidence_index"].values():
        assert "excerpt" not in value
        assert value["anchor"] is None or "/Archives/" in value["anchor"]


def test_u1_state_from_record_round_trips_and_refuses_a_tampered_field(pack):
    events, edges = _two_issuer_rows()
    generation, projection, bundle = _built(
        events, edges, [ISSUER_ONE, ISSUER_TWO], rule_pack=pack
    )
    record = _state_record(bundle, ISSUER_ONE)
    rebuilt = state_from_record(record)
    assert rebuilt.as_record() == record
    assert rebuilt.state_id == record["state_id"]

    tampered = json.loads(json.dumps(record))
    tampered["receipt"]["input_digest"] = sha256_of("another issuer's rows")
    with pytest.raises(ContractViolation):
        state_from_record(tampered)

    widened = json.loads(json.dumps(record))
    widened["authority"] = {**widened["authority"], "rank_authority": True}
    with pytest.raises(ContractViolation):
        validate_state_bundle({**bundle, "issuers": [widened]})

    renamed = json.loads(json.dumps(bundle))
    renamed["issuers"].append(json.loads(json.dumps(record)))
    with pytest.raises(ContractViolation, match="twice"):
        validate_state_bundle(renamed)

    rebound = json.loads(json.dumps(bundle))
    rebound["as_of"] = "2026-10-13T00:00:00Z"
    with pytest.raises(ContractViolation):
        validate_state_bundle(rebound)

    assert state_bundle_module.issuer_inputs(
        bundle, generation, ISSUER_TWO
    ).input_digest == _state_record(bundle, ISSUER_TWO)["receipt"]["input_digest"]


def test_u1_ticker_observations_collapse_to_transitions(pack):
    events, edges = _s1_filed_amended_effective_withdrawn()
    rows = [
        *events,
        _event(
            71,
            "S-3",
            accepted_at="2026-08-06T10:00:00Z",
            seen_at="2026-08-06T12:00:00Z",
            file_number="333-555",
            ticker="XYZ",
        ),
        _event(
            72,
            "S-3",
            accepted_at="2026-08-07T10:00:00Z",
            seen_at="2026-08-07T12:00:00Z",
            file_number="333-556",
            ticker="XYZ",
        ),
        _event(
            73,
            "S-3",
            accepted_at="2026-08-08T10:00:00Z",
            seen_at="2026-08-08T12:00:00Z",
            file_number="333-557",
            ticker="ABC",
        ),
    ]
    _, _, bundle = _built(rows, edges, [ISSUER_ONE], rule_pack=pack)
    observed = bundle["issuer_index"][ISSUER_ONE]["ticker_observations"]
    assert [row["ticker"] for row in observed] == ["ABC", "XYZ", "ABC"]
    assert [row["first_observed_at"] for row in observed] == sorted(
        row["first_observed_at"] for row in observed
    )
    assert observed[0]["event_id"] == events[0]["event_id"]
    assert observed[0]["accession"] == events[0]["filing"]["accession"]
    assert all(set(row) == {"ticker", "first_observed_at", "event_id", "accession"} for row in observed)


def test_u1_bundle_refuses_a_generation_or_an_edge_it_cannot_bind(pack):
    events, edges = _two_issuer_rows()
    generation = _generation(events, edges)
    projection = _projection(generation, [ISSUER_ONE, ISSUER_TWO])

    missing = VerifiedProjectionGeneration(
        tuple(events), tuple(edges), (), {**generation.telemetry, "generation_id": None}
    )
    with pytest.raises(ValueError, match="no verified capital-structure generation"):
        build_state_bundle(
            generation=missing,
            projection=_projection(missing, [ISSUER_ONE]),
            health=HEALTH,
            rule_pack=pack,
            as_of=AS_OF,
            generated_at=GENERATED_AT,
            projection_sha256=sha256_of(projection),
        )
    with pytest.raises(ValueError, match="no verified capital-structure generation"):
        build_capital_inputs(missing, projection, projection_sha256=sha256_of(projection))

    crossed = _generation(
        events,
        [*edges, _edge(events[0], events[-1], "amendment_of")],
    )
    with pytest.raises(ValueError, match="cross-issuer event edge is forbidden"):
        build_capital_inputs(
            crossed,
            _projection(crossed, [ISSUER_ONE, ISSUER_TWO]),
            projection_sha256=sha256_of(projection),
        )

    with pytest.raises(ValueError, match="cannot precede"):
        build_state_bundle(
            generation=generation,
            projection=projection,
            health=HEALTH,
            rule_pack=pack,
            as_of=AS_OF,
            generated_at="2026-10-13T00:00:00Z",
            projection_sha256=sha256_of(projection),
        )
    with pytest.raises(ValueError, match="health horizon is required"):
        build_state_bundle(
            generation=generation,
            projection=projection,
            health={},
            rule_pack=pack,
            as_of=AS_OF,
            generated_at=GENERATED_AT,
            projection_sha256=sha256_of(projection),
        )


def test_u1_bundle_envelope_carries_the_frozen_versions_and_authority(pack):
    events, edges = _two_issuer_rows()
    _, _, bundle = _built(events, edges, [ISSUER_ONE, ISSUER_TWO], rule_pack=pack)
    assert bundle["schema"] == STATE_BUNDLE_SCHEMA
    assert bundle["bundle_version"] == STATE_BUNDLE_VERSION
    assert bundle["contract_version"] == STATE_CONTRACT_VERSION
    assert bundle["authority"] == AUTHORITY
    assert bundle["rule_pack"] == {
        "rule_pack_id": pack.rule_pack_id,
        "rule_pack_version": pack.version,
        "rule_pack_digest": pack.file_sha256,
    }
    assert set(bundle) == {
        "schema",
        "contract_version",
        "bundle_version",
        "generation_id",
        "as_of",
        "generated_at",
        "projection_generation_id",
        "input_generations",
        "rule_pack",
        "horizons",
        "coverage",
        "unavailable",
        "capabilities_proven",
        "issuers",
        "issuer_index",
        "evidence_index",
        "authority",
    }
    assert sorted(bundle["issuer_index"]) == [ISSUER_ONE, ISSUER_TWO]
    for row in bundle["issuers"]:
        assert row["request"]["view_mode"] == "current"
        assert row["request"]["rule_pack_id"] == pack.rule_pack_id
    # A supply, cash or ranking number has nowhere to live (SPEC §10): the
    # envelope is closed and every property name is checked against the frozen
    # forbidden-property pattern.
    smuggled = json.loads(json.dumps(bundle))
    smuggled["horizons"]["runway"] = 1
    with pytest.raises(ContractViolation):
        validate_state_bundle(smuggled)
    renamed = json.loads(json.dumps(bundle))
    renamed["generation_id"] = "state_bundle:cs:" + "0" * 32
    with pytest.raises(ContractViolation, match="does not match its inputs"):
        validate_state_bundle(renamed)
