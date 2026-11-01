"""Mechanism / channel library runtime for news-impact facts.

Implements masterplan section 4 (the seven-channel reviewed library, the
sourced-term driver bridge, not-yet-quantifiable records, and duration
scenarios without weights) under Phase 0 freeze D1r / DEC:NEWS-IMPACT-PHASE0-FREEZE
(closed enums, evidence = owner source_span.v1 or field_absence.v1, no
confidence / probability / score / price_target / fair_value) and Wave 3
seat rulings W3-R1–W3-R6 plus A2 section 7 defaults.

The mapper is a pure function of one fact dict plus channel_library.v1.
``channel_hint`` is never a mapping input (I-HINT-1); a hint/map disagreement
yields warning code ``V_HINT_NOT_MAP`` and does not reject. Source text is
DATA (masterplan §3.5): instruction-shaped quotes are recorded as injection
findings and ignored.

Determinism: no clock reads, no randomness, sorted iteration over sets/dicts,
stable rule order (priority, then rule_id). ``as_of`` is never read; callers
pass already-validated facts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

LIBRARY_NAME = "channel_library.v1"
LIBRARY_RELPATH = Path("contracts") / "news_impact" / "channel_library.v1.json"
MAPPING_SCHEMA_RELPATH = Path("contracts") / "news_impact" / "channel_mapping.v1.schema.json"
BRIDGE_SCHEMA_RELPATH = Path("contracts") / "news_impact" / "driver_bridge.v1.schema.json"

T1 = "capital_allocation_event.v1"
T2 = "demand_guidance_contract_event.v1"
T3 = "strategic_product_partnership_event.v1"
UNMAPPED_SCHEMA = "unmapped_event.v1"
INPUT_SCHEMAS = (T1, T2, T3, UNMAPPED_SCHEMA)

EARNINGS_HEAD_CHANNELS = frozenset(
    {
        "revenue_demand",
        "margin_cost",
        "capital_allocation",
        "moat_duration",
        "strategic_option",
        "financial_incentives_survival",
    }
)
MARKET_ONLY = "market_only"
CHANNEL_IDS = (
    "revenue_demand",
    "margin_cost",
    "capital_allocation",
    "moat_duration",
    "strategic_option",
    "financial_incentives_survival",
    "market_only",
)
BRIDGE_TERM_IDS = (
    "eligible_units",
    "realized_revenue_per_unit",
    "incremental_margin",
    "operating_costs",
    "cash_taxes",
    "required_capital",
)
DURATION_SCENARIO_IDS = (
    "failure",
    "niche_adoption",
    "broad_adoption",
    "displacement_cannibalization",
)
MARKET_CLASS = frozenset(
    {
        "rating_change",
        "analyst_estimate_revision",
        "macro_release",
        "mna_rumor",
    }
)
STICKY_STATUSES = frozenset({"ineligible_role", "strategic_review"})
FORBIDDEN_KEYS = frozenset(
    {
        "confidence",
        "probability",
        "score",
        "price_target",
        "fair_value",
        "sentiment",
        "contagion",
        "rating",
        "likelihood",
        "weight",
    }
)
COMPANY_ID_RE = re.compile(r"^cik:(?!0{10}$)[0-9]{10}$")
FACT_ID_RE = re.compile(r"^fact_[0-9a-f]{24}$")
INJECTION_RE = re.compile(
    r"ignore (all )?previous instructions|you are now |system prompt|"
    r"disregard (the )?(above|prior)|assign revenue_demand",
    re.IGNORECASE,
)
WHO_WOULD_RULE = "seat_dec_after_empirical_or_explicit_assumption"
PROPHET_FLAGS = {
    "may_rank": False,
    "may_size": False,
    "may_gate": False,
    "prophet_authority": False,
}

CODES = frozenset(
    {
        "LIBRARY_MISSING_FILE",
        "LIBRARY_BAD_VERSION",
        "LIBRARY_DUPLICATE_RULE_ID",
        "INSTANCE_NOT_MAPPING",
        "INVARIANT_I_MO_1",
        "INVARIANT_I_MO_2",
        "INVARIANT_I_DOUBLE_1",
        "INVARIANT_I_ROLE_1",
        "INVARIANT_I_CORR_1",
        "INVARIANT_I_ORIG_1",
    }
)

V_HINT_NOT_MAP = "V_HINT_NOT_MAP"

_DURATION_EVIDENCE: dict[str, tuple[str, ...]] = {
    "failure": (
        "independent_deployment_absent_through_horizon",
        "maintenance_cost_exceeds_stated_monetization",
    ),
    "niche_adoption": (
        "repeated_active_use_in_named_segment",
        "support_revenue_stated",
    ),
    "broad_adoption": (
        "paid_bookings_span_backed",
        "reported_incremental_orders",
    ),
    "displacement_cannibalization": (
        "compute_per_workload_down_on_issuer_hardware",
        "deployments_on_non_issuer_hardware",
    ),
}

_NYQ_EVIDENCE: dict[str, dict[str, str]] = {
    "authorization_without_execution": {
        "description": "executed repurchase amount and net dilution against this authorization",
        "named_window": "through_horizon_period",
        "source_owner": "executed_capital_action",
    },
    "addressable_market_not_funded": {
        "description": "bookings or recognized revenue in a stated fiscal period, span-backed, distinct from the TAM figure",
        "named_window": "stated_fiscal_period",
        "source_owner": "issuer_filing",
    },
    "driver_bridge_term_absent": {
        "description": "independent production deployments, paid bookings, and hardware mix on the announced models",
        "named_window": "until_independent_milestone",
        "source_owner": "independent_deployment",
    },
    "claim_class_none_stated": {
        "description": "issuer names funded demand, an option path, or a duration claim with span-backed evidence",
        "named_window": "decision_cut_session",
        "source_owner": "issuer_filing",
    },
    "attention_proxy_only": {
        "description": "span-backed paid bookings or recognized units, distinct from downloads or stars",
        "named_window": "stated_fiscal_period",
        "source_owner": "issuer_filing",
    },
    "commentary_only": {
        "description": "an issuer operating fact (guidance, execution, funded contract, or product milestone)",
        "named_window": "decision_cut_session",
        "source_owner": "issuer_filing",
    },
}


class MechanismsError(Exception):
    """Module-specific error carrying a closed ``CODES`` member in ``code``."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ChannelAssignment:
    """One assigned channel id plus its closed role."""

    id: str
    role: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "role": self.role}


@dataclass(frozen=True)
class MappingWarning:
    """Non-rejecting mapper warning. ``V_HINT_NOT_MAP`` is the v1 code."""

    code: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class ChannelMapping:
    """Validated-shape channel_mapping.v1 plus side-channel warnings."""

    schema: str
    library_version: str
    rule_ids: tuple[str, ...]
    fact_id: str
    company_id: str
    input_schema: str
    assigned_channels: tuple[ChannelAssignment, ...]
    mapping_status: str
    earnings_head: str
    prophet_flags: dict[str, bool]
    unsolicited_instruction_detected: bool
    driver_bridge: dict[str, Any] | None
    not_yet_quantifiable: dict[str, Any] | None
    duration_scenarios: dict[str, Any] | None
    inherits_from_fact_id: str | None
    unmapped: dict[str, Any] | None
    named_quantities: dict[str, Any] | None
    display_words: str | None
    warnings: tuple[MappingWarning, ...]
    stripped_fields: tuple[str, ...]
    injection_findings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema": self.schema,
            "library_version": self.library_version,
            "rule_ids": list(self.rule_ids),
            "fact_id": self.fact_id,
            "company_id": self.company_id,
            "input_schema": self.input_schema,
            "assigned_channels": [c.to_dict() for c in self.assigned_channels],
            "mapping_status": self.mapping_status,
            "earnings_head": self.earnings_head,
            "driver_bridge": self.driver_bridge,
            "not_yet_quantifiable": self.not_yet_quantifiable,
            "duration_scenarios": self.duration_scenarios,
            "inherits_from_fact_id": self.inherits_from_fact_id,
            "prophet_flags": {
                "may_rank": False,
                "may_size": False,
                "may_gate": False,
                "prophet_authority": False,
            },
            "unsolicited_instruction_detected": False,
        }
        if self.unmapped is not None:
            out["unmapped"] = self.unmapped
        if self.named_quantities:
            out["named_quantities"] = self.named_quantities
        if self.display_words:
            out["display_words"] = self.display_words
        return out


def canonical_json(obj: Any) -> str:
    """Canonical JSON: sorted keys, compact separators, UTF-8 preserved."""

    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _default_path(rel: Path) -> Path:
    return Path(__file__).resolve().parents[2] / rel


def load_library(path: str | Path | None = None) -> dict[str, Any]:
    """Lazy-load ``channel_library.v1.json``. No module-level I/O.

    Raises ``MechanismsError`` with ``LIBRARY_MISSING_FILE``,
    ``LIBRARY_BAD_VERSION``, or ``LIBRARY_DUPLICATE_RULE_ID``.
    """

    p = Path(path) if path is not None else _default_path(LIBRARY_RELPATH)
    if not p.is_file():
        raise MechanismsError("LIBRARY_MISSING_FILE", f"channel library not found: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != LIBRARY_NAME:
        found = raw.get("schema") if isinstance(raw, dict) else type(raw).__name__
        raise MechanismsError(
            "LIBRARY_BAD_VERSION",
            f"library schema {found!r} is not {LIBRARY_NAME}",
        )
    rules = raw.get("mapping_rules")
    if not isinstance(rules, list):
        raise MechanismsError("LIBRARY_BAD_VERSION", "mapping_rules is not a list")
    seen: set[str] = set()
    for rule in rules:
        rid = rule.get("rule_id") if isinstance(rule, dict) else None
        if not isinstance(rid, str) or not rid:
            raise MechanismsError("LIBRARY_BAD_VERSION", "mapping rule missing rule_id")
        if rid in seen:
            raise MechanismsError(
                "LIBRARY_DUPLICATE_RULE_ID",
                f"duplicate mapping rule_id {rid}",
            )
        seen.add(rid)
    return raw


def load_channel_mapping_schema(path: str | Path | None = None) -> dict[str, Any]:
    """Lazy-load ``channel_mapping.v1.schema.json``."""

    p = Path(path) if path is not None else _default_path(MAPPING_SCHEMA_RELPATH)
    if not p.is_file():
        raise MechanismsError("LIBRARY_MISSING_FILE", f"mapping schema not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def load_driver_bridge_schema(path: str | Path | None = None) -> dict[str, Any]:
    """Lazy-load ``driver_bridge.v1.schema.json``."""

    p = Path(path) if path is not None else _default_path(BRIDGE_SCHEMA_RELPATH)
    if not p.is_file():
        raise MechanismsError("LIBRARY_MISSING_FILE", f"driver-bridge schema not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def strip_forbidden_fields(obj: Any, prefix: str = "") -> tuple[Any, list[str]]:
    """Drop forbidden keys at ingest. Returns (cleaned, stripped JSON-pointer list)."""

    stripped: list[str] = []
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key in sorted(obj.keys(), key=lambda k: str(k)):
            ptr = f"{prefix}/{key}"
            if key in FORBIDDEN_KEYS:
                stripped.append(ptr)
                continue
            child, child_stripped = strip_forbidden_fields(obj[key], ptr)
            out[key] = child
            stripped.extend(child_stripped)
        return out, stripped
    if isinstance(obj, list):
        out_list = []
        for i, item in enumerate(obj):
            child, child_stripped = strip_forbidden_fields(item, f"{prefix}/{i}")
            out_list.append(child)
            stripped.extend(child_stripped)
        return out_list, stripped
    return obj, stripped


def _pointer_get(instance: Mapping[str, Any], pointer: str) -> tuple[bool, Any]:
    if pointer == "" or pointer == "/":
        return True, instance
    if not pointer.startswith("/"):
        return False, None
    node: Any = instance
    for raw in pointer[1:].split("/"):
        part = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, Mapping) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return False, None
    return True, node


def _match_when(when: Any, instance: Mapping[str, Any]) -> bool:
    if not isinstance(when, dict) or not when:
        return False
    if "all" in when:
        items = when["all"]
        return isinstance(items, list) and all(_match_when(w, instance) for w in items)
    if "any" in when:
        items = when["any"]
        return isinstance(items, list) and any(_match_when(w, instance) for w in items)
    if "not" in when:
        return not _match_when(when["not"], instance)
    if "eq" in when:
        ptr, value = when["eq"]
        found, got = _pointer_get(instance, ptr)
        return found and got == value
    if "in" in when:
        ptr, values = when["in"]
        found, got = _pointer_get(instance, ptr)
        return found and got in values
    if "form_in" in when:
        ptr, forms = when["form_in"]
        found, got = _pointer_get(instance, ptr)
        if not found or not isinstance(got, Mapping):
            return False
        return got.get("form") in forms
    if "exists" in when:
        ptr = when["exists"]
        found, got = _pointer_get(instance, ptr)
        return found and got is not None
    if "is_company_id" in when:
        ptr = when["is_company_id"]
        found, got = _pointer_get(instance, ptr)
        return found and isinstance(got, str) and COMPANY_ID_RE.match(got) is not None
    return False


def _sorted_rules(library: Mapping[str, Any]) -> list[dict[str, Any]]:
    rules = [r for r in library.get("mapping_rules", []) if isinstance(r, dict)]
    return sorted(rules, key=lambda r: (int(r.get("priority", 0)), str(r.get("rule_id", ""))))


def _upsert_assign(
    assigned: list[ChannelAssignment], additions: Sequence[Mapping[str, Any]]
) -> list[ChannelAssignment]:
    by_id = {c.id: c for c in assigned}
    order = [c.id for c in assigned]
    for item in additions:
        cid = item.get("id")
        role = item.get("role")
        if not isinstance(cid, str) or not isinstance(role, str):
            continue
        by_id[cid] = ChannelAssignment(id=cid, role=role)
        if cid not in order:
            order.append(cid)
    return [by_id[i] for i in order if i in by_id]


def _apply_remove(assigned: list[ChannelAssignment], remove: Sequence[Any]) -> list[ChannelAssignment]:
    drop = {r for r in remove if isinstance(r, str)}
    return [c for c in assigned if c.id not in drop]


def _scan_injections(obj: Any, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, str):
        if INJECTION_RE.search(obj):
            hits.append(prefix or "/")
        return hits
    if isinstance(obj, Mapping):
        for key in sorted(obj.keys(), key=lambda k: str(k)):
            hits.extend(_scan_injections(obj[key], f"{prefix}/{key}"))
        return hits
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            hits.extend(_scan_injections(item, f"{prefix}/{i}"))
    return hits


def _absence(subject: str, reason: str = "not_stated", detail: str = "", missing: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": "field_absence.v1",
        "authority": "context_only",
        "reason": reason,
        "subject": subject,
        "detail": detail,
        "missing_fields": list(missing) if missing is not None else [subject],
    }


def _absent_term(term_id: str) -> dict[str, Any]:
    return {"form": "absent", "absence": _absence(term_id, missing=[term_id], detail="")}


def _project_quantity(qty: Mapping[str, Any], source_contract_path: str) -> dict[str, Any] | None:
    form = qty.get("form")
    if form == "point":
        out: dict[str, Any] = {
            "form": "point",
            "value": qty.get("value"),
            "unit": qty.get("unit"),
            "basis": qty.get("basis"),
            "source_contract_path": source_contract_path,
        }
        if "currency" in qty:
            out["currency"] = qty["currency"]
        if "bound" in qty:
            out["bound"] = qty["bound"]
        return out
    if form in ("range", "interval"):
        out = {
            "form": "interval" if form == "interval" else "range",
            "low": qty.get("low"),
            "high": qty.get("high"),
            "unit": qty.get("unit"),
            "basis": qty.get("basis"),
            "source_contract_path": source_contract_path,
        }
        if "currency" in qty:
            out["currency"] = qty["currency"]
        return out
    if form == "absent":
        absence = qty.get("absence")
        if not isinstance(absence, dict):
            absence = _absence(source_contract_path.lstrip("/"))
        return {"form": "absent", "absence": dict(absence)}
    return None


def _term_from_quantity(qty: Mapping[str, Any], source_contract_path: str) -> dict[str, Any] | None:
    """Map a frozen quantity (point/range/absent) onto a driver-bridge term."""

    form = qty.get("form")
    if form == "point":
        evidence = qty.get("evidence")
        term: dict[str, Any] = {
            "form": "point",
            "value": qty.get("value"),
            "bound": qty.get("bound", "exact"),
            "unit": qty.get("unit", "NA"),
            "currency": qty.get("currency", "NA"),
            "basis": qty.get("basis", "total"),
            "source_contract_path": source_contract_path,
            "evidence": evidence if isinstance(evidence, dict) else {
                "claimed_quote": "not_stated",
                "span": {
                    "schema": "source_span.v1",
                    "authority": "context_only",
                    "span_id": "span_absent_term_placeholder",
                    "document_id": "doc_absent",
                    "document_version": 1,
                    "locator": {"kind": "text_span"},
                    "receipt_state": "address_only",
                },
            },
        }
        if "period" in qty:
            term["period"] = qty["period"]
        return term
    if form in ("range", "interval"):
        evidence = qty.get("evidence")
        term = {
            "form": "interval",
            "low": qty.get("low"),
            "high": qty.get("high"),
            "unit": qty.get("unit", "NA"),
            "currency": qty.get("currency", "NA"),
            "basis": qty.get("basis", "total"),
            "source_contract_path": source_contract_path,
            "evidence": evidence if isinstance(evidence, dict) else {
                "claimed_quote": "not_stated",
                "span": {
                    "schema": "source_span.v1",
                    "authority": "context_only",
                    "span_id": "span_absent_term_placeholder",
                    "document_id": "doc_absent",
                    "document_version": 1,
                    "locator": {"kind": "text_span"},
                    "receipt_state": "address_only",
                },
            },
        }
        if "period" in qty:
            term["period"] = qty["period"]
        return term
    if form == "absent":
        return _absent_term(source_contract_path.lstrip("/").split("/")[0])
    if form == "assumption":
        return dict(qty)
    return None


def _qty_when(when: str, instance: Mapping[str, Any], qty: Mapping[str, Any] | None) -> bool:
    if when == "V_NO_SUM_T2":
        return False
    form = qty.get("form") if isinstance(qty, Mapping) else None
    metric = instance.get("metric")
    stage = instance.get("demand_stage")
    claim = instance.get("economic_claim_class")
    role = instance.get("primary_amount_role")
    rev = instance.get("revision_direction")
    if when == "T2 metric=units and demand_stage in bookings,recognized_revenue and form in point,range":
        return metric == "units" and stage in ("bookings", "recognized_revenue") and form in ("point", "range")
    if when == "T2 metric=revenue":
        return metric == "revenue" and form in ("point", "range", "interval")
    if when == "T2 metric=bookings":
        return metric == "bookings" and form in ("point", "range", "interval")
    if when == "T2 metric=backlog":
        return metric == "backlog" and form in ("point", "range", "interval")
    if when == "T2 metric=eps":
        return metric == "eps" and form in ("point", "range", "interval")
    if when == "T3 economic_claim_class=funded_demand and form in point,range":
        return claim == "funded_demand" and form in ("point", "range")
    if when == "economic_claim_class=funded_demand and form in point,range":
        return claim == "funded_demand" and form in ("point", "range")
    if when == "primary_amount_role=incremental_authorization and form in point,range":
        return role == "incremental_authorization" and form in ("point", "range")
    if when == "form in point,range":
        return form in ("point", "range")
    if when == "revision_direction=awarded":
        return rev == "awarded" and form in ("point", "range", "interval")
    return False


def _named_quantities(
    instance: Mapping[str, Any], library: Mapping[str, Any], assigned: Sequence[ChannelAssignment]
) -> dict[str, Any]:
    channels = {c["id"]: c for c in library.get("channels", []) if isinstance(c, dict) and "id" in c}
    assigned_ids = [c.id for c in assigned]
    # Always consult T1 capital_allocation maps when the input is T1, even if
    # a sticky rule left assigned empty — named quantities still describe the packet.
    consult_ids = list(assigned_ids)
    schema = instance.get("schema")
    if schema == T1 and "capital_allocation" not in consult_ids:
        consult_ids.append("capital_allocation")
    if schema == T2 and "revenue_demand" not in consult_ids:
        consult_ids.append("revenue_demand")
    out: dict[str, Any] = {}
    for cid in consult_ids:
        rec = channels.get(cid)
        if not rec:
            continue
        for entry in rec.get("quantity_form_map") or []:
            if not isinstance(entry, dict):
                continue
            feeds = entry.get("feeds")
            path = entry.get("contract_path")
            when = entry.get("when") or ""
            if not isinstance(feeds, str) or not isinstance(path, str):
                continue
            if feeds == "forbidden":
                continue
            found, qty = _pointer_get(instance, path)
            if not found or not isinstance(qty, Mapping):
                continue
            if not _qty_when(when, instance, qty):
                # Case A includes executed_amount even when form=absent.
                if feeds == "executed_retired_or_issued" and qty.get("form") == "absent":
                    projected = _project_quantity(qty, path)
                    if projected is not None:
                        out[feeds] = projected
                continue
            projected = _project_quantity(qty, path)
            if projected is not None:
                out[feeds] = projected
    return dict((k, out[k]) for k in sorted(out.keys()))


def _term_bounds(term: Mapping[str, Any]) -> tuple[float, float] | None:
    form = term.get("form")
    if form == "point" and isinstance(term.get("value"), (int, float)):
        v = float(term["value"])
        return v, v
    if form in ("interval", "range") and isinstance(term.get("low"), (int, float)) and isinstance(term.get("high"), (int, float)):
        return float(term["low"]), float(term["high"])
    return None


def _margin_bounds(term: Mapping[str, Any]) -> tuple[float, float] | None:
    bounds = _term_bounds(term)
    if bounds is None:
        return None
    lo, hi = bounds
    if term.get("basis") == "percent":
        return lo / 100.0, hi / 100.0
    return lo, hi


def _compute_product(terms: Mapping[str, Mapping[str, Any]]) -> dict[str, Any] | None:
    units = _term_bounds(terms["eligible_units"])
    price = _term_bounds(terms["realized_revenue_per_unit"])
    margin = _margin_bounds(terms["incremental_margin"])
    opex = _term_bounds(terms["operating_costs"])
    tax = _term_bounds(terms["cash_taxes"])
    cap = _term_bounds(terms["required_capital"])
    if None in (units, price, margin, opex, tax, cap):
        return None
    vals: list[float] = []
    for u in units:  # type: ignore[union-attr]
        for p in price:  # type: ignore[union-attr]
            for m in margin:  # type: ignore[union-attr]
                for oc in opex:  # type: ignore[union-attr]
                    for ct in tax:  # type: ignore[union-attr]
                        for rc in cap:  # type: ignore[union-attr]
                            vals.append(u * p * m - oc - ct - rc)
    currency = terms["realized_revenue_per_unit"].get("currency") or terms["eligible_units"].get("currency") or "NA"
    unit = terms["realized_revenue_per_unit"].get("unit") or "USD"
    return {
        "kind": "net",
        "low": min(vals),
        "high": max(vals),
        "unit": unit,
        "currency": currency if isinstance(currency, str) else "NA",
    }


def assemble_driver_bridge(
    instance: Mapping[str, Any],
    assigned: Sequence[ChannelAssignment],
    *,
    fact_id: str,
    company_id: str,
    product_status_hint: str | None = None,
) -> dict[str, Any]:
    """Assemble ``driver_bridge.v1``. Product is net-only; never ``gross_only``."""

    roles = {c.id: c.role for c in assigned}
    rd_countable = roles.get("revenue_demand") == "earnings_countable"
    channel = "revenue_demand" if "revenue_demand" in roles or rd_countable else (
        assigned[0].id if assigned else "revenue_demand"
    )
    unlabelled = False
    terms: dict[str, Any] = {tid: _absent_term(tid) for tid in BRIDGE_TERM_IDS}

    if rd_countable:
        metric = instance.get("metric")
        stage = instance.get("demand_stage")
        claim = instance.get("economic_claim_class")
        stated = instance.get("stated_amount") if isinstance(instance.get("stated_amount"), Mapping) else None
        qty = instance.get("stated_quantity") if isinstance(instance.get("stated_quantity"), Mapping) else None
        if (
            isinstance(stated, Mapping)
            and metric == "units"
            and stage in ("bookings", "recognized_revenue")
            and stated.get("form") in ("point", "range")
        ):
            converted = _term_from_quantity(stated, "/stated_amount")
            if converted is None:
                unlabelled = True
            else:
                terms["eligible_units"] = converted
        if (
            isinstance(qty, Mapping)
            and claim == "funded_demand"
            and qty.get("form") in ("point", "range")
        ):
            converted = _term_from_quantity(qty, "/stated_quantity")
            if converted is None:
                unlabelled = True
            else:
                terms["eligible_units"] = converted
        for tid in BRIDGE_TERM_IDS:
            raw = instance.get(tid)
            if isinstance(raw, Mapping) and raw.get("form") in ("point", "range", "interval", "absent", "assumption"):
                converted = _term_from_quantity(raw, f"/{tid}")
                if converted is None:
                    unlabelled = True
                else:
                    terms[tid] = converted
            elif raw is not None and not isinstance(raw, Mapping):
                unlabelled = True
            elif isinstance(raw, Mapping) and "form" not in raw and (
                "value" in raw or "low" in raw
            ):
                unlabelled = True

    forms = [terms[t].get("form") for t in BRIDGE_TERM_IDS]
    if not rd_countable:
        status = product_status_hint or "not_applicable_channel"
        product = None
        # Case C: option_path still surfaces the six absent terms.
        option_countable = roles.get("strategic_option") == "earnings_countable"
        emit_terms = option_countable or status == "withheld_term_absent"
        return {
            "schema": "driver_bridge.v1",
            "authority": "context_only",
            "fact_id": fact_id,
            "company_id": company_id,
            "channel": "revenue_demand" if emit_terms else channel,
            "product_status": "not_applicable_channel",
            "product": None,
            "terms": terms if emit_terms else None,
        }
    if unlabelled or any(f not in ("point", "interval", "range", "absent", "assumption") for f in forms):
        status = "withheld_unlabelled_assumption"
        product = None
        # Do not emit unlabelled number objects (schema-invalid). Keep typed terms.
    elif any(f == "assumption" for f in forms):
        status = "withheld_labelled_assumption"
        product = None
    elif any(f == "absent" for f in forms):
        status = "withheld_term_absent"
        product = None
    else:
        # Normalize range -> interval already done in _term_from_quantity.
        status = "computed"
        product = _compute_product(terms)
        if product is None:
            status = "withheld_term_absent"
    return {
        "schema": "driver_bridge.v1",
        "authority": "context_only",
        "fact_id": fact_id,
        "company_id": company_id,
        "channel": "revenue_demand",
        "product_status": status,
        "product": product,
        "terms": terms,
    }


def assemble_not_yet_quantifiable(
    *,
    fact_id: str,
    company_id: str,
    assigned: Sequence[ChannelAssignment],
    reason: str,
    missing_terms: Sequence[str],
    instance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble ``not_yet_quantifiable.v1`` (section 4.8)."""

    evidence = dict(_NYQ_EVIDENCE.get(reason, _NYQ_EVIDENCE["driver_bridge_term_absent"]))
    if reason == "authorization_without_execution" and instance and instance.get("novelty") == "corrected_fact":
        evidence["description"] = "executed repurchase amount and net dilution against the corrected authorization"
    channels_touched = [
        {"id": c.id, "role": "watch_only"} for c in assigned if c.id != MARKET_ONLY
    ]
    display = _nyq_display(reason, instance or {}, assigned)
    return {
        "schema": "not_yet_quantifiable.v1",
        "fact_id": fact_id,
        "company_id": company_id,
        "channels_touched": channels_touched,
        "earnings_head": "withheld",
        "reason": reason,
        "missing_terms": list(missing_terms),
        "next_discriminating_evidence": evidence,
        "display_words": display,
    }


def _nyq_display(reason: str, instance: Mapping[str, Any], assigned: Sequence[ChannelAssignment]) -> str:
    if reason == "authorization_without_execution":
        inc = instance.get("incremental_amount") if isinstance(instance.get("incremental_amount"), Mapping) else None
        horizon = instance.get("horizon_period") if isinstance(instance.get("horizon_period"), Mapping) else None
        year = horizon.get("year") if horizon else None
        value = inc.get("value") if inc else None
        if instance.get("novelty") == "corrected_fact":
            return "This packet corrects the prior authorization fact; executed amount remains not stated."
        if isinstance(value, (int, float)) and year:
            billions = value / 1_000_000_000
            if billions == int(billions):
                mag = str(int(billions))
            else:
                mag = str(billions)
            return (
                f"Additional authorization of {mag} billion USD is on the packet through fiscal {year}; "
                "executed amount is not stated. Operating revenue is not on this packet."
            )
        return "Authorization is on the packet; executed amount is not stated. Operating revenue is not on this packet."
    if reason == "addressable_market_not_funded":
        return "Addressable-market size is on the packet; funded demand is not. Earnings-head demand is withheld."
    if reason == "claim_class_none_stated":
        return "No economic claim class is stated; channels stay empty until a funded, option, or duration claim is named."
    if reason == "attention_proxy_only":
        return "Adoption-proxy language is on the packet; funded demand is not. Downloads are attention, not profit receipts."
    if reason == "commentary_only":
        return "Commentary does not assign an earnings-head channel."
    name = instance.get("object_name") or "The announced object"
    return (
        f"{name} is an announced product path; funded demand, retained economics, "
        "and duration evidence are not on this packet."
    )


def assemble_duration_scenarios(assigned: Sequence[ChannelAssignment]) -> dict[str, Any] | None:
    """Assemble ``duration_scenario_set.v1`` with ``weights_status=forbidden_in_v1``."""

    ids = [c.id for c in assigned if c.id in ("strategic_option", "moat_duration")]
    if not ids:
        return None
    # unique, assign order
    seen: list[str] = []
    for i in ids:
        if i not in seen:
            seen.append(i)
    scenarios = [
        {
            "id": sid,
            "evidence_needed_before_weight": list(_DURATION_EVIDENCE[sid]),
            "who_would_rule": WHO_WOULD_RULE,
        }
        for sid in DURATION_SCENARIO_IDS
    ]
    return {
        "schema": "duration_scenario_set.v1",
        "channel_ids": seen,
        "weights_status": "forbidden_in_v1",
        "scenarios": scenarios,
    }


def _unmapped_block(instance: Mapping[str, Any], news_event_class: str, reason: str) -> dict[str, Any]:
    return {
        "schema": "unmapped_event.v1",
        "reason": reason,
        "news_event_class": news_event_class[:32] if news_event_class else "unclassified",
        "strategic_review_status": "eligible",
        "next_discriminating_evidence": {
            "description": (
                "an issuer operating fact (guidance, execution, funded contract, or product milestone) "
                "spanning a primary source"
            ),
            "named_window": "decision_cut_session",
            "source_owner": "issuer_filing",
        },
    }


def _walk_forbidden(obj: Any) -> list[str]:
    hits: list[str] = []
    if isinstance(obj, Mapping):
        for key in obj:
            if key in FORBIDDEN_KEYS:
                hits.append(str(key))
            hits.extend(_walk_forbidden(obj[key]))
    elif isinstance(obj, list):
        for item in obj:
            hits.extend(_walk_forbidden(item))
    return hits


def enforce_invariants(
    *,
    input_schema: str,
    assigned: Sequence[ChannelAssignment],
    mapping_status: str,
    issuer_role: Any,
    novelty: Any,
    inherits_from_fact_id: str | None,
    supersedes_fact_id: Any,
    payload: Mapping[str, Any],
) -> None:
    """Hard-fail mapper bugs. Each code is a closed ``CODES`` member."""

    ids = [c.id for c in assigned]
    roles = {c.id: c.role for c in assigned}
    has_market = MARKET_ONLY in ids
    has_earnings = any(i in EARNINGS_HEAD_CHANNELS for i in ids)
    if has_market and has_earnings:
        raise MechanismsError("INVARIANT_I_MO_1", "market_only disjoint from earnings_head channels")
    if input_schema in (T1, T2, T3) and has_market:
        raise MechanismsError("INVARIANT_I_MO_2", "market_only forbidden on T1/T2/T3")
    countable_duration = [
        cid for cid in ("strategic_option", "moat_duration") if roles.get(cid) == "earnings_countable"
    ]
    if len(countable_duration) > 1:
        raise MechanismsError("INVARIANT_I_DOUBLE_1", "option and moat both earnings_countable")
    if issuer_role == "incidental" and input_schema in (T1, T2, T3):
        if mapping_status != "ineligible_role" or assigned:
            raise MechanismsError(
                "INVARIANT_I_ROLE_1",
                "incidental issuer must be ineligible_role with empty channels",
            )
    if novelty == "corrected_fact" and input_schema in (T1, T2, T3):
        if isinstance(supersedes_fact_id, str) and FACT_ID_RE.match(supersedes_fact_id):
            if inherits_from_fact_id != supersedes_fact_id:
                raise MechanismsError(
                    "INVARIANT_I_CORR_1",
                    "inherits_from_fact_id must equal supersedes_fact_id",
                )
    leaked = _walk_forbidden(payload)
    if leaked:
        raise MechanismsError("INVARIANT_I_ORIG_1", f"forbidden keys leaked: {sorted(set(leaked))}")


def map_event(
    instance: Mapping[str, Any] | Any,
    library: Mapping[str, Any] | None = None,
    library_path: str | Path | None = None,
) -> ChannelMapping:
    """Map one frozen news_impact fact onto ``channel_mapping.v1``.

    Algorithm: A2 section 4.11. ``channel_hint`` is peeled off before the
    rule sweep (I-HINT-1) and compared afterwards for ``V_HINT_NOT_MAP``.
    """

    if not isinstance(instance, Mapping):
        raise MechanismsError("INSTANCE_NOT_MAPPING", "map_event requires a JSON object")
    lib = dict(library) if library is not None else load_library(library_path)
    cleaned, stripped = strip_forbidden_fields(dict(instance))
    if not isinstance(cleaned, dict):
        raise MechanismsError("INSTANCE_NOT_MAPPING", "stripped instance is not an object")
    injections = tuple(_scan_injections(cleaned))
    hint = cleaned.pop("channel_hint", None)  # never a mapper input
    working: dict[str, Any] = cleaned

    fired: list[str] = []
    assigned: list[ChannelAssignment] = []
    status: str | None = None
    nyq_reason: str | None = None
    want_scenarios = False
    bridge_hint: str | None = None
    sticky = False

    for rule in _sorted_rules(lib):
        when = rule.get("when")
        if not _match_when(when, working):
            continue
        rid = str(rule["rule_id"])
        fired.append(rid)
        if sticky:
            assigned = _apply_remove(assigned, rule.get("remove") or [])
            continue
        if "assign" in rule:
            assigned = _upsert_assign(assigned, rule.get("assign") or [])
        if rule.get("remove"):
            assigned = _apply_remove(assigned, rule.get("remove") or [])
        if rule.get("set_status") and status is None:
            status = str(rule["set_status"])
            if status in STICKY_STATUSES and int(rule.get("priority", 0)) <= 20:
                sticky = True
                assigned = []
        if rule.get("set_nyq"):
            nyq_reason = str(rule["set_nyq"])
        if rule.get("set_scenarios"):
            want_scenarios = True
        if rule.get("set_bridge"):
            bridge_hint = str(rule["set_bridge"])

    input_schema = working.get("schema")
    if input_schema not in INPUT_SCHEMAS:
        input_schema = UNMAPPED_SCHEMA
    fact_id = working.get("fact_id") if isinstance(working.get("fact_id"), str) else "fact_000000000000000000000000"
    company_id = working.get("company_id") if isinstance(working.get("company_id"), str) else "cik:0000000001"
    novelty = working.get("novelty")
    issuer_role = working.get("issuer_role")
    supersedes = working.get("supersedes_fact_id")

    inherits: str | None = None
    if novelty == "corrected_fact" and isinstance(supersedes, str) and FACT_ID_RE.match(supersedes):
        inherits = supersedes
        if status is None and input_schema == T1:
            status = "superseded_inherit"

    if status is None:
        if assigned:
            status = "mapped"
        elif input_schema == UNMAPPED_SCHEMA:
            nec = working.get("news_event_class")
            status = "unmapped_novel" if nec in MARKET_CLASS else "strategic_review"
        else:
            status = "strategic_review"

    earnings_head = "open" if any(c.role == "earnings_countable" for c in assigned) else "withheld"

    emit_bridge = not (
        (status in ("unmapped_novel", "ineligible_role", "strategic_review") and not assigned)
        or (status == "unmapped_novel")
    )
    # Case E: NYQ TAM has empty channels but still emits a not-applicable bridge.
    if status == "not_yet_quantifiable" and not assigned:
        emit_bridge = True
    if status == "unmapped_novel":
        emit_bridge = False

    roles = {c.id: c.role for c in assigned}
    if nyq_reason is None and status == "not_yet_quantifiable":
        if working.get("economic_claim_class") == "none_stated":
            nyq_reason = "claim_class_none_stated"
        else:
            nyq_reason = "driver_bridge_term_absent"

    bridge: dict[str, Any] | None = None
    if emit_bridge:
        bridge = assemble_driver_bridge(
            working,
            assigned,
            fact_id=fact_id,
            company_id=company_id,
            product_status_hint=bridge_hint,
        )
        if (
            nyq_reason is None
            and bridge.get("product_status") == "withheld_term_absent"
            and roles.get("revenue_demand") == "earnings_countable"
        ):
            nyq_reason = "driver_bridge_term_absent"

    missing: list[str] = []
    if nyq_reason == "driver_bridge_term_absent" and bridge and isinstance(bridge.get("terms"), dict):
        missing = [t for t in BRIDGE_TERM_IDS if bridge["terms"].get(t, {}).get("form") == "absent"]
    elif nyq_reason == "addressable_market_not_funded":
        missing = ["eligible_units", "realized_revenue_per_unit", "incremental_margin"]

    nyq_obj: dict[str, Any] | None = None
    if nyq_reason is not None:
        nyq_obj = assemble_not_yet_quantifiable(
            fact_id=fact_id,
            company_id=company_id,
            assigned=assigned,
            reason=nyq_reason,
            missing_terms=missing,
            instance=working,
        )

    scenarios: dict[str, Any] | None = None
    if want_scenarios:
        scenarios = assemble_duration_scenarios(assigned)

    named = _named_quantities(working, lib, assigned)
    if status in ("ineligible_role", "strategic_review") and not assigned:
        named = {}

    unmapped: dict[str, Any] | None = None
    display: str | None = None
    if input_schema == UNMAPPED_SCHEMA or status == "unmapped_novel":
        nec = working.get("news_event_class") if isinstance(working.get("news_event_class"), str) else "unclassified"
        um_reason = "no_matching_template"
        if nec == "unclassified" or working.get("reason") == "classify_event_none":
            um_reason = "classify_event_none" if nec == "unclassified" else "no_matching_template"
        if issuer_role == "incidental":
            um_reason = "role_incidental"
        unmapped = _unmapped_block(working, str(nec), um_reason)
        display = (
            "This item is a rating-class headline without an accepted operating template. "
            "It stays on the market-hypothesis head only."
            if any(c.id == MARKET_ONLY for c in assigned)
            else "This item has no accepted operating template and stays eligible for strategic review."
        )

    warnings: list[MappingWarning] = []
    if isinstance(hint, str):
        assigned_ids = {c.id for c in assigned}
        if hint not in assigned_ids:
            warnings.append(
                MappingWarning(
                    code=V_HINT_NOT_MAP,
                    detail=f"channel_hint={hint} disagrees with assigned {sorted(assigned_ids)}",
                )
            )

    payload_preview = {
        "assigned_channels": [c.to_dict() for c in assigned],
        "named_quantities": named,
        "driver_bridge": bridge,
        "not_yet_quantifiable": nyq_obj,
        "duration_scenarios": scenarios,
    }
    enforce_invariants(
        input_schema=str(input_schema),
        assigned=assigned,
        mapping_status=str(status),
        issuer_role=issuer_role,
        novelty=novelty,
        inherits_from_fact_id=inherits,
        supersedes_fact_id=supersedes,
        payload=payload_preview,
    )

    mapping = ChannelMapping(
        schema="channel_mapping.v1",
        library_version=LIBRARY_NAME,
        rule_ids=tuple(fired),
        fact_id=str(fact_id),
        company_id=str(company_id),
        input_schema=str(input_schema),
        assigned_channels=tuple(assigned),
        mapping_status=str(status),
        earnings_head=earnings_head,
        prophet_flags=dict(PROPHET_FLAGS),
        unsolicited_instruction_detected=False,
        driver_bridge=bridge,
        not_yet_quantifiable=nyq_obj,
        duration_scenarios=scenarios,
        inherits_from_fact_id=inherits,
        unmapped=unmapped,
        named_quantities=named or None,
        display_words=display,
        warnings=tuple(warnings),
        stripped_fields=tuple(stripped),
        injection_findings=injections,
    )
    leaked = _walk_forbidden(mapping.to_dict())
    if leaked:
        raise MechanismsError("INVARIANT_I_ORIG_1", f"forbidden keys leaked: {sorted(set(leaked))}")
    return mapping


__all__ = [
    "CODES",
    "FORBIDDEN_KEYS",
    "LIBRARY_NAME",
    "V_HINT_NOT_MAP",
    "ChannelAssignment",
    "ChannelMapping",
    "MappingWarning",
    "MechanismsError",
    "assemble_driver_bridge",
    "assemble_duration_scenarios",
    "assemble_not_yet_quantifiable",
    "canonical_json",
    "enforce_invariants",
    "load_channel_mapping_schema",
    "load_driver_bridge_schema",
    "load_library",
    "map_event",
    "strip_forbidden_fields",
]
