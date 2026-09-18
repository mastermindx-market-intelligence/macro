"""China physical-gold premium monitor.

Display-only context for the Commodity Vector Gold detail surface.

The canonical construction compares Shanghai Gold Benchmark PM (RMB/gram)
with an entitled London AM benchmark (USD/troy ounce), normalized through an
entitled USDCNY observation.  An optional intraday construction may compare
SGE Au99.99 with an entitled London/global spot reference.

This module is deliberately provider-neutral and read-only.  It never scrapes,
collects, persists, scores, ranks, sizes, or changes commodity authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd


TROY_OZ_GRAMS = 31.1034768
_REQUIRED_LEG_KEYS = ("group", "name", "column", "source_label")


@dataclass(frozen=True)
class _Unavailable:
    code: str
    en: str
    zh: str


_REASON = {
    "not_configured": _Unavailable(
        "not_configured",
        "Entitled Shanghai/London benchmark sources are not configured yet.",
        "尚未配置已获授权的上海／伦敦基准数据源。",
    ),
    "source_not_entitled": _Unavailable(
        "source_not_entitled",
        "A configured source is not marked entitled for this product surface.",
        "已配置的数据源未被标记为可用于本产品页面。",
    ),
    "source_config_invalid": _Unavailable(
        "source_config_invalid",
        "A source reference is incomplete or malformed.",
        "数据源引用不完整或格式无效。",
    ),
    "source_data_unavailable": _Unavailable(
        "source_data_unavailable",
        "One or more required benchmark legs are unavailable.",
        "一个或多个必需的基准数据暂不可用。",
    ),
    "no_aligned_observation": _Unavailable(
        "no_aligned_observation",
        "The benchmark legs do not share a valid aligned observation.",
        "各基准数据腿没有可用的对齐观测值。",
    ),
}


def _to_utc_index(index) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(index, utc=True))


def _positive_series(frame: pd.DataFrame | None, column: str, *, daily: bool) -> pd.Series:
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty or column not in frame:
        return pd.Series(dtype=float)
    values = pd.to_numeric(frame[column], errors="coerce").astype(float)
    idx = _to_utc_index(frame.index)
    if daily:
        idx = idx.tz_convert(None).normalize()
    values = pd.Series(values.to_numpy(), index=idx, dtype=float)
    values = values[np.isfinite(values.to_numpy()) & (values.to_numpy() > 0)]
    return values[~values.index.duplicated(keep="last")].sort_index()


def _premium_frame(sge_rmb_g: pd.Series, london_usd_oz: pd.Series, usdcny: pd.Series) -> pd.DataFrame:
    joined = pd.concat(
        [
            sge_rmb_g.rename("sge_rmb_g"),
            london_usd_oz.rename("london_usd_oz"),
            usdcny.rename("usdcny"),
        ],
        axis=1,
        join="inner",
    ).dropna()
    if joined.empty:
        return pd.DataFrame(
            columns=[
                "sge_rmb_g",
                "london_usd_oz",
                "usdcny",
                "sge_usd_oz",
                "spread_usd_oz",
                "premium_pct",
                "ma5_pct",
            ]
        )
    out = joined.astype(float)
    out["sge_usd_oz"] = out["sge_rmb_g"] * TROY_OZ_GRAMS / out["usdcny"]
    out["spread_usd_oz"] = out["sge_usd_oz"] - out["london_usd_oz"]
    out["premium_pct"] = (out["sge_usd_oz"] / out["london_usd_oz"] - 1.0) * 100.0
    out = out.replace([np.inf, -np.inf], np.nan).dropna()
    out["ma5_pct"] = out["premium_pct"].rolling(5, min_periods=1).mean()
    return out


def compute_daily_benchmark(
    sge: pd.DataFrame,
    london: pd.DataFrame,
    fx: pd.DataFrame,
    *,
    sge_column: str,
    london_column: str,
    fx_column: str,
) -> pd.DataFrame:
    """Return same-date canonical SHAUPM/London benchmark observations."""
    return _premium_frame(
        _positive_series(sge, sge_column, daily=True),
        _positive_series(london, london_column, daily=True),
        _positive_series(fx, fx_column, daily=True),
    )


def compute_intraday_proxy(
    sge: pd.DataFrame,
    london: pd.DataFrame,
    fx: pd.DataFrame,
    *,
    sge_column: str,
    london_column: str,
    fx_column: str,
    max_skew_minutes: float = 15.0,
) -> pd.DataFrame:
    """Return at most one current indicative point when latest legs are aligned."""
    legs = [
        _positive_series(sge, sge_column, daily=False),
        _positive_series(london, london_column, daily=False),
        _positive_series(fx, fx_column, daily=False),
    ]
    if any(s.empty for s in legs):
        return pd.DataFrame()
    latest = [s.iloc[[-1]] for s in legs]
    stamps = [s.index[-1] for s in latest]
    skew = (max(stamps) - min(stamps)).total_seconds() / 60.0
    if not np.isfinite(skew) or skew > float(max_skew_minutes):
        return pd.DataFrame()

    aligned_at = max(stamps)
    out = _premium_frame(
        pd.Series([float(latest[0].iloc[0])], index=[aligned_at]),
        pd.Series([float(latest[1].iloc[0])], index=[aligned_at]),
        pd.Series([float(latest[2].iloc[0])], index=[aligned_at]),
    )
    if not out.empty:
        out["methodology"] = "intraday_indicative"
        out["sge_observed_at"] = stamps[0]
        out["london_observed_at"] = stamps[1]
        out["fx_observed_at"] = stamps[2]
    return out


def _validate_leg(spec: object) -> _Unavailable | None:
    if not isinstance(spec, dict):
        return _REASON["source_config_invalid"]
    if spec.get("entitled") is not True:
        return _REASON["source_not_entitled"]
    if any(not isinstance(spec.get(k), str) or not spec.get(k).strip() for k in _REQUIRED_LEG_KEYS):
        return _REASON["source_config_invalid"]
    return None


def _read_method(
    method_cfg: object,
    *,
    reader: Callable[[str, str], pd.DataFrame | None],
    intraday: bool,
) -> tuple[pd.DataFrame, list[str], _Unavailable | None]:
    if not isinstance(method_cfg, dict) or not method_cfg:
        return pd.DataFrame(), [], _REASON["not_configured"]

    specs = {}
    labels = []
    for key in ("sge", "london", "fx"):
        spec = method_cfg.get(key)
        problem = _validate_leg(spec)
        if problem is not None:
            return pd.DataFrame(), labels, problem
        specs[key] = spec
        labels.append(spec["source_label"])
    frames = {}
    for key, spec in specs.items():
        try:
            frames[key] = reader(spec["group"], spec["name"])
        except Exception:
            frames[key] = None
        if frames[key] is None or not isinstance(frames[key], pd.DataFrame) or frames[key].empty:
            return pd.DataFrame(), labels, _REASON["source_data_unavailable"]

    if intraday:
        out = compute_intraday_proxy(
            frames["sge"],
            frames["london"],
            frames["fx"],
            sge_column=specs["sge"]["column"],
            london_column=specs["london"]["column"],
            fx_column=specs["fx"]["column"],
            max_skew_minutes=float(method_cfg.get("max_skew_minutes", 15.0)),
        )
    else:
        out = compute_daily_benchmark(
            frames["sge"],
            frames["london"],
            frames["fx"],
            sge_column=specs["sge"]["column"],
            london_column=specs["london"]["column"],
            fx_column=specs["fx"]["column"],
        )
    if out.empty:
        return out, labels, _REASON["no_aligned_observation"]
    return out, labels, None


def _as_utc(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _daily_fresh(frame: pd.DataFrame, cfg: dict, now: pd.Timestamp) -> bool:
    if frame.empty:
        return False
    max_age = int(cfg.get("max_age_days", 7))
    asof = pd.Timestamp(frame.index[-1]).tz_localize("UTC")
    return (now.normalize() - asof.normalize()).days <= max_age


def _intraday_fresh(frame: pd.DataFrame, cfg: dict, now: pd.Timestamp) -> bool:
    if frame.empty:
        return False
    max_age = float(cfg.get("max_age_minutes", 180.0))
    asof = _as_utc(frame.index[-1])
    age = (now - asof).total_seconds() / 60.0
    return age >= 0 and age <= max_age


def _point(row: pd.Series, when, *, intraday: bool) -> dict:
    return {
        ("ts" if intraday else "date"): (
            _as_utc(when).isoformat() if intraday else pd.Timestamp(when).date().isoformat()
        ),
        "premium_pct": float(row["premium_pct"]),
        "spread_usd_oz": float(row["spread_usd_oz"]),
        "sge_usd_oz": float(row["sge_usd_oz"]),
        "london_usd_oz": float(row["london_usd_oz"]),
        "ma5_pct": float(row["ma5_pct"]),
    }


def _state(premium: float | None) -> tuple[str, str, str]:
    if premium is None or not np.isfinite(premium):
        return "unavailable", "Unavailable", "暂不可用"
    if premium > 0:
        return "premium", "Premium", "溢价"
    if premium < 0:
        return "discount", "Discount", "折价"
    return "parity", "Near parity", "接近平价"


def _unavailable_vm(reason: _Unavailable) -> dict:
    return {
        "available": False,
        "status": "unavailable",
        "reason_code": reason.code,
        "reason_en": reason.en,
        "reason_zh": reason.zh,
        "current_method": None,
        "methodology_label_en": "China physical premium",
        "methodology_label_zh": "中国实物黄金溢价",
        "state": "unavailable",
        "state_en": "Unavailable",
        "state_zh": "暂不可用",
        "premium_pct": None,
        "spread_usd_oz": None,
        "sge_usd_oz": None,
        "london_usd_oz": None,
        "stats": {"avg_5": None, "range_30": None},
        "canonical": {"available": False, "fresh": False, "asof": None, "sources": []},
        "intraday": {"available": False, "fresh": False, "asof": None, "sources": []},
        "chart": {"canonical": [], "intraday": None},
    }


def build_view_model(
    cfg: dict | None,
    *,
    reader: Callable[[str, str], pd.DataFrame | None] | None = None,
    now=None,
) -> dict:
    """Build the display-only Gold premium view-model from entitled store refs."""
    if reader is None:
        from lib import store

        reader = store.read

    cfg = cfg if isinstance(cfg, dict) else {}
    if not cfg:
        return _unavailable_vm(_REASON["not_configured"])

    now_ts = _as_utc(now if now is not None else pd.Timestamp.now(tz="UTC"))
    canonical_cfg = cfg.get("canonical")
    intraday_cfg = cfg.get("intraday")

    canonical, canonical_sources, canonical_problem = _read_method(
        canonical_cfg, reader=reader, intraday=False
    )
    intraday, intraday_sources, intraday_problem = _read_method(
        intraday_cfg, reader=reader, intraday=True
    )

    canonical_available = canonical_problem is None and not canonical.empty
    intraday_available = intraday_problem is None and not intraday.empty
    canonical_fresh = canonical_available and _daily_fresh(canonical, canonical_cfg, now_ts)
    intraday_fresh = intraday_available and _intraday_fresh(intraday, intraday_cfg, now_ts)

    if not canonical_available and not intraday_available:
        problem = canonical_problem or intraday_problem or _REASON["source_data_unavailable"]
        vm = _unavailable_vm(problem)
        vm["canonical"]["sources"] = canonical_sources
        vm["intraday"]["sources"] = intraday_sources
        return vm

    canonical_points = [
        _point(row, idx, intraday=False) for idx, row in canonical.iterrows()
    ] if canonical_available else []
    intraday_point = (
        _point(intraday.iloc[-1], intraday.index[-1], intraday=True)
        if intraday_available else None
    )

    if intraday_fresh:
        current_row = intraday.iloc[-1]
        current_method = "intraday"
        label_en, label_zh = "Indicative intraday basis", "日内指示性价差"
    elif canonical_available:
        current_row = canonical.iloc[-1]
        current_method = "canonical"
        label_en, label_zh = "Official daily benchmark basis", "官方日度基准价差"
    else:
        current_row = intraday.iloc[-1]
        current_method = "intraday"
        label_en, label_zh = "Indicative intraday basis", "日内指示性价差"

    premium = float(current_row["premium_pct"])
    state, state_en, state_zh = _state(premium)
    last30 = canonical["premium_pct"].tail(30) if canonical_available else pd.Series(dtype=float)

    canonical_asof = (
        pd.Timestamp(canonical.index[-1]).date().isoformat() if canonical_available else None
    )
    intraday_asof = (
        _as_utc(intraday.index[-1]).isoformat() if intraday_available else None
    )

    return {
        "available": True,
        "status": "available",
        "reason_code": None,
        "reason_en": None,
        "reason_zh": None,
        "current_method": current_method,
        "methodology_label_en": label_en,
        "methodology_label_zh": label_zh,
        "state": state,
        "state_en": state_en,
        "state_zh": state_zh,
        "premium_pct": premium,
        "spread_usd_oz": float(current_row["spread_usd_oz"]),
        "sge_usd_oz": float(current_row["sge_usd_oz"]),
        "london_usd_oz": float(current_row["london_usd_oz"]),
        "stats": {
            "avg_5": float(canonical["premium_pct"].tail(5).mean()) if canonical_available else None,
            "range_30": (
                [float(last30.min()), float(last30.max())] if not last30.empty else None
            ),
        },
        "canonical": {
            "available": canonical_available,
            "fresh": bool(canonical_fresh),
            "asof": canonical_asof,
            "sources": canonical_sources,
        },
        "intraday": {
            "available": intraday_available,
            "fresh": bool(intraday_fresh),
            "asof": intraday_asof,
            "sources": intraday_sources,
        },
        "chart": {
            "canonical": canonical_points,
            "intraday": intraday_point,
        },
    }
