"""Admin shell UX guardrails for navigation and progressive disclosure.

These source-level tests keep the admin console usable as its page count grows. They
intentionally test the shipped static shell rather than backend behavior.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "admin" / "static" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "admin" / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "admin" / "static" / "styles.css").read_text(encoding="utf-8")


def test_admin_navigation_has_search_and_keyboard_access():
    assert 'id="navSearch"' in APP
    assert 'placeholder="Find an admin page…"' in APP
    assert 'data-nav-group' in APP
    assert 'data-nav-label=' in APP
    # Native buttons provide Enter/Space activation without emulating controls on divs.
    assert '<button type="button" class="nav-item"' in APP
    assert 'el.setAttribute("aria-current", "page")' in APP
    assert 'No matching pages' in APP


def test_mobile_navigation_is_a_drawer_not_a_horizontal_page_strip():
    assert 'id="sidebarToggle"' in INDEX
    assert 'aria-controls="sidebar"' in INDEX
    assert 'id="sidebarScrim"' in INDEX
    assert '.sidebar.open' in CSS
    assert 'transform:translateX(-102%)' in CSS
    assert '.sidebar-scrim.show' in CSS
    assert 'body.nav-open' in CSS
    assert 'if (e.key === "Escape") setSidebarOpen(false)' in APP
    assert 'if (window.matchMedia("(max-width: 900px)").matches) setSidebarOpen(false)' in APP


def test_overview_keeps_primary_copy_concise_and_diagnostics_progressive():
    assert 'Key alerts — check in with Fable' not in APP
    assert 'Brief for Fable' not in APP
    assert '<div class="section">Needs attention</div>' in APP
    assert 'title="Copy the full alert context">Copy brief</button>' in APP
    assert 'class="tech-details"' in APP
    assert 'Program-watch data was not returned. This is not an all-clear.' in APP
    assert 'Deploy actions are unavailable.' in APP


def test_research_tools_do_not_repeat_internal_proprietary_disclaimers_on_every_card():
    assert '<div class="rt-kicker">Research workspace</div>' in APP
    assert '<p>Diagnostics, calibration, and internal research methods.</p>' in APP
    assert 'Internal diagnostics for model votes and neural-system output.' not in APP
    assert 'Proprietary cross-market, liquidity, and risk diagnostics.' not in APP
    assert 'Admin-only research workspace.' in APP


def test_experiments_table_hides_secondary_details_until_needed():
    assert 'Long-running tests and data collections, with the next review date and action.' in APP
    assert '<summary>Source</summary>' in APP
    assert '<details class="row-actions">' in APP
    assert '<summary class="btn">Actions</summary>' in APP
    assert '>Mark acted</button>' in APP
    assert '>Snooze</button>' in APP
    assert '>Dismiss</button>' in APP
    assert '>Override</button>' in APP
    assert '.row-actions-menu' in CSS


def test_site_access_keeps_provider_details_out_of_primary_copy():
    assert 'Country detection not configured' in APP
    assert '<summary>Technical details</summary>' in APP
    assert 'Country source is resolved by <code>/api/gate/check</code>' in APP
    assert '<div class="section">Blocked IPs ' in APP
    assert '<div class="section">Always allowed ' in APP
    assert '<div class="section">Blocked countries ' in APP
    assert 'Names via browser Intl.DisplayNames' not in APP
    assert 'Off = fail-open.' not in APP


def _node_assert(code: str) -> None:
    """Execute the shipped helper bodies, rather than a reimplemented model."""
    import shutil
    import subprocess
    import pytest
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the admin browser-helper contract")
    prelude = """
const assert = require('node:assert/strict');
const APP = require('node:fs').readFileSync(0, 'utf8');
function block(start, end) {
  const a = APP.indexOf(start); const b = APP.indexOf(end, a);
  assert(a >= 0 && b > a, `Missing source boundary: ${start}`);
  return APP.slice(a, b);
}
"""
    result = subprocess.run(
        [node, "-e", prelude + "\n(async () => {\n" + code + "\n})().catch(e => { console.error(e); process.exitCode = 1; });"],
        input=APP, text=True, capture_output=True, timeout=20, cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_workspace_keeps_every_route_once_but_only_13_primary_pages():
    _node_assert("""
const groups = new Function(block('const NAV_GROUPS = [', 'const TAB_LABELS = ') + '; return NAV_GROUPS;')();
const ids = groups.flatMap(group => group.items.map(item => item[0]));
const expected = 'overview health system deploy analytics users support_tickets email_center revenue marketing_floor marketing_outbox marketing_content marketing_publish neural_web intelligence_os orchestrator prophet macro_thesis mastermind_ai mastermind_logs alerts long_hold context_lobe causal_lab chronicle research_tools experiments marketing_sentinel marketing_lanes marketing_radar marketing_reply_queue marketing_seo marketing_models marketing_health marketing_learning marketing_lab marketing_lobes marketing_overview marketing_departments marketing_campaigns marketing_channels personas marketing_allies marketing_ads marketing_experiments control_room metabolism codex cost content site_gate features brief vector'.split(' ');
assert.equal(ids.length, 54);
assert.equal(new Set(ids).size, 54);
assert.deepEqual([...ids].sort(), expected.sort());
assert.equal(groups.filter(group => group.primary).flatMap(group => group.items).length, 13);
""")


def test_overview_distinguishes_unknown_and_failed_checks():
    _node_assert("""
const model = new Function(block('function adminOverviewModel(', 'function adminOverviewMetric(') + '; return adminOverviewModel;')();
assert.equal(model({}).healthKnown, false);
assert.equal(model({health: {healthy: true, age_hours: null}}).healthKnown, false);
assert.equal(model({health: {healthy: true, age_hours: 1}}).healthKnown, true);
const failed = model({health: {healthy: true, age_hours: 1}, services: {available: true, healthy: false}});
assert.equal(failed.notices.length, 1);
assert.equal(failed.notices[0].page, 'system');
assert.equal(failed.notices[0].tone, 'bad');
assert.equal(model({health: {healthy: false, age_hours: 1}}).notices[0].page, 'health');
""")


def test_overview_demotes_research_without_removing_it_and_does_not_dispatch():
    overview = APP.split('RENDER.overview = async () => {', 1)[1].split('/* ---- RESEARCH TOOLS', 1)[0]
    assert overview.index('<details class="admin-secondary">') < overview.index('${renderKeyAlerts(')
    assert '${renderProgramWatch(s.program_watch)}' in overview
    assert 'wireKeyAlertCopies(s.key_alerts)' in overview
    assert 'wireProgramWatch(s.program_watch)' in overview
    assert 'dispatch(' not in overview
    assert 'tracking enabled' not in overview
    assert '>Live<' not in overview
    assert 'estimate, not billed spend' in overview
    assert 'this is not a complete system health check' in overview


def test_page_render_failure_is_recoverable_and_late_errors_do_not_replace_new_pages():
    _node_assert("""
const failures = [];
const run = new Function('adminPageFailure', 'route', 'let ADMIN_RENDER_EPOCH = 0;' + block('function runAdminRender(', 'function go(') + '; return runAdminRender;')((id) => failures.push(id), () => {});
await run('broken', () => { throw new Error('read unavailable'); });
assert.deepEqual(failures, ['broken']);
failures.length = 0;
let rejectOld;
const old = run('old', () => new Promise((resolve, reject) => { rejectOld = reject; }));
await Promise.resolve();
await run('current', () => {});
rejectOld(new Error('old request failed'));
await old;
assert.deepEqual(failures, []);
""")


def test_reads_have_a_body_deadline_but_writes_are_not_retried_or_aborted():
    _node_assert("""
const helper = block('const ADMIN_READ_TIMEOUT_MS = ', 'async function api(');
const timers = []; const cleared = []; const calls = [];
const make = (fetcher, parser) => new Function('fetch', 'readJson', 'AbortController', 'setTimeout', 'clearTimeout', helper + ';return readAdminResponse;')(
  fetcher, parser, AbortController,
  (fn, delay) => { timers.push({fn, delay}); return timers.length; },
  id => cleared.push(id)
);
const read = make(async (path, opts) => { calls.push({path, opts}); return {body: {ok:true}}; }, async response => response.body);
assert.deepEqual((await read('/read')).value, {ok:true});
assert.equal(timers[0].delay, 30000);
assert(calls[0].opts.signal instanceof AbortSignal);
assert.deepEqual(cleared, [1]);
await read('/write', {method:'POST', body:'{}'});
assert.equal(timers.length, 1);
assert.equal(calls.length, 2);
assert.equal(calls[1].opts.signal, undefined);
let signal; let bodyStarted;
const started = new Promise(resolve => { bodyStarted = resolve; });
const hung = make(async (path, opts) => { signal = opts.signal; return {}; }, () => new Promise((resolve, reject) => {
  signal.addEventListener('abort', () => reject(new Error('aborted')), {once:true}); bodyStarted();
}));
const pending = hung('/hung-body'); await started;
timers.at(-1).fn();
await assert.rejects(pending, /too long to respond/);
assert.equal(cleared.length, 2);
""")


def test_startup_cannot_treat_a_failed_session_probe_as_authenticated():
    init = APP.split('(async function init() {', 1)[1]
    assert 'SESSION = await api("/api/session")' in init
    assert 'typeof SESSION.auth_enabled !== "boolean"' in init
    assert 'typeof SESSION.authenticated !== "boolean"' in init
    assert 'Unable to verify your session.' in init
    assert 'catch(() => ({ auth_enabled: false, authenticated: true }))' not in init
    assert 'SUMMARY = next; // keep the last good snapshot' in APP


def test_content_review_intersects_filters_before_twelve_card_pagination():
    _node_assert("""
const review = new Function('const CS_REVIEW_PAGE_SIZE = 12;' + block('function csReviewPage(', 'function csRefreshPlan(') + '; return csReviewPage;')();
const entries = Array.from({length: 48}, (_, i) => ({acctId: i % 2 ? 'beta' : 'alpha', post:{id:i, type:i % 3 ? 'chart' : 'signal', headline:'Draft ' + i, ticker: i === 44 ? 'AMD' : 'XYZ'}}));
const original = JSON.stringify(entries);
assert.equal(review(entries).rows.length, 12);
assert.equal(review(entries, {page: 2}).rows[0].post.id, 12);
assert.equal(review(entries, {page: 999}).page, 4);
assert.equal(review(entries, {page: -1}).page, 1);
assert.equal(review(entries, {}, 500).rows.length, 12);
let selection = {type:'signal', account:'beta'};
assert.deepEqual(review(entries, selection).rows.map(x => x.post.id), [3,9,15,21,27,33,39,45]);
assert.deepEqual(review(entries, {account:'beta', type:'signal'}), review(entries, selection));
assert.equal(review(entries, {query:'amd'}).rows[0].post.id, 44);
assert.equal(review(entries, {query:'  DrAfT 44 ', account:'alpha', type:'chart'}).total, 1);
assert.equal(review(entries, {query:'AMD', account:'beta'}).total, 0);
const empty = review(entries, {query:'does not exist', page:9});
assert.deepEqual([empty.from,empty.to,empty.page,empty.pages,empty.total], [0,0,1,1,0]);
assert.equal(JSON.stringify(entries), original);
assert.equal(review([null, {}, {post:null}]).total, 0);
""")


def test_content_review_uses_light_reads_and_never_inlines_chart_documents():
    renderer = APP.split('RENDER.marketing_content = async () => {', 1)[1].split('/* Is the content plan stale?', 1)[0]
    assert '"/api/marketing/content?charts=metadata"' in APP
    assert 'csWireReview(allPosts, postCardHtml, d.content_revision, renderEpoch)' in renderer
    assert 'allPosts.map(postCardHtml)' not in renderer
    assert '${featured.svg}' not in renderer
    assert 'data-cs-preview' in renderer
    assert 'renderEpoch !== ADMIN_RENDER_EPOCH' in renderer
    assert 'Nothing on this page has been sent.' not in renderer
    preview = APP.split('async function csLoadPreview(', 1)[1].split('function csWireReview(', 1)[0]
    assert 'document.createElement("img")' in preview
    assert '.innerHTML' not in preview
    assert 'response.content_revision !== revision' in preview
    assert 'details.isConnected' in preview
    assert 'plan_changed' in preview
    assert 'Retry preview' in preview
    assert 'Refresh plan' in preview


def test_unrecorded_drop_reasons_are_not_reported_as_passed_drafts():
    _node_assert("""
const drop = new Function(block('function csDropPanel(', '/* Scroll helper for the funnel cells') + '; return csDropPanel;')();
for (const data of [{}, {funnel:null}, {funnel:{drop_reasons:{}}}]) {
  const html = drop(data);
  assert(html.includes('No drop reasons were recorded'));
  assert(html.includes('does not prove every draft passed'));
  assert(!html.includes('Every planned post got words'));
}
""")


def test_content_queue_distinguishes_local_delivery_refusal_and_unknown_effect():
    _node_assert("""
const classify = new Function(block('const CS_INTEL_REFUSAL_LABEL = ', 'async function csQueueIntel(') + '; return csIntelQueueOutcome;')();
assert.equal(classify({ok:true,item_id:'item-1',account:'alpha',delivered:true}), 'queued');
assert.equal(classify({ok:true,item_id:'item-1',account:'alpha',delivered:false}), 'local_only');
assert.equal(classify({ok:true,item_id:'item-1',account:'alpha'}), 'local_only');
assert.equal(classify({ok:false,reason:'story_locked'}), 'refused');
for (const result of [null, {}, {ok:true}, {ok:false,error:'server failed'}, {ok:false,reason:'error'}, {ok:false,reason:'__proto__'}]) {
  assert.equal(classify(result), 'unknown');
}
""")


def test_content_queue_lost_ack_never_claims_no_effect_or_reissues_write():
    _node_assert("""
const source = block('const CS_INTEL_REFUSAL_LABEL = ', '/* Filters update one shared selection');
async function exercise(response, throws = false) {
  const calls = [], links = [], messages = [];
  const out = {style:{}, textContent:'', append(...nodes) { links.push(...nodes.filter(node => node && node.type === 'button')); }};
  const card = {querySelector: () => out, getAttribute: key => key === 'data-story-id' ? 'story-a' : 'draft-a'};
  const button = {disabled:false, textContent:'Queue for X', closest: () => card};
  const doc = {createElement: () => ({}), createTextNode: text => text};
  const queue = new Function('post','toast','document','go',source + '; return csQueueIntel;')(
    async (path, body) => { calls.push({path,body}); if (throws) throw new Error('lost acknowledgement'); return response; },
    message => messages.push(message), doc, page => messages.push(page)
  );
  await queue(button);
  const label = button.textContent, detail = out.textContent;
  await queue(button);
  return {calls, links, label, detail, button, messages};
}
const lost = await exercise(null, true);
assert.equal(lost.calls.length, 1);
assert.equal(lost.label, 'Status unknown');
assert(lost.detail.includes('may have completed'));
assert(!lost.detail.includes('nothing was queued'));
assert.equal(lost.links.length, 1);
assert.equal(lost.button.disabled, true);
assert.deepEqual(lost.calls[0].body, {story_id:'story-a',draft_id:'draft-a'});
const local = await exercise({ok:true,item_id:'item-1',account:'alpha',delivered:false});
assert.equal(local.calls.length, 1);
assert.equal(local.label, 'Delivery unconfirmed');
assert(local.detail.includes('not confirmed'));
const confirmed = await exercise({ok:true,item_id:'item-1',account:'alpha',delivered:true});
assert.equal(confirmed.calls.length, 1);
assert.equal(confirmed.label, 'Queued');
const refused = await exercise({ok:false,reason:'story_locked',detail:'already owned'});
assert.equal(refused.label, 'Queue for X');
assert.equal(refused.button.disabled, false);
assert(refused.detail.includes('Refused by'));
""")


def test_publisher_receipt_labels_preserve_delivery_uncertainty():
    """A legacy posted record is not independently verified delivery evidence."""
    start = APP.index('RENDER.marketing_publish = async () => {')
    end = APP.index('/* Dark-desk park readout', start)
    renderer = APP[start:end]
    assert '["posted", "Publisher records", "var(--muted)"]' in renderer
    assert 'Recent publisher records' in renderer
    assert 'not delivery confirmation or permission to resend' in renderer
    assert '["posted", "Posted",' not in renderer
    assert 'What goes out next, what is stuck, and what already went.' not in renderer
    assert 'Live posts land here with their Buffer receipt' not in renderer
    assert 'Engagement is polled after the post lands' not in renderer
    assert 'Submission receipts and confirmed delivery remain separate.' in renderer
    # Preserve the existing ledger fields, receipt navigation, and measurement nulls.
    assert 'const posted = d.recent_posted || [];' in renderer
    assert 'posted: ["#pub-posted",' in renderer
    assert 'r.external_url' in renderer and 'r.external_id' in renderer
    assert 'v2 == null ?' in renderer and 'not measured yet' in renderer
    assert 'recorded ${a.posted || 0}' in renderer
    assert 'pubWireGoLive(d);' in renderer
    assert 'onclick="pubRunDryRun(this)"' in renderer


def test_site_inventory_searches_all_rows_before_bounded_pagination():
    _node_assert("""
const select = new Function(block('function adminInventoryPage(', 'RENDER.content = ') + '; return adminInventoryPage;')();
const pages = Array.from({length:12622}, (_, i) => ({name: `page-${i}.html`, kb:i, age_hours:i}));
const original = JSON.stringify(pages);
assert.equal(select(pages).rows.length, 50);
assert.deepEqual(select(pages).rows, pages.slice(0,50));
assert.equal(select(pages, '', 2).rows[0].name, 'page-50.html');
assert.equal(select(pages, '  PAGE-12621  ').rows[0].name, 'page-12621.html');
assert.equal(select(pages, 'not-a-page').total, 0);
assert.equal(select(pages, '', Infinity).page, 1);
assert.equal(select(pages, '', -1).page, 1);
assert.equal(select(pages, '', 99999).page, 253);
assert.equal(select(pages, '', 253).rows.length, 22);
const seen = []; for (let n=1; n<=253; n++) seen.push(...select(pages,'',n).rows.map(p=>p.name));
assert.equal(seen.length,12622); assert.equal(new Set(seen).size,12622);
assert.equal(JSON.stringify(pages), original);
const empty = select([], '', 7);
assert.deepEqual([empty.page,empty.pages,empty.from,empty.to,empty.total],[1,1,0,0,0]);
""")


def test_site_inventory_late_initial_read_cannot_replace_a_new_page():
    _node_assert("""
const vm = require('node:vm');
let finish; const view = {innerHTML:'new page', isConnected:true};
const sandbox = {RENDER:{}, CURRENT:'content', ADMIN_RENDER_EPOCH:1, $:()=>view,
  api:()=>new Promise(resolve=>{finish=resolve;}), card:()=>'', esc:String, fmtAge:String};
vm.createContext(sandbox);
vm.runInContext(block('function adminInventoryPage(', '/* ---- NEURAL WEB (W8a)'),sandbox);
const pending = sandbox.RENDER.content();
sandbox.CURRENT='overview'; sandbox.ADMIN_RENDER_EPOCH=2;
finish({pages:[],total_pages:0}); await pending;
assert.equal(view.innerHTML,'new page');
""")


def test_site_inventory_has_named_controls_and_read_error_recovery():
    content = APP.split('RENDER.content = async () => {', 1)[1].split('/* ---- NEURAL WEB (W8a)', 1)[0]
    assert 'id="inventorySearch" type="search"' in content
    assert 'label for="inventorySearch"' in content
    assert 'aria-live="polite"' in content
    assert 'adminInventoryPage(d.pages, search.value, page)' in content
    assert 'page = 1; draw();' in content
    assert 'Link check unavailable. Try again.' in content
    assert 'Live-site check unavailable. Try again.' in content
    assert '$("#view").appendChild' not in content
    assert 'post(' not in content and 'dispatch(' not in content
