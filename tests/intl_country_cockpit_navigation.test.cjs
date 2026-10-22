'use strict';

/*
 * Country cockpit + Tools / retained-research navigation, in a real browser.
 *
 * ---------------------------------------------------------------------------
 * THIS IS A MODELLED PARENT, NOT THE TERMINAL APP SHELL.
 * The parent below is a small in-test stand-in served from one of the bridge's
 * own allowed local parent origins. It really hosts the child in a cross-origin
 * iframe, really speaks mmx.shared-shell.v1 (INIT / READY / NAVIGATE /
 * LOCATION_ACCEPTED), really owns acceptance and the outgoing history, and runs
 * the UNMODIFIED templates/shared_shell_bridge.js and
 * templates/intl_country_cockpit.js from disk. What it is not: the production
 * Terminal AppShell. Assertions about parent chrome, the parent's own view
 * controls and cross-frame occlusion are therefore out of scope here and stay
 * with the root's actual-parent acceptance run. The fixture history channel uses
 * wrapped child navigation; it does not implement fresh frames or INIT.restore
 * saved-view restoration. Those require the actual-parent driver.
 *
 * Run: node --test tests/intl_country_cockpit_navigation.test.cjs
 * The parent origin must be one the bridge itself allows
 * (LOCAL_PARENTS in templates/shared_shell_bridge.js).
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const { chromium } = require('playwright');

const BRIDGE = fs.readFileSync(path.join(__dirname, '..', 'templates', 'shared_shell_bridge.js'), 'utf8');
const CONTROLLER = fs.readFileSync(path.join(__dirname, '..', 'templates', 'intl_country_cockpit.js'), 'utf8');

const PARENT_ORIGIN = 'http://127.0.0.1:3100';   // in the bridge's LOCAL_PARENTS
const CHILD_ORIGIN = 'http://127.0.0.1:3105';
const PROTOCOL = 'mmx.shared-shell.v1';
const GENERATION = 'g1';
const LIBRARY = '?view=library&market=&pins=&horizon=1m&basis=usd_unhedged&return_basis=price&group=';
const UNICODE_ID = 'ünï-目标';

let browser;

test.before(async () => {
  browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL });
});

test.after(async () => {
  if (browser) await browser.close();
});

function filler(id, rows) {
  let out = `<div class="filler" id="${id}">`;
  for (let i = 0; i < rows; i++) out += `<p>row ${i}</p>`;
  return out + '</div>';
}

/* The legacy page the country controller enhances. Structure mirrors the real
 * one as described by the actual-parent evidence: the country section and the
 * Tools disclosure are SIBLINGS, and a nested research target sits inside
 * #intl-analysis-tools > #intl-legacy-research > anonymous details.ref-fold.
 * Every anchor
 * a test clicks is outside those disclosures so it stays reachable once they
 * have been opened and closed again. */
function childHtml() {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="mmx-shell-document" content="20261018.1">
<meta name="mmx-shell-response" content="content">
<title>International country cockpit</title>
<style>
  :root { --mmx-shared-shell-css-ready: 1; }
  body { margin: 0; font: 13px/1.4 system-ui, sans-serif; }
  .imc-toolbar { position: sticky; top: 0; z-index: 10; background: #fff;
                 border-bottom: 2px solid #333; padding: 6px; }
  .imc-country-rail a { margin-right: 8px; }
  .filler p { height: 120px; margin: 0; }
  details > summary { padding: 6px; background: #eee; }
</style>
<script>${BRIDGE}</script>
</head><body>
<main id="page">
  <div data-im-country-analysis id="cockpit">
    <div class="imc-toolbar-anchor">
      <div class="imc-toolbar" id="imc-toolbar">
        <nav class="imc-country-rail">
          <a id="rail-jp" href="#imc-country-JP" data-imc-country>Japan</a>
          <a id="rail-kr" href="#imc-country-KR" data-imc-country>Korea</a>
        </nav>
      </div>
      <div class="imc-assistant-slot" id="imc-assistant-slot"></div>
    </div>
    <details class="imc-country" id="imc-country-JP" open>
      <summary id="jp-summary">Japan</summary>
      <a id="root-tools-link" href="#intl-analysis-tools">Analysis tools</a>
      <a id="root-nested-link" href="#intl-legacy-research">Legacy research</a>
      <a id="root-deep-link" href="#deep-target">Deep research note</a>
      <a id="root-path-link" href="/intl.html#intl-analysis-tools">Tools as an explicit path</a>
      <p id="jp-body">Japan body</p>
    </details>
    <details class="imc-country" id="imc-country-KR"><summary id="kr-summary">Korea</summary><p id="kr-body">Korea body</p></details>
    <details class="imc-country" id="imc-country-TW"><summary id="tw-summary">Taiwan</summary><p id="tw-body">Taiwan body</p></details>
  </div>
  <nav id="siblings">
    <a id="sibling-tools-link" href="#intl-analysis-tools">Tools, sibling section</a>
    <a id="sibling-deep-link" href="#deep-target">Deep note, sibling section</a>
    <a id="unicode-link" href="#${UNICODE_ID}">Unicode note</a>
    <a id="missing-link" href="#missing-target">Missing</a>
    <a id="malformed-link" href="#%ZZ">Malformed</a>
    <a id="outside-link" href="#outside-target">Outside the tools</a>
    <a id="foreign-link" href="https://evil.example/intl.html#intl-analysis-tools">Foreign</a>
    <a id="otherpath-link" href="/other.html#intl-analysis-tools">Other path</a>
    <a id="otherquery-link" href="/intl.html?view=chart#intl-analysis-tools">Other query</a>
    <a id="credential-link" href="http://user:secret@127.0.0.1:3105/intl.html#intl-analysis-tools">Credentials</a>
    <a id="blank-link" target="_blank" href="#intl-analysis-tools">New tab</a>
    <a id="download-link" download href="#intl-analysis-tools">Download</a>
    <a id="rolebutton-link" role="button" href="#intl-analysis-tools">Acts as a button</a>
  </nav>
  <details id="intl-analysis-tools">
    <summary id="tools-summary">International analysis tools</summary>
    ${filler('tools-filler', 26)}
    <details id="intl-legacy-research">
      <summary id="legacy-summary">Legacy research</summary>
      <details class="ref-fold">
        <summary id="ref-summary">Reference</summary>
        <p id="deep-target">Deep target</p>
        <p id="${UNICODE_ID}">Unicode target</p>
      </details>
    </details>
  </details>
  ${filler('tail-filler', 34)}
  <h1 id="outside-heading">Outside</h1>
  <p id="outside-target">Outside target</p>
</main>
<script>
// The incumbent workspace's own view control: a wrapped same-document history
// call, exactly as the real page switches view. The bridge and its parent own
// what that means.
document.addEventListener('click', function (event) {
  const button = event.target.closest('button[data-im-action="set_view"]');
  if (!button) return;
  const url = new URL(location.href);
  url.search = button.getAttribute('data-im-view') === 'library'
    ? '${LIBRARY.slice(1)}'
    : 'view=country&market=&pins=&horizon=1m&basis=usd_unhedged&return_basis=price&group=';
  url.hash = '';
  history.pushState(history.state, '', url.pathname + url.search);
});
// MODELING BOUNDARY: the modeled parent is cross-origin, so it cannot reach into
// this frame the way the real shared runtime does. The modeled parent therefore
// hands the restoration back over its own fixture-level channel, and the page
// performs it with the same wrapped history call its own view control uses - the
// bridge and the controller under test see an ordinary controlled navigation.
window.addEventListener('message', function (event) {
  var data = event.data;
  if (event.origin !== '${PARENT_ORIGIN}') return;
  if (!data || data.type !== 'restore-location') return;
  history.replaceState(history.state, '', data.href);
  window.scrollTo(0, data.y || 0);
});
</script>
<script>${CONTROLLER}</script>
</body></html>`;
}

/* The modelled Terminal AppShell. */
function parentHtml() {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Shell</title></head>
<body>
<h1 id="parent-title">Modeled shell</h1>
<iframe id="child" src="${CHILD_ORIGIN}/intl.html?mmx_shell=1&mmx_generation=${GENERATION}"
        width="640" height="480" style="border:0"></iframe>
<script>
(function () {
  var frame = document.getElementById('child');
  var win = frame.contentWindow;
  var log = { ready: 0, nav: 0, ack: 0, errors: [], navs: [], locations: 0 };
  var stack = [];
  window.__shell = log;
  function post(data) { win.postMessage(data, '${CHILD_ORIGIN}'); }
  window.addEventListener('message', function (event) {
    var d = event.data;
    if (!d || d.protocol !== '${PROTOCOL}' || d.frameGeneration !== '${GENERATION}') return;
    if (d.type === 'READY') { log.ready += 1; log.readyPayload = d; return; }
    if (d.type === 'ERROR') { log.errors.push(d.code); return; }
    if (d.type === 'NAVIGATE') {
      log.nav += 1;
      log.navs.push({ href: d.href, mode: d.mode, sameDocument: d.sameDocument, requestId: d.requestId });
      // The parent owns URL acceptance.
      log.ack += 1;
      post({ protocol: '${PROTOCOL}', frameGeneration: '${GENERATION}', type: 'LOCATION_ACCEPTED',
             requestId: d.requestId, canonicalPath: d.href });
    }
  });
  frame.addEventListener('load', function () {
    post({ protocol: '${PROTOCOL}', frameGeneration: '${GENERATION}', type: 'INIT', theme: 'dark', locale: 'en',
           contextRevision: 1, canonicalPath: '/intl.html',
           catalog: { legacyPaths: ['/intl.html'], nativePaths: ['/pricing'] }, restore: null });
  });
  // Outgoing view/history ownership, with a reader position per entry.
  window.__pushEntry = function (href, y) {
    stack.push({ href: href, y: y || 0 });
    history.pushState({ idx: stack.length - 1 }, '');
  };
  window.addEventListener('popstate', function (event) {
    var entry = stack[(event.state && event.state.idx) || 0];
    if (!entry) return;
    log.restored = entry;
    post({ type: 'restore-location', href: entry.href, y: entry.y });
  });
}());
</script>
</body></html>`;
}

async function createShell(options = {}) {
  const o = Object.assign({ query: '', hash: '', parent: true }, options);
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(4000);
  // Synthetic clicks in this suite reach the real listeners with real modifier
  // flags but must not then perform their native default action (new tabs,
  // downloads, top-level navigations): what is under test is the guard, not the
  // browser's popup behaviour. Trusted clicks are never touched, so ordinary
  // activation, the real country view switch and the real new-tab case below
  // still behave natively. Registered on the window BUBBLE phase so it runs
  // after the bridge's own document-phase handler.
  await page.addInitScript(() => {
    window.addEventListener('click', (event) => { if (!event.isTrusted) event.preventDefault(); }, false);
  });
  // Matched by URL shape, not by a glob: the child is always requested with its
  // mmx_shell/mmx_generation query.
  const isPath = (origin) => (url) => url.origin === origin && new URL(url).pathname === '/intl.html';
  await context.route(isPath(CHILD_ORIGIN), route => route.fulfill({
    contentType: 'text/html; charset=utf-8', body: childHtml(),
  }));
  if (o.parent) {
    await context.route(isPath(PARENT_ORIGIN), route => route.fulfill({
      contentType: 'text/html; charset=utf-8', body: parentHtml(),
    }));
    await page.goto(`${PARENT_ORIGIN}/intl.html`);
    await page.waitForFunction(() => window.__shell && window.__shell.ready >= 1);
  } else {
    const target = new URL(`${CHILD_ORIGIN}/intl.html${o.query}`);
    target.hash = o.hash;
    await page.goto(target.href);
  }
  const frame = o.parent ? page.frames().find(f => f.url().startsWith(CHILD_ORIGIN)) : page.mainFrame();
  assert.ok(frame, 'the child frame must be reachable');
  return { context, page, frame };
}

const shellLog = (page) => page.evaluate(() => window.__shell);
const isOpen = (frame, id) => frame.evaluate((x) => document.getElementById(x).open, id);
const locationHref = (frame) => frame.evaluate(() => location.href);
const scrollY = (frame) => frame.evaluate(() => window.pageYOffset);

/* Arrival is proved the way the root proof does it: the element must sit inside
 * the child scrollport, clear of the sticky toolbar, and elementFromPoint at its
 * own leading edge must not land on that toolbar. */
const ARRIVAL = (id) => {
  const el = document.getElementById(id);
  if (!el) return false;
  // Content inside a CLOSED disclosure keeps a layout box in this engine, so a
  // rectangle alone would call an unrevealed destination "visible". Only painted
  // content counts as an arrival.
  if (typeof el.checkVisibility === 'function' &&
      !el.checkVisibility({ checkVisibilityCSS: true, contentVisibilityAuto: true,
                            opacityProperty: true, visibilityProperty: true })) return false;
  const box = el.getBoundingClientRect();
  const toolbar = document.getElementById('imc-toolbar');
  const tb = toolbar.getBoundingClientRect();
  const x = Math.min(Math.max(box.left + 6, 1), window.innerWidth - 1);
  const y = Math.min(Math.max(box.top + 3, 1), window.innerHeight - 1);
  const hit = document.elementFromPoint(x, y);
  return box.bottom > 0 && box.top < window.innerHeight && box.top >= tb.bottom - 1 &&
    !!hit && hit !== toolbar && !toolbar.contains(hit);
};
async function awaitArrival(frame, id) {
  await frame.waitForFunction(ARRIVAL, id, { timeout: 3000 });
}
async function assertNoArrival(frame, id) {
  assert.equal(await frame.evaluate(ARRIVAL, id), false, `${id} must not be a visible arrival`);
}
async function openState(frame) {
  return frame.evaluate(() => ({
    refFold: document.querySelector('details.ref-fold').open,
    tools: document.getElementById('intl-analysis-tools').open,
    legacy: document.getElementById('intl-legacy-research').open,
    jp: document.getElementById('imc-country-JP').open,
  }));
}
/* Bridge messages and the accepted-location notification are delivered as tasks,
 * so a counter or a disclosure state read straight after an activation can still
 * be looking at the previous turn. Two nested timer turns in the parent let every
 * queued message land before anything is read. */
async function settle(page) {
  await page.evaluate(() => new Promise((resolve) => setTimeout(() => setTimeout(resolve, 0), 0)));
}
async function settleFrame(frame) {
  await frame.evaluate(() => new Promise(resolve =>
    requestAnimationFrame(() => requestAnimationFrame(resolve))));
}
async function navigationCounts(page, frame, hasParent = true) {
  const child = await frame.evaluate(() => ({ href: location.href, history: history.length }));
  if (!hasParent) return { child };
  const parent = await page.evaluate(() => ({
    nav: window.__shell.nav, ack: window.__shell.ack, history: history.length,
    errors: window.__shell.errors.slice(),
  }));
  return { child, parent };
}
async function waitNav(page, count) {
  await page.waitForFunction((n) => window.__shell && window.__shell.nav >= n, count);
  await settle(page);
}
// The modeled parent's own view control: real wrapped history, real acceptance.
async function switchToLibrary(frame) {
  await frame.evaluate(() => {
    const b = document.createElement('button');
    b.setAttribute('data-im-action', 'set_view');
    b.setAttribute('data-im-view', 'library');
    b.id = 'set-library';
    document.body.appendChild(b);
    b.click();
    b.remove();
  });
}

test('E first and repeated Tools activation from the root and from the sibling section', async () => {
  const { context, page, frame } = await createShell();
  try {
    assert.deepEqual(await openState(frame), { refFold: false, tools: false, legacy: false, jp: true });
    assert.equal(await frame.evaluate(() => document.getElementById('root-tools-link').getAttribute('href')),
      `${PARENT_ORIGIN}/intl.html#intl-analysis-tools`, 'the anchor really is projected');

    await frame.click('#root-tools-link');
    await waitNav(page, 1);
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), true);
    await awaitArrival(frame, 'tools-summary');

    // A repeat is the same canonical fragment: it must not fabricate a second one.
    await frame.click('#root-tools-link');
    await awaitArrival(frame, 'tools-summary');
    assert.equal((await shellLog(page)).nav, 1, 'only the first activation may reach the parent');

    // Manually closed, then activated again from the sibling section.
    await frame.evaluate(() => { document.getElementById('intl-analysis-tools').open = false; });
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), false);
    await frame.click('#sibling-tools-link');
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), true);
    await awaitArrival(frame, 'tools-summary');
    await settle(page);
    assert.equal((await shellLog(page)).nav, 1, 'a reopened disclosure is still the same canonical fragment');
  } finally { await context.close(); }
});

test('E Tools still activates after the parent changes the current query', async () => {
  const { context, page, frame } = await createShell();
  try {
    await switchToLibrary(frame);
    await waitNav(page, 1);
    assert.ok((await locationHref(frame)).includes('view=library'));
    assert.equal((await shellLog(page)).nav, 1);
    // Anti-vacuity: the projection still displays the query-less parent href.
    assert.equal(await frame.evaluate(() => document.getElementById('root-tools-link').getAttribute('href')),
      `${PARENT_ORIGIN}/intl.html#intl-analysis-tools`);

    await frame.click('#root-tools-link');
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), true, 'the query change must not strand Tools');
    await awaitArrival(frame, 'tools-summary');
    await waitNav(page, 2);
    const log = await shellLog(page);
    assert.equal(log.nav, 2);
    assert.equal(log.navs[1].sameDocument, true, 'the authored fragment is still this document');

    await frame.evaluate(() => { document.getElementById('intl-analysis-tools').open = false; });
    await frame.click('#root-tools-link');
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), true, 'the repeat after the query change reopens');
    await awaitArrival(frame, 'tools-summary');
    await settle(page);
    assert.equal((await shellLog(page)).nav, 2, 'no new navigation for the repeated fragment');

    // The explicitly path-authored link is a different destination, and must not
    // be treated as a local fragment arrival.
    await frame.evaluate(() => { document.getElementById('intl-analysis-tools').open = false; });
    await frame.click('#root-path-link');
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), false,
      'an authored /intl.html#id is not this document after the view change');
    await frame.click('#root-tools-link');
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), true);
  } finally { await context.close(); }
});

test('E the same nested destination repeats after Library with every ancestor manually closed', async () => {
  const { context, page, frame } = await createShell();
  try {
    await switchToLibrary(frame);
    await waitNav(page, 1);
    await frame.click('#root-deep-link');
    await waitNav(page, 2);
    await awaitArrival(frame, 'deep-target');
    assert.deepEqual(await openState(frame), { refFold: true, tools: true, legacy: true, jp: true });
    assert.equal(await frame.evaluate(() => location.hash), '#deep-target');
    const first = await navigationCounts(page, frame);
    assert.equal(first.parent.nav, 2);
    assert.equal(first.parent.ack, 2);

    await frame.evaluate(() => {
      document.querySelector('details.ref-fold').open = false;
      document.getElementById('intl-legacy-research').open = false;
      document.getElementById('intl-analysis-tools').open = false;
    });
    await settleFrame(frame);
    assert.deepEqual(await openState(frame), { refFold: false, tools: false, legacy: false, jp: true });
    await frame.click('#sibling-deep-link');
    await awaitArrival(frame, 'deep-target');
    await settle(page);
    assert.deepEqual(await openState(frame), { refFold: true, tools: true, legacy: true, jp: true });
    assert.deepEqual(await navigationCounts(page, frame), first,
      'the same fragment reopens every ancestor without a new NAVIGATE, ACK, URL or history entry');
  } finally { await context.close(); }
});

test('E the nested destination is not left below the fold or under the sticky toolbar', async () => {
  const { context, frame } = await createShell();
  try {
    await frame.click('#sibling-deep-link');
    await awaitArrival(frame, 'deep-target');
    const box = await frame.evaluate(() => {
      const el = document.getElementById('deep-target');
      const b = el.getBoundingClientRect();
      const t = document.getElementById('imc-toolbar').getBoundingClientRect();
      return { top: b.top, bottom: b.bottom, toolbarBottom: t.bottom, viewport: window.innerHeight, y: window.pageYOffset };
    });
    assert.ok(box.top >= box.toolbarBottom - 1, `destination ${box.top} must clear the toolbar ${box.toolbarBottom}`);
    assert.ok(box.top > 0, 'the destination was below the visible viewport');
    assert.ok(box.y > 0, 'the disclosure really had to reflow for this to arrive');
    assert.ok(box.bottom <= box.viewport, 'the destination is inside the child scrollport');

    // The huge Tools wrapper itself arrives at its summary, not at its own top.
    await frame.evaluate(() => {
      document.getElementById('intl-legacy-research').open = false;
      document.getElementById('intl-analysis-tools').open = false;
    });
    await frame.click('#sibling-tools-link');
    await awaitArrival(frame, 'tools-summary');
    await assertNoArrival(frame, 'deep-target');
  } finally { await context.close(); }
});

test('E unicode, malformed, missing and unrelated ids are handled without guessing', async () => {
  const { context, frame } = await createShell();
  try {
    await frame.click('#unicode-link');
    assert.deepEqual(await openState(frame), { refFold: true, tools: true, legacy: true, jp: true });
    await awaitArrival(frame, UNICODE_ID);
    await frame.evaluate(() => {
      document.querySelector('details.ref-fold').open = false;
      document.getElementById('intl-analysis-tools').open = false;
      document.getElementById('intl-legacy-research').open = false;
    });

    for (const id of ['#missing-link', '#malformed-link', '#outside-link']) {
      await frame.click(id);
      assert.deepEqual(await openState(frame),
        { refFold: false, tools: false, legacy: false, jp: true }, `${id} must not open Tools`);
      // A collapsed summary still renders, so probe a target that only exists inside
      // the collapsed research chain: nothing may have been brought into view.
      await assertNoArrival(frame, 'deep-target');
    }
  } finally { await context.close(); }
});

test('F modified, non-primary, native-target and lookalike activations preserve the current page', async () => {
  const { context, page, frame } = await createShell();
  try {
    const before = await locationHref(frame);
    const navBefore = (await shellLog(page)).nav;

    // A REAL modified click: whether the browser then opens a tab is its own
    // business, but this page must not move and the parent must hear nothing.
    const popups = [];
    const onPopup = (p) => { popups.push(p); p.close().catch(() => {}); };
    context.on('page', onPopup);
    await frame.click('#root-tools-link', { modifiers: ['Control'] });
    await settle(page);
    context.off('page', onPopup);
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), false);
    assert.equal(await locationHref(frame), before);

    // The remaining modified and non-primary activations: same guard, dispatched so
    // the browser's own tab/download handling cannot disturb the assertions.
    for (const modifiers of [{ altKey: true }, { metaKey: true }, { shiftKey: true }, { button: 1 }, { button: 2 }]) {
      await frame.dispatchEvent('#root-tools-link', 'click',
        Object.assign({ button: 0, ctrlKey: false, metaKey: false, shiftKey: false, altKey: false }, modifiers));
      assert.equal(await isOpen(frame, 'intl-analysis-tools'), false,
        `${JSON.stringify(modifiers)} must keep native semantics`);
      assert.equal(await locationHref(frame), before, `${JSON.stringify(modifiers)} must not move this page`);
    }

    // Dispatched clicks carry the same listener path without opening new tabs or
    // starting downloads, which is what a real _blank/download activation would.
    // Each keeps its native outcome: a genuine same-origin destination with another
    // query is still a real navigation, and a rejected one is still an explicit
    // refusal - none of them may reveal local Tools.
    for (const [id, why] of [['#blank-link', '_blank'], ['#download-link', 'download'],
      ['#rolebutton-link', 'role=button'], ['#foreign-link', 'foreign origin'],
      ['#otherpath-link', 'other path'], ['#otherquery-link', 'other query'],
      ['#credential-link', 'credentials']]) {
      const navBefore = (await shellLog(page)).nav;
      const errBefore = (await shellLog(page)).errors.length;
      await frame.dispatchEvent(id, 'click', { button: 0, ctrlKey: false, metaKey: false, shiftKey: false, altKey: false });
      assert.equal(await isOpen(frame, 'intl-analysis-tools'), false, `${why} must not reveal local Tools`);
      assert.equal(await locationHref(frame), before, `${why} must not change this page`);
      // A collapsed summary still renders, so probe a target that only exists inside
      // the collapsed research chain.
      await assertNoArrival(frame, 'deep-target');
      await settle(page);
      const log = await shellLog(page);
      if (why === 'other query') {
        assert.equal(log.nav, navBefore + 1, 'a different query is still a real same-site navigation');
      } else {
        assert.equal(log.nav, navBefore, `${why} must not reach the parent`);
      }
      const refused = why === 'other path' || why === 'credentials';
      assert.equal(log.errors.length, errBefore + (refused ? 1 : 0),
        `${why} keeps the bridge's own refusal behaviour`);
    }

    // Existing native semantics are untouched: the bridge still marks foreign links.
    assert.equal(await frame.evaluate(() => document.getElementById('foreign-link').getAttribute('target')), '_blank');
    assert.ok((await frame.evaluate(() => document.getElementById('foreign-link').getAttribute('rel'))).includes('noopener'));
  } finally { await context.close(); }
});

test('G an accepted location is read from this window, never from event.detail', async () => {
  const { context, page, frame } = await createShell();
  try {
    // A forged detail must not select anything while the location says otherwise.
    await frame.evaluate(() => {
      window.dispatchEvent(new CustomEvent('mmx:shell-location', { detail: { hash: '#intl-analysis-tools' } }));
      window.dispatchEvent(new CustomEvent('mmx:shell-location', { detail: '#intl-legacy-research' }));
    });
    assert.deepEqual(await openState(frame), { refFold: false, tools: false, legacy: false, jp: true });

    // The real notification, with the location the parent actually accepted.
    await frame.evaluate((href) => { history.replaceState(history.state, '', href); },
      `/intl.html${LIBRARY}#deep-target`);
    await waitNav(page, 1);
    assert.deepEqual(await openState(frame), { refFold: true, tools: true, legacy: true, jp: true });
    await awaitArrival(frame, 'deep-target');
  } finally { await context.close(); }
});

test('G country selection keeps its own focus, rail and history behaviour', async () => {
  const { context, page, frame } = await createShell();
  try {
    assert.equal(await frame.evaluate(() => document.getElementById('rail-jp').getAttribute('aria-current')), 'location');
    await frame.click('#rail-kr');
    assert.equal(await isOpen(frame, 'imc-country-KR'), true);
    assert.equal(await isOpen(frame, 'imc-country-JP'), false, 'one country at a time');
    assert.equal(await frame.evaluate(() => document.getElementById('rail-kr').getAttribute('aria-current')), 'location');
    assert.equal(await frame.evaluate(() => document.getElementById('rail-jp').getAttribute('aria-current')), null);
    assert.equal(await frame.evaluate(() => document.activeElement.id), 'kr-summary');
    await waitNav(page, 1);
    assert.equal((await shellLog(page)).nav, 1);
    assert.equal((await shellLog(page)).navs[0].sameDocument, true);
  } finally { await context.close(); }
});

test('G reveal never steals focus from a keyboard activation', async () => {
  const { context, page, frame } = await createShell();
  try {
    await frame.evaluate(() => document.getElementById('root-tools-link').focus());
    await frame.evaluate(() => document.getElementById('root-tools-link').click());
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), true);
    assert.equal(await frame.evaluate(() => document.activeElement.id), 'root-tools-link',
      'the disclosure must not take focus');
    await awaitArrival(frame, 'tools-summary');

    await frame.evaluate(() => document.getElementById('root-tools-link').focus());
    await page.keyboard.press('Enter');
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), true, 'a keyboard activation is an ordinary one');
    assert.equal(await frame.evaluate(() => document.activeElement.id), 'root-tools-link');
  } finally { await context.close(); }
});

test('G a newer destination cancels the stale deferred scroll', async () => {
  const { context, frame } = await createShell();
  try {
    // Both activations land in one turn; only the second may settle the position.
    await frame.evaluate(() => {
      document.getElementById('root-tools-link').click();
      document.getElementById('sibling-deep-link').click();
    });
    await awaitArrival(frame, 'deep-target');
    await assertNoArrival(frame, 'tools-summary');
    assert.deepEqual(await openState(frame), { refFold: true, tools: true, legacy: true, jp: true });
  } finally { await context.close(); }
});

test('G modeled history dispatches wrapped child navigation (not saved-view restoration)', async () => {
  const { context, page, frame } = await createShell();
  try {
    await frame.click('#sibling-tools-link');
    await awaitArrival(frame, 'tools-summary');
    const restingY = await scrollY(frame);
    const restingHref = await locationHref(frame);

    // Fixture entries dispatch ordinary wrapped child navigation. They do not model
    // a fresh parent-owned frame or its INIT.restore contract.
    await page.evaluate((entry) => window.__pushEntry(entry.href, entry.y), { href: restingHref, y: restingY });
    await page.evaluate((href) => window.__pushEntry(href, 0),
      `${CHILD_ORIGIN}/intl.html${LIBRARY}#deep-target`);

    await page.goBack();
    await page.waitForFunction(() => window.__shell.restored);
    await frame.waitForFunction((href) => location.href === href, restingHref);
    // A visible destination requires no additional alignment after this modeled
    // navigation. Actual saved-view preservation is checked by the actual parent.
    await awaitArrival(frame, 'tools-summary');
    assert.ok(Math.abs((await scrollY(frame)) - restingY) <= 2,
      `restoration moved from ${restingY} to ${await scrollY(frame)}`);

    await page.goForward();
    await frame.waitForFunction((href) => location.hash === '#deep-target');
    // This fixture dispatches a new wrapped child navigation to the deep target.
    // It is not evidence that a real parent's saved position may be overridden.
    assert.deepEqual(await openState(frame), { refFold: true, tools: true, legacy: true, jp: true });
    await awaitArrival(frame, 'deep-target');
  } finally { await context.close(); }
});

test('G standalone keeps a strict local test for hash and direct nested activation', async () => {
  const { context, page } = await createShell({ parent: false });
  try {
    const frame = page.mainFrame();
    assert.equal(await frame.evaluate(() => typeof window.MMXSharedShell), 'undefined',
      'a standalone page has no bridge to ask');
    await frame.click('#root-nested-link');
    assert.deepEqual(await openState(frame), { refFold: false, tools: true, legacy: true, jp: true });
    await awaitArrival(frame, 'legacy-summary');

    // Strict local checks: a foreign lookalike still reveals nothing.
    await frame.evaluate(() => {
      document.querySelector('details.ref-fold').open = false;
      document.getElementById('intl-analysis-tools').open = false;
      document.getElementById('intl-legacy-research').open = false;
    });
    for (const id of ['#foreign-link', '#otherpath-link', '#otherquery-link', '#blank-link']) {
      await frame.dispatchEvent(id, 'click', { button: 0 });
      assert.equal(await isOpen(frame, 'intl-analysis-tools'), false, `${id} must not reveal standalone Tools`);
      await assertNoArrival(frame, 'deep-target');
    }

    // A direct load with a nested hash opens the whole chain and arrives there.
    await page.goto(`${CHILD_ORIGIN}/intl.html#deep-target`);
    assert.deepEqual(await openState(page.mainFrame()), { refFold: true, tools: true, legacy: true, jp: true });
    await awaitArrival(page.mainFrame(), 'deep-target');
  } finally { await context.close(); }
});

test('E protocol, version and admission are unchanged by the repair', async () => {
  const { context, page, frame } = await createShell();
  try {
    const log = await shellLog(page);
    assert.equal(log.ready, 1);
    assert.equal(log.errors.length, 0);
    assert.equal(log.readyPayload.bridgeVersion, '20261018.1');
    assert.equal(log.readyPayload.documentVersion, '20261018.1');
    assert.equal(log.readyPayload.responseKind, 'content');
    assert.equal(await frame.evaluate(() => window.MMXSharedShell.__mmxBridge), PROTOCOL);
    assert.equal(await frame.evaluate(() => window.MMXSharedShell.active), true);
    assert.equal(typeof (await frame.evaluate(() => Object.keys(window.MMXSharedShell).sort().join(','))),
      'string');
    // The helper is the only addition to the published surface.
    assert.equal(await frame.evaluate(() => typeof window.MMXSharedShell.sameDocumentFragment), 'function');
    assert.equal(await frame.evaluate(() => Object.isFrozen(window.MMXSharedShell)), true);
    assert.deepEqual(await frame.evaluate(() => Object.keys(window.MMXSharedShell).sort()),
      ['__mmxBridge', 'active', 'applyingContext', 'navigate', 'openAuth', 'sameDocumentFragment']);
  } finally { await context.close(); }
});

test('G a live bridge without the helper fails closed and keeps the accepted-location fallback', async () => {
  const { context, page, frame } = await createShell();
  try {
    // The probe records how many accepted-location notifications had arrived when
    // Tools first became open. Speculative classification would open it at zero.
    await frame.evaluate(() => {
      window.__locationEvents = 0;
      window.__openedAt = null;
      window.addEventListener('mmx:shell-location', () => { window.__locationEvents += 1; });
      const tools = document.getElementById('intl-analysis-tools');
      new MutationObserver(() => {
        if (tools.open && window.__openedAt === null) window.__openedAt = window.__locationEvents;
      }).observe(tools, { attributes: true, attributeFilter: ['open'] });
    });
    await frame.evaluate(() => {
      delete window.MMXSharedShell;
      window.MMXSharedShell = Object.freeze({ __mmxBridge: 'mmx.shared-shell.v1', active: true });
    });

    await frame.click('#root-tools-link');
    await frame.waitForFunction(() => document.getElementById('intl-analysis-tools').open, null, { timeout: 3000 });
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), true, 'the fallback still resolves the arrival');
    const openedAt = await frame.evaluate(() => window.__openedAt);
    assert.ok(openedAt >= 1,
      `classification must fail closed: Tools opened after ${openedAt} accepted-location notifications`);
    await awaitArrival(frame, 'tools-summary');
  } finally { await context.close(); }
});

test('F native Tools links remain native in root and sibling positions, embedded and standalone', async () => {
  for (const parent of [true, false]) {
    for (const placement of ['imc-country-JP', 'siblings']) {
      const { context, page, frame } = await createShell({ parent });
      try {
        await frame.evaluate((containerId) => {
          const container = document.getElementById(containerId);
          for (const kind of ['download', 'blank', 'rolebutton']) {
            const a = document.createElement('a');
            a.id = 'native-' + kind;
            a.href = '#intl-analysis-tools';
            a.textContent = kind;
            if (kind === 'download') a.setAttribute('download', '');
            if (kind === 'blank') a.setAttribute('target', '_blank');
            if (kind === 'rolebutton') a.setAttribute('role', 'button');
            container.appendChild(a);
          }
        }, placement);
        await settleFrame(frame);
        const before = await navigationCounts(page, frame, parent);
        const beforeOpen = await openState(frame);
        const beforeY = await scrollY(frame);
        for (const kind of ['download', 'blank', 'rolebutton']) {
          // Synthetic default effects are suppressed at window bubble, after both
          // real handlers. This tests their exclusions without a download or popup.
          await frame.dispatchEvent('#native-' + kind, 'click', { button: 0 });
          await settleFrame(frame);
          await settle(page);
          const label = `${parent ? 'embedded' : 'standalone'} ${placement} ${kind}`;
          assert.deepEqual(await openState(frame), beforeOpen, label + ' keeps disclosures unchanged');
          assert.equal(await scrollY(frame), beforeY, label + ' keeps the reader position');
          assert.deepEqual(await navigationCounts(page, frame, parent), before,
            label + ' leaves URL, history and parent messages unchanged');
        }
      } finally { await context.close(); }
    }
  }
});

test('F an intercepted parent-origin role=button repeats the current Tools fragment', async () => {
  for (const placement of ['imc-country-JP', 'siblings']) {
    const { context, page, frame } = await createShell();
    try {
      await frame.click('#root-tools-link');
      await waitNav(page, 1);
      await awaitArrival(frame, 'tools-summary');
      await frame.evaluate(({ placement, href }) => {
        const a = document.createElement('a');
        a.id = 'parent-button';
        a.href = href;
        a.setAttribute('role', 'button');
        a.textContent = 'Tools';
        document.getElementById(placement).appendChild(a);
        document.getElementById('intl-analysis-tools').open = false;
      }, { placement, href: `${PARENT_ORIGIN}/intl.html#intl-analysis-tools` });
      await settleFrame(frame);
      assert.equal(await isOpen(frame, 'intl-analysis-tools'), false);
      assert.equal(await frame.evaluate(() =>
        window.MMXSharedShell.sameDocumentFragment(document.getElementById('parent-button'))),
      'intl-analysis-tools', 'the bridge explicitly classifies this first-party exception');
      const before = await navigationCounts(page, frame);
      await frame.click('#parent-button');
      await awaitArrival(frame, 'tools-summary');
      await settle(page);
      assert.equal(await isOpen(frame, 'intl-analysis-tools'), true);
      assert.deepEqual(await navigationCounts(page, frame), before,
        placement + ' reopens without an ACK or another history entry');
    } finally { await context.close(); }
  }
});

test('F an activation canceled at window capture leaves disclosure, position and navigation unchanged', async () => {
  const { context, page, frame } = await createShell();
  try {
    const before = await navigationCounts(page, frame);
    const beforeOpen = await openState(frame);
    const beforeY = await scrollY(frame);
    await frame.evaluate(() => {
      window.addEventListener('click', event => event.preventDefault(), { capture: true, once: true });
    });
    await frame.click('#root-tools-link');
    await settleFrame(frame);
    await settle(page);
    assert.deepEqual(await openState(frame), beforeOpen);
    assert.equal(await scrollY(frame), beforeY);
    assert.deepEqual(await navigationCounts(page, frame), before);
    // Later target/bubble cancellation is not proved by this capture-phase case.
  } finally { await context.close(); }
});

test('G newer outside, missing, country and query destinations cancel pending research alignment', async () => {
  for (const destination of ['outside', 'missing', 'country', 'query']) {
    const { context, page, frame } = await createShell();
    try {
      const newer = await frame.evaluate((destination) => {
        // Keep both actions in one task: the first research rAF is still pending.
        document.getElementById('root-deep-link').click();
        if (destination === 'outside') document.getElementById('outside-link').click();
        if (destination === 'missing') {
          document.getElementById('missing-link').click();
          window.scrollTo(0, 900);
        }
        if (destination === 'country') document.getElementById('rail-kr').click();
        if (destination === 'query') {
          history.replaceState(history.state, '', '/intl.html?view=history&note=a%20b&note=a+b&&flag&');
          window.scrollTo(0, 900);
        }
        return { href: location.href, y: window.pageYOffset };
      }, destination);
      await waitNav(page, 2);
      await settleFrame(frame);
      assert.equal(await locationHref(frame), newer.href, destination + ' remains current');
      if (destination === 'outside') await awaitArrival(frame, 'outside-target');
      if (destination === 'country') {
        assert.equal(await isOpen(frame, 'imc-country-KR'), true);
        assert.equal(await frame.evaluate(() => document.activeElement.id), 'kr-summary');
        await awaitArrival(frame, 'kr-summary');
      }
      if (destination === 'missing' || destination === 'query') {
        assert.ok(Math.abs((await scrollY(frame)) - newer.y) <= 1,
          destination + ' retains the position chosen after the newer navigation');
      }
      await assertNoArrival(frame, 'deep-target');
    } finally { await context.close(); }
  }
});
