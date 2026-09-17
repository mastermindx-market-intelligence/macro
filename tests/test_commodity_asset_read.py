"""Asset-read projection: one dated fact set, zero new trading authority."""
from copy import deepcopy
import json
import pytest
from scripts.commodity_asset_read import build_asset_read, exposure_percent, attach_asset_reads


def row():
    return {"close":100.0,"alloc_optimal":0.5,"risk_regime":"low_risk", "risk_index":12.0,
            "momentum_state":"bull","ts_trend":"up","driver_score":-0.4}


def view(action="BUY",down=()):
    return {"conviction":{"action":action,"score":30},
            "verdict":{"grade":"TREND-FOLLOW"},
            "mtf_rows":[{"key":k,"trend":"down" if k in down else "up",
                         "macd":"neg" if k in down else "pos"} for k in ("D","3D","W")]}


def read(values=None,display=None,**kw):
    defaults={"signal_asof":"2026-09-15","price_asof":"2026-09-15", "reference_asof":"2026-09-15","instrument":"GC=F"}
    defaults.update(kw)
    return build_asset_read("gold",row() if values is None else values,
                            view() if display is None else display,**defaults)


@pytest.mark.parametrize("value",[None,True,False,float("nan"),float("inf"),-0.1,1.1,"0.5"])
def test_unknown_allocation_never_becomes_zero(value):
    assert exposure_percent(value) is None


@pytest.mark.parametrize("value,want",[(0,0),(0.5,50),(1,100),(0.125,12.5)])
def test_valid_allocations_are_preserved(value,want):
    assert exposure_percent(value)==want


def test_gold_zero_exposure_is_not_overridden_by_positive_trend():
    r=row();r.update(alloc_optimal=0,risk_regime="high_risk",momentum_state="bear")
    v=read(r,view("SELL",("D","3D")))
    assert v["state"]=="defensive" and v["exposure_pct"]==0
    assert v["structural_trend"]=="up"
    assert v["timeframes"][1]["trend"]=="down"
    assert "zero_exposure" in v["reason_codes"]


def test_buy_signal_and_zero_target_are_disclosed_not_averaged():
    r=row();r["alloc_optimal"]=0
    v=read(r,view("BUY"))
    assert v["state"]=="mixed" and "policy_disagreement" in v["reason_codes"]


def test_positive_control_remains_positive_but_grants_no_trade_authority():
    v=read()
    assert v["state"]=="positive"
    assert v["authority"]=="display_only"
    assert v["new_entry_permission"] is None


@pytest.mark.parametrize("key",["D","3D"])
def test_bearish_tactical_read_cannot_render_positive(key):
    v=read(display=view("BUY",(key,)))
    assert v["state"]=="mixed" and "tactical_disagreement" in v["reason_codes"]


def test_high_risk_is_not_hidden_by_long_term_uptrend():
    r=row();r["risk_regime"]="high_risk"
    assert read(r)["state"]!="positive"


@pytest.mark.parametrize("which",["signal_asof","price_asof","reference_asof"])
def test_missing_date_is_explicitly_incomplete(which):
    v=read(**{which:None})
    assert v["state"]=="incomplete" and v["quality"]=="incomplete"


@pytest.mark.parametrize("value",[True,123,"invalid","2026-02-31",""])
def test_malformed_dates_never_look_current(value):
    assert read(signal_asof=value)["state"]=="incomplete"


def test_older_asset_does_not_inherit_freshness_from_other_assets():
    v=read(reference_asof="2026-09-18")
    assert v["state"]=="lagging" and v["lag_calendar_days"]==3
    assert v["signal_asof"]=="2026-09-15"


def test_future_or_split_snapshot_is_not_accepted():
    assert read(signal_asof="2026-09-16")["state"]=="incomplete"
    assert read(price_asof="2026-09-14")["state"]=="incomplete"


@pytest.mark.parametrize("missing",["risk_regime","momentum_state","alloc_optimal"])
def test_missing_core_policy_inputs_are_not_clearance(missing):
    r=row();del r[missing]
    assert read(r)["state"]=="incomplete"


def test_missing_timeframe_is_not_filled_as_up_or_flat():
    display=view();display["mtf_rows"]=[display["mtf_rows"][0]]
    v=read(display=display)
    assert v["state"]=="incomplete"
    assert v["timeframes"][1]["trend"] is None


def test_duplicate_timeframe_evidence_is_incomplete():
    display=view();display["mtf_rows"].append(dict(display["mtf_rows"][0]))
    assert read(display=display)["state"]=="incomplete"


def test_expansion_asset_has_no_invented_allocation_policy():
    v=build_asset_read("corn",row(),view("BUY"),signal_asof="2026-09-15",price_asof="2026-09-15",reference_asof="2026-09-15",instrument="ZC=F")
    assert v["exposure_pct"] is None and v["allocation_applicable"] is False
    assert v["model_action"] is None


def test_input_objects_unchanged_and_output_strict_json():
    r,d=row(),view();before=deepcopy((r,d));v=read(r,d)
    assert (r,d)==before
    json.dumps(v,allow_nan=False)


def test_bad_model_score_is_not_smuggled_into_json():
    d=view();d["conviction"]["score"]=float("nan")
    assert read(display=d)["model_score"] is None


def test_missing_instrument_is_not_silently_gold_futures():
    assert read(instrument=None)["state"]=="incomplete"



def test_one_projection_is_shared_by_detail_and_machine_index():
    import pandas as pd
    from lib import config
    frames={"gold":pd.DataFrame([row()],index=pd.to_datetime(["2026-09-15"]))}
    d={"name":"gold","mtf_rows":view()["mtf_rows"],"verdict":view()["verdict"]}
    asset={"key":"gold",**view()}
    projected=attach_asset_reads([d],frames,[asset],config.load()["commodities"])
    assert d["asset_read"] is projected["gold"]
    assert projected["gold"]["instrument"]=="GC=F"
    assert projected["gold"]["exposure_pct"]==50


def test_member_lag_is_measured_against_actual_newest_input():
    import pandas as pd
    from lib import config
    frames={"gold":pd.DataFrame([row()],index=pd.to_datetime(["2026-09-12"])),
            "oil":pd.DataFrame([row()],index=pd.to_datetime(["2026-09-15"]))}
    detail=[{"name":k,"mtf_rows":view()["mtf_rows"],"verdict":view()["verdict"]} for k in frames]
    assets=[{"key":k,**view()} for k in frames]
    out=attach_asset_reads(detail,frames,assets,config.load()["commodities"])
    assert out["gold"]["state"]=="lagging" and out["gold"]["lag_calendar_days"]==3
    assert out["oil"]["quality"]=="dated"


def test_duplicate_or_unsorted_source_dates_are_not_accepted():
    import pandas as pd
    from lib import config
    for dates in (["2026-09-15","2026-09-15"],["2026-09-15","2026-09-14"]):
        frames={"gold":pd.DataFrame([row(),row()],index=pd.to_datetime(dates))}
        detail=[{"name":"gold","mtf_rows":view()["mtf_rows"],"verdict":view()["verdict"]}]
        result=attach_asset_reads(detail,frames,[{"key":"gold",**view()}],config.load()["commodities"])
        assert result["gold"]["state"]=="incomplete"


def test_core_asset_does_not_borrow_another_assets_model():
    import pandas as pd
    from lib import config
    frames={"gold":pd.DataFrame([row()],index=pd.to_datetime(["2026-09-15"]))}
    detail=[{"name":"gold","mtf_rows":view()["mtf_rows"],"verdict":view()["verdict"]}]
    result=attach_asset_reads(detail,frames,[{"key":"oil",**view()}],config.load()["commodities"])
    assert result["gold"]["model_action"] is None
    assert result["gold"]["state"]=="incomplete"


def test_price_gap_is_visible_even_when_signal_row_is_newer():
    import pandas as pd
    from lib import config
    old,new=row(),row();new["close"]=float("nan")
    frame=pd.DataFrame([old,new],index=pd.to_datetime(["2026-09-14","2026-09-15"]))
    detail=[{"name":"gold","mtf_rows":view()["mtf_rows"],"verdict":view()["verdict"]}]
    result=attach_asset_reads(detail,{"gold":frame},[{"key":"gold",**view()}],config.load()["commodities"])
    assert result["gold"]["state"]=="incomplete"
    assert result["gold"]["price_asof"]=="2026-09-14"


@pytest.mark.parametrize("grade",["WAIT","CAUTION","BUY-THE-DIP","DON'T CHASE","AVOID"])
def test_asset_summary_cannot_overrule_existing_timeframe_verdict(grade):
    display=view();display["verdict"]["grade"]=grade
    result=read(display=display)
    assert result["state"]!="positive"
    assert result["timing_grade"]==grade


def test_missing_timeframe_verdict_is_not_positive_clearance():
    display=view();display.pop("verdict")
    assert read(display=display)["state"]=="incomplete"



def test_fixture_split_uses_actual_projection_and_preserves_policy_disagreement():
    from scripts.capture_commodity_asset_read_evidence import fixture_context
    context=fixture_context("split")
    reads=context["vm"]["asset_reads"]
    assert reads["gold"]["state"]=="defensive"
    assert reads["gold"]["exposure_pct"]==0
    assert reads["silver"]["state"]=="mixed"
    assert reads["oil"]["state"]=="positive"
    assert reads["oil"]["exposure_pct"]==100
    assert all(r["new_entry_permission"] is None for r in reads.values())


@pytest.mark.parametrize("scenario,state",[("incomplete","incomplete"),("lagging","lagging")])
def test_fixture_degraded_states_are_derived_not_hardcoded(scenario,state):
    from scripts.capture_commodity_asset_read_evidence import fixture_context
    assert fixture_context(scenario)["vm"]["asset_reads"]["gold"]["state"]==state


def test_real_template_renders_asset_reads_and_missing_target_honestly():
    from scripts.capture_commodity_asset_read_evidence import fixture_context
    from scripts.capture_commodities_w6_evidence import render_page
    context=fixture_context("incomplete")
    markup=render_page(context)
    assert 'data-asset-read="gold" data-read-state="incomplete"' in markup
    assert 'Model exposure' in markup and 'Signal date' in markup
    assert 'None%' not in markup and 'nan%' not in markup
    assert 'asset-read-open' in markup


def test_asset_read_component_escapes_instrument_text():
    from scripts.capture_commodity_asset_read_evidence import fixture_context
    from scripts.capture_commodities_w6_evidence import render_page
    context=fixture_context("split")
    context["vm"]["asset_reads"]["gold"]["instrument"]='<script>alert(1)</script>'
    markup=render_page(context)
    assert '<script>alert(1)</script>' not in markup
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in markup


@pytest.mark.parametrize("target",[0.25,0.5,1.0])
def test_negative_model_label_with_positive_target_is_disclosed(target):
    r=row();r["alloc_optimal"]=target
    result=read(r,view("SELL"))
    assert result["state"]=="mixed"
    assert result["exposure_pct"]==target*100
    assert "policy_disagreement" in result["reason_codes"]


@pytest.mark.parametrize("target,expected",[(None,None),(float("nan"),None),(0.0,0),(0.5,50),(1.0,100)])
def test_real_asset_vm_preserves_nullable_exposure(target,expected):
    from tests.test_commodity_signals import _price, _drivers
    from engine import commodity_signals
    from scripts import build_commodities as builder
    px=_price(n=900)
    frame=commodity_signals.compute_asset({"asset":"gold","price":px,"drivers":_drivers(px.index)})
    frame["alloc_optimal"]=frame["alloc_optimal"].astype(object)
    frame.loc[frame.index[-1],"alloc_optimal"]=target
    result=builder.asset_vm("gold",frame,{"assets":{},"meta":{}})
    assert result["alloc_pct"] == expected



def test_hub_loader_keeps_canonical_asset_reads(tmp_path,monkeypatch):
    from scripts import build_vector as hub
    data=tmp_path/"data"; (data/"commodity").mkdir(parents=True)
    payload={"regime":"Stagflation","favored":["gold","silver"],"date":"Sep 15, 2026",
             "asset_reads":{"gold":read()}}
    (data/"commodity/latest.json").write_text(json.dumps(payload))
    (tmp_path/"site").mkdir();(tmp_path/"site/commodities.html").write_text("page")
    monkeypatch.setattr(hub.config,"load",lambda:{"storage":{"site_dir":"site"}})
    monkeypatch.setattr(hub.config,"data_dir",lambda:data)
    monkeypatch.setattr(hub.config,"ROOT",tmp_path)
    state=hub._commodities_state()
    assert state["asset_reads"]==payload["asset_reads"]
    assert state["present"]


def test_hub_renders_asset_evidence_not_regime_favored_list():
    from scripts import build_vector as hub
    vm={"risk_on":False,"risk_index":80,"risk_word":"High","momentum":-0.2}
    r=row();r["alloc_optimal"]=0
    gold=read(r,view("SELL",("D","3D")))
    payload={"label":"Stagflation","favored":["gold","silver"],"asset_reads":{"gold":gold}}
    markup=hub._g_vectors(vm,payload,{},{},{},{},{},{})
    assert 'data-commodity-asset="gold"' in markup
    assert 'Defensive model posture' in markup
    assert '2026-09-15' in markup
    assert 'Favored:' not in markup


def test_hub_missing_or_foreign_asset_read_is_unavailable():
    from scripts import build_vector as hub
    wrong=read();wrong["asset"]="oil"
    for raw in ({}, {"asset_reads":None}, {"asset_reads":{"gold":wrong}}):
        markup=hub._commodity_asset_chips(raw)
        assert 'Gold: Evidence unavailable' in markup
        assert 'Positive model posture' not in markup
        assert 'Favored:' not in markup


def test_hub_asset_labels_escape_untrusted_text():
    from scripts import build_vector as hub
    gold=read();gold["title_en"]='<script>alert(1)</script>'
    markup=hub._commodity_asset_chips({"asset_reads":{"gold":gold}})
    assert '<script>alert(1)</script>' not in markup
    assert '&lt;script&gt;' in markup


def test_hub_never_infers_an_asset_from_the_sector_label():
    from scripts import build_vector as hub
    markup=hub._commodity_asset_chips({"label":"Reflation","favored":["gold","silver"]})
    assert markup.count('Evidence unavailable')==4
    assert 'Reflation' not in markup



def test_asset_read_invariants_across_the_nominal_policy_grid():
    from itertools import product
    count=0
    for action,target,risk,momentum,day,three,timing in product(
        ("BUY","HOLD","SELL"),(0.0,0.5,1.0),("low_risk","high_risk"),
        ("bull","neutral","bear"),("up","flat","down"),("up","flat","down"),
        ("TREND-FOLLOW","WAIT","AVOID")):
        r=row();r.update(alloc_optimal=target,risk_regime=risk,momentum_state=momentum)
        d=view(action);d["mtf_rows"][0]["trend"]=day;d["mtf_rows"][1]["trend"]=three
        d["verdict"]["grade"]=timing
        result=read(r,d)
        assert result["new_entry_permission"] is None
        assert result["exposure_pct"]==100*target
        if (action=="BUY" and target==0) or (action=="SELL" and target>0):
            assert result["state"]=="mixed" and "policy_disagreement" in result["reason_codes"]
        if result["state"]=="positive":
            assert action=="BUY" and target>0 and risk=="low_risk"
            assert momentum=="bull" and day==three=="up" and timing=="TREND-FOLLOW"
        count+=1
    assert count==1458


@pytest.mark.parametrize("value", [None, "", [], {}, True])
def test_invalid_asset_name_returns_incomplete_without_exception(value):
    result=build_asset_read(value,row(),view(),signal_asof="2026-09-15",
                            price_asof="2026-09-15",reference_asof="2026-09-15",instrument="GC=F")
    assert result["state"]=="incomplete"
    assert result["new_entry_permission"] is None

@pytest.mark.parametrize("field", ["risk_regime","momentum_state","ts_trend"])
def test_nullable_enum_scalar_is_missing_not_an_exception(field):
    import pandas as pd
    values=row();values[field]=pd.NA
    assert read(values)["state"]=="incomplete"

@pytest.mark.parametrize("container", [True, 17, 2.5])
def test_scalar_timeframe_container_is_incomplete_not_a_crash(container):
    display=view();display["mtf_rows"]=container
    assert read(display=display)["state"]=="incomplete"

@pytest.mark.parametrize("bad_record", [None, True, "not a timeframe", 5])
def test_corrupt_record_cannot_be_ignored_to_claim_alignment(bad_record):
    display=view();display["mtf_rows"].append(bad_record)
    assert read(display=display)["state"]=="incomplete"


def test_cross_asset_identity_in_source_row_is_incomplete():
    values=row();values["asset"]="silver"
    assert read(values)["state"]=="incomplete"


def test_cross_asset_identity_in_detail_is_incomplete():
    display=view();display["name"]="silver"
    assert read(display=display)["state"]=="incomplete"


def test_huge_integer_exposure_does_not_escape_numeric_validation():
    assert exposure_percent(10**400) is None


def test_matching_optional_source_identities_preserve_values():
    values=row();values["asset"]="gold";display=view();display["name"]="gold"
    actual=read(values,display)
    assert actual["state"]=="positive" and actual["exposure_pct"]==50


@pytest.mark.parametrize("kind", ["nullable", "vector"])
def test_nullable_or_vector_asset_names_stay_incomplete(kind):
    import pandas as pd
    import numpy as np
    name=pd.NA if kind=="nullable" else np.array(["gold","silver"])
    values=row();values["asset"]="gold";display=view();display["name"]="gold"
    result=build_asset_read(name,values,display,signal_asof="2026-09-15",
                            price_asof="2026-09-15",reference_asof="2026-09-15",instrument="GC=F")
    assert result["state"]=="incomplete" and result["asset"] is None
    json.dumps(result,allow_nan=False)


def test_invalid_scalar_matrix_fails_closed_without_mutation():
    import pandas as pd
    import numpy as np
    values=[None,True,False,0,1.5,"unknown",{},[],["up"],pd.NA,np.array(["up","down"])]
    count=0
    for target in ("name","risk_regime","momentum_state","ts_trend","mtf_rows",
                   "frame_key","frame_trend","model_action","row_identity","view_identity"):
        for value in values:
            r=row();r["asset"]="gold";v=view();v["name"]="gold";name="gold"
            if target=="name": name=value
            elif target in ("risk_regime","momentum_state","ts_trend"):r[target]=value
            elif target=="mtf_rows":v[target]=value
            elif target=="frame_key":v["mtf_rows"][0]["key"]=value
            elif target=="frame_trend":v["mtf_rows"][0]["trend"]=value
            elif target=="model_action":v["conviction"]["action"]=value
            elif target=="row_identity":r["asset"]=value
            else:v["name"]=value
            before=(repr(r),repr(v))
            result=build_asset_read(name,r,v,signal_asof="2026-09-15",price_asof="2026-09-15",
                                    reference_asof="2026-09-15",instrument="GC=F")
            assert result["state"]=="incomplete", (target,type(value).__name__)
            assert result["new_entry_permission"] is None
            assert before==(repr(r),repr(v))
            json.dumps(result,allow_nan=False)
            count+=1
    assert count==110


@pytest.mark.parametrize("bad", [float("inf"),float("-inf"),True,False,"100",None,float("nan")])
def test_nonfinite_price_cannot_advance_observation_clock(bad):
    import pandas as pd
    dates=pd.to_datetime(["2026-09-14","2026-09-15"])
    frame=pd.DataFrame([row(),row()],index=dates)
    frame["close"]=pd.Series([100.,bad],index=dates,dtype=object)
    d={"name":"gold",**view()};assets=[{"key":"gold","conviction":view()["conviction"]}]
    result=attach_asset_reads([d],{"gold":frame},assets,{"assets":{"gold":["GC=F"]}})["gold"]
    assert result["price_asof"]=="2026-09-14"
    assert result["signal_asof"]=="2026-09-15"
    assert result["state"]=="incomplete"

@pytest.mark.parametrize("price", [0.,-1.,100.])
def test_finite_price_clock_is_preserved_without_directional_filter(price):
    import pandas as pd
    frame=pd.DataFrame([{**row(),"close":price}],index=pd.to_datetime(["2026-09-15"]))
    d={"name":"gold",**view()};assets=[{"key":"gold","conviction":view()["conviction"]}]
    result=attach_asset_reads([d],{"gold":frame},assets,{"assets":{"gold":["GC=F"]}})["gold"]
    assert result["price_asof"]=="2026-09-15"
    assert result["state"]=="positive" and result["exposure_pct"]==50



def test_full_page_capture_wires_requested_width_and_overlay_check():
    import inspect
    from scripts.capture_commodity_asset_read_evidence import main
    code=inspect.getsource(main)
    assert '--full-page' in code
    assert 'owner.assert_document_fits(document_geometry)' in code
    assert 'document_geometry["viewport_width"] = width' in code
    assert 'page.evaluate(owner._OVERLAY_PROBE.strip())' in code
    assert code.index('owner.assert_document_fits(document_geometry)') < code.index('page.screenshot(full_page=True')


def test_full_page_capture_discloses_fixture_limits_and_preserves_component_mode():
    import inspect
    from scripts.capture_commodity_asset_read_evidence import main
    code=inspect.getsource(main)
    assert 'touch=args.full_page and width==390' in code
    assert 'section.screenshot(type="png")' in code
    assert 'Whole-page synthetic fixture' in code
    assert 'not production' in code


# Calibration is evidence about the parameter source, never win probability.
def _calibration(asset="gold", reliable=True):
    return {"meta":{"horizons":[63,126],"method":"split-half forward-return calibration"},
            "assets":{asset:{"weights":{"trend":0.6,"real_rates":0.4},"score_reliable":reliable}}}


def _calibration_evidence(value, asset="gold"):
    from scripts import commodity_asset_read as projection
    assert hasattr(projection, "calibration_evidence"), "parameter-source evidence is missing"
    return projection.calibration_evidence(asset,value)


def test_empty_calibration_is_not_reliable_by_default():
    result=_calibration_evidence({})
    assert result["status"]=="defaults"
    assert result["declared_reliable"] is None
    assert result["horizons_bars"]==[]


@pytest.mark.parametrize("reliable,status",[(True,"stored"),(False,"weak"),(None,"unrated")])
def test_calibration_discloses_declared_quality_without_promoting_it(reliable,status):
    result=_calibration_evidence(_calibration(reliable=reliable))
    assert result["status"]==status
    assert result["horizons_bars"]==[63,126]
    assert result["declared_reliable"] is reliable
    assert "win probability" in result["disclosure_en"].lower()


def test_calibration_never_borrows_another_assets_parameters():
    assert _calibration_evidence(_calibration(asset="silver"))["status"]=="defaults"


@pytest.mark.parametrize("bad",[True,[],"bad",17])
def test_invalid_calibration_container_is_unavailable(bad):
    assert _calibration_evidence(bad)["status"]=="unavailable"


def test_calibration_horizons_are_declared_positive_integer_bars():
    cal=_calibration();cal["meta"]["horizons"]=[True,63,"126",None,-1,0,float("inf"),126,63]
    assert _calibration_evidence(cal)["horizons_bars"]==[63,126]


def test_calibration_metadata_does_not_mutate_weights():
    cal=_calibration();before=deepcopy(cal)
    _calibration_evidence(cal)
    assert cal==before


def test_projection_carries_calibration_but_preserves_numerical_values():
    d=view();d["conviction"]["reliable"]=True
    d["conviction"]["calibration_evidence"]=_calibration_evidence({})
    result=read(display=d)
    assert result["model_evidence"]["status"]=="defaults"
    assert result["model_score"]==30 and result["exposure_pct"]==50
    assert result["model_action"]=="BUY" and result["new_entry_permission"] is None


def test_projection_does_not_treat_old_reliable_flag_as_calibration_receipt():
    d=view();d["conviction"]["reliable"]=True
    result=read(display=d)
    assert result["model_evidence"]["status"]=="unavailable"


def test_projection_rejects_foreign_calibration_receipt():
    d=view();d["conviction"]["calibration_evidence"]=_calibration_evidence(_calibration("silver"),"silver")
    assert read(display=d)["model_evidence"]["status"]=="unavailable"


def test_projection_does_not_forward_untrusted_calibration_copy():
    d=view();e=_calibration_evidence(_calibration());e["label_en"]="Guaranteed winner"
    d["conviction"]["calibration_evidence"]=e
    assert "Guaranteed" not in read(display=d)["model_evidence"]["label_en"]


def test_asset_vm_binds_the_same_calibration_used_by_score(monkeypatch):
    from tests.test_commodity_signals import _price,_drivers
    from engine import commodity_signals,commodity_conviction
    from scripts import build_commodities as builder
    px=_price(n=900);drivers=_drivers(px.index)
    frame=commodity_signals.compute_asset({"asset":"gold","price":px,"drivers":drivers})
    cal=_calibration();seen=[]
    numeric={"score":12.25,"action":"BUY","confidence":0.53,"reliable":True}
    def observe(*args):
        seen.append(args[-1]);return dict(numeric)
    monkeypatch.setattr(commodity_conviction,"conviction",observe)
    result=builder.asset_vm("gold",frame,{"assets":{},"meta":{}},drivers,{},cal,None)
    assert seen==[cal] and seen[0] is cal
    assert result["conviction"]["calibration_evidence"]["status"]=="stored"
    assert all(result["conviction"][key]==value for key,value in numeric.items())


def test_asset_vm_resolves_missing_calibration_once(monkeypatch):
    from tests.test_commodity_signals import _price,_drivers
    from engine import commodity_signals,commodity_conviction
    from scripts import build_commodities as builder
    px=_price(n=900);drivers=_drivers(px.index)
    frame=commodity_signals.compute_asset({"asset":"gold","price":px,"drivers":drivers})
    calls=[];cal={}
    monkeypatch.setattr(commodity_conviction,"load_calibration",lambda:(calls.append("load") or cal))
    monkeypatch.setattr(commodity_conviction,"conviction",lambda *args:{"score":0,"action":"HOLD","confidence":0.5,"reliable":True})
    result=builder.asset_vm("gold",frame,{"assets":{},"meta":{}},drivers,{},None,None)
    assert calls==["load"]
    assert result["conviction"]["calibration_evidence"]["status"]=="defaults"


def test_card_and_detail_expose_calibration_as_separate_evidence():
    from pathlib import Path
    base=Path(__file__).resolve().parents[1]
    for path in ("templates/_commodity_asset_read.html.j2","templates/commodities.html.j2"):
        text=(base/path).read_text()
        assert "data-model-evidence" in text and "horizons_bars" in text


def test_hub_shows_parameter_origin_without_recomputing_score():
    from scripts import build_vector as hub
    d=view();d["conviction"]["calibration_evidence"]=_calibration_evidence({})
    gold=read(display=d)
    text=hub._commodity_asset_chips({"asset_reads":{"gold":gold}})
    assert "Default parameters" in text
    assert "Positive model posture" in text


@pytest.mark.parametrize("kind", ["nullable", "vector", "bool", "string", "nan", "zero"])
def test_malformed_calibration_weights_are_unavailable_not_assumed(kind):
    import numpy as np
    import pandas as pd
    cal = _calibration()
    values = {"nullable": pd.NA, "vector": np.array([1,2]), "bool": True,
              "string": "0.6", "nan": {"trend": float("nan")}, "zero": {"trend":0}}
    cal["assets"]["gold"]["weights"] = values[kind]
    assert _calibration_evidence(cal)["status"] == "unavailable"


def test_calibration_fixture_discloses_all_sources_without_changing_policy():
    from scripts.capture_commodity_asset_read_evidence import fixture_context
    base = fixture_context("split")["vm"]["asset_reads"]
    actual = fixture_context("calibration")["vm"]["asset_reads"]
    for asset,status in {"gold":"weak","silver":"stored","copper":"defaults","oil":"unrated"}.items():
        assert actual[asset]["model_evidence"]["status"] == status
        for field in ("state","exposure_pct","model_score","model_action","signal_asof","new_entry_permission"):
            assert actual[asset][field] == base[asset][field]


def test_capture_exercises_calibration_disclosure_and_detail_identity():
    import inspect
    from scripts.capture_commodity_asset_read_evidence import main
    source = inspect.getsource(main)
    assert '"--include-calibration"' in source
    assert 'calibration_details_verified' in source
    assert 'card_evidence.locator("summary").click()' in source
    assert 'detail_evidence.get_attribute("data-model-evidence")' in source


@pytest.mark.parametrize("target", ["schema", "asset", "argument"])
@pytest.mark.parametrize("kind", ["nullable", "vector"])
def test_model_evidence_qualifies_nonscalar_identity_before_comparing(target,kind):
    import pandas as pd
    import numpy as np
    from scripts.commodity_asset_read import model_evidence_read
    receipt = _calibration_evidence(_calibration())
    value = pd.NA if kind == "nullable" else np.array(["gold","silver"])
    asset = "gold"
    if target == "argument": asset = value
    else: receipt[target] = value
    result = model_evidence_read(asset,receipt)
    assert result["status"] == "unavailable"
    json.dumps(result,allow_nan=False)
