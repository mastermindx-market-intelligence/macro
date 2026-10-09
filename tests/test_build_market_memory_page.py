"""Static-shell and integration contracts for the Market Memory product page."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

from lib import seo
from scripts import build_market_memory_page

ROOT = Path(__file__).resolve().parent.parent


def test_market_memory_shell_renders_without_market_data() -> None:
    html = build_market_memory_page.render(ROOT)

    assert "Market Memory" in html
    assert 'id="mm-macro-episodes"' in html
    assert 'id="mm-symbol-form"' in html
    assert 'id="mm-grid-list"' in html
    assert 'src="market_memory.js"' in html
    assert "No ranking · no gating · no sizing · no Prophet training authority" in html
    assert "survivor-biased" in html
    assert "macro states are recomputed today" in html
    assert "recomputed historical episodes" in html
    assert "audited historical episodes" not in html
    assert all(line == line.rstrip() for line in html.splitlines())


def test_rendered_market_memory_artifact_keeps_temporal_disclosures() -> None:
    html = (ROOT / "site" / "market_memory.html").read_text(encoding="utf-8")

    assert "macro states are recomputed today" in html
    assert "recomputed historical episodes" in html
    assert "audited historical episodes" not in html


def test_market_memory_client_uses_only_the_owned_read_api() -> None:
    source = (ROOT / "site" / "market_memory.js").read_text(encoding="utf-8")

    assert "'/api/market-memory/v1'" in source
    assert "request('/macro?limit=6')" in source
    assert "request('/symbol/'" in source
    assert "basisPoints(query.spread_2s10s)" in source
    assert "data.historical_basis" in source
    assert "error.status === 403" in source
    assert "macroRequest: 0" in source
    assert "requestId !== state.macroRequest" in source
    assert "requestId !== state.symbolRequest" in source
    assert "function redactForSignOut()" in source
    assert "state.macroRequest += 1" in source
    assert "state.symbolRequest += 1" in source
    assert "state.macro = null" in source
    assert "state.symbol = null" in source
    assert "if (!user) {" in source
    assert "redactForSignOut();" in source
    assert 'data-mm-action="signin"' in source
    assert "window.MDXAuth.open('signin')" in source
    assert "window.MDXAuth.onChange" in source
    assert "signin.html" not in source
    assert "konseki" not in source.lower()
    assert "may_train_prophet" not in source


def test_market_memory_assets_are_template_owned_and_byte_identical() -> None:
    for name in ("market_memory.css", "market_memory.js"):
        assert (ROOT / "templates" / name).read_bytes() == (
            ROOT / "site" / name
        ).read_bytes()


def test_market_memory_is_wired_into_build_router_and_navigation() -> None:
    build_source = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    app_source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    nav_source = (ROOT / "templates" / "_navlinks.html.j2").read_text(encoding="utf-8")

    assert "build_market_memory_page" in build_source
    assert "app.market_memory" in app_source
    assert "market_memory.html" in nav_source
    assert "Put today beside comparable episodes" in nav_source
    card_start = nav_source.index('href="{{ NP }}market_memory.html"')
    card_end = nav_source.index("</a>", card_start)
    assert "nm-tier" not in nav_source[card_start:card_end]


def test_market_memory_public_shell_is_discoverable_but_payload_stays_api_owned() -> (
    None
):
    assert seo.is_public_path("/market_memory.html") is True
    names = {name for name, _url, _path in seo.discover_core_pages(ROOT / "site")}
    assert "market_memory" in names

    caddy = (ROOT / "app" / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    for matcher in ("gate_html", "gate_html_err"):
        block = caddy.split(f"@{matcher} {{", 1)[1].split("}", 1)[0]
        assert "/market_memory.html" in block


def test_market_memory_symbol_reader_uses_bounded_r2_projection() -> None:
    engine_source = (ROOT / "engine" / "neuralweb" / "market_memory.py").read_text(
        encoding="utf-8"
    )
    api_source = (ROOT / "app" / "market_memory.py").read_text(encoding="utf-8")

    assert '"site" / "stockdata"' not in engine_source
    assert "stock_record" in engine_source
    assert "_project_event_atlas" in engine_source
    assert "event_atlas.live_state(" not in engine_source
    assert "from engine import event_atlas" not in engine_source
    assert "R2_PUBLIC_BASE" in api_source
    assert "allow_redirects=False" in api_source
    assert "_MAX_STOCKDATA_BYTES" in api_source


def test_direct_builder_cli_bootstraps_repository_imports() -> None:
    source = (ROOT / "scripts" / "build_market_memory_page.py").read_text(
        encoding="utf-8"
    )

    assert "sys.path.insert(0, str(_REPO_ROOT))" in source



@pytest.mark.parametrize("relative", ["templates/market_memory.js", "site/market_memory.js"])
def test_new_symbol_intent_cannot_revive_retired_evidence(relative: str) -> None:
    """Execute the full owned client; snapshot is emitted by symbol_context from
    the existing test_market_memory._stock_record fixture, without live data.
    """
    node = shutil.which("node")
    assert node is not None, "Node is required for the Market Memory client contract"
    script = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const record = {"schema":"market_memory.symbol.v1","available":true,"ticker":"AAPL","source_schema":"event_atlas.live_state.v1","as_of":"2026-08-07","taxonomy_version":"sea.v1","align_now":1,"bull_now":{"2B":false,"3B":false,"W":true},"grids":{"W":{"date":"2026-08-01","direction":"bear","depth_class":"mid","level":"above_zero","washout_len_class":"na","align_class":1,"bars_since":2,"live_fresh":true,"bull_now":true,"receipt":{"horizons":{"13w":{"global":{"n_distinct_years":4},"name_post":{"med":4.0,"win":60.0,"med_exc":1.0,"w":0.2},"post2010":{"name_post":{"med":4.0,"win":60.0,"med_exc":1.0,"w":0.2}},"n_global":10,"n_archetype":7,"n_name":3,"era_note":null},"26w":{"global":{"n_distinct_years":4},"name_post":{"med":4.0,"win":60.0,"med_exc":1.0,"w":0.2},"post2010":{"name_post":{"med":4.0,"win":60.0,"med_exc":1.0,"w":0.2}},"n_global":10,"n_archetype":7,"n_name":3,"era_note":null}}}}},"reason":null,"historical_basis":"recomputed_history","universe_basis":"current_membership_survivor_biased_backfill","authority":{"tier":"display","horizon_role":"context","context_only":true,"proposal_weight":0,"may_rank":false,"may_gate":false,"may_size":false,"may_escalate":false,"may_trade":false,"may_originate":false,"may_select_options_candidate":false,"may_execute":false,"may_write_options_episode":false,"may_append_outcome":false,"may_train_prophet":false},"context_note":"Historical context, not a forecast or recommendation. Episodes are dependent observations and their outcomes do not establish causality."};
const ids = ['mm-macro-state', 'mm-macro-query', 'mm-macro-episodes', 'mm-macro-note', 'mm-symbol-form', 'mm-symbol-input', 'mm-symbol-summary', 'mm-grid-list'];
const elements = Object.fromEntries(ids.map(id => [id, {innerHTML:'', textContent:'', value:'', className:'', events:{}, addEventListener(type, fn){this.events[type]=fn;}}]));
const events = {};
const pending = [];
let lang = 'en';
let authChanged;
const location = new URL('https://mastermind-x.com/market_memory.html?ticker=AAPL');
const document = {readyState:'complete',documentElement:{getAttribute:()=>lang},getElementById:id=>elements[id],addEventListener(type,fn){events[type]=fn;}};
const context = {document,location,URL,localStorage:{getItem:()=>null,setItem(){}},history:{replaceState(_,__,url){location.href=new URL(url,location).href;}},fetch:url=>new Promise(resolve=>pending.push({url,resolve})),window:{MDXAuth:{onChange(fn){authChanged=fn;}}}};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
const tick = () => new Promise(resolve => setImmediate(resolve));
const summary = () => elements['mm-symbol-summary'].innerHTML;
const grids = () => elements['mm-grid-list'].innerHTML;
const submit = ticker => {elements['mm-symbol-input'].value=ticker;elements['mm-symbol-form'].events.submit({preventDefault(){}});};
const changeLanguage = () => {lang=lang==='en'?'zh':'en';events.langchange();};
const reply = (ticker, status=200) => {const item=pending.find(p=>p.url.endsWith('/symbol/'+ticker)&&!p.done);assert.ok(item, 'request '+ticker);item.done=true;item.resolve({ok:status===200,status,json:()=>Promise.resolve({...record,ticker})});};
const noEvidence = () => {assert.ok(!summary().includes('mm-symbol-ticker'),summary());assert.ok(!grids().includes('mm-grid-card'),grids());};
(async () => {
 await tick(); reply('AAPL'); await tick(); assert.ok(summary().includes('>AAPL</span>')); assert.ok(grids().includes('mm-grid-card'));
 submit('NVDA'); await tick(); const loading=summary(); const loadingGrids=grids(); changeLanguage(); noEvidence(); assert.equal(summary(),loading); assert.equal(grids(),loadingGrids); assert.equal(location.search,'?ticker=NVDA');
 reply('NVDA'); await tick(); assert.ok(summary().includes('>NVDA</span>')); assert.ok(grids().includes('mm-grid-card'));
 submit('A APL'); const invalid=summary(); changeLanguage(); noEvidence(); assert.equal(summary(),invalid); assert.equal(location.search,'?ticker=NVDA');
 submit('MSFT'); await tick(); submit('AAPL'); await tick(); reply('MSFT'); await tick(); changeLanguage(); noEvidence(); reply('AAPL'); await tick(); assert.ok(summary().includes('>AAPL</span>'));
 submit('NVDA'); await tick(); reply('NVDA',503); await tick(); const failure=summary(); changeLanguage(); noEvidence(); assert.equal(summary(),failure);
 submit('NVDA'); await tick(); reply('NVDA'); await tick(); assert.ok(summary().includes('>NVDA</span>'));
 submit('MSFT'); await tick(); submit('!'); const invalidPending=summary(); reply('MSFT'); await tick(); changeLanguage(); noEvidence(); assert.equal(summary(),invalidPending);
 submit('AAPL'); await tick(); reply('AAPL'); await tick(); submit('NVDA'); await tick(); authChanged(null); const signedOut=summary(); reply('NVDA'); await tick(); changeLanguage(); noEvidence(); assert.equal(summary(),signedOut);
 console.log('pending, invalid, latest-intent, late completion, failure, recovery, sign-out and language assertions passed');
})().catch(error => {console.error(error);process.exitCode=1;});
'''
    result = subprocess.run(
        [node, "-e", script, str(ROOT / relative)],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
