"""Read a pinned Git snapshot and emit diagnostic evidence, never alter its owners.

Usage: python run_snapshot_audit.py --repo /path/to/macro --ref <40-char-SHA>
Optional --out is exclusive-create; existing evidence is never overwritten.
Requires pandas/numpy to read existing Parquet and run existing clock functions.
No network, checkout, model fit, new strategy, outcome replay, or canonical write.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types

import numpy as np
import pandas as pd

from intake_audit import summarize_effective_ledger


class Snapshot:
    def __init__(self, repo: str, ref: str):
        if re.fullmatch(r"[0-9a-f]{40}", ref) is None:
            raise ValueError("immutable full lowercase commit SHA required")
        self.repo, self.ref = str(Path(repo).resolve()), ref
        resolved = subprocess.check_output(
            ["git", "-C", self.repo, "rev-parse", "--verify", ref + "^{commit}"], text=True).strip()
        if resolved != ref:
            raise ValueError("source commit identity mismatch")
        self.buffers: dict[str, bytes] = {}

    def read(self, path: str) -> bytes:
        if path not in self.buffers:
            self.buffers[path] = subprocess.check_output(
                ["git", "-C", self.repo, "show", self.ref + ":" + path])
        return self.buffers[path]

    def frame(self, path: str, columns=None) -> pd.DataFrame:
        return pd.read_parquet(io.BytesIO(self.read(path)), columns=columns)

    def module(self, name: str, path: str):
        module = types.ModuleType(name)
        module.__file__ = str(Path(self.repo) / path)
        sys.modules[name] = module
        exec(compile(self.read(path), self.ref + ":" + path, "exec"), module.__dict__)
        return module

    def receipts(self) -> dict:
        return {p: {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
                for p, b in sorted(self.buffers.items())}


def ledger(snapshot: Snapshot) -> dict:
    owner = snapshot.module("pinned_prophet_integrity", "engine/prophet_integrity.py")
    # Use the owner loader unchanged, including strict sidecar validation.
    with tempfile.TemporaryDirectory(prefix="prophet-intake-") as tmp:
        root = Path(tmp)
        for name in ("ledger.jsonl", "ledger_corrections.jsonl", "ledger_quarantine.json"):
            path = "data/prophet/" + name
            dst = root / path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(snapshot.read(path))
        projected = owner.load_effective_ledger(root)
    reconstructed = {r["id"] for r in projected.rows if owner.is_reconstructed(r)}
    return summarize_effective_ledger(projected.rows, projected.quarantined_ids, reconstructed,
                                      source_identity={"macro_commit": snapshot.ref,
                                                       "projection_owner": "engine/prophet_integrity.py"})


def clocks(snapshot: Snapshot) -> dict:
    # This subprocess owns its temporary import namespace. Only the existing pure
    # US-calendar, anchor, oracle and exact cascade function are executed.
    lib = types.ModuleType("lib")
    lib.__path__ = []
    sys.modules["lib"] = lib
    lib.nyse_calendar = snapshot.module("lib.nyse_calendar", "lib/nyse_calendar.py")
    anchor = snapshot.module("pinned_session_anchor", "engine/session_anchor.py")
    canon = snapshot.module("pinned_canon", "engine/canon.py")
    parsed = ast.parse(snapshot.read("engine/confluence_tiers.py"))
    node = next(x for x in parsed.body if isinstance(x, ast.FunctionDef) and x.name == "_tf_bars")
    namespace = {"pd": pd, "np": np, "session_positions": anchor.session_positions}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "pinned:_tf_bars", "exec"), namespace)
    cases = []
    for ticker in ("SPY", "NVDA", "AMD", "TSLA", "WMT", "JPM"):
        close = snapshot.frame(f"data/yahoo/{ticker}.parquet", ["close"])["close"]
        close = close.dropna().sort_index().loc["2014-01-01":"2026-09-30"]
        if len(close) < 600 or close.index.has_duplicates:
            raise ValueError(f"{ticker}: inadequate or duplicate history for fixed diagnostic")
        cutoff = close.index[-500]
        for grain in (2, 3):
            full = namespace["_tf_bars"](close, grain)[0]
            oracle = canon.resample_sessions(close, grain)[0]
            for dropped in (1, 2, 3, 4, 5):
                def changed(a, b):
                    a, b = a.loc[a.index >= cutoff], b.loc[b.index >= cutoff]
                    common = a.index.intersection(b.index)
                    return bool(len(a.index.symmetric_difference(b.index)) or
                                not a.reindex(common).equals(b.reindex(common)))
                cases.append({"ticker": ticker, "grain_sessions": grain, "leading_drop": dropped,
                              "absolute_grid_changed": changed(full, namespace["_tf_bars"](close.iloc[dropped:], grain)[0]),
                              "ordinal_oracle_changed": changed(oracle, canon.resample_sessions(close.iloc[dropped:], grain)[0])})
    return {"kind": "mechanical_not_outcome_test", "comparisons": len(cases),
            "absolute_grid_changed": sum(x["absolute_grid_changed"] for x in cases),
            "ordinal_oracle_changed": sum(x["ordinal_oracle_changed"] for x in cases),
            "cases": cases,
            "scope": "Same trailing 500 input sessions; only leading slices vary. No EMA, crossover or return comparison.",
            "limitations": "Not Terminal parity, full production-path proof, missing-session handling, or right-edge completion proof. Oracle differences are documented design, not a fresh bug."}


def availability(snapshot: Snapshot) -> dict:
    owner = snapshot.module("pinned_regime_coverage", "engine/regime_conditioning_coverage.py")
    axes = snapshot.frame("data/signal_archive/track_record.parquet", ["date", *owner.CANDIDATE_AXES])
    report = owner.assess(axes)
    candidate_path = "data/us_prophet_rank/candidates/2026-09.parquet"
    fields = ["stamp_date", "ticker", "board_definition", "selection_era", "theme_membership_count",
              "regime__absent", "regime__basis"]
    candidates = snapshot.frame(candidate_path, fields)
    historical = snapshot.frame("data/regime/regime_v2_pit.parquet", ["pit_class"])
    real = snapshot.frame("data/fred/DFII10.parquet")
    tech = json.loads(snapshot.read("site/factordata/tech_lab.json"))
    return {
        "existing_estimability_report": report,
        "scope_warning": "regime_at_entry is a per-security price-trend axis, not evidence of deep macro history. PR #8301 separately repairs this report's scope presentation; no mutation here.",
        "september_candidates": {
            "rows": len(candidates), "unique_dates": int(candidates.stamp_date.nunique()),
            "unique_tickers": int(candidates.ticker.nunique()),
            "span": [str(candidates.stamp_date.min()), str(candidates.stamp_date.max())],
            "board_definitions": candidates.board_definition.value_counts(dropna=False).to_dict(),
            "selection_eras": candidates.selection_era.value_counts(dropna=False).to_dict(),
            "theme_membership_positive_rows": int((pd.to_numeric(candidates.theme_membership_count, errors="coerce") > 0).sum()),
            "regime_basis": candidates['regime__basis'].fillna('missing').value_counts().to_dict(),
            "note": "Snapshot rows and ticker counts are not independent regime observations or proof of delivered recommendations."},
        "historical_regime_artifact": {"rows": len(historical), "span": [str(historical.index.min()), str(historical.index.max())],
                                       "pit_classes": historical.pit_class.fillna('missing').value_counts().to_dict(),
                                       "note": "Specific artifact coverage; not the freshness of every current regime source."},
        "dfii10": {"rows": len(real), "span": [str(real.index.min()), str(real.index.max())],
                   "note": "Latest stored values do not establish historical first-known or ingestion time."},
        "technical_lab_artifact": {"signal_definitions": len(tech['signals']), "universe_n": tech['universe_n'],
                                   "generated_utc": tech['generated_utc'], "universe_caveat": tech.get('universe_caveat')},
        "outcome_policy": "No W3 race, Phase-22 prospective outcome, indicator ranking, threshold fit, or subtheme raw replay was read or executed."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    snapshot = Snapshot(args.repo, args.ref)
    report = {"schema": "prophet.regime_indicator_snapshot_audit/v1",
              "generated_utc": datetime.now(timezone.utc).isoformat(), "source_commit": args.ref,
              "authority": {k: False for k in ("rank", "entry", "size", "trade", "promotion")},
              "ledger": ledger(snapshot), "clock_diagnostic": clocks(snapshot),
              "availability": availability(snapshot)}
    report['sources'] = snapshot.receipts()
    encoded = (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    if args.out:
        # No automatic overwrite or directory creation; caller chooses an existing evidence owner.
        with args.out.open("xb") as stream:
            stream.write(encoded)
        print(json.dumps({"output": str(args.out), "bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest(),
                          "ledger_counts": report['ledger']['counts'],
                          "clock_comparisons": report['clock_diagnostic']['comparisons'],
                          "absolute_grid_changed": report['clock_diagnostic']['absolute_grid_changed'],
                          "ordinal_oracle_changed": report['clock_diagnostic']['ordinal_oracle_changed']}))
    else:
        print(encoded.decode(), end="")


if __name__ == "__main__":
    main()
