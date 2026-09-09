/* Progressive enhancement only: the canonical assembler owns all evidence and scores. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const root = $('alert-center'), dialog = $('ac-detail');
  let data;
  try { data = JSON.parse($('ac-data').textContent); }
  catch (_) { $('ac-stale').hidden = false; $('ac-stale').textContent = document.documentElement.dataset.lang === 'zh' ? '交互证据无法载入，原始来源链接仍可使用。' : 'Interactive evidence could not load. The original source links remain available below.'; return; }
  const xp = data.explorer || {}, signals = xp.signals || [], history = xp.history || [];
  const byId = new Map(signals.map(a => [String(a.alert_id), a]));
  const topIds = new Set(data.top_ids || []), views = ['now', 'situations', 'signals', 'history'];
  const small = window.matchMedia('(max-width:1000px)');
  let limit = 8, returnId = '', state = {}, searchTimer;
  const zh = () => document.documentElement.dataset.lang === 'zh';
  const tr = (en, cn) => zh() ? (cn || en) : en;
  const field = (o, k) => String((zh() && o[k + '_zh']) || o[k] || '');
  const plain = s => String(s || '').replace(/^[\p{P}\p{S}\s]+/u, '').trim();
  const finite = v => typeof v === 'number' && Number.isFinite(v);
  const day = a => a.board_date || tr('Date unknown', '日期未知');
  const hasFilters = () => state.src !== 'all' || state.sev !== 'all' || state.cl !== 'all' || state.q || state.s;
  function node(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }
  function safeHref(value) {
    if (typeof value !== 'string' || !value.trim()) return null;
    try { const u = new URL(value, location.href); return u.origin === location.origin && /\.html$/.test(u.pathname) ? u.href : null; }
    catch (_) { return null; }
  }
  function readState() {
    const p = new URLSearchParams(location.hash.slice(1));
    const source = p.get('src') || 'all', topic = p.get('cl') || 'all';
    return {view: views.includes(p.get('view')) ? p.get('view') : 'now',
      sev: ['act', 'critical', 'major'].includes(p.get('sev')) ? p.get('sev') : 'all',
      cl: ['stress', 'regime', 'liquidity', 'rotation', 'single_name', 'other'].includes(topic) ? topic : 'all',
      q: ['new', 'recurring'].includes(p.get('q')) ? p.get('q') : '',
      s: (p.get('s') || '').slice(0, 300), src: source,
      id: (p.get('id') || '').slice(0, 128), evt: (p.get('evt') || '').slice(0, 100)};
  }
  function route(patch, replace) {
    Object.assign(state, patch);
    if (!state.id) state.evt = "";
    const p = new URLSearchParams();
    for (const key of ['view', 'sev', 'cl', 'q', 's', 'src', 'id', 'evt']) {
      if (state[key] && state[key] !== 'all' && !(key === 'view' && state[key] === 'now')) p.set(key, state[key]);
    }
    const url = location.pathname + location.search + (p.size ? '#' + p.toString() : '');
    window.history[replace ? 'replaceState' : 'pushState'](null, '', url);
    render();
  }
  function options(id, entries, value) {
    const el = $(id); el.replaceChildren();
    entries.forEach(([key, text]) => { const op = node('option', text); op.value = key; el.append(op); });
    if (!entries.some(([key]) => key === value)) { const op = node('option', tr('Source not in this snapshot', '此快照无该来源')); op.value = value; el.append(op); }
    el.value = value;
  }
  function labels() {
    options('ac-source', [['all', tr('All sources', '所有来源')], ...((data.coverage || {}).sources || xp.sources || []).filter(s => !(xp.restricted_sources || []).includes(s.source)).map(s => [s.source, field(s, 'label')])], state.src);
    options('ac-priority', [['all', tr('All priorities', '所有优先级')], ['act', tr('Review first', '优先查看')], ['critical', tr('Critical', '重要')], ['major', tr('Major', '较大变化')]], state.sev);
    options('ac-topic', [['all', tr('All topics', '所有主题')], ['stress', tr('Risk & credit', '风险与信用')], ['regime', tr('Regime changes', '环境变化')], ['liquidity', tr('Liquidity & rates', '流动性与利率')], ['rotation', tr('Sector rotation', '板块轮动')], ['single_name', tr('Single-name activity', '个股活动')], ['other', tr('Other', '其他')]], state.cl);
    $('ac-search').placeholder = tr('Ticker, change or keyword', '股票、变化或关键词');
    for (const [id, en, cn] of [['ac-search', 'Search alerts', '搜索警报'], ['ac-source', 'Source', '来源'], ['ac-priority', 'Priority', '优先级'], ['ac-topic', 'Topic', '主题'], ['ac-close', 'Close evidence', '关闭证据']]) $(id).setAttribute('aria-label', tr(en, cn));
    $('ac-search').value = state.s;
    if (state.sev !== 'all' || state.cl !== 'all' || state.q) $('ac-more-filters').open = true;
    root.querySelectorAll('[data-view]').forEach(b => b.setAttribute('aria-current', b.dataset.view === state.view ? 'page' : 'false'));
    root.querySelectorAll('[data-quick]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.quick === state.q)));
  }
  function matches(a, observed) {
    const record = observed || a;
    if (state.src !== 'all' && a.source !== state.src) return false;
    if (state.sev === 'act' && a.tier !== 'act') return false;
    if (state.sev === 'critical' && a.severity !== 'critical') return false;
    if (state.sev === 'major' && a.severity !== 'major') return false;
    if (state.cl !== 'all' && a.cluster !== state.cl) return false;
    if (state.q === 'new' && (!validDay(data.board_date) || record.board_date !== data.board_date)) return false;
    if (state.q === 'recurring' && a.lifecycle !== 'recurring') return false;
    const hay = [record.headline, record.headline_zh, record.detail, record.detail_zh, a.asset, a.type, a.source_label, a.source_label_zh].join(' ').toLocaleLowerCase();
    return !state.s || hay.includes(state.s.toLocaleLowerCase());
  }
  const eventClock = e => e.event_ts || e.event_date || e.board_date || 'unknown';
  function select(id, trigger, observed) { returnId = id; route({id, evt:observed ? eventClock(observed) : ''}); if (trigger) $('ac-close').focus(); }
  function signalRow(a, index, observed) {
    const r = node('button', undefined, 'acx-row'); r.type = 'button';
    r.dataset.alertId = a.alert_id; r.setAttribute('aria-haspopup', 'dialog'); r.setAttribute('aria-controls', 'ac-detail');
    r.setAttribute('aria-expanded', String(state.id === a.alert_id));
    const item = observed || a, main = node('span', undefined, 'acx-row-main');
    const meta = node('span', field(a, 'source_label') + ' · ' + day(item), 'acx-row-meta');
    main.append(meta, node('strong', plain(field(item, 'headline')) || tr('Untitled observation', '未命名记录')));
    if (!observed && a.fire_count > 1) main.append(node('span', tr('Re-fired ', '重复触发 ') + a.fire_count + (a.continuity_verified ? tr(' times · source reports continuity', ' 次 · 来源报告持续状态') : tr(' times · continuity not verified', ' 次 · 未验证持续性')), 'acx-row-sub'));
    const action = node('span', observed ? tr('Open history →', '查看历史 →') : a.tier === 'act' ? tr('Review first →', '优先查看 →') : tr('Investigate →', '查看证据 →'), 'acx-row-action');
    if (a.tier === 'act' && !observed) action.classList.add('is-priority');
    r.append(node('span', String(index + 1).padStart(2, '0'), 'acx-rank'), main, action);
    r.addEventListener('click', () => select(a.alert_id, true, observed)); return r;
  }
  function situationRow(s) {
    const wrap = node('section', undefined, 'acx-situation');
    const members = s.member_ids.map(id => byId.get(id)).filter(Boolean);
    const matching = members.filter(a => matches(a));
    wrap.append(node('h3', field(s, 'subject')),
      node('p', tr('Same explicit subject, ', '同一明确对象，') + matching.length + '/' + members.length + tr(' observations match. No claim of independent confirmation.', ' 条记录匹配；不代表独立确认。')));
    matching.forEach((a, i) => wrap.append(signalRow(a, i))); return wrap;
  }
  function render() {
    labels();
    const titles = {now:['Review queue','优先查看'], situations:['Related changes','相关变化'], signals:['All signals','全部信号'], history:['Observed firings','实际触发记录']};
    const notes = {now:['Original attention order — not trading instructions.','原有关注优先级，并非交易指令。'], situations:['Specific subjects, with the original observations side by side.','同一明确对象的不同记录，并列查看。'], signals:['The complete grouped population, beyond the capped review queue.','完整分组记录，不受优先列表数量上限影响。'], history:['Actual logged events. Dates do not imply continuous activity.','真实事件记录，日期不代表持续状态。']};
    $('ac-view-title').textContent = tr(...titles[state.view]); $('ac-view-note').textContent = tr(...notes[state.view]);
    let rows;
    if (state.view === 'situations') rows = (xp.situations || []).filter(s => s.member_ids.some(id => byId.has(id) && matches(byId.get(id))));
    else if (state.view === 'history') rows = history.filter(h => byId.has(h.alert_id) && matches(byId.get(h.alert_id), h));
    else rows = signals.filter(a => (state.view !== 'now' || hasFilters() || topIds.has(a.alert_id)) && matches(a));
    const selectedIndex = rows.findIndex(r => state.view === 'situations'
      ? r.member_ids.includes(state.id)
      : r.alert_id === state.id && (state.view !== 'history' || !state.evt || eventClock(r) === state.evt));
    if (selectedIndex >= limit) limit = selectedIndex + 1;
    const list = $('ac-results'); list.replaceChildren();
    rows.slice(0, limit).forEach((r, i) => list.append(state.view === 'situations' ? situationRow(r) : state.view === 'history' ? signalRow(byId.get(r.alert_id), i, r) : signalRow(r, i)));
    const empty = $('ac-noresults'); empty.hidden = rows.length > 0;
    if (!rows.length) {
      let title = tr('Nothing matches these filters','没有符合筛选条件的记录'), why = tr('Try another source, a wider topic, or reset the filters.','请切换来源、扩大主题范围或重置筛选。');
      if (!hasFilters()) { title = state.view === 'situations' ? tr('No related changes to bundle','暂无可归组的相关变化') : tr('No observations in this window','此时间段暂无记录'); why = state.view === 'situations' ? tr('Bundles require different observations about the same explicit subject. Individual signals remain available.','归组需要同一明确对象的不同记录，仍可浏览单条信号。') : tr('Check source coverage before drawing a market conclusion.','请先检查数据覆盖，不要据此判断市场。'); }
      const source = ((data.coverage || {}).sources || []).find(s => s.source === state.src);
      if (source && ['unavailable','no_coverage'].includes(source.state)) { title = tr('This source has no available coverage','该来源暂无可用覆盖'); why = tr('Other sources remain usable. Missing evidence is not a quiet market.','其他来源仍可使用；证据缺失不代表市场平静。'); }
      empty.querySelector('h3').textContent = title; empty.querySelector('p').textContent = why;
    }
    $('ac-count').textContent = String(rows.length) + (hasFilters() ? tr(' matching',' 条匹配') : tr(' observations',' 条记录'));
    $('ac-show-more').hidden = rows.length <= limit; $('ac-browse-all').hidden = state.view === 'signals';
    $('ac-result-status').textContent = rows.length ? tr('Showing ','已显示 ') + Math.min(limit, rows.length) + '/' + rows.length : '';
    const note = $('ac-filter-note'); note.hidden = true;
    if (state.view === 'history' && xp.history_truncated > 0) { note.hidden = false; note.textContent = tr('Published history contains the latest ','已发布历史包含最近 ') + history.length + '/' + xp.history_total + tr(' firings. Older records remain in the source log.',' 次触发；更早记录仍在原始日志中。'); }
    if (state.id && !byId.has(state.id)) { note.hidden = false; note.textContent = tr('The linked observation is not in this snapshot. It may have changed after a correction or moved outside the window.','此快照无对应记录，可能已修正或超出时间范围。'); }
    if (state.id && byId.has(state.id)) inspect(byId.get(state.id)); else if (dialog.open) dialog.close();
    freshness();
  }
  function section(parent, en, cn) { const s = node('section'); s.append(node('h3', tr(en, cn))); parent.append(s); return s; }
  function pairs(parent, entries) { const dl = node('dl'); entries.forEach(([key, value]) => dl.append(node('dt', key), node('dd', String(value)))); parent.append(dl); }
  function inspect(a) {
    const body = $('ac-detail-body'); body.replaceChildren();
    $('ac-share').href = location.href;
    body.append(node('p', field(a, 'source_label') + ' · ' + day(a), 'acx-eyebrow'));
    const title = node('h2', plain(field(a, 'headline'))); title.id = 'ac-detail-title'; body.append(title);
    if (state.evt) {
      const selectedEvents = history.filter(e => e.alert_id === a.alert_id && eventClock(e) === state.evt);
      const selected = section(body, 'Selected historical firing', '选中的历史触发');
      selected.dataset.selectedEvent = state.evt;
      if (!selectedEvents.length) selected.append(node('p', tr('This firing is not in the published history. It may be outside the cap or corrected; no substitute event is shown.','此触发不在已发布历史中，可能超出数量限制或已修正；不会以其他记录替代。')));
      selectedEvents.forEach(e => {
        selected.append(node('p', eventClock(e)), node('strong', plain(field(e, 'headline'))));
        if (field(e, 'detail')) selected.append(node('p', field(e, 'detail')));
        pairs(selected, [[tr('Source observation','来源观测'), e.source_asof || tr('Not supplied','未提供')],
          [tr('Recorded by source','来源记录时间'), e.recorded_at || tr('Not supplied','未提供')]]);
      });
      selected.append(node('p', tr('The following source summary and validation describe the current snapshot, not a reconstructed historical score.','下方摘要与验证描述当前快照，不是重建的历史评分。')));
      body.append(node('h3', tr('Current signal summary', '当前信号摘要')));
    }
    if (field(a, 'detail')) body.append(node('p', field(a, 'detail')));
    const href = safeHref(a.link);
    if (href) { const link = node('a', tr('Open original evidence →', '打开原始证据 →'), 'acx-text-link'); link.href = href; body.append(link); }
    else body.append(node('p', tr('A verified source link is not available.','暂无已确认的来源链接。')));
    const clocks = section(body, 'When this happened', '事件时间');
    pairs(clocks, [[tr('Event time / date','事件时间 / 日期'), a.event_ts || a.event_date || a.board_date || tr('Unknown','未知')], [tr('Source observation','来源观测'), a.source_asof || tr('Not supplied','未提供')], [tr('Recorded by source','来源记录时间'), a.recorded_at || tr('Not supplied','未提供')]]);
    clocks.append(node('p', a.date_precision === 'date' ? tr('The source provides a session date, not an intraday timestamp.','来源仅提供交易日，并无日内时间。') : tr('Build time is separate from the event clock.','生成时间与事件时间不同。')));
    const v = a.validation || {}, validation = section(body, 'How much evidence?', '证据有多充分？');
    const verdictLabels = {
      backtested:['Backtested family','已回测的信号类别'], scored:['Scored family','已计分的信号类别'],
      confirmer:['Context confirmer — not a standalone timing signal','背景确认项，并非独立择时信号'],
      calibrated:['Source reports calibration — inspect its limits','来源报告已校准，请核查适用范围'],
      no_edge:['TESTED · NO EDGE','已检验 · 无边际'], underpowered:['INSUFFICIENT SAMPLE','样本不足'],
      documented:['Not separately backtested','未单独回测'], display:['Context only','仅作背景'],
      killed:['NO-GO · rejected','否决 · 不应使用']
    };
    const key = Object.prototype.hasOwnProperty.call(verdictLabels, v.verdict) ? v.verdict : 'unknown';
    const verdict = node('p', key === 'unknown' ? tr('Validation not available','暂无验证结果') : tr(...verdictLabels[key]), 'acx-validation');
    verdict.dataset.validationVerdict = key;
    validation.append(verdict);
    if (v.scorecard_name) validation.append(node('p', String(v.scorecard_name)));
    const metrics = [];
    if (finite(v.hit) && v.hit >= 0 && v.hit <= 1) metrics.push([tr('Historical hit rate','历史命中率'), (v.hit * 100).toFixed(1) + '%']);
    if (finite(v.ic)) metrics.push(['IC', v.ic.toFixed(3)]);
    if (finite(v.dsr)) metrics.push(['DSR', v.dsr.toFixed(3)]);
    if (finite(v.n)) metrics.push([tr('Historical observations','历史样本'), v.n]);
    if (v.horizon) metrics.push([tr('Study horizon','研究周期'), v.horizon]);
    if (metrics.length) pairs(validation, metrics);
    for (const pair of v.extra || []) if (Array.isArray(pair) && pair.length === 2) pairs(validation, [pair]);
    if (field(v, 'note')) { validation.append(node('h3', tr('Source research note', '来源研究说明')), node('p', field(v, 'note'))); }
    const validationHref = safeHref(v.link);
    if (validationHref) { const link = node('a', tr('Inspect the study →','查看研究 →'), 'acx-text-link'); link.href = validationHref; validation.append(link); }
    validation.append(node('p', tr('A family-level study is not a probability for this individual alert.','类别研究并非此条警报的成功概率。')));
    const priority = section(body, 'Why it is in this position', '为何排在此处');
    priority.append(node('p', tr('Attention priority ','关注优先级 ') + (finite(a.priority) ? a.priority : '—') + tr(' · not a trading score',' · 并非交易评分')));
    const names = {conviction:['Source tier','来源等级'], severity:['Severity','严重程度'], recency:['Event recency','事件时间'], cross_asset:['Cross-asset context','跨资产背景']};
    pairs(priority, Object.entries(a.priority_components || {}).map(([k, val]) => [names[k] ? tr(...names[k]) : k, Array.isArray(val) ? val[0] : tr('Not supplied','未提供')]));
    const related = (xp.situations || []).find(s => s.member_ids.includes(a.alert_id));
    if (related) { const sec = section(body, 'Related observations', '相关记录'); sec.append(node('p', tr('Same explicit subject, not independent confirmation.','同一明确对象，不代表独立确认。'))); related.member_ids.filter(id => id !== a.alert_id && byId.has(id)).forEach(id => { const b = node('button', plain(field(byId.get(id), 'headline')), 'acx-text-link'); b.type = 'button'; b.addEventListener('click', () => select(id, false)); sec.append(b); }); }
    const h = history.filter(e => e.alert_id === a.alert_id), observed = section(body, 'Observed history', '实际事件历史');
    observed.append(node('p', Math.min(30, h.length) + '/' + (a.fire_count || h.length) + tr(' logged firings shown. Gaps are not continuous activity.',' 次触发记录；记录间隔不代表持续状态。')));
    h.slice(0, 30).forEach(e => { const line = node('div', undefined, 'acx-history-entry'), time = node('time', e.event_ts || e.event_date || e.board_date || tr('Date unknown','日期未知')); if (e.event_ts || e.event_date) time.dateTime = e.event_ts || e.event_date; line.append(time, node('span', plain(field(e, 'headline')))); observed.append(line); });
    if (h.length > 30) observed.append(node('p', tr('Showing the 30 most recent records. Browse History for the full published set.','此处显示最近 30 条记录，请到历史记录页查看已发布的完整集合。')));
    if (!h.length) observed.append(node('p', tr('No individual firing records are available in this projection. First/last dates alone are not a timeline.','此投影暂无逐次触发记录；首末日期不等于完整时间线。')));
    if (!dialog.open) dialog.showModal();
  }
  function closeDetail() {
    const id = returnId || state.id; route({id:''});
    const button = Array.from($('ac-results').querySelectorAll('[data-alert-id]')).find(b => b.dataset.alertId === id);
    if (button) button.focus(); else $('ac-view-title').focus();
  }
  function validDay(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const instant = new Date(value + 'T00:00:00Z');
    return Number.isFinite(instant.valueOf()) && instant.toISOString().slice(0, 10) === value;
  }
  function freshness() {
    const note = $('ac-stale');
    const parts = new Intl.DateTimeFormat('en-US', {timeZone:'America/New_York', year:'numeric', month:'2-digit', day:'2-digit'}).formatToParts(new Date());
    const get = type => parts.find(p => p.type === type).value;
    const today = get('year') + '-' + get('month') + '-' + get('day');
    note.hidden = validDay(data.board_date) && data.board_date === today;
    if (!validDay(data.board_date)) note.textContent = tr('Snapshot date unavailable — freshness cannot be verified. Original event dates remain visible.','快照日期不可用，无法确认新鲜度。原始事件日期仍可查看。');
    else if (data.board_date > today) note.textContent = tr('Snapshot day is in the future — do not treat this page as a current market reading.','快照日期晚于当前日期，请勿将其视为当前市场读数。');
    else note.textContent = tr('This page is a snapshot from ','此页面为 ') + data.board_date + tr('. Relative dates refer to that New York session. Refresh to check for a newer publication.',' 的快照；相对日期依据该纽约交易日。刷新可检查是否有新发布。');
  }
  function reset() {
    clearTimeout(searchTimer); limit = state.view === 'now' ? 8 : 25;
    route({src:'all', sev:'all', cl:'all', q:'', s:'', id:''});
  }
  root.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => {
    limit = b.dataset.view === 'now' ? 8 : 25; route({view:b.dataset.view, id:''});
  }));
  $('ac-filters').addEventListener('submit', e => {
    e.preventDefault(); clearTimeout(searchTimer);
    route({s:$('ac-search').value, view:state.view === 'now' ? 'signals' : state.view, id:''});
  });
  $('ac-search').addEventListener('input', e => {
    const s = e.target.value.slice(0,300); state.s = s; clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { limit = 25; route({s, view:state.view === 'now' ? 'signals' : state.view, id:''}, true); }, 160);
  });
  for (const [id, key] of [['ac-source','src'], ['ac-priority','sev'], ['ac-topic','cl']]) {
    $(id).addEventListener('change', e => { limit = 25; route({[key]:e.target.value, view:state.view === 'now' ? 'signals' : state.view, id:''}); });
  }
  $('ac-reset').addEventListener('click', reset);
  $('ac-reset-empty').addEventListener('click', reset);
  $('ac-show-more').addEventListener('click', () => { limit += 25; render(); });
  $('ac-browse-all').addEventListener('click', () => { limit = 25; route({view:'signals', id:''}); });
  $('ac-close').addEventListener('click', closeDetail);
  dialog.addEventListener('cancel', e => { e.preventDefault(); closeDetail(); });
  root.querySelectorAll('[data-quick]').forEach(b => b.addEventListener('click', () => {
    limit = 25; route({q:state.q === b.dataset.quick ? '' : b.dataset.quick, view:state.view === 'now' ? 'signals' : state.view, id:''});
  }));
  root.querySelectorAll('a[href="#coverage"]').forEach(a => a.addEventListener('click', e => {
    e.preventDefault(); $('coverage').open = true; $('coverage').scrollIntoView({block:'start'});
  }));
  window.addEventListener('hashchange', () => {
    state = readState(); limit = state.view === 'now' ? 8 : 25; render();
    if (location.hash === '#coverage') $('coverage').open = true;
  });
  new MutationObserver(() => render()).observe(document.documentElement, {attributes:true, attributeFilter:['data-lang']});
  state = readState(); limit = state.view === 'now' ? 8 : 25; render();
  root.classList.add('acx-enhanced');
  if (location.hash === '#coverage') $('coverage').open = true;
})();
