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
  assert.ok(h.includes('data-observation-id=""')); // O06: an invalid view claims no observation id
  assert.ok(!h.includes('rotobs_XYZ'));
});

test('O06: a view counts only with its source-owned ledger receipt', () => {
  const variants = [
    ['missing', (v) => { delete v.recorded; }],
    ['null', (v) => { v.recorded = null; }],
    ['non-object', (v) => { v.recorded = 'macro.rotation_events.ledger'; }],
    ['array', (v) => { v.recorded = [v.recorded]; }],
    ['wrong source', (v) => { v.recorded.source = 'macro.rotation_events.cache'; }],
    ['wrong ledger', (v) => { v.recorded.ledger = 'rotation_events/other.jsonl'; }],
    ['uppercase hex', (v) => { v.recorded.receipt_sha256 = v.recorded.receipt_sha256.toUpperCase(); }],
    ['63 chars', (v) => { v.recorded.receipt_sha256 = v.recorded.receipt_sha256.slice(1); }],
    ['non-string digest', (v) => { v.recorded.receipt_sha256 = 7; }],
  ];
  const good = render('journey_b_both_fell', 'en');
  assert.equal(stateOf(good), 'observed');
  assert.ok(/data-observation-id="rotobs_[0-9a-f]{40}"/.test(good), 'valid view keeps its id');
  for (const [label, mutate] of variants) {
    const view = fixture('journey_b_both_fell');
    mutate(view);
    for (const lang of ['en', 'zh']) {
      const h = fn(view, null, view.notification.event_as_of, lang, NOW);
      assert.equal(stateOf(h), 'unreadable', label + '/' + lang);
      assert.ok(h.includes('data-observation-id=""'), label + ' claims no id');
      assert.ok(!h.includes(view.notification.observation_id), label + ' id never shown');
    }
  }
  const h = render('malformed_missing_recorded', 'zh');
  assert.ok(h.includes('轮动记录未通过校验，未予显示。'));
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
  assert.ok(h2.includes('data-observation-id=""'), 'a malformed id is never echoed');
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

test('repair wave C: bilingual study rows, separated history, escaped record fields', () => {
  const zh = render('corrected', 'zh');
  for (const s of ['<span class="l-zh">数据源日期 ', '个配对可评估；缺失：', '<span class="l-zh">rotobs_ 编号为内容寻址', '来源链根：']) {
    assert.ok(zh.includes(s), 'ZH study row: ' + s);
  }
  assert.ok(render('corrected', 'en').includes('<br><span class="l-en">Corrected: '), 'original and corrected on separate lines');
  assert.ok(render('withdrawn', 'en').includes('<br><span class="l-en">Current: Withdrawn'), 'original and current on separate lines');
  assert.ok(fn(null, { as_of: '2026-10-30' }, '2026-10-30', 'zh', NOW).includes('<span class="l-zh">数据日期 2026-10-30</span>'),
    'ZH rotation context');
  const bad = '<img src=x onerror=alert(1)>';
  const w = fixture('withdrawn');
  w.previous.observation_id = bad;
  w.basis = bad;
  w.notification.source_as_of = '2026-10-29'; // lib _opt_iso_date: a real date; markup there is checked below
  w.coverage = { evaluable_2s: bad, registered_pairs: 8, missing_pair_ids: [] };
  w.lineage_roots = [bad];
  const outs = [
    fn(w, null, '2026-10-30', 'en', NOW),
    fn(null, { as_of: bad }, '2026-10-30', 'en', NOW),
    fn(null, { as_of: '2026-09-01' }, bad, 'en', NOW),
    fn(null, { as_of: bad }, bad, 'zh', NOW),
  ];
  assert.equal(stateOf(outs[0]), 'withdrawn', 'payloads leave the validated state unchanged');
  { const s = fixture('withdrawn'); s.notification.source_as_of = '2026-10-29' + bad;
    const h = fn(s, null, '2026-10-30', 'en', NOW);
    assert.equal(stateOf(h), 'unreadable', 'markup in a withdrawal source date fails the lib date check');
    assert.ok(!h.includes('<img'), 'never rendered'); }
  // lib _aware_utc parity: a stamp the lib rejects is unreadable, never rendered
  for (const key of ['observed_at', 'not_after']) {
    for (const st of ['garbage-but-long-enough-Z', '2026-10-30T21:15:00<b>Z', '2026-10-30T21:15:60Z',
                      '2026-02-30T21:15:00+00:00', '2026-10-30' + bad + 'T21:15:00Z']) {
      const s = fixture('withdrawn'); s.notification[key] = st;
      const h = fn(s, null, '2026-10-30', 'en', NOW);
      assert.equal(stateOf(h), 'unreadable', key + ' ' + st);
      assert.ok(!h.includes('<img') && !h.includes('<b>'), 'never rendered'); } }
  for (const sfx of ['+00:00', 'Z']) {
    const s = fixture('withdrawn'); const n = s.notification;
    n.observed_at = n.observed_at.replace('+00:00', '.123456' + sfx); n.not_after = n.not_after.replace('+00:00', sfx);
    assert.equal(stateOf(fn(s, null, '2026-10-30', 'en', NOW)), 'withdrawn', 'producer isoformat stamp ' + sfx); }
  assert.equal(stateOf(outs[2]), 'stale', 'aged context with a malformed session');
  for (const h of outs) {
    assert.ok(!h.includes('<img'), 'raw injected element');
    assert.ok(h.includes('&lt;img'), 'payload rendered as text');
  }
});

test('review r1: explicit keys, non-object wrapper, monospace id', () => {
  for (const key of ['values', 'source_as_of']) {
    const w = fixture('withdrawn');
    delete w.notification[key];
    assert.equal(stateOf(fn(w, null, '2026-10-30', 'en', NOW)), 'unreadable', 'withdrawal without explicit ' + key);
    const o = fixture('journey_b_both_fell');
    delete o.notification[key];
    assert.equal(stateOf(fn(o, null, o.notification.event_as_of, 'en', NOW)), 'unreadable', 'observation without explicit ' + key);
  }
  for (const bad of ['rotobs_x', ['a'], 7, true]) {
    assert.equal(stateOf(fn(bad, null, '2026-10-30', 'en', NOW)), 'unreadable', 'present non-object wrapper ' + JSON.stringify(bad));
  }
  assert.equal(stateOf(fn(null, null, '2026-10-30', 'en', NOW)), 'unavailable', 'null wrapper stays absent');
  assert.equal(stateOf(fn(undefined, null, '2026-10-30', 'en', NOW)), 'unavailable', 'missing wrapper stays absent');
  assert.match(src, /\.rc-ew-id\{user-select:all;font-family:var\(--font-mono\);\}/, 'selectable monospace id');
});

test('EW-P4-FU: blank pair_id and calendar-invalid dates are unreadable; real dates pass', () => {
  const run = (patch, session) => {
    const v = fixture('observed_rise');
    Object.assign(v.notification, patch);
    return stateOf(fn(v, null, session || v.notification.event_as_of, 'en', NOW));
  };
  for (const pid of ['   ', '\t', ' \n ', '\x1c', '\x1f', '\x85', '\u3000', '\u2028 \xa0', 'a'.repeat(129), '\u{1F600}'.repeat(129)]) {
    assert.equal(run({ pair_id: pid }), 'unreadable', JSON.stringify(pid)); }
  // lib _req_str keeps these: U+FEFF is not Python whitespace; length counts code points
  for (const pid of ['\ufeff', 'a'.repeat(128), '\u{1F600}'.repeat(128), 'x\u3000']) {
    assert.notEqual(run({ pair_id: pid }), 'unreadable', JSON.stringify(pid)); }
  const wd = (src) => { const v = fixture('withdrawn'); v.notification.source_as_of = src;
    return stateOf(fn(v, null, v.notification.event_as_of, 'en', NOW)); };
  for (const d of ['2025-13-01', '2026-02-30', '2025-02-29', '0000-01-01', '2026-1-01', 'garbage']) {
    assert.equal(wd(d), 'unreadable', 'withdrawal source ' + d); }
  { const ev = fixture('withdrawn').notification.event_as_of;
    assert.equal(wd(String(+ev.slice(0, 4) - 1) + ev.slice(4)), 'withdrawn'); }
  for (const d of ['2026-00-10', '2025-13-01', '2026-02-30', '2026-04-31', '2025-02-29', '0000-01-01']) {
    assert.equal(run({ event_as_of: d, source_as_of: d }, '2026-10-30'), 'unreadable', d);
  }
  for (const d of ['2024-02-29', '2026-04-30', '2025-12-31']) {
    assert.notEqual(run({ event_as_of: d, source_as_of: d }), 'unreadable', d);
  }
  assert.equal(stateOf(render('malformed_blank_pair', 'en')), 'unreadable');
  assert.equal(stateOf(render('malformed_calendar', 'en', '2026-10-30')), 'unreadable');
});
