'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const api = require('../templates/catalyst_research_assessment.js');
const fixtureDir = path.join(__dirname, '../research/catalyst_intelligence/decision_desk_r1/fixtures/stock_assessment_r8');
const names = ['delayed_reconstruction', 'history_missing'];
const fixtures = Object.fromEntries(names.map(name => [name, JSON.parse(fs.readFileSync(path.join(fixtureDir, name + '.assessment.json'), 'utf8'))]));
const fresh = (name = names[0]) => structuredClone(fixtures[name]);
const words = view => JSON.stringify(view);
const rejects = change => { const packet = fresh(); change(packet); assert.throws(() => api.validateAssessment(packet), /RESEARCH_PACKET_UNAVAILABLE/); };
function freeze(value) {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}

// A deliberately small DOM double: browser layout and actual DOM semantics are
// checked separately by the retained Playwright proof, not claimed by this test.
class Element {
  constructor(tag, doc) { this.tagName = tag.toUpperCase(); this.ownerDocument = doc; this.children = []; this._text = ''; this.className = ''; }
  get classList() {
    const node = this, current = () => new Set(node.className.split(/\s+/).filter(Boolean));
    return {
      contains(value) { return current().has(value); },
      add(value) { const set = current(); set.add(value); node.className = [...set].join(' '); },
      remove(value) { const set = current(); set.delete(value); node.className = [...set].join(' '); }
    };
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join('\n'); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this._text = ''; this.children = nodes; }
  set innerHTML(_) { throw new Error('HTML injection must not be used'); }
}
function root() {
  const document = {createElement(tag) { return new Element(tag, document); }};
  return document.createElement('div');
}
function tags(node) { return [node.tagName, ...node.children.flatMap(tags)]; }

test('retained owner bodies and original capture receipt have exact pinned bytes', () => {
  const expected = {
    'delayed_reconstruction.assessment.json': 'c4799c41792553d19234b9bdd978b27170f11b9e804c1927a36e4f041de651fb',
    'history_missing.assessment.json': '39defcc38d635182c05c1bac28a05ffc357f0f70614fb370aa124572fc7b52b2',
    'capture-receipt.json': '7c059aec43adf4514659d8571dcb43ba9e407441a093188c4c2c5c0d275f70e8'
  };
  for (const [file, digest] of Object.entries(expected)) assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(fixtureDir, file))).digest('hex'), digest);
  const receipt = JSON.parse(fs.readFileSync(path.join(fixtureDir, 'capture-receipt.json'), 'utf8'));
  for (const capture of receipt.captures) {
    assert.equal(fixtures[capture.case].assessment_id, capture.assessment_id);
    assert.equal(expected[capture.case + '.assessment.json'], capture.stdout_sha256);
  }
});

test('both exact v3 captures validate and present without modifying any input', () => {
  for (const name of names) {
    const packet = freeze(fresh(name)), before = JSON.stringify(packet);
    assert.equal(api.validateAssessment(packet), packet);
    assert.equal(api.presentation(packet, 'en').sections.length, 4);
    assert.equal(api.presentation(packet, 'zh').sections.length, 4);
    assert.equal(JSON.stringify(packet), before);
  }
});

test('missing history preserves current company evidence and never becomes no change', () => {
  const compared = words(api.presentation(fresh(), 'en'));
  const missing = words(api.presentation(fresh('history_missing'), 'en'));
  assert.match(compared, /Source correction recorded/);
  assert.match(missing, /Comparison is unavailable; missing evidence does not mean no change/);
  assert.match(missing, /issuer restated remaining authorization/);
  assert.doesNotMatch(missing, /Source correction recorded/);
  for (const text of [compared, missing]) assert.doesNotMatch(text, /source_correction_reduces_magnitude|150b|numeric reduction/i);
});

test('unrequested comparison differs from missing history and retains current news', () => {
  const packet = fresh();
  packet.news_context.comparison = {state: 'NOT_REQUESTED', reason_code: 'COMPARISON_NOT_REQUESTED',
    information_cutoff_at: null, prior_views: null, pairs: null,
    source_envelopes: {current: packet.news_context.current.source_envelope, prior: null}};
  const text = words(api.presentation(packet, 'en'));
  assert.match(text, /Comparison was not requested/);
  assert.match(text, /issuer restated remaining authorization/);
  assert.doesNotMatch(text, /Comparison is unavailable/);
});

test('source correction is an owner indicator, not an invented magnitude or economic conclusion', () => {
  const packet = fresh();
  packet.news_context.current.views[0].weakening_conditions = [
    {code: 'source_correction_reduces_magnitude', armed: true, fabricated_numeric_reduction: 99}
  ];
  const text = words(api.presentation(packet, 'en'));
  assert.match(text, /Source correction recorded/);
  assert.doesNotMatch(text, /fabricated_numeric_reduction|reduces_magnitude|99/);
  packet.news_context.comparison.pairs[0].material_delta_triggers = [];
  const empty = words(api.presentation(packet, 'en'));
  assert.match(empty, /Empty indicators do not prove no economic change/);
  assert.doesNotMatch(empty, /Source correction recorded/);
});

test('observed returns retain cohort, coverage and percentage-point qualifications', () => {
  const text = words(api.presentation(fresh(), 'en'));
  assert.match(text, /Supplied research cohort; coverage is not the whole subtheme/);
  assert.match(text, /3 of 3 eligible issuers observed/);
  assert.match(text, /\+11 percentage points/);
  assert.match(text, /2 advancing · 1 declining · 0 unchanged/);
  assert.match(text, /Returns do not establish causality or a predictive edge/);
});

test('valid partial and absent peer coverage do not become complete-cohort evidence', () => {
  const partial = fresh(), pc = partial.peer_context.context;
  pc.state = 'PARTIAL'; pc.coverage.eligible_peer_issuers = 4; pc.coverage.fraction = 0.75;
  pc.statistics.complete_cohort_equal_weight_return_pct = null;
  assert.match(words(api.presentation(partial, 'en')), /3 of 4 eligible issuers observed/);
  const absent = fresh();
  absent.peer_context = {state: 'UNAVAILABLE', context: null, reason_code: 'PEER_INPUT_NOT_SUPPLIED'};
  const text = words(api.presentation(absent, 'en'));
  assert.match(text, /A peer cohort was not supplied/);
  assert.doesNotMatch(text, /\+11 percentage points/);
});

test('zero observations and missing focal price remain explicit unavailable values', () => {
  const zero = fresh(), pc = zero.peer_context.context;
  pc.state = 'NO_OBSERVED_PEERS'; pc.observed_peers = []; pc.coverage.observed_peer_issuers = 0; pc.coverage.fraction = 0;
  for (const key of ['observed_subset_equal_weight_return_pct', 'complete_cohort_equal_weight_return_pct',
    'focal_minus_observed_peers_pp', 'observed_subset_median_return_pct', 'observed_subset_dispersion_pp']) pc.statistics[key] = null;
  for (const key of ['advancing', 'declining', 'unchanged', 'effective_observed_issuer_count']) pc.statistics[key] = 0;
  assert.match(words(api.presentation(zero, 'en')), /0 of 3 eligible issuers observed/);
  const missing = fresh(), mp = missing.peer_context.context;
  mp.state = 'FOCAL_PRICE_UNAVAILABLE'; mp.focal_observation = null;
  mp.statistics.focal_minus_observed_peers_pp = null; mp.statistics.complete_cohort_equal_weight_return_pct = null;
  assert.equal(api.validateAssessment(missing), missing);
});

test('no owner input does not erase other supplied facets or imply entry availability', () => {
  const packet = fresh();
  packet.entry_context.state = 'OWNER_INPUT_UNAVAILABLE';
  packet.entry_context.owner_projection = null; packet.entry_context.source_envelope = null;
  packet.news_context.current = {state: 'UNAVAILABLE', reason_code: 'NEWS_INPUT_NOT_SUPPLIED',
    information_cutoff_at: packet.information_cutoff_at, views: null, source_envelope: null};
  packet.news_context.comparison = {state: 'NOT_REQUESTED', reason_code: 'COMPARISON_NOT_REQUESTED',
    information_cutoff_at: null, prior_views: null, pairs: null, source_envelopes: {current: null, prior: null}};
  const text = words(api.presentation(packet, 'en'));
  assert.match(text, /Current owner evidence was not supplied/);
  assert.match(text, /\+11 percentage points/);
  assert.doesNotMatch(text, /RAN_DONT_CHASE/);
});

test('even an owner ENTRY_OPEN state remains research-only and supplies no action', () => {
  const packet = fresh(), output = root();
  packet.entry_context.owner_projection.state = 'ENTRY_OPEN';
  packet.entry_context.owner_projection.entry_open = true;
  packet.entry_context.owner_projection.blockers = [];
  const component = api.mount(output, {assessment: packet});
  assert.match(output.textContent, /Research control and shadow only; this is not current entry availability/);
  assert.equal(tags(output).some(tag => ['BUTTON', 'A', 'FORM', 'INPUT'].includes(tag)), false);
  component.destroy();
});

test('all top and peer authority elevations, rights claims and qualified numeric estimates fail closed', () => {
  for (const scope of ['authority', 'peer_context']) {
    for (const key of Object.keys(fresh().authority)) rejects(p => { (scope === 'authority' ? p.authority : p.peer_context.context.authority)[key] = true; });
  }
  rejects(p => { p.source_admission_established = true; });
  rejects(p => { p.decision_availability_established = true; });
  rejects(p => { p.peer_context.context.source_admission_established = true; });
  rejects(p => { p.entry_context.decision_availability_established = true; });
  rejects(p => { p.qualification = 'LIVE'; });
  rejects(p => { p.owner_state_qualification = 'ADMITTED'; });
  rejects(p => { p.entry_context.strategy_authority_tier = 'LIVE'; });
  for (const key of Object.keys(fresh().advanced_estimates)) {
    rejects(p => { p.advanced_estimates[key].value = 0.7; });
    rejects(p => { p.advanced_estimates[key].state = 'QUALIFIED'; });
  }
});

test('owner news cannot acquire Prophet authority or cross company identity', () => {
  for (const key of Object.keys(fresh().news_context.current.views[0].prophet_flags)) {
    rejects(p => { p.news_context.current.views[0].prophet_flags[key] = true; });
  }
  rejects(p => { p.news_context.current.views[0].authority = 'decision'; });
  rejects(p => { p.news_context.current.views[0].company_id = 'other'; });
  rejects(p => { p.news_context.comparison.prior_views[0].company_id = 'other'; });
});

test('peer and entry identity mismatches cannot be presented as the focal company', () => {
  for (const field of ['company_id', 'security_id', 'identity_epoch', 'identity_source_ref']) {
    rejects(p => { p.peer_context.context.focal[field] = 'different'; });
  }
  rejects(p => { p.entry_context.owner_projection.security_id = 'different'; });
  rejects(p => { p.entry_context.owner_projection.identity_epoch = 'different'; });
  rejects(p => { p.peer_context.context.focal_observation.company_id = 'different'; });
});

test('impossible coverage, duplicate issuers and contradictory breadth fail closed', () => {
  rejects(p => { p.peer_context.context.coverage.fraction = 0.5; });
  rejects(p => { p.peer_context.context.coverage.observed_peer_issuers = 2; });
  rejects(p => { p.peer_context.context.observed_peers[1] = p.peer_context.context.observed_peers[0]; });
  rejects(p => { p.peer_context.context.observed_peers[0].company_id = p.focal.company_id; });
  rejects(p => { p.peer_context.context.statistics.advancing = 3; });
  rejects(p => { p.peer_context.context.state = 'PARTIAL'; });
  rejects(p => { p.peer_context.context.interpretation_limits = []; });
});

test('comparison must cover the exact current/prior proposition union with truthful presence', () => {
  rejects(p => { p.news_context.comparison.pairs = []; });
  rejects(p => { p.news_context.comparison.pairs.push(structuredClone(p.news_context.comparison.pairs[0])); });
  rejects(p => { p.news_context.comparison.pairs[0].presence = 'PRIOR_ONLY'; });
  rejects(p => { p.news_context.comparison.pairs[0].view_key.company_id = 'other'; });
  rejects(p => { p.news_context.current.views.push(structuredClone(p.news_context.current.views[0])); });
  rejects(p => { p.news_context.comparison.source_envelopes.current.source_revision = 'different'; });
});

test('source-envelope ordering rejects sub-millisecond inversions instead of rounding them away', () => {
  rejects(p => {
    const e = p.entry_context.source_envelope;
    e.materialized_at = '2026-09-28T20:00:13.000002Z';
    e.received_at = '2026-09-28T20:00:13.000001Z';
  });
  const packet = fresh(), e = packet.entry_context.source_envelope;
  e.materialized_at = '2026-09-28T20:00:13.000001Z';
  e.received_at = '2026-09-28T20:00:13.000002Z';
  assert.equal(api.validateAssessment(packet), packet);
});

test('invalid dates, ambiguous offsets, unsupported precision and future observations are refused', () => {
  for (const value of ['2026-02-30T20:00:08Z', '2026-09-28T24:00:08Z', '2026-09-28T20:00:60Z',
    '0000-09-28T20:00:08Z', '2026-09-28T20:00:08+00:00', '2026-09-28T20:00:08.0000001Z']) {
    rejects(p => { p.composed_at = value; });
  }
  rejects(p => { p.peer_context.context.observed_peers[0].known_at = '2026-09-28T20:00:08.000001Z'; });
  rejects(p => { p.entry_context.owner_projection.evaluated_at = '2026-09-28T20:00:08.000001Z'; });
  rejects(p => { p.news_context.current.views[0].decision_cut = '2026-09-28T20:00:07Z'; });
  rejects(p => { p.news_context.comparison.information_cutoff_at = p.information_cutoff_at; });
});

test('unsupported schemas, non-JSON values, cycles and non-finite data fail closed', () => {
  rejects(p => { p.schema = 'catalyst.stock_research_assessment.v4'; });
  rejects(p => { p.peer_context.context.statistics.advancing = NaN; });
  rejects(p => { p.entry_context.owner_projection.current_price = Infinity; });
  rejects(p => { p.extra = undefined; });
  rejects(p => { p.extra = new Date(); });
  rejects(p => { p.extra = p; });
  for (const packet of [null, [], 'packet', 1]) assert.throws(() => api.validateAssessment(packet), /RESEARCH_PACKET_UNAVAILABLE/);
});

test('owner text and source identifiers render literally without markup or executable navigation', () => {
  const packet = fresh(), output = root(), marker = '<img src=x onerror="globalThis.compromised=true">';
  packet.news_context.current.views[0].display.plain_status = marker;
  packet.focal.identity_source_ref = 'javascript:alert(1)';
  packet.peer_context.context.focal.identity_source_ref = packet.focal.identity_source_ref;
  api.mount(output, {assessment: packet});
  assert.match(output.textContent, /<img src=x onerror=/);
  assert.match(output.textContent, /javascript:alert\(1\)/);
  assert.equal(tags(output).some(tag => ['IMG', 'SCRIPT', 'IFRAME', 'A'].includes(tag)), false);
  assert.equal(globalThis.compromised, undefined);
});

test('invalid replacement clears prior content immediately, then a valid packet can restore it', () => {
  const output = root(), component = api.mount(output, {assessment: fresh()});
  assert.match(output.textContent, /issuer restated remaining authorization/);
  const invalid = fresh(); invalid.authority.may_execute = true;
  assert.equal(component.setAssessment(invalid), false);
  assert.match(output.textContent, /Research unavailable/);
  assert.doesNotMatch(output.textContent, /issuer restated|sha256:|cik:0001045810|\+12%/);
  assert.equal(component.setLocale('zh'), true);
  assert.match(output.textContent, /研究暂不可用/);
  assert.equal(component.setAssessment(fresh('history_missing')), true);
  assert.match(output.textContent, /比较证据不足/);
});

test('mount snapshots valid input and locale changes do not resurrect later caller mutations', () => {
  const packet = fresh(), output = root(), component = api.mount(output, {assessment: packet});
  packet.source_admission_established = true;
  packet.news_context.current.views[0].display.plain_status = 'UNTRUSTED_LATER_MUTATION';
  component.setLocale('zh');
  assert.match(output.textContent, /公司研究/);
  assert.match(output.textContent, /issuer restated remaining authorization/);
  assert.doesNotMatch(output.textContent, /UNTRUSTED_LATER_MUTATION/);
  component.setLocale('en');
  assert.match(output.textContent, /Company research/);
});

test('teardown is idempotent, respects pre-existing root classes and prevents resurrection', () => {
  for (const preexisting of [false, true]) {
    const output = root(); if (preexisting) output.classList.add('bci-decision-desk');
    output.classList.add('caller-class');
    const component = api.mount(output, {assessment: fresh()});
    component.destroy(); component.destroy();
    assert.equal(output.textContent, '');
    assert.equal(output.classList.contains('caller-class'), true);
    assert.equal(output.classList.contains('bci-decision-desk'), preexisting);
    assert.equal(component.setAssessment(fresh()), false);
    assert.equal(component.setLocale('en'), false);
    assert.equal(output.textContent, '');
  }
});

test('legacy peer ISO clocks accept producer-valid reduced, basic, week and fractional forms', () => {
  // These are test-only representations of the same owner clock contract; the
  // retained source captures themselves are never edited or regenerated.
  for (const value of ['2026-09-28T13Z', '2026-09-28T13:00Z', '20260928T130000Z',
    '2026-W40-1T13:00Z', '2026W401T130000Z', '2026-W40T13Z',
    '2026-09-28T13:00:00,123456Z', '2026-09-28T13:00:00.123456789Z']) {
    const packet = fresh(); packet.peer_context.context.cohort.formed_at = value;
    assert.equal(api.validateAssessment(packet), packet, value);
  }
  const packet = fresh(), pc = packet.peer_context.context;
  pc.window.end_at = '2026-09-28T20:00Z';
  pc.observed_peers[0].known_at = '20260928T200008,0000009Z';
  assert.equal(api.validateAssessment(packet), packet, 'owner truncates fractional precision to microseconds');
});

test('peer clock compatibility preserves calendar, ordering and strict v3 envelope boundaries', () => {
  for (const value of ['2025-W53-1T13Z', '2026-W40-8T13Z', '20260230T1300Z',
    '2026-09-28T13:00+00:00', '2026-09-28 13:00Z', '2026-09-28T24Z']) {
    rejects(p => { p.peer_context.context.cohort.formed_at = value; });
  }
  rejects(p => { p.peer_context.context.observed_peers[0].known_at = '20260928T200008,0000011Z'; });
  rejects(p => { p.entry_context.source_envelope.materialized_at = '2026-09-28T20:00Z'; });
  rejects(p => { p.composed_at = '20260928T200016Z'; });
});

test('owner contradictions cannot promote blocked entry or retrospectively formed cohorts', () => {
  rejects(p => {
    p.entry_context.owner_projection.state = 'ENTRY_OPEN';
    p.entry_context.owner_projection.entry_open = true;
    assert.ok(p.entry_context.owner_projection.blockers.length);
  });
  rejects(p => { p.peer_context.context.cohort.formed_at = p.peer_context.context.window.end_at; });
  rejects(p => { p.peer_context.context.cohort.purpose = 'all_competitors'; });
  rejects(p => { p.peer_context.context.window.max_age_seconds = 0; });
});

test('NewsImpact display summaries are identified as derived owner summaries in both languages', () => {
  const english = words(api.presentation(fresh(), 'en')), chinese = words(api.presentation(fresh(), 'zh'));
  assert.match(english, /NewsImpact summary · current/);
  assert.match(chinese, /NewsImpact 摘要 · 当前/);
  assert.doesNotMatch(english, /Source text · current|Source text · watch next/);
  assert.doesNotMatch(chinese, /来源原文 · 当前|来源原文 · 后续关注/);
});
