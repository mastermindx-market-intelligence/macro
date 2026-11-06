from __future__ import annotations

"""Q12 evaluation: freeze guard, eligibility census, baseline reproduction, D1 diagnostic.

Usage:
  python3.12 evaluate.py [--data-root DIR] [--utc STAMP_FROM_date_-u]

Exit codes: 0 completed (verdict in results/summary.json); 3 refused (PREREG.md sha256
differs from FREEZE.log); 4 eligible or alias-candidate store found (a
PREREG_AMENDMENT.md must fix the column mapping before any outcome is read). Every invocation appends one JSON line to
RUNS.log with the command, exit code, input sha256s and output sha256s.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
Q12_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BASE_ROOT = os.path.join(os.path.dirname(Q12_ROOT), "_base")
PREREG = os.path.join(HERE, "PREREG.md")
FREEZE = os.path.join(HERE, "FREEZE.log")
RUNS = os.path.join(HERE, "RUNS.log")
RESULTS = os.path.join(HERE, "results")
DEFAULT_DATA = "/Users/chriswong/Documents/Cluade/macro-main/data"

RIGHT = {"right", "is_call", "put_call", "option_type", "cp", "call_put"}
STRIKE = {"strike", "k", "strike_price"}
EXPIRY = {"exp", "expiry", "expiration", "expiry_date", "expiration_date"}
TS = {"ts", "timestamp", "quote_ts", "asof", "time", "quote_time", "quote_timestamp"}
BID = {"bid", "bid_price", "nbbo_bid", "close_bid", "call_bid", "put_bid", "bid_px"}
ASK = {"ask", "ask_price", "nbbo_ask", "close_ask", "call_ask", "put_ask", "ask_px"}
IDENT = {"multiplier", "deliverable", "contract_size", "settlement", "exercise",
         "exercise_style", "settlement_style", "root"}
PRICEISH = {"avg_price", "mid", "mark", "last", "close", "price", "option_price", "iv"}
TXT_QUOTE = re.compile(rb'"(bid|ask|bid_price|ask_price|nbbo_bid|nbbo_ask)"\s*:', re.I)

# Alias pass (finisher addition after the independent audit): the exact-name sets above
# can miss renamed quote columns. Names are split into tokens (snake/camel/digits) and a
# store is an ALIAS CANDIDATE when it carries a bid-level AND an ask-level token plus a
# strike token. Tokens that mark a size, share, side, flow or count statistic disqualify
# a column, because those are not quote LEVELS. Candidates force exit 4 (amendment
# before any outcome is read), exactly like exact-name eligibility.
TXT_KEY = re.compile(rb'"([A-Za-z][A-Za-z0-9_]{0,63})"\s*:')
ALIAS_BID = {"bid", "bidpx", "bidprice", "nbb"}
ALIAS_ASK = {"ask", "askpx", "askprice", "offer", "nbo"}
ALIAS_STRIKE = {"strike", "strk", "k"}
ALIAS_EXCLUDE = {"share", "size", "sz", "side", "flow", "count", "cnt", "n", "qty",
                 "volume", "vol", "median", "pct", "ratio", "imbalance", "notional",
                 "premium", "prem", "at", "spread", "bp", "bps", "basket"}


def _tokens(name: str) -> set[str]:
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return {t for t in re.split(r"[^a-z0-9]+|(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])",
                                spaced.lower()) if t}


def alias_classify(names: list[str]) -> dict:
    bid, ask, strike = [], [], []
    for n in names:
        t = _tokens(n)
        if t & ALIAS_STRIKE or "strike" in n.lower():
            strike.append(n)
        if t & ALIAS_EXCLUDE:
            continue
        if t & ALIAS_BID:
            bid.append(n)
        if t & ALIAS_ASK:
            ask.append(n)
    return {"candidate": bool(bid and ask and strike), "bid": bid, "ask": ask,
            "strike": strike}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def frozen_hash() -> str | None:
    try:
        with open(FREEZE) as fh:
            m = re.search(r"sha256=([0-9a-f]{64})", fh.read())
    except OSError:
        return None
    return m.group(1) if m else None


def append_run(cmd: list[str], code: int, inputs: dict, outputs: dict, note: str,
               utc: str | None) -> None:
    rec = {"utc": utc, "command": " ".join(cmd), "exit_code": code, "note": note,
           "inputs_sha256": inputs, "outputs_sha256": outputs}
    with open(RUNS, "a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")


def classify(names: list[str]) -> dict:
    low = {n.lower() for n in names}
    has = {
        "right": bool(low & RIGHT), "strike": bool(low & STRIKE),
        "expiry": bool(low & EXPIRY), "ts": bool(low & TS),
        "bid": bool(low & BID), "ask": bool(low & ASK), "identity": bool(low & IDENT),
    }
    eligible = all(has.values())
    near = has["strike"] and has["expiry"] and (has["bid"] or has["ask"] or bool(low & PRICEISH))
    return {"eligible": eligible, "near_miss": near and not eligible, "has": has}


def census(data_root: str) -> dict:
    import pyarrow.parquet as pq

    eligible, near, errors, alias = [], [], [], []
    n_pq = n_txt = 0
    for dirpath, dirnames, filenames in os.walk(data_root):
        dirnames.sort()
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, data_root)
            low = fn.lower()
            try:
                if low.endswith(".parquet"):
                    n_pq += 1
                    names = pq.read_schema(p).names
                    c = classify(names)
                    al = alias_classify(names)
                    if al["candidate"] and not c["eligible"]:
                        alias.append({"file": rel, **al})
                    if c["eligible"]:
                        eligible.append({"file": rel, "cols": names})
                    elif c["near_miss"]:
                        near.append({"file": rel, "has": c["has"]})
                elif low.endswith((".json", ".jsonl", ".csv")):
                    n_txt += 1
                    with open(p, "rb") as fh:
                        head = fh.read(65536)
                    if TXT_QUOTE.search(head) and b'"strike' in head.lower():
                        eligible.append({"file": rel, "kind": "text_head_bid_ask_strike"})
                    else:
                        keys = sorted({k.decode() for k in TXT_KEY.findall(head)})
                        al = alias_classify(keys)
                        if al["candidate"]:
                            alias.append({"file": rel, "kind": "text_head", **al})
            except Exception as exc:  # reported, never hidden
                errors.append({"file": rel, "error": repr(exc)[:160]})
    # collapse near misses by directory so the result stays small
    by_dir: dict[str, dict] = {}
    for n in near:
        d = os.path.dirname(n["file"]) or "."
        slot = by_dir.setdefault(d, {"n_files": 0, "example": n["file"], "has": n["has"]})
        slot["n_files"] += 1
    return {"data_root": data_root, "parquet_schemas": n_pq, "text_heads": n_txt,
            "eligible": eligible, "alias_candidates": alias,
            "near_miss_by_dir": by_dir, "errors": errors}


def load_incumbent():
    path = os.path.join(BASE_ROOT, "engine", "intraday_greeks.py")
    spec = importlib.util.spec_from_file_location("q12_incumbent_intraday_greeks", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses resolve the defining module here
    spec.loader.exec_module(mod)
    return mod, path


def baseline_repro() -> tuple[dict, str]:
    import math

    sys.path.insert(0, Q12_ROOT)
    from engine import options_parity_forward_interval as q

    inc, inc_path = load_incumbent()
    D, T = 0.98, 0.5
    r = -math.log(D) / T  # so the incumbent's e^{-rT} equals D

    def leg(right, bid, ask, k=100.0, idx=10, ex="european"):
        return q.OptionQuote(right, "IDX", "E1", k, "100 IDX", 100.0,
                             "cash_pm" if ex == "european" else "physical", ex,
                             bid, ask, idx)

    def incumbent_forward(legs):
        cs = [{"exp_years": T, "strike": l.strike, "right": l.right,
               "mid": (l.bid + l.ask) / 2} for l in legs]
        s = inc.parity_spot(cs, r=r, q=0.0)
        return None if s is None else s / D

    def q12(legs):
        est, diag = q.estimate_forward(legs, d_band=(D, D), now_index=10,
                                       max_quote_age=2, max_async=1)
        return {"status": est.status, "lo": est.lo, "hi": est.hi,
                "reasons": list(est.reasons),
                "rejected": [list(r_) for _, r_ in diag["rejected"]]}

    cases = {
        "witness_european_F101": [leg("C", 5.00, 5.16), leg("P", 4.02, 4.18)],
        "crossed_call": [leg("C", 5.20, 5.10), leg("P", 4.02, 4.18)],
        "stale_put": [leg("C", 5.00, 5.16), leg("P", 4.02, 4.18, idx=3)],
        "incompatible_strikes": [leg("C", 5.00, 5.16), leg("P", 4.02, 4.18),
                                 leg("C", 2.880, 3.040, k=105.0),
                                 leg("P", 5.940, 6.100, k=105.0)],
        "american_pair": [leg("C", 5.00, 5.16, ex="american"),
                          leg("P", 4.02, 4.18, ex="american")],
    }
    out = {}
    for name, legs in cases.items():
        out[name] = {"incumbent_B1_forward_point": incumbent_forward(legs),
                     "q12": q12(legs)}
    # B2: price-space parity absence, reproduced from the incumbent's own record
    dis_path = os.path.join(BASE_ROOT, "engine", "options_dislocation.py")
    with open(dis_path) as fh:
        txt = fh.read()
    out["B2_price_space_parity"] = {
        "structurally_absent_recorded": '"structurally_absent"' in txt
        and "NO option price column" in txt,
        "source": "_base/engine/options_dislocation.py synthetic_stock_price_deviation",
    }
    return out, inc_path


def d1_async(data_root: str) -> tuple[dict, str]:
    import numpy as np
    import pandas as pd

    path = os.path.join(data_root, "flow_signals", "ledger.parquet")
    df = pd.read_parquet(path, columns=["session_date", "ts", "root", "right", "exp",
                                        "strike"])
    df["t"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["t"])
    df["r"] = df["right"].astype(str).str.upper().str[:1]
    gaps = []
    n_keys_both = 0
    for _, g in df.groupby(["session_date", "root", "exp", "strike"], sort=False):
        c = np.sort(g.loc[g["r"] == "C", "t"].astype("int64").to_numpy())
        p = np.sort(g.loc[g["r"] == "P", "t"].astype("int64").to_numpy())
        if len(c) == 0 or len(p) == 0:
            continue
        n_keys_both += 1
        idx = np.clip(np.searchsorted(p, c), 1, len(p)) - 1
        nxt = np.clip(idx + 1, 0, len(p) - 1)
        g1 = np.minimum(np.abs(c - p[idx]), np.abs(c - p[nxt]))
        gaps.append(float(g1.min()) / 1e9)
    arr = np.array(gaps) if gaps else np.array([np.nan])
    qs = {f"p{int(x * 100)}": float(np.nanquantile(arr, x)) for x in (0.1, 0.25, 0.5, 0.75, 0.9)}
    return ({"file": "data/flow_signals/ledger.parquet", "n_events": int(len(df)),
             "n_keys_with_call_and_put": n_keys_both,
             "nearest_call_put_gap_seconds_quantiles": qs,
             "share_keys_gap_le_1s": float(np.nanmean(arr <= 1.0)) if gaps else None,
             "bid_ask_levels_present": False,
             "note": "descriptive only (PREREG D1); one-sided trade-print events, never a "
                     "verdict input"}, path)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=DEFAULT_DATA)
    ap.add_argument("--utc", default=None)
    a = ap.parse_args(argv[1:])
    cmd = [os.path.basename(sys.executable)] + argv

    pre = sha256(PREREG)
    fz = frozen_hash()
    if fz is None or fz != pre:
        append_run(cmd, 3, {"PREREG.md": pre}, {}, f"REFUSED: PREREG sha256 {pre} != "
                   f"FREEZE {fz}", a.utc)
        print("REFUSED: PREREG.md sha256 differs from FREEZE.log", file=sys.stderr)
        return 3

    os.makedirs(RESULTS, exist_ok=True)
    inputs = {"PREREG.md": pre, "FREEZE.log": sha256(FREEZE),
              "evaluate.py": sha256(os.path.abspath(__file__)),
              "engine/options_parity_forward_interval.py":
                  sha256(os.path.join(Q12_ROOT, "engine", "options_parity_forward_interval.py"))}

    cen = census(a.data_root)
    base, inc_path = baseline_repro()
    inputs["_base/engine/intraday_greeks.py"] = sha256(inc_path)
    inputs["_base/engine/options_dislocation.py"] = sha256(
        os.path.join(BASE_ROOT, "engine", "options_dislocation.py"))
    d1, d1_path = d1_async(a.data_root)
    inputs["data/flow_signals/ledger.parquet"] = sha256(d1_path)
    chains = sorted(os.listdir(os.path.join(a.data_root, "polygon_gex", "chains")))
    lines = "".join(sha256(os.path.join(a.data_root, "polygon_gex", "chains", f)) + " " + f
                    + "\n" for f in chains if f.endswith(".parquet"))
    inputs["data/polygon_gex/chains/*.parquet(aggregate)"] = hashlib.sha256(
        lines.encode()).hexdigest()

    n_elig = len(cen["eligible"])
    n_alias = len(cen["alias_candidates"])
    if n_elig or n_alias:
        verdict, code = "AMENDMENT_REQUIRED", 4
    else:
        verdict, code = "INSUFFICIENT_DATA", 0
    summary = {
        "verdict": verdict,
        "eligible_stores": n_elig,
        "alias_candidate_stores": n_alias,
        "missing_input": None if (n_elig or n_alias) else (
            "synchronized same-timestamp call/put two-sided bid/ask quotes with strike, "
            "expiry, deliverable/multiplier and settlement/exercise identity (preferably "
            "European cash-settled index options), plus a dated discount curve"),
        "comparison_H2_run": False,
        "parquet_schemas_scanned": cen["parquet_schemas"],
        "text_heads_scanned": cen["text_heads"],
        "census_errors": len(cen["errors"]),
    }
    outs = {}
    for name, obj in (("census.json", cen), ("baseline_repro.json", base),
                      ("d1_async.json", d1), ("summary.json", summary)):
        p = os.path.join(RESULTS, name)
        with open(p, "w") as fh:
            json.dump(obj, fh, indent=1, sort_keys=True, default=str)
            fh.write("\n")
        outs["results/" + name] = sha256(p)
    append_run(cmd, code, inputs, outs, f"verdict={verdict}", a.utc)
    print(json.dumps(summary, indent=1))
    return code


if __name__ == "__main__":
    try:
        rc = main(sys.argv)
    except Exception as exc:  # a crash is still a run: log it, then fail loudly
        utc = sys.argv[sys.argv.index("--utc") + 1] if "--utc" in sys.argv[:-1] else None
        append_run([os.path.basename(sys.executable)] + sys.argv, 1,
                   {"PREREG.md": sha256(PREREG)}, {}, f"CRASH: {exc!r}"[:300], utc)
        raise
    sys.exit(rc)
