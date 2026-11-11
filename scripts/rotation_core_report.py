"""Build the Rotation Core Stage-D artifact (schema rotation_core.evaluation/v1) and its Markdown report."""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _git(*a):
    return subprocess.check_output(["git", "-C", str(ROOT), *a]).decode().strip()


def pct(x, nd=2):
    return "n/a" if x is None else f"{100 * x:+.{nd}f}%"


def num(x, nd=2):
    return "n/a" if x is None else f"{x:.{nd}f}"


def ci(c, scale=100, nd=2):
    return "n/a" if not c else f"[{c[0] * scale:+.{nd}f}, {c[1] * scale:+.{nd}f}]"


def build_artifact(res: dict, header: dict, hashes: dict, pin: str, B: int, seed: int) -> dict:
    jobs = res["jobs"]
    dq = res.get("data_quality", {})
    src_ok = dq.get("l0_ge_99pct")
    lvl0 = "L0_descriptive" if src_ok is True else ("L0_NOT_MET_source_coverage" if src_ok is False
                                                    else "L0_UNVERIFIED_source_coverage")
    release = {"overall_level": lvl0, "l0_source_check": {"l0_ge_99pct": src_ok,
                                                          "rule": "header L0: >= 99% of sessions priced for the job's instruments"}, "levels_defined": ["L0_descriptive", "L1_accepted_historical",
                                                                     "L2_prospective_shadow"],
               "stage": "D", "cap_rule": "No configuration can reach L1 in Stage D: G4 (hold-out) is sealed by the "
                                         "parent's access ruling. Incumbents and J4 are capped at L0 regardless.",
               "jobs": {}}
    for j in ("J1", "J2", "J3"):
        g = jobs[j]["gates"]
        release["jobs"][j] = {"level": lvl0,
                              "candidates_clearing_G1_G2_G3_G5_on_D": [c for c, v in g.items() if v["clears_G1_G2_G3_G5_on_D"]],
                              "criteria": g}
    release["jobs"]["J4"] = {"level": lvl0, "criteria": jobs["J4"].get("gates"),
                             "cap": jobs["J4"].get("cap", jobs["J4"].get("reason"))}
    release["jobs"]["J5"] = {"level": lvl0, "note": "confirmatory on H only; D descriptive"}
    limitations = [
        "Stage D only: every number covers the development window; the hold-out (2020-01-02 onward) is sealed and was not computed.",
        "Adjusted closes are today's restatement of dividends and splits, not as-published prices.",
        "About six named stress episodes fall in D; per-episode pivot results are descriptions, not statistics.",
        "A null here usually means 'not detectable with this sample' - read each contrast's power line.",
        "J4 uses survivor-heavy Yahoo prices; members without prices are excluded and counted (priced share < 85%).",
        "Incumbent models were designed on this history; their results are in-sample replications (L0).",
        "Long-history tier is index-level (Ken French market, ^GSPC), with no tradable instrument; descriptive only.",
        "Nothing here is a call, forecast, ranking, gate, size or trade.",
    ]
    return {
        "schema": "rotation_core.evaluation/v1", "view": "STRATEGY_EVALUATION_VIEW",
        "protocol_ref": "research/rotation_core/protocol_header_v1.json",
        "protocol": {"id": header["protocol_id"], "header_sha256": "af2a09886132bb784535e21134b63c2c86c579e186c248b20bb617fc77580f32",
                     "header_commit": "623f0a4623", "frozen_on": header["frozen_on_utc"]},
        "code": {"commit": _git("rev-parse", "HEAD"), "harness_dirty": bool(_git("status", "--porcelain", "--",
                                                                                 "engine/rotation_core_evaluation.py",
                                                                                 "engine/rotation_core_j4.py",
                                                                                 "scripts/run_rotation_core_v1.py",
                                                                                 "scripts/rotation_core_report.py")),
                 "module": ["engine/rotation_core_evaluation.py", "engine/rotation_core_j4.py"],
                 "runner": "scripts/run_rotation_core_v1.py --stage D",
                 "bootstrap": {"B": B, "seed": seed, "mean_block_sessions": 21, "j4_mean_block_months": 3}},
        "data_clocks": {"macro_data_commit": pin, "inputs_sha256": hashes, "last_close_used": "2019-12-31",
                        "computed_at": datetime.now(timezone.utc).isoformat()},
        "stage": "D", "window_rule": "returns dated <= 2019-12-31; J4 formations <= 2015-12",
        "may_rank": False, "may_gate": False, "may_size": False, "may_trade": False, "may_escalate": False,
        "release": release, "limitations": limitations, "jobs": jobs, "incumbents": res["incumbents"],
        "long_history": res["long_history"], "data_quality": res["data_quality"],
        "dsr_trial_count": res["dsr_trial_count"], "deviations": res["deviations"],
    }


def _fam_table(fam, effect_label):
    lines = ["| Test | Observed | 95% CI | p (raw) | p (Holm) | E1 / E2 | SE | MDE80 (Holm) | Detectable? |",
             "|---|---|---|---|---|---|---|---|---|"]
    for tid, r in fam.items():
        sh = r["kind"] == "sharpe"
        f = (lambda x: num(x, 3)) if sh else (lambda x: pct(x))
        c = ("n/a" if not r["ci95"] else f"[{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}]") if sh else ci(r["ci95"])
        e = r["eras"]
        p = r["power"]
        lines.append(f"| {tid} | {f(r['observed'])} | {c} | {r['p_one_sided_centred']:.4f} | {r['holm']['p_holm']:.4f} | "
                     f"{f(e['E1'])} / {f(e['E2'])} | {f(p['se']) if not sh else num(p['se'], 3)} | "
                     f"{f(p['mde80_holm']) if not sh else num(p['mde80_holm'], 3)} | "
                     f"{'yes' if p['mde80_holm'] <= p['reference_effect'] else 'no'} |")
    return lines


def _metrics_table(met, keys=None):
    lines = ["| Book | CAGR | Vol | Sharpe | MaxDD | Up / Down cap. | Beta | Mean weight | Traded/yr | Costs/yr | DSR |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in keys or met:
        m = met[k]
        dsr = m.get("dsr") or {}
        lines.append(f"| {k} | {pct(m['ann_return'])} | {pct(m['ann_vol'], 1)} | {num(m['sharpe'])} | {pct(m['max_drawdown'], 1)} | "
                     f"{num(m['up_capture_monthly'])} / {num(m['down_capture_monthly'])} | {num(m['beta_vs_spy'])} | "
                     f"{num(m['mean_risky_weight'])} | {num(m['traded_notional_per_year'])} | {pct(m['costs_paid_per_year'], 2)} | "
                     f"{num(dsr.get('dsr'), 3)} |")
    return lines


def _gate_line(c, g):
    marks = []
    for row in g["criteria"]:
        nm = row["criterion"].split(" ")[0]
        mt = row["met"]
        marks.append(f"{nm}:{'✓' if mt is True else ('·' if isinstance(mt, str) else '✗')}")
    return f"| {c} | " + " ".join(marks) + f" | {'yes' if g['clears_G1_G2_G3_G5_on_D'] else 'no'} |"


def _pivot_lines(piv, books):
    out = []
    for b in books:
        if b not in piv:
            continue
        p = piv[b]
        parts = []
        for ep, row in p["episodes"].items():
            if row.get("status") == "outside_window":
                continue
            if row.get("exit") == "missed":
                parts.append(f"{ep}: never out (strategy {pct(row['strategy_return_peak_to_trough'], 0)} vs market "
                             f"{pct(row['market_drawdown'], 0)})")
                continue
            lead = row["exit_lead_sessions"]
            when = (f"{-lead} sessions after the top" if lead < 0 else f"{lead} sessions before the top")
            lost = pct(row.get("lost_before_exit", 0.0), 0)
            if row.get("reentry"):
                lag = row["reentry_lag_sessions"]
                back = (f"back {lag} sessions after the bottom, missing {pct(row['missed_after_trough'], 0)}"
                        if lag >= 0 else f"back {-lag} sessions before the bottom")
            else:
                back = "not back in by the end of D"
            parts.append(f"{ep}: out {when}{'' if lead >= 0 else ' having lost ' + lost}; {back}")
        out.append(f"- **{b}** — " + "; ".join(parts) +
                   f". Calm-period false pivots: {num(p['false_pivots_per_calm_year'])}/calm-yr, cost "
                   f"{pct(p['false_pivot_cost_per_calm_year'])}/calm-yr.")
    return out


def write_markdown(art: dict, path: Path) -> None:
    J = art["jobs"]
    L = ["# Rotation Core — Stage D results (development window only; hold-out sealed)", "",
         f"Header `{art['protocol']['header_sha256'][:12]}…` (commit {art['protocol']['header_commit']}); code "
         f"`{art['code']['commit'][:10]}`; computed {art['data_clocks']['computed_at'][:19]}Z. Schema `{art['schema']}`. "
         "All `may_*` flags are false. Every number is a fraction unless marked; intervals are 95% stationary-bootstrap.",
         "", "**Release:** every job is **L0 descriptive** in Stage D (G4 sealed). "
         "Candidates clearing G1, G2, G3 and G5 on D are listed per job; that is the parent's stated condition for opening H.", ""]
    for j, title, keyorder in (("J1", "J1 — market risk state (SPY vs cash)", None),
                               ("J2", "J2 — sector rotation (SPDRs)", None),
                               ("J3", "J3 — cross-asset rotation", None)):
        jj = J[j]
        L += [f"## {title}", "", f"Window D: {jj['window_D'][0]} → {jj['window_D'][1]}.", ""]
        L += _metrics_table(jj["metrics"])
        fam = jj.get("family_F1") or jj.get("family_F2") or jj.get("family_F3")
        L += ["", "Confirmatory family (Holm within family):", ""] + _fam_table(fam, "")
        L += ["", "| Candidate | Gates (✓ met, ✗ not, · not evaluated) | Clears G1+G2+G3+G5 on D |", "|---|---|---|"]
        L += [_gate_line(c, g) for c, g in jj["gates"].items()]
        L += [""] + [f"- {r['contrast']}: {r['power']['sentence']}." for r in fam.values()] + [""]
        if j in ("J1", "J3") and jj.get("posthoc_vs_spy_rsp"):
            L += ["### Post-hoc descriptive: vs SPY and RSP, full period vs stress episodes (not a header comparator; no test)", "",
                  "| Book | Bench | Window | CAGR (bench) | Sharpe (bench) | MaxDD (bench) | Up/Down cap. full | Stress capture pooled | Up cap. outside stress |",
                  "|---|---|---|---|---|---|---|---|---|"]
            for bn, rows in jj["posthoc_vs_spy_rsp"].items():
                for c, r in rows.items():
                    L.append(f"| {c} | {bn} | {r['window'][0]}→{r['window'][1]} | {pct(r['ann_return'])} ({pct(r['bench_ann_return'])}) | "
                             f"{num(r['sharpe'])} ({num(r['bench_sharpe'])}) | {pct(r['max_drawdown'], 1)} ({pct(r['bench_max_drawdown'], 1)}) | "
                             f"{num(r['up_capture_full'])}/{num(r['down_capture_full'])} | {num(r['stress_capture_pooled'])} | "
                             f"{num(r['up_capture_outside_stress'])} |")
            L.append("")
        if j == "J1":
            L += ["### Pivot table (D episodes; 2020, 2022, 2025, 2026 sealed in H)", ""]
            L += _pivot_lines(jj["pivots"], ["B1", "B3", "B4", "J1-A", "J1-B", "J1-C", "J1-D", "J1-E", "J1-I1", "J1-I2"])
            L += ["", f"J1* selected on D: **{jj['selection']['J1_star']}** (P1 observed: "
                  + ", ".join(f"{k} {pct(v)}" for k, v in jj["selection"]["p1_observed_D"].items()) + ")", ""]
        if j == "J2":
            L += ["### Episode holdings (D episodes)", ""]
            for ep, h in jj["episode_holdings_D"].items():
                L.append(f"- **{ep}** (peak {h['peak']}, trough {h['trough']}): SPY {pct(h['spy_return'], 1)}, "
                         f"XLP/XLU/XLV {pct(h['defensive_trio_return'], 1)} (trio − SPY {pct(h['trio_minus_spy'], 1)}).")
                for b in ("B5", "B6", "B7", "J2-A", "J2-B", "J2-C", "J2-D", "J2-I1", "J2-E", "J5-A"):
                    if b in h["books"]:
                        bb = h["books"][b]
                        L.append(f"  - {b}: at peak {bb['held_at_peak']}; at trough {bb['held_at_trough']}")
            L += ["", f"J2* selected on D: **{jj['selection']['J2_star']}**.", ""]
    j4 = J["J4"]
    L += ["## J4 — amplification (L0 cap)", ""]
    if j4.get("status") == "evaluated":
        L += [f"Formations {j4['formations_D'][0]} → {j4['formations_D'][1]}; price sources {j4['price_sources']}.",
              f"- J4-A Δ (leading − lagging selection spread): {pct(j4['J4-A']['observed'])}/yr, CI {ci(j4['J4-A']['ci95'])}, "
              f"p {j4['J4-A']['p_one_sided_centred']:.4f}, Holm {j4['J4-A']['holm']['p_holm']:.4f}; E1/E2 "
              f"{pct(j4['J4-A']['eras']['E1'])} / {pct(j4['J4-A']['eras']['E2'])}. {j4['J4-A']['power']['sentence']}.",
              f"- J4-B book excess: {pct(j4['J4-B']['observed'])}/yr, CI {ci(j4['J4-B']['ci95'])}, Holm {j4['J4-B']['holm']['p_holm']:.4f}; "
              f"at 2× costs {pct(j4['J4-B_cost_2x_ann'])}.",
              f"- Treatments: {j4['treatments']}; GICS-assignment sensitivity {j4['sensitivity_gics_assignment']}.",
              f"- Priced share by year: " + ", ".join(f"{y}: {v['priced_share']:.0%}" for y, v in j4["coverage_by_year"].items()), ""]
    else:
        L += [f"Unavailable: {j4.get('reason')}", ""]
    J5 = J["J5"]
    L += ["## J5 / J2-E (descriptive in D; J1*/J2* were selected on D, so these D numbers are in-sample)", "",
          f"J1* = {J5['J1_star']}, J2* = {J5['J2_star']}. Point differences in D: "
          + ", ".join(f"{k} {pct(v)}" for k, v in J5["point_differences_D"].items()), ""]
    L += _metrics_table(J5["metrics"])
    L += ["", "## Incumbents (replication only, L0)", ""]
    for tid, r in art["incumbents"]["family_FI"].items():
        if r.get("status") == "unavailable":
            L.append(f"- {tid}: unavailable (enters Holm at p=1)")
            continue
        sh = r["kind"] == "sharpe"
        L.append(f"- {tid}: {num(r['observed'], 3) if sh else pct(r['observed'])}, Holm p {r['holm']['p_holm']:.4f}")
    L.append(f"- Availability: {art['incumbents']['J1']}; J2-I1 {art['incumbents']['J2-I1']}")
    L += ["", "## Long-history descriptive tier (index-level, L0)", ""]
    for tier, t in art["long_history"]["tiers"].items():
        L += [f"### {tier} (from {t['first_decision']})", ""] + _metrics_table(t["metrics"]) + [""]
        L += _pivot_lines(t["pivots"], list(t["metrics"])) + [""]
    L += ["## Deviations", ""] + [f"- [{d['kind']}] {d['text']}" for d in art["deviations"]]
    L += ["", "## Limitations", ""] + [f"- {x}" for x in art["limitations"]]
    path.write_text("\n".join(L) + "\n")
