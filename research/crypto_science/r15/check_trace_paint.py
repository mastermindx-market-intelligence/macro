"""Observe the actual SVG stroke after reveal; no path or source-data rewrite."""
from pathlib import Path
import http.server,json,socketserver,threading,sys
from playwright.sync_api import sync_playwright
HERE=Path(__file__).resolve().parent
SITE=Path('/Volumes/Mastermind/research/crypto-vector-r2-20260926-sol-001/r15_actual')

def main():
    target=HERE/('trace_paint_green.json' if '--green' in sys.argv else 'trace_paint_red.json')
    if target.exists():raise RuntimeError('Paint proof already exists; preserve it')
    rows=[]
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(SITE),**kw)
        def log_message(self,*a):pass
    with socketserver.ThreadingTCPServer(('127.0.0.1',0),Handler) as server:
        t=threading.Thread(target=server.serve_forever,daemon=True);t.start();base=f'http://127.0.0.1:{server.server_address[1]}'
        try:
            with sync_playwright() as p:
                b=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
                for width in [390,1440]:
                    page=b.new_page(viewport={'width':width,'height':1000})
                    page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base+'/') else r.abort())
                    page.goto(base+'/crypto.html',wait_until='networkidle')
                    f=page.locator('#crypto-overview .desk-tape .ilx');f.scroll_into_view_if_needed();page.wait_for_timeout(1700)
                    row=f.locator('.ilx-path').evaluate('''p=>{const n=p.getTotalLength(),m=p.getScreenCTM(),s=getComputedStyle(p);let sum=0,last=null;for(let j=0;j<=2000;j++){const q=p.getPointAtLength(n*j/2000);const x=q.matrixTransform(m);if(last)sum+=Math.hypot(x.x-last.x,x.y-last.y);last=x;}return {viewboxLength:n,screenLength:sum,dashArray:s.strokeDasharray,dashOffset:s.strokeDashoffset,vectorEffect:s.vectorEffect,endStroke:p.isPointInStroke(p.getPointAtLength(n-.5)),tailPoint:p.getPointAtLength(n-.5),scaleX:m.a,scaleY:m.d}}''')
                    row['width']=width;rows.append(row);page.close()
                b.close()
        finally:server.shutdown();t.join(timeout=2)
    target.write_text(json.dumps({'classification':'SVG_RENDERING_DIAGNOSTIC_NOT_FINANCIAL_SIGNAL','cases':rows},indent=2)+'\n')
    print(json.dumps(rows,indent=2))
    assert all(x['dashArray']=='none' and x['endStroke'] for x in rows),'The desk price line must paint through its endpoint at both widths'

if __name__=='__main__':main()
