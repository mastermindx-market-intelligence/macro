"""Explicit synthetic D06 UI fixtures. Never copied into published data owners."""
from __future__ import annotations
import copy
import numpy as np
import pandas as pd


def stage_fixtures():
    from scripts.capture_stage_analysis_w7_evidence import (
        fixture_sga, screener_payload, board_payload, ranks_payload, earnings_payload, alt_payload)
    context = fixture_sga()
    context["population"]["data_session"] = "2026-09-09"
    context["data_session"] = "2026-09-09"
    screener = screener_payload()
    screener.update(built="2026-09-10T12:00:00Z", target_stage_week="2026-09-04",
                    target_week_source="fixture-calendar", population=copy.deepcopy(context["population"]))
    for row in screener["rows"]:
        row["stage_source_asof"] = "2026-09-09"
        if row["stage_current"] is True:
            row["stage_week_end"] = "2026-09-04"
    board = board_payload()
    board.update(target_stage_week="2026-09-04", population=copy.deepcopy(context["population"]))
    calls = earnings_payload()
    calls["rows"][0]["positive_highlights"] = "1. Synthetic fixture: demand increased.\n2. Synthetic fixture: guidance increased."
    calls["rows"][0]["key_quote"] = "Synthetic fixture quotation for reader verification."
    side = lambda tag, delta: {"count": 1, "median_delta": delta,
        "industry_allocation": [{"gics_industry": "Semiconductors", "count": 1}],
        "level1_tags": [{"tag": tag, "count": 1}]}
    flow = {"industry_id": "semis", "industry_name": "Semiconductors", "state": "NEUTRAL",
            "turn_flag": "bounce", "n": 2, "sata_mean": 6, "rs_chg_4w_median": 0,
            "rs_level_median": 0, "breadth_4w_pct": 50, "stage2_count": 1, "stage4_count": 1,
            "stage2_stage4_ratio": 1, "fresh_stage2_pct": 50, "stage2_median_age_wks": 6}
    alt = alt_payload()
    alt["sources"]["google"].update(asof="2026-09-09", seed_only=False, topics=[
        {"topic": "Synthetic AI demand topic", "type": "Technology", "yoy_pct": 20,
         "description": "Synthetic interface-verification topic.", "explanation": "Synthetic company match.",
         "matched_ticker": "NVDA", "matched_company": "NVIDIA"}])
    data = {
        "screener.json": screener,
        "stage_board_weekly.json": copy.deepcopy(board),
        "stage_board_daily.json": copy.deepcopy(board),
        "industry_ranks.json": ranks_payload(),
        "industry_heatmap.json": {"history": {"status": "accruing", "first_week": "2026-08-28", "weeks_available": 2, "weeks_target": 26},
            "regions": {"USA": {"weeks": ["2026-09-04", "2026-08-28"], "rows": [{"industry": "Semiconductors", "ranks": [1, None]}]}}},
        "ec_industry_heatmap.json": {"regions": {"USA": {"weeks": ["2026-09-04", "2026-08-28", "2026-08-21"],
            "rows": [{"industry": "Semiconductors", "cells": [{"combined": 50.2, "count": 2}, None, {"combined": None, "count": 0}]}]}}},
        "industry_flows.json": {"industry_regions": {"USA": [flow, dict(flow, industry_id="software", industry_name="Software", rs_chg_4w_median=2)]},
            "sub_industry_regions": {"USA": [dict(flow, industry_id="designers", industry_name="Semiconductor designers")]}},
        "earnings_table.json": calls,
        "earnings_season.json": {"data_status": "ok", "quarters": [{"quarter": "Q2 2026", "n_calls": 2,
            "raisers": side("guidance_raised", 4), "decliners": side("demand_slowdown", -3)}]},
        "earnings_compare.json": {"data_status": "ok", "rows": [{"ticker": "NVDA", "company_name": "NVIDIA",
            "region": "USA", "current_quarter": "Q2 2026", "prior_quarter": "Q1 2026",
            "current_combined": 80.2, "prior_combined": 76.2, "delta_combined": 4, "new_tags": ["guidance_raised"]}]},
        "altdata_trending.json": alt,
        "research_index.json": {"items": [{"ticker_ui": "NVDA", "thesis_summary":
            "Synthetic company primer for interface verification. "*8,
            "has_gemini": True, "has_openai": True, "has_claude": True}]}
    }
    return context, data


def spv_fixture_vm():
    from scripts import build_spvector as spv
    from tests.test_spvector_page import _spvector_vm
    vm = copy.deepcopy(_spvector_vm())
    idx = pd.bdate_range("2013-01-02", "2026-10-21")
    x = np.arange(len(idx))
    spy = pd.Series(150*np.exp(x/2600)*(1+.07*np.sin(x/110)), index=idx)
    alloc = pd.Series(np.take([1., .66, .33, 0.], (x//210)%4), index=idx)
    alloc.iloc[-30:] = 1.
    risk = pd.Series(20+25*(1+np.sin(x/90)), index=idx)
    eq = pd.Series(np.exp(x/2850)*(1+.04*np.sin(x/120)), index=idx)
    hodl = spy/spy.iloc[0]
    vm.update(as_of="Oct 21, 2026", built="Synthetic UI fixture · 2026-11-04",
              bench_start="Jan 02, 2013", price=float(spy.iloc[-1]), score=21,
              score_as_of="2026-10-19", score_aligned_as_of="2026-10-21",
              allocation_as_of="2026-10-21", legs_as_of="2026-10-22", legs_score=24.8,
              last_switch={"date": "2026-09-10", "frm": 66, "to": 100},
              overlay={"enabled": True, "veto": True, "overlay_weight": .66, "mechanical_weight": 1.,
                       "veto_reason": "Synthetic recorded research rationale. Not applied to the mechanical weight.",
                       "note": ""},
              overlay_log={"days": 76, "rows": 430, "vetoes": 3, "first": "Jun 12, 2026", "last": "Oct 21, 2026"})
    vm["sc"]["years"] = round((idx[-1]-idx[0]).days/365.25,1)
    vm["next_note"] = "Synthetic fixture: a sustained score above 25 would reduce the band weight to 66%."
    vm["next_note_zh"] = "合成示例：评分持续高于25时，区间权重降至66%。"
    vm["disloc"].update(capitulation=0, put_absent=False, cap_as_of="2026-10-20",
                        put_as_of="2026-10-19", put_legs_as_of="2026-10-18",
                        put_legs={"recession": False, "fedput_off": False})
    vm["charts"] = {"strategy": spv._chart_strategy(spy, alloc, risk, eq),
        "growth": spv._chart_growth(eq, hodl),
        "dd": spv._chart_dd((eq/eq.cummax()-1)*100, (hodl/hodl.cummax()-1)*100)}
    return vm
