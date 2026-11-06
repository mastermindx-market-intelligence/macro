"""Real Chromium: canonical semantics, responsive finance views and local controls."""
from pathlib import Path
import copy
import json
import pytest
from playwright.sync_api import expect, sync_playwright
from engine.neuralweb import brain_financial_views as fv
from tests.test_brain_financial_views import fund, wire, exact_wire

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def page():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        p=browser.new_page(viewport={"width":390,"height":844},reduced_motion="reduce")
        p.set_content('<!doctype html><html data-theme="dark" data-lang="en"><head></head><body style="margin:12px;background:#101722;color:#eef2f8;font-family:system-ui"><main id="mmb-root" style="--mmb-text:#eef2f8;--mmb-muted:#a6b6cb;--mmb-card:#172333;--mmb-line:#344258;--mmb-info:#78b8f9;--mmb-hi:#9989ff;--mmb-font:system-ui"><div id="host"></div></main></body></html>')
        p.add_style_tag(path=str(ROOT/"templates/mm_brain_finance.css"))
        p.add_script_tag(path=str(ROOT/"templates/mm_brain_finance_math_v1.js"))
        p.add_script_tag(path=str(ROOT/"templates/mm_brain_finance.js"))
        yield p
        browser.close()

def mount(page,w):
    return page.evaluate("""w=>MMBrainFinance.mount(document.querySelector('#host'),w,
        {onExpand:()=>{window.__expands=(window.__expands||0)+1;}})""",w)

def test_canonical_market_and_eps_semantics_normalize_full_snapshot(page):
    source=fund("600519.SS")
    source["statements"]["quarterly"]["income"]["eps_basic"]=[1,3,6,10,2,4,8,12]
    result=page.evaluate("""f=>{
      const m=MMBrainFinanceMath,s=f.statements.quarterly;
      return {cn:m.incomeView(f.ticker,s,'quarterly').income,
              us:m.incomeView('NVDA',s,'quarterly').income,
              hk:m.incomeView('0700.HK',{...s,flow_basis:'discrete_period'},'quarterly').income};
    }""",source)
    assert result["cn"]["revenue"]==[10,20,30,40,15,30,45,60]
    assert result["cn"]["eps_basic"]==[1,None,None,None,2,None,None,None]
    assert result["us"]["revenue"]==[10,30,60,100,15,45,90,150]
    assert result["hk"]["revenue"]==result["us"]["revenue"]

def test_financial_family_fallback_excludes_industrial_rows(page):
    source=fund("JPM")
    source["profile"]["sector"]="Financials"
    for key in ("cogs","gross_profit","ebitda"):
        source["statements"]["quarterly"]["income"][key]=[None]*8
    result=page.evaluate("""f=>{
      const m=MMBrainFinanceMath,prepared=m.applyLegacyStatementFamilyFallback(f);
      const model=MMBrainFinance.statementModel(prepared,m,'quarterly','income');
      return {keys:model.keys,label:m.incomeViewTopLineLabel(model.view,false),mode:m.incomeViewFamilyMode(model.view)};
    }""",source)
    assert result["mode"]=="financial"
    assert result["label"]=="Total operating income"
    assert not set(result["keys"]) & {"cogs","gross_profit","ebitda"}

def test_missing_basis_and_mobile_period_detail_then_expand(page):
    w=wire("600519.SS",basis="annual",period_count=4)
    assert mount(page,w)
    expect(page.locator(".mmb-f-period-detail")).to_be_visible()
    expect(page.locator(".mmb-f-statement-table")).to_be_hidden()
    expect(page.get_by_role("button",name="Annual",exact=True)).to_be_disabled()
    expect(page.get_by_role("button",name="Quarterly",exact=True)).to_have_attribute("aria-pressed","true")
    assert page.locator(".mmb-f-detail-row").first.inner_text().startswith("Revenue")
    page.get_by_role("button",name="Enlarge / full table").click()
    expect(page.locator(".mmb-f-statement-table")).to_be_visible()
    assert page.evaluate("window.__expands")==1
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    # View changes use only the original snapshot. No network/model call is possible.
    page.evaluate("()=>{window.fetch=()=>{throw new Error('unexpected fetch')};}")
    page.get_by_role("button",name="Balance sheet",exact=True).click()
    expect(page.locator(".mmb-f-statement-table")).to_contain_text("Total assets")
    page.get_by_role("button",name="Cash flow",exact=True).click()
    expect(page.locator(".mmb-f-body")).to_contain_text("Cash flows retain the source reporting basis")

@pytest.mark.parametrize("width",[320,390,820,1440])
def test_container_responsiveness_and_a11y(page,width):
    page.set_viewport_size({"width":width,"height":900})
    assert mount(page,wire())
    expect(page.locator(".mmb-f-card")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    assert not page.locator("svg").evaluate_all("(els)=>els.some(el=>/NaN|Infinity/.test(el.outerHTML))")
    assert page.locator("button").evaluate_all("(els)=>els.filter(el=>el.getClientRects().length).every(el=>el.getBoundingClientRect().height>=44)")
    if width>600:
        expect(page.locator(".mmb-f-statement-table")).to_be_visible()
        expect(page.locator(".mmb-f-period-detail")).to_be_hidden()
    page.get_by_role("button",name="Cash flow",exact=True).focus()
    page.keyboard.press("Enter")
    expect(page.get_by_role("button",name="Cash flow",exact=True)).to_be_focused()

def test_range_controls_slice_dates_not_bar_interval_and_no_numeric_coercion(page):
    result=page.evaluate("""()=>{
      const bars=[{date:'2024-01-01',close:90},{date:'2025-12-31',close:100},
        {date:'2026-01-02',close:110},{date:'2026-09-30',close:120},{date:'2026-10-21',close:125}];
      return {one:MMBrainFinance.rangeBars(bars,'1M'),ytd:MMBrainFinance.rangeBars(bars,'YTD'),
        all:MMBrainFinance.rangeBars(bars,'MAX'),month:MMBrainFinance.cutoffFor('1M','2026-03-31')};
    }""")
    assert [x["date"] for x in result["one"]]==["2026-09-30","2026-10-21"]
    assert len(result["ytd"])==3 and len(result["all"])==5
    assert result["month"]=="2026-02-28"

def test_csv_uses_exact_canonical_values_and_neutralizes_text_formulas(page):
    w=wire("600519.SS",basis="interim")
    assert mount(page,w)
    with page.expect_download() as info:
        page.get_by_role("button",name="Download statement snapshot").click()
    content=Path(info.value.path()).read_text(encoding="utf-8-sig")
    assert '"Revenue","10","20","30","40","15","30","45","60"' in content
    assert "Unscaled source currency" in content
    assert page.evaluate("""()=>MMBrainFinance.csvCell('  =HYPERLINK(1)')""")=='''"'  =HYPERLINK(1)"'''
    assert w["visual"]["data"]["fund"]["statements"]["quarterly"]["income"]["revenue"][-1]==150

def test_renderer_rejects_bad_payload_and_deduplicates(page):
    w=wire()
    assert mount(page,w)
    assert mount(page,w)
    expect(page.locator(".mmb-f-card")).to_have_count(1)
    bad=copy.deepcopy(w);bad["visual_id"]="b"*24
    bad["visual"]["data"]["fund"]["statements"]["quarterly"]["income"]["revenue"][0]=True
    assert not mount(page,bad)
    bad=copy.deepcopy(w);bad["visual_id"]="c"*24;bad["visual"]["title"]="<img src=x>"
    assert not mount(page,bad)
    expect(page.locator("img")).to_have_count(0)

def test_summary_has_no_quote_treatment_and_company_facts_stay_labelled(page,tmp_path):
    summary=fv.compile_financial_widget({"template":"transcript","symbol":"AAPL"},
        {"reader":"get_earnings","call_id":"s","result":{"symbol":"AAPL","latest_earnings_call":{
            "summary":"The company discussed revenue.","fiscal_period":"Q4 2026"}}},"summary")
    assert mount(page,summary)
    expect(page.locator(".mmb-f-badge")).to_have_text("AI-assisted call summary")
    expect(page.locator("blockquote")).to_have_count(0)
    company=fv.compile_financial_widget({"template":"company","symbol":"AAPL"},
        {"reader":"get_fundamentals","call_id":"c","result":{"symbol":"AAPL","profile":{
            "name":"Example","sector":"Technology","description":"An illustrative source fixture","mktcap_bn":10},
            "valuation":{"trailing_pe":20}}},"company")
    assert mount(page,company)
    expect(page.locator(".mmb-f-metrics")).to_contain_text("Trailing P/E")
    expect(page.locator(".mmb-f-body").last).to_contain_text("currency is not supplied")
    quotes=exact_wire(tmp_path)
    assert mount(page,quotes)
    original=[f["quote"]["text"] for f in quotes["visual"]["data"]["facts"]]
    expect(page.locator(".mmb-f-badge").last).to_have_text("Source excerpts")
    expect(page.locator(".mmb-f-excerpt figcaption").first).to_contain_text("Executive · Prepared remarks")
    expect(page.locator(".mmb-f-excerpt figcaption").filter(has_text="Q&A")).to_have_count(2)
    assert page.locator("blockquote").all_text_contents()==original
    page.evaluate("document.documentElement.dataset.lang='zh';document.dispatchEvent(new Event('langchange'))")
    expect(page.locator(".mmb-f-badge").last).to_have_text("原文摘录")
    expect(page.locator(".mmb-f-excerpt figcaption").first).to_contain_text("管理层 · 预备发言")
    expect(page.locator(".mmb-f-excerpt figcaption").filter(has_text="问答")).to_have_count(2)
    assert page.locator("blockquote").all_text_contents()==original

def test_mathml_is_lazy_safe_and_literal_fallback(page):
    page.add_script_tag(path=str(ROOT/"templates/mm_brain_math.js"))
    page.evaluate("""()=>{
      const h=document.querySelector('#host');
      for (const text of ['\\\\frac{FCF}{(1+r)^t}','\\\\href{javascript:alert(1)}{bad}','\\\\unknowncommand']) {
        const n=document.createElement('span');n.dataset.mmbMath='display';n.textContent=text;h.appendChild(n);
      }
      MMBrainMath.render(h);
    }""")
    expect(page.locator("math")).to_have_count(2)  # untrusted href stays noninteractive MathML text
    expect(page.locator("a,[href]")).to_have_count(0)
    expect(page.locator(".mmb-math-fallback")).to_have_count(1)


def test_selected_period_drives_desktop_table_and_live_locale_preserves_snapshot(page):
    page.set_viewport_size({"width":1440,"height":1000})
    w=wire(basis="interim",period_count=4)
    assert mount(page,w)
    expect(page.locator(".mmb-f-statement-table thead")).to_contain_text("Q4 2025")
    page.get_by_label("Through period",exact=True).select_option("3")
    expect(page.locator(".mmb-f-statement-table thead")).to_contain_text("Q4 2024")
    expect(page.locator(".mmb-f-statement-table thead")).not_to_contain_text("2025")
    snapshot=page.locator(".mmb-f-card").get_attribute("data-snapshot-id")
    page.evaluate("document.documentElement.dataset.lang='zh';document.dispatchEvent(new Event('langchange'))")
    expect(page.get_by_role("button",name="利润表",exact=True)).to_be_visible()
    expect(page.locator(".mmb-f-eyebrow")).to_have_text("财务报表")
    expect(page.locator(".mmb-f-footer")).to_contain_text("已保存快照")
    expect(page.locator(".mmb-f-statement-table thead")).to_contain_text("Q4 2024")
    page.evaluate("document.documentElement.dataset.lang='en';window.dispatchEvent(new Event('mm:lang'))")
    expect(page.get_by_label("Through period",exact=True)).to_have_value("3")
    expect(page.locator(".mmb-f-eyebrow")).to_have_text("Financial statements")
    assert page.locator(".mmb-f-card").get_attribute("data-snapshot-id")==snapshot
    page.evaluate("MMBrainFinance.clear(document.querySelector('#host'));document.dispatchEvent(new Event('langchange'))")
    expect(page.locator(".mmb-f-card")).to_have_count(0)
