"""``engine/news_impact/transfer.py`` — the A4 one-hop transfer layer.

Implements the one-hop supplier/customer transfer record of MASTERPLAN.md
section 8 (record target generator, role/direction, mechanism, exposure or
UNKNOWN, timing, alternatives, graph provenance, and a cited span naming
BOTH parties) as frozen spec sections 4.1-4.6 and 4.8 of the seat-accepted
Phase 1 design packet ``designs/A4_transfer_obs/A4_transfer_obs.md``, under
the Phase 0 freeze (PHASE0_FREEZE_2026-10-11 D12 identity = ``cik:`` + 10
digits, D13/D14 evidence = owner ``source_span.v1`` or ``field_absence.v1``,
closed enums, no confidence/probability/price-target/score field anywhere).
Abstention is the default outcome: every examined candidate that does not
pass every gate emits a schema-valid ``transfer_absence.v1`` naming the
first failing gate (design 4.3/4.4).

Seat rulings bound (Wave 3): ``V_TWO_PARTY_SPAN`` is never skipped and has
no off parameter; graph/GMI generator kinds are candidate-only inputs and
never admission evidence (design 4.2: the only legal generator_kind on an
emitted edge is ``source_span_two_party``); exposure is UNKNOWN in v1;
``target_role`` is the closed four-value enum; ``macro_shock_fanout.v1``
is consumed as a ``$def`` inside ``transfer_edge.v1.schema.json``; the
residual factor set is ``{market, documented_peer_residual}`` (declared
here for the observation lane; this module emits no residuals).  Section
4.7 (observation windows) belongs to a separate lane and is NOT built
here.  Section 4.6 peer-set preselection is provided as a pure value
builder for that lane.

Deterministic by construction: ids are sha256 prefixes over canonical JSON
of the record identity, iteration is sorted or caller-ordered, ``as_of`` /
``observed_at`` are always parameters, no clock reads, no randomness, no
network, no module-level I/O (the contract is read lazily by
:func:`load_transfer_schema`).  Mention text, quotes and fixtures are DATA
(masterplan section 3.5): nothing in them is ever interpreted as an
instruction; a detected unsolicited instruction forces the
``instruction_detected`` absence and nothing else.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date as _date
from hashlib import sha256
from pathlib import Path
from typing import Any

from engine.news_impact.issuer import Mention, resolve_mention

TRANSFER_SCHEMA_NAME = "transfer_edge.v1.schema.json"
SPAN_GATE_GENERATOR_ID = "span_gate.v1"

# ------------------------------------------------------------- closed worlds
# Mirrors of contracts_w3/news_impact/transfer_edge.v1.schema.json $defs.
# test_news_impact_transfer.py cross-checks every one against the schema.

TARGET_ROLES: tuple[str, ...] = ("customer", "supplier", "competitor", "partner")
EDGE_DIRECTIONS: tuple[str, ...] = ("source_to_target", "target_to_source")
OPERATING_EFFECTS: tuple[str, ...] = ("positive", "negative", "mixed", "unknown")
CHANNELS: tuple[str, ...] = (
    "revenue_demand", "margin_cost", "capital_allocation", "moat_duration",
    "strategic_option", "financial_incentives_survival", "market_only")
GENERATOR_KINDS: tuple[str, ...] = (
    "source_span_two_party", "gmi_member_of", "gmi_supplies_reserved",
    "gmi_expresses", "gmi_tracks", "group_reads_basket",
    "group_linked_outsiders", "demand_chain_hardcoded", "gics_peer",
    "residual_comovement", "tagged_ticker_list", "shock_exposure_roster")
GRAPH_NAMES: tuple[str, ...] = (
    "economic_relationship", "fundamental_comparability", "residual_market")
ABSTENTION_REASONS: tuple[str, ...] = (
    "no_two_party_span", "span_names_one_party_only", "target_identity_unresolved",
    "source_equals_target", "hop_exceeds_one", "cycle_on_source_fact",
    "graph2_membership_only", "graph3_residual_only", "participation_only_refused",
    "gmi_member_of_only", "demand_chain_list_only", "linked_outsider_role_unlabeled",
    "role_incidental_or_unknown", "channel_market_only_no_graph1",
    "source_fact_not_validated", "source_fact_negated",
    "source_fact_superseded_stale_cite", "body_unavailable", "rights_redacted",
    "parse_failed", "name_resolution_ambiguous", "instruction_detected",
    "llm_relatedness_tag_refused", "structure_learner_refused",
    "causal_dag_refused", "peer_selected_by_rally",
    "no_documented_exposure_for_shock", "competitor_without_competitive_claim",
    "second_hop_refused", "k3d_participation_only_hold")

# Candidate-only generators (design 4.2 "On an emitted edge the only legal
# generator_kind is source_span_two_party"; Appendix B consumption map).
# A candidate carrying one of these kinds can never be admitted; it is
# recorded on the absence as refused_generator under the mapped reason.
# gmi_supplies_reserved (Graph-1 but graph-side) and shock_exposure_roster
# (fanout roster row) are deliberately absent: they fall through to the
# span gates (seat ruling on design section 7 defaults 2 and 4.5 step 3).
GENERATOR_GATE_REASON: dict[str, str] = {
    "gmi_member_of": "gmi_member_of_only",
    "gmi_expresses": "graph2_membership_only",
    "gmi_tracks": "graph2_membership_only",
    "group_reads_basket": "graph2_membership_only",
    "gics_peer": "graph2_membership_only",
    "residual_comovement": "graph3_residual_only",
    "tagged_ticker_list": "llm_relatedness_tag_refused",
    "demand_chain_hardcoded": "demand_chain_list_only",
    "group_linked_outsiders": "linked_outsider_role_unlabeled",
}

# Declarative candidate disqualifiers -> design 4.4 reason, checked in this
# fixed order (the design section 4.4 numeric order of the reasons).
REFUSAL_FLAG_REASONS: tuple[tuple[str, str], ...] = (
    ("participation_only", "participation_only_refused"),
    ("body_unavailable", "body_unavailable"),
    ("rights_redacted", "rights_redacted"),
    ("parse_failed", "parse_failed"),
    ("llm_relatedness_tag", "llm_relatedness_tag_refused"),
    ("structure_learner", "structure_learner_refused"),
    ("causal_dag", "causal_dag_refused"),
    ("selected_by_rally", "peer_selected_by_rally"),
    ("k3d_participation_only", "k3d_participation_only_hold"),
)
REFUSAL_FLAGS: frozenset[str] = frozenset(f for f, _ in REFUSAL_FLAG_REASONS)

# V_COMPETITOR_CLAIM (design 4.2): the span must state a competitive
# relationship (displace, take share, rival product), not co-membership.
COMPETITIVE_MARKERS: tuple[str, ...] = (
    "displace", "take share", "taking share", "takes share", "rival",
    "compete", "compet", "market share", "wins share", "loses share")

# Design 4.6: the only legal v1 peer-set selector; the rest are absent.
PEER_SET_SELECTION = "documented_exposure"
FORBIDDEN_PEER_SELECTORS: frozenset[str] = frozenset({
    "rallied_most", "participation_only", "gmi_member_of_only",
    "residual_comovement_group", "mag7_membership"})

# Seat ruling: residual factor set is {market, documented_peer_residual}
# (design section 7 default 3).  Declared for the observation lane; this
# module emits no residual numbers.
RESIDUAL_FACTOR_IDS: tuple[str, ...] = ("market", "documented_peer_residual")

# W3-R3: keys stripped at ingest, never passed through.
FORBIDDEN_INBOUND_KEYS: frozenset[str] = frozenset({
    "confidence", "probability", "likelihood", "score", "sentiment",
    "contagion", "price_target", "target_price", "fair_value",
    "valuation_target", "rating_score"})

_COMPANY_ID_RE = re.compile(r"^cik:(?!0{10}$)[0-9]{10}$")
_FACT_ID_RE = re.compile(r"^fact_[0-9a-f]{24}$")
_TRANSFER_ID_RE = re.compile(r"^xfer_[0-9a-f]{24}$")
_SHOCK_ID_RE = re.compile(r"^shock_[0-9a-f]{24}$")
_ISO_Z_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

# ---------------------------------------------------------------- error codes

class TransferError(Exception):
    """Raised for malformed injected input (never for a gate rejection).

    ``code`` is one of :data:`CODES` (W3-R5).  A gate rejection is a typed
    absence, not an error: abstention is the default outcome.
    """

    code: str

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


CODES = frozenset({
    "UNKNOWN_CANDIDATE_KEY", "UNKNOWN_REFUSAL_FLAG", "UNKNOWN_GENERATOR_KIND",
    "UNKNOWN_GRAPH", "UNKNOWN_CHANNEL", "UNKNOWN_TARGET_ROLE",
    "UNKNOWN_OPERATING_EFFECT", "UNKNOWN_EDGE_DIRECTION",
    "MALFORMED_COMPANY_ID", "MALFORMED_FACT_ID", "MALFORMED_TRANSFER_ID",
    "MALFORMED_SHOCK_ID", "MALFORMED_TIMESTAMP", "HOP_COUNT_INVALID",
    "MISSING_SOURCE_COMPANY", "DISPLAY_SUMMARY_REQUIRED",
    "TARGET_IDENTITY_CONFLICT", "CANDIDATE_SPAN_MALFORMED",
    "EVIDENCE_SPAN_MALFORMED", "ROSTER_TOO_SMALL", "ROSTER_TOO_LARGE",
    "ROSTER_DUPLICATE_COMPANY", "ROSTER_ROW_MALFORMED",
    "ROSTER_NAME_REQUIRED", "PEER_SET_EMPTY", "PEER_SET_TOO_LARGE",
    "PEER_SET_CONTAINS_TARGET", "UNKNOWN_PEER_SELECTOR",
    "ABSENCE_REASON_UNKNOWN", "SOURCE_COMPANY_MISMATCH",
})


# ------------------------------------------------------------------- helpers

def canonical_json(obj: Any) -> str:
    """Canonical JSON (W3-R2): sorted keys, compact separators, no ASCII escapes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _mint_id(prefix: str, *identity: str) -> str:
    """Deterministic 24-hex id: sha256 over the pipe-joined identity tuple."""
    return prefix + sha256("|".join(identity).encode("utf-8")).hexdigest()[:24]


def _check_company_id(value: str, what: str) -> str:
    if not isinstance(value, str) or not _COMPANY_ID_RE.match(value):
        raise TransferError("MALFORMED_COMPANY_ID", f"{what} {value!r} is not cik: + 10 digits")
    return value


def _check_timestamp(value: str, what: str) -> str:
    if not isinstance(value, str) or not _ISO_Z_RE.match(value):
        raise TransferError("MALFORMED_TIMESTAMP", f"{what} {value!r} is not UTC YYYY-MM-DDTHH:MM:SSZ")
    return value


def _field_absence(reason: str, subject: str, detail: str = "",
                   missing_fields: Iterable[str] = ()) -> dict[str, Any]:
    if reason not in ("not_stated", "stated_without_number", "range_only",
                      "redacted_rights", "parse_failed"):
        raise TransferError("ABSENCE_REASON_UNKNOWN", f"absence reason {reason!r} not in the frozen enum")
    return {
        "schema": "field_absence.v1",
        "authority": "context_only",
        "reason": reason,
        "subject": subject,
        "detail": detail,
        "missing_fields": sorted(set(missing_fields)),
    }


def load_transfer_schema(path: str | Path | None = None) -> dict:
    """Read the frozen transfer contract lazily (no module-level I/O).

    Default path is ``<repo>/contracts/news_impact/transfer_edge.v1.schema.json``
    relative to this module, which resolves to the frozen Phase 1 contract
    in the harness overlay (``contracts_w3``).
    """
    p = Path(path) if path is not None else \
        Path(__file__).resolve().parents[2] / "contracts" / "news_impact" / TRANSFER_SCHEMA_NAME
    return json.loads(p.read_text(encoding="utf-8"))


def strip_forbidden_keys(data: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    """W3-R3 ingest strip: drop forbidden keys, return them sorted by name.

    Unknown-but-not-forbidden keys are NOT stripped here; the closed
    candidate vocabulary rejects them (freeze S12/R4: unknown keys are
    rejected, never silently dropped).
    """
    stripped = sorted(k for k in data if k in FORBIDDEN_INBOUND_KEYS)
    clean = {k: v for k, v in data.items() if k not in FORBIDDEN_INBOUND_KEYS}
    return clean, tuple(stripped)


# ------------------------------------------------------------ value objects

@dataclass(frozen=True)
class SourceFact:
    """The cited news-impact fact, injected as data (never re-derived here).

    ``accepted`` mirrors the fact's validation state; ``novelty`` is the
    frozen event novelty (``corrected_fact`` engages V_SOURCE_FACT);
    ``superseded_by_fact_id`` is set when a later accepted correction has
    already superseded THIS fact (citing it is then stale);
    ``lineage_fact_ids`` is the fact's correction lineage including itself
    (V_ONE_HOP / V_NO_CYCLE scope), defaulting to the fact alone.
    """

    fact_id: str
    company_id: str
    accepted: bool = True
    novelty: str | None = None
    negated: bool = False
    superseded_by_fact_id: str | None = None
    instruction_detected: bool = False
    lineage_fact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.fact_id, str) or not _FACT_ID_RE.match(self.fact_id):
            raise TransferError("MALFORMED_FACT_ID", f"fact_id {self.fact_id!r} is not fact_ + 24 hex")
        _check_company_id(self.company_id, "SourceFact.company_id")
        lineage = tuple(sorted(set(self.lineage_fact_ids) | {self.fact_id}))
        object.__setattr__(self, "lineage_fact_ids", lineage)
        for other in lineage:
            if not _FACT_ID_RE.match(other):
                raise TransferError("MALFORMED_FACT_ID", f"lineage id {other!r} is not fact_ + 24 hex")
        if self.superseded_by_fact_id is not None and \
                not _FACT_ID_RE.match(self.superseded_by_fact_id):
            raise TransferError("MALFORMED_FACT_ID",
                                f"superseded_by_fact_id {self.superseded_by_fact_id!r} is not fact_ + 24 hex")

    @property
    def lineage(self) -> tuple[str, ...]:
        """Fact ids in this fact's correction lineage, sorted, self included."""
        return self.lineage_fact_ids


@dataclass(frozen=True)
class PriorTransfer:
    """An already-minted transfer on a fact lineage, injected as data."""

    transfer_id: str
    source_fact_id: str
    source_company_id: str
    target_company_id: str
    observed_at: str

    def __post_init__(self) -> None:
        if not _TRANSFER_ID_RE.match(self.transfer_id):
            raise TransferError("MALFORMED_TRANSFER_ID",
                                f"transfer_id {self.transfer_id!r} is not xfer_ + 24 hex")
        if not _FACT_ID_RE.match(self.source_fact_id):
            raise TransferError("MALFORMED_FACT_ID",
                                f"source_fact_id {self.source_fact_id!r} is not fact_ + 24 hex")
        _check_company_id(self.source_company_id, "PriorTransfer.source_company_id")
        _check_company_id(self.target_company_id, "PriorTransfer.target_company_id")
        _check_timestamp(self.observed_at, "PriorTransfer.observed_at")


@dataclass(frozen=True)
class TransferCandidate:
    """One examined transfer candidate (design 4.2 inputs, injected as data).

    ``target_company_id`` is the resolved second issuer, or ``None`` with
    ``target_mention`` left for the D12 ladder.  ``span`` is the owner
    ``source_span.v1`` payload of the cited sentence and ``claimed_quote``
    its projector-side stand-in; together they are the only authorizing
    evidence (``V_TWO_PARTY_SPAN`` has no off switch).  ``refusal_flags``
    are declarative disqualifiers from :data:`REFUSAL_FLAGS`.
    ``stripped_fields`` records forbidden keys removed at ingest (W3-R3).
    """

    source_company_id: str
    target_company_id: str | None = None
    target_mention: Mention | None = None
    target_role: str | None = None
    generator_kind: str = "source_span_two_party"
    generator_id: str = SPAN_GATE_GENERATOR_ID
    graph: str = "economic_relationship"
    hop_count: int = 1
    mechanism_channel: str = "revenue_demand"
    operating_effect_on_target: str = "unknown"
    edge_direction: str = "source_to_target"
    claimed_quote: str | None = None
    span: Mapping[str, Any] | None = None
    exposure_absence: Mapping[str, Any] | None = None
    timing: Mapping[str, Any] | None = None
    alternatives: Any = None
    refusal_flags: frozenset[str] = frozenset()
    shock_id: str | None = None
    supersedes_transfer_id: str | None = None
    transfer_id: str | None = None
    display_summary: str | None = None
    absence_display_summary: str | None = None
    span_absence_detail: str = ""
    absence_two_party_span: Mapping[str, Any] | None = None
    stripped_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_company_id(self.source_company_id, "candidate source")
        if self.target_company_id is not None:
            _check_company_id(self.target_company_id, "candidate target")
        if self.generator_kind not in GENERATOR_KINDS:
            raise TransferError("UNKNOWN_GENERATOR_KIND",
                                f"generator_kind {self.generator_kind!r} not in the closed enum")
        if self.graph not in GRAPH_NAMES:
            raise TransferError("UNKNOWN_GRAPH", f"graph {self.graph!r} not in the closed enum")
        if self.mechanism_channel not in CHANNELS:
            raise TransferError("UNKNOWN_CHANNEL",
                                f"mechanism_channel {self.mechanism_channel!r} not in the frozen seven")
        if self.target_role is not None and self.target_role not in TARGET_ROLES:
            raise TransferError("UNKNOWN_TARGET_ROLE",
                                f"target_role {self.target_role!r} not in the closed enum")
        if self.operating_effect_on_target not in OPERATING_EFFECTS:
            raise TransferError("UNKNOWN_OPERATING_EFFECT",
                                f"operating_effect_on_target {self.operating_effect_on_target!r} not in the enum")
        if self.edge_direction not in EDGE_DIRECTIONS:
            raise TransferError("UNKNOWN_EDGE_DIRECTION",
                                f"edge_direction {self.edge_direction!r} not in the enum")
        if not isinstance(self.hop_count, int) or isinstance(self.hop_count, bool) or self.hop_count < 1:
            raise TransferError("HOP_COUNT_INVALID", f"hop_count {self.hop_count!r} is not an integer >= 1")
        unknown = sorted(set(self.refusal_flags) - REFUSAL_FLAGS)
        if unknown:
            raise TransferError("UNKNOWN_REFUSAL_FLAG", f"refusal flags {unknown} not in the closed set")
        object.__setattr__(self, "refusal_flags", frozenset(self.refusal_flags))
        if self.shock_id is not None and not _SHOCK_ID_RE.match(self.shock_id):
            raise TransferError("MALFORMED_SHOCK_ID", f"shock_id {self.shock_id!r} is not shock_ + 24 hex")
        for id_field in ("supersedes_transfer_id", "transfer_id"):
            value = getattr(self, id_field)
            if value is not None and not _TRANSFER_ID_RE.match(value):
                raise TransferError("MALFORMED_TRANSFER_ID", f"{id_field} {value!r} is not xfer_ + 24 hex")
        if self.span is not None and (not isinstance(self.span, Mapping)
                                      or self.span.get("schema") != "source_span.v1"):
            raise TransferError("CANDIDATE_SPAN_MALFORMED",
                                "span must be an owner source_span.v1 mapping")
        object.__setattr__(self, "refusal_flags", frozenset(sorted(self.refusal_flags)))


# ------------------------------------------------------- dict ingest (W3-R3)

_CANDIDATE_KEYS = frozenset({
    "source_company_id", "target_company_id", "target_mention", "target_role",
    "generator_kind", "generator_id", "graph", "hop_count", "mechanism_channel",
    "operating_effect_on_target", "edge_direction", "claimed_quote", "span",
    "exposure_absence", "timing", "alternatives", "refusal_flags", "shock_id",
    "supersedes_transfer_id", "transfer_id", "display_summary",
    "absence_display_summary", "span_absence_detail", "absence_two_party_span",
})


def candidate_from_dict(data: Mapping[str, Any]) -> TransferCandidate:
    """Ingest one plain-dict candidate: strip forbidden keys (recorded),
    reject unknown keys, resolve the closed enums, build the frozen value.

    ``target_mention`` is ``{ticker, cik, text, asof}`` (owner
    :class:`engine.news_impact.issuer.Mention` shape; ``asof`` ISO date).
    """
    clean, stripped = strip_forbidden_keys(data)
    unknown = sorted(set(clean) - _CANDIDATE_KEYS)
    if unknown:
        raise TransferError("UNKNOWN_CANDIDATE_KEY", f"candidate keys {unknown} not in the closed vocabulary")
    if "source_company_id" not in clean:
        raise TransferError("MISSING_SOURCE_COMPANY",
                            "a candidate requires source_company_id (the source fact's issuer)")
    kwargs: dict[str, Any] = {k: v for k, v in clean.items() if k != "target_mention"}
    kwargs["refusal_flags"] = frozenset(clean.get("refusal_flags", ()))
    kwargs["stripped_fields"] = stripped
    mention_data = clean.get("target_mention")
    if mention_data is not None:
        if not isinstance(mention_data, Mapping):
            raise TransferError("TARGET_IDENTITY_CONFLICT", "target_mention must be a mapping")
        asof = mention_data.get("asof")
        if isinstance(asof, str):
            asof = _date.fromisoformat(asof)
        kwargs["target_mention"] = Mention(
            text=str(mention_data.get("text", "")),
            ticker=mention_data.get("ticker"),
            cik=mention_data.get("cik"),
            exchange_mic=mention_data.get("exchange_mic"),
            asof=asof,
        )
    return TransferCandidate(**kwargs)


def source_fact_from_dict(data: Mapping[str, Any]) -> SourceFact:
    """Ingest one plain-dict source fact (same strip/reject ingest law)."""
    allowed = {"fact_id", "company_id", "accepted", "novelty", "negated",
               "superseded_by_fact_id", "instruction_detected", "lineage_fact_ids"}
    clean, _stripped = strip_forbidden_keys(data)
    unknown = sorted(set(clean) - allowed)
    if unknown:
        raise TransferError("UNKNOWN_CANDIDATE_KEY", f"source fact keys {unknown} not in the closed vocabulary")
    return SourceFact(**clean)


# --------------------------------------------------------- V_TWO_PARTY_SPAN

def span_parties(text: str, aliases: Mapping[str, str]) -> frozenset[str]:
    """Company ids the text names, via the injected alias -> company_id table.

    Tokens are alphanumeric runs, upper-cased; a token resolves when the
    alias table carries it.  Sibling aliases (GOOGL/GOOG) that map to one
    CIK therefore count as ONE party (design P1/4.2 V_TWO_PARTY_SPAN).
    """
    if not isinstance(text, str) or not isinstance(aliases, Mapping):
        return frozenset()
    resolved = set()
    for token in _TOKEN_RE.findall(text):
        company_id = aliases.get(token) or aliases.get(token.upper())
        if company_id is not None:
            resolved.add(company_id)
    return frozenset(resolved)


def names_both_parties(text: str, source_company_id: str, target_company_id: str,
                       aliases: Mapping[str, str]) -> bool:
    """``V_TWO_PARTY_SPAN``: the replayed bytes resolve to BOTH parties."""
    parties = span_parties(text, aliases)
    return source_company_id in parties and target_company_id in parties


def _replay_text(candidate: TransferCandidate) -> str:
    """The projector-side stand-in for the replayed bytes (design P1):
    the claimed quote, plus the span's display excerpt when one is held."""
    parts = [candidate.claimed_quote or ""]
    excerpt = candidate.span.get("display_excerpt") if isinstance(candidate.span, Mapping) else None
    if isinstance(excerpt, str):
        parts.append(excerpt)
    return " ".join(p for p in parts if p)


# ------------------------------------------------------ emission value types

def _prophet_flags() -> dict[str, bool]:
    return {"may_rank": False, "may_size": False, "may_gate": False,
            "prophet_authority": False}


@dataclass(frozen=True)
class TransferEdge:
    """An emitted ``transfer_edge.v1`` record (every gate passed)."""

    source_fact_id: str
    source_company_id: str
    target_company_id: str
    target_role: str
    edge_direction: str
    operating_effect_on_target: str
    mechanism_channel: str
    exposure: dict[str, Any]
    timing: dict[str, Any]
    alternatives: Any
    generator_id: str
    observed_at: str
    source_available_at: str
    display_summary: str
    two_party_span: dict[str, Any]
    transfer_id: str
    shock_id: str | None = None
    supersedes_transfer_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "transfer_edge.v1",
            "authority": "context_only",
            "prophet_flags": _prophet_flags(),
            "unsolicited_instruction_detected": False,
            "transfer_id": self.transfer_id,
            "source_fact_id": self.source_fact_id,
            "source_company_id": self.source_company_id,
            "target_company_id": self.target_company_id,
            "target_role": self.target_role,
            "edge_direction": self.edge_direction,
            "operating_effect_on_target": self.operating_effect_on_target,
            "mechanism_channel": self.mechanism_channel,
            "exposure": self.exposure,
            "timing": self.timing,
            "alternatives": self.alternatives,
            "graph_provenance": {
                "graph": "economic_relationship",
                "generator_kind": "source_span_two_party",
                "generator_id": self.generator_id,
                "as_of": self.observed_at,
                "belief_time": self.observed_at,
                "hop_count": 1,
                "path": [self.source_company_id, self.target_company_id],
            },
            "two_party_span": self.two_party_span,
            "shock_id": self.shock_id,
            "supersedes_transfer_id": self.supersedes_transfer_id,
            "observed_at": self.observed_at,
            "source_available_at": self.source_available_at,
            "display_summary": self.display_summary,
        }


@dataclass(frozen=True)
class TransferAbsence:
    """A typed ``transfer_absence.v1`` non-edge — the default outcome."""

    source_fact_id: str
    source_company_id: str
    abstention_reason: str
    observed_at: str
    source_available_at: str
    display_summary: str
    absence_id: str
    candidate_target_company_id: Any
    refused_generator: Any
    two_party_span: Any
    unsolicited_instruction_detected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "transfer_absence.v1",
            "authority": "context_only",
            "prophet_flags": _prophet_flags(),
            "unsolicited_instruction_detected": self.unsolicited_instruction_detected,
            "absence_id": self.absence_id,
            "source_fact_id": self.source_fact_id,
            "source_company_id": self.source_company_id,
            "candidate_target_company_id": self.candidate_target_company_id,
            "abstention_reason": self.abstention_reason,
            "refused_generator": self.refused_generator,
            "two_party_span": self.two_party_span,
            "observed_at": self.observed_at,
            "source_available_at": self.source_available_at,
            "display_summary": self.display_summary,
        }


@dataclass(frozen=True)
class MacroShockFanout:
    """A ``macro_shock_fanout.v1`` record: one shock, analysed once (4.5).

    The fanout does not mint edges by itself (design A6): roster rows carry
    either the id of a transfer minted from documented exposure or a typed
    ``field_absence.v1`` ref.
    """

    shock_id: str
    source_fact_id: str
    shock_span: dict[str, Any]
    exposure_roster: tuple[dict[str, Any], ...]
    observed_at: str
    source_available_at: str
    display_summary: str
    stripped_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "macro_shock_fanout.v1",
            "authority": "context_only",
            "prophet_flags": _prophet_flags(),
            "shock_id": self.shock_id,
            "source_fact_id": self.source_fact_id,
            "shock_span": self.shock_span,
            "analysed_once": True,
            "exposure_roster": [row for row in self.exposure_roster],
            "observed_at": self.observed_at,
            "source_available_at": self.source_available_at,
            "display_summary": self.display_summary,
        }


@dataclass(frozen=True)
class TransferResult:
    """Edges and absences for one source fact, plus the ingest strip record."""

    edges: tuple[TransferEdge, ...] = ()
    absences: tuple[TransferAbsence, ...] = ()
    stripped_fields: tuple[str, ...] = ()

    def to_dicts(self) -> list[dict[str, Any]]:
        """Every record, deterministically ordered by (schema, id)."""
        records = [e.to_dict() for e in self.edges] + [a.to_dict() for a in self.absences]
        return sorted(records, key=lambda r: (r["schema"], r.get("transfer_id", r.get("absence_id"))))


# ---------------------------------------------------------------- the gates

def _absence_target_payload(candidate: TransferCandidate, resolved_id: str | None,
                            ambiguity_note: str | None) -> Any:
    if resolved_id is not None:
        return resolved_id
    detail = (f"issuer identity ambiguous: {ambiguity_note}" if ambiguity_note
              else "issuer identity unresolved at source_available_at")
    return _field_absence("not_stated", "candidate_target_company_id", detail,
                          missing_fields=("candidate_target_company_id",))


def _refused_generator(candidate: TransferCandidate, resolved_id: str | None,
                       observed_at: str) -> Any:
    if resolved_id is None:
        return _field_absence("not_stated", "refused_generator",
                              "candidate target unresolved; no graph path recorded")
    return {
        "graph": candidate.graph,
        "generator_kind": candidate.generator_kind,
        "generator_id": candidate.generator_id,
        "as_of": observed_at,
        "belief_time": observed_at,
        "hop_count": 1,
        "path": [candidate.source_company_id, resolved_id],
    }


def _absence(candidate: TransferCandidate, source_fact: SourceFact, reason: str,
             *, resolved_id: str | None, ambiguity_note: str | None,
             observed_at: str, source_available_at: str) -> TransferAbsence:
    if reason not in ABSTENTION_REASONS:
        raise TransferError("ABSENCE_REASON_UNKNOWN", f"reason {reason!r} not in the closed enum")
    target = _absence_target_payload(candidate, resolved_id, ambiguity_note)
    span_payload = candidate.absence_two_party_span if candidate.absence_two_party_span is not None else \
        _field_absence("not_stated", "two_party_span", candidate.span_absence_detail)
    summary = candidate.absence_display_summary or \
        f"No transfer edge is emitted; abstention reason {reason}."
    return TransferAbsence(
        absence_id=_mint_id("xfer_", "transfer_absence.v1", source_fact.fact_id,
                            candidate.source_company_id, str(resolved_id),
                            reason, candidate.generator_kind),
        source_fact_id=source_fact.fact_id,
        source_company_id=candidate.source_company_id,
        abstention_reason=reason,
        observed_at=observed_at,
        source_available_at=source_available_at,
        display_summary=summary,
        candidate_target_company_id=target,
        refused_generator=_refused_generator(candidate, resolved_id, observed_at),
        two_party_span=span_payload,
        unsolicited_instruction_detected=(reason == "instruction_detected"),
    )


def _latest_prior(priors: Sequence[PriorTransfer]) -> PriorTransfer:
    return max(priors, key=lambda p: (p.observed_at, p.transfer_id))


def evaluate_candidate(
    candidate: TransferCandidate,
    source_fact: SourceFact,
    *,
    aliases: Mapping[str, str],
    ledger: Mapping[str, Any] | None = None,
    prior_transfers: Iterable[PriorTransfer] = (),
    observed_at: str,
    source_available_at: str,
) -> TransferEdge | TransferAbsence:
    """Run the design 4.4 gate pipeline for one candidate; abstention default.

    Gate order (documented law; the worked case 5.2 pins provenance before
    span): fact-level (instruction, validity, negation, stale cite) ->
    declarative refusal flags -> target identity -> self hop -> explicit
    second hop -> lineage hop -> lineage cycle -> generator provenance ->
    role -> cited span presence -> body receipt -> V_TWO_PARTY_SPAN ->
    market_only channel -> V_COMPETITOR_CLAIM.  The first failing gate
    names the absence; only a candidate that passes every gate mints an
    edge.  ``V_TWO_PARTY_SPAN`` is never skipped and cannot be configured
    off: this function exposes no parameter that disables any gate.
    """
    _check_timestamp(observed_at, "observed_at")
    _check_timestamp(source_available_at, "source_available_at")
    if candidate.source_company_id != source_fact.company_id:
        raise TransferError(
            "SOURCE_COMPANY_MISMATCH",
            f"candidate source {candidate.source_company_id} is not the source "
            f"fact's issuer {source_fact.company_id}")
    ctx = {"resolved_id": candidate.target_company_id, "ambiguity_note": None}

    def reject(reason: str) -> TransferAbsence:
        return _absence(candidate, source_fact, reason, observed_at=observed_at,
                        source_available_at=source_available_at, **ctx)

    # -- fact-level gates --------------------------------------------------
    if source_fact.instruction_detected:
        return reject("instruction_detected")
    if not source_fact.accepted:
        return reject("source_fact_not_validated")
    if source_fact.negated:
        return reject("source_fact_negated")
    stale = source_fact.superseded_by_fact_id is not None or (
        source_fact.novelty == "corrected_fact"
        and candidate.supersedes_transfer_id is None)
    if stale:
        return reject("source_fact_superseded_stale_cite")

    # -- declarative refusal flags ----------------------------------------
    for flag, reason in REFUSAL_FLAG_REASONS:
        if flag in candidate.refusal_flags:
            return reject(reason)

    # -- target identity (D12 ladder when the id is absent) ----------------
    resolved_id = candidate.target_company_id
    if resolved_id is None and candidate.target_mention is not None:
        resolution = resolve_mention(candidate.target_mention, ledger=ledger)
        if resolution.company_id is not None:
            resolved_id = resolution.company_id
        elif resolution.absence_reason == "ambiguous_ticker":
            ctx["ambiguity_note"] = "ambiguous_ticker: " + ", ".join(resolution.candidates)
        else:
            ctx["ambiguity_note"] = None
    ctx["resolved_id"] = resolved_id
    if resolved_id is None:
        return reject("name_resolution_ambiguous" if ctx["ambiguity_note"]
                      else "target_identity_unresolved")
    if candidate.target_company_id is not None and candidate.target_mention is not None:
        resolution = resolve_mention(candidate.target_mention, ledger=ledger)
        if resolution.company_id is not None and resolution.company_id != candidate.target_company_id:
            raise TransferError(
                "TARGET_IDENTITY_CONFLICT",
                f"target_company_id {candidate.target_company_id} disagrees with the "
                f"ladder resolution {resolution.company_id}")

    # -- structural gates (V_SELF_HOP, V_ONE_HOP, V_NO_CYCLE) ---------------
    if resolved_id == candidate.source_company_id:
        return reject("source_equals_target")
    if candidate.hop_count > 1:
        return reject("second_hop_refused")
    priors = tuple(p for p in prior_transfers
                   if p.source_fact_id in source_fact.lineage)
    if any(p.source_company_id == resolved_id for p in priors):
        return reject("hop_exceeds_one")
    same_pair = [p for p in priors
                 if {p.source_company_id, p.target_company_id} ==
                 {candidate.source_company_id, resolved_id}]
    if same_pair:
        latest = _latest_prior(same_pair)
        if candidate.supersedes_transfer_id != latest.transfer_id:
            return reject("cycle_on_source_fact")

    # -- generator provenance (candidate-only, never admission evidence) ---
    mapped = GENERATOR_GATE_REASON.get(candidate.generator_kind)
    if mapped is not None:
        return reject(mapped)

    # -- role ---------------------------------------------------------------
    if candidate.target_role not in TARGET_ROLES:
        return reject("role_incidental_or_unknown")

    # -- cited span (V_TWO_PARTY_SPAN territory; never skippable) -----------
    shock_row = candidate.generator_kind == "shock_exposure_roster"
    span_missing_reason = "no_documented_exposure_for_shock" if shock_row else "no_two_party_span"
    party_reason = "no_documented_exposure_for_shock" if shock_row else "span_names_one_party_only"
    if candidate.claimed_quote is None or candidate.span is None:
        return reject(span_missing_reason)
    receipt_state = candidate.span.get("receipt_state")
    if receipt_state != "byte_replayed":
        return reject("body_unavailable")
    if not names_both_parties(_replay_text(candidate),
                              candidate.source_company_id, resolved_id, aliases):
        return reject(party_reason)

    # -- channel and competitive claim --------------------------------------
    if candidate.mechanism_channel == "market_only":
        return reject("channel_market_only_no_graph1")
    if candidate.target_role == "competitor":
        text = _replay_text(candidate).lower()
        if not any(marker in text for marker in COMPETITIVE_MARKERS):
            return reject("competitor_without_competitive_claim")

    # -- every gate passed: emit the edge ------------------------------------
    if not candidate.display_summary:
        raise TransferError("DISPLAY_SUMMARY_REQUIRED",
                            "an emitted edge requires a caller-supplied display_summary")
    exposure = {"form": "unknown",
                "absence": dict(candidate.exposure_absence)
                if candidate.exposure_absence is not None
                else _field_absence("not_stated", "exposure")}
    timing = dict(candidate.timing) if candidate.timing is not None else {
        "lag_kind": "unknown",
        "horizon_period": _field_absence("not_stated", "timing.horizon_period")}
    alternatives = candidate.alternatives if candidate.alternatives is not None \
        else _field_absence("not_stated", "alternatives")
    transfer_id = candidate.transfer_id or _mint_id(
        "xfer_", "transfer_edge.v1", source_fact.fact_id,
        candidate.source_company_id, resolved_id)
    return TransferEdge(
        transfer_id=transfer_id,
        source_fact_id=source_fact.fact_id,
        source_company_id=candidate.source_company_id,
        target_company_id=resolved_id,
        target_role=candidate.target_role,
        edge_direction=candidate.edge_direction,
        operating_effect_on_target=candidate.operating_effect_on_target,
        mechanism_channel=candidate.mechanism_channel,
        exposure=exposure,
        timing=timing,
        alternatives=alternatives,
        generator_id=SPAN_GATE_GENERATOR_ID,
        observed_at=observed_at,
        source_available_at=source_available_at,
        display_summary=candidate.display_summary,
        two_party_span={"claimed_quote": candidate.claimed_quote, "span": dict(candidate.span)},
        shock_id=candidate.shock_id,
        supersedes_transfer_id=candidate.supersedes_transfer_id,
    )


def build_transfers(
    source_fact: SourceFact,
    candidates: Iterable[TransferCandidate],
    *,
    aliases: Mapping[str, str],
    ledger: Mapping[str, Any] | None = None,
    prior_transfers: Iterable[PriorTransfer] = (),
    observed_at: str,
    source_available_at: str,
) -> TransferResult:
    """Evaluate every candidate for one source fact (design 4.4 pipeline).

    Output ordering is deterministic: records sort by ``(schema, id)`` in
    :meth:`TransferResult.to_dicts`, so two runs on permuted candidate
    order give byte-identical canonical JSON.  ``stripped_fields`` is the
    sorted union of every candidate's ingest strip record (W3-R3).
    """
    edges, absences = [], []
    stripped: set[str] = set()
    materialized = tuple(candidates)
    for candidate in materialized:
        stripped |= set(candidate.stripped_fields)
        outcome = evaluate_candidate(
            candidate, source_fact, aliases=aliases, ledger=ledger,
            prior_transfers=prior_transfers, observed_at=observed_at,
            source_available_at=source_available_at)
        if isinstance(outcome, TransferEdge):
            edges.append(outcome)
        else:
            absences.append(outcome)
    return TransferResult(edges=tuple(edges), absences=tuple(absences),
                          stripped_fields=tuple(sorted(stripped)))


# ----------------------------------------------- design 4.5 macro shock fanout

def _check_evidence_span(span: Any, what: str) -> dict[str, Any]:
    if not isinstance(span, Mapping) or not isinstance(span.get("claimed_quote"), str) \
            or not isinstance(span.get("span"), Mapping) \
            or span["span"].get("schema") != "source_span.v1":
        raise TransferError("EVIDENCE_SPAN_MALFORMED",
                            f"{what} must be {{claimed_quote, span:source_span.v1}}")
    return {"claimed_quote": span["claimed_quote"], "span": dict(span["span"])}


def build_macro_shock_fanout(
    source_fact: SourceFact,
    shock_span: Mapping[str, Any],
    roster: Iterable[Mapping[str, Any]],
    *,
    observed_at: str,
    source_available_at: str,
    display_summary: str,
) -> MacroShockFanout:
    """Analyse one multi-issuer shock once and fan out by exposure (4.5).

    Roster rows are injected plain dicts with the closed key set
    ``{company_id, display_name, exposure_absence, transfer_ref}``:
    ``transfer_ref`` is the id of a transfer minted from this shock's
    documented exposure, or absent when the shock text does not name the
    issuer (a ``field_absence.v1`` ref is then minted, naming
    ``display_name``; design 4.5 step 3 and worked case 5.8).  Roster order
    is the caller's order.  Zero per-issuer frontier calls: this function
    never classifies, never mints edges, and consults no model.
    """
    _check_timestamp(observed_at, "observed_at")
    _check_timestamp(source_available_at, "source_available_at")
    rows_in = tuple(roster)
    if len(rows_in) < 2:
        raise TransferError("ROSTER_TOO_SMALL", f"exposure_roster needs 2-64 rows, got {len(rows_in)}")
    if len(rows_in) > 64:
        raise TransferError("ROSTER_TOO_LARGE", f"exposure_roster needs 2-64 rows, got {len(rows_in)}")
    allowed = {"company_id", "display_name", "exposure_absence", "transfer_ref"}
    seen: set[str] = set()
    stripped: set[str] = set()
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(rows_in):
        clean, row_stripped = strip_forbidden_keys(raw)
        stripped |= set(row_stripped)
        unknown = sorted(set(clean) - allowed)
        if unknown:
            raise TransferError("ROSTER_ROW_MALFORMED", f"roster row {index} keys {unknown} not allowed")
        company_id = clean.get("company_id")
        _check_company_id(company_id, f"roster row {index} company_id")
        if company_id in seen:
            raise TransferError("ROSTER_DUPLICATE_COMPANY",
                                f"roster row {index} repeats company_id {company_id}")
        seen.add(company_id)
        transfer_ref = clean.get("transfer_ref")
        if transfer_ref is None:
            name = clean.get("display_name")
            if not isinstance(name, str) or not name:
                raise TransferError("ROSTER_NAME_REQUIRED",
                                    f"roster row {index} without transfer_ref needs display_name")
            transfer_ref = _field_absence(
                "not_stated", "transfer_ref",
                f"no two-party span from this shock text to {name}")
        elif isinstance(transfer_ref, str) and not _TRANSFER_ID_RE.match(transfer_ref):
            raise TransferError("MALFORMED_TRANSFER_ID",
                                f"roster row {index} transfer_ref {transfer_ref!r} is not xfer_ + 24 hex")
        rows.append({
            "company_id": company_id,
            "exposure": {"form": "unknown",
                         "absence": dict(clean["exposure_absence"])
                         if clean.get("exposure_absence") is not None
                         else _field_absence("not_stated", "exposure")},
            "transfer_ref": dict(transfer_ref) if isinstance(transfer_ref, Mapping) else transfer_ref,
        })
    return MacroShockFanout(
        shock_id=_mint_id("shock_", "macro_shock_fanout.v1", source_fact.fact_id),
        source_fact_id=source_fact.fact_id,
        shock_span=_check_evidence_span(shock_span, "shock_span"),
        exposure_roster=tuple(rows),
        observed_at=observed_at,
        source_available_at=source_available_at,
        display_summary=display_summary,
        stripped_fields=tuple(sorted(stripped)),
    )


# --------------------------------------- design 4.6 peer-set preselection

def build_peer_set(member_ids: Iterable[str],
                   excluded_target_id: str) -> dict[str, Any]:
    """The only legal v1 peer set: documented exposure, target excluded.

    Members keep caller order (observation fixtures order them by
    documented exposure, not lexically); duplicates collapse.  The target
    is never a member of its own peer residual (design 4.6, I5).
    """
    _check_company_id(excluded_target_id, "excluded_target_id")
    members: list[str] = []
    for member in member_ids:
        _check_company_id(member, "peer_set member")
        if member == excluded_target_id:
            raise TransferError("PEER_SET_CONTAINS_TARGET",
                                f"peer set must not contain the excluded target {excluded_target_id}")
        if member not in members:
            members.append(member)
    if not members:
        raise TransferError("PEER_SET_EMPTY", "peer_set needs 1-64 members, got 0")
    if len(members) > 64:
        raise TransferError("PEER_SET_TOO_LARGE", f"peer_set needs 1-64 members, got {len(members)}")
    return {
        "selection": PEER_SET_SELECTION,
        "member_ids": members,
        "excluded_target_id": excluded_target_id,
        "target_excluded": True,
    }


def peer_set_absence(selection: str) -> dict[str, Any]:
    """A ``field_absence.v1`` on ``peer_set`` for an illegal selector (4.6)."""
    if selection not in FORBIDDEN_PEER_SELECTORS:
        raise TransferError("UNKNOWN_PEER_SELECTOR",
                            f"selector {selection!r} is not a named illegal selector")
    return _field_absence(
        "not_stated", "peer_set",
        f"selector {selection!r} is not documented exposure; peer set not stated",
        missing_fields=("peer_set",))
