/* sector_dossier.js — the native Sector Dossier on sectors/<ETF>.html (macro issue 7646, Cycles wave L5).
 * Pure string renderers over SC_FACE / SC_STATES (a node vm runs them in tests) plus a DOM
 * binder that only runs in a browser. DECK is generated from
 * design_refs/sector-paper-20261021/copy_deck.json (tests assert equality) — do not hand-edit it.
 * PAIRS are bilingual pairs reused verbatim from existing templates, each with its source line;
 * the L5 return records them as DECK-GAP rows. No clock is read here: the cycle face is dated by
 * the payload's own meta.today / meta.asOf, never Date.now(). */
(function (root) {
  'use strict';
  var DECK = {"dossier.record_h2":["Track record","跟踪记录"],"dossier.evidence_date_label":["Evidence date","证据日期"],"dossier.history_label":["History","历史"],"dossier.recon_label":["Reconstructed from prices","按价格重建"],"dossier.recon_body":["Reconstructed from prices: calculated later, not what Mastermind showed at the time.","按价格重建：事后计算，并非 Mastermind 当时显示的内容。"],"dossier.open_central_link":["Open in Sector Central","在板块中枢查看"],"dossier.invalid_subject_state":["Selected sector unavailable","无法识别所选板块"],"cycles.fragmentation_chip":["Fragmentation data","分化数据"],"components.asof_label":["As of","截至"],"components.rel_not_supplied":["Sector relationship not supplied","未提供板块间关系"],"components.no_evidence_attached":["No Sector evidence attached","未附带板块证据"],"components.provenance_label":["How this was measured","测量方式"],"states.error_title":["History unavailable right now","历史暂不可用"],"states.error_body":["The current read above is unaffected.","上方的当前读数不受影响。"]};
  var PAIRS = {"tab.overview":["Overview","概览","templates/crypto.html.j2:303"],"tab.cycle":["Cycle","周期","templates/sector.html.j2:251"],"tab.signals":["Signals","信号","templates/aibrief.html.j2:186"],"tab.drivers":["Drivers","驱动因素","templates/vector.html.j2:526"],"tab.companies":["Companies","公司","templates/government_revenue.html.j2:110"],"tab.evidence":["Evidence","证据","templates/subsector_detail.html.j2:171"],"members":["Members","成分","templates/baskets_hk.html.j2:406"],"ticker":["Ticker","代码","templates/_china_special_situations_rows.html.j2:221"],"weight":["Weight","权重","templates/_macro_suite_shell.html.j2:814"],"not_covered":["Not covered","未覆盖","templates/am_edition.html.j2:238"],"ev.freshness":["Freshness","新鲜度","templates/subsector_detail.html.j2:165"],"ev.coverage":["Coverage","覆盖","templates/subsector_detail.html.j2:166"],"ev.method":["Method","方法","templates/subsector_detail.html.j2:166"],"trend.200d":["200d trend","200日趋势","templates/subsector_detail.html.j2:178"],"trend.above":["Above ✓","上方 ✓","templates/subsector_detail.html.j2:178"],"trend.below":["Below","下方","templates/subsector_detail.html.j2:178"],"frag.not_representative":["aggregate not representative","聚合读数或失真","templates/sector_cycles.js:279"]};
  var TABS = ['overview', 'cycle', 'signals', 'drivers', 'companies', 'evidence', 'record'];
  var SPDR_IDS = ['xlb', 'xlc', 'xle', 'xlf', 'xli', 'xlk', 'xlp', 'xlre', 'xlu', 'xlv', 'xly'];
  var DATA_URL = '../sectordata/sector_cycles.json';
  var SC_DOSSIER = { version: 'sc-dossier.v1', TABS: TABS, DATA_URL: DATA_URL };

  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;'); }
  function bi(en, zh, cls) { var c = cls ? ' ' + cls : ''; return '<span class="l-en' + c + '">' + esc(en) + '</span><span class="l-zh' + c + '">' + esc(zh) + '</span>'; }
  function pairOf(key) { var p = DECK[key] || PAIRS[key]; if (!p) throw new Error('sc-dossier: no copy for ' + key); return p; }
  function D(key, cls) { var p = pairOf(key); return bi(p[0], p[1], cls); }
  function face() { return root.SC_FACE || null; }
  function states() { return root.SC_STATES || null; }
  function sid(x) { return String(x == null ? '' : x).toUpperCase(); }

  /* Same pivot filter as sector_cycles.js _turnsOf: confirmed peaks/troughs only. */
  function turnsOf(rec) {
    return ((rec && (rec.turns || rec.turns_tail)) || []).filter(function (t) {
      var k = t && String(t.k || '').toLowerCase();
      return !!t && t.provisional !== true && t.x != null && (k === 'peak' || k === 'trough');
    });
  }
  function findRecord(payload, fund) {
    var want = sid(fund), list = payload && Array.isArray(payload.sectors) ? payload.sectors : [], i, r;
    if (!want) return null;
    for (i = 0; i < list.length; i++) {
      r = list[i];
      if (r && (sid(r.ticker) === want || sid(r.id) === want)) return r;
    }
    return null;
  }
  function ctxOf(payload, lang) {
    var meta = (payload && payload.meta) || {};
    return { today: meta.today, meta: meta, asof: meta.asOf, fixture: false, lang: lang === 'zh' ? 'zh' : 'en' };
  }
  /* SC_FACE / SC_STATES absent (script blocked or failed): a constant composite, never a blank tab. */
  function unavailableComposite() {
    return '<div class="sc-state sc-state--unavailable" data-state="unavailable" role="status">'
      + '<p class="sc-state-t">' + D('states.error_title') + '</p><p class="sc-state-b">' + D('states.error_body') + '</p></div>';
  }
  function invalidSubject(fund) {
    return '<div class="sc-state sc-state--unavailable" data-state="invalid_subject" data-subject="' + esc(sid(fund)) + '" role="status">'
      + '<p class="sc-state-t">' + D('dossier.invalid_subject_state') + '</p></div>';
  }
  function centralHref(fund) { return '../sector_central.html#cycles/s=' + encodeURIComponent(sid(fund)); }

  /* C21: member breadth comes from rotation_context.fragmentation, read exactly as sector_cycles.js
     _rotFromContext/side() reads it. Non-aligned, malformed or missing rows are typed states; a
     fragmentation row that is not fragmented shows its legs only — never a "no fragmentation" claim. */
  function breadth(payload, fund) {
    var St = states(), rc = payload && payload.rotation_context, fr, list, row = null, i, key = String(fund || '').toLowerCase(), legs, out;
    if (!St) return unavailableComposite();
    if (!rc || typeof rc !== 'object' || rc.status === 'unavailable' || (!rc.events && !rc.fragmentation)) {
      return St.stateHTML('unavailable', { context: 'fragmentation', align: rc && rc.status ? rc : null });
    }
    fr = rc.fragmentation || { status: 'missing_input', reason: 'missing_session' };
    if (fr.status !== 'aligned') return St.stateHTML(St.fromAlignment(fr), { context: 'fragmentation', align: fr });
    list = fr.sectors;
    if (!Array.isArray(list)) return St.stateHTML('malformed', { context: 'fragmentation', align: fr });
    for (i = 0; i < list.length; i++) if (list[i] && String(list[i].key || '').toLowerCase() === key) { row = list[i]; break; }
    /* an aligned payload without this sector's row: the sector has no sub-industry leg map,
       so breadth is not covered (not an outage, and never drawn as zero dispersion). */
    if (!row) return '<p class="scd-breadth-nc" data-state="not_covered">' + D('not_covered') + '</p>';
    /* a row whose member legs are gone has lost its member coverage: unavailable, never "no fragmentation". */
    legs = Array.isArray(row.legs) ? row.legs.filter(function (l) { return l && l.key; }) : [];
    if (!legs.length) return St.stateHTML('unavailable', { context: 'fragmentation', align: fr });
    out = '<div class="scd-breadth" data-fragmented="' + (row.fragmented ? 'true' : 'false') + '">';
    if (row.fragmented) {
      out += '<p class="scd-breadth-chip"><span class="sc-chip sc-chip--warn">' + D('frag.not_representative') + '</span></p>';
      if (row.copy_en || row.copy_zh) out += '<p class="scd-breadth-copy">' + bi(row.copy_en || '', row.copy_zh || '') + '</p>';
    }
    out += '<ul class="scd-legs">';
    for (i = 0; i < legs.length; i++) {
      var lg = legs[i];
      out += '<li class="scd-leg" data-leg="' + esc(lg.key) + '"><span class="l-en">' + esc(lg.name_en || lg.key) + '</span><span class="l-zh">' + esc(lg.name_zh || '') + '</span>'
        + (typeof lg.ret === 'number' && isFinite(lg.ret) ? ' <span class="scd-num">' + esc((lg.ret >= 0 ? '+' : '') + (lg.ret * 100).toFixed(1) + '%') + '</span>' : '') + '</li>';
    }
    out += '</ul>';
    return out + '<p class="scd-meta">' + D('components.asof_label') + ' <span class="scd-num">' + esc(row.asof || fr.artifact_session || '') + '</span></p></div>';
  }
  /* C21: the ETF's own trend gate, kept apart from member breadth. */
  function etfTrend(rec) {
    var now = (rec && rec.now) || {};
    if (now.above200d === true || now.above200d === false) {
      return '<p class="scd-trend" data-above200d="' + (now.above200d ? 'true' : 'false') + '">' + D('trend.200d') + ' · ' + D(now.above200d ? 'trend.above' : 'trend.below') + '</p>';
    }
    return '<p class="scd-trend" data-above200d="unknown">' + D('trend.200d') + ' · <span class="scf-na">' + D('states.error_title') + '</span></p>';
  }

  function renderCycle(payload, fund, lang) {
    var F = face(), St = states(), rec, ctx, x;
    if (!F || !St) return unavailableComposite();
    rec = findRecord(payload, fund);
    if (!rec) return invalidSubject(fund);
    ctx = ctxOf(payload, lang);
    x = Object.assign({}, rec, { turns_tail: turnsOf(rec) });
    return '<div class="scd-cycle" data-sector="' + esc(rec.id || sid(fund)) + '">'
      + F.card(x, ctx) + F.timing(x, ctx) + F.rsTrail(x, ctx) + F.turnInspector(x, ctx) + F.trendRisk(x, ctx, null)
      + '<section class="scf scf-sec scd-sub scd-breadth-sec" aria-label="' + esc(pairOf('cycles.fragmentation_chip')[ctx.lang === 'zh' ? 1 : 0]) + '"><div class="scf-sec-ttl"><h3>' + D('cycles.fragmentation_chip') + '</h3></div>'
      + etfTrend(rec) + breadth(payload, fund) + '</section>'
      + '<p class="scd-open"><a href="' + esc(centralHref(fund)) + '">' + D('dossier.open_central_link') + '</a></p></div>';
  }
  /* Producerless tabs: a typed state plus a machine-readable residual (no invented copy). */
  function renderSignals() {
    return '<div class="sc-state sc-state--unavailable" data-state="unavailable" data-residual="no-etf-signal-producer" role="status">'
      + '<p class="sc-state-t">' + D('components.no_evidence_attached') + '</p></div>';
  }
  function renderDrivers() {
    var St = states();
    if (!St) return unavailableComposite();
    return St.stateHTML('unavailable', { context: 'relationship' }).replace('role="status"', 'role="status" data-residual="no-sector-driver-producer"');
  }
  function renderEvidence(payload, lang) {
    var F = face(), St = states(), meta = (payload && payload.meta) || {}, cov;
    if (!F || !St) return unavailableComposite();
    cov = St.coverage(payload && Array.isArray(payload.sectors) ? payload.sectors : null, SPDR_IDS);
    return '<dl class="scd-facts">'
      + '<div data-fact="freshness"><dt>' + D('ev.freshness') + '</dt><dd>' + D('dossier.evidence_date_label') + ' '
      + (meta.asOf ? '<span class="scd-num">' + esc(meta.asOf) + '</span>' : St.stateHTML('unavailable', { compact: true })) + '</dd></div>'
      + '<div data-fact="coverage"><dt>' + D('ev.coverage') + '</dt><dd data-coverage="' + esc(cov.state) + '">'
      + (cov.measured == null ? St.stateHTML('unavailable', { compact: true })
        : '<span class="scd-num">' + esc(cov.measured + '/' + cov.expected) + '</span>' + (cov.state === 'fresh' ? '' : ' ' + St.stateHTML('partial', { compact: true, x: cov.measured, y: cov.expected })))
      + '</dd></div>'
      + '<div data-fact="method"><dt>' + D('ev.method') + '</dt><dd>' + D('dossier.history_label') + ' · ' + D('dossier.recon_label')
      + '<details class="scf scf-prov cyc-prov scd-note"><summary>' + D('components.provenance_label') + '</summary>'
      + '<dl class="cyc-prov-body"><div><dt>' + D('dossier.recon_label') + '</dt><dd>' + D('dossier.recon_body') + '</dd></div></dl></details>'
      + '</dd></div></dl>';
  }
  /* Record tab: the SSR trust panel is the sector's own record; the cycle engine's method notes
     (hazard parity, sizing inert, lead/lag stop) follow it. The self-grader scorecard lives on
     Sector Central only, so the tab links there instead of drawing an empty grader. */
  function renderRecord(payload, fund, lang) {
    var F = face();
    if (!F) return unavailableComposite();
    return F.methods((payload && payload.meta) || {}, ctxOf(payload, lang))
      + '<p class="scd-open"><a href="' + esc(centralHref(fund)) + '">' + D('dossier.open_central_link') + '</a></p>';
  }
  /* a failed/typed fetch: every data tab says so with the same typed state. */
  function renderFetchState(res) {
    var St = states();
    if (!St) return unavailableComposite();
    return St.stateHTML(res && res.state || 'unavailable', { align: res });
  }

  SC_DOSSIER.DECK = DECK;
  SC_DOSSIER.PAIRS = PAIRS;
  SC_DOSSIER.turnsOf = turnsOf;
  SC_DOSSIER.findRecord = findRecord;
  SC_DOSSIER.ctxOf = ctxOf;
  SC_DOSSIER.breadth = breadth;
  SC_DOSSIER.renderCycle = renderCycle;
  SC_DOSSIER.renderSignals = renderSignals;
  SC_DOSSIER.renderDrivers = renderDrivers;
  SC_DOSSIER.renderEvidence = renderEvidence;
  SC_DOSSIER.renderRecord = renderRecord;
  SC_DOSSIER.renderFetchState = renderFetchState;
  SC_DOSSIER.unavailableComposite = unavailableComposite;
  SC_DOSSIER.centralHref = centralHref;
  SC_DOSSIER.tabFor = function (hash, panelOf) {
    var h = String(hash || '').replace(/^#/, '');
    if (!h) return { tab: TABS[0], target: null };
    if (TABS.indexOf(h) >= 0) return { tab: h, target: null };
    var p = panelOf ? panelOf(h) : null;
    return p ? { tab: p, target: h } : { tab: TABS[0], target: null };
  };

  /* ---------- DOM binder (browser only) ---------- */
  function lang() { return root.document && root.document.documentElement.getAttribute('data-lang') === 'zh' ? 'zh' : 'en'; }
  function bind(doc) {
    var shell = doc.getElementById('scd'), fund, tabs, panels, data = null, fetched = false, current = null;
    if (!shell) return;
    fund = shell.getAttribute('data-fund') || '';
    tabs = Array.prototype.slice.call(shell.querySelectorAll('[role="tab"]'));
    panels = {};
    TABS.forEach(function (t) { panels[t] = doc.getElementById('scd-p-' + t); });
    function panelOf(id) {
      var el = doc.getElementById(id), k;
      for (k in panels) if (panels[k] && el && panels[k].contains(el)) return k;
      return null;
    }
    function mount(id, html) { var m = doc.getElementById(id); if (m) m.innerHTML = html; }
    function paint() {
      var L = lang();
      if (!fetched) return;
      if (data && data.state === 'fresh') {
        mount('scd-cycle', renderCycle(data.data, fund, L));
        mount('scd-evidence', renderEvidence(data.data, L));
        mount('scd-record-face', renderRecord(data.data, fund, L));
      } else {
        mount('scd-cycle', renderFetchState(data));
        mount('scd-evidence', renderFetchState(data));
        mount('scd-record-face', renderFetchState(data));
      }
    }
    function load() {
      var St = states(), p;
      mount('scd-signals', renderSignals());
      mount('scd-drivers', renderDrivers());
      if (!St || !face()) { fetched = true; data = null; mount('scd-cycle', unavailableComposite()); mount('scd-evidence', unavailableComposite()); mount('scd-record-face', unavailableComposite()); return; }
      ['scd-cycle', 'scd-evidence', 'scd-record-face'].forEach(function (id) { mount(id, St.stateHTML('loading')); });
      p = St.fetchTyped(DATA_URL, { list: 'sectors' });
      if (!p) { fetched = true; data = { state: 'unavailable' }; paint(); return; }
      p.then(function (res) { fetched = true; data = res; paint(); });
    }
    function select(tab, focus, target) {
      if (TABS.indexOf(tab) < 0) tab = TABS[0];
      tabs.forEach(function (b) {
        var on = b.getAttribute('data-tab') === tab;
        b.setAttribute('aria-selected', on ? 'true' : 'false');
        b.setAttribute('tabindex', on ? '0' : '-1');
        if (on && focus) b.focus();
      });
      TABS.forEach(function (t) { if (panels[t]) panels[t].hidden = t !== tab; });
      current = tab;
      if (target) { var el = doc.getElementById(target); if (el && el.scrollIntoView) el.scrollIntoView(); }
    }
    function route() { var r = SC_DOSSIER.tabFor(root.location ? root.location.hash : '', panelOf); select(r.tab, false, r.target); }
    tabs.forEach(function (b, i) {
      b.addEventListener('click', function (e) {
        e.preventDefault();
        var t = b.getAttribute('data-tab');
        if (b.getAttribute('aria-selected') !== 'true' && root.history && root.history.pushState) root.history.pushState(null, '', '#' + t);
        select(t, false, null);
      });
      b.addEventListener('keydown', function (e) {
        var k = e.key, j = null;
        if (k === 'ArrowRight') j = (i + 1) % tabs.length;
        else if (k === 'ArrowLeft') j = (i - 1 + tabs.length) % tabs.length;
        else if (k === 'Home') j = 0;
        else if (k === 'End') j = tabs.length - 1;
        else if (k === 'Enter' || k === ' ') { e.preventDefault(); b.click(); return; }
        if (j == null) return;
        e.preventDefault();
        tabs[j].focus();
        tabs.forEach(function (o, n) { o.setAttribute('tabindex', n === j ? '0' : '-1'); });
      });
    });
    root.addEventListener('hashchange', route);
    root.addEventListener('popstate', route);
    var mo = root.MutationObserver ? new root.MutationObserver(function () { paint(); }) : null;
    if (mo) mo.observe(doc.documentElement, { attributes: true, attributeFilter: ['data-lang'] });
    shell.setAttribute('data-bound', 'true');
    route();
    load();
  }
  SC_DOSSIER.bind = bind;

  root.SC_DOSSIER = SC_DOSSIER;
  if (root.document && root.document.getElementById) {
    if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', function () { bind(root.document); });
    else bind(root.document);
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = SC_DOSSIER;
})(typeof window !== 'undefined' ? window : this);
