/* Read projection only: no fetch, model call, event identity or private state. */
(function (root) {
  'use strict';
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }
  function pair(value) {
    value = value && typeof value === 'object' ? value : {};
    return '<span class="l-en">' + esc(value.en || '') + '</span>'
      + '<span class="l-zh">' + esc(value.zh || value.en || '') + '</span>';
  }
  function rows(date) {
    var el = document.getElementById('calendar-event-context-data');
    if (!el) return [];
    try {
      var data = JSON.parse(el.textContent || '[]');
      if (!Array.isArray(data)) return [];
      return data.filter(function (row) {
        return row && row.schema === 'calendar_event_context.v1' && row.event_date === date;
      });
    } catch (e) { return []; }
  }
  function safeSource(value) {
    try {
      var u = new URL(value);
      var hosts = ['www.treasurydirect.gov','www.bls.gov','www.bea.gov','www.dol.gov',
        'www.federalreserve.gov','www.ismworld.org','www.cboe.com','www.eia.gov','www.opec.org'];
      return u.protocol === 'https:' && !u.username && !u.password && hosts.indexOf(u.hostname) !== -1 ? u.href : '';
    } catch (e) { return ''; }
  }
  function factValue(fact) {
    if (fact.value === null || fact.value === undefined || fact.value === '') {
      return pair({en:'Not supplied',zh:'未提供'});
    }
    var text = String(fact.value);
    if (fact.key === 'offering_amount_usd' && /^[0-9]+(?:\.[0-9]+)?$/.test(text)) {
      var parts = text.split('.');
      text = '$' + parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (parts.length > 1 ? '.' + parts[1] : '');
    }
    return esc(text);
  }
  function card(row) {
    var facts = Array.isArray(row.facts) ? row.facts.filter(function (f) { return f && f.label; }) : [];
    var questions = Array.isArray(row.questions) ? row.questions : [];
    var limits = Array.isArray(row.limitations) ? row.limitations : [];
    var label = row.coverage === 'conflicting_terms' ? {en:'Conflicting source terms',zh:'来源条款冲突'}
      : row.coverage === 'official_terms' ? {en:'Official terms',zh:'官方条款'}
      : row.coverage === 'partial_terms' ? {en:'Partial official terms',zh:'部分官方条款'}
      : {en:'Reference context',zh:'参考背景'};
    var url = safeSource(row.source_url);
    return '<article class="card eic-card" data-context-type="' + esc(row.event_type) + '">'
      + '<header class="eic-heading"><h3>' + pair(row.title) + '</h3><span class="eic-state">' + pair(label) + '</span></header>'
      + '<p class="eic-limit">' + pair(row.event_type === 'AUCTION'
        ? {en:'Announcement snapshot · results not loaded',zh:'公告快照 · 未加载拍卖结果'}
        : {en:'Reference guide · not a live assessment',zh:'参考指南 · 非实时评估'}) + '</p>'
      + '<p class="eic-summary">' + pair(row.summary) + '</p>'
      + (facts.length ? '<dl class="eic-facts">' + facts.map(function (f) {
        return '<div><dt>' + pair(f.label) + '</dt><dd>' + factValue(f) + '</dd></div>';
      }).join('') + '</dl>' : '')
      + '<details class="mx-disc eic-detail"><summary>' + pair({en:'Reading guide · what to examine',zh:'阅读指南 · 观察重点'}) + '</summary>'
      + '<div class="eic-detail-body">' + questions.map(function (q) { return '<p>' + pair(q) + '</p>'; }).join('')
      + limits.map(function (q) { return '<p class="eic-limit">' + pair(q) + '</p>'; }).join('') + '</div></details>'
      + (url ? '<a class="eic-source" href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">'
        + pair({en:'Official publisher / reference',zh:'官方发布方／参考资料'}) + ' ↗</a>' : '')
      + '</article>';
  }
  root.MMXCalendarEventContext = {
    signature: function (date) { return JSON.stringify(rows(date)); },
    renderDate: function (date) {
      var found = rows(date);
      return found.length ? '<section class="eic-stack" aria-label="Event reading context">' + found.map(card).join('') + '</section>' : '';
    }
  };
})(typeof window !== 'undefined' ? window : globalThis);
