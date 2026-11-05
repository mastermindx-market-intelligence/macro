#!/usr/bin/env python3
"""GLT T09 component forecast study runner (measurement-only).

Registers the preregistered family in the trial ledger, runs the
rolling-origin study through ``engine.global_liquidity_forecast`` and writes
one result-card JSON. Measurement only: no network access of any kind, and
the only file written is the result JSON named by ``--out``. The canonical
``data/trial_ledger.jsonl`` is owned by the nightly pipeline; this runner
refuses that path (and any ``--out`` under ``data/`` or ``site/``).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from engine import canon
from engine import global_liquidity_forecast as glf
from engine.global_liquidity_knowledge_time import cutoff_utc
from engine.trial_ledger import TrialLedger

# Raw column names in the canonical stores (spec section 9). WRESBAL is read
# directly; TGA/RRP additionally go through engine.canon with a parity assert.
REAL_COLUMNS = {
    "reserves_wresbal_bn": "reserve_balances",
    "tga_bn": "tga_mn",
    "rrp_bn": "on_rrp",
}
FIXTURE_FILES = {
    "reserves_wresbal_bn": "reserves_wresbal.csv",
    "tga_bn": "tga.csv",
    "rrp_bn": "rrp.csv",
}
FIXTURE_UNITS_PER_BN = {"reserves_wresbal_bn": 1000.0, "tga_bn": 1000.0, "rrp_bn": 1.0}


def _normalize_raw(raw: pd.DataFrame) -> pd.DataFrame:
    """Index on the observation date: naive, normalized datetime64."""
    if "obs_date" in raw.columns:
        raw = raw.set_index("obs_date")
    elif "date" in raw.columns:
        raw = raw.set_index("date")
    idx = pd.to_datetime(raw.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    raw = raw.copy()
    raw.index = idx.normalize()
    return raw


def _clean_series(raw: pd.DataFrame, column: str, dev_end: date) -> pd.Series:
    """dropna -> dedup keep last -> sort -> truncate to obs_date <= dev_end."""
    s = pd.to_numeric(raw[column], errors="coerce").dropna()
    s = s[~s.index.duplicated(keep="last")]
    s = s.sort_index()
    return s[s.index <= pd.Timestamp(dev_end)]


def _iso_or_none(value) -> str | None:
    return None if value is None else pd.Timestamp(value).date().isoformat()


def _receipt(target: str, rel: str, path: Path | None, series: pd.Series | None) -> dict:
    if series is None:
        return {"target": target, "path": rel, "sha256": None, "rows_loaded": None,
                "first_obs": None, "last_obs": None}
    return {
        "target": target,
        "path": rel,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows_loaded": int(len(series)),
        "first_obs": _iso_or_none(series.index.min()) if len(series) else None,
        "last_obs": _iso_or_none(series.index.max()) if len(series) else None,
    }


def _canon_channel(s: pd.Series, root: Path, family, target: str) -> pd.Series:
    """TGA/RRP through engine.canon, asserting unit parity on the raw index."""
    tga_path = root / family.sources["tga_bn"]["path"]
    comp = canon.load_net_liquidity_components(
        s.index, fred_dir=root / "data" / "fred", tga_path=tga_path)
    got = comp[target].astype(float)
    expected = (s / 1000.0) if target == "tga_bn" else s.astype(float)
    if len(s):
        drift = float((got - expected).abs().max())
        assert drift <= 1e-9, f"canon parity failed for {target}: max abs diff {drift}"
    return got


def _frame_for_module(s: pd.Series, family, target: str) -> pd.DataFrame:
    """Spec section 3 source-frame contract: RangeIndex, obs_date + value ($bn), clock, dev_end cutoff."""
    frame = pd.DataFrame({"obs_date": pd.DatetimeIndex(s.index), "value": s.to_numpy(dtype=float)})
    frame = glf.attach_publication_clock(
        frame, rule=family.clocks[target]["rule"], decision_tz=family.origins.decision_tz)
    cut = cutoff_utc(family.windows.dev_end, family.origins.decision_tz)
    return frame[frame["published_at_utc"] <= cut].reset_index(drop=True)


def load_real_sources(root, family):
    """(sources, input_receipts) from the canonical parquet stores under root."""
    root = Path(root)
    sources: dict = {}
    receipts: list = []
    for target in family.targets:
        rel = Path(family.sources[target]["path"]).as_posix()
        path = root / rel
        if not path.exists():
            sources[target] = {"frame": None, "status": f"source_missing:{rel}"}
            receipts.append(_receipt(target, rel, None, None))
            continue
        raw = _normalize_raw(pd.read_parquet(path))
        s = _clean_series(raw, REAL_COLUMNS[target], family.windows.dev_end)
        if target == "reserves_wresbal_bn":
            bn = s / 1000.0  # WRESBAL is read directly, not through canon
        else:
            bn = _canon_channel(s, root, family, target)
        sources[target] = {"frame": _frame_for_module(bn, family, target), "status": "loaded"}
        receipts.append(_receipt(target, rel, path, s))
    return sources, receipts


def load_fixture_sources(fixture_dir, family):
    """(sources, input_receipts, announcements) from a synthetic CSV fixture."""
    fixture_dir = Path(fixture_dir)
    sources: dict = {}
    receipts: list = []
    announcements: list = []
    for target in family.targets:
        rel = FIXTURE_FILES[target]
        path = fixture_dir / rel
        if not path.exists():
            sources[target] = {"frame": None, "status": f"fixture_missing:{rel}"}
            receipts.append(_receipt(target, rel, None, None))
            continue
        raw = _normalize_raw(pd.read_csv(path))
        s = _clean_series(raw, "value", family.windows.dev_end)
        bn = s / FIXTURE_UNITS_PER_BN[target]
        sources[target] = {"frame": _frame_for_module(bn, family, target), "status": "loaded"}
        receipts.append(_receipt(target, rel, path, s))
    ann_path = fixture_dir / "announcements.json"
    if ann_path.exists():
        for item in json.loads(ann_path.read_text()):
            ann = dict(item)
            ann["published_at"] = datetime.fromisoformat(ann["published_at"])
            changes = []
            for change in ann.get("changes", ()):
                change = dict(change)
                change["effective"] = date.fromisoformat(str(change["effective"]))
                changes.append(change)
            ann["changes"] = changes
            announcements.append(ann)
    return sources, receipts, announcements


def _info_cutoffs(family):
    """ISO date of the last eval origin per (target, horizon) — calendar only, no data."""
    fridays = glf.panel_fridays(family.windows, family.origins)
    idx = fridays[(fridays >= pd.Timestamp(family.windows.train_start))
                  & (fridays <= pd.Timestamp(family.windows.dev_end))]
    cutoffs: dict = {}
    for target in family.targets:
        for h in family.horizons_weeks:
            origins = glf.rolling_origins(
                idx, train_end=family.windows.train_end, dev_end=family.windows.dev_end,
                reserved_start=family.windows.reserved_start,
                min_train_weeks=family.origins.min_train_weeks,
                step_weeks=family.origins.step_weeks, horizon_weeks=h,
                purge_weeks=family.windows.purge_weeks)
            cutoffs[(target, h)] = origins[-1].date().isoformat() if len(origins) else None
    return cutoffs


def _parse_args(argv):
    ap = argparse.ArgumentParser(
        description="GLT T09 preregistered component forecast study (measurement-only)")
    ap.add_argument("--config", default="config/global_liquidity_forecast_v1.yml")
    ap.add_argument("--root", default=".")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out", default="research/GLT_T09_FORECAST_RESULT_2026-10-13.json")
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--fixture", default=None)
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    root = Path(args.root).resolve()

    def _under_root(p: str) -> Path:
        q = Path(p)
        return q if q.is_absolute() else (root / q)

    ledger_path = _under_root(args.ledger).resolve()
    out_path = _under_root(args.out).resolve()
    config_path = _under_root(args.config)

    if ledger_path == (root / "data" / "trial_ledger.jsonl").resolve():
        print("refusing --ledger: data/trial_ledger.jsonl is owned by the nightly pipeline",
              file=sys.stderr)
        return 2
    for bad_dir in ("data", "site"):
        try:
            out_path.relative_to((root / bad_dir).resolve())
        except ValueError:
            continue
        print(f"refusing --out under {bad_dir}/", file=sys.stderr)
        return 2
    try:
        as_of = datetime.fromisoformat(args.as_of)
    except ValueError:
        print("--as-of must be an ISO datetime", file=sys.stderr)
        return 2
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        print("--as-of must be timezone-aware", file=sys.stderr)
        return 2

    family = glf.load_family(config_path)
    if args.fixture:
        sources, receipts, announcements = load_fixture_sources(args.fixture, family)
    else:
        sources, receipts = load_real_sources(root, family)
        announcements = []

    ledger = TrialLedger(ledger_path, family=family.name)
    new_trials = glf.register_family(ledger, family, info_cutoffs=_info_cutoffs(family))
    cells = glf.run_study(sources, family=family, announcements=announcements)
    identity = glf.reconcile_forecast_identity(None, None)  # no H.4.1 anchor input
    inputs = {
        "mode": "fixture" if args.fixture else "real",
        "announcements": len(announcements),
        "announcements_supplied": bool(announcements),
        "sources": receipts,
    }
    card = glf.result_card(
        family=family, cells=cells, inputs=inputs,
        ledger_receipt={"family": family.name, "literal_n": ledger.literal_n(),
                        "declared_budget": family.n_trials_total},
        forecast_identity=identity, as_of=as_of.isoformat())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    glf.write_card(card, out_path)

    literal_n = ledger.literal_n()
    n_issued = sum(1 for cell in cells if cell["disposition"] == "issued")
    print(f"ledger: new_trials={new_trials} literal_n={literal_n} "
          f"declared_budget={family.n_trials_total}", flush=True)
    print(f"::notice title=glt-t09::{len(cells)} cells, {n_issued} issued, "
          f"literal_n={literal_n}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
