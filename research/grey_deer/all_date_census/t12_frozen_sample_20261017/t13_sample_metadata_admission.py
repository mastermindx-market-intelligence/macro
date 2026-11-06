"""Post-observation index-only admission map from exact frozen T12 metadata.

Root must freeze this source and its adopted contract before first execution.
No builder import, labels, prices, features, fits, trial ledger or network.
Exit 0 means a diagnostic artifact was emitted, never model admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

EXPECTED_SAMPLE_SHA256 = "944e0054b724aef775a5073ee8a1537779b464454a304acf4a4b396cd818a583"
EXPECTED_RECEIPT_SHA256 = "ad8a1f5fe92fb12690a25794f917619a2e113baaf9a07fc3f446207020340d4f"
EXPECTED_CLOSE_SHA256 = "60f0d81c686fce6e03ace59c9549d9cd28713b10973b2d2711fc465740fd0bc8"
EXPECTED_OHLCV_SHA256 = "c686f0bc683f3109c1be5431cab99661734f2481fc98e8479320e285507be6fb"
EXPECTED_BLOBS = {
    "scripts/research/grey_deer_episode_samples.py": "0a0eecb98e743b780db1ee3b0382e268d592fa67",
    "research/grey_deer/EPISODE_SAMPLE_SPEC_2026-10-13.md": "fe68838867982e845297aeb0daf518e0387120f9",
    "scripts/research/grey_deer_pullback_stage1.py": "76d231d6d12c8693cd07a2540b360c24f6c50b42",
}
N = 1321
WARM = 63
PRE = 21
HORIZONS = (5, 10, 21)
REQUESTED_CONTROLS = 3
BUFFER = 63


def require(ok: bool, detail: str) -> None:
    if not ok:
        raise ValueError("REFUSE_METADATA_IDENTITY_OR_STRUCTURE: " + detail)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def interval_overlap(a: list[int], b: list[int]) -> list[int] | None:
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return [lo, hi] if lo <= hi else None


def size(interval: list[int] | None) -> int:
    return 0 if interval is None else interval[1] - interval[0] + 1


def eligible_band(h: int) -> list[int]:
    return [WARM, N - 1 - h]


def positive_bounds(episode: dict, retained: list[int] | None) -> dict:
    """Bound retained positives using frozen count and boundary metadata only."""
    k = episode["n_event_origins"]
    lo, hi = episode["window_idx"]
    h = episode["horizon"]
    if lo == 0 or hi == N - 1:
        return {
            "first_positive_idx": None, "last_positive_idx": None,
            "retained_positive_count": None, "lower_bound": 0,
            "upper_bound": min(k, size(retained)),
            "basis": "UNKNOWN_CLIPPED_POSITIVE_BOUNDARIES",
        }
    first, last = lo + PRE, hi - h
    require(lo <= first <= last <= hi, "positive boundary inverse invalid")
    require(1 <= k <= last - first + 1, "positive count impossible in span")
    require((first == last) == (k == 1), "first/last/count inconsistent")
    require(last + h < N, "recorded positive boundary is immature")
    span = [first, last]
    inside = size(interval_overlap(span, retained)) if retained else 0
    outside = size(span) - inside
    boundaries = set((first, last))
    known_inside = sum(retained is not None and retained[0] <= i <= retained[1]
                       for i in boundaries)
    known_outside = len(boundaries) - known_inside
    lower = max(known_inside, k - outside, 0)
    upper = min(inside, k - known_outside, k)
    require(0 <= lower <= upper <= k, "positive bounds inconsistent")
    return {
        "first_positive_idx": first, "last_positive_idx": last,
        "retained_positive_count": lower if lower == upper else None,
        "lower_bound": lower, "upper_bound": upper,
        "basis": "ORIGINAL_COUNT_AND_PINNED_PADDING_INVERSE",
    }


def inspect_metadata(sample_raw: bytes, receipt_raw: bytes) -> dict:
    require(sha256(sample_raw) == EXPECTED_SAMPLE_SHA256, "sample SHA256 mismatch")
    require(len(sample_raw) == 6359, "sample size mismatch")
    require(sha256(receipt_raw) == EXPECTED_RECEIPT_SHA256, "receipt SHA256 mismatch")
    sample, receipt = json.loads(sample_raw), json.loads(receipt_raw)
    require(json.dumps(sample, sort_keys=True).encode("utf-8") == sample_raw,
            "noncanonical sample bytes")
    identity = {
        "schema": "grey_deer_episode_samples.v1", "ticker": "SPY",
        "seed": 20261013, "n_sessions": N,
        "first": "2021-07-06", "last": "2026-10-07",
        "input_sha256": EXPECTED_CLOSE_SHA256,
    }
    require(all(sample.get(k) == v for k, v in identity.items()), "sample identity mismatch")
    require(set(sample["horizons"]) == {str(h) for h in HORIZONS}, "horizons mismatch")
    require(receipt["sample_sha256"] == EXPECTED_SAMPLE_SHA256, "receipt sample mismatch")
    require(receipt["sample_identity"] == identity, "receipt identity mismatch")
    require(receipt["input_admission"]["normalized"]["sha256"] == EXPECTED_OHLCV_SHA256,
            "normalized input identity mismatch")
    require(all(receipt["source_pins"][path]["blob"] == blob
                for path, blob in EXPECTED_BLOBS.items()), "source pin mismatch")

    date_by_index: dict[int, str] = {}
    date_sources: dict[int, list[str]] = {}

    def bind_date(i: int, date: str, source: str) -> None:
        require(0 <= i < N and isinstance(date, str)
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) is not None,
                "invalid metadata date binding")
        require(i not in date_by_index or date_by_index[i] == date,
                "conflicting date at index " + str(i))
        date_by_index[i] = date
        date_sources.setdefault(i, []).append(source)

    bind_date(0, sample["first"], "sample.first")
    bind_date(N - 1, sample["last"], "sample.last")
    windows: list[dict] = []
    episodes_by_id: dict[str, dict] = {}
    controls_by_episode: dict[str, list[dict]] = {}
    horizon_summary: list[dict] = []

    for h in HORIZONS:
        group = sample["horizons"][str(h)]
        previous_hi = -1
        for j, original in enumerate(group["episodes"]):
            ep = dict(original, horizon=h, role="EPISODE_WINDOW",
                      window_id=original["episode_id"], control_id=None)
            lo, hi = ep["window_idx"]
            require(type(lo) is int and type(hi) is int and 0 <= lo <= hi < N,
                    "episode interval invalid")
            require(lo > previous_hi, "episode order or overlap invalid")
            require(ep["episode_id"] == f"h{h}-e{j:03d}", "episode ID invalid")
            previous_hi = hi
            episodes_by_id[ep["episode_id"]] = ep
            controls_by_episode[ep["episode_id"]] = []
            windows.append(ep)
            bounds = positive_bounds(ep, eligible_band(h))
            if bounds["first_positive_idx"] is not None:
                bind_date(bounds["first_positive_idx"], ep["first_event"], ep["window_id"] + ".first_event")
                bind_date(bounds["last_positive_idx"], ep["last_event"], ep["window_id"] + ".last_event")
        controls: list[dict] = []
        for original in group["controls"]:
            control = dict(original, horizon=h, role="CONTROL_WINDOW",
                           window_id=original["control_id"])
            parent = episodes_by_id.get(control["episode_id"])
            require(parent is not None and parent["horizon"] == h, "control parent invalid")
            lo, hi = control["window_idx"]
            require(type(lo) is int and type(hi) is int and 0 <= lo <= hi < N,
                    "control interval invalid")
            require(size(control["window_idx"]) == size(parent["window_idx"]), "control length drift")
            attached = controls_by_episode[control["episode_id"]]
            require(control["control_id"] == f'{control["episode_id"]}-c{len(attached):03d}',
                    "control placement ID invalid")
            require(control["seed"] == sample["seed"], "control seed mismatch")
            require(control["month_matched"] == (control["window"][0][5:7] == parent["window"][0][5:7]),
                    "month-match flag mismatch")
            require(all(interval_overlap([lo - BUFFER, hi + BUFFER], ep["window_idx"]) is None
                        for ep in group["episodes"]), "control/episode buffer intersection")
            require(all(interval_overlap(control["window_idx"], other["window_idx"]) is None
                        for other in controls), "controls overlap within horizon")
            require(len(attached) < REQUESTED_CONTROLS, "too many attached controls")
            attached.append(control)
            controls.append(control)
            windows.append(control)
        requested = len(group["episodes"]) * REQUESTED_CONTROLS
        require(group["shortfall"] == requested - len(controls), "shortfall mismatch")
        horizon_summary.append({
            "horizon": h, "episodes": len(group["episodes"]),
            "original_positive_origins": sum(ep["n_event_origins"] for ep in group["episodes"]),
            "requested_controls": requested, "placed_controls": len(controls),
            "original_shortfall": group["shortfall"],
            "original_requested_allocation": "COMPLETE" if group["shortfall"] == 0 else "INCOMPLETE_REQUESTED_ALLOCATION",
            "independent_episode_count": None,
        })

    for window in windows:
        lo, hi = window["window_idx"]
        bind_date(lo, window["window"][0], window["window_id"] + ".window_start")
        bind_date(hi, window["window"][1], window["window_id"] + ".window_end")
    known = sorted(date_by_index.items())
    require(all(a[1] < b[1] for a, b in zip(known, known[1:])), "metadata date order invalid")

    origin_rows: list[dict] = []
    window_summary: list[dict] = []
    for window in windows:
        h = window["horizon"]
        lo, hi = window["window_idx"]
        kept = interval_overlap([lo, hi], eligible_band(h))
        window_summary.append({
            "horizon": h, "window_id": window["window_id"], "role": window["role"],
            "episode_id": window["episode_id"], "control_id": window["control_id"],
            "original_window_idx": [lo, hi], "original_window_dates": window["window"],
            "window_origin_count": hi - lo + 1, "candidate_origin_count": size(kept),
            "candidate_origin_idx_band": kept,
            "pre_warmup_origin_count": size(interval_overlap([lo, hi], [0, WARM - 1])),
            "immature_origin_count": size(interval_overlap([lo, hi], [N - h, N - 1])),
            "positive_support": positive_bounds(window, kept) if window["role"] == "EPISODE_WINDOW" else None,
            "month_matched": window.get("month_matched"),
            "score_admitted": False,
        })
        for i in range(lo, hi + 1):
            warm, mature = i >= WARM, i + h < N
            reasons = ([] if warm else ["PRE_WARMUP"]) + ([] if mature else ["IMMATURE"])
            origin_rows.append({
                "horizon": h, "window_id": window["window_id"], "role": window["role"],
                "episode_id": window["episode_id"], "control_id": window["control_id"],
                "origin_idx": i, "within_window_offset": i - lo,
                "original_window_idx": [lo, hi],
                "date": date_by_index.get(i), "date_metadata_sources": date_sources.get(i, []),
                "warm": warm, "mature": mature, "candidate_window_origin": warm and mature,
                "index_exclusion_reasons": reasons,
                "label": None, "feature_availability": None, "score_admitted": False,
            })

    pair_summary: list[dict] = []
    episode_summary: list[dict] = []
    for ep in episodes_by_id.values():
        h = ep["horizon"]
        lo, hi = ep["window_idx"]
        ep_kept = interval_overlap([lo, hi], eligible_band(h))
        event_support = positive_bounds(ep, ep_kept)
        controls = controls_by_episode[ep["episode_id"]]
        attached_pairs: list[dict] = []
        for control in controls:
            clo, chi = control["window_idx"]
            c_kept = interval_overlap([clo, chi], eligible_band(h))
            offset_lo = max(0, WARM - lo, WARM - clo)
            offset_hi = min(hi - lo, N - 1 - h - lo, N - 1 - h - clo)
            offsets = [offset_lo, offset_hi] if offset_lo <= offset_hi else None
            event_band = [lo + offsets[0], lo + offsets[1]] if offsets else None
            common_support = positive_bounds(ep, event_band)
            pair = {
                "horizon": h, "episode_id": ep["episode_id"], "control_id": control["control_id"],
                "candidate_control_origins": size(c_kept),
                "control_fully_eligible": size(c_kept) == chi - clo + 1,
                "role_supported": event_support["lower_bound"] > 0 and size(c_kept) > 0,
                "common_offset_band": offsets, "common_offset_origin_count": size(offsets),
                "event_positive_support_at_common_offsets": common_support,
                "common_offset_supported": common_support["lower_bound"] > 0,
                "month_matched": control["month_matched"],
            }
            pair_summary.append(pair)
            attached_pairs.append(pair)
        episode_summary.append({
            "horizon": h, "episode_id": ep["episode_id"],
            "original_positive_origins": ep["n_event_origins"],
            "positive_support": event_support,
            "requested_controls": REQUESTED_CONTROLS, "placed_controls": len(controls),
            "original_shortfall": REQUESTED_CONTROLS - len(controls),
            "controls_with_candidate_origins": sum(p["candidate_control_origins"] > 0 for p in attached_pairs),
            "fully_eligible_controls": sum(p["control_fully_eligible"] for p in attached_pairs),
            "role_supported_pairs": sum(p["role_supported"] for p in attached_pairs),
            "common_offset_supported_pairs": sum(p["common_offset_supported"] for p in attached_pairs),
            "all_three_common_offset_supported": sum(p["common_offset_supported"] for p in attached_pairs) == REQUESTED_CONTROLS,
            "independent_episode_count": None,
        })
    for row in horizon_summary:
        eps = [ep for ep in episode_summary if ep["horizon"] == row["horizon"]]
        pairs = [p for p in pair_summary if p["horizon"] == row["horizon"]]
        role_count = sum(p["role_supported"] for p in pairs)
        offset_count = sum(p["common_offset_supported"] for p in pairs)
        row.update({
            "episodes_with_established_positive_support": sum(ep["positive_support"]["lower_bound"] > 0 for ep in eps),
            "episodes_with_role_supported_control": sum(ep["role_supported_pairs"] > 0 for ep in eps),
            "episodes_with_common_offset_supported_control": sum(ep["common_offset_supported_pairs"] > 0 for ep in eps),
            "episodes_with_three_common_offset_supported_controls": sum(ep["all_three_common_offset_supported"] for ep in eps),
            "role_supported_pairs": role_count, "common_offset_supported_pairs": offset_count,
            "minimal_role_support": "NECESSARY_SUPPORT_PRESENT_NOT_POWER" if role_count else "REFUSE_NO_ESTABLISHED_MATCHED_SUPPORT",
            "minimal_common_offset_support": "NECESSARY_SUPPORT_PRESENT_NOT_POWER" if offset_count else "REFUSE_NO_ESTABLISHED_MATCHED_SUPPORT",
            "confirmatory_model_admission": "NOT_ADMITTED",
        })

    overlaps: list[dict] = []
    for j, a in enumerate(windows):
        for b in windows[j + 1:]:
            if a["horizon"] == b["horizon"]:
                continue
            intersection = interval_overlap(a["window_idx"], b["window_idx"])
            if intersection is not None:
                overlaps.append({
                    "a": {k: a[k] for k in ("horizon", "window_id", "role", "episode_id")},
                    "b": {k: b[k] for k in ("horizon", "window_id", "role", "episode_id")},
                    "intersection_idx": intersection, "intersection_origin_count": size(intersection),
                    "independent_replication": False,
                })
    return {
        "schema": "grey_deer.t13_sample_metadata_admission.v1",
        "design_status": "POST_OBSERVATION_ADMISSION_DIAGNOSTIC",
        "metadata_diagnostic": "ACCEPTED_EXACT_IDENTITY_AND_STRUCTURE",
        "sample_sha256": EXPECTED_SAMPLE_SHA256, "receipt_sha256": EXPECTED_RECEIPT_SHA256,
        "sample_identity": identity, "warm_idx": WARM,
        "calendar_identity": "BOUND_BY_INPUT_DIGEST_FULL_DATE_VECTOR_NOT_PRESENT",
        "labels_recomputed": False, "labels_emitted": False,
        "sample_regenerated": False, "feature_join_performed": False,
        "fits": 0, "trial_writes": 0, "fit_admitted": False,
        "source_purpose": "UNKNOWN", "feature_admission": "HOLD_SOURCE_PURPOSE_AND_EXACT_AVAILABILITY",
        "confirmatory_model_admission": "NOT_ADMITTED",
        "independent_episode_count": None,
        "model_admission_unresolved": [
            "SOURCE_PURPOSE_UNKNOWN", "EXACT_FULL_CALENDAR_NOT_BOUND_FOR_JOIN",
            "EXACT_ORIGINAL_LABEL_VECTOR_NOT_ADMITTED", "CHRONOLOGICAL_EVALUATION_NOT_FROZEN",
            "INDEPENDENCE_AND_POWER_NOT_ESTABLISHED", "MODEL_AND_UTILITY_GATES_NOT_FROZEN",
        ],
        "horizons": horizon_summary, "episodes": episode_summary,
        "pairs": pair_summary, "windows": window_summary,
        "cross_horizon_window_overlaps": overlaps, "origins": origin_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-f]{40}", args.freeze_commit) is not None, "freeze commit syntax")
    contract_raw = args.contract.read_bytes()
    require(sha256(contract_raw) == args.contract_sha256, "adopted contract SHA256 mismatch")
    require(args.output.resolve() not in {args.sample.resolve(), args.receipt.resolve(), args.contract.resolve(), Path(__file__).resolve()},
            "output aliases an input")
    result = inspect_metadata(args.sample.read_bytes(), args.receipt.read_bytes())
    result["provenance"] = {
        "diagnostic_source_sha256": sha256(Path(__file__).read_bytes()),
        "adopted_contract_sha256": args.contract_sha256,
        "root_declared_freeze_commit": args.freeze_commit,
        "commit_independently_verified_by_diagnostic": False,
    }
    raw = (json.dumps(result, sort_keys=True, indent=2) + "\n").encode("utf-8")
    with args.output.open("xb") as stream:
        stream.write(raw)
    print(json.dumps({
        "output_sha256": sha256(raw), "bytes": len(raw),
        "metadata_diagnostic": result["metadata_diagnostic"],
        "fit_admitted": False, "horizons": result["horizons"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
