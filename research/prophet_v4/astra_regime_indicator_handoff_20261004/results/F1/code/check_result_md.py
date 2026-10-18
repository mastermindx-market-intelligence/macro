"""H2/P2: Verify every LABELLED number in RESULT.md matches its SPECIFIC key in
result.json at the rendered precision.

P2 (round 4): parse BOTH bounds of every `95% week-cluster CI | [lo, hi]` cell;
bind `h1 (≤ 5)` to hazard.overall.h1[0] (the height), not n_h1; compare every
hazard height (not only CI bounds); a scalar h1 is a MISMATCH (schema
violation), never a TypeError.

Mutations on either side (RESULT.md or result.json) must produce >= 1 mismatch.
The four specified mutations plus the extra scalar-h1 mutation are exercised
by run_specified_mutations() on scratch copies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent

TOL = 0.5e-3  # 4-decimal rendering matches; 3-decimal CIs also match


def _drill(payload, key_path):
    val = payload
    for k in key_path:
        if isinstance(val, list):
            try:
                val = val[int(k)]
            except (ValueError, IndexError, TypeError):
                return None, False
        elif isinstance(val, dict):
            if k not in val:
                return None, False
            val = val[k]
        else:
            # scalar where a nested key was requested → schema miss
            return val, False
    return val, True


def _find_number_after(md_text: str, label: str) -> float | None:
    idx = md_text.find(label)
    if idx < 0:
        return None
    snippet = md_text[idx + len(label): idx + len(label) + 80]
    m = re.search(r"[+\-]?\d+(?:\.\d+)?", snippet)
    if not m:
        return None
    return float(m.group())


def _bracket_pair_after(md_text: str, label: str) -> tuple[float, float] | None:
    """Parse BOTH bounds of the first `[lo, hi]` after `label`."""
    idx = md_text.find(label)
    if idx < 0:
        return None
    snippet = md_text[idx: idx + 240]
    m = re.search(
        r"\[\s*([+\-]?\d+(?:\.\d+)?)\s*,\s*([+\-]?\d+(?:\.\d+)?)\s*\]",
        snippet,
    )
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def _all_bracket_pairs_after_label(md_text: str, label: str) -> list[tuple[float, float]]:
    out = []
    for m in re.finditer(re.escape(label), md_text):
        snippet = md_text[m.start(): m.start() + 240]
        bm = re.search(
            r"\[\s*([+\-]?\d+(?:\.\d+)?)\s*,\s*([+\-]?\d+(?:\.\d+)?)\s*\]",
            snippet,
        )
        if bm:
            out.append((float(bm.group(1)), float(bm.group(2))))
    return out


def _bold_number_in_row(md_text: str, label: str) -> float | None:
    """The height in a markdown table row is rendered bold (`**0.1246**`)."""
    idx = md_text.find(label)
    if idx < 0:
        return None
    line = md_text[idx:].split("\n", 1)[0]
    m = re.search(r"\*\*([+\-]?\d+(?:\.\d+)?)\*\*", line)
    if m:
        return float(m.group(1))
    return None


def _close(a, b) -> bool:
    try:
        return abs(float(a) - float(b)) < TOL
    except (TypeError, ValueError):
        return False


# LABELED pairs (md_label, [key_path...], kind).
# kind:
#   first     — first number after the label
#   bold      — bold number on the same table row (hazard heights)
#   (default first)
LABELED_CHECKS = [
    ("Episodes kept (all 3 horizons non-null) | **", ["honest_n", "episodes"], "first"),
    ("Distinct as_of dates | **", ["honest_n", "as_of_dates"], "first"),
    ("Distinct as_of ISO weeks | **", ["honest_n", "as_of_weeks"], "first"),
    ("Distinct tickers | **", ["honest_n", "tickers"], "first"),
    ("Severe (h21 excess ≤ −0.07 OR mae ≤ −0.07) | **", ["honest_n", "severe"], "first"),
    ("Target (excess_h21 ≥ +0.07 and not SEVERE) | **", ["honest_n", "target"], "first"),
    ("Neither | **", ["honest_n", "neither"], "first"),
    ("OOS AUC (primary) | **", ["entry_model", "oos_auc"], "first"),
    ("In-sample AUC", ["entry_model", "in_sample_auc"], "first"),
    ("n_oos episodes", ["entry_model", "n_oos"], "first"),
    ("n_test_weeks | **", ["entry_model", "n_test_weeks"], "first"),
    ("Sensitivity OOS AUC (22-cal-day, NOT binding)", ["entry_model", "sensitivity", "oos_auc"], "first"),
    ("Sensitivity n_oos", ["entry_model", "sensitivity", "n_oos"], "first"),
    ("Sensitivity n_test_weeks", ["entry_model", "sensitivity", "n_test_weeks"], "first"),
    ("Removed by binding rule vs old -21-session rule", ["entry_model", "n_removed_strict"], "first"),
    # P2: h1/h2/h3 HEIGHTS (bold), not n_h1
    ("h1 (≤ 5)", ["hazard", "overall", "h1", "0"], "bold"),
    ("h2 (6–10 \\| not severe by 5)", ["hazard", "overall", "h2", "0"], "bold"),
    ("h3 (11–21 \\| not severe by 10)", ["hazard", "overall", "h3", "0"], "bold"),
    ("Counts: deteriorated", ["attribution", "overall", "n_det"], "first"),
    ("EXPIRED |", ["prophet_ledger", "by_outcome", "EXPIRED", "n"], "first"),
    ("INVALIDATED |", ["prophet_ledger", "by_outcome", "INVALIDATED", "n"], "first"),
    ("T1_HIT |", ["prophet_ledger", "by_outcome", "T1_HIT", "n"], "first"),
    ("T2_HIT |", ["prophet_ledger", "by_outcome", "T2_HIT", "n"], "first"),
    ("NO_ENTRY |", ["prophet_ledger", "by_outcome", "NO_ENTRY", "n"], "first"),
]


def check_files(rj_path: Path, rmd_path: Path) -> tuple[list, int, str]:
    """Compare RESULT.md labelled numbers to result.json. Never raises on
    schema surprises: a scalar h1 is recorded as a mismatch."""
    mismatches: list[dict] = []
    checked = 0
    payload = json.loads(Path(rj_path).read_text())
    md_text = Path(rmd_path).read_text()

    for label, key_path, kind in LABELED_CHECKS:
        val, ok_drill = _drill(payload, key_path)
        if kind == "bold":
            md_val = _bold_number_in_row(md_text, label)
        else:
            md_val = _find_number_after(md_text, label)
        checked += 1
        if not ok_drill:
            mismatches.append({
                "label": label,
                "key": ".".join(key_path),
                "md_val": md_val,
                "rj_val": val,
                "reason": "schema violation: key path did not resolve to a number",
            })
            continue
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            mismatches.append({
                "label": label,
                "key": ".".join(key_path),
                "md_val": md_val,
                "rj_val": val,
                "reason": "schema violation: expected numeric leaf",
            })
            continue
        if md_val is None:
            mismatches.append({
                "label": label,
                "key": ".".join(key_path),
                "md_val": None,
                "rj_val": val,
                "reason": "label not found in RESULT.md",
            })
            continue
        if not _close(md_val, val):
            mismatches.append({
                "label": label,
                "key": ".".join(key_path),
                "md_val": md_val,
                "rj_val": val,
            })

    # P2: BOTH bounds of every `95% week-cluster CI | [lo, hi]` cell
    auc_ci = payload.get("entry_model", {}).get("oos_auc_ci")
    pairs = _all_bracket_pairs_after_label(md_text, "95% week-cluster CI | [")
    if not pairs:
        mismatches.append({
            "label": "95% week-cluster CI | [",
            "key": "entry_model.oos_auc_ci",
            "md_val": None,
            "rj_val": auc_ci,
            "reason": "CI cell not found",
        })
        checked += 1
    else:
        lo, hi = pairs[0]
        checked += 2
        if not (isinstance(auc_ci, (list, tuple)) and len(auc_ci) >= 2):
            mismatches.append({
                "label": "95% week-cluster CI | [",
                "key": "entry_model.oos_auc_ci",
                "md_val": (lo, hi),
                "rj_val": auc_ci,
                "reason": "schema violation: oos_auc_ci is not a pair",
            })
        else:
            if not _close(lo, auc_ci[0]):
                mismatches.append({
                    "label": "oos_auc_ci[0]",
                    "key": "entry_model.oos_auc_ci[0]",
                    "md_val": lo,
                    "rj_val": auc_ci[0],
                })
            if not _close(hi, auc_ci[1]):
                mismatches.append({
                    "label": "oos_auc_ci[1]",
                    "key": "entry_model.oos_auc_ci[1]",
                    "md_val": hi,
                    "rj_val": auc_ci[1],
                })

    # Sensitivity CI both bounds
    sens = payload.get("entry_model", {}).get("sensitivity", {})
    sens_ci = sens.get("oos_auc_ci")
    sens_pair = _bracket_pair_after(md_text, "Sensitivity 95% CI | [")
    if sens_pair is not None:
        checked += 2
        slo, shi = sens_pair
        if not (isinstance(sens_ci, (list, tuple)) and len(sens_ci) >= 2):
            mismatches.append({
                "label": "Sensitivity 95% CI",
                "key": "entry_model.sensitivity.oos_auc_ci",
                "md_val": sens_pair,
                "rj_val": sens_ci,
                "reason": "schema violation",
            })
        else:
            if not _close(slo, sens_ci[0]):
                mismatches.append({
                    "label": "sensitivity.oos_auc_ci[0]",
                    "md_val": slo,
                    "rj_val": sens_ci[0],
                })
            if not _close(shi, sens_ci[1]):
                mismatches.append({
                    "label": "sensitivity.oos_auc_ci[1]",
                    "md_val": shi,
                    "rj_val": sens_ci[1],
                })

    # Attribution overall CIs (both bounds)
    attr = payload.get("attribution", {}).get("overall", {})
    for md_lab, key in [
        ("deteriorated after non-negative H10 (excess_h10 ≥ 0) | **",
         "deteriorated_after_nonneg_h10"),
        ("immediate failure (excess_h5 < 0 AND excess_h10 < 0) | **",
         "immediate_failure"),
    ]:
        vec = attr.get(key)
        pair = _bracket_pair_after(md_text, md_lab)
        if pair is None:
            continue
        checked += 2
        if not (isinstance(vec, (list, tuple)) and len(vec) >= 3):
            mismatches.append({
                "label": md_lab,
                "key": f"attribution.overall.{key}",
                "md_val": pair,
                "rj_val": vec,
                "reason": "schema violation: expected [share, lo, hi]",
            })
            continue
        if vec[1] is None:
            continue
        lo, hi = pair
        if not _close(lo, vec[1]) or not _close(hi, vec[2]):
            mismatches.append({
                "label": f"{key}_ci",
                "md_val": pair,
                "rj_val": vec[1:],
            })

    # P2: every hazard height AND both CI bounds; scalar h1 → mismatch, no crash
    haz_overall = payload.get("hazard", {}).get("overall", {})
    haz_labels = {
        "h1": "h1 (≤ 5)",
        "h2": "h2 (6–10",
        "h3": "h3 (11–21",
    }
    for key, lab in haz_labels.items():
        v = haz_overall.get(key)
        checked += 1
        if not (isinstance(v, (list, tuple)) and len(v) >= 1):
            mismatches.append({
                "label": lab,
                "key": f"hazard.overall.{key}",
                "md_val": _bold_number_in_row(md_text, lab),
                "rj_val": v,
                "reason": "schema violation: expected [height, lo, hi]",
            })
            continue
        md_h = _bold_number_in_row(md_text, lab)
        if md_h is None or not _close(md_h, v[0]):
            mismatches.append({
                "label": f"hazard.{key}[0]",
                "key": f"hazard.overall.{key}[0]",
                "md_val": md_h,
                "rj_val": v[0] if isinstance(v, (list, tuple)) and len(v) else v,
            })
        # CI bounds when present
        if not (isinstance(v, (list, tuple)) and len(v) >= 3):
            mismatches.append({
                "label": f"hazard.{key} ci",
                "key": f"hazard.overall.{key}",
                "md_val": None,
                "rj_val": v,
                "reason": "schema violation: expected [height, lo, hi]",
            })
            checked += 1
            continue
        if v[1] is None:
            continue
        pair = _bracket_pair_after(md_text, lab)
        if pair is None:
            continue
        checked += 2
        lo, hi = pair
        if not _close(lo, v[1]) or not _close(hi, v[2]):
            mismatches.append({
                "label": f"hazard.{key}_ci",
                "md_val": pair,
                "rj_val": v[1:],
            })

    # Bootstrap pct
    boot = payload.get("entry_model", {}).get("bootstrap", {})
    if boot.get("n_draws_valid"):
        pct = 100.0 * boot.get("n_draws_ge_065", 0) / boot["n_draws_valid"]
        m = re.search(r"([+\-]?\d+\.\d+)% of the \d+ bootstrap draws", md_text)
        if m:
            md_pct = float(m.group(1))
            checked += 1
            if abs(md_pct - pct) >= 0.05:
                mismatches.append({
                    "label": "bootstrap_pct",
                    "md_val": md_pct,
                    "rj_val": pct,
                })

    n_mis = len(mismatches)
    if n_mis:
        msg = f"check_result_md: {n_mis}/{checked} mismatches"
    else:
        msg = f"check_result_md: 0/{checked} mismatches (all {checked} labeled numbers present)"
    return mismatches, checked, msg


def run_specified_mutations(results_dir: Path | None = None) -> dict:
    """P2 battery: scratch copies of {RESULT.md, result.json, check_result_md.py}.

    Cases:
      clean
      RESULT.md 0.6227→0.9999
      RESULT.md 0.6738→0.1111
      result.json oos_auc→0.8123
      result.json hazard.overall.h1[0]→0.9
      result.json hazard.overall.h1 scalar 0.9
    """
    results_dir = Path(results_dir) if results_dir else RESULTS_DIR
    src_rj = (results_dir / "result.json").read_text()
    src_md = (results_dir / "RESULT.md").read_text()
    src_ck = Path(__file__).resolve()

    def _run_pair(rj_text: str, md_text: str) -> dict:
        with tempfile.TemporaryDirectory(prefix="f1_checker_") as td:
            td = Path(td)
            code = td / "code"
            code.mkdir()
            (td / "result.json").write_text(rj_text)
            (td / "RESULT.md").write_text(md_text)
            shutil.copy(src_ck, code / "check_result_md.py")
            r = subprocess.run(
                [sys.executable, str(code / "check_result_md.py")],
                capture_output=True, text=True, timeout=60,
            )
            text = (r.stdout or "") + (r.stderr or "")
            n_mis = None
            m = re.search(r"check_result_md: (\d+)/(\d+) mismatches", text)
            if m:
                n_mis = int(m.group(1))
                n_chk = int(m.group(2))
            else:
                n_chk = None
            return {
                "returncode": r.returncode,
                "output": text.strip(),
                "n_mismatch": n_mis,
                "n_checked": n_chk,
            }

    out = {}
    out["clean"] = _run_pair(src_rj, src_md)

    out["md_auc_09999"] = _run_pair(src_rj, src_md.replace("0.6227", "0.9999"))
    out["md_cihi_01111"] = _run_pair(src_rj, src_md.replace("0.6738", "0.1111"))

    d = json.loads(src_rj)
    d["entry_model"]["oos_auc"] = 0.8123
    out["rj_auc_08123"] = _run_pair(json.dumps(d, indent=2, default=str), src_md)

    d = json.loads(src_rj)
    d["hazard"]["overall"]["h1"][0] = 0.9
    out["rj_h1_09"] = _run_pair(json.dumps(d, indent=2, default=str), src_md)

    d = json.loads(src_rj)
    d["hazard"]["overall"]["h1"] = 0.9  # scalar schema violation
    out["rj_h1_scalar"] = _run_pair(json.dumps(d, indent=2, default=str), src_md)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--md", dest="md_path", default=None)
    args = parser.parse_args(argv)
    rj_path = Path(args.json_path) if args.json_path else RESULTS_DIR / "result.json"
    rmd_path = Path(args.md_path) if args.md_path else RESULTS_DIR / "RESULT.md"
    if not rj_path.exists() or not rmd_path.exists():
        print(f"missing input: rj={rj_path.exists()} rmd={rmd_path.exists()}",
              file=sys.stderr)
        return 1
    try:
        mismatches, checked, msg = check_files(rj_path, rmd_path)
    except Exception as e:
        # Last-resort: never crash the scalar-h1 case with a traceback.
        print(f"check_result_md: 1/0 mismatches (exception: {type(e).__name__}: {e})",
              file=sys.stderr)
        return 1
    if mismatches:
        print(msg, file=sys.stderr)
        for m in mismatches[:20]:
            print(f"  {m}", file=sys.stderr)
        return 1
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
