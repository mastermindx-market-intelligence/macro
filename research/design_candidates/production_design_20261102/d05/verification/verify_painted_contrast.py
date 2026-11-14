#!/usr/bin/env python3
"""D05-RESP-11: actual paint probe on existing source, controlled heatmap input.
No application/source writes. Transparent-ink probe preserves computed text shadow.
"""
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from PIL import Image
import base64, hashlib, io, json, math, re, time, traceback

ROOT=Path('/Volumes/Mastermind/agent-workspaces/macro/web/d05-native-source-verification-20261104/.pytest_cache/d05-composed-20261104')
OUT=ROOT/'painted-contrast-0c4493-v3'
OUT.mkdir(exist_ok=True)
SITE=ROOT/'site'
PROV=json.loads((SITE/'fixture_provenance.json').read_text())
assert PROV['runtime_ref']=='0c4493c7025f7c1c0f9e558860d5e4ba33457cd1'
for rel,want in PROV['emitted_assets'].items():
    assert hashlib.sha256((SITE/rel).read_bytes()).hexdigest()==want,rel
assert hashlib.sha1(b'blob '+str(len((SITE/'heatmap.js').read_bytes())).encode()+b'\0'+(SITE/'heatmap.js').read_bytes()).hexdigest()=='8e48256c59e351fbf1db5f9314151550d44c7541'
base='http://localhost:3100'
child='http://localhost:8765'
values=[-4,-2,-1,-0.2,0,0.2,1,2,4,None]
fixture={'label_en':'D05 CONTROLLED CONTRAST FIXTURE','label_zh':'D05 对比度固定样本',
 'source':'d05-contrast-fixture-not-live','asof':'2026-10-30','market':'us','currency':'USD',
 'size_basis':'marketcap','n_tiles':len(values),'sectors':[{'key':'Contrast','en':'Contrast fixture','zh':'对比度样本'}],
 'tiles':[{'t':'FX'+str(i),'name':'Fixture '+str(i),'sector':'Contrast','industry':'Fixture','size':100,
 'perf':{'1D':v,'1W':v,'MTD':v,'1M':v,'3M':v,'6M':v,'YTD':v,'1Y':v}} for i,v in enumerate(values)]}
fixture_text=json.dumps(fixture,separators=(',',':'))
(OUT/'heatmap_fixture.json').write_text(fixture_text+'\n')
user={'id':'e2e-user-default','email':'responsive@example.com','aud':'authenticated','app_metadata':{},'user_metadata':{}}
session={'access_token':'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJlMmUtdXNlci1kZWZhdWx0In0.fixture-only','refresh_token':'d05-fixture-only','expires_in':3600,'expires_at':int(time.time())+3600,'token_type':'bearer','user':user}
cookie='base64-'+base64.urlsafe_b64encode(json.dumps(session,separators=(',',':')).encode()).decode().rstrip('=')
result={'source_ref':PROV['runtime_ref'],'fixture_only':True,'preview_manifest_sha256':hashlib.sha256((SITE/'fixture_provenance.json').read_bytes()).hexdigest(),
 'emitted_assets_verified':len(PROV['emitted_assets']),'heatmap_fixture_sha256':hashlib.sha256(fixture_text.encode()).hexdigest(),
 'heatmap_blob':'8e48256c59e351fbf1db5f9314151550d44c7541','cases':[],
 'method':'Capture actual viewport. Preserve computed text-shadow and geometry while making only target ink transparent. Compare paired screenshots to locate painted glyph pixels. Compute intended foreground (including ancestor opacity) against the actually painted substrate at those glyph coordinates, and separately report actual raster-core contrast. Normal text requires4.5:1; genuine >=24px or >=18.6667px/700+ large text requires3:1. This is fixture text/selected-focus evidence, not full WCAG or shared acceptance.'}

def luminance(rgb):
    vals=[c/255 for c in rgb[:3]]
    vals=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in vals]
    return .2126*vals[0]+.7152*vals[1]+.0722*vals[2]
def ratio(a,b):
    x,y=sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)
def rgba(css):
    nums=[float(x) for x in re.findall(r'[\d.]+',css)]
    assert len(nums) in (3,4),css
    if css.startswith('color(srgb '):
        return [v*255 for v in nums[:3]]+([nums[3]] if len(nums)==4 else [1])
    assert css.startswith(('rgb(','rgba(')),css
    return nums[:3]+([nums[3]] if len(nums)==4 else [1])
def q(v,f):
    v=sorted(v)
    return v[min(len(v)-1,int((len(v)-1)*f))]
def save_image(page,name):
    data=page.screenshot(path=str(OUT/(name+'.png')),full_page=False,animations='disabled')
    return Image.open(io.BytesIO(data)).convert('RGB'),hashlib.sha256(data).hexdigest()

def measure(page,f,selector,name):
    framebox=page.locator('iframe[data-shared-shell-frame]').bounding_box()
    assert framebox
    targets=f.evaluate("""sel=>Array.from(document.querySelectorAll(sel)).filter(el=>{
      const r=el.getBoundingClientRect(),c=getComputedStyle(el);
      return r.width>0&&r.height>0&&c.visibility!=='hidden'&&r.right>0&&r.bottom>0&&r.left<innerWidth&&r.top<innerHeight;
    }).map((el,i)=>{
      el.dataset.d05Contrast=String(i);const c=getComputedStyle(el),r=el.getBoundingClientRect();
      let opacity=1,filters=[],clips=[{left:0,top:0,right:innerWidth,bottom:innerHeight}],p=el;
      while(p){const s=getComputedStyle(p);opacity*=Number(s.opacity);if(s.filter!=='none')filters.push(s.filter);
        if(p!==el&&/(hidden|auto|scroll|clip)/.test(s.overflow+s.overflowX+s.overflowY)){const b=p.getBoundingClientRect();clips.push({left:b.left,top:b.top,right:b.right,bottom:b.bottom});}
        p=p.parentElement;
      }
      return {i,text:el.innerText,color:c.color,fontSize:parseFloat(c.fontSize),fontWeight:c.fontWeight,textShadow:c.textShadow,opacity,filters,hovered:el.matches(':hover'),
       rect:{left:r.left,top:r.top,right:r.right,bottom:r.bottom},clips,classes:el.className,tile:el.closest('.hm-tile')?.getAttribute('data-i')||null};
    })""",selector)
    before,bhash=save_image(page,name+'-actual')
    f.evaluate("""()=>{window.__d05InkProbe=[];document.querySelectorAll('[data-d05-contrast]').forEach(el=>{
      const shadow=getComputedStyle(el).textShadow;
      window.__d05InkProbe.push([el,el.getAttribute('style')]);
      el.style.setProperty('text-shadow',shadow,'important');
      el.style.setProperty('color','transparent','important');
      el.style.setProperty('-webkit-text-fill-color','transparent','important');
      el.querySelectorAll('*').forEach(child=>{window.__d05InkProbe.push([child,child.getAttribute('style')]);const s=getComputedStyle(child).textShadow;child.style.setProperty('text-shadow',s,'important');child.style.setProperty('color','transparent','important');child.style.setProperty('-webkit-text-fill-color','transparent','important');});
    });}""")
    bg,ghash=save_image(page,name+'-substrate')
    f.evaluate("""()=>{for(const [el,style] of window.__d05InkProbe){if(style===null)el.removeAttribute('style');else el.setAttribute('style',style);}document.querySelectorAll('[data-d05-contrast]').forEach(el=>delete el.dataset.d05Contrast);delete window.__d05InkProbe;}""")
    rows=[]
    for t in targets:
        rr=t['rect'];left=max([rr['left']]+[c['left'] for c in t['clips']]);top=max([rr['top']]+[c['top'] for c in t['clips']])
        right=min([rr['right']]+[c['right'] for c in t['clips']]);bottom=min([rr['bottom']]+[c['bottom'] for c in t['clips']])
        x0=max(0,math.ceil(left+framebox['x']));x1=min(before.width,math.floor(right+framebox['x']))
        y0=max(0,math.ceil(top+framebox['y']));y1=min(before.height,math.floor(bottom+framebox['y']))
        fg=rgba(t['color']);alpha=fg[3]*t['opacity'];intended=[];painted=[];samples=[]
        for y in range(y0,y1):
            for x in range(x0,x1):
                a=before.getpixel((x,y));b=bg.getpixel((x,y))
                if max(abs(a[k]-b[k]) for k in range(3))<10:continue
                effective=[fg[k]*alpha+b[k]*(1-alpha) for k in range(3)]
                cr=ratio(effective,b);intended.append(cr);painted.append(ratio(a,b));samples.append((cr,x,y,a,b))
        row={**t,'selector':selector,'clip_main_px':[x0,y0,x1,y1],'painted_glyph_pixels':len(samples)}
        if not samples:
            row['result']='NOT_MEASURABLE_NO_VISIBLE_GLYPH'
        else:
            worst=min(samples,key=lambda v:v[0]);threshold=3 if t['fontSize']>=24 or (t['fontSize']>=18.6667 and float(t['fontWeight'])>=700) else 4.5
            row.update({'required_ratio':threshold,'minimum_intended_contrast':round(min(intended),4),'p05_intended_contrast':round(q(intended,.05),4),
              'p95_actual_raster_contrast':round(q(painted,.95),4),'maximum_actual_raster_contrast':round(max(painted),4),
              'worst_sample':{'xy':[worst[1],worst[2]],'actual_rgb':worst[3],'substrate_rgb':worst[4]},
              'result':'PASS' if min(intended)>=threshold else 'FAIL'})
        rows.append(row)
    return {'name':name,'selector':selector,'actual_png':name+'-actual.png','actual_sha256':bhash,'substrate_png':name+'-substrate.png','substrate_sha256':ghash,'rows':rows}

def focus_probe(page,f,selector,name):
    loc=f.locator(selector)
    if not loc.is_visible():return {'selector':selector,'result':'NOT_VISIBLE_AT_THIS_WIDTH'}
    loc.scroll_into_view_if_needed()
    loc.focus()
    page.keyboard.press('Shift+Tab')
    before_id=f.evaluate("document.activeElement?.outerHTML?.slice(0,250)")
    before,bhash=save_image(page,name+'-before')
    page.keyboard.press('Tab')
    active=f.evaluate("""sel=>{let el=document.activeElement,c=getComputedStyle(el),r=el.getBoundingClientRect();return {matches:el.matches(sel),focusVisible:el.matches(':focus-visible'),outlineColor:c.outlineColor,outlineWidth:c.outlineWidth,outlineOffset:c.outlineOffset,boxShadow:c.boxShadow,rect:{left:r.left,top:r.top,right:r.right,bottom:r.bottom}}}""",selector)
    after,ahash=save_image(page,name+'-focused')
    framebox=page.locator('iframe[data-shared-shell-frame]').bounding_box()
    r=active['rect'];x0=max(0,int(r['left']+framebox['x']-8));y0=max(0,int(r['top']+framebox['y']-8))
    x1=min(after.width,int(r['right']+framebox['x']+8));y1=min(after.height,int(r['bottom']+framebox['y']+8))
    changed=[]
    for y in range(y0,y1):
        for x in range(x0,x1):
            a=after.getpixel((x,y));b=before.getpixel((x,y))
            if max(abs(a[k]-b[k]) for k in range(3))>=15:changed.append((ratio(a,b),x,y,a,b))
    return {'selector':selector,'keyboard_sequence':'focus target to seed position; Shift+Tab; paired baseline; Tab back to target','preceding_element':before_id,
     'active':active,'changed_pixel_count':len(changed),'pixels_at_least_3_to_1':sum(v[0]>=3 for v in changed),
     'maximum_actual_change_contrast':round(max([v[0] for v in changed]or[1]),4),
     'result':'VISIBLE_MEASURED' if active['matches'] and active['focusVisible'] and any(v[0]>=3 for v in changed) else 'FAIL_OR_INSUFFICIENT',
     'limitation':'Selected control reachability and painted-indicator evidence only; not complete focus-area, perimeter, clipping or whole-page keyboard conformance.',
     'before_png':name+'-before.png','before_sha256':bhash,'focused_png':name+'-focused.png','focused_sha256':ahash}

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,chromium_sandbox=True)
    for width,height,theme in [(1440,1000,'dark'),(1440,1000,'light'),(390,844,'dark'),(390,844,'light')]:
        name=str(width)+'-'+theme+'-en'
        case={'case':name,'viewport':[width,height],'theme':theme,'lang':'en','errors':[],'measurements':[],'focus':[]}
        ctx=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,reduced_motion='reduce',has_touch=width<1024)
        ctx.add_init_script("""(()=>{const t="""+json.dumps(theme)+""";localStorage.setItem('theme',t);localStorage.setItem('lang','en');localStorage.setItem('mm.theme',t);localStorage.setItem('mm.lang','en');if(location.port==='8765'){window.MM_TERMINAL_BASE='https://app.mastermind-x.com/terminal';window.SUPABASE_CFG={url:'http://localhost:8765/fixture-auth',anonKey:'d05-fixture-only',ref:'d05-native-fixture'};}})();""")
        ctx.add_cookies([{'name':'sb-d05-native-fixture-auth-token','value':cookie,'url':child},{'name':'mm_e2e_rs30','value':'1','url':base}])
        def route(r):
            u=r.request.url
            if urlsplit(u).path=='/marketdata/sp500_heatmap.json':
                r.fulfill(status=200,content_type='application/json',body=fixture_text);return
            if u.startswith(child+'/fixture-auth/auth/v1/user'):
                r.fulfill(status=200,content_type='application/json',body=json.dumps(user));return
            if u.startswith((child+'/',base+'/')):r.continue_();return
            r.abort()
        ctx.route('**/*',route)
        page=ctx.new_page();page.on('pageerror',lambda e:case['errors'].append(str(e)))
        try:
            page.goto(base+'/sector_central.html?g=XLE#map',wait_until='domcontentloaded',timeout=90000)
            page.wait_for_function("document.querySelector('main[data-shared-shell-phase]')?.dataset.sharedShellPhase==='ready'",timeout=45000)
            f=page.locator('iframe[data-shared-shell-frame]').element_handle().content_frame()
            assert f
            if page.evaluate("document.documentElement.dataset.theme")!=theme:
                page.get_by_role('button',name='Light theme',exact=True).filter(visible=True).click()
            page.wait_for_function("t=>document.documentElement.dataset.theme===t",arg=theme)
            f.wait_for_function("t=>document.documentElement.dataset.theme===t",arg=theme)
            f.locator('.si-view-btn[data-view="money"]').click()
            f.wait_for_function("document.querySelectorAll('#heatmap-scorecard .hm-tile').length===10")
            f.evaluate("document.fonts.ready");page.evaluate("document.fonts.ready")
            f.locator('#heatmap-scorecard').scroll_into_view_if_needed()
            page.mouse.move(0,0)
            case['pointer_setup']='Mouse moved to parent viewport0,0, outside the measurement iframe; native hover styling is not forced.'
            case['rendered_presentation']={'parent_theme':page.evaluate('document.documentElement.dataset.theme'),'child_theme':f.evaluate('document.documentElement.dataset.theme'),'parent_lang':page.evaluate('document.documentElement.dataset.lang'),'child_lang':f.evaluate('document.documentElement.dataset.lang')}
            assert set(case['rendered_presentation'].values())=={theme,'en'}
            case['rendered_tile_count']=f.locator('#heatmap-scorecard .hm-tile').count()
            case['measurements'].append(measure(page,f,'#heatmap-scorecard .hm-tile .sym, #heatmap-scorecard .hm-tile .pc, #heatmap-scorecard .hm-sc-sechd .nm, #heatmap-scorecard .hm-sc-sechd .pc',name+'-heatmap'))
            case['focus'].append(focus_probe(page,f,'#heatmap-scorecard .hm-sc-exp',name+'-expand-focus'))
            case['focus'].append(focus_probe(page,f,'.si-view-btn[data-view="money"]',name+'-money-focus'))
            case['flow_cell_count']=f.locator('.scf-wrap table.scf td.scf-c').count()
            if case['flow_cell_count']:
                f.locator('.scf-wrap').scroll_into_view_if_needed()
                sizes=f.locator('.scf-wrap').evaluate("el=>({client:el.clientWidth,total:el.scrollWidth})")
                maximum=max(0,sizes['total']-sizes['client'])
                positions=sorted(set([0,maximum]+[min(maximum,i*sizes['client']//2) for i in range(1,math.ceil(maximum/max(1,sizes['client']/2))+1)]))
                for idx,pos in enumerate(positions):
                    f.locator('.scf-wrap').evaluate("(el,x)=>el.scrollLeft=x",pos)
                    measured=measure(page,f,'.scf-wrap table.scf td.scf-c',name+'-flow-'+str(idx))
                    measured['scroll_left']=pos
                    case['measurements'].append(measured)
            else:case['flow_scope']='NO_NATIVE_FLOW_TABLE_IN_EXISTING_PREVIEW; no manufactured flow DOM'
            assert not case['errors'],case['errors']
            rows=[r for m in case['measurements'] for r in m['rows'] if r['result'] in ('PASS','FAIL')]
            case['measured_rows']=len(rows);case['failed_rows']=len([r for r in rows if r['result']=='FAIL'])
            case['minimum_contrast']=min([r['minimum_intended_contrast'] for r in rows]or[0])
            case['result']='MEASURED_FAILURES' if case['failed_rows'] else 'MEASURED_PASS_WITHIN_SCOPE'
        except Exception as e:
            case['result']='HARNESS_OR_RUNTIME_ERROR';case['exception']=repr(e);case['traceback']=traceback.format_exc()
        finally:
            result['cases'].append(case);(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps({k:case.get(k) for k in ['case','result','rendered_tile_count','flow_cell_count','measured_rows','failed_rows','minimum_contrast','exception']},ensure_ascii=False),flush=True)
            ctx.close()
    browser.close()
print('RESULT',str(OUT/'result.json'),flush=True)
