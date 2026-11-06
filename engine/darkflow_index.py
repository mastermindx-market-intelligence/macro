"""Independent DIX-style observation, not institutional flow or a trade signal.

Consumes the existing FINRA and unadjusted-price stores. No network, state writes,
model calls, risk score, alerts, or PSS-AF1 changes. See research/DARKFLOW_INDEX.md.
FINRA ShortVolume includes ShortExemptVolume; adding the latter double counts it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

import numpy as np
import pandas as pd

SCHEMA = "darkflow_index.v1"
METHOD = "finra-short-marked-dollar-share.v1"
# Explicit common-share aliases only. Do not uppercase preferred-share tickers.
ALIASES = {"BRK/B": "BRK-B", "BRK.B": "BRK-B", "BF/B": "BF-B", "BF.B": "BF-B"}


@dataclass(frozen=True)
class Policy:
    market_coverage: float = 0.90
    min_market_names: int = 400
    sector_coverage: float = 0.80
    min_sector_names: int = 5
    percentile_window: int = 252
    percentile_min: int = 60
    history_sessions: int = 504


def canonical_symbol(value: object) -> str:
    symbol = str(value).strip()
    return ALIASES.get(symbol, symbol)


def _days(values) -> pd.Series:
    return pd.to_datetime(values, errors="coerce", utc=True).dt.tz_localize(None).dt.normalize()


def _finite(value) -> float | None:
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


def _round(value, places: int = 4) -> float | None:
    value = _finite(value)
    return round(value, places) if value is not None else None


def _clean_rows(frame: pd.DataFrame, columns: list[str]) -> tuple[pd.DataFrame, dict]:
    required = {"date", "ticker", *columns}
    if frame is None or not required.issubset(frame.columns):
        return pd.DataFrame(columns=list(required)), {"missing_schema": True, "rejected": 0}
    out = frame[list(required)].copy()
    out["date"] = _days(out["date"])
    out["ticker"] = out["ticker"].map(canonical_symbol)
    for column in columns:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    valid = out["date"].notna() & out["ticker"].str.fullmatch(r"[A-Z][A-Z0-9-]{0,14}", na=False)
    valid &= np.isfinite(out[columns]).all(axis=1)
    # Ambiguous duplicates are not summed (facilities may already be consolidated).
    duplicates = out.duplicated(["date", "ticker"], keep=False)
    return out[valid & ~duplicates], {
        "missing_schema": False, "rejected": int((~valid | duplicates).sum()),
        "duplicate_rows": int(duplicates.sum()),
    }


def members_on(membership: pd.DataFrame, day: pd.Timestamp) -> set[str]:
    """Inclusive endpoints match the repository's historical-membership contract."""
    started = membership["start_date"] <= day
    active = membership["end_date"].isna() | (membership["end_date"] >= day)
    return set(membership.loc[started & active, "ticker"])


def _reading(rows: pd.DataFrame, expected: int, coverage_floor: float, minimum: int = 1) -> dict:
    n = len(rows)
    coverage = n / expected if expected else 0.0
    qualified = expected >= minimum and n >= minimum and coverage >= coverage_floor
    dollars = float(rows["dollars"].sum()) if n else 0.0
    value = 100 * float(rows["short_dollars"].sum()) / dollars if qualified and dollars > 0 else None
    return {
        "value": _round(value), "observed_names": n, "expected_names": expected,
        "coverage_pct": _round(100 * coverage, 2),
        "state": "observed" if value is not None else "insufficient_coverage",
        "median_ratio_pct": _round(100 * rows["ratio"].median()) if qualified else None,
    }


def decompose(current: pd.DataFrame, prior: pd.DataFrame) -> dict:
    """Exact midpoint attribution, retaining entry/exit and coverage-mix effects.

    Contributions sum to aggregate change. Weight changes are NOT buying/selling.
    Source rows must already be validated; this does not grant coverage authority.
    """
    if current.empty or prior.empty:
        return {"state": "unavailable", "rows": []}
    a = current.set_index("ticker")[["ratio", "dollars"]].copy()
    b = prior.set_index("ticker")[["ratio", "dollars"]].copy()
    a["weight"] = a.dollars / a.dollars.sum()
    b["weight"] = b.dollars / b.dollars.sum()
    records = []
    for ticker in sorted(set(a.index) | set(b.index)):
        if ticker in a.index and ticker in b.index:
            ca, cb = a.loc[ticker], b.loc[ticker]
            ratio = 100 * (ca.weight + cb.weight) / 2 * (ca.ratio - cb.ratio)
            weight = 100 * (ca.ratio + cb.ratio) / 2 * (ca.weight - cb.weight)
            membership = 0.0
        else:
            ratio = weight = 0.0
            membership = (100 * a.loc[ticker, "weight"] * a.loc[ticker, "ratio"]
                          if ticker in a.index else -100 * b.loc[ticker, "weight"] * b.loc[ticker, "ratio"])
        records.append({"ticker": ticker, "ratio_pp": ratio, "weight_pp": weight,
                        "coverage_mix_pp": membership, "total_pp": ratio + weight + membership})
    total = lambda key: _round(sum(r[key] for r in records), 8)
    return {"state": "observed", "ratio_pp": total("ratio_pp"), "weight_pp": total("weight_pp"),
            "coverage_mix_pp": total("coverage_mix_pp"), "total_pp": total("total_pp"),
            "common_names": len(set(a.index) & set(b.index)),
            "rows": [{k: (_round(v, 6) if isinstance(v, (float, np.floating)) else v)
                      for k, v in row.items()}
                     for row in sorted(records, key=lambda r: abs(r["total_pp"]), reverse=True)[:12]]}


def build_index(panel: pd.DataFrame, prices: pd.DataFrame, membership: pd.DataFrame,
                sectors: dict[str, str], sessions: list, *, asof: str,
                known_at: str, price_basis: str, policy: Policy = Policy()) -> dict:
    """Build a causal dated display from explicit inputs, including missing sessions.

    Historical rows are reconstructed from the supplied source vintage, NOT claimed
    as originally available then. First observed publication is supplied by the caller.
    """
    if price_basis != "unadjusted":
        raise ValueError("Raw contemporaneous prices required; adjusted prices cannot weight raw shares")
    if not 0 < policy.market_coverage <= 1 or not 0 < policy.sector_coverage <= 1:
        raise ValueError("Coverage floors must be in (0, 1]")
    days = sorted({pd.Timestamp(d).normalize() for d in sessions if str(d)[:10] <= asof})
    days = days[-policy.history_sessions:]
    if not days or str(days[-1].date()) != asof:
        raise ValueError("asof must be the final explicit market session")
    required = {"ticker", "start_date", "end_date", "src"}
    if membership is None or not required.issubset(membership.columns):
        raise ValueError("Historical index membership is required")
    mem = membership[membership.src == "sp500"].copy()
    mem["ticker"] = mem["ticker"].map(canonical_symbol)
    mem["start_date"] = _days(mem["start_date"])
    mem["end_date"] = _days(mem["end_date"])
    if mem.empty or mem.start_date.isna().any():
        raise ValueError("Historical S&P 500 membership is missing or malformed")
    raw, finra_quality = _clean_rows(panel, ["short_vol", "short_exempt", "total_vol"])
    px, price_quality = _clean_rows(prices, ["close"])
    eligible = (raw.total_vol > 0) & (raw.short_vol >= 0) & (raw.short_vol <= raw.total_vol)
    eligible &= (raw.short_exempt >= 0) & (raw.short_exempt <= raw.short_vol)
    finra_quality["invalid_volume_rows"] = int((~eligible).sum())
    raw = raw[eligible]
    price_quality["invalid_price_rows"] = int((px.close <= 0).sum())
    px = px[px.close > 0]
    joined = raw.merge(px, on=["date", "ticker"], how="inner", validate="one_to_one")
    joined = joined[joined.date.isin(days)].copy()
    joined["ratio"] = joined.short_vol / joined.total_vol
    joined["dollars"] = joined.close * joined.total_vol
    joined["short_dollars"] = joined.close * joined.short_vol
    joined = joined[np.isfinite(joined[["dollars", "short_dollars"]]).all(axis=1)]
    sector_map = {canonical_symbol(k): str(v) for k, v in sectors.items()}
    joined["sector"] = joined.ticker.map(sector_map).fillna("Unclassified")
    grouped = {d: g for d, g in joined.groupby("date", sort=False)}
    empty = joined.iloc[:0]
    series, frames, expected_sets = [], {}, {}
    sector_history = {name: [] for name in sorted(set(sector_map.values()) | {"Unclassified"})}
    for day in days:
        expected = members_on(mem, day)
        rows = grouped.get(day, empty)
        rows = rows[rows.ticker.isin(expected)]
        frames[day], expected_sets[day] = rows, expected
        series.append({"date": str(day.date()), **_reading(rows, len(expected), policy.market_coverage, policy.min_market_names)})
        for name, points in sector_history.items():
            n_expected = sum(sector_map.get(t, "Unclassified") == name for t in expected)
            reading = _reading(rows[rows.sector == name], n_expected, policy.sector_coverage, policy.min_sector_names)
            points.append({"date": str(day.date()), "value": reading["value"],
                           "coverage_pct": reading["coverage_pct"]})
    by_day = {row["date"]: row for row in series}
    last = dict(series[-1])
    for n in [1, 3, 5]:
        old = series[-n - 1] if len(series) > n else None
        last[f"change_{n}d_pp"] = (_round(last["value"] - old["value"])
                                        if last["value"] is not None and old and old["value"] is not None else None)
    # Three-session finite differences reduce one-day noise. These describe the
    # ratio trajectory, not investor intent, price direction or a reversal call.
    recent4, recent7 = series[-4:], series[-7:]
    last["velocity_3d_pp_per_session"] = (
        _round((recent4[-1]["value"] - recent4[0]["value"]) / 3)
        if len(recent4) == 4 and all(r["value"] is not None for r in recent4) else None
    )
    last["acceleration_3d_pp_per_session2"] = (
        _round((recent7[-1]["value"] - 2 * recent7[3]["value"] + recent7[0]["value"]) / 9)
        if len(recent7) == 7 and all(r["value"] is not None for r in recent7) else None
    )
    window = series[-5:]
    last["mean_5d"] = (_round(np.mean([r["value"] for r in window]))
                         if len(window) == 5 and all(r["value"] is not None for r in window) else None)
    baseline = [r["value"] for r in series[-policy.percentile_window - 1:-1] if r["value"] is not None]
    last["percentile_observations"] = len(baseline)
    last["percentile"] = (_round(100 * (sum(v < last["value"] for v in baseline)
                                          + .5 * sum(v == last["value"] for v in baseline)) / len(baseline), 1)
                          if last["value"] is not None and len(baseline) >= policy.percentile_min else None)
    current = frames[days[-1]]
    prior_day = days[-6] if len(days) >= 6 else None
    prior = frames[prior_day] if prior_day is not None else empty
    expected = expected_sets[days[-1]]
    last["missing_finra_names"] = len(expected - set(raw.loc[raw.date == days[-1], "ticker"]))
    last["missing_price_names"] = len(expected - set(px.loc[px.date == days[-1], "ticker"]))
    sector_rows = []
    for sector in sorted({sector_map.get(t, "Unclassified") for t in expected}):
        members = {t for t in expected if sector_map.get(t, "Unclassified") == sector}
        cur = current[current.sector == sector]
        read = _reading(cur, len(members), policy.sector_coverage, policy.min_sector_names)
        old_expected = (sum(sector_map.get(t, "Unclassified") == sector for t in expected_sets[prior_day])
                        if prior_day is not None else 0)
        old_read = _reading(prior[prior.sector == sector], old_expected,
                            policy.sector_coverage, policy.min_sector_names)
        change = (read["value"] - old_read["value"]
                  if read["value"] is not None and old_read["value"] is not None else None)
        sector_rows.append({"sector": sector, **read, "change_5d_pp": _round(change),
                            "sample_dollar_weight_pct": _round(100 * cur.dollars.sum() / current.dollars.sum())
                            if len(current) and last["value"] is not None else None})
    prior_qualified = prior_day is not None and by_day[str(prior_day.date())]["value"] is not None
    comparable = current[["ticker", "ratio"]].merge(prior[["ticker", "ratio"]], on="ticker", suffixes=("", "_prior"))
    last["ratio_breadth_names"] = len(comparable)
    last["ratio_breadth_up_pct"] = (_round(100 * (comparable.ratio > comparable.ratio_prior).mean(), 1)
                                    if len(comparable) and prior_qualified and last["value"] is not None else None)
    attribution = (decompose(current, prior) if prior_qualified and last["value"] is not None
                   else {"state": "unavailable", "rows": []})
    last_complete = next((r for r in reversed(series) if r["value"] is not None), None)
    observations = [{"ticker": r.ticker, "ratio_pct": _round(100 * r.ratio), "sector": r.sector}
                    for r in current.itertuples()] if last["value"] is not None else []
    result = {
        "schema": SCHEMA, "method": METHOD, "known_at": known_at, "asof": asof,
        "tier": "display", "trade_authority": False, "provider_parity_verified": False,
        "universe": "S&P 500 historical membership", "price_basis": price_basis,
        "history_basis": "reconstructed_source_vintage", "sector_basis": "current_classification",
        "policy": asdict(policy), "current": last, "last_complete": last_complete,
        "sectors": sector_rows, "attribution_5d": attribution, "history": series,
        "sector_history": sector_history,
        "names": observations, "quality": {"finra": finra_quality, "prices": price_quality},
        "interpretation": "Short-marked off-exchange volume, not net selling or institutional buying.",
    }
    # Deterministic content identity includes all inputs exposed to consumers, never NaN.
    body = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    result["generation"] = hashlib.sha256(body.encode()).hexdigest()
    return result
