/* Source-level journey checks for the standalone design reference.
 * This minimal DOM harness checks state/history/focus intent. It cannot prove
 * browser layout, accessibility-tree behavior, animation rendering or production.
 * Run: node verify-motion-reference.cjs
 */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, 'evidence-motion-reference.html'), 'utf8');
const script = html.match(/<script>([\s\S]+)<\/script>/)[1];

function fixture(url = 'https://design-reference.invalid/evidence.html', retainedState = null, preferences = {}) {
  const nodes = new Map(), copyNodes = [], handlers = new Map();
  const document = { documentElement: { dataset: {} }, activeElement: null };
  function element(attrs, text = '') {
    const id = attrs.match(/\bid="([^"]+)"/)?.[1];
    const copy = attrs.match(/\bdata-copy="([^"]+)"/)?.[1];
    const listeners = new Map(), classes = new Set(), animationStarts = [];
    const el = { id, textContent: text, dataset: copy ? { copy } : {}, hidden: /\bhidden\b/.test(attrs), value: '', checked: false, offsetWidth: 800,
      animationStarts,
      classList: { add: name => { classes.add(name); if (name === 'enter') animationStarts.push(name); }, remove: name => classes.delete(name), contains: name => classes.has(name) },
      addEventListener: (name, fn) => listeners.set(name, fn),
      focus: () => { document.activeElement = el; },
      fire(name, extra = {}) { const event = { button: 0, preventDefault() { this.defaultPrevented = true; }, ...extra }; listeners.get(name)?.(event); return event; }
    };
    if (id) nodes.set(id, el);
    if (copy) copyNodes.push(el);
    return el;
  }
  for (const match of html.matchAll(/<([a-z][a-z0-9-]*)\b([^>]*)>([^<]*)/g)) element(match[2], match[3]);
  document.getElementById = id => { assert(nodes.has(id), `Fixture node exists: ${id}`); return nodes.get(id); };
  document.querySelectorAll = selector => { assert.equal(selector, '[data-copy]'); return copyNodes; };
  const entries = [{ url, state: retainedState }];
  let index = 0;
  let mediaChange = () => {};
  const media = { matches: !!preferences.reducedMotion, addEventListener: (_, fn) => { mediaChange = fn; } };
  const context = { document, URL, console, scrollY: 0,
    location: new URL(url),
    matchMedia: () => media,
    addEventListener: (name, fn) => handlers.set(name, fn),
    requestAnimationFrame: fn => fn(),
    scrollTo: options => { context.scrollY = options.top; }
  };
  function move(delta) {
    const next = index + delta;
    if (next < 0 || next >= entries.length) return;
    index = next; context.location = new URL(entries[index].url);
    handlers.get('popstate')?.({ state: structuredClone(entries[index].state) });
  }
  context.history = {
    get state() { return entries[index].state; },
    replaceState(state, _, href) { entries[index] = { state: structuredClone(state), url: String(href) }; context.location = new URL(href); },
    pushState(state, _, href) { entries.splice(index + 1); entries.push({ state: structuredClone(state), url: String(href) }); index++; context.location = new URL(href); },
    back: () => move(-1), forward: () => move(1)
  };
  vm.runInNewContext(script, context, { filename: 'evidence-motion-reference.html' });
  return { context, nodes, get: id => nodes.get(id), click: id => nodes.get(id).fire('click'),
    change: (id, value) => { nodes.get(id).value = value; nodes.get(id).fire('change'); },
    input: value => { nodes.get('query').value = value; nodes.get('query').fire('input'); },
    focused: () => document.activeElement?.id,
    setSystemReducedMotion: value => { media.matches = value; mediaChange({ matches: value }); },
    back: context.history.back, forward: context.history.forward,
    url: () => context.location, state: () => context.history.state
  };
}

const checks = [];
function check(name, fn) { fn(); checks.push(name); }

check('Open evidence preserves the query and pins the source snapshot', () => {
  const f = fixture(); f.input('HBM'); f.click('open-evidence');
  assert.equal(f.get('evidence-view').hidden, false);
  assert.equal(f.url().searchParams.get('q'), 'HBM');
  assert.equal(f.url().searchParams.get('snapshot'), 'gmi-2026-11-03');
  assert.equal(f.focused(), 'evidence-title');
});
check('Back restores the original scroll position and triggering control', () => {
  const f = fixture(); f.context.scrollY = 420; f.click('open-evidence'); f.back();
  assert.equal(f.context.scrollY, 420); assert.equal(f.focused(), 'open-evidence');
});
check('Forward puts the evidence heading in view', () => {
  const f = fixture(); f.context.scrollY = 420; f.click('open-evidence'); f.back(); f.forward();
  assert.equal(f.context.scrollY, 0); assert.equal(f.focused(), 'evidence-title');
});
check('Current appearance/language/motion survive Back with a matching URL', () => {
  const f = fixture(); f.click('open-evidence'); f.click('language'); f.click('theme');
  f.get('reduce').checked = true; f.get('reduce').fire('change'); f.back();
  assert.equal(f.url().searchParams.get('lang'), 'zh'); assert.equal(f.context.document.documentElement.lang, 'zh-CN');
  assert.equal(f.url().searchParams.get('appearance'), 'light');
  assert.equal(f.url().searchParams.get('motion'), 'reduce');
  f.forward(); assert.equal(f.get('evidence-view').classList.contains('enter'), false);
});
check('History and reload cannot undo the simulated current access denial', () => {
  const f = fixture(); f.click('open-evidence'); f.change('source-state', 'denied'); f.back();
  assert.equal(f.get('theme-card').hidden, true); assert.equal(f.url().searchParams.get('state'), 'denied');
  assert.equal(f.focused(), 'theme-title');
  const reloaded = fixture(f.url().href, f.state());
  assert.equal(reloaded.get('theme-card').hidden, true); assert.equal(reloaded.get('evidence-card').hidden, true);
});
check('Reload restores a qualified theme return position', () => {
  const f = fixture(); f.context.scrollY = 420; f.click('open-evidence'); f.back();
  const reloaded = fixture(f.url().href, f.state());
  assert.equal(reloaded.context.scrollY, 420); assert.equal(reloaded.focused(), 'open-evidence');
});
check('A direct evidence link returns safely without assuming an origin history entry', () => {
  const f = fixture('https://design-reference.invalid/evidence.html?view=evidence'); f.click('back');
  assert.equal(f.get('theme-view').hidden, false); assert.equal(f.focused(), 'theme-title');
});
check('Empty results retain the query and expose an explicit clear action', () => {
  const f = fixture(); f.input('unmatched specimen');
  assert.equal(f.get('no-results').hidden, false); assert.equal(f.get('theme-card').hidden, true);
  f.click('clear-query'); assert.equal(f.get('theme-card').hidden, false); assert.equal(f.focused(), 'query');
});
check('A failed read keeps the dated example without pretending it is current', () => {
  const f = fixture(); f.change('source-state', 'failed');
  assert.equal(f.get('theme-card').hidden, false); assert.equal(f.get('read-notice').hidden, false);
  assert.equal(f.url().searchParams.get('state'), 'failed');
});


function reading(f) {
  return Object.fromEntries(['metric', 'value', 'unit', 'period', 'capture'].map(key => [key, f.get('ex-' + key).textContent]));
}
function visibleResult(f) {
  return { reading: reading(f), hidden: f.get('ex-reading').hidden, busy: f.get('ex-panel').ariaBusy,
    status: f.get('ex-status').textContent, announcement: f.get('ex-announce').textContent,
    entrances: f.get('ex-reading').animationStarts.length };
}

check('Expectations context changes retire the complete previous reading', () => {
  const f = fixture(); assert.equal(f.get('ex-value').textContent, '11.02');
  f.get('ex-context').focus(); f.change('ex-context', 'revenue');
  assert.equal(f.get('ex-reading').hidden, true); assert.equal(f.get('ex-panel').ariaBusy, 'true');
  assert.deepEqual(reading(f), { metric: '', value: '', unit: '', period: '', capture: '' });
  assert.match(f.get('ex-selected').textContent, /Revenue/);
  assert.match(f.get('ex-status').textContent, /Loading/);
  assert.equal(f.focused(), 'ex-context');
  f.click('ex-fail-latest');
  assert.equal(f.get('ex-reading').hidden, true);
  assert.deepEqual(reading(f), { metric: '', value: '', unit: '', period: '', capture: '' });
  assert.match(f.get('ex-status').textContent, /could not load/);
});
check('Expectations refresh and failure retain the same complete dated bundle', () => {
  const f = fixture(), before = reading(f);
  f.get('ex-refresh').focus(); f.click('ex-refresh');
  assert.deepEqual(reading(f), before); assert.equal(f.get('ex-reading').hidden, false);
  assert.equal(f.get('ex-panel').ariaBusy, 'true'); assert.match(f.get('ex-status').textContent, /dated reading retained/);
  assert.equal(f.focused(), 'ex-refresh');
  f.click('ex-fail-latest');
  assert.deepEqual(reading(f), before); assert.equal(f.get('ex-panel').ariaBusy, 'false');
  assert.match(f.get('ex-status').textContent, /Read failed/);
  assert.equal(f.get('ex-reading').classList.contains('enter'), false);
});
check('Expectations latest response commits labels, value, period and clock together', () => {
  const f = fixture(); f.click('ex-refresh'); f.click('ex-deliver-latest');
  assert.deepEqual(reading(f), { metric: 'EPS', value: '11.12', unit: 'USD/share', period: 'FY 2027 · 31 Aug 2027', capture: '21 Oct 2026 · 13:05 UTC' });
  assert.equal(f.get('ex-panel').ariaBusy, 'false');
  assert.equal(f.get('ex-announce').textContent, 'Selected reading updated.');
  assert.equal(f.get('ex-reading').animationStarts.length, 1);
  assert.match(f.get('ex-receipt').textContent, /Committed: 1/);
  f.click('language');
  assert.equal(f.get('ex-value').textContent, '11.12'); assert.equal(f.get('ex-unit').textContent, '美元/股');
  assert.equal(f.get('ex-capture').textContent, '2026年10月21日 · 13:05 UTC');
  f.click('ex-refresh'); f.click('theme'); f.click('language');
  assert.equal(f.get('ex-value').textContent, '11.12'); assert.equal(f.get('ex-capture').textContent, '21 Oct 2026 · 13:05 UTC');
  assert.equal(f.get('ex-panel').ariaBusy, 'true'); assert.match(f.get('ex-receipt').textContent, /Pending: 2/);
});
check('Expectations rejects late A→B→A and overlapping-refresh responses', () => {
  const f = fixture(); f.click('ex-refresh'); f.change('ex-context', 'revenue'); f.change('ex-context', 'eps');
  const waiting = visibleResult(f); f.get('ex-deliver-earlier').focus(); f.click('ex-deliver-earlier');
  assert.deepEqual(visibleResult(f), waiting); assert.equal(f.focused(), 'ex-deliver-earlier');
  f.click('ex-deliver-latest');
  assert.equal(f.get('ex-value').textContent, '11.20'); assert.equal(f.get('ex-capture').textContent, '22 Oct 2026 · 13:05 UTC');
  const g = fixture(); g.click('ex-refresh'); g.click('ex-refresh'); g.click('ex-deliver-latest');
  const settled = visibleResult(g); g.click('ex-deliver-earlier');
  assert.deepEqual(visibleResult(g), settled);
  assert.equal(g.get('ex-value').textContent, '11.20'); assert.match(g.get('ex-receipt').textContent, /Committed: 1/);
});
check('Expectations manual and system reduced motion preserve the accepted reading', () => {
  const manual = fixture(); manual.get('reduce').checked = true; manual.get('reduce').fire('change');
  manual.click('ex-refresh'); manual.click('ex-deliver-latest');
  const system = fixture(undefined, null, { reducedMotion: true }); system.click('ex-refresh'); system.click('ex-deliver-latest');
  assert.deepEqual(reading(manual), reading(system)); assert.equal(manual.get('ex-value').textContent, '11.12');
  assert.equal(manual.get('ex-reading').classList.contains('enter'), false);
  assert.equal(system.get('ex-reading').classList.contains('enter'), false);
  const changing = fixture(); changing.click('ex-refresh'); changing.click('ex-deliver-latest');
  assert.equal(changing.get('ex-reading').classList.contains('enter'), true);
  const accepted = reading(changing), receipt = changing.get('ex-receipt').textContent;
  changing.get('ex-context').focus(); changing.setSystemReducedMotion(true);
  assert.equal(changing.get('ex-reading').classList.contains('enter'), false);
  assert.deepEqual(reading(changing), accepted); assert.equal(changing.get('ex-receipt').textContent, receipt);
  assert.equal(changing.focused(), 'ex-context');
  changing.setSystemReducedMotion(false);
  assert.equal(changing.get('ex-reading').classList.contains('enter'), false);
  assert.deepEqual(reading(changing), accepted);
});

console.log(JSON.stringify({ result: 'PASS', checks: checks.length, passed: checks, limitation: 'Source DOM harness only; browser layout, motion rendering and installed integration remain unverified.' }, null, 2));

