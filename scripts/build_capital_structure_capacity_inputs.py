"""Build the Capital Structure capacity inputs bundle over the served state.

SPEC_U1B §3.  This offline, fail-closed producer reads the SERVED
``state_bundle.json`` (U1a) for the issuer set, cutoff and served generation,
and the verified projection generation through the same verifier the projection
uses, then binds per issuer exactly what each nightly run can lawfully produce:

* instruments — from ``instrument_candidate_terms.parquet`` when the candidate
  compiler has materialized rows for the issuer, resolved with an owner
  decisions ledger when one is admitted (never fuzzy, never invented);
* share basis — only from admitted share-count observations and corporate
  actions under the root (never from a provider, a publication chain or R2);
* financials — unavailable until the F0b binder exists on an admitted
  companyfacts artifact;
* commitments — from the covenant-term ledger, falling back to document-term
  rows, with the quarantine twin excluded by name;
* rules — the L0 rule applicability pack as of the cutoff's date.

It publishes ONE ``capacity_inputs.json`` — one generation or nothing: a
missing generation, a missing or invalid state bundle, or any family binding
failure exits non-zero and leaves the last good bundle byte-identical.  It
never reads raw SEC objects, never performs network I/O, never touches a path
outside ``--root``, and never widens a frozen contract.

Usage:
    python -m scripts.build_capital_structure_capacity_inputs
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.capital_structure.covenant_terms import COVENANT_TERM_SCHEMA  # noqa: E402
from engine.capital_structure.document_terms import DOCUMENT_TERM_SCHEMA  # noqa: E402
from engine.capital_structure.instrument_candidates import INSTRUMENT_CANDIDATE_TERM_SCHEMA  # noqa: E402
from engine.capital_structure.instrument_resolution import resolve_instruments  # noqa: E402
from engine.capital_structure.issuer_state_contracts import (  # noqa: E402
    COMPATIBLE_INPUT_SCHEMAS,
    CandidateBundle,
    CommitmentInputs,
    GenerationBinding,
    ResolutionInputs,
    ShareInputs,
    CorporateActionInputs,
    sha256_of,
)
from engine.capital_structure.rule_applicability import (  # noqa: E402
    build_rule_pack,
    load_rule_applicability_pack,
)
from engine.capital_structure.scenario_inputs import (  # noqa: E402
    CAPACITY_INPUTS_FILENAME,
    COMMITMENTS_FAMILY,
    FINANCIALS_FAMILY,
    INSTRUMENTS_FAMILY,
    RULES_FAMILY,
    SHARE_BASIS_FAMILY,
    CapacityInputsBundle,
    FamilyEntry,
    RulesEntry,
    ScenarioInputsError,
    validate_capacity_inputs_bundle,
)
from engine.capital_structure.share_basis import select_share_basis  # noqa: E402
from engine.capital_structure.state_bundle import validate_state_bundle  # noqa: E402
from engine.capital_structure.term_integration import CANDIDATE_FAMILY  # noqa: E402
from engine.capital_structure.verified_projection_generation import (  # noqa: E402
    read_verified_projection_generation,
)

STATE_BUNDLE_FILENAME = "state_bundle.json"
CANDIDATE_TERMS_FILENAME = "instrument_candidate_terms.parquet"
DECISIONS_FILENAME = "instrument_resolution_decisions.jsonl"
SHARE_OBSERVATIONS_FILENAME = "share_count_observations.jsonl"
CORPORATE_ACTIONS_FILENAME = "corporate_actions.jsonl"
COVENANT_LEDGER_FILENAME = "covenant_term_observations.parquet"
DOCUMENT_LEDGER_FILENAME = "document_term_observations.parquet"

#: The owner that adjudicates instrument identity when a decisions ledger is
#: admitted; ``none`` when no ledger exists (SPEC_U1B §3).
DECIDED_BY_LEDGER = "capital-structure-owner"
DECIDED_BY_NONE = "none"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _data_root() -> Path:
    from lib import config

    return config.data_dir() / "capital_structure"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write_one(payload: bytes, target: Path) -> None:
    """Replace one target atomically using a same-directory staged file.

    Copied line-for-line from ``scripts/build_capital_structure_projection.py``
    (SPEC_U1B packet: the helper is private there, so the producer carries its
    own 10-line copy rather than importing a private name).
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, staged_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    staged = Path(staged_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, target)
    finally:
        if staged.exists():
            staged.unlink()


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise ScenarioInputsError(f"{label} is required: {path} is absent")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScenarioInputsError(f"{label} is unreadable: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ScenarioInputsError(f"{label} must be a JSON object")
    return dict(value)


def _read_jsonl_records(path: Path, label: str) -> tuple[dict[str, Any], ...]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ScenarioInputsError(f"{label} is unreadable: {exc}") from exc
    records = []
    for index, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ScenarioInputsError(f"{label} line {index} is not valid JSON") from exc
        if not isinstance(value, Mapping):
            raise ScenarioInputsError(f"{label} line {index} must be a JSON object")
        records.append(dict(value))
    return tuple(records)


def _issuer_rows(path: Path, json_column: str, issuer_id: str, label: str) -> tuple[dict[str, Any], ...]:
    import pandas as pd

    frame = pd.read_parquet(path)
    if "issuer_id" not in frame.columns:
        raise ScenarioInputsError(f"{label} carries no issuer_id column")
    mask = frame["issuer_id"].astype(str) == issuer_id
    selected = frame.loc[mask]
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(selected[json_column].tolist()):
        if not isinstance(raw, str) or not raw:
            raise ScenarioInputsError(f"{label} row {index} lacks a {json_column} payload")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ScenarioInputsError(f"{label} row {index} has malformed {json_column}") from exc
        if not isinstance(value, Mapping):
            raise ScenarioInputsError(f"{label} row {index} {json_column} must be an object")
        rows.append(dict(value))
    return tuple(rows)


def _bind_instruments(root: Path, issuer_id: str, as_of: str) -> FamilyEntry:
    """Bind the instruments family, or name why nothing is bound (SPEC_U1B §3)."""
    ledger_path = root / CANDIDATE_TERMS_FILENAME
    if not ledger_path.exists():
        return FamilyEntry(
            family=INSTRUMENTS_FAMILY,
            support="unavailable",
            reason_codes=("candidate_terms_not_materialized",),
        )
    records = _issuer_rows(ledger_path, "candidate_term_json", issuer_id, "instrument_candidate_terms")
    if not records:
        return FamilyEntry(
            family=INSTRUMENTS_FAMILY,
            support="unavailable",
            reason_codes=("candidate_terms_not_materialized",),
        )
    decisions_path = root / DECISIONS_FILENAME
    if decisions_path.exists():
        decisions = _read_jsonl_records(decisions_path, "instrument_resolution_decisions")
        decided_by = DECIDED_BY_LEDGER
        limits: tuple[str, ...] = ()
    else:
        decisions = ()
        decided_by = DECIDED_BY_NONE
        limits = ("decisions_ledger_absent",)
    resolution_inputs = ResolutionInputs(tuple(decisions), decided_by, as_of)
    # Mirror term_integration.CandidateIntegration.candidate_binding: the
    # candidate family binds its artifact digest and its own as_of.  Support is
    # the resolution's outcome — one deterministic re-resolve at "supported"
    # when every candidate resolved, so the published binding never overstates.
    support = "partial"
    while True:
        bundle = CandidateBundle(
            GenerationBinding(
                CANDIDATE_FAMILY,
                INSTRUMENT_CANDIDATE_TERM_SCHEMA,
                support,
                artifact_sha256=sha256_of(list(records)),
                as_of=as_of,
            ),
            records,
            as_of,
        )
        instrument_set = resolve_instruments(bundle, resolution_inputs, as_of)
        if support == "partial" and not instrument_set.unresolved_candidate_ids:
            support = "supported"
            continue
        break
    entry_support = "partial" if instrument_set.unresolved_candidate_ids else "supported"
    return FamilyEntry(
        family=INSTRUMENTS_FAMILY,
        support=entry_support,
        reason_codes=limits if entry_support == "partial" else (),
        binding=GenerationBinding(
            CANDIDATE_FAMILY,
            INSTRUMENT_CANDIDATE_TERM_SCHEMA,
            entry_support,
            artifact_sha256=sha256_of(list(records)),
            as_of=as_of,
        ),
        record=instrument_set,
    )


def _bind_share_basis(root: Path, issuer_id: str, as_of: str) -> FamilyEntry:
    """Bind the share-basis family only from admitted files under the root."""
    share_path = root / SHARE_OBSERVATIONS_FILENAME
    actions_path = root / CORPORATE_ACTIONS_FILENAME
    if not share_path.exists():
        return FamilyEntry(
            family=SHARE_BASIS_FAMILY,
            support="unavailable",
            reason_codes=("share_observations_not_admitted",),
        )
    if not actions_path.exists():
        return FamilyEntry(
            family=SHARE_BASIS_FAMILY,
            support="unavailable",
            reason_codes=("corporate_actions_absent",),
        )
    observations = _read_jsonl_records(share_path, "share_count_observations")
    actions = _read_jsonl_records(actions_path, "corporate_actions")
    if not observations:
        return FamilyEntry(
            family=SHARE_BASIS_FAMILY,
            support="unavailable",
            reason_codes=("share_observations_not_admitted",),
        )
    accepted_share_schemas = COMPATIBLE_INPUT_SCHEMAS["share_count_observations"]
    share_schema = observations[0].get("schema")
    if share_schema not in accepted_share_schemas or any(
        row.get("schema") != share_schema for row in observations
    ):
        raise ScenarioInputsError(
            f"share_count_observations: records do not share one accepted schema ({share_schema!r})"
        )
    share_binding = GenerationBinding(
        "share_count_observations",
        share_schema,
        "partial",
        artifact_sha256=sha256_of(list(observations)),
        as_of=as_of,
    )
    action_schema = COMPATIBLE_INPUT_SCHEMAS["corporate_actions"][0]
    actions_binding = GenerationBinding(
        "corporate_actions",
        action_schema,
        "partial",
        artifact_sha256=sha256_of(list(actions)),
        as_of=as_of,
    )
    basis = select_share_basis(
        ShareInputs(share_binding, observations),
        CorporateActionInputs(actions_binding, actions),
        as_of,
    )
    support = basis.provenance.support
    return FamilyEntry(
        family=SHARE_BASIS_FAMILY,
        support=support,
        reason_codes=(),
        binding=share_binding,
        record=basis,
    )


def _financials_entry() -> FamilyEntry:
    """Financials stay unavailable until the F0b binder is admitted (SPEC_U1B §0)."""
    return FamilyEntry(
        family=FINANCIALS_FAMILY,
        support="unavailable",
        reason_codes=("companyfacts_snapshot_unavailable",),
    )


def _bind_commitments(
    root: Path, issuer_id: str, as_of: str, source_generation_id: str
) -> FamilyEntry:
    """Bind commitments from covenant rows, falling back to document rows."""
    covenant_path = root / COVENANT_LEDGER_FILENAME
    records: tuple[dict[str, Any], ...] = ()
    family: str | None = None
    if covenant_path.exists():
        records = _issuer_rows(
            covenant_path, "observation_json", issuer_id, "covenant_term_observations"
        )
        family = "covenant_terms"
    if not records:
        document_path = root / DOCUMENT_LEDGER_FILENAME
        if document_path.exists():
            records = _issuer_rows(
                document_path, "observation_json", issuer_id, "document_term_observations"
            )
            family = "document_terms"
    if not records or family is None:
        return FamilyEntry(
            family=COMMITMENTS_FAMILY,
            support="unavailable",
            reason_codes=("commitment_rows_absent",),
        )
    schema = COVENANT_TERM_SCHEMA if family == "covenant_terms" else DOCUMENT_TERM_SCHEMA
    binding = GenerationBinding(
        family,
        schema,
        "partial",
        generation_id=source_generation_id,
        artifact_sha256=sha256_of(list(records)),
        as_of=as_of,
    )
    return FamilyEntry(
        family=COMMITMENTS_FAMILY,
        support="partial",
        reason_codes=(),
        binding=binding,
        record=CommitmentInputs(binding, records),
    )


def _bind_rules(as_of_date: str) -> RulesEntry:
    """The L0 pack as of the cutoff's date; ``None`` is typed unavailability."""
    built, unknowns, _conditions, _excluded = build_rule_pack(load_rule_applicability_pack(), as_of_date)
    if built is None:
        return RulesEntry(
            support="unavailable",
            reason_codes=("no_rule_governs_as_of",),
            unknowns=tuple(unknowns),
        )
    return RulesEntry(support="supported", unknowns=tuple(unknowns), record=built)


def build_from_disk(
    *,
    root: Path | str | None = None,
    generated_at: str | None = None,
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Verify the generation and the served state, and publish one bundle — or nothing."""
    root = Path(root) if root is not None else _data_root()
    target = Path(out_path) if out_path is not None else (root / CAPACITY_INPUTS_FILENAME)

    state_bundle = _read_json_object(root / STATE_BUNDLE_FILENAME, "state bundle")
    try:
        validate_state_bundle(state_bundle)
    except ValueError as exc:
        raise ScenarioInputsError(f"state bundle is invalid: {exc}") from exc

    generation = read_verified_projection_generation(root)
    telemetry = generation.telemetry
    if telemetry.get("status") == "missing" or not telemetry.get("generation_id"):
        raise ScenarioInputsError(
            "no verified capital-structure generation: the producer writes nothing over a missing generation"
        )
    source_generation_id = str(telemetry["generation_id"])
    as_of = str(state_bundle["as_of"])
    state_generation_id = str(state_bundle["generation_id"])
    as_of_date = as_of[:10]

    issuers: dict[str, dict[str, FamilyEntry]] = {}
    for record in state_bundle.get("issuers") or ():
        issuer_id = str(record["request"]["issuer_id"])
        issuers[issuer_id] = {
            INSTRUMENTS_FAMILY: _bind_instruments(root, issuer_id, as_of),
            SHARE_BASIS_FAMILY: _bind_share_basis(root, issuer_id, as_of),
            FINANCIALS_FAMILY: _financials_entry(),
            COMMITMENTS_FAMILY: _bind_commitments(root, issuer_id, as_of, source_generation_id),
        }
    rules = _bind_rules(as_of_date)

    bundle = CapacityInputsBundle(
        as_of=as_of,
        generated_at=generated_at or _now_iso(),
        state_generation_id=state_generation_id,
        source_generation_id=source_generation_id,
        rules=rules,
        issuers=issuers,
    )
    record = bundle.as_record()
    # Validate the exact bytes that will be published, never the in-memory form.
    payload = (json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    validate_capacity_inputs_bundle(json.loads(payload.decode("utf-8")))
    _atomic_write_one(payload, target)
    tallies = record["coverage"]["families"]
    return {
        "status": "ok",
        "generation_id": record["generation_id"],
        "state_generation_id": state_generation_id,
        "source_generation_id": source_generation_id,
        "as_of": as_of,
        "issuers": record["coverage"]["issuer_count"],
        "families": {family: tally["unavailable"] for family, tally in tallies.items()},
        "out_path": str(target),
        "byte_length": len(payload),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None, help="capital-structure data root (default data/capital_structure)")
    parser.add_argument("--out-path", type=Path, default=None)
    parser.add_argument("--generated-at", default=None)
    args = parser.parse_args(argv)
    try:
        summary = build_from_disk(root=args.root, generated_at=args.generated_at, out_path=args.out_path)
    except (ScenarioInputsError, ValueError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
