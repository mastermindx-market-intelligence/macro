(function () {
  'use strict';

  // Production state crosses only the authenticated API. Localhost reads the
  // ignored builder artifact so browser QA never needs a live account or bucket.
  var IS_LOOPBACK = /^(localhost|127(?:\.\d{1,3}){3}|\[?::1\]?)$/i.test(window.location.hostname);
  var DATA_URL = IS_LOOPBACK
    ? '/data/fundamental_forensics/private/state.json.gz'
    : '/api/forensics/state';
  var HEALTH_URL = '/api/forensics/health';
  var ATTESTED_HISTORY_URL = '/api/forensics/v1/attested-history';
  var FINANCIAL_QUERY_URL = '/api/forensics/v1/financial/query';
  var FINANCIAL_REVISIONS_URL = '/api/forensics/v1/financial/revisions';
  var FINANCIAL_STATEMENTS_URL = '/api/forensics/v1/financial/statements';
  var FINANCIAL_QUERY_XLSX_URL = '/api/forensics/v1/financial/query.xlsx';
  var DESKTOP_QUERY = '(min-width: 1100px)';
  var state = {
    payload: null,
    // Which of the workbench's mutually exclusive surfaces is on screen.
    // 'pending'/'open' show the workbench; every other value shows the gate.
    access: 'pending',
    symbol: '',
    findingId: '',
    priority: 'all',
    topic: 'all',
    tab: 'radar',
    // §6 URL state: everything below is serialised into the query string, so a
    // permalink is the whole desk — no browser storage APIs are touched.
    asOfDate: '',
    policy: 'latest_known_as_of',
    cohortId: '',
    peerMetric: '',
    peerAlign: 'exclude',
    peerN: 3,
    peerTol: 45,
    currentPeriod: 0,
    priorPeriod: 1,
    disclosureSection: 'all',
    disclosureFindingId: '',
    redlineId: '',
    evidenceKind: 'finding',
    searchMatches: [],
    searchIndex: -1,
    loadToken: 0,
    lastFocus: null,
    unknownRequestedSymbol: '',
    sourceMode: 'map',
    // §2/§3 — cell evidence + the query nodes the source controls resolve
    // against (populated by the financial query fetch).
    queryNodes: null,
    cellEvidence: null,
    financialToken: 0,
    financial: { phase: 'idle' },
    statementColumns: [],
    statements: { phase: 'idle' },
    statementCells: [],
    exportUnavailable: false,
    receipt: {
      phase: 'idle',
      requestToken: 0,
      latest: null,
      ownerCik: '',
      page: null,
      pageCursors: [null],
      pageIndex: 0,
      rootCellId: '',
      detail: null,
      detailPhase: 'idle',
      lastFocus: null
    },
    // X2-s saved views: the id of the restored view (kept until the user
    // navigates away), a T1 refusal reason when a listed view will not load,
    // and the stored request of a pinned restore, re-POSTed verbatim while
    // the desk still matches the view's subject, policy and cutoff.
    savedActiveId: '',
    savedRefusal: '',
    savedStoreError: false,
    pinnedRequest: null,
    // FIF PF-3/PF-4: the dataset mode the health header named ('golden',
    // 'production' or '' when the answer never arrived), and the entity the
    // current health request was issued for (race guard + no duplicate
    // fetches for one selection).
    datasetMode: '',
    healthRequestedFor: '',
    // FIF PF r1 (R1): every health request ISSUED increments healthSeq and
    // remembers its own seq; healthAnswer holds the accepted answer — the one
    // whose seq is still current AND whose entity is the selected company —
    // so the compare chain waits for the SELECTED issuer's answer even after
    // a company switch, and an older answer can never overwrite a newer one.
    healthSeq: 0,
    healthAnswer: null
  };

  var ui = {};
  var desktopMedia = window.matchMedia(DESKTOP_QUERY);
  var gateSigninHtml = '';

  var METRICS = [
    { key: 'revenue', en: 'Revenue', zh: '营收', format: 'currency' },
    { key: 'gross_profit', en: 'Gross profit', zh: '毛利润', format: 'currency' },
    { key: 'receivables', en: 'Receivables', zh: '应收账款', format: 'currency' },
    { key: 'inventory', en: 'Inventory', zh: '存货', format: 'currency' },
    { key: 'cfo', en: 'Cash from operations', zh: '经营现金流', format: 'currency' },
    { key: 'capex', en: 'Capital expenditure', zh: '资本开支', format: 'currency' },
    { key: 'op_income', en: 'Operating income', zh: '营业利润', format: 'currency' },
    { key: 'ni', en: 'Net income', zh: '净利润', format: 'currency' },
    { key: 'contract_liabilities', en: 'Contract liabilities', zh: '合同负债', format: 'currency' }
  ];

  var TOPIC_LABELS = {
    revenue: ['Revenue', '营收'],
    revenue_recognition: ['Revenue recognition', '收入确认'],
    receivables: ['Receivables', '应收账款'],
    receivables_vs_revenue: ['Receivables vs revenue', '应收账款与营收'],
    inventory: ['Inventory', '存货'],
    inventory_vs_revenue: ['Inventory vs revenue', '存货与营收'],
    cash_conversion: ['Cash conversion', '现金转化'],
    working_capital: ['Working capital', '营运资本'],
    capitalized_expenses: ['Capitalized expenses', '费用资本化'],
    capex: ['Capital expenditure', '资本开支'],
    capital_intensity: ['Capital intensity', '资本强度'],
    restructuring: ['Restructuring charges', '重组费用'],
    recurring_charges: ['Recurring charges', '重复性费用'],
    stock_compensation: ['Stock compensation', '股权激励'],
    dilution: ['Dilution', '稀释'],
    non_gaap: ['Non-GAAP adjustments', '非 GAAP 调整'],
    pensions: ['Pensions', '养老金'],
    tax: ['Tax', '税务'],
    customer_concentration: ['Customer concentration', '客户集中度'],
    supplier_concentration: ['Supplier concentration', '供应商集中度'],
    commitments: ['Commitments', '承诺事项'],
    leases: ['Lease obligations', '租赁义务'],
    debt: ['Debt', '债务'],
    debt_refinancing: ['Debt refinancing', '债务再融资'],
    covenants: ['Debt covenants', '债务契约'],
    going_concern: ['Going concern', '持续经营'],
    auditor: ['Auditor', '审计师'],
    auditor_report: ['Auditor report', '审计师报告'],
    material_weakness: ['Material weakness', '重大缺陷'],
    risk_factors: ['Risk factors', '风险因素'],
    business: ['Business', '业务'],
    mda: ['Management discussion', '管理层讨论'],
    financial_statements: ['Financial statements', '财务报表'],
    controls: ['Controls and procedures', '控制与程序'],
    accounting_policies: ['Accounting policies', '会计政策'],
    preamble: ['Filing preamble', '披露前言'],
    segments: ['Segments', '分部'],
    kpi_disappearance: ['Disappearing KPI', '消失的 KPI'],
    margin: ['Margins', '利润率'],
    margins: ['Margins', '利润率']
  };

  function byId(id) { return document.getElementById(id); }

  function cacheUi() {
    ui.workspace = byId('ff-workspace');
    ui.main = byId('ff-main');
    ui.asOf = byId('ff-as-of');
    ui.sourceSnapshot = byId('ff-source-snapshot');
    ui.freshnessStatus = byId('ff-freshness-status');
    ui.runMeta = byId('ff-run-meta');
    ui.sourceLabel = byId('ff-source-label');
    ui.deskHeader = byId('ff-desk-header');
    ui.deskStamp = byId('ff-desk-stamp');
    ui.deskAsOf = byId('ff-desk-asof');
    ui.asofLatest = byId('ff-asof-latest');
    ui.asofInput = byId('ff-asof-input');
    ui.exportLink = byId('ff-export-link');
    ui.exportBtn = byId('ff-export-btn');
    ui.exportWrap = byId('ff-desk-export');
    ui.statCoverageLabel = byId('ff-stat-coverage-label');
    ui.search = byId('ff-company-search');
    ui.searchClear = byId('ff-search-clear');
    ui.companyOptions = byId('ff-company-options');
    ui.companyIdentity = byId('ff-company-identity');
    ui.companyAction = byId('ff-company-action');
    ui.notice = byId('ff-data-notice');
    ui.overview = byId('ff-overview');
    ui.overviewStatus = byId('ff-overview-status');
    ui.quickSignal = byId('ff-quick-signal');
    ui.quickSignalLabel = byId('ff-quick-signal-label');
    ui.quickSignalTitle = byId('ff-quick-signal-title');
    ui.quickSignalSummary = byId('ff-quick-signal-summary');
    ui.quickSignalMagnitude = byId('ff-quick-signal-magnitude');
    ui.statAttention = byId('ff-stat-attention');
    ui.statWatch = byId('ff-stat-watch');
    ui.statCoverage = byId('ff-stat-coverage');
    ui.statSources = byId('ff-stat-sources');
    ui.tabs = Array.prototype.slice.call(document.querySelectorAll('.ff-tab'));
    ui.viewStatus = byId('ff-view-status');
    ui.priorityFilters = byId('ff-priority-filters');
    ui.topic = byId('ff-topic-select');
    ui.filterSummary = byId('ff-filter-summary');
    ui.findings = byId('ff-findings');
    ui.statements = byId('ff-statements');
    ui.disclosureSection = byId('ff-disclosure-section');
    ui.disclosureSummary = byId('ff-disclosure-summary');
    ui.disclosureFeed = byId('ff-disclosure-feed');
    ui.redlineSummary = byId('ff-redline-summary');
    ui.redlineList = byId('ff-redline-list');
    ui.timeline = byId('ff-timeline');
    ui.currentPeriod = byId('ff-current-period');
    ui.priorPeriod = byId('ff-prior-period');
    ui.compareGrid = byId('ff-compare-grid');
    ui.trace = byId('ff-trace');
    ui.sourceTabs = Array.prototype.slice.call(document.querySelectorAll('.ff-source-tab'));
    ui.sourceMapPanel = byId('ff-source-panel-map');
    ui.receiptPanel = byId('ff-source-panel-receipt');
    ui.receipt = byId('ff-receipt');
    ui.evidence = byId('ff-evidence');
    ui.evidenceTitle = byId('ff-evidence-title');
    ui.evidenceBody = byId('ff-evidence-body');
    ui.evidenceClose = byId('ff-evidence-close');
    ui.receiptInspector = byId('ff-receipt-inspector');
    ui.receiptInspectorTitle = byId('ff-receipt-inspector-title');
    ui.receiptInspectorBody = byId('ff-receipt-inspector-body');
    ui.receiptInspectorClose = byId('ff-receipt-inspector-close');
    ui.scrim = byId('ff-scrim');
    ui.siteNav = document.querySelector('.site-nav');
    ui.gate = byId('ff-gate');
    ui.gateState = byId('ff-gate-state');
    ui.gatePreview = byId('ff-gate-preview');
    // The anonymous state is authored in the shell so a stranger and a crawler
    // read it without running JS. Stash it verbatim before any other state
    // overwrites the node: signing out mid-session has to restore exactly this
    // markup, and a second copy of the copy in JS would drift from the shell.
    if (ui.gateState && !gateSigninHtml) gateSigninHtml = ui.gateState.innerHTML;
  }

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function pair(en, zh) {
    var safeEn = en == null || en === '' ? '—' : String(en);
    var safeZh = zh == null || zh === '' ? safeEn : String(zh);
    return '<span class="l-en">' + esc(safeEn) + '</span>' +
      '<span class="l-zh">' + esc(safeZh) + '</span>';
  }

  function lang() {
    return document.documentElement.getAttribute('data-lang') === 'zh' ? 'zh' : 'en';
  }

  function localized(value, preferred) {
    if (value == null) return '';
    if (typeof value !== 'object') return String(value);
    var wanted = preferred || lang();
    var alternate = wanted === 'zh' ? (value['zh-Hans'] || value.zh_hans || value.zh_CN) : '';
    return String(value[wanted] || alternate || value.en || value.zh || value.label || value.name || '');
  }

  function fieldPair(obj, stem, fallback) {
    obj = obj || {};
    var en = obj[stem + '_en'];
    var zh = obj[stem + '_zh'];
    if (en == null) en = obj[stem];
    if (en == null) en = fallback || '';
    if (zh == null) zh = en;
    return pair(en, zh);
  }

  function formatDate(value) {
    if (!value) return '—';
    var text = String(value);
    var match = text.match(/^\d{4}-\d{2}-\d{2}/);
    return match ? match[0] : text;
  }

  function translatedDataPhrase(value, preferred) {
    var text = String(value || '');
    if (preferred !== 'zh') return text;
    var known = {
      'SEC Company Facts normalized projection': 'SEC 公司事实标准化投影',
      'repository quarterly and annual EDGAR panels': '仓库内季度及年度 EDGAR 面板',
      'normalized_quarterly_projection': '标准化季度投影',
      'filing_index': '披露索引',
      'companyfacts_source': '公司事实来源'
    };
    return known[text] || text;
  }

  function basisPair(value) {
    var raw = value || 'Source basis unavailable';
    return pair(prettify(raw), translatedDataPhrase(raw, 'zh'));
  }

  function numberValue(value) {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value === 'string' && value.trim() !== '') {
      var parsed = Number(value.replace(/,/g, ''));
      if (Number.isFinite(parsed)) return parsed;
    }
    return null;
  }

  function compactNumber(value, digits) {
    var numeric = numberValue(value);
    if (numeric == null) return value == null || value === '' ? '—' : String(value);
    var abs = Math.abs(numeric);
    var precision = digits == null ? 1 : digits;
    if (abs >= 1e12) return (numeric / 1e12).toFixed(precision).replace(/\.0$/, '') + 'T';
    if (abs >= 1e9) return (numeric / 1e9).toFixed(precision).replace(/\.0$/, '') + 'B';
    if (abs >= 1e6) return (numeric / 1e6).toFixed(precision).replace(/\.0$/, '') + 'M';
    if (abs >= 1e3) return (numeric / 1e3).toFixed(precision).replace(/\.0$/, '') + 'K';
    return numeric.toLocaleString('en-US', { maximumFractionDigits: 2 });
  }

  function formatMoney(value) {
    var numeric = numberValue(value);
    if (numeric == null) return value == null || value === '' ? '—' : String(value);
    var sign = numeric < 0 ? '−' : '';
    return sign + '$' + compactNumber(Math.abs(numeric), 1);
  }

  function formatPercent(value) {
    var numeric = numberValue(value);
    if (numeric == null) return value == null || value === '' ? '—' : String(value);
    // State-contract percentages are always decimal ratios, including values
    // above 1.0 (for example 1.869 means 186.9%, never 1.9%).
    var pct = numeric * 100;
    return pct.toLocaleString('en-US', { maximumFractionDigits: 1 }) + '%';
  }

  function formatValue(value, format) {
    var style = String(format || '').toLowerCase();
    if (value == null || value === '') return '—';
    if (/percent|percentage|pct/.test(style)) return formatPercent(value);
    if (/currency|money|usd|dollar/.test(style)) return formatMoney(value);
    if (/multiple|ratio_x|times/.test(style)) {
      var ratio = numberValue(value);
      return ratio == null ? String(value) : ratio.toLocaleString('en-US', { maximumFractionDigits: 2 }) + '×';
    }
    if (/integer|count/.test(style)) {
      var count = numberValue(value);
      return count == null ? String(value) : Math.round(count).toLocaleString('en-US');
    }
    return compactNumber(value, 1);
  }

  function formatSigned(value, format) {
    var numeric = numberValue(value);
    if (numeric == null) return formatValue(value, format);
    if (numeric === 0) return formatValue(numeric, format);
    var prefix = numeric > 0 ? '+' : '−';
    return prefix + formatValue(Math.abs(numeric), format);
  }

  // P2 repair (item 7): the difference between two percentages is a move in
  // percentage POINTS, never a percent change — "−3.8% → 0.1%" reads
  // "+3.9 pts", not "+4.0%". Non-percent formats keep formatSigned.
  function isPercentFormat(format) {
    return /percent|percentage|pct/.test(String(format || '').toLowerCase());
  }

  function formatChange(value, format, preferred) {
    var numeric = numberValue(value);
    if (numeric == null || !isPercentFormat(format)) return formatSigned(value, format);
    var points = Math.abs(numeric * 100).toLocaleString('en-US', { maximumFractionDigits: 1 });
    var prefix = numeric > 0 ? '+' : numeric < 0 ? '−' : '';
    return prefix + points + (preferred === 'zh' ? ' 个百分点' : ' pts');
  }

  // The first value that actually moved: the glance number, the card summary
  // and the rail all describe this one value (R2: never a sort key).
  function firstChangedValue(finding) {
    var values = Array.isArray(finding && finding.values) ? finding.values : [];
    for (var index = 0; index < values.length; index += 1) {
      var value = objectValue(values[index]);
      if (value && numberValue(value.delta) != null) return value;
    }
    return null;
  }

  // Item 8: the value the change is measured FROM. When a sibling value's
  // current equals this value's prior, that sibling names the basis (an
  // annual series compares the latest year with the oldest, not the year
  // before); otherwise the finding's prior filing period does.
  function basisValue(finding, value) {
    var prior = numberValue(value && value.prior);
    var values = Array.isArray(finding && finding.values) ? finding.values : [];
    if (prior == null) return null;
    for (var index = 0; index < values.length; index += 1) {
      var other = objectValue(values[index]);
      if (other && other !== value && numberValue(other.current) === prior) return other;
    }
    return null;
  }

  function periodToken(label) {
    var match = String(label || '').match(/^(FY\d{4}(?:\s?Q\d)?)(?:\s|$)/);
    return match ? match[1] : '';
  }

  function trimSharedMetric(label, ownLabel) {
    var a = String(label || '').match(/^(FY\d{4}(?:\s?Q\d)?)\s+(.+)$/);
    var b = String(ownLabel || '').match(/^(FY\d{4}(?:\s?Q\d)?)\s+(.+)$/);
    return a && b && a[2] === b[2] ? a[1] : String(label || '');
  }

  function comparisonBasis(finding, value) {
    var basis = basisValue(finding, value);
    if (basis) {
      var basisEn = String(basis.label_en || basis.label || '');
      var basisZh = String(basis.label_zh || basisEn);
      var ownEn = String(value.label_en || value.label || '');
      var ownZh = String(value.label_zh || ownEn);
      return { en: trimSharedMetric(basisEn, ownEn), zh: trimSharedMetric(basisZh, ownZh) };
    }
    if (finding && finding.period_prior) return { en: String(finding.period_prior), zh: String(finding.period_prior) };
    return { en: 'the comparison period', zh: '对比期' };
  }

  // Item 8: the period chip names the comparison the numbers make. An annual
  // series ("FY2025 accrual intensity" vs "FY2023 …") names its own years;
  // otherwise the finding's filing periods stand.
  function findingPeriodText(finding) {
    finding = finding || {};
    var value = firstChangedValue(finding);
    var basis = value ? basisValue(finding, value) : null;
    var currentToken = value ? periodToken(value.label_en || value.label) : '';
    var basisToken = basis ? periodToken(basis.label_en || basis.label) : '';
    if (currentToken && basisToken) return currentToken + ' vs ' + basisToken;
    var periods = [finding.period_current, finding.period_prior].filter(Boolean);
    return periods.length > 1 ? periods[0] + ' vs ' + periods[1] : periods[0] || '—';
  }

  // Item 7: a percent-format change is described from the structured values
  // (level, basis, move in points) instead of the engine sentence, whose
  // ratio-difference wording prints points as a percent. Other formats keep
  // the engine summary.
  function findingSummaryHtml(finding, fallback) {
    var value = firstChangedValue(finding);
    var current = value ? numberValue(value.current) : null;
    var prior = value ? numberValue(value.prior) : null;
    var delta = value ? numberValue(value.delta) : null;
    if (!value || !isPercentFormat(value.format) || current == null || prior == null || delta == null) {
      return fieldPair(finding, 'summary', fallback);
    }
    var basis = comparisonBasis(finding, value);
    var labelEn = String(value.label_en || value.label || prettify(value.key));
    var labelZh = String(value.label_zh || labelEn);
    var currentText = formatValue(current, value.format);
    var priorText = formatValue(prior, value.format);
    if (delta === 0) {
      return pair(labelEn + ' was ' + currentText + ', unchanged from ' + basis.en + '.',
        labelZh + '为 ' + currentText + '，与' + basis.zh + '持平。');
    }
    var up = delta > 0;
    return pair(
      labelEn + ' was ' + currentText + ', ' + (up ? 'up ' : 'down ') +
        formatChange(Math.abs(delta), value.format, 'en').replace(/^\+/, '') +
        ' from ' + basis.en + ' (' + priorText + ').',
      labelZh + '为 ' + currentText + '，较' + basis.zh + '（' + priorText + '）' + (up ? '上升 ' : '下降 ') +
        formatChange(Math.abs(delta), value.format, 'zh').replace(/^\+/, '') + '。'
    );
  }

  // Item 9: GICS sector names carry a ZH twin at glance.
  var SECTOR_ZH = {
    'Information Technology': '信息技术',
    'Health Care': '医疗保健',
    'Financials': '金融',
    'Consumer Discretionary': '非必需消费品',
    'Consumer Staples': '必需消费品',
    'Communication Services': '通信服务',
    'Industrials': '工业',
    'Energy': '能源',
    'Materials': '原材料',
    'Utilities': '公用事业',
    'Real Estate': '房地产'
  };

  function sectorZh(sector) {
    var text = String(sector || '');
    return SECTOR_ZH[text] || text;
  }

  // Item 9: the glance names the source in plain words, never the state
  // contract's internal projection label.
  function plainSourcePair(source) {
    source = source || {};
    var rawEn = localized(source.label, 'en') || localized(source.basis, 'en');
    var probe = [rawEn, localized(source.name, 'en'), localized(source.basis, 'en')].join(' ');
    if (/\bSEC\b|EDGAR|company ?facts/i.test(probe)) return pair('SEC company filings', 'SEC 公司财报');
    if (!rawEn) return '—';
    var rawZh = localized(source.label, 'zh') || localized(source.basis, 'zh') || rawEn;
    return pair(rawEn, translatedDataPhrase(rawZh, 'zh'));
  }

  function periodLabel(period) {
    if (!period) return '—';
    var year = period.fiscal_year == null ? '' : String(period.fiscal_year);
    var quarter = period.fiscal_quarter == null ? '' : String(period.fiscal_quarter);
    var label = year && quarter ? 'FY' + year + ' Q' + quarter : [year, quarter].filter(Boolean).join(' ');
    return label || formatDate(period.period_end);
  }

  function prettify(value) {
    var text = String(value || '').replace(/[_-]+/g, ' ').trim();
    return text ? text.charAt(0).toUpperCase() + text.slice(1) : 'Other';
  }

  function topicPair(topic) {
    var key = String(topic || 'other').toLowerCase();
    var known = TOPIC_LABELS[key];
    if (known) return pair(known[0], known[1]);
    return pair(prettify(key), '其他：' + prettify(key));
  }

  function topicText(topic, preferred) {
    var key = String(topic || 'other').toLowerCase();
    var known = TOPIC_LABELS[key];
    if (known) return preferred === 'zh' ? known[1] : known[0];
    return preferred === 'zh' ? '其他：' + prettify(key) : prettify(key);
  }

  function priorityInfo(priority) {
    if (priority === 'high') return { icon: '!', en: 'Needs attention', zh: '需要关注' };
    return { icon: '○', en: 'Keep an eye on', zh: '持续观察' };
  }

  function safeUrl(value) {
    if (!value) return '';
    try {
      var parsed = new URL(String(value), window.location.href);
      return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? parsed.href : '';
    } catch (error) {
      return '';
    }
  }

  function companies() {
    return state.payload && state.payload.companies && typeof state.payload.companies === 'object'
      ? state.payload.companies : {};
  }

  function company() {
    return state.symbol ? companies()[state.symbol] : null;
  }

  function orderedFindings(targetCompany) {
    var findings = targetCompany && Array.isArray(targetCompany.findings) ? targetCompany.findings.slice() : [];
    var ranked = state.payload && Array.isArray(state.payload.ranked_findings) ? state.payload.ranked_findings : [];
    var positions = {};
    ranked.forEach(function (entry, index) {
      if (String(entry.symbol || '').toUpperCase() === state.symbol) positions[String(entry.finding_id)] = index;
    });
    findings.sort(function (a, b) {
      var ai = Object.prototype.hasOwnProperty.call(positions, String(a.id)) ? positions[String(a.id)] : 100000;
      var bi = Object.prototype.hasOwnProperty.call(positions, String(b.id)) ? positions[String(b.id)] : 100000;
      if (ai !== bi) return ai - bi;
      if (a.priority === b.priority) return 0;
      return a.priority === 'high' ? -1 : 1;
    });
    return findings;
  }

  function selectedFinding() {
    var findings = orderedFindings(company());
    for (var index = 0; index < findings.length; index += 1) {
      if (String(findings[index].id) === String(state.findingId)) return findings[index];
    }
    return null;
  }

  function selectedFindingButton() {
    return Array.prototype.find.call(ui.findings.querySelectorAll('[data-finding-id]'), function (candidate) {
      return candidate.getAttribute('data-finding-id') === state.findingId;
    }) || null;
  }

  // Wave 2 disclosure state is deliberately optional. The filing-diff producer
  // is additive to the v1 normalized statement contract, so a company without
  // a comparable accession pair must render an honest empty state rather than a
  // synthetic redline or an inferred text result.
  function objectValue(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : null;
  }

  function disclosureBundle(target) {
    var candidates = target ? [
      target.disclosure_bundle,
      target.disclosures,
      target.filing_disclosures,
      target.filing_diff
    ] : [];
    for (var index = 0; index < candidates.length; index += 1) {
      var candidate = candidates[index];
      if (Array.isArray(candidate)) {
        for (var itemIndex = candidate.length - 1; itemIndex >= 0; itemIndex -= 1) {
          if (objectValue(candidate[itemIndex])) return candidate[itemIndex];
        }
      }
      if (objectValue(candidate)) return candidate;
    }
    return {};
  }

  function disclosureTracks(target) {
    var bundle = disclosureBundle(target || company());
    return (Array.isArray(bundle.tracks) ? bundle.tracks : []).filter(function (track) {
      return objectValue(track);
    });
  }

  function disclosureTrackClock(track) {
    var filing = objectValue(track && track.current_filing) || {};
    var clocks = objectValue(filing.clocks) || objectValue(track && track.clocks) || {};
    return String(clocks.accepted_at || filing.filed_at || filing.filed || track.as_of || '').replace(/[^0-9TZ:+-]/g, '');
  }

  function readyDisclosureTracks(target) {
    var ready = disclosureTracks(target).filter(function (track) {
      return objectValue(track.comparison) && String(track.status || 'ready').toLowerCase() === 'ready';
    });
    ready.sort(function (left, right) {
      var rightClock = disclosureTrackClock(right);
      var leftClock = disclosureTrackClock(left);
      if (rightClock !== leftClock) return rightClock.localeCompare(leftClock);
      return String(right.form || '').localeCompare(String(left.form || ''));
    });
    return ready;
  }

  function selectedDisclosureTrack(target) {
    return readyDisclosureTracks(target)[0] || null;
  }

  function disclosureComparison(target) {
    var bundle = disclosureBundle(target);
    var track = selectedDisclosureTrack(target);
    var candidates = [
      track && track.comparison,
      bundle.comparison,
      bundle.latest_comparison,
      bundle.disclosure_comparison,
      bundle
    ];
    for (var index = 0; index < candidates.length; index += 1) {
      var candidate = objectValue(candidates[index]);
      if (!candidate) continue;
      if (candidate.prior_document || candidate.current_document || candidate.redline_ops || candidate.redlines || candidate.findings) return candidate;
    }
    return {};
  }

  function disclosureFindings(target) {
    target = target || company();
    var tracks = readyDisclosureTracks(target);
    if (tracks.length) {
      var tracked = [];
      tracks.forEach(function (track) {
        var comparison = objectValue(track.comparison) || {};
        (Array.isArray(comparison.findings) ? comparison.findings : []).forEach(function (item) {
          if (!objectValue(item)) return;
          tracked.push(Object.assign({}, item, { _track_form: String(track.form || '') }));
        });
      });
      return tracked;
    }
    var comparison = disclosureComparison(target);
    var bundle = disclosureBundle(target);
    var values = Array.isArray(comparison.findings) ? comparison.findings :
      (Array.isArray(bundle.findings) ? bundle.findings : []);
    return values.filter(function (item) { return objectValue(item); });
  }

  function disclosureRedlines(target) {
    target = target || company();
    var tracks = readyDisclosureTracks(target);
    if (tracks.length) {
      var tracked = [];
      tracks.forEach(function (track) {
        var comparison = objectValue(track.comparison) || {};
        var values = Array.isArray(comparison.redline_ops) ? comparison.redline_ops :
          (Array.isArray(comparison.redlines) ? comparison.redlines : []);
        values.forEach(function (item) {
          if (!objectValue(item)) return;
          tracked.push(Object.assign({}, item, { _track_form: String(track.form || '') }));
        });
      });
      return tracked;
    }
    var comparison = disclosureComparison(target);
    var bundle = disclosureBundle(target);
    var values = Array.isArray(comparison.redline_ops) ? comparison.redline_ops :
      (Array.isArray(comparison.redlines) ? comparison.redlines :
        (Array.isArray(bundle.redline_ops) ? bundle.redline_ops :
          (Array.isArray(bundle.redlines) ? bundle.redlines : [])));
    return values.filter(function (item) { return objectValue(item); });
  }

  function disclosureDocuments(target) {
    target = target || company();
    var comparison = disclosureComparison(target);
    var bundle = disclosureBundle(target);
    var values = [];
    function appendDocument(item, form, role) {
      if (!objectValue(item)) return;
      var accession = String(item.accession || '');
      var duplicate = values.some(function (saved) {
        return saved === item || (accession && accession === String(saved.accession || ''));
      });
      if (!duplicate) values.push(Object.assign({}, item, { _track_form: form || item.form || '', _filing_role: role || '' }));
    }
    readyDisclosureTracks(target).forEach(function (track) {
      appendDocument(track.prior_filing, String(track.form || ''), 'prior');
      appendDocument(track.current_filing, String(track.form || ''), 'current');
    });
    [
      comparison.prior_document,
      comparison.current_document,
      bundle.prior_document,
      bundle.current_document
    ].forEach(function (item) {
      appendDocument(item, '', '');
    });
    if (Array.isArray(bundle.documents)) {
      bundle.documents.forEach(function (item) {
        appendDocument(item, '', '');
      });
    }
    return values;
  }

  function disclosureSectionById(sectionId) {
    if (!sectionId) return '';
    var comparisons = readyDisclosureTracks(company()).map(function (track) {
      return objectValue(track.comparison) || {};
    });
    if (!comparisons.length) comparisons.push(disclosureComparison(company()));
    var groups = [];
    comparisons.forEach(function (comparison) {
      var sectionGroups = comparison.sections || {};
      groups.push(sectionGroups.prior, sectionGroups.current, comparison.prior_sections, comparison.current_sections);
    });
    for (var index = 0; index < groups.length; index += 1) {
      var sections = Array.isArray(groups[index]) ? groups[index] : [];
      for (var sectionIndex = 0; sectionIndex < sections.length; sectionIndex += 1) {
        if (String(sections[sectionIndex].section_id || '') === String(sectionId)) return String(sections[sectionIndex].key || '');
      }
    }
    return '';
  }

  function disclosureFindingSection(finding) {
    if (!finding) return 'other';
    if (finding.section_key) return String(finding.section_key);
    var sectionIds = [];
    if (Array.isArray(finding.current_section_ids)) sectionIds = sectionIds.concat(finding.current_section_ids);
    if (Array.isArray(finding.prior_section_ids)) sectionIds = sectionIds.concat(finding.prior_section_ids);
    var receipts = Array.isArray(finding.evidence_receipts) ? finding.evidence_receipts : [];
    receipts.forEach(function (receipt) {
      if (receipt && receipt.section_id) sectionIds.push(receipt.section_id);
    });
    for (var index = 0; index < sectionIds.length; index += 1) {
      var section = disclosureSectionById(sectionIds[index]);
      if (section) return section;
    }
    return 'other';
  }

  function disclosureFindingId(finding) {
    return String((finding && (finding.finding_id || finding.id || finding.key)) || '');
  }

  function redlineId(redline) {
    return String((redline && (redline.op_id || redline.id || redline.key)) || '');
  }

  function selectedDisclosureFinding() {
    var wanted = String(state.disclosureFindingId || '');
    return disclosureFindings().find(function (finding) { return disclosureFindingId(finding) === wanted; }) || null;
  }

  function selectedRedline() {
    var wanted = String(state.redlineId || '');
    return disclosureRedlines().find(function (redline) { return redlineId(redline) === wanted; }) || null;
  }

  function selectedEvidenceButton() {
    var attribute = state.evidenceKind === 'disclosure-finding' ? 'data-disclosure-finding-id' :
      state.evidenceKind === 'redline' ? 'data-redline-id' : 'data-finding-id';
    var wanted = state.evidenceKind === 'disclosure-finding' ? state.disclosureFindingId :
      state.evidenceKind === 'redline' ? state.redlineId : state.findingId;
    return Array.prototype.find.call(document.querySelectorAll('[' + attribute + ']'), function (candidate) {
      return candidate.getAttribute(attribute) === String(wanted);
    }) || null;
  }

  function setLoading() {
    ui.viewStatus.innerHTML = pair('Loading filing data…', '正在载入财报数据…');
    var loading = '<div class="ff-loading" role="status"><span class="ff-loading-dot" aria-hidden="true"></span>' +
      pair('Loading filing review data…', '正在载入财报审阅数据…') + '</div>';
    ui.findings.innerHTML = loading;
    ui.statements.innerHTML = loading;
    ui.disclosureFeed.innerHTML = loading;
    ui.redlineList.innerHTML = loading;
    ui.timeline.innerHTML = loading;
    ui.compareGrid.innerHTML = loading;
    ui.trace.innerHTML = loading;
  }

  // Same shape as receiptFailurePhase() below, which already separates "you may
  // not read this" from "this is broken" for the private receipt pane. The main
  // loader used to collapse both into one 'Data unavailable' card, so a visitor
  // who simply was not signed in was told the product was broken and handed a
  // Retry button that could never work.
  //
  // The three denials are distinct products of app/forensics.py: 401 from the
  // authentication dependency, 403 from the site_full entitlement check, and 503
  // when the state object itself is missing. Anything without a status (offline,
  // a decode failure, a contract violation) is a genuine fault, so it takes the
  // temporary branch and keeps its Retry.
  function stateFailurePhase(error) {
    var status = error && error.status;
    if (status === 401) return 'signin';
    if (status === 403) return 'upgrade';
    return 'unavailable';
  }

  var GATE_COPY = {
    upgrade: {
      chip: ['Included in Essential', 'Essential 包含'],
      title: ['Not in your plan', '当前方案未包含'],
      stance: [
        'Essential opens the findings, the rules behind them, and the SEC sources.',
        'Essential 可查阅全部发现、触发它们的规则，以及对应的 SEC 来源。'
      ],
      primary: ['View Essential plans', '查看 Essential 方案'],
      primaryAction: 'plans'
    },
    unavailable: {
      chip: ['Temporary', '暂时'],
      title: ['Data is being refreshed', '数据正在更新'],
      stance: [
        'Nothing is wrong with your account. Try again in a few minutes.',
        '这与你的账户无关，请稍后几分钟再试。'
      ],
      primary: ['Retry', '重试'],
      primaryAction: 'retry'
    },
    empty: {
      chip: ['Coverage', '覆盖范围'],
      title: ['No companies this run', '本次更新没有公司'],
      stance: [
        'This is not an all-clear — the latest run added no companies to review.',
        '这不代表“没有问题”——本次更新未纳入可审阅的公司。'
      ],
      note: ['Check back after the next filing run.', '下次披露更新后再来查看。']
    }
  };

  function renderGateState(phase) {
    var copy = GATE_COPY[phase];
    if (!copy) return;
    var actions = '';
    if (copy.primary) {
      actions = '<div class="ff-gate-actions"><button class="ff-gate-primary" type="button" data-gate-action="' +
        copy.primaryAction + '">' + pair(copy.primary[0], copy.primary[1]) + '</button></div>';
    } else if (copy.note) {
      actions = '<p class="ff-gate-note">' + pair(copy.note[0], copy.note[1]) + '</p>';
    }
    ui.gateState.innerHTML = '<p class="ff-gate-chip"><span class="ff-gate-dot" aria-hidden="true"></span>' +
      pair(copy.chip[0], copy.chip[1]) + '</p>' +
      '<h2 id="ff-gate-title">' + pair(copy.title[0], copy.title[1]) + '</h2>' +
      '<p class="ff-gate-stance">' + pair(copy.stance[0], copy.stance[1]) + '</p>' + actions;
  }

  // One surface is on screen at a time: the workbench, or the gate. Routing both
  // through here is what keeps a half-populated workbench from sitting under an
  // error, which is how the old error path left the tab bar, the filter chrome
  // and the company picker live over seven panels of "Data unavailable".
  function setAccess(next) {
    ui.gate.removeAttribute('aria-busy');
    if (state.access === next) return;
    state.access = next;
    var gated = next !== 'pending' && next !== 'open';
    ui.workspace.setAttribute('data-access', next);
    ui.workspace.classList.toggle('ff-gated', gated);
    ui.gate.hidden = !gated;
    if (!gated) return;
    // The gate carries the whole message; a second copy in the notice strip
    // would be the stacked-disclaimer defect the copy law forbids.
    ui.notice.hidden = true;
    ui.notice.innerHTML = '';
    // Both funnel states get the product story; the two states behind the wall
    // do not. A Free member is the visitor closest to paying, so showing them
    // less than a stranger gets is backwards — and the preview holds no rows, so
    // there is nothing to withhold. A signed-in Essential member hitting a
    // refresh or an empty run already owns the desk: pitching it back to them is
    // noise over the one thing they came for, which is when to return.
    ui.gatePreview.hidden = next !== 'signin' && next !== 'upgrade';
    ui.gateState.setAttribute('data-state', next);
    if (next === 'signin') ui.gateState.innerHTML = gateSigninHtml;
    else renderGateState(next);
  }

  function openPlans() {
    if (window.MMOnboard && typeof window.MMOnboard.open === 'function') {
      window.MMOnboard.open('upgrade', { plan: 'essential', period: 'annual' });
      return;
    }
    if (window.MMXSharedShell) { window.MMXSharedShell.openAuth('billing'); return; }
    window.location.href = '/plans.html';
  }

  function openSignin() {
    if (window.MMXAccessPreview && typeof window.MMXAccessPreview.openSignin === 'function') {
      window.MMXAccessPreview.openSignin();
      return;
    }
    if (window.MDXAuth && typeof window.MDXAuth.open === 'function') {
      window.MDXAuth.open('signin');
      return;
    }
    if (window.MMXSharedShell) { window.MMXSharedShell.openAuth('signin'); return; }
    window.location.href = '/?signin=1';
  }

  function showLoadError(error) {
    var phase = stateFailurePhase(error);
    setAccess(phase);
    ui.viewStatus.innerHTML = phase === 'signin' ? pair('Sign in to read the desk', '登录后查阅') :
      phase === 'upgrade' ? pair('Included in Essential', 'Essential 包含') :
        pair('Data is being refreshed', '数据正在更新');
  }

  function withAuth(headers) {
    headers = headers || {};
    if (IS_LOOPBACK || !(window.MDXAuth && window.MDXAuth.client)) return Promise.resolve(headers);
    return window.MDXAuth.client()
      .then(function (client) { return client.auth.getSession(); })
      .then(function (result) {
        var token = result && result.data && result.data.session && result.data.session.access_token;
        if (token) headers.Authorization = 'Bearer ' + token;
        return headers;
      })
      .catch(function () { return headers; });
  }

  function loadData() {
    var token = state.loadToken + 1;
    state.loadToken = token;
    setLoading();
    ui.notice.hidden = true;
    ui.notice.className = 'ff-data-notice';
    // Deliberately does NOT reset access to 'pending'. A retry from the
    // refreshing state should keep showing that state until the answer changes;
    // dropping back to the skeleton would flash a loading state at a visitor who
    // is already being told to wait, and would flash it at every anonymous
    // visitor between init() and the 401.
    ui.gate.setAttribute('aria-busy', 'true');

    withAuth({ Accept: 'application/gzip' })
      .then(function (headers) {
        return fetch(DATA_URL, {
          headers: headers,
          credentials: 'same-origin',
          cache: 'no-store'
        });
      })
      .then(function (response) {
        if (!response.ok) {
          // Carry the status onto the error the way historyRequest() does: it is
          // the only thing that tells signed-out from unentitled from broken.
          var failure = new Error('State request failed');
          failure.status = response.status;
          throw failure;
        }
        // Inspect the received bytes instead of trusting Content-Encoding. Fetch
        // may already have decoded a proxy encoding; a literal private .gz object
        // still carries the gzip magic bytes. This also survives accidental outer
        // proxy compression without attempting to parse the inner gzip as JSON.
        return response.arrayBuffer().then(function (buffer) {
          var bytes = new Uint8Array(buffer);
          var isGzip = bytes.length > 2 && bytes[0] === 0x1f && bytes[1] === 0x8b;
          if (!isGzip) return new Response(buffer).json();
          if (typeof window.DecompressionStream !== 'function') {
            throw new Error('This browser cannot open the protected compressed state');
          }
          var stream = new Blob([buffer]).stream().pipeThrough(new window.DecompressionStream('gzip'));
          return new Response(stream).json();
        });
      })
      .then(function (payload) {
        if (token !== state.loadToken) return;
        if (!payload || !payload.companies || typeof payload.companies !== 'object') {
          throw new Error('Invalid state contract');
        }
        state.payload = payload;
        // A run that covers nobody is a fact about the run, not a failure and
        // not an all-clear, so it gets its own gate state rather than seven
        // panels of empty cards behind a live tab bar.
        setAccess(Object.keys(payload.companies).length ? 'open' : 'empty');
        if (state.access === 'empty') {
          loadHealth();
          return;
        }
        selectInitialCompany();
        applyUrlState(true);
        renderAll();
        loadHealth();
      })
      .catch(function (error) {
        if (token !== state.loadToken) return;
        showLoadError(error);
        loadHealth();
      });
  }

  function requestedSymbol() {
    var params = new URLSearchParams(window.location.search);
    return String(params.get('symbol') || '').trim().toUpperCase();
  }

  // ── URL state schema (§6) ───────────────────────────────────────────────
  // Unknown params are ignored and invalid enums fall back to their default;
  // reading never throws. `symbol` keeps working exactly as before.
  var URL_TABS = ['radar', 'statements', 'disclosures', 'redlines', 'timeline', 'compare', 'trace', 'peers'];
  var URL_POLICIES = ['as_reported', 'latest_known_as_of', 'latest_restated'];

  function urlInt(value, fallback) {
    var parsed = parseInt(value, 10);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
  }

  function readUrlParams() {
    var params = new URLSearchParams(window.location.search);
    var tab = String(params.get('tab') || '');
    var policy = String(params.get('policy') || '');
    var align = String(params.get('align') || '');
    var span = String(params.get('span') || '');
    var src = String(params.get('src') || '');
    return {
      symbol: String(params.get('symbol') || '').trim().toUpperCase(),
      tab: URL_TABS.indexOf(tab) >= 0 ? tab : 'radar',
      asOfDate: /^\d{4}-\d{2}-\d{2}$/.test(String(params.get('as_of') || '')) ? String(params.get('as_of')) : '',
      policy: URL_POLICIES.indexOf(policy) >= 0 ? policy : 'latest_known_as_of',
      finding: String(params.get('finding') || ''),
      disc: String(params.get('disc') || ''),
      redline: String(params.get('redline') || ''),
      drawer: String(params.get('drawer') || '') === '1',
      occ: String(params.get('occ') || ''),
      cell: String(params.get('cell') || ''),
      snap: String(params.get('snap') || ''),
      span: /^\d+-\d+$/.test(span) ? span : '',
      src: src === 'receipt' ? 'receipt' : 'map',
      cohort: String(params.get('cohort') || ''),
      peerMetric: String(params.get('peer_metric') || ''),
      align: align === 'shift_labeled' ? 'shift_labeled' : 'exclude',
      peerN: urlInt(params.get('peer_n'), 3),
      peerTol: urlInt(params.get('peer_tol'), 45),
      peers: String(params.get('peers') || '') === '1'
    };
  }

  // Serialises the desk state table (§6.1). Drawer keys ride only the frame a
  // source control pushed, so an ordinary permalink never carries them.
  function writeUrl(push, drawerExtra) {
    var params = new URLSearchParams();
    if (state.symbol) params.set('symbol', state.symbol);
    if (state.tab && state.tab !== 'radar') params.set('tab', state.tab);
    if (state.asOfDate) params.set('as_of', state.asOfDate);
    if (state.policy && state.policy !== 'latest_known_as_of') params.set('policy', state.policy);
    if (state.findingId) params.set('finding', state.findingId);
    if (state.disclosureFindingId) params.set('disc', state.disclosureFindingId);
    if (state.redlineId) params.set('redline', state.redlineId);
    if (state.sourceMode === 'receipt') params.set('src', 'receipt');
    if (state.cohortId) params.set('cohort', state.cohortId);
    if (state.peerMetric) params.set('peer_metric', state.peerMetric);
    if (state.peerAlign === 'shift_labeled') params.set('align', 'shift_labeled');
    if (state.peerN !== 3) params.set('peer_n', String(state.peerN));
    if (state.peerTol !== 45) params.set('peer_tol', String(state.peerTol));
    if (drawerExtra && drawerExtra.drawer) {
      params.set('drawer', '1');
      if (drawerExtra.occ) params.set('occ', drawerExtra.occ);
      if (drawerExtra.cell) params.set('cell', drawerExtra.cell);
      if (drawerExtra.snap) params.set('snap', drawerExtra.snap);
      if (drawerExtra.span) params.set('span', drawerExtra.span);
    }
    var search = params.toString();
    var next = window.location.pathname + (search ? '?' + search : '') + window.location.hash;
    if (push) window.history.pushState({ ffDesk: true }, '', next);
    else window.history.replaceState({ ffDesk: true }, '', next);
  }

  // Applies a parsed URL frame to the desk. `first` normalises the landing URL
  // with replaceState so it becomes shareable without an extra back stop.
  function applyUrlState(first) {
    var url = readUrlParams();
    if (url.symbol) {
      var resolved = resolveSymbol(url.symbol);
      if (resolved && resolved !== state.symbol) setCompany(resolved, false);
    }
    state.asOfDate = url.asOfDate;
    state.policy = url.policy;
    state.sourceMode = url.src;
    state.cohortId = url.cohort;
    state.peerMetric = url.peerMetric;
    state.peerAlign = url.align;
    state.peerN = url.peerN;
    state.peerTol = url.peerTol;
    if (url.finding) state.findingId = url.finding;
    if (url.disc) state.disclosureFindingId = url.disc;
    if (url.redline) state.redlineId = url.redline;
    setTab(url.peers ? 'peers' : url.tab, false);
    if (first) writeUrl(false);
    return url;
  }

  // A drawer frame on the URL re-opens the exact occurrence a permalink points
  // at. Source controls (row 4) carry the data attributes this resolves
  // against; with no match the drawer simply stays closed — never a throw.
  function openDrawerFromUrl(url) {
    if (!url || !url.drawer) return;
    var control = null;
    if (url.occ) control = document.querySelector('[data-occurrence-id="' + cssEscape(url.occ) + '"]');
    if (!control && url.cell) control = document.querySelector('[data-root-cell-id="' + cssEscape(url.cell) + '"].ff-source-control');
    if (control) activateSourceControl(control);
  }

  function cssEscape(value) {
    return window.CSS && typeof window.CSS.escape === 'function'
      ? window.CSS.escape(String(value))
      : String(value).replace(/[^a-zA-Z0-9_-]/g, '');
  }

  // Closing the drawer (Escape, close button, scrim): back out of a pushed
  // drawer frame, else rewrite the URL without drawer keys (§6.2).
  function closeDrawerAndSync() {
    if (readUrlParams().drawer) {
      closeEvidence(true);
      window.history.back();
      return;
    }
    writeUrl(false);
    closeEvidence(true);
  }

  function resolveSymbol(candidate) {
    var keys = Object.keys(companies());
    var wanted = String(candidate || '').toUpperCase();
    for (var index = 0; index < keys.length; index += 1) {
      if (keys[index].toUpperCase() === wanted) return keys[index];
    }
    return '';
  }

  function selectInitialCompany() {
    var keys = Object.keys(companies());
    var requested = requestedSymbol();
    var preferred = resolveSymbol(requested);
    var defaultSymbol = resolveSymbol(state.payload.default_symbol);
    state.unknownRequestedSymbol = requested && !preferred ? requested : '';
    setCompany(preferred || defaultSymbol || keys[0] || '', false);
  }

  function setCompany(symbol, updateUrl) {
    var resolved = resolveSymbol(symbol);
    if (!resolved) return;
    state.symbol = resolved;
    state.priority = 'all';
    state.topic = 'all';
    state.currentPeriod = 0;
    var periods = company() && Array.isArray(company().periods) ? company().periods : [];
    state.priorPeriod = periods.length > 1 ? 1 : 0;
    var findings = orderedFindings(company());
    state.findingId = findings.length ? String(findings[0].id) : '';
    state.disclosureSection = 'all';
    state.disclosureFindingId = '';
    state.redlineId = '';
    state.evidenceKind = 'finding';
    resetReceiptState();
    resetFinancialState();
    resetStatementsState();
    ui.search.value = resolved;
    ui.searchClear.hidden = false;
    closeSearch();
    closeEvidence(false);
    if (updateUrl) {
      // A manual company switch ends the restored view's context — the badge
      // and the pinned-bytes override must not describe another issuer.
      state.savedActiveId = '';
      state.savedRefusal = '';
      state.savedStoreError = false;
      state.pinnedRequest = null;
      writeUrl(true);
      state.unknownRequestedSymbol = '';
    }
    renderCompany();
    if (state.sourceMode === 'receipt') ensureReceiptForCompany();
    // PF-3: the per-issuer generation rides the health answer, so a company
    // change re-fetches health for the new selection (the X2-s one-fetch rule
    // still holds per view; loadHealth drops a redundant request for the
    // issuer it already covers).
    loadHealth();
    ensureFinancialData();
  }

  function renderAll() {
    renderRunMeta();
    renderCompany();
    setTab(state.tab, false);
  }

  function freshnessCopy(status) {
    if (status === 'current') return ['Current', '当前'];
    if (status === 'stale') return ['Stale', '已过期'];
    if (status === 'degraded') return ['Degraded', '降级'];
    return ['Unavailable', '不可用'];
  }

  function applyHealth(health) {
    state.health = health && typeof health === 'object' ? health : { status: 'unavailable', clocks: {} };
    renderRunMeta();
    setAsofControlsFromState();
    // PF-3: a compare chain that parked waiting for the first health answer
    // (no clock can be built without it) is re-driven here with the real
    // clocks and generation — never from empty values.
    if (state.tab === 'compare' && state.financial && state.financial.awaitingHealth) {
      ensureFinancialData();
    }
  }

  function loadHealth() {
    var target = company();
    var entityId = target && target.entity_id ? String(target.entity_id) : '';
    // One health answer per selected issuer: a request already in flight for
    // exactly this entity is not repeated (X2-s — one fetch carries both the
    // clocks and the generation).
    if (entityId && state.healthRequestedFor === entityId) return Promise.resolve();
    state.healthRequestedFor = entityId;
    // PF r1 (R1): this request's sequence token — only an answer whose seq is
    // still the newest ISSUED one may touch the desk.
    var seq = state.healthSeq + 1;
    state.healthSeq = seq;
    return withAuth({ Accept: 'application/json' })
      .then(function (headers) {
        return fetch(entityId ? HEALTH_URL + '?entity_id=' + encodeURIComponent(entityId) : HEALTH_URL, {
          headers: headers,
          credentials: 'same-origin',
          cache: 'no-store'
        });
      })
      .then(function (response) {
        if (!response.ok) throw response;
        // X2-s: the newer-generation signal rides the SAME health fetch —
        // names/ids only (app/forensics.py health headers), never a second
        // request. Annotated onto the client-side copy, not the wire contract.
        // PF-3: the generation is stored with the entity it belongs to, and
        // the dataset mode header rides the same answer into state.
        // PF r1 (R2): the names-only dataset pointer rides the same answer.
        var generation = {
          id: String(response.headers.get('X-FIF-Dataset-Generation-Id') || ''),
          admitted_at: String(response.headers.get('X-FIF-Dataset-Admitted-At') || ''),
          entity_id: entityId
        };
        var mode = String(response.headers.get('X-FIF-Financial-Dataset-Mode') || '');
        var pointer = String(response.headers.get('X-FIF-Dataset-Pointer') || '');
        return response.json().then(function (payload) {
          if (generation.id) payload.generation = generation;
          return { payload: payload, mode: mode, entityId: entityId, pointer: pointer };
        });
      })
      .then(function (answer) {
        // PF r1 (R1) race guard: an answer is current only when its seq is
        // still the newest issued one AND its entity is the selected company.
        // PFM r1 (item 1): the entity comparison is strict — an empty entity
        // id on either side is never a match, so an answer issued before any
        // company was selected cannot land once a company is.
        // Anything older is dropped whole — it must not become the desk's
        // clocks, generation or pointer, even when its entity matches.
        var current = company();
        var currentId = current && current.entity_id ? String(current.entity_id) : '';
        if (seq !== state.healthSeq) return;
        if (String(currentId || '') !== String(answer.entityId || '')) return;
        state.healthAnswer = { entity_id: answer.entityId, seq: seq, ok: true, pointer: answer.pointer };
        state.datasetMode = answer.mode;
        applyHealth(answer.payload);
      })
      .catch(function (error) {
        var current = company();
        var currentId = current && current.entity_id ? String(current.entity_id) : '';
        if (seq !== state.healthSeq) return;
        // PFM r1 (item 1): the same strict comparison — an empty entity id
        // is no match. An answer issued before any company was selected
        // cannot be recorded once a company is.
        if (String(currentId || '') !== String(entityId || '')) return;
        // PF r1 (R2/R5): a failed health fetch is an availability fact, never
        // "not published": record the failed answer for the current seq only,
        // reset the mode and clear the fetch lock so the same issuer can be
        // retried; the honest 503 copy follows from the failed answer.
        // PFM r1 (item 3): a 401 or 403 is an access answer, not an outage —
        // route the desk through the SAME access handling the financial
        // chain already uses for those statuses (showLoadError) and record
        // the status on the failed answer; every other failure (no status,
        // 5xx, network) keeps the 503 copy and Retry unchanged.
        var access = error && (error.status === 401 || error.status === 403);
        state.healthAnswer = {
          entity_id: entityId,
          seq: seq,
          ok: false,
          status: error && error.status,
          pointer: ''
        };
        state.datasetMode = '';
        state.healthRequestedFor = '';
        if (access) {
          showLoadError(error);
          return;
        }
        applyHealth({ status: 'unavailable', clocks: {} });
      });
  }

  function renderRunMeta() {
    var health = state.health || {};
    var status = health.status;
    if (status !== 'current' && status !== 'stale' && status !== 'degraded') status = 'unavailable';
    var clocks = health.clocks || {};
    var payload = state.payload || {};
    var source = payload.source || {};
    var filing = clocks.latest_source_filing_date || payload.as_of || '';
    var snapshot = clocks.broad_source_at || clocks.composed_state_at || payload.generated_at || '';
    var copy = freshnessCopy(status);
    if (ui.runMeta) ui.runMeta.setAttribute('data-freshness', status);
    if (ui.freshnessStatus) ui.freshnessStatus.innerHTML = pair(copy[0], copy[1]);
    if (ui.asOf) ui.asOf.textContent = filing ? formatDate(filing) : '—';
    if (ui.sourceSnapshot) ui.sourceSnapshot.textContent = snapshot ? formatDate(snapshot) : '—';
    if (ui.sourceLabel) ui.sourceLabel.innerHTML = plainSourcePair(source);
    // One as-of line for the desk (doctrine Law 4): the hidden dd cells above
    // keep their ids for renderRunMeta and the tests, and the stamp carries the
    // same two facts in one band.
    var stampDate = (state.asOfDate || filing || snapshot || '').toString();
    var stampText = formatDate(stampDate) || '—';
    if (ui.deskStamp) {
      // At <=700px the run-meta strip folds away (R-a), so the stamp also names
      // the source there; CSS hides this span from 701px up.
      var stampSource = plainSourcePair(source);
      ui.deskStamp.innerHTML = pair('As of ' + stampText + ' · ' + copy[0], '截止 ' + stampText + ' · ' + copy[1]) +
        (stampSource && stampSource !== '—' ? '<span class="ff-desk-stamp-source"> · ' + stampSource + '</span>' : '');
    }
    setAsofControlsFromState();
    refreshExportState();
    renderSavedUI();
  }

  function renderCompany() {
    var target = company();
    if (!target) {
      renderNoCompanies();
      return;
    }
    var symbol = target.symbol || state.symbol;
    var identityCoreEn = [target.sector, target.latest_period].filter(Boolean).join(' · ');
    var identityCoreZh = [sectorZh(target.sector), target.latest_period].filter(Boolean).join(' · ');
    var identityDetailEn = [identityCoreEn, target.latest_filed ? 'Filed ' + formatDate(target.latest_filed) : ''].filter(Boolean).join(' · ');
    var identityDetailZh = [identityCoreZh, target.latest_filed ? '披露于 ' + formatDate(target.latest_filed) : ''].filter(Boolean).join(' · ');
    ui.companyIdentity.innerHTML = '<div class="ff-company-mark" aria-hidden="true">' + esc(String(symbol).slice(0, 5)) + '</div>' +
      '<div><div class="ff-company-name">' + esc(target.name || symbol) + '</div>' +
      '<div class="ff-company-detail">' + pair(identityDetailEn || '—', identityDetailZh || '—') + '</div></div>';

    var findings = orderedFindings(target);
    var highCount = findings.filter(function (item) { return item.priority === 'high'; }).length;
    var watchCount = findings.filter(function (item) { return item.priority === 'watch'; }).length;
    var action = target.action || {};
    var actionKey = action.key || (highCount ? 'high' : watchCount ? 'watch' : 'covered');
    var actionEn = actionKey === 'high'
      ? highCount + (highCount === 1 ? ' needs attention' : ' need attention')
      : actionKey === 'watch'
        ? watchCount + ' to watch'
        : actionKey === 'limited' ? 'Some checks could not run' : 'No unusual change in covered checks';
    var actionZh = actionKey === 'high'
      ? highCount + ' 项变化需要关注'
      : actionKey === 'watch'
        ? watchCount + ' 项变化值得持续观察'
        : actionKey === 'limited' ? '部分检查无法运行' : '已覆盖检查暂无异常变化';
    var actionIcon = actionKey === 'high' ? '!' : actionKey === 'watch' ? '○' : actionKey === 'limited' ? '?' : '✓';
    ui.companyAction.setAttribute('data-action', actionKey);
    ui.companyAction.innerHTML = '<span class="ff-action-glyph" aria-hidden="true">' + actionIcon + '</span>' +
      '<span class="ff-action-copy">' + pair(actionEn, actionZh) + '</span>';

    renderNotice(target);
    renderOverview(target, findings);
    renderTopicOptions(findings);
    renderFindings();
    renderStatements(target);
    renderDisclosureControls(target);
    renderDisclosureFeed(target);
    renderRedlines(target);
    renderTimeline(target);
    renderCompareControls(target);
    renderCompare(target);
    renderTrace(target);
    renderCurrentEvidence();
    updateViewStatus();
  }

  function renderOverview(target, findings) {
    findings = Array.isArray(findings) ? findings : [];
    var high = findings.filter(function (item) { return item.priority === 'high'; });
    var watch = findings.filter(function (item) { return item.priority === 'watch'; });
    var coverage = target.coverage || {};
    var coverageValue = numberValue(coverage.metrics_pct);
    var evidenceCount = findings.reduce(function (total, finding) {
      return total + (Array.isArray(finding.evidence) ? finding.evidence.length : 0);
    }, 0);
    var first = high[0] || watch[0] || findings[0] || null;

    ui.statAttention.textContent = String(high.length);
    ui.statWatch.textContent = String(watch.length);
    ui.statCoverage.textContent = coverageValue == null ? '—' : formatPercent(coverageValue);
    // Item 3: partial coverage is disclosed at glance in the stat itself (the
    // duplicate notice band is gone); nulls stay printed, gaps stay blank.
    if (ui.statCoverageLabel) {
      var partial = coverageValue != null && (coverageValue <= 1 ? coverageValue < 0.999 : coverageValue < 99.9);
      ui.statCoverageLabel.innerHTML = partial
        ? pair('of expected metrics compared · gaps left blank', '预期指标已对比 · 缺失值留空')
        : pair('Metrics compared', '已对比指标');
    }
    ui.statSources.textContent = String(evidenceCount);

    var statusKey = high.length ? 'attention' : watch.length ? 'watch' : first ? 'watch' : 'clear';
    ui.overviewStatus.setAttribute('data-state', statusKey);
    ui.overviewStatus.innerHTML = high.length
      ? pair(high.length + ' change' + (high.length === 1 ? '' : 's') + ' need attention', high.length + ' 项变化需要关注')
      : watch.length
        ? pair(watch.length + ' change' + (watch.length === 1 ? '' : 's') + ' to watch', watch.length + ' 项变化值得观察')
        : pair('No unusual change in covered checks', '已覆盖检查暂无异常变化');

    if (!first) {
      ui.quickSignal.setAttribute('data-priority', 'clear');
      if (ui.quickSignalMagnitude) {
        ui.quickSignalMagnitude.innerHTML = '';
        ui.quickSignalMagnitude.hidden = true;
      }
      ui.quickSignalLabel.innerHTML = pair('Latest covered comparison', '最新已覆盖对比');
      ui.quickSignalTitle.innerHTML = pair('No unusual change surfaced', '暂无异常变化');
      ui.quickSignalSummary.innerHTML = pair(
        'That is not a clean-company verdict. Check the coverage and source limitations before drawing a conclusion.',
        '这并不代表公司没有问题。得出结论前，请先查看覆盖范围和来源局限。'
      );
      var emptyTrigger = ui.quickSignal.querySelector('[data-open-primary-finding]');
      if (emptyTrigger) {
        emptyTrigger.setAttribute('data-go-tab', 'trace');
        emptyTrigger.removeAttribute('data-open-primary-finding');
        emptyTrigger.innerHTML = pair('Check coverage and sources', '查看覆盖范围和来源') + ' <span aria-hidden="true">→</span>';
      }
      return;
    }

    ui.quickSignal.setAttribute('data-priority', first.priority || 'watch');
    ui.quickSignalLabel.innerHTML = pair('Why it matters', '为什么重要');
    ui.quickSignalTitle.innerHTML = fieldPair(first, 'title', 'Filing change');
    ui.quickSignalSummary.innerHTML = findingSummaryHtml(first, 'Open this signal to see the numbers and source.');
    // R2: magnitude is a value on the card, never the sort key — the ranking
    // stays orderedFindings (review priority, then recency). Item 7: it is the
    // first value that MOVED (values[0] of an annual series has no delta), in
    // percentage points for percent-format values.
    if (ui.quickSignalMagnitude) {
      var firstValue = firstChangedValue(first);
      var magnitude = firstValue ? firstValue.delta : null;
      if (magnitude != null) {
        ui.quickSignalMagnitude.innerHTML = pair(
          'Change ' + formatChange(magnitude, firstValue.format, 'en'),
          '变化 ' + formatChange(magnitude, firstValue.format, 'zh')
        );
        ui.quickSignalMagnitude.hidden = false;
      } else {
        ui.quickSignalMagnitude.innerHTML = '';
        ui.quickSignalMagnitude.hidden = true;
      }
    }
    var trigger = ui.quickSignal.querySelector('.ff-quick-signal-open');
    if (trigger) {
      trigger.setAttribute('data-open-primary-finding', '');
      trigger.removeAttribute('data-go-tab');
      // §2.2 — the CTA carries the primary finding's span attributes when the
      // state has attached them (P1-b); none are invented here.
      var findingBounds = spanBounds(first.source_span);
      if (findingBounds) {
        trigger.setAttribute('data-span-start', String(Math.trunc(findingBounds[0])));
        trigger.setAttribute('data-span-end', String(Math.trunc(findingBounds[1])));
      } else {
        trigger.removeAttribute('data-span-start');
        trigger.removeAttribute('data-span-end');
      }
      if (first.occurrence_id) trigger.setAttribute('data-occurrence-id', String(first.occurrence_id));
      else trigger.removeAttribute('data-occurrence-id');
      if (first.current_accession) trigger.setAttribute('data-accession', String(first.current_accession));
      else trigger.removeAttribute('data-accession');
      trigger.innerHTML = pair('Open source', '打开来源') + ' <span aria-hidden="true">→</span>';
    }
  }

  // Coverage-less runs are one product state, so they get one home. This used to
  // paint seven "The current state file contains no company records" cards —
  // machine vocabulary aimed at a reader who cannot act on it, under a live tab
  // bar that implied there was something behind the other six tabs.
  function renderNoCompanies() {
    setAccess('empty');
    ui.viewStatus.innerHTML = pair('No companies this run', '本次更新没有公司');
  }

  // Item 3: partial coverage is disclosed in #ff-stat-coverage at glance and
  // the source limitations live in the Trace tab ("What to know about this
  // data"), so the band carries only the one notice nothing else shows: an
  // uncovered requested symbol.
  function renderNotice(target) {
    var headline = '';
    var details = '';

    if (state.unknownRequestedSymbol) {
      headline = pair(state.unknownRequestedSymbol + ' is not covered yet, so we are showing ' + state.symbol + '.',
        '尚未覆盖 ' + state.unknownRequestedSymbol + '，现显示 ' + state.symbol + '。');
    }
    if (!headline && !details) {
      ui.notice.hidden = true;
      ui.notice.innerHTML = '';
      return;
    }
    ui.notice.className = 'ff-data-notice';
    ui.notice.hidden = false;
    ui.notice.innerHTML = '<span class="ff-notice-icon" aria-hidden="true">i</span><div>' +
      (headline || pair('Coverage details are available.', '可查看覆盖范围详情。')) + details + '</div>';
  }

  function renderTopicOptions(findings) {
    var topics = [];
    findings.forEach(function (finding) {
      var topic = String(finding.topic || 'other');
      if (topics.indexOf(topic) === -1) topics.push(topic);
    });
    var current = topics.indexOf(state.topic) >= 0 ? state.topic : 'all';
    state.topic = current;
    var html = '<option value="all">' + (lang() === 'zh' ? '全部主题' : 'All topics') + '</option>';
    topics.sort().forEach(function (topic) {
      html += '<option value="' + esc(topic) + '">' + esc(topicText(topic, lang())) + '</option>';
    });
    ui.topic.innerHTML = html;
    ui.topic.value = current;
  }

  function filteredFindings() {
    return orderedFindings(company()).filter(function (finding) {
      var priorityMatch = state.priority === 'all' || finding.priority === state.priority;
      var topicMatch = state.topic === 'all' || String(finding.topic || 'other') === state.topic;
      return priorityMatch && topicMatch;
    });
  }

  function renderFindings() {
    var all = orderedFindings(company());
    var visible = filteredFindings();
    var counts = {
      all: all.length,
      high: all.filter(function (item) { return item.priority === 'high'; }).length,
      watch: all.filter(function (item) { return item.priority === 'watch'; }).length
    };
    Object.keys(counts).forEach(function (key) {
      var node = document.querySelector('[data-count-for="' + key + '"]');
      if (node) node.textContent = String(counts[key]);
    });
    Array.prototype.forEach.call(ui.priorityFilters.querySelectorAll('[data-priority]'), function (button) {
      var active = button.getAttribute('data-priority') === state.priority;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', active ? 'true' : 'false');
    });

    ui.filterSummary.innerHTML = pair(visible.length + ' of ' + all.length + (all.length === 1 ? ' signal' : ' signals'),
      '显示 ' + visible.length + ' / ' + all.length + ' 个信号');

    if (!visible.length) {
      var hasAny = all.length > 0;
      var target = company() || {};
      var coverage = target.coverage || {};
      var actionKey = (target.action || {}).key;
      var evaluable = numberValue(coverage.detectors_evaluable);
      var detectorTotal = numberValue(coverage.detectors_total);
      var coverageLimited = !hasAny && (
        actionKey === 'limited' || (evaluable != null && detectorTotal != null && evaluable < detectorTotal)
      );
      var coverageDetailEn = evaluable != null && detectorTotal != null
        ? 'Only ' + evaluable + ' of ' + detectorTotal + ' checks were evaluable; missing checks remain unknown.'
        : 'Some checks were not evaluable; missing checks remain unknown.';
      var coverageDetailZh = evaluable != null && detectorTotal != null
        ? '仅 ' + evaluable + ' / ' + detectorTotal + ' 项检查可评估；缺失检查仍为未知。'
        : '部分检查无法评估；缺失检查仍为未知。';
      ui.findings.innerHTML = emptyState(
        hasAny ? 'No findings match these filters' : coverageLimited ? 'Coverage incomplete' : 'No review prompt in covered checks',
        hasAny ? '没有符合筛选条件的发现' : coverageLimited ? '检查覆盖不完整' : '已覆盖检查暂无复核提示',
        hasAny ? 'Change the priority or topic filter.' : coverageLimited ? coverageDetailEn : 'This is not a clean-company verdict; inspect coverage and limitations in Sources.',
        hasAny ? '请调整优先级或主题筛选。' : coverageLimited ? coverageDetailZh : '这并非“公司无问题”的结论；请在证据链中查看覆盖范围与局限。',
        hasAny ? '↺' : coverageLimited ? '?' : '✓');
      if (!hasAny) {
        state.findingId = '';
        if (state.evidenceKind === 'finding') renderEvidence(null);
      }
      return;
    }

    var selectedVisible = visible.some(function (finding) { return String(finding.id) === String(state.findingId); });
    if (!selectedVisible) state.findingId = String(visible[0].id);

    ui.findings.innerHTML = visible.map(function (finding) {
      var priority = priorityInfo(finding.priority);
      var selected = String(finding.id) === String(state.findingId);
      var periodText = findingPeriodText(finding);
      return '<div role="listitem"><button type="button" class="ff-finding' + (selected ? ' is-selected' : '') + '"' +
        ' data-finding-id="' + esc(finding.id) + '" data-priority="' + esc(finding.priority || 'watch') + '"' +
        ' aria-current="' + (selected ? 'true' : 'false') + '" aria-controls="ff-evidence">' +
        '<span class="ff-priority-mark" aria-hidden="true">' + priority.icon + '</span>' +
        '<span class="ff-finding-copy"><span class="ff-finding-overline"><span class="ff-priority-label">' +
        pair(priority.en, priority.zh) + '</span><span aria-hidden="true">·</span><span>' + topicPair(finding.topic) + '</span></span>' +
        '<h3>' + fieldPair(finding, 'title', 'Untitled finding') + '</h3>' +
        '<span class="ff-finding-summary">' + findingSummaryHtml(finding, 'No summary supplied.') + '</span></span>' +
        '<span class="ff-finding-periods"><strong>' + esc(periodText) + '</strong>' +
        pair('Why this matters', '为什么重要') + ' <span aria-hidden="true">→</span></span></button></div>';
    }).join('');
    if (state.evidenceKind === 'finding') renderEvidence(selectedFinding());
  }

  function emptyState(titleEn, titleZh, copyEn, copyZh, mark) {
    return '<div class="ff-empty-state"><div><span class="ff-empty-mark" aria-hidden="true">' + esc(mark || '—') + '</span>' +
      '<h3>' + pair(titleEn, titleZh) + '</h3><p>' + pair(copyEn, copyZh) + '</p></div></div>';
  }

  // ── Source controls (§2, R3) ────────────────────────────────────────────
  // Every displayed number is a control into #ff-evidence on the exact
  // occurrence/version/span. With no recorded span the control renders the
  // explicit unavailable state — never a generic EDGAR browse fallback and
  // never an invented span (AM1).
  function spanBounds(value) {
    if (Array.isArray(value) && value.length >= 2) {
      var listStart = numberValue(value[0]);
      var listEnd = numberValue(value[1]);
      if (listStart != null && listEnd != null) return [Math.trunc(listStart), Math.trunc(listEnd)];
    }
    if (value && typeof value === 'object') {
      var start = numberValue(value.start != null ? value.start : value.char_start);
      var end = numberValue(value.end != null ? value.end : value.char_end);
      if (start != null && end != null) return [Math.trunc(start), Math.trunc(end)];
    }
    return null;
  }

  // §2.3.1 — financial query cell provenance.
  function controlFromQueryNode(node, compactText) {
    node = objectValue(node) || {};
    var provenance = objectValue(node.provenance) || {};
    var fact = objectValue(provenance.selected_raw_fact) || {};
    var bounds = spanBounds(fact.source_span);
    return {
      kind: 'cell',
      compactText: compactText,
      occurrenceId: String(fact.occurrence_id || ''),
      rootCellId: String(node.cell_id || node.root_cell_id || ''),
      snapshotId: String(node.snapshot_id || ''),
      accession: String(provenance.accession || ''),
      spanStart: bounds ? bounds[0] : null,
      spanEnd: bounds ? bounds[1] : null
    };
  }

  // §2.3.2 — statement cell receipt. The span is a mapping with start/char_start.
  function controlFromStatementCell(cell, compactText) {
    cell = objectValue(cell) || {};
    var receipt = objectValue(cell.source_receipt) || {};
    var bounds = spanBounds(receipt.source_span);
    return {
      kind: 'statement',
      compactText: compactText,
      occurrenceId: String(receipt.occurrence_id || cell.occurrence_id || ''),
      rootCellId: String(receipt.root_cell_id || cell.cell_id || ''),
      snapshotId: String(receipt.snapshot_id || ''),
      accession: String(receipt.accession || cell.accession || ''),
      spanStart: bounds ? bounds[0] : null,
      spanEnd: bounds ? bounds[1] : null
    };
  }

  // §2.3.3 — disclosure / redline receipts.
  function controlFromEvidenceReceipt(receipt, kind, compactText) {
    receipt = objectValue(receipt) || {};
    var bounds = spanBounds(receipt.source_span);
    return {
      kind: kind,
      compactText: compactText,
      occurrenceId: String(receipt.occurrence_id || receipt.block_id || ''),
      rootCellId: '',
      snapshotId: '',
      accession: String(receipt.accession || receipt.accession_number || ''),
      spanStart: bounds ? bounds[0] : null,
      spanEnd: bounds ? bounds[1] : null
    };
  }

  function spanOk(opts) {
    return opts.spanStart != null && opts.spanEnd != null &&
      String(opts.spanStart) !== '' && String(opts.spanEnd) !== '';
  }

  // §2.4 — frozen control markup. `inlineInButton` emits the same classes and
  // copy on a span: HTML forbids nesting a control button inside the card
  // buttons (findings, disclosures, redlines), and the card itself keeps the
  // select/open behaviour there.
  function sourceControlHtml(opts, inlineInButton) {
    opts = opts || {};
    var compact = esc(opts.compactText == null || opts.compactText === '' ? '—' : opts.compactText);
    if (!spanOk(opts)) {
      var tag = inlineInButton ? 'span' : 'button';
      var disabledAttrs = inlineInButton ? ' aria-disabled="true"' : ' disabled aria-disabled="true"';
      return '<' + tag + ' type="button" class="ff-source-control is-unavailable"' + disabledAttrs +
        ' data-tip-en="Source span unavailable" data-tip-zh="来源片段不可用">' +
        '<span class="ff-compact tnum">' + compact + '</span>' +
        '<span class="ff-source-unavail">' + pair('Source span unavailable', '来源片段不可用') + '</span></' + tag + '>';
    }
    return '<button type="button" class="ff-source-control"' +
      ' data-source-kind="' + esc(opts.kind || 'cell') + '"' +
      ' data-occurrence-id="' + esc(opts.occurrenceId || '') + '"' +
      ' data-root-cell-id="' + esc(opts.rootCellId || '') + '"' +
      ' data-snapshot-id="' + esc(opts.snapshotId || '') + '"' +
      ' data-accession="' + esc(opts.accession || '') + '"' +
      ' data-span-start="' + esc(String(opts.spanStart)) + '"' +
      ' data-span-end="' + esc(String(opts.spanEnd)) + '"' +
      ' aria-controls="ff-evidence"' +
      ' data-tip-en="Open the source span for this number" data-tip-zh="打开该数字的来源片段">' +
      '<span class="ff-compact tnum">' + compact + '</span></button>';
  }

  // §2.3.4 — a finding value with no attached occurrence is matched to a query
  // node by metric id plus period label; no match stays disabled (AM1).
  function queryNodeForValue(value) {
    var nodes = state.queryNodes;
    if (!Array.isArray(nodes) || !objectValue(value)) return null;
    var wantedKey = String(value.metric_id || value.key || '');
    var wantedPeriod = String(value.period_label || value.period || '');
    for (var index = 0; index < nodes.length; index += 1) {
      var node = objectValue(nodes[index]);
      if (!node) continue;
      if (wantedKey && String(node.metric_id || '') !== wantedKey) continue;
      if (wantedPeriod && String(node.period_label || node.period || '') !== wantedPeriod) continue;
      return node;
    }
    return null;
  }

  function valueControlOpts(value, which) {
    var node = queryNodeForValue(value);
    var text = which === 'prior' ? value.prior : which === 'delta' ? value.delta : value.current;
    var shown = which === 'delta' ? formatChange(text, value.format, lang()) : formatValue(text, value.format);
    if (node) {
      var control = controlFromQueryNode(node, shown);
      control.kind = 'finding';
      control.exactText = node.value == null ? '' : String(node.value);
      control.unit = node.unit || '';
      return control;
    }
    return { kind: 'finding', compactText: shown };
  }

  // The plain-word cell glossary (R7): one sentence per glance metric, no
  // detector jargon. The same sentences live in
  // docs/site_semantics/fundamental_forensics.md.
  var CELL_GLOSSARY = {
    revenue: ['Revenue is the money the company billed for its goods or services in the period.', '营收是公司在该期间因商品或服务而开票的收入。'],
    gross_profit: ['Gross profit is revenue minus the direct cost of producing what was sold.', '毛利润是营收减去直接生产成本后的金额。'],
    accounts_receivable_net: ['Receivables are amounts customers owe the company and have not yet paid.', '应收账款是客户尚未支付给公司的款项。'],
    inventory_net: ['Inventory is the value of goods made or bought and not yet sold.', '存货是已生产或采购但尚未售出的商品价值。'],
    net_cash_from_operating_activities: ['Operating cash flow is the cash the core business generated or consumed in the period.', '经营现金流是核心业务在该期间产生或消耗的现金。'],
    capital_expenditures: ['Capital expenditure is the cash spent on long-lived assets such as plants and equipment.', '资本开支是用于厂房、设备等长期资产的现金支出。'],
    operating_income_loss: ['Operating income is profit from the core business before interest and taxes.', '营业利润是核心业务在扣除利息和税费前的利润。'],
    net_income_loss: ['Net income is the profit remaining after all expenses and taxes.', '净利润是扣除全部费用与税负后剩余的利润。'],
    contract_liabilities: ['Contract liabilities is cash customers paid in advance for goods or services not yet delivered.', '合同负债是客户已预付、但公司尚未交付商品或服务的现金。']
  };

  var METRIC_ID_BY_KEY = {
    revenue: 'revenue',
    gross_profit: 'gross_profit',
    receivables: 'accounts_receivable_net',
    inventory: 'inventory_net',
    cfo: 'net_cash_from_operating_activities',
    capex: 'capital_expenditures',
    op_income: 'operating_income_loss',
    ni: 'net_income_loss'
  };

  function glossarySentence(metricId) {
    var entry = CELL_GLOSSARY[String(metricId || '')];
    return entry ? pair(entry[0], entry[1]) : pair(
      'This is a value the company reported in its filing; open the source span to read it in place.',
      '这是公司在财报中披露的数值；打开来源片段可在原文中查看。'
    );
  }

  // §2.5 — activating a control pushes one drawer frame (§6.2) and renders
  // the cell evidence view: plain-word title, exact API bytes, compact
  // secondary, bounded excerpt, technical ids folded into a details block.
  function activateSourceControl(control) {
    if (!control || control.disabled) return;
    state.lastFocus = control;
    state.evidenceKind = 'cell';
    state.cellEvidence = cellEvidenceFromControl(control);
    writeUrl(true, {
      drawer: true,
      occ: control.getAttribute('data-occurrence-id') || '',
      cell: control.getAttribute('data-root-cell-id') || '',
      snap: control.getAttribute('data-snapshot-id') || '',
      span: (control.getAttribute('data-span-start') || '') + '-' + (control.getAttribute('data-span-end') || '')
    });
    renderCellEvidence(state.cellEvidence);
    openAnalysisDrawer();
  }

  function metricLabelById(metricId) {
    var wanted = String(metricId || '');
    for (var index = 0; index < METRICS.length; index += 1) {
      if (METRIC_ID_BY_KEY[METRICS[index].key] === wanted) return pair(METRICS[index].en, METRICS[index].zh);
    }
    return wanted ? pair(prettify(wanted), prettify(wanted)) : '';
  }

  function cellEvidenceFromControl(control) {
    var cell = {
      kind: control.getAttribute('data-source-kind') || 'cell',
      occurrenceId: control.getAttribute('data-occurrence-id') || '',
      rootCellId: control.getAttribute('data-root-cell-id') || '',
      snapshotId: control.getAttribute('data-snapshot-id') || '',
      accession: control.getAttribute('data-accession') || '',
      spanStart: control.getAttribute('data-span-start') || '',
      spanEnd: control.getAttribute('data-span-end') || '',
      compactText: control.querySelector('.ff-compact') ? control.querySelector('.ff-compact').textContent : '',
      metricId: '',
      titlePair: '',
      exactText: '',
      unit: '',
      excerpt: ''
    };
    // Exact facts attach only when this control backs onto a query node whose
    // value is canonical decimal text; a JSON number is a contract break and
    // renders unavailable rather than Number()-ed (A38 / AM1).
    var nodes = Array.isArray(state.queryNodes) ? state.queryNodes : [];
    for (var index = 0; index < nodes.length; index += 1) {
      var node = objectValue(nodes[index]);
      if (!node) continue;
      var fact = objectValue(objectValue(node.provenance) && objectValue(node.provenance).selected_raw_fact) || {};
      var occurrenceMatch = cell.occurrenceId && String(fact.occurrence_id || '') === cell.occurrenceId;
      var cellMatch = cell.rootCellId && String(node.cell_id || node.root_cell_id || '') === cell.rootCellId;
      if (!occurrenceMatch && !cellMatch) continue;
      cell.metricId = String(node.metric_id || '');
      cell.titlePair = metricLabelById(cell.metricId);
      cell.exactText = typeof node.value === 'string' ? node.value : '';
      cell.unit = node.unit == null ? '' : String(node.unit);
      cell.excerpt = String(node.display_excerpt || node.source_excerpt || '').trim();
      break;
    }
    // Statement-tree cells resolve against the flat cell list the tree
    // renderer collected; the as-reported label is the plain-word title.
    if (!cell.titlePair) {
      var statementCells = Array.isArray(state.statementCells) ? state.statementCells : [];
      for (var cellIndex = 0; cellIndex < statementCells.length; cellIndex += 1) {
        var entry = statementCells[cellIndex];
        var byOccurrence = cell.occurrenceId && entry.occurrenceId === cell.occurrenceId;
        var byRoot = cell.rootCellId && entry.rootCellId === cell.rootCellId;
        if (!byOccurrence && !byRoot) continue;
        cell.metricId = entry.metricId;
        cell.titlePair = entry.label ? pair(entry.label, entry.label) : '';
        cell.exactText = entry.value;
        cell.unit = entry.unit;
        break;
      }
    }
    // The revisions package supplies the three vintages verbatim for the
    // drawer; glance compacts, the drawer prints bytes.
    cell.revisionsRow = revisionsRowFor(cell.metricId);
    return cell;
  }

  // ── Cutoff + revisions panel (§3, R4) ───────────────────────────────────
  // One as-of line drives both PIT clocks; a picked day expands to
  // {date}T23:59:59Z on both, and Latest resolves a real cutoff below.

  // The health generation for the company currently selected — null when the
  // answer named no generation or belongs to another issuer (PF-3: pointers
  // are per issuer, so a foreign generation is never this desk's cutoff).
  function selectedGeneration() {
    var health = state.health || {};
    var generation = objectValue(health.generation);
    var target = company();
    if (!generation || !generation.id) return null;
    // PF r2 (m2): an absent identifier on either side is no match — two
    // empty strings never make another issuer's generation this desk's.
    if (!target || !target.entity_id || !generation.entity_id) return null;
    if (String(generation.entity_id) !== String(target.entity_id)) return null;
    return generation;
  }

  // PF-3 — the Latest cutoff. recorded_at is the LATEST instant among the
  // present values of {clocks.composed_state_at, the selected issuer's
  // generation admitted_at (production mode only), clocks.broad_source_at};
  // instants are compared parsed and the winner's ORIGINAL string is emitted.
  // source_snapshot_at is broad_source_at when present, else recorded_at. An
  // empty result means no lawful cutoff exists and the honest no-clocks copy
  // shows. Shared by policyClocks (Latest branch) and reResolveSavedView.
  // PF r1 (R6): an UNPARSEABLE value counts as absent — including
  // broad_source_at in the source_snapshot_at seat, which then falls back to
  // recorded_at. Instants compare at FULL precision (fractional seconds are
  // parsed here beyond Date.parse's milliseconds); on an exact tie the
  // preference order is the generation admitted_at, then
  // composed_state_at, then broad_source_at.
  function parseInstantParts(value) {
    if (typeof value !== 'string') return null;
    var match = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:?\d{2})?$/.exec(value);
    if (!match) return null;
    var base = Date.parse(
      match[1] + '-' + match[2] + '-' + match[3] + 'T' +
      match[4] + ':' + match[5] + ':' + match[6] + (match[8] || 'Z')
    );
    if (!Number.isFinite(base)) return null;
    var fraction = match[7] || '';
    while (fraction.length < 9) fraction += '0';
    return { ms: base, fraction: fraction };
  }

  function instantAfter(candidate, winner) {
    if (candidate.ms !== winner.ms) return candidate.ms > winner.ms;
    return candidate.fraction > winner.fraction;
  }

  function latestCutoffs() {
    var clocks = (state.health && state.health.clocks) || {};
    var generation = state.datasetMode === 'production' ? selectedGeneration() : null;
    // Tie preference (R6) is the iteration order: admitted_at first, then
    // composed_state_at, then broad_source_at; only a strictly later instant
    // replaces the winner.
    var candidates = [
      generation && generation.admitted_at ? String(generation.admitted_at) : '',
      clocks.composed_state_at ? String(clocks.composed_state_at) : '',
      clocks.broad_source_at ? String(clocks.broad_source_at) : ''
    ];
    var winner = '';
    var winnerParts = null;
    candidates.forEach(function (value) {
      if (!value) return;
      var parts = parseInstantParts(value);
      if (!parts) return;
      if (winnerParts && !instantAfter(parts, winnerParts)) return;
      winner = value;
      winnerParts = parts;
    });
    if (!winner) return { source_snapshot_at: '', recorded_at: '' };
    var broadParts = clocks.broad_source_at ? parseInstantParts(String(clocks.broad_source_at)) : null;
    return {
      source_snapshot_at: broadParts ? String(clocks.broad_source_at) : winner,
      recorded_at: winner
    };
  }

  function policyClocks() {
    if (state.asOfDate) {
      return { source_snapshot_at: state.asOfDate + 'T23:59:59Z', recorded_at: state.asOfDate + 'T23:59:59Z' };
    }
    return latestCutoffs();
  }

  function queryMetricIds() {
    var ids = [];
    METRICS.forEach(function (metric) {
      // contract_liabilities is not in the S1 core 40: state table only.
      if (metric.key === 'contract_liabilities') return;
      if (METRIC_ID_BY_KEY[metric.key]) ids.push(METRIC_ID_BY_KEY[metric.key]);
    });
    return ids;
  }

  // PF-1: the period identity the server's admission uses — a mirror of
  // period_semantic_key (financial_intelligence_packet.py) for the
  // {kind: 'duration', start, end, label} objects this page sends: the fiscal
  // fields ride at their wire defaults (none/unknown), so the key is exactly
  // kind|start|end. Two columns with this same key are ONE period to the API.
  function statementPeriodKey(column) {
    return ['duration', String(column.start), String(column.end), 0, 0, 'unknown', 0, 0].join('|');
  }

  // Periods on the wire carry exactly {kind, start, end, label}. A state
  // period without a start is skipped — the panel then says so; a start is
  // never invented (AM1).
  function queryPeriods(target) {
    var periods = [];
    if (state.statementColumns.length) {
      state.statementColumns.forEach(function (column) {
        if (column && column.start && column.end) {
          periods.push({ kind: 'duration', start: column.start, end: column.end, label: column.label });
        }
      });
      return periods;
    }
    (Array.isArray(target.periods) ? target.periods : []).forEach(function (period) {
      if (!objectValue(period) || !period.start || !period.end) return;
      periods.push({ kind: 'duration', start: String(period.start), end: String(period.end), label: periodLabel(period) });
    });
    return periods;
  }

  function buildQueryBody(selection) {
    var target = company() || {};
    return {
      schema: 'fundamental_forensics.financial_query_request/v1',
      entity_id: String(target.entity_id || ''),
      policy: Object.assign({ selection: selection || state.policy || 'latest_known_as_of' }, policyClocks()),
      metric_ids: queryMetricIds(),
      periods: queryPeriods(target)
    };
  }

  function revisionsRequestBody(latestBody) {
    var body = Object.assign({}, latestBody, {
      schema: 'fundamental_forensics.financial_revision_request/v1'
    });
    body.policy = Object.assign({}, latestBody.policy, { selection: 'latest_known_as_of' });
    return body;
  }

  function financialPost(url, body, meta) {
    return withAuth({ 'Content-Type': 'application/json', Accept: 'application/json' })
      .then(function (headers) {
        return fetch(url, {
          method: 'POST',
          headers: headers,
          credentials: 'same-origin',
          cache: 'no-store',
          body: JSON.stringify(body)
        });
      })
      .then(function (response) {
        if (!response.ok) {
          var failure = new Error('Financial request failed');
          failure.status = response.status;
          // PF-2: attach the server's parsed JSON detail string so the panel
          // can tell admission refusals apart — best-effort: a body that is
          // not JSON leaves detail empty, and parsing never throws a second
          // error. The detail drives copy choice only; it is never rendered.
          return response.text().then(function (text) {
            try {
              var parsed = JSON.parse(text);
              if (parsed && typeof parsed.detail === 'string') failure.detail = parsed.detail;
            } catch (_parseError) { /* a non-JSON body carries no detail */ }
            throw failure;
          }, function () { throw failure; });
        }
        // A38: the adapter-byte equality header is verified against the raw
        // body before anything parses; a missing or mismatched digest is
        // treated as a 503 and no number renders.
        var claimed = String(response.headers.get('X-FIF-Response-SHA256') || '').toLowerCase();
        // X2-s: hand the verified digest to the caller (saved_against) without
        // touching the envelope — meta is an optional sink, never read back.
        if (meta) meta.responseSha256 = claimed;
        return response.arrayBuffer().then(function (buffer) {
          return sha256Hex(buffer).then(function (actual) {
            if (!claimed || !actual || actual !== claimed) {
              var mismatch = new Error('Financial response digest mismatch');
              mismatch.status = 503;
              throw mismatch;
            }
            return JSON.parse(new TextDecoder().decode(buffer));
          });
        });
      });
  }

  function sha256Hex(buffer) {
    if (!(window.crypto && window.crypto.subtle && typeof window.crypto.subtle.digest === 'function')) {
      return Promise.resolve('');
    }
    return window.crypto.subtle.digest('SHA-256', buffer).then(function (digest) {
      var bytes = new Uint8Array(digest);
      var hex = '';
      for (var index = 0; index < bytes.length; index += 1) {
        hex += (bytes[index] < 16 ? '0' : '') + bytes[index].toString(16);
      }
      return hex;
    });
  }

  function queryNodesFrom(payload) {
    var receipt = objectValue(payload && payload.receipt) || {};
    return Array.isArray(receipt.nodes) ? receipt.nodes.filter(objectValue) : [];
  }

  function revisionsRowsFrom(payload) {
    return Array.isArray(payload && payload.revisions) ? payload.revisions.filter(objectValue) : [];
  }

  function resetFinancialState() {
    state.financialToken += 1;
    state.financial = { phase: 'idle' };
    state.queryNodes = null;
    state.statementColumns = [];
  }

  function ensureFinancialData() {
    if (state.tab !== 'compare') return;
    var target = company();
    if (!target) return;
    // PF r2 (M1): every re-evaluation supersedes any compare chain still in
    // flight, so an early answer below (earlier day, no records, health
    // failure, …) is never overwritten by the reply to a request the desk no
    // longer stands behind.
    var token = state.financialToken + 1;
    state.financialToken = token;
    // X2-s: a restored PINNED view re-POSTs its stored request bytes verbatim
    // on every leg — the latest-known leg too is the STORED bytes with only
    // policy.selection switched to latest_known_as_of, so a pinned view saved
    // under as_reported still compares like against like; without a pinned
    // view the desk builds each leg exactly as before.
    var pinnedBody = activePinnedRequest();
    var latestBody = pinnedBody ? pinnedVariant('latest_known_as_of') : buildQueryBody('latest_known_as_of');
    if (!latestBody.entity_id) {
      state.financial = { phase: 'no-entity' };
      renderRevisions();
      return;
    }
    // PF-3 / PF r1 (R1): the cutoff policy reads the health answer FOR THE
    // SELECTED ISSUER, and only the answer that is still CURRENT — its seq is
    // the newest issued one, exactly the acceptance rule that recorded it. A
    // compare chain that arrives before that answer — including right after
    // a company switch, or a re-select that re-issued health after a failure,
    // while the previous answer is still on the desk — parks in loading and
    // is re-driven by applyHealth; a cutoff is never built from another
    // issuer's clocks or a superseded answer.
    var answer = state.healthAnswer;
    if (!answer ||
        String(answer.entity_id || '') !== String(target.entity_id || '') ||
        answer.seq !== state.healthSeq) {
      state.financial = { phase: 'loading', awaitingHealth: true };
      renderRevisions();
      return;
    }
    // PF r1 (R2): a failed health fetch is an availability fact in ANY mode —
    // the honest 503 copy with its Retry button, never a guess and never a
    // query.
    if (!answer.ok) {
      // PFM r1 (item 3): an access failure (401/403) is NOT an outage — the
      // desk was already routed through showLoadError in the health catch,
      // so the revisions panel must not show either 503 copy and no
      // financial query may be issued for an unauthenticated or unentitled
      // reader. The financial chain's 401/403 catch above already follows
      // this same shape.
      if (answer.status === 401 || answer.status === 403) {
        return;
      }
      state.financial = { phase: 'error', healthRetry: true };
      renderRevisions();
      return;
    }
    // PF-4 / PF r1 (R2): in production mode the names-only pointer header
    // tells the three cases apart. 'none': the store was built and this
    // issuer genuinely has no published records — no query can be honest.
    // 'admitted' with a generation for this issuer: proceed as before.
    // Anything else — a missing pointer header, 'unavailable' (the store is
    // down or damaged), or 'admitted' without a generation — is a temporary
    // availability failure, not "not published": the 503 copy with Retry.
    var generation = state.datasetMode === 'production' ? selectedGeneration() : null;
    if (state.datasetMode === 'production') {
      if (answer.pointer === 'none') {
        state.financial = { phase: 'no-records' };
        renderRevisions();
        return;
      }
      if (answer.pointer !== 'admitted' || !generation) {
        state.financial = { phase: 'error', healthRetry: true };
        renderRevisions();
        return;
      }
    }
    // PF-4: a picked day whose end-of-day cutoff precedes the generation's
    // admission cannot be served by this store (the API's own floor answers
    // 503); the page says so instead of sending a query that cannot succeed.
    // This fact is knowable from the day alone, so it precedes the period
    // check — a state without period starts must not mask it.
    if (state.asOfDate && generation) {
      var dayEnd = Date.parse(state.asOfDate + 'T23:59:59Z');
      var admitted = Date.parse(generation.admitted_at);
      if (Number.isFinite(dayEnd) && Number.isFinite(admitted) && dayEnd < admitted) {
        state.financial = { phase: 'earlier', admittedAt: String(generation.admitted_at) };
        renderRevisions();
        return;
      }
    }
    if (!latestBody.periods.length) {
      state.financial = { phase: 'no-periods' };
      renderRevisions();
      return;
    }
    if (!latestBody.policy.source_snapshot_at || !latestBody.policy.recorded_at) {
      state.financial = { phase: 'no-clocks' };
      renderRevisions();
      return;
    }
    // X2-s r1: the exported body is the pinned bytes while the pinned view is
    // active, otherwise the DESK's own selection (buildQueryBody() with no
    // argument) — never the forced latest_known_as_of leg above.
    state.financial = { phase: 'loading', queryBody: pinnedBody || buildQueryBody() };
    renderRevisions();
    var latestMeta = {};
    Promise.all([
      financialPost(FINANCIAL_QUERY_URL, pinnedBody ? pinnedVariant('as_reported') : buildQueryBody('as_reported')),
      financialPost(FINANCIAL_QUERY_URL, latestBody, latestMeta),
      financialPost(FINANCIAL_QUERY_URL, pinnedBody ? pinnedVariant('latest_restated') : buildQueryBody('latest_restated')),
      financialPost(FINANCIAL_REVISIONS_URL, revisionsRequestBody(latestBody))
    ]).then(function (answers) {
      if (token !== state.financialToken) return;
      var delivery = objectValue(answers[1] && answers[1].delivery) || {};
      state.financial = {
        phase: 'ready',
        asReported: queryNodesFrom(answers[0]),
        latest: queryNodesFrom(answers[1]),
        restated: queryNodesFrom(answers[2]),
        revisions: revisionsRowsFrom(answers[3]),
        receiptPolicy: objectValue(objectValue(answers[1] && answers[1].receipt) && objectValue(answers[1].receipt).policy) || {},
        queryBody: pinnedBody || buildQueryBody(),
        // X2-s: the verified digest and the dataset generation the answer was
        // served from — refs for saved_against, never values.
        responseSha256: latestMeta.responseSha256 || '',
        generationId: String(delivery.dataset_generation_id || '')
      };
      state.queryNodes = state.financial.latest;
      renderRevisions();
      // X2-b+c r3 R3-3b: reconcile FIRST — a view another tab unpinned,
      // changed or deleted while this tab's pinned fetch was in flight must
      // be refused before the backfill can write anything against it.
      reconcileSavedActive();
      backfillSavedAgainst();
      renderSavedUI();
    }).catch(function (error) {
      if (token !== state.financialToken) return;
      if (error && (error.status === 401 || error.status === 403)) {
        showLoadError(error);
        return;
      }
      state.financial = {
        phase: 'error',
        errorStatus: error && error.status,
        // PF-2: the server's detail string (when the body was JSON) drives
        // the copy choice; it is never rendered.
        errorDetail: (error && typeof error.detail === 'string') ? error.detail : ''
      };
      renderRevisions();
    });
  }

  function revisionNodeFor(nodes, metricId) {
    for (var index = 0; index < nodes.length; index += 1) {
      if (String(nodes[index].metric_id || '') === String(metricId)) return nodes[index];
    }
    return null;
  }

  function revisionsRowFor(metricId) {
    var rows = state.financial && Array.isArray(state.financial.revisions) ? state.financial.revisions : [];
    for (var index = 0; index < rows.length; index += 1) {
      if (String(rows[index].metric_id || '') === String(metricId)) return rows[index];
    }
    return null;
  }

  function absenceCell(copyEn, copyZh) {
    return '<span class="ff-revisions-absence">' + pair(copyEn, copyZh) + '</span>';
  }

  function revisionControlCell(nodes, metricId) {
    var node = revisionNodeFor(nodes, metricId);
    if (!node) return absenceCell('No value at this cutoff', '该截止日无此值');
    if (String(node.state || '') === 'missing') return absenceCell('No value at this cutoff', '该截止日无此值');
    if (String(node.state || '') === 'not_evaluable') return absenceCell('Cannot evaluate', '无法评估');
    var exact = typeof node.value === 'string' ? node.value : '';
    if (!exact) return absenceCell('No value at this cutoff', '该截止日无此值');
    var control = controlFromQueryNode(node, formatValue(node.value, 'currency'));
    return sourceControlHtml(control);
  }

  // §3.3 — three columns map to the three policies; a restated value that
  // differs from its root tints the column (dark fill / light hairline+fill).
  function renderRevisions() {
    var host = byId('ff-revisions-table');
    if (!host) return;
    var financial = state.financial || { phase: 'idle' };
    var header = '<tr><th>' + pair('Metric / 指标', 'Metric / 指标') + '</th>' +
      '<th>' + pair('Original reported', '原始披露') + '</th>' +
      '<th>' + pair('Latest as of cutoff', '截止时点最新值') + '</th>' +
      '<th>' + pair('Restated', '重述后') + '</th></tr>';
    if (financial.phase === 'loading') {
      host.innerHTML = '<div class="ff-loading" role="status"><span class="ff-loading-dot" aria-hidden="true"></span>' +
        pair('Loading revisions…', '正在载入重述对照…') + '</div>';
      return;
    }
    if (financial.phase === 'no-entity' ||
        (financial.phase === 'error' && financial.errorStatus === 400 &&
         financial.errorDetail === 'unknown entity')) {
      host.innerHTML = emptyState(
        'Issuer identity unavailable', '发行人标识不可用',
        'The desk cannot query this issuer yet, so no vintage is shown. Nothing is guessed from the ticker.',
        '暂无法查询该发行人，因此不显示任何版本；不会从股票代码推测发行人标识。', '—'
      );
      return;
    }
    // PF-2: any other 400 is a refusal for this company and date, not an
    // identity failure — the copy says what happened and nothing raw leaks.
    if (financial.phase === 'error' && financial.errorStatus === 400) {
      host.innerHTML = emptyState(
        'This view could not be evaluated', '无法评估此视图',
        'The request for this company and date was refused, so nothing is shown. Nothing is guessed.',
        '该公司与日期的请求被拒绝，因此不显示任何内容。我们不做猜测。', '—'
      );
      return;
    }
    // PF-2: no recorded cutoff is a build-time fact, not an identity failure.
    if (financial.phase === 'no-clocks') {
      host.innerHTML = emptyState(
        'No recorded cutoff yet', '尚无记录截止时点',
        'The desk has no recorded build time to read from yet, so no vintage is shown. Check back after the next build.',
        '本页尚无可读取的记录构建时间，因此不显示任何版本。请在下次构建后再查看。', '—'
      );
      return;
    }
    // PF-4: production mode with no published generation for this issuer.
    if (financial.phase === 'no-records') {
      host.innerHTML = emptyState(
        'No filing records published yet', '尚未发布申报记录',
        'We have not published filing records for this company yet, so no vintage is shown.',
        '我们尚未发布该公司的申报记录，因此不显示任何版本。', '—'
      );
      return;
    }
    // PF-4: a picked day earlier than the issuer's last publication.
    if (financial.phase === 'earlier') {
      var publishedDay = formatDate(financial.admittedAt || '');
      host.innerHTML = emptyState(
        'Earlier dates not available', '无更早日期',
        'This company\'s filing records were last published on ' + publishedDay + '. Pick that day or later, or use Latest.',
        '该公司的申报记录最近一次发布于' + publishedDay + '。请选择该日或之后的日期，或使用“最新”。', '—'
      );
      return;
    }
    if (financial.phase === 'no-periods') {
      host.innerHTML = emptyState(
        'Period start unavailable', '期间起始日不可用',
        'The state does not carry a period start date for this issuer, so no cutoff query can be built.',
        '状态数据中没有该发行人的期间起始日，因此无法构建截止日查询。', '—'
      );
      return;
    }
    // PF r2 (m3): a failed health check is not the revisions service, so its
    // copy names no service; a failed compare chain keeps the revisions copy.
    if (financial.phase === 'error' && financial.healthRetry) {
      host.innerHTML = emptyState(
        'Data temporarily unavailable', '数据暂不可用',
        'The desk could not confirm which filing records are available right now. Try again in a moment.',
        '本页暂时无法确认可用的申报记录，请稍后再试。', '↺'
      ) + '<div class="ff-revisions-retry"><button type="button" data-financial-retry="1">' + pair('Retry', '重试') + '</button></div>';
      return;
    }
    if (financial.phase === 'error') {
      host.innerHTML = emptyState(
        'Revisions temporarily unavailable', '重述服务暂不可用',
        'The revisions service did not answer with verifiable bytes. Try again in a moment.',
        '重述服务未返回可校验的数据，请稍后再试。', '↺'
      ) + '<div class="ff-revisions-retry"><button type="button" data-financial-retry="1">' + pair('Retry', '重试') + '</button></div>';
      return;
    }
    if (financial.phase !== 'ready') {
      host.innerHTML = '';
      return;
    }
    var hasRevision = Array.isArray(financial.revisions) && financial.revisions.length > 0;
    var rows = queryMetricIds().map(function (metricId) {
      var restatedCell = hasRevision
        ? revisionControlCell(financial.restated, metricId)
        : absenceCell('No revision in this package', '本数据包中无重述');
      var revisionRow = revisionsRowFor(metricId);
      var tinted = !!(revisionRow && revisionRow.revised_value !== revisionRow.root_value);
      return '<tr' + (tinted ? ' class="is-restated"' : '') + '><td data-label-en="Metric" data-label-zh="指标">' + metricLabelById(metricId) + '</td>' +
        '<td data-label-en="Original reported" data-label-zh="原始披露">' + revisionControlCell(financial.asReported, metricId) + '</td>' +
        '<td data-label-en="Latest as of cutoff" data-label-zh="截止时点最新值">' + revisionControlCell(financial.latest, metricId) + '</td>' +
        '<td data-label-en="Restated" data-label-zh="重述后">' + restatedCell + '</td></tr>';
    }).join('');
    var policy = financial.receiptPolicy || {};
    var echo = policy.source_snapshot_at || policy.recorded_at
      ? '<p class="ff-revisions-echo">' + pair(
          'Cutoff ' + formatDate(policy.source_snapshot_at || '') + ' · ' + String(policy.selection || 'latest_known_as_of'),
          '截止 ' + formatDate(policy.source_snapshot_at || '') + ' · ' + String(policy.selection || 'latest_known_as_of')
        ) + '</p>'
      : '';
    host.innerHTML = echo + '<div class="ff-table-wrap"><table class="ff-table ff-revisions-table"><thead>' + header +
      '</thead><tbody>' + rows + '</tbody></table></div>';
  }

  function setAsofControlsFromState() {
    if (!ui.asofLatest || !ui.asofInput) return;
    var latestActive = !state.asOfDate;
    ui.asofLatest.classList.toggle('is-active', latestActive);
    ui.asofLatest.setAttribute('aria-pressed', latestActive ? 'true' : 'false');
    ui.asofInput.value = state.asOfDate || '';
    ui.asofInput.setAttribute('lang', lang() === 'zh' ? 'zh-CN' : 'en');
    // §3.1 — with no health clocks and no picked day there is no lawful
    // cutoff, so the control is disabled rather than guessing one.
    var clocks = (state.health && state.health.clocks) || {};
    var clocksKnown = !!(clocks.broad_source_at || clocks.composed_state_at);
    var disabled = !state.asOfDate && !clocksKnown;
    ui.asofLatest.disabled = disabled;
    ui.asofInput.disabled = disabled;
    // PF-4: in production mode with a known generation for the selected
    // issuer, no day before the last publication can be served, so the
    // picker's min is that day. It clears when the company changes or the
    // generation is unknown (or the mode is golden/absent).
    var generation = state.datasetMode === 'production' ? selectedGeneration() : null;
    // PF r2 (n1): the minimum is the admission's UTC day, the same day the
    // 'earlier' check measures against ({day}T23:59:59Z), whatever offset the
    // header carried.
    var admittedMs = generation && generation.admitted_at ? Date.parse(generation.admitted_at) : NaN;
    if (Number.isFinite(admittedMs)) {
      ui.asofInput.setAttribute('min', new Date(admittedMs).toISOString().slice(0, 10));
    } else {
      ui.asofInput.removeAttribute('min');
    }
  }

  // ── Statement tree (§3.5 statements POST, spec row 6) ───────────────────
  // Accession comes from the disclosure layer's current filing or the query
  // provenance — never guessed from a ticker or a period label.
  function currentAccession() {
    var current = disclosureDocuments(company()).find(function (document) {
      return document._filing_role === 'current';
    });
    if (current && (current.accession || current.accession_number)) {
      return String(current.accession || current.accession_number);
    }
    var finding = selectedDisclosureFinding();
    if (finding && finding.current_accession) return String(finding.current_accession);
    var nodes = Array.isArray(state.queryNodes) ? state.queryNodes : [];
    for (var index = 0; index < nodes.length; index += 1) {
      var provenance = objectValue(nodes[index] && nodes[index].provenance) || {};
      if (provenance.accession) return String(provenance.accession);
    }
    return '';
  }

  function resetStatementsState() {
    state.statements = { phase: 'idle' };
    state.statementCells = [];
    state.statementColumns = [];
  }

  function ensureStatements() {
    if (state.tab !== 'statements') return;
    var target = company();
    if (!target) return;
    if (state.statements.phase === 'loading' || state.statements.phase === 'ready') return;
    var entityId = String(target.entity_id || '');
    var accession = currentAccession();
    if (!entityId || !accession) {
      state.statements = { phase: 'unavailable' };
      renderStatementTree();
      return;
    }
    var token = state.financialToken + 1;
    state.financialToken = token;
    state.statements = { phase: 'loading' };
    renderStatementTree();
    financialPost(FINANCIAL_STATEMENTS_URL, {
      schema: 'fundamental_forensics.financial_statement_request/v1',
      entity_id: entityId,
      accession: accession
    }).then(function (payload) {
      if (token !== state.financialToken) return;
      var statements = Array.isArray(payload && payload.statements) ? payload.statements.filter(objectValue) : [];
      state.statements = { phase: statements.length ? 'ready' : 'empty', statements: statements };
      state.statementCells = [];
      var columns = [];
      // PF-1: every statement repeats its comparative periods, so columns are
      // de-duplicated by the server's own period identity before they are
      // stored — exactly the semantic key the query admission uses
      // (period_semantic_key: for the {kind, start, end, label} objects this
      // page sends, kind/start/end with the fiscal fields at their wire
      // defaults). The FIRST column seen for a key wins, label included, and
      // first-seen order is kept; without this the revisions request repeats
      // a period and the API refuses it as a duplicate.
      var seenPeriods = {};
      statements.forEach(function (statement) {
        (Array.isArray(statement.columns) ? statement.columns : []).forEach(function (column) {
          if (objectValue(column) && column.start && column.end) {
            var key = statementPeriodKey(column);
            if (seenPeriods[key]) return;
            seenPeriods[key] = true;
            columns.push({ label: column.label, start: column.start, end: column.end });
          }
        });
      });
      state.statementColumns = columns;
      renderStatementTree();
    }).catch(function (error) {
      if (token !== state.financialToken) return;
      if (error && (error.status === 401 || error.status === 403)) {
        showLoadError(error);
        return;
      }
      state.statements = { phase: 'error' };
      renderStatementTree();
    });
  }

  function statementCellControl(cell, row) {
    cell = objectValue(cell) || {};
    var quality = String(cell.quality_state || '');
    var exact = typeof cell.value === 'string' ? cell.value : '';
    // A38/AM1: exact bytes render only as canonical decimal text; a JSON
    // number or a non-available quality state renders the disabled control.
    if (quality !== 'available' || !exact) {
      return sourceControlHtml({ kind: 'statement' });
    }
    var control = controlFromStatementCell(cell, formatValue(cell.value, 'currency'));
    control.metricId = String(row.standardized_metric_id || '');
    state.statementCells.push({
      occurrenceId: control.occurrenceId,
      rootCellId: control.rootCellId,
      label: String(row.as_reported_label || ''),
      metricId: control.metricId,
      value: exact,
      unit: cell.unit == null ? '' : String(cell.unit),
      accession: control.accession
    });
    return sourceControlHtml(control);
  }

  var STATEMENT_WITHHELD_COPY = pair(
    'We couldn\'t rebuild this statement line by line from this filing yet, so it isn\'t shown here.',
    '我们暂时无法从该财报逐行重建此报表，因此此处未显示。'
  );
  var ACCESSION_ALL_REFUSED_COPY = pair(
    'We couldn\'t rebuild this filing\'s statements line by line yet. The normalized table below still covers its figures.',
    '我们暂时无法逐行重建该财报的报表。下方的标准化表格仍涵盖其数据。'
  );

  function statementTypeHeading(statement) {
    var kind = String(statement.statement_type || '');
    if (kind === 'income_statement') return pair('Income statement', '利润表');
    if (kind === 'balance_sheet') return pair('Balance sheet', '资产负债表');
    if (kind === 'cash_flow') return pair('Cash flow statement', '现金流量表');
    return pair(statement.title || 'Statement', statement.title || '报表');
  }

  function withheldStatementBlock(statement) {
    return '<section class="ff-statement-block ff-statement-block--withheld"><h3>' +
      statementTypeHeading(statement) + '</h3><p class="ff-statement-withheld-copy">' +
      STATEMENT_WITHHELD_COPY + '</p></section>';
  }

  // S0 as-reported labels lead; spans come from each cell's source_receipt.
  function renderStatementTree() {
    if (!ui.statements) return;
    var statements = state.statements || { phase: 'idle' };
    if (statements.phase === 'idle' || statements.phase === 'unavailable' || statements.phase === 'error' || statements.phase === 'empty') {
      var target = company() || {};
      renderStatements(target);
      var reason = statements.phase === 'unavailable'
        ? pair('Issuer identity or filing accession unavailable, so the as-reported statement tree cannot be opened. The normalized state table below is unchanged.',
               '发行人标识或财报文件编号不可用，因此无法打开按披露原样的报表树；下方标准化状态表保持不变。')
        : statements.phase === 'error'
          ? pair('The statement tree is temporarily unavailable, so the normalized state table is shown unchanged.',
                 '报表树暂不可用，因此按原样显示标准化状态表。')
          : statements.phase === 'empty'
            ? pair('This filing carries no primary statements, so the normalized state table is shown unchanged.',
                   '该财报没有主要报表，因此按原样显示标准化状态表。')
            : '';
      if (reason) {
        ui.statements.insertAdjacentHTML('afterbegin', '<p class="ff-statement-notice">' + reason + '</p>');
      }
      return;
    }
    if (statements.phase === 'loading') {
      ui.statements.innerHTML = '<div class="ff-loading" role="status"><span class="ff-loading-dot" aria-hidden="true"></span>' +
        pair('Loading the as-reported statement tree…', '正在载入按披露原样的报表树…') + '</div>';
      return;
    }
    state.statementCells = [];
    var payloadStatements = statements.statements.filter(objectValue);
    var allRefused = payloadStatements.length === 3 &&
      payloadStatements.every(function (statement) { return objectValue(statement.refusal); });
    if (allRefused) {
      var target = company() || {};
      renderStatements(target);
      ui.statements.insertAdjacentHTML('afterbegin',
        '<section class="ff-statement-block ff-statement-block--withheld ff-statement-block--notice">' +
        '<p class="ff-statement-withheld-copy">' + ACCESSION_ALL_REFUSED_COPY + '</p></section>');
      return;
    }
    var blocks = payloadStatements.map(function (statement) {
      if (objectValue(statement.refusal)) {
        return withheldStatementBlock(statement);
      }
      var columns = Array.isArray(statement.columns) ? statement.columns.filter(objectValue) : [];
      var rows = Array.isArray(statement.rows) ? statement.rows.filter(objectValue) : [];
      var header = '<th>' + pair('Line item / 报表项目', 'Line item / 报表项目') + '</th>' + columns.map(function (column) {
        return '<th>' + esc(column.label || '—') + '</th>';
      }).join('');
      var body = rows.map(function (row) {
        var cells = Array.isArray(row.cells) ? row.cells : [];
        var label = '<td data-label-en="Line item" data-label-zh="报表项目" class="ff-statement-label">' + esc(row.as_reported_label || '—') + '</td>';
        var filled = columns.map(function (column, index) {
          return '<td data-label-en="' + esc(column.label || '—') + '" data-label-zh="' + esc(column.label || '—') + '">' +
            statementCellControl(cells[index], row) + '</td>';
        }).join('');
        return '<tr>' + label + filled + '</tr>';
      }).join('');
      return '<section class="ff-statement-block"><h3>' + esc(statement.title || statement.statement_type || 'Statement') + '</h3>' +
        '<div class="ff-table-wrap"><table class="ff-table ff-statement-table"><thead><tr>' + header +
        '</tr></thead><tbody>' + body + '</tbody></table></div></section>';
    }).join('');
    ui.statements.innerHTML = blocks;
  }

  // ── Peer panel (§4, R5) ─────────────────────────────────────────────────
  // Read-only. URL state is the only persistence; no browser storage APIs
  // are touched. The payload blob is C1's CohortTable.to_dict(); policy
  // fields are not echoed by to_dict(), so the URL is the authority for the
  // policy line.
  var PEER_EXCLUSIONS = {
    'A35-I1': ['Same company, another share class', '同一公司的另一类股份'],
    'A35-X1': ['No observation in this package', '本数据包中无观察值'],
    'A35-B1': ['This metric does not apply', '该指标不适用'],
    'A35-W1': ['Statement not rebuilt from this filing', '未能从该财报重建此报表'],
    'A35-P1': ['Reporting period does not line up', '报告期未对齐'],
    'A35-P2': ['Shifted period', '期间已平移'],
    'A35-R1': ['No comparable reference for this company', '本公司无可比基准'],
    'A35-K1': ['Period type differs from the reference', '期间类型与基准不同'],
    'A35-U1': ['Unit differs from the reference', '单位与基准不同'],
    'A35-D1': ['Period length differs from the reference', '期间长度与基准不同'],
    'A35-V1': ['Metric definition version differs', '指标定义版本不同']
  };

  function peerExclusionCopy(code) {
    var known = PEER_EXCLUSIONS[code];
    if (!known) return { en: 'Excluded', zh: '已排除' };
    return { en: known[0], zh: known[1] };
  }

  function peerCohort() {
    var cohort = objectValue(state.payload && state.payload.peer_cohort);
    return cohort && Array.isArray(cohort.members) && Array.isArray(cohort.emissions) ? cohort : null;
  }

  function peerPolicyLine() {
    var alignCopy = state.peerAlign === 'shift_labeled'
      ? ['shift and label misaligned periods', '平移并标注未对齐期间']
      : ['exclude misaligned periods', '排除未对齐期间'];
    return pair(
      'Policy: ' + alignCopy[0] + ' · ' + state.peerTol + '-day window · at least ' + state.peerN + ' peers',
      '策略：' + alignCopy[1] + ' · ' + state.peerTol + ' 天窗口 · 至少 ' + state.peerN + ' 家同业'
    );
  }

  function selectedPeerEmission(cohort) {
    var emissions = cohort.emissions.filter(objectValue);
    if (!emissions.length) return null;
    if (state.peerMetric) {
      for (var index = 0; index < emissions.length; index += 1) {
        if (String(emissions[index].metric_id || '') === state.peerMetric) return emissions[index];
      }
    }
    state.peerMetric = String(emissions[0].metric_id || '');
    return emissions[0];
  }

  function anchorIssuerId(cohort) {
    var target = company() || {};
    if (target.entity_id) return String(target.entity_id);
    var wanted = String(state.symbol || '').toUpperCase();
    var members = cohort.members.filter(objectValue);
    for (var index = 0; index < members.length; index += 1) {
      var tickers = Array.isArray(members[index].tickers) ? members[index].tickers : [];
      for (var tickerIndex = 0; tickerIndex < tickers.length; tickerIndex += 1) {
        if (String(tickers[tickerIndex]).toUpperCase() === wanted) return String(members[index].issuer_id || '');
      }
    }
    return '';
  }

  function renderPeers() {
    var policyNode = byId('ff-peer-policy');
    var includedNode = byId('ff-peer-included');
    var excludedNode = byId('ff-peer-excluded');
    if (!policyNode || !includedNode || !excludedNode) return;
    policyNode.innerHTML = peerPolicyLine();
    var cohort = peerCohort();
    if (!cohort) {
      includedNode.innerHTML = emptyState(
        'Peer cohort unavailable', '同业组不可用',
        'This run did not publish a peer cohort, so no ranks or exclusions are shown. The link keeps its peer settings for when one lands.',
        '本次更新未发布同业组，因此不显示排名或排除项。链接会保留同业设置，待其发布后生效。', '▦'
      );
      excludedNode.innerHTML = '';
      return;
    }
    var emission = selectedPeerEmission(cohort);
    if (!emission) {
      includedNode.innerHTML = emptyState(
        'Peer cohort unavailable', '同业组不可用',
        'The published cohort carries no metric emissions.',
        '发布的同业组不包含任何指标排放。', '▦'
      );
      excludedNode.innerHTML = '';
      return;
    }
    var metricOptions = cohort.emissions.filter(objectValue).map(function (entry) {
      var metricId = String(entry.metric_id || '');
      return '<option value="' + esc(metricId) + '"' + (metricId === state.peerMetric ? ' selected' : '') + '>' +
        (metricLabelById(metricId) || esc(metricId)) + '</option>';
    }).join('');
    var selector = '<label class="ff-topic-filter ff-peer-metric"><span>' + pair('Metric', '指标') + '</span>' +
      '<select id="ff-peer-metric-select">' + metricOptions + '</select></label>';
    if (String(emission.emission_state || '') === 'below_min_n') {
      includedNode.innerHTML = selector + emptyState(
        'Not enough peers to rank', '同业数量不足以排名',
        'The qualifying group is smaller than the minimum, so no rank or average is computed.',
        '符合条件的公司数量低于最小值，因此不计算排名或平均值。', '▦'
      );
    } else if (String(emission.emission_state || '') === 'anchor_unavailable') {
      includedNode.innerHTML = selector + emptyState(
        'No comparable reference for this company', '本公司无可比基准',
        'This company has no usable value for this metric, so peers are not ranked against it.',
        '本公司在此指标上没有可用数值，因此不对同业排名。', '▦'
      );
    } else {
      var anchorId = anchorIssuerId(cohort);
      var rows = Array.isArray(emission.rows) ? emission.rows.filter(objectValue) : [];
      var members = cohort.members.filter(objectValue);
      var includedHtml = rows.map(function (row) {
        var member = null;
        for (var index = 0; index < members.length; index += 1) {
          if (String(members[index].issuer_id || '') === String(row.issuer_id || '')) member = members[index];
        }
        var tickers = member && Array.isArray(member.tickers) ? member.tickers : [];
        var isAnchor = anchorId && String(row.issuer_id || '') === anchorId;
        // Row values are decimal strings from C1: compact on the face, and a
        // control only where a span exists — peer rows carry none, so the
        // disabled state keeps the number honest (no re-ranking in browser).
        var valueControl = sourceControlHtml({ kind: 'peer', compactText: formatValue(row.value, 'currency') }, true);
        return '<div class="ff-peer-row' + (isAnchor ? ' is-anchor' : '') + '"'+ (isAnchor ? ' aria-current="true"' : '') + '>' +
          (isAnchor ? '<span class="ff-peer-anchor">' + pair('This company', '本公司') + '</span>' : '') +
          '<span class="ff-peer-ticker">' + esc(tickers[0] || row.issuer_id || '—') + '</span>' +
          '<span class="ff-peer-value">' + valueControl + '</span>' +
          '<span class="ff-peer-period">' + esc(row.period_label || '—') + '</span>' +
          (row.rank != null ? '<span class="ff-peer-rank">#' + esc(String(row.rank)) + '</span>' : '') +
          '</div>';
      }).join('');
      includedNode.innerHTML = selector + (includedHtml || emptyState(
        'Peer cohort unavailable', '同业组不可用',
        'The selected emission carries no member rows.',
        '所选指标排放不包含成员行。', '▦'
      ));
    }
    var exclusions = Array.isArray(cohort.exclusions) ? cohort.exclusions.filter(objectValue) : [];
    var exclusionHtml = exclusions.map(function (exclusion) {
      var code = String(exclusion.code || '');
      var known = PEER_EXCLUSIONS[code];
      var copy = known ? pair(known[0], known[1]) : pair('Excluded', '已排除');
      // Raw codes never sit on the glance tier; they fold into a details row.
      return '<details class="ff-peer-exclusion"><summary>' + copy + '</summary><code>' + esc(code || '—') + '</code></details>';
    }).join('');
    excludedNode.innerHTML = exclusions.length
      ? '<p class="ff-peer-subhead">' + pair('Excluded from this metric', '未计入本指标') + '</p>' + exclusionHtml
      : '<p class="ff-peer-subhead">' + pair('No exclusions recorded for this metric.', '本指标没有记录排除项。') + '</p>';
    var metricSelect = byId('ff-peer-metric-select');
    if (metricSelect) {
      metricSelect.addEventListener('change', function () {
        state.peerMetric = metricSelect.value || '';
        writeUrl(true);
        renderPeers();
      });
    }
  }

  // ── Saved views (X2-s) ──────────────────────────────────────────────────
  // Device-local briefcase (templates/fif_saved_briefcase.js, GovRev
  // discipline: never fetches) + P2's URL writer as the permalink. The saved
  // object binds to X0's request contract via its request_contract field; a
  // drift refuses the load with the plain "saved view unavailable" state —
  // never a repair, never a crash. Composed only from existing classes.
  var SAVED_COPY = {
    listLabel: ['Saved views', '已存视图'],
    empty: ['No saved views yet', '暂无已存视图'],
    choose: ['Choose a saved view', '选择已存视图'],
    save: ['Save this view', '保存当前视图'],
    rename: ['Rename', '重命名'],
    remove: ['Delete', '删除'],
    unavailable: ['unavailable', '不可用'],
    unavailableTitle: ['Saved view unavailable', '已存视图不可用'],
    unavailableContractCopy: [
      'This view was saved against an older contract and cannot be opened here. You can still delete it.',
      '此视图基于较早的契约保存，无法在此打开。你仍可将其删除。'
    ],
    unavailableIssuerCopy: [
      'This view\'s company is not covered by the current run, so it cannot be opened.',
      '当前更新未覆盖此视图的公司，因此无法打开。'
    ],
    unavailableMissingCopy: [
      'This saved view is no longer on this device — it may have been deleted in another tab.',
      '此已存视图已不在本设备上——可能已在其他标签页中删除。'
    ],
    // X2-b+c r2 MAJOR-1: an edit in another tab (unpinned, re-cut request)
    // refuses the active view. Never re-derived here — the user reopens it.
    unavailableChangedCopy: [
      'This saved view was changed in another tab. Reopen it to continue.',
      '此已保存视图已在另一个标签页中更改。请重新打开以继续。'
    ],
    unavailableStoreCopy: [
      'Saved views on this device could not be read, so they are left untouched. Saving is paused here.',
      '无法读取本设备上的已存视图，因此保持原样不作改动。此处暂停保存。'
    ],
    writeFailedCopy: [
      'Your browser did not save this change. Nothing else was changed.',
      '浏览器未保存此更改，其他内容未变。'
    ],
    pinnedTo: ['Pinned to', '固定于'],
    latest: ['latest', '最新'],
    asOf: ['As of', '截止'],
    newerGeneration: [
      'A newer filing generation exists — this view stays pinned to its cutoff.',
      '已有更新的财报数据版本——本视图仍固定于其截止日。'
    ],
    reResolve: ['Re-resolve at latest', '按最新重新解析'],
    peerSave: ['Save this peer view', '保存同业视图']
  };
  var POLICY_PLAIN = {
    as_reported: ['As reported', '按披露原样'],
    // The badge reads "Pinned to <date> · <phrase>", so the phrase must
    // stand on its own after the date (X2-s r1: no dangling "as of").
    latest_known_as_of: ['Latest known on that date', '该日已知最新'],
    latest_restated: ['Latest restated', '最新重述']
  };

  var savedBriefcase = null;

  function initSavedBriefcase() {
    if (!(window.FifSavedBriefcase && typeof window.FifSavedBriefcase.create === 'function')) return;
    savedBriefcase = window.FifSavedBriefcase.create();
    var controls = byId('ff-saved-controls');
    if (controls) controls.hidden = false;
    var peerRow = byId('ff-peer-save-row');
    if (peerRow) peerRow.hidden = false;
  }

  function savedPlainPolicy(selection) {
    var entry = POLICY_PLAIN[String(selection || '')];
    return entry || POLICY_PLAIN.latest_known_as_of;
  }

  function savedStampDate() {
    var clocks = (state.health && state.health.clocks) || {};
    var payload = state.payload || {};
    return clocks.broad_source_at || clocks.composed_state_at || payload.generated_at || '';
  }

  function savedSavePhase() {
    if (state.access === 'signin' || state.access === 'pending') return 'signin';
    if (state.access === 'upgrade') return 'upgrade';
    var target = company() || {};
    var body = buildQueryBody();
    var legal = !!target.entity_id && !!body.periods.length &&
      !!body.policy.source_snapshot_at && !!body.policy.recorded_at;
    return legal ? 'ready' : 'unavailable';
  }

  function buildSavedViewInput(name) {
    var target = company() || {};
    var body = buildQueryBody();
    var evidenceRefs = [];
    // A ref is stored only for an open cell evidence view with a REAL span —
    // a span is never invented (AM1); ids and spans only, never values.
    if (state.evidenceKind === 'cell' && state.cellEvidence) {
      var evidence = state.cellEvidence;
      var spanStart = numberValue(evidence.spanStart);
      var spanEnd = numberValue(evidence.spanEnd);
      if ((evidence.occurrenceId || evidence.accession) && spanStart != null && spanEnd != null) {
        evidenceRefs.push({
          accession: String(evidence.accession || ''),
          occurrence_id: String(evidence.occurrenceId || ''),
          source_span: [Math.trunc(spanStart), Math.trunc(spanEnd)]
        });
      }
    }
    return {
      name: name,
      issuer: {
        entity_id: String(target.entity_id || ''),
        cik: String(target.cik || ''),
        ticker: String(target.symbol || state.symbol || '')
      },
      request: body,
      peers: {
        cohort: state.cohortId || null,
        peer_metric: state.peerMetric || null,
        align: state.peerAlign === 'shift_labeled' ? 'shift_labeled' : 'exclude',
        peer_n: state.peerN,
        peer_tol: state.peerTol
      },
      view: {
        tab: state.tab,
        finding: state.tab === 'radar' ? (state.findingId || null) : null
      },
      pinned: !!state.asOfDate,
      saved_against: {
        generation_id: ((state.health && state.health.generation) || {}).id ||
          String(state.financial && state.financial.generationId || '') || null,
        admitted_at: ((state.health && state.health.generation) || {}).admitted_at || null,
        response_sha256: state.financial && state.financial.responseSha256 || null
      },
      evidence_refs: evidenceRefs,
      watch: { issuer: false }
    };
  }

  function performSavedSave(name) {
    if (!savedBriefcase) return { ok: false, reason: 'module' };
    var result = savedBriefcase.save(buildSavedViewInput(name));
    if (result.ok) {
      state.savedActiveId = result.view.id;
      state.savedRefusal = '';
      state.savedStoreError = false;
      state.pinnedRequest = result.view.pinned ? result.view.request : null;
    } else if (result.reason === 'storage') {
      state.savedStoreError = true;
    }
    renderSavedUI();
    return result;
  }

  // A pinned restore re-POSTs the stored request bytes VERBATIM — but only
  // while the desk still matches the view's subject, policy and cutoff day.
  // Any manual navigation away makes the override inert by itself.
  function activePinnedRequest() {
    if (state.pinnedRequest) reconcileSavedActive();
    var request = state.pinnedRequest;
    if (!request || typeof request !== 'object') return null;
    var target = company() || {};
    if (!target.entity_id || String(target.entity_id) !== String(request.entity_id)) return null;
    var selection = String((request.policy || {}).selection || '');
    if (String(state.policy || 'latest_known_as_of') !== selection) return null;
    if (state.asOfDate !== String((request.policy || {}).source_snapshot_at || '').slice(0, 10)) return null;
    return request;
  }

  function pinnedVariant(selection) {
    var request = activePinnedRequest();
    if (!request) return null;
    return Object.assign({}, request, {
      policy: Object.assign({}, request.policy, { selection: selection })
    });
  }

  // X2-b r2 MINOR-1 + X2-b+c r2 MAJOR-1, r3 R3-3/R3-4: another tab can
  // delete or break the active view, CHANGE it (unpin it, re-cut its
  // request), or break the whole store. The next read notices every one: the
  // view turns into its own refusal ('store' for a read-only store, 'changed'
  // for an edit), so the notice shows, no badge renders, no stale pinned
  // bytes are served, Export returns no body while the refusal is active
  // (exportQueryBody), and the resolve-path backfill writes nothing against a
  // capture the store no longer matches.
  function reconcileSavedActive() {
    if (!savedBriefcase || !state.savedActiveId || state.savedRefusal) return;
    if (savedBriefcase.readOnly()) {
      state.savedRefusal = 'store';
      state.pinnedRequest = null;
      return;
    }
    var result = savedBriefcase.load(state.savedActiveId);
    if (!result.ok) {
      state.savedRefusal = result.reason;
      state.pinnedRequest = null;
      return;
    }
    // MAJOR-1 + r3 R3-4: compare what this tab is serving against what the
    // store now holds — the loaded view's pinned flag, and its canonical
    // request bytes measured with the briefcase's own canonicalJson (the
    // same sorted-key, key-order-blind notion of equality the store and the
    // manifest use; JSON.stringify would let a same-content request with
    // reordered keys refuse). Any mismatch — pinned->latest, latest->pinned,
    // a changed request — refuses as 'changed'; never silently re-derived.
    var view = result.view;
    var servingPinned = !!state.pinnedRequest;
    var storedBytes = window.FifSavedBriefcase.canonicalJson(view.request);
    var servingBytes = window.FifSavedBriefcase.canonicalJson(state.pinnedRequest);
    if (view.pinned !== servingPinned ||
      (servingPinned && storedBytes !== servingBytes)) {
      state.savedRefusal = 'changed';
      state.pinnedRequest = null;
    }
  }

  function savedActiveView() {
    // A refused restore (issuer or any load refusal) is never the active view:
    // no pinned badge, no newer-generation chip, no saved_against backfill from
    // a desk it does not describe. Any refusal keeps the view inactive; a
    // write failure is tracked separately in state.savedStoreError. Delete
    // stays reachable through savedActiveId.
    if (!savedBriefcase || !state.savedActiveId) return null;
    if (state.savedRefusal) return null;
    var result = savedBriefcase.load(state.savedActiveId);
    return result.ok ? result.view : null;
  }

  function backfillSavedAgainst() {
    // X2-b+c r3 R3-3b: reconcile before any write (the fetch-resolve path
    // reconciles first too; this seam stays safe when driven directly), then
    // write only when no refusal is active. MINOR-3 (repair): the polarity is
    // main's — only a LATEST view (a fresh save or a re-resolve, which clears
    // the digest) is backfilled; a pinned view keeps the digest it was saved
    // with. The reconcile is what makes that safe: a view another tab pinned,
    // unpinned, re-cut or deleted while this tab's fetch was in flight is
    // refused first, so a digest from a fetch this desk no longer serves
    // never lands in it.
    reconcileSavedActive();
    var view = savedActiveView();
    if (!view || view.pinned || state.pinnedRequest) return;
    var digest = state.financial && state.financial.responseSha256 || '';
    if (!digest || view.saved_against.response_sha256 === digest) return;
    savedBriefcase.update(view.id, {
      saved_against: {
        generation_id: view.saved_against.generation_id,
        admitted_at: view.saved_against.admitted_at,
        response_sha256: digest
      }
    });
  }

  function savedNoticeHtml(kind) {
    var copy = kind === 'issuer' ? SAVED_COPY.unavailableIssuerCopy
      : kind === 'missing' ? SAVED_COPY.unavailableMissingCopy
      : kind === 'changed' ? SAVED_COPY.unavailableChangedCopy
      : kind === 'store' ? SAVED_COPY.unavailableStoreCopy
      : SAVED_COPY.unavailableContractCopy;
    // Existing classes only: the notice is an icon span plus a title element
    // and a copy element inside one container div (X2-s r1, MINOR-5).
    return '<span class="ff-notice-icon" aria-hidden="true">i</span><div><strong>' +
      pair(SAVED_COPY.unavailableTitle[0], SAVED_COPY.unavailableTitle[1]) +
      '</strong><div>' + pair(copy[0], copy[1]) + '</div></div>';
  }

  function renderSavedUI() {
    var select = byId('ff-saved-select');
    if (!select || !savedBriefcase) return;
    var saveBtn = byId('ff-saved-save');
    var nameInput = byId('ff-saved-name');
    var renameBtn = byId('ff-saved-rename');
    var deleteBtn = byId('ff-saved-delete');
    var badge = byId('ff-saved-badge');
    var notice = byId('ff-saved-notice');
    var peerSave = byId('ff-peer-save');
    var listing = savedBriefcase.list();
    var current = lang();
    // X2-s r1: a populated list offers a choice; only a truly empty list says
    // "No saved views yet".
    var placeholder = listing.length ? SAVED_COPY.choose : SAVED_COPY.empty;

    var options = '<option value="">' + (current === 'zh' ? placeholder[1] : placeholder[0]) + '</option>';
    listing.forEach(function (entry) {
      var label = entry.name;
      if (!entry.available) label += ' · ' + (current === 'zh' ? SAVED_COPY.unavailable[1] : SAVED_COPY.unavailable[0]);
      options += '<option value="' + esc(entry.id) + '">' + esc(label) + '</option>';
    });
    select.innerHTML = options;
    select.value = state.savedActiveId || '';

    // X2-s r1 (MAJOR-3): an unreadable store is read-only — Save/peer-save
    // stay disabled and Rename/Delete stay hidden through attributes only,
    // and the notice names the paused store instead of a contract drift.
    var storeReadOnly = savedBriefcase.readOnly();
    reconcileSavedActive();
    var phase = savedSavePhase();
    var name = nameInput && nameInput.value ? String(nameInput.value).trim() : '';
    if (saveBtn) {
      saveBtn.disabled = storeReadOnly || phase !== 'ready' || !name;
      saveBtn.setAttribute('data-label-en', SAVED_COPY.save[0]);
      saveBtn.setAttribute('data-label-zh', SAVED_COPY.save[1]);
      saveBtn.setAttribute('aria-label', current === 'zh' ? SAVED_COPY.save[1] : SAVED_COPY.save[0]);
    }
    if (peerSave) {
      peerSave.disabled = storeReadOnly || phase !== 'ready';
      peerSave.innerHTML = pair(SAVED_COPY.peerSave[0], SAVED_COPY.peerSave[1]);
    }
    var active = storeReadOnly ? null : savedActiveView();
    var renameable = !!active;
    if (renameBtn) renameBtn.hidden = !renameable;
    if (deleteBtn) deleteBtn.hidden = !state.savedActiveId || storeReadOnly;

    if (badge) {
      if (active && active.pinned) {
        var pinnedDate = formatDate(String((active.request.policy || {}).source_snapshot_at || ''));
        var policyCopy = savedPlainPolicy((active.request.policy || {}).selection);
        badge.innerHTML = pair(SAVED_COPY.pinnedTo[0] + ' ' + pinnedDate + ' · ' + policyCopy[0],
          SAVED_COPY.pinnedTo[1] + ' ' + pinnedDate + ' · ' + policyCopy[1]);
        badge.hidden = false;
      } else if (active) {
        var latestDate = formatDate(savedStampDate());
        badge.innerHTML = pair(SAVED_COPY.asOf[0] + ' ' + latestDate + ' · ' + SAVED_COPY.latest[0],
          SAVED_COPY.asOf[1] + ' ' + latestDate + ' · ' + SAVED_COPY.latest[1]);
        badge.hidden = false;
      } else {
        badge.hidden = true;
      }
    }

    if (notice) {
      // X2-s r2 (R2-4) precedence, exactly: an unreadable store (read
      // failure) -> a failed write (state.savedStoreError) -> a stale
      // newer-generation chip -> a refused view -> hidden.
      var action = '';
      var stale = savedGenerationStale();
      if (storeReadOnly) {
        notice.innerHTML = savedNoticeHtml('store');
        notice.hidden = false;
      } else if (state.savedStoreError) {
        notice.innerHTML = '<span class="ff-notice-icon" aria-hidden="true">i</span><div>' +
          pair(SAVED_COPY.writeFailedCopy[0], SAVED_COPY.writeFailedCopy[1]) + '</div>';
        notice.hidden = false;
      } else if (stale) {
        action = ' <button type="button" class="ff-retry" data-saved-reresolve="1">' +
          pair(SAVED_COPY.reResolve[0], SAVED_COPY.reResolve[1]) + '</button>';
        notice.innerHTML = '<span class="ff-notice-icon" aria-hidden="true">i</span><div>' +
          pair(SAVED_COPY.newerGeneration[0], SAVED_COPY.newerGeneration[1]) + action + '</div>';
        notice.hidden = false;
      } else if (state.savedRefusal) {
        notice.innerHTML = savedNoticeHtml(state.savedRefusal);
        notice.hidden = false;
      } else {
        notice.hidden = true;
        notice.innerHTML = '';
      }
    }
    // X2-b+c r4 (MINOR-4): every path that sets or clears a saved-view
    // refusal ends here — a refused restore, the resolve path, another tab's
    // edit noticed on render — so Export re-reads the refusal on each of
    // them instead of only on the next run-meta render.
    refreshExportState();
  }

  // The newer-generation signal: the view was saved against one production
  // dataset generation and health now names a different one (headers read on
  // the SAME health fetch P2 already makes; never ffprods_… at glance).
  // PF-3: generations are per issuer — a health generation that belongs to
  // another issuer never marks this view stale.
  function savedGenerationStale() {
    var view = savedActiveView();
    if (!view || !view.pinned) return null;
    var against = view.saved_against || {};
    var generation = (state.health && state.health.generation) || {};
    if (!against.generation_id || !generation.id) return null;
    if (generation.entity_id && String(generation.entity_id) !== String(view.request.entity_id || '')) return null;
    if (against.generation_id === generation.id) return null;
    return { view: view, generation: generation };
  }

  function reResolveSavedView() {
    var stale = savedGenerationStale();
    if (!stale || !savedBriefcase) return { ok: false, reason: 'stale' };
    // PF-3: the re-resolved cutoff comes from the SAME helper the Latest
    // policy uses — recorded_at is the latest of the present values, so a
    // desk whose composed_state_at is absent but whose generation and
    // broad_source_at are known re-resolves instead of refusing as 'clocks'.
    var cutoffs = latestCutoffs();
    if (!cutoffs.recorded_at || !cutoffs.source_snapshot_at) return { ok: false, reason: 'clocks' };
    var request = JSON.parse(JSON.stringify(stale.view.request));
    request.policy.source_snapshot_at = cutoffs.source_snapshot_at;
    request.policy.recorded_at = cutoffs.recorded_at;
    var result = savedBriefcase.update(stale.view.id, {
      request: request,
      pinned: false,
      saved_against: {
        generation_id: stale.generation.id,
        admitted_at: stale.generation.admitted_at || '',
        response_sha256: ''
      }
    });
    if (result.ok) restoreSavedView(stale.view.id);
    else if (result.reason === 'storage') {
      state.savedStoreError = true;
      renderSavedUI();
    }
    return result;
  }

  function restoreSavedView(id) {
    if (!savedBriefcase) return { ok: false, reason: 'module' };
    state.savedStoreError = false;
    var result = savedBriefcase.load(id);
    state.savedActiveId = String(id || '');
    if (!result.ok) {
      // 'missing' keeps its own kind (its own notice copy): the view was on
      // this device and is gone now; everything else keeps its refusal reason.
      state.savedRefusal = result.reason;
      state.pinnedRequest = null;
      renderSavedUI();
      return result;
    }
    state.savedRefusal = '';
    var view = result.view;
    // issuer is display/index metadata; the query identity stays
    // request.entity_id and is never inferred from the ticker. The ticker
    // must resolve AND the resolved issuer must still carry the stored
    // entity_id — a ticker that resolves to a different entity refuses as
    // 'issuer' BEFORE any desk-state mutation.
    var resolved = view.issuer && view.issuer.ticker ? resolveSymbol(view.issuer.ticker) : '';
    var resolvedCompany = resolved ? companies()[resolved] : null;
    if (!resolvedCompany || String(resolvedCompany.entity_id) !== String(view.request.entity_id)) {
      state.savedRefusal = 'issuer';
      state.pinnedRequest = null;
      renderSavedUI();
      return { ok: false, reason: 'issuer' };
    }
    // Desk state first, then setCompany: the financial query it triggers must
    // see the restored policy, cutoff and pinned bytes, not the defaults.
    // checkView guarantees every field read below exists in canonical form —
    // no defaults are applied here; an un-appliable value refuses at load as
    // a contract refusal, never silently coerces.
    state.policy = view.request.policy.selection;
    state.asOfDate = view.pinned ? view.request.policy.source_snapshot_at.slice(0, 10) : '';
    state.cohortId = view.peers.cohort == null ? '' : view.peers.cohort;
    state.peerMetric = view.peers.peer_metric == null ? '' : view.peers.peer_metric;
    state.peerAlign = view.peers.align === 'shift_labeled' ? 'shift_labeled' : 'exclude';
    state.peerN = view.peers.peer_n;
    state.peerTol = view.peers.peer_tol;
    state.pinnedRequest = view.pinned ? view.request : null;
    setCompany(resolved, false);
    setTab(view.view.tab, false);
    if (view.view.finding && state.tab === 'radar') {
      state.findingId = String(view.view.finding);
      state.evidenceKind = 'finding';
      renderFindings();
      renderCurrentEvidence();
    }
    // The permalink is P2's own writer — never a second URL builder.
    writeUrl(true);
    updateViewStatus();
    // X2-s r1: the as-of controls and the desk stamp follow the restored
    // cutoff (a pinned view shows its date, never "Latest" plus an empty
    // field); renderRunMeta re-syncs both and then renders the saved UI.
    renderRunMeta();
    return { ok: true, view: view };
  }

  function savedRenameActive(name) {
    if (!savedBriefcase || !state.savedActiveId) return { ok: false, reason: 'missing' };
    var result = savedBriefcase.update(state.savedActiveId, { name: name });
    if (result.ok) state.savedStoreError = false;
    else if (result.reason === 'storage') state.savedStoreError = true;
    renderSavedUI();
    return result;
  }

  function savedDeleteActive() {
    if (!savedBriefcase || !state.savedActiveId) return { ok: false, reason: 'missing' };
    var result = savedBriefcase.remove(state.savedActiveId);
    if (result.ok) {
      state.savedActiveId = '';
      state.savedRefusal = '';
      state.savedStoreError = false;
      state.pinnedRequest = null;
    } else if (result.reason === 'storage') {
      state.savedStoreError = true;
    }
    renderSavedUI();
    return result;
  }

  // ── Export entry (§5, R6) ───────────────────────────────────────────────
  // One Export control in the desk header. It POSTs the byte-identical query
  // body for the current issuer, cutoff and policy; reload remains the only
  // refresh. The route is X1: a 404/405 disables the control (AM3/R-D) and no
  // JSON-download fallback is invented.
  var XLSX_MEDIA_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

  function exportQueryBody() {
    // X2-b+c r3 R3-3a: while a saved-view refusal is active the desk still
    // holds the stale pinned query body; Export must not re-POST it. The
    // refusal copy already tells the reader to reopen the view, so Export
    // gets no body at all, whatever the phase. The reconcile-on-read makes
    // the guard hold even when the edit in the other tab is not yet noticed.
    reconcileSavedActive();
    if (state.savedRefusal) return null;
    if (state.financial && state.financial.queryBody && state.financial.phase === 'ready') {
      return state.financial.queryBody;
    }
    return buildQueryBody();
  }

  function exportPhase() {
    if (state.access === 'signin' || state.access === 'pending') return 'signin';
    if (state.access === 'upgrade') return 'upgrade';
    if (state.exportUnavailable) return 'unavailable';
    // X2-b+c r3 MINOR-4 (repair): the button agrees with exportQueryBody — a
    // saved-view refusal leaves Export with no body, so the control reads
    // unavailable instead of offering a click that does nothing.
    reconcileSavedActive();
    if (state.savedRefusal) return 'unavailable';
    var target = company() || {};
    var body = buildQueryBody();
    var legal = !!target.entity_id && !!body.periods.length &&
      !!body.policy.source_snapshot_at && !!body.policy.recorded_at;
    return legal ? 'ready' : 'unavailable';
  }

  // Item 11: the tooltip names the actual reason the export is off.
  function exportTip(phase) {
    if (phase === 'signin') return ['Sign in to download this company\'s numbers as a workbook.', '登录后可将该公司的数据下载为工作簿。'];
    if (phase === 'upgrade') return ['Workbook export is included in the Essential plan.', '工作簿导出包含在 Essential 方案中。'];
    if (phase === 'ready') return ['Download this company\'s numbers as of the selected date.', '下载所选日期的该公司数据。'];
    if (state.exportUnavailable) {
      return state.exportUnavailableCause === 'route'
        ? ['Export unavailable: this server does not offer workbook downloads yet.', '导出不可用：此服务器尚未提供工作簿下载。']
        : ['Export unavailable: the last download request failed. Reload to try again.', '导出不可用：上次下载请求失败，请重新载入后再试。'];
    }
    // MINOR-4: the saved-view notice already names the cause and the action.
    if (state.savedRefusal) return ['Export unavailable for this view.', '此视图暂不支持导出。'];
    var target = company() || {};
    var body = buildQueryBody();
    var en = [];
    var zh = [];
    if (!target.entity_id) { en.push('this company has no SEC identifier in this run'); zh.push('本次数据缺少该公司的 SEC 识别码'); }
    if (!body.periods.length) { en.push('there are no filing periods to export'); zh.push('没有可导出的财报期间'); }
    if (!body.policy.source_snapshot_at) { en.push('the source snapshot date is unknown'); zh.push('来源快照日期未知'); }
    if (!body.policy.recorded_at) { en.push('the recording date is unknown'); zh.push('记录日期未知'); }
    if (!en.length) return ['Export unavailable for this view.', '此视图暂不支持导出。'];
    return ['Export unavailable: ' + en.join('; ') + '.', '导出不可用：' + zh.join('；') + '。'];
  }

  function refreshExportState() {
    if (!ui.exportBtn) return;
    var phase = exportPhase();
    var copy = phase === 'signin' ? ['Sign in to export', '登录后导出'] :
      phase === 'upgrade' ? ['Included in Essential', 'Essential 包含'] :
        phase === 'unavailable' ? ['Export unavailable', '导出不可用'] : ['Export', '导出'];
    ui.exportBtn.disabled = phase !== 'ready';
    ui.exportBtn.innerHTML = pair(copy[0], copy[1]);
    ui.exportBtn.setAttribute('data-label-en', copy[0]);
    ui.exportBtn.setAttribute('data-label-zh', copy[1]);
    var current = lang();
    ui.exportBtn.setAttribute('aria-label', current === 'zh' ? copy[1] : copy[0]);
    var tip = exportTip(phase);
    // A disabled button receives no pointer events, so the wrapper carries
    // the same tip for hover; the button keeps it for focus/assistive tech.
    [ui.exportBtn, ui.exportWrap].forEach(function (node) {
      if (!node) return;
      node.setAttribute('data-tip-en', tip[0]);
      node.setAttribute('data-tip-zh', tip[1]);
    });
  }

  function exportFilename(response) {
    var disposition = String(response.headers.get('Content-Disposition') || '');
    var match = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
    if (match && match[1]) return match[1];
    var queryId = String(response.headers.get('X-FIF-Query-Id') || '').trim();
    if (queryId) return queryId + '.xlsx';
    return 'fundamental_forensics.xlsx';
  }

  function runExport() {
    if (!ui.exportBtn || ui.exportBtn.disabled) return;
    var body = exportQueryBody();
    // X2-b+c r3: a saved-view refusal yields no body — never POST "null".
    if (!body) return;
    withAuth({ 'Content-Type': 'application/json', Accept: XLSX_MEDIA_TYPE })
      .then(function (headers) {
        return fetch(FINANCIAL_QUERY_XLSX_URL, {
          method: 'POST',
          headers: headers,
          credentials: 'same-origin',
          cache: 'no-store',
          body: JSON.stringify(body)
        });
      })
      .then(function (response) {
        if (response.status === 404 || response.status === 405) {
          // The workbook route is not present at this base (X1): the control
          // goes disabled and stays disabled — no fallback download.
          state.exportUnavailable = true;
          state.exportUnavailableCause = 'route';
          refreshExportState();
          return null;
        }
        if (response.status === 401 || response.status === 403) {
          showLoadError({ status: response.status });
          return null;
        }
        if (!response.ok) throw new Error('Export request failed');
        var filename = exportFilename(response);
        return response.blob().then(function (blob) {
          var url = URL.createObjectURL(blob);
          var anchor = document.createElement('a');
          anchor.href = url;
          anchor.download = filename;
          document.body.appendChild(anchor);
          anchor.click();
          document.body.removeChild(anchor);
          window.setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
        });
      })
      .catch(function () {
        state.exportUnavailable = true;
        state.exportUnavailableCause = 'failed';
        refreshExportState();
      });
  }

  function renderCellEvidence(cell) {
    if (!cell) {
      renderEvidence(null);
      return;
    }
    var glossaryId = cell.metricId || '';
    ui.evidenceTitle.innerHTML = cell.titlePair || pair('What this number is', '这个数字是什么');
    var exact = cell.exactText != null && String(cell.exactText) !== '' ? String(cell.exactText) : '';
    var excerpt = String(cell.excerpt || '').trim();
    var body = '<section class="ff-signal-meaning"><span>' + pair('What this number is', '这个数字是什么') + '</span><p>' +
      glossarySentence(glossaryId) + '</p></section>' +
      '<section class="ff-proof-section"><h3>' + pair('Exact value', '精确数值') + '</h3>' +
      (exact ? '<code class="ff-exact">' + esc(exact) + '</code>' +
        '<p class="ff-proof-compact-line"><b>' + pair('Compact', '简写') + '</b> ' + esc(cell.compactText || '—') + '</p>' +
        (cell.unit ? '<p class="ff-proof-compact-line"><b>' + pair('Unit', '单位') + '</b> ' + esc(cell.unit) + '</p>' : '')
        : '<p class="ff-proof-compact-line">' + pair('Exact value unavailable for this cell.', '该单元格的精确数值不可用。') + '</p>') +
      '</section>' +
      '<section class="ff-proof-section"><h3>' + pair('Source span', '来源片段') + '</h3>' +
      (excerpt ? '<blockquote class="ff-span-excerpt">' + esc(excerpt) + '</blockquote>' :
        '<p class="ff-proof-compact-line">' + pair('Source span unavailable', '来源片段不可用') + '</p>') +
      (cell.accession ? '<p class="ff-proof-compact-line"><b>' + pair('Accession', '文件编号') + '</b> <span class="ff-accession">' + esc(cell.accession) + '</span></p>' : '') +
      '</section>' +
      (cell.revisionsRow ? '<section class="ff-proof-section"><h3>' + pair('Original, latest, restated', '原始、截止最新、重述后') + '</h3>' +
        '<dl class="ff-receipt-waterfall-fields">' +
        '<div><dt>' + pair('Original reported', '原始披露') + '</dt><dd><code>' + esc(cell.revisionsRow.root_value == null ? '—' : String(cell.revisionsRow.root_value)) + '</code></dd></div>' +
        '<div><dt>' + pair('Prior', '上期') + '</dt><dd><code>' + esc(cell.revisionsRow.prior_value == null ? '—' : String(cell.revisionsRow.prior_value)) + '</code></dd></div>' +
        '<div><dt>' + pair('Restated', '重述后') + '</dt><dd><code>' + esc(cell.revisionsRow.revised_value == null ? '—' : String(cell.revisionsRow.revised_value)) + '</code></dd></div>' +
        '</dl></section>' : '') +
      '<details class="ff-proof-details"><summary>' + pair('Technical ids', '技术编号') + '</summary><div><dl class="ff-receipt-waterfall-fields">' +
      (cell.occurrenceId ? '<div><dt>occurrence</dt><dd><code title="' + esc(cell.occurrenceId) + '">' + esc(shortTraceId(cell.occurrenceId)) + '</code></dd></div>' : '') +
      (cell.rootCellId ? '<div><dt>root cell</dt><dd><code title="' + esc(cell.rootCellId) + '">' + esc(shortTraceId(cell.rootCellId)) + '</code></dd></div>' : '') +
      (cell.snapshotId ? '<div><dt>snapshot</dt><dd><code title="' + esc(cell.snapshotId) + '">' + esc(shortTraceId(cell.snapshotId)) + '</code></dd></div>' : '') +
      '<div><dt>span</dt><dd><code>' + esc(cell.spanStart && cell.spanEnd ? cell.spanStart + '-' + cell.spanEnd : '—') + '</code></dd></div>' +
      '</dl></div></details>';
    ui.evidenceBody.innerHTML = body;
  }

  function disclosureSectionPair(section) {
    var normalized = String(section || 'other').toLowerCase();
    if (normalized === 'other') return pair('Other disclosure', '其他披露');
    return topicPair(normalized);
  }

  function disclosureSectionText(section, preferred) {
    var normalized = String(section || 'other').toLowerCase();
    if (normalized === 'other') return preferred === 'zh' ? '其他披露' : 'Other disclosure';
    return topicText(normalized, preferred);
  }

  function documentDate(document) {
    if (!document) return '—';
    return formatDate(document.filed_at || document.filing_date || document.filed || document.report_date);
  }

  function documentSourceUrl(document) {
    return safeUrl(document && (document.source_url || document.url || document.filing_url));
  }

  function documentAccession(document) {
    return String((document && (document.accession || document.accession_number || document.id)) || '—');
  }

  function disclosureFindingState(finding) {
    var status = String((finding && (finding.state || finding.review_level || finding.status)) || '').toLowerCase();
    if (status === 'triggered' || status === 'manual_review' || status === 'review') {
      return { key: 'review', icon: '◇', en: 'Observed change', zh: '观察到变化' };
    }
    if (status === 'clear' || status === 'no_review') {
      return { key: 'clear', icon: '·', en: 'No review prompt', zh: '未出现复核提示' };
    }
    return { key: 'limited', icon: '?', en: 'Needs source review', zh: '需查看来源' };
  }

  function disclosureFindingLabel(finding) {
    var labels = finding && (finding.labels || finding.label);
    var en = localized(labels, 'en') || (finding && (finding.title_en || finding.title || finding.detector_id)) || 'Disclosure change';
    var zh = localized(labels, 'zh') || (finding && (finding.title_zh || finding.title || finding.detector_id)) || '披露变化';
    return pair(en, zh);
  }

  function readablePhraseList(raw, preferred) {
    var labels = {
      monthly_active_users: ['monthly active users', '月活跃用户'],
      daily_active_users: ['daily active users', '日活跃用户'],
      net_revenue_retention: ['net revenue retention', '净收入留存率'],
      active_customers: ['active customers', '活跃客户'],
      paying_customers: ['paying customers', '付费客户'],
      subscribers: ['subscribers', '订阅用户'],
      same_store_sales: ['same-store sales', '同店销售'],
      orders: ['orders', '订单']
    };
    return String(raw || '').split(',').filter(Boolean).map(function (item) {
      var value = labels[item];
      return value ? value[preferred === 'zh' ? 1 : 0] : prettify(item);
    }).join(preferred === 'zh' ? '、' : ', ');
  }

  function disclosureWhyPair(finding) {
    var why = objectValue(finding && finding.why_flagged) || {};
    var count = numberValue(why.changed_paragraph_count);
    if (count != null) return pair(
      count + ' matched passage' + (count === 1 ? ' was' : 's were') + ' textually changed.',
      '有 ' + count + ' 个匹配段落出现文本变化。'
    );
    count = numberValue(why.changed_policy_block_count);
    if (count != null) return pair(
      count + ' policy passage' + (count === 1 ? ' was' : 's were') + ' textually changed.',
      '有 ' + count + ' 个政策段落出现文本变化。'
    );
    if (why.missing_kpi_keys) {
      var enList = readablePhraseList(why.missing_kpi_keys, 'en');
      var zhList = readablePhraseList(why.missing_kpi_keys, 'zh');
      return pair(
        'A previously matched metric phrase was not found in the supplied current filing: ' + enList + '.',
        '在提供的本期财报中未找到此前匹配的指标词组：' + zhList + '。'
      );
    }
    if (why.reason === 'same_reporting_form_required') return pair(
      'The supplied filings are not the same reporting form, so this comparison is not evaluable.',
      '提供的财报不是同一类报表，因此无法直接比较。'
    );
    if (why.reason === 'risk_factor_section_missing') return pair(
      'The expected risk-factor section was not found in one supplied filing.',
      '在一份提供的财报中未找到预期的风险因素章节。'
    );
    if (why.reason === 'policy_disclosure_missing_in_one_filing') return pair(
      'The matched policy disclosure was not found in both supplied filings.',
      '在两份提供的财报中未同时找到匹配的政策披露。'
    );
    return pair(
      'The comparison engine found a reviewable lexical difference. Read the source excerpts before interpreting it.',
      '对比引擎发现了值得复核的文字差异；请先阅读来源摘录再作解读。'
    );
  }

  function disclosureFindingsForView(target) {
    return disclosureFindings(target).filter(function (finding) {
      var info = disclosureFindingState(finding);
      var section = disclosureFindingSection(finding);
      return info.key === 'review' && (state.disclosureSection === 'all' || section === state.disclosureSection);
    });
  }

  function activeRedlines(target) {
    return disclosureRedlines(target).filter(function (redline) {
      var operation = String(redline.operation || '').toLowerCase();
      if (redline.suppressed || operation === 'unchanged' || operation === 'moved' || operation === 'suppressed_boilerplate') return false;
      return operation === 'modified' || operation === 'added' || operation === 'removed' || operation === 'table_cell_changed' || !operation;
    });
  }

  function redlineOperationInfo(redline) {
    var operation = String((redline && redline.operation) || '').toLowerCase();
    if (operation === 'added') return { key: 'added', en: 'Text added', zh: '新增文本' };
    if (operation === 'removed') return { key: 'removed', en: 'Text removed', zh: '删除文本' };
    if (operation === 'table_cell_changed') return { key: 'table', en: 'Table cell changed', zh: '表格单元格变化' };
    return { key: 'modified', en: 'Wording changed', zh: '措辞变化' };
  }

  function redlineSection(redline) {
    return String((redline && redline.section_key) || 'other');
  }

  function editPreview(redline) {
    var edits = Array.isArray(redline && redline.inline_edits) ? redline.inline_edits : [];
    if (!edits.length) return pair('Open to read the supplied source excerpts.', '打开以阅读提供的来源摘录。');
    var edit = edits[0] || {};
    var before = String(edit.prior_text || '').trim();
    var after = String(edit.current_text || '').trim();
    var content = before || after || '';
    if (content.length > 132) content = content.slice(0, 131) + '…';
    return pair(content || 'Open to read the supplied source excerpts.', content || '打开以阅读提供的来源摘录。');
  }

  function renderDisclosureControls(target) {
    var sections = [];
    disclosureFindings(target).forEach(function (finding) {
      var key = disclosureFindingSection(finding);
      if (sections.indexOf(key) < 0) sections.push(key);
    });
    activeRedlines(target).forEach(function (redline) {
      var key = redlineSection(redline);
      if (sections.indexOf(key) < 0) sections.push(key);
    });
    if (sections.indexOf(state.disclosureSection) < 0) state.disclosureSection = 'all';
    var html = '<option value="all">' + esc(lang() === 'zh' ? '全部章节' : 'All sections') + '</option>';
    sections.sort().forEach(function (section) {
      html += '<option value="' + esc(section) + '">' + esc(disclosureSectionText(section, lang())) + '</option>';
    });
    ui.disclosureSection.innerHTML = html;
    ui.disclosureSection.value = state.disclosureSection;
    ui.disclosureSection.disabled = !sections.length;
  }

  function renderDisclosureFeed(target) {
    var documents = disclosureDocuments(target);
    var pairCount = readyDisclosureTracks(target).length;
    var allFindings = disclosureFindings(target);
    var visible = disclosureFindingsForView(target);
    var compared = pairCount > 0;
    ui.disclosureSummary.innerHTML = compared ? pair(
      visible.length + ' review prompt' + (visible.length === 1 ? '' : 's') + ' across ' + pairCount + ' filing pair' + (pairCount === 1 ? '' : 's'),
      pairCount + ' 组财报对比中有 ' + visible.length + ' 项复核提示'
    ) : pair('Comparable filing pair unavailable', '暂无可比财报组合');
    if (!compared && !allFindings.length) {
      if (state.evidenceKind === 'disclosure-finding') {
        state.disclosureFindingId = '';
        renderTabEvidenceEmpty('disclosures');
      }
      ui.disclosureFeed.innerHTML = emptyState(
        'No comparable filing pair yet', '尚无可比财报组合',
        'Disclosure comparison appears only after two compatible SEC filings are available. Nothing is inferred from missing text.',
        '只有在两份兼容的 SEC 财报可用后才会显示披露对比；不会从缺失文本推断结果。', '?'
      );
      return;
    }
    if (!visible.length) {
      if (state.evidenceKind === 'disclosure-finding') {
        state.disclosureFindingId = '';
        renderTabEvidenceEmpty('disclosures');
      }
      var filtered = allFindings.some(function (finding) { return disclosureFindingState(finding).key === 'review'; });
      ui.disclosureFeed.innerHTML = emptyState(
        filtered ? 'No observed changes in this section' : 'No review prompt in this comparison',
        filtered ? '该章节未见观察到的变化' : '本次对比暂无复核提示',
        filtered ? 'Choose another section to inspect the available observations.' : 'This is not a conclusion that every disclosure is unchanged; inspect the filing trail and source coverage.',
        filtered ? '请选择其他章节查看已有观察结果。' : '这不代表每项披露都没有变化；请查看披露轨迹和来源覆盖范围。', filtered ? '↺' : '✓'
      );
      return;
    }
    if (!selectedDisclosureFinding() || !visible.some(function (finding) { return disclosureFindingId(finding) === state.disclosureFindingId; })) {
      state.disclosureFindingId = disclosureFindingId(visible[0]);
    }
    ui.disclosureFeed.innerHTML = visible.map(function (finding) {
      var selected = disclosureFindingId(finding) === state.disclosureFindingId;
      var section = disclosureFindingSection(finding);
      var status = disclosureFindingState(finding);
      var form = String(finding._track_form || '');
      // §2.2 — the change row carries the span of its first evidence receipt;
      // opening the card opens the drawer on that exact occurrence.
      var receiptControl = controlFromEvidenceReceipt(
        (Array.isArray(finding.evidence_receipts) ? finding.evidence_receipts : []).filter(objectValue)[0],
        'disclosure', ''
      );
      var spanAttrs = spanOk(receiptControl)
        ? ' data-source-kind="disclosure"' +
          ' data-occurrence-id="' + esc(receiptControl.occurrenceId) + '"' +
          ' data-accession="' + esc(receiptControl.accession) + '"' +
          ' data-span-start="' + esc(String(receiptControl.spanStart)) + '"' +
          ' data-span-end="' + esc(String(receiptControl.spanEnd)) + '"'
        : '';
      return '<div role="listitem"><button type="button" class="ff-disclosure-card' + (selected ? ' is-selected' : '') + '"' +
        ' data-disclosure-finding-id="' + esc(disclosureFindingId(finding)) + '"' + spanAttrs +
        ' aria-current="' + (selected ? 'true' : 'false') + '" aria-controls="ff-evidence">' +
        '<span class="ff-disclosure-mark" aria-hidden="true">' + status.icon + '</span><span class="ff-disclosure-copy">' +
        '<span class="ff-finding-overline"><span class="ff-observed-label">' + pair(status.en, status.zh) + '</span>' +
        (form ? '<span aria-hidden="true">·</span><span>' + esc(form) + '</span>' : '') +
        '<span aria-hidden="true">·</span><span>' + disclosureSectionPair(section) + '</span></span>' +
        '<h3>' + disclosureFindingLabel(finding) + '</h3><span class="ff-finding-summary">' + disclosureWhyPair(finding) + '</span></span>' +
        '<span class="ff-finding-periods"><strong>' + esc(String(finding.current_accession || '—')) + '</strong>' + pair('Read excerpts', '阅读摘录') + '</span></button></div>';
    }).join('');
    if (state.evidenceKind === 'disclosure-finding') renderCurrentEvidence();
  }

  function renderRedlines(target) {
    var redlines = activeRedlines(target);
    var filtered = redlines.filter(function (redline) {
      return state.disclosureSection === 'all' || redlineSection(redline) === state.disclosureSection;
    });
    ui.redlineSummary.innerHTML = pair(
      filtered.length + ' visible text change' + (filtered.length === 1 ? '' : 's'),
      '显示 ' + filtered.length + ' 条文本变化'
    );
    if (!redlines.length) {
      if (state.evidenceKind === 'redline') {
        state.redlineId = '';
        renderTabEvidenceEmpty('redlines');
      }
      ui.redlineList.innerHTML = emptyState(
        'No source redlines available', '暂无来源逐字对照',
        'A redline appears only when the comparison engine has matched supplied filing text. Suppressed boilerplate is intentionally excluded.',
        '只有在对比引擎匹配到提供的财报文本时才会显示逐字对照；已抑制的模板文本会被有意排除。', '—'
      );
      return;
    }
    if (!filtered.length) {
      if (state.evidenceKind === 'redline') {
        state.redlineId = '';
        renderTabEvidenceEmpty('redlines');
      }
      ui.redlineList.innerHTML = emptyState(
        'No redlines in this section', '该章节暂无逐字对照',
        'Choose another section to inspect the available filing changes.',
        '请选择其他章节查看已有的财报变化。', '↺'
      );
      return;
    }
    if (!selectedRedline() || !filtered.some(function (redline) { return redlineId(redline) === state.redlineId; })) {
      state.redlineId = redlineId(filtered[0]);
    }
    ui.redlineList.innerHTML = filtered.map(function (redline) {
      var selected = redlineId(redline) === state.redlineId;
      var operation = redlineOperationInfo(redline);
      var form = String(redline._track_form || '');
      var count = numberValue(redline.changed_token_count);
      var countText = count == null ? '' : count + (count === 1 ? ' changed word' : ' changed words');
      var zhCountText = count == null ? '' : count + ' 个变化词';
      // §2.2 — changed tokens carry the span of the prior/current receipt.
      // A span inside the card button cannot be its own button (HTML forbids
      // the nesting), so the wrapper is a span and the card keeps the open
      // behaviour on the exact occurrence.
      var receiptControl = controlFromEvidenceReceipt(
        objectValue(redline.current_receipt) || objectValue(redline.prior_receipt), 'redline', ''
      );
      var previewAttrs = spanOk(receiptControl)
        ? ' data-source-kind="redline"' +
          ' data-occurrence-id="' + esc(receiptControl.occurrenceId) + '"' +
          ' data-accession="' + esc(receiptControl.accession) + '"' +
          ' data-span-start="' + esc(String(receiptControl.spanStart)) + '"' +
          ' data-span-end="' + esc(String(receiptControl.spanEnd)) + '"'
        : '';
      var previewClass = spanOk(receiptControl) ? 'ff-source-control' : 'ff-source-control is-unavailable';
      return '<div role="listitem"><button type="button" class="ff-redline-card' + (selected ? ' is-selected' : '') + '"' +
        ' data-redline-id="' + esc(redlineId(redline)) + '" aria-current="' + (selected ? 'true' : 'false') + '" aria-controls="ff-evidence">' +
        '<span class="ff-redline-operation" data-operation="' + esc(operation.key) + '">' + pair(operation.en, operation.zh) + '</span>' +
        '<span class="ff-redline-copy"><span class="ff-finding-overline">' + (form ? esc(form) + '<span aria-hidden="true">·</span>' : '') + disclosureSectionPair(redlineSection(redline)) +
        (countText ? '<span aria-hidden="true">·</span><span>' + pair(countText, zhCountText) + '</span>' : '') + '</span><p><span class="' + previewClass + '"' + previewAttrs +
        (spanOk(receiptControl) ? '' : ' aria-disabled="true" data-tip-en="Source span unavailable" data-tip-zh="来源片段不可用"') + '>' +
        editPreview(redline) + '</span></p></span>' +
        '<span class="ff-redline-open">' + pair('Inspect', '查看') + '<span aria-hidden="true">↗</span></span></button></div>';
    }).join('');
    if (state.evidenceKind === 'redline') renderCurrentEvidence();
  }

  function renderTimeline(target) {
    var documents = disclosureDocuments(target);
    if (!documents.length) {
      ui.timeline.innerHTML = emptyState(
        'No filing trail supplied', '未提供披露轨迹',
        'The disclosure layer has not supplied filing accessions for this company.',
        '该公司的披露层尚未提供财报文件编号。', '—'
      );
      return;
    }
    ui.timeline.innerHTML = '<div class="ff-timeline-rail" aria-hidden="true"></div><div class="ff-timeline-list">' + documents.map(function (document, index) {
      var href = documentSourceUrl(document);
      var form = String(document._track_form || document.form || document.form_type || 'SEC filing');
      var role = document._filing_role === 'current' ? pair('Current ' + form, '本期 ' + form) :
        (document._filing_role === 'prior' ? pair('Prior ' + form, '上期 ' + form) : pair('Source filing', '来源财报'));
      var reportDate = formatDate(document.report_date);
      var sourceAction = href ? '<a class="ff-source-link ff-timeline-link" href="' + esc(href) + '" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">↗</span>' + pair('Open SEC filing', '打开 SEC 财报') + '</a>' : '<span class="ff-timeline-unavailable">' + pair('SEC link not supplied', '未提供 SEC 链接') + '</span>';
      return '<article class="ff-timeline-card"><span class="ff-timeline-node" aria-hidden="true">' + (index + 1) + '</span><p class="ff-kicker">' + role + '</p><h3>' + esc(form) + '</h3><dl><div><dt>' + pair('Filed', '披露日') + '</dt><dd>' + esc(documentDate(document)) + '</dd></div><div><dt>' + pair('Report date', '报告期') + '</dt><dd>' + esc(reportDate) + '</dd></div><div><dt>' + pair('Accession', '文件编号') + '</dt><dd class="ff-accession">' + esc(documentAccession(document)) + '</dd></div></dl>' + sourceAction + '</article>';
    }).join('') + '</div>';
  }

  function renderStatements(target) {
    var periods = Array.isArray(target.periods) ? target.periods : [];
    if (!periods.length) {
      ui.statements.innerHTML = emptyState('No statement periods available', '暂无财务报表期间',
        'The source state has no normalized periods for this company.', '来源状态中没有该公司的标准化期间。', '—');
      return;
    }
    var header = '<th>' + pair('Period / filed', '期间 / 披露日') + '</th>' + METRICS.map(function (metric) {
      return '<th>' + pair(metric.en, metric.zh) + '</th>';
    }).join('');
    var rows = periods.map(function (period) {
      var first = '<td data-label-en="Period / filed" data-label-zh="期间 / 披露日">' + esc(periodLabel(period)) +
        '<span class="ff-period-filed">' + esc(formatDate(period.filed || period.period_end)) + '</span></td>';
      return '<tr>' + first + METRICS.map(function (metric) {
        return '<td data-label-en="' + esc(metric.en) + '" data-label-zh="' + esc(metric.zh) + '">' +
          sourceControlHtml({ kind: 'statement', compactText: formatValue(period[metric.key], metric.format) }) + '</td>';
      }).join('') + '</tr>';
    }).join('');
    ui.statements.innerHTML = '<div class="ff-table-wrap"><table class="ff-table"><thead><tr>' + header +
      '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  function renderCompareControls(target) {
    var periods = Array.isArray(target.periods) ? target.periods : [];
    if (!periods.length) {
      ui.currentPeriod.innerHTML = '';
      ui.priorPeriod.innerHTML = '';
      ui.currentPeriod.disabled = true;
      ui.priorPeriod.disabled = true;
      return;
    }
    state.currentPeriod = Math.min(state.currentPeriod, periods.length - 1);
    state.priorPeriod = Math.min(state.priorPeriod, periods.length - 1);
    var options = periods.map(function (period, index) {
      var suffix = period.period_end ? ' · ' + formatDate(period.period_end) : '';
      return '<option value="' + index + '">' + esc(periodLabel(period) + suffix) + '</option>';
    }).join('');
    ui.currentPeriod.disabled = false;
    ui.priorPeriod.disabled = false;
    ui.currentPeriod.innerHTML = options;
    ui.priorPeriod.innerHTML = options;
    ui.currentPeriod.value = String(state.currentPeriod);
    ui.priorPeriod.value = String(state.priorPeriod);
  }

  function renderCompare(target) {
    var periods = Array.isArray(target.periods) ? target.periods : [];
    if (!periods.length) {
      ui.compareGrid.innerHTML = emptyState('No periods to compare', '暂无可对比期间',
        'At least one reported period is required.', '至少需要一个披露期间。', '—');
      return;
    }
    var current = periods[state.currentPeriod] || periods[0];
    var prior = periods[state.priorPeriod] || periods[0];
    ui.compareGrid.innerHTML = METRICS.map(function (metric) {
      var currentNumber = numberValue(current[metric.key]);
      var priorNumber = numberValue(prior[metric.key]);
      var delta = currentNumber != null && priorNumber != null ? currentNumber - priorNumber : null;
      var pct = delta != null && priorNumber !== 0 ? delta / Math.abs(priorNumber) : null;
      var deltaText = delta == null ? '—' : formatSigned(delta, metric.format);
      if (pct != null) deltaText += ' · ' + formatSigned(pct, 'percent');
      return '<article class="ff-compare-card"><h3>' + pair(metric.en, metric.zh) + '</h3>' +
        '<div class="ff-compare-values"><div class="ff-compare-value"><span>' + pair('Current · ' + periodLabel(current), '本期 · ' + periodLabel(current)) +
        '</span>' + sourceControlHtml({ kind: 'cell', compactText: formatValue(current[metric.key], metric.format) }) + '</div>' +
        '<div class="ff-compare-value"><span>' + pair('Prior · ' + periodLabel(prior), '上期 · ' + periodLabel(prior)) +
        '</span>' + sourceControlHtml({ kind: 'cell', compactText: formatValue(prior[metric.key], metric.format) }) + '</div></div>' +
        '<div class="ff-compare-delta">' + pair('Change ' + deltaText, '变化 ' + deltaText) + '</div></article>';
    }).join('');
  }

  function companyFactsUrl(target) {
    var source = state.payload.source || {};
    var pattern = String(source.companyfacts_url_pattern || '');
    if (!pattern) return '';
    var cikRaw = String(target.cik || '').replace(/\D/g, '');
    var cikPadded = cikRaw ? cikRaw.padStart(10, '0') : '';
    var expanded = pattern
      .replace(/\{cik_padded\}/gi, cikPadded)
      .replace(/\{cik10\}/gi, cikPadded)
      .replace(/\{cik\}/gi, cikRaw)
      .replace(/\{symbol\}/gi, encodeURIComponent(target.symbol || state.symbol));
    return safeUrl(expanded);
  }

  function normalizeDetectors() {
    var raw = state.payload.detectors || [];
    if (Array.isArray(raw)) {
      return raw.map(function (item, index) {
        return typeof item === 'object' ? Object.assign({ key: item.key || item.id || 'detector-' + (index + 1) }, item) : { key: String(item) };
      });
    }
    if (typeof raw === 'object') {
      return Object.keys(raw).map(function (key) {
        var item = raw[key];
        return typeof item === 'object' ? Object.assign({ key: key }, item) : { key: key, description: String(item) };
      });
    }
    return [];
  }

  function renderTrace(target) {
    var source = state.payload.source || {};
    var coverage = target.coverage || {};
    var findings = orderedFindings(target);
    var evidenceCount = findings.reduce(function (total, finding) {
      return total + (Array.isArray(finding.evidence) ? finding.evidence.length : 0);
    }, 0);
    var sourceEn = localized(source.label, 'en') || 'Source';
    var sourceZh = translatedDataPhrase(localized(source.label, 'zh') || sourceEn, 'zh');
    var basisEn = localized(source.basis, 'en') || localized(coverage.basis, 'en') || '—';
    var basisZh = translatedDataPhrase(
      localized(source.basis, 'zh') || localized(coverage.basis, 'zh') || basisEn, 'zh'
    );
    var sourceUrl = companyFactsUrl(target);
    var limitationsEn = Array.isArray(source.limitations_en) ? source.limitations_en : [];
    var limitationsZh = Array.isArray(source.limitations_zh) ? source.limitations_zh : [];
    var limitationCount = Math.max(limitationsEn.length, limitationsZh.length);
    var limitations = '';
    for (var limitIndex = 0; limitIndex < limitationCount; limitIndex += 1) {
      limitations += '<li>' + pair(limitationsEn[limitIndex] || limitationsZh[limitIndex], limitationsZh[limitIndex] || limitationsEn[limitIndex]) + '</li>';
    }
    if (!limitations) limitations = '<li>' + pair('No source-level limitation was supplied.', '未提供来源层面的局限说明。') + '</li>';

    var detectors = normalizeDetectors();
    var detectorHtml = detectors.length ? detectors.map(function (detector) {
      var nameEn = detector.label_en || detector.name_en || detector.title_en || prettify(detector.key);
      var nameZh = detector.label_zh || detector.name_zh || detector.title_zh || '规则：' + prettify(detector.key);
      var meta = [detector.key, detector.version, detector.status].filter(Boolean).join(' · ');
      return '<li class="ff-detector-item"><div class="ff-detector-name">' + pair(nameEn, nameZh) + '</div>' +
        '<div class="ff-detector-meta">' + esc(meta || '—') + '</div></li>';
    }).join('') : '<li class="ff-detector-item">' + pair('No detector registry supplied.', '未提供检测器清单。') + '</li>';

    var traceFindings = findings.length ? findings.map(function (finding) {
      var receipts = Array.isArray(finding.evidence) ? finding.evidence : [];
      var receiptLinks = receipts.length ? receipts.map(function (receipt) {
        var href = safeUrl(receipt.url);
        var label = fieldPair(receipt, 'label', 'SEC source');
        return href ? '<a class="ff-trace-receipt" href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">' +
          '<span aria-hidden="true">↗</span>' + label + '</a>' : '<span class="ff-trace-receipt">' + label + '</span>';
      }).join('') : '<span class="ff-trace-receipt">' + pair('No source link supplied', '未提供来源链接') + '</span>';
      return '<article class="ff-trace-finding"><div class="ff-trace-finding-head"><div><p class="ff-kicker">' +
        topicPair(finding.topic) + ' · ' + esc(finding.detector || '—') + '</p><h3>' + fieldPair(finding, 'title', 'Untitled finding') +
        '</h3></div><button class="ff-trace-open" type="button" data-open-finding="' + esc(finding.id) + '">' +
        pair('See details', '查看详情') + '</button></div><code class="ff-proof-code">' +
        fieldPair(finding, 'formula', 'Formula not supplied') + '</code><div class="ff-trace-receipts">' + receiptLinks + '</div></article>';
    }).join('') : emptyState('No source-map findings', '暂无来源映射发现',
      'There are no findings to map for this company.', '该公司暂无可映射来源的发现。', '—');

    var disclosureTrack = selectedDisclosureTrack(target);
    var disclosureDocs = disclosureDocuments(target);
    var disclosureFindingItems = disclosureFindings(target);
    var disclosureRedlineItems = activeRedlines(target);
    var disclosureLinks = disclosureDocs.map(function (document) {
      var href = documentSourceUrl(document);
      var label = [document.form || document.form_type || 'SEC filing', documentAccession(document)].filter(Boolean).join(' · ');
      return href ? '<a class="ff-trace-receipt" href="' + esc(href) + '" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">↗</span>' + esc(label) + '</a>' :
        '<span class="ff-trace-receipt">' + esc(label) + '</span>';
    }).join('');
    var disclosureTrace = disclosureTrack ? '<section class="ff-trace-card"><p class="ff-kicker">' +
      pair('Wording comparison', '措辞对比') + '</p><h3>' + pair('The two filings used here', '本次使用的两份财报') + '</h3><p>' + pair(
        disclosureFindingItems.length + ' results · ' + disclosureRedlineItems.length + ' wording changes',
        disclosureFindingItems.length + ' 项结果 · ' + disclosureRedlineItems.length + ' 条措辞变化'
      ) + '</p><div class="ff-trace-receipts">' + (disclosureLinks || '<span class="ff-trace-receipt">' + pair('No filing link supplied', '未提供财报链接') + '</span>') + '</div></section>' :
      '<section class="ff-trace-card"><p class="ff-kicker">' + pair('Wording comparison', '措辞对比') + '</p><h3>' + pair('Not available yet', '暂不可用') + '</h3><p>' + pair(
        'Wording changes appear when two matching SEC filings are available.',
        '当有两份匹配的 SEC 财报时，这里会显示措辞变化。'
      ) + '</p></section>';

    ui.trace.innerHTML = '<div class="ff-trace-grid"><div><section class="ff-trace-card"><p class="ff-kicker">' +
      pair('Data source', '数据来源') + '</p><h3>' + pair(sourceEn, sourceZh) + '</h3><p>' + pair(basisEn, basisZh) + '</p>' +
      '<div class="ff-coverage-grid"><div class="ff-coverage-stat"><small>' + pair('Periods', '期间数') + '</small><strong>' +
      esc(coverage.periods == null ? (Array.isArray(target.periods) ? target.periods.length : 0) : coverage.periods) + '</strong></div>' +
      '<div class="ff-coverage-stat"><small>' + pair('Metric coverage', '指标覆盖率') + '</small><strong>' +
      esc(coverage.metrics_pct == null ? '—' : formatPercent(coverage.metrics_pct)) + '</strong></div>' +
      '<div class="ff-coverage-stat"><small>' + pair('Signals', '信号数') + '</small><strong>' + findings.length + '</strong></div>' +
      '<div class="ff-coverage-stat"><small>' + pair('Source links', '来源链接') + '</small><strong>' + evidenceCount + '</strong></div></div>' +
      (sourceUrl ? '<a class="ff-source-link" href="' + esc(sourceUrl) + '" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">↗</span>' +
        pair('Open Company Facts at the SEC', '在 SEC 打开公司事实数据') + '</a>' : '') +
      '<details class="ff-trace-details"><summary>' + pair('What to know about this data', '关于这些数据需要了解') + '</summary><div class="ff-proof-section"><ul class="ff-source-limitations">' + limitations + '</ul></div></details></section>' +
      '<section class="ff-trace-card"><details class="ff-trace-details"><summary>' + pair('How signals are detected', '信号如何识别') + '</summary><div><ul class="ff-detector-list">' + detectorHtml + '</ul></div></details></section>' + disclosureTrace + '</div>' +
      '<div class="ff-trace-findings">' + traceFindings + '</div></div>';
  }

  // The sealed history surface is deliberately a reading layer. It never
  // replays source material, produces a score, or turns a receipt into a
  // broader issuer conclusion. Keep all request-time data bounded to one root
  // page plus the one waterfall the analyst has explicitly opened.
  function normalizedCik(value) {
    var digits = String(value == null ? '' : value).trim();
    return /^\d{1,10}$/.test(digits) ? digits.padStart(10, '0') : '';
  }

  function isSnapshotId(value) {
    return /^ffqsv2_[a-f0-9]{64}$/.test(String(value || ''));
  }

  function isBaseSnapshotId(value) {
    return /^ffqs_[a-f0-9]{64}$/.test(String(value || ''));
  }

  function isRootCellId(value) {
    return /^metric_cell_[a-f0-9]{64}$/.test(String(value || ''));
  }

  function isReceiptObject(value) {
    return Object.prototype.toString.call(value) === '[object Object]';
  }

  function hasExactReceiptKeys(value, keys) {
    if (!isReceiptObject(value)) return false;
    var actual = Object.keys(value).sort();
    var expected = keys.slice().sort();
    return actual.length === expected.length && actual.every(function (key, index) {
      return key === expected[index];
    });
  }

  function isSafeReceiptInteger(value) {
    return Number.isSafeInteger(value) && value >= 0;
  }

  function isBoundedReceiptText(value, maximum) {
    return typeof value === 'string' && value.length > 0 && value.length <= maximum;
  }

  function receiptUtcOrderKey(value) {
    if (typeof value !== 'string' || value.length > 64) return null;
    var match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{6}))?Z$/.exec(value);
    if (!match) return null;
    var year = Number(match[1]);
    var month = Number(match[2]);
    var day = Number(match[3]);
    var hour = Number(match[4]);
    var minute = Number(match[5]);
    var second = Number(match[6]);
    if (year < 1 || month < 1 || month > 12 || day < 1 || day > 31 ||
        hour > 23 || minute > 59 || second > 59) return null;
    var calendar = new Date(0);
    calendar.setUTCHours(0, 0, 0, 0);
    calendar.setUTCFullYear(year, month - 1, day);
    calendar.setUTCHours(hour, minute, second, 0);
    if (calendar.getUTCFullYear() !== year || calendar.getUTCMonth() !== month - 1 ||
        calendar.getUTCDate() !== day || calendar.getUTCHours() !== hour ||
        calendar.getUTCMinutes() !== minute || calendar.getUTCSeconds() !== second) return null;
    return match.slice(1, 7).join('') + (match[7] || '000000');
  }

  function isReceiptDate(value, nullable) {
    if (value === null && nullable) return true;
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    var parts = value.split('-').map(Number);
    if (parts[0] < 1 || parts[1] < 1 || parts[1] > 12 || parts[2] < 1 || parts[2] > 31) return false;
    var parsed = new Date(0);
    parsed.setUTCHours(0, 0, 0, 0);
    parsed.setUTCFullYear(parts[0], parts[1] - 1, parts[2]);
    return parsed.getUTCFullYear() === parts[0] && parsed.getUTCMonth() === parts[1] - 1 &&
      parsed.getUTCDate() === parts[2];
  }

  function receiptArraysEqual(left, right) {
    return Array.isArray(left) && Array.isArray(right) && left.length === right.length &&
      left.every(function (value, index) { return value === right[index]; });
  }

  function receiptStringList(value, pattern) {
    if (!Array.isArray(value) || value.length > 1024) return null;
    var previous = null;
    for (var index = 0; index < value.length; index += 1) {
      var current = value[index];
      if (typeof current !== 'string' || !pattern.test(current) ||
          (previous !== null && current <= previous)) return null;
      previous = current;
    }
    return value.slice();
  }

  function receiptSubset(subset, superset) {
    var allowed = new Set(superset);
    return subset.every(function (value) { return allowed.has(value); });
  }

  function checkedReceiptRoot(value) {
    if (!hasExactReceiptKeys(value, [
      'root_cell_id', 'selected_leaf_occurrence_ids', 'eligible_leaf_occurrence_ids',
      'attested_occurrence_ids', 'status'
    ]) || !isRootCellId(value.root_cell_id)) return null;
    var occurrencePattern = /^rawfact_[a-f0-9]{64}$/;
    var selected = receiptStringList(value.selected_leaf_occurrence_ids, occurrencePattern);
    var eligible = receiptStringList(value.eligible_leaf_occurrence_ids, occurrencePattern);
    var attested = receiptStringList(value.attested_occurrence_ids, occurrencePattern);
    if (!selected || !eligible || !attested || selected.length + eligible.length + attested.length > 3072 ||
        !receiptSubset(eligible, selected) || !receiptSubset(attested, eligible)) return null;
    var expectedStatus;
    if (!selected.length || !eligible.length) expectedStatus = 'not_evaluable';
    else if (eligible.length === selected.length && attested.length === selected.length) expectedStatus = 'all_leaves_attested';
    else if (attested.length) expectedStatus = 'partially_attested';
    else expectedStatus = 'not_attested';
    if (value.status !== expectedStatus) return null;
    return {
      root_cell_id: value.root_cell_id,
      selected_leaf_occurrence_ids: selected,
      eligible_leaf_occurrence_ids: eligible,
      attested_occurrence_ids: attested,
      status: expectedStatus
    };
  }

  function checkedReceiptAuthority(value) {
    if (!hasExactReceiptKeys(value, [
      'positive_claim', 'coverage_scope', 'claim_basis', 'source_reverified_at_read',
      'match_body_replayed_at_read', 'nonclaims'
    ]) || value.positive_claim !== 'B3_selected_member_companyfacts_row_correspondence_only' ||
        value.coverage_scope !== 'selected_raw_fact_leaves_only' ||
        value.claim_basis !== 'sealed_publication_receipt' ||
        value.source_reverified_at_read !== false || value.match_body_replayed_at_read !== false ||
        !isReceiptObject(value.nonclaims)) return null;
    var nonclaimKeys = Object.keys(value.nonclaims);
    if (!nonclaimKeys.length || nonclaimKeys.some(function (key) { return value.nonclaims[key] !== false; }) ||
        value.nonclaims.filing_complete !== false || value.nonclaims.trading_authority !== false ||
        value.nonclaims.neural_web_authority !== false) return null;
    return value;
  }

  function sameReceiptAuthority(left, right) {
    var leftAuthority = checkedReceiptAuthority(left);
    var rightAuthority = checkedReceiptAuthority(right);
    if (!leftAuthority || !rightAuthority) return false;
    var leftKeys = Object.keys(leftAuthority.nonclaims).sort();
    var rightKeys = Object.keys(rightAuthority.nonclaims).sort();
    return receiptArraysEqual(leftKeys, rightKeys);
  }

  function checkedReceiptIdentity(value) {
    if (!isReceiptObject(value) || !isSnapshotId(value.snapshot_id) ||
        !isBaseSnapshotId(value.base_snapshot_id) || !/^[a-f0-9]{64}$/.test(String(value.query_hash || '')) ||
        receiptUtcOrderKey(value.published_at) === null) return null;
    return {
      snapshot_id: value.snapshot_id,
      base_snapshot_id: value.base_snapshot_id,
      query_hash: value.query_hash,
      published_at: value.published_at
    };
  }

  function sameReceiptIdentity(value, expected) {
    var actual = checkedReceiptIdentity(value);
    var wanted = checkedReceiptIdentity(expected);
    return !!actual && !!wanted && actual.snapshot_id === wanted.snapshot_id &&
      actual.base_snapshot_id === wanted.base_snapshot_id && actual.query_hash === wanted.query_hash &&
      actual.published_at === wanted.published_at;
  }

  function checkedSnapshotClocks(value, publishedAt) {
    var keys = [
      'query_source_snapshot_at', 'query_recorded_at', 'query_computed_at', 'query_published_at',
      'operator_verification_observed_at', 'published_at'
    ];
    if (!hasExactReceiptKeys(value, keys) || value.published_at !== publishedAt) return null;
    var clocks = {};
    for (var index = 0; index < keys.length; index += 1) {
      clocks[keys[index]] = receiptUtcOrderKey(value[keys[index]]);
      if (clocks[keys[index]] === null) return null;
    }
    var latestInput = clocks.query_source_snapshot_at > clocks.query_recorded_at ?
      clocks.query_source_snapshot_at : clocks.query_recorded_at;
    if (clocks.query_computed_at < latestInput ||
        clocks.query_published_at < clocks.query_computed_at ||
        clocks.operator_verification_observed_at < clocks.query_published_at ||
        clocks.published_at < clocks.operator_verification_observed_at) return null;
    return value;
  }

  function checkedCoverageSummary(value) {
    var countKeys = ['root_cell_count', 'all_leaves_attested', 'partially_attested', 'not_attested', 'not_evaluable'];
    if (!hasExactReceiptKeys(value, ['coverage_scope', 'positive_label'].concat(countKeys)) ||
        value.coverage_scope !== 'selected_raw_fact_leaves_only' ||
        value.positive_label !== 'B3_selected_member_companyfacts_row_correspondence_only' ||
        countKeys.some(function (key) { return !isSafeReceiptInteger(value[key]); })) return null;
    var statusTotal = value.all_leaves_attested + value.partially_attested + value.not_attested + value.not_evaluable;
    return value.root_cell_count === statusTotal && value.root_cell_count <= 100000 ? value : null;
  }

  function checkedConversionReceipt(value) {
    var keys = [
      'receipt_id', 'schema', 'adapter_version', 'capture_id', 'manifest_id', 'cik', 'clocks',
      'availability', 'occurrence_count', 'output_occurrence_count', 'pit_eligible_count'
    ];
    var clockKeys = [
      'acquisition_started_at', 'captured_at', 'recorded_at', 'source_snapshot_at', 'submissions_recorded_at'
    ];
    if (!hasExactReceiptKeys(value, keys) || !/^cffledger_[a-f0-9]{64}$/.test(String(value.receipt_id || '')) ||
        value.schema !== 'fundamental_forensics.companyfacts_ledger_receipt/v2' ||
        !isBoundedReceiptText(value.adapter_version, 128) ||
        !/^ffseccfc_[a-f0-9]{64}$/.test(String(value.capture_id || '')) ||
        !/^ffseccfm_[a-f0-9]{64}$/.test(String(value.manifest_id || '')) ||
        !/^\d{10}$/.test(String(value.cik || '')) ||
        !hasExactReceiptKeys(value.clocks, clockKeys) ||
        clockKeys.some(function (key) { return receiptUtcOrderKey(value.clocks[key]) === null; }) ||
        ['available', 'partial'].indexOf(value.availability) === -1 ||
        !isSafeReceiptInteger(value.occurrence_count) || !isSafeReceiptInteger(value.output_occurrence_count) ||
        !isSafeReceiptInteger(value.pit_eligible_count) || value.occurrence_count !== value.output_occurrence_count ||
        value.pit_eligible_count > value.output_occurrence_count) return null;
    return value;
  }

  function checkedLatestReceipt(value) {
    var keys = [
      'snapshot_id', 'base_snapshot_id', 'query_hash', 'published_at', 'policy', 'clocks',
      'coverage_summary', 'companyfacts_conversion_receipt', 'authority'
    ];
    var identity = checkedReceiptIdentity(value);
    if (!hasExactReceiptKeys(value, keys) || !identity ||
        !hasExactReceiptKeys(value.policy, ['version', 'fingerprint']) ||
        value.policy.version !== 'ffqsv2_exact_join/v1' ||
        value.policy.fingerprint !== '6e4ba04cf9c775ac280ba1426985246ffbdf730222b4521c4b26a41f5623871a' ||
        !checkedSnapshotClocks(value.clocks, value.published_at) ||
        !checkedCoverageSummary(value.coverage_summary) ||
        !checkedConversionReceipt(value.companyfacts_conversion_receipt) ||
        !checkedReceiptAuthority(value.authority)) return null;
    return value;
  }

  function shortTraceId(value) {
    var text = String(value || '');
    if (text.length <= 22) return text || '—';
    return text.slice(0, 14) + '…' + text.slice(-6);
  }

  function selectedReceiptRootButton() {
    var wanted = String(state.receipt.rootCellId || '');
    return Array.prototype.find.call(document.querySelectorAll('[data-root-cell-id]'), function (candidate) {
      return candidate.getAttribute('data-root-cell-id') === wanted;
    }) || null;
  }

  function receiptStatusInfo(status) {
    var known = {
      all_leaves_attested: {
        key: 'all',
        en: 'All selected leaves have correspondence',
        zh: '所有选定叶节点均有对应记录'
      },
      partially_attested: {
        key: 'partial',
        en: 'Some selected leaves have correspondence',
        zh: '部分选定叶节点有对应记录'
      },
      not_attested: {
        key: 'none',
        en: 'No selected leaf correspondence recorded',
        zh: '未记录选定叶节点对应关系'
      },
      not_evaluable: {
        key: 'not-evaluable',
        en: 'No eligible selected leaf',
        zh: '没有符合条件的选定叶节点'
      }
    };
    return known[String(status || '')] || {
      key: 'unknown',
      en: 'Receipt state unavailable',
      zh: '凭据状态不可用'
    };
  }

  function receiptCount(value) {
    return Array.isArray(value) ? value.length : 0;
  }

  function compactReceiptRoot(value) {
    var root = checkedReceiptRoot(value);
    if (!root) return null;
    return {
      root_cell_id: root.root_cell_id,
      status: root.status,
      selected: root.selected_leaf_occurrence_ids.length,
      eligible: root.eligible_leaf_occurrence_ids.length,
      attested: root.attested_occurrence_ids.length,
      selected_leaf_occurrence_ids: root.selected_leaf_occurrence_ids,
      eligible_leaf_occurrence_ids: root.eligible_leaf_occurrence_ids,
      attested_occurrence_ids: root.attested_occurrence_ids
    };
  }

  function receiptReadyPayload(value) {
    return !!checkedLatestReceipt(value);
  }

  function checkedReceiptPagePayload(value, latest, requestedCursor, pageIndex, previousTotal) {
    var keys = [
      'snapshot_id', 'base_snapshot_id', 'query_hash', 'published_at', 'authority', 'page', 'roots'
    ];
    var pageKeys = ['cursor', 'next_cursor', 'limit', 'returned', 'total'];
    var expectedCursor = requestedCursor || null;
    if (!hasExactReceiptKeys(value, keys) || !sameReceiptIdentity(value, latest) ||
        !sameReceiptAuthority(value.authority, latest.authority) ||
        !hasExactReceiptKeys(value.page, pageKeys) || !Array.isArray(value.roots) ||
        value.page.cursor !== expectedCursor || value.page.limit !== 25 ||
        !isSafeReceiptInteger(value.page.returned) || !isSafeReceiptInteger(value.page.total) ||
        value.page.returned !== value.roots.length || value.page.returned > value.page.limit ||
        value.page.total !== latest.coverage_summary.root_cell_count ||
        (previousTotal !== null && previousTotal !== value.page.total) ||
        (pageIndex === 0 && expectedCursor !== null) || (pageIndex > 0 && !isRootCellId(expectedCursor))) return null;
    var roots = [];
    var leafReferences = 0;
    var previousRootId = expectedCursor;
    for (var index = 0; index < value.roots.length; index += 1) {
      var root = checkedReceiptRoot(value.roots[index]);
      if (!root || (previousRootId !== null && root.root_cell_id <= previousRootId)) return null;
      leafReferences += root.selected_leaf_occurrence_ids.length + root.eligible_leaf_occurrence_ids.length +
        root.attested_occurrence_ids.length;
      if (leafReferences > 12288) return null;
      roots.push(compactReceiptRoot(root));
      previousRootId = root.root_cell_id;
    }
    var nextCursor = value.page.next_cursor;
    if (nextCursor !== null && (!isRootCellId(nextCursor) || !roots.length ||
        nextCursor !== roots[roots.length - 1].root_cell_id || roots.length !== value.page.limit)) return null;
    if (!roots.length && nextCursor !== null) return null;
    var consumed = pageIndex * value.page.limit + roots.length;
    if (consumed > value.page.total || (nextCursor === null && consumed !== value.page.total) ||
        (nextCursor !== null && consumed >= value.page.total)) return null;
    return {
      cursor: value.page.cursor,
      nextCursor: nextCursor,
      returned: value.page.returned,
      total: value.page.total,
      rows: roots
    };
  }

  function receiptDecimalText(value) {
    return typeof value === 'string' && value.length <= 4096 && value !== '-0' &&
      /^-?(?:0|[1-9]\d*)(?:\.\d*[1-9])?$/.test(value);
  }

  function checkedReceiptWaterfallRow(value, occurrenceId, eligible, attested, latest) {
    if (!isReceiptObject(value) || value.occurrence_id !== occurrenceId ||
        value.eligible !== eligible || value.attested !== attested) return null;
    if (!attested) {
      return hasExactReceiptKeys(value, ['occurrence_id', 'eligible', 'attested']) ? value : null;
    }
    var keys = [
      'occurrence_id', 'eligible', 'attested', 'attestation_id', 'match_id', 'companyfacts',
      'stored_b3_projection'
    ];
    var companyfactsKeys = ['cik', 'accession', 'taxonomy', 'concept', 'unit', 'period', 'value'];
    var projectionKeys = [
      'attestation_id', 'authority_snapshot_id', 'package_id', 'extraction_id', 'cik', 'accession',
      'companyfacts_capture_id', 'companyfacts_manifest_id', 'companyfacts_response_sha256',
      'companyfacts_match_count', 'attested_at'
    ];
    var companyfacts = value.companyfacts;
    var projection = value.stored_b3_projection;
    var conversion = latest.companyfacts_conversion_receipt;
    if (!eligible || !hasExactReceiptKeys(value, keys) ||
        !/^ffatt_[a-f0-9]{64}$/.test(String(value.attestation_id || '')) ||
        !/^ffatt_match_[a-f0-9]{64}$/.test(String(value.match_id || '')) ||
        !hasExactReceiptKeys(companyfacts, companyfactsKeys) ||
        !hasExactReceiptKeys(companyfacts.period, ['start', 'end']) ||
        companyfacts.cik !== conversion.cik || !/^\d{10}-\d{2}-\d{6}$/.test(String(companyfacts.accession || '')) ||
        !isBoundedReceiptText(companyfacts.taxonomy, 256) || !isBoundedReceiptText(companyfacts.concept, 256) ||
        !isBoundedReceiptText(companyfacts.unit, 256) || !isReceiptDate(companyfacts.period.start, true) ||
        !isReceiptDate(companyfacts.period.end, false) || !receiptDecimalText(companyfacts.value) ||
        !hasExactReceiptKeys(projection, projectionKeys) || projection.attestation_id !== value.attestation_id ||
        !/^ffsecsrc_[a-f0-9]{64}$/.test(String(projection.authority_snapshot_id || '')) ||
        !/^ffpkg_[a-f0-9]{64}$/.test(String(projection.package_id || '')) ||
        !/^ffxbrl_[a-f0-9]{64}$/.test(String(projection.extraction_id || '')) ||
        projection.cik !== companyfacts.cik || projection.accession !== companyfacts.accession ||
        projection.companyfacts_capture_id !== conversion.capture_id ||
        projection.companyfacts_manifest_id !== conversion.manifest_id ||
        !/^[a-f0-9]{64}$/.test(String(projection.companyfacts_response_sha256 || '')) ||
        !Number.isSafeInteger(projection.companyfacts_match_count) || projection.companyfacts_match_count <= 0 ||
        receiptUtcOrderKey(projection.attested_at) === null) return null;
    return value;
  }

  function checkedReceiptDetailPayload(value, latest, rootCellId, cachedRoot) {
    var keys = [
      'snapshot_id', 'base_snapshot_id', 'query_hash', 'published_at', 'authority', 'root', 'waterfall'
    ];
    if (!hasExactReceiptKeys(value, keys) || !sameReceiptIdentity(value, latest) ||
        !sameReceiptAuthority(value.authority, latest.authority) || !Array.isArray(value.waterfall) ||
        value.waterfall.length > 1024) return null;
    var root = checkedReceiptRoot(value.root);
    if (!root || root.root_cell_id !== rootCellId || !cachedRoot ||
        root.status !== cachedRoot.status ||
        !receiptArraysEqual(root.selected_leaf_occurrence_ids, cachedRoot.selected_leaf_occurrence_ids) ||
        !receiptArraysEqual(root.eligible_leaf_occurrence_ids, cachedRoot.eligible_leaf_occurrence_ids) ||
        !receiptArraysEqual(root.attested_occurrence_ids, cachedRoot.attested_occurrence_ids) ||
        value.waterfall.length !== root.selected_leaf_occurrence_ids.length) return null;
    var eligible = new Set(root.eligible_leaf_occurrence_ids);
    var attested = new Set(root.attested_occurrence_ids);
    var recordedPairs = new Set();
    var waterfall = [];
    for (var index = 0; index < root.selected_leaf_occurrence_ids.length; index += 1) {
      var occurrenceId = root.selected_leaf_occurrence_ids[index];
      var row = checkedReceiptWaterfallRow(
        value.waterfall[index], occurrenceId, eligible.has(occurrenceId), attested.has(occurrenceId), latest
      );
      if (!row) return null;
      if (row.attested) {
        var pairKey = row.attestation_id + ':' + row.match_id;
        if (recordedPairs.has(pairKey)) return null;
        recordedPairs.add(pairKey);
      }
      waterfall.push(row);
    }
    return {root: compactReceiptRoot(root), waterfall: waterfall};
  }

  function resetReceiptState() {
    var token = state.receipt.requestToken + 1;
    state.receipt = {
      phase: 'idle',
      requestToken: token,
      latest: null,
      ownerCik: '',
      page: null,
      pageCursors: [null],
      pageIndex: 0,
      rootCellId: '',
      detail: null,
      detailPhase: 'idle',
      lastFocus: null
    };
    closeReceiptInspector(false);
  }

  function historyRequest(path) {
    return withAuth({ Accept: 'application/json' })
      .then(function (headers) {
        return fetch(ATTESTED_HISTORY_URL + path, {
          headers: headers,
          credentials: 'same-origin',
          cache: 'no-store'
        });
      })
      .then(function (response) {
        if (!response.ok) {
          var failure = new Error('History request failed');
          failure.status = response.status;
          throw failure;
        }
        return response.json();
      });
  }

  function receiptOwnerMatches(target, receipt) {
    var selected = normalizedCik(target && target.cik);
    var conversion = receipt && receipt.companyfacts_conversion_receipt;
    return !!selected && !!conversion && selected === normalizedCik(conversion.cik);
  }

  function setSourceMode(mode, focusPanel) {
    var next = mode === 'receipt' ? 'receipt' : 'map';
    state.sourceMode = next;
    ui.workspace.setAttribute('data-source-mode', next);
    ui.sourceTabs.forEach(function (button) {
      var active = button.getAttribute('data-source-mode') === next;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
      button.tabIndex = active ? 0 : -1;
    });
    ui.sourceMapPanel.hidden = next !== 'map';
    ui.receiptPanel.hidden = next !== 'receipt';
    // Do not retain or resume an in-flight private receipt read after the
    // analyst has returned to the public evidence map. A later receipt open
    // starts a fresh, CIK-gated request instead of stranding the UI in loading.
    if (next === 'receipt') {
      closeReceiptInspector(false);
      ensureReceiptForCompany();
    } else {
      resetReceiptState();
      renderReceiptInspector();
    }
    if (focusPanel) {
      (next === 'receipt' ? ui.receiptPanel : ui.sourceMapPanel).focus({ preventScroll: true });
    }
  }

  function receiptFailurePhase(error) {
    return error && (error.status === 401 || error.status === 403) ? 'access' : 'unavailable';
  }

  function ensureReceiptForCompany() {
    var target = company();
    if (!target || state.sourceMode !== 'receipt') return;
    var cik = normalizedCik(target.cik);
    if (!cik) {
      state.receipt.phase = 'mismatch';
      state.receipt.ownerCik = '';
      renderReceipt();
      return;
    }
    if (state.receipt.ownerCik === cik && (
      state.receipt.phase === 'loading' || state.receipt.phase === 'ready' || state.receipt.phase === 'mismatch'
    )) {
      renderReceipt();
      return;
    }
    resetReceiptState();
    state.receipt.ownerCik = cik;
    state.receipt.phase = 'loading';
    var token = state.receipt.requestToken + 1;
    state.receipt.requestToken = token;
    renderReceipt();
    historyRequest('/latest')
      .then(function (payload) {
        if (token !== state.receipt.requestToken || state.sourceMode !== 'receipt') return;
        if (!receiptReadyPayload(payload)) throw new Error('Receipt identity is malformed');
        if (!receiptOwnerMatches(company(), payload)) {
          state.receipt.latest = payload;
          state.receipt.phase = 'mismatch';
          renderReceipt();
          return;
        }
        state.receipt.latest = payload;
        loadReceiptRoots(null, 0);
      })
      .catch(function (error) {
        if (token !== state.receipt.requestToken || state.sourceMode !== 'receipt') return;
        state.receipt.phase = receiptFailurePhase(error);
        renderReceipt();
      });
  }

  function loadReceiptRoots(cursor, pageIndex) {
    var receipt = state.receipt;
    var latest = receipt.latest;
    if (!latest || !isSnapshotId(latest.snapshot_id) || state.sourceMode !== 'receipt') return;
    var previousTotal = receipt.page ? receipt.page.total : null;
    var token = receipt.requestToken + 1;
    receipt.requestToken = token;
    receipt.phase = 'loading';
    receipt.detail = null;
    receipt.rootCellId = '';
    receipt.detailPhase = 'idle';
    closeReceiptInspector(false);
    renderReceipt();
    var suffix = '/snapshots/' + encodeURIComponent(latest.snapshot_id) + '/roots?limit=25';
    if (cursor) suffix += '&cursor=' + encodeURIComponent(cursor);
    historyRequest(suffix)
      .then(function (payload) {
        if (token !== state.receipt.requestToken || state.sourceMode !== 'receipt') return;
        var page = checkedReceiptPagePayload(payload, latest, cursor || null, pageIndex, previousTotal);
        if (!page) throw new Error('Receipt page is malformed');
        receipt.page = page;
        receipt.pageIndex = pageIndex;
        receipt.phase = 'ready';
        renderReceipt();
      })
      .catch(function (error) {
        if (token !== state.receipt.requestToken || state.sourceMode !== 'receipt') return;
        receipt.phase = receiptFailurePhase(error);
        renderReceipt();
      });
  }

  function receiptPageNext() {
    var receipt = state.receipt;
    if (!receipt.page || !receipt.page.nextCursor) return;
    receipt.pageCursors = receipt.pageCursors.slice(0, receipt.pageIndex + 1);
    receipt.pageCursors.push(receipt.page.nextCursor);
    loadReceiptRoots(receipt.page.nextCursor, receipt.pageIndex + 1);
  }

  function receiptPagePrevious() {
    var receipt = state.receipt;
    if (receipt.pageIndex < 1) return;
    loadReceiptRoots(receipt.pageCursors[receipt.pageIndex - 1], receipt.pageIndex - 1);
  }

  function requestReceiptRoot(rootCellId, trigger) {
    var receipt = state.receipt;
    var latest = receipt.latest;
    if (!latest || !isSnapshotId(latest.snapshot_id) || !isRootCellId(rootCellId)) return;
    var cachedRoot = receipt.page && receipt.page.rows.find(function (row) {
      return row.root_cell_id === rootCellId;
    });
    if (!cachedRoot) return;
    receipt.rootCellId = rootCellId;
    receipt.detail = null;
    receipt.detailPhase = 'loading';
    receipt.lastFocus = trigger || document.activeElement;
    var token = receipt.requestToken + 1;
    receipt.requestToken = token;
    renderReceipt();
    receipt.lastFocus = selectedReceiptRootButton() || trigger || document.activeElement;
    renderReceiptInspector();
    openReceiptInspector();
    historyRequest('/snapshots/' + encodeURIComponent(latest.snapshot_id) + '/roots/' + encodeURIComponent(rootCellId))
      .then(function (payload) {
        if (token !== state.receipt.requestToken || state.sourceMode !== 'receipt') return;
        var detail = checkedReceiptDetailPayload(payload, latest, rootCellId, cachedRoot);
        if (!detail) throw new Error('Receipt detail is malformed');
        receipt.detail = detail;
        receipt.detailPhase = 'ready';
        renderReceiptInspector();
      })
      .catch(function () {
        if (token !== state.receipt.requestToken || state.sourceMode !== 'receipt') return;
        receipt.detail = null;
        receipt.detailPhase = 'unavailable';
        renderReceiptInspector();
      });
  }

  function receiptStatusBadge(status) {
    var info = receiptStatusInfo(status);
    return '<span class="ff-receipt-status is-' + esc(info.key) + '">' + pair(info.en, info.zh) + '</span>';
  }

  function receiptStat(labelEn, labelZh, value) {
    return '<div class="ff-receipt-stat"><small>' + pair(labelEn, labelZh) + '</small><strong>' + esc(value == null ? '—' : value) + '</strong></div>';
  }

  function receiptEmpty(titleEn, titleZh, bodyEn, bodyZh, action) {
    return '<div class="ff-receipt-empty"><span class="ff-empty-mark" aria-hidden="true">◇</span><div><h3>' + pair(titleEn, titleZh) + '</h3><p>' + pair(bodyEn, bodyZh) + '</p>' + (action || '') + '</div></div>';
  }

  function renderReceipt() {
    if (!ui.receipt) return;
    var receipt = state.receipt;
    if (receipt.phase === 'idle') {
      ui.receipt.innerHTML = receiptEmpty(
        'Run record', '运行记录',
        'Open this view to see the saved publication details for the selected company.',
        '打开此视图，查看所选公司的已保存发布详情。'
      );
      renderReceiptInspector();
      return;
    }
    if (receipt.phase === 'loading') {
      ui.receipt.innerHTML = '<div class="ff-loading" role="status"><span class="ff-loading-dot" aria-hidden="true"></span>' +
        pair('Loading run record…', '正在载入运行记录…') + '</div>';
      renderReceiptInspector();
      return;
    }
    if (receipt.phase === 'mismatch') {
      var mismatchEn = receipt.ownerCik ?
        'The available record belongs to a different company, so nothing was loaded.' :
        'This company has no SEC identifier in the dataset, so the record cannot be matched.';
      var mismatchZh = receipt.ownerCik ?
        '可用记录属于另一家公司，因此未载入内容。' :
        '数据集中没有该公司的 SEC 标识，因此无法匹配记录。';
      ui.receipt.innerHTML = receiptEmpty(
        'No run record for this company', '该公司暂无运行记录',
        mismatchEn, mismatchZh
      );
      renderReceiptInspector();
      return;
    }
    if (receipt.phase === 'access') {
      ui.receipt.innerHTML = receiptEmpty(
        'Run record unavailable in this session', '当前会话无法访问运行记录',
        'The source map still works. Sign in again, then retry.',
        '来源地图仍可使用。请重新登录后再试。',
        '<button class="ff-receipt-retry" type="button" data-receipt-action="retry">' + pair('Retry', '重试') + '</button>'
      );
      renderReceiptInspector();
      return;
    }
    if (receipt.phase !== 'ready' || !receipt.latest || !receipt.page) {
      ui.receipt.innerHTML = receiptEmpty(
        'Run record temporarily unavailable', '运行记录暂时不可用',
        'The source map still works. Try this view again in a moment.',
        '来源地图仍可使用。请稍后再试。',
        '<button class="ff-receipt-retry" type="button" data-receipt-action="retry">' + pair('Retry', '重试') + '</button>'
      );
      renderReceiptInspector();
      return;
    }

    var latest = receipt.latest;
    var coverage = latest.coverage_summary || {};
    var authority = latest.authority || {};
    var conversion = latest.companyfacts_conversion_receipt || {};
    var clocks = conversion.clocks || {};
    var policy = latest.policy || {};
    var rows = receipt.page.rows;
    var rootRows = rows.length ? rows.map(function (root) {
      var selected = receipt.rootCellId === root.root_cell_id;
      return '<button class="ff-receipt-root' + (selected ? ' is-selected' : '') + '" type="button" data-root-cell-id="' + esc(root.root_cell_id) + '"' +
        ' aria-controls="ff-receipt-inspector" aria-current="' + (selected ? 'true' : 'false') + '"><span class="ff-receipt-root-id"><code title="' + esc(root.root_cell_id) + '">' +
        esc(shortTraceId(root.root_cell_id)) + '</code><small>' + pair(root.selected + ' selected · ' + root.eligible + ' eligible · ' + root.attested + ' recorded', root.selected + ' 个选定 · ' + root.eligible + ' 个符合条件 · ' + root.attested + ' 个已记录') +
        '</small></span>' + receiptStatusBadge(root.status) + '<span class="ff-receipt-root-arrow" aria-hidden="true">›</span></button>';
    }).join('') : receiptEmpty(
      'No root coverage rows', '没有根覆盖行',
      'The sealed receipt contains no root coverage rows.',
      '该密封凭据不包含根覆盖行。'
    );
    var previousDisabled = receipt.pageIndex < 1 ? ' disabled' : '';
    var nextDisabled = !receipt.page.nextCursor ? ' disabled' : '';
    var nonclaims = authority.nonclaims || {};
    var limits = [];
    if (nonclaims.filing_complete === false) limits.push(pair('Does not establish filing completeness.', '不证明披露文件完整性。'));
    if (nonclaims.trading_authority === false) limits.push(pair('Does not grant trading authority.', '不授予交易决策权限。'));
    if (nonclaims.neural_web_authority === false) limits.push(pair('Does not grant Neural Web authority.', '不授予 Neural Web 权限。'));

    ui.receipt.innerHTML = '<div class="ff-receipt-intro"><div><p class="ff-kicker">' + pair('Sealed publication receipt', '密封发布凭据') +
      '</p><h3>' + pair('Recorded correspondence, read at its stated scope', '在声明范围内读取已记录的对应关系') + '</h3><p>' + pair(
        'This view reads a stored receipt. Source material is not reread while you inspect it.',
        '此视图读取存储的凭据；检查期间不会重新读取来源材料。'
      ) + '</p></div><span class="ff-receipt-live-mark" aria-hidden="true">◇</span></div>' +
      '<div class="ff-receipt-identity"><div class="ff-receipt-identity-main"><span>' + pair('Receipt snapshot', '凭据快照') + '</span><code title="' + esc(latest.snapshot_id) + '">' + esc(shortTraceId(latest.snapshot_id)) + '</code></div>' +
      '<div>' + receiptStat('Published', '发布时间', formatDate(latest.published_at)) + '</div>' +
      '<div>' + receiptStat('Issuer CIK', '发行人 CIK', normalizedCik(conversion.cik)) + '</div>' +
      '<div>' + receiptStat('Policy', '策略', policy.version || '—') + '</div></div>' +
      '<section class="ff-receipt-card ff-receipt-authority"><div class="ff-receipt-card-head"><div><p class="ff-kicker">' + pair('Scope', '范围') + '</p><h3>' + pair('What this receipt records', '此凭据记录的内容') + '</h3></div>' +
      '<span class="ff-receipt-scope-mark">' + pair('Scoped', '限定范围') + '</span></div><p>' + pair(
        'Selected Company Facts row correspondence only. The receipt is a sealed publication record, not a source reread.',
        '仅限选定的 Company Facts 行对应关系。该凭据是密封的发布记录，并非来源重读。'
      ) + '</p><ul class="ff-receipt-limits">' + (limits.join('') || '<li>' + pair('No broader authority is supplied.', '未提供更广泛的权限。') + '</li>') + '</ul></section>' +
      '<section class="ff-receipt-card"><div class="ff-receipt-card-head"><div><p class="ff-kicker">' + pair('Coverage control room', '覆盖控制室') + '</p><h3>' + pair('Selected-leaf correspondence states', '选定叶节点对应状态') + '</h3></div><span class="ff-receipt-micro">' + pair('Root cells ' + (coverage.root_cell_count == null ? receipt.page.total : coverage.root_cell_count), '根单元 ' + (coverage.root_cell_count == null ? receipt.page.total : coverage.root_cell_count)) + '</span></div>' +
      '<div class="ff-receipt-status-grid">' +
        '<div>' + receiptStatusBadge('all_leaves_attested') + '<strong>' + esc(coverage.all_leaves_attested == null ? '—' : coverage.all_leaves_attested) + '</strong></div>' +
        '<div>' + receiptStatusBadge('partially_attested') + '<strong>' + esc(coverage.partially_attested == null ? '—' : coverage.partially_attested) + '</strong></div>' +
        '<div>' + receiptStatusBadge('not_attested') + '<strong>' + esc(coverage.not_attested == null ? '—' : coverage.not_attested) + '</strong></div>' +
        '<div>' + receiptStatusBadge('not_evaluable') + '<strong>' + esc(coverage.not_evaluable == null ? '—' : coverage.not_evaluable) + '</strong></div></div></section>' +
      '<section class="ff-receipt-card"><div class="ff-receipt-card-head"><div><p class="ff-kicker">' + pair('Company Facts conversion', 'Company Facts 转换') + '</p><h3>' + pair('Recorded input window', '已记录的输入窗口') + '</h3></div><span class="ff-receipt-micro">' + esc(conversion.availability || '—') + '</span></div><div class="ff-receipt-stats">' +
        receiptStat('Occurrences', '事实条目', conversion.occurrence_count) + receiptStat('Output rows', '输出行', conversion.output_occurrence_count) + receiptStat('PIT eligible', 'PIT 符合条件', conversion.pit_eligible_count) + '</div>' +
        '<dl class="ff-receipt-clocks"><div><dt>' + pair('Captured', '捕获时间') + '</dt><dd>' + esc(formatDate(clocks.captured_at)) + '</dd></div><div><dt>' + pair('Source snapshot', '来源快照') + '</dt><dd>' + esc(formatDate(clocks.source_snapshot_at)) + '</dd></div><div><dt>' + pair('Recorded', '记录时间') + '</dt><dd>' + esc(formatDate(clocks.recorded_at)) + '</dd></div></dl></section>' +
      '<section class="ff-receipt-card ff-receipt-root-card"><div class="ff-receipt-card-head"><div><p class="ff-kicker">' + pair('Receipt cells', '凭据单元') + '</p><h3>' + pair('Open one recorded waterfall', '打开一个已记录的瀑布') + '</h3></div><span class="ff-receipt-micro">' + pair('Page ' + (receipt.pageIndex + 1), '第 ' + (receipt.pageIndex + 1) + ' 页') + '</span></div><p class="ff-receipt-root-note">' + pair(
        'Cell identifiers are trace keys. A user-facing metric label is not inferred where the receipt does not provide one.',
        '单元标识符是追踪键。凭据未提供时不会推断面向用户的指标标签。'
      ) + '</p><div class="ff-receipt-root-list" role="list">' + rootRows + '</div><div class="ff-receipt-pager"><button type="button" data-receipt-action="previous"' + previousDisabled + '>' + pair('Previous', '上一页') + '</button><span>' + pair(receipt.page.returned + ' of ' + receipt.page.total + ' cells', receipt.page.returned + ' / ' + receipt.page.total + ' 个单元') + '</span><button type="button" data-receipt-action="next"' + nextDisabled + '>' + pair('Next', '下一页') + '</button></div></section>';
    renderReceiptInspector();
  }

  function receiptDetailValue(labelEn, labelZh, value) {
    return '<div><dt>' + pair(labelEn, labelZh) + '</dt><dd><code>' + esc(value == null || value === '' ? '—' : value) + '</code></dd></div>';
  }

  function receiptWaterfallRow(row, index) {
    var item = row && typeof row === 'object' ? row : {};
    var attested = item.attested === true;
    var companyfacts = attested && item.companyfacts && typeof item.companyfacts === 'object' ? item.companyfacts : null;
    var trail = attested && item.stored_b3_projection && typeof item.stored_b3_projection === 'object' ? item.stored_b3_projection : null;
    var heading = attested ? pair('Recorded correspondence', '已记录的对应关系') : pair('No recorded correspondence', '没有已记录的对应关系');
    var contents = attested && companyfacts ? '<dl class="ff-receipt-waterfall-fields">' +
      receiptDetailValue('Concept', '概念', [companyfacts.taxonomy, companyfacts.concept].filter(Boolean).join(': ')) +
      receiptDetailValue('Period', '期间', companyfacts.period && [companyfacts.period.start, companyfacts.period.end].filter(Boolean).join(' → ')) +
      receiptDetailValue('Unit', '单位', companyfacts.unit) + receiptDetailValue('Exact value', '精确数值', companyfacts.value) +
      receiptDetailValue('Accession', '文件编号', companyfacts.accession) + '</dl>' +
      '<details class="ff-receipt-projection"><summary>' + pair('Stored provenance projection', '存储的溯源投影') + '</summary><dl class="ff-receipt-waterfall-fields">' +
      receiptDetailValue('Attestation ID', '证明 ID', item.attestation_id) + receiptDetailValue('Match ID', '匹配 ID', item.match_id) +
      receiptDetailValue('Package ID', '包 ID', trail && trail.package_id) + receiptDetailValue('Extraction ID', '提取 ID', trail && trail.extraction_id) +
      receiptDetailValue('Recorded at', '记录时间', trail && trail.attested_at) + '</dl></details>' :
      '<p class="ff-receipt-unmatched">' + pair(
        item.eligible === false ? 'No eligible selected leaf is recorded for this row.' : 'No selected correspondence is recorded in this receipt.',
        item.eligible === false ? '该行未记录符合条件的选定叶节点。' : '该凭据未记录选定对应关系。'
      ) + '</p>';
    return '<article class="ff-receipt-waterfall-row' + (attested ? ' is-recorded' : ' is-open') + '"><div class="ff-receipt-waterfall-head"><span class="ff-receipt-waterfall-index" aria-hidden="true">' + (index + 1) + '</span><div><strong>' + heading + '</strong><code title="' + esc(item.occurrence_id || '') + '">' + esc(shortTraceId(item.occurrence_id)) + '</code></div><span class="ff-receipt-leaf-state">' + pair(item.eligible === false ? 'Not eligible' : 'Eligible', item.eligible === false ? '不符合条件' : '符合条件') + '</span></div>' + contents + '</article>';
  }

  function renderReceiptInspector() {
    if (!ui.receiptInspectorBody) return;
    var receipt = state.receipt;
    if (!receipt.rootCellId) {
      ui.receiptInspectorTitle.innerHTML = pair('Choose a value', '选择一个数值');
      ui.receiptInspectorBody.innerHTML = '<div class="ff-evidence-empty"><span class="ff-empty-mark" aria-hidden="true">◇</span><p>' + pair(
        'Choose a value to see its recorded source path.',
        '选择一个数值，查看其记录的来源路径。'
      ) + '</p></div>';
      return;
    }
    ui.receiptInspectorTitle.innerHTML = pair('Receipt cell', '凭据单元') + '<code class="ff-receipt-inspector-id" title="' + esc(receipt.rootCellId) + '">' + esc(shortTraceId(receipt.rootCellId)) + '</code>';
    if (receipt.detailPhase === 'loading') {
      ui.receiptInspectorBody.innerHTML = '<div class="ff-loading" role="status"><span class="ff-loading-dot" aria-hidden="true"></span>' + pair('Loading recorded trail…', '正在载入已记录轨迹…') + '</div>';
      return;
    }
    if (receipt.detailPhase !== 'ready' || !receipt.detail) {
      ui.receiptInspectorBody.innerHTML = receiptEmpty(
        'Value details temporarily unavailable', '数值详情暂时不可用',
        'The source path is shown only when its recorded details can be read.',
        '仅在能够读取已记录详情时，才会显示来源路径。',
        '<button class="ff-receipt-retry" type="button" data-receipt-detail-retry="true">' + pair('Retry', '重试') + '</button>'
      );
      return;
    }
    var detail = receipt.detail;
    var root = detail.root;
    var waterfall = detail.waterfall;
    var summary = root.attested + ' of ' + root.selected + ' selected leaves have recorded correspondence';
    var waterfallHtml = waterfall.length ? waterfall.map(receiptWaterfallRow).join('') : receiptEmpty(
      'No selected leaves supplied', '未提供选定叶节点',
      'This receipt cell has no selected leaf rows to display.',
      '该凭据单元没有可显示的选定叶节点行。'
    );
    ui.receiptInspectorBody.innerHTML = '<div class="ff-receipt-inspector-summary">' + receiptStatusBadge(root.status) + '<p>' + pair(summary, root.attested + ' / ' + root.selected + ' 个选定叶节点有已记录的对应关系') + '</p><p class="ff-receipt-boundary">' + pair(
      'This waterfall preserves unmatched leaves and does not reread source material.',
      '此瀑布保留未匹配叶节点，且不重新读取来源材料。'
    ) + '</p></div><div class="ff-receipt-waterfall">' + waterfallHtml + '</div>';
  }

  function receiptUrl(receipt) {
    return safeUrl(receipt && (receipt.source_url || receipt.url || receipt.filing_url));
  }

  function receiptAccession(receipt) {
    return String((receipt && (receipt.accession || receipt.accession_number)) || '—');
  }

  function plainLimitationPair(value) {
    var raw = String(value || '').toLowerCase();
    var known = {
      phrase_based_label_matching: ['Phrase matching can miss a renamed metric.', '短语匹配可能遗漏改名后的指标。'],
      does_not_establish_management_motive: ['This comparison does not establish management motive.', '本次对比不能证明管理层动机。'],
      does_not_determine_legal_materiality: ['This comparison does not determine legal materiality.', '本次对比不判断法律重大性。'],
      section_heading_detection_is_pattern_based: ['Section matching depends on filing headings and may be incomplete.', '章节匹配依赖财报标题，可能不完整。'],
      does_not_quantify_economic_effect: ['The text comparison does not quantify an economic effect.', '文本对比不量化经济影响。'],
      does_not_classify_the_reason_for_change: ['The text comparison does not classify why wording changed.', '文本对比不判断措辞变化的原因。'],
      firm_extraction_is_pattern_based: ['Firm-name matching is pattern based and should be checked in the source.', '事务所名称匹配基于模式，应在原文中核验。'],
      engagement_change_requires_source_review: ['Confirm any engagement change in the original filing.', '请在原始财报中确认任何审计委聘变化。'],
      does_not_determine_remediation_status: ['The wording alone does not establish remediation status.', '单凭措辞无法确定整改状态。'],
      negation_handling_is_sentence_based: ['Context can extend beyond the matched sentence.', '上下文可能超出匹配句子。'],
      absence_is_measured_within_supplied_filing_text: ['Absence is measured only within the supplied filing text.', '“未出现”只在提供的财报文本范围内成立。'],
      cross_form_kpi_cadence_is_not_comparable: ['Different reporting forms may disclose a metric on different schedules.', '不同类型的报表可能按不同节奏披露指标。']
    };
    var knownPair = known[raw];
    return knownPair ? pair(knownPair[0], knownPair[1]) : pair(
      'Review the supplied filing scope and source excerpts before relying on this observation.',
      '在依赖此观察结果前，请核对提供的财报范围和来源摘录。'
    );
  }

  function benignExplanationPair(value) {
    var raw = String(value || '').trim();
    var known = {
      'A metric can be renamed, moved to earnings materials, or omitted in a shorter filing.': [
        'A metric can be renamed, moved to earnings materials, or omitted in a shorter filing.',
        '指标可能更名、移至业绩材料，或在较短财报中省略。'
      ],
      'This is a lexical change flag, not a legal-materiality conclusion.': [
        'This is a lexical change flag, not a legal-materiality conclusion.',
        '这是文字变化提示，并非对法律重大性的结论。'
      ],
      'Policy wording can change because of presentation, standard-adoption boilerplate, or relocation.': [
        'Policy wording can change because of presentation, standard-adoption boilerplate, or relocation.',
        '政策措辞可能因展示方式、准则采用模板文本或位置调整而变化。'
      ],
      'A firm-name change can reflect a legal-name update or audit-firm combination.': [
        'A firm-name change can reflect a legal-name update or audit-firm combination.',
        '事务所名称变化可能反映法定名称更新或审计机构合并。'
      ],
      'Control language can describe a remediated, historical, or acquired-business condition.': [
        'Control language can describe a remediated, historical, or acquired-business condition.',
        '控制相关措辞可能描述已整改、历史性或收购业务相关的情况。'
      ]
    };
    var translated = known[raw];
    return translated ? pair(translated[0], translated[1]) : pair(
      raw || 'The engine records a non-exclusive alternative explanation; source review is still needed.',
      '引擎记录了一个非排他的替代解释；仍需核对原始来源。'
    );
  }

  function receiptMarkup(receipt, index) {
    var href = receiptUrl(receipt);
    var form = String((receipt && receipt.form) || 'SEC filing');
    var accession = receiptAccession(receipt);
    var filingRole = String((receipt && receipt.filing_role) || '');
    var roleMarkup = filingRole === 'current' ? '<span class="ff-filing-role is-current">' + pair('Current', '本期') + '</span>' :
      (filingRole === 'prior' ? '<span class="ff-filing-role is-prior">' + pair('Prior', '上期') + '</span>' : '');
    // The projection keeps the exact raw source fragment for its hash/span
    // receipt, but supplies an inert presentation companion so Inline XBRL
    // attributes never flood the analyst-facing evidence pane.
    var excerpt = String((receipt && (receipt.display_excerpt || receipt.source_excerpt)) || '').trim();
    var sourceAction = href ? '<a class="ff-receipt-link" href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">' +
      pair('Open SEC filing', '打开 SEC 财报') + '<span aria-hidden="true">↗</span></a>' : '<span class="ff-receipt-basis">' +
      pair('SEC link not supplied', '未提供 SEC 链接') + '</span>';
    return '<article class="ff-disclosure-receipt"><div class="ff-disclosure-receipt-head"><span class="ff-receipt-icon" aria-hidden="true">' + (index + 1) + '</span><div><strong>' + esc(form) + roleMarkup + '</strong><span class="ff-disclosure-accession">' + esc(accession) + '</span></div>' + sourceAction + '</div>' +
      (excerpt ? '<blockquote class="ff-source-excerpt">' + esc(excerpt) + '</blockquote>' : '<p class="ff-receipt-basis">' + pair('No bounded source excerpt was supplied.', '未提供受限长度的来源摘录。') + '</p>') + '</article>';
  }

  function redlineMarkup(redline) {
    if (!redline) return '';
    var edits = Array.isArray(redline.inline_edits) ? redline.inline_edits : [];
    var lines = edits.length ? edits.slice(0, 8).map(function (edit) {
      var before = String(edit.prior_text || '').trim();
      var after = String(edit.current_text || '').trim();
      var beforeLine = before ? '<div class="ff-diff-line is-prior"><span aria-hidden="true">−</span><span>' + esc(before) + '</span></div>' : '';
      var afterLine = after ? '<div class="ff-diff-line is-current"><span aria-hidden="true">+</span><span>' + esc(after) + '</span></div>' : '';
      return '<div class="ff-diff-edit">' + beforeLine + afterLine + '</div>';
    }).join('') : '<p class="ff-redline-fallback">' + pair(
      'No inline token view was supplied; compare the bounded source excerpts below.',
      '未提供词级对照；请比较下方受限长度的来源摘录。'
    ) + '</p>';
    return '<div class="ff-diff-card"><div class="ff-diff-card-head"><span>' + disclosureSectionPair(redlineSection(redline)) + '</span><span class="ff-diff-machine-note">' +
      pair('Machine-matched text', '机器匹配文本') + '</span></div>' + lines + '</div>';
  }

  function redlinesForDisclosureFinding(finding) {
    if (!finding) return [];
    var prior = String(finding.prior_accession || '');
    var current = String(finding.current_accession || '');
    var section = disclosureFindingSection(finding);
    var evidenceBlockIds = (Array.isArray(finding.evidence_receipts) ? finding.evidence_receipts : []).map(function (receipt) {
      return String((receipt && receipt.block_id) || '');
    }).filter(Boolean);
    return activeRedlines().filter(function (redline) {
      var oldReceipt = redline.prior_receipt || {};
      var newReceipt = redline.current_receipt || {};
      var accessionMatches = (!prior || receiptAccession(oldReceipt) === prior) && (!current || receiptAccession(newReceipt) === current);
      var blockMatches = evidenceBlockIds.length && [oldReceipt, newReceipt].some(function (receipt) {
        return evidenceBlockIds.indexOf(String((receipt && receipt.block_id) || '')) >= 0;
      });
      // Section inheritance remains useful for exploration, but a detector's
      // exact evidence block IDs are the stronger source contract. This keeps
      // a Revenue Recognition prompt from opening an unrelated later lease
      // redline that happens to share an inherited note-section key.
      return accessionMatches && (blockMatches || (!evidenceBlockIds.length && (section === 'other' || redlineSection(redline) === section)));
    }).slice(0, 2);
  }

  function renderDisclosureEvidence(item, kind) {
    if (!item) {
      renderEvidence(null);
      return;
    }
    var isFinding = kind === 'disclosure-finding';
    var title = isFinding ? disclosureFindingLabel(item) : pair(redlineOperationInfo(item).en, redlineOperationInfo(item).zh);
    var receipts = isFinding ? (Array.isArray(item.evidence_receipts) ? item.evidence_receipts : []) : [item.prior_receipt, item.current_receipt].filter(Boolean);
    var relatedRedlines = isFinding ? redlinesForDisclosureFinding(item) : [item];
    var status = isFinding ? disclosureFindingState(item) : { icon: '◇', en: 'Observed text change', zh: '观察到文本变化' };
    var summary = isFinding ? disclosureWhyPair(item) : pair(
      'The comparison engine matched text from the supplied filings. Read both excerpts before interpreting the change.',
      '对比引擎匹配了提供财报中的文本；请先阅读两段摘录再解读变化。'
    );
    var limitations = isFinding ? (Array.isArray(item.limitations) ? item.limitations : []) : [];
    var limitationHtml = limitations.length ? limitations.map(function (value) { return '<li>' + plainLimitationPair(value) + '</li>'; }).join('') :
      '<li>' + pair('This is an observed lexical change, not an explanation of motive, materiality, or impact.', '这是观察到的文字变化，不代表对动机、重大性或影响的解释。') + '</li>';
    var alternative = isFinding && item.benign_explanation ? '<p class="ff-disclosure-alternative"><strong>' + pair('Alternative explanation: ', '其他可能解释：') + '</strong>' + benignExplanationPair(item.benign_explanation) + '</p>' : '';
    var redlineHtml = relatedRedlines.length ? relatedRedlines.map(redlineMarkup).join('') : '<p class="ff-redline-fallback">' + pair(
      'No matched redline was supplied for this review prompt. Use the source excerpts to inspect the filing language.',
      '该复核提示未提供匹配的逐字对照；请使用来源摘录核对财报措辞。'
    ) + '</p>';
    var receiptHtml = receipts.length ? receipts.slice(0, 6).map(receiptMarkup).join('') : '<div class="ff-empty-state"><div><p>' + pair(
      'No filing receipt was supplied for this comparison result.', '该对比结果未提供财报凭据。'
    ) + '</p></div></div>';
    ui.evidenceTitle.innerHTML = title;
    ui.evidenceBody.innerHTML = '<div class="ff-proof-badge ff-disclosure-proof-badge" data-priority="watch"><span aria-hidden="true">' + status.icon + '</span>' +
      pair(status.en, status.zh) + '</div><p class="ff-proof-summary">' + summary + '</p><p class="ff-disclosure-honesty">' + pair(
      'Observed language is not a motive claim. The source excerpts are the evidence.',
      '观察到的措辞不是动机主张；来源摘录才是证据。'
    ) + '</p>' + alternative +
      '<section class="ff-proof-section"><h3>' + pair('Matched wording', '匹配到的措辞') + '</h3>' + redlineHtml + '</section>' +
      '<section class="ff-proof-section"><h3>' + pair('SEC source excerpts', 'SEC 来源摘录') + '</h3><div class="ff-disclosure-receipts">' + receiptHtml + '</div></section>' +
      '<section class="ff-proof-section"><h3>' + pair('Reading boundaries', '阅读边界') + '</h3><ul class="ff-limitations">' + limitationHtml + '</ul></section>';
  }

  function renderTabEvidenceEmpty(tab) {
    var guides = {
      statements: {
        icon: '▥', title: ['How to read these financials', '如何阅读这些财务数据'],
        body: ['Start with the newest column, then scan left to see whether the move is new or part of a trend.', '先看最新一列，再向左回看，判断这次变化是新出现还是延续趋势。'],
        steps: [['Compare key periods', '对比关键期间', 'compare'], ['Return to key signals', '返回关键信号', 'radar'], ['Verify the source', '核对原始来源', 'trace']]
      },
      disclosures: {
        icon: '◫', title: ['Choose a filing change', '选择一项披露变化'],
        body: ['Open a change to read the current and prior SEC excerpts side by side. The comparison describes wording, not motive.', '打开一项变化，并列阅读本期与上期的 SEC 摘录。这里描述的是措辞变化，而非动机。'],
        steps: [['See exact redlines', '查看逐字差异', 'redlines'], ['View filing history', '查看披露历史', 'timeline'], ['Verify the source', '核对原始来源', 'trace']]
      },
      redlines: {
        icon: '≠', title: ['Choose an exact wording change', '选择一处逐字变化'],
        body: ['Open a matched change to see what was removed, added, or replaced in the source text.', '打开一处匹配变化，查看原文中删除、新增或替换的内容。'],
        steps: [['Read summarized changes', '阅读变化摘要', 'disclosures'], ['View filing history', '查看披露历史', 'timeline'], ['Verify the source', '核对原始来源', 'trace']]
      },
      timeline: {
        icon: '◷', title: ['Use the filing history as context', '用披露历史补充背景'],
        body: ['Confirm which forms and dates are being compared before interpreting any signal or wording change.', '解读任何信号或措辞变化前，请先确认对比的是哪些表格和日期。'],
        steps: [['Read wording changes', '阅读措辞变化', 'disclosures'], ['Compare key periods', '对比关键期间', 'compare'], ['Verify the source', '核对原始来源', 'trace']]
      },
      compare: {
        icon: '↔', title: ['Choose two periods to compare', '选择两个期间进行对比'],
        body: ['Use the selectors to compare reported values. Direction alone is not a verdict; open a signal for the rule and context.', '使用选择器对比披露数值。方向本身不是结论；请打开信号查看规则和背景。'],
        steps: [['Open key signals', '打开关键信号', 'radar'], ['Read wording changes', '阅读措辞变化', 'disclosures'], ['Verify the source', '核对原始来源', 'trace']]
      },
      trace: {
        icon: '✓', title: ['Your source and coverage guide', '来源与覆盖指南'],
        body: ['Use the source map for SEC links. Open the run record when you need the saved publication details.', '使用来源地图查看 SEC 链接。需要已保存的发布详情时，可打开运行记录。'],
        steps: [['Return to key signals', '返回关键信号', 'radar'], ['Compare key periods', '对比关键期间', 'compare'], ['Read filing history', '阅读披露历史', 'timeline']]
      }
    };
    var guide = guides[tab] || guides.trace;
    ui.evidenceTitle.innerHTML = pair(guide.title[0], guide.title[1]);
    ui.evidenceBody.innerHTML = '<div class="ff-view-guide"><span class="ff-view-guide-icon" aria-hidden="true">' + guide.icon + '</span><p>' +
      pair(guide.body[0], guide.body[1]) + '</p><div class="ff-view-guide-actions">' + guide.steps.map(function (step) {
        return '<button type="button" data-go-tab="' + esc(step[2]) + '">' + pair(step[0], step[1]) + '<span aria-hidden="true">→</span></button>';
      }).join('') + '</div></div>';
  }

  function renderCurrentEvidence() {
    if (state.evidenceKind === 'cell' && state.cellEvidence) {
      renderCellEvidence(state.cellEvidence);
      return;
    }
    if (state.evidenceKind === 'disclosure-finding') {
      renderDisclosureEvidence(selectedDisclosureFinding(), 'disclosure-finding');
      return;
    }
    if (state.evidenceKind === 'redline') {
      renderDisclosureEvidence(selectedRedline(), 'redline');
      return;
    }
    if (state.evidenceKind === 'view') {
      renderTabEvidenceEmpty(state.tab);
      return;
    }
    renderEvidence(selectedFinding());
  }

  function renderEvidence(finding) {
    if (!finding) {
      ui.evidenceTitle.innerHTML = pair('Choose a signal', '选择一个信号');
      ui.evidenceBody.innerHTML = '<div class="ff-evidence-empty"><span class="ff-empty-mark" aria-hidden="true">↳</span><p>' +
      pair('Choose a signal to understand what it means, compare the numbers, and verify the SEC source.', '选择一个信号，了解它的含义、对比关键数字并核对 SEC 来源。') + '</p></div>';
      return;
    }
    var priority = priorityInfo(finding.priority);
    ui.evidenceTitle.innerHTML = fieldPair(finding, 'title', 'Untitled finding');
    var values = Array.isArray(finding.values) ? finding.values : [];
    var valueRows = values.length ? values.map(function (value) {
      var cellOpts = [valueControlOpts(value, 'current'), valueControlOpts(value, 'prior'), valueControlOpts(value, 'delta')];
      // Item 2 (§2.1): an unavailable span is shown, not dimmed — the number
      // keeps full ink, the control takes a dashed hairline, and the row
      // prints the visible .ff-source-unavail label once under its metric
      // (each control still carries it in its accessible name and tip).
      var rowUnavailable = cellOpts.some(function (opts) { return !spanOk(opts || {}); });
      return '<div class="ff-value-row"><div class="ff-value-label">' + fieldPair(value, 'label', prettify(value.key)) +
        (rowUnavailable ? '<span class="ff-source-unavail ff-value-row-unavail">' + pair('Source span unavailable', '来源片段不可用') + '</span>' : '') + '</div>' +
        '<div class="ff-value-cell"><small>' + pair('Current', '本期') + '</small>' + sourceControlHtml(cellOpts[0]) + '</div>' +
        '<div class="ff-value-cell"><small>' + pair('Compared with', '对比基准') + '</small>' + sourceControlHtml(cellOpts[1]) + '</div>' +
        '<div class="ff-value-cell"><small>' + pair('Change', '变化') + '</small>' + sourceControlHtml(cellOpts[2]) + '</div></div>';
    }).join('') : '<div class="ff-empty-state"><div><p>' + pair('No value bridge was supplied for this result.', '此结果未提供数值变化桥。') + '</p></div></div>';

    var receipts = Array.isArray(finding.evidence) ? finding.evidence : [];
    var receiptHtml = receipts.length ? receipts.map(function (receipt, index) {
      var href = safeUrl(receipt.url);
      var label = fieldPair(receipt, 'label', 'SEC source ' + (index + 1));
      var labelMarkup = href ? '<a class="ff-receipt-link" href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">' + label + '</a>' : label;
      return '<li class="ff-receipt"><span class="ff-receipt-icon" aria-hidden="true">' + (index + 1) + '</span>' +
        '<div><div class="ff-receipt-label">' + labelMarkup + '</div><div class="ff-receipt-basis">' +
        basisPair(receipt.basis) + '</div></div><span class="ff-receipt-date">' + esc(formatDate(receipt.date)) + '</span></li>';
    }).join('') : '<li class="ff-receipt"><span class="ff-receipt-icon" aria-hidden="true">—</span><div><div class="ff-receipt-label">' +
      pair('No source link supplied', '未提供来源链接') + '</div><div class="ff-receipt-basis">' +
      pair('Treat this result as incomplete until its source is available.', '在来源可用前，请将此结果视为不完整。') + '</div></div></li>';

    var limitationsEn = Array.isArray(finding.limitations_en) ? finding.limitations_en : [];
    var limitationsZh = Array.isArray(finding.limitations_zh) ? finding.limitations_zh : [];
    var limitationCount = Math.max(limitationsEn.length, limitationsZh.length);
    var limitationHtml = '';
    for (var index = 0; index < limitationCount; index += 1) {
      limitationHtml += '<li>' + pair(limitationsEn[index] || limitationsZh[index], limitationsZh[index] || limitationsEn[index]) + '</li>';
    }
    if (!limitationHtml) limitationHtml = '<li>' + pair('No finding-specific limitation was supplied.', '未提供该发现的特定局限。') + '</li>';

    ui.evidenceBody.innerHTML = '<div class="ff-proof-badge" data-priority="' + esc(finding.priority || 'watch') + '"><span aria-hidden="true">' +
      priority.icon + '</span>' + pair(priority.en, priority.zh) + '</div>' +
      '<section class="ff-signal-meaning"><span>' + pair('Why this matters', '为什么重要') + '</span><p>' +
      findingSummaryHtml(finding, 'No summary supplied.') + '</p></section>' +
      '<section class="ff-proof-section"><h3>' + pair('Numbers behind the signal', '信号背后的数字') + '</h3><div class="ff-value-grid">' + valueRows + '</div></section>' +
      '<section class="ff-proof-section ff-proof-actions"><h3>' + pair('Explore the full picture', '继续查看完整情况') + '</h3><div class="ff-proof-action-grid">' +
      '<button type="button" data-go-tab="compare">' + pair('Compare periods', '对比期间') + '<span aria-hidden="true">→</span></button>' +
      '<button type="button" data-go-tab="disclosures">' + pair('Read filing changes', '阅读披露变化') + '<span aria-hidden="true">→</span></button>' +
      '<button type="button" data-go-tab="trace">' + pair('Verify SEC sources', '核对 SEC 来源') + '<span aria-hidden="true">→</span></button>' +
      '</div></section>' +
      '<section class="ff-proof-section"><h3>' + pair('Verify with the SEC', '通过 SEC 核对') + '</h3><ol class="ff-receipts">' + receiptHtml + '</ol></section>' +
      '<details class="ff-proof-details"><summary>' + pair('How this signal was detected', '这个信号如何识别') + '</summary><div>' +
      // Item 10: the method facts sit here, in plain words, not at glance.
      '<p class="ff-proof-method">' + pair('Compared: ' + findingPeriodText(finding) + '. Method: the same fixed rule for every company.',
        '对比：' + findingPeriodText(finding) + '。方法：对每家公司使用同一固定规则。') + '</p><code class="ff-proof-code">' +
      fieldPair(finding, 'formula', 'Formula not supplied') + '</code><p class="ff-threshold"><strong>' + pair('Signal appears when: ', '信号触发条件：') + '</strong>' +
      fieldPair(finding, 'threshold', 'Threshold not supplied') + '</p></div></details>' +
      '<details class="ff-proof-details"><summary>' + pair('What this signal cannot tell you', '这个信号无法说明什么') + '</summary><div><ul class="ff-limitations">' + limitationHtml + '</ul></div></details>';
  }

  function setTab(tab, focusPanel) {
    var allowed = ['radar', 'statements', 'disclosures', 'redlines', 'timeline', 'compare', 'trace', 'peers'];
    if (allowed.indexOf(tab) === -1) tab = 'radar';
    var previousTab = state.tab;
    state.tab = tab;
    ui.workspace.setAttribute('data-tab', tab);
    ui.tabs.forEach(function (button) {
      var active = button.getAttribute('data-tab') === tab;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
      button.tabIndex = active ? 0 : -1;
      var panel = byId(button.getAttribute('aria-controls'));
      if (panel) panel.hidden = !active;
    });
    if (previousTab !== tab) {
      closeEvidence(false);
      closeReceiptInspector(false);
      if (previousTab === 'trace' && tab !== 'trace') resetReceiptState();
    }
    if (tab === 'radar') {
      state.evidenceKind = 'finding';
      renderEvidence(selectedFinding());
    } else if (tab === 'disclosures') {
      if (state.evidenceKind !== 'disclosure-finding' || !selectedDisclosureFinding()) {
        state.evidenceKind = 'view';
        renderTabEvidenceEmpty(tab);
      }
    } else if (tab === 'redlines') {
      if (state.evidenceKind !== 'redline' || !selectedRedline()) {
        state.evidenceKind = 'view';
        renderTabEvidenceEmpty(tab);
      }
    } else if (tab === 'trace') {
      state.evidenceKind = 'view';
      renderTabEvidenceEmpty(tab);
      setSourceMode(state.sourceMode, false);
    } else if (tab === 'compare') {
      state.evidenceKind = 'view';
      renderTabEvidenceEmpty(tab);
      ensureFinancialData();
    } else if (tab === 'statements') {
      state.evidenceKind = 'view';
      renderTabEvidenceEmpty(tab);
      ensureStatements();
    } else if (tab === 'peers') {
      state.evidenceKind = 'view';
      renderTabEvidenceEmpty(tab);
      renderPeers();
    } else {
      state.evidenceKind = 'view';
      renderTabEvidenceEmpty(tab);
    }
    updateViewStatus();
    if (focusPanel) {
      var selectedTab = document.querySelector('.ff-tab[data-tab="' + tab + '"]');
      var targetPanel = selectedTab ? byId(selectedTab.getAttribute('aria-controls')) : null;
      if (targetPanel) targetPanel.focus({ preventScroll: true });
    }
  }

  function updateViewStatus() {
    var target = company();
    if (!target) return;
    var findings = orderedFindings(target);
    var periods = Array.isArray(target.periods) ? target.periods : [];
    var evidenceCount = findings.reduce(function (total, finding) {
      return total + (Array.isArray(finding.evidence) ? finding.evidence.length : 0);
    }, 0);
    if (state.tab === 'radar') {
      ui.viewStatus.innerHTML = pair(findings.length + (findings.length === 1 ? ' signal' : ' signals') + ' · filed ' + formatDate(target.latest_filed),
        findings.length + ' 个信号 · 披露于 ' + formatDate(target.latest_filed));
    } else if (state.tab === 'statements') {
      ui.viewStatus.innerHTML = pair(periods.length + ' normalized periods', periods.length + ' 个标准化期间');
    } else if (state.tab === 'compare') {
      ui.viewStatus.innerHTML = pair('Neutral period bridge', '中性期间变化桥');
    } else if (state.tab === 'disclosures') {
      var disclosureCount = disclosureFindingsForView(target).length;
      ui.viewStatus.innerHTML = pair(
        disclosureCount + ' observed wording change' + (disclosureCount === 1 ? '' : 's'),
        disclosureCount + ' 项观察到的措辞变化'
      );
    } else if (state.tab === 'redlines') {
      var redlineCount = activeRedlines(target).length;
      ui.viewStatus.innerHTML = pair(
        redlineCount + ' matched text change' + (redlineCount === 1 ? '' : 's'),
        redlineCount + ' 条匹配文本变化'
      );
    } else if (state.tab === 'timeline') {
      var filingCount = disclosureDocuments(target).length;
      ui.viewStatus.innerHTML = pair(
        filingCount + ' filing' + (filingCount === 1 ? '' : 's') + ' in the source trail',
        '来源轨迹中有 ' + filingCount + ' 份财报'
      );
    } else if (state.sourceMode === 'receipt') {
      var receipt = state.receipt;
      if (receipt.phase === 'ready' && receipt.page) {
        ui.viewStatus.innerHTML = pair(receipt.page.total + ' receipt cells', receipt.page.total + ' 个凭据单元');
      } else if (receipt.phase === 'mismatch') {
        ui.viewStatus.innerHTML = pair('No issuer receipt', '无该发行人凭据');
      } else {
        ui.viewStatus.innerHTML = pair('Receipt on demand', '按需读取凭据');
      }
    } else if (state.tab === 'peers') {
      var cohort = peerCohort();
      ui.viewStatus.innerHTML = cohort
        ? pair((cohort.members_n != null ? cohort.members_n : cohort.members.length) + ' peer members', (cohort.members_n != null ? cohort.members_n : cohort.members.length) + ' 家同业成员')
        : pair('Peer cohort unavailable', '同业组不可用');
    } else {
      ui.viewStatus.innerHTML = pair(evidenceCount + ' source links', evidenceCount + ' 条来源链接');
    }
  }

  function searchCompanies(query) {
    var needle = String(query || '').trim().toLowerCase();
    var matches = Object.keys(companies()).map(function (key) {
      var item = companies()[key];
      return { key: key, company: item };
    }).filter(function (entry) {
      if (!needle) return true;
      var haystack = [entry.key, entry.company.symbol, entry.company.name, entry.company.sector].filter(Boolean).join(' ').toLowerCase();
      return haystack.indexOf(needle) >= 0;
    }).sort(function (a, b) {
      var aStarts = a.key.toLowerCase().indexOf(needle) === 0 ? 0 : 1;
      var bStarts = b.key.toLowerCase().indexOf(needle) === 0 ? 0 : 1;
      return aStarts - bStarts || a.key.localeCompare(b.key);
    }).slice(0, 10);
    state.searchMatches = matches;
    state.searchIndex = matches.length ? 0 : -1;
    renderSearchOptions();
  }

  function renderSearchOptions() {
    if (!state.searchMatches.length) {
      ui.companyOptions.innerHTML = '<div class="ff-search-empty">' + pair('No covered company matches.', '覆盖范围内无匹配公司。') + '</div>';
      ui.companyOptions.hidden = false;
      ui.search.setAttribute('aria-expanded', 'true');
      ui.search.setAttribute('aria-activedescendant', '');
      return;
    }
    ui.companyOptions.innerHTML = state.searchMatches.map(function (entry, index) {
      var target = entry.company;
      var optionId = 'ff-company-option-' + index;
      return '<button type="button" class="ff-company-option' + (index === state.searchIndex ? ' is-active' : '') + '" role="option"' +
        ' id="' + optionId + '" data-symbol="' + esc(entry.key) + '" aria-selected="' + (index === state.searchIndex ? 'true' : 'false') + '">' +
        '<span class="ff-option-symbol">' + esc(target.symbol || entry.key) + '</span><span><span class="ff-option-name">' +
        esc(target.name || entry.key) + '</span><span class="ff-option-sector">' + pair(target.sector || '—', sectorZh(target.sector) || '—') + '</span></span></button>';
    }).join('');
    ui.companyOptions.hidden = false;
    ui.search.setAttribute('aria-expanded', 'true');
    ui.search.setAttribute('aria-activedescendant', 'ff-company-option-' + state.searchIndex);
  }

  function closeSearch() {
    ui.companyOptions.hidden = true;
    ui.search.setAttribute('aria-expanded', 'false');
    ui.search.setAttribute('aria-activedescendant', '');
    state.searchIndex = -1;
  }

  function moveSearchIndex(delta) {
    if (!state.searchMatches.length) return;
    state.searchIndex = (state.searchIndex + delta + state.searchMatches.length) % state.searchMatches.length;
    renderSearchOptions();
    var active = byId('ff-company-option-' + state.searchIndex);
    if (active) active.scrollIntoView({ block: 'nearest' });
  }

  function openAnalysisDrawer() {
    state.lastFocus = selectedEvidenceButton() || document.activeElement;
    ui.evidence.classList.add('is-open');
    ui.workspace.setAttribute('data-analysis-open', 'true');
    ui.evidence.setAttribute('role', 'dialog');
    ui.evidence.setAttribute('aria-modal', 'true');
    ui.scrim.hidden = false;
    document.body.classList.add('ff-modal-open');
    setInert(ui.main, true);
    setInert(ui.siteNav, true);
    window.requestAnimationFrame(function () {
      if (ui.evidenceClose) ui.evidenceClose.focus();
    });
  }

  function openEvidence() {
    var selected = state.evidenceKind === 'disclosure-finding' ? selectedDisclosureFinding() :
      state.evidenceKind === 'redline' ? selectedRedline() : selectedFinding();
    if (!selected) return;
    openAnalysisDrawer();
  }

  function closeEvidence(restoreFocus) {
    var wasOpen = ui.evidence.classList.contains('is-open');
    ui.evidence.classList.remove('is-open');
    ui.workspace.removeAttribute('data-analysis-open');
    ui.evidence.removeAttribute('role');
    ui.evidence.removeAttribute('aria-modal');
    ui.scrim.hidden = true;
    document.body.classList.remove('ff-modal-open');
    setInert(ui.main, false);
    setInert(ui.siteNav, false);
    if (wasOpen && restoreFocus !== false && state.lastFocus && typeof state.lastFocus.focus === 'function') {
      state.lastFocus.focus({ preventScroll: true });
    }
  }

  function openReceiptInspector() {
    if (desktopMedia.matches || !state.receipt.rootCellId) return;
    ui.receiptInspector.classList.add('is-open');
    ui.receiptInspector.setAttribute('role', 'dialog');
    ui.receiptInspector.setAttribute('aria-modal', 'true');
    ui.scrim.hidden = false;
    document.body.classList.add('ff-modal-open');
    setInert(ui.main, true);
    setInert(ui.siteNav, true);
    window.requestAnimationFrame(function () { ui.receiptInspectorClose.focus(); });
  }

  function closeReceiptInspector(restoreFocus) {
    if (!ui.receiptInspector) return;
    var wasOpen = ui.receiptInspector.classList.contains('is-open');
    ui.receiptInspector.classList.remove('is-open');
    ui.receiptInspector.removeAttribute('role');
    ui.receiptInspector.removeAttribute('aria-modal');
    if (!ui.evidence.classList.contains('is-open')) {
      ui.scrim.hidden = true;
      document.body.classList.remove('ff-modal-open');
      setInert(ui.main, false);
      setInert(ui.siteNav, false);
    }
    if (wasOpen && restoreFocus !== false && state.receipt.lastFocus && typeof state.receipt.lastFocus.focus === 'function') {
      state.receipt.lastFocus.focus({ preventScroll: true });
    }
  }

  function setInert(element, inert) {
    if (!element) return;
    if (inert) {
      element.setAttribute('inert', '');
      element.setAttribute('aria-hidden', 'true');
    } else {
      element.removeAttribute('inert');
      element.removeAttribute('aria-hidden');
    }
  }

  function focusableInEvidence() {
    return Array.prototype.slice.call(ui.evidence.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])'
    )).filter(function (node) { return node.offsetParent !== null; });
  }

  function focusableInReceiptInspector() {
    return Array.prototype.slice.call(ui.receiptInspector.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])'
    )).filter(function (node) { return node.offsetParent !== null; });
  }

  function handleEvidenceKeydown(event) {
    if (!ui.evidence.classList.contains('is-open')) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      closeDrawerAndSync();
      return;
    }
    if (event.key !== 'Tab') return;
    var focusable = focusableInEvidence();
    if (!focusable.length) {
      event.preventDefault();
      ui.evidence.focus();
      return;
    }
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function handleReceiptInspectorKeydown(event) {
    if (!ui.receiptInspector.classList.contains('is-open')) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      closeReceiptInspector(true);
      return;
    }
    if (event.key !== 'Tab') return;
    var focusable = focusableInReceiptInspector();
    if (!focusable.length) {
      event.preventDefault();
      ui.receiptInspector.focus();
      return;
    }
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  // Act only when the desktop match really CROSSES. A full-page capture (and some
  // zoom / devtools resizes) re-dispatches `change` with an unchanged match; closing on
  // that would drop an analysis drawer the reader opened on purpose.
  var lastDesktopMatch = desktopMedia.matches;
  function handleViewportChange() {
    var matches = desktopMedia.matches;
    var crossed = matches !== lastDesktopMatch;
    lastDesktopMatch = matches;
    if (matches && crossed) {
      closeEvidence(false);
      closeReceiptInspector(false);
    }
  }

  function updateLocalizedAttributes() {
    var current = lang();
    if (ui.search) ui.search.placeholder = ui.search.getAttribute('data-placeholder-' + current) || '';
    var savedNameNode = byId('ff-saved-name');
    if (savedNameNode) savedNameNode.placeholder = savedNameNode.getAttribute('data-placeholder-' + current) || '';
    Array.prototype.forEach.call(document.querySelectorAll('[data-label-en][data-label-zh]'), function (node) {
      var label = node.getAttribute('data-label-' + current);
      if (label) node.setAttribute('aria-label', label);
    });
    if (state.payload && company()) {
      renderTopicOptions(orderedFindings(company()));
      renderDisclosureControls(company());
      renderDisclosureFeed(company());
      renderRedlines(company());
      renderTimeline(company());
      renderCompareControls(company());
      renderCompare(company());
      renderRunMeta();
      renderRevisions();
      renderPeers();
      renderCurrentEvidence();
      renderReceipt();
      renderReceiptInspector();
    }
    renderSavedUI();
  }

  function bindEvents() {
    // Delegated so the three runtime states can replace the gate's markup
    // without re-binding, the way the receipt pane's data-receipt-action works.
    ui.gate.addEventListener('click', function (event) {
      var trigger = event.target.closest('[data-gate-action]');
      if (!trigger) return;
      var action = trigger.getAttribute('data-gate-action');
      if (action === 'plans') openPlans();
      else if (action === 'signin') openSignin();
      else if (action === 'retry') loadData();
    });

    ui.workspace.addEventListener('click', function (event) {
      var destination = event.target.closest('[data-go-tab]');
      if (destination) {
        setTab(destination.getAttribute('data-go-tab'), false);
        writeUrl(true);
        var activeTab = document.querySelector('.ff-tab.is-active');
        if (activeTab) activeTab.scrollIntoView({ block: 'nearest', inline: 'nearest' });
        return;
      }
      var primary = event.target.closest('[data-open-primary-finding]');
      if (!primary || !state.payload) {
        // §2.5 — a real source-control button (statement cell, compare cell,
        // drawer value) opens the cell evidence view on its occurrence. The
        // span variants inside card buttons fall through to the card handlers.
        var sourceControl = event.target.closest('.ff-source-control');
        if (sourceControl && sourceControl.tagName === 'BUTTON' && !sourceControl.disabled) {
          activateSourceControl(sourceControl);
        }
        return;
      }
      var findings = orderedFindings(company());
      if (!findings.length) {
        setTab('trace', false);
        return;
      }
      state.findingId = String(findings[0].id);
      state.priority = 'all';
      state.topic = 'all';
      state.evidenceKind = 'finding';
      setTab('radar', false);
      renderTopicOptions(findings);
      renderFindings();
      renderCurrentEvidence();
      openEvidence();
    });

    ui.tabs.forEach(function (button, index) {
      button.addEventListener('click', function () {
        setTab(button.getAttribute('data-tab'), false);
        writeUrl(true);
      });
      button.addEventListener('keydown', function (event) {
        var next = index;
        if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % ui.tabs.length;
        else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (index - 1 + ui.tabs.length) % ui.tabs.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = ui.tabs.length - 1;
        else return;
        event.preventDefault();
        ui.tabs[next].focus();
        setTab(ui.tabs[next].getAttribute('data-tab'), false);
        writeUrl(true);
      });
    });

    ui.sourceTabs.forEach(function (button, index) {
      button.addEventListener('click', function () {
        setSourceMode(button.getAttribute('data-source-mode'), false);
        updateViewStatus();
        writeUrl(true);
      });
      button.addEventListener('keydown', function (event) {
        var next = index;
        if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % ui.sourceTabs.length;
        else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (index - 1 + ui.sourceTabs.length) % ui.sourceTabs.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = ui.sourceTabs.length - 1;
        else return;
        event.preventDefault();
        ui.sourceTabs[next].focus();
        setSourceMode(ui.sourceTabs[next].getAttribute('data-source-mode'), false);
        updateViewStatus();
        writeUrl(true);
      });
    });

    ui.priorityFilters.addEventListener('click', function (event) {
      var button = event.target.closest('[data-priority]');
      if (!button || !state.payload) return;
      state.priority = button.getAttribute('data-priority');
      renderFindings();
      updateViewStatus();
    });

    ui.topic.addEventListener('change', function () {
      state.topic = ui.topic.value;
      renderFindings();
    });

    ui.findings.addEventListener('click', function (event) {
      var button = event.target.closest('[data-finding-id]');
      if (!button) return;
      state.findingId = button.getAttribute('data-finding-id');
      state.evidenceKind = 'finding';
      renderFindings();
      renderCurrentEvidence();
      writeUrl(true);
      openEvidence();
    });

    ui.disclosureSection.addEventListener('change', function () {
      state.disclosureSection = ui.disclosureSection.value || 'all';
      renderDisclosureFeed(company());
      renderRedlines(company());
      updateViewStatus();
    });

    ui.disclosureFeed.addEventListener('click', function (event) {
      var button = event.target.closest('[data-disclosure-finding-id]');
      if (!button) return;
      state.disclosureFindingId = button.getAttribute('data-disclosure-finding-id');
      state.evidenceKind = 'disclosure-finding';
      renderDisclosureFeed(company());
      renderCurrentEvidence();
      writeUrl(true);
      openEvidence();
    });

    ui.redlineList.addEventListener('click', function (event) {
      var button = event.target.closest('[data-redline-id]');
      if (!button) return;
      state.redlineId = button.getAttribute('data-redline-id');
      state.evidenceKind = 'redline';
      renderRedlines(company());
      renderCurrentEvidence();
      writeUrl(true);
      openEvidence();
    });

    ui.trace.addEventListener('click', function (event) {
      var button = event.target.closest('[data-open-finding]');
      if (!button) return;
      state.findingId = button.getAttribute('data-open-finding');
      state.priority = 'all';
      state.topic = 'all';
      state.evidenceKind = 'finding';
      setTab('radar', false);
      renderTopicOptions(orderedFindings(company()));
      renderFindings();
      renderCurrentEvidence();
      writeUrl(true);
      if (desktopMedia.matches) {
        var target = selectedFindingButton();
        if (target) target.focus({ preventScroll: false });
      } else {
        openEvidence();
      }
    });

    ui.receipt.addEventListener('click', function (event) {
      var root = event.target.closest('[data-root-cell-id]');
      if (root) {
        requestReceiptRoot(root.getAttribute('data-root-cell-id'), root);
        return;
      }
      var action = event.target.closest('[data-receipt-action]');
      if (action) {
        var name = action.getAttribute('data-receipt-action');
        if (name === 'retry') ensureReceiptForCompany();
        else if (name === 'next') receiptPageNext();
        else if (name === 'previous') receiptPagePrevious();
      }
    });

    ui.receiptInspectorBody.addEventListener('click', function (event) {
      if (!event.target.closest('[data-receipt-detail-retry]') || !state.receipt.rootCellId) return;
      requestReceiptRoot(state.receipt.rootCellId, state.receipt.lastFocus);
    });

    // §3.1 — Latest clears as_of; a picked day rewrites both clocks to that
    // day's 23:59:59Z. Nothing queries per keystroke, only on change.
    if (ui.asofLatest) {
      ui.asofLatest.addEventListener('click', function () {
        state.asOfDate = '';
        state.savedActiveId = '';
        state.savedRefusal = '';
        state.savedStoreError = false;
        state.pinnedRequest = null;
        setAsofControlsFromState();
        writeUrl(true);
        renderRunMeta();
        ensureFinancialData();
      });
    }
    if (ui.asofInput) {
      ui.asofInput.addEventListener('change', function () {
        var value = String(ui.asofInput.value || '');
        if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return;
        state.asOfDate = value;
        state.savedActiveId = '';
        state.savedRefusal = '';
        state.savedStoreError = false;
        state.pinnedRequest = null;
        setAsofControlsFromState();
        writeUrl(true);
        renderRunMeta();
        ensureFinancialData();
      });
    }
    if (ui.exportBtn) {
      ui.exportBtn.addEventListener('click', runExport);
    }

    // X2-s saved views: restore via the list, save/rename/delete in the desk
    // band, one save entry on the peers panel, one action on the notice chip.
    var savedSelect = byId('ff-saved-select');
    if (savedSelect) {
      savedSelect.addEventListener('change', function () {
        if (!savedSelect.value) {
          state.savedActiveId = '';
          state.savedRefusal = '';
          state.savedStoreError = false;
          state.pinnedRequest = null;
          renderSavedUI();
          return;
        }
        restoreSavedView(savedSelect.value);
      });
    }
    var savedName = byId('ff-saved-name');
    var savedSaveBtn = byId('ff-saved-save');
    function savedNameValue() {
      return savedName ? String(savedName.value || '').trim() : '';
    }
    if (savedSaveBtn) {
      savedSaveBtn.addEventListener('click', function () {
        var name = savedNameValue();
        if (!name) return;
        performSavedSave(name);
      });
    }
    if (savedName) {
      savedName.addEventListener('input', renderSavedUI);
      savedName.addEventListener('keydown', function (event) {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        var name = savedNameValue();
        if (name) performSavedSave(name);
      });
    }
    var savedRenameBtn = byId('ff-saved-rename');
    if (savedRenameBtn) {
      savedRenameBtn.addEventListener('click', function () {
        var name = savedNameValue();
        if (name) savedRenameActive(name);
      });
    }
    var savedDeleteBtn = byId('ff-saved-delete');
    if (savedDeleteBtn) {
      savedDeleteBtn.addEventListener('click', savedDeleteActive);
    }
    var peerSaveBtn = byId('ff-peer-save');
    if (peerSaveBtn) {
      peerSaveBtn.addEventListener('click', function () {
        if (!savedName) return;
        if (!savedNameValue()) {
          // A generated, editable default — the user's text stays verbatim
          // once they touch it; nothing here is bilingual storage.
          savedName.value = String(state.symbol || '') + ' peers';
        }
        var name = savedNameValue();
        if (name) performSavedSave(name);
      });
    }
    var savedNotice = byId('ff-saved-notice');
    if (savedNotice) {
      savedNotice.addEventListener('click', function (event) {
        if (event.target.closest('[data-saved-reresolve]')) reResolveSavedView();
      });
    }
    ui.workspace.addEventListener('click', function (event) {
      if (!event.target.closest('[data-financial-retry]')) return;
      // PF r1 (R2): the 503 copy shown because of HEALTH retries the health
      // fetch itself — the chain resumes from applyHealth once the answer
      // lands. PFM r1 (item 4): the compare-chain Retry does the same —
      // refreshing health first — so a failure caused by a superseded
      // generation can recover when the store now serves a newer one.
      // Both branches keep their original copy; only the click handler
      // changes.
      state.healthRequestedFor = '';
      state.healthAnswer = null;
      state.financial = { phase: 'loading', awaitingHealth: true };
      renderRevisions();
      loadHealth();
    });

    ui.currentPeriod.addEventListener('change', function () {
      state.currentPeriod = Number(ui.currentPeriod.value) || 0;
      renderCompare(company());
    });
    ui.priorPeriod.addEventListener('change', function () {
      state.priorPeriod = Number(ui.priorPeriod.value) || 0;
      renderCompare(company());
    });

    ui.search.addEventListener('focus', function () { if (state.payload) searchCompanies(ui.search.value); });
    ui.search.addEventListener('input', function () {
      ui.searchClear.hidden = !ui.search.value;
      searchCompanies(ui.search.value);
    });
    ui.search.addEventListener('keydown', function (event) {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        if (ui.companyOptions.hidden) searchCompanies(ui.search.value);
        else moveSearchIndex(1);
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        if (ui.companyOptions.hidden) searchCompanies(ui.search.value);
        else moveSearchIndex(-1);
      } else if (event.key === 'Enter' && !ui.companyOptions.hidden && state.searchIndex >= 0) {
        event.preventDefault();
        setCompany(state.searchMatches[state.searchIndex].key, true);
      } else if (event.key === 'Escape') {
        closeSearch();
        ui.search.value = state.symbol;
        ui.searchClear.hidden = false;
      }
    });

    ui.companyOptions.addEventListener('mousedown', function (event) { event.preventDefault(); });
    ui.companyOptions.addEventListener('click', function (event) {
      var option = event.target.closest('[data-symbol]');
      if (option) setCompany(option.getAttribute('data-symbol'), true);
    });
    ui.searchClear.addEventListener('click', function () {
      ui.search.value = '';
      ui.searchClear.hidden = true;
      ui.search.focus();
      searchCompanies('');
    });

    document.addEventListener('click', function (event) {
      if (!event.target.closest('.ff-combobox-wrap')) closeSearch();
    });
    document.addEventListener('langchange', updateLocalizedAttributes);

    ui.notice.addEventListener('click', function (event) {
      if (event.target.closest('#ff-retry')) loadData();
    });
    ui.evidenceClose.addEventListener('click', function () { closeDrawerAndSync(); });
    ui.receiptInspectorClose.addEventListener('click', function () { closeReceiptInspector(true); });
    ui.scrim.addEventListener('click', function () {
      if (ui.receiptInspector.classList.contains('is-open')) closeReceiptInspector(true);
      else closeDrawerAndSync();
    });
    ui.evidence.addEventListener('keydown', handleEvidenceKeydown);
    ui.receiptInspector.addEventListener('keydown', handleReceiptInspectorKeydown);

    if (desktopMedia.addEventListener) desktopMedia.addEventListener('change', handleViewportChange);
    else desktopMedia.addListener(handleViewportChange);

    // Back/forward drives the whole desk: the URL frame is applied, a drawer
    // frame closes the drawer WITHOUT another history.back (the pop itself is
    // the back), and a drawer=1 frame re-opens the occurrence it names.
    window.addEventListener('popstate', function () {
      if (!state.payload) return;
      var url = readUrlParams();
      if (!url.drawer && ui.evidence.classList.contains('is-open')) {
        closeEvidence(true);
      }
      // A history move re-addresses the desk from the URL alone: the restored
      // saved view (and its pinned bytes) no longer describes this frame.
      state.savedActiveId = '';
      state.savedRefusal = '';
      state.savedStoreError = false;
      state.pinnedRequest = null;
      if (url.symbol) {
        var next = resolveSymbol(url.symbol);
        if (next && next !== state.symbol) setCompany(next, false);
      }
      state.asOfDate = url.asOfDate;
      state.policy = url.policy;
      state.sourceMode = url.src;
      state.cohortId = url.cohort;
      state.peerMetric = url.peerMetric;
      state.peerAlign = url.align;
      state.peerN = url.peerN;
      state.peerTol = url.peerTol;
      if (url.finding) state.findingId = url.finding;
      if (url.disc) state.disclosureFindingId = url.disc;
      if (url.redline) state.redlineId = url.redline;
      setTab(url.peers ? 'peers' : url.tab, false);
      if (url.drawer) openDrawerFromUrl(url);
      renderSavedUI();
    });
  }

  function init() {
    cacheUi();
    bindEvents();
    initSavedBriefcase();
    updateLocalizedAttributes();
    // tier_preview.js resolves the visitor's tier from the session cookie before
    // any network call and stamps it on <html>; both scripts are deferred, so it
    // has already run. Showing the preview here rather than after the 401 is
    // what stops a stranger meeting a loading skeleton that resolves into a
    // wall. The fetch below remains the authority and corrects this if wrong.
    if (document.documentElement.getAttribute('data-access-tier') === 'anon') setAccess('signin');
    if (!IS_LOOPBACK) {
      var bindAuth = function () {
        if (window.MDXAuth && window.MDXAuth.onChange) {
          window.MDXAuth.onChange(function () {
            if (!state.payload) loadData();
          });
        }
      };
      if (window.MDXAuth) bindAuth();
      else window.addEventListener('load', bindAuth, { once: true });
    }
    loadData();
  }

  // A deliberately opt-in pure-function seam for the dependency-free Node
  // contract suite. Production never sets this sentinel and receives no test
  // surface; the browser runtime still consumes the exact same validators.
  if (window.__FF_RECEIPT_CONTRACT_TEST__ === true) {
    window.__FF_RECEIPT_CONTRACT_TEST__ = Object.freeze({
      normalizedCik: normalizedCik,
      checkedLatestReceipt: checkedLatestReceipt,
      checkedReceiptRoot: checkedReceiptRoot,
      checkedReceiptPagePayload: checkedReceiptPagePayload,
      checkedReceiptDetailPayload: checkedReceiptDetailPayload
    });
  }

  if (window.__FF_WORKBENCH_TEST__ === true) {
    window.__FF_WORKBENCH_TEST__ = {
      openAnalysisDrawer: openAnalysisDrawer,
      openEvidence: openEvidence,
      closeEvidence: closeEvidence,
      applyHealth: applyHealth,
      freshnessCopy: freshnessCopy,
      state: state,
      ui: ui,
      cacheUi: cacheUi,
      // P2 URL-state + exact-value seams for the dependency-free Node
      // contract suite; production never sets this sentinel.
      writeUrl: writeUrl,
      readUrlParams: readUrlParams,
      applyUrlState: applyUrlState,
      setTab: setTab,
      closeDrawerAndSync: closeDrawerAndSync,
      renderCellEvidence: renderCellEvidence,
      cellEvidenceFromControl: cellEvidenceFromControl,
      bindEvents: bindEvents,
      // X2-s saved-views seams (same opt-in contract as above).
      initSavedBriefcase: initSavedBriefcase,
      renderSavedUI: renderSavedUI,
      restoreSavedView: restoreSavedView,
      performSavedSave: performSavedSave,
      savedRenameActive: savedRenameActive,
      savedDeleteActive: savedDeleteActive,
      reResolveSavedView: reResolveSavedView,
      buildSavedViewInput: buildSavedViewInput,
      backfillSavedAgainst: backfillSavedAgainst,
      activePinnedRequest: activePinnedRequest,
      reconcileSavedActive: reconcileSavedActive,
      savedSavePhase: savedSavePhase,
      savedGenerationStale: savedGenerationStale,
      exportQueryBody: exportQueryBody,
      runExport: runExport,
      // PF-1..PF-4 seams (same opt-in contract as above): the cutoff helper,
      // the health fetch and the financial chain, for the dependency-free
      // Node contract suite. Production never sets this sentinel.
      policyClocks: policyClocks,
      latestCutoffs: latestCutoffs,
      selectedGeneration: selectedGeneration,
      setCompany: setCompany,
      loadHealth: loadHealth,
      ensureFinancialData: ensureFinancialData,
      ensureStatements: ensureStatements,
      renderStatementTree: renderStatementTree,
      peerExclusionCopy: peerExclusionCopy,
      financialPost: financialPost,
      renderRevisions: renderRevisions,
      setAsofControlsFromState: setAsofControlsFromState
    };
  } else if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
}());
