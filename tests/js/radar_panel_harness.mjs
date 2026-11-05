/**
 * Fake-DOM harness for site/radar_panel.js honesty-section tests (W23-L8).
 *
 * Loads the real panel into a fresh node:vm context per render, stubs fetch
 * with inline fixtures (URL basename -> committed-shaped object), runs
 * window.renderRadarFull and returns the rendered #rx-honesty section HTML
 * (renderHonesty) or the whole mount plus every #id node the panel painted
 * (renderPanel: the board rows land in #rx-tbody, the name rows in #rx-nrows).
 * Stdlib only; no network; no site/ or data/ reads at test time. Source path
 * mirrors tests/js/stockbrief_freshness.test.mjs (RADAR_PANEL_JS override,
 * resolved against process.cwd(), else the repo-relative URL).
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import vm from 'node:vm';

function sourcePath() {
  if (process.env.RADAR_PANEL_JS) return resolve(process.cwd(), process.env.RADAR_PANEL_JS);
  return new URL('../../site/radar_panel.js', import.meta.url);
}

function fakeEl() {
  return {
    innerHTML: '',
    textContent: '',
    value: 'all',
    style: {},
    id: '',
    appendChild() {},
    addEventListener() {},
    removeEventListener() {},
    setAttribute() {},
    getAttribute() { return null; },
    querySelector() { return fakeEl(); },
    querySelectorAll() { return []; },
    classList: {
      add() {},
      remove() {},
      toggle() {},
      contains() { return false; },
    },
  };
}

// The mount resolves "#id" to one persistent element per id, as a real DOM
// does, so innerHTML the panel paints into byId() nodes can be read back.
function fakeMount() {
  const nodes = {};
  const mount = fakeEl();
  mount.querySelector = function querySelector(sel) {
    const m = /^#([\w-]+)$/.exec(String(sel));
    if (!m) return fakeEl();
    if (!nodes[m[1]]) nodes[m[1]] = fakeEl();
    return nodes[m[1]];
  };
  return { mount, nodes };
}

function makeFetch(byName) {
  return function fetchStub(url) {
    const name = String(url).split('/').pop();
    const fixture = Object.prototype.hasOwnProperty.call(byName, name)
      ? byName[name] : undefined;
    if (fixture === undefined || fixture === null) {
      return Promise.resolve({ ok: false, json: async () => null });
    }
    return Promise.resolve({ ok: true, json: async () => fixture });
  };
}

const tick = () => new Promise((done) => setTimeout(done, 0));

async function render(fixtures) {
  const { mount, nodes } = fakeMount();
  const fakeDocument = {
    readyState: 'complete',
    querySelector(sel) {
      return sel === '#divergence-radar' ? mount : fakeEl();
    },
    getElementById() { return null; },
    createElement() { return fakeEl(); },
    addEventListener() {},
    removeEventListener() {},
    documentElement: { getAttribute() { return null; } },
    head: fakeEl(),
    body: fakeEl(),
  };
  const byName = {
    'radar.json': fixtures.radar,
    'radar_enriched.json': fixtures.enriched,
    'radar_news.json': fixtures.news,
    'radar_ticker.json': fixtures.tickers,
    'radar_ic.json': fixtures.ic,
    'radar_track_record.json': fixtures.track,
    'narrative_brain.json': fixtures.brain,
  };
  const errors = [];
  const onError = (err) => {
    errors.push(String((err && err.message) ? err.message : err));
  };
  const src = readFileSync(sourcePath(), 'utf8');
  const sandbox = {
    document: fakeDocument,
    fetch: makeFetch(byName),
    setTimeout,
    clearTimeout,
    console,
  };
  const ctx = vm.createContext(sandbox);
  vm.runInContext('var window = globalThis;', ctx);
  process.on('unhandledRejection', onError);
  process.on('uncaughtException', onError);
  try {
    vm.runInContext(src, ctx, { filename: 'radar_panel.js' });
    vm.runInContext('window.renderRadarFull({ base: "basketdata/" });', ctx);
    await tick();
    await tick();
  } catch (err) {
    onError(err);
  } finally {
    process.removeListener('unhandledRejection', onError);
    process.removeListener('uncaughtException', onError);
  }
  if (errors.length) assert.fail('render threw: ' + errors.join(' | '));
  const painted = {};
  for (const id of Object.keys(nodes)) painted[id] = nodes[id].innerHTML;
  return { html: mount.innerHTML, nodes: painted };
}

export async function renderPanel(fixtures) {
  return render(fixtures);
}

export async function renderHonesty(fixtures) {
  const { html } = await render(fixtures);
  const start = html.indexOf('<section class="rx-honesty');
  assert.ok(start >= 0, 'honesty section rendered into the mount');
  const end = html.indexOf('</section>', start);
  assert.ok(end > start, 'honesty section is closed');
  return html.slice(start, end + '</section>'.length);
}
