from __future__ import annotations

# Q01 evaluation driver (research only; never imported by product code).
#
# Implements the frozen PREREG.md section 10 procedure plus amendment A1:
#   S0  refuse to run (exit 2, logged) when PREREG.md / PREREG_AMENDMENT.md hashes differ from FREEZE.log
#   S1  reproduce the incumbent exact-leg baseline (engine/options_skew.skew_map) on 28 chain files
#   S2  eligibility census of the PREREG section 5 candidates + the A1 exhaustive schema sweep
#   S3  pre-registered data gate (>= 100 eligible sessions, >= 40 holdout sessions)
#   S4  the section 8-9 comparison (only when S3 passes)
#   S5  NON_EVIDENTIAL synthetic mechanics: the S4 code path on seeded synthetic SVI sessions
#
# Every run appends one JSON line to RUNS.log (command, exit code, PREREG/amendment sha256, input and
# output sha256s). No wall-clock value is read. Outputs are written only into this directory.
# Exit codes: 0 completed (any verdict), 1 crash, 2 freeze-hash mismatch, 3 census candidate that
# meets the eligibility contract but has no pre-registered adapter (manual review; no verdict),
# 4 a declared input differs from its recorded sha256 (refuses before S1; no verdict).

import hashlib
import json
import math
import os
import re
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
STAGING = os.path.abspath(os.path.join(REPO, ".."))
DATA = "/Users/chriswong/Documents/Cluade/macro-main/data"
DATA_VINTAGE = "cdab6268"
PREREG = os.path.join(HERE, "PREREG.md")
AMENDMENT = os.path.join(HERE, "PREREG_AMENDMENT.md")
FREEZE = os.path.join(HERE, "FREEZE.log")
RUNS = os.path.join(HERE, "RUNS.log")
MODULE_PATH = os.path.join(REPO, "engine", "options_arbfree_surface.py")
TEST_PATH = os.path.join(REPO, "tests", "test_options_arbfree_surface.py")
INCUMBENT_PATH = os.path.join(REPO, "engine", "options_skew.py")
INCUMBENT_SHA256 = "8f68ad06c29ff9e05d6f4a710912b12a8523344d3b84a22524867e4711b38dce"

OUT_BASELINE = "baseline_reproduction.json"
OUT_CENSUS = "eligibility_census.json"
OUT_VERDICT = "verdict.json"
OUT_SYNTH = "synthetic_mechanics.json"

EUROPEAN_INDEX_ROOTS = ("SPX", "SPXW", "XSP", "NDX", "NDXP", "RUT", "RUTW", "DJX", "MRUT")
BASELINE_FIELDS = ("otm_put_iv", "atm_call_iv", "skew", "spot", "tenor_days")
BASELINE_TOL = 1e-9
ROOT_COLUMNS = ("underlying", "root", "symbol", "ticker", "instrument", "currency", "underlying_symbol")

# Section 4 gate and section 8-9 design constants (frozen values).
GATE_MIN_SESSIONS = 100
GATE_MIN_HOLDOUT = 40
MIN_EXPIRIES = 2
MIN_STRIKES = 6
TRAIN_FRACTION = 0.6
LAM_GRID = (0.01, 0.1, 1.0)
MBB_BLOCK = 5
MBB_B = 2000
MBB_SEED = 101
BAR_SVI_FAIL_RATE = 0.05
BAR_BENCH_DENSE_PASS = 0.99
BAR_CI_UPPER = 0.10
BAR_STATE_CHANGE = 0.10
PERTURB_DRAWS = 8

# Field-presence patterns. Parquet: applied to each lower-cased column name. Text (A1 sniff): applied to
# the lower-cased first 64 KiB. Deliberately broad: a broader pattern can only add candidates, so it
# can only make an absence finding harder to reach.
NAME_PATTERNS = {
    "bid": r"(^|[^a-z])bid([^a-z]|$)",
    "ask": r"(^|[^a-z])(ask|offer)([^a-z]|$)",
    "strike": r"strike|^k$",
    "expiry": r"expir|maturity|^t$|(^|[^a-z])dte([^a-z]|$)",
    "quote_ts": r"quote.*(ts|time)|sip_timestamp|ms_of_day|quote_ts",
    "condition": r"condition",
    "forward": r"forward|(^|[^a-z])fwd([^a-z]|$)",
    "discount": r"discount|^df$|(^|[^a-z])rate([^a-z]|$)",
    "style": r"style|exercise",
    "settlement": r"settle|am_pm",
}
TEXT_PATTERNS = {
    "bid": r"(?<![a-z])bid(?![a-z])",
    "ask": r"(?<![a-z])(ask|offer)(?![a-z])",
    "strike": r"strike",
    "expiry": r"expir|maturity|(?<![a-z])dte(?![a-z])",
}
A1_TEXT_EXT = (".csv", ".json", ".jsonl")
A1_TEXT_MAX_BYTES = 20 * 1024 * 1024
A1_SNIFF_BYTES = 64 * 1024

MISSING_INPUT = (
    "a same-session European cash-settled index-option quote chain (roots SPX/SPXW/XSP/NDX/RUT) with "
    "per-contract bid, ask, quote timestamp and quote condition, exact expiry timestamp and AM/PM "
    "settlement convention, plus an owner-supplied per-expiry forward and discount (Q12 / trusted "
    "forward owner), under retained rights, for >= 100 chronologically ordered sessions"
)


# ------------------------------------------------------------------------------------ helpers


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_freeze() -> dict[str, str]:
    out: dict[str, str] = {}
    with open(FREEZE, encoding="utf-8") as fh:
        for line in fh:
            if "=" in line:
                k, _, v = line.rstrip("\n").partition("=")
                out[k.strip()] = v.strip()
    return out


def run_index() -> int:
    if not os.path.exists(RUNS):
        return 1
    with open(RUNS, encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip()) + 1


def append_run(record: dict) -> None:
    with open(RUNS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def write_json(name: str, payload: dict) -> str:
    path = os.path.join(HERE, name)
    text = json.dumps(payload, sort_keys=True, indent=1, default=repr, allow_nan=True) + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return sha256_file(path)


def expected_hashes() -> dict[str, str]:
    """Input hashes declared in the frozen PREREG section 5 (the file is hash-checked in S0)."""
    with open(PREREG, encoding="utf-8") as fh:
        text = fh.read()
    sec = text.split("## 5.", 1)[1].split("## 6.", 1)[0]
    out = {m.group(1): m.group(2) for m in re.finditer(r"`([^`]+)`\s+([0-9a-f]{64})", sec)}
    out["engine/options_skew.py"] = INCUMBENT_SHA256
    return out


def resolve(rel: str) -> str:
    if rel.startswith("_base/") or rel == "DATA_MAP.md":
        return os.path.join(STAGING, rel)
    if rel.startswith("engine/"):
        return os.path.join(REPO, rel)
    return os.path.join(DATA, rel)


def field_flags(names: list[str]) -> dict[str, bool]:
    low = [str(n).lower() for n in names]
    return {f: any(re.search(p, n) for n in low) for f, p in NAME_PATTERNS.items()}


def text_flags(blob: str) -> dict[str, bool]:
    low = blob.lower()
    return {f: re.search(p, low) is not None for f, p in TEXT_PATTERNS.items()}


def same_value(a, b) -> bool:
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    if math.isnan(fa) and math.isnan(fb):
        return True
    return abs(fa - fb) < BASELINE_TOL


# ------------------------------------------------------------------------------------ S1


def stage_s1(chain_rels: list[str], snap_rel: str) -> dict:
    import pandas as pd

    if os.path.exists(os.path.join(REPO, ".env")):
        return {"state": "SKIPPED", "reason": "a .env exists in the staging clone; importing lib.config "
                "would read it, so the incumbent import is refused"}
    if REPO not in sys.path:
        sys.path.insert(0, REPO)
    q01_preloaded = "engine.options_arbfree_surface" in sys.modules
    from engine import options_skew as osk

    snap = pd.read_parquet(resolve(snap_rel))
    pg = snap[snap["source"].astype(str) == "polygon_gex"].copy()
    pg["_asof10"] = pg["asof"].astype(str).str[:10]
    per_date = []
    totals = {"rows": 0, "match": 0, "mismatch": 0, "missing_in_recompute": 0, "extra_in_recompute": 0}
    mismatch_examples = []
    last_chain = None
    for rel in chain_rels:
        date = os.path.basename(rel)[:10]
        chain = pd.read_parquet(resolve(rel))
        last_chain = chain
        recomputed = osk.skew_map(chain)
        sub = pg[pg["_asof10"] == date]
        n_match = n_mis = n_missing = 0
        seen = set()
        for _, row in sub.iterrows():
            u = row["underlying"]
            seen.add(u)
            got = recomputed.get(u)
            if got is None:
                n_missing += 1
                continue
            ok = all(same_value(got.get(c), row[c]) for c in BASELINE_FIELDS)
            ok = ok and got.get("n_strikes") is not None and int(got.get("n_strikes")) == int(row["n_strikes"])
            if ok:
                n_match += 1
            else:
                n_mis += 1
                if len(mismatch_examples) < 10:
                    mismatch_examples.append({"date": date, "underlying": str(u), "fields": {
                        c: [repr(got.get(c)), repr(row[c])] for c in BASELINE_FIELDS + ("n_strikes",)}})
        extra = len(set(recomputed) - seen)
        per_date.append({"date": date, "snapshot_rows": int(len(sub)), "match": n_match,
                         "mismatch": n_mis, "missing_in_recompute": n_missing,
                         "extra_in_recompute": int(extra), "recomputed_underlyings": len(recomputed)})
        totals["rows"] += int(len(sub))
        totals["match"] += n_match
        totals["mismatch"] += n_mis
        totals["missing_in_recompute"] += n_missing
        totals["extra_in_recompute"] += int(extra)

    # Requirement 6 discriminator: exact-leg bytes before and after importing the Q01 module.
    def digest() -> str:
        return sha256_text(json.dumps(osk.skew_map(last_chain), sort_keys=True, default=repr))

    vars_before = sorted(vars(osk))
    ids_before = {k: id(v) for k, v in vars(osk).items() if callable(v)}
    before = digest()
    mods_before = set(sys.modules)
    import engine.options_arbfree_surface as q01  # noqa: F401  (import is the discriminator)

    new_engine_mods = sorted(m for m in set(sys.modules) - mods_before if m.startswith(("engine", "lib")))
    after = digest()
    compat = {
        "q01_module_preloaded_before_check": q01_preloaded,
        "skew_map_digest_before_import": before,
        "skew_map_digest_after_import": after,
        "byte_identical": before == after,
        "options_skew_vars_unchanged": vars_before == sorted(vars(osk)),
        "options_skew_callables_unchanged": ids_before == {k: id(v) for k, v in vars(osk).items()
                                                           if callable(v)},
        "options_skew_sha256_after": sha256_file(INCUMBENT_PATH),
        "options_skew_sha256_expected": INCUMBENT_SHA256,
        "new_engine_or_lib_modules_on_import": new_engine_mods,
        "q01_research_only": bool(getattr(q01, "RESEARCH_ONLY", False)),
        "q01_authority": q01.authority(),
        "digest_chain_date": os.path.basename(chain_rels[-1])[:10],
    }
    state = "REPRODUCED" if (totals["mismatch"] == 0 and totals["missing_in_recompute"] == 0
                             and totals["rows"] > 0) else "NOT_FULLY_REPRODUCED"
    return {"state": state, "tolerance_abs": BASELINE_TOL, "fields": list(BASELINE_FIELDS) + ["n_strikes"],
            "totals": totals, "per_date": per_date, "mismatch_examples": mismatch_examples,
            "exact_leg_compatibility": compat}


# ------------------------------------------------------------------------------------ S2


def census_parquet(path: str) -> dict:
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(path)
    names = list(pf.schema_arrow.names)
    entry = {"kind": "parquet", "rows": int(pf.metadata.num_rows), "columns": names,
             "fields": field_flags(names)}
    roots = {}
    for col in ROOT_COLUMNS:
        if col in names:
            vals = pq.read_table(path, columns=[col]).column(0).to_pylist()
            uniq = sorted({str(v) for v in vals if v is not None})
            roots[col] = {"n_unique": len(uniq),
                          "index_roots_present": sorted(set(uniq) & set(EUROPEAN_INDEX_ROOTS))}
    entry["root_columns"] = roots
    if "style" in [n.lower() for n in names]:
        col = names[[n.lower() for n in names].index("style")]
        vals = pq.read_table(path, columns=[col]).column(0).to_pylist()
        entry["style_values"] = sorted({str(v) for v in vals})[:20]
    return entry


def census_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    shape = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            shape[str(k)] = (type(v).__name__, len(v) if isinstance(v, (list, dict, str)) else v
                             if isinstance(v, (int, float, bool)) or v is None else None)
    return {"kind": "json", "top_level_type": type(obj).__name__, "shape": shape,
            "fields": text_flags(json.dumps(obj))}


def contract_complete(entry: dict) -> bool | None:
    """True: every section 4 field family and a European index root are present.
    None: every field family is present but the root set cannot be determined from a recognised
    root column (fails toward manual review, never toward an absence finding). False otherwise."""
    f = entry.get("fields", {})
    need = ("bid", "ask", "strike", "expiry", "quote_ts", "condition", "forward", "discount")
    style_or_settle = f.get("style") or f.get("settlement")
    if not (all(f.get(n) for n in need) and style_or_settle):
        return False
    roots = entry.get("root_columns", {})
    if not roots:
        return None
    return True if any(r["index_roots_present"] for r in roots.values()) else False


def sniff_entry(blob: str, is_csv: bool) -> dict:
    """Field flags and index-root tokens from the first 64 KiB of a text file."""
    if is_csv:
        first = blob.splitlines()[0] if blob else ""
        names = [c.strip().strip('"') for c in first.split(",")]
    else:
        names = sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", blob)))
    tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", blob))
    present = sorted(tokens & set(EUROPEAN_INDEX_ROOTS))
    return {"kind": "text", "fields": field_flags(names),
            "root_columns": {"_sniff_tokens": {"n_unique": len(tokens), "index_roots_present": present}}}


def a1_sweep() -> dict:
    import pyarrow.parquet as pq

    listing = []
    candidates = []
    counts = {"files": 0, "symlinks_skipped": 0, "parquet": 0, "parquet_unreadable": 0,
              "text_sniffed": 0, "text_over_limit": 0, "text_unreadable": 0, "other": 0}
    partial = {"bid_and_ask": {}, "strike_and_expiry": {}}
    for dirpath, dirnames, filenames in os.walk(DATA, followlinks=False):
        dirnames.sort()
        for fn in sorted(filenames):
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, DATA)
            if os.path.islink(path):
                counts["symlinks_skipped"] += 1
                continue
            counts["files"] += 1
            try:
                size = os.path.getsize(path)
            except OSError:
                size = -1
            low = fn.lower()
            flags = None
            if low.endswith(".parquet"):
                counts["parquet"] += 1
                try:
                    flags = field_flags(list(pq.read_schema(path).names))
                except Exception:  # noqa: BLE001 - unreadable footer is counted, not fatal
                    counts["parquet_unreadable"] += 1
            elif low.endswith(A1_TEXT_EXT):
                if size > A1_TEXT_MAX_BYTES:
                    counts["text_over_limit"] += 1
                else:
                    try:
                        with open(path, "rb") as fh:
                            blob = fh.read(A1_SNIFF_BYTES).decode("utf-8", errors="replace")
                        flags = text_flags(blob)
                        counts["text_sniffed"] += 1
                    except OSError:
                        counts["text_unreadable"] += 1
            else:
                counts["other"] += 1
            top = rel.split(os.sep, 1)[0]
            if flags is not None:
                if flags.get("bid") and flags.get("ask"):
                    partial["bid_and_ask"][top] = partial["bid_and_ask"].get(top, 0) + 1
                if flags.get("strike") and flags.get("expiry"):
                    partial["strike_and_expiry"][top] = partial["strike_and_expiry"].get(top, 0) + 1
                if flags.get("bid") and flags.get("ask") and flags.get("strike") and flags.get("expiry"):
                    candidates.append((rel, size))
                    continue
            listing.append(f"{rel}\t{size}")
    cand_out = []
    for rel, size in candidates:
        path = os.path.join(DATA, rel)
        entry = {"relpath": rel, "bytes": size, "sha256": sha256_file(path)}
        if rel.lower().endswith(".parquet"):
            entry.update(census_parquet(path))
        else:
            with open(path, "rb") as fh:
                blob = fh.read(A1_SNIFF_BYTES).decode("utf-8", errors="replace")
            entry.update(sniff_entry(blob, rel.lower().endswith(".csv")))
        entry["contract_complete"] = contract_complete(entry)
        cand_out.append(entry)
    listing.sort()
    return {"data_root": DATA, "vintage": DATA_VINTAGE, "counts": counts,
            "candidate_rule": "bid-like AND ask/offer-like AND strike-like AND expiry-like field",
            "patterns_parquet": NAME_PATTERNS, "patterns_text": TEXT_PATTERNS,
            "n_candidates": len(cand_out), "candidates": cand_out,
            "partial_match_counts_by_top_level_dir": partial,
            "non_candidate_count": len(listing),
            "non_candidate_listing_sha256": sha256_text("\n".join(listing))}


def stage_s2(cand_rels: list[str], chain_rels: list[str], snap_rel: str) -> dict:
    sources = {}
    for rel in cand_rels + [snap_rel] + chain_rels:
        path = resolve(rel)
        if rel == "DATA_MAP.md" or rel.startswith("_base/"):
            continue
        if not os.path.exists(path):
            sources[rel] = {"state": "ABSENT"}
            continue
        entry = census_parquet(path) if rel.endswith(".parquet") else census_json(path)
        entry["contract_complete"] = contract_complete(entry)
        entry["missing_fields"] = sorted(k for k, v in entry["fields"].items() if not v)
        if entry["kind"] == "parquet":
            entry["index_roots_present"] = sorted({r for rc in entry["root_columns"].values()
                                                   for r in rc["index_roots_present"]})
        sources[rel] = entry
    # Compact the 28 chain files into one summary row each (columns are identical across dates).
    chain_summary = {rel: {"rows": sources[rel].get("rows"),
                           "missing_fields": sources[rel].get("missing_fields"),
                           "index_roots_present": sources[rel].get("index_roots_present"),
                           "contract_complete": sources[rel].get("contract_complete")}
                     for rel in chain_rels if rel in sources}
    chain_columns = sorted({tuple(sources[rel]["columns"]) for rel in chain_rels if rel in sources})
    for rel in chain_rels:
        sources.pop(rel, None)
    sweep = a1_sweep()
    # True (complete) and None (root set undeterminable) both stop at S3 for manual review.
    complete_sources = sorted([r for r, e in sources.items() if e.get("contract_complete") is not False]
                              + [r for r, e in chain_summary.items() if e.get("contract_complete") is not False]
                              + [c["relpath"] for c in sweep["candidates"]
                                 if c["contract_complete"] is not False])
    return {"sources": sources, "polygon_gex_chains": {"distinct_column_sets": [list(c) for c in chain_columns],
                                                       "per_file": chain_summary},
            "a1_sweep": sweep, "contract_complete_sources": sorted(set(complete_sources)),
            # 0 by construction: a session is eligible only from a contract-complete source, and any
            # such source (or an undeterminable one) stops at S3 with exit 3 before this count is used,
            # because counting its sessions needs a pre-registered adapter that does not exist.
            "eligible_sessions": 0 if not complete_sources else None,
            "european_index_roots": list(EUROPEAN_INDEX_ROOTS)}


# ------------------------------------------------------------------------------------ S4


_NODE_KEYS = ("strike", "kappa", "lo", "hi", "mid", "spread", "legs")


def holdout_indices(n: int) -> list[int]:
    return [i for i in range(1, n - 1) if i % 3 == 1]


def split_slice(s: dict) -> tuple[dict, dict]:
    n = len(s["kappa"])
    hold = set(holdout_indices(n))
    keep = [i for i in range(n) if i not in hold]
    train = dict(s)
    for key in _NODE_KEYS:
        train[key] = [s[key][i] for i in keep]
    held = {key: [s[key][i] for i in sorted(hold)] for key in ("kappa", "lo", "hi", "spread")}
    return train, held


def eligible_slices(slices: list[dict]) -> list[dict]:
    """Section 4: the expiries with >= 6 screened strikes; the session is eligible with >= 2 of them."""
    return [s for s in slices if len(s["kappa"]) >= MIN_STRIKES]


def oob_distance(v, lo: float, hi: float, spread: float) -> float:
    return max(0.0, lo - v, v - hi) / max(spread, 1e-6)


def session_losses(m, train_slices: list[dict], held: list[dict], lam: float) -> dict:
    bench = m.fit_benchmark(train_slices)
    svi = m.fit_svi_surface(train_slices, lam=lam, seed=0, n_starts=6, maxiter=400)
    out = {"bench_state": bench["state"], "svi_state": svi["state"],
           "svi_slice_states": [s["state"] for s in svi["slices"]],
           "flags": {}, "n_heldout": 0}
    lb, ls = [], []
    for j, h in enumerate(held):
        if not h["kappa"]:
            continue
        ev_b = m.evaluate_at(bench, j, h["kappa"])
        ev_s = m.evaluate_at(svi, j, h["kappa"])
        for i in range(len(h["kappa"])):
            lo, hi, sp = h["lo"][i], h["hi"][i], h["spread"][i]
            fb, fs = ev_b["flag"][i], ev_s["flag"][i]
            out["flags"][f"bench:{fb}"] = out["flags"].get(f"bench:{fb}", 0) + 1
            out["flags"][f"svi:{fs}"] = out["flags"].get(f"svi:{fs}", 0) + 1
            vb, vs = ev_b["value"][i], ev_s["value"][i]
            lb.append(1.0 if vb is None else oob_distance(vb, lo, hi, sp))
            ls.append(1.0 if vs is None else oob_distance(vs, lo, hi, sp))
            out["n_heldout"] += 1
    out["L_bench"] = float(sum(lb) / len(lb)) if lb else None
    out["L_svi"] = float(sum(ls) / len(ls)) if ls else None
    return out


def moving_block_ci(values: list[float]) -> dict:
    import numpy as np

    d = np.asarray(values, float)
    n = d.size
    if n == 0:
        return {"n": 0, "mean": None, "ci95": [None, None], "block": None, "B": MBB_B, "seed": MBB_SEED}
    block = min(MBB_BLOCK, n)
    nb = int(math.ceil(n / block))
    rng = np.random.default_rng(MBB_SEED)
    starts = rng.integers(0, n - block + 1, size=(MBB_B, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(MBB_B, -1)[:, :n]
    means = d[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"n": int(n), "mean": float(d.mean()), "ci95": [float(lo), float(hi)], "block": int(block),
            "n_blocks": nb, "B": MBB_B, "seed": MBB_SEED}


def run_comparison(m, sessions: list[tuple[str, list[dict]]]) -> dict:
    """Section 8-9 design on chronologically ordered (session_id, slices) pairs."""
    import numpy as np

    attrition: dict[str, int] = {}
    usable = []
    for sid, slices in sessions:
        good = eligible_slices(slices)
        if len(good) < MIN_EXPIRIES:
            attrition["below_strike_or_expiry_minimum"] = attrition.get("below_strike_or_expiry_minimum", 0) + 1
            continue
        pairs = [split_slice(s) for s in good]
        usable.append((sid, [p[0] for p in pairs], [p[1] for p in pairs]))
    n = len(usable)
    n_train = int(math.floor(TRAIN_FRACTION * n))
    train, hold = usable[:n_train], usable[n_train:]

    # Training-only tuning of lam: minimum median training L_svi over benchmark-admissible sessions.
    lam_scores = {}
    for lam in LAM_GRID:
        vals = []
        for _, tr, held in train:
            res = session_losses(m, tr, held, lam)
            if res["bench_state"] == m.ADMISSIBLE and res["L_svi"] is not None:
                vals.append(res["L_svi"])
        lam_scores[str(lam)] = float(np.median(vals)) if vals else None
    finite = [(lam_scores[str(lam)], i, lam) for i, lam in enumerate(LAM_GRID) if lam_scores[str(lam)] is not None]
    lam_star = min(finite)[2] if finite else LAM_GRID[1]

    rows = []
    bench_states: dict[str, int] = {}
    svi_slices = svi_failed = 0
    flags: dict[str, int] = {}
    state_change = []
    for ordinal, (sid, tr, held) in enumerate(hold):
        res = session_losses(m, tr, held, lam_star)
        bench_states[res["bench_state"]] = bench_states.get(res["bench_state"], 0) + 1
        svi_slices += len(res["svi_slice_states"])
        svi_failed += sum(1 for st in res["svi_slice_states"] if st in (m.FAILED_FIT, m.FAILED_CHECK))
        for k, v in res["flags"].items():
            flags[k] = flags.get(k, 0) + v
        pert = m.perturbation_sensitivity(tr, method="svi", n_draws=PERTURB_DRAWS, seed=ordinal,
                                          svi_options={"lam": lam_star})
        state_change.append(float(pert["state_change_fraction"]))
        paired = res["bench_state"] == m.ADMISSIBLE and res["L_bench"] is not None
        if not paired:
            key = f"holdout_benchmark_{res['bench_state']}"
            attrition[key] = attrition.get(key, 0) + 1
        rows.append({"session": sid, "bench_state": res["bench_state"], "svi_state": res["svi_state"],
                     "L_bench": res["L_bench"], "L_svi": res["L_svi"],
                     "D": (res["L_svi"] - res["L_bench"]) if paired else None,
                     "n_heldout_nodes": res["n_heldout"],
                     "perturbation_state_change_fraction": state_change[-1]})
    d_vals = [r["D"] for r in rows if r["D"] is not None]
    ci = moving_block_ci(d_vals)
    n_adm = bench_states.get(m.ADMISSIBLE, 0)
    n_chk = bench_states.get(m.FAILED_CHECK, 0)
    dense_rate = (n_adm / (n_adm + n_chk)) if (n_adm + n_chk) else None
    fail_rate = (svi_failed / svi_slices) if svi_slices else None
    med_change = float(np.median(state_change)) if state_change else None
    bars = {
        "svi_failed_slice_rate": {"value": fail_rate, "bar": f"<= {BAR_SVI_FAIL_RATE}",
                                  "pass": fail_rate is not None and fail_rate <= BAR_SVI_FAIL_RATE},
        "benchmark_dense_pass_rate": {"value": dense_rate, "bar": f">= {BAR_BENCH_DENSE_PASS}",
                                      "pass": dense_rate is not None and dense_rate >= BAR_BENCH_DENSE_PASS},
        "mean_D_ci95_upper": {"value": ci["ci95"][1], "bar": f"<= {BAR_CI_UPPER}",
                              "pass": ci["ci95"][1] is not None and ci["ci95"][1] <= BAR_CI_UPPER},
        "median_perturbation_state_change": {"value": med_change, "bar": f"<= {BAR_STATE_CHANGE}",
                                             "pass": med_change is not None and med_change <= BAR_STATE_CHANGE},
    }
    decision = "KEEP" if all(b["pass"] for b in bars.values()) else "REJECT"
    return {"n_sessions_input": len(sessions), "n_sessions_usable": n, "n_train": len(train),
            "n_holdout": len(hold), "n_holdout_paired": len(d_vals),
            "holdout_blocks": int(math.ceil(len(hold) / MBB_BLOCK)) if hold else 0,
            "lam_grid": list(LAM_GRID), "lam_training_median_L_svi": lam_scores, "lam_selected": lam_star,
            "mbb": ci, "bars": bars, "decision": decision, "attrition": attrition,
            "holdout_benchmark_states": bench_states, "holdout_svi_slices": svi_slices,
            "holdout_svi_failed_slices": svi_failed, "evaluation_flags": flags, "holdout_rows": rows}


# ------------------------------------------------------------------------------------ S5


def stage_s5(m) -> dict:
    import numpy as np

    base = (0.02, 0.1, -0.5, 0.0, 0.1)
    taus = (0.1, 0.25)
    expiries = (1000, 2000)
    strikes = [float(x) for x in np.linspace(80.0, 120.0, 13)]
    rng = np.random.default_rng(20)
    sessions = []
    screen_counts: dict[str, int] = {}
    for sidx in range(20):
        ja, jb, jr = rng.uniform(0.85, 1.15), rng.uniform(0.85, 1.15), rng.uniform(-0.1, 0.1)
        params = [(base[0] * ja * t, base[1] * jb * t, base[2] + jr, base[3], base[4]) for t in taus]
        recs, fwds = m.synthetic_svi_records(params, expiries, strikes, noise_seed=1000 + sidx)
        screen = m.screen_quotes(recs, session=1, session_open=0, as_of=390, forwards=fwds, roots=("SPX",))
        for k, v in screen["counts"].items():
            screen_counts[str(k)] = screen_counts.get(str(k), 0) + int(v) if isinstance(v, int) else 0
        sessions.append((f"synthetic-{sidx:02d}", m.build_slices(screen, root="SPX")))
    result = run_comparison(m, sessions)
    return {"label": "NON_EVIDENTIAL synthetic mechanics: seeded synthetic raw-SVI sessions with known "
                     "truth; demonstrates that the S4 code path runs end to end; NOT market evidence and "
                     "NOT a verdict input",
            "data_gate_bypassed_for_mechanics_only": True,
            "design": {"sessions": 20, "expiries": list(expiries), "taus": list(taus), "strikes": strikes,
                       "base_svi": list(base), "jitter_seed": 20, "noise_seeds": "1000+i"},
            "screen_counts_total": screen_counts, "mechanics_result": result,
            "mechanics_decision_is_not_a_verdict": True}


# ------------------------------------------------------------------------------------ main


def main() -> int:
    record = {"run": run_index(), "command": [sys.executable] + list(sys.argv),
              "env_threads": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                                              "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")},
              "data_root": DATA, "data_vintage": DATA_VINTAGE}
    # S0 ------------------------------------------------------------------------------
    frz = read_freeze()
    prereg_sha = sha256_file(PREREG)
    amend_sha = sha256_file(AMENDMENT) if os.path.exists(AMENDMENT) else None
    record.update({"prereg_sha256": prereg_sha, "prereg_sha256_frozen": frz.get("PREREG_SHA256"),
                   "amendment_sha256": amend_sha, "amendment_sha256_frozen": frz.get("AMENDMENT_SHA256"),
                   "freeze_log_sha256": sha256_file(FREEZE)})
    amend_ok = True
    if frz.get("AMENDMENT_SHA256") or amend_sha:
        amend_ok = amend_sha == frz.get("AMENDMENT_SHA256")
        if amend_ok:
            with open(AMENDMENT, encoding="utf-8") as fh:
                amend_ok = f"AMENDS_PREREG_SHA256={frz.get('PREREG_SHA256')}" in fh.read()
    if prereg_sha != frz.get("PREREG_SHA256") or not amend_ok:
        record.update({"exit_code": 2, "stage_reached": "S0", "verdict": None,
                       "reason": "freeze hash mismatch; refusing to run"})
        append_run(record)
        print("S0 REFUSED: PREREG/amendment hash differs from FREEZE.log")
        return 2
    record["code_sha256"] = {"evaluate.py": sha256_file(os.path.abspath(__file__)),
                             "engine/options_arbfree_surface.py": sha256_file(MODULE_PATH),
                             "tests/test_options_arbfree_surface.py": sha256_file(TEST_PATH)}
    expected = expected_hashes()
    chain_rels = sorted(r for r in expected if r.startswith("polygon_gex/chains/"))
    snap_rel = "options_skew/snapshots.parquet"
    cand_rels = [r for r in expected if r not in chain_rels and r != snap_rel and r != "engine/options_skew.py"
                 and not r.startswith("_base/")]
    inputs, mismatches = {}, []
    for rel, exp in sorted(expected.items()):
        path = resolve(rel)
        got = sha256_file(path) if os.path.exists(path) else "ABSENT"
        inputs[rel] = got
        if got != exp:
            mismatches.append({"input": rel, "expected": exp, "actual": got})
    record.update({"inputs_sha256": inputs, "input_hash_mismatches": mismatches,
                   "n_declared_inputs": len(expected), "n_chain_files": len(chain_rels)})
    if mismatches:
        # Inputs drifted from the recorded vintage: no stage may read them (finisher fix, audit 2).
        record.update({"exit_code": 4, "stage_reached": "S0", "verdict": None,
                       "reason": "declared input sha256 mismatch; refusing to run S1-S5"})
        append_run(record)
        print("S0 REFUSED: declared input hash mismatch:", [x["input"] for x in mismatches])
        return 4
    outputs = {}
    stage = "S0"
    try:
        # S1 --------------------------------------------------------------------------
        stage = "S1"
        s1 = stage_s1(chain_rels, snap_rel)
        s1["input_hash_mismatches"] = mismatches
        outputs[OUT_BASELINE] = write_json(OUT_BASELINE, s1)
        # S2 --------------------------------------------------------------------------
        stage = "S2"
        s2 = stage_s2(cand_rels, chain_rels, snap_rel)
        outputs[OUT_CENSUS] = write_json(OUT_CENSUS, s2)
        record["a1_candidates_sha256"] = {c["relpath"]: c["sha256"] for c in s2["a1_sweep"]["candidates"]}
        # S3 --------------------------------------------------------------------------
        stage = "S3"
        if s2["contract_complete_sources"]:
            record.update({"exit_code": 3, "stage_reached": stage, "verdict": None,
                           "reason": "contract-complete census candidate without a pre-registered adapter; "
                                     "manual review required before any S4 run",
                           "outputs_sha256": outputs})
            append_run(record)
            print("S3 STOP: contract-complete candidate(s):", s2["contract_complete_sources"])
            return 3
        n_eligible = int(s2["eligible_sessions"])
        gate_pass = n_eligible >= GATE_MIN_SESSIONS and (n_eligible - int(math.floor(
            TRAIN_FRACTION * n_eligible))) >= GATE_MIN_HOLDOUT
        verdict = {
            "brief": "Q01", "schema": "options_arbfree_surface.research.v1",
            "verdict": "INSUFFICIENT_DATA" if not gate_pass else None,
            "eligible_sessions": n_eligible,
            "gate": {"min_sessions": GATE_MIN_SESSIONS, "min_holdout_sessions": GATE_MIN_HOLDOUT,
                     "pass": gate_pass},
            "exact_missing_input": MISSING_INPUT if not gate_pass else None,
            "comparison_run": False, "effect_size_reported": False,
            "baseline_state": s1["state"],
            "baseline_totals": s1.get("totals"),
            "exact_leg_byte_identical": s1.get("exact_leg_compatibility", {}).get("byte_identical"),
            "a1_candidates": s2["a1_sweep"]["n_candidates"],
            "contract_complete_sources": s2["contract_complete_sources"],
            "falsifier_state": "NOT_EVALUATED (comparison not run; challenger not described as reliable)",
            "authority": {"may_display": False, "may_rank": False, "may_alert": False,
                          "may_score": False, "may_deploy": False},
        }
        # S4 is unreachable at this vintage: no adapter exists because no eligible source exists.
        outputs[OUT_VERDICT] = write_json(OUT_VERDICT, verdict)
        # S5 --------------------------------------------------------------------------
        stage = "S5"
        import engine.options_arbfree_surface as m

        s5 = stage_s5(m)
        outputs[OUT_SYNTH] = write_json(OUT_SYNTH, s5)
        record.update({"exit_code": 0, "stage_reached": "S5", "verdict": verdict["verdict"],
                       "outputs_sha256": outputs})
        append_run(record)
        print(json.dumps({"verdict": verdict["verdict"], "eligible_sessions": n_eligible,
                          "baseline": s1["state"], "baseline_totals": s1.get("totals"),
                          "a1_candidates": s2["a1_sweep"]["n_candidates"],
                          "synthetic_decision": s5["mechanics_result"]["decision"],
                          "outputs": outputs}, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - a crash is logged, then re-raised as exit 1
        record.update({"exit_code": 1, "stage_reached": stage, "verdict": None,
                       "error": f"{type(exc).__name__}: {exc}", "outputs_sha256": outputs})
        append_run(record)
        raise


if __name__ == "__main__":
    sys.exit(main())
