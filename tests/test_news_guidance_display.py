"""Ticker News display consumes synthetic owner output, never computes a signal."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re

import pytest
from jinja2 import Environment, FileSystemLoader
from test_news_guidance_comparison import workspace, ASOF
from engine.company_intelligence.guidance_comparison import compare_guidance_workspaces, public_guidance_context

ROOT = Path(__file__).resolve().parents[1]


def payload(*, percent=False, correction=False, prior=True):
    kwargs = {"metric": "revenue_yoy_pct", "unit": "percent"} if percent else {}
    old = workspace(9, 11, **kwargs) if percent else workspace()
    new = workspace(10, 12, later=True, **kwargs) if percent else workspace(76000, 78000, later=True)
    if correction:
        new["lifecycle"]["state"] = "corrected"
    return public_guidance_context(compare_guidance_workspaces(new, old if prior else None, as_of=ASOF))


def view(data):
    assert importlib.util.find_spec("lib.news_guidance_view") is not None, "Ticker guidance display adapter is missing"
    from lib.news_guidance_view import guidance_view
    return guidance_view(data)


def render(data):
    context = {"ticker": "ACME", "name": "Synthetic Example", "news": [], "news_guidance": view(data),
               "hero": None, "stats": None, "stale": False, "jsonld_str": "{}", "canonical_url": "", "meta_desc": ""}
    return Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True).get_template("ticker.html.j2").render(**context)


def test_absent_input_adds_no_panel():
    assert view(None) is None


def test_existing_owner_ranges_and_delta_reach_bilingual_view_unchanged():
    data=payload(); before=deepcopy(data); result=view(data); row=result["rows"][0]
    assert row["label_en"]=="Vehicle deliveries" and row["label_zh"]=="汽车交付量"
    assert row["prior_en"]=="100,000–103,000 vehicles"
    assert row["current_en"]=="76,000–78,000 vehicles"
    assert row["change_en"]=="Midpoint change: -24,500 vehicles"
    assert "-24.137931%" in row["relative_en"]
    assert data==before


def test_rate_difference_never_masquerades_as_relative_percent():
    row=view(payload(percent=True))["rows"][0]
    assert row["change_en"]=="Midpoint change: 1 percentage point"
    assert row["relative_en"]=="" and "百分点" in row["change_zh"]


def test_source_correction_remains_distinct_from_management_revision():
    row=view(payload(correction=True))["rows"][0]
    assert row["status_en"]=="Corrected source" and row["status_zh"]=="来源更正"
    text=json.dumps(row).lower()
    assert "guidance cut" not in text and "sell" not in text


def test_named_missing_prior_is_visible_not_zero():
    result=view(payload(prior=False))
    assert result["rows"]==[] and "No comparable prior guidance" in result["note_en"]
    assert "0%" not in json.dumps(result)


@pytest.mark.parametrize("field,value",[("authority","signal"),("schema","wrong"),("temporal_basis","decision_time"),
    ("is_context_only",False),("display_only",False),("available",1),("comparisons",{}),("consensus",{}),("as_of","bad")])
def test_invalid_envelope_never_renders_numbers(field,value):
    data=payload(); data[field]=value; result=view(data)
    assert not result["rows"] and result["note_en"]


def test_permission_flags_must_be_actual_false():
    data=payload(); data["prophet_flags"]["may_rank"]=0
    assert not view(data)["rows"]


@pytest.mark.parametrize("field,value",[("current_low","NaN"),("midpoint_delta",float("inf")),
    ("prior_high",True),("current_high","1e10000"),("horizon","<script>bad</script>"),
    ("delta_unit","percent"),("interpretation","bullish"),("unit","unmapped_currency_scale")])
def test_invalid_row_is_counted_not_interpreted(field,value):
    data=payload(); data["comparisons"][0][field]=value; result=view(data)
    assert not result["rows"] and result["unavailable_count"]==1


def test_malformed_row_does_not_hide_later_valid_comparison():
    data=payload(); data["comparisons"].insert(0,None); result=view(data)
    assert len(result["rows"])==1 and result["unavailable_count"]==1


def test_bounded_output_discloses_remaining_comparisons():
    data=payload(); data["comparisons"]*=6; result=view(data)
    assert len(result["rows"])==4 and result["omitted_count"]==2


def test_source_dates_are_not_the_calculation_date():
    row=view(payload())["rows"][0]
    assert "2026-09-24 15:00 UTC" in row["current_source_en"]
    assert "2026-09-23 15:00 UTC" in row["prior_source_en"]
    assert "16:00" not in row["current_source_en"]


def test_public_html_has_keyboard_details_both_languages_and_no_private_locators():
    data=payload(); data["comparisons"][0]["evidence"][0]["document_id"]="PRIVATE-DOCUMENT-SECRET"
    html=render(data)
    assert 'data-news-guidance' in html and '<summary' in html
    assert "Guidance changes" in html and "指引变化" in html
    assert "76,000–78,000 vehicles" in html and "76,000–78,000 辆" in html
    assert "PRIVATE-DOCUMENT-SECRET" not in html and "evt_cik0000000001" not in html
    assert 'id="news"' in html and 'href="#news"' in html


def test_missing_context_does_not_change_existing_headline_markup():
    env=Environment(loader=FileSystemLoader(str(ROOT/'templates')),autoescape=True)
    ctx={"ticker":"ACME","name":"Synthetic","news":[{"title":"Existing headline","url":"https://example.test/a","source":"Primary","published":"2026-09-24"}],"hero":None,"stats":None,"stale":False,"jsonld_str":"{}"}
    old=env.get_template('ticker.html.j2').render(**ctx)
    new=env.get_template('ticker.html.j2').render(**ctx,news_guidance=view(None))
    assert old==new and 'Existing headline' in new and 'data-news-guidance' not in new


def test_real_artifact_loader_and_page_context_wire_the_same_ticker_only(tmp_path):
    from scripts import build_ticker_pages as pages
    news=tmp_path/'news'; news.mkdir()
    rec={"top":[{"title":"Existing headline","url":"https://example.test/a","published":"2026-09-24"}],"guidance_context":payload()}
    (news/'by_ticker.json').write_text(json.dumps({"schema":"news_flow.v1","tickers":{"ACME":rec}}))
    agg=pages.load_all_aggregates(tmp_path)
    ctx=pages.build_page_context("ACME","Synthetic","Technology",{},agg,"2026-09-24T16:00:00Z")
    assert ctx.get("news_guidance"), "Existing artifact is not connected to the ticker view"
    assert ctx["news_guidance"]["rows"][0]["current_en"]=="76,000–78,000 vehicles"
    other=pages.build_page_context("OTHER","Other","Technology",{},agg,"2026-09-24T16:00:00Z")
    assert other.get("news_guidance") is None
    no_guidance=deepcopy(agg); no_guidance["news_map"]["ACME"].pop("guidance_context")
    before=pages.build_page_context("ACME","Synthetic","Technology",{},no_guidance,"2026-09-24T16:00:00Z")
    assert {k:v for k,v in before.items() if k!="news_guidance"}=={k:v for k,v in ctx.items() if k!="news_guidance"}
    html=Environment(loader=FileSystemLoader(str(ROOT/'templates')),autoescape=True).get_template('ticker.html.j2').render(**ctx)
    assert 'data-news-guidance' in html and '76,000–78,000 vehicles' in html


def test_new_display_suite_runs_in_existing_source_gate():
    import yaml
    jobs=yaml.safe_load((ROOT/'.github/ci/legacy-jobs.yml').read_text())["jobs"]
    owner=jobs["earnings-release-identity"]
    assert owner["gate"]=="code"
    assert any('tests/test_news_guidance_display.py' in step.get('run','') for step in owner['steps'])
    assert any('jinja2' in step.get('run','') for step in owner['steps'])


def test_collapsed_summary_exposes_the_material_change_and_correction_state():
    html=render(payload(correction=True))
    summary=re.search(r'<details[^>]*data-news-guidance[^>]*>\s*(<summary.*?</summary>)',html,re.S)[1]
    assert '-24,500 vehicles' in summary and 'Corrected source' in summary and '来源更正' in summary


def test_collapsed_missing_state_does_not_look_like_a_supported_change():
    html=render(payload(prior=False))
    summary=re.search(r'<details[^>]*data-news-guidance[^>]*>\s*(<summary.*?</summary>)',html,re.S)[1]
    assert 'No comparable prior guidance' in summary and '暂无可比' in summary


def test_existing_builder_and_template_have_the_same_guidance_consumer():
    # Static tripwire complements the real artifact-loader/VM/template test above.
    from scripts import build_ticker_pages as pages
    source=(ROOT/'templates/ticker.html.j2').read_text()
    assert 'guidance_view((news_rec or {}).get("guidance_context"))' in (ROOT/'scripts/build_ticker_pages.py').read_text()
    assert 'data-news-guidance' in source


def test_html_escapes_untrusted_existing_headline_alongside_guidance():
    env=Environment(loader=FileSystemLoader(str(ROOT/'templates')),autoescape=True)
    ctx={"ticker":"ACME","name":"Synthetic","hero":None,"stats":None,"stale":False,"jsonld_str":"{}",
         "news":[{"title":"<img src=x onerror=alert(1)>","url":"https://example.test/a","source":"source","published":"2026-09-24"}],"news_guidance":view(payload())}
    html=env.get_template('ticker.html.j2').render(**ctx)
    assert '<img src=x onerror=alert(1)>' not in html and '&lt;img' in html


def test_optional_relative_change_does_not_invent_zero():
    old=workspace(0,0); new=workspace(1,3,later=True)
    data=public_guidance_context(compare_guidance_workspaces(new,old,as_of=ASOF))
    row=view(data)['rows'][0]
    assert 'undefined' in row['relative_en'] and '0%' not in row['relative_en']


def test_invalid_disclosure_clock_refuses_the_row():
    data=payload(); data['comparisons'][0]['evidence'][0]['source_available_at']='bad'
    assert view(data)['unavailable_count']==1


def test_guidance_only_ticker_can_render_with_no_headline_list():
    env=Environment(loader=FileSystemLoader(str(ROOT/'templates')),autoescape=True)
    html=env.get_template('ticker.html.j2').render(ticker='ACME',name='Synthetic',news=None,news_guidance=view(payload()),hero=None,stats=None,stale=False,jsonld_str='{}')
    assert 'data-news-guidance' in html and '76,000–78,000 vehicles' in html


def test_existing_exclusive_dossier_gate_covers_guidance_dependency():
    # Hosted contract-delta found this real import-closure hole: dossier tests
    # import build_ticker_pages, which now imports the pure guidance formatter.
    import fnmatch
    import yaml
    jobs = yaml.safe_load((ROOT / '.github/ci/legacy-jobs.yml').read_text())["jobs"]
    job = jobs["conviction-profile"]
    assert job["scope"] == "exclusive" and job["gate"] == "code"
    assert any(fnmatch.fnmatchcase("lib/news_guidance_view.py", pattern)
               for pattern in job["paths"]), "exclusive dossier gate omits its new import"


@pytest.mark.parametrize("reason", ["guidance_source_clock_missing", "guidance_source_clock_unknown",
                                    "guidance_source_clock_invalid", "guidance_source_clock_ambiguous"])
def test_source_clock_absence_uses_existing_plain_timing_message(reason):
    data = payload(prior=False); data["reasons"] = [reason]
    display = view(data)
    assert display["note_en"] == "Disclosure timing could not be verified."
    assert display["note_zh"] == "无法核实披露时间。"
    html = render(data)
    assert reason not in html and 'Disclosure timing could not be verified.' in html
    assert '-24,500' not in html


@pytest.mark.parametrize("known", [True, False])
def test_actual_news_to_ticker_path_preserves_source_clock_and_absence(tmp_path, monkeypatch, known):
    from test_news_guidance_comparison import transcript_workspace
    from engine import financial_news
    from scripts import build_ticker_pages as pages
    monkeypatch.setattr(financial_news.nc, "build_entity_map", lambda: {"tickers": {}})
    records = financial_news.mastermind_by_ticker(
        {"by_ticker": {"ACME": [{"title": "Synthetic source", "url": "https://example.test/a"}]}},
        guidance_workspaces={"ACME": {"current": transcript_workspace(later=True, known=known),
                                     "prior": transcript_workspace(), "expected_security_id": "xnas:ACME"}},
        as_of=ASOF)
    folder = tmp_path / "news"; folder.mkdir()
    (folder / "by_ticker.json").write_text(json.dumps({"schema": "news_flow.v1", "tickers": records}))
    ctx = pages.build_page_context("ACME", "Synthetic", "Technology", {},
                                  pages.load_all_aggregates(tmp_path), "2026-09-24T16:00:00Z")
    html = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True).get_template('ticker.html.j2').render(**ctx)
    assert 'data-news-guidance' in html and 'Synthetic source' in html
    if known:
        assert 'Current disclosure: 2026-09-24 15:10 UTC' in html
        assert 'Current disclosure: 2026-09-24 15:00 UTC' not in html
        assert '-24,500 vehicles' in html
    else:
        assert 'Disclosure timing could not be verified.' in html
        assert '-24,500 vehicles' not in html
    assert 'fixture-release' not in html and 'guidance_source_clock' not in html


# R9: the same ticker artifact accepts an owner release history, not a chosen pair.
def test_owner_release_history_reaches_the_existing_news_artifact_and_ticker(monkeypatch, tmp_path):
    from test_news_guidance_comparison import release_history, EVENT
    from engine import financial_news
    from scripts import build_ticker_pages as pages
    history = release_history()
    security = history[-1]['workspace']['issuer']['listings'][0]['security_id']
    monkeypatch.setattr(financial_news.nc, 'build_entity_map', lambda: {})
    feed = {'by_ticker': {'ACME': [{'title':'Existing story', 'url':'https://example.test/story'}]}}
    supplied = {'ACME': {'release_revisions': history, 'event_id': EVENT, 'expected_security_id': security}}
    before = deepcopy(supplied)
    news = financial_news.mastermind_by_ticker(feed, guidance_workspaces=supplied, as_of=ASOF)
    assert news['ACME']['guidance_context']['available'], 'Source history never reached the comparator'
    assert supplied == before
    baseline = financial_news.mastermind_by_ticker(feed)
    assert {k:v for k,v in news['ACME'].items() if k!='guidance_context'} == baseline['ACME']
    target = tmp_path/'news'; target.mkdir()
    (target/'by_ticker.json').write_text(json.dumps({'schema':'news_flow.v1','tickers':news}))
    agg = pages.load_all_aggregates(tmp_path)
    ctx = pages.build_page_context('ACME','Synthetic','Technology',{},agg,ASOF.isoformat())
    html = Environment(loader=FileSystemLoader(str(ROOT/'templates')),autoescape=True).get_template('ticker.html.j2').render(**ctx)
    assert '76,000–78,000 vehicles' in html and '-24,500 vehicles' in html
    assert 'fixture-release' not in html
    assert pages.build_page_context('OTHER','Other','Technology',{},agg,ASOF.isoformat())['news_guidance'] is None


def test_release_history_and_manual_pair_are_not_silently_prioritized(monkeypatch):
    from test_news_guidance_comparison import release_history, EVENT
    from engine import financial_news
    history = release_history(); security = history[-1]['workspace']['issuer']['listings'][0]['security_id']
    pair = {'release_revisions':history,'event_id':EVENT,'expected_security_id':security,
            'current':history[-1]['workspace'],'prior':history[0]['workspace']}
    monkeypatch.setattr(financial_news.nc,'build_entity_map',lambda:{})
    result = financial_news.mastermind_by_ticker({'by_ticker':{'ACME':[]}},guidance_workspaces={'ACME':pair},as_of=ASOF)
    context = result['ACME']['guidance_context']
    assert not context['available'] and context['reasons'] == ['guidance_input_ambiguous']


def test_release_history_does_not_create_new_ticker_keys(monkeypatch):
    from test_news_guidance_comparison import release_history, EVENT
    from engine import financial_news
    monkeypatch.setattr(financial_news.nc,'build_entity_map',lambda:{})
    result = financial_news.mastermind_by_ticker({'by_ticker':{'ACME':[]}},
        guidance_workspaces={'OTHER':{'release_revisions':release_history(),'event_id':EVENT}},as_of=ASOF)
    assert set(result)=={'ACME'} and 'guidance_context' not in result['ACME']


def test_invalid_history_has_a_plain_bilingual_explanation(monkeypatch):
    from test_news_guidance_comparison import history_context
    data = public_guidance_context(history_context([None]))
    result = view(data)
    assert result['note_en']=='Release history could not be verified.' and result['note_zh']
