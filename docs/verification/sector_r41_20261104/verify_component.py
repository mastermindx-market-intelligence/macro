#!/usr/bin/env python3
"""Real Chromium component proof; labelled synthetic data, no network/user writes."""
from __future__ import annotations
import argparse, hashlib, json, runpy, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
JS=ROOT/'templates/sector_dossier_cycle.js';CSS=ROOT/'templates/sector_dossier_cycle.css'
prelude=runpy.run_path(str(ROOT/'tests/test_sector_dossier_cycle_js.py'))['PRELUDE']
fixture=json.loads(subprocess.check_output(['node','-e',prelude+';console.log(JSON.stringify(fixture()));',str(JS)],text=True))
fixture['sectors'][0]['osc']=[{'x':2024+i/12,'v':v} for i,v in enumerate([25,37,62,74,61,35,18,31,55,77,68,44,27,36,53,61,49,35,46,68,86,91,79,65,70,85,87,74])]
chart=subprocess.check_output(['git','-C',str(ROOT),'show','4a2291747fd2d8d364a3838e1ed2263636bc64a6:site/mm_charts.js'],text=True)
options={'accessState':'allowed','dataState':'ready','family':'sectors','id':'xle','locale':'en','expectedAsOf':'2026-10-30'}
HOST=r'''(input)=>{
 window.source=input.source;window.options=input.options;window.calls=[];window.chartDestroyed=0;
 window.addHost=(extra={})=>Object.assign({},window.options,extra,{
  onMembers:s=>calls.push({action:'members',...s}),onOpenCycles:s=>calls.push({action:'cycles',...s}),onSources:s=>calls.push({action:'sources',...s}),
  renderChart:(root,context)=>{const points=context.record.osc;
   const chart=MMChart.create(root,{xDomain:[2024,2026.3],yDomain:[0,100],
    yTicks:[{v:0,label:'0'},{v:50,label:'50'},{v:100,label:'100'}],animate:false,crosshair:true,zoom:true,
    padding:{t:16,r:16,b:32,l:42},series:[{id:context.record.id,label:context.record.ticker,color:'var(--link)',
     hist:points.map(p=>({x:p.x,y:p.v})),proj:[],markers:[]}]});
   window.testChart=chart;
   return ()=>{chart.destroy();window.chartDestroyed+=1;};}
 });window.component=SectorDossierCycle.mount(document.querySelector('#subject'),source,addHost());}'''
results=[]
try:
 with sync_playwright() as tool:
  browser=tool.chromium.launch(headless=True,chromium_sandbox=True)
  try:
   for width in [1440,768,390,320]:
    for theme in ['dark','light']:
     for locale in ['en','zh']:
      page=browser.new_page(viewport={'width':width,'height':1000},reduced_motion='reduce');errors=[]
      page.on('pageerror',lambda err:errors.append(str(err)));page.route('**/*',lambda route:route.abort())
      page.set_content('<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:var(--bg);color:var(--text)"><main style="padding:24px;max-width:1440px;margin:0 auto"><p style="font:12px sans-serif">R4.1 COMPONENT · SYNTHETIC FIXTURE · NOT LIVE</p><div id="subject"></div></main></body></html>')
      page.evaluate('([theme,locale])=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=locale;}',[theme,locale])
      page.add_style_tag(content=(ROOT/'templates/theme.css').read_text());page.add_style_tag(content=CSS.read_text())
      page.add_script_tag(content=chart);page.add_script_tag(content=JS.read_text())
      page.evaluate(HOST,{'source':fixture,'options':dict(options,locale=locale)})
      page.locator('.sdc-chart svg').wait_for();page.wait_for_timeout(50)
      metrics=page.evaluate('''()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,
       duplicates:[...document.querySelectorAll('[id]')].map(n=>n.id).filter((v,i,a)=>a.indexOf(v)!==i),
       buttons:[...document.querySelectorAll('.sdc-action')].map(n=>n.getBoundingClientRect().height),
       chartCount:document.querySelectorAll('.sdc-chart svg').length,state:document.querySelector('.sdc').dataset.state})''')
      contrast=page.evaluate('''()=>{const rgb=s=>(s.match(/[0-9.]+/g)||[]).slice(0,3).map(Number);
       const lum=a=>a.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
       return [...document.querySelectorAll('.sdc-title,.sdc-label,.sdc-muted,.sdc-value,.sdc-action:not(:disabled)')].filter(e=>e.textContent).map(e=>{
        const st=getComputedStyle(e);let p=e,bg='rgba(0, 0, 0, 0)';while(p&&bg==='rgba(0, 0, 0, 0)'){bg=getComputedStyle(p).backgroundColor;p=p.parentElement;}
        const a=lum(rgb(st.color)),b=lum(rgb(bg));return {text:e.textContent.slice(0,50),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),required:parseFloat(st.fontSize)>=24?3:4.5};});}''')
      assert all(c['ratio']>=c['required'] for c in contrast),(width,theme,locale,[c for c in contrast if c['ratio']<c['required']])
      metrics['minTextContrast']=min(c['ratio'] for c in contrast)
      assert not metrics['overflow'],(width,theme,locale,metrics)
      assert not metrics['duplicates'],metrics
      labels=page.evaluate('''()=>[...document.querySelectorAll('.sdc-chart .mmc-axis text')].filter(n=>getComputedStyle(n).visibility!=='hidden').map(n=>{const b=n.getBoundingClientRect();return {text:n.textContent,left:b.left,right:b.right};})''')
      assert len(labels)>=2,labels
      assert all(b['left']-a['right']>=3.5 for a,b in zip(labels,labels[1:])),('overlapping_date_labels',width,theme,locale,labels)
      assert min(metrics['buttons'])>=44 and metrics['chartCount']==1 and metrics['state']=='ready',metrics
      assert page.locator('.sdc-values > summary').count()==1,'Exact values must be implemented, not a decorative label'
      page.keyboard.press('Tab');assert page.evaluate('document.activeElement.parentElement.classList.contains("sdc-values")')
      page.keyboard.press('Enter');assert page.locator('.sdc-values').get_attribute('open') is not None
      assert page.locator('.sdc-values tbody tr').count()==28
      assert page.locator('.sdc-values tbody tr').first.inner_text()=='2024\t25'
      page.keyboard.press('Enter');assert page.locator('.sdc-values').get_attribute('open') is None
      page.keyboard.press('Tab');assert page.evaluate('document.activeElement.classList.contains("sdc-action")')
      page.keyboard.press('Enter');assert page.evaluate('calls[0].action')=='members'
      assert page.evaluate('calls[0].id')=='xle' and page.evaluate('calls[0].asOf')=='2026-10-30'
      name=f'{width}-{theme}-{locale}';page.screenshot(path=str(args.out/(name+'.png')),full_page=True)
      # Native zoom redraws the axis; collision handling must survive that redraw
      # without changing the chart's observations, domain behavior or zoom support.
      page.evaluate('testChart.setView([2024.2,2025.3],false)');page.wait_for_timeout(80)
      zoom_labels=page.evaluate('''()=>[...document.querySelectorAll('.sdc-chart .mmc-axis text')].filter(n=>getComputedStyle(n).visibility!=='hidden').map(n=>{const b=n.getBoundingClientRect();return {left:b.left,right:b.right};})''')
      assert len(zoom_labels)>=2 and all(b['left']-a['right']>=3.5 for a,b in zip(zoom_labels,zoom_labels[1:])),zoom_labels
      assert page.evaluate('testChart.spec.series[0].hist.length')==28
      assert page.evaluate('testChart.spec.zoom') is True
      page.evaluate('component.update(source,addHost())');assert page.evaluate('chartDestroyed')==1
      page.locator('.sdc-action').first.click();assert page.evaluate('calls.length')==2
      page.evaluate('''()=>{const hostile=structuredClone(source);hostile.sectors[0].name='<img src=x onerror="window.injected=true">';
       hostile.sectors[0].name_zh=hostile.sectors[0].name;component.update(hostile,addHost());}''')
      assert page.locator('#subject img').count()==0 and page.evaluate('window.injected===undefined')
      assert '<img' in page.locator('.sdc-title').inner_text()
      page.evaluate('''()=>{window.oldButton=document.querySelector('.sdc-action');const denied=new Proxy({}, {get(){throw Error('sensitive read');}});
       component.update(denied,addHost({accessState:'forbidden'}));oldButton.click();}''')
      assert page.locator('.sdc').get_attribute('data-state')=='denied' and page.locator('.sdc-chart svg').count()==0
      assert '+6.1%' not in page.locator('#subject').inner_text() and page.evaluate('calls.length')==2
      for state in ['loading','unavailable','stale']:
       page.evaluate('(state)=>component.update(source,addHost({dataState:state}))',state)
       assert page.locator('.sdc').get_attribute('data-state')==state
      page.evaluate('component.update(source,addHost({expectedAsOf:"2026-10-29"}))')
      assert page.locator('.sdc').get_attribute('data-state')=='incompatible_generation' and '+6.1%' not in page.locator('#subject').inner_text()
      # Invalid attached history must be distinguished from absent history; valid facts survive.
      page.evaluate('''()=>{const invalid=structuredClone(source);invalid.sectors[0].osc[1].v=null;component.update(invalid,addHost());}''')
      assert page.locator('.sdc-history').get_attribute('data-state')=='invalid'
      assert page.locator('.sdc-chart svg').count()==0 and page.locator('.sdc-values').count()==0
      assert '+6.1%' in page.locator('#subject').inner_text()
      assert page.locator('.sdc-chart').inner_text() != ('尚未附上历史序列' if locale=='zh' else 'History not attached')
      # Exact-value pagination remains bounded and source order survives navigation.
      page.evaluate('''()=>{const many=structuredClone(source);many.sectors[0].osc=Array.from({length:122},(_,i)=>({x:2000+i/12,v:i%101}));
       component.update(many,Object.assign(addHost(),{onSources:undefined}));}''')
      page.locator('.sdc-values > summary').click();assert page.locator('.sdc-values tbody tr').count()==50
      page.locator('.sdc-page').last.click();assert page.locator('.sdc-values tbody tr').count()==50
      page.locator('.sdc-page').last.click();assert page.locator('.sdc-values tbody tr').count()==22
      assert page.locator('.sdc-page').last.is_disabled()
      page.locator('.sdc-page').first.click();assert page.locator('.sdc-values tbody tr').count()==50
      page.locator('.sdc-action').last.click();assert page.locator('.sdc-sources').get_attribute('open') is not None
      assert page.evaluate('document.activeElement.parentElement.classList.contains("sdc-sources")')
      assert page.locator('.sdc-source-list dd').count()==7
      assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
      page.evaluate('component.update(source,addHost({accessState:"forbidden"}))')
      assert page.locator('.sdc-values').count()==0 and page.locator('.sdc-sources').count()==0
      page.evaluate('component.destroy();component.update(source,addHost())');assert page.locator('#subject').inner_html()==''
      assert errors==[],errors
      results.append({'width':width,'theme':theme,'locale':locale,'status':'passed','checks':metrics});page.close()
   version=browser.version
  finally:browser.close()
 report={'status':'passed','browser':version,'fixture':'synthetic, not production','cases':results,
  'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [JS,CSS]}}
 (args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':'passed','cases':len(results),'out':str(args.out)}))
except Exception as exc:
 (args.out/'result.json').write_text(json.dumps({'status':'failed','completed':results,'error':str(exc)},indent=2)+'\n');raise
