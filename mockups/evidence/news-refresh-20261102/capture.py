import sys,json,runpy,re,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True);phase=sys.argv[3] if len(sys.argv)>3 else 'baseline'
sys.path.insert(0,str(root));tests=runpy.run_path(str(root/'tests/test_news_page_render.py'));html=tests['_render_full']();src=(root/'templates/news.html.j2').read_text();start=src.index('  (function(){',src.index('// ---- INTELLIGENCE DESK'));end=src.index('  // ---- LIVE WIRE',start);desk=src[start:end]
html=re.sub(r'<script\b[^>]*>[\s\S]*?</script>','',html,flags=re.I);html=re.sub(r'<link\b[^>]*>','',html,flags=re.I);html=html.replace('</head>','<style>'+(root/'templates/theme.css').read_text()+'</style></head>')
payload={'schema':'intelligence.desk/v1','updated_at':'2026-11-02T20:00:00Z','health':{'state':'live','active_stories':1,'confirmed':1,'sources_online':2},'stories':[{'id':'fixture-source-story','headline':'Policy statement retains its original source','headline_zh':'政策声明保留原始来源','brief':'Fixture evidence remains readable when an update fails.','brief_zh':'更新失败时，测试依据仍可阅读。','stage':'confirmed','lane':'macro','lane_label_en':'Macro','lane_label_zh':'宏观','source_count':2,'updated_at':'2026-11-02T20:00:00Z','evidence':[{'name':'Fixture official statement','url':'https://example.invalid/source','published_at':'2026-11-02T19:55:00Z'}],'tickers':['SPY']}]}
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 try:
  for width in ([1440] if phase=='baseline' else [1440,390]):
   for theme in (['dark'] if phase=='baseline' else ['dark','light']):
    for lang in (['en'] if phase=='baseline' else ['en','zh']):
     page=browser.new_page(viewport={'width':width,'height':900 if width==1440 else 844},reduced_motion='reduce');requests=[];page.route('**/*',lambda route:(requests.append(route.request.url),route.abort()))
     page.set_content(html);page.evaluate('([theme,lang])=>{document.documentElement.setAttribute("data-theme",theme);document.documentElement.setAttribute("data-lang",lang)}',[theme,lang]);page.evaluate('''payload=>{window.__deskPayload=payload;window.__pollCallback=null;window.__refreshMode='ok';window.fetch=()=>window.__refreshMode==='failure'?Promise.reject(Error('fixture transport failed')):Promise.resolve({status:200,ok:true,json:()=>Promise.resolve(window.__deskPayload)});window.setInterval=callback=>{window.__pollCallback=callback;return 1}}''',payload)
     page.add_script_tag(content=desk);page.locator('.nxi-open').first.wait_for();page.locator('#nxIntel').screenshot(path=str(out/f'{phase}-{width}-{theme}-{lang}-ready.png'));page.locator('.nxi-open').first.click();page.locator('#nxIntelDrawer').wait_for(state='visible');source_before=page.locator('#nxIntelDrawerBody').inner_text();health_before=page.locator('#nxIntelHealth').inner_text();updated_before=page.locator('#nxIntelUpdated').inner_text();page.evaluate("()=>{window.__refreshMode='failure';window.__pollCallback()}");page.wait_for_timeout(60)
     failure={'state':page.locator('#nxIntel').get_attribute('data-state'),'health':page.locator('#nxIntelHealth').inner_text(),'updated':page.locator('#nxIntelUpdated').inner_text(),'drawerRetained':page.locator('#nxIntelDrawerBody').inner_text()==source_before,'storyCount':page.locator('.nxi-open').count()};page.locator('#nxIntelClose').click();page.locator('#nxIntel').screenshot(path=str(out/f'{phase}-{width}-{theme}-{lang}-failed.png'))
     if phase!='baseline':
      assert failure['state']=='degraded',failure
      assert failure['drawerRetained'] and failure['storyCount']==1,failure
      assert failure['health']!=health_before,failure
      assert page.locator('#nxIntelCadence').inner_text()==('上次载入的排序 · 附带依据' if lang=='zh' else 'Last loaded ranking · evidence attached')
      assert page.locator('.nxi-pulse').evaluate('(n)=>getComputedStyle(n).backgroundColor')=='rgba(0, 0, 0, 0)'
      assert page.locator('#nxIntel').evaluate('(n)=>n.scrollWidth<=n.clientWidth')
      page.evaluate("()=>{document.documentElement.setAttribute('data-lang',document.documentElement.getAttribute('data-lang')==='en'?'zh':'en');document.dispatchEvent(new Event('langchange'))}");assert page.locator('#nxIntel').get_attribute('data-state')=='degraded'
      page.evaluate("lang=>{document.documentElement.setAttribute('data-lang',lang);document.dispatchEvent(new Event('langchange'));window.__refreshMode='ok';window.__deskPayload.updated_at='2026-11-02T20:10:00Z';window.__pollCallback()}",lang);page.wait_for_timeout(60);assert page.locator('#nxIntel').get_attribute('data-state')=='live';assert page.locator('#nxIntelHealth').inner_text()==health_before
      page.locator('.nxi-open').first.click();assert page.locator('#nxIntelDrawerBody').inner_text()==source_before;page.keyboard.press('Escape');assert page.locator('.nxi-open').first.evaluate('(n)=>document.activeElement===n')
     assert not requests,requests
     results.append({'width':width,'theme':theme,'lang':lang,'healthy':health_before,'sourceUpdateBefore':updated_before,'failed':failure,'externalRequests':requests});page.close()
 finally:browser.close()
report={'phase':phase,'sourceTemplateSha256':hashlib.sha256(src.encode()).hexdigest(),'kind':'CAPTURED_CURRENT_TEMPLATE_JS_ACTUAL_LOCAL_CHROMIUM_MOCKED_FEED_NO_PROVIDER','results':results};(out/f'{phase}-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
