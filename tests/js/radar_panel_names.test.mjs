/**
 * W23-L18 Spec 5 — Stocks tab: separate per-name reads from theme echoes.
 *
 * Fixtures are committed-shaped copies of radar_ticker.json (schema
 * radar_ticker.v1, as_of 2026-10-19, n 215, n_attributed 185) with the two
 * rows quoted from the committed record — SNAP (source "signal",
 * rs_vs_spy_60d 30.1, signal_score 39) and DDOG (source "basket_attributed",
 * rs_vs_spy_60d -2.54, signal_score null, basket non_ai_software) — plus one
 * committed-shaped radar flag (radar.flags must be non-empty). Rendered
 * through tests/js/radar_panel_harness.mjs — stdlib only, no network, no
 * site/ or data/ reads at test time. The tab button lives in mount.innerHTML
 * (html); the name rows are painted by paintNames into nodes['rx-nrows'].
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { renderPanel } from './radar_panel_harness.mjs';

function flag() {
  return {
    id: '2026-10-14-industrial_distribution',
    basket: 'industrial_distribution',
    name: 'Industrial Distribution & Capital Goods',
    name_zh: '工业分销与资本品',
    category: 'Mixed',
    state: 'QUIET',
    lifecycle: 'quiet',
    divergence: 0.937,
    salience: 0.937,
    consensus: { rel_60d: -0.02, z: -0.19, dir: -1 },
    news: {
      n_articles_7d: 2, velocity: 1.2, acceleration: 1.2, metric: 1.2,
      unscheduled_share: 1.0, tier1_share: 0.0, buckets: [],
      is_context_only: true,
    },
    warn: {
      warn_z: null, warn_workers_90d: null, warn_count_90d: null,
      warn_yoy_ratio: null, matched_tickers: [], n_matched: 0,
      coverage_note: 'WARN store absent — no employer layoff data.',
    },
    note: 'Activity and price have moved together.',
    note_zh: '活动与价格同步。',
    observable: {
      accel: 0.384, dir: -1, z: 1.161, recent_3m_usd: -8000.0,
      base_3m_usd: 0.0, n_covered: 12, n_sources: 3,
      covered: ['AIT', 'FAST', 'FERG', 'GWW', 'KMT', 'MSM'],
      sources: [],
    },
  };
}

function radarFixture() {
  return {
    schema: 'radar.v2',
    is_context_only: true,
    as_of: '2026-10-14',
    generated_at: '2026-10-19T22:45:28.882285+00:00',
    lag_months: 3,
    coverage: {
      themes_covered: 48, divergences: 11, members_with_data: 403,
      max_sources: 9,
    },
    hypotheses: [],
    caveats: [],
    caveats_zh: [],
    flags: [flag()],
  };
}

function snapRow() {
  return {
    ticker: 'SNAP', state: 'NEGATIVE_DIVERGENCE', lifecycle: 'fading',
    edge_score: 54, signal_score: 39, rs_vs_spy_60d: 30.1,
    action: 'WATCH', conviction: 'medium', extended: false,
    channels: ['activist_13d', 'app_demand', 'lobbying'], affiliations: [],
    activity: -0.44, price: 3.76,
    flows: { present: true, lean: 1, accumulating: 2, distributing: 0 },
    options: { present: false },
    crowd: { penalty: 0.0, dark_pool_distribution: 0, retail_buzz: 0 },
    source: 'signal',
    note: 'SNAP has led (+30.1% vs SPY) but the alt-data signal is cooling ' +
      '(39/100) — price ahead of activity. · ETF accumulating',
  };
}

function ddogRow() {
  return {
    ticker: 'DDOG', state: 'NEGATIVE_DIVERGENCE', lifecycle: 'fading',
    edge_score: 23, signal_score: null, rs_vs_spy_60d: -2.54,
    within_basket_pct: 1.0, basket: 'non_ai_software',
    basket_name: 'Non-AI Software', basket_state: 'NEGATIVE_DIVERGENCE',
    source: 'basket_attributed', channels: [], affiliations: [],
    note: 'DDOG has led the Non-AI Software basket (100th pct) but the ' +
      "theme's activity is fading — distribution risk.",
  };
}

function tickersFixture(rows, n, nAttributed) {
  const f = { schema: 'radar_ticker.v1', as_of: '2026-10-19', n_divergences: 95 };
  if (n !== undefined) f.n = n;
  if (nAttributed !== undefined) f.n_attributed = nAttributed;
  f.tickers = rows;
  return f;
}

async function render(tickers) {
  return renderPanel({
    radar: radarFixture(), tickers: tickers,
    enriched: null, news: null, ic: null, track: null, brain: null,
  });
}

function tabButton(html) {
  const m = /<button class="rx-tab" data-pane="stocks">[\s\S]*?<\/button>/.exec(html);
  assert.ok(m, 'the Stocks tab button rendered');
  return m[0];
}

function rowList(rowsHtml) {
  return String(rowsHtml).split('<div class="rx-nrow">').slice(1);
}

function rowFor(rowsHtml, ticker) {
  const hit = rowList(rowsHtml).filter(function (r) {
    return r.startsWith('<a class="rx-tk" href="stock.html#' + ticker + '">' +
      ticker + '</a>');
  });
  assert.equal(hit.length, 1, 'exactly one rendered row for ' + ticker);
  return hit[0];
}

// Every added label/tip: [en, zh] twins that must be non-identical.
const ADDED_PAIRS = [
  ["Theme's read", '主题读数'],
  [' · 30 with a read of their own', ' · 其中 30 只个股有自身读数'],
  ['This name has no read of its own; it shows its theme\'s read.',
    '该股没有自身读数，显示的是所属主题的读数。'],
];
const BANNED = ['实时', '申报', '证伪', 'validated', '已验证', 'live', 'forecast',
  'falsifier'];

test('test_tab_label_qualifies_the_name_count', async () => {
  const { html } = await render(tickersFixture([snapRow(), ddogRow()], 215, 185));
  const tab = tabButton(html);
  assert.ok(tab.includes('(2)'), 'tab counts the real rows, not artifact n: ' + tab);
  assert.ok(tab.includes('30 with a read of their own'), 'qualifier shows 30');
  assert.ok(tab.includes('其中 30'), 'qualifier is bilingual');
  assert.ok(tab.includes('<span class="rx-mut">'), 'qualifier reuses rx-mut');
  assert.ok(!tab.includes('1 with a read'), '30 comes from the artifact counts, ' +
    'not a client-side recount of the two rows');
  assert.ok(!tab.includes('185'), 'n_attributed itself is never printed');
  assert.ok(!tab.includes('(215)'), 'the artifact n is never the tab count');
});

test('test_attributed_row_is_marked_and_signal_row_is_not', async () => {
  const { html, nodes } = await render(tickersFixture([snapRow(), ddogRow()], 215, 185));
  const rowsHtml = nodes['rx-nrows'];
  const ddog = rowFor(rowsHtml, 'DDOG');
  const snap = rowFor(rowsHtml, 'SNAP');
  assert.ok(ddog.includes('<span class="rx-badge rx-badge-sm rx-mut"'),
    'attributed row carries the muted marker badge');
  assert.ok(ddog.includes("Theme's read"), 'attributed row says Theme\'s read (EN)');
  assert.ok(ddog.includes('主题读数'), 'attributed row marker is bilingual');
  assert.ok(ddog.includes('data-tip-en="This name has no read of its own; ' +
    'it shows its theme\'s read."'), 'marker explains itself in EN on hover');
  assert.ok(!snap.includes("Theme's read"), 'the signal row is not marked');
  assert.ok(!snap.includes('rx-badge-sm rx-mut'), 'the signal row gets no marker span');
  const tab = tabButton(html);
  for (const s of [rowsHtml, tab]) {
    assert.ok(!s.includes('basket_attributed'), 'raw source slug never printed');
    assert.ok(!s.includes('signal"'), 'raw source slug never printed as a value');
  }
});

test('test_signal_score_is_not_re_exposed', async () => {
  const { nodes } = await render(tickersFixture([snapRow(), ddogRow()], 215, 185));
  const rowsHtml = nodes['rx-nrows'];
  for (const banned of ['39/100', 'signal_score', '(100th pct)']) {
    assert.ok(!rowsHtml.includes(banned), 'rows must not contain ' + banned);
  }
});

test('test_counts_fall_back_when_the_artifact_is_thin', async () => {
  const noCounts = await render(tickersFixture([snapRow(), ddogRow()]));
  const tab1 = tabButton(noCounts.html);
  assert.ok(tab1.includes('(2)'), 'plain length kept without n');
  assert.ok(!tab1.includes('rx-mut'), 'no qualifier when the artifact has no counts');
  const badCounts = await render(tickersFixture([snapRow(), ddogRow()], 2, 5));
  const tab2 = tabButton(badCounts.html);
  assert.ok(!tab2.includes('rx-mut'), 'no qualifier when n_attributed exceeds n');
  for (const out of [noCounts, badCounts]) {
    const corpus = out.html + String(out.nodes['rx-nrows']);
    assert.ok(!corpus.includes('NaN'), 'no NaN leaks');
    assert.ok(!corpus.includes('undefined'), 'no undefined leaks');
  }
});

test('test_row_set_is_unchanged', async () => {
  const two = await render(tickersFixture([snapRow(), ddogRow()], 215, 185));
  const r2 = rowList(two.nodes['rx-nrows']);
  assert.equal(r2.length, 2, 'both fixture rows painted');
  assert.ok(r2[0].startsWith('<a class="rx-tk" href="stock.html#SNAP">'),
    'SNAP first: |30.1| beats |-2.54| under the untouched |rs| sort');
  assert.ok(r2[1].startsWith('<a class="rx-tk" href="stock.html#DDOG">'),
    'DDOG second');
  const many = [];
  for (let i = 0; i < 30; i++) {
    const base = i % 2 ? ddogRow() : snapRow();
    base.ticker = 'T' + i;
    base.rs_vs_spy_60d = 60 - i;
    many.push(base);
  }
  const big = await render(tickersFixture(many, 215, 185));
  assert.equal(rowList(big.nodes['rx-nrows']).length, 24,
    'the 30-row fixture still paints exactly the _nameVisible=24 cap');
});

test('test_names_copy_is_bilingual_and_lexically_clean', async () => {
  const { html, nodes } = await render(tickersFixture([snapRow(), ddogRow()], 215, 185));
  const marker = /<span class="rx-badge rx-badge-sm rx-mut"([\s\S]*?)<\/span><\/span>/
    .exec(String(nodes['rx-nrows']));
  assert.ok(marker, 'marker badge present for the bilingual check');
  const qual = /<span class="rx-mut">([\s\S]*?)<\/span><\/span>/.exec(tabButton(html));
  assert.ok(qual, 'tab qualifier present for the bilingual check');
  const rendered = marker[0] + qual[0];
  for (const [en, zh] of ADDED_PAIRS.slice(0, 2)) {
    assert.notEqual(en, zh, 'added pair must not be identical text');
    assert.ok(rendered.includes('<span class="l-en">' + en + '</span>' +
      '<span class="l-zh">' + zh + '</span>'),
      'added label ships EN and zh twins through bi(): ' + en);
  }
  const tipEn = /data-tip-en="([^"]*)"/.exec(marker[0]);
  const tipZh = /data-tip-zh="([^"]*)"/.exec(marker[0]);
  assert.ok(tipEn && tipZh, 'marker carries a hover tip in both languages');
  assert.equal(tipEn[1], ADDED_PAIRS[2][0], 'tip EN is the quoted sentence');
  assert.equal(tipZh[1], ADDED_PAIRS[2][1], 'tip zh is its non-identical twin');
  for (const s of [marker[0], qual[0], ...ADDED_PAIRS.flat()]) {
    for (const w of BANNED) {
      assert.ok(!s.includes(w), 'banned word in added copy: ' + w);
    }
  }
});
