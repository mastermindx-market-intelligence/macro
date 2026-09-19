from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
from typing import Any

import numpy as np
import pandas as pd

from scripts import research_skylit_r2_exposure_decomposition as r2

SCHEMA = "skylit.r6.cross_expiry_topology_feasibility/v1"
EXPOSURE_UNIT = getattr(r2, "EXPOSURE_UNIT", "USD dealer-delta change per +1% spot move")
TENOR_BUCKETS = (
    ("0DTE", 0, 0),
    ("1-2DTE", 1, 2),
    ("3-7DTE", 3, 7),
    ("8-30DTE", 8, 30),
    ("31-90DTE", 31, 90),
    ("91D+", 91, None),
)


class R6Refusal(ValueError):
    pass


def _coordinate_spec(expected_move_pct: float | None) -> dict[str, Any]:
    if expected_move_pct is not None:
        value = float(expected_move_pct)
        if not np.isfinite(value) or value <= 0:
            raise R6Refusal("expected_move_pct must be finite and positive")
        scale = float(np.log1p(value / 100.0))
        if not np.isfinite(scale) or scale <= 0:
            raise R6Refusal("expected_move_pct produces an invalid log scale")
        return {
            "kind": "log_moneyness_over_expected_move",
            "expected_move_pct": value,
            "scale": scale,
            "grid_min": -4.0,
            "grid_max": 4.0,
            "grid_bins": 160,
            "em_normalized": True,
        }
    return {
        "kind": "log_moneyness",
        "expected_move_pct": None,
        "scale": 1.0,
        "grid_min": -0.50,
        "grid_max": 0.50,
        "grid_bins": 200,
        "em_normalized": False,
    }


def _tenor_bucket(dte: int) -> str | None:
    for name, lo, hi in TENOR_BUCKETS:
        if dte < lo:
            continue
        if hi is None or dte <= hi:
            return name
    return None


def _normalize_frame(frame: pd.DataFrame, session: str, spec: dict[str, Any]) -> pd.DataFrame:
    required = {"root", "expiration", "strike", "right", "spot", "exposure_gex"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise R6Refusal(f"settled state missing columns: {missing}")
    if frame.empty:
        raise R6Refusal("settled state has no contracts")

    out = frame.copy()
    out["strike"] = pd.to_numeric(out["strike"], errors="coerce")
    out["spot"] = pd.to_numeric(out["spot"], errors="coerce")
    out["exposure_gex"] = pd.to_numeric(out["exposure_gex"], errors="coerce")
    out["expiration"] = pd.to_datetime(out["expiration"], errors="coerce")
    day = date.fromisoformat(session)
    out["dte"] = out["expiration"].dt.date.map(lambda x: (x - day).days if pd.notna(x) else np.nan)

    valid = (
        np.isfinite(out["strike"]) & (out["strike"] > 0)
        & np.isfinite(out["spot"]) & (out["spot"] > 0)
        & np.isfinite(out["exposure_gex"])
        & np.isfinite(out["dte"]) & (out["dte"] >= 0)
    )
    if not bool(valid.all()):
        raise R6Refusal(f"invalid settled-state rows: {int((~valid).sum())}/{len(out)}")

    spot = float(out["spot"].median())
    if spot <= 0:
        raise R6Refusal("invalid spot")
    out["x"] = np.log(out["strike"] / spot) / float(spec["scale"])
    if not np.isfinite(out["x"]).all():
        raise R6Refusal("non-finite normalized strike coordinate")
    out["expiration"] = out["expiration"].dt.date.astype(str)
    out["tenor_bucket"] = out["dte"].astype(int).map(_tenor_bucket)
    return out


def _strike_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = frame.groupby("strike", as_index=False).agg(
        x=("x", "first"),
        gross_abs_exposure=("exposure_gex", lambda s: float(np.abs(s).sum())),
        signed_net_exposure=("exposure_gex", "sum"),
    )
    grouped = grouped[
        np.isfinite(grouped["gross_abs_exposure"])
        & (grouped["gross_abs_exposure"] > 0)
    ].copy()
    total = float(grouped["gross_abs_exposure"].sum())
    if not np.isfinite(total) or total <= 0:
        raise R6Refusal("zero/invalid gross exposure mass")
    grouped["p"] = grouped["gross_abs_exposure"] / total
    return grouped.sort_values("x").reset_index(drop=True)


def _distribution_metrics(dist: pd.DataFrame) -> dict[str, Any]:
    x = dist["x"].to_numpy(float)
    p = dist["p"].to_numpy(float)
    n = len(dist)
    mu = float(np.sum(p * x))
    variance = float(np.sum(p * np.square(x - mu)))
    hhi = float(np.sum(np.square(p)))
    entropy = 0.0 if n <= 1 else float(-np.sum(np.where(p > 0, p * np.log(p), 0.0)) / np.log(n))
    signed_net = float(dist["signed_net_exposure"].sum())
    gross = float(dist["gross_abs_exposure"].sum())
    return {
        "n_strikes": n,
        "gross_abs_exposure": gross,
        "signed_net_exposure": signed_net,
        "signed_regime": 1 if signed_net > 0 else -1 if signed_net < 0 else 0,
        "centroid_x": mu,
        "dispersion_x": float(np.sqrt(max(variance, 0.0))),
        "normalized_entropy": entropy,
        "hhi": hhi,
        "effective_node_count": (1.0 / hhi if hhi > 0 else None),
        "top_node_share": float(p.max()) if n else None,
        "mass_above_spot": float(p[x > 0].sum()),
        "mass_above_centroid": float(p[x > mu].sum()),
    }


def _wasserstein_1(a: pd.DataFrame, b: pd.DataFrame) -> float:
    xa = a["x"].to_numpy(float)
    xb = b["x"].to_numpy(float)
    pa = a["p"].to_numpy(float)
    pb = b["p"].to_numpy(float)
    support = np.unique(np.concatenate([xa, xb]))
    if len(support) <= 1:
        return 0.0
    ca = np.array([pa[xa <= s].sum() for s in support[:-1]], dtype=float)
    cb = np.array([pb[xb <= s].sum() for s in support[:-1]], dtype=float)
    return float(np.sum(np.abs(ca - cb) * np.diff(support)))


def _grid_vector(dist: pd.DataFrame, spec: dict[str, Any]) -> tuple[np.ndarray, float]:
    lo = float(spec["grid_min"])
    hi = float(spec["grid_max"])
    bins = int(spec["grid_bins"])
    edges = np.linspace(lo, hi, bins + 1)
    x = dist["x"].to_numpy(float)
    p = dist["p"].to_numpy(float)
    clipped = (x < lo) | (x > hi)
    clipped_mass = float(p[clipped].sum())
    x_clipped = np.clip(x, lo + 1e-12, hi - 1e-12)
    hist, _ = np.histogram(x_clipped, bins=edges, weights=p)
    return hist.astype(float), clipped_mass


def _cosine_similarity(a: pd.DataFrame, b: pd.DataFrame, spec: dict[str, Any]) -> tuple[float | None, float, float]:
    va, clip_a = _grid_vector(a, spec)
    vb, clip_b = _grid_vector(b, spec)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom <= 0:
        return None, clip_a, clip_b
    return float(np.dot(va, vb) / denom), clip_a, clip_b


def _slope(rows: list[dict[str, Any]], field: str) -> float | None:
    pairs = [(float(r["dte"]), float(r[field])) for r in rows if r.get(field) is not None]
    if len(pairs) < 2:
        return None
    x = np.array([p[0] for p in pairs], dtype=float)
    y = np.array([p[1] for p in pairs], dtype=float)
    if np.allclose(x, x[0]):
        return None
    return float(np.polyfit(x, y, 1)[0])


def analyze_state(
    settled_state: dict[str, Any],
    session: str,
    *,
    expected_move_pct: float | None = None,
) -> dict[str, Any]:
    if not settled_state.get("target_gate_pass"):
        raise R6Refusal("R2 settled state is not source-qualified")
    frame = settled_state.get("frame")
    if not isinstance(frame, pd.DataFrame):
        raise R6Refusal("R2 settled state frame unavailable")

    spec = _coordinate_spec(expected_move_pct)
    work = _normalize_frame(frame, session, spec)

    expiry_rows: list[dict[str, Any]] = []
    expiry_dist: dict[str, pd.DataFrame] = {}
    for exp, group in work.groupby("expiration", sort=True):
        dist = _strike_distribution(group)
        expiry_dist[str(exp)] = dist
        metrics = _distribution_metrics(dist)
        metrics.update({
            "expiration": str(exp),
            "dte": int(group["dte"].iloc[0]),
            "tenor_bucket": str(group["tenor_bucket"].iloc[0]),
        })
        expiry_rows.append(metrics)
    expiry_rows.sort(key=lambda r: (r["dte"], r["expiration"]))

    adjacent: list[dict[str, Any]] = []
    for left, right in zip(expiry_rows, expiry_rows[1:]):
        a = expiry_dist[left["expiration"]]
        b = expiry_dist[right["expiration"]]
        cosine, clip_a, clip_b = _cosine_similarity(a, b, spec)
        adjacent.append({
            "left_expiration": left["expiration"],
            "right_expiration": right["expiration"],
            "left_dte": left["dte"],
            "right_dte": right["dte"],
            "wasserstein_1_x": _wasserstein_1(a, b),
            "cosine_similarity": cosine,
            "centroid_displacement_x": right["centroid_x"] - left["centroid_x"],
            "dispersion_change_x": right["dispersion_x"] - left["dispersion_x"],
            "signed_regime_agreement": left["signed_regime"] == right["signed_regime"],
            "left_grid_clipped_mass": clip_a,
            "right_grid_clipped_mass": clip_b,
        })

    tenor_rows: list[dict[str, Any]] = []
    for name, _, _ in TENOR_BUCKETS:
        group = work[work["tenor_bucket"] == name]
        if group.empty:
            tenor_rows.append({"tenor_bucket": name, "present": False})
            continue
        dist = _strike_distribution(group)
        metrics = _distribution_metrics(dist)
        metrics.update({
            "tenor_bucket": name,
            "present": True,
            "n_expirations": int(group["expiration"].nunique()),
        })
        tenor_rows.append(metrics)

    total_gross = float(sum(row["gross_abs_exposure"] for row in expiry_rows))
    dominant = max(expiry_rows, key=lambda r: r["gross_abs_exposure"]) if expiry_rows else None
    max_w = max((row["wasserstein_1_x"] for row in adjacent), default=None)
    cosines = [row["cosine_similarity"] for row in adjacent if row["cosine_similarity"] is not None]
    front_back_gap = (
        expiry_rows[-1]["centroid_x"] - expiry_rows[0]["centroid_x"]
        if len(expiry_rows) >= 2
        else None
    )

    return {
        "schema": SCHEMA,
        "status": "TOPOLOGY_CONSTRUCTION_COMPLETE",
        "research_authority": "research_only",
        "outcome_labels_opened": False,
        "root": settled_state.get("root"),
        "session": session,
        "decision_eligible_not_before_session": settled_state.get("decision_eligible_not_before_session"),
        "position_tier": r2.POSITION_TIER,
        "exposure_unit": EXPOSURE_UNIT,
        "magnitude_semantics": "gross_absolute_contract_exposure_aggregated_by_strike",
        "signed_semantics": "separate_naive_position_tier_net_exposure",
        "coordinate": spec,
        "source_state": {
            "base_input_sha256": settled_state.get("base_input_sha256"),
            "settled_oi_input_sha256": settled_state.get("settled_oi_input_sha256"),
            "unexpired_identity_contracts": settled_state.get("unexpired_identity_contracts"),
            "model_input_contract_rate": settled_state.get("model_input_contract_rate"),
            "spot_input_contract_rate": settled_state.get("spot_input_contract_rate"),
            "settled_oi_contract_rate": settled_state.get("settled_oi_contract_rate"),
            "exposure_mass_coverage": settled_state.get(
                "settled_oi_exposure_mass_coverage_on_prior_known_mass"
            ),
        },
        "daily_view": {
            "same_day_expiry_present": bool((work["dte"] == 0).any()),
            "note": "settled EOD R2 normally excludes contracts expired on the session; intraday 0DTE topology is a separate data lane",
        },
        "by_expiry": expiry_rows,
        "adjacent_expiry_geometry": adjacent,
        "by_tenor": tenor_rows,
        "summary": {
            "n_expirations": len(expiry_rows),
            "dominant_expiration": dominant["expiration"] if dominant else None,
            "dominant_expiration_gross_share": (
                dominant["gross_abs_exposure"] / total_gross
                if dominant and total_gross > 0
                else None
            ),
            "front_back_centroid_gap_x": front_back_gap,
            "max_adjacent_wasserstein_1_x": max_w,
            "median_adjacent_cosine_similarity": (
                float(np.median(cosines)) if cosines else None
            ),
            "centroid_slope_per_dte": _slope(expiry_rows, "centroid_x"),
            "entropy_slope_per_dte": _slope(expiry_rows, "normalized_entropy"),
            "concentration_slope_per_dte": _slope(expiry_rows, "top_node_share"),
        },
        "limitations": [
            "Stage 0 describes geometry only; no future market outcomes are read",
            "EM-normalized mode requires an externally qualified expected-move input",
            "cosine uses an explicit fixed coordinate grid and reports clipped tail mass",
            "persistent-node matching and expiry-roll prediction are later R6 slices",
            "signed fields inherit the declared R2 position tier; magnitude fields do not",
        ],
    }


def run_session(
    session: str,
    root: str,
    *,
    store: str | Path | None = None,
    expected_move_pct: float | None = None,
) -> dict[str, Any]:
    state = r2.build_settled_state(session, root, store=store)
    return analyze_state(state, session, expected_move_pct=expected_move_pct)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Research-only R6 settled cross-expiry topology Stage-0 analyzer"
    )
    p.add_argument("--root", required=True)
    p.add_argument("--session", required=True, help="Settled NYSE session YYYY-MM-DD")
    p.add_argument("--store", help="Optional canonical ThetaData store override")
    p.add_argument(
        "--expected-move-pct",
        type=float,
        help="Optional qualified 1-sigma expected move in percent; omitted => log-moneyness fallback",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = run_session(
            args.session,
            args.root,
            store=args.store,
            expected_move_pct=args.expected_move_pct,
        )
    except (r2.R2Refusal, R6Refusal, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
