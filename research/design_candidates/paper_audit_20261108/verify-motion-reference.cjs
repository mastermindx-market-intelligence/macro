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

function fixture(url = 'https://design-reference.invalid/evidence.html', retainedState = null) {
  const nodes = new Map(), copyNodes = [], handlers = new Map();
  const document = { documentElement: { dataset: {} }, activeElement: null };
  function element(attrs, text = '') {
    const id = attrs.match(/\bid="([^"]+)"/)?.[1];
    const copy = attrs.match(/\bdata-copy="([^"]+)"/)?.[1];
    const listeners = new Map(), classes = new Set();
    const el = { id, textContent: text, dataset: copy ? { copy } : {}, hidden: /\bhidden\b/.test(attrs), value: '', checked: false, offsetWidth: 800,
      classList: { add: name => classes.add(name), remove: name => classes.delete(name), contains: name => classes.has(name) },
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
  const context = { document, URL, console, scrollY: 0,
    location: new URL(url),
    matchMedia: () => ({ matches: false, addEventListener() {} }),
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

console.log(JSON.stringify({ result: 'PASS', checks: checks.length, passed: checks, limitation: 'Source DOM harness only; browser layout, motion rendering and installed integration remain unverified.' }, null, 2));
