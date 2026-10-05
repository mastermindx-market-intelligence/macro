"""Read-only W3 post-floor statistical guardrail (measurement only).

Lawful surface after the frozen honest-N floor of 20 distinct matured H=10
paired sessions. Below the floor this prints accrual only — no IC, mean,
p-value, interval, leader, or hidden comparison.

Capture ownership: the persisted paired output written by the capture owners
is the registered capture owner. This reader never reconstructs, requalifies,
or re-runs the row constructor over it — it validates the stored grain exactly
as persisted. A stamp is admitted only when every row carries exactly
``source == candidates_store+grades_store`` and exactly
``benchmark == SPY`` (a missing/empty/null source and a null ``benchmark``
backed by a legacy ``bench`` column both refuse), and only when
``grain_fingerprint(stored frame)`` equals both the live observation record's
``paired_fingerprint`` and the session record's ``paired_fingerprint``.

ZERO AUTHORITY. No rank, gate, size, featured, plan, C2, reversion, promotion,
or AgentOS write. An adverse primary tripwire is a diagnostic label only.

Run:  python -m scripts.report_us_prophet_w3_guardrail --root PATH
Stdout is JSON only. ``--root`` is required. No output file is written.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import us_prophet_w3 as w3  # noqa: E402
from engine.validation import newey_west_tstat, rank_ic  # noqa: E402

SCHEMA_GUARDRAIL = "us.prophet_w3_guardrail/v1"
HAC_LAGS = 9
TOP_N = 30
MIN_NAMES = 2
PRIMARY_LABEL_NONCONFIRMATORY = "rank-IC adverse, top-30 not confirmatory"
PAIRED_SOURCE_CANONICAL = f"{w3.SOURCE_CANDIDATES}+{w3.SOURCE_GRADES}"
SESSION_FINGERPRINT_FIELDS = (
    "paired_fingerprint",
    "family_fingerprint",
    "coverage_fingerprint",
    "observation_fingerprint",
)
ACCRUAL_FORBIDDEN_TOKENS = (
    "IC_C1", "IC_shadow", "delta IC", "delta_ic", "ΔIC",
    "p-value", "pvalue", "p_value",
    "HAC", "confidence interval", "confidence_interval",
    "who is winning", "leader", "winner",
    "mean_delta", "ci95", "tripwire",
)


class GuardrailReadError(ValueError):
    """A selected stamp is not a lawful complete observation; the whole read refuses."""


def _authority_block() -> dict[str, Any]:
    return {
        "authority": False,
        "rank_authority": False,
        "gate_authority": False,
        "size_authority": False,
        "featured_authority": False,
        "plan_authority": False,
        "c2_trigger": False,
        "automatic_reversion": False,
        "promotion": False,
        "agentos_write": False,
    }


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _finite(value: Any) -> bool:
    return w3._is_finite_number(value)


def _is_race_liveness(rec: dict[str, Any]) -> bool:
    liveness = str(rec.get("liveness") or "")
    if liveness != w3.LIVENESS_PAIRED_ACCRUED:
        return False
    if liveness in w3.TERMINAL_LIVENESS:
        return False
    if _as_int(rec.get("n_pending_outcome")) != 0:
        return False
    n_paired = _as_int(rec.get("n_paired"))
    n_v3 = _as_int(rec.get("n_v3_buy_rows"))
    if n_paired is None or n_paired <= 0:
        return False
    if n_v3 is None or n_v3 <= 0:
        return False
    return True


def _session_metadata_ok(rec: dict[str, Any]) -> bool:
    if str(rec.get("schema") or "") != w3.SCHEMA_SESSION:
        return False
    if str(rec.get("structural_schema") or "") != w3.STRUCTURAL_SCHEMA:
        return False
    for field in SESSION_FINGERPRINT_FIELDS:
        if not str(rec.get(field) or "").strip():
            return False
    return True


def _accrual_counts(sessions: dict[str, dict[str, Any]],
                    selected: list[str]) -> dict[str, Any]:
    values = list(sessions.values())
    missing = sum(1 for rec in values if rec.get("liveness") == w3.LIVENESS_MISSING)
    degraded = sum(1 for rec in values if rec.get("liveness") == w3.LIVENESS_DEGRADED)
    unmatured = sum(1 for rec in values if rec.get("liveness") == w3.LIVENESS_UNMATURED)
    accrued = sum(1 for rec in values if rec.get("liveness") == w3.LIVENESS_PAIRED_ACCRUED)
    return {
        "honest_n_floor": w3.HONEST_N_FLOOR,
        "n_session_stamps": len(sessions),
        "paired_sessions_accrued": unmatured + accrued,
        "matured_h10_sessions": accrued,
        "unmatured_sessions": unmatured,
        "n_missing": missing,
        "n_degraded_or_unpaired": degraded,
        "n_selected_sessions": len(selected),
        "selected_stamps": list(selected),
    }


def _assert_accrual_only(payload: dict[str, Any]) -> None:
    # Free-text `refusal` may name a non-numeric diagnostic (e.g. HAC undefined).
    # Copy without it so the lexical scan still covers every structured
    # comparison-bearing field and cannot re-raise from the refusal prose.
    inspected = {key: value for key, value in payload.items() if key != "refusal"}
    text = json.dumps(inspected, default=str)
    lowered = text.lower()
    for token in ACCRUAL_FORBIDDEN_TOKENS:
        if token.lower() in lowered:
            raise GuardrailReadError(
                f"accrual-only surface refused forbidden comparison token {token!r}"
            )


def _base_doc(status: str, accrual: dict[str, Any], *,
              refusal: str | None = None) -> dict[str, Any]:
    payload = {
        "schema": SCHEMA_GUARDRAIL,
        "status": status,
        "measurement_only": True,
        **_authority_block(),
        "accrual": accrual,
        "horizon": w3.PRIMARY_HORIZON,
        "benchmark": w3.BENCH,
        "canonical_board": w3.CANONICAL_BOARD,
        "shadow_definition": w3.SHADOW_DEFINITION,
        "grader": "engine.us_prophet_grades.load_grades",
        "investigation_open": False,
        "investigation_label": None,
    }
    if refusal is not None:
        payload["refusal"] = refusal
    return payload


def _validate_paired_frame(stamp: str, frame: pd.DataFrame,
                           rec: dict[str, Any]) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise GuardrailReadError(f"stamp {stamp} paired grain is empty")
    n_paired = _as_int(rec.get("n_paired"))
    if n_paired is None or int(len(frame)) != n_paired:
        raise GuardrailReadError(
            f"stamp {stamp} paired row count {len(frame)} != session n_paired {n_paired}"
        )
    seen: set[tuple] = set()
    for raw in frame.to_dict(orient="records"):
        row_stamp = str(raw.get("stamp_date") or "")[:10]
        if row_stamp != stamp:
            raise GuardrailReadError(
                f"stamp {stamp} paired row carries stamp_date {row_stamp}")
        if str(raw.get("schema") or "") != w3.SCHEMA_PAIRED:
            raise GuardrailReadError(
                f"stamp {stamp} paired schema {raw.get('schema')!r} is not {w3.SCHEMA_PAIRED}"
            )
        if str(raw.get("board_definition") or "") != w3.CANONICAL_BOARD:
            raise GuardrailReadError(
                f"stamp {stamp} board_definition {raw.get('board_definition')!r}"
            )
        if str(raw.get("prophet_shadow_definition") or "") != w3.SHADOW_DEFINITION:
            raise GuardrailReadError(
                f"stamp {stamp} prophet_shadow_definition "
                f"{raw.get('prophet_shadow_definition')!r}"
            )
        horizon = _as_int(raw.get("horizon"))
        if horizon != w3.PRIMARY_HORIZON:
            raise GuardrailReadError(f"stamp {stamp} horizon {raw.get('horizon')!r}")
        bench = raw.get("benchmark")
        if str(bench or "") != w3.BENCH:
            raise GuardrailReadError(
                f"stamp {stamp} persisted benchmark {bench!r} is not {w3.BENCH} "
                "(legacy 'bench' fallback is not accepted)"
            )
        ticker = str(raw.get("ticker") or "")
        if not ticker:
            raise GuardrailReadError(f"stamp {stamp} paired row missing ticker")
        key = (row_stamp, ticker, horizon)
        if key in seen:
            raise GuardrailReadError(f"stamp {stamp} duplicate paired key {key}")
        seen.add(key)
        for col in ("prophet_score", "score_rank",
                    "prophet_shadow_score", "prophet_shadow_score_rank",
                    "excess_spy"):
            if not _finite(raw.get(col)):
                raise GuardrailReadError(
                    f"stamp {stamp} {ticker} non-finite {col}={raw.get(col)!r}"
                )
        stored_fp = str(raw.get("identity_fingerprint") or "")
        recomputed = w3.fingerprint(raw, w3.PAIRED_IDENTITY)
        if not stored_fp or stored_fp != recomputed:
            raise GuardrailReadError(
                f"stamp {stamp} {ticker} identity fingerprint mismatch")
        source = str(raw.get("source") or "")
        w3._require_committed_source("paired_source", source)
        if source != PAIRED_SOURCE_CANONICAL:
            # The persisted capture owner records the canonical combined source
            # on every row — missing, empty, null and foreign sources refuse.
            raise GuardrailReadError(
                f"stamp {stamp} paired source {source!r} is not {PAIRED_SOURCE_CANONICAL}"
            )
    return frame


def _load_and_validate_stamp(root: Any, stamp: str,
                             rec: dict[str, Any]) -> pd.DataFrame:
    if not w3.stamp_observation_complete(root, stamp):
        raise GuardrailReadError(
            f"stamp {stamp} is not a complete observation (paired+family+coverage)"
        )
    live = w3.observation_fingerprints(root, stamp)
    for field in SESSION_FINGERPRINT_FIELDS:
        expected = str(rec.get(field) or "")
        got = str(live.get(field) or "")
        if not expected or expected != got:
            raise GuardrailReadError(
                f"stamp {stamp} {field} mismatch: session={expected} store={got}"
            )
    frame = w3.load_paired_stamp(root, stamp)
    validated = _validate_paired_frame(stamp, frame, rec)
    grain_fp = w3.grain_fingerprint(
        validated, w3.PAIRED_KEY, w3.PAIRED_IDENTITY)
    live_fp = str(live.get("paired_fingerprint") or "")
    rec_fp = str(rec.get("paired_fingerprint") or "")
    if not grain_fp or grain_fp != live_fp or grain_fp != rec_fp:
        raise GuardrailReadError(
            f"stamp {stamp} paired grain fingerprint "
            f"{grain_fp[:16] if grain_fp else grain_fp!r} does not match BOTH the "
            f"observation ({live_fp[:16] if live_fp else live_fp!r}) and the session "
            f"({rec_fp[:16] if rec_fp else rec_fp!r}) paired_fingerprint"
        )
    return validated


def _stamp_rank_ics(frame: pd.DataFrame) -> tuple[float, float, float]:
    c1 = rank_ic(-pd.to_numeric(frame["score_rank"], errors="coerce"),
                 pd.to_numeric(frame["excess_spy"], errors="coerce"),
                 min_names=MIN_NAMES)
    shadow = rank_ic(
        -pd.to_numeric(frame["prophet_shadow_score_rank"], errors="coerce"),
        pd.to_numeric(frame["excess_spy"], errors="coerce"),
        min_names=MIN_NAMES)
    if not math.isfinite(c1) or not math.isfinite(shadow):
        raise GuardrailReadError("undefined rank-IC on a selected stamp")
    return float(c1), float(shadow), float(c1) - float(shadow)


def top_n_inclusive_ties(frame: pd.DataFrame, rank_col: str,
                         n: int = TOP_N) -> tuple[pd.DataFrame, int]:
    """Rank-order top-n including every name tied at the cutoff rank."""
    ranks = pd.to_numeric(frame[rank_col], errors="coerce")
    keep = frame.loc[ranks.notna()].copy()
    if keep.empty:
        return keep, 0
    keep = keep.assign(_rank=ranks.loc[keep.index])
    keep = keep.loc[keep["_rank"].map(_finite)].sort_values("_rank", kind="mergesort")
    if keep.empty:
        return keep, 0
    if len(keep) <= n:
        out = keep.drop(columns="_rank")
        return out, int(len(out))
    cutoff = keep["_rank"].iloc[n - 1]
    selected = keep.loc[keep["_rank"] <= cutoff].drop(columns="_rank")
    return selected, int(len(selected))


def _stamp_top30(frame: pd.DataFrame) -> dict[str, Any]:
    c1, c1_n = top_n_inclusive_ties(frame, "score_rank", TOP_N)
    shadow, shadow_n = top_n_inclusive_ties(frame, "prophet_shadow_score_rank", TOP_N)
    if c1.empty or shadow.empty:
        raise GuardrailReadError("top-30 selection empty on a selected stamp")
    c1_mean = float(pd.to_numeric(c1["excess_spy"], errors="coerce").mean())
    shadow_mean = float(pd.to_numeric(shadow["excess_spy"], errors="coerce").mean())
    if not math.isfinite(c1_mean) or not math.isfinite(shadow_mean):
        raise GuardrailReadError("non-finite top-30 mean excess on a selected stamp")
    return {
        "c1_n": c1_n,
        "shadow_n": shadow_n,
        "c1_mean_excess_spy": c1_mean,
        "shadow_mean_excess_spy": shadow_mean,
        "delta": c1_mean - shadow_mean,
    }


def hac_t_interval(deltas, lags: int = HAC_LAGS) -> dict[str, Any]:
    """Student-t HAC interval for mean ΔIC. Normal p is diagnostic only."""
    from scipy.stats import t as student_t

    nw = newey_west_tstat(deltas, lags=lags, unrounded=True)
    mean = nw["mean"]
    se = nw["se"]
    t_stat = nw["t"]
    n = int(nw["n"])
    if mean is None or se is None or t_stat is None or n < 2:
        raise GuardrailReadError("HAC estimator undefined on the ΔIC series")
    df = n - 1
    crit = float(student_t.ppf(0.975, df))
    ci_lo = float(mean) - crit * float(se)
    ci_hi = float(mean) + crit * float(se)
    tripwire = bool(ci_hi < 0)
    return {
        "n": n,
        "df": df,
        "hac_lags": int(nw["lags"]),
        "hac_lags_requested": int(nw["lags_requested"]),
        "mean": float(mean),
        "se": float(se),
        "t": float(t_stat),
        "ci95_lo": ci_lo,
        "ci95_hi": ci_hi,
        "tripwire_upper95ci_lt_0": tripwire,
        "p_normal_diagnostic": None if nw["p"] is None else float(nw["p"]),
    }


def _statistical_read(accrual: dict[str, Any],
                      stamps: list[str],
                      frames: list[pd.DataFrame]) -> dict[str, Any]:
    per_stamp: list[dict[str, Any]] = []
    deltas: list[float] = []
    top_deltas: list[float] = []
    for stamp, frame in zip(stamps, frames):
        ic_c1, ic_shadow, delta = _stamp_rank_ics(frame)
        top = _stamp_top30(frame)
        deltas.append(delta)
        top_deltas.append(float(top["delta"]))
        per_stamp.append({
            "stamp_date": stamp,
            "n_paired": int(len(frame)),
            "ic_c1": ic_c1,
            "ic_shadow": ic_shadow,
            "delta_ic": delta,
            "top30": top,
        })
    primary = hac_t_interval(deltas, lags=HAC_LAGS)
    secondary_mean = float(sum(top_deltas) / len(top_deltas))
    primary_fires = bool(primary["tripwire_upper95ci_lt_0"])
    secondary_adverse = bool(secondary_mean < 0)
    label = None
    if primary_fires and not secondary_adverse:
        label = PRIMARY_LABEL_NONCONFIRMATORY
    payload = _base_doc("READ", accrual)
    payload["primary"] = {
        "metric": "delta_rank_ic",
        "sign": "spearman(-score_rank, excess_spy); delta = IC_C1 - IC_shadow",
        "min_names": MIN_NAMES,
        **primary,
        "controls_investigation": True,
    }
    payload["secondary"] = {
        "metric": "top30_mean_excess_spy",
        "n_cutoff": TOP_N,
        "ties": "inclusive_of_cutoff",
        "mean_delta": secondary_mean,
        "adverse": secondary_adverse,
        "or_trigger": False,
        "cancels_primary": False,
        "by_stamp": [
            {"stamp_date": row["stamp_date"], **row["top30"]}
            for row in per_stamp
        ],
    }
    payload["per_stamp"] = per_stamp
    payload["investigation_open"] = primary_fires
    payload["investigation_label"] = label if primary_fires else None
    payload["p_normal_controls_primary"] = False
    return payload


def read_w3_guardrail(root: Any) -> dict[str, Any]:
    """First call is sessions_by_stamp. Loaders run only after the floor is met."""
    sessions = w3.sessions_by_stamp(root)
    race = sorted(
        stamp for stamp, rec in sessions.items() if _is_race_liveness(rec)
    )
    selected = [stamp for stamp in race if _session_metadata_ok(sessions[stamp])]
    malformed_meta = [stamp for stamp in race if stamp not in selected]
    accrual = _accrual_counts(sessions, selected)

    if len(selected) < w3.HONEST_N_FLOOR:
        payload = _base_doc(
            "FLOOR_UNMET",
            accrual,
            refusal=(
                f"honest-N floor unmet: {len(selected)} matured H=10 paired "
                f"sessions; first lawful comparison at {w3.HONEST_N_FLOOR}"
            ),
        )
        payload["first_lawful_comparison_read"] = (
            f"PENDING until {w3.HONEST_N_FLOOR} matured H=10 sessions")
        _assert_accrual_only(payload)
        return payload

    if malformed_meta:
        payload = _base_doc(
            "REFUSED",
            accrual,
            refusal=(
                "malformed claimed paired_accrued stamp(s) "
                f"{malformed_meta}; whole read refused (no survivor drop)"
            ),
        )
        _assert_accrual_only(payload)
        return payload

    try:
        frames = [
            _load_and_validate_stamp(root, stamp, sessions[stamp])
            for stamp in selected
        ]
        return _statistical_read(accrual, selected, frames)
    except (GuardrailReadError, w3.W3IntegrityError, w3.W3SchemaError) as exc:
        payload = _base_doc("REFUSED", accrual, refusal=str(exc))
        _assert_accrual_only(payload)
        return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--root",
        required=True,
        help="repo root containing data/us_prophet_rank/w3 (required; no live default)",
    )
    args = ap.parse_args(argv)
    payload = read_w3_guardrail(Path(args.root))
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str, sort_keys=True))
    if payload.get("status") == "REFUSED":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
