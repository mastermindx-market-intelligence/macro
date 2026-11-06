"""Local browser fixtures only; never authenticated production or scientific-event proof."""
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import functools, threading, json, hashlib
from playwright.sync_api import sync_playwright
from jinja2 import Environment, FileSystemLoader
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        if self.path == '/__risk_component.html':
            body=fixture_html.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        else: super().do_GET()
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT/'site')))
threading.Thread(target=server.serve_forever,daemon=True).start()
settled=json.loads((ROOT/'site/riskdata/risk_envelope.json').read_text())
env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=True)
template=env.get_template('_risk_envelope_band.html.j2')
hint=template.make_module({'risk_envelope':None}).risk_button_context(settled)
component=template.render(risk_envelope=settled)
css=env.get_template('_risk_envelope_band.css.j2').render()
fixture_html='<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="theme.css"><style>'+css+'</style></head><body><main style="max-width:900px;margin:16px auto;padding:12px"><button id="mx5BtnRisk"><span class="l-en">Risk Radar · 56</span><span class="l-zh">风险雷达 · 56</span>'+str(hint)+'</button><div id="dlg-risk">'+component+'</div></main><script src="risk_envelope_live.js"></script></body></html>'
rows=[]
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for width,height in [(1440,900),(390,844)]:
            for lang in ['en','zh']:
                for theme in ['light','dark']:
                    feed=deepcopy(settled)
                    feed.update(revision='live_provisional',precedence='live',live_active=True,source_session='2026-09-19',built='2026-09-19 15:00:00 UTC',stale_after_min=5,overlays={'settled_bundle_id':settled['bundle_id']},live_transition={'candidate_stage':'FRAGILE','stable_stage':'FRAGILE','pending':None})
                    mode={'fail':False,'requests':0}
                    context=browser.new_context(viewport={'width':width,'height':height},color_scheme=theme)
                    context.add_init_script('window.LIVE_POLL_SEC=15;localStorage.setItem("theme",'+json.dumps(theme)+');localStorage.removeItem("themeAuto");localStorage.setItem("lang",'+json.dumps(lang)+');')
                    page=context.new_page(); errors=[]
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    page.clock.install(time=datetime(2026,9,19,15,0,1,tzinfo=timezone.utc))
                    def respond(route):
                        mode['requests']+=1
                        if mode['fail']: route.abort('failed')
                        else: route.fulfill(status=200,content_type='application/json',body=json.dumps(feed))
                    page.route('**/live/risk_envelope.json*',respond)
                    response=page.goto('http://127.0.0.1:'+str(server.server_port)+'/__risk_component.html',wait_until='domcontentloaded')
                    assert response and response.ok
                    page.clock.run_for(2000);page.wait_for_timeout(250)
                    page.evaluate('(s)=>{document.documentElement.dataset.theme=s.theme;document.documentElement.dataset.lang=s.lang;}',{'theme':theme,'lang':lang})
                    button=page.locator('#mx5BtnRisk')
                    baseline=page.locator('#risk-envelope-band .gde-reads').inner_text()
                    radar_text=button.locator(':scope > .l-en').text_content()
                    def capture(phase):
                        assert page.locator('#risk-envelope-band .gde-reads').inner_text()==baseline
                        assert button.locator(':scope > .l-en').text_content()==radar_text
                        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                        name=f'{width}-{lang}-{theme}-component-{phase}.png'
                        page.screenshot(path=str(OUT/name),full_page=False)
                        return {'phase':phase,'file':name,'hint':page.locator('#gde-button-context').inner_text(),'live_visible':page.locator('#gde-live-reading').is_visible(),'fallback_visible':page.locator('#gde-live-fallback').is_visible(),'settled_read_unchanged':True,'radar_score_unchanged':True}
                    assert page.locator('#gde-live-reading').is_visible()
                    phases=[capture('healthy')]
                    feed['hazard_summary']['stage']='TRANSMITTING'
                    feed['live_transition'].update(candidate_stage='TRANSMITTING',pending={'stage':'TRANSMITTING','ticks':1,'needs':2})
                    page.clock.fast_forward(16000);page.wait_for_timeout(250)
                    assert page.locator('#gde-button-context .l-en').text_content()=='Live: Checking stress'
                    phases.append(capture('pending'))
                    summary=page.locator('#risk-envelope-band summary');summary.focus();page.keyboard.press('Enter')
                    assert page.locator('#gde-live-sources').is_visible()
                    assert settled['provenance']['sources'][0]['as_of'] in page.locator('#gde-live-source-rows').inner_text()
                    page.keyboard.press('Enter')
                    mode['fail']=True
                    page.clock.fast_forward(16000);page.wait_for_timeout(250)
                    assert not page.locator('#gde-live-reading').is_visible()
                    assert page.locator('#gde-live-fallback').is_visible()
                    assert page.locator('#gde-button-context .l-en').text_content()=='Fragile internals'
                    phases.append(capture('network-fallback'))
                    mode['fail']=False
                    feed['live_transition'].update(stable_stage='TRANSMITTING',pending=None)
                    page.clock.fast_forward(16000);page.wait_for_timeout(250)
                    assert page.locator('#gde-live-reading').is_visible()
                    assert not page.locator('#gde-live-fallback').is_visible()
                    assert page.locator('#gde-button-context .l-en').text_content()=='Live: Stress spreading'
                    phases.append(capture('recovery'))
                    assert not errors,errors
                    rows.append({'width':width,'lang':lang,'theme':theme,'phases':phases,'errors':errors,'request_count':mode['requests'],'source_dates_verified':True})
                    context.close()
        browser.close()
    result={'mode':'isolated production partial and shipped poller; synthetic live responses and virtual browser clock','authenticated_production':False,'natural_market_event':False,'page_sha256':hashlib.sha256((ROOT/'site/macro.html').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256((ROOT/'site/risk_envelope_live.js').read_bytes()).hexdigest(),'rows':rows}
    (OUT/'live-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print('LIVE_COMPONENT_PROOF',len(rows),'cells',sum(len(row['phases']) for row in rows),'observed states')
finally:
    server.shutdown();server.server_close()
