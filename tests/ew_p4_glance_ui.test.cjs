'use strict';
// EW-P4.T1 (GD-EW-P4-B1): Sector Central observation glance — executes the
// production ewGlanceHtml between its markers (like rotation_early_context_ui
// does for EARLY_CONTEXT), plus source-level wiring checks for load()'s
// loading/unavailable states. No packages, no network, no DOM.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test').test;
const vm = require('node:vm');

const target = process.argv[2] || path.join(__dirname, '..', 'templates', 'rotation_events.js');
const src = fs.readFileSync(target, 'utf8');
const m = src.match(/\/\* EW_GLANCE_FN_START \*\/([\s\S]*?)\/\* EW_GLANCE_FN_END \*\//);
assert.ok(m, 'production function markers');
const escSource = "function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;');}";
const make = (prefix) => vm.runInNewContext('(function(){' + prefix + m[1] + ';return ewGlanceHtml;})()');
const fn = make(escSource), fnNoEsc = make('');
const FIX = path.join(__dirname, 'fixtures', 'ew_p4_observation');
const expected = JSON.parse(fs.readFileSync(path.join(FIX, 'expected.json'), 'utf8'));
const NOW = Date.parse('2026-10-31T12:00:00Z');

// SC session defaults to the fixture's own event date; the two cases that need
// today's session (2026-10-30) to exercise the stale / future-dated rules:
const SESSION_OVERRIDES = { stale_obs: '2026-10-30', malformed_future: '2026-10-30' };

function fixture(name) { return JSON.parse(fs.readFileSync(path.join(FIX, name + '.json'), 'utf8')); }
function render(name, lang, session) {
  const view = fixture(name);
  return fn(view, null, session || SESSION_OVERRIDES[name] || view.notification.event_as_of, lang || 'en', NOW);
}
const stateOf = (h) => (h.match(/data-ew-state="([a-z]+)"/) || [])[1];

test('state parity against expected.json, EN and ZH', () => {
  for (const name of Object.keys(expected)) {
    if (name === 'journey_c_envelope_1d253e1d') continue; // Radar envelope, not an SC wrapper
    for (const lang of ['en', 'zh']) {
      const h = render(name, lang);
      assert.equal(stateOf(h), expected[name].state, name + ' state');
      assert.ok(h.includes(lang === 'en' ? expected[name].en_contains : expected[name].zh_contains),
        name + '/' + lang + ' copy');
    }
  }
});

test('EN and ZH state words on the glance', () => {
  const cases = [
    ['journey_b_both_fell', 'Observed', '已观察到'],
    ['reversal', 'Reversal', '方向反转'],
    ['corrected', 'Corrected', '已更正'],
    ['withdrawn', 'Withdrawn', '已撤回'],
    ['stale_obs', 'Stale', '已过时'],
    ['partial_window_mismatch', 'Partial', '证据不完整'],
    ['conflict_20s', 'Conflicting horizons', '周期分歧'],
  ];
  for (const [name, en, zh] of cases) {
    assert.ok(render(name, 'en').includes('>' + en + '<'), name + ' EN word');
    assert.ok(render(name, 'zh').includes('>' + zh + '<'), name + ' ZH word');
  }
  assert.ok(fn(null, null, null, 'en', NOW).includes('>Unavailable<'), 'unavailable EN');
  assert.ok(fn(null, null, null, 'zh', NOW).includes('>暂不可用<'), 'unavailable ZH');
});

test('stricter id rule: lib-valid rotobs_XYZ stays UI-unreadable', () => {
  const h = render('malformed_id', 'en');
  assert.equal(stateOf(h), 'unreadable');
  assert.ok(h.includes('Rotation record failed checks and is not shown.'));
  assert.ok(h.includes('data-observation-id="rotobs_XYZ"')); // raw id echoed escaped, still not shown as fact
});

test('no observation: missing early_context is unavailable, aged context is stale', () => {
  assert.equal(stateOf(fn(null, null, null, 'en', NOW)), 'unavailable');
  const stale = fn(null, { as_of: '2026-10-20' }, '2026-10-30', 'en', NOW);
  assert.equal(stateOf(stale), 'stale');
  assert.ok(stale.includes('Rotation data unavailable for Oct 30; latest is Oct 20.'));
  assert.equal(stateOf(fn(null, { as_of: '2026-10-29' }, '2026-10-30', 'en', NOW)), 'unavailable');
});

test('legs withheld when the 2-session window mismatches, shown when only 20s is missing', () => {
  const mismatch = render('partial_window_mismatch', 'en');
  assert.ok(mismatch.includes('Partial evidence for XLP vs XLK; ratio withheld.'));
  assert.ok(!mismatch.includes('+2.06%'));
  const missing20 = render('partial_missing_20s', 'en');
  assert.ok(missing20.includes('Both fell; XLP fell less than XLK.'));
  assert.ok(missing20.includes('-1.00%') && missing20.includes('-3.00%') && missing20.includes('+2.06%'));
  assert.ok(missing20.includes('Not supplied') && missing20.includes('未提供'));
});

test('conflicting horizons carry the conflict sentence as text', () => {
  const h = render('conflict_20s', 'en');
  assert.ok(h.includes('The two-session move conflicts with the 20-session trend.'));
  assert.ok(render('conflict_20s', 'zh').includes('两个交易日的变化与20个交易日趋势不一致。'));
});

test('dynamic strings are escaped; a script payload in pair_id never appears raw', () => {
  const view = fixture('journey_b_both_fell');
  view.notification.pair_id = '</div><script>alert("1")</script>&';
  const h = fn(view, null, '2026-10-30', 'en', NOW);
  assert.ok(!h.includes('<script>'), 'raw <script>');
  assert.ok(h.includes('&lt;script&gt;'));
  assert.ok(h.includes('&quot;'));
  assert.ok(!/\son[a-z]+\s*=\s*["']/.test(h));
  const badId = fixture('journey_b_both_fell');
  badId.notification.observation_id = 'rotobs_"><img src=x onerror=alert(1)>aaaaaaaaaaaaaaaaaaaaaaaaaa';
  const h2 = fn(badId, null, '2026-10-30', 'en', NOW);
  assert.ok(!h2.includes('<img'), 'raw injected element via id');
  assert.ok(h2.includes('&lt;img'), 'id payload is escaped');
});

test('input is never mutated and the shared escape helper is optional', () => {
  const view = fixture('journey_b_both_fell');
  const before = JSON.stringify(view);
  fn(view, null, '2026-10-30', 'en', NOW);
  fn(view, null, '2026-10-30', 'zh', NOW);
  assert.equal(JSON.stringify(view), before);
  assert.ok(fnNoEsc(fixture('journey_b_both_fell'), null, '2026-10-30', 'en', NOW)
    .includes('US Technology leadership'));
});

test('study uses native details/summary and carries the full record', () => {
  const h = render('journey_b_both_fell', 'en');
  assert.ok(h.includes('<details class="rc-ew-study"><summary>'));
  assert.ok(h.includes('>Study this record<') && h.includes('>查看记录细节<'));
  assert.ok(h.includes('rotobs_ ids are content-addressed'));
  assert.ok(h.includes('6 of 8 pairs evaluable'));
  assert.ok(h.includes('raw prices are not republished'));
  const zh = render('journey_b_both_fell', 'zh');
  assert.ok(zh.includes('>查看记录细节<'));
  assert.ok(!zh.includes('本交易日无合格观察记录。')); // a record exists here
});

test('correction and withdrawal keep the original in history', () => {
  const corrected = render('corrected', 'en');
  assert.ok(corrected.includes('Corrected; the original notice remains in history.'));
  assert.ok(corrected.includes('Original (rotobs_'));
  assert.ok(corrected.includes('Corrected: n -0.50% · d -3.00% · r +2.58%'));
  const withdrawn = render('withdrawn', 'en');
  assert.ok(withdrawn.includes('Evidence for XLP vs XLK was withdrawn on Oct 30.'));
  const glanceOnly = withdrawn.slice(0, withdrawn.indexOf('<details')); // the study keeps the original
  assert.ok(!glanceOnly.includes('+2.06%'), 'withdrawn glance must not show stale numbers');
  assert.ok(withdrawn.includes('Original (rotobs_') && withdrawn.includes('n -1.00%'), 'study keeps original values');
  assert.ok(withdrawn.includes('Withdrawn — the record no longer asserts a measurement.'));
});

test('no title= attributes and no consent controls in the rendered output', () => {
  for (const name of Object.keys(expected)) {
    if (name === 'journey_c_envelope_1d253e1d') continue;
    const h = render(name, 'en') + render(name, 'zh');
    assert.ok(!/title=/.test(h), name + ' title=');
    assert.ok(!/<(form|input|button)\b/.test(h), name + ' consent control');
  }
});

test('no forecast/odds/sizing language anywhere in the rendered glance output', () => {
  const banned = ['forecast', 'odds', 'probability', 'hazard', 'crash', 'sizing', 'buy', 'sell',
    'trim', 'hedge', 'reduce exposure', 'activation', '预测', '概率', '崩盘', '买入', '卖出',
    '减仓', '加仓', '仓位', '对冲'];
  for (const name of Object.keys(expected)) {
    if (name === 'journey_c_envelope_1d253e1d') continue;
    const h = (render(name, 'en') + render(name, 'zh')).toLowerCase();
    for (const word of banned) assert.ok(!h.includes(word), name + ': ' + word);
  }
});

test('loading shell says Checking — never a calm word — and precedes the fetch', () => {
  assert.ok(src.includes('function ewLoadingHtml()'), 'loading shell present');
  const loading = src.slice(src.indexOf('function ewLoadingHtml()'), src.indexOf('function load()'));
  assert.ok(loading.includes('Checking rotation evidence…'));
  assert.ok(loading.includes('正在核对轮动依据…'));
  assert.ok(loading.includes('data-ew-state="loading"'));
  for (const calm of ['normal', 'stable', 'no change', '正常', '稳定', '无变化']) {
    assert.ok(!loading.toLowerCase().includes(calm), 'loading copy contains calm word: ' + calm);
  }
});

test('fetch/parse failure renders the scoped unavailable state', () => {
  assert.ok(src.includes("if(earlyEl) earlyEl.innerHTML=ewLoadingHtml();"), 'loading renders before fetch');
  assert.ok(src.includes("el.innerHTML=ewGlanceHtml(null,null,null,isZh()?'zh':'en',Date.now());"),
    'catch path renders unavailable');
  const failed = fn(null, null, null, 'en', NOW);
  assert.equal(stateOf(failed), 'unavailable');
  assert.ok(failed.includes('Rotation data unavailable — not proof of stability.'));
});

test('the glance is prepended to the early-context output and does not alter it', () => {
  assert.ok(src.includes("earlyEl.innerHTML=ewHtml+earlyContextHtml(res[0],isZh()?'zh':'en',Date.now())"),
    'prepend wiring');
  assert.ok(src.indexOf('ewGlanceHtml(view,ec,') < src.indexOf("earlyContextHtml(res[0],isZh()?'zh':'en',Date.now())"));
  const early = src.match(/\/\* EARLY_CONTEXT_FN_START \*\/([\s\S]*?)\/\* EARLY_CONTEXT_FN_END \*\//)[1];
  assert.ok(early.includes('function earlyContextHtml('), 'earlyContextHtml untouched');
});

test('the pre-existing rc-ec edge stripe is repaired, rc-ew uses even borders', () => {
  assert.ok(src.includes('.rc-ec-stale,.rc-ec-conflict{border:1px solid var(--line);border-radius:var(--r-ctl,8px);background:var(--surface-warn-subtle);'));
  assert.ok(!src.includes('.rc-ec-stale,.rc-ec-conflict{border-left:'));
  const rcEw = src.slice(src.indexOf('.rc-ew{margin'), src.indexOf("var s=document.createElement"));
  assert.ok(!/border-(left|right|top|inline-start|inline-end|block-start)\s*:/.test(rcEw));
  assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(rcEw));
  assert.ok(!rcEw.includes('rgb(') && !rcEw.includes('hsl('));
  assert.ok(rcEw.includes('.rc-ew-next:focus-visible,.rc-ew-study summary:focus-visible{outline:2px solid var(--link);outline-offset:2px;}'));
});

test('repair wave B: separator, routes and a single both-fell sentence', () => {
  const h = render('journey_b_both_fell', 'en');
  assert.ok(h.includes(' · <span class="rc-ew-built">'), 'quality · built separator');
  assert.ok(!h.includes('#rc-early-context'), 'no unregistered in-page route');
  assert.ok(h.includes('href="#rc-events-mount"'), 'registered SC route');
  assert.equal(h.split('Both fell; XLP fell less than XLK.').length - 1, 1, 'stated once');
  // JSON.parse makes 2.0 === 2, so the JS glance cannot tell a float session
  // count from an integer one; the Radar (Jinja) path enforces integers.
  assert.equal(JSON.parse('{"s":2.0}').s, 2);
});
