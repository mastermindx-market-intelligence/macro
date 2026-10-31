"""D5 reviewed acquisition-domain ontology — program/capability/platform graph.

Frozen against ``research/defense_intelligence/DEFENSE_D5_PROGRAM_GRAPH_ARCHITECTURE_FREEZE.md``.
This module is the ONLY admission point for ``government_program_ontology.v1``.
It never derives a program, capability, role, or milestone from a name,
ticker, or fuzzy match; every canonical row is human-reviewed (``curate``) and
every discovery-only row stays ``proposed`` (``propose``, never here).

Refusal semantics are two-tier (freeze SS3.2):

* At ADMISSION time (``scripts/curate_government_program_ontology.py``) an
  offending candidate ROW is refused; the artifact never gains it.
* At LOAD time (this module) the estate's accumulate-then-refuse pattern
  applies: every named-error hit is collected, and if any exist the WHOLE
  artifact is refused via :class:`OntologyInputError` naming every offending
  row and error. A canonical artifact with one bad row is corrupt state, not
  a degraded rail.

Consumers (the workspace builder, the dossier composer) catch
:class:`OntologyInputError` -- and the artifact's plain absence, which is not
an error -- and emit the typed "ontology unavailable" forms instead of
crashing (freeze SS4).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone
from hashlib import sha256
import json
import math
import re
import unicodedata
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse

from engine.government_revenue.public_agreement import agreement_assertion_id as public_agreement_assertion_id, agreement_payload_errors


CONTRACT = "government_program_ontology.v1"
SCHEMA_VERSION = "1.0.0"
PUBLIC_CAPACITY_VERSION = "1.2.0"
PUBLIC_CAPACITY_COLLECTION = "public_capacity_assertions"
PUBLIC_CAPACITY_KINDS = frozenset({"announced_target", "installed_capacity", "demonstrated_throughput"})
PUBLIC_CAPACITY_UNITS = {
    "announced_target": frozenset({"units", "units_per_year", "relative_multiplier"}),
    "installed_capacity": frozenset({"units_per_year"}),
    "demonstrated_throughput": frozenset({"units", "units_per_year"}),
}
PUBLIC_CAPACITY_KEYS = frozenset({
    "id", "revision", "program_id", "product_scope", "product_label", "entity_id",
    "kind", "quantity", "comparator", "unit", "period_label", "known_at",
    "valid_from", "valid_to", "verification_state", "evidence_refs",
    "predecessor_id", "succession_reason",
})
#: Ontology 1.3 (additive over 1.2): closed, source-attributed public oversight
#: findings. Financial/cost/schedule/process observations only -- never a legal
#: verdict, readiness state, issuer allocation or investment ranking, which is
#: why an oversight row carries a quoted excerpt and its hash and NO quantity.
PUBLIC_OVERSIGHT_VERSION = "1.3.0"
PUBLIC_AGREEMENT_VERSION = "1.4.0"
PUBLIC_AGREEMENT_COLLECTION = "public_agreement_assertions"
PUBLIC_OVERSIGHT_COLLECTION = "public_oversight_assertions"
PUBLIC_OVERSIGHT_FINDING_KINDS = frozenset({
    "cost", "schedule", "production_constraint", "contract_process", "protest_status",
})
PUBLIC_OVERSIGHT_REPORTER_ENUM = frozenset({"oversight_body", "quoted_program_office"})
#: Oversight findings may only cite an admitted public official acquisition or
#: congressional source on the existing publisher-host allowlist; issuer IR
#: disclosures and alliance-policy context rows are not oversight sources.
PUBLIC_OVERSIGHT_EVIDENCE_CLASSES = frozenset({
    "official_budget_exhibit", "official_acquisition_report", "official_contract_announcement",
    "official_program_page", "congressional_research",
})
PUBLIC_OVERSIGHT_KEYS = frozenset({
    "id", "revision", "program_id", "finding_kind", "reported_by", "report_series",
    "report_document_id", "report_edition", "published_on", "period_label", "summary",
    "excerpt", "excerpt_sha256", "page", "printed_page_label", "known_at", "valid_from",
    "valid_to", "verification_state", "evidence_refs", "predecessor_id", "succession_reason",
})
#: Bounded free-text fields. The excerpt is the EXACT quoted source text: it is
#: hashed verbatim (no normalization) so any later edit is detectable.
PUBLIC_OVERSIGHT_TEXT_LIMITS: dict[str, int] = {
    "report_series": 256, "report_document_id": 256, "report_edition": 256,
    "period_label": 256, "summary": 2000, "excerpt": 4000,
}
WORKSHEET_CONTRACT = "government_program_ontology_review_worksheet.v1"
WORKSHEET_SCHEMA_VERSION = "1.0.0"
EVENT_CONTRACT = "government_procurement_event.v2"

AUTHORITY: dict[str, Any] = {
    "tier": "display",
    "context_only": True,
    "can_rank": False,
    "can_size": False,
    "can_gate": False,
    "can_originate_signal": False,
    "can_add_candidates": False,
    "can_escalate": False,
}

TOP_LEVEL_KEYS: tuple[str, ...] = (
    "contract", "schema_version", "graph_id", "graph_known_at", "graph_effective_at",
    "authority", "evidence", "programs", "capabilities", "platforms",
    "program_capability_links", "role_assertions", "milestones",
    "program_event_links", "review_coverage", "conflicts", "overrides",
)
_TOP_LEVEL_SET = frozenset(TOP_LEVEL_KEYS)

#: Logical kinds: minted-slug id, `(id, revision)` uniqueness, rename/restructure law.
LOGICAL_COLLECTIONS: tuple[str, ...] = ("programs", "capabilities", "platforms")
#: Content-addressed kinds: `<prefix>:<sha12>` id, succession via superseded_evidence/attribute_revision.
CONTENT_ADDRESSED_COLLECTIONS: tuple[str, ...] = (
    "role_assertions", "milestones", "program_capability_links", "program_event_links",
)

PHASE_ENUM = frozenset({"development", "production", "sustainment", "restructured", "terminated"})
ROLE_ENUM = frozenset({"prime_contractor", "teaming_partner", "subcontractor", "supplier"})
SUCCESSION_REASON_ENUM = frozenset({"renamed", "attribute_revision", "superseded_evidence", "restructured"})
CONTENT_ADDRESSED_SUCCESSION_REASONS = frozenset({"superseded_evidence", "attribute_revision"})
MILESTONE_KIND_ENUM = frozenset({"budget_event", "contract_event", "delivery_event", "review_event"})
TEMPORAL_KIND_ENUM = frozenset({"date", "window"})
EVIDENCE_CLASS_ENUM = frozenset({
    "official_budget_exhibit", "official_acquisition_report", "official_contract_announcement",
    "official_program_page", "congressional_research", "issuer_disclosure", "official_alliance_policy",
})
CLAIM_SCOPE_ENUM = frozenset({
    "program_identity", "capability_need", "role", "milestone",
    "program_capability_link", "program_event_link", "ownership_context", "policy_context",
})
#: Per-kind required coverage scope (freeze SS3.1a, exhaustive).
REQUIRED_CLAIM_SCOPES: dict[str, tuple[str, ...]] = {
    "programs": ("program_identity",),
    "capabilities": ("capability_need",),
    "platforms": ("program_identity",),
    "role_assertions": ("program_identity", "role"),
    "milestones": ("milestone",),
    "program_capability_links": ("program_capability_link",),
    "program_event_links": ("program_event_link",),
}


def allowed_claim_scopes(version: Any) -> frozenset[str]:
    """Claim scopes an artifact of ``version`` may carry on an evidence row.

    Each bounded extension is version-gated: 1.2 adds ``public_capacity``,
    1.3 adds ``public_oversight`` and PRESERVES 1.2's ``public_capacity``.
    Older artifacts keep the exact prior scope surface, so an old version
    still fail-closes on the newer scope names.
    """
    if version == PUBLIC_AGREEMENT_VERSION:
        return CLAIM_SCOPE_ENUM | {"public_capacity", "public_oversight", "public_agreement"}
    if version == PUBLIC_OVERSIGHT_VERSION:
        return CLAIM_SCOPE_ENUM | {"public_capacity", "public_oversight"}
    if version == PUBLIC_CAPACITY_VERSION:
        return CLAIM_SCOPE_ENUM | {"public_capacity"}
    return CLAIM_SCOPE_ENUM


SOURCE_IDENTITY_SYSTEM_ENUM = frozenset({
    "p1_line_item", "rdte_pe", "sar_msar", "official_program_page",
    "contract_announcement", "congressional_research",
})
#: Loader-enforced publisher host allowlist (freeze SS3.1a). Extend only by
#: contract version bump. The asserting issuer's own IR host for
#: ``issuer_disclosure`` rows is authorized per-row via the worksheet pin,
#: never added here (no global issuer->host table exists in the estate).
PUBLISHER_HOST_ALLOWLIST = frozenset({
    "comptroller.defense.gov", "comptroller.war.gov", "www.defense.gov", "www.war.gov",
    "www.secnav.navy.mil", "www.navy.mil", "www.esd.whs.mil", "www.gao.gov",
    "www.congress.gov", "crsreports.congress.gov", "api.usaspending.gov",
    "www.usaspending.gov", "www.sec.gov",
})
REVIEW_STATES = frozenset({"confirmed", "reviewed", "analyst_approved"})
PROPOSED_STATE = "proposed"
COVERAGE_SCOPE_ENUM = frozenset({"program_identity", "capability", "participants", "milestones", "program_event_link"})
COVERAGE_SUBJECT_TYPE_ENUM = frozenset({"program", "award_event"})
#: freeze SS3.1c scope -> collection map (subject_type -> collections it can affect).
COVERAGE_SCOPE_COLLECTIONS: dict[str, tuple[str, ...]] = {
    "program_identity": ("programs", "platforms"),
    "capability": ("program_capability_links",),
    "participants": ("role_assertions",),
    "milestones": ("milestones",),
    "program_event_link": ("program_event_links",),
}
CONFLICT_REASON_ENUM = frozenset({"incompatible_claims", "multi_program_event_attribution"})
OVERRIDE_ACTION_ENUM = frozenset({"retire_row", "block"})

#: LLM boundary (A7-consistent, freeze SS3.2) -- reused verbatim from
#: engine/government_revenue/issuer_graph_expansion.py. A model may never
#: originate program IDs, budget IDs, supplier relationships, validity
#: dates, or economic exposure.
FORBIDDEN_INPUT_KEYS = frozenset({
    "discovery_query_ticker", "query_ticker", "similarity", "similarity_score",
    "name_similarity", "match_score", "fuzzy_score", "confidence_score",
    "llm_rationale", "model_rationale", "search_snippet", "web_snippet",
})
FORBIDDEN_ASSOCIATION_METHODS = frozenset({
    "curated_fuzzy_name", "discovery_query_ticker", "fuzzy_name", "fuzzy",
    "name_similarity", "similar_name", "web_search", "search_snippet",
    "llm", "llm_assertion", "model_assertion", "analyst_recollection",
})

_STRICT_DT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")
_FULL_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_GRAPH_ID = re.compile(r"^program-ontology:(candidate|reviewed):\d{4}-\d{2}-\d{2}:[a-z0-9]+(?:-[a-z0-9]+)*$")
_PROGRAM_ID = re.compile(r"^acq-program:[a-z0-9-]+$")
_CAPABILITY_ID = re.compile(r"^acq-capability:[a-z0-9-]+$")
_PLATFORM_ID = re.compile(r"^platform:[a-z0-9-]+$")
_EVID = re.compile(r"^ev:[0-9a-f]{12}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PROG_ROLE_ID = re.compile(r"^prog-role:[0-9a-f]{12}$")
_PROG_MILESTONE_ID = re.compile(r"^prog-milestone:[0-9a-f]{12}$")
_PROG_CAP_ID = re.compile(r"^prog-cap:[0-9a-f]{12}$")
_PROG_EVENT_ID = re.compile(r"^prog-event:[0-9a-f]{12}$")
_REV_COV_ID = re.compile(r"^rev-cov:[0-9a-f]{12}$")
_CONF_ID = re.compile(r"^conf:[0-9a-f]{12}$")
_OVR_ID = re.compile(r"^ovr:[0-9a-f]{12}$")


class OntologyInputError(ValueError):
    """Raised when a program-ontology artifact fails certification.

    Carries the full accumulate-then-refuse inventory (freeze SS3.2): every
    named error code hit anywhere in the artifact, and every offending row id
    (or ``"<top_level>"`` for a header-level defect), so a caller can report
    exactly what was wrong. Never partially certifies, never repairs.
    """

    def __init__(self, errors: Iterable[str], offending_rows: Iterable[str] = ()) -> None:
        self.errors = sorted(set(errors))
        self.offending_rows = sorted(set(offending_rows))
        super().__init__(
            "program ontology certification refused: " + ", ".join(self.errors)
        )


# ---------------------------------------------------------------------------
# Primitive helpers
# ---------------------------------------------------------------------------


def _text(value: Any) -> str | None:
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


def _strict_datetime(value: Any) -> datetime | None:
    """Parse a D5 timestamp: exactly ``YYYY-MM-DDTHH:MM:SS+00:00``, no other spelling."""
    raw = _text(value)
    if raw is None or _STRICT_DT.fullmatch(raw) is None:
        return None
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S+00:00")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def _full_date(value: Any) -> date | None:
    raw = _text(value)
    if raw is None or _FULL_DATE.fullmatch(raw) is None:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def analysis_as_of(value: Any) -> datetime | None:
    """Coerce ``as_of`` to the estate's end-of-day analysis clock (freeze SS3.1c)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    d = _full_date(value)
    if d is not None:
        return datetime.combine(d, time.max, tzinfo=timezone.utc)
    return _strict_datetime(value)


def _normalize_field(value: Any) -> str:
    """One `sha12` preimage slot: NFC-normalize, lowercase, collapse whitespace."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        raise TypeError("booleans are not a valid sha12 preimage field")
    text = str(value)
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def sha12(*fields: Any) -> str:
    """First 12 lowercase hex of SHA-256 over the ``|``-joined preimage (freeze SS3.1a)."""
    preimage = "|".join(_normalize_field(field) for field in fields)
    return sha256(preimage.encode("utf-8")).hexdigest()[:12]


def _preimage_timestamp(value: Any) -> str:
    """Canonicalize a timestamp preimage slot to UTC ``YYYY-MM-DDTHH:MM:SS+00:00``."""
    parsed = _strict_datetime(value)
    if parsed is None:
        raise ValueError(f"invalid timestamp for sha12 preimage: {value!r}")
    return parsed.strftime("%Y-%m-%dT%H:%M:%S+00:00")


# ---------------------------------------------------------------------------
# Id / preimage grammar (freeze SS3.1a "exhaustive" registry)
# ---------------------------------------------------------------------------


def role_assertion_id(
    *, program_id: str, platform_id: str | None, entity_id: str, role: str,
    role_scope: str, valid_from: str, revision: int,
) -> str:
    return "prog-role:" + sha12(
        program_id, platform_id, entity_id, role, role_scope,
        _preimage_timestamp(valid_from), int(revision),
    )


def public_capacity_assertion_id(row: Mapping[str, Any]) -> str:
    """Bind literal semantic content, clocks, review and evidence; never a quantity estimate."""
    body = {key: row[key] for key in sorted(PUBLIC_CAPACITY_KEYS - {"id"})}
    body["evidence_refs"] = sorted(body["evidence_refs"])
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "prog-capacity:" + sha256(encoded.encode("utf-8")).hexdigest()[:24]


def public_oversight_assertion_id(row: Mapping[str, Any]) -> str:
    """Content-derived oversight row identity (sibling of
    :func:`public_capacity_assertion_id`): binds the quoted excerpt and its
    hash, the report/edition metadata, the source clocks and the cited
    evidence -- so any transcription edit mints a DIFFERENT row that must go
    through succession, never an in-place mutation."""
    body = {key: row[key] for key in sorted(PUBLIC_OVERSIGHT_KEYS - {"id"})}
    body["evidence_refs"] = sorted(body["evidence_refs"])
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "prog-oversight:" + sha256(encoded.encode("utf-8")).hexdigest()[:24]


def public_oversight_excerpt_sha256(excerpt: Any) -> str:
    """SHA-256 over the exact quoted excerpt text, UTF-8, NO normalization.

    The excerpt is evidence: a smart-quote substitution or whitespace edit is
    a content change and must fail the hash, not silently pass."""
    if not isinstance(excerpt, str):
        raise ValueError("oversight excerpt must be a string")
    return sha256(excerpt.encode("utf-8")).hexdigest()


def coverage_scopes_for(graph: Mapping[str, Any]) -> frozenset[str]:
    extra: set[str] = set()
    if graph.get("schema_version") == PUBLIC_CAPACITY_VERSION:
        extra.add("public_capacity")
    if graph.get("schema_version") in (PUBLIC_OVERSIGHT_VERSION, PUBLIC_AGREEMENT_VERSION):
        extra |= {"public_capacity", "public_oversight"}
    if graph.get("schema_version") == PUBLIC_AGREEMENT_VERSION:
        extra |= {"public_agreement"}
    return COVERAGE_SCOPE_ENUM | extra


def milestone_id(
    *, program_id: str, kind: str, title: str, temporal_kind: str,
    date_value: str | None, window: Mapping[str, Any] | None, revision: int,
) -> str:
    if temporal_kind == "date":
        slot5, slot6 = date_value, None
    else:
        window = window or {}
        slot5, slot6 = window.get("from"), window.get("to")
    return "prog-milestone:" + sha12(program_id, kind, title, temporal_kind, slot5, slot6, int(revision))


def program_capability_link_id(
    *, program_id: str, capability_id: str, valid_from: str, revision: int,
) -> str:
    return "prog-cap:" + sha12(program_id, capability_id, _preimage_timestamp(valid_from), int(revision))


def program_event_link_id(
    *, program_id: str, event_contract: str, event_id: str, valid_from: str, revision: int,
) -> str:
    return "prog-event:" + sha12(
        program_id, event_contract, event_id, _preimage_timestamp(valid_from), int(revision)
    )


def review_coverage_id(
    *, scope: str, subject_type: str, subject_id: str, worksheet_sha256: str, known_at: str,
) -> str:
    return "rev-cov:" + sha12(scope, subject_type, subject_id, worksheet_sha256, _preimage_timestamp(known_at))


def conflict_id(
    *, scope: str, subject_type: str, subject_id: str, candidate_row_ids: Sequence[str], known_at: str,
) -> str:
    joined = ",".join(sorted(candidate_row_ids))
    return "conf:" + sha12(scope, subject_type, subject_id, joined, _preimage_timestamp(known_at))


def override_id(
    *, action: str, target_row_id: str | None, subject_type: str | None,
    subject_id: str | None, known_at: str,
) -> str:
    return "ovr:" + sha12(action, target_row_id, subject_type, subject_id, _preimage_timestamp(known_at))


def evidence_id_for_sha256(document_sha256: str) -> str:
    """``ev:<sha12>`` -- the first 12 hex of the row's OWN document sha256, no preimage join."""
    digest = _text(document_sha256)
    if digest is None or _SHA256.fullmatch(digest.lower()) is None:
        raise ValueError(f"invalid evidence sha256: {document_sha256!r}")
    return "ev:" + digest.lower()[:12]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class _Ctx:
    """One certification pass's accumulate-then-refuse state."""

    __slots__ = ("errors", "offending")

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.offending: set[str] = set()

    def err(self, code: str, row_id: str | None = None) -> None:
        if code not in self.errors:
            self.errors.append(code)
        if row_id is not None:
            self.offending.add(row_id)

    def raise_if_any(self) -> None:
        if self.errors:
            raise OntologyInputError(self.errors, self.offending)


def _rows(raw: Mapping[str, Any], field: str, ctx: _Ctx) -> list[dict[str, Any]]:
    value = raw.get(field)
    if not isinstance(value, list):
        ctx.err("ontology_shape_invalid", "<top_level>")
        return []
    out: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, Mapping):
            ctx.err("ontology_row_shape_invalid", "<top_level>")
            continue
        out.append(dict(row))
    return out


def _host(url: Any) -> str | None:
    raw = _text(url)
    if raw is None:
        return None
    try:
        parsed = urlparse(raw)
    except ValueError:
        return None
    return (parsed.hostname or "").lower() or None


def _validate_evidence(raw: Mapping[str, Any], ctx: _Ctx) -> dict[str, dict[str, Any]]:
    evidence_rows = _rows(raw, "evidence", ctx)
    index: dict[str, dict[str, Any]] = {}
    for row in evidence_rows:
        evidence_id = _text(row.get("evidence_id"))
        sha = _text(row.get("sha256"))
        row_key = evidence_id or "<evidence>"
        if evidence_id is None or _EVID.fullmatch(evidence_id) is None:
            ctx.err("ontology_row_shape_invalid", row_key)
        if sha is None or _SHA256.fullmatch(sha.lower()) is None:
            ctx.err("ontology_row_shape_invalid", row_key)
        elif evidence_id is not None and evidence_id != "ev:" + sha.lower()[:12]:
            ctx.err("evidence_id_mismatch", row_key)
        evidence_class = _text(row.get("evidence_class"))
        if evidence_class not in EVIDENCE_CLASS_ENUM:
            ctx.err("ontology_row_shape_invalid", row_key)
        scopes = row.get("claim_scopes")
        # 1.0 remains strict; 1.1 admits alliance policy only as context.
        if raw.get("schema_version") == "1.0.0" and (
            evidence_class == "official_alliance_policy"
            or (isinstance(scopes, list) and "policy_context" in scopes)
        ):
            ctx.err("ontology_row_shape_invalid", row_key)
        if evidence_class == "official_alliance_policy":
            if scopes != ["policy_context"]:
                ctx.err("alliance_policy_scope_refused", row_key)
            source = urlparse(str(row.get("source_url") or ""))
            if (source.scheme != "https" or source.hostname != "www.nato.int"
                or source.username or source.password
                or row.get("retrieved_from_url") != row.get("source_url")):
                ctx.err("alliance_policy_publisher_refused", row_key)
        if (
            not isinstance(scopes, list) or not scopes
            or any(not isinstance(scope, str) for scope in scopes)
            or len(scopes) != len(set(scopes))
            or any(scope not in allowed_claim_scopes(raw.get("schema_version")) for scope in scopes)
        ):
            ctx.err("ontology_row_shape_invalid", row_key)
        retrieved_at = _strict_datetime(row.get("retrieved_at"))
        known_at = _strict_datetime(row.get("known_at"))
        if retrieved_at is None:
            ctx.err("ontology_row_shape_invalid", row_key)
        if known_at is None:
            ctx.err("ontology_row_shape_invalid", row_key)
        elif retrieved_at is not None and retrieved_at > known_at:
            ctx.err("evidence_retrieved_after_known_at", row_key)
        pin = _text(row.get("pinned_issuer_host"))
        basis = _text(row.get("pinned_issuer_host_basis"))
        source_host = _host(row.get("source_url"))
        if evidence_class == "issuer_disclosure":
            if not pin or not basis:
                ctx.err("issuer_host_pin_refused", row_key)
            elif source_host != pin.lower():
                ctx.err("issuer_host_pin_refused", row_key)
        else:
            if pin or basis:
                ctx.err("ontology_row_shape_invalid", row_key)
            # Explicit source amendment in the new capacity contract; the
            # published 1.0/1.1 global allowlist remains unchanged.
            source_url = row.get("source_url")
            army_capacity_source = (
                raw.get("schema_version") in (PUBLIC_CAPACITY_VERSION, PUBLIC_OVERSIGHT_VERSION, PUBLIC_AGREEMENT_VERSION)
                and evidence_class == "official_contract_announcement"
                and source_host == "www.army.mil"
                and isinstance(source_url, str) and source_url == source_url.strip()
                and not any(ord(char) <= 0x20 or ord(char) == 0x7f for char in source_url)
                and source_url.startswith("https://")
                and urlparse(source_url).netloc == "www.army.mil"
                and source_url == row.get("retrieved_from_url")
                and isinstance(scopes, list) and bool(scopes)
                and all(isinstance(scope, str) for scope in scopes)
                and set(scopes) <= {"program_identity", "public_capacity"}
            )
            # 1.4 adds only source-attached agreement observations. The new
            # publisher cannot supply programme identity, roles or milestones.
            agreement_source = (
                raw.get("schema_version") == PUBLIC_AGREEMENT_VERSION
                and evidence_class == "official_contract_announcement"
                and source_host == "www.sda.mil"
                and isinstance(source_url, str) and source_url == source_url.strip()
                and not any(ord(char) <= 0x20 or ord(char) == 0x7f for char in source_url)
                and "\\" not in source_url and source_url.startswith("https://")
                and urlparse(source_url).netloc == "www.sda.mil"
                and source_url == row.get("retrieved_from_url")
                and isinstance(scopes, list) and scopes == ["public_agreement"]
            )
            if not army_capacity_source and not agreement_source and (source_host is None or (source_host not in PUBLISHER_HOST_ALLOWLIST and not (evidence_class == "official_alliance_policy" and source_host == "www.nato.int"))):
                ctx.err("publisher_host_refused", row_key)
        if not _text(row.get("retrieved_from_url")):
            ctx.err("publisher_host_refused", row_key)
        if evidence_id is not None:
            existing = index.get(evidence_id)
            if existing is None:
                index[evidence_id] = row
            elif existing != row:
                # Widening exception: rows differing ONLY in claim_scopes union.
                stripped_existing = {k: v for k, v in existing.items() if k != "claim_scopes"}
                stripped_new = {k: v for k, v in row.items() if k != "claim_scopes"}
                if stripped_existing == stripped_new:
                    merged = dict(existing)
                    merged_scopes = sorted(set(existing.get("claim_scopes", [])) | set(row.get("claim_scopes", [])))
                    merged["claim_scopes"] = merged_scopes
                    index[evidence_id] = merged
                else:
                    ctx.err("duplicate_identity_conflict", row_key)
    return index


def _succession_pair_ok(
    row: Mapping[str, Any], *, content_addressed: bool, ctx: _Ctx, row_id: str,
) -> None:
    revision = row.get("revision")
    predecessor_id = row.get("predecessor_id")
    succession_reason = row.get("succession_reason")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        ctx.err("ontology_row_shape_invalid", row_id)
        return
    if content_addressed:
        if revision == 1:
            if predecessor_id is not None or succession_reason is not None:
                ctx.err("succession_shape_invalid", row_id)
        else:
            if predecessor_id is None or succession_reason not in CONTENT_ADDRESSED_SUCCESSION_REASONS:
                ctx.err("succession_shape_invalid", row_id)
    else:
        # Logical kind: revision-1 rows carry the pair ONLY on an identity
        # break (predecessor_id + succession_reason == "restructured");
        # otherwise the pair is forbidden. revision >= 2 rows REQUIRE the
        # pair, with "restructured" reserved for the identity-break's own
        # predecessor close-out row.
        if revision == 1:
            if predecessor_id is not None:
                if succession_reason != "restructured":
                    ctx.err("succession_shape_invalid", row_id)
            elif succession_reason is not None:
                ctx.err("succession_shape_invalid", row_id)
        else:
            if succession_reason not in SUCCESSION_REASON_ENUM:
                ctx.err("succession_shape_invalid", row_id)
            if predecessor_id is not None and succession_reason != "restructured":
                ctx.err("succession_shape_invalid", row_id)


def _validate_temporal_claim(
    row: Mapping[str, Any], *, ctx: _Ctx, row_id: str, evidence_index: Mapping[str, Mapping[str, Any]],
    graph_known_at: datetime | None, graph_effective_at: datetime | None,
) -> tuple[datetime | None, datetime | None, datetime | None]:
    known_at = _strict_datetime(row.get("known_at"))
    valid_from = _strict_datetime(row.get("valid_from"))
    valid_to_raw = row.get("valid_to")
    valid_to = None if valid_to_raw is None else _strict_datetime(valid_to_raw)
    if known_at is None:
        ctx.err("ontology_row_shape_invalid", row_id)
    if valid_from is None:
        ctx.err("ontology_row_shape_invalid", row_id)
    if valid_to_raw is not None and valid_to is None:
        ctx.err("ontology_row_shape_invalid", row_id)
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        ctx.err("claim_validity_window_inverted", row_id)
    if known_at is not None and graph_known_at is not None and known_at > graph_known_at:
        ctx.err("future_known_claim", row_id)
    if valid_from is not None and graph_effective_at is not None and valid_from > graph_effective_at:
        ctx.err("future_effective_claim", row_id)
    refs = row.get("evidence_refs")
    if not isinstance(refs, list) or not refs or len(refs) != len(set(refs)):
        ctx.err("missing_evidence_refs", row_id)
        refs = []
    scopes_union: set[str] = set()
    for ref in refs:
        source = evidence_index.get(_text(ref) or "")
        if source is None:
            ctx.err("dangling_reference", row_id)
            continue
        scopes_union |= set(source.get("claim_scopes", []))
        evidence_known_at = _strict_datetime(source.get("known_at"))
        if known_at is not None and evidence_known_at is not None and evidence_known_at > known_at:
            ctx.err("evidence_known_after_claim", row_id)
    return known_at, valid_from, valid_to


def _check_claim_scope_coverage(
    collection: str, scopes_union: set[str], *, ctx: _Ctx, row_id: str,
) -> None:
    required = REQUIRED_CLAIM_SCOPES.get(collection, ())
    if any(scope not in scopes_union for scope in required):
        ctx.err("claim_scope_coverage_missing", row_id)


def _intervals_overlap(
    a_from: datetime | None, a_to: datetime | None, b_from: datetime | None, b_to: datetime | None,
) -> bool:
    """Freeze SS5 frozen temporal-compatibility definition (half-open
    [from, to) intervals, STRICT inequality): ``a.valid_from <
    (b.valid_to or +inf) AND b.valid_from < (a.valid_to or +inf)``. A row
    starting exactly when the other ends does NOT overlap it."""
    if a_from is None or b_from is None:
        return True
    a_upper = a_to or datetime.max.replace(tzinfo=timezone.utc)
    b_upper = b_to or datetime.max.replace(tzinfo=timezone.utc)
    return a_from < b_upper and b_from < a_upper


def _overlaps_any(
    a_from: datetime | None, a_to: datetime | None, candidate_rows: Sequence[Mapping[str, Any]],
) -> bool:
    """True iff [a_from, a_to) overlaps at least one candidate row's interval
    (freeze SS3.1: a relation's interval must be compatible with an endpoint
    that may itself span several logical revisions)."""
    if a_from is None or not candidate_rows:
        return True
    for row in candidate_rows:
        b_from = _strict_datetime(row.get("valid_from"))
        b_to_raw = row.get("valid_to")
        b_to = None if b_to_raw is None else _strict_datetime(b_to_raw)
        if _intervals_overlap(a_from, a_to, b_from, b_to):
            return True
    return False


def canonical_award_identity_comparand(award_change: Mapping[str, Any]) -> str | None:
    """Freeze SS3.1b's exact precedence over an event's own `award_change`
    fields (mirrors `point_in_time.py:148-165`'s `canonical_award_identity`,
    including the idempotent `removeprefix`): `generated:<id>` preferred,
    else the raw `award_key`, else `piid:<id>`, else ``None``."""
    generated_award_id = award_change.get("generated_award_id")
    award_key = award_change.get("award_key")
    piid = award_change.get("piid")
    if generated_award_id:
        return "generated:" + str(generated_award_id).removeprefix("generated:")
    if award_key:
        return award_key
    if piid:
        return f"piid:{piid}"
    return None


def _event_hash_agrees(row: Mapping[str, Any], live_event: Mapping[str, Any]) -> bool:
    """SS3.1b hash-agreement check shared by the curate-time verifier and
    this loader's load-time re-verification."""
    award_change = live_event.get("award_change") or {}
    source_identity = award_change.get("source_identity") or {}
    if (
        row.get("event_source_identity_id") != source_identity.get("id")
        or row.get("event_source_identity_content_sha256") != source_identity.get("content_sha256")
    ):
        return False
    return row.get("canonical_award_identity") == canonical_award_identity_comparand(award_change)


def load_program_ontology_graph(
    raw: Mapping[str, Any] | None,
    *,
    workspace_events: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Validate and normalize a reviewed D5 program-ontology artifact.

    Returns ``None`` when ``raw`` is ``None`` (the artifact is simply absent
    -- not an error; freeze SS4's "ontology unavailable" form applies).
    Raises :class:`OntologyInputError` when the artifact is present but fails
    certification. Returns a deep-copied, validated dict otherwise.

    ``workspace_events`` (freeze SS3.1b, load-time half): when supplied
    (``{event_id: government_procurement_event.v2 row}``), every linked
    event STILL PRESENT in it is re-verified for source-identity/canonical-
    identity hash agreement; a mismatch refuses `event_identity_mismatch`.
    An event absent from this mapping is NOT a refusal -- the event plane is
    append-only truth and aging out of a capped window is not evidence of
    nonexistence. Omitting the parameter entirely (``None``) skips this
    re-verification altogether (a caller with no workspace available, e.g.
    an isolated schema check).
    """
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise OntologyInputError(["ontology_not_mapping"], ["<top_level>"])

    ctx = _Ctx()
    # Refuse malformed reference types before any cross-reference set operation.
    malformed_refs: list[str] = []
    def check_reference_types(value: Any, row_key: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key == "evidence_ref" and not isinstance(child, str):
                    malformed_refs.append(row_key)
                elif key in {"evidence_refs", "claim_scopes"} and (not isinstance(child, list) or any(not isinstance(item, str) for item in child)):
                    malformed_refs.append(row_key)
                else:
                    check_reference_types(child, row_key)
        elif isinstance(value, list):
            for child in value:
                key = str(child.get("id") or child.get("link_id") or row_key) if isinstance(child, Mapping) else row_key
                check_reference_types(child, key)
    check_reference_types(raw, "<top_level>")
    if malformed_refs:
        raise OntologyInputError(["ontology_row_shape_invalid"], malformed_refs)
    agreement_enabled = raw.get("schema_version") == PUBLIC_AGREEMENT_VERSION
    oversight_enabled = raw.get("schema_version") in (PUBLIC_OVERSIGHT_VERSION, PUBLIC_AGREEMENT_VERSION)
    # 1.3 is strictly additive over 1.2: the capacity collection stays present
    # AND fully validated below; the oversight collection joins the required
    # top-level shape. Any older version carrying the newer collection (or the
    # newer claim scope) still refuses on its own unchanged shape law.
    capacity_enabled = oversight_enabled or raw.get("schema_version") == PUBLIC_CAPACITY_VERSION
    top_level_keys = TOP_LEVEL_KEYS + ((PUBLIC_CAPACITY_COLLECTION,) if capacity_enabled else ()) + ((PUBLIC_OVERSIGHT_COLLECTION,) if oversight_enabled else ()) + ((PUBLIC_AGREEMENT_COLLECTION,) if agreement_enabled else ())
    if set(raw) != set(top_level_keys):
        ctx.err("ontology_shape_invalid", "<top_level>")
    if raw.get("contract") != CONTRACT:
        ctx.err("ontology_contract_invalid", "<top_level>")
    if raw.get("schema_version") not in {SCHEMA_VERSION, "1.1.0", PUBLIC_CAPACITY_VERSION, PUBLIC_OVERSIGHT_VERSION, PUBLIC_AGREEMENT_VERSION}:
        ctx.err("ontology_schema_version_invalid", "<top_level>")
    graph_id = _text(raw.get("graph_id"))
    if graph_id is None or _GRAPH_ID.fullmatch(graph_id) is None:
        ctx.err("invalid_graph_id", "<top_level>")
    graph_known_at = _strict_datetime(raw.get("graph_known_at"))
    graph_effective_at = _strict_datetime(raw.get("graph_effective_at"))
    if graph_known_at is None:
        ctx.err("invalid_graph_known_at", "<top_level>")
    if graph_effective_at is None:
        ctx.err("invalid_graph_effective_at", "<top_level>")
    if raw.get("authority") != AUTHORITY:
        ctx.err("invalid_authority_block", "<top_level>")

    evidence_index = _validate_evidence(raw, ctx)

    policy_ids = {key for key, row in evidence_index.items()
                  if row.get("evidence_class") == "official_alliance_policy"}
    def refuse_policy_attribution(value: Any, row_key: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key == "evidence_ref" and child in policy_ids:
                    ctx.err("alliance_policy_noncontext_use", row_key)
                elif key == "evidence_refs" and isinstance(child, list) and policy_ids.intersection(item for item in child if isinstance(item, str)):
                    ctx.err("alliance_policy_noncontext_use", row_key)
                else:
                    refuse_policy_attribution(child, row_key)
        elif isinstance(value, list):
            for child in value:
                refuse_policy_attribution(child, row_key)
    for collection in top_level_keys:
        if collection == "evidence":
            continue
        rows = raw.get(collection)
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, Mapping):
                    refuse_policy_attribution(row, str(row.get("id") or row.get("link_id") or collection))

    programs = _rows(raw, "programs", ctx)
    capabilities = _rows(raw, "capabilities", ctx)
    platforms = _rows(raw, "platforms", ctx)
    program_capability_links = _rows(raw, "program_capability_links", ctx)
    role_assertions = _rows(raw, "role_assertions", ctx)
    milestones = _rows(raw, "milestones", ctx)
    program_event_links = _rows(raw, "program_event_links", ctx)
    review_coverage = _rows(raw, "review_coverage", ctx)
    conflicts = _rows(raw, "conflicts", ctx)
    overrides = _rows(raw, "overrides", ctx)

    program_ids: set[str] = set()
    program_by_id_rev: dict[tuple[str, int], dict[str, Any]] = {}
    for row in programs:
        row_id = _text(row.get("id")) or "<program>"
        revision = row.get("revision")
        key = f"{row_id}:{revision}"
        if row_id is None or _PROGRAM_ID.fullmatch(row_id) is None:
            ctx.err("ontology_row_shape_invalid", key)
        phase = _text(row.get("phase"))
        if phase not in PHASE_ENUM:
            ctx.err("ontology_row_shape_invalid", key)
        if row.get("budget_program_keys") != []:
            ctx.err("ontology_row_shape_invalid", key)
        if row.get("verification_state") not in REVIEW_STATES:
            ctx.err("ontology_row_shape_invalid", key)
        _succession_pair_ok(row, content_addressed=False, ctx=ctx, row_id=key)
        known_at, valid_from, valid_to = _validate_temporal_claim(
            row, ctx=ctx, row_id=key, evidence_index=evidence_index,
            graph_known_at=graph_known_at, graph_effective_at=graph_effective_at,
        )
        scopes_union = _row_evidence_scopes(row, evidence_index)
        _check_claim_scope_coverage("programs", scopes_union, ctx=ctx, row_id=key)
        for src in row.get("source_identities") or []:
            if not isinstance(src, Mapping) or _text(src.get("system")) not in SOURCE_IDENTITY_SYSTEM_ENUM:
                ctx.err("ontology_row_shape_invalid", key)
        program_ids.add(row_id)
        if isinstance(revision, int) and not isinstance(revision, bool):
            _register_logical_row(program_by_id_rev, (row_id, revision), row, ctx=ctx, row_key=key)

    capability_ids: set[str] = set()
    capability_by_id_rev: dict[tuple[str, int], dict[str, Any]] = {}
    for row in capabilities:
        row_id = _text(row.get("id")) or "<capability>"
        revision = row.get("revision")
        key = f"{row_id}:{revision}"
        if row_id is None or _CAPABILITY_ID.fullmatch(row_id) is None:
            ctx.err("ontology_row_shape_invalid", key)
        if row.get("verification_state") not in REVIEW_STATES:
            ctx.err("ontology_row_shape_invalid", key)
        _succession_pair_ok(row, content_addressed=False, ctx=ctx, row_id=key)
        _validate_temporal_claim(
            row, ctx=ctx, row_id=key, evidence_index=evidence_index,
            graph_known_at=graph_known_at, graph_effective_at=graph_effective_at,
        )
        scopes_union = _row_evidence_scopes(row, evidence_index)
        _check_claim_scope_coverage("capabilities", scopes_union, ctx=ctx, row_id=key)
        capability_ids.add(row_id)
        if isinstance(revision, int) and not isinstance(revision, bool):
            _register_logical_row(capability_by_id_rev, (row_id, revision), row, ctx=ctx, row_key=key)

    platform_ids: set[str] = set()
    platform_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    platform_by_id_rev: dict[tuple[str, int], dict[str, Any]] = {}
    for row in platforms:
        row_id = _text(row.get("id")) or "<platform>"
        revision = row.get("revision")
        key = f"{row_id}:{revision}"
        if row_id is None or _PLATFORM_ID.fullmatch(row_id) is None:
            ctx.err("ontology_row_shape_invalid", key)
        program_ref = _text(row.get("program_id"))
        if program_ref is None or program_ref not in program_ids:
            ctx.err("dangling_reference", key)
        variant_of = row.get("variant_of")
        if variant_of is not None:
            variant_of = _text(variant_of)
            if variant_of not in platform_ids and variant_of != row_id:
                # Forward references inside one artifact are legal; resolved
                # against the FULL platform id set collected below.
                pass
        if row.get("verification_state") not in REVIEW_STATES:
            ctx.err("ontology_row_shape_invalid", key)
        _succession_pair_ok(row, content_addressed=False, ctx=ctx, row_id=key)
        _validate_temporal_claim(
            row, ctx=ctx, row_id=key, evidence_index=evidence_index,
            graph_known_at=graph_known_at, graph_effective_at=graph_effective_at,
        )
        scopes_union = _row_evidence_scopes(row, evidence_index)
        _check_claim_scope_coverage("platforms", scopes_union, ctx=ctx, row_id=key)
        if row_id:
            platform_ids.add(row_id)
            platform_by_id[row_id].append(row)
        if isinstance(revision, int) and not isinstance(revision, bool):
            _register_logical_row(platform_by_id_rev, (row_id, revision), row, ctx=ctx, row_key=key)
    # Second pass: variant_of / program_id-consistency now the full platform
    # id set is known.
    for row in platforms:
        row_id = _text(row.get("id")) or "<platform>"
        key = f"{row_id}:{row.get('revision')}"
        variant_of = row.get("variant_of")
        if variant_of is not None:
            variant_of = _text(variant_of)
            if variant_of not in platform_ids:
                ctx.err("dangling_reference", key)
            else:
                variant_rows = platform_by_id.get(variant_of) or []
                if variant_rows and variant_rows[0].get("program_id") != row.get("program_id"):
                    ctx.err("dangling_reference", key)

    for row in program_capability_links:
        row_id = _text(row.get("link_id")) or "<prog-cap>"
        key = row_id
        if row_id is None or _PROG_CAP_ID.fullmatch(row_id) is None:
            ctx.err("ontology_row_shape_invalid", key)
        program_ref = _text(row.get("program_id"))
        capability_ref = _text(row.get("capability_id"))
        if program_ref not in program_ids or capability_ref not in capability_ids:
            ctx.err("dangling_reference", key)
        if row.get("verification_state") not in REVIEW_STATES:
            ctx.err("ontology_row_shape_invalid", key)
        _succession_pair_ok(row, content_addressed=True, ctx=ctx, row_id=key)
        known_at, valid_from, valid_to = _validate_temporal_claim(
            row, ctx=ctx, row_id=key, evidence_index=evidence_index,
            graph_known_at=graph_known_at, graph_effective_at=graph_effective_at,
        )
        scopes_union = _row_evidence_scopes(row, evidence_index)
        _check_claim_scope_coverage("program_capability_links", scopes_union, ctx=ctx, row_id=key)
        if program_ref in program_ids and capability_ref in capability_ids:
            program_revs = [r for r in programs if _text(r.get("id")) == program_ref]
            capability_revs = [r for r in capabilities if _text(r.get("id")) == capability_ref]
            if not _overlaps_any(valid_from, valid_to, program_revs) or not _overlaps_any(valid_from, valid_to, capability_revs):
                ctx.err("temporal_incompatible", key)
        if row_id and _PROG_CAP_ID.fullmatch(row_id) and valid_from is not None:
            try:
                expected = program_capability_link_id(
                    program_id=row.get("program_id"), capability_id=row.get("capability_id"),
                    valid_from=row.get("valid_from"), revision=row.get("revision") or 0,
                )
            except (TypeError, ValueError):
                expected = None
            if expected is not None and expected != row_id:
                ctx.err("duplicate_identity_conflict", key)

    role_assertion_ids: set[str] = set()
    for row in role_assertions:
        row_id = _text(row.get("id")) or "<prog-role>"
        key = row_id
        if row_id is None or _PROG_ROLE_ID.fullmatch(row_id) is None:
            ctx.err("ontology_row_shape_invalid", key)
        program_ref = _text(row.get("program_id"))
        if program_ref not in program_ids:
            ctx.err("dangling_reference", key)
        platform_ref = row.get("platform_id")
        if platform_ref is not None:
            platform_ref = _text(platform_ref)
            platform_rows = platform_by_id.get(platform_ref) or []
            if platform_ref not in platform_ids:
                ctx.err("platform_reference_invalid", key)
            elif platform_rows[0].get("program_id") != program_ref:
                ctx.err("platform_reference_invalid", key)
            else:
                p_valid_from = _strict_datetime(platform_rows[0].get("valid_from"))
                p_valid_to_raw = platform_rows[0].get("valid_to")
                p_valid_to = None if p_valid_to_raw is None else _strict_datetime(p_valid_to_raw)
                r_valid_from = _strict_datetime(row.get("valid_from"))
                r_valid_to_raw = row.get("valid_to")
                r_valid_to = None if r_valid_to_raw is None else _strict_datetime(r_valid_to_raw)
                if not _intervals_overlap(r_valid_from, r_valid_to, p_valid_from, p_valid_to):
                    ctx.err("platform_reference_invalid", key)
        if _text(row.get("entity_id")) is None:
            ctx.err("ontology_row_shape_invalid", key)
        if _text(row.get("role")) not in ROLE_ENUM:
            ctx.err("ontology_row_shape_invalid", key)
        if _text(row.get("role_scope")) is None:
            ctx.err("ontology_row_shape_invalid", key)
        if not isinstance(row.get("shared_scope"), bool):
            ctx.err("ontology_row_shape_invalid", key)
        if not isinstance(row.get("single_document_dual_scope"), bool):
            ctx.err("ontology_row_shape_invalid", key)
        if "economic_weight" not in row or row.get("economic_weight") is not None:
            ctx.err("ontology_row_shape_invalid", key)
        if row.get("verification_state") not in REVIEW_STATES:
            ctx.err("ontology_row_shape_invalid", key)
        _succession_pair_ok(row, content_addressed=True, ctx=ctx, row_id=key)
        known_at, valid_from, valid_to = _validate_temporal_claim(
            row, ctx=ctx, row_id=key, evidence_index=evidence_index,
            graph_known_at=graph_known_at, graph_effective_at=graph_effective_at,
        )
        scopes_union = _row_evidence_scopes(row, evidence_index)
        _check_claim_scope_coverage("role_assertions", scopes_union, ctx=ctx, row_id=key)
        if row_id in role_assertion_ids:
            ctx.err("duplicate_identity_conflict", key)
        role_assertion_ids.add(row_id)
        if row_id and _PROG_ROLE_ID.fullmatch(row_id) and valid_from is not None:
            try:
                expected = role_assertion_id(
                    program_id=row.get("program_id"), platform_id=row.get("platform_id"),
                    entity_id=row.get("entity_id"), role=row.get("role"),
                    role_scope=row.get("role_scope"), valid_from=row.get("valid_from"),
                    revision=row.get("revision") or 0,
                )
            except (TypeError, ValueError):
                expected = None
            if expected is not None and expected != row_id:
                ctx.err("duplicate_identity_conflict", key)

    milestone_ids: set[str] = set()
    milestones_by_program: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in milestones:
        row_id = _text(row.get("id")) or "<prog-milestone>"
        key = row_id
        if row_id is None or _PROG_MILESTONE_ID.fullmatch(row_id) is None:
            ctx.err("ontology_row_shape_invalid", key)
        program_ref = _text(row.get("program_id"))
        if program_ref not in program_ids:
            ctx.err("dangling_reference", key)
        kind = _text(row.get("kind"))
        if kind not in MILESTONE_KIND_ENUM:
            ctx.err("ontology_row_shape_invalid", key)
        temporal_kind = _text(row.get("temporal_kind"))
        has_date = "date" in row
        has_window = "window" in row
        if temporal_kind not in TEMPORAL_KIND_ENUM:
            ctx.err("milestone_temporal_shape_invalid", key)
        elif temporal_kind == "date":
            if not has_date or has_window or _full_date(row.get("date")) is None:
                ctx.err("milestone_temporal_shape_invalid", key)
        elif temporal_kind == "window":
            window = row.get("window")
            if (
                has_date or not has_window or not isinstance(window, Mapping)
                or _full_date(window.get("from")) is None or _full_date(window.get("to")) is None
                or _full_date(window.get("from")) > _full_date(window.get("to"))
            ):
                ctx.err("milestone_temporal_shape_invalid", key)
        if has_date and has_window:
            ctx.err("milestone_temporal_shape_invalid", key)
        if not has_date and not has_window:
            ctx.err("milestone_temporal_shape_invalid", key)
        if row.get("verification_state") not in REVIEW_STATES:
            ctx.err("ontology_row_shape_invalid", key)
        _succession_pair_ok(row, content_addressed=True, ctx=ctx, row_id=key)
        _validate_temporal_claim(
            row, ctx=ctx, row_id=key, evidence_index=evidence_index,
            graph_known_at=graph_known_at, graph_effective_at=graph_effective_at,
        )
        scopes_union = _row_evidence_scopes(row, evidence_index)
        _check_claim_scope_coverage("milestones", scopes_union, ctx=ctx, row_id=key)
        if row_id in milestone_ids:
            ctx.err("duplicate_identity_conflict", key)
        milestone_ids.add(row_id)
        if row_id and _PROG_MILESTONE_ID.fullmatch(row_id) and temporal_kind in TEMPORAL_KIND_ENUM:
            try:
                expected = milestone_id(
                    program_id=row.get("program_id"), kind=kind, title=row.get("title"),
                    temporal_kind=temporal_kind, date_value=row.get("date"),
                    window=row.get("window"), revision=row.get("revision") or 0,
                )
            except (TypeError, ValueError):
                expected = None
            if expected is not None and expected != row_id:
                ctx.err("duplicate_identity_conflict", key)
        if program_ref:
            milestones_by_program[program_ref].append(row)

    program_event_link_ids: set[str] = set()
    links_by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in program_event_links:
        row_id = _text(row.get("link_id")) or "<prog-event>"
        key = row_id
        if row_id is None or _PROG_EVENT_ID.fullmatch(row_id) is None:
            ctx.err("ontology_row_shape_invalid", key)
        program_ref = _text(row.get("program_id"))
        if program_ref not in program_ids:
            ctx.err("dangling_reference", key)
        if row.get("event_contract") != EVENT_CONTRACT:
            ctx.err("ontology_row_shape_invalid", key)
        event_id_value = _text(row.get("event_id"))
        if event_id_value is None:
            ctx.err("ontology_row_shape_invalid", key)
        if row.get("verification_state") not in REVIEW_STATES:
            ctx.err("ontology_row_shape_invalid", key)
        _succession_pair_ok(row, content_addressed=True, ctx=ctx, row_id=key)
        known_at, valid_from, valid_to = _validate_temporal_claim(
            row, ctx=ctx, row_id=key, evidence_index=evidence_index,
            graph_known_at=graph_known_at, graph_effective_at=graph_effective_at,
        )
        scopes_union = _row_evidence_scopes(row, evidence_index)
        _check_claim_scope_coverage("program_event_links", scopes_union, ctx=ctx, row_id=key)
        if row_id in program_event_link_ids:
            ctx.err("duplicate_identity_conflict", key)
        program_event_link_ids.add(row_id)
        if workspace_events is not None and event_id_value is not None:
            live_event = workspace_events.get(event_id_value)
            if live_event is not None and not _event_hash_agrees(row, live_event):
                ctx.err("event_identity_mismatch", key)
        if row_id and _PROG_EVENT_ID.fullmatch(row_id) and valid_from is not None:
            try:
                expected = program_event_link_id(
                    program_id=row.get("program_id"), event_contract=row.get("event_contract"),
                    event_id=row.get("event_id"), valid_from=row.get("valid_from"),
                    revision=row.get("revision") or 0,
                )
            except (TypeError, ValueError):
                expected = None
            if expected is not None and expected != row_id:
                ctx.err("duplicate_identity_conflict", key)
        if event_id_value:
            links_by_event[event_id_value].append(row)

    capacity_ids: set[str] = set()
    if capacity_enabled:
        capacity_rows = _rows(raw, PUBLIC_CAPACITY_COLLECTION, ctx)
        for row in capacity_rows:
            key = _text(row.get("id")) or "<public-capacity>"
            text_fields = ("id", "program_id", "product_scope", "product_label", "kind", "comparator", "unit", "period_label", "known_at", "valid_from", "verification_state")
            nullable_fields = ("entity_id", "valid_to", "predecessor_id", "succession_reason")
            if (set(row) != PUBLIC_CAPACITY_KEYS
                    or any(not isinstance(row.get(field), str) for field in text_fields)
                    or any(row.get(field) is not None and not isinstance(row[field], str) for field in nullable_fields)):
                ctx.err("public_capacity_shape_invalid", key)
                continue
            if re.fullmatch(r"prog-capacity:[a-f0-9]{24}", key) is None:
                ctx.err("public_capacity_identity_invalid", key)
            if key in capacity_ids:
                ctx.err("duplicate_identity_conflict", key)
            capacity_ids.add(key)
            quantity = row.get("quantity")
            if type(quantity) not in (int, float) or (type(quantity) is float and not math.isfinite(quantity)) or quantity <= 0:
                ctx.err("public_capacity_quantity_invalid", key)
            if row.get("kind") not in PUBLIC_CAPACITY_KINDS or row.get("unit") not in PUBLIC_CAPACITY_UNITS.get(row.get("kind"), ()):
                ctx.err("public_capacity_kind_unit_invalid", key)
            if row.get("comparator") not in {"exact", "approximately", "greater_than"}:
                ctx.err("public_capacity_comparator_invalid", key)
            if row.get("product_scope") not in {"whole_program", "component"}:
                ctx.err("public_capacity_scope_invalid", key)
            for field in ("product_label", "period_label"):
                if not isinstance(row.get(field), str) or not 1 <= len(row[field].strip()) <= 256:
                    ctx.err("public_capacity_shape_invalid", key)
            if row.get("entity_id") is not None and (not isinstance(row["entity_id"], str) or not row["entity_id"].strip()):
                ctx.err("public_capacity_shape_invalid", key)
            if row.get("verification_state") not in REVIEW_STATES:
                ctx.err("public_capacity_review_required", key)
            program_ref = row.get("program_id")
            if program_ref not in program_ids:
                ctx.err("dangling_reference", key)
            _succession_pair_ok(row, content_addressed=True, ctx=ctx, row_id=key)
            _, valid_from, valid_to = _validate_temporal_claim(
                row, ctx=ctx, row_id=key, evidence_index=evidence_index,
                graph_known_at=graph_known_at, graph_effective_at=graph_effective_at,
            )
            if not {"program_identity", "public_capacity"} <= _row_evidence_scopes(row, evidence_index):
                ctx.err("claim_scope_coverage_missing", key)
            if program_ref in program_ids and not _overlaps_any(valid_from, valid_to, [r for r in programs if r.get("id") == program_ref]):
                ctx.err("temporal_incompatible", key)
            try:
                if public_capacity_assertion_id(row) != key:
                    ctx.err("public_capacity_identity_invalid", key)
            except (KeyError, TypeError, ValueError):
                ctx.err("public_capacity_identity_invalid", key)
        for row in capacity_rows:
            predecessor = row.get("predecessor_id")
            if predecessor is not None:
                key = _text(row.get("id")) or "<public-capacity>"
                previous = next((item for item in capacity_rows if item.get("id") == predecessor), None)
                if previous is None:
                    ctx.err("dangling_reference", key)
                elif (row.get("revision") != previous.get("revision", 0) + 1
                      or any(row.get(field) != previous.get(field) for field in ("program_id", "product_scope", "product_label", "entity_id", "kind"))
                      or (_strict_datetime(row.get("known_at")) is not None and _strict_datetime(previous.get("known_at")) is not None
                          and _strict_datetime(row["known_at"]) < _strict_datetime(previous["known_at"]))):
                    ctx.err("public_capacity_succession_invalid", key)

    oversight_ids: set[str] = set()
    if oversight_enabled:
        oversight_rows = _rows(raw, PUBLIC_OVERSIGHT_COLLECTION, ctx)
        for row in oversight_rows:
            key = _text(row.get("id")) or "<public-oversight>"
            str_fields = ("id", "program_id", "finding_kind", "reported_by", "report_series",
                          "report_document_id", "report_edition", "published_on", "period_label",
                          "summary", "excerpt", "excerpt_sha256", "known_at", "valid_from",
                          "verification_state")
            int_fields = ("revision", "page")
            nullable_fields = ("valid_to", "printed_page_label", "predecessor_id", "succession_reason")
            if (set(row) != PUBLIC_OVERSIGHT_KEYS
                    or any(not isinstance(row.get(field), str) for field in str_fields)
                    or any(type(row.get(field)) is not int for field in int_fields)
                    or any(row.get(field) is not None and not isinstance(row[field], str) for field in nullable_fields)):
                ctx.err("public_oversight_shape_invalid", key)
                continue
            if re.fullmatch(r"prog-oversight:[a-f0-9]{24}", key) is None:
                ctx.err("public_oversight_identity_invalid", key)
            if key in oversight_ids:
                ctx.err("duplicate_identity_conflict", key)
            oversight_ids.add(key)
            if row["page"] < 1:
                ctx.err("public_oversight_page_invalid", key)
            if row["finding_kind"] not in PUBLIC_OVERSIGHT_FINDING_KINDS:
                ctx.err("public_oversight_finding_kind_invalid", key)
            if row["reported_by"] not in PUBLIC_OVERSIGHT_REPORTER_ENUM:
                ctx.err("public_oversight_reported_by_invalid", key)
            publication_date = _full_date(row["published_on"])
            claim_known_at = _strict_datetime(row["known_at"])
            if publication_date is None:
                ctx.err("public_oversight_publication_date_invalid", key)
            elif claim_known_at is not None and publication_date > claim_known_at.date():
                # A report date does not set claim currency, but a claim cannot
                # be publicly known before its cited report's publication day.
                ctx.err("public_oversight_publication_after_known", key)
            for field, limit in PUBLIC_OVERSIGHT_TEXT_LIMITS.items():
                if not 1 <= len(row[field].strip()) <= limit:
                    ctx.err("public_oversight_shape_invalid", key)
            if row["printed_page_label"] is not None and not 1 <= len(row["printed_page_label"].strip()) <= 64:
                ctx.err("public_oversight_shape_invalid", key)
            if row["excerpt_sha256"] != public_oversight_excerpt_sha256(row["excerpt"]):
                ctx.err("public_oversight_excerpt_hash_mismatch", key)
            if row["verification_state"] not in REVIEW_STATES:
                ctx.err("public_oversight_review_required", key)
            program_ref = row["program_id"]
            if program_ref not in program_ids:
                ctx.err("dangling_reference", key)
            _succession_pair_ok(row, content_addressed=True, ctx=ctx, row_id=key)
            _, valid_from, valid_to = _validate_temporal_claim(
                row, ctx=ctx, row_id=key, evidence_index=evidence_index,
                graph_known_at=graph_known_at, graph_effective_at=graph_effective_at,
            )
            # Source law: every cited ref must be ONE qualified oversight
            # source -- oversight-scoped, an official acquisition/congressional
            # class, and (when several refs) all the SAME document. An excerpt
            # pinned to a mixed or unrelated citation is refused.
            sources = [evidence_index.get(_text(ref) or "") for ref in row["evidence_refs"]]
            if any(source is None
                   or "public_oversight" not in set(source.get("claim_scopes") or [])
                   or source.get("evidence_class") not in PUBLIC_OVERSIGHT_EVIDENCE_CLASSES
                   for source in sources):
                ctx.err("public_oversight_evidence_unrelated", key)
            source_digests = {source.get("sha256") for source in sources if isinstance(source, Mapping)}
            source_urls = {source.get("source_url") for source in sources if isinstance(source, Mapping)}
            if len(source_digests) > 1 or len(source_urls) > 1:
                ctx.err("public_oversight_evidence_unrelated", key)
            if not {"program_identity", "public_oversight"} <= _row_evidence_scopes(row, evidence_index):
                ctx.err("claim_scope_coverage_missing", key)
            if program_ref in program_ids and not _overlaps_any(valid_from, valid_to, [r for r in programs if r.get("id") == program_ref]):
                ctx.err("temporal_incompatible", key)
            try:
                if public_oversight_assertion_id(row) != key:
                    ctx.err("public_oversight_identity_invalid", key)
            except (KeyError, TypeError, ValueError):
                ctx.err("public_oversight_identity_invalid", key)
        # Correction-chain law: a successor revises the SAME finding -- same
        # program, finding kind and reporter, the next revision number, never
        # an earlier known_at. A change of finding kind or reporter is a NEW
        # finding (or a retirement), never a correction of the old one.
        for row in oversight_rows:
            predecessor = row.get("predecessor_id")
            if predecessor is None:
                continue
            key = _text(row.get("id")) or "<public-oversight>"
            previous = next((item for item in oversight_rows if item.get("id") == predecessor), None)
            if previous is None:
                ctx.err("dangling_reference", key)
            elif (row.get("revision") != previous.get("revision", 0) + 1
                  or any(row.get(field) != previous.get(field) for field in ("program_id", "finding_kind", "reported_by"))
                  or (_strict_datetime(row.get("known_at")) is not None and _strict_datetime(previous.get("known_at")) is not None
                      and _strict_datetime(row["known_at"]) < _strict_datetime(previous["known_at"]))):
                ctx.err("public_oversight_succession_invalid", key)

    agreement_ids: set[str] = set()
    agreement_rows = _rows(raw, PUBLIC_AGREEMENT_COLLECTION, ctx) if agreement_enabled else []
    for row in agreement_rows:
        key = _text(row.get("id")) or "<public-agreement>"
        # D5 graph timestamps retain their canonical +00:00 spelling.
        if _strict_datetime(row.get("known_at")) is None:
            ctx.err("public_agreement_invalid_known_at", key)
        for error in agreement_payload_errors(row, evidence_index, graph_known_at=raw.get("graph_known_at")):
            ctx.err(error, key)
        if key in agreement_ids:
            ctx.err("duplicate_identity_conflict", key)
        agreement_ids.add(key)
    for row in agreement_rows:
        predecessor = row.get("predecessor_id")
        if not isinstance(predecessor, str):
            continue
        key = _text(row.get("id")) or "<public-agreement>"
        previous = next((item for item in agreement_rows if item.get("id") == predecessor), None)
        if previous is None:
            ctx.err("dangling_reference", key)
        else:
            revision = row.get("revision"); prior_revision = previous.get("revision")
            known = _strict_datetime(row.get("known_at")); prior_known = _strict_datetime(previous.get("known_at"))
            if (not isinstance(revision, int) or isinstance(revision, bool)
                    or not isinstance(prior_revision, int) or isinstance(prior_revision, bool)
                    or revision != prior_revision + 1 or row.get("source_url") != previous.get("source_url")
                    or known is None or prior_known is None or known <= prior_known):
                ctx.err("public_agreement_succession_invalid", key)
    # Multiple independent roots from the same document URL are ambiguous.
    # Corrections must name a predecessor; a retirement is explicit, immutable.
    # Visibility changes only at known_at. A future retirement must not
    # conceal an earlier interval with two independent current roots.
    boundaries = {_strict_datetime(item.get("known_at")) for item in agreement_rows + overrides}
    boundaries.discard(None)
    for cutoff in [None, *sorted(boundaries)]:
        current = current_content_addressed_rows(agreement_rows, id_key="id", analysis_as_of=cutoff,
            retired_ids=retired_row_ids(overrides, cutoff))
        urls: set[str] = set()
        for row in current:
            url = _text(row.get("source_url"))
            if url is not None and url in urls:
                ctx.err("public_agreement_multiplicity_invalid", _text(row.get("id")) or "<public-agreement>")
            if url is not None:
                urls.add(url)

    all_row_ids = (
        program_ids | capability_ids | platform_ids | role_assertion_ids
        | milestone_ids | {r.get("link_id") for r in program_capability_links if r.get("link_id")}
        | program_event_link_ids | capacity_ids | oversight_ids | agreement_ids
    )

    coverage_ids: set[str] = set()
    for row in review_coverage:
        row_id = _text(row.get("coverage_id")) or "<rev-cov>"
        key = row_id
        if row_id is None or _REV_COV_ID.fullmatch(row_id) is None:
            ctx.err("ontology_row_shape_invalid", key)
        scope = _text(row.get("scope"))
        subject_type = _text(row.get("subject_type"))
        if scope not in coverage_scopes_for(raw):
            ctx.err("ontology_row_shape_invalid", key)
        if subject_type not in coverage_subject_types_for(raw):
            ctx.err("ontology_row_shape_invalid", key)
        if scope == "public_capacity" and (subject_type != "program" or row.get("subject_id") not in program_ids):
            ctx.err("public_capacity_coverage_invalid", key)
        if (scope == "public_agreement" or subject_type == "source_evidence") and (
            not agreement_enabled or scope != "public_agreement" or subject_type != "source_evidence"
            or row.get("subject_id") not in evidence_index
        ):
            ctx.err("public_agreement_coverage_invalid", key)
        worksheet_sha = _text(row.get("worksheet_sha256"))
        if worksheet_sha is None or _SHA256.fullmatch(worksheet_sha.lower()) is None:
            ctx.err("ontology_row_shape_invalid", key)
        known_at = _strict_datetime(row.get("known_at"))
        if known_at is None:
            ctx.err("ontology_row_shape_invalid", key)
        admitted_count = row.get("admitted_count")
        if not isinstance(admitted_count, int) or isinstance(admitted_count, bool) or admitted_count < 0:
            ctx.err("ontology_row_shape_invalid", key)
        if row_id in coverage_ids:
            ctx.err("duplicate_identity_conflict", key)
        coverage_ids.add(row_id)
        if row_id and _REV_COV_ID.fullmatch(row_id) and worksheet_sha is not None and known_at is not None:
            try:
                expected = review_coverage_id(
                    scope=scope, subject_type=subject_type, subject_id=row.get("subject_id"),
                    worksheet_sha256=worksheet_sha, known_at=row.get("known_at"),
                )
            except (TypeError, ValueError):
                expected = None
            if expected is not None and expected != row_id:
                ctx.err("duplicate_identity_conflict", key)

    conflict_ids: set[str] = set()
    for row in conflicts:
        row_id = _text(row.get("conflict_id")) or "<conf>"
        key = row_id
        if row_id is None or _CONF_ID.fullmatch(row_id) is None:
            ctx.err("ontology_row_shape_invalid", key)
        if _text(row.get("scope")) not in coverage_scopes_for(raw):
            ctx.err("ontology_row_shape_invalid", key)
        if _text(row.get("subject_type")) not in coverage_subject_types_for(raw):
            ctx.err("ontology_row_shape_invalid", key)
        if (row.get("scope") == "public_agreement" or row.get("subject_type") == "source_evidence") and (
            not agreement_enabled or row.get("scope") != "public_agreement"
            or row.get("subject_type") != "source_evidence" or row.get("subject_id") not in evidence_index
        ):
            ctx.err("public_agreement_coverage_invalid", key)
        if _text(row.get("reason_code")) not in CONFLICT_REASON_ENUM:
            ctx.err("ontology_row_shape_invalid", key)
        candidates = row.get("candidate_row_ids")
        if not isinstance(candidates, list) or len(candidates) < 2:
            ctx.err("ontology_row_shape_invalid", key)
        else:
            for candidate in candidates:
                if _text(candidate) not in all_row_ids:
                    ctx.err("dangling_reference", key)
            if row.get("scope") == "public_capacity" and (
                row.get("subject_type") != "program" or row.get("subject_id") not in program_ids
                or any(not any(item.get("id") == candidate and item.get("program_id") == row.get("subject_id")
                               for item in raw.get(PUBLIC_CAPACITY_COLLECTION, [])) for candidate in candidates)
            ):
                ctx.err("public_capacity_conflict_invalid", key)
            if row.get("scope") == "public_oversight" and (
                row.get("subject_type") != "program" or row.get("subject_id") not in program_ids
                or any(not any(item.get("id") == candidate and item.get("program_id") == row.get("subject_id")
                               for item in raw.get(PUBLIC_OVERSIGHT_COLLECTION, [])) for candidate in candidates)
            ):
                ctx.err("public_oversight_conflict_invalid", key)
        if row.get("verification_state") not in REVIEW_STATES:
            ctx.err("ontology_row_shape_invalid", key)
        _validate_temporal_claim(
            row, ctx=ctx, row_id=key, evidence_index=evidence_index,
            graph_known_at=graph_known_at, graph_effective_at=graph_effective_at,
        )
        if row_id in conflict_ids:
            ctx.err("duplicate_identity_conflict", key)
        conflict_ids.add(row_id)
        if row_id and _CONF_ID.fullmatch(row_id) and isinstance(candidates, list) and candidates:
            try:
                expected = conflict_id(
                    scope=row.get("scope"), subject_type=row.get("subject_type"),
                    subject_id=row.get("subject_id"), candidate_row_ids=candidates,
                    known_at=row.get("known_at"),
                )
            except (TypeError, ValueError):
                expected = None
            if expected is not None and expected != row_id:
                ctx.err("duplicate_identity_conflict", key)

    override_ids: set[str] = set()
    for row in overrides:
        row_id = _text(row.get("override_id")) or "<ovr>"
        key = row_id
        if row_id is None or _OVR_ID.fullmatch(row_id) is None:
            ctx.err("ontology_row_shape_invalid", key)
        action = _text(row.get("action"))
        if action not in OVERRIDE_ACTION_ENUM:
            ctx.err("ontology_row_shape_invalid", key)
        target_row_id = _text(row.get("target_row_id"))
        subject_type = _text(row.get("subject_type"))
        subject_id = _text(row.get("subject_id"))
        if action == "retire_row":
            if target_row_id is None or (
                target_row_id not in all_row_ids and target_row_id not in conflict_ids
            ):
                ctx.err("dangling_reference", key)
        if action == "block":
            if subject_type not in coverage_subject_types_for(raw) or subject_id is None:
                ctx.err("ontology_row_shape_invalid", key)
        if subject_type == "source_evidence" and (not agreement_enabled or subject_id not in evidence_index):
            ctx.err("public_agreement_coverage_invalid", key)
        if row.get("verification_state") not in REVIEW_STATES:
            ctx.err("ontology_row_shape_invalid", key)
        _validate_temporal_claim(
            row, ctx=ctx, row_id=key, evidence_index=evidence_index,
            graph_known_at=graph_known_at, graph_effective_at=graph_effective_at,
        )
        if row_id in override_ids:
            ctx.err("duplicate_identity_conflict", key)
        override_ids.add(row_id)
        if row_id and _OVR_ID.fullmatch(row_id):
            try:
                expected = override_id(
                    action=action, target_row_id=target_row_id, subject_type=subject_type,
                    subject_id=subject_id, known_at=row.get("known_at"),
                )
            except (TypeError, ValueError):
                expected = None
            if expected is not None and expected != row_id:
                ctx.err("duplicate_identity_conflict", key)

    # Link multiplicity invariants (mirrors the curate-time invariant,
    # fail-closed against a hand-edited artifact -- freeze SS3.1). A subject
    # with >=2 current links is refused UNLESS a current conflicts[] row
    # already declares it conflicted -- that is the legal "declared conflict"
    # state, not a certification defect.
    conflicted_capability_subjects = {
        row.get("subject_id") for row in conflicts
        if row.get("scope") == "capability" and row.get("subject_type") == "program"
        and _text(row.get("conflict_id")) not in override_targets_of(overrides)
    }
    conflicted_event_subjects = {
        row.get("subject_id") for row in conflicts
        if row.get("scope") == "program_event_link" and row.get("subject_type") == "award_event"
        and _text(row.get("conflict_id")) not in override_targets_of(overrides)
    }
    retired_link_ids = override_targets_of(overrides)
    _check_link_multiplicity(
        program_capability_links, key_fn=lambda r: r.get("program_id"),
        exempt_subjects=conflicted_capability_subjects, retired_ids=retired_link_ids, ctx=ctx,
    )
    _check_link_multiplicity(
        program_event_links, key_fn=lambda r: r.get("event_id"),
        exempt_subjects=conflicted_event_subjects, retired_ids=retired_link_ids, ctx=ctx,
    )

    ctx.raise_if_any()

    normalized = {key: raw[key] for key in top_level_keys}
    return normalized


def _row_evidence_scopes(
    row: Mapping[str, Any], evidence_index: Mapping[str, Mapping[str, Any]],
) -> set[str]:
    scopes: set[str] = set()
    for ref in row.get("evidence_refs") or []:
        source = evidence_index.get(_text(ref) or "")
        if source is not None:
            scopes |= set(source.get("claim_scopes", []))
    return scopes


def _register_logical_row(
    by_id_rev: dict[tuple[str, int], dict[str, Any]], key: tuple[str, int],
    row: dict[str, Any], *, ctx: _Ctx, row_key: str,
) -> None:
    """Logical kinds are unique on (id, revision) (freeze SS5): a byte-
    identical resubmission dedupes idempotently; two rows sharing the key
    with DIFFERING bytes refuse certification `duplicate_identity_conflict`.
    Must run BEFORE any dict collapse -- collapsing first (a plain
    ``dict[key] = row`` overwrite) makes the second row's bytes
    unobservable and the check a permanent no-op."""
    existing = by_id_rev.get(key)
    if existing is not None and existing != row:
        ctx.err("duplicate_identity_conflict", row_key)
        return
    by_id_rev[key] = row


def _current_link_ids(
    rows: Sequence[Mapping[str, Any]], *, retired_ids: set[str] = frozenset(),
) -> set[str]:
    """A row is CURRENT (freeze SS5) iff no visible row names it in
    predecessor_id AND it is not targeted by a `retire_row` override.
    Load-time structural check: certification has no `analysis_as_of` of its
    own, so this reads every row/override the artifact carries (a load-time
    certification is not itself point-in-time; PIT filtering is the
    derivation layer's job, see `current_content_addressed_rows`)."""
    predecessors = {_text(r.get("predecessor_id")) for r in rows if r.get("predecessor_id")}
    id_key = "link_id" if rows and "link_id" in rows[0] else "id"
    return {
        _text(r.get(id_key)) for r in rows
        if _text(r.get(id_key)) not in predecessors and _text(r.get(id_key)) not in retired_ids
    }


def override_targets_of(overrides: Sequence[Mapping[str, Any]]) -> set[str]:
    """Every ``target_row_id`` named by a `retire_row` override, irrespective
    of visibility (used for load-time structural checks that are not
    themselves point-in-time)."""
    return {
        _text(r.get("target_row_id"))
        for r in overrides
        if r.get("action") == "retire_row" and _text(r.get("target_row_id"))
    }


def _check_link_multiplicity(
    rows: Sequence[Mapping[str, Any]], *, key_fn: Any, exempt_subjects: set[Any],
    retired_ids: set[str], ctx: _Ctx,
) -> None:
    if not rows:
        return
    current_ids = _current_link_ids(rows, retired_ids=retired_ids)
    by_subject: dict[str, list[str]] = defaultdict(list)
    id_key = "link_id"
    for row in rows:
        row_id = _text(row.get(id_key))
        if row_id in current_ids:
            by_subject[key_fn(row)].append(row_id)
    for subject, ids in by_subject.items():
        if len(ids) >= 2 and subject not in exempt_subjects:
            ctx.err("link_multiplicity_invalid", subject or "<unknown-subject>")


# ---------------------------------------------------------------------------
# Derivation layer -- currency, revision resolution, review-coverage state,
# conflict lookup, and the workspace `program_link` field (freeze SS3.1b/
# SS3.1c/SS4/SS5). Consumed by engine/government_revenue/program_dossier.py
# and the `program_link` wiring in engine/government_revenue/workspace.py.
# ---------------------------------------------------------------------------


def visible_rows(rows: Sequence[Mapping[str, Any]], analysis_as_of: datetime | None) -> list[dict[str, Any]]:
    """Rows whose `known_at` is at or before `analysis_as_of` (None = no filter)."""
    if analysis_as_of is None:
        return [dict(r) for r in rows]
    out = []
    for row in rows:
        known_at = _strict_datetime(row.get("known_at"))
        if known_at is not None and known_at <= analysis_as_of:
            out.append(dict(row))
    return out


def retired_row_ids(overrides: Sequence[Mapping[str, Any]], analysis_as_of: datetime | None) -> set[str]:
    """Ids targeted by a visible `retire_row` override (freeze SS5)."""
    out: set[str] = set()
    for row in visible_rows(overrides, analysis_as_of):
        if row.get("action") == "retire_row":
            target = _text(row.get("target_row_id"))
            if target:
                out.add(target)
    return out


def current_identities(
    rows: Sequence[Mapping[str, Any]], *, id_key: str, analysis_as_of: datetime | None, retired_ids: set[str],
) -> set[str]:
    """Current LOGICAL identities (freeze SS5): visible, not named as a
    predecessor by any visible row of the same collection, not retired.
    Distinct from row-level currency: a plain rename leaves BOTH revisions
    of one id visible and current -- only an identity-break (a DIFFERENT id
    naming this one in `predecessor_id`) or a `retire_row` override on the
    identity removes it.
    """
    vis = visible_rows(rows, analysis_as_of)
    predecessor_ids = {_text(r.get("predecessor_id")) for r in vis if r.get("predecessor_id")}
    ids = {_text(r.get(id_key)) for r in vis}
    return {i for i in ids if i and i not in predecessor_ids and i not in retired_ids}


def current_content_addressed_rows(
    rows: Sequence[Mapping[str, Any]], *, id_key: str, analysis_as_of: datetime | None, retired_ids: set[str],
) -> list[dict[str, Any]]:
    """Current rows of a content-addressed collection (each row is its own
    identity; a successor names the exact predecessor row id)."""
    vis = visible_rows(rows, analysis_as_of)
    predecessor_ids = {_text(r.get("predecessor_id")) for r in vis if r.get("predecessor_id")}
    return [
        r for r in vis
        if _text(r.get(id_key)) not in predecessor_ids and _text(r.get(id_key)) not in retired_ids
    ]


def coverage_subject_types_for(graph: Mapping[str, Any]) -> frozenset[str]:
    """Documentary coverage refers to an existing evidence ID, not a programme."""
    if graph.get("schema_version") == PUBLIC_AGREEMENT_VERSION:
        return COVERAGE_SUBJECT_TYPE_ENUM | {"source_evidence"}
    return COVERAGE_SUBJECT_TYPE_ENUM


def current_public_agreement_rows(
    graph: Mapping[str, Any], *, analysis_as_of: datetime | None,
) -> list[dict[str, Any]]:
    """Cutoff-visible documentary observations, never programme/issuer attribution."""
    if graph.get("schema_version") != PUBLIC_AGREEMENT_VERSION:
        return []
    overrides = visible_rows(graph.get("overrides") or [], analysis_as_of)
    blocked = {row.get("subject_id") for row in overrides
               if row.get("action") == "block" and row.get("subject_type") == "source_evidence"}
    rows = current_content_addressed_rows(graph.get(PUBLIC_AGREEMENT_COLLECTION) or [], id_key="id",
        analysis_as_of=analysis_as_of, retired_ids=retired_row_ids(overrides, analysis_as_of))
    return [row for row in rows if row.get("verification_state") == "reviewed"
            and not blocked.intersection(row.get("evidence_refs") or [])]


def current_public_capacity_rows(
    graph: Mapping[str, Any], program_id: str, *, analysis_as_of: datetime | None,
) -> list[dict[str, Any]]:
    """Literal public observations, never totals, utilization or readiness estimates."""
    if graph.get("schema_version") not in (PUBLIC_CAPACITY_VERSION, PUBLIC_OVERSIGHT_VERSION, PUBLIC_AGREEMENT_VERSION):
        return []
    if any(row.get("action") == "block" and row.get("subject_type") == "program"
           and row.get("subject_id") == program_id
           for row in visible_rows(graph.get("overrides") or [], analysis_as_of)):
        return []
    retired = retired_row_ids(graph.get("overrides") or [], analysis_as_of)
    if program_id not in current_identities(graph.get("programs") or [], id_key="id",
                                            analysis_as_of=analysis_as_of, retired_ids=retired):
        return []
    cutoff = analysis_as_of or _strict_datetime(graph.get("graph_effective_at"))
    rows = current_content_addressed_rows(graph.get(PUBLIC_CAPACITY_COLLECTION) or [],
        id_key="id", analysis_as_of=analysis_as_of, retired_ids=retired)
    return [row for row in rows if row.get("program_id") == program_id
            and row.get("verification_state") in REVIEW_STATES
            and _strict_datetime(row["valid_from"]) <= cutoff
            and (row.get("valid_to") is None or cutoff < _strict_datetime(row["valid_to"]))]


def current_public_oversight_rows(
    graph: Mapping[str, Any], program_id: str, *, analysis_as_of: datetime | None,
) -> list[dict[str, Any]]:
    """Cutoff-visible, current, unretired oversight findings for one program.

    Quoted, source-attributed observations only: the report edition and its
    publication date travel with the row as source METADATA; currency here is
    decided solely by the row's own known_at/valid_from/valid_to claim clocks,
    exactly like every other content-addressed rail."""
    if graph.get("schema_version") not in (PUBLIC_OVERSIGHT_VERSION, PUBLIC_AGREEMENT_VERSION):
        return []
    if any(row.get("action") == "block" and row.get("subject_type") == "program"
           and row.get("subject_id") == program_id
           for row in visible_rows(graph.get("overrides") or [], analysis_as_of)):
        return []
    retired = retired_row_ids(graph.get("overrides") or [], analysis_as_of)
    if program_id not in current_identities(graph.get("programs") or [], id_key="id",
                                            analysis_as_of=analysis_as_of, retired_ids=retired):
        return []
    cutoff = analysis_as_of or _strict_datetime(graph.get("graph_effective_at"))
    rows = current_content_addressed_rows(graph.get(PUBLIC_OVERSIGHT_COLLECTION) or [],
        id_key="id", analysis_as_of=analysis_as_of, retired_ids=retired)
    return [row for row in rows if row.get("program_id") == program_id
            and row.get("verification_state") in REVIEW_STATES
            and _strict_datetime(row["valid_from"]) <= cutoff
            and (row.get("valid_to") is None or cutoff < _strict_datetime(row["valid_to"]))]


def resolve_revision(
    rows_for_id: Sequence[Mapping[str, Any]], *, at: datetime, fallback_latest_visible: bool = True,
) -> dict[str, Any] | None:
    """Latest known revision whose `[valid_from, valid_to)` validity covers `at`.

    Falls back to the latest VISIBLE revision when none covers `at` (identity
    attributes outlive validity close-out, freeze SS4's capability-rail rule,
    applied generically).
    """
    covering: list[tuple[datetime, dict[str, Any]]] = []
    for row in rows_for_id:
        valid_from = _strict_datetime(row.get("valid_from"))
        valid_to_raw = row.get("valid_to")
        valid_to = None if valid_to_raw is None else _strict_datetime(valid_to_raw)
        if valid_from is not None and valid_from <= at and (valid_to is None or at < valid_to):
            covering.append((valid_from, dict(row)))
    if covering:
        covering.sort(key=lambda pair: (pair[0], pair[1].get("revision") or 0))
        return covering[-1][1]
    if not fallback_latest_visible:
        return None
    known_rows = [
        (kn, dict(row)) for row in rows_for_id
        if (kn := _strict_datetime(row.get("known_at"))) is not None
    ]
    if not known_rows:
        return None
    known_rows.sort(key=lambda pair: (pair[0], pair[1].get("revision") or 0))
    return known_rows[-1][1]


def current_program_capability_link(
    graph: Mapping[str, Any], program_id: str, *, analysis_as_of: datetime | None,
) -> dict[str, Any] | None:
    retired = retired_row_ids(graph.get("overrides") or [], analysis_as_of)
    current = current_content_addressed_rows(
        graph.get("program_capability_links") or [], id_key="link_id",
        analysis_as_of=analysis_as_of, retired_ids=retired,
    )
    matches = [r for r in current if r.get("program_id") == program_id]
    return matches[0] if len(matches) == 1 else None


def current_conflict_for(
    graph: Mapping[str, Any], *, scope: str, subject_type: str, subject_id: str, analysis_as_of: datetime | None,
) -> dict[str, Any] | None:
    """The CURRENT (visible, not retired) `conflicts[]` row for a scope+subject, if any."""
    retired = retired_row_ids(graph.get("overrides") or [], analysis_as_of)
    for row in visible_rows(graph.get("conflicts") or [], analysis_as_of):
        if (
            row.get("scope") == scope
            and row.get("subject_type") == subject_type
            and row.get("subject_id") == subject_id
            and _text(row.get("conflict_id")) not in retired
        ):
            return dict(row)
    return None


def derive_review_coverage(
    graph: Mapping[str, Any], *, scope: str, subject_type: str, subject_id: str, analysis_as_of: datetime | None,
) -> tuple[str, str | None]:
    """The freeze SS3.1c four-branch derivation law. Returns `(state, known_at_iso)`.

    Purely a function of the artifact's own rows -- no worksheet, no research
    prose. `known_at_iso` is populated only for `reviewed_none` (the LATEST
    visible covering coverage row's `known_at`); `None` otherwise.
    """
    if scope in ("public_capacity", "public_oversight", "public_agreement") and any(
        row.get("action") == "block" and row.get("subject_type") == subject_type
        and row.get("subject_id") == subject_id
        for row in visible_rows(graph.get("overrides") or [], analysis_as_of)
    ):
        return "not_reviewed", None
    conflict = current_conflict_for(
        graph, scope=scope, subject_type=subject_type, subject_id=subject_id, analysis_as_of=analysis_as_of,
    )
    if conflict is not None:
        return "conflicted", None

    admitted = _admitted_current_count(
        graph, scope=scope, subject_type=subject_type, subject_id=subject_id, analysis_as_of=analysis_as_of,
    )
    if admitted > 0:
        return "reviewed", None

    covering = [
        row for row in visible_rows(graph.get("review_coverage") or [], analysis_as_of)
        if row.get("scope") == scope and row.get("subject_type") == subject_type and row.get("subject_id") == subject_id
    ]
    if covering:
        covering.sort(key=lambda r: _strict_datetime(r.get("known_at")) or datetime.min.replace(tzinfo=timezone.utc))
        return "reviewed_none", covering[-1].get("known_at")
    return "not_reviewed", None


def _admitted_current_count(
    graph: Mapping[str, Any], *, scope: str, subject_type: str, subject_id: str, analysis_as_of: datetime | None,
) -> int:
    retired = retired_row_ids(graph.get("overrides") or [], analysis_as_of)
    if scope == "public_agreement" and subject_type == "source_evidence":
        return sum(subject_id in row["evidence_refs"] for row in current_public_agreement_rows(graph, analysis_as_of=analysis_as_of))
    if scope == "public_capacity" and subject_type == "program":
        return len(current_public_capacity_rows(graph, subject_id, analysis_as_of=analysis_as_of))
    if scope == "public_oversight" and subject_type == "program":
        return len(current_public_oversight_rows(graph, subject_id, analysis_as_of=analysis_as_of))
    if scope == "program_identity" and subject_type == "program":
        current = current_identities(
            graph.get("programs") or [], id_key="id", analysis_as_of=analysis_as_of, retired_ids=retired,
        )
        return 1 if subject_id in current else 0
    if scope == "capability" and subject_type == "program":
        link = current_program_capability_link(graph, subject_id, analysis_as_of=analysis_as_of)
        return 1 if link is not None else 0
    if scope == "participants" and subject_type == "program":
        current = current_content_addressed_rows(
            graph.get("role_assertions") or [], id_key="id", analysis_as_of=analysis_as_of, retired_ids=retired,
        )
        return sum(1 for r in current if r.get("program_id") == subject_id)
    if scope == "milestones" and subject_type == "program":
        current = current_content_addressed_rows(
            graph.get("milestones") or [], id_key="id", analysis_as_of=analysis_as_of, retired_ids=retired,
        )
        return sum(1 for r in current if r.get("program_id") == subject_id)
    if scope == "program_event_link":
        current = current_content_addressed_rows(
            graph.get("program_event_links") or [], id_key="link_id", analysis_as_of=analysis_as_of, retired_ids=retired,
        )
        if subject_type == "award_event":
            return sum(1 for r in current if r.get("event_id") == subject_id)
        if subject_type == "program":
            return sum(1 for r in current if r.get("program_id") == subject_id)
    return 0


#: freeze SS4 -- the program rail's own reason code; NEVER the atlas's
#: `no_reviewed_exact_path` (its bound copy is recipient-identity prose).
PROGRAM_LINK_REASON_NO_REVIEWED_LINK = "no_reviewed_program_link"
ONTOLOGY_UNAVAILABLE_REASON = "ontology_unavailable"


def derive_workspace_program_link(
    graph: Mapping[str, Any] | None, *, event_id: str, analysis_as_of: datetime | None, graph_id: str | None,
) -> dict[str, Any]:
    """The workspace award view's `program_link` field -- exactly five keys,
    exactly the freeze SS4 shapes. `graph` is the LOADED (certified) ontology,
    or `None` when the artifact is absent/uncertified (the fourth shape)."""
    if graph is None:
        return {
            "state": "source_unavailable",
            "reason_code": ONTOLOGY_UNAVAILABLE_REASON,
            "program_id": None,
            "program_event_link_id": None,
            "ontology_graph_id": None,
        }
    current_graph_id = graph.get("graph_id")
    conflict = current_conflict_for(
        graph, scope="program_event_link", subject_type="award_event", subject_id=event_id,
        analysis_as_of=analysis_as_of,
    )
    if conflict is not None:
        return {
            "state": "conflicted",
            "reason_code": None,
            "program_id": None,
            "program_event_link_id": None,
            "ontology_graph_id": current_graph_id,
        }
    retired = retired_row_ids(graph.get("overrides") or [], analysis_as_of)
    current_links = current_content_addressed_rows(
        graph.get("program_event_links") or [], id_key="link_id", analysis_as_of=analysis_as_of, retired_ids=retired,
    )
    matches = [r for r in current_links if r.get("event_id") == event_id]
    if len(matches) == 1:
        link = matches[0]
        return {
            "state": "reviewed",
            "reason_code": None,
            "program_id": link.get("program_id"),
            "program_event_link_id": link.get("link_id"),
            "ontology_graph_id": current_graph_id,
        }
    state, _known_at = derive_review_coverage(
        graph, scope="program_event_link", subject_type="award_event", subject_id=event_id,
        analysis_as_of=analysis_as_of,
    )
    # `reviewed` cannot reach here (already handled above via current_links);
    # only `not_reviewed` / `reviewed_none` are possible outcomes left.
    return {
        "state": state if state in ("not_reviewed", "reviewed_none") else "not_reviewed",
        "reason_code": PROGRAM_LINK_REASON_NO_REVIEWED_LINK,
        "program_id": None,
        "program_event_link_id": None,
        "ontology_graph_id": current_graph_id,
    }


#: Public aliases for the strict D5 timestamp/date parsers -- used by
#: engine/government_revenue/program_dossier.py and the test battery.
strict_datetime = _strict_datetime
full_date = _full_date


event_hash_agrees = _event_hash_agrees


def load_program_ontology_graph_or_none(
    raw: Mapping[str, Any] | None,
    *,
    workspace_events: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Load, catching :class:`OntologyInputError` into `None` (freeze SS4:
    consumers treat absence and refused certification identically -- the
    typed unavailable form, never a crash)."""
    try:
        return load_program_ontology_graph(raw, workspace_events=workspace_events)
    except OntologyInputError:
        return None


__all__ = [
    "AUTHORITY",
    "CONTRACT",
    "SCHEMA_VERSION",
    "WORKSHEET_CONTRACT",
    "WORKSHEET_SCHEMA_VERSION",
    "EVENT_CONTRACT",
    "TOP_LEVEL_KEYS",
    "OntologyInputError",
    "FORBIDDEN_INPUT_KEYS",
    "FORBIDDEN_ASSOCIATION_METHODS",
    "PROPOSED_STATE",
    "REVIEW_STATES",
    "sha12",
    "role_assertion_id",
    "milestone_id",
    "program_capability_link_id",
    "program_event_link_id",
    "review_coverage_id",
    "conflict_id",
    "override_id",
    "evidence_id_for_sha256",
    "public_oversight_assertion_id",
    "public_oversight_excerpt_sha256",
    "load_program_ontology_graph",
    "load_program_ontology_graph_or_none",
    "visible_rows",
    "retired_row_ids",
    "current_identities",
    "current_content_addressed_rows",
    "resolve_revision",
    "current_program_capability_link",
    "current_public_oversight_rows",
    "current_conflict_for",
    "derive_review_coverage",
    "derive_workspace_program_link",
    "PROGRAM_LINK_REASON_NO_REVIEWED_LINK",
    "ONTOLOGY_UNAVAILABLE_REASON",
    "analysis_as_of",
    "strict_datetime",
    "full_date",
    "canonical_award_identity_comparand",
    "event_hash_agrees",
]
