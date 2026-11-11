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
          f"Named episodes used for false-call counts: {', '.join(res['episodes'])}. Dropped industry-days (no imputation): {res['dropped_industry_days']}.", ""]
    open(path, "w").write("\n".join(L) + "\n")


def write_stage1_md(res, path):
    L = ["# Rotation Core v2 — STAGE 1 (pre-1998 confirmation window, R13)", "",
         f"{res['label']} Window {res['window'][0]} → {res['window'][1]}; selected setting {res['selected_setting']}; header "
         f"`{res['header_sha256'][:12]}…`. Industry portfolios, not tradable. The exposure-matched mix is an after-the-fact attribution yardstick, not holdable; SPY (French market), RSP (EW proxy) and equal-weight industries are the holdable yardsticks. Dropped industry-days (no imputation): "
         f"{res['dropped_industry_days']}.", "",
         "| Book | vs matched mix, full | E1 1928–45 | E2 1946–97 | vs French market | vs EW proxy | vs BASE | MaxDD vs mix | Turnover | Costs/yr | False DEFEND / calm yr |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, key in (("H1", "H1"), ("H1 at 2× costs", "H1_at_2x_costs"), ("price-only control", "price_only_control"),
                      ("H3", "H3"), ("H3 at 2× costs", "H3_at_2x_costs"), ("cash ablation", "cash_ablation")):
        x = res[key]; mc = x["vs_matched_mix"]
        L.append(f"| {name} | {_p(mc['observed'])} {_ci(mc['ci95'])} | {_p(x['eras']['E1_1928_1945']['observed'])} | "
                 f"{_p(x['eras']['E2_1946_1997']['observed'])} | {_p(x['vs_French_market_(SPY_yardstick)']['ann'])} | "
                 f"{_p(x['vs_EW_proxy_(RSP_yardstick)']['ann'])} | {_p(x['vs_BASE_equal_weight_industries']['ann'])} | "
                 f"{_p(x['max_drawdown'], 1)} vs {_p(x['max_drawdown_matched_mix'], 1)} | {x['turnover_one_way_per_year']:.2f} | "
                 f"{_p(x['costs_per_year'])} | {x['false_DEFEND_calls_per_calm_year']:.2f} |")
    h2 = res["H2_paired_H1_minus_price_only"]
    L += ["", f"H2 (H1 − price-only, paired): full {_p(h2['full']['ann'])} {_ci(h2['full']['ci95'])}; "
          f"E1 {_p(h2['E1_1928_1945']['ann'])}; E2 {_p(h2['E2_1946_1997']['ann'])}.", "",
          f"**R13 opening condition (H1 or H3 positive over its matched mix in both eras):** "
          f"{res['opening_condition_H1_or_H3_positive_in_both_eras']}. No pooled Holm p at this stage.", ""]
    open(path, "w").write("\n".join(L) + "\n")
