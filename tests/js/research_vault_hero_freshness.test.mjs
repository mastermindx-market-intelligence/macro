// tests/js/research_vault_hero_freshness.test.mjs
//
// Hero-band regression coverage for the research desk.
//
// The real updateHero() body is read out of site/research_vault_app.js and
// executed under node:vm against bounded DOM stubs. Nothing here boots the
// rest of the app, touches a browser, or loads a CDN, and the tests assert on
// observed output rather than on the presence of source text.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const APP = resolve(ROOT, 'site/research_vault_app.js');
const appSource = readFileSync(APP, 'utf8');

const extracted = appSource.match(/^  function updateHero\(\) \{[\s\S]*?^  \}/m);
assert.ok(extracted, 'updateHero() not found in ' + APP + ' — has its indentation or signature changed?');
const UPDATE_HERO = extracted[0];

const DASH = '—';
const DELAYED_EN = 'Research updates are delayed. Showing the saved catalog.';
const DELAYED_ZH = '研报更新延迟，正在显示已保存的目录。';
const UNAVAILABLE_EN =
  'The research catalog could not be loaded. This is a loading problem, not an empty vault.';
const UNAVAILABLE_ZH = '无法载入研报目录。这是加载问题，并非研报库为空。';
const PREVIEW_EN = 'Latest preview loaded. Whole-vault weekly totals are temporarily unavailable.';
const PREVIEW_ZH = '最新预览已载入，完整库的本周统计暂不可用。';
const EMPTY_EN = 'No institutional reports are available yet.';
const EMPTY_ZH = '暂时还没有可用的机构研报。';

// A snapshot whose items WOULD yield a confident weekly claim (3 reports, 2
// desks, a most-covered theme, 2 highlighted) if anything derived from them.
const SNAPSHOT_ITEMS = [
  { id: 'r1', inst: 'Desk Alpha', tags: ['Chips', 'Capex'], top: true, date: '2026-10-20' },
  { id: 'r2', inst: 'Desk Beta', tags: ['Chips'], top: true, date: '2026-10-19' },
  { id: 'r3', inst: 'Desk Beta', tags: ['Power Grid'], top: false, date: '2026-10-18' },
];

// Proof of the ordering guarantee: if the stale guard is removed, misplaced,
// or placed after a derivation, this trap fires instead of a silent wrong
// number reaching the DOM.
function staleClockTrap() {
  throw new Error('isThisWeek() ran against a stale catalog: the hero derived a current-week claim');
}

function render(spec) {
  const nodes = new Map();
  let buildWebCalls = 0;
  const sandbox = {
    CATALOG_SOURCE: spec.source,
    CATALOG_FRESH: spec.fresh,
    CATALOG_PREVIEW: spec.preview === true,
    CATALOG_SUMMARY: spec.summaryObj || null,
    ITEMS: spec.items || [],
    TOTAL_COUNT: spec.total === undefined ? 2960 : spec.total,
    $: (id) => {
      if (!nodes.has(id)) nodes.set(id, { id, textContent: '' });
      return nodes.get(id);
    },
    buildWeb: () => { buildWebCalls += 1; },
    summaryNumber: (key) =>
      spec.summary && Object.prototype.hasOwnProperty.call(spec.summary, key) ? spec.summary[key] : null,
    isThisWeek: spec.isThisWeek,
    isDeskInst: (inst) => typeof inst === 'string' && inst.indexOf('Desk') === 0,
    T: (en) => en,
  };

  runInNewContext(UPDATE_HERO + '\nupdateHero();', sandbox, { timeout: 1000 });

  return {
    text: (id) => {
      const el = nodes.get(id);
      return el === undefined ? null : String(el.textContent);
    },
    buildWebCalls: () => buildWebCalls,
  };
}

test('stale live catalog: weekly figures neutral, archive total kept, delayed leads', () => {
  const v = render({
    source: 'live', fresh: false, items: SNAPSHOT_ITEMS, isThisWeek: staleClockTrap,
  });
  assert.equal(v.text('fig-new'), DASH);
  assert.equal(v.text('fig-desks'), DASH);
  assert.equal(v.text('fig-theme'), DASH);
  assert.equal(v.text('fig-total'), '2960');
  assert.equal(v.text('v-en-lead'), DELAYED_EN);
  assert.equal(v.text('v-zh-lead'), DELAYED_ZH);
  assert.equal(v.buildWebCalls(), 1);
  assert.doesNotMatch(v.text('v-en-lead'), /this week/);
  assert.doesNotMatch(v.text('v-zh-lead'), /本周新增/);
});

test('stale snapshot catalog: identical neutralisation to the stale live path', () => {
  const v = render({
    source: 'snapshot', fresh: false, items: SNAPSHOT_ITEMS, isThisWeek: staleClockTrap,
  });
  assert.equal(v.text('fig-new'), DASH);
  assert.equal(v.text('fig-desks'), DASH);
  assert.equal(v.text('fig-theme'), DASH);
  assert.equal(v.text('fig-total'), '2960');
  assert.equal(v.text('v-en-lead'), DELAYED_EN);
  assert.equal(v.text('v-zh-lead'), DELAYED_ZH);
  assert.equal(v.buildWebCalls(), 1);
});

test('unavailable catalog: every figure stays neutral with the loading-problem copy', () => {
  const v = render({
    source: 'unavailable', fresh: false, items: [], total: 0, isThisWeek: staleClockTrap,
  });
  assert.equal(v.text('fig-new'), DASH);
  assert.equal(v.text('fig-desks'), DASH);
  assert.equal(v.text('fig-theme'), DASH);
  assert.equal(v.text('fig-total'), DASH, 'an unavailable catalog must not claim a known total');
  assert.equal(v.text('v-en-lead'), UNAVAILABLE_EN);
  assert.equal(v.text('v-zh-lead'), UNAVAILABLE_ZH);
  assert.equal(v.buildWebCalls(), 1);
});

test('fresh catalog with server aggregate: 12 / 4 / 73 and the weekly lead lines survive', () => {
  const v = render({
    source: 'live', fresh: true, items: SNAPSHOT_ITEMS,
    isThisWeek: () => true,
    summary: { new_this_week: 12, desks_this_week: 4, highlighted: 73 },
    summaryObj: { most_covered_theme: 'Compute Supply Chain' },
  });
  assert.equal(v.text('fig-new'), '12');
  assert.equal(v.text('fig-desks'), '4');
  assert.equal(v.text('fig-theme'), 'Compute Supply Chain');
  assert.equal(v.text('fig-total'), '2960');
  assert.equal(
    v.text('v-en-lead'),
    '12 new institutional reports this week · 73 highlighted · 4 desks publishing.'
  );
  assert.equal(v.text('v-zh-lead'), '本周新增 12 篇机构研报 · 73 篇精选 · 4 家研究部门在发。');
  assert.equal(v.buildWebCalls(), 1);
});

test('fresh entitlement preview without an aggregate never turns a 3-item slice into a claim', () => {
  const v = render({
    source: 'live', fresh: true, preview: true, items: SNAPSHOT_ITEMS,
    isThisWeek: () => true, summary: null,
  });
  assert.equal(v.text('fig-new'), DASH, 'slice length must not be published as a weekly total');
  assert.equal(v.text('fig-desks'), DASH);
  assert.equal(v.text('fig-theme'), DASH);
  assert.equal(v.text('fig-total'), '2960');
  assert.equal(v.text('v-en-lead'), PREVIEW_EN);
  assert.equal(v.text('v-zh-lead'), PREVIEW_ZH);
  assert.doesNotMatch(v.text('v-en-lead'), /3 new institutional report/);
  assert.doesNotMatch(v.text('v-zh-lead'), /本周新增 3/);
});

test('stale catalog at TOTAL_COUNT 0 keeps the known 0 and still says delayed, not empty', () => {
  const v = render({
    source: 'snapshot', fresh: false, items: [], total: 0, isThisWeek: staleClockTrap,
  });
  assert.equal(v.text('fig-total'), '0', 'a stale zero is still a known archive count');
  assert.equal(v.text('fig-new'), DASH);
  assert.equal(v.text('fig-desks'), DASH);
  assert.equal(v.text('fig-theme'), DASH);
  assert.equal(v.text('v-en-lead'), DELAYED_EN);
  assert.equal(v.text('v-zh-lead'), DELAYED_ZH);
  assert.notEqual(v.text('v-en-lead'), EMPTY_EN);
  assert.notEqual(v.text('v-zh-lead'), EMPTY_ZH);
});

test('language repaint during initial loading preserves the existing shell', () => {
  const v = render({
    source: 'loading', fresh: false, items: SNAPSHOT_ITEMS, isThisWeek: staleClockTrap,
  });
  for (const id of ['fig-new', 'fig-desks', 'fig-theme', 'fig-total', 'v-en-lead', 'v-zh-lead']) {
    assert.equal(v.text(id), null, id + ' must remain untouched before a catalog settles');
  }
  assert.equal(v.buildWebCalls(), 0);
});
