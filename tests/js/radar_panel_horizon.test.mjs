/**
 * W23-L17 Spec 4 (W21A) — the Divergence Radar honesty check reads the radar's
 * own promise horizon out of the committed artifact instead of showing only the
 * 21-day split line.
 *
 * Fixtures are committed-shaped copies of radar_ic.json (seed_horizon_cal_d 91;
 * horizons [21, 63, 91]; 21d episodes n_matured 3288, claims n 1485 /
 * dir_accuracy 0.53 / base_dart 0.525; 63d 1871 / n 934 / 0.539 / 0.534;
 * 91d 1033 / n 513 / 0.522 / 0.529) and radar_track_record.json (open 263,
 * scored 114). Rendered through tests/js/radar_panel_harness.mjs — stdlib only,
 * no network, no site/ or data/ reads at test time.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { renderHonesty } from './radar_panel_harness.mjs';

const EN_91 = "Measured at the horizon the radar's theses are written for (91 calendar days), "
  + 'the divergence calls were right 52% of the time against a 53% bar — below it — across '
  + '513 graded calls from 1,033 matured episodes. A descriptive read at that horizon, '
  + 'not the headline grade.';

const ZH_91 = '按雷达论点所针对的期限（91 个日历日）衡量，背离判断方向正确率 52%'
  + '（基准 53%）—— 低于基准 —— 共 513 条已评分判断，来自 1,033 个已到期片段。'
  + '这是该期限下的描述性读数，并非标题处的评级。';

const BANNED = ['实时', '申报', '证伪', 'validated', '已验证', 'live',
  'forecast', 'falsifier', 'verdict', 'significant', 'proved'];

function icFixture() {
  return {
    as_of: '2026-10-14',
    schema: 'radar_ic.v2',
    n_snapshots: 18675,
    n_matured: 16280,
    ic_all: -0.0271,
    ic_all_signed: -0.0465,
    horizon_d: 21,
    horizons: [21, 63, 91],
    seed_horizon_cal_d: 91,
    verdict: {
      status: 'null',
      basis: { horizon: 21, t_hac: 0.291, n_days: 65, n_claim_episodes: 1485 },
      gates: { min_claim_episodes: 60, t_sig: 2.0 },
    },
    base_rate: { n: 16280, p_up: 0.416 },
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
      63: {
        episodes: {
          n_matured: 1871,
          claims: { n: 934, dir_accuracy: 0.539, base_dart: 0.534 },
          diagonal: { n: 861, dir_accuracy: 0.496 },
        },
      },
      91: {
        episodes: {
          n_matured: 1033,
          claims: { n: 513, dir_accuracy: 0.522, base_dart: 0.529 },
          diagonal: { n: 497, dir_accuracy: 0.479 },
        },
        ic_daily_hac_claims: { t_hac: -0.201, n: 23 },
      },
    },
  };
}

function flag() {
  return {
    basket: 'semicap_equipment',
    name: 'Semiconductor Equipment (WFE)',
    name_zh: '半导体设备（晶圆厂设备）',
    state: 'POSITIVE_DIVERGENCE',
    salience: 2.152,
    observable: { accel: 1.907 },
    consensus: {},
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
      lag_months: 3,
      hypotheses: [],
      caveats: [],
      caveats_zh: [],
      flags: [flag()],
    },
    brain: null,
    enriched: null,
    news: null,
    tickers: null,
  };
}

function splitParas(s) {
  const re = /<p class="rx-h-split">[\s\S]*?<\/p>/g;
  const out = [];
  let m;
  while ((m = re.exec(s))) out.push(m[0]);
  return out;
}

function paraWith(s, needle) {
  return splitParas(s).find((p) => p.includes(needle)) || '';
}

function legs(p) {
  const m = p.match(/<span class="l-en">([\s\S]*?)<\/span><span class="l-zh">([\s\S]*?)<\/span>/);
  assert.ok(m, 'paragraph carries an EN and a ZH span');
  return { en: m[1], zh: m[2] };
}

function h2Of(s) {
  const m = s.match(/<h2 class="rx-h-title">([\s\S]*?)<\/h2>/);
  assert.ok(m, 'headline h2 renders');
  return m[1];
}

test('test_promise_horizon_block_renders_from_a_committed_shaped_record', async () => {
  const s = await renderHonesty(base());
  const para = paraWith(s, 'calendar days');
  assert.ok(para, 'the promise-horizon paragraph renders');
  assert.ok(para.includes('91 calendar days'), 'the horizon comes from the record');
  const copy = legs(para);
  assert.equal(copy.en, EN_91, 'EN copy is the committed promise-horizon read');
  assert.ok(copy.en.includes('52%'), 'the 91-day accuracy renders');
  assert.ok(copy.en.includes('53% bar'), 'the accuracy keeps its own bar');
  assert.ok(copy.en.includes('513'), 'the graded-call count renders');
  assert.ok(copy.en.includes('1,033'), 'the matured-episode count renders');
  assert.ok(copy.en.includes('below it'), 'the comparator names the sign');
  const twentyOne = splitParas(s).filter((p) => p.includes('were right 53% of the time'));
  assert.equal(twentyOne.length, 1, 'the 21-day split line survives as its own paragraph');
  assert.ok(twentyOne[0].includes('Split honestly'), 'the 21-day line is the split line');
  assert.notEqual(twentyOne[0], para, 'the two horizons are two separate paragraphs');
});

test('test_horizon_is_resolved_from_the_artifact_not_hardcoded', async () => {
  const fx = base();
  fx.ic.seed_horizon_cal_d = 63;
  const s = await renderHonesty(fx);
  const para = paraWith(s, 'calendar days');
  assert.ok(para, 'the promise-horizon paragraph renders at 63');
  assert.ok(para.includes('63 calendar days'), 'the resolved horizon is 63, not 91');
  const copy = legs(para);
  assert.ok(copy.en.includes('right 54% of the time'), '63d accuracy renders');
  assert.ok(copy.en.includes('against a 53% bar'), '63d bar renders');
  assert.ok(copy.en.includes('above it'), 'the comparator follows the sign');
  assert.ok(copy.en.includes('934'), '63d graded-call count renders');
  assert.ok(copy.en.includes('1,871'), '63d matured-episode count renders');
  assert.ok(!s.includes('513'), 'the 91-day cohort is not printed');
});

test('test_horizon_falls_back_through_the_horizon_list', async () => {
  const fx = base();
  delete fx.ic.seed_horizon_cal_d;
  const s = await renderHonesty(fx);
  const para = paraWith(s, 'calendar days');
  assert.ok(para, 'the horizon list carries the fallback');
  assert.ok(para.includes('91 calendar days'), 'the longest horizon is used');
  assert.ok(legs(para).en.includes('513'), 'the 91-day cohort renders via the fallback');
  const fx2 = base();
  delete fx2.ic.seed_horizon_cal_d;
  delete fx2.ic.horizons;
  const s2 = await renderHonesty(fx2);
  assert.equal(paraWith(s2, 'calendar days'), '', 'no horizon info, no new paragraph');
});

test('test_promise_read_is_not_presented_as_a_verdict', async () => {
  const withBlock = await renderHonesty(base());
  const fx = base();
  delete fx.ic.by_horizon[63];
  delete fx.ic.by_horizon[91];
  const without = await renderHonesty(fx);
  assert.equal(h2Of(withBlock), h2Of(without), 'the headline grade is unchanged');
  assert.equal(legs(paraWith(withBlock, 'calendar days')).en, EN_91);
  const copy = legs(paraWith(withBlock, 'calendar days'));
  for (const word of ['verdict', 'significant', 'proved', 'validated']) {
    assert.ok(!copy.en.includes(word), 'EN avoids ' + word);
    assert.ok(!copy.zh.includes(word), 'ZH avoids ' + word);
  }
  assert.ok(copy.en.includes('not the headline grade'), 'EN labels itself descriptive');
  assert.ok(copy.zh.includes('并非标题处的评级'), 'ZH labels itself descriptive');
});

test('test_missing_or_thin_horizon_block_renders_nothing_new', async () => {
  const fx = base();
  delete fx.ic.by_horizon[63];
  delete fx.ic.by_horizon[91];
  const s21 = await renderHonesty(fx);
  const baseline = await renderHonesty((() => {
    const b = base();
    delete b.ic.seed_horizon_cal_d;
    delete b.ic.horizons;
    return b;
  })());
  assert.equal(splitParas(s21).length, splitParas(baseline).length,
    'a 21-only record adds no paragraph');
  assert.equal(paraWith(s21, 'calendar days'), '', 'nothing new at the promise horizon');
  const thin = base();
  thin.ic.by_horizon[91].episodes.claims.n = 29;
  const sThin = await renderHonesty(thin);
  assert.equal(paraWith(sThin, 'calendar days'), '', 'a 29-call cohort renders nothing new');
  assert.equal(splitParas(sThin).length, splitParas(baseline).length,
    'the thin cohort adds no paragraph');
  for (const s of [s21, sThin]) {
    assert.ok(!s.includes('NaN'), 'no NaN');
    assert.ok(!s.includes('undefined'), 'no undefined');
  }
});

test('test_promise_copy_is_bilingual', async () => {
  const s = await renderHonesty(base());
  const para = paraWith(s, 'calendar days');
  assert.ok(para, 'the promise-horizon paragraph renders');
  const copy = legs(para);
  assert.ok(copy.zh !== copy.en, 'the ZH twin is not the EN text');
  assert.equal(copy.zh, ZH_91, 'ZH copy is the committed promise-horizon read');
  assert.ok(copy.zh.includes('个日历日'), 'ZH states the horizon unit');
  assert.ok(copy.zh.includes('低于基准'), 'ZH states the comparator');
  assert.ok(/[\u4e00-\u9fff]/.test(copy.zh), 'ZH twin is Chinese');
  for (const banned of BANNED) {
    assert.ok(!copy.en.includes(banned), 'EN avoids ' + banned);
    assert.ok(!copy.zh.includes(banned), 'ZH avoids ' + banned);
  }
});
