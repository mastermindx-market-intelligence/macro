from __future__ import annotations

"""Q02 evaluate.py: the single pre-registered evaluation run for the American-exercise and
discrete-dividend pricing/Greek qualification (PREREG.md sections 3, 7, 9, 10 and 11).

RESEARCH ONLY. Nothing here wires, registers, schedules, promotes, gates or activates anything,
and nothing imports this file.

Stages
  0  Guards. sha256(PREREG.md) must equal the hash recorded in FREEZE.log, and only one
     evaluation run may pass the guards per frozen hash. When PREREG_AMENDMENT.md exists, its
     sha256 must equal the last hash recorded in AMENDMENT_FREEZE.log, and the one-run rule
     applies per (frozen PREREG hash, amendment hash) pair, so every rerun needs its own
     recorded amendment written before it. Every run, refusals included, is appended to
     RUNS.log with command, exit code, and input and output sha256s.
  1  Inventory. Every section-3 input is re-hashed; any mismatch, missing or extra chain file
     refuses the run past this stage.
  2  Code baseline: the module's analytic European Greeks reproduce the engine/greeks.py
     formula. Empirical baseline B1: its absence is proven from the chain schemas (no option
     price column, so no implied volatility can be inverted). E1 numerical summary on the
     synthetic section-7 scenarios.
  3  Section-9 attrition census per row and per distinct (date, underlying), for the strict
     arm and the labelled-assumption sensitivity arm, with the module's fail-closed selector
     applied to every chain row using terms provided by the data alone.
  4  Data gate HG. E2 runs only if HG holds.
  5  Absence scan of the whole data root (column/key names only) for joinable option-term,
     option-quote and dividend-schedule sources.

Vendor iv/delta/gamma columns are never read: they are outputs of an undeclared vendor model,
and reconstructing prices or inferring dividends from them is forbidden (PREREG section 9).
"""

import collections
import gzip
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.optimize import brentq

HERE = Path(__file__).resolve().parent
Q02_ROOT = HERE.parents[2]
DATA_ROOT = Path("/Users/chriswong/Documents/Cluade/macro-main/data")
DATA_VINTAGE = "cdab6268"

CHAIN_DIR_REL = "polygon_gex/chains"
SOFR_REL = "ofr/FNYR-SOFR-A.parquet"
CHAIN_COLUMNS_READ = ["underlying", "strike_ticker", "expiry", "K", "is_call", "spot", "asof"]
VENDOR_MODEL_COLUMNS = ("iv", "delta", "gamma")
OCC_RE = re.compile(r"^O:([A-Z0-9.]+?)(\d{6})([CP])(\d{8})$")

# Sensitivity arm only (PREREG section 9): a declared OCC product-class exercise-style map.
# It is an ASSUMPTION, labelled as one in every output that uses it.
EUROPEAN_INDEX_ROOTS = frozenset({"SPX", "SPXW", "XSP", "NDX", "NDXP", "RUT", "RUTW", "MRUT",
                                  "VIX", "VIXW", "DJX", "XEO"})

GATE_MIN_DATES_PER_HALF = 10
GATE_MIN_UNDERLYINGS_TEST = 10

E2_BLOCK = 5
E2_RESAMPLES = 2000
E2_SEED = 2002
E2_BRACKET = (0.005, 5.0)
E2_MIN_TRAIN_INVERSION_RATE = 0.90
E2_KEEP_MIN_VOL_POINTS = 0.5

JSON_SCAN_CAP_BYTES = 8 << 20
CANDIDATE_EXAMPLES = 25

AMENDMENT_NAME = "PREREG_AMENDMENT.md"
AMENDMENT_FREEZE_NAME = "AMENDMENT_FREEZE.log"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_PREREG_MISMATCH = 2
EXIT_ALREADY_RUN = 3
EXIT_INVENTORY_MISMATCH = 4
EXIT_UNINTERPRETED_INPUT = 5

# Column/key-name token groups for the stage judgement and the absence scan (names only).
TOKEN_GROUPS: Dict[str, str] = {
    "EXERCISE": r"exercis|option_style|american|european",
    "DELIVERABLE": r"deliverable|shares_per|multiplier|contract_size|underlying_shares",
    "SETTLEMENT": r"settle|am_pm|expiration_type",
    "DIV_EXDATE": r"(^|[_\s-])ex[_\s-]?(div|date)",
    "DIV_AMOUNT": (r"cash_amount|dividend_amount|div_amount|amount_per_share|per_share_amount|"
                   r"dividend_per_share|dividend.*amount|amount.*dividend|(^|_)dps($|_)"),
    "DIV_DECL": r"declar|known_at|announce|record_date|pay_date|payable",
    "OPT_QUOTE": (r"(^|_)(bid|ask|mid|mark|last|last_price|last_trade|nbbo|close)($|_)|^c$|^vw$|"
                  r"premium|option_price|option_trade_price"),
    "OPT_CONTRACT_ID": (r"strike_ticker|option_contract|option_symbol|(^|_)(occ|osi)(_|$)|"
                        r"contract_id|contract_symbol|contract_ticker|options?_ticker|(^|_)option$"),
}

PREREG_TABLE_RE = re.compile(
    r"^\| ([A-Za-z0-9_./-]+\.(?:parquet|json))(?: \([^|]*\))? \| ([0-9a-f]{64}) \|$")
PREREG_GREEKS_RE = re.compile(r"`engine/greeks\.py` sha256 `([0-9a-f]{64})`")
RESEARCH_REL = "research/quant_assessment_2026_10/Q02_american_exercise_greeks"


# ======================================================================================
# Hashing, RUNS.log and guards
# ======================================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _freeze_hashes(freeze_path: Path) -> List[str]:
    if not freeze_path.exists():
        return []
    out = []
    for line in freeze_path.read_text().splitlines():
        tok = line.split()
        if tok and re.fullmatch(r"[0-9a-f]{64}", tok[0]):
            out.append(tok[0])
    return out


def read_freeze_hash(freeze_path: Path) -> Optional[str]:
    """The first 64-hex token that starts a line of FREEZE.log, or None."""
    hashes = _freeze_hashes(freeze_path)
    return hashes[0] if hashes else None


def read_last_freeze_hash(freeze_path: Path) -> Optional[str]:
    """The last 64-hex token that starts a line (AMENDMENT_FREEZE.log is append-only and gets
    one line per amendment append), or None."""
    hashes = _freeze_hashes(freeze_path)
    return hashes[-1] if hashes else None


def parse_runs_log(runs_log: Path) -> List[Dict[str, object]]:
    """Blocks of RUNS.log as dicts; repeated keys (input/output/note) become lists."""
    if not runs_log.exists():
        return []
    blocks: List[Dict[str, object]] = []
    cur: Optional[Dict[str, object]] = None
    for line in runs_log.read_text().splitlines():
        if line.startswith("=== RUN"):
            cur = {"input": [], "output": [], "note": []}
            continue
        if line.startswith("=== END"):
            if cur is not None:
                blocks.append(cur)
            cur = None
            continue
        if cur is None or ": " not in line:
            continue
        key, val = line.split(": ", 1)
        if key in ("input", "output", "note"):
            cur[key].append(val)  # type: ignore[union-attr]
        else:
            cur[key] = val
    return blocks


def prior_evaluate_runs(runs_log: Path, prereg_hash: str, amendment_hash: str = "none") -> List[str]:
    """Statuses of earlier evaluate runs for this (frozen hash, amendment hash) that passed the
    guards.

    A COMPLETED, BLOCKED or FAILED run counts: once a run has passed the guards it may have
    read data, so a second run under the same frozen state would be a second look (section 11).
    REFUSED runs stop before any outcome-bearing data is read and do not count. A block with no
    amendment_sha256 field ran without an amendment ("none").
    """
    out = []
    for blk in parse_runs_log(runs_log):
        status = str(blk.get("status", ""))
        if (blk.get("kind") == "evaluate" and blk.get("prereg_sha256") == prereg_hash
                and str(blk.get("amendment_sha256", "none")) == amendment_hash
                and status.split(" ")[0] in ("COMPLETED", "BLOCKED", "FAILED")):
            out.append(status)
    return out


def append_run(runs_log: Path, *, kind: str, command: str, exit_code: int, status: str,
               prereg_hash: str, recorded_hash: Optional[str], inputs: Sequence[Tuple[str, str]],
               outputs: Sequence[Tuple[str, str]], notes: Sequence[str],
               elapsed: Optional[float], amendment_hash: Optional[str] = None,
               amendment_recorded: Optional[str] = None) -> None:
    lines = []
    if not runs_log.exists():
        lines += ["# Q02 RUNS.log: append-only. One block per run, refusals included.",
                  "# Fields: kind, command, exit_code, status, prereg_sha256, freeze_recorded_sha256,",
                  "# elapsed_seconds, input/output lines '<path> <sha256>', note lines.", ""]
    lines += ["=== RUN ===", f"kind: {kind}", f"command: {command}", f"exit_code: {exit_code}",
              f"status: {status}", f"prereg_sha256: {prereg_hash}",
              f"freeze_recorded_sha256: {recorded_hash}"]
    if amendment_hash is not None:
        lines += [f"amendment_sha256: {amendment_hash}",
                  f"amendment_freeze_recorded_sha256: {amendment_recorded}"]
    if elapsed is not None:
        lines.append(f"elapsed_seconds: {elapsed:.1f}")
    lines += [f"input: {p} {h}" for p, h in inputs]
    lines += [f"output: {p} {h}" for p, h in outputs]
    lines += [f"note: {n}" for n in notes]
    lines += ["=== END ===", ""]
    with open(runs_log, "a") as fh:
        fh.write("\n".join(lines))


def runtime_notes() -> List[str]:
    env = {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                          "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}
    try:
        nice = os.nice(0)
    except OSError:
        nice = None
    notes = [f"thread_env {' '.join(f'{k}={v}' for k, v in env.items())}", f"niceness {nice}",
             f"python {sys.version.split()[0]} numpy {np.__version__} pandas {pd.__version__}"]
    if any(v != "2" for v in env.values()) or (nice is not None and nice < 10):
        notes.append("runtime_limits_not_as_declared (expected thread limits 2 and nice 10)")
    return notes


# ======================================================================================
# Stage 1: inventory
# ======================================================================================

def parse_prereg_inputs(prereg_text: str) -> Tuple[Dict[str, str], Optional[str]]:
    table = {}
    for line in prereg_text.splitlines():
        m = PREREG_TABLE_RE.match(line.strip())
        if m:
            table[m.group(1)] = m.group(2)
    g = PREREG_GREEKS_RE.search(prereg_text)
    return table, (g.group(1) if g else None)


def inventory(prereg_text: str, data_root: Path, q02_root: Path) -> Dict[str, object]:
    expected, greeks_expected = parse_prereg_inputs(prereg_text)
    chain_expected = sorted(r for r in expected if r.startswith(CHAIN_DIR_REL + "/"))
    chain_dir = data_root / CHAIN_DIR_REL
    chain_present = sorted(f"{CHAIN_DIR_REL}/{p.name}" for p in chain_dir.glob("*.parquet")) \
        if chain_dir.is_dir() else []
    problems = []
    missing = sorted(set(chain_expected) - set(chain_present))
    extra = sorted(set(chain_present) - set(chain_expected))
    problems += [f"chain_missing {r}" for r in missing]
    problems += [f"chain_extra {r}" for r in extra]
    actual = {}
    for rel in sorted(expected):
        p = data_root / rel
        if not p.is_file():
            problems.append(f"input_missing {rel}")
            continue
        actual[rel] = sha256_file(p)
        if actual[rel] != expected[rel]:
            problems.append(f"hash_mismatch {rel}")
    greeks_path = q02_root / "engine" / "greeks.py"
    greeks_actual = sha256_file(greeks_path) if greeks_path.is_file() else None
    if greeks_expected is None or greeks_actual != greeks_expected:
        problems.append("hash_mismatch engine/greeks.py")
    if len(chain_expected) == 0:
        problems.append("prereg_table_has_no_chain_inputs")
    code = {}
    for rel in ("engine/options_american_exercise.py", "tests/test_options_american_exercise.py"):
        p = q02_root / rel
        code[rel] = sha256_file(p) if p.is_file() else None
    return {
        "data_root": str(data_root), "data_vintage": DATA_VINTAGE,
        "expected": expected, "actual": actual,
        "chain_files_expected": len(chain_expected), "chain_files_present": len(chain_present),
        "chain_missing": missing, "chain_extra": extra,
        "greeks_expected": greeks_expected, "greeks_actual": greeks_actual,
        "code_sha256": code, "problems": problems, "ok": not problems,
    }


# ======================================================================================
# Module loading by path (nothing in the repository imports the new module)
# ======================================================================================

def load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ======================================================================================
# Stage 2: code baseline and E1 numerical summary
# ======================================================================================

def code_baseline(mod, greeks) -> Dict[str, object]:
    """Module analytic European Greeks vs the engine/greeks.py formula (T1e on a grid)."""
    cases = []
    for K in (80.0, 100.0, 120.0):
        for T in (0.5, 0.1):
            for q in (0.01, 0.0):
                for is_call in (True, False):
                    cases.append((100.0, K, T, 0.25, is_call, 0.03, q))
    for is_call in (True, False):
        cases.append((4500.0, 4300.0, 0.02, 0.18, is_call, 0.043, 0.0))
        cases.append((37.5, 40.0, 1.7, 0.6, is_call, -0.005, 0.02))
    max_diff = {"delta": 0.0, "gamma": 0.0, "vanna": 0.0, "charm": 0.0}
    for S, K, T, sig, is_call, r, q in cases:
        ours = mod.bs_greeks(S, K, T, sig, is_call, r, q)
        ref = greeks.bs_greeks(S, K, T, sig, is_call, r=r, q=q)
        for name, a, b in zip(max_diff, ours, ref):
            max_diff[name] = max(max_diff[name], abs(a - b))
    degenerate_nan = all(math.isnan(x) for x in mod.bs_greeks(100.0, 100.0, 0.0, 0.25, True))
    worst = max(max_diff.values())
    return {
        "reference": "engine/greeks.py bs_greeks (incumbent European continuous-yield formula)",
        "cases": len(cases), "max_abs_diff": max_diff, "worst": worst,
        "tolerance": 1e-12, "reproduced": worst <= 1e-12 and degenerate_nan,
        "degenerate_input_returns_nan": degenerate_nan,
    }


def e1_numerical(mod, greeks) -> Dict[str, object]:
    """Section-7 tolerances on the synthetic scenarios (no market data)."""
    S0, K0, T0, SIG0, R0, Q0 = 100.0, 100.0, 0.5, 0.25, 0.03, 0.01
    FINE = 400
    checks: List[Dict[str, object]] = []

    def add(cid: str, case: str, value: float, tol: float, passed: bool) -> None:
        checks.append({"id": cid, "case": case, "value": float(value), "tolerance": tol,
                       "pass": bool(passed)})

    statuses = {}
    for is_call in (True, False):
        for K in (80.0, 100.0, 120.0):
            for T in (T0, 0.1):
                qual = mod.qualify_fd(S0, K, T, SIG0, R0, Q0, is_call, american=False)
                lv = {n: qual.quantities[n].levels[2] for n in ("price", "delta", "gamma",
                                                                 "vanna", "charm")}
                d, g, v, c = greeks.bs_greeks(S0, K, T, SIG0, is_call, r=R0, q=Q0)
                p = mod.bs_price(S0, K, T, SIG0, is_call, R0, Q0)
                tag = f"{'call' if is_call else 'put'} K={K:g} T={T:g}"
                add("T1a", tag, abs(lv["price"] - p), 5e-3, abs(lv["price"] - p) <= 5e-3)
                add("T1b", tag, abs(lv["delta"] - d), 2e-3, abs(lv["delta"] - d) <= 2e-3)
                add("T1c", tag, abs(lv["gamma"] - g), 5e-4, abs(lv["gamma"] - g) <= 5e-4)
                tv = 5e-3 + 5e-2 * abs(v)
                tc = 5e-3 + 5e-2 * abs(c)
                add("T1d_vanna", tag, abs(lv["vanna"] - v), tv, abs(lv["vanna"] - v) <= tv)
                add("T1d_charm", tag, abs(lv["charm"] - c), tc, abs(lv["charm"] - c) <= tc)
                statuses[f"european {tag}"] = {n: qual.quantities[n].status for n in lv}
    base = code_baseline(mod, greeks)
    add("T1e", "analytic grid", base["worst"], 1e-12, base["reproduced"])
    for is_call in (True, False):
        d, g, _, _ = greeks.bs_greeks(S0, K0, T0, SIG0, is_call, r=R0, q=Q0)
        p = mod.bs_price(S0, K0, T0, SIG0, is_call, R0, Q0)
        coarse = mod.fd_solve(S0, K0, T0, SIG0, R0, Q0, is_call, False, M=100)
        fine = mod.fd_solve(S0, K0, T0, SIG0, R0, Q0, is_call, False, M=FINE)
        tag = "call" if is_call else "put"
        for name, ref, a, b in (("price", p, coarse.price, fine.price),
                                ("delta", d, coarse.delta, fine.delta),
                                ("gamma", g, coarse.gamma, fine.gamma)):
            add("T1f", f"{tag} {name} err4N-errN", abs(b - ref) - abs(a - ref), 0.0,
                abs(b - ref) < abs(a - ref))
        fd = mod.fd_solve(S0, K0, T0, SIG0, R0, Q0, is_call, False, dividends=[(0.25, 2.0)], M=FINE)
        ref = mod.european_one_dividend_quadrature(S0, K0, T0, SIG0, R0, Q0, is_call, 0.25, 2.0)
        add("T1g", f"{tag} D=2@0.25", abs(fd.price - ref), 1e-2, abs(fd.price - ref) <= 1e-2)
    for K in (80.0, 100.0, 120.0):
        res = mod.fd_solve(S0, K, T0, SIG0, R0, Q0, False, True, M=FINE)
        gap = float(np.min(res.values - np.maximum(K - res.s_nodes, 0.0)))
        add("T2a", f"put K={K:g} min(V-intrinsic)", gap, -1e-10, gap >= -1e-10)
    for is_call in (True, False):
        for divs in ((), ((0.25, 2.0),)):
            grid = mod.build_grid(S0, K0, T0, SIG0, FINE, sum(dv for _, dv in divs))
            am = mod.fd_solve(S0, K0, T0, SIG0, R0, Q0, is_call, True, dividends=divs, grid=grid)
            eu = mod.fd_solve(S0, K0, T0, SIG0, R0, Q0, is_call, False, dividends=divs, grid=grid)
            gap = min(float(np.min(am.values - eu.values)), am.price - eu.price)
            add("T2b", f"{'call' if is_call else 'put'} divs={len(divs)} min(Am-Eu)", gap, -1e-10,
                gap >= -1e-10)
    for K in (80.0, 100.0, 120.0):
        put = mod.fd_solve(S0, K, T0, SIG0, R0, Q0, False, True, M=FINE)
        call = mod.fd_solve(S0, K, T0, SIG0, R0, Q0, True, True, M=FINE)
        ok = put.price < K and call.price < S0 and float(np.max(put.values)) <= K
        add("T2c", f"K={K:g} put<K and call<S", max(put.price - K, call.price - S0), 0.0, ok)
    am = mod.fd_solve(S0, K0, T0, SIG0, R0, 0.0, True, True, M=FINE)
    diff = abs(am.price - mod.bs_price(S0, K0, T0, SIG0, True, R0, 0.0))
    add("T2d", "call q=0 no dividend", diff, 5e-3, diff <= 5e-3)
    for K in (80.0, 100.0, 120.0):
        fd = mod.fd_solve(S0, K, T0, SIG0, R0, Q0, False, True, M=FINE)
        crr = mod.crr_price(S0, K, T0, SIG0, R0, Q0, False, True, steps=2000)
        add("T2e", f"put K={K:g} FD-CRR", abs(fd.price - crr), 2e-2, abs(fd.price - crr) <= 2e-2)
        qual = mod.qualify_fd(S0, K, T0, SIG0, R0, Q0, False, american=True)
        statuses[f"american put K={K:g} T=0.5"] = dict(
            {n: qual.quantities[n].status for n in qual.quantities},
            near_exercise_boundary=bool(qual.near_boundary))
    args = (100.0, 80.0, 0.5, 0.2, 0.03, 0.0, True)
    divs = [(0.25, 5.0)]
    grid = mod.build_grid(100.0, 80.0, 0.5, 0.2, FINE, 5.0)
    am = mod.fd_solve(*args, True, dividends=divs, grid=grid)
    eu = mod.fd_solve(*args, False, dividends=divs, grid=grid)
    crr = mod.crr_price(*args, True, dividends=divs, steps=2000)
    add("T2f", "deep-ITM D=5 call FD-CRR", abs(am.price - crr), 5e-2, abs(am.price - crr) <= 5e-2)
    add("T2f_premium", "deep-ITM D=5 call Am-Eu", am.price - eu.price, 0.5, am.price - eu.price >= 0.5)
    qual = mod.qualify_fd(*args, True, dividends=divs)
    statuses["american call deep-ITM D=5@0.25"] = dict(
        {n: qual.quantities[n].status for n in qual.quantities},
        near_exercise_boundary=bool(qual.near_boundary))
    failed = [f"{c['id']} {c['case']}" for c in checks if not c["pass"]]
    return {"scenarios": "PREREG section 7 (synthetic, relative units)", "finest_levels": FINE,
            "checks": checks, "n_checks": len(checks), "n_failed": len(failed),
            "failed": failed, "all_pass": not failed, "classification_status": statuses}


# ======================================================================================
# Stage 3: attrition census and selector application
# ======================================================================================

def compile_groups() -> Dict[str, "re.Pattern[str]"]:
    return {k: re.compile(v, re.IGNORECASE) for k, v in TOKEN_GROUPS.items()}


def column_groups(names: Iterable[str]) -> Dict[str, List[str]]:
    groups = compile_groups()
    names = list(names)
    return {g: sorted(n for n in names if rx.search(n)) for g, rx in groups.items()}


def provided_flags(names: Iterable[str]) -> Dict[str, bool]:
    """Stage 4-8 judgement from column names: is the term provided by the chain itself?"""
    hit = column_groups([n for n in names if n not in VENDOR_MODEL_COLUMNS])
    return {
        "exercise_style": bool(hit["EXERCISE"]),
        "deliverable_multiplier": bool(hit["DELIVERABLE"]),
        "settlement_clock": bool(hit["SETTLEMENT"]),
        "pit_dividend_schedule": bool(hit["DIV_EXDATE"]) and bool(hit["DIV_AMOUNT"]),
        "option_price": bool(hit["OPT_QUOTE"]),
    }


def load_sofr(path: Path) -> Tuple[np.ndarray, np.ndarray, Dict[str, object]]:
    """SOFR fixings (declared unit: percent; converted to decimal by /100).

    The retained file stores `date` as the pandas index (pandas metadata index_columns), so the
    table is read through pyarrow with the pandas metadata ignored, keeping `date` a column.
    """
    df = pq.read_table(path, columns=["date", "sofr"]).to_pandas(ignore_metadata=True).dropna()
    days = df["date"].to_numpy().astype("datetime64[D]")
    pct = df["sofr"].to_numpy(dtype=float)
    order = np.argsort(days, kind="stable")
    days, pct = days[order], pct[order]
    dec = pct / 100.0
    info = {"rows": int(len(days)), "declared_unit": "percent", "converted": "decimal = percent / 100",
            "share_within_module_rate_bounds": float(np.mean((dec >= -0.1) & (dec <= 0.5)))
            if len(dec) else None}
    return days, dec, info


def rate_lookup(sofr_days: np.ndarray, sofr_dec: np.ndarray, asof_days: np.ndarray,
                asof_ok: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """SOFR for the latest fixing date on or before each snapshot date (section 2)."""
    rate = np.full(len(asof_days), np.nan)
    ok = np.zeros(len(asof_days), dtype=bool)
    if len(sofr_days) == 0:
        return rate, ok
    idx = np.searchsorted(sofr_days, asof_days, side="right") - 1
    ok = asof_ok & (idx >= 0)
    rate[ok] = sofr_dec[idx[ok]]
    return rate, ok


def _distinct(und: pd.Series, mask: np.ndarray) -> int:
    return int(und[mask].nunique(dropna=True))


STAGES = ("rows", "parseable_occ", "exercise_style", "deliverable_multiplier", "settlement_clock",
          "pit_dividend_schedule", "option_price", "rate")


def census_file(df: pd.DataFrame, flags: Mapping[str, bool], sofr_days: np.ndarray,
                sofr_dec: np.ndarray, mod) -> Dict[str, object]:
    """Section-9 stages, selector decisions and pair structure for one chain snapshot."""
    n = len(df)
    und = df["underlying"].astype(object).where(df["underlying"].notna(), None)
    und_list = [None if u is None else str(u) for u in und.tolist()]
    und = pd.Series(und_list, dtype=object)
    tick = df["strike_ticker"].astype(object).where(df["strike_ticker"].notna(), "")
    ext = tick.astype(str).str.extract(OCC_RE.pattern)
    parse = ext[0].notna().to_numpy()
    root = ext[0].where(ext[0].notna(), None)
    root_list = [None if r is None or (isinstance(r, float) and math.isnan(r)) else str(r)
                 for r in root.tolist()]
    adj_cache: Dict[Tuple[Optional[str], Optional[str]], Optional[bool]] = {}
    adj = np.zeros(n, dtype=bool)
    adj_known = np.zeros(n, dtype=bool)
    for i, (r, u) in enumerate(zip(root_list, und_list)):
        key = (r, u)
        if key not in adj_cache:
            adj_cache[key] = mod._adjusted_looking(r, u)
        val = adj_cache[key]
        adj_known[i] = val is not None
        adj[i] = bool(val)
    # Unknown (no root or no underlying) is neither standard- nor adjusted-looking.
    std = parse & adj_known & ~adj
    adjm = parse & adj_known & adj

    K = df["K"].to_numpy(dtype=float)
    is_call = df["is_call"].astype("boolean").fillna(False).to_numpy(dtype=bool)
    call_known = df["is_call"].notna().to_numpy()
    exp = df["expiry"]
    exp_ok = exp.notna().to_numpy()
    exp_day_min = np.where(exp_ok, exp.to_numpy().astype("datetime64[D]").astype("datetime64[m]")
                           .astype("int64"), 0)
    asof = df["asof"]
    asof_ok = asof.notna().to_numpy()
    asof_min = np.where(asof_ok, asof.to_numpy().astype("datetime64[m]").astype("int64"), 0)
    asof_days = asof.to_numpy().astype("datetime64[D]")
    rate, rate_ok = rate_lookup(sofr_days, sofr_dec, asof_days, asof_ok)
    spot = df["spot"].to_numpy(dtype=float)

    # Consistency diagnostics between the OCC symbol and the parsed columns (counts only).
    with np.errstate(invalid="ignore"):
        strike_parsed = pd.to_numeric(ext[3], errors="coerce").to_numpy(dtype=float) / 1000.0
    cons_strike = int(np.sum(parse & (np.abs(strike_parsed - K) <= 1e-6)))
    cp = ext[2].to_numpy(dtype=object)
    cons_cp = int(np.sum(parse & call_known & ((cp == "C") == is_call)))
    occ_day = pd.to_datetime("20" + ext[1].astype(str), format="%Y%m%d", errors="coerce")
    cons_exp = int(np.sum(parse & exp_ok & (occ_day.to_numpy().astype("datetime64[D]")
                                              == exp.to_numpy().astype("datetime64[D]"))))

    # Stage masks. Stages 4-8 are judged from the chain's own columns (flags); a provided
    # term would need an interpreter, which the caller refuses to guess.
    # The caller refuses any file whose own columns provide one of these terms, so here each
    # stage-4..8 term is absent from the chain; the strict arm never guesses a style.
    if any(flags.values()):
        raise ValueError("census_file requires a chain with no provided term columns")
    zeros = np.zeros(n, dtype=bool)
    strict_style = zeros
    sens_style_val = [None if r is None else ("EUROPEAN" if r in EUROPEAN_INDEX_ROOTS else "AMERICAN")
                      for r in root_list]
    sens_style = np.array([v is not None for v in sens_style_val], dtype=bool)
    sens_eur = np.array([v == "EUROPEAN" for v in sens_style_val], dtype=bool)
    deliv = zeros
    settle = zeros
    divs = zeros
    price = zeros

    def chain(style_mask: np.ndarray,
              base: np.ndarray) -> Tuple[Dict[str, Tuple[int, int]], np.ndarray]:
        c = {"rows": np.ones(n, dtype=bool) & base}
        c["parseable_occ"] = c["rows"] & parse
        c["exercise_style"] = c["parseable_occ"] & style_mask
        c["deliverable_multiplier"] = c["exercise_style"] & deliv
        c["settlement_clock"] = c["deliverable_multiplier"] & settle
        c["pit_dividend_schedule"] = c["settlement_clock"] & divs
        c["option_price"] = c["pit_dividend_schedule"] & price
        c["rate"] = c["option_price"] & rate_ok
        return {k: (int(v.sum()), _distinct(und, v)) for k, v in c.items()}, c["rate"]

    ones = np.ones(n, dtype=bool)
    strict_cum, strict_final = chain(strict_style, ones)
    strict_cum_std, _ = chain(strict_style, std)
    sens_cum, sens_final = chain(sens_style, ones)
    sens_cum_std, _ = chain(sens_style, std)
    marginal_masks = {"rows": ones, "parseable_occ": parse, "standard_looking_root": std,
                      "adjusted_looking_root": adjm, "exercise_style": strict_style,
                      "exercise_style_sensitivity_map": sens_style,
                      "deliverable_multiplier": deliv, "settlement_clock": settle,
                      "pit_dividend_schedule": divs, "option_price": price, "rate": rate_ok}
    marginal = {k: (int(v.sum()), _distinct(und, v)) for k, v in marginal_masks.items()}

    # Module selector on every row, terms from the data alone. sigma is None: there is no
    # option price to invert, and the vendor iv is never used. clock is None: no settlement
    # clock is provided. Deliverable, multiplier and settlement are None (not provided).
    hist_strict: collections.Counter = collections.Counter()
    hist_sens: collections.Counter = collections.Counter()
    avail_strict = np.zeros(n, dtype=bool)
    avail_sens = np.zeros(n, dtype=bool)
    no_clock_rows = 0
    K_list = K.tolist()
    spot_list = [None if not math.isfinite(s) else float(s) for s in spot.tolist()]
    rate_list = [float(x) if ok else None for x, ok in zip(rate.tolist(), rate_ok.tolist())]
    for i in range(n):
        if not asof_ok[i]:
            no_clock_rows += 1
            continue
        v = int(asof_min[i])
        market = mod.MarketInputs(spot=spot_list[i], sigma=None, rate=rate_list[i],
                                  continuous_yield=None, valuation=v, cutoff=v, dividends=None)
        eds = int(exp_day_min[i]) if exp_ok[i] else None
        for style, hist, avail in ((None, hist_strict, avail_strict),
                                   (sens_style_val[i], hist_sens, avail_sens)):
            terms = mod.ContractTerms(underlying=und_list[i], occ_root=root_list[i],
                                      exercise_style=style, deliverable_kind=None,
                                      deliverable_shares=None, multiplier=None, settlement=None,
                                      expiry_day_start=eds, strike=K_list[i],
                                      is_call=bool(is_call[i]))
            dec = mod.select_model(terms, None, market)
            hist[(dec.model, dec.reasons)] += 1
            if dec.model != mod.MODEL_UNAVAILABLE:
                avail[i] = True

    # Pair structure: (underlying, expiry, strike) groups with a call and a put.
    def pairs(mask: np.ndarray) -> Tuple[int, int]:
        if not mask.any():
            return 0, 0
        sub = pd.DataFrame({"u": und[mask].to_numpy(), "e": exp_day_min[mask], "k": K[mask],
                            "c": is_call[mask]})
        g = sub.groupby(["u", "e", "k"], dropna=True)["c"].agg(["any", "all"])
        both = g[g["any"] & ~g["all"]]
        return int(len(both)), int(both.index.get_level_values(0).nunique())

    structural_mask = parse & call_known & exp_ok & np.isfinite(K) & und.notna().to_numpy()
    s_pairs, s_unds = pairs(structural_mask)
    e_strict, e_strict_u = pairs(strict_final & avail_strict)
    e_sens, e_sens_u = pairs(sens_final & avail_sens)
    e_strict_priced = pairs(strict_final & avail_strict & price)[0]
    e_sens_priced = pairs(sens_final & avail_sens & price)[0]
    priced_pairs = pairs(structural_mask & price)[0]
    elig_und_strict = set(und[strict_final & avail_strict].dropna().tolist())
    elig_und_sens = set(und[sens_final & avail_sens].dropna().tolist())
    return {
        "rows": n,
        "distinct_underlyings": _distinct(und, ones),
        "cumulative_strict": strict_cum, "cumulative_strict_standard_root": strict_cum_std,
        "cumulative_sensitivity": sens_cum, "cumulative_sensitivity_standard_root": sens_cum_std,
        "marginal": marginal,
        "sensitivity_european_rows": int(sens_eur.sum()),
        "sensitivity_european_roots": sorted({r for r, e in zip(root_list, sens_eur) if e and r}),
        "consistency": {"strike": cons_strike, "call_put": cons_cp, "expiry": cons_exp,
                        "parseable": int(parse.sum()),
                        "root_relation_unknown": int(np.sum(parse & ~adj_known))},
        "selector_strict": hist_strict, "selector_sensitivity": hist_sens,
        "selector_available_strict": int(avail_strict.sum()),
        "selector_available_sensitivity": int(avail_sens.sum()),
        "rows_without_valuation_clock": no_clock_rows,
        "structural_pairs": s_pairs, "structural_pair_underlyings": s_unds,
        "structural_pairs_priced_both_legs": priced_pairs,
        "eligible_pairs_strict": e_strict, "eligible_pair_underlyings_strict": e_strict_u,
        "eligible_pairs_priced_strict": e_strict_priced,
        "eligible_pairs_priced_sensitivity": e_sens_priced,
        "eligible_pairs_sensitivity": e_sens, "eligible_pair_underlyings_sensitivity": e_sens_u,
        "eligible_underlyings_strict": sorted(elig_und_strict),
        "eligible_underlyings_sensitivity": sorted(elig_und_sens),
    }


def merge_counts(acc: Dict[str, List[int]], part: Mapping[str, Tuple[int, int]]) -> None:
    for k, (r, d) in part.items():
        cur = acc.setdefault(k, [0, 0])
        cur[0] += r
        cur[1] += d


def gate_decision(per_date: Sequence[Mapping[str, object]], arm: str) -> Dict[str, object]:
    """HG thresholds (a)-(c) for one arm from per-date census results (dates ascending)."""
    n = len(per_date)
    half = n // 2
    train, test = per_date[:half], per_date[half:]
    key = f"eligible_pairs_{arm}"
    a_train = sum(1 for d in train if d[key] > 0)
    a_test = sum(1 for d in test if d[key] > 0)
    test_unds = set()
    for d in test:
        test_unds |= set(d[f"eligible_underlyings_{arm}"])
    n_elig = sum(int(d[key]) for d in per_date)
    # Every eligible pair must carry a data-provided price on both legs. With zero eligible
    # pairs (c) is only vacuously true and is reported as such; HG then fails on (a) and (b).
    priced = sum(int(d[f"eligible_pairs_priced_{arm}"]) for d in per_date)
    c_holds = priced == n_elig
    a = a_train >= GATE_MIN_DATES_PER_HALF and a_test >= GATE_MIN_DATES_PER_HALF
    b = len(test_unds) >= GATE_MIN_UNDERLYINGS_TEST
    return {
        "arm": arm, "dates_total": n, "dates_train": len(train), "dates_test": len(test),
        "a_dates_with_eligible_pair_train": a_train, "a_dates_with_eligible_pair_test": a_test,
        "a_threshold_per_half": GATE_MIN_DATES_PER_HALF, "a_holds": a,
        "b_test_underlyings_with_eligible_pairs": len(test_unds),
        "b_threshold": GATE_MIN_UNDERLYINGS_TEST, "b_holds": b,
        "c_eligible_pairs": n_elig, "c_priced_both_legs": priced,
        "c_holds": c_holds, "c_note": "vacuous over 0 eligible pairs" if n_elig == 0 else "",
        "hg_holds": bool(a and b and c_holds),
    }


# ======================================================================================
# E2 (conditional on HG): implemented to the frozen section-10 specification
# ======================================================================================

def invert_iv(price_fn: Callable[[float], float], target: float,
              bracket: Tuple[float, float] = E2_BRACKET) -> Optional[float]:
    """Brent root of price_fn(sigma) = target on the fixed bracket, or None (no root)."""
    lo, hi = bracket
    try:
        flo = price_fn(lo) - target
        fhi = price_fn(hi) - target
    except ValueError:
        return None
    if not (math.isfinite(flo) and math.isfinite(fhi)) or flo * fhi > 0.0:
        return None
    if flo == 0.0:
        return lo
    if fhi == 0.0:
        return hi
    return float(brentq(lambda s: price_fn(s) - target, lo, hi, xtol=1e-10, rtol=1e-12,
                        maxiter=200))


def daily_statistic(gaps_by_underlying: Mapping[str, Sequence[Tuple[float, float]]]) -> Optional[float]:
    """D_d = mean over underlyings of [median g_EUR - median g_AMER] (vol points)."""
    vals = []
    for pairs_u in gaps_by_underlying.values():
        if pairs_u:
            arr = np.asarray(pairs_u, dtype=float)
            vals.append(float(np.median(arr[:, 0]) - np.median(arr[:, 1])))
    return float(np.mean(vals)) if vals else None


def moving_block_bootstrap(x: Sequence[float], block: int = E2_BLOCK, resamples: int = E2_RESAMPLES,
                           seed: int = E2_SEED) -> Optional[Tuple[float, float, float]]:
    """Point estimate and 95% percentile interval of the mean by moving-block bootstrap."""
    arr = np.asarray(x, dtype=float)
    n = len(arr)
    if n < block or not np.all(np.isfinite(arr)):
        return None
    rng = np.random.default_rng(seed)
    k = math.ceil(n / block)
    offsets = np.arange(block)
    means = np.empty(resamples)
    for b in range(resamples):
        starts = rng.integers(0, n - block + 1, size=k)
        idx = (starts[:, None] + offsets[None, :]).ravel()[:n]
        means[b] = arr[idx].mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(arr.mean()), float(lo), float(hi)


def e2_decision(estimate: float, lower: float, upper: float) -> str:
    if estimate >= E2_KEEP_MIN_VOL_POINTS and lower > 0.0:
        return "KEEP"
    if upper < E2_KEEP_MIN_VOL_POINTS:
        return "REJECT"
    return "INSUFFICIENT_DATA"


# ======================================================================================
# Stage 5: absence scan (names only)
# ======================================================================================

KEY_RE = re.compile(rb'"([A-Za-z0-9_ .\-]{1,64})"\s*:')


def _names_of(path: Path, low: str) -> Tuple[Optional[str], Optional[List[str]]]:
    if low.endswith(".parquet"):
        return "parquet", list(pq.read_schema(path).names)
    if low.endswith((".json", ".jsonl", ".gz")):
        opener = gzip.open if low.endswith(".gz") else open
        with opener(path, "rb") as fh:
            buf = fh.read(JSON_SCAN_CAP_BYTES)
        return "json_like", sorted({k.decode("ascii", "replace") for k in KEY_RE.findall(buf)})
    if low.endswith(".csv"):
        with open(path, "r", errors="replace") as fh:
            head = fh.readline()
        return "csv", [c.strip().strip('"') for c in head.split(",") if c.strip()]
    if low.endswith((".xlsx", ".xls")):
        return "spreadsheet_unscanned", None
    return None, None


def absence_scan(data_root: Path) -> Dict[str, object]:
    groups = compile_groups()
    kinds: collections.Counter = collections.Counter()
    skipped_ext: collections.Counter = collections.Counter()
    errors: collections.Counter = collections.Counter()
    group_files: Dict[str, collections.Counter] = {g: collections.Counter() for g in groups}
    group_keys: Dict[str, collections.Counter] = {g: collections.Counter() for g in groups}
    cands: Dict[str, List[Tuple[str, Dict[str, List[str]]]]] = {
        "option_terms": [], "option_quote": [], "dividend_schedule": []}
    inv_lines = []
    unscanned = []
    for root, dirs, files in os.walk(data_root):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for f in sorted(files):
            p = Path(root) / f
            rel = p.relative_to(data_root).as_posix()
            try:
                size = p.stat().st_size
            except OSError:
                errors["stat"] += 1
                continue
            inv_lines.append(f"{rel}\t{size}")
            low = f.lower()
            try:
                kind, names = _names_of(p, low)
            except Exception as exc:  # noqa: BLE001 - counted, never silently dropped
                errors[type(exc).__name__] += 1
                continue
            if kind is None:
                skipped_ext[low.rsplit(".", 1)[-1] if "." in low else ""] += 1
                continue
            kinds[kind] += 1
            if names is None:
                unscanned.append(rel)
                continue
            top = rel.split("/")[0]
            hit = {g: sorted(n for n in names if rx.search(n)) for g, rx in groups.items()}
            for g, v in hit.items():
                if v:
                    group_files[g][top] += 1
                    for nm in v:
                        group_keys[g][nm.lower()] += 1
            lower = [n.lower() for n in names]
            contract = bool(hit["OPT_CONTRACT_ID"]) or (any("strike" in n for n in lower)
                                                        and any("expir" in n for n in lower))
            keep = {g: v[:12] for g, v in hit.items() if v}
            if contract and (hit["EXERCISE"] or hit["DELIVERABLE"] or hit["SETTLEMENT"]):
                cands["option_terms"].append((rel, keep))
            if contract and hit["OPT_QUOTE"]:
                cands["option_quote"].append((rel, keep))
            if hit["DIV_EXDATE"] and hit["DIV_AMOUNT"]:
                cands["dividend_schedule"].append((rel, keep))
    rules = {}
    for rule, lst in cands.items():
        by_top = collections.Counter(r.split("/")[0] for r, _ in lst)
        examples = []
        for rel, keep in lst[:CANDIDATE_EXAMPLES]:
            examples.append({"path": rel, "sha256": sha256_file(data_root / rel), "keys": keep})
        sizes = []
        for rel, _ in lst:
            try:
                sizes.append(f"{rel}\t{(data_root / rel).stat().st_size}")
            except OSError:
                sizes.append(f"{rel}\t?")
        rules[rule] = {"files": len(lst), "by_top_dir": dict(by_top.most_common()),
                       "examples": examples,
                       "list_digest_sha256": sha256_text("\n".join(sizes))}
    terms = cands["option_terms"]
    liftable = {
        "stage4_exercise_style": [r for r, k in terms if "EXERCISE" in k],
        "stage5_deliverable_multiplier": [r for r, k in terms if "DELIVERABLE" in k],
        "stage6_settlement_clock": [r for r, k in terms if "SETTLEMENT" in k],
        "stage7_pit_dividend_schedule": [r for r, _ in cands["dividend_schedule"]],
    }
    return {
        "scope": "file names, parquet schemas, csv header lines, json/jsonl/gz keys in the first "
                 f"{JSON_SCAN_CAP_BYTES} bytes; spreadsheets not scanned; no row values read",
        "files_scanned_by_kind": dict(kinds), "skipped_extensions": dict(skipped_ext.most_common()),
        "errors": dict(errors), "unscanned_spreadsheets": unscanned,
        "inventory_files": len(inv_lines),
        "inventory_digest_sha256": sha256_text("\n".join(inv_lines)),
        "token_groups": TOKEN_GROUPS,
        "group_files_by_top_dir": {g: dict(c.most_common(12)) for g, c in group_files.items()},
        "group_key_names": {g: dict(c.most_common(25)) for g, c in group_keys.items()},
        "candidate_rules": {
            "option_terms": "contract id AND (EXERCISE or DELIVERABLE or SETTLEMENT) key",
            "option_quote": "contract id AND OPT_QUOTE key",
            "dividend_schedule": "DIV_EXDATE AND DIV_AMOUNT key",
            "contract_id": "OPT_CONTRACT_ID key, or a strike key together with an expiry key",
        },
        "candidates": rules,
        "liftable_stage_sources": {k: {"files": len(v), "examples": v[:CANDIDATE_EXAMPLES]}
                                   for k, v in liftable.items()},
    }


# ======================================================================================
# Driver
# ======================================================================================

def _json_default(o: object) -> object:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    raise TypeError(type(o).__name__)


def write_json(path: Path, obj: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=1, sort_keys=True, default=_json_default) + "\n"
    path.write_text(text)
    return sha256_text(text)


def _hist_rows(hist: collections.Counter) -> List[Dict[str, object]]:
    return [{"model": m, "reasons": list(r), "rows": c}
            for (m, r), c in sorted(hist.items(), key=lambda kv: -kv[1])]


def run(here: Path, q02_root: Path, data_root: Path, argv: Sequence[str]) -> int:
    t0 = time.perf_counter()
    command = " ".join([sys.executable, *argv])
    runs_log = here / "RUNS.log"
    prereg_path = here / "PREREG.md"
    freeze_path = here / "FREEZE.log"
    prereg_hash = sha256_file(prereg_path)
    recorded = read_freeze_hash(freeze_path)
    amend_path = here / AMENDMENT_NAME
    amend_freeze_path = here / AMENDMENT_FREEZE_NAME
    amend_hash = sha256_file(amend_path) if amend_path.exists() else "none"
    amend_recorded = read_last_freeze_hash(amend_freeze_path) if amend_freeze_path.exists() else "none"
    notes = runtime_notes() + [f"data_root {data_root} (read-only, vintage {DATA_VINTAGE})"]
    inputs: List[Tuple[str, str]] = [(f"{RESEARCH_REL}/PREREG.md", prereg_hash)]
    if freeze_path.exists():
        inputs.append((f"{RESEARCH_REL}/FREEZE.log", sha256_file(freeze_path)))
    if amend_path.exists():
        inputs.append((f"{RESEARCH_REL}/{AMENDMENT_NAME}", amend_hash))
    if amend_freeze_path.exists():
        inputs.append((f"{RESEARCH_REL}/{AMENDMENT_FREEZE_NAME}", sha256_file(amend_freeze_path)))
    inputs.append((f"{RESEARCH_REL}/evaluate.py", sha256_file(Path(__file__).resolve())))

    def log(status: str, code: int, outputs: Sequence[Tuple[str, str]] = (),
            extra: Sequence[str] = ()) -> int:
        append_run(runs_log, kind="evaluate", command=command, exit_code=code, status=status,
                   prereg_hash=prereg_hash, recorded_hash=recorded, inputs=inputs,
                   outputs=outputs, notes=list(notes) + list(extra),
                   elapsed=time.perf_counter() - t0, amendment_hash=amend_hash,
                   amendment_recorded=amend_recorded)
        print(f"{status} exit={code}")
        return code

    if recorded is None or recorded != prereg_hash:
        return log("REFUSED prereg_hash_differs_from_freeze_log", EXIT_PREREG_MISMATCH)
    if amend_recorded is None or amend_hash != amend_recorded:
        return log("REFUSED amendment_hash_differs_from_amendment_freeze_log", EXIT_PREREG_MISMATCH)
    prior = prior_evaluate_runs(runs_log, prereg_hash, amend_hash)
    if prior:
        return log("REFUSED one_run_per_frozen_hash_already_used", EXIT_ALREADY_RUN,
                   extra=[f"prior_status {s}" for s in prior])

    results = here / "results"
    outputs: List[Tuple[str, str]] = []

    def out(name: str, obj: object) -> None:
        outputs.append((f"{RESEARCH_REL}/results/{name}", write_json(results / name, obj)))

    try:
        prereg_text = prereg_path.read_text()
        inv = inventory(prereg_text, data_root, q02_root)
        for rel, h in sorted(inv["actual"].items()):
            inputs.append((f"data/{rel}", h))
        inputs.append(("engine/greeks.py", str(inv["greeks_actual"])))
        for rel, h in sorted(inv["code_sha256"].items()):
            inputs.append((rel, str(h)))
        out("inventory.json", inv)
        if not inv["ok"]:
            return log("REFUSED inventory_mismatch", EXIT_INVENTORY_MISMATCH, outputs,
                       [f"problem {p}" for p in inv["problems"]])

        mod = load_by_path("q02_options_american_exercise",
                           q02_root / "engine" / "options_american_exercise.py")
        greeks = load_by_path("q02_incumbent_greeks", q02_root / "engine" / "greeks.py")

        chain_rels = sorted(r for r in inv["expected"] if r.startswith(CHAIN_DIR_REL + "/"))
        schemas = {r: list(pq.read_schema(data_root / r).names) for r in chain_rels}
        flags_by_file = {r: provided_flags(n) for r, n in schemas.items()}
        union_cols = sorted({c for n in schemas.values() for c in n})
        baseline = {
            "code_baseline": code_baseline(mod, greeks),
            "empirical_baseline_B1": {
                "definition": "European continuous-yield BS (engine/greeks.py formula, q = 0) "
                              "inverted to the observed option mid price",
                "chain_columns_union": union_cols,
                "price_columns_present": sorted({c for n in schemas.values()
                                                 for c in column_groups(n)["OPT_QUOTE"]}),
                "reproducible": any(f["option_price"] for f in flags_by_file.values()),
                "absence_reason": "no chain file carries bid/ask/mid/last; the vendor iv column "
                                  "is a vendor-model output and is never used as a price",
            },
        }
        out("baseline.json", baseline)
        e1 = e1_numerical(mod, greeks)
        out("e1_numerical.json", e1)

        provided_any = sorted({k for f in flags_by_file.values() for k, v in f.items() if v})
        if provided_any:
            return log("REFUSED uninterpreted_provided_term_columns", EXIT_UNINTERPRETED_INPUT,
                       outputs, [f"provided {k}: a terms interpreter and a PREREG amendment are "
                                 "required before any further stage" for k in provided_any])

        sofr_days, sofr_dec, sofr_info = load_sofr(data_root / SOFR_REL)
        per_date: List[Dict[str, object]] = []
        acc = {k: {} for k in ("cumulative_strict", "cumulative_strict_standard_root",
                               "cumulative_sensitivity", "cumulative_sensitivity_standard_root",
                               "marginal")}
        hist_strict: collections.Counter = collections.Counter()
        hist_sens: collections.Counter = collections.Counter()
        cons = collections.Counter()
        sens_roots: set = set()
        totals = collections.Counter()
        for rel in chain_rels:
            df = pq.read_table(data_root / rel, columns=CHAIN_COLUMNS_READ).to_pandas()
            res = census_file(df, flags_by_file[rel], sofr_days, sofr_dec, mod)
            for k in acc:
                merge_counts(acc[k], res[k])
            hist_strict.update(res["selector_strict"])
            hist_sens.update(res["selector_sensitivity"])
            cons.update(res["consistency"])
            sens_roots |= set(res["sensitivity_european_roots"])
            for k in ("rows", "selector_available_strict", "selector_available_sensitivity",
                      "rows_without_valuation_clock", "structural_pairs",
                      "structural_pairs_priced_both_legs", "eligible_pairs_strict",
                      "eligible_pairs_sensitivity", "sensitivity_european_rows"):
                totals[k] += int(res[k])
            per_date.append({
                "date": Path(rel).stem, "rows": res["rows"],
                "distinct_underlyings": res["distinct_underlyings"],
                "parseable": res["marginal"]["parseable_occ"][0],
                "rate_rows": res["marginal"]["rate"][0],
                "structural_pairs": res["structural_pairs"],
                "structural_pair_underlyings": res["structural_pair_underlyings"],
                "eligible_pairs_strict": res["eligible_pairs_strict"],
                "eligible_pairs_sensitivity": res["eligible_pairs_sensitivity"],
                "eligible_pairs_priced_strict": res["eligible_pairs_priced_strict"],
                "eligible_pairs_priced_sensitivity": res["eligible_pairs_priced_sensitivity"],
                "eligible_underlyings_strict": res["eligible_underlyings_strict"],
                "eligible_underlyings_sensitivity": res["eligible_underlyings_sensitivity"],
            })
        per_date.sort(key=lambda d: d["date"])
        half = len(per_date) // 2
        attrition = {
            "unit_note": "each count is [rows, distinct (date, underlying)]",
            "stages_cumulative": list(STAGES),
            "stage3_partition": "standard-looking root (root equals underlying, no digit suffix) "
                                "vs adjusted-looking; both carried into stage 4 in the "
                                "'cumulative_*' chains, standard-looking only in "
                                "'cumulative_*_standard_root'",
            "stage_judgement": "stages 4-8 judged from the chain's own columns; the absence scan "
                               "reports any other source that could be joined",
            "chain_provided_flags": flags_by_file[chain_rels[0]] if chain_rels else {},
            "chain_provided_flags_identical_across_files":
                len({json.dumps(f, sort_keys=True) for f in flags_by_file.values()}) == 1,
            "sensitivity_arm": {
                "label": "ASSUMPTION: declared OCC product-class exercise-style map, support "
                         "reporting only, not a trial",
                "european_roots": sorted(EUROPEAN_INDEX_ROOTS),
                "european_roots_seen": sorted(sens_roots),
                "rows_mapped_european": totals["sensitivity_european_rows"],
            },
            **{k: {s: v for s, v in acc[k].items()} for k in acc},
            "occ_consistency_rows": dict(cons),
            "sofr": sofr_info,
            "totals": dict(totals),
            "per_date": [{k: v for k, v in d.items() if not k.startswith("eligible_underlyings")}
                         for d in per_date],
            "split": {"train_dates": [d["date"] for d in per_date[:half]],
                      "test_dates": [d["date"] for d in per_date[half:]]},
        }
        out("attrition.json", attrition)
        selector = {
            "inputs": "terms from the data alone: underlying, OCC root, strike, call/put, expiry "
                      "day; exercise style None (strict) or the labelled map (sensitivity); "
                      "deliverable, multiplier and settlement None; clock None; spot from the "
                      "chain; sigma None (no option price; vendor iv never used); rate SOFR; "
                      "continuous yield None; dividends None; valuation = cutoff = asof minute",
            "strict": _hist_rows(hist_strict), "sensitivity": _hist_rows(hist_sens),
            "rows_decided_strict": sum(hist_strict.values()),
            "rows_decided_sensitivity": sum(hist_sens.values()),
            "rows_not_unavailable_strict": totals["selector_available_strict"],
            "rows_not_unavailable_sensitivity": totals["selector_available_sensitivity"],
            "rows_without_valuation_clock": totals["rows_without_valuation_clock"],
        }
        out("selector.json", selector)

        absence = absence_scan(data_root)
        out("absence_scan.json", absence)

        gate_strict = gate_decision(per_date, "strict")
        gate_sens = gate_decision(per_date, "sensitivity")
        missing = [s for s in STAGES[2:] if acc["cumulative_strict"][s][0] == 0]
        first_zero_strict = next((s for s in STAGES if acc["cumulative_strict"][s][0] == 0), None)
        first_zero_sens = next((s for s in STAGES if acc["cumulative_sensitivity"][s][0] == 0), None)
        marg = acc["marginal"]
        zero_marginal = [s for s in ("exercise_style", "deliverable_multiplier", "settlement_clock",
                                     "pit_dividend_schedule", "option_price")
                         if marg[s][0] == 0]
        lift = absence["liftable_stage_sources"]
        robust = {
            "strict_fails_at": first_zero_strict,
            "sensitivity_fails_at": first_zero_sens,
            "joinable_sources_for_failing_stages": {
                "exercise_style": lift["stage4_exercise_style"]["files"],
                "deliverable_multiplier": lift["stage5_deliverable_multiplier"]["files"],
                "settlement_clock": lift["stage6_settlement_clock"]["files"],
                "pit_dividend_schedule": lift["stage7_pit_dividend_schedule"]["files"],
            },
        }
        hg = gate_strict["hg_holds"]
        if hg:
            e2 = {"status": "BLOCKED", "reason": "HG holds but no terms interpreter exists; a "
                  "PREREG amendment is required before E2 may run"}
            out("gate.json", {"strict": gate_strict, "sensitivity": gate_sens, "e2": e2})
            return log("BLOCKED hg_holds_without_terms_interpreter", EXIT_UNINTERPRETED_INPUT,
                       outputs)
        e2 = {"status": "NOT_RUN", "reason": "HG fails (PREREG section 9): E2 is not run",
              "estimate_vol_points": None, "ci95": None, "decision": None,
              "honest_n": {"test_dates_with_eligible_pairs": 0, "blocks": 0,
                           "underlyings": 0, "eligible_pairs": 0}}
        gate = {"strict": gate_strict, "sensitivity": gate_sens, "e2": e2,
                "structural_pairs_all_dates": totals["structural_pairs"],
                "structural_pairs_priced_both_legs": totals["structural_pairs_priced_both_legs"],
                "robustness": robust}
        out("gate.json", gate)
        verdict = "INSUFFICIENT_DATA"
        summary = {
            "verdict": verdict,
            "reason": "HG fails (PREREG section 9), so E2 (the single trial) is not run; stages "
                      "with zero marginal row support in the retained chains: "
                      + (", ".join(zero_marginal) if zero_marginal else "none"),
            "missing_inputs_strict_cumulative": missing,
            "zero_support_stages_marginal": zero_marginal,
            "e1_all_pass": e1["all_pass"], "e1_failed": e1["failed"],
            "code_baseline_reproduced": baseline["code_baseline"]["reproduced"],
            "empirical_baseline_reproducible": baseline["empirical_baseline_B1"]["reproducible"],
            "hg_strict": gate_strict["hg_holds"], "hg_sensitivity": gate_sens["hg_holds"],
            "rows": totals["rows"], "dates": len(per_date),
            "selector_rows_not_unavailable": [totals["selector_available_strict"],
                                              totals["selector_available_sensitivity"]],
            "real_contract_outputs": "UNAVAILABLE (every row)",
            "e2": "NOT_RUN",
        }
        out("summary.json", summary)
        return log("COMPLETED", EXIT_OK, outputs, [f"verdict {verdict}"])
    except Exception as exc:  # noqa: BLE001 - logged as FAILED, then re-raised
        log(f"FAILED {type(exc).__name__}: {exc}", EXIT_FAILED, outputs)
        raise


if __name__ == "__main__":
    sys.exit(run(HERE, Q02_ROOT, DATA_ROOT, sys.argv))
