"""U1C — the document-term fee rows sealed into the Capital Structure state bundle.

The ledger is built here with pandas from rows shaped exactly like the sealed
compiler's records (every key of ``engine/capital_structure/document_terms.py``
record construction), so the state contract's own key law accepts them.  No
digest or id is hard-coded: every expectation is derived from the fixture rows,
the rule pack or the frozen contract constants.  The event/edge fixtures, the
disk fixture and the in-memory generation/projection builders are reused BY
IMPORT from the existing suites, never re-implemented.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd
import pytest

from engine.capital_structure import capacity as c1
from engine.capital_structure import rule_applicability as ra
from engine.capital_structure.capacity import explain_capacity
from engine.capital_structure.issuer_state_contracts import (
    ContractViolation,
    FinancingScenario,
    PriceAssumption,
    sha256_of,
)
from engine.capital_structure.registration_integration import (
    REGISTRATION_PATH_SCHEMA,
    REGISTRATION_FAMILY,
    integrate_registration_paths,
)
from engine.capital_structure.state_bundle import (
    DOCUMENT_LEDGER_FILENAME,
    DOCUMENT_TERMS_FAMILY,
    FEE_TABLE_TERM_NAME,
    build_capital_inputs,
    build_state_bundle,
    issuer_inputs,
    read_document_terms_ledger,
    stable_id,
    state_from_record,
    then_known_state,
    validate_state_bundle,
)
from engine.capital_structure.verified_projection_generation import (
    read_verified_projection_generation,
)
import scripts.build_capital_structure_projection as projection_builder
import scripts.build_capital_structure_state as state_builder
from tests.test_build_capital_structure_projection import _compiled_root
from tests.test_capital_structure_registration_integration import (
    AS_OF,
    GENERATED_AT,
    _s3_amended_effective_post_effective,
)
from tests.test_capital_structure_state_bundle import (
    DISK_PROJECTION_AT,
    DISK_STATE_AT,
    HEALTH,
    ISSUER_ONE,
    _generation,
    _projection,
    _state_record,
)


ISSUER = ISSUER_ONE
#: The S-3 origin accession of the integration suite's
#: ``_s3_amended_effective_post_effective`` fixture (suffix 11, correction 1).
ACC = "0000000001-26-000011"
MANIFEST = "manifest:cs-fee-table:" + "7" * 40
SALE = AS_OF[:10]
#: Between the fee row v1 (2026-08-02T05:00:00Z) and its correction v2
#: (2026-08-06T00:00:00Z), so the correction is genuinely not yet observed.
CUTOFF_EARLY = "2026-08-05T00:00:00Z"
V1_AVAILABLE_AT = "2026-08-02T05:00:00Z"
V1_SOURCE_AT = "2026-08-01T21:00:00Z"
V2_AVAILABLE_AT = "2026-08-06T00:00:00Z"
V2_SOURCE_AT = "2026-08-05T21:00:00Z"

LEDGER_COLUMNS = [
    "observation_id", "logical_observation_id", "issuer_id", "accession", "form",
    "source_manifest_id", "term_name", "state", "available_at",
    "correction_version", "observation_json",
]


@pytest.fixture(scope="module")
def pack():
    return ra.load_rule_applicability_pack()


# ---------------------------------------------------------------------------
# Fixture ledger rows: the sealed compiler's own record shape
# ---------------------------------------------------------------------------


def _fee_observation(
    name: str,
    *,
    value: str | None,
    available_at: str,
    source_available_at: str,
    issuer_id: str = ISSUER,
    accession: str = ACC,
    disposition: str = "observed",
    correction_version: int = 1,
    correction_of: str | None = None,
) -> dict[str, Any]:
    """One ledger row with every key the document-term compiler writes."""
    return {
        "schema": c1.DOCUMENT_TERM_SCHEMA,
        "observation_id": f"document-term:cs:{name}",
        "logical_observation_id": f"document-term-logical:cs:{name}",
        "issuer_id": issuer_id,
        "filing": {
            "accession": accession,
            "form": "S-3",
            "filing_date": source_available_at[:10],
            "accepted_at": source_available_at,
        },
        "document": {
            "source_manifest_id": MANIFEST,
            "source_id": accession,
            "document_role": "complete_submission",
            "canonical_url": f"https://www.sec.gov/Archives/edgar/data/1/{accession}.htm",
            "content_sha256": "a" * 64,
            "child_document_type": None,
            "child_sequence": None,
            "child_filename": None,
            "child_text_start": None,
            "child_text_end": None,
        },
        "security": {
            "row_id": f"row:{name}",
            "table_index": 1,
            "row_index": 1,
            "title_raw": "Common stock",
            "title_normalized": "common_stock",
            "classification": "common_stock",
        },
        "term": {
            "name": FEE_TABLE_TERM_NAME,
            "term_type": "amount",
            "scope": "registration_fee_table_row",
        },
        "state": {"disposition": disposition, "reason": "fee_table_row_transcribed"},
        "reported": {"raw_text": None if value is None else f"${value}"},
        # The first slice is a unit-preserving transcription, not a conversion.
        "normalized": {"value": value, "unit": "USD", "currency": "USD", "scale": "1"},
        "evidence": {
            "source_manifest_id": MANIFEST,
            "spans": [
                {
                    "manifest_id": MANIFEST,
                    "span_id": f"span:{name}",
                    "locator_type": "text_range",
                    "locator": "fee table",
                    "text_sha256": "b" * 64,
                }
            ],
        },
        "extraction": {
            "method": "deterministic",
            "parser_version": "document-terms/1.0.0",
            "review_status": "unreviewed",
        },
        "relationships": {
            "amends": [],
            "supersedes": [] if correction_of is None else [correction_of],
            "contradiction_ids": [],
        },
        "point_in_time": {
            "source_available_at": source_available_at,
            "available_at": available_at,
        },
        "version": {
            "immutable_record": True,
            "correction_version": correction_version,
            "correction_of": correction_of,
        },
    }


def _standard_ledger() -> list[dict[str, Any]]:
    """One observed row, its later correction, and one ambiguous row."""
    observed = _fee_observation(
        "fee-a",
        value="50000000",
        available_at=V1_AVAILABLE_AT,
        source_available_at=V1_SOURCE_AT,
    )
    ambiguous = _fee_observation(
        "fee-b",
        value=None,
        available_at=V1_AVAILABLE_AT,
        source_available_at=V1_SOURCE_AT,
        disposition="ambiguous",
    )
    correction = _fee_observation(
        "fee-a",
        value="60000000",
        available_at=V2_AVAILABLE_AT,
        source_available_at=V2_SOURCE_AT,
        correction_version=2,
        correction_of=str(observed["observation_id"]),
    )
    return [observed, ambiguous, correction]


def _write_ledger(path: Path, observations: Sequence[dict[str, Any]]) -> Path:
    """The nightly's ledger shape: one canonical observation_json per row."""
    rows = []
    for observation in observations:
        rows.append(
            {
                "observation_id": observation["observation_id"],
                "logical_observation_id": observation["logical_observation_id"],
                "issuer_id": observation["issuer_id"],
                "accession": observation["filing"]["accession"],
                "form": observation["filing"]["form"],
                "source_manifest_id": observation["document"]["source_manifest_id"],
                "term_name": observation["term"]["name"],
                "state": observation["state"]["disposition"],
                "available_at": observation["point_in_time"]["available_at"],
                "correction_version": int(observation["version"]["correction_version"]),
                "observation_json": json.dumps(
                    observation, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ),
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=LEDGER_COLUMNS).to_parquet(path, index=False)
    return path


def _bundle(
    events,
    edges,
    pack,
    *,
    ledger_path: Path | None = None,
    as_of: str = AS_OF,
    generated_at: str = GENERATED_AT,
):
    """One validated bundle over the S-3 fixture, sealed with the ledger if given."""
    generation = _generation(events, edges)
    projection = _projection(generation, [ISSUER])
    document_terms = (
        read_document_terms_ledger(ledger_path) if ledger_path is not None else None
    )
    bundle = build_state_bundle(
        generation=generation,
        projection=projection,
        health=HEALTH,
        rule_pack=pack,
        as_of=as_of,
        generated_at=generated_at,
        projection_sha256=sha256_of(projection),
        document_terms=document_terms,
    )
    validate_state_bundle(bundle)
    return generation, projection, bundle


def _fee_rows(records: Iterable[Any]) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in records
        if isinstance(row, dict) and row.get("schema") == c1.DOCUMENT_TERM_SCHEMA
    ]


def _family_record_of(state_record: dict[str, Any]) -> dict[str, Any]:
    return next(
        row for row in state_record["families"] if row["family"] == REGISTRATION_FAMILY
    )


def _path_records_of(records: Iterable[Any]) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in records
        if isinstance(row, dict) and row.get("schema") == REGISTRATION_PATH_SCHEMA
    ]


def _scenario() -> FinancingScenario:
    return FinancingScenario(
        view="then_known",
        as_of=AS_OF,
        horizon_start=SALE,
        horizon_end="2026-12-31",
        price=PriceAssumption(kind="fixed", fixed_price="2.00"),
        other_assumptions=(
            ("exchange_offering_treatment", "non_public"),
            ("listing_venue", "nasdaq"),
            ("price_relative_to_minimum_price", "below"),
        ),
        fee_rate="0.01",
        discount_rate="0.02",
    )


# ---------------------------------------------------------------------------
# Sealing: the fourth binding and the family's fee rows
# ---------------------------------------------------------------------------


def test_fee_term_constant_is_the_capacity_one():
    assert FEE_TABLE_TERM_NAME == c1.FEE_TABLE_TERM_NAME
    assert FEE_TABLE_TERM_NAME == "proposed_maximum_aggregate_offering_price"


def test_ledger_seals_a_fourth_binding_and_both_dispositions(pack, tmp_path):
    events, edges = _s3_amended_effective_post_effective()
    rows = _standard_ledger()
    ledger = _write_ledger(tmp_path / DOCUMENT_LEDGER_FILENAME, rows)
    sha = hashlib.sha256(ledger.read_bytes()).hexdigest()
    _, _, bundle = _bundle(events, edges, pack, ledger_path=ledger)

    assert [row["input_family"] for row in bundle["input_generations"]] == [
        "events",
        "event_edges",
        "event_projection",
        DOCUMENT_TERMS_FAMILY,
    ]
    binding = next(
        row
        for row in bundle["input_generations"]
        if row["input_family"] == DOCUMENT_TERMS_FAMILY
    )
    assert binding["support"] == "partial"
    assert binding["schema"] == c1.DOCUMENT_TERM_SCHEMA
    assert binding["artifact_sha256"] == sha
    assert binding["as_of"] == max(
        row["point_in_time"]["available_at"] for row in rows
    )
    assert binding["generation_id"] == stable_id("document_terms", {"artifact_sha256": sha})

    # The binding's selection seals BOTH dispositions; the family carries the
    # CURRENT version of each logical row after the paths.
    family = _family_record_of(_state_record(bundle, ISSUER))
    fee = _fee_rows(family["records"])
    assert [row["logical_observation_id"] for row in fee] == [
        "document-term-logical:cs:fee-a",
        "document-term-logical:cs:fee-b",
    ]
    assert fee[0]["version"]["correction_version"] == 2
    assert fee[0]["normalized"]["value"] == "60000000"
    assert fee[1]["state"]["disposition"] == "ambiguous"
    assert _path_records_of(family["records"]), "the paths must come first"
    assert family["records"][-len(fee):] == fee


def test_capacity_reads_the_sealed_registered_amount_as_known(pack, tmp_path):
    events, edges = _s3_amended_effective_post_effective()
    ledger = _write_ledger(tmp_path / DOCUMENT_LEDGER_FILENAME, _standard_ledger())
    _, _, bundle = _bundle(events, edges, pack, ledger_path=ledger)
    state = state_from_record(_state_record(bundle, ISSUER))
    built = ra.build_rule_pack(pack, SALE)[0]
    assert built is not None, f"no qualified rule text on {SALE}"
    evaluation = explain_capacity(state, _scenario(), built, pack=pack)
    bound = [
        row
        for row in evaluation.inputs["registration_paths"]
        if row.get("fee_table_accession") == ACC
    ]
    assert bound, f"no path bound to the fixture fee row: {evaluation.inputs['registration_paths']}"
    assert all(row["registered_amount"]["status"] == "known" for row in bound)
    assert all(row["registered_amount"]["value"] == "60000000" for row in bound)


def test_a_correction_after_the_cutoff_is_invisible_then_visible(pack, tmp_path):
    events, edges = _s3_amended_effective_post_effective()
    ledger = _write_ledger(tmp_path / DOCUMENT_LEDGER_FILENAME, _standard_ledger())
    generation, _, bundle = _bundle(events, edges, pack, ledger_path=ledger)
    record = _state_record(bundle, ISSUER)
    inputs = issuer_inputs(bundle, generation, ISSUER, document_terms_ledger=ledger)

    early = then_known_state(record, inputs, cutoff=CUTOFF_EARLY, rule_pack=pack)
    early_fee = _fee_rows(early.family(REGISTRATION_FAMILY).records)
    assert [row["version"]["correction_version"] for row in early_fee] == [1, 1]
    assert early_fee[0]["normalized"]["value"] == "50000000"

    late = then_known_state(record, inputs, cutoff=AS_OF, rule_pack=pack)
    late_fee = _fee_rows(late.family(REGISTRATION_FAMILY).records)
    assert [row["version"]["correction_version"] for row in late_fee] == [2, 1]
    assert late_fee[0]["normalized"]["value"] == "60000000"


def test_changed_ledger_bytes_refuse_the_reader(pack, tmp_path):
    events, edges = _s3_amended_effective_post_effective()
    ledger = _write_ledger(tmp_path / DOCUMENT_LEDGER_FILENAME, _standard_ledger())
    generation, _, bundle = _bundle(events, edges, pack, ledger_path=ledger)
    raw = bytearray(ledger.read_bytes())
    raw[len(raw) // 2] ^= 0xFF
    ledger.write_bytes(bytes(raw))
    with pytest.raises(ContractViolation, match="document_terms_artifact_mismatch"):
        issuer_inputs(bundle, generation, ISSUER, document_terms_ledger=ledger)


def test_input_digest_reproduces_across_two_builds(pack, tmp_path):
    events, edges = _s3_amended_effective_post_effective()
    ledger = _write_ledger(tmp_path / DOCUMENT_LEDGER_FILENAME, _standard_ledger())
    document_terms = read_document_terms_ledger(ledger)
    generation = _generation(events, edges)
    projection = _projection(generation, [ISSUER])
    kwargs = dict(
        generation=generation,
        projection=projection,
        health=HEALTH,
        rule_pack=pack,
        as_of=AS_OF,
        generated_at=GENERATED_AT,
    )
    first = build_state_bundle(
        projection_sha256=sha256_of(projection), document_terms=document_terms, **kwargs
    )
    second = build_state_bundle(
        projection_sha256=sha256_of(projection), document_terms=document_terms, **kwargs
    )
    published_first = _state_record(first, ISSUER)["receipt"]["input_digest"]
    assert published_first == _state_record(second, ISSUER)["receipt"]["input_digest"]
    inputs = issuer_inputs(first, generation, ISSUER, document_terms_ledger=ledger)
    assert inputs.input_digest == published_first
    whole = build_capital_inputs(
        generation,
        projection,
        projection_sha256=sha256_of(projection),
        document_terms=document_terms,
    )
    assert (
        build_capital_inputs(
            generation,
            projection,
            projection_sha256=sha256_of(projection),
            document_terms=document_terms,
        ).input_digest
        == whole.input_digest
    )


# ---------------------------------------------------------------------------
# Absence, share basis and the unchanged three-binding bundle
# ---------------------------------------------------------------------------


def test_no_ledger_means_no_fourth_binding_and_a_named_absence(pack):
    events, edges = _s3_amended_effective_post_effective()
    generation, _, bundle = _bundle(events, edges, pack)
    assert [row["input_family"] for row in bundle["input_generations"]] == [
        "events",
        "event_edges",
        "event_projection",
    ]
    family = _family_record_of(_state_record(bundle, ISSUER))
    assert _fee_rows(family["records"]) == []
    assert "document_terms_ledger_absent" in family["unavailable"]
    # The reader neither reads nor requires a ledger.
    inputs = issuer_inputs(bundle, generation, ISSUER)
    assert inputs.document_terms == ()
    assert inputs.input_digest == _state_record(bundle, ISSUER)["receipt"]["input_digest"]


def test_ledgerless_registration_family_records_are_exactly_the_paths(pack):
    """Without a ledger the family's records are the integrator's own paths."""
    events, edges = _s3_amended_effective_post_effective()
    _, projection, bundle = _bundle(events, edges, pack)
    generation = _generation(events, edges)
    inputs = build_capital_inputs(
        generation, projection, projection_sha256=sha256_of(projection)
    )
    reg = integrate_registration_paths(
        inputs, as_of=AS_OF, generated_at=GENERATED_AT, rule_pack=pack
    )
    family = _family_record_of(_state_record(bundle, ISSUER))
    assert family["records"] == list(reg.family_state().records)
    assert sorted(family["unavailable"]) == sorted(
        set(reg.family_state().unavailable) | {"document_terms_ledger_absent"}
    )


def _disk_root(tmp_path: Path) -> Path:
    """One good projection build over the compiled disk fixture."""
    root = _compiled_root(tmp_path)
    projection_builder.build_from_disk(
        root=root,
        canonical_path=root / "projection.json",
        public_path=tmp_path / "site" / "latest.json",
        generated_at=DISK_PROJECTION_AT,
    )
    return root


def test_disk_bundle_as_of_covers_the_sealed_ledger(pack, tmp_path):
    """DEC:CS-V2-U1C-BUNDLE-AS-OF-COVERS-SEALED-INPUTS on the real disk path."""
    root = _disk_root(tmp_path)
    projection = json.loads((root / "projection.json").read_text(encoding="utf-8"))
    issuer_id = str(projection["records"][0]["issuer_id"])
    telemetry_as_of = json.loads((root / "telemetry.json").read_text(encoding="utf-8"))[
        "as_of"
    ]
    ledger = _write_ledger(
        root / DOCUMENT_LEDGER_FILENAME,
        [
            _fee_observation(
                "disk-fee",
                issuer_id=issuer_id,
                value="1000000",
                available_at="2026-08-03T00:00:00Z",
                source_available_at="2026-08-02T20:00:00Z",
            )
        ],
    )
    assert "2026-08-03T00:00:00Z" > telemetry_as_of

    # The sealed ledger's clock is the bundle as_of, so the build clock runs
    # after it (generated_at can never precede as_of).
    summary = state_builder.build_from_disk(root=root, generated_at="2026-08-03T06:00:00Z")
    assert summary["as_of"] == "2026-08-03T00:00:00Z"
    bundle = json.loads((root / "state_bundle.json").read_text(encoding="utf-8"))
    validate_state_bundle(bundle)
    assert bundle["input_generations"][-1]["input_family"] == DOCUMENT_TERMS_FAMILY

    # An explicit as_of is honoured unchanged, and a row available after it
    # simply stays invisible in the then-known view.
    explicit = state_builder.build_from_disk(
        root=root, as_of=telemetry_as_of, generated_at=DISK_STATE_AT
    )
    assert explicit["as_of"] == telemetry_as_of
    explicit_bundle = json.loads((root / "state_bundle.json").read_text(encoding="utf-8"))
    assert explicit_bundle["as_of"] == telemetry_as_of
    generation = read_verified_projection_generation(root)
    inputs = issuer_inputs(
        explicit_bundle, generation, issuer_id, document_terms_ledger=ledger
    )
    invisible = then_known_state(
        _state_record(explicit_bundle, issuer_id),
        inputs,
        cutoff=telemetry_as_of,
        rule_pack=pack,
    )
    assert _fee_rows(invisible.family(REGISTRATION_FAMILY).records) == []
    visible = then_known_state(
        _state_record(bundle, issuer_id),
        issuer_inputs(bundle, generation, issuer_id, document_terms_ledger=ledger),
        cutoff="2026-08-03T00:00:00Z",
        rule_pack=pack,
    )
    visible_fee = _fee_rows(visible.family(REGISTRATION_FAMILY).records)
    assert [row["normalized"]["value"] for row in visible_fee] == ["1000000"]


def test_existing_three_binding_bundle_is_unchanged(pack, tmp_path):
    """The pre-U1C disk fixture still validates, and its evidence is unperturbed."""
    root = _disk_root(tmp_path)
    telemetry_as_of = json.loads((root / "telemetry.json").read_text(encoding="utf-8"))[
        "as_of"
    ]
    summary = state_builder.build_from_disk(root=root, generated_at=DISK_STATE_AT)
    assert summary["as_of"] == telemetry_as_of
    bundle = json.loads((root / "state_bundle.json").read_text(encoding="utf-8"))
    validate_state_bundle(bundle)
    assert [row["input_family"] for row in bundle["input_generations"]] == [
        "events",
        "event_edges",
        "event_projection",
    ]
    issuer_id = str(bundle["issuers"][0]["request"]["issuer_id"])
    index = bundle["issuer_index"][issuer_id]
    coverage = index["coverage"]["registration"]
    assert coverage["support"] == "partial"
    assert coverage["examined"] == 0 and coverage["total"] == 0
    assert coverage["no_active_path"] is False
    assert "no_shelf_form_family_observed" in coverage["unexamined_reason_codes"]
    family = _family_record_of(_state_record(bundle, issuer_id))
    assert "document_terms_ledger_absent" in family["unavailable"]
    assert _fee_rows(family["records"]) == []
    path_ids = {
        str(row["path_id"]) for row in _path_records_of(family["records"])
    }
    assert set(index["path_evidence"]) == path_ids


# ---------------------------------------------------------------------------
# F2: an explicit as_of is a real cutoff for the served current mode
# ---------------------------------------------------------------------------


def test_explicit_as_of_never_seals_fee_rows_available_after_it(pack, tmp_path):
    """One row available before the explicit as_of, one after: the served
    current-mode bundle seals only the earlier row, and the reader reproduces
    the published digest through the SAME selection path."""
    root = _disk_root(tmp_path)
    projection = json.loads((root / "projection.json").read_text(encoding="utf-8"))
    issuer_id = str(projection["records"][0]["issuer_id"])
    telemetry_as_of = json.loads((root / "telemetry.json").read_text(encoding="utf-8"))[
        "as_of"
    ]
    ledger = _write_ledger(
        root / DOCUMENT_LEDGER_FILENAME,
        [
            _fee_observation(
                "fee-before-explicit-as-of",
                issuer_id=issuer_id,
                value="1000000",
                available_at="2026-08-02T11:00:00Z",
                source_available_at="2026-08-02T10:00:00Z",
            ),
            _fee_observation(
                "fee-after-explicit-as-of",
                issuer_id=issuer_id,
                value="2000000",
                available_at="2026-08-03T00:00:00Z",
                source_available_at="2026-08-02T20:00:00Z",
            ),
        ],
    )

    summary = state_builder.build_from_disk(
        root=root, as_of=telemetry_as_of, generated_at=DISK_STATE_AT
    )
    assert summary["as_of"] == telemetry_as_of
    bundle = json.loads((root / "state_bundle.json").read_text(encoding="utf-8"))
    assert bundle["as_of"] == telemetry_as_of
    validate_state_bundle(bundle)

    family = _family_record_of(_state_record(bundle, issuer_id))
    fee = _fee_rows(family["records"])
    assert [row["normalized"]["value"] for row in fee] == ["1000000"]

    generation = read_verified_projection_generation(root)
    inputs = issuer_inputs(bundle, generation, issuer_id, document_terms_ledger=ledger)
    assert inputs.input_digest == (
        _state_record(bundle, issuer_id)["receipt"]["input_digest"]
    )


# ---------------------------------------------------------------------------
# F3: share basis is served as an explicit unavailable family
# ---------------------------------------------------------------------------


def _share_schemas_in(node: Any) -> set[str]:
    """Every record schema appearing anywhere inside a JSON-able structure."""
    found: set[str] = set()
    if isinstance(node, Mapping):
        schema = node.get("schema")
        if isinstance(schema, str):
            found.add(schema)
        for value in node.values():
            found |= _share_schemas_in(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            found |= _share_schemas_in(value)
    return found


def test_share_basis_is_served_as_an_explicit_unavailable_family(pack, tmp_path):
    """Every issuer carries share_basis as unavailable with no records, the
    bundle coverage never names it, and capacity reads no share record."""
    events, edges = _s3_amended_effective_post_effective()
    ledger = _write_ledger(tmp_path / DOCUMENT_LEDGER_FILENAME, _standard_ledger())
    _, _, bundle = _bundle(events, edges, pack, ledger_path=ledger)

    assert len(bundle["issuers"]) > 0
    for record in bundle["issuers"]:
        families = {row["family"]: row for row in record["families"]}
        assert set(families) == {"registration", "share_basis"}
        share = families["share_basis"]
        assert share["provenance"]["support"] == "unavailable"
        assert share["records"] == []
        assert share["unavailable"] == ["share_count_generation_not_admitted"]
    assert "share_basis" not in bundle["coverage"]["families"]

    # The generic contract re-construction (validate_state_bundle already ran
    # state_from_record per issuer) round-trips the new family byte for byte.
    state = state_from_record(_state_record(bundle, ISSUER))
    share_family = state.family("share_basis")
    assert share_family is not None
    assert share_family.records == ()
    assert share_family.provenance.support == "unavailable"

    built = ra.build_rule_pack(pack, SALE)[0]
    assert built is not None, f"no qualified rule text on {SALE}"
    evaluation = explain_capacity(state, _scenario(), built, pack=pack)
    share_schemas = set(c1.SHARE_COUNT_SCHEMAS) | {c1.SHARE_BASIS_RESULT_SCHEMA}
    served = _share_schemas_in(evaluation.inputs)
    assert not served & share_schemas, sorted(served & share_schemas)
