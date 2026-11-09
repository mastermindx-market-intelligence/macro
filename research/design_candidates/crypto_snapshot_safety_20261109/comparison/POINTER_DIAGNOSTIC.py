import json, os
from pathlib import Path
from test_crypto_intelligence_r4_browser import comparison_page, browser, page_url

def test_comparison_pointer_diagnostic(comparison_page):
    page, _ = comparison_page("en",390,"mixed")
    page.locator('[data-asset-row="SOL"] .cri-asset').click()
    page.locator("#cri-dialog-close").click()
    page.wait_for_function("location.hash==='#markets'&&!document.getElementById('cri-dialog').open")
    out=Path(os.environ["MMX_COMPARISON_DIAGNOSTIC_DIR"]);out.mkdir(parents=True,exist_ok=True)
    def state():
        return page.evaluate("""()=>({
          url:location.href,active:document.activeElement?.outerHTML,
          hovered:[...document.querySelectorAll(':hover')].map(n=>({tag:n.tagName,id:n.id,cls:n.className})).slice(-10),
          nav:[...document.querySelectorAll('#settings-pop,#settings-trigger,#btn-settings,.cri-heading [data-open="comparison"],.site-nav')].map(n=>{
            const b=n.getBoundingClientRect(),s=getComputedStyle(n);return{id:n.id,cls:n.className,box:{x:b.x,y:b.y,width:b.width,height:b.height},display:s.display,visibility:s.visibility,pointerEvents:s.pointerEvents};
          }),scroll:scrollY
        })""")
    before=state();page.screenshot(path=str(out/"after-close.png"))
    page.mouse.move(10,780)
    after=state()
    page.locator('[data-view="markets"] [data-open="comparison"]').click()
    page.wait_for_function("document.getElementById('cri-dialog-body').dataset.panel==='comparison'")
    (out/"pointer.json").write_text(json.dumps({"before":before,"after_pointer_leave":after,"comparison_opened_after_leaving":True},ensure_ascii=False,indent=2)+"\n")
