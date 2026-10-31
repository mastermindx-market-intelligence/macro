/* Mastermind Brain financial views v2. Closed source snapshots; no model HTML or data fetching. */
(function (win) {
  'use strict';
  var D = win.document, NS = 'http://www.w3.org/2000/svg';
  var NORMALIZER = 'terminal-statements-38723cef-v1', mathPromise;
  var templates = ['price', 'financial_statement', 'company', 'transcript'];
  function finite(n) { return typeof n === 'number' && Number.isFinite(n) && Math.abs(n) <= 1e15; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x); }
  function text(x) { return x == null ? '' : String(x); }
  function el(tag, cls, value) {
    var n = D.createElement(tag); if (cls) n.className = cls;
    if (value != null) n.textContent = text(value); return n;
  }
  function svg(tag, attrs) {
    var n = D.createElementNS(NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, text(attrs[k])); }); return n;
  }
  function zh(host) {
    var node = host.closest('[data-lang]');
    return /^zh/i.test((node && node.getAttribute('data-lang')) ||
      D.documentElement.getAttribute('data-lang') || D.documentElement.lang || '');
  }
  function tr(c, en, cn) { return c.zh ? cn : en; }
  function add(parent, tag, cls, value) { var n = el(tag, cls, value); parent.appendChild(n); return n; }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function num(n, digits) {
    return finite(n) ? n.toLocaleString(undefined, {maximumFractionDigits: digits == null ? 2 : digits}) : '—';
  }
  function pct(n) { return finite(n) ? (n > 0 ? '+' : '') + num(n, 2) + '%' : '—'; }
  function signed(node, n) {
    if (finite(n)) node.classList.add(n >= 0 ? 'mmb-f-positive' : 'mmb-f-negative');
    return node;
  }
  function note(c, s) { if (s) add(c.body, 'p', 'mmb-f-note', s); }
  function button(parent, label, action, pressed) {
    var b = add(parent, 'button', 'mmb-f-button', label); b.type = 'button';
    if (pressed != null) b.setAttribute('aria-pressed', pressed ? 'true' : 'false');
    b.addEventListener('click', action); return b;
  }
  function select(parent, label, options, selected, onChange) {
    var wrap = add(parent, 'label', 'mmb-f-select');
    add(wrap, 'span', '', label);
    var s = add(wrap, 'select'); s.setAttribute('aria-label', label);
    options.forEach(function (o) { var n = add(s, 'option', '', o[1]); n.value = o[0]; });
    s.value = text(selected);
    s.addEventListener('change', function () { onChange(s.value); }); return s;
  }
  function redraw(c, action) {
    var active = D.activeElement, key = active && active.getAttribute('data-focus-key');
    action(); clear(c.body); renderBody(c);
    if (key) {
      var nodes = c.body.querySelectorAll('[data-focus-key]');
      for (var i = 0; i < nodes.length; i++) if (nodes[i].getAttribute('data-focus-key') === key) { nodes[i].focus(); break; }
    }
  }
  function controls(c, choices, stateKey, title) {
    var row = add(c.body, 'div', 'mmb-f-controls'); row.setAttribute('role', 'group');
    row.setAttribute('aria-label', title);
    choices.forEach(function (choice) {
      var b = button(row, choice[1], function () { redraw(c, function () { c.state[stateKey] = choice[0]; }); },
        c.state[stateKey] === choice[0]);
      b.setAttribute('data-focus-key', stateKey + ':' + choice[0]); if (choice[2]) b.disabled = true;
    }); return row;
  }
  function csvCell(value) {
    if (finite(value)) return '"' + String(value) + '"';
    var s = value == null ? '' : String(value);
    if (/^[\s\u0000-\u001f]*[=+\-@]/.test(s)) s = "'" + s;
    return '"' + s.replace(/"/g, '""') + '"';
  }
  function download(c, rows) {
    var data = rows.map(function (r) { return r.map(csvCell).join(','); }).join('\r\n');
    var blob = new win.Blob(['\ufeff', data], {type: 'text/csv;charset=utf-8'});
    var url = win.URL.createObjectURL(blob), a = el('a');
    a.href = url; a.download = c.v.source.entity_id + '-' + c.v.template + '.csv';
    D.body.appendChild(a); a.click(); a.remove(); win.setTimeout(function () { win.URL.revokeObjectURL(url); }, 1000);
  }
  function exportButton(c, rows, label) {
    var actions = add(c.body, 'div', 'mmb-f-actions');
    button(actions, label || tr(c, 'Download displayed data', '下载当前数据'), function () { download(c, rows); });
  }
  function validate(wire) {
    try {
      if (!obj(wire) || wire.type !== 'chart' || !/^[a-f0-9]{24}$/.test(wire.visual_id) ||
          JSON.stringify(wire).length > 131072) return false;
      var v = wire.visual, s = v && v.source;
      if (!obj(v) || v.version !== 2 || templates.indexOf(v.template) < 0 || !obj(v.data) || !obj(v.view) ||
          !obj(s) || !/^[a-f0-9]{64}$/.test(s.snapshot_id) || !/^[A-Z0-9.^=_-]{1,24}$/.test(s.entity_id)) return false;
      var safe = true;
      function walk(x, depth) {
        if (depth > 12) { safe = false; return; }
        if (typeof x === 'number' && !finite(x)) safe = false;
        if (typeof x === 'string' && (x.length > 4000 || /<\s*[\/!a-z]|[\u0000-\u0008\u000b\u000c\u000e-\u001f\u202a-\u202e\u2066-\u2069]/i.test(x))) safe = false;
        if (Array.isArray(x)) { if (x.length > 600) safe = false; x.forEach(function (a) { walk(a, depth + 1); }); }
        else if (obj(x)) Object.keys(x).forEach(function (k) { if (k === '__proto__' || k === 'constructor') safe = false; walk(x[k], depth + 1); });
      }
      walk(v, 0);
      if (!safe) return false;
      if (v.template === 'financial_statement') {
        var f = v.data.fund;
        return v.normalizer_version === NORMALIZER && obj(f) && f.schema === 'mastermind.fund/v1' &&
          f.ticker === s.entity_id && obj(f.statements) &&
          ['annual', 'quarterly'].every(function (k) {
            var p = f.statements[k];
            return p == null || (obj(p) && Array.isArray(p.periods) && p.periods.length <= 160 &&
              ['income', 'balance', 'cashflow'].every(function (block) {
                return obj(p[block]) && Object.keys(p[block]).every(function (key) {
                  var a = p[block][key]; return Array.isArray(a) && a.length <= p.periods.length &&
                    a.every(function (n) { return n == null || finite(n); });
                });
              }));
          });
      }
      if (v.normalizer_version !== null || v.data.symbol !== s.entity_id) return false;
      if (v.template === 'price') {
        var q = v.data.quote, previous = '';
        return obj(q) && finite(q.price) && q.price > 0 && Array.isArray(v.data.bars) &&
          v.data.bars.every(function (b) {
            var valid = obj(b) && /^\d{4}-\d{2}-\d{2}$/.test(b.date) &&
              Number.isFinite(Date.parse(b.date + 'T00:00:00Z')) && b.date > previous && finite(b.close) && b.close > 0;
            previous = b.date; return valid;
          });
      }
      if (v.template === 'company') return obj(v.data.profile) && Array.isArray(v.data.metrics) &&
        v.data.metrics.length <= 12 && v.data.metrics.every(function (m) { return obj(m) && finite(m.value); });
      return obj(v.data.event) && Array.isArray(v.data.facts) && v.data.facts.length <= 6 &&
        ((v.data.kind === 'summary' && typeof v.data.summary === 'string' && v.data.facts.length === 0) ||
         (v.data.kind === 'quotes' && s.reader === 'read_earnings_evidence' &&
          v.data.facts.every(function (f) { return obj(f.quote) && typeof f.quote.text === 'string' && obj(f.quote.receipt); })));
    } catch (_) { return false; }
  }
  function loadMath(base) {
    if (win.MMBrainFinanceMath && win.MMBrainFinanceMath.version === NORMALIZER) return Promise.resolve(win.MMBrainFinanceMath);
    if (mathPromise) return mathPromise;
    mathPromise = new Promise(function (resolve, reject) {
      var script = D.createElement('script');
      script.src = new URL('mm_brain_finance_math_v1.js?v=b20772591c20', base || D.baseURI).href;
      script.async = true;
      script.onload = function () {
        if (win.MMBrainFinanceMath && win.MMBrainFinanceMath.version === NORMALIZER) resolve(win.MMBrainFinanceMath);
        else { script.remove(); mathPromise = null; reject(new Error('normalizer_unavailable')); }
      };
      script.onerror = function () { script.remove(); mathPromise = null; reject(new Error('normalizer_unavailable')); };
      D.head.appendChild(script);
    }); return mathPromise;
  }
  function lineChart(c, points, label) {
    var valid = points.filter(function (p) { return finite(p.value); });
    if (valid.length < 2) { note(c, tr(c, 'Not enough qualified observations to chart this range.', '此区间没有足够的有效数据。')); return; }
    var style=win.getComputedStyle(c.body);
    var width=Math.max(240,Math.min(960,c.body.clientWidth-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight)));
    var height=200, left=8, right=width-8, top=20, bottom=166;
    var low = Math.min.apply(null, valid.map(function (p) { return p.value; }));
    var high = Math.max.apply(null, valid.map(function (p) { return p.value; }));
    var pad = (high - low) * 0.1 || Math.abs(high) * 0.01 || 1; low -= pad; high += pad;
    var dates = points.map(function (p) { return Date.parse(p.date + 'T00:00:00Z'); });
    var dated = dates.every(Number.isFinite), first = dated ? dates[0] : 0, last = dated ? dates[dates.length - 1] : points.length - 1;
    var chart = svg('svg', {viewBox: '0 0 ' + width + ' ' + height, role: 'img', 'aria-label': label, class: 'mmb-f-chart'});
    var title = svg('title'); title.textContent = label; chart.appendChild(title);
    var y = function (value) { return bottom - (value - low) / (high - low) * (bottom - top); };
    for (var g = 0; g < 3; g++) {
      var val = low + (high - low) * g / 2, yy = y(val);
      chart.appendChild(svg('line', {x1: left, x2: right, y1: yy, y2: yy, class: 'mmb-f-grid'}));
      var tick = svg('text', {x: right, y: yy - 4, 'text-anchor': 'end', class: 'mmb-f-axis'}); tick.textContent = num(val, 2); chart.appendChild(tick);
    }
    var path = '', open = false;
    points.forEach(function (p, i) {
      if (!finite(p.value)) { open = false; return; }
      var x = left + ((dated ? dates[i] : i) - first) / Math.max(1, last - first) * (right - left);
      path += (open ? ' L' : ' M') + x.toFixed(2) + ',' + y(p.value).toFixed(2); open = true;
    });
    chart.appendChild(svg('path', {d: path, class: 'mmb-f-line', fill: 'none'}));
    [0, points.length - 1].forEach(function (i) {
      var axis = svg('text', {x: i ? right : left, y: 191, 'text-anchor': i ? 'end' : 'start', class: 'mmb-f-axis'});
      axis.textContent = points[i].label || points[i].date; chart.appendChild(axis);
    });
    c.body.appendChild(chart);
  }
  function cutoffFor(range, end) {
    var d = new Date(end + 'T00:00:00Z'), day = d.getUTCDate();
    if (range === 'MAX') return '';
    if (range === 'YTD') return d.getUTCFullYear() + '-01-01';
    var months = {'1M': 1, '3M': 3, '6M': 6, '1Y': 12}[range];
    if (!months) return '';
    d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() - months);
    var maxDay = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
    d.setUTCDate(Math.min(day, maxDay)); return d.toISOString().slice(0, 10);
  }
  function rangeBars(bars, range, anchor) {
    if (!bars.length) return [];
    var end = /^\d{4}-\d{2}-\d{2}$/.test(anchor || '') && Number.isFinite(Date.parse(anchor)) ? anchor : bars[bars.length - 1].date;
    var cutoff = cutoffFor(range, end);
    return bars.filter(function (b) { return !cutoff || b.date >= cutoff; });
  }
  function table(parent, caption, headers, rows) {
    var wrap = add(parent, 'div', 'mmb-f-table-wrap'); wrap.tabIndex = 0; wrap.setAttribute('aria-label', caption);
    var tab = add(wrap, 'table', 'mmb-f-table'); add(tab, 'caption', '', caption);
    var head = add(add(tab, 'thead'), 'tr');
    headers.forEach(function (s) { var th = add(head, 'th', '', s); th.scope = 'col'; });
    var body = add(tab, 'tbody');
    rows.forEach(function (r) {
      var row = add(body, 'tr');
      r.forEach(function (s, i) { var cell = add(row, i ? 'td' : 'th', '', s); if (!i) cell.scope = 'row'; });
    }); return wrap;
  }
  function renderPrice(c) {
    var data = c.v.data, q = data.quote, bars = rangeBars(data.bars, c.state.range, (q.as_of || '').slice(0,10));
    var hero = add(c.body, 'div', 'mmb-f-price-hero');
    add(hero, 'strong', 'mmb-f-price', num(q.price, 4));
    if (data.currency) add(hero, 'span', 'mmb-f-unit', data.currency);
    signed(add(hero, 'span', 'mmb-f-change', pct(q.change_pct)), q.change_pct);
    add(c.body, 'p', 'mmb-f-note', tr(c, 'Change vs previous close', '较前收盘变动') +
      (q.delayed_min != null ? ' · ' + q.delayed_min + tr(c, ' min delayed', ' 分钟延迟') : '') +
      (q.live === true ? ' · ' + tr(c, 'Live quote', '实时报价') : ''));
    controls(c, ['1M','3M','6M','YTD','1Y','MAX'].map(function (r) {
      return [r, r === 'MAX' ? tr(c, 'All available', '全部可用') : r, !data.bars.length];
    }), 'range', tr(c, 'Price history range', '价格历史区间'));
    if (bars.length) {
      var change = bars.length > 1 ? (bars[bars.length - 1].close / bars[0].close - 1) * 100 : null;
      signed(add(c.body, 'p', 'mmb-f-range-return', pct(change) + ' · ' + tr(c, 'displayed close-to-close return', '当前区间收盘价回报')), change);
      lineChart(c, bars.map(function (b) { return {date: b.date, value: b.close}; }), tr(c, 'Daily closing prices', '每日收盘价'));
      note(c, tr(c, 'Daily closes through ', '每日收盘价截至 ') + bars[bars.length - 1].date +
        ' · ' + tr(c, 'Available history starts ', '可用历史开始于 ') + data.bars[0].date);
      var detail = add(c.body, 'details', 'mmb-f-details'); add(detail, 'summary', '', tr(c, 'View chart data', '查看图表数据'));
      var rows = bars.map(function (b) { return [b.date, num(b.close, 6)]; });
      table(detail, tr(c, 'Displayed daily closes', '当前区间每日收盘价'), [tr(c, 'Date', '日期'), tr(c, 'Close', '收盘价')], rows);
      exportButton(c, [['Symbol', data.symbol], ['Source', q.source], ['Snapshot as of', c.v.source.asof],
        ['Daily close history through', data.history_asof], ['Date', 'Close', 'Currency']].concat(bars.map(function (b) { return [b.date, b.close, data.currency]; })));
    } else note(c, tr(c, 'The quote is available. Qualified daily history is unavailable in this snapshot.', '此快照有报价，但没有合格的每日历史数据。'));
  }
  var LABELS = {
    revenue:['Revenue','营业收入'], cogs:['Cost of revenue','营业成本'], gross_profit:['Gross profit','毛利'],
    opex:['Operating expenses','营业费用'], op_income:['Operating income','营业利润'],
    nonop_income:['Non-operating income','营业外收入'], pretax_income:['Pretax income','税前利润'],
    taxes:['Income tax','所得税'], net_income:['Net income','净利润'], eps_basic:['EPS, basic','基本每股收益'],
    eps_diluted:['EPS, diluted','稀释每股收益'], ebitda:['EBITDA','EBITDA'],
    assets:['Total assets','总资产'], assets_st:['Current assets','流动资产'], assets_lt:['Non-current assets','非流动资产'],
    liabilities:['Total liabilities','总负债'], liab_st:['Current liabilities','流动负债'], liab_lt:['Non-current liabilities','非流动负债'],
    equity:['Total equity','总权益'], debt:['Total debt','总债务'], cash:['Cash & equivalents','现金及等价物'], net_debt:['Net debt','净债务'],
    cfo:['Operating cash flow','经营现金流'], cfi:['Investing cash flow','投资现金流'], cff:['Financing cash flow','融资现金流'],
    capex:['Capital expenditure','资本支出'], fcf:['Free cash flow','自由现金流']
  };
  var ROWS = {income:['revenue','cogs','gross_profit','opex','op_income','nonop_income','pretax_income','taxes','net_income','eps_basic','eps_diluted','ebitda'],
    balance:['assets','assets_st','assets_lt','liabilities','liab_st','liab_lt','equity','debt','cash','net_debt'],
    cashflow:['cfo','cfi','cff','capex','fcf']};
  function statementModel(fund, math, basis, block) {
    var set = fund.statements[basis], view = math.incomeView(fund.ticker, set, basis);
    var values = block === 'income' ? view.income : (set && set[block]) || {};
    var keys = ROWS[block].filter(function (key) {
      return block !== 'income' || math.isIndustrialIncomeView(view) || ['cogs','gross_profit','ebitda'].indexOf(key) < 0;
    });
    return {set: set, view: view, keys: keys, values: values,
      valuesFor: function (key) { return block === 'income' && key === 'opex' ? view.operatingExpenses : values[key] || []; }};
  }
  function rowLabel(c, model, key) {
    if (c.state.statement === 'income' && key === 'revenue') return c.math.incomeViewTopLineLabel(model.view, c.zh);
    if (c.state.statement === 'income' && key === 'opex') return c.math.incomeViewOperatingExpenseLabel(model.view, c.zh);
    return LABELS[key][c.zh ? 1 : 0];
  }
  function renderStatement(c) {
    if (!c.math) { note(c, tr(c, 'Loading financial statement presentation…', '正在加载财务报表…')); return; }
    var f = c.fund, m = c.math;
    var annual = m.statementBasisAvailable(f.statements.annual), interim = m.statementBasisAvailable(f.statements.quarterly);
    c.state.basis = m.resolveStatementBasis(c.state.basis, annual, interim);
    controls(c, [['income',tr(c,'Income statement','利润表')],['balance',tr(c,'Balance sheet','资产负债表')],['cashflow',tr(c,'Cash flow','现金流量表')]], 'statement', tr(c,'Statement','报表'));
    controls(c, [['annual',tr(c,'Annual','年度'),!annual],['quarterly',m.statementCadenceLabel(f.statements.quarterly,'quarterly',c.zh),!interim]], 'basis', tr(c,'Reporting basis','报告周期'));
    var model = statementModel(f, m, c.state.basis, c.state.statement), set = model.set;
    if (!set || !set.periods.length) { note(c, tr(c,'This reporting basis is unavailable.','此报告周期暂无数据。')); return; }
    var total = set.periods.length, count = Math.min(c.v.view.period_count || 4, total);
    var latest = c.state.period != null && c.state.period < total ? c.state.period : total - 1;
    var start = Math.max(0, latest + 1 - count), indexes = [];
    for (var i = start; i <= latest; i++) indexes.push(i);
    var currency = f.stmt_currency || tr(c, 'currency not supplied', '币种未提供');
    note(c, currency + ' · ' + tr(c, 'Millions, except per-share figures', '百万，每股数据除外') +
      ' · ' + m.statementPeriodCountLabel(set, c.state.basis, c.zh));
    var toolbar = add(c.body,'div','mmb-f-statement-toolbar');
    var period = select(toolbar, tr(c,'Through period','截至期间'),
      set.periods.map(function (p, ix) { return [ix,p]; }).reverse(), latest,
      function (value) { redraw(c,function(){c.state.period=Number(value);}); });
    period.setAttribute('data-focus-key','period');
    var expand = button(toolbar, tr(c,'Enlarge / full table','展开完整表格'), function () {
      redraw(c,function(){c.state.fullTable=!c.state.fullTable;});
      if (c.options.onExpand) c.options.onExpand();
    }, c.state.fullTable);
    expand.setAttribute('data-focus-key','expand');
    var labelKeys = model.keys, fullRows = labelKeys.map(function (key) {
      var vals = model.valuesFor(key), perShare = /^eps_/.test(key);
      return [rowLabel(c,model,key)].concat(indexes.map(function (ix) { return num(finite(vals[ix]) ? vals[ix]/(perShare?1:1e6) : null,2); }));
    });
    var tableWrap = table(c.body, tr(c,'Financial statement · ','财务报表 · ') + currency +
      tr(c,' · millions except EPS',' · 百万，每股收益除外'),
      [tr(c,'Line item','项目')].concat(indexes.map(function (ix) { return set.periods[ix]; })), fullRows);
    tableWrap.classList.add('mmb-f-statement-table');
    if (c.state.fullTable) tableWrap.classList.add('mmb-f-table-expanded');
    var compact = add(c.body,'dl','mmb-f-period-detail');
    if (c.state.fullTable) compact.classList.add('mmb-f-detail-hidden');
    var priority = c.state.statement === 'income' ? ['revenue','op_income','net_income','eps_basic','eps_diluted'] :
      c.state.statement === 'balance' ? ['assets','liabilities','equity','cash','debt'] : labelKeys;
    var detailKeys = c.state.detailAll ? labelKeys : labelKeys.filter(function(k){return priority.indexOf(k)>=0;});
    detailKeys.forEach(function (key) {
      var vals=model.valuesFor(key), previous=m.priorComparableIndex(set,latest,c.state.basis), changes=m.comparablePeriodChanges(vals,set,c.state.basis);
      var row=add(compact,'div','mmb-f-detail-row');
      add(row,'dt','',rowLabel(c,model,key));
      var dd=add(row,'dd');
      add(dd,'strong','',num(finite(vals[latest])?vals[latest]/(/^eps_/.test(key)?1:1e6):null,2));
      var comparison=previous==null?tr(c,'No comparable prior period','无可比上期'):
        set.periods[previous]+' '+num(finite(vals[previous])?vals[previous]/(/^eps_/.test(key)?1:1e6):null,2)+' · '+pct(changes[latest]);
      add(dd,'small','mmb-f-comparison',comparison);
    });
    if (labelKeys.length > detailKeys.length || c.state.detailAll) {
      var more = button(c.body, c.state.detailAll ? tr(c,'Show key line items','显示关键项目') : tr(c,'Show all line items','显示全部项目'), function(){redraw(c,function(){c.state.detailAll=!c.state.detailAll;});}, c.state.detailAll);
      more.classList.add('mmb-f-detail-toggle'); more.setAttribute('data-focus-key','detail-toggle');
      if(c.state.fullTable)more.hidden=true;
    }
    var selectedMeta = [];
    if (set.filed_by_period && set.filed_by_period[latest]) selectedMeta.push(tr(c,'Filed ','披露于 ')+set.filed_by_period[latest]);
    if (set.restated_by_period && set.restated_by_period[latest]) selectedMeta.push(tr(c,'Restated source','来源已重述'));
    if (set.src_by_period && set.src_by_period[latest]) selectedMeta.push(tr(c,'Source ','来源 ')+set.src_by_period[latest]);
    if (selectedMeta.length) note(c,set.periods[latest]+' · '+selectedMeta.join(' · '));
    if (c.state.statement==='income') {
      note(c,m.cumulativeQuarterNote(model.view,c.zh)); note(c,m.incomeViewFamilyDisclosure(model.view,c.zh));
    } else if (c.state.statement==='cashflow') note(c,tr(c,'Cash flows retain the source reporting basis; no income-statement differencing is applied.','现金流保留来源报告口径，不应用利润表差分。'));
    var gap=m.vendorGapNotice(set,c.state.statement,c.zh);
    if(gap) note(c,tr(c,'Historical source gaps: ','历史来源缺项：')+gap.rows.join(', ')+
      (gap.fullFrom?tr(c,' · full rows from ',' · 完整项目自 ')+gap.fullFrom:''));
    var chartKeys=labelKeys.filter(function(k){return model.valuesFor(k).some(finite);});
    if(chartKeys.length) {
      var key=chartKeys.indexOf(c.state.metric)>=0?c.state.metric:chartKeys[0];
      var chartControl=add(c.body,'div','mmb-f-chart-control');
      var selector=select(chartControl,tr(c,'Chart metric','图表指标'),chartKeys.map(function(k){return[k,rowLabel(c,model,k)];}),key,
        function(value){redraw(c,function(){c.state.metric=value;});});
      selector.setAttribute('data-focus-key','metric');
      var vals=model.valuesFor(key), divisor=/^eps_/.test(key)?1:1e6;
      lineChart(c,indexes.map(function(ix){return{date:'',label:set.periods[ix],value:finite(vals[ix])?vals[ix]/divisor:null};}),
        rowLabel(c,model,key)+' · '+currency+(divisor===1?'':tr(c,' millions',' 百万')));
    }
    var exportRows=[['Symbol',f.ticker],['Statement',c.state.statement],['Basis',c.state.basis],['Currency',f.stmt_currency],
      ['Units','Unscaled source currency; EPS per share'],['Snapshot as of',f.asof],['Snapshot',c.v.source.snapshot_id],
      ['Normalizer',NORMALIZER],['Line item'].concat(set.periods)];
    labelKeys.forEach(function(key){var values=model.valuesFor(key);exportRows.push([rowLabel(c,model,key)].concat(set.periods.map(function(_,ix){return values[ix] == null ? null:values[ix];})));});
    exportButton(c,exportRows,tr(c,'Download statement snapshot','下载报表快照'));
  }
  function renderCompany(c) {
    var data=c.v.data,p=data.profile;
    add(c.body,'h4','mmb-f-company-name',p.name||data.symbol);
    if(p.sector)add(c.body,'p','mmb-f-sector',p.sector);
    if(p.description)add(c.body,'p','mmb-f-description',p.description);
    var grid=add(c.body,'dl','mmb-f-metrics');
    var labels={market_cap:['Market cap','市值'],trailing_pe:['Trailing P/E','市盈率（TTM）'],forward_pe:['Forward P/E','预期市盈率'],price_to_book:['Price / book','市净率'],price_to_sales:['Price / sales','市销率']};
    data.metrics.forEach(function(m){
      var cell=add(grid,'div');add(cell,'dt','',(labels[m.key]||[m.label,m.label])[c.zh?1:0]);
      add(cell,'dd','',num(m.value,2)+(m.unit?' '+m.unit:''));
    });
    if(data.metrics.some(function(m){return m.unit==='bn';})) note(c,tr(c,'Market cap is in billions in the source currency; currency is not supplied in this snapshot.','市值以来源币种的十亿为单位；此快照未提供币种。'));
    if(!data.metrics.length)note(c,tr(c,'Valuation metrics are unavailable in this snapshot.','此快照未提供估值指标。'));
    exportButton(c,[['Symbol',data.symbol],['Company',p.name],['Sector',p.sector],['Metric','Value','Unit','As of']]
      .concat(data.metrics.map(function(m){return[m.label,m.value,m.unit,m.asof];})));
  }
  function renderTranscript(c) {
    var data=c.v.data,event=data.event;
    add(c.body,'p','mmb-f-sector',[event.period,event.date].filter(Boolean).join(' · '));
    if(data.kind==='summary') {
      add(c.body,'span','mmb-f-badge',tr(c,'AI-assisted call summary','AI 辅助电话会摘要'));
      add(c.body,'p','mmb-f-description',data.summary);
      if(data.source_url) {
        try { var url=new URL(data.source_url);if(url.protocol==='https:'&&!url.username&&!url.password){
          var link=add(c.body,'a','mmb-f-source-link',tr(c,'View source','查看来源'));link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';
        }}catch(_){}
      }
    } else {
      add(c.body,'span','mmb-f-badge',tr(c,'Source excerpts','原文摘录'));
      if(!data.facts.length)note(c,tr(c,'No qualified excerpt is available.','暂无合格摘录。'));
      var roles={executive:['Executive','管理层'],analyst:['Analyst','分析师'],operator:['Operator','主持人']};
      var chapters={prepared:['Prepared remarks','预备发言'],q_and_a:['Q&A','问答']};
      function caption(value,labels){return Object.prototype.hasOwnProperty.call(labels,value)?labels[value][c.zh?1:0]:value;}
      data.facts.forEach(function(f){
        var block=add(c.body,'figure','mmb-f-excerpt');
        add(block,'blockquote','',f.quote.text);
        add(block,'figcaption','',[f.speaker,caption(f.role,roles),caption(f.chapter,chapters)].filter(Boolean).join(' · '));
      });
      if(data.correction_status) note(c,tr(c,'Source status: ','来源状态：')+data.correction_status);
    }
  }
  function renderBody(c) {
    c.zh=zh(c.root);
    if(c.v.template==='price')renderPrice(c);
    else if(c.v.template==='financial_statement')renderStatement(c);
    else if(c.v.template==='company')renderCompany(c);
    else renderTranscript(c);
  }
  function mount(host,wire,options) {
    if(!host||!validate(wire))return null;
    var existing=host.querySelector('[data-visual-id="'+wire.visual_id+'"]');if(existing)return existing;
    var v=wire.visual,root=add(host,'section','mmb-f-card');root.dataset.visualId=wire.visual_id;
    root.setAttribute('aria-label',v.title);root.dataset.snapshotId=v.source.snapshot_id;
    var c={root:root,v:v,options:options||{},zh:zh(host),state:{
      range:v.view.range||'1Y',statement:v.view.statement||'income',basis:v.view.basis==='interim'?'quarterly':'annual',
      metric:v.view.metric||null,period:null,fullTable:false,detailAll:false}};
    var header=add(root,'header','mmb-f-header');
    var names={price:['Price & trend','价格与趋势'],financial_statement:['Financial statements','财务报表'],company:['Company brief','公司概况'],transcript:['Earnings call','业绩电话会']};
    var eyebrow=add(header,'span','mmb-f-eyebrow');add(header,'h3','',v.source.entity_id);
    c.body=add(root,'div','mmb-f-body');
    var footer=add(root,'footer','mmb-f-footer');
    var sources=v.template==='financial_statement'?v.data.fund.src:
      v.template==='price'?{statements:v.data.quote.source}:null;
    var source=sources&&[sources.statements,sources.statement_lineage].filter(Boolean).join(' / ');
    var sourceLabel=add(footer,'span'), snapshotLabel=add(footer,'span','mmb-f-snapshot-label');
    function refreshLocale() {
      c.zh=zh(root);eyebrow.textContent=names[v.template][c.zh?1:0];
      root.setAttribute('aria-label',v.source.entity_id+' · '+names[v.template][c.zh?1:0]);
      sourceLabel.textContent=(source||tr(c,'Mastermind source snapshot','Mastermind 来源快照'))+' · '+
        tr(c,'As of ','截至 ')+(v.source.asof||tr(c,'not supplied','未提供'));
      snapshotLabel.textContent=tr(c,'Saved snapshot · controls use this data','已保存快照 · 控件使用此数据');
    }
    function languageChanged(){if(root.isConnected){refreshLocale();redraw(c,function(){});}}
    refreshLocale();renderBody(c);
    D.addEventListener('langchange',languageChanged);win.addEventListener('mm:lang',languageChanged);
    var disposeResize=function(){};
    root._financeDispose=function(){
      disposeResize();D.removeEventListener('langchange',languageChanged);win.removeEventListener('mm:lang',languageChanged);
    };
    if(win.ResizeObserver){
      var lastWidth=root.getBoundingClientRect().width, timer;
      var resize=new win.ResizeObserver(function(){
        var nextWidth=root.getBoundingClientRect().width;
        if(Math.abs(nextWidth-lastWidth)<1)return;lastWidth=nextWidth;
        win.clearTimeout(timer);timer=win.setTimeout(function(){if(root.isConnected)redraw(c,function(){});},90);
      });
      resize.observe(root);disposeResize=function(){resize.disconnect();win.clearTimeout(timer);};
    }
    if(v.template==='financial_statement'){
      loadMath(c.options.assetBase).then(function(math){
        if(!root.isConnected)return;c.math=math;
        c.fund=math.applyLegacyStatementFamilyFallback(JSON.parse(JSON.stringify(v.data.fund)));
        clear(c.body);renderBody(c);
      }).catch(function(){if(root.isConnected){clear(c.body);note(c,tr(c,'Statement presentation is unavailable. Please try the answer again.','报表暂时无法显示，请重试回答。'));}});
    }
    return root;
  }
  win.MMBrainFinance={mount:mount,clear:function(host){if(host)host.querySelectorAll('.mmb-f-card').forEach(function(n){if(n._financeDispose)n._financeDispose();n.remove();});},
    validate:validate,rangeBars:rangeBars,cutoffFor:cutoffFor,statementModel:statementModel,csvCell:csvCell,version:2};
})(window);
