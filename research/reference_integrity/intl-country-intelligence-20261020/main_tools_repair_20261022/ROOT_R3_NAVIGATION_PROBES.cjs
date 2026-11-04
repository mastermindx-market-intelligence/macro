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
 * with the root's actual-parent acceptance run.
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

const BRIDGE = fs.readFileSync(path.join("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018", 'templates', 'shared_shell_bridge.js'), 'utf8');
const CONTROLLER = fs.readFileSync(path.join("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018", 'templates', 'intl_country_cockpit.js'), 'utf8');

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
 * details.ref-fold > #intl-analysis-tools > #intl-legacy-research. Every anchor
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
  <details class="ref-fold" id="ref-fold">
    <summary id="ref-summary">Reference</summary>
    <details id="intl-analysis-tools">
      <summary id="tools-summary">International analysis tools</summary>
      ${filler('tools-filler', 26)}
      <details id="intl-legacy-research">
        <summary id="legacy-summary">Legacy research</summary>
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
    refFold: document.getElementById('ref-fold').open,
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


test('ROOT already-canceled activation leaves disclosures and navigation unchanged', async () => {
  const {context,page,frame}=await createShell();
  try {
    const before={href:await locationHref(frame),open:await openState(frame),nav:(await shellLog(page)).nav};
    await frame.evaluate(() => {
      const event=new MouseEvent('click',{bubbles:true,cancelable:true,button:0});
      event.preventDefault();
      document.getElementById('root-tools-link').dispatchEvent(event);
    });
    await settle(page);
    assert.deepEqual(await openState(frame),before.open,'a canceled activation must not open disclosures');
    assert.equal(await locationHref(frame),before.href);
    assert.equal((await shellLog(page)).nav,before.nav);
  } finally {await context.close();}
});
test('ROOT a newer destination outside Tools cancels its pending alignment', async () => {
  const {context,page,frame}=await createShell();
  try {
    const result=await frame.evaluate(async () => {
      document.getElementById('root-tools-link').click();
      document.getElementById('outside-link').click();
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      return {hash:location.hash,y:scrollY};
    });
    assert.equal(result.hash,'#outside-target');
    await settle(page);
    assert.equal(await frame.evaluate(ARRIVAL,'outside-target'),true,'the latest destination must remain the visible arrival');
    await assertNoArrival(frame,'tools-summary');
  } finally {await context.close();}
});
