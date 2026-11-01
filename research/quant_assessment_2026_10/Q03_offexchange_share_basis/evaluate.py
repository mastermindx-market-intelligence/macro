from __future__ import annotations

"""Q03 evaluation — off-exchange participation share basis (research only).

Usage:
    python evaluate.py --stage baseline
    python evaluate.py --stage primary

Refuses to run unless sha256(PREREG.md) equals the hash recorded in FREEZE.log.
Appends one JSON line per run to RUNS.log with the command, exit code, input
sha256s and output sha256s. Reads macro-main data READ-ONLY (columns
date/ticker/total_vol only; short-ratio columns are never read).
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine import darkpool_signals as dps  # noqa: E402
from engine import offexchange_share_basis as sb  # noqa: E402

DATA = Path(os.environ.get("Q03_DATA_DIR",
                           "/Users/chriswong/Documents/Cluade/macro-main/data"))
PANEL = DATA / "finra_short_volume" / "panel.parquet"
PANEL_DEEP = DATA / "finra_short_volume" / "panel_deep.parquet"
STORE = DATA / "edgar" / "share_quality_reference.json"
YAHOO = DATA / "yahoo"
PREREG = HERE / "PREREG.md"
FREEZE = HERE / "FREEZE.log"
RUNS = HERE / "RUNS.log"
RESULTS = HERE / "results"

# ── frozen parameters (PREREG §4, §7–§10) ──────────────────────────────────────
PRE_N = 40
POST_N = 40
MIN_VALID = 30
MIN_LOG_RATIO = math.log(1.5)
EFF_SLACK_DAYS = 5
MIN_CONTROLS = 5
TRAIN_FRAC = 0.4
BAR = math.log(1.25)
N_BOOT = 10_000
SEED = 3003
MIN_HOLDOUT_EVENTS = 6
MIN_HOLDOUT_BLOCKS = 4
SHARE_OK = 0.80
FIRE_TOL = 3
Z_POST = 20


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_hash() -> str:
    m = re.search(r"sha256=([0-9a-f]{64})", FREEZE.read_text())
    if not m:
        raise SystemExit("FREEZE.log carries no sha256")
    return m.group(1)


# ── loaders (replicate incumbent desk conventions, read-only) ───────────────────
def load_panel() -> pd.DataFrame:
    frames = []
    for p in (PANEL_DEEP, PANEL):
        frames.append(pd.read_parquet(p, columns=["date", "ticker", "total_vol"]))
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(subset=["date", "ticker"], keep="last")
    return df.sort_values(["date", "ticker"])


def load_yahoo(tk: str, hashes: dict) -> pd.Series | None:
    p = YAHOO / f"{tk}.parquet"
    if not p.exists():
        return None
    hashes[tk] = sha_file(p)
    df = pd.read_parquet(p)
    df.index = pd.to_datetime(df.index).normalize()
    if "volume" not in df.columns:
        return None
    s = df["volume"].dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s if not s.empty else None


def joined(tk: str, panel_by_tk: dict, hashes: dict):
    fin = panel_by_tk.get(tk)
    if fin is None or fin.empty:
        return None
    vol = load_yahoo(tk, hashes)
    if vol is None:
        return None
    as_of = vol.index.max()
    j = pd.DataFrame({"finra": fin}).join(pd.DataFrame({"vendor": vol}), how="inner")
    j = j.sort_index()
    if j.empty:
        return None
    return j, as_of


def vintage_for(tk: str, entry: dict | None, first_date, store_id: str):
    if entry is None:
        return sb.FactorVintage(ticker=tk, vintage_id=store_id, source="share_quality_reference",
                                actions=(), attested=False)
    acts = []
    for d, r in sorted((entry.get("splits") or {}).items()):
        ts = pd.Timestamp(d)
        if first_date is not None and ts <= first_date:
            continue
        acts.append(sb.CorporateAction(ts, float(r)))
    fetched = entry.get("fetched")
    return sb.FactorVintage(ticker=tk, vintage_id=f"{store_id}:{fetched}",
                            source="share_quality_reference", actions=tuple(acts),
                            attested=True,
                            attested_through=pd.Timestamp(fetched) if fetched else None)


def all_actions(entry: dict) -> list[tuple[pd.Timestamp, float]]:
    return [(pd.Timestamp(d), float(r)) for d, r in sorted((entry.get("splits") or {}).items())]


def read_series(tk, j, as_of, vint):
    r = sb.normalize_participation(
        tk, list(j.index), list(j["finra"].astype(float)), list(j["vendor"].astype(float)),
        vint, denominator_convention=sb.ADJUSTED_AS_OF, denominator_as_of=as_of)
    return r


def window_vals(read, idx: int, horizon):
    """(pre_corr, post_corr, pre_raw, post_raw, post_dates) over VALID rows with p>0."""
    pos = read.positions
    lo = max(0, idx - PRE_N)
    pre_i = range(lo, idx)
    post_i = [k for k in range(idx, min(len(pos), idx + POST_N))
              if horizon is None or pos[k] <= horizon]

    def ok(k):
        p = read.participation[k]
        return read.row_class[k] == sb.VALID and p is not None and p > 0

    pre = [k for k in pre_i if ok(k)]
    post = [k for k in post_i if ok(k)]
    return pre, post, post_i


def level_shift(vals_pre, vals_post) -> float:
    return float(np.median(np.log(vals_post)) - np.median(np.log(vals_pre)))


_POS_CACHE: dict = {}


def first_idx_on_or_after(pos, d) -> int | None:
    key = (id(pos), len(pos))
    arr = _POS_CACHE.get(key)
    if arr is None:
        arr = np.array(pos, dtype="datetime64[ns]")
        _POS_CACHE[key] = arr
    k = int(np.searchsorted(arr, np.datetime64(d), side="left"))
    return k if k < len(pos) else None


def break_stats(vals, idx_in_window):
    s = pd.Series(vals, dtype="float64")
    b = dps.share_break_index(s)
    usable = dps.usable_history(s)
    literal = b is not None and abs(b - idx_in_window) <= FIRE_TOL
    anyw = b is not None and idx_in_window <= b <= idx_in_window + POST_N - 1
    return {"break_index": b, "fire_pm3": bool(literal), "fire_in_post_window": bool(anyw),
            "rows_discarded": int(len(s) - len(usable))}


def post_abs_z(series_vals: list, start: int) -> float | None:
    zs = []
    for j in range(start, min(len(series_vals), start + Z_POST)):
        hist = series_vals[max(0, j - dps.Z_WINDOW):j + 1]
        z = dps.trailing_z(hist)
        if z is not None:
            zs.append(abs(z))
    return float(np.median(zs)) if zs else None


# ── stages ─────────────────────────────────────────────────────────────────────
def stage_baseline(inputs: dict, outputs: dict) -> dict:
    # 1) fixture: true 0.2, mismatched 0.02 at 10:1, restored 0.2
    pos = list(range(80))
    raw_cons = [1e6 if i < 40 else 1e7 for i in pos]
    finra = [0.2 * c for c in raw_cons]
    vendor = [c * 10 if i < 40 else c for i, c in zip(pos, raw_cons)]
    fv = sb.FactorVintage("FIX", "fixture", "fixture", (sb.CorporateAction(40, 10.0),))
    fr = sb.normalize_participation("FIX", pos, finra, vendor, fv,
                                    denominator_convention=sb.ADJUSTED_AS_OF, denominator_as_of=79)
    fixture = {
        "true_participation": 0.2,
        "mismatched_pre_split": fr.raw_participation[0],
        "factor": fr.factor_applied[0],
        "restored_pre_split": fr.participation[0],
        "incumbent_break_index_raw": dps.share_break_index(pd.Series(fr.raw_participation)),
        "incumbent_break_index_corrected": dps.share_break_index(pd.Series(fr.participation)),
    }
    # 2) retained case: AVGO 10:1 effective 2024-07-15
    store_raw = STORE.read_bytes()
    inputs["share_quality_reference.json"] = hashlib.sha256(store_raw).hexdigest()
    store = json.loads(store_raw)
    panel = load_panel()
    fin = panel[panel["ticker"] == "AVGO"].set_index("date")["total_vol"]
    yh: dict = {}
    jj = joined("AVGO", {"AVGO": fin}, yh)
    inputs.update({f"yahoo/{k}.parquet": v for k, v in yh.items()})
    j, as_of = jj
    entry = store["tickers"].get("AVGO")
    vint = vintage_for("AVGO", entry, j.index.min(), inputs["share_quality_reference.json"][:12])
    rd = read_series("AVGO", j, as_of, vint)
    d = pd.Timestamp("2024-07-15")
    idx = first_idx_on_or_after(rd.positions, d)
    pre, post, _ = window_vals(rd, idx, vint.attested_through)
    corr = rd.participation
    raw = rd.raw_participation
    full_raw = [x for x in raw if x is not None and x > 0]
    full_corr = [x for x, c in zip(corr, rd.row_class) if c == sb.VALID and x is not None and x > 0]
    case = {
        "ticker": "AVGO", "effective": str(d.date()), "store_entry": entry,
        "vendor_as_of": str(as_of.date()), "joined_rows": len(j),
        "first_joined": str(j.index.min().date()), "last_joined": str(j.index.max().date()),
        "valid_pre": len(pre), "valid_post": len(post),
        "median_pre_raw": float(np.median([raw[k] for k in pre])),
        "median_post_raw": float(np.median([raw[k] for k in post])),
        "median_pre_corr": float(np.median([corr[k] for k in pre])),
        "median_post_corr": float(np.median([corr[k] for k in post])),
        "D_raw": level_shift([raw[k] for k in pre], [raw[k] for k in post]),
        "D_corr": level_shift([corr[k] for k in pre], [corr[k] for k in post]),
        "log_ratio": math.log(10.0),
        "incumbent_full_raw": {"break_index": dps.share_break_index(pd.Series(full_raw)),
                               "rows": len(full_raw),
                               "usable_rows": int(len(dps.usable_history(pd.Series(full_raw))))},
        "incumbent_full_corr": {"break_index": dps.share_break_index(pd.Series(full_corr)),
                                "rows": len(full_corr),
                                "usable_rows": int(len(dps.usable_history(pd.Series(full_corr))))},
        "result_id": rd.result_id, "level_status": rd.level_status,
    }
    out = {"stage": "baseline", "fixture": fixture, "retained_case": case}
    p = RESULTS / "baseline.json"
    p.write_text(json.dumps(out, indent=2, default=str))
    outputs["results/baseline.json"] = sha_file(p)
    return out


def stage_primary(inputs: dict, outputs: dict) -> dict:
    store_raw = STORE.read_bytes()
    store_sha = hashlib.sha256(store_raw).hexdigest()
    inputs["share_quality_reference.json"] = store_sha
    store = json.loads(store_raw)["tickers"]
    panel = load_panel()
    panel_by_tk = {tk: g.set_index("date")["total_vol"] for tk, g in panel.groupby("ticker")}
    tickers = sorted(panel_by_tk)
    yh: dict = {}
    reads, meta, attrition = {}, {}, []
    unattested_breaks = []
    for tk in tickers:
        jj = joined(tk, panel_by_tk, yh)
        if jj is None:
            continue
        j, as_of = jj
        entry = store.get(tk)
        if entry is None:
            vals = [float(a) / float(b) for a, b in zip(j["finra"], j["vendor"])
                    if pd.notna(a) and pd.notna(b) and b > 0 and a >= 0]
            bi = dps.share_break_index(pd.Series(vals))
            if bi is not None:
                unattested_breaks.append({"ticker": tk, "break_index": bi, "rows": len(vals)})
            continue
        if not entry.get("fetched"):
            attrition.append({"ticker": tk, "effective": "", "ratio": "", "rule": "NO_FETCHED_STAMP"})
            continue
        vint = vintage_for(tk, entry, j.index.min(), store_sha[:12])
        reads[tk] = read_series(tk, j, as_of, vint)
        meta[tk] = {"entry": entry, "as_of": as_of, "H": vint.attested_through,
                    "first": j.index.min(), "last": j.index.max()}
    inputs["yahoo_files_count"] = len(yh)
    inputs["yahoo_files_digest"] = hashlib.sha256(
        json.dumps(sorted(yh.items())).encode()).hexdigest()
    yp = RESULTS / "yahoo_inputs.json"
    yp.write_text(json.dumps(dict(sorted(yh.items())), indent=0))
    outputs["results/yahoo_inputs.json"] = sha_file(yp)

    # controls: attested, no store action with date in [first joined, H]
    controls = [tk for tk, m in meta.items()
                if not any(m["first"] <= d <= m["H"] for d, _ in all_actions(m["entry"]))]
    control_identity_ok = True
    for tk in controls:
        r = reads[tk]
        if r.participation != r.raw_participation:
            control_identity_ok = False

    events = []
    z_cache: dict = {}
    for tk, m in meta.items():
        acts = all_actions(m["entry"])
        rd = reads[tk]
        pos = rd.positions
        for d, ratio in acts:
            if not (m["first"] <= d <= m["last"]):
                continue
            row = {"ticker": tk, "effective": str(d.date()), "ratio": ratio}
            kind = sb.classify_ratio(ratio)
            if kind not in (sb.FORWARD_SPLIT, sb.REVERSE_SPLIT):
                attrition.append({**row, "rule": f"R1_KIND_{kind}"}); continue
            if abs(math.log(ratio)) < MIN_LOG_RATIO:
                attrition.append({**row, "rule": "R1_RATIO_BELOW_1.5"}); continue
            idx = first_idx_on_or_after(pos, d)
            if idx is None or (pos[idx] - d).days > EFF_SLACK_DAYS:
                attrition.append({**row, "rule": "R2_NO_EFFECTIVE_ROW"}); continue
            pre, post, post_i = window_vals(rd, idx, m["H"])
            if len(pre) < MIN_VALID or len(post) < MIN_VALID:
                attrition.append({**row, "rule": f"R4_SUPPORT pre={len(pre)} post={len(post)}"})
                continue
            w_lo = pos[max(0, idx - PRE_N)]
            w_hi = pos[post_i[-1]]
            if any(w_lo <= d2 <= w_hi and d2 != d for d2, _ in acts):
                attrition.append({**row, "rule": "R5_OTHER_ACTION_IN_WINDOW"}); continue
            corr = rd.participation
            raw = rd.raw_participation
            pre_c, post_c = [corr[k] for k in pre], [corr[k] for k in post]
            pre_r, post_r = [raw[k] for k in pre], [raw[k] for k in post]
            # same-date controls
            cD = []
            cz = []
            for c in controls:
                if c == tk or meta[c]["H"] < w_hi:
                    continue
                cr = reads[c]
                cpos = cr.positions
                ci = first_idx_on_or_after(cpos, d)
                if ci is None or (cpos[ci] - d).days > EFF_SLACK_DAYS:
                    continue
                cpre, cpost, _ = window_vals(cr, ci, meta[c]["H"])
                if len(cpre) < MIN_VALID or len(cpost) < MIN_VALID:
                    continue
                cv = cr.participation
                cD.append(level_shift([cv[k] for k in cpre], [cv[k] for k in cpost]))
                zk = (c, ci)
                if zk not in z_cache:
                    cvals = [x if x is not None else np.nan for x in cv]
                    z_cache[zk] = post_abs_z(cvals, ci)
                z = z_cache[zk]
                if z is not None:
                    cz.append(z)
            if len(cD) < MIN_CONTROLS:
                attrition.append({**row, "rule": f"CONTROLS_{len(cD)}_LT_{MIN_CONTROLS}"})
                continue
            cmed = float(np.median(cD))
            D_c = level_shift(pre_c, post_c)
            D_r = level_shift(pre_r, post_r)
            win_idx = list(pre) + list(post)
            k0 = len(pre)
            bs_raw = break_stats([raw[k] for k in win_idx], k0)
            bs_cor = break_stats([corr[k] for k in win_idx], k0)
            raw_vals = [x if x is not None else np.nan for x in raw]
            cor_vals = [x if x is not None else np.nan for x in corr]
            events.append({
                **row, "kind": kind, "log_ratio": math.log(ratio),
                "quarter": f"{d.year}Q{(d.month - 1) // 3 + 1}",
                "valid_pre": len(pre), "valid_post": len(post), "n_controls": len(cD),
                "D_corr": D_c, "D_raw": D_r, "control_median_D": cmed,
                "E_corr": D_c - cmed, "E_raw": D_r - cmed,
                "inc_raw_fire_pm3": bs_raw["fire_pm3"],
                "inc_raw_fire_post": bs_raw["fire_in_post_window"],
                "inc_raw_rows_discarded": bs_raw["rows_discarded"],
                "inc_corr_fire_pm3": bs_cor["fire_pm3"],
                "inc_corr_fire_post": bs_cor["fire_in_post_window"],
                "inc_corr_rows_discarded": bs_cor["rows_discarded"],
                "post_abs_z_raw": post_abs_z(raw_vals, idx),
                "post_abs_z_corr": post_abs_z(cor_vals, idx),
                "post_abs_z_controls_median": float(np.median(cz)) if cz else None,
                "level_status": rd.level_status,
            })

    events.sort(key=lambda e: (e["effective"], e["ticker"]))
    n = len(events)
    n_train = int(math.floor(TRAIN_FRAC * n))
    train, hold = events[:n_train], events[n_train:]
    for e in train:
        e["split"] = "train"
    for e in hold:
        e["split"] = "holdout"

    def honest(es):
        return {"events": len(es), "tickers": len({e["ticker"] for e in es}),
                "quarter_blocks": len({e["quarter"] for e in es})}

    diag = None
    if train:
        mr = float(np.median([e["E_raw"] for e in train]))
        ml = float(np.median([e["log_ratio"] for e in train]))
        diag = {"median_E_raw": mr, "median_log_ratio": ml,
                "A1_consistent": abs(mr - ml) <= BAR}

    boot = None
    gates = {}
    hn = honest(hold)
    if hn["events"] < MIN_HOLDOUT_EVENTS or hn["quarter_blocks"] < MIN_HOLDOUT_BLOCKS:
        verdict = "INSUFFICIENT_DATA"
    else:
        blocks = sorted({e["quarter"] for e in hold})
        by_b = {b: np.array([e["E_corr"] for e in hold if e["quarter"] == b]) for b in blocks}
        by_b_raw = {b: np.array([e["E_raw"] for e in hold if e["quarter"] == b]) for b in blocks}
        rng = np.random.default_rng(SEED)
        meds, meds_raw = np.empty(N_BOOT), np.empty(N_BOOT)
        for i in range(N_BOOT):
            pick = rng.integers(0, len(blocks), len(blocks))
            meds[i] = np.median(np.concatenate([by_b[blocks[k]] for k in pick]))
            meds_raw[i] = np.median(np.concatenate([by_b_raw[blocks[k]] for k in pick]))
        e_corr = np.array([e["E_corr"] for e in hold])
        e_raw = np.array([e["E_raw"] for e in hold])
        boot = {
            "median_E_corr": float(np.median(e_corr)),
            "ci95_E_corr": [float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))],
            "median_E_raw": float(np.median(e_raw)),
            "ci95_E_raw": [float(np.percentile(meds_raw, 2.5)), float(np.percentile(meds_raw, 97.5))],
            "share_abs_E_corr_le_bar": float(np.mean(np.abs(e_corr) <= BAR)),
            "share_abs_E_raw_le_bar": float(np.mean(np.abs(e_raw) <= BAR)),
            "blocks": blocks,
        }
        gates = {
            "a_ci_within_bar": bool(-BAR <= boot["ci95_E_corr"][0] and boot["ci95_E_corr"][1] <= BAR),
            "b_share_within_bar": bool(boot["share_abs_E_corr_le_bar"] >= SHARE_OK),
            "c_controls_identity": bool(control_identity_ok),
        }
        verdict = None  # finalized after the panel re-hash in main()

    def rate(es, k):
        return float(np.mean([bool(e[k]) for e in es])) if es else None

    summary = {
        "stage": "primary",
        "params": {"PRE_N": PRE_N, "POST_N": POST_N, "MIN_VALID": MIN_VALID,
                   "MIN_LOG_RATIO": MIN_LOG_RATIO, "BAR": BAR, "N_BOOT": N_BOOT, "SEED": SEED,
                   "TRAIN_FRAC": TRAIN_FRAC, "MIN_CONTROLS": MIN_CONTROLS},
        "coverage": {"panel_tickers": len(tickers),
                     "attested_joined_tickers": len(reads), "controls_pool": len(controls),
                     "unattested_tickers_with_incumbent_break": len(unattested_breaks),
                     "unattested_break_names": sorted(u["ticker"] for u in unattested_breaks)},
        "honest_n": {"all": honest(events), "train": honest(train), "holdout": hn},
        "training_diagnostic_A1": diag,
        "holdout_bootstrap": boot,
        "gates": gates,
        "control_identity_ok": control_identity_ok,
        "incumbent_comparator": {
            "holdout_raw_fire_pm3_rate": rate(hold, "inc_raw_fire_pm3"),
            "holdout_raw_fire_post_rate": rate(hold, "inc_raw_fire_post"),
            "holdout_corr_fire_pm3_rate": rate(hold, "inc_corr_fire_pm3"),
            "holdout_corr_fire_post_rate": rate(hold, "inc_corr_fire_post"),
            "all_raw_fire_post_rate": rate(events, "inc_raw_fire_post"),
            "all_corr_fire_post_rate": rate(events, "inc_corr_fire_post"),
        },
        "attrition_counts": pd.Series([a["rule"].split(" ")[0] for a in attrition]).value_counts().to_dict()
        if attrition else {},
        "verdict_pre_integrity": verdict,
    }
    ev = RESULTS / "events.csv"
    pd.DataFrame(events).to_csv(ev, index=False)
    outputs["results/events.csv"] = sha_file(ev)
    at = RESULTS / "attrition.csv"
    pd.DataFrame(attrition, columns=["ticker", "effective", "ratio", "rule"]).to_csv(at, index=False)
    outputs["results/attrition.csv"] = sha_file(at)
    return summary


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["baseline", "primary"], required=True)
    a = ap.parse_args(argv)
    inputs: dict = {}
    outputs: dict = {}
    code = 1
    err = None
    try:
        got = sha_file(PREREG)
        want = frozen_hash()
        inputs["PREREG.md"] = got
        if got != want:
            err = f"REFUSED: sha256(PREREG.md)={got} != FREEZE.log {want}"
            print(err, file=sys.stderr)
            code = 2
            return code
        inputs["evaluate.py"] = sha_file(Path(__file__).resolve())
        inputs["engine/offexchange_share_basis.py"] = sha_file(ROOT / "engine" / "offexchange_share_basis.py")
        inputs["engine/darkpool_signals.py"] = sha_file(ROOT / "engine" / "darkpool_signals.py")
        before = {"panel.parquet": sha_file(PANEL), "panel_deep.parquet": sha_file(PANEL_DEEP)}
        inputs.update(before)
        RESULTS.mkdir(exist_ok=True)
        if a.stage == "baseline":
            out = stage_baseline(inputs, outputs)
            print(json.dumps(out, indent=2, default=str))
        else:
            out = stage_primary(inputs, outputs)
            after = {"panel.parquet": sha_file(PANEL), "panel_deep.parquet": sha_file(PANEL_DEEP)}
            integrity = (after == before)
            out["panel_sha_before"] = before
            out["panel_sha_after"] = after
            out["gates"]["d_panel_unchanged_no_short_columns"] = bool(integrity)
            if out["verdict_pre_integrity"] == "INSUFFICIENT_DATA":
                out["verdict"] = "INSUFFICIENT_DATA"
            else:
                out["verdict"] = "KEEP" if all(out["gates"].values()) else "REJECT"
            p = RESULTS / "primary.json"
            p.write_text(json.dumps(out, indent=2, default=str))
            outputs["results/primary.json"] = sha_file(p)
            print(json.dumps(out, indent=2, default=str))
        code = 0
        return code
    except SystemExit as e:
        err = str(e)
        code = 2
        return code
    except Exception:  # noqa: BLE001
        err = traceback.format_exc(limit=5)
        print(err, file=sys.stderr)
        code = 1
        return code
    finally:
        rec = {"command": "python " + " ".join([str(Path(__file__).name)] + argv),
               "stage": a.stage, "exit_code": code, "inputs_sha256": inputs,
               "outputs_sha256": outputs}
        if err:
            rec["error"] = err[-800:]
        with open(RUNS, "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
