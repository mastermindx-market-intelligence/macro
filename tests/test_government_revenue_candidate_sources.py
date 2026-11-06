"""Behavioral regression tests for candidate source URL presentation.

The signed-in production Candidate Radar evidence drawer rendered object
references that carry only a ``ref_id`` (no URL) as page-self links, and
string identifiers such as ``govws-...`` or bare usaspending award IDs as
nonexistent relative URLs, because the permissive shared ``safeUrl`` helper
resolves anything against ``location.href`` before its https-only filter.

These tests drive the real ``templates/government-revenue-candidate-radar.js``
inside Node's ``vm`` sandbox with a verbatim copy of the production
``safeUrl`` semantics, load a receipt-verified candidate through the queue
pipeline, render the inspector hero, capture the evidence drawer through the
``data-candidate-evidence`` click handler, and assert on the emitted anchors:

* only explicit absolute HTTPS URLs supplied by a reference become clickable
  (string refs, and object ``url`` / ``source_url`` / ``href`` aliases with
  fall-through to a later valid alias);
* identifiers, relative, scheme-relative, non-HTTPS, credential-bearing,
  ``javascript:`` and ``data:`` values stay visible as plain text;
* retained receipt/event references stay visible as text in both English and
  Chinese, and issuer-path evidence is never relabeled as an event source.

Standard library only; requires the ``node`` executable.
"""

from __future__ import annotations

import html as html_module
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "government-revenue-candidate-radar.js"

LOCATION_HREF = "https://radar.example.test/government-revenue"
USASPENDING_URL = "https://www.usaspending.gov/award/ASST_TX_2026_0001"
SAM_URL = "https://www.sam.gov/contract/OPP-2026-0001"
GOVWS_ID = "govws-3f2a9c81d4b7e504"
USASPENDING_ID = "ASST_TX_2026_0001"
DATA_URI = "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg=="
RELATIVE = "documents/award-notice.pdf"
PROTOCOL_RELATIVE = "//cdn.example.test/award-notice.pdf"
PLAIN_HTTP = "http://www.example.test/award-notice.pdf"
USERINFO_HTTPS = "https://svc-key:secret@www.example.test/award-notice.pdf"
CANDIDATE_ID = "grc1-a1b2c3d4e5f601728394a5b6"

SCENARIOS = [
    dict(name="malformed_https",refs=["https:award.example.test/one"],hero_hrefs=[],drawer_hrefs=[],visible=["<p>https:award.example.test/one</p>"],forbidden=['href="']),
    dict(name="post_only_endpoint",refs=[{"ref_id":"transaction-query","url":"https://api.usaspending.gov/api/v2/transactions/"}],hero_hrefs=[],drawer_hrefs=[],visible=["<p>transaction-query</p>"],forbidden=['href="']),
    dict(name="bound_award_receipt",refs=[{"ref_id":"award-retained"}],resolved_refs=[{"ref_id":"award-retained","url":"https://api.usaspending.gov/api/v2/awards/award-exact/"}],hero_hrefs=["https://api.usaspending.gov/api/v2/awards/award-exact/"],drawer_hrefs=["https://api.usaspending.gov/api/v2/awards/award-exact/"],visible=["<p>award-retained</p>"],forbidden=["radar.example.test/award-retained"]),

    dict(
        name="missing_url_object",
        refs=[{"ref_id": "doc-9f81c2a7"}],
        hero_hrefs=[],
        drawer_hrefs=[],
        visible=["<p>doc-9f81c2a7</p>"],
        forbidden=["href=\"", "radar.example.test/doc-9f81c2a7"],
    ),
    dict(
        name="govws_id_string",
        refs=[GOVWS_ID],
        hero_hrefs=[],
        drawer_hrefs=[],
        visible=["<p>" + GOVWS_ID + "</p>"],
        forbidden=["radar.example.test/govws"],
    ),
    dict(
        name="usaspending_id_string",
        refs=[USASPENDING_ID],
        hero_hrefs=[],
        drawer_hrefs=[],
        visible=["<p>" + USASPENDING_ID + "</p>"],
        forbidden=["radar.example.test/ASST_TX_2026_0001", "usaspending.gov/award"],
    ),
    dict(
        name="relative_string",
        refs=[RELATIVE],
        hero_hrefs=[],
        drawer_hrefs=[],
        visible=["<p>" + RELATIVE + "</p>"],
        forbidden=["radar.example.test/documents"],
    ),
    dict(
        name="protocol_relative_string",
        refs=[PROTOCOL_RELATIVE],
        hero_hrefs=[],
        drawer_hrefs=[],
        visible=["<p>" + PROTOCOL_RELATIVE + "</p>"],
        forbidden=["href=\"//cdn", "https://cdn.example.test"],
    ),
    dict(
        name="javascript_scheme_string",
        refs=["javascript:alert(1)"],
        hero_hrefs=[],
        drawer_hrefs=[],
        visible=["<p>javascript:alert(1)</p>"],
        forbidden=["href=\"javascript"],
    ),
    dict(
        name="data_uri_string",
        refs=[DATA_URI],
        hero_hrefs=[],
        drawer_hrefs=[],
        visible=["<p>" + DATA_URI + "</p>"],
        forbidden=["href=\"data:"],
    ),
    dict(
        name="plain_http_string",
        refs=[PLAIN_HTTP],
        hero_hrefs=[],
        drawer_hrefs=[],
        visible=["<p>" + PLAIN_HTTP + "</p>"],
        forbidden=["href=\"http://"],
    ),
    dict(
        name="userinfo_https_string",
        refs=[USERINFO_HTTPS],
        hero_hrefs=[],
        drawer_hrefs=[],
        visible=["<p>" + USERINFO_HTTPS + "</p>"],
        forbidden=["href=\"https://svc-key"],
    ),
    dict(
        name="valid_https_string",
        refs=[USASPENDING_URL],
        hero_hrefs=[USASPENDING_URL],
        drawer_hrefs=[USASPENDING_URL],
        visible=["<p>" + USASPENDING_URL + "</p>"],
        forbidden=[],
    ),
    dict(
        name="valid_object_url",
        refs=[{"ref_id": "doc-award-1", "url": USASPENDING_URL}],
        hero_hrefs=[USASPENDING_URL],
        drawer_hrefs=[USASPENDING_URL],
        visible=["<p>doc-award-1</p>"],
        forbidden=[],
    ),
    dict(
        name="object_blank_alias_falls_through",
        refs=[{"ref_id": "doc-award-2", "url": "", "href": SAM_URL}],
        hero_hrefs=[SAM_URL],
        drawer_hrefs=[SAM_URL],
        visible=["<p>doc-award-2</p>"],
        forbidden=[],
    ),
    dict(
        name="object_invalid_alias_falls_through",
        refs=[{"ref_id": "doc-award-3", "source_url": "javascript:alert(1)", "href": SAM_URL}],
        hero_hrefs=[SAM_URL],
        drawer_hrefs=[SAM_URL],
        visible=["<p>doc-award-3</p>"],
        forbidden=["javascript:"],
    ),
    dict(
        name="mixed_invalid_and_valid_refs",
        refs=[GOVWS_ID, USASPENDING_URL, {"ref_id": "doc-award-4", "url": SAM_URL}],
        hero_hrefs=[USASPENDING_URL],
        drawer_hrefs=[USASPENDING_URL, SAM_URL],
        visible=["<p>" + GOVWS_ID + "</p>", "<p>" + USASPENDING_URL + "</p>", "<p>doc-award-4</p>"],
        forbidden=["radar.example.test/govws"],
    ),
    dict(
        name="event_ref_valid_receipt_ref_not",
        refs=[{"ref_id": "doc-award-5"}],
        event_refs=[USASPENDING_URL],
        hero_hrefs=[],
        drawer_hrefs=[USASPENDING_URL],
        visible=["<p>doc-award-5</p>", "<p>" + USASPENDING_URL + "</p>"],
        forbidden=[],
    ),
]

# Node harness: runs the template under ``vm`` with a verbatim production
# safeUrl, loads one candidate through the real queue pipeline, renders the
# hero, and captures the evidence drawer HTML for every scenario.
HARNESS_JS = r"""
'use strict';
const fs = require('fs');
const vm = require('vm');

const templatePath = process.argv[2];
const lang = process.argv[3];
const scenarios = JSON.parse(process.argv[4]);

const LOCATION_HREF = 'https://radar.example.test/government-revenue';
const location = { href: LOCATION_HREF };
/* Shared production helper, verbatim: permissive relative resolution against
 * location.href with an https-only filter. */
function safeUrl(x){try{var u=new URL(String(x||''),location.href);return u.protocol==='https:'?u.href:''}catch(e){return''}}

const sandbox = { URL: URL, console: console, location: location };
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(templatePath, 'utf8'), sandbox, { filename: 'government-revenue-candidate-radar.js' });
const createRadar = sandbox.window.createGovernmentRevenueCandidateRadar;
if (typeof createRadar !== 'function') throw new Error('createGovernmentRevenueCandidateRadar missing');

function obj(v){return !!v && typeof v === 'object' && !Array.isArray(v);}
function arr(v){return Array.isArray(v) ? v.slice() : [];}
function esc(v){return String(v == null ? '' : v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
function text(v){return String(v == null ? '' : v);}
function n(v){
  if (typeof v === 'number' && isFinite(v)) return v;
  if (typeof v === 'string' && v.trim() !== '' && !isNaN(Number(v))) return Number(v);
  return null;
}
function money(v){return '$' + v;}
function date(v){return String(v == null ? '' : v);}
function tr(en, zh){return lang === 'zh' ? zh : en;}

function fakeElement(){
  return { className: '', innerHTML: '', listeners: {},
    addEventListener: function(type, fn){ (this.listeners[type] = this.listeners[type] || []).push(fn); },
    click: function(){ (this.listeners.click || []).slice().forEach(function(fn){ fn({}); }); } };
}
const host = fakeElement();
const evidenceBtn = fakeElement();
const copyBtn = fakeElement();
host.querySelector = function(selector){
  if (selector === '[data-candidate-evidence]') return evidenceBtn;
  if (selector === '[data-candidate-copy]') return copyBtn;
  return null;
};
const drawerCalls = [];
const lastRows = { rows: [] };

let resolvedRefs = null;
const radar = createRadar({
  sourceReceipts: function(value){return resolvedRefs===null?value.source_receipt_refs:resolvedRefs;},
  obj: obj, arr: arr, esc: esc, text: text, n: n, money: money, date: date, tr: tr,
  safeUrl: safeUrl, host: function(){ return host; },
  onRows: function(rows){ lastRows.rows = rows; },
  openEvidenceDrawer: function(payload){ drawerCalls.push(payload); },
  copyLink: function(){}
});

const HEX = 'a1b2c3d4e5f601728394a5b6';
const AUTH = { tier: 'display', context_only: true, can_rank: false, can_size: false, can_gate: false, can_originate_signal: false, can_add_candidates: false, can_escalate: false };
function buildCandidate(receiptRefs, eventRefs){
  return { contract: 'government_revenue_candidate.v1', schema_version: '1.0.0',
    candidate_id: 'grc1-' + HEX, ticker: 'RTX', issuer_company_id: 'iss-0011223344',
    candidate_scope: 'government_revenue_research', is_neuralweb_trade_candidate: false,
    candidate_family: 'defense_contract_award', candidate_state: 'detected',
    transmission_direction: 'possible_positive', defense_relevant: true,
    company_name: 'Example Defense Systems', agency_name: 'Department of Defense',
    known_at: '2026-10-14T12:00:00Z', effective_at: '2026-10-13T00:00:00Z',
    event_refs: eventRefs, source_receipt_refs: receiptRefs,
    ownership_path_refs: ['ownpath-1'], artifact_content_ids: ['art-1'],
    issuer_resolution_ref: { contract: 'government_recipient_resolution.v1', graph_id: 'graph-issued-1', evidence_refs: ['ev-ref-1'] },
    authority: AUTH };
}

async function loadRow(receiptRefs, eventRefs){
  const contentId = 'grcq1-' + HEX;
  const envelope = { contract: 'government_revenue_candidate_queue.v1', schema_version: '1.0.0',
    content_id: contentId, total: 1, authority: AUTH, known_at: '2026-10-14T12:00:00Z',
    mapping_backlog_total: 0, mapping_backlog: [],
    items: [buildCandidate(receiptRefs, eventRefs)] };
  const mappingEnvelope = { contract: 'government_revenue_candidate_queue.v1', schema_version: '1.0.0',
    content_id: contentId, total: 0, authority: AUTH, items: [], next_cursor: null };
  sandbox.fetch = function(url){
    const payload = String(url).indexOf('mapping-backlog') >= 0 ? mappingEnvelope : envelope;
    return Promise.resolve({ ok: true, json: function(){ return Promise.resolve(payload); } });
  };
  const rows = await radar.load();
  if (!Array.isArray(rows) || rows.length !== 1) throw new Error('expected exactly one normalized candidate row, got ' + (rows && rows.length));
  if (lastRows.rows.length !== 1) throw new Error('onRows did not publish one row');
  return rows[0];
}

(async function(){
  const out = { location_href: LOCATION_HREF, safeurl_probe: safeUrl('govws-probe'), scenarios: {} };
  for (const spec of scenarios){
    resolvedRefs = spec.resolved_refs || null;
    drawerCalls.length = 0;
    evidenceBtn.listeners = {};
    copyBtn.listeners = {};
    lastRows.rows = [];
    host.innerHTML = '';
    const row = await loadRow(spec.refs, spec.event_refs || ['ev-receipt-1']);
    radar.render(row);
    if (!host.innerHTML) throw new Error('hero was not rendered');
    evidenceBtn.click();
    if (drawerCalls.length !== 1) throw new Error('evidence drawer was not captured');
    out.scenarios[spec.name] = { hero: host.innerHTML, drawer: drawerCalls[0].html, drawer_title: drawerCalls[0].title };
  }
  process.stdout.write(JSON.stringify(out));
})().catch(function(error){ console.error((error && error.stack) || String(error)); process.exit(1); });
"""


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node executable is unavailable; template behavior cannot be executed")
    assert TEMPLATE.is_file(), f"missing template: {TEMPLATE}"
    workdir = tmp_path_factory.mktemp("candidate-radar-harness")
    harness = workdir / "harness.js"
    harness.write_text(HARNESS_JS, encoding="utf-8")
    out = {}
    for lang in ("en", "zh"):
        proc = subprocess.run(
            [node, str(harness), str(TEMPLATE), lang, json.dumps(SCENARIOS)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0, f"harness failed for lang={lang}: {proc.stderr.strip()}"
        out[lang] = json.loads(proc.stdout)
    return out


def _anchors(markup):
    return len(re.findall(r"<a\b", markup or ""))


def _hrefs(markup):
    return [html_module.unescape(match) for match in re.findall(r'href="([^"]*)"', markup or "")]


def test_shared_safeurl_semantics_are_permissive(rendered):
    """The harness uses the production safeUrl, which resolves identifiers
    against the page URL. This pins the exact bug environment."""
    assert rendered["en"]["location_href"] == LOCATION_HREF
    assert rendered["en"]["safeurl_probe"] == "https://radar.example.test/govws-probe"


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario["name"])
def test_candidate_source_links(rendered, scenario):
    for lang in ("en", "zh"):
        zh = lang == "zh"
        data = rendered[lang]["scenarios"][scenario["name"]]
        hero, drawer = data["hero"], data["drawer"]

        # The drawer is captured through the real evidence button handler.
        assert data["drawer_title"] == ("候选证据" if zh else "Candidate evidence")

        # Retained receipt/event references stay visible as text.
        for snippet in scenario["visible"]:
            assert snippet in drawer, f"{scenario['name']}[{lang}]: reference text missing"
        retained = "保留引用" if zh else "Retained reference"
        assert drawer.count(retained) == len(scenario["refs"]) + len(scenario.get("event_refs", ["ev-receipt-1"]))

        # Issuer-path evidence is present as evidence text, not relabeled.
        assert ("发行人路径" if zh else "Issuer path") in drawer
        assert "candidate_id: " + CANDIDATE_ID in drawer

        # Nothing forbidden ever lands in the markup.
        blob = hero + drawer
        for bad in scenario["forbidden"]:
            assert bad not in blob, f"{scenario['name']}[{lang}]: found forbidden {bad!r}"

        # Anchor counts and exact hrefs.
        assert _anchors(hero) == len(scenario["hero_hrefs"]), f"{scenario['name']}[{lang}]: hero anchors"
        assert _anchors(drawer) == len(scenario["drawer_hrefs"]), f"{scenario['name']}[{lang}]: drawer anchors"
        assert _hrefs(hero) == scenario["hero_hrefs"], f"{scenario['name']}[{lang}]: hero hrefs"
        assert _hrefs(drawer) == scenario["drawer_hrefs"], f"{scenario['name']}[{lang}]: drawer hrefs"

        open_source = "打开来源" if zh else "Open source"
        if scenario["hero_hrefs"]:
            assert 'target="_blank"' in hero and 'rel="noopener"' in hero
            assert (open_source + " ↗") in hero
        else:
            assert open_source not in hero, f"{scenario['name']}[{lang}]: hero link copy without a valid URL"
        if scenario["drawer_hrefs"]:
            assert 'target="_blank"' in drawer and 'rel="noopener"' in drawer
            assert open_source in drawer
        else:
            assert open_source not in drawer, f"{scenario['name']}[{lang}]: drawer link copy without a valid URL"

        # Hero stays intact regardless of link availability.
        assert "RTX · Example Defense Systems" in hero
        assert ("查看证据" if zh else "View evidence") in hero


def test_drawer_keeps_non_source_evidence(rendered):
    drawer = rendered["en"]["scenarios"]["missing_url_object"]["drawer"]
    assert "Research boundary" in drawer
    assert "This is a research candidate, not a buy signal or trade instruction." in drawer
    assert "issuer_resolution_ref: graph-issued-1" in drawer
    assert "ownership_path_refs: ownpath-1" in drawer


def test_invalid_alias_never_becomes_href(rendered):
    for lang in ("en", "zh"):
        data = rendered[lang]["scenarios"]["object_invalid_alias_falls_through"]
        assert _hrefs(data["drawer"]) == [SAM_URL]
        assert "javascript:" not in data["hero"] + data["drawer"]
