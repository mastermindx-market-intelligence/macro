(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(require('./intl_workspace_state.js'));
  } else {
    root.IntlWorkspace = factory(root.IntlWorkspaceState);
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function (IntlWorkspaceState) {
  'use strict';

  var HANDLES = typeof WeakMap === 'function' ? new WeakMap() : null;
  var STATE_KEYS = ['view', 'selected_market', 'compare_markets', 'horizon', 'currency_basis', 'return_basis', 'source_reference', 'expanded', 'library_group', 'baseline', 'return_stack'];
  var ISSUE_TEXT = {
    AMBIGUOUS_PANEL: { en: 'Data is ambiguous for this selection', zh: '此选择的数据不明确' },
    DESTROYED: { en: 'Workspace is destroyed', zh: '工作区已销毁' },
    INVALID_QUERY: { en: 'Invalid URL state restored', zh: '无效 URL 状态已还原' },
    PIN_LIMIT: { en: 'Pin limit reached', zh: '已达固定上限' },
    QUERY_TOO_LONG: { en: 'URL state is too long', zh: 'URL 状态过长' },
    STALE_SOURCE: { en: 'Source changed', zh: '数据源已变化' },
    NO_MATCHING_PANEL: { en: 'Data unavailable for this selection', zh: '无匹配数据' },
    UNSUPPORTED_MODE: { en: 'Unsupported workspace mode', zh: '不支持的工作区模式' },
    UNSUPPORTED_VIEW: { en: 'This view is not available yet', zh: '此视图暂不可用' },
    UNSUPPORTED_VALUE: { en: 'Unsupported value', zh: '不支持的值' }
  };

  function destroyedResult() {
    return { ok: false, state: null, issues: [{ code: 'DESTROYED', field: 'workspace' }], intent: null };
  }

  function textFor(issues, language) {
    var code = issues && issues.length > 0 && issues[0] && issues[0].code ? String(issues[0].code) : 'GENERIC';
    var localized = ISSUE_TEXT[code];
    if (!localized) return language === 'zh' ? '工作区状态不可用' : 'Workspace state unavailable';
    return language === 'zh' ? localized.zh : localized.en;
  }

  function issueCode(issues, fallback) {
    return issues && issues.length > 0 && issues[0] && issues[0].code ? String(issues[0].code) : fallback;
  }

  function normalLanguage(element) {
    var language = element.ownerDocument.documentElement.getAttribute('lang');
    return language && language.toLowerCase().indexOf('zh') === 0 ? 'zh' : 'en';
  }

  function required(root, selector) {
    var element = owned(root, selector)[0];
    if (!element) throw new Error('Missing required International workspace element: ' + selector);
    return element;
  }

  function owned(root, selector) {
    return Array.from(root.querySelectorAll(selector)).filter(function (node) {
      return node.closest('[data-im-workspace]') === root;
    });
  }

  function snapshotRoot(root) {
    var selector = '[data-im-heading],[data-im-issues],[data-im-unavailable],[data-im-panel],'+
      '[data-im-action],[data-im-expanded-region],[data-im-expansion-trigger] .l-en,[data-im-expansion-trigger] .l-zh';
    return [root].concat(owned(root, selector)).map(function (node) {
      var attrs = [], text = false, value = false;
      if (node === root) attrs.push('data-im-enhanced');
      if (node.matches('[data-im-heading]')) attrs.push('tabindex');
      if (node.matches('[data-im-issues]')) { attrs.push('role'); text = true; }
      if (node.matches('[data-im-unavailable],[data-im-panel],[data-im-expanded-region]')) attrs.push('hidden');
      if (node.matches('button[data-im-action="set_view"]')) attrs.push('disabled','aria-pressed');
      if (node.matches('select[data-im-action]')) value = ['select_market','set_library_group','set_view','set_horizon','set_basis'].includes(node.getAttribute('data-im-action'));
      if (node.matches('[data-im-expansion-trigger]')) attrs.push('hidden','aria-expanded','data-im-expanded');
      if (node.matches('[data-im-expansion-trigger] .l-en,[data-im-expansion-trigger] .l-zh')) text = true;
      return {node:node, attrs:Array.from(new Set(attrs)).map(function (name) {return [name,node.getAttribute(name)];}),
        value:value ? node.value : null, children:text ? Array.from(node.childNodes) : null};
    });
  }

  function rememberNodes(controller, snapshot) {
    snapshot.forEach(function (entry) {
      if (!controller.original.some(function (old) { return old.node === entry.node; })) controller.original.push(entry);
    });
  }

  function restoreRoot(root, snapshot) {
    snapshot.forEach(function (entry) {
      var node = entry.node;
      if (node !== root && node.closest('[data-im-workspace]') !== root) return;
      entry.attrs.forEach(function (attribute) {
        if (attribute[1] === null) node.removeAttribute(attribute[0]);
        else node.setAttribute(attribute[0], attribute[1]);
      });
      if (entry.value !== null) node.value = entry.value;
      if (entry.children !== null) node.replaceChildren.apply(node, entry.children);
    });
  }

  function panelValid(panel, config, source) {
    if (!['overview', 'compare', 'macro', 'risk', 'history', 'library'].includes(panel.getAttribute('data-view')) ||
        !config.horizons.includes(panel.getAttribute('data-horizon')) ||
        !config.bases.includes(panel.getAttribute('data-basis')) ||
        !panel.hasAttribute('data-source') || panel.getAttribute('data-source') !== (source === null ? '' : source)) return false;
    if (panel.hasAttribute('data-market') && panel.getAttribute('data-market') !== '' &&
        !config.markets.includes(panel.getAttribute('data-market'))) return false;
    if (panel.hasAttribute('data-pins')) {
      try {
        var pins = JSON.parse(panel.getAttribute('data-pins'));
        if (!Array.isArray(pins) || pins.length > 4 || new Set(pins).size !== pins.length ||
            pins.some(function (id) { return !config.markets.includes(id); })) return false;
      } catch (_) { return false; }
    }
    return true;
  }

  function panelFor(controller, state) {
    return owned(controller.root, '[data-im-panel]').filter(function (panel) {
      if (!panelValid(panel, controller.config, state.source_reference) ||
          panel.getAttribute('data-view') !== state.view ||
          panel.getAttribute('data-horizon') !== state.horizon ||
          panel.getAttribute('data-basis') !== state.currency_basis) return false;
      if (panel.hasAttribute('data-market') && (panel.getAttribute('data-market') || null) !== state.selected_market) return false;
      if (panel.hasAttribute('data-pins') && JSON.stringify(JSON.parse(panel.getAttribute('data-pins'))) !== JSON.stringify(state.compare_markets)) return false;
      return true;
    });
  }

  function structuralPanels(controller, source) {
    return new Set(owned(controller.root, '[data-im-panel]').filter(function (panel) {
      return panelValid(panel, controller.config, source);
    }).map(function (panel) { return panel.getAttribute('data-view'); }));
  }

  function paint(controller, state, issues) {
    var root = controller.root;
    var panels = panelFor(controller, state);
    var panel = panels.length === 1 ? panels[0] : null;
    var supported = structuralPanels(controller, state.source_reference);
    owned(root, '[data-im-action]').forEach(function (control) {
      var action = control.getAttribute('data-im-action');
      if (action === 'set_view' && control.tagName === 'BUTTON') {
        control.setAttribute('aria-pressed', String(control.getAttribute('data-im-view') === state.view));
        control.disabled = !supported.has(control.getAttribute('data-im-view'));
      } else if (control.tagName === 'SELECT') {
        var fields = {select_market:'selected_market', set_library_group:'library_group',
          set_view:'view', set_horizon:'horizon', set_basis:'currency_basis'};
        if (fields[action]) control.value = state[fields[action]] === null ? '' : state[fields[action]];
      }
    });
    owned(root, '[data-im-panel]').forEach(function (node) { node.hidden = node !== panel; });
    required(root, '[data-im-unavailable]').hidden = !!panel;
    var reported = issues.slice();
    if (panels.length > 1) reported.unshift({code:'AMBIGUOUS_PANEL', field:'panel'});
    else if (!panel && !reported.length) reported.push({code:supported.has(state.view) ? 'NO_MATCHING_PANEL' : 'UNSUPPORTED_VIEW', field:'panel'});
    required(root, '[data-im-issues]').textContent = reported.length ? textFor(reported, normalLanguage(root)) : '';
    if (panel) {
      owned(root, '[data-im-expanded-region]').filter(function (node) { return panel.contains(node); }).forEach(function (node) { node.hidden = !state.expanded; });
      owned(root, '[data-im-expansion-trigger]').filter(function (node) { return panel.contains(node); }).forEach(function (node) {
        node.hidden = false;
        node.setAttribute('aria-expanded', String(state.expanded));
        node.setAttribute('data-im-expanded', String(!state.expanded));
        var en = node.querySelector('.l-en'), zh = node.querySelector('.l-zh');
        if (en) en.textContent = state.expanded ? 'Collapse all markets' : 'Expand all markets';
        if (zh) zh.textContent = state.expanded ? '收起全部市场' : '展开全部市场';
      });
    }
    return reported;
  }

  function repaintIssues(controller) {
    required(controller.root, '[data-im-issues]').textContent = controller.issues.length ? textFor(controller.issues, normalLanguage(controller.root)) : '';
  }

  function urlPath(pathname) {
    return typeof pathname === 'string' && pathname.charAt(0) === '/' && pathname.indexOf('\\') === -1 && pathname.slice(0, 2) !== '//' && !/[\u0000-\u001f\u007f-\u009f]/.test(pathname) ? pathname : '/';
  }

  function anchorHash(location, anchorIds) {
    var raw = location.hash;
    if (!raw) return '';
    var decoded;
    try {
      decoded = decodeURIComponent(raw.charAt(0) === '#' ? raw.slice(1) : raw);
    } catch (error) { return ''; }
    if (decodeURIComponent(encodeURIComponent(decoded)) !== decoded || anchorIds.indexOf(decoded) === -1) return '';
    return '#' + encodeURIComponent(decoded);
  }

  function nextUrl(controller, query) {
    var location = controller.environment.window.location;
    return urlPath(location.pathname) + '?' + query + anchorHash(location, controller.config.anchor_ids);
  }

  function stageAndCommit(controller, state, issues, actionType) {
    var previous = controller.state;
    var snapshot = snapshotRoot(controller.root);
    rememberNodes(controller, snapshot);
    var serialized = controller.reducer.serializeQuery(state);
    if (!serialized.ok) return {ok:false, state:previous, issues:serialized.issues, intent:null};
    var shouldPush = !['mount', 'popstate', 'resize'].includes(actionType) && serialized.query !== controller.serializedQuery;
    try {
      var reported = paint(controller, state, issues);
      if (shouldPush) controller.environment.window.history.pushState(null, '', nextUrl(controller, serialized.query));
      controller.state = state;
      controller.issues = reported;
      controller.serializedQuery = serialized.query;
      return {ok:true, state:state, issues:reported, intent:null};
    } catch (error) {
      restoreRoot(controller.root, snapshot);
      if (actionType === 'mount') throw error;
      return {ok:false, state:previous, issues:[{code:'UI_UPDATE_FAILED', field:'workspace'}], intent:null};
    }
  }

  function dispatch(controller, action) {
    if (!controller.live) return destroyedResult();
    var result = controller.reducer.reduce(controller.state, action);
    if (!result.ok) { controller.issues = result.issues; repaintIssues(controller); return result; }
    if (action && action.type === 'replace_source') return { ok: false, state: controller.state, issues: [{ code: 'USE_REPLACE_SOURCE', field: 'source_reference' }], intent: null };
    if (action && action.type === 'set_view' && !structuralPanels(controller, controller.state.source_reference).has(action.view)) {
      controller.issues = [{code:'UNSUPPORTED_VIEW', field:'view'}]; repaintIssues(controller);
      return {ok:false, state:controller.state, issues:controller.issues, intent:null};
    }
    var committed = stageAndCommit(controller, result.state, result.issues, action && action.type, false);
    if (committed.ok) { committed.intent = result.intent; if (result.intent && result.intent.type === 'restore_focus') restoreFocus(controller, result.intent.anchor_id); }
    return committed;
  }

  function restoreFocus(controller, anchorId) {
    var root = controller.root, win = controller.environment.window;
    var candidate = controller.config.anchor_ids.includes(anchorId) ? owned(root, '[id]').find(function (node) { return node.id === anchorId; }) : null;
    var visible = candidate && !candidate.closest('[hidden]') && candidate.getClientRects().length && win.getComputedStyle(candidate).visibility !== 'hidden';
    var target = visible ? candidate : required(root, '[data-im-heading]');
    target.focus();
  }

  function popstate(controller) {
    if (!controller.live) return;
    var parsed = controller.reducer.parseQuery(controller.environment.window.location.search);
    var committed = stageAndCommit(controller, parsed.state, parsed.issues, 'popstate', false);
    controller.issues = committed.issues;
  }

  function actionFromEvent(controller, event) {
    if (event.type === 'click') {
      var button = event.target && event.target.closest ? event.target.closest('button[data-im-action]') : null;
      if (!button || button.disabled || button.closest('[data-im-workspace]') !== controller.root || event.target.closest('a,input,textarea,select,[contenteditable]')) return null;
      var type = button.getAttribute('data-im-action');
      if (type === 'set_view') return { type: type, view: button.getAttribute('data-im-view') };
      if (type === 'select_market' || type === 'pin' || type === 'unpin') return { type: type, market_id: button.getAttribute('data-im-market') || null };
      if (type === 'set_horizon') return { type: type, horizon: button.getAttribute('data-im-horizon') };
      if (type === 'set_basis') return { type: type, currency_basis: button.getAttribute('data-im-basis') };
      if (type === 'set_library_group') return { type: type, group_id: button.getAttribute('data-im-group') || null };
      if (type === 'push_return') return { type: type, anchor_id: button.getAttribute('data-im-anchor') || null };
      if (type === 'set_expanded') {
        var expanded = button.getAttribute('data-im-expanded');
        if (expanded !== 'true' && expanded !== 'false') return null;
        return { type: type, expanded: expanded === 'true' };
      }
      if (type === 'capture_baseline' || type === 'back' || type === 'resize') return { type: type };
      return null;
    }
    var select = event.target && event.target.tagName === 'SELECT' && event.target.hasAttribute('data-im-action') ? event.target : null;
    if (!select || select.disabled || select.closest('[data-im-workspace]') !== controller.root) return null;
    var selectAction = select.getAttribute('data-im-action');
    if (selectAction === 'select_market') return { type: selectAction, market_id: select.value === '' ? null : select.value };
    if (selectAction === 'set_library_group') return { type: selectAction, group_id: select.value === '' ? null : select.value };
    var fields = {set_view:'view', set_horizon:'horizon', set_basis:'currency_basis', pin:'market_id', unpin:'market_id', push_return:'anchor_id'};
    if (fields[selectAction]) { var selected = {type:selectAction}; selected[fields[selectAction]] = select.value === '' ? null : select.value; return selected; }
    if (selectAction === 'set_expanded' && ['true','false'].includes(select.value)) return {type:selectAction, expanded:select.value === 'true'};
    return null;
  }

  function clickOrChange(controller, event) {
    var action = actionFromEvent(controller, event);
    if (!action) return;
    event.preventDefault();
    dispatch(controller, action);
  }

  function replaceSource(controller, newSource, expectedSource) {
    if (!controller.live) return destroyedResult();
    if (arguments.length < 3 || expectedSource === undefined) return { ok: false, state: controller.state, issues: [{ code: 'EXPECTED_SOURCE_REQUIRED', field: 'expectedSource' }], intent: null };
    if (!controller.live || expectedSource !== controller.state.source_reference) return { ok: false, state: controller.state, issues: [{ code: 'STALE_SOURCE', field: 'expectedSource' }], intent: null };
    var replacement = IntlWorkspaceState.createIntlWorkspaceState(controller.configWithSource(newSource));
    var parsed = replacement.parseQuery(controller.reducer.serializeQuery(controller.state).query);
    if (!parsed.ok) return { ok: false, state: controller.state, issues: parsed.issues, intent: null };
    var expanded = replacement.reduce(parsed.state, { type: 'set_expanded', expanded: controller.state.expanded });
    if (!expanded.ok) return expanded;
    var previousNodes = snapshotRoot(controller.root);
    rememberNodes(controller, previousNodes);
    var previousState = controller.state;
    var previousReducer = controller.reducer;
    var previousSerialized = controller.serializedQuery;
    var previousIssues = controller.issues;
    var failed = true;
    try {
      var reported = paint(controller, expanded.state, []);
      controller.reducer = replacement;
      controller.state = expanded.state;
      controller.issues = reported;
      controller.serializedQuery = replacement.serializeQuery(expanded.state).query;
      failed = false;
      return { ok: true, state: expanded.state, issues: reported, intent: { type: 'invalidate_source_bound_context' } };
    } finally {
      if (failed) {
        controller.reducer = previousReducer;
        controller.state = previousState;
        controller.issues = previousIssues;
        controller.serializedQuery = previousSerialized;
        restoreRoot(controller.root, previousNodes);
      }
    }
  }

  function mountIntlWorkspace(root, config, environment) {
    if (!environment || typeof environment !== 'object') environment = arguments.length >= 3 ? environment : { window: root.ownerDocument.defaultView };
    if (arguments.length === 2) environment = { window: root.ownerDocument.defaultView };
    if (HANDLES && HANDLES.has(root)) {
      var existing = HANDLES.get(root);
      if (existing) return existing;
    }
    if (!root || root.nodeType !== 1 || !root.hasAttribute('data-im-workspace') || !root.hasAttribute('data-im-mode')) throw new TypeError('IntlWorkspace root must be an Element');
    if (root.getAttribute('data-im-mode') !== 'macro') {
      var refusal = new TypeError('Unsupported International workspace mode');
      refusal.code = 'UNSUPPORTED_MODE';
      throw refusal;
    }
    if (!IntlWorkspaceState || typeof IntlWorkspaceState.createIntlWorkspaceState !== 'function') throw new Error('IntlWorkspaceState API is unavailable');
    var window = environment.window;
    if (!window || !window.history || !window.location || !window.MutationObserver) throw new Error('Workspace environment API is unavailable');
    var reducer = IntlWorkspaceState.createIntlWorkspaceState(config);
    config = JSON.parse(JSON.stringify(config));
    var sourceConfig = config;
    var configWithSource = function (source) {
      var copy = {};
      var fields = ['markets', 'horizons', 'bases', 'default_horizon', 'default_basis', 'source_reference', 'anchor_ids', 'library_group_ids'];
      for (var index = 0; index < fields.length; index += 1) copy[fields[index]] = fields[index] === 'source_reference' ? source : sourceConfig[fields[index]];
      return copy;
    };
    var controller = {
      root: root, config: config, configWithSource: configWithSource, reducer: reducer, environment: { window: window },
      state: null, issues: [], serializedQuery: '', live: false, original: []
    };
    var snapshot = snapshotRoot(root);
    controller.original = snapshot.slice();
    var installed = { listeners: false, popstate: false, observer: null };
    try {
      required(root, '[data-im-heading]').setAttribute('tabindex', '-1');
      required(root, '[data-im-issues]').setAttribute('role', 'status');
      required(root, '[data-im-unavailable]');
      var parsed = reducer.parseQuery(window.location.search);
      stageAndCommit(controller, parsed.state, parsed.issues, 'mount', false);
      controller.live = true;
      controller.onClick = function (event) { clickOrChange(controller, event); };
      controller.onChange = function (event) { clickOrChange(controller, event); };
      controller.onPopstate = function () { popstate(controller); };
      controller.onResize = function () { dispatch(controller, {type:'resize'}); };
      root.addEventListener('click', controller.onClick, false);
      root.addEventListener('change', controller.onChange, false);
      window.addEventListener('popstate', controller.onPopstate, false);
      window.addEventListener('resize', controller.onResize, false);
      controller.observer = new window.MutationObserver(function () { repaintIssues(controller); });
      controller.observer.observe(window.document.documentElement, { attributes: true, attributeFilter: ['lang'] });
      root.setAttribute('data-im-enhanced', 'true');
      var handle = {
        dispatch: function (action) { return JSON.parse(JSON.stringify(dispatch(controller, action))); },
        getState: function () { return controller.state === null ? null : JSON.parse(JSON.stringify(controller.state)); },
        replaceSource: function (newSource, expectedSource) { return JSON.parse(JSON.stringify(replaceSource(controller, newSource, expectedSource))); },
        destroy: function () { return destroy(controller); }
      };
      if (!HANDLES) throw new Error('WeakMap is unavailable');
      HANDLES.set(root, handle);
      return handle;
    } catch (error) {
      if (controller.observer) controller.observer.disconnect();
      if (controller.onClick) root.removeEventListener('click', controller.onClick, false);
      if (controller.onChange) root.removeEventListener('change', controller.onChange, false);
      if (controller.onPopstate) window.removeEventListener('popstate', controller.onPopstate, false);
      if (controller.onResize) window.removeEventListener('resize', controller.onResize, false);
      restoreRoot(root, controller.original);
      throw error;
    }
  }

  function destroy(controller) {
    if (!controller.live) return false;
    controller.live = false;
    controller.state = null;
    controller.reducer = null;
    if (controller.observer) controller.observer.disconnect();
    controller.root.removeEventListener('click', controller.onClick, false);
    controller.root.removeEventListener('change', controller.onChange, false);
    controller.environment.window.removeEventListener('popstate', controller.onPopstate, false);
    controller.environment.window.removeEventListener('resize', controller.onResize, false);
    HANDLES.delete(controller.root);
    restoreRoot(controller.root, controller.original);
    return true;
  }

  return { mountIntlWorkspace: mountIntlWorkspace };
});
