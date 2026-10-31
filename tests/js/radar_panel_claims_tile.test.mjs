/**
 * W23-L8 Spec 2 — the calls tile reports the graded claims cohort, not every
 * matured episode, in the Divergence Radar honesty check.
 *
 * Fixtures are committed-shaped copies of radar_ic.json (21d episodes:
 * n_matured 3288; claims n 1485, dir_accuracy 0.53, base_dart 0.525;
 * diagonal 1481/0.446; h21 diagonal 7532/0.448) and radar_track_record.json
 * (open 263). Rendered through tests/js/radar_panel_harness.mjs — stdlib
 * only, no network, no site/ or data/ reads at test time.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { renderHonesty } from './radar_panel_harness.mjs';

function icFixture() {
  return {
    as_of: '2026-10-14',
    n_snapshots: 18675,
    n_matured: 16280,
    ic_all: -0.0271,
    ic_all_signed: -0.0465,
    verdict: { status: 'null', gates: { min_claim_episodes: 60, t_sig: 2.0 } },
    base_rate: { p_up: 0.416 },
    era_breaks: [{ era: 2, date: '2026-08-05' }],
    by_horizon: {
      21: {
        episodes: {
          n_matured: 3288,
          claims: { n: 1485, dir_accuracy: 0.53, base_dart: 0.525 },
          diagonal: { n: 1481, dir_accuracy: 0.446 },
          base_rate: { n: 3288, p_up: 0.396 },
        },
        diagonal: { n: 7532, dir_accuracy: 0.448 },
        ic_daily_hac_claims: { t_hac: 0.291, n: 65 },
      },
    },
  };
}

function flag(basket, name, nameZh, divergence) {
  return {
    id: '2026-10-14-' + basket,
    basket,
    name,
    name_zh: nameZh,
    category: 'Mixed',
    state: 'QUIET',
    lifecycle: 'quiet',
    divergence,
    salience: Math.abs(divergence),
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
      covered: ['AIT', 'FAST', 'GWW', 'POOL', 'URI', 'WCC'],
      sources: [
        {
          name: 'congress_netbuy', label_en: 'Congress net-buy',
          label_zh: '国会净买入', accel: null, z: -0.193, weight: 0.6,
          n_covered: 12,
        },
      ],
    },
  };
}

function base() {
  return {
    ic: icFixture(),
    track: {
      schema: 'ai_desk_track_record.v1',
      as_of: '2026-10-17',
      scored_total: 114,
      open: 263,
      overall: {
        n: 114, hits: 53, misses: 61, hit_rate: 0.465, dir_accuracy: 0.281,
      },
      recent: [],
    },
    radar: {
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
      flags: [
        flag('industrial_distribution', 'Industrial Distribution & Capital Goods',
          '工业分销与资本品', 0.937),
        flag('us_sector_financials', 'Financials (Equal-Weight)',
          '金融（等权）', -0.11),
        flag('defensives', 'Defensives', '防御板块', -0.499),
      ],
    },
    brain: null,
    enriched: null,
    news: null,
    tickers: null,
  };
}

function tiles(s) {
  const out = [];
  const re = /<div class="rx-tile"><div class="rx-tile-v">([^<]*)<\/div>/g;
  let m;
  while ((m = re.exec(s))) out.push({ value: m[1] });
  return out;
}

function tilesWithLabels(s) {
  const out = [];
  const re = new RegExp('<div class="rx-tile"><div class="rx-tile-v">([^<]*)<\\/div>'
    + '<div class="rx-tile-l"><span class="l-en">([^<]*)<\\/span>', 'g');
  let m;
  while ((m = re.exec(s))) out.push({ value: m[1], en: m[2] });
  return out;
}

function receiptPart(s) {
  const start = s.indexOf('<details class="rx-receipt"');
  const end = s.indexOf('</details>', start);
  assert.ok(start >= 0 && end > start, 'receipt details present');
  return s.slice(start, end);
}

function receiptSpans(s) {
  const re = new RegExp('<p><span class="l-en">([\\s\\S]*?)<\\/span>'
    + '<span class="l-zh">([\\s\\S]*?)<\\/span>');
  const m = receiptPart(s).match(re);
  assert.ok(m, 'receipt paragraph has EN and ZH spans');
  return { en: m[1], zh: m[2] };
}

function splitPara(s, needle) {
  const re = /<p class="rx-h-split">[\s\S]*?<\/p>/g;
  let m;
  while ((m = re.exec(s))) {
    if (m[0].includes(needle)) return m[0];
  }
  return '';
}

test('test_calls_tile_reports_the_claims_cohort_not_every_episode', async () => {
  const s = await renderHonesty(base());
  const tile = tilesWithLabels(s).find((t) => t.en === 'Independent calls graded');
  assert.ok(tile, 'calls tile present');
  assert.equal(tile.value, '1,485', 'tile shows the claims cohort, not episodes');
  assert.ok(!s.replace(/<details class="rx-receipt"[\s\S]*?<\/details>/, '')
    .includes('3,288'), '3,288 confined to the receipt');
  const spans = receiptSpans(s);
  assert.ok(spans.en.includes('3,288'), '3,288 in EN receipt');
  assert.ok(spans.zh.includes('3,288'), '3,288 in ZH receipt');
});

test('test_receipt_keeps_both_counts_but_stops_equating_them_with_calls', async () => {
  const s = await renderHonesty(base());
  const r = receiptSpans(s);
  assert.ok(r.en.includes('3,288'), 'episode count kept in EN');
  assert.ok(r.en.includes('1,485'), 'claims count kept in EN');
  assert.ok(r.en.includes('matured at 21d'), 'horizon wording kept');
  assert.ok(r.en.includes('16,280'), 'raw daily rows kept in EN');
  assert.ok(r.zh.includes('3,288'), 'episode count kept in ZH');
  assert.ok(r.zh.includes('1,485'), 'claims count kept in ZH');
  assert.ok(r.zh.includes('16,280'), 'raw daily rows kept in ZH');
  assert.ok(!r.en.includes('Independent calls ='), 'EN stops equating');
  assert.ok(!r.zh.includes('独立解读＝'), 'ZH stops equating');
});

test('test_tile_and_split_line_now_agree', async () => {
  const s = await renderHonesty(base());
  const tile = tilesWithLabels(s).find((t) => t.en === 'Independent calls graded');
  assert.equal(tile.value, icFixture().by_horizon[21].episodes.claims.n
    .toLocaleString(), 'tile equals claims.n');
  const para = splitPara(s, 'Split honestly');
  assert.ok(para.includes('right 53% of the time'), 'accuracy sentence renders');
  assert.ok(para.includes('against a 53% bar'), 'base_dart bar renders');
});

test('test_small_claims_cohort_does_not_blank_the_tile', async () => {
  const fx = base();
  fx.ic.by_horizon[21].episodes.claims = {
    n: 0, dir_accuracy: 0.53, base_dart: 0.525,
  };
  const s = await renderHonesty(fx);
  const tile = tilesWithLabels(s).find((t) => t.en === 'Independent calls graded');
  assert.ok(tile, 'zero cohort still renders a tile');
  assert.equal(tile.value, '0', 'tile shows 0, never NaN or blank');
  assert.ok(!s.includes('NaN'), 'no NaN');
  assert.ok(!/<div class="rx-tile-v"><\/div>/.test(s), 'no empty tile value');
  const fx2 = base();
  delete fx2.ic.by_horizon[21].episodes.claims;
  const s2 = await renderHonesty(fx2);
  assert.ok(!tilesWithLabels(s2).some((t) => t.en === 'Independent calls graded'),
    'absent claims omits the tile');
  assert.ok(!s2.includes('NaN') && !s2.includes('undefined'), 'no sentinels');
  assert.ok(tiles(s2).some((t) => t.value === '18,675') &&
    tiles(s2).some((t) => t.value === '263'), 'other tiles unaffected');
});
