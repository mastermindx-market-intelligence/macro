"""s1_synth.py — synthetic-frame builder used ONLY by tests/test_sni_s1_*.py.

tmp_path + synthetic data ONLY: no data/ reads, no writes outside tmp_path.
Session grids come from the real rule calendars (lib.nyse_calendar /
lib.hk_calendar) so resolver arithmetic is exercised; every PRICE is synthetic.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
for p in (str(REPO / "research/single_name_intelligence/residual"), str(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)

from lib import hk_calendar, nyse_calendar  # noqa: E402
from s1_data import InjectableStore  # noqa: E402
from s1_manifest import build_rows, manifest_bytes, split_digests  # noqa: E402
from s1_prereg import RUNS_REL, VERSION, canonical_json, prereg_digest  # noqa: E402
from run_s1 import PROTOCOL_SUBJECTS  # noqa: E402

PATHS = {
    "adr_baba": "data/yahoo/BABA.parquet",
    "hkd_9988": "data/hk_stocks/9988.HK.parquet",
    "hkd_0700": "data/hk_stocks/0700.HK.parquet",
    "SPY": "data/yahoo/SPY.parquet",
    "KWEB": "data/yahoo/KWEB.parquet",
    "2800.HK": "data/hk/2800.HK.parquet",
    "3033.HK": "data/hk/3033.HK.parquet",
}


def sessions_us(n: int, start: date = date(2019, 1, 2)) -> list:
    out, d = [], start
    while len(out) < n:
        if nyse_calendar.is_session(d):
            out.append(d)
        d += timedelta(days=1)
    return out


def sessions_hk(n: int, start: date = date(2019, 1, 2)) -> list:
    out, d = [], start
    while len(out) < n:
        if hk_calendar.is_session(d):
            out.append(d)
        d += timedelta(days=1)
    return out


def walk(dates: list, seed: int, start: float = 100.0, vol: float = 0.01) -> list:
    """Deterministic pseudo-price series aligned to dates (numpy default_rng)."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, vol, size=len(dates))
    return [float(start * float(np.prod(np.exp(r[: i + 1])))) for i in range(len(dates))]


def synth_frames(n: int = 1400, leak: bool = False) -> dict:
    """Frames for every path run_s1 touches, on real session grids. `leak`
    plants ONE adjustment-vintage step in BABA's close_price early in the TUNE
    window (a constant factor would produce no step at all)."""
    us = sessions_us(n)
    hk = sessions_hk(n)
    frames = {}
    leak_start = next(d for d in us if d >= date(2024, 4, 1))
    for key, dates, seed in (
        ("adr_baba", us, 1), ("SPY", us, 2), ("KWEB", us, 3),
        ("hkd_9988", hk, 4), ("hkd_0700", hk, 5),
        ("2800.HK", hk, 6), ("3033.HK", hk, 7),
    ):
        closes = walk(dates, seed)
        f = {"Date": list(dates), "close": closes}
        if key in ("adr_baba", "SPY", "KWEB"):
            if leak and key == "adr_baba":
                f["close_price"] = [c * (1.05 if d >= leak_start else 1.0)
                                    for c, d in zip(closes, dates)]
            else:
                f["close_price"] = list(closes)
        frames[PATHS[key]] = f
    return frames


def write_synthetic_repo(tmp: Path, frames: dict) -> InjectableStore:
    """Manifests + seal + challenger universe under tmp/<RUNS_REL>, built
    outcome-free from the injected frames."""
    store = InjectableStore(frames)
    runs = tmp / RUNS_REL
    (runs / "manifests").mkdir(parents=True)
    membership = []
    for pid in ("P01", "P02", "P03"):
        for subj in PROTOCOL_SUBJECTS[pid]:
            dates = store.index_dates(subj["data_path"])
            for h in (5, 21, 63):
                rows = build_rows(pid, subj["issuer_key"], subj["counter"],
                                  subj["security_id"], subj["market"], h, dates, dates[-1])
                name = f"{pid}_{subj['counter']}_{h}.jsonl"
                (runs / "manifests" / name).write_bytes(manifest_bytes(rows))
                for sp, info in split_digests(rows).items():
                    membership.append({
                        "protocol_id": pid, "version": VERSION, "subject": subj["counter"],
                        "security_id": subj["security_id"], "h": h, "split": sp,
                        "count": info["count"],
                        "membership_sha256": info["membership_sha256"],
                    })
    seal = {
        "lane": "s1_residual", "version": VERSION, "base": "SYNTHETIC",
        "branch": "SYNTHETIC", "input_ref": store.input_ref,
        "labels": ["synthetic"], "authority_flags": {},
        "families": {}, "trial_ledger_path": "synthetic",
        "membership_table": sorted(membership,
                                   key=lambda r: (r["protocol_id"], r["subject"], r["h"],
                                                  r["split"])),
        "s0_blob_ids": {}, "prereg_digest_sha256": prereg_digest(),
        "identity": {}, "seal_builder_audit": {"spy_calls": [], "index_only": True},
        "outcome_free": True,
    }
    (runs / "SEAL_AND_BUDGET.json").write_text(canonical_json(seal) + "\n", encoding="utf-8")
    (runs / "PREREG_SPEC.json").write_text(canonical_json(_spec()) + "\n", encoding="utf-8")
    (runs / "INPUT_MANIFEST.json").write_text(canonical_json({}) + "\n", encoding="utf-8")
    universe = {"admitted_count": 0, "admitted": [], "files_examined": 0,
                "rejected_by_reason": {}, "order": "synthetic",
                "criteria": {}, "disclosures": ["synthetic test universe: empty"]}
    (runs / "CHALLENGER_UNIVERSE.json").write_text(canonical_json(universe) + "\n",
                                                   encoding="utf-8")
    return store


def _spec() -> dict:
    from s1_prereg import build_spec
    return build_spec()
