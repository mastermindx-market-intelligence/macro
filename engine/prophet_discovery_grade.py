"""Governed outcome evaluator for HK/CA Prophet discovery observations.

This is Lane-B's separately-keyed "third door": it reads the existing
zero-authority discovery store, imports the canonical board-ledger price /
benchmark / suspension owners, and calls engine.grading.forward_metrics.
It never changes discovery identity, rank, entry, publication or Brain state.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from engine import board_ledger, board_shadow, grading
from lib import config

MARKETS = ("HK", "CA")
HORIZONS = tuple(board_ledger._HORIZONS_D)
KEY = (
    "session_date", "market", "security_ref",
    "security_ref_raw", "challenger_definition",
)

MATURED = "MATURED"
ACCRUING = "ACCRUING"
SUSPENDED = "SUSPENDED"
UNAVAILABLE_PRICE = "UNAVAILABLE_PRICE"
NO_FILL = "NO_FILL"

_IDENTITY = list(KEY)
_BASE = [
    *_IDENTITY,
    "candidate_origin", "availability_status", "availability_source",
    "outcome_state", "fill_date", "fill_offset", "entry_price",
    "suspended", "benchmark_available", "survivorship",
    "terminal_state_clean8_21", "terminal_state_clean15_126",
]
_METRICS: list[str] = []
for _h in HORIZONS:
    _METRICS.extend([
        f"fwd_ret_{_h}", f"fwd_mfe_{_h}", f"fwd_mdd_{_h}",
        f"bench_ret_{_h}", f"excess_ret_{_h}",
    ])
SCHEMA = tuple([*_BASE, *_METRICS])
_SOURCE_REQUIRED = {
    "session_date", "security_ref", "security_ref_raw",
    "challenger_definition",
}


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=list(SCHEMA))


def _blank_metrics() -> dict[str, Any]:
    return {name: None for name in _METRICS}


def _base_row(row: pd.Series, market: str) -> dict[str, Any]:
    return {
        "session_date": str(row["session_date"]),
        "market": market,
        "security_ref": str(row["security_ref"]),
        "security_ref_raw": str(row["security_ref_raw"]),
        "challenger_definition": str(row["challenger_definition"]),
        "candidate_origin": row.get("candidate_origin"),
        "availability_status": row.get("availability_status"),
        "availability_source": row.get("availability_source"),
        "outcome_state": None,
        "fill_date": None,
        "fill_offset": None,
        "entry_price": None,
        "suspended": None,
        "benchmark_available": None,
        "survivorship": "no_dead_name_store",
        "terminal_state_clean8_21": None,
        "terminal_state_clean15_126": None,
        **_blank_metrics(),
    }
def _float_or_none(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def grade_frame(market: str, discovery: pd.DataFrame) -> pd.DataFrame:
    """Grade discovery observations with the exact HK/CA board-ledger conventions."""
    m = str(market or "").upper()
    if m not in MARKETS:
        raise ValueError(f"unsupported market {market!r}")
    if discovery is None or discovery.empty:
        return _empty_frame()

    missing = sorted(_SOURCE_REQUIRED - set(discovery.columns))
    if missing:
        raise ValueError(f"discovery source missing required columns: {missing}")
    if "market" in discovery.columns:
        foreign = {
            str(x).upper() for x in discovery["market"].dropna().unique()
            if str(x).upper() != m
        }
        if foreign:
            raise ValueError(f"{m} discovery source contains foreign market rows: {sorted(foreign)}")

    bench = board_ledger._bench_close(m)
    cache: dict = {}
    rows: list[dict[str, Any]] = []

    for _, source in discovery.iterrows():
        out = _base_row(source, m)
        ticker = out["security_ref"]
        close = board_ledger._name_close(m, ticker, ca_cache=cache)
        if close is None or close.empty:
            out["outcome_state"] = UNAVAILABLE_PRICE
            out["benchmark_available"] = bench is not None
            rows.append(out)
            continue
        signal_date = out["session_date"]
        fill_iloc = grading.fill_index(close, signal_date)
        if fill_iloc is None:
            out["outcome_state"] = NO_FILL
            out["benchmark_available"] = bench is not None
            rows.append(out)
            continue

        fill_date = pd.Timestamp(close.index[fill_iloc])
        out["fill_date"] = str(fill_date.date())
        if board_ledger._is_suspended(close, fill_date):
            out["outcome_state"] = SUSPENDED
            out["suspended"] = True
            out["benchmark_available"] = bench is not None
            rows.append(out)
            continue

        fm = grading.forward_metrics(close, signal_date, horizons=HORIZONS)
        bm = (
            grading.forward_metrics(bench, signal_date, horizons=HORIZONS)
            if bench is not None and not bench.empty else {}
        )
        out["fill_date"] = fm.get("fill_date")
        out["fill_offset"] = fm.get("fill_offset")
        out["entry_price"] = _float_or_none(fm.get("entry_price"))
        out["suspended"] = False
        out["benchmark_available"] = bool(bm)

        matured = 0
        for h in HORIZONS:
            name_ret = _float_or_none(fm.get(f"fwd_ret_{h}"))
            bench_ret = _float_or_none(bm.get(f"fwd_ret_{h}")) if bm else None
            out[f"fwd_ret_{h}"] = name_ret
            out[f"fwd_mfe_{h}"] = _float_or_none(fm.get(f"fwd_mfe_{h}"))
            out[f"fwd_mdd_{h}"] = _float_or_none(fm.get(f"fwd_mdd_{h}"))
            out[f"bench_ret_{h}"] = bench_ret
            out[f"excess_ret_{h}"] = (
                name_ret - bench_ret
                if name_ret is not None and bench_ret is not None else None
            )
            matured += int(name_ret is not None)

        # Canonical terminal-state partitions from engine.grading. These are
        # outcome labels only: they never feed candidate identity, rank, entry,
        # publication, or Brain authority. Insufficient forward history stays
        # null exactly as grading.terminal_state defines it.
        ts8 = grading.terminal_state(
            close,
            signal_date,
            liftoff_mult=grading.LIFTOFF_8,
            liftoff_horizon=grading.LIFTOFF_HORIZON_21,
        )
        ts15 = grading.terminal_state(
            close,
            signal_date,
            liftoff_mult=grading.LIFTOFF_15,
            liftoff_horizon=grading.LIFTOFF_HORIZON_126,
        )
        out["terminal_state_clean8_21"] = ts8.get("state")
        out["terminal_state_clean15_126"] = ts15.get("state")
        out["outcome_state"] = MATURED if matured == len(HORIZONS) else ACCRUING
        rows.append(out)
    frame = pd.DataFrame(rows).reindex(columns=list(SCHEMA))
    if frame.empty:
        return _empty_frame()
    return frame.sort_values(list(KEY), kind="stable").reset_index(drop=True)


def _outcome_path(market: str) -> Path:
    return (
        config.data_dir() / board_shadow.STORE_DIR
        / f"{market.lower()}_discovery_outcomes.parquet"
    )


def _same_frame(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    try:
        pd.testing.assert_frame_equal(
            left.reset_index(drop=True),
            right.reset_index(drop=True),
            check_dtype=False,
            check_like=False,
        )
        return True
    except AssertionError:
        return False


def _median_or_none(frame: pd.DataFrame, column: str) -> float | None:
    if column not in frame.columns:
        return None
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    return float(values.median()) if not values.empty else None


def _terminal_summary(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    if column not in frame.columns:
        states = pd.Series(dtype=object)
    else:
        states = frame[column].dropna().astype(str)
    counts = states.value_counts().to_dict()
    n = int(len(states))

    def rate(*labels: str) -> float | None:
        if not n:
            return None
        return float(sum(int(counts.get(label, 0)) for label in labels) / n)

    return {
        "n_matured": n,
        "counts": {str(k): int(v) for k, v in counts.items()},
        "clean_liftoff_rate": rate(grading.TerminalState.CLEAN_LIFTOFF),
        "stopped_dead_money_rate": rate(
            grading.TerminalState.STOPPED,
            grading.TerminalState.DEAD_MONEY,
        ),
        "cushioned_rate": rate(grading.TerminalState.CUSHIONED),
    }


def _summary_core(frame: pd.DataFrame) -> dict[str, Any]:
    """Canonical measured metrics for one observation cohort."""
    n = int(len(frame))
    states = (
        frame["outcome_state"].fillna("UNKNOWN").astype(str)
        if "outcome_state" in frame.columns else pd.Series(dtype=object)
    )
    unavailable = int((states == UNAVAILABLE_PRICE).sum()) if n else 0
    horizons: dict[str, dict[str, Any]] = {}
    for h in HORIZONS:
        mfe_col = f"fwd_mfe_{h}"
        matured = (
            int(pd.to_numeric(frame[mfe_col], errors="coerce").notna().sum())
            if mfe_col in frame.columns else 0
        )
        horizons[f"{h}d"] = {
            "n_matured": matured,
            "mfe_median": _median_or_none(frame, mfe_col),
            "mae_median": _median_or_none(frame, f"fwd_mdd_{h}"),
            "excess_ret_median": _median_or_none(frame, f"excess_ret_{h}"),
        }
    return {
        "n_observations": n,
        "price_store_coverage_rate": (
            float((n - unavailable) / n) if n else None
        ),
        "horizons": horizons,
        "terminal_states": {
            "clean8_21": _terminal_summary(
                frame, "terminal_state_clean8_21"
            ),
            "clean15_126": _terminal_summary(
                frame, "terminal_state_clean15_126"
            ),
        },
    }


def summarize_outcomes(frame: pd.DataFrame) -> dict[str, Any]:
    """Measured discovery quality, including descriptive source strata.

    Origin-token cohorts overlap by construction and are NEVER a rank/promotion
    plane. Undefined winner/first-surface/catastrophic denominators remain absent.
    """
    summary = _summary_core(frame)
    by_availability: dict[str, dict[str, Any]] = {}
    if "availability_status" in frame.columns:
        labels = frame["availability_status"].fillna("UNKNOWN").astype(str)
        for label in sorted(labels.unique()):
            by_availability[label] = _summary_core(frame[labels == label])

    by_origin_token: dict[str, dict[str, Any]] = {}
    if "candidate_origin" in frame.columns:
        origins = frame["candidate_origin"].fillna("").astype(str)
        tokens = sorted({
            token
            for origin in origins
            for token in origin.split("+")
            if token
        })
        for token in tokens:
            mask = origins.map(lambda raw: token in raw.split("+"))
            by_origin_token[token] = _summary_core(frame[mask])

    summary.update({
        "cohort_semantics": "overlapping_descriptive_only",
        "by_availability": by_availability,
        "by_origin_token": by_origin_token,
    })
    return summary


def grade_market(market: str) -> dict[str, Any]:
    """Refresh one market's derived outcome store from its append-only discovery source."""
    m = str(market or "").upper()
    if m not in MARKETS:
        raise ValueError(f"unsupported market {market!r}")
    source_path = board_shadow._lane_b_path(m)
    out_path = _outcome_path(m)
    if not source_path.exists():
        return {
            "market": m, "available": False, "state": "SOURCE_ABSENT",
            "n_source": 0, "n_rows": 0,
        }
    try:
        source = pd.read_parquet(source_path)
    except Exception as exc:
        raise RuntimeError(f"{m} discovery source unreadable: {exc}") from exc
    fresh = grade_frame(m, source)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    changed = True
    if out_path.exists():
        try:
            prior = pd.read_parquet(out_path).reindex(columns=list(SCHEMA))
            changed = not _same_frame(prior, fresh)
        except Exception:
            changed = True

    if changed:
        tmp = out_path.with_suffix(".tmp.parquet")
        fresh.to_parquet(tmp, index=False)
        tmp.replace(out_path)

    counts = fresh["outcome_state"].value_counts(dropna=False).to_dict()
    terminal8 = (
        fresh["terminal_state_clean8_21"].dropna().astype(str).value_counts().to_dict()
    )
    terminal15 = (
        fresh["terminal_state_clean15_126"].dropna().astype(str).value_counts().to_dict()
    )
    return {
        "market": m,
        "available": True,
        "state": "UPDATED" if changed else "UNCHANGED",
        "n_source": int(len(source)),
        "n_rows": int(len(fresh)),
        "n_matured": int(counts.get(MATURED, 0)),
        "n_accruing": int(counts.get(ACCRUING, 0)),
        "n_suspended": int(counts.get(SUSPENDED, 0)),
        "n_unavailable_price": int(counts.get(UNAVAILABLE_PRICE, 0)),
        "n_no_fill": int(counts.get(NO_FILL, 0)),
        "terminal_clean8_21": terminal8,
        "terminal_clean15_126": terminal15,
        "candidate_metrics": summarize_outcomes(fresh),
    }


def grade_all() -> dict[str, dict[str, Any]]:
    return {market: grade_market(market) for market in MARKETS}
