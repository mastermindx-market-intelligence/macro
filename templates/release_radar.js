/* Release Radar runtime — lazy-loaded by macro.html on Events dialog demand.
 * Extracted from dashboard.html.j2 to keep ~94 KB of parse/execute work off the
 * mobile dashboard critical path. Keep this file Jinja-free and same-origin.
 */
(function(){
    'use strict';
    var RR_EL = document.getElementById('rr-content');
    var RR_OVERLAY = document.getElementById('rr-modal-overlay');
    var RR_MODAL_INNER = document.getElementById('rr-modal-inner');
    var RR_MODAL_CLOSE = document.getElementById('rr-modal-close');
    var RR_TAB_STRIP = document.getElementById('rr-tab-strip');
    var RR_TITLE_BLOCK = document.getElementById('rr-modal-title-block');
    /* Inline Release Radar panel inside dlg-events (replaces the retired
       rr-date-overlay). Resolved LAZILY — this script block sits ABOVE the
       dlg-events markup in the document, so the elements don't exist when the IIFE
       first runs; they do by the time the async fetch resolves. */
    function _rrInlineBody(){ return document.getElementById('rr-inline-body'); }
    function _rrInlineDateEl(){ return document.getElementById('rr-inline-date'); }
    var _rrInlineDate = null;           /* currently-selected date string */
    var _rrInlineSignature = null;      /* selected date + current forecast payload */
    var _rrInlineSwapToken = 0;         /* invalidates delayed paints after rapid clicks */
    var _rrInlineSwapTimer = null;
    /* INT-03: focus management — track invoker for restore on close */
    var _rrModalInvoker = null;

    /* ---- base helpers ---- */
    function esc(s){ return s == null ? '' : String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    function fmtNum(v, digits){ return (v == null || isNaN(v)) ? '—' : Number(v).toFixed(digits != null ? digits : 2); }
    function fmtPct(v){ return (v == null || isNaN(v)) ? '—' : (Number(v)*100).toFixed(0) + '%'; }
    /* claims / nfp level formatting: values in thousands */
    function fmtK(v){ return (v == null || isNaN(v)) ? '—' : Number(v).toFixed(0) + 'k'; }

    /* release name bilingual map — covers all active release types */
    var RN_EN = {
      cpi:'CPI', nfp:'NFP Payrolls', claims:'Initial Claims',
      pce:'PCE', ppi:'PPI', retail:'Retail Sales'
    };
    var RN_ZH = {
      cpi:'消费者物价指数', nfp:'非农就业', claims:'初请失业金',
      pce:'PCE通胀', ppi:'生产者物价', retail:'零售销售'
    };
    /* sub-type suffix for headline vs core vs final-demand */
    var RT_SUFFIX_EN = {
      cpi_headline:'(Headline)', cpi_core:'(Core)', pce_headline:'(Headline)',
      pce_core:'(Core)', ppi_finaldemand:'(Final Demand)', nfp:'', claims:'', retail_sales:''
    };
    var RT_SUFFIX_ZH = {
      cpi_headline:'(整体)', cpi_core:'(核心)', pce_headline:'(整体)',
      pce_core:'(核心)', ppi_finaldemand:'(最终需求)', nfp:'', claims:'', retail_sales:''
    };
    function relName(rel, release_type){
      var k = (rel||'').toLowerCase();
      var rt = (release_type||'').toLowerCase();
      var sfxEN = RT_SUFFIX_EN[rt] || '';
      var sfxZH = RT_SUFFIX_ZH[rt] || '';
      return '<span class="l-en">'+esc(RN_EN[k]||rel)+(sfxEN?' '+sfxEN:'')+'</span>'
            +'<span class="l-zh">'+esc(RN_ZH[k]||rel)+(sfxZH?' '+sfxZH:'')+'</span>';
    }

    /* ---- MRI-R24 chip helpers ---- */

    /* expectation chip (expectation_read.tag) */
    function expectationChip(er){
      if (!er || !er.tag) return '';
      var tag = (er.tag||'').toLowerCase();
      var cls, labelEN, labelZH;
      if (tag === 'above_expectations'){
        cls='rr-exp-above'; labelEN='above expectations'; labelZH='高于预期';
      } else if (tag === 'below_expectations'){
        cls='rr-exp-below'; labelEN='below expectations'; labelZH='低于预期';
      } else {
        cls='rr-exp-aligned'; labelEN='aligned'; labelZH='符合预期';
      }
      return '<span class="rr-exp '+esc(cls)+'">'
        +'<span class="l-en">'+esc(labelEN)+'</span>'
        +'<span class="l-zh">'+esc(labelZH)+'</span>'
        +'</span>';
    }

    /* trend skew chip (surprise_skew.tag) */
    function skewChip(sk){
      if (!sk || sk.tag == null) return '';
      var tag = (sk.tag||'').toLowerCase();
      if (!tag) return '';
      var cls = tag==='hotter'?'rr-skew-hot':tag==='cooler'?'rr-skew-cool':'rr-skew-inline';
      var tagEN = tag==='hotter'?'hotter':tag==='cooler'?'cooler':'inline';
      var tagZH = tag==='hotter'?'偏热':tag==='cooler'?'偏冷':'持平';
      var sig = (sk.sigma != null && !isNaN(sk.sigma)) ? ' '+fmtNum(sk.sigma,1)+'σ' : '';
      return '<span class="rr-skew '+esc(cls)+'">'
        +'<span class="l-en">'+esc(tagEN)+esc(sig)+'</span>'
        +'<span class="l-zh">'+esc(tagZH)+esc(sig)+'</span>'
        +'</span>';
    }

    /* source coverage chip (coverage_flags) */
    function coverageChip(cf){
      if (!cf) return '';
      var wc = cf.weight_coverage != null ? Number(cf.weight_coverage) : 0;
      var fp = cf.fresh_proxy_coverage != null ? Number(cf.fresh_proxy_coverage) : 0;
      var nv = cf.non_vintaged_share != null ? Number(cf.non_vintaged_share) : 0;
      var mm = cf.model_maturity != null ? cf.model_maturity : 0;
      /* derive tier: fresh ≥0.85wc + ≥0.6fp; partial: wc≥0.5; stale: wc≥0.1; else prior-heavy */
      var tier, cls;
      if (wc >= 0.85 && fp >= 0.6){ tier='fresh'; cls='rr-cov-fresh'; }
      else if (wc >= 0.5){ tier='partial'; cls='rr-cov-partial'; }
      else if (wc >= 0.1){ tier='stale'; cls='rr-cov-stale'; }
      else { tier='prior-heavy'; cls='rr-cov-prior'; }
      var tierEN = tier==='fresh'?'fresh':tier==='partial'?'partial':tier==='stale'?'stale':'prior-heavy';
      var tierZH = tier==='fresh'?'充分':tier==='partial'?'部分':tier==='stale'?'陈旧':'以先验为主';
      var nStr = mm > 0 ? ' (n='+mm+' scored)' : '';
      return '<span class="rr-cov '+esc(cls)+'">'
        +'<span class="l-en">'+esc(tierEN)+esc(nStr)+'</span>'
        +'<span class="l-zh">'+esc(tierZH)+(mm>0?' (n='+mm+' scored)':'')+'</span>'
        +'</span>';
    }

    /* interval cone bar (p10–p90, tick at point) */
    function intervalBar(proj){
      if (!proj) return '';
      var p10 = proj.p10, p90 = proj.p90, pt = proj.point;
      if (p10 == null || p90 == null) return '';
      var span = p90 - p10;
      if (span <= 0) return '';
      var fillL = 0, fillW = 100, tickX = 50;
      var p25 = proj.p25, p75 = proj.p75;
      if (p25 != null && p75 != null) {
        fillL = Math.max(0, Math.min(100, (p25-p10)/span*100));
        fillW = Math.max(0, Math.min(100, (p75-p25)/span*100));
      }
      /* tick at point if present, else p50, else center */
      var tickSrc = pt != null ? pt : (proj.p50 != null ? proj.p50 : null);
      if (tickSrc != null) tickX = Math.max(0, Math.min(100, (tickSrc-p10)/span*100));
      return '<div class="rr-interval-bar">'
        +'<div class="rr-interval-fill" style="left:'+fillL.toFixed(1)+'%;width:'+fillW.toFixed(1)+'%"></div>'
        +(tickSrc != null ? '<div class="rr-interval-tick" style="left:'+tickX.toFixed(1)+'%"></div>' : '')
        +'</div>'
        +'<div class="rr-interval-labels">'
        +'<span>p10 '+fmtNum(p10,2)+'</span>'
        +'<span>p90 '+fmtNum(p90,2)+'</span>'
        +'</div>';
    }

    /* benchmark strip */
    function benchStrip(bs, rel){
      if (!bs) return '';
      var isClaims = (rel||'').toLowerCase() === 'claims';
      var isNfp = (rel||'').toLowerCase() === 'nfp';
      var useK = isClaims || isNfp;
      var items = [];
      if (bs.naive_prior != null)
        items.push(['<span class="l-en">Naive prior</span><span class="l-zh">朴素先验</span>', useK ? fmtK(bs.naive_prior) : fmtNum(bs.naive_prior,2)]);
      if (isClaims && bs.trailing_4w != null)
        items.push(['<span class="l-en">Trailing 4w</span><span class="l-zh">近4周均值</span>', fmtK(bs.trailing_4w)]);
      if (!isClaims && bs.trailing_3m != null)
        items.push(['<span class="l-en">Trailing 3m</span><span class="l-zh">近3月均值</span>', useK ? fmtK(bs.trailing_3m) : fmtNum(bs.trailing_3m,2)]);
      if (bs.ar_model != null)
        items.push(['AR model', useK ? fmtK(bs.ar_model) : fmtNum(bs.ar_model,2)]);
      /* Cleveland nowcast: CPI family only */
      if (!isClaims && !isNfp && (rel||'').toLowerCase()==='cpi' && bs.cleveland_nowcast != null)
        items.push(['Cleveland nowcast', fmtNum(bs.cleveland_nowcast,2)]);
      if (!items.length) return '';
      var rows = items.map(function(r){
        return '<div class="rr-bench-row"><span class="rr-bench-name">'+r[0]+'</span><span class="rr-bench-val">'+esc(r[1])+'</span></div>';
      }).join('');
      return '<div class="rr-bench">'
        +'<div class="rr-bench-label"><span class="l-en">Benchmarks</span><span class="l-zh">基准对比（非共识）</span></div>'
        +rows
        +'</div>';
    }

    /* policy backdrop strip */
    function policyStrip(pb){
      if (!pb) return '';
      var items = [];
      if (pb.fed_stance) {
        var stEN = {hawkish:'Hawkish',neutral:'Neutral',dovish:'Dovish'};
        var stZH = {hawkish:'鹰派',neutral:'中性',dovish:'鸽派'};
        var sk = (pb.fed_stance||'').toLowerCase();
        items.push('<span class="rr-policy-item">'
          +'<span class="l-en">Fed: <b>'+esc(stEN[sk]||pb.fed_stance)+'</b></span>'
          +'<span class="l-zh">美联储：<b>'+esc(stZH[sk]||pb.fed_stance)+'</b></span>'
          +'</span>');
      }
      if (pb.gap_bp != null)
        items.push('<span class="rr-policy-item">'
          +'<span class="l-en">Market vs dots: <b>'+fmtNum(pb.gap_bp,0)+' bp</b></span>'
          +'<span class="l-zh">市场vs点阵：<b>'+fmtNum(pb.gap_bp,0)+' bp</b></span>'
          +'</span>');
      if (pb.implied_cuts_12m != null)
        items.push('<span class="rr-policy-item">'
          +'<span class="l-en">Implied cuts (12m): <b>'+fmtNum(pb.implied_cuts_12m,1)+'</b></span>'
          +'<span class="l-zh">隐含降息（12月）：<b>'+fmtNum(pb.implied_cuts_12m,1)+'</b></span>'
          +'</span>');
      if (pb.next_fomc)
        items.push('<span class="rr-policy-item">'
          +'<span class="l-en">Next FOMC: <b>'+esc(pb.next_fomc)+'</b></span>'
          +'<span class="l-zh">下次FOMC：<b>'+esc(pb.next_fomc)+'</b></span>'
          +'</span>');
      if (pb.guidance_direction)
        items.push('<span class="rr-policy-item">'
          +'<span class="l-en">Guidance: <b>'+esc(pb.guidance_direction)+'</b></span>'
          +'<span class="l-zh">指引方向：<b>'+esc(pb.guidance_direction)+'</b></span>'
          +'</span>');
      if (!items.length) return '';
      return '<div class="rr-policy">'+items.join('')+'</div>';
    }

    /* scoreboard sub-block */
    function scoreboardBlock(lastScored){
      if (!lastScored || !Array.isArray(lastScored) || !lastScored.length) {
        return '<div class="rr-scoreboard">'
          +'<div class="rr-scoreboard-title"><span class="l-en">Track record</span><span class="l-zh">历史评分</span></div>'
          +'<div class="rr-empty">'
          +'<span class="l-en">Forward accrual began 2026-07 — no scored prints yet.</span>'
          +'<span class="l-zh">自2026年7月起正向评分积累中，暂无已评分数据。</span>'
          +'</div>'
          +'</div>';
      }
      var byRel = {};
      lastScored.forEach(function(row){
        var k = (row.release||'other').toLowerCase();
        if (!byRel[k]) byRel[k] = {n:0, mae_ours:0, mae_naive:0, skew_hits:0};
        byRel[k].n += 1;
        if (row.our_mae != null) byRel[k].mae_ours += Number(row.our_mae);
        if (row.naive_mae != null) byRel[k].mae_naive += Number(row.naive_mae);
        if (row.skew_hit) byRel[k].skew_hits += 1;
      });
      var thead = '<tr>'
        +'<th><span class="l-en">Release</span><span class="l-zh">数据</span></th>'
        +'<th><span class="l-en">n</span><span class="l-zh">n</span></th>'
        +'<th><span class="l-en">MAE ours</span><span class="l-zh">本方MAE</span></th>'
        +'<th><span class="l-en">MAE naive</span><span class="l-zh">朴素MAE</span></th>'
        +'<th><span class="l-en">Skew hit%</span><span class="l-zh">偏态命中%</span></th>'
        +'</tr>';
      var rows = Object.keys(byRel).map(function(k){
        var g = byRel[k];
        var maeO = g.n ? (g.mae_ours/g.n).toFixed(3) : '—';
        var maeN = g.n ? (g.mae_naive/g.n).toFixed(3) : '—';
        var skhit = g.n ? (g.skew_hits/g.n*100).toFixed(0)+'%' : '—';
        return '<tr><td>'+relName(k,'')+'</td><td>'+g.n+'</td>'
          +'<td>'+esc(maeO)+'</td><td>'+esc(maeN)+'</td><td>'+esc(skhit)+'</td></tr>';
      }).join('');
      return '<div class="rr-scoreboard">'
        +'<div class="rr-scoreboard-title"><span class="l-en">Track record</span><span class="l-zh">历史评分</span></div>'
        +'<table class="rr-track-table"><thead>'+thead+'</thead><tbody>'+rows+'</tbody></table>'
        +'</div>';
    }

    /* component breakdown bar — reads contribution_pp (cpi_bridge schema) or contrib_pp (legacy) */
    function componentsBar(components, rel){
      if (!Array.isArray(components) || !components.length) return '';
      var maxAbs = 0;
      components.forEach(function(c){
        var v = c.contribution_pp != null ? c.contribution_pp : (c.contrib_pp != null ? c.contrib_pp : null);
        if (v != null) maxAbs = Math.max(maxAbs, Math.abs(v));
      });
      if (maxAbs === 0) return '';
      var COMP_NAME_EN = {
        energy:'Energy', shelter:'Shelter', core_persistence:'Core persist.',
        pipeline:'Pipeline', private:'Private', government:'Govt.',
        'birth-death':'Birth-death', residual:'Residual',
        energy_gasoline:'Gasoline', energy_electricity:'Electricity',
        food_at_home:'Food@home', core_goods_pipeline:'Core goods',
        core_services_ex_shelter:'Core svcs ex-shlt', unmodelled_residual:'Unmod. residual'
      };
      var COMP_NAME_ZH = {
        energy:'能源', shelter:'住房', core_persistence:'核心持续',
        pipeline:'管道', private:'私人', government:'政府',
        'birth-death':'出生死亡', residual:'残差',
        energy_gasoline:'汽油', energy_electricity:'电力',
        food_at_home:'食品', core_goods_pipeline:'核心商品',
        core_services_ex_shelter:'核心服务(不含住房)', unmodelled_residual:'未建模残差'
      };
      var rows = components.map(function(c){
        if (!c) return '';
        var cv = c.contribution_pp != null ? c.contribution_pp : (c.contrib_pp != null ? c.contrib_pp : null);
        if (cv == null) return '';
        var name = c.block || c.name || '';
        var isResidual = name === 'residual' || name === 'birth-death' || name === 'unmodelled_residual';
        var pct = Math.abs(cv) / maxAbs * 50;
        var isPos = cv >= 0;
        var nameEN = COMP_NAME_EN[name] || name;
        var nameZH = COMP_NAME_ZH[name] || name;
        var barFill = isPos
          ? '<div class="rr-comp-bar-fill-pos" style="width:'+pct.toFixed(1)+'%"></div>'
          : '<div class="rr-comp-bar-fill-neg" style="width:'+pct.toFixed(1)+'%"></div>';
        var valStr = (cv > 0 ? '+' : '') + fmtNum(cv, 3) + 'pp';
        var nameSpan = '<span class="rr-comp-name'+(isResidual?' rr-comp-muted':'')+'">'
          +'<span class="l-en">'+esc(nameEN)+'</span>'
          +'<span class="l-zh">'+esc(nameZH)+'</span>'
          +(isResidual?'<span class="rr-row-status">'
            +'<span class="l-en">plug residual</span>'
            +'<span class="l-zh">残差</span>'
            +'</span>':'')
          +'</span>';
        return '<div class="rr-comp-row">'
          +nameSpan
          +'<div class="rr-comp-bar-wrap">'+barFill+'</div>'
          +'<span class="rr-comp-val'+(isResidual?' rr-comp-muted':'')+'">'+esc(valStr)+'</span>'
          +'</div>';
      }).join('');
      return '<div class="rr-comp-section">'
        +'<div class="rr-comp-label">'
        +'<span class="l-en">What is driving the number</span>'
        +'<span class="l-zh">驱动因素分解</span>'
        +'</div>'
        +'<div class="rr-comp-rows">'+rows+'</div>'
        +'</div>';
    }

    /* confidence composition bar — uses coverage_flags (fresh_proxy/non_vintaged) as proxy */
    function confidenceBar(cv2, cv2comps){
      if (cv2 == null || !cv2comps) return '';
      var wk = cv2comps.w_known != null ? cv2comps.w_known : 0;
      var wp = cv2comps.w_proxy != null ? cv2comps.w_proxy : 0;
      var wr = cv2comps.w_residual != null ? cv2comps.w_residual : 0;
      var total = wk + wp + wr;
      if (total <= 0) return '';
      var pK = (wk/total*100).toFixed(1), pP = (wp/total*100).toFixed(1), pR = (100 - parseFloat(pK) - parseFloat(pP)).toFixed(1);
      return '<div class="rr-conf-section">'
        +'<div class="rr-comp-label">'
        +'<span class="l-en">Data quality composition</span>'
        +'<span class="l-zh">数据质量构成</span>'
        +'</div>'
        +'<div class="rr-conf-bar-wrap">'
        +'<div class="rr-conf-seg-known" style="width:'+pK+'%"></div>'
        +'<div class="rr-conf-seg-proxy" style="width:'+pP+'%"></div>'
        +'<div class="rr-conf-seg-residual" style="width:'+pR+'%"></div>'
        +'</div>'
        +'<div class="rr-conf-legend">'
        +'<span><span class="rr-conf-leg-dot" style="background:color-mix(in srgb,var(--up) 70%,transparent)"></span>'
        +'<span class="l-en">Known '+pK+'%</span><span class="l-zh">已知 '+pK+'%</span></span>'
        +'<span><span class="rr-conf-leg-dot" style="background:color-mix(in srgb,var(--warn) 65%,transparent)"></span>'
        +'<span class="l-en">Proxy '+pP+'%</span><span class="l-zh">代理 '+pP+'%</span></span>'
        +'<span><span class="rr-conf-leg-dot" style="background:color-mix(in srgb,var(--muted) 40%,transparent)"></span>'
        +'<span class="l-en">Residual '+pR+'%</span><span class="l-zh">残差 '+pR+'%</span></span>'
        +'</div>'
        +'</div>';
    }

    /* market-implied benchmark row */
    function marketImpliedRow(mi){
      if (!mi || mi == null) return '';
      var src = (mi.source || '').toLowerCase();
      var valStr = '—';
      if (src === 'kalshi' && mi.implied_median != null)
        valStr = fmtNum(mi.implied_median, 2);
      else if (src === 'polymarket' && mi.implied != null)
        valStr = String(mi.implied);
      if (valStr === '—') return '';
      var srcLabel = src === 'kalshi' ? 'Kalshi' : src === 'polymarket' ? 'Polymarket' : esc(mi.source||'');
      return '<div class="rr-mkt-row">'
        +'<span class="rr-mkt-label">'
        +'<span class="l-en">Market-implied</span>'
        +'<span class="l-zh">市场隐含</span>'
        +'</span>'
        +'<span class="rr-mkt-val">'+esc(valStr)+'</span>'
        +'<span class="rr-mkt-source">'+esc(srcLabel)+'</span>'
        +'</div>';
    }

    /* surprise distribution 3-segment gauge */
    function surpriseDistGauge(sd){
      if (!sd) return '';
      var ph = sd.p_hot, pi = sd.p_inline, pc = sd.p_cold;
      if (ph == null && pi == null && pc == null) return '';
      var phPct = (ph != null ? ph : 0) * 100;
      var piPct = (pi != null ? pi : 0) * 100;
      var pcPct = (pc != null ? pc : 0) * 100;
      return '<div class="rr-sdist-wrap">'
        +'<div class="rr-sdist-bar-wrap">'
        +'<div class="rr-sdist-hot" style="width:'+phPct.toFixed(1)+'%"></div>'
        +'<div class="rr-sdist-inline" style="width:'+piPct.toFixed(1)+'%"></div>'
        +'<div class="rr-sdist-cold" style="width:'+pcPct.toFixed(1)+'%"></div>'
        +'</div>'
        +'<div class="rr-sdist-legend">'
        +'<span><span class="l-en">Hot '+phPct.toFixed(0)+'%</span><span class="l-zh">热 '+phPct.toFixed(0)+'%</span></span>'
        +'<span><span class="l-en">Inline '+piPct.toFixed(0)+'%</span><span class="l-zh">中性 '+piPct.toFixed(0)+'%</span></span>'
        +'<span><span class="l-en">Cold '+pcPct.toFixed(0)+'%</span><span class="l-zh">冷 '+pcPct.toFixed(0)+'%</span></span>'
        +'</div>'
        +'</div>';
    }

    /* reaction sensitivity footer */
    function reactionSensRow(rs){
      if (!rs) return '';
      var h10 = rs.dgs10_h1_hot_bp, c10 = rs.dgs10_h1_cold_bp;
      var hS = rs.spy_h1_hot_pct, cS = rs.spy_h1_cold_pct;
      if (h10 == null && c10 == null && hS == null && cS == null) return '';
      var n = rs.regime_cells_used;
      var note = rs.note ? esc(rs.note) : '';
      var hotParts = [];
      if (h10 != null) hotParts.push('10y '+(h10>0?'+':'')+fmtNum(h10,0)+'bp');
      if (hS != null) hotParts.push('SPY '+(hS>0?'+':'')+fmtNum(hS,2)+'%');
      var coldParts = [];
      if (c10 != null) coldParts.push('10y '+(c10>0?'+':'')+fmtNum(c10,0)+'bp');
      if (cS != null) coldParts.push('SPY '+(cS>0?'+':'')+fmtNum(cS,2)+'%');
      var hotStr = hotParts.length ? hotParts.join(', ') : '—';
      var coldStr = coldParts.length ? coldParts.join(', ') : '—';
      /* guard: only show (n=…) when field is a finite number, not boolean/null */
      var nStr = (typeof n === 'number' && isFinite(n)) ? ' (n='+n+')' : '';
      return '<div class="rr-sens-footer">'
        +'<span class="l-en">Hot print historically: <b>'+esc(hotStr)+'</b> next session'+nStr+'</span>'
        +'<span class="l-zh">历史上热数据：<b>'+esc(hotStr)+'</b>（次交易日）'+nStr+'</span>'
        +'<br>'
        +'<span class="l-en">Cold print historically: <b>'+esc(coldStr)+'</b> next session</span>'
        +'<span class="l-zh">历史上冷数据：<b>'+esc(coldStr)+'</b>（次交易日）</span>'
        +(note?'<div class="rr-sens-note">'+note+'</div>':'')
        +'</div>';
    }

    /* revision risk line (NFP) */
    function revisionRiskLine(rr){
      if (!rr) return '';
      var mk = rr.mean_k, pu = rr.pct_upward;
      if (mk == null && pu == null) return '';
      var mkStr = mk != null ? fmtNum(mk, 1)+'k' : '—';
      var puStr = pu != null ? fmtNum(pu, 0)+'%' : '—';
      return '<div class="rr-rev-risk">'
        +'<span class="l-en">First-print revision risk: avg <b>'+esc(mkStr)+'</b>, <b>'+esc(puStr)+'</b> revised up</span>'
        +'<span class="l-zh">首次发布修正风险：平均 <b>'+esc(mkStr)+'</b>，<b>'+esc(puStr)+'</b> 向上修正</span>'
        +'</div>';
    }

    /* quirk flag chips */
    function quirkChips(flags){
      if (!Array.isArray(flags) || !flags.length) return '';
      var chips = flags.map(function(f){
        var en = f.en || f.code || '';
        var zh = f.zh || f.en || f.code || '';
        var cite = f.cite || '';
        return '<span class="rr-quirk-chip"'
          +(cite?' data-cite="'+esc(cite)+'"':'')+' aria-label="'+esc(cite)+'">'
          +'<span class="rr-quirk-icon">&#9888;</span>'
          +'<span class="l-en">'+esc(en)+'</span>'
          +'<span class="l-zh">'+esc(zh)+'</span>'
          +'</span>';
      }).join('');
      return '<div class="rr-quirk-row">'+chips+'</div>';
    }

    /* MRI-R24: CPI bridge waterfall (shadows.cpi_bridge) */
    function cpiBridgeWaterfall(bridge){
      if (!bridge || !Array.isArray(bridge.components) || !bridge.components.length) return '';
      var comps = bridge.components;
      var maxAbs = 0;
      comps.forEach(function(c){ if (c && c.contribution_pp != null) maxAbs = Math.max(maxAbs, Math.abs(c.contribution_pp)); });
      if (maxAbs === 0) return '';
      var BNAME_EN = {
        energy_gasoline:'Gasoline', energy_electricity:'Electricity', shelter:'Shelter',
        food_at_home:'Food@home', core_goods_pipeline:'Core goods',
        core_services_ex_shelter:'Core svcs', unmodelled_residual:'Unmod. residual'
      };
      var BNAME_ZH = {
        energy_gasoline:'汽油', energy_electricity:'电力', shelter:'住房',
        food_at_home:'食品', core_goods_pipeline:'核心商品',
        core_services_ex_shelter:'核心服务', unmodelled_residual:'未建模残差'
      };
      var rows = comps.map(function(c){
        if (!c || c.contribution_pp == null) return '';
        var cv = c.contribution_pp;
        var block = c.block || '';
        var isPrior = c.prior_only === true;
        /* partially-composed block: shipped an estimate, but not on all its inputs */
        var isPartial = c.degraded === true;
        var pct = Math.abs(cv) / maxAbs * 50;
        var isPos = cv >= 0;
        var nameEN = BNAME_EN[block] || block;
        var nameZH = BNAME_ZH[block] || block;
        var barFill = isPos
          ? '<div class="rr-bridge-fill-pos" style="width:'+pct.toFixed(1)+'%"></div>'
          : '<div class="rr-bridge-fill-neg" style="width:'+pct.toFixed(1)+'%"></div>';
        var valStr = (cv > 0 ? '+' : '') + fmtNum(cv, 3) + 'pp';
        return '<div class="rr-bridge-row">'
          +'<span class="rr-bridge-name'+(isPrior?' rr-comp-muted':'')+'">'
          +'<span class="l-en">'+esc(nameEN)+'</span>'
          +'<span class="l-zh">'+esc(nameZH)+'</span>'
          +(isPrior?'<span class="rr-row-status">'
            +'<span class="l-en">prior</span><span class="l-zh">先验</span>'
            +'</span>':'')
          +(isPartial?'<span class="rr-row-status">'
            +'<span class="l-en">partial</span><span class="l-zh">部分输入</span>'
            +'</span>':'')
          +'</span>'
          +'<div class="rr-bridge-bar-wrap">'+barFill+'</div>'
          +'<span class="rr-bridge-val'+(isPrior?' rr-comp-muted':'')+'">'+esc(valStr)+'</span>'
          +'</div>';
      }).join('');
      var priorShare = bridge.prior_driven_share != null ? fmtPct(bridge.prior_driven_share) : '—';
      var covResidual = bridge.coverage_residual_pp != null ? fmtNum(bridge.coverage_residual_pp,3)+'pp' : '—';
      /* Partial-input receipt. Merged into the panel's single footnote (doctrine Law 4:
         one footnote per panel, merge never stack). Named blocks, counted inputs, and
         what it cost — no raw series slugs on a user-facing surface. */
      var partials = comps.filter(function(c){ return c && c.degraded === true; });
      var partEN = '', partZH = '';
      if (partials.length){
        partEN = ' · Partial inputs: ' + partials.map(function(c){
          return (BNAME_EN[c.block] || c.block) + ' ' + c.legs_used + ' of ' + c.legs_expected;
        }).join(', ') + ' — confidence lowered to match.';
        partZH = ' · 部分输入：' + partials.map(function(c){
          return (BNAME_ZH[c.block] || c.block) + ' ' + c.legs_expected + '项中的' + c.legs_used + '项';
        }).join('、') + ' — 置信度已相应下调。';
      }
      return '<div class="rr-comp-section">'
        +'<div class="rr-comp-label">'
        +'<span class="l-en">Component-bridge waterfall</span>'
        +'<span class="l-zh">组件桥接瀑布</span>'
        +'</div>'
        +'<div class="rr-comp-rows">'+rows+'</div>'
        +'<div style="font-size:9.5px;color:var(--muted);margin-top:4px">'
        +'<span class="l-en">Prior-driven share: <b>'+esc(priorShare)+'</b> · Coverage residual: <b>'+esc(covResidual)+'</b>'+esc(partEN)+'</span>'
        +'<span class="l-zh">先验比重：<b>'+esc(priorShare)+'</b> · 覆盖残差：<b>'+esc(covResidual)+'</b>'+esc(partZH)+'</span>'
        +'</div>'
        +'</div>';
    }

    /* MRI-R24: v3_factor challenger shadow row */
    function v3FactorRow(v3, isClaims, isNfp){
      if (!v3) return '';
      var useK = isClaims || isNfp;
      var ptStr = v3.point != null ? (useK ? fmtK(v3.point) : fmtNum(v3.point,2)) : '—';
      var warning = v3.warning || '';
      return '<div class="rr-shadow-row">'
        +'<div class="rr-shadow-label">'
        +'<span class="l-en">V3 Factor · comparison model</span>'
        +'<span class="l-zh">V3 因子 · 对比模型</span>'
        +'</div>'
        +'<div style="font-size:11px;font-variant-numeric:tabular-nums">'
        +'<span class="l-en">Point: <b>'+esc(ptStr)+'</b></span>'
        +'<span class="l-zh">点预测：<b>'+esc(ptStr)+'</b></span>'
        +'</div>'
        +intervalBar(v3)
        +(warning?'<div class="rr-shadow-warn">'+esc(warning)+'</div>':'')
        +'</div>';
    }

    /* ---- MRI-R39a: expected-value sourcing (directive 3) ---- */
    /* Returns {val:string, label:{en,zh}, src:string|null} */
    function _expectedVal(item){
      var rel = (item.release||'').toLowerCase();
      var isClaims = rel === 'claims';
      var isNfp = rel === 'nfp';
      var useK = isClaims || isNfp;
      var er = item.expectation_read;
      /* (a) expectation_read.expectation_median when non-null */
      if (er && er.expectation_median != null){
        var srcs = er.sources || [];
        var srcTag = '';
        if (srcs.indexOf('cleveland_nowcast') !== -1) srcTag = 'CLE';
        else if (srcs.indexOf('kalshi') !== -1 || srcs.indexOf('polymarket') !== -1) srcTag = 'MKT';
        var valStr = useK ? fmtK(er.expectation_median) : fmtNum(er.expectation_median,2)+'pp';
        return {val:valStr, labelEN:'exp', labelZH:'预期', src:srcTag};
      }
      /* (b) bench median: naive_prior, trailing_3m (or trailing_4w for claims), ar_model,
             cleveland_nowcast, expanding_mean — EXCLUDE market_implied */
      var bs = item.benchmark_set || {};
      var benchKeys = isClaims
        ? ['naive_prior','trailing_4w','ar_model','expanding_mean']
        : ['naive_prior','trailing_3m','ar_model','cleveland_nowcast','expanding_mean'];
      var vals = [];
      benchKeys.forEach(function(k){
        var v = bs[k];
        if (v != null && !isNaN(Number(v))) vals.push(Number(v));
      });
      if (!vals.length) return null;
      vals.sort(function(a,b){return a-b;});
      var med = vals.length % 2 === 0
        ? (vals[vals.length/2-1]+vals[vals.length/2])/2
        : vals[Math.floor(vals.length/2)];
      var valStr = useK ? fmtK(med) : fmtNum(med,2)+'pp';
      return {val:valStr, labelEN:'bench', labelZH:'基准', src:null};
    }

    /* MRI-R40 honesty: a benchmark-augmented point is not "ours" alone. */
    function _usesBenchmarkAugmentedPrimary(item){
      var comb = item && item.combined;
      return !!(item
        && item.primary_forecast_basis === 'combined_v1_benchmark_augmented'
        && comb
        && comb.combined_point != null);
    }

    /* Context chips are valid only when they describe the displayed point's basis. */
    function _contextMetricsMatchPrimary(item){
      var primaryBasis = item && item.primary_forecast_basis;
      var contextBasis = item && item.context_metrics_basis;
      if (!primaryBasis) return true; /* legacy champion artifact */
      if (!contextBasis) return primaryBasis !== 'combined_v1_benchmark_augmented';
      return contextBasis === primaryBasis;
    }

    /* ---- MRI-R39a: compact card (operator directive 1-3) ---- */
    function renderCard(item){
      var rel = item.release || '';
      var rt = item.release_type || '';
      var proj = item.projection || {};
      var isClaims = rel.toLowerCase() === 'claims';
      var isNfp = rel.toLowerCase() === 'nfp';
      var isRetail = rel.toLowerCase() === 'retail';
      var useK = isClaims || isNfp;
      var isBenchmarkOnly = proj.mode === 'benchmark_only';
      /* no_data: retail_sales with no data or all projection intervals null */
      var pit = item.pit || {};
      var isNoData = isRetail && (
        String(pit.reason||'').indexOf('no_data') !== -1 ||
        (proj.p10 == null && proj.p90 == null)
      );
      var daysTo = item.days_to != null ? item.days_to : null;
      var daysLabel = daysTo != null
        ? ('<span class="l-en">in '+esc(daysTo)+'d</span>'
           +'<span class="l-zh">'+esc(daysTo)+'天后</span>')
        : ('<span class="l-en">awaiting date</span><span class="l-zh">待日期</span>');

      /* --- no_data card: compact one-liner --- */
      if (isNoData){
        return '<div class="rr-card" data-rr-rel="'+esc(rel)+'" data-rr-rt="'+esc(rt)+'">'
          +'<div class="rr-card-head">'
          +'<span class="rr-card-name">'+relName(rel,rt)+'</span>'
          +'<span class="rr-countdown">'+daysLabel+'</span>'
          +'</div>'
          +'<div class="rr-nodata-compact">'
          +'<span class="l-en">awaiting data</span>'
          +'<span class="l-zh">待数据</span>'
          +'</div>'
          +'<span class="rr-chevron">▸</span>'
          +'</div>';
      }

      /* --- MRI-R40: resolve the explicitly declared primary display basis --- */
      var comb = item.combined || null;
      var usesBenchmarkBlend = _usesBenchmarkAugmentedPrimary(item);
      var contextMetricsAligned = _contextMetricsMatchPrimary(item);
      var displayPoint = usesBenchmarkBlend ? comb.combined_point : proj.point;
      var displayP10 = (usesBenchmarkBlend && comb.p10 != null) ? comb.p10 : proj.p10;
      var displayP90 = (usesBenchmarkBlend && comb.p90 != null) ? comb.p90 : proj.p90;
      var displayP25 = (usesBenchmarkBlend && comb.p25 != null) ? comb.p25 : proj.p25;
      var displayP75 = (usesBenchmarkBlend && comb.p75 != null) ? comb.p75 : proj.p75;
      var primaryLabel = usesBenchmarkBlend
        ? '<span class="l-en">Model + benchmark blend</span><span class="l-zh">模型与基准混合</span>'
        : '<span class="l-en">ours</span><span class="l-zh">本方</span>';
      var primaryLabelStyle = usesBenchmarkBlend
        ? ' style="white-space:normal;text-transform:none;font-size:9.5px;letter-spacing:.04em;line-height:1.15;max-width:128px"'
        : '';

      /* --- OURS column --- */
      var oursVal = '—';
      if (!isBenchmarkOnly && displayPoint != null){
        oursVal = useK ? fmtK(displayPoint) : fmtNum(displayPoint,2)+'pp';
      }
      /* for NFP None-point: ours = '—' (fall through) */

      /* --- EXPECTED column (directive 3) --- */
      var expObj = _expectedVal(item);

      /* --- benchmark_only: ours=— (claims shows bench number only in exp col) --- */
      /* Already handled: isBenchmarkOnly → oursVal='—', expObj from bench median */

      /* --- ONE chip: expectation_read.tag preferred, else surprise_skew.tag --- */
      var er = item.expectation_read;
      var sk = item.surprise_skew;
      var chip = '';
      if (!isBenchmarkOnly && contextMetricsAligned){
        if (er && er.tag) chip = expectationChip(er);
        else if (sk && sk.tag) chip = skewChip(sk);
      }

      /* --- build nums row --- */
      var numsRow = '';
      if (isBenchmarkOnly){
        /* claims: show only bench number, no ours column */
        var bmoExp = expObj;
        numsRow = '<div class="rr-nums-row">'
          +(bmoExp
            ? '<div class="rr-num-col">'
              +'<div class="rr-num-lbl">'
              +'<span class="l-en">'+esc(bmoExp.labelEN)+'</span>'
              +'<span class="l-zh">'+esc(bmoExp.labelZH)+'</span>'
              +(bmoExp.src?'<span class="rr-num-src">'+esc(bmoExp.src)+'</span>':'')
              +'</div>'
              +'<div class="rr-num-val">'+esc(bmoExp.val)+'</div>'
              +'</div>'
            : '')
          +'</div>'
          +'<div class="rr-chips-row">'
          +'<span class="rr-bmo-tag">'
          +'<span class="l-en">benchmark-only</span>'
          +'<span class="l-zh">仅基准</span>'
          +'</span>'
          +'</div>';
      } else {
        /* normal card: ours + expected side by side */
        var expColHtml = expObj
          ? '<div class="rr-num-col">'
            +'<div class="rr-num-lbl">'
            +'<span class="l-en">'+esc(expObj.labelEN)+'</span>'
            +'<span class="l-zh">'+esc(expObj.labelZH)+'</span>'
            +(expObj.src?'<span class="rr-num-src">'+esc(expObj.src)+'</span>':'')
            +'</div>'
            +'<div class="rr-num-val">'+esc(expObj.val)+'</div>'
            +'</div>'
          : '';
        numsRow = '<div class="rr-nums-row">'
          +'<div class="rr-num-col">'
          +'<div class="rr-num-lbl"'+primaryLabelStyle+'>'+primaryLabel+'</div>'
          +(oursVal==='—'
            ? '<div class="rr-num-dash">—</div>'
            : '<div class="rr-num-val">'+esc(oursVal)+'</div>')
          +'</div>'
          +expColHtml
          +'</div>'
          +(chip?'<div class="rr-chips-row">'+chip+'</div>':'');
      }

      return '<div class="rr-card" data-rr-rel="'+esc(rel)+'" data-rr-rt="'+esc(rt)+'">'
        +'<div class="rr-card-head">'
        +'<span class="rr-card-name">'+relName(rel, rt)+'</span>'
        +'<span class="rr-card-period">'+esc(item.period||'')+'</span>'
        +'<span class="rr-countdown">'+daysLabel+'</span>'
        +'</div>'
        +numsRow
        +'<span class="rr-chevron">▸</span>'
        +'</div>';
    }

    /* ---- MRI-R39: 5-tab modal ---- */
    /* Tabs: 0=OVERVIEW 1=MODELS 2=COMPONENTS 3=HISTORY 4=CONTEXT */
    /* Null tabs (no content) hidden entirely. */

    /* inline SVG interval cone with benchmark ticks — spec: viewBox 0 0 320 56 */
    function intervalConeSVG(proj, bs, rel){
      if (!proj) return '';
      var p10 = proj.p10, p90 = proj.p90, pt = proj.point;
      if (p10 == null || p90 == null) return '';
      var span = p90 - p10;
      if (span <= 0) return '';
      var p25 = proj.p25, p75 = proj.p75;
      var W = 320, H = 56, PAD = 24;
      var iW = W - 2*PAD;
      function xOf(v){ return PAD + Math.max(0,Math.min(iW,(v-p10)/span*iW)); }
      /* p25-p75 shaded box */
      var boxL = p25 != null ? xOf(p25) : xOf(p10);
      var boxR = p75 != null ? xOf(p75) : xOf(p90);
      /* point marker */
      var ptX = pt != null ? xOf(pt) : (proj.p50 != null ? xOf(proj.p50) : null);
      var isClaims = (rel||'').toLowerCase() === 'claims';
      var isNfp = (rel||'').toLowerCase() === 'nfp';
      var useK = isClaims || isNfp;
      /* benchmark ticks — same-basis only (not market_implied which is YoY/level) */
      var benchKeys = ['naive_prior','trailing_3m','trailing_4w','ar_model','cleveland_nowcast','expanding_mean'];
      var benchLabels = {naive_prior:'naive',trailing_3m:'3m',trailing_4w:'4w',ar_model:'AR',cleveland_nowcast:'CLE',expanding_mean:'xmn'};
      var ticks = [];
      if (bs) {
        benchKeys.forEach(function(k){
          var v = bs[k];
          if (v == null || v < p10 || v > p90) return;
          ticks.push({x:xOf(v), label:benchLabels[k]||k, v:v});
        });
      }
      var svgParts = ['<svg viewBox="0 0 320 56" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:56px;display:block;overflow:visible">'];
      /* whisker line p10-p90 */
      svgParts.push('<line x1="'+xOf(p10)+'" y1="28" x2="'+xOf(p90)+'" y2="28" stroke="var(--line)" stroke-width="2"/>');
      /* end caps */
      svgParts.push('<line x1="'+xOf(p10)+'" y1="22" x2="'+xOf(p10)+'" y2="34" stroke="var(--muted)" stroke-width="1.5"/>');
      svgParts.push('<line x1="'+xOf(p90)+'" y1="22" x2="'+xOf(p90)+'" y2="34" stroke="var(--muted)" stroke-width="1.5"/>');
      /* p25-p75 shaded box */
      svgParts.push('<rect x="'+boxL+'" y="20" width="'+(boxR-boxL)+'" height="16" fill="color-mix(in srgb,var(--up) 28%,transparent)" rx="2"/>');
      /* benchmark ticks (muted) */
      ticks.forEach(function(t){
        svgParts.push('<line x1="'+t.x+'" y1="15" x2="'+t.x+'" y2="41" stroke="var(--muted)" stroke-width="1" stroke-dasharray="2,2"/>');
        svgParts.push('<text x="'+t.x+'" y="12" text-anchor="middle" font-size="8" fill="var(--muted)" font-family="ui-monospace,monospace">'+esc(t.label)+'</text>');
      });
      /* point marker */
      if (ptX != null){
        var ptLabel = useK ? fmtK(pt) : fmtNum(pt,2);
        svgParts.push('<line x1="'+ptX+'" y1="14" x2="'+ptX+'" y2="42" stroke="var(--text)" stroke-width="2.5"/>');
        svgParts.push('<text x="'+ptX+'" y="52" text-anchor="middle" font-size="9" fill="var(--text)" font-family="ui-monospace,monospace" font-weight="bold">'+esc(ptLabel)+'</text>');
      }
      /* p10/p90 labels */
      svgParts.push('<text x="'+PAD+'" y="52" text-anchor="start" font-size="8" fill="var(--muted)" font-family="ui-monospace,monospace">p10 '+(useK?fmtK(p10):fmtNum(p10,2))+'</text>');
      svgParts.push('<text x="'+(W-PAD)+'" y="52" text-anchor="end" font-size="8" fill="var(--muted)" font-family="ui-monospace,monospace">p90 '+(useK?fmtK(p90):fmtNum(p90,2))+'</text>');
      svgParts.push('</svg>');
      return svgParts.join('');
    }

    /* model dot plot — shared HTML/CSS axis; text remains native and never stretches */
    function modelDotPlot(item, isBenchmarkOnly, isClaims, isNfp){
      if (isBenchmarkOnly) return '';
      var proj = item.projection || {};
      var shadows = item.shadows || {};
      var mi = (item.benchmark_set||{}).market_implied;
      var useK = isClaims || isNfp;
      /* collect model points: champion, v3_factor, cpi_bridge, mf_energy */
      var models = [];
      if (proj.point != null) models.push({key:'champion',pt:proj.point,p10:proj.p10,p90:proj.p90,shape:'filled',label:'Champion'});
      var v3 = shadows.v3_factor;
      if (v3 && v3.point != null) models.push({key:'v3_factor',pt:v3.point,p10:v3.p10,p90:v3.p90,shape:'hollow',label:'v3_factor'});
      var bridge = shadows.cpi_bridge;
      if (bridge && bridge.point != null) models.push({key:'cpi_bridge',pt:bridge.point,shape:'diamond',label:'cpi_bridge'});
      var mfe = shadows.mf_energy;
      if (mfe && mfe.point != null) models.push({key:'mf_energy',pt:mfe.point,p10:mfe.p10,p90:mfe.p90,shape:'triangle',label:'mf_energy'});
      if (!models.length) return '';
      /* axis range: min/max of all model points + p10/p90 */
      var allVals = [];
      models.forEach(function(m){ allVals.push(m.pt); if(m.p10!=null)allVals.push(m.p10); if(m.p90!=null)allVals.push(m.p90); });
      var vMin = Math.min.apply(null,allVals), vMax = Math.max.apply(null,allVals);
      if (vMin === vMax){ vMin -= 0.05; vMax += 0.05; }
      var span = vMax - vMin;
      function pctOf(v){ return Math.max(0,Math.min(100,(v-vMin)/span*100)); }
      var rows = models.map(function(m){
        var pointPct = pctOf(m.pt);
        var range = '';
        if (m.p10 != null && m.p90 != null){
          var rangeL = pctOf(m.p10), rangeR = pctOf(m.p90);
          range = '<span class="rr-model-range" style="left:'+rangeL.toFixed(1)+'%;width:'+Math.max(0,rangeR-rangeL).toFixed(1)+'%"></span>';
        }
        var valStr = useK ? fmtK(m.pt) : fmtNum(m.pt,2);
        return '<div class="rr-model-row'+(m.key==='champion'?' rr-model-row-champion':'')+'">'
          +'<span class="rr-model-name">'+esc(m.label)+'</span>'
          +'<span class="rr-model-track">'+range
          +'<span class="rr-model-marker rr-marker-'+esc(m.shape)+'" style="left:'+pointPct.toFixed(1)+'%"></span>'
          +'</span>'
          +'<span class="rr-model-value">'+esc(valStr)+'</span>'
          +'</div>';
      }).join('');
      var lowLabel = useK ? fmtK(vMin) : fmtNum(vMin,2);
      var highLabel = useK ? fmtK(vMax) : fmtNum(vMax,2);
      var html = '<div class="rr-model-plot" role="img" aria-label="Model comparison on one shared scale">'
        +rows
        +'<div class="rr-model-scale"><span></span><span class="rr-model-scale-track">'
        +'<span>'+esc(lowLabel)+'</span>'
        +'<span class="rr-model-scale-label"><span class="l-en">shared scale</span><span class="l-zh">统一刻度</span></span>'
        +'<span>'+esc(highLabel)+'</span>'
        +'</span><span></span></div>'
        +'</div>';
      /* market-implied in own row, explicit basis tag, NEVER on shared axis */
      if (mi){
        var miVal = mi.implied_median != null ? fmtNum(mi.implied_median,2) : (mi.implied != null ? String(mi.implied) : '—');
        var miSrc = mi.source === 'kalshi' ? 'Kalshi' : mi.source === 'polymarket' ? 'Polymarket' : esc(mi.source||'');
        var basisNote = esc(mi.event_title||'');
        html += '<div class="rr-mkt-row">'
          +'<span class="rr-mkt-label"><span class="l-en">Market-implied</span><span class="l-zh">市场隐含</span></span>'
          +'<span class="rr-mkt-val">'+esc(miVal)+'</span>'
          +'<span class="rr-mkt-source">'+esc(miSrc)+'</span>'
          +(basisNote?'<span style="font-size:9px;color:var(--muted);margin-left:4px" title="'+esc(basisNote)+'">'
            +'<span class="l-en">different basis</span><span class="l-zh">不同基准</span></span>':'')
          +'</div>';
      }
      return html;
    }

    /* surprise anatomy mini-table for history tab */
    function surpriseAnatomyTable(releaseKey){
      /* static catalog — filtered by release family */
      var catalog = [
        {date:'2001-03',rel:'NFP',miss:'MISS',cause:'Seasonal anomaly'},
        {date:'2002-01',rel:'NFP',miss:'BEAT',cause:'Benchmark revision'},
        {date:'2005-09',rel:'NFP',miss:'MISS',cause:'Hurricane Katrina (-35k)'},
        {date:'2005-10',rel:'NFP',miss:'BEAT',cause:'Katrina bounce'},
        {date:'2005-09',rel:'CPI',miss:'BEAT',cause:'Hurricane energy spike'},
        {date:'2008-01',rel:'NFP',miss:'MISS',cause:'Recession onset'},
        {date:'2010-05',rel:'NFP',miss:'BEAT',cause:'Census hiring (+411k)'},
        {date:'2011-09',rel:'CPI',miss:'BEAT',cause:'Supply chain / energy'},
        {date:'2019-10',rel:'NFP',miss:'MISS',cause:'GM strike (-50k)'},
        {date:'2021-04',rel:'NFP',miss:'MISS',cause:'Labor supply shortfall'},
        {date:'2021-10',rel:'CPI',miss:'BEAT',cause:'Shelter surge acceleration'},
        {date:'2022-06',rel:'CPI',miss:'BEAT',cause:'Energy+shelter peak'},
        {date:'2023-01',rel:'NFP',miss:'BEAT',cause:'Birth-death + seasonal factor'},
        {date:'2024-08',rel:'NFP',miss:'MISS',cause:'Benchmark revision -818k'},
        {date:'2025-01',rel:'CPI',miss:'BEAT',cause:'Annual weight-update'}
      ];
      var rk = (releaseKey||'').toUpperCase();
      var filtered = catalog.filter(function(e){
        if (rk.indexOf('NFP')!==-1 || rk.indexOf('PAYROLL')!==-1) return e.rel==='NFP';
        if (rk.indexOf('CPI')!==-1) return e.rel==='CPI';
        return true;
      });
      if (!filtered.length) return '';
      var rows = filtered.slice(0,8).map(function(e){
        return '<tr>'
          +'<td>'+esc(e.date)+'</td>'
          +'<td>'+esc(e.miss)+'</td>'
          +'<td>'+esc(e.cause)+'</td>'
          +'</tr>';
      }).join('');
      return '<table class="rr-anatomy-table">'
        +'<thead><tr>'
        +'<th><span class="l-en">Date</span><span class="l-zh">日期</span></th>'
        +'<th><span class="l-en">vs Exp</span><span class="l-zh">结果</span></th>'
        +'<th><span class="l-en">Cause</span><span class="l-zh">原因</span></th>'
        +'</tr></thead>'
        +'<tbody>'+rows+'</tbody>'
        +'</table>';
    }

    /* ---- MRI-R39: 5-tab renderModal ---- */
    function renderModal(item, captureHealth){
      var rel = item.release || '';
      var rt = item.release_type || '';
      var proj = item.projection || {};
      var isClaims = rel.toLowerCase() === 'claims';
      var isNfp = rel.toLowerCase() === 'nfp';
      var isRetail = rel.toLowerCase() === 'retail';
      var useK = isClaims || isNfp;
      var isBenchmarkOnly = proj.mode === 'benchmark_only';
      var pit = item.pit || {};
      var isNoData = isRetail && (
        String(pit.reason||'').indexOf('no_data') !== -1 ||
        (proj.p10 == null && proj.p90 == null)
      );
      var shadows = item.shadows || {};
      var v3 = shadows.v3_factor || null;
      var bridge = shadows.cpi_bridge || null;
      var mfe = shadows.mf_energy || null;
      var cf = item.coverage_flags || null;
      var conf = item.confidence;
      var er = item.expectation_read;
      var sk = item.surprise_skew;
      var pi = item.print_integrity || null;
      var piRegime = pi ? (pi.regime || 'normal') : null;
      /* MRI-R40: combined block */
      var comb = item.combined || null;
      var usesBenchmarkBlend = _usesBenchmarkAugmentedPrimary(item);
      var contextMetricsAligned = _contextMetricsMatchPrimary(item);
      var dispPt = usesBenchmarkBlend ? comb.combined_point : proj.point;
      var dispP10 = (usesBenchmarkBlend && comb.p10 != null) ? comb.p10 : proj.p10;
      var dispP90 = (usesBenchmarkBlend && comb.p90 != null) ? comb.p90 : proj.p90;
      var dispP25 = (usesBenchmarkBlend && comb.p25 != null) ? comb.p25 : proj.p25;
      var dispP75 = (usesBenchmarkBlend && comb.p75 != null) ? comb.p75 : proj.p75;
      /* build a display-proj object for intervalConeSVG */
      var dispProj = usesBenchmarkBlend ? {
        point: dispPt, p10: dispP10, p25: dispP25,
        p50: (comb.p50 != null ? comb.p50 : proj.p50),
        p75: dispP75, p90: dispP90
      } : proj;

      /* ---- TAB 0: OVERVIEW ---- */
      var tab0 = '';
      {
        /* large point — sources the declared primary basis */
        var ptStr = '—';
        if (!isBenchmarkOnly && !isNoData && dispPt != null)
          ptStr = useK ? fmtK(dispPt) : fmtNum(dispPt,2)+(rt.indexOf('nfp')===-1?'pp':'');
        /* "Blend of N inputs" receipt line — models and benchmarks are distinct. */
        var combInputs = (usesBenchmarkBlend && comb && comb.combined_components
          && Array.isArray(comb.combined_components.inputs_used))
          ? comb.combined_components.inputs_used : [];
        var combNStr = '';
        if (combInputs.length > 0) combNStr = String(combInputs.length);
        var includesCleveland = combInputs.indexOf('cleveland') !== -1;
        var combSubtitle = combNStr
          ? '<div style="font-size:10px;color:var(--muted);margin-top:1px">'
            +'<span class="l-en">Blend of '+esc(combNStr)+' inputs'
              +(includesCleveland?' · includes Cleveland benchmark':'')+'</span>'
            +'<span class="l-zh">'+esc(combNStr)+'项输入混合'
              +(includesCleveland?' · 含克利夫兰基准':'')+'</span>'
            +'</div>'
          : '';
        var pointLabelEN = usesBenchmarkBlend ? 'Model + benchmark blend' : 'Our projection';
        var pointLabelZH = usesBenchmarkBlend ? '模型与基准混合' : '本方预测';
        tab0 += '<div class="rr-grp">'
          +'<div style="font-size:28px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.1">'+esc(ptStr)+'</div>'
          +'<div style="font-size:10px;color:var(--muted);margin-top:2px">'
          +'<span class="l-en">'+pointLabelEN+' · '+esc(item.period||'')+(item.release_date?' · '+esc(item.release_date):'')+'</span>'
          +'<span class="l-zh">'+pointLabelZH+' · '+esc(item.period||'')+(item.release_date?' · '+esc(item.release_date):'')+'</span>'
          +'</div>'
          +combSubtitle
          +'</div>';
        /* SVG cone — use combined interval when available */
        if (!isBenchmarkOnly && !isNoData && dispP10 != null){
          tab0 += '<div class="rr-grp">'+intervalConeSVG(dispProj, item.benchmark_set, rel)+'</div>';
        }
        /* chips + coverage */
        var chips = '';
        if (!isBenchmarkOnly && !isNoData){
          if (contextMetricsAligned){
            chips += expectationChip(er||null);
            chips += skewChip(sk||null);
          }
          chips += coverageChip(cf||null);
        }
        if (chips) tab0 += '<div class="rr-grp"><div class="rr-chips-row">'+chips+'</div></div>';
        /* vs strongest benchmark delta — use display point */
        if (!isBenchmarkOnly && !isNoData && dispPt != null && item.benchmark_set){
          var bs2 = item.benchmark_set;
          var bVals = [bs2.naive_prior, bs2.trailing_3m, bs2.ar_model, bs2.cleveland_nowcast, bs2.expanding_mean];
          bVals = bVals.filter(function(v){return v != null;});
          if (bVals.length){
            var bMedian = bVals.slice().sort(function(a,b){return a-b;})[Math.floor(bVals.length/2)];
            var delta = dispPt - bMedian;
            var dSign = delta >= 0 ? '+' : '';
            var dStr = useK ? dSign+fmtNum(delta,0)+'k' : dSign+fmtNum(delta,2)+'pp';
            tab0 += '<div style="font-size:10.5px;color:var(--muted)">'
              +'<span class="l-en">vs benchmark median: <b style="color:var(--text)">'+esc(dStr)+'</b></span>'
              +'<span class="l-zh">vs基准中位数：<b style="color:var(--text)">'+esc(dStr)+'</b></span>'
              +'</div>';
          }
        }
        /* benchmark-only / no-data states */
        if (isBenchmarkOnly){
          tab0 += '<div class="rr-empty">'
            +'<span class="l-en">Benchmark-only — §6 kill rule triggered; no model point. Benchmarks in Models tab.</span>'
            +'<span class="l-zh">仅基准 — §6规则触发；无模型点预测。基准见模型标签页。</span>'
            +'</div>';
        }
        if (isNoData){
          tab0 += '<div class="rr-empty">'
            +'<span class="l-en">Awaiting data — series not yet on disk; machinery ready.</span>'
            +'<span class="l-zh">待数据 — 系列未入库，系统就绪。</span>'
            +'</div>';
        }
        /* confidence */
        if (!isBenchmarkOnly && !isNoData && conf != null){
          tab0 += '<div style="font-size:10px;color:var(--muted);margin-top:6px">'
            +'<span class="l-en">Confidence: <b style="color:var(--text)">'+esc(fmtPct(conf))+'</b></span>'
            +'<span class="l-zh">置信度：<b style="color:var(--text)">'+esc(fmtPct(conf))+'</b></span>'
            +'</div>';
        }
      }

      /* ---- TAB 1: MODELS ---- */
      var tab1 = '';
      {
        /* model dot plot */
        if (!isBenchmarkOnly && !isNoData){
          tab1 += '<div class="rr-grp"><div class="rr-grp-label">'
            +'<span class="l-en">Model comparison</span><span class="l-zh">模型对比</span>'
            +'</div>'
            +modelDotPlot(item, isBenchmarkOnly, isClaims, isNfp)
            +'</div>';
        }
        /* benchmark table */
        if (item.benchmark_set){
          tab1 += '<div class="rr-grp"><div class="rr-grp-label">'
            +'<span class="l-en">Benchmarks (not investment advice)</span><span class="l-zh">基准对比（非投资建议）</span>'
            +'</div>';
          var bs = item.benchmark_set;
          var isCl2 = isClaims;
          var bench2rows = [];
          if (bs.naive_prior != null)
            bench2rows.push(['<span class="l-en">Naive prior</span><span class="l-zh">朴素先验</span>', useK?fmtK(bs.naive_prior):fmtNum(bs.naive_prior,2)]);
          if (isCl2 && bs.trailing_4w != null)
            bench2rows.push(['<span class="l-en">Trailing 4w</span><span class="l-zh">近4周均值</span>', fmtK(bs.trailing_4w)]);
          if (!isCl2 && bs.trailing_3m != null)
            bench2rows.push(['<span class="l-en">Trailing 3m</span><span class="l-zh">近3月均值</span>', useK?fmtK(bs.trailing_3m):fmtNum(bs.trailing_3m,2)]);
          if (bs.ar_model != null)
            bench2rows.push(['AR model', useK?fmtK(bs.ar_model):fmtNum(bs.ar_model,2)]);
          if (!isCl2 && !isNfp && bs.cleveland_nowcast != null)
            bench2rows.push(['Cleveland nowcast', fmtNum(bs.cleveland_nowcast,2)]);
          if (bs.expanding_mean != null)
            bench2rows.push(['<span class="l-en">Expanding mean</span><span class="l-zh">累积均值</span>', useK?fmtK(bs.expanding_mean):fmtNum(bs.expanding_mean,2)]);
          tab1 += bench2rows.map(function(r){
            return '<div class="rr-bench-row"><span class="rr-bench-name">'+r[0]+'</span><span class="rr-bench-val">'+esc(r[1])+'</span></div>';
          }).join('');
          tab1 += '</div>';
        }
        /* v3_factor shadow */
        if (!isBenchmarkOnly && v3){
          tab1 += '<div class="rr-grp">'+v3FactorRow(v3, isClaims, isNfp)+'</div>';
        }
        /* MRI-R40: combined_v1 weight receipt (technical detail — hover/receipt per DESIGN_DOCTRINE) */
        if (!isBenchmarkOnly && comb && comb.combined_components){
          var cc = comb.combined_components;
          var ccInputs = cc.inputs_used || [];
          var ccWeights = cc.weights || {};
          var ccPoints = cc.points || {};
          var ccMAE = cc.MAE_shrunk_i || {};
          var ccCold = cc.cold_start;
          var ccRows = ccInputs.map(function(iid){
            var w = ccWeights[iid]; var pt = ccPoints[iid];
            var wStr = w != null ? (Math.round(w*1000)/10).toFixed(1)+'%' : '—';
            var ptStr2 = pt != null ? fmtNum(pt,2) : '—';
            return '<div class="rr-bench-row"><span class="rr-bench-name">'+esc(iid)+'</span>'
              +'<span class="rr-bench-val">'+esc(ptStr2)+'pp &nbsp; <span style="color:var(--muted)">w='+esc(wStr)+'</span></span></div>';
          }).join('');
          var coldNote = ccCold
            ? '<div style="font-size:9.5px;color:var(--muted);margin-top:3px">'
              +'<span class="l-en">Equal weights (cold start — no scored prints yet)</span>'
              +'<span class="l-zh">等权重（冷启动，尚无评分数据）</span>'
              +'</div>'
            : '';
          tab1 += '<div class="rr-grp"><div class="rr-grp-label">'
            +'<span class="l-en">Blend weights (display-only receipt)</span>'
            +'<span class="l-zh">混合权重（仅展示收据）</span>'
            +'</div>'
            +ccRows
            +coldNote
            +'</div>';
        }
        /* market-implied: already rendered inside modelDotPlot() with basis tag — do NOT add again here */
        /* surprise distribution — gated on !isBenchmarkOnly */
        var sd = item.surprise_distribution;
        if (!isBenchmarkOnly && !isNoData && contextMetricsAligned && sd){
          tab1 += '<div class="rr-grp"><div class="rr-grp-label">'
            +'<span class="l-en">Surprise distribution</span><span class="l-zh">惊喜分布</span>'
            +'</div>'
            +surpriseDistGauge(sd)
            +'</div>';
        }
        if (!tab1){
          tab1 = '<div class="rr-empty">'
            +'<span class="l-en">Benchmark-only — no model point available.</span>'
            +'<span class="l-zh">仅基准 — 无模型点预测。</span>'
            +'</div>';
        }
      }

      /* ---- TAB 2: COMPONENTS ---- */
      var tab2 = '';
      /* champion attribution — gated on !isBenchmarkOnly */
      var champComponents = (item.components && Array.isArray(item.components) && item.components.length) ? item.components : null;
      if (!isBenchmarkOnly && !isNoData && champComponents){
        tab2 += '<div class="rr-grp"><div class="rr-grp-label">'
          +'<span class="l-en">Champion attribution</span><span class="l-zh">冠军归因</span>'
          +'</div>'
          +componentsBar(champComponents, rel)
          +'</div>';
      }
      /* CPI bridge waterfall — gated on !isBenchmarkOnly */
      if (!isBenchmarkOnly && !isNoData && bridge){
        tab2 += '<div class="rr-grp"><div class="rr-grp-label">'
          +'<span class="l-en">Component-bridge waterfall</span><span class="l-zh">组件桥接瀑布</span>'
          +'</div>'
          +cpiBridgeWaterfall(bridge)
          +'</div>';
      }
      /* confidence composition — gated on !isBenchmarkOnly */
      var cv2 = item.confidence_v2 != null ? item.confidence_v2 : conf;
      var cv2comps = item.confidence_components_v2 || null;
      if (!isBenchmarkOnly && !isNoData && cv2 != null){
        if (!cv2comps && cf && cf.weight_coverage > 0){
          var wc2 = Number(cf.weight_coverage||0);
          var fp2 = Number(cf.fresh_proxy_coverage||0);
          var nv2 = Number(cf.non_vintaged_share||0);
          cv2comps = {w_known:wc2*(1-nv2),w_proxy:wc2*nv2+(1-wc2)*fp2,w_residual:Math.max(0,1-wc2*(1-nv2)-wc2*nv2-(1-wc2)*fp2)};
        }
        if (!isBenchmarkOnly && cv2comps){
          tab2 += '<div class="rr-grp"><div class="rr-grp-label">'
            +'<span class="l-en">Confidence composition</span><span class="l-zh">置信度构成</span>'
            +'</div>'
            +confidenceBar(cv2, cv2comps)
            +'</div>';
        }
      }

      /* ---- TAB 3: HISTORY ---- */
      var tab3 = '';
      {
        /* scoreboard — accruing note when empty */
        tab3 += '<div class="rr-grp"><div class="rr-grp-label">'
          +'<span class="l-en">Track record</span><span class="l-zh">历史评分</span>'
          +'</div>'
          +'<div class="rr-empty">'
          +'<span class="l-en">Accruing — first scored prints land this month.</span>'
          +'<span class="l-zh">积累中 — 本月首批评分数据到来。</span>'
          +'</div>'
          +'</div>';
        /* NFP revision context */
        if (isNfp && item.revision_context){
          var rc = item.revision_context;
          var lb = (rc.level_bias_annotation||null);
          tab3 += '<div class="rr-grp"><div class="rr-grp-label">'
            +'<span class="l-en">NFP revision intelligence</span><span class="l-zh">NFP修正情报</span>'
            +'</div>';
          if (lb){
            tab3 += '<div style="font-size:10.5px;color:var(--muted);line-height:1.6">'
              +'<span class="l-en">Level bias: expansions <b>+'+esc(lb.expansion_mean_cumulative_revision_k||'?')+'k</b> mean cumulative · contractions <b>'+esc(lb.contraction_mean_cumulative_revision_k||'?')+'k</b></span>'
              +'<span class="l-zh">水平偏差：扩张期平均累积 <b>+'+esc(lb.expansion_mean_cumulative_revision_k||'?')+'k</b> · 收缩期 <b>'+esc(lb.contraction_mean_cumulative_revision_k||'?')+'k</b></span>'
              +'</div>';
          }
          var ms = (rc.model_status||null);
          if (ms){
            tab3 += '<div style="font-size:9.5px;color:var(--muted);margin-top:4px;font-style:italic">'+esc(ms.note||'')+'</div>';
          }
          /* revision risk from item — gated on !isBenchmarkOnly */
          var rrisk = item.revision_risk;
          if (!isBenchmarkOnly && rrisk){
            tab3 += '<div style="margin-top:4px">'+revisionRiskLine(rrisk)+'</div>';
          }
          tab3 += '</div>';
        }
        /* surprise anatomy reference table */
        var relKey = rt || rel;
        var anatomyHTML = surpriseAnatomyTable(relKey);
        if (anatomyHTML){
          tab3 += '<div class="rr-grp"><div class="rr-grp-label">'
            +'<span class="l-en">Surprise anatomy — notable episodes</span><span class="l-zh">意外解析 — 典型案例</span>'
            +'</div>'
            +anatomyHTML
            +'</div>';
        }
      }

      /* ---- TAB 4: CONTEXT ---- */
      var tab4 = '';
      {
        /* W4 EVW: event-window phase + collision context (display-only, RIC program).
           Reads item.event_window_ctx attached by build_release_forecast._attach_evw_context().
           is_context_only=True — display only, never scored (RIC-R3, DO_NOT_REBUILD.md §4). */
        var evwCtx = item.event_window_ctx;
        if (evwCtx && evwCtx.is_context_only) {
          var evwParts = [];
          /* Phase read */
          if (evwCtx.phase && evwCtx.phase !== 'quiet') {
            evwParts.push(
              '<div class="rr-ctx-row">'
              +'<span class="l-en">'+esc(evwCtx.phase_read_en||'')+'</span>'
              +'<span class="l-zh">'+esc(evwCtx.phase_read_zh||'')+'</span>'
              +'</div>'
            );
          }
          /* Active collisions */
          if (evwCtx.active_collisions && evwCtx.active_collisions.length) {
            var colCopy = {
              cpi_in_opex_week: {
                en: 'CPI lands inside expiration week — expect louder tape. Watch, don’t chase.',
                zh: 'CPI 落于期权到期周内——预计市场噪音更大。观望为主，勿追涨。'
              },
              fomc_in_opex_week: {
                en: 'Fed decision inside expiration week — pin risk elevated.',
                zh: '美联储决议落于到期周内——锁定风险上升。'
              },
              cpi_fomc_same_week: {
                en: 'CPI and Fed decision same week — one print can reset the other’s read.',
                zh: 'CPI 与美联储决议同周发布——一个数据可能重置另一个的解读。'
              },
              triple_stack: {
                en: 'Triple stack: data print, Fed, and OPEX converge this week — louder tape likely.',
                zh: '三重叠加：数据、美联储与期权到期本周齐发——市场噪音可能明显放大。'
              }
            };
            evwCtx.active_collisions.forEach(function(c){
              var cp = colCopy[c];
              if (cp) evwParts.push(
                '<div class="rr-ctx-row">'
                +'<span class="l-en">'+esc(cp.en)+'</span>'
                +'<span class="l-zh">'+esc(cp.zh)+'</span>'
                +'</div>'
              );
            });
          }
          /* Ex-ante read */
          var ea = evwCtx.ex_ante;
          if (ea && ea.available) {
            evwParts.push(
              '<div class="rr-ctx-row" style="margin-top:4px;font-size:10.5px">'
              +'<span class="l-en">'+esc(ea.glance_en||'')+'</span>'
              +'<span class="l-zh">'+esc(ea.glance_zh||'')+'</span>'
              +'</div>'
            );
            /* Disclaimer */
            evwParts.push(
              '<div style="font-size:9.5px;color:var(--muted);margin-top:2px">'
              +'<span class="l-en">'+esc(ea.disclaimer_en||'')+'</span>'
              +'<span class="l-zh">'+esc(ea.disclaimer_zh||'')+'</span>'
              +'</div>'
            );
          }
          if (evwParts.length) {
            tab4 += '<div class="rr-grp"><div class="rr-grp-label">'
              +'<span class="l-en">Calendar context</span><span class="l-zh">日历参考</span>'
              +'</div>'
              +evwParts.join('')
              +'<div style="font-size:9px;color:var(--muted);margin-top:3px">'
              +'<span class="l-en">Display context only — not a signal, no return claim (RIC-R3).</span>'
              +'<span class="l-zh">仅供展示 — 非信号，不作收益主张。</span>'
              +'</div></div>';
          }
        }

        /* policy backdrop */
        if (item.policy_backdrop){
          tab4 += '<div class="rr-grp"><div class="rr-grp-label">'
            +'<span class="l-en">Policy backdrop</span><span class="l-zh">政策背景</span>'
            +'</div>'
            +policyStrip(item.policy_backdrop)
            +'</div>';
        }
        /* reaction sensitivity — gated on !isBenchmarkOnly */
        var rsi = item.reaction_sensitivity;
        if (!isBenchmarkOnly && !isNoData && rsi){
          tab4 += '<div class="rr-grp"><div class="rr-grp-label">'
            +'<span class="l-en">Reaction sensitivity</span><span class="l-zh">市场反应敏感度</span>'
            +'</div>'
            +reactionSensRow(rsi)
            +'</div>';
        }
        /* quirk chips */
        if (item.quirk_flags && item.quirk_flags.length){
          tab4 += '<div class="rr-grp"><div class="rr-grp-label">'
            +'<span class="l-en">Quirk flags</span><span class="l-zh">特殊标记</span>'
            +'</div>'
            +quirkChips(item.quirk_flags)
            +'</div>';
        }
        /* print integrity chip */
        if (pi && piRegime){
          var piCls = piRegime==='normal'?'rr-integrity-normal':piRegime==='disrupted'?'rr-integrity-disrupted':'rr-integrity-degraded';
          var piEN = piRegime==='normal'?'Normal':piRegime==='disrupted'?'Disrupted':'Degraded';
          var piZH = piRegime==='normal'?'正常':piRegime==='disrupted'?'中断':'退化';
          tab4 += '<div class="rr-grp"><div class="rr-grp-label">'
            +'<span class="l-en">Print integrity</span><span class="l-zh">数据完整性</span>'
            +'</div>'
            +'<span class="rr-integrity-chip '+esc(piCls)+'">'
            +'<span class="l-en">'+esc(piEN)+'</span>'
            +'<span class="l-zh">'+esc(piZH)+'</span>'
            +'</span>';
          /* sub-readings */
          var subParts = [];
          if (pi.cpi_median_se_trend) subParts.push('SE trend: '+esc(pi.cpi_median_se_trend));
          if (pi.revision_streak) subParts.push('revision streak: '+esc(pi.revision_streak));
          if (subParts.length) tab4 += '<div style="font-size:9.5px;color:var(--muted);margin-top:4px">'+subParts.join(' · ')+'</div>';
          tab4 += '</div>';
        }
        /* capture health strip */
        if (captureHealth && captureHealth.past_due_unscored && captureHealth.past_due_unscored.length){
          tab4 += '<div class="rr-grp"><div class="rr-grp-label">'
            +'<span class="l-en">Capture health</span><span class="l-zh">采集健康</span>'
            +'</div>'
            +'<div class="rr-health-strip">'
            +'<span class="l-en"><span class="rr-health-warn">&#9888;</span> '+captureHealth.past_due_unscored.length+' past-due unscored: '
            +captureHealth.past_due_unscored.map(function(u){return esc((u.release||'')+'/'+(u.period||'')+' ('+u.reason+')');}).join(', ')
            +'</span>'
            +'<span class="l-zh"><span class="rr-health-warn">&#9888;</span> '+captureHealth.past_due_unscored.length+' 待评分: '
            +captureHealth.past_due_unscored.map(function(u){return esc((u.release||'')+'/'+(u.period||''));}).join(', ')
            +'</span>'
            +'</div></div>';
        }
        if (!tab4){
          tab4 = '<div class="rr-empty">'
            +'<span class="l-en">No context data for this release.</span>'
            +'<span class="l-zh">此数据发布无上下文信息。</span>'
            +'</div>';
        }
      }

      return {tab0:tab0, tab1:tab1, tab2:tab2, tab3:tab3, tab4:tab4};
    }

    /* ---- modal open / close / tab switching ---- */
    var _rrItems = [];
    var _captureHealth = null;

    /* ---- modal open / close ---- */
    function _rrPeriodLabels(period){
      var raw = String(period||'');
      var m = /^(\d{4})-(\d{2})$/.exec(raw);
      if (!m) return {en:raw,zh:raw};
      var month = Number(m[2]);
      var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      if (month < 1 || month > 12) return {en:raw,zh:raw};
      return {en:months[month-1]+' '+m[1],zh:m[1]+'年'+month+'月'};
    }
    function _rrDateLabels(dateStr){
      var raw = String(dateStr||'');
      var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);
      if (!m) return {en:raw,zh:raw};
      var month = Number(m[2]), day = Number(m[3]);
      var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      if (month < 1 || month > 12) return {en:raw,zh:raw};
      return {en:'Releases '+months[month-1]+' '+day,zh:month+'月'+day+'日发布'};
    }
    function _rrCountdownLabels(days){
      var n = Number(days);
      if (!isFinite(n)) return null;
      if (n === 0) return {en:'Releases today',zh:'今日发布'};
      if (n === 1) return {en:'Releases tomorrow',zh:'明日发布'};
      if (n > 1) return {en:n+' days away',zh:n+'天后'};
      return {en:Math.abs(n)+' days since release',zh:'已发布'+Math.abs(n)+'天'};
    }
    function _rrMetaChip(labels, primary, prefix){
      if (!labels || (!labels.en && !labels.zh)) return '';
      return '<span class="rr-meta-chip'+(primary?' rr-meta-chip-primary':'')+'">'
        +(prefix||'')
        +'<span class="l-en">'+esc(labels.en||labels.zh||'')+'</span>'
        +'<span class="l-zh">'+esc(labels.zh||labels.en||'')+'</span>'
        +'</span>';
    }

    function openModal(item){
      if (!RR_OVERLAY || !RR_MODAL_INNER) return;
      var rel = item.release || '';
      var rt = item.release_type || '';
      var proj = item.projection || {};
      var isClaims = rel.toLowerCase() === 'claims';
      var isNfp = rel.toLowerCase() === 'nfp';
      var isBenchmarkOnly = proj.mode === 'benchmark_only';
      var pit = item.pit || {};
      var isRetail = rel.toLowerCase() === 'retail';
      var isNoData = isRetail && (String(pit.reason||'').indexOf('no_data') !== -1 || (proj.p10==null&&proj.p90==null));

      /* health dot indicator */
      var captureHealth = _captureHealth;
      var hasDue = captureHealth && captureHealth.past_due_unscored && captureHealth.past_due_unscored.length;
      var periodLabels = _rrPeriodLabels(item.period);
      var dateLabels = item.release_date ? _rrDateLabels(item.release_date) : null;
      var countdownLabels = item.days_to != null ? _rrCountdownLabels(item.days_to) : null;
      var cutoff = item.cutoff_label ? String(item.cutoff_label).replace(/-/g,'−') : '';
      var cutoffLabels = cutoff ? {en:'Data through '+cutoff,zh:'数据截至 '+cutoff} : null;
      var titleHTML = '<div class="rr-modal-title">'+relName(rel, rt)+'</div>'
        +'<div class="rr-modal-sub">'
        +_rrMetaChip(periodLabels,true,hasDue?'<span class="rr-health-dot" title="Capture health: past-due score"></span>':'')
        +_rrMetaChip(dateLabels,false,'')
        +_rrMetaChip(countdownLabels,false,'')
        +_rrMetaChip(cutoffLabels,false,'')
        +'</div>';
      if (RR_TITLE_BLOCK) RR_TITLE_BLOCK.innerHTML = titleHTML;

      var tabs = renderModal(item, captureHealth);

      /* define which tabs are visible: null/empty tabs hidden */
      var tabDefs = [
        {id:'t0',en:'Overview',zh:'概览',content:tabs.tab0},
        {id:'t1',en:'Models',zh:'模型',content:tabs.tab1},
        {id:'t2',en:'Components',zh:'组件',content:tabs.tab2,skip:isBenchmarkOnly||isNoData},
        {id:'t3',en:'History',zh:'历史',content:tabs.tab3},
        {id:'t4',en:'Context',zh:'情境',content:tabs.tab4}
      ];
      var visibleTabs = tabDefs.filter(function(t){return !t.skip && t.content;});

      /* build tab strip */
      if (RR_TAB_STRIP){
        RR_TAB_STRIP.innerHTML = visibleTabs.map(function(t,i){
          return '<button class="rr-tab'+(i===0?' active':'')+'" data-tab="'+esc(t.id)+'" role="tab" aria-selected="'+(i===0?'true':'false')+'">'
            +'<span class="l-en">'+esc(t.en)+'</span>'
            +'<span class="l-zh">'+esc(t.zh)+'</span>'
            +'</button>';
        }).join('');
        RR_TAB_STRIP.querySelectorAll('.rr-tab').forEach(function(btn){
          btn.addEventListener('click', function(){
            var tid = btn.getAttribute('data-tab');
            RR_TAB_STRIP.querySelectorAll('.rr-tab').forEach(function(b){
              b.classList.toggle('active', b.getAttribute('data-tab')===tid);
              b.setAttribute('aria-selected', b.getAttribute('data-tab')===tid ? 'true':'false');
            });
            RR_MODAL_INNER.querySelectorAll('.rr-pane').forEach(function(p){
              p.classList.toggle('active', p.getAttribute('data-tab')===tid);
            });
          });
        });
      }

      /* build panes */
      RR_MODAL_INNER.innerHTML = visibleTabs.map(function(t,i){
        return '<div class="rr-pane'+(i===0?' active':'')+'" data-tab="'+esc(t.id)+'">'+t.content+'</div>';
      }).join('');

      RR_OVERLAY.classList.add('open');
      document.body.style.overflow = 'hidden';
      var lang = (document.documentElement.getAttribute('data-lang') || 'en');
      RR_OVERLAY.setAttribute('data-lang', lang);
      /* INT-03: save invoker, set tabindex, focus dialog */
      _rrModalInvoker = document.activeElement || null;
      var modal = document.getElementById('rr-modal-body');
      if(modal){ if(!modal.hasAttribute('tabindex')) modal.setAttribute('tabindex','-1'); modal.focus(); }
    }

    function closeModal(){
      if (!RR_OVERLAY) return;
      RR_OVERLAY.classList.remove('open');
      document.body.style.overflow = '';
      /* INT-03: restore invoker focus */
      try{ if(_rrModalInvoker && _rrModalInvoker.focus) _rrModalInvoker.focus(); }catch(e){}
      _rrModalInvoker = null;
    }

    /* INT-03: Tab trap within the modal */
    if (RR_OVERLAY) RR_OVERLAY.addEventListener('keydown', function(e){
      if(e.key !== 'Tab') return;
      var modal = document.getElementById('rr-modal-body'); if(!modal) return;
      var focusable = Array.prototype.slice.call(modal.querySelectorAll(
        'button:not([disabled]),a[href],[tabindex]:not([tabindex="-1"]),input:not([disabled]),select:not([disabled]),textarea:not([disabled])'
      )).filter(function(el){ return el.offsetParent !== null; });
      if(!focusable.length) return;
      var first = focusable[0], last = focusable[focusable.length-1];
      if(e.shiftKey){ if(document.activeElement===first){ e.preventDefault(); last.focus(); } }
      else { if(document.activeElement===last){ e.preventDefault(); first.focus(); } }
    });

    if (RR_MODAL_CLOSE) RR_MODAL_CLOSE.addEventListener('click', closeModal);
    if (RR_OVERLAY) RR_OVERLAY.addEventListener('click', function(e){ if (e.target === RR_OVERLAY) closeModal(); });

    /* ---- Inline Release Radar panel (folds the retired rr-date-overlay into
       dlg-events). The THIS WEEK calendar cards are the selector; #rr-inline shows
       the selected date's model prints on the same surface. A print card still
       opens the 5-tab #rr-modal for depth. */
    var RR_MOS_EN = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    function _itemsForDate(dateStr){
      return (_rrItems || []).filter(function(it){ return it.release_date === dateStr; });
    }
    /* an item carries a real modelled point (not benchmark-only, not no-data retail).
       Module-scoped so both renderRadar's see-more logic and the inline default
       selector share one definition. */
    function _hasModelledPoint(it){
      var proj = it.projection || {};
      return proj.mode !== 'benchmark_only' && proj.point !== null && proj.point !== undefined
             && (it.release||'').toLowerCase() !== 'retail';
    }
    /* nearest upcoming date whose prints carry a real modelled point; else the
       nearest covered date; else null. Mirrors renderRadar's default-visible guard. */
    function _defaultCoveredDate(){
      var dates = [];
      (_rrItems||[]).forEach(function(it){
        if (it.release_date && dates.indexOf(it.release_date) === -1) dates.push(it.release_date);
      });
      dates.sort();
      for (var i=0;i<dates.length;i++){
        if (_itemsForDate(dates[i]).some(_hasModelledPoint)) return dates[i];
      }
      return dates[0] || null;
    }
    /* Honest empty state for a calendar date with no model coverage. */
    function _inlineEmptyHTML(card){
      var timeEl = card ? card.querySelector('.mx5-dlg-cal-time') : null;
      var badgeEl = card ? card.querySelector('.mx5-dlg-cal-badge') : null;
      var timeTxt = timeEl ? timeEl.textContent.trim() : '';
      var impactHTML = badgeEl ? badgeEl.outerHTML : '';
      var metaBits = '';
      if (timeTxt) metaBits += '<span>'+esc(timeTxt)+'</span>';
      if (impactHTML) metaBits += impactHTML;
      return '<div class="rr-inline-empty">'
        +'<div class="rr-inline-empty-line">'
        +'<span class="l-en">No model projections for this date — event risk only.</span>'
        +'<span class="l-zh">该日期无模型预测 — 仅为事件风险提示。</span>'
        +'</div>'
        +(metaBits ? '<div class="rr-inline-empty-meta">'+metaBits+'</div>' : '')
        +'</div>';
    }
    function _setInlineHeader(dateStr, covered){
      var el = _rrInlineDateEl();
      if (!el) return;
      if (!dateStr){ el.innerHTML =
        '<span class="l-en">Upcoming prints</span><span class="l-zh">即将公布</span>'; return; }
      var mo = parseInt(dateStr.slice(5,7),10), dy = parseInt(dateStr.slice(8,10),10);
      var sub = document.getElementById('rr-inline-sub');
      if (sub) sub.innerHTML = covered
        ? '<span class="l-en">our projection vs benchmarks</span><span class="l-zh">本方预测 vs 基准</span>'
        : '<span class="l-en">event risk only</span><span class="l-zh">仅为事件风险提示</span>';
      var dot = covered ? '<span class="mx5-dlg-cal-dot" aria-hidden="true"></span>' : '';
      el.innerHTML = dot
        +'<span class="l-en">'+esc(RR_MOS_EN[mo]||'')+' '+dy+'</span>'
        +'<span class="l-zh">'+mo+'月'+dy+'日</span>';
    }
    function _inlineItemsSignature(dateStr, items){
      try{ return dateStr+'|'+JSON.stringify(items || []); }
      catch(e){ return dateStr+'|'+String((items || []).length); }
    }
    function _syncInlineDateSelection(dateStr){
      document.querySelectorAll('#dlg-events .mx5-dlg-cal-card.rr-select').forEach(function(card){
        var active = card.getAttribute('data-cal-date') === dateStr;
        card.classList.toggle('rr-active', active);
        card.setAttribute('aria-pressed', active ? 'true' : 'false');
        if (active) card.setAttribute('aria-current','date');
        else card.removeAttribute('aria-current');
      });
    }
    /* Select a calendar date into the inline panel. Covered → print cards (reuse
       renderCard + openModal); non-covered → honest empty state. Short cross-fade,
       reduced-motion-guarded. Focus is restored to the source card, never a popup. */
    function selectInlineDate(dateStr, sourceCard, immediate){
      var body = _rrInlineBody();
      if (!body) return;
      var items = _itemsForDate(dateStr);
      var signature = _inlineItemsSignature(dateStr, items);
      var unchanged = _rrInlineDate === dateStr && _rrInlineSignature === signature;
      _rrInlineDate = dateStr;
      _syncInlineDateSelection(dateStr);
      /* GDP → PCE → claims on one date is one selection, not three fake refreshes.
         The payload signature still allows a future intraday forecast refresh. */
      if (!immediate && unchanged) return;
      var covered = items.length > 0;
      var bodyHTML;
      if (covered){
        bodyHTML = '<div class="rr-grid">'+items.map(renderCard).join('')+'</div>';
      } else {
        bodyHTML = _inlineEmptyHTML(sourceCard);
      }
      var swap = !immediate && !_prefReducedRR();
      var token = ++_rrInlineSwapToken;
      if (_rrInlineSwapTimer !== null){
        clearTimeout(_rrInlineSwapTimer);
        _rrInlineSwapTimer = null;
      }
      var paint = function(){
        if (token !== _rrInlineSwapToken) return;
        body.innerHTML = bodyHTML;
        _rrInlineSignature = signature;
        _setInlineHeader(dateStr, covered);
        if (covered){
          body.querySelectorAll('.rr-card').forEach(function(el, idx){
            el.setAttribute('role','button');
            el.setAttribute('tabindex','0');
            el.setAttribute('aria-haspopup','dialog');
            /* focus the card before opening so openModal captures it as the invoker —
               on close, focus returns to this inline card (not a dead popup). */
            function go(){ if (items[idx]){ try{ el.focus(); }catch(e){} openModal(items[idx]); } }
            el.addEventListener('click', go);
            el.addEventListener('keydown', function(e){ if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); go(); } });
          });
        }
        /* reveal: rAF for a smooth fade, plus a setTimeout fallback so the panel is
           never left invisible if rAF stalls (e.g. background tab / preview). */
        if (swap){
          var reveal = function(){ body.classList.remove('rr-inline-swap'); };
          if (typeof requestAnimationFrame === 'function') requestAnimationFrame(reveal);
          setTimeout(reveal, 40);
        }
      };
      if (swap){
        body.classList.add('rr-inline-swap');
        _rrInlineSwapTimer = setTimeout(function(){
          _rrInlineSwapTimer = null;
          paint();
        }, 130);
      } else {
        paint();
      }
    }
    function _prefReducedRR(){
      try{ return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches; }
      catch(e){ return false; }
    }

    /* Wire every dlg-events calendar card as a radar selector. FOMC cards route to
       the Fed Path board instead (chip affordance); covered dates get a radar dot;
       all others select and show the honest empty state. Auto-selects the default
       covered date on first wire so the panel is never empty on open. */
    function wireCalendarCards(){
      var cards = document.querySelectorAll('#dlg-events .mx5-dlg-cal-card[data-cal-date]');
      var firstSelect = null;
      cards.forEach(function(card){
        if (card._rrWired) return;
        card._rrWired = true;
        var dateStr = card.getAttribute('data-cal-date');
        var calType = (card.getAttribute('data-cal-type') || '').toUpperCase();
        /* FOMC (policy rate decision) → Fed Path Forward Board, not inline radar. */
        if (calType === 'FOMC'){
          card.classList.add('rr-fed');
          card.setAttribute('role','button');
          card.setAttribute('tabindex','0');
          card.setAttribute('aria-haspopup','dialog');
          var fedChip = document.createElement('div');
          fedChip.className = 'mx5-dlg-cal-fed';
          fedChip.innerHTML = '<span class="l-en">Fed Path &#8594;</span><span class="l-zh">联储路径 &#8594;</span>';
          card.appendChild(fedChip);
          var goFed = function(){ if (window.mx5OpenDlg) window.mx5OpenDlg('dlg-fed'); };
          card.addEventListener('click', goFed);
          card.addEventListener('keydown', function(e){ if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); goFed(); } });
          return;
        }
        /* selectable card */
        card.classList.add('rr-select');
        card.setAttribute('role','button');
        card.setAttribute('tabindex','0');
        card.setAttribute('aria-controls','rr-inline-body');
        card.setAttribute('aria-pressed','false');
        var hasCoverage = _itemsForDate(dateStr).length > 0;
        if (hasCoverage){
          var dot = document.createElement('div');
          dot.className = 'mx5-dlg-cal-radar';
          dot.innerHTML = '<span class="mx5-dlg-cal-dot" aria-hidden="true"></span>'
            +'<span class="l-en">Release Radar</span><span class="l-zh">数据发布雷达</span>';
          card.appendChild(dot);
          if (!firstSelect) firstSelect = card;
        }
        card.addEventListener('click', function(){ selectInlineDate(dateStr, card); });
        card.addEventListener('keydown', function(e){
          if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); selectInlineDate(dateStr, card); }
        });
      });
      /* default selection: nearest covered date's own card if visible, else the
         first covered calendar card, else the earliest calendar card. */
      if (!_rrInlineDate){
        var def = _defaultCoveredDate();
        var defCard = def ? document.querySelector('#dlg-events .mx5-dlg-cal-card[data-cal-date="'+def+'"].rr-select') : null;
        if (!defCard) defCard = firstSelect;
        if (!defCard) defCard = document.querySelector('#dlg-events .mx5-dlg-cal-card.rr-select');
        if (defCard){
          selectInlineDate(defCard.getAttribute('data-cal-date'), defCard, true);
        } else if (def && _rrInlineBody()){
          /* radar has data but no calendar card matches (rare) — show default date's cards */
          selectInlineDate(def, null, true);
        }
      }
    }

    /* INT-01: stop propagation so the mx2 Escape handler doesn't also fire when the
       RR detail modal closes. The inline panel lives inside dlg-events, so the
       dialog's own Escape handling covers it — only the detail modal needs a guard. */
    document.addEventListener('keydown', function(e){
      if (e.key !== 'Escape') return;
      if (RR_OVERLAY && RR_OVERLAY.classList.contains('open')){ e.stopImmediatePropagation(); closeModal(); return; }
    });

    /* sync modal lang when language is toggled */
    if (typeof MutationObserver !== 'undefined' && RR_OVERLAY){
      new MutationObserver(function(){
        var lang = document.documentElement.getAttribute('data-lang') || 'en';
        RR_OVERLAY.setAttribute('data-lang', lang);
      }).observe(document.documentElement, {attributes:true, attributeFilter:['data-lang']});
    }

    /* main render */
    function renderRadar(d){
      if (!d || typeof d !== 'object') {
        RR_EL.innerHTML = '<div class="rr-placeholder">'
          +'<span class="l-en">Release Radar data not yet available — nightly producer accruing.</span>'
          +'<span class="l-zh">数据发布雷达暂无数据，夜间生产任务积累中。</span>'
          +'</div>';
        /* Degraded path: no radar data. Calendar cards stay selectable (all show the
           honest empty state); the inline panel shows a graceful no-data line rather
           than a blank hole. _rrItems stays [] so no card gets a coverage dot. */
        _rrItems = [];
        var _ib = _rrInlineBody();
        if (_ib){
          _ib.innerHTML = '<div class="rr-inline-empty">'
            +'<div class="rr-inline-empty-line">'
            +'<span class="l-en">Model projections aren&rsquo;t available right now. Pick a calendar event above for its time and impact.</span>'
            +'<span class="l-zh">暂无模型预测。请点击上方日历事件查看其时间与影响。</span>'
            +'</div></div>';
        }
        wireCalendarCards();
        return;
      }
      _rrItems = Array.isArray(d.upcoming) ? d.upcoming : [];
      _captureHealth = d.capture_health || null;
      var lastScored = Array.isArray(d.last_scored) ? d.last_scored : [];
      var asof = d.asof || '';

      /* ---- directive 4: see-more logic ---- */
      /* Find earliest release_date among items that have a release_date */
      var dates = [];
      _rrItems.forEach(function(it){
        if (it.release_date && dates.indexOf(it.release_date) === -1)
          dates.push(it.release_date);
      });
      dates.sort();
      /* Default-visible = items sharing the EARLIEST upcoming date */
      var visibleDate = dates[0] || null;
      /* Guard: if none of those have a modelled point, also show next date that does
         (_hasModelledPoint is module-scoped — shared with the inline default selector). */
      if (visibleDate){
        var firstHasModel = _rrItems.some(function(it){
          return it.release_date === visibleDate && _hasModelledPoint(it);
        });
        if (!firstHasModel){
          /* find next date with a modelled point */
          var nextModelDate = null;
          for (var di = 1; di < dates.length; di++){
            if (_rrItems.some(function(it){ return it.release_date === dates[di] && _hasModelledPoint(it); })){
              nextModelDate = dates[di];
              break;
            }
          }
          if (nextModelDate) visibleDate = nextModelDate;
        }
      }
      /* Partition items */
      var visibleItems = [];
      var hiddenItems = [];
      _rrItems.forEach(function(it){
        if (!it.release_date || it.release_date === visibleDate)
          visibleItems.push(it);
        else
          hiddenItems.push(it);
      });
      /* Note: retail (no date) always goes in visible per the logic above since its release_date is null */
      /* Actually retail has release_date=null, so it falls into visibleItems above. Move it to hidden. */
      var visibleFinal = [];
      var hiddenFinal = [];
      _rrItems.forEach(function(it, idx){
        var isNoDataCard = (it.release||'').toLowerCase() === 'retail';
        if (isNoDataCard){
          hiddenFinal.push(it);
        } else if (it.release_date === visibleDate){
          visibleFinal.push(it);
        } else {
          hiddenFinal.push(it);
        }
      });

      var cardsHtml;
      if (!_rrItems.length){
        cardsHtml = '<div class="rr-placeholder">'
          +'<span class="l-en">No upcoming releases in the current window.</span>'
          +'<span class="l-zh">当前窗口内无即将发布的数据。</span>'
          +'</div>';
      } else {
        /* map items to cards, tracking global index for click handler */
        var _allOrdered = visibleFinal.concat(hiddenFinal);
        /* rebuild _rrItems in visible-first order so click idx aligns */
        _rrItems = _allOrdered;
        var visCards = visibleFinal.map(renderCard).join('');
        var hidCards = hiddenFinal.map(renderCard).join('');
        var nHidden = hiddenFinal.length;
        var seeMoreHtml = nHidden > 0
          ? '<div class="rr-see-more-wrap">'
            +'<button class="rr-see-more-btn" id="rr-see-more-btn" type="button">'
            +'<span class="l-en">See more ('+nHidden+')</span>'
            +'<span class="l-zh">显示更多（'+nHidden+'）</span>'
            +'</button>'
            +'</div>'
          : '';
        var hiddenWrap = nHidden > 0
          ? '<div class="rr-grid rr-hidden-cards" id="rr-hidden-cards" style="display:none">'+hidCards+'</div>'
            +seeMoreHtml
          : '';
        cardsHtml = '<div class="rr-grid">'+visCards+'</div>'
          +hiddenWrap;
      }

      RR_EL.innerHTML = cardsHtml;
      /* wire up card clicks — index matches _rrItems (visible-first order) */
      var cardEls = RR_EL.querySelectorAll('.rr-card');
      cardEls.forEach(function(el, idx){
        el.addEventListener('click', function(){ if (_rrItems[idx]) openModal(_rrItems[idx]); });
      });
      /* wire see-more toggle */
      var smBtn = document.getElementById('rr-see-more-btn');
      var smWrap = document.getElementById('rr-hidden-cards');
      if (smBtn && smWrap){
        var _smOpen = false;
        smBtn.addEventListener('click', function(){
          _smOpen = !_smOpen;
          smWrap.style.display = _smOpen ? '' : 'none';
          smBtn.innerHTML = _smOpen
            ? '<span class="l-en">See less</span><span class="l-zh">收起</span>'
            : '<span class="l-en">See more ('+hiddenFinal.length+')</span><span class="l-zh">显示更多（'+hiddenFinal.length+'）</span>';
          /* re-sync lang class on button */
          var lang = document.documentElement.getAttribute('data-lang') || 'en';
          smBtn.closest('[data-lang]') || void 0;
        });
      }
      /* MRI-R39a: populate track-record overlay with scoreboardBlock data */
      var RR_TR_BODY = document.getElementById('rr-tr-body');
      if (RR_TR_BODY) {
        RR_TR_BODY.innerHTML = scoreboardBlock(lastScored);
      }
      /* wire dlg-events calendar cards as the inline radar selector + auto-select default */
      wireCalendarCards();
    }

    /* MRI-R39a: track-record overlay open/close */
    var RR_TR_OVERLAY = document.getElementById('rr-tr-overlay');
    var RR_TR_BTN = document.getElementById('rr-tr-btn');
    var RR_TR_CLOSE = document.getElementById('rr-tr-close');
    function openTrackRecord(){
      if (!RR_TR_OVERLAY) return;
      RR_TR_OVERLAY.classList.add('is-open');
      document.body.style.overflow = 'hidden';
    }
    function closeTrackRecord(){
      if (!RR_TR_OVERLAY) return;
      RR_TR_OVERLAY.classList.remove('is-open');
      document.body.style.overflow = '';
    }
    if (RR_TR_BTN) RR_TR_BTN.addEventListener('click', openTrackRecord);
    if (RR_TR_CLOSE) RR_TR_CLOSE.addEventListener('click', closeTrackRecord);
    if (RR_TR_OVERLAY) RR_TR_OVERLAY.addEventListener('click', function(e){
      if (e.target === RR_TR_OVERLAY) closeTrackRecord();
    });

    /* fetch — pattern mirrors sector_central.html.j2:670 */
    fetch('macrodata/release_forecast.json', { cache: 'no-cache' })
      .then(function(r){ return r.ok ? r.json() : null; })
      .catch(function(){ return null; })
      .then(renderRadar);

    /* Deep-link hook: jump the inline Release Radar panel to its default covered date
       (the "Open Release Radar" button was retired — the panel is always visible in
       dlg-events). Kept as the stable RR-script tail symbol. */
    window.mmOpenFirstRR = function(){
      var def = _defaultCoveredDate();
      if (!def) return;
      var card = document.querySelector('#dlg-events .mx5-dlg-cal-card[data-cal-date="'+def+'"].rr-select');
      selectInlineDate(def, card, true);
    };
  })();
