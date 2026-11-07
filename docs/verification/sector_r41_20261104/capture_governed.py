#!/usr/bin/env python3
"""Use the repository's canonical capture owner for R4.1 component evidence.

The served route is an isolated, labelled synthetic test fixture, NOT a deployed
product route. No production auth, data loader or navigation owner is replaced.
"""
from __future__ import annotations
import json
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as owner
from playwright.sync_api import sync_playwright

SITE = ROOT / '.pytest_cache/r41-component-site'
OUT = ROOT / 'mockups/evidence/sector-r41-dossier-component'
SITE.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
prelude = runpy.run_path(str(ROOT / 'tests/test_sector_dossier_cycle_js.py'))['PRELUDE']
fixture = json.loads(subprocess.check_output(['node','-e',prelude+';console.log(JSON.stringify(fixture()));',str(ROOT/'templates/sector_dossier_cycle.js')], text=True))
# More than two samples make visual chart review meaningful. These are explicit
# test-only observations, not inferred market data or a production fallback.
fixture['sectors'][0]['osc'] = [{'x':2024+i/12,'v':v} for i,v in enumerate([25,37,62,74,61,35,18,31,55,77,68,44,27,36,53,61,49,35,46,68,86,91,79,65,70,85,87,74])]
for name in ['theme.css','sector_dossier_cycle.js','sector_dossier_cycle.css']:
 (SITE/name).write_bytes((ROOT/'templates'/name).read_bytes())
(SITE/'mm_charts.js').write_bytes(subprocess.check_output(['git','-C',str(ROOT),'show','4a2291747fd2d8d364a3838e1ed2263636bc64a6:site/mm_charts.js']))
html='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>R4.1 Dossier component — synthetic fixture</title><link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="sector_dossier_cycle.css"><style>body{margin:0;background:var(--bg);color:var(--text)}main{padding:24px;max-width:1440px;margin:0 auto}.fixture-label{font:12px/1.5 var(--font-ui);color:var(--muted)}</style></head><body><main><p class="fixture-label">R4.1 COMPONENT · SYNTHETIC FIXTURE · NOT LIVE</p><div id="subject"></div><p id="fixture-action" role="status" class="fixture-label"></p></main><script src="mm_charts.js"></script><script src="sector_dossier_cycle.js"></script><script>
const source=__SOURCE__;let handle;
const action=s=>{document.querySelector('#fixture-action').textContent='Test callback received '+s.id+' at '+s.asOf;};
function render(){const locale=document.documentElement.dataset.lang==='zh'?'zh':'en';
 const options={accessState:'allowed',dataState:'ready',family:'sectors',id:'xle',locale,expectedAsOf:'2026-10-30',onMembers:action,onOpenCycles:action,onSources:action,
 renderChart:(root,context)=>MMChart.create(root,{xDomain:[2024,2026.3],yDomain:[0,100],yTicks:[{v:0,label:'0'},{v:50,label:'50'},{v:100,label:'100'}],animate:false,crosshair:true,zoom:true,padding:{t:16,r:16,b:32,l:42},series:[{id:context.record.id,label:'XLE · fixture',color:'var(--link)',hist:context.record.osc.map(p=>({x:p.x,y:p.v})),proj:[],markers:[]}]})};
 if(handle)handle.update(source,options);else handle=SectorDossierCycle.mount(document.querySelector('#subject'),source,options);}
window.setLang=lang=>{document.documentElement.dataset.lang=lang;document.documentElement.lang=lang==='zh'?'zh-CN':'en';render();};
window.setTheme=theme=>{document.documentElement.dataset.theme=theme;render();};
setTheme(localStorage.getItem('theme')||'dark');setLang(localStorage.getItem('lang')||'en');
</script></body></html>'''.replace('__SOURCE__',json.dumps(fixture,ensure_ascii=False).replace('<','\\u003c'))
(SITE/'sector_dossier_component.html').write_text(html)

def authorized_driver(**kw):
 # Keep the existing capture owner's observations/manifest schema. Only supply
 # its supported driver seam with the stricter Chromium sandbox enabled.
 manager=sync_playwright().start()
 try: browser=manager.chromium.launch(headless=kw['headless'],chromium_sandbox=True)
 except Exception: manager.stop();raise
 return owner._PlaywrightDriver(manager,browser,kw['user_agent'],dict(kw['observer_config']),kw['settle_ms'])

raise SystemExit(owner.main([
 '--registry',str(SITE/'no-production-registry.json'),
 '--site-dir',str(SITE),'--routes','/sector_dossier_component.html',
 '--viewports','desktop,mobile','--themes','dark,light','--locales','en,zh',
 '--output-dir',str(OUT),'--manifest',str(OUT/'manifest.json'),'--smells',str(OUT/'smells.json'),
 '--delay-ms','0','--settle-ms','100','--timeout-s','15',
 '--force-state','hover:hover(.sdc-action)','--force-state','focus:focus(.sdc-action)'
],driver_factory=authorized_driver))
