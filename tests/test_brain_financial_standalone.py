"""Standalone chat consumes the same source snapshot/renderer and retract lifecycle."""
import json
from pathlib import Path
from urllib.parse import urlsplit
import pytest
from playwright.sync_api import sync_playwright, expect
from tests.test_brain_financial_views import wire
from tests.test_brain_visuals_browser import sample

ROOT=Path(__file__).resolve().parents[1]
TID="11111111-1111-1111-1111-111111111111"

@pytest.fixture
def standalone():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":390,"height":844},reduced_motion="reduce")
        state={"visual":wire(),"events":[],"requests":[]}
        def route(r):
            path=urlsplit(r.request.url).path
            state["requests"].append(path)
            if path=="/chat.html":
                return r.fulfill(content_type="text/html",body=(ROOT/"templates/chat.html").read_text())
            if path=="/api/brain/me":
                body={"tier":"pro","quotas":{"fast":{"remaining":99,"limit":100,"period":"day"},"pro":{"remaining":1,"limit":2,"period":"day"}}}
            elif path=="/api/brain/threads":
                body={"threads":[{"id":TID,"title":"Retained statement","lane":"fast","updated_at":"2026-10-21"}]}
            elif path=="/api/brain/threads/"+TID:
                body={"thread":{"id":TID},"messages":[{"role":"assistant","content":"The statement is shown below.","visuals":[state["visual"]],"visual_notices":state.get("notices",[])}]}
            elif path=="/api/brain/stream":
                return r.fulfill(content_type="text/event-stream",body="".join("data: "+json.dumps(e)+"\n\n" for e in state["events"]))
            else:
                candidate=ROOT/"templates"/path.removeprefix("/")
                if candidate.is_file() and (path.startswith("/mm_brain_") or path.endswith(".css")):
                    return r.fulfill(content_type="text/css" if path.endswith(".css") else "application/javascript",body=candidate.read_text())
                return r.fulfill(content_type="application/javascript",body="")
            r.fulfill(content_type="application/json",body=json.dumps(body))
        page.route("**/*",route)
        page.add_init_script("""window.MDXAuth={
          enabled:()=>true,open:()=>{},
          onChange:fn=>{window.__onAuth=fn;fn({id:'user-A'});},
          client:()=>Promise.resolve({auth:{getSession:()=>Promise.resolve({data:{session:{access_token:'fixture-only'}}})}})
        };""")
        page.goto("http://standalone.test/chat.html")
        yield page,state
        browser.close()

def test_history_loads_finance_and_clear_on_principal_change(standalone):
    page,state=standalone
    page.get_by_role("button",name="History",exact=True).click()
    page.get_by_text("Retained statement",exact=True).click()
    expect(page.locator(".mmb-f-card")).to_have_count(1)
    expect(page.locator(".msg-prose")).to_contain_text("The statement is shown below.")
    expect(page.locator(".mmb-f-period-detail")).to_be_visible()
    page.evaluate("window.__onAuth({id:'user-B'})")
    expect(page.locator(".mmb-f-card")).to_have_count(0)

def test_standalone_preserves_card_across_later_prose_and_done_dedup(standalone):
    page,state=standalone
    w=state["visual"]
    state["events"]=[{"type":"delta","text":"The statement "},w,
        {"type":"delta","text":"is shown below."},{"type":"done","charts":[w],"citations":[]}]
    page.locator("#msg-input").fill("Show AAPL financial statements")
    page.locator("#send-btn").click()
    expect(page.locator(".mmb-f-card")).to_have_count(1)
    expect(page.locator(".msg.assistant .msg-prose")).to_have_text("The statement is shown below.")
    before=state["requests"].count("/api/brain/stream")
    page.get_by_role("button",name="Cash flow",exact=True).click()
    assert state["requests"].count("/api/brain/stream")==before

def test_standalone_retract_prevents_late_card_resurrection(standalone):
    page,state=standalone
    w=state["visual"]
    state["events"]=[{"type":"delta","text":"Rejected content."},w,
        {"type":"retract","text":"A corrected answer."},{"type":"done","filtered":True,"charts":[w]},w]
    page.locator("#msg-input").fill("Show AAPL financial statements")
    page.locator("#send-btn").click()
    expect(page.locator(".msg.assistant .msg-prose")).to_have_text("A corrected answer.")
    page.wait_for_timeout(100)
    expect(page.locator(".mmb-f-card")).to_have_count(0)

def test_standalone_reuses_v1_and_shared_dom_markdown(standalone):
    page,state=standalone
    state["visual"]=sample()
    page.get_by_role("button",name="History",exact=True).click()
    page.get_by_text("Retained statement",exact=True).click()
    expect(page.locator(".mmb-v")).to_have_count(1)
    assert page.locator(".mmb-v").evaluate("(e)=>getComputedStyle(e).borderTopWidth")=="1px"
    page.evaluate("""()=>{
      const host=document.querySelector('.msg-prose');
      MMBrainMarkdown.renderInto(host,'| Metric | Value |\\n| --- | --- |\\n| Revenue | 10 |\\n\\n<script>alert(1)</script>');
    }""")
    expect(page.locator(".msg-prose table")).to_have_count(1)
    expect(page.locator(".msg-prose script")).to_have_count(0)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")


def test_standalone_explains_withheld_history_evidence(standalone):
    page,state=standalone
    state["notices"]=[{"type":"membership_required","template":"transcript"}]
    page.get_by_role("button",name="History",exact=True).click()
    page.get_by_text("Retained statement",exact=True).click()
    expect(page.locator(".mmb-visual-notice .l-en")).to_contain_text("requires membership")
    page.evaluate("document.documentElement.dataset.lang='zh';document.dispatchEvent(new Event('langchange'))")
    expect(page.locator(".mmb-visual-notice .l-zh")).to_be_visible()
    page.evaluate("window.__onAuth({id:'user-B'})")
    expect(page.locator(".mmb-visual-notice")).to_have_count(0)


@pytest.mark.parametrize("width,height,min_card_width",[(390,844,300),(1440,900,650)])
def test_short_answer_financial_card_uses_available_reading_width(standalone,width,height,min_card_width):
    page,state=standalone
    page.set_viewport_size({"width":width,"height":height})
    if page.locator("#chat-history-toggle").is_visible():
        page.locator("#chat-history-toggle").click()
    page.get_by_text("Retained statement",exact=True).click()
    card=page.locator(".mmb-f-card")
    expect(card).to_have_count(1)
    expect(card).to_be_visible()
    box=card.bounding_box()
    assert box and box["width"]>=min_card_width
    assert box["x"]>=0 and box["x"]+box["width"]<=width
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    if width>540:
        expect(card.locator("table")).to_be_visible()
    else:
        expect(card.locator(".mmb-f-period-detail")).to_be_visible()
