"""Authored numerical and document checks; not factual review or application acceptance."""
from __future__ import annotations
from collections import Counter
from fractions import Fraction as F
from math import isclose
from pathlib import Path
import json
import re
from calculate_wave6 import (calculate, annuity_pv, project_npv, account_value,
                             route_contribution, measurement_case, water_contribution,
                             available_event)

ROOT = Path(__file__).resolve().parent
checks: list[dict] = []


def check(name: str, condition: bool, category: str = "arithmetic") -> None:
    checks.append({"name": name, "category": category, "pass": bool(condition)})


def close(name: str, observed: float, expected: float | F) -> None:
    check(name, isclose(observed, float(expected), rel_tol=1e-10, abs_tol=1e-10))


def reject(name: str, fn) -> None:
    try:
        fn()
    except (ValueError, TypeError):
        check(name, True, "invalid_input")
    else:
        check(name, False, "invalid_input")


def rational_annuity(years: int, rate: F) -> F:
    return (1-(1+rate)**(-years))/rate


def main() -> int:
    result = calculate()
    af8 = rational_annuity(8, F(9,100))
    close("modular_full_exact_formula", result["modular"]["npv_full_m"], -10+3*af8)
    close("modular_60_exact_formula", result["modular"]["npv_60pct_m"], -10+af8)
    close("modular_break_even", result["modular"]["break_even_utilization"], (10/af8+2)/5)
    close("zero_rate_annuity", annuity_pv(7, 4, 0), 28)
    close("negative_cash_is_not_clamped", project_npv(0, -2, 2, 0), -4)
    for q, label, contribution in [(F(95,100), "95", 30), (F(9,10), "90", 30), (F(9,10), "90", 35)]:
        expected = F(contribution,1)/F(109,100)*(1-(q/F(109,100))**10)/(1-q/F(109,100))
        close(f"retention_closed_form_{contribution}_{label}", account_value(contribution, float(q), 10, .09), expected)
    close("no_renewals_first_payment_only", account_value(30, 0, 10, .09), F(3000,109))
    close("certain_renewals", account_value(30, 1, 10, .09), 30*rational_annuity(10,F(9,100)))
    check("higher_contribution_can_lose_to_churn", result["retention"]["pv_contribution35_retention90"] < result["retention"]["pv_contribution30_retention95"])
    close("ending_units95", result["retention"]["ending_units95"],1070)
    close("ending_units90", result["retention"]["ending_units90"],1020)
    for key, value in {"raw_energy_difference":200,"adjusted_energy_saving":50,"old_bill":180,"new_bill":250,"counterfactual_bill":262.5,"avoided_current_bill":12.5}.items():
        close("measurement_"+key,result["measurement"][key],value)
    close("negative_verified_savings_remain_negative", measurement_case(1200,950,1000,.15,.25)["adjusted_energy_saving"],-50)
    af10=rational_annuity(10,F(8,100));af5=rational_annuity(5,F(8,100))
    for key, expected in {
        "npv_ten_years_m":-2+F(35,100)*af10,
        "npv_five_years_m":-2+F(35,100)*af5,
        "npv_30pct_net_benefit_capture_m":-2+F(105,1000)*af10,
        "npv_25pct_capex_overrun_m":-F(5,2)+F(35,100)*af10}.items():
        close("retrofit_"+key,result["retrofit"][key],expected)
    for stops,expected in [(250,300),(275,450),(300,600),(301,-594),(500,600)]:
        close(f"route_{stops}",route_contribution(stops,300)["contribution"],expected)
    close("zero_stops_zero_active_routes",route_contribution(0,300)["contribution"],0)
    close("price_churn_contribution",result["price_churn"]["contribution"],285)
    close("price_churn_revenue",result["price_churn"]["revenue"],2835)
    for key, value in {"baseline_volume_only_m":F(3,5),"lower_volume_only_m":F(3,50),"baseline_availability_m":F(3,5),"lower_volume_availability_m":F(9,25)}.items():
        close("water_"+key,result["water"][key],value)
    a=result["reported_arithmetic"]
    expected={
        "fix_cfo_increase_m":F(1363709,1000),
        "fix_billings_cash_contribution_change_m":F(684726,1000),
        "emcor_reported_incremental_margin_pct":F(132128,850492)*100,
        "otis_service_reported_incremental_margin_pct":F(21,261)*100,
        "kone_reported_profit_change_pct":(F(3222,3380)-1)*100,
        "kone_adjusted_profit_change_pct":(F(3699,3472)-1)*100,
        "wm_fcf_current_m":2024,"wm_fcf_previous_m":1293,"wm_fcf_change_m":731,
        "xylem_product_gross_margin_pct":F(860,1953)*100,
        "xylem_service_gross_margin_pct":F(103,383)*100,
        "limbach_acquisition_share_reported_increase_pct":F(30935,31216)*100,
        "limbach_guidance_previous_margin_midpoint_pct":F(92,745)*100,
        "limbach_guidance_current_margin_midpoint_pct":F(81,775)*100,
        "abm_quarter_cfo_growth_pct":(F(1468,1750)-1)*100,
        "abm_nine_month_cfo_growth_pct":(F(275,101)-1)*100,
        "veralto_reported_recurring_share_pct":F(1802,2896)*100,
        "pentair_final_vs_april_midpoint_pct":(F(1140,1485)-1)*100,
        "pentair_final_vs_preliminary_pct":(F(114,112)-1)*100,
    }
    for key, value in expected.items():close(key,a[key],value)
    for cutoff, source in [("2026-04-27",None),("2026-04-28","W6-S15"),("2026-07-13","W6-S15"),("2026-07-14","W6-S16"),("2026-07-27","W6-S16"),("2026-07-28","W6-S17")]:
        event=available_event(cutoff)
        check("availability_"+cutoff,(None if event is None else event["source"])==source,"availability")
    for name,fn in [
        ("zero_horizon",lambda:annuity_pv(1,0,.1)),
        ("fractional_horizon",lambda:annuity_pv(1,2.5,.1)),
        ("minus_one_rate",lambda:annuity_pv(1,2,-1)),
        ("nan_rate",lambda:annuity_pv(1,2,float('nan'))),
        ("negative_initial",lambda:project_npv(-1,2,5,.1)),
        ("negative_retention",lambda:account_value(30,-.1,10,.09)),
        ("retention_above_one",lambda:account_value(30,1.1,10,.09)),
        ("fractional_stops",lambda:route_contribution(2.5,300)),
        ("negative_stops",lambda:route_contribution(-1,300)),
        ("zero_route_capacity",lambda:route_contribution(1,0)),
        ("negative_route_cost",lambda:route_contribution(1,300,route_cost=-1)),
        ("negative_energy",lambda:measurement_case(1,-1,1,.1,.1)),
        ("nonfinite_water",lambda:water_contribution(float('inf'),1,2)),
        ("invalid_availability_date",lambda:available_event("2026-99-99")),
    ]:reject(name,fn)
    evidence=(ROOT/'INDUSTRIALS_WAVE6_EVIDENCE_2026-09-23.md').read_text()
    model=(ROOT/'INDUSTRIALS_WAVE6_ECONOMIC_MODEL_2026-09-23.md').read_text()
    ids=re.findall(r'^## (W6-S\d\d) -',evidence,re.M)
    check("26_unique_sources",len(ids)==len(set(ids))==26,"integrity")
    check("26_source_urls",len(re.findall(r'^Source: https://',evidence,re.M))==26,"integrity")
    check("24_research_slices",len(re.findall(r'^\| BSE-\d\d',model,re.M))==24,"integrity")
    check("12_hypotheses",len(re.findall(r'^\| H6-\d\d',model,re.M))==12,"integrity")
    check("32_unexecuted_requirements",len(re.findall(r'^\| W6-T\d\d',model,re.M))==32 and 'unexecuted application' in model,"integrity")
    refs=set(re.findall(r'W6-S\d\d',model))|set(a["sources"])
    check("references_resolve",refs<=set(ids),"integrity")
    check("no_nonfinite_output",'NaN' not in json.dumps(result,allow_nan=False),"integrity")
    check("finite_retention_no_terminal",'no terminal value' in model.lower(),"integrity")
    check("model_limits_visible",'not an optimized routing' in model and 'not statistically estimated' in model,"integrity")
    check("handoff_held_and_mission_incomplete",'not a final Fable CEO handoff' in model and 'MISSION_COMPLETE: false' in model,"integrity")
    failed=[c for c in checks if not c["pass"]]
    report={"scope":"authored_research_only","passed":len(checks)-len(failed),"failed":len(failed),
            "categories":dict(Counter(c["category"] for c in checks)),"checks":checks}
    (ROOT/'WAVE6_CHECKS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('scope','passed','failed','categories')},indent=2))
    for c in failed:print('FAIL:',c['name'])
    return 1 if failed else 0


if __name__=='__main__':
    raise SystemExit(main())
