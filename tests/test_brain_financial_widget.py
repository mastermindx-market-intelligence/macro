"""Shared widget delivery, snapshot replay, expansion and safe lazy math."""
from pathlib import Path
from playwright.sync_api import expect
from tests.test_brain_history_widget import page  # noqa: F401
from tests.test_brain_visuals_widget import history, stream
from tests.test_brain_financial_views import wire

ROOT=Path(__file__).resolve().parents[1]

def assets(page):
    for name in ("mm_brain_presentation.js","mm_brain_finance.js","mm_brain_finance_math_v1.js",
                 "mm_brain_finance.css","mm_brain_math.js"):
        page.route("**/"+name+"*",lambda route,name=name:route.fulfill(
            content_type="text/css" if name.endswith(".css") else "application/javascript",
            body=(ROOT/"templates"/name).read_text()))

def test_history_financial_view_expands_existing_chat_and_clears_on_account_change(page):
    assets(page)
    history(page,wire())
    expect(page.locator(".mmb-f-card")).to_have_count(1)
    expect(page.locator(".mmb-f-period-detail")).to_be_visible()
    page.get_by_role("button",name="Enlarge / full table").click()
    expect(page.locator(".mmb-panel")).to_have_class(__import__("re").compile(r"\bmax\b"))
    expect(page.locator(".mmb-f-statement-table")).to_be_visible()
    page.evaluate("window.__principal='B';window.__onAuth({id:'user-B'})")
    expect(page.locator(".mmb-f-card")).to_have_count(0)

def test_financial_sse_and_done_deduplicate_and_local_controls_dont_call_model(page):
    assets(page)
    w=wire()
    stream(page,[{"type":"delta","text":"The statement is ready."},w,w,
        {"type":"done","charts":[w],"citations":[]}])
    expect(page.locator(".mmb-f-card")).to_have_count(1)
    before=page.evaluate("window.__requests.length")
    page.get_by_role("button",name="Cash flow",exact=True).click()
    expect(page.locator(".mmb-f-body")).to_contain_text("Cash flows retain")
    assert page.evaluate("window.__requests.length")==before

def test_retract_and_stop_do_not_resurrect_financial_cards(page):
    assets(page)
    w=wire()
    stream(page,[{"type":"delta","text":"Rejected answer."},w,
        {"type":"retract","text":"A corrected answer."},{"type":"done","filtered":True,"charts":[w]}])
    expect(page.locator(".mmb-txt")).to_contain_text("A corrected answer.")
    page.wait_for_timeout(100)
    expect(page.locator(".mmb-f-card")).to_have_count(0)

def test_formulas_render_but_currency_and_code_remain_literal(page):
    assets(page)
    from tests.test_brain_visuals_widget import TID
    formula=r"Discounted cash flow: \(PV=\frac{FCF}{(1+r)^t}\). Price is $120 and $130."+"\n\n"+r"\[V=\sum_{t=1}^{T}\frac{FCF_t}{(1+r)^t}\]"+"\n\n"+r"`\(not_math\)`"
    page.evaluate("""([text,tid])=>{
      const old=window.fetch;
      window.fetch=(url,options={})=>url.endsWith('/'+tid)?Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({
        thread:{id:tid},messages:[{role:'assistant',content:text}]})}):old(url,options);
    }""",[formula,TID])
    page.locator(f'.mmb-ti[data-id="{TID}"] .mmb-ti-body').click()
    expect(page.locator("math")).to_have_count(2)
    expect(page.locator(".mmb-txt")).to_contain_text("Price is $120 and $130")
    expect(page.locator(".mmb-txt code")).to_have_text(r"\(not_math\)")
