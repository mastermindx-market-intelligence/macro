from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import research_skylit_r2_exposure_decomposition as r2

SCHEMA = "skylit.r8.daily_position_change_evidence/v1"
KEY = list(r2.KEY)


class R8Refusal(ValueError):
    pass


def _default_store_api():
    from engine import thetadata_store
    return thetadata_store


def _default_calendar_api():
    from lib import nyse_calendar
    return nyse_calendar


def _normalize_source_identity(frame: pd.DataFrame, root: str, *, label: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=KEY)
    mask = r2._identity_valid_mask(frame, root)
    invalid = int((~mask).sum())
    if invalid:
        raise R8Refusal(
            f"{label} has malformed contract identity rows for {root.upper()}: "
            f"{invalid}/{len(frame)}"
        )
    try:
        return r2._normalize_identity(frame, root)
    except r2.R2Refusal as exc:
        raise R8Refusal(f"{label}: {exc}") from exc


def _integer_like(values: pd.Series, *, tol: float = 1e-9) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return np.isfinite(numeric) & (np.abs(numeric - np.round(numeric)) <= tol)


def _normalize_oi(frame: pd.DataFrame, root: str, *, label: str, value_name: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=KEY + [value_name])
    mask = r2._identity_valid_mask(frame, root)
    invalid_identity = int((~mask).sum())
    if invalid_identity:
        raise R8Refusal(
            f"{label} has malformed contract identity rows for {root.upper()}: "
            f"{invalid_identity}/{len(frame)}"
        )
    if "open_interest" not in frame.columns:
        raise R8Refusal(f"{label} is missing open_interest")
    boolean_oi = frame["open_interest"].map(lambda v: isinstance(v, (bool, np.bool_)))
    if bool(boolean_oi.any()):
        raise R8Refusal(
            f"{label} has Boolean option contract OI for {root.upper()}: "
            f"{int(boolean_oi.sum())}/{len(frame)}"
        )
    raw_oi = pd.to_numeric(frame["open_interest"], errors="coerce")
    noninteger = np.isfinite(raw_oi) & (raw_oi >= 0) & ~_integer_like(raw_oi)
    if bool(noninteger.any()):
        raise R8Refusal(
            f"{label} has non-integer option contract OI for {root.upper()}: "
            f"{int(noninteger.sum())}/{len(frame)}"
        )
    try:
        out = r2._normalize_identity(frame, root, require_oi=True)
    except r2.R2Refusal as exc:
        raise R8Refusal(f"{label}: {exc}") from exc
    return out[KEY + ["open_interest"]].rename(columns={"open_interest": value_name})


def _digest(frame: pd.DataFrame, columns: list[str]) -> str:
    return r2._digest_frame(frame, columns)


def _safe_fraction(num: float, den: float) -> float | None:
    if not np.isfinite(den) or den <= 0:
        return None
    return float(num / den)


def _cohort(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "contracts": 0,
            "volume": 0.0,
            "net_oi_increase": 0,
            "net_oi_decrease": 0,
            "net_oi_flat": 0,
            "sum_delta_oi": 0.0,
            "sum_abs_delta_oi": 0.0,
        }
    delta = frame["delta_oi"].to_numpy(float)
    return {
        "contracts": int(len(frame)),
        "volume": float(frame["volume"].sum()),
        "net_oi_increase": int(np.sum(delta > 0)),
        "net_oi_decrease": int(np.sum(delta < 0)),
        "net_oi_flat": int(np.sum(delta == 0)),
        "sum_delta_oi": float(np.sum(delta)),
        "sum_abs_delta_oi": float(np.sum(np.abs(delta))),
    }


def _build_evidence_frame(
    session: str,
    root: str,
    *,
    store: str | Path | None = None,
    store_api=None,
    calendar_api=None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    store_api = store_api or _default_store_api()
    calendar_api = calendar_api or _default_calendar_api()
    session_day = r2._canonical_session(session, calendar_api)
    settled_publication_session = r2._next_session(session, calendar_api)
    root = root.upper()

    if store is None:
        store = store_api.resolve_thetadata_store(required=True, purpose="skylit-r8-stage0")

    eod_raw = store_api.eod_matrix_for_date(session, root, store=store)
    if eod_raw is None or eod_raw.empty:
        raise R8Refusal(f"no EOD volume board for {root} {session}")
    eod = _normalize_source_identity(eod_raw, root, label="EOD")
    if "volume" not in eod.columns:
        raise R8Refusal(f"EOD board missing volume for {root} {session}")
    boolean_volume = eod["volume"].map(lambda v: isinstance(v, (bool, np.bool_)))
    if bool(boolean_volume.any()):
        raise R8Refusal(
            f"EOD board has Boolean option contract volume for {root} {session}: "
            f"{int(boolean_volume.sum())}/{len(eod)}"
        )
    eod["volume"] = pd.to_numeric(eod["volume"], errors="coerce")
    noninteger_volume = (
        np.isfinite(eod["volume"])
        & (eod["volume"] >= 0)
        & ~_integer_like(eod["volume"])
    )
    if bool(noninteger_volume.any()):
        raise R8Refusal(
            f"EOD board has non-integer option contract volume for {root} {session}: "
            f"{int(noninteger_volume.sum())}/{len(eod)}"
        )

    prior_raw = store_api.oi_for_date(session, root, store=store)
    later_raw = store_api.oi_for_date(settled_publication_session, root, store=store)
    prior = _normalize_oi(
        prior_raw, root, label="prior OI", value_name="prior_open_interest"
    )
    later = _normalize_oi(
        later_raw, root, label="settled OI", value_name="settled_open_interest"
    )

    board = eod.merge(prior, on=KEY, how="left", validate="one_to_one")
    board = board.merge(later, on=KEY, how="left", validate="one_to_one")
    expiry = pd.to_datetime(board["expiration"], errors="coerce").dt.date
    board["eligible_later_oi"] = expiry > session_day
    board["volume_valid"] = np.isfinite(board["volume"]) & (board["volume"] >= 0)
    board["prior_oi_known"] = (
        np.isfinite(board["prior_open_interest"])
        & (board["prior_open_interest"] >= 0)
    )
    board["settled_oi_known"] = (
        np.isfinite(board["settled_open_interest"])
        & (board["settled_open_interest"] >= 0)
    )
    board["fully_matched"] = (
        board["eligible_later_oi"]
        & board["volume_valid"]
        & board["prior_oi_known"]
        & board["settled_oi_known"]
    )

    board["delta_oi"] = np.nan
    matched = board["fully_matched"]
    board.loc[matched, "delta_oi"] = (
        board.loc[matched, "settled_open_interest"]
        - board.loc[matched, "prior_open_interest"]
    )
    board["turnover_ratio"] = np.nan
    positive_prior = matched & (board["prior_open_interest"] > 0)
    board.loc[positive_prior, "turnover_ratio"] = (
        board.loc[positive_prior, "volume"]
        / board.loc[positive_prior, "prior_open_interest"]
    )
    board["high_turnover"] = positive_prior & (
        board["volume"] > board["prior_open_interest"]
    )
    board["zero_prior_oi"] = matched & (board["prior_open_interest"] == 0)

    board["trade_conservation_compatible"] = False
    delta_abs = np.abs(board["delta_oi"])
    board.loc[matched, "trade_conservation_compatible"] = (
        delta_abs.loc[matched] <= board.loc[matched, "volume"] + 1e-9
    )

    consistent = matched & board["trade_conservation_compatible"]
    delta = board["delta_oi"]
    volume = board["volume"]
    board["min_open_open_volume"] = np.nan
    board["max_open_open_volume"] = np.nan
    board["min_close_close_volume"] = np.nan
    board["max_close_close_volume"] = np.nan
    board["max_mixed_open_close_volume"] = np.nan
    board.loc[consistent, "min_open_open_volume"] = np.maximum(delta.loc[consistent], 0.0)
    board.loc[consistent, "min_close_close_volume"] = np.maximum(-delta.loc[consistent], 0.0)
    # V, OI and deltaOI are whole-contract counts.  The continuous algebraic
    # upper bounds (V +/- delta)/2 can be half-integral (e.g. V=1, delta=0),
    # but a half contract is not a feasible transaction count.  Floor the
    # maxima to the exact integer feasible set; the lower bounds are already
    # integral because deltaOI is integral.
    board.loc[consistent, "max_open_open_volume"] = np.floor(
        (volume.loc[consistent] + delta.loc[consistent]) / 2.0
    )
    board.loc[consistent, "max_close_close_volume"] = np.floor(
        (volume.loc[consistent] - delta.loc[consistent]) / 2.0
    )
    board.loc[consistent, "max_mixed_open_close_volume"] = (
        volume.loc[consistent] - np.abs(delta.loc[consistent])
    )

    volume_digest_frame = board[KEY + ["volume"]].copy()
    prior_digest_frame = board[board["prior_oi_known"]][KEY + ["prior_open_interest"]].copy()
    later_digest_frame = board[board["settled_oi_known"]][KEY + ["settled_open_interest"]].copy()

    prior_effective_session = calendar_api.session_n_back(session_day, 1)
    if prior_effective_session is None:
        raise R8Refusal(f"calendar cannot resolve prior session before {session}")

    receipt = {
        "root": root,
        "session": session,
        "prior_oi_publication_session": session,
        "prior_position_effective_through_session": prior_effective_session.isoformat(),
        "settled_oi_publication_session": settled_publication_session,
        "settled_position_effective_through_session": session,
        "decision_eligible_not_before_session": settled_publication_session,
        "volume_input_sha256": _digest(volume_digest_frame, KEY + ["volume"]),
        "prior_oi_input_sha256": _digest(
            prior_digest_frame, KEY + ["prior_open_interest"]
        ),
        "settled_oi_input_sha256": _digest(
            later_digest_frame, KEY + ["settled_open_interest"]
        ),
    }
    return board, receipt


def analyze_session(
    session: str,
    root: str,
    *,
    store: str | Path | None = None,
    store_api=None,
    calendar_api=None,
) -> dict[str, Any]:
    board, receipt = _build_evidence_frame(
        session,
        root,
        store=store,
        store_api=store_api,
        calendar_api=calendar_api,
    )

    eligible = board[board["eligible_later_oi"]].copy()
    matched = eligible[eligible["fully_matched"]].copy()
    consistent = matched[matched["trade_conservation_compatible"]].copy()
    inconsistent = matched[~matched["trade_conservation_compatible"]].copy()
    high = matched[matched["high_turnover"]].copy()
    normal = matched[
        (matched["prior_open_interest"] > 0) & ~matched["high_turnover"]
    ].copy()
    zero_prior = matched[matched["zero_prior_oi"]].copy()

    total_consistent_volume = float(consistent["volume"].sum())
    min_open = float(consistent["min_open_open_volume"].sum())
    max_open = float(consistent["max_open_open_volume"].sum())
    min_close = float(consistent["min_close_close_volume"].sum())
    max_close = float(consistent["max_close_close_volume"].sum())
    max_mixed = float(consistent["max_mixed_open_close_volume"].sum())

    eligible_n = int(len(eligible))
    matched_n = int(len(matched))
    volume_valid_n = int(eligible["volume_valid"].sum())
    prior_known_n = int(eligible["prior_oi_known"].sum())
    settled_known_n = int(eligible["settled_oi_known"].sum())

    return {
        "schema": SCHEMA,
        "status": "DAILY_POSITION_EVIDENCE_COMPLETE",
        "research_authority": "research_only",
        "outcome_labels_opened": False,
        "later_position_evidence_opened": True,
        "root": root.upper(),
        "session": session,
        "source_receipt": receipt,
        "coverage": {
            "eod_contracts": int(len(board)),
            "same_session_expiry_contracts": int((~board["eligible_later_oi"]).sum()),
            "eligible_later_oi_contracts": eligible_n,
            "valid_volume_contracts": volume_valid_n,
            "prior_oi_known_contracts": prior_known_n,
            "settled_oi_known_contracts": settled_known_n,
            "fully_matched_contracts": matched_n,
            "trade_conservation_compatible_contracts": int(len(consistent)),
            "trade_conservation_incompatible_contracts": int(len(inconsistent)),
            "volume_contract_rate": _safe_fraction(volume_valid_n, eligible_n),
            "prior_oi_contract_rate": _safe_fraction(prior_known_n, eligible_n),
            "settled_oi_contract_rate": _safe_fraction(settled_known_n, eligible_n),
            "fully_matched_contract_rate": _safe_fraction(matched_n, eligible_n),
        },
        "cohorts": {
            "high_turnover_volume_gt_prior_oi": _cohort(high),
            "ordinary_turnover_volume_le_prior_oi": _cohort(normal),
            "known_zero_prior_oi": _cohort(zero_prior),
        },
        "conditional_trade_only_bounds": {
            "assumption": (
                "deltaOI = open_open_trade_volume - close_close_trade_volume; "
                "no exercise, assignment, corporate-action adjustment, correction, "
                "or other non-trade OI change"
            ),
            "trade_conservation_compatible_contracts_only": True,
            "whole_contract_integer_bounds": True,
            "total_volume": total_consistent_volume,
            "min_open_open_volume": min_open,
            "max_open_open_volume": max_open,
            "min_close_close_volume": min_close,
            "max_close_close_volume": max_close,
            "max_mixed_open_close_volume": max_mixed,
            "open_open_share_lower": _safe_fraction(min_open, total_consistent_volume),
            "open_open_share_upper": _safe_fraction(max_open, total_consistent_volume),
            "close_close_share_lower": _safe_fraction(min_close, total_consistent_volume),
            "close_close_share_upper": _safe_fraction(max_close, total_consistent_volume),
        },
        "identification_law": {
            "volume_div_prior_oi": (
                "turnover relative to prior settled OI; not transaction-level opening share"
            ),
            "delta_oi": (
                "later net change in outstanding OI; positive means net stock increased, "
                "not that every observed trade opened"
            ),
            "open_close_bounds": (
                "conditional whole-contract trade-only bounds under "
                "V=OO+CC+M and deltaOI=OO-CC; not identified when non-trade "
                "OI changes may have occurred"
            ),
            "institution_identity": "unknown_without_participant_type_source",
            "dealer_side": "unknown_from_daily_volume_and_oi_alone",
        },
        "limitations": [
            "same-session expirations are excluded from later-OI matching rather than treated as missing zero",
            "missing prior or later OI remains missing and is never zero-imputed",
            "contracts with abs(deltaOI) > volume violate the trade-only conservation baseline; this may reflect exercise/assignment, corporate actions, corrections, timing/identity issues, or other non-trade OI changes",
            "even when abs(deltaOI) <= volume, conditional trade-only bounds are not ground truth if non-trade OI changes occurred",
            "this Stage-0 object uses daily aggregate volume; it does not infer trade aggressor, sweep, package, institution or dealer identity",
            "no future underlying return, realized volatility, option PnL or trade outcome is read",
        ],
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Research-only R8 daily Volume/OI -> later position evidence audit"
    )
    p.add_argument("--session", required=True, help="Trading session YYYY-MM-DD")
    p.add_argument("--root", required=True)
    p.add_argument("--store", help="Optional canonical ThetaData store override")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = analyze_session(args.session, args.root, store=args.store)
    except (r2.R2Refusal, R8Refusal, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
