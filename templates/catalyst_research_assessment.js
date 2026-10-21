/* Pure v3 research presentation. No acquisition, WMN join or action authority. */
(function (global, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else global.CatalystResearchAssessment = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const QUAL = 'SUPPLIED_OWNER_STATE_NOT_INDEPENDENTLY_ADMITTED';
  const AUTH = ['may_admit_membership', 'may_change_entry', 'may_claim_causality',
    'may_execute', 'may_gate', 'may_publish', 'may_rank', 'may_size'];
  const ADVANCED = {
    best_entry_policy: 'NOT_QUALIFIED', fundamental_value_priced_in: 'NOT_ESTIMABLE',
    causal_theme_spillover: 'NOT_ESTIMABLE', predictive_lead_lag: 'NOT_QUALIFIED',
    clinical_outcome_probability: 'NOT_QUALIFIED'
  };
  const ENTRY_STATES = ['NOT_READY', 'APPROACHING_ENTRY', 'ENTRY_OPEN', 'WAIT_PULLBACK',
    'RAN_DONT_CHASE', 'INVALIDATED', 'UNAVAILABLE_DATA'];
  const LIMITS = ['RELATIVE_RETURN_IS_NOT_FACTOR_RESIDUAL', 'PARTICIPATION_IS_NOT_CAUSAL_SPILLOVER',
    'NO_INTRADAY_LEAD_LAG_FROM_WINDOW_RETURNS', 'COHORT_IS_NOT_ALL_SUBTHEME_SECURITIES',
    'NO_SOURCE_OR_DISPLAY_ADMISSION'];
  const OWN = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  function need(value) { if (!value) throw new Error('RESEARCH_PACKET_UNAVAILABLE'); }
  function record(value) {
    need(value !== null && typeof value === 'object' && !Array.isArray(value));
    const proto = Object.getPrototypeOf(value);
    need(proto === Object.prototype || proto === null);
    return value;
  }
  function text(value) { need(typeof value === 'string' && value.trim().length > 0); return value; }
  function array(value) { need(Array.isArray(value)); return value; }
  function strings(value) { array(value).forEach(text); return value; }
  function number(value) { need(typeof value === 'number' && Number.isFinite(value)); return value; }
  function nullableNumber(value) { if (value !== null) number(value); }
  function count(value) { need(Number.isSafeInteger(value) && value >= 0); return value; }
  function digest(value) { need(typeof value === 'string' && /^sha256:[a-f0-9]{64}$/.test(value)); }
  function falseFlags(value, keys) {
    record(value);
    need(Object.keys(value).length === keys.length);
    keys.forEach(key => need(OWN(value, key) && value[key] === false));
  }
  function jsonValue(value, seen, depth) {
    need(depth <= 32);
    if (value === null || typeof value === 'boolean' || typeof value === 'string') return;
    if (typeof value === 'number') { number(value); return; }
    need(value !== undefined && typeof value === 'object' && !seen.has(value));
    seen.add(value);
    if (Array.isArray(value)) { need(value.length <= 2000); value.forEach(v => jsonValue(v, seen, depth + 1)); }
    else { record(value); Object.values(value).forEach(v => jsonValue(v, seen, depth + 1)); }
    seen.delete(value);
  }
  // Keep all six supported fractional digits; Date.parse would discard microseconds.
  function instant(value) {
    const match = typeof value === 'string' &&
      /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?Z$/.exec(value);
    need(match);
    const [year, month, day, hour, minute, second] = match.slice(1, 7).map(Number);
    need(year >= 1 && month >= 1 && month <= 12 && day >= 1 && day <= 31 &&
      hour < 24 && minute < 60 && second < 60);
    const date = new Date(0);
    date.setUTCFullYear(year, month - 1, day);
    date.setUTCHours(hour, minute, second, 0);
    need(date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 &&
      date.getUTCDate() === day);
    return BigInt(date.getTime()) * 1000n + BigInt((match[7] || '').padEnd(6, '0'));
  }
  // peer_context.clock preserves Python ISO forms, unlike the strict v3
  // envelope clocks. Normalize only that legacy peer grammar at this boundary.
  function peerInstant(value) {
    need(typeof value === 'string' && value.length <= 512);
    const match = /^(\d{4}-\d{2}-\d{2}|\d{8}|\d{4}-W\d{2}(?:-\d)?|\d{4}W\d{2}\d?)T(\d{2}(?::\d{2}(?::\d{2})?|\d{2}(?:\d{2})?)?)(?:[.,](\d+))?Z$/.exec(value);
    need(match);
    let date = match[1];
    if (date.includes('W')) {
      const weekParts = /^(\d{4})-?W(\d{2})(?:-?(\d))?$/.exec(date);
      const year = Number(weekParts[1]), week = Number(weekParts[2]), weekday = Number(weekParts[3] || 1);
      need(year >= 1 && week >= 1 && week <= 53 && weekday >= 1 && weekday <= 7);
      const start = new Date(0);
      start.setUTCFullYear(year, 0, 4); start.setUTCHours(0, 0, 0, 0);
      start.setUTCDate(start.getUTCDate() - (start.getUTCDay() + 6) % 7 + (week - 1) * 7);
      const thursday = new Date(start.getTime());
      thursday.setUTCDate(thursday.getUTCDate() + 3);
      need(thursday.getUTCFullYear() === year); // Refuse a nonexistent ISO week 53.
      start.setUTCDate(start.getUTCDate() + weekday - 1);
      date = start.toISOString().slice(0, 10);
    } else if (!date.includes('-')) date = date.slice(0, 4) + '-' + date.slice(4, 6) + '-' + date.slice(6, 8);
    const parts = match[2].includes(':') ? match[2].split(':') : match[2].match(/\d{2}/g);
    const normalized = date + 'T' + parts[0] + ':' + (parts[1] || '00') + ':' + (parts[2] || '00') +
      (match[3] ? '.' + match[3].slice(0, 6) : '') + 'Z';
    return instant(normalized);
  }
  function identity(value) {
    record(value);
    ['company_id', 'security_id', 'identity_epoch', 'identity_source_ref'].forEach(k => text(value[k]));
  }
  function sameIdentity(a, b) {
    identity(a);
    ['company_id', 'security_id', 'identity_epoch', 'identity_source_ref'].forEach(k => need(a[k] === b[k]));
  }
  function envelope(value, owner, cut, composed) {
    record(value);
    need(value.schema === 'catalyst.supplied_owner_time_envelope.v1' && value.owner === owner);
    const at = instant(value.information_cutoff_at), made = instant(value.materialized_at),
      received = instant(value.received_at);
    need(at === cut && at <= made && made <= received && received <= composed);
    text(value.source_ref); text(value.source_revision); digest(value.payload_digest);
  }
  function sameEnvelope(a, b) {
    if (a === null || b === null) { need(a === b); return; }
    record(a); record(b);
    ['schema', 'owner', 'information_cutoff_at', 'materialized_at', 'received_at',
      'source_ref', 'source_revision', 'payload_digest'].forEach(k => need(a[k] === b[k]));
  }
  function observation(value, windowEnd, cut) {
    record(value); text(value.company_id); text(value.security_id); text(value.source_ref);
    number(value.return_pct);
    const known = peerInstant(value.known_at);
    need(windowEnd <= known && known <= cut);
  }
  function peers(value, focal, cut) {
    record(value);
    if (value.state === 'UNAVAILABLE') {
      need(value.context === null && value.reason_code === 'PEER_INPUT_NOT_SUPPLIED'); return;
    }
    need(value.state === 'PROJECTED' && value.reason_code === null);
    const p = record(value.context), coverage = record(p.coverage), stats = record(p.statistics);
    need(p.schema === 'catalyst.peer_research_context.v1' &&
      p.qualification === 'SUPPLIED_RESEARCH_COHORT_ONLY' && p.source_admission_established === false);
    falseFlags(p.authority, AUTH); digest(p.input_digest); digest(p.context_id); sameIdentity(p.focal, focal);
    need(instant(p.decision_at) === cut);
    const window = record(p.window), start = peerInstant(window.start_at), end = peerInstant(window.end_at);
    need(start < end && end <= cut); text(window.currency); text(window.return_basis);
    need(number(window.max_age_seconds) > 0);
    const cohort = record(p.cohort);
    ['definition_ref', 'membership_ref', 'purpose', 'rights_ref', 'subtheme_id', 'universe_description']
      .forEach(k => text(cohort[k]));
    need(cohort.purpose === 'supplied_research_cohort' && peerInstant(cohort.formed_at) <= start);
    const total = count(coverage.eligible_peer_issuers), n = count(coverage.observed_peer_issuers);
    need(n <= total && count(coverage.ambiguous_peer_issuers) <= total);
    if (total === 0) need(coverage.fraction === null);
    else need(Math.abs(number(coverage.fraction) - n / total) < 1e-12);
    const observed = array(p.observed_peers), companies = new Set(), securities = new Set();
    need(observed.length === n && count(stats.effective_observed_issuer_count) === n);
    observed.forEach(row => {
      observation(row, end, cut);
      need(row.company_id !== focal.company_id && row.security_id !== focal.security_id &&
        !companies.has(row.company_id) && !securities.has(row.security_id));
      companies.add(row.company_id); securities.add(row.security_id);
    });
    const own = p.focal_observation;
    if (own !== null) {
      observation(own, end, cut);
      need(own.company_id === focal.company_id && own.security_id === focal.security_id);
    }
    const states = ['FOCAL_MEMBERSHIP_UNAVAILABLE', 'FOCAL_PRICE_UNAVAILABLE', 'NO_ELIGIBLE_PEERS',
      'NO_OBSERVED_PEERS', 'COMPLETE', 'PARTIAL'];
    need(states.includes(p.state));
    if (p.state === 'COMPLETE') need(own !== null && total > 0 && n === total);
    if (p.state === 'PARTIAL') need(own !== null && n > 0 && n < total);
    if (p.state === 'NO_ELIGIBLE_PEERS') need(own !== null && total === 0);
    if (p.state === 'NO_OBSERVED_PEERS') need(own !== null && total > 0 && n === 0);
    if (p.state === 'FOCAL_PRICE_UNAVAILABLE') need(own === null);
    if (p.state === 'FOCAL_MEMBERSHIP_UNAVAILABLE') need(own === null && n === 0);
    ['observed_subset_equal_weight_return_pct', 'complete_cohort_equal_weight_return_pct',
      'focal_minus_observed_peers_pp', 'observed_subset_median_return_pct', 'observed_subset_dispersion_pp']
      .forEach(k => nullableNumber(stats[k]));
    need((stats.observed_subset_equal_weight_return_pct === null) === (n === 0));
    need((stats.observed_subset_median_return_pct === null) === (n === 0));
    need((stats.observed_subset_dispersion_pp === null) === (n === 0));
    if (stats.observed_subset_dispersion_pp !== null) need(stats.observed_subset_dispersion_pp >= 0);
    need((stats.focal_minus_observed_peers_pp === null) === (own === null || n === 0));
    if (p.state === 'COMPLETE') need(stats.complete_cohort_equal_weight_return_pct === stats.observed_subset_equal_weight_return_pct);
    else need(stats.complete_cohort_equal_weight_return_pct === null);
    need(count(stats.advancing) + count(stats.declining) + count(stats.unchanged) === n);
    array(p.excluded).forEach(row => { record(row); text(row.security_id); text(row.reason); });
    strings(p.interpretation_limits);
    LIMITS.forEach(limit => need(p.interpretation_limits.includes(limit)));
  }
  function entry(value, focal, cut, composed) {
    record(value);
    need(value.owner_state_qualification === QUAL && value.decision_availability_established === false);
    if (value.state === 'OWNER_INPUT_UNAVAILABLE') {
      need(value.owner_projection === null && value.source_envelope === null); return;
    }
    envelope(value.source_envelope, 'prophet_b4', cut, composed);
    if (value.state === 'DIFFERENT_INFORMATION_CUT') { need(value.owner_projection === null); return; }
    need(value.state === 'OWNER_RESEARCH_CONTEXT_ATTACHED' &&
      value.interpretation === 'RECONSTRUCTED_CONTEXT_IS_NOT_CURRENT_ENTRY_AVAILABILITY' &&
      value.scope === 'EXISTING_STRATEGY_AND_HORIZON_ONLY' &&
      value.strategy_authority_tier === 'SHADOW_ONLY' && value.strategy_scientific_status === 'CONTROL_ONLY');
    const p = record(value.owner_projection);
    need(p.schema === 'prophet.entry_availability/v1' && p.security_id === focal.security_id &&
      p.identity_epoch === focal.identity_epoch && ENTRY_STATES.includes(p.state));
    need(instant(p.evaluated_at) === cut && instant(p.quote_asof) <= cut);
    need(typeof p.entry_open === 'boolean' && p.entry_open === (p.state === 'ENTRY_OPEN'));
    ['strategy_id', 'strategy_version', 'horizon', 'horizon_role', 'entry_policy_version'].forEach(k => text(p[k]));
    strings(p.blockers); need(p.state !== 'ENTRY_OPEN' || p.blockers.length === 0);
    nullableNumber(p.current_price);
    ['distance_to_zone_pct', 'extension_atr', 'move_since_anchor_pct', 'move_since_first_trigger_pct',
      'risk_to_invalidation_pct'].forEach(k => nullableNumber(p[k]));
  }
  function newsViews(value, company, cut) {
    const index = new Map();
    array(value).forEach(view => {
      record(view);
      need(view.schema === 'thesis_view.v1' && view.authority === 'context_only' && view.company_id === company);
      falseFlags(view.prophet_flags, ['may_gate', 'may_rank', 'may_size', 'prophet_authority']);
      const key = text(view.original_proposition_fact_id);
      need(!index.has(key)); index.set(key, view);
      need(instant(view.decision_cut) === cut && instant(view.as_of_utc) === cut);
      const display = record(view.display);
      text(display.plain_status); text(display.what_we_are_watching);
    });
    return index;
  }
  function news(value, company, cut, composed) {
    record(value);
    need(value.owner_state_qualification === QUAL &&
      value.semantics === 'UNCHANGED_NEWS_IMPACT_THESIS_AND_MATERIAL_DELTA_TRIGGERS' &&
      value.interpretation === 'EMPTY_TRIGGERS_ARE_NOT_PROOF_OF_NO_ECONOMIC_CHANGE');
    const current = record(value.current), comparison = record(value.comparison);
    need(instant(current.information_cutoff_at) === cut);
    let currentIndex = new Map();
    if (current.state === 'UNAVAILABLE') {
      need(current.views === null && current.source_envelope === null);
      need(['NEWS_INPUT_NOT_SUPPLIED', 'CURRENT_OWNER_INPUT_NOT_SUPPLIED'].includes(current.reason_code));
    } else {
      need(current.state === 'PROJECTED_RESEARCH' && current.reason_code === null);
      envelope(current.source_envelope, 'news_impact', cut, composed);
      currentIndex = newsViews(current.views, company, cut);
    }
    const sources = record(comparison.source_envelopes);
    sameEnvelope(sources.current, current.source_envelope);
    if (comparison.state === 'NOT_REQUESTED') {
      need(comparison.reason_code === 'COMPARISON_NOT_REQUESTED' &&
        comparison.information_cutoff_at === null && comparison.prior_views === null &&
        comparison.pairs === null && sources.prior === null); return;
    }
    const priorCut = instant(comparison.information_cutoff_at);
    need(priorCut < cut);
    if (sources.prior !== null) envelope(sources.prior, 'news_impact', priorCut, composed);
    if (comparison.state === 'UNAVAILABLE') {
      need(comparison.prior_views === null && comparison.pairs === null);
      if (current.state === 'UNAVAILABLE') need(comparison.reason_code === 'CURRENT_OWNER_INPUT_NOT_SUPPLIED');
      else need(comparison.reason_code === 'PRIOR_OWNER_INPUT_NOT_SUPPLIED' && sources.prior === null);
      return;
    }
    need(comparison.state === 'PROJECTED_RESEARCH' && comparison.reason_code === null &&
      current.state === 'PROJECTED_RESEARCH' && sources.prior !== null);
    const priorIndex = newsViews(comparison.prior_views, company, priorCut);
    const expected = new Set([...currentIndex.keys(), ...priorIndex.keys()]), seen = new Set();
    array(comparison.pairs).forEach(pair => {
      record(pair); record(pair.view_key);
      const key = text(pair.view_key.original_proposition_fact_id);
      need(pair.view_key.company_id === company && expected.has(key) && !seen.has(key)); seen.add(key);
      const currentPresent = currentIndex.has(key), priorPresent = priorIndex.has(key);
      need(pair.presence === (currentPresent && priorPresent ? 'BOTH_CUTS' : currentPresent ? 'CURRENT_ONLY' : 'PRIOR_ONLY'));
      if (currentPresent) strings(pair.material_delta_triggers);
      else need(pair.material_delta_triggers === null);
    });
    need(seen.size === expected.size);
  }
  function validateAssessment(packet) {
    jsonValue(packet, new Set(), 0); record(packet);
    need(packet.schema === 'catalyst.stock_research_assessment.v3' &&
      packet.qualification === 'NONACTIVATED_RESEARCH_CONSUMER' &&
      packet.source_admission_established === false && packet.decision_availability_established === false &&
      packet.owner_state_qualification === QUAL &&
      packet.timing_semantics === 'SUPPLIED_RECONSTRUCTION_NOT_PROOF_OF_ACTUAL_DECISION_AVAILABILITY' &&
      packet.composition_rule === 'SEPARATE_OWNER_FACETS_NO_FUSION_SCORE_OR_GATE_OVERRIDE');
    falseFlags(packet.authority, AUTH); identity(packet.focal); digest(packet.assessment_id); digest(packet.input_digest);
    const cut = instant(packet.information_cutoff_at), composed = instant(packet.composed_at);
    need(cut <= composed);
    peers(packet.peer_context, packet.focal, cut);
    entry(packet.entry_context, packet.focal, cut, composed);
    news(packet.news_context, packet.focal.company_id, cut, composed);
    const advanced = record(packet.advanced_estimates);
    need(Object.keys(advanced).length === Object.keys(ADVANCED).length);
    Object.entries(ADVANCED).forEach(([key, state]) => {
      const estimate = record(advanced[key]); need(estimate.state === state && estimate.value === null);
    });
    return packet;
  }
  function presentation(packet, locale) {
    validateAssessment(packet);
    const zh = locale === 'zh', choose = (en, cn) => zh ? cn : en;
    const absent = choose('Unavailable', '暂无数据');
    const num = value => value === null ? absent : new Intl.NumberFormat(zh ? 'zh-CN' : 'en-US', {maximumFractionDigits: 2}).format(value);
    const pct = value => value === null ? absent : (value > 0 ? '+' : '') + num(value) + '%';
    const pp = value => value === null ? absent : (value > 0 ? '+' : '') + num(value) + choose(' percentage points', ' 个百分点');
    const clock = value => value === null ? absent : value.replace('T', ' ').replace('Z', ' UTC');
    const row = (en, cn, value) => ({label: choose(en, cn), text: value});
    const sections = [], sourceRows = [
      row('Assessment', '研究版本', packet.assessment_id),
      row('Company', '公司标识', packet.focal.company_id),
      row('Security', '证券标识', packet.focal.security_id),
      row('Identity epoch', '身份版本', packet.focal.identity_epoch),
      row('Identity source', '身份来源', packet.focal.identity_source_ref),
      row('Information cutoff', '信息截止时间', clock(packet.information_cutoff_at)),
      row('Composed later', '研究汇总时间', clock(packet.composed_at))
    ];
    function sourceEnvelope(label, value) {
      if (!value) return;
      sourceRows.push({label, text: value.source_ref + ' · ' + value.source_revision},
        row('Information / created / received', '信息截止／生成／接收',
          [value.information_cutoff_at, value.materialized_at, value.received_at].map(clock).join(' · ')),
        row('Payload reference', '内容摘要标识', value.payload_digest));
    }
    const nc = packet.news_context, current = nc.current, comparison = nc.comparison, newsRows = [];
    if (current.state === 'UNAVAILABLE') newsRows.push(row('Current evidence', '当前证据', choose('Current owner evidence was not supplied.', '尚未提供当前来源证据。')));
    else if (!current.views.length) newsRows.push(row('Current evidence', '当前证据', choose('This supplied cut contains no company items.', '所提供的信息切片中没有该公司的条目。')));
    else current.views.forEach(view => {
      newsRows.push(row('NewsImpact summary · current', 'NewsImpact 摘要 · 当前', view.display.plain_status),
        row('NewsImpact summary · watch next', 'NewsImpact 摘要 · 后续关注', view.display.what_we_are_watching));
      sourceRows.push(row('News proposition', '新闻命题标识', view.original_proposition_fact_id));
    });
    const compText = comparison.state === 'NOT_REQUESTED' ? choose('Comparison was not requested.', '未请求历史比较。') :
      comparison.state === 'UNAVAILABLE' ? choose('Comparison is unavailable; missing evidence does not mean no change.', '比较证据不足；这不代表没有变化。') :
      choose('Current and prior supplied cuts are compared. Empty indicators do not prove no economic change.', '已比较所提供的当前与先前信息；没有变化标记并不代表经济影响未变。');
    newsRows.push(row('Change comparison', '变化比较', compText));
    if (comparison.state === 'PROJECTED_RESEARCH') {
      comparison.pairs.forEach(pair => {
        const triggers = pair.material_delta_triggers;
        const description = pair.presence === 'PRIOR_ONLY' ? choose('Only present in the prior cut.', '仅出现在先前信息切片中。') :
          pair.presence === 'CURRENT_ONLY' ? choose('Only present in the current cut.', '仅出现在当前信息切片中。') :
          choose('Present in both supplied cuts.', '在两个信息切片中均有记录。');
        newsRows.push(row('Evidence continuity', '证据延续', description));
        if (triggers && triggers.includes('source_correction')) newsRows.push(row('Owner change indicator', '来源变化标记', choose('Source correction recorded.', '已记录来源更正。')));
        else if (triggers && triggers.length) newsRows.push(row('Owner change indicator', '来源变化标记', choose('The owner reports an update; inspect its evidence.', '来源报告了更新，请核查证据。')));
        sourceRows.push(row('Comparison proposition', '比较命题标识', pair.view_key.original_proposition_fact_id),
          row('Owner change codes', '来源变化代码', triggers === null ? absent : triggers.join(', ') || choose('No indicators supplied', '未提供变化标记')));
      });
      sourceRows.push(row('Prior information cutoff', '先前信息截止时间', clock(comparison.information_cutoff_at)));
    }
    sections.push({title: choose('Company change', '公司变化'), rows: newsRows});
    sourceEnvelope(choose('Current news source', '当前新闻来源'), current.source_envelope);
    sourceEnvelope(choose('Prior news source', '先前新闻来源'), comparison.source_envelopes.prior);
    const peerRows = [], pc = packet.peer_context.context;
    if (!pc) peerRows.push(row('Peer evidence', '同组证据', choose('A peer cohort was not supplied.', '尚未提供同组研究数据。')));
    else {
      peerRows.push(row('Comparison scope', '比较范围', choose('Supplied research cohort; coverage is not the whole subtheme.', '仅为所提供的研究组，不代表整个细分主题。')),
        row('Company return', '公司区间回报', pc.focal_observation ? pct(pc.focal_observation.return_pct) : absent),
        row('Observed peer average', '已观察同组均值', pct(pc.statistics.observed_subset_equal_weight_return_pct)),
        row('Company minus peers', '公司与同组之差', pp(pc.statistics.focal_minus_observed_peers_pp)),
        row('Coverage', '覆盖情况', choose(pc.coverage.observed_peer_issuers + ' of ' + pc.coverage.eligible_peer_issuers + ' eligible issuers observed.',
          '已观察 ' + pc.coverage.observed_peer_issuers + '／' + pc.coverage.eligible_peer_issuers + ' 家符合条件的公司。')),
        row('Participation', '涨跌分布', choose(pc.statistics.advancing + ' advancing · ' + pc.statistics.declining + ' declining · ' + pc.statistics.unchanged + ' unchanged',
          pc.statistics.advancing + ' 家上涨 · ' + pc.statistics.declining + ' 家下跌 · ' + pc.statistics.unchanged + ' 家持平')));
      sourceRows.push(row('Price window', '价格观察区间', clock(pc.window.start_at) + ' → ' + clock(pc.window.end_at)),
        row('Return basis / currency', '回报口径／币种', pc.window.return_basis + ' · ' + pc.window.currency),
        row('Cohort source / rights', '研究组来源／使用权', pc.cohort.membership_ref + ' · ' + pc.cohort.rights_ref),
        row('Cohort description · source text', '研究组说明 · 来源原文', pc.cohort.universe_description));
      pc.observed_peers.forEach(item => sourceRows.push(row('Observed peer', '已观察同组证券', item.security_id + ' · ' + pct(item.return_pct) + ' · ' + item.source_ref)));
      pc.excluded.forEach(item => sourceRows.push(row('Excluded · source code', '已排除 · 来源代码', item.security_id + ' · ' + item.reason)));
    }
    sections.push({title: choose('Peer movement', '同组表现'), rows: peerRows});
    const ec = packet.entry_context, entryRows = [];
    if (ec.state !== 'OWNER_RESEARCH_CONTEXT_ATTACHED') entryRows.push(row('Entry evidence', '入场研究证据',
      ec.state === 'DIFFERENT_INFORMATION_CUT' ? choose('The supplied entry state uses another information cutoff.', '所提供的入场状态对应另一信息截止时间。') :
        choose('Entry-owner evidence was not supplied.', '尚未提供入场模块的来源证据。')));
    else {
      const ep = ec.owner_projection;
      const names = {
        NOT_READY: ['Conditions are not ready', '条件尚未就绪'], APPROACHING_ENTRY: ['Conditions are approaching', '条件正在接近'],
        ENTRY_OPEN: ['The supplied example has an open state', '所提供的示例状态为开放'],
        WAIT_PULLBACK: ['The owner is waiting for a pullback', '来源模块正在等待回调'],
        RAN_DONT_CHASE: ['The move exceeded the chase boundary', '价格走势已超出追价边界'],
        INVALIDATED: ['The supplied setup was invalidated', '所提供的形态已失效'],
        UNAVAILABLE_DATA: ['Required entry data is unavailable', '所需的入场数据不可用']
      };
      entryRows.push(row('Supplied research state', '所提供的研究状态', choose(...names[ep.state])),
        row('Use limitation', '使用限制', choose('Research control and shadow only; this is not current entry availability.', '仅用于研究对照与影子观察，不代表当前可入场。')),
        row('Strategy / horizon', '策略／周期', ep.strategy_id === 'EARLY_LEADERSHIP_SECTOR_ROTATION' ?
          choose('Early leadership sector rotation · ' + (ep.horizon === '2_15_SESSIONS' ? '2–15 sessions' : 'see source horizon'),
            '早期领涨板块轮动 · ' + (ep.horizon === '2_15_SESSIONS' ? '2–15 个交易时段' : '请查看来源周期')) :
          choose('See the supplied owner strategy and horizon.', '请查看来源所提供的策略与周期。')),
        row('Price in example', '示例中的价格', num(ep.current_price)),
        row('Owner blockers', '来源限制', choose(ep.blockers.length + ' reported; inspect source detail.', '已报告 ' + ep.blockers.length + ' 项，请核查来源详情。')));
      sourceRows.push(row('Entry state / strategy / horizon', '入场状态／策略／周期', ep.state + ' · ' + ep.strategy_id + ' · ' + ep.horizon),
        row('Entry research restrictions', '入场研究限制', ec.strategy_scientific_status + ' · ' + ec.strategy_authority_tier),
        row('Entry blocker codes', '入场限制代码', ep.blockers.join(', ') || choose('None supplied', '未提供')),
        row('Quote / evaluation', '报价／评估时间', clock(ep.quote_asof) + ' · ' + clock(ep.evaluated_at)));
      [['distance_to_zone_pct', 'Distance to zone (%)', '与区间距离（%）'],
        ['extension_atr', 'Extension in ATR units', '以 ATR 衡量的延伸'],
        ['move_since_anchor_pct', 'Move since anchor (%)', '锚点以来变化（%）'],
        ['move_since_first_trigger_pct', 'Move since trigger (%)', '触发以来变化（%）'],
        ['risk_to_invalidation_pct', 'Distance to invalidation (%)', '与失效位距离（%）']]
        .forEach(([key, en, cn]) => sourceRows.push(row(en, cn, num(ep[key]))));
    }
    sections.push({title: choose('Entry context', '入场背景'), rows: entryRows});
    sourceEnvelope(choose('Entry source', '入场研究来源'), ec.source_envelope);
    const advancedNames = {
      best_entry_policy: ['Best entry policy', '最佳入场策略'], fundamental_value_priced_in: ['Value priced in', '价值计价程度'],
      causal_theme_spillover: ['Causal spillover', '因果外溢'], predictive_lead_lag: ['Predictive leadership', '预测性领涨'],
      clinical_outcome_probability: ['Clinical outcome probability', '临床结果概率']
    };
    sections.push({title: choose('Estimates still missing', '尚缺的估计'), rows: Object.keys(ADVANCED).map(key =>
      row(...advancedNames[key], packet.advanced_estimates[key].state === 'NOT_QUALIFIED' ?
        choose('Not yet qualified', '尚未通过验证') : choose('Cannot be estimated from these inputs', '无法由这些输入估计')))});
    return {
      eyebrow: choose('SYNTHETIC RESEARCH PREVIEW', '合成研究预览'), title: choose('Company research', '公司研究'),
      intro: choose('Review the evidence. Live source and decision availability remain unproven.', '核查研究证据；实时来源与决策时可用性尚未证实。'),
      sections, sourceRows, sourcesTitle: choose('Sources and timing', '来源与时间'),
      sourcesNote: choose('Supplied references do not establish source rights, native admission or current publication. Returns do not establish causality or a predictive edge.',
        '所提供的引用不能证明来源使用权、原生准入或当前发布状态。回报不代表因果关系或预测优势。')
    };
  }
  function mount(root, options) {
    need(root && root.ownerDocument && typeof root.replaceChildren === 'function');
    options = options || {};
    const doc = root.ownerDocument, hadClass = root.classList.contains('bci-decision-desk');
    let locale = options.locale === 'zh' ? 'zh' : 'en', snapshot = null, destroyed = false;
    root.classList.add('bci-decision-desk');
    function el(tag, className, value) {
      const node = doc.createElement(tag);
      if (className) node.className = className;
      if (value !== undefined) node.textContent = value;
      return node;
    }
    function field(row) {
      const node = el('div', 'bci-dd-field');
      node.append(el('h4', '', row.label), el('p', '', row.text)); return node;
    }
    function draw(view) {
      const shell = el('div', 'bci-dd-shell'), header = el('header', 'bci-dd-header'), heading = el('div');
      heading.append(el('p', 'bci-dd-eyebrow', view.eyebrow), el('h2', '', view.title), el('p', 'bci-dd-intro', view.intro));
      header.append(heading); shell.append(header);
      const body = el('div', 'bci-dd-body'), grid = el('div', 'bci-dd-cases');
      view.sections.forEach(section => {
        const card = el('section', 'bci-dd-card');
        card.append(el('h3', '', section.title)); section.rows.forEach(row => card.append(field(row))); grid.append(card);
      });
      const sources = el('details', 'bci-dd-scope');
      sources.append(el('summary', '', view.sourcesTitle), el('p', '', view.sourcesNote));
      view.sourceRows.forEach(row => sources.append(field(row)));
      body.append(grid, sources); shell.append(body);
      root.replaceChildren(shell);
    }
    function unavailable() {
      snapshot = null;
      root.replaceChildren();
      const shell = el('div', 'bci-dd-shell');
      shell.append(el('h2', '', locale === 'zh' ? '研究暂不可用' : 'Research unavailable'),
        el('p', 'bci-dd-intro', locale === 'zh' ? '无法显示此数据包，请加载受支持的研究示例。' : 'This packet cannot be shown. Load a supported research example.'));
      root.append(shell);
    }
    function setAssessment(packet) {
      if (destroyed) return false;
      try {
        validateAssessment(packet);
        const next = JSON.parse(JSON.stringify(packet)), view = presentation(next, locale);
        draw(view); snapshot = next; return true;
      } catch (_) { unavailable(); return false; }
    }
    function setLocale(value) {
      if (destroyed) return false;
      locale = value === 'zh' ? 'zh' : 'en';
      if (snapshot) draw(presentation(snapshot, locale)); else unavailable();
      return true;
    }
    function destroy() {
      if (destroyed) return;
      destroyed = true; snapshot = null; root.replaceChildren();
      if (!hadClass) root.classList.remove('bci-decision-desk');
    }
    setAssessment(options.assessment);
    return Object.freeze({setAssessment, setLocale, destroy});
  }
  return Object.freeze({validateAssessment, presentation, mount});
});
