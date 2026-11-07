"""Capture actual Brain surfaces through the existing canonical evidence owner.

Uses hermetic API/auth fixtures, never a real credential or model. AAPL statements
are an immutable public-source specimen; every other market value/quote is a
synthetic UI fixture. No screenshot is production or live-model acceptance.
"""
from __future__ import annotations
import hashlib
import json
import mimetypes
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, date
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import expect
from scripts import capture_page_evidence as house
from engine.neuralweb import brain_financial_views as fv
from tests.test_brain_history_widget import page as shared_fixture
from tests.test_brain_financial_standalone import standalone as standalone_fixture
from tests.test_brain_financial_widget import assets
from tests.test_brain_visuals_widget import TID
from tests.test_brain_chart_price_controls import source, chart, bars
from tests.test_brain_financial_views import exact_wire

OUT=ROOT/"mockups/evidence/brain-intelligent-output"
CASES=("statement","statement-lower","price","company","quotes","summary","math","technical","standalone")
COPY_EN="Illustrative UI fixture. These example values are not live market data."
COPY_ZH="图解界面示例。示例数值并非实时市场数据。"


def specimen():
    statement=json.loads((Path(__file__).with_name("statement-public-AAPL.json")).read_text())
    assert fv.validate_financial_view(statement)
    daily=bars(date(2025,1,1))
    price=fv.compile_financial_widget({"template":"price","symbol":"EXAMPLE"},
        {"reader":"get_quote","call_id":"illustrative-price","result":{
            "symbol":"EXAMPLE","quote":{"symbol":"EXAMPLE","price":daily[-1][4],
            "prev_close":daily[-2][4],"change_pct":.07,"as_of":daily[-1][0],
            "source":"Illustrative fixture","live":False},"currency":"USD",
            "bars":[{"date":b[0],"close":b[4]} for b in daily],"history_asof":daily[-1][0]}},"illustrative-price")
    company=fv.compile_financial_widget({"template":"company","symbol":"EXAMPLE"},
        {"reader":"get_fundamentals","call_id":"illustrative-company","result":{
            "symbol":"EXAMPLE","asof":"2026-10-21","profile":{"name":"Example Research Company",
            "sector":"Technology","description":"An illustrative company profile for reviewing the interface. No investment conclusion is implied.",
            "mktcap_bn":10.5},"valuation":{"trailing_pe":24.1,"forward_pe":21.3,"price_to_book":3.2,"price_to_sales":5.4}}},"illustrative-company")
    summary=fv.compile_financial_widget({"template":"transcript","symbol":"EXAMPLE"},
        {"reader":"get_earnings","call_id":"illustrative-summary","result":{"symbol":"EXAMPLE",
            "latest_earnings_call":{"summary":"In this fictional example, management discussed demand, operating costs and cash generation. This is an AI-assisted summary, not an exact quotation.",
            "fiscal_period":"Q3 2026","call_date":"2026-10-21"}}},"illustrative-summary")
    with tempfile.TemporaryDirectory(prefix="brain-evidence-quote-") as folder:
        quotes=exact_wire(Path(folder))
    result={"statement":statement,"statement-lower":statement,"price":price,"company":company,
            "quotes":quotes,"summary":summary,"standalone":statement}
    assert all(fv.validate_financial_view(v) for v in result.values())
    return result


def local_asset(route):
    name=urlsplit(route.request.url).path.lstrip("/")
    candidate=ROOT/"templates"/name
    if not candidate.is_file():
        candidate=ROOT/"site"/name
    if candidate.is_file():
        return route.fulfill(content_type=mimetypes.guess_type(name)[0] or "application/octet-stream",
                             body=candidate.read_bytes())
    return route.abort()


class Driver:
    def __init__(self,wires):
        self.wires=wires

    def capture(self,*,url,cell,timeout_s):
        case=cell.page_id.removeprefix("brain-output-")
        generator=standalone_fixture.__wrapped__() if case=="standalone" else shared_fixture.__wrapped__()
        initial=next(generator)
        page=initial[0] if case=="standalone" else initial
        errors=[];failures=[];counts={"requests":0,"bytes":0}
        page.on("pageerror",lambda e:errors.append({"text":str(e),"source_url":None}))
        page.on("console",lambda e:errors.append({"text":e.text,"source_url":(e.location or {}).get("url")}) if e.type=="error" else None)
        page.on("response",lambda r:failures.append({"url":r.url,"status":r.status}) if r.status>=400 else None)
        page.on("request",lambda r:counts.__setitem__("requests",counts["requests"]+1))
        def finished(request):
            try:counts["bytes"]+=int(request.sizes().get("responseBodySize") or 0)
            except Exception:pass
        page.on("requestfinished",finished)
        try:
            page.set_viewport_size({"width":cell.width,"height":cell.height})
            page.emulate_media(color_scheme=cell.theme,reduced_motion="reduce")
            page.evaluate("""s=>{
              document.documentElement.dataset.theme=s.theme;
              document.documentElement.dataset.lang=s.locale;
              document.documentElement.lang=s.locale==='zh'?'zh-CN':'en';
              localStorage.setItem('theme',s.theme);localStorage.setItem('lang',s.locale);
              document.dispatchEvent(new Event('themechange'));document.dispatchEvent(new Event('langchange'));
            }""",{"theme":cell.theme,"locale":cell.locale})
            if case=="standalone":
                state=initial[1];state["visual"]=self.wires[case]
                if page.locator("#chat-history-toggle").is_visible():page.locator("#chat-history-toggle").click()
                page.get_by_text("Retained statement",exact=True).click()
                expect(page.locator(".mmb-f-card")).to_have_count(1)
                page.locator("#msg-list").evaluate("(e)=>e.scrollTop=0")
            else:
                page.route("**/*",local_asset)
                assets(page)
                page.add_style_tag(path=str(ROOT/"templates/theme.css"))
                if case=="technical":
                    source(page,bars())
                    chart(page)
                    expect(page.locator(".mmb-cx-body > svg")).to_have_count(1)
                else:
                    content=(COPY_ZH if cell.locale=="zh" else COPY_EN)
                    if case.startswith("statement"):
                        content="AAPL · Public statement snapshot · 2026-10-21" if cell.locale=="en" else "AAPL · 公开财务报表快照 · 2026-10-21"
                    if case=="math":
                        content=("Discounted cash flow — illustrative formulation." if cell.locale=="en" else "现金流折现：示例公式。")
                        content+="\n\n"+r"\[V=\sum_{t=1}^{T}\frac{FCF_t}{(1+r)^t}+\frac{TV}{(1+r)^T}\]"
                        content+="\n\n> Assumptions are explicit. Typesetting does not calculate a valuation."
                        content+="\n\n| Input | Example |\n| --- | --- |\n| Discount rate | 8% |\n| Currency | USD |"
                        content+="\n\nPrice remains ordinary currency text: $120."
                    w=self.wires.get(case)
                    page.evaluate("""([wire,text,tid])=>{
                      const old=window.fetch;
                      window.fetch=(url,options={})=>url.endsWith('/'+tid)?Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({
                        thread:{id:tid},messages:[{role:'assistant',content:text,visuals:wire?[wire]:[]}]})}):old(url,options);
                    }""",[w,content,TID])
                    menu=page.locator('.mmb-menu[data-act="side"]')
                    if menu.is_visible() and not page.locator(".mmb-threads").is_visible():
                        menu.click()
                    page.locator(f'.mmb-ti[data-id="{TID}"] .mmb-ti-body').click()
                    expect(page.locator("math" if case=="math" else ".mmb-f-card")).to_have_count(1)
                page.locator("#mmb-scroll").evaluate("(e)=>e.scrollTop=0")
                if case=="statement-lower":
                    page.locator("#mmb-scroll").evaluate("(e)=>e.scrollTop=e.scrollHeight")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(220)
            applied_force=None
            if cell.force_state:
                applied_force=house._apply_interaction_force(page,cell.force_state,timeout_ms=3000)
                page.wait_for_timeout(180)
            applied=page.evaluate("({theme:document.documentElement.dataset.theme,locale:document.documentElement.dataset.lang})")
            observed=page.evaluate(house._OBSERVER_SCRIPT,house.DEFAULT_OBSERVER_CONFIG) or {}
            screenshot=page.screenshot(full_page=False)
            return house.CellObservation(cell_id=cell.cell_id,loaded=True,screenshot_png=screenshot,
                observed=observed,console_errors=tuple(errors),failed_responses=tuple(failures),
                request_count=counts["requests"],payload_bytes_total=counts["bytes"],
                applied_theme=applied["theme"],applied_locale=applied["locale"],
                applied_force_state=applied_force,timing=None)
        except Exception as error:
            return house.CellObservation(cell_id=cell.cell_id,loaded=False,error=str(error),
                console_errors=tuple(errors),failed_responses=tuple(failures))
        finally:
            try:next(generator)
            except StopIteration:pass


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    wires=specimen()
    assets_names=("mm_brain.js","mm_brain_finance.js","mm_brain_finance.css","mm_brain_presentation.js",
                  "mm_brain_math.js","mm_brain_markdown.js","chat.css","chat.html")
    target={"kind":"local-hermetic-widget-fixture",
        "resolved_sha_or_none":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "asset_sha256":{n:hashlib.sha256((ROOT/"templates"/n).read_bytes()).hexdigest() for n in assets_names},
        "recipe_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "statement_snapshot_id":wires["statement"]["visual"]["source"]["snapshot_id"],
        "source_note":"Working-tree assets at capture; HEAD is only the parent checkpoint. No live gateway/provider or production proof."}
    generated=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifests=[];smells=[];smell_document=None
    for case in CASES:
        selector='.mmb-f-body > .mmb-f-controls:first-child > button:first-child' if case=="statement" else '.mmb-cx-ranges button[data-range="1M"]'
        forced=house.parse_force_states((f"{case}-hover:hover({selector})",f"{case}-focus:focus({selector})")) if case in {"statement","technical"} else ()
        result=house.run_capture(rows=[{"page_id":"brain-output-"+case,"capture_route":case+".html","route_kind":"hermetic chat specimen"}],
            driver=Driver(wires),base_url="http://brain-output-fixture.test",output_dir=OUT,manifest_dir=OUT,
            viewports=("desktop","mobile"),locales=("en","zh"),themes=("dark","light"),
            delay_ms=220,timeout_s=20,generated_at=generated,target=target,
            selection={"fixture":case},force_states=forced)
        manifests.append(result["manifest"]);smells.extend(result["smells"]["pages"])
        if smell_document is None:smell_document=result["smells"]
        print(case,result["manifest"]["totals"],flush=True)
    manifest=manifests[0]
    manifest["pages"]=[page for m in manifests for page in m["pages"]]
    manifest["selection"]={"fixtures":list(CASES),"adapter":str(Path(__file__).relative_to(ROOT))}
    manifest["axes"]["force_states"]=[s for m in manifests for s in m["axes"]["force_states"]]
    manifest["totals"]={"pages":len(manifest["pages"]),
        "states_attempted":sum(len(p["states"]) for p in manifest["pages"]),
        "states_captured":sum(bool(s.get("captured")) for p in manifest["pages"] for s in p["states"])}
    manifest["honesty"]["access"]="Existing hermetic auth/API fixture only. No real credentials, membership, gateway or model request; synthetic quote evidence is fixture text."
    manifest["honesty"]["data"]="AAPL statement is a fixed public snapshot. Other prices, company metrics and transcript content are explicitly illustrative."
    manifest["honesty"]["metrics"]="Request/payload observations begin after fixture bootstrap; timing is unmeasured. Viewport captures show real chat composition; statement-lower shows the message scroll bottom."
    manifest["outcome"]="captured" if manifest["totals"]["states_captured"]==manifest["totals"]["states_attempted"] else "partial"
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    smell_document["pages"]=smells
    (OUT/"smells.json").write_text(json.dumps(smell_document,ensure_ascii=False,indent=2)+"\n")
    paths=[f"{folder}/{name}" for folder in ("templates","site") for name in assets_names]
    (OUT/"EVIDENCE.yml").write_text("schema: mastermind.page_evidence_receipt.v1\nchanged_paths:\n"+
        "".join("  - "+p+"\n" for p in paths)+"manifest: mockups/evidence/brain-intelligent-output/manifest.json\n")
    print(json.dumps(manifest["totals"]),flush=True)
    return 0 if manifest["outcome"]=="captured" else 1


if __name__=="__main__":
    raise SystemExit(main())
