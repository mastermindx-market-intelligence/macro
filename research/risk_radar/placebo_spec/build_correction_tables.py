"""Build the regenerated placebo tables (Rule A) beside the published pre-repair figures.

Reads only committed JSON: the three published placebo blocks in research/risk_radar/walkforward/
and PLACEBO_RESCORE_RULE_A_v1.json. No outcome is joined here; nothing is re-run.
Usage: python3 build_correction_tables.py > PLACEBO_CORRECTION_TABLES_RULE_A.md
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
W = HERE.parent / "walkforward"
R = json.loads((HERE / "PLACEBO_RESCORE_RULE_A_v1.json").read_text())["reads"]
PUB = {
    "WALKFORWARD_SCORECARD_OOS_v1 §3": (json.loads((W / "WALKFORWARD_SCORECARD_OOS_v1.json").read_text()), "oos"),
    "SCORECARD_INSAMPLE §6 (INSAMPLE_READS_LAG1_v2)": (json.loads((W / "INSAMPLE_READS_LAG1_v2.json").read_text())["placebo"], "flat"),
    "PIVOT_SCORECARD_INSAMPLE Placebo (PIVOT_PLACEBO_INSAMPLE_v2)": (json.loads((W / "PIVOT_PLACEBO_INSAMPLE_v2.json").read_text()), "flat"),
}


def find_oos(pub):
    def walk(o):
        if isinstance(o, dict):
            if "walkforward_loud" in o and "n_draws" in o:
                return o["walkforward_loud"]
            for v in o.values():
                r = walk(v)
                if r is not None:
                    return r
    return walk(pub)


def f(x, nd=3):
    return "—" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def main():
    out = ["# Placebo tables regenerated under Rule A (correction line, not a new read)", "",
           "Rule: PLACEBO_PLACEMENT_SPEC_v1 Rule A, cap 10·n_draws (Amendment 1, co-signed). Old = the published",
           "pre-repair figure; each was reproduced from the defective module before the Rule A run",
           "(`rescore_rule_a.py`). Same inputs, seeds, windows and draws; only the placement changed. The chance",
           "account is unchanged. Fold decisions, \"retains default\" and \"inconclusive\" never used the placebo.", "",
           "Pivot-table HY rows: the published JSON predates the HY release-rule lag fix (bb856951), so the old",
           "figure is not reproducible on today's input; the Rule A figure below is on the corrected input and",
           "replaces the published HY rows.", ""]
    for read, blk in R.items():
        pub, kind = PUB[read]
        src = find_oos(pub) if kind == "oos" else pub
        out += [f"## {read}", "",
                "| series | near | defined | acceptance | placed mass in band (alert) | top p90 old → new | top mean old → new | bottom p90 old → new | false risk-off/yr mean old → new |",
                "|---|---|---|---:|---|---|---|---|---|"]
        for key, row in blk.items():
            name, near = key.split("|")
            old = (src.get(near) if kind == "oos" else src.get(key)) or {}
            fig = row["figures"]
            ib = row["in_band_mass_share"] or {}
            hy = " (HY: replaces published row)" if row.get("pre_repair_reproduced") not in (None, True) else ""
            out.append(
                f"| {name}{hy} | {near} | {'yes' if row['defined'] else '**not defined at this exposure**'} | "
                f"{f(row['acceptance'])} | {f(ib.get('placed'))} ({f(ib.get('alert'))}) | "
                f"{f((old.get('top') or {}).get('placebo_p90'))} → {f(fig['top_placebo_p90'])} | "
                f"{f((old.get('top') or {}).get('placebo_mean'))} → {f(fig['top_placebo_mean'])} | "
                f"{f((old.get('bottom') or {}).get('placebo_p90'))} → {f(fig['bottom_placebo_p90'])} | "
                f"{f((old.get('false_risk_off_per_year') or {}).get('placebo_mean'))} → {f(fig['fro_mean'])} |")
        out.append("")
    print("\n".join(out))


if __name__ == "__main__":
    main()
