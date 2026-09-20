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
TRANSITION_SCHEMA = "skylit.r6.topology_transition/v1"
EXPOSURE_UNIT = getattr(r2, "EXPOSURE_UNIT", "USD dealer-delta change per +1% spot move")
COSINE_MAX_CLIPPED_MASS = 0.01
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
            "cosine_max_clipped_mass": COSINE_MAX_CLIPPED_MASS,
            "em_normalized": True,
        }
    return {
        "kind": "log_moneyness",
        "expected_move_pct": None,
        "scale": 1.0,
        "grid_min": -0.50,
        "grid_max": 0.50,
        "grid_bins": 200,
        "cosine_max_clipped_mass": COSINE_MAX_CLIPPED_MASS,
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


def _persistent_node_spec(
    prominence_fraction: float | None,
    match_tolerance_x: float | None,
    min_expiries: int | None,
) -> dict[str, Any] | None:
    values = (prominence_fraction, match_tolerance_x, min_expiries)
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise R6Refusal(
            "persistent-node matching requires prominence_fraction, "
            "match_tolerance_x and min_expiries together"
        )
    prominence = float(prominence_fraction)
    tolerance = float(match_tolerance_x)
    minimum = int(min_expiries)
    if not np.isfinite(prominence) or not 0 < prominence <= 1:
        raise R6Refusal("node_prominence_fraction must be within (0, 1]")
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise R6Refusal("node_match_tolerance_x must be finite and positive")
    if minimum < 2 or float(min_expiries) != minimum:
        raise R6Refusal("node_min_expiries must be an integer >= 2")
    return {
        "prominence_fraction_of_expiry_max": prominence,
        "match_tolerance_x": tolerance,
        "min_consecutive_expiries": minimum,
    }


def _persistent_node_matching(
    expiry_rows: list[dict[str, Any]],
    expiry_dist: dict[str, pd.DataFrame],
    match_spec: dict[str, Any] | None,
) -> dict[str, Any]:
    if match_spec is None:
        return {
            "status": "NOT_REQUESTED",
            "spec": None,
            "candidate_node_count": None,
            "track_count": None,
            "persistent_track_count": None,
            "tracks": [],
        }

    prominence = float(match_spec["prominence_fraction_of_expiry_max"])
    tolerance = float(match_spec["match_tolerance_x"])
    minimum = int(match_spec["min_consecutive_expiries"])
    tracks: list[dict[str, Any]] = []
    candidate_total = 0

    for expiry_index, expiry_row in enumerate(expiry_rows):
        dist = expiry_dist[expiry_row["expiration"]]
        max_mass = float(dist["gross_abs_exposure"].max())
        threshold = prominence * max_mass
        candidates: list[dict[str, Any]] = []
        for row in dist.itertuples(index=False):
            if float(row.gross_abs_exposure) + 1e-15 < threshold:
                continue
            candidates.append({
                "expiration": expiry_row["expiration"],
                "dte": expiry_row["dte"],
                "tenor_bucket": expiry_row["tenor_bucket"],
                "strike": float(row.strike),
                "x": float(row.x),
                "share": float(row.p),
                "gross_abs_exposure": float(row.gross_abs_exposure),
                "signed_net_exposure": float(row.signed_net_exposure),
            })
        candidates.sort(key=lambda row: (row["x"], -row["gross_abs_exposure"]))
        candidate_total += len(candidates)

        eligible_tracks = [
            idx
            for idx, track in enumerate(tracks)
            if track["_last_expiry_index"] == expiry_index - 1
        ]
        pairs: list[tuple[float, int, int]] = []
        for track_idx in eligible_tracks:
            last_x = float(tracks[track_idx]["nodes"][-1]["x"])
            for candidate_idx, candidate in enumerate(candidates):
                distance = abs(last_x - float(candidate["x"]))
                if distance <= tolerance:
                    pairs.append((distance, track_idx, candidate_idx))
        pairs.sort(key=lambda item: (item[0], item[1], item[2]))

        used_tracks: set[int] = set()
        used_candidates: set[int] = set()
        for distance, track_idx, candidate_idx in pairs:
            if track_idx in used_tracks or candidate_idx in used_candidates:
                continue
            candidate = dict(candidates[candidate_idx])
            candidate["match_distance_x"] = float(distance)
            tracks[track_idx]["nodes"].append(candidate)
            tracks[track_idx]["_last_expiry_index"] = expiry_index
            used_tracks.add(track_idx)
            used_candidates.add(candidate_idx)

        for candidate_idx, candidate in enumerate(candidates):
            if candidate_idx in used_candidates:
                continue
            node = dict(candidate)
            node["match_distance_x"] = None
            tracks.append({
                "_last_expiry_index": expiry_index,
                "nodes": [node],
            })

    persistent: list[dict[str, Any]] = []
    for track_idx, track in enumerate(tracks):
        nodes = track["nodes"]
        if len(nodes) < minimum:
            continue
        xs = np.array([node["x"] for node in nodes], dtype=float)
        shares = np.array([node["share"] for node in nodes], dtype=float)
        gross = np.array([node["gross_abs_exposure"] for node in nodes], dtype=float)
        match_distances = [
            float(node["match_distance_x"])
            for node in nodes
            if node["match_distance_x"] is not None
        ]
        persistent.append({
            "track_id": int(track_idx),
            "n_expiries": len(nodes),
            "first_expiration": nodes[0]["expiration"],
            "last_expiration": nodes[-1]["expiration"],
            "x_mean": float(xs.mean()),
            "x_min": float(xs.min()),
            "x_max": float(xs.max()),
            "x_span": float(xs.max() - xs.min()),
            "mean_node_share": float(shares.mean()),
            "max_node_share": float(shares.max()),
            "mean_gross_abs_exposure": float(gross.mean()),
            "max_match_distance_x": max(match_distances) if match_distances else 0.0,
            "tenor_buckets": list(dict.fromkeys(node["tenor_bucket"] for node in nodes)),
            "nodes": nodes,
        })

    persistent.sort(
        key=lambda track: (
            -track["n_expiries"],
            -track["max_node_share"],
            track["x_mean"],
        )
    )
    return {
        "status": "COMPLETE",
        "spec": match_spec,
        "candidate_node_count": candidate_total,
        "track_count": len(tracks),
        "persistent_track_count": len(persistent),
        "tracks": persistent,
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
    clip_gate = float(spec.get("cosine_max_clipped_mass", COSINE_MAX_CLIPPED_MASS))
    # Never let the boundary bins absorb a material tail and then report a
    # precise-looking cosine. Wasserstein remains exact on the discrete support.
    if max(clip_a, clip_b) > clip_gate:
        return None, clip_a, clip_b
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


def _dominant_tenor(by_tenor: list[dict[str, Any]]) -> str | None:
    present = [row for row in by_tenor if row.get("present")]
    if not present:
        return None
    return max(present, key=lambda row: float(row["gross_abs_exposure"]))["tenor_bucket"]


def _persistent_track_transition(
    block0: dict[str, Any],
    block1: dict[str, Any],
) -> dict[str, Any]:
    if block0.get("status") != "COMPLETE" or block1.get("status") != "COMPLETE":
        return {
            "status": "NOT_REQUESTED",
            "continued": None,
            "born": None,
            "died": None,
            "continuations": [],
        }
    spec0 = block0.get("spec") or {}
    spec1 = block1.get("spec") or {}
    tolerance0 = float(spec0.get("match_tolerance_x", np.nan))
    tolerance1 = float(spec1.get("match_tolerance_x", np.nan))
    if not np.isfinite(tolerance0) or not np.isfinite(tolerance1) or not np.isclose(tolerance0, tolerance1):
        raise R6Refusal("persistent-node transition requires the same match_tolerance_x in both states")
    tolerance = tolerance0
    tracks0 = block0.get("tracks") or []
    tracks1 = block1.get("tracks") or []
    pairs: list[tuple[float, int, int]] = []
    for i, left in enumerate(tracks0):
        for j, right in enumerate(tracks1):
            distance = abs(float(left["x_mean"]) - float(right["x_mean"]))
            if distance <= tolerance:
                pairs.append((distance, i, j))
    pairs.sort(key=lambda item: (item[0], item[1], item[2]))

    used0: set[int] = set()
    used1: set[int] = set()
    continuations: list[dict[str, Any]] = []
    for distance, i, j in pairs:
        if i in used0 or j in used1:
            continue
        left = tracks0[i]
        right = tracks1[j]
        used0.add(i)
        used1.add(j)
        continuations.append({
            "track0_id": left["track_id"],
            "track1_id": right["track_id"],
            "x0": float(left["x_mean"]),
            "x1": float(right["x_mean"]),
            "delta_x": float(right["x_mean"] - left["x_mean"]),
            "match_distance_x": float(distance),
            "n_expiries0": int(left["n_expiries"]),
            "n_expiries1": int(right["n_expiries"]),
        })

    continuations.sort(key=lambda row: (row["match_distance_x"], row["x0"]))
    return {
        "status": "COMPLETE",
        "match_tolerance_x": tolerance,
        "continued": len(continuations),
        "born": len(tracks1) - len(used1),
        "died": len(tracks0) - len(used0),
        "continuations": continuations,
    }


def analyze_state(
    settled_state: dict[str, Any],
    session: str,
    *,
    expected_move_pct: float | None = None,
    node_prominence_fraction: float | None = None,
    node_match_tolerance_x: float | None = None,
    node_min_expiries: int | None = None,
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
    persistent_spec = _persistent_node_spec(
        node_prominence_fraction,
        node_match_tolerance_x,
        node_min_expiries,
    )
    persistent_nodes = _persistent_node_matching(
        expiry_rows,
        expiry_dist,
        persistent_spec,
    )

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
            "cosine_available": cosine is not None,
            "cosine_refusal_reason": (
                "grid_clipped_mass"
                if cosine is None and max(clip_a, clip_b) > float(spec["cosine_max_clipped_mass"])
                else None
            ),
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
    max_grid_clip = max(
        (
            max(row["left_grid_clipped_mass"], row["right_grid_clipped_mass"])
            for row in adjacent
        ),
        default=None,
    )
    cosine_refused = sum(1 for row in adjacent if row["cosine_similarity"] is None)
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
        "persistent_node_matching": persistent_nodes,
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
            "cosine_pairs_available": len(cosines),
            "cosine_pairs_refused": cosine_refused,
            "max_adjacent_grid_clipped_mass": max_grid_clip,
            "persistent_track_count": persistent_nodes["persistent_track_count"],
            "centroid_slope_per_dte": _slope(expiry_rows, "centroid_x"),
            "entropy_slope_per_dte": _slope(expiry_rows, "normalized_entropy"),
            "concentration_slope_per_dte": _slope(expiry_rows, "top_node_share"),
        },
        "limitations": [
            "Stage 0 describes geometry only; no future market outcomes are read",
            "EM-normalized mode requires an externally qualified expected-move input",
            "cosine uses an explicit fixed coordinate grid and refuses any pair with >1% clipped mass; Wasserstein remains exact on discrete support",
            "persistent-node matching is construction-only and parameter-explicit; expiry-roll prediction is a later R6 slice",
            "signed fields inherit the declared R2 position tier; magnitude fields do not",
        ],
    }


def analyze_transition(
    settled_state0: dict[str, Any],
    settled_state1: dict[str, Any],
    session0: str,
    session1: str,
    *,
    expected_move_pct0: float | None = None,
    expected_move_pct1: float | None = None,
    node_prominence_fraction: float | None = None,
    node_match_tolerance_x: float | None = None,
    node_min_expiries: int | None = None,
) -> dict[str, Any]:
    day0 = date.fromisoformat(session0)
    day1 = date.fromisoformat(session1)
    if day1 <= day0:
        raise R6Refusal("R6 transition requires session1 after session0")

    view0 = analyze_state(
        settled_state0,
        session0,
        expected_move_pct=expected_move_pct0,
        node_prominence_fraction=node_prominence_fraction,
        node_match_tolerance_x=node_match_tolerance_x,
        node_min_expiries=node_min_expiries,
    )
    view1 = analyze_state(
        settled_state1,
        session1,
        expected_move_pct=expected_move_pct1,
        node_prominence_fraction=node_prominence_fraction,
        node_match_tolerance_x=node_match_tolerance_x,
        node_min_expiries=node_min_expiries,
    )
    spec0 = view0["coordinate"]
    spec1 = view1["coordinate"]
    if spec0["kind"] != spec1["kind"]:
        raise R6Refusal("R6 transition cannot mix expected-move and raw log-moneyness coordinates")

    frame0 = settled_state0.get("frame")
    frame1 = settled_state1.get("frame")
    if not isinstance(frame0, pd.DataFrame) or not isinstance(frame1, pd.DataFrame):
        raise R6Refusal("R6 transition requires both settled-state frames")
    work0 = _normalize_frame(frame0, session0, spec0)
    work1 = _normalize_frame(frame1, session1, spec1)
    dist0 = _strike_distribution(work0)
    dist1 = _strike_distribution(work1)
    metrics0 = _distribution_metrics(dist0)
    metrics1 = _distribution_metrics(dist1)

    comparison_spec = dict(spec0)
    cosine, clip0, clip1 = _cosine_similarity(dist0, dist1, comparison_spec)

    tenor0 = {row["tenor_bucket"]: row for row in view0["by_tenor"] if row.get("present")}
    tenor1 = {row["tenor_bucket"]: row for row in view1["by_tenor"] if row.get("present")}
    total0 = float(sum(float(row["gross_abs_exposure"]) for row in tenor0.values()))
    total1 = float(sum(float(row["gross_abs_exposure"]) for row in tenor1.values()))
    tenor_changes: list[dict[str, Any]] = []
    polarity_changes: list[dict[str, Any]] = []
    for name, _, _ in TENOR_BUCKETS:
        left = tenor0.get(name)
        right = tenor1.get(name)
        share0 = (
            float(left["gross_abs_exposure"]) / total0
            if left is not None and total0 > 0
            else None
        )
        share1 = (
            float(right["gross_abs_exposure"]) / total1
            if right is not None and total1 > 0
            else None
        )
        tenor_changes.append({
            "tenor_bucket": name,
            "present0": left is not None,
            "present1": right is not None,
            "gross_share0": share0,
            "gross_share1": share1,
            "gross_share_change": (
                share1 - share0
                if share0 is not None and share1 is not None
                else None
            ),
        })
        if (
            left is not None
            and right is not None
            and int(left["signed_regime"]) != int(right["signed_regime"])
        ):
            polarity_changes.append({
                "tenor_bucket": name,
                "signed_regime0": int(left["signed_regime"]),
                "signed_regime1": int(right["signed_regime"]),
            })

    expiries0 = {row["expiration"] for row in view0["by_expiry"]}
    expiries1 = {row["expiration"] for row in view1["by_expiry"]}
    persistent_transition = _persistent_track_transition(
        view0["persistent_node_matching"],
        view1["persistent_node_matching"],
    )

    return {
        "schema": TRANSITION_SCHEMA,
        "status": "TOPOLOGY_TRANSITION_COMPLETE",
        "research_authority": "research_only",
        "outcome_labels_opened": False,
        "root": settled_state0.get("root"),
        "session0": session0,
        "session1": session1,
        "calendar_days": (day1 - day0).days,
        "decision_eligible_not_before_session": settled_state1.get(
            "decision_eligible_not_before_session"
        ),
        "coordinate0": spec0,
        "coordinate1": spec1,
        "whole_board": {
            "wasserstein_1_x": _wasserstein_1(dist0, dist1),
            "cosine_similarity": cosine,
            "cosine_available": cosine is not None,
            "cosine_refusal_reason": (
                "grid_clipped_mass"
                if cosine is None
                and max(clip0, clip1) > float(comparison_spec["cosine_max_clipped_mass"])
                else None
            ),
            "grid_clipped_mass0": clip0,
            "grid_clipped_mass1": clip1,
            "centroid_change_x": metrics1["centroid_x"] - metrics0["centroid_x"],
            "dispersion_change_x": metrics1["dispersion_x"] - metrics0["dispersion_x"],
            "entropy_change": metrics1["normalized_entropy"] - metrics0["normalized_entropy"],
            "hhi_change": metrics1["hhi"] - metrics0["hhi"],
            "top_node_share_change": metrics1["top_node_share"] - metrics0["top_node_share"],
            "gross_abs_exposure0": metrics0["gross_abs_exposure"],
            "gross_abs_exposure1": metrics1["gross_abs_exposure"],
            "gross_abs_exposure_change": (
                metrics1["gross_abs_exposure"] - metrics0["gross_abs_exposure"]
            ),
            "signed_regime0": metrics0["signed_regime"],
            "signed_regime1": metrics1["signed_regime"],
        },
        "expiry_population": {
            "count0": len(expiries0),
            "count1": len(expiries1),
            "common": len(expiries0 & expiries1),
            "dropped": sorted(expiries0 - expiries1),
            "added": sorted(expiries1 - expiries0),
        },
        "tenor": {
            "dominant0": _dominant_tenor(view0["by_tenor"]),
            "dominant1": _dominant_tenor(view1["by_tenor"]),
            "changes": tenor_changes,
            "polarity_changes": polarity_changes,
        },
        "persistent_nodes": persistent_transition,
        "limitations": [
            "construction-only topology migration; no future price/return/volatility labels are read",
            "whole-board comparison uses the declared normalized coordinate in each session",
            "persistent-track continuation is one-to-one within the same declared normalized-x tolerance",
            "added/dropped expiry populations are reported, not silently zero-imputed",
        ],
    }


def run_session(
    session: str,
    root: str,
    *,
    store: str | Path | None = None,
    expected_move_pct: float | None = None,
    node_prominence_fraction: float | None = None,
    node_match_tolerance_x: float | None = None,
    node_min_expiries: int | None = None,
) -> dict[str, Any]:
    state = r2.build_settled_state(session, root, store=store)
    return analyze_state(
        state,
        session,
        expected_move_pct=expected_move_pct,
        node_prominence_fraction=node_prominence_fraction,
        node_match_tolerance_x=node_match_tolerance_x,
        node_min_expiries=node_min_expiries,
    )


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
    p.add_argument("--node-prominence-fraction", type=float)
    p.add_argument("--node-match-tolerance-x", type=float)
    p.add_argument("--node-min-expiries", type=int)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = run_session(
            args.session,
            args.root,
            store=args.store,
            expected_move_pct=args.expected_move_pct,
            node_prominence_fraction=args.node_prominence_fraction,
            node_match_tolerance_x=args.node_match_tolerance_x,
            node_min_expiries=args.node_min_expiries,
        )
    except (r2.R2Refusal, R6Refusal, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
