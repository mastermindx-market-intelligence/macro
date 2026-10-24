/**
 * W23-L8 Spec 1 — settled theses in the Divergence Radar honesty check.
 *
 * Fixtures are committed-shaped copies of the seeded records:
 * radar_track_record.json (as_of 2026-10-17; scored_total 114; open 263;
 * overall hits 53 / misses 61; recent industrial_distribution miss,
 * us_sector_financials hit, defensives miss) and radar_ic.json (n_snapshots
 * 18675; 21d episodes n_matured 3288, claims n 1485 dir 0.53 bar 0.525).
 * Rendered through tests/js/radar_panel_harness.mjs — stdlib only, no
 * network, no site/ or data/ reads at test time.
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

function trackFixture() {
  return {
    schema: 'ai_desk_track_record.v1',
    as_of: '2026-10-17',
    scored_total: 114,
    open: 263,
    overall: {
      n: 114, hits: 53, misses: 61, hit_rate: 0.465, dir_accuracy: 0.281,
    },
    recent: [
      {
        id: '2026-07-17-radar-industrial_distribution',
        subject: 'industrial_distribution', lean: 'positive_divergence',
        conviction: null, outcome: 'miss', realized: -0.0867,
        check_by: '2026-10-16',
      },
      {
        id: '2026-07-17-radar-us_sector_financials',
        subject: 'us_sector_financials', lean: 'positive_divergence',
        conviction: null, outcome: 'hit', realized: -0.0391,
        check_by: '2026-10-16',
      },
      {
        id: '2026-07-06-radar-defensives',
        subject: 'defensives', lean: 'positive_divergence',
        conviction: null, outcome: 'miss', realized: -0.0776,
        check_by: '2026-10-05',
      },
    ],
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
      covered: ['AIT', 'FAST', 'FERG', 'GWW', 'KMT', 'MSM'],
      sources: [
        {
          name: 'congress_netbuy', label_en: 'Congress net-buy',
          label_zh: '国会净买入', accel: null, z: -0.193, weight: 0.6,
          n_covered: 12,
        },
        {
          name: 'lobbying_ramp', label_en: 'Lobbying ramp',
          label_zh: '游说支出', accel: 0.25, z: 3.5, weight: 0.7,
          n_covered: 3,
        },
      ],
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
    flags: [
      flag('industrial_distribution', 'Industrial Distribution & Capital Goods',
        '工业分销与资本品', 0.937),
      flag('us_sector_financials', 'Financials (Equal-Weight)',
        '金融（等权）', -0.11),
      flag('defensives', 'Defensives', '防御板块', -0.499),
    ],
  };
}

function base() {
  return {
    ic: icFixture(), track: trackFixture(), radar: radarFixture(),
    brain: null, enriched: null, news: null, tickers: null,
  };
}

function tiles(s) {
  const out = [];
  const re = /<div class="rx-tile"><div class="rx-tile-v">([^<]*)<\/div>/g;
  let m;
  while ((m = re.exec(s))) out.push({ value: m[1] });
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

function paraSpans(para) {
  const re = new RegExp('<span class="l-en">([\\s\\S]*?)<\\/span>'
    + '<span class="l-zh">([\\s\\S]*?)<\\/span>');
  const m = para.match(re);
  assert.ok(m, 'paragraph has EN and ZH spans');
  return { en: m[1], zh: m[2] };
}

function spanPairs(s) {
  const out = [];
  const re = /<span class="l-en">([^<]*)<\/span><span class="l-zh">([^<]*)<\/span>/g;
  let m;
  while ((m = re.exec(s))) out.push({ en: m[1], zh: m[2] });
  return out;
}

function splitPara(s, needle) {
  const re = /<p class="rx-h-split">[\s\S]*?<\/p>/g;
  let m;
  while ((m = re.exec(s))) {
    if (m[0].includes(needle)) return m[0];
  }
  return '';
}

test('test_settled_thesis_count_renders_from_a_committed_shaped_record', async () => {
  const s = await renderHonesty(base());
  assert.ok(s.includes('<div class="rx-tile-v">114</div>' +
    '<div class="rx-tile-l"><span class="l-en">3-month theses settled' +
    '</span><span class="l-zh">3个月论点已到期'), 'settled tile renders');
  assert.ok(s.includes('53 held'), 'hits count phrased as held');
  assert.ok(s.includes('61 did not hold'), 'misses count phrased as not held');
  assert.ok(s.includes('<div class="rx-tile-v">263</div>'), 'open tile intact');
  assert.ok(s.includes('not proof the call was right'), 'low-bar clause present');
});

test('test_settled_rows_name_their_subject_and_check_date', async () => {
  const s = await renderHonesty(base());
  const r = receiptSpans(s);
  assert.ok(r.en.includes('2026-10-16'), 'check date 16th in EN');
  assert.ok(r.en.includes('2026-10-05'), 'check date 5th in EN');
  assert.ok(r.en.includes('did not hold'), 'plain-words outcome in EN');
  assert.ok(r.en.includes('Industrial Distribution'), 'flag name (EN)');
  assert.ok(r.en.includes('Financials (Equal-Weight)'), 'EN name 2');
  assert.ok(r.en.includes('Defensives'), 'EN name 3');
  assert.ok(r.zh.includes('工业分销与资本品'), 'flag name (ZH) 1');
  assert.ok(r.zh.includes('金融（等权）'), 'flag name (ZH) 2');
  assert.ok(r.zh.includes('防御板块'), 'flag name (ZH) 3');
  assert.ok(!/\bmiss(es)?\b/i.test(s), 'no raw miss word in section');
  assert.ok(!/\bhits?\b/i.test(s), 'no raw hit word in section');
  const para = splitPara(s, 'have settled');
  assert.ok(para.length > 0, 'settled sentence present');
  assert.ok(!para.includes('%'), 'no percentage in the settled sentence');
});

test('test_settled_rows_fall_back_to_the_slug_only_inside_the_receipt', async () => {
  const fx = base();
  fx.track.recent[0] = {
    ...fx.track.recent[0], subject: 'payments_fintech',
    id: '2026-07-17-radar-payments_fintech',
  };
  const s = await renderHonesty(fx);
  assert.ok(s.includes('payments_fintech'), 'slug printed');
  const outside = s.replace(/<details class="rx-receipt"[\s\S]*?<\/details>/, '');
  assert.ok(!outside.includes('payments_fintech'), 'slug only inside receipt');
  const r = receiptPart(s);
  assert.ok(r.includes('payments_fintech'), 'slug inside receipt');
});

test('test_ledger_as_of_is_dated', async () => {
  const s = await renderHonesty(base());
  const spans = paraSpans(splitPara(s, 'have settled'));
  assert.ok(spans.en.includes('as of 2026-10-17'), 'EN sentence dated');
  assert.ok(spans.zh.includes('截至 2026-10-17'), 'ZH sentence dated');
  const rs = receiptSpans(s);
  assert.ok(rs.en.includes('ledger as of 2026-10-17'), 'EN receipt dated');
  assert.ok(rs.zh.includes('记录截至 2026-10-17'), 'ZH receipt dated');
  const fx = base();
  delete fx.track.as_of;
  const s2 = await renderHonesty(fx);
  assert.ok(splitPara(s2, 'have settled').length > 0, 'sentence still renders');
  assert.ok(!s2.includes('as of ,'), 'no bare as-of comma');
  assert.ok(!s2.includes('as of —'), 'no bare as-of dash');
  assert.ok(!s2.includes('截至 ，'), 'no bare ZH as-of');
});

test('test_absent_ledger_renders_no_zero_tile', async () => {
  const s = await renderHonesty({ ...base(), track: { open: 263 } });
  assert.ok(!s.includes('3-month theses settled'), 'no settled tile');
  assert.ok(!s.includes('have settled'), 'no settled sentence');
  assert.ok(!s.includes('NaN'), 'no NaN');
  assert.ok(!s.includes('undefined'), 'no undefined');
  assert.ok(!s.includes('>0<'), 'no zero tile value');
  assert.ok(s.includes('<div class="rx-tile-v">263</div>'), 'open tile still renders');
});

test('test_new_copy_is_bilingual_and_lexically_clean', async () => {
  const s = await renderHonesty(base());
  const pairs = spanPairs(s);
  for (const needle of ['have settled', 'Most recently settled',
    '3-month theses settled']) {
    const pair = pairs.find((p) => p.en.includes(needle));
    assert.ok(pair, 'EN copy present for ' + needle);
    assert.ok(pair.zh !== pair.en, 'ZH twin differs for ' + needle);
    assert.ok(/[\u4e00-\u9fff]/.test(pair.zh), 'ZH twin is Chinese');
  }
  for (const banned of ['申报', '实时', 'falsifier', 'refuted', 'z-score',
    'percentile rank', '证伪', 'validated', '已验证', 'forecast']) {
    assert.ok(!s.includes(banned), 'section avoids ' + banned);
  }
});
