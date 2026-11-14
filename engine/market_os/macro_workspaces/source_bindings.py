"""Pure source attribution for the existing Macro workspace owners.

The four correction maps below are relocated, unchanged, from their composers.
Those composers import aliases so corrections and consumer attribution share
one definition. This module reads only the supplied publication: no data files,
numerical owners, clocks, collectors, or fallback source discovery.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from engine.market_os.macro_workspaces import registry

LIQUIDITY_SOURCE_COMPONENT_MAP: dict[str, tuple[str, ...]] = {
    "net_liquidity": ("liquidity_overlay_level", "liquidity_quality_level", "net_liquidity_roc"),
    "nfci": ("nfci_pctile",),
    "ofr_fsi": ("ofr_fsi_pctile",),
    "hy_oas": ("hy_oas_z",),
}
LABOR_SOURCE_COMPONENT_MAP: dict[str, tuple[str, ...]] = {
    "claims": ("claims_momentum",),
    "indeed": ("job_postings_momentum",),
    "withheld_tax": ("income_growth_proxy",),
    "sahm": ("sahm_rule_level",),
    "recession_claims": ("claims_recession_subscore",),
}
GROWTH_SOURCE_COMPONENT_MAP: dict[str, tuple[str, ...]] = {
    "gdpnow": ("gdpnow_growth",),
    "wei": ("wei_growth",),
    "business_cycle_leading": ("leading_tier_momentum", "leading_diffusion"),
    "business_cycle_coincident": ("coincident_tier_momentum", "coincident_diffusion", "coincident_index_level"),
    "growth_axis": ("growth_axis_score",),
}
FINANCIAL_SOURCE_METRIC_MAP: dict[str, tuple[str, ...]] = {
    "nfci": ("nfci", "nfci_pctile", "nfci_change_13w", "nfci_credit_subindex"),
    "ofr_fsi": ("ofr_fsi", "ofr_fsi_pctile", "ofr_fsi_change_13w", "ofr_funding_functional"),
    "hy_oas": ("hy_oas_pct", "hy_oas_z"),
    "us10y": ("real_10y", "real_10y_pctile", "real_10y_chg_63d_bp"),
    "vol_regime": ("vix", "vol_regime_risk_score", "move_pctile"),
}

# Qualified against inflation_system.compose.v1's component construction and
# _sources(). This is NOT Inflation's correction map, which names metrics.
# The current-month nowcast has no matching published source disclosure; the
# next-release forecast record does not cover that different input.
INFLATION_DRIVER_SOURCE_MAP: dict[str, tuple[str, ...]] = {
    "cpi_headline_core": (
        "core_cpi_annualized_3m", "headline_cpi_annualized_3m", "core_cpi_yoy",
        "core_acceleration_3m_minus_6m", "core_minus_headline_yoy_gap",
    ),
    "cpi_sticky_flexible_proxies": (
        "sticky_flexible_spread", "sticky_acceleration_3m_minus_6m",
    ),
}
POLICY_DRIVER_SOURCE_MAP = {
    "cb_policy_rates": ("fed_funds_rate",),
    "fed_funds_futures": ("market_implied_path_12m_bp", "dots_vs_market_gap_bp"),
    "fomc_sep_dots": ("dots_vs_market_gap_bp",),
    "treasury_curve_real_yields": ("curve_2s10s", "real_10y"),
    "cb_balance_sheets": ("fed_balance_sheet_impulse_13w", "ecb_balance_sheet_impulse_13w", "boj_balance_sheet_impulse_13w"),
}
CENTRAL_BANK_DRIVER_SOURCE_MAP = {
    "cb_balance_sheets": ("cb_fed_balance_sheet_impulse_13w", "cb_ecb_balance_sheet_impulse_13w", "cb_boj_balance_sheet_impulse_13w"),
    "glt_component_receipts": ("glt_broad_dollar_contribution_z", "glt_high_yield_oas_contribution_z", "glt_real_yield_10y_contribution_z"),
}
DEBT_DRIVER_SOURCE_MAP = {
    "tga": ("tga_impulse_13w",),
    "net_issuance": ("net_issuance_sum_13w", "net_issuance_pace_delta_4w_vs_13w_avg_daily"),
    "treasury_auctions": ("auction_demand_spread_recent_vs_baseline", "auction_latest_high_yield"),
    "withheld_taxes": ("withheld_taxes_yoy_4w",),
    "bis_household_dsr": ("household_debt_service_ratio_level",),
    "bis_credit_gap": ("credit_gap_level",),
}
HOUSING_DRIVER_SOURCE_MAP = {
    "mortgage_rate": ("mortgage_30y_rate_level", "mortgage_30y_rate_change_13w"),
    "housing_starts": ("housing_starts_yoy", "permits_minus_starts_spread"),
    "building_permits": ("building_permits_yoy", "permits_minus_starts_spread"),
    "case_shiller_hpi": ("case_shiller_national_hpi_yoy",),
    "national_rent_zori": ("national_rent_zori_yoy",),
}
_MAPS = {
    ("liquidity_regime", "liquidity_regime.compose.v1"): LIQUIDITY_SOURCE_COMPONENT_MAP,
    ("labor_markets", "labor_markets.compose.v1"): LABOR_SOURCE_COMPONENT_MAP,
    ("growth_real_economy", "growth_real_economy.compose.v1"): GROWTH_SOURCE_COMPONENT_MAP,
    ("financial_conditions", "financial_conditions.compose.v1"): FINANCIAL_SOURCE_METRIC_MAP,
    ("inflation_system", "inflation_system.compose.v1"): INFLATION_DRIVER_SOURCE_MAP,
    ("monetary_policy", "monetary_policy.compose.v1"): POLICY_DRIVER_SOURCE_MAP,
    ("liquidity_central_banks", "liquidity_central_banks.compose.v1"): CENTRAL_BANK_DRIVER_SOURCE_MAP,
    ("national_debt_liabilities", "national_debt_liabilities.compose.v1"): DEBT_DRIVER_SOURCE_MAP,
    ("housing_real_estate", "housing_real_estate.compose.v1"): HOUSING_DRIVER_SOURCE_MAP,
}

# Exact constructor refinements, never conversions or a null-unit wildcard.
# Every exception is tied to the registry's accepted method and metric identity.
_UNIT_REFINEMENTS = {
    ("financial_conditions", "real_10y_pctile"): ("percentile", "pct", "percent"),
    ("financial_conditions", "nfci_credit_subindex"): ("z_score", "stddev", "z_score"),
    ("financial_conditions", "ofr_funding_functional"): ("z_score", "stddev", "z_score"),
    ("financial_conditions", "move_pctile"): ("percentile", "pct", "percent"),
    ("financial_conditions", "hy_oas_z"): ("z_score", "stddev", "z_score"),
    ("liquidity_central_banks", "glt_broad_dollar_contribution_z"): ("z_score", "stddev", "z_score"),
    ("liquidity_central_banks", "glt_high_yield_oas_contribution_z"): ("z_score", "stddev", "z_score"),
    ("liquidity_central_banks", "glt_real_yield_10y_contribution_z"): ("z_score", "stddev", "z_score"),
    ("national_debt_liabilities", "household_debt_service_ratio_level"): ("percent", "percent_of_disposable_income", "percent"),
    ("trade_flows", "import_price_index_level"): ("index", "index_nsa", "index"),
    ("trade_flows", "export_price_index_level"): ("index", "index_nsa", "index"),
    ("trade_flows", "export_import_coverage_ratio"): ("ratio", None, "ratio"),
    ("trade_flows", "terms_of_trade_proxy"): ("ratio", None, "ratio"),
}

# Axis components have no unit field in snapshot v1. These are the exact
# driver constructor units for the accepted v1 methods, not inferred labels.
_COMPONENT_UNITS = {
    "liquidity_regime": {
        "nfci_pctile": "percentile", "ofr_fsi_pctile": "percentile", "hy_oas_z": "z_score",
        "rates_scare_score": "score", "liquidity_overlay_level": "categorical",
        "liquidity_quality_level": "categorical", "net_liquidity_roc": "USD_bn",
    },
    "labor_markets": {
        "claims_momentum": "z_score", "job_postings_momentum": "percent", "income_growth_proxy": "percent",
        "sahm_rule_level": "ratio", "claims_recession_subscore": "ratio",
    },
    "growth_real_economy": {
        "gdpnow_growth": "percent", "wei_growth": "percent", "leading_tier_momentum": "index_pts",
        "coincident_tier_momentum": "index_pts", "leading_diffusion": "percent", "coincident_diffusion": "percent",
        "coincident_index_level": "index", "growth_axis_score": "z_score",
    },
    "inflation_system": {
        "core_cpi_annualized_3m": "pct_saar", "headline_cpi_annualized_3m": "pct_saar", "core_cpi_yoy": "pct_yoy",
        "current_month_core_nowcast_annualized": "pct_saar", "sticky_flexible_spread": "pp_spread",
        "core_acceleration_3m_minus_6m": "pp", "sticky_acceleration_3m_minus_6m": "pp", "core_minus_headline_yoy_gap": "pp",
    },
}
_DEFINITION_REFINEMENTS = {
    ("rates_curves", "us10y_level"): ("fred.DGS10", "fred.DGS10.us10y"),
    ("rates_curves", "us10y_real_level"): ("fred.DFII10", "fred.DFII10.us10y_real"),
    ("rates_curves", "term_premium_10y_level"): ("fred.THREEFYTP10", "fred.THREEFYTP10.term_premium_10y"),
    ("liquidity_central_banks", "cb_fed_balance_sheet_impulse_13w"): ("cb_desk.cbs[FED].bs_impulse.impulse_13w", "cb_desk.cbs.bs_impulse.impulse_13w"),
    ("liquidity_central_banks", "cb_ecb_balance_sheet_impulse_13w"): ("cb_desk.cbs[ECB].bs_impulse.impulse_13w", "cb_desk.cbs.bs_impulse.impulse_13w"),
    ("liquidity_central_banks", "cb_boj_balance_sheet_impulse_13w"): ("cb_desk.cbs[BOJ].bs_impulse.impulse_13w", "cb_desk.cbs.bs_impulse.impulse_13w"),
}


def _same_value(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    return left == right and (left is None) == (right is None)


def driver_binding(snapshot: Mapping[str, Any], driver: Mapping[str, Any]) -> dict:
    """An exact published input/source join, or an explicit unlinked result.

    Components require matching ID, owner field, raw value and constructor unit.
    Metrics require matching ID, definition, model version, raw value and unit
    (or explicitly qualified constructor definition/unit refinements).
    A source attribution never upgrades an absent or simulated input.
    """
    workspace = (snapshot.get("workspace") or {}).get("id")
    method = (snapshot.get("headline") or {}).get("method_version")
    result = {"schema": "mastermind.macro_driver_binding.v1", "state": "unlinked",
              "method_version": method, "input_kind": None, "input_id": None,
              "source_refs": [], "reason": "owner_method_unqualified"}
    if (workspace not in registry.WORKSPACE_IDS or method != registry.entry(workspace).get("method_version")
            or method != f"{workspace}.compose.v1"):
        return result
    identifier = driver.get("driver_id")
    components = [component for axis in (snapshot.get("axes") or {}).get("items") or []
                  for component in axis.get("components") or []
                  if component.get("component_id") == identifier]
    metric_identifier = identifier
    if (workspace, method, identifier) == ("financial_conditions", "financial_conditions.compose.v1", "hy_oas_z_credit_leg"):
        # This role has an exact underlying metric with the same raw value and
        # definition_id as the driver's owner_field; no label matching is used.
        metric_identifier = "hy_oas_z"
    metrics = [metric for metric in (snapshot.get("metrics") or {}).get("items") or []
               if metric.get("metric_id") == metric_identifier]
    metric = None
    if components:
        if (len(components) != 1 or components[0].get("owner_field") != driver.get("owner_field")
                or not _same_value(components[0].get("raw_value"), driver.get("value"))
                or identifier not in _COMPONENT_UNITS.get(workspace, {})
                or _COMPONENT_UNITS[workspace][identifier] != driver.get("unit")):
            return {**result, "reason": "input_identity_mismatch"}
        result.update(input_kind="component", input_id=identifier)
    elif len(metrics) == 1 and _same_value(metrics[0].get("value"), driver.get("value")) and (
            metrics[0].get("unit") == driver.get("unit") or
            _UNIT_REFINEMENTS.get((workspace, metric_identifier)) == (driver.get("unit"), metrics[0].get("unit"), metrics[0].get("value_type"))):
        metric = metrics[0]
        if (metric.get("model_version") != method or not (
                metric.get("definition_id") == driver.get("owner_field") or
                _DEFINITION_REFINEMENTS.get((workspace, metric_identifier)) ==
                (driver.get("owner_field"), metric.get("definition_id")))):
            return {**result, "reason": "input_identity_mismatch"}
        result.update(input_kind="metric", input_id=metric_identifier)
    else:
        return {**result, "reason": "input_identity_mismatch"}
    mapping = _MAPS.get((workspace, method), {})
    expected = [source for source, members in mapping.items() if (metric_identifier if metric else identifier) in members]
    if not expected and metric:
        expected = list(metric.get("source_refs") or [])
    if not expected:
        return {**result, "reason": "source_mapping_absent"}
    sources = (snapshot.get("sources") or {}).get("items") or []
    resolved = []
    for reference in expected:
        candidates = [source for source in sources if source.get("source_id") == reference]
        if not candidates:
            fred = re.fullmatch(r"FRED:([A-Z0-9_]+)", reference)
            if fred:
                candidates = [source for source in sources
                              if source.get("artifact_ref") == f"data/fred/{fred.group(1)}.parquet"]
        if len(candidates) != 1:
            return {**result, "reason": "source_disclosure_ambiguous" if candidates else "source_disclosure_missing"}
        resolved.append(candidates[0]["source_id"])
    if len(set(resolved)) != len(resolved):
        return {**result, "reason": "source_disclosure_ambiguous"}
    return {**result, "state": "bound", "source_refs": resolved, "reason": None}
