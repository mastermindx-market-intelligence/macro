"""T10 measurement-only regional scenario map for the global-liquidity programme.

Adds a versioned, measurement-only regional view beside the T05 producer
(``engine.global_liquidity_transmission.py``). Five regions are qualified
separately -- us, euro_area, japan, china, hong_kong -- as ``measured``,
``assumption_only_context`` or ``missing_input`` from injected owner inputs.
ECB and BoJ stocks stay in local units with a separate FX-translation line
that is never fresh money and never uses a fixing after ``as_of``. China
carries PBoC stance and TSF direction as non-comparable context; the PBoC
balance sheet is ``missing_input``. Hong Kong is ``missing_input`` without a
qualified HKMA aggregate-balance owner.

C06 (T3 register): no global scalar; a global aggregate request is refused
and the map reports ``insufficient_comparable_pit_coverage``.
C19: US reserve/funding identities and the T08 conditional-accounting
scenario are refused outside the US; PBoC FX reserves are refused as a
balance-sheet substitute.  Producer output (``regional_gates``) stays empty.

Pure functions only: pure data in, pure data out.  Dates are normalised
to :class:`datetime.date` before comparison; a ``datetime`` is never compared
to a ``date``.
"""
from __future__ import annotations

import numbers
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Any, Optional

from engine.global_liquidity_accounting import fx_rate_to_usd
from engine.global_liquidity_outlook import (
    ESTIMATE_TYPES,
    SCHEMA as T08_SCHEMA,
)

__all__ = [
    "SCHEMA",
    "AUTHORITY",
    "VALIDATED",
    "CLAIM_LEVEL",
    "FIT_POLICY",
    "REGIONS",
    "STATUSES",
    "PIT_STATUS_VOCAB",
    "ESTIMATE_TYPES",
    "LOCAL_UNIT",
    "STOCK_CONCEPT",
    "STOCK_LABEL",
    "S11_COMPONENT",
    "S11_LOCAL_UNIT",
    "REFUSED_SUBSTITUTE_STORES",
    "FX_RESERVE_COLUMNS",
    "US_RESERVE_IDENTITY",
    "US_FUNDING_IDENTITY",
    "US_CONDITIONAL_ACCOUNTING",
    "US_LAW_IDS",
    "LOCAL_UNIT_STOCK",
    "FX_TRANSLATION_NOT_FRESH_MONEY",
    "BOJ_MONTH_END_ANCHOR",
    "CN_TSF_NON_COMPARABLE",
    "FX_RESERVES_NOT_BALANCE_SHEET",
    "HK_CURRENCY_BOARD_AGG_BALANCE",
    "NO_GLOBAL_SCALAR",
    "PBOC_MISSING_TEXT",
    "HK_MISSING_TEXT",
    "AGGREGATE_NULL_STATUS",
    "AGGREGATE_NULL_REASON",
    "CN_NO_QUANTITY_ASSUMPTION",
    "RegionalScenarioRefused",
    "refuse_us_law_transfer",
    "refuse_fx_reserves_substitute",
    "refuse_future_fixing",
    "refuse_global_aggregate",
    "s11_stock_owner",
    "s11_fx_pair",
    "qualify_region",
    "build_scenario_map",
    "RegionEntry",
]


# ---------------------------------------------------------------------------
# S1  module constants (exact names and values)
# ---------------------------------------------------------------------------

SCHEMA = "glt_regional_scenario_map.v1"
AUTHORITY = "measurement_only"
VALIDATED = False
CLAIM_LEVEL = "regional_qualification_display_tier"
FIT_POLICY = "new empirical fits use T14"

REGIONS = ("us", "euro_area", "japan", "china", "hong_kong")
STATUSES = ("measured", "assumption_only_context", "missing_input")
PIT_STATUS_VOCAB = (
    "release_lag_aligned_non_revised",
    "release_lag_aligned_revision_unknown",
)

LOCAL_UNIT = {
    "us": "USD",
    "euro_area": "EUR",
    "japan": "JPY",
    "china": "CNY",
    "hong_kong": "HKD",
}

STOCK_CONCEPT = {
    "us": "central_bank_assets",
    "euro_area": "central_bank_assets",
    "japan": "central_bank_assets",
    "china": "central_bank_assets",
    "hong_kong": "hkma_aggregate_balance",
}

STOCK_LABEL = {
    "us": "Fed total assets (fed_total_assets)",
    "euro_area": "ECB total assets (ecb_total_assets)",
    "japan": "BoJ total assets (boj_total_assets)",
    "china": "PBoC total assets (central_bank_balance_sheet)",
    "hong_kong": "HKMA aggregate balance",
}

S11_COMPONENT = {"us": "fed", "euro_area": "ecb", "japan": "boj"}
S11_LOCAL_UNIT = {"fed": "USD", "ecb": "EUR", "boj": "JPY"}

REFUSED_SUBSTITUTE_STORES = (
    "data/china_pboc/fx_reserves.parquet",
    "data/china_omo/operations.parquet",
)
FX_RESERVE_COLUMNS = ("fx_reserves", "gold_reserves")

US_RESERVE_IDENTITY = "us_reserve_identity_r_eq_a_minus_n"
US_FUNDING_IDENTITY = "us_funding_identity_net_liquidity"
US_CONDITIONAL_ACCOUNTING = "us_conditional_accounting_t08"
US_LAW_IDS = (US_RESERVE_IDENTITY, US_FUNDING_IDENTITY, US_CONDITIONAL_ACCOUNTING)

LOCAL_UNIT_STOCK = "measured_stock_in_local_unit"
FX_TRANSLATION_NOT_FRESH_MONEY = "fx_translation_not_fresh_money"
BOJ_MONTH_END_ANCHOR = "boj_month_end_anchor"
CN_TSF_NON_COMPARABLE = "cn_tsf_non_comparable_to_us_credit"
FX_RESERVES_NOT_BALANCE_SHEET = "fx_reserves_not_central_bank_balance_sheet"
HK_CURRENCY_BOARD_AGG_BALANCE = "hk_currency_board_aggregate_balance"
NO_GLOBAL_SCALAR = "no_global_scalar"

PBOC_MISSING_TEXT = (
    "PBoC total assets (central_bank_balance_sheet): no repository owner store; "
    "data/china_pboc/fx_reserves.parquet is an asset-side FX position, refused as a substitute"
)
HK_MISSING_TEXT = (
    "HKMA aggregate balance: no qualified repository owner "
    "(data/hkma/interbank_liquidity.parquet agg_balance has unknown units and no first-known receipt)"
)

AGGREGATE_NULL_STATUS = "insufficient_comparable_pit_coverage"
AGGREGATE_NULL_REASON = (
    "no global liquidity scalar: regional stocks are in non-comparable local units "
    "with different release bases, China/HK have no qualified balance-sheet owner, "
    "and FX translation is not fresh money"
)
CN_NO_QUANTITY_ASSUMPTION = "cn_no_balance_sheet_quantity_implied"

_STOCK_REQUIRED_KEYS = (
    "owner_module",
    "store",
    "column",
    "local_unit",
    "unit_multiplier",
    "release_basis",
    "observed_at",
    "known_at",
    "pit_status",
    "concept",
)

_DEFAULT_NO_OWNER_TEXT = {
    "us": "Fed total assets (fed_total_assets): no owner input supplied (config/global_liquidity_transmission_v1.yml#monetary_components.fed)",
    "euro_area": "ECB total assets (ecb_total_assets): no owner input supplied (config/global_liquidity_transmission_v1.yml#monetary_components.ecb)",
    "japan": "BoJ total assets (boj_total_assets): no owner input supplied (config/global_liquidity_transmission_v1.yml#monetary_components.boj)",
    "china": PBOC_MISSING_TEXT,
    "hong_kong": HK_MISSING_TEXT,
}


# ---------------------------------------------------------------------------
# S2  errors and refusal helpers
# ---------------------------------------------------------------------------


class RegionalScenarioRefused(ValueError):
    """Refused regional qualification.  ``code`` is a stable string from S2."""

    def __init__(self, code: str, message: str, *, offending: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.offending = offending

    def __str__(self) -> str:
        return f"RegionalScenarioRefused[{self.code}]: {self.args[0]!s} (offending={self.offending!r})"


def _as_date(value: Any) -> date:
    """Normalise a date input to :class:`datetime.date`.

    ``datetime`` -> ``.date()``; ISO ``"YYYY-MM-DD..."`` string -> the first
    ten characters; anything else raises :class:`TypeError`.  Never compares
    a ``datetime`` to a ``date``.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise TypeError(f"date input must be date/datetime/str, got {type(value).__name__}")


def _ensure_number(name: str, value: Any) -> None:
    """Booleans and non-numbers are refused (S4 / S5); None is left to the caller's null ladder."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(f"{name!r} must not be a bool; got {value!r}")
    if not isinstance(value, numbers.Real):
        raise TypeError(f"{name!r} must be a real number; got {value!r}")
    return None


def refuse_us_law_transfer(region_id: str, law_ids) -> None:
    """Raise ``us_law_transfer`` when a US law is applied outside the US.

    ``law_ids`` may be None, one law id as a ``str``, or a flat list/tuple/set/
    frozenset of ``str``.  Any other shape cannot be verified free of US laws
    and is refused outside the US (fail-closed).
    """
    if region_id == "us" or law_ids is None:
        return None
    if isinstance(law_ids, str):
        law_ids = (law_ids,)
    if not isinstance(law_ids, (list, tuple, set, frozenset)) or not all(
        isinstance(lid, str) for lid in law_ids
    ):
        raise RegionalScenarioRefused(
            "us_law_transfer",
            "law_ids must be one law id or a flat collection of law ids; an "
            "unverifiable law list is refused outside the US",
            offending={"region_id": region_id, "law_ids": repr(law_ids)},
        )
    if any(lid in US_LAW_IDS for lid in law_ids):
        raise RegionalScenarioRefused(
            "us_law_transfer",
            "US reserve/funding identities and T08 conditional-accounting "
            "are refused outside the US",
            offending={"region_id": region_id, "law_ids": list(law_ids)},
        )
    return None


def refuse_fx_reserves_substitute(required_concept: str, offered: Any) -> None:
    """Refuse an FX-reserves position offered as a region's stock.

    The concept limb applies where the required concept is
    ``central_bank_assets``; the store and column limbs apply to every
    required concept (an FX-reserve store or column is never a balance-sheet
    quantity for any region).
    """
    if not isinstance(offered, dict):
        return None
    if required_concept == "central_bank_assets" and offered.get("concept") == "fx_reserves":
        raise RegionalScenarioRefused(
            "fx_reserves_as_balance_sheet",
            "FX reserves are refused as a central-bank balance-sheet substitute",
            offending=offered.get("store"),
        )
    store = offered.get("store")
    if store == "data/china_pboc/fx_reserves.parquet":
        raise RegionalScenarioRefused(
            "fx_reserves_as_balance_sheet",
            "data/china_pboc/fx_reserves.parquet is an asset-side FX position, "
            "refused as a substitute",
            offending=store,
        )
    column = offered.get("column")
    if column in FX_RESERVE_COLUMNS:
        raise RegionalScenarioRefused(
            "fx_reserves_as_balance_sheet",
            f"FX-reserve column {column!r} is refused as a substitute",
            offending=column,
        )
    return None


def refuse_future_fixing(fixing_date: Any, as_of: date) -> None:
    """Refuse an FX fixing whose publication date is after the cutoff."""
    fd = _as_date(fixing_date)
    if fd > as_of:
        raise RegionalScenarioRefused(
            "fx_fixing_after_as_of",
            f"FX fixing date {fd.isoformat()} is after as_of {as_of.isoformat()}",
            offending=fixing_date,
        )
    return None


def refuse_global_aggregate(request: Any) -> None:
    """Refuse any global aggregate / scalar request."""
    if request is not None:
        raise RegionalScenarioRefused(
            "global_aggregate_requested",
            "global aggregate / scalar requests are refused (C06)",
            offending=request,
        )
    return None


def _validate_owner_keys(stock: dict) -> Optional[list]:
    """Return the sorted list of required stock keys that are absent or None.

    Special-case: ``pit_status`` is reported when present but not in the
    PIT_STATUS_VOCAB.
    """
    missing = [k for k in _STOCK_REQUIRED_KEYS if stock.get(k) is None]
    ps = stock.get("pit_status")
    if ps is not None and ps not in PIT_STATUS_VOCAB:
        missing.append("pit_status")
    # Preserve spec ordering: remove "pit_status" duplicates if any
    return sorted(set(missing))

# ---------------------------------------------------------------------------
# S3 / S11  stock owner helpers
# ---------------------------------------------------------------------------


def s11_stock_owner(
    config: dict,
    component: str,
    *,
    observed_at: Any,
    known_at: Any,
    value: Any = None,
) -> dict:
    """Build a STOCK dict by copying verbatim from the S11 spec.

    ``config`` is the already-parsed S11 spec of
    ``config/global_liquidity_transmission_v1.yml``.
    """
    spec = config["monetary_components"][component]
    store = spec["store"]
    key = spec["key"]
    return {
        "concept": "central_bank_assets",
        "owner_module": (
            f"config/global_liquidity_transmission_v1.yml#monetary_components.{component}"
        ),
        "store": f"data/{store}/{key}.parquet",
        "column": spec["column"],
        "local_unit": S11_LOCAL_UNIT[component],
        "unit_multiplier": spec["unit_multiplier"],
        "value": value,
        "release_basis": (
            f"{spec['frequency']}; period_anchor={spec['period_anchor']}; "
            f"release_lag_bdays={spec['release_lag_bdays']}"
        ),
        "observed_at": observed_at,
        "known_at": known_at,
        "pit_status": spec["pit_status"],
        "revision_risk": spec.get("revision_risk"),
    }


def s11_fx_pair(config: dict, component: str) -> Optional[dict]:
    """Return the FX-fixing dict for a S11 component, or ``None`` when null."""
    fx = config["monetary_components"][component].get("fx")
    if fx is None:
        return None
    return {
        "pair": fx["key"],
        "invert": fx["invert"],
        "store": f"data/{fx['store']}/{fx['key']}.parquet",
        "column": fx["column"],
    }


# ---------------------------------------------------------------------------
# S4  stock qualification
# ---------------------------------------------------------------------------


def _qualify_stock(region_id: str, stock: Optional[dict], as_of: date) -> Optional[dict]:
    """Run the binding S4 sequence on one STOCK dict for ``region_id``.

    Returns the copied stock block on success; raises
    :class:`RegionalScenarioRefused` with the appropriate ``code`` on a
    structured refusal; returns ``None`` when the stock is "not qualified"
    (missing owner, missing fields, or null value).
    """
    if stock is None or not isinstance(stock, dict):
        return None

    # step 2: refuse FX reserves as a substitute -- runs for every region.
    refuse_fx_reserves_substitute(STOCK_CONCEPT[region_id], stock)

    # step 3: OMO / substitute store -> concept_mismatch
    if stock.get("store") in REFUSED_SUBSTITUTE_STORES:
        raise RegionalScenarioRefused(
            "concept_mismatch",
            f"store {stock.get('store')!r} is not a balance-sheet owner for {region_id!r}",
            offending=stock.get("store"),
        )

    # step 4: stock.concept (when present) must match STOCK_CONCEPT[region_id]
    if "concept" in stock and stock["concept"] is not None and stock["concept"] != STOCK_CONCEPT[region_id]:
        raise RegionalScenarioRefused(
            "concept_mismatch",
            f"concept {stock['concept']!r} != STOCK_CONCEPT[{region_id!r}]={STOCK_CONCEPT[region_id]!r}",
            offending=stock.get("concept"),
        )

    # step 5: stock.local_unit (when present) must match the region's local unit
    lu = stock.get("local_unit")
    if lu is not None and lu != LOCAL_UNIT[region_id]:
        raise RegionalScenarioRefused(
            "not_local_unit",
            f"stock.local_unit {lu!r} != {LOCAL_UNIT[region_id]!r} for {region_id!r}",
            offending=lu,
        )

    # step 6: known_at must not be after as_of
    known_at = stock.get("known_at")
    if known_at is not None:
        ka_d = _as_date(known_at)
        if ka_d > as_of:
            raise RegionalScenarioRefused(
                "known_after_as_of",
                f"stock.known_at {ka_d.isoformat()} is after as_of {as_of.isoformat()}",
                offending=known_at,
            )

    # step 6b: an observation dated after as_of cannot be known at as_of (protocol section 9)
    observed_at = stock.get("observed_at")
    if observed_at is not None:
        ob_d = _as_date(observed_at)
        if ob_d > as_of:
            raise RegionalScenarioRefused(
                "known_after_as_of",
                f"stock.observed_at {ob_d.isoformat()} is after as_of {as_of.isoformat()}",
                offending=observed_at,
            )

    # step 7: missing required keys
    missing = _validate_owner_keys(stock)
    if missing:
        return None

    # step 8: value is None -> null at as_of
    value = stock.get("value")
    if value is None:
        return None
    _ensure_number("stock.value", value)
    if stock.get("unit_multiplier") is None:
        raise TypeError("'stock.unit_multiplier' must be a real number; got None")
    _ensure_number("stock.unit_multiplier", stock.get("unit_multiplier"))

    # step 9: qualified -- copy without recomputing.
    return {
        "concept": stock["concept"],
        "owner_module": stock["owner_module"],
        "store": stock["store"],
        "column": stock["column"],
        "local_unit": stock["local_unit"],
        "unit_multiplier": stock["unit_multiplier"],
        "value": stock["value"],
        "release_basis": stock["release_basis"],
        "observed_at": _as_date(stock["observed_at"]).isoformat(),
        "known_at": _as_date(stock["known_at"]).isoformat(),
        "pit_status": stock["pit_status"],
        "revision_risk": stock.get("revision_risk"),
    }


def _build_fx_translation(
    region_id: str,
    slice_: dict,
    stock_block: dict,
    as_of: date,
) -> Optional[dict]:
    """Compose the FX translation block; never returns a fresh-money line."""
    fixing = slice_.get("fx_fixing") or {}
    fixing_date = fixing.get("fixing_date")
    if fixing_date is not None:
        refuse_future_fixing(fixing_date, as_of)

    quote = fixing.get("quote")
    _ensure_number("fixing.quote", quote)
    invert = bool(fixing.get("invert"))

    usd_per_local = None
    if fixing:
        usd_per_local = fx_rate_to_usd(quote, invert=invert)

    value = stock_block["value"]
    unit_multiplier = stock_block["unit_multiplier"]

    usd_value = None
    null_reason: Optional[str] = None
    if not fixing or fixing_date is None:
        # An undated fixing is not a qualified fixing (protocol section 9): no rate, no USD value.
        usd_per_local = None
        null_reason = "fx_fixing_missing"
    elif usd_per_local is None:
        null_reason = "fx_quote_unusable"
    else:
        usd_value = value * unit_multiplier * usd_per_local

    return {
        "pair": fixing.get("pair"),
        "invert": invert,
        "fixing_date": _as_date(fixing_date).isoformat() if fixing_date is not None else None,
        "usd_per_local": usd_per_local,
        "usd_value": usd_value,
        "is_fresh_money": False,
        "basis": "translation_only",
        "law_id": FX_TRANSLATION_NOT_FRESH_MONEY,
        "null_reason": null_reason,
    }


def _walk_keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk_keys(item)


def _has_forbidden_key(node, fragments) -> bool:
    """Recursive search for any key containing a forbidden fragment."""
    return any(any(frag in k for frag in fragments) for k in _walk_keys(node))


# ---------------------------------------------------------------------------
# S5  per-region rules + RegionEntry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegionEntry:
    """One row of the regional map; ``to_dict()`` is plain JSON-serialisable."""

    region_id: str
    status: str
    local_unit: str
    stock: Optional[dict]
    fx_translation: Optional[dict]
    context: list
    assumptions: list
    missing_inputs: list
    laws_applied: list
    laws_refused: list
    scenario: Optional[dict]

    def to_dict(self) -> dict:
        out = asdict(self)
        for k, v in out.items():
            if isinstance(v, tuple):
                out[k] = list(v)
        return out


def _validate_us_outlook(outlook: dict, as_of: date) -> dict:
    """Validate the injected T08 outlook against the S5 rules."""
    if not isinstance(outlook, dict):
        raise RegionalScenarioRefused(
            "us_scenario_invalid",
            "outlook must be a mapping",
            offending=type(outlook).__name__,
        )
    if outlook.get("schema") != T08_SCHEMA:
        raise RegionalScenarioRefused(
            "us_scenario_invalid",
            f"outlook.schema {outlook.get('schema')!r} != T08_SCHEMA {T08_SCHEMA!r}",
            offending=outlook.get("schema"),
        )
    if outlook.get("authority") != "measurement_only":
        raise RegionalScenarioRefused(
            "us_scenario_invalid",
            f"outlook.authority {outlook.get('authority')!r} != 'measurement_only'",
            offending=outlook.get("authority"),
        )
    if outlook.get("validated") is not False:
        raise RegionalScenarioRefused(
            "us_scenario_invalid",
            "outlook.validated must be False (T08 is measurement-only)",
            offending=outlook.get("validated"),
        )

    paths = outlook.get("paths") or {}
    if not isinstance(paths, dict):
        raise RegionalScenarioRefused(
            "us_scenario_invalid",
            "outlook.paths must be a mapping",
            offending=type(paths).__name__,
        )
    for comp, path in paths.items():
        if not isinstance(path, dict):
            raise RegionalScenarioRefused(
                "us_scenario_invalid",
                f"outlook path {comp!r} must be a mapping",
                offending=comp,
            )
        if path.get("estimate_type") not in ESTIMATE_TYPES:
            raise RegionalScenarioRefused(
                "us_scenario_invalid",
                f"path {comp!r}.estimate_type {path.get('estimate_type')!r} not in ESTIMATE_TYPES",
                offending=path.get("estimate_type"),
            )
    reserves = outlook.get("reserves") or {}
    if reserves.get("estimate_type") not in ESTIMATE_TYPES:
        raise RegionalScenarioRefused(
            "us_scenario_invalid",
            f"reserves.estimate_type {reserves.get('estimate_type')!r} not in ESTIMATE_TYPES",
            offending=reserves.get("estimate_type"),
        )
    sr = outlook.get("statistical_residual") or {}
    if sr.get("estimate_type") not in ESTIMATE_TYPES:
        raise RegionalScenarioRefused(
            "us_scenario_invalid",
            f"statistical_residual.estimate_type {sr.get('estimate_type')!r} not in ESTIMATE_TYPES",
            offending=sr.get("estimate_type"),
        )
    if _has_forbidden_key(outlook, ("probability",)):
        raise RegionalScenarioRefused(
            "us_scenario_invalid",
            "outlook payload contains a 'probability' key (forbidden)",
            offending=None,
        )

    outlook_asof = outlook.get("as_of")
    if outlook_asof is not None:
        try:
            ad = _as_date(outlook_asof)
        except (TypeError, ValueError):
            raise RegionalScenarioRefused(
                "us_scenario_invalid",
                f"outlook.as_of {outlook_asof!r} is not a date/datetime/str",
                offending=outlook_asof,
            )
        if ad > as_of:
            raise RegionalScenarioRefused(
                "known_after_as_of",
                f"outlook.as_of {ad.isoformat()} is after map as_of {as_of.isoformat()}",
                offending=outlook_asof,
            )

    return {
        "owner_module": "engine/global_liquidity_outlook.py",
        "source_schema": outlook["schema"],
        "source_as_of": outlook["as_of"],
        "source_claim_level": outlook["claim_level"],
        "component_estimate_types": {
            c: p["estimate_type"] for c, p in paths.items()
        },
        "reserves_estimate_type": reserves["estimate_type"],
        "statistical_residual_estimate_type": sr["estimate_type"],
        "authority": AUTHORITY,
        "validated": False,
    }


def _tsf_direction(latest: Any, prior: Any) -> tuple:
    if latest is None or prior is None:
        return None, "tsf_value_null"
    _ensure_number("tsf.latest", latest)
    _ensure_number("tsf.prior", prior)
    if latest > prior:
        return "higher", None
    if latest < prior:
        return "lower", None
    return "unchanged", None


def _china_tsf_item(tsf: dict, as_of: date) -> dict:
    ka = _as_date(tsf["known_at"])
    if ka > as_of:
        raise RegionalScenarioRefused(
            "known_after_as_of",
            f"tsf.known_at {ka.isoformat()} is after as_of {as_of.isoformat()}",
            offending=tsf.get("known_at"),
        )
    ob = _as_date(tsf["observed_at"])
    if ob > as_of:
        raise RegionalScenarioRefused(
            "known_after_as_of",
            f"tsf.observed_at {ob.isoformat()} is after as_of {as_of.isoformat()}",
            offending=tsf.get("observed_at"),
        )
    direction, dnull = _tsf_direction(tsf.get("latest"), tsf.get("prior"))
    item = {
        "kind": "tsf_direction",
        "store": "data/china_credit/tsf.parquet",
        "column": "tsf_total",
        "unit": "CNY 100 millions, monthly increment (flow)",
        "direction": direction,
        "observed_at": _as_date(tsf["observed_at"]).isoformat(),
        "known_at": ka.isoformat(),
        "comparability": "non_comparable_to_us_credit",
        "law_id": CN_TSF_NON_COMPARABLE,
    }
    if dnull is not None:
        item["direction_null_reason"] = dnull
    return item


def _china_stance_item(stance: dict, as_of: date) -> dict:
    if stance.get("schema") != "china_pboc_stance.v1":
        return None
    sa = _as_date(stance["asof"])
    if sa > as_of:
        raise RegionalScenarioRefused(
            "known_after_as_of",
            f"stance.asof {sa.isoformat()} is after as_of {as_of.isoformat()}",
            offending=stance.get("asof"),
        )
    return {
        "kind": "pboc_stance",
        "owner_module": "engine/china_pboc_stance.py",
        "schema": "china_pboc_stance.v1",
        "stance": stance["stance"],
        "asof": sa.isoformat(),
    }


def _qualify_us(slice_: dict, as_of: date) -> RegionEntry:
    stock_qualified = _qualify_stock("us", slice_.get("stock"), as_of)
    if stock_qualified is None:
        return RegionEntry(
            region_id="us",
            status="missing_input",
            local_unit=LOCAL_UNIT["us"],
            stock=None,
            fx_translation=None,
            context=[],
            assumptions=[],
            missing_inputs=[_missing_text_for("us", slice_.get("stock"))],
            laws_applied=[LOCAL_UNIT_STOCK, US_RESERVE_IDENTITY, US_FUNDING_IDENTITY, US_CONDITIONAL_ACCOUNTING],
            laws_refused=[],
            scenario=None,
        )

    scenario = None
    outlook = slice_.get("outlook")
    if outlook is not None:
        scenario = _validate_us_outlook(outlook, as_of)

    return RegionEntry(
        region_id="us",
        status="measured",
        local_unit=LOCAL_UNIT["us"],
        stock=stock_qualified,
        fx_translation=None,
        context=[],
        assumptions=[],
        missing_inputs=[],
        laws_applied=[LOCAL_UNIT_STOCK, US_RESERVE_IDENTITY, US_FUNDING_IDENTITY, US_CONDITIONAL_ACCOUNTING],
        laws_refused=[],
        scenario=scenario,
    )


def _missing_text_for(region_id: str, stock: Any) -> str:
    if not isinstance(stock, dict):
        return _DEFAULT_NO_OWNER_TEXT[region_id]
    missing = _validate_owner_keys(stock)
    if missing:
        return f"{STOCK_LABEL[region_id]}: missing owner field(s) {', '.join(missing)}"
    if stock.get("value") is None:
        return f"{STOCK_LABEL[region_id]}: owner value null at as_of"
    return _DEFAULT_NO_OWNER_TEXT[region_id]


def _qualify_euro_area(slice_: dict, as_of: date) -> RegionEntry:
    stock_qualified = _qualify_stock("euro_area", slice_.get("stock"), as_of)
    if stock_qualified is None:
        return RegionEntry(
            region_id="euro_area",
            status="missing_input",
            local_unit=LOCAL_UNIT["euro_area"],
            stock=None,
            fx_translation=None,
            context=[],
            assumptions=[],
            missing_inputs=[_missing_text_for("euro_area", slice_.get("stock"))],
            laws_applied=[LOCAL_UNIT_STOCK, FX_TRANSLATION_NOT_FRESH_MONEY],
            laws_refused=list(US_LAW_IDS),
            scenario=None,
        )
    return RegionEntry(
        region_id="euro_area",
        status="measured",
        local_unit=LOCAL_UNIT["euro_area"],
        stock=stock_qualified,
        fx_translation=_build_fx_translation("euro_area", slice_, stock_qualified, as_of),
        context=[],
        assumptions=[],
        missing_inputs=[],
        laws_applied=[LOCAL_UNIT_STOCK, FX_TRANSLATION_NOT_FRESH_MONEY],
        laws_refused=list(US_LAW_IDS),
        scenario=None,
    )


def _qualify_japan(slice_: dict, as_of: date) -> RegionEntry:
    stock_qualified = _qualify_stock("japan", slice_.get("stock"), as_of)
    if stock_qualified is None:
        return RegionEntry(
            region_id="japan",
            status="missing_input",
            local_unit=LOCAL_UNIT["japan"],
            stock=None,
            fx_translation=None,
            context=[],
            assumptions=[],
            missing_inputs=[_missing_text_for("japan", slice_.get("stock"))],
            laws_applied=[LOCAL_UNIT_STOCK, FX_TRANSLATION_NOT_FRESH_MONEY, BOJ_MONTH_END_ANCHOR],
            laws_refused=list(US_LAW_IDS),
            scenario=None,
        )
    return RegionEntry(
        region_id="japan",
        status="measured",
        local_unit=LOCAL_UNIT["japan"],
        stock=stock_qualified,
        fx_translation=_build_fx_translation("japan", slice_, stock_qualified, as_of),
        context=[],
        assumptions=[],
        missing_inputs=[],
        laws_applied=[LOCAL_UNIT_STOCK, FX_TRANSLATION_NOT_FRESH_MONEY, BOJ_MONTH_END_ANCHOR],
        laws_refused=list(US_LAW_IDS),
        scenario=None,
    )


def _qualify_hong_kong(slice_: dict, as_of: date) -> RegionEntry:
    stock_qualified = _qualify_stock("hong_kong", slice_.get("stock"), as_of)
    if stock_qualified is None:
        return RegionEntry(
            region_id="hong_kong",
            status="missing_input",
            local_unit=LOCAL_UNIT["hong_kong"],
            stock=None,
            fx_translation=None,
            context=[],
            assumptions=[],
            missing_inputs=[_missing_text_for("hong_kong", slice_.get("stock"))],
            laws_applied=[HK_CURRENCY_BOARD_AGG_BALANCE],
            laws_refused=list(US_LAW_IDS),
            scenario=None,
        )
    laws_applied = [HK_CURRENCY_BOARD_AGG_BALANCE, LOCAL_UNIT_STOCK, FX_TRANSLATION_NOT_FRESH_MONEY]
    return RegionEntry(
        region_id="hong_kong",
        status="measured",
        local_unit=LOCAL_UNIT["hong_kong"],
        stock=stock_qualified,
        fx_translation=_build_fx_translation("hong_kong", slice_, stock_qualified, as_of),
        context=[],
        assumptions=[],
        missing_inputs=[],
        laws_applied=laws_applied,
        laws_refused=list(US_LAW_IDS),
        scenario=None,
    )


def _qualify_china(slice_: dict, as_of: date) -> RegionEntry:
    stock_qualified = _qualify_stock("china", slice_.get("stock"), as_of)
    context = []
    missing_inputs = []

    stance = slice_.get("stance")
    if stance is not None:
        stance_item = _china_stance_item(stance, as_of)
        if stance_item is not None:
            context.append(stance_item)
        else:
            missing_inputs.append(
                f"PBoC stance context: owner schema {stance.get('schema')!r} is not china_pboc_stance.v1"
            )
    else:
        missing_inputs.append("PBoC stance context: no owner input supplied (engine/china_pboc_stance.py)")

    tsf = slice_.get("tsf")
    if tsf is not None:
        context.append(_china_tsf_item(tsf, as_of))
    else:
        missing_inputs.append("China TSF: no owner input supplied (data/china_credit/tsf.parquet)")

    if stock_qualified is None:
        missing_inputs.insert(0, _missing_text_for("china", slice_.get("stock")))

    if stock_qualified is not None:
        status = "measured"
        assumptions: list = []
    elif context:
        status = "assumption_only_context"
        assumptions = [CN_NO_QUANTITY_ASSUMPTION]
    else:
        status = "missing_input"
        assumptions = [CN_NO_QUANTITY_ASSUMPTION]

    return RegionEntry(
        region_id="china",
        status=status,
        local_unit=LOCAL_UNIT["china"],
        stock=stock_qualified,
        fx_translation=None,
        context=context,
        assumptions=assumptions,
        missing_inputs=missing_inputs,
        laws_applied=[FX_RESERVES_NOT_BALANCE_SHEET, CN_TSF_NON_COMPARABLE],
        laws_refused=list(US_LAW_IDS),
        scenario=None,
    )


_QUALIFY_DISPATCH = {
    "us": _qualify_us,
    "euro_area": _qualify_euro_area,
    "japan": _qualify_japan,
    "china": _qualify_china,
    "hong_kong": _qualify_hong_kong,
}


def qualify_region(region_id: str, *, owners: dict, as_of: date) -> RegionEntry:
    """Qualify one region from injected owners (S5)."""
    if region_id not in REGIONS:
        raise RegionalScenarioRefused(
            "unknown_region",
            f"region_id {region_id!r} not in REGIONS {REGIONS!r}",
            offending=region_id,
        )
    slice_ = (owners or {}).get(region_id) or {}
    refuse_us_law_transfer(region_id, slice_.get("law_ids", ()))
    if region_id != "us" and "outlook" in slice_:
        raise RegionalScenarioRefused(
            "us_scenario_transfer",
            f"outlook is US-only; refusing transfer to {region_id!r}",
            offending=region_id,
        )
    return _QUALIFY_DISPATCH[region_id](slice_, as_of)


# ---------------------------------------------------------------------------
# S6  map
# ---------------------------------------------------------------------------


def build_scenario_map(owners: dict, *, as_of: date, aggregate: Any = None) -> dict:
    """Build the full regional scenario map (S6)."""
    refuse_global_aggregate(aggregate)
    owners = owners or {}
    for key in owners.keys():
        if key == "global":
            raise RegionalScenarioRefused(
                "global_aggregate_requested",
                "owners key 'global' is refused (C06)",
                offending=key,
            )
        if key not in REGIONS:
            raise RegionalScenarioRefused(
                "unknown_region",
                f"owners key {key!r} not in REGIONS {REGIONS!r}",
                offending=key,
            )
    regions = {
        r: qualify_region(r, owners=owners, as_of=as_of).to_dict() for r in REGIONS
    }
    return {
        "schema": SCHEMA,
        "as_of": as_of.isoformat(),
        "regions": regions,
        "global_scalar": None,
        "aggregate_null_status": AGGREGATE_NULL_STATUS,
        "aggregate_null_reason": AGGREGATE_NULL_REASON,
        "aggregate_law_id": NO_GLOBAL_SCALAR,
        "authority": AUTHORITY,
        "validated": VALIDATED,
        "claim_level": CLAIM_LEVEL,
        "fit_policy": FIT_POLICY,
    }
