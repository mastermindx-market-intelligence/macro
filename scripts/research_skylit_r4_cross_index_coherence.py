from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
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


def _parse_expected_moves(values: list[str] | None) -> dict[str, float]:
    out: dict[str, float] = {}
    for item in values or []:
        if "=" not in item:
            raise R4Refusal(f"expected move must be ROOT=PCT, got {item!r}")
        root, raw = item.split("=", 1)
        root = root.strip().upper()
        if not root:
            raise R4Refusal("expected move root cannot be empty")
        if root in out:
            raise R4Refusal(f"duplicate expected move root: {root}")
        try:
            value = float(raw)
        except Exception as exc:
            raise R4Refusal(f"invalid expected move for {root}: {raw!r}") from exc
        if not np.isfinite(value) or value <= 0:
            raise R4Refusal(f"expected move for {root} must be finite and positive")
        out[root] = value
    return out


def _validate_states(
    states: dict[str, dict[str, Any]],
    session: str,
    expected_moves: dict[str, float] | None,
) -> tuple[list[str], bool]:
    roots = [str(root).upper() for root in states]
    if len(roots) < 2:
        raise R4Refusal("R4 requires at least two distinct roots")
    if len(set(roots)) != len(roots):
        raise R4Refusal("R4 roots must be unique")

    expected = {str(k).upper(): float(v) for k, v in (expected_moves or {}).items()}
    em_mode = bool(expected)
    if em_mode and set(expected) != set(roots):
        missing = sorted(set(roots) - set(expected))
        extra = sorted(set(expected) - set(roots))
        raise R4Refusal(
            f"expected-move mode requires one value per root; missing={missing} extra={extra}"
        )

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
    return roots, em_mode


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


def _pairwise(
    roots: list[str],
    root_meta: dict[str, dict[str, Any]],
    root_dist: dict[str, dict[str, pd.DataFrame]],
    bucket: str,
) -> list[dict[str, Any]]:
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
                    "wasserstein_1_x": None,
                    "cosine_similarity": None,
                    "centroid_distance_x": None,
                    "dispersion_difference_x": None,
                    "entropy_difference": None,
                    "signed_regime_agreement": None,
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

        cosine, clip_a, clip_b = r6._cosine_similarity(a, b, left_spec)
        ma = root_meta[left]["metrics"][bucket]
        mb = root_meta[right]["metrics"][bucket]
        rows.append(
            {
                "left": left,
                "right": right,
                "present": True,
                "wasserstein_1_x": r6._wasserstein_1(a, b),
                "cosine_similarity": cosine,
                "left_grid_clipped_mass": clip_a,
                "right_grid_clipped_mass": clip_b,
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
            }
        )
    return rows


def _bucket_summary(
    roots: list[str],
    root_meta: dict[str, dict[str, Any]],
    pairs: list[dict[str, Any]],
    bucket: str,
) -> dict[str, Any]:
    present_pairs = [row for row in pairs if row["present"]]
    if not present_pairs:
        return {
            "bucket": bucket,
            "comparable_roots": [
                root for root in roots if root_meta[root]["metrics"][bucket]["present"]
            ],
            "pair_count": 0,
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
    comparable = [
        root for root in roots if root_meta[root]["metrics"][bucket]["present"]
    ]
    centroids = np.array(
        [float(root_meta[root]["metrics"][bucket]["centroid_x"]) for root in comparable],
        dtype=float,
    )

    root_distances: dict[str, list[float]] = {root: [] for root in comparable}
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
    if len(average_distance) >= 3:
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
        "comparable_roots": comparable,
        "pair_count": len(present_pairs),
        "mean_pairwise_wasserstein_1_x": float(np.mean(wasserstein)),
        "max_pairwise_wasserstein_1_x": float(np.max(wasserstein)),
        "mean_pairwise_cosine_similarity": (
            float(np.mean(cosines)) if cosines else None
        ),
        "centroid_dispersion_across_roots_x": (
            float(np.std(centroids)) if len(centroids) >= 2 else None
        ),
        "outlier_root": outlier_root,
        "outlier_tie": outlier_tie,
        "average_wasserstein_by_root": average_distance,
    }


def analyze_states(
    states: dict[str, dict[str, Any]],
    session: str,
    *,
    expected_moves: dict[str, float] | None = None,
) -> dict[str, Any]:
    normalized_states = {str(root).upper(): state for root, state in states.items()}
    roots, em_mode = _validate_states(normalized_states, session, expected_moves)
    expected = {str(k).upper(): float(v) for k, v in (expected_moves or {}).items()}

    root_meta: dict[str, dict[str, Any]] = {}
    root_dist: dict[str, dict[str, pd.DataFrame]] = {}
    source_receipts: dict[str, Any] = {}
    for root in roots:
        meta, dist = _root_groups(
            normalized_states[root],
            session,
            expected_move_pct=expected.get(root) if em_mode else None,
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
        }

    pairwise_by_bucket: dict[str, list[dict[str, Any]]] = {}
    summaries: list[dict[str, Any]] = []
    for bucket in BUCKETS:
        pairs = _pairwise(roots, root_meta, root_dist, bucket)
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
        "expected_move_pct_by_root": expected if em_mode else None,
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
    expected_moves: dict[str, float] | None = None,
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
        expected_moves=expected_moves,
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
        "--expected-move",
        action="append",
        help="Optional ROOT=PCT; if supplied, every root requires one value",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        expected = _parse_expected_moves(args.expected_move)
        result = run_session(
            args.session,
            args.roots,
            store=args.store,
            expected_moves=expected or None,
        )
    except (r2.R2Refusal, r6.R6Refusal, R4Refusal, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
