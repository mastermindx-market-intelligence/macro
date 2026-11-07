"""China Market State P3 validation harness.

Research-only reconstruction of the existing six-leg China Market State display
score. The committed preregistration contract MUST predate every forward-outcome
calculation produced by this script.

No production score, weight, cut, mapping, ledger, UI, sizing, Risk Radar,
Portfolio, or Prophet behavior is modified.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import multiprocessing as mp
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine import china_conditions as cc
from engine import china_regime as cr
from engine import cycles
from engine import market_state as ms
from engine.china_inputs import build_features
from engine.grading_stats import BOOT_DRAWS, BOOT_SEED, effective_n
from engine.market_state_cn import _CN_INDICES
from lib import store

PREREG_DIR = ROOT / "research" / "cn_market_state_validation"
PREREG_PATH = PREREG_DIR / "preregistration.v1.json"
MODEL_MANIFEST_PATH = PREREG_DIR / "model_source_manifest.v1.json"
INPUT_MANIFEST_PATH = PREREG_DIR / "input_manifest.v1.json"
METHOD_MANIFEST_PATH = PREREG_DIR / "method_manifest.v1.json"
DEFAULT_OUT = PREREG_DIR / "results_summary.v1.json"

_TREND_FRAME: pd.DataFrame | None = None


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_json(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_prereg() -> dict:
    doc = _read_json(PREREG_PATH)
    claimed = doc.get("prereg_payload_sha256")
    core = {k: v for k, v in doc.items() if k != "prereg_payload_sha256"}
    got = _sha256_json(core)
    if not claimed or got != claimed:
        raise RuntimeError(f"prereg payload mismatch: claimed={claimed} got={got}")

    for p in (MODEL_MANIFEST_PATH, INPUT_MANIFEST_PATH, METHOD_MANIFEST_PATH):
        man = _read_json(p)
        for row in man["entries"]:
            rel = row["path"]
            fp = ROOT / rel
            if not fp.exists():
                raise RuntimeError(f"frozen manifest path missing: {rel}")
            blob = subprocess.check_output(
                ["git", "hash-object", str(fp)], cwd=ROOT, text=True
            ).strip()
            if blob != row["git_blob_sha"]:
                raise RuntimeError(
                    f"frozen manifest mismatch: {rel} "
                    f"expected={row['git_blob_sha']} got={blob}"
                )
    return doc


def shcomp_sessions(sample_end: str) -> pd.DatetimeIndex:
    df = store.read("china", "000001.SS")
    if df is None or "close" not in df:
        raise RuntimeError("Shanghai Composite store missing")
    s = df["close"].dropna().loc[:pd.Timestamp(sample_end)]
    return pd.DatetimeIndex(s.index).drop_duplicates().sort_values()


def next_session_strictly_after(
    day: pd.Timestamp, sessions: pd.DatetimeIndex
) -> pd.Timestamp | None:
    d = pd.Timestamp(day)
    if d.tzinfo is not None:
        d = d.tz_localize(None)
    d = d.normalize()
    i = int(sessions.searchsorted(d, side="right"))
    return sessions[i] if i < len(sessions) else None


def availability_calendar_date(ref: pd.Timestamp, rule: str) -> pd.Timestamp:
    ref = pd.Timestamp(ref).normalize()
    if rule == "pmi_month_end":
        return ref + pd.offsets.MonthEnd(0)
    nxt = ref + pd.offsets.MonthBegin(1)
    if rule == "next_month_16":
        return nxt.replace(day=16)
    if rule == "next_month_20":
        return nxt.replace(day=20)
    raise ValueError(rule)


def shift_series_to_release(
    s: pd.Series, sessions: pd.DatetimeIndex, rule: str
) -> pd.Series:
    rows: dict[pd.Timestamp, float] = {}
    for d, v in s.dropna().items():
        act = next_session_strictly_after(
            availability_calendar_date(pd.Timestamp(d), rule), sessions
        )
        if act is not None:
            rows[act] = float(v)
    return pd.Series(rows, dtype=float).sort_index()


def shift_frame_by_calendar_rule(
    df: pd.DataFrame, sessions: pd.DatetimeIndex, rule: str
) -> pd.DataFrame:
    rows: dict[pd.Timestamp, pd.Series] = {}
    for d, row in df.iterrows():
        act = next_session_strictly_after(
            availability_calendar_date(pd.Timestamp(d), rule), sessions
        )
        if act is not None:
            rows[act] = row
    if not rows:
        return pd.DataFrame(columns=df.columns)
    out = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    return out[~out.index.duplicated(keep="last")]


def shift_tsf_to_release(
    df: pd.DataFrame, sessions: pd.DatetimeIndex
) -> pd.DataFrame:
    rows: dict[pd.Timestamp, pd.Series] = {}
    for d, row in df.iterrows():
        av = pd.to_datetime(row.get("availability_date"), errors="coerce")
        if pd.isna(av):
            av = availability_calendar_date(pd.Timestamp(d), "next_month_16")
        act = next_session_strictly_after(pd.Timestamp(av), sessions)
        if act is not None:
            rows[act] = row
    if not rows:
        return pd.DataFrame(columns=df.columns)
    out = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    return out[~out.index.duplicated(keep="last")]


def align_like_production(
    idx: pd.DatetimeIndex, s: pd.Series, limit: int | None
) -> pd.Series:
    s = s[~s.index.duplicated(keep="last")].sort_index()
    u = idx.union(s.index)
    x = s.reindex(u)
    if limit:
        x = x.ffill(limit=limit)
    return x.reindex(idx)


def build_release_lagged_view(
    reference: pd.DataFrame, sample_end: str
) -> tuple[pd.DataFrame, dict]:
    sessions = shcomp_sessions(sample_end)
    f = reference.copy()
    idx = pd.DatetimeIndex(f.index)
    specs = [
        ("pmi", "pmi_mfg", "pmi_month_end", 90),
        ("pmi", "pmi_nonmfg", "pmi_month_end", 90),
        ("ppi", "ppi_yoy", "next_month_16", 90),
        ("money_supply", "m2_yoy", "next_month_16", 90),
        ("money_supply", "m1_yoy", "next_month_16", 90),
        ("gdp", "gdp_yoy", "next_month_20", 130),
    ]
    for name, col, rule, limit in specs:
        raw = store.read("china_macro", name)
        if raw is None or col not in raw:
            f[col] = np.nan
            continue
        shifted = shift_series_to_release(raw[col], sessions, rule)
        f[col] = align_like_production(idx, shifted, limit)

    overrides: dict[tuple[str, str], pd.DataFrame] = {}
    tsf = store.read("china_credit", "tsf")
    hp = store.read("china_property", "home_price")
    if tsf is not None:
        overrides[("china_credit", "tsf")] = shift_tsf_to_release(tsf, sessions)
    if hp is not None:
        overrides[("china_property", "home_price")] = shift_frame_by_calendar_rule(
            hp, sessions, "next_month_20"
        )
    return f, overrides


@contextlib.contextmanager
def store_read_overrides(overrides: dict[tuple[str, str], pd.DataFrame]):
    original = store.read

    def read(group: str, name: str):
        key = (group, name)
        if key in overrides:
            return overrides[key]
        return original(group, name)

    store.read = read
    try:
        yield
    finally:
        store.read = original


def int_component(s01: pd.Series) -> pd.Series:
    return (s01.clip(0, 1) * 100).round().astype("Float64")


def risk_component(rf: pd.DataFrame) -> pd.Series:
    r = rf.get("roro")
    if r is None:
        return pd.Series(index=rf.index, dtype="Float64")
    base = pd.Series(0.5, index=rf.index, dtype=float)
    base[r > 0.35] = 0.78
    base[r < -0.35] = 0.22
    cols = [
        f"roro_{k}" for k, _en, _zh in cc._RORO_LEG_META
        if f"roro_{k}" in rf.columns
    ]
    if cols:
        legs = rf[cols]
        pos = (legs > 0).sum(axis=1)
        neg = (legs < 0).sum(axis=1)
        n = pos + neg
        base = (base + (((pos - neg) / n.where(n > 0)) * 0.12).fillna(0)).clip(0, 1)
    out = int_component(base)
    out[r.isna()] = pd.NA
    return out


def vol_component(rf: pd.DataFrame) -> pd.Series:
    q = rf["roro_qvix"] if "roro_qvix" in rf else pd.Series(np.nan, index=rf.index)
    m = rf["roro_margin"] if "roro_margin" in rf else pd.Series(np.nan, index=rf.index)
    q_s = (0.5 + q * 0.18).clip(0, 1)
    m_s = (0.5 + m * 0.18).clip(0, 1)
    num = q_s.fillna(0) * 0.62 + m_s.fillna(0) * 0.38
    den = q.notna().astype(float) * 0.62 + m.notna().astype(float) * 0.38
    return int_component(num / den.replace(0, np.nan))


def breadth_component(f: pd.DataFrame) -> pd.Series:
    b = f["pct_above_200"].dropna()
    # build_china uses mean(window <= latest): max-rank percentile under ties.
    p = b.rolling(252 * 5, min_periods=60).rank(method="max", pct=True)
    px = f["510300.SS"].dropna()
    div = (
        (b < b.shift(21)).reindex(f.index).fillna(False)
        & (px > px.shift(21)).reindex(f.index).fillna(False)
    )
    return int_component(p.reindex(f.index) - div.astype(float) * 0.16)


def liquidity_component(f: pd.DataFrame, rec: pd.Series) -> pd.Series:
    liq = cr.liquidity_overlay(f)
    base = liq.map(
        {"expanding": 0.82, "neutral": 0.5, "contracting": 0.28}
    ).fillna(0.5)
    lab = pd.Series(index=f.index, dtype=object)
    lab.loc[rec.notna() & (rec < cc._REC_BANDS[0])] = "low"
    lab.loc[
        rec.notna() & (rec >= cc._REC_BANDS[0]) & (rec < cc._REC_BANDS[1])
    ] = "elevated"
    lab.loc[rec.notna() & (rec >= cc._REC_BANDS[1])] = "high"
    adj = lab.map({"low": 0.08, "elevated": 0.0, "high": -0.12}).fillna(0)
    return int_component((base + adj).clip(0, 1))


def stress_component(rec: pd.Series, dd: pd.Series) -> pd.Series:
    band = pd.Series(index=rec.index, dtype=object)
    band.loc[dd.notna() & (dd < 50)] = "low"
    band.loc[dd.notna() & (dd >= 50) & (dd < 75)] = "elevated"
    band.loc[dd.notna() & (dd >= 75) & (dd < 90)] = "high"
    band.loc[dd.notna() & (dd >= 90)] = "extreme"
    risk_on = (1 - rec / 100).where(rec.notna(), 0.6)
    dd_s = band.map(
        {"low": 0.85, "elevated": 0.5, "high": 0.25, "extreme": 0.1}
    ).fillna(0.6)
    out = int_component(0.5 * risk_on + 0.5 * dd_s)
    out[rec.isna() & dd.isna()] = pd.NA
    return out


def reconstruct_nontrend(
    f: pd.DataFrame,
    overrides: dict[tuple[str, str], pd.DataFrame] | None = None,
) -> tuple[pd.DataFrame, dict]:
    with store_read_overrides(overrides or {}):
        rf = cc.roro_frame(f)
        rec, reclegs = cc._recession_score_series(f)
        dd = cc._drawdown_score_series(f, rec)
        ddcomps = cc._drawdown_components(f, rec)

    out = pd.DataFrame(index=f.index)
    out["risk"] = risk_component(rf)
    out["vol"] = vol_component(rf)
    out["breadth"] = breadth_component(f)
    out["liquidity"] = liquidity_component(f, rec)
    out["stress"] = stress_component(rec, dd)

    rcols = [c for c in rf if c.startswith("roro_") and c != "roro_raw"]
    meta = {
        "roro_active": (
            rf[rcols].notna().sum(axis=1)
            if rcols else pd.Series(0, index=f.index)
        ),
        "slowdown_active": (
            pd.DataFrame(
                {k: d["score"].notna() for k, d in reclegs.items()},
                index=f.index,
            ).sum(axis=1)
            if reclegs else pd.Series(0, index=f.index)
        ),
        "drawdown_active": (
            sum(
                (z.notna().astype(int) for z, _w in ddcomps.values()),
                start=pd.Series(0, index=f.index, dtype=int),
            )
            if ddcomps else pd.Series(0, index=f.index)
        ),
        "recession_score": rec,
        "drawdown_score": dd,
    }
    q = (
        rf["roro_qvix"].notna().astype(int)
        if "roro_qvix" in rf else pd.Series(0, index=f.index)
    )
    m = (
        rf["roro_margin"].notna().astype(int)
        if "roro_margin" in rf else pd.Series(0, index=f.index)
    )
    meta["vol_active"] = q + m
    return out, meta


def trend_one_date(date: pd.Timestamp, market: str) -> float | None:
    assert _TREND_FRAME is not None
    f = _TREND_FRAME.loc[:date]
    means: list[float] = []
    for ticker, _en, _zh in _CN_INDICES:
        if ticker not in f:
            continue
        s = f[ticker].dropna().astype(float)
        if len(s) < 60:
            continue
        snap = cycles.mtf_snapshot(s, completed_only=True, market=market)
        num = den = 0.0
        for tf, w in ms._TF_W.items():
            st = snap.get(tf) or {}
            if not st:
                continue
            num += w * ms._tf_sign(st)
            den += w
        if den:
            means.append(num / den)
    if not means:
        return None
    return float(round(100 * ms._clamp((float(np.mean(means)) + 1) / 2)))


def _trend_worker(date_value):
    d = pd.Timestamp(date_value)
    return d, trend_one_date(d, "US"), trend_one_date(d, "CN")


def reconstruct_trend(
    f: pd.DataFrame, dates: pd.DatetimeIndex, workers: int = 1
) -> pd.DataFrame:
    global _TREND_FRAME
    _TREND_FRAME = f
    if workers <= 1:
        rows = [_trend_worker(d) for d in dates]
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(processes=workers) as pool:
            rows = list(pool.imap(_trend_worker, dates, chunksize=8))
    return (
        pd.DataFrame(
            rows, columns=["date", "trend_us_anchor", "trend_cn_anchor"]
        )
        .set_index("date")
        .sort_index()
    )


def blend_scores(
    components: pd.DataFrame, weights: dict[str, float]
) -> pd.Series:
    cols = [
        k for k, w in weights.items()
        if float(w) > 0 and k in components.columns
    ]
    if not cols:
        return pd.Series(index=components.index, dtype="Float64")
    w = pd.Series({k: float(weights[k]) for k in cols})
    vals = components[cols].astype(float)
    num = vals.mul(w, axis=1).sum(axis=1, skipna=True)
    den = vals.notna().mul(w, axis=1).sum(axis=1)
    return (num / den.replace(0, np.nan)).round().astype("Float64")


def model_weights(prereg: dict) -> dict[str, dict[str, float]]:
    models = {
        k: v for k, v in prereg["fixed_models"].items()
        if isinstance(v, dict)
    }
    current = prereg["fixed_models"]["current"]
    for drop in current:
        models[f"loco_{drop}"] = {
            k: w for k, w in current.items() if k != drop
        }
    return models


def build_model_scores(
    components: pd.DataFrame, prereg: dict
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            name: blend_scores(components, weights)
            for name, weights in model_weights(prereg).items()
        }
    )


def build_outcomes(sample_end: str) -> pd.DataFrame:
    px = (
        store.read("china", "000001.SS")["close"]
        .dropna()
        .loc[:pd.Timestamp(sample_end)]
    )
    idx = pd.DatetimeIndex(px.index)
    vals = px.to_numpy(float)
    rows = []
    for i, stamp in enumerate(idx):
        row = {"stamp": stamp}
        if i + 21 < len(vals):
            entry = vals[i + 1]
            w21 = vals[i + 1 : i + 22]
            row.update(
                entry_close=entry,
                maxdd21=float(np.min(w21) / entry - 1),
                dd21_5pct=bool(np.min(w21) / entry - 1 <= -0.05),
                ret21=float(vals[i + 21] / entry - 1),
            )
        else:
            row.update(
                entry_close=np.nan,
                maxdd21=np.nan,
                dd21_5pct=pd.NA,
                ret21=np.nan,
            )
        if i + 42 < len(vals):
            entry = vals[i + 1]
            w42 = vals[i + 1 : i + 43]
            row.update(
                maxdd42=float(np.min(w42) / entry - 1),
                dd42_10pct=bool(np.min(w42) / entry - 1 <= -0.10),
                ret42=float(vals[i + 42] / entry - 1),
            )
        else:
            row.update(
                maxdd42=np.nan,
                dd42_10pct=pd.NA,
                ret42=np.nan,
            )
        rows.append(row)
    return pd.DataFrame(rows).set_index("stamp")


def roc_auc_binary(y, risk_score) -> float | None:
    a = pd.DataFrame({"y": y, "s": risk_score}).dropna()
    if a.empty:
        return None
    yy = a["y"].astype(bool).to_numpy()
    n1 = int(yy.sum())
    n0 = int((~yy).sum())
    if not n1 or not n0:
        return None
    ranks = a["s"].rank(method="average").to_numpy(float)
    return float(
        (ranks[yy].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    )


def spearman(a, b) -> float | None:
    x = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(x) < 3:
        return None
    v = x["a"].corr(x["b"], method="spearman")
    return None if pd.isna(v) else float(v)


def run_count(mask: pd.Series) -> int:
    m = mask.fillna(False).astype(bool)
    return int((m & ~m.shift(1, fill_value=False)).sum())


def basic_metrics(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> dict:
    j = scores.join(outcomes, how="inner")
    out: dict = {}
    for name in scores.columns:
        s = j[name]
        out[name] = {
            "n_score": int(s.notna().sum()),
            "auc_dd21": roc_auc_binary(j["dd21_5pct"], 100 - s),
            "auc_dd42": roc_auc_binary(j["dd42_10pct"], 100 - s),
            "spearman_ret21": spearman(s, j["ret21"]),
            "spearman_ret42": spearman(s, j["ret42"]),
            "spearman_maxdd21": spearman(s, j["maxdd21"]),
            "spearman_maxdd42": spearman(s, j["maxdd42"]),
        }

    m21 = j.dropna(subset=["dd21_5pct"])
    m42 = j.dropna(subset=["dd42_10pct"])
    out["_sample"] = {
        "n_rows": len(j),
        "n_mature21": len(m21),
        "n_mature42": len(m42),
        "event_rate_dd21": (
            float(m21["dd21_5pct"].astype(float).mean()) if len(m21) else None
        ),
        "event_rate_dd42": (
            float(m42["dd42_10pct"].astype(float).mean()) if len(m42) else None
        ),
        "effective_n_dd21": (
            effective_n(m21.index.to_numpy(), 21, calendar)
            if len(m21) else None
        ),
        "effective_n_dd42": (
            effective_n(m42.index.to_numpy(), 42, calendar)
            if len(m42) else None
        ),
        "event_episodes_dd21": run_count(m21["dd21_5pct"]),
        "event_episodes_dd42": run_count(m42["dd42_10pct"]),
    }
    return out


def cut_snapshot(
    score: pd.Series,
    outcomes: pd.DataFrame,
    lower: int,
    upper: int,
) -> dict:
    j = pd.DataFrame({"score": score}).join(outcomes, how="inner")
    band = pd.Series(index=j.index, dtype=object)
    band.loc[j.score < lower] = "RISK_OFF"
    band.loc[(j.score >= lower) & (j.score < upper)] = "MIXED"
    band.loc[j.score >= upper] = "RISK_ON"
    out = {
        "lower": lower,
        "upper": upper,
        "band_counts": band.value_counts().to_dict(),
        "churn": int((band != band.shift()).iloc[1:].sum()) if len(band) > 1 else 0,
    }
    for target in ("dd21_5pct", "dd42_10pct"):
        a = pd.DataFrame({"y": j[target], "band": band}).dropna()
        base = float(a.y.astype(float).mean()) if len(a) else None
        bands = {}
        for label in ("RISK_OFF", "MIXED", "RISK_ON"):
            x = a[a.band == label].y.astype(float)
            rate = float(x.mean()) if len(x) else None
            bands[label] = {
                "n": len(x),
                "rate": rate,
                "lift_vs_base": (rate / base if rate is not None and base else None),
            }
        ro = a.band == "RISK_OFF"
        events = a.y.astype(bool)
        tp = int((ro & events).sum())
        pred = int(ro.sum())
        nev = int(events.sum())
        out[target] = {
            "base_rate": base,
            "bands": bands,
            "riskoff_precision": tp / pred if pred else None,
            "riskoff_recall": tp / nev if nev else None,
        }
    return out


def circular_block_indices(
    n: int, block: int, rng: np.random.Generator
) -> np.ndarray:
    nb = int(math.ceil(n / block))
    starts = rng.integers(0, n, size=nb)
    offsets = np.arange(block)
    return ((starts[:, None] + offsets[None, :]).ravel()[:n] % n).astype(int)


def ci95(values: list[float], draws: int) -> list[float] | None:
    if not values or (draws and len(values) < draws // 2):
        return None
    return [
        float(np.percentile(values, 2.5)),
        float(np.percentile(values, 97.5)),
    ]


def bootstrap_auc(
    y: pd.Series,
    score: pd.Series,
    *,
    block: int,
    draws: int,
    seed: int = BOOT_SEED,
) -> dict:
    a = pd.DataFrame({"y": y, "score": score}).dropna()
    point = roc_auc_binary(a["y"], 100 - a["score"]) if len(a) else None
    out = {"point": point, "ci95": None, "n": len(a), "valid_draws": 0}
    if (
        point is None
        or draws <= 0
        or len(a) < max(30, block * 3)
    ):
        return out
    yy = a["y"].astype(bool).reset_index(drop=True)
    ss = a["score"].astype(float).reset_index(drop=True)
    rng = np.random.default_rng(seed)
    vals: list[float] = []
    for _ in range(draws):
        ix = circular_block_indices(len(a), block, rng)
        v = roc_auc_binary(
            yy.iloc[ix].reset_index(drop=True),
            100 - ss.iloc[ix].reset_index(drop=True),
        )
        if v is not None:
            vals.append(v)
    out["ci95"] = ci95(vals, draws)
    out["valid_draws"] = len(vals)
    return out


def bootstrap_auc_delta(
    y: pd.Series,
    current: pd.Series,
    challenger: pd.Series,
    *,
    block: int,
    draws: int,
    seed: int = BOOT_SEED,
) -> dict:
    a = pd.DataFrame(
        {"y": y, "current": current, "challenger": challenger}
    ).dropna()
    if a.empty:
        return {"point": None, "ci95": None, "n": 0, "valid_draws": 0}
    cur = roc_auc_binary(a["y"], 100 - a["current"])
    alt = roc_auc_binary(a["y"], 100 - a["challenger"])
    point = None if cur is None or alt is None else alt - cur
    out = {"point": point, "ci95": None, "n": len(a), "valid_draws": 0}
    if (
        point is None
        or draws <= 0
        or len(a) < max(30, block * 3)
    ):
        return out
    yy = a["y"].astype(bool).reset_index(drop=True)
    cur_s = a["current"].astype(float).reset_index(drop=True)
    alt_s = a["challenger"].astype(float).reset_index(drop=True)
    rng = np.random.default_rng(seed)
    vals: list[float] = []
    for _ in range(draws):
        ix = circular_block_indices(len(a), block, rng)
        yb = yy.iloc[ix].reset_index(drop=True)
        c = roc_auc_binary(yb, 100 - cur_s.iloc[ix].reset_index(drop=True))
        x = roc_auc_binary(yb, 100 - alt_s.iloc[ix].reset_index(drop=True))
        if c is not None and x is not None:
            vals.append(x - c)
    out["ci95"] = ci95(vals, draws)
    out["valid_draws"] = len(vals)
    return out


def bootstrap_spearman(
    x: pd.Series,
    y: pd.Series,
    *,
    block: int,
    draws: int,
    seed: int = BOOT_SEED,
) -> dict:
    a = pd.DataFrame({"x": x, "y": y}).dropna()
    point = spearman(a["x"], a["y"]) if len(a) else None
    out = {"point": point, "ci95": None, "n": len(a), "valid_draws": 0}
    if (
        point is None
        or draws <= 0
        or len(a) < max(30, block * 3)
    ):
        return out
    xv = a["x"].reset_index(drop=True)
    yv = a["y"].reset_index(drop=True)
    rng = np.random.default_rng(seed)
    vals: list[float] = []
    for _ in range(draws):
        ix = circular_block_indices(len(a), block, rng)
        v = spearman(
            xv.iloc[ix].reset_index(drop=True),
            yv.iloc[ix].reset_index(drop=True),
        )
        if v is not None:
            vals.append(v)
    out["ci95"] = ci95(vals, draws)
    out["valid_draws"] = len(vals)
    return out


def bootstrap_group_difference(
    y: pd.Series,
    left: pd.Series,
    right: pd.Series,
    *,
    block: int,
    draws: int,
    seed: int = BOOT_SEED,
) -> dict:
    a = pd.DataFrame({"y": y, "left": left, "right": right}).dropna()
    lm = a["left"].astype(bool)
    rm = a["right"].astype(bool)
    if not lm.any() or not rm.any():
        return {"point": None, "ci95": None, "n": len(a), "valid_draws": 0}
    yy = a["y"].astype(float)
    point = float(yy[lm].mean() - yy[rm].mean())
    out = {"point": point, "ci95": None, "n": len(a), "valid_draws": 0}
    if draws <= 0 or len(a) < max(30, block * 3):
        return out
    yv = yy.reset_index(drop=True)
    lv = lm.reset_index(drop=True)
    rv = rm.reset_index(drop=True)
    rng = np.random.default_rng(seed)
    vals: list[float] = []
    for _ in range(draws):
        ix = circular_block_indices(len(a), block, rng)
        yb = yv.iloc[ix].reset_index(drop=True)
        lb = lv.iloc[ix].reset_index(drop=True)
        rb = rv.iloc[ix].reset_index(drop=True)
        if lb.any() and rb.any():
            vals.append(float(yb[lb].mean() - yb[rb].mean()))
    out["ci95"] = ci95(vals, draws)
    out["valid_draws"] = len(vals)
    return out


def primary_inference(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    draws: int,
) -> dict:
    j = scores.join(outcomes, how="inner")
    base = basic_metrics(scores, outcomes, calendar)
    for name in scores.columns:
        base[name]["auc_dd21_block"] = bootstrap_auc(
            j["dd21_5pct"], j[name], block=21, draws=draws
        )
        base[name]["auc_dd42_block"] = bootstrap_auc(
            j["dd42_10pct"], j[name], block=42, draws=draws
        )
        if name != "current":
            base[name]["delta_auc_dd21_vs_current"] = bootstrap_auc_delta(
                j["dd21_5pct"],
                j["current"],
                j[name],
                block=21,
                draws=draws,
            )
            base[name]["delta_auc_dd42_vs_current"] = bootstrap_auc_delta(
                j["dd42_10pct"],
                j["current"],
                j[name],
                block=42,
                draws=draws,
            )
    base["current"]["spearman_ret21_block"] = bootstrap_spearman(
        j["current"], j["ret21"], block=21, draws=draws
    )
    base["current"]["spearman_ret42_block"] = bootstrap_spearman(
        j["current"], j["ret42"], block=42, draws=draws
    )
    base["current"]["spearman_maxdd21_block"] = bootstrap_spearman(
        j["current"], j["maxdd21"], block=21, draws=draws
    )
    base["current"]["spearman_maxdd42_block"] = bootstrap_spearman(
        j["current"], j["maxdd42"], block=42, draws=draws
    )
    return base


def cut_inference(
    score: pd.Series,
    outcomes: pd.DataFrame,
    lower: int,
    upper: int,
    draws: int,
) -> dict:
    out = cut_snapshot(score, outcomes, lower, upper)
    j = pd.DataFrame({"score": score}).join(outcomes, how="inner")
    riskoff = j["score"] < lower
    mixed = (j["score"] >= lower) & (j["score"] < upper)
    riskon = j["score"] >= upper
    out["dependence"] = {}
    for target, block in (("dd21_5pct", 21), ("dd42_10pct", 42)):
        out["dependence"][target] = {
            "riskoff_minus_nonriskoff": bootstrap_group_difference(
                j[target], riskoff, ~riskoff, block=block, draws=draws
            ),
            "riskon_minus_mixed": bootstrap_group_difference(
                j[target], riskon, mixed, block=block, draws=draws
            ),
        }
    out["dependence"]["returns"] = {
        "riskon_minus_mixed_ret21": bootstrap_group_difference(
            j["ret21"], riskon, mixed, block=21, draws=draws
        ),
        "riskon_minus_mixed_ret42": bootstrap_group_difference(
            j["ret42"], riskon, mixed, block=42, draws=draws
        ),
    }
    return out


def slice_results(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    prereg: dict,
    calendar: pd.DatetimeIndex,
) -> dict:
    defs = {
        "primary": ("2012-08-14", "2026-09-24"),
        "half_1": ("2012-08-14", "2019-09-02"),
        "half_2": ("2019-09-03", "2026-09-24"),
        "post_2016": ("2016-01-01", "2026-09-24"),
        "near_current": ("2020-06-15", "2026-09-24"),
    }
    out = {}
    for key, (a, b) in defs.items():
        out[key] = basic_metrics(
            scores.loc[a:b], outcomes.loc[a:b], calendar
        )
    return out


def crisis_loco_results(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    prereg: dict,
    calendar: pd.DatetimeIndex,
) -> dict:
    start = prereg["availability_eras"]["contract_complete_primary_start"]
    primary = scores.loc[start : prereg["sample_end"]]
    oo = outcomes.loc[start : prereg["sample_end"]]
    out = {}
    eras = list(prereg["crisis_loco"]) + [
        {**x, "name": "stress_" + x["name"]}
        for x in prereg.get("additional_stress_era_sensitivity", [])
    ]
    for era in eras:
        mask = ~(
            (primary.index >= pd.Timestamp(era["start"]))
            & (primary.index <= pd.Timestamp(era["end"]))
        )
        out[era["name"]] = basic_metrics(
            primary.loc[mask], oo.loc[mask], calendar
        )
    return out


def threshold_sensitivity(
    score: pd.Series,
    outcomes: pd.DataFrame,
    prereg: dict,
    draws: int,
) -> dict:
    low = {}
    for c in prereg["threshold_grid"]["lower_cuts"]:
        low[str(c)] = cut_inference(score, outcomes, c, 60, draws)
    high = {}
    for c in prereg["threshold_grid"]["upper_cuts"]:
        high[str(c)] = cut_inference(score, outcomes, 42, c, draws)

    grid = {}
    for lo in prereg["threshold_grid"]["lower_cuts"]:
        for hi in prereg["threshold_grid"]["upper_cuts"]:
            if lo >= hi:
                continue
            snap = cut_snapshot(score, outcomes, lo, hi)
            grid[f"{lo}_{hi}"] = {
                "band_counts": snap["band_counts"],
                "churn": snap["churn"],
            }
    return {
        "baseline": cut_inference(score, outcomes, 42, 60, draws),
        "lower_cut": low,
        "upper_cut": high,
        "grid_churn": grid,
        "boundary_occupancy": {
            "within_2_of_42": int(score.between(40, 44, inclusive="both").sum()),
            "within_2_of_60": int(score.between(58, 62, inclusive="both").sum()),
            "score_38_to_41": int(score.between(38, 41, inclusive="both").sum()),
            "score_42_to_45": int(score.between(42, 45, inclusive="both").sum()),
        },
    }


def current_day_sensitivity(
    components: pd.DataFrame, prereg: dict
) -> dict:
    day = pd.Timestamp(prereg["sample_end"])
    row = components.loc[[day]]
    scores = (
        build_model_scores(row, prereg)
        .iloc[0]
        .dropna()
        .astype(float)
        .to_dict()
    )
    return {
        "date": str(day.date()),
        "components": row.iloc[0].dropna().astype(float).to_dict(),
        "frozen_weight_scenarios": scores,
        "current_distance_to_42": (
            float(scores["current"] - 42) if "current" in scores else None
        ),
        "current_distance_to_60": (
            float(scores["current"] - 60) if "current" in scores else None
        ),
    }


def to_native(v):
    if isinstance(v, dict):
        return {str(k): to_native(x) for k, x in v.items()}
    if isinstance(v, list):
        return [to_native(x) for x in v]
    if isinstance(v, tuple):
        return [to_native(x) for x in v]
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return None if np.isnan(v) else float(v)
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    return v


def run(
    *,
    workers: int = 1,
    output: Path = DEFAULT_OUT,
    draws: int = BOOT_DRAWS,
) -> dict:
    prereg = verify_prereg()
    sample_end = prereg["sample_end"]
    ref = build_features().loc[:pd.Timestamp(sample_end)].copy()
    release, overrides = build_release_lagged_view(ref, sample_end)

    sessions = shcomp_sessions(sample_end)
    start = pd.Timestamp(
        prereg["availability_eras"]["contract_complete_primary_start"]
    )
    primary_sessions = sessions[sessions >= start]

    trend = reconstruct_trend(ref, primary_sessions, workers=workers)
    ref_nt, ref_meta = reconstruct_nontrend(ref)
    rel_nt, rel_meta = reconstruct_nontrend(release, overrides)

    ref_components = ref_nt.join(
        trend[["trend_us_anchor"]].rename(
            columns={"trend_us_anchor": "trend"}
        ),
        how="left",
    ).reindex(primary_sessions)
    rel_components = rel_nt.join(
        trend[["trend_us_anchor"]].rename(
            columns={"trend_us_anchor": "trend"}
        ),
        how="left",
    ).reindex(primary_sessions)
    rel_cn_components = rel_nt.join(
        trend[["trend_cn_anchor"]].rename(
            columns={"trend_cn_anchor": "trend"}
        ),
        how="left",
    ).reindex(primary_sessions)

    ref_scores = build_model_scores(ref_components, prereg)
    rel_scores = build_model_scores(rel_components, prereg)
    rel_cn_scores = build_model_scores(rel_cn_components, prereg)

    # Must reproduce the frozen current artifact before any result is trusted.
    orient = prereg["current_model"]["today_orientation"]
    day = pd.Timestamp(orient["artifact_asof"])
    got = (
        ref_components.loc[day]
        .dropna()
        .astype(int)
        .to_dict()
    )
    expected = {
        k: int(v) for k, v in orient["components"].items()
    }
    if got != expected:
        raise RuntimeError(
            f"current component reproduction failed: expected={expected} got={got}"
        )
    got_score = int(ref_scores.loc[day, "current"])
    if got_score != int(orient["raw_score"]):
        raise RuntimeError(
            f"current score reproduction failed: "
            f"expected={orient['raw_score']} got={got_score}"
        )

    outcomes = build_outcomes(sample_end)
    primary = rel_scores.loc[start:pd.Timestamp(sample_end)]

    primary_infer = primary_inference(
        primary, outcomes, primary_sessions, draws
    )
    thresholds = threshold_sensitivity(
        primary["current"], outcomes, prereg, draws
    )
    result = {
        "schema": "cn_market_state_p3_results.v1",
        "operation": prereg["operation"],
        "prereg_payload_sha256": prereg["prereg_payload_sha256"],
        "prereg_file_sha256": _sha256_file(PREREG_PATH),
        "base_sha": prereg["base_sha"],
        "sample_end": sample_end,
        "bootstrap_draws": draws,
        "bootstrap_seed": BOOT_SEED,
        "evidence_class": "A_RECONSTRUCTED_HISTORICAL",
        "current_reproduction": {
            "components": got,
            "raw_score": got_score,
            "matches_frozen_artifact": True,
            "production_reference_today": current_day_sensitivity(
                ref_components, prereg
            ),
            "release_lagged_today": current_day_sensitivity(
                rel_components, prereg
            ),
            "cn_anchor_today": current_day_sensitivity(
                rel_cn_components, prereg
            ),
        },
        "primary_release_lagged": {
            "inference": primary_infer,
            "slices": slice_results(
                rel_scores, outcomes, prereg, primary_sessions
            ),
            "crisis_loco": crisis_loco_results(
                rel_scores, outcomes, prereg, primary_sessions
            ),
            "thresholds": thresholds,
        },
        "sensitivities": {
            "production_reference": basic_metrics(
                ref_scores.loc[primary.index], outcomes, primary_sessions
            ),
            "cn_session_anchor": basic_metrics(
                rel_cn_scores.loc[primary.index], outcomes, primary_sessions
            ),
        },
        "coverage": {
            "primary_session_count": len(primary_sessions),
            "reference_top_level_nonnull": ref_components.notna().sum().to_dict(),
            "release_top_level_nonnull": rel_components.notna().sum().to_dict(),
            "release_sublegs_latest": {
                "roro_active": int(
                    rel_meta["roro_active"]
                    .reindex(primary_sessions)
                    .dropna()
                    .iloc[-1]
                ),
                "vol_active": int(
                    rel_meta["vol_active"]
                    .reindex(primary_sessions)
                    .dropna()
                    .iloc[-1]
                ),
                "slowdown_active": int(
                    rel_meta["slowdown_active"]
                    .reindex(primary_sessions)
                    .dropna()
                    .iloc[-1]
                ),
                "drawdown_active": int(
                    rel_meta["drawdown_active"]
                    .reindex(primary_sessions)
                    .dropna()
                    .iloc[-1]
                ),
            },
        },
    }
    result = to_native(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "result_path": str(output.relative_to(ROOT)),
                "result_sha256": _sha256_file(output),
                "current_reproduction": result["current_reproduction"],
                "primary_sample": result["primary_release_lagged"][
                    "inference"
                ]["_sample"],
                "current_auc21": result["primary_release_lagged"][
                    "inference"
                ]["current"]["auc_dd21_block"],
                "current_auc42": result["primary_release_lagged"][
                    "inference"
                ]["current"]["auc_dd42_block"],
                "cut42_dd21": result["primary_release_lagged"][
                    "thresholds"
                ]["baseline"]["dependence"]["dd21_5pct"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--bootstrap-draws", type=int, default=BOOT_DRAWS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    run(
        workers=max(1, args.workers),
        output=args.output,
        draws=max(0, args.bootstrap_draws),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
