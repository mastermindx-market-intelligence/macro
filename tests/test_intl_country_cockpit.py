"""Country interpretation: economic meaning, independent clocks and failure isolation."""
from copy import deepcopy
from datetime import date
import csv
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader
from engine import i18n
from engine.intl_equity_risk import equity_risk_all
from lib.intl_country_assessment import build_country_assessments
from lib.intl_country_inputs import load_country_inputs
from collectors.intl_country_sources import parse_bis, collect_country_inputs, merge_country_inputs, SCHEMA

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 18)


def record(cc="KR"):
    return {"cc":cc,"date":"2026-10-18","macro":{"policy_rate":99,"cpi_yoy":-0.5,"gdp_yoy":2.1},
            "macro_asof":{"cpi_yoy":"2021-06","gdp":"2026-04"},
            "equity":{"as_of":"2026-10-15","above_50d":False,"above_200d":False,
                      "trend_200d_complete":True,"off_52w_high":-39.2,
                      "high_window_observations":252,"high_window_start":"2025-10-15"}}


def forecast(cc="KR", **changes):
    value={"cc":cc,"kind":"sourced_forecast","provider":"IMF",
           "source_url":"https://www.imf.org/en/Publications/WEO","published":"2026-07-08",
           "unit":"percent","period_basis":"calendar_year",
           "values":{"2026":2.6,"2027":2.5},"revision_current_pp":0.7,"revision_from":"2026-04"}
    value.update(changes)
    return value


def observation(key="inflation", **changes):
    value={"metric":key,"value":2.79,"period":"2026-07","unit":"% y/y",
           "provider":"Bank for International Settlements","source_url":"https://data.bis.org/topics/CPI",
           "status":"observed","change_3m_pp":0.22}
    value.update(changes)
    return value


def view(rec=None, official=None, forecasts=None, commentary=None):
    return build_country_assessments({"date":"2026-10-18","records":[rec or record()]},
                                    today=TODAY,official=official,forecasts=forecasts,
                                    commentary=commentary)["countries"][0]


def test_forecast_and_price_pressure_are_distinct():
    c=view(forecasts={"KR":forecast()})
    assert c["market"]["state"]=="pressure"
    assert c["forecast"]["current"]==2.6
    assert c["forecast"]["revision"]==0.7
    assert "2026-04" in c["read_en"]
    assert "confirmation" not in c["title_en"].lower()
    assert "recovery" not in c["read_en"].lower()


def test_page_date_cannot_refresh_an_instrument():
    rec=record()
    rec["equity"]["as_of"]="2026-07-01"
    c=view(rec)
    assert c["market"]["state"]=="unknown"
    assert c["market"]["drawdown"] is None
    rec["equity"].pop("as_of")
    assert view(rec)["market"]["current"] is False


def test_insufficient_long_trend_does_not_mean_bearish():
    rec=record();rec["equity"]["trend_200d_complete"]=False
    assert view(rec)["market"]["state"]=="unknown"


def test_legacy_short_rate_proxy_never_becomes_policy_rate():
    policy=next(m for m in view()["metrics"] if m["key"]=="policy")
    assert policy["value"] is None


def test_stale_observation_keeps_date_and_is_not_current():
    inflation=next(m for m in view()["metrics"] if m["key"]=="inflation")
    assert inflation["value"]==-0.5 and inflation["period"]=="2021-06"
    assert inflation["quality"]=="dated"
    assert inflation["current"] is False


@pytest.mark.parametrize("value",[True,float("nan"),float("inf"),10**500])
def test_invalid_numerics_do_not_escape_into_observations(value):
    c=view(official={"KR":{"inflation":observation(value=value)}})
    assert next(m for m in c["metrics"] if m["key"]=="inflation")["value"] is None


@pytest.mark.parametrize("changes",[{"unit":"index"},{"metric":"policy"},{"status":"estimated"},
                                    {"source_url":"javascript:alert(1)"},{"source_url":"https://[invalid"}])
def test_wrong_measure_or_source_is_withheld(changes):
    c=view(official={"KR":{"inflation":observation(**changes)}})
    assert next(m for m in c["metrics"] if m["key"]=="inflation")["value"] is None


def test_future_observation_is_not_current():
    c=view(official={"KR":{"inflation":observation(period="2026-12")}})
    assert not next(m for m in c["metrics"] if m["key"]=="inflation")["current"]


@pytest.mark.parametrize("published",["2026-10-19","2025-01-01"])
def test_forecast_vintage_is_checked(published):
    assert view(forecasts={"KR":forecast(published=published)})["forecast"] is None


def test_fiscal_basis_survives_without_calendar_relabel():
    c=view(record("IN"), forecasts={"IN":forecast("IN",period_basis="fiscal_year")})
    assert c["forecast"]["period_basis"]=="fiscal_year"
    assert "FY2026" in c["read_en"]


def test_contraction_cannot_be_called_slower_expansion():
    c=view(forecasts={"KR":forecast(values={"2026":1.0,"2027":-0.8})})
    assert c["forecast"]["path_en"]=="Contraction projected"
    assert "contraction" in c["title_en"].lower()


def test_fx_requires_its_own_clock():
    rec=record();rec["macro"]["fx_strength_3m"]=4.95
    assert view(rec)["market"]["fx_3m"] is None
    rec["macro_asof"]["fx_strength_3m"]="2026-10-14"
    assert view(rec)["market"]["fx_3m"]==4.95


def test_input_is_not_mutated_and_duplicate_countries_fail():
    latest={"records":[record()]}
    before=deepcopy(latest)
    build_country_assessments(latest,today=TODAY,forecasts={"KR":forecast()})
    assert latest==before
    with pytest.raises(ValueError,match="duplicate_country"):
        build_country_assessments({"records":[record(),record()]},today=TODAY)


def test_malformed_optional_nested_data_degrades():
    rec=record();rec.update(macro="bad",macro_asof=4,equity=[])
    c=view(rec)
    assert c["market"]["state"]=="unknown"
    assert all(m["value"] is None for m in c["metrics"])


def test_new_engine_clocks_follow_each_actual_series():
    dates=pd.bdate_range("2025-01-01",periods=270)
    frame=pd.DataFrame({"JP":range(100,370),"KR":range(200,470)},index=dates,dtype=float)
    frame.loc[dates[-1],"KR"]=float("nan")
    risks=equity_risk_all(frame)
    assert risks["JP"]["as_of"]==str(dates[-1].date())
    assert risks["KR"]["as_of"]==str(dates[-2].date())
    assert risks["KR"]["high_window_observations"]==252
    assert risks["KR"]["high_window_start"]==str(dates[-253].date())
    assert risks["KR"]["trend_200d_complete"]
    assert not equity_risk_all(frame.iloc[:120])["KR"]["trend_200d_complete"]


HEADERS=["STRUCTURE_ID","FREQ:Frequency","REF_AREA:Reference area",
         "TIME_PERIOD:Time period or range","OBS_VALUE:Observation Value",
         "UNIT_MEASURE:Unit of measure","UNIT_MULT:Unit Multiplier",
         "OBS_CONF:Observation confidentiality","OBS_STATUS:Observation Status"]


def bis_archive(rows,kind="inflation"):
    dataset="WS_LONG_CPI" if kind=="inflation" else "WS_CBPOL"
    stream=io.StringIO();writer=csv.writer(stream);writer.writerow(HEADERS)
    for overrides in rows:
        item={"STRUCTURE_ID":"BIS:"+dataset+"(1.0):M.KR","FREQ:Frequency":"M:Monthly",
              "REF_AREA:Reference area":"KR:Korea","TIME_PERIOD:Time period or range":"2026-07",
              "OBS_VALUE:Observation Value":"2.79","UNIT_MEASURE:Unit of measure":"771",
              "UNIT_MULT:Unit Multiplier":"0","OBS_CONF:Observation confidentiality":"F",
              "OBS_STATUS:Observation Status":"A"}
        item.update(overrides);writer.writerow([item[k] for k in HEADERS])
    buffer=io.BytesIO()
    with ZipFile(buffer,"w") as archive:archive.writestr(dataset+"_csv_flat.csv",stream.getvalue())
    return buffer.getvalue()


def test_bis_uses_three_calendar_months_not_previous_row():
    rows=[{"TIME_PERIOD:Time period or range":"2026-03","OBS_VALUE:Observation Value":"2.0"},
          {"TIME_PERIOD:Time period or range":"2026-04","OBS_VALUE:Observation Value":"2.57"},{}]
    item=parse_bis(bis_archive(rows),"inflation",retrieved_at="2026-10-18")["observations"]["KR"]
    assert item["period"]=="2026-07" and item["change_3m_pp"]==0.22
    rows.pop(1)
    assert parse_bis(bis_archive(rows),"inflation",retrieved_at="2026-10-18")["observations"]["KR"]["change_3m_pp"] is None


@pytest.mark.parametrize("override",[{"OBS_CONF:Observation confidentiality":"C"},
                                    {"OBS_STATUS:Observation Status":"E"},
                                    {"UNIT_MEASURE:Unit of measure":"index"},
                                    {"TIME_PERIOD:Time period or range":"2026-10"}])
def test_bis_rejects_nonpublic_wrong_units_and_unfinished_months(override):
    assert not parse_bis(bis_archive([override]),"inflation",retrieved_at="2026-10-18")["observations"]


def test_conflicting_source_observation_is_rejected():
    with pytest.raises(ValueError,match="conflicting"):
        parse_bis(bis_archive([{},{"OBS_VALUE:Observation Value":"9.5"}]),"inflation",retrieved_at="2026-10-18")


def test_bad_archive_does_not_stop_other_sources():
    result=collect_country_inputs(lambda url,**kw:b"invalid",retrieved_at="2026-10-18")
    assert len(result["errors"])==4
    assert result["official"]=={} and result["forecasts"]=={}


def test_partial_refresh_retains_unrelated_vintages_and_newer_release():
    previous={"schema":SCHEMA,"official":{"KR":{"inflation":observation()}},"forecasts":{"KR":forecast()}}
    incoming={"schema":SCHEMA,"official":{"KR":{"policy":observation("policy",unit="%",period="2026-09")}},
              "forecasts":{"KR":forecast(published="2026-04-14")},"errors":[{"source":"imf","error":"HTTPError"}]}
    before=deepcopy(previous);result=merge_country_inputs(previous,incoming)
    assert result["official"]["KR"]["inflation"]["period"]=="2026-07"
    assert result["official"]["KR"]["policy"]["period"]=="2026-09"
    assert result["forecasts"]["KR"]["published"]=="2026-07-08"
    assert previous==before


def test_expired_commentary_cannot_supply_a_current_country_thesis():
    commentary=json.loads((ROOT/"config/intl_country_commentary.json").read_text())["countries"]
    commentary["KR"]["published"]="2025-01-01"
    assert view(commentary=commentary)["research"] is None


def test_country_template_has_complete_native_content():
    source=load_country_inputs(ROOT/"data",ROOT)
    model=build_country_assessments({"records":[record()]},today=TODAY,
                                  official=source["official"],forecasts=source["forecasts"],
                                  commentary=source["commentary"])
    env=Environment(loader=FileSystemLoader(ROOT/"templates"))
    env.globals.update(t=i18n.t,td=i18n.td,tr=i18n.tr)
    html=env.get_template("intl_country_cockpit.html.j2").render(intl_analysis=model)
    assert 'id="imc-country-KR"' in html
    assert "Export strength meets higher rates" in html
    assert "Bank of Korea" in html and "2026-09-10" in html
    assert "From recent high" in html
    assert "52-week high" not in html
    assert "Saved research" not in html


@pytest.mark.parametrize("section", ["official", "forecasts"])
@pytest.mark.parametrize("malformed", [[], "invalid", 42, None])
def test_malformed_refresh_sections_cannot_destroy_last_good_sources(section, malformed):
    previous = {"schema": SCHEMA, "official": {"KR": {"inflation": observation()}},
                "forecasts": {"KR": forecast()}}
    result = merge_country_inputs(previous, {"schema": SCHEMA, section: malformed})
    assert result["official"]["KR"]["inflation"] == previous["official"]["KR"]["inflation"]
    assert result["forecasts"]["KR"] == previous["forecasts"]["KR"]


def test_newer_malformed_values_cannot_displace_valid_source_vintage():
    previous = {"schema": SCHEMA, "official": {"KR": {"inflation": observation()}},
                "forecasts": {"KR": forecast()}}
    incoming = {"schema": SCHEMA,
                "official": {"KR": {"inflation": observation(value=True, period="2026-09")}},
                "forecasts": {"KR": forecast(published="2026-10-01", values={"2026": 2.0, "2027": None})}}
    result = merge_country_inputs(previous, incoming)
    assert result["official"]["KR"]["inflation"] == previous["official"]["KR"]["inflation"]
    assert result["forecasts"]["KR"] == previous["forecasts"]["KR"]


def test_input_loader_contains_malformed_nested_json(tmp_path):
    config = tmp_path / "config"
    config.mkdir()
    (config / "intl_country_baseline.json").write_text(json.dumps({
        "schema": SCHEMA, "official": ["invalid"], "forecasts": {"KR": "invalid"}
    }))
    inputs = load_country_inputs(tmp_path / "data", tmp_path)
    result = build_country_assessments({"records": [record()]}, today=TODAY,
                                      official=inputs["official"], forecasts=inputs["forecasts"])
    assert len(result["countries"]) == 1
