"""Research-only driver-conditioned transition study after large 10Y impulses."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine import pit
from engine import treasury_supply
from engine.trial_ledger import TrialLedger

FAMILY = "ric_rate_shock_driver_transition_v1"
START = "2017-01-03"
END = "2025-12-31"
PRIMARY_START = "2022-01-01"
LABELS = ("reversal", "no_hit", "continuation")
MODELS = (
    "unconditional",
    "impulse_direction",
    "decomposition",
    "decomp_term",
    "crossasset",
    "full",
)
SPEC = {
    "impulse_bars": 5,
    "threshold_history": 252,
    "threshold_quantile": 0.80,
    "threshold_floor_bp": 15.0,
    "volatility_bars": 20,
    "barrier_vol_scale": float(np.sqrt(5.0)),
    "barrier_floor_bp": 10.0,
    "horizon_bars": 10,
    "real_be_dominance_ratio": 1.5,
    "term_premium_state_bp": 5.0,
    "credit_state_bp": 10.0,
    "oil_state_pct": 3.0,
    "curve_state_bp": 10.0,
    "auction_recency_calendar_days": 3,
    "auction_trailing": 8,
    "auction_min_trailing": 5,
    "auction_strong_z": 0.6,
    "shrinkage": 12.0,
    "minimum_training_events": 30,
    "minimum_primary_events": 50,
    "minimum_subgroup_events": 20,
    "start": START,
    "end": END,
    "primary_start": PRIMARY_START,
    "primary_model": "decomp_term",
    "primary_baseline": "impulse_direction",
    "evidence_tier": "retrospective_seen_history_market_proxy_not_promotion",
}
DATA_PATHS = {
    "dgs10": ROOT / "data/fred/DGS10.parquet",
    "dgs2": ROOT / "data/fred/DGS2.parquet",
    "real10": ROOT / "data/fred/DFII10.parquet",
    "be10": ROOT / "data/fred/T10YIE.parquet",
    "oil": ROOT / "data/fred/DCOILWTICO.parquet",
    "hy": ROOT / "data/fred/BAMLH0A0HYM2.parquet",
    "vintages": ROOT / "data/fred_vintage/vintages.parquet",
    "auctions": ROOT / "data/treasury_auctions/auctions.parquet",
}
CODE_PATHS = (
    "research/rates_direction/rate_shock_driver_transition.py",
    "research/rates_direction/RATE_SHOCK_DRIVER_TRANSITION_V1.md",
    "tests/test_rate_shock_driver_transition.py",
    "engine/pit.py",
    "engine/treasury_supply.py",
)
FREEZE = ROOT / "research/rates_direction/rate_shock_driver_transition_freeze_v1.json"


def file_hash(path: Path | str) -> str:
    p = Path(path)
    h = sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _col(path: Path) -> pd.Series:
    df = pd.read_parquet(path)
    if df.shape[1] != 1:
        raise ValueError(f"one-column source required: {path}")
    s = pd.to_numeric(df.iloc[:, 0], errors="coerce").astype(float)
    s.index = pd.DatetimeIndex(s.index).tz_localize(None)
    if not s.index.is_monotonic_increasing or s.index.has_duplicates:
        raise ValueError(f"strict date order required: {path}")
    return s


def _state3(value: float, threshold: float, up: str, down: str, flat: str) -> str:
    if not np.isfinite(value):
        return "UNKNOWN"
    if value >= threshold:
        return up
    if value <= -threshold:
        return down
    return flat


def _driver_state(direction: int, real_bp: float, be_bp: float, ratio: float) -> str:
    if direction not in (-1, 1) or not np.isfinite(real_bp) or not np.isfinite(be_bp):
        return "UNKNOWN"
    real = direction * real_bp
    be = direction * be_bp
    eps = 1e-9
    if real > 0 and real >= ratio * max(be, eps):
        return "REAL"
    if be > 0 and be >= ratio * max(real, eps):
        return "INFLATION"
    if real > 0 and be > 0:
        return "MIXED"
    return "CONFLICT"


def _auction_history() -> pd.DataFrame:
    raw = pd.read_parquet(DATA_PATHS["auctions"])
    prep = treasury_supply._prep(raw)
    scored = treasury_supply._score_rows(
        prep,
        {
            "trailing": SPEC["auction_trailing"],
            "min_trailing": SPEC["auction_min_trailing"],
        },
    )
    scored = scored.dropna(subset=["auction_date"]).copy()
    scored["auction_date"] = pd.to_datetime(scored["auction_date"]).dt.normalize()
    return scored


def _auction_state(scored: pd.DataFrame, date: pd.Timestamp) -> str:
    prior = scored[scored["auction_date"] <= date]
    if prior.empty:
        return "NONE"
    latest_date = prior["auction_date"].max()
    if (date - latest_date).days > SPEC["auction_recency_calendar_days"]:
        return "NONE"
    same = prior[prior["auction_date"] == latest_date]
    vals = pd.to_numeric(same["absorption_z"], errors="coerce").dropna()
    if vals.empty:
        return "NONE"
    value = float(vals.mean())
    if value <= -SPEC["auction_strong_z"]:
        return "SOFT"
    if value >= SPEC["auction_strong_z"]:
        return "STRONG"
    return "INLINE"


def build_frame() -> pd.DataFrame:
    nominal = _col(DATA_PATHS["dgs10"]).rename("nominal")
    index = nominal.loc[START:END].dropna().index
    frame = pd.DataFrame(index=index)
    frame["nominal"] = nominal.reindex(index)
    frame["dgs2"] = _col(DATA_PATHS["dgs2"]).reindex(index).ffill(limit=3)
    frame["real10"] = _col(DATA_PATHS["real10"]).reindex(index).ffill(limit=3)
    frame["be10"] = _col(DATA_PATHS["be10"]).reindex(index).ffill(limit=3)
    frame["oil"] = _col(DATA_PATHS["oil"]).reindex(index).ffill(limit=5)
    frame["hy"] = _col(DATA_PATHS["hy"]).reindex(index).ffill(limit=3)

    vintages = pd.read_parquet(DATA_PATHS["vintages"])
    tp = pit.series(
        "term_premium_10y",
        as_of=END,
        basis="release",
        index=index,
        vintages=vintages,
    )
    frame["term_premium"] = pd.to_numeric(tp, errors="coerce")

    n = SPEC["impulse_bars"]
    frame["impulse_bp"] = frame["nominal"].diff(n) * 100.0
    frame["real_change_bp"] = frame["real10"].diff(n) * 100.0
    frame["be_change_bp"] = frame["be10"].diff(n) * 100.0
    frame["tp_change_bp"] = frame["term_premium"].diff(n) * 100.0
    frame["hy_change_bp"] = frame["hy"].diff(n) * 100.0
    frame["oil_change_pct"] = frame["oil"].pct_change(n, fill_method=None) * 100.0
    frame["curve_2s10s"] = (frame["nominal"] - frame["dgs2"]) * 100.0
    frame["curve_change_bp"] = frame["curve_2s10s"].diff(n)

    daily_bp = frame["nominal"].diff() * 100.0
    frame["vol20_bp"] = daily_bp.rolling(SPEC["volatility_bars"]).std()
    frame["barrier_bp"] = np.maximum(
        SPEC["barrier_floor_bp"],
        frame["vol20_bp"] * SPEC["barrier_vol_scale"],
    )
    rolling = (
        frame["impulse_bp"]
        .abs()
        .shift(1)
        .rolling(SPEC["threshold_history"], min_periods=SPEC["threshold_history"])
        .quantile(SPEC["threshold_quantile"])
    )
    frame["impulse_threshold_bp"] = np.maximum(SPEC["threshold_floor_bp"], rolling)
    frame["large_impulse"] = frame["impulse_bp"].abs() >= frame["impulse_threshold_bp"]
    frame["trigger"] = frame["large_impulse"] & ~frame["large_impulse"].shift(1).fillna(False)
    return frame


def label_event(frame: pd.DataFrame, i: int, direction: int) -> dict:
    barrier = float(frame["barrier_bp"].iloc[i])
    origin = float(frame["nominal"].iloc[i])
    end = min(len(frame) - 1, i + SPEC["horizon_bars"])
    if end - i < SPEC["horizon_bars"]:
        return {
            "label": "censored",
            "target_end_index": end,
            "target_end": frame.index[end].isoformat(),
            "barrier_bp": barrier,
        }
    hit_cont = None
    hit_rev = None
    max_cont = -np.inf
    max_rev = -np.inf
    for j in range(i + 1, end + 1):
        delta = direction * (float(frame["nominal"].iloc[j]) - origin) * 100.0
        max_cont = max(max_cont, delta)
        max_rev = max(max_rev, -delta)
        if hit_cont is None and delta >= barrier:
            hit_cont = j
        if hit_rev is None and delta <= -barrier:
            hit_rev = j
        if hit_cont is not None or hit_rev is not None:
            break
    if hit_cont is not None and hit_rev is not None and hit_cont == hit_rev:
        label = "ambiguous"
        first = hit_cont
    elif hit_cont is not None and (hit_rev is None or hit_cont < hit_rev):
        label = "continuation"
        first = hit_cont
    elif hit_rev is not None:
        label = "reversal"
        first = hit_rev
    else:
        label = "no_hit"
        first = None
    return {
        "label": label,
        "target_end_index": end,
        "target_end": frame.index[end].isoformat(),
        "first_hit_index": first,
        "first_hit": None if first is None else frame.index[first].isoformat(),
        "barrier_bp": barrier,
        "max_continuation_bp": float(max_cont),
        "max_reversal_bp": float(max_rev),
    }


def build_events(frame: pd.DataFrame) -> list[dict]:
    auctions = _auction_history()
    events = []
    blocked_through = -1
    for i, (date, row) in enumerate(frame.iterrows()):
        if i <= blocked_through or not bool(row["trigger"]):
            continue
        required = (
            row["impulse_bp"],
            row["real_change_bp"],
            row["be_change_bp"],
            row["barrier_bp"],
        )
        if not all(np.isfinite(float(x)) for x in required):
            continue
        direction = 1 if row["impulse_bp"] > 0 else -1
        outcome = label_event(frame, i, direction)
        blocked_through = outcome["target_end_index"]
        driver = _driver_state(
            direction,
            float(row["real_change_bp"]),
            float(row["be_change_bp"]),
            SPEC["real_be_dominance_ratio"],
        )
        tp_signed = direction * float(row["tp_change_bp"]) if np.isfinite(row["tp_change_bp"]) else np.nan
        event = {
            "origin_index": i,
            "origin": date.isoformat(),
            "direction": direction,
            "impulse_bp": float(row["impulse_bp"]),
            "threshold_bp": float(row["impulse_threshold_bp"]),
            "barrier_bp": float(row["barrier_bp"]),
            "driver_state": driver,
            "term_premium_state": _state3(
                tp_signed,
                SPEC["term_premium_state_bp"],
                "CONFIRM",
                "OPPOSE",
                "FLAT",
            ),
            "credit_state": _state3(
                float(row["hy_change_bp"]),
                SPEC["credit_state_bp"],
                "WIDEN",
                "TIGHTEN",
                "FLAT",
            ),
            "oil_state": _state3(
                float(row["oil_change_pct"]),
                SPEC["oil_state_pct"],
                "UP",
                "DOWN",
                "FLAT",
            ),
            "curve_state": _state3(
                float(row["curve_change_bp"]),
                SPEC["curve_state_bp"],
                "STEEPEN",
                "FLATTEN",
                "FLAT",
            ),
            "auction_state": _auction_state(auctions, date.normalize()),
            "real_change_bp": None if not np.isfinite(row["real_change_bp"]) else float(row["real_change_bp"]),
            "be_change_bp": None if not np.isfinite(row["be_change_bp"]) else float(row["be_change_bp"]),
            "tp_change_bp": None if not np.isfinite(row["tp_change_bp"]) else float(row["tp_change_bp"]),
            "hy_change_bp": None if not np.isfinite(row["hy_change_bp"]) else float(row["hy_change_bp"]),
            "oil_change_pct": None if not np.isfinite(row["oil_change_pct"]) else float(row["oil_change_pct"]),
            "curve_change_bp": None if not np.isfinite(row["curve_change_bp"]) else float(row["curve_change_bp"]),
            "outcome": outcome,
        }
        events.append(event)
    return events


def _counts(events: list[dict]) -> np.ndarray:
    c = Counter(e["outcome"]["label"] for e in events if e["outcome"]["label"] in LABELS)
    return np.array([c[x] for x in LABELS], dtype=float)


def _shrink(subset: list[dict], parent: np.ndarray) -> np.ndarray:
    counts = _counts(subset)
    n = float(counts.sum())
    w = SPEC["shrinkage"]
    return (counts + w * parent) / (n + w)


def _match(e: dict, origin: dict, fields: tuple[str, ...]) -> bool:
    return all(e.get(k) == origin.get(k) for k in fields)


def forecast_events(events: list[dict]) -> list[dict]:
    rows = []
    for i, origin in enumerate(events):
        if origin["outcome"]["label"] not in LABELS:
            continue
        date = pd.Timestamp(origin["origin"])
        train = [
            e
            for e in events[:i]
            if e["outcome"]["label"] in LABELS
            and pd.Timestamp(e["outcome"]["target_end"]) < date
        ]
        if len(train) < SPEC["minimum_training_events"]:
            continue
        uncond = (_counts(train) + 1.0) / (len(train) + len(LABELS))
        same_dir = [e for e in train if e["direction"] == origin["direction"]]
        p_dir = _shrink(same_dir, uncond)

        decomp_fields = ("direction", "driver_state")
        p_decomp = _shrink([e for e in train if _match(e, origin, decomp_fields)], p_dir)

        term_fields = decomp_fields + ("term_premium_state",)
        p_term = _shrink([e for e in train if _match(e, origin, term_fields)], p_decomp)

        cross_fields = term_fields + ("credit_state", "oil_state", "curve_state")
        p_cross = _shrink([e for e in train if _match(e, origin, cross_fields)], p_term)

        full_fields = cross_fields + ("auction_state",)
        p_full = _shrink([e for e in train if _match(e, origin, full_fields)], p_cross)

        rows.append(
            {
                "origin": origin["origin"],
                "direction": origin["direction"],
                "states": {
                    k: origin[k]
                    for k in (
                        "driver_state",
                        "term_premium_state",
                        "credit_state",
                        "oil_state",
                        "curve_state",
                        "auction_state",
                    )
                },
                "training_events": len(train),
                "last_training_target_end": max(e["outcome"]["target_end"] for e in train),
                "probabilities": {
                    "unconditional": uncond.tolist(),
                    "impulse_direction": p_dir.tolist(),
                    "decomposition": p_decomp.tolist(),
                    "decomp_term": p_term.tolist(),
                    "crossasset": p_cross.tolist(),
                    "full": p_full.tolist(),
                },
                "outcome": origin["outcome"],
                "event": {
                    k: origin[k]
                    for k in (
                        "impulse_bp",
                        "threshold_bp",
                        "barrier_bp",
                        "real_change_bp",
                        "be_change_bp",
                        "tp_change_bp",
                        "hy_change_bp",
                        "oil_change_pct",
                        "curve_change_bp",
                    )
                },
                "authority": False,
            }
        )
    return rows


def summarize(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["outcome"]["label"] in LABELS]
    out = {
        "forecast_events": len(rows),
        "scored_events": len(scored),
        "outcome_counts": dict(Counter(r["outcome"]["label"] for r in rows)),
        "direction_counts": dict(Counter(str(r["direction"]) for r in rows)),
        "driver_counts": dict(Counter(r["states"]["driver_state"] for r in rows)),
        "models": {},
        "authority": False,
    }
    if not scored:
        return out
    y = np.array([LABELS.index(r["outcome"]["label"]) for r in scored])
    truth = np.eye(len(LABELS))[y]
    losses = {}
    for name in MODELS:
        probs = np.array([r["probabilities"][name] for r in scored], dtype=float)
        loss = ((probs - truth) ** 2).sum(axis=1)
        losses[name] = loss
        out["models"][name] = {
            "brier": float(loss.mean()),
            "log_loss": float(-np.log(probs[np.arange(len(y)), y]).mean()),
        }
    base = losses[SPEC["primary_baseline"]]
    for name in MODELS:
        if name == SPEC["primary_baseline"]:
            continue
        diff = base - losses[name]
        out["models"][name]["brier_improvement_vs_primary_baseline"] = float(diff.mean())
        out["models"][name]["relative_brier_improvement_vs_primary_baseline"] = float(
            diff.mean() / base.mean()
        )
    return out


def partition(rows: list[dict]) -> dict[str, list[dict]]:
    cut = pd.Timestamp(PRIMARY_START)
    return {
        "development_2017_2021": [r for r in rows if pd.Timestamp(r["origin"]) < cut],
        "seen_primary_2022_2025": [r for r in rows if pd.Timestamp(r["origin"]) >= cut],
    }


def verify_freeze(receipt: dict) -> None:
    if receipt.get("spec") != SPEC:
        raise ValueError("spec mismatch")
    if set(receipt.get("data_sha256", {})) != set(DATA_PATHS):
        raise ValueError("data set mismatch")
    for key, digest in receipt["data_sha256"].items():
        if file_hash(DATA_PATHS[key]) != digest:
            raise ValueError("data changed: " + key)
    if set(receipt.get("code_sha256", {})) != set(CODE_PATHS):
        raise ValueError("code set mismatch")
    for rel, digest in receipt["code_sha256"].items():
        if file_hash(ROOT / rel) != digest:
            raise ValueError("code changed: " + rel)


def freeze() -> None:
    if FREEZE.exists():
        raise FileExistsError("freeze exists")
    ledger = TrialLedger(path=ROOT / "data/trial_ledger.jsonl", family=FAMILY)
    if ledger.literal_n() != 0:
        raise ValueError("family already registered")
    receipt = {
        "schema": "ric.rate_shock_driver_transition.freeze.v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "strategy_outcomes_opened_for_this_construction": False,
        "history_seen_elsewhere_in_program": True,
        "spec": SPEC,
        "data_sha256": {k: file_hash(v) for k, v in DATA_PATHS.items()},
        "code_sha256": {p: file_hash(ROOT / p) for p in CODE_PATHS},
        "ledger_before_sha256": file_hash(ROOT / "data/trial_ledger.jsonl"),
        "new_configs": len(MODELS) - 1,
        "primary": "seen_primary_2022_2025:decomp_term_vs_impulse_direction",
        "policy_futures_excluded_for_roll_contamination": True,
        "authority": False,
    }
    FREEZE.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


def run(output: Path) -> None:
    receipt = json.loads(FREEZE.read_text())
    verify_freeze(receipt)
    ledger_path = ROOT / "data/trial_ledger.jsonl"
    if file_hash(ledger_path) != receipt["ledger_before_sha256"]:
        raise ValueError("trial ledger changed; reconcile")
    ledger = TrialLedger(path=ledger_path, family=FAMILY)
    if ledger.literal_n() != 0:
        raise ValueError("family state changed")

    output.mkdir(parents=True, exist_ok=False)
    configs = [
        {"model": m, "spec": SPEC, "freeze_sha256": file_hash(FREEZE)}
        for m in MODELS
        if m != "unconditional"
    ]
    registered = ledger.log_grid(
        configs,
        info_cutoff=END,
        source="rate_shock_driver_transition_seen_history",
        note="Retrospective seen-history transition study; no promotion authority.",
    )
    reg = {
        "family": FAMILY,
        "registered": registered,
        "literal_n": ledger.literal_n(),
        "ledger_before_sha256": receipt["ledger_before_sha256"],
        "ledger_after_sha256": file_hash(ledger_path),
        "freeze_sha256": file_hash(FREEZE),
    }
    (output / "registration.json").write_text(json.dumps(reg, indent=2) + "\n")
    if registered != len(configs) or ledger.literal_n() != len(configs):
        raise ValueError("partial registration")

    frame = build_frame()
    events = build_events(frame)
    rows = forecast_events(events)
    with (output / "events.jsonl").open("x") as fh:
        for e in events:
            fh.write(json.dumps(e, allow_nan=False) + "\n")
    with (output / "predictions.jsonl").open("x") as fh:
        for r in rows:
            fh.write(json.dumps(r, allow_nan=False) + "\n")

    parts = partition(rows)
    summary = {
        "schema": "ric.rate_shock_driver_transition.result.v1",
        "spec": SPEC,
        "registration": reg,
        "event_count": len(events),
        "forecast_count": len(rows),
        "data_sha256": receipt["data_sha256"],
        "event_sha256": file_hash(output / "events.jsonl"),
        "prediction_sha256": file_hash(output / "predictions.jsonl"),
        "partitions": {k: summarize(v) for k, v in parts.items()},
        "all_dates": summarize(rows),
        "primary_sample_floor_met": (
            len(parts["seen_primary_2022_2025"]) >= SPEC["minimum_primary_events"]
        ),
        "policy_futures_excluded_for_roll_contamination": True,
        "seen_history": True,
        "authority": False,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    primary = summary["partitions"]["seen_primary_2022_2025"]
    print(
        json.dumps(
            {
                "events": len(events),
                "forecasts": len(rows),
                "primary_scored": primary["scored_events"],
                "primary_floor_met": summary["primary_sample_floor_met"],
                "outcomes": primary["outcome_counts"],
                "drivers": primary["driver_counts"],
                "models": primary["models"],
                "output": str(output),
            },
            indent=2,
        )
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("freeze", "run"))
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if args.action == "freeze":
        freeze()
    else:
        if args.output is None:
            ap.error("run requires --output")
        run(args.output)


if __name__ == "__main__":
    main()
