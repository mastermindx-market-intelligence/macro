#!/usr/bin/env python3
"""Independent verifier for frozen Theta retrospective v1.1 result artifacts."""

from __future__ import annotations
import argparse, hashlib, json, math, sys
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any
import numpy as np
import pandas as pd
from scipy import stats
from lib import nyse_calendar

TOL = 1e-12
PROTOCOL_SHA = "67011db3d3aed08827f027cafc5b5a2bf890289a1017b227cad15fc240826e68"
FEATURES = {
    "GEX_NORM_TO_FWD_RV": "net_gamma_norm",
    "VEX_NORM_TO_SPY_EXCESS": "net_vanna_norm",
    "CEX_NORM_TO_SPY_EXCESS": "net_charm_norm",
    "VANNA_RELIEF_TO_SPY_EXCESS": "vanna_relief",
    "CW_IVSPREAD_LEVEL_TO_SPY_EXCESS": "cw_ivspread",
    "D5_CW_IVSPREAD_TO_SPY_EXCESS": "d5_cw_ivspread",
    "SKEW_ACCEL_TO_SPY_EXCESS": "skew_accel",
    "TERM_SLOPE_TO_SPY_EXCESS": "term_slope",
    "DOI5_TO_SPY_EXCESS": "doi5",
    "MOM5_BASELINE_TO_SPY_EXCESS": "mom5",
}


def load(path: Path):
    return json.loads(path.read_text())


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fdate(v):
    return date.fromisoformat(str(v)[:10])


def close(actual, expected, name, errors):
    if (
        not isinstance(actual, (int, float))
        or not math.isfinite(float(actual))
        or abs(float(actual) - expected) > TOL
    ):
        errors.append(f"{name}: reported={actual!r} recomputed={expected:.17g}")


def calendar_for(era):
    return nyse_calendar.sessions_between(
        date.fromisoformat(era["start"]), date.fromisoformat(era["end"])
    )


def effective_blocks(rows, h):
    end = None
    n = 0
    for row in sorted(rows, key=lambda x: fdate(x["date"])):
        start = nyse_calendar.session_n_forward(fdate(row["date"]), 1)
        finish = nyse_calendar.session_n_forward(start, h)
        if end is None or start > end:
            n += 1
            end = finish
    return n


def direct_hac(rows, era, h):
    cal = calendar_for(era)
    pos = {d: i for i, d in enumerate(cal)}
    observed = {}
    for row in rows:
        d = fdate(row["date"])
        x = float(row["ic"])
        if d not in pos:
            raise ValueError(f"IC date outside era: {d}")
        if not math.isfinite(x):
            raise ValueError(f"nonfinite IC: {d}")
        if pos[d] in observed:
            raise ValueError(f"duplicate IC date: {d}")
        observed[pos[d]] = x
    values = list(observed.values())
    n = len(values)
    if n < 3:
        return None, "INSUFFICIENT_HAC_OBSERVATIONS"
    m = float(np.mean(values))
    med = float(np.median(values))
    u = np.asarray(
        [observed[i] - m if i in observed else 0.0 for i in range(len(cal))],
        dtype=float,
    )
    lag = min(max(math.floor(4 * (n / 100) ** (2 / 9)), 2 * h), n - 2)
    numerator = float(u @ u)
    for ell in range(1, lag + 1):
        numerator += 2 * (1 - ell / (lag + 1)) * float(u[ell:] @ u[:-ell])
    variance = numerator / (n * n)
    if not math.isfinite(variance) or variance <= 0:
        return {"lag": lag, "variance": variance}, "DEGENERATE_HAC_VARIANCE"
    se = math.sqrt(variance)
    dist = stats.t(df=n - 1)
    critical = float(dist.ppf(0.975))
    return {
        "mean": m,
        "median": med,
        "lag": lag,
        "variance": variance,
        "se": se,
        "t": m / se,
        "p": float(2 * dist.sf(abs(m / se))),
        "ci": [m - critical * se, m + critical * se],
        "df": n - 1,
    }, None


def bh_expectations(pvalues):
    """Tie-invariant BH values; ranks remain an allowed range for equal p values."""
    values = sorted(float(p) for p in pvalues.values())
    groups = []
    for value in values:
        if not groups or value != groups[-1][0]:
            groups.append([value, 1])
        else:
            groups[-1][1] += 1
    cumulative = 0
    terms = []
    for value, count in groups:
        first = cumulative + 1
        cumulative += count
        terms.append((value, first, cumulative, 60 * value / cumulative))
    suffix = 1.0
    by_value = {}
    for value, first, last, term in reversed(terms):
        suffix = min(suffix, term)
        by_value[value] = (first, last, min(1.0, suffix), suffix <= 0.1)
    return {ident: by_value[float(p)] for ident, p in pvalues.items()}


def verify(protocol, result):
    errors = []
    if (
        hashlib.sha256(
            (
                json.dumps(
                    protocol, sort_keys=True, ensure_ascii=True, separators=(",", ":")
                )
                + "\n"
            ).encode()
        ).hexdigest()
        != PROTOCOL_SHA
    ):
        errors.append("frozen protocol SHA mismatch")
    if protocol.get("study_id") != "THETA-EOD-RETROSPECTIVE-ASSOCIATION-V1.1":
        errors.append("unexpected protocol study_id")
    if result.get("study_id") != protocol.get("study_id"):
        errors.append("study_id mismatch")
    if (
        result.get("protocol_sha256")
        != hashlib.sha256(
            (
                json.dumps(
                    protocol, sort_keys=True, ensure_ascii=True, separators=(",", ":")
                )
                + "\n"
            ).encode()
        ).hexdigest()
    ):
        errors.append("protocol_sha256 mismatch")
    manifest = result.get("manifest_sha256")
    if (
        not isinstance(manifest, str)
        or len(manifest) != 64
        or any(c not in "0123456789abcdef" for c in manifest)
    ):
        errors.append("manifest_sha256 malformed")
    for key, want in [
        ("pit_status", "PIT_UNPROVEN"),
        ("research_only", True),
        ("historical_alpha_validated", False),
    ]:
        if result.get(key) != want:
            errors.append(f"{key} guard mismatch")
    contrasts = {c["id"]: c for c in protocol["contrasts"]}
    eras = {e["id"]: e for e in protocol["eras"]}
    horizons = tuple(protocol["horizons_nyse_sessions"])
    expected = {(c, e, h) for c in contrasts for e in eras for h in horizons}
    cells = result.get("cells")
    if result.get("n_cells") != 60:
        errors.append("n_cells must equal 60")
    if result.get("family_size") != 60 or result.get("bh_alpha") != 0.1:
        errors.append("BH family contract mismatch")
    if not isinstance(cells, list):
        raise ValueError("cells must be list")
    indexed = {}
    for cell in cells:
        key = (cell.get("contrast"), cell.get("era"), cell.get("horizon"))
        if key not in expected:
            errors.append(f"unregistered cell {key}")
            continue
        if key in indexed:
            errors.append(f"duplicate cell {key}")
            continue
        indexed[key] = cell
        contrast, era, h = key
        if cell.get("id") != f"{contrast}.{era}.{h}":
            errors.append(f"{key}: id mismatch")
        if cell.get("feature") != FEATURES[contrast]:
            errors.append(f"{key}: feature mismatch")
        target = ("rv" if contrast == "GEX_NORM_TO_FWD_RV" else "excess") + f"_{h}"
        if cell.get("target") != target:
            errors.append(f"{key}: target mismatch")
    if set(indexed) != expected:
        errors.append(f"cell set mismatch: have={len(indexed)} expected=60")
    pvalues = {}
    evaluable = 0
    for key in sorted(expected):
        if key not in indexed:
            continue
        cell = indexed[key]
        contrast, eraid, h = key
        rows = cell.get("ic_series")
        if not isinstance(rows, list):
            errors.append(f"{key}: ic_series not list")
            continue
        n = len(rows)
        blocks = effective_blocks(rows, h)
        close(cell.get("n_dates"), n, f"{key}.n_dates", errors)
        close(cell.get("effective_blocks"), blocks, f"{key}.effective_blocks", errors)
        try:
            inf, hac_reason = direct_hac(rows, eras[eraid], h)
        except ValueError as exc:
            errors.append(f"{key}: {exc}")
            continue
        observed = [float(row["ic"]) for row in rows]
        if observed:
            close(
                cell.get("mean_ic"), float(np.mean(observed)), f"{key}.mean_ic", errors
            )
            close(
                cell.get("median_ic"),
                float(np.median(observed)),
                f"{key}.median_ic",
                errors,
            )
        elif cell.get("mean_ic") is not None or cell.get("median_ic") is not None:
            errors.append(f"{key}: zero-observation mean_ic/median_ic must be null")
        for descriptive in (
            "versus_momentum_descriptive",
            "vanna_ablation_descriptive",
        ):
            d = cell.get(descriptive)
            if not isinstance(d, dict) or d.get("inferential_test") is not False:
                errors.append(f"{key}: {descriptive} must be descriptive-only")
                continue
            paired = d.get("series")
            if not isinstance(paired, list):
                errors.append(f"{key}: {descriptive}.series not list")
                continue
            close(d.get("n_dates"), len(paired), f"{key}.{descriptive}.n_dates", errors)
            diffs = []
            for row in paired:
                try:
                    value = float(row["ic_difference"])
                except (KeyError, TypeError, ValueError):
                    errors.append(f"{key}: malformed {descriptive} row")
                    continue
                if not math.isfinite(value):
                    errors.append(f"{key}: nonfinite {descriptive} difference")
                    continue
                diffs.append(value)
            if diffs:
                close(
                    d.get("mean_paired_ic_difference"),
                    float(np.mean(diffs)),
                    f"{key}.{descriptive}.mean",
                    errors,
                )
            elif d.get("mean_paired_ic_difference") is not None:
                errors.append(f"{key}: empty {descriptive} mean must be null")
            for field in (
                "raw_p",
                "bh_adj_p",
                "bh_rank",
                "bh_reject",
                "reject_h0",
                "p_value",
                "t_stat",
                "ci95",
            ):
                if field in d:
                    errors.append(
                        f"{key}: {descriptive} contains inferential field {field}"
                    )
        support_reason = (
            "INSUFFICIENT_IC_DATES"
            if n < 126
            else ("INSUFFICIENT_NONOVERLAPPING_BLOCKS" if blocks < 30 else hac_reason)
        )
        if support_reason:
            if (
                cell.get("state") != "NON_EVALUABLE"
                or cell.get("reason") != support_reason
            ):
                errors.append(
                    f"{key}: sparse reason/state mismatch, expected {support_reason}"
                )
            for field in ("raw_p", "ci95", "bh_adj_p", "bh_rank"):
                if cell.get(field) is not None:
                    errors.append(f"{key}: {field} must be null when non-evaluable")
            if cell.get("bh_reject") is not False:
                errors.append(f"{key}: bh_reject must be false when non-evaluable")
            continue
        evaluable += 1
        pvalues[cell["id"]] = inf["p"]
        if cell.get("state") != "EVALUABLE" or cell.get("reason") is not None:
            errors.append(f"{key}: evaluable state/reason mismatch")
        for field, val in [
            ("mean_ic", inf["mean"]),
            ("median_ic", inf["median"]),
            ("lag", inf["lag"]),
            ("variance", inf["variance"]),
            ("standard_error", inf["se"]),
            ("t_stat", inf["t"]),
            ("raw_p", inf["p"]),
            ("df", inf["df"]),
        ]:
            close(cell.get(field), val, f"{key}.{field}", errors)
        reported = cell.get("ci95")
        if not isinstance(reported, list) or len(reported) != 2:
            errors.append(f"{key}: ci95 malformed")
        else:
            close(reported[0], inf["ci"][0], f"{key}.ci95[0]", errors)
            close(reported[1], inf["ci"][1], f"{key}.ci95[1]", errors)
    expected_bh = bh_expectations(pvalues)
    reported_ranks = []
    for ident, (rank_min, rank_max, adj, reject) in expected_bh.items():
        cell = next(c for c in cells if c.get("id") == ident)
        reported = cell.get("bh_rank")
        if (
            not isinstance(reported, int)
            or isinstance(reported, bool)
            or not rank_min <= reported <= rank_max
        ):
            errors.append(
                f"{ident}.bh_rank: reported={reported!r} allowed={rank_min}..{rank_max}"
            )
        else:
            reported_ranks.append(reported)
        close(cell.get("bh_adj_p"), adj, f"{ident}.bh_adj_p", errors)
        if cell.get("bh_reject") is not reject:
            errors.append(f"{ident}.bh_reject mismatch")
    if sorted(reported_ranks) != list(range(1, len(expected_bh) + 1)):
        errors.append("bh_rank values must be a unique 1..m permutation")
    return {
        "ok": not errors,
        "errors": errors,
        "cells": 60,
        "evaluable": evaluable,
        "non_evaluable": 60 - evaluable,
        "manifest_sha256": result.get("manifest_sha256"),
        "tolerance": TOL,
        "method": "independent_direct_full_calendar_hac_and_bh_k60",
    }


def self_test(protocol_path):
    from scripts.research.options_history_retrospective import evaluate_cell
    from scripts.research.options_history_gauntlet import _bh_fdr

    protocol = load(protocol_path)
    cal = pd.DatetimeIndex(
        nyse_calendar.sessions_between(date(2017, 1, 1), date(2025, 12, 31))
    )
    roots = ["A", "B", "C", "D", "E", "F"]
    panels = {}
    for r_i, r in enumerate(roots):
        sign = np.array(
            [1 if i % 5 in (0, 1, 2) else -1 for i in range(len(cal))], dtype=float
        )
        rank = float(r_i + 1)
        frame = pd.DataFrame(index=cal)
        for j, feature in enumerate(FEATURES.values()):
            frame[feature] = rank if j % 2 == 0 else -rank
        for h in (5, 21):
            frame[f"excess_{h}"] = sign * rank
            frame[f"rv_{h}"] = sign * rank
            frame[f"label_reason_{h}"] = None
        panels[r] = frame
    cells = [
        evaluate_cell(panels, roots, cal, era, h, c)
        for era in protocol["eras"]
        for h in protocol["horizons_nyse_sessions"]
        for c in FEATURES
    ]
    # This intentionally includes both signs of IC and has full evaluability in all sixty cells.
    result = {
        "study_id": protocol["study_id"],
        "protocol_sha256": sha(protocol_path),
        "manifest_sha256": "a" * 64,
        "pit_status": "PIT_UNPROVEN",
        "research_only": True,
        "historical_alpha_validated": False,
        "n_cells": 60,
        "family_size": 60,
        "bh_alpha": 0.1,
        "cells": cells,
        "quality": {},
        "unsupported": {},
        "interpretation": "synthetic witness",
    }
    pvalues = {c["id"]: c["raw_p"] for c in cells if c["state"] == "EVALUABLE"}
    canonical_bh = _bh_fdr(pvalues, k_family=60, alpha=0.1)
    for c in cells:
        if c["id"] in canonical_bh:
            b = canonical_bh[c["id"]]
            c.update(
                bh_rank=b["rank"], bh_adj_p=b["bh_adj_p"], bh_reject=b["reject_h0"]
            )
    receipt = verify(protocol, result)
    if not receipt["ok"]:
        raise AssertionError(receipt["errors"])
    bad_q = json.loads(json.dumps(result))
    bad_q["cells"][0]["bh_adj_p"] = 0.999999
    if verify(protocol, bad_q)["ok"]:
        raise AssertionError("bad BH adjusted p accepted")
    bad_rank = json.loads(json.dumps(result))
    bad_rank["cells"][0]["bh_rank"] = 1
    if verify(protocol, bad_rank)["ok"]:
        raise AssertionError("bad BH rank accepted")
    if not any(x["mean_ic"] > 0 for x in cells) or not any(
        x["mean_ic"] < 0 for x in cells
    ):
        raise AssertionError("witness lacks positive/negative cells")
    return receipt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result", type=Path, nargs="?")
    ap.add_argument("protocol", type=Path)
    ap.add_argument("--receipt", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    receipt = (
        self_test(args.protocol)
        if args.self_test
        else verify(load(args.protocol), load(args.result))
    )
    if not args.self_test:
        receipt["result_sha256"] = sha(args.result)
    receipt["protocol_sha256"] = sha(args.protocol)
    out = json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n"
    if args.receipt:
        args.receipt.write_text(out)
    else:
        print(out, end="")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
