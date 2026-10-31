"""Real shared widget: lazy asset loading, stream/done replay, and saved history.

API/model boundaries are deliberately hermetic; this is not live-provider proof.
"""
from pathlib import Path

from playwright.sync_api import expect

from tests.test_brain_history_widget import page  # noqa: F401 (existing auth/history fixture)
from tests.test_brain_visuals_browser import sample

ROOT = Path(__file__).resolve().parents[1]
TID = '11111111-1111-1111-1111-111111111111'


def assets(page):
    page.route('**/mm_brain_visuals.js*', lambda r: r.fulfill(content_type='application/javascript',body=(ROOT/'templates/mm_brain_visuals.js').read_text()))
    page.route('**/mm_brain_visuals.css*', lambda r: r.fulfill(content_type='text/css',body=(ROOT/'templates/mm_brain_visuals.css').read_text()))


def history(page, wire):
    page.evaluate('''([wire,tid])=>{
      const old=window.fetch;
      window.fetch=(url,options={})=>url.endsWith('/'+tid) ? Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({thread:{id:tid},messages:[{role:'assistant',content:'The direct answer comes first.',visuals:[wire,wire]}]})}) : old(url,options);
    }''',[wire,TID])
    page.locator(f'.mmb-ti[data-id="{TID}"] .mmb-ti-body').click()


def stream(page, events, hold=False):
    page.evaluate('''([events,hold])=>{
      const old=window.fetch;
      window.fetch=(url,options={})=>{
        if(!url.endsWith('/api/brain/stream'))return old(url,options);
        return Promise.resolve(new Response(new ReadableStream({start(controller){
          window.__visualController=controller;
          for(const e of events)controller.enqueue(new TextEncoder().encode('data: '+JSON.stringify(e)+'\\n\\n'));
          if(!hold)controller.close();
        }}),{headers:{'Content-Type':'text/event-stream'}}));
      };
    }''',[events,hold])
    page.locator('#mmb-ta').fill('Draw an illustrative comparison')
    page.locator('#mmb-send').click()


def test_history_loads_native_assets_and_keeps_answer_first(page):
    assets(page)
    history(page,sample())
    expect(page.locator('.mmb-v')).to_have_count(1)
    assert page.locator('.mmb-bub').last.evaluate('(e)=>e.querySelector(".mmb-txt").compareDocumentPosition(e.querySelector(".mmb-v")) & Node.DOCUMENT_POSITION_FOLLOWING')
    expect(page.locator('.mmb-v-plot svg')).to_be_visible()
    page.evaluate("window.__principal='B';window.__onAuth({id:'user-B'})")
    expect(page.locator('.mmb-v')).to_have_count(0)


def test_stream_and_done_deliver_exactly_one_visual_even_with_duplicates(page):
    assets(page)
    wire=sample()
    stream(page,[{'type':'meta','thread_id':TID},{'type':'delta','text':'The direct answer comes first.'},wire,wire,{'type':'done','charts':[wire], 'citations':[]}])
    expect(page.locator('.mmb-v')).to_have_count(1)
    expect(page.locator('.mmb-v-plot svg')).to_be_visible()


def test_done_before_late_chart_still_reconstructs_once(page):
    assets(page)
    wire=sample()
    stream(page,[{'type':'delta','text':'Answer.'},{'type':'done','charts':[wire],'citations':[]},wire])
    expect(page.locator('.mmb-v')).to_have_count(1)


def test_retract_and_filtered_done_do_not_resurrect_pending_visual(page):
    assets(page)
    wire=sample()
    stream(page,[{'type':'delta','text':'Rejected answer.'},wire,{'type':'retract','text':'Replaced answer.'},{'type':'done','charts':[wire],'filtered':True}])
    expect(page.locator('.mmb-txt')).to_contain_text('Replaced answer.')
    page.wait_for_timeout(200)
    expect(page.locator('.mmb-v')).to_have_count(0)


def test_stop_clears_visual_and_late_done_is_ignored(page):
    assets(page)
    wire=sample()
    stream(page,[{'type':'delta','text':'Partial answer.'},wire],hold=True)
    expect(page.locator('.mmb-v')).to_have_count(1)
    page.locator('#mmb-send').click()  # existing Stop control while streaming
    expect(page.locator('.mmb-v')).to_have_count(0)
    page.evaluate('''wire=>{try{window.__visualController.enqueue(new TextEncoder().encode('data: '+JSON.stringify({type:'done',charts:[wire]})+'\\n\\n'));window.__visualController.close();}catch(_){}}''',wire)
    page.wait_for_timeout(100)
    expect(page.locator('.mmb-v')).to_have_count(0)


def test_asset_failure_does_not_remove_text_answer(page):
    page.route('**/mm_brain_visuals.js*', lambda r:r.abort())
    page.route('**/mm_brain_visuals.css*', lambda r:r.abort())
    history(page,sample())
    expect(page.locator('.mmb-txt')).to_contain_text('The direct answer comes first.')
    expect(page.locator('[data-pending-visual]')).to_contain_text('could not load')


def test_expired_run_restores_visual_from_its_exact_saved_turn(page):
    assets(page)
    wire = sample()
    page.evaluate('''([wire,tid])=>{
      const old=window.fetch;
      window.fetch=(url,options={})=>{
        if(url.includes('/api/brain/runs/'))return Promise.resolve({ok:false,status:404});
        if(url.endsWith('/'+tid))return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({thread:{id:tid},messages:[
          {role:'user',content:'Draw an illustrative comparison'},
          {role:'assistant',content:'Recovered exact answer.',visuals:[wire]}
        ]})});
        return old(url,options);
      };
    }''', [wire,TID])
    stream(page,[{'type':'run','thread_id':TID,'run_id':'retained-visual-test'},{'type':'meta','thread_id':TID},{'type':'delta','text':'Partial.'}])
    expect(page.locator('.mmb-txt')).to_contain_text('Recovered exact answer.',timeout=10000)
    expect(page.locator('.mmb-v')).to_have_count(1)


def test_missing_css_never_silently_mounts_a_second_unstyled_visual(page):
    page.route('**/mm_brain_visuals.js*', lambda r:r.fulfill(content_type='application/javascript',body=(ROOT/'templates/mm_brain_visuals.js').read_text()))
    page.route('**/mm_brain_visuals.css*', lambda r:r.abort())
    wire = sample()
    history(page,wire)
    expect(page.locator('[data-pending-visual]')).to_contain_text('could not load')
    # The script may have loaded despite the failed stylesheet. A later card must
    # preserve the same explicit unavailable state, not use the unstyled module.
    history(page,sample(identity='second'))
    expect(page.locator('[data-pending-visual]')).to_contain_text('could not load')
    expect(page.locator('.mmb-v')).to_have_count(0)
