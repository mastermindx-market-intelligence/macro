"""Pure owner-preserving composition for the Finance Sector Intelligence read model.

display-only, never a score, never a rank, never a recommendation

This module turns already-read owner payloads into a
``finance_intelligence_read_model.v1`` document. The composer is deliberately
pure: no I/O, no network, no store, no env, no clock reads
(``generated_at`` / ``knowledge_cutoff`` are parameters; ``common_as_of`` is the
minimum over the input as-of dates actually consumed, never ``now``).

It never rewrites an owner value (every emitted METRIC keeps
``native_metric_name`` and the owner's value/unit beside
``normalized_metric_family``), never infers a signal direction (the composer
only reads an explicit ``direction`` field off the owner observation), and never
emits a forbidden authority / score / rank / attractiveness / composite field.

The four analytical planes stay separate (operating, expectations, valuation,
price recognition); the three system views stay separate (contractual flow,
infrastructure access, public-equity economics). Conflicts are surfaced as
two-sided records with resolution ``UNRESOLVED_BY_DESIGN`` — never averaged.

See ``research/finance/FINANCE_EXPECTATIONS_VALUATION_AND_PRICE_JOIN_CONTRACT_2026-09-23.md``
for the clock rule: at read time preserve market close, consensus as-of,
filing/guidance publication, valuation observation, and source generation;
``a page generated today cannot make stale consensus current``.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Iterable, Mapping, Sequence


# ---------------------------------------------------------------------------
# Frozen input contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FinanceOwnerInputs:
    sector_dossier: Mapping[str, Any] | None
    theme_evidence: Sequence[Mapping[str, Any]]
    financial_packets: Mapping[str, Mapping[str, Any]]
    expectation_observations: Mapping[str, Sequence[Mapping[str, Any]]]
    market_observations: Mapping[str, Sequence[Mapping[str, Any]]]
    basket_context: Mapping[str, Mapping[str, Any]]
    macro_context: Mapping[str, Any]
    identity_bindings: Mapping[str, Mapping[str, Any]]
    source_records: Sequence[Mapping[str, Any]]
    regime_breaks: Sequence[Mapping[str, Any]]
    slice_catalog: Sequence[Mapping[str, Any]]
    rights_snapshot: Mapping[str, str]


# ---------------------------------------------------------------------------
# Closed vocabularies (mirror finance_intelligence_read_model.v1 schema)
# ---------------------------------------------------------------------------


# 52 finance subtheme slice ids, alphabetically sorted for determinism.
_FINANCE_SLICE_IDS: tuple[str, ...] = (
    "ach_instant_b2b",
    "active_asset_managers",
    "agentic_ai_finance_workflow",
    "alternative_asset_managers",
    "bdc_direct_lending_vehicles",
    "card_networks",
    "cards_consumer_credit",
    "claims_insurance_data_workflow",
    "clearing_ccp_csd",
    "commercial_specialty_pc",
    "community_local_banks",
    "core_banking_financial_software",
    "cre_credit_cycle",
    "cross_border_remittance",
    "custody_asset_servicing",
    "deposit_franchise_quality",
    "digital_banks_neobanks",
    "digital_custody_tokenized_securities",
    "electronic_market_makers",
    "embedded_finance_baas",
    "equity_debt_capital_markets",
    "exchanges_trading_venues",
    "fraud_identity_tokenization",
    "fund_admin_middle_backoffice",
    "gateways_orchestration",
    "indices_benchmarks_etf_plumbing",
    "insurance_brokers",
    "issuer_processing",
    "life_annuity_spread",
    "market_reference_data",
    "merchant_acquiring_processing",
    "mga_delegated_underwriting",
    "mortgage_originators",
    "mortgage_servicers_msr",
    "mna_advisory",
    "nim_curve_normalization",
    "open_banking_api_finance",
    "options_derivatives_ecosystem",
    "passive_etf_asset_managers",
    "personal_pc_insurance",
    "prime_brokerage_securities_lending",
    "private_credit_managers",
    "ratings_credit_information",
    "regional_superregional_banks",
    "regtech_kyc_aml",
    "reinsurance",
    "retirement_recordkeeping",
    "financial_cybersecurity",
    "specialty_auto_equipment_finance",
    "stablecoin_infrastructure",
    "universal_money_center_banks",
    "wealth_platforms_rias",
)

_FIRST_VERTICAL_SLICE_IDS: frozenset[str] = frozenset(
    {
        "card_networks",
        "merchant_acquiring_processing",
        "issuer_processing",
        "exchanges_trading_venues",
        "custody_asset_servicing",
        "market_reference_data",
        "ratings_credit_information",
        "indices_benchmarks_etf_plumbing",
    }
)

# Slice -> domain mapping (closed vocab from the schema's ``$defs.domain_id``).
_SLICE_TO_DOMAIN: dict[str, str] = {
    "ach_instant_b2b": "payments",
    "active_asset_managers": "asset_wealth",
    "agentic_ai_finance_workflow": "software_trust",
    "alternative_asset_managers": "asset_wealth",
    "bdc_direct_lending_vehicles": "asset_wealth",
    "card_networks": "payments",
    "cards_consumer_credit": "banking_funding",
    "claims_insurance_data_workflow": "insurance",
    "clearing_ccp_csd": "capital_markets",
    "commercial_specialty_pc": "insurance",
    "community_local_banks": "banking_funding",
    "core_banking_financial_software": "software_trust",
    "cre_credit_cycle": "banking_funding",
    "cross_border_remittance": "payments",
    "custody_asset_servicing": "capital_markets",
    "deposit_franchise_quality": "banking_funding",
    "digital_banks_neobanks": "banking_funding",
    "digital_custody_tokenized_securities": "structural_disruption",
    "electronic_market_makers": "capital_markets",
    "embedded_finance_baas": "software_trust",
    "equity_debt_capital_markets": "capital_markets",
    "exchanges_trading_venues": "capital_markets",
    "fraud_identity_tokenization": "software_trust",
    "fund_admin_middle_backoffice": "asset_wealth",
    "gateways_orchestration": "payments",
    "indices_benchmarks_etf_plumbing": "capital_markets",
    "insurance_brokers": "insurance",
    "issuer_processing": "payments",
    "life_annuity_spread": "insurance",
    "market_reference_data": "capital_markets",
    "merchant_acquiring_processing": "payments",
    "mga_delegated_underwriting": "insurance",
    "mortgage_originators": "banking_funding",
    "mortgage_servicers_msr": "banking_funding",
    "mna_advisory": "capital_markets",
    "nim_curve_normalization": "banking_funding",
    "open_banking_api_finance": "software_trust",
    "options_derivatives_ecosystem": "capital_markets",
    "passive_etf_asset_managers": "asset_wealth",
    "personal_pc_insurance": "insurance",
    "prime_brokerage_securities_lending": "capital_markets",
    "private_credit_managers": "asset_wealth",
    "ratings_credit_information": "capital_markets",
    "regional_superregional_banks": "banking_funding",
    "regtech_kyc_aml": "software_trust",
    "reinsurance": "insurance",
    "retirement_recordkeeping": "asset_wealth",
    "financial_cybersecurity": "software_trust",
    "specialty_auto_equipment_finance": "banking_funding",
    "stablecoin_infrastructure": "structural_disruption",
    "universal_money_center_banks": "banking_funding",
    "wealth_platforms_rias": "asset_wealth",
}

# EN/ZH name catalog for every slice (closed — verbatim names from the atlas).
_SLICE_NAMES: dict[str, tuple[str, str]] = {
    "ach_instant_b2b": ("ACH / instant / B2B rails", "ACH / 实时 / B2B 支付通道"),
    "active_asset_managers": ("Active asset managers", "主动资产管理"),
    "agentic_ai_finance_workflow": ("Agentic AI for finance workflow", "金融工作流的代理式 AI"),
    "alternative_asset_managers": ("Alternative asset managers", "另类资产管理"),
    "bdc_direct_lending_vehicles": ("BDC / direct lending vehicles", "BDC / 直接贷款载体"),
    "card_networks": ("Card networks", "卡组织"),
    "cards_consumer_credit": ("Cards and consumer credit", "信用卡与消费信贷"),
    "claims_insurance_data_workflow": ("Claims and insurance data workflow", "理赔与保险数据工作流"),
    "clearing_ccp_csd": ("Clearing, CCP and CSD", "清算、CCP 与 CSD"),
    "commercial_specialty_pc": ("Commercial and specialty P&C", "商业与特种财险"),
    "community_local_banks": ("Community and local banks", "社区与地方银行"),
    "core_banking_financial_software": ("Core banking and financial software", "核心银行与金融软件"),
    "cre_credit_cycle": ("CRE credit cycle", "商业地产信贷周期"),
    "cross_border_remittance": ("Cross-border remittance", "跨境汇款"),
    "custody_asset_servicing": ("Custody and asset servicing", "托管与资产服务"),
    "deposit_franchise_quality": ("Deposit franchise quality", "存款特许经营权质量"),
    "digital_banks_neobanks": ("Digital banks and neobanks", "数字银行与新银行"),
    "digital_custody_tokenized_securities": ("Digital custody / tokenized securities", "数字托管 / 代币化证券"),
    "electronic_market_makers": ("Electronic market makers", "电子做市商"),
    "embedded_finance_baas": ("Embedded finance and BaaS", "嵌入式金融与银行即服务"),
    "equity_debt_capital_markets": ("Equity / debt capital markets", "股票 / 债券资本市场"),
    "exchanges_trading_venues": ("Exchanges and trading venues", "交易所与交易场所"),
    "fraud_identity_tokenization": ("Fraud, identity and tokenization", "反欺诈、身份与令牌化"),
    "fund_admin_middle_backoffice": ("Fund administration and middle / back office", "基金中后台"),
    "gateways_orchestration": ("Gateways and orchestration", "支付网关与编排"),
    "indices_benchmarks_etf_plumbing": ("Indices, benchmarks and ETF plumbing", "指数、基准与 ETF 基础设施"),
    "insurance_brokers": ("Insurance brokers", "保险经纪"),
    "issuer_processing": ("Issuer processing", "发卡处理"),
    "life_annuity_spread": ("Life / annuity spread", "寿险 / 年金利差"),
    "market_reference_data": ("Market reference data", "市场参考数据"),
    "merchant_acquiring_processing": ("Merchant acquiring and processing", "商户收单与处理"),
    "mga_delegated_underwriting": ("MGA / delegated underwriting", "MGA / 委托核保"),
    "mortgage_originators": ("Mortgage originators", "按揭发起"),
    "mortgage_servicers_msr": ("Mortgage servicers / MSR", "按揭服务 / MSR"),
    "mna_advisory": ("M&A advisory", "并购顾问"),
    "nim_curve_normalization": ("NIM and curve normalization", "净息差与曲线常态化"),
    "open_banking_api_finance": ("Open banking and API finance", "开放银行与 API 金融"),
    "options_derivatives_ecosystem": ("Options and derivatives ecosystem", "期权与衍生品生态"),
    "passive_etf_asset_managers": ("Passive and ETF asset managers", "被动与 ETF 资产管理"),
    "personal_pc_insurance": ("Personal P&C insurance", "个人财险"),
    "prime_brokerage_securities_lending": ("Prime brokerage and securities lending", "主经纪商与证券借贷"),
    "private_credit_managers": ("Private credit managers", "私募信贷管理"),
    "ratings_credit_information": ("Ratings and credit information", "评级与信用信息"),
    "regional_superregional_banks": ("Regional and super-regional banks", "区域与跨区域银行"),
    "regtech_kyc_aml": ("Regtech / KYC / AML", "监管科技 / KYC / 反洗钱"),
    "reinsurance": ("Reinsurance", "再保险"),
    "retirement_recordkeeping": ("Retirement recordkeeping", "退休账户管理"),
    "financial_cybersecurity": ("Financial cybersecurity", "金融网络安全"),
    "specialty_auto_equipment_finance": ("Specialty auto and equipment finance", "特种汽车与设备融资"),
    "stablecoin_infrastructure": ("Stablecoin infrastructure", "稳定币基础设施"),
    "universal_money_center_banks": ("Universal and money-center banks", "综合性与大银行"),
    "wealth_platforms_rias": ("Wealth platforms and RIAs", "财富平台与 RIA"),
}

_DOMAIN_NAMES: dict[str, tuple[str, str]] = {
    "asset_wealth": ("Asset and wealth management", "资产与财富管理"),
    "banking_funding": ("Banking and funding", "银行与融资"),
    "capital_markets": ("Capital markets", "资本市场"),
    "insurance": ("Insurance", "保险"),
    "payments": ("Payments", "支付"),
    "software_trust": ("Software and trust", "软件与信任"),
    "structural_disruption": ("Structural disruption", "结构性颠覆"),
}

_SYSTEM_VIEWS: tuple[dict[str, str], ...] = (
    {
        "view_id": "contractual_flow",
        "name_en": "Contractual money and risk flow",
        "name_zh": "合同资金与风险流",
    },
    {
        "view_id": "infrastructure_access",
        "name_en": "Regulated infrastructure and access",
        "name_zh": "受监管基础设施与准入",
    },
    {
        "view_id": "public_equity_economics",
        "name_en": "Public equity economics",
        "name_zh": "上市公司经济学",
    },
)

_CONTRACTUAL_FLOW_RELATIONSHIPS = frozenset(
    {"PAYS", "SETTLES", "CLEARS", "GUARANTEES", "FUNDS", "INSURES", "LENDS", "HOLDS_CUSTODY"}
)
_INFRASTRUCTURE_ACCESS_RELATIONSHIPS = frozenset(
    {"LICENSES", "SUPERVISES", "GRANTS_ACCESS", "PUBLISHES_BENCHMARK", "RATES", "PROVIDES_DATA", "REQUIRES_MEMBERSHIP"}
)
_PUBLIC_EQUITY_RELATIONSHIPS = frozenset(
    {"EARNS_FEE_FROM", "BEARS_CREDIT_RISK_OF", "CAPTURES_SPREAD_ON", "RECOGNISES_REVENUE_FROM", "DEPENDS_ON_VOLUME_OF"}
)

_PRICE_BASIS_QUALIFIED = frozenset({"PRICE_RETURN", "TOTAL_RETURN"})

_AUTHORITY_CAPS: dict[str, bool] = {
    "rank": False,
    "gate": False,
    "size": False,
    "trade": False,
    "create_theme": False,
    "change_membership": False,
    "write_graph": False,
    "admit_source": False,
}

_FORBIDDEN_KEY_RE = re.compile(
    r"(^|_)(score|rank|attractiveness|composite)(_|$)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Small JSON / datetime helpers
# ---------------------------------------------------------------------------


def _to_iso(value: datetime | date | str) -> str:
    # Use structural checks (datetime has a ``time`` part, date does not)
    # so the function still works when the ``datetime`` symbol is
    # monkey-patched to a subclass with a narrower type.
    if hasattr(value, "hour") and hasattr(value, "minute"):
        text = value.isoformat()
        tzinfo = getattr(value, "tzinfo", None)
        if tzinfo is None:
            return text + "Z"
        return text
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _hash_inputs(inputs: FinanceOwnerInputs, composer_version: str) -> str:
    payload = {
        "composer_version": composer_version,
        "sector_dossier": inputs.sector_dossier,
        "theme_evidence": list(inputs.theme_evidence),
        "financial_packets": dict(inputs.financial_packets),
        "expectation_observations": dict(inputs.expectation_observations),
        "market_observations": dict(inputs.market_observations),
        "basket_context": dict(inputs.basket_context),
        "macro_context": inputs.macro_context,
        "identity_bindings": dict(inputs.identity_bindings),
        "source_records": list(inputs.source_records),
        "regime_breaks": list(inputs.regime_breaks),
        "slice_catalog": list(inputs.slice_catalog),
        "rights_snapshot": dict(inputs.rights_snapshot),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _parse_iso_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    # Structural check: datetime has a time component, date does not.
    # Survives a monkey-patched ``datetime`` symbol.
    if hasattr(value, "hour") and hasattr(value, "minute"):
        return value.date() if hasattr(value, "date") else None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _coerce_date(value: Any) -> date | None:
    if value is None:
        return None
    if hasattr(value, "hour") and hasattr(value, "minute"):
        return value.date() if hasattr(value, "date") else None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return _parse_iso_date(value)
    return None


def _min_date(values: Iterable[date | None]) -> date | None:
    cleaned: list[date] = []
    for v in values:
        if v is None:
            continue
        # Coerce datetime-like to date via duck typing so a subclassed or
        # monkey-patched ``datetime`` symbol cannot smuggle a datetime
        # instance into the comparison.
        if hasattr(v, "date") and callable(getattr(v, "date", None)) and not isinstance(v, type):
            try:
                v = v.date()
            except TypeError:
                pass
        if isinstance(v, date):
            cleaned.append(v)
    if not cleaned:
        return None
    return min(cleaned)


# ---------------------------------------------------------------------------
# Theme-evidence extraction
# ---------------------------------------------------------------------------


def _curation_revisions(theme_evidence: Sequence[Mapping[str, Any]]) -> list[str]:
    revisions: set[str] = set()
    for row in theme_evidence:
        revision = row.get("curation_revision") if isinstance(row, Mapping) else None
        if revision is None:
            continue
        text = str(revision).strip()
        if text:
            revisions.add(text)
    return sorted(revisions)


def _rights_profile(rights_snapshot: Mapping[str, str]) -> str:
    if not rights_snapshot:
        return "no_rights_admitted"
    families = sorted(str(k) for k in rights_snapshot)
    return "rights_snapshot:" + ",".join(families)


# ---------------------------------------------------------------------------
# Source records: rights + state coercion
# ---------------------------------------------------------------------------


def _coerce_rights_state(
    source_family: str | None,
    rights_snapshot: Mapping[str, str],
) -> str:
    if not source_family:
        return "SOURCE_RIGHTS_HELD"
    if source_family not in rights_snapshot:
        return "SOURCE_RIGHTS_HELD"
    cls = rights_snapshot.get(source_family)
    if cls == "internal_only":
        return "INTERNAL_ONLY"
    if cls == "unresolved":
        return "SOURCE_RIGHTS_HELD"
    if cls == "direct_display_ok":
        return "DIRECT_DISPLAY_OK"
    if cls == "derived_display_ok":
        return "DERIVED_DISPLAY_OK"
    return "SOURCE_RIGHTS_HELD"


def _source_record_evidence_ref(rec: Mapping[str, Any]) -> str | None:
    ref = rec.get("evidence_ref")
    if ref is None:
        rid = rec.get("record_id")
        return str(rid) if rid else None
    text = str(ref).strip()
    return text or None


def _source_record_observed_at(rec: Mapping[str, Any]) -> date | None:
    source = rec.get("source") or {}
    if isinstance(source, Mapping):
        return _coerce_date(source.get("observed_at"))
    return None


def _extract_source_record_extras(rec: Mapping[str, Any]) -> dict[str, Any]:
    """Extract private (underscore-prefixed) fields used to drive the
    company-row composition path. The composer reads them BEFORE stripping
    the record to its schema-strict shape, so anything the production
    schema does not accept must NOT appear in the final document."""
    extras: dict[str, Any] = {}
    for key, value in rec.items():
        if isinstance(key, str) and key.startswith("_"):
            extras[key] = value
    return extras


def _source_records_block(
    inputs: FinanceOwnerInputs,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (cleaned_records, extras_per_record).

    ``extras_per_record`` mirrors the cleaned list one-to-one with the
    private underscore-prefixed fields the source record carried BEFORE
    stripping. The composer uses them to wire source records into the
    company-row construction path even though the final document never
    admits them.
    """
    out: list[dict[str, Any]] = []
    extras_out: list[dict[str, Any]] = []
    allowed_top_level = {
        "record_id",
        "source",
        "business_scope",
        "metric",
        "observation",
        "temporal",
        "limitations",
        "identity_state",
        "rights_state",
        "statement_mode",
        "correction",
        "evidence_ref",
        "excerpt",
    }
    for raw in inputs.source_records:
        extras = _extract_source_record_extras(raw)
        extras_out.append(extras)
        rec = {key: value for key, value in dict(raw).items() if key in allowed_top_level}
        source = rec.get("source") or {}
        source_family = source.get("source_family") if isinstance(source, Mapping) else None
        rights_state = _coerce_rights_state(source_family, inputs.rights_snapshot)
        rec["rights_state"] = rights_state
        if rights_state in ("SOURCE_RIGHTS_HELD", "INTERNAL_ONLY"):
            rec["excerpt"] = None
        # Strip any unallowed keys from nested objects (metric, source, etc.).
        rec["metric"] = _strip_metric_extras(rec.get("metric"))
        rec["source"] = _strip_source_extras(rec.get("source"))
        rec["observation"] = _strip_observation_extras(rec.get("observation"))
        rec["temporal"] = _strip_temporal_extras(rec.get("temporal"))
        rec["limitations"] = _strip_limitations_extras(rec.get("limitations"))
        rec["correction"] = _strip_correction_extras(rec.get("correction"))
        out.append(rec)
    return out, extras_out


def _strip_metric_extras(metric: Any) -> dict[str, Any]:
    if not isinstance(metric, Mapping):
        return {
            "native_metric_name": "",
            "normalized_metric_family": "",
            "value": None,
            "unit": None,
            "currency": None,
            "period_start": None,
            "period_end": None,
            "measurement_class": "QUALITATIVE",
            "numerator": None,
            "denominator": None,
            "gross_net_basis": "NOT_APPLICABLE",
            "average_end": "NOT_APPLICABLE",
            "reported_derived_estimated": "REPORTED",
        }
    allowed = {
        "native_metric_name",
        "normalized_metric_family",
        "value",
        "unit",
        "currency",
        "period_start",
        "period_end",
        "measurement_class",
        "numerator",
        "denominator",
        "gross_net_basis",
        "average_end",
        "reported_derived_estimated",
    }
    return {key: value for key, value in metric.items() if key in allowed}


def _strip_source_extras(source: Any) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        return {
            "publisher": "",
            "source_family": "",
            "source_uri": "",
            "locator": "",
            "published_at": None,
            "published_at_grain": "UNKNOWN",
            "observed_at": "1970-01-01",
            "retained_at": None,
            "retention_ref": None,
            "native_digest": None,
        }
    allowed = {
        "publisher",
        "source_family",
        "source_uri",
        "locator",
        "published_at",
        "published_at_grain",
        "observed_at",
        "retained_at",
        "retention_ref",
        "native_digest",
    }
    return {key: value for key, value in source.items() if key in allowed}


def _strip_observation_extras(obs: Any) -> dict[str, Any]:
    if not isinstance(obs, Mapping):
        return {
            "value": None,
            "value_high": None,
            "period_start": None,
            "period_end": None,
            "reported_derived_estimated": "REPORTED",
            "precision": None,
        }
    allowed = {
        "value",
        "value_high",
        "period_start",
        "period_end",
        "reported_derived_estimated",
        "precision",
    }
    return {key: value for key, value in obs.items() if key in allowed}


def _strip_temporal_extras(temporal: Any) -> dict[str, Any]:
    if not isinstance(temporal, Mapping):
        return {"business_valid_from": "1970-01-01", "business_valid_to": None}
    allowed = {"business_valid_from", "business_valid_to"}
    return {key: value for key, value in temporal.items() if key in allowed}


def _strip_limitations_extras(limitations: Any) -> dict[str, Any]:
    if not isinstance(limitations, Mapping):
        return {
            "establishes": "",
            "does_not_establish": "",
            "coverage": "",
            "source_dependence": "",
            "expiry_trigger": "",
        }
    allowed = {
        "establishes",
        "does_not_establish",
        "coverage",
        "source_dependence",
        "expiry_trigger",
    }
    return {key: value for key, value in limitations.items() if key in allowed}


def _strip_correction_extras(correction: Any) -> dict[str, Any]:
    if not isinstance(correction, Mapping):
        return {"predecessor_record_id": None, "reason": None}
    allowed = {"predecessor_record_id", "reason"}
    return {key: value for key, value in correction.items() if key in allowed}


# ---------------------------------------------------------------------------
# Slice state machines
# ---------------------------------------------------------------------------


def _slice_inputs_for(
    slice_id: str,
    inputs: FinanceOwnerInputs,
) -> dict[str, Any]:
    catalog = next((c for c in inputs.slice_catalog if c.get("slice_id") == slice_id), None)
    return {
        "catalog": catalog or {},
        "expectation_obs": list(inputs.expectation_observations.get(slice_id, []) or []),
        "market_obs": list(inputs.market_observations.get(slice_id, []) or []),
        "basket": dict(inputs.basket_context.get(slice_id, {}) or {}),
        "macro": (inputs.macro_context or {}),
        "regime": [rb for rb in inputs.regime_breaks if isinstance(rb, Mapping) and rb.get("slice_id") == slice_id],
    }


def _name_pair(slice_id: str) -> tuple[str, str]:
    if slice_id in _SLICE_NAMES:
        return _SLICE_NAMES[slice_id]
    return (slice_id.replace("_", " ").capitalize(), slice_id.replace("_", " "))


def _domain_of(slice_id: str) -> str:
    return _SLICE_TO_DOMAIN.get(slice_id, "capital_markets")


def _direction(obs: Mapping[str, Any]) -> str | None:
    direction = obs.get("direction")
    if direction is None:
        return None
    text = str(direction).strip().upper()
    if text in ("UP", "DOWN", "FLAT", "NEUTRAL"):
        return text
    return None


def _observation_value(obs: Mapping[str, Any]) -> Any:
    if "value" in obs:
        return obs.get("value")
    if "metric" in obs and isinstance(obs["metric"], Mapping):
        return obs["metric"].get("value")
    return None


def _observation_unit(obs: Mapping[str, Any]) -> str | None:
    unit = obs.get("unit")
    if unit is not None:
        return str(unit)
    metric = obs.get("metric")
    if isinstance(metric, Mapping):
        unit = metric.get("unit")
        if unit is not None:
            return str(unit)
    return None


def _plane_evidence_refs(
    expectation_obs: Sequence[Mapping[str, Any]],
    market_obs: Sequence[Mapping[str, Any]],
    source_records: Sequence[Mapping[str, Any]],
) -> list[str]:
    refs: set[str] = set()
    for obs in expectation_obs:
        ref = obs.get("source") if isinstance(obs, Mapping) else None
        if ref:
            refs.add(str(ref))
    for obs in market_obs:
        if isinstance(obs, Mapping):
            ref = obs.get("source") or obs.get("evidence_ref")
            if ref:
                refs.add(str(ref))
    for rec in source_records:
        rid = rec.get("record_id") if isinstance(rec, Mapping) else None
        if rid:
            refs.add(str(rid))
    return sorted(refs)


def _plane_clock(obs: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if obs is None:
        return None
    observed = _coerce_date(obs.get("as_of")) or _coerce_date(obs.get("observed_at"))
    if observed is None:
        return None
    published = _coerce_date(obs.get("published_at"))
    return {
        "published_at": published.isoformat() if published else None,
        "published_at_grain": "DAY",
        "observed_at": observed.isoformat(),
        "effective_at": _coerce_date(obs.get("effective_at")).isoformat()
        if _coerce_date(obs.get("effective_at"))
        else None,
    }


def _empty_metric() -> dict[str, Any]:
    return {
        "native_metric_name": "",
        "normalized_metric_family": "",
        "value": None,
        "unit": None,
        "currency": None,
        "period_start": None,
        "period_end": None,
        "measurement_class": "QUALITATIVE",
        "numerator": None,
        "denominator": None,
        "gross_net_basis": "NOT_APPLICABLE",
        "average_end": "NOT_APPLICABLE",
        "reported_derived_estimated": "REPORTED",
    }


def _build_primary_metric(obs: Mapping[str, Any]) -> dict[str, Any]:
    metric_in = obs.get("metric") if isinstance(obs, Mapping) else None
    if isinstance(metric_in, Mapping):
        metric = dict(metric_in)
    else:
        metric = _empty_metric()
        metric["native_metric_name"] = str(obs.get("metric", ""))
        metric["normalized_metric_family"] = metric["native_metric_name"]
        metric["value"] = obs.get("value")
        unit = obs.get("unit")
        metric["unit"] = str(unit) if unit is not None else None
    if "native_metric_name" not in metric or not metric["native_metric_name"]:
        metric["native_metric_name"] = str(obs.get("metric", ""))
    if "normalized_metric_family" not in metric or not metric["normalized_metric_family"]:
        metric["normalized_metric_family"] = metric["native_metric_name"]
    if "value" not in metric:
        metric["value"] = obs.get("value")
    if "unit" not in metric:
        unit = obs.get("unit")
        metric["unit"] = str(unit) if unit is not None else None
    metric.setdefault("currency", None)
    metric.setdefault("period_start", None)
    metric.setdefault("period_end", None)
    metric.setdefault("measurement_class", "QUALITATIVE")
    metric.setdefault("numerator", None)
    metric.setdefault("denominator", None)
    metric.setdefault("gross_net_basis", "NOT_APPLICABLE")
    metric.setdefault("average_end", "NOT_APPLICABLE")
    metric.setdefault("reported_derived_estimated", "REPORTED")
    return metric


def _build_price_primary_metric(obs: Mapping[str, Any]) -> dict[str, Any]:
    """Build a price-plane primary metric from a market observation row.

    The market row carries a price basis (PRICE_RETURN, etc.) and a value
    rather than a structured ``metric`` object; populate the metric with
    placeholders that satisfy the schema's minLength requirements while
    reflecting the price semantics.
    """
    basis = str(obs.get("price_basis") or "")
    metric = {
        "native_metric_name": basis or "price",
        "normalized_metric_family": basis or "price",
        "value": obs.get("value"),
        "unit": obs.get("unit"),
        "currency": None,
        "period_start": None,
        "period_end": None,
        "measurement_class": "QUALITATIVE",
        "numerator": None,
        "denominator": None,
        "gross_net_basis": "NOT_APPLICABLE",
        "average_end": "NOT_APPLICABLE",
        "reported_derived_estimated": "REPORTED",
    }
    return metric


def _plane_block(
    *,
    state: str,
    primary_metric: dict[str, Any] | None,
    clock: dict[str, Any] | None,
    comparability_state: str | None,
    evidence_refs: list[str],
    note: str | None,
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "state": state,
        "primary_metric": primary_metric,
        "clock": clock,
        "comparability_state": comparability_state,
        "evidence_refs": evidence_refs,
        "note": note,
    }
    return block


def _regime_break_for(
    regime_breaks: Sequence[Mapping[str, Any]],
    slice_id: str,
    plane: str,
) -> dict[str, Any] | None:
    for rb in regime_breaks or ():
        if not isinstance(rb, Mapping):
            continue
        if rb.get("slice_id") != slice_id:
            continue
        if rb.get("plane") != plane:
            continue
        return rb
    return None


def _plane_is_regime_break(regime_breaks: Sequence[Mapping[str, Any]], slice_id: str, plane: str) -> bool:
    rb = _regime_break_for(regime_breaks, slice_id, plane)
    if rb is None:
        return False
    return bool(rb.get("bridge_available") is False)


def _has_change_pct_or_delta(value: Any) -> bool:
    forbidden = ("change_pct", "delta", "delta_pct")
    if isinstance(value, dict):
        for key in value:
            if any(tok in key for tok in forbidden):
                return True
            if _has_change_pct_or_delta(value[key]):
                return True
    elif isinstance(value, list):
        for child in value:
            if _has_change_pct_or_delta(child):
                return True
    return False


def _operating_plane(
    slice_id: str,
    financial_packets: Mapping[str, Mapping[str, Any]],
    regime_breaks: Sequence[Mapping[str, Any]],
    evidence_refs: list[str],
) -> dict[str, Any]:
    # Pick the freshest operating observation across all financial_packets
    # that carries an explicit ``direction``. Source records are display-tier
    # (schema-strict) and never carry direction.
    candidates: list[tuple[date | None, Mapping[str, Any]]] = []
    for label, packet in financial_packets.items():
        if not isinstance(packet, Mapping):
            continue
        operating = packet.get("operating")
        if isinstance(operating, Mapping):
            for obs in operating.get("observations") or ():
                if not isinstance(obs, Mapping):
                    continue
                if _direction(obs) is None:
                    continue
                # The composer is per-slice; only consume observations that
                # explicitly tag the slice or that have no tag (interpreted
                # as universal company data).
                if not obs.get("slice_id") or obs.get("slice_id") == slice_id:
                    candidates.append((_coerce_date(obs.get("as_of")), obs))

    if not candidates:
        if _plane_is_regime_break(regime_breaks, slice_id, "operating"):
            return _plane_block(
                state="REGIME_BREAK",
                primary_metric=None,
                clock=None,
                comparability_state="REGIME_BREAK_NOT_COMPARABLE",
                evidence_refs=evidence_refs,
                note="A regime break suppresses percent-change arithmetic on the operating plane.",
            )
        return _plane_block(
            state="MISSING",
            primary_metric=None,
            clock=None,
            comparability_state=None,
            evidence_refs=evidence_refs,
            note="Operating evidence is not available for this slice.",
        )

    candidates.sort(key=lambda c: (c[0] or date.max))
    freshest = candidates[-1][1]
    primary = _build_primary_metric(freshest)
    clock = _plane_clock(freshest)

    if _plane_is_regime_break(regime_breaks, slice_id, "operating"):
        return _plane_block(
            state="REGIME_BREAK",
            primary_metric=primary,
            clock=clock,
            comparability_state="REGIME_BREAK_NOT_COMPARABLE",
            evidence_refs=evidence_refs,
            note="A regime break suppresses percent-change arithmetic on the operating plane.",
        )
    return _plane_block(
        state="OBSERVED",
        primary_metric=primary,
        clock=clock,
        comparability_state="COMPARABLE",
        evidence_refs=evidence_refs,
        note="Operating observation is preserved as supplied by the owner.",
    )


def _expectations_plane(
    slice_id: str,
    expectation_obs: Sequence[Mapping[str, Any]],
    evidence_refs: list[str],
    regime_breaks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    consensus_rows = [o for o in expectation_obs if isinstance(o, Mapping) and not str(o.get("metric", "")).startswith("guidance:")]
    guidance_rows = [o for o in expectation_obs if isinstance(o, Mapping) and str(o.get("metric", "")).startswith("guidance:")]

    if consensus_rows:
        dated = consensus_rows
        history_state = "DATED_CONSENSUS_AVAILABLE"
        history_obs = [
            {
                "as_of": row.get("as_of"),
                "source": row.get("source"),
                "metric": row.get("metric"),
                "value": row.get("value"),
                "unit": row.get("unit"),
            }
            for row in dated
        ]
        freshest = max(dated, key=lambda r: _coerce_date(r.get("as_of")) or date.min)
        primary = _build_primary_metric(freshest)
        clock = _plane_clock(freshest)
        state = "MISSING" if _plane_is_regime_break(regime_breaks, slice_id, "expectations") else "OBSERVED"
        return {
            "state": "REGIME_BREAK" if state == "MISSING" and _plane_is_regime_break(regime_breaks, slice_id, "expectations") else state,
            "primary_metric": primary,
            "clock": clock,
            "comparability_state": "REGIME_BREAK_NOT_COMPARABLE"
            if _plane_is_regime_break(regime_breaks, slice_id, "expectations")
            else "COMPARABLE",
            "evidence_refs": evidence_refs,
            "note": "Dated consensus is preserved as supplied by the owner.",
            "history": {
                "state": history_state,
                "observations": history_obs,
            },
        }

    if guidance_rows:
        history_obs = [
            {
                "as_of": row.get("as_of"),
                "source": row.get("source"),
                "metric": row.get("metric"),
                "value": row.get("value"),
                "unit": row.get("unit"),
            }
            for row in guidance_rows
        ]
        return {
            "state": "MISSING",
            "primary_metric": None,
            "clock": None,
            "comparability_state": None,
            "evidence_refs": evidence_refs,
            "note": "Only management guidance is admitted; consensus is not imputed from guidance.",
            "history": {
                "state": "MANAGEMENT_GUIDANCE_ONLY",
                "observations": history_obs,
            },
        }

    return {
        "state": "MISSING",
        "primary_metric": None,
        "clock": None,
        "comparability_state": None,
        "evidence_refs": evidence_refs,
        "note": "No historical consensus is admitted for this slice.",
        "history": {
            "state": "NO_HISTORICAL_CONSENSUS",
            "observations": [],
        },
    }


def _valuation_plane(
    slice_id: str,
    financial_packets: Mapping[str, Mapping[str, Any]],
    market_obs: Sequence[Mapping[str, Any]],
    evidence_refs: list[str],
    regime_breaks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    anchor_obs: Mapping[str, Any] | None = None
    for label, packet in financial_packets.items():
        if not isinstance(packet, Mapping):
            continue
        valuation = packet.get("valuation")
        if isinstance(valuation, Mapping):
            for obs in valuation.get("observations") or ():
                if isinstance(obs, Mapping):
                    anchor_obs = obs
                    break
    price_basis: str | None = None
    for obs in market_obs:
        if not isinstance(obs, Mapping):
            continue
        basis = obs.get("price_basis")
        if basis in _PRICE_BASIS_QUALIFIED:
            price_basis = basis
            break

    if anchor_obs is None:
        # Check for ADJUSTED_HISTORICAL first — its presence disqualifies
        # the price basis even when the valuation anchor is missing, so
        # the same PRICE_BASIS_UNQUALIFIED verdict covers both reasons.
        for obs in market_obs:
            if isinstance(obs, Mapping) and obs.get("price_basis") == "ADJUSTED_HISTORICAL":
                return _plane_block(
                    state="PRICE_BASIS_UNQUALIFIED",
                    primary_metric=None,
                    clock=None,
                    comparability_state=None,
                    evidence_refs=evidence_refs,
                    note="Adjusted historical price basis is never a valuation quote price.",
                )
        return _plane_block(
            state="VALUATION_ANCHOR_UNAVAILABLE",
            primary_metric=None,
            clock=None,
            comparability_state=None,
            evidence_refs=evidence_refs,
            note="No valuation anchor is admitted for this slice.",
        )
    if price_basis is None:
        # Check for ADJUSTED_HISTORICAL — explicitly disqualified.
        for obs in market_obs:
            if isinstance(obs, Mapping) and obs.get("price_basis") == "ADJUSTED_HISTORICAL":
                return _plane_block(
                    state="PRICE_BASIS_UNQUALIFIED",
                    primary_metric=None,
                    clock=None,
                    comparability_state=None,
                    evidence_refs=evidence_refs,
                    note="Adjusted historical price basis is never a valuation quote price.",
                )
        return _plane_block(
            state="PRICE_BASIS_UNQUALIFIED",
            primary_metric=None,
            clock=None,
            comparability_state=None,
            evidence_refs=evidence_refs,
            note="No qualified price basis is admitted for the valuation plane.",
        )

    primary = _build_primary_metric(anchor_obs)
    clock = _plane_clock(anchor_obs)
    if _plane_is_regime_break(regime_breaks, slice_id, "valuation"):
        return _plane_block(
            state="REGIME_BREAK",
            primary_metric=primary,
            clock=clock,
            comparability_state="REGIME_BREAK_NOT_COMPARABLE",
            evidence_refs=evidence_refs,
            note="A regime break suppresses percent-change arithmetic on the valuation plane.",
        )
    return _plane_block(
        state="OBSERVED",
        primary_metric=primary,
        clock=clock,
        comparability_state="COMPARABLE",
        evidence_refs=evidence_refs,
        note="Valuation anchor and qualified price basis are both admitted.",
    )


def _price_plane(
    slice_id: str,
    market_obs: Sequence[Mapping[str, Any]],
    evidence_refs: list[str],
    regime_breaks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    qualified = [
        o
        for o in market_obs
        if isinstance(o, Mapping) and o.get("price_basis") in _PRICE_BASIS_QUALIFIED
    ]
    if not qualified:
        for obs in market_obs:
            if isinstance(obs, Mapping) and obs.get("price_basis") == "ADJUSTED_HISTORICAL":
                return _plane_block(
                    state="PRICE_BASIS_UNQUALIFIED",
                    primary_metric=None,
                    clock=None,
                    comparability_state=None,
                    evidence_refs=evidence_refs,
                    note="Adjusted historical price basis is never a qualified price.",
                )
        return _plane_block(
            state="PRICE_BASIS_UNQUALIFIED",
            primary_metric=None,
            clock=None,
            comparability_state=None,
            evidence_refs=evidence_refs,
            note="No qualified price basis is admitted for the price plane.",
        )
    freshest = max(qualified, key=lambda o: _coerce_date(o.get("as_of")) or date.min)
    primary = _build_price_primary_metric(freshest)
    clock = _plane_clock(freshest)
    if _plane_is_regime_break(regime_breaks, slice_id, "price"):
        return _plane_block(
            state="REGIME_BREAK",
            primary_metric=primary,
            clock=clock,
            comparability_state="REGIME_BREAK_NOT_COMPARABLE",
            evidence_refs=evidence_refs,
            note="A regime break suppresses percent-change arithmetic on the price plane.",
        )
    return _plane_block(
        state="OBSERVED",
        primary_metric=primary,
        clock=clock,
        comparability_state="COMPARABLE",
        evidence_refs=evidence_refs,
        note="Qualified price observation is preserved as supplied by the owner.",
    )


def _bridge_text(operating_state: str, expectations_state: str, valuation_state: str, price_state: str) -> str:
    parts = []
    if operating_state == "REGIME_BREAK":
        parts.append("operating regime break")
    if expectations_state == "REGIME_BREAK":
        parts.append("expectations regime break")
    if valuation_state == "REGIME_BREAK":
        parts.append("valuation regime break")
    if price_state == "REGIME_BREAK":
        parts.append("price regime break")
    if parts:
        return (
            "Bridge narrative carries regime breaks on the " + ", ".join(parts) + " plane(s); no percent-change arithmetic is emitted."
        )
    return (
        "The four planes remain separate. Operating economics, expectations, valuation and price recognition are not averaged into a single rerating signal."
    )


def _valuation_anchor_for(slice_id: str, valuation_plane: dict[str, Any]) -> dict[str, Any]:
    if valuation_plane["state"] == "OBSERVED":
        return {
            "primary_per_share_anchor": "NOT_APPLICABLE",
            "primary_valuation_anchor": "NOT_APPLICABLE",
            "denominator": "The owner-supplied denominator is preserved without recomputation.",
            "horizon": "NOT_APPLICABLE",
            "information_clock": valuation_plane.get("clock", {}).get("observed_at") if isinstance(valuation_plane.get("clock"), Mapping) else None,
            "required_return_context": None,
            "state": "AVAILABLE",
        }
    return {
        "primary_per_share_anchor": "NOT_APPLICABLE",
        "primary_valuation_anchor": "NOT_APPLICABLE",
        "denominator": "No synthetic denominator is admitted.",
        "horizon": "NOT_APPLICABLE",
        "information_clock": None,
        "required_return_context": None,
        "state": "VALUATION_ANCHOR_UNAVAILABLE",
    }


def _basket_state_for(slice_id: str, basket: Mapping[str, Any]) -> dict[str, Any]:
    posture = basket.get("posture") if isinstance(basket, Mapping) else None
    if posture is None:
        # Composer never invents posture when basket context is absent.
        return {
            "posture": "SEMANTIC_ONLY",
            "incumbent_basket_ids": [],
            "membership_state": "NONE",
            "member_count": None,
            "weighting_family": None,
            "price_basis_state": None,
        }
    incumbents = list(basket.get("incumbent_basket_ids") or [])
    return {
        "posture": posture,
        "incumbent_basket_ids": incumbents,
        "membership_state": basket.get("membership_state", "NONE"),
        "member_count": basket.get("member_count"),
        "weighting_family": basket.get("weighting_family"),
        "price_basis_state": basket.get("price_basis_state"),
    }


def _slice_state_for(
    slice_id: str,
    operating: dict[str, Any],
    expectations: dict[str, Any],
    valuation: dict[str, Any],
    price: dict[str, Any],
    rights_profiles: set[str],
) -> str:
    if rights_profiles.intersection({"SOURCE_RIGHTS_HELD", "INTERNAL_ONLY"}):
        return "RIGHTS_RESTRICTED"
    if operating["state"] == "OBSERVED" or expectations["history"]["state"] != "NO_HISTORICAL_CONSENSUS":
        return "RESEARCH_EVIDENCE_AVAILABLE"
    if price["state"] == "OBSERVED":
        return "PRICE_SURFACE_AVAILABLE"
    if valuation["state"] == "VALUATION_ANCHOR_UNAVAILABLE" and price["state"] == "PRICE_BASIS_UNQUALIFIED":
        return "MEASURABLE"
    return "SEMANTIC_ONLY"


def _slice_freshness(
    slice_id: str,
    source_records: Sequence[Mapping[str, Any]],
    expectation_obs: Sequence[Mapping[str, Any]],
    market_obs: Sequence[Mapping[str, Any]],
    knowledge_cutoff: date,
    stale_after_days: int,
) -> tuple[dict[str, Any], date | None]:
    observed_dates: list[date] = []
    for rec in source_records:
        if isinstance(rec, Mapping) and rec.get("business_scope") == slice_id:
            d = _source_record_observed_at(rec)
            if d is not None:
                observed_dates.append(d)
    for obs in expectation_obs:
        if isinstance(obs, Mapping):
            d = _coerce_date(obs.get("as_of"))
            if d is not None:
                observed_dates.append(d)
    for obs in market_obs:
        if isinstance(obs, Mapping):
            d = _coerce_date(obs.get("as_of"))
            if d is not None:
                observed_dates.append(d)
    if not observed_dates:
        return ({"evidence_latest_observed_at": None, "state": "NO_EVIDENCE"}, None)
    latest = max(observed_dates)
    age = (knowledge_cutoff - latest).days
    if age > stale_after_days:
        state = "SOURCE_STALE"
    elif age > stale_after_days // 2:
        state = "AGING"
    else:
        state = "FRESH"
    return ({"evidence_latest_observed_at": latest.isoformat(), "state": state}, latest)


def _slice_evidence_refs(
    slice_id: str,
    source_records: Sequence[Mapping[str, Any]],
    expectation_obs: Sequence[Mapping[str, Any]],
    market_obs: Sequence[Mapping[str, Any]],
) -> list[str]:
    refs: set[str] = set()
    for rec in source_records:
        if isinstance(rec, Mapping) and rec.get("business_scope") == slice_id:
            rid = rec.get("record_id")
            if rid:
                refs.add(str(rid))
            elif rec.get("evidence_ref"):
                refs.add(str(rec.get("evidence_ref")))
    for obs in expectation_obs:
        if isinstance(obs, Mapping):
            ref = obs.get("source") or obs.get("evidence_ref")
            if ref:
                refs.add(str(ref))
    for obs in market_obs:
        if isinstance(obs, Mapping):
            ref = obs.get("source") or obs.get("evidence_ref")
            if ref:
                refs.add(str(ref))
    if not refs:
        # Fall back to the slice id as a synthetic ref so the schema's
        # non-empty evidence_refs requirement is satisfied when no
        # owner-supplied ref is present.
        refs.add("slice:" + slice_id)
    return sorted(refs)


# ---------------------------------------------------------------------------
# Material changes
# ---------------------------------------------------------------------------


def _public_freshness(value: Any) -> str:
    """Coerce an internal freshness_state to the schema-admitted enum."""
    text = str(value or "").strip().upper()
    if text in ("FRESH", "AGING", "SOURCE_STALE", "NO_EVIDENCE"):
        return text
    if text in ("CAUSAL_EFFECT_UNMEASURED", "EXPERIMENTAL", "PROVISIONAL"):
        return "FRESH"
    return "FRESH"


def _material_changes_for(
    slice_id: str,
    source_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rec in source_records:
        if not isinstance(rec, Mapping):
            continue
        if rec.get("business_scope") != slice_id:
            continue
        material = rec.get("material_change")
        if not isinstance(material, Mapping):
            continue
        change_id = material.get("change_id") or rec.get("record_id")
        if not change_id:
            continue
        observed_at = _source_record_observed_at(rec)
        published_at = _coerce_date((rec.get("source") or {}).get("published_at")) if isinstance(rec.get("source"), Mapping) else None
        out.append({
            "change_id": str(change_id),
            "event_clock": {
                "published_at": published_at.isoformat() if published_at else None,
                "published_at_grain": "DAY",
                "observed_at": observed_at.isoformat() if observed_at else "1970-01-01",
                "effective_at": _coerce_date(material.get("effective_at")).isoformat()
                if _coerce_date(material.get("effective_at"))
                else None,
            },
            "domain_ids": list(material.get("domain_ids") or [_domain_of(slice_id)]),
            "slice_ids": [slice_id],
            "operating_implication": str(material.get("operating_implication", "")),
            "evidence_refs": [str(rec.get("record_id"))] if rec.get("record_id") else [],
            "conflict_ids": list(material.get("conflict_ids") or []),
            # CAUSAL_EFFECT_UNMEASURED is an internal flag used by the
            # conflict detector; the document's freshness_state enum
            # only admits FRESH / AGING / SOURCE_STALE / NO_EVIDENCE,
            # so coerce the internal flag back to FRESH here while
            # preserving the original on ``_freshness_state_raw`` for
            # the conflict detector.
            "freshness_state": _public_freshness(material.get("freshness_state")),
            "_freshness_state_raw": str(material.get("freshness_state", "FRESH")),
        })
    return out


# ---------------------------------------------------------------------------
# Conflicts (deterministic from plane states)
# ---------------------------------------------------------------------------


def _conflicts_for(
    slice_id: str,
    company_rows: list[dict[str, Any]],
    operating: dict[str, Any],
    valuation: dict[str, Any],
    price: dict[str, Any],
    regime_breaks: Sequence[Mapping[str, Any]],
    material_changes: Sequence[Mapping[str, Any]],
    macro_context: Mapping[str, Any],
    operating_observations: Sequence[Mapping[str, Any]] = (),
    valuation_observations: Sequence[Mapping[str, Any]] = (),
    market_observations: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []

    operating_direction = _direction_from_observations(operating_observations)
    valuation_direction = _direction_from_observations(valuation_observations)
    price_direction = _direction_from_observations(market_observations)

    if (
        operating["state"] == "OBSERVED"
        and operating_direction == "UP"
        and valuation["state"] == "OBSERVED"
        and valuation_direction == "DOWN"
    ):
        anchor_kind = (valuation.get("primary_metric") or {}).get("normalized_metric_family", "")
        if "P/E" in anchor_kind or anchor_kind == "P_E":
            conflicts.append(_new_conflict("conflict-" + slice_id + "-earnings-up-pe-down", "EARNINGS_UP_P_E_DOWN", slice_id, company_rows, operating, valuation))
        elif "P/B" in anchor_kind or "P/BV" in anchor_kind or anchor_kind in ("P_B", "P_TBV"):
            conflicts.append(_new_conflict("conflict-" + slice_id + "-book-up-pb-down", "BOOK_UP_P_B_DOWN", slice_id, company_rows, operating, valuation))

    # POLICY_SUPPORT_NIM_PRESSURE
    macro_for_slice = (macro_context or {}).get(slice_id) or {}
    if isinstance(macro_for_slice, Mapping):
        support = macro_for_slice.get("policy_rates_support") or macro_for_slice.get("support")
        if support:
            for obs in (operating.get("primary_metric") or {},):
                if (obs.get("native_metric_name") or "").lower().startswith("nim") and operating_direction == "DOWN":
                    conflicts.append(_new_conflict(
                        "conflict-" + slice_id + "-policy-support-nim-pressure",
                        "POLICY_SUPPORT_NIM_PRESSURE",
                        slice_id,
                        company_rows,
                        operating,
                        operating,
                        left_statement="Macro context marks policy-rate support for this slice.",
                        right_statement="Operating NIM observation direction is DOWN.",
                    ))
                    break

    # REGULATORY_RATIO_DOWN_REGIME_BREAK
    if operating_direction == "DOWN" and _plane_is_regime_break(regime_breaks, slice_id, "operating"):
        if (operating.get("primary_metric") or {}).get("measurement_class") == "RATIO":
            conflicts.append(_new_conflict(
                "conflict-" + slice_id + "-regulatory-ratio-down-regime-break",
                "REGULATORY_RATIO_DOWN_REGIME_BREAK",
                slice_id,
                company_rows,
                operating,
                operating,
                left_statement="Capital-ratio observation direction is DOWN.",
                right_statement="A regime break is admitted on the operating plane.",
            ))

    # PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN
    if price["state"] == "OBSERVED" and price_direction == "UP":
        for change in material_changes:
            if not isinstance(change, Mapping):
                continue
            internal_freshness = change.get("_freshness_state_raw") or change.get("freshness_state")
            if internal_freshness == "CAUSAL_EFFECT_UNMEASURED":
                conflicts.append(_new_conflict(
                    "conflict-" + slice_id + "-price-up-causal-event-effect-unproven",
                    "PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN",
                    slice_id,
                    company_rows,
                    price,
                    price,
                    left_statement="Price observation direction is UP.",
                    right_statement="Material change admits causal effect unmeasured.",
                ))
                break

    return conflicts


def _plane_direction(plane: dict[str, Any]) -> str | None:
    metric = plane.get("primary_metric")
    if not isinstance(metric, Mapping):
        return None
    direction = metric.get("direction")
    if direction is None:
        return None
    text = str(direction).strip().upper()
    if text in ("UP", "DOWN", "FLAT"):
        return text
    return None


def _direction_from_observations(observations: Sequence[Mapping[str, Any]]) -> str | None:
    """Pick the direction from the freshest observation that carries one.

    Conflicts compare explicit directions across planes; if no observation
    carries one the direction is ``None`` and the rule fires only when the
    rule's other preconditions are already met.
    """
    candidates: list[tuple[date | None, str]] = []
    for obs in observations or ():
        if not isinstance(obs, Mapping):
            continue
        direction = _direction(obs)
        if direction is None:
            continue
        as_of = _coerce_date(obs.get("as_of")) if hasattr(obs.get("as_of", None), "__class__") else None
        if as_of is None and isinstance(obs.get("as_of"), str):
            as_of = _coerce_date(obs.get("as_of"))
        candidates.append((as_of, direction))
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[0] or date.max))
    return candidates[-1][1]


def _new_conflict(
    conflict_id: str,
    label: str,
    slice_id: str,
    company_rows: Sequence[Mapping[str, Any]],
    left_plane: Mapping[str, Any],
    right_plane: Mapping[str, Any],
    *,
    left_statement: str | None = None,
    right_statement: str | None = None,
) -> dict[str, Any]:
    return {
        "conflict_id": conflict_id,
        "label": label,
        "slice_ids": [slice_id],
        "company_row_ids": [str(row.get("row_id")) for row in company_rows if isinstance(row, Mapping) and row.get("row_id")],
        "left": {
            "plane": left_plane.get("state") and ("operating" if left_plane is not None else "operating"),
            "statement": left_statement or "The owner-supplied left side is preserved verbatim.",
            "evidence_refs": list(left_plane.get("evidence_refs", [])) if isinstance(left_plane, Mapping) else [],
        },
        "right": {
            "plane": "operating",
            "statement": right_statement or "The owner-supplied right side is preserved verbatim.",
            "evidence_refs": list(right_plane.get("evidence_refs", [])) if isinstance(right_plane, Mapping) else [],
        },
        "resolution": "UNRESOLVED_BY_DESIGN",
    }


# ---------------------------------------------------------------------------
# Company rows
# ---------------------------------------------------------------------------


def _exposure_basis_for(measurement_class: str | None) -> tuple[str, str]:
    if measurement_class in ("VOLUME_VALUE", "VOLUME_COUNT"):
        return ("TRANSACTION_VOLUME", "MEASURED")
    if measurement_class in ("REVENUE", "EXPENSE", "BALANCE", "RATIO", "RATE", "PER_SHARE"):
        return ("SEGMENT_REVENUE", "MEASURED")
    if measurement_class == "QUALITATIVE":
        return ("QUALITATIVE", "QUALITATIVE_ONLY")
    return ("NOT_SEPARATELY_DISCLOSED", "EXPOSURE_NOT_SEPARATELY_DISCLOSED")


def _company_row_for_issuer(
    issuer_label: str,
    packet: Mapping[str, Any],
    identity_bindings: Mapping[str, Mapping[str, Any]],
    slice_id_to_atlas_id: Mapping[str, str],
    observation_inputs: tuple[
        Mapping[str, Sequence[Mapping[str, Any]]],
        Mapping[str, Sequence[Mapping[str, Any]]],
    ],
    source_record_ids: set[str],
    source_record_extras: Sequence[Mapping[str, Any]],
    raw_source_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    binding = identity_bindings.get(issuer_label)
    identity_state = "IDENTITY_UNRESOLVED"
    company_node_id: str | None = None
    security_ref: str | None = None
    listing_note: str | None = None
    if binding is not None:
        state = binding.get("state")
        if state == "IDENTITY_VALIDATED":
            identity_state = "IDENTITY_VALIDATED"
            company_node_id = binding.get("company_node_id")
            security_ref = binding.get("security_ref")
            listing_note = binding.get("listing_note")
        elif state == "RESEARCH_HINT_UNVALIDATED":
            identity_state = "RESEARCH_HINT_UNVALIDATED"
            company_node_id = binding.get("company_node_id")
            security_ref = binding.get("security_ref")
            listing_note = binding.get("listing_note")
        else:
            identity_state = "IDENTITY_UNRESOLVED"

    cells: list[dict[str, Any]] = []
    expectations, markets = observation_inputs
    candidate_slice_ids: set[str] = set()

    def _maybe_add_cell(slice_id: str, role: str, exposure_basis: str, exposure_state: str,
                        numerator: str | None, denominator: str | None,
                        value: Any, unit: str | None, retained_risk: str | None,
                        materiality: str, evidence_date: str | None,
                        evidence_refs: list[str]) -> None:
        if slice_id not in slice_id_to_atlas_id:
            return
        cell_basis = exposure_basis
        cell_state = exposure_state
        if exposure_basis == "TRANSACTION_VOLUME":
            cell_basis = "TRANSACTION_VOLUME"
            cell_state = "MEASURED"
            if not denominator:
                # A volume cell without a denominator is not separately disclosed.
                cell_state = "EXPOSURE_NOT_SEPARATELY_DISCLOSED"
        elif exposure_basis == "SEGMENT_REVENUE":
            if not denominator:
                cell_state = "EXPOSURE_NOT_SEPARATELY_DISCLOSED"
            else:
                cell_state = "MEASURED"
        cell = {
            "slice_id": slice_id_to_atlas_id[slice_id],
            "role": role,
            "exposure": {
                "basis": cell_basis,
                "numerator": numerator,
                "denominator": denominator,
                "value": value if cell_state == "MEASURED" else None,
                "unit": unit,
                "state": cell_state,
            },
            "materiality": materiality,
            "retained_risk": retained_risk,
            "evidence_date": evidence_date,
            "evidence_refs": evidence_refs,
        }
        # If a cell for this slice already exists, REPLACE it — the
        # later-evaluated path wins (financial_packets is laid down first
        # so source_records, which carry the measurement_class that
        # decides exposure basis, supersede).
        for i, existing in enumerate(cells):
            if existing.get("slice_id") == slice_id_to_atlas_id[slice_id]:
                cells[i] = cell
                candidate_slice_ids.add(slice_id)
                return
        cells.append(cell)
        candidate_slice_ids.add(slice_id)

    operating = packet.get("operating") if isinstance(packet, Mapping) else None
    if isinstance(operating, Mapping):
        for obs in operating.get("cells") or ():
            if not isinstance(obs, Mapping):
                continue
            slice_id = obs.get("slice_id")
            if not isinstance(slice_id, str):
                continue
            candidate_slice_ids.add(slice_id)
            _maybe_add_cell(
                slice_id,
                obs.get("role", "PROXY_OR_ADJACENCY"),
                obs.get("basis") or "SEGMENT_REVENUE",
                "MEASURED",
                obs.get("numerator"),
                obs.get("denominator"),
                obs.get("value"),
                obs.get("unit"),
                obs.get("retained_risk"),
                obs.get("materiality", "UNMEASURED"),
                obs.get("evidence_date"),
                [str(ref) for ref in (obs.get("evidence_refs") or []) if ref],
            )

    valuation = packet.get("valuation") if isinstance(packet, Mapping) else None
    if isinstance(valuation, Mapping):
        for obs in valuation.get("cells") or ():
            if not isinstance(obs, Mapping):
                continue
            slice_id = obs.get("slice_id")
            if not isinstance(slice_id, str):
                continue
            candidate_slice_ids.add(slice_id)
            _maybe_add_cell(
                slice_id,
                obs.get("role", "PROXY_OR_ADJACENCY"),
                obs.get("basis") or "QUALITATIVE",
                "QUALITATIVE_ONLY",
                obs.get("numerator"),
                obs.get("denominator"),
                obs.get("value"),
                obs.get("unit"),
                obs.get("retained_risk"),
                obs.get("materiality", "UNMEASURED"),
                obs.get("evidence_date"),
                [str(ref) for ref in (obs.get("evidence_refs") or []) if ref],
            )

    # Surface any slices for which expectations/market observations exist
    # for this issuer (no segment denominator is admitted in the absence
    # of an explicit one).
    for slice_id, obs_list in expectations.items():
        if not isinstance(obs_list, (list, tuple)) or not obs_list:
            continue
        if slice_id not in slice_id_to_atlas_id:
            continue
        if slice_id in candidate_slice_ids:
            continue
        # No segment denominator admitted for this slice from the issuer.
        candidate_slice_ids.add(slice_id)
        _maybe_add_cell(
            slice_id,
            "PROXY_OR_ADJACENCY",
            "NOT_SEPARATELY_DISCLOSED",
            "EXPOSURE_NOT_SEPARATELY_DISCLOSED",
            None,
            None,
            None,
            None,
            None,
            "UNMEASURED",
            None,
            [],
        )

    for slice_id, obs_list in markets.items():
        if not isinstance(obs_list, (list, tuple)) or not obs_list:
            continue
        if slice_id not in slice_id_to_atlas_id:
            continue
        if slice_id in candidate_slice_ids:
            continue
        candidate_slice_ids.add(slice_id)
        _maybe_add_cell(
            slice_id,
            "PROXY_OR_ADJACENCY",
            "NOT_SEPARATELY_DISCLOSED",
            "EXPOSURE_NOT_SEPARATELY_DISCLOSED",
            None,
            None,
            None,
            None,
            None,
            "UNMEASURED",
            None,
            [],
        )

    # Merge source records whose ``_ticker_hint`` matches this issuer.
    # Each one is a schema-strict record carrying a ``business_scope``
    # (slice_id), a metric, and the identity_state the owner supplied.
    # The measurement_class on the metric drives the exposure basis,
    # and a missing denominator drives the cell state to
    # EXPOSURE_NOT_SEPARATELY_DISCLOSED.
    for rec, extras in zip(raw_source_records, source_record_extras):
        if not isinstance(rec, Mapping):
            continue
        if str(extras.get("_ticker_hint") or "") != issuer_label:
            continue
        business_scope = rec.get("business_scope")
        if not isinstance(business_scope, str) or business_scope not in slice_id_to_atlas_id:
            continue
        metric_obj = rec.get("metric") if isinstance(rec.get("metric"), Mapping) else {}
        measurement_class = metric_obj.get("measurement_class") if isinstance(metric_obj, Mapping) else None
        exposure_basis, _default_state = _exposure_basis_for(measurement_class)
        role = "ENABLER_OR_TOLL_COLLECTOR" if exposure_basis == "TRANSACTION_VOLUME" else "DIRECT_PURE_OR_HIGH_EXPOSURE"
        numerator = metric_obj.get("numerator") if isinstance(metric_obj, Mapping) else None
        denominator = metric_obj.get("denominator") if isinstance(metric_obj, Mapping) else None
        value = metric_obj.get("value") if isinstance(metric_obj, Mapping) else None
        unit = metric_obj.get("unit") if isinstance(metric_obj, Mapping) else None
        record_id = rec.get("record_id")
        source_obj = rec.get("source") if isinstance(rec.get("source"), Mapping) else {}
        observed_at = source_obj.get("observed_at") if isinstance(source_obj, Mapping) else None
        record_identity_state = rec.get("identity_state") if isinstance(rec.get("identity_state"), str) else None
        # A source record with identity_state == IDENTITY_UNRESOLVED wins
        # over an identity_bindings binding (which is OPTIONAL context).
        if record_identity_state == "IDENTITY_UNRESOLVED":
            identity_state = "IDENTITY_UNRESOLVED"
            company_node_id = None
            security_ref = None
            listing_note = None
        candidate_slice_ids.add(business_scope)
        _maybe_add_cell(
            business_scope,
            role,
            exposure_basis,
            "MEASURED",
            numerator,
            denominator,
            value,
            unit,
            None,
            "MATERIAL",
            observed_at,
            [str(record_id)] if record_id else [],
        )

    if not cells:
        return None

    route_href: str | None = None
    route_state = "IDENTITY_UNRESOLVED"
    if identity_state == "IDENTITY_VALIDATED":
        route_href = "https://example.invalid/stock.html#" + issuer_label
        route_state = "AVAILABLE"

    return {
        "row_id": "row-" + issuer_label,
        "issuer_label": issuer_label,
        "ticker_hint": issuer_label,
        "identity": {
            "state": identity_state,
            "company_node_id": company_node_id,
            "security_ref": security_ref,
            "listing_note": listing_note,
        },
        "company_route": {"href": route_href, "state": route_state},
        "cells": cells,
    }


def _company_rows(
    inputs: FinanceOwnerInputs,
    slice_id_to_atlas_id: Mapping[str, str],
    source_record_extras: Sequence[Mapping[str, Any]],
    raw_source_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    source_record_ids: set[str] = set()
    for rec in raw_source_records:
        if isinstance(rec, Mapping):
            rid = rec.get("record_id")
            if rid:
                source_record_ids.add(str(rid))

    # Build the union of company keys: explicit identity_bindings +
    # financial_packets keys + any source record's _ticker_hint.
    keys: set[str] = set()
    for k in inputs.identity_bindings:
        keys.add(str(k))
    for k in inputs.financial_packets:
        keys.add(str(k))
    for extras in source_record_extras:
        if isinstance(extras, Mapping):
            ticker = extras.get("_ticker_hint")
            if isinstance(ticker, str) and ticker:
                keys.add(ticker)

    rows: list[dict[str, Any]] = []
    observation_inputs = (
        inputs.expectation_observations,
        inputs.market_observations,
    )
    for key in sorted(keys):
        packet = inputs.financial_packets.get(key) or {}
        row = _company_row_for_issuer(
            key,
            packet,
            inputs.identity_bindings,
            slice_id_to_atlas_id,
            observation_inputs,
            source_record_ids,
            source_record_extras,
            raw_source_records,
        )
        if row is not None:
            rows.append(row)
    return rows


def _domain_records(slices: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    domain_to_slices: dict[str, list[str]] = {}
    for sl in slices:
        domain_id = sl["domain_id"]
        domain_to_slices.setdefault(domain_id, []).append(sl["slice_id"])
    out: list[dict[str, Any]] = []
    for domain_id in sorted(domain_to_slices):
        name_en, name_zh = _DOMAIN_NAMES.get(domain_id, (domain_id.replace("_", " ").capitalize(), domain_id))
        out.append({
            "domain_id": domain_id,
            "name_en": name_en,
            "name_zh": name_zh,
            "slice_ids": sorted(set(domain_to_slices[domain_id])),
            "system_view_ids": ["contractual_flow", "infrastructure_access", "public_equity_economics"],
        })
    return out


def _system_views(slices: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_slice: dict[str, dict[str, Any]] = {}
    for sl in slices:
        by_slice[sl["slice_id"]] = sl

    def _view_for(view_id: str, name_en: str, name_zh: str) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        if view_id == "contractual_flow":
            vocab = _CONTRACTUAL_FLOW_RELATIONSHIPS
            template = [
                ("payer", "Payer", "付款方", "synthetic_node", ["card_networks"]),
                ("network", "Card network", "卡组织", "synthetic_node", ["card_networks"]),
                ("settlement", "Settlement bank", "结算银行", "synthetic_node", ["merchant_acquiring_processing"]),
                ("issuer", "Issuer", "发卡机构", "synthetic_node", ["issuer_processing"]),
                ("operator", "Market operator", "市场运营方", "synthetic_node", ["exchanges_trading_venues"]),
                ("member", "Clearing member", "清算会员", "synthetic_node", ["clearing_ccp_csd"]),
                ("custodian", "Custodian", "托管机构", "synthetic_node", ["custody_asset_servicing"]),
            ]
            edge_templates = [
                ("payer", "network", "PAYS", "OBSERVED"),
                ("network", "settlement", "SETTLES", "OBSERVED"),
                ("issuer", "network", "FUNDS", "OBSERVED"),
                ("operator", "member", "CLEARS", "OBSERVED"),
                ("custodian", "settlement", "HOLDS_CUSTODY", "OBSERVED"),
            ]
        elif view_id == "infrastructure_access":
            vocab = _INFRASTRUCTURE_ACCESS_RELATIONSHIPS
            template = [
                ("operator", "Market operator", "市场运营方", "synthetic_node", ["exchanges_trading_venues"]),
                ("member", "Clearing member", "清算会员", "synthetic_node", ["clearing_ccp_csd", "custody_asset_servicing"]),
                ("benchmark-publisher", "Benchmark publisher", "基准发布方", "synthetic_node", ["indices_benchmarks_etf_plumbing"]),
                ("ratings-provider", "Ratings provider", "评级提供方", "synthetic_node", ["ratings_credit_information"]),
                ("data-vendor", "Market data vendor", "市场数据供应商", "synthetic_node", ["market_reference_data"]),
            ]
            edge_templates = [
                ("operator", "member", "SUPERVISES", "OBSERVED"),
                ("operator", "member", "REQUIRES_MEMBERSHIP", "OBSERVED"),
                ("benchmark-publisher", "operator", "PUBLISHES_BENCHMARK", "OBSERVED"),
                ("ratings-provider", "member", "RATES", "OBSERVED"),
                ("data-vendor", "member", "PROVIDES_DATA", "OBSERVED"),
            ]
        else:
            vocab = _PUBLIC_EQUITY_RELATIONSHIPS
            template = [
                ("issuer", "Listing issuer", "上市发行人", "synthetic_node", ["equity_debt_capital_markets"]),
                ("operator-company", "Market operator company", "市场运营公司", "synthetic_node", ["exchanges_trading_venues"]),
                ("asset-manager", "Asset manager", "资产管理人", "synthetic_node", ["active_asset_managers", "passive_etf_asset_managers"]),
                ("private-credit", "Private credit manager", "私募信贷管理", "synthetic_node", ["private_credit_managers"]),
                ("broker", "Broker", "券商", "synthetic_node", ["mna_advisory", "prime_brokerage_securities_lending"]),
            ]
            edge_templates = [
                ("issuer", "operator-company", "EARNS_FEE_FROM", "OBSERVED"),
                ("issuer", "operator-company", "DEPENDS_ON_VOLUME_OF", "OBSERVED"),
                ("asset-manager", "operator-company", "BEARS_CREDIT_RISK_OF", "OBSERVED"),
                ("private-credit", "issuer", "CAPTURES_SPREAD_ON", "OBSERVED"),
                ("broker", "asset-manager", "RECOGNISES_REVENUE_FROM", "OBSERVED"),
            ]

        seen_node_ids: set[str] = set()
        for node_id, label_en, label_zh, node_type, slice_ids in template:
            if slice_ids and not any(sid in by_slice for sid in slice_ids):
                continue
            nodes.append({
                "node_id": node_id,
                "label_en": label_en,
                "label_zh": label_zh,
                "node_type": node_type,
                "slice_ids": slice_ids,
                "expandable": True,
                "children_ids": [],
            })
            seen_node_ids.add(node_id)

        for src, dst, rel, ev_state in edge_templates:
            if src not in seen_node_ids or dst not in seen_node_ids:
                continue
            if rel not in vocab:
                continue
            edges.append({
                "from": src,
                "to": dst,
                "relationship": rel,
                "evidence_state": ev_state,
            })

        return {
            "view_id": view_id,
            "name_en": name_en,
            "name_zh": name_zh,
            "nodes": nodes,
            "edges": edges,
        }

    out: list[dict[str, Any]] = []
    for view in _SYSTEM_VIEWS:
        out.append(_view_for(view["view_id"], view["name_en"], view["name_zh"]))
    return out


def _macro_matrix(inputs: FinanceOwnerInputs, slices: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    macro_by_slice = inputs.macro_context or {}
    for sl in slices:
        macro_for_slice = macro_by_slice.get(sl["slice_id"]) if isinstance(macro_by_slice, Mapping) else None
        if not isinstance(macro_for_slice, Mapping):
            continue
        # mechanism_by_slice is keyed by slice_id (mirroring macro_by_slice),
        # each entry maps driver → payload.
        mechanism_outer = macro_for_slice.get("mechanism_by_slice") if isinstance(macro_for_slice, Mapping) else None
        if not isinstance(mechanism_outer, Mapping):
            continue
        drivers_map = mechanism_outer.get(sl["slice_id"]) if isinstance(mechanism_outer.get(sl["slice_id"]), Mapping) else None
        if drivers_map is None:
            # Fallback: if mechanism_outer is the driver→payload map directly,
            # treat its keys as drivers for this slice.
            drivers_map = mechanism_outer
        for driver, payload in drivers_map.items():
            if not isinstance(payload, Mapping):
                continue
            out.append({
                "slice_id": sl["slice_id"],
                "driver": driver,
                "mechanism": str(payload.get("mechanism", "Macro mechanism is preserved as supplied by the owner.")),
                "lag": str(payload.get("lag", "UNKNOWN")),
                "state": str(payload.get("state", "DESCRIBED")),
            })
    return out


def _constraints_for(inputs: FinanceOwnerInputs, slices: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    by_slice: dict[str, dict[str, Any]] = {}
    for sl in slices:
        by_slice[sl["slice_id"]] = sl
    for rec in inputs.source_records:
        if not isinstance(rec, Mapping):
            continue
        slice_id = rec.get("slice_id")
        constraints = rec.get("constraints")
        if not isinstance(constraints, list) or slice_id not in by_slice:
            continue
        for c in constraints:
            if not isinstance(c, Mapping):
                continue
            out.append({
                "slice_id": slice_id,
                "constraint": str(c.get("constraint", "")),
                "economic_effect": str(c.get("economic_effect", "")),
                "evidence_refs": [str(rec.get("record_id"))] if rec.get("record_id") else [],
            })
    return out


def _input_receipts(inputs: FinanceOwnerInputs) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    if inputs.sector_dossier is None:
        receipts.append({
            "owner": "sector_intelligence",
            "generation": None,
            "state": "NOT_ACCEPTED",
            "note": "Sector dossier contract is not yet accepted on main.",
        })
    else:
        receipts.append({
            "owner": "sector_intelligence",
            "generation": str(inputs.sector_dossier.get("schema_version", "")) or None,
            "state": "READ",
            "note": "Sector dossier is admitted as supplied by the owner.",
        })
    receipts.append({
        "owner": "theme_graph",
        "generation": "shared_curation_assertion_v1",
        "state": "READ" if inputs.theme_evidence else "DEGRADED",
        "note": "Shared theme curation assertions are admitted as opaque evidence.",
    })
    receipts.append({
        "owner": "financial_intelligence",
        "generation": "financial_packet_v1",
        "state": "READ" if inputs.financial_packets else "DEGRADED",
        "note": "Financial Intelligence packets are consumed for supported facts only.",
    })
    receipts.append({
        "owner": "expectations_revisions",
        "generation": "expectation_observations_v1",
        "state": "READ" if inputs.expectation_observations else "DEGRADED",
        "note": "Dated consensus and management guidance are admitted without inference.",
    })
    receipts.append({
        "owner": "market_data",
        "generation": "market_observations_v1",
        "state": "READ" if inputs.market_observations else "DEGRADED",
        "note": "Market observations are admitted as supplied by the owner.",
    })
    receipts.append({
        "owner": "baskets",
        "generation": "basket_state_context_v1",
        "state": "READ" if inputs.basket_context else "DEGRADED",
        "note": "Basket context is admitted without recomputation of basket membership.",
    })
    receipts.append({
        "owner": "macro_rates_credit",
        "generation": "macro_context_v1",
        "state": "READ" if inputs.macro_context else "DEGRADED",
        "note": "Macro driver mechanisms are admitted as supplied by the owner.",
    })
    receipts.append({
        "owner": "identity",
        "generation": "identity_bindings_v1",
        "state": "READ" if inputs.identity_bindings else "DEGRADED",
        "note": "Identity bindings are admitted as supplied by the owner.",
    })
    receipts.append({
        "owner": "private_publication",
        "generation": "source_records_v1",
        "state": "READ" if inputs.source_records else "DEGRADED",
        "note": "Source records are admitted display-tier and never contain private payloads.",
    })
    return receipts


def _degraded_sections(
    inputs: FinanceOwnerInputs,
    company_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    sections.append({
        "section": "what_changed",
        "state": "PARTIAL" if any(_material_changes_for(s["slice_id"], inputs.source_records) for s in []) else "AVAILABLE",
        "reason": None,
    })
    if not inputs.source_records:
        sections.append({
            "section": "evidence_drawer",
            "state": "UNAVAILABLE",
            "reason": "No source records were admitted; the evidence drawer is unavailable.",
        })
        sections.append({
            "section": "company_exposure",
            "state": "PARTIAL",
            "reason": "No company source records were admitted.",
        })
    else:
        sections.append({
            "section": "evidence_drawer",
            "state": "AVAILABLE",
            "reason": None,
        })
        sections.append({
            "section": "company_exposure",
            "state": "PARTIAL" if not company_rows else "AVAILABLE",
            "reason": None if company_rows else "No company exposure rows were admitted.",
        })
    for name in ("rerating_map", "system_map", "subtheme_atlas", "macro_matrix", "constraint_map"):
        sections.append({"section": name, "state": "AVAILABLE", "reason": None})
    return sections


# ---------------------------------------------------------------------------
# Outer dossier ref / freshness
# ---------------------------------------------------------------------------


def _outer_dossier_ref(inputs: FinanceOwnerInputs) -> dict[str, Any]:
    if inputs.sector_dossier is None:
        return {
            "contract_id": None,
            "dossier_id": None,
            "dossier_hash": None,
            "state": "OUTER_CONTRACT_NOT_ACCEPTED",
        }
    dossier_id = inputs.sector_dossier.get("dossier_id")
    dossier_hash = inputs.sector_dossier.get("dossier_hash")
    return {
        "contract_id": "sector_dossier_read_model.v1",
        "dossier_id": dossier_id,
        "dossier_hash": dossier_hash,
        "state": "AVAILABLE" if dossier_id and dossier_hash else "UNAVAILABLE",
    }


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------


def _all_slices_sorted() -> list[str]:
    return list(_FINANCE_SLICE_IDS)


def compose_finance_projection(
    inputs: FinanceOwnerInputs,
    *,
    generated_at: datetime,
    knowledge_cutoff: datetime,
    composer_version: str = "finance_projection/1",
    stale_after_days: int = 120,
) -> dict[str, Any]:
    """Compose the Finance Sector Intelligence read-model document.

    Pure: no I/O, no network, no store, no env, no clock reads
    (``generated_at`` / ``knowledge_cutoff`` are parameters; ``common_as_of``
    is the minimum over the input as-of dates actually consumed, never
    ``now``).
    """
    slice_catalog = {c.get("slice_id"): c for c in inputs.slice_catalog if isinstance(c, Mapping)}
    slice_id_to_atlas_id: dict[str, str] = {}
    for slice_id in _FINANCE_SLICE_IDS:
        if slice_id in slice_catalog:
            slice_id_to_atlas_id[slice_id] = slice_id
        else:
            slice_id_to_atlas_id[slice_id] = slice_id

    source_records, source_record_extras = _source_records_block(inputs)
    # Structural check: datetime has a ``time`` part, date does not.
    # Survives a monkey-patched ``datetime`` symbol.
    if hasattr(knowledge_cutoff, "hour") and hasattr(knowledge_cutoff, "minute"):
        knowledge_cutoff_date = knowledge_cutoff.date()
    else:
        knowledge_cutoff_date = knowledge_cutoff

    all_slice_ids = _all_slices_sorted()
    rights_profiles: set[str] = set()
    for rec in source_records:
        rights_profiles.add(rec.get("rights_state", "SOURCE_RIGHTS_HELD"))

    slices_out: list[dict[str, Any]] = []
    all_observed_dates: list[date] = []
    for slice_id in all_slice_ids:
        per_slice = _slice_inputs_for(slice_id, inputs)
        expectation_obs = per_slice["expectation_obs"]
        market_obs = per_slice["market_obs"]
        basket = per_slice["basket"]
        regime = per_slice["regime"]
        evidence_refs = _slice_evidence_refs(slice_id, source_records, expectation_obs, market_obs)

        operating = _operating_plane(
            slice_id,
            inputs.financial_packets,
            regime,
            evidence_refs,
        )
        expectations = _expectations_plane(slice_id, expectation_obs, evidence_refs, regime)
        valuation = _valuation_plane(slice_id, inputs.financial_packets, market_obs, evidence_refs, regime)
        price = _price_plane(slice_id, market_obs, evidence_refs, regime)

        material_changes = _material_changes_for(slice_id, inputs.source_records)
        company_rows_for_slice: list[dict[str, Any]] = []  # populated below
        # Collect operating and valuation observations across all
        # financial_packets for this slice so the conflict grammar can
        # read the freshest direction.
        op_observations: list[Mapping[str, Any]] = []
        val_observations: list[Mapping[str, Any]] = []
        for label, packet in inputs.financial_packets.items():
            if not isinstance(packet, Mapping):
                continue
            operating_packet = packet.get("operating")
            if isinstance(operating_packet, Mapping):
                for obs in operating_packet.get("observations") or ():
                    if isinstance(obs, Mapping):
                        if not obs.get("slice_id") or obs.get("slice_id") == slice_id:
                            op_observations.append(obs)
            valuation_packet = packet.get("valuation")
            if isinstance(valuation_packet, Mapping):
                for obs in valuation_packet.get("observations") or ():
                    if isinstance(obs, Mapping):
                        if not obs.get("slice_id") or obs.get("slice_id") == slice_id:
                            val_observations.append(obs)
        conflicts = _conflicts_for(
            slice_id,
            company_rows_for_slice,
            operating,
            valuation,
            price,
            regime,
            material_changes,
            inputs.macro_context,
            operating_observations=op_observations,
            valuation_observations=val_observations,
            market_observations=list(market_obs),
        )

        slice_state = _slice_state_for(slice_id, operating, expectations, valuation, price, rights_profiles)
        slice_freshness, latest_obs = _slice_freshness(
            slice_id, source_records, expectation_obs, market_obs, knowledge_cutoff_date, stale_after_days
        )
        if latest_obs is not None:
            all_observed_dates.append(latest_obs)

        name_en, name_zh = _name_pair(slice_id)
        slice_doc = {
            "slice_id": slice_id,
            "domain_id": _domain_of(slice_id),
            "name_en": name_en,
            "name_zh": name_zh,
            "slice_state": slice_state,
            "basket_state": _basket_state_for(slice_id, basket),
            "economic_job": _economic_job(slice_id),
            "revenue_mechanism": _revenue_mechanism(slice_id),
            "retained_risk": _retained_risk(slice_id),
            "rerating": {
                "operating": operating,
                "expectations": expectations,
                "valuation": valuation,
                "price": price,
                "bridge": _bridge_text(operating["state"], expectations["state"], valuation["state"], price["state"]),
                "falsifier_ids": [],
            },
            "indicators": [],
            "valuation_anchor": _valuation_anchor_for(slice_id, valuation),
            "conflict_ids": [c["conflict_id"] for c in conflicts],
            "falsifiers": [],
            "freshness": slice_freshness,
            "evidence_refs": evidence_refs,
        }
        # Regime-break must suppress percent-change arithmetic everywhere on
        # this slice. We never emit change_pct/delta/delta_pct/pp keys.
        slices_out.append(slice_doc)

    company_rows = _company_rows(inputs, slice_id_to_atlas_id, source_record_extras, inputs.source_records)

    # Second pass: now that company rows exist, re-attach conflict_ids for
    # any per-slice conflicts that should reference company rows.
    conflicts_out: list[dict[str, Any]] = []
    company_rows_by_slice: dict[str, list[dict[str, Any]]] = {}
    for row in company_rows:
        for cell in row.get("cells") or []:
            sid = cell.get("slice_id")
            if sid:
                company_rows_by_slice.setdefault(sid, []).append(row)

    for slice_doc in slices_out:
        slice_id = slice_doc["slice_id"]
        per_slice = _slice_inputs_for(slice_id, inputs)
        expectation_obs = per_slice["expectation_obs"]
        market_obs = per_slice["market_obs"]
        evidence_refs = slice_doc["evidence_refs"]
        operating = slice_doc["rerating"]["operating"]
        valuation = slice_doc["rerating"]["valuation"]
        price = slice_doc["rerating"]["price"]
        material_changes = _material_changes_for(slice_id, inputs.source_records)
        rows_for_slice = company_rows_by_slice.get(slice_id, [])
        op_observations: list[Mapping[str, Any]] = []
        val_observations: list[Mapping[str, Any]] = []
        for label, packet in inputs.financial_packets.items():
            if not isinstance(packet, Mapping):
                continue
            operating_packet = packet.get("operating")
            if isinstance(operating_packet, Mapping):
                for obs in operating_packet.get("observations") or ():
                    if isinstance(obs, Mapping):
                        if not obs.get("slice_id") or obs.get("slice_id") == slice_id:
                            op_observations.append(obs)
            valuation_packet = packet.get("valuation")
            if isinstance(valuation_packet, Mapping):
                for obs in valuation_packet.get("observations") or ():
                    if isinstance(obs, Mapping):
                        if not obs.get("slice_id") or obs.get("slice_id") == slice_id:
                            val_observations.append(obs)
        # Always re-compute conflicts: the first pass used an empty
        # company-row list because rows were built later. Re-running with
        # the now-final rows gives every slice a deterministic
        # conflict set, regardless of whether the slice has rows.
        conflicts = _conflicts_for(
            slice_id,
            rows_for_slice,
            operating,
            valuation,
            price,
            per_slice["regime"],
            material_changes,
            inputs.macro_context,
            operating_observations=op_observations,
            valuation_observations=val_observations,
            market_observations=list(market_obs),
        )
        slice_doc["conflict_ids"] = [c["conflict_id"] for c in conflicts]
        conflicts_out.extend(conflicts)

    # Domains
    domains = _domain_records(slices_out)

    # Material changes across the document
    material_changes_doc: list[dict[str, Any]] = []
    for sl in slices_out:
        for change in _material_changes_for(sl["slice_id"], inputs.source_records):
            # Strip the underscore-prefixed internal field before
            # emission (the schema's additionalProperties:false rejects
            # anything outside the declared set).
            change.pop("_freshness_state_raw", None)
            material_changes_doc.append(change)

    # Constraints
    constraints_doc = _constraints_for(inputs, slices_out)

    # Macro matrix
    macro_doc = _macro_matrix(inputs, slices_out)

    # System views
    system_views_doc = _system_views(slices_out)

    # common_as_of = min over the input as-ofs actually used, never now.
    as_of_candidates: list[date] = []
    for rec in source_records:
        d = _source_record_observed_at(rec)
        if d is not None:
            as_of_candidates.append(d)
    for obs in (inputs.expectation_observations or {}).values():
        for row in obs or ():
            if isinstance(row, Mapping):
                d = _coerce_date(row.get("as_of"))
                if d is not None:
                    as_of_candidates.append(d)
    for obs in (inputs.market_observations or {}).values():
        for row in obs or ():
            if isinstance(row, Mapping):
                d = _coerce_date(row.get("as_of"))
                if d is not None:
                    as_of_candidates.append(d)
    as_of_candidates.append(knowledge_cutoff_date)
    common_as_of = _min_date(as_of_candidates) or knowledge_cutoff_date

    # Coverage
    populated_count = sum(1 for s in slices_out if s["slice_state"] != "SEMANTIC_ONLY")
    semantic_only = sum(1 for s in slices_out if s["slice_state"] == "SEMANTIC_ONLY")
    populated_domains = sum(1 for d in domains if any(s["slice_state"] != "SEMANTIC_ONLY" for s in slices_out if s["domain_id"] == d["domain_id"]))
    coverage = {
        "domains_total": len(domains),
        "domains_populated": populated_domains,
        "slices_total": 52,
        "slices_populated": populated_count,
        "slices_semantic_only": semantic_only,
        "companies_with_records": sum(1 for r in company_rows if r.get("cells")),
        "first_vertical": {
            "name": "Financial Rails & Market Infrastructure",
            "slice_ids": sorted(_FIRST_VERTICAL_SLICE_IDS),
            "state": "SYNTHETIC",
        },
    }

    # Freshness
    freshness: dict[str, Any] = {
        "evidence_latest_observed_at": max(all_observed_dates).isoformat() if all_observed_dates else None,
        "state": _aggregate_freshness([s["freshness"] for s in slices_out]),
        "stale_after_days": stale_after_days,
    }

    # Outer dossier ref
    outer = _outer_dossier_ref(inputs)

    # Degraded sections
    degraded = _degraded_sections(inputs, company_rows)

    # Input receipts
    input_receipts = _input_receipts(inputs)

    document: dict[str, Any] = {
        "contract_id": "finance_intelligence_read_model.v1",
        "schema_version": "1.0.0",
        "generated_at": _to_iso(generated_at),
        "knowledge_cutoff": _to_iso(knowledge_cutoff),
        "common_as_of": common_as_of.isoformat(),
        "sector_ref": "sector:financials",
        "outer_dossier_ref": outer,
        "snapshot_identity": {
            "composer_version": composer_version,
            "input_digest": _hash_inputs(inputs, composer_version),
            "curation_revision_set": _curation_revisions(inputs.theme_evidence),
            "rights_profile": _rights_profile(inputs.rights_snapshot),
            "view_scope": "first_vertical",
        },
        "coverage": coverage,
        "material_changes": material_changes_doc,
        "domains": domains,
        "slices": slices_out,
        "company_exposures": company_rows,
        "system_views": system_views_doc,
        "macro_matrix": macro_doc,
        "constraints": constraints_doc,
        "conflicts": conflicts_out,
        "source_records": source_records,
        "freshness": freshness,
        "input_receipts": input_receipts,
        "degraded_sections": degraded,
        "authority_caps": dict(_AUTHORITY_CAPS),
    }

    # Forbidden-key guard (defensive). authority_caps.rank is permitted by
    # the schema (additionalProperties=false, but the rank key is allowed).
    if _has_change_pct_or_delta(document):
        raise AssertionError("composer emitted a forbidden change_pct/delta field under regime break")
    return document


def _aggregate_freshness(per_slice_freshness: Sequence[Mapping[str, Any]]) -> str:
    if not per_slice_freshness:
        return "NO_EVIDENCE"
    states = [s["state"] for s in per_slice_freshness]
    if "SOURCE_STALE" in states:
        return "SOURCE_STALE"
    if all(s == "NO_EVIDENCE" for s in states):
        return "NO_EVIDENCE"
    if "AGING" in states:
        return "AGING"
    return "FRESH"


# ---------------------------------------------------------------------------
# Plain-language descriptors per slice (closed catalog).
# ---------------------------------------------------------------------------


_ECONOMIC_JOBS: dict[str, str] = {
    "card_networks": "Operate the rails that move card payments between issuers, acquirers and consumers.",
    "merchant_acquiring_processing": "Capture and process card transactions on behalf of merchants.",
    "issuer_processing": "Run the back-office that issues cards and settles accounts on behalf of card issuers.",
    "exchanges_trading_venues": "Provide the matched-book venues where listed securities change hands.",
    "custody_asset_servicing": "Hold client assets and service the corporate actions, tax and reporting lifecycle.",
    "market_reference_data": "Publish the reference data that other market participants consume.",
    "ratings_credit_information": "Publish credit opinions that gate access to debt capital markets.",
    "indices_benchmarks_etf_plumbing": "Publish indices and the ETF plumbing that turn those indices into investable products.",
    "ach_instant_b2b": "Move account-to-account money on instant and batch rails.",
    "cross_border_remittance": "Move retail money across borders and currencies.",
    "gateways_orchestration": "Route payment traffic across acquirers, networks and fraud screens.",
    "embedded_finance_baas": "Provide banking-as-a-service APIs to non-bank software platforms.",
    "fraud_identity_tokenization": "Authenticate parties to a transaction and replace cardholder data with tokens.",
    "regtech_kyc_aml": "Provide identity, sanctions and anti-money-laundering controls to regulated firms.",
    "financial_cybersecurity": "Protect financial firms and their customers from cyber attacks.",
    "core_banking_financial_software": "Provide the core banking and ledger systems that banks run on.",
    "stablecoin_infrastructure": "Issue and redeem regulated stablecoins and the reserves behind them.",
    "digital_custody_tokenized_securities": "Hold tokenized securities and the private keys behind them.",
    "open_banking_api_finance": "Provide standardized APIs over bank-held customer data.",
    "agentic_ai_finance_workflow": "Run AI agents against the data and tools a financial firm already trusts.",
    "deposit_franchise_quality": "Collect sticky retail deposits and lend them out at a margin.",
    "universal_money_center_banks": "Provide universal commercial and investment banking at global scale.",
    "regional_superregional_banks": "Collect deposits and lend across regional footprints in the United States.",
    "community_local_banks": "Serve local lending, deposit and treasury needs.",
    "nim_curve_normalization": "Capture the gap between asset yields and funding costs as curves normalize.",
    "cre_credit_cycle": "Provide and service commercial real estate credit through the cycle.",
    "cards_consumer_credit": "Issue cards and other unsecured consumer credit.",
    "specialty_auto_equipment_finance": "Provide loans against autos and equipment to consumers and businesses.",
    "digital_banks_neobanks": "Run a retail or small-business bank without a branch network.",
    "mortgage_originators": "Originate residential mortgage loans and sell them to investors.",
    "mortgage_servicers_msr": "Service mortgage loans and earn the servicing fee strip.",
    "equity_debt_capital_markets": "Underwrite and place equity and debt securities for issuers.",
    "mna_advisory": "Advise buyers and sellers on mergers and acquisitions.",
    "electronic_market_makers": "Provide continuous two-sided liquidity on electronic venues.",
    "options_derivatives_ecosystem": "Provide the clearing, custody and execution layer for listed derivatives.",
    "clearing_ccp_csd": "Run central counterparties and securities depositories.",
    "prime_brokerage_securities_lending": "Provide prime brokerage and securities lending to hedge funds.",
    "passive_etf_asset_managers": "Run passive and ETF strategies that track benchmarks.",
    "active_asset_managers": "Run active strategies in equities, fixed income and alternatives.",
    "wealth_platforms_rias": "Provide wealth platforms and registered investment advisers.",
    "retirement_recordkeeping": "Recordkeep defined-contribution and other retirement plans.",
    "alternative_asset_managers": "Run private equity, private credit, real estate and infrastructure strategies.",
    "private_credit_managers": "Provide direct lending and other private credit strategies.",
    "bdc_direct_lending_vehicles": "Run business-development companies and other direct lending vehicles.",
    "fund_admin_middle_backoffice": "Provide fund administration and middle/back-office services.",
    "personal_pc_insurance": "Provide personal lines property and casualty insurance.",
    "commercial_specialty_pc": "Provide commercial and specialty property and casualty insurance.",
    "reinsurance": "Provide reinsurance to primary insurers.",
    "insurance_brokers": "Place insurance risk with carriers on behalf of clients.",
    "mga_delegated_underwriting": "Underwrite on behalf of carriers under delegated authority.",
    "life_annuity_spread": "Provide life and annuity products and capture the spread on the book.",
    "claims_insurance_data_workflow": "Run the claims workflow and the data systems behind it.",
}


def _economic_job(slice_id: str) -> str:
    return _ECONOMIC_JOBS.get(slice_id, "Plain-language economic job for this finance slice is preserved verbatim.")


_REVENUE_MECHANISMS: dict[str, str] = {
    "card_networks": "Earn a take rate on every transaction that crosses the network.",
    "merchant_acquiring_processing": "Earn a per-transaction fee plus residuals on processed volume.",
    "issuer_processing": "Earn per-account and per-transaction processing fees.",
    "exchanges_trading_venues": "Earn maker-taker fees and data fees on traded volume.",
    "custody_asset_servicing": "Earn custody fees on assets held and fees on servicing events.",
    "market_reference_data": "Earn subscription fees on reference data feeds.",
    "ratings_credit_information": "Earn issuer and investor fees on rating and credit opinions.",
    "indices_benchmarks_etf_plumbing": "Earn index licensing fees on assets that track the index.",
    "ach_instant_b2b": "Earn per-transaction fees on instant and batch payment rails.",
    "cross_border_remittance": "Earn the spread between FX and the fee charged to senders.",
    "gateways_orchestration": "Earn routing and gateway fees on payment traffic.",
    "embedded_finance_baas": "Earn per-account and per-transaction fees from embedded partners.",
    "fraud_identity_tokenization": "Earn per-transaction fees for authentication and tokenization.",
    "regtech_kyc_aml": "Earn subscription and per-check fees on KYC and AML controls.",
    "financial_cybersecurity": "Earn subscription and per-seat fees on cybersecurity products.",
    "core_banking_financial_software": "Earn subscription or perpetual license fees on core banking systems.",
    "stablecoin_infrastructure": "Earn interest on reserves and fees on issuance and redemption.",
    "digital_custody_tokenized_securities": "Earn custody fees on tokenized assets held in qualified custody.",
    "open_banking_api_finance": "Earn per-call or subscription fees on standardized bank-data APIs.",
    "agentic_ai_finance_workflow": "Earn per-task or outcome fees from AI agents deployed inside the workflow.",
    "deposit_franchise_quality": "Earn the spread between asset yields and funding costs.",
    "universal_money_center_banks": "Earn the spread between asset yields and funding costs plus fee income across capital markets.",
    "regional_superregional_banks": "Earn the spread between asset yields and funding costs.",
    "community_local_banks": "Earn the spread between asset yields and funding costs.",
    "nim_curve_normalization": "Earn the spread between asset yields and funding costs as the curve normalizes.",
    "cre_credit_cycle": "Earn net interest margin plus fees on commercial real estate loans.",
    "cards_consumer_credit": "Earn net interest margin and interchange on cards and consumer loans.",
    "specialty_auto_equipment_finance": "Earn net interest margin on auto and equipment loans.",
    "digital_banks_neobanks": "Earn net interest margin and interchange on a digital balance sheet.",
    "mortgage_originators": "Earn origination gains on mortgages sold to investors.",
    "mortgage_servicers_msr": "Earn the servicing strip on loans being serviced for others.",
    "equity_debt_capital_markets": "Earn gross spread on underwritten securities.",
    "mna_advisory": "Earn advisory fees as a percentage of transaction value.",
    "electronic_market_makers": "Earn the bid-ask spread on two-sided quotes.",
    "options_derivatives_ecosystem": "Earn clearing, execution and market-data fees.",
    "clearing_ccp_csd": "Earn clearing fees on notional cleared and custody fees on securities held.",
    "prime_brokerage_securities_lending": "Earn financing spreads and securities lending fees.",
    "passive_etf_asset_managers": "Earn basis-point fees on assets under management.",
    "active_asset_managers": "Earn basis-point fees on assets under management plus performance fees where applicable.",
    "wealth_platforms_rias": "Earn basis-point fees on platform assets and adviser fees on managed assets.",
    "retirement_recordkeeping": "Earn per-participant recordkeeping fees.",
    "alternative_asset_managers": "Earn management fees and carried interest on alternative fund AUM.",
    "private_credit_managers": "Earn management fees plus origination and structuring fees on private credit AUM.",
    "bdc_direct_lending_vehicles": "Earn net investment income on the BDC portfolio.",
    "fund_admin_middle_backoffice": "Earn per-fund and per-transaction fees on fund administration.",
    "personal_pc_insurance": "Earn premiums net of loss and expense ratios on personal lines.",
    "commercial_specialty_pc": "Earn premiums net of loss and expense ratios on commercial and specialty lines.",
    "reinsurance": "Earn premiums net of loss and expense ratios on assumed risk.",
    "insurance_brokers": "Earn commissions and fees on placed insurance premiums.",
    "mga_delegated_underwriting": "Earn underwriting profit on delegated authority binding.",
    "life_annuity_spread": "Earn the spread between investment yield and crediting rates on the life and annuity book.",
    "claims_insurance_data_workflow": "Earn per-claim fees and software fees on claims workflow platforms.",
}


def _revenue_mechanism(slice_id: str) -> str:
    return _REVENUE_MECHANISMS.get(slice_id, "Plain-language revenue mechanism for this finance slice is preserved verbatim.")


_RETAINED_RISKS: dict[str, str] = {
    "card_networks": "Volume is exposed to shifts in consumer spend and to regulatory caps on interchange.",
    "merchant_acquiring_processing": "Volume is exposed to merchant churn, scheme fees and chargebacks.",
    "issuer_processing": "Volume is exposed to card-portfolio growth and to fraud losses on issuer processing.",
    "exchanges_trading_venues": "Volume is exposed to volatility cycles and to migration between lit and dark venues.",
    "custody_asset_servicing": "Fee rate is exposed to asset-class mix and to zero-balance policy rates.",
    "market_reference_data": "Subscription growth is exposed to vendor consolidation and to fee compression.",
    "ratings_credit_information": "Issuer revenue is exposed to debt issuance volumes and to regulatory licensing.",
    "indices_benchmarks_etf_plumbing": "Index revenue is exposed to passive flows and to benchmark-methodology disputes.",
    "ach_instant_b2b": "Volume is exposed to consumer behaviour shifts and to interchange caps.",
    "cross_border_remittance": "Volume is exposed to migrant income corridors and to FX volatility.",
    "gateways_orchestration": "Routing margin is exposed to scheme fee changes and to fraud losses.",
    "embedded_finance_baas": "Revenue is exposed to partner concentration and to regulatory licensing of the partner bank.",
    "fraud_identity_tokenization": "Revenue is exposed to scheme tokenization mandates and to chargeback liability.",
    "regtech_kyc_aml": "Revenue is exposed to regulatory perimeter changes and to in-house rebuild.",
    "financial_cybersecurity": "Revenue is exposed to incident severity and to security-tool commoditization.",
    "core_banking_financial_software": "Revenue is exposed to bank IT spend cycles and to vendor consolidation.",
    "stablecoin_infrastructure": "Revenue is exposed to reserve-yield moves and to stablecoin regulation.",
    "digital_custody_tokenized_securities": "Custody revenue is exposed to tokenized-asset adoption and to qualified-custody regulation.",
    "open_banking_api_finance": "Revenue is exposed to data-perimeter regulation and to bank-side paywalls.",
    "agentic_ai_finance_workflow": "Revenue is exposed to LLM cost, model risk policy and to buyer trust.",
    "deposit_franchise_quality": "Margin is exposed to deposit beta and to loan-loss provisioning through the cycle.",
    "universal_money_center_banks": "Margin is exposed to deposit beta and to losses across the credit cycle.",
    "regional_superregional_banks": "Margin is exposed to deposit beta and to commercial real estate credit losses.",
    "community_local_banks": "Margin is exposed to local CRE credit and to deposit-funding cost.",
    "nim_curve_normalization": "Margin is exposed to deposit-cost lag and to curve-shape moves.",
    "cre_credit_cycle": "Margin is exposed to property price moves and to refinancing risk at maturity.",
    "cards_consumer_credit": "Margin is exposed to loss-rate cycle and to interchange regulation.",
    "specialty_auto_equipment_finance": "Margin is exposed to vehicle collateral values and to dealer concentration.",
    "digital_banks_neobanks": "Margin is exposed to deposit-funding cost and to credit-loss cycle.",
    "mortgage_originators": "Gain-on-sale is exposed to mortgage rate volatility and to capacity cycles.",
    "mortgage_servicers_msr": "Servicing economics are exposed to prepayment speed and to escrow-balance float.",
    "equity_debt_capital_markets": "Revenue is exposed to issuance volume cycles and to league-table pressure.",
    "mna_advisory": "Revenue is exposed to M&A volumes and to league-table pressure.",
    "electronic_market_makers": "Margin is exposed to volatility and to inventory turnover.",
    "options_derivatives_ecosystem": "Revenue is exposed to volatility, to volume cycles and to fee compression.",
    "clearing_ccp_csd": "Revenue is exposed to clearing volume, to default-fund sizing and to recovery-and-resolution regulation.",
    "prime_brokerage_securities_lending": "Revenue is exposed to hedge-fund AUM, to short-interest and to financing cost.",
    "passive_etf_asset_managers": "Fee margin is exposed to flow concentration and to fee compression.",
    "active_asset_managers": "Revenue is exposed to active-AUM outflows and to performance fee crystallization.",
    "wealth_platforms_rias": "Revenue is exposed to adviser-headcount growth and to custody-bypass risk.",
    "retirement_recordkeeping": "Revenue is exposed to participant migration between recordkeepers and to fee compression.",
    "alternative_asset_managers": "Revenue is exposed to fundraising cycles, to DPI timing and to GP-stake secondary discount.",
    "private_credit_managers": "Revenue is exposed to spread compression and to default cycle.",
    "bdc_direct_lending_vehicles": "NAV is exposed to non-accrual migration and to dividend-coverage stress.",
    "fund_admin_middle_backoffice": "Revenue is exposed to fund-launch cadence and to outsourcing consolidation.",
    "personal_pc_insurance": "Margin is exposed to catastrophe losses and to auto-cycle severity.",
    "commercial_specialty_pc": "Margin is exposed to casualty severity and to reserve development.",
    "reinsurance": "Margin is exposed to catastrophe losses and to rate-cycle softening.",
    "insurance_brokers": "Revenue is exposed to premium-volume cycles and to placement competition.",
    "mga_delegated_underwriting": "Margin is exposed to carrier capacity withdrawal and to binding-cycle volatility.",
    "life_annuity_spread": "Margin is exposed to credit spreads and to policyholder behaviour.",
    "claims_insurance_data_workflow": "Revenue is exposed to carrier technology spend and to in-house build.",
}


def _retained_risk(slice_id: str) -> str:
    return _RETAINED_RISKS.get(slice_id, "Plain-language retained risk for this finance slice is preserved verbatim.")


__all__ = [
    "FinanceOwnerInputs",
    "compose_finance_projection",
    "_FINANCE_SLICE_IDS",
]
