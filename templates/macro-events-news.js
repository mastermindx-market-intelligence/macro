/* Progressive enhancement for the existing Macro dialog. No network requests,
   persistence, alert ownership, or market scoring. All content is server-rendered. */
(function () {
  'use strict';
  var root = document.getElementById('dlg-news');
  if (!root || !root.classList.contains('nd-desk')) return;
  var tools = root.querySelector('.nd-tools');
  var search = root.querySelector('#nd-search');
  var body = root.querySelector('.nd-body');
  var items = Array.from(root.querySelectorAll('[data-nd-item]'));
  var sections = Array.from(root.querySelectorAll('[data-nd-section]'));
  var tabs = Array.from(root.querySelectorAll('[data-nd-mode]'));
  var empty = root.querySelector('[data-nd-no-results]');
  var modes = ['briefing', 'review', 'calendar', 'news', 'context'];
  var limits = {review: 3, calendar: 4, news: 3, context: 2};
  var mode = 'briefing';
  if (!tools || !search || !body || !empty || !tabs.length) return;

  function zh() { return document.documentElement.getAttribute('data-lang') === 'zh'; }
  function normalize(value) { return String(value || '').normalize('NFKC').toLocaleLowerCase().replace(/\s+/g, ' ').trim(); }
  // Keep search out of generic expandable explanations: match the observation,
  // headline, ticker, publisher and supplied date, not hidden boilerplate.
  var haystacks = new Map();
  function indexItems() {
    items.forEach(function (item) {
      var nodes = item.querySelectorAll('.nd-item-title,.nd-change,h4,.nd-item-meta,.nd-story-meta,.nd-event-full-date,.nd-event-date');
      var dates = Array.from(item.querySelectorAll('[data-nd-date]')).map(function (node) { return node.getAttribute('data-nd-date'); });
      haystacks.set(item, normalize(Array.from(nodes).map(function (node) { return node.textContent; }).concat(dates).join(' ')));
    });
  }

  function apply() {
    var query = normalize(search.value);
    var words = query.split(' ').filter(Boolean);
    var matched = {review: 0, calendar: 0, news: 0, context: 0};
    var shown = {review: 0, calendar: 0, news: 0, context: 0};
    var total = 0;
    items.forEach(function (item) {
      var kind = item.getAttribute('data-nd-item');
      var inScope = mode === 'briefing' || mode === kind;
      if (inScope) total += 1;
      var hit = inScope && words.every(function (word) { return haystacks.get(item).includes(word); });
      if (hit) matched[kind] += 1;
      var visible = hit && (mode !== 'briefing' || query || shown[kind] < limits[kind]);
      item.hidden = !visible;
      if (visible) shown[kind] += 1;
    });
    sections.forEach(function (section) {
      var kind = section.getAttribute('data-nd-section');
      section.hidden = (mode !== 'briefing' && mode !== kind) || (Boolean(query) && matched[kind] === 0);
      var more = section.querySelector('[data-nd-more]');
      if (more) more.hidden = section.hidden || matched[kind] <= shown[kind];
    });
    tabs.forEach(function (tab) {
      var selected = tab.getAttribute('data-nd-mode') === mode;
      tab.classList.toggle('is-selected', selected);
      tab.setAttribute('aria-pressed', String(selected));
    });
    var count = Object.values(shown).reduce(function (a, b) { return a + b; }, 0);
    root.querySelectorAll('[data-nd-shown]').forEach(function (node) { node.textContent = String(count); });
    root.querySelectorAll('[data-nd-total]').forEach(function (node) { node.textContent = String(total); });
    empty.hidden = !query || count > 0;
    root.classList.toggle('nd-single-view', mode !== 'briefing');
    root.classList.toggle('nd-searching', Boolean(query));
  }

  function selectMode(next, focusTab) {
    if (!modes.includes(next)) return;
    mode = next;
    apply();
    body.scrollTop = 0;
    if (focusTab) {
      var tab = tabs.find(function (node) { return node.getAttribute('data-nd-mode') === mode; });
      if (tab) tab.focus({preventScroll: true});
    }
  }
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () { selectMode(tab.getAttribute('data-nd-mode'), false); });
  });
  root.querySelectorAll('[data-nd-more]').forEach(function (button) {
    button.addEventListener('click', function () { selectMode(button.getAttribute('data-nd-more'), true); });
  });
  root.querySelectorAll('[data-nd-reset]').forEach(function (button) {
    button.addEventListener('click', function () {
      search.value = '';
      selectMode('briefing', false);
      search.focus({preventScroll: true});
    });
  });
  search.addEventListener('input', apply);
  root.querySelector('.nd-tabs').addEventListener('keydown', function (event) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    var index = tabs.indexOf(document.activeElement);
    if (index < 0) return;
    event.preventDefault();
    var next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    tabs[next].focus();
  });

  // Civil dates retain the producer's date: never parse YYYY-MM-DD in local time.
  function civil(value) {
    var match = /^(\d{4})-(\d{2})-(\d{2})(?:$|[ T])/.exec(String(value || ''));
    if (!match) return null;
    var y = Number(match[1]), m = Number(match[2]), d = Number(match[3]);
    var date = new Date(Date.UTC(y, m - 1, d, 12));
    if (date.getUTCFullYear() !== y || date.getUTCMonth() !== m - 1 || date.getUTCDate() !== d) return null;
    return {date: date, iso: match[1] + '-' + match[2] + '-' + match[3]};
  }
  function utcStamp(value) {
    var match = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?(?:\s*UTC|Z)?$/.exec(String(value || '').trim());
    if (!match || !civil(match[1]) || Number(match[2]) > 23 || Number(match[3]) > 59 || Number(match[4] || 0) > 59) return null;
    return new Date(match[1] + 'T' + match[2] + ':' + match[3] + ':' + (match[4] || '00') + 'Z');
  }
  function dateLabels() {
    var locale = zh() ? 'zh-CN' : 'en-US';
    search.placeholder = search.getAttribute(zh() ? 'data-placeholder-zh' : 'data-placeholder-en');
    var dayFormat = new Intl.DateTimeFormat(locale, {year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC'});
    var stampFormat = new Intl.DateTimeFormat(locale, {year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: 'UTC'});
    root.querySelectorAll('[data-nd-date]').forEach(function (node) {
      var raw = node.getAttribute('data-nd-date');
      var day = civil(raw);
      var stamp = node.getAttribute('data-nd-date-kind') === 'utc' ? utcStamp(raw) : null;
      node.title = raw;
      if (stamp) {
        node.textContent = stampFormat.format(stamp);
        node.dateTime = stamp.toISOString();
      } else if (day) {
        node.textContent = dayFormat.format(day.date);
        node.dateTime = day.iso;
      }
    });
    var nyParts = new Intl.DateTimeFormat('en-US', {year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'America/New_York'}).formatToParts(new Date());
    var part = function (type) { return nyParts.find(function (p) { return p.type === type; }).value; };
    var today = part('year') + '-' + part('month') + '-' + part('day');
    root.querySelectorAll('[data-nd-calendar-date]').forEach(function (node) {
      var day = civil(node.getAttribute('data-nd-calendar-date'));
      if (!day) return;
      node.querySelector('[data-nd-month]').textContent = new Intl.DateTimeFormat(locale, {month: 'short', timeZone: 'UTC'}).format(day.date);
      node.querySelector('[data-nd-day]').textContent = String(day.date.getUTCDate());
      var past = node.closest('.nd-event').querySelector('.nd-past-date');
      if (past) past.hidden = day.iso >= today;
    });
    var sourceClock = root.querySelector('[data-nd-date-kind="utc"]');
    var built = sourceClock && utcStamp(sourceClock.getAttribute('data-nd-date'));
    var stale = root.querySelector('[data-nd-stale]');
    if (stale) stale.hidden = !built || Date.now() - built.getTime() <= 48 * 60 * 60 * 1000;
  }

  // Rich-dialog heading and local keyboard floor. The existing mx5 manager
  // remains the owner of opening, closing, scroll lock and opener restoration.
  root.addEventListener('focus', function (event) {
    if (event.target === root) root.querySelector('#nd-title').focus({preventScroll: true});
  }, true);
  root.addEventListener('keydown', function (event) {
    if (event.key !== 'Tab') return;
    var focusable = Array.from(root.querySelectorAll('button,a[href],summary,input,select,textarea,[tabindex]')).filter(function (node) {
      return !node.disabled && node.tabIndex >= 0 && node.getClientRects().length && getComputedStyle(node).visibility !== 'hidden';
    });
    if (!focusable.length) return;
    var index = focusable.indexOf(document.activeElement);
    if ((event.shiftKey && index <= 0) || (!event.shiftKey && (index < 0 || index === focusable.length - 1))) {
      event.preventDefault();
      event.stopPropagation();
      focusable[event.shiftKey ? focusable.length - 1 : 0].focus();
    }
  });
  try {
    dateLabels();
    indexItems();
    apply();
    tools.hidden = false;
    root.classList.add('nd-enhanced');
    new MutationObserver(function () { dateLabels(); indexItems(); apply(); }).observe(document.documentElement, {attributes: true, attributeFilter: ['data-lang']});
  } catch (error) {
    // A failed enhancement never erases server-rendered evidence or empty states.
    items.forEach(function (item) { item.hidden = false; });
    sections.forEach(function (section) { section.hidden = false; });
    tools.hidden = true;
    empty.hidden = true;
    root.classList.remove('nd-enhanced', 'nd-single-view', 'nd-searching');
  }
}());
