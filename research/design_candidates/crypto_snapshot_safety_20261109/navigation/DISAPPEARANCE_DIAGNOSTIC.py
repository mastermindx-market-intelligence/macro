import json
import test_crypto_intelligence_r4_browser as cases
from test_crypto_intelligence_r4_browser import browser, page_url, snapshot_page


def test_disappearance_event_order(snapshot_page):
    pages = []
    def factory(*args, **kwargs):
        page = snapshot_page(*args, **kwargs)
        pages.append(page)
        page.evaluate("""() => {
          window.__eventOrder=[];
          const get=Storage.prototype.getItem, set=Storage.prototype.setItem;
          Storage.prototype.getItem=function(key) {
            const result=get.call(this,key);
            if(key===__snapshotKey) __eventOrder.push({event:'read',panel:new URLSearchParams(location.hash.split('?')[1]).get('panel'),empty:result==='[]',title:document.getElementById('cri-dialog-title').textContent});
            return result;
          };
          window.addEventListener('popstate',()=>__eventOrder.push({event:'capture-observer',panel:new URLSearchParams(location.hash.split('?')[1]).get('panel'),raw:__snapshotNativeGet.call(localStorage,__snapshotKey)==='[]',title:document.getElementById('cri-dialog-title').textContent}),true);
          window.addEventListener('hashchange',()=>__eventOrder.push({event:'hashchange-observer',panel:new URLSearchParams(location.hash.split('?')[1]).get('panel'),raw:__snapshotNativeGet.call(localStorage,__snapshotKey)==='[]',title:document.getElementById('cri-dialog-title').textContent}));
        }""")
        return page
    try:
        cases.test_r4_saved_case_disappearing_during_back_does_not_restore_stale_content(factory)
    finally:
        print("EVENT_ORDER_DIAGNOSTIC", json.dumps(pages[0].evaluate("({events:__eventOrder,url:location.href,title:document.getElementById('cri-dialog-title').textContent,raw:__snapshotNativeGet.call(localStorage,__snapshotKey),active:document.activeElement.outerHTML.slice(0,300)})")))
