"""Reproducible, research-only consumer of the Prophet entry/regime adapters.

A versioned experiment specification is required. Price inputs are read from its
exact Git commit, never the moving worktree. No frozen race/outcome store is read.
The cache is an operation-local research artifact, not a new market/event ledger.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any

import numpy as np
import pandas as pd

from scripts import prophet_fusion_mechanisms as core
from scripts.prophet_fusion_arena import OutputPathRefusal

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "research/prophet_fusion/entry_regime_v1_spec.json"


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(x) for x in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(_json_value(value), indent=2, sort_keys=True, allow_nan=False) + "\n"
    temporary = path.with_name(path.name + ".writing")
    temporary.write_text(text)
    temporary.replace(path)


def safe_cache(path: Path) -> Path:
    # Reuse the existing owner's output fence, including symlink resolution.
    from scripts.prophet_fusion_arena import _safe_out_dir
    out = _safe_out_dir(path)
    out.mkdir(parents=True, exist_ok=True)
    (out / ".gitignore").write_text("*\n")
    return out


def _git_bytes(source: str, path: str) -> bytes:
    if not path.startswith("data/") or ".." in Path(path).parts:
        raise core.MechanismRefusal("UNREGISTERED_INPUT_PATH")
    proc = subprocess.run(["git", "show", f"{source}:{path}"], cwd=ROOT,
                          capture_output=True, timeout=120, check=False)
    if proc.returncode:
        raise core.MechanismRefusal(f"PINNED_INPUT_UNAVAILABLE:{path}")
    if proc.stdout.startswith(b"version https://git-lfs.github.com"):
        raise core.MechanismRefusal(f"UNMATERIALIZED_LFS_INPUT:{path}")
    return proc.stdout


def _read_close(raw: bytes, column: str, name: str) -> pd.Series:
    try:
        frame = pd.read_parquet(io.BytesIO(raw), columns=[column])
    except Exception as exc:
        raise core.MechanismRefusal(f"PARQUET_CONTRACT:{name}:{type(exc).__name__}") from exc
    return core.validate_close(frame[column], name)


def adapter_digest() -> str:
    return core.digest_bytes(Path(core.__file__).read_bytes())


def qualify(spec: dict, out: Path) -> dict:
    """Outcome-blind input/source qualification and immutable capture."""
    manifest_path = out / "input_manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        if previous["spec_sha256"] != spec["_sha256"]:
            raise core.MechanismRefusal("CACHE_SPEC_CONFLICT")
        for item in previous["inputs"]:
            path = out / item["cache_name"]
            if not path.is_file() or core.digest_bytes(path.read_bytes()) != item["sha256"]:
                raise core.MechanismRefusal("CACHE_INPUT_DIGEST_CONFLICT")
        return previous
    input_dir = out / "inputs"
    input_dir.mkdir(exist_ok=True)
    sources = [("SPY_BENCHMARK", spec["benchmark_path"], spec["benchmark_column"])]
    sources += [(ticker, spec["price_path_template"].format(ticker=ticker), spec["price_column"])
                for ticker in spec["universe"]]
    items, series = [], {}
    for name, path, column in sources:
        raw = _git_bytes(spec["source_base"], path)
        close = _read_close(raw, column, name)
        dest = input_dir / f"{name}.parquet"
        dest.write_bytes(raw)
        blob_header = f"blob {len(raw)}\0".encode()
        items.append({"name": name, "source_path": path, "column": column,
                      "git_blob_sha": hashlib.sha1(blob_header + raw).hexdigest(),
                      "sha256": core.digest_bytes(raw), "bytes": len(raw),
                      "cache_name": str(dest.relative_to(out)), "rows": len(close),
                      "first_session": str(close.index[0].date()),
                      "last_session": str(close.index[-1].date())})
        series[name] = close
    benchmark = series["SPY_BENCHMARK"]
    calendar_checks = {}
    for name in spec["universe"]:
        aligned = core.align_calendar(series[name], benchmark)
        start, end = pd.Timestamp(spec["start"]), pd.Timestamp(spec["end"])
        if start not in aligned.index or end not in aligned.index:
            raise core.MechanismRefusal(f"REGISTERED_WINDOW_NOT_COVERED:{name}")
        if int(aligned.index.get_loc(end)) + 1 + spec["secondary_horizon"] >= len(aligned):
            raise core.MechanismRefusal(f"REGISTERED_WINDOW_NOT_FULLY_MATURED:{name}")
        calendar_checks[name] = {"registered_window_fully_covered": True,
                                "aligned_rows": len(aligned),
                                "common_end": str(aligned.index[-1].date()),
                                "excluded_after_benchmark_end": len(series[name]) - len(aligned)}
    manifest = {
        "schema": "prophet.entry_regime_input_manifest/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_base": spec["source_base"], "spec_sha256": spec["_sha256"],
        "inputs": items, "calendar_checks": calendar_checks,
        "outcome_blind": True, "frozen_race_stores_read": [],
        "survivorship_biased": spec["survivorship_biased"],
        "historical_availability": spec["historical_availability"],
        "price_basis": spec["price_basis"], "promotion_eligible": False,
    }
    write_json(manifest_path, manifest)
    return manifest


def _load_input(out: Path, manifest: dict, name: str) -> pd.Series:
    item = next(x for x in manifest["inputs"] if x["name"] == name)
    raw = (out / item["cache_name"]).read_bytes()
    if core.digest_bytes(raw) != item["sha256"]:
        raise core.MechanismRefusal("INPUT_CHANGED_AFTER_QUALIFICATION")
    return _read_close(raw, item["column"], name)


def _lower_priority() -> None:
    if hasattr(os, "nice"):
        os.nice(8)


def _collect_one(ticker: str, spec: dict, out_string: str, manifest: dict) -> dict:
    out = Path(out_string)
    receipt_path = out / "observations" / f"{ticker}.json"
    data_path = receipt_path.with_suffix(".parquet")
    expected = {"spec_sha256": spec["_sha256"], "adapter_sha256": adapter_digest(),
                "source_base": spec["source_base"]}
    if receipt_path.exists():
        old = json.loads(receipt_path.read_text())
        if any(old.get(k) != v for k, v in expected.items()):
            raise core.MechanismRefusal("OBSERVATION_CACHE_IDENTITY_CONFLICT")
        if not data_path.is_file() or core.digest_bytes(data_path.read_bytes()) != old["data_sha256"]:
            raise core.MechanismRefusal("OBSERVATION_CACHE_DIGEST_CONFLICT")
        return {**old, "reused": True}
    b = _load_input(out, manifest, "SPY_BENCHMARK")
    c = core.align_calendar(_load_input(out, manifest, ticker), b)
    first = int(c.index.searchsorted(pd.Timestamp(spec["start"])))
    last = int(c.index.searchsorted(pd.Timestamp(spec["end"]), side="right"))
    dates = c.index[max(0, first - spec["entry_gap_sessions"]):last]
    if len(dates) == 0:
        raise core.MechanismRefusal(f"NO_DECISION_SESSIONS:{ticker}")
    t = time.monotonic()
    # Infrastructure canary only: no outcomes or threshold selection.
    probes = dates[np.unique(np.linspace(0, len(dates) - 1, 5).astype(int))]
    check = core.technical_core_observations(ticker, c, probes)
    if not check["status"].eq("EVALUATED").any():
        raise core.MechanismRefusal(f"GATE_UNAVAILABLE_ON_ALL_CANARIES:{ticker}")
    observations = core.technical_core_observations(ticker, c, dates)
    data_path.parent.mkdir(exist_ok=True)
    observations.to_parquet(data_path)
    receipt = {**expected, "schema": core.OBSERVATION_SCHEMA, "ticker": ticker,
               "rows": len(observations), "elapsed_seconds": round(time.monotonic() - t, 3),
               "status_counts": observations["status"].value_counts().to_dict(),
               "data_sha256": core.digest_bytes(data_path.read_bytes()),
               "basis": "technical_core_no_washout_waiver_no_event_latch",
               "outcome_blind": True, "reused": False}
    write_json(receipt_path, receipt)
    return receipt


def collect(spec: dict, out: Path, manifest: dict, workers: int = 2) -> list[dict]:
    if workers not in (1, 2):
        raise core.MechanismRefusal("LOCAL_COMPUTE_CAP_MAX_TWO")
    results = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_lower_priority) as pool:
        futures = {pool.submit(_collect_one, ticker, spec, str(out), manifest): ticker
                   for ticker in spec["universe"]}
        for future in as_completed(futures):
            receipt = future.result()
            results.append(receipt)
            print(json.dumps({"phase": "prefix_observations", "ticker": receipt["ticker"],
                              "rows": receipt["rows"], "status_counts": receipt["status_counts"],
                              "elapsed_seconds": receipt["elapsed_seconds"],
                              "reused": receipt["reused"]}), flush=True)
    write_json(out / "collection_receipt.json", {
        "schema": "prophet.entry_regime_collection/v1", "spec_sha256": spec["_sha256"],
        "adapter_sha256": adapter_digest(), "outcome_blind": True,
        "assets": sorted(results, key=lambda r: r["ticker"]), "complete": len(results) == len(spec["universe"]),
    })
    return results


def _verified_observations(ticker: str, spec: dict, out: Path) -> pd.DataFrame:
    receipt_path = out / "observations" / f"{ticker}.json"
    data_path = receipt_path.with_suffix(".parquet")
    receipt = json.loads(receipt_path.read_text())
    if (receipt.get("spec_sha256") != spec["_sha256"]
            or receipt.get("adapter_sha256") != adapter_digest()
            or core.digest_bytes(data_path.read_bytes()) != receipt["data_sha256"]):
        raise core.MechanismRefusal("OBSERVATIONS_NOT_BOUND_TO_CURRENT_CONTRACT")
    frame = pd.read_parquet(data_path)
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise core.MechanismRefusal("OBSERVATION_SESSION_CONTRACT")
    if len(frame) != receipt["rows"] or not frame["ticker"].eq(ticker).all():
        raise core.MechanismRefusal("OBSERVATION_IDENTITY_CONTRACT")
    return frame


def event_frame(spec: dict, out: Path, manifest: dict) -> tuple[pd.DataFrame, dict]:
    """One frozen onset population per trigger; contexts select, never re-time it."""
    collection = json.loads((out / "collection_receipt.json").read_text())
    if (not collection.get("complete") or collection.get("spec_sha256") != spec["_sha256"]
            or {r["ticker"] for r in collection["assets"]} != set(spec["universe"])):
        raise core.MechanismRefusal("INCOMPLETE_OR_DIFFERENT_COLLECTION")
    b = _load_input(out, manifest, "SPY_BENCHMARK")
    context = core.market_context(b)
    state = (context["market_uptrend"].astype("string") + ":" +
             context["no_volatility_stress"].astype("string")).fillna("unknown")
    context["regime_spell"] = state.ne(state.shift()).fillna(True).astype("int64").cumsum()
    rows, coverage = [], {}
    horizons = (spec["primary_horizon"], spec["secondary_horizon"])
    for ticker in spec["universe"]:
        c = core.align_calendar(_load_input(out, manifest, ticker), b)
        obs = _verified_observations(ticker, spec, out)
        triggers = core.momentum_triggers(c)
        triggers["technical_core_t12"] = obs["signal"].reindex(c.index).astype("boolean")
        beta = core.ex_ante_beta(c, b)
        core_known = triggers["technical_core_t12"].notna()
        prior_core_known = core_known.shift(1, fill_value=False).rolling(3, min_periods=3).sum().eq(3)
        market_known = context["market_context_known"].reindex(c.index, fill_value=False)
        common = core_known & prior_core_known & market_known
        in_window = (c.index >= pd.Timestamp(spec["start"])) & (c.index <= pd.Timestamp(spec["end"]))
        cov: dict[str, Any] = {
            "decision_sessions": int(in_window.sum()),
            "core_unavailable_sessions": int((~core_known & in_window).sum()),
            "market_unknown_sessions": int((~market_known & in_window).sum()),
            "common_qualified_sessions": int((common & in_window).sum()),
            "triggers": {},
        }
        for trigger in core.TRIGGERS:
            onset = core.onset_mask(triggers[trigger], spec["entry_gap_sessions"]) & in_window
            accepted = onset & common
            stats = {"raw_onsets": int(onset.sum()), "common_qualified_onsets": int(accepted.sum()),
                     "excluded_unknown_frame": int((onset & ~common).sum()), "unmatured_by_horizon": {}}
            for date in c.index[accepted]:
                base = {"ticker": ticker, "date": date, "trigger": trigger,
                        "market_uptrend": bool(context.at[date, "market_uptrend"]),
                        "no_volatility_stress": bool(context.at[date, "no_volatility_stress"]),
                        "regime_spell": int(context.at[date, "regime_spell"]),
                        "ex_ante_beta": beta.loc[date], "tier": None, "provisional": None}
                if trigger == "technical_core_t12":
                    base.update(tier=obs.at[date, "tier"], provisional=obs.at[date, "provisional"])
                for horizon in horizons:
                    outcome = core.canonical_outcome(c, b, date, horizon)
                    if outcome["status"] != "MATURED":
                        key = str(horizon)
                        stats["unmatured_by_horizon"][key] = stats["unmatured_by_horizon"].get(key, 0) + 1
                        continue
                    row = {**base, **outcome, "horizon": horizon}
                    for cost in spec["cost_sensitivity_bps"]:
                        row[f"net_{cost}bps"] = float(core.net_return(outcome["gross_return"], cost))
                    net = row[f"net_{spec['primary_round_trip_cost_bps']}bps"]
                    row["net_return"] = net
                    row["net_positive"] = float(net > 0)
                    row["net_excess"] = net - outcome["benchmark_return"]
                    row["beta_residual"] = (net - beta.loc[date] * outcome["benchmark_return"]
                                            if pd.notna(beta.loc[date]) else np.nan)
                    rows.append(row)
            cov["triggers"][trigger] = stats
        coverage[ticker] = cov
    if not rows:
        raise core.MechanismRefusal("NO_QUALIFIED_MATURED_EVENTS")
    frame = pd.DataFrame(rows)
    if frame.duplicated(["ticker", "date", "trigger", "horizon"]).any():
        raise core.MechanismRefusal("DUPLICATE_EVENT_OUTCOME")
    return frame, coverage


def select_arm(frame: pd.DataFrame, arm: str, horizon: int) -> pd.DataFrame:
    trigger, context = arm.split("__")
    subset = frame.loc[(frame["trigger"] == trigger) & (frame["horizon"] == horizon)]
    if context != "unfiltered":
        subset = subset.loc[subset[context].eq(True)]
    return subset


def independent_episode_count(frame: pd.DataFrame) -> int:
    count = 0
    for _, group in frame.groupby("ticker", sort=False):
        last_exit = None
        for row in group.sort_values("date").itertuples():
            if last_exit is None or row.date > last_exit:
                count += 1
                last_exit = pd.Timestamp(row.exit_date)
    return count


def _date_mean(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or frame[column].notna().sum() == 0:
        return None
    return float(frame.groupby("date")[column].mean().mean())


def arm_summary(frame: pd.DataFrame, arm: str, horizon: int, spec: dict) -> dict:
    sample = select_arm(frame, arm, horizon)
    trigger, context = arm.split("__")
    base = select_arm(frame, f"{trigger}__unfiltered", horizon)
    retained_index = set(sample.index)
    rejected = base.loc[~base.index.isin(retained_index)]
    wins = base["net_positive"].sum()
    result = {
        "arm": arm, "horizon": horizon, "events": len(sample),
        "decision_dates": int(sample["date"].nunique()), "names": int(sample["ticker"].nunique()),
        "nonoverlapping_name_episodes": independent_episode_count(sample),
        "market_regime_spells": int(sample["regime_spell"].nunique()),
        "net_excess": _date_mean(sample, "net_excess"),
        "net_return": _date_mean(sample, "net_return"),
        "net_positive_rate_date_weighted": _date_mean(sample, "net_positive"),
        "net_positive_rate_event_weighted": float(sample["net_positive"].mean()) if len(sample) else None,
        "ex_ante_beta_residual": _date_mean(sample, "beta_residual"),
        "signal_retention": len(sample) / len(base) if len(base) else None,
        "winner_retention": float(sample["net_positive"].sum() / wins) if wins else None,
        "rejected_event_count": len(rejected), "rejected_net_excess": _date_mean(rejected, "net_excess"),
        "cost_sensitivity_net_return": {str(c): _date_mean(sample, f"net_{c}bps")
                                        for c in spec["cost_sensitivity_bps"]},
        "promotion_eligible": False,
    }
    return result


def moving_block_contrast(
    left: np.ndarray, right: np.ndarray, *, block: int, replications: int,
    seed: int, alpha: float, comparisons: int,
) -> dict:
    """Resample the SAME calendar blocks for both arms; names never become IID trials."""
    left, right = np.asarray(left, dtype=float), np.asarray(right, dtype=float)
    if left.ndim != 1 or left.shape != right.shape or len(left) < block or block < 1:
        raise core.MechanismRefusal("BLOCK_SAMPLE_CONTRACT")
    if comparisons < 1 or replications < 1 or not 0 < alpha < 1:
        raise core.MechanismRefusal("BOOTSTRAP_SPEC_CONTRACT")
    if not np.isfinite(left).any() or not np.isfinite(right).any():
        return {"status": "EMPTY_ARM", "delta": None, "ci95": None, "familywise_ci": None}
    n = len(left)
    rng = np.random.default_rng(seed)
    full, remainder = divmod(n, block)
    starts = rng.integers(0, n - block + 1, size=(replications, full))
    tail = rng.integers(0, n - remainder + 1, size=replications) if remainder else None

    def means(values: np.ndarray) -> np.ndarray:
        valid = np.isfinite(values)
        total = np.concatenate(([0.0], np.cumsum(np.where(valid, values, 0.0))))
        count = np.concatenate(([0], np.cumsum(valid.astype(int))))
        sums = (total[starts + block] - total[starts]).sum(axis=1)
        counts = (count[starts + block] - count[starts]).sum(axis=1)
        if remainder:
            sums += total[tail + remainder] - total[tail]
            counts += count[tail + remainder] - count[tail]
        return np.divide(sums, counts, out=np.full(replications, np.nan), where=counts > 0)

    draws = means(left) - means(right)
    finite = np.isfinite(draws)
    value = float(np.nanmean(left) - np.nanmean(right))
    if finite.sum() < 0.95 * replications:
        return {"status": "SPARSE_BOOTSTRAP", "delta": value, "ci95": None,
                "familywise_ci": None, "valid_replications": int(finite.sum())}
    valid_draws = draws[finite]
    tail_alpha = alpha / comparisons / 2
    return {
        "status": "COMPUTED_DESCRIPTIVE", "delta": value,
        "ci95": np.quantile(valid_draws, [alpha / 2, 1 - alpha / 2]).tolist(),
        "familywise_ci": np.quantile(valid_draws, [tail_alpha, 1 - tail_alpha]).tolist(),
        "valid_replications": int(finite.sum()), "calendar_sessions": n,
        "nonoverlapping_calendar_blocks": n // block, "block_sessions": block,
        "method": "paired_moving_calendar_blocks_equal_decision_date_means",
    }


def compare_arms(frame: pd.DataFrame, grid: pd.DatetimeIndex, spec: dict) -> list[dict]:
    horizon = spec["primary_horizon"]
    u = spec["uncertainty"]
    comparisons = []
    for left, right in spec["primary_comparisons"]:
        a, b = select_arm(frame, left, horizon), select_arm(frame, right, horizon)
        av = a.groupby("date")["net_excess"].mean().reindex(grid).to_numpy()
        bv = b.groupby("date")["net_excess"].mean().reindex(grid).to_numpy()
        if len(grid) < u["block_sessions"]:
            result = {"status": "TOO_FEW_CALENDAR_SESSIONS", "delta": None,
                      "ci95": None, "familywise_ci": None}
        else:
            result = moving_block_contrast(
                av, bv, block=u["block_sessions"], replications=u["replications"],
                seed=u["seed"], alpha=u["familywise_alpha"],
                comparisons=spec["integer_primary_comparison_count"])
        episodes = [independent_episode_count(a), independent_episode_count(b)]
        floor_ok = (min(episodes) >= u["minimum_name_episodes_per_arm"]
                    and len(grid) // u["block_sessions"] >= u["minimum_nonoverlapping_blocks"])
        halves = {}
        for name, before in (("before_split", True), ("after_split", False)):
            mask_a = a["date"] < pd.Timestamp(spec["split_date"])
            mask_b = b["date"] < pd.Timestamp(spec["split_date"])
            aa, bb = a.loc[mask_a if before else ~mask_a], b.loc[mask_b if before else ~mask_b]
            ma, mb = _date_mean(aa, "net_excess"), _date_mean(bb, "net_excess")
            halves[name] = {"delta": ma - mb if ma is not None and mb is not None else None,
                            "left_dates": int(aa["date"].nunique()), "right_dates": int(bb["date"].nunique())}
        result.update(left=left, right=right, horizon=horizon, honest_n_floor_met=floor_ok,
                      nonoverlapping_name_episodes=episodes, chronological_halves=halves,
                      promotion_eligible=False)
        comparisons.append(result)
    return comparisons


def evaluate(spec: dict, out: Path, manifest: dict) -> dict:
    frame, coverage = event_frame(spec, out, manifest)
    frame.to_parquet(out / "graded_research_events.parquet", index=False)
    benchmark = _load_input(out, manifest, "SPY_BENCHMARK")
    grid = benchmark.index[(benchmark.index >= pd.Timestamp(spec["start"]))
                           & (benchmark.index <= pd.Timestamp(spec["end"]))]
    arms = [f"{t}__{c}" for t in core.TRIGGERS for c in core.CONTEXTS]
    summaries = [arm_summary(frame, arm, h, spec) for h in (21, 63) for arm in arms]
    comparisons = compare_arms(frame, grid, spec)
    technical = frame.loc[frame["trigger"].eq("technical_core_t12") & frame["horizon"].eq(21)]
    strata = []
    for (tier, provisional), group in technical.groupby(["tier", "provisional"], dropna=False):
        strata.append({"tier": tier, "provisional": provisional, "events": len(group),
                       "net_excess": _date_mean(group, "net_excess"),
                       "net_positive_rate": _date_mean(group, "net_positive")})
    from scripts.prophet_fusion_arena import build_folds
    fold_plan = build_folds([str(x.date()) for x in grid], horizon=63, embargo=63, strict=False)
    report = {
        "schema": "prophet.entry_regime_mechanism_report/v1", "study_id": spec["study_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(), "spec_sha256": spec["_sha256"],
        "source_base": spec["source_base"], "adapter_sha256": adapter_digest(),
        "study_code_sha256": core.digest_bytes(Path(__file__).read_bytes()),
        "status": "RETROSPECTIVE_MECHANISM_PILOT_NOT_PROMOTION_BEARING",
        "promotion_eligible": False, "survivorship_biased": spec["survivorship_biased"],
        "historical_availability": spec["historical_availability"], "price_basis": spec["price_basis"],
        "fill_basis": spec["fill_basis"], "cost_model": "symmetric_half_cost_on_entry_and_exit",
        "primary_round_trip_cost_bps": spec["primary_round_trip_cost_bps"],
        "primary_metric": spec["primary_metric"],
        "integer_primary_comparison_count": spec["integer_primary_comparison_count"],
        "window": [spec["start"], spec["end"]], "split_date": spec["split_date"],
        "input_manifest": manifest, "coverage": coverage, "arm_summaries": summaries,
        "primary_comparisons": comparisons, "technical_core_strata_descriptive": strata,
        "chronological_fold_qualification": {"folds": [f.as_dict() for f in fold_plan.folds],
                                              "refusals": fold_plan.refusals,
                                              "note": "No model was fitted; folds only qualify future use of the incumbent arena."},
        "limitations": [
            "Fixed survivor panel; not a point-in-time constituent universe or population estimate.",
            "Current price-history reconstruction is not original as-known vendor vintage data.",
            "Technical core excludes the live basket waiver and event latch; not board performance.",
            "Price adjustment basis has not been independently audited; no alpha or promotion claim.",
            "Fixed next-close returns are not executable stop/target outcomes or portfolio returns.",
            "Regime selection changes calendar exposure; beta residuals are descriptive, not a full risk-matched portfolio test.",
            "Historical eras were known before this study; pre-computation registration does not make them pristine out-of-sample data.",
            "No frozen W3/W2 race store, live rank, position size, trade or production service was changed.",
        ],
    }
    write_json(out / "report.json", report)
    (out / "report.md").write_text(render_markdown(report))
    return report


def render_markdown(report: dict) -> str:
    def pct(value: Any) -> str:
        return "unknown" if value is None or not np.isfinite(value) else f"{100 * value:.2f}%"
    lines = ["# Entry/regime mechanism pilot", "", f"**{report['status']}**", "",
             "This is a research consumer, not a buy list. No live authority is granted.", "",
             f"Source `{report['source_base']}`; spec SHA256 `{report['spec_sha256']}`.",
             f"Window {report['window'][0]} to {report['window'][1]}; next-session-close fills; "
             f"{report['primary_round_trip_cost_bps']} bps assumed round-trip costs.", "",
             "## Data and interpretation limits", ""]
    lines.extend(f"- {x}" for x in report["limitations"])
    lines += ["", "## Fixed-horizon outcomes", "",
              "Returns and positive-return rates below are equally weighted by decision date, not by ticker rows. "
              "Episodes exclude overlapping holding windows within a name. Different names can still share market risk.", ""]
    for horizon in (21, 63):
        lines += [f"### {horizon} sessions", "",
                  "| Arm | Events | Dates | Episodes | Net return | Excess vs SPY | Positive net | Retained |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for row in report["arm_summaries"]:
            if row["horizon"] == horizon:
                lines.append(f"| {row['arm']} | {row['events']} | {row['decision_dates']} | "
                             f"{row['nonoverlapping_name_episodes']} | {pct(row['net_return'])} | "
                             f"{pct(row['net_excess'])} | {pct(row['net_positive_rate_date_weighted'])} | "
                             f"{pct(row['signal_retention'])} |")
        lines.append("")
    lines += ["## Prespecified primary contrasts", "",
              "Paired 126-session calendar-block bootstrap; 11 prespecified contrasts. Familywise intervals "
              "use Bonferroni tail adjustment. This quantifies sampling uncertainty within the flawed historical "
              "panel; it does not repair survivor/vintage/basis bias or confer promotion eligibility.", "",
              "| Challenger minus comparator | Delta excess | 95% interval | Familywise interval | Honest-N floor |",
              "|---|---:|---|---|---|"]
    for row in report["primary_comparisons"]:
        ci = row.get("ci95")
        family = row.get("familywise_ci")
        ci_s = "withheld" if ci is None else f"[{pct(ci[0])}, {pct(ci[1])}]"
        family_s = "withheld" if family is None else f"[{pct(family[0])}, {pct(family[1])}]"
        lines.append(f"| {row['left']} minus {row['right']} | {pct(row.get('delta'))} | "
                     f"{ci_s} | {family_s} | {row['honest_n_floor_met']} |")
    lines += ["", "## Coverage", "", "| Name | Sessions | Common qualified | Core unavailable |",
              "|---|---:|---:|---:|"]
    for name, row in report["coverage"].items():
        lines.append(f"| {name} | {row['decision_sessions']} | {row['common_qualified_sessions']} | "
                     f"{row['core_unavailable_sessions']} |")
    lines += ["", "Machine-readable report additionally retains rejected-trade results, winner retention, "
              "cost stress, beta-residual diagnostics, chronological halves, provisional/T1/T2 strata, "
              "source digests and the unchanged incumbent fold floors.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("qualify", "collect", "report", "run"))
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    args = parser.parse_args(argv)
    try:
        spec = core.load_spec(args.spec)
        out = safe_cache(args.out)
        manifest = qualify(spec, out)
        print(json.dumps({"phase": "qualified", "inputs": len(manifest["inputs"]),
                          "spec_sha256": spec["_sha256"], "promotion_eligible": False}), flush=True)
        if args.phase in ("collect", "run"):
            collect(spec, out, manifest, args.workers)
        if args.phase in ("report", "run"):
            report = evaluate(spec, out, manifest)
            print(json.dumps({"phase": "reported", "status": report["status"],
                              "arms": len(report["arm_summaries"]),
                              "primary_contrasts": len(report["primary_comparisons"]),
                              "report": str(out / "report.json")}), flush=True)
        return 0
    except (core.MechanismRefusal, OutputPathRefusal, FileNotFoundError, ValueError, KeyError) as exc:
        print(json.dumps({"phase": "REFUSED", "type": type(exc).__name__, "reason": str(exc)}), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
