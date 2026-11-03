/* sector_cycles_compare.js — SC_COMPARE seam 'sc-compare.v1' (programme 7646, lane L3).
 * Pure render of the Cycles compare tray: up to four series side by side, each labelled with its
 * own kind · basis. No DOM, no fetch, no clock and no aggregate: rows are never blended, averaged
 * or ranked, and series measured on different bases carry an explicit disclosure. Copy is reused
 * from the frozen copy deck and existing in-file pairs; an unconfirmed basis is a gap, never a guess. */
(function (root) {
  'use strict';
  var SC_COMPARE = { version: 'sc-compare.v1', max: 4 };
  /* Reused pairs: cycles.compare_chip, components.clear, cycles.kind_basis_pattern,
     authority.basis_total_return / authority.basis_price_only (_sector_central_coverage.js.j2:81),
     `different basis` (dashboard.html.j2:10529), BASE 'Unavailable today' (sector_cycles.js:1255). */
  var PAIRS = {
    compare: ['Compare', '对比'], clear: ['Clear', '清空'],
    diff: ['different basis', '不同基准'], na: ['Unavailable today', '今日暂不可用']
  };
  var BASIS = { tr: ['total return', '含股息总回报'], price: ['price only', '仅价格'] };
  var KIND = { sector: ['sector', '板块'], basket: ['basket', '篮子'] };
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
  function bi(en, zh) { return '<span class="l-en">' + en + '</span><span class="l-zh">' + zh + '</span>'; }
  function P(p) { return bi(esc(p[0]), esc(p[1])); }
  function pick(p, ctx) { return ctx && ctx.lang === 'zh' ? p[1] : p[0]; }
  /* kind · basis per cycles.kind_basis_pattern "{kind} · {basis}"; tr_fallback / missing / unknown -> gap. */
  function basisOf(rec) {
    var b = rec && rec.basis, k = rec && rec.kind;
    if (!b || b === 'tr_fallback' || !BASIS[b] || !KIND[k]) return null;
    return b;
  }
  function basisLabel(rec) {
    var b = basisOf(rec);
    if (!b) return '<span class="scf-na" data-deck-gap="basis-' + esc((rec && rec.basis) || 'missing') + '">' + P(PAIRS.na) + '</span>';
    var k = KIND[rec.kind], v = BASIS[b];
    return bi(esc(k[0] + ' · ' + v[0]), esc(k[1] + ' · ' + v[1]));
  }
  SC_COMPARE.basisOf = basisOf;
  SC_COMPARE.basisLabel = basisLabel;
  /* True when two or more rows carry confirmed bases that differ. */
  SC_COMPARE.mixedBasis = function (recs) {
    var seen = {}, n = 0, i, b;
    for (i = 0; i < (recs || []).length; i++) { b = basisOf(recs[i]); if (b && !seen[b]) { seen[b] = 1; n++; } }
    return n > 1;
  };
  function nameOf(rec) { var en = rec.name || rec.short || rec.id || ''; return bi(esc(en), esc(rec.name_zh || rec.short_zh || en)); }
  SC_COMPARE.tray = function (selected, ctx) {
    var recs = (selected || []).filter(function (r) { return r && r.id; }).slice(0, SC_COMPARE.max);
    if (!recs.length) return '';
    var extra = ctx && typeof ctx.rowExtra === 'function' ? ctx.rowExtra : null, rows = '', i, r;
    for (i = 0; i < recs.length; i++) {
      r = recs[i];
      rows += '<li class="sc-cmp-row" data-id="' + esc(r.id) + '">' +
        '<span class="sc-cmp-sw" aria-hidden="true"' + (r.accent ? ' style="background:' + esc(r.accent) + '"' : '') + '></span>' +
        '<span class="sc-cmp-nm">' + nameOf(r) + '</span>' +
        '<span class="sc-cmp-basis">' + basisLabel(r) + '</span>' +
        (extra ? '<span class="sc-cmp-x">' + (extra(r) || '') + '</span>' : '') +
        '<button type="button" class="sc-cmp-btn" aria-pressed="true" data-id="' + esc(r.id) + '">' + P(PAIRS.compare) + '</button>' +
        '</li>';
    }
    return '<div class="sc-cmp" role="group" aria-label="' + esc(pick(PAIRS.compare, ctx)) + '">' +
      '<div class="sc-cmp-head"><span class="sc-cmp-h">' + P(PAIRS.compare) + '</span>' +
      (SC_COMPARE.mixedBasis(recs) ? '<span class="cyc-outline sc-cmp-diff">' + P(PAIRS.diff) + '</span>' : '') +
      '<button type="button" class="sc-cmp-clear" data-act="clear">' + P(PAIRS.clear) + '</button></div>' +
      '<ul class="sc-cmp-rows">' + rows + '</ul></div>';
  };
  root.SC_COMPARE = SC_COMPARE;
})(typeof window !== 'undefined' ? window : this);
