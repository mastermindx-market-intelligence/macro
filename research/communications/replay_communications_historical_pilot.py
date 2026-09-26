"""Fixed, retrospective Communications historical-input diagnostic.

Reads only the accompanying author-transcribed public-source research JSON.
This is not a native financial feed, live forecaster, backtest service, source
parser, valuation engine or trading model. Printed source dates filter this
sample; they do not prove intraday availability or original system retention.
Only an explicitly requested --output path is written. No network or model.
"""
from __future__ import annotations
import argparse
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction as F
import json
from pathlib import Path
import re

ROSTER = ("Meta", "Alphabet", "The Trade Desk", "Magnite")
FLAGS = ("can_rank", "can_gate", "can_size", "can_originate", "can_open_entry")
CORE = ("revenue", "operating_costs_including_cost_of_revenue", "operating_income")
NUM = re.compile(r"^-?(0|[1-9]\d*)(\.\d+)?$")
DEFAULT_INPUT = Path(__file__).with_name("COMMUNICATIONS_HISTORICAL_INPUT_PILOT_2026-09-24.json")

def number(value):
    if not isinstance(value, str) or not NUM.fullmatch(value):
        raise ValueError("invalid_decimal_string")
    try:
        out = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid_decimal_string") from exc
    if not out.is_finite():
        raise ValueError("nonfinite")
    return F(out)

def text(value):
    """Six decimal places is output formatting, not source precision."""
    value = F(value)
    if value.denominator == 1:
        return str(value.numerator)
    with localcontext() as ctx:
        ctx.prec = 48
        return format(Decimal(value.numerator) / Decimal(value.denominator), ".6f")

def sources(data):
    return {s["id"]:s for s in data["source_register"]}

def _unique(items):
    ids = [r["id"] for r in items]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_record_id")

def _context(row, source_map, cash=False):
    if row["issuer"] not in ROSTER or row["source_id"] not in source_map:
        raise ValueError("unknown_subject_or_source")
    s = source_map[row["source_id"]]
    if s["issuer"] != row["issuer"]:
        raise ValueError("source_issuer_mismatch")
    start, end = date.fromisoformat(row["period_start"]), date.fromisoformat(row["period_end"])
    if start > end or date.fromisoformat(s["publication_date"]) < end:
        raise ValueError("period_or_publication_mismatch")
    if row["currency"] != "USD":
        raise ValueError("currency_mismatch")
    scale = 1000000 if row["issuer"] in ("Meta","Alphabet") else 1000
    if type(row["units_per_printed_unit"]) is not int or row["units_per_printed_unit"] != scale:
        raise ValueError("scale_mismatch")
    if row["scope"] != "consolidated_issuer":
        raise ValueError("scope_mismatch")
    expected_basis = "reported_GAAP_cash_flow_unaudited" if cash else "reported_GAAP_unaudited"
    if row["basis"] != expected_basis:
        raise ValueError("basis_mismatch")
    return start, end

def validate_pilot(data):
    if tuple(data["roster"]) != ROSTER:
        raise ValueError("fixed_roster_changed")
    if set(data["authority"]) != set(FLAGS) or any(data["authority"][k] is not False for k in FLAGS):
        raise ValueError("authority_not_absent")
    _unique(data["source_register"])
    smap = sources(data)
    for group in ("income_observations","cash_flow_observations"):
        _unique(data[group])
    keys=set()
    for row in data["income_observations"]:
        start,end=_context(row,smap)
        if row["period_type"] != "quarter" or start.isoformat()!=f"{end.year}-04-01" or end.isoformat()!=f"{end.year}-06-30":
            raise ValueError("income_period_mismatch")
        values={k:number(row[k]) for k in CORE}
        if values["revenue"] <= 0 or values["operating_costs_including_cost_of_revenue"] < 0:
            raise ValueError("income_domain")
        if values["revenue"]-values["operating_costs_including_cost_of_revenue"] != values["operating_income"]:
            raise ValueError("accounting_identity")
        key=(row["issuer"],row["period_end"],row["source_id"])
        if key in keys: raise ValueError("duplicate_income_context")
        keys.add(key)
    for row in data["cash_flow_observations"]:
        start,end=_context(row,smap,cash=True)
        allowed = {
            (f"{end.year}-01-01",f"{end.year}-03-31","quarter"),
            (f"{end.year}-01-01",f"{end.year}-06-30","year_to_date_half_year"),
            (f"{end.year}-04-01",f"{end.year}-06-30","quarter"),
        }
        if (str(start),str(end),row["period_type"]) not in allowed:
            raise ValueError("cash_period_mismatch")
        if row["flow_convention"] != "signed_cash_flows": raise ValueError("cash_sign_convention")
        required=set(data["cash_subtotal_definitions"][row["issuer"]]["fields"])
        if set(row["components"]) != required: raise ValueError("cash_component_mismatch")
        for key,value in row["components"].items():
            n=number(value)
            if key!="cfo" and n>0: raise ValueError("cash_outflow_sign")
        for value in row["selected_working_capital_lines"].values(): number(value)
        if row["issuer_reported_fcf"] is not None:
            if number(row["issuer_reported_fcf"]) != sum(map(number,row["components"].values()),F(0)):
                raise ValueError("issuer_cash_reconciliation")
    return True

def selected_income(data, issuer, year, ceiling):
    """Research sample selection only; no historical-completeness claim."""
    cap=date.fromisoformat(ceiling); smap=sources(data)
    rows=[r for r in data["income_observations"]
          if r["issuer"]==issuer and r["period_end"]==f"{year}-06-30"
          and date.fromisoformat(smap[r["source_id"]]["publication_date"])<=cap]
    if not rows: return None
    latest=max(smap[r["source_id"]]["publication_date"] for r in rows)
    rows=[r for r in rows if smap[r["source_id"]]["publication_date"]==latest]
    if len(rows)!=1: raise ValueError("ambiguous_source_day")
    return rows[0]

def quarter_cash(data, issuer, year):
    """Reconcile one quarter from exact selected printed inputs."""
    smap=sources(data)
    rows=[r for r in data["cash_flow_observations"] if r["issuer"]==issuer
          and r["period_end"].startswith(str(year))
          and smap[r["source_id"]]["publication_date"].startswith(str(year))]
    direct=[r for r in rows if r["period_start"]==f"{year}-04-01" and r["period_end"]==f"{year}-06-30"]
    if direct:
        if len(direct)!=1: raise ValueError("cash_inputs_ambiguous")
        refs=[direct[0]["id"]]
        comps={k:number(v) for k,v in direct[0]["components"].items()}
        wc={k:number(v) for k,v in direct[0]["selected_working_capital_lines"].items()}
        method="quarter_reported"
    else:
        h1=[r for r in rows if r["period_type"]=="year_to_date_half_year"]
        q1=[r for r in rows if r["period_start"]==f"{year}-01-01" and r["period_end"]==f"{year}-03-31"]
        if len(h1)!=1 or len(q1)!=1: raise ValueError("cash_inputs_missing")
        a,b=h1[0],q1[0]
        for key in ("scope","currency","units_per_printed_unit","basis","flow_convention","period_start"):
            if a[key]!=b[key]: raise ValueError("cash_context_mismatch")
        if a["period_end"]!=f"{year}-06-30" or a["period_start"]!=f"{year}-01-01":
            raise ValueError("cash_period_mismatch")
        if set(a["components"]) != set(b["components"]): raise ValueError("cash_component_mismatch")
        comps={k:number(a["components"][k])-number(b["components"][k]) for k in a["components"]}
        wc={k:number(a["selected_working_capital_lines"][k])-number(b["selected_working_capital_lines"][k])
            for k in a["selected_working_capital_lines"].keys() & b["selected_working_capital_lines"].keys()}
        refs=[a["id"],b["id"]]
        method="same_year_H1_minus_Q1; selected definitions author-checked"
    subtotal=sum(comps.values(),F(0))
    return {
      "issuer":issuer,"year":year,"period_start":f"{year}-04-01","period_end":f"{year}-06-30",
      "method":method,"input_refs":refs,"cfo":text(comps["cfo"]),
      "signed_components":{k:text(v) for k,v in comps.items()},
      "selected_cash_subtotal":text(subtotal),"cash_label":data["cash_subtotal_definitions"][issuer]["label"],
      "working_capital_lines":{k:text(v) for k,v in wc.items()},
      "units_per_printed_unit":1000000 if issuer in ("Meta","Alphabet") else 1000,
      "not_peer_standardized":True,
    }

def run(data):
    validate_pilot(data)
    smap=sources(data)
    forecasts=[]; outcomes=[]; vintages=[]; exact=True
    for issuer in ROSTER:
        origin=smap[data["origin_source_ids"][issuer]]
        target=smap[data["outcome_source_ids"][issuer]]
        a=selected_income(data,issuer,2023,origin["publication_date"])
        b=selected_income(data,issuer,2024,origin["publication_date"])
        c=selected_income(data,issuer,2025,target["publication_date"])
        later=selected_income(data,issuer,2024,target["publication_date"])
        if b is not None and later is not None:
            vintages.append({"issuer":issuer,"original_record":b["id"],"later_comparative_record":later["id"],
                "selected_core_amounts_agree":all(b[k]==later[k] for k in CORE),
                "meaning":"Selected printed consolidated values only, not proof all definitions or source bytes are identical."})
        if any(r is None for r in (a,b,c)):
            forecasts.append({"issuer":issuer,"status":"unavailable","reason":"required_selected_income_missing"})
            outcomes.append({"issuer":issuer,"status":"unavailable"})
            continue
        r0,r1,r2=(number(r["revenue"]) for r in (a,b,c))
        o0,o1,o2=(number(r["operating_income"]) for r in (a,b,c))
        if r1==r0: raise ValueError("historical_slope_denominator_zero")
        rh=r1*r1/r0
        slope=(o1-o0)/(r1-r0)
        m1=o1/r1; m2=o2/r2
        om=rh*m1; os=o1+(rh-r1)*slope
        revenue_effect=m1*(r2-rh)
        realized_margin_effect=o2-m1*r2
        exact=exact and revenue_effect+realized_margin_effect==o2-om
        forecasts.append({
          "issuer":issuer,"status":"retrospective_diagnostic_only",
          "source_date_ceiling":origin["publication_date"],"target_release_date":target["publication_date"],
          "training_input_refs":[a["id"],b["id"]],"outcome_ref":c["id"],
          "units_per_printed_unit":b["units_per_printed_unit"],
          "repeat_level_revenue_prediction":text(r1),"repeated_growth_revenue_prediction":text(rh),
          "actual_revenue":text(r2),"repeat_level_revenue_error_pct_actual":text((r2-r1)/r2*100),
          "repeat_growth_revenue_error_pct_actual":text((r2-rh)/r2*100),
          "frozen_margin_operating_income_prediction":text(om),"slope_operating_income_prediction":text(os),
          "actual_operating_income":text(o2),"historical_oi_change_per_revenue_change_pct":text(slope*100),
          "frozen_margin_error_pp_target_revenue":text((o2-om)/r2*100),
          "slope_error_pp_target_revenue":text((o2-os)/r2*100),
          "ex_post_error_decomposition":{"revenue_effect":text(revenue_effect),"realized_margin_effect":text(realized_margin_effect),
              "warning":"Uses actual 2025 results to explain error; never a 2024 forecasting input."},
          "not_preregistered":True,"causal_or_trading_validation":False,
        })
        cash24=quarter_cash(data,issuer,2024);cash25=quarter_cash(data,issuer,2025)
        cf0=number(cash24["selected_cash_subtotal"]);cf1=number(cash25["selected_cash_subtotal"])
        outcomes.append({
          "issuer":issuer,"status":"reported_historical_comparison",
          "revenue_growth_pct":text((r2/r1-1)*100),
          "operating_income_change":text(o2-o1),"operating_income_growth_pct":text((o2/o1-1)*100),
          "operating_margin_2024_pct":text(m1*100),"operating_margin_2025_pct":text(m2*100),
          "selected_cash_subtotal_2024":text(cf0),"selected_cash_subtotal_2025":text(cf1),
          "selected_cash_subtotal_direction":"up" if cf1>cf0 else "down" if cf1<cf0 else "unchanged",
          "cash_details":[cash24,cash25],"units_per_printed_unit":b["units_per_printed_unit"],
          "stock_outcome":"not_measured",
        })
    mg0=quarter_cash(data,"Magnite",2024);mg1=quarter_cash(data,"Magnite",2025)
    wc0=sum(map(number,mg0["working_capital_lines"].values()),F(0))
    wc1=sum(map(number,mg1["working_capital_lines"].values()),F(0))
    d_cfo=number(mg1["cfo"])-number(mg0["cfo"])
    mg_da=data["diagnostic_observations"][0]
    reduction=number(mg_da["prior"])-number(mg_da["current"])
    mg_origin=smap[data["origin_source_ids"]["Magnite"]]["publication_date"]
    mg_prior=selected_income(data,"Magnite",2023,mg_origin)
    mg_current=selected_income(data,"Magnite",2024,mg_origin)
    op_rise=number(mg_current["operating_income"])-number(mg_prior["operating_income"])
    return {
      "study":"fixed_retrospective_historical_input_pilot",
      "income_records":len(data["income_observations"]),"cash_records":len(data["cash_flow_observations"]),
      "source_register_count":len(smap),"methodology_sources":1,
      "vintage_checks":vintages,"forecast_diagnostics":forecasts,"outcome_comparisons":outcomes,
      "exact_error_decompositions":exact,
      "magnite_depreciation_diagnostic":{"da_expense_reduction":text(reduction),
          "operating_income_improvement":text(op_rise),"reduction_as_pct_of_op_improvement":text(reduction/op_rise*100),
          "warning":"Accounting decomposition, not cash benefit, causal estimate, or normalized earnings."},
      "magnite_working_capital_diagnostic":{"selected_wc_2024":text(wc0),"selected_wc_2025":text(wc1),
          "selected_wc_change":text(wc1-wc0),"cfo_change":text(d_cfo),
          "remaining_accounting_change":text(d_cfo-(wc1-wc0)),
          "warning":"Receivable and payable/accrued changes are only two cash-flow lines; this is not causal attribution or a normalized CFO."},
      "limitations":data["unqualified"],
      "forecast_origin_clock":"printed_source_day_only; no intraday/system-replay certification",
      "no_fitted_model":True,"no_champion_selected":True,"no_price_or_trade_evaluation":True,
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    data=json.loads(DEFAULT_INPUT.read_text(encoding="utf-8"))
    result=run(data)
    rendered=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(rendered,encoding="utf-8")
    print(json.dumps({"income_records":result["income_records"],"cash_records":result["cash_records"],
      "forecasts":len(result["forecast_diagnostics"]),"exact_error_decompositions":result["exact_error_decompositions"],
      "output":str(args.output) if args.output else None}))

if __name__=="__main__":
    main()
