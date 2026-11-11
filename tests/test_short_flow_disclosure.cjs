const fs = require('fs'), path = require('path'), assert = require('assert');
const text = fs.readFileSync(path.join(__dirname, '../templates/stock.html.j2'), 'utf8');
function block(t) {
  const a = t.indexOf('      if (pos.short_flow) {');
  const b = t.indexOf('      if (pos.insider)', a);
  assert(a >= 0 && b > a);
  return t.slice(a, b);
}
function helpers(t) {
  const a = t.indexOf('  function lz(');
  const b = t.indexOf('  function radarSVG(', a);
  assert(a >= 0 && b > a);
  return t.slice(a, b);
}
function render(t, sf, locale) {
  const rows = [];
  // Execute the shipped localization, escaping, numeric markup and row helpers.
  const f = new Function('pos', 'lang', 'record',
    helpers(t) + '\nvar html=""; var shippedKvRow=kvRow;' +
    'kvRow=function(k,v,w){record(k,v,w);return shippedKvRow(k,v,w);};' +
    block(t) + ';return {html:html, labels:{ratio:LF("sfratio"),trend:LF("sftrend"),z:LF("sfz"),na:LF("na")}};');
  const out = f({short_flow: sf}, () => locale, (k, v, w) => rows.push([k, v, w]));
  return {...out, rows};
}
const notes = {
  partial: ['Partial history', '历史样本不足'],
  observed_zero: ['Reported zero', '报告的卖空成交量为零']
};
const scopes = {
  latest: ['Latest ratio', '最新比率'],
  recent: ['Recent volume window', '近期成交量窗口'],
  baseline: ['Baseline volume window', '基准成交量窗口'],
  history_z: ['Historical z-score', '历史 z 分数']
};
const reasons = {
  parse_error: ['invalid input', '输入无效'],
  unavailable: ['incomplete inputs', '输入不完整'],
  no_observation: ['no paired volume observation', '没有配对的成交量观测']
};
const base = {short_ratio_pct: 50, trend_pp: 0, ratio_z: 0, n_days: 25, asof: '2026-11-11'};
function row(out, label) { return out.rows.find(r => r[0] === out.labels[label]); }
function qualify(out, sf, locale) {
  const i = locale === 'zh' ? 1 : 0;
  assert.strictEqual(row(out, 'ratio')[1], sf.short_ratio_pct == null ? out.labels.na : sf.short_ratio_pct.toFixed(1) + '%');
  const recognized = Object.keys(scopes).filter(k => sf.coverage && sf.coverage[k] && Object.hasOwn(reasons, sf.coverage[k].state));
  for (const scope of recognized) {
    assert(out.html.includes(scopes[scope][i] + ': ' + reasons[sf.coverage[scope].state][i] + '.'));
  }
  if (!recognized.length && Object.hasOwn(reasons, sf.state)) {
    assert(out.html.includes((i ? '卖空流量数据' : 'Short-flow data') + ': ' + reasons[sf.state][i] + '.'));
  }
  assert.strictEqual(!!row(out, 'z'), sf.ratio_z != null || recognized.includes('history_z'));
  if (sf.ratio_z == null && recognized.includes('history_z')) assert.strictEqual(row(out, 'z')[1], out.labels.na);
  if (notes[sf.state]) assert(out.html.includes(notes[sf.state][i]));
  else assert(!out.html.includes(notes.observed_zero[i]));
}
let cases = 0;
for (const lang of ['en', 'zh']) {
  for (const state of Object.keys(notes)) {
    const sf = {...base, state, short_ratio_pct: state === 'observed_zero' ? 0 : 50, ratio_z: state === 'partial' ? null : 0};
    qualify(render(text, sf, lang), sf, lang); cases++;
  }
  for (const scope of Object.keys(scopes)) for (const state of Object.keys(reasons)) {
    const sf = {...base, state, coverage: {[scope]: {state, reason: '<img unsafe>', n_rows: 25, n_missing: 1}}};
    if (scope === 'latest') sf.short_ratio_pct = null;
    if (scope === 'recent' || scope === 'baseline') sf.trend_pp = null;
    if (scope === 'history_z') sf.ratio_z = null;
    const out = render(text, sf, lang);
    qualify(out, sf, lang);
    assert(!out.html.includes('<img unsafe>'));
    if (scope === 'history_z') assert(row(out, 'ratio')[1] === '50.0%' && row(out, 'trend')[1].includes('0.0%'));
    cases++;
  }
  const mixed = {...base, state: 'parse_error', ratio_z: null, coverage: {
    history_z: {state: 'parse_error'}, baseline: {state: 'unavailable'},
    recent: {state: 'parse_error'}, latest: {state: 'no_observation'}
  }};
  const out = render(text, mixed, lang); qualify(out, mixed, lang);
  const offsets = Object.keys(scopes).map(k => out.html.indexOf(scopes[k][lang === 'zh' ? 1 : 0] + ':'));
  assert(offsets.every((v, i) => i === 0 || v > offsets[i - 1])); cases++;
  const unsafe = {...base, state: '<script>unsafe</script>', asof: '<img src=x onerror=unsafe>',
    coverage: {'<img unsafe>': {state: 'parse_error'}, history_z: {state: 'constructor'}, latest: {state: '<script>'}}};
  const escaped = render(text, unsafe, lang);
  assert(!escaped.html.includes('<img') && !escaped.html.includes('<script>'));
  assert(escaped.html.includes('&lt;img src=x onerror=unsafe&gt;'));
  assert(!escaped.html.includes('constructor')); cases++;
  const roundedPositive = {...base, short_ratio_pct: 0};
  qualify(render(text, roundedPositive, lang), roundedPositive, lang); cases++;
}
const baseline = process.env.SHORT_FLOW_BASELINE;
let htmlParity = 0, numericRowParity = 0;
if (baseline) {
  const old = fs.readFileSync(baseline, 'utf8');
  for (const lang of ['en', 'zh']) for (const state of [undefined, 'observed', 'unknown', 'unavailable', 'parse_error', 'no_observation']) for (let i = 0; i < 100; i++) {
    const sf = {state, short_ratio_pct: i, trend_pp: i - 50, ratio_z: i % 3 === 0 ? null : (i - 50) / 10, n_days: 20 + i, asof: '2026-11-11'};
    const next = render(text, sf, lang), previous = render(old, sf, lang);
    if (Object.hasOwn(reasons, state)) { assert.deepStrictEqual(next.rows, previous.rows); numericRowParity++; qualify(next, sf, lang); }
    else { assert.deepStrictEqual(next, previous); htmlParity++; }
    cases++;
  }
  for (const lang of ['en', 'zh']) for (const state of Object.keys(notes)) {
    const sf = {...base, state, short_ratio_pct: 0, trend_pp: -37.5, ratio_z: null, n_days: 8};
    assert.deepStrictEqual(render(text, sf, lang), render(old, sf, lang)); htmlParity++; cases++;
  }
}
const rendered = {};
if (process.argv[2]) {
  const sf = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')).short_flow;
  assert(sf && typeof sf === 'object');
  for (const lang of ['en', 'zh']) { rendered[lang] = render(text, sf, lang); qualify(rendered[lang], sf, lang); cases++; }
}
console.log(JSON.stringify({passed: cases, baselineParity: !!baseline, htmlParity, numericRowParity, rendered}));
