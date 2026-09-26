"""Governed outcome evaluator for HK/CA Prophet discovery observations.

This is Lane-B's separately-keyed "third door": it reads the existing
zero-authority discovery store, imports the canonical board-ledger price /
benchmark / suspension owners, and calls engine.grading.forward_metrics.
It never changes discovery identity, rank, entry, publication or Brain state.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from engine import board_ledger, board_shadow, grading, ledger_lane, validation
from lib import config

MARKETS = ("HK", "CA")
HORIZONS = tuple(board_ledger._HORIZONS_D)
_CATASTROPHIC_HORIZON = 21
_CATASTROPHIC_RETURN = -0.15
_TOP_K_REGRET_HORIZON = 21
KEY = (
    "session_date", "market", "security_ref",
    "security_ref_raw", "challenger_definition",
)
_SOURCE_KEY = (
    "session_date", "security_ref", "security_ref_raw",
    "challenger_definition",
)
_HISTORY_LIMITS = {
    "history_coverage": "window_bounded_positive_records_only",
    "continuous_tenure_supported": False,
    "exact_exit_supported": False,
    "exit_reason_supported": False,
}

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
_SOURCE_REQUIRED = set(_SOURCE_KEY)
_SOURCE_EVIDENCE = (
    "candidate_origin", "availability_status", "availability_source",
)


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=list(SCHEMA))


def _frame_digest(frame: pd.DataFrame, columns: tuple[str, ...]) -> str:
    canonical = frame.reindex(columns=list(columns)).copy()
    for column in columns:
        canonical[column] = canonical[column].map(
            lambda value: "<NULL>" if pd.isna(value) else str(value)
        )
    canonical = canonical.sort_values(list(columns), kind="stable")
    payload = json.dumps(
        {"columns": list(columns), "rows": canonical.values.tolist()},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _identity_digest(frame: pd.DataFrame) -> str:
    return _frame_digest(frame, _SOURCE_KEY)


def _cohort_digest(frame: pd.DataFrame) -> str:
    return _frame_digest(frame, (*_SOURCE_KEY, *_SOURCE_EVIDENCE))


def _source_evidence(frame: pd.DataFrame) -> dict[tuple[str, ...], tuple[str, ...]]:
    if frame.duplicated(list(KEY), keep=False).any():
        raise RuntimeError("append-only source continuity: prior outcome identity duplicated")
    evidence: dict[tuple[str, ...], tuple[str, ...]] = {}
    for _, row in frame.iterrows():
        key = tuple(
            "<NULL>" if pd.isna(row.get(column)) else str(row.get(column))
            for column in KEY
        )
        values = tuple(
            "<NULL>" if pd.isna(row.get(column)) else str(row.get(column))
            for column in _SOURCE_EVIDENCE
        )
        evidence[key] = values
    return evidence


def _assert_append_only_source_continuity(
    prior: pd.DataFrame, fresh: pd.DataFrame
) -> None:
    prior_evidence = _source_evidence(prior)
    fresh_evidence = _source_evidence(fresh)
    missing = set(prior_evidence) - set(fresh_evidence)
    revised = {
        key for key in set(prior_evidence) & set(fresh_evidence)
        if prior_evidence[key] != fresh_evidence[key]
    }
    if missing or revised:
        raise RuntimeError(
            "append-only source continuity violated: "
            f"missing_identities={len(missing)} revised_identities={len(revised)}"
        )


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
    if discovery.duplicated(list(_SOURCE_KEY), keep=False).any():
        raise ValueError(f"{m} discovery source contains duplicate observation identity")

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


def _catastrophic_summary(frame: pd.DataFrame) -> dict[str, Any]:
    column = f"fwd_ret_{_CATASTROPHIC_HORIZON}"
    values = (
        pd.to_numeric(frame[column], errors="coerce")
        if column in frame.columns else pd.Series(dtype=float)
    )
    valid = values.notna() & np.isfinite(values)
    matured = values[valid]
    n = int(len(matured))
    n_catastrophic = int((matured <= _CATASTROPHIC_RETURN).sum())
    return {
        "definition": "fwd_ret_21<=-0.15",
        "horizon": _CATASTROPHIC_HORIZON,
        "threshold": _CATASTROPHIC_RETURN,
        "n_matured": n,
        "n_catastrophic": n_catastrophic,
        "rate": (float(n_catastrophic / n) if n else None),
    }


def _summary_core(frame: pd.DataFrame) -> dict[str, Any]:
    """Canonical measured metrics for one observation cohort."""
    n = int(len(frame))
    states = (
        frame["outcome_state"].fillna("UNKNOWN").astype(str)
        if "outcome_state" in frame.columns else pd.Series(dtype=object)
    )
    unavailable = int((states == UNAVAILABLE_PRICE).sum()) if n else 0
    if "benchmark_available" in frame.columns:
        benchmark_available = int(
            frame["benchmark_available"].fillna(False).astype(bool).sum()
        )
        benchmark_coverage_rate = (
            float(benchmark_available / n) if n else None
        )
    else:
        benchmark_available = None
        benchmark_coverage_rate = None
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
        "n_benchmark_available": benchmark_available,
        "benchmark_coverage_rate": benchmark_coverage_rate,
        "horizons": horizons,
        "terminal_states": {
            "clean8_21": _terminal_summary(
                frame, "terminal_state_clean8_21"
            ),
            "clean15_126": _terminal_summary(
                frame, "terminal_state_clean15_126"
            ),
        },
        "catastrophic_outcome_21d": _catastrophic_summary(frame),
    }


def summarize_outcomes(frame: pd.DataFrame) -> dict[str, Any]:
    """Measured discovery quality, including descriptive source strata.

    Origin-token cohorts overlap by construction and are NEVER a rank/promotion
    plane. Eventual-winner/first-surface metrics remain absent until their complete
    owner-universe population is lawfully available.
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


def summarize_maturity_reasons(
    market: str,
    frame: pd.DataFrame,
) -> dict[str, Any]:
    """Explain outcome maturity without changing canonical outcome rows.

    ``SUSPENDED`` is the shared board-ledger predicate, not proof of an exchange
    halt. This reporting seam uses the native market benchmark only to tell
    whether enough market sessions have elapsed to evaluate that predicate. It
    never changes a stored outcome, price, fill, rank, entry gate, or authority.
    """
    m = str(market or "").upper()
    if m not in MARKETS:
        raise ValueError(f"unsupported market {market!r}")

    counts = {
        "fully_matured": 0,
        "horizon_accruing": 0,
        "insufficient_followup": 0,
        "short_name_history_after_market_mature": 0,
        "canonical_suspension_not_reproduced": 0,
        "followup_clock_unavailable": 0,
        "no_next_bar_observed": 0,
        "missing_price_store": 0,
        "unknown_state": 0,
    }
    if frame is None or frame.empty:
        return {
            "semantics": "derived_reporting_only_no_grade_authority",
            "canonical_suspended_semantics": (
                "shared_board_ledger_predicate_not_exchange_halt_proof"
            ),
            "confirmed_exchange_suspension_evidence": "NOT_EVALUATED",
            "counts": counts,
        }

    bench = board_ledger._bench_close(m)
    cache: dict = {}
    min_followup = int(board_ledger.SUSPENSION_SESSIONS)
    for _, row in frame.iterrows():
        state = str(row.get("outcome_state") or "UNKNOWN")
        if state == MATURED:
            counts["fully_matured"] += 1
            continue
        if state == ACCRUING:
            counts["horizon_accruing"] += 1
            continue
        if state == NO_FILL:
            counts["no_next_bar_observed"] += 1
            continue
        if state == UNAVAILABLE_PRICE:
            counts["missing_price_store"] += 1
            continue
        if state != SUSPENDED:
            counts["unknown_state"] += 1
            continue

        fill = pd.to_datetime(row.get("fill_date"), errors="coerce")
        ticker = str(row.get("security_ref") or "")
        close = board_ledger._name_close(m, ticker, ca_cache=cache)
        if pd.isna(fill) or bench is None or bench.empty or close is None or close.empty:
            counts["followup_clock_unavailable"] += 1
            continue

        # A short benchmark file is not evidence of ordinary right-censoring.
        # Both native clocks must contain the observed fill, and the benchmark
        # must cover the name's observed sessions before counting follow-up.
        # This proves relative clock consistency only, not absolute freshness.
        clocks = (bench.index, close.index)
        if any(
            not isinstance(index, pd.DatetimeIndex)
            or index.hasnans
            or not index.is_unique
            or not index.is_monotonic_increasing
            for index in clocks
        ):
            counts["followup_clock_unavailable"] += 1
            continue
        try:
            coherent = (
                fill in bench.index
                and fill in close.index
                and bench.index[-1] >= close.index[-1]
                and close.index[close.index >= fill].isin(bench.index).all()
            )
            if not coherent:
                counts["followup_clock_unavailable"] += 1
                continue
            market_after = int((bench.index > fill).sum())
            name_after = int((close.index > fill).sum())
        except (TypeError, ValueError):
            # Incomparable native timestamps stay unknown; never normalize them
            # into an invented common calendar or silently rewrite stored rows.
            counts["followup_clock_unavailable"] += 1
            continue
        if market_after < min_followup:
            counts["insufficient_followup"] += 1
            continue
        if name_after < min_followup:
            counts["short_name_history_after_market_mature"] += 1
        else:
            counts["canonical_suspension_not_reproduced"] += 1

    return {
        "semantics": "derived_reporting_only_no_grade_authority",
        "canonical_suspended_semantics": (
            "shared_board_ledger_predicate_not_exchange_halt_proof"
        ),
        "confirmed_exchange_suspension_evidence": "NOT_EVALUATED",
        "minimum_followup_sessions": min_followup,
        "counts": counts,
    }


def _bridge_unavailable(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "metric_semantics": "board_admission_not_eventual_winner",
        **_HISTORY_LIMITS,
    }


def summarize_board_admission_bridge(
    discovery: pd.DataFrame,
    board: pd.DataFrame | None,
) -> dict[str, Any]:
    """Describe whether discovery surfaced names before first board admission.

    This is NOT eventual-winner recall.  It answers one narrower, mechanically
    owned question: within the actual discovery-history window, how often did a
    ticker appear in Lane B before (or on) the date of its first canonical board
    admission?  Calendar lead time is reported only for strictly-prior surfaces.
    """
    if board is None:
        return _bridge_unavailable("board_store_absent")
    if discovery is None or discovery.empty:
        return _bridge_unavailable("discovery_store_empty")
    if board.empty:
        return _bridge_unavailable("board_store_empty")
    if "session_date" not in discovery.columns:
        return _bridge_unavailable("discovery_missing_session_date")
    identity_col = (
        "security_ref" if "security_ref" in discovery.columns
        else "security_ref_raw" if "security_ref_raw" in discovery.columns
        else None
    )
    if identity_col is None:
        return _bridge_unavailable("discovery_missing_identity")
    if "date" not in board.columns or "ticker" not in board.columns:
        return _bridge_unavailable("board_missing_identity")

    disc = discovery[[identity_col, "session_date"]].copy()
    disc = disc[disc[identity_col].notna()].copy()
    disc["_session"] = pd.to_datetime(disc["session_date"], errors="coerce")
    disc = disc[disc["_session"].notna()].copy()
    if disc.empty:
        return _bridge_unavailable("discovery_dates_unusable")
    disc["_ticker"] = disc[identity_col].astype(str)

    start = pd.Timestamp(disc["_session"].min()).normalize()
    end = pd.Timestamp(disc["_session"].max()).normalize()

    brd = board[["date", "ticker"]].copy()
    brd = brd[brd["ticker"].notna()].copy()
    brd["_date"] = pd.to_datetime(brd["date"], errors="coerce")
    brd = brd[brd["_date"].notna()].copy()
    brd["_date"] = brd["_date"].map(lambda x: pd.Timestamp(x).normalize())
    brd["_ticker"] = brd["ticker"].astype(str)
    brd = brd.sort_values(["_date", "_ticker"], kind="stable")
    brd = brd.drop_duplicates(subset=["_date", "_ticker"], keep="first")

    # Find the first positive record in the available canonical ledger before
    # applying the discovery window. Otherwise a name positively recorded
    # pre-window can be falsely relabeled as a new in-window admission when it
    # appears again. This still does not prove first-ever admission because the
    # historical ledger itself is incomplete; _HISTORY_LIMITS carries that
    # qualification into the receipt.
    first_observed_board = brd.drop_duplicates(subset=["_ticker"], keep="first")
    pre_window = first_observed_board[first_observed_board["_date"] < start]
    first_board = first_observed_board[
        (first_observed_board["_date"] >= start)
        & (first_observed_board["_date"] <= end)
    ].copy()

    first_disc = (
        disc.groupby("_ticker", sort=False)["_session"].min()
        .map(lambda x: pd.Timestamp(x).normalize())
        .to_dict()
    )

    prior = same_day = never = later_only = 0
    leads: list[int] = []
    for _, row in first_board.iterrows():
        ticker = row["_ticker"]
        admitted = pd.Timestamp(row["_date"]).normalize()
        first = first_disc.get(ticker)
        if first is None:
            never += 1
            continue
        if first < admitted:
            prior += 1
            leads.append(int((admitted - first).days))
        elif first == admitted:
            same_day += 1
        else:
            later_only += 1

    n = int(len(first_board))
    lead_series = pd.Series(leads, dtype=float)
    lead_summary = {
        "n": int(len(leads)),
        "median": float(lead_series.median()) if not lead_series.empty else None,
        "p25": float(lead_series.quantile(0.25)) if not lead_series.empty else None,
        "p75": float(lead_series.quantile(0.75)) if not lead_series.empty else None,
    }
    return {
        "available": True,
        "metric_semantics": "board_admission_not_eventual_winner",
        "window": {"from": str(start.date()), "to": str(end.date())},
        "first_admission_basis": "first_positive_board_record_in_available_ledger",
        "n_pre_window_positive_board_records_excluded": int(len(pre_window)),
        "n_first_board_admissions": n,
        "n_prior_discovered": int(prior),
        "n_same_day_only": int(same_day),
        "n_never_discovered": int(never),
        "n_discovered_only_after_admission": int(later_only),
        "n_no_pre_admission_surface": int(never + later_only),
        "prior_discovery_recall_rate": (float(prior / n) if n else None),
        "prior_or_same_day_surface_rate": (
            float((prior + same_day) / n) if n else None
        ),
        "calendar_lead_days": lead_summary,
        **_HISTORY_LIMITS,
    }


_RANK_RACE_SEMANTICS = "same_population_same_outcomes_shadow_rank_race"


def _rank_race_unavailable(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "metric_semantics": _RANK_RACE_SEMANTICS,
    }


def _rank_ic_summary(values: list[float], horizon: int) -> dict[str, Any]:
    return validation.ic_summary(
        values,
        periods_per_year=252,
        hac_lags=int(horizon),
    )


def _top_k_regret_summary(merged: pd.DataFrame) -> dict[str, Any]:
    outcome_col = f"excess_ret_{_TOP_K_REGRET_HORIZON}"

    def summarize(rule: str) -> dict[str, Any]:
        incumbent_regret: list[float] = []
        challenger_regret: list[float] = []
        ks: list[int] = []
        if outcome_col not in merged.columns:
            day_groups = ()
        else:
            day_groups = merged.groupby("_date", sort=True)
        for _date, day in day_groups:
            inc = pd.to_numeric(day["incumbent_rank"], errors="coerce")
            chal = pd.to_numeric(day["challenger_rank"], errors="coerce")
            y = pd.to_numeric(day[outcome_col], errors="coerce")
            mask = (
                inc.notna() & chal.notna() & y.notna()
                & np.isfinite(inc) & np.isfinite(chal) & np.isfinite(y)
            )
            if not bool(mask.any()):
                continue
            eligible = pd.DataFrame({
                "_ticker": day.loc[mask, "_ticker"].astype(str),
                "incumbent_rank": inc[mask].astype(float),
                "challenger_rank": chal[mask].astype(float),
                "outcome": y[mask].astype(float),
            })
            n = int(len(eligible))
            if rule == "1":
                k = 1
            elif rule == "5":
                if n < 5:
                    continue
                k = 5
            else:
                k = max(1, int(np.ceil(0.10 * n)))
            oracle = eligible.sort_values(
                ["outcome", "_ticker"], ascending=[False, True], kind="stable"
            ).head(k)["outcome"].mean()
            inc_mean = eligible.sort_values(
                ["incumbent_rank", "_ticker"], ascending=[True, True], kind="stable"
            ).head(k)["outcome"].mean()
            chal_mean = eligible.sort_values(
                ["challenger_rank", "_ticker"], ascending=[True, True], kind="stable"
            ).head(k)["outcome"].mean()
            incumbent_regret.append(float(oracle - inc_mean))
            challenger_regret.append(float(oracle - chal_mean))
            ks.append(k)

        return {
            "n_dates": int(len(ks)),
            "k_min": int(min(ks)) if ks else None,
            "k_max": int(max(ks)) if ks else None,
            "incumbent_mean_regret": (
                float(np.mean(incumbent_regret)) if incumbent_regret else None
            ),
            "incumbent_median_regret": (
                float(np.median(incumbent_regret)) if incumbent_regret else None
            ),
            "challenger_mean_regret": (
                float(np.mean(challenger_regret)) if challenger_regret else None
            ),
            "challenger_median_regret": (
                float(np.median(challenger_regret)) if challenger_regret else None
            ),
        }

    return {
        "definition": "oracle_mean_excess_21-minus-arm_topk_mean_excess_21",
        "horizon": _TOP_K_REGRET_HORIZON,
        "population": "same_joined_challenger_covered_names",
        "1": summarize("1"),
        "5": summarize("5"),
        "top_decile": summarize("top_decile"),
    }


def summarize_rank_races(
    rank_pairs: pd.DataFrame | None,
    outcomes: pd.DataFrame | None,
) -> dict[str, Any]:
    """Evaluate Lane-A rankers on identical covered names and outcomes.

    Rank 1 is best, so the signal passed to canonical rank_ic is negative rank.
    For every date/challenger/horizon the incumbent IC is computed on the exact
    subset that challenger could rank. Coverage is reported separately; a thin
    challenger can never make the incumbent look stronger by comparing against
    a larger name set. This is zero-authority measurement only.
    """
    if rank_pairs is None:
        return _rank_race_unavailable("rank_pair_store_absent")
    if rank_pairs.empty:
        return _rank_race_unavailable("rank_pair_store_empty")
    if outcomes is None:
        return _rank_race_unavailable("rank_outcomes_absent")

    required = {
        "date", "ticker", "challenger_definition",
        "incumbent_rank", "challenger_rank",
        "challenger_rank_domain", "challenger_coverage",
        "population_n", "challenger_offlist_n",
    }
    if missing := sorted(required - set(rank_pairs.columns)):
        return _rank_race_unavailable(
            "rank_pair_missing_columns:" + ",".join(missing)
        )
    outcome_required = {"session_date", "security_ref"}
    if missing := sorted(outcome_required - set(outcomes.columns)):
        return _rank_race_unavailable(
            "rank_outcome_missing_columns:" + ",".join(missing)
        )

    pairs = rank_pairs.copy()
    pairs["_date"] = pairs["date"].astype(str)
    pairs["_ticker"] = pairs["ticker"].astype(str)
    pairs["_definition"] = pairs["challenger_definition"].astype(str)

    if not (pairs["challenger_rank_domain"].astype(str) == "minted_population").all():
        return _rank_race_unavailable("rank_pair_population_contract_violation")
    if pairs.duplicated(["_date", "_ticker", "_definition"]).any():
        return _rank_race_unavailable("rank_pair_population_contract_violation")

    for (_date, _definition), group in pairs.groupby(
        ["_date", "_definition"], sort=False
    ):
        population_values = pd.to_numeric(
            group["population_n"], errors="coerce"
        )
        if (
            bool(population_values.isna().any())
            or not bool(np.isfinite(population_values).all())
            or population_values.nunique(dropna=False) != 1
        ):
            return _rank_race_unavailable(
                "rank_pair_population_contract_violation"
            )
        population_n = float(population_values.iloc[0])
        if (
            population_n != int(population_n)
            or int(population_n) != len(group)
        ):
            return _rank_race_unavailable(
                "rank_pair_population_contract_violation"
            )

        for column, allow_missing in (
            ("incumbent_rank", False),
            ("challenger_rank", True),
        ):
            supplied = group[column].notna()
            numeric = pd.to_numeric(group[column], errors="coerce")
            invalid = supplied & (
                numeric.isna()
                | ~np.isfinite(numeric)
                | (numeric <= 0)
                | (numeric != np.floor(numeric))
            )
            if (not allow_missing and not bool(supplied.all())) or bool(invalid.any()):
                return _rank_race_unavailable(
                    "rank_pair_population_contract_violation"
                )

        offlist = pd.to_numeric(
            group["challenger_offlist_n"], errors="coerce"
        )
        if (
            bool(offlist.isna().any())
            or not bool(np.isfinite(offlist).all())
            or bool((offlist < 0).any())
            or bool((offlist != np.floor(offlist)).any())
            or offlist.nunique(dropna=False) != 1
        ):
            return _rank_race_unavailable(
                "rank_pair_population_contract_violation"
            )

        coverage = pd.to_numeric(
            group["challenger_coverage"], errors="coerce"
        )
        observed_cov = float(
            pd.to_numeric(group["challenger_rank"], errors="coerce").notna().sum()
            / len(group)
        )
        if (
            bool(coverage.isna().any())
            or not bool(np.isfinite(coverage).all())
            or bool(((coverage < 0) | (coverage > 1)).any())
            or coverage.nunique(dropna=False) != 1
            or abs(float(coverage.iloc[0]) - observed_cov) > 1e-6
        ):
            return _rank_race_unavailable(
                "rank_pair_population_contract_violation"
            )

    graded = outcomes.copy()
    graded["_date"] = graded["session_date"].astype(str)
    graded["_ticker"] = graded["security_ref"].astype(str)
    graded = graded.drop_duplicates(["_date", "_ticker"], keep="first")

    challengers: dict[str, dict[str, Any]] = {}
    for definition in sorted(pairs["_definition"].unique()):
        sub = pairs[pairs["_definition"] == definition].copy()
        merged = sub.merge(
            graded,
            on=["_date", "_ticker"],
            how="left",
            suffixes=("", "_outcome"),
            validate="many_to_one",
        )
        challenger_rank = pd.to_numeric(
            merged["challenger_rank"], errors="coerce"
        )
        n_population = int(len(merged))
        n_ranked = int(challenger_rank.notna().sum())
        stored_cov = pd.to_numeric(
            merged["challenger_coverage"], errors="coerce"
        ).dropna()
        offlist = pd.to_numeric(
            merged["challenger_offlist_n"], errors="coerce"
        ).dropna()

        horizon_rows: dict[str, dict[str, Any]] = {}
        for horizon in HORIZONS:
            outcome_col = f"excess_ret_{horizon}"
            incumbent_ics: list[float] = []
            challenger_ics: list[float] = []
            deltas: list[float] = []
            if outcome_col in merged.columns:
                for _date, day in merged.groupby("_date", sort=True):
                    inc = pd.to_numeric(day["incumbent_rank"], errors="coerce")
                    chal = pd.to_numeric(day["challenger_rank"], errors="coerce")
                    y = pd.to_numeric(day[outcome_col], errors="coerce")
                    mask = (
                        inc.notna() & chal.notna() & y.notna()
                        & np.isfinite(inc) & np.isfinite(chal) & np.isfinite(y)
                    )
                    if not bool(mask.any()):
                        continue
                    inc_ic = validation.rank_ic(-inc[mask], y[mask])
                    chal_ic = validation.rank_ic(-chal[mask], y[mask])
                    if np.isfinite(inc_ic) and np.isfinite(chal_ic):
                        incumbent_ics.append(float(inc_ic))
                        challenger_ics.append(float(chal_ic))
                        deltas.append(float(chal_ic - inc_ic))
            horizon_summary = {
                "n_paired_dates": int(len(deltas)),
                "incumbent_rank_ic": _rank_ic_summary(
                    incumbent_ics, horizon
                ),
                "challenger_rank_ic": _rank_ic_summary(
                    challenger_ics, horizon
                ),
                "challenger_minus_incumbent_ic": _rank_ic_summary(
                    deltas, horizon
                ),
            }
            if horizon == _TOP_K_REGRET_HORIZON:
                horizon_summary["top_k_regret"] = _top_k_regret_summary(merged)
            horizon_rows[f"{horizon}d"] = horizon_summary

        challengers[definition] = {
            "n_population_rows": n_population,
            "n_ranked_rows": n_ranked,
            "n_dates": int(sub["_date"].nunique()),
            "observed_coverage_rate": (
                float(n_ranked / n_population) if n_population else None
            ),
            "stored_coverage_min": (
                float(stored_cov.min()) if not stored_cov.empty else None
            ),
            "stored_coverage_max": (
                float(stored_cov.max()) if not stored_cov.empty else None
            ),
            "challenger_offlist_n_max": (
                int(offlist.max()) if not offlist.empty else None
            ),
            "horizons": horizon_rows,
        }

    return {
        "available": True,
        "metric_semantics": _RANK_RACE_SEMANTICS,
        "challengers": challengers,
    }


def evaluate_rank_races(market: str) -> dict[str, Any]:
    """Read Lane A and grade its unique population with the canonical spine."""
    m = str(market or "").upper()
    if m not in MARKETS:
        raise ValueError(f"unsupported market {market!r}")
    path = board_shadow._lane_a_path(m)
    if not path.exists():
        return _rank_race_unavailable("rank_pair_store_absent")
    try:
        pairs = pd.read_parquet(path)
    except Exception as exc:
        return _rank_race_unavailable(
            f"rank_pair_store_unreadable:{type(exc).__name__}"
        )
    if pairs.empty:
        return _rank_race_unavailable("rank_pair_store_empty")
    if "market" in pairs.columns:
        foreign = {
            str(value).upper()
            for value in pairs["market"].dropna().unique()
            if str(value).upper() != m
        }
        if foreign:
            return _rank_race_unavailable("rank_pair_store_foreign_market")

    population = (
        pairs[["date", "ticker"]]
        .dropna()
        .drop_duplicates()
        .sort_values(["date", "ticker"], kind="stable")
        .reset_index(drop=True)
    )
    source = pd.DataFrame({
        "session_date": population["date"].astype(str),
        "market": m,
        "security_ref": population["ticker"].astype(str),
        "security_ref_raw": population["ticker"].astype(str),
        "challenger_definition": "rank_pair_outcome_v1",
    })
    outcomes = grade_frame(m, source)
    return summarize_rank_races(pairs, outcomes)


def _discovery_source_receipt(market: str) -> dict[str, Any]:
    m = str(market or "").upper()
    path = board_shadow._discovery_receipt_path(m)
    artifact = f"{board_shadow.STORE_DIR}/{m.lower()}_discovery_receipt.json"
    if not path.exists():
        return {
            "artifact": artifact,
            "available": False,
            "healthy": False,
            "reason": "receipt_absent",
            "as_of": None,
            "registry_state": None,
            "definitions": [],
            "challenger_failures": [],
            "stamped_at": None,
        }
    try:
        payload = json.loads(path.read_text())
    except Exception as exc:
        return {
            "artifact": artifact,
            "available": False,
            "healthy": False,
            "reason": f"receipt_unreadable:{type(exc).__name__}",
            "as_of": None,
            "registry_state": None,
            "definitions": [],
            "challenger_failures": [],
            "stamped_at": None,
        }
    if not isinstance(payload, dict):
        return {
            "artifact": artifact,
            "available": False,
            "healthy": False,
            "reason": "receipt_not_mapping",
            "as_of": None,
            "registry_state": None,
            "definitions": [],
            "challenger_failures": [],
            "stamped_at": None,
        }

    raw_asof = payload.get("as_of")
    try:
        as_of = (
            str(pd.Timestamp(raw_asof).date())
            if raw_asof not in (None, "") else None
        )
    except Exception:
        as_of = None
    registry_state = (
        str(payload.get("registry_state"))
        if payload.get("registry_state") not in (None, "") else None
    )
    definitions_raw = payload.get("definitions")
    failures_raw = payload.get("challenger_failures")
    definitions = (
        [str(value) for value in definitions_raw]
        if isinstance(definitions_raw, list) else []
    )
    challenger_failures = (
        list(failures_raw) if isinstance(failures_raw, list) else []
    )

    reason = None
    if str(payload.get("market") or "").upper() != m:
        reason = "market_mismatch"
    elif as_of is None:
        reason = "receipt_missing_asof"
    elif not isinstance(definitions_raw, list):
        reason = "receipt_invalid_definitions"
    elif not isinstance(failures_raw, list):
        reason = "receipt_invalid_failures"
    elif not (registry_state or "").startswith("wrote_n_rows n="):
        reason = "registry_not_successful"
    elif challenger_failures:
        reason = "challenger_failures"

    return {
        "artifact": artifact,
        "available": True,
        "healthy": reason is None,
        "reason": reason,
        "as_of": as_of,
        "registry_state": registry_state,
        "definitions": definitions,
        "challenger_failures": challenger_failures,
        "stamped_at": payload.get("stamped_at"),
    }


def _require_source_receipt_asof(
    market: str,
    receipt: dict[str, Any],
    expected_source_asof: str,
) -> str:
    try:
        expected = str(pd.Timestamp(expected_source_asof).date())
    except Exception as exc:
        raise ValueError(
            f"invalid expected source as_of {expected_source_asof!r}"
        ) from exc
    if not receipt.get("available"):
        raise RuntimeError(
            f"{market} source receipt unavailable: {receipt.get('reason')}"
        )
    if receipt.get("as_of") != expected:
        raise RuntimeError(
            f"{market} source receipt as_of mismatch: "
            f"expected {expected}, observed {receipt.get('as_of')}"
        )
    if not receipt.get("healthy"):
        raise RuntimeError(
            f"{market} source receipt unhealthy: {receipt.get('reason')}"
        )
    return expected


def grade_market(
    market: str,
    *,
    expected_source_asof: str | None = None,
) -> dict[str, Any]:
    """Refresh one market's derived outcome store from its append-only discovery source."""
    m = str(market or "").upper()
    if m not in MARKETS:
        raise ValueError(f"unsupported market {market!r}")
    if not ledger_lane.nightly_advance_enabled():
        raise RuntimeError(
            f"{m} discovery outcome write refused: nightly ledger lane not armed"
        )
    source_receipt = _discovery_source_receipt(m)
    if expected_source_asof is not None:
        _require_source_receipt_asof(m, source_receipt, expected_source_asof)
    source_path = board_shadow._lane_b_path(m)
    out_path = _outcome_path(m)
    source_artifact = f"{board_shadow.STORE_DIR}/{m.lower()}_discovery.parquet"
    output_artifact = (
        f"{board_shadow.STORE_DIR}/{m.lower()}_discovery_outcomes.parquet"
    )
    if not source_path.exists():
        return {
            "market": m, "available": False, "state": "SOURCE_ABSENT",
            "n_source": 0, "n_rows": 0,
            "source_artifact": source_artifact,
            "output_artifact": output_artifact,
            "source_cutoff": None,
            "source_session_count": 0,
            "source_identity_digest": None,
            "outcome_identity_digest": None,
            "identity_parity": None,
            "source_cohort_digest": None,
            "outcome_cohort_digest": None,
            "cohort_parity": None,
            "source_contract": "lane_b_append_only_keep_first",
            "source_receipt": source_receipt,
        }
    try:
        source = pd.read_parquet(source_path)
    except Exception as exc:
        raise RuntimeError(f"{m} discovery source unreadable: {exc}") from exc
    fresh = grade_frame(m, source)
    source_identity_digest = _identity_digest(source)
    outcome_identity_digest = _identity_digest(fresh)
    identity_parity = (
        len(source) == len(fresh)
        and source_identity_digest == outcome_identity_digest
    )
    if not identity_parity:
        raise RuntimeError(f"{m} discovery outcome identity parity failed")
    source_cohort_digest = _cohort_digest(source)
    outcome_cohort_digest = _cohort_digest(fresh)
    cohort_parity = source_cohort_digest == outcome_cohort_digest
    if not cohort_parity:
        raise RuntimeError(f"{m} discovery outcome cohort parity failed")
    source_dates = source["session_date"].dropna().astype(str)
    source_cutoff = str(source_dates.max()) if len(source_dates) else None
    source_session_count = int(source_dates.nunique())
    board = board_shadow._read_board_parquet(m, ["date", "ticker"])
    board_admission_bridge = summarize_board_admission_bridge(source, board)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    changed = True
    if out_path.exists():
        try:
            prior = pd.read_parquet(out_path).reindex(columns=list(SCHEMA))
        except Exception as exc:
            raise RuntimeError(f"{m} prior outcome store unreadable: {exc}") from exc
        _assert_append_only_source_continuity(prior, fresh)
        changed = not _same_frame(prior, fresh)

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
        "source_artifact": source_artifact,
        "output_artifact": output_artifact,
        "source_cutoff": source_cutoff,
        "source_session_count": source_session_count,
        "source_identity_digest": source_identity_digest,
        "outcome_identity_digest": outcome_identity_digest,
        "identity_parity": identity_parity,
        "source_cohort_digest": source_cohort_digest,
        "outcome_cohort_digest": outcome_cohort_digest,
        "cohort_parity": cohort_parity,
        "source_contract": "lane_b_append_only_keep_first",
        "source_receipt": source_receipt,
        "terminal_clean8_21": terminal8,
        "terminal_clean15_126": terminal15,
        "candidate_metrics": summarize_outcomes(fresh),
        "maturity_reasons": summarize_maturity_reasons(m, fresh),
        "board_admission_bridge": board_admission_bridge,
        "rank_races": evaluate_rank_races(m),
    }


def grade_all() -> dict[str, dict[str, Any]]:
    """Grade both markets while preserving truthful per-market effects."""
    results: dict[str, dict[str, Any]] = {}
    for market in MARKETS:
        try:
            results[market] = grade_market(market)
        except Exception as exc:  # noqa: BLE001 — receipt must expose partial effects
            results[market] = {
                "market": market,
                "available": False,
                "state": "ERROR",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
    return results
