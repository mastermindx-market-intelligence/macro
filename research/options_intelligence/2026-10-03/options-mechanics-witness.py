#!/usr/bin/env python3
"""Bounded research witness; executes pinned pure functions, never production paths.

Usage: python options-mechanics-witness.py --output options-mechanics-witness.json
Requires Python 3.10+, NumPy, pandas, and Node.js. No network calls or installation.
Source capsules embedded below are inserted from already-fetched immutable files.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd

TERMINAL_HEDGE_PROFILE_TYPESCRIPT = r'''export function hedgeProfile(
  rows: readonly MscStrikeRow[] | null | undefined,
  greek: HedgeGreek,
  spot: number | null | undefined,
): HedgeProfile {
  const field = greekField(greek);
  const out: HedgeRow[] = [];
  for (const r of rows ?? []) {
    if (!r || !isNum(r.strike)) continue;
    const v = r[field];
    if (!isNum(v)) continue;
    // negate: dealer ACTION is the mirror of the dealer POSITION change
    out.push({ strike: r.strike, hedgeMn: v === 0 ? 0 : -v });
  }
  out.sort((a, b) => a.strike - b.strike);

  const anchored = SECOND_ORDER.has(greek) && isNum(spot) && spot > 0;
  const cumulative: { strike: number; cumMn: number }[] = [];

  if (!anchored) {
    let acc = 0;
    for (const r of out) {
      acc += r.hedgeMn;
      cumulative.push({ strike: r.strike, cumMn: acc });
    }
  } else {
    const s = spot as number;
    const below = out.filter((r) => r.strike < s).sort((a, b) => b.strike - a.strike);
    const above = out.filter((r) => r.strike >= s);
    let accDown = 0;
    const down: { strike: number; cumMn: number }[] = [];
    for (const r of below) {
      accDown += r.hedgeMn;
      down.push({ strike: r.strike, cumMn: accDown });
    }
    down.reverse();
    let accUp = 0;
    const up: { strike: number; cumMn: number }[] = [];
    for (const r of above) {
      accUp += r.hedgeMn;
      up.push({ strike: r.strike, cumMn: accUp });
    }
    cumulative.push(...down, ...up);
  }

  let maxAbsMn = 0;
  for (const r of out) maxAbsMn = Math.max(maxAbsMn, Math.abs(r.hedgeMn));
  let maxAbsCumMn = 0;
  for (const c of cumulative) maxAbsCumMn = Math.max(maxAbsCumMn, Math.abs(c.cumMn));

  return { greek, rows: out, cumulative, anchored, maxAbsMn, maxAbsCumMn, perUnit: PER_UNIT[greek] };
}
'''

TERMINAL_PRELUDE_TYPESCRIPT = r'''const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
export const SECOND_ORDER: ReadonlySet<HedgeGreek> = new Set<HedgeGreek>(["gamma", "vanna", "charm"]);
const PER_UNIT: Record<HedgeGreek, HedgeProfile["perUnit"]> = {
  gamma: "1% spot",
  vanna: "1 vol point",
  charm: "1 day",
  delta: "position",
};

function greekField(greek: HedgeGreek): keyof MscStrikeRow {
  return greek === "gamma" ? "gamma_net"
    : greek === "delta" ? "delta_net"
    : greek === "vanna" ? "vanna_net"
    : "charm_net";
}
'''

MACRO_FUNCTIONS_PYTHON = r'''def gamma_profile(c: pd.DataFrame, S: float, cfg: dict):
    """Net dealer gamma RE-PRICED across a ±25% spot grid — the exposure PROFILE.

    This is the category's flagship object (masterplan §4.2 `profile`): exposure as a
    FUNCTION of spot, not merely at it. It is also the single source for the flip —
    ``_gamma_flip`` delegates here so the published curve and the published crossing
    can never disagree (the 2026-08-01 defect family was exactly two derivations of
    one quantity drifting apart).

    Returns ``(grid, net, flips)`` — numpy arrays of trial spots and net dealer gamma
    in dollars per ``pct_move`` at each, plus every zero-crossing (interpolated) —
    or ``(None, None, [])`` when the chain is too thin to re-price.
    """
    g = c.dropna(subset=["K", "T", "iv"])
    if len(g) < 20 or not (S > 0):
        return None, None, []
    K = g["K"].to_numpy(float); T = g["T"].to_numpy(float)
    sig = g["iv"].to_numpy(float); oi = g["oi"].to_numpy(float)
    sgn = np.where(g["is_call"].to_numpy(bool), 1.0, -1.0)
    r, q, mult, pm = cfg["r"], cfg["q"], cfg["contract_multiplier"], cfg["pct_move"]
    sqrtT = np.sqrt(T)
    grid = S * np.linspace(0.75, 1.25, 101)
    net = np.empty(len(grid))
    for i, Sx in enumerate(grid):
        d1 = (np.log(Sx / K) + (r - q + 0.5 * sig * sig) * T) / (sig * sqrtT)
        gamma = np.exp(-q * T) * np.exp(-0.5 * d1 * d1) / SQRT2PI / (Sx * sig * sqrtT)
        net[i] = float(np.sum(sgn * gamma * oi * mult * Sx * Sx * pm))
    flips = []
    for i in range(len(grid) - 1):
        if net[i] == 0.0 or (net[i] < 0) != (net[i + 1] < 0):
            x0, x1, y0, y1 = grid[i], grid[i + 1], net[i], net[i + 1]
            flips.append(float(x0 - y0 * (x1 - x0) / (y1 - y0) if y1 != y0 else x0))
    return grid, net, flips


def _gamma_flip(c: pd.DataFrame, S: float, cfg: dict):
    """Zero-gamma spot via a ±25% spot grid reevaluation (clone of
    collectors/deribit._gamma_flip, with the equity multiplier + r/q). ABOVE flip =
    net long gamma (dealers dampen / pin); BELOW = net short (dealers amplify).
    Returns (flip, signed dist-to-flip %, regime). Thin wrapper over
    ``gamma_profile`` — one grid evaluation, one definition."""
    grid, net, flips = gamma_profile(c, S, cfg)
    if grid is None:
        return None, None, None
    if not flips:
        return None, None, ("long" if net[len(grid) // 2] >= 0 else "short")
    flip = min(flips, key=lambda f: abs(f - S))
    return float(flip), round(100.0 * (S - flip) / S, 2), ("long" if S >= flip else "short")
'''

SOURCE_CAPSULE = {
  "terminal": {
    "repository": "mastermindx-market-intelligence/mastermind-terminal",
    "commit": "a049d46fa2415d3949aae5efc0ee515b6667c7a0",
    "path": "terminal/lib/marketStructure.ts",
    "url": "https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/a049d46fa2415d3949aae5efc0ee515b6667c7a0/terminal/lib/marketStructure.ts",
    "git_blob_sha": "b57bb1b794522c80af5a8288a82bcb06d64ed939",
    "file_sha256": "9dbb320e5f89dee717e8f6d7fa044ec36036a46c514dc685efd5dcd8cb1c852a",
    "file_bytes": 32139,
    "function_lines": "646-697",
    "prelude_lines": "86,597,623-635",
    "function_sha256": "fd21c46014e78e3bf68cb2dfd944c46056a90cb7c9fc1367a885adc2b7a9f053"
  },
  "macro": {
    "repository": "mastermindx-market-intelligence/macro",
    "commit": "6f5e78e94e8808582a650cdfa0fc3357040a179c",
    "path": "engine/gex_engine.py",
    "url": "https://github.com/mastermindx-market-intelligence/macro/blob/6f5e78e94e8808582a650cdfa0fc3357040a179c/engine/gex_engine.py",
    "git_blob_sha": "15cff47b86b6a452daa6268a7f8be5455f914b13",
    "file_sha256": "781298048633b08050ae00fe6bb5fd89fdc20d0d040630e7b0a4b3d7d5e97e2c",
    "file_bytes": 10018,
    "function_lines": "43-90",
    "function_sha256": "77d8691290f482573b55a7ffcfe26c9cee64c358ee1eabe6ab9fb45728e0637e"
  },
  "terminal_ui": {
    "repository": "mastermindx-market-intelligence/mastermind-terminal",
    "commit": "a049d46fa2415d3949aae5efc0ee515b6667c7a0",
    "path": "terminal/components/msc/HedgingCards.tsx",
    "url": "https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/a049d46fa2415d3949aae5efc0ee515b6667c7a0/terminal/components/msc/HedgingCards.tsx",
    "git_blob_sha": "b3562a6b227673a94e8f2cc55bb55b64fe87dce3",
    "file_sha256": "55b9d401674b8f4b283a0c0b02f9d5f032912f60e067af97f71624c54aaac67e",
    "file_bytes": 18225
  }
}
SOURCE_CAPSULE['terminal']['hedge_profile_typescript'] = TERMINAL_HEDGE_PROFILE_TYPESCRIPT
SOURCE_CAPSULE['terminal']['prelude_typescript'] = TERMINAL_PRELUDE_TYPESCRIPT
SOURCE_CAPSULE['macro']['functions_python'] = MACRO_FUNCTIONS_PYTHON


@dataclass(frozen=True)
class Option:
    K: float
    T: float
    sigma: float
    n: float
    is_call: bool = True
    multiplier: float = 100.0


def phi(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def delta(o, S, sigma=None):
    vol = o.sigma if sigma is None else sigma
    d1 = (math.log(S / o.K) + 0.5 * vol * vol * o.T) / (vol * math.sqrt(o.T))
    return cdf(d1) - (0.0 if o.is_call else 1.0)


def gamma(o, S):
    d1 = (math.log(S / o.K) + 0.5 * o.sigma * o.sigma * o.T) / (o.sigma * math.sqrt(o.T))
    return phi(d1) / (S * o.sigma * math.sqrt(o.T))


def gamma_rows(book, S0):
    rows = {}
    for o in book:
        rows[o.K] = rows.get(o.K, 0.0) + o.n * o.multiplier * gamma(o, S0) * S0 * S0 * 0.01 / 1e6
    return [{"strike": k, "gamma_net": v} for k, v in sorted(rows.items())]


def endpoint_hedge(book, S0, target):
    q0 = -sum(o.n * o.multiplier * delta(o, S0) for o in book)
    q1 = -sum(o.n * o.multiplier * delta(o, target) for o in book)
    d_shares = q1 - q0
    return {"S0": S0, "target_spot": target, "initial_hedge_shares": q0,
            "target_hedge_shares": q1, "hedge_share_change": d_shares,
            "H_dollars": target * d_shares, "H_mn": target * d_shares / 1e6,
            "cash_balance_change_dollars": -target * d_shares}


def terminal_function_js():
    """Erase only explicit TypeScript annotations; keep the algorithm unchanged."""
    source = SOURCE_CAPSULE["terminal"]["hedge_profile_typescript"]
    assert hashlib.sha256(source.encode()).hexdigest() == SOURCE_CAPSULE["terminal"]["function_sha256"]
    header = "export function hedgeProfile(\n  rows: readonly MscStrikeRow[] | null | undefined,\n  greek: HedgeGreek,\n  spot: number | null | undefined,\n): HedgeProfile {"
    substitutions = [
        (header, "function hedgeProfile(rows, greek, spot) {"),
        ("const out: HedgeRow[] = [];", "const out = [];"),
        ("const cumulative: { strike: number; cumMn: number }[] = [];", "const cumulative = [];"),
        ("const s = spot as number;", "const s = spot;"),
        ("const down: { strike: number; cumMn: number }[] = [];", "const down = [];"),
        ("const up: { strike: number; cumMn: number }[] = [];", "const up = [];"),
    ]
    for old, new in substitutions:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    prelude = SOURCE_CAPSULE["terminal"]["prelude_typescript"]
    prelude_substitutions = [
        ("(v: unknown): v is number", "(v)"),
        ("export const SECOND_ORDER: ReadonlySet<HedgeGreek> = new Set<HedgeGreek>", "const SECOND_ORDER = new Set"),
        ('const PER_UNIT: Record<HedgeGreek, HedgeProfile["perUnit"]>', "const PER_UNIT"),
        ("function greekField(greek: HedgeGreek): keyof MscStrikeRow", "function greekField(greek)"),
    ]
    for old, new in prelude_substitutions:
        assert prelude.count(old) == 1, old
        prelude = prelude.replace(old, new)
    return prelude + "\n" + source


def terminal_profiles(cases):
    node = os.environ.get("CODEX_PRIMARY_RUNTIME_NODE") or shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required to execute the original Terminal algorithm")
    program = terminal_function_js() + "\n" + (
        "const fs = require('fs');\n"
        "const cases = JSON.parse(fs.readFileSync(0,'utf8'));\n"
        "process.stdout.write(JSON.stringify(cases.map(c => hedgeProfile(c.rows,c.greek,c.spot))));\n"
    )
    result = subprocess.run([node, "-e", program], input=json.dumps(cases), text=True,
                            capture_output=True, check=True)
    version = subprocess.run([node, "--version"], text=True, capture_output=True, check=True).stdout.strip()
    return json.loads(result.stdout), version, hashlib.sha256(program.encode()).hexdigest()


def macro_functions():
    source = SOURCE_CAPSULE["macro"]["functions_python"]
    assert hashlib.sha256(source.encode()).hexdigest() == SOURCE_CAPSULE["macro"]["function_sha256"]
    tree = ast.parse(source)
    assert [x.name for x in tree.body if isinstance(x, ast.FunctionDef)] == ["gamma_profile", "_gamma_flip"]
    assert all(isinstance(x, ast.FunctionDef) for x in tree.body)
    namespace = {"np": np, "pd": pd, "SQRT2PI": math.sqrt(2.0 * math.pi)}
    exec(compile(tree, "pinned_macro_gex_engine_functions", "exec"), namespace)
    return namespace["gamma_profile"], namespace["_gamma_flip"]


def cumulative_at(profile, strike):
    matches = [r["cumMn"] for r in profile["cumulative"] if r["strike"] == strike]
    assert len(matches) == 1
    return matches[0]


def simpson_delta_change(book, lo, hi, intervals=2000):
    step = (hi - lo) / intervals
    values = [sum(o.n * o.multiplier * gamma(o, lo + j * step) for o in book)
              for j in range(intervals + 1)]
    return step / 3.0 * (values[0] + values[-1] + 4.0 * sum(values[1:-1:2]) + 2.0 * sum(values[2:-1:2]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    S0 = 100.0
    normal_T = 30.0 / 365.0
    zero_book = [Option(100.0, normal_T, 0.2, 1000.0), Option(110.0, normal_T, 0.2, 1000.0)]
    base_book = [Option(95.0, normal_T, 0.2, 1000.0), Option(105.0, normal_T, 0.2, 1000.0)]
    more_lower = [replace(base_book[0], n=3000.0), base_book[1]]
    shared = Option(110.0, normal_T, 0.2, 1000.0)

    def matched_pair(first, alternative):
        weight = first.n * gamma(first, S0) / gamma(alternative, S0)
        return [first, shared], [replace(alternative, n=weight), shared]

    maturity_a, maturity_b = matched_pair(Option(100.0, 7.0 / 365.0, 0.2, 1000.0),
                                           Option(100.0, 180.0 / 365.0, 0.2, 1.0))
    iv_a, iv_b = matched_pair(Option(100.0, normal_T, 0.1, 1000.0),
                             Option(100.0, normal_T, 0.5, 1.0))
    books = {"zero_move": zero_book, "lower_branch": base_book, "more_lower_strike_inventory": more_lower,
             "matched_maturity_A": maturity_a, "matched_maturity_B": maturity_b,
             "matched_iv_A": iv_a, "matched_iv_B": iv_b}
    cases = [{"rows": gamma_rows(b, S0), "greek": "gamma", "spot": S0} for b in books.values()]
    # Same economic rows in reverse input order: source explicitly sorts them.
    cases.append({"rows": list(reversed(gamma_rows(base_book, S0))), "greek": "gamma", "spot": S0})
    profiles_raw, node_version, js_sha = terminal_profiles(cases)
    profiles = dict(zip(books, profiles_raw))
    assert profiles_raw[-1] == profiles["lower_branch"]

    zero = endpoint_hedge(zero_book, S0, S0)
    zero["source_profile_value_at_spot_mn_per_plus_1pct"] = cumulative_at(profiles["zero_move"], S0)
    assert zero["H_dollars"] == 0.0
    assert zero["source_profile_value_at_spot_mn_per_plus_1pct"] < 0

    lower = endpoint_hedge(base_book, S0, 95.0)
    lower["source_profile_value_at_target_mn_per_plus_1pct"] = cumulative_at(profiles["lower_branch"], 95.0)
    upper = endpoint_hedge(base_book, S0, 105.0)
    upper["source_profile_value_at_target_mn_per_plus_1pct"] = cumulative_at(profiles["lower_branch"], 105.0)
    assert lower["H_dollars"] > 0 > lower["source_profile_value_at_target_mn_per_plus_1pct"]
    assert upper["H_dollars"] < 0

    omitted = {"baseline": upper, "more_lower_strike_inventory": endpoint_hedge(more_lower, S0, 105.0)}
    omitted["more_lower_strike_inventory"]["source_profile_value_at_target_mn_per_plus_1pct"] = cumulative_at(profiles["more_lower_strike_inventory"], 105.0)
    assert omitted["baseline"]["source_profile_value_at_target_mn_per_plus_1pct"] == omitted["more_lower_strike_inventory"]["source_profile_value_at_target_mn_per_plus_1pct"]
    assert abs(omitted["baseline"]["H_dollars"] - omitted["more_lower_strike_inventory"]["H_dollars"]) > 1e6

    matched = {}
    for label, a, b in [("maturity", maturity_a, maturity_b), ("iv", iv_a, iv_b)]:
        rows_a, rows_b = gamma_rows(a, S0), gamma_rows(b, S0)
        err = max(abs(ra["gamma_net"] - rb["gamma_net"]) for ra, rb in zip(rows_a, rows_b))
        assert err < 1e-12
        pa, pb = profiles["matched_" + label + "_A"], profiles["matched_" + label + "_B"]
        profile_err = max(abs(x["cumMn"] - y["cumMn"]) for x, y in zip(pa["cumulative"], pb["cumulative"]))
        assert profile_err < 1e-12
        ha, hb = endpoint_hedge(a, S0, 110.0), endpoint_hedge(b, S0, 110.0)
        assert abs(ha["H_dollars"] - hb["H_dollars"]) > 1e6
        matched[label] = {"book_A": [asdict(o) for o in a], "book_B": [asdict(o) for o in b],
                          "snapshot_gamma_max_error_mn": err, "profile_max_error_mn": profile_err,
                          "source_profile_at_target_A_mn_per_plus_1pct": cumulative_at(pa, 110.0),
                          "source_profile_at_target_B_mn_per_plus_1pct": cumulative_at(pb, 110.0),
                          "A": ha, "B": hb}

    tiny = endpoint_hedge(base_book, S0, S0 + 0.0001)
    total_gamma_shares_per_dollar = sum(o.n * o.multiplier * gamma(o, S0) for o in base_book)
    tiny_approx = -tiny["target_spot"] * total_gamma_shares_per_dollar * (tiny["target_spot"] - S0)
    tiny_rel_error = abs(tiny_approx - tiny["H_dollars"]) / abs(tiny["H_dollars"])
    assert tiny_rel_error < 1e-4
    integrated = -105.0 * simpson_delta_change(base_book, S0, 105.0)
    assert math.isclose(integrated, upper["H_dollars"], rel_tol=1e-9, abs_tol=1e-5)
    short_hedge = endpoint_hedge([replace(o, n=-o.n) for o in base_book], S0, 105.0)
    assert math.isclose(short_hedge["H_dollars"], -upper["H_dollars"], rel_tol=1e-12)
    # Equal sigma*sqrt(T), r=q=0, frozen inputs: different T/IV alone need not change a spot-only curve.
    equal_voltime = [replace(o, T=4.0*o.T, sigma=0.5*o.sigma) for o in base_book]
    equal_hedge = endpoint_hedge(equal_voltime, S0, 105.0)
    assert math.isclose(equal_hedge["H_dollars"], upper["H_dollars"], rel_tol=1e-12)

    gamma_profile, gamma_flip = macro_functions()
    cfg = {"r": 0.0, "q": 0.0, "contract_multiplier": 100.0, "pct_move": 0.01}

    def chain(orientation):
        # Twenty distinct positive-OI contracts pass the function's documented >=20-row gate.
        low_call = orientation == "descending"
        rows = [{"K": 95.0 + j * 0.01, "T": normal_T, "iv": 0.2, "oi": 100.0,
                 "is_call": low_call} for j in range(10)]
        rows += [{"K": 105.0 + j * 0.01, "T": normal_T, "iv": 0.2, "oi": 100.0,
                  "is_call": not low_call} for j in range(10)]
        if orientation == "all_calls":
            for row in rows:
                row["is_call"] = True
        return pd.DataFrame(rows)

    flip_witnesses = []
    for orientation, spot in [("descending", 98.0), ("descending", 101.0),
                              ("ascending", 98.0), ("ascending", 101.0), ("all_calls", 101.0)]:
        c = chain(orientation)
        grid, net, flips = gamma_profile(c, spot, cfg)
        flip, distance, regime = gamma_flip(c, spot, cfg)
        middle = len(grid) // 2
        assert math.isclose(grid[middle], spot, abs_tol=1e-12)
        actual = "long" if net[middle] > 0 else "short" if net[middle] < 0 else "zero"
        selected_crossing = None
        if flip is not None:
            j = int(np.searchsorted(grid, flip) - 1)
            selected_crossing = {"left_spot": float(grid[j]), "right_spot": float(grid[j+1]),
                                 "left_gamma_dollars_per_1pct": float(net[j]),
                                 "right_gamma_dollars_per_1pct": float(net[j+1]),
                                 "orientation": "ascending" if net[j+1] > net[j] else "descending"}
        agrees = regime == actual
        if orientation == "descending":
            assert len(flips) == 1 and not agrees
            assert selected_crossing["orientation"] == "descending"
        else:
            assert agrees
        flip_witnesses.append({"chain": orientation, "input_spot": spot, "contract_rows": len(c),
                               "assumed_sign": "call +1; put -1", "returned_flip": flip,
                               "all_flips": flips, "returned_distance_percent": distance,
                               "returned_regime": regime, "same_curve_gamma_at_spot_dollars_per_1pct": float(net[middle]),
                               "same_curve_regime": actual, "regime_agrees_with_own_curve": agrees,
                               "selected_crossing": selected_crossing})

    result = {
        "title": "Options mechanics: bounded source and synthetic numerical witness",
        "research_date": "2026-10-03", "status": "PASS: all intended counterexample and control assertions",
        "production_execution": False, "production_mutations": False,
        "claim_scope": "Pinned pure-source execution and synthetic Black-Scholes scenarios only; no live runtime, dealer inventory, prediction, or alpha claim.",
        "convention": {"r": 0, "q": 0, "T_unit": "years, frozen during spot move", "volatility": "annual decimal, frozen during spot move",
                       "option_position": "n signed contracts; positive long; multiplier shares per contract",
                       "hedge_shares": "q(S)=-sum(n*multiplier*Delta(S))",
                       "H": "S_target*(q_target-q_initial), dollars; positive underlying buy trade notional",
                       "cash": "cash balance change from one endpoint hedge trade is -H; financing and existing cash mark excluded",
                       "path_limit": "H is endpoint rehedge notional, not cumulative continuously executed trading cash or turnover",
                       "gamma_rows": "sum(n*multiplier*Gamma(S0)*S0^2*0.01)/1e6; $mn sensitivity per +1% spot at S0",
                       "matched_weights": "Fractional signed scenario weights are intentional analytic portfolio scalings, not observed contract counts."},
        "source_provenance": {k: {kk: vv for kk, vv in v.items() if kk not in ("hedge_profile_typescript", "prelude_typescript", "functions_python")}
                              for k, v in SOURCE_CAPSULE.items()},
        "execution": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                      "node": node_version, "terminal_js_program_sha256": js_sha,
                      "terminal_method": "Original source with enumerated TypeScript-only type erasure, executed in Node",
                      "macro_method": "Original gamma_profile and _gamma_flip ASTs only; injected numpy/pandas/SQRT2PI; no production imports"},
        "terminal_inputs": {name: {"book": [asdict(o) for o in b], "rows": gamma_rows(b, S0), "profile": profiles[name]} for name, b in books.items()},
        "witness_zero_move": zero, "witness_lower_branch": lower, "witness_upper_branch_control": upper,
        "witness_omitted_inventory": omitted, "witness_matched_gamma": matched,
        "controls": {"reversed_input_same_profile": True, "tiny_move_exact_H_dollars": tiny["H_dollars"],
                     "tiny_move_gamma_approx_H_dollars": tiny_approx, "tiny_move_relative_error": tiny_rel_error,
                     "all_strike_gamma_spot_integral_H_dollars": integrated, "exact_H_dollars_for_integral": upper["H_dollars"],
                     "inventory_sign_reversal_H_dollars": short_hedge["H_dollars"],
                     "equal_sigma_sqrtT_same_H_dollars": equal_hedge["H_dollars"]},
        "macro_synthetic_chain_recipe": {"lower_strikes": "95.00 + 0.01*j, j=0..9", "upper_strikes": "105.00 + 0.01*j, j=0..9",
                                          "T": normal_T, "iv": 0.2, "oi_each": 100, "multiplier": 100,
                                          "descending": "lower calls, upper puts", "ascending": "lower puts, upper calls",
                                          "all_calls": "both groups calls"},
        "witness_gamma_flip": flip_witnesses,
    }
    payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(payload)
        print(json.dumps({"status": result["status"], "output": str(args.output), "bytes": len(payload.encode()),
                          "sha256": hashlib.sha256(payload.encode()).hexdigest()}, indent=2))
    else:
        sys.stdout.write(payload)


if __name__ == "__main__":
    main()
