/**
 * W35-LA — Divergence Radar: what would break each logged read.
 *
 * Fixtures are inline committed-shaped copies of site/basketdata/radar.json
 * (schema radar.v2, as_of 2026-10-20, 48 flags, 10 hypotheses): the defense/ITA,
 * memory_storage/SMH and ai_infra/SMH rows, each carrying its pre-set
 * falsifier.check (kind rel_return, vs SPY, op "<", threshold -0.05, horizon_d
 * 63), check_by 2027-01-19 and logged_at 2026-10-22T07:09:34, plus the flags
 * that name those baskets ("Defense & Aerospace" / 国防与航空航天, "Memory, HBM &
 * Storage" / 内存、HBM 与存储, "AI Infrastructure" / AI 基础设施). Rendered through
 * tests/js/radar_panel_harness.mjs — stdlib only, no network, no site/ or data/
 * reads at test time. The section lives in mount.innerHTML (html), between the
 * honesty check and the AI read.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { renderPanel } from './radar_panel_harness.mjs';

const PD = 'POSITIVE_DIVERGENCE';
const OMIT = 'OMIT';
const THREE = ['defense', 'memory_storage', 'ai_infra'];

// Theme names quoted from the committed radar.json flags at as_of 2026-10-20.
const NAMES = {
  defense: ['Defense & Aerospace', '国防与航空航天'],
  power_grid: ['Power & Grid Buildout', '电力与电网'],
  memory_storage: ['Memory, HBM & Storage', '内存、HBM 与存储'],
  semicap_equipment: ['Semiconductor Equipment (WFE)', '半导体设备（晶圆厂设备）'],
  quantum_computing: ['Quantum Computing', '量子计算'],
  reshoring: ['Reshoring & Industrial Capex', '回流与工业资本开支'],
  us_sector_financials: ['Financials (Equal-Weight)', '金融（等权）'],
  us_sector_realestate: ['Real Estate (Equal-Weight)', '房地产（等权）'],
  ai_infra: ['AI Infrastructure', 'AI 基础设施'],
  us_sector_discretionary: ['Consumer Discretionary (Equal-Weight)', '非必需消费（等权）'],
};

// The ten logged subjects and their ETF proxies, in artifact order.
const COMMITTED = [
  ['defense', 'ITA'], ['power_grid', 'XLU'], ['memory_storage', 'SMH'],
  ['semicap_equipment', 'SMH'], ['quantum_computing', 'QTUM'], ['reshoring', 'XLI'],
  ['us_sector_financials', 'XLF'], ['us_sector_realestate', 'XLRE'],
  ['ai_infra', 'SMH'], ['us_sector_discretionary', 'XLY'],
];

function flag(basket) {
  const pair = NAMES[basket] || [basket, basket];
  return {
    id: '2026-10-20-' + basket,
    basket,
    name: pair[0],
    name_zh: pair[1],
    category: 'Semiconductors',
    state: PD,
    lifecycle: 'emerging',
    divergence: 2.152,
    salience: 2.152,
    observable: {
      accel: 1.907, dir: 1, z: 0.962, covered: ['AEIS', 'AMAT', 'LRCX', 'UCTT'],
    },
  };
}

function hyp(subject, ticker, over) {
  const row = {
    id: '2026-10-20-radar-' + subject,
    subject,
    subject_ticker: ticker,
    lean: 'positive_divergence',
    horizon_d: 63,
    thesis: 'Real activity (federal contracts, federal grants/loans, gov contracts ' +
      '(quiver)) on LMT, NOC, LHX is accelerating (~1.4× YoY) while the theme\'s ' +
      '60-day relative strength sits at -20%. Activity ahead of price — watch.',
    falsifier: {
      text: ticker + ' under-performs SPY by more than 5% over ~3 months — real ' +
        'activity did not lead price.',
      check: {
        kind: 'rel_return', subject_ticker: ticker, vs: 'SPY', op: '<',
        threshold: -0.05, horizon_d: 63,
      },
    },
    check_by: '2027-01-19',
    logged_at: '2026-10-22T07:09:34.466711+00:00',
  };
  return Object.assign(row, over || {});
}

async function render(hypotheses, flags, extra) {
  const radar = {
    schema: 'radar.v2',
    is_context_only: true,
    as_of: '2026-10-20',
    lag_months: 3,
    coverage: { themes_covered: 48, divergences: 11 },
    caveats: [],
    caveats_zh: [],
    flags: flags ? flags.map(flag) : THREE.map(flag),
  };
  if (hypotheses !== OMIT) radar.hypotheses = hypotheses;
  const { radarOver, ...rest } = extra || {};
  Object.assign(radar, radarOver || {});
  return renderPanel(Object.assign({ radar }, rest));
}

function section(html) {
  const start = html.indexOf('<section class="rx-checks"');
  assert.ok(start >= 0, 'the open-checks section rendered into the mount');
  const end = html.indexOf('</section>', start);
  assert.ok(end > start, 'the open-checks section is closed');
  return html.slice(start, end + '</section>'.length);
}

function rows(sec) {
  return sec.split('<div class="rx-ck-row">').slice(1);
}

function collect(sec, head) {
  const re = new RegExp(head + '<span class="l-en">([\\s\\S]*?)</span>' +
    '<span class="l-zh">([\\s\\S]*?)</span>', 'g');
  const out = [];
  let m;
  while ((m = re.exec(sec)) !== null) out.push({ en: m[1], zh: m[2] });
  return out;
}

const conds = (sec) => collect(sec, '<span class="rx-ck-cond">');
const spanPairs = (sec) => collect(sec, '');
const notes = (sec) => sec.match(/<p class="rx-ck-note">[\s\S]*?<\/p>/g) || [];

test('test_checks_section_lists_each_logged_thesis', async () => {
  const { html } = await render(THREE.map((b, i) => hyp(b, i ? 'SMH' : 'ITA')));
  const sec = section(html);
  assert.equal(rows(sec).length, 3, 'one row per logged thesis');
  for (const b of THREE) {
    assert.ok(sec.includes(NAMES[b][0].replace('&', '&amp;')), 'EN theme name: ' + b);
    assert.ok(sec.includes(NAMES[b][1]), 'zh theme name: ' + b);
  }
  assert.ok(sec.includes('basket/defense.html'), 'a known theme links to its page');
  assert.ok(sec.includes('stock.html#ITA'), 'the proxy ticker links to the terminal');
  assert.ok(sec.includes('check by'), 'the check-by label ships EN');
  assert.ok(sec.includes('核对日'), 'the check-by label ships zh');
  assert.ok(sec.includes('2027-01-19'), 'the fixed check date is printed');
  assert.ok(sec.includes('3 theses'), 'the intro counts the rows it printed');

  const page = (await render([hyp('defense', 'ITA')], null,
    { brain: { assessments: [] } })).html;
  const at = {
    honesty: page.indexOf('id="rx-honesty"'),
    checks: page.indexOf('id="rx-checks"'),
    brain: page.indexOf('class="rx-brain'),
    foot: page.indexOf('class="rx-foot"'),
  };
  for (const k of Object.keys(at)) assert.ok(at[k] >= 0, 'the page carries ' + k);
  assert.ok(at.honesty < at.checks, 'the checks follow the honesty section');
  assert.ok(at.checks < at.brain, 'the checks precede the AI read');
  assert.ok(at.brain < at.foot, 'the AI read precedes the footer');
});

test('test_break_condition_reads_from_the_check', async () => {
  const trails = hyp('defense', 'ITA');
  const shorter = hyp('memory_storage', 'SMH');
  shorter.falsifier.check = {
    kind: 'rel_return', vs: 'QQQ', op: '<', threshold: -0.08, horizon_d: 42,
  };
  const beats = hyp('ai_infra', 'SMH');
  beats.falsifier.check = {
    kind: 'rel_return', vs: 'SPY', op: '>', threshold: 0.05, horizon_d: 63,
  };
  const sec = section((await render([trails, shorter, beats])).html);
  const got = conds(sec);
  assert.equal(got.length, 3, 'every row carries one condition');
  assert.equal(got[0].en, 'breaks if it trails SPY by more than 5% from its log date ' +
    'to its check date (about 3 months)');
  assert.equal(got[0].zh, '若从记录日到核对日（约 3 个月）累计落后 SPY 超过 5%，则不成立');
  assert.equal(got[1].en, 'breaks if it trails QQQ by more than 8% from its log date ' +
    'to its check date (about 2 months)', 'the condition reads the check, not a constant');
  assert.equal(got[1].zh, '若从记录日到核对日（约 2 个月）累计落后 QQQ 超过 8%，则不成立');
  assert.equal(got[2].en, 'breaks if it beats SPY by more than 5% from its log date ' +
    'to its check date (about 3 months)', 'op ">" reads as beats');
  assert.equal(got[2].zh, '若从记录日到核对日（约 3 个月）累计跑赢 SPY 超过 5%，则不成立');
});

test('test_unscorable_or_odd_checks_degrade_plainly', async () => {
  const noCheck = hyp('defense', 'ITA');
  delete noCheck.falsifier;
  const otherKind = hyp('memory_storage', 'SMH');
  otherKind.falsifier = { text: 'SMH level check', check: { kind: 'level', vs: 'SPY' } };
  const oddSign = hyp('ai_infra', 'SMH');
  oddSign.falsifier.check = {
    kind: 'rel_return', vs: 'SPY', op: '<', threshold: 0.05, horizon_d: 63,
  };
  const oddOp = hyp('defense', 'ITA');
  oddOp.falsifier.check = {
    kind: 'rel_return', vs: 'SPY', op: '>', threshold: -0.05, horizon_d: 63,
  };
  const sec = section((await render([noCheck, otherKind, oddSign, oddOp])).html);
  const got = conds(sec);
  assert.equal(got.length, 4, 'every row still carries a condition');
  assert.ok(got[3].en.startsWith('graded on its return against SPY'), got[3].en);
  assert.equal(got[0].en, 'no machine check — logged, not graded');
  assert.equal(got[0].zh, '无机械核对 —— 仅记录，不评分');
  assert.equal(got[1].en, 'no machine check — logged, not graded');
  assert.equal(got[2].en, 'graded on its return against SPY from its log date to its ' +
    'check date (about 3 months)');
  assert.equal(got[2].zh, '按从记录日到核对日（约 3 个月）相对 SPY 的累计收益评分');
  for (const bad of ['NaN', 'undefined', '-5%', 'Infinity']) {
    assert.ok(!sec.includes(bad), 'the section never prints ' + bad);
  }
});

test('test_shared_proxy_is_named_once', async () => {
  const sec = section((await render(THREE.map((b, i) => hyp(b, i ? 'SMH' : 'ITA')))).html);
  const pair = notes(sec);
  assert.equal(pair.length, 1, 'one note for the one shared proxy');
  assert.ok(pair[0].includes('SMH stands in for 2'), 'the note names the proxy and count');
  assert.ok(pair[0].includes('SMH 同时代表其中 2 个主题'), 'the note ships a zh twin');
  assert.ok(!pair[0].includes('ITA'), 'a proxy only one row uses gets no note');

  const sec10 = section((await render(COMMITTED.map((p) => hyp(p[0], p[1])),
    COMMITTED.map((p) => p[0]))).html);
  assert.equal(rows(sec10).length, 10, 'the committed record renders ten rows');
  assert.equal(notes(sec10).length, 1, 'only SMH is shared in the committed record');
  assert.equal((sec10.match(/3 of these themes/g) || []).length, 1,
    'SMH is named as standing in for three themes, once');
});

// A shared ticker proves one price, not one date or one condition.
test('test_shared_proxy_note_claims_only_the_shared_price', async () => {
  const later = hyp('ai_infra', 'SMH', { check_by: '2027-03-01' });
  later.falsifier.check = {
    kind: 'rel_return', vs: 'QQQ', op: '<', threshold: -0.08, horizon_d: 42,
  };
  const sec = section((await render([hyp('memory_storage', 'SMH'), later])).html);
  const pair = notes(sec);
  assert.equal(pair.length, 1, 'two rows on one proxy still get the note');
  const [got] = collect(pair[0], '');
  assert.equal(got.en, 'SMH stands in for 2 of these themes, so those checks read the ' +
    'same price — not 2 independent tests.');
  assert.equal(got.zh, 'SMH 同时代表其中 2 个主题，这些核对依据同一价格 —— ' +
    '并非 2 次相互独立的检验。');
  for (const bad of ['settle', '结算', 'one test', '一次检验']) {
    assert.ok(!sec.includes(bad), 'the section never claims ' + bad);
  }
});

test('test_shared_proxy_note_counts_only_graded_rows', async () => {
  const soft = hyp('ai_infra', 'SMH');
  soft.falsifier.check = { kind: 'soft', reason: 'no ETF proxy to score' };
  const one = section((await render([hyp('memory_storage', 'SMH'), soft])).html);
  assert.equal(notes(one).length, 0, 'one graded row and one soft row share nothing to read');
  const three = section((await render([hyp('memory_storage', 'SMH'),
    hyp('semicap_equipment', 'SMH'), soft])).html);
  assert.ok(notes(three)[0].includes('SMH stands in for 2 of these themes'),
    'the soft row is not counted: ' + notes(three)[0]);
});

test('test_engine_prose_is_not_printed', async () => {
  const sec = section((await render([hyp('defense', 'ITA')])).html);
  assert.ok(!sec.includes('quiver'), 'the engine thesis names a vendor; the page does not');
  assert.ok(!sec.includes('is accelerating'), 'no thesis prose');
  assert.ok(!sec.includes('under-performs SPY'), 'no falsifier prose');
  assert.ok(!sec.includes('positive_divergence'), 'no lean enum');
  assert.ok(!sec.includes('2026-10-20-radar-'), 'no hypothesis id');
  assert.ok(!sec.includes('2026-10-22T07:09:34'), 'no logged_at stamp');
  assert.ok(!sec.includes('rel_return'), 'no raw check kind');
  assert.ok(!sec.includes('&lt;'), 'no raw check op');
});

test('test_section_is_absent_without_theses', async () => {
  const cases = [
    ['missing', OMIT],
    ['empty', []],
    ['a string', 'x'],
    ['null', null],
    ['rows without a subject', [{ subject_ticker: 'ITA' }, { subject: '' }]],
  ];
  for (const [label, value] of cases) {
    const { html } = await render(value);
    assert.ok(!html.includes('rx-checks'), 'no section when hypotheses are ' + label);
    assert.ok(html.includes('id="rx-honesty"'), 'the page still renders for ' + label);
  }
});

test('test_unknown_theme_is_readable_and_unlinked', async () => {
  const sec = section((await render([hyp('us_sector_new', 'XYZ')])).html);
  assert.ok(sec.includes('us sector new'), 'an unknown subject prints a readable name');
  assert.ok(!sec.includes('basket/us_sector_new.html'), 'and carries no theme link');
  assert.ok(sec.includes('<span class="rx-ck-theme">'), 'the theme cell is a plain span');
});

test('test_checks_copy_is_bilingual_and_lexically_clean', async () => {
  const sec = section((await render(COMMITTED.map((p) => hyp(p[0], p[1])),
    COMMITTED.map((p) => p[0]))).html);
  const pairs = spanPairs(sec);
  const nEn = (sec.match(/<span class="l-en">/g) || []).length;
  assert.equal(pairs.length, nEn, 'every EN span ships a zh twin');
  assert.ok(pairs.length >= 10, 'the section is fully bilingual: ' + pairs.length);
  for (const p of pairs) {
    assert.ok(p.en.length > 0 && p.zh.length > 0, 'neither side is empty: ' + p.en);
    assert.notEqual(p.en, p.zh, 'the zh twin is not the EN text: ' + p.en);
  }
  const banned = ['实时', '申报', '证伪', 'validated', '已验证', 'live', 'forecast',
    'falsifier', 'refuted', 'z-score', 'percentile', 'buy', 'sell'];
  for (const w of banned) assert.ok(!sec.includes(w), 'the section avoids ' + w);
});

test('test_check_by_prints_the_date_alone', async () => {
  const sec = section((await render([hyp('defense', 'ITA',
    { check_by: '2027-01-19T07:09:34+00:00' })])).html);
  assert.ok(sec.includes('2027-01-19'), 'the date part is printed');
  assert.ok(!sec.includes('T07:09'), 'the clock part never reaches the page');
});

// The record is dated by as_of, so nothing here may say the theses are today's.
test('test_section_never_calls_a_dated_record_today', async () => {
  const dated = section((await render([hyp('defense', 'ITA')])).html);
  const [lead] = collect(dated, '<p class="rx-h-para">');
  assert.ok(lead.en.startsWith('The radar record dated 2026-10-20 holds 1 thesis. '), lead.en);
  assert.ok(lead.zh.startsWith('日期为 2026-10-20 的雷达记录包含 1 条论点。'), lead.zh);
  const [head] = collect(dated, '<h2 class="rx-h-title">');
  assert.equal(head.en, 'Logged theses and their checks');
  assert.equal(head.zh, '已记录的论点及其核对条件');

  const undated = section((await render([hyp('defense', 'ITA')], null,
    { radarOver: { as_of: null } })).html);
  const [bare] = collect(undated, '<p class="rx-h-para">');
  assert.ok(bare.en.startsWith('The radar record holds 1 thesis. '), bare.en);
  assert.ok(bare.zh.startsWith('雷达记录包含 1 条论点。'), bare.zh);
  for (const sec of [dated, undated]) {
    for (const bad of ['Today', 'today', '今日', '今天']) {
      assert.ok(!sec.includes(bad), 'the section never says ' + bad);
    }
  }
});

// The grader reads one close on the log date and one on the check date.
test('test_condition_copy_is_endpoint_only', async () => {
  const beats = hyp('ai_infra', 'SMH');
  beats.falsifier.check = {
    kind: 'rel_return', vs: 'SPY', op: '>', threshold: 0.05, horizon_d: 63,
  };
  const odd = hyp('memory_storage', 'SMH');
  odd.falsifier.check = {
    kind: 'rel_return', vs: 'SPY', op: '<', threshold: 0.05, horizon_d: 63,
  };
  const sec = section((await render([hyp('defense', 'ITA'), beats, odd])).html);
  for (const got of conds(sec)) {
    assert.ok(!got.zh.includes('内'), 'no zh condition reads as path-dependent: ' + got.zh);
    assert.ok(got.zh.includes('累计'), 'every zh condition is cumulative: ' + got.zh);
    assert.ok(got.en.includes('from its log date to its check date'), got.en);
    assert.ok(!/session|交易日/.test(got.en + got.zh), 'no session count: ' + got.en);
  }
  const [lead] = collect(sec, '<p class="rx-h-para">');
  assert.ok(lead.en.includes('it holds if that condition is not met on that date'), lead.en);
  assert.ok(lead.zh.includes('当日条件未满足即视为成立'), lead.zh);
  assert.ok(!lead.en.includes('triggered') && !lead.zh.includes('届时'),
    'the lead does not read as a watch over the window');
});

// A grader reads a rel_return check at check_by and never reads horizon_d.
test('test_graded_row_needs_a_date_not_a_horizon', async () => {
  const noHorizon = hyp('defense', 'ITA');
  delete noHorizon.horizon_d;
  delete noHorizon.falsifier.check.horizon_d;
  const [kept] = conds(section((await render([noHorizon])).html));
  assert.equal(kept.en, 'breaks if it trails SPY by more than 5% from its log date to its ' +
    'check date');
  assert.equal(kept.zh, '若从记录日到核对日累计落后 SPY 超过 5%，则不成立');

  const noDate = hyp('defense', 'ITA', { check_by: null });
  const sec = section((await render([noDate])).html);
  const [dropped] = conds(sec);
  assert.equal(dropped.en, 'no machine check — logged, not graded');
  assert.ok(!sec.includes('rx-ck-when'), 'an undated row prints no date');
});

test('test_intro_counts_only_the_checked_rows', async () => {
  const soft = (b) => {
    const row = hyp(b, null);
    row.falsifier = { text: 'x', check: { kind: 'soft', reason: 'no ETF proxy to score' } };
    return row;
  };
  const leadOf = (sec) => collect(sec, '<p class="rx-h-para">')[0];

  const all = section((await render([hyp('defense', 'ITA'), hyp('ai_infra', 'SMH')])).html);
  assert.ok(leadOf(all).en.includes('holds 2 theses. Each is checked on a fixed date '),
    leadOf(all).en);
  assert.ok(leadOf(all).zh.includes('2 条论点。每条在固定日期'), leadOf(all).zh);

  const lone = section((await render([hyp('defense', 'ITA')])).html);
  assert.ok(leadOf(lone).en.includes('holds 1 thesis. It is checked on a fixed date '),
    leadOf(lone).en);

  const mixed = section((await render([hyp('defense', 'ITA'), hyp('ai_infra', 'SMH'),
    soft('robotics_automation')])).html);
  assert.ok(leadOf(mixed).en.includes('holds 3 theses. 2 of them are checked on a fixed date '),
    leadOf(mixed).en);
  assert.ok(leadOf(mixed).en.endsWith('not proof. The rest are logged, not graded.'),
    leadOf(mixed).en);
  assert.ok(leadOf(mixed).zh.includes('其中 2 条在固定日期'), leadOf(mixed).zh);
  assert.ok(leadOf(mixed).zh.endsWith('并非证明。其余仅记录，不评分。'), leadOf(mixed).zh);
  assert.equal((mixed.match(/rx-ck-when/g) || []).length, 2, 'a soft row prints no check date');

  const single = section((await render([hyp('defense', 'ITA'),
    soft('robotics_automation')])).html);
  assert.ok(leadOf(single).en.includes('1 of them is checked on a fixed date '),
    leadOf(single).en);

  const none = section((await render([soft('robotics_automation')])).html);
  assert.ok(leadOf(none).en.endsWith('holds 1 thesis. No machine check applies: logged, ' +
    'not graded.'), leadOf(none).en);
  assert.ok(leadOf(none).zh.endsWith('1 条论点。无机械核对：仅记录，不评分。'), leadOf(none).zh);
  assert.ok(!none.includes('rx-ck-when'), 'no row prints a check date');
  assert.ok(!none.includes('fixed date') && !none.includes('固定日期'),
    'the intro promises no date when no row has one');
  assert.ok(!none.includes('a low bar'), 'the intro explains no bar when no row has one');
});

test('test_horizon_falls_back_to_the_thesis_row', async () => {
  const row = hyp('defense', 'ITA');
  delete row.falsifier.check.horizon_d;
  const [got] = conds(section((await render([row])).html));
  assert.equal(got.en, 'breaks if it trails SPY by more than 5% from its log date to its ' +
    'check date (about 3 months)');
});

test('test_one_month_reads_singular', async () => {
  const row = hyp('defense', 'ITA');
  row.falsifier.check.horizon_d = 21;
  const [got] = conds(section((await render([row])).html));
  assert.ok(got.en.endsWith('to its check date (about 1 month)'), got.en);
});

test('test_holding_is_called_a_low_bar', async () => {
  const sec = section((await render([hyp('defense', 'ITA')])).html);
  assert.ok(sec.includes('a low bar, not proof'), 'EN states what holding means');
  assert.ok(sec.includes('门槛很低，并非证明'), 'zh states what holding means');
});

// bi() and esc() both escape, so a value passed through bi() must not also go
// through esc(): "&" would then reach the reader as a literal "&amp;".
test('test_artifact_values_are_escaped_exactly_once', async () => {
  const row = hyp('defense', 'A&<x>');
  row.falsifier.check.vs = 'B&<y>';
  const twin = hyp('no_<z>_flag', 'a&<x>');
  twin.falsifier.check.vs = 'B&<y>';
  const sec = section((await render([row, twin])).html);
  for (const tag of ['<x>', '<y>', '<z>']) assert.ok(!sec.includes(tag), 'no raw ' + tag);
  assert.ok(!sec.includes('&amp;amp;') && !sec.includes('&amp;lt;'), 'nothing escaped twice');
  const [got] = conds(sec);
  assert.ok(got.en.includes('trails B&amp;&lt;y&gt; by'), got.en);
  assert.ok(got.zh.includes('落后 B&amp;&lt;y&gt; 超过'), got.zh);
  assert.ok(sec.includes('no &lt;z&gt; flag'), 'an unknown theme name is escaped');
  assert.ok(sec.includes('A&amp;&lt;X&gt; stands in for 2'), 'the shared-proxy note is escaped');
});
