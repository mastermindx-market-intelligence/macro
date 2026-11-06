(function () {
  'use strict';

  var API = '/api/market-memory/v1';
  var state = {
    macro: null,
    symbol: null,
    ticker: 'AAPL',
    latestRaw: 'AAPL',
    macroRequest: 0,
    symbolRequest: 0,
    macroAuthBlocked: false,
    symbolAuthBlocked: false,
    macroNotice: null,
    symbolNotice: null,
    legacyMacroPending: false,
    legacySymbolPending: false
  };
  var ui = {};

  function isZh() { return document.documentElement.getAttribute('data-lang') === 'zh'; }
  function copy(en, zh) { return isZh() ? (zh || en) : en; }
  function esc(value) {
    return String(value === null || value === undefined ? '' : value).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  function asObject(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
  function asArray(value) { return Array.isArray(value) ? value : []; }
  function present(value) { return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value)); }
  function num(value, digits) { return present(value) ? Number(value).toFixed(digits === undefined ? 1 : digits) : '—'; }
  function signed(value, digits, suffix) {
    if (!present(value)) return '—';
    var n = Number(value);
    return (n > 0 ? '+' : '') + n.toFixed(digits === undefined ? 1 : digits) + (suffix || '');
  }
  function logReturn(value) {
    if (!present(value)) return null;
    return (Math.exp(Number(value)) - 1) * 100;
  }
  function basisPoints(value) { return present(value) ? Number(value) * 100 : null; }
  function tone(value) {
    if (!present(value) || Number(value) === 0) return '';
    return Number(value) > 0 ? ' is-up' : ' is-down';
  }
  function apiBase() {
    return /(^|\.)mastermind-x\.com$/i.test(location.hostname || '') ? '' : (window.MM_API || '');
  }

  function withAuth(headers) {
    headers = headers || {};
    if (!(window.MDXAuth && window.MDXAuth.client)) return Promise.resolve(headers);
    return window.MDXAuth.client()
      .then(function (client) { return client.auth.getSession(); })
      .then(function (result) {
        var token = result && result.data && result.data.session && result.data.session.access_token;
        if (token) headers.Authorization = 'Bearer ' + token;
        return headers;
      })
      .catch(function () { return headers; });
  }

  function request(path) {
    return withAuth({ Accept: 'application/json' }).then(function (headers) {
      return fetch(apiBase() + API + path, {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: headers
      });
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (payload) {
        if (!response.ok) {
          var error = new Error((payload && payload.detail) || ('HTTP ' + response.status));
          error.status = response.status;
          error.payload = payload;
          throw error;
        }
        return payload;
      });
    });
  }

  function syncIntent(patch) {
    if (!window.MarketMemoryIntent) return true; // Existing standalone legacy client.
    var result = window.MarketMemoryIntent.syncReturn(patch);
    if (result.ok) return true;
    // Clear a stale auth destination on invalid/oversize intent. No source data is stored.
    try { var url = new URL(location.href); url.searchParams.delete('ret'); history.replaceState(history.state, '', url.pathname + '?' + url.searchParams.toString()); } catch (error) { /* no-op */ }
    return false;
  }
  function signinHref() {
    if (!window.MarketMemoryIntent) return '#mm-symbol-form';
    // Rendering a notice must not mutate the shared OAuth capsule.
    var patch = {language: isZh() ? 'zh' : 'en'};
    if (state.symbolRequest) patch.issuerInput = state.latestRaw;
    var result = window.MarketMemoryIntent.target(patch);
    if (!result.ok) return '#mm-symbol-form';
    var params = new URLSearchParams();
    params.set('signin', '1');
    params.set('ret', result.target);
    return '/?' + params.toString();
  }
  function invalidTickerFeedback() {
    state.symbolNotice = {kind: 'invalid'};
    ui.symbolSummary.innerHTML = empty('Check the ticker', '请检查代码', 'Use a canonical market symbol such as AAPL, BRK-B or BTC-USD.', '请输入 AAPL、BRK-B 或 BTC-USD 等标准市场代码。');
    ui.gridList.innerHTML = '';
  }

  function empty(titleEn, titleZh, bodyEn, bodyZh, error) {
    var action = '';
    var upgradeRequired = error && (error.status === 402 || error.status === 403);
    if (error && error.status === 401) {
      action = ' <a href="' + esc(signinHref()) + '" data-mm-action="signin">' + esc(copy('Sign in', '登录')) + ' →</a>';
      if (window.MarketMemoryIntent && !window.MarketMemoryIntent.oauthPreservation().ok) {
        action += ' ' + esc(copy('This tab cannot preserve your selection through Google sign-in.', '此标签页无法在 Google 登录后保留当前选择。'));
      }
    } else if (upgradeRequired) {
      action = ' <a href="plans.html">' + esc(copy('View plans', '查看方案')) + ' →</a>';
    }
    return '<div class="mm-empty"><strong>' + esc(copy(titleEn, titleZh)) + '</strong>' +
      '<span>' + esc(copy(bodyEn, bodyZh)) + action + '</span></div>';
  }

  function chip(value, extra) {
    if (!value && value !== 0) return '';
    return '<span class="mm-chip' + (extra || '') + '">' + esc(String(value).replace(/_/g, ' ')) + '</span>';
  }

  function queryCard(labelEn, labelZh, value, note, extra) {
    return '<div class="mm-query-card' + (extra || '') + '"><span>' + esc(copy(labelEn, labelZh)) +
      '</span><strong>' + esc(value || '—') + '</strong>' + (note ? '<small>' + esc(note) + '</small>' : '') + '</div>';
  }

  function deltaText(query, episode) {
    var bits = [];
    if (present(episode.vix) && present(query.vix)) {
      bits.push('<b>VIX</b> ' + num(episode.vix, 1) + ' ' + esc(copy('then', '当时')) + ' / ' + num(query.vix, 1) + ' ' + esc(copy('now', '现在')));
    }
    if (present(episode.spread_2s10s) && present(query.spread_2s10s)) {
      bits.push('<b>2s10s</b> ' + signed(basisPoints(episode.spread_2s10s), 0, 'bp') + ' / ' + signed(basisPoints(query.spread_2s10s), 0, 'bp'));
    }
    if (present(episode.breadth_pct_above_200) && present(query.breadth_pct_above_200)) {
      bits.push('<b>' + esc(copy('breadth', '广度')) + '</b> ' + num(episode.breadth_pct_above_200, 0) + '% / ' + num(query.breadth_pct_above_200, 0) + '%');
    }
    return bits.length ? bits.join(' · ') : esc(copy('Difference detail unavailable', '差异细节暂不可用'));
  }

  function outcome(label, value) {
    var pct = logReturn(value);
    return '<div class="mm-outcome' + tone(pct) + '"><span>' + esc(label) +
      '</span><strong>' + (pct === null ? '—' : esc(signed(pct, 1, '%'))) + '</strong></div>';
  }

  function renderMacro() {
    var data = state.macro;
    if (!data) return;
    var query = asObject(data.query);
    ui.macroState.className = 'mm-state-pill is-live';
    ui.macroState.textContent = copy('State through ', '状态截至 ') + (data.as_of || '—');
    ui.macroQuery.innerHTML =
      queryCard('Current state', '当前状态', query.date || data.as_of || '—', [query.quad, query.liquidity, query.cycle].filter(Boolean).join(' · '), ' is-state') +
      queryCard('Growth', '增长', signed(query.growth_z, 2, 'σ')) +
      queryCard('Inflation', '通胀', signed(query.inflation_z, 2, 'σ')) +
      queryCard('2s10s', '2年/10年', signed(basisPoints(query.spread_2s10s), 0, 'bp')) +
      queryCard('10y3m', '10年/3月', signed(basisPoints(query.spread_10y3m), 0, 'bp')) +
      queryCard('VIX · Breadth', 'VIX · 广度', num(query.vix, 1), present(query.breadth_pct_above_200) ? num(query.breadth_pct_above_200, 0) + '% > 200d' : '—');

    var episodes = asArray(data.episodes);
    if (!episodes.length) {
      ui.macroEpisodes.innerHTML = empty('No comparable episodes', '暂无可比片段', 'The complete-state history did not return a dated match.', '完整状态历史未返回可比日期。');
    } else {
      ui.macroEpisodes.innerHTML = episodes.map(function (episode) {
        var fwd = asObject(episode.fwd);
        var chips = chip(episode.quad) + chip(episode.liquidity) + chip(episode.cycle);
        return '<article class="mm-episode">' +
          '<div class="mm-episode-date"><strong>' + esc(episode.date || '—') + '</strong><span>' +
            esc(copy('retrieval distance ', '检索距离 ')) + esc(num(episode.distance, 3)) + '</span></div>' +
          '<div class="mm-state-chips">' + chips + '</div>' +
          '<div class="mm-difference">' + deltaText(query, episode) + '</div>' +
          outcome(copy('S&P · 5 sessions', '标普 · 5交易日'), fwd.spx_h5) +
          outcome(copy('S&P · 20 sessions', '标普 · 20交易日'), fwd.spx_h20) +
          outcome(copy('S&P · 60 sessions', '标普 · 60交易日'), fwd.spx_h60) +
        '</article>';
      }).join('');
    }
    var note = copy(
      'Eligible coverage ' + (data.coverage || '—') + ' · ' + (data.n_candidates || 0) + ' candidate days after the exclusion window.',
      '可用覆盖 ' + (data.coverage || '—') + ' · 排除窗口后共有 ' + (data.n_candidates || 0) + ' 个候选交易日。'
    );
    var basis = String(data.historical_basis || 'basis unavailable').replace(/_/g, ' ');
    note = copy(
      'Historical basis: ' + basis + '. These states are recomputed today from later-complete/currently available history, not a record of what Mastermind knew on each date. ',
      '历史基础：' + basis + '。这些状态按今日可得且事后完整的历史重新计算，并非 Mastermind 在各历史日期当时已知内容的记录。'
    ) + note;
    if (data.query_lag_note) note += ' ' + data.query_lag_note;
    ui.macroNote.textContent = note + ' ' + (data.context_note || '');
  }

  function loadMacro() {
    if (ui.legacy && !ui.legacy.hasAttribute('open')) { state.legacyMacroPending = true; return; }
    var requestId = ++state.macroRequest;
    state.macro = null;
    state.macroNotice = {kind: 'loading'};
    renderMacroNotice();
    request('/macro?limit=6').then(function (payload) {
      if (requestId !== state.macroRequest) return;
      state.macroAuthBlocked = false;
      state.macro = payload;
      state.macroNotice = null;
      renderMacro();
    }).catch(function (error) {
      if (requestId !== state.macroRequest) return;
      state.macroAuthBlocked = error.status === 401;
      state.macro = null;
      state.macroNotice = {kind: 'error', status: error.status};
      renderMacroNotice();
    });
  }

  function redactForSignOut() {
    state.macroRequest += 1;
    state.symbolRequest += 1;
    state.macro = null;
    state.symbol = null;
    state.macroAuthBlocked = true;
    state.symbolAuthBlocked = !!state.ticker;
    state.macroNotice = {kind: 'signedout', status: 401};
    state.symbolNotice = {kind: 'signedout', status: 401};
    renderMacroNotice();
    renderSymbolNotice();
  }

  function renderMacroNotice() {
    var notice = state.macroNotice;
    if (!notice) return;
    if (notice.kind === 'loading') {
      ui.macroState.className = 'mm-state-pill';
      ui.macroState.textContent = copy('Loading macro memory…', '正在加载宏观记忆…');
      ui.macroQuery.innerHTML = '<div class="mm-skeleton mm-skeleton-query"></div>';
      ui.macroEpisodes.innerHTML = '<div class="mm-skeleton"></div>';
      ui.macroNote.textContent = '';
      return;
    }
    var signedOut = notice.kind === 'signedout';
    ui.macroState.className = 'mm-state-pill is-error';
    ui.macroState.textContent = signedOut ? copy('Sign in required', '需要登录') : copy('Memory unavailable', '记忆暂不可用');
    ui.macroQuery.innerHTML = empty(
      notice.status === 401 ? 'Sign in to open Market Memory' : 'Macro memory unavailable',
      notice.status === 401 ? '登录以打开市场记忆' : '宏观记忆暂不可用',
      signedOut ? 'Authenticated context is cleared when you sign out.' :
        (notice.status === 402 || notice.status === 403 ? 'This evidence surface requires full-site access.' : 'The source engine did not return a complete state.'),
      signedOut ? '退出登录后，已保存的上下文将被清除。' :
        (notice.status === 402 || notice.status === 403 ? '该证据页面需要完整站点权限。' : '源引擎未返回完整状态。'),
      notice
    );
    ui.macroEpisodes.innerHTML = '';
    ui.macroNote.textContent = signedOut ? copy(
      'No historical payload remains in this browser view.', '此浏览器视图中未保留历史载荷。'
    ) : '';
  }

  function renderSymbolNotice() {
    var notice = state.symbolNotice;
    if (!notice) return;
    ui.gridList.innerHTML = '';
    if (notice.kind === 'invalid') { invalidTickerFeedback(); return; }
    if (notice.kind === 'unpreservable') {
      ui.symbolSummary.innerHTML = empty('Cannot preserve this link', '无法保留此链接',
        'Shorten the input or correct the page reference before signing in.', '请缩短输入或修正页面引用，然后登录。');
      return;
    }
    if (notice.kind === 'resume') {
      ui.symbolSummary.innerHTML = empty('Selection unavailable after sign-in', '登录后无法恢复选择',
        'This tab could not restore the previous selection. Choose a ticker or saved capture again.',
        '此标签页无法恢复先前选择。请重新选择代码或已保存记录。');
      return;
    }
    var signedOut = notice.kind === 'signedout';
    ui.symbolSummary.innerHTML = empty(
      notice.status === 404 ? 'No memory for ' + notice.ticker : (notice.status === 401 ? 'Sign in to open symbol memory' : 'Symbol memory unavailable'),
      notice.status === 404 ? notice.ticker + ' 暂无记忆' : (notice.status === 401 ? '登录以打开个股记忆' : '个股记忆暂不可用'),
      signedOut ? 'Authenticated symbol context is cleared when you sign out.' :
        (notice.status === 402 || notice.status === 403 ? 'This evidence surface requires full-site access.' : 'No supported price history or event receipt was returned.'),
      signedOut ? '退出登录后，已保存的个股上下文将被清除。' :
        (notice.status === 402 || notice.status === 403 ? '该证据页面需要完整站点权限。' : '未返回受支持的价格历史或事件凭据。'),
      notice
    );
  }

  var GRID_LABELS = {
    W: ['Weekly bars', '周线'],
    '2B': ['2-session bars', '2交易日线'],
    '3B': ['3-session bars', '3交易日线']
  };
  var HORIZON_LABELS = {
    '13w': ['13 weeks', '13周'],
    '26w': ['26 weeks', '26周'],
    '21s': ['21 sessions', '21交易日'],
    '63s': ['63 sessions', '63交易日']
  };

  function horizonStat(labelEn, labelZh, value, suffix) {
    return '<div class="mm-stat"><span>' + esc(copy(labelEn, labelZh)) + '</span><strong>' +
      (present(value) ? esc(signed(value, 1, suffix || '%')) : '—') + '</strong></div>';
  }

  function renderHorizon(key, block) {
    block = asObject(block);
    var posterior = asObject(block.name_post);
    var post = asObject(block.post2010);
    var postPosterior = asObject(post.name_post);
    var label = HORIZON_LABELS[key] || [key, key];
    var years = asObject(block.global).n_distinct_years;
    var support = copy(
      'name n=' + (block.n_name || 0) + ' · cohort n=' + (block.n_archetype || 0) + ' · library n=' + (block.n_global || 0) + (years ? ' · ' + years + ' distinct years' : ''),
      '本股 n=' + (block.n_name || 0) + ' · 同类组 n=' + (block.n_archetype || 0) + ' · 全库 n=' + (block.n_global || 0) + (years ? ' · ' + years + ' 个不同年份' : '')
    );
    var detail = copy(
      'Post-2010 posterior: typical ' + signed(postPosterior.med, 1, '%') + ' · positive share ' + num(postPosterior.win, 1) + '%. Name weight ' + num(posterior.w, 3) + '.',
      '2010年后收缩结果：典型 ' + signed(postPosterior.med, 1, '%') + ' · 正收益占比 ' + num(postPosterior.win, 1) + '%。本股权重 ' + num(posterior.w, 3) + '。'
    );
    return '<section class="mm-horizon"><div class="mm-horizon-head"><strong>' + esc(copy(label[0], label[1])) +
      '</strong><span>' + esc(copy('shrunk receipt', '收缩凭据')) + '</span></div>' +
      '<div class="mm-stat-row">' +
        horizonStat('Typical return', '典型收益', posterior.med, '%') +
        horizonStat('Positive share', '正收益占比', posterior.win, '%') +
        horizonStat('Excess vs SPY', '相对SPY超额', posterior.med_exc, '%') +
      '</div><div class="mm-support">' + esc(support) + '</div>' +
      (block.era_note ? '<div class="mm-era-note">' + esc(block.era_note) + '</div>' : '') +
      '<details class="mm-details"><summary>' + esc(copy('Open era and weighting receipt', '展开年代与权重凭据')) +
      '</summary><p>' + esc(detail) + '</p></details></section>';
  }

  function renderGrid(key, grid) {
    grid = asObject(grid);
    var label = GRID_LABELS[key] || [key, key];
    var receipt = asObject(grid.receipt);
    var horizons = asObject(receipt.horizons);
    var direction = String(grid.direction || '—').toLowerCase();
    var freshness = grid.live_fresh === true;
    var bars = present(grid.bars_since) ? Number(grid.bars_since) : null;
    var meta = copy(
      (freshness ? 'recent episode' : 'historical class') + (bars === null ? '' : ' · ' + bars + ' completed bars ago'),
      (freshness ? '近期事件' : '历史类别') + (bars === null ? '' : ' · ' + bars + ' 根完整K线前')
    );
    var classes = chip(direction, direction === 'bull' ? ' is-bull' : (direction === 'bear' ? ' is-bear' : '')) +
      chip(grid.depth_class) + chip(grid.level) + chip(grid.washout_len_class) + chip(copy('align ', '共振 ') + (grid.align_class === null || grid.align_class === undefined ? '—' : grid.align_class));
    var body = Object.keys(horizons).map(function (h) { return renderHorizon(h, horizons[h]); }).join('');
    if (!body) body = empty('Receipt is still accruing', '凭据仍在积累', 'No matured outcome cell is available for this event class.', '该事件类别尚无成熟结果单元。');
    return '<article class="mm-grid-card"><header class="mm-grid-head"><div><h3>' + esc(copy(label[0], label[1])) +
      '</h3><p>' + esc(grid.date || '—') + ' · ' + esc(meta) + '</p></div>' +
      chip(freshness ? copy('fresh', '近期') : copy('older', '较早'), freshness ? ' is-fresh' : ' is-old') +
      '</header><div class="mm-class-row">' + classes + '</div>' + body + '</article>';
  }

  function renderSymbol() {
    var data = state.symbol;
    if (!data) return;
    var grids = asObject(data.grids);
    var bull = asObject(data.bull_now);
    var bullish = Object.keys(bull).filter(function (key) { return bull[key] === true; }).length;
    ui.symbolSummary.innerHTML = '<div class="mm-symbol-id"><span class="mm-symbol-ticker">' + esc(data.ticker || state.ticker) +
      '</span><div><strong>' + esc(copy('Episode memory', '事件记忆')) + '</strong><span>' +
      esc(copy('Current class compared with matching matured episodes', '当前类别与匹配的成熟历史事件比较')) + '</span></div></div>' +
      '<div class="mm-symbol-meta"><div><span>' + esc(copy('As of', '截至')) + '</span><strong>' + esc(data.as_of || '—') +
      '</strong></div><div><span>' + esc(copy('Bull grids', '多头周期')) + '</span><strong>' + bullish + '/3</strong></div>' +
      '<div><span>' + esc(copy('Authority', '权限')) + '</span><strong>A0 · ' + esc(copy('context', '语境')) + '</strong></div></div>';

    var order = ['W', '2B', '3B'];
    var cards = order.filter(function (key) { return grids[key]; }).map(function (key) {
      return renderGrid(key, grids[key]);
    });
    ui.gridList.innerHTML = cards.length ? cards.join('') : empty(
      'No episode history for ' + (data.ticker || state.ticker),
      (data.ticker || state.ticker) + ' 暂无事件历史',
      'The symbol may be unsupported or too new for the frozen taxonomy.',
      '该代码可能尚未覆盖，或历史不足以进入固定分类。'
    );
  }

  function normalizeTicker(raw) {
    var ticker = String(raw || '').trim().toUpperCase();
    return /^[A-Z0-9^][A-Z0-9.^=_-]{0,19}$/.test(ticker) ? ticker : '';
  }

  function loadSymbol(raw) {
    var requestId = ++state.symbolRequest;
    state.symbol = null;  // A new intent invalidates evidence before validation or loading.
    state.symbolNotice = null;
    state.latestRaw = raw === null || raw === undefined ? '' : String(raw);
    var intentSaved = syncIntent({ issuerInput: state.latestRaw, language: isZh() ? 'zh' : 'en' });
    var ticker = normalizeTicker(raw);
    state.ticker = ticker;  // Empty means the latest submitted intent cannot be retried.
    state.symbolAuthBlocked = false;
    if (!intentSaved) {
      state.ticker = '';
      state.symbolNotice = {kind: 'unpreservable'};
      renderSymbolNotice();
      return;
    }
    if (!ticker) { invalidTickerFeedback(); return; }
    ui.symbolInput.value = ticker;
    ui.symbolSummary.innerHTML = '<div class="mm-skeleton mm-skeleton-query"></div>';
    ui.gridList.innerHTML = '<div class="mm-skeleton"></div><div class="mm-skeleton"></div><div class="mm-skeleton"></div>';
    try { localStorage.setItem('market_memory_ticker', ticker); } catch (error) { /* no-op */ }
    if (window.MarketMemoryIntent) syncIntent({ticker: ticker});
    else {
      try {
        var url = new URL(location.href); url.searchParams.set('ticker', ticker);
        history.replaceState(null, '', url.pathname + '?' + url.searchParams.toString());
      } catch (error) { /* standalone legacy client */ }
    }

    // Hidden legacy panels defer only the read; validation and intent sync above still run.
    if (ui.legacy && !ui.legacy.hasAttribute('open')) { state.legacySymbolPending = true; return; }
    request('/symbol/' + encodeURIComponent(ticker)).then(function (payload) {
      if (requestId !== state.symbolRequest) return;
      state.symbolAuthBlocked = false;
      state.symbol = payload;
      state.symbolNotice = null;
      renderSymbol();
    }).catch(function (error) {
      if (requestId !== state.symbolRequest) return;
      state.symbolAuthBlocked = error.status === 401;
      state.symbol = null;
      state.symbolNotice = {kind: 'error', status: error.status, ticker: ticker};
      renderSymbolNotice();
    });
  }

  function boot() {
    ui.macroState = document.getElementById('mm-macro-state');
    ui.macroQuery = document.getElementById('mm-macro-query');
    ui.macroEpisodes = document.getElementById('mm-macro-episodes');
    ui.macroNote = document.getElementById('mm-macro-note');
    ui.symbolForm = document.getElementById('mm-symbol-form');
    ui.symbolInput = document.getElementById('mm-symbol-input');
    ui.symbolSummary = document.getElementById('mm-symbol-summary');
    ui.gridList = document.getElementById('mm-grid-list');

    ui.legacy = document.getElementById('mmr-legacy');
    // The retained page hides these panels inside <details id="mmr-legacy">.
    // Its first open starts the deferred reads; standalone pages stay eager.
    if (ui.legacy) {
      ui.legacy.addEventListener('toggle', function () {
        if (!ui.legacy.hasAttribute('open')) return;
        if (state.legacyMacroPending) { state.legacyMacroPending = false; loadMacro(); }
        if (state.legacySymbolPending) { state.legacySymbolPending = false; loadSymbol(state.latestRaw); }
      });
    }

    ui.symbolForm.addEventListener('submit', function (event) {
      event.preventDefault();
      loadSymbol(ui.symbolInput.value);
    });
    document.addEventListener('click', function (event) {
      var action = event.target && event.target.closest && event.target.closest('[data-mm-action="signin"]');
      if (!action || event.defaultPrevented || event.button > 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      if (!syncIntent({issuerInput: state.latestRaw, language: isZh() ? 'zh' : 'en'})) { event.preventDefault(); return; }
      if (window.MDXAuth && typeof window.MDXAuth.open === 'function') {
        event.preventDefault();
        window.MDXAuth.open('signin');
      }
    });
    if (window.MDXAuth && typeof window.MDXAuth.onChange === 'function') {
      window.MDXAuth.onChange(function (user) {
        if (!user) {
          redactForSignOut();
          return;
        }
        var retryMacro = state.macroAuthBlocked;
        var retrySymbol = state.symbolAuthBlocked;
        if (retryMacro) loadMacro();
        if (retrySymbol && state.ticker) loadSymbol(state.latestRaw);
      });
    }
    document.addEventListener('langchange', function () {
      var patch = {language: isZh() ? 'zh' : 'en'};
      if (window.MarketMemoryIntent && typeof window.MarketMemoryIntent.selectLanguage === 'function') {
        window.MarketMemoryIntent.selectLanguage(patch.language);
      }
      if (state.symbolRequest) patch.issuerInput = state.latestRaw;
      syncIntent(patch);
      if (state.macro) renderMacro();
      else renderMacroNotice();
      if (state.symbol) renderSymbol();
      else renderSymbolNotice();
    });

    var initial = '', explicitInput = false;
    if (window.MarketMemoryIntent) {
      var resumed = window.MarketMemoryIntent.resumeStatus();
      if (!resumed.ok) {
        state.ticker = '';
        state.symbolNotice = {kind: 'resume'};
        renderSymbolNotice();
        return;
      }
      var restored = window.MarketMemoryIntent.read();
      if (!restored.ok) {
        state.ticker = ''; invalidTickerFeedback(); syncIntent(); return;
      }
      if (restored.intent.language && typeof window.setLang === 'function') window.setLang(restored.intent.language);
      explicitInput = Object.prototype.hasOwnProperty.call(restored.intent, 'issuerInput');
      if (explicitInput) initial = restored.intent.issuerInput;
    }
    if (!explicitInput) {
      try { initial = new URL(location.href).searchParams.get('ticker') || localStorage.getItem('market_memory_ticker') || ''; } catch (error) { /* no-op */ }
      initial = normalizeTicker(initial) || 'AAPL';
    }
    ui.symbolInput.value = initial;
    window.addEventListener('popstate', function () {
      if (!window.MarketMemoryIntent) return;
      var restored = window.MarketMemoryIntent.read();
      if (!restored.ok) { ++state.symbolRequest; state.ticker = ''; state.symbol = null; invalidTickerFeedback(); return; }
      if (restored.intent.language && typeof window.setLang === 'function') window.setLang(restored.intent.language);
      var raw = Object.prototype.hasOwnProperty.call(restored.intent, 'issuerInput') ? restored.intent.issuerInput : (restored.intent.ticker || '');
      ui.symbolInput.value = raw; loadSymbol(raw);
    });

    loadMacro();
    loadSymbol(initial);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
}());

