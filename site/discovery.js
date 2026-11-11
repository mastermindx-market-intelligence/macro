/* Top Picks page controls and opt-in standalone native-entry restoration. */
(function () {
  'use strict';
  var root = document.querySelector('[data-discovery-history="v1"]');
  if (!root) return;
  var tabs = Array.from(root.querySelectorAll('.tabs [data-tab]'));
  var select = document.getElementById('secsel');
  var stretch = document.getElementById('hideStretch');
  var strong = document.getElementById('seg-strong'), weak = document.getElementById('seg-weak');
  if (!tabs.length || !select || !stretch || !strong || !weak) return;
  var sectors = Array.from(select.options).map(function (o) { return o.value; }).filter(Boolean);
  var groups = Array.from(root.querySelectorAll('[data-grp="seclist"]'));
  var source = root.getAttribute('data-discovery-asof') || '';
  var enabled = window.top === window.self && !window.MMXSharedShell;
  var KEY = 'mmx.topPicks.v1', path = window.location.pathname;
  var writable = enabled, validEntry = false, activity = 0, frame = null, leaving = null, restoring = false;
  var issue = '', restored = false, observationChanged = false, missingRow = false, moved = false;
  var note = document.getElementById('discovery-return-status');
  var filterNote = document.getElementById('discovery-filter-status');
  var links = [], byKey = new Map(), scrollers = new Map();
  var returnEpoch = activity, lastUrl = location.href;

  function l(en, zh) { return document.documentElement.getAttribute('data-lang') === 'zh' ? zh : en; }
  function record(v) { return v !== null && typeof v === 'object' && !Array.isArray(v) && Object.prototype.toString.call(v) === '[object Object]'; }
  function text(v, n) { return typeof v === 'string' && v.length <= n; }
  function coord(v) { return typeof v === 'number' && isFinite(v) && Math.abs(v) <= 10000000; }
  function visible(el) { return !!el && el.getClientRects().length > 0 && !el.closest('[hidden]'); }
  function hide(el, value) { el.hidden = value; el.style.display = value ? 'none' : ''; }
  function otherOwner() {
    if (window.top !== window.self || window.MMXSharedShell || location.pathname !== path) return true;
    var overlay = window.MDXTerminalOverlay;
    if (overlay && overlay.isOpen && overlay.isOpen()) return true;
    try { var raw = window.history.state; return record(raw) && Object.prototype.hasOwnProperty.call(raw, '__mdxTerminalOverlay'); }
    catch (e) { return false; }
  }
  function blank() { return { version: 1, path: path, tab: 'global', side: 'strong', sector: sectors[0] || '', hideStretch: false, asOf: source, position: null }; }
  function read() {
    validEntry = false;
    var clean = blank(), raw, v;
    if (!enabled) return clean;
    try { raw = window.history.state; } catch (e) { writable = false; return clean; }
    if (raw !== null && !record(raw)) { writable = false; return clean; }
    if (!raw || !Object.prototype.hasOwnProperty.call(raw, KEY)) return clean;
    v = raw[KEY];
    if (!record(v) || v.version !== 1 || v.path !== path ||
        ['global', 'sectors', 'sector'].indexOf(v.tab) < 0 ||
        ['strong', 'weak'].indexOf(v.side) < 0 || !text(v.sector, 160) ||
        typeof v.hideStretch !== 'boolean' || !text(v.asOf, 400)) {
      issue = 'invalid'; return clean;
    }
    clean.tab = v.tab; clean.side = v.side; clean.hideStretch = v.hideStretch;
    clean.sector = v.sector;
    if (v.sector && sectors.indexOf(v.sector) < 0) { clean.sector = ''; issue = 'sector'; }
    var p = v.position;
    if (p !== null && (!record(p) || !text(p.key, 900) || !text(p.focus, 900) ||
        !coord(p.offset) || !coord(p.x) || !coord(p.y) || p.x < 0 || p.y < 0 ||
        !coord(p.tableLeft) || p.tableLeft < 0 || (p.table !== undefined && !text(p.table, 900)))) {
      issue = 'position';
    } else if (p) {
      clean.position = { key: p.key, focus: p.focus, offset: p.offset, x: p.x, y: p.y, tableLeft: p.tableLeft, table: p.table || '' };
    }
    validEntry = true; observationChanged = !!v.asOf && v.asOf !== source;
    return clean;
  }

  root.querySelectorAll('a[href^="stock.html#"]').forEach(function (a) {
    var sector = a.closest('[data-grp="seclist"]'), global = a.closest('[data-grp="glist"]'), buy = a.closest('.bz-card');
    if (!sector && !global && !buy) return;
    var ticker;
    try { ticker = decodeURIComponent(new URL(a.getAttribute('href'), location.href).hash.slice(1)); } catch (e) { return; }
    if (!text(ticker, 160) || !ticker) return;
    var side = sector ? (Array.from(sector.querySelectorAll('table')).indexOf(a.closest('table')) === 0 ? 'strong' : 'weak') : global ? global.id.slice(2) : '';
    var key = JSON.stringify([sector ? 'sector' : global ? 'global' : 'buyzone', side, sector ? sector.getAttribute('data-sector') : '', ticker]);
    a.setAttribute('data-discovery-key', key); links.push(a);
    byKey.set(key, byKey.has(key) ? null : a);
  });
  root.querySelectorAll('.discovery-scroll').forEach(function (el) {
    var sector = el.closest('[data-grp="seclist"]'), global = el.closest('[data-grp="glist"]');
    var side = sector ? (Array.from(sector.querySelectorAll('.discovery-scroll')).indexOf(el) === 0 ? 'strong' : 'weak') : global ? global.id.slice(2) : '';
    var key = JSON.stringify([sector ? 'sector' : global ? 'global' : 'sectors', side, sector ? sector.getAttribute('data-sector') : '']);
    el.setAttribute('data-discovery-scroll-key', key); el.setAttribute('aria-describedby', 'discovery-table-help');
    scrollers.set(key, el);
  });
  function focusKey(el) {
    if (!el || !root.contains(el)) return '';
    if (el.hasAttribute('data-discovery-key')) return el.getAttribute('data-discovery-key');
    if (el.hasAttribute('data-discovery-scroll-key')) return 'scroll:' + el.getAttribute('data-discovery-scroll-key');
    if (['secsel', 'hideStretch', 'seg-strong', 'seg-weak', 'discovery-tab-global', 'discovery-tab-sectors', 'discovery-tab-sector'].indexOf(el.id) >= 0) return 'control:' + el.id;
    return '';
  }
  function focusElement(key) {
    if (key.indexOf('scroll:') === 0) return scrollers.get(key.slice(7)) || null;
    if (key.indexOf('control:') === 0) {
      var el = document.getElementById(key.slice(8));
      return el && focusKey(el) === key ? el : null;
    }
    return byKey.get(key) || null;
  }
  var state = read(); restored = validEntry;

  function announce() {
    var parts = [];
    if (enabled && !writable) parts.push(l('This browser entry cannot retain the view.', '此浏览器历史记录无法保留视图。'));
    if (restored) parts.push(l('View settings restored. Rankings use the current snapshot.', '视图设置已恢复，排名使用当前快照。'));
    if (observationChanged) parts.push(l('The source date has changed since your last visit.', '来源日期与上次访问相比已改变。'));
    if (issue === 'invalid') parts.push(l('The previous view could not be restored. Default settings are shown.', '无法恢复先前视图，现显示默认设置。'));
    if (issue === 'sector') parts.push(l('The previous sector is no longer supplied. Choose a sector to continue.', '来源中已无先前板块，请选择一个板块继续。'));
    if (issue === 'position') parts.push(l('View settings were retained; the previous position was unavailable.', '已保留视图设置，但先前位置不可用。'));
    if (missingRow) parts.push(l('The previous company is no longer in this view. Returned to the view controls.', '先前公司已不在此视图中，已返回视图控件。'));
    if (moved) parts.push(l('Your later focus and position were kept.', '已保留您返回后主动选择的焦点和位置。'));
    note.textContent = parts.join(' '); note.hidden = !parts.length;
  }
  function filterSummary() {
    var box = document.getElementById('g-' + state.side);
    var rows = Array.from(box.querySelectorAll('tr[data-grade]'));
    var shown = rows.filter(function (r) { return !r.hidden; }).length;
    var msg;
    if (!rows.length) msg = l('No ranked names are supplied for this list.', '此列表没有来源排名个股。');
    else if (!shown) msg = l('All names are hidden by this filter. Clear Hide stretched / parabolic to show them.', '此筛选隐藏了全部个股，取消“隐藏拉伸/抛物”即可显示。');
    else msg = l(shown + ' of ' + rows.length + ' supplied names shown.', '显示来源中的 ' + shown + ' / ' + rows.length + ' 只个股。');
    if (state.hideStretch) msg += ' ' + l('This filter applies to Top Picks only.', '此筛选仅作用于精选列表。');
    filterNote.textContent = msg;
  }
  function apply() {
    tabs.forEach(function (b) {
      var on = b.dataset.tab === state.tab;
      b.classList.toggle('on', on); b.setAttribute('aria-selected', String(on)); b.tabIndex = on ? 0 : -1;
      hide(document.getElementById('tab-' + b.dataset.tab), !on);
    });
    [strong, weak].forEach(function (b) {
      var on = b.id === 'seg-' + state.side;
      b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on));
    });
    hide(document.getElementById('g-strong'), state.side !== 'strong');
    hide(document.getElementById('g-weak'), state.side !== 'weak');
    select.value = state.sector;
    groups.forEach(function (g) { hide(g, !state.sector || g.getAttribute('data-sector') !== state.sector); });
    stretch.checked = state.hideStretch;
    root.querySelectorAll('#tab-global tr[data-grade]').forEach(function (row) {
      hide(row, state.hideStretch && ['stretched', 'parabolic'].indexOf(row.getAttribute('data-grade')) >= 0);
    });
    Array.from(select.options).forEach(function (o) {
      var label = o.getAttribute(document.documentElement.getAttribute('data-lang') === 'zh' ? 'data-label-zh' : 'data-label-en');
      if (label !== null) o.textContent = label + (o.hasAttribute('data-count') ? ' (' + o.getAttribute('data-count') + ')' : '');
    });
    root.querySelector('.tabs').setAttribute('aria-label', l('Discovery views', '发现视图'));
    root.querySelector('.seg').setAttribute('aria-label', l('Conviction ranking', '信念排名'));
    document.getElementById('discovery-table-help').textContent = l('Scroll tables sideways to see every column.', '横向滚动表格可查看全部列。');
    scrollers.forEach(function (el, key) {
      var parts = JSON.parse(key), label;
      if (parts[0] === 'sectors') label = l('Sectors by conviction', '按信念排序的板块');
      else {
        label = parts[1] === 'strong' ? l('Top conviction', '高信念') : l('Avoid', '回避');
        var option = Array.from(select.options).find(function (o) { return o.value === parts[2]; });
        label += ' — ' + (parts[0] === 'global' ? l('Top Picks', '精选') : option ? option.textContent : parts[2]);
      }
      el.setAttribute('aria-label', label);
    });
    filterSummary(); announce();
  }
  function write() {
    if (!writable || otherOwner()) return;
    try {
      var raw = window.history.state;
      if (raw !== null && !record(raw)) throw new Error('foreign history owner');
      var next = {};
      Object.keys(raw || {}).forEach(function (key) {
        Object.defineProperty(next, key, { value: raw[key], writable: true, configurable: true, enumerable: true });
      });
      next[KEY] = state;
      window.history.replaceState(next, '');
    } catch (e) { writable = false; announce(); }
  }
  function change() {
    activity++;
    state.position = null; issue = ''; missingRow = false; moved = false;
    apply(); write();
  }
  tabs.forEach(function (b, i) {
    b.addEventListener('click', function () { state.tab = b.dataset.tab; change(); });
    b.addEventListener('keydown', function (e) {
      if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
      var next;
      if (e.key === 'ArrowRight') next = (i + 1) % tabs.length;
      else if (e.key === 'ArrowLeft') next = (i + tabs.length - 1) % tabs.length;
      else if (e.key === 'Home') next = 0;
      else if (e.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      e.preventDefault(); tabs[next].focus(); tabs[next].click();
    });
  });
  strong.addEventListener('click', function () { state.side = 'strong'; change(); });
  weak.addEventListener('click', function () { state.side = 'weak'; change(); });
  select.addEventListener('change', function () { state.sector = select.value; change(); });
  stretch.addEventListener('change', function () { state.hideStretch = stretch.checked; change(); });
  document.addEventListener('langchange', apply);
  apply();
  if (!validEntry) write();
  if (!enabled) return;

  function capture(target) {
    if (otherOwner()) return;
    var candidate = target || document.activeElement;
    var a = candidate && candidate.closest && candidate.closest('[data-discovery-key]');
    var focusedTable = candidate && candidate.closest && candidate.closest('.discovery-scroll');
    if ((!a || !visible(a)) && !focusedTable) {
      a = links.find(function (el) {
        if (!visible(el)) return false;
        var r = el.getBoundingClientRect(); return r.bottom > 90 && r.top < window.innerHeight;
      }) || null;
    }
    var box = (a && a.closest('.discovery-scroll')) || focusedTable;
    var anchor = a || box;
    state.position = {
      key: a ? a.getAttribute('data-discovery-key') : '', offset: anchor ? anchor.getBoundingClientRect().top : 0,
      table: box ? box.getAttribute('data-discovery-scroll-key') : '',
      x: Math.max(0, window.scrollX), y: Math.max(0, window.scrollY), tableLeft: box ? box.scrollLeft : 0,
      focus: target && target.closest && target.closest('[data-discovery-key]') ? focusKey(target.closest('[data-discovery-key]')) : focusKey(document.activeElement)
    };
    write();
  }
  ['pointerdown', 'keydown', 'wheel', 'touchstart', 'input', 'change'].forEach(function (name) {
    document.addEventListener(name, function (e) {
      if (restoring) return;
      activity++; leaving = null;
      var a = e.target.closest && e.target.closest('[data-discovery-key]');
      if (a && (name === 'pointerdown' || name === 'touchstart' || (name === 'keydown' && e.key === 'Enter'))) capture(a);
    }, true);
  });
  document.addEventListener('focusin', function (e) {
    if (restoring) return;
    activity++;
    if (e.target.hasAttribute && e.target.hasAttribute('data-discovery-key')) capture(e.target);
  }, true);
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('[data-discovery-key]');
    if (a) { leaving = a; capture(a); }
  }, true);
  window.addEventListener('pagehide', function () { capture(leaving); });
  function restorePosition() {
    if (!validEntry || !state.position || otherOwner()) return;
    var p = state.position, stamp = returnEpoch, restoreUrl = location.href;
    if (frame !== null) cancelAnimationFrame(frame);
    frame = requestAnimationFrame(function () {
      frame = requestAnimationFrame(function () {
        frame = null;
        if (otherOwner() || location.href !== restoreUrl) return;
        var ae = document.activeElement, sameFocus = p.focus && focusKey(ae) === p.focus;
        if (activity !== stamp || (ae !== document.body && ae !== document.documentElement && !sameFocus)) {
          moved = true; announce(); return;
        }
        var a = p.key ? byKey.get(p.key) : null;
        if (a && !visible(a)) a = null;
        var fallback = state.tab === 'sector' ? select : tabs.find(function (b) { return b.dataset.tab === state.tab; });
        var f = p.focus ? focusElement(p.focus) : null;
        var box = p.table ? scrollers.get(p.table) : a && a.closest('.discovery-scroll');
        if (box && !visible(box)) box = null;
        var lostTable = (p.table && !box) || (p.focus.indexOf('scroll:') === 0 && (!f || !visible(f)));
        restoring = true;
        try {
          if ((p.key && !a) || (p.focus && p.focus.indexOf('control:') !== 0 && p.focus.indexOf('scroll:') !== 0 && (!f || !visible(f))) || lostTable) {
            missingRow = !lostTable; if (lostTable && issue !== 'sector') issue = 'position';
            window.scrollTo(0, Math.max(0, window.scrollY + fallback.getBoundingClientRect().top - 90));
            fallback.focus({ preventScroll: true });
          } else {
            if (box) box.scrollLeft = p.tableLeft;
            var anchor = a || box;
            window.scrollTo(p.x, Math.max(0, anchor ? window.scrollY + anchor.getBoundingClientRect().top - p.offset : p.y));
            if (f && visible(f) && !f.disabled) f.focus({ preventScroll: true });
          }
        } finally { restoring = false; }
        announce();
      });
    });
  }
  window.addEventListener('pageshow', function (e) {
    if (otherOwner()) return;
    if (e.persisted) { returnEpoch = activity; state = read(); restored = validEntry; apply(); }
    restorePosition();
  });
  window.addEventListener('popstate', function () {
    var url = location.href;
    if (url === lastUrl) return; // The incumbent overlay uses the same URL.
    lastUrl = url;
    if (otherOwner()) return;
    var prior = state;
    if (frame !== null) { cancelAnimationFrame(frame); frame = null; }
    returnEpoch = activity; writable = enabled; issue = ''; missingRow = false; moved = false;
    state = read(); restored = validEntry;
    if (!validEntry && writable && !issue) {
      // A newly-created native fragment entry has no local state yet.
      state = prior; state.position = null; state.asOf = source;
      write();
    }
    // Native same-document history owns its viewport and table scroll restoration.
    // The stored company position may predate later scrolling within this document.
    apply();
  });
  if (document.readyState === 'complete') restorePosition();
})();
