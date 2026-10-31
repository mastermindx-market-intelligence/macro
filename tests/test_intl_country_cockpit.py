"""Country interpretation: economic meaning, independent clocks and failure isolation."""
from copy import deepcopy
from datetime import date
from math import fsum
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
from lib.intl_country_inputs import (
    load_country_inputs, load_stored_country_observations, stored_observation_view,
    equity_source_for, EQUITY_OBSERVATION_SCHEMA,
)
from collectors.intl_country_sources import parse_bis, collect_country_inputs, merge_country_inputs, SCHEMA

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 18)


def record(cc="KR"):
    # Synthetic but fully traceable contract fixture; no live Yahoo fetch claimed.
    dates = pd.bdate_range(end="2026-10-15", periods=252)
    rows = [[stamp.date().isoformat(), 250.0] for stamp in dates]
    rows[-1][1] = 152.0

    def mean_window(target, minimum):
        window = rows[-target:]
        return {"method": "arithmetic_mean", "target_observations": target,
                "minimum_observations": minimum, "observations": len(window),
                "start": window[0][0], "end": window[-1][0],
                "value": fsum(row[1] for row in window) / len(window)}

    evidence = {
        "schema": EQUITY_OBSERVATION_SCHEMA, "source": equity_source_for(cc),
        "as_of": rows[-1][0], "rows": rows, "latest_close": 152.0,
        "mean_50": mean_window(50, 25), "mean_200": mean_window(200, 100),
        "recent_high": {"method": "maximum", "target_observations": 252,
                        "minimum_observations": 60, "observations": 252,
                        "start": rows[0][0], "end": rows[-1][0], "value": 250.0,
                        "high_date": rows[-2][0], "tie_policy": "most_recent"},
    }
    return {"cc":cc,"date":"2026-10-18","macro":{"policy_rate":99,"cpi_yoy":-0.5,"gdp_yoy":2.1},
            "macro_asof":{"cpi_yoy":"2021-06","gdp":"2026-04"},
            "equity":{"as_of":rows[-1][0],"price":152.0,"above_50d":False,"above_200d":False,
                      "trend_200d_complete":True,"off_52w_high":-39.2,
                      "high_window_observations":252,"high_window_start":rows[0][0],
                      "observation_evidence": evidence}}


def forecast(cc="KR", **changes):
    value={"cc":cc,"kind":"sourced_forecast","provider":"IMF",
           "source_url":"https://www.imf.org/en/Publications/WEO","published":"2026-07-08",
           "retrieved_at":"2026-10-18T00:00:00+00:00","first_observed_at":"2026-10-18T00:00:00+00:00","admitted_at":"2026-10-18T00:00:00+00:00",
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


def view(rec=None, official=None, forecasts=None, commentary=None, stored_observations=None):
    return build_country_assessments({"date":"2026-10-18","records":[rec or record()]},
                                    today=TODAY,official=official,forecasts=forecasts,
                                    commentary=commentary, stored_observations=stored_observations)["countries"][0]


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
    country = view(official={"KR": {"inflation": observation(value=-0.5, period="2021-06")}})
    inflation=next(m for m in country["metrics"] if m["key"]=="inflation")
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


def test_legacy_fx_score_is_not_a_currency_return():
    rec=record();rec["macro"]["fx_strength_3m"]=4.95
    assert view(rec)["market"]["fx_3m"] is None
    rec["macro_asof"]["fx_strength_3m"]="2026-10-14"
    assert view(rec)["market"]["fx_3m"] is None


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
    from collectors.intl_policy_sources import RELEASES
    policy_errors = [error for error in result["errors"] if error.get("status") == "release_not_verified"]
    assert {error["source_url"] for error in policy_errors} == {release["source_url"] for release in RELEASES}
    assert {"inflation", "policy", "imf", "taiwan"} <= {error["source"] for error in result["errors"]}
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
                                  commentary=source["commentary"], forecast_archive=source["forecast_archive"])
    env=Environment(loader=FileSystemLoader(ROOT/"templates"))
    env.globals.update(t=i18n.t,td=i18n.td,tr=i18n.tr)
    html=env.get_template("intl_country_cockpit.html.j2").render(intl_analysis=model)
    assert 'id="imc-country-KR"' in html
    assert "Export strength meets higher rates" in html
    assert "Country thesis based on" in html
    assert "3.3" in html and "2.8" in html
    assert "Inflation path" in html and "Current account" in html
    assert "+0.7" in html and "2026-07" in html
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
    assert all(result["forecasts"]["KR"][key] == previous["forecasts"]["KR"][key]
               for key in ("cc", "provider", "published", "source_url", "unit", "period_basis", "values"))


def test_newer_malformed_values_cannot_displace_valid_source_vintage():
    previous = {"schema": SCHEMA, "official": {"KR": {"inflation": observation()}},
                "forecasts": {"KR": forecast()}}
    incoming = {"schema": SCHEMA,
                "official": {"KR": {"inflation": observation(value=True, period="2026-09")}},
                "forecasts": {"KR": forecast(published="2026-10-01", values={"2026": 2.0, "2027": None})}}
    result = merge_country_inputs(previous, incoming)
    assert result["official"]["KR"]["inflation"] == previous["official"]["KR"]["inflation"]
    assert all(result["forecasts"]["KR"][key] == previous["forecasts"]["KR"][key]
               for key in ("cc", "provider", "published", "source_url", "unit", "period_basis", "values"))


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



def current_policy_model(*, policy_reviews=None, policy_decisions=None):
    base = json.loads((ROOT / "config/intl_country_baseline.json").read_text())
    commentary = json.loads((ROOT / "config/intl_country_commentary.json").read_text())["countries"]
    return build_country_assessments(
        {"records": [record(cc) for cc in ("JP", "KR", "TW", "IN", "AU", "GB", "EZ")]},
        today=date(2026, 10, 19), official=base["official"], forecasts=base["forecasts"],
        forecast_archive=base["forecast_archive"], commentary=commentary,
        policy_decisions=policy_decisions if policy_decisions is not None else base["policy_decisions"],
        policy_reviews=policy_reviews if policy_reviews is not None else base.get("policy_reviews"))


def render_policy_model(model):
    env = Environment(loader=FileSystemLoader(ROOT / "templates"))
    env.globals.update(t=i18n.t, td=i18n.td, tr=i18n.tr)
    return env.get_template("intl_country_cockpit.html.j2").render(intl_analysis=model)


def test_current_country_views_expose_all_seven_named_decisions():
    model = current_policy_model()
    assert len(model["countries"]) == 7
    assert all(c["policy_decision"]["current"] for c in model["countries"])
    assert all(c["research"] is not None for c in model["countries"])
    html = render_policy_model(model)
    for country in model["countries"]:
        policy = country["policy_decision"]
        block = html.split(f'aria-labelledby="imc-policy-{country["cc"]}"', 1)[1].split("</section>", 1)[0]
        assert policy["instrument_en"] in block
        assert policy["decision_date"] in block and policy["effective_date"] in block
        for support in policy.get("supporting_sources", []):
            assert support["label_en"] in block
    jp = html.split('aria-labelledby="imc-policy-JP"', 1)[1].split("</section>", 1)[0]
    assert "imc-policy-qualifier" in jp and "Around" in jp and "around " in jp
    assert "1.25" in jp and "1.00" in jp


def test_source_review_suppresses_the_dependent_national_thesis_and_policy_rationale():
    base = json.loads((ROOT / "config/intl_country_baseline.json").read_text())
    old = next(r for r in base["policy_decisions"] if r["cc"] == "AU")
    event = {**old, "schema": "intl_policy_review.v1", "status": "review_required", "record_id": None,
             "observed_at": "2026-10-19T12:00:00+00:00"}
    model = current_policy_model(policy_reviews=[*base.get("policy_reviews", []), event])
    country = next(c for c in model["countries"] if c["cc"] == "AU")
    assert country["policy_decision"]["state"] == "review_required"
    assert country["research"] is None
    assert country["title_en"] != "Inflation persists as demand cools"
    block = render_policy_model(model).split('aria-labelledby="imc-policy-AU"', 1)[1].split("</section>", 1)[0]
    assert "source needs review" in block
    assert "imc-policy-value" not in block and "imc-policy-rationale" not in block
    assert old["rationale_en"] not in block


def test_first_failed_policy_qualification_withholds_same_bank_commentary():
    base = json.loads((ROOT / "config/intl_country_baseline.json").read_text())
    item = next(r for r in base["policy_decisions"] if r["cc"] == "AU")
    event = {**item, "schema": "intl_policy_review.v1", "status": "review_required",
             "record_id": None, "observed_at": "2026-10-19T12:00:00+00:00"}
    model = current_policy_model(
        policy_decisions=[r for r in base["policy_decisions"] if r["cc"] != "AU"],
        policy_reviews=[event])
    country = next(c for c in model["countries"] if c["cc"] == "AU")
    assert country["research"] is None
    assert country["policy_decision"]["state"] == "review_required"
    block = render_policy_model(model).split('aria-labelledby="imc-policy-AU"', 1)[1].split("</section>", 1)[0]
    assert "source needs review" in block and "imc-policy-value" not in block


def test_new_announcement_retires_older_national_interpretation_before_effective_date():
    from lib.intl_policy_evidence import normalize_policy_decision
    base = json.loads((ROOT / "config/intl_country_baseline.json").read_text())
    item = next(r for r in base["policy_decisions"] if r["cc"] == "GB")
    future = normalize_policy_decision({**item, "value": 4.0, "previous_value": 3.75,
        "action": "increase", "decision_date": "2026-10-15", "published": "2026-10-15",
        "effective_date": "2026-11-01", "last_change_date": "2026-11-01",
        "first_observed_at": "2026-10-19T12:00:00+00:00"})
    assert future is not None
    model = current_policy_model(policy_decisions=[*base["policy_decisions"], future])
    country = next(c for c in model["countries"] if c["cc"] == "GB")
    assert country["policy_decision"]["current"]
    assert country["policy_decision"]["value"] == 3.75
    assert country["research"] is None
    block = render_policy_model(model).split('aria-labelledby="imc-policy-GB"', 1)[1].split("</section>", 1)[0]
    assert "Announced change" in block and "4.00%" in block and "2026-11-01" in block


@pytest.mark.parametrize("withdrawn, heading, heading_zh", [
    (("current_account", "fiscal_balance"), "Fiscal position", "财政状况"),
    (("current_account", "government_debt"), "Fiscal position", "财政状况"),
    (("fiscal_balance",), "External & fiscal position", "外部与财政状况"),
    (("government_debt",), "External & fiscal position", "外部与财政状况"),
    (("fiscal_balance", "government_debt"), "External position", "外部状况"),
])
def test_partial_withdrawal_names_only_the_remaining_and_missing_fiscal_measures(
        withdrawn, heading, heading_zh):
    import re
    from html import unescape
    from lib.intl_forecast_vintages import merge_publications, select_publications

    source = load_country_inputs(ROOT / "data", ROOT)
    as_of = date(2026, 10, 19)
    selected = [series for metric in withdrawn for series in select_publications(
        source["forecast_archive"], "KR", series_id=metric, today=as_of)]
    withdrawals = [{**series, "withdrawn_at": "2026-10-19T23:45:00+00:00",
                    "withdrawal_source_url": "https://www.imf.org/en/withdrawal"}
                   for series in selected if series["series_id"] in withdrawn]
    assert len(withdrawals) == len(withdrawn)
    archive, diagnostics = merge_publications(
        source["forecast_archive"], withdrawals, observed_at="2026-10-19T23:50:00+00:00")
    assert diagnostics == []
    model = build_country_assessments(
        {"records": [record()]}, today=as_of, official=source["official"],
        forecasts=source["forecasts"], commentary=source["commentary"],
        forecast_archive=archive)
    balances = {b["series_id"] for b in model["countries"][0]["outlook"]["balances"]}
    assert balances == {"current_account", "fiscal_balance", "government_debt"} - set(withdrawn)
    env = Environment(loader=FileSystemLoader(ROOT / "templates"))
    env.globals.update(t=i18n.t, td=i18n.td, tr=i18n.tr)
    html = env.get_template("intl_country_cockpit.html.j2").render(intl_analysis=model)
    panel = unescape(re.search(r'<section class="imc-balances"[^>]*>(.*?)</section>', html, re.S).group(1))
    assert heading in panel and heading_zh in panel
    if "current_account" not in balances:
        assert "External position" not in panel and "外部状况" not in panel
    fiscal_missing = set(withdrawn) & {"fiscal_balance", "government_debt"}
    if len(fiscal_missing) == 2:
        assert "Fiscal projections have not been verified for this country." in html
    else:
        assert "Fiscal projections have not been verified for this country." not in html
        if "fiscal_balance" in fiscal_missing:
            assert "A government balance projection has not been verified" in html
            assert "政府财政收支预测尚未核验" in html
            assert "A government debt projection has not been verified" not in html
        else:
            assert "A government debt projection has not been verified" in html
            assert "政府债务预测尚未核验" in html
            assert "A government balance projection has not been verified" not in html


@pytest.mark.parametrize("period", ["2026-12", "2026-10-19", "unknown", None, "2026-13"])
@pytest.mark.parametrize("key", ["inflation", "gdp"])
def test_future_or_unknown_observed_periods_never_display_as_earlier(key, period):
    c = view(official={"KR":{key:observation(key=key, metric=key, period=period)}})
    metric = next(m for m in c["metrics"] if m["key"] == key)
    assert metric["value"] is None
    assert metric["quality"] == "missing" and not metric["current"]


@pytest.mark.parametrize("period", ["2026-12", "2026-10-19", "unknown", None])
def test_anonymous_legacy_gdp_is_withheld_without_changing_legacy_tools(period):
    rec = record()
    rec["macro_asof"]["gdp"] = period
    metric = next(m for m in view(rec)["metrics"] if m["key"] == "gdp")
    assert metric["value"] is None and metric["quality"] == "missing"
    rec["macro_asof"]["gdp"] = "2024-01"
    metric = next(m for m in view(rec)["metrics"] if m["key"] == "gdp")
    assert metric["value"] is None and metric["quality"] == "missing"
    assert rec["macro"]["gdp_yoy"] == 2.1 and rec["macro_asof"]["gdp"] == "2024-01"


def _stored_case(tmp_path, *, cc="JP", metric="gdp", dates=None, values=None):
    """A local collector/store fixture, never a claim about live provider values."""
    root = tmp_path / "data"
    folder = root / "intl_macro"
    folder.mkdir(parents=True, exist_ok=True)
    if dates is None:
        dates = (["2025-04-01", "2025-07-01", "2025-10-01", "2026-01-01", "2026-04-01"]
                 if metric == "gdp" else ["2026-07-01"])
    if values is None:
        values = [100.0, 101.0, 102.0, 103.0, 104.0] if metric == "gdp" else [2.4]
    column = f"{cc}_{metric}"
    frame = pd.DataFrame({column: values}, index=pd.to_datetime(dates))
    frame.to_parquet(folder / (column + ".parquet"))
    ids = {"JP": {"gdp": "JPNRGDPEXP", "unemployment": "LRHUTTTTJPM156S"},
           "KR": {"gdp": "NGDPRSAXDCKRQ", "unemployment": "LRHUTTTTKRM156S"},
           "AU": {"gdp": "NGDPRSAXDCAUQ", "unemployment": "LRHUTTTTAUM156S"},
           "GB": {"gdp": "NGDPRSAXDCGBQ", "unemployment": "LRHUTTTTGBM156S"},
           "EZ": {"gdp": "CLVMNACSCAB1GQEA19"}}
    cfg = {"countries": {cc: {"fred": ids[cc]}},
           "macro": {"fred_base_url": "https://fred.stlouisfed.org/graph/fredgraph.csv"}}
    if (cc, metric) == ("EZ", "unemployment"):
        cfg["macro"]["official_series"] = {"EZ_unemployment": {
            "provider": "eurostat", "dataset": "une_rt_m", "since": "2000-01", "unit": "PC_ACT",
            "params": {"geo": "EA21", "s_adj": "SA", "age": "TOTAL", "unit": "PC_ACT", "sex": "T"}}}
        metadata = {"provider": "eurostat", "source_id": "une_rt_m", "status": "official", "unit": "PC_ACT",
                    "source_url": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_m"
                                  "?lang=en&geo=EA21&s_adj=SA&age=TOTAL&unit=PC_ACT&sex=T&sinceTimePeriod=2000-01"}
    else:
        fid = ids[cc][metric]
        metadata = {"provider": "fred_fallback", "source_id": fid, "unit": None, "status": "fallback",
                    "source_url": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + fid}
    metadata["last_observation"] = dates[-1]
    provenance = {"schema": "intl_macro_provenance.v1", "series": {column: metadata}}
    (folder / "provenance.json").write_text(json.dumps(provenance))
    return root, cfg, provenance


def _rewrite_provenance(root, provenance):
    (root / "intl_macro/provenance.json").write_text(json.dumps(provenance))


def test_stored_gdp_has_actual_quarter_endpoints_without_new_custody(tmp_path):
    root, cfg, provenance = _stored_case(tmp_path)
    path = root / "intl_macro/JP_gdp.parquet"
    original_bytes = path.read_bytes()
    mapping = load_stored_country_observations(root, cfg, today=TODAY)
    gdp = mapping["JP"]["gdp"]
    assert gdp["value"] == pytest.approx(4.0)
    assert (gdp["period"], gdp["period_end"]) == ("2026-Q2", "2026-06-30")
    assert [point["date"] for point in gdp["observations"]] == [
        "2025-04-01", "2025-07-01", "2025-10-01", "2026-01-01", "2026-04-01"]
    assert [point["value"] for point in gdp["observations"]] == [100, 101, 102, 103, 104]
    assert gdp["method"] == "(end / start - 1) * 100"
    assert gdp["source_url"] == "https://fred.stlouisfed.org/series/JPNRGDPEXP"
    assert gdp["native_unit"] == "Billions of chained 2015 yen"
    assert gdp["retrieved_at"] is None and gdp["vintage_custody"] == "not_recorded"
    provenance["series"]["JP_gdp"].update(requested_at="2099-01-01", source_updated="2099-01-01")
    _rewrite_provenance(root, provenance)
    assert load_stored_country_observations(root, cfg, today=TODAY) == mapping
    assert path.read_bytes() == original_bytes
    rec = record("JP")
    original_record = deepcopy(rec)
    metric = next(m for m in view(rec, stored_observations=mapping)["metrics"] if m["key"] == "gdp")
    assert metric["value"] == pytest.approx(4.0) and metric["evidence"] == gdp
    assert metric["period_end"] == "2026-06-30" and rec == original_record


@pytest.mark.parametrize("cc,series", [
    ("JP", "JPNRGDPEXP"), ("KR", "NGDPRSAXDCKRQ"), ("AU", "NGDPRSAXDCAUQ"),
    ("GB", "NGDPRSAXDCGBQ"), ("EZ", "CLVMNACSCAB1GQEA19"),
])
def test_each_gdp_uses_its_actual_configured_series(tmp_path, cc, series):
    root, cfg, _ = _stored_case(tmp_path, cc=cc)
    item = load_stored_country_observations(root, cfg, today=TODAY)[cc]["gdp"]
    assert item["series_id"] == series
    assert item["stored_path"] == f"intl_macro/{cc}_gdp.parquet"
    assert item["source_url"] == "https://fred.stlouisfed.org/series/" + series


@pytest.mark.parametrize("dates", [
    ["2025-01-01", "2025-04-01", "2025-10-01", "2026-01-01", "2026-04-01"],
    ["2025-04-01", "2025-07-01", "2025-10-01", "2026-04-01", "2026-04-01"],
    ["2025-04-01", "2025-07-01", "2025-10-01", "2026-01-01", "2026-05-01"],
    ["2025-04-01", "2025-07-01", "2025-10-01", "2026-01-01", "2026-04-02"],
    ["2025-10-01", "2026-01-01", "2026-04-01", "2026-07-01", "2026-10-01"],
])
def test_gdp_row_offsets_cannot_stand_in_for_four_calendar_quarters(tmp_path, dates):
    root, cfg, _ = _stored_case(tmp_path, dates=dates)
    assert load_stored_country_observations(root, cfg, today=TODAY) == {}


@pytest.mark.parametrize("values", [
    [0, 101, 102, 103, 104], [100, 101, float("inf"), 103, 104],
    [True] * 5, [100, 101, None, 103, 104],
])
def test_stored_gdp_refuses_invalid_or_missing_window_levels(tmp_path, values):
    root, cfg, _ = _stored_case(tmp_path, values=values)
    assert load_stored_country_observations(root, cfg, today=TODAY) == {}


@pytest.mark.parametrize("key,value", [
    ("source_id", "NGDPRSAXDCGBQ"), ("source_url", "https://www.cao.go.jp/"),
    ("last_observation", "2026-01-01"), ("provider", "eurostat"),
    ("status", "missing"), ("unit", "unreviewed_units"),
])
def test_stored_macro_requires_matching_producer_identity_and_latest_row(tmp_path, key, value):
    root, cfg, provenance = _stored_case(tmp_path)
    provenance["series"]["JP_gdp"][key] = value
    _rewrite_provenance(root, provenance)
    assert load_stored_country_observations(root, cfg, today=TODAY) == {}


def test_stored_macro_refuses_wrong_configuration_or_store_column(tmp_path):
    root, cfg, _ = _stored_case(tmp_path)
    cfg["countries"]["JP"]["fred"]["gdp"] = "NGDPRSAXDCGBQ"
    assert load_stored_country_observations(root, cfg, today=TODAY) == {}
    cfg["countries"]["JP"]["fred"]["gdp"] = "JPNRGDPEXP"
    path = root / "intl_macro/JP_gdp.parquet"
    pd.read_parquet(path).rename(columns={"JP_gdp": "GB_gdp"}).to_parquet(path)
    assert load_stored_country_observations(root, cfg, today=TODAY) == {}


@pytest.mark.parametrize("key,value", [
    ("period", "2026-04"), ("period_end", "2026-04-30"), ("value", 9.9),
    ("series_id", "NGDPRSAXDCGBQ"), ("native_unit", "Percent"),
    ("retrieved_at", "2026-10-18T00:00:00+00:00"),
])
def test_caller_mapping_cannot_relabel_or_refresh_a_stored_observation(tmp_path, key, value):
    root, cfg, _ = _stored_case(tmp_path)
    mapping = load_stored_country_observations(root, cfg, today=TODAY)
    mapping["JP"]["gdp"][key] = value
    assert stored_observation_view(mapping["JP"]["gdp"], "JP", "gdp", today=TODAY) is None
    metric = next(m for m in view(record("JP"), stored_observations=mapping)["metrics"] if m["key"] == "gdp")
    assert metric["value"] is None and metric["evidence"] is None


@pytest.mark.parametrize("cc,series", [
    ("JP", "LRHUTTTTJPM156S"), ("KR", "LRHUTTTTKRM156S"),
    ("AU", "LRHUTTTTAUM156S"), ("GB", "LRHUTTTTGBM156S"),
])
def test_stored_unemployment_preserves_exact_monthly_level(tmp_path, cc, series):
    root, cfg, _ = _stored_case(tmp_path, cc=cc, metric="unemployment", values=[4.48448])
    item = load_stored_country_observations(root, cfg, today=TODAY)[cc]["unemployment"]
    assert item["value"] == 4.48448
    assert item["period"] == "2026-07" and item["period_end"] == "2026-07-31"
    assert item["observations"] == [{"date": "2026-07-01", "value": 4.48448}]
    assert item["series_id"] == series and item["method"] == "reported_level"
    assert item["source_url"] == "https://fred.stlouisfed.org/series/" + series
    assert item["retrieved_at"] is None


def test_euro_area_unemployment_keeps_actual_eurostat_dimensions(tmp_path):
    root, cfg, provenance = _stored_case(tmp_path, cc="EZ", metric="unemployment", values=[6.2])
    mapping = load_stored_country_observations(root, cfg, today=TODAY)
    item = mapping["EZ"]["unemployment"]
    assert item["source"] == "Eurostat" and item["series_id"] == "une_rt_m"
    assert "geo=EA21" in item["source_url"] and item["geography"] == "Euro area (EA21)"
    assert "fred" not in item["source_url"] and item["value"] == 6.2
    provenance["series"]["EZ_unemployment"]["source_url"] = item["source_url"].replace("geo=EA21", "geo=EA19")
    _rewrite_provenance(root, provenance)
    assert load_stored_country_observations(root, cfg, today=TODAY) == {}


@pytest.mark.parametrize("value", [-0.1, 100.1, float("inf"), True])
def test_unemployment_requires_a_finite_reported_percentage(tmp_path, value):
    root, cfg, _ = _stored_case(tmp_path, metric="unemployment", values=[value])
    assert load_stored_country_observations(root, cfg, today=TODAY) == {}


def test_qualified_national_gdp_cpi_and_policy_keep_precedence(tmp_path):
    root, cfg, _ = _stored_case(tmp_path)
    mapping = load_stored_country_observations(root, cfg, today=TODAY)
    for cc in ("JP", "TW", "IN"):
        official = {cc: {
            "gdp": observation("gdp", unit="% y/y", period="2026-Q2", value=7.3,
                               provider="Reviewed national source", source_url="https://example.gov/gdp"),
            "inflation": observation(value=2.0),
            "policy": observation("policy", unit="%", period="2026-09", value=1.0),
        }}
        country = view(record(cc), official=official, stored_observations=mapping)
        metrics = {metric["key"]: metric for metric in country["metrics"]}
        assert metrics["gdp"]["value"] == 7.3 and metrics["gdp"]["evidence"] is None
        assert metrics["gdp"]["source_url"] == "https://example.gov/gdp"
        assert metrics["inflation"]["value"] == 2.0 and metrics["policy"]["value"] == 1.0
        assert metrics["gdp"]["period_end"] == "2026-06-30"


def test_dated_matched_stored_observation_remains_available(tmp_path):
    root, cfg, _ = _stored_case(tmp_path, dates=[
        "2023-04-01", "2023-07-01", "2023-10-01", "2024-01-01", "2024-04-01"])
    mapping = load_stored_country_observations(root, cfg, today=TODAY)
    gdp = next(m for m in view(record("JP"), stored_observations=mapping)["metrics"] if m["key"] == "gdp")
    assert gdp["value"] == pytest.approx(4.0) and gdp["quality"] == "dated"
    assert not gdp["current"] and gdp["evidence"]["retrieved_at"] is None


def test_corrupt_stored_series_isolated_and_anonymous_observations_missing(tmp_path):
    root, cfg, _ = _stored_case(tmp_path)
    (root / "intl_macro/JP_gdp.parquet").write_bytes(b"not a parquet")
    assert load_stored_country_observations(root, cfg, today=TODAY) == {}
    country = view()
    assert all(metric["value"] is None for metric in country["metrics"])


@pytest.mark.parametrize("changes", [
    {"value": None}, {"value": True}, {"status": "missing"},
    {"unit": "index"}, {"period": "2026-Q4"}, {"source_url": "javascript:invalid"},
])
def test_unqualified_official_gdp_does_not_block_a_separately_matched_stored_trace(tmp_path, changes):
    root, cfg, _ = _stored_case(tmp_path)
    mapping = load_stored_country_observations(root, cfg, today=TODAY)
    official = {"JP": {"gdp": observation("gdp", **{
        "unit": "% y/y", "period": "2026-Q2", "value": 7.3, **changes})}}
    metric = next(m for m in view(record("JP"), official=official,
                                  stored_observations=mapping)["metrics"] if m["key"] == "gdp")
    assert metric["value"] == pytest.approx(4.0)
    assert metric["source_url"] == "https://fred.stlouisfed.org/series/JPNRGDPEXP"
    assert metric["evidence"] is not None and metric["change_3m_pp"] is None


def test_valid_older_official_gdp_still_has_precedence_over_stored_fallback(tmp_path):
    root, cfg, _ = _stored_case(tmp_path)
    mapping = load_stored_country_observations(root, cfg, today=TODAY)
    official = {"JP": {"gdp": observation("gdp", unit="% y/y", period="2024-Q2", value=7.3)}}
    metric = next(m for m in view(record("JP"), official=official,
                                  stored_observations=mapping)["metrics"] if m["key"] == "gdp")
    assert metric["value"] == 7.3 and metric["quality"] == "dated"
    assert metric["evidence"] is None and metric["period"] == "2024-Q2"
