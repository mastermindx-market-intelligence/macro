"""Synthetic Chromium integration for the inert client, not production/browser auth."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(_ROOT))
from engine.market_navigator import Receipt,Observation,Condition,Scenario,compose
from engine.market_navigator_response import bind_response
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    cutoff='2026-10-21T20:01:00Z'
    receipt=Receipt('fixture:browser','synthetic-v1','2026-10-21T20:00:00Z',
        '2026-10-21T20:00:01Z','2026-10-21T20:00:02Z','2026-10-21T20:05:00Z')
    row=Observation('price','SPY:ARCX','price',100.0,'USD',('intraday',),receipt)
    rule=Scenario(key='reclaim',subject='SPY:ARCX',horizon='intraday',
        definition_available_at='2026-10-21T19:00:00Z',definition_ref='fixture:rule',
        deadline='2026-10-21T20:04:00Z',triggers=(Condition('price','gt',101,'USD'),),
        invalidations=(Condition('price','lt',98,'USD'),))
    context=compose(subject='SPY:ARCX',horizon='intraday',as_of=cutoff,observations=(row,),scenarios=(rule,))
    wire=bind_response(context,request_id='fixture',expected_subject='SPY:ARCX',expected_horizon='intraday',requested_as_of=cutoff)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page();errors=[];requests=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.resource_type))
        page.set_content('<main id="state" aria-live="polite">Synthetic client test</main>')
        page.add_script_tag(path=str(_ROOT/'templates/market_navigator_client.js'))
        result=page.evaluate('''async (wire) => {
          const api=globalThis.MastermindNavigatorClient, pending=[], states=[], checks=[], storage=[];
          ['getItem','setItem','removeItem','clear'].forEach(name=>{Storage.prototype[name]=function(){storage.push(name);throw new Error('unexpected storage');};});
          const copy=x=>JSON.parse(JSON.stringify(x));
          const check=(name,truth)=>{if(!truth)throw new Error(name);checks.push(name);};
          window.fetch=()=>{throw new Error('unexpected network');};
          const c=api.createController({read:(request,signal)=>new Promise((resolve,reject)=>pending.push({request,signal,resolve,reject})),
            render:state=>{states.push(state);document.getElementById('state').textContent=state.status;}});
          const q={subject:'SPY:ARCX',horizon:'intraday',as_of:wire.requested_as_of};
          const response=p=>({...copy(wire),request_id:p.request.request_id});
          const a=c.load(q);check('loading_clears_content',states.at(-1).data===null);
          const b=c.load({...q,subject:'QQQ:XNAS'});check('superseded_read_aborted',pending[0].signal.aborted);
          pending[1].resolve(response(pending[1]));await b;
          check('current_response_delivered',states.at(-1).status==='recorded_context');
          const count=states.length;pending[0].resolve(response(pending[0]));await a;
          check('late_response_ignored',states.length===count);
          const d=c.load(q),bad=response(pending[2]);bad.data.as_of='2026-10-21T20:01:00.000001Z';pending[2].resolve(bad);await d;
          check('microsecond_mismatch_rejected',states.at(-1).status==='invalid_response');
          const e=c.load(q);pending[3].reject(new Error('sensitive upstream detail'));await e;
          check('errors_sanitized',states.at(-1).status==='unavailable'&&!JSON.stringify(states).includes('sensitive'));
          check('no_automatic_retry',pending.length===4);
          const f=c.load(q);c.clear();const n=states.length;pending[4].resolve(response(pending[4]));await f;
          check('clear_cancels_inflight_result',states.length===n&&states.at(-1).data===null);
          c.dispose();check('all_payload_authority_false',states.filter(s=>s.data).every(s=>Object.values(s.data.authority).every(v=>v===false)));
          check('no_browser_storage_access',storage.length===0);
          return {checks,passed:checks.length,final_state:states.at(-1).status,storage_accesses:storage.length};
        }''',wire)
        report={'schema':'market_navigator.client_browser_proof/v1','evidence_class':'SYNTHETIC_LOCAL_BROWSER',
            'browser':browser.version,'production_proof':False,'paper_applied':False,
            'authenticated_source_read':False,'network_requests':len(requests),'page_errors':errors,**result}
        browser.close()
    if errors:raise RuntimeError(errors)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
