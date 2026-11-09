"""Accepted-input integration of direct terms into closed candidate terms (T0).

Capital Structure Intelligence V2, masterplan task T0 (gates A04, A08, A09).
This module adds no extraction, collector, resolver or network call.  It
composes the existing sealed compilers on an *accepted* C0 input generation:

    direct document terms (sealed parser, verified retained bytes)
      -> ``compile_candidate_term_records``  (append-only, one-to-one)
      -> ``current_candidate_terms_as_of``   (system-time visibility)

and re-proves the closed candidate boundary on every record it hands on:

* A candidate is pre-instrument.  Its ``authority`` block is exactly the closed
  block, and no key that would mint or imply an instrument identity or quantity
  appears at any depth.  Only the I0 resolver may mint an instrument, and only
  from an explicit owner decision.
* Identity is immutable and clock-independent (A04).  The occurrence identity
  (``logical_candidate_term_id``) is a digest of the source slot -- source
  manifest, table row and term -- plus the mapping version; never a name, a
  strike, a clock or a legacy key.  The version identity
  (``candidate_term_id``) is minted once and re-observation of the same bytes
  never re-mints it.  A later interpretation is a later correction, visible only
  from the system time it was compiled, never retroactive source knowledge.
* Only an accepted procedure mints a fact (A09).  Every direct term's origin is
  derived from its sealed extraction record and checked against the E0
  reference pack's ``fact_origins``.  External proposals -- LLM spans and
  interpretations, issuer assertions, model prose, or a bare *claim* of a
  canonical origin -- never enter the compile; each is returned as an explicit
  refusal with a reason.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from engine.capital_structure.document_terms import DOCUMENT_TERM_SCHEMA
from engine.capital_structure.instrument_candidates import (
    INSTRUMENT_CANDIDATE_TERM_SCHEMA,
    MAPPING_VERSION,
    candidate_term_id_for,
    compile_candidate_term_records,
    current_candidate_terms_as_of,
    logical_candidate_term_id_for,
)
from engine.capital_structure.issuer_state_contracts import (
    CalculationReceipt,
    CandidateBundle,
    CapitalInputs,
    GenerationBinding,
    sha256_of,
    stable_id,
)
from engine.capital_structure.reference_qualification import (
    CANONICAL_FACT_ORIGINS,
    NON_CANONICAL_FACT_ORIGINS,
    ReferencePack,
    fact_origin_is_canonical,
    load_reference_pack,
)

TERM_INTEGRATION_VERSION = "capital-structure-term-integration/1.0.0"
DIRECT_FAMILY = "document_terms"
CANDIDATE_FAMILY = "instrument_candidate_terms"

#: The only authority block a candidate term may carry.
CLOSED_CANDIDATE_AUTHORITY: Mapping[str, bool] = MappingProxyType({
    "is_context_only": True,
    "instrument_authority": False,
    "capacity_authority": False,
    "risk_authority": False,
    "probability_authority": False,
    "rank_authority": False,
    "sizing_authority": False,
    "entry_authority": False,
    "trade_authority": False,
    "prophet_authority": False,
})

#: Keys that would mint or imply an instrument identity, resolution or quantity.
#: Any of them at any depth of a candidate means the pre-instrument boundary broke.
INSTRUMENT_IDENTITY_KEYS = frozenset({
    "instrument_id",
    "instrument_candidate_id",
    "resolved_instrument_id",
    "instrument_set_id",
    "resolution",
    "resolution_id",
    "quantity_status",
    "outstanding_quantity",
})

#: Sealed direct-term extraction methods and the E0 fact origin each carries.
#: ``deferred`` is the canonical procedure declining to read a value: same
#: origin, but it bears no fact.
_EXTRACTION_METHOD_ORIGINS: Mapping[str, str] = MappingProxyType({
    "deterministic": "canonical_extraction",
    "deferred": "canonical_extraction",
})

#: Refusal reasons, closed.
REFUSAL_REASONS = (
    "fact_origin_not_canonical",
    "fact_origin_unknown",
    "canonical_origin_requires_sealed_procedure",
)


class TermIntegrationRefusal(ValueError):
    """An input would breach the closed candidate boundary or the A09 origin law."""


@dataclass(frozen=True)
class DirectTermOrigin:
    """E0 fact origin of one accepted direct term, derived from its sealed extraction."""

    observation_id: str
    logical_observation_id: str
    fact_origin: str
    extraction_method: str
    parser_version: str
    fact_bearing: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "logical_observation_id": self.logical_observation_id,
            "fact_origin": self.fact_origin,
            "extraction_method": self.extraction_method,
            "parser_version": self.parser_version,
            "fact_bearing": self.fact_bearing,
        }


@dataclass(frozen=True)
class TermRefusal:
    """An external proposal that was refused and never entered the compile."""

    nomination_id: str
    fact_origin: str
    reason: str

    def __post_init__(self) -> None:
        if self.reason not in REFUSAL_REASONS:
            raise TermIntegrationRefusal(f"refusal reason {self.reason!r} is not in {list(REFUSAL_REASONS)}")

    def as_record(self) -> dict[str, Any]:
        return {"nomination_id": self.nomination_id, "fact_origin": self.fact_origin, "reason": self.reason}


@dataclass(frozen=True)
class CandidateIntegration:
    """Closed candidate terms compiled from one accepted direct-term generation.

    ``records`` is the full append-only candidate ledger (existing plus this
    run's additions); ``current`` is the version of each occurrence visible at
    ``as_of``.  When the direct-term family is not supported, nothing was
    verified, so both are empty and ``support`` says why -- callers must never
    persist ``records`` from such an integration over an existing ledger.
    """

    source_binding: GenerationBinding
    support: str
    as_of: str
    generated_at: str
    records: tuple[dict[str, Any], ...]
    current: tuple[dict[str, Any], ...]
    counts: Mapping[str, int]
    origins: tuple[DirectTermOrigin, ...]
    refusals: tuple[TermRefusal, ...]
    receipt: CalculationReceipt

    @property
    def candidate_binding(self) -> GenerationBinding:
        """C0 binding of the ``instrument_candidate_terms`` family this integration supplies."""
        if self.support in ("supported", "partial"):
            return GenerationBinding(
                CANDIDATE_FAMILY,
                INSTRUMENT_CANDIDATE_TERM_SCHEMA,
                self.support,
                artifact_sha256=sha256_of(list(self.current)),
                as_of=self.as_of,
            )
        return GenerationBinding(CANDIDATE_FAMILY, None, self.support, as_of=self.as_of)

    def candidate_bundle(self) -> CandidateBundle:
        """The C0 ``CandidateBundle`` of current candidates -- the I0 resolver input."""
        return CandidateBundle(self.candidate_binding, tuple(deepcopy(list(self.current))), self.as_of)

    def as_record(self) -> dict[str, Any]:
        return {
            "version": TERM_INTEGRATION_VERSION,
            "source_binding": self.source_binding.as_record(),
            "candidate_binding": self.candidate_binding.as_record(),
            "support": self.support,
            "as_of": self.as_of,
            "generated_at": self.generated_at,
            "counts": dict(self.counts),
            "candidate_term_ids": [row["candidate_term_id"] for row in self.current],
            "origins": [item.as_record() for item in self.origins],
            "refusals": [item.as_record() for item in self.refusals],
            "receipt": self.receipt.as_record(),
        }


def _walk_keys(value: Any, path: str) -> list[str]:
    hits: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in INSTRUMENT_IDENTITY_KEYS:
                hits.append(f"{path}.{key}")
            hits.extend(_walk_keys(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            hits.extend(_walk_keys(item, f"{path}[{index}]"))
    return hits


def assert_closed_candidate_term(record: Mapping[str, Any]) -> None:
    """Re-prove that one candidate term is still a closed pre-instrument projection."""
    label = str(record.get("candidate_term_id") or "<candidate>")
    if record.get("schema") != INSTRUMENT_CANDIDATE_TERM_SCHEMA:
        raise TermIntegrationRefusal(f"{label}: schema {record.get('schema')!r} is not a candidate term")
    authority = record.get("authority")
    if not isinstance(authority, Mapping) or dict(authority) != dict(CLOSED_CANDIDATE_AUTHORITY):
        raise TermIntegrationRefusal(f"{label}: authority is not the closed candidate block")
    hits = _walk_keys(record, "<candidate>")
    if hits:
        raise TermIntegrationRefusal(f"{label}: instrument identity keys present: {hits}")
    if (record.get("candidate") or {}).get("mapping_version") != MAPPING_VERSION:
        raise TermIntegrationRefusal(f"{label}: unknown candidate mapping version")
    if record.get("candidate_term_id") != candidate_term_id_for(record):
        raise TermIntegrationRefusal(f"{label}: candidate_term_id is not the digest of its record")
    source = record.get("source_term") or {}
    if source.get("schema") != DOCUMENT_TERM_SCHEMA:
        raise TermIntegrationRefusal(f"{label}: source term is not a direct document term")
    expected_logical = logical_candidate_term_id_for({"logical_observation_id": source.get("logical_observation_id")})
    if record.get("logical_candidate_term_id") != expected_logical:
        raise TermIntegrationRefusal(f"{label}: occurrence identity is not derived from its source slot")


def direct_term_origin(record: Mapping[str, Any], pack: ReferencePack) -> DirectTermOrigin:
    """Derive one direct term's E0 fact origin from its sealed extraction record."""
    extraction = record.get("extraction") or {}
    method = str(extraction.get("method") or "")
    origin = _EXTRACTION_METHOD_ORIGINS.get(method)
    label = str(record.get("observation_id") or "<direct term>")
    if origin is None:
        raise TermIntegrationRefusal(
            f"{label}: extraction method {method!r} is not an accepted canonical procedure (fact_origin_not_canonical)"
        )
    if not (fact_origin_is_canonical(origin) and pack.fact_origins.get(origin) is True):
        raise TermIntegrationRefusal(f"{label}: fact origin {origin!r} may not mint under the reference pack")
    state = (record.get("state") or {}).get("disposition")
    return DirectTermOrigin(
        observation_id=label,
        logical_observation_id=str(record.get("logical_observation_id") or ""),
        fact_origin=origin,
        extraction_method=method,
        parser_version=str(extraction.get("parser_version") or ""),
        fact_bearing=method == "deterministic" and state == "observed",
    )


def refuse_nomination(nomination: Mapping[str, Any], pack: ReferencePack) -> TermRefusal:
    """Refuse one external fact proposal with an explicit reason.

    A proposal never mints a candidate.  Non-canonical origins are refused as
    such; a proposal *claiming* a canonical origin is refused too, because a
    canonical fact enters only through the sealed direct-term procedure (or a
    reference-pack-pinned gold fixture), never through an assertion that it did.
    """
    if not isinstance(nomination, Mapping):
        raise TermIntegrationRefusal("nomination must be a mapping")
    origin = str(nomination.get("fact_origin") or "")
    nomination_id = stable_id("term-nomination", dict(nomination))
    known = pack.fact_origins.get(origin)
    if known is None or origin not in (CANONICAL_FACT_ORIGINS | NON_CANONICAL_FACT_ORIGINS):
        reason = "fact_origin_unknown"
    elif known is True and fact_origin_is_canonical(origin):
        reason = "canonical_origin_requires_sealed_procedure"
    else:
        reason = "fact_origin_not_canonical"
    return TermRefusal(nomination_id=nomination_id, fact_origin=origin, reason=reason)


def _assert_pack_law(pack: ReferencePack) -> None:
    for origin in CANONICAL_FACT_ORIGINS:
        if pack.fact_origins.get(origin) is not True:
            raise TermIntegrationRefusal(f"reference pack does not let canonical origin {origin!r} mint")
    for origin in NON_CANONICAL_FACT_ORIGINS:
        if pack.fact_origins.get(origin) is not False:
            raise TermIntegrationRefusal(f"reference pack lets non-canonical origin {origin!r} mint")


def _rule_digest(pack: ReferencePack) -> str:
    return sha256_of({
        "term_integration": TERM_INTEGRATION_VERSION,
        "candidate_schema": INSTRUMENT_CANDIDATE_TERM_SCHEMA,
        "mapping_version": MAPPING_VERSION,
        "direct_schema": DOCUMENT_TERM_SCHEMA,
        "extraction_method_origins": dict(_EXTRACTION_METHOD_ORIGINS),
        "fact_origins": dict(pack.fact_origins),
        "closed_authority": dict(CLOSED_CANDIDATE_AUTHORITY),
    })


def integrate_candidate_terms(
    inputs: CapitalInputs,
    *,
    source_manifests: Sequence[Mapping[str, Any]],
    source_reader: Callable[[Mapping[str, Any]], bytes | None],
    generated_at: str,
    as_of: str,
    existing_candidate_terms: Sequence[Mapping[str, Any]] = (),
    nominations: Sequence[Mapping[str, Any]] = (),
    reference_pack: ReferencePack | None = None,
) -> CandidateIntegration:
    """Compile closed candidate terms from the accepted direct-term generation in ``inputs``.

    Deterministic and offline: no HTTP, no LLM, no SEC request.  Fails closed
    (raises) on a missing direct-term binding, a non-canonical direct-term
    origin, a reference pack that would let a non-canonical origin mint, any
    sealed-gate failure, or any candidate that is not a closed projection.
    """
    if not isinstance(inputs, CapitalInputs):
        raise TermIntegrationRefusal("inputs must be a C0 CapitalInputs")
    pack = reference_pack if reference_pack is not None else load_reference_pack()
    _assert_pack_law(pack)
    binding = inputs.binding(DIRECT_FAMILY)
    if binding is None:
        raise TermIntegrationRefusal("inputs carry no document_terms binding; bind it explicitly, even as unavailable")
    existing = [deepcopy(dict(row)) for row in existing_candidate_terms]
    bound_existing = [deepcopy(dict(row)) for row in inputs.candidate_terms]
    if existing and bound_existing and sha256_of(existing) != sha256_of(bound_existing):
        raise TermIntegrationRefusal("existing candidate terms differ from the candidate terms bound in inputs")
    existing = existing or bound_existing
    refusals = tuple(refuse_nomination(item, pack) for item in nominations)
    direct = [deepcopy(dict(row)) for row in inputs.document_terms]
    receipt = CalculationReceipt.build(
        inputs={
            "source_binding": binding.as_record(),
            "document_terms_sha256": sha256_of(direct),
            "existing_candidate_terms_sha256": sha256_of(existing),
            "source_manifests_sha256": sha256_of([dict(item) for item in source_manifests]),
            "generated_at": generated_at,
            "as_of": as_of,
        },
        rule_digest=_rule_digest(pack),
        implementation=TERM_INTEGRATION_VERSION,
        computed_at=generated_at,
    )
    if binding.support not in ("supported", "partial"):
        return CandidateIntegration(
            source_binding=binding, support=binding.support, as_of=as_of, generated_at=generated_at,
            records=(), current=(),
            counts=MappingProxyType({"input_document_terms": 0, "created": 0, "unchanged": 0, "total": 0,
                                     "existing_unverified": len(existing)}),
            origins=(), refusals=refusals, receipt=receipt,
        )
    origins = tuple(direct_term_origin(row, pack) for row in direct)
    for row in existing:
        assert_closed_candidate_term(row)
    compiled = compile_candidate_term_records(
        direct,
        source_manifests=source_manifests,
        source_reader=source_reader,
        existing_candidate_terms=existing,
        generated_at=generated_at,
    )
    records = tuple(compiled["observations"])
    for row in records:
        assert_closed_candidate_term(row)
    current = tuple(current_candidate_terms_as_of(
        list(records),
        as_of,
        document_term_observations=direct,
        source_manifests=source_manifests,
        source_reader=source_reader,
    ))
    return CandidateIntegration(
        source_binding=binding, support=binding.support, as_of=as_of, generated_at=generated_at,
        records=records, current=current, counts=MappingProxyType(dict(compiled["counts"])),
        origins=origins, refusals=refusals, receipt=receipt,
    )


__all__ = [
    "CANDIDATE_FAMILY",
    "CLOSED_CANDIDATE_AUTHORITY",
    "CandidateIntegration",
    "DIRECT_FAMILY",
    "DirectTermOrigin",
    "INSTRUMENT_IDENTITY_KEYS",
    "REFUSAL_REASONS",
    "TERM_INTEGRATION_VERSION",
    "TermIntegrationRefusal",
    "TermRefusal",
    "assert_closed_candidate_term",
    "direct_term_origin",
    "integrate_candidate_terms",
    "refuse_nomination",
]
