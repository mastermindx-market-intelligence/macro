"""Exercise the real widget locally; fixture auth/quotas never reach a server."""
import hashlib
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/{OUT.relative_to(ROOT)}/fixture.html'
results = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height in ((1440, 900), (390, 844)):
            for theme in ('dark', 'light'):
                for language in ('en', 'zh'):
                    context = browser.new_context(viewport={'width': width, 'height': height})
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(url, wait_until='load')
                    page.wait_for_function('window.__fixtureReady === true')
                    page.evaluate('([theme,lang]) => {document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang;}', [theme, language])
                    page.wait_for_timeout(550)
                    placeholder = page.locator('#mmb-ta').get_attribute('placeholder')
                    assert placeholder.startswith('Ask a research question' if language == 'en' else '\u63d0\u51fa\u4e00\u4e2a\u7814\u7a76\u95ee\u9898'), placeholder
                    assert page.locator('.mmb-rrow,.mmb-rpill,.mmb-rcost').count() == 0
                    assert page.locator('#mmb-lane [data-lane="pro"]').get_attribute('aria-pressed') == 'true'
                    assert '150' in page.locator('#mmb-q').inner_text()
                    geometry = page.evaluate('''() => {
                      const ta=document.querySelector('#mmb-ta').getBoundingClientRect();
                      const tools=document.querySelector('.mmb-tools').getBoundingClientRect();
                      const box=document.querySelector('.mmb-box').getBoundingClientRect();
                      return {gap:tools.top-ta.bottom,left:box.left,right:box.right,width:innerWidth};
                    }''')
                    assert -1 <= geometry['gap'] <= 4, geometry
                    assert geometry['left'] >= -1 and geometry['right'] <= width + 1, geometry
                    page.locator('#mmb-ta').fill('Local fixture research question')
                    page.locator('#mmb-send').click()
                    page.wait_for_function('window.__requests.length === 1')
                    request = page.evaluate('window.__requests[0]')
                    assert request['mode'] == 'research' and request['lane'] == 'pro', request
                    page.wait_for_function('!document.querySelector("#mmb-send").classList.contains("stop")')
                    page.locator('#mmb-lane [data-lane="fast"]').click()
                    page.locator('#mmb-ta').fill('Local fixture ordinary question')
                    page.locator('#mmb-send').click()
                    page.wait_for_function('window.__requests.length === 2')
                    ordinary = page.evaluate('window.__requests[1]')
                    assert ordinary['mode'] == 'chat' and ordinary['lane'] == 'fast', ordinary
                    page.locator('#mmb-lane [data-lane="pro"]').click()
                    assert page.evaluate('JSON.parse(localStorage.getItem("mm.brain.prefs")).lane') == 'pro'
                    page.reload(wait_until='load')
                    page.wait_for_function('window.__fixtureReady === true')
                    assert page.locator('#mmb-lane [data-lane="pro"]').get_attribute('aria-pressed') == 'true'
                    page.evaluate("window.__fixtureTier='free';MMBrain.close();MMBrain.open();")
                    page.wait_for_function('document.querySelector("#mmb-lane [data-lane=fast]").getAttribute("aria-pressed") === "true"')
                    page.locator('#mmb-ta').fill('/')
                    page.locator('.mmb-slash-i[data-i="1"]').click()
                    assert page.locator('#mmb-lane [data-lane="pro"]').get_attribute('aria-pressed') == 'false'
                    assert page.evaluate('window.__requests.length') == 0
                    assert not errors, errors
                    results.append({'width':width,'theme':theme,'language':language,'composer_gap_px':geometry['gap'],'checks':'pass','page_errors':errors})
                    context.close()
        browser.close()
finally:
    server.shutdown()
report = {'scope':'local real-widget browser test; synthetic auth and quotas; no production request', 'asset_sha256':hashlib.sha256((ROOT/'templates/mm_brain.js').read_bytes()).hexdigest(),'results':results}
(OUT/'behavior.json').write_text(json.dumps(report, indent=2)+'\n')
print(f'PASS: {len(results)} browser states; research/fast routing, Pro preferences, entitlement refusal, no banner/gap/runtime errors.')
