"""Bounded observation histories for the native economic workspace consumer.

Projection only: the existing collector parquets remain the data owners. These
are latest revised component observations, NOT archived workspace states, PIT
vintages, forecasts known on each historical date, or a new market score.
No request handler reads these files. The suite builder loads each source once.
"""
from __future__ import annotations

import copy
import datetime as dt
import math
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

MAX_POINTS = 780
BASIS = "latest_revised_observation_history"
REVISION = (
    "Latest local collector history; reference dates, not first-known dates. "
    "Revisions can change earlier observations. No interpolation or resampling. "
    "Reference-period age is not source-update freshness; release and collection clocks are unknown. "
    f"At most {MAX_POINTS} source observations are published per series."
)


@dataclass(frozen=True)
class HistorySource:
    key: str
    column: str
    en: str
    zh: str
    unit: str
    cadence_days: int
    grace_days: int
    divisor: float = 1.0
    group: str = "fred"

    @property
    def source_id(self) -> str:
        return f"history:{self.group}:{self.key}"

    @property
    def artifact(self) -> str:
        return f"data/{self.group}/{self.key}.parquet"


# Native collector columns/units: config.yml fred groups and build.py Treasury
# mapping. These are explicit REFERENCE-AGE policies. Existing raw-series pairs
# are reused for RSAFS (80+17), TGA and corridor rates (5+4). Other pairs are
# descriptive history windows, not the original assessment's freshness policy.
# GDPNow is quarter-start dated and revises within the quarter; its date cannot
# establish whether the collector captured the latest intraquarter update.
SOURCES = {
    "WALCL": HistorySource("WALCL", "fed_balance_sheet", "Federal Reserve assets", "美联储资产", "USD_bn", 7, 7, 1000),
    "RRPONTSYD": HistorySource("RRPONTSYD", "on_rrp", "Overnight reverse repo", "隔夜逆回购", "USD_bn", 1, 6),
    "tga": HistorySource("tga", "tga_mn", "Treasury cash balance", "财政部现金余额", "USD_bn", 5, 4, 1000, "treasury"),
    "GDPNOW": HistorySource("GDPNOW", "gdpnow", "GDPNow · quarterly growth, annualized", "GDPNow·季度增长率（年化）", "percent_saar", 92, 31),
    "WEI": HistorySource("WEI", "wei", "Weekly Economic Index", "每周经济指数", "index", 7, 7),
    "INDPRO": HistorySource("INDPRO", "industrial_prod", "Industrial production", "工业生产", "index", 45, 17),
    "RSAFS": HistorySource("RSAFS", "retail_sales", "Retail sales · nominal", "零售销售额·名义值", "USD_mn", 80, 17),
    "IC4WSA": HistorySource("IC4WSA", "initial_claims_4wk", "Initial claims · 4-week average", "首次申领失业救济·四周平均", "count", 7, 7),
    "CCSA": HistorySource("CCSA", "continued_claims", "Continuing claims", "持续申领失业救济", "count", 14, 7),
    "PAYEMS": HistorySource("PAYEMS", "payrolls", "Nonfarm payroll employment", "非农就业人数", "thousands", 45, 17),
    "CPIAUCSL": HistorySource("CPIAUCSL", "headline_cpi", "Consumer prices · all items", "消费者价格·所有项目", "cpi_index", 45, 17),
    "CPILFESL": HistorySource("CPILFESL", "core_cpi", "Consumer prices · core", "消费者价格·核心", "cpi_index", 45, 17),
    "PCEPI": HistorySource("PCEPI", "headline_pce", "PCE prices · all items", "PCE价格·所有项目", "pce_index", 45, 17),
    "PCEPILFE": HistorySource("PCEPILFE", "core_pce", "PCE prices · core", "PCE价格·核心", "pce_index", 45, 17),
    "EFFR": HistorySource("EFFR", "effr", "Effective federal funds rate", "有效联邦基金利率", "percent", 5, 4),
    "SOFR": HistorySource("SOFR", "sofr", "Secured overnight financing rate", "担保隔夜融资利率", "percent", 5, 4),
    "IORB": HistorySource("IORB", "iorb", "Interest on reserve balances", "准备金余额利率", "percent", 5, 4),
    "NFCI": HistorySource("NFCI", "nfci", "National Financial Conditions Index", "全国金融状况指数", "index", 7, 7),
    "ANFCI": HistorySource("ANFCI", "anfci", "Adjusted Financial Conditions Index", "调整后的金融状况指数", "index", 7, 7),
    "NFCICREDIT": HistorySource("NFCICREDIT", "nfci_credit", "Financial conditions · credit", "金融状况·信贷", "index", 7, 7),
    "NFCIRISK": HistorySource("NFCIRISK", "nfci_risk", "Financial conditions · risk", "金融状况·风险", "index", 7, 7),
}
WORKSPACE_SOURCES = {
    "liquidity_regime": ("WALCL", "RRPONTSYD", "tga"),
    "growth_real_economy": ("GDPNOW", "WEI", "INDPRO"),
    "business_activity": ("INDPRO", "RSAFS"),
    "labor_markets": ("IC4WSA", "CCSA", "PAYEMS"),
    "inflation_system": ("CPIAUCSL", "CPILFESL", "PCEPI", "PCEPILFE"),
    "monetary_policy": ("EFFR", "SOFR", "IORB"),
    "financial_conditions": ("NFCI", "ANFCI", "NFCICREDIT", "NFCIRISK"),
}

PUBLISHERS = {
    "WALCL": "Board of Governors of the Federal Reserve System",
    "RRPONTSYD": "Federal Reserve Bank of New York",
    "tga": "U.S. Department of the Treasury",
    "GDPNOW": "Federal Reserve Bank of Atlanta",
    "WEI": "Daniel J. Lewis; Karel Mertens; James H. Stock",
    "INDPRO": "Board of Governors of the Federal Reserve System",
    "RSAFS": "U.S. Census Bureau",
    "IC4WSA": "U.S. Employment and Training Administration",
    "CCSA": "U.S. Employment and Training Administration",
    "PAYEMS": "U.S. Bureau of Labor Statistics",
    "CPIAUCSL": "U.S. Bureau of Labor Statistics",
    "CPILFESL": "U.S. Bureau of Labor Statistics",
    "PCEPI": "U.S. Bureau of Economic Analysis",
    "PCEPILFE": "U.S. Bureau of Economic Analysis",
    "EFFR": "Federal Reserve Bank of New York",
    "SOFR": "Federal Reserve Bank of New York",
    "IORB": "Board of Governors of the Federal Reserve System",
    "NFCI": "Federal Reserve Bank of Chicago",
    "ANFCI": "Federal Reserve Bank of Chicago",
    "NFCICREDIT": "Federal Reserve Bank of Chicago",
    "NFCIRISK": "Federal Reserve Bank of Chicago",
}


def _date(value: Any) -> dt.date:
    if isinstance(value, dt.datetime):
        if value.time() != dt.time():
            raise ValueError("history requires reference dates, not intraday clocks")
        return value.date()
    if isinstance(value, dt.date):
        return value
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("history reference date must be YYYY-MM-DD")
    return dt.date.fromisoformat(value)


def _read_rows(path: Path, column: str) -> list[tuple[str, float | None]] | None:
    """Missing is absent; present unreadable/malformed data raises before publish.

    Keep null observations. Do not use build._load_series_rows, which drops them.
    Lazy pandas keeps the pure projection usable in contract tests.
    """
    if not path.exists():
        return None
    import pandas as pd  # noqa: PLC0415

    frame = pd.read_parquet(path)
    if column not in frame.columns:
        raise ValueError(f"history column missing: {path.name}:{column}")
    series = frame[column]
    result = []
    for raw_date, value in series.items():
        stamp = pd.Timestamp(raw_date)
        if pd.isna(stamp) or stamp.time() != dt.time():
            raise ValueError(f"invalid history date in {path.name}")
        result.append((stamp.date().isoformat(), None if pd.isna(value) else value))
    return result


def project_source(spec: HistorySource, rows: Sequence | None, *, built_at: str) -> dict:
    """Pure, fail-closed normalization, with real null gaps and a bounded tail."""
    built = dt.datetime.fromisoformat(built_at.replace("Z", "+00:00"))
    if built.tzinfo is None:
        raise ValueError("built_at requires an explicit timezone")
    today = built.astimezone(dt.timezone.utc).date()
    dated: dict[dt.date, float | None] = {}
    for row in rows or ():
        if not isinstance(row, (tuple, list)) or len(row) != 2:
            raise ValueError("history row must be a date/value pair")
        date, value = _date(row[0]), row[1]
        if date > today or date in dated:
            raise ValueError("history has a future or duplicate reference date")
        if value is not None and (isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value))):
            raise ValueError("history value must be finite numeric or null")
        dated[date] = None if value is None else float(value) / spec.divisor
    ordered = sorted(dated.items())[-MAX_POINTS:]
    points = [{"t": d.isoformat(), "v": v} for d, v in ordered]
    measured = [(d, v) for d, v in ordered if v is not None]
    latest = measured[-1][0] if measured else None
    # This token describes reference-period age ONLY. The native view labels it
    # accordingly in both series and evidence, never as source-update freshness.
    age = (today - latest).days if latest else None
    freshness = ("SOURCE_FAILED" if age is None else "CURRENT" if age <= spec.cadence_days
                 else "LATE_WITHIN_TOLERANCE" if age <= spec.cadence_days + spec.grace_days
                 else "STALE_SOURCE")
    label = {"en": spec.en, "zh": spec.zh}
    provider = PUBLISHERS[spec.key]
    canonical = f"https://fred.stlouisfed.org/series/{spec.key}" if spec.group == "fred" else "https://fiscaldata.treasury.gov/datasets/daily-treasury-statement/"
    attribution = f"{provider}, {spec.en} [{spec.key}], retrieved from FRED, Federal Reserve Bank of St. Louis; {canonical}. Source attribution is retained for display and reuse." if spec.group == "fred" else f"{provider}; {canonical}."
    source = {
        "source_id": spec.source_id, "label": label,
        "owner_ref": canonical, "provider": provider + (" · via FRED" if spec.group == "fred" else ""),
        "reference_period": latest.isoformat() if latest else None,
        "released_at": None, "first_known_at": None, "collected_at": None, "revised_at": None,
        "correction_state": "unknown", "rights_state": "OPEN",
        "transform": (attribution + f" Collector column {spec.column}; divide by {spec.divisor:g}. " + REVISION
                      + f" Reference-age cadence/grace: {spec.cadence_days}/{spec.grace_days} calendar days."),
        "definition_id": spec.source_id, "definition_version": "1.0.0",
        "artifact_ref": spec.artifact, "freshness": freshness,
    }
    return {"entry": {
        "series_id": spec.source_id, "label": label, "unit": spec.unit, "basis": BASIS,
        "points": points, "source_ref": spec.source_id, "freshness": freshness,
        "revision_behavior": REVISION,
    }, "source": source, "present": bool(measured)}


def load_economic_histories(*, fred_dir: Path | str, treasury_dir: Path | str,
                            built_at: str, reader: Callable | None = None) -> dict:
    """One source read per batch, shared across workspace projections."""
    read = reader or _read_rows
    projected = {}
    for key, spec in SOURCES.items():
        directory = Path(fred_dir if spec.group == "fred" else treasury_dir)
        projected[key] = project_source(spec, read(directory / f"{key}.parquet", spec.column), built_at=built_at)
    result = {}
    for workspace, keys in WORKSPACE_SOURCES.items():
        available = sum(projected[key]["present"] for key in keys)
        result[workspace] = {
            "series": {"items": [projected[key]["entry"] for key in keys],
                       "status": "PRESENT" if available == len(keys) else "PARTIAL" if available else "ABSENT",
                       "null_reason": None if available == len(keys) else "SOURCE_FAILED"},
            "sources": [projected[key]["source"] for key in keys],
        }
    return result


def attach_workspace_history(body: Mapping, projection: Mapping | None) -> dict:
    """Preserve current assessment/authority/availability; add optional depth."""
    result = copy.deepcopy(dict(body))
    if projection is None:
        return result
    if (result.get("series") or {}).get("items"):
        raise ValueError("history attachment refuses to replace an existing series owner")
    source_block = result.setdefault("sources", {"items": []})
    existing = {item["source_id"] for item in source_block["items"]}
    for source in projection["sources"]:
        if source["source_id"] in existing:
            raise ValueError("history source identity collides with an existing owner")
        existing.add(source["source_id"])
        source_block["items"].append(copy.deepcopy(source))
    result["series"] = copy.deepcopy(projection["series"])
    return result
