"""SPEC_U1B §1 gates 1-5 and 16-19: the capacity inputs bundle and its producer.

Fixtures are imported from the suites that own them and never copied: the S0
§10 family set (A21 state fixtures, I1/I2 supply instruments, B1 basis, F1
financials and commitments, L0 rules), the I0 instrument-resolution
``_bundle()``/``_decisions()`` candidates, the U1a disk path
(``_compiled_root`` + the projection builder + the state builder), and the
covenant/document ledger column shapes from the sealed compilers.  No digest,
id or count is hard-coded: every expectation is derived with ``sha256_of`` /
``stable_id`` or read back from the fixture generation.

The one shared helper, :func:`check_bundle`, validates every bundle produced in
this file: JSON schema, contract version, the record-null law, the closed
reason vocabulary, and the coverage tallies.
"""
from __future__ import annotations

import ast
import builtins
import inspect
import io
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import pytest

import tests.test_capital_structure_capacity as C1
import tests.test_capital_structure_funding as F
import tests.test_capital_structure_instrument_resolution as IR
import tests.test_capital_structure_issuer_state_contracts as T
import tests.test_capital_structure_supply_scenarios as SS
from engine.capital_structure import rule_applicability as ra
from engine.capital_structure.funding import project_funding
from engine.capital_structure.instrument_resolution import resolve_instruments
from engine.capital_structure.issuer_state_contracts import (
    COMPATIBLE_INPUT_SCHEMAS,
    STATE_CONTRACT_VERSION,
    Unknown,
    GenerationBinding,
    sha256_of,
    stable_id,
)
from engine.capital_structure.scenario_inputs import (
    CAPACITY_INPUTS_FILENAME,
    COMMITMENTS_FAMILY,
    FINANCIALS_FAMILY,
    INSTRUMENTS_FAMILY,
    INPUT_UNAVAILABLE_REASONS,
    RULES_FAMILY,
    SHARE_BASIS_FAMILY,
    CapacityInputsBundle,
    FamilyEntry,
    RulesEntry,
    ScenarioInputs,
    ScenarioInputsError,
    ScenarioInputsUnavailable,
    assemble_scenario_inputs,
    commitment_inputs_from_record,
    financial_inputs_from_fif_cash_receipt,
    financial_inputs_from_record,
    instrument_set_from_record,
    validate_capacity_inputs_bundle,
)
import scripts.build_capital_structure_capacity_inputs as producer
import scripts.build_capital_structure_projection as projection_builder
import scripts.build_capital_structure_state as state_builder
from scripts.compile_capital_structure_instrument_candidate_terms import (
    CANDIDATE_TERM_COLUMNS,
    DOCUMENT_TERM_COLUMNS,
    _to_frame,
)
from scripts.compile_capital_structure_covenant_terms import COVENANT_OBSERVATION_COLUMNS
from tests.test_build_capital_structure_projection import _compiled_root

#: The S0 §10 fixture world: the supply fixtures are cut at T.AS_OF.
GATE_AS_OF = T.AS_OF
GATE_DATE = "2026-10-13"
GATE_ISSUER = "cik:0001234567"
#: The disk world: late enough that the I0 fixture candidates (available
#: 2026-08-08T00:00:00Z) and the fixture identity decisions (decided 2026-08-06
#: and 2026-08-07) are visible at the served cutoff.
SERVED_AS_OF = IR.FUTURE
PROJECTION_AT = "2026-08-02T13:00:00Z"
#: The state build stamps its generation; it may never precede the cutoff it cuts at.
STATE_AT = "2026-08-09T12:00:00Z"
#: The disk root's one issuer and the I0 fixture issuer are the same CIK.
ISSUER = IR.ISSUER

#: Family -> (input family, accepted schema) for fixture-entry bindings.
ENTRY_FAMILIES = {
    INSTRUMENTS_FAMILY: (
        "instrument_candidate_terms",
        COMPATIBLE_INPUT_SCHEMAS["instrument_candidate_terms"][0],
    ),
    SHARE_BASIS_FAMILY: (
        "share_count_observations",
        COMPATIBLE_INPUT_SCHEMAS["share_count_observations"][0],
    ),
    FINANCIALS_FAMILY: ("financials", COMPATIBLE_INPUT_SCHEMAS["financials"][0]),
    COMMITMENTS_FAMILY: ("covenant_terms", COMPATIBLE_INPUT_SCHEMAS["covenant_terms"][0]),
}


# ---------------------------------------------------------------------------
# Fixtures — the S0 §10 family set and the U1a disk path, imported not copied
# ---------------------------------------------------------------------------


def _fixture_instruments():
    """A resolved I1 warrant set: instruments that carry economic terms."""
    instrument_id, instrument = SS.make_instrument(
        "series_u1b_gate_warrants",
        instruments_outstanding="1000000",
        shares_per_instrument="1",
        exercise_price="1.50",
    )
    return SS.instrument_set((instrument_id, instrument))


def _entry_for(obj: Any, family: str) -> FamilyEntry:
    support = obj.provenance.support if hasattr(obj, "provenance") else obj.binding.support
    input_family, schema = ENTRY_FAMILIES[family]
    return FamilyEntry(
        family=family,
        support=support,
        reason_codes=(),
        binding=GenerationBinding(
            input_family,
            schema,
            support,
            artifact_sha256=sha256_of(obj.as_record()),
            as_of=getattr(obj, "as_of", None),
        ),
        record=obj,
    )


def _fixture_family_entries() -> dict[str, FamilyEntry]:
    """The S0 §10 per-issuer families, bound exactly as the producer binds them."""
    return {
        INSTRUMENTS_FAMILY: _entry_for(_fixture_instruments(), INSTRUMENTS_FAMILY),
        SHARE_BASIS_FAMILY: _entry_for(SS.basis(), SHARE_BASIS_FAMILY),
        FINANCIALS_FAMILY: _entry_for(F.financials(F.cash(), F.ocf()), FINANCIALS_FAMILY),
        COMMITMENTS_FAMILY: _entry_for(
            F.covenants(F.covenant("cov-min-1", "2000000", available_at="2026-10-01T00:00:00Z")),
            COMMITMENTS_FAMILY,
        ),
    }


def _fixture_rules(date: str = GATE_DATE) -> RulesEntry:
    """The L0 pack as of the date, with the builder's own unknowns kept."""
    built, unknowns, _conditions, _excluded = ra.build_rule_pack(
        ra.load_rule_applicability_pack(), date
    )
    assert built is not None, f"the L0 pack governs on {date}"
    return RulesEntry(support="supported", unknowns=tuple(unknowns), record=built)


def _fixture_bundle(
    entries: dict[str, FamilyEntry] | None = None,
    *,
    rules: RulesEntry | None = None,
    issuer_id: str = GATE_ISSUER,
    as_of: str = GATE_AS_OF,
) -> dict[str, Any]:
    """One capacity inputs bundle over the S0 §10 fixtures, serialized."""
    bundle = CapacityInputsBundle(
        as_of=as_of,
        generated_at=f"{as_of[:10]}T12:00:00Z",
        state_generation_id=stable_id("state_bundle", {"fixture": "u1b"}),
        source_generation_id=stable_id("projection:cs:", {"fixture": "u1b"}),
        rules=rules if rules is not None else _fixture_rules(),
        issuers={issuer_id: entries if entries is not None else _fixture_family_entries()},
    )
    return bundle.as_record()


def to_json(record: Mapping[str, Any]) -> dict[str, Any]:
    """The published form: one JSON round trip, exactly what a reader loads."""
    return json.loads(json.dumps(record, sort_keys=True))


# ---------------------------------------------------------------------------
# The ONE shared helper every test in this file calls
# ---------------------------------------------------------------------------


def check_bundle(record: Mapping[str, Any]) -> dict[str, Any]:
    """Schema + contract laws + tallies; returns the parsed published record."""
    parsed = to_json(record)
    validate_capacity_inputs_bundle(parsed)
    assert parsed["contract_version"] == STATE_CONTRACT_VERSION
    for issuer_id, entries in parsed["issuers"].items():
        for family, entry in entries.items():
            if entry["support"] == "unavailable":
                assert entry["record"] is None, f"{issuer_id}.{family}"
                assert entry["binding"] is None, f"{issuer_id}.{family}"
                assert len(entry["reason_codes"]) > 0, f"{issuer_id}.{family}"
            else:
                assert entry["record"] is not None, f"{issuer_id}.{family}"
            for code in entry["reason_codes"]:
                assert code in INPUT_UNAVAILABLE_REASONS, code
    tallies = {
        family: {"supported": 0, "partial": 0, "unavailable": 0}
        for family in (INSTRUMENTS_FAMILY, SHARE_BASIS_FAMILY, FINANCIALS_FAMILY, COMMITMENTS_FAMILY)
    }
    for entries in parsed["issuers"].values():
        for family in tallies:
            tallies[family][entries[family]["support"]] += 1
    assert parsed["coverage"]["families"] == tallies
    assert parsed["coverage"]["issuer_count"] == len(parsed["issuers"])
    return parsed


def _read_produced_bundle(root: Path) -> dict[str, Any]:
    """Read the producer's output and pass it through the shared helper."""
    return check_bundle(json.loads((root / CAPACITY_INPUTS_FILENAME).read_text(encoding="utf-8")))


def _served_root(base: Path) -> Path:
    """One real disk generation: verified events, served projection, state bundle."""
    base.mkdir(parents=True, exist_ok=True)
    root = _compiled_root(base)
    projection_builder.build_from_disk(
        root=root,
        canonical_path=root / "projection.json",
        public_path=base / "site" / "latest.json",
        generated_at=PROJECTION_AT,
    )
    state_builder.build_from_disk(root=root, as_of=SERVED_AS_OF, generated_at=STATE_AT)
    return root


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def _parquet_frame(columns: list[str], rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=columns)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Gate 1 — every family round-trips through its contract class
# ---------------------------------------------------------------------------


def test_u1b_inputs_bundle_round_trips_every_family_through_contract_classes() -> None:
    instruments = _fixture_instruments()
    basis = SS.basis()
    financials = F.financials(F.cash(), F.ocf())
    commitments = F.covenants(
        F.covenant("cov-min-1", "2000000", available_at="2026-10-01T00:00:00Z")
    )
    rules = _fixture_rules().record
    parsed = check_bundle(_fixture_bundle())
    inputs = assemble_scenario_inputs(parsed, GATE_ISSUER, GATE_AS_OF)
    assert isinstance(inputs, ScenarioInputs)
    # Byte identity for every family, against the ORIGINAL fixture objects.
    for original, reconstructed in (
        (instruments, inputs.instruments),
        (basis, inputs.basis),
        (financials, inputs.financials),
        (commitments, inputs.commitments),
        (rules, inputs.rules),
    ):
        assert json.dumps(original.as_record(), sort_keys=True) == json.dumps(
            reconstructed.as_record(), sort_keys=True
        ), type(original).__name__
    # The assembled fields sit in compose_scenario's own argument order:
    # (instruments, basis, financials, commitments, rules, bindings).
    assert (
        inputs.instruments.issuer_id
        == inputs.basis.issuer_id
        == GATE_ISSUER
    )
    assert len(inputs.bindings) == 4


# ---------------------------------------------------------------------------
# Gate 2 — a missing family is typed unavailability, never a default
# ---------------------------------------------------------------------------


def test_u1b_missing_family_is_typed_unavailability_not_a_default() -> None:
    entries = _fixture_family_entries()
    entries[FINANCIALS_FAMILY] = FamilyEntry(
        family=FINANCIALS_FAMILY,
        support="unavailable",
        reason_codes=("companyfacts_snapshot_unavailable",),
    )
    parsed = check_bundle(_fixture_bundle(entries=entries))
    outcome = assemble_scenario_inputs(parsed, GATE_ISSUER, GATE_AS_OF)
    assert isinstance(outcome, ScenarioInputsUnavailable)
    assert outcome.components == {
        FINANCIALS_FAMILY: {
            "support": "unavailable",
            "reason_codes": ["companyfacts_snapshot_unavailable"],
        }
    }
    assert outcome.available == (
        INSTRUMENTS_FAMILY, SHARE_BASIS_FAMILY, COMMITMENTS_FAMILY, RULES_FAMILY,
    )
    # No record, no binding and no number exists to compose from.
    entry = parsed["issuers"][GATE_ISSUER][FINANCIALS_FAMILY]
    assert entry["record"] is None and entry["binding"] is None


# ---------------------------------------------------------------------------
# Gate 3 — partial families pass through with their limits
# ---------------------------------------------------------------------------


def _partial_instrument_set():
    """The I0 partial world: one founding decision, the repeat left unresolved."""
    first = IR._filing(IR._bundle(), IR.FIRST_ACCESSION)
    return resolve_instruments(
        IR._bundle(), IR._decisions(IR._found(IR._ids(first))), IR.AS_OF
    )


def test_u1b_partial_family_is_passed_through_with_its_limits() -> None:
    partial_instruments = _partial_instrument_set()
    assert partial_instruments.provenance.support == "partial"
    assert partial_instruments.unresolved_candidate_ids
    entries = {
        INSTRUMENTS_FAMILY: FamilyEntry(
            family=INSTRUMENTS_FAMILY,
            support="partial",
            reason_codes=("decisions_ledger_absent",),
            binding=GenerationBinding(
                "instrument_candidate_terms",
                COMPATIBLE_INPUT_SCHEMAS["instrument_candidate_terms"][0],
                "partial",
                artifact_sha256=sha256_of(partial_instruments.as_record()),
                as_of=IR.AS_OF,
            ),
            record=partial_instruments,
        ),
        SHARE_BASIS_FAMILY: _entry_for(
            T.share_basis(issuer_id=IR.ISSUER, as_of=IR.AS_OF), SHARE_BASIS_FAMILY
        ),
        FINANCIALS_FAMILY: _entry_for(F.financials(F.cash(), F.ocf()), FINANCIALS_FAMILY),
        COMMITMENTS_FAMILY: _entry_for(
            F.covenants(F.covenant("cov-min-1", "2000000")), COMMITMENTS_FAMILY
        ),
    }
    parsed = check_bundle(
        _fixture_bundle(entries=entries, issuer_id=IR.ISSUER, as_of=IR.AS_OF)
    )
    inputs = assemble_scenario_inputs(parsed, IR.ISSUER, IR.AS_OF)
    assert isinstance(inputs, ScenarioInputs)
    # The partial instrument set travels with its unresolved candidates and the
    # covenant-bound commitments with their binding — limits echoed, never
    # silently upgraded.
    assert json.dumps(partial_instruments.as_record(), sort_keys=True) == json.dumps(
        inputs.instruments.as_record(), sort_keys=True
    )
    assert inputs.instruments.unresolved_candidate_ids
    entry = parsed["issuers"][IR.ISSUER]
    assert entry[INSTRUMENTS_FAMILY]["reason_codes"] == ["decisions_ledger_absent"]
    assert entry[INSTRUMENTS_FAMILY]["support"] == "partial"
    assert entry[COMMITMENTS_FAMILY]["binding"]["input_family"] == "covenant_terms"
    assert entry[COMMITMENTS_FAMILY]["support"] == "partial"


# ---------------------------------------------------------------------------
# Gate 4 — the bundle binds the served state generation and the request as_of
# ---------------------------------------------------------------------------


def test_u1b_bundle_binds_state_generation_and_as_of() -> None:
    parsed = check_bundle(_fixture_bundle())
    with pytest.raises(ScenarioInputsError, match="inputs_generation_mismatch"):
        assemble_scenario_inputs(
            parsed,
            GATE_ISSUER,
            GATE_AS_OF,
            served_state_generation_id=stable_id("state_bundle", {"fixture": "another"}),
        )
    with pytest.raises(ScenarioInputsError, match="inputs_as_of_mismatch"):
        assemble_scenario_inputs(parsed, GATE_ISSUER, "2026-10-14T00:00:00Z")
    # A bound family cut at another as_of is the same typed refusal.
    entries = _fixture_family_entries()
    record = json.loads(json.dumps(_fixture_bundle(entries=entries)))
    record["issuers"][GATE_ISSUER][COMMITMENTS_FAMILY]["binding"]["as_of"] = (
        "2030-01-01T00:00:00Z"
    )
    with pytest.raises(ScenarioInputsError, match="inputs_as_of_mismatch"):
        assemble_scenario_inputs(record, GATE_ISSUER, GATE_AS_OF)
    with pytest.raises(ScenarioInputsError, match="unknown_issuer"):
        assemble_scenario_inputs(parsed, "cik:0000000000", GATE_AS_OF)


# ---------------------------------------------------------------------------
# Gate 5 — the rules family is the L0 pack, not a fixture
# ---------------------------------------------------------------------------


def test_u1b_rule_pack_is_the_l0_pack_not_a_fixture(tmp_path: Path) -> None:
    root = _served_root(tmp_path)
    producer.build_from_disk(root=root)
    parsed = _read_produced_bundle(root)
    rules_entry = parsed[RULES_FAMILY]
    assert rules_entry["support"] == "supported"
    as_of_date = str(parsed["as_of"])[:10]
    # The published digest is the digest of the pack build_rule_pack returns
    # for the cutoff's date — the engine's own L0 answer, nothing hand-written.
    expected = ra.build_rule_pack(ra.load_rule_applicability_pack(), as_of_date)[0]
    assert expected is not None
    assert parsed["rule_pack"]["rule_pack_digest"] == expected.digest
    assert rules_entry["record"]["digest"] == expected.digest
    assert parsed["rule_pack"]["source"] == "L0"

    # A RulePack with another digest is refused: re-stamp the identity so the
    # only law left broken is the rule-pack digest itself.
    other_date = "2026-10-14"
    other_pack = ra.build_rule_pack(ra.load_rule_applicability_pack(), other_date)[0]
    assert other_pack is not None and other_pack.digest != expected.digest
    tampered = json.loads(json.dumps(parsed))
    tampered["rules"]["record"] = json.loads(json.dumps(other_pack.as_record()))
    body = {
        key: value
        for key, value in tampered.items()
        if key not in ("schema", "contract_version", "generation_id", "generated_at")
    }
    tampered["generation_id"] = stable_id("capacity_inputs", body)
    with pytest.raises(ScenarioInputsError, match="rule_pack"):
        validate_capacity_inputs_bundle(tampered)

    # A cutoff no rule governs is typed unavailability, unknowns kept.
    def no_rules(pack: Any, date: str) -> tuple[Any, tuple[Unknown, ...], tuple[str, ...], tuple[str, ...]]:
        unknown = Unknown("unknown:u1b-withheld", "no qualified text", "a qualified edition", ())
        return None, (unknown,), (), ()

    saved = producer.build_rule_pack
    producer.build_rule_pack = no_rules
    try:
        refused_root = _served_root(tmp_path / "no_rules")
        producer.build_from_disk(root=refused_root)
    finally:
        producer.build_rule_pack = saved
    without_rules = _read_produced_bundle(refused_root)
    assert without_rules[RULES_FAMILY]["support"] == "unavailable"
    assert without_rules[RULES_FAMILY]["reason_codes"] == ["no_rule_governs_as_of"]
    assert without_rules[RULES_FAMILY]["record"] is None
    assert without_rules[RULES_FAMILY]["unknowns"] == [
        {
            "unknown_id": "unknown:u1b-withheld",
            "description": "no qualified text",
            "resolving_fact": "a qualified edition",
            "affects": [],
        }
    ]


# ---------------------------------------------------------------------------
# Gate 16 — one generation or nothing, with typed per-family absence
# ---------------------------------------------------------------------------


def test_u1b_producer_writes_one_generation_or_nothing(tmp_path: Path) -> None:
    # (a) A missing generation publishes nothing at all: without the compiler's
    # telemetry commit or its ledgers, the verifier reports status missing.
    missing_root = _served_root(tmp_path / "missing")
    for name in (
        "telemetry.json",
        "event_versions.parquet",
        "event_edges.parquet",
        "review_queue.parquet",
    ):
        (missing_root / name).unlink()
    with pytest.raises(ScenarioInputsError, match="no verified capital-structure generation"):
        producer.build_from_disk(root=missing_root)
    assert not (missing_root / CAPACITY_INPUTS_FILENAME).exists()

    # (b) The verified generation publishes one bundle: every family that the
    # nightly cannot lawfully produce is unavailable with its closed reason.
    root = _served_root(tmp_path / "served")
    producer.build_from_disk(root=root)
    parsed = _read_produced_bundle(root)
    entry = parsed["issuers"][ISSUER]
    assert entry[INSTRUMENTS_FAMILY] == {
        "support": "unavailable",
        "reason_codes": ["candidate_terms_not_materialized"],
        "binding": None,
        "record": None,
    }
    assert entry[SHARE_BASIS_FAMILY]["reason_codes"] == ["share_observations_not_admitted"]
    assert entry[FINANCIALS_FAMILY]["reason_codes"] == ["companyfacts_snapshot_unavailable"]
    assert entry[COMMITMENTS_FAMILY]["reason_codes"] == ["commitment_rows_absent"]
    assert parsed[RULES_FAMILY]["support"] == "supported"
    state_bundle = json.loads((root / "state_bundle.json").read_text(encoding="utf-8"))
    assert parsed["state_generation_id"] == state_bundle["generation_id"]

    # (c) A failed run leaves the last good bundle byte-identical.
    good_bytes = (root / CAPACITY_INPUTS_FILENAME).read_bytes()
    state_bundle["generation_id"] = state_bundle["generation_id"][:-1] + (
        "0" if state_bundle["generation_id"][-1] != "0" else "1"
    )
    (root / "state_bundle.json").write_text(
        json.dumps(state_bundle, indent=2, sort_keys=True), encoding="utf-8"
    )
    with pytest.raises((ScenarioInputsError, ValueError)):
        producer.build_from_disk(root=root)
    assert (root / CAPACITY_INPUTS_FILENAME).read_bytes() == good_bytes


# ---------------------------------------------------------------------------
# Gate 17 — candidate terms bind when the compiler has materialized them
# ---------------------------------------------------------------------------


def _candidate_ledger_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in IR._bundle().candidate_terms]


def test_u1b_producer_binds_candidate_terms_when_present(tmp_path: Path) -> None:
    records = _candidate_ledger_rows()
    root = _served_root(tmp_path)
    _write_parquet(root / producer.CANDIDATE_TERMS_FILENAME, _to_frame(records))

    # (a) No decisions ledger: every candidate stays unresolved, nothing invented.
    producer.build_from_disk(root=root)
    parsed = _read_produced_bundle(root)
    entry = parsed["issuers"][ISSUER][INSTRUMENTS_FAMILY]
    assert entry["support"] == "partial"
    assert entry["reason_codes"] == ["decisions_ledger_absent"]
    assert entry["record"]["unresolved_candidate_ids"]
    assert not entry["record"]["instruments"]
    assert entry["binding"]["artifact_sha256"] == sha256_of(records)
    rebuilt = instrument_set_from_record(entry["record"])
    assert json.dumps(rebuilt.as_record(), sort_keys=True) == json.dumps(
        entry["record"], sort_keys=True
    )

    # (b) An admitted decisions ledger: the same candidates resolve.
    first, second = IR._filing(IR._bundle(), IR.FIRST_ACCESSION), IR._filing(
        IR._bundle(), IR.SECOND_ACCESSION
    )
    decisions = IR._decisions(
        IR._found(IR._ids(first)),
        IR._amend(IR._ids(second), IR._supersede_all()),
        as_of=SERVED_AS_OF,
    ).decisions
    ledger = root / producer.DECISIONS_FILENAME
    ledger.write_text(
        "".join(_canonical(decision) + "\n" for decision in decisions), encoding="utf-8"
    )
    producer.build_from_disk(root=root)
    resolved = _read_produced_bundle(root)
    resolved_entry = resolved["issuers"][ISSUER][INSTRUMENTS_FAMILY]
    assert resolved_entry["support"] == "supported"
    assert resolved_entry["reason_codes"] == []
    assert resolved_entry["record"]["unresolved_candidate_ids"] == []
    assert len(resolved_entry["record"]["instruments"]) == 1
    resolved_set = instrument_set_from_record(resolved_entry["record"])
    assert json.dumps(resolved_set.as_record(), sort_keys=True) == json.dumps(
        resolved_entry["record"], sort_keys=True
    )


# ---------------------------------------------------------------------------
# Gate 18 — covenant commitments bind per issuer into the real funding path
# ---------------------------------------------------------------------------


def _covenant_ledger_row(observation_id: str, value: str) -> dict[str, Any]:
    observation = F.covenant(observation_id, value, available_at="2026-08-05T21:00:00Z")
    return {
        "observation_id": observation_id,
        "logical_observation_id": f"logical:{observation_id}",
        "issuer_id": ISSUER,
        "accession": observation["filing"]["accession"],
        "form": observation["filing"]["form"],
        "source_manifest_id": "manifest:u1b",
        "term_name": observation["term"]["name"],
        "clause_id": "clause:1",
        "state": observation["state"]["disposition"],
        "available_at": observation["point_in_time"]["available_at"],
        "correction_version": 1,
        "observation_json": _canonical(observation),
    }


def _document_ledger_row(observation_id: str, name: str, value: str) -> dict[str, Any]:
    observation = F.document_term(observation_id, name, value, filing_date="2026-07-01")
    return {
        "observation_id": observation_id,
        "logical_observation_id": f"logical:{observation_id}",
        "issuer_id": ISSUER,
        "accession": observation["filing"]["accession"],
        "form": observation["filing"]["form"],
        "source_manifest_id": "manifest:u1b",
        "term_name": observation["term"]["name"],
        "state": observation["state"]["disposition"],
        "available_at": observation["point_in_time"]["available_at"],
        "correction_version": 1,
        "observation_json": _canonical(observation),
    }


@pytest.mark.parametrize(
    "case",
    [
        pytest.param("issuer_a_covenant_terms", id="issuer_a_covenant_terms"),
        pytest.param("issuer_b_document_terms", id="issuer_b_document_terms"),
        pytest.param("issuer_c_rows_absent", id="issuer_c_rows_absent"),
    ],
)
def test_u1b_producer_binds_covenant_commitments_per_issuer(
    tmp_path: Path, case: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _served_root(tmp_path)
    telemetry = json.loads((root / "telemetry.json").read_text(encoding="utf-8"))
    if case == "issuer_a_covenant_terms":
        # Issuer A: one direct USD minimum-liquidity row admitted, and a
        # quarantined row that must stay excluded from the bound commitments.
        _write_parquet(
            root / producer.COVENANT_LEDGER_FILENAME,
            _parquet_frame(
                COVENANT_OBSERVATION_COLUMNS,
                [_covenant_ledger_row("cov-min-u1b-a", "2500000")],
            ),
        )
        quarantine = dict(_covenant_ledger_row("cov-min-u1b-a", "2500000"))
        quarantine["observation_id"] = "cov-min-u1b-a-quarantined"
        quarantine["observation_json"] = _canonical(
            F.covenant("cov-min-u1b-a-quarantined", "999999", available_at="2026-08-05T21:00:00Z")
        )
        _write_parquet(
            root / (producer.COVENANT_LEDGER_FILENAME.replace(".parquet", "") + ".quarantined.parquet"),
            _parquet_frame(COVENANT_OBSERVATION_COLUMNS, [quarantine]),
        )
    elif case == "issuer_b_document_terms":
        _write_parquet(
            root / producer.DOCUMENT_LEDGER_FILENAME,
            _parquet_frame(
                DOCUMENT_TERM_COLUMNS,
                [_document_ledger_row("doc-fee-u1b-b", "registration_fee", "1500")],
            ),
        )

    producer.build_from_disk(root=root)
    parsed = _read_produced_bundle(root)
    entry = parsed["issuers"][ISSUER][COMMITMENTS_FAMILY]

    if case == "issuer_c_rows_absent":
        assert entry == {
            "support": "unavailable",
            "reason_codes": ["commitment_rows_absent"],
            "binding": None,
            "record": None,
        }
        return

    assert entry["support"] == "partial"
    assert entry["binding"]["generation_id"] == telemetry["generation_id"]
    commitments = commitment_inputs_from_record(entry["record"])
    assert json.dumps(commitments.as_record(), sort_keys=True) == json.dumps(
        entry["record"], sort_keys=True
    )
    if case == "issuer_a_covenant_terms":
        assert entry["binding"]["input_family"] == "covenant_terms"
        assert len(commitments.commitments) == 1
        # The floor project_funding reports is the cov-min-u1b-a row's own
        # normalized.value — the quarantined 999999 row never entered the
        # bound commitments.
        schedule = project_funding(
            F.financials(F.cash(), F.ocf()), commitments, F.scenario()
        )
        floor = schedule.periods[0].minimum_liquidity
        assert floor.status == "known" and floor.value is not None
        assert Decimal(floor.value) == Decimal("2500000")
        assert "0001234567-26-000101" in (floor.note or "")
    else:
        assert entry["binding"]["input_family"] == "document_terms"
        assert len(commitments.commitments) == 1


# ---------------------------------------------------------------------------
# Gate 19 — no provider, credential or source-store path is ever touched
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "share_count_publication",
    "share_count_r2",
    "companyfacts_authenticated",
    "build_source_stores",
    "boto3",
    "requests.",
)


def test_u1b_producer_never_reads_provider_or_credential_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = inspect.getsource(producer)
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, token
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for token in _FORBIDDEN_TOKENS:
                    assert token not in alias.name, alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for token in _FORBIDDEN_TOKENS:
                assert token not in module, module

    # Behavior: the producer succeeds with the source-store builder poisoned,
    # and every Python-level file it opens is inside --root (or the interpreter
    #'s own stdlib/site-packages).
    import engine.capital_structure.source_store as source_store

    def explode(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("the producer must never build source stores")

    monkeypatch.setattr(source_store, "build_source_stores", explode)

    root = _served_root(tmp_path)
    _write_parquet(
        root / producer.CANDIDATE_TERMS_FILENAME,
        _to_frame(_candidate_ledger_rows()),
    )
    opened: list[str] = []
    real_open = builtins.open

    def spy(file: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(file, (str, bytes, os.PathLike)):
            opened.append(os.fspath(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(io, "open", spy)
    producer.build_from_disk(root=root)
    resolved_root = root.resolve()
    # The producer's own frozen contracts and the L0 rule pack it reads are
    # repo definition files, the same class of read as importing the module;
    # every DATA path must stay inside --root.
    repo = Path(producer.__file__).resolve().parents[1]
    allowed = (resolved_root, repo / "contracts", repo / "config")
    for path in opened:
        candidate = Path(path)
        if not candidate.is_absolute():
            continue
        resolved = candidate.resolve()
        inside_allowed = any(resolved.is_relative_to(base.resolve()) for base in allowed)
        interpreter = path.startswith(sys.prefix) or "/usr/lib/python" in path or "site-packages" in path
        assert inside_allowed or interpreter, path


# ---------------------------------------------------------------------------
# Governed FIF cash receipt boundary (synthetic owner fixtures, no live data)
# ---------------------------------------------------------------------------


def _fif_cash_witness(*, exact_value: str | None = None, metric_id: str = "cash_and_cash_equivalents",
                      end: str = "2024-12-31", issuer_sic: str | None = None,
                      cik: str | None = None, class_restricted_cash: bool = False):
    from copy import deepcopy
    from dataclasses import replace

    import tests.test_fundamental_forensics_production_dataset_store as FIF
    from engine.fundamental_forensics import production_datasets as PDS
    from engine.fundamental_forensics.production_provider import ProductionFinancialQueryProvider
    from engine.fundamental_forensics.query_service import execute_financial_query
    from engine.fundamental_forensics.raw_ledger import RawFactLedger

    material = FIF._material()
    if exact_value is not None:
        # Alter the existing synthetic owner fixture, retaining no real-world
        # claim. Re-derive occurrence and production-generation identities.
        events = tuple(
            replace(event, raw_token=exact_value, parsed_value=Decimal(exact_value),
                    decimals="INF", precision=None, occurrence_id=None)
            if event.concept_qname == "us-gaap:CashAndCashEquivalentsAtCarryingValue"
            else event
            for event in material.ledger.events
        )
        # The owner fixture binds metadata by occurrence ID, not accession.
        # A changed value has a new ID even when its filing/body is unchanged.
        metadata = {
            changed.occurrence_id: material.filing_metadata[original.occurrence_id]
            for original, changed in zip(material.ledger.events, events)
        }
        material = replace(material, ledger=RawFactLedger(events=events), filing_metadata=metadata)
    if cik is not None:
        # A synthetic single-cash generation for the existing CS disk fixture's
        # CIK. Retain its distinct display ticker so the join cannot use ticker.
        cash, = (event for event in material.ledger.events
                 if event.concept_qname == "us-gaap:CashAndCashEquivalentsAtCarryingValue")
        binding = replace(material.binding, entity_id=f"test.issuer.{cik}", cik=cik, source_entity_id=cik)
        entity = replace(material.entity, entity_id=binding.entity_id, cik=cik, source_entity_id=cik)
        metadata = material.filing_metadata[cash.occurrence_id]
        cash = replace(
            cash, source=replace(cash.source, entity_id=cik),
            context=replace(cash.context, entity_identifier=cik), occurrence_id=None,
        )
        material = replace(
            material, binding=binding, entity=entity, ledger=RawFactLedger(events=(cash,)),
            filing_metadata={cash.occurrence_id: metadata},
        )
    if class_restricted_cash:
        # Synthetic governed variant: a real class-dependent VALUE must fail
        # the adapter's no-SIC replay. Retain all owner digest validation.
        from engine.fundamental_forensics.metric_registry import _content_digest

        registry = deepcopy(material.registry_payload)
        catalog = registry["catalog"]
        contract, = (row for row in catalog["metrics"]
                     if row["metric_id"] == "cash_and_cash_equivalents")
        contract["rule"] = {**contract["rule"], "version": "1.0.1"}
        contract["applicability"] = {
            "issuer_class_basis": "sic", "applicable_classes": ["software"],
            "excluded_classes": [], "basis_note": "synthetic cash-class replay fixture",
        }
        catalog["catalog_version"] = "1.1.1"
        catalog["content_sha256"] = _content_digest(catalog)
        material = replace(material, registry_payload=registry)
    store, publication = FIF._publish(material)
    generation = PDS.load_generation(store, material.binding.entity_id, publication.generation_id)
    body = json.dumps({
        "schema": "fundamental_forensics.financial_query_request/v1",
        "entity_id": material.binding.entity_id,
        "policy": {
            "selection": "latest_known_as_of",
            "source_snapshot_at": "2026-10-05T00:00:00Z",
            "recorded_at": "2026-10-05T00:00:00Z",
        },
        "metric_ids": [metric_id],
        "periods": [{"kind": "instant", "start": None, "end": end, "label": "reported-instant"}],
    }).encode("utf-8")
    result = execute_financial_query(
        body=body, provider=ProductionFinancialQueryProvider(store),
        issuer_sic_resolver=lambda _cik: issuer_sic,
    )
    return generation, result


@pytest.fixture(scope="module")
def fif_cash_witness():
    return _fif_cash_witness()


def _adapt_fif_cash(witness, **overrides):
    kwargs = {
        "issuer_id": "sec:cik:0000999999",
        "available_at": "2026-10-05T01:00:00Z",
        "as_of": "2026-10-05T02:00:00Z",
    }
    kwargs.update(overrides)
    return financial_inputs_from_fif_cash_receipt(*witness, **kwargs)


def test_fif_cash_binds_only_dated_exact_cash_with_original_provenance(fif_cash_witness) -> None:
    import hashlib
    from engine.fundamental_forensics.query import MetricMatrix
    from engine.fundamental_forensics.raw_ledger import canonical_json

    generation, result = fif_cash_witness
    built = _adapt_fif_cash(fif_cash_witness)
    fact, = built.facts
    cell, = MetricMatrix.from_dict(result.envelope["receipt"]).cells
    assert built.binding.support == "partial"
    assert built.binding.generation_id == generation.generation_id
    assert built.binding.artifact_sha256 == sha256_of([fact])
    assert built.binding.as_of == "2026-10-05T02:00:00Z"
    assert built.cash_basis == "unrestricted_cash"
    assert fact["amount"] == {"value": "15", "unit": "usd", "status": "known"}
    assert fact["measured_at"] == "2024-12-31"
    assert fact["available_at"] == "2026-10-05T01:00:00Z"
    assert fact["source"]["query_response"] == result.envelope
    assert fact["source"]["query_response"]["authority"] == {"class": "context_only", "display_only": True}
    assert fact["source"]["query_response"]["delivery"]["attested"] is False
    assert fact["source"]["query_response"]["delivery"]["capture_basis"] == "reconstruction"
    assert fact["source"]["dataset_clocks"] == generation.manifest["clocks"]
    assert fact["source"]["query_response_sha256"] == result.sha256
    assert fact["source"]["receipt_sha256"] == hashlib.sha256(canonical_json(cell.to_dict()).encode()).hexdigest()
    assert financial_inputs_from_record(built.as_record()).as_record() == built.as_record()
    assert set(fact) == {
        "schema", "item_id", "item_kind", "availability", "amount",
        "measured_at", "gross_net", "available_at", "source",
    }


def test_fif_cash_never_rounds_through_binary_float() -> None:
    from engine.fundamental_forensics.query import MetricMatrix

    value = "9007199254740993.125"
    witness = _fif_cash_witness(exact_value=value)
    cell, = MetricMatrix.from_dict(witness[1].envelope["receipt"]).cells
    assert cell.is_value and cell.value == Decimal(value)
    built = _adapt_fif_cash(witness)
    assert built.facts[0]["amount"]["value"] == value


@pytest.mark.parametrize("overrides", [
    {"issuer_id": "sec:cik:0000789019"},
    {"issuer_id": "issuer:0000999999"},
    {"issuer_id": "FIP1"},
    {"available_at": "2026-10-05T00:00:00"},
    {"available_at": "2026-10-05T01:00:00.0000001Z"},
    {"as_of": "2026-10-05T02:00:00.0000001Z"},
    {"as_of": "2026-10-05T00:30:00Z"},
    {"available_at": "2026-10-04T23:59:59Z"},
    {"available_at": "2026-09-30T23:59:59Z"},
])
def test_fif_cash_rejects_identity_or_unproved_cutoff(fif_cash_witness, overrides) -> None:
    with pytest.raises(ScenarioInputsError):
        _adapt_fif_cash(fif_cash_witness, **overrides)


@pytest.mark.parametrize("damage", ["body", "digest", "authority", "attestation", "role_bytes"])
def test_fif_cash_rejects_receipt_and_generation_damage(fif_cash_witness, damage) -> None:
    import hashlib
    from dataclasses import replace
    from engine.fundamental_forensics.raw_ledger import canonical_json

    generation, result = fif_cash_witness
    if damage == "body":
        result = replace(result, body=result.body + b" ")
    elif damage == "digest":
        result = replace(result, sha256="0" * 64)
    elif damage == "role_bytes":
        payloads = dict(generation.role_payloads)
        payloads["ledger_json"] = payloads["ledger_json"] + b" "
        generation = replace(generation, role_payloads=payloads)
    else:
        envelope = json.loads(result.body)
        if damage == "authority":
            envelope["authority"]["display_only"] = False
        else:
            envelope["delivery"]["attested"] = True
        body = canonical_json(envelope).encode("utf-8")
        result = replace(result, body=body, sha256=hashlib.sha256(body).hexdigest(), envelope=envelope)
    with pytest.raises(ScenarioInputsError):
        _adapt_fif_cash((generation, result))


@pytest.mark.parametrize("kwargs", [
    {"metric_id": "accounts_receivable_net"},
    {"end": "2022-12-31"},
])
def test_fif_cash_refuses_other_or_missing_witnesses(kwargs) -> None:
    with pytest.raises(ScenarioInputsError):
        _adapt_fif_cash(_fif_cash_witness(**kwargs))


def test_fif_cash_accepts_outcome_inert_sic_with_identical_replay(fif_cash_witness) -> None:
    generation, result = _fif_cash_witness(issuer_sic="7372")
    original_generation, original_result = fif_cash_witness
    assert generation.generation_id == original_generation.generation_id
    assert result.body == original_result.body
    assert result.sha256 == original_result.sha256
    assert _adapt_fif_cash((generation, result)).as_record() == _adapt_fif_cash(fif_cash_witness).as_record()


def test_fif_cash_refuses_a_value_that_requires_issuer_class() -> None:
    from engine.fundamental_forensics.query import MetricMatrix

    witness = _fif_cash_witness(issuer_sic="7372", class_restricted_cash=True)
    cell, = MetricMatrix.from_dict(witness[1].envelope["receipt"]).cells
    assert cell.is_value and cell.value == Decimal("15")
    missing_generation, missing_result = _fif_cash_witness(class_restricted_cash=True)
    assert missing_generation.generation_id == witness[0].generation_id
    missing, = MetricMatrix.from_dict(missing_result.envelope["receipt"]).cells
    assert not missing.is_value and missing.reason == "issuer_class_unknown"
    with pytest.raises(ScenarioInputsError, match="receipt does not reproduce"):
        _adapt_fif_cash(witness)


def test_fif_cash_uses_only_supplied_memory(fif_cash_witness, monkeypatch) -> None:
    from dataclasses import replace
    from engine.fundamental_forensics import production_datasets as PDS
    from engine.fundamental_forensics import query_service

    class NoStore:
        def __getattr__(self, _name):
            raise AssertionError("adapter must not access the original store")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("adapter must not acquire configuration or data")

    generation, result = fif_cash_witness
    monkeypatch.setattr(PDS, "build_production_dataset_store", forbidden)
    monkeypatch.setattr(query_service, "resolve_issuer_sic", forbidden)
    _adapt_fif_cash((replace(generation, store=NoStore()), result))


def test_fif_cash_builder_entry_is_optional_and_keeps_other_family_gates(fif_cash_witness) -> None:
    assert producer._financials_entry().support == "unavailable"
    entry = producer._financials_entry(
        issuer_id="sec:cik:0000999999", as_of="2026-10-05T02:00:00Z",
        witness=(*fif_cash_witness, "2026-10-05T01:00:00Z"),
    )
    assert entry.support == "partial"
    entries = {
        INSTRUMENTS_FAMILY: FamilyEntry(INSTRUMENTS_FAMILY, "unavailable", ("candidate_terms_not_materialized",)),
        SHARE_BASIS_FAMILY: FamilyEntry(SHARE_BASIS_FAMILY, "unavailable", ("share_observations_not_admitted",)),
        FINANCIALS_FAMILY: entry,
        COMMITMENTS_FAMILY: FamilyEntry(COMMITMENTS_FAMILY, "unavailable", ("commitment_rows_absent",)),
    }
    bundle = check_bundle(_fixture_bundle(
        entries, issuer_id="sec:cik:0000999999", as_of="2026-10-05T02:00:00Z",
        rules=RulesEntry(support="unavailable", reason_codes=("no_rule_governs_as_of",)),
    ))
    inputs = assemble_scenario_inputs(bundle, "sec:cik:0000999999", "2026-10-05T02:00:00Z")
    assert isinstance(inputs, ScenarioInputsUnavailable)
    assert FINANCIALS_FAMILY in inputs.available
    assert INSTRUMENTS_FAMILY in inputs.components
    assert RULES_FAMILY in inputs.components


def test_fif_cash_builder_refuses_coverage_widening_and_preserves_last_bundle(tmp_path, fif_cash_witness) -> None:
    root = _served_root(tmp_path)
    producer.build_from_disk(root=root)
    target = root / CAPACITY_INPUTS_FILENAME
    before = target.read_bytes()
    with pytest.raises(ScenarioInputsError, match="not in the served issuer set"):
        producer.build_from_disk(
            root=root,
            fif_cash_receipts={"sec:cik:0000789019": (*fif_cash_witness, "2026-10-05T01:00:00Z")},
        )
    assert target.read_bytes() == before


def test_fif_cash_builder_binds_verified_witness_for_an_existing_served_issuer(tmp_path) -> None:
    from dataclasses import replace

    root = _served_root(tmp_path)
    as_of = "2026-10-05T02:00:00Z"
    state_builder.build_from_disk(root=root, as_of=as_of, generated_at="2026-10-05T03:00:00Z")
    state_bytes = (root / producer.STATE_BUNDLE_FILENAME).read_bytes()
    producer.build_from_disk(root=root, generated_at="2026-10-05T03:01:00Z")
    before = _read_produced_bundle(root)
    assert set(before["issuers"]) == {ISSUER}
    assert before["issuers"][ISSUER][FINANCIALS_FAMILY]["support"] == "unavailable"

    generation, result = _fif_cash_witness(cik=ISSUER.removeprefix("sec:cik:"))
    summary = producer.build_from_disk(
        root=root, generated_at="2026-10-05T03:02:00Z",
        fif_cash_receipts={ISSUER: (generation, result, "2026-10-05T01:00:00Z")},
    )
    after = _read_produced_bundle(root)
    assert summary["status"] == "ok"
    assert summary["issuers"] == 1
    assert summary["families"][FINANCIALS_FAMILY] == 0
    assert set(after["issuers"]) == {ISSUER}
    assert after["state_generation_id"] == before["state_generation_id"]
    assert after["source_generation_id"] == before["source_generation_id"]
    assert (root / producer.STATE_BUNDLE_FILENAME).read_bytes() == state_bytes
    financials = after["issuers"][ISSUER][FINANCIALS_FAMILY]
    assert financials["support"] == "partial"
    assert financials["record"]["facts"][0]["amount"]["value"] == "15"
    assert financials["record"]["facts"][0]["measured_at"] == "2024-12-31"
    assert financials["record"]["facts"][0]["source"]["query_response"] == result.envelope
    for family in (INSTRUMENTS_FAMILY, SHARE_BASIS_FAMILY, COMMITMENTS_FAMILY):
        assert after["issuers"][ISSUER][family] == before["issuers"][ISSUER][family]
    assert after["rules"] == before["rules"]

    target = root / CAPACITY_INPUTS_FILENAME
    last_good = target.read_bytes()
    damaged = replace(result, body=result.body + b" ")
    with pytest.raises(ScenarioInputsError):
        producer.build_from_disk(
            root=root, fif_cash_receipts={ISSUER: (generation, damaged, "2026-10-05T01:00:00Z")},
        )
    assert target.read_bytes() == last_good
