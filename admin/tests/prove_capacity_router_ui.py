"""Real Chromium UI proof using a deterministic, content-free router fixture.

No provider calls or production authentication. Screenshots are synthetic QA,
not evidence of production deployment. Run with an installed Playwright browser.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import time

from playwright.sync_api import sync_playwright
from admin.capacity_fabric_schema import SCHEMA, TOKEN_FIELDS, clean_snapshot
from admin.capacity_router import panel
from admin.capacity_intelligence import analyze
from admin.capacity_stream import delta

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__import__('os').environ.get('CAPACITY_UI_PROOF_DIR', str(ROOT / 'verify_shots/capacity-router-upgrade-20261113')))


def fixture():
    now = time.time()
    routes = [{'id':f'route-{i:02}', 'provider':f'pool-{i%36:02}', 'wire':'anthropic',
        'models':[f'model-{(i*2+j)%60:02}' for j in range(2)],'priority':10,'weight':1,
        'cooling':i%11==0,'served':100+i,'attempt_failed':i%5,'refused':0} for i in range(37)]
    records=[]
    for i in range(144):
        route=routes[i%37];active=i<24;usage={k:None for k in TOKEN_FIELDS};usage.update(input_tokens=100+i,output_tokens=None if i%7==0 else 20+i)
        records.append({'id':f'{i+1:032x}','started_at':now-30-i*2,'ended_at':None if active else now-i,
            'last_activity_at':now-.2 if active else now-i,'first_content_at':now-20-i*2,
            'state':'streaming' if active else 'completed','status_code':200,'provider':route['provider'],
            'route_id':route['id'],'requested_model':route['models'][0],'served_model':route['models'][0],
            'lane':'fabric/balanced','client':'T3','agent_id':f'{1000+i//2:032x}',
            'parent_agent_id':f'{1000:032x}' if i>2 and i%4==0 else None,'session_id':f'{2000+i:032x}',
            'usage':usage,'usage_source':'provider_reported','usage_final':not active,'streaming':active,'content_events':i+4,'attempts':[]})
    series=[{'at':int(now//60)*60-i*60,'completed':i+5,'failed':0,'usage_known':i+4,
        'input_tokens':2000+i*100,'output_tokens':200+i*20,'input_tokens_known':i+4,'output_tokens_known':i+4} for i in range(30)]
    raw={'schema':SCHEMA,'epoch':'f'*32,'sequence':1,'started_at':now-7200,'generated_at':now,
        'routes':routes,'aliases':{'fabric/balanced':[f'model-{i:02}' for i in range(12)],'fabric/fast':['model-12','model-13'], 'fabric/frontier':['model-58','model-59']},
        'active':records[:24],'recent':records[24:],'series':series,'totals':{},'history_state':'recorded',
        'claude':{'reachable':True,'observed_at':now,'stranded_family':'fable','accounts':[
            {'id':'abcd1234','label':'max-4','used_5h':0,'budget_5h':1000,'remaining_5h':1000,
             'inflight':0,'last_status':'window_rolled','drain':False,
             'families':{name:{'used_weekly':0,'budget_weekly':limit,'remaining_weekly':limit,
                 'cooldown_until':now+1800,'weekly_resets_at':now+3600,
                 'weekly_reset_source':'provider'} for name,limit in
                 [('fable',4000),('opus',1400),('sonnet',1000),('haiku',500),('other',100)]}},
            {'id':'efgh5678','label':'max-3','used_5h':None,'budget_5h':1000,'remaining_5h':None,
             'inflight':0,'last_status':'ok','drain':False,
             'families':{'opus':{'used_weekly':None,'budget_weekly':1400,
                 'remaining_weekly':1390,'cooldown_until':None,'weekly_resets_at':now+3600,
                 'weekly_reset_source':'estimated'}}}
        ]}}
    raw=clean_snapshot(raw)
    with tempfile.TemporaryDirectory() as temp:
        p=Path(temp)/'snapshot.json';p.write_text(json.dumps(raw));data=panel(60,path=p,now=now)
    history={'ok':True,'all_time':True,'start':now-86400,'end':now,'observed_through':now,'resolution_s':300,
        'series':data['series'],'summary':{'requests':120,'input_tokens':300000,'output_tokens':10000,'cache_read_tokens':None,'cache_write_tokens':0},
        'models':[],'pools':[],'demand':[],'coverage':{'epochs':2,'totals_since':now-86400,'time_series_since':now-7200,
        'model_pool_since':now-7200,'model_pool_requests':120,'counter_requests':200,'ingestion_gaps':1,'detailed_retention_days':7,'series_retention_days':400}}
    return data,history


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    data,history=fixture();errors=[];proof={}
    controls={'ok':True,'writable':False,'routes':data['routes'],'aliases':data['aliases'],
              'epoch':data['epoch'],'revision':'b'*64,'effective_revision':'b'*64,'interval_s':2,
              'message':'Fixture: native configuration owner.'}
    control_calls=[];uncertain_apply=[False]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1080},device_scale_factor=1,timezone_id='America/Los_Angeles')
        context.add_init_script('''window.__streams=[];window.EventSource=class {constructor(url){this.url=url;this.listeners={};window.__streams.push(this);}addEventListener(n,f){this.listeners[n]=f;}close(){this.closed=true;}emit(n,data){if(!this.closed&&this.listeners[n])this.listeners[n]({data:JSON.stringify(data)});}};''')
        html='''<!doctype html><html data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/capacity-router.css"></head><body><main id="fixture-root" style="padding:20px;max-width:100%;min-width:0"></main><script src="/capacity-router.js"></script><script>window.fixtureState=CapacityRouter.mount(document.querySelector('#fixture-root'));</script></body></html>'''
        def respond(route):
            path=route.request.url.split('capacity.test',1)[-1].split('?')[0]
            if path=='/':return route.fulfill(content_type='text/html',body=html)
            if path in ['/styles.css','/capacity-router.css','/capacity-router.js']:
                return route.fulfill(content_type='text/javascript' if path.endswith('.js') else 'text/css',body=(ROOT/'admin/static'/path[1:]).read_text())
            if path=='/api/capacity-router':return route.fulfill(json=data)
            if path=='/api/capacity-router/history':return route.fulfill(json=history)
            if path=='/api/capacity-router/intelligence':return route.fulfill(json=analyze(data,history,now=data['generated_at']))
            if path=='/api/capacity-router/settings':
                if route.request.method=='GET':return route.fulfill(json=controls)
                body=route.request.post_data_json;control_calls.append(body)
                operation=f'{len(control_calls):032x}'
                if body['action']=='reconcile':
                    assert body['operation_id']==controls['last_operation']['operation_id']
                    receipt=dict(controls['last_operation'],state='APPLIED',ok=True)
                    controls.update(writable=True,last_operation=receipt)
                    return route.fulfill(json=receipt)
                if body['expected_revision']!=controls['revision']:
                    return route.fulfill(status=409,json={'ok':False,'state':'CONFLICT','code':'CONFIGURATION_REVISION_CHANGED'})
                if body['action']=='validate':return route.fulfill(json={'ok':True,'state':'VALIDATED','operation_id':operation})
                controls['interval_s']=body['patch'].get('interval_s',controls['interval_s'])
                controls['revision']=controls['effective_revision']=f'{len(control_calls):064x}'
                if uncertain_apply[0]:
                    receipt={'ok':False,'state':'EFFECT_UNKNOWN','operation_id':operation}
                    controls.update(writable=False,last_operation=receipt)
                    return route.fulfill(status=202,json=receipt)
                return route.fulfill(json={'ok':True,'state':'APPLIED','operation_id':operation})
            return route.fulfill(status=404,json={'error':'fixture route not provided'})
        context.route('https://capacity.test/**',respond)
        page=context.new_page();page.on('pageerror',lambda e:(errors.append(str(e)),print('BROWSER_ERROR',str(e),flush=True)))
        page.goto('https://capacity.test/');page.wait_for_selector('.cf-node')
        proof['topology_nodes']=page.locator('.cf-node').count();proof['topology_edges']=page.locator('.cf-edge').count()
        assert proof['topology_nodes']>=36+37+60+4+72,proof
        assert page.locator('.cf-overflow').count()==0
        page.evaluate('window.retainedNode=document.querySelector(".cf-node")')
        topology_changed=copy.deepcopy(data);topology_changed['sequence']=2;topology_changed['active'][1]['content_events']+=1
        event,body=delta(data,topology_changed)
        page.evaluate('([event,body])=>window.__streams.at(-1).emit(event,body)',[event,body])
        assert page.evaluate('window.retainedNode===document.querySelector(".cf-node")'),'topology node replaced'
        proof['incremental_node_identity']=True;data=topology_changed
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        page.screenshot(path=str(OUT/'dark-topology.png'),full_page=True)
        page.locator('.cf-tabs [data-view=requests]').click();page.wait_for_selector('.cf-request-panel tbody tr')
        page.evaluate('window.retainedRow=document.querySelector(".cf-request-panel tbody tr")')
        changed=copy.deepcopy(data);changed['sequence']=3;changed['active'][0]['content_events']+=9;changed['active'][0]['usage']['output_tokens']=33
        event,body=delta(data,changed)
        page.evaluate('([event,body])=>window.__streams.at(-1).emit(event,body)',[event,body])
        assert page.evaluate('window.retainedRow===document.querySelector(".cf-request-panel tbody tr")'),'request row replaced'
        assert page.locator('.cf-request-panel tbody tr').first.get_attribute('data-version').endswith(':33')
        proof['incremental_row_identity']=True
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        page.screenshot(path=str(OUT/'dark-requests.png'),full_page=True)
        # Claude is a gateway observation, not an authoritative provider quota.
        # A five-hour counter of zero must not make a benched account "available".
        page.locator('.cf-tabs [data-view=claude]').click()
        page.wait_for_selector('.cf-cap-dashboard')
        assert page.locator('.cf-cap-account').count()==2
        assert '5' in page.locator('.cf-cap-stat').nth(1).inner_text()
        assert 'Benched' in page.locator('.cf-cap-dashboard').inner_text()
        assert '0 / 1,000 tracked units' in page.locator('.cf-cap-dashboard').inner_text()
        assert 'Unknown' in page.locator('.cf-cap-dashboard').inner_text()
        assert 'Gateway budget counters are not verified' in page.locator('.cf-cap-dashboard').inner_text()
        page.locator('[data-field=claude-family]').select_option('opus')
        assert page.locator('.cf-cap-lane').count()==2
        page.locator('[data-field=claude-family]').select_option('all')
        assert page.locator('.cf-cap-lane').count()==6
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        page.screenshot(path=str(OUT/'dark-claude-capacity.png'),full_page=True)
        # No current telemetry => no current quota percentage or active hold claim.
        page.evaluate('window.fixtureState.data.claude.observed_at -= 7200')
        page.locator('.cf-tabs [data-view=providers]').click()
        page.locator('.cf-tabs [data-view=claude]').click()
        assert 'Stale telemetry' in page.locator('.cf-cap-alert').inner_text()
        assert page.locator('.cf-cap-percent:not(.muted)').count()==0
        proof['claude_counters_freshness_benches_and_filters']=True
        # The global live strip must expire too, rather than displaying a stale
        # ten-request snapshot as ten requests currently executing.
        page.evaluate('window.fixtureState.data.generated_at -= 7200')
        page.wait_for_function('document.querySelector(".cf-metric strong").textContent.trim()==="—"')
        assert 'current unknown' in page.locator('.cf-metric').first.inner_text()
        page.evaluate('window.fixtureState.data.generated_at = Date.now()/1000')
        page.wait_for_function('document.querySelector(".cf-metric strong").textContent.trim()!=="—"')
        proof['router_live_metrics_expire_on_stale_snapshot']=True
        # Continue other proof views with restored fresh fixture.
        page.evaluate('window.fixtureState.data.claude.observed_at = Date.now()/1000')
        page.locator('.cf-tabs [data-view=providers]').click()
        page.locator('.cf-tabs [data-view=history]').click();page.wait_for_selector('.cf-history-metrics')
        page.locator('[data-field=window]').select_option('0');page.wait_for_selector('.cf-history-metrics')
        assert 'All recorded consumption' in page.locator('.cf-view').inner_text()
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        page.screenshot(path=str(OUT/'dark-history.png'),full_page=True)
        page.locator('.cf-tabs [data-view=intelligence]').click();page.wait_for_selector('.cf-intelligence-table')
        assert page.locator('.cf-intelligence-table tbody tr').count()==60
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        page.screenshot(path=str(OUT/'dark-intelligence.png'),full_page=True)
        page.locator('.cf-tabs [data-view=settings]').click();page.wait_for_selector('.cf-settings-form')
        assert page.locator('[data-action=apply-settings]').is_disabled()
        controls['writable']=True
        page.locator('[data-action=discard-settings]').click()
        page.wait_for_function('!document.querySelector("[data-setting=interval]").disabled')
        priority=page.locator('input[data-setting=priority]').first
        priority.fill('-1');page.locator('[data-action=preview-settings]').click()
        assert not control_calls,'invalid value reached transport'
        priority.fill('10')
        page.locator('[data-setting=interval]').select_option('0.5')
        page.locator('[data-action=preview-settings]').click()
        page.wait_for_function('!document.querySelector("[data-action=apply-settings]").disabled')
        page.locator('[data-setting=interval]').select_option('1')
        assert page.locator('[data-action=apply-settings]').is_disabled(),'edited form retained stale validation'
        page.locator('[data-setting=interval]').select_option('0.5')
        page.locator('[data-action=preview-settings]').click()
        page.wait_for_function('!document.querySelector("[data-action=apply-settings]").disabled')
        page.locator('[data-action=apply-settings]').click()
        page.wait_for_function('window.fixtureState.settings?.interval_s===0.5&&!window.fixtureState.settingsPending')
        assert controls['interval_s']==.5
        proof['settings_validation_and_explicit_apply']=True
        uncertain_apply[0]=True
        page.locator('[data-setting=interval]').select_option('1')
        page.locator('[data-action=preview-settings]').click()
        page.wait_for_function('!document.querySelector("[data-action=apply-settings]").disabled')
        page.locator('[data-action=apply-settings]').click()
        page.wait_for_function('window.fixtureState.settingsEffectUnknown&&!window.fixtureState.settingsPending')
        assert page.locator('[data-action=apply-settings]').is_disabled()
        count=sum(c['action']=='apply' for c in control_calls)
        page.locator('[data-action=discard-settings]').click()
        page.wait_for_function('window.fixtureState.settings?.writable&&!window.fixtureState.settingsPending')
        assert sum(c['action']=='apply' for c in control_calls)==count
        assert control_calls[-1]['action']=='reconcile'
        proof['settings_uncertainty_reconciled_without_apply_replay']=True
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        page.screenshot(path=str(OUT/'dark-settings.png'),full_page=True)
        page.evaluate('document.documentElement.dataset.theme="light"')
        page.locator('.cf-tabs [data-view=flow]').click();page.wait_for_selector('.cf-topology')
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        page.screenshot(path=str(OUT/'light-topology.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844});page.emulate_media(reduced_motion='reduce')
        page.evaluate('window.fixtureState.visibility()');page.wait_for_timeout(100)
        proof['mobile_overflow']=page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
        assert not proof['mobile_overflow'],'page overflows at 390px'
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        page.screenshot(path=str(OUT/'mobile-light-topology.png'),full_page=True)
        assert not errors,errors
        proof['page_errors']=errors;proof['themes']=['dark','light'];proof['viewports']=[1440,390];proof['source']='deterministic synthetic telemetry; not production'
        browser.close()
    (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))


if __name__=='__main__':
    run()
