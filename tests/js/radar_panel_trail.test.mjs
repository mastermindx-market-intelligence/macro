/**
 * W23-L16 Spec 3 (W21A) — dated trail dots; stop calling 14 reads "14 days".
 *
 * Fixtures are inline committed-shaped copies of the seeded records: the
 * radar.json semicap_equipment flag (id 2026-10-14-semicap_equipment, state
 * POSITIVE_DIVERGENCE, lifecycle emerging, divergence/salience 2.152,
 * observable accel 1.907 / dir 1 / z 0.962, covered AEIS…UCTT) and the
 * radar_enriched.json 15-entry state_strip (09-23 … 10-19, 10-09/10-14
 * QUIET). No site/ or data/ reads at test time; stdlib only; no network.
 * Surfaces: the board trail lives in nodes['rx-tbody'] (painted by
 * paintThemes); the card trail row and the board header <th> live in html
 * (mount.innerHTML).
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { renderPanel } from './radar_panel_harness.mjs';

const PD = 'POSITIVE_DIVERGENCE';

function semicapFlag() {
  return {
    id: '2026-10-14-semicap_equipment',
    basket: 'semicap_equipment',
    name: 'Semiconductor Equipment (WFE)',
    name_zh: '半导体设备（晶圆厂设备）',
    category: 'Semiconductors',
    state: PD,
    lifecycle: 'emerging',
    divergence: 2.152,
    salience: 2.152,
    observable: {
      accel: 1.907,
      dir: 1,
      z: 0.962,
      covered: ['AEIS', 'AMAT', 'ENTG', 'KLAC', 'KLIC', 'LRCX', 'MKSI', 'UCTT'],
    },
  };
}

function committedStrip() {
  return [
    { d: '09-23', s: PD }, { d: '09-25', s: PD }, { d: '09-26', s: PD },
    { d: '09-27', s: PD }, { d: '10-01', s: PD }, { d: '10-03', s: PD },
    { d: '10-04', s: PD }, { d: '10-05', s: PD }, { d: '10-06', s: PD },
    { d: '10-07', s: PD }, { d: '10-09', s: 'QUIET' }, { d: '10-14', s: 'QUIET' },
    { d: '10-16', s: PD }, { d: '10-17', s: PD }, { d: '10-19', s: PD },
  ];
}

async function renderWith(strip) {
  return renderPanel({
    radar: { as_of: '2026-10-19', flags: [semicapFlag()] },
    enriched: { flags: [{ basket: 'semicap_equipment', state_strip: strip }] },
  });
}

// Board surface: the one <tr> in #rx-tbody that carries the trail span.
function boardRow(nodes) {
  const tbody = nodes['rx-tbody'] || '';
  const rows = tbody.split('<tr>').filter((r) => r.includes('rx-trail'));
  assert.equal(rows.length, 1, 'exactly one board trail row painted');
  return rows[0];
}

// Card surface: every "What's behind this" row in mount.innerHTML with a trail.
function cardTrailRows(html) {
  const re = /<div class="rx-more-row"><span class="rx-more-k">[\s\S]*?<\/span><\/div>/g;
  const rows = (html.match(re) || []).filter((t) => t.includes('rx-trail'));
  assert.ok(rows.length >= 1, 'at least one card trail row rendered');
  return rows;
}

function allText(html, nodes) {
  return html + Object.keys(nodes).map((k) => nodes[k]).join('');
}

test('test_each_trail_dot_carries_its_recorded_date', async () => {
  const { html, nodes } = await renderWith(committedStrip());
  const row = boardRow(nodes);
  const dots = row.match(/<i /g) || [];
  assert.equal(dots.length, 14, 'the board row keeps exactly 14 dots (slice(-14))');
  assert.ok(/data-tip-en="10-16 · /.test(row), 'board dot 10-16 carries its date as a tip');
  assert.ok(/data-tip-en="09-25 · /.test(row), 'board dot 09-25 carries its date as a tip');
  assert.ok(/data-tip-zh="10-16 · /.test(row), 'board dot 10-16 has a zh tip too');
  assert.ok(!allText(html, nodes).includes('09-23'),
    'the sliced-off 15th entry (09-23) appears nowhere');
});

test('test_trail_label_does_not_claim_consecutive_days', async () => {
  const { html, nodes } = await renderWith(committedStrip());
  const all = allText(html, nodes);
  assert.ok(!all.includes('Last 14 days'), 'no "Last 14 days" on either surface or the header');
  assert.ok(!all.includes('过去14天'), 'no 过去14天 anywhere');
  assert.ok(!all.includes('The read on each of the last 14 days.'), 'old header tip is gone');
  for (const row of cardTrailRows(html)) {
    assert.ok(row.includes('09-25 to 10-19'), 'the card label prints the real span');
    assert.ok(row.includes('09-25 至 10-19'), 'the zh card label prints the real span');
  }
  assert.ok(html.includes('Recent reads'), 'the header shows the new label');
});

test('test_span_is_computed_not_hardcoded', async () => {
  const strip = [
    { d: '07-20', s: PD }, { d: '08-01', s: PD }, { d: '08-04', s: PD },
    { d: '08-07', s: PD }, { d: '08-10', s: PD }, { d: '08-13', s: PD },
    { d: '08-16', s: PD }, { d: '08-19', s: PD }, { d: '08-22', s: PD },
    { d: '08-25', s: PD }, { d: '08-28', s: PD }, { d: '08-31', s: PD },
    { d: '09-03', s: PD }, { d: '10-17', s: PD }, { d: '10-19', s: PD },
  ];
  const { html, nodes } = await renderWith(strip);
  const row = boardRow(nodes);
  assert.ok(/data-tip-en="08-01 · /.test(row), 'first kept dot is 08-01 of this fixture');
  for (const card of cardTrailRows(html)) {
    assert.ok(card.includes('08-01 to 10-19'), 'the span comes from this strip, not a constant');
    assert.ok(card.includes('最近 14 次解读 · 08-01 至 10-19'), 'zh span too');
  }
  assert.ok(!allText(html, nodes).includes('09-25'),
    'the committed-strip span 09-25 must not survive into a different fixture');
});

test('test_short_strip_counts_its_own_reads', async () => {
  const two = await renderWith([{ d: '10-17', s: PD }, { d: '10-19', s: PD }]);
  assert.equal((boardRow(two.nodes).match(/<i /g) || []).length, 2, 'two dots');
  for (const card of cardTrailRows(two.html)) {
    assert.ok(card.includes('Last 2 reads · 10-17 to 10-19'), 'two reads are counted, not 14');
    assert.ok(card.includes('最近 2 次解读 · 10-17 至 10-19'), 'zh twin');
  }
  const one = await renderWith([{ d: '10-19', s: PD }]);
  for (const card of cardTrailRows(one.html)) {
    assert.ok(card.includes('<span class="l-en">Last 1 read</span>'),
      'one entry reads "Last 1 read" with no date span');
    assert.ok(card.includes('最近 1 次解读'), 'zh twin');
    assert.ok(!card.includes(' to '), 'no span claimed for a single read');
  }
  assert.ok(!allText(two.html, two.nodes).includes('NaN'), 'no NaN (2-entry)');
  assert.ok(!allText(two.html, two.nodes).includes('undefined'), 'no undefined (2-entry)');
  assert.ok(!allText(one.html, one.nodes).includes('NaN'), 'no NaN (1-entry)');
  assert.ok(!allText(one.html, one.nodes).includes('undefined'), 'no undefined (1-entry)');
});

test('test_trail_copy_is_bilingual', async () => {
  const { html, nodes } = await renderWith(committedStrip());
  const banned = ['实时', '申报', '证伪', 'validated', '已验证', 'forecast', 'falsifier'];
  const row = boardRow(nodes);
  const dotRe =
    /<i style="background:[^"]*" data-tip-en="([^"]*)" data-tip-zh="([^"]*)"><\/i>/g;
  const dots = row.match(dotRe) || [];
  assert.equal(dots.length, 14, 'every board dot carries a paired en/zh tip');
  let m;
  while ((m = dotRe.exec(row)) !== null) {
    assert.ok(m[1] && m[2], 'tip pair is non-empty on both sides');
    assert.notEqual(m[1], m[2], 'en and zh dot tips differ');
    const both = m[1] + m[2];
    for (const w of banned) assert.ok(!both.includes(w), 'no banned word in dot tips');
  }
  assert.ok(!/data-tip(?:-en|-zh)="[^"]*\blive\b/.test(row), 'no "live" in dot tips');
  for (const card of cardTrailRows(html)) {
    const en = /<span class="l-en">([^<]*)<\/span>/.exec(card);
    const zh = /<span class="l-zh">([^<]*)<\/span>/.exec(card);
    assert.ok(en && zh && en[1] && zh[1], 'card label ships .l-en and .l-zh');
    assert.notEqual(en[1], zh[1], 'card label zh is a real twin, not the en text');
    for (const w of banned) {
      assert.ok(!(en[1] + zh[1]).includes(w), 'no banned word in labels');
    }
  }
  const thRe = /<th data-tip-en="([^"]*)" data-tip-zh="([^"]*)">([\s\S]*?)<\/th>/;
  const th = thRe.exec(html);
  assert.ok(th && th[0].includes('Recent reads'), 'header ships the new en label');
  assert.ok(th[1] && th[2] && th[1] !== th[2], 'header tip pair differs by language');
  const thZh = /<span class="l-zh">([^<]*)<\/span>/.exec(th[0]);
  assert.ok(thZh && thZh[1] === '近期解读', 'header ships a real zh twin');
  for (const w of banned.concat(['live'])) {
    assert.ok(!(th[0]).includes(w), 'no banned word in the header');
  }
});
