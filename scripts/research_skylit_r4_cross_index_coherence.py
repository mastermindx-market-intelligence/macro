from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
from typing import Any

import numpy as np
import pandas as pd

from scripts import research_skylit_r2_exposure_decomposition as r2
from scripts import research_skylit_r6_cross_expiry_topology as r6

SCHEMA = "skylit.r4.cross_index_coherence_feasibility/v1"
ALL_BUCKET = "ALL"
BUCKETS = (ALL_BUCKET,) + tuple(name for name, _, _ in r6.TENOR_BUCKETS)


class R4Refusal(ValueError):
    pass


def _parse_expected_move_receipts(values: list[str] | None) -> dict[str, dict[str, Any]]:
    """Parse explicit ROOT=<json> expected-move receipts for the CLI.

    A bare ROOT=PCT is intentionally no longer accepted: R4 only calls a coordinate
    expected-move-normalized when value, horizon, method and clocks are bound together.
    """
    out: dict[str, dict[str, Any]] = {}
    for item in values or []:
        if "=" not in item:
            raise R4Refusal(f"expected-move receipt must be ROOT=<json>, got {item!r}")
        root, raw = item.split("=", 1)
        root = root.strip().upper()
        if not root:
            raise R4Refusal("expected-move receipt root cannot be empty")
        if root in out:
            raise R4Refusal(f"duplicate expected-move receipt root: {root}")
        try:
            payload = json.loads(raw)
        except Exception as exc:
            raise R4Refusal(f"invalid expected-move receipt JSON for {root}") from exc
        if not isinstance(payload, dict):
            raise R4Refusal(f"expected-move receipt for {root} must be a JSON object")
        out[root] = payload
    return out


def _canonical_day(value: object, *, label: str) -> str:
    try:
        ts = pd.Timestamp(value)
    except Exception as exc:
        raise R4Refusal(f"{label} must be a real date") from exc
    if pd.isna(ts):
        raise R4Refusal(f"{label} must be a real date")
    return ts.date().isoformat()


def _normalise_expected_move_receipts(
    roots: list[str],
    states: dict[str, dict[str, Any]],
    session: str,
    receipts: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    if not receipts:
        return {}

    expected_roots = set(roots)
    raw_by_root: dict[str, dict[str, Any]] = {}
    for key, value in receipts.items():
        root_key = str(key).upper()
        if root_key in raw_by_root:
            raise R4Refusal(f"duplicate expected-move receipt root after normalization: {root_key}")
        raw_by_root[root_key] = value
    got_roots = set(raw_by_root)
    if got_roots != expected_roots:
        missing = sorted(expected_roots - got_roots)
        extra = sorted(got_roots - expected_roots)
        raise R4Refusal(
            f"expected-move mode requires one receipt per root; missing={missing} extra={extra}"
        )

    normalised: dict[str, dict[str, Any]] = {}
    methods: set[str] = set()
    horizons: set[str] = set()
    r4_session = _canonical_day(session, label="R4 session")
    for root in roots:
        raw = raw_by_root[root]
        required = {
            "pct", "horizon", "method",
            "source_effective_session", "decision_eligible_not_before_session",
        }
        missing = sorted(required - set(raw))
        if missing:
            raise R4Refusal(f"expected-move receipt for {root} missing fields: {missing}")
        try:
            pct = float(raw["pct"])
        except Exception as exc:
            raise R4Refusal(f"invalid expected-move pct for {root}") from exc
        if not np.isfinite(pct) or pct <= 0:
            raise R4Refusal(f"expected-move pct for {root} must be finite and positive")

        method = str(raw["method"]).strip()
        horizon = str(raw["horizon"]).strip()
        if not method or not horizon:
            raise R4Refusal(f"expected-move method/horizon must be non-empty for {root}")

        effective = _canonical_day(
            raw["source_effective_session"],
            label=f"{root} expected-move source_effective_session",
        )
        eligible = _canonical_day(
            raw["decision_eligible_not_before_session"],
            label=f"{root} expected-move decision_eligible_not_before_session",
        )
        state_clock = _canonical_day(
            states[root]["decision_eligible_not_before_session"],
            label=f"{root} R2 decision clock",
        )
        if effective > r4_session:
            raise R4Refusal(
                f"expected-move receipt for {root} is effective after R4 session"
            )
        if eligible > state_clock:
            raise R4Refusal(
                f"expected-move receipt for {root} is not available by R4 decision cutoff"
            )
        methods.add(method)
        horizons.add(horizon)
        normalised[root] = {
            "pct": pct,
            "horizon": horizon,
            "method": method,
            "source_effective_session": effective,
            "decision_eligible_not_before_session": eligible,
            "source_receipt": raw.get("source_receipt"),
        }

    if len(methods) != 1:
        raise R4Refusal(f"expected-move methods are not aligned: {sorted(methods)}")
    if len(horizons) != 1:
        raise R4Refusal(f"expected-move horizons are not aligned: {sorted(horizons)}")
    return normalised


def _validate_states(
    states: dict[str, dict[str, Any]],
    session: str,
    expected_move_receipts: dict[str, dict[str, Any]] | None,
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    roots = [str(root).upper() for root in states]
    if len(roots) < 2:
        raise R4Refusal("R4 requires at least two distinct roots")
    if len(set(roots)) != len(roots):
        raise R4Refusal("R4 roots must be unique")

    clocks: set[str] = set()
    tiers: set[str] = set()
    units: set[str] = set()
    for root in roots:
        state = states[root]
        if not state.get("target_gate_pass"):
            raise R4Refusal(f"R2 settled state is not source-qualified for {root}")
        if str(state.get("session")) != session:
            raise R4Refusal(
                f"state/session mismatch for {root}: {state.get('session')!r} != {session!r}"
            )
        frame = state.get("frame")
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            raise R4Refusal(f"qualified R2 frame unavailable for {root}")
        declared_root = str(state.get("root", "")).upper()
        if declared_root != root:
            raise R4Refusal(
                f"state/root identity mismatch: key={root} state={declared_root or '<missing>'}"
            )
        frame_roots = set(frame["root"].astype(str).str.upper()) if "root" in frame.columns else set()
        if frame_roots != {root}:
            raise R4Refusal(
                f"frame/root identity mismatch for {root}: {sorted(frame_roots)}"
            )

        clock = state.get("decision_eligible_not_before_session")
        tier = state.get("position_tier", r2.POSITION_TIER)
        unit = state.get("exposure_unit", r2.EXPOSURE_UNIT)
        if not isinstance(clock, str) or not clock.strip():
            raise R4Refusal(f"missing decision-eligible clock for {root}")
        if not isinstance(tier, str) or not tier.strip():
            raise R4Refusal(f"missing position tier for {root}")
        if not isinstance(unit, str) or not unit.strip():
            raise R4Refusal(f"missing exposure unit for {root}")
        clocks.add(clock.strip())
        tiers.add(tier.strip())
        units.add(unit.strip())

    if len(clocks) != 1:
        raise R4Refusal(f"cross-root decision clocks are not aligned: {sorted(clocks)}")
    if len(tiers) != 1:
        raise R4Refusal(f"cross-root position tiers are not aligned: {sorted(tiers)}")
    if len(units) != 1:
        raise R4Refusal(f"cross-root exposure units are not aligned: {sorted(units)}")
    receipts = _normalise_expected_move_receipts(
        roots, states, session, expected_move_receipts
    )
    return roots, receipts


def _root_groups(
    state: dict[str, Any],
    session: str,
    *,
    expected_move_pct: float | None,
) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    spec = r6._coordinate_spec(expected_move_pct)
    work = r6._normalize_frame(state["frame"], session, spec)

    grouped: dict[str, pd.DataFrame] = {ALL_BUCKET: work}
    for name, _, _ in r6.TENOR_BUCKETS:
        grouped[name] = work[work["tenor_bucket"] == name].copy()

    distributions: dict[str, pd.DataFrame] = {}
    metrics: dict[str, Any] = {}
    for bucket in BUCKETS:
        frame = grouped[bucket]
        if frame.empty:
            metrics[bucket] = {
                "present": False,
                "n_expirations": 0,
            }
            continue
        dist = r6._strike_distribution(frame)
        distributions[bucket] = dist
        one = r6._distribution_metrics(dist)
        one.update(
            {
                "present": True,
                "n_expirations": int(frame["expiration"].nunique()),
            }
        )
        metrics[bucket] = one

    return {
        "coordinate": spec,
        "metrics": metrics,
    }, distributions


def _restrict_to_common_support(
    dist: pd.DataFrame,
    lo: float,
    hi: float,
) -> tuple[pd.DataFrame, float]:
    kept = dist[(dist["x"] >= lo) & (dist["x"] <= hi)].copy()
    retained = float(kept["p"].sum()) if not kept.empty else 0.0
    if retained > 0:
        kept["p"] = kept["p"] / retained
    return kept.reset_index(drop=True), retained


def _pairwise(
    roots: list[str],
    root_meta: dict[str, dict[str, Any]],
    root_dist: dict[str, dict[str, pd.DataFrame]],
    bucket: str,
    *,
    min_common_support_mass: float,
) -> list[dict[str, Any]]:
    available = {
        root: root_dist[root].get(bucket)
        for root in roots
        if root_dist[root].get(bucket) is not None
    }
    support_ranges = {
        root: (float(dist["x"].min()), float(dist["x"].max()))
        for root, dist in available.items()
    }
    common_min = (
        max(bounds[0] for bounds in support_ranges.values())
        if len(support_ranges) >= 2
        else None
    )
    common_max = (
        min(bounds[1] for bounds in support_ranges.values())
        if len(support_ranges) >= 2
        else None
    )
    global_overlap = (
        common_min is not None
        and common_max is not None
        and common_min <= common_max
    )
    restricted: dict[str, pd.DataFrame] = {}
    retained: dict[str, float] = {}
    if global_overlap:
        for root, dist in available.items():
            narrowed, mass = _restrict_to_common_support(
                dist, float(common_min), float(common_max)
            )
            restricted[root] = narrowed
            retained[root] = mass

    rows: list[dict[str, Any]] = []
    for left, right in itertools.combinations(roots, 2):
        a = root_dist[left].get(bucket)
        b = root_dist[right].get(bucket)
        if a is None or b is None:
            rows.append(
                {
                    "left": left,
                    "right": right,
                    "present": False,
                    "reason": "missing_tenor_population",
                    "wasserstein_1_x": None,
                    "cosine_similarity": None,
                    "centroid_distance_x": None,
                    "dispersion_difference_x": None,
                    "entropy_difference": None,
                    "signed_regime_agreement": None,
                    "left_centroid_x": None,
                    "right_centroid_x": None,
                    "full_board_wasserstein_1_x": None,
                    "full_board_cosine_similarity": None,
                    "common_support": None,
                }
            )
            continue

        left_spec = root_meta[left]["coordinate"]
        right_spec = root_meta[right]["coordinate"]
        grid_keys = ("kind", "grid_min", "grid_max", "grid_bins", "em_normalized")
        if any(left_spec[k] != right_spec[k] for k in grid_keys):
            raise R4Refusal(
                f"incompatible coordinate grids for {left}/{right} in {bucket}"
            )

        full_cosine, full_clip_a, full_clip_b = r6._cosine_similarity(a, b, left_spec)
        full_wasserstein = r6._wasserstein_1(a, b)
        left_min, left_max = support_ranges[left]
        right_min, right_max = support_ranges[right]
        support = {
            "support_scope": "all_present_roots_in_bucket",
            "roots_defining_support": sorted(available),
            "left_x_min": left_min,
            "left_x_max": left_max,
            "right_x_min": right_min,
            "right_x_max": right_max,
            "common_x_min": common_min if global_overlap else None,
            "common_x_max": common_max if global_overlap else None,
            "left_retained_mass": retained.get(left, 0.0),
            "right_retained_mass": retained.get(right, 0.0),
            "min_required_mass": min_common_support_mass,
        }

        if not global_overlap:
            rows.append(
                {
                    "left": left,
                    "right": right,
                    "present": False,
                    "reason": "no_common_coordinate_support",
                    "wasserstein_1_x": None,
                    "cosine_similarity": None,
                    "centroid_distance_x": None,
                    "dispersion_difference_x": None,
                    "entropy_difference": None,
                    "signed_regime_agreement": None,
                    "left_centroid_x": None,
                    "right_centroid_x": None,
                    "full_board_wasserstein_1_x": full_wasserstein,
                    "full_board_cosine_similarity": full_cosine,
                    "full_board_left_grid_clipped_mass": full_clip_a,
                    "full_board_right_grid_clipped_mass": full_clip_b,
                    "common_support": support,
                }
            )
            continue

        ar = restricted[left]
        br = restricted[right]
        if (
            retained[left] < min_common_support_mass
            or retained[right] < min_common_support_mass
            or ar.empty
            or br.empty
        ):
            rows.append(
                {
                    "left": left,
                    "right": right,
                    "present": False,
                    "reason": "insufficient_common_support_mass",
                    "wasserstein_1_x": None,
                    "cosine_similarity": None,
                    "centroid_distance_x": None,
                    "dispersion_difference_x": None,
                    "entropy_difference": None,
                    "signed_regime_agreement": None,
                    "left_centroid_x": None,
                    "right_centroid_x": None,
                    "full_board_wasserstein_1_x": full_wasserstein,
                    "full_board_cosine_similarity": full_cosine,
                    "full_board_left_grid_clipped_mass": full_clip_a,
                    "full_board_right_grid_clipped_mass": full_clip_b,
                    "common_support": support,
                }
            )
            continue

        cosine, clip_a, clip_b = r6._cosine_similarity(ar, br, left_spec)
        ma = r6._distribution_metrics(ar)
        mb = r6._distribution_metrics(br)
        rows.append(
            {
                "left": left,
                "right": right,
                "present": True,
                "reason": None,
                "wasserstein_1_x": r6._wasserstein_1(ar, br),
                "cosine_similarity": cosine,
                "left_grid_clipped_mass": clip_a,
                "right_grid_clipped_mass": clip_b,
                "left_centroid_x": float(ma["centroid_x"]),
                "right_centroid_x": float(mb["centroid_x"]),
                "centroid_distance_x": abs(
                    float(ma["centroid_x"]) - float(mb["centroid_x"])
                ),
                "dispersion_difference_x": abs(
                    float(ma["dispersion_x"]) - float(mb["dispersion_x"])
                ),
                "entropy_difference": abs(
                    float(ma["normalized_entropy"]) - float(mb["normalized_entropy"])
                ),
                "signed_regime_agreement": (
                    int(ma["signed_regime"]) == int(mb["signed_regime"])
                ),
                "full_board_wasserstein_1_x": full_wasserstein,
                "full_board_cosine_similarity": full_cosine,
                "full_board_left_grid_clipped_mass": full_clip_a,
                "full_board_right_grid_clipped_mass": full_clip_b,
                "common_support": support,
            }
        )
    return rows


def _bucket_summary(
    roots: list[str],
    root_meta: dict[str, dict[str, Any]],
    pairs: list[dict[str, Any]],
    bucket: str,
) -> dict[str, Any]:
    roots_with_bucket = [
        root for root in roots if root_meta[root]["metrics"][bucket]["present"]
    ]
    present_pairs = [row for row in pairs if row["present"]]
    comparable_roots = sorted(
        {root for row in present_pairs for root in (row["left"], row["right"])}
    )
    expected_pairs = len(roots_with_bucket) * (len(roots_with_bucket) - 1) // 2
    complete_pair_graph = (
        len(roots_with_bucket) >= 2 and len(present_pairs) == expected_pairs
    )
    if not present_pairs:
        return {
            "bucket": bucket,
            "roots_with_bucket": roots_with_bucket,
            "comparable_roots": [],
            "pair_count": 0,
            "pair_total": len(pairs),
            "complete_pair_graph": False,
            "mean_pairwise_wasserstein_1_x": None,
            "max_pairwise_wasserstein_1_x": None,
            "mean_pairwise_cosine_similarity": None,
            "centroid_dispersion_across_roots_x": None,
            "outlier_root": None,
            "outlier_tie": [],
        }

    wasserstein = np.array(
        [float(row["wasserstein_1_x"]) for row in present_pairs], dtype=float
    )
    cosines = [
        float(row["cosine_similarity"])
        for row in present_pairs
        if row["cosine_similarity"] is not None
    ]

    centroid_by_root: dict[str, float] = {}
    for row in present_pairs:
        centroid_by_root[row["left"]] = float(row["left_centroid_x"])
        centroid_by_root[row["right"]] = float(row["right_centroid_x"])
    centroids = np.array(
        [centroid_by_root[root] for root in comparable_roots if root in centroid_by_root],
        dtype=float,
    )

    root_distances: dict[str, list[float]] = {root: [] for root in comparable_roots}
    for row in present_pairs:
        w = float(row["wasserstein_1_x"])
        root_distances[row["left"]].append(w)
        root_distances[row["right"]].append(w)
    average_distance = {
        root: float(np.mean(vals))
        for root, vals in root_distances.items()
        if vals
    }

    outlier_root: str | None = None
    outlier_tie: list[str] = []
    if complete_pair_graph and len(average_distance) >= 3:
        maximum = max(average_distance.values())
        tied = sorted(
            root
            for root, value in average_distance.items()
            if abs(value - maximum) <= 1e-12
        )
        if len(tied) == 1:
            outlier_root = tied[0]
        else:
            outlier_tie = tied

    return {
        "bucket": bucket,
        "roots_with_bucket": roots_with_bucket,
        "comparable_roots": comparable_roots,
        "pair_count": len(present_pairs),
        "pair_total": len(pairs),
        "complete_pair_graph": complete_pair_graph,
        "mean_pairwise_wasserstein_1_x": float(np.mean(wasserstein)),
        "max_pairwise_wasserstein_1_x": float(np.max(wasserstein)),
        "mean_pairwise_cosine_similarity": (
            float(np.mean(cosines)) if cosines else None
        ),
        "centroid_dispersion_across_roots_x": (
            float(np.std(centroids))
            if complete_pair_graph and len(centroids) >= 2
            else None
        ),
        "outlier_root": outlier_root,
        "outlier_tie": outlier_tie,
        "average_wasserstein_by_root": average_distance,
    }


def analyze_states(
    states: dict[str, dict[str, Any]],
    session: str,
    *,
    expected_move_receipts: dict[str, dict[str, Any]] | None = None,
    min_common_support_mass: float,
) -> dict[str, Any]:
    if not np.isfinite(min_common_support_mass) or not (0.0 < min_common_support_mass <= 1.0):
        raise R4Refusal("min_common_support_mass must be finite in (0, 1]")
    normalized_states = {str(root).upper(): state for root, state in states.items()}
    roots, expected_receipts = _validate_states(
        normalized_states, session, expected_move_receipts
    )
    em_mode = bool(expected_receipts)

    root_meta: dict[str, dict[str, Any]] = {}
    root_dist: dict[str, dict[str, pd.DataFrame]] = {}
    source_receipts: dict[str, Any] = {}
    for root in roots:
        meta, dist = _root_groups(
            normalized_states[root],
            session,
            expected_move_pct=expected_receipts[root]["pct"] if em_mode else None,
        )
        root_meta[root] = meta
        root_dist[root] = dist
        source_receipts[root] = {
            "decision_eligible_not_before_session": normalized_states[root].get(
                "decision_eligible_not_before_session"
            ),
            "base_input_sha256": normalized_states[root].get("base_input_sha256"),
            "settled_oi_input_sha256": normalized_states[root].get(
                "settled_oi_input_sha256"
            ),
            "exposure_unit": normalized_states[root].get(
                "exposure_unit", r2.EXPOSURE_UNIT
            ),
            "position_tier": normalized_states[root].get(
                "position_tier", r2.POSITION_TIER
            ),
            "model_input_contract_rate": normalized_states[root].get(
                "model_input_contract_rate"
            ),
            "spot_input_contract_rate": normalized_states[root].get(
                "spot_input_contract_rate"
            ),
            "settled_oi_contract_rate": normalized_states[root].get(
                "settled_oi_contract_rate"
            ),
            "exposure_mass_coverage": normalized_states[root].get(
                "settled_oi_exposure_mass_coverage_on_prior_known_mass"
            ),
            "expected_move_receipt": expected_receipts.get(root) if em_mode else None,
        }

    pairwise_by_bucket: dict[str, list[dict[str, Any]]] = {}
    summaries: list[dict[str, Any]] = []
    for bucket in BUCKETS:
        pairs = _pairwise(
            roots,
            root_meta,
            root_dist,
            bucket,
            min_common_support_mass=min_common_support_mass,
        )
        pairwise_by_bucket[bucket] = pairs
        summaries.append(_bucket_summary(roots, root_meta, pairs, bucket))

    return {
        "schema": SCHEMA,
        "status": "CROSS_INDEX_GEOMETRY_COMPLETE",
        "research_authority": "research_only",
        "outcome_labels_opened": False,
        "trade_or_sizing_authority": False,
        "session": session,
        "roots": roots,
        "spx_spxw_combined": False,
        "spx_spxw_identity_note": (
            "SPX and SPXW remain distinct identities; no implicit merge is performed."
        ),
        "coordinate_mode": (
            "expected_move_normalized" if em_mode else "log_moneyness_fallback"
        ),
        "expected_move_pct_by_root": (
            {root: expected_receipts[root]["pct"] for root in roots}
            if em_mode else None
        ),
        "expected_move_receipts": expected_receipts if em_mode else None,
        "min_common_support_mass": min_common_support_mass,
        "categorical_trinity_baseline": None,
        "categorical_trinity_reason": (
            "Stage 0 does not reinterpret signed GEX agreement as Skylit's 2-of-3/3-of-3 "
            "doctrine. The existing MatrixConfluence baseline is evaluated separately."
        ),
        "source_receipts": source_receipts,
        "root_topology": {
            root: {
                "coordinate": root_meta[root]["coordinate"],
                "by_bucket": root_meta[root]["metrics"],
            }
            for root in roots
        },
        "pairwise_by_bucket": pairwise_by_bucket,
        "system_by_bucket": summaries,
        "limitations": [
            "Stage 0 compares topology geometry only; no future price or option outcomes are read.",
            "Gross exposure shape is normalized separately from total exposure scale.",
            "Primary pairwise geometry is restricted to common normalized strike support and requires the declared retained-mass gate; full-board W1/cosine remain sensitivity diagnostics.",
            "Signed-regime agreement is descriptive and is not a Trinity trade or sizing state.",
            "Top-node overlap, cross-Greek alignment, R5 scenario coherence, liquidity weighting and the production MatrixConfluence baseline are later declared arms.",
            "SPX and SPXW are never silently substituted or combined.",
        ],
    }


def run_session(
    session: str,
    roots: list[str],
    *,
    store: str | Path | None = None,
    expected_move_receipts: dict[str, dict[str, Any]] | None = None,
    min_common_support_mass: float,
) -> dict[str, Any]:
    normalized = [root.upper() for root in roots]
    if len(set(normalized)) != len(normalized):
        raise R4Refusal("duplicate roots are not allowed")
    states = {
        root: r2.build_settled_state(session, root, store=store)
        for root in normalized
    }
    return analyze_states(
        states,
        session,
        expected_move_receipts=expected_move_receipts,
        min_common_support_mass=min_common_support_mass,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Research-only R4 cross-index topology coherence Stage-0 analyzer"
    )
    p.add_argument("--session", required=True, help="Settled NYSE session YYYY-MM-DD")
    p.add_argument(
        "--root",
        action="append",
        dest="roots",
        required=True,
        help="Explicit root identity; repeat at least twice (e.g. SPXW, SPY, QQQ)",
    )
    p.add_argument("--store", help="Optional canonical ThetaData store override")
    p.add_argument(
        "--expected-move-receipt",
        action="append",
        help=(
            "Optional ROOT=<json> receipt with pct,horizon,method,"
            "source_effective_session,decision_eligible_not_before_session; "
            "if supplied, every root requires one"
        ),
    )
    p.add_argument(
        "--min-common-support-mass",
        type=float,
        required=True,
        help="Frozen retained-mass gate for primary common-support pairwise geometry",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        expected = _parse_expected_move_receipts(args.expected_move_receipt)
        result = run_session(
            args.session,
            args.roots,
            store=args.store,
            expected_move_receipts=expected or None,
            min_common_support_mass=args.min_common_support_mass,
        )
    except (r2.R2Refusal, r6.R6Refusal, R4Refusal, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
