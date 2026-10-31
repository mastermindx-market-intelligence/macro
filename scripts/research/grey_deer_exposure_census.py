"""Complete date-by-exposure census under GD-T12-CENSUS-20261017-v1.

Research only. No collector, fit, prospective issuance, policy or publisher.
Observed features and future labels are separately prefixed. Existing T12
episode logic is reused within contiguous valid-source segments.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.research import grey_deer_episode_samples as t12  # noqa: E402

SCHEMA = "grey_deer.all_date_census.v1"
HORIZONS = (5, 10, 21)
PROTOCOL_ID = "GD-T12-CENSUS-20261017-v1"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def valid_price(s: pd.Series) -> pd.Series:
    return pd.Series(np.isfinite(s.to_numpy(dtype=float)), index=s.index) & s.gt(0)


def strict_return(s: pd.Series, h: int) -> pd.Series:
    ok = valid_price(s).rolling(h + 1, min_periods=h + 1).sum().eq(h + 1)
    return (s / s.shift(h) - 1).where(ok)


def observed_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Past/current data only; no outcomes, future episode IDs or fitting."""
    tr = frame["close"].where(valid_price(frame["close"]))
    price = frame["close_price"].where(valid_price(frame["close_price"]))
    out = pd.DataFrame(index=frame.index)
    for h in (1, 2, 5, 20, 63):
        out[f"obs_tr_return_{h}"] = strict_return(tr, h)
    for h in (63, 252):
        out[f"obs_price_dd_{h}"] = price / price.rolling(h, min_periods=h).max() - 1
    for h in (20, 200):
        out[f"obs_price_sma_gap_{h}"] = price / price.rolling(h, min_periods=h).mean() - 1
    dd = out["obs_price_dd_63"]
    damage = dd.le(-0.05).astype("boolean").where(dd.notna())
    out["obs_damage_5pct"] = damage
    out["obs_damage_onset_5pct"] = (
        damage & ~damage.shift(1)
    ).where(damage.notna() & damage.shift(1).notna())
    recent_damage = damage.astype("Float64").rolling(21, min_periods=21).max()
    repair_ok = (
        recent_damage.notna()
        & out["obs_price_sma_gap_20"].notna()
        & out["obs_tr_return_5"].notna()
    )
    out["obs_stabilization_candidate"] = (
        recent_damage.gt(0)
        & out["obs_price_sma_gap_20"].gt(0)
        & out["obs_tr_return_5"].gt(0)
    ).astype("boolean").where(repair_ok)
    out["obs_large_tr_move_audit"] = (
        np.log(tr / tr.shift(1)).abs() > math.log(1.25)
    ).astype("boolean").where(tr.notna() & tr.shift(1).notna())
    return out


def origin_states(frame: pd.DataFrame, source_index: pd.DatetimeIndex) -> pd.Series:
    states = pd.Series("MISSING_SOURCE_SESSION", index=frame.index, dtype="object")
    if len(source_index) == 0:
        return pd.Series("SOURCE_ABSENT", index=frame.index, dtype="object")
    states.loc[frame.index < source_index.min()] = "PRE_SOURCE_COVERAGE"
    states.loc[frame.index > source_index.max()] = "POST_SOURCE_COVERAGE"
    present = frame.index.isin(source_index)
    good = valid_price(frame["close"]) & valid_price(frame["close_price"])
    states.loc[present & ~good] = "PRICE_INVALID"
    states.loc[present & good] = "OBSERVED"
    return states


def future_labels(tr: pd.Series, states: pd.Series) -> pd.DataFrame:
    """Label support must contain origin and every future reference session."""
    s = tr.where(valid_price(tr) & states.eq("OBSERVED"))
    inherited = t12.stage1.build_labels(s)
    result = pd.DataFrame(index=s.index)
    n = len(s)
    observed = states.eq("OBSERVED")
    for h in HORIZONS:
        complete = valid_price(s).rolling(h + 1, min_periods=h + 1).sum().shift(-h).eq(h + 1)
        mature = pd.Series(np.arange(n) + h < n, index=s.index)
        status = pd.Series("ELIGIBLE", index=s.index, dtype="object")
        status.loc[~complete] = "GAP_WINDOW"
        status.loc[~mature] = "IMMATURE_CALENDAR"
        status.loc[~observed] = "ORIGIN_" + states.loc[~observed]
        eligible = status.eq("ELIGIBLE")
        result[f"out_status_{h}"] = status
        result[f"out_mfl_{h}"] = inherited[h]["A"].where(eligible)
        result[f"out_loss_5pct_{h}"] = inherited[h]["Y"].astype("boolean").where(eligible)
        result[f"out_label_end_{h}"] = pd.Series(s.index, index=s.index).shift(-h).where(eligible)
    eligible = result["out_status_21"].eq("ELIGIBLE")
    future = pd.concat([s.shift(-k) / s - 1 for k in range(1, 22)], axis=1)
    gain = future.ge(0.05).to_numpy()
    loss = future.le(-0.05).to_numpy()
    first_gain = np.where(gain.any(axis=1), gain.argmax(axis=1) + 1, 22)
    first_loss = np.where(loss.any(axis=1), loss.argmax(axis=1) + 1, 22)
    path = np.where(first_gain < first_loss, "GAIN_FIRST",
                    np.where(first_loss < first_gain, "LOSS_FIRST", "NEITHER"))
    result["out_competing_path_21"] = pd.Series(path, index=s.index).where(
        eligible, result["out_status_21"])
    return result


def contiguous_segments(valid: pd.Series) -> list[tuple[int, int]]:
    pos = np.flatnonzero(valid.to_numpy(dtype=bool))
    if not len(pos):
        return []
    groups = np.split(pos, np.flatnonzero(np.diff(pos) > 1) + 1)
    return [(int(g[0]), int(g[-1]) + 1) for g in groups]


def recipient_episodes(tr: pd.Series, ticker: str, states: pd.Series) -> list[dict]:
    """T12 outcome annotations; never known at first/last event origin."""
    tr = tr.where(valid_price(tr) & states.eq("OBSERVED"))
    episodes = []
    for segment, (lo, hi) in enumerate(contiguous_segments(valid_price(tr))):
        close = tr.iloc[lo:hi]
        for h in HORIZONS:
            for ep in t12.event_episodes(close, h):
                first = int(tr.index.get_loc(pd.Timestamp(ep["first_event"])))
                last = int(tr.index.get_loc(pd.Timestamp(ep["last_event"])))
                episodes.append({
                    **ep,
                    "episode_id": f"{ticker}-s{segment}-{ep['episode_id']}",
                    "ticker": ticker, "horizon": h,
                    "window_idx": [lo + ep["window_idx"][0], lo + ep["window_idx"][1]],
                    "first_event_idx": first, "last_event_idx": last,
                    "outcome_support_idx": [first, last + h],
                    "independence": "NOT_ESTABLISHED",
                    "known_at": None,
                    "annotation_role": "POST_OUTCOME",
                })
    return episodes


def dependence_groups(episodes: list[dict], h: int) -> list[dict]:
    """Overlap of future support is dependence, not a count of independent crises."""
    eps = sorted((e for e in episodes if e["horizon"] == h),
                 key=lambda e: tuple(e["outcome_support_idx"]))
    groups = []
    for ep in eps:
        lo, hi = ep["outcome_support_idx"]
        if groups and lo <= groups[-1]["support_idx"][1]:
            group = groups[-1]
            group["support_idx"][1] = max(group["support_idx"][1], hi)
            group["recipient_episode_ids"].append(ep["episode_id"])
        else:
            groups.append({"support_idx": [lo, hi],
                           "recipient_episode_ids": [ep["episode_id"]]})
    return groups


def rotation_shape(num: float, den: float) -> str | None:
    if not (np.isfinite(num) and np.isfinite(den)):
        return None
    if num < 0 and den < 0:
        return "BOTH_DOWN_RELATIVE_COMPARISON_ONLY"
    if num > 0 and den < 0:
        return "RECEIVER_UP_DONOR_DOWN_PRICE_DIVERGENCE"
    if num < 0 and den > 0:
        return "RECEIVER_DOWN_DONOR_UP"
    if num > 0 and den > 0:
        return "BOTH_UP"
    return "FLAT_COMPONENT"


def clean_json(value):
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean_json(v) for v in value]
    if value is pd.NA or value is pd.NaT or value is None:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return value


def summarise(rows: pd.DataFrame, episodes: list[dict]) -> dict:
    counts = {}
    for h in HORIZONS:
        eligible = rows[f"out_status_{h}"].eq("ELIGIBLE")
        y = rows[f"out_loss_5pct_{h}"].fillna(False).astype(bool)
        observed = rows["obs_damage_5pct"].notna()
        gate_known = rows["obs_spy_gate_component"].notna()
        comparable = eligible & observed & gate_known
        damage = rows["obs_damage_5pct"].fillna(False).astype(bool)
        gate = rows["obs_spy_gate_component"].fillna(False).astype(bool)
        policies = {}
        for name, alert in [
            ("damage_flag", damage),
            ("damage_and_spy_component", damage & gate),
        ]:
            subset = comparable
            active = subset & alert
            policies[name] = {
                "comparable_origins": int(subset.sum()),
                "positive_outcomes": int((subset & y).sum()),
                "flag_days": int(active.sum()),
                "flag_with_further_loss": int((active & y).sum()),
                "flag_without_further_loss": int((active & ~y).sum()),
                "unflagged_further_loss": int((subset & ~alert & y).sum()),
                "interpretation": "EXPLORATORY_ASSOCIATION_NOT_VALIDATED_WARNING",
            }
        counts[str(h)] = {
            "status_counts": rows[f"out_status_{h}"].value_counts().to_dict(),
            "eligible": int(eligible.sum()),
            "positive_outcome_origins": int((eligible & y).sum()),
            "negative_outcome_origins": int((eligible & ~y).sum()),
            "recipient_episodes": sum(e["horizon"] == h for e in episodes),
            "verified_independent_episodes": None,
            "policies": policies,
        }
    damage_known = rows["obs_damage_5pct"].notna()
    damage = rows["obs_damage_5pct"].fillna(False).astype(bool)
    gate_known = rows["obs_spy_gate_component"].notna()
    gate = rows["obs_spy_gate_component"].fillna(False).astype(bool)
    repair = rows["obs_stabilization_candidate"].fillna(False).astype(bool)
    return {
        "rows": len(rows), "origin_status_counts": rows["origin_status"].value_counts().to_dict(),
        "damage_known_origins": int(damage_known.sum()),
        "damage_flag_days": int(damage.sum()),
        "damage_days_spy_component_off": int((damage & gate_known & ~gate).sum()),
        "observed_damage_onsets": int(rows["obs_damage_onset_5pct"].fillna(False).sum()),
        "large_move_audit_count": int(rows["obs_large_tr_move_audit"].fillna(False).sum()),
        "horizons": counts,
        "stabilization_candidate_path_counts": rows.loc[repair, "out_competing_path_21"].value_counts().to_dict(),
    }


def verify_method_dependencies(repo: Path, source_commit: str) -> list[dict]:
    """Bind the files actually imported, not just the frozen price objects."""
    modules = {
        "scripts/research/grey_deer_episode_samples.py": t12,
        "scripts/research/grey_deer_pullback_stage1.py": t12.stage1,
        "lib/observed_moves.py": t12.stage1.om,
    }
    receipts = []
    for relative, module in modules.items():
        loaded = Path(module.__file__).resolve()
        if loaded != (ROOT / relative).resolve():
            raise ValueError(f"METHOD_IMPORT_PATH_MISMATCH:{relative}")
        expected = subprocess.check_output(
            ["git", "-C", str(repo), "show", f"{source_commit}:{relative}"])
        actual = loaded.read_bytes()
        if sha256(actual) != sha256(expected):
            raise ValueError(f"METHOD_SOURCE_MISMATCH:{relative}")
        receipts.append({
            "path": relative, "source_commit": source_commit,
            "sha256": sha256(actual),
            "git_blob_sha": hashlib.sha1(
                b"blob " + str(len(actual)).encode() + b"\0" + actual).hexdigest(),
        })
    return receipts


def load_inputs(repo: Path, protocol: dict) -> tuple[dict, list]:
    ref = protocol["source"]["commit"]
    metadata = {m["ticker"]: m for m in protocol["source"]["metadata"]}
    frames, receipts = {}, []
    for ticker in protocol["universe"]:
        path = f"data/yahoo/{ticker}.parquet"
        raw = subprocess.check_output(["git", "-C", str(repo), "show", f"{ref}:{path}"])
        digest = sha256(raw)
        if digest != metadata[ticker]["sha256"]:
            raise ValueError(f"SOURCE_HASH_MISMATCH:{ticker}")
        frame = pd.read_parquet(io.BytesIO(raw))
        frame.index = pd.DatetimeIndex(pd.to_datetime(frame.index)).tz_localize(None).normalize()
        if frame.index.has_duplicates:
            raise ValueError(f"DUPLICATE_SOURCE_DATE:{ticker}")
        if not frame.index.is_monotonic_increasing:
            raise ValueError(f"UNSORTED_SOURCE_DATE:{ticker}")
        if not {"close", "close_price"}.issubset(frame):
            raise ValueError(f"DUAL_BASIS_ABSENT:{ticker}")
        frames[ticker] = frame[["close", "close_price"]].astype(float)
        receipts.append({"ticker": ticker, "source_path": path, "sha256": digest,
                         "rows": len(frame), "first": str(frame.index.min().date()),
                         "last": str(frame.index.max().date())})
    return frames, receipts


def build_census(frames: dict, protocol: dict) -> tuple[pd.DataFrame, dict, list, pd.DataFrame]:
    c = protocol["calendar"]
    calendar = frames["SPY"].index
    calendar = calendar[(calendar >= c["start"]) & (calendar <= c["cutoff"])]
    spy = frames["SPY"].reindex(calendar)["close"]
    spy = spy.where(valid_price(spy))
    spy_ma = spy.rolling(200, min_periods=200).mean()
    spy_gate = spy.lt(spy_ma).astype("boolean").where(spy_ma.notna() & valid_price(spy))
    outputs, episodes, per_exposure = [], [], {}
    for ticker, exposure in protocol["universe"].items():
        original = frames[ticker]
        frame = original.reindex(calendar)
        obs = observed_features(frame)
        states = origin_states(frame, original.index)
        labels = future_labels(frame["close"], states)
        rows = pd.concat([obs, labels], axis=1)
        rows.insert(0, "origin_status", states)
        rows.insert(0, "exposure", exposure)
        rows.insert(0, "ticker", ticker)
        rows["obs_spy_gate_component"] = spy_gate
        rows.index.name = "date"
        eps = recipient_episodes(frame["close"], ticker, states)
        per_exposure[ticker] = summarise(rows, eps)
        outputs.append(rows.reset_index())
        episodes.extend(eps)
    combined = pd.concat(outputs, ignore_index=True)
    expected_rows = len(calendar) * len(protocol["universe"])
    if len(combined) != expected_rows:
        raise AssertionError("LATTICE_CARDINALITY")
    summary = {
        "schema": SCHEMA, "qualification": "RETROSPECTIVE_EXPLORATORY_NO_PROMOTION",
        "calendar_sessions": len(calendar), "exposures": len(protocol["universe"]),
        "expected_lattice_rows": expected_rows, "all": summarise(combined, episodes),
        "per_exposure": per_exposure, "dependence": {},
    }
    for h in HORIZONS:
        groups = dependence_groups(episodes, h)
        summary["dependence"][str(h)] = {
            "calendar_support_groups": len(groups), "groups": groups,
            "verified_independent_episodes": None,
            "note": "Overlapping support components; neither groups nor recipient sums prove independence.",
        }
    indexed = combined.set_index(["ticker", "date"])
    rotations = []
    for num, den in protocol["comparisons"]["rotation_pairs"]:
        for h in protocol["comparisons"]["rotation_horizons"]:
            a = indexed.loc[num, f"obs_tr_return_{h}"]
            b = indexed.loc[den, f"obs_tr_return_{h}"]
            for date in calendar:
                av, bv = a.loc[date], b.loc[date]
                ratio = (1 + av) / (1 + bv) - 1 if pd.notna(av) and pd.notna(bv) else np.nan
                rotations.append({
                    "date": date, "numerator": num, "denominator": den, "sessions": h,
                    "numerator_tr_return": av, "denominator_tr_return": bv,
                    "ratio_return": ratio, "shape": rotation_shape(av, bv),
                    "measured_flow": False,
                })
    return combined, summary, episodes, pd.DataFrame(rotations)


def write_csv_gz(path: Path, frame: pd.DataFrame):
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as out:
                frame.to_csv(out, index=False, float_format="%.8g", date_format="%Y-%m-%d")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--expected-protocol-sha", required=True)
    ap.add_argument("--source-repo", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    raw_protocol = args.protocol.read_bytes()
    digest = sha256(raw_protocol)
    if digest != args.expected_protocol_sha:
        raise ValueError("PROTOCOL_HASH_MISMATCH")
    protocol = json.loads(raw_protocol)
    if protocol["protocol_id"] != PROTOCOL_ID:
        raise ValueError("UNSUPPORTED_PROTOCOL")
    if args.output.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    dependencies = verify_method_dependencies(args.source_repo, protocol["source"]["commit"])
    frames, sources = load_inputs(args.source_repo, protocol)
    rows, summary, episodes, rotation = build_census(frames, protocol)
    args.output.mkdir(parents=True)
    write_csv_gz(args.output / "origins.csv.gz", rows)
    write_csv_gz(args.output / "rotation.csv.gz", rotation)
    case = protocol["comparisons"]["date_case"]
    case_rows = rows[rows["date"].between(case["start"], case["end"])]
    case_rows.to_csv(args.output / "september_october_origins.csv", index=False,
                     float_format="%.8g", date_format="%Y-%m-%d")
    rotation[rotation["date"].between(case["start"], case["end"])].to_csv(
        args.output / "september_october_rotation.csv", index=False,
        float_format="%.8g", date_format="%Y-%m-%d")
    for name, value in [("summary.json", summary), ("episodes.json", episodes)]:
        (args.output / name).write_text(json.dumps(clean_json(value), sort_keys=True,
                                                  indent=2, allow_nan=False) + "\n")
    manifest = {
        "schema": SCHEMA, "protocol_id": PROTOCOL_ID, "protocol_sha256": digest,
        "source_commit": protocol["source"]["commit"],
        "script_sha256": sha256(Path(__file__).read_bytes()),
        "method_dependencies": dependencies,
        "code_commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "source_receipts": sources,
        "artifact_sha256": {p.name: sha256(p.read_bytes()) for p in sorted(args.output.iterdir())},
        "authority": {"rank": False, "gate": False, "size": False, "execute": False},
        "historical_availability": "UNKNOWN",
        "predictive_claims_promoted": 0, "new_model_fits": 0,
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "rows": len(rows),
                      "calendar_sessions": summary["calendar_sessions"],
                      "exposures": summary["exposures"],
                      "artifact_bytes": {p.name: p.stat().st_size for p in args.output.iterdir()}},
                     sort_keys=True))


if __name__ == "__main__":
    main()
