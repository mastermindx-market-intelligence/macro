/* BioCatalyst Decision Desk — presentation consumer for WMN 1.0.0.
 * The host owns authentication, current publication selection and navigation.
 * No data collection, identity repair, forecast, persistence or monitoring here.
 */
(function (host, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else host.BioCatalystDecisionDesk = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';

  const METHOD = 'biocatalyst.research_triage.v1';
  const VIEWS = ['upcoming', 'reconcile', 'history'];
  const HORIZONS = [7, 30, 90, 180, 365];
  const LANES = ['ACT_NOW', 'RECONCILE', 'RESEARCH_NEXT', 'MONITOR'];
  const FAMILIES = ['issuer_readout_guidance', 'regulatory_target_disclosed',
    'advisory_meeting_disclosed', 'result_announced', 'regulatory_action',
    'registry_primary_completion', 'registry_study_completion'];
  const ESTIMATES = ['probability', 'materiality', 'historical_response', 'incorporation'];
  const obj = x => x !== null && typeof x === 'object' && !Array.isArray(x);
  const str = (x, max = 4096) => typeof x === 'string' && x.trim().length > 0 && x.length <= max;
  const strings = x => Array.isArray(x) && x.length <= 200 && x.every(v => str(v));
  const civil = x => typeof x === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x) &&
    !Number.isNaN(Date.parse(x + 'T00:00:00Z')) && new Date(x + 'T00:00:00Z').toISOString().slice(0, 10) === x;
  const utc = x => typeof x === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(x) &&
    civil(x.slice(0, 10)) && !Number.isNaN(Date.parse(x));
  function reject(code) { const e = new Error(code); e.code = code; throw e; }
  function need(value, code = 'CONTRACT_UNAVAILABLE') { if (!value) reject(code); }
  function canonical(x) {
    if (Array.isArray(x)) return '[' + x.map(canonical).join(',') + ']';
    if (obj(x)) return '{' + Object.keys(x).sort().map(k => JSON.stringify(k) + ':' + canonical(x[k])).join(',') + '}';
    return JSON.stringify(x);
  }
  function freeze(x) {
    if (obj(x) || Array.isArray(x)) { Object.values(x).forEach(freeze); Object.freeze(x); }
    return x;
  }
  function snapshot(x) { return freeze(JSON.parse(JSON.stringify(x))); }
  function authority(a) {
    return obj(a) && a.classification === 'research_priority_only' &&
      ['trade_origination', 'changes_availability', 'position_sizing', 'prophet_admission'].every(k => a[k] === false);
  }
  function query(input = {}) {
    const view = input.view || 'upcoming';
    const q = {view, horizon_days: view === 'upcoming' ? (input.horizon_days ?? 90) : null,
      q: null, event_family: null, lane: null, limit: 50};
    need(VIEWS.includes(q.view) && (view === 'upcoming' ? HORIZONS.includes(q.horizon_days) : input.horizon_days == null), 'INVALID_QUERY');
    need(['q', 'event_family', 'lane'].every(k => input[k] === undefined || input[k] === null), 'INVALID_QUERY');
    need(input.limit === undefined || input.limit === 50, 'INVALID_QUERY');
    return freeze(q);
  }
  function rowKey(row) { return JSON.stringify([row.event_fact_ref, row.row_key.issuer_id]); }
  function stockLinks(row) {
    if (row.issuer.state !== 'resolved') return [];
    return row.links.stock_research.flatMap(link => {
      const security = row.issuer.securities.find(s => s.security_id === link.security_id);
      if (!security || link.relationship_role !== 'issuer' || !str(link.href)) return [];
      // Retain the owner's URL, but require one exact, issuer-bound stock route.
      const match = /^stock\.html\?ticker=([^&#]+)$/.exec(link.href);
      if (!match) return [];
      try {
        if (decodeURIComponent(match[1]) !== security.display_symbol) return [];
      } catch (_) { return []; }
      return [{href: link.href, symbol: security.display_symbol, security_id: security.security_id}];
    });
  }
  function evidenceLinks(row) {
    if (!row.event_family.startsWith('registry_')) return [];
    const seen = new Set();
    return row.evidence.flatMap(item => {
      // This is the existing registry evidence shape. Other evidence shapes
      // need an explicit owner-approved adapter; never derive a URL from an ID.
      if (!obj(item) || !str(item.url) || !row.timing.evidence_refs.includes(item.url)) return [];
      try {
        const url = new URL(item.url);
        if (url.protocol !== 'https:' || url.username || url.password || seen.has(url.href)) return [];
        seen.add(url.href);
        return [{href: item.url, label: url.hostname}];
      } catch (_) { return []; }
    });
  }
  function validateRow(r, cutoff, anchor) {
    need(obj(r) && obj(r.row_key) && str(r.event_fact_ref) && FAMILIES.includes(r.event_family));
    need(r.row_key.event_fact_ref === r.event_fact_ref && str(r.event_revision_ref) && typeof r.revision_is_current === 'boolean');
    need(['uncorroborated', 'corroborated', 'cancelled', 'withdrawn'].includes(r.occurrence));
    const t = r.timing, i = r.issuer, p = r.research_priority, rev = r.revision_summary;
    need(obj(t) && ['consistent', 'conflicted'].includes(t.state) && str(t.source_class));
    need((t.lower_date === null || civil(t.lower_date)) && (t.upper_date === null || civil(t.upper_date)));
    need(!(t.lower_date && t.upper_date) || t.lower_date <= t.upper_date);
    need(str(t.precision) && (t.source_wording === null || typeof t.source_wording === 'string') && strings(t.evidence_refs));
    need(obj(i) && ['resolved', 'unresolved', 'ambiguous'].includes(i.state) && Array.isArray(i.securities) && i.securities.length <= 100);
    need(r.row_key.issuer_id === i.issuer_id);
    if (i.state === 'resolved') {
      need(str(i.issuer_id) && str(i.company_id) && i.relationship_role === 'issuer' && i.identity_scope === 'current_only' && utc(i.identity_observed_at));
      need(!cutoff || Date.parse(i.identity_observed_at) <= Date.parse(cutoff), 'IDENTITY_CUT_MISMATCH');
      const ids = new Set();
      i.securities.forEach(s => {
        need(obj(s) && str(s.security_id) && str(s.listing_key) && str(s.display_symbol, 80) && s.state === 'active' && civil(s.symbol_observed_on));
        need(!cutoff || s.symbol_observed_on <= cutoff.slice(0, 10), 'IDENTITY_CUT_MISMATCH');
        need(!ids.has(s.security_id)); ids.add(s.security_id);
      });
    } else need(i.issuer_id === null && i.relationship_role === null && i.identity_scope === 'unavailable' && i.securities.length === 0);
    need(obj(rev) && rev.revision_ref === r.event_revision_ref && rev.revision_is_current === r.revision_is_current);
    need(rev.last_material_revision_known_at === null || utc(rev.last_material_revision_known_at));
    need(obj(p) && p.disposition === 'SELECTED' && p.method_id === METHOD && LANES.includes(p.lane) && authority(p.authority));
    need(str(p.primary_reason) && strings(p.gap_reasons) && civil(p.comparison_date) && (!anchor || p.comparison_date === anchor));
    ESTIMATES.forEach(k => {
      const v = r[k];
      need(obj(v) && v.state === 'NOT_ESTIMABLE' && v.value === null && str(v.reason_code) && v.method_ref === null && v.as_of === null && strings(v.evidence_refs));
    });
    need(obj(r.missingness) && ['source', 'identity', 'asset', 'economic', 'estimates'].every(k => strings(r.missingness[k])));
    need(Array.isArray(r.evidence) && r.evidence.length <= 200 && r.evidence.every(obj));
    need(Array.isArray(r.assets) && Array.isArray(r.relationships) && str(r.economic_exposure_state));
    need(obj(r.links) && Array.isArray(r.links.stock_research) && r.links.stock_research.length <= 100 && r.links.stock_research.every(obj));
    return r;
  }
  function validatePage(p, expectedQuery) {
    need(obj(p) && p.contract_id === 'biocatalyst_what_matters_next.v1' && p.schema_version === '1.0.0' && str(p.generation_id));
    need(['ready', 'partial', 'stale', 'empty'].includes(p.state) && p.method_id === METHOD && authority(p.authority) && strings(p.reason_codes));
    need(obj(p.input_cut) && utc(p.input_cut.cutoff) && Array.isArray(p.input_cut.members));
    need(utc(p.evaluation_cutoff) && civil(p.anchor_date) && p.anchor_date === p.evaluation_cutoff.slice(0, 10));
    need(Date.parse(p.input_cut.cutoff) <= Date.parse(p.evaluation_cutoff));
    need(obj(p.query) && canonical(p.query) === canonical(query(p.query)), 'QUERY_MISMATCH');
    if (expectedQuery) need(canonical(p.query) === canonical(expectedQuery), 'QUERY_MISMATCH');
    need(obj(p.coverage) && obj(p.coverage.family_states) && strings(p.coverage.missing_owner_ports));
    const n = p.pagination;
    need(obj(n) && n.limit === 50 && Number.isSafeInteger(n.total) && n.total >= 0 && (n.next_cursor === null || str(n.next_cursor, 20000)));
    need(Array.isArray(p.rows) && p.rows.length <= n.limit && p.rows.length <= n.total);
    need(p.state !== 'empty' || (n.total === 0 && p.rows.length === 0));
    const seen = new Set();
    p.rows.forEach(r => {
      validateRow(r, p.input_cut.cutoff, p.anchor_date);
      const key = rowKey(r); need(!seen.has(key), 'DUPLICATE_ROW'); seen.add(key);
    });
    return p;
  }
  function validateDetail(d, page, selected) {
    need(obj(d) && d.contract_id === 'biocatalyst_wmn_detail.v1' && d.schema_version === '1.0.0' && authority(d.authority));
    need(d.generation_id === page.generation_id, 'RELOAD_REQUIRED');
    validateRow(d.event, page.input_cut.cutoff, page.anchor_date);
    // A different revision/issuer/timing in the same snapshot is inconsistent.
    need(canonical(d.event) === canonical(selected), 'RELOAD_REQUIRED');
    need(Array.isArray(d.related_events) && d.related_events.length <= 200 && strings(d.reason_codes));
    d.related_events.forEach(r => {
      validateRow(r, page.input_cut.cutoff, page.anchor_date);
      need(r.issuer.issuer_id === selected.issuer.issuer_id && rowKey(r) !== rowKey(selected));
    });
    if (selected.event_family.startsWith('registry_')) {
      const parts = selected.event_fact_ref.split(':');
      need(obj(d.trial) && /^NCT\d{8}$/.test(d.trial.nct_id) && d.trial.nct_id === parts[1]);
    } else need(d.trial === null);
    return d;
  }
  function errorCode(e) {
    if ([401, 402, 403].includes(e && e.status)) return 'ACCESS_REQUIRED';
    if (e && (e.status === 409 || e.code === 'RELOAD_REQUIRED')) return 'RELOAD_REQUIRED';
    return 'UNAVAILABLE';
  }

  function createController(options) {
    need(options && typeof options.loadPage === 'function' && typeof options.loadDetail === 'function' && typeof options.getContextKey === 'function', 'HOST_BINDINGS_REQUIRED');
    let current = freeze({phase: 'idle', query: query(options.query), page: null, detail: null, selectedKey: null, more: false, issue: null});
    let epoch = 0, detailEpoch = 0, pageAbort, detailAbort, context = null, destroyed = false;
    const listeners = new Set();
    const notify = patch => {
      if (destroyed) return;
      current = freeze(Object.assign({}, current, patch));
      listeners.forEach(fn => fn(current));
    };
    function invalidate(issue = null) {
      epoch++; detailEpoch++;
      if (pageAbort) pageAbort.abort();
      if (detailAbort) detailAbort.abort();
      notify({phase: issue ? 'unavailable' : 'idle', page: null, detail: null, selectedKey: null, more: false, issue});
    }
    function contextKey() {
      let key;
      try { key = options.getContextKey(); } catch (_) { reject('CONTEXT_UNAVAILABLE'); }
      need(str(key), 'CONTEXT_UNAVAILABLE'); return key;
    }
    function isCurrent(ticket, capturedContext) {
      if (destroyed || ticket !== epoch) return false;
      try { if (contextKey() === capturedContext) return true; } catch (_) { /* clear */ }
      invalidate('CONTEXT_CHANGED'); return false;
    }
    async function refresh(nextQuery = current.query) {
      if (destroyed) return;
      invalidate();
      let q;
      try { q = query(nextQuery); context = contextKey(); }
      catch (_) { invalidate('UNAVAILABLE'); return; }
      const ticket = epoch, capturedContext = context;
      pageAbort = new AbortController();
      notify({phase: 'loading', query: q, issue: null});
      try {
        const payload = await options.loadPage({query: q, cursor: null, signal: pageAbort.signal});
        if (!isCurrent(ticket, capturedContext)) return;
        const page = snapshot(validatePage(payload, q));
        need(page.pagination.next_cursor !== null || page.rows.length === page.pagination.total, 'RELOAD_REQUIRED');
        notify({phase: 'loaded', page, issue: null});
      } catch (e) { if (isCurrent(ticket, capturedContext)) invalidate(errorCode(e)); }
    }
    async function more() {
      if (destroyed || !current.page || current.more || !current.page.pagination.next_cursor) return;
      const ticket = epoch, capturedContext = context, prior = current.page;
      if (!isCurrent(ticket, capturedContext)) return;
      const cursor = prior.pagination.next_cursor;
      pageAbort = new AbortController(); notify({more: true});
      try {
        const raw = await options.loadPage({query: current.query, cursor, signal: pageAbort.signal});
        if (!isCurrent(ticket, capturedContext)) return;
        const page = validatePage(raw, prior.query);
        need(page.generation_id === prior.generation_id && page.evaluation_cutoff === prior.evaluation_cutoff &&
          canonical(page.input_cut) === canonical(prior.input_cut) && page.state === prior.state &&
          canonical(page.coverage) === canonical(prior.coverage) && page.pagination.total === prior.pagination.total, 'RELOAD_REQUIRED');
        const seen = new Set(prior.rows.map(rowKey));
        page.rows.forEach(r => { need(!seen.has(rowKey(r)), 'RELOAD_REQUIRED'); seen.add(rowKey(r)); });
        need(page.rows.length > 0 && page.pagination.next_cursor !== cursor && seen.size <= page.pagination.total, 'RELOAD_REQUIRED');
        need(page.pagination.next_cursor !== null || seen.size === page.pagination.total, 'RELOAD_REQUIRED');
        notify({page: snapshot(Object.assign({}, page, {rows: prior.rows.concat(page.rows)})), more: false});
      } catch (e) { if (isCurrent(ticket, capturedContext)) invalidate(errorCode(e)); }
    }
    async function open(key) {
      if (destroyed || !current.page || !isCurrent(epoch, context)) return;
      const page = current.page, row = page.rows.find(r => rowKey(r) === key);
      if (!row) return;
      if (detailAbort) detailAbort.abort();
      const ticket = epoch, detailTicket = ++detailEpoch, capturedContext = context;
      detailAbort = new AbortController(); notify({detail: {phase: 'loading'}, selectedKey: key});
      try {
        const raw = await options.loadDetail({event_fact_ref: row.event_fact_ref,
          issuer_id: row.row_key.issuer_id, generation_id: page.generation_id, signal: detailAbort.signal});
        if (!isCurrent(ticket, capturedContext) || detailTicket !== detailEpoch) return;
        const payload = snapshot(validateDetail(raw, page, row));
        notify({detail: {phase: 'loaded', payload}});
      } catch (e) {
        if (isCurrent(ticket, capturedContext) && detailTicket === detailEpoch) invalidate(errorCode(e));
      }
    }
    function close() {
      detailEpoch++; if (detailAbort) detailAbort.abort();
      notify({detail: null, selectedKey: null});
    }
    return {
      refresh, more, open, close,
      getState: () => current,
      subscribe(fn) { listeners.add(fn); fn(current); return () => listeners.delete(fn); },
      contextChanged() { context = null; invalidate('CONTEXT_CHANGED'); },
      clear() { invalidate(); },
      destroy() { invalidate(); destroyed = true; listeners.clear(); }
    };
  }

  const COPY = {
    eyebrow: ['BIOCATALYST / DECISION DESK', 'BIOCATALYST / 决策工作台'],
    title: ['Know what to review next.', '明确下一步，知道该看什么。'],
    intro: ['Company milestones, the questions they raise, and the evidence to check.', '聚焦公司关键事件、待解问题与需要核查的证据。'],
    upcoming: ['Upcoming', '即将发生'], reconcile: ['Needs review', '需要核实'], history: ['Event history', '事件历史'],
    refresh: ['Refresh', '刷新'], horizon: ['Time horizon', '时间范围'], view: ['Review view', '查看范围'],
    loading: ['Checking the latest available review…', '正在检查最新可用内容…'], idle: ['Load your next review.', '载入下一步研究事项。'],
    unavailable: ['This review is temporarily unavailable.', '研究内容暂时不可用。'],
    unavailableBody: ['Refresh to request a current view. Previous cases have been cleared.', '请刷新以获取当前内容。之前显示的研究事项已清除。'],
    access: ['Sign in with access to view these cases.', '请使用拥有访问权限的账户登录。'],
    reload: ['The underlying review changed.', '研究依据已发生变化。'],
    reloadBody: ['Refresh to load one consistent version of the cases and their evidence.', '请刷新，载入版本一致的研究事项与证据。'],
    context: ['Your account or research context changed.', '账户或研究范围已更改。'],
    empty: ['No matching events in this view.', '当前范围内没有匹配事件。'],
    emptyBody: ['Try another horizon or check events that need review. Coverage is limited to the supplied sources.', '可调整时间范围，或查看需要核实的事件。覆盖范围仅限已提供的来源。'],
    partial: ['Limited coverage · see scope', '覆盖有限 · 查看范围'], stale: ['Source refresh needed', '来源需要更新'],
    scope: ['Coverage and method', '覆盖范围与方法'],
    scopeBody: ['The order is for research attention. Coverage and estimates can be incomplete; an absent event does not establish that nothing happened.', '排序用于安排研究重点。覆盖与估计可能不完整；未显示事件不代表没有事件发生。'],
    scopeOrder: ['Research order is supplied by the existing BioCatalyst method.', '研究顺序由现有 BioCatalyst 方法提供。'],
    snapshot: ['Review evaluated', '研究评估时间'], sourceCut: ['Source cutoff', '来源截止时间'],
    cases: ['Cases in this view', '当前研究事项'], loaded: ['Loaded', '已载入'], more: ['Load more', '载入更多'],
    case: ['Review case', '查看研究事项'], close: ['Close case', '关闭研究事项'],
    task: ['Next step', '下一步'], uncertainty: ['What remains unresolved', '尚待解决'],
    wording: ['Source wording', '来源原文'], noWording: ['No source wording supplied.', '未提供来源原文。'],
    setup: ['Setup', '概况'], scenarios: ['Scenarios', '情景'], research: ['Research', '研究'], sources: ['Sources', '来源'],
    sourceMissing: ['The source link was not supplied in this view.', '此视图未提供来源链接。'],
    sourceMissingBody: ['The wording can be reviewed, but its supporting document cannot yet be inspected here.', '可查看已提供的原文，但暂时无法在此核查其依据文件。'],
    noEstimates: ['Scenario estimates are not available yet.', '情景估计暂未提供。'],
    noEstimatesBody: ['Clinical likelihood, commercial impact, historical price response and what the market has priced in require separate evidence. This review does not supply those estimates.', '临床成功率、商业影响、历史价格反应及市场已计入的预期需要分别论证。此研究事项暂未提供这些估计。'],
    identity: ['Company identity', '公司身份'], identityBody: ['The supplied link uses current issuer identity. It does not establish historical identity or economic exposure.', '链接使用当前发行人身份；不能据此确定历史身份或经济权益。'],
    unresolved: ['Issuer unresolved', '发行人未确定'], ambiguous: ['Issuer needs confirmation', '发行人需要确认'],
    interval: ['Supplied date interval', '所提供的日期区间'], precision: ['Source precision', '来源时间精度'],
    timingUnknown: ['Timing is not established.', '时间尚未确定。'],
    registry: ['Registry schedule', '注册登记时间'], company: ['Company disclosure', '公司披露'],
    registryCaution: ['A registry completion date does not establish when results will be released.', '注册登记的完成日期不能确定结果公布时间。'],
    missingEconomic: ['The event’s economic exposure has not been established.', '事件的经济权益关系尚未确定。'],
    openStock: ['Open company research', '打开公司研究'],
    facts: ['Supplied record', '所提供的记录'], conflictTitle: ['Resolve the timing conflict first.', '先核实时间信息冲突。'],
    conflictRisk: ['The supplied timing is inconsistent. A current expectation cannot be established.', '所提供的时间信息存在冲突，暂时无法确定当前预期。'],
    conflictTask: ['Compare the source records before relying on a date.', '先对比来源记录，再使用时间判断。'],
    withdrawnTitle: ['This event is no longer an upcoming expectation.', '此事件不再属于待发生预期。'],
    withdrawnTask: ['Review the resolved event history.', '核查已结束事件的历史记录。'],
    supersededTitle: ['This version has been superseded.', '此版本已被后续版本替代。'],
    supersededTask: ['Load the current review before using this milestone.', '使用此关键事件前，请载入当前研究版本。'],
    supersededRisk: ['A newer version exists. This alone does not establish whether the event changed or ended.', '已存在后续版本。仅凭这一点无法判断事件是否变化或结束。'],
    historicalRecord: ['This is a historical event or revision record. It does not establish the current expectation.', '这是历史事件或版本记录，不能据此确定当前预期。'],
    pastTitle: ['Confirm whether the milestone occurred.', '确认关键事件是否已发生。'],
    pastTask: ['Check the source for an outcome or a revised timing window.', '核查来源是否已公布结果或更新预期时间。'],
    pastRisk: ['The supplied window has passed without a corroborated outcome in this review.', '所提供的时间窗口已过，但此研究事项尚未确认事件结果。'],
    staleTitle: ['Recheck the source before using this milestone.', '使用此关键事件前，请先重新核查来源。'],
    staleRisk: ['The source is not current in this review.', '此研究事项的来源状态并非最新。'],
    identityTask: ['Confirm the issuer before opening company research.', '打开公司研究前，请先确认发行人。'],
    identityRisk: ['The event has not been linked to one confirmed issuer.', '此事件尚未关联至已确认的唯一发行人。'],
    timingTask: ['Establish the timing from the source record.', '依据来源记录确认时间。'],
    reviewTask: ['Review the disclosed milestone and its supporting evidence.', '核查已披露的关键事件及其支持证据。'],
    evidenceRisk: ['A supporting source link is still needed.', '仍需支持此内容的来源链接。'],
    outcomeRisk: ['The eventual result and its investment impact remain uncertain.', '最终结果及其投资影响仍不确定。'],
    historyTitle: ['Review what the resolved event established.', '核查已结束事件能确认的事实。'],
    noChangeClaim: ['This milestone record does not include a verified before-and-after change.', '此关键事件记录未提供经过核实的前后变化。']
  };
  const FAMILY_COPY = {
    issuer_readout_guidance: ['Review the next disclosed clinical update.', '核查下一次已披露的临床进展。'],
    regulatory_target_disclosed: ['Prepare to review the regulatory milestone.', '准备核查监管关键事件。'],
    advisory_meeting_disclosed: ['Prepare to review the advisory meeting.', '准备核查咨询委员会会议。'],
    result_announced: ['Examine the announced results.', '审阅已公布的结果。'],
    regulatory_action: ['Review the regulatory action.', '核查监管行动。'],
    registry_primary_completion: ['Verify the primary completion schedule.', '核实主要研究完成时间。'],
    registry_study_completion: ['Verify the study completion schedule.', '核实研究完成时间。']
  };
  const LANES_COPY = {ACT_NOW: ['Review soon', '近期核查'], RECONCILE: ['Resolve an open question', '核实待解问题'],
    RESEARCH_NEXT: ['Research next', '后续研究'], MONITOR: ['Keep in view', '保持关注']};
  function presentation(row, page, locale = 'en') {
    const lang = locale.startsWith('zh') ? 1 : 0;
    const t = key => COPY[key][lang];
    const resolved = row.issuer.state === 'resolved';
    const symbols = row.issuer.securities.map(s => s.display_symbol);
    let title = FAMILY_COPY[row.event_family][lang], task = t('reviewTask');
    let risk = evidenceLinks(row).length ? t('outcomeRisk') : t('evidenceRisk');
    let restricted = false;
    if (!row.revision_is_current) {
      title = t('supersededTitle'); task = t('supersededTask'); risk = t('supersededRisk'); restricted = true;
    } else if (['cancelled', 'withdrawn'].includes(row.occurrence)) {
      title = t('withdrawnTitle'); task = t('withdrawnTask'); risk = t('noChangeClaim'); restricted = true;
    } else if (page.state === 'stale' || row.missingness.source.length) {
      title = t('staleTitle'); task = t('reviewTask'); risk = t('staleRisk'); restricted = true;
    } else if (row.timing.state === 'conflicted') {
      title = t('conflictTitle'); task = t('conflictTask'); risk = t('conflictRisk'); restricted = true;
    } else if (!resolved) {
      task = t('identityTask'); risk = t('identityRisk'); restricted = true;
    } else if (!row.timing.lower_date || !row.timing.upper_date) {
      task = t('timingTask'); risk = t('timingUnknown'); restricted = true;
    } else if (row.occurrence === 'uncorroborated' && row.timing.upper_date < page.anchor_date) {
      title = t('pastTitle'); task = t('pastTask'); risk = t('pastRisk'); restricted = true;
    } else if (row.occurrence === 'corroborated') title = t('historyTitle');
    return {title, task, risk, restricted, symbol: resolved && symbols.length ? symbols.join(' · ') : t(row.issuer.state === 'ambiguous' ? 'ambiguous' : 'unresolved'),
      lane: LANES_COPY[row.research_priority.lane][lang]};
  }

  let nextInstance = 0;
  function createDecisionDesk(options) {
    const root = options && options.root;
    need(root && root.ownerDocument && typeof root.replaceChildren === 'function', 'ROOT_REQUIRED');
    const doc = root.ownerDocument, locale = (options.locale || 'en').startsWith('zh') ? 'zh' : 'en';
    const t = key => COPY[key][locale === 'zh' ? 1 : 0];
    const id = 'bci-dd-' + (++nextInstance), controller = createController(options);
    let tab = 'setup', previousKey = null, returnKey = null, requestedTab = null;
    const caseTabs = ['setup', 'scenarios', 'research', 'sources'];
    function announceCase(key, selectedTab) {
      if (!options.onCaseChange) return;
      const row = controller.getState().page?.rows.find(r => rowKey(r) === key);
      options.onCaseChange(row ? Object.freeze({event_fact_ref: row.event_fact_ref,
        issuer_id: row.row_key.issuer_id, tab: selectedTab}) : null);
    }
    root.classList.add('bci-decision-desk'); root.lang = locale === 'zh' ? 'zh-CN' : 'en';
    function el(tag, className, text) {
      const n = doc.createElement(tag); if (className) n.className = className;
      if (text !== undefined) n.textContent = text; return n;
    }
    function button(text, action, className = 'bci-dd-button') {
      const n = el('button', className, text); n.type = 'button'; n.addEventListener('click', action); return n;
    }
    function field(label, content) {
      const n = el('section', 'bci-dd-field'); n.append(el('h4', '', label), el('p', '', content)); return n;
    }
    function link(href, label, intent) {
      const a = el('a', 'bci-dd-link', label); a.href = href;
      if (intent.kind === 'evidence') { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
      if (options.onNavigate) a.addEventListener('click', e => {
        if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault(); options.onNavigate(Object.freeze(Object.assign({href}, intent)));
      });
      return a;
    }
    function sourceSection(row) {
      const area = el('div', 'bci-dd-sources');
      const links = evidenceLinks(row);
      if (links.length) links.forEach(item => area.append(link(item.href, item.label + ' ↗', {kind: 'evidence'})));
      else area.append(field(t('sourceMissing'), t('sourceMissingBody')));
      area.append(field(t('wording'), row.timing.source_wording || t('noWording')));
      return area;
    }
    function draw(state) {
      const active = doc.activeElement;
      const focusKey = root.contains(active) && active.dataset ? active.dataset.focus : null;
      const hadDetail = previousKey !== null;
      if (state.selectedKey !== previousKey) { tab = requestedTab || 'setup'; requestedTab = null; }
      previousKey = state.selectedKey;
      const shell = el('div', 'bci-dd-shell'), header = el('header', 'bci-dd-header');
      const heading = el('div'); heading.append(el('p', 'bci-dd-eyebrow', t('eyebrow')), el('h2', '', t('title')), el('p', 'bci-dd-intro', t('intro')));
      const refresh = button(t('refresh') + ' ↻', () => controller.refresh()); refresh.dataset.focus = 'refresh';
      header.append(heading, refresh); shell.append(header);
      const toolbar = el('div', 'bci-dd-toolbar');
      const views = el('div', 'bci-dd-views'); views.setAttribute('role', 'group'); views.setAttribute('aria-label', t('view'));
      VIEWS.forEach(view => {
        const b = button(t(view), () => controller.refresh({view, horizon_days: view === 'upcoming' ? (state.query.horizon_days || 90) : null}), 'bci-dd-view');
        b.setAttribute('aria-pressed', String(state.query.view === view)); b.dataset.focus = 'view-' + view; views.append(b);
      });
      const label = el('label', 'bci-dd-horizon', t('horizon'));
      const select = el('select'); select.setAttribute('aria-label', t('horizon')); select.dataset.focus = 'horizon';
      HORIZONS.forEach(days => { const option = el('option', '', locale === 'zh' ? days + ' 天' : days + ' days'); option.value = String(days); option.selected = days === state.query.horizon_days; select.append(option); });
      select.addEventListener('change', () => controller.refresh({view: state.query.view, horizon_days: Number(select.value)}));
      label.append(select); toolbar.append(views); if (state.query.view === 'upcoming') toolbar.append(label); shell.append(toolbar);
      const body = el('div', 'bci-dd-body'); body.setAttribute('aria-busy', String(state.phase === 'loading'));
      const status = el('p', 'bci-dd-status'); status.setAttribute('role', 'status');
      if (!state.page) {
        const title = state.phase === 'loading' ? t('loading') : state.issue === 'ACCESS_REQUIRED' ? t('access') :
          state.issue === 'RELOAD_REQUIRED' ? t('reload') : state.issue === 'CONTEXT_CHANGED' ? t('context') :
          state.phase === 'idle' ? t('idle') : t('unavailable');
        status.textContent = title; body.append(status);
        if (state.phase === 'unavailable') body.append(el('p', 'bci-dd-muted', t(state.issue === 'RELOAD_REQUIRED' ? 'reloadBody' : 'unavailableBody')));
      } else {
        const page = state.page;
        const summary = el('div', 'bci-dd-summary');
        summary.append(el('h3', '', t('cases') + ' · ' + page.pagination.total));
        status.textContent = t('snapshot') + ' ' + page.evaluation_cutoff.replace('T', ' ').replace('Z', ' UTC'); summary.append(status); body.append(summary);
        if (page.state === 'partial' || page.state === 'stale') {
          const scopeLink = button(t(page.state === 'stale' ? 'stale' : 'partial'), () => {
            const scope = root.querySelector('.bci-dd-scope'); scope.open = true; scope.querySelector('summary').focus();
          }, 'bci-dd-text-button'); body.append(scopeLink);
        }
        const list = el('div', 'bci-dd-cases');
        page.rows.forEach(row => {
          const view = presentation(row, page, locale), key = rowKey(row);
          const card = el('article', 'bci-dd-card'); card.dataset.caseKey = key;
          const top = el('div', 'bci-dd-card-top'); top.append(el('span', 'bci-dd-symbol', view.symbol), el('span', 'bci-dd-lane', view.restricted ? t('reconcile') : view.lane));
          card.append(top, el('h3', 'bci-dd-case-title', view.title));
          // Restricted records retain evidence only behind the case detail.
          if (!view.restricted) card.append(el('p', 'bci-dd-wording', row.timing.source_wording || t('noWording')));
          card.append(field(t('task'), view.task), field(t('uncertainty'), view.risk));
          const open = button(t('case') + ' →', () => { returnKey = key; controller.open(key); announceCase(key, 'setup'); }, 'bci-dd-button bci-dd-primary');
          open.dataset.openKey = key; open.dataset.focus = 'open-' + key; card.append(open); list.append(card);
        });
        if (!page.rows.length) list.append(field(t('empty'), t('emptyBody')));
        body.append(list);
        if (page.pagination.next_cursor) { const more = button(state.more ? t('loading') : t('more'), controller.more); more.disabled = state.more; more.dataset.focus = 'more'; body.append(more); }
        const scope = el('details', 'bci-dd-scope'); scope.append(el('summary', '', t('scope')),
          el('p', '', t('scopeBody')), el('p', '', t('scopeOrder')),
          field(t('sourceCut'), page.input_cut.cutoff.replace('T', ' ').replace('Z', ' UTC')));
        body.append(scope);
      }
      shell.append(body);
      if (state.detail) {
        const dialog = el('section', 'bci-dd-detail'); dialog.setAttribute('role', 'region'); dialog.setAttribute('aria-labelledby', id + '-case-title');
        const title = el('h3', '', state.detail.phase === 'loaded' ? presentation(state.detail.payload.event, state.page, locale).symbol : t('case'));
        title.id = id + '-case-title'; title.tabIndex = -1; title.dataset.focus = 'case-heading';
        const top = el('div', 'bci-dd-detail-top');
        const close = button(t('close') + ' ×', () => { controller.close(); announceCase(null, null); }); close.dataset.focus = 'close'; top.append(title, close); dialog.append(top);
        if (state.detail.phase === 'loading') dialog.append(el('p', 'bci-dd-status', t('loading')));
        else {
          const row = state.detail.payload.event, view = presentation(row, state.page, locale);
          dialog.append(el('p', 'bci-dd-detail-title', view.title));
          const tabs = el('div', 'bci-dd-tabs'); tabs.setAttribute('role', 'tablist'); tabs.setAttribute('aria-label', t('case'));
          const keys = caseTabs;
          keys.forEach(key => {
            const b = button(t(key), () => { tab = key; draw(controller.getState()); announceCase(state.selectedKey, tab); }, 'bci-dd-tab');
            b.id = id + '-tab-' + key; b.dataset.focus = 'tab-' + key; b.dataset.tab = key;
            b.setAttribute('role', 'tab'); b.setAttribute('aria-selected', String(key === tab)); b.setAttribute('aria-controls', id + '-panel'); b.tabIndex = key === tab ? 0 : -1;
            b.addEventListener('keydown', event => {
              let index = keys.indexOf(key);
              if (event.key === 'ArrowRight') index = (index + 1) % keys.length;
              else if (event.key === 'ArrowLeft') index = (index + keys.length - 1) % keys.length;
              else if (event.key === 'Home') index = 0;
              else if (event.key === 'End') index = keys.length - 1;
              else return;
              event.preventDefault(); tab = keys[index]; draw(controller.getState()); root.querySelector('[data-tab="' + tab + '"]').focus(); announceCase(state.selectedKey, tab);
            }); tabs.append(b);
          });
          const panel = el('div', 'bci-dd-tab-panel'); panel.id = id + '-panel'; panel.setAttribute('role', 'tabpanel'); panel.setAttribute('aria-labelledby', id + '-tab-' + tab); panel.tabIndex = 0;
          if (tab === 'setup') {
            panel.append(field(t('task'), view.task), field(t('uncertainty'), view.risk));
            if (!view.restricted) panel.append(field(t('wording'), row.timing.source_wording || t('noWording')));
            if (row.event_family.startsWith('registry_')) panel.append(el('p', 'bci-dd-muted', t('registryCaution')));
            if (!view.restricted) stockLinks(row).forEach(item => panel.append(link(item.href, t('openStock') + ' · ' + item.symbol + ' ↗', {kind: 'stock', security_id: item.security_id})));
          } else if (tab === 'scenarios') panel.append(field(t('noEstimates'), t('noEstimatesBody')), field(t('uncertainty'), view.risk));
          else if (tab === 'sources') panel.append(sourceSection(row));
          else {
            panel.append(field(t('identity'), t('identityBody')), field(t('facts'), t(!row.revision_is_current || row.occurrence !== 'uncorroborated' ? 'historicalRecord' : 'noChangeClaim')),
              field(t('interval'), [row.timing.lower_date, row.timing.upper_date].filter(Boolean).join(' — ') || t('timingUnknown')),
              field(t('precision'), row.timing.precision), el('p', 'bci-dd-muted', t('missingEconomic')));
          }
          dialog.append(tabs, panel);
        }
        shell.append(dialog);
      }
      root.replaceChildren(shell);
      if (state.detail && !hadDetail) root.querySelector('[data-focus="case-heading"]').focus();
      else if (!state.detail && hadDetail) {
        const opener = Array.from(root.querySelectorAll('[data-open-key]')).find(n => n.dataset.openKey === returnKey);
        (opener || refresh).focus();
      } else if (focusKey) {
        const target = Array.from(root.querySelectorAll('[data-focus]')).find(n => n.dataset.focus === focusKey);
        if (target) target.focus();
      }
    }
    const unsubscribe = controller.subscribe(draw);
    const escape = event => { if (event.key === 'Escape' && controller.getState().detail) { event.preventDefault(); controller.close(); announceCase(null, null); } };
    root.addEventListener('keydown', escape);
    // The host maps its existing URL state to this method after loading a page.
    // No hash, router or history mutation is owned by this component.
    controller.openCase = ({event_fact_ref, issuer_id = null, tab: initialTab = 'setup'}) => {
      need(caseTabs.includes(initialTab), 'INVALID_TAB');
      const key = JSON.stringify([event_fact_ref, issuer_id]);
      if (!controller.getState().page?.rows.some(r => rowKey(r) === key)) return false;
      if (controller.getState().selectedKey === key) { tab = initialTab; draw(controller.getState()); }
      else { requestedTab = initialTab; returnKey = key; controller.open(key); }
      return true;
    };
    const destroy = controller.destroy;
    controller.destroy = () => { unsubscribe(); root.removeEventListener('keydown', escape); destroy(); root.replaceChildren(); root.classList.remove('bci-decision-desk'); };
    return controller;
  }
  return Object.freeze({createDecisionDesk, createController, validatePage, validateDetail, rowKey, stockLinks, evidenceLinks, presentation});
});
