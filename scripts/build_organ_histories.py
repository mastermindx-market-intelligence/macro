#!/usr/bin/env python3
"""Offline builder — engine alert histories for the three HOUSE organs (COO ruling 38 Part A).

Replays the engine's OWN code at one pinned commit. Every state/label/phase in the
output is the engine's own output: this script IMPORTS and CALLS the engine functions
and never copies a threshold or rule, and never edits anything under engine/.

Organs (house groups only; the vendor-keyed turn_down organ is OUT of scope):
  1. us_basket WASHED_OUT -> CONFIRMED  — engine/us_basket_turn.replay (:1041), TWO
     labelled membership versions in the same file:
       * membership_basis="dated"   : dated [added, removed) membership, PIT. This is
         the LIVE engine basis (compute_all :785 uses active_members + ew_level_from_closes
         with the dated mask), so the fidelity test applies to this version.
       * membership_basis="current" : today's active members applied as far back as the
         inputs reach (added=None, removed kept). A SENSITIVITY, not the organ history.
  2. phase_v2                          — engine/sector_cycles.build_sector (:1202) per
     session, which calls cycle_ontology.classify_phase via record_series (:668).
  3. rolling_over                      — engine/sector_central._rolling_over (:278) on the
     `now` block built by the engine's own build_sector, carried through _carry (:1127).

Inputs are read, never written. No production builder is run, no nightly is rerun.
Nothing here relates to outcomes. Git holds only group-level rows: no member ticker,
price or per-security date is emitted (the Tiingo archive is named as a source only).

Prices are RESTATED as of capture (price_basis="restated"); the sidecar says so.
The 2000-bar trailing window matches scripts/backfill_forward_logs.py:85 (WINDOW_CAP),
documented PIT-equivalent for signal fields (tests/test_backfill_pit.py).

Run:
  /opt/homebrew/Caskroom/miniconda/base/bin/python3 scripts/build_organ_histories.py
  ... --smoke          # quick mechanics check, scratch outputs
  ... --workers 12     # multiprocessing pool size
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

from lib import config                       # noqa: E402
from engine import us_basket_turn as ubt      # noqa: E402
from engine import sector_cycles as sc        # noqa: E402
from engine import sector_central as central  # noqa: E402
from engine.inputs import yahoo_closes        # noqa: E402

# ── pinned engine identity (git rev-parse origin/main at build start) ──────────────
ENGINE_CODE_SHA = "72082493cb5e29cf5fe4a093fadf6f435b6fe2c3"
# sha256 of the exact engine module bytes at the pin; the runtime self-check hashes the
# imported files against these so a drifted engine fails the build instead of silently
# producing a non-faithful history.
EXPECTED_ENGINE_HASHES = {
    "engine/us_basket_turn.py": "f32048f646d8d48169e00e59c408064b9ef375ca61993b9b37349023ef0f7a66",
    "engine/sector_cycles.py": "ed67fb446930397ffaa8149c69bf8e100870772f5244bce8c28f50b449b56286",
    "engine/sector_central.py": "9c9ada9106e53ae7bc062da86c1475829a1f517af9bffbe1ee3162b7e53dffb9",
    "engine/cycle_ontology.py": "76e5981192aa9e379869734060e71f2e80918cdf49b73b75a583ae96e73599ec",
    "engine/inputs.py": "b322465049397c1d36ff7b4ab07f131b34fd635b6624289f51bdf3b9ec205c65",
    "engine/cycles.py": "679fafe2ef043a67bd390d9d9425bb610831453f76018be49e449294e1d33f56",
}

# Locators (NOT copied rules): the window cap is the backfill's own constant; the 252
# level window is the engine's drawdown window, used only to locate first_knowable.
WINDOW_CAP = 2000                 # scripts/backfill_forward_logs.py:85
BASKET_LEVEL_WINDOW = 252         # engine/us_basket_turn.py:340 (first-knowable locator)
DESK_BLOCK = pd.Timestamp("2023-12-29")   # rows after this are kept and labelled, not dropped
REPLAY_END = "2030-01-01"         # beyond the tape; replay breaks at the last level session

SPDRS = list(sc.SECTORS.keys())   # the 11 house SPDR sector keys
SCRATCH = Path("/tmp/r38a")
CURRENT_ROOT = SCRATCH / "current_root"

HIST_DIR = ROOT / "data" / "breadth" / "history"
OUT_PARQUET = HIST_DIR / "organ_histories_house.parquet"
OUT_META = HIST_DIR / "organ_histories_house.meta.json"
OUT_REPORT = ROOT / "research" / "breadth_history" / "ORGAN_HISTORIES_REPORT.md"

NO_OUTCOME = (
    "These are engine alert histories only. Nothing in this file relates to outcomes, "
    "returns, forward performance or any grading; every state is the engine's own "
    "descriptive output replayed on restated prices."
)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ── engine-pin self-check ──────────────────────────────────────────────────────────
def verify_engine_pin() -> dict:
    got = {}
    for rel, want in EXPECTED_ENGINE_HASHES.items():
        b = (ROOT / rel).read_bytes()
        h = hashlib.sha256(b).hexdigest()
        got[rel] = h
        if h != want:
            raise SystemExit(
                f"ENGINE PIN MISMATCH: {rel}\n  want {want}\n  got  {h}\n"
                "The imported engine code differs from the pinned commit; refusing to build."
            )
    log(f"engine pin self-check OK ({len(got)} modules) @ {ENGINE_CODE_SHA}")
    return got


# ── current-version scratch root (today's members, added=None, removed kept) ───────
def setup_current_root() -> Path:
    real = config.data_dir()
    raw = json.loads((real / "baskets" / "membership.json").read_text())
    for _bid, b in (raw.get("baskets") or {}).items():
        for m in b.get("members") or []:
            m["added"] = None   # current sensitivity: no PIT add gate; removed kept so
            # active_members() still excludes removed members => today's active members.
    CURRENT_ROOT.mkdir(parents=True, exist_ok=True)
    (CURRENT_ROOT / "baskets").mkdir(parents=True, exist_ok=True)
    (CURRENT_ROOT / "baskets" / "membership.json").write_text(json.dumps(raw))
    # symlink the price stores so the engine's own _load_close ladder behaves as on main
    for sub in ("stocks", "baskets/ohlcv"):
        link = CURRENT_ROOT / sub
        target = real / sub
        if target.exists() and not link.exists():
            link.symlink_to(target, target_is_directory=True)
    return CURRENT_ROOT


# ── basket organ ───────────────────────────────────────────────────────────────────
def basket_task(args: tuple) -> dict:
    """Replay one basket in one membership version via the engine's own replay()."""
    bid, version = args
    root = config.data_dir() if version == "dated" else CURRENT_ROOT
    full = ubt.replay(bid, "1900-01-01", REPLAY_END, data_root=root)
    out = {"organ": "us_basket", "bid": bid, "version": version,
           "rows": [], "first_knowable": None, "n_sessions": len(full)}
    if not full:
        return out
    # first_knowable: the 252nd session of the engine-built level series (the engine's
    # own 252d drawdown window is fully populated here). replay emits every level session
    # when start precedes the tape, so full[i]['date'] == levels.index[i].
    fk = (full[BASKET_LEVEL_WINDOW - 1]["date"]
          if len(full) >= BASKET_LEVEL_WINDOW else full[0]["date"])
    out["first_knowable"] = fk

    # n_members: the engine's own PIT bar count on each session (_members_at_session).
    basket = ubt._load_membership(root).get(bid) or {}
    members = ubt.active_members(basket)
    closes: dict[str, pd.Series] = {}
    for m in members:
        s = ubt._load_close(m["ticker"], root)
        if s is not None:
            closes[m["ticker"]] = s

    prev_state = None
    for r in full:
        state = r["state"]
        confirmed_transition = bool(
            state == "CONFIRMED" and prev_state is not None and prev_state != "CONFIRMED"
        )
        prev_state = state
        if r["date"] < fk:
            continue
        nm = ubt._members_at_session(members, closes, r["date"])
        out["rows"].append({
            "organ": "us_basket", "level": "basket", "group_key": bid,
            "session_date": r["date"], "state": state,
            "first_knowable_date": fk, "membership_basis": version,
            "n_members": int(nm), "engine_code_sha": ENGINE_CODE_SHA,
            "after_2023_12_29": bool(pd.Timestamp(r["date"]) > DESK_BLOCK),
            "days_in_state": int(r["days_in_state"]),
            "confirmed_transition": confirmed_transition,
        })
    return out


# ── sector organs (phase_v2 + rolling_over share one build_sector call) ────────────
_G: dict = {}


def sector_init() -> None:
    closes = yahoo_closes()
    _G["closes"] = closes
    _G["closes_px"] = yahoo_closes(basis="price").reindex(closes.index)
    _G["cal"] = closes.index


def sector_task(args: tuple) -> dict:
    ticker, js = args
    closes = _G["closes"]
    closes_px = _G["closes_px"]
    cal = _G["cal"]
    meta = sc.SECTORS[ticker]
    key = ticker.lower()
    phase_rows: list[dict] = []
    roll_rows: list[dict] = []
    fk_phase = None
    fk_roll = None
    for j in js:
        lo = max(0, j + 1 - WINDOW_CAP)
        sub = closes.iloc[lo:j + 1]
        sub_px = closes_px.iloc[lo:j + 1]
        ws = sub.index[0]
        rec = sc.build_sector(ticker, meta, sub, ws, closes_px=sub_px)
        if not rec:
            continue
        now = rec.get("now") or {}
        d = str(cal[j].date())
        after = bool(cal[j] > DESK_BLOCK)
        # phase_v2 — the engine's own ontology phase
        pv2 = now.get("phase_v2")
        if pv2 is not None:
            if fk_phase is None:
                fk_phase = d
            phase_rows.append({
                "organ": "phase_v2", "level": "sector", "group_key": key,
                "session_date": d, "state": pv2,
                "first_knowable_date": fk_phase, "membership_basis": "etf_price",
                "n_members": 1, "engine_code_sha": ENGINE_CODE_SHA,
                "after_2023_12_29": after,
                "phase": now.get("phase"),
                "pos_v2": now.get("pos_v2"),
                "osc_slope": now.get("osc_slope"),
                "basis": now.get("basis"),
                "phase_v2_source": now.get("phase_v2_source"),
            })
        # rolling_over — the engine's own predicate + carried phase label
        rolling = bool(central._rolling_over(now))
        carried = central._carry(rec)
        label = (carried.get("cycle") or {}).get("phaseLabel")
        if fk_roll is None:
            fk_roll = d
        roll_rows.append({
            "organ": "rolling_over", "level": "sector", "group_key": key,
            "session_date": d, "state": label,
            "first_knowable_date": fk_roll, "membership_basis": "etf_price",
            "n_members": 1, "engine_code_sha": ENGINE_CODE_SHA,
            "after_2023_12_29": after,
            "rolling": rolling,
            "osc_slope": now.get("osc_slope"),
            "pos_v2": now.get("pos_v2"),
            "pos": now.get("pos"),
            "timing_state": now.get("timing_state"),
            "signal": now.get("signal"),
            "divergence": bool(now.get("divergence")) if now.get("divergence") is not None else None,
        })
    return {"ticker": ticker, "phase_rows": phase_rows, "roll_rows": roll_rows,
            "fk_phase": fk_phase, "fk_roll": fk_roll}


def _sector_jobs(closes: pd.DataFrame, tickers: list[str], chunk: int,
                 last_n: int | None = None) -> list[tuple]:
    """Per-ticker valid-session indices past the 300-bar build floor, chunked for the pool."""
    cal = closes.index
    jobs: list[tuple] = []
    for tk in tickers:
        valid = np.flatnonzero(closes[tk].notna().to_numpy())
        if len(valid) == 0:
            continue
        # build_sector requires len(full) >= 300; start a little before the floor and let
        # the engine's own early-return guard decide (no copied threshold beyond the floor
        # locator, which the engine itself enforces).
        start = int(valid[0]) + 299
        js = [int(j) for j in valid if int(j) >= start]
        if last_n is not None:
            js = js[-last_n:]
        for k in range(0, len(js), chunk):
            jobs.append((tk, js[k:k + chunk]))
    return jobs


# ── fidelity ───────────────────────────────────────────────────────────────────────
def _cmp_state(replay_map: dict, store_rows: list, organ: str) -> dict:
    """replay_map[(key, date)] = state; store_rows = [(key, date, stored_state)]."""
    match = 0
    mismatches: list[dict] = []
    missing = 0
    for key, date, stored in store_rows:
        got = replay_map.get((key, date))
        if got is None:
            missing += 1
            mismatches.append({"group_key": key, "session_date": date,
                               "stored": stored, "replayed": None, "kind": "missing_in_replay"})
            continue
        if got == stored:
            match += 1
        else:
            mismatches.append({"group_key": key, "session_date": date,
                               "stored": stored, "replayed": got, "kind": "state_diff"})
    total = len(store_rows)
    return {"organ": organ, "total": total, "match": match,
            "mismatch": len(mismatches), "missing_in_replay": missing,
            "mismatches": mismatches}


def fidelity_us_basket(df: pd.DataFrame) -> dict:
    led = ubt.load_ledger(config.data_dir())
    sub = df[(df["organ"] == "us_basket") & (df["membership_basis"] == "dated")]
    rmap = {(r.group_key, r.session_date): r.state for r in sub.itertuples()}
    store_rows = []
    for row in led:
        d = row.get("date") or ""
        if "2026-08-07" <= d <= "2026-11-06":
            store_rows.append((row.get("basket_id") or "", d, row.get("state")))
    res = _cmp_state(rmap, store_rows, "us_basket_dated_vs_ledger")
    res["store"] = "data/us_basket_turn/ledger.jsonl"
    res["window"] = "2026-08-07..2026-11-06"
    res["basis_note"] = ("dated version is the live engine basis "
                         "(compute_all uses active_members + ew_level_from_closes, PIT dated mask)")
    return res


def fidelity_phase_v2(df: pd.DataFrame) -> dict:
    sub = df[df["organ"] == "phase_v2"]
    rmap = {(r.group_key, r.session_date): r.state for r in sub.itertuples()}
    root = config.data_dir()
    out = {}
    # monthly backfill
    bf = pd.read_parquet(root / "sector_cycles" / "backfill.parquet")
    bf = bf[bf["id"].isin([t.lower() for t in SPDRS])]
    bf_rows = [(str(r.id), str(r.date), r.phase_v2) for r in bf.itertuples()
               if "2010-12-31" <= str(r.date) <= "2026-06-30"]
    res_bf = _cmp_state(rmap, bf_rows, "phase_v2_vs_backfill")
    res_bf["store"] = "data/sector_cycles/backfill.parquet"
    res_bf["cadence"] = "month_end"
    out["backfill"] = res_bf
    # daily forward log
    fl = pd.read_parquet(root / "sector_cycles" / "forward_log.parquet")
    fl = fl[fl["id"].isin([t.lower() for t in SPDRS])]
    fl_rows = [(str(r.id), str(r.date), r.phase_v2) for r in fl.itertuples()
               if str(r.date) >= "2026-07-02"]
    res_fl = _cmp_state(rmap, fl_rows, "phase_v2_vs_forward_log")
    res_fl["store"] = "data/sector_cycles/forward_log.parquet"
    res_fl["cadence"] = "daily"
    out["forward_log"] = res_fl
    return out


def fidelity_rolling_over(df: pd.DataFrame, n_sessions: int) -> dict:
    """No persisted store exists (ruling 38 §2d, COO accepted). Compare the replay on the
    latest available sessions with the live engine's own computation path: sc.compute(asof)
    builds each sector's `now` exactly as the nightly does, then central._rolling_over."""
    sub = df[df["organ"] == "rolling_over"]
    dates = sorted(sub["session_date"].unique())[-n_sessions:]
    rmap = {(r.group_key, r.session_date): bool(r.rolling) for r in sub.itertuples()}
    label_map = {(r.group_key, r.session_date): r.state for r in sub.itertuples()}
    match = 0
    mismatches: list[dict] = []
    compared = 0
    for d in dates:
        live = sc.compute(asof=d)
        if not live:
            continue
        for rec in live.get("sectors") or []:
            key = rec.get("id")
            now = rec.get("now") or {}
            live_rolling = bool(central._rolling_over(now))
            live_label = "Rolling over" if live_rolling else now.get("phaseLabel")
            got = rmap.get((key, d))
            if got is None:
                continue
            compared += 1
            got_label = label_map.get((key, d))
            if got == live_rolling and got_label == live_label:
                match += 1
            else:
                mismatches.append({"group_key": key, "session_date": d,
                                   "stored": live_rolling, "replayed": got,
                                   "stored_label": live_label, "replayed_label": got_label,
                                   "kind": "rolling_diff"})
    return {"organ": "rolling_over_vs_live_engine", "total": compared, "match": match,
            "mismatch": len(mismatches), "mismatches": mismatches,
            "sessions": dates, "store": None,
            "note": ("No persisted rolling series exists. Fidelity is the replay vs the live "
                     "engine's own computation (sector_cycles.compute(asof) + "
                     "sector_central._rolling_over) on the latest sessions. COO accepted "
                     "this test (ruling 38 §2d).")}


# ── assembly ───────────────────────────────────────────────────────────────────────
def assemble(basket_results: list[dict], sector_results: list[dict]) -> tuple[pd.DataFrame, dict]:
    rows: list[dict] = []
    first_knowable: dict = {}
    for br in basket_results:
        rows.extend(br["rows"])
        if br["first_knowable"]:
            first_knowable.setdefault("us_basket", {})[f"{br['bid']}|{br['version']}"] = br["first_knowable"]
    # aggregate sector first-knowable across chunks (min date per key/organ)
    fk_phase: dict[str, str] = {}
    fk_roll: dict[str, str] = {}
    for sr in sector_results:
        rows.extend(sr["phase_rows"])
        rows.extend(sr["roll_rows"])
        key = sr["ticker"].lower()
        if sr["fk_phase"] and (key not in fk_phase or sr["fk_phase"] < fk_phase[key]):
            fk_phase[key] = sr["fk_phase"]
        if sr["fk_roll"] and (key not in fk_roll or sr["fk_roll"] < fk_roll[key]):
            fk_roll[key] = sr["fk_roll"]
    # stamp the aggregated first_knowable onto sector rows (chunk-local values may differ)
    for r in rows:
        if r["organ"] == "phase_v2":
            r["first_knowable_date"] = fk_phase.get(r["group_key"], r["first_knowable_date"])
        elif r["organ"] == "rolling_over":
            r["first_knowable_date"] = fk_roll.get(r["group_key"], r["first_knowable_date"])
    first_knowable["phase_v2"] = fk_phase
    first_knowable["rolling_over"] = fk_roll

    df = pd.DataFrame(rows)
    # stable column order
    common = ["organ", "level", "group_key", "session_date", "state", "first_knowable_date",
              "membership_basis", "n_members", "engine_code_sha", "after_2023_12_29"]
    organ_fields = ["days_in_state", "confirmed_transition", "phase", "pos_v2", "osc_slope",
                    "basis", "phase_v2_source", "rolling", "pos", "timing_state", "signal",
                    "divergence"]
    cols = [c for c in common + organ_fields if c in df.columns]
    df = df[cols]
    # nullable typing for clean parquet
    for c in ("days_in_state", "n_members"):
        if c in df:
            df[c] = df[c].astype("Int64")
    for c in ("confirmed_transition", "rolling", "divergence", "after_2023_12_29"):
        if c in df:
            df[c] = df[c].astype("boolean")
    df = df.sort_values(["organ", "membership_basis", "group_key", "session_date"]).reset_index(drop=True)
    return df, first_knowable


def write_outputs(df: pd.DataFrame, first_knowable: dict, fidelity: dict,
                  engine_hashes: dict, parquet_path: Path, meta_path: Path,
                  report_path: Path, build_seconds: float) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(parquet_path, index=False)
    pb = parquet_path.read_bytes()
    parquet_sha = hashlib.sha256(pb).hexdigest()
    try:
        parquet_rel = str(parquet_path.relative_to(ROOT))
    except ValueError:                      # scratch/smoke output outside the tree
        parquet_rel = str(parquet_path)

    # per-organ row/key summaries
    organs = {}
    for organ, g in df.groupby("organ"):
        organs[organ] = {
            "rows": int(len(g)),
            "keys": int(g["group_key"].nunique()),
            "first_session": str(g["session_date"].min()),
            "last_session": str(g["session_date"].max()),
            "membership_basis": sorted(g["membership_basis"].unique().tolist()),
        }

    meta = {
        "schema": "organ_histories_house/v1",
        "engine_code_sha": ENGINE_CODE_SHA,
        "engine_module_sha256": engine_hashes,
        "price_basis": "restated",
        "price_basis_note": ("Prices are restated as of capture (the latest committed tape), "
                             "not point-in-time as-of each historical session. Fidelity against "
                             "the live stores is measured on this restated basis; mismatches are "
                             "reported, not tuned."),
        "no_outcome": NO_OUTCOME,
        "window_cap_bars": WINDOW_CAP,
        "window_cap_source": "scripts/backfill_forward_logs.py:85 (PIT-equivalent for signal fields)",
        "inputs": {
            "us_basket_membership": "data/baskets/membership.json (seed 2023-05-09)",
            "us_basket_member_closes": "data/stocks/{T}.parquet, data/baskets/ohlcv/{T}.parquet (Tiingo archive)",
            "sector_prices": "data/yahoo/{T}.parquet (11 SPDR sectors + SPY benchmark), TR + close_price basis",
            "fidelity_stores": [
                "data/us_basket_turn/ledger.jsonl",
                "data/sector_cycles/backfill.parquet",
                "data/sector_cycles/forward_log.parquet",
            ],
        },
        "membership_basis": {
            "us_basket_dated": ("Dated [added, removed) membership applied point-in-time. This is "
                                "the LIVE engine basis: compute_all (engine/us_basket_turn.py:785) "
                                "uses active_members + ew_level_from_closes with the dated mask. "
                                "The fidelity test applies to this version."),
            "us_basket_current": ("SENSITIVITY only: today's active members (added=None, removed "
                                  "kept) applied as far back as the inputs reach. Not the organ "
                                  "history and not the live basis."),
            "sector_organs": "ETF price series only; no membership concept applies (n_members=1).",
        },
        "first_knowable": {
            "method": {
                "us_basket": ("252nd session of the engine-built EW level series "
                              "(engine/us_basket_turn.py:340 drawdown window fully populated); "
                              "located from the engine's own replay output, not a copied rule."),
                "phase_v2": ("First session where the engine's build_sector returns a non-null "
                             "phase_v2 (300-bar build floor + weekly MTF warm), found empirically."),
                "rolling_over": ("First session where the engine's build_sector returns a record "
                                 "whose `now` the override predicate can read, found empirically."),
            },
            "by_organ_key": first_knowable,
        },
        "organs": organs,
        "fidelity": fidelity,
        "parquet": {"path": parquet_rel, "bytes": len(pb), "sha256": parquet_sha},
        "build_seconds": round(build_seconds, 1),
        "scope_note": ("Three HOUSE organs only (us_basket washout, phase_v2, rolling_over). "
                       "The vendor-keyed turn_down organ is out of scope for this draft."),
    }
    meta_path.write_text(json.dumps(meta, indent=2, default=str))

    # one-page report
    lines = [
        "# Engine alert histories — three HOUSE organs (COO ruling 38 Part A)",
        "",
        f"Engine pin: `{ENGINE_CODE_SHA}`. Prices: **restated** as of capture. "
        "Every state is the engine's own output; the engine was imported and called, never edited.",
        "",
        NO_OUTCOME,
        "",
        "| organ | keys | first knowable | rows | fidelity match/total |",
        "|---|---|---|---|---|",
    ]
    fk_summary = {
        "us_basket": "≈2024-05 (dated, 252-session floor); current as far back as inputs reach",
        "phase_v2": "per-key 300-bar floor + MTF warm (nine ≈2000-02, XLC ≈2019-08, XLRE ≈2017-02)",
        "rolling_over": "per-key 300-bar floor + MTF warm (same as phase_v2)",
    }
    fid_summary = {
        "us_basket": fidelity.get("us_basket", {}),
        "phase_v2": fidelity.get("phase_v2", {}),
        "rolling_over": fidelity.get("rolling_over", {}),
    }

    def _fid_str(organ: str) -> str:
        f = fid_summary.get(organ) or {}
        if organ == "phase_v2":
            bf = f.get("backfill", {})
            fl = f.get("forward_log", {})
            return (f"backfill {bf.get('match', '?')}/{bf.get('total', '?')}; "
                    f"forward {fl.get('match', '?')}/{fl.get('total', '?')}")
        return f"{f.get('match', '?')}/{f.get('total', '?')}"

    for organ in ("us_basket", "phase_v2", "rolling_over"):
        o = organs.get(organ, {})
        lines.append(f"| {organ} | {o.get('keys', '?')} | {fk_summary[organ]} | "
                     f"{o.get('rows', '?')} | {_fid_str(organ)} |")
    lines += ["", "## Fidelity detail", ""]
    ub = fidelity.get("us_basket", {})
    lines.append(f"- **us_basket (dated vs ledger.jsonl, {ub.get('window', '')})**: "
                 f"{ub.get('match', '?')}/{ub.get('total', '?')} match, "
                 f"{ub.get('mismatch', '?')} mismatch. {ub.get('basis_note', '')}")
    pv = fidelity.get("phase_v2", {})
    for nm in ("backfill", "forward_log"):
        r = pv.get(nm, {})
        lines.append(f"- **phase_v2 vs {nm}** ({r.get('cadence', '')}): "
                     f"{r.get('match', '?')}/{r.get('total', '?')} match, "
                     f"{r.get('mismatch', '?')} mismatch.")
    ro = fidelity.get("rolling_over", {})
    lines.append(f"- **rolling_over vs live engine** (latest {len(ro.get('sessions', []))} sessions): "
                 f"{ro.get('match', '?')}/{ro.get('total', '?')} match, "
                 f"{ro.get('mismatch', '?')} mismatch. {ro.get('note', '')}")
    lines += ["", "## Mismatches (every one; none tuned away)", ""]
    any_mm = False
    for label, res in (("us_basket", ub),
                       ("phase_v2/backfill", pv.get("backfill", {})),
                       ("phase_v2/forward_log", pv.get("forward_log", {})),
                       ("rolling_over", ro)):
        for mm in res.get("mismatches", []):
            any_mm = True
            lines.append(f"- {label}: {mm.get('group_key')} @ {mm.get('session_date')} "
                         f"stored={mm.get('stored')!r} replayed={mm.get('replayed')!r} "
                         f"({mm.get('kind')})")
    if not any_mm:
        lines.append("- None.")
    lines += ["", f"Parquet: `{meta['parquet']['path']}` — {meta['parquet']['bytes']} bytes, "
              f"sha256 `{meta['parquet']['sha256']}`.", ""]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))
    log(f"wrote {parquet_path} ({len(pb)} bytes, sha256 {parquet_sha})")
    log(f"wrote {meta_path}")
    log(f"wrote {report_path}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--sector-chunk", type=int, default=400)
    ap.add_argument("--rolling-fidelity-sessions", type=int, default=10)
    ap.add_argument("--smoke", action="store_true", help="quick mechanics check, scratch outputs")
    ap.add_argument("--skip-fidelity", action="store_true")
    args = ap.parse_args(argv)

    import multiprocessing as mp

    t0 = time.time()
    engine_hashes = verify_engine_pin()
    setup_current_root()
    real = config.data_dir()
    closes = yahoo_closes()
    log(f"panel {closes.shape} {closes.index.min().date()} -> {closes.index.max().date()}")

    us_baskets = sorted(ubt._load_membership(real).keys())
    tickers = SPDRS
    if args.smoke:
        us_baskets = us_baskets[:2]
        tickers = SPDRS[:2]
        log(f"SMOKE: baskets={us_baskets} tickers={tickers}")

    ctx = mp.get_context("spawn")
    basket_results: list[dict] = []
    sector_results: list[dict] = []

    # baskets: one task per (basket, version)
    basket_jobs = [(bid, v) for bid in us_baskets for v in ("dated", "current")]
    if args.smoke:
        basket_jobs = [(bid, "dated") for bid in us_baskets] + [(us_baskets[0], "current")]
    log(f"basket tasks: {len(basket_jobs)}")
    with ctx.Pool(args.workers) as pool:
        for i, res in enumerate(pool.imap_unordered(basket_task, basket_jobs)):
            basket_results.append(res)
            if (i + 1) % 10 == 0 or args.smoke:
                log(f"  baskets {i + 1}/{len(basket_jobs)} "
                    f"({res['bid']}/{res['version']} rows={len(res['rows'])})")
    log(f"baskets done in {time.time() - t0:.1f}s")

    # sectors: chunked (ticker, session-indices) tasks
    sector_jobs = _sector_jobs(closes, tickers, args.sector_chunk,
                               last_n=120 if args.smoke else None)
    log(f"sector tasks: {len(sector_jobs)}")
    ts = time.time()
    with ctx.Pool(args.workers, initializer=sector_init) as pool:
        for i, res in enumerate(pool.imap_unordered(sector_task, sector_jobs)):
            sector_results.append(res)
            if (i + 1) % 20 == 0 or args.smoke:
                log(f"  sectors {i + 1}/{len(sector_jobs)} "
                    f"({res['ticker']} phase={len(res['phase_rows'])} roll={len(res['roll_rows'])})")
    log(f"sectors done in {time.time() - ts:.1f}s")

    df, first_knowable = assemble(basket_results, sector_results)
    log(f"assembled {len(df)} rows; organs={df['organ'].value_counts().to_dict()}")

    fidelity: dict = {}
    if not args.skip_fidelity:
        tf = time.time()
        fidelity["us_basket"] = fidelity_us_basket(df)
        fidelity["phase_v2"] = fidelity_phase_v2(df)
        fidelity["rolling_over"] = fidelity_rolling_over(df, args.rolling_fidelity_sessions)
        log(f"fidelity done in {time.time() - tf:.1f}s")
        log(f"  us_basket {fidelity['us_basket']['match']}/{fidelity['us_basket']['total']} "
            f"mm={fidelity['us_basket']['mismatch']}")
        for nm in ("backfill", "forward_log"):
            r = fidelity["phase_v2"][nm]
            log(f"  phase_v2/{nm} {r['match']}/{r['total']} mm={r['mismatch']}")
        ro = fidelity["rolling_over"]
        log(f"  rolling_over {ro['match']}/{ro['total']} mm={ro['mismatch']}")

    if args.smoke:
        pq = SCRATCH / "smoke_organ_histories_house.parquet"
        mt = SCRATCH / "smoke_organ_histories_house.meta.json"
        rp = SCRATCH / "smoke_ORGAN_HISTORIES_REPORT.md"
    else:
        pq, mt, rp = OUT_PARQUET, OUT_META, OUT_REPORT
    write_outputs(df, first_knowable, fidelity, engine_hashes, pq, mt, rp, time.time() - t0)
    log(f"TOTAL {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
