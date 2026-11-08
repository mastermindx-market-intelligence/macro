/* sector_cycles_states.js — SC_STATES seam 'sc-states.v1' (programme 7646, lane L4).
 * One typed vocabulary for every Cycles read: classify a response, fetch it typed, check two
 * generations against each other, count coverage and render a state with deck copy only.
 * No wall clock, no invented copy: DECK is generated from design_refs/sector-paper-20261021/
 * copy_deck.json (tests assert equality) — do not hand-edit it. */
(function (root) {
  'use strict';
  var DECK = {"states.fresh_title":["Up to date","已是最新"],"states.fresh_body":["The latest completed session is in; each panel stamps its own evidence date.","最新完成的交易日已纳入；每个面板均标注证据日期。"],"states.incompatible_generation_title":["History is from a different day","历史来自不同日期"],"states.incompatible_generation_body":["History {x}, current read {y}. Not drawn, so the two are never mixed.","历史 {x}，当前读数 {y}。不绘制，避免混用。"],"states.partial_title":["Partial coverage","覆盖不完整"],"states.partial_body":["Based on {x} of {y} checks","基于 {y} 项检查中的 {x} 项"],"states.error_title":["History unavailable right now","历史暂不可用"],"states.error_body":["The current read above is unaffected.","上方的当前读数不受影响。"],"states.empty_title":["No recorded events are open.","目前没有已记录事件。"],"states.empty_body":["Events appear here once Mastermind records one.","Mastermind 记录后将自动出现。"],"states.no_access_title":["Sign in to view","登录后可查看"],"states.no_access_body":["Sign in with access to view these observations.","请使用有权限的账户登录查看。"],"states.no_access_action":["Sign in","登录"],"states.loading_title":["Loading…","加载中…"],"states.loading_body":["Loading history…","历史加载中…"],"states.unauthorized_title":["Not in your plan","当前方案未包含"],"states.unauthorized_body":["You are signed in; this part needs a different plan.","你已登录；此部分需要其他方案。"],"states.unauthorized_action":["See plans","查看方案"],"states.invalid_payload_title":["Source could not be checked","无法核验来源"],"states.invalid_payload_body":["The source coverage could not be checked. Open the full evidence for details.","无法核验来源覆盖情况。请打开完整证据查看详情。"],"states.empty_search_title":["No items match this phase","该阶段暂无条目"],"states.empty_search_body":["Nothing on the clock. Tap an item or hit Select all visible to chart them.","图中暂无条目。点击任一条目或点全选可见即可绘制。"],"states.empty_search_action":["All phases","全部阶段"],"brief.coverage_unavailable_title":["Sector measurement coverage unavailable","板块测量覆盖暂不可用"],"brief.coverage_unavailable_body":["Coverage and its evidence date appear with the measured-sector read.","覆盖情况与证据日期随板块实测数据一同显示。"],"components.rel_not_supplied":["Sector relationship not supplied","未提供板块间关系"],"cycles.stance_unavailable":["Stance unavailable","立场不可用"],"cycles.hazard_unavailable":["No calibrated cell for this leg. The producer could not form a monotone turn curve; shown as a gap, never as zero.","该周期段没有校准单元格。生产端无法形成单调的转折曲线；显示为空缺，绝不记为零。"],"cycles.fragmentation_chip":["Fragmentation data","分化数据"]};
  var SC_STATES = { version: 'sc-states.v1' };
  var HOP = Object.prototype.hasOwnProperty;
  var STATES = ['fresh', 'empty', 'unavailable', 'unauthorized', 'forbidden', 'not_found', 'malformed', 'offline', 'incompatible_generation'];
  /* A field the producer did not supply. Composed from deck fragments; DECK-GAP (no single deck key). */
  var FIELD_UNAVAILABLE = '<span class="l-en">— unavailable</span><span class="l-zh">— 不可用</span>';
  /* state -> deck stem. 401 is "sign in" (no_access); 403 is "not in your plan" (unauthorized).
     404, offline and unavailable read as the history-unavailable pair (offline_* is the write
     string "changes kept locally", wrong for a read: DECK-GAP). */
  var STEM = {
    fresh: 'states.fresh', empty: 'states.empty', unavailable: 'states.error', not_found: 'states.error',
    offline: 'states.error', unauthorized: 'states.no_access', forbidden: 'states.unauthorized',
    malformed: 'states.invalid_payload', incompatible_generation: 'states.incompatible_generation',
    partial: 'states.partial', loading: 'states.loading'
  };
  var ACTION = { unauthorized: 'states.no_access_action', forbidden: 'states.unauthorized_action' };
  /* context overrides for the unavailable family (unavailable / not_found / offline). */
  var UNAVAILABLE_CTX = {
    coverage: ['brief.coverage_unavailable_title', 'brief.coverage_unavailable_body'],
    relationship: ['components.rel_not_supplied', null],
    stance: ['cycles.stance_unavailable', null],
    hazard: ['cycles.hazard_unavailable', null]
  };
  var UNAVAILABLE_FAMILY = { unavailable: 1, not_found: 1, offline: 1 };
  /* The ZH empty body names the brand in Latin script; a ZH face carries zero Latin, so the empty
     state shows its title only (DECK-GAP). */
  var TITLE_ONLY = { 'states.empty': 1 };

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function pair(key) { return HOP.call(DECK, key) ? DECK[key] : null; }
  function fill(s, x, y) { return String(s).split('{x}').join(x).split('{y}').join(y); }
  function sessionOf(o) {
    if (!o || typeof o !== 'object') return null;
    var k = ['asOf', 'as_of'], i;
    for (i = 0; i < k.length; i++) if (typeof o[k[i]] === 'string' && o[k[i]]) return o[k[i]];
    return null;
  }

  /* classify -> one state name. expect: {list: key, generation: consumer session}. */
  function classifyFull(http, body, expect) {
    var ex = expect || {}, b = body, gen;
    if (http === 0) return { state: 'offline', reason: 'network' };
    if (http === 401) return { state: 'unauthorized', reason: 'http_401' };
    if (http === 403) return { state: 'forbidden', reason: 'http_403' };
    if (http === 404) return { state: 'not_found', reason: 'http_404' };
    if (http === 204) return { state: 'empty', reason: 'http_204' };
    if (typeof http === 'number' && (http < 200 || http >= 300)) return { state: 'unavailable', reason: 'http_' + http };
    if (typeof b === 'string') {
      try { b = JSON.parse(b); } catch (e) { return { state: 'malformed', reason: 'parse' }; }
    }
    if (!b || typeof b !== 'object' || Array.isArray(b)) return { state: 'malformed', reason: 'schema' };
    if (b.ok === false) return { state: 'malformed', reason: 'not_ok' };
    if (ex.generation) {
      gen = SC_STATES.generationCheck([b, { asOf: ex.generation }]);
      if (!gen.ok) return { state: 'incompatible_generation', reason: 'as_of_mismatch', data: b, artifact_session: gen.x, consumer_session: gen.y };
    }
    if (ex.list) {
      if (!Array.isArray(b[ex.list])) return { state: 'malformed', reason: 'schema', data: b };
      if (!b[ex.list].length) return { state: 'empty', reason: 'empty_list', data: b };
    }
    return { state: 'fresh', reason: 'ok', data: b };
  }
  SC_STATES.classify = function (http, body, expect) { return classifyFull(http, body, expect).state; };

  /* fetchTyped -> Promise<{state, data, reason, http, artifact_session?, consumer_session?}>; never rejects.
     data is set only for fresh / empty, so another generation can never be drawn by accident. */
  SC_STATES.fetchTyped = function (url, expect) {
    var P = root.Promise || (typeof Promise !== 'undefined' ? Promise : null), F = root.fetch || (typeof fetch === 'function' ? fetch : null);
    function out(c, http) {
      var r = { state: c.state, data: (c.state === 'fresh' || c.state === 'empty') && c.data ? c.data : null, reason: c.reason, http: http };
      if (c.artifact_session != null) { r.artifact_session = c.artifact_session; r.consumer_session = c.consumer_session; }
      return r;
    }
    if (!P) return null;
    if (!F) return P.resolve(out({ state: 'unavailable', reason: 'no_fetch' }, null));
    try {
      return P.resolve(F(url, { cache: 'no-cache', credentials: 'same-origin' })).then(function (res) {
        var http = res && typeof res.status === 'number' ? res.status : null;
        if (!res || typeof res.text !== 'function') return out({ state: 'malformed', reason: 'schema' }, http);
        return res.text().then(function (txt) { return out(classifyFull(http, txt, expect), http); }, function () { return out({ state: 'offline', reason: 'network' }, http); });
      }, function () { return out({ state: 'offline', reason: 'network' }, 0); }).then(null, function () {
        return out({ state: 'unavailable', reason: 'receiver_error' }, null);
      });
    } catch (e) {
      return P.resolve(out({ state: 'offline', reason: 'network' }, 0));
    }
  };

  /* generationCheck: every entry's own session (asOf / as_of; an alignment record contributes its
     artifact_session and consumer_session) must agree. Entries without a session are skipped. No
     wall-clock rule: a mismatch is a mismatch whichever side is newer. x = first disagreeing
     (artifact) session, y = the reference (consumer) session. */
  SC_STATES.generationCheck = function (list) {
    var vals = [], mismatches = [], i, e, s, y;
    list = Array.isArray(list) ? list : [];
    for (i = 0; i < list.length; i++) {
      e = list[i]; s = sessionOf(e);
      if (s) { vals.push([i, s]); continue; }
      if (e && typeof e === 'object') {
        if (typeof e.artifact_session === 'string' && e.artifact_session) vals.push([i, e.artifact_session]);
        if (typeof e.consumer_session === 'string' && e.consumer_session) vals.push([i, e.consumer_session]);
      }
    }
    if (!vals.length) return { ok: true, mismatches: [], x: null, y: null };
    /* list order is [artifact..., consumer]: the last value is the consumer read (y). */
    y = vals[vals.length - 1][1];
    for (i = 0; i < vals.length; i++) if (vals[i][1] !== y) mismatches.push({ index: vals[i][0], value: vals[i][1], expected: y });
    if (!mismatches.length) return { ok: true, mismatches: [], x: null, y: null };
    return { ok: false, mismatches: mismatches, x: mismatches[0].value, y: y };
  };

  /* fromAlignment: engine/sector_generation_guard.session_alignment status -> state. */
  SC_STATES.fromAlignment = function (align) {
    var st = align && typeof align === 'object' ? align.status : null;
    if (st === 'aligned') return 'fresh';
    if (st === 'incompatible_generation') return 'incompatible_generation';
    if (st === 'missing_input') return 'unavailable';
    if (st === 'invalid_payload') return 'malformed';
    return 'unavailable';
  };

  /* coverage: how many of the expected ids carry a record. Unknown records are unavailable, never 0. */
  SC_STATES.coverage = function (records, expectedIds) {
    var exp = Array.isArray(expectedIds) ? expectedIds : [], have = {}, missing = [], i;
    if (!Array.isArray(records) || !exp.length) return { state: 'unavailable', measured: null, expected: null, missing: null };
    for (i = 0; i < records.length; i++) if (records[i] && records[i].id != null) have[String(records[i].id)] = 1;
    for (i = 0; i < exp.length; i++) if (!have[String(exp[i])]) missing.push(exp[i]);
    return { state: missing.length ? 'partial' : 'fresh', measured: exp.length - missing.length, expected: exp.length, missing: missing };
  };

  function bi(p, x, y, cls, tip) {
    var en = fill(p[0], x, y), zh = fill(p[1], x, y);
    return '<span class="l-en' + (cls ? ' ' + cls : '') + '"' + (tip ? ' title="' + esc(fill(tip[0], x, y)) + '"' : '') + '>' + esc(en) + '</span>'
      + '<span class="l-zh' + (cls ? ' ' + cls : '') + '"' + (tip ? ' title="' + esc(fill(tip[1], x, y)) + '"' : '') + '>' + esc(zh) + '</span>';
  }
  /* stateHTML(state, ctx): deck pairs only, both languages (the page's l-en/l-zh rule picks one).
     ctx = {context, compact, align, x, y, href}. align may be an alignment record or a
     fetchTyped result; either way its artifact_session / consumer_session date the
     incompatible-generation case. */
  SC_STATES.stateHTML = function (state, ctx) {
    var c = ctx || {}, st = HOP.call(STEM, state) ? state : 'unavailable', al = c.align || {}, t, b, a, k, ov, x, y, head = '', html;
    x = c.x != null ? String(c.x) : (al.artifact_session != null ? String(al.artifact_session) : '—');
    y = c.y != null ? String(c.y) : (al.consumer_session != null ? String(al.consumer_session) : '—');
    k = STEM[st];
    if (st === 'empty' && c.context === 'phase') k = 'states.empty_search';
    t = pair(k + '_title'); b = TITLE_ONLY[k] ? null : pair(k + '_body');
    a = ACTION[st] ? pair(ACTION[st]) : (k === 'states.empty_search' ? pair('states.empty_search_action') : null);
    if (UNAVAILABLE_FAMILY[st]) {
      ov = HOP.call(UNAVAILABLE_CTX, c.context) ? UNAVAILABLE_CTX[c.context] : null;
      if (ov) { t = pair(ov[0]); b = ov[1] ? pair(ov[1]) : null; }
    }
    /* a fragmentation chip names its subject first, whatever the state. */
    if (c.context === 'fragmentation') head = bi(pair('cycles.fragmentation_chip'), x, y, 'sc-state-k');
    if (c.compact) {
      return '<span class="sc-state sc-state--' + st + ' sc-state--compact" data-state="' + st + '">'
        + (head ? head + ' ' : '') + bi(t, x, y, '', b) + '</span>';
    }
    html = '<div class="sc-state sc-state--' + st + '" data-state="' + st + '" role="status">'
      + '<p class="sc-state-t">' + (head ? head + ' · ' : '') + bi(t, x, y) + '</p>'
      + (b ? '<p class="sc-state-b">' + bi(b, x, y) + '</p>' : '');
    if (a && c.href) html += '<a class="sc-state-a" href="' + esc(c.href) + '">' + bi(a, x, y) + '</a>';
    else if (a && k === 'states.empty_search' && c.action) html += '<button type="button" class="sc-state-a" data-sc-action="' + esc(c.action) + '">' + bi(a, x, y) + '</button>';
    return html + '</div>';
  };
  SC_STATES.fieldUnavailable = function () { return FIELD_UNAVAILABLE; };
  SC_STATES.STATES = STATES.slice();
  SC_STATES._deck = DECK;
  root.SC_STATES = SC_STATES;
  if (typeof module !== 'undefined' && module.exports) module.exports = SC_STATES;
})(typeof window !== 'undefined' ? window : this);
