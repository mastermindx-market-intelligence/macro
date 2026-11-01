"""Prophet news-impact adapter — the one context-only seam into Prophet.

Implements masterplan section 12 (Phase 4 evidence adapter; Phase 5 promotion
is out of scope) and section 14 (news-impact facts may not rank, size, or
gate), under PHASE0_FREEZE_2026-10-11.md D12 (``cik:`` + 10 identity), D16
(envelope / corrections), D17 (injection is data, quarantine stays outside
publishable templates), and seat rulings R1/R2/R4 (display projection and
closed locators). Design packet A7 section 4 is the frozen spec; section 7
Q1 is overridden by W3-R7: this module is a PURE LEAF. It emits
``prophet_evidence.v1`` records and a ``facet`` assembler a later wiring PR
may call. It does not patch, import, or call any Prophet consumer.

No confidence / probability / score / price_target / fair_value / sentiment
/ contagion field is defined or passed through. ``as_of`` is always derived
from the fact's ``source_available_at`` (I10); there is no clock read, no
network, no model call, and no module-level I/O.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

from engine.news_impact.validate import project_display

SCHEMA_NAME = "prophet_evidence.v1"
BUNDLE_SCHEMA_NAME = "prophet_evidence_bundle.v1"
AUTHORITY = "context_only"
STANCE_KEY = "stance_heads_up"
ADAPTER_VERSION = "ni-prophet-adapter-2"
# news_impact_event.v1 quantity_range carries no bound; display_quantity requires one.
RANGE_BOUND = "exact"

CODES = frozenset({
    "AUTHORITY_NOT_CONTEXT_ONLY",
    "PROPHET_FLAG_TRUE",
    "UNSOLICITED_INSTRUCTION",
    "FORBIDDEN_FIELD",
    "locator_key_not_in_contract",
    "CORRECTED_FACT_MISSING_SUPERSEDES",
    "UNKNOWN_TEMPLATE",
    "INVALID_COMPANY_ID",
    "MISSING_REQUIRED_FIELD",
    "TEXT_UNSAFE",
    "TRANSFER_NOT_ONE_HOP",
    "TRANSFER_EXPOSURE_NOT_UNKNOWN",
    "ROLLOUT_GATE_CLOSED",
    "QUARANTINE_REFUSED",
    "DOCUMENT_VERSION_MINIMUM",
    "SLOT_TOO_LONG",
    "COPY_KEY_MISSING",
    "SCHEMA_VIOLATION",
    "CHANNEL_INVALID",
    "UNSOLICITED_MUST_BE_FALSE",
})

FORBIDDEN_NAMES = frozenset({
    "confidence", "probability", "score", "sentiment_score", "sentiment_strength",
    "quality", "quality_score", "weighted_score", "signal_score", "convergence_score",
    "priority", "strength", "lean", "conviction", "rating", "rank", "weight",
    "alpha", "percentile", "z_score", "t_stat", "ic", "price_target", "fair_value",
    "fair value", "target", "expected_move", "bullishness", "rerating", "contagion",
    "falsifier", "refutation", "prophet_score", "prophet_rank", "entry_authority",
    "trade_authority", "sizing_authority", "can_gate", "can_rank", "can_size",
    "sentiment",
})
FLAG_KEYS = frozenset({"may_rank", "may_size", "may_gate", "prophet_authority"})

CROSS_FIELDS = frozenset({
    "schema", "authority", "prophet_flags", "unsolicited_instruction_detected",
    "fact_id", "document_id", "observed_at", "source_available_at", "supersedes_fact_id",
    "company_id", "issuer_role", "novelty", "commitment_status", "negated",
    "channel_hint", "cluster_grain", "action_type", "primary_amount_role",
    "incremental_amount", "remaining_authorization", "executed_amount",
    "horizon_period", "action_span", "demand_stage", "metric", "revision_direction",
    "stated_amount", "prior_amount", "fiscal_period", "counterparty_company_id",
    "event_kind", "object_name", "counterparty_role", "economic_claim_class",
    "stated_quantity", "record_kind", "listing_join", "absence", "channel",
    "kind", "thesis_id", "supporting_fact_ids", "contrary_fact_ids",
    "next_observation_key", "deadline_date", "watching_key", "supporting_claim_ids",
    "contrary_claim_ids", "source_company_id", "target_company_id", "target_role",
    "direction", "mechanism_channel", "exposure", "one_hop", "edge_span",
    "display_state", "as_of", "owner_reason", "reason", "subject", "detail",
    "missing_fields", "template_schema", "issuer_role",
})
HOVER_ONLY_FIELDS = frozenset({
    "contrary_mechanism_quote", "conditions_quote", "consideration_quote",
    "license_quote", "baseline",
})
ALWAYS_DROP = frozenset({
    "option_ceiling", "adoption_proxy_quote", "news_event_class",
    "quarantine_note", "routing_label",
})
QUANTITY_INTERNAL = frozenset({"period", "negated", "evidence"})

TEMPLATE_SCHEMAS = (
    "capital_allocation_event.v1",
    "demand_guidance_contract_event.v1",
    "strategic_product_partnership_event.v1",
)
TEMPLATE_CHANNEL_DEFAULT = {
    "capital_allocation_event.v1": "capital_allocation",
    "demand_guidance_contract_event.v1": "revenue_demand",
    "strategic_product_partnership_event.v1": "strategic_option",
}
CHANNELS = frozenset({
    "revenue_demand", "margin_cost", "capital_allocation", "moat_duration",
    "strategic_option", "financial_incentives_survival", "market_only",
})
T1_QUANTITY_SLOTS = (
    "incremental_amount", "remaining_authorization", "executed_amount",
)
T2_QUANTITY_SLOTS = ("stated_amount",)
T3_QUANTITY_SLOTS = ("stated_quantity",)
TEMPLATE_SLOT_KEYS = {
    "T1_authorization": (
        "action_plain", "status_plain", "amount_plain", "remaining_plain", "window_plain",
    ),
    "T1_execution": ("action_plain", "status_plain", "amount_plain", "window_plain"),
    "T1_no_change": ("action_plain", "amount_plain"),
    "T2_guidance": ("metric_plain", "revision_plain", "amount_plain", "window_plain"),
    "T2_contract": ("status_plain", "amount_plain", "window_plain"),
    "T2_no_change": ("metric_plain", "amount_plain"),
    "T3_option": ("event_plain", "object_plain", "window_plain"),
    "T3_milestone": ("event_plain", "object_plain", "status_plain", "window_plain"),
    "T3_no_change": ("object_plain",),
    "ABSENCE_defer": (),
    "ABSENCE_rights": (),
    "SUPERSEDED": ("amount_plain", "prior_amount_plain", "window_plain"),
}
SLOT_MAX = {
    "action_plain": 40, "amount_plain": 48, "remaining_plain": 48, "window_plain": 40,
    "status_plain": 32, "metric_plain": 32, "revision_plain": 32, "object_plain": 48,
    "event_plain": 40, "prior_amount_plain": 48,
}
LOCATOR_KEYS = {
    "text_span": frozenset({
        "kind", "sub_kind", "segment_index", "span_start_byte", "span_end_byte",
    }),
    "table_cell": frozenset({
        "kind", "page", "table", "row", "column", "cell_ref", "note",
    }),
    "slide_region": frozenset({"kind", "page", "region", "note"}),
}
LOCATOR_REQUIRED = {
    "text_span": frozenset({
        "kind", "sub_kind", "segment_index", "span_start_byte", "span_end_byte",
    }),
}
COMPANY_ID_RE = re.compile(r"^cik:(?!0{10}$)[0-9]{10}$")
FACT_ID_RE = re.compile(r"^fact_[0-9a-f]{24}$")
THESIS_ID_RE = re.compile(r"^thesis_[0-9a-f]{24}$")
TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,14}$")
COPY_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{2,62}$")
URL_RE = re.compile(r"(?i)\b(https?|ftps?|wss?|file|javascript|vbscript|gopher|hxxps?|hxtp)\s*:")
INJECTION_RE = re.compile(
    r"(?i)(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+|every\s+)?"
    r"(previous|prior|above|preceding|earlier)|you\s+are\s+now|"
    r"set\s+(may_rank|may_size|may_gate|prophet_authority)|system\s*prompt"
)
ROLLOUT_CHECKS = (
    "validator_chokepoint",
    "eval_receipt",
    "labeling_agreement",
    "consumer_isolation",
    "contract_freeze_intact",
    "rights",
)
_STATE_ORDER = {
    "current": 0,
    "not_yet_quantifiable": 1,
    "no_change": 2,
    "deferred": 3,
    "rights_restricted": 3,
    "absence": 3,
    "superseded": 4,
}
CONTRARY_LABEL_EN = "what could go the other way"
CONTRARY_LABEL_ZH = "另一方向的可能"
FALSE_FLAGS = {
    "may_rank": False,
    "may_size": False,
    "may_gate": False,
    "prophet_authority": False,
}


class ProphetAdapterError(Exception):
    """Refuse to emit. ``code`` is a member of :data:`CODES`."""

    def __init__(self, code: str, message: str = "") -> None:
        if code not in CODES:
            raise ValueError(f"adapter code not in CODES: {code!r}")
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class ProphetEvidence:
    """One closed ``prophet_evidence.v1`` record plus adapter metadata.

    Metadata (``stripped_fields``, ``channel_source``, ``hover``, ``slots_zh``,
    ``injection_findings``) never crosses into :meth:`to_dict`.
    """

    payload: dict[str, Any]
    stripped_fields: tuple[str, ...] = ()
    channel_source: str = "channel_hint"
    hover: tuple[dict[str, str], ...] = ()
    slots_zh: dict[str, str] = field(default_factory=dict)
    injection_findings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """JSON-compatible dict of the closed record (no adapter metadata)."""
        return copy.deepcopy(self.payload)


@dataclass(frozen=True)
class NewsImpactFacet:
    """Assembler output a later wiring PR may attach as an unblended facet."""

    bundle: dict[str, Any]
    by_ticker: dict[str, tuple[dict[str, Any], ...]]
    unresolved_cik: dict[str, tuple[dict[str, Any], ...]]
    n_news_impact: int
    news_impact_schema: str = SCHEMA_NAME

    def to_dict(self) -> dict[str, Any]:
        """JSON-compatible facet mapping (bundle + ticker / unresolved index)."""
        return {
            "bundle": copy.deepcopy(self.bundle),
            "by_ticker": {k: list(v) for k, v in sorted(self.by_ticker.items())},
            "_unresolved_cik": {
                k: list(v) for k, v in sorted(self.unresolved_cik.items())
            },
            "n_news_impact": self.n_news_impact,
            "news_impact_schema": self.news_impact_schema,
        }


@dataclass(frozen=True)
class RolloutGate:
    """Section 4.8 rollout gate: adapter-on iff every injected check is true."""

    checks: dict[str, bool]
    is_open: bool
    failed: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """JSON-compatible gate record."""
        return {
            "is_open": self.is_open,
            "failed": list(self.failed),
            "checks": {k: self.checks[k] for k in ROLLOUT_CHECKS},
        }


def canonical_json(obj: Any) -> str:
    """Canonical JSON: sorted keys, compact separators, keep non-ascii."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _schema_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "contracts" / "news_impact"


def load_prophet_schema(path: Path | str | None = None) -> dict[str, Any]:
    """Load ``prophet_evidence.v1.schema.json`` (lazy; no module-level I/O)."""
    p = Path(path) if path is not None else _schema_dir() / "prophet_evidence.v1.schema.json"
    return json.loads(p.read_text(encoding="utf-8"))


def load_copy_templates(path: Path | str | None = None) -> dict[str, Any]:
    """Load ``copy_templates.v1.json`` (lazy; no module-level I/O)."""
    p = Path(path) if path is not None else _schema_dir() / "copy_templates.v1.json"
    return json.loads(p.read_text(encoding="utf-8"))


def load_channel_mapping_schema(path: Path | str | None = None) -> dict[str, Any]:
    """Load ``channel_mapping.v1.schema.json`` (lazy; no module-level I/O)."""
    p = Path(path) if path is not None else _schema_dir() / "channel_mapping.v1.schema.json"
    return json.loads(p.read_text(encoding="utf-8"))


def load_transfer_edge_schema(path: Path | str | None = None) -> dict[str, Any]:
    """Load ``transfer_edge.v1.schema.json`` (lazy; no module-level I/O)."""
    p = Path(path) if path is not None else _schema_dir() / "transfer_edge.v1.schema.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _record_validator(schema: Mapping[str, Any] | None = None) -> Draft202012Validator:
    root = dict(schema if schema is not None else load_prophet_schema())
    defs = root.get("$defs", {})
    doc = {
        "$schema": root.get("$schema", "https://json-schema.org/draft/2020-12/schema"),
        "$defs": defs,
        "$ref": "#/$defs/prophet_evidence.v1",
    }
    return Draft202012Validator(doc)


def _bundle_validator(schema: Mapping[str, Any] | None = None) -> Draft202012Validator:
    root = dict(schema if schema is not None else load_prophet_schema())
    defs = root.get("$defs", {})
    doc = {
        "$schema": root.get("$schema", "https://json-schema.org/draft/2020-12/schema"),
        "$defs": defs,
        "$ref": "#/$defs/prophet_evidence_bundle.v1",
    }
    return Draft202012Validator(doc)


def _text_safe_validator(schema: Mapping[str, Any] | None = None) -> Draft202012Validator:
    root = dict(schema if schema is not None else load_prophet_schema())
    return Draft202012Validator({"$ref": "#/$defs/text_safe", "$defs": root["$defs"]})


def _require_text_safe(value: str, *, path: str, schema: Mapping[str, Any] | None = None) -> str:
    if not isinstance(value, str):
        raise ProphetAdapterError("TEXT_UNSAFE", f"{path} is not a string")
    errs = list(_text_safe_validator(schema).iter_errors(value))
    if errs or URL_RE.search(value):
        raise ProphetAdapterError("TEXT_UNSAFE", f"{path} fails text_safe")
    return value


def _as_of_date(source_available_at: str) -> str:
    text = str(source_available_at).strip()
    if not text:
        raise ProphetAdapterError("MISSING_REQUIRED_FIELD", "source_available_at")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ProphetAdapterError("SCHEMA_VIOLATION", f"source_available_at: {exc}") from exc
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.date().isoformat()


def _company_id(raw: object) -> str:
    text = str(raw or "").strip()
    if COMPANY_ID_RE.fullmatch(text):
        return text
    raise ProphetAdapterError("INVALID_COMPANY_ID", f"{raw!r}")


def _one_decimal(n: float) -> str:
    rounded = round(n, 1)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    text = f"{rounded:.1f}"
    if text.endswith(".0"):
        return text[:-2]
    return text


def format_amount(quantity: Mapping[str, Any], locale: str) -> str:
    """Deterministic amount_format (copy_templates.v1). Never derives EPS or % cap."""
    if quantity.get("form") == "absent":
        return ""
    bound = str(quantity.get("bound") or "exact")
    currency = str(quantity.get("currency") or "")
    unit = str(quantity.get("unit") or "")
    if quantity.get("form") == "range":
        low = format_amount(
            {**dict(quantity), "form": "point", "value": quantity.get("low")}, locale
        )
        high = format_amount(
            {**dict(quantity), "form": "point", "value": quantity.get("high")}, locale
        )
        return f"{low}–{high}"
    value = quantity.get("value")
    if not isinstance(value, (int, float)):
        return ""
    av = abs(float(value))
    sign = "-" if float(value) < 0 else ""
    usd = currency == "USD" or unit == "USD"
    if usd and av >= 1e9:
        en = f"{sign}${_one_decimal(float(value) / 1e9)} billion"
        zh = f"{sign}{_one_decimal(float(value) / 1e8)}亿美元"
    elif usd and av >= 1e6:
        en = f"{sign}${_one_decimal(float(value) / 1e6)} million"
        zh = f"{sign}{_one_decimal(float(value) / 1e4)}万美元"
    elif usd:
        en = f"{sign}${_one_decimal(float(value))}"
        zh = f"{sign}{_one_decimal(float(value))}美元"
    else:
        body = f"{_one_decimal(float(value))} {unit}".strip()
        en = f"{sign}{body}"
        zh = f"{sign}{body}"
    prefix_en = {"approximately": "about ", "up_to": "up to ", "at_least": "at least "}.get(bound, "")
    prefix_zh = {"approximately": "约", "up_to": "至多", "at_least": "至少"}.get(bound, "")
    return f"{prefix_zh}{zh}" if locale == "zh" else f"{prefix_en}{en}"


def format_window(period: Any, locale: str, templates: Mapping[str, Any]) -> str:
    """Deterministic window_format. Absence → 'window not stated' / ZH pair."""
    table = templates.get("window_format") or {}
    absent = table.get("absent") or {"en": "window not stated", "zh": "未说明窗口"}
    if not isinstance(period, dict) or period.get("schema") == "field_absence.v1":
        return str(absent.get(locale) or absent.get("en"))
    kind = period.get("period_kind")
    year = period.get("year")
    quarter = period.get("quarter")
    if kind == "fiscal_year" and year is not None:
        row = table.get("fiscal_year") or {"en": "through fiscal {year}", "zh": "至{year}财年"}
        return str(row.get(locale) or row.get("en")).format(year=year)
    if kind == "quarter" and year is not None and quarter is not None:
        row = table.get("quarter") or {"en": "in {year} Q{quarter}", "zh": "{year}年第{quarter}季"}
        return str(row.get(locale) or row.get("en")).format(year=year, quarter=quarter)
    return str(absent.get(locale) or absent.get("en"))


def _dict_lookup(templates: Mapping[str, Any], family: str, key: object, locale: str) -> str | None:
    table = (templates.get("slot_dictionaries") or {}).get(family) or {}
    row = table.get(str(key)) if key is not None else None
    if not isinstance(row, dict):
        return None
    return str(row.get(locale) or row.get("en") or "")


def _scan_injection(node: Any, findings: list[str], path: str = "") -> None:
    if isinstance(node, dict):
        for key in sorted(node):
            _scan_injection(node[key], findings, f"{path}/{key}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _scan_injection(item, findings, f"{path}/{i}")
    elif isinstance(node, str) and INJECTION_RE.search(node):
        findings.append(path or "/")


def _strip_ingest(
    node: Any, stripped: list[str], path: str = "", *, top: bool = False
) -> Any:
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for key in sorted(node):
            child_path = f"{path}.{key}" if path else key
            if key in FORBIDDEN_NAMES or key in FLAG_KEYS and path != "prophet_flags":
                if path == "prophet_flags" and key in FLAG_KEYS:
                    out[key] = node[key]
                    continue
                if key in FLAG_KEYS and path == "prophet_flags":
                    out[key] = node[key]
                    continue
                if key in FORBIDDEN_NAMES:
                    stripped.append(child_path)
                    continue
            if top and key in ALWAYS_DROP:
                stripped.append(child_path)
                continue
            if top and key not in CROSS_FIELDS and key not in HOVER_ONLY_FIELDS and key != "prophet_flags":
                if key in FORBIDDEN_NAMES:
                    stripped.append(child_path)
                    continue
                if key not in {
                    "schema", "authority", "prophet_flags", "unsolicited_instruction_detected",
                }:
                    stripped.append(child_path)
                    continue
            out[key] = _strip_ingest(node[key], stripped, child_path, top=False)
        return out
    if isinstance(node, list):
        return [_strip_ingest(item, stripped, f"{path}[]", top=False) for item in node]
    return node


def _absence_dict(raw: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": "field_absence.v1",
        "authority": AUTHORITY,
        "reason": raw.get("reason"),
        "subject": raw.get("subject"),
        "detail": raw.get("detail") if raw.get("detail") is not None else "",
        "missing_fields": list(raw.get("missing_fields") or []),
    }
    if raw.get("owner_reason"):
        out["owner_reason"] = raw["owner_reason"]
    return out


def _require_quantity_keys(slot: str, raw: Mapping[str, Any], keys: tuple[str, ...]) -> None:
    for key in keys:
        if key not in raw:
            raise ProphetAdapterError("MISSING_REQUIRED_FIELD", f"{slot}.{key}")


def _project_quantity(slot: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    _require_quantity_keys(slot, raw, ("form",))
    form = raw["form"]
    if form not in {"point", "range", "absent"}:
        raise ProphetAdapterError("SCHEMA_VIOLATION", f"{slot}.form")
    if form == "absent":
        absence = raw.get("absence") or {}
        return {"slot": slot, "form": "absent", "absence": _absence_dict(absence)}
    if form == "range":
        # "exact" is the only bound that adds no hedge the v1 range does not carry.
        _require_quantity_keys(slot, raw, ("low", "high", "unit", "currency", "basis"))
        return {
            "slot": slot,
            "form": "range",
            "low": raw["low"],
            "high": raw["high"],
            # A bound the input carries is kept as given; output validation judges it.
            "bound": raw["bound"] if "bound" in raw else RANGE_BOUND,
            "unit": raw["unit"],
            "currency": raw["currency"],
            "basis": raw["basis"],
        }
    _require_quantity_keys(slot, raw, ("value", "bound", "unit", "currency", "basis"))
    return {
        "slot": slot,
        "form": "point",
        "value": raw["value"],
        "bound": raw["bound"],
        "unit": raw["unit"],
        "currency": raw["currency"],
        "basis": raw["basis"],
    }


def _check_locator(locator: Mapping[str, Any]) -> None:
    kind = locator.get("kind")
    allowed = LOCATOR_KEYS.get(str(kind))
    if allowed is None:
        raise ProphetAdapterError("locator_key_not_in_contract", f"kind={kind!r}")
    extra = [k for k in locator if k not in allowed]
    if extra:
        raise ProphetAdapterError(
            "locator_key_not_in_contract",
            "extra locator keys: " + ",".join(sorted(extra)),
        )


def _project_span(
    evidence: Mapping[str, Any],
    *,
    slot: str,
    schema: Mapping[str, Any] | None,
) -> dict[str, Any]:
    claimed = evidence.get("claimed_quote")
    span_in = evidence.get("span")
    if not isinstance(span_in, dict):
        raise ProphetAdapterError("MISSING_REQUIRED_FIELD", f"{slot}.span")
    if span_in.get("document_version") is not None and int(span_in["document_version"]) < 1:
        raise ProphetAdapterError("DOCUMENT_VERSION_MINIMUM", "document_version")
    locator = span_in.get("locator") or {}
    if not isinstance(locator, dict):
        raise ProphetAdapterError("locator_key_not_in_contract", f"{slot}.locator")
    _check_locator(locator)
    projected = project_display({"span": copy.deepcopy(span_in)})
    span = projected["span"]
    claimed_s = "" if claimed is None else str(claimed)
    if len(claimed_s) < 1 or len(claimed_s) > 500:
        raise ProphetAdapterError("TEXT_UNSAFE", f"{slot}.claimed_quote length")
    _require_text_safe(claimed_s, path=f"{slot}.claimed_quote", schema=schema)
    excerpt = span.get("display_excerpt")
    if isinstance(excerpt, str):
        if len(excerpt) > 500 or URL_RE.search(excerpt):
            span["display_excerpt"] = None
        else:
            try:
                _require_text_safe(excerpt, path=f"{slot}.display_excerpt", schema=schema)
            except ProphetAdapterError:
                span["display_excerpt"] = None
    return {
        "slot": slot,
        "claimed_quote": claimed_s,
        "span": {
            "schema": "source_span.v1",
            "authority": AUTHORITY,
            "span_id": span["span_id"],
            "document_id": span["document_id"],
            "document_version": span["document_version"],
            "locator": dict(span["locator"]),
            "text_sha256": span.get("text_sha256"),
            "display_excerpt": span.get("display_excerpt"),
            "rights_profile": span.get("rights_profile") or "rp_unknown_v1",
            "receipt_state": span["receipt_state"],
            "receipt": copy.deepcopy(span.get("receipt")),
            "unreplayable_reason": span.get("unreplayable_reason"),
        },
    }


def _listing_join(
    company_id: str, listing: Mapping[str, Any] | None
) -> dict[str, Any]:
    if listing is None:
        return {
            "ticker": None,
            "state": "unresolved_listing",
            "absence": {
                "schema": "field_absence.v1",
                "authority": AUTHORITY,
                "reason": "not_stated",
                "subject": "listing_ticker",
                "detail": "no ticker join for this cik",
                "missing_fields": ["ticker"],
            },
        }
    if "state" in listing and "ticker" in listing and "cik:" not in "".join(listing.keys()):
        ticker = listing.get("ticker")
        state = listing.get("state")
        if state == "resolved" and isinstance(ticker, str) and TICKER_RE.fullmatch(ticker):
            return {"ticker": ticker, "state": "resolved"}
        if state == "unresolved_listing":
            absence = listing.get("absence") or {
                "schema": "field_absence.v1",
                "authority": AUTHORITY,
                "reason": "not_stated",
                "subject": "listing_ticker",
                "detail": "unresolved listing",
                "missing_fields": ["ticker"],
            }
            return {"ticker": None, "state": "unresolved_listing", "absence": _absence_dict(absence)}
    ticker = listing.get(company_id)
    if isinstance(ticker, str) and TICKER_RE.fullmatch(ticker):
        return {"ticker": ticker, "state": "resolved"}
    # sorted lookup for a one-entry {company_id: ticker} already handled
    for key in sorted(listing):
        if key == company_id:
            val = listing[key]
            if isinstance(val, str) and TICKER_RE.fullmatch(val):
                return {"ticker": val, "state": "resolved"}
    return {
        "ticker": None,
        "state": "unresolved_listing",
        "absence": {
            "schema": "field_absence.v1",
            "authority": AUTHORITY,
            "reason": "not_stated",
            "subject": "listing_ticker",
            "detail": "no ticker join for this cik",
            "missing_fields": ["ticker"],
        },
    }


def _channel_of(
    event: Mapping[str, Any],
    schema_name: str,
    channel_mapping: Mapping[str, Any] | None,
) -> tuple[str, str]:
    if channel_mapping:
        assigned = list(channel_mapping.get("assigned_channels") or [])
        assigned_sorted = sorted(assigned, key=lambda r: (str(r.get("role")), str(r.get("id"))))
        if assigned_sorted:
            cid = assigned_sorted[0].get("id")
            if cid in CHANNELS:
                return str(cid), "channel_mapping"
    hint = event.get("channel_hint") or event.get("channel")
    if hint is None or hint == "":
        default = TEMPLATE_CHANNEL_DEFAULT.get(schema_name, "capital_allocation")
        return default, "template_default"
    if hint not in CHANNELS:
        raise ProphetAdapterError("CHANNEL_INVALID", str(hint))
    return str(hint), "channel_hint"


def _select_template_id(
    event: Mapping[str, Any],
    schema_name: str,
    *,
    display_state: str,
    rights_restricted: bool,
) -> str:
    if display_state in {"deferred", "absence"}:
        return "ABSENCE_defer"
    if rights_restricted or display_state == "rights_restricted":
        return "ABSENCE_rights"
    novelty = event.get("novelty")
    if novelty == "new_reporting_of_old_fact":
        return {
            "capital_allocation_event.v1": "T1_no_change",
            "demand_guidance_contract_event.v1": "T2_no_change",
            "strategic_product_partnership_event.v1": "T3_no_change",
        }.get(schema_name, "T1_no_change")
    if novelty == "corrected_fact":
        return "SUPERSEDED"
    if schema_name == "capital_allocation_event.v1":
        if event.get("commitment_status") in {"executed", "completed"}:
            return "T1_execution"
        return "T1_authorization"
    if schema_name == "demand_guidance_contract_event.v1":
        stage = event.get("demand_stage")
        rev = event.get("revision_direction")
        if stage in {"bookings", "backlog", "pipeline"} or rev in {"awarded", "cancelled"}:
            return "T2_contract"
        return "T2_guidance"
    # T3
    qty = event.get("stated_quantity") if isinstance(event.get("stated_quantity"), dict) else {}
    claim = event.get("economic_claim_class")
    absent_reason = (qty.get("absence") or {}).get("reason") if qty.get("form") == "absent" else None
    if claim == "option_path" or (
        qty.get("form") == "absent" and absent_reason in {"stated_without_number", "not_stated"}
    ):
        return "T3_option"
    return "T3_milestone"


def _display_state_for(
    event: Mapping[str, Any],
    schema_name: str,
    template_id: str,
    *,
    rights_restricted: bool,
    force_superseded: bool,
) -> str:
    if force_superseded:
        return "superseded"
    if rights_restricted:
        return "rights_restricted"
    novelty = event.get("novelty")
    if novelty == "new_reporting_of_old_fact":
        return "no_change"
    if template_id == "T3_option":
        return "not_yet_quantifiable"
    if template_id == "ABSENCE_defer":
        return "deferred"
    if template_id == "ABSENCE_rights":
        return "rights_restricted"
    return "current"


def _slot_value(name: str, value: str) -> str:
    max_len = SLOT_MAX.get(name, 48)
    if len(value) > max_len:
        raise ProphetAdapterError("SLOT_TOO_LONG", f"{name} length {len(value)} > {max_len}")
    return value


def _build_slots(
    event: Mapping[str, Any],
    template_id: str,
    templates: Mapping[str, Any],
    locale: str,
    *,
    predecessor: Mapping[str, Any] | None,
) -> dict[str, str]:
    wanted = TEMPLATE_SLOT_KEYS.get(template_id, ())
    out: dict[str, str] = {}
    schema_name = str(event.get("schema") or "")
    action = _dict_lookup(templates, "action_type", event.get("action_type"), locale)
    status = _dict_lookup(templates, "commitment_status", event.get("commitment_status"), locale)
    metric = _dict_lookup(templates, "metric", event.get("metric"), locale)
    revision = _dict_lookup(templates, "revision_direction", event.get("revision_direction"), locale)
    event_plain = _dict_lookup(templates, "event_kind", event.get("event_kind"), locale)
    object_name = event.get("object_name")
    period = event.get("horizon_period") if "horizon_period" in event else event.get("fiscal_period")
    window = format_window(period, locale, templates)

    def qty_plain(raw: Any) -> str:
        if isinstance(raw, dict):
            return format_amount(raw, locale)
        return ""

    amount = ""
    remaining = ""
    prior = ""
    if schema_name == "capital_allocation_event.v1":
        role = event.get("primary_amount_role")
        inc = event.get("incremental_amount")
        exe = event.get("executed_amount")
        if template_id == "T1_execution":
            amount = qty_plain(exe)
        else:
            amount = qty_plain(inc) if isinstance(inc, dict) and inc.get("form") != "absent" else qty_plain(inc)
            if role == "executed":
                amount = qty_plain(exe)
        remaining = qty_plain(event.get("remaining_authorization"))
    elif schema_name == "demand_guidance_contract_event.v1":
        amount = qty_plain(event.get("stated_amount"))
        prior = qty_plain(event.get("prior_amount"))
    elif schema_name == "strategic_product_partnership_event.v1":
        amount = qty_plain(event.get("stated_quantity"))
    if template_id == "SUPERSEDED" and predecessor is not None:
        pred_schema = str(predecessor.get("schema") or "")
        if pred_schema == "capital_allocation_event.v1":
            prior = qty_plain(predecessor.get("incremental_amount"))
        elif pred_schema == "demand_guidance_contract_event.v1":
            prior = qty_plain(predecessor.get("stated_amount"))
        elif pred_schema == "strategic_product_partnership_event.v1":
            prior = qty_plain(predecessor.get("stated_quantity"))
        if not amount:
            amount = qty_plain(event.get("incremental_amount") or event.get("stated_amount"))

    values = {
        "action_plain": action or "",
        "status_plain": status or "",
        "amount_plain": amount,
        "remaining_plain": remaining,
        "window_plain": window,
        "metric_plain": metric or "",
        "revision_plain": revision or "",
        "event_plain": event_plain or "",
        "object_plain": str(object_name) if object_name else "",
        "prior_amount_plain": prior,
    }
    for key in wanted:
        val = values.get(key) or ""
        if val == "":
            continue
        out[key] = _slot_value(key, val)
    return out


def _glance(
    event: Mapping[str, Any],
    template_id: str,
    templates: Mapping[str, Any],
    *,
    predecessor: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, str]]:
    block = (templates.get("templates") or {}).get(template_id)
    if not isinstance(block, dict):
        raise ProphetAdapterError("COPY_KEY_MISSING", template_id)
    for key_name in ("title_key", "subtitle_key", "window_key", "watching_key"):
        key = block.get(key_name)
        if not isinstance(key, str) or not COPY_KEY_RE.fullmatch(key):
            raise ProphetAdapterError("COPY_KEY_MISSING", f"{template_id}.{key_name}")
    slots_en = _build_slots(event, template_id, templates, "en", predecessor=predecessor)
    slots_zh = _build_slots(event, template_id, templates, "zh", predecessor=predecessor)
    glance = {
        "template_id": template_id,
        "title_key": block["title_key"],
        "subtitle_key": block["subtitle_key"],
        "window_key": block["window_key"],
        "watching_key": block["watching_key"],
        "stance_key": STANCE_KEY,
        "slots": slots_en,
    }
    return glance, slots_zh


def _hover_from(event: Mapping[str, Any], schema: Mapping[str, Any] | None) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    quote = event.get("contrary_mechanism_quote")
    if isinstance(quote, str) and quote.strip():
        clipped = quote[:500]
        try:
            _require_text_safe(clipped, path="contrary_mechanism_quote", schema=schema)
            rows.append({
                "label_en": CONTRARY_LABEL_EN,
                "label_zh": CONTRARY_LABEL_ZH,
                "quote": clipped,
            })
        except ProphetAdapterError:
            pass
    for field_name in ("conditions_quote", "consideration_quote", "license_quote"):
        raw = event.get(field_name)
        if isinstance(raw, str) and raw.strip():
            clipped = raw[:500]
            try:
                _require_text_safe(clipped, path=field_name, schema=schema)
                rows.append({"label_en": field_name, "label_zh": field_name, "quote": clipped})
            except ProphetAdapterError:
                pass
    baseline = event.get("baseline")
    if isinstance(baseline, dict) and baseline.get("type"):
        rows.append({
            "label_en": "baseline_type",
            "label_zh": "baseline_type",
            "quote": str(baseline.get("type")),
        })
    rows.sort(key=lambda r: (r.get("label_en") or "", r.get("quote") or ""))
    return tuple(rows)


def _quantities_for(
    event: Mapping[str, Any], schema_name: str, template_id: str, stripped: list[str]
) -> list[dict[str, Any]]:
    if schema_name == "capital_allocation_event.v1":
        slots = T1_QUANTITY_SLOTS
    elif schema_name == "demand_guidance_contract_event.v1":
        slots = T2_QUANTITY_SLOTS
        if template_id == "SUPERSEDED" and isinstance(event.get("prior_amount"), dict):
            slots = ("stated_amount",)
    else:
        slots = T3_QUANTITY_SLOTS
    out: list[dict[str, Any]] = []
    for slot in slots:
        raw = event.get(slot)
        if not isinstance(raw, dict):
            continue
        for inner in QUANTITY_INTERNAL:
            if inner in raw:
                stripped.append(f"{slot}.{inner}")
        projected = _project_quantity(slot, raw)
        if template_id == "SUPERSEDED" and projected.get("form") == "absent":
            continue
        out.append(projected)
    return out


def _force_flags(raw: Any) -> dict[str, bool]:
    flags = raw if isinstance(raw, dict) else {}
    for key in sorted(FLAG_KEYS):
        if flags.get(key) is True:
            raise ProphetAdapterError("PROPHET_FLAG_TRUE", key)
    return dict(FALSE_FLAGS)


def guard_promotion(obj: Mapping[str, Any]) -> None:
    """Refuse if authority, flags, or a §4.7 field name would cross."""
    if obj.get("authority") != AUTHORITY:
        raise ProphetAdapterError("AUTHORITY_NOT_CONTEXT_ONLY", str(obj.get("authority")))
    flags = obj.get("prophet_flags") or {}
    if not isinstance(flags, dict):
        raise ProphetAdapterError("PROPHET_FLAG_TRUE", "prophet_flags")
    for key in sorted(FLAG_KEYS):
        if flags.get(key) is True:
            raise ProphetAdapterError("PROPHET_FLAG_TRUE", key)
        if flags.get(key) not in (False, None) and key in flags and flags[key] is not False:
            raise ProphetAdapterError("PROPHET_FLAG_TRUE", key)
    if obj.get("unsolicited_instruction_detected") is not False and "unsolicited_instruction_detected" in obj:
        if obj.get("unsolicited_instruction_detected") is not False:
            raise ProphetAdapterError("UNSOLICITED_MUST_BE_FALSE", "unsolicited_instruction_detected")

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key in sorted(node):
                child = f"{path}/{key}" if path else key
                if key in FORBIDDEN_NAMES:
                    raise ProphetAdapterError("FORBIDDEN_FIELD", child)
                if key in FLAG_KEYS and not path.endswith("prophet_flags"):
                    raise ProphetAdapterError("FORBIDDEN_FIELD", child)
                walk(node[key], child)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}/{i}")

    walk(obj, "")


def _banned_token_hit(text: str, token: str) -> bool:
    """ALL-CAPS slugs (WATCH, IGNITION) match as whole tokens, not substrings of 'watching'."""
    if not token:
        return False
    if " " in token or "-" in token:
        return token.lower() in text.lower()
    if token.isupper() and token.isalpha():
        return re.search(r"\b" + re.escape(token) + r"\b", text) is not None
    return re.search(r"(?i)\b" + re.escape(token) + r"\b", text) is not None


def render_glance_copy(
    record: Mapping[str, Any] | ProphetEvidence,
    *,
    copy_templates: Mapping[str, Any] | None = None,
    slots_zh: Mapping[str, str] | None = None,
) -> dict[str, dict[str, str]]:
    """Fill EN/ZH glance strings from copy_templates.v1 keys + slots. No model."""
    payload = record.to_dict() if isinstance(record, ProphetEvidence) else dict(record)
    templates = dict(copy_templates if copy_templates is not None else load_copy_templates())
    glance = payload.get("glance") or {}
    template_id = glance.get("template_id")
    block = (templates.get("templates") or {}).get(template_id) or {}
    slots_en = dict(glance.get("slots") or {})
    zh_slots = dict(slots_zh or {})
    if isinstance(record, ProphetEvidence) and record.slots_zh:
        zh_slots = dict(record.slots_zh)
    stance = templates.get("stance") or {}
    banned = list((templates.get("banned_glance_tokens") or {}).get("tokens") or [])

    def fill(locale: str) -> dict[str, str]:
        loc = block.get(locale) or {}
        slots = zh_slots if locale == "zh" else slots_en

        def sub(text: str) -> str:
            out = text
            for key in sorted(slots):
                out = out.replace("{" + key + "}", str(slots[key]))
            return out

        filled = {
            "title": sub(str(loc.get("title") or "")),
            "subtitle": sub(str(loc.get("subtitle") or "")),
            "window": sub(str(loc.get("window") or "")),
            "watching": sub(str(loc.get("watching") or "")),
            "stance": str(stance.get(locale) or stance.get("en") or ""),
        }
        blob = " ".join(filled.values())
        for token in banned:
            if token and _banned_token_hit(blob, token):
                raise ProphetAdapterError("TEXT_UNSAFE", f"banned glance token {token!r}")
        if locale == "en":
            title_words = [w for w in filled["title"].split() if w]
            sub_words = [w for w in filled["subtitle"].split() if w]
            if len(title_words) > 4 or len(sub_words) > 14:
                raise ProphetAdapterError(
                    "SLOT_TOO_LONG",
                    f"word budget title={len(title_words)} subtitle={len(sub_words)}",
                )
        return filled

    return {"en": fill("en"), "zh": fill("zh")}


def check_rollout_gate(checks: Mapping[str, Any]) -> RolloutGate:
    """Section 4.8: adapter-on only when every named check is true (injected)."""
    stripped = [k for k in checks if k not in ROLLOUT_CHECKS]
    resolved = {name: bool(checks.get(name)) for name in ROLLOUT_CHECKS}
    failed = tuple(name for name in ROLLOUT_CHECKS if not resolved[name])
    del stripped  # recorded only if a caller inspects input; gate itself is closed
    return RolloutGate(checks=resolved, is_open=not failed, failed=failed)


def consumer_payload(
    assembled: NewsImpactFacet, *, rollout: RolloutGate
) -> dict[str, Any] | None:
    """Wiring seam: ``None`` until section 4.8 holds; else the bundle."""
    if not rollout.is_open:
        return None
    return copy.deepcopy(assembled.bundle)


def _as_record_dict(item: Mapping[str, Any] | ProphetEvidence) -> dict[str, Any]:
    return item.to_dict() if isinstance(item, ProphetEvidence) else copy.deepcopy(dict(item))


def _record_sort_tuple(payload: Mapping[str, Any]) -> tuple[Any, ...]:
    state = payload.get("display_state") or ""
    avail = payload.get("source_available_at") or ""
    ref = payload.get("subject_ref") or {}
    fid = ref.get("fact_id") or ref.get("thesis_id") or payload.get("company_id") or ""
    return (_STATE_ORDER.get(str(state), 9), avail, fid)


def _sort_records(payloads: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    items = [dict(p) for p in payloads]
    items.sort(key=lambda r: (_record_sort_tuple(r)[1], _record_sort_tuple(r)[2]), reverse=True)
    items.sort(key=lambda r: _STATE_ORDER.get(str(r.get("display_state") or ""), 9))
    return items


def facet(
    records: Iterable[Mapping[str, Any] | ProphetEvidence],
    *,
    as_of: str,
    rollout: RolloutGate | None = None,
    schema_path: Path | str | None = None,
) -> NewsImpactFacet:
    """Assemble the news-impact facet for a later consumer call.

    Unresolved listings stay under ``_unresolved_cik`` and are counted.
    ``as_of`` is an injected parameter (I10); this function does not read a clock.
    """
    payloads = [_as_record_dict(r) for r in records]
    for payload in payloads:
        guard_promotion(payload)
    ordered = _sort_records(payloads)
    by_ticker: dict[str, list[dict[str, Any]]] = {}
    unresolved: dict[str, list[dict[str, Any]]] = {}
    for payload in ordered:
        join = payload.get("listing_join") or {}
        if join.get("state") == "resolved" and join.get("ticker"):
            by_ticker.setdefault(str(join["ticker"]), []).append(payload)
        else:
            unresolved.setdefault(str(payload.get("company_id")), []).append(payload)
    by_ticker_t = {k: tuple(v) for k, v in sorted(by_ticker.items())}
    unresolved_t = {k: tuple(v) for k, v in sorted(unresolved.items())}
    bundle = {
        "schema": BUNDLE_SCHEMA_NAME,
        "authority": AUTHORITY,
        "prophet_flags": dict(FALSE_FLAGS),
        "as_of": as_of,
        "n_records": len(ordered),
        "records": ordered,
        "disclaimer_key": STANCE_KEY,
    }
    guard_promotion(bundle)
    schema = load_prophet_schema(schema_path)
    errs = list(_bundle_validator(schema).iter_errors(bundle))
    if errs:
        raise ProphetAdapterError("SCHEMA_VIOLATION", errs[0].message)
    assembled = NewsImpactFacet(
        bundle=bundle,
        by_ticker=by_ticker_t,
        unresolved_cik=unresolved_t,
        n_news_impact=len(ordered),
    )
    if rollout is not None and not rollout.is_open:
        # Leaf still returns the facet; wiring uses consumer_payload → None.
        return assembled
    return assembled


def _build_absence(
    event: Mapping[str, Any],
    *,
    listing: Mapping[str, Any] | None,
    templates: Mapping[str, Any],
    stripped: list[str],
    findings: list[str],
    schema: Mapping[str, Any],
) -> ProphetEvidence:
    company_id = _company_id(event.get("company_id"))
    observed = event.get("observed_at")
    available = event.get("source_available_at")
    if not observed or not available:
        raise ProphetAdapterError("MISSING_REQUIRED_FIELD", "observed_at/source_available_at")
    absence_raw = event.get("absence") or event
    if absence_raw.get("schema") != "field_absence.v1" and event.get("schema") == "field_absence.v1":
        absence_raw = event
    absence = _absence_dict(absence_raw if isinstance(absence_raw, dict) else {})
    channel, channel_source = _channel_of(event, "capital_allocation_event.v1", None)
    display_state = "deferred"
    if absence.get("reason") == "redacted_rights":
        display_state = "rights_restricted"
        template_id = "ABSENCE_rights"
    else:
        template_id = "ABSENCE_defer"
    glance, slots_zh = _glance(
        {**dict(event), "schema": "capital_allocation_event.v1"},
        template_id,
        templates,
        predecessor=None,
    )
    payload = {
        "schema": SCHEMA_NAME,
        "authority": AUTHORITY,
        "prophet_flags": dict(FALSE_FLAGS),
        "record_kind": "absence",
        "company_id": company_id,
        "as_of": _as_of_date(str(available)),
        "observed_at": observed,
        "source_available_at": available,
        "issuer_role": event.get("issuer_role") or "subject",
        "channel": channel,
        "display_state": display_state,
        "subject_ref": absence,
        "glance": glance,
        "source_spans": [],
        "quantities": [],
        "absence": absence,
        "listing_join": _listing_join(company_id, listing or event.get("listing_join")),
        "unsolicited_instruction_detected": False,
    }
    guard_promotion(payload)
    errs = list(_record_validator(schema).iter_errors(payload))
    if errs:
        raise ProphetAdapterError("SCHEMA_VIOLATION", errs[0].message)
    return ProphetEvidence(
        payload=payload,
        stripped_fields=tuple(sorted(set(stripped))),
        channel_source=channel_source,
        hover=(),
        slots_zh=slots_zh,
        injection_findings=tuple(findings),
    )


def _build_transfer(
    event: Mapping[str, Any],
    *,
    listing: Mapping[str, Any] | None,
    templates: Mapping[str, Any],
    stripped: list[str],
    findings: list[str],
    schema: Mapping[str, Any],
) -> ProphetEvidence:
    if event.get("one_hop") is not True:
        raise ProphetAdapterError("TRANSFER_NOT_ONE_HOP", str(event.get("one_hop")))
    if event.get("exposure") != "UNKNOWN":
        raise ProphetAdapterError("TRANSFER_EXPOSURE_NOT_UNKNOWN", str(event.get("exposure")))
    source_id = _company_id(event.get("source_company_id") or event.get("company_id"))
    target_id = _company_id(event.get("target_company_id"))
    observed = event.get("observed_at")
    available = event.get("source_available_at")
    if not observed or not available:
        raise ProphetAdapterError("MISSING_REQUIRED_FIELD", "observed_at/source_available_at")
    edge_span_raw = event.get("edge_span")
    source_spans: list[dict[str, Any]] = []
    if isinstance(edge_span_raw, dict) and "span" in edge_span_raw:
        source_spans.append(_project_span(edge_span_raw, slot=str(edge_span_raw.get("slot") or "edge_span"), schema=schema))
    channel = event.get("mechanism_channel") or event.get("channel_hint") or "revenue_demand"
    if channel not in CHANNELS:
        raise ProphetAdapterError("CHANNEL_INVALID", str(channel))
    glance, slots_zh = _glance(
        {
            "schema": "strategic_product_partnership_event.v1",
            "event_kind": "partnership",
            "object_name": "one-hop transfer",
            "horizon_period": {
                "schema": "field_absence.v1",
                "authority": AUTHORITY,
                "reason": "not_stated",
                "subject": "horizon_period",
                "detail": "",
                "missing_fields": ["horizon_period"],
            },
        },
        "T3_option",
        templates,
        predecessor=None,
    )
    payload = {
        "schema": SCHEMA_NAME,
        "authority": AUTHORITY,
        "prophet_flags": dict(FALSE_FLAGS),
        "record_kind": "transfer_edge",
        "company_id": source_id,
        "as_of": _as_of_date(str(available)),
        "observed_at": observed,
        "source_available_at": available,
        "issuer_role": event.get("issuer_role") or "subject",
        "channel": channel,
        "display_state": "current",
        "subject_ref": {
            "kind": "transfer_edge",
            "source_company_id": source_id,
            "target_company_id": target_id,
            "target_role": event.get("target_role") or "supplier",
            "direction": event.get("direction") or "unknown",
            "mechanism_channel": channel,
            "exposure": "UNKNOWN",
            "one_hop": True,
            "edge_span": source_spans[0] if source_spans else _project_span(
                event["edge_span"], slot="edge_span", schema=schema
            ),
        },
        "glance": glance,
        "source_spans": source_spans,
        "quantities": [],
        "absence": None,
        "listing_join": _listing_join(source_id, listing),
        "unsolicited_instruction_detected": False,
    }
    guard_promotion(payload)
    errs = list(_record_validator(schema).iter_errors(payload))
    if errs:
        raise ProphetAdapterError("SCHEMA_VIOLATION", errs[0].message)
    return ProphetEvidence(
        payload=payload,
        stripped_fields=tuple(sorted(set(stripped))),
        channel_source="channel_hint",
        hover=(),
        slots_zh=slots_zh,
        injection_findings=tuple(findings),
    )


def _build_thesis(
    event: Mapping[str, Any],
    *,
    listing: Mapping[str, Any] | None,
    templates: Mapping[str, Any],
    stripped: list[str],
    findings: list[str],
    schema: Mapping[str, Any],
) -> ProphetEvidence:
    company_id = _company_id(event.get("company_id"))
    thesis_id = event.get("thesis_id")
    if not isinstance(thesis_id, str) or not THESIS_ID_RE.fullmatch(thesis_id):
        raise ProphetAdapterError("MISSING_REQUIRED_FIELD", "thesis_id")
    observed = event.get("observed_at")
    available = event.get("source_available_at")
    if not observed or not available:
        raise ProphetAdapterError("MISSING_REQUIRED_FIELD", "observed_at/source_available_at")
    deadline = event.get("deadline_date")
    if deadline is None:
        deadline = {
            "schema": "field_absence.v1",
            "authority": AUTHORITY,
            "reason": "not_stated",
            "subject": "deadline_date",
            "detail": "",
            "missing_fields": ["deadline_date"],
        }
    watching_key = event.get("watching_key") or "t3_opt_watching"
    next_key = event.get("next_observation_key") or watching_key
    for key in (watching_key, next_key):
        if not COPY_KEY_RE.fullmatch(str(key)):
            raise ProphetAdapterError("COPY_KEY_MISSING", str(key))
    supporting = sorted(event.get("supporting_fact_ids") or event.get("supporting_claim_ids") or [])
    contrary = sorted(event.get("contrary_fact_ids") or event.get("contrary_claim_ids") or [])
    glance, slots_zh = _glance(
        {
            "schema": "strategic_product_partnership_event.v1",
            "event_kind": "other_strategic",
            "object_name": "thesis view",
            "horizon_period": deadline if isinstance(deadline, dict) and deadline.get("year") else {
                "schema": "field_absence.v1",
                "authority": AUTHORITY,
                "reason": "not_stated",
                "subject": "horizon_period",
                "detail": "",
                "missing_fields": ["horizon_period"],
            },
        },
        "T3_option",
        templates,
        predecessor=None,
    )
    glance["watching_key"] = watching_key
    payload = {
        "schema": SCHEMA_NAME,
        "authority": AUTHORITY,
        "prophet_flags": dict(FALSE_FLAGS),
        "record_kind": "thesis_view",
        "company_id": company_id,
        "as_of": _as_of_date(str(available)),
        "observed_at": observed,
        "source_available_at": available,
        "issuer_role": event.get("issuer_role") or "subject",
        "channel": event.get("channel_hint") or event.get("channel") or "strategic_option",
        "display_state": "current",
        "subject_ref": {
            "kind": "thesis_view",
            "thesis_id": thesis_id,
            "cluster_grain": "thesis_link",
            "supporting_fact_ids": supporting,
            "contrary_fact_ids": contrary,
            "next_observation_key": next_key,
            "deadline_date": deadline,
            "watching_key": watching_key,
        },
        "glance": glance,
        "source_spans": [],
        "quantities": [],
        "absence": None,
        "listing_join": _listing_join(company_id, listing),
        "unsolicited_instruction_detected": False,
    }
    if payload["channel"] not in CHANNELS:
        raise ProphetAdapterError("CHANNEL_INVALID", str(payload["channel"]))
    guard_promotion(payload)
    errs = list(_record_validator(schema).iter_errors(payload))
    if errs:
        raise ProphetAdapterError("SCHEMA_VIOLATION", errs[0].message)
    return ProphetEvidence(
        payload=payload,
        stripped_fields=tuple(sorted(set(stripped))),
        channel_source="channel_hint" if event.get("channel_hint") else "template_default",
        hover=(),
        slots_zh=slots_zh,
        injection_findings=tuple(findings),
    )


def build_prophet_evidence(
    event: Mapping[str, Any],
    *,
    listing: Mapping[str, Any] | None = None,
    predecessor: Mapping[str, Any] | None = None,
    channel_mapping: Mapping[str, Any] | None = None,
    transfer_edge: Mapping[str, Any] | None = None,
    copy_templates: Mapping[str, Any] | None = None,
    schema_path: Path | str | None = None,
    force_superseded: bool = False,
) -> ProphetEvidence:
    """Project a validated news-impact fact (or typed absence) to prophet_evidence.v1.

    ``listing``, ``predecessor``, ``channel_mapping`` and ``transfer_edge`` are
    injected data. Copy templates and the prophet schema load lazily from
    ``contracts/news_impact`` unless a path / dict is supplied.
    """
    if not isinstance(event, Mapping):
        raise ProphetAdapterError("MISSING_REQUIRED_FIELD", "event")
    stripped: list[str] = []
    findings: list[str] = []
    _scan_injection(event, findings)
    cleaned = _strip_ingest(copy.deepcopy(dict(event)), stripped, top=True)
    if cleaned.get("unsolicited_instruction_detected") is True:
        raise ProphetAdapterError("UNSOLICITED_INSTRUCTION", "unsolicited_instruction_detected")
    if cleaned.get("schema") == "quarantine_note.v1":
        raise ProphetAdapterError("QUARANTINE_REFUSED", "quarantine_note.v1")
    if cleaned.get("authority") not in (None, AUTHORITY) and cleaned.get("schema") in TEMPLATE_SCHEMAS:
        raise ProphetAdapterError("AUTHORITY_NOT_CONTEXT_ONLY", str(cleaned.get("authority")))
    if cleaned.get("authority") not in (None, AUTHORITY) and cleaned.get("record_kind") in {
        "fact", "absence", "thesis_view", "transfer_edge",
    }:
        raise ProphetAdapterError("AUTHORITY_NOT_CONTEXT_ONLY", str(cleaned.get("authority")))
    _force_flags(cleaned.get("prophet_flags"))
    templates = dict(copy_templates if copy_templates is not None else load_copy_templates())
    schema = load_prophet_schema(schema_path)

    record_kind = cleaned.get("record_kind")
    schema_name = str(cleaned.get("schema") or "")
    if schema_name == "field_absence.v1" or record_kind == "absence":
        return _build_absence(
            cleaned, listing=listing, templates=templates, stripped=stripped,
            findings=findings, schema=schema,
        )
    if schema_name == "transfer_edge.v1" or record_kind == "transfer_edge" or cleaned.get("kind") == "transfer_edge":
        body = dict(cleaned)
        if transfer_edge:
            body.update(dict(transfer_edge))
        return _build_transfer(
            body, listing=listing, templates=templates, stripped=stripped,
            findings=findings, schema=schema,
        )
    if schema_name == "thesis_view.v1" or record_kind == "thesis_view" or cleaned.get("kind") == "thesis_view":
        return _build_thesis(
            cleaned, listing=listing, templates=templates, stripped=stripped,
            findings=findings, schema=schema,
        )
    if schema_name not in TEMPLATE_SCHEMAS:
        raise ProphetAdapterError("UNKNOWN_TEMPLATE", schema_name or "<missing>")

    for key in ("fact_id", "document_id", "observed_at", "source_available_at", "company_id"):
        if not cleaned.get(key):
            raise ProphetAdapterError("MISSING_REQUIRED_FIELD", key)
    if not FACT_ID_RE.fullmatch(str(cleaned["fact_id"])):
        raise ProphetAdapterError("SCHEMA_VIOLATION", "fact_id")
    company_id = _company_id(cleaned["company_id"])
    if cleaned.get("novelty") == "corrected_fact" and not cleaned.get("supersedes_fact_id"):
        raise ProphetAdapterError("CORRECTED_FACT_MISSING_SUPERSEDES", "supersedes_fact_id")

    hover = _hover_from(event, schema)
    for name in HOVER_ONLY_FIELDS:
        if name in event:
            stripped.append(name)

    source_spans: list[dict[str, Any]] = []
    rights_restricted = False
    action_span = cleaned.get("action_span")
    if isinstance(action_span, dict) and action_span.get("span"):
        projected = _project_span(action_span, slot="action_span", schema=schema)
        source_spans.append(projected)
        excerpt = projected["span"].get("display_excerpt")
        receipt_state = projected["span"].get("receipt_state")
        if excerpt is None and receipt_state == "byte_replayed":
            rights_restricted = True
    if (cleaned.get("absence") or {}).get("reason") == "redacted_rights":
        rights_restricted = True

    template_id = _select_template_id(
        cleaned, schema_name, display_state="current", rights_restricted=rights_restricted
    )
    display_state = _display_state_for(
        cleaned, schema_name, template_id,
        rights_restricted=rights_restricted, force_superseded=force_superseded,
    )
    if display_state == "rights_restricted":
        template_id = "ABSENCE_rights"
        for item in source_spans:
            item["span"]["display_excerpt"] = None
    if display_state == "no_change":
        template_id = {
            "capital_allocation_event.v1": "T1_no_change",
            "demand_guidance_contract_event.v1": "T2_no_change",
            "strategic_product_partnership_event.v1": "T3_no_change",
        }[schema_name]
    if display_state == "superseded" and template_id == "SUPERSEDED":
        # predecessor history row keeps family template, not the successor SUPERSEDED glance
        template_id = {
            "capital_allocation_event.v1": "T1_authorization",
            "demand_guidance_contract_event.v1": "T2_guidance",
            "strategic_product_partnership_event.v1": "T3_milestone",
        }[schema_name]

    glance, slots_zh = _glance(cleaned, template_id, templates, predecessor=predecessor)
    channel, channel_source = _channel_of(cleaned, schema_name, channel_mapping)
    quantities = _quantities_for(cleaned, schema_name, template_id, stripped)
    cluster_grain = cleaned.get("cluster_grain")
    if cluster_grain is None:
        raise ProphetAdapterError("MISSING_REQUIRED_FIELD", "cluster_grain")

    absence_out: dict[str, Any] | None = None
    if display_state == "rights_restricted":
        absence_out = {
            "schema": "field_absence.v1",
            "authority": AUTHORITY,
            "reason": "redacted_rights",
            "subject": "display_excerpt",
            "detail": "excerpt nulled under R1",
            "missing_fields": ["display_excerpt"],
        }
        if isinstance(cleaned.get("absence"), dict) and cleaned["absence"].get("reason") == "redacted_rights":
            absence_out = _absence_dict(cleaned["absence"])
    elif isinstance(cleaned.get("absence"), dict):
        absence_out = _absence_dict(cleaned["absence"])

    listing_join = _listing_join(company_id, listing if listing is not None else cleaned.get("listing_join"))

    payload: dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "authority": AUTHORITY,
        "prophet_flags": dict(FALSE_FLAGS),
        "record_kind": "fact",
        "company_id": company_id,
        "as_of": _as_of_date(str(cleaned["source_available_at"])),
        "observed_at": cleaned["observed_at"],
        "source_available_at": cleaned["source_available_at"],
        "issuer_role": cleaned.get("issuer_role") or "subject",
        "channel": channel,
        "display_state": display_state,
        "novelty": cleaned["novelty"],
        "commitment_status": cleaned["commitment_status"],
        "negated": bool(cleaned.get("negated")),
        "cluster_grain": cluster_grain,
        "subject_ref": {
            "kind": "fact",
            "fact_id": cleaned["fact_id"],
            "template_schema": schema_name,
            "document_id": cleaned["document_id"],
            "supersedes_fact_id": cleaned.get("supersedes_fact_id"),
        },
        "glance": glance,
        "source_spans": source_spans,
        "quantities": quantities,
        "absence": absence_out,
        "listing_join": listing_join,
        "unsolicited_instruction_detected": False,
    }
    if transfer_edge:
        # consumed as a dict; v1 exposure stays UNKNOWN and is not mixed into this fact
        stripped.append("transfer_edge")
    guard_promotion(payload)
    errs = list(_record_validator(schema).iter_errors(payload))
    if errs:
        raise ProphetAdapterError("SCHEMA_VIOLATION", errs[0].message)
    return ProphetEvidence(
        payload=payload,
        stripped_fields=tuple(sorted(set(stripped))),
        channel_source=channel_source,
        hover=hover,
        slots_zh=slots_zh,
        injection_findings=tuple(findings),
    )


def adapt_batch(
    events: Iterable[Mapping[str, Any]],
    *,
    listing: Mapping[str, Any] | None = None,
    channel_mapping: Mapping[str, Any] | None = None,
    copy_templates: Mapping[str, Any] | None = None,
    schema_path: Path | str | None = None,
) -> tuple[ProphetEvidence, ...]:
    """Project many events. A successor marks its in-batch predecessor superseded."""
    items = [dict(e) for e in events]
    items.sort(key=lambda e: (str(e.get("source_available_at") or ""), str(e.get("fact_id") or "")))
    by_id = {str(e["fact_id"]): e for e in items if e.get("fact_id")}
    superseded: set[str] = set()
    for event in items:
        pred_id = event.get("supersedes_fact_id")
        if pred_id:
            superseded.add(str(pred_id))
    out: list[ProphetEvidence] = []
    for event in items:
        pred = by_id.get(str(event.get("supersedes_fact_id"))) if event.get("supersedes_fact_id") else None
        force = str(event.get("fact_id")) in superseded
        out.append(build_prophet_evidence(
            event,
            listing=listing,
            predecessor=pred,
            channel_mapping=channel_mapping,
            copy_templates=copy_templates,
            schema_path=schema_path,
            force_superseded=force,
        ))
    return tuple(out)
