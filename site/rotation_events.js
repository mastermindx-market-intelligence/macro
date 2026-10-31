/* rotation_events.js — the Rotation Events rail (Rotation Command W1 — RC-R1/R3/R6).
 *
 * Extracted verbatim from the retired subsector_rotation.html.j2 section #rc-events
 * (Sector Intelligence consolidation). Mounts into #rc-events-mount inside the merged
 * sector_central.html #si-movement section, so the section heading is an h3 (it now
 * lives INSIDE a section rather than being one).
 *
 * Reads marketdata/rotation_events.json + marketdata/sector_fragmentation.json.
 * Absent/failed fetch = graceful quiet note. DISPLAY-ONLY — ranks nothing, gates
 * nothing, sizes nothing.
 *
 * Three renderers, unchanged mechanics:
 *   • renderFlowLanes — the donor ➜ receiver flow-lane hero (#rc-flowmap-content)
 *   • renderClosures  — the "closed recently" strip so nothing vanishes silently
 *   • render          — the event cards + fragmented-sector chips (#rc-events-content)
 */
(function () {
  'use strict';

  function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
  function isZh(){return document.documentElement.getAttribute('data-lang')==='zh';}
  function t(en,zh){return isZh()&&zh?zh:en;}
  function L(en,zh){return '<span class="l-en">'+en+'</span><span class="l-zh">'+(zh==null?en:zh)+'</span>';}
  function pc(v,dp){return v==null?'—':((v>0?'+':'')+(v*100).toFixed(dp==null?1:dp)+'%');}

/* EARLY_CONTEXT_FN_START */
function earlyContextHtml(ev, lang, nowMs) {
  var ZH = lang === 'zh', DAY = 86400000, MAXROWS = 64, MAXCODES = 10, STALE_DAYS = 4;
  var STATE_KEYS = ['DEFENSIVE_RELATIVE_STRENGTH', 'MIXED_ROTATION', 'BROADENING', 'NO_EARLY_SHIFT'];
  var escFn = (typeof esc === 'function') ? esc : function (s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  };
  var W = {
    title: ['Early defensive rotation evidence', '早期防御性轮动证据'],
    unavail: ['Early-context evidence unavailable:', '早期观察暂不可用：'],
    noPacket: ['Early defensive observations are unavailable; this does not mean there is no rotation.', '早期防御性观察暂不可用；这不代表没有轮动。'],
    empty: ['No registered defensive comparisons', '没有已登记的防御性比较'],
    stale: ['Historical/stale snapshot — not a current signal', '历史／陈旧快照——不是当前信号'],
    d1: ['Forecast and sizing: not qualified', '预测与仓位：尚未通过验证'],
    d2: ['Price comparison, not measured fund flows', '价格比较，不代表已测得的资金流'],
    stateCopy: ['Producer-reported overall rotation state:', '数据源报告的整体轮动状态：'],
    noState: ['no state recorded', '未记录状态'],
    states: [['defensive relative strength', '防御板块相对强势'], ['mixed rotation', '混合轮动'], ['broadening', '上涨范围扩大'], ['no early shift', '无早期变化']],
    asOf: ['Observation date', '观察日期'], age: ['UTC calendar age', 'UTC日历天数'], days: ['day(s)', '天'],
    scope: ['Defensive-sector comparisons only. Retailers and broadening proxies remain separate context.', '仅显示防御板块比较；零售商与市场扩散代理仍是独立背景。'],
    avT: ['Availability', '可用时间'], na1: ['unknown', '未知'], avAt: ['first available', '首次可用'],
    lnT: ['Lineage', '来源链'], roots: ['sources', '来源'], more: ['more not shown', '项未显示'],
    reasons: ['Evidence notes', '证据说明'], noCodes: ['none recorded', '无记录'], details: ['Source and window details', '来源与窗口详情'],
    twoS: ['Two-session', '两个交易日'], fiveS: ['Five-session', '五个交易日'], twentyS: ['Twenty-session', '二十个交易日'],
    winNA: ['unavailable', '不可用'], numAbs: ['defensive leg absolute return', '防御端绝对收益'],
    denAbs: ['risk leg absolute return', '风险端绝对收益'], rel: ['relative wealth', '相对财富变化'],
    flatBoth: ['Both legs flat; no measured shift', '两端均持平；无可测变化'],
    defFlat: ['Defensive leg flat', '防御端持平'], riskFlat: ['Risk leg flat', '风险端持平'],
    riskOff: ['Defensive leg rising; risk leg falling', '防御端上涨；风险端下跌'],
    shelter: ['Relative shelter only: both legs falling', '仅相对抗跌：两端均下跌'],
    bothUp: ['Both legs rising; compare their relative returns', '两端均上涨；请比较相对收益'],
    defDown: ['Defensive leg falling; risk leg rising', '防御端下跌；风险端上涨'],
    bothDown: ['Both legs falling; no positive relative shift', '两端均下跌；无正向相对变化'],
    conflict: ['Two-session and twenty-session relative directions disagree', '两日与二十日的相对方向相反'],
    conflictGap: ['Twenty-session comparison unavailable; longer-horizon agreement is unknown.', '二十日比较不可用；较长周期是否一致尚未知。'],
    rowNA: ['Not displayed as evidence', '不作为证据显示'],
    dupConflict: ['Abstained: duplicate alias with conflicting evidence', '未采用：重复别名的证据冲突'],
    dupSame: ['Duplicate alias collapsed; shown once', '重复别名已合并，仅显示一次']
  };
  function T(k) { return W[k][ZH ? 1 : 0]; }
  function E(s) { return escFn(String(s == null ? '' : s).slice(0, 2048)); }
  function codes(list) {
    if (!Array.isArray(list)) return E(T('noCodes'));
    var out = [];
    for (var i = 0; i < list.length && i < 64 && out.length < MAXCODES; i++) {
      if (typeof list[i] === 'string' && list[i]) out.push(list[i].slice(0, 160));
    }
    return out.length ? E(out.join(', ')) : E(T('noCodes'));
  }
  function ts(s) {
    if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return NaN;
    var v = Date.parse(s + 'T00:00:00Z');
    return isFinite(v) && new Date(v).toISOString().slice(0, 10) === s ? v : NaN;
  }
  function N(v) { return typeof v === 'number' && isFinite(v) ? v : null; }
  function pct(v) { return (v > 0 ? '+' : '') + v.toFixed(2) + '%'; }
  function block(inner) {
    return '<section class="rc-early-context" aria-label="' + E(T('title')) + '"><h4 class="rc-ec-title">' + E(T('title')) + '</h4>' + inner
      + '<p class="rc-ec-disclosure">' + E(T('d1')) + ' · ' + E(T('d2')) + '</p></section>';
  }
  function unavail(code) { return block('<p class="rc-ec-unavail" role="note">' + E(T('unavail') + ' ' + code) + '</p>'); }
  // The caller supplies the display clock. No second, hidden clock or market calendar.
  if (N(nowMs) === null || nowMs < 0 || !isFinite(new Date(nowMs).getTime())) return unavail('CLOCK_UNUSABLE');
  var today = Math.floor(nowMs / DAY) * DAY;
  var ctx = ev && typeof ev === 'object' && !Array.isArray(ev) ? ev.early_context : undefined;
  if (ctx === undefined || ctx === null) return block('<p class="rc-ec-nopacket" role="note">' + E(T('noPacket')) + '</p>');
  if (typeof ctx !== 'object' || Array.isArray(ctx)) return unavail('PACKET_UNREADABLE');
  if (ctx.schema !== 'rotation_early_context/v1' || ctx.definition_id !== 'rotation_early_context/1' || ctx.display_only !== true) return unavail('SCHEMA_UNRECOGNIZED');
  var asOf = ctx.as_of, asOfTs = ts(asOf);
  if (!isFinite(asOfTs)) return unavail('AS_OF_UNREADABLE');
  if (asOfTs > today) return unavail('AS_OF_IN_FUTURE');
  var si = ctx.state === null ? -1 : STATE_KEYS.indexOf(ctx.state);
  if (si < 0 && ctx.state !== null) return unavail('STATE_UNRECOGNIZED');
  var pairs = ctx.pairs;
  if (!Array.isArray(pairs)) return unavail('PACKET_UNREADABLE');
  if (pairs.length > MAXROWS) return unavail('ROW_LIMIT_EXCEEDED');
  if (pairs.some(function(p){ return !p || typeof p !== 'object' || Array.isArray(p); })) return unavail('PAIR_UNREADABLE');
  var age = Math.floor((today - asOfTs) / DAY), out = [];
  if (age >= STALE_DAYS) out.push('<p class="rc-ec-stale" role="note"><strong>' + E(T('stale')) + '</strong></p>');
  out.push('<p class="rc-ec-asof">' + E(T('asOf')) + ': <time datetime="' + E(asOf) + '">' + E(asOf) + '</time> · ' + E(T('age')) + ': ' + age + ' ' + E(T('days')) + '</p>');
  var av = ctx.availability && typeof ctx.availability === 'object' ? ctx.availability : {};
  var ln = ctx.lineage && typeof ctx.lineage === 'object' ? ctx.lineage : {};
  out.push('<p class="rc-ec-quality">' + E(T('avT') + ': ' + (typeof av.status === 'string' ? av.status : T('na1')) + ' · ' + T('lnT') + ': ' + (typeof ln.status === 'string' ? ln.status : T('na1'))) + '</p>');
  var def = pairs.filter(function(p){ return p.context_group === 'defensive_sector'; });
  function rowSig(r) {
    return JSON.stringify({schema:r.schema, requested_as_of:r.requested_as_of, value_as_of:r.value_as_of,
      eligible_2s:r.eligible_2s, horizons:r.horizons, reason_codes:r.reason_codes, lineage:r.lineage});
  }
  var byAlias = Object.create(null), mode = Object.create(null), hidden = Object.create(null), j, k;
  for (j = 0; j < def.length; j++) {
    if (typeof def[j].num !== 'string' || typeof def[j].den !== 'string') continue;
    k = JSON.stringify([def[j].num.trim().toUpperCase(), def[j].den.trim().toUpperCase()]);
    (byAlias[k] = byAlias[k] || []).push(j);
  }
  for (k in byAlias) {
    var idx = byAlias[k];
    if (idx.length < 2) continue;
    var same = true, sig0;
    try {
      sig0 = rowSig(def[idx[0]]);
      for (var m1 = 1; m1 < idx.length; m1++) if (rowSig(def[idx[m1]]) !== sig0) same = false;
    } catch (err) { same = false; }
    for (var m2 = 0; m2 < idx.length; m2++) mode[idx[m2]] = same ? 'same' : 'conflict';
    if (same) for (var m3 = 1; m3 < idx.length; m3++) hidden[idx[m3]] = true;
  }
  function checkWin(w, sessions) {
    if (!w || typeof w !== 'object' || Array.isArray(w)) return {ok:false, why:'WINDOW_ABSENT'};
    if (w.eligible !== true) return {ok:false, why:'WINDOW_NOT_INDEPENDENTLY_ELIGIBLE'};
    if (w.sessions !== sessions) return {ok:false, why:'WINDOW_SESSION_COUNT_MISMATCH'};
    if (w.end !== asOf) return {ok:false, why:'WINDOW_END_DATE_MISMATCH'};
    var st = ts(w.start);
    if (!isFinite(st) || st >= asOfTs) return {ok:false, why:'WINDOW_START_UNREADABLE'};
    var n = N(w.numerator_return_pct), d = N(w.denominator_return_pct), r = N(w.ratio_return_pct);
    if (n === null || d === null || r === null) return {ok:false, why:'WINDOW_VALUE_NOT_A_FINITE_NUMBER'};
    if (!(n > -100) || !(d > -100)) return {ok:false, why:'WINDOW_ABSOLUTE_RETURN_AT_OR_BELOW_MINUS_100'};
    if (!(Math.abs(((1 + n / 100) / (1 + d / 100) - 1) * 100 - r) <= 1e-6)) return {ok:false, why:'WINDOW_RATIO_INCONSISTENT'};
    return {ok:true, n:n, d:d, r:r, w:w};
  }
  function dirKey(n, d, r) {
    if (n === 0 && d === 0) return 'flatBoth';
    if (n === 0) return 'defFlat';
    if (d === 0) return 'riskFlat';
    if (n > 0 && d > 0) return 'bothUp';
    if (n > 0) return 'riskOff';
    if (d > 0) return 'defDown';
    return r > 0 ? 'shelter' : 'bothDown';
  }
  function winHtml(title, c) {
    if (!c.ok) return '<p class="rc-ec-win-na" role="note">' + E(title + ' — ' + T('winNA') + ': ' + c.why) + '</p>';
    return '<div class="rc-ec-window"><h5>' + E(title) + '</h5><dl class="rc-ec-values">'
      + '<div><dt>' + E(T('numAbs')) + '</dt><dd>' + E(pct(c.n)) + '</dd></div>'
      + '<div><dt>' + E(T('denAbs')) + '</dt><dd>' + E(pct(c.d)) + '</dd></div>'
      + '<div><dt>' + E(T('rel')) + '</dt><dd>' + E(pct(c.r)) + '</dd></div></dl></div>';
  }
  function rowHtml(row, note) {
    var o = ['<article class="rc-ec-pair">'];
    if (note) o.push('<p class="rc-ec-row-note">' + E(note) + '</p>');
    function na(code) { return o.join('') + '<p class="rc-ec-row-na" role="note">' + E(T('rowNA') + ': ' + code) + '</p></article>'; }
    if (row.schema !== 'ratio_lens.short_horizon.v1') return na('ROW_SCHEMA_UNRECOGNIZED');
    if (typeof row.num !== 'string' || !row.num.trim() || typeof row.den !== 'string' || !row.den.trim()) return na('ROW_PAIR_IDENTITY_MISSING');
    o.push('<h5 class="rc-ec-pair-title">' + E(row.num + ' / ' + row.den) + '</h5>');
    if (row.requested_as_of !== asOf || row.value_as_of !== asOf) return na('ROW_DATE_MISMATCH');
    var hz = row.horizons && typeof row.horizons === 'object' && !Array.isArray(row.horizons) ? row.horizons : {};
    var e2 = row.eligible_2s === true ? checkWin(hz['2s'], 2) : {ok:false, why:'ROW_2S_NOT_ELIGIBLE'};
    var e5 = checkWin(hz['5s'], 5), e20 = checkWin(hz['20s'], 20);
    if (e2.ok) o.push('<p class="rc-ec-label">' + E(T(dirKey(e2.n, e2.d, e2.r))) + '</p>');
    o.push(winHtml(T('twoS'), e2));
    if (e2.ok && e20.ok && e2.r * e20.r < 0) o.push('<p class="rc-ec-conflict" role="note"><strong>' + E(T('conflict')) + '</strong> · ' + E(pct(e2.r) + ' / ' + pct(e20.r)) + '</p>');
    else if (e2.ok && !e20.ok) o.push('<p class="rc-ec-conflict" role="note">' + E(T('conflictGap')) + '</p>');
    o.push('<details class="rc-ec-details"><summary>' + E(T('details')) + '</summary>');
    var nm = ZH ? row.name_zh || row.name_en : row.name_en || row.name_zh;
    if (typeof nm === 'string') o.push('<p>' + E(nm) + '</p>');
    o.push(winHtml(T('fiveS'), e5), winHtml(T('twentyS'), e20));
    o.push('<p class="rc-ec-meta">' + E(typeof row.pair_id === 'string' ? row.pair_id : '') + ' · ' + E(asOf) + '</p>');
    [e2, e5, e20].forEach(function(c){ if(c.ok) o.push('<p class="rc-ec-meta">' + E(c.w.start + ' → ' + c.w.end) + ' · ' + codes(c.w.reason_codes) + '</p>'); });
    o.push('<p class="rc-ec-reasons">' + E(T('reasons') + ': ') + codes(row.reason_codes) + '</p></details>');
    return o.join('') + '</article>';
  }
  if (!def.length) out.push('<p class="rc-ec-empty" role="note">' + E(T('empty')) + '</p>');
  else {
    out.push('<div class="rc-ec-grid">');
    for (var n2 = 0; n2 < def.length; n2++) {
      if (hidden[n2]) continue;
      if (mode[n2] === 'conflict') out.push('<article class="rc-ec-pair"><h5>' + E(def[n2].num + ' / ' + def[n2].den) + '</h5><p class="rc-ec-row-na" role="note">' + E(T('dupConflict')) + '</p></article>');
      else out.push(rowHtml(def[n2], mode[n2] === 'same' ? T('dupSame') : ''));
    }
    out.push('</div>');
  }
  out.push('<details class="rc-ec-packet"><summary>' + E(T('details')) + '</summary><p>' + E(T('stateCopy')) + ' ' + E(si < 0 ? T('noState') : W.states[si][ZH ? 1 : 0]) + '</p><p>' + E(T('scope')) + '</p>');
  out.push('<p>' + E(T('avAt') + ': ' + (typeof av.available_at === 'string' ? av.available_at : T('na1'))) + '</p>');
  out.push('<p>' + E(T('roots') + ': ') + codes(ln.roots) + '</p><p>' + E(T('reasons') + ': ') + codes(ctx.reason_codes) + '</p></details>');
  return block(out.join(''));
}
/* EARLY_CONTEXT_FN_END */

  /* ── styles (injected once, guarded by element id — subsector_rotation.js model).
     Carried over from the retired page's own <style> block; `#rc-events h2` becomes
     `#rc-events h3` because the heading demoted when the section moved inside
     #si-movement. ── */
  function injectStyle(){
    if(document.getElementById('rc-events-style')) return;
    var c=''
      +'.rc-early-context{margin:14px 0;padding:14px;border:1px solid var(--line);border-radius:var(--r-card,12px);background:var(--panel2);overflow-wrap:anywhere;}'
      +'.rc-ec-title{font-size:15px;font-weight:800;margin:0 0 6px;}.rc-ec-asof,.rc-ec-quality{font-size:11px;color:var(--muted);margin:4px 0;}'
      +'.rc-ec-grid{display:grid;align-items:start;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:10px;margin:12px 0;}'
      +'.rc-ec-pair{min-width:0;padding:12px;border:1px solid var(--line);border-radius:var(--r-ctl,8px);background:var(--panel);}'
      +'.rc-ec-pair h5{font-size:12px;margin:0 0 5px;}.rc-ec-pair .rc-ec-pair-title{font-size:14px;}.rc-ec-label{font-size:12px;line-height:1.5;margin:6px 0 10px;}'
      +'.rc-ec-values{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:6px 0 10px;}.rc-ec-values dt{font-size:10px;color:var(--muted);line-height:1.35;}.rc-ec-values dd{font-size:15px;font-weight:700;font-variant-numeric:tabular-nums;margin:5px 0 0;}'
      +'.rc-ec-stale,.rc-ec-conflict{border-left:3px solid var(--warn);padding:6px 9px;color:var(--ink-warn,var(--warn));font-size:11px;line-height:1.5;}'
      +'.rc-ec-details,.rc-ec-packet{font-size:11px;line-height:1.5;}.rc-ec-details summary,.rc-ec-packet summary{cursor:pointer;padding:5px 0;}.rc-ec-details summary:focus-visible,.rc-ec-packet summary:focus-visible{outline:2px solid var(--link);outline-offset:2px;}'
      +'.rc-ec-meta,.rc-ec-reasons,.rc-ec-row-note,.rc-ec-disclosure{font-size:10.5px;line-height:1.5;color:var(--muted);}.rc-ec-win-na,.rc-ec-row-na,.rc-ec-empty,.rc-ec-nopacket,.rc-ec-unavail{font-size:12px;line-height:1.5;}'
      +'#rc-events { margin:0 2px 22px; }'
      +'#rc-events h3 { font-size:17px; font-weight:800; letter-spacing:-.015em; margin:0 0 4px; }'
      +'.rc-sub { color:var(--muted); font-size:12px; margin:0 0 10px; max-width:84ch; line-height:1.5; }'
      +'.rc-grid { display:flex; flex-wrap:wrap; gap:10px; }'
      +'.rc-card { flex:1 1 300px; min-width:260px; border-radius:12px; border:1px solid var(--line);'
      +'  background:var(--panel); padding:12px 14px; }'
      +'.rc-card.rc-major { border-left:4px solid var(--warn); }'
      +'.rc-hd { display:flex; align-items:baseline; gap:7px; margin-bottom:5px; flex-wrap:wrap; }'
      +'.rc-title { font-weight:800; font-size:13.5px; }'
      +'.rc-sev { font-size:9.5px; font-weight:700; text-transform:uppercase; padding:2px 7px; border-radius:6px;'
      +'  background:color-mix(in srgb,var(--muted) 15%,transparent); color:var(--muted); letter-spacing:.04em; }'
      +'.rc-sev.major { background:color-mix(in srgb,var(--warn) 20%,transparent); color:var(--ink-warn, var(--warn)); }'
      +'.rc-sev.notable { background:color-mix(in srgb,var(--link) 16%,transparent); color:var(--ink-link, var(--link)); }'
      +'.rc-day { font-size:11px; color:var(--muted); margin-left:auto; font-variant-numeric:tabular-nums; }'
      +'.rc-copy { font-size:12.5px; line-height:1.55; }'
      +'.rc-receipts { margin-top:6px; font-size:10.5px; color:var(--muted); font-variant-numeric:tabular-nums; }'
      +'.rc-stale { font-style:italic; }'
      +'.rc-quiet { color:var(--muted); font-size:12.5px; padding:8px 0; }'
      +'.rc-frag { margin-top:12px; }'
      +'.rc-frag-hd { font-size:10.5px; font-weight:800; text-transform:uppercase; letter-spacing:.07em;'
      +'  color:var(--muted); margin:0 0 7px; }'
      +'.rc-frag-chips { display:flex; flex-wrap:wrap; gap:6px; }'
      +'.rc-frag-chip { font-size:11px; padding:4px 10px; border-radius:8px; border:1px solid var(--line);'
      +'  background:color-mix(in srgb,var(--warn) 9%,var(--panel2)); line-height:1.45; }'
      +'.rc-frag-chip b { font-weight:800; }'
      +'.rc-caveat { margin-top:10px; font-size:10.5px; color:var(--muted); line-height:1.55; }'
      /* ── Flow-lanes hero (.rcf-*) ── */
      +'#rc-flowmap-content { margin-bottom:14px; }'
      +'.rcf-empty { color:var(--muted); font-size:12.5px; padding:8px 0; }'
      +'.rcf-lane { display:flex; flex-wrap:wrap; align-items:center; gap:8px 12px;'
      +'  padding:10px 13px; border-radius:11px; border:1px solid var(--line);'
      +'  background:var(--panel2); margin-bottom:8px; position:relative; }'
      +'.rcf-lane.rcf-handoff    { border-left:4px solid var(--link); }'
      +'.rcf-lane.rcf-into_strength { border-left:4px solid var(--up); }'
      +'.rcf-lane.rcf-contagion_break { border-left:4px solid var(--warn); }'
      +'.rcf-lane.rcf-faltering  { border-left:4px solid var(--muted); }'
      +'.rcf-pill { font-size:11.5px; font-weight:700; padding:3px 10px; border-radius:8px;'
      +'  background:color-mix(in srgb,var(--text) 8%,var(--panel)); border:1px solid var(--line);'
      +'  white-space:nowrap; }'
      +'.rcf-arrow { font-size:13px; color:var(--muted); flex:none; }'
      +'.rcf-state { font-size:12.5px; font-weight:600; flex:1 1 160px; min-width:120px; }'
      +'.rcf-stance { font-size:10.5px; font-weight:700; padding:2px 8px; border-radius:6px;'
      +'  white-space:nowrap; }'
      +'.rcf-stance.rcf-watch { background:color-mix(in srgb,var(--link) 14%,transparent); color:var(--ink-link, var(--link)); }'
      +'.rcf-stance.rcf-favour { background:color-mix(in srgb,var(--up) 14%,transparent); color:var(--ink-up, var(--up)); }'
      +'.rcf-stance.rcf-aside  { background:color-mix(in srgb,var(--warn) 14%,transparent); color:var(--ink-warn, var(--warn)); }'
      +'.rcf-stance.rcf-weak   { background:color-mix(in srgb,var(--muted) 14%,transparent); color:var(--muted); }'
      +'.rcf-decay { width:100%; height:5px; border-radius:3px;'
      +'  background:var(--panel2); border:1px solid var(--line); overflow:hidden; margin-top:4px; }'
      +'.rcf-decay-bar { height:100%; border-radius:3px; background:var(--warn); transition:width .3s; }'
      +'.rcf-decay-cap { font-size:10px; color:var(--ink-warn, var(--warn)); margin-top:3px; }'
      +'.rcf-help { display:inline-block; font-size:9.5px; font-weight:700; color:var(--muted);'
      +'  border:1px solid var(--line); border-radius:50%; width:16px; height:16px; line-height:14px;'
      +'  text-align:center; cursor:help; flex:none; }'
      +'.rcf-footer { font-size:10.5px; color:var(--muted); margin-top:4px; line-height:1.5; }'
      +'.rcf-coldstart-note { font-size:10px; color:var(--muted); margin-left:6px; }'
      /* ── Closures strip (.rcx-*) ── */
      +'#rc-closures { margin-bottom:10px; }'
      +'.rcx-strip { font-size:11.5px; color:var(--muted); border:1px solid var(--line);'
      +'  border-radius:9px; padding:7px 12px; background:var(--panel2); }'
      +'.rcx-toggle { cursor:pointer; font-weight:700; user-select:none; }'
      +'.rcx-toggle:hover { color:var(--text); }'
      +'.rcx-list { margin-top:7px; display:flex; flex-direction:column; gap:4px; }'
      +'.rcx-row { font-size:11px; color:var(--muted); }'
      +'.rcx-foot { margin-top:5px; font-size:10px; color:var(--muted); font-style:italic; }'
      +'@media (max-width:520px) {'
      +'  .rcf-lane { gap:6px 8px; }'
      +'  .rcf-state { flex-basis:100%; }'
      +'  .rcf-decay { margin-top:3px; }'
      +'}';
    var s=document.createElement('style');
    s.id='rc-events-style';
    s.textContent=c;
    document.head.appendChild(s);
  }

  /* ── mount: build the section shell into #rc-events-mount (once). Static copy uses
     dual l-en/l-zh spans so a language switch needs no rebuild. ── */
  function mount(){
    var host=document.getElementById('rc-events-mount');
    if(!host) return false;
    if(document.getElementById('rc-events')) return true;
    host.innerHTML=''
      +'<section id="rc-events" aria-label="Rotation events">'
      +'<h3>⟲ '+L('Rotation Events','轮动事件')+'</h3>'
      +'<p class="rc-sub">'+L(
          'Price-based evidence of changing sector leadership. Compare early observations with recorded events; neither is a buy list.',
          '基于价格的板块领导力变化证据。比较早期观察与已记录事件；两者均非买入清单。')+'</p>'
      +'<div id="rc-early-context"></div>'
      +'<div id="rc-flowmap-content"></div>'
      +'<div id="rc-closures"></div>'
      +'<div id="rc-events-content"><p class="rc-quiet">'
      +'<span class="l-en">Loading…</span><span class="l-zh">加载中…</span></p></div>'
      +'</section>';
    return true;
  }

  /* ── Part 5A: renderFlowLanes — builds the #rc-flowmap-content hero ── */
  function renderFlowLanes(ev){
    var el=document.getElementById('rc-flowmap-content');
    if(!el) return;
    // graceful degrade: no velocity_board → entire section hidden already (we just render lanes)
    var active=(ev&&ev.active)||[];
    if(!active.length){
      el.innerHTML='<p class="rcf-empty">'
        +t('No confirmed rotation events in this snapshot. Early observations above are separate; an empty event list is not an all-clear.',
           '此快照无已确认的轮动事件。上方早期观察独立显示；事件列表为空不代表风险已排除。')
        +'</p>';
      return;
    }
    var html='';
    var sevRank={major:0,notable:1,standard:2};
    var sorted=active.slice().sort(function(a,b){
      var d=(sevRank[a.severity]!=null?sevRank[a.severity]:9)-(sevRank[b.severity]!=null?sevRank[b.severity]:9);
      return d!==0?d:String(b.started||'').localeCompare(String(a.started||''));
    });
    sorted.forEach(function(e){
      // Determine event_type — default to handoff for v1 payload without event_type (graceful degrade)
      var etype=e.event_type||'handoff';
      /* Donor/receiver labels. Both languages are resolved, not just the active one:
         the hover card writes an EN and a ZH attribute at the same time, and a card
         built from only the active language leaves the other half in English until
         the next re-render. */
      var donorEn,donorZh,recvEn,recvZh;
      if(etype==='correlation_break'||etype==='contagion_break'){
        // contagion — use a+b from contagion field or from the event itself
        donorEn=esc(e.from_leg&&(e.from_leg.name_en||e.from_leg.key)||'—');
        donorZh=esc(e.from_leg&&(e.from_leg.name_zh||e.from_leg.name_en||e.from_leg.key)||'—');
        recvEn=esc(e.to_leg&&(e.to_leg.name_en||e.to_leg.key)||'—');
        recvZh=esc(e.to_leg&&(e.to_leg.name_zh||e.to_leg.name_en||e.to_leg.key)||'—');
      } else {
        donorEn=esc(e.from_leg&&(e.from_leg.name_en||e.from_leg.key)||e.donor||'—');
        donorZh=esc(e.from_leg&&(e.from_leg.name_zh||e.from_leg.name_en)||e.donor||'—');
        recvEn=esc(e.to_leg&&(e.to_leg.name_en||e.to_leg.key)||e.receiver||'—');
        recvZh=esc(e.to_leg&&(e.to_leg.name_zh||e.to_leg.name_en)||e.receiver||'—');
      }
      // Mag-7 basket pill: never show "MAGS"
      if((e.to_leg&&(e.to_leg.key==='mag7'||e.to_leg.key==='mag7_basket'))||e.receiver==='mag7_basket'){
        recvEn='Mag-7 basket'; recvZh='七巨头等权篮子';
      }
      var donorName=isZh()?donorZh:donorEn, receiverName=isZh()?recvZh:recvEn;
      // Health / faltering
      var h=e.health||null;
      var isFaltering=!!(h&&(h.weakening||h.lapse_count>=2||h.neg_run>=2));
      var effectiveType=isFaltering?'faltering':etype;

      // State line and stance per type. The state line doubles as the hover card's
      // headline, so it is kept in both languages.
      var stateLineEn,stateLineZh,stanceText,stanceCls;
      if(effectiveType==='into_strength'){
        stateLineEn='Strength rotating toward '+recvEn;
        stateLineZh='强势正在轮向'+recvZh;
        stanceText=t('In favour — watch for entry','处于优势——留意入场');
        stanceCls='rcf-favour';
      } else if(effectiveType==='contagion_break'||effectiveType==='correlation_break'){
        stateLineEn=donorEn+' and '+recvEn+' no longer offsetting — falling together';
        stateLineZh=donorZh+'与'+recvZh+'不再互相对冲——同步下跌';
        stanceText=t('Stand aside — diversification fading','暂避——分散效果减弱');
        stanceCls='rcf-aside';
      } else if(effectiveType==='faltering'){
        stateLineEn=donorEn+'→'+recvEn+' rotation weakening';
        stateLineZh=donorZh+'→'+recvZh+'轮动转弱';
        stanceText=t('Rotation weakening — may close','轮动转弱——或将关闭');
        stanceCls='rcf-weak';
      } else {
        // handoff (default for unknown types — cautious fallback per spec)
        stateLineEn='Recorded leadership shift: '+donorEn+' → '+recvEn;
        stateLineZh='已记录的领导力转移：'+donorZh+' → '+recvZh;
        stanceText=t('Watch — don\'t chase','观望，不要追高');
        stanceCls='rcf-watch';
      }
      var stateLine=isZh()?stateLineZh:stateLineEn;

      /* Hover card (Tier-2). Rewritten 2026-08-04 with the popup overhaul: the old
         tip was one run-on chain of eight machine fragments — "Out: X −30% from
         peak · In: Y +12.6% off low · Ratio: +6.3%/10s · Historical: about half
         reach +7.8% in ~9 sessions (n=8) · Heads-up…" — with the English suffixes
         hardcoded, so the Chinese card read half in English. It is now a headline,
         two plain sentences, and a receipt line for the base rate. Both languages
         are built separately rather than sharing one pre-resolved string. */
      var r=e.receipts||{};
      var bodyEn=[],bodyZh=[];
      if(r.blowoff&&r.blowoff.drawdown_pct!=null){
        var dd=(r.blowoff.drawdown_pct*100).toFixed(0);
        bodyEn.push(donorEn+' sits '+dd+'% below its peak.');
        bodyZh.push(donorZh+'较峰值低 '+dd+'%。');
      }
      if(r.turn&&r.turn.off_low_pct!=null){
        var ol=(r.turn.off_low_pct*100).toFixed(1);
        bodyEn.push(recvEn+' is '+ol+'% up off its low.');
        bodyZh.push(recvZh+'自低点回升 '+ol+'%。');
      }
      if(r.ratio&&r.ratio.ratio_chg_10s!=null){
        var rc=Math.abs(r.ratio.ratio_chg_10s*100).toFixed(1);
        bodyEn.push('The two have moved '+rc+'% apart over the last ten sessions'
          +(r.ratio.ratio_20s_high?', the widest gap in a month.':'.'));
        bodyZh.push('近十个交易日两者差距扩大 '+rc+'%'+(r.ratio.ratio_20s_high?'，为一个月来最大。':'。'));
      }
      bodyEn.push('A heads-up on shifting leadership, not a buy signal.');
      bodyZh.push('这是领导权变化的提示，并非买入信号。');
      /* The receipt strip — base rates, sample sizes and money flow. Sanctioned
         Tier-2 home for the machine facts the body must not carry. */
      var rcEn=[],rcZh=[];
      var ru=(ev&&ev.ruler&&ev.ruler.modern&&ev.ruler.modern.run_pct)?ev.ruler.modern:null;
      if(ru&&ru.n>=5){
        rcEn.push('past handoffs: half ran +'+ru.run_pct.median+'% within ~'+ru.sessions_to_peak.median+' sessions (n='+ru.n+')');
        rcZh.push('历史同类轮动：半数在约'+ru.sessions_to_peak.median+'个交易日内录得 +'+ru.run_pct.median+'%（n='+ru.n+'）');
      }
      var fr=e.flow_receipts||null;
      if(fr&&fr.receiver&&fr.receiver.flow_5d_mn!=null){
        var fm='$'+(fr.receiver.flow_5d_mn/1e6).toFixed(0)+'M';
        rcEn.push('ETF flow 5d '+fm+(fr.receiver.flow_asof?' · as of '+esc(fr.receiver.flow_asof):''));
        rcZh.push('ETF 5日资金 '+fm+(fr.receiver.flow_asof?' · 截至 '+esc(fr.receiver.flow_asof):''));
      }

      var laneClass='rcf-lane rcf-'+esc(etype.replace('correlation_break','contagion_break'));
      html+='<div class="'+laneClass+'"'
        +' data-tip-t-en="'+esc(stateLineEn)+'" data-tip-t-zh="'+esc(stateLineZh)+'"'
        +' data-tip-en="'+esc(bodyEn.join(' '))+'" data-tip-zh="'+esc(bodyZh.join(''))+'"'
        +(rcEn.length?' data-tip-rc-en="'+esc(rcEn.join(' · '))+'" data-tip-rc-zh="'+esc(rcZh.join(' · '))+'"':'')
        +'>'
        +'<span class="rcf-pill">'+donorName+'</span>'
        +'<span class="rcf-arrow">&#x279C;</span>'
        +'<span class="rcf-pill">'+receiverName+'</span>'
        +'<span class="rcf-state">'+stateLine+'</span>'
        +'<span class="rcf-stance '+stanceCls+'">'+stanceText+'</span>';
      // Decay meter for faltering events
      if(effectiveType==='faltering'&&h){
        var stc=h.sessions_to_close!=null?h.sessions_to_close:(h.sessions_to_close_bound||null);
        var lapse=h.lapse_count||0;
        var bound=(stc!=null?stc:5);
        var barPct=Math.max(0,Math.min(100,100*(1-lapse/Math.max(bound,1))));
        html+='<div style="width:100%">'
          +'<div class="rcf-decay"><div class="rcf-decay-bar" style="width:'+barPct.toFixed(0)+'%"></div></div>'
          +(stc!=null?'<div class="rcf-decay-cap">'+t('may close in '+stc+' sessions','或于'+stc+'个交易日内关闭')+'</div>':'')
          +'</div>';
      }
      html+='</div>';
    });
    // Footer
    var asof=(ev&&ev.as_of)||'—';
    var coldstarNote=(ev&&ev.coldstart)?
      '<span class="rcf-coldstart-note"><span class="rcf-help"'
      +' data-tip-t-en="Counts look reset" data-tip-t-zh="计数看似重置"'
      +' data-tip-en="History was rebuilt last night, so the day counts start over. The events themselves are unchanged."'
      +' data-tip-zh="昨夜重建了历史，因此天数从头计起。事件本身没有变化。">?</span></span>'
      :'';
    html+='<div class="rcf-footer">'
      +'<span class="l-en">A heads-up on shifting leadership — not a buy list. as of '+esc(asof)+'</span>'
      +'<span class="l-zh">领导权变化的提示——非买入清单。截至 '+esc(asof)+'</span>'
      +' <span class="rcf-help" tabindex="0" role="button" aria-label="details"'
      +' data-tip-t-en="How these are tracked" data-tip-t-zh="这些事件如何被跟踪"'
      +' data-tip-en="Every event is logged and its outcome followed. Most are still being measured, so nothing here ranks, gates or sizes anything."'
      +' data-tip-zh="每个事件都会记录并跟踪结果。多数仍在观察中，因此此处不排名、不门控、不调仓。"'
      +' data-tip-rc-en="each series measured on its own history · Mag-7 = equal-weight basket, not the MAGS ETF · logging began 2026-06-25"'
      +' data-tip-rc-zh="各序列以自身历史衡量 · 七巨头为等权篮子，非 MAGS ETF · 自 2026-06-25 起记录">?</span>'
      +coldstarNote
      +'</div>';
    el.innerHTML=html;
  }

  /* ── leg display names for the closures strip ──────────────────────────────
     Closure rows carry their OWN names (from_name_en/zh + to_name_en/zh, written by
     engine/rotation_events.py) because a closed pair has left active[] — there is
     nothing left in the payload to look a name up from. Rows written before that
     landed, or a stale cached payload, fall through a ladder so the strip never
     prints a machine slug (DESIGN_DOCTRINE Law 2):
       1. names stored on the row
       2. harvest from an active event in the SAME payload (matched on leg key)
       3. prettified slug — last resort, never blocks the render
     Step 3 has no translation to offer, so zh shows the prettified English. ── */
  var LEGNAMES={};
  function harvestLegNames(ev){
    LEGNAMES={};
    ((ev&&ev.active)||[]).forEach(function(e){
      [e.from_leg,e.to_leg,e.donor,e.receiver].forEach(function(leg){
        if(leg&&typeof leg==='object'&&leg.key&&(leg.name_en||leg.name_zh)){
          LEGNAMES[leg.key]={en:leg.name_en||leg.name_zh,zh:leg.name_zh||leg.name_en};
        }
      });
    });
  }
  var LEG_ACRONYMS={ai:'AI',etf:'ETF',reit:'REIT',ipo:'IPO',us:'US',hk:'HK',esg:'ESG'};
  function prettifySlug(k){
    var parts=String(k==null?'':k).split(/[_\-]+/).filter(Boolean);
    if(!parts.length) return '';
    return parts.map(function(w,i){
      var a=LEG_ACRONYMS[w.toLowerCase()];
      if(a) return a;
      return i===0?w.charAt(0).toUpperCase()+w.slice(1):w;
    }).join(' ');
  }
  function legName(row,side){
    var stored=isZh()?(row[side+'_name_zh']||row[side+'_name_en'])
                     :(row[side+'_name_en']||row[side+'_name_zh']);
    if(stored) return stored;
    var key=side==='from'?(row.from_leg||row.from_sector||row.donor)
                         :(row.to_leg||row.to_sector||row.receiver);
    if(key&&typeof key==='object') key=key.key;   // defensive: a nested leg object
    if(!key) return '—';
    var h=LEGNAMES[key];
    if(h) return isZh()?h.zh:h.en;
    return prettifySlug(key);
  }

  /* ── Part 5A: renderClosures — builds the #rc-closures strip ── */
  function renderClosures(ev){
    var el=document.getElementById('rc-closures');
    if(!el) return;
    // graceful degrade: no closures data → hide entirely
    var closures=(ev&&(ev.closures||ev.closed_recent||ev.closed_tonight))||[];
    if(!closures.length){ el.innerHTML=''; return; }
    var REASON={
      ratio_slope_flipped:{en:'the move reversed',zh:'走势反转'},
      conditions_lapsed  :{en:'signals faded',    zh:'信号消退'},
      ttl                :{en:'ran its course',    zh:'自然结束'}
    };
    harvestLegNames(ev);
    var N=closures.length;
    var listHtml='';
    closures.forEach(function(c){
      var donor=esc(legName(c,'from'));
      var recv=esc(legName(c,'to'));
      var rkey=c.reason||c.close_reason||'';
      var rmap=REASON[rkey]||{en:esc(rkey),zh:esc(rkey)};
      var reasonPlain=isZh()?rmap.zh:rmap.en;
      var dayN=c.day_n!=null?c.day_n:'—';
      listHtml+='<div class="rcx-row">'
        +donor+' → '+recv+' · '
        +t('ended: ','结束：')+reasonPlain+' · '
        +t('lasted ','持续 ')+dayN+t(' sessions','个交易日')
        +'</div>';
    });
    var expanded=false;
    var id='rcx-list-'+Math.random().toString(36).slice(2,7);
    el.innerHTML='<div class="rcx-strip">'
      +'<span class="rcx-toggle" id="rcx-tog-'+id+'">'
      +'<span class="l-en">Closed recently: '+N+' ▾</span>'
      +'<span class="l-zh">近期关闭：'+N+' ▾</span>'
      +'</span>'
      +'<div class="rcx-list" id="'+id+'" style="display:none">'+listHtml
      +'<div class="rcx-foot">'
      +t('Shown so nothing disappears silently.','列出以避免事件悄然消失。')
      +'</div></div></div>';
    var tog=el.querySelector('#rcx-tog-'+id);
    var lst=el.querySelector('#'+id);
    if(tog&&lst){
      tog.addEventListener('click',function(){
        expanded=!expanded;
        lst.style.display=expanded?'':'none';
      });
    }
  }

  function render(ev, frag){
    var el=document.getElementById('rc-events-content');
    if(!el) return;
    var html='';
    var active=(ev&&ev.active)||[];
    if(!active.length){
      html+='<p class="rc-quiet">'+t('No active rotation events — quiet state is a valid state.',
        '当前无活跃轮动事件——安静状态是有效状态。')+'</p>';
    }else{
      var sevRank={major:0,notable:1,standard:2};
      active=active.slice().sort(function(a,b){
        var d=(sevRank[a.severity]!=null?sevRank[a.severity]:9)-(sevRank[b.severity]!=null?sevRank[b.severity]:9);
        return d!==0?d:String(b.started||'').localeCompare(String(a.started||''));
      });
      html+='<div class="lst-wrap"><div class="rc-grid lst-collapse lst-cap4 is-collapsed">';
      active.forEach(function(e){
        var sev=e.severity||'standard';
        var title=isZh()
          ? esc(e.from_leg.name_zh)+' → '+esc(e.to_leg.name_zh)+'（'+esc(e.sector_name_zh)+'）'
          : esc(e.from_leg.name_en)+' → '+esc(e.to_leg.name_en)+' ('+esc(e.sector_name_en)+')';
        var r=e.receipts||{};
        var rec='';
        if(r.blowoff&&r.turn&&r.ratio){
          rec=t('blowoff ','冲顶回落 ')+'−'+(r.blowoff.drawdown_pct*100).toFixed(0)+'%'
            +' · '+t('off low ','低点回升 ')+pc(r.turn.off_low_pct)
            +' · '+t('ratio ','比值 ')+pc(r.ratio.ratio_chg_10s)+'/10s';
          // D-9: health state replaces the old (as of last confirmation) italic
          var h=e.health||null;
          if(h&&(h.weakening||h.lapse_count>=2||h.neg_run>=2)){
            var stc=h.sessions_to_close!=null?h.sessions_to_close:(h.sessions_to_close_bound||null);
            rec+=' <span style="color:var(--ink-warn, var(--warn));font-weight:600;">'
              +t('Weakening — may close'+(stc!=null?' in '+stc+' sessions':''),
                 '转弱——'+(stc!=null?'或于'+stc+'个交易日内关闭':'或将关闭'))+'</span>';
          } else if(h&&h.lapse_count>0&&!e.confirmed_tonight){
            rec+=' <span style="color:var(--muted);font-style:italic;">'
              +t('Cooling — last confirmed '+esc(e.asof||''),'降温——最近确认 '+esc(e.asof||''))+'</span>';
          }
          // RC-R10 honest late-ruler: the measured census distribution instead of a
          // binary "late" instinct. Descriptive only, never a gate.
          var ru=(ev&&ev.ruler&&ev.ruler.modern&&ev.ruler.modern.run_pct)?ev.ruler.modern:null;
          if(ru&&ru.n>=5){
            rec+='<br>'+t('vs modern-era handoffs: median run ','对照现代样本：中位行情 ')
              +'+'+ru.run_pct.median+'% ('+t('p75 ','75分位 ')+'+'+ru.run_pct.p75+'%), '
              +t('peaking ~','约 ')+ru.sessions_to_peak.median
              +t(' sessions in (n='+ru.n+', descriptive only)',' 个交易日见顶（n='+ru.n+'，仅描述性）');
          }
        }
        html+='<div class="rc-card rc-'+esc(sev)+'">'
          +'<div class="rc-hd"><span class="rc-sev '+esc(sev)+'">'+esc(sev)+'</span>'
          +'<span class="rc-title">'+title+'</span>'
          +'<span class="rc-day">'+t('day ','第')+esc(e.day_n)+t('',' 天')+' · '+esc(e.started)+'</span></div>'
          +'<div class="rc-copy">'+esc(isZh()?e.copy_zh:e.copy_en)+'</div>'
          +(rec?'<div class="rc-receipts">'+rec+'</div>':'')
          +'</div>';
      });
      html+='</div>';
      if(active.length>4){
        html+='<button class="lst-more" type="button" aria-expanded="false"><span class="lm-show">'
          +t('Show more','显示更多')+' ▾</span><span class="lm-hide">'+t('Show less','收起')+' ▴</span></button>';
      }
      html+='</div>';
    }
    var rows=(frag&&frag.sectors)||[];
    var flagged=rows.filter(function(r){return r.fragmented;});
    if(flagged.length){
      html+='<div class="rc-frag"><div class="rc-frag-hd">'
        +t('Fragmented sectors — aggregate reads not representative',
           '内部分化板块——聚合读数或失真')+'</div><div class="rc-frag-chips">';
      flagged.forEach(function(r){
        html+='<span class="rc-frag-chip"><b>'+esc(isZh()?r.name_zh:r.name_en)+' ('+esc(r.etf)+')</b> — '
          +esc(isZh()?r.copy_zh:r.copy_en)+'</span>';
      });
      // D-8: stance for fragmentation section
      html+='</div><div style="font-size:10.5px;color:var(--muted);margin-top:6px;">'
        +t('Judge the pieces, not the sector average.','看内部分支，别看板块平均。')
        +'</div></div>';
    }
    // Dead-end #9: cross-sector callout when an into_strength event is active
    if(ev){
      var xsActive=(ev.active||[]).filter(function(e){
        return (e.event_type==='into_strength'||e.event_type==='cross_handoff')&&(e.to_sector||e.to_leg);
      });
      if(xsActive.length){
        xsActive.forEach(function(e){
          var toSec=isZh()
            ?(e.to_sector_zh||e.sector_name_zh||(e.to_leg&&(e.to_leg.name_zh||e.to_leg.name_en))||'')
            :(e.to_sector_en||e.sector_name_en||(e.to_leg&&(e.to_leg.name_en||e.to_leg.key))||'');
          if(toSec){
            html+='<div style="font-size:11px;color:var(--ink-link, var(--link));margin-top:8px;">'
              +t('Relative leadership is shifting toward '+esc(toSec)+' — see the recorded comparison above.',
                 '相对领导力正向'+esc(toSec)+'转移——见上方已记录的比较。')
              +'</div>';
          }
        });
      }
    }
    html+='<div class="rc-caveat">'
      +t('A heads-up, not a buy signal — these events don\'t rank, gate, or size anything, and most are still being measured. as of ',
         '仅为提示，非买入信号——这些事件不排名、不设门控、不调仓位，且多数仍在观察中。截至 ')
      +esc((ev&&ev.as_of)||'—')+'</div>';
    el.innerHTML=html;
  }

  function load(){
    if(!mount()) return;
    Promise.all([
      fetch('marketdata/rotation_events.json',{cache:'no-cache'}).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;}),
      fetch('marketdata/sector_fragmentation.json',{cache:'no-cache'}).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;})
    ]).then(function(res){
      var earlyEl=document.getElementById('rc-early-context');
      if(earlyEl) earlyEl.innerHTML=earlyContextHtml(res[0],isZh()?'zh':'en',Date.now());
      if(!res[0]&&!res[1]){
        var el=document.getElementById('rc-events-content');
        if(el) el.innerHTML='<p class="rc-quiet"><span class="l-en">Rotation-event data unavailable.</span><span class="l-zh">轮动事件数据暂不可用。</span></p>';
        return;
      }
      renderFlowLanes(res[0]);
      renderClosures(res[0]);
      render(res[0],res[1]);
    }).catch(function(){/* fail-soft: leave the loading/quiet note in place */});
  }

  function boot(){
    injectStyle();
    load();
    var _rcObs=new MutationObserver(load);
    _rcObs.observe(document.documentElement,{attributes:true,attributeFilter:['data-lang','data-theme']});
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot);
  else boot();
})();
