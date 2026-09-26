from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'source'; BROWSER=ROOT/'r7-browser'
sys.path.insert(0,str(SRC))
from scripts.capture_page_evidence import run_capture,CellObservation,canonical_json_bytes
out=SRC/'mockups/evidence/news-guidance-20260926';out.mkdir(parents=True,exist_ok=True)
records=json.loads((BROWSER/'rest-capture-results.json').read_text())['checks']
index={(r['state'],r['width'],r['lang'],r['theme']):r for r in records}
class RecordedRealBrowserDriver:
    def capture(self,*,url,cell,timeout_s):
        name=cell.route.rsplit('/',1)[-1].removesuffix('.html')
        record=index[(name,cell.width,cell.locale,cell.theme)]
        assert record['viewport_height']==cell.height
        assert record['applied_theme']==cell.theme and record['applied_locale']==cell.locale
        assert not record['errors'] and record['keyboard_closed'] and record['within_panel']
        return CellObservation(cell_id=cell.cell_id,loaded=True,
            screenshot_png=(BROWSER/record['rest_screenshot']).read_bytes(),
            applied_theme=record['applied_theme'],applied_locale=record['applied_locale'],
            request_count=None,payload_bytes_total=None,
            observed={'raw_slug_hit_count':None,'todo_placeholder_hit_count':None})
result=run_capture(rows=[{'page_id':'news-guidance-'+name+'-fixture','route':'/'+name+'.html','capture_route':'/'+name+'.html','route_kind':'synthetic_fixture'} for name in ['normal','correction','missing-prior','rate']],
    driver=RecordedRealBrowserDriver(),base_url='http://127.0.0.1',output_dir=out/'evidence',manifest_dir=out,
    viewports=['desktop','mobile'],locales=['en','zh'],themes=['dark','light'],delay_ms=0,timeout_s=1,
    generated_at=max(r['captured_at'] for r in records),
    target={'kind':'synthetic_ticker_news_fixture','production_acceptance':False,
      'source_parent':'f56ebe6690465813bfd342e7abeb9d3eae2054e3',
      'source_delta_sha256':{p:hashlib.sha256((SRC/p).read_bytes()).hexdigest() for p in ['lib/news_guidance_view.py','scripts/build_ticker_pages.py','templates/ticker.html.j2']},
      'browser':'existing native Chrome, fresh operation-owned profile',
      'driver':'Puppeteer real browser captures consumed through the unchanged canonical PageDriver seam',
      'driver_sha256':hashlib.sha256((BROWSER/'capture-rest.cjs').read_bytes()).hexdigest(),
      'driver_module':'capture-rest.cjs','recorded_capture_input':'browser-results.json',
      'scripts_and_iframes_removed':True,'no_live_input':True,
      'measurement_limit':'Component screenshots, keyboard/locale/geometry assertions only; broader network and page census metrics not measured.'})
manifest=result['manifest']
for page in manifest['pages']:
    page['metrics']['console_error_count']=None
(out/'manifest.json').write_bytes(canonical_json_bytes(manifest))
(out/'EVIDENCE.yml').write_text('schema: mastermind.page_evidence_receipt.v1\nchanged_paths:\n  - templates/ticker.html.j2\nmanifest: mockups/evidence/news-guidance-20260926/manifest.json\n')
(out/'browser-results.json').write_text(json.dumps({'fixture_only':True,'production_acceptance':False,'checks':records},indent=2))
shutil.copyfile(BROWSER/'capture-rest.cjs',out/'capture-rest.cjs')
shutil.copyfile(__file__,out/'emit-owner-manifest.py')
for state in ['normal','correction','missing-prior','rate']:
    # Store the exact synthetic page for honest source/screenshot reproduction.
    shutil.copyfile(BROWSER/(state+'.html'),out/(state+'.html'))
for record in records:
    # Keyboard-opened captures are additional test artifacts, not mislabeled REST cells.
    shutil.copyfile(BROWSER/record['screenshot'],out/record['screenshot'])
print('CANONICAL_EMITTER_RESULT',manifest['schema'],manifest['totals'],len(list(out.rglob('*.png'))))
