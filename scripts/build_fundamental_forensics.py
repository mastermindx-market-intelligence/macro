"""Build the display-only Filing Forensics workbench state and page.

This is deliberately a projection builder, not the canonical SEC lineage engine.
It reads the repository's already-normalized quarterly/annual EDGAR panels and
turns five transparent accounting checks into a compact browser artifact.  The
canonical accession-aware, acceptance-time replay engine lives in
``engine.fundamental_forensics`` and can replace this projection without changing
the UI contract once its scheduled raw store is available.

No finding produced here is a fraud claim, a company score, or trading authority.
The page is additive and fail-soft: a missing input leaves the last rendered page
untouched when called from the main site build.

The assembled state is written atomically to a gitignored local path.  Production
publishes that validated gzip to the existing private Research Vault object store;
the public repository and Pages mirror receive only the data-free shell/assets.

Usage::

    python -m scripts.build_fundamental_forensics
    python -m scripts.build_fundamental_forensics --publish-private
    python -m scripts.build_fundamental_forensics --publish-only
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import math
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd
from jinja2 import Environment, FileSystemLoader

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402
from engine.fundamental_forensics.private_state import (
    LOCAL_STATE_RELATIVE,
    MAX_COMPRESSED_BYTES,
    MAX_DECOMPRESSED_BYTES,
    STATE_SCHEMA,
    decode_state_blob,
    publish_state_blob,
)  # noqa: E402
from engine.fundamental_forensics.disclosure_projection import (
    DisclosureProjectionError,
    read_disclosure_projection_directory,
)  # noqa: E402
from engine.fundamental_forensics.detectors import issuer_class_for_sic  # noqa: E402
from engine.fundamental_forensics.metric_registry import (  # noqa: E402
    ISSUER_CLASSES,
    load_core_metric_registry,
    qualify_metric,
)
from engine.fundamental_forensics.peer_cohort import (  # noqa: E402
    CohortDefinition,
    CohortMember,
    MetricObservation,
    build_cohort_table,
)
from engine.fundamental_forensics.production_datasets import (  # noqa: E402
    ProductionDatasetError,
    build_production_dataset_store,
    load_latest_generation,
    registry_from_payload,
)

log = logging.getLogger("build_fundamental_forensics")

SCHEMA = STATE_SCHEMA

# The counts-only public projection: aggregate totals the anonymous gate may
# print, carried in a committed file because the private state is gitignored.
PUBLIC_SUMMARY_RELATIVE = Path("data/fundamental_forensics/public_summary.json")
PUBLIC_SUMMARY_SCHEMA = "fundamental_forensics.public_summary/v1"
# FIF P1-b: the committed authority tables and the pinned coverage contract
# that names the peer-cohort members. Both are read at runtime; no ticker,
# CIK, issuer id, or SIC literal lives in this file.
ISSUER_MASTER_RELATIVE = Path("data/reference/issuer_master.parquet")
COVERAGE_CONTRACT_RELATIVE = Path("config/fundamental_forensics/coverage/five_issuer_v1.json")
# The state payload envelope that carries the peer-cohort projection.
STATE_PAYLOAD_SCHEMA = "fundamental_forensics_state_payload.v1"
PEER_COHORT_REASON_DATASET_ABSENT = "production_dataset_absent"
PEER_COHORT_REASON_OVER_BUDGET = "state_byte_budget_exceeded"
# How long a committed projection may keep being published. daily.yml's run_py
# prints an ::error annotation for a failed builder but does NOT exit non-zero,
# so a broken forensics build leaves the nightly green while build_site keeps
# re-rendering this page from the last good file — the counts would freeze and
# stay published forever. The stamp bounds that: a projection nobody has
# refreshed in a month stops being printed instead of quietly going stale.
PUBLIC_SUMMARY_MAX_AGE_DAYS = 30
QUARTERLY_METRICS = (
    "revenue",
    "gross_profit",
    "receivables",
    "inventory",
    "cfo",
    "capex",
    "op_income",
    "ni",
    "contract_liabilities",
)

DETECTORS = (
    {
        "id": "margin_compression_despite_revenue_growth",
        "topic": "margin",
        "title_en": "Margin compression",
        "title_zh": "利润率承压",
        "description_en": "Revenue grew while gross margin moved lower year over year.",
        "description_zh": "收入同比增长，但毛利率下降。",
        "threshold_en": "Revenue growth ≥ 3%; current gross margin < prior-year quarter",
        "threshold_zh": "收入增长 ≥ 3%；本季毛利率低于去年同期",
    },
    {
        "id": "receivables_stretch",
        "topic": "working_capital",
        "title_en": "Receivables outran revenue",
        "title_zh": "应收账款跑赢收入",
        "description_en": "Receivables grew materially faster than reported revenue.",
        "description_zh": "应收账款增长明显快于报告收入。",
        "threshold_en": "Receivables growth > revenue growth + 10 percentage points",
        "threshold_zh": "应收账款增速 > 收入增速 + 10 个百分点",
    },
    {
        "id": "inventory_build",
        "topic": "working_capital",
        "title_en": "Inventory outran revenue",
        "title_zh": "库存跑赢收入",
        "description_en": "Inventory accumulated materially faster than reported revenue.",
        "description_zh": "库存累积明显快于报告收入。",
        "threshold_en": "Inventory growth > revenue growth + 15 percentage points",
        "threshold_zh": "库存增速 > 收入增速 + 15 个百分点",
    },
    {
        "id": "capital_intensity_rising",
        "topic": "capital_intensity",
        "title_en": "Capital intensity rose",
        "title_zh": "资本强度上升",
        "description_en": "Capital spending grew faster than revenue and operating income.",
        "description_zh": "资本开支增速快于收入及经营利润。",
        "threshold_en": "Capex growth > revenue and operating-income growth by 10 percentage points",
        "threshold_zh": "资本开支增速比收入及经营利润增速高 10 个百分点",
    },
    {
        "id": "accruals_trending_up",
        "topic": "cash_conversion",
        "title_en": "Accrual burden rose",
        "title_zh": "应计负担上升",
        "description_en": "Three-year accrual intensity moved materially higher.",
        "description_zh": "三年应计强度明显上升。",
        "threshold_en": "Latest minus oldest (net income − CFO) / assets ≥ 3 percentage points",
        "threshold_zh": "最新与最早的（净利润 − 经营现金流）/ 资产差值 ≥ 3 个百分点",
    },
)

# The state transport remains intentionally compact even when the raw archive
# cache grows.  The disclosure projection module bounds each company record;
# this second guard prevents a one-off bulk import from crowding out the
# existing broad-universe workbench state.  Omitted records remain available in
# the private projection directory and are reported explicitly in coverage.
# Real two-track Inline XBRL comparisons can legitimately reach ~550 KiB even
# after the redline/receipt caps are applied (AAPL's annual + quarterly pair is
# a measured example). Keep a firm per-company ceiling, but do not silently
# discard the very evidence-heavy issuers this feature exists to investigate.
MAX_DISCLOSURE_PROJECTION_BYTES = 768 * 1024
MAX_DISCLOSURE_STATE_BYTES = 12 * 1024 * 1024


def _finite(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _ratio(num: Any, den: Any) -> float | None:
    n, d = _finite(num), _finite(den)
    if n is None or d is None or d <= 0:
        return None
    return n / d


def _growth(current: Any, prior: Any) -> float | None:
    c, p = _finite(current), _finite(prior)
    if c is None or p is None or p <= 0:
        return None
    return c / p - 1.0


def _json_number(value: Any) -> float | None:
    val = _finite(value)
    return round(val, 8) if val is not None else None


def _period_label(row: pd.Series) -> str:
    fy = int(row["fiscal_year"])
    fq = row.get("fiscal_quarter")
    # Annual period stamps carry a fiscal year and no quarter: the accruals
    # finding measures ANNUAL rows, so its label must not borrow a quarter.
    if fq is None or pd.isna(fq):
        return f"FY{fy}"
    return f"FY{fy} Q{int(fq)}"


def _source_links(cik: int | None, filed: str | None) -> list[dict[str, Any]]:
    if cik is None:
        return []
    cik10 = f"{int(cik):010d}"
    return [
        {
            "label_en": "SEC filing history",
            "label_zh": "SEC 披露历史",
            "date": filed,
            "url": f"https://www.sec.gov/edgar/browse/?CIK={int(cik)}&owner=exclude&action=getcompany",
            "basis": "filing_index",
        },
        {
            "label_en": "SEC Company Facts JSON",
            "label_zh": "SEC 公司事实 JSON",
            "date": filed,
            "url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json",
            "basis": "companyfacts_source",
        },
    ]


def _value(
    key: str,
    label_en: str,
    label_zh: str,
    current: Any,
    prior: Any,
    delta: Any,
    fmt: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "label_en": label_en,
        "label_zh": label_zh,
        "current": _json_number(current),
        "prior": _json_number(prior),
        "delta": _json_number(delta),
        "format": fmt,
    }


def _finding(
    detector: str,
    priority: str,
    current: pd.Series,
    prior: pd.Series,
    *,
    title_en: str,
    title_zh: str,
    summary_en: str,
    summary_zh: str,
    formula_en: str,
    formula_zh: str,
    threshold_en: str,
    threshold_zh: str,
    values: list[dict[str, Any]],
    cik: int | None,
    limitations_en: Iterable[str] = (),
    limitations_zh: Iterable[str] = (),
) -> dict[str, Any]:
    current_label = _period_label(current)
    prior_label = _period_label(prior)
    return {
        "id": f"{detector}:{current_label.replace(' ', '-').lower()}",
        "detector": detector,
        "priority": priority,
        "topic": next(d["topic"] for d in DETECTORS if d["id"] == detector),
        "title_en": title_en,
        "title_zh": title_zh,
        "summary_en": summary_en,
        "summary_zh": summary_zh,
        "period_current": current_label,
        "period_prior": prior_label,
        "formula_en": formula_en,
        "formula_zh": formula_zh,
        "threshold_en": threshold_en,
        "threshold_zh": threshold_zh,
        "values": values,
        "evidence": _source_links(cik, str(current.get("filed") or "")),
        "limitations_en": list(limitations_en),
        "limitations_zh": list(limitations_zh),
        # FIF P1-b (I4): the state panel is not accession-coherent and carries
        # no occurrence ledger, so occurrence provenance is an explicit JSON
        # null with a basis string — never a fabricated id, span, or "null"
        # text. Hydrating real ids is a future ledger-join lane.
        "occurrence_id": None,
        "source_span": None,
        "occurrence_basis": "panel_projection_not_occurrence_bound",
        "display_only": True,
        "authority": "review_priority_only",
    }


def detect_quarterly(current: pd.Series, prior: pd.Series, cik: int | None) -> list[dict[str, Any]]:
    """Return transparent triggered checks for matched fiscal quarters."""
    out: list[dict[str, Any]] = []
    rev_g = _growth(current.get("revenue"), prior.get("revenue"))
    gm_cur = _ratio(current.get("gross_profit"), current.get("revenue"))
    gm_prev = _ratio(prior.get("gross_profit"), prior.get("revenue"))
    # A computable revenue GROWTH is not the same as a usable revenue BASE.
    # _growth only requires the PRIOR denominator to be positive, so a filer
    # whose revenue collapses to 0 (or is reported negative) still yields
    # rev_g = -1.0 or lower. The working-capital spreads below then degenerate:
    # `ar_g > rev_g + 0.10` becomes `ar_g > -0.90`, which almost any receivables
    # series clears — a near-certain FALSE FIRE driven entirely by the revenue
    # collapse rather than by any receivables behaviour. Both sibling
    # implementations already refuse here (engine/moat_falsifiers.py returns
    # None; engine/fundamental_forensics/detectors.py returns NOT_EVALUABLE with
    # "positive_revenue_and_nonzero_prior_balance_required"), so this gate makes
    # the workbench agree with them instead of publishing the artefact.
    # The margin check needs no such gate: _ratio already requires d > 0.
    rev_cur = _finite(current.get("revenue"))
    rev_cur_positive = rev_cur is not None and rev_cur > 0

    if rev_g is not None and rev_g >= 0.03 and gm_cur is not None and gm_prev is not None and gm_cur < gm_prev:
        compression = gm_prev - gm_cur
        priority = "high" if compression >= 0.03 else "watch"
        out.append(_finding(
            "margin_compression_despite_revenue_growth", priority, current, prior,
            title_en="Revenue grew. Gross margin did not.",
            title_zh="收入增长，毛利率却下降。",
            summary_en=f"Revenue rose {rev_g:.1%} year over year while gross margin fell {compression*100:.1f} percentage points.",
            summary_zh=f"收入同比增长 {rev_g:.1%}，毛利率下降 {compression*100:.1f} 个百分点。",
            formula_en="Gross margin = gross profit / revenue; compare the same fiscal quarter year over year.",
            formula_zh="毛利率 = 毛利润 / 收入；对比去年同期季度。",
            threshold_en="Revenue growth ≥ 3% and current gross margin < prior-year quarter.",
            threshold_zh="收入增长 ≥ 3%，且本季毛利率低于去年同期。",
            values=[
                _value("revenue_growth", "Revenue growth", "收入增长", rev_g, None, None, "percent"),
                _value("gross_margin", "Gross margin", "毛利率", gm_cur, gm_prev, gm_cur - gm_prev, "percent"),
            ], cik=cik,
            limitations_en=("A lower margin can reflect mix, acquisitions, pass-through costs, or deliberate investment.",),
            limitations_zh=("毛利率下降也可能源于产品组合、并购、成本转嫁或主动投资。",),
        ))

    ar_g = _growth(current.get("receivables"), prior.get("receivables"))
    if rev_g is not None and rev_cur_positive and ar_g is not None and ar_g > rev_g + 0.10:
        gap = ar_g - rev_g
        out.append(_finding(
            "receivables_stretch", "high" if gap >= 0.25 else "watch", current, prior,
            title_en="Receivables are outrunning sales.",
            title_zh="应收账款跑赢销售。",
            summary_en=f"Receivables grew {gap*100:.1f} percentage points faster than revenue year over year.",
            summary_zh=f"应收账款增速比收入快 {gap*100:.1f} 个百分点。",
            formula_en="Receivables growth minus revenue growth.",
            formula_zh="应收账款增速减去收入增速。",
            threshold_en="Spread > 10 percentage points.",
            threshold_zh="差值 > 10 个百分点。",
            values=[
                _value("receivables_growth", "Receivables growth", "应收账款增长", ar_g, None, None, "percent"),
                _value("revenue_growth", "Revenue growth", "收入增长", rev_g, None, None, "percent"),
                _value("growth_gap", "Growth gap", "增速差", gap, None, None, "percent"),
            ], cik=cik,
            limitations_en=("Seasonality, billing cadence, acquisitions, and customer mix can create a benign gap.",),
            limitations_zh=("季节性、开票节奏、并购及客户结构可能造成良性差异。",),
        ))

    inv_g = _growth(current.get("inventory"), prior.get("inventory"))
    if rev_g is not None and rev_cur_positive and inv_g is not None and inv_g > rev_g + 0.15:
        gap = inv_g - rev_g
        out.append(_finding(
            "inventory_build", "high" if gap >= 0.30 else "watch", current, prior,
            title_en="Inventory is building faster than sales.",
            title_zh="库存增长快于销售。",
            summary_en=f"Inventory grew {gap*100:.1f} percentage points faster than revenue year over year.",
            summary_zh=f"库存增速比收入快 {gap*100:.1f} 个百分点。",
            formula_en="Inventory growth minus revenue growth.",
            formula_zh="库存增速减去收入增速。",
            threshold_en="Spread > 15 percentage points.",
            threshold_zh="差值 > 15 个百分点。",
            values=[
                _value("inventory_growth", "Inventory growth", "库存增长", inv_g, None, None, "percent"),
                _value("revenue_growth", "Revenue growth", "收入增长", rev_g, None, None, "percent"),
                _value("growth_gap", "Growth gap", "增速差", gap, None, None, "percent"),
            ], cik=cik,
            limitations_en=("A planned product ramp, supply protection, acquisitions, or commodity inflation can explain the build.",),
            limitations_zh=("产品爬坡、供应保障、并购或大宗商品通胀可能解释库存增加。",),
        ))

    capex_g = _growth(current.get("capex"), prior.get("capex"))
    op_g = _growth(current.get("op_income"), prior.get("op_income"))
    op_cur = _finite(current.get("op_income"))
    # Current capex must be POSITIVE — the detector is about rising capital
    # SPENDING, and a non-positive current capex is net disposal proceeds (or a
    # quarter with none reported), which is the opposite direction. _growth only
    # constrains the PRIOR, so without this gate a zero/negative current capex
    # yields a well-formed capex_g <= -1.0 that can never clear rev_g + 0.10 —
    # so the pair reports "clear" forever AND is counted as covered, a permanent
    # verdict drawn from evidence that cannot support one. Both siblings already
    # refuse here (engine/moat_falsifiers.py skips on current capex <= 0; the
    # registry kernel returns not_evaluable with
    # "nonzero_revenue_and_positive_capex_required").
    capex_cur = _finite(current.get("capex"))
    capex_cur_positive = capex_cur is not None and capex_cur > 0
    capex_triggered = False
    capex_gap = None
    if capex_g is not None and rev_g is not None and capex_cur_positive and capex_g > rev_g + 0.10:
        if op_cur is not None and op_cur <= 0:
            capex_triggered, capex_gap = True, capex_g - rev_g
        elif op_g is not None and capex_g > op_g + 0.10:
            capex_triggered, capex_gap = True, min(capex_g - rev_g, capex_g - op_g)
    if capex_triggered and capex_gap is not None:
        out.append(_finding(
            "capital_intensity_rising", "high" if capex_gap >= 0.25 else "watch", current, prior,
            title_en="Capital spending accelerated ahead of output.",
            title_zh="资本开支增速领先产出。",
            summary_en=f"Capex growth exceeded operating growth by at least {capex_gap*100:.1f} percentage points.",
            summary_zh=f"资本开支增速至少比经营增长快 {capex_gap*100:.1f} 个百分点。",
            formula_en="Capex growth compared with revenue and operating-income growth.",
            formula_zh="比较资本开支、收入及经营利润增速。",
            threshold_en="Capex growth exceeds both comparators by > 10 percentage points; revenue-only when operating income is non-positive.",
            threshold_zh="资本开支增速比两项指标均高 > 10 个百分点；经营利润非正时仅比较收入。",
            values=[
                _value("capex_growth", "Capex growth", "资本开支增长", capex_g, None, None, "percent"),
                _value("revenue_growth", "Revenue growth", "收入增长", rev_g, None, None, "percent"),
                _value("operating_income_growth", "Operating income growth", "经营利润增长", op_g, None, None, "percent"),
            ], cik=cik,
            limitations_en=("Growth investment can be economically attractive; this check identifies a review question, not a negative verdict.",),
            limitations_zh=("增长性投资可能具有经济价值；本检查仅提出复核问题，不构成负面结论。",),
        ))
    return out


def _accrual_rows(annual: pd.DataFrame) -> pd.DataFrame:
    """The exact three-year row window the accruals detector measures.

    Shared by ``_accrual_inputs`` (the values) and ``detect_accruals`` (the
    period stamps), so a finding can never cite a row it did not measure.
    """
    return annual.sort_values(["fy", "period_end"], na_position="first").tail(3)


def _annual_period_row(row: pd.Series, has_filed: bool) -> pd.Series:
    """An annual period stamp: fiscal year only, never a borrowed quarter."""
    data: dict[str, Any] = {"fiscal_year": int(row["fy"])}
    if has_filed:
        filed = row.get("filed")
        data["filed"] = "" if filed is None or pd.isna(filed) else str(filed)
    return pd.Series(data)


def _accrual_inputs(annual: pd.DataFrame) -> tuple[list[int], list[float]] | None:
    """Return the exact three-year detector inputs, or None when not evaluable."""
    if annual.empty:
        return None
    rows = _accrual_rows(annual)
    if len(rows) != 3:
        return None
    fys = [int(v) for v in rows["fy"]]
    if fys[1] - fys[0] != 1 or fys[2] - fys[1] != 1:
        return None
    vals: list[float] = []
    for _, row in rows.iterrows():
        ni, cfo, assets = (_finite(row.get(k)) for k in ("ni", "cfo", "assets"))
        if ni is None or cfo is None or assets is None or assets <= 0:
            return None
        vals.append((ni - cfo) / assets)
    return fys, vals


def detector_evaluability(
    current: pd.Series,
    prior: pd.Series,
    annual: pd.DataFrame,
) -> dict[str, bool]:
    """Apply the same denominator/period gates as each detector.

    A finite value is not automatically an evaluable input: growth requires a
    positive prior denominator, capital intensity changes branch when operating
    income is non-positive, and accruals require three consecutive fiscal years.
    Keeping this map beside the detector math prevents false "covered" labels.
    """
    rev_g = _growth(current.get("revenue"), prior.get("revenue"))
    gm_cur = _ratio(current.get("gross_profit"), current.get("revenue"))
    gm_prev = _ratio(prior.get("gross_profit"), prior.get("revenue"))
    ar_g = _growth(current.get("receivables"), prior.get("receivables"))
    inv_g = _growth(current.get("inventory"), prior.get("inventory"))
    capex_g = _growth(current.get("capex"), prior.get("capex"))
    op_cur = _finite(current.get("op_income"))
    op_g = _growth(current.get("op_income"), prior.get("op_income"))
    # Mirrors the gate added to detect_quarterly: a non-positive CURRENT revenue
    # makes the working-capital spread an artefact of the revenue collapse, so
    # the pair is not evaluable rather than "covered but clear".
    rev_cur = _finite(current.get("revenue"))
    rev_cur_positive = rev_cur is not None and rev_cur > 0
    # Mirrors detect_quarterly: a non-positive CURRENT capex is disposal
    # proceeds, not capital spending, so the pair is not evaluable rather than
    # "covered and clear".
    capex_cur = _finite(current.get("capex"))
    capex_cur_positive = capex_cur is not None and capex_cur > 0
    capex_evaluable = (
        capex_g is not None
        and rev_g is not None
        and capex_cur_positive
        and op_cur is not None
        and (op_cur <= 0 or op_g is not None)
    )
    return {
        "margin_compression_despite_revenue_growth": rev_g is not None and gm_cur is not None and gm_prev is not None,
        "receivables_stretch": rev_g is not None and ar_g is not None and rev_cur_positive,
        "inventory_build": rev_g is not None and inv_g is not None and rev_cur_positive,
        "capital_intensity_rising": capex_evaluable,
        "accruals_trending_up": _accrual_inputs(annual) is not None,
    }


def detect_accruals(annual: pd.DataFrame, current_q: pd.Series, prior_q: pd.Series, cik: int | None) -> dict[str, Any] | None:
    """Three-period annual accrual trend using the repository's locked 3pp rule.

    ``current_q``/``prior_q`` are retained for call-site stability only: the
    finding is measured on ANNUAL rows, so its period stamps and evidence date
    come from the annual frame's latest and base fiscal years — never from the
    quarterly rows the surrounding build happens to be standing on.
    """
    inputs = _accrual_inputs(annual)
    if inputs is None:
        return None
    fys, vals = inputs
    delta = vals[-1] - vals[0]
    if delta < 0.03 or vals[-1] <= vals[0]:
        return None
    rows = _accrual_rows(annual)
    has_filed = "filed" in annual.columns
    latest_fy = _annual_period_row(rows.iloc[-1], has_filed)
    base_fy = _annual_period_row(rows.iloc[0], has_filed)
    return _finding(
        "accruals_trending_up", "high" if delta >= 0.05 else "watch", latest_fy, base_fy,
        title_en="Earnings moved further ahead of cash.",
        title_zh="利润进一步领先现金流。",
        summary_en=f"Accrual intensity rose {delta*100:.1f} percentage points across FY{fys[0]}–FY{fys[-1]}.",
        summary_zh=f"FY{fys[0]}–FY{fys[-1]} 应计强度上升 {delta*100:.1f} 个百分点。",
        formula_en="Accrual intensity = (net income − operating cash flow) / assets.",
        formula_zh="应计强度 =（净利润 − 经营现金流）/ 资产。",
        threshold_en="Latest minus oldest ≥ 3 percentage points across three consecutive fiscal years.",
        threshold_zh="连续三个财年中，最新值减最早值 ≥ 3 个百分点。",
        values=[
            _value("accrual_oldest", f"FY{fys[0]} accrual intensity", f"FY{fys[0]} 应计强度", vals[0], None, None, "percent"),
            _value("accrual_middle", f"FY{fys[1]} accrual intensity", f"FY{fys[1]} 应计强度", vals[1], None, None, "percent"),
            _value("accrual_latest", f"FY{fys[2]} accrual intensity", f"FY{fys[2]} 应计强度", vals[2], vals[0], delta, "percent"),
        ], cik=cik,
        limitations_en=("Working-capital timing and business-model differences can move accrual ratios without implying misstatement.",),
        limitations_zh=("营运资金时点及商业模式差异可能影响应计比率，并不意味着错报。",),
    )


def _metadata(root: Path) -> tuple[dict[str, str], dict[str, str], dict[str, int]]:
    names: dict[str, str] = {}
    sectors: dict[str, str] = {}
    membership = root / "data" / "universe" / "membership.parquet"
    if membership.exists():
        m = pd.read_parquet(membership)
        if "active" in m.columns:
            m = m[m["active"].fillna(False)]
        for row in m.drop_duplicates("ticker", keep="last").to_dict("records"):
            ticker = str(row.get("ticker") or "").upper()
            if ticker:
                names[ticker] = str(row.get("name") or ticker)
                sectors[ticker] = str(row.get("sector") or "Unclassified")
    sector_path = root / "data" / "breadth" / "ticker_sectors.parquet"
    if sector_path.exists():
        for row in pd.read_parquet(sector_path).to_dict("records"):
            ticker = str(row.get("ticker") or "").upper()
            if ticker and row.get("sector"):
                sectors[ticker] = str(row["sector"])
    ciks: dict[str, int] = {}
    fundamentals = root / "data" / "edgar" / "fundamentals.parquet"
    if fundamentals.exists():
        f = pd.read_parquet(fundamentals, columns=["cik"])
        for ticker, row in f.iterrows():
            cik = _finite(row.get("cik"))
            if cik is not None:
                ciks[str(ticker).upper()] = int(cik)
    return names, sectors, ciks


def _cik10(value: Any) -> str | None:
    """Normalize a CIK of any common shape onto the zero-padded 10-text form."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>", "nat"}:
        return None
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    if not text.isdigit():
        return None
    return text.zfill(10)


@dataclass(frozen=True)
class IssuerMasterIndex:
    """One read of the committed issuer master, joined by exact CIK only.

    This is a JOIN, never a mint: an issuer id reaches the state only from a
    committed authority row whose CIK carries exactly one issuer id. Missing,
    unreadable, absent, and ambiguous all stay null with a machine-readable
    reason; nothing is ever derived from a ticker or listing guess.
    """

    available: bool
    bound: Mapping[str, str]
    ambiguous: frozenset[str]

    def join(self, cik10: str | None) -> tuple[str | None, str]:
        if cik10 is None:
            return None, "cik_absent_in_panel"
        if not self.available:
            return None, "issuer_master_unavailable"
        if cik10 in self.ambiguous:
            return None, "issuer_master_ambiguous_for_cik"
        issuer_id = self.bound.get(cik10)
        if issuer_id is None:
            return None, "issuer_master_row_absent_for_cik"
        return issuer_id, "issuer_master_row"


def _issuer_master_index(root: Path) -> IssuerMasterIndex:
    """Read the committed issuer master once per build, fail-soft.

    A missing or unreadable file is a normal state (fresh clone, partial
    checkout) that mirrors ``_metadata``'s fail-soft shape: every company then
    reports ``issuer_master_unavailable`` instead of an error.
    """
    path = root / ISSUER_MASTER_RELATIVE
    if not path.exists():
        return IssuerMasterIndex(available=False, bound={}, ambiguous=frozenset())
    try:
        frame = pd.read_parquet(path, columns=["issuer_id", "cik"]).dropna(
            subset=["issuer_id", "cik"]
        )
    except Exception:  # noqa: BLE001 - unreadable authority is a normal state here
        return IssuerMasterIndex(available=False, bound={}, ambiguous=frozenset())
    grouped: dict[str, set[str]] = {}
    for raw_cik, raw_issuer in zip(frame["cik"], frame["issuer_id"]):
        cik10 = _cik10(raw_cik)
        issuer_id = str(raw_issuer).strip()
        if cik10 is None or not issuer_id:
            continue
        grouped.setdefault(cik10, set()).add(issuer_id)
    bound = {cik: ids.pop() for cik, ids in grouped.items() if len(ids) == 1}
    ambiguous = frozenset(cik for cik, ids in grouped.items() if len(ids) > 1)
    return IssuerMasterIndex(available=True, bound=bound, ambiguous=ambiguous)


def _clean_period(row: pd.Series) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "fiscal_year": int(row["fiscal_year"]),
        "fiscal_quarter": int(row["fiscal_quarter"]),
        "period_end": str(row.get("period_end") or ""),
        "filed": str(row.get("filed") or ""),
    }
    # FIF P1-b (I2): the canonical query-period projection, carried alongside
    # the existing fiscal fields. State rows are fiscal-quarter DURATION
    # buckets; `start` is the companyfacts duration start retained by the
    # backfill (rows from a pre-I2 panel carry none) or an explicit null with
    # its basis — never a derived date and never an empty placeholder.
    start_raw = row.get("period_start")
    start = start_raw if isinstance(start_raw, str) and start_raw else None
    doc["kind"] = "duration"
    doc["start"] = start
    doc["end"] = doc["period_end"]
    doc["label"] = _period_label(row)
    doc["period_start_basis"] = (
        "companyfacts_duration_start" if start is not None else "absent_in_projection"
    )
    for metric in QUARTERLY_METRICS:
        doc[metric] = _json_number(row.get(metric))
    return doc


def _source_generated_at(quarterly: pd.DataFrame, annual: pd.DataFrame, as_of: str | None) -> str:
    """Return a stable source-snapshot clock instead of a wall-clock build time."""
    candidates: list[pd.Timestamp] = []
    for frame in (quarterly, annual):
        if frame.empty or "as_of" not in frame.columns:
            continue
        parsed = pd.to_datetime(frame["as_of"], errors="coerce", utc=True).dropna()
        if not parsed.empty:
            candidates.append(parsed.max())
    if candidates:
        return max(candidates).floor("s").isoformat()
    if as_of:
        return f"{as_of}T23:59:59+00:00"
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _state_disclosure_projection(projection: dict[str, Any]) -> dict[str, Any]:
    """Return the browser-safe private slice of one verified projection.

    The on-disk projection is already bounded and source-receipt rich.  Keep
    the explicit source/clock fields in state, but drop the duplicate issuer
    identity because it is carried by the company object that owns this slice.
    """
    return {
        "schema": projection["schema"],
        "projection_id": projection["projection_id"],
        "clocks": dict(projection["clocks"]),
        "source": dict(projection["source"]),
        "coverage": dict(projection["coverage"]),
        "tracks": list(projection["tracks"]),
        "limitations": list(projection["limitations"]),
        "display_only": True,
        "authority": "review_priority_only",
    }


def _load_disclosure_projections(root: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Load optional, prebuilt accession-level comparisons without blocking v1.

    Heavy SEC retrieval/comparison is deliberately elsewhere.  A bad optional
    private projection is ignored fail-soft here; it cannot turn a successful
    base workbench build into an invented disclosure result.
    """
    try:
        return read_disclosure_projection_directory(root), []
    except DisclosureProjectionError as exc:
        log.warning("ignored invalid disclosure projection directory: %s", exc)
        return {}, [type(exc).__name__]


def _disclosure_budgeted(
    projections: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    """Select canonical projection records that fit the compact state budget."""
    selected: dict[str, dict[str, Any]] = {}
    total = 0
    too_large = 0
    deferred = 0
    for ticker, projection in sorted(projections.items()):
        encoded = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(encoded) > MAX_DISCLOSURE_PROJECTION_BYTES:
            too_large += 1
            continue
        if total + len(encoded) > MAX_DISCLOSURE_STATE_BYTES:
            deferred += 1
            continue
        selected[ticker] = projection
        total += len(encoded)
    return selected, {
        "loaded": len(projections),
        "selected": len(selected),
        "too_large": too_large,
        "deferred_for_state_budget": deferred,
        "embedded_bytes": total,
    }


# ---------------------------------------------------------------------------
# FIF P1-b (I5, waves 1+2): the peer-cohort payload projection.
#
# Members come ONLY from the pinned coverage contract (read at runtime); their
# issuer ids come ONLY from the exact-CIK issuer-master join above; their
# observations come ONLY from the P1 precomputed statement trees in the
# production dataset store. Every absence is typed in ``member_exclusions``
# with the closed code set below — never a silent drop, never a fallback to a
# golden provider or fixture, and never a float: values cross this boundary as
# ``Decimal`` of the parser's canonical cell text.
# ---------------------------------------------------------------------------

_PEER_EXCLUSION_SIC = "issuer_sic_unavailable"
_PEER_EXCLUSION_DATASET = "production_dataset_absent"
_PEER_EXCLUSION_IDENTITY = "issuer_identity_unresolved"


def _read_coverage_contract(root: Path) -> dict[str, Any] | None:
    """Read the pinned coverage contract, fail-soft to None."""
    try:
        raw = json.loads((root / COVERAGE_CONTRACT_RELATIVE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def _pinned_sic(raw: Any) -> str | None:
    """Return the contract's pinned SIC when it is a parseable code, else None.

    Absent, empty, and unparseable values are indistinguishable for gating
    purposes: the member is excluded BEFORE any class derivation, so a missing
    SIC can never leak into a fail-open applicability call.
    """
    if raw is None or isinstance(raw, bool):
        return None
    text = str(raw).strip()
    if not text or not text.isdigit():
        return None
    return text


def _contract_members(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Project the contract's issuer rows, in contract order."""
    members: list[dict[str, Any]] = []
    for issuer in contract.get("issuers") or []:
        if not isinstance(issuer, dict):
            continue
        ticker = str(issuer.get("ticker") or "").upper()
        cik10 = _cik10(issuer.get("cik"))
        if not ticker or cik10 is None:
            continue
        accession_periods: dict[str, str] = {}
        accessions: list[str] = []
        for row in issuer.get("accessions") or []:
            if not isinstance(row, dict):
                continue
            accession = row.get("accession")
            if not isinstance(accession, str):
                continue
            accessions.append(accession)
            period = row.get("period_of_report")
            if isinstance(period, str):
                try:
                    date.fromisoformat(period)
                except ValueError:
                    continue
                accession_periods[accession] = period
        members.append({
            "ticker": ticker,
            "cik10": cik10,
            "sic": issuer.get("sic"),
            "accessions": accessions,
            "accession_periods": accession_periods,
        })
    return members


def _contract_metric_ids(contract: Mapping[str, Any]) -> tuple[str, ...]:
    denominator = contract.get("field_denominator")
    if not isinstance(denominator, dict):
        return ()
    raw = denominator.get("metric_ids")
    if not isinstance(raw, list):
        return ()
    return tuple(item for item in raw if isinstance(item, str) and item)


def _class_not_applicable_metric_ids(root: Path) -> dict[str, frozenset[str]]:
    """Per-issuer-class metric exclusions derived from the shipped catalog.

    G0-b retired the ticker-keyed ``field_denominator.not_applicable`` overlay:
    the build path derives its exclusions from the same S1-b class policies the
    query path qualifies through ``qualify_metric`` (formula=None, the direct
    stage's exact call), so a per-ticker answer can no longer diverge from the
    class answer. Keyed by issuer class — never by ticker, CIK, or issuer name
    — and resolved per member through ``issuer_class_for_sic`` at the call
    site.
    """
    registry = load_core_metric_registry(root)
    out: dict[str, frozenset[str]] = {}
    for issuer_class in sorted(ISSUER_CLASSES):
        excluded = frozenset(
            contract.metric_id
            for contract in registry.contracts
            if qualify_metric(contract, None, issuer_class, {}).state != "applicable"
        )
        if excluded:
            out[issuer_class] = excluded
    return out


def _cohort_policy_defaults() -> dict[str, Any]:
    """The C1 CohortDefinition defaults, imported — never duplicated literals."""
    probe = CohortDefinition(cohort_id="", anchor_issuer_id="", members=(), metric_ids=())
    return {
        "alignment_mode": probe.alignment_mode,
        "period_tolerance_days": probe.period_tolerance_days,
        "min_n": probe.min_n,
    }


def _generation_metric_versions(
    generation: Any,
    metric_ids: tuple[str, ...],
    cache: dict[str, dict[str, str]] | None = None,
) -> dict[str, str]:
    """The rule version of each metric in the member generation's pinned registry.

    A generation whose registry role is absent, undecodable or cannot be
    rebuilt yields no versions: its observations then carry
    ``metric_version=None``, which the cohort's A35-V1 check excludes against
    any versioned anchor. ``cache`` is keyed by the role payload digest, so
    members published under one registry snapshot rebuild it once.
    """
    payloads = getattr(generation, "role_payloads", None)
    raw = payloads.get("registry_json") if isinstance(payloads, Mapping) else None
    if not isinstance(raw, (bytes, bytearray)):
        return {}
    digest = hashlib.sha256(bytes(raw)).hexdigest()
    if cache is not None and digest in cache:
        return cache[digest]
    versions: dict[str, str] = {}
    try:
        registry = registry_from_payload(json.loads(bytes(raw).decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError, ProductionDatasetError):
        registry = None
    if registry is not None:
        for metric_id in metric_ids:
            try:
                version = registry.metric(metric_id).version
            except KeyError:
                continue
            if isinstance(version, str) and version:
                versions[metric_id] = version
    if cache is not None:
        cache[digest] = versions
    return versions


def _tree_metric_observations(
    generation: Any,
    accessions: list[str],
    metric_ids: tuple[str, ...],
    excluded_metrics: frozenset[str],
    accession_periods: Mapping[str, str],
    same_end: dict[str, tuple[MetricObservation, ...]] | None = None,
    metric_versions: Mapping[str, str] | None = None,
) -> dict[str, MetricObservation] | None:
    """Project the latest available cell per metric from the precomputed trees.

    Returns ``None`` when no contract accession's tree is readable — the typed
    dataset-absent case. A cell whose value is not canonical text contributes
    nothing (the cohort table then reports that member×metric as a missing
    observation); no value is converted, scaled, rounded, or floated here.
    A cell without a stated period kind or unit contributes nothing either:
    the cohort's A35-K1/U1 controls compare against the anchor's basis and
    unit, so an observation with neither known is not comparable (A35).
    ``metric_versions`` (``_generation_metric_versions``) stamps each
    observation with the member registry's rule version for A35-V1.
    ``excluded_metrics`` is the member's class-derived not-applicable closure
    (G0-b), intersected with the field denominator by the caller.

    Cells sharing the latest end date (a 10-Q's quarter beside its
    year-to-date column) resolve to the shortest stated duration, so among
    distinct durations the pick never depends on cell order; cells of equal
    duration keep the first one met in contract accession order, and a dated
    cell always outranks an undated one. When ``same_end`` is given, every metric
    whose latest end date carried more than one cell gets all of them there,
    for the caller to align against an anchor (``_aligned_to_anchor``).
    """
    wanted = set(metric_ids)
    latest: dict[str, MetricObservation] = {}
    latest_end: dict[str, date] = {}
    candidates: dict[str, list[MetricObservation]] = {}
    metric_statement_types: dict[str, set[str]] = {}
    refused: set[tuple[str, str]] = set()
    readable = False
    for accession in accessions:
        try:
            tree = generation.statement_trees(accession)
        except ProductionDatasetError:
            continue
        readable = True
        for statement in tree.get("statements") or []:
            if not isinstance(statement, dict):
                continue
            statement_type = statement.get("statement_type")
            if statement.get("refusal") and isinstance(statement_type, str):
                refused.add((accession, statement_type))
            for tree_row in statement.get("rows") or []:
                metric_id = tree_row.get("standardized_metric_id")
                if not isinstance(metric_id, str) or metric_id not in wanted:
                    continue
                if isinstance(statement_type, str):
                    metric_statement_types.setdefault(metric_id, set()).add(statement_type)
                for cell in tree_row.get("cells") or []:
                    value_text = cell.get("value")
                    if not isinstance(value_text, str):
                        continue
                    period = cell.get("period") or {}
                    end = period.get("end")
                    if not isinstance(end, str):
                        continue
                    start = period.get("start")
                    start_date: date | None = None
                    if isinstance(start, str):
                        try:
                            start_date = date.fromisoformat(start)
                        except ValueError:
                            continue
                    try:
                        end_date = date.fromisoformat(end)
                        value = Decimal(value_text)
                    except (ValueError, InvalidOperation):
                        continue
                    period_kind = period.get("kind")
                    cell_unit = cell.get("unit")
                    if not (isinstance(period_kind, str) and period_kind):
                        continue
                    if not (isinstance(cell_unit, str) and cell_unit):
                        continue
                    incumbent_end = latest_end.get(metric_id)
                    if incumbent_end is not None and end_date < incumbent_end:
                        continue
                    observation = MetricObservation(
                        value=value,
                        period_end=end_date,
                        period_basis=period_kind,
                        applicable=metric_id not in excluded_metrics,
                        period_start=start_date,
                        unit=cell_unit,
                        metric_version=(metric_versions or {}).get(metric_id),
                    )
                    if incumbent_end is None or end_date > incumbent_end:
                        latest_end[metric_id] = end_date
                        latest[metric_id] = observation
                        candidates[metric_id] = [observation]
                        continue
                    candidates[metric_id].append(observation)
                    days = _duration_days(observation)
                    incumbent_days = _duration_days(latest[metric_id])
                    if days is not None and (incumbent_days is None or days < incumbent_days):
                        latest[metric_id] = observation
    for metric_id, observation in list(latest.items()):
        statement_types = metric_statement_types.get(metric_id, set())
        if not statement_types:
            continue
        rm_dates: list[date] = []
        for refused_accession, refused_type in refused:
            if refused_type not in statement_types:
                continue
            period_text = accession_periods.get(refused_accession)
            if not isinstance(period_text, str):
                continue
            try:
                rm_dates.append(date.fromisoformat(period_text))
            except ValueError:
                continue
        if not rm_dates:
            continue
        rm = max(rm_dates)
        if observation.period_end is not None and observation.period_end < rm:
            latest[metric_id] = MetricObservation(
                value=None,
                period_end=rm,
                period_basis=observation.period_basis,
                applicable=observation.applicable,
                withheld=True,
            )
    if same_end is not None:
        for metric_id, observation in latest.items():
            pool = candidates.get(metric_id, [])
            if len(pool) > 1 and not observation.withheld:
                same_end[metric_id] = tuple(pool)
    return latest if readable else None


def _duration_days(observation: MetricObservation) -> int | None:
    if observation.period_start is None or observation.period_end is None:
        return None
    return (observation.period_end - observation.period_start).days


@dataclass(frozen=True)
class _AdmittedPeer:
    member: Mapping[str, Any]
    issuer_id: str
    # A14: the owner binding's identity — cik in canonical cik10 form and the
    # binding's listing label (contract ticker only when the binding has none).
    binding_cik: str
    binding_ticker: str
    sic: str
    issuer_class: str
    observations: Mapping[str, MetricObservation]
    same_end: Mapping[str, tuple[MetricObservation, ...]] = field(default_factory=dict)


def _aligned_to_anchor(
    peer: _AdmittedPeer, anchor_observations: Mapping[str, MetricObservation]
) -> Mapping[str, MetricObservation]:
    """The peer's observations with each same-end tie resolved toward the anchor.

    Only a metric whose latest end date carried several cells is touched: the
    one closest in duration to the anchor's own cell replaces the default
    (shortest) pick. Nothing moves off the latest end date, so a duration no
    candidate can match still reaches the kernel's A35-D1 exclusion.
    """
    aligned = dict(peer.observations)
    for metric_id, pool in peer.same_end.items():
        anchor_obs = anchor_observations.get(metric_id)
        target = None if anchor_obs is None else _duration_days(anchor_obs)
        if target is None:
            continue
        aligned[metric_id] = min(
            pool,
            key=lambda obs: (
                _duration_days(obs) is None,
                abs((_duration_days(obs) or 0) - target),
                _duration_days(obs) or 0,
            ),
        )
    return aligned


def _member_exclusion(
    member: Mapping[str, Any],
    issuer_id: str | None,
    code: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "ticker": member["ticker"],
        "cik": member["cik10"],
        "issuer_id": issuer_id,
        "code": code,
        "reason": reason,
    }


def _compose_peer_cohort(
    root: Path, issuer_master: IssuerMasterIndex
) -> tuple[dict[str, Any] | None, str | None]:
    """Build the peer-cohort payload, or a typed null with its reason.

    Evaluation order is fixed: an unavailable store excludes every member
    (``production_dataset_absent``); otherwise per member, in contract order,
    identity (exact-CIK join) is resolved before the generation is read, the
    generation's owner identity binding before the SIC gate, and the SIC gate
    before any class derivation — so a member without a pinned SIC never
    reaches an applicability call. An excluded member never enters a
    CohortDefinition.
    """
    contract = _read_coverage_contract(root)
    members = _contract_members(contract) if contract else []
    if not members:
        return None, PEER_COHORT_REASON_DATASET_ABSENT
    contract_id = str(contract.get("contract_id") or "")
    metric_ids = _contract_metric_ids(contract)
    class_not_applicable = _class_not_applicable_metric_ids(root)

    exclusions: list[dict[str, Any]] = []
    admitted: list[_AdmittedPeer] = []
    store = build_production_dataset_store()
    if store is None:
        for member in members:
            issuer_id, _ = issuer_master.join(member["cik10"])
            exclusions.append(_member_exclusion(
                member, issuer_id, _PEER_EXCLUSION_DATASET,
                "production dataset store is unavailable",
            ))
        return None, PEER_COHORT_REASON_DATASET_ABSENT

    registry_versions: dict[str, dict[str, str]] = {}
    for member in members:
        issuer_id, join_reason = issuer_master.join(member["cik10"])
        if issuer_id is None:
            exclusions.append(_member_exclusion(
                member, None, _PEER_EXCLUSION_IDENTITY,
                f"issuer id unresolved via issuer master: {join_reason}",
            ))
            continue
        try:
            generation = load_latest_generation(store, issuer_id)
        except ProductionDatasetError:
            generation = None
        if generation is None:
            exclusions.append(_member_exclusion(
                member, issuer_id, _PEER_EXCLUSION_DATASET,
                "no admitted production dataset generation for the issuer",
            ))
            continue
        # A14: the identity authority is the generation's owner binding (the
        # admission-time manifest issuer block), never the contract's local
        # cik/ticker. A binding that cannot be read, or whose cik has no
        # cik10 form, is an absent dataset identity; a cik that names a
        # different issuer than the contract row is an identity disagreement
        # — either way the member is excluded, never silently re-keyed.
        try:
            binding = generation.binding
        except ProductionDatasetError:
            binding = None
        binding_cik = _cik10(binding.cik) if binding is not None else None
        if binding_cik is None:
            exclusions.append(_member_exclusion(
                member, issuer_id, _PEER_EXCLUSION_DATASET,
                "no owner identity binding on the admitted production dataset generation",
            ))
            continue
        if binding_cik != member["cik10"]:
            exclusions.append(_member_exclusion(
                member, issuer_id, _PEER_EXCLUSION_IDENTITY,
                # A14 review F1: the authority-side cik is carried in the
                # reason so the disagreement is reconstructable from the row.
                f"contract cik disagrees with owner binding cik {binding_cik}",
            ))
            continue
        # the binding's listing label wins; the contract ticker survives only
        # when the binding carries none (A14).
        binding_ticker = (
            str(binding.ticker).strip().upper()
            if binding.ticker is not None else ""
        ) or member["ticker"]
        sic = _pinned_sic(member["sic"])
        if sic is None:
            exclusions.append(_member_exclusion(
                member, issuer_id, _PEER_EXCLUSION_SIC,
                "coverage contract carries no parseable pinned sic for the issuer",
            ))
            continue
        issuer_class = issuer_class_for_sic(sic)
        excluded_metrics = (
            frozenset(metric_ids) & class_not_applicable.get(issuer_class, frozenset())
        )
        same_end: dict[str, tuple[MetricObservation, ...]] = {}
        observations = _tree_metric_observations(
            generation, member["accessions"], metric_ids, excluded_metrics,
            member.get("accession_periods") or {}, same_end=same_end,
            metric_versions=_generation_metric_versions(
                generation, metric_ids, registry_versions
            ),
        )
        if observations is None:
            exclusions.append(_member_exclusion(
                member, issuer_id, _PEER_EXCLUSION_DATASET,
                "no readable precomputed statement trees for the contract accessions",
            ))
            continue
        admitted.append(_AdmittedPeer(
            member=member,
            issuer_id=issuer_id,
            binding_cik=binding_cik,
            binding_ticker=binding_ticker,
            sic=sic,
            issuer_class=issuer_class,
            observations=observations,
            same_end=same_end,
        ))

    # Distinct contract CIKs can in principle join to one issuer id; the
    # cohort kernel requires unique entity ids, so later duplicates stay out
    # with the identity-plane exclusion rather than a build failure.
    seen_ids: set[str] = set()
    unique_admitted: list[_AdmittedPeer] = []
    for peer in admitted:
        if peer.issuer_id in seen_ids:
            exclusions.append(_member_exclusion(
                peer.member, peer.issuer_id, _PEER_EXCLUSION_IDENTITY,
                "issuer id collides across contract members",
            ))
            continue
        seen_ids.add(peer.issuer_id)
        unique_admitted.append(peer)
    admitted = unique_admitted
    if not admitted:
        return None, PEER_COHORT_REASON_DATASET_ABSENT

    tables: list[dict[str, Any]] = []
    for anchor in admitted:
        observations_by_issuer = {
            peer.issuer_id: peer.observations
            if peer is anchor
            else _aligned_to_anchor(peer, anchor.observations)
            for peer in admitted
        }
        definition = CohortDefinition(
            cohort_id=f"{contract_id}:{anchor.issuer_id}" if contract_id else anchor.issuer_id,
            anchor_issuer_id=anchor.issuer_id,
            members=tuple(
                CohortMember(
                    issuer_id=peer.issuer_id,
                    # A14: the owner binding's identity is the only key the
                    # kernel collapses on; the contract row's local cik/ticker
                    # never reach the table.
                    cik=peer.binding_cik,
                    tickers=(peer.binding_ticker,),
                    issuer_class=peer.issuer_class,
                    sic=peer.sic,
                )
                for peer in admitted
            ),
            metric_ids=metric_ids,
        )
        table = build_cohort_table(definition, observations_by_issuer)
        # to_dict() passes through unchanged: no re-rank, no re-format, no
        # invented row — only the anchor identity is attached beside it.
        tables.append({**table.to_dict(), "anchor_issuer_id": anchor.issuer_id})

    return {
        "contract_id": contract_id,
        "policy": _cohort_policy_defaults(),
        "tables": tables,
        "member_exclusions": exclusions,
    }, None


def _peer_cohort_within_budget(state: dict[str, Any]) -> bool:
    """Whether the state carrying its peer-cohort payload fits the transport.

    Same budget the writer enforces (deterministic serialization, 5 MiB
    gzip / 32 MiB raw); an over-budget payload is dropped whole with a typed
    reason, never truncated.
    """
    encoded = (
        json.dumps(state, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    if len(encoded) > MAX_DECOMPRESSED_BYTES:
        return False
    return len(gzip.compress(encoded, compresslevel=9)) <= MAX_COMPRESSED_BYTES


def compose_state(root: Path, *, generated_at: str | None = None) -> dict[str, Any]:
    q_path = root / "data" / "edgar" / "statements_quarterly.parquet"
    a_path = root / "data" / "edgar" / "statements.parquet"
    if not q_path.exists():
        raise FileNotFoundError(q_path)
    quarterly = pd.read_parquet(q_path)
    annual = pd.read_parquet(a_path) if a_path.exists() else pd.DataFrame()
    names, sectors, ciks = _metadata(root)
    issuer_master = _issuer_master_index(root)
    disclosure_projections, disclosure_load_issues = _load_disclosure_projections(root)
    disclosure_projections, disclosure_budget = _disclosure_budgeted(disclosure_projections)

    for col in ("fiscal_year", "fiscal_quarter"):
        quarterly[col] = pd.to_numeric(quarterly[col], errors="coerce")
    quarterly = quarterly.dropna(subset=["ticker", "fiscal_year", "fiscal_quarter", "period_end"])
    quarterly["ticker"] = quarterly["ticker"].astype(str).str.upper()
    quarterly["filed"] = quarterly["filed"].fillna("").astype(str)
    quarterly = quarterly.sort_values(["ticker", "fiscal_year", "fiscal_quarter", "filed", "period_end"])
    quarterly = quarterly.drop_duplicates(["ticker", "fiscal_year", "fiscal_quarter"], keep="last")
    if not annual.empty:
        annual["ticker"] = annual["ticker"].astype(str).str.upper()

    companies: dict[str, dict[str, Any]] = {}
    ranked: list[dict[str, Any]] = []
    coverage_by_detector = {d["id"]: {"evaluated": 0, "triggered": 0} for d in DETECTORS}
    all_latest_filed: list[str] = []
    disclosure_attached = 0
    disclosure_tracks_ready = 0
    disclosure_tracks_not_evaluable = 0

    for ticker, rows in quarterly.groupby("ticker", sort=True):
        rows = rows.sort_values(["period_end", "filed"])
        current = rows.iloc[-1]
        same_q = rows[
            (rows["fiscal_quarter"] == current["fiscal_quarter"])
            & (rows["fiscal_year"] == current["fiscal_year"] - 1)
        ]
        if same_q.empty:
            continue
        prior = same_q.iloc[-1]
        cik = ciks.get(ticker)
        findings = detect_quarterly(current, prior, cik)
        annual_rows = annual[annual["ticker"] == ticker] if not annual.empty else pd.DataFrame()
        accrual = detect_accruals(annual_rows, current, prior, cik)
        if accrual:
            findings.append(accrual)

        # Coverage is an evidence-availability measure, never a company score.
        available = sum(
            _finite(current.get(metric)) is not None and _finite(prior.get(metric)) is not None
            for metric in QUARTERLY_METRICS
        )
        metrics_pct = available / len(QUARTERLY_METRICS)
        latest_filed = str(current.get("filed") or "")
        if latest_filed:
            all_latest_filed.append(latest_filed)

        evaluability = detector_evaluability(current, prior, annual_rows)
        evaluable_count = sum(evaluability.values())
        for detector in DETECTORS:
            det_id = detector["id"]
            if evaluability[det_id]:
                coverage_by_detector[det_id]["evaluated"] += 1
            if any(f["detector"] == det_id for f in findings):
                coverage_by_detector[det_id]["triggered"] += 1

        findings.sort(key=lambda f: (0 if f["priority"] == "high" else 1, f["detector"]))
        if any(f["priority"] == "high" for f in findings):
            action = {"key": "high", "en": "Changes need attention", "zh": "有变化需要关注"}
        elif findings:
            action = {"key": "watch", "en": "Changes to keep an eye on", "zh": "有变化值得持续观察"}
        elif evaluable_count < len(DETECTORS):
            action = {
                "key": "limited",
                "en": "Some checks could not run",
                "zh": "部分检查无法运行",
            }
        else:
            action = {
                "key": "covered",
                "en": "No unusual change in covered checks",
                "zh": "已覆盖检查暂无异常变化",
            }

        recent = rows.tail(8).iloc[::-1]
        entity_id, entity_id_reason = issuer_master.join(_cik10(cik))
        company = {
            "symbol": ticker,
            "name": names.get(ticker, ticker),
            "sector": sectors.get(ticker, "Unclassified"),
            "cik": cik,
            # FIF P1-b (I1): joined from the committed issuer master by exact
            # CIK only — null with a machine-readable reason otherwise.
            "entity_id": entity_id,
            "entity_id_reason": entity_id_reason,
            "latest_period": _period_label(current),
            "latest_filed": latest_filed,
            "action": action,
            "coverage": {
                "periods": int(len(recent)),
                "metrics_pct": round(metrics_pct, 4),
                "detectors_evaluable": evaluable_count,
                "detectors_total": len(DETECTORS),
                "basis": "normalized_quarterly_projection",
            },
            "findings": findings,
            "periods": [_clean_period(row) for _, row in recent.iterrows()],
        }
        disclosure = disclosure_projections.get(ticker)
        if disclosure is not None:
            company["disclosures"] = _state_disclosure_projection(disclosure)
            disclosure_attached += 1
            disclosure_tracks_ready += int(disclosure["coverage"].get("tracks_ready") or 0)
            disclosure_tracks_not_evaluable += int(disclosure["coverage"].get("tracks_not_evaluable") or 0)
        companies[ticker] = company
        for finding in findings:
            ranked.append({
                "symbol": ticker,
                "finding_id": finding["id"],
                "priority": finding["priority"],
                "topic": finding["topic"],
                "latest_filed": latest_filed,
            })

    ranked.sort(key=lambda row: (
        0 if row["priority"] == "high" else 1,
        -(int(row["latest_filed"].replace("-", "")[:8]) if row["latest_filed"][:10].replace("-", "").isdigit() else 0),
        row["symbol"], row["finding_id"],
    ))
    high_n = sum(1 for row in ranked if row["priority"] == "high")
    as_of = max(all_latest_filed) if all_latest_filed else None
    generated = generated_at or _source_generated_at(quarterly, annual, as_of)
    # A stable, evidence-rich launch symbol makes the workbench reproducible while
    # the ranked feed remains fully live.  Fall back deterministically when SMCI
    # leaves the universe or has no current review item.
    default_symbol = (
        "SMCI"
        if companies.get("SMCI", {}).get("findings")
        else (ranked[0]["symbol"] if ranked else next(iter(companies), "AAPL"))
    )

    peer_cohort, peer_cohort_reason = _compose_peer_cohort(root, issuer_master)
    state = {
        "schema": SCHEMA,
        "generated_at": generated,
        "as_of": as_of,
        "source": {
            "label": "SEC Company Facts normalized broad-universe projection",
            "basis": "repository quarterly and annual EDGAR panels",
            "limitations_en": [
                "This broad-universe statements projection preserves filing dates but is not accession-coherent; optional disclosure records below have their own accession and source-receipt lineage.",
                "Quarterly flow fields can be derived from year-to-date facts, and different metrics can come from independently selected standard concepts.",
                "Open the SEC source endpoints before relying on a finding; company-specific taxonomy and corporate actions can require review.",
                "Findings are deterministic review prompts, not misconduct claims, ratings, or trading signals.",
            ],
            "limitations_zh": [
                "广覆盖报表投影保留披露日期，但并非 accession 一致；下方可选披露记录拥有各自的 accession 与来源回执谱系。",
                "季度流量字段可能由年初至今数据推导，不同指标也可能来自独立选择的标准概念。",
                "依赖任何发现前请打开 SEC 来源端点；公司自定义分类及公司行动可能需要人工复核。",
                "发现是确定性的复核提示，不是欺诈指控、评级或交易信号。",
            ],
            "companyfacts_url_pattern": "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json",
            "accession_disclosure_projection": {
                "available": bool(disclosure_projections),
                "basis": "prebuilt checksum-bound primary-document comparisons; never fetched during render",
                "knowledge_clock": "source_event_acceptance_time",
            },
        },
        "summary": {
            "companies": len(companies),
            "findings": len(ranked),
            "high": high_n,
            "watch": len(ranked) - high_n,
            "latest_filing": as_of,
            "detector_coverage": coverage_by_detector,
            "disclosure_coverage": {
                **disclosure_budget,
                "attached_to_companies": disclosure_attached,
                "unmatched_company_projections": max(0, disclosure_budget["selected"] - disclosure_attached),
                "tracks_ready": disclosure_tracks_ready,
                "tracks_not_evaluable": disclosure_tracks_not_evaluable,
                "load_issues": disclosure_load_issues,
            },
        },
        "detectors": list(DETECTORS),
        "default_symbol": default_symbol,
        "ranked_findings": ranked,
        "companies": companies,
        # FIF P1-b (I5): the payload envelope. peer_cohort carries the cohort
        # tables through unchanged or is null with exactly one reason.
        "payload": {
            "schema": STATE_PAYLOAD_SCHEMA,
            "peer_cohort": peer_cohort,
            "peer_cohort_reason": peer_cohort_reason,
        },
    }
    if peer_cohort is not None and not _peer_cohort_within_budget(state):
        state["payload"]["peer_cohort"] = None
        state["payload"]["peer_cohort_reason"] = PEER_COHORT_REASON_OVER_BUDGET
    return state


def render(root: Path, state: dict[str, Any]) -> Path:
    """Atomically render the public shell/assets, then commit private state last."""
    summary = state.get("summary") or {}
    _write_public_summary(root, summary, generated_at=state.get("generated_at"))
    page = render_shell(root, state_summary=summary)
    _write_state_atomic(root / LOCAL_STATE_RELATIVE, state)
    return page


def _temp_sibling(path: Path) -> Path:
    return path.with_name(f".{path.name}.{os.getpid()}.tmp")


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = _temp_sibling(destination)
    try:
        shutil.copyfile(source, temp)
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)


def _write_state_atomic(path: Path, state: dict[str, Any]) -> Path:
    """Write one deterministic, validated gzip without exposing partial bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = _temp_sibling(path)
    encoded = json.dumps(state, ensure_ascii=False, separators=(",", ":")) + "\n"
    try:
        with temp.open("wb") as raw_fh:
            # Suppress the temp filename in the gzip header; mtime=0 alone is
            # insufficient because the PID-bearing atomic temp path would make
            # byte-identical state hash differently on every build process.
            with gzip.GzipFile(filename="", fileobj=raw_fh, mode="wb", compresslevel=9, mtime=0) as zipped:
                zipped.write(encoded.encode("utf-8"))
            raw_fh.flush()
            os.fsync(raw_fh.fileno())
        decode_state_blob(temp.read_bytes())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return path


def public_summary_projection(summary: dict[str, Any]) -> dict[str, int]:
    """Project the private summary down to the two counts the gate may publish.

    Aggregate COUNTS are free by the same house rule the tier preview states:
    a count names nobody, while the member rows are the product. This builds the
    projection field by field on purpose — never by spreading `summary` — so a
    later key added to compose_state() (a symbol, a top-finding, a per-company
    breakdown) cannot reach a public byte by default.
    """
    return {
        "companies": int(summary.get("companies") or 0),
        "findings": int(summary.get("findings") or 0),
    }


def _reusable_public_summary_stamp(path: Path, projection: dict[str, int]) -> str | None:
    """Return the prior file's stamp when it carries the identical projection.

    A rewrite of unchanged counts must produce byte-identical bytes, never a
    fresher stamp: ``generated_at`` here is a source-snapshot clock, and a
    render that only re-projects the same counts has no source event to
    freshen it with (FIF A21 — no re-render freshness). The wall-clock
    fallback stays for the genuine no-prior-file case (fresh clone, first
    build).
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict) or raw.get("schema") != PUBLIC_SUMMARY_SCHEMA:
        return None
    try:
        if public_summary_projection(raw) != projection:
            return None
    except (TypeError, ValueError):
        return None
    stamped = raw.get("generated_at")
    if not isinstance(stamped, str) or not stamped:
        return None
    return stamped


def _write_public_summary(root: Path, summary: dict[str, Any], *, generated_at: str | None = None) -> Path:
    """Persist the counts-only projection so BOTH render paths read one number.

    The private state is gitignored, and build_site.py re-renders this shell
    through render_from_state() moments after the nightly forensics build (see
    daily.yml — forensics, then build_site) and again on every render.yml lane
    that never composes state at all. A count passed only in-process would be
    overwritten by that second render within seconds and would never exist on a
    render-lane rebuild. This file is committed by the nightly's broad
    `git add data/`, so the shell prints the same counts on every path.
    """
    path = root / PUBLIC_SUMMARY_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    projection = public_summary_projection(summary)
    stamped = (
        generated_at
        or _reusable_public_summary_stamp(path, projection)
        or datetime.now(timezone.utc).isoformat()
    )
    payload = {
        "schema": PUBLIC_SUMMARY_SCHEMA,
        "generated_at": stamped,
        **projection,
    }
    temp = _temp_sibling(path)
    try:
        temp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return path


def read_public_summary(root: Path, *, now: datetime | None = None) -> dict[str, int]:
    """Read the committed counts, or {} when absent/unreadable/malformed/stale.

    Absence is a normal state, not an error: a fresh clone, a CI checkout and
    the very first build all lack the file, and the page must simply omit the
    fact rather than print a zero or a stale literal. A projection older than
    PUBLIC_SUMMARY_MAX_AGE_DAYS is treated the same way as an absent one — see
    that constant for why an unrefreshed file can otherwise outlive its build.
    """
    try:
        raw = json.loads((root / PUBLIC_SUMMARY_RELATIVE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict) or raw.get("schema") != PUBLIC_SUMMARY_SCHEMA:
        return {}
    try:
        stamped = datetime.fromisoformat(str(raw["generated_at"]))
    except (KeyError, TypeError, ValueError):
        return {}
    if stamped.tzinfo is None:
        stamped = stamped.replace(tzinfo=timezone.utc)
    age = (now or datetime.now(timezone.utc)) - stamped
    if age.days > PUBLIC_SUMMARY_MAX_AGE_DAYS:
        return {}
    try:
        return public_summary_projection(raw)
    except (TypeError, ValueError):
        return {}


def render_shell(root: Path, state_summary: dict[str, Any] | None = None) -> Path:
    """Render only the public workbench shell, versioned assets, and free counts.

    `state_summary` carries no rows — only the aggregate counts projected by
    public_summary_projection(). When the caller supplies none (build_site's
    compatibility hook), the committed projection is read from disk so every
    render path agrees.
    """
    site = root / "site"
    site.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(str(root / "templates")), autoescape=True)
    counts = public_summary_projection(state_summary) if state_summary else read_public_summary(root)
    html = env.get_template("fundamental_forensics.html.j2").render(
        generated_utc="private-state-runtime",
        state_summary=counts,
        active_section="research",
        active_page="fundamental_forensics",
        holding_js_version=hashlib.sha256((root / "templates" / "institutional_holding_research.js").read_bytes()).hexdigest()[:8],
        holding_css_version=hashlib.sha256((root / "templates" / "institutional_holding_research.css").read_bytes()).hexdigest()[:8],
    )
    page = site / "fundamental_forensics.html"
    page_temp = _temp_sibling(page)
    try:
        write_page(page_temp, html)
        os.replace(page_temp, page)
    finally:
        page_temp.unlink(missing_ok=True)
    for name in ("fundamental_forensics.css", "fundamental_forensics.js",
                 "institutional_holding_research.css", "institutional_holding_research.js"):
        _atomic_copy(root / "templates" / name, site / name)
    return page


def render_from_state(root: Path) -> Path:
    """Compatibility hook for build_site: render only the public shell/assets."""
    return render_shell(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=config.ROOT)
    parser.add_argument("--generated-at", default=None, help="Injected clock for deterministic builds/tests")
    publish_group = parser.add_mutually_exclusive_group()
    publish_group.add_argument(
        "--publish-private",
        action="store_true",
        help="Build locally, then publish and byte-verify the private R2 object",
    )
    publish_group.add_argument(
        "--publish-only",
        action="store_true",
        help="Publish the already-built local private state without recomputing",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        state_path = root / LOCAL_STATE_RELATIVE
        if args.publish_only:
            if not publish_state_blob(state_path):
                raise RuntimeError("private state publish or read-back verification failed")
            log.info("published and verified %s", state_path)
            return 0
        state = compose_state(root, generated_at=args.generated_at)
        page = render(root, state)
        log.info("wrote %s (%d companies, %d findings)", page, state["summary"]["companies"], state["summary"]["findings"])
        if args.publish_private and not publish_state_blob(state_path):
            raise RuntimeError("private state publish or read-back verification failed")
        return 0
    except Exception as exc:  # noqa: BLE001 - additive page must not break the main build
        log.exception("fundamental forensics build skipped: %s", exc)
        print(f"::warning title=fundamental_forensics::build skipped ({type(exc).__name__}: {exc})", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
