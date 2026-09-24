/*!
 * theme-research.js — generic paid theme-research client (Theme Tracker page).
 *
 * Operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001, T10 part 1.
 * Theme-agnostic by construction: the anchor theme, the slices and both
 * endpoints come from the mount's data-* attributes; nothing in this file is
 * semiconductor-specific. No backend ships with this file — the client speaks
 * the frozen semiconductor_theme_research.v1 envelope and renders section
 * statuses, never invented zeros.
 *
 * Account safety (proven by execution under node — see
 * tests/test_semiconductor_theme_research_ui.py):
 *   - the session token comes ONLY from MDXAuth.client() (the same session
 *     acquisition the biocatalyst dossier uses); auth changes arrive via
 *     MDXAuth.onChange. No second SDK, no cookies, no token storage.
 *   - every in-flight request carries (epoch, principalKey); a response that
 *     no longer matches the current epoch/principal is dropped without
 *     touching state or DOM, and every network path re-checks in .finally.
 *   - the ONLY browser storage is the remembered slice/view/time-mode
 *     selection under 'theme_research_sel' — never a token, never payload
 *     data, never anything user-derived.
 *   - every server-derived string passes through textSafe + textContent;
 *     there is no innerHTML assignment anywhere in this file.
 *
 * Authority law: any envelope whose authority flags are not all false is
 * refused outright — this surface never ranks, gates, sizes or times anything.
 */
(function () {
  'use strict';

  var PAGE_LIMIT = 20;

  /* THEME-RESEARCH-CONTRACT-BEGIN */
  /*
   * The pure state/envelope contract — deliberately DOM-free so it can be
   * lifted verbatim and executed under plain node (marker-extraction idiom
   * shared with intelligence-hub-market-pulse.js). Nothing in this block may
   * reference document, window, network or any other browser global.
   */
  var TR_SCHEMA = 'semiconductor_theme_research.v1';
  var TR_TOP_KEYS = [
    'schema', 'definition_version', 'generation', 'request', 'native_subjects',
    'summary', 'companies', 'industrial_views', 'economics', 'expectations',
    'evidence_refs', 'authorized_coverage', 'limitations', 'authority'
  ];
  var TR_SECTION_KEYS = [
    'native_subjects', 'summary', 'companies', 'industrial_views', 'economics',
    'authorized_coverage', 'limitations'
  ];
  var TR_EXPECTATION_KEYS = [
    'management', 'external_consensus', 'house_forecast', 'market_incorporation'
  ];
  var TR_AUTHORITY_KEYS = [
    'can_rank', 'can_gate', 'can_size', 'can_originate', 'can_open_entry'
  ];
  var TR_STATUS_VOCAB = ['ready', 'degraded', 'unavailable', 'refused'];

  function newResearchState() {
    return {
      epoch: 0,
      principalKey: 'anon',
      payload: null,
      error: null,
      generation: null,
      selection: null
    };
  }

  function _sameKeySet(obj, expected) {
    var seen = Object.keys(obj || {});
    if (seen.length !== expected.length) return false;
    for (var i = 0; i < expected.length; i++) {
      if (!Object.prototype.hasOwnProperty.call(obj, expected[i])) return false;
    }
    return true;
  }

  function _validStatus(value) {
    return typeof value === 'string' && TR_STATUS_VOCAB.indexOf(value) >= 0;
  }

  function validateEnvelope(payload) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return { ok: false, reason: 'payload is not an object' };
    }
    if (!_sameKeySet(payload, TR_TOP_KEYS)) {
      return { ok: false, reason: 'top-level key set is not the closed v1 set' };
    }
    if (payload.schema !== TR_SCHEMA) {
      return { ok: false, reason: 'schema is not ' + TR_SCHEMA };
    }
    if (typeof payload.generation !== 'string' || !payload.generation) {
      return { ok: false, reason: 'generation must be a non-empty string' };
    }
    if (typeof payload.definition_version !== 'string' || !payload.definition_version) {
      return { ok: false, reason: 'definition_version must be a non-empty string' };
    }
    for (var s = 0; s < TR_SECTION_KEYS.length; s++) {
      var key = TR_SECTION_KEYS[s];
      var section = payload[key];
      if (!section || typeof section !== 'object' || Array.isArray(section)) {
        return { ok: false, reason: 'section ' + key + ' is missing or not an object' };
      }
      if (!_validStatus(section.status)) {
        return { ok: false, reason: 'section ' + key + ' has an invalid status' };
      }
    }
    var expectations = payload.expectations;
    if (!expectations || typeof expectations !== 'object' || Array.isArray(expectations)) {
      return { ok: false, reason: 'expectations is missing or not an object' };
    }
    for (var e = 0; e < TR_EXPECTATION_KEYS.length; e++) {
      var expKey = TR_EXPECTATION_KEYS[e];
      var exp = expectations[expKey];
      if (!exp || typeof exp !== 'object' || Array.isArray(exp)) {
        return { ok: false, reason: 'expectations.' + expKey + ' is missing or not an object' };
      }
      if (!_validStatus(exp.status)) {
        return { ok: false, reason: 'expectations.' + expKey + ' has an invalid status' };
      }
    }
    var authority = payload.authority;
    if (!authority || typeof authority !== 'object' || Array.isArray(authority)) {
      return { ok: false, reason: 'authority is missing or not an object' };
    }
    for (var a = 0; a < TR_AUTHORITY_KEYS.length; a++) {
      var authKey = TR_AUTHORITY_KEYS[a];
      if (!Object.prototype.hasOwnProperty.call(authority, authKey)) {
        return { ok: false, reason: 'authority.' + authKey + ' is missing' };
      }
      if (authority[authKey] !== false) {
        return { ok: false, reason: 'authority.' + authKey + ' must be false' };
      }
    }
    return { ok: true, reason: null };
  }

  /* A response is accepted only when it answers the request the CURRENT
   * state issued. A late answer for another epoch or another principal is
   * dropped with zero side effects; a current answer that fails envelope
   * validation is recorded as invalid_envelope and never rendered. */
  function applyResearchResponse(state, requestEpoch, principalKey, payload) {
    if (!state || typeof state !== 'object') return false;
    if (requestEpoch !== state.epoch || principalKey !== state.principalKey) return false;
    var verdict = validateEnvelope(payload);
    if (!verdict.ok) {
      state.error = { code: 'invalid_envelope' };
      return false;
    }
    state.payload = payload;
    state.generation = payload.generation;
    state.error = null;
    return true;
  }

  function clearResearchState(state) {
    if (!state || typeof state !== 'object') return state;
    state.payload = null;
    state.error = null;
    state.generation = null;
    return state;
  }

  function nextEpoch(state, principalKey) {
    state.epoch = state.epoch + 1;
    state.principalKey = principalKey;
    state.payload = null;
    state.error = null;
    state.generation = null;
    return state.epoch;
  }

  /* No HTML interpretation, ever: source-derived strings flow through this
   * and then textContent, so markup in a label stays literal visible text. */
  function textSafe(value) {
    if (value === null || value === undefined) return '';
    if (typeof value === 'object') {
      try { return JSON.stringify(value); } catch (e) { return String(value); }
    }
    return String(value);
  }
  /* THEME-RESEARCH-CONTRACT-END */

  /* ---- mount + page wiring -------------------------------------------- */

  var MOUNT = document.querySelector('[data-theme-research-mount]');
  if (!MOUNT) return;  // this page did not render the section; nothing to do

  var ANCHOR_THEME_ID = MOUNT.getAttribute('data-anchor-theme-id') || '';
  var SLICES = String(MOUNT.getAttribute('data-slices') || '')
    .split(',').map(function (s) { return s.trim(); }).filter(Boolean);
  var apiQueryUrl = MOUNT.getAttribute('data-api-query');
  var apiEvidenceUrl = MOUNT.getAttribute('data-api-evidence');

  var VIEWS = ['composition', 'manufacturing', 'commercial', 'capacity', 'economics'];
  var MODES = ['latest', 'source_history', 'system_replay'];

  /* Closed bilingual maps — static literals only, same discipline as the
   * dossier's V2_ZH. Unknown keys fall back to the raw slug in both languages
   * rather than being invented. */
  var L = {
    slice: {
      hbm_packaging: ['HBM & advanced packaging', 'HBM 与先进封装'],
      sic_gan_specialty: ['SiC / GaN specialty devices', 'SiC / GaN 特种器件']
    },
    view: {
      composition: ['Composition', '构成'],
      manufacturing: ['Manufacturing', '制造'],
      commercial: ['Commercial', '商业'],
      capacity: ['Capacity', '产能'],
      economics: ['Economics', '经济性']
    },
    mode: {
      latest: ['Latest build', '最新构建'],
      source_history: ['Source history', '按来源历史'],
      system_replay: ['System replay', '系统回放']
    },
    status: {
      ready: ['Ready', '就绪'],
      degraded: ['Degraded — partial data', '降级——部分数据'],
      unavailable: ['Unavailable', '不可用'],
      refused: ['Refused', '拒绝提供']
    },
    label: {
      fact: ['Fact', '事实'],
      target: ['Target', '目标'],
      interpretation: ['Interpretation', '解释']
    },
    expectation: {
      management: ['Management', '管理层'],
      external_consensus: ['External consensus', '外部共识'],
      house_forecast: ['House forecast', '内部预测'],
      market_incorporation: ['Market incorporation', '市场消化程度']
    }
  };

  var GATE_COPY = [
    'This section is member research. Sign in with a Mastermind account to read it.',
    '本栏目为会员研究内容。请使用 Mastermind 账户登录后阅读。'
  ];

  /* ---- runtime state --------------------------------------------------- */

  var state = newResearchState();
  var ui = { gate: false, loading: false, errorText: null, drawerInvoker: null };
  var controller = null;         // page-query abort lane
  var evidenceController = null; // evidence abort lane
  var evidenceRefreshTried = false;
  var offset = 0;

  var currentSlice = SLICES[0] || '';
  var currentView = VIEWS[0];
  var currentMode = MODES[0];

  /* ---- tiny DOM helpers (textContent only; no markup strings anywhere) -- */

  function clear(el) { el.textContent = ''; }

  function t(en, zh) {
    var frag = document.createDocumentFragment();
    var enSpan = document.createElement('span');
    enSpan.className = 'l-en';
    enSpan.textContent = en;
    var zhSpan = document.createElement('span');
    zhSpan.className = 'l-zh';
    zhSpan.textContent = zh || en;
    frag.appendChild(enSpan);
    frag.appendChild(zhSpan);
    return frag;
  }

  function pair(map, key) {
    var entry = map[key];
    return entry ? [entry[0], entry[1]] : [key, key];
  }

  function el(tag, className) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    return node;
  }

  function button(className, en, zh) {
    var btn = el('button', className);
    btn.type = 'button';
    btn.appendChild(t(en, zh));
    return btn;
  }

  function mutedLine(fragment) {
    var p = el('p', 'tr-muted');
    p.appendChild(fragment);
    return p;
  }

  function statusWord(status) {
    var w = pair(L.status, status);
    return t(w[0], w[1]);
  }

  function chip(kind) {
    var node = el('span', 'tr-chip tr-chip-' + textSafe(kind));
    var w = pair(L.label, kind);
    node.appendChild(t(w[0], w[1]));
    return node;
  }

  /* ---- remembered selection (the only storage this file touches) -------- */

  function restoreSelection() {
    try {
      var raw = localStorage.getItem('theme_research_sel');
      if (raw) {
        var sel = JSON.parse(raw);
        if (sel && SLICES.indexOf(sel.slice_key) >= 0) currentSlice = sel.slice_key;
        if (sel && VIEWS.indexOf(sel.view) >= 0) currentView = sel.view;
        if (sel && MODES.indexOf(sel.time_mode) >= 0) currentMode = sel.time_mode;
      }
    } catch (e) { /* unreadable memory is not an error; defaults stand */ }
    state.selection = { slice_key: currentSlice, view: currentView, time_mode: currentMode };
  }

  function rememberSelection() {
    try {
      localStorage.setItem('theme_research_sel', JSON.stringify({
        slice_key: currentSlice, view: currentView, time_mode: currentMode
      }));
    } catch (e) { /* remembering a selection is best-effort */ }
  }

  /* ---- auth (the only session acquisition surface) ---------------------- */

  function withAuthHeaders(headers) {
    headers = headers || {};
    if (!(window.MDXAuth && window.MDXAuth.client)) return Promise.resolve(headers);
    return window.MDXAuth.client().then(function (client) { return client.auth.getSession(); }).then(function (result) {
      var token = result && result.data && result.data.session && result.data.session.access_token;
      if (token) headers.Authorization = 'Bearer ' + token;
      return headers;
    }).catch(function () { return headers; });
  }

  function principalOf(user) {
    return (user && user.id) ? String(user.id) : 'anon';
  }

  function abortInFlight() {
    if (controller) { try { controller.abort(); } catch (e) { /* already gone */ } controller = null; }
    if (evidenceController) { try { evidenceController.abort(); } catch (e) { /* already gone */ } evidenceController = null; }
  }

  /* ---- requests --------------------------------------------------------- */

  function queryRequestBody(newOffset) {
    return {
      anchor_theme_id: ANCHOR_THEME_ID,
      slice_key: currentSlice,
      view: currentView,
      time_mode: currentMode,
      source_cutoff: null,
      recorded_cutoff: null,
      offset: newOffset,
      limit: PAGE_LIMIT,
      /* expected_generation is REQUIRED once paging past the first page —
       * the server must prove the generation the user is still reading. */
      expected_generation: newOffset > 0 ? state.generation : null
    };
  }

  function fetchPage(newOffset, isRefreshRetry) {
    if (!apiQueryUrl) return;
    var reqEpoch = state.epoch;
    var reqPrincipal = state.principalKey;
    abortInFlight();
    var ctrl = new AbortController();
    controller = ctrl;
    ui.loading = true;
    ui.errorText = null;
    renderStatus();

    withAuthHeaders({ 'Content-Type': 'application/json' })
      .then(function (headers) {
        return fetch(apiQueryUrl, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(queryRequestBody(newOffset)),
          signal: ctrl.signal
        });
      })
      .then(function (resp) {
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) return null;
        if (resp.status === 401 || resp.status === 403) {
          /* sign-in / upgrade required: show the gate copy, never the body */
          ui.gate = true;
          return null;
        }
        if (resp.status === 409) {
          return resp.json().catch(function () { return null; }).then(function (errBody) {
            var code = errBody && errBody.error && errBody.error.code;
            if (code === 'refresh_required' && !isRefreshRetry) {
              /* generation changed under the reader: back to page 1, once */
              if (state.epoch === reqEpoch && state.principalKey === reqPrincipal) {
                offset = 0;
                fetchPage(0, true);
              }
              return null;
            }
            throw new Error((errBody && errBody.error && errBody.error.action) || ('http ' + resp.status));
          });
        }
        if (!resp.ok) {
          return resp.json().catch(function () { return null; }).then(function (errBody) {
            var err = errBody && errBody.error;
            throw new Error((err && (err.action || err.code)) || ('http ' + resp.status));
          });
        }
        return resp.json();
      })
      .then(function (payload) {
        if (payload === null || payload === undefined) { renderAll(); return; }
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) return;
        if (applyResearchResponse(state, reqEpoch, reqPrincipal, payload)) {
          offset = newOffset;
          evidenceRefreshTried = false;
        }
        renderAll();
      })
      .catch(function (err) {
        if (err && err.name === 'AbortError') return;
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) return;
        ui.errorText = (err && err.message) || 'request failed';
        renderAll();  /* previous payload (same epoch/principal) stays on screen */
      })
      .finally(function () {
        if (controller === ctrl) controller = null;
        /* re-check epoch/principal before touching the DOM */
        if (state.epoch === reqEpoch && state.principalKey === reqPrincipal) {
          ui.loading = false;
          renderStatus();
        }
      });
  }

  /* Evidence bodies are not frozen by the v1 contract, so the drawer renders
   * whichever plain-text field the server ships and falls back to literal
   * pretty-printed JSON — always via textContent, never as markup. */
  function evidenceText(payload) {
    var fields = ['text', 'statement', 'note', 'body', 'summary'];
    for (var i = 0; i < fields.length; i++) {
      var v = payload && payload[fields[i]];
      if (typeof v === 'string' && v) return v;
    }
    try { return JSON.stringify(payload, null, 2); } catch (e) { return textSafe(payload); }
  }

  function openEvidence(ref, invokingButton) {
    if (!apiEvidenceUrl || !state.generation) return;
    openDrawer(invokingButton);
    clear(drawerBody);
    drawerBody.appendChild(mutedLine(t('Loading evidence…', '正在加载证据…')));
    var reqEpoch = state.epoch;
    var reqPrincipal = state.principalKey;
    if (evidenceController) { try { evidenceController.abort(); } catch (e) { /* already gone */ } }
    var ctrl = new AbortController();
    evidenceController = ctrl;

    withAuthHeaders({ 'Content-Type': 'application/json' })
      .then(function (headers) {
        var body = queryRequestBody(offset);
        body.assertion_ref = String(ref);
        /* expected_generation is REQUIRED for evidence: the receipt must
         * prove it answers the generation the user is reading. */
        body.expected_generation = state.generation;
        return fetch(apiEvidenceUrl, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(body),
          signal: ctrl.signal
        });
      })
      .then(function (resp) {
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) return null;
        if (resp.status === 401 || resp.status === 403) return { __gate: true };
        if (resp.status === 409) {
          return resp.json().catch(function () { return null; }).then(function (errBody) {
            var code = errBody && errBody.error && errBody.error.code;
            if (code === 'refresh_required') {
              if (!evidenceRefreshTried &&
                  state.epoch === reqEpoch && state.principalKey === reqPrincipal) {
                evidenceRefreshTried = true;
                offset = 0;
                fetchPage(0, true);
              }
              return { __refresh: true };
            }
            throw new Error((errBody && errBody.error && errBody.error.action) || ('http ' + resp.status));
          });
        }
        if (!resp.ok) {
          return resp.json().catch(function () { return null; }).then(function (errBody) {
            var err = errBody && errBody.error;
            throw new Error((err && (err.action || err.code)) || ('http ' + resp.status));
          });
        }
        return resp.json();
      })
      .then(function (payload) {
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) return;
        if (!payload) return;
        clear(drawerBody);
        if (payload.__gate) {
          drawerBody.appendChild(el('p', 'tr-gate-copy')).appendChild(t(GATE_COPY[0], GATE_COPY[1]));
          return;
        }
        if (payload.__refresh) {
          drawerBody.appendChild(mutedLine(t(
            'The underlying research was refreshed — reloading page 1. Reopen the evidence afterwards.',
            '底层研究已刷新——正在重新加载第 1 页。之后请重新打开该证据。'
          )));
          return;
        }
        var pre = el('pre', 'tr-evidence-pre');
        pre.textContent = textSafe(evidenceText(payload));
        drawerBody.appendChild(pre);
      })
      .catch(function (err) {
        if (err && err.name === 'AbortError') return;
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) return;
        clear(drawerBody);
        var p = el('p', 'tr-error');
        p.textContent = textSafe((err && err.message) || 'request failed');
        drawerBody.appendChild(p);
      })
      .finally(function () {
        if (evidenceController === ctrl) evidenceController = null;
        /* re-check epoch/principal before touching the DOM */
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) closeDrawerQuiet();
      });
  }

  /* ---- DOM scaffold ------------------------------------------------------ */

  var gateBox, controlsBox, statusLine, summaryBox, tableWrap, expectationsBox,
      evidenceBox, evidenceList, pagerBox, prevBtn, nextBtn, pageInfo,
      drawer, drawerBody, drawerClose;

  function buildDom() {
    var shell = el('div', 'tr-shell');

    gateBox = el('div', 'tr-gate');
    var gateCopy = el('p', 'tr-gate-copy');
    gateCopy.appendChild(t(GATE_COPY[0], GATE_COPY[1]));
    gateBox.appendChild(gateCopy);
    var signIn = button('tr-signin', 'Sign in', '登录');
    signIn.addEventListener('click', function () {
      if (window.MDXAuth && typeof window.MDXAuth.open === 'function') window.MDXAuth.open('signin');
    });
    gateBox.appendChild(signIn);

    controlsBox = el('div', 'tr-controls');
    buildControls();

    statusLine = el('p', 'tr-status');
    statusLine.setAttribute('role', 'status');

    var bodyWrap = el('div', 'tr-body');
    summaryBox = el('div', 'tr-summary');
    tableWrap = el('div', 'tr-tablewrap');
    expectationsBox = el('div', 'tr-expectations');
    bodyWrap.appendChild(summaryBox);
    bodyWrap.appendChild(tableWrap);
    bodyWrap.appendChild(expectationsBox);

    evidenceBox = el('div', 'tr-evidence');
    var evHead = el('h3');
    evHead.appendChild(t('Evidence receipts', '证据凭据'));
    evidenceBox.appendChild(evHead);
    evidenceList = el('div', 'tr-evidence-list');
    evidenceBox.appendChild(evidenceList);

    pagerBox = el('div', 'tr-pager');
    prevBtn = button('tr-prev', 'Previous', '上一页');
    prevBtn.addEventListener('click', function () {
      if (offset > 0) fetchPage(Math.max(0, offset - PAGE_LIMIT), false);
    });
    nextBtn = button('tr-next', 'Next', '下一页');
    nextBtn.addEventListener('click', function () {
      /* paging past page 1 pins expected_generation to the read generation */
      fetchPage(offset + PAGE_LIMIT, false);
    });
    pageInfo = el('span', 'tr-pageinfo');
    pagerBox.appendChild(prevBtn);
    pagerBox.appendChild(pageInfo);
    pagerBox.appendChild(nextBtn);

    drawer = el('div', 'tr-drawer');
    drawer.setAttribute('role', 'dialog');
    drawer.setAttribute('aria-modal', 'false');
    drawer.hidden = true;
    drawerClose = button('tr-drawer-close', 'Close', '关闭');
    drawerClose.addEventListener('click', closeDrawer);
    drawerBody = el('div', 'tr-drawer-body');
    drawer.appendChild(drawerClose);
    drawer.appendChild(drawerBody);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !drawer.hidden) closeDrawer();
    });

    shell.appendChild(gateBox);
    shell.appendChild(controlsBox);
    shell.appendChild(statusLine);
    shell.appendChild(bodyWrap);
    shell.appendChild(pagerBox);
    shell.appendChild(evidenceBox);
    MOUNT.appendChild(shell);
    MOUNT.appendChild(drawer);
  }

  function buildControls() {
    var sliceRow = el('div', 'tr-tabrow');
    sliceRow.setAttribute('data-tr-role', 'slices');
    SLICES.forEach(function (key) {
      var w = pair(L.slice, key);
      var tab = button('tr-tab', w[0], w[1]);
      tab.setAttribute('data-tr-slice', key);
      tab.addEventListener('click', function () {
        if (currentSlice === key) return;
        currentSlice = key;
        onSelectionChange();
      });
      sliceRow.appendChild(tab);
    });

    var viewRow = el('div', 'tr-tabrow');
    viewRow.setAttribute('data-tr-role', 'views');
    VIEWS.forEach(function (key) {
      var w = pair(L.view, key);
      var tab = button('tr-tab', w[0], w[1]);
      tab.setAttribute('data-tr-view', key);
      tab.addEventListener('click', function () {
        if (currentView === key) return;
        currentView = key;
        onSelectionChange();
      });
      viewRow.appendChild(tab);
    });

    var modeWrap = el('label', 'tr-mode');
    var modeLabel = el('span', 'tr-mode-label');
    modeLabel.appendChild(t('Time basis', '时间基准'));
    var modeSelect = el('select');
    modeSelect.className = 'tr-mode-select';
    MODES.forEach(function (key) {
      var w = pair(L.mode, key);
      var opt = el('option');
      opt.value = key;
      opt.appendChild(t(w[0], w[1]));
      modeSelect.appendChild(opt);
    });
    modeSelect.addEventListener('change', function () {
      if (currentMode === modeSelect.value) return;
      currentMode = modeSelect.value;
      onSelectionChange();
    });
    modeWrap.appendChild(modeLabel);
    modeWrap.appendChild(modeSelect);
    controlsBox.setAttribute('data-tr-role', 'controls');
    controlsBox.appendChild(sliceRow);
    controlsBox.appendChild(viewRow);
    controlsBox.appendChild(modeWrap);
  }

  /* ---- rendering --------------------------------------------------------- */

  function sectionForView() {
    if (!state.payload) return null;
    var views = state.payload.industrial_views;
    if (views && typeof views === 'object' && views[currentView] &&
        typeof views[currentView] === 'object') {
      return views[currentView];
    }
    if (currentView === 'economics' && state.payload.economics &&
        typeof state.payload.economics === 'object') {
      return state.payload.economics;
    }
    return null;
  }

  function renderControls() {
    var sliceTabs = controlsBox.querySelectorAll('[data-tr-slice]');
    Array.prototype.forEach.call(sliceTabs, function (tab) {
      tab.classList.toggle('on', tab.getAttribute('data-tr-slice') === currentSlice);
    });
    var viewTabs = controlsBox.querySelectorAll('[data-tr-view]');
    Array.prototype.forEach.call(viewTabs, function (tab) {
      tab.classList.toggle('on', tab.getAttribute('data-tr-view') === currentView);
    });
    var select = controlsBox.querySelector('select');
    if (select) select.value = currentMode;
  }

  function renderStatus() {
    clear(statusLine);
    if (ui.gate) { statusLine.hidden = true; return; }
    statusLine.hidden = false;
    var span;
    if (ui.loading) {
      statusLine.appendChild(t('Loading…', '加载中…'));
    } else if (state.error) {
      statusLine.appendChild(t(
        'The response did not match the expected shape and was not shown.',
        '返回数据不符合预期格式，未予显示。'
      ));
    } else if (ui.errorText) {
      span = el('span', 'tr-error');
      span.textContent = textSafe(ui.errorText);
      statusLine.appendChild(span);
      if (state.payload) {
        statusLine.appendChild(document.createTextNode(' '));
        statusLine.appendChild(t(
          'Showing the previous successful read.',
          '当前显示上一次成功读取的内容。'
        ));
      }
    } else if (state.payload) {
      span = el('span', 'tr-muted');
      span.textContent = textSafe(state.payload.definition_version);
      statusLine.appendChild(t('Ready · ', '已就绪 · '));
      statusLine.appendChild(span);
    } else {
      statusLine.appendChild(t('Nothing loaded yet.', '尚未加载内容。'));
    }
  }

  function renderLabeledList(container, headingEn, headingZh, value) {
    var heading = el('h3');
    heading.appendChild(t(headingEn, headingZh));
    container.appendChild(heading);
    var items = Array.isArray(value) ? value : (value === null || value === undefined || value === '' ? [] : [value]);
    if (!items.length) {
      container.appendChild(mutedLine(t('Nothing recorded yet.', '暂无记录。')));
      return;
    }
    items.forEach(function (item) {
      var line = el('p', 'tr-line');
      if (item && typeof item === 'object' && !Array.isArray(item)) {
        if (item.label) line.appendChild(chip(item.label));
        var span = el('span');
        span.textContent = textSafe(item.text !== undefined ? item.text : (item.value !== undefined ? item.value : ''));
        line.appendChild(span);
      } else {
        var plain = el('span');
        plain.textContent = textSafe(item);
        line.appendChild(plain);
      }
      container.appendChild(line);
    });
  }

  function renderSummary() {
    clear(summaryBox);
    if (ui.gate || !state.payload) { summaryBox.hidden = true; return; }
    summaryBox.hidden = false;
    var summary = state.payload.summary || {};
    renderLabeledList(summaryBox, 'What changed', '发生了什么变化', summary.what_changed);
    renderLabeledList(summaryBox, 'Why it matters', '为何重要', summary.why_it_matters);
    if (summary.next_evidence !== undefined && summary.next_evidence !== null && summary.next_evidence !== '') {
      renderLabeledList(summaryBox, 'Next evidence to watch', '下一个待观察证据', summary.next_evidence);
    }
  }

  function renderTable() {
    clear(tableWrap);
    if (ui.gate) { tableWrap.hidden = true; return; }
    tableWrap.hidden = false;

    var table = el('table', 'tr-table');
    var thead = el('thead');
    var headRow = el('tr');
    [['Item', '项目'], ['Reading', '读数'], ['Note', '注记']].forEach(function (pair_) {
      var th = el('th');
      th.appendChild(t(pair_[0], pair_[1]));
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    var tbody = el('tbody');
    var section = sectionForView();
    if (!state.payload) {
      appendStatusRow(tbody, t('Nothing loaded yet.', '尚未加载内容。'));
    } else if (!section) {
      appendStatusRow(tbody, statusWord('unavailable'));
    } else if (section.status !== 'ready') {
      /* the section's own status word — never an invented zero */
      appendStatusRow(tbody, statusWord(section.status));
    } else {
      var rows = Array.isArray(section.rows) ? section.rows : [];
      if (!rows.length) {
        appendStatusRow(tbody, t('No rows in this view yet.', '该视图暂无条目。'));
      }
      rows.forEach(function (row) {
        var tr = el('tr');
        var labelCell = el('td', 'tr-cell-label');
        if (row && typeof row === 'object') {
          if (row.label_kind) labelCell.appendChild(chip(row.label_kind));
          var labelSpan = el('span');
          labelSpan.textContent = textSafe(row.label);
          labelCell.appendChild(labelSpan);
          var valueCell = el('td');
          valueCell.textContent = textSafe(row.value);
          var noteCell = el('td', 'tr-muted');
          noteCell.textContent = textSafe(row.note);
          tr.appendChild(labelCell);
          tr.appendChild(valueCell);
          tr.appendChild(noteCell);
        } else {
          labelCell.textContent = textSafe(row);
          tr.appendChild(labelCell);
          tr.appendChild(el('td'));
          tr.appendChild(el('td'));
        }
        tbody.appendChild(tr);
      });
    }
    table.appendChild(tbody);
    tableWrap.appendChild(table);
  }

  function appendStatusRow(tbody, fragment) {
    var tr = el('tr');
    var td = el('td', 'tr-cell-status');
    td.colSpan = 3;
    td.appendChild(fragment);
    tr.appendChild(td);
    tbody.appendChild(tr);
  }

  function renderExpectations() {
    clear(expectationsBox);
    if (ui.gate || !state.payload) { expectationsBox.hidden = true; return; }
    expectationsBox.hidden = false;
    var heading = el('h3');
    heading.appendChild(t('Expectations', '预期'));
    expectationsBox.appendChild(heading);
    var expectations = state.payload.expectations || {};
    Object.keys(L.expectation).forEach(function (key) {
      var row = el('div', 'tr-xrow');
      var label = el('span', 'tr-xlabel');
      var w = pair(L.expectation, key);
      label.appendChild(t(w[0], w[1]));
      var value = el('span', 'tr-xvalue');
      var sub = expectations[key];
      var status = sub && typeof sub === 'object' ? sub.status : undefined;
      if (L.status[status]) {
        value.appendChild(statusWord(status));
        value.className = 'tr-xvalue tr-x-' + status;
      } else {
        value.textContent = textSafe(status);
      }
      row.appendChild(label);
      row.appendChild(value);
      expectationsBox.appendChild(row);
    });
  }

  function renderEvidence() {
    clear(evidenceList);
    if (ui.gate) { evidenceBox.hidden = true; return; }
    evidenceBox.hidden = false;
    var refs = (state.payload && Array.isArray(state.payload.evidence_refs))
      ? state.payload.evidence_refs : [];
    if (!refs.length) {
      evidenceList.appendChild(mutedLine(t('No evidence receipts in this read.', '本次读取没有证据凭据。')));
      return;
    }
    refs.forEach(function (ref) {
      var btn = button('tr-evidence-btn', 'Receipt', '凭据');
      var label = el('span');
      label.textContent = ' ' + textSafe(ref);
      btn.appendChild(label);
      btn.addEventListener('click', function () { openEvidence(ref, btn); });
      evidenceList.appendChild(btn);
    });
  }

  function renderPager() {
    if (ui.gate || !state.payload) {
      pagerBox.hidden = true;
      prevBtn.disabled = true;
      nextBtn.disabled = true;
      return;
    }
    pagerBox.hidden = false;
    prevBtn.disabled = offset <= 0;
    nextBtn.disabled = !state.payload;
    var from = offset + 1;
    var to = offset + PAGE_LIMIT;
    clear(pageInfo);
    pageInfo.appendChild(t(
      'Rows ' + from + '–' + to + ' · pinned to the read generation',
      '第 ' + from + '–' + to + ' 行 · 锁定当前读取版本'
    ));
  }

  function renderAll() {
    gateBox.hidden = !ui.gate;
    controlsBox.hidden = ui.gate;
    renderControls();
    renderStatus();
    renderSummary();
    renderTable();
    renderExpectations();
    renderEvidence();
    renderPager();
  }

  /* ---- drawer focus law --------------------------------------------------- */

  function openDrawer(invokingButton) {
    ui.drawerInvoker = invokingButton || null;
    drawer.hidden = false;
    drawerClose.focus();
  }

  function closeDrawer() {
    drawer.hidden = true;
    var invoker = ui.drawerInvoker;
    ui.drawerInvoker = null;
    if (invoker && typeof invoker.focus === 'function') invoker.focus();
  }

  function closeDrawerQuiet() {
    drawer.hidden = true;
    ui.drawerInvoker = null;
  }

  /* ---- change plumbing ----------------------------------------------------- */

  function onSelectionChange() {
    state.selection = { slice_key: currentSlice, view: currentView, time_mode: currentMode };
    rememberSelection();
    abortInFlight();
    nextEpoch(state, state.principalKey);
    clearResearchState(state);
    offset = 0;
    evidenceRefreshTried = false;
    ui.errorText = null;
    ui.gate = false;
    renderAll();
    if (state.principalKey !== 'anon') fetchPage(0, false);
  }

  function onAuthUser(user) {
    var principal = principalOf(user);
    MOUNT.hidden = false;  /* reveal only once auth has resolved, signed-in or not */
    abortInFlight();
    nextEpoch(state, principal);
    clearResearchState(state);
    offset = 0;
    evidenceRefreshTried = false;
    closeDrawerQuiet();
    ui.loading = false;
    ui.errorText = null;
    ui.gate = false;
    renderAll();  /* re-render immediately, before any new response resolves */
    if (principal === 'anon') {
      ui.gate = true;
      renderAll();
    } else {
      fetchPage(0, false);
    }
  }

  /* ---- boot ---------------------------------------------------------------- */

  restoreSelection();
  buildDom();
  renderAll();

  if (window.MDXAuth && typeof window.MDXAuth.onChange === 'function') {
    window.MDXAuth.onChange(function (user) { onAuthUser(user); });
    /* Safety net: if the auth surface never settles (SDK blocked), still
     * reveal the mount with the anonymous gate copy rather than nothing. */
    window.setTimeout(function () { if (MOUNT.hidden) onAuthUser(null); }, 2500);
  } else {
    onAuthUser(null);
  }
})();
