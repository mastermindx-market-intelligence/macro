"""Capture real Chromium UI states with clearly declared SYNTHETIC price fixtures.

Uses the existing capture_page_evidence observer seam and manifest producer.
No source provider or licensed raw price is read or copied into Git.
Real retained-data browser proof stays in the private web_test_runs surface.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
from scripts.capture_page_evidence import CellObservation, run_capture, parse_force_states, canonical_json_bytes
from engine.neuralweb import market_memory_history_archive as ar
from engine.neuralweb.market_memory_history_view import export_browser
from engine.neuralweb.market_memory_history_macro import build_macro_chronology, write_macro_chronology
from tests.test_market_memory_history_macro import packet, resign


def main():
    output = Path(__file__).resolve().parent
    build = ROOT / '.test-tmp' / 'canonical-visual-filings-zh-fixture'
    if build.exists() or (output / 'p0_evidence.json').exists():
        raise SystemExit('Original capture exists; preserve and reconcile it before any recapture.')
    build.mkdir()
    symbols = 'SPY QQQ IWM RSP DIA XLB XLC XLE XLF XLI XLK XLP XLRE XLU XLV XLY TLT IEF SHY HYG LQD UUP GLD USO SLV'.split()
    def fixture_reader(_source, symbol, refs, *scope, **kwargs):
        rank = symbols.index(symbol)
        rows = []
        for i in range(730):
            day = date(2019, 1, 1) + timedelta(days=i)
            if day.weekday() >= 5: continue
            value = 100 + rank * 3 + i * .015 + 12 * math.sin(i / 17 + rank)
            rows.append({'market_date': day.isoformat(), 'close_raw': value,
                         'close_tradj': value, 'volume_raw': 1000000 + rank * 10000})
        return SimpleNamespace(rows=tuple(rows), source_partitions=tuple(tuple(x) for x in refs),
            metadata=lambda: {'source': 'SYNTHETIC_UI_FIXTURE_NOT_MARKET_DATA',
                'vendor_symbol': symbol, 'pit_backtest_eligible': False,
                'redistribution_admitted': False, 'historical_identity_admitted': False})
    request = {'schema':'market_memory.history_inputs.v1','mode':'RETROSPECTIVE_EXPLORATORY',
        'basis':'tradj','benchmark':'SPY','start':'2020-01-01','end':'2020-12-30',
        'warmup_start':'2019-01-01','capture_cutoff':'2026-10-15T00:00:00Z',
        'acknowledge_hindsight':True,'selection':'SYNTHETIC UI FIXTURE ONLY. No market observations or historical signal claims.',
        'symbols':[{'vendor_symbol':s,'refs':[['2026-10-15', hashlib.sha256(s.encode()).hexdigest()]]} for s in symbols]}
    with patch.object(ar, 'read_research_history', fixture_reader):
        receipt = ar.write_archive(ar.assemble_history(request), build / 'archive')
    macro_input = packet()
    macro_input['rows'] = [dict(macro_input['rows'][0],series=series,value=100+i,
        period='2020-12-01T00:00:00',realtime_start='2020-12-30T00:00:00',realtime_end='2021-01-31T00:00:00')
        for i,series in enumerate(['FIXTURE_CPI','FIXTURE_JOBS'])]
    chronology = build_macro_chronology(resign(macro_input), start='2020-01-01', end='2020-12-30')
    macro_receipt = write_macro_chronology(chronology, build / 'macro.json')
    from tests.test_market_memory_history_filings import payload, row
    filings = build / 'earnings_8k_dates.parquet'
    filings.write_bytes(payload([row(ticker='FIXTURE'+str(i), accession=f'0000320193-20-{i:06}',
        filing_date='2020-12-30', report_date='2020-12-28', acceptance_datetime='2020-12-30T20:00:00Z') for i in range(3)]))
    html_receipt = export_browser(build / 'archive', build / 'fixture-history.html',
        expected_manifest_sha256=receipt['manifest_sha256'], macro_path=build / 'macro.json',
        expected_macro_sha256=macro_receipt['sha256'],include_outcomes=True,
        filings_path=filings,expected_filings_sha256=hashlib.sha256(filings.read_bytes()).hexdigest())
    class Driver:
        def __init__(self, browser): self.browser = browser
        def capture(self, *, url, cell, timeout_s):
            page = self.browser.new_page(viewport={'width':cell.width,'height':cell.height},reduced_motion='reduce')
            errors=[]; remote=[]
            page.on('pageerror',lambda e: errors.append(str(e)))
            page.on('request',lambda r: remote.append(r.url) if r.url.startswith(('http:','https:')) else None)
            try:
                page.goto(url,wait_until='load',timeout=timeout_s*1000)
                expect(page.locator('#mmh-date')).to_be_enabled(timeout=30000)
                if cell.theme == 'light': page.locator('#mmh-theme').click()
                if cell.locale == 'zh': page.locator('#mmh-language').click()
                assert page.evaluate('document.documentElement.dataset.theme') == cell.theme
                assert page.evaluate('document.documentElement.dataset.lang') == cell.locale
                assert page.locator('#mmh-table tbody tr').count() == 25
                assert page.locator('#mmh-macro-table tbody tr').count() == 2
                assert page.locator('#mmh-filings-table tbody tr').count() == 3
                assert page.locator('#mmh-filings-next').is_disabled()
                assert page.locator('#mmh-outcomes').is_hidden()
                assert not errors and not remote
                applied = None
                if cell.force_state:
                    assert cell.force_state.kind == 'focus'
                    page.keyboard.press('Tab')
                    page.locator(cell.force_state.value).focus()
                    assert page.locator(cell.force_state.value).evaluate("el=>el.matches(':focus-visible')")
                    applied = cell.force_state.name
                observed=page.evaluate("({document_height_px:document.documentElement.scrollHeight,horizontal_overflow:document.documentElement.scrollWidth>innerWidth})")
                assert not observed['horizontal_overflow']
                shot=page.screenshot(full_page=True)
                return CellObservation(cell_id=cell.cell_id,loaded=True,screenshot_png=shot,
                    observed=observed,applied_theme=cell.theme,applied_locale=cell.locale,applied_force_state=applied)
            finally: page.close()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            result=run_capture(rows=[{'page_id':'market-memory-history-synthetic-fixture',
                'route':'/fixture-history.html','capture_route':'/fixture-history.html','route_kind':'explicit_fixture'}],
                driver=Driver(browser),base_url=build.as_uri(),output_dir=output / 'screenshots',
                manifest_dir=output,viewports=['desktop','mobile'],locales=['en','zh'],themes=['dark','light'],
                delay_ms=0,timeout_s=30,generated_at=datetime.now(timezone.utc).isoformat(),
                force_states=parse_force_states(['date_focus:focus(#mmh-date)']),
                target={'data':'SYNTHETIC_UI_FIXTURE_NOT_MARKET_DATA','private_provider_data_read':False,
                    'html_sha256':html_receipt['html_sha256'],'driver_ref':'mockups/evidence/market-memory-history-filings/capture_fixture.py',
                    'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                selection={'purpose':'real DOM/theme/locale/viewport/focus evidence, not real-market acceptance'})
        finally: browser.close()
    manifest=result['manifest']
    assert manifest['totals']['states_captured']==16
    (output/'p0_evidence.json').write_bytes(canonical_json_bytes(manifest))
    (output/'EVIDENCE.yml').write_text('schema: mastermind.page_evidence_receipt.v1\nchanged_paths:\n  - templates/market_memory_history.html.j2\n  - templates/market_memory_history.js\nmanifest: mockups/evidence/market-memory-history-filings/p0_evidence.json\n',encoding='utf-8')
    (output/'README.md').write_text('# Historical Market Memory visual evidence\n\nSixteen real Chromium screenshots: desktop/mobile × EN/ZH × dark/light, each at rest and actual keyboard-visible date focus. Captured by the existing canonical producer with its PageDriver observer seam.\n\nAll displayed prices, macro values and SEC-style filing records in this committed evidence are explicit synthetic fixtures. No licensed source price or raw archive was copied into Git. This is UI rendering evidence only, not historical data or production acceptance. Actual source-bound browser checks are retained separately under the private Market Time Machine web_test_runs evidence.\n',encoding='utf-8')
    print(json.dumps({'outcome':manifest['outcome'],'totals':manifest['totals'],'html_sha256':html_receipt['html_sha256'],'data':'SYNTHETIC_UI_FIXTURE_NOT_MARKET_DATA'}))

if __name__=='__main__': main()
