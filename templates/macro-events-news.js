/* R2 progressive enhancement of the existing dlg-news component.
   No fetch, storage, subscription, timer, score or second modal manager.
   The mx5 host owns opening, closing, inertness, trapping focus and page scroll.
   Source rows are MOVED into details and restored, never cloned into new alerts. */
(function () {
  'use strict';
  var root = document.getElementById('dlg-news');
  if (!root || !root.classList.contains('nd-desk') || root.dataset.ndReady) return;
  var $ = function (selector) { return root.querySelector(selector); };
  var all = function (selector) { return Array.from(root.querySelectorAll(selector)); };
  var tools = $('.nd-tools'), search = $('#nd-search'), body = $('.nd-body');
  var grid = $('.nd-grid'), empty = $('[data-nd-no-results]'), footer = $('.nd-footer');
  var following = $('.nd-following'), detail = $('.nd-detail');
  var back = $('[data-nd-back]'), detailRecord = $('[data-nd-detail-record]');
  var detailTitle = $('#nd-detail-title'), facts = $('[data-nd-detail-facts]');
  var kindFilter = $('[data-nd-kind-filter]'), publisherFilter = $('[data-nd-publisher-filter]');
  var tabs = all('[data-nd-mode]'), sections = all('[data-nd-section]'), items = all('[data-nd-item]');
  var modes = ['briefing', 'releases', 'stories', 'following'];
  if (!tools || !search || !body || !grid || !empty || !following || !detail || !back ||
      !detailRecord || !detailTitle || !facts || !kindFilter || !publisherFilter || tabs.length !== 4) return;
  var mode = 'briefing', origin = null, observer = null, busy = false;
  var limits = {review: 1, calendar: 2, news: 2, context: 1};
  var states = Object.create(null), records = new Map(), publishers = [];
  modes.forEach(function (key) { states[key] = {query: '', filter: 'all', publisher: 'all', scroll: 0, filtersOpen: false, expanded: {}}; });

  function zh() { return document.documentElement.getAttribute('data-lang') === 'zh'; }
  function word(en, cn) { return zh() ? cn : en; }
  function text(node, value) { if (node && node.textContent !== String(value)) node.textContent = String(value); }
  function element(tag, className, value) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = value;
    return node;
  }
  function normalize(value) { return String(value || '').normalize('NFKC').toLocaleLowerCase().replace(/\s+/g, ' ').trim(); }
  function localized(node) {
    if (!node) return '';
    var language = node.querySelector(zh() ? '.l-zh' : '.l-en');
    return (language || node).textContent.trim();
  }
  function titleFor(item) { return localized(item.querySelector('.nd-item-title,h4')); }
  function tabLabel(key) { return localized(tabs.find(function (tab) { return tab.dataset.ndMode === key; })); }
  function inScope(kind) { return mode === 'briefing' || (mode === 'releases' && kind === 'calendar') || (mode === 'stories' && kind === 'news'); }
  function option(select, value, label) { var node = element('option', '', label); node.value = value; select.appendChild(node); }
  function configureFilters() {
    var state = states[mode];
    kindFilter.replaceChildren();
    option(kindFilter, 'all', word('All records', '全部记录'));
    if (mode === 'briefing') {
      option(kindFilter, 'review', word('Priority changes', '优先变化'));
      option(kindFilter, 'calendar', word('Scheduled events', '已排期事件'));
      option(kindFilter, 'news', word('Stories', '新闻'));
      option(kindFilter, 'context', word('Context observations', '背景观察'));
    } else if (mode === 'releases') {
      option(kindFilter, 'scheduled', word('Scheduled releases', '数据公布日程'));
      option(kindFilter, 'major', word('Major releases', '重要数据公布'));
      option(kindFilter, 'context', word('Calendar context', '日历背景'));
    } else if (mode === 'stories') {
      option(kindFilter, 'linked', word('Source link supplied', '已提供来源链接'));
      option(kindFilter, 'unlinked', word('Source link missing', '缺少来源链接'));
    }
    kindFilter.value = state.filter;
    publisherFilter.replaceChildren();
    option(publisherFilter, 'all', word('All publishers', '全部发布者'));
    publishers.forEach(function (name, index) { option(publisherFilter, String(index), name || word('Publisher unavailable', '发布者未提供')); });
    publisherFilter.value = state.publisher;
    $('[data-nd-publisher-filter-label]').hidden = mode !== 'stories';
    $('.nd-filter-row').hidden = mode === 'following' || !state.filtersOpen;
    $('[data-nd-filter-toggle]').setAttribute('aria-expanded', String(state.filtersOpen));
    var active = (state.filter !== 'all' ? 1 : 0) + (state.publisher !== 'all' ? 1 : 0);
    text($('[data-nd-filter-toggle]'), word('Filters', '筛选') + (active ? ' (' + active + ')' : ''));
    $('.nd-search-row').hidden = mode === 'following';
    search.value = state.query;
  }
  function filterMatches(item, record, filter) {
    if (filter === 'all') return true;
    if (mode === 'briefing') return record.kind === filter;
    if (mode === 'releases') return filter === 'scheduled' ? record.scheduled : filter === 'major' ? record.major : !record.scheduled;
    if (mode === 'stories') return filter === 'linked' ? record.linked : !record.linked;
    return true;
  }
  function indexItems() {
    items.forEach(function (item) {
      var nodes = item.querySelectorAll('.nd-item-title,.nd-change,h4,.nd-item-meta,.nd-story-meta,.nd-event-full-date,.nd-event-date');
      var dates = Array.from(item.querySelectorAll('[data-nd-date]')).map(function (node) { return node.dataset.ndDate; });
      records.get(item).haystack = normalize(Array.from(nodes).map(function (node) { return node.textContent; }).concat(dates).join(' '));
    });
  }
  function apply() {
    if (origin) return;
    var state = states[mode], query = normalize(state.query), words = query.split(' ').filter(Boolean);
    var matched = {review: 0, calendar: 0, news: 0, context: 0};
    var shown = {review: 0, calendar: 0, news: 0, context: 0}, total = 0;
    var filtered = Boolean(query) || state.filter !== 'all' || state.publisher !== 'all';
    items.forEach(function (item) {
      var record = records.get(item), kind = record.kind, scope = inScope(kind);
      if (scope) total += 1;
      var hit = scope && filterMatches(item, record, state.filter) &&
        (mode !== 'stories' || state.publisher === 'all' || String(record.publisher) === state.publisher) &&
        words.every(function (part) { return record.haystack.includes(part); });
      if (hit) matched[kind] += 1;
      var visible = hit && (mode !== 'briefing' || filtered || state.expanded[kind] || shown[kind] < limits[kind]);
      item.hidden = !visible;
      if (visible) shown[kind] += 1;
    });
    sections.forEach(function (section) {
      var kind = section.dataset.ndSection;
      // A missing source keeps its warning even when loaded rows do not match.
      section.hidden = !inScope(kind) || (filtered && matched[kind] === 0 && total > 0 && section.dataset.ndSourceState !== 'unavailable');
      var more = section.querySelector('[data-nd-more]');
      if (more) more.hidden = section.hidden || matched[kind] <= shown[kind];
    });
    tabs.forEach(function (tab) {
      var selected = tab.dataset.ndMode === mode;
      tab.classList.toggle('is-selected', selected);
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    var count = Object.values(shown).reduce(function (sum, value) { return sum + value; }, 0);
    var result = $('.nd-result-count');
    text(result, word(count + ' of ' + total + ' loaded records shown', '显示 ' + count + ' / ' + total + ' 条已加载记录'));
    result.hidden = mode === 'following';
    empty.hidden = mode === 'following' || !filtered || total === 0 || count > 0;
    grid.hidden = mode === 'following';
    following.hidden = mode !== 'following';
    footer.hidden = false;
    body.setAttribute('aria-labelledby', 'nd-tab-' + mode);
    root.classList.toggle('nd-single-view', mode !== 'briefing');
    root.classList.toggle('nd-searching', filtered);
    root.dataset.ndTask = mode;
  }
  function restoreRecord(focus) {
    if (!origin) return;
    var previous = origin;
    previous.anchor.replaceWith(previous.item);
    previous.item.classList.remove('nd-detail-selected');
    previous.disclosures.forEach(function (entry) { entry[0].open = entry[1]; });
    previous.item.querySelector('[data-nd-inspect]').hidden = false;
    origin = null;
    detail.hidden = true;
    root.classList.remove('nd-reading-detail');
    $('.nd-search-row').hidden = mode === 'following';
    configureFilters();
    apply();
    body.scrollTop = previous.scroll;
    if (focus && previous.opener.isConnected) previous.opener.focus({preventScroll: true});
  }
  function selectMode(next, focusTab, clear) {
    if (!modes.includes(next)) return;
    restoreRecord(false);
    states[mode].scroll = body.scrollTop;
    mode = next;
    if (clear) states[mode] = {query: '', filter: 'all', publisher: 'all', scroll: 0, filtersOpen: false, expanded: {}};
    configureFilters(); apply(); body.scrollTop = states[mode].scroll;
    if (focusTab) tabs.find(function (tab) { return tab.dataset.ndMode === mode; }).focus({preventScroll: true});
  }
  function fact(label, value) {
    facts.appendChild(element('dt', '', label));
    facts.appendChild(element('dd', '', value || word('Not supplied', '未提供')));
  }
  function detailCopy() {
    if (!origin) return;
    var item = origin.item, record = records.get(item), kind = record.kind;
    text(back, word('← Back to ', '← 返回') + tabLabel(mode));
    text(detailTitle, titleFor(item));
    text($('[data-nd-detail-kind]'), kind === 'news' ? word('STORY / SOURCE EVIDENCE', '新闻 / 来源依据') : kind === 'calendar' ? word('RELEASE / SCHEDULE CONTEXT', '数据公布 / 日程背景') : word('CHANGE / OBSERVATION', '变化 / 观察'));
    facts.replaceChildren();
    if (kind === 'news') {
      text($('[data-nd-detail-note]'), word('A source report, not independently verified fact or a validated trading signal. Repeated reporting is not independent confirmation.', '这是来源报道，并非独立核实的事实或经过验证的交易信号。重复报道不等于独立确认。'));
      fact(word('Publisher', '发布者'), record.publisherName);
      fact(word('Published · source clock', '发布时间 · 来源时钟'), item.dataset.ndPublished);
      fact(word('Seen · source clock', '采集时间 · 来源时钟'), item.dataset.ndSeen);
      fact(word('First seen · ledger clock', '首次采集 · 记录时钟'), item.dataset.ndFirstSeen);
      fact(word('Source event identity', '来源事件标识'), item.dataset.ndSourceId);
      fact(word('Correction lineage', '更正沿革'), word('Not supplied to this component', '此组件未收到此项数据'));
    } else if (kind === 'calendar') {
      text($('[data-nd-detail-note]'), word('Scheduled does not mean published. A passed date does not establish an official result or explain a market move.', '已排期不等于已公布。日期已过并不能确认官方结果，也不能解释市场走势。'));
      fact(word('Schedule date', '排期日期'), (item.querySelector('[data-nd-date]') || {}).textContent);
      fact(word('Scheduled time', '排期时间'), (item.querySelector('.nd-event-time') || {}).textContent);
      var officialPanel = item.querySelector('[data-nd-official-count]');
      var officialCount = officialPanel ? Number(officialPanel.dataset.ndOfficialCount) : 0;
      fact(word('Official actual', '官方公布值'), officialCount > 0 ? word(officialCount + ' measure(s) in the result panel', '结果面板内有 ' + officialCount + ' 项指标') : '');
      if (officialCount > 0) {
        text($('[data-nd-detail-kind]'), word('RELEASE / OFFICIAL RESULT', '数据公布 / 官方结果'));
        text($('[data-nd-detail-note]'), word('Exact first-result receipts match this release and evidence cutoff. They do not establish a consensus surprise or explain the market reaction.', '首次公布值的凭据与此数据公布及证据截止时间精确匹配，但不能据此确认超出共识的幅度或解释市场反应。'));
        fact(word('Evidence cutoff', '证据截止时间'), officialPanel.dataset.ndEvidenceAsof);
      }
      fact(word('Matching consensus', '同口径共识值'), '');
      fact(word('Observed reaction series', '观察到的市场反应序列'), '');
    } else {
      text($('[data-nd-detail-note]'), word('Review the source observation and its limitations. This view does not upgrade a warning into a confirmed market phase or grant permission to trade.', '请核查来源观察及其局限。此视图不会将预警升级为已确认的市场阶段，也不授予交易权限。'));
      fact(word('Observation date', '观察日期'), (item.querySelector('[data-nd-date]') || {}).textContent);
      fact(word('Evidence scope', '依据范围'), word('Only fields supplied with this source record', '仅限此来源记录提供的字段'));
    }
  }
  function inspect(item, opener) {
    if (origin || !records.has(item)) return;
    var anchor = document.createComment('nd-origin');
    var scroll = body.scrollTop;
    states[mode].scroll = scroll;
    item.before(anchor);
    origin = {item: item, opener: opener, anchor: anchor, scroll: scroll, disclosures: Array.from(item.querySelectorAll('details')).map(function (node) { return [node, node.open]; })};
    origin.disclosures.forEach(function (entry) { if (!entry[0].hasAttribute('data-nd-provenance')) entry[0].open = true; });
    detailRecord.appendChild(item);
    item.hidden = false; item.classList.add('nd-detail-selected'); opener.hidden = true;
    grid.hidden = true; following.hidden = true; empty.hidden = true; footer.hidden = true;
    $('.nd-search-row').hidden = true; $('.nd-filter-row').hidden = true;
    detailCopy(); detail.hidden = false; root.classList.add('nd-reading-detail');
    body.scrollTop = 0; detailTitle.focus({preventScroll: true});
  }

  // Date-only values retain the producer's civil day, independent of client zone.
  function civil(value) {
    var match = /^(\d{4})-(\d{2})-(\d{2})(?:$|[ T])/.exec(String(value || ''));
    if (!match) return null;
    var year = Number(match[1]), month = Number(match[2]), day = Number(match[3]);
    var date = new Date(0); date.setUTCFullYear(year, month - 1, day); date.setUTCHours(12, 0, 0, 0);
    if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
    return {date: date, iso: match[1] + '-' + match[2] + '-' + match[3]};
  }
  // Only the generated_utc contract permits a suffix-less timestamp as UTC.
  function utcStamp(value) {
    var match = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})(?::(\d{2})(\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2}|\s*UTC)?$/.exec(String(value || '').trim());
    if (!match || !civil(match[1]) || Number(match[2]) > 23 || Number(match[3]) > 59 || Number(match[4] || 0) > 59) return null;
    var zone = match[6] || 'Z';
    if (/UTC/.test(zone)) zone = 'Z';
    if (zone !== 'Z') { var h = Number(zone.slice(1, 3)), m = Number(zone.slice(4)); if (h > 14 || m > 59 || (h === 14 && m)) return null; }
    var stamp = new Date(match[1] + 'T' + match[2] + ':' + match[3] + ':' + (match[4] || '00') + (match[5] || '') + zone);
    return Number.isFinite(stamp.getTime()) ? stamp : null;
  }
  function dateLabels() {
    var locale = zh() ? 'zh-CN' : 'en-US';
    search.placeholder = search.getAttribute(zh() ? 'data-placeholder-zh' : 'data-placeholder-en');
    all('[data-nd-aria-en]').forEach(function (node) { node.setAttribute('aria-label', node.getAttribute(zh() ? 'data-nd-aria-zh' : 'data-nd-aria-en')); });
    var dayFormat = new Intl.DateTimeFormat(locale, {year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC'});
    var stampFormat = new Intl.DateTimeFormat(locale, {year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: 'UTC'});
    all('[data-nd-date]').forEach(function (node) {
      var raw = node.dataset.ndDate, day = civil(raw), isUtc = node.dataset.ndDateKind === 'utc';
      var stamp = isUtc ? utcStamp(raw) : null;
      node.title = raw; node.removeAttribute('datetime');
      if (stamp) { text(node, stampFormat.format(stamp)); node.dateTime = stamp.toISOString(); }
      else if (day && !isUtc) { text(node, dayFormat.format(day.date)); node.dateTime = day.iso; }
      else text(node, raw || word('Date unavailable', '日期未提供'));
    });
    var parts = new Intl.DateTimeFormat('en-US', {year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'America/New_York'}).formatToParts(new Date());
    var part = function (type) { return parts.find(function (p) { return p.type === type; }).value; };
    var today = part('year') + '-' + part('month') + '-' + part('day');
    all('[data-nd-calendar-date]').forEach(function (node) {
      var day = civil(node.dataset.ndCalendarDate);
      if (!day) return;
      text(node.querySelector('[data-nd-month]'), new Intl.DateTimeFormat(locale, {month: 'short', timeZone: 'UTC'}).format(day.date));
      text(node.querySelector('[data-nd-day]'), day.date.getUTCDate());
      var past = node.closest('.nd-event').querySelector('.nd-past-date');
      if (past) past.hidden = day.iso >= today;
    });
    var clock = $('.nd-snapshot [data-nd-date-kind="utc"]'), built = clock && utcStamp(clock.dataset.ndDate);
    var stale = $('[data-nd-stale]'), age = built ? Date.now() - built.getTime() : null;
    root.dataset.ndClockState = !clock ? 'unknown' : !built ? 'invalid' : age < -300000 ? 'future' : age > 172800000 ? 'stale' : 'current';
    if (stale) {
      var state = root.dataset.ndClockState;
      stale.hidden = state === 'current' || state === 'unknown';
      text(stale, state === 'invalid' ? word('The build timestamp could not be validated. Freshness is unknown; inspect the source dates.', '无法验证生成时间，数据新鲜度未知。请核查各项来源日期。') : state === 'future' ? word('The build timestamp is ahead of this clock. Freshness is unconfirmed; inspect the source dates.', '生成时间晚于当前时钟，新鲜度尚未确认。请核查来源日期。') : word('This snapshot is more than two days old. Check the dated sources; scheduled dates may have passed.', '此快照已超过两天。请核查来源日期，日程日期可能已过。'));
    }
    items.forEach(function (item) {
      var kind = records.get(item).kind;
      text(item.querySelector('[data-nd-inspect]'), kind === 'news' ? word('Read story →', '查看新闻 →') : kind === 'calendar' ? word('Inspect release →', '查看数据公布 →') : word('Review change →', '核查变化 →'));
    });
  }
  function fallback() {
    // A broken enhancement preserves ALL server-rendered evidence and native disclosures.
    if (origin) { origin.anchor.replaceWith(origin.item); origin = null; }
    if (observer) observer.disconnect();
    items.forEach(function (item) { item.hidden = false; item.classList.remove('nd-detail-selected'); var b = item.querySelector('[data-nd-inspect]'); if (b) b.remove(); });
    sections.forEach(function (section) { section.hidden = false; });
    all('[data-nd-more]').forEach(function (button) { button.hidden = true; });
    $('.nd-search-row').appendChild($('.nd-result-count'));
    tools.hidden = true; empty.hidden = true; following.hidden = true; detail.hidden = true; grid.hidden = false; footer.hidden = false;
    root.classList.remove('nd-enhanced', 'nd-single-view', 'nd-searching', 'nd-reading-detail');
    root.dataset.ndReady = 'failed';
    body.removeAttribute('role'); body.removeAttribute('aria-labelledby');
  }
  function guard(action) {
    return function (event) {
      if (root.dataset.ndReady === 'failed' || busy) return;
      busy = true;
      try { action(event); } catch (error) { fallback(); } finally { busy = false; }
    };
  }
  try {
    items.forEach(function (item) {
      var publisher = item.querySelector('.nd-publisher');
      var publisherName = publisher && !publisher.querySelector('.l-en,.l-zh') ? publisher.textContent.trim() : '';
      var pindex = publishers.indexOf(publisherName);
      if (item.dataset.ndItem === 'news' && pindex === -1) { pindex = publishers.length; publishers.push(publisherName); }
      records.set(item, {kind: item.dataset.ndItem, scheduled: item.classList.contains('nd-event'), major: Boolean(item.querySelector('.nd-tag-calendar')), linked: Boolean(item.querySelector('h4 a[href]')), publisherName: publisherName, publisher: pindex, haystack: ''});
      var button = element('button', 'nd-text-link nd-inspect'); button.type = 'button'; button.dataset.ndInspect = '';
      (item.querySelector('.nd-event-content') || item).appendChild(button);
      button.addEventListener('click', guard(function () { inspect(item, button); }));
    });
    tabs.forEach(function (tab) { tab.addEventListener('click', guard(function () { selectMode(tab.dataset.ndMode, false, false); })); });
    $('.nd-tabs').addEventListener('keydown', guard(function (event) {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      var index = tabs.indexOf(document.activeElement); if (index < 0) return;
      event.preventDefault();
      var next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
      tabs.forEach(function (tab, i) { tab.tabIndex = i === next ? 0 : -1; });
      tabs[next].focus({preventScroll: true}); tabs[next].scrollIntoView({block: 'nearest', inline: 'nearest'});
    }));
    all('[data-nd-more]').forEach(function (button) {
      button.addEventListener('click', guard(function () {
        var kind = button.dataset.ndMore;
        if (kind === 'calendar' || kind === 'news') selectMode(kind === 'calendar' ? 'releases' : 'stories', true, true);
        else {
          states[mode].expanded[kind] = true;
          var scroll = body.scrollTop; apply(); body.scrollTop = scroll;
          var section = button.closest('[data-nd-section]');
          var first = section.querySelector('[data-nd-inspect]'); if (first) first.focus({preventScroll: true});
        }
      }));
    });
    all('[data-nd-reset]').forEach(function (button) {
      button.addEventListener('click', guard(function () {
        states[mode].query = ''; states[mode].filter = 'all'; states[mode].publisher = 'all';
        configureFilters(); apply(); body.scrollTop = 0; search.focus({preventScroll: true});
      }));
    });
    search.addEventListener('input', guard(function () { states[mode].query = search.value; apply(); body.scrollTop = 0; }));
    kindFilter.addEventListener('change', guard(function () { states[mode].filter = kindFilter.value; configureFilters(); apply(); body.scrollTop = 0; }));
    publisherFilter.addEventListener('change', guard(function () { states[mode].publisher = publisherFilter.value; configureFilters(); apply(); body.scrollTop = 0; }));
    $('[data-nd-filter-toggle]').addEventListener('click', guard(function () { states[mode].filtersOpen = !states[mode].filtersOpen; configureFilters(); }));
    back.addEventListener('click', guard(function () { restoreRecord(true); }));
    root.addEventListener('keydown', guard(function (event) {
      if (event.key === 'Escape' && origin) { event.preventDefault(); event.stopImmediatePropagation(); restoreRecord(true); }
      else if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey && !event.isComposing && !origin && mode !== 'following' && !event.target.closest('input,select,textarea,[contenteditable]:not([contenteditable="false"])')) {
        event.preventDefault(); search.focus({preventScroll: true});
      }
    }), true);
    root.addEventListener('click', guard(function (event) {
      if (event.target.closest('.nd-close,.mx5-dlg-backdrop')) restoreRecord(false);
    }), true);
    root.addEventListener('focus', guard(function (event) {
      if (event.target === root) { restoreRecord(false); $('#nd-title').focus({preventScroll: true}); }
    }), true);
    $('.nd-snapshot').appendChild($('.nd-result-count'));
    dateLabels(); indexItems(); configureFilters(); apply();
    tools.hidden = false; root.classList.add('nd-enhanced'); root.dataset.ndReady = 'true';
    observer = new MutationObserver(guard(function () {
      var scroll = body.scrollTop; dateLabels(); indexItems();
      if (origin) detailCopy(); else { configureFilters(); apply(); }
      body.scrollTop = scroll;
    }));
    observer.observe(document.documentElement, {attributes: true, attributeFilter: ['data-lang']});
  } catch (error) { fallback(); }
}());
