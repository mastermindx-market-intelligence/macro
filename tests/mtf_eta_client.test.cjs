const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const sourceRoot = process.env.SOURCE_ROOT || root;
const copy = process.env.SOURCE_COPY || 'templates';
const source = fs.readFileSync(path.join(sourceRoot, copy, 'mtf.js'), 'utf8');
const actualZero = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/mtf_eta/512980.SS-mtf.json')));
const actualPositive = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/mtf_eta/XIT.TO-mtf.json')));

// Execute the complete current renderer. Only DOM storage/style lookup are doubled.
// hydrateMTF's real JSON parsing and renderMTF's public entry are exercised unchanged.
function boot(lang = 'en', fixture = null) {
  let onLoad;
  const el = { innerHTML: '', getAttribute: () => JSON.stringify(fixture) };
  const document = {
    documentElement: { getAttribute: () => lang },
    querySelectorAll: () => fixture ? [el] : [],
    addEventListener: (event, callback) => { assert.equal(event, 'DOMContentLoaded'); onLoad = callback; },
  };
  const context = { window: {}, document, getComputedStyle: () => ({ getPropertyValue: () => '' }) };
  vm.runInNewContext(source, context, { filename: path.join(sourceRoot, copy, 'mtf.js') });
  assert.equal(typeof context.window.renderMTF, 'function');
  assert.equal(typeof onLoad, 'function');
  if (fixture) onLoad();
  return { el, render: mtf => context.window.renderMTF(el, mtf) };
}
function render(mtf, lang = 'en') {
  const before = JSON.stringify(mtf);
  const b = boot(lang); b.render(mtf);
  assert.equal(JSON.stringify(mtf), before, 'presentation must not mutate the producer payload');
  return b.el.innerHTML;
}
function state(direction, days, bars = 0.5) {
  const m = { rsi14: 50, stoch: 50, spark_rsi: [45, 50], spark_stoch: [40, 50],
    spark_hist: direction === 'up' ? [-1, -0.5] : [1, 0.5], macd_pos: direction === 'down',
    macd_approaching_up: direction === 'up', macd_approaching_dn: direction === 'down',
    macd_bars_to_cross: bars };
  if (days !== undefined) m.macd_days_to_cross = days;
  return m;
}
function eta(value, direction, lang) {
  return '≈' + value + (lang === 'zh' ? (direction === 'up' ? '日后上穿' : '日后下穿')
    : (direction === 'up' ? 'd to ↑cross' : 'd to ↓cross'));
}

for (const lang of ['en', 'zh']) {
  test(`actual committed 512980.SS data-mtf boot preserves zero-day ETA (${lang})`, () => {
    assert.equal(actualZero.D.macd_days_to_cross, 0);
    assert.equal(actualZero.D.macd_bars_to_cross, 0.5);
    assert.equal(actualZero.D.macd_approaching_up, true);
    const b = boot(lang, actualZero);
    assert.ok(b.el.innerHTML.includes(eta(0, 'up', lang)), 'committed zero-day ETA must not become one day');
    assert.ok(!b.el.innerHTML.includes(eta(1, 'up', lang)));
    assert.equal((b.el.innerHTML.match(/class="mtf-card"/g) || []).length, 3);
  });
  test(`actual XIT.TO positive-day caller remains six days (${lang})`, () => {
    assert.equal(actualPositive.D.macd_days_to_cross, 6);
    assert.equal(actualPositive.D.macd_bars_to_cross, 5.9);
    assert.ok(boot(lang, actualPositive).el.innerHTML.includes(eta(6, 'down', lang)));
  });
  for (const direction of ['up', 'down']) {
    test(`valid zero wins over a positive bars fallback (${direction}, ${lang})`, () => {
      assert.ok(render({ D: state(direction, 0) }, lang).includes(eta(0, direction, lang)));
    });
    for (const [tf, days, bars] of [['D', 2, 1.6], ['3D', 6, 2], ['W', 10, 2]]) {
      test(`producer trading days retain priority on ${tf} (${direction}, ${lang})`, () => {
        assert.ok(render({ [tf]: state(direction, days, bars) }, lang).includes(eta(days, direction, lang)));
      });
    }
    for (const days of [undefined, null]) {
      test(`legacy ${days === null ? 'null' : 'absent'} days keeps bars fallback (${direction}, ${lang})`, () => {
        assert.ok(render({ D: state(direction, days, 2.4) }, lang).includes(eta(2, direction, lang)));
      });
    }
    for (const days of ['', false, NaN]) {
      test(`other falsy ${String(days)} keeps inherited fallback (${direction}, ${lang})`, () => {
        assert.ok(render({ D: state(direction, days, 2.4) }, lang).includes(eta(2, direction, lang)));
      });
    }
    test(`confirmed-cross wording precedes zero ETA (${direction}, ${lang})`, () => {
      const m = state(direction, 0);
      m[direction === 'up' ? 'macd_cross_up' : 'macd_cross_dn'] = true;
      const out = render({ D: m }, lang);
      assert.ok(!out.includes('≈'));
      assert.ok(out.includes(lang === 'zh' ? (direction === 'up' ? '刚上穿' : '刚下穿')
        : (direction === 'up' ? 'just crossed up' : 'just crossed down')));
    });
    test(`missing ETA remains directional state without invented countdown (${direction}, ${lang})`, () => {
      const out = render({ D: state(direction, null, null) }, lang);
      assert.ok(!out.includes('≈'));
      assert.ok(out.includes(lang === 'zh' ? (direction === 'up' ? '看空' : '看多')
        : (direction === 'up' ? 'bearish' : 'bullish')));
    });
  }
}
test('template and site renderer bytes are paired', () => {
  assert.deepEqual(fs.readFileSync(path.join(sourceRoot, 'templates/mtf.js')),
    fs.readFileSync(path.join(sourceRoot, 'site/mtf.js')));
});
