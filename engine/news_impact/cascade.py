"""A5 cost cascade controller as a pure planner (never executes a stage).

Implements masterplan section 10 (processing order, cache identity, escalation
rules, audit reserve, review packet, budget exhaustion, proposed $10/$250
ceilings) and Phase 0 freeze D12/D13/D14/D16 (cik identity, source_span /
field_absence evidence, closed enums, novelty=corrected_fact requires
supersedes_fact_id) plus seat Wave-3 rulings W3-R1..R6 and A5_cost.md
sections 4.1-4.9 / 7 (Q1-Q10 defaults).

The planner loads ``contracts/news_impact/cascade.v1.json`` lazily, decides
which stages run, mints cache keys, applies escalation and the 12% SHA256
audit reserve, builds review packets, accounts budget as log-and-defer, and
emits ``cost_counters.v1``. It does not pick a provider or model, does not
import ``lib.ai_costs``, and does not call a model.

Standing kills respected by field name: DNR:KILL-LLM-ORIGINATION,
KILL-LLM-CONFIDENCE, KILL-LLM-CONTAGION-TAGS, KILL-CAUSAL-DAG-ALPHA,
KILL-THESIS-LOBE, KILL-STALENESS-ALPHA, HOLD-STRUCTURE-LEARNERS.
``relationship_generation_while_6514_held`` stays 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

CASCADE_RELPATH = Path("contracts") / "news_impact" / "cascade.v1.json"
COUNTERS_SCHEMA_RELPATH = Path("contracts") / "news_impact" / "cost_counters.v1.schema.json"
CACHE_NS = "news_impact.inference_cache.v1"
FROZEN_EVENT_SCHEMA_PREFIX = "3edc7139"
DEFAULT_SCHEMA_VERSION = "news_impact_event.v1:3edc7139"
DEFAULT_AUDIT_SEED = 20261012
DEFAULT_AUDIT_RATE = 0.12
DEFAULT_MISS_RATE_CAP = 0.05
DEFAULT_REDUCTION_RATIO_MIN = 4.0
DEFAULT_STRONGER_SLOT_CAP = 24
DEFAULT_FRONTIER_SLOT_CAP = 2
DEFAULT_DAY_USD = 10.0
DEFAULT_MONTH_USD = 250.0
RELATIONSHIP_GENERATION_HELD = 0

STAGE_ORDER: tuple[str, ...] = (
    "ingestion",
    "deterministic_screen_dedup",
    "compact_extraction",
    "validation",
    "issuer_exposure_lookup",
    "deterministic_mechanism",
    "stronger_adjudication",
    "frontier_thesis_review",
    "consumers",
)
STAGE_INDEX: dict[str, int] = {s: i for i, s in enumerate(STAGE_ORDER)}
STAGE_TIER: dict[str, str] = {
    "ingestion": "deterministic",
    "deterministic_screen_dedup": "deterministic",
    "compact_extraction": "cheap",
    "validation": "deterministic",
    "issuer_exposure_lookup": "deterministic",
    "deterministic_mechanism": "deterministic",
    "stronger_adjudication": "stronger",
    "frontier_thesis_review": "frontier",
    "consumers": "deterministic",
}
PAID_STAGES: frozenset[str] = frozenset(
    {"compact_extraction", "stronger_adjudication", "frontier_thesis_review"}
)
LANE_BY_STAGE: dict[str, str] = {
    "compact_extraction": "news-impact-extract",
    "stronger_adjudication": "news-impact-adjudicate",
    "frontier_thesis_review": "news-impact-frontier",
}
AUDIT_LANE = "news-impact-audit"
REQUIRED_LANES: frozenset[str] = frozenset(
    {
        "news-impact-extract",
        "news-impact-adjudicate",
        "news-impact-frontier",
        "news-impact-audit",
    }
)
PAID_OWNER_SEQUENCE: tuple[str, ...] = (
    "capability_broker.resolve",
    "llm_auth.make_call",
    "ai_costs.record_usage",
)
QUEUE_OWNER = "engine/qbus.py"

TERMINAL_PRIOR: frozenset[str] = frozenset(
    {
        "completed",
        "cache_hit",
        "stop_duplicate",
        "stop_low_value",
        "stop_not_material_delta",
        "stop_unresolved_issuer",
        "extract_complete",
        "validate_complete",
        "validate_reject",
        "lookup_complete",
        "lookup_absence",
        "mechanism_complete",
        "mechanism_absence",
        "adjudicate_complete",
        "frontier_complete",
        "consume_complete",
        "defer_budget",
        "defer_capacity",
        "defer_body_unavailable",
        "defer_rights",
        "reject",
        "audit_sample",
        "process",
    }
)
CACHE_KEY_FIELDS: tuple[str, ...] = (
    "document_id",
    "document_revision",
    "news_revision_id",
    "content_hash",
    "body_sha256",
    "event_facts_hash",
    "baseline_id",
    "relationship_generation",
    "model_id",
    "prompt_version",
    "schema_version",
    "rights_profile",
    "stage_id",
)
FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "confidence",
        "probability",
        "score",
        "llm_importance",
        "llm_tone",
        "price_target",
        "fair_value",
        "rating",
        "expected_move",
        "sentiment",
        "contagion",
    }
)
AUDIT_STRATA: tuple[str, ...] = (
    "rejected_low_value",
    "stop_duplicate",
    "stop_not_material_delta",
    "extracted_not_escalated",
    "validate_reject",
    "deferred_any",
)
AUDIT_WEIGHTS: dict[str, float] = {
    "rejected_low_value": 0.25,
    "stop_duplicate": 0.10,
    "stop_not_material_delta": 0.25,
    "extracted_not_escalated": 0.25,
    "validate_reject": 0.10,
    "deferred_any": 0.05,
}
DONATE_STRATA: tuple[str, ...] = (
    "extracted_not_escalated",
    "stop_not_material_delta",
)
MATERIAL_COMMITMENT = frozenset({"executed", "completed", "withdrawn"})
MATERIAL_REVISION = frozenset({"raised", "cut", "withdrawn", "cancelled", "awarded"})
MATERIAL_T1_ACTIONS = frozenset(
    {"share_repurchase", "equity_issuance", "debt_issuance", "special_dividend"}
)
TIME_SENSITIVE_CLASSES = frozenset(
    {
        "guidance_cut",
        "customer_loss",
        "product_delay",
        "regulatory_probe",
        "litigation",
        "bankruptcy_restructuring",
        "mna_rumor",
    }
)
CHANNEL_HINTS = frozenset(
    {
        "revenue_demand",
        "margin_cost",
        "capital_allocation",
        "moat_duration",
        "strategic_option",
        "financial_incentives_survival",
        "market_only",
    }
)
UNRESOLVED_DECISIONS = frozenset(
    {
        "which_template",
        "critical_numeric_conflict",
        "mechanism_choice",
        "correction_linkage",
        "exposure_identity",
        "none",
    }
)
REJECT_AUDIT_DISPOSITIONS = frozenset(
    {
        "stop_low_value",
        "stop_not_material_delta",
        "stop_duplicate",
        "validate_reject",
        "reject",
    }
)
INJECTION_MARKERS: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all previous",
    "you are now",
    "system prompt",
    "disregard the above",
)
DEFAULT_TOKEN_ENVELOPES: dict[str, tuple[int, int]] = {
    "compact_extraction": (2200, 250),
    "stronger_adjudication": (4500, 700),
    "frontier_thesis_review": (12000, 1500),
}
TIER_RANK: dict[str, int] = {
    "deterministic": 0,
    "cheap": 1,
    "stronger": 2,
    "frontier": 3,
}

CODES: frozenset[str] = frozenset(
    {
        "stage_order_violation",
        "token_envelope_exceeded",
        "lane_not_in_manifest",
        "relationship_generation_held",
        "missing_item_id",
        "invalid_utc_day",
        "unknown_stage",
        "corrected_fact_without_supersedes",
        "contract_load_failed",
        "invalid_audit_stratum",
        "unprocessed_mapped_to_neutral",
        "ceiling_not_proposed",
    }
)

__all__ = [
    "CODES",
    "CACHE_KEY_FIELDS",
    "FORBIDDEN_FIELDS",
    "PAID_OWNER_SEQUENCE",
    "STAGE_ORDER",
    "CascadeError",
    "ItemFacts",
    "BudgetSnapshot",
    "CapacitySnapshot",
    "CacheEntry",
    "CacheKeyParts",
    "RoutingDecision",
    "StagePlan",
    "ItemPlan",
    "BatchPlan",
    "ReviewPacket",
    "AuditSelection",
    "BudgetDayReport",
    "load_cascade",
    "load_cost_counters_schema",
    "canonical_json",
    "compute_cache_key",
    "event_facts_hash",
    "field_absence",
    "strip_forbidden",
    "item_facts_from_mapping",
    "material_change_predicate",
    "escalation_reason_for",
    "audit_stratum_for",
    "rank_key",
    "select_audit_reserve",
    "estimate_tokens",
    "build_review_packet",
    "assert_stage_order",
    "check_lane",
    "check_envelope",
    "refuse_neutral_mapping",
    "plan_item",
    "plan_batch",
    "emit_cost_counters",
    "evaluate_scale_gates",
    "next_utc_day",
]


class CascadeError(Exception):
    """Module-specific error carrying a closed ``CODES`` string."""

    def __init__(self, code: str, message: str = "") -> None:
        if code not in CODES:
            raise ValueError(f"unknown cascade code: {code!r}")
        super().__init__(message or code)
        self.code = code


def canonical_json(obj: Any) -> str:
    """Canonical JSON: sorted keys, compact separators, UTF-8."""
    return json_dumps(obj)


def json_dumps(obj: Any) -> str:
    import json

    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _as_dict(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _as_dict(value[k]) for k in sorted(value, key=lambda x: str(x))}
    if isinstance(value, (list, tuple)):
        return [_as_dict(v) for v in value]
    return value


def field_absence(
    subject: str,
    reason: str = "not_stated",
    detail: str = "",
    missing_fields: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Typed ``field_absence.v1`` payload (owner-shaped, never omitted)."""
    missing = list(missing_fields) if missing_fields is not None else [subject]
    return {
        "schema": "field_absence.v1",
        "authority": "context_only",
        "reason": reason,
        "subject": subject,
        "detail": detail,
        "missing_fields": missing,
    }


def strip_forbidden(obj: Any) -> tuple[Any, tuple[str, ...]]:
    """Drop forbidden keys at ingest; record their names in ``stripped_fields``."""
    stripped: list[str] = []

    def _walk(node: Any) -> Any:
        if isinstance(node, Mapping):
            out: dict[str, Any] = {}
            for k in sorted(node, key=lambda x: str(x)):
                key = str(k)
                if key in FORBIDDEN_FIELDS:
                    stripped.append(key)
                    continue
                out[key] = _walk(node[k])
            return out
        if isinstance(node, list):
            return [_walk(v) for v in node]
        if isinstance(node, tuple):
            return [_walk(v) for v in node]
        return node

    cleaned = _walk(obj)
    return cleaned, tuple(sorted(set(stripped)))


def _injection_findings(*texts: str | None) -> tuple[str, ...]:
    found: list[str] = []
    for text in texts:
        if not text:
            continue
        low = text.lower()
        for marker in INJECTION_MARKERS:
            if marker in low:
                found.append(marker)
    return tuple(sorted(set(found)))


def _default_contract_path(rel: Path) -> Path:
    return Path(__file__).resolve().parents[2] / rel


def load_cascade(path: str | Path | None = None) -> dict[str, Any]:
    """Load ``cascade.v1.json`` lazily (no module-level I/O)."""
    import json

    p = Path(path) if path is not None else _default_contract_path(CASCADE_RELPATH)
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise CascadeError("contract_load_failed", f"cannot read {p}: {exc}") from exc
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise CascadeError("contract_load_failed", f"invalid JSON at {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise CascadeError("contract_load_failed", f"cascade contract is not an object: {p}")
    return data


def load_cost_counters_schema(path: str | Path | None = None) -> dict[str, Any]:
    """Load ``cost_counters.v1.schema.json`` lazily."""
    import json

    p = Path(path) if path is not None else _default_contract_path(COUNTERS_SCHEMA_RELPATH)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CascadeError("contract_load_failed", f"cannot load counters schema {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise CascadeError("contract_load_failed", f"counters schema is not an object: {p}")
    return data


def next_utc_day(utc_day: str) -> str:
    """Return the next UTC calendar day of an injected ``YYYY-MM-DD`` value."""
    try:
        d = date.fromisoformat(utc_day)
    except ValueError as exc:
        raise CascadeError("invalid_utc_day", f"utc_day must be YYYY-MM-DD: {utc_day!r}") from exc
    return (d + timedelta(days=1)).isoformat()


def _require_utc_day(utc_day: str) -> str:
    if not utc_day:
        raise CascadeError("invalid_utc_day", "utc_day is required")
    try:
        date.fromisoformat(utc_day)
    except ValueError as exc:
        raise CascadeError("invalid_utc_day", f"utc_day must be YYYY-MM-DD: {utc_day!r}") from exc
    return utc_day


def _utc_date_of(stamp: str | None) -> str | None:
    if not stamp:
        return None
    return stamp[:10]


def event_facts_hash(facts: Mapping[str, Any] | None) -> str:
    """SHA256 of canonical JSON of extracted critical fields, or ``none``."""
    if not facts:
        return "none"
    return sha256(canonical_json(_as_dict(facts)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CacheKeyParts:
    """Inputs to ``news_impact.inference_cache.v1`` (A5 §4.3)."""

    document_id: str
    document_revision: int
    news_revision_id: str
    content_hash: str
    body_sha256: str
    event_facts_hash: str
    baseline_id: str
    relationship_generation: int
    model_id: str
    prompt_version: str
    schema_version: str
    rights_profile: str
    stage_id: str

    def __post_init__(self) -> None:
        if self.relationship_generation != RELATIONSHIP_GENERATION_HELD:
            raise CascadeError(
                "relationship_generation_held",
                "relationship_generation stays 0 while PR #6514 is HOLD-FOR-SOL",
            )
        if self.stage_id not in STAGE_INDEX:
            raise CascadeError("unknown_stage", f"unknown stage_id: {self.stage_id!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_revision": self.document_revision,
            "news_revision_id": self.news_revision_id,
            "content_hash": self.content_hash,
            "body_sha256": self.body_sha256,
            "event_facts_hash": self.event_facts_hash,
            "baseline_id": self.baseline_id,
            "relationship_generation": self.relationship_generation,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "schema_version": self.schema_version,
            "rights_profile": self.rights_profile,
            "stage_id": self.stage_id,
        }


def compute_cache_key(parts: CacheKeyParts) -> str:
    """Exact-match cache key (A5 §4.3). No TTL, no wall-clock invalidation."""
    joined = "|".join(
        [
            CACHE_NS,
            parts.document_id,
            str(parts.document_revision),
            parts.news_revision_id,
            parts.content_hash,
            parts.body_sha256,
            parts.event_facts_hash,
            parts.baseline_id,
            str(parts.relationship_generation),
            parts.model_id,
            parts.prompt_version,
            parts.schema_version,
            parts.rights_profile,
            parts.stage_id,
        ]
    )
    return sha256(joined.encode("utf-8")).hexdigest()


def assert_stage_order(prior: Mapping[int, str], next_index: int) -> None:
    """A stage may not run unless every lower index has a terminal disposition."""
    if next_index not in range(len(STAGE_ORDER)):
        raise CascadeError("unknown_stage", f"stage_index out of range: {next_index}")
    for i in range(next_index):
        disp = prior.get(i)
        if disp not in TERMINAL_PRIOR:
            raise CascadeError(
                "stage_order_violation",
                f"stage {next_index} skipped index {i} (disposition={disp!r})",
            )


def check_lane(lane_id: str, manifest: Iterable[str]) -> None:
    """Raise if a paid lane is absent from the injected capability manifest."""
    allowed = frozenset(manifest)
    if lane_id not in allowed:
        raise CascadeError("lane_not_in_manifest", f"lane {lane_id!r} not in injected manifest")


def refuse_neutral_mapping(inference_state: str, revision_direction: str | None) -> None:
    """Unprocessed ≠ neutral (A5 §4.9 invariant 9 / S6)."""
    if inference_state == "deferred" and revision_direction is not None:
        raise CascadeError(
            "unprocessed_mapped_to_neutral",
            "deferred items must not gain a revision_direction",
        )


def check_envelope(stage_id: str, input_tokens: int, output_tokens: int) -> None:
    """Raise when a planned call would exceed the hard token envelope."""
    env = DEFAULT_TOKEN_ENVELOPES.get(stage_id)
    if env is None:
        return
    cap_in, cap_out = env
    if input_tokens > cap_in or output_tokens > cap_out:
        raise CascadeError(
            "token_envelope_exceeded",
            f"{stage_id} tokens {input_tokens}/{output_tokens} exceed {cap_in}/{cap_out}",
        )


@dataclass(frozen=True)
class ItemFacts:
    """Injected facts about one item. The planner never fetches or infers them."""

    item_id: str
    utc_day: str = ""
    event_key: str | None = None
    company_id: str | None = None
    case_id: str | None = None
    title: str = ""
    source: str = ""
    domain: str = ""
    author: str = ""
    source_available_at: str | None = None
    observed_at: str | None = None
    news_event_class: str | None = None
    already_in_qbus: bool = False
    is_cluster_representative: bool = True
    representative_item_id: str | None = None
    new_numeral: bool = False
    new_counterparty: bool = False
    commitment_status_change: bool = False
    corrected_fact_marker: bool = False
    body_available: bool = True
    rights_ok: bool = True
    issuer_resolved: bool = True
    low_value: bool | None = None
    low_value_token: str | None = None
    template: str | None = None
    channel_hint: str | None = None
    commitment_status: str | None = None
    action_type: str | None = None
    revision_direction: str | None = None
    novelty: str | None = None
    supersedes_fact_id: str | None = None
    critical_quantity_form: str | None = None
    quantity_present: bool = False
    prior_fact_absent: bool = False
    prior_numeric_differs: bool = False
    cheap_pass_a: Mapping[str, Any] | None = None
    cheap_pass_b: Mapping[str, Any] | None = None
    mechanism_absence: bool = False
    mechanism_card_absent: bool = False
    active_thesis_present: bool = False
    thesis_incompatible: bool = False
    thesis_stored_commitment_status: str | None = None
    validation_reject: bool = False
    lookup_absence: bool = False
    extraction_complete: bool = True
    document_id: str = ""
    document_revision: int = 1
    news_revision_id: str = ""
    content_hash: str = ""
    body_sha256: str = ""
    event_facts: Mapping[str, Any] | None = None
    baseline_id: str = "absence"
    relationship_generation: int = 0
    model_id: str = ""
    prompt_version: str = ""
    schema_version: str = DEFAULT_SCHEMA_VERSION
    rights_profile: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    est_cost_usd: float = 0.0
    stronger_input_tokens: int = 0
    stronger_output_tokens: int = 0
    stronger_est_cost_usd: float = 0.0
    frontier_input_tokens: int = 0
    frontier_output_tokens: int = 0
    frontier_est_cost_usd: float = 0.0
    stronger_unresolved_decision: str = "none"
    event_cluster_id: str | None = None
    audit_label_material: bool = False
    new_evidence: Any = None
    old_thesis: Any = None
    driver_exposure_facts: tuple[Any, ...] = ()
    alternative_mechanisms: tuple[Any, ...] = ()
    cluster_sibling_titles: tuple[str, ...] = ()
    mechanism_card_bodies: tuple[Any, ...] = ()
    prior_stage_dispositions: Mapping[int, str] | None = None
    group_id: str | None = None
    fold: str | None = None

    def __post_init__(self) -> None:
        if not self.item_id:
            raise CascadeError("missing_item_id", "item_id must be non-empty")
        if self.relationship_generation != RELATIONSHIP_GENERATION_HELD:
            raise CascadeError(
                "relationship_generation_held",
                "relationship_generation stays 0 while PR #6514 is HOLD-FOR-SOL",
            )
        if self.novelty == "corrected_fact" and not self.supersedes_fact_id:
            raise CascadeError(
                "corrected_fact_without_supersedes",
                "novelty=corrected_fact requires supersedes_fact_id (D16)",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "utc_day": self.utc_day,
            "event_key": self.event_key,
            "company_id": self.company_id,
            "case_id": self.case_id,
            "title": self.title,
            "source": self.source,
            "news_event_class": self.news_event_class,
            "already_in_qbus": self.already_in_qbus,
            "is_cluster_representative": self.is_cluster_representative,
            "body_available": self.body_available,
            "rights_ok": self.rights_ok,
            "template": self.template,
            "channel_hint": self.channel_hint,
            "commitment_status": self.commitment_status,
            "action_type": self.action_type,
            "novelty": self.novelty,
            "supersedes_fact_id": self.supersedes_fact_id,
            "est_cost_usd": self.est_cost_usd,
        }


_ITEM_FIELDS = frozenset(ItemFacts.__dataclass_fields__)


def item_facts_from_mapping(data: Mapping[str, Any]) -> tuple[ItemFacts, tuple[str, ...]]:
    """Build ``ItemFacts`` from a mapping, stripping forbidden keys (W3-R3)."""
    cleaned, stripped = strip_forbidden(data)
    kwargs: dict[str, Any] = {}
    for k, v in cleaned.items():
        if k in _ITEM_FIELDS:
            kwargs[k] = v
    if "driver_exposure_facts" in kwargs and not isinstance(
        kwargs["driver_exposure_facts"], tuple
    ):
        kwargs["driver_exposure_facts"] = tuple(kwargs["driver_exposure_facts"])
    if "alternative_mechanisms" in kwargs and not isinstance(
        kwargs["alternative_mechanisms"], tuple
    ):
        kwargs["alternative_mechanisms"] = tuple(kwargs["alternative_mechanisms"])
    if "cluster_sibling_titles" in kwargs and not isinstance(
        kwargs["cluster_sibling_titles"], tuple
    ):
        kwargs["cluster_sibling_titles"] = tuple(kwargs["cluster_sibling_titles"])
    if "mechanism_card_bodies" in kwargs and not isinstance(
        kwargs["mechanism_card_bodies"], tuple
    ):
        kwargs["mechanism_card_bodies"] = tuple(kwargs["mechanism_card_bodies"])
    return ItemFacts(**kwargs), stripped


def material_change_predicate(item: ItemFacts) -> bool:
    """A5 §4.4 first-row predicate over already-typed fields. No score."""
    form = item.critical_quantity_form
    if form == "absent":
        return False
    if not item.quantity_present:
        return False
    status_hit = (item.commitment_status or "") in MATERIAL_COMMITMENT
    rev_hit = (item.revision_direction or "") in MATERIAL_REVISION
    t1_hit = (item.action_type or "") in MATERIAL_T1_ACTIONS
    if not (status_hit or rev_hit or t1_hit):
        return False
    return item.prior_fact_absent or item.prior_numeric_differs


def _passes_disagree(item: ItemFacts) -> bool:
    if item.cheap_pass_a is None or item.cheap_pass_b is None:
        return False
    a, _ = strip_forbidden(dict(item.cheap_pass_a))
    b, _ = strip_forbidden(dict(item.cheap_pass_b))
    return canonical_json(a) != canonical_json(b)


def escalation_reason_for(item: ItemFacts, *, allow_second_cheap: bool = False) -> str:
    """A5 §4.4 reasons over typed fields. Audit is applied later on the residual.

    When two cheap passes disagree AND the material-change predicate holds, the
    more specific ``disputed_high_consequence_fact`` wins. Strict first-match on
    the printed table would let ``material_issuer_relative_change`` shadow W3.
    """
    del allow_second_cheap
    material = material_change_predicate(item)
    if _passes_disagree(item) and material:
        return "disputed_high_consequence_fact"
    if material:
        return "material_issuer_relative_change"
    if item.mechanism_card_absent:
        return "unfamiliar_mechanism"
    if item.mechanism_absence and (not item.channel_hint or item.channel_hint not in CHANNEL_HINTS):
        return "unfamiliar_mechanism"
    if item.channel_hint is not None and item.channel_hint not in CHANNEL_HINTS:
        return "unfamiliar_mechanism"
    if item.active_thesis_present and item.thesis_incompatible:
        return "contradiction_to_active_thesis"
    if item.active_thesis_present and item.thesis_stored_commitment_status:
        if (
            item.commitment_status == "withdrawn"
            and item.thesis_stored_commitment_status == "executed"
            and item.novelty != "corrected_fact"
        ):
            return "contradiction_to_active_thesis"
        if (
            item.revision_direction == "cut"
            and item.thesis_stored_commitment_status == "raised"
        ):
            return "contradiction_to_active_thesis"
    cls = item.news_event_class or ""
    adverse = (
        cls in TIME_SENSITIVE_CLASSES
        or item.commitment_status == "withdrawn"
        or item.revision_direction in {"cut", "withdrawn", "cancelled"}
    )
    if adverse:
        obs = _utc_date_of(item.observed_at)
        avail = _utc_date_of(item.source_available_at)
        if obs is not None and avail is not None and obs == avail:
            return "time_sensitive_adverse_information"
    return "none"


def _second_cheap_offered(item: ItemFacts) -> bool:
    """Q7 default NO: second cheap pass only when material-change already holds."""
    return material_change_predicate(item)


def audit_stratum_for(disposition: str, inference_state: str) -> str | None:
    """Map a residual (non-escalated) item onto a closed audit stratum."""
    if disposition == "stop_low_value":
        return "rejected_low_value"
    if disposition == "stop_duplicate":
        return "stop_duplicate"
    if disposition == "stop_not_material_delta":
        return "stop_not_material_delta"
    if disposition == "validate_reject":
        return "validate_reject"
    if inference_state == "deferred" or disposition in {
        "defer_budget",
        "defer_capacity",
        "defer_body_unavailable",
        "defer_rights",
    }:
        return "deferred_any"
    if disposition in {"mechanism_complete", "mechanism_absence", "extract_complete", "lookup_complete", "lookup_absence", "validate_complete"}:
        return "extracted_not_escalated"
    if disposition == "reject":
        return "rejected_low_value"
    return None


def rank_key(seed: int, stratum: str, item_id: str) -> str:
    """SHA256 rank key; smallest hexdigest wins. No ``random`` module."""
    if stratum not in AUDIT_WEIGHTS and stratum != "":
        raise CascadeError("invalid_audit_stratum", f"unknown audit_stratum: {stratum!r}")
    return sha256(f"{seed}|{stratum}|{item_id}".encode("utf-8")).hexdigest()


def _hamilton_quotas(n: int, weights: Mapping[str, float], keys: Sequence[str]) -> dict[str, int]:
    if n <= 0:
        return {k: 0 for k in keys}
    raw = {k: n * float(weights[k]) for k in keys}
    floors = {k: int(raw[k] // 1) for k in keys}
    leftover = n - sum(floors.values())
    order = sorted(keys, key=lambda k: (-(raw[k] - floors[k]), k))
    out = dict(floors)
    for k in order[:leftover]:
        out[k] += 1
    return out


@dataclass(frozen=True)
class AuditSelection:
    """Seeded stratified audit draw (A5 §4.5)."""

    seed: int
    rate: float
    review_capacity: int
    n_escalate: int
    n_audit_target: int
    n_audit: int
    n_audit_starved: int
    selected_item_ids: tuple[str, ...]
    quota: dict[str, int]
    rank_order: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "rate": self.rate,
            "review_capacity": self.review_capacity,
            "n_escalate": self.n_escalate,
            "n_audit_target": self.n_audit_target,
            "n_audit": self.n_audit,
            "n_audit_starved": self.n_audit_starved,
            "selected_item_ids": list(self.selected_item_ids),
            "quota": {k: self.quota[k] for k in sorted(self.quota)},
            "rank_order": list(self.rank_order),
        }


def select_audit_reserve(
    residuals: Sequence[tuple[str, str]],
    *,
    n_escalate: int,
    stronger_slot_cap: int = DEFAULT_STRONGER_SLOT_CAP,
    seed: int = DEFAULT_AUDIT_SEED,
    rate: float = DEFAULT_AUDIT_RATE,
) -> AuditSelection:
    """Draw audit items by SHA256 rank. ``residuals`` is ``(item_id, stratum)``."""
    review_capacity = stronger_slot_cap
    starved = 0
    # DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS: ceil, computed exactly. Reproduces Q6
    # (12% of 24 = 3) and never under-audits; float ceil would make 0.14 * 50 = 8.
    target = math.ceil(Fraction(str(rate)) * review_capacity)
    if n_escalate >= review_capacity:
        target = 0
        starved = 1
    else:
        leftover_slots = review_capacity - n_escalate
        if target > leftover_slots:
            target = leftover_slots
    by_stratum: dict[str, list[str]] = {s: [] for s in AUDIT_STRATA}
    for item_id, stratum in residuals:
        if stratum not in by_stratum:
            raise CascadeError("invalid_audit_stratum", f"unknown audit_stratum: {stratum!r}")
        by_stratum[stratum].append(item_id)
    for s in AUDIT_STRATA:
        by_stratum[s].sort(key=lambda i: (rank_key(seed, s, i), i))
    quota = _hamilton_quotas(target, AUDIT_WEIGHTS, AUDIT_STRATA)
    taken: dict[str, list[str]] = {s: [] for s in AUDIT_STRATA}
    shortfall = 0
    for s in AUDIT_STRATA:
        need = quota[s]
        have = by_stratum[s]
        take_n = min(need, len(have))
        taken[s] = have[:take_n]
        shortfall += need - take_n
    for donor in DONATE_STRATA:
        if shortfall <= 0:
            break
        already = set(taken[donor])
        extra = [i for i in by_stratum[donor] if i not in already]
        grab = extra[:shortfall]
        taken[donor].extend(grab)
        shortfall -= len(grab)
    selected: list[str] = []
    rank_pairs: list[tuple[str, str]] = []
    for s in AUDIT_STRATA:
        for i in taken[s]:
            selected.append(i)
            rank_pairs.append((rank_key(seed, s, i), i))
    rank_pairs.sort()
    rank_order = tuple(i for _, i in rank_pairs)
    # Stable unique order: rank_order is the take order.
    seen: set[str] = set()
    unique: list[str] = []
    for i in rank_order:
        if i not in seen:
            seen.add(i)
            unique.append(i)
    return AuditSelection(
        seed=seed,
        rate=rate,
        review_capacity=review_capacity,
        n_escalate=n_escalate,
        n_audit_target=target,
        n_audit=len(unique),
        n_audit_starved=starved,
        selected_item_ids=tuple(sorted(unique)),
        quota=quota,
        rank_order=tuple(unique),
    )


def estimate_tokens(obj: Any) -> int:
    """Deterministic token estimate: ceil(utf8_bytes / 4). No tokenizer import."""
    raw = canonical_json(_as_dict(obj)).encode("utf-8")
    return max(1, (len(raw) + 3) // 4)


@dataclass(frozen=True)
class ReviewPacket:
    """``news_impact.review_packet.v1`` (A5 §4.6)."""

    new_evidence: Any
    old_thesis: Any
    driver_exposure_facts: tuple[Any, ...]
    alternative_mechanisms: tuple[Any, ...]
    unresolved_decision: str
    unresolved_detail: str
    cluster_sibling_titles: tuple[str, ...] = ()
    mechanism_card_bodies: tuple[Any, ...] = ()
    deferred: bool = False
    defer_reason: str | None = None
    estimated_input_tokens: int = 0
    stripped_fields: tuple[str, ...] = ()
    injection_findings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "news_impact.review_packet.v1",
            "new_evidence": _as_dict(self.new_evidence),
            "old_thesis": _as_dict(self.old_thesis),
            "driver_exposure_facts": [_as_dict(x) for x in self.driver_exposure_facts],
            "alternative_mechanisms": [_as_dict(x) for x in self.alternative_mechanisms],
            "unresolved_decision": self.unresolved_decision,
            "unresolved_detail": self.unresolved_detail,
            "cluster_sibling_titles": list(self.cluster_sibling_titles),
            "mechanism_card_bodies": [_as_dict(x) for x in self.mechanism_card_bodies],
            "deferred": self.deferred,
            "defer_reason": self.defer_reason,
            "estimated_input_tokens": self.estimated_input_tokens,
            "stripped_fields": list(self.stripped_fields),
            "injection_findings": list(self.injection_findings),
        }


def build_review_packet(
    item: ItemFacts,
    *,
    unresolved_decision: str = "none",
    unresolved_detail: str = "",
    tier: str = "stronger",
    new_evidence: Any = None,
    old_thesis: Any = None,
    driver_exposure_facts: Sequence[Any] | None = None,
    alternative_mechanisms: Sequence[Any] | None = None,
    cluster_sibling_titles: Sequence[str] | None = None,
    mechanism_card_bodies: Sequence[Any] | None = None,
) -> ReviewPacket:
    """Build the expensive review packet; drop in A5 §4.6 order if over cap."""
    if unresolved_decision not in UNRESOLVED_DECISIONS:
        unresolved_decision = "none"
    evidence = new_evidence if new_evidence is not None else item.new_evidence
    if evidence is None:
        evidence = field_absence("new_evidence", "not_stated", "no candidate packet injected")
    thesis = old_thesis if old_thesis is not None else item.old_thesis
    if thesis is None:
        thesis = field_absence("old_thesis", "not_stated", "no accepted thesis packet for company_id")
    drivers = tuple(
        driver_exposure_facts if driver_exposure_facts is not None else item.driver_exposure_facts
    )[:10]
    alts = tuple(
        alternative_mechanisms
        if alternative_mechanisms is not None
        else item.alternative_mechanisms
    )[:4]
    siblings = tuple(
        cluster_sibling_titles
        if cluster_sibling_titles is not None
        else item.cluster_sibling_titles
    )[:5]
    cards = tuple(
        mechanism_card_bodies
        if mechanism_card_bodies is not None
        else item.mechanism_card_bodies
    )[:3]
    evidence, s1 = strip_forbidden(evidence)
    thesis, s2 = strip_forbidden(thesis)
    stripped = tuple(sorted(set(s1) | set(s2)))
    findings = _injection_findings(item.title, unresolved_detail)
    detail = unresolved_detail[:240]
    cap_in = DEFAULT_TOKEN_ENVELOPES[
        "frontier_thesis_review" if tier == "frontier" else "stronger_adjudication"
    ][0]

    def _pack(
        ev: Any,
        th: Any,
        dr: tuple[Any, ...],
        alt: tuple[Any, ...],
        sib: tuple[str, ...],
        cd: tuple[Any, ...],
        deferred: bool = False,
        reason: str | None = None,
    ) -> ReviewPacket:
        pkt = ReviewPacket(
            new_evidence=ev,
            old_thesis=th,
            driver_exposure_facts=dr,
            alternative_mechanisms=alt,
            unresolved_decision=unresolved_decision,
            unresolved_detail=detail,
            cluster_sibling_titles=sib,
            mechanism_card_bodies=cd,
            deferred=deferred,
            defer_reason=reason,
            estimated_input_tokens=0,
            stripped_fields=stripped,
            injection_findings=findings,
        )
        tokens = estimate_tokens(pkt.to_dict())
        return replace(pkt, estimated_input_tokens=tokens)

    packet = _pack(evidence, thesis, drivers, alts, siblings, cards)
    # Drop order (never drop 1-2): (6) siblings >5, (5) cards >3, (4) drivers >10, (3) alts >4.
    # Lists are already capped at those maxima; shrink further toward empty if still over.
    shrink_steps = [
        ("siblings", lambda p: replace(p, cluster_sibling_titles=())),
        ("cards", lambda p: replace(p, mechanism_card_bodies=())),
        ("drivers", lambda p: replace(p, driver_exposure_facts=p.driver_exposure_facts[: max(0, len(p.driver_exposure_facts) - 1)] if False else p.driver_exposure_facts[:-1] if p.driver_exposure_facts else p.driver_exposure_facts)),
        ("alts", lambda p: replace(p, alternative_mechanisms=p.alternative_mechanisms[:-1] if p.alternative_mechanisms else p.alternative_mechanisms)),
    ]
    # Explicit shrink: siblings, then cards, then drivers one-by-one, then alts one-by-one.
    while packet.estimated_input_tokens > cap_in:
        if packet.cluster_sibling_titles:
            packet = _pack(
                evidence,
                thesis,
                packet.driver_exposure_facts,
                packet.alternative_mechanisms,
                packet.cluster_sibling_titles[:-1],
                packet.mechanism_card_bodies,
            )
            continue
        if packet.mechanism_card_bodies:
            packet = _pack(
                evidence,
                thesis,
                packet.driver_exposure_facts,
                packet.alternative_mechanisms,
                packet.cluster_sibling_titles,
                packet.mechanism_card_bodies[:-1],
            )
            continue
        if len(packet.driver_exposure_facts) > 0:
            packet = _pack(
                evidence,
                thesis,
                packet.driver_exposure_facts[:-1],
                packet.alternative_mechanisms,
                packet.cluster_sibling_titles,
                packet.mechanism_card_bodies,
            )
            continue
        if len(packet.alternative_mechanisms) > 0:
            packet = _pack(
                evidence,
                thesis,
                packet.driver_exposure_facts,
                packet.alternative_mechanisms[:-1],
                packet.cluster_sibling_titles,
                packet.mechanism_card_bodies,
            )
            continue
        return _pack(
            evidence,
            thesis,
            (),
            (),
            (),
            (),
            deferred=True,
            reason="token_envelope_exceeded",
        )
    del shrink_steps
    return packet


@dataclass(frozen=True)
class BudgetSnapshot:
    """Injected usage ledger window. No clock read; ``utc_day`` is a parameter."""

    utc_day: str
    usd_day: float = 0.0
    usd_month: float = 0.0
    day_usd_cap: float = DEFAULT_DAY_USD
    month_usd_cap: float = DEFAULT_MONTH_USD
    ceiling_authority: str = "proposed_not_authorized"
    enforce_proposed: bool = True

    def __post_init__(self) -> None:
        _require_utc_day(self.utc_day)
        if self.ceiling_authority not in {
            "proposed_not_authorized",
            "authorized",
            "exhausted",
        }:
            raise CascadeError(
                "ceiling_not_proposed",
                f"unknown ceiling_authority: {self.ceiling_authority!r}",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "utc_day": self.utc_day,
            "usd_day": self.usd_day,
            "usd_month": self.usd_month,
            "day_usd_cap": self.day_usd_cap,
            "month_usd_cap": self.month_usd_cap,
            "ceiling_authority": self.ceiling_authority,
            "enforce_proposed": self.enforce_proposed,
        }


@dataclass(frozen=True)
class CapacitySnapshot:
    """Injected capability manifest, cooling flag, gate verdict, and slot use."""

    lanes: tuple[str, ...] = ()
    all_cooling: bool = False
    gate_blocked: bool = False
    stronger_used: int = 0
    frontier_used: int = 0
    stronger_slot_cap: int = DEFAULT_STRONGER_SLOT_CAP
    frontier_slot_cap: int = DEFAULT_FRONTIER_SLOT_CAP
    cluster_frontier_used: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "lanes": list(self.lanes),
            "all_cooling": self.all_cooling,
            "gate_blocked": self.gate_blocked,
            "stronger_used": self.stronger_used,
            "frontier_used": self.frontier_used,
            "stronger_slot_cap": self.stronger_slot_cap,
            "frontier_slot_cap": self.frontier_slot_cap,
            "cluster_frontier_used": list(self.cluster_frontier_used),
        }


@dataclass(frozen=True)
class CacheEntry:
    cache_key: str
    inference_state: str
    packet: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache_key": self.cache_key,
            "inference_state": self.inference_state,
            "packet": _as_dict(self.packet),
        }


@dataclass(frozen=True)
class BudgetDayReport:
    schema: str = "news_impact.budget_day.v1"
    case_id: str | None = None
    utc_day: str = ""
    ceiling_authority: str = "proposed_not_authorized"
    day_usd_cap: float = DEFAULT_DAY_USD
    month_usd_cap: float = DEFAULT_MONTH_USD
    usd_day: float = 0.0
    usd_month: float = 0.0
    day_would_bind: bool = False
    month_would_bind: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "case_id": self.case_id,
            "utc_day": self.utc_day,
            "ceiling_authority": self.ceiling_authority,
            "day_usd_cap": self.day_usd_cap,
            "month_usd_cap": self.month_usd_cap,
            "usd_day": self.usd_day,
            "usd_month": self.usd_month,
            "day_would_bind": self.day_would_bind,
            "month_would_bind": self.month_would_bind,
        }


@dataclass(frozen=True)
class StagePlan:
    stage_id: str
    stage_index: int
    disposition: str
    model_tier_class: str
    run: bool
    cache_key: str | None = None
    lane_id: str | None = None
    admission: tuple[str, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "stage_index": self.stage_index,
            "disposition": self.disposition,
            "model_tier_class": self.model_tier_class,
            "run": self.run,
            "cache_key": self.cache_key,
            "lane_id": self.lane_id,
            "admission": list(self.admission),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RoutingDecision:
    item_id: str
    utc_day: str
    stage_terminal: str
    routing_disposition: str
    escalation_reason: str
    inference_state: str
    model_tier_class: str
    schema: str = "news_impact.routing_decision.v1"
    case_id: str | None = None
    event_key: str | None = None
    company_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    est_cost_usd: float = 0.0
    cache_hit: bool = False
    cause: str | None = None
    representative_item_id: str | None = None
    new_numeral: bool | None = None
    new_counterparty: bool | None = None
    qbus_retained: bool = True
    tape_truncated: bool = False
    synthetic_neutral_written: bool = False
    offer_again_utc_day: str | None = None
    defer_reason: str | None = None
    frontier_used: bool = False
    audit_drawn: bool = False
    audit_stratum: str | None = None
    second_cheap_pass_offered: bool = False
    n_rungs_attempted: int = 0
    visible_factual_layer: dict[str, Any] | None = None
    display_window: str | None = None
    body_available: bool = True
    template: str | None = None
    channel_hint: str | None = None
    commitment_status: str | None = None
    action_type: str | None = None
    novelty: str | None = None
    supersedes_fact_id: str | None = None
    injection_findings: tuple[str, ...] = ()
    stripped_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "schema": self.schema,
            "case_id": self.case_id,
            "item_id": self.item_id,
            "event_key": self.event_key,
            "company_id": self.company_id,
            "utc_day": self.utc_day,
            "stage_terminal": self.stage_terminal,
            "routing_disposition": self.routing_disposition,
            "escalation_reason": self.escalation_reason,
            "inference_state": self.inference_state,
            "model_tier_class": self.model_tier_class,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "est_cost_usd": self.est_cost_usd,
            "cache_hit": self.cache_hit,
            "cause": self.cause,
            "representative_item_id": self.representative_item_id,
            "new_numeral": self.new_numeral,
            "new_counterparty": self.new_counterparty,
            "qbus_retained": self.qbus_retained,
            "tape_truncated": self.tape_truncated,
            "synthetic_neutral_written": self.synthetic_neutral_written,
            "offer_again_utc_day": self.offer_again_utc_day,
            "defer_reason": self.defer_reason,
            "frontier_used": self.frontier_used,
            "audit_drawn": self.audit_drawn,
            "audit_stratum": self.audit_stratum,
            "second_cheap_pass_offered": self.second_cheap_pass_offered,
            "n_rungs_attempted": self.n_rungs_attempted,
            "visible_factual_layer": self.visible_factual_layer,
            "display_window": self.display_window,
            "body_available": self.body_available,
            "template": self.template,
            "channel_hint": self.channel_hint,
            "commitment_status": self.commitment_status,
            "action_type": self.action_type,
            "novelty": self.novelty,
            "supersedes_fact_id": self.supersedes_fact_id,
            "injection_findings": list(self.injection_findings),
            "stripped_fields": list(self.stripped_fields),
        }
        return d


@dataclass(frozen=True)
class ItemPlan:
    item_id: str
    stages: tuple[StagePlan, ...]
    decision: RoutingDecision
    review_packet: ReviewPacket | None = None
    budget_day: BudgetDayReport | None = None
    stripped_fields: tuple[str, ...] = ()
    injection_findings: tuple[str, ...] = ()
    paid_cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "stages": [s.to_dict() for s in self.stages],
            "decision": self.decision.to_dict(),
            "review_packet": None if self.review_packet is None else self.review_packet.to_dict(),
            "budget_day": None if self.budget_day is None else self.budget_day.to_dict(),
            "stripped_fields": list(self.stripped_fields),
            "injection_findings": list(self.injection_findings),
            "paid_cost_usd": self.paid_cost_usd,
        }


def _low_value_of(item: ItemFacts) -> tuple[bool, str | None]:
    if item.low_value is True:
        return True, item.low_value_token or "injected_low_value"
    if item.low_value is False:
        return False, None
    if item.low_value_token:
        return True, item.low_value_token
    return False, None


def _material_delta(item: ItemFacts) -> bool:
    if not item.body_available:
        return False
    new_disc = (
        item.new_numeral
        or item.new_counterparty
        or item.commitment_status_change
        or item.corrected_fact_marker
        or item.novelty == "corrected_fact"
    )
    return item.is_cluster_representative or new_disc


def _cache_parts_for(item: ItemFacts, stage_id: str) -> CacheKeyParts:
    facts_hash = event_facts_hash(item.event_facts)
    return CacheKeyParts(
        document_id=item.document_id,
        document_revision=item.document_revision,
        news_revision_id=item.news_revision_id,
        content_hash=item.content_hash,
        body_sha256=item.body_sha256,
        event_facts_hash=facts_hash,
        baseline_id=item.baseline_id,
        relationship_generation=RELATIONSHIP_GENERATION_HELD,
        model_id=item.model_id,
        prompt_version=item.prompt_version,
        schema_version=item.schema_version,
        rights_profile=item.rights_profile,
        stage_id=stage_id,
    )


def _lookup_cache(
    cache: Mapping[str, CacheEntry] | None, key: str
) -> CacheEntry | None:
    if not cache:
        return None
    hit = cache.get(key)
    if hit is None:
        return None
    if hit.inference_state == "completed":
        return hit
    return None


def _visible_layer(item: ItemFacts) -> dict[str, Any]:
    return {
        "title": item.title,
        "source": item.source,
        "source_available_at": item.source_available_at,
        "company_id": item.company_id,
        "news_event_class": item.news_event_class,
    }


def _highest_tier(*tiers: str) -> str:
    best = "deterministic"
    best_n = 0
    for t in tiers:
        n = TIER_RANK.get(t, 0)
        if n > best_n:
            best = t
            best_n = n
    return best


def _budget_would_bind(budget: BudgetSnapshot, cost: float) -> tuple[bool, bool]:
    day = budget.usd_day + cost > budget.day_usd_cap
    month = budget.usd_month + cost > budget.month_usd_cap
    return day, month


def _admit_paid(
    *,
    stage_id: str,
    lane_id: str,
    item: ItemFacts,
    budget: BudgetSnapshot,
    capacity: CapacitySnapshot,
    input_tokens: int,
    output_tokens: int,
    cost: float,
    slot_kind: str | None,
) -> tuple[str | None, str | None]:
    """Return (defer_disposition, reason) or (None, None) if admitted.

    Planner only: records the owner sequence, never calls it.
    """
    manifest = frozenset(capacity.lanes)
    if lane_id not in manifest:
        return "defer_capacity", "lane_not_in_manifest"
    if capacity.all_cooling:
        return "defer_capacity", "all_cooling"
    if capacity.gate_blocked:
        return "defer_capacity", "budget_gate"
    env = DEFAULT_TOKEN_ENVELOPES.get(stage_id)
    if env is not None and (input_tokens > env[0] or output_tokens > env[1]):
        return "defer_budget", "token_envelope_exceeded"
    day_bind, month_bind = _budget_would_bind(budget, cost)
    if budget.enforce_proposed and (day_bind or month_bind):
        return "defer_budget", "day_ceiling" if day_bind else "month_ceiling"
    if slot_kind == "stronger" and capacity.stronger_used >= capacity.stronger_slot_cap:
        return "defer_budget", "stronger_slot_cap"
    if slot_kind == "frontier" and capacity.frontier_used >= capacity.frontier_slot_cap:
        return "defer_budget", "frontier_slot_cap"
    return None, None


def plan_item(
    item: ItemFacts,
    *,
    budget: BudgetSnapshot,
    capacity: CapacitySnapshot,
    cache: Mapping[str, CacheEntry] | None = None,
    as_of: str | None = None,
    audit_drawn: bool = False,
    stripped_fields: tuple[str, ...] = (),
) -> ItemPlan:
    """Plan stages for one item. Never executes a stage or a model call."""
    utc_day = _require_utc_day(as_of or item.utc_day or budget.utc_day)
    if item.utc_day and item.utc_day != utc_day:
        utc_day = _require_utc_day(item.utc_day)
    findings = _injection_findings(item.title)
    stages: list[StagePlan] = []
    prior: dict[int, str] = dict(item.prior_stage_dispositions or {})
    if prior:
        # Validate existing chain before walking.
        for idx in sorted(prior):
            if idx > 0:
                try:
                    assert_stage_order(prior, idx)
                except CascadeError:
                    raise

    def _record(
        stage_id: str,
        disposition: str,
        *,
        run: bool,
        cache_key: str | None = None,
        lane_id: str | None = None,
        reason: str | None = None,
        paid: bool = False,
    ) -> StagePlan:
        idx = STAGE_INDEX[stage_id]
        if stage_id != "consumers":
            assert_stage_order(prior, idx)
        plan = StagePlan(
            stage_id=stage_id,
            stage_index=idx,
            disposition=disposition,
            model_tier_class=STAGE_TIER[stage_id],
            run=run,
            cache_key=cache_key,
            lane_id=lane_id,
            admission=PAID_OWNER_SEQUENCE if paid else (),
            reason=reason,
        )
        stages.append(plan)
        prior[idx] = disposition
        return plan

    # --- 0 ingestion ---
    _record("ingestion", "process", run=True)

    # --- 1 screen / dedup ---
    is_lv, lv_token = _low_value_of(item)
    screen_disp = "process"
    screen_reason: str | None = None
    cause: str | None = None
    if is_lv:
        screen_disp = "stop_low_value"
        screen_reason = lv_token
        cause = "low_value"
    elif item.already_in_qbus:
        screen_disp = "stop_duplicate"
        cause = "item_id"
        screen_reason = "item_id keep-FIRST"
    elif (not item.is_cluster_representative) and not (
        item.new_numeral
        or item.new_counterparty
        or item.commitment_status_change
        or item.corrected_fact_marker
        or item.novelty == "corrected_fact"
    ):
        screen_disp = "stop_duplicate"
        cause = "cluster_representative"
        screen_reason = "cluster_representative"
    elif not item.body_available:
        screen_disp = "defer_body_unavailable"
        screen_reason = "body_unavailable"
    elif not item.rights_ok:
        screen_disp = "defer_rights"
        screen_reason = "rights_registry_miss"
    elif not _material_delta(item):
        screen_disp = "stop_not_material_delta"
        screen_reason = "not_material_delta"
    _record(
        "deterministic_screen_dedup",
        screen_disp,
        run=True,
        reason=screen_reason,
    )

    stopped_early = screen_disp != "process"
    cache_hit = False
    paid_cost = 0.0
    in_tok = 0
    out_tok = 0
    used_tier = "deterministic"
    esc = "none"
    inference = "not_required"
    terminal_stage = "deterministic_screen_dedup"
    terminal_disp = screen_disp
    defer_reason: str | None = None
    review: ReviewPacket | None = None
    frontier_used = False
    day_bind = False
    month_bind = False
    offer_again: str | None = None
    display_window: str | None = None
    visible: dict[str, Any] | None = None

    def _stop_here(disp: str, stage_id: str, *, inf: str, tier: str, reason: str | None = None) -> None:
        nonlocal terminal_disp, terminal_stage, inference, used_tier, defer_reason
        terminal_disp = disp
        terminal_stage = stage_id
        inference = inf
        used_tier = _highest_tier(used_tier, tier)
        if reason is not None:
            defer_reason = reason

    if stopped_early:
        if screen_disp in {"defer_body_unavailable", "defer_rights"}:
            _stop_here(
                screen_disp,
                "deterministic_screen_dedup",
                inf="deferred",
                tier="deterministic",
                reason=screen_reason,
            )
            visible = _visible_layer(item)
            display_window = (
                "inference deferred this UTC day because the body or rights were unavailable."
            )
            offer_again = next_utc_day(utc_day)
        else:
            _stop_here(
                screen_disp,
                "deterministic_screen_dedup",
                inf="not_required",
                tier="deterministic",
            )
    else:
        # --- 2 compact extraction (cheap) ---
        parts = _cache_parts_for(item, "compact_extraction")
        key = compute_cache_key(parts)
        hit = _lookup_cache(cache, key)
        cheap_in = item.input_tokens
        cheap_out = item.output_tokens
        cheap_cost = item.est_cost_usd
        if hit is not None:
            cache_hit = True
            _record(
                "compact_extraction",
                "cache_hit",
                run=False,
                cache_key=key,
                lane_id=LANE_BY_STAGE["compact_extraction"],
                paid=False,
                reason="cache_hit",
            )
            used_tier = "cheap"
            in_tok = 0
            out_tok = 0
            paid_cost = 0.0
            extract_ok = True
        else:
            dfd, why = _admit_paid(
                stage_id="compact_extraction",
                lane_id=LANE_BY_STAGE["compact_extraction"],
                item=item,
                budget=budget,
                capacity=capacity,
                input_tokens=cheap_in,
                output_tokens=cheap_out,
                cost=cheap_cost,
                slot_kind=None,
            )
            day_bind, month_bind = _budget_would_bind(budget, cheap_cost)
            if dfd is not None:
                _record(
                    "compact_extraction",
                    dfd,
                    run=False,
                    cache_key=key,
                    lane_id=LANE_BY_STAGE["compact_extraction"],
                    paid=True,
                    reason=why,
                )
                _stop_here(
                    dfd,
                    "deterministic_screen_dedup",
                    inf="deferred",
                    tier="cheap",
                    reason=why,
                )
                visible = _visible_layer(item)
                display_window = (
                    "inference deferred this UTC day because the incremental "
                    "inference ceiling was reached."
                    if dfd == "defer_budget"
                    else "inference deferred this UTC day because capacity was not admitted."
                )
                offer_again = next_utc_day(utc_day)
                extract_ok = False
            else:
                extract_disp = "extract_complete" if item.extraction_complete else "reject"
                _record(
                    "compact_extraction",
                    extract_disp,
                    run=True,
                    cache_key=key,
                    lane_id=LANE_BY_STAGE["compact_extraction"],
                    paid=True,
                )
                used_tier = "cheap"
                in_tok = cheap_in
                out_tok = cheap_out
                paid_cost = cheap_cost
                extract_ok = extract_disp == "extract_complete"
                if not extract_ok:
                    _stop_here("reject", "compact_extraction", inf="rejected", tier="cheap")

        if inference != "deferred" and terminal_disp not in {"reject"} and extract_ok:
            # --- 3 validation ---
            if item.validation_reject:
                _record("validation", "validate_reject", run=True, reason="validate_reject")
                _stop_here("validate_reject", "validation", inf="rejected", tier=used_tier)
            else:
                _record("validation", "validate_complete", run=True)
                # --- 4 issuer lookup ---
                if not item.issuer_resolved:
                    _record(
                        "issuer_exposure_lookup",
                        "stop_unresolved_issuer",
                        run=True,
                        reason="not_stated",
                    )
                    _stop_here(
                        "stop_unresolved_issuer",
                        "issuer_exposure_lookup",
                        inf="not_required",
                        tier=used_tier,
                    )
                elif item.lookup_absence:
                    _record("issuer_exposure_lookup", "lookup_absence", run=True)
                    # still continue to mechanism (typed absence)
                    lookup_ok = True
                else:
                    _record("issuer_exposure_lookup", "lookup_complete", run=True)
                    lookup_ok = True
                if inference != "deferred" and terminal_disp not in {
                    "stop_unresolved_issuer",
                    "validate_reject",
                    "reject",
                }:
                    # --- 5 deterministic mechanism ---
                    mech_disp = (
                        "mechanism_absence" if item.mechanism_absence else "mechanism_complete"
                    )
                    _record("deterministic_mechanism", mech_disp, run=True)
                    _stop_here(mech_disp, "deterministic_mechanism", inf="completed", tier=used_tier)

                    esc = escalation_reason_for(item)
                    if audit_drawn and esc == "none":
                        esc = "audit_reserve_draw"

                    need_stronger = esc != "none"
                    if need_stronger:
                        lane = (
                            AUDIT_LANE
                            if esc == "audit_reserve_draw"
                            else LANE_BY_STAGE["stronger_adjudication"]
                        )
                        s_in = item.stronger_input_tokens or item.input_tokens
                        s_out = item.stronger_output_tokens or item.output_tokens
                        s_cost = item.stronger_est_cost_usd or 0.0
                        pkt = build_review_packet(
                            item,
                            unresolved_decision=(
                                "critical_numeric_conflict"
                                if esc == "disputed_high_consequence_fact"
                                else "mechanism_choice"
                                if esc == "unfamiliar_mechanism"
                                else "correction_linkage"
                                if esc == "contradiction_to_active_thesis"
                                else "none"
                            )
                            if item.stronger_unresolved_decision == "none"
                            and esc != "audit_reserve_draw"
                            else item.stronger_unresolved_decision,
                            tier="stronger",
                        )
                        if pkt.deferred:
                            _record(
                                "stronger_adjudication",
                                "defer_budget",
                                run=False,
                                lane_id=lane,
                                paid=True,
                                reason="token_envelope_exceeded",
                            )
                            _stop_here(
                                "defer_budget",
                                "deterministic_mechanism",
                                inf="deferred",
                                tier="stronger",
                                reason="token_envelope_exceeded",
                            )
                            visible = _visible_layer(item)
                            offer_again = next_utc_day(utc_day)
                        else:
                            dfd, why = _admit_paid(
                                stage_id="stronger_adjudication",
                                lane_id=lane,
                                item=item,
                                budget=replace(
                                    budget,
                                    usd_day=budget.usd_day + paid_cost,
                                    usd_month=budget.usd_month + paid_cost,
                                ),
                                capacity=capacity,
                                input_tokens=s_in,
                                output_tokens=s_out,
                                cost=s_cost,
                                slot_kind="stronger",
                            )
                            db, mb = _budget_would_bind(
                                replace(
                                    budget,
                                    usd_day=budget.usd_day + paid_cost,
                                    usd_month=budget.usd_month + paid_cost,
                                ),
                                s_cost,
                            )
                            day_bind = day_bind or db
                            month_bind = month_bind or mb
                            if dfd is not None:
                                _record(
                                    "stronger_adjudication",
                                    dfd,
                                    run=False,
                                    lane_id=lane,
                                    paid=True,
                                    reason=why,
                                )
                                _stop_here(
                                    dfd,
                                    "deterministic_mechanism",
                                    inf="deferred",
                                    tier="stronger",
                                    reason=why,
                                )
                                visible = _visible_layer(item)
                                display_window = (
                                    "inference deferred this UTC day because the incremental "
                                    "inference ceiling was reached."
                                )
                                offer_again = next_utc_day(utc_day)
                            else:
                                review = pkt
                                _record(
                                    "stronger_adjudication",
                                    "adjudicate_complete",
                                    run=True,
                                    lane_id=lane,
                                    paid=True,
                                )
                                _stop_here(
                                    "adjudicate_complete",
                                    "stronger_adjudication",
                                    inf="completed",
                                    tier="stronger",
                                )
                                in_tok = s_in
                                out_tok = s_out
                                paid_cost += s_cost
                                unresolved = item.stronger_unresolved_decision
                                still_hard = unresolved not in {"", "none", None} and esc in {
                                    "unfamiliar_mechanism",
                                    "contradiction_to_active_thesis",
                                }
                                cluster_id = item.event_cluster_id
                                cluster_used = cluster_id is not None and cluster_id in set(
                                    capacity.cluster_frontier_used
                                )
                                if still_hard and not cluster_used:
                                    f_in = item.frontier_input_tokens
                                    f_out = item.frontier_output_tokens
                                    f_cost = item.frontier_est_cost_usd
                                    dfd, why = _admit_paid(
                                        stage_id="frontier_thesis_review",
                                        lane_id=LANE_BY_STAGE["frontier_thesis_review"],
                                        item=item,
                                        budget=replace(
                                            budget,
                                            usd_day=budget.usd_day + paid_cost,
                                            usd_month=budget.usd_month + paid_cost,
                                        ),
                                        capacity=capacity,
                                        input_tokens=f_in,
                                        output_tokens=f_out,
                                        cost=f_cost,
                                        slot_kind="frontier",
                                    )
                                    if dfd is not None:
                                        _record(
                                            "frontier_thesis_review",
                                            dfd,
                                            run=False,
                                            lane_id=LANE_BY_STAGE["frontier_thesis_review"],
                                            paid=True,
                                            reason=why,
                                        )
                                        # remain at stronger output
                                    else:
                                        _record(
                                            "frontier_thesis_review",
                                            "frontier_complete",
                                            run=True,
                                            lane_id=LANE_BY_STAGE["frontier_thesis_review"],
                                            paid=True,
                                        )
                                        _stop_here(
                                            "frontier_complete",
                                            "frontier_thesis_review",
                                            inf="completed",
                                            tier="frontier",
                                        )
                                        in_tok = f_in
                                        out_tok = f_out
                                        paid_cost += f_cost
                                        frontier_used = True

    # --- 8 consumers: always planned for a terminal packet ---
    if inference in {"completed", "deferred", "rejected", "not_required"}:
        try:
            _record("consumers", "consume_complete", run=True)
        except CascadeError as exc:
            if exc.code == "stage_order_violation":
                # Halt this item; consumers skipped when the chain was halted mid-order.
                pass
            else:
                raise

    if inference == "deferred":
        visible = visible or _visible_layer(item)
        offer_again = offer_again or next_utc_day(utc_day)

    day_bind, month_bind = (
        day_bind or _budget_would_bind(budget, item.est_cost_usd)[0],
        month_bind or _budget_would_bind(budget, item.est_cost_usd)[1],
    )

    stratum = None
    if esc in {"none", "audit_reserve_draw"}:
        stratum = audit_stratum_for(terminal_disp, inference)

    decision = RoutingDecision(
        item_id=item.item_id,
        utc_day=utc_day,
        stage_terminal=terminal_stage,
        routing_disposition=terminal_disp,
        escalation_reason=esc if not stopped_early else "none",
        inference_state=inference,
        model_tier_class=used_tier,
        case_id=item.case_id,
        event_key=item.event_key,
        company_id=item.company_id,
        input_tokens=in_tok,
        output_tokens=out_tok,
        est_cost_usd=0.0 if inference == "deferred" or cache_hit else paid_cost,
        cache_hit=cache_hit,
        cause=cause,
        representative_item_id=item.representative_item_id if cause == "cluster_representative" else None,
        new_numeral=item.new_numeral if cause == "cluster_representative" else None,
        new_counterparty=item.new_counterparty if cause == "cluster_representative" else None,
        qbus_retained=True,
        tape_truncated=False,
        synthetic_neutral_written=False,
        offer_again_utc_day=offer_again,
        defer_reason=defer_reason,
        frontier_used=frontier_used,
        audit_drawn=audit_drawn,
        audit_stratum=stratum,
        second_cheap_pass_offered=_second_cheap_offered(item),
        n_rungs_attempted=0,
        visible_factual_layer=visible,
        display_window=display_window,
        body_available=item.body_available,
        template=item.template,
        channel_hint=item.channel_hint,
        commitment_status=item.commitment_status,
        action_type=item.action_type,
        novelty=item.novelty,
        supersedes_fact_id=item.supersedes_fact_id,
        injection_findings=findings,
        stripped_fields=stripped_fields,
    )
    budget_day = BudgetDayReport(
        case_id=item.case_id,
        utc_day=utc_day,
        ceiling_authority=budget.ceiling_authority,
        day_usd_cap=budget.day_usd_cap,
        month_usd_cap=budget.month_usd_cap,
        usd_day=budget.usd_day,
        usd_month=budget.usd_month,
        day_would_bind=day_bind,
        month_would_bind=month_bind,
    )
    return ItemPlan(
        item_id=item.item_id,
        stages=tuple(stages),
        decision=decision,
        review_packet=review,
        budget_day=budget_day,
        stripped_fields=stripped_fields,
        injection_findings=findings,
        paid_cost_usd=0.0 if inference == "deferred" or cache_hit else paid_cost,
    )


def _item_sort_key(item: ItemFacts) -> tuple[str, str]:
    return (item.source_available_at or "", item.item_id)


@dataclass(frozen=True)
class BatchPlan:
    plans: tuple[ItemPlan, ...]
    audit: AuditSelection
    counters: dict[str, Any]
    seed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "plans": [p.to_dict() for p in self.plans],
            "audit": self.audit.to_dict(),
            "counters": self.counters,
            "seed": self.seed,
        }


def plan_batch(
    items: Sequence[ItemFacts],
    *,
    budget: BudgetSnapshot,
    capacity: CapacitySnapshot,
    cache: Mapping[str, CacheEntry] | None = None,
    as_of: str | None = None,
    seed: int = DEFAULT_AUDIT_SEED,
    audit_rate: float = DEFAULT_AUDIT_RATE,
    run_id: str = "cascade-run",
    tape_sha: str = "unknown0",
    n_labeled: int = 0,
    material_event_recall: float | None = None,
    critical_numeric_correctness: float | None = None,
    unsupported_ticker_to_supplier: int = 0,
    n_audit_rejects_labeled_material: int = 0,
) -> BatchPlan:
    """Plan a batch. Input order does not affect canonical JSON (sorted by PIT key)."""
    ordered = tuple(sorted(items, key=_item_sort_key))
    # Pass 1: through mechanism / early stop, no audit flag.
    first_plans: list[ItemPlan] = []
    running = budget
    stronger_used = capacity.stronger_used
    frontier_used_n = capacity.frontier_used
    cluster_used = set(capacity.cluster_frontier_used)
    cap = capacity
    for it in ordered:
        plan = plan_item(
            it,
            budget=running,
            capacity=cap,
            cache=cache,
            as_of=as_of,
            audit_drawn=False,
        )
        first_plans.append(plan)
        if plan.paid_cost_usd:
            running = replace(
                running,
                usd_day=running.usd_day + plan.paid_cost_usd,
                usd_month=running.usd_month + plan.paid_cost_usd,
            )
        if plan.decision.routing_disposition == "adjudicate_complete":
            stronger_used += 1
            cap = replace(cap, stronger_used=stronger_used)
        if plan.decision.frontier_used:
            frontier_used_n += 1
            if it.event_cluster_id:
                cluster_used.add(it.event_cluster_id)
            cap = replace(
                cap,
                frontier_used=frontier_used_n,
                cluster_frontier_used=tuple(sorted(cluster_used)),
            )

    n_escalate = sum(
        1
        for p in first_plans
        if p.decision.escalation_reason not in {"none", "audit_reserve_draw"}
        and p.decision.inference_state == "completed"
    )
    # Also count planned true escalations that completed mechanism even if stronger deferred.
    n_escalate = sum(
        1
        for p, it in zip(first_plans, ordered)
        if escalation_reason_for(it) not in {"none", "audit_reserve_draw"}
        and p.decision.stage_terminal
        in {"deterministic_mechanism", "stronger_adjudication", "frontier_thesis_review"}
        and p.decision.routing_disposition
        in {
            "mechanism_complete",
            "mechanism_absence",
            "adjudicate_complete",
            "frontier_complete",
            "defer_budget",
            "defer_capacity",
        }
        and p.decision.escalation_reason not in {"none", "audit_reserve_draw"}
    )
    n_escalate_true = 0
    residuals: list[tuple[str, str]] = []
    for p, it in zip(first_plans, ordered):
        reason = escalation_reason_for(it)
        if reason != "none":
            if p.decision.stage_terminal in {
                "deterministic_mechanism",
                "stronger_adjudication",
                "frontier_thesis_review",
            } or p.decision.routing_disposition in {
                "mechanism_complete",
                "mechanism_absence",
                "adjudicate_complete",
            }:
                n_escalate_true += 1
            continue
        if p.decision.inference_state in {"completed", "not_required", "deferred", "rejected"}:
            stratum = audit_stratum_for(
                p.decision.routing_disposition, p.decision.inference_state
            )
            if stratum is not None:
                residuals.append((it.item_id, stratum))

    audit = select_audit_reserve(
        residuals,
        n_escalate=n_escalate_true,
        stronger_slot_cap=capacity.stronger_slot_cap,
        seed=seed,
        rate=audit_rate,
    )
    drawn = set(audit.rank_order)

    # Pass 2: re-plan with audit flags and a fresh running budget so audit items
    # can consume leftover stronger slots. True escalations still go first.
    second: list[ItemPlan] = []
    running = budget
    stronger_used = capacity.stronger_used
    frontier_used_n = capacity.frontier_used
    cluster_used = set(capacity.cluster_frontier_used)
    # Escalations first (stable by PIT key among each class), then audit, then rest.
    def _prio(pair: tuple[ItemFacts, ItemPlan]) -> tuple[int, str, str]:
        it, p = pair
        reason = escalation_reason_for(it)
        if reason != "none":
            return (0, it.source_available_at or "", it.item_id)
        if it.item_id in drawn:
            return (1, it.source_available_at or "", it.item_id)
        return (2, it.source_available_at or "", it.item_id)

    pairs = sorted(zip(ordered, first_plans), key=_prio)
    # Emit in original PIT order; compute with escalation-first admission.
    plans_by_id: dict[str, ItemPlan] = {}
    for it, _first in pairs:
        cap_now = replace(
            capacity,
            stronger_used=stronger_used,
            frontier_used=frontier_used_n,
            cluster_frontier_used=tuple(sorted(cluster_used)),
        )
        plan = plan_item(
            it,
            budget=running,
            capacity=cap_now,
            cache=cache,
            as_of=as_of,
            audit_drawn=it.item_id in drawn and escalation_reason_for(it) == "none",
        )
        plans_by_id[it.item_id] = plan
        if plan.paid_cost_usd:
            running = replace(
                running,
                usd_day=running.usd_day + plan.paid_cost_usd,
                usd_month=running.usd_month + plan.paid_cost_usd,
            )
        if plan.decision.routing_disposition == "adjudicate_complete":
            stronger_used += 1
        if plan.decision.frontier_used:
            frontier_used_n += 1
            if it.event_cluster_id:
                cluster_used.add(it.event_cluster_id)

    final_plans = tuple(plans_by_id[it.item_id] for it in ordered)
    counters = emit_cost_counters(
        final_plans,
        audit=audit,
        budget=running,
        run_id=run_id,
        sampling_seed=seed,
        tape_sha=tape_sha,
        n_labeled=n_labeled,
        material_event_recall=material_event_recall,
        critical_numeric_correctness=critical_numeric_correctness,
        unsupported_ticker_to_supplier=unsupported_ticker_to_supplier,
        n_audit_rejects_labeled_material=n_audit_rejects_labeled_material,
        items=ordered,
    )
    return BatchPlan(plans=final_plans, audit=audit, counters=counters, seed=seed)


def _empty_stage_counters() -> list[dict[str, Any]]:
    rows = []
    for sid in STAGE_ORDER:
        rows.append(
            {
                "stage_id": sid,
                "model_tier_class": STAGE_TIER[sid],
                "n_offered": 0,
                "n_complete": 0,
                "n_cache_hit": 0,
                "n_defer_budget": 0,
                "n_defer_capacity": 0,
                "n_defer_body_unavailable": 0,
                "n_reject": 0,
                "n_envelope_exceeded": 0,
                "sum_input_tokens": 0,
                "sum_output_tokens": 0,
                "sum_est_cost_usd": 0.0,
            }
        )
    return rows


def emit_cost_counters(
    plans: Sequence[ItemPlan],
    *,
    audit: AuditSelection | None,
    budget: BudgetSnapshot,
    run_id: str,
    sampling_seed: int,
    tape_sha: str,
    n_labeled: int,
    material_event_recall: float | None = None,
    critical_numeric_correctness: float | None = None,
    unsupported_ticker_to_supplier: int = 0,
    n_audit_rejects_labeled_material: int = 0,
    items: Sequence[ItemFacts] | None = None,
) -> dict[str, Any]:
    """Emit ``news_impact.cost_counters.v1`` (A5 §4.8)."""
    stages = _empty_stage_counters()
    by_id = {s["stage_id"]: s for s in stages}
    n_raw = len(plans)
    n_low_value = 0
    n_identity_dup = 0
    n_cluster_dup = 0
    n_body_unavail = 0
    n_material_delta = 0
    n_extract = 0
    n_extract_complete = 0
    n_escalate = 0
    n_audit = 0
    n_frontier = 0
    n_terminal = 0
    n_deferred_budget = 0
    n_stage_order_violation = 0
    n_audit_rejects = 0
    sum_cost = 0.0
    dispositions: list[str] = []

    item_by_id: dict[str, ItemFacts] = {}
    if items is not None:
        for it in items:
            item_by_id[it.item_id] = it

    cases: list[dict[str, Any]] = []
    for plan in plans:
        d = plan.decision
        dispositions.append(d.routing_disposition)
        n_terminal += 1
        if d.routing_disposition == "stop_low_value":
            n_low_value += 1
        if d.routing_disposition == "stop_duplicate" and d.cause == "item_id":
            n_identity_dup += 1
        if d.routing_disposition == "stop_duplicate" and d.cause == "cluster_representative":
            n_cluster_dup += 1
        if d.routing_disposition == "defer_body_unavailable":
            n_body_unavail += 1
        if d.routing_disposition == "defer_budget":
            n_deferred_budget += 1
        if d.escalation_reason not in {"none", "audit_reserve_draw"}:
            n_escalate += 1
        if d.escalation_reason == "audit_reserve_draw" or d.audit_drawn:
            n_audit += 1
        if d.routing_disposition == "frontier_complete":
            n_frontier += 1
        if d.audit_drawn and d.routing_disposition in REJECT_AUDIT_DISPOSITIONS:
            n_audit_rejects += 1
        sum_cost += float(d.est_cost_usd)

        offered_paid = False
        for sp in plan.stages:
            row = by_id[sp.stage_id]
            row["n_offered"] += 1
            if sp.disposition in {
                "process",
                "extract_complete",
                "validate_complete",
                "lookup_complete",
                "lookup_absence",
                "mechanism_complete",
                "mechanism_absence",
                "adjudicate_complete",
                "frontier_complete",
                "consume_complete",
                "cache_hit",
            }:
                row["n_complete"] += 1
            if sp.disposition == "cache_hit":
                row["n_cache_hit"] += 1
            if sp.disposition == "defer_budget":
                row["n_defer_budget"] += 1
            if sp.disposition == "defer_capacity":
                row["n_defer_capacity"] += 1
            if sp.disposition == "defer_body_unavailable":
                row["n_defer_body_unavailable"] += 1
            if sp.disposition in {"reject", "validate_reject"}:
                row["n_reject"] += 1
            if sp.reason == "token_envelope_exceeded":
                row["n_envelope_exceeded"] += 1
            if sp.stage_id == "compact_extraction" and sp.disposition in {
                "extract_complete",
                "cache_hit",
                "defer_budget",
                "defer_capacity",
            }:
                offered_paid = True
        if offered_paid:
            n_extract += 1
        if any(sp.disposition == "extract_complete" for sp in plan.stages):
            n_extract_complete += 1
        if d.routing_disposition != "stop_low_value" and d.routing_disposition != "stop_duplicate":
            if d.stage_terminal != "deterministic_screen_dedup" or d.routing_disposition in {
                "defer_budget",
                "defer_capacity",
                "defer_body_unavailable",
                "defer_rights",
                "stop_not_material_delta",
            }:
                pass
        # material delta: screen passed to extraction or would have
        if any(sp.stage_id == "compact_extraction" for sp in plan.stages):
            n_material_delta += 1

        by_id["compact_extraction"]["sum_input_tokens"] += int(
            d.input_tokens if d.model_tier_class == "cheap" else 0
        )
        by_id["compact_extraction"]["sum_output_tokens"] += int(
            d.output_tokens if d.model_tier_class == "cheap" else 0
        )
        if d.model_tier_class == "cheap":
            by_id["compact_extraction"]["sum_est_cost_usd"] += float(d.est_cost_usd)
        if d.model_tier_class == "stronger":
            by_id["stronger_adjudication"]["sum_input_tokens"] += int(d.input_tokens)
            by_id["stronger_adjudication"]["sum_output_tokens"] += int(d.output_tokens)
            by_id["stronger_adjudication"]["sum_est_cost_usd"] += float(d.est_cost_usd)
        if d.model_tier_class == "frontier":
            by_id["frontier_thesis_review"]["sum_input_tokens"] += int(d.input_tokens)
            by_id["frontier_thesis_review"]["sum_output_tokens"] += int(d.output_tokens)
            by_id["frontier_thesis_review"]["sum_est_cost_usd"] += float(d.est_cost_usd)

        it = item_by_id.get(d.item_id)
        cases.append(
            {
                "case_id": d.case_id or d.item_id,
                "group_id": None if it is None else it.group_id,
                "fold": None if it is None else it.fold,
                "template_id": d.template,
                "item_id": d.item_id,
                "company_id": d.company_id,
                "stage_terminal": d.stage_terminal,
                "routing_disposition": d.routing_disposition,
                "escalation_reason": d.escalation_reason,
                "inference_state": d.inference_state,
                "cache_hit": d.cache_hit,
                "n_rungs_attempted": d.n_rungs_attempted,
                "input_tokens": d.input_tokens,
                "output_tokens": d.output_tokens,
                "est_cost_usd": d.est_cost_usd,
                "model_tier_class": d.model_tier_class,
                "prompt_version": None if it is None else (it.prompt_version or None),
                "schema_version": None if it is None else (it.schema_version or None),
                "rights_profile": None if it is None else (it.rights_profile or None),
                "supersedes_fact_id": d.supersedes_fact_id,
                "body_available": d.body_available,
                "audit_stratum": d.audit_stratum,
                "audit_drawn": d.audit_drawn,
            }
        )

    n_eligible = n_raw - n_low_value
    n_first = n_eligible - n_identity_dup
    n_cluster_rep = n_first - n_cluster_dup
    reduction_ratio = n_raw / max(n_extract, 1)
    n_audit_starved = 0 if audit is None else audit.n_audit_starved
    if audit is not None:
        n_audit = audit.n_audit
    miss_rate: float | None
    if n_audit_rejects == 0:
        miss_rate = None
    else:
        miss_rate = n_audit_rejects_labeled_material / n_audit_rejects

    # Accounting identity: every item has exactly one terminal disposition.
    accounting_ok = n_raw == n_terminal == len(dispositions)

    day_would_bind = budget.usd_day > budget.day_usd_cap or any(
        (p.budget_day.day_would_bind if p.budget_day else False) for p in plans
    )
    month_would_bind = budget.usd_month > budget.month_usd_cap or any(
        (p.budget_day.month_would_bind if p.budget_day else False) for p in plans
    )

    run = {
        "n_raw": n_raw,
        "n_low_value": n_low_value,
        "n_identity_dup": n_identity_dup,
        "n_cluster_dup": n_cluster_dup,
        "n_eligible": n_eligible,
        "n_first": n_first,
        "n_cluster_rep": n_cluster_rep,
        "n_body_unavail": n_body_unavail,
        "n_material_delta": n_material_delta,
        "n_extract": n_extract,
        "n_extract_complete": n_extract_complete,
        "n_escalate": n_escalate,
        "n_audit": n_audit,
        "n_audit_starved": n_audit_starved,
        "n_frontier": n_frontier,
        "n_terminal": n_terminal,
        "n_deferred_budget": n_deferred_budget,
        "n_stage_order_violation": n_stage_order_violation,
        "reduction_ratio": reduction_ratio,
        "sum_est_cost_usd": sum_cost,
        "usd_day_max": budget.usd_day,
        "day_would_bind": bool(day_would_bind),
        "month_would_bind": bool(month_would_bind),
        "reject_audit_miss_rate": miss_rate,
        "n_audit_rejects": n_audit_rejects,
        "n_audit_rejects_labeled_material": n_audit_rejects_labeled_material,
        "accounting_identity_ok": accounting_ok,
    }
    gates = evaluate_scale_gates(
        run,
        material_event_recall=material_event_recall,
        critical_numeric_correctness=critical_numeric_correctness,
        unsupported_ticker_to_supplier=unsupported_ticker_to_supplier,
    )
    return {
        "schema": "news_impact.cost_counters.v1",
        "authority": "context_only",
        "run_id": run_id,
        "sampling_seed": sampling_seed,
        "tape_sha": tape_sha,
        "n_labeled": n_labeled,
        "ceiling_authority": budget.ceiling_authority,
        "stages": stages,
        "run": run,
        "scale_gates": gates,
        "cases": cases,
    }


def evaluate_scale_gates(
    run: Mapping[str, Any],
    *,
    material_event_recall: float | None,
    critical_numeric_correctness: float | None,
    unsupported_ticker_to_supplier: int,
    miss_rate_cap: float = DEFAULT_MISS_RATE_CAP,
    reduction_ratio_min: float = DEFAULT_REDUCTION_RATIO_MIN,
) -> dict[str, Any]:
    """A5 §4.8 scale gates. Missing measurements do not permit scaling."""
    accounting = bool(run.get("accounting_identity_ok"))
    order_ok = int(run.get("n_stage_order_violation") or 0) == 0
    miss = run.get("reject_audit_miss_rate")
    ratio = run.get("reduction_ratio")
    miss_ok = miss is not None and float(miss) <= miss_rate_cap
    ratio_ok = ratio is not None and float(ratio) >= reduction_ratio_min
    recall_ok = material_event_recall is not None and float(material_event_recall) >= 0.95
    numeric_ok = (
        critical_numeric_correctness is not None
        and float(critical_numeric_correctness) >= 0.98
    )
    supplier_ok = unsupported_ticker_to_supplier == 0
    cost_logged = run.get("sum_est_cost_usd") is not None
    scale = (
        accounting
        and order_ok
        and recall_ok
        and numeric_ok
        and supplier_ok
        and miss_ok
        and ratio_ok
        and cost_logged
    )
    return {
        "accounting_identity": accounting,
        "stage_order_violation_ok": order_ok,
        "material_event_recall": material_event_recall,
        "critical_numeric_correctness": critical_numeric_correctness,
        "unsupported_ticker_to_supplier": unsupported_ticker_to_supplier,
        "reject_audit_miss_rate": miss,
        "reduction_ratio": ratio,
        "scale_permitted": bool(scale),
    }
