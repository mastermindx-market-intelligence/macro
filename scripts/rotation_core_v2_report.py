"""Markdown for the v2 selection-window results. Every number is labelled selection-window, not evidence."""


def _p(x, nd=2):
    return "n/a" if x is None else f"{100 * x:+.{nd}f}%"


def _ci(c):
    return "n/a" if not c else f"[{100 * c[0]:+.2f}, {100 * c[1]:+.2f}]"


def _row(name, st):
    mc = st["vs_matched_mix"]
    return (f"| {name} | {_p(mc['observed'])} {_ci(mc['ci95'])} p={mc['p_one_sided_centred']:.3f} | "
            f"{_p(st['vs_SPY']['ann'])} | {_p(st['vs_RSP_or_stated_EW_proxy_before_2003_05']['ann'])} | "
            f"{_p(st['vs_BASE_equal_weight_industries']['ann'])} | {_p(st['max_drawdown'], 1)} vs {_p(st['max_drawdown_matched_mix'], 1)} | "
            f"{st['turnover_one_way_per_year']:.2f} | {_p(st['costs_per_year'])} | "
            f"{st['false_DEFEND_calls_per_calm_year']:.2f} |")


def write_selection_md(res, path):
    L = ["# Rotation Core v2 — SELECTION WINDOW results (1998-01-02 → 2019-12-31)", "",
         f"**Label: selection-window, not evidence.** This window was previously examined (v1, Pro run B; disclosed in the "
         f"frozen header `{res['header_sha256'][:12]}…`). These numbers choose the grid point and nothing else. "
         f"{res['warmup_note']}. Annualised differences; 95% stationary-bootstrap intervals (block 21, B = 10,000) on "
         "the matched-mix contrast, whose mix is rebuilt inside every resample. Industry portfolios are not tradable.", "",
         "| Book | vs exposure-matched mix (after-the-fact attribution yardstick, not holdable; binding contrast) | vs SPY | vs RSP (EW proxy before 2003-05) | vs BASE (EW industries) | MaxDD vs mix | One-way turnover/yr | Costs/yr (10 bp) | False DEFEND calls / calm yr |",
         "|---|---|---|---|---|---|---|---|---|"]
    for k, v in res["settings"].items():
        L.append(_row(f"H1 {k}", v["H1"]))
        L.append(_row(f"price-only {k}", v["price_only_control"]))
        L.append(_row(f"cash ablation {k}", v["cash_ablation"]))
    L.append(_row("H3 (R5 on beta legs)", res["H3"]))
    L += ["", "| Setting | H1 vs matched mix at 2× costs | Costs/yr at 2× | H2: H1 − price-only (paired) | H1 state share N / D / A |",
          "|---|---|---|---|---|"]
    for k, v in res["settings"].items():
        x = v["H1_at_2x_costs"]; h2 = v["H2_paired_H1_minus_price_only"]; sh = v["H1"]["share"]
        L.append(f"| {k} | {_p(x['vs_matched_mix']['observed'])} {_ci(x['vs_matched_mix']['ci95'])} | {_p(x['costs_per_year'])} | "
                 f"{_p(h2['ann'])} {_ci(h2['ci95'])} p={h2['p_one_sided_centred']:.3f} | {sh['NEUTRAL']:.0%} / {sh['DEFEND']:.0%} / {sh['ATTACK']:.0%} |")
    sel = res["selection"]
    L += ["", f"**Selected setting: `{sel['selected']}`** ({sel['rule']}). {sel['inherit']}.",
          "Observed H1 excess over matched mix by setting (selection-window): " +
          ", ".join(f"{k} {_p(v)}" for k, v in sel["observed_by_setting"].items()), "",
          f"Named episodes used for false-call counts: {', '.join(res['episodes'])}. Dropped industry-days (no imputation; "
          f"eligible industries only, not the header's 366 scope): {res['dropped_industry_days']}.", ""]
    open(path, "w").write("\n".join(L) + "\n")


def write_final_md(res, path):
    """Final conjunction (stage 2). Verdicts first; the 2020-2025 standalone estimate is the effect size; pooled
    figures are labelled conditional on the gate."""
    L = ["# Rotation Core v2 — FINAL CONJUNCTION (historical tier)", "", res["label"], "",
         "| Hypothesis | Verdict | Failed legs | Fund veto fired |", "|---|---|---|---|"]
    for h, v in res["verdicts"].items():
        L.append(f"| {h} | {v['verdict']} | {len(v['failed_legs'])} of {v['legs_total']} | {v['fund_veto_fired']} |")
    st = res["standalone_2020_2025_OUT_OF_SAMPLE_EFFECT_SIZE"]["block21"]
    L += ["", "## 2020–2025 standalone (out-of-sample effect size; block 21; one-sided centred p governs)", "",
          "| Reading / cost run / hypothesis | Annualised | 95% interval | p one-sided | p two-sided (labelled, not governing) |",
          "|---|---|---|---|---|"]
    for k, x in st.items():
        L.append(f"| {k} | {_p(x['observed_ann'])} | {_ci(x['ci95_ann'])} | {x['p_one_sided_centred']:.4f} | "
                 f"{x['p_two_sided_centred_LABELLED_NOT_GOVERNING']:.4f} |")
    L += ["", "## Pooled pre-1998 + 2020–2025 (conditional on the pre-1998 gate, not an unbiased effect size)", "",
          "| Block | Reading / cost / convention | Hypothesis | Annualised | p one-sided | Holm p | Rejected |", "|---|---|---|---|---|---|---|"]
    for blk, d in res["pooled_CONDITIONAL_ON_GATE"].items():
        for key, hy in d.items():
            for h, x in hy.items():
                hm = res["holm_m3"][blk][key][h]
                L.append(f"| {blk}{' (sensitivity)' if blk != 'block21' else ''} | {key} | {h} | "
                         f"{_p(x['observed_ann_CONDITIONAL_ON_GATE'])} | {x['p_one_sided_centred']:.4f} | "
                         f"{hm['p_holm']:.4f} | {hm['reject_h0']} |")
    w = res.get("witnessed")
    if w:
        L += ["", f"Witnessed outside this repository (R22.3): start/release commit {w.get('start_commit')}, gate commit "
                  f"{w.get('gate_commit')}; acknowledged {w.get('acknowledged_at')}."]
    L += ["", res["descriptive_only"], "", res["data_provenance"], "", res["reporting_rule_i"], "", res["independence"], ""]
    open(path, "w").write("\n".join(L) + "\n")
