"""Actual basket/context owners compose the Brief without builder effects."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import importlib.util
from functools import lru_cache
import json
from pathlib import Path

import pandas as pd
import pytest

from engine import baskets, sector_pulse, theme_context, us_act_now
from engine import sector_basket_documents as documents
from lib import config, store


@lru_cache(maxsize=1)
def _captured_example():
    path = Path(__file__).parent / "test_sector_basket_context_inputs.py"
    spec = importlib.util.spec_from_file_location("basket_context_fixtures_for_documents", path)
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    data = baskets.compute_baskets_from_inputs(helpers.basket_inputs())
    context = helpers.context_inputs()
    ti = deepcopy(context.theme_intel)
    for rank, theme in enumerate(ti["themes"], 1):
        theme.update(rank=rank, name=theme["id"], name_zh="中文"+theme["id"])
    ti["act_now"] = {"buy": [{"id": "alpha"}], "add_on_pullback": [{"id": "beta"}],
                      "reduce": [{"id": "gamma"}, {"id": "delta"}]}
    rows = [{"id": "b-gamma", "name": "Gamma", "kind": "basket", "phase": "Trough", "pos": 2.,
             "osc_slope": 1.3, "signal": "BUY", "above200d": False,
             "timing_state": "COUNTERTREND BOUNCE", "date": "2026-10-30"},
            {"id": "b-delta", "name": "Delta", "kind": "basket", "phase": "Recovery", "pos": 5.,
             "osc_slope": 1., "signal": "BUY", "above200d": False, "date": "2026-10-30"},
            {"id": "xlc", "name": "Communication", "kind": "sector", "phase": "Trough", "pos": 3.,
             "osc_slope": 1., "signal": "BUY", "above200d": False, "date": "2026-10-30"}]
    factor = {"schema": "factor_seasonality.v2", "as_of": "2026-11-01", "now": {
        "chip_en": "Seasonal context", "chip_zh": "季节背景", "headline_en": "Context", "headline_zh": "背景",
        "stance_en": "Watch", "stance_zh": "观察", "factors": [
            {"key": "momentum", "verdict": "neutral"}, {"key": "quality", "verdict": "neutral"}]}}
    return documents.SectorBasketDocumentInputs(source_session="2026-11-04", basket_payload=data,
        theme_intel=ti, allocation=context.allocation, context_history=context.history,
        rotation_events=context.rotation_events, bottoming_cycle_rows=rows,
        bottoming_ledger_session="2026-10-30", sector_names_zh={"xlc": "通信", "gamma": "覆盖名称"},
        factor_seasonality=factor, flow={"as_of": "2026-11-03", "cluster": {"regime": "broadening", "extra": 9}, "private": 1},
        pulse_archive=[], pulse_heat_calibration={},
        built_at=datetime(2026,11,5,6,30,tzinfo=timezone(timedelta(hours=8))))


def inputs():
    return deepcopy(_captured_example())


def test_actual_owner_outputs_form_coherent_brief_and_keep_older_display_clocks():
    value = inputs(); before = deepcopy(value)
    result = documents.assemble_sector_basket_documents(value)
    assert result.baskets["as_of"] == "2026-11-04"
    assert result.baskets["chart"] == value.basket_payload["chart"]
    act = result.baskets["theme_intel"]["act_now"]
    for lane in ("buy", "add_on_pullback", "reduce"):
        assert act[lane] == value.theme_intel["act_now"][lane]
    assert act["dual_read_ids"] == ["b-gamma", "gamma"]
    assert act["recovering_ids"] == ["b-delta", "delta"]
    assert [row["id"] for row in act["bottoming_watch"]] == ["b-gamma", "xlc"]
    assert [row["name_zh"] for row in act["bottoming_watch"]] == ["覆盖名称", "通信"]
    assert all(row["gate_conflict"] for row in act["bottoming_watch"])
    handoff = result.si_handoff
    assert set(handoff) == {"theme_context", "factor_season", "flow", "basket_member_syms", "generated_utc"}
    assert handoff["theme_context"]["as_of"] == "2026-11-04"
    assert handoff["factor_season"] is None
    assert handoff["flow"] == {"cluster": {"regime": "broadening"}}
    assert handoff["basket_member_syms"] == list("ABCDEFGHI")
    assert handoff["generated_utc"] == "2026-11-04 22:30 UTC"
    assert result.evidence["bottoming_ledger_session"] == "2026-10-30"
    assert result.evidence["factor_source_as_of"] == "2026-11-01"
    assert result.evidence["flow_source_as_of"] == "2026-11-03"
    assert result.pulse["as_of"] == "2026-11-04"
    assert result.baskets["theme_intel"]["themes"][0]["pulse_heat"] == result.pulse["themes"][0]["heat"]
    assert value == before
    json.dumps([result.baskets, result.si_handoff, result.evidence], allow_nan=False)


def test_no_builder_archive_ledger_config_or_store_effects_and_no_input_aliases(monkeypatch):
    value = inputs(); before = deepcopy(value)
    attempted = []
    def forbidden(*args, **kwargs):
        attempted.append("effect")
        raise AssertionError("Composition reached an ambient effect")
    for obj, names in ((config, ("load", "data_dir")), (store, ("read",)),
                       (pd, ("read_parquet",)), (us_act_now, ("load_cycle_rows",)),
                       (sector_pulse, ("_load_archive_snapshots", "_heat_calibration", "write_pulse", "write_score_snapshot")),
                       (theme_context, ("_load_history", "_write_history", "_seed_from_archive", "_load_alignment_events", "_advance_enabled", "write_context"))):
        for name in names:
            monkeypatch.setattr(obj, name, forbidden)
    result = documents.assemble_sector_basket_documents(value)
    assert attempted == []
    result.baskets["theme_intel"]["themes"][0]["name"] = "changed"
    result.baskets["chart"]["mutated"] = True
    result.si_handoff["theme_context"]["as_of"] = "1900-01-01"
    assert value == before


@pytest.mark.parametrize("rows,source", [(None,"absent"), ([],"present_empty")])
def test_absent_and_empty_bottoming_source_remain_distinct(rows, source):
    value = replace(inputs(), bottoming_cycle_rows=rows, bottoming_ledger_session=None)
    result = documents.assemble_sector_basket_documents(value)
    assert result.baskets["theme_intel"]["act_now"]["bottoming_watch"] == []
    assert result.evidence["bottoming_source"] == source
    assert bool(result.evidence["bottoming_notes"]) is (rows is None)


@pytest.mark.parametrize("field", ["basket_payload", "theme_intel", "allocation"])
def test_mixed_baseline_is_not_a_current_brief(field):
    value = inputs(); changed = deepcopy(getattr(value, field)); changed["as_of"] = "2026-11-03"
    with pytest.raises(ValueError, match="baseline session mismatch"):
        documents.assemble_sector_basket_documents(replace(value, **{field:changed}))


@pytest.mark.parametrize("case", ["future_ledger", "undated_rows", "wrong_row_date", "absent_dated_ledger",
    "naive_build", "build_before_observation", "missing_chart", "missing_allocation_ranks", "nonfinite"])
def test_invalid_composition_cannot_publish_current_context(case):
    value = inputs()
    if case == "future_ledger": value=replace(value,bottoming_ledger_session="2026-11-05")
    elif case == "undated_rows": value=replace(value,bottoming_ledger_session=None)
    elif case == "wrong_row_date": value.bottoming_cycle_rows[0]["date"]="2026-10-29"
    elif case == "absent_dated_ledger": value=replace(value,bottoming_cycle_rows=None)
    elif case == "naive_build": value=replace(value,built_at=datetime(2026,11,5))
    elif case == "build_before_observation": value=replace(value,built_at=datetime(2026,11,3,tzinfo=timezone.utc))
    elif case == "missing_chart": value.basket_payload.pop("chart")
    elif case == "missing_allocation_ranks": value.allocation["ranks"]=[]
    elif case == "nonfinite": value.basket_payload["unexpected"]=float("nan")
    with pytest.raises(ValueError):
        documents.assemble_sector_basket_documents(value)


@pytest.mark.parametrize("factor,expected", [(None,None), ({},None),
    ({"schema":"old","now":{"chip_en":"x"}},None),
    ({"schema":"factor_seasonality.v2","now":{"chip_en":"x","factors":[42]}},None)])
def test_optional_factor_absence_and_malformed_values_do_not_invent_chip(factor,expected):
    assert documents.factor_season_from_inputs(factor)==expected


@pytest.mark.parametrize("factors,tone", [
    ([{"key":"quality","verdict":"headwind"},{"key":"momentum","verdict":"tailwind"}],"tailwind"),
    ([{"key":"momentum","verdict":"neutral"},{"key":"quality","verdict":"headwind"},
      {"key":"value","verdict":"tailwind"}],"headwind")])
def test_factor_chip_preserves_existing_momentum_priority_and_order(factors,tone):
    factor={"schema":"factor_seasonality.v2","now":{"chip_en":"Chip","chip_zh":"标签",
        "headline_en":"Heading","headline_zh":"标题","stance_en":"Watch","stance_zh":"观察","factors":factors}}
    assert documents.factor_season_from_inputs(factor)=={"chip_en":"Chip","chip_zh":"标签",
        "tip_en":"Heading Watch","tip_zh":"标题 观察","tone":tone}


def test_member_projection_uses_computed_rows_not_raw_membership():
    assert documents.basket_member_symbols({"baskets":[{"members":[{"symbol":" b "},{"symbol":"a"},
        {"symbol":"B"},{"ticker":"OUTSIDE"},{"symbol":None}]}]}) == ["A","B"]


def test_assembled_documents_feed_the_existing_native_brief_projection():
    from engine.sector_native_view import SectorViewInputs, SectorViewReceipt, project_sector_view
    value = inputs()
    assembled = documents.assemble_sector_basket_documents(value)
    source = value.source_session
    central = {"as_of": source, "sectors": [
        {"id": "xlv", "ticker": "XLV", "kind": "sector", "name": "Health Care"}]}
    cycles = {"meta": {"asOf": source, "rs_history": {
        "schema": "sector_cycles.rs_history.v1", "mode": "reconstructed_price_history",
        "naturally_observed": False, "basis": "tr", "benchmark": "SPY",
        "horizons_sessions": [21,63], "max_points_per_sector": 252}},
        "sectors": [{"id":"xlv", "ticker":"XLV", "kind":"sector", "rs_history":[], "turns":[]}]}
    board = {lane: [] for lane in ("buy_now", "buy_soon", "on_the_run", "take_profits", "hold", "avoid")}
    board["hold"] = [{"ticker":"alpha", "name":"Alpha", "kind":"theme", "href":"basket/alpha.html"}]
    action = {"schema":"sector_intelligence_action_board.v1", "as_of":source, "action_board":board}
    view = project_sector_view(SectorViewInputs(central, cycles, assembled.baskets, assembled.si_handoff, action),
        SectorViewReceipt("controlled-composition", source, "2026-11-04T23:00:00Z", "accepted", "controlled-inputs"),
        audience="preview")
    brief = view["data"]["brief"]
    assert brief["as_of"] == source
    assert brief["comparison"]["status"] == "available"
    assert brief["comparison"]["subject"]["id"] == "alpha"
    assert brief["comparison"]["series"]["end"] == source
    assert brief["comparison"]["series"]["sessions"] == 20
    assert len(brief["comparison"]["series"]["points"]) == 21
    assert brief["leadership"]["strength"]
    assert "bottoming_ledger_session" not in json.dumps(view)
