from pathlib import Path
import asyncio
import hashlib
import importlib.util
import json
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'mockups/evidence/news-shared-integration-20261020-c3'
spec = importlib.util.spec_from_file_location('news_ui_fixture', ROOT / 'scripts/verify_ticker_news_ui.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
SOURCES = ('templates/theme.css', 'templates/ticker_news.css', 'templates/ticker_news.js', 'templates/ticker_news_panel.html.j2', 'scripts/verify_ticker_news_ui.py')

def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}

async def main():
    before = hashes()
    packet = fixture.snapshot()
    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width':1440,'height':900})
        page.on('pageerror', lambda e: errors.append(str(e)))
        async def route(r):
            url = r.request.url
            if url.startswith('https://news-fixture.test/api/ticker-news/'):
                if '/stream?' in url:
                    await r.fulfill(status=200,content_type='text/event-stream',body=': heartbeat\n\n')
                elif '/stories/' in url:
                    members = [deepcopy(packet['rows'][0]), deepcopy(packet['rows'][0])]
                    members[1].update(source='massive:reuters.com',publisher='Reuters',source_item_id='wire-1',title='Reuters reports acquisition consideration of $8.2 billion',published_at='2026-10-20T09:55:00Z',received_at='2026-10-20T09:55:01Z')
                    await r.fulfill(json={'schema':'ticker_news.story.v1','story_id':'story-1','source_count':2,'item_count':2,'members':members})
                else:
                    await r.fulfill(json=packet)
            elif url.startswith('https://news-fixture.test/'):
                await r.fulfill(content_type='text/html',body=fixture.document())
            else:
                await r.abort()
        await page.route('**/*',route)
        await page.goto('https://news-fixture.test/#NVDA')
        await page.locator('.tn-row').first.wait_for()
        assert await page.locator('.tn-row').count() == 2
        await page.locator('.tn-group summary').click()
        await page.get_by_text('Reuters reports acquisition consideration of $8.2 billion',exact=True).wait_for()
        assert await page.locator('.tn-member').count() == 2
        en = await page.locator('main').inner_html()
        await page.evaluate("document.documentElement.dataset.lang='zh'; document.dispatchEvent(new Event('langchange'))")
        await page.wait_for_function("document.querySelector('.tn-comparison').textContent === '报道存在差异'")
        zh = await page.locator('main').inner_html()
        assert 'MDXAuth' not in en + zh and '<script' not in en + zh
        assert not errors, errors
        await browser.close()
    assert hashes() == before, 'fixture source changed during rendering'
    OUT.mkdir(parents=True,exist_ok=True)
    frozen = json.dumps({'en':en,'zh':zh},ensure_ascii=False).replace('<','\\u003c')
    html = '''<!doctype html><html lang="en" data-lang="en" data-theme="dark"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ticker news component — fictional visual fixture</title>
<link rel="stylesheet" href="/templates/theme.css"><link rel="stylesheet" href="/templates/ticker_news.css">
<style>*{box-sizing:border-box}body{margin:0;padding:24px;background:var(--bg);color:var(--text);font-family:var(--font-ui,system-ui,sans-serif)}main{max-width:1180px;margin:auto}.fixture{font:12px/1.6 system-ui;color:var(--muted);margin:0}.l-zh{display:none}[data-lang=zh] .l-en{display:none}[data-lang=zh] .l-zh{display:inline}@media(max-width:600px){body{padding:12px}}</style>
</head><body><main></main><script>
const fixtureDOM = ''' + frozen + ''';
let renderedLocale;
function applyFixtureLocale(){const locale=document.documentElement.dataset.lang==='zh'?'zh':'en';if(locale===renderedLocale)return;renderedLocale=locale;document.querySelector('main').innerHTML=fixtureDOM[locale];}
new MutationObserver(applyFixtureLocale).observe(document.documentElement,{attributes:true,attributeFilter:['data-lang','lang']});
applyFixtureLocale();
</script></body></html>
'''
    (OUT/'fixture.html').write_text(html)
    provenance = {'observed_at':datetime.now(timezone.utc).isoformat(),'scope':'Anonymous static component preview, frozen from the shipped consumer rendering existing fictional API fixtures in English and Chinese. No production data, authenticated deployment, provider delivery, or full stock-page claim. Capture page has no auth client, credentials, API requests, or news runtime; native hover/focus/details remain available. Separate UI and real-SSE fixture tests prove dynamic behavior.','source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_sha256':before,'fixture_sha256':hashlib.sha256(html.encode()).hexdigest(),'page_errors':errors}
    (OUT/'fixture-provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'fixture':str(OUT/'fixture.html'),'source_sha256':before,'page_errors':errors}))

asyncio.run(main())
