(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) {
    var search;
    try { search = require('./intl_library_search.js'); } catch (error) { if (error.code !== 'MODULE_NOT_FOUND') throw error; }
    module.exports = factory(require('./intl_workspace_state.js'), search);
  } else {
    root.IntlWorkspace = factory(root.IntlWorkspaceState, root.IntlLibrarySearch);
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function (IntlWorkspaceState, IntlLibrarySearch) {
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

  // Library is metadata owned by this workspace. Search state is a local draft;
  // the existing reducer remains the sole owner of shareable research context.
  function prepareLibrary(root, config) {
    var panels = owned(root, '[data-view="library"][data-im-library-static]');
    if (panels.length !== 1) return null;
    var panel = panels[0];
    function all(selector) { return owned(root, selector).filter(function (node) { return panel.contains(node); }); }
    function one(selector) { var nodes = all(selector); return nodes.length === 1 ? nodes[0] : null; }
    var library = {panel:panel, all:all, input:one('[data-im-library-search]'), form:one('[data-im-library-search-form]'),
      clear:one('[data-im-library-clear]'), status:one('[data-im-library-status]'), groupsRoot:one('[data-im-library-groups]'),
      results:one('[data-im-library-results]'), empty:one('[data-im-library-empty]'), back:one('[data-im-library-back]'),
      groups:all('[data-im-library-group]'), rows:all('[data-im-library-tool]'), valid:false, query:'', composing:false};
    library.placements = library.rows.map(function (node) { return {node:node,parent:node.parentNode,next:node.nextSibling}; });
    try {
      if (!['input','form','clear','status','groupsRoot','results','empty','back'].every(function (key) { return !!library[key]; }) ||
          !IntlLibrarySearch || typeof IntlLibrarySearch.searchIntlTools !== 'function') return library;
      var script = one('script[data-im-library-catalogue]');
      if (!script) return library;
      var catalogue = JSON.parse(script.textContent);
      // The accepted helper validates the complete public catalogue schema.
      IntlLibrarySearch.searchIntlTools(catalogue, '', null);
      var groups = new Set(library.groups.map(function (group) { return group.getAttribute('data-im-library-group'); }));
      if (groups.size !== 6 || library.groups.length !== 6 || catalogue.length !== 18 || library.rows.length !== 18 ||
          groups.size !== config.library_group_ids.length || config.library_group_ids.some(function (id) { return !groups.has(id); }) ||
          library.groups.some(function (group) {
            var id=group.getAttribute('data-im-library-group');
            return !library.groupsRoot.contains(group) || catalogue.filter(function (item) { return item.group_id===id; }).length!==3 ||
              all('[data-im-library-tools]').filter(function (list) { return list.closest('[data-im-library-group]')===group; }).length!==1;
          })) return library;
      var byKey = new Map(library.rows.map(function (row) { return [row.getAttribute('data-im-library-tool'),row]; }));
      if (byKey.size !== library.rows.length || catalogue.some(function (item) {
        var row = byKey.get(item.presentation_key);
        return !row || row.getAttribute('data-im-library-order') !== String(item.order) ||
          !row.parentNode.matches('[data-im-library-tools]') || row.parentNode.getAttribute('data-im-library-tools') !== item.group_id ||
          !groups.has(item.group_id) || !row.closest('[data-im-library-group]') ||
          row.closest('[data-im-library-group]').getAttribute('data-im-library-group') !== item.group_id;
      })) return library;
      library.catalogue = catalogue; library.byKey = byKey; library.valid = true;
      library.query = library.input.value;
    } catch (_) { /* The approved static page survives failed enhancement. */ }
    return library;
  }

  function restoreLibraryRows(placements) {
    // Restore right siblings first, including whitespace/text siblings. Moving
    // original nodes preserves third-party handlers and exact pre-mount order.
    placements.slice().reverse().forEach(function (entry) {
      var next = entry.next && entry.next.parentNode === entry.parent ? entry.next : null;
      if (entry.node.parentNode !== entry.parent || entry.node.nextSibling !== next) entry.parent.insertBefore(entry.node,next);
    });
  }

  function paintLibrary(controller, state) {
    var library = controller.library;
    if (!library || library.panel.hidden) return;
    var zh = normalLanguage(controller.root) === 'zh';
    if (!library.valid) {
      library.panel.removeAttribute('data-im-library-enhanced');
      if (library.input) library.input.disabled = true;
      if (library.clear) library.clear.disabled = true;
      library.all('[data-im-library-group-open]').forEach(function (button) { button.hidden = true; });
      if (library.status) library.status.textContent = zh ? '此视图的工具目录暂不可用。' : 'The tool catalogue is unavailable for this view.';
      return;
    }
    library.panel.setAttribute('data-im-library-enhanced','true');
    library.input.disabled = false; library.clear.disabled = false;
    library.input.setAttribute('placeholder',zh ? '工具名称、问题或别名' : 'Tool name, question or alias');
    var matches, invalid = false;
    try { matches = IntlLibrarySearch.searchIntlTools(library.catalogue, library.query, state.library_group); }
    catch (_) { invalid = true; matches = []; }
    var searching = library.query.trim().length > 0;
    var resultRows = !invalid && searching ? matches.map(function (match) { return library.byKey.get(match.presentation_key); }) : [];
    var resultSet = new Set(resultRows);
    restoreLibraryRows(library.placements.filter(function (entry) { return !resultSet.has(entry.node); }));
    library.groupsRoot.hidden = invalid || searching;
    library.groups.forEach(function (group) {
      var id = group.getAttribute('data-im-library-group');
      group.hidden = !!state.library_group && id !== state.library_group;
      if (id === state.library_group) group.setAttribute('data-im-library-active','');
      else group.removeAttribute('data-im-library-active');
    });
    library.all('[data-im-library-group-open]').forEach(function (button) { button.hidden = false; });
    library.results.hidden = invalid || !searching || !matches.length;
    library.empty.hidden = invalid || !searching || !!matches.length;
    library.back.hidden = !state.library_group;
    library.status.textContent = invalid ? (zh ? '搜索内容无效。请输入不超过256个字符，且不含不支持的控制字符。' : 'Search input is invalid. Use up to 256 characters without unsupported control characters.') :
      searching && !matches.length ? (zh ? '没有匹配的工具。请尝试其他工具名称或问题。' : 'No tools match this search. Try another tool name or question.') : '';
    var nextResult = null;
    resultRows.slice().reverse().forEach(function (row) {
      if (row.parentNode !== library.results || row.nextSibling !== nextResult) {
        if (nextResult === null) library.results.appendChild(row);
        else library.results.insertBefore(row,nextResult);
      }
      nextResult = row;
    });
  }

  function libraryEvent(controller, event) {
    var library = controller.library;
    if (!controller.live || !library || !library.valid || library.panel.hidden ||
        !event.target.closest || event.target.closest('[data-im-workspace]')!==controller.root) return false;
    if (event.type === 'submit' && event.target === library.form) { event.preventDefault(); return true; }
    var clear = event.type === 'click' && event.target.closest && event.target.closest('[data-im-library-clear]') === library.clear;
    if (!clear && event.target !== library.input) return false;
    if (event.type === 'compositionstart') { library.composing = true; return true; }
    if (event.type === 'input' && library.composing) {
      // Validate the interim draft through the same helper, but keep the last
      // committed result set until composition ends (including locale changes).
      try { IntlLibrarySearch.searchIntlTools(library.catalogue, library.input.value, controller.state.library_group, {composing:true}); } catch (_) {}
      return true;
    }
    if (clear || event.type === 'compositionend' || event.type === 'input') {
      if (clear) { event.preventDefault(); library.input.value = ''; }
      var previousQuery = library.query;
      library.composing = false; library.query = library.input.value;
      var committed = stageAndCommit(controller,controller.state,controller.issues,'resize');
      if (!committed.ok) { library.query=previousQuery; library.input.value=previousQuery; }
      if (clear) library.input.focus();
      return true;
    }
    return false;
  }

  var INSPECTOR_FIELDS = ['local', 'usd', 'fx_contribution'];

  function inspectorPublic(controller) {
    if (!controller.inspector) return null;
    return { market: controller.inspector.market, mode: controller.inspector.mode, field: controller.inspector.field };
  }

  function inspectorResult(controller, ok, issues) {
    return { ok: ok, state: controller.state, issues: issues || [], intent: null, inspector: inspectorPublic(controller) };
  }

  function isPlainOwnObject(value) {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
    var prototype = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  function ownDataCopy(value, expectedKeys) {
    if (!isPlainOwnObject(value)) return null;
    if (Object.getOwnPropertySymbols(value).length !== 0) return null;
    var names = Object.getOwnPropertyNames(value);
    if (names.length !== expectedKeys.length) return null;
    var copy = {};
    for (var index = 0; index < expectedKeys.length; index += 1) {
      var key = expectedKeys[index];
      if (!Object.prototype.hasOwnProperty.call(value, key)) return null;
      var descriptor = Object.getOwnPropertyDescriptor(value, key);
      if (!descriptor || !('value' in descriptor) || descriptor.get || descriptor.set) return null;
      var field = descriptor.value;
      var fieldType = typeof field;
      if (fieldType === 'function' || fieldType === 'symbol' || fieldType === 'undefined' || fieldType === 'bigint') return null;
      if (fieldType === 'number' && !Number.isFinite(field)) return null;
      if (fieldType === 'object' && field !== null) return null;
      copy[key] = field;
    }
    return copy;
  }

  function normalizeSource(value) {
    if (value === null || value === '') return null;
    if (typeof value !== 'string') return undefined;
    return value;
  }

  function articleSource(article) {
    if (!article.hasAttribute('data-source')) return null;
    var value = article.getAttribute('data-source');
    return value === '' ? null : value;
  }

  function articleOwned(controller, node) {
    return !!(node && node.closest && node.closest('[data-im-workspace]') === controller.root);
  }

  function inspectorShell(controller) {
    var shells = owned(controller.root, 'dialog[data-im-inspector-shell]');
    return shells.length === 1 ? shells[0] : null;
  }

  function articleMatchesTuple(article, state) {
    return article.getAttribute('data-horizon') === state.horizon &&
      article.getAttribute('data-basis') === state.currency_basis &&
      article.getAttribute('data-return-basis') === state.return_basis &&
      !article.hasAttribute('data-view');
  }

  function articleMatchesRequest(controller, article, marketId, expectedSource) {
    return articleOwned(controller, article) &&
      article.getAttribute('data-market-id') === marketId &&
      articleMatchesTuple(article, controller.state) &&
      articleSource(article) === expectedSource;
  }

  function matchingInspectorArticles(controller, marketId, expectedSource) {
    return owned(controller.root, '[data-im-inspector-payload]').filter(function (article) {
      return articleMatchesRequest(controller, article, marketId, expectedSource);
    });
  }

  function overviewContextId(panel) {
    if (!panel || typeof panel.id !== 'string') return null;
    var suffix = '-overview';
    if (panel.id.length <= suffix.length) return null;
    if (panel.id.slice(panel.id.length - suffix.length) !== suffix) return null;
    var contextId = panel.id.slice(0, panel.id.length - suffix.length);
    return contextId || null;
  }

  function activeOverviewPanels(controller) {
    if (!controller.state || controller.state.view !== 'overview') return [];
    return panelFor(controller, controller.state).filter(function (panel) {
      return panel.getAttribute('data-view') === 'overview';
    });
  }

  function inspectorFingerprint(state) {
    return JSON.stringify({
      view: state.view,
      horizon: state.horizon,
      currency_basis: state.currency_basis,
      return_basis: state.return_basis,
      selected_market: state.selected_market,
      pins: state.compare_markets,
      source: state.source_reference
    });
  }

  function appendWords(parent, en, zh) {
    var enNode = parent.ownerDocument.createElement('span');
    enNode.className = 'l-en';
    enNode.textContent = en;
    var zhNode = parent.ownerDocument.createElement('span');
    zhNode.className = 'l-zh';
    zhNode.setAttribute('lang', 'zh');
    zhNode.textContent = zh;
    parent.appendChild(enNode);
    parent.appendChild(zhNode);
  }

  function makeInspectorButton(document, action, en, zh) {
    var button = document.createElement('button');
    button.setAttribute('type', 'button');
    button.setAttribute('data-im-inspector-action', action);
    appendWords(button, en, zh);
    return button;
  }

  function captureScrollOffsets(controller, origin) {
    var win = controller.environment.window;
    var lists = [];
    var node = origin;
    while (node && node !== controller.root) {
      if (node.nodeType === 1 && (node.scrollTop || node.scrollLeft)) {
        lists.push({ node: node, top: node.scrollTop, left: node.scrollLeft });
      }
      node = node.parentNode;
    }
    return {
      windowX: win.scrollX || win.pageXOffset || 0,
      windowY: win.scrollY || win.pageYOffset || 0,
      lists: lists
    };
  }

  function restoreScrollOffsets(controller, scroll) {
    if (!scroll) return;
    var win = controller.environment.window;
    if (typeof win.scrollTo === 'function') win.scrollTo(scroll.windowX, scroll.windowY);
    scroll.lists.forEach(function (entry) {
      if (!entry.node || !entry.node.isConnected) return;
      entry.node.scrollTop = entry.top;
      entry.node.scrollLeft = entry.left;
    });
  }

  function nodeUsable(controller, node) {
    if (!node || !node.isConnected || !articleOwned(controller, node)) return false;
    if (node.closest('[hidden]')) return false;
    if (!node.getClientRects || !node.getClientRects().length) return false;
    var win = controller.environment.window;
    try {
      if (win.getComputedStyle && win.getComputedStyle(node).visibility === 'hidden') return false;
    } catch (_) {}
    return true;
  }

  function inspectorHeading(article, mode, field) {
    if (mode === 'ledger') return article.querySelector('[data-im-inspector-page="ledger"] [tabindex="-1"], [data-im-inspector-page="ledger"] h4');
    if (mode === 'field' && field) {
      var block = article.querySelector('[data-im-inspector-field="' + field + '"]');
      return block ? block.querySelector('[tabindex="-1"], h5') : null;
    }
    if (mode === 'deeper') {
      var deeper = article.querySelector('[data-im-inspector-page="deeper"]');
      return deeper ? deeper.querySelector('[tabindex="-1"], h4') : article.querySelector('[data-im-inspector-title]');
    }
    return article.querySelector('[data-im-inspector-title]');
  }

  function snapshotInspectorOwned(root) {
    var selector = '[data-im-inspector-origin],[data-im-inspector-payload],[data-im-inspector-enhancement],[data-im-inspector-page],[data-im-inspector-ledger],[data-im-inspector-field],[data-im-inspector-shell]';
    return owned(root, selector).map(function (node) {
      var attrs = ['hidden'];
      if (node.matches('details')) attrs.push('open');
      if (node.matches('[data-im-inspector-shell]')) attrs.push('aria-labelledby', 'aria-label');
      return {
        node: node,
        attrs: attrs.map(function (name) { return [name, node.getAttribute(name)]; }),
        open: 'open' in node ? !!node.open : null,
        parent: node.matches('[data-im-inspector-payload]') ? node.parentNode : null,
        next: node.nextSibling
      };
    });
  }

  function snapshotInspectorSubtree(article, shell, originDetails) {
    var nodes = [article, shell, originDetails];
    if (article) nodes = nodes.concat(Array.from(article.querySelectorAll('[data-im-inspector-enhancement],[data-im-inspector-page],[data-im-inspector-ledger],[data-im-inspector-field],[data-im-inspector-deeper-unavailable]')));
    return nodes.filter(Boolean).map(function (node) {
      return {
        node: node,
        hidden: !!node.hidden,
        open: 'open' in node ? !!node.open : null,
        labelledby: node.getAttribute ? node.getAttribute('aria-labelledby') : null,
        label: node.getAttribute ? node.getAttribute('aria-label') : null
      };
    });
  }

  function restoreOwnedPresentation(entries) {
    if (!entries) return;
    entries.forEach(function (entry) {
      if (!entry.node) return;
      entry.node.hidden = entry.hidden;
      if (entry.node.removeAttribute) {
        if (entry.labelledby == null) entry.node.removeAttribute('aria-labelledby');
        else entry.node.setAttribute('aria-labelledby', entry.labelledby);
      }
      if (entry.node.matches && entry.node.matches('dialog')) return;
      if (entry.open !== null && 'open' in entry.node) entry.node.open = entry.open;
    });
  }

  function placeNode(node, parent, next) {
    if (!node || !parent) return;
    var reference = next && next.parentNode === parent ? next : null;
    if (node.parentNode !== parent || node.nextSibling !== reference) parent.insertBefore(node, reference);
  }

  function prepareInspector(controller) {
    var prepared = { supported: false, originals: snapshotInspectorOwned(controller.root), added: [], generation: 0, modalityFailed: false, shell: null };
    var shell = inspectorShell(controller);
    if (!shell || typeof shell.showModal !== 'function' || typeof shell.close !== 'function') return prepared;
    prepared.supported = true;
    prepared.shell = shell;
    return prepared;
  }

  function paintInspectorFallbacks(controller, state) {
    if (!controller.inspectorHost) return;
    owned(controller.root, '[data-im-inspector-origin]').forEach(function (details) {
      if (controller.inspector && controller.inspector.placement.originDetails === details) {
        details.hidden = true;
        return;
      }
      var article = details.querySelector('[data-im-inspector-payload]');
      if (!article || !articleOwned(controller, article)) {
        details.hidden = false;
        return;
      }
      if (!articleMatchesTuple(article, state)) {
        details.hidden = true;
        return;
      }
      var disclosed = articleSource(article);
      if (disclosed !== null && disclosed !== state.source_reference) {
        details.hidden = true;
        return;
      }
      details.hidden = false;
    });
  }

  function applyInspectorLanguage(controller) {
    var shell = controller.inspectorHost && controller.inspectorHost.shell;
    if (!shell) return;
    var zh = normalLanguage(controller.root) === 'zh';
    var label = shell.getAttribute(zh ? 'data-im-label-zh' : 'data-im-label-en');
    if (label) shell.setAttribute('aria-label', label);
  }

  function ensureEnhancedControls(controller, article) {
    var host = controller.inspectorHost;
    var nav = article.querySelector('[data-im-inspector-enhancement]');
    if (!nav || !articleOwned(controller, nav)) return nav;
    nav.hidden = false;
    if (!nav.querySelector('[data-im-inspector-action="evidence"]')) {
      var evidence = makeInspectorButton(article.ownerDocument, 'evidence', 'Evidence', '依据');
      nav.appendChild(evidence);
      host.added.push(evidence);
    }
    if (!nav.querySelector('[data-im-inspector-action="deeper"]')) {
      var deeper = makeInspectorButton(article.ownerDocument, 'deeper', 'Go deeper', '深入研究');
      nav.appendChild(deeper);
      host.added.push(deeper);
    }
    return nav;
  }

  function applyInspectorMode(controller, mode, field, options) {
    var attachment = controller.inspector;
    if (!attachment) return false;
    var previousMode = attachment.mode;
    var previousField = attachment.field;
    var article = attachment.placement.article;
    var previousFocus = article.ownerDocument.activeElement;
    var snapshot = snapshotInspectorSubtree(article, attachment.placement.shell, attachment.placement.originDetails);
    var host = controller.inspectorHost;
    var addedCount = host && host.added ? host.added.length : 0;
    try {
      var read = article.querySelector('[data-im-inspector-page="read"]');
      var ledger = article.querySelector('[data-im-inspector-ledger]');
      var deeper = article.querySelector('[data-im-inspector-page="deeper"]');
      var unavailable = article.querySelector('[data-im-inspector-deeper-unavailable]');
      if (mode === 'deeper' && !deeper && !unavailable) {
        unavailable = article.ownerDocument.createElement('p');
        unavailable.setAttribute('data-im-inspector-deeper-unavailable', '');
        appendWords(unavailable, 'No deeper destinations are available for this market.', '此市场暂无深入研究目标。');
        article.appendChild(unavailable);
        if (host && host.added) host.added.push(unavailable);
      }
      if (read) read.hidden = mode !== 'read';
      if (ledger) {
        ledger.hidden = mode !== 'ledger' && mode !== 'field';
        ledger.open = mode === 'ledger' || mode === 'field';
      }
      Array.from(article.querySelectorAll('[data-im-inspector-field]')).forEach(function (node) {
        var id = node.getAttribute('data-im-inspector-field');
        if (mode === 'field') {
          node.hidden = id !== field;
          node.open = id === field;
        } else if (mode === 'ledger') {
          node.hidden = false;
          node.open = false;
        } else {
          node.hidden = true;
          node.open = false;
        }
      });
      if (deeper) deeper.hidden = mode !== 'deeper';
      unavailable = article.querySelector('[data-im-inspector-deeper-unavailable]');
      if (unavailable) unavailable.hidden = !(mode === 'deeper' && !deeper);
      attachment.mode = mode;
      attachment.field = mode === 'field' ? field : null;
      var heading = inspectorHeading(article, mode, field);
      var shell = attachment.placement.shell;
      if (heading && heading.id) shell.setAttribute('aria-labelledby', heading.id);
      else shell.removeAttribute('aria-labelledby');
      applyInspectorLanguage(controller);
      if (!options || options.focus !== false) {
        var focusTarget = options && options.focusNode ? options.focusNode : heading;
        if (focusTarget && typeof focusTarget.focus === 'function') focusTarget.focus();
      }
      return true;
    } catch (_) {
      attachment.mode = previousMode;
      attachment.field = previousField;
      restoreOwnedPresentation(snapshot);
      if (host && host.added) {
        while (host.added.length > addedCount) {
          var extra = host.added.pop();
          if (extra && extra.parentNode) extra.parentNode.removeChild(extra);
        }
      }
      if (previousFocus && typeof previousFocus.focus === 'function') {
        try { previousFocus.focus(); } catch (error) {}
      }
      return false;
    }
  }

  function captureLiveInspector(controller) {
    var attachment = controller.inspector;
    if (!attachment) return null;
    var article = attachment.placement.article;
    return {
      market: attachment.market,
      mode: attachment.mode,
      field: attachment.field,
      origin: attachment.origin,
      scroll: attachment.scroll,
      focus: attachment.focus,
      generation: attachment.generation,
      contextFingerprint: attachment.contextFingerprint,
      fieldTrigger: attachment.fieldTrigger,
      readControl: attachment.readControl,
      ownedSnapshot: attachment.ownedSnapshot,
      placement: {
        article: article,
        originDetails: attachment.placement.originDetails,
        originParent: attachment.placement.originParent,
        originNext: attachment.placement.originNext,
        originOpen: attachment.placement.originOpen,
        shell: attachment.placement.shell,
        dialogParent: article.parentNode,
        dialogNext: article.nextSibling
      },
      modal: dialogIsModal(attachment.placement.shell),
      focusNow: article.ownerDocument.activeElement
    };
  }

  function dialogIsModal(shell) {
    return !!(shell && (shell.open || (typeof shell.matches === 'function' && shell.matches(':modal'))));
  }

  function closeInspectorDialog(controller, shell) {
    if (!shell) return;
    controller.inspectorSilent = true;
    try {
      if (dialogIsModal(shell) && typeof shell.close === 'function') shell.close();
    } catch (_) {}
    controller.inspectorSilent = false;
  }

  function visuallyCloseInspector(controller, options) {
    var attachment = controller.inspector;
    if (!attachment) return;
    var placement = attachment.placement;
    var article = placement.article;
    closeInspectorDialog(controller, placement.shell);
    restoreOwnedPresentation(attachment.ownedSnapshot);
    var nav = article.querySelector('[data-im-inspector-enhancement]');
    if (nav) nav.hidden = true;
    placeNode(article, placement.originParent, placement.originNext);
    if (placement.originDetails) {
      placement.originDetails.open = !!placement.originOpen;
      placement.originDetails.hidden = false;
    }
    if (options && options.release) controller.inspector = null;
  }

  function releaseInspectorToOrigin(controller, snap) {
    if (!snap || !snap.placement) {
      controller.inspector = null;
      return;
    }
    if (controller.inspector) visuallyCloseInspector(controller, { release: true });
    else {
      var articleHome = snap.placement.article;
      closeInspectorDialog(controller, snap.placement.shell);
      restoreOwnedPresentation(snap.ownedSnapshot);
      if (articleHome) {
        var homeNav = articleHome.querySelector('[data-im-inspector-enhancement]');
        if (homeNav) homeNav.hidden = true;
        placeNode(articleHome, snap.placement.originParent, snap.placement.originNext);
      }
    }
    var originDetails = snap.placement.originDetails;
    if (originDetails) {
      originDetails.hidden = false;
      originDetails.open = true;
    }
    controller.inspector = null;
    if (controller.state) paintInspectorFallbacks(controller, controller.state);
    var focusNode = snap.focusNow;
    if (!nodeUsable(controller, focusNode)) {
      focusNode = originDetails && originDetails.querySelector('[data-im-inspector-trigger]');
    }
    if (!nodeUsable(controller, focusNode) && snap.placement.article) {
      focusNode = inspectorHeading(snap.placement.article, 'read', null);
    }
    if (focusNode && typeof focusNode.focus === 'function') {
      try { focusNode.focus(); } catch (_) {}
    }
  }

  function rehydrateInspector(controller, snap) {
    if (!snap) return false;
    try {
      var article = snap.placement.article;
      var shell = snap.placement.shell;
      placeNode(article, snap.placement.dialogParent, snap.placement.dialogNext);
      restoreOwnedPresentation(snap.ownedSnapshot);
      if (article) {
        var nav = article.querySelector('[data-im-inspector-enhancement]');
        if (nav) nav.hidden = false;
      }
      controller.inspector = {
        market: snap.market,
        mode: snap.mode,
        field: snap.field,
        origin: snap.origin,
        scroll: snap.scroll,
        focus: snap.focus,
        generation: snap.generation,
        contextFingerprint: snap.contextFingerprint,
        placement: {
          article: article,
          originDetails: snap.placement.originDetails,
          originParent: snap.placement.originParent,
          originNext: snap.placement.originNext,
          originOpen: snap.placement.originOpen,
          shell: snap.placement.shell
        },
        ownedSnapshot: snap.ownedSnapshot,
        fieldTrigger: snap.fieldTrigger,
        readControl: snap.readControl
      };
      var nativeOk = !snap.modal;
      if (snap.modal) {
        nativeOk = false;
        if (shell && typeof shell.showModal === 'function') {
          try {
            if (!dialogIsModal(shell)) shell.showModal();
            nativeOk = dialogIsModal(shell);
          } catch (_) {
            nativeOk = false;
          }
        }
      }
      // A native platform failure cannot restore modal; do not swallow mode false.
      if (!nativeOk || !applyInspectorMode(controller, snap.mode, snap.field, { focus: false })) {
        releaseInspectorToOrigin(controller, snap);
        return false;
      }
      if (controller.state) paintInspectorFallbacks(controller, controller.state);
      if (snap.focusNow && typeof snap.focusNow.focus === 'function' && snap.focusNow.isConnected) {
        try { snap.focusNow.focus(); } catch (_) {}
      }
      return true;
    } catch (_) {
      try { releaseInspectorToOrigin(controller, snap); } catch (error) {}
      return false;
    }
  }

  function closeInspector(controller, options) {
    if (!controller.live && !(options && options.destroying)) return destroyedResult();
    var attachment = controller.inspector;
    if (!attachment) return inspectorResult(controller, true, []);
    var restoreScroll = !options || options.restoreScroll !== false;
    var restoreFocus = !options || options.restoreFocus !== false;
    var contextUnchanged = controller.state && attachment.contextFingerprint === inspectorFingerprint(controller.state);
    var originNode = attachment.origin && attachment.origin.node;
    var originFingerprint = attachment.origin && attachment.origin.contextFingerprint;
    var scroll = attachment.scroll;
    visuallyCloseInspector(controller, { release: true });
    if (controller.state) paintInspectorFallbacks(controller, controller.state);
    if (restoreScroll && contextUnchanged) restoreScrollOffsets(controller, scroll);
    if (restoreFocus) {
      var originValid = !!(originNode && originFingerprint === inspectorFingerprint(controller.state) && nodeUsable(controller, originNode));
      var target = originValid ? originNode : owned(controller.root, '[data-im-heading]')[0];
      if (target && typeof target.focus === 'function') {
        try { target.focus(); } catch (_) {}
      }
    }
    return inspectorResult(controller, true, []);
  }

  function inspectorBack(controller) {
    if (!controller.live) return destroyedResult();
    var attachment = controller.inspector;
    if (!attachment) return inspectorResult(controller, true, []);
    var mode = attachment.mode;
    if (mode === 'field') {
      var trigger = attachment.fieldTrigger;
      if (!applyInspectorMode(controller, 'ledger', null, { focusNode: nodeUsable(controller, trigger) ? trigger : null })) {
        return inspectorResult(controller, false, [{ code: 'UI_UPDATE_FAILED', field: 'inspector' }]);
      }
      return inspectorResult(controller, true, []);
    }
    if (mode === 'ledger' || mode === 'deeper') {
      var readControl = attachment.readControl;
      var heading = inspectorHeading(attachment.placement.article, 'read', null);
      if (!applyInspectorMode(controller, 'read', null, { focusNode: nodeUsable(controller, readControl) ? readControl : heading })) {
        return inspectorResult(controller, false, [{ code: 'UI_UPDATE_FAILED', field: 'inspector' }]);
      }
      return inspectorResult(controller, true, []);
    }
    return closeInspector(controller, {});
  }

  function inspectorEvidence(controller, control) {
    var attachment = controller.inspector;
    if (!attachment) return inspectorResult(controller, false, [{ code: 'NO_MATCHING_PANEL', field: 'inspector' }]);
    if (attachment.mode !== 'read' && attachment.mode !== 'deeper') return inspectorResult(controller, true, []);
    attachment.readControl = control || attachment.readControl;
    if (!applyInspectorMode(controller, 'ledger', null, {})) {
      return inspectorResult(controller, false, [{ code: 'UI_UPDATE_FAILED', field: 'inspector' }]);
    }
    return inspectorResult(controller, true, []);
  }

  function inspectorDeeper(controller, control) {
    var attachment = controller.inspector;
    if (!attachment) return inspectorResult(controller, false, [{ code: 'NO_MATCHING_PANEL', field: 'inspector' }]);
    if (attachment.mode !== 'read' && attachment.mode !== 'ledger') return inspectorResult(controller, true, []);
    attachment.readControl = control || attachment.readControl;
    if (!applyInspectorMode(controller, 'deeper', null, {})) {
      return inspectorResult(controller, false, [{ code: 'UI_UPDATE_FAILED', field: 'inspector' }]);
    }
    return inspectorResult(controller, true, []);
  }

  function inspectorField(controller, field, control) {
    var attachment = controller.inspector;
    if (!attachment || attachment.mode !== 'ledger') {
      return inspectorResult(controller, false, [{ code: 'NO_MATCHING_PANEL', field: 'inspector' }]);
    }
    if (INSPECTOR_FIELDS.indexOf(field) === -1) return inspectorResult(controller, false, [{ code: 'INVALID_ACTION', field: 'field' }]);
    var node = attachment.placement.article.querySelector('[data-im-inspector-field="' + field + '"]');
    if (!node) return inspectorResult(controller, false, [{ code: 'NO_MATCHING_PANEL', field: 'field' }]);
    attachment.fieldTrigger = control || node.querySelector('[data-im-inspector-field-trigger]');
    if (!applyInspectorMode(controller, 'field', field, {})) {
      return inspectorResult(controller, false, [{ code: 'UI_UPDATE_FAILED', field: 'inspector' }]);
    }
    return inspectorResult(controller, true, []);
  }

  function openInspector(controller, request) {
    if (!controller.live) return destroyedResult();
    var copied = ownDataCopy(request, ['market_id', 'expected_source']);
    if (!copied) return inspectorResult(controller, false, [{ code: 'INVALID_ACTION', field: 'inspector' }]);
    if (typeof copied.market_id !== 'string' || copied.market_id.length === 0) {
      return inspectorResult(controller, false, [{ code: 'INVALID_ACTION', field: 'market_id' }]);
    }
    var expected = normalizeSource(copied.expected_source);
    if (expected === undefined && copied.expected_source !== null) {
      return inspectorResult(controller, false, [{ code: 'INVALID_ACTION', field: 'expected_source' }]);
    }
    var currentSource = normalizeSource(controller.state.source_reference);
    if (expected !== currentSource) return inspectorResult(controller, false, [{ code: 'STALE_SOURCE', field: 'expected_source' }]);
    var host = controller.inspectorHost;
    var shell = host && host.shell ? host.shell : inspectorShell(controller);
    if (!host || !host.supported || host.modalityFailed || !shell) {
      return inspectorResult(controller, false, [{ code: 'NO_MATCHING_PANEL', field: 'inspector' }]);
    }
    var overviewPanels = activeOverviewPanels(controller);
    if (overviewPanels.length > 1) return inspectorResult(controller, false, [{ code: 'AMBIGUOUS_PANEL', field: 'inspector' }]);
    if (overviewPanels.length !== 1) return inspectorResult(controller, false, [{ code: 'NO_MATCHING_PANEL', field: 'inspector' }]);
    var contextId = overviewContextId(overviewPanels[0]);
    if (!contextId) return inspectorResult(controller, false, [{ code: 'NO_MATCHING_PANEL', field: 'inspector' }]);
    var matches = matchingInspectorArticles(controller, copied.market_id, expected).filter(function (article) {
      return article.getAttribute('data-im-inspector-context') === contextId;
    });
    if (matches.length > 1) return inspectorResult(controller, false, [{ code: 'AMBIGUOUS_PANEL', field: 'inspector' }]);
    if (matches.length !== 1) return inspectorResult(controller, false, [{ code: 'NO_MATCHING_PANEL', field: 'inspector' }]);
    var article = matches[0];
    if (controller.inspector && controller.inspector.placement.article === article && dialogIsModal(shell)) {
      if (!applyInspectorMode(controller, 'read', null, {})) {
        return inspectorResult(controller, false, [{ code: 'UI_UPDATE_FAILED', field: 'inspector' }]);
      }
      return inspectorResult(controller, true, []);
    }
    if (controller.inspector) closeInspector(controller, { restoreScroll: true, restoreFocus: false });
    var originDetails = article.closest('[data-im-inspector-origin]');
    var trigger = controller.pendingInspectorTrigger ||
      (originDetails && originDetails.querySelector('[data-im-inspector-trigger]')) || article;
    var focusNow = article.ownerDocument.activeElement;
    var scroll = captureScrollOffsets(controller, originDetails || article);
    var originOpen = originDetails ? !!originDetails.open : false;
    var originParent = article.parentNode;
    var originNext = article.nextSibling;
    var fingerprint = inspectorFingerprint(controller.state);
    ensureEnhancedControls(controller, article);
    var ownedBefore = snapshotInspectorSubtree(article, shell, originDetails);
    placeNode(article, shell, null);
    if (originDetails) {
      originDetails.open = false;
      originDetails.hidden = true;
    }
    controller.inspector = {
      market: copied.market_id,
      mode: 'read',
      field: null,
      origin: { node: trigger, contextFingerprint: fingerprint },
      scroll: scroll,
      focus: focusNow,
      generation: (host.generation += 1),
      contextFingerprint: fingerprint,
      placement: {
        article: article,
        originDetails: originDetails,
        originParent: originParent,
        originNext: originNext,
        originOpen: originOpen,
        shell: shell
      },
      ownedSnapshot: ownedBefore,
      fieldTrigger: null,
      readControl: null
    };
    var shown = false;
    try {
      if (!applyInspectorMode(controller, 'read', null, { focus: false })) {
        placeNode(article, originParent, originNext);
        restoreOwnedPresentation(ownedBefore);
        if (originDetails) {
          originDetails.open = originOpen;
          originDetails.hidden = false;
        }
        var failedNav = article.querySelector('[data-im-inspector-enhancement]');
        if (failedNav) failedNav.hidden = true;
        controller.inspector = null;
        paintInspectorFallbacks(controller, controller.state);
        return inspectorResult(controller, false, [{ code: 'UI_UPDATE_FAILED', field: 'inspector' }]);
      }
      try {
        shell.showModal();
        shown = true;
      } catch (showError) {
        placeNode(article, originParent, originNext);
        restoreOwnedPresentation(ownedBefore);
        if (originDetails) {
          originDetails.open = originOpen;
          originDetails.hidden = false;
        }
        var modalNav = article.querySelector('[data-im-inspector-enhancement]');
        if (modalNav) modalNav.hidden = true;
        controller.inspector = null;
        host.modalityFailed = true;
        paintInspectorFallbacks(controller, controller.state);
        return inspectorResult(controller, false, [{ code: 'UI_UPDATE_FAILED', field: 'inspector' }]);
      }
      var heading = inspectorHeading(article, 'read', null);
      if (heading && heading.focus) heading.focus();
      paintInspectorFallbacks(controller, controller.state);
      return inspectorResult(controller, true, []);
    } catch (_) {
      if (shown) {
        closeInspector(controller, { restoreScroll: true, restoreFocus: true });
      } else {
        placeNode(article, originParent, originNext);
        restoreOwnedPresentation(ownedBefore);
        if (originDetails) {
          originDetails.open = originOpen;
          originDetails.hidden = false;
        }
        var nav = article.querySelector('[data-im-inspector-enhancement]');
        if (nav) nav.hidden = true;
        controller.inspector = null;
        paintInspectorFallbacks(controller, controller.state);
        restoreScrollOffsets(controller, scroll);
        if (focusNow && typeof focusNow.focus === 'function') {
          try { focusNow.focus(); } catch (error) {}
        }
      }
      return inspectorResult(controller, false, [{ code: 'UI_UPDATE_FAILED', field: 'inspector' }]);
    }
  }

  function teardownInspector(controller) {
    if (controller.inspector) closeInspector(controller, { restoreScroll: false, restoreFocus: false, destroying: true });
    var host = controller.inspectorHost;
    if (!host) return;
    if (host.shell && controller.onInspectorCancel) {
      host.shell.removeEventListener('cancel', controller.onInspectorCancel, false);
    }
    if (host.shell && controller.onInspectorKeydown) {
      host.shell.removeEventListener('keydown', controller.onInspectorKeydown, true);
    }
    if (host.shell && controller.onInspectorClose) {
      host.shell.removeEventListener('close', controller.onInspectorClose, false);
    }
    host.added.slice().forEach(function (node) {
      if (node && node.parentNode) node.parentNode.removeChild(node);
    });
    host.added = [];
    host.originals.forEach(function (entry) {
      var node = entry.node;
      if (!node) return;
      if (entry.parent) placeNode(node, entry.parent, entry.next);
      entry.attrs.forEach(function (attribute) {
        if (attribute[1] === null) node.removeAttribute(attribute[0]);
        else node.setAttribute(attribute[0], attribute[1]);
      });
      if (entry.open !== null && 'open' in node && !(node.matches && node.matches('dialog'))) node.open = entry.open;
    });
    controller.inspector = null;
  }

  function inspectorEvent(controller, event) {
    if (!controller.live || !controller.inspectorHost) return false;
    var target = event.target;
    if (!target || !target.closest) return false;
    if (target.closest('[data-im-workspace]') !== controller.root) return false;
    if (event.type !== 'click') return false;
    var deeperLink = target.closest('a');
    if (deeperLink && controller.inspector && articleOwned(controller, deeperLink) &&
        deeperLink.closest('[data-im-inspector-page="deeper"]')) {
      closeInspector(controller, { restoreScroll: false, restoreFocus: false });
      return false;
    }
    var openBtn = target.closest('button[data-im-inspector-open]');
    if (openBtn && articleOwned(controller, openBtn) && !openBtn.disabled) {
      event.preventDefault();
      controller.pendingInspectorTrigger = openBtn;
      var sourceAttr = openBtn.hasAttribute('data-source') ? openBtn.getAttribute('data-source') : null;
      openInspector(controller, { market_id: openBtn.getAttribute('data-market-id'), expected_source: normalizeSource(sourceAttr) });
      controller.pendingInspectorTrigger = null;
      return true;
    }
    var trigger = target.closest('[data-im-inspector-trigger]');
    if (trigger && articleOwned(controller, trigger) && controller.inspectorHost.supported && !controller.inspectorHost.modalityFailed) {
      var origin = trigger.closest('[data-im-inspector-origin]');
      var article = origin && origin.querySelector('[data-im-inspector-payload]');
      if (article && articleMatchesRequest(controller, article, article.getAttribute('data-market-id'), normalizeSource(controller.state.source_reference))) {
        event.preventDefault();
        controller.pendingInspectorTrigger = trigger;
        openInspector(controller, { market_id: article.getAttribute('data-market-id'), expected_source: articleSource(article) });
        controller.pendingInspectorTrigger = null;
        return true;
      }
    }
    if (!controller.inspector) return false;
    var actionBtn = target.closest('[data-im-inspector-action]');
    if (actionBtn && articleOwned(controller, actionBtn)) {
      var action = actionBtn.getAttribute('data-im-inspector-action');
      event.preventDefault();
      if (action === 'close') closeInspector(controller, {});
      else if (action === 'back') inspectorBack(controller);
      else if (action === 'evidence') inspectorEvidence(controller, actionBtn);
      else if (action === 'deeper') inspectorDeeper(controller, actionBtn);
      return true;
    }
    var ledgerTrigger = target.closest('[data-im-inspector-ledger-trigger]');
    if (ledgerTrigger && articleOwned(controller, ledgerTrigger)) {
      event.preventDefault();
      if (controller.inspector.mode === 'read' || controller.inspector.mode === 'deeper') inspectorEvidence(controller, ledgerTrigger);
      return true;
    }
    var fieldTrigger = target.closest('[data-im-inspector-field-trigger]');
    if (fieldTrigger && articleOwned(controller, fieldTrigger)) {
      event.preventDefault();
      if (controller.inspector.mode === 'ledger') {
        var fieldNode = fieldTrigger.closest('[data-im-inspector-field]');
        inspectorField(controller, fieldNode && fieldNode.getAttribute('data-im-inspector-field'), fieldTrigger);
      }
      return true;
    }
    return false;
  }

  function inspectorCancel(controller, event) {
    if (controller.inspectorSilent) return;
    if (event && typeof event.preventDefault === 'function') event.preventDefault();
    if (!controller.live || !controller.inspector) return;
    inspectorBack(controller);
  }

  function inspectorNativeClose(controller, event) {
    if (controller.inspectorSilent) return;
    if (!controller.live) return;
    var host = controller.inspectorHost;
    var shell = host && host.shell;
    if (!shell) return;
    if (event && event.target && event.target !== shell) return;
    if (dialogIsModal(shell)) return;
    var attachment = controller.inspector;
    if (!attachment || attachment.placement.shell !== shell) return;
    closeInspector(controller, {});
  }

  function inspectorEscapeKey(controller, event) {
    if (controller.inspectorSilent || !controller.inspector) return;
    if (!event || (event.key !== 'Escape' && event.key !== 'Esc')) return;
    if (typeof event.preventDefault === 'function') event.preventDefault();
    inspectorBack(controller);
  }

  // Compare consumes only a server-ordered, identity-free slot catalogue.
  // Financial text and endpoint windows stay on their original DOM nodes.
  function comparePlan(controller, panel, state) {
    if (!panel || !panel.hasAttribute('data-im-compare-panel') || panel.getAttribute('data-return-basis') !== 'price') return null;
    var all = function (selector) { return owned(controller.root, selector).filter(function (node) { return node.closest('[data-im-panel]') === panel; }); };
    var one = function (selector) { var nodes = all(selector); return nodes.length === 1 ? nodes[0] : null; };
    var script = one('script[data-im-compare-catalogue]'), body = one('tbody[data-im-compare-rows]');
    var status = one('[data-im-compare-status]'), controls = one('[data-im-compare-controls]'), picker = one('select[data-im-compare-pin]');
    if (!script || script.type !== 'application/json' || script.textContent.length > 65536 || !body || !status || !controls || !picker || !controls.contains(picker)) return null;
    var data;
    try { data = JSON.parse(script.textContent); } catch (_) { return null; }
    var keys = function (value, expected) { return value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === expected.length && expected.every(function (k) { return Object.prototype.hasOwnProperty.call(value,k); }); };
    var count = controller.config.markets.length;
    if (!keys(data,['schema','slot_order','cohorts']) || data.schema !== 'intl-compare-catalogue.v1' ||
        !Array.isArray(data.slot_order) || data.slot_order.length !== count || data.slot_order.some(function (slot,i) { return slot !== i; }) || !Array.isArray(data.cohorts)) return null;
    var slotNumber = function (text) { return typeof text === 'string' && /^(0|[1-9][0-9]*)$/.test(text) && Number(text) < count ? Number(text) : null; };
    var rows = new Map(), membership = new Map(), groups = new Map();
    var rowNodes = all('tr[data-im-compare-slot]');
    if (rowNodes.length !== count) return null;
    for (var row of rowNodes) {
      var slot = slotNumber(row.getAttribute('data-im-compare-slot'));
      if (slot === null || rows.has(slot) || row.parentNode !== body) return null;
      rows.set(slot,row);
    }
    for (var cohort of data.cohorts) {
      if (!keys(cohort,['id','order_slots']) || typeof cohort.id !== 'string' || !/^c(0|[1-9][0-9]*)$/.test(cohort.id) || groups.has(cohort.id) || !Array.isArray(cohort.order_slots) || !cohort.order_slots.length) return null;
      for (var member of cohort.order_slots) {
        if (!Number.isInteger(member) || !rows.has(member) || membership.has(member)) return null;
        membership.set(member,cohort.id);
      }
      groups.set(cohort.id,cohort.order_slots);
    }
    if (data.cohorts.length && !panel.getAttribute('data-source')) return null;
    for (var pair of rows) {
      if ((pair[1].getAttribute('data-im-compare-cohort-id') || null) !== (membership.get(pair[0]) || null)) return null;
    }
    var windows = all('[data-im-compare-cohort]'), windowIds = new Set();
    for (var windowNode of windows) {
      var id = windowNode.getAttribute('data-im-compare-cohort');
      if (!groups.has(id) || windowIds.has(id)) return null;
      windowIds.add(id);
    }
    if (windows.length !== groups.size) return null;
    var removes = all('button[data-im-compare-remove]'), removeSlots = new Set();
    for (var button of removes) {
      var removeSlot = slotNumber(button.getAttribute('data-im-compare-remove'));
      if (removeSlot === null || removeSlots.has(removeSlot) || button.closest('tr[data-im-compare-slot]') !== rows.get(removeSlot)) return null;
      removeSlots.add(removeSlot);
    }
    if (removes.length !== count) return null;
    var options = Array.from(picker.options), optionSlots = new Set(), empty = 0;
    for (var option of options) {
      if (option.parentNode !== picker || !option.hasAttribute('data-im-label-en') || !option.hasAttribute('data-im-label-zh')) return null;
      if (option.value === '') { empty++; continue; }
      var optionSlot = slotNumber(option.value);
      if (optionSlot === null || optionSlots.has(optionSlot) || !rows.get(optionSlot).hasAttribute('data-im-compare-cohort-id')) return null;
      optionSlots.add(optionSlot);
    }
    if (empty !== 1 || optionSlots.size !== rowNodes.filter(function (node) { return node.hasAttribute('data-im-compare-cohort-id'); }).length) return null;
    var selected = state.compare_markets.map(function (market) { return controller.config.markets.indexOf(market); });
    if (selected.some(function (slot) { return !rows.has(slot); })) return null;
    var verdict = 'incomplete', reason = 'selection_incomplete', order = selected.length ? selected.slice() : data.slot_order.slice();
    if (selected.length >= 2) {
      var groupId = membership.get(selected[0]);
      if (selected.some(function (slot) { return !membership.has(slot); })) reason = 'selection_unqualified';
      else if (selected.some(function (slot) { return membership.get(slot) !== groupId; })) reason = 'unequal_windows';
      else { verdict = 'comparable'; reason = ''; order = groups.get(groupId).filter(function (slot) { return selected.includes(slot); }); }
      if (reason) verdict = 'incomparable';
    }
    return {panel:panel,body:body,rows:rows,status:status,controls:controls,picker:picker,options:options,removes:removes,windows:windows,membership:membership,selected:selected,order:order,verdict:verdict,reason:reason};
  }

  function compareFocus(root) {
    var node = root.ownerDocument.activeElement;
    return node && node.closest && node.closest('[data-im-workspace]') === root &&
      node.closest('[data-im-compare-slot]') ? node : null;
  }

  function restoreCompareFocus(root, node) {
    if (node && node.isConnected && node.closest('[data-im-workspace]') === root &&
        !node.closest('[hidden]') && !node.matches(':disabled') && node.getClientRects().length &&
        root.ownerDocument.activeElement !== node) node.focus({preventScroll:true});
  }

  function paintCompare(controller, plan) {
    if (!plan) return;
    var focused = compareFocus(controller.root);
    var zh = normalLanguage(controller.root) === 'zh';
    var messages = {
      selection_incomplete: ['Select two to four markets to compare matching windows.', '选择两到四个市场，以比较相同的计算区间。'],
      selection_unqualified: ['Some selected markets lack qualified evidence. All selections are retained.', '部分所选市场缺少符合条件的依据。全部选择已保留。'],
      unequal_windows: ['Selected markets have different calculation windows. All selections are retained.', '所选市场的计算区间不同。全部选择已保留。'],
      comparable: ['Matching calculation windows · ordered by return.', '相同计算区间 · 按回报排序。']
    };
    plan.panel.setAttribute('data-im-compare-state',plan.verdict);
    plan.panel.setAttribute('data-im-compare-reason',plan.reason);
    plan.status.textContent = messages[plan.reason || 'comparable'][zh ? 1 : 0];
    var desired = plan.order.concat(Array.from(plan.rows.keys()).sort(function (a,b) { return a-b; }).filter(function (slot) { return !plan.order.includes(slot); }));
    var current = Array.from(plan.body.children).filter(function (node) { return Array.from(plan.rows.values()).includes(node); });
    if (desired.some(function (slot,i) { return current[i] !== plan.rows.get(slot); })) desired.forEach(function (slot) { plan.body.appendChild(plan.rows.get(slot)); });
    plan.rows.forEach(function (row,slot) { row.hidden = !plan.order.includes(slot); });
    plan.removes.forEach(function (button) { button.hidden = !plan.selected.includes(Number(button.getAttribute('data-im-compare-remove'))); });
    plan.windows.forEach(function (node) { node.hidden = !!plan.selected.length && !plan.selected.some(function (slot) { return plan.membership.get(slot) === node.getAttribute('data-im-compare-cohort'); }); });
    plan.options.forEach(function (option) { option.textContent = option.getAttribute(zh ? 'data-im-label-zh' : 'data-im-label-en'); option.disabled = option.value !== '' && plan.selected.includes(Number(option.value)); });
    plan.picker.value = '';
    plan.controls.hidden = false;
    restoreCompareFocus(controller.root,focused);
  }

  function compareEvent(controller, event) {
    var target = event.target;
    if (!target || !target.closest || target.closest('[data-im-workspace]') !== controller.root) return false;
    var button = event.type === 'click' ? target.closest('button[data-im-compare-remove]') : null;
    var picker = event.type === 'change' && target.matches('select[data-im-compare-pin]') ? target : null;
    if (!button && !picker) return false;
    var matches = panelFor(controller,controller.state), panel = matches.length === 1 ? matches[0] : null;
    var control = button || picker;
    if (!panel || panel.hidden || !panel.contains(control) || control.disabled || control.closest('[hidden]')) return true;
    var plan = comparePlan(controller,panel,controller.state);
    if (!plan || (picker && picker !== plan.picker) || (button && !plan.removes.includes(button))) return true;
    var value = button ? button.getAttribute('data-im-compare-remove') : picker.value;
    if (value === '' || !/^(0|[1-9][0-9]*)$/.test(value)) return true;
    var slot = Number(value);
    if (!plan.rows.has(slot) || (button ? !plan.selected.includes(slot) : !plan.options.some(function (o) { return o.value === value && !o.disabled; }))) return true;
    event.preventDefault();
    var result = dispatch(controller,{type:button ? 'unpin' : 'pin',market_id:controller.config.markets[slot]});
    if (result.ok && button) plan.picker.focus();
    return true;
  }

  function snapshotRoot(root) {
    var selector = '[data-im-heading],[data-im-issues],[data-im-unavailable],[data-im-panel],'+
      '[data-im-action],[data-im-expanded-region],[data-im-expansion-trigger] .l-en,[data-im-expansion-trigger] .l-zh,'+
      '[data-im-library-static],[data-im-library-search],[data-im-library-clear],[data-im-library-status],'+
      '[data-im-library-groups],[data-im-library-group],[data-im-library-results],[data-im-library-empty],[data-im-library-tool],'+
      '[data-im-inspector-origin],[data-im-inspector-payload],[data-im-inspector-enhancement],[data-im-inspector-page],'+
      '[data-im-inspector-ledger],[data-im-inspector-field],[data-im-inspector-shell],[data-im-inspector-deeper-unavailable],'+
      '[data-im-compare-panel],[data-im-compare-slot],[data-im-compare-status],[data-im-compare-cohort],[data-im-compare-controls],[data-im-compare-remove],[data-im-compare-pin],[data-im-compare-pin] option';
    return [root].concat(owned(root, selector)).map(function (node) {
      var attrs = [], text = false, value = false;
      if (node === root) attrs.push('data-im-enhanced');
      if (node.matches('[data-im-heading]')) attrs.push('tabindex');
      if (node.matches('[data-im-library-static]')) attrs.push('data-horizon','data-basis','data-im-library-enhanced');
      if (node.matches('[data-im-library-group]')) attrs.push('data-im-library-active');
      if (node.matches('[data-im-library-groups],[data-im-library-group],[data-im-library-results],[data-im-library-empty],[data-im-library-group-open],[data-im-library-back]')) attrs.push('hidden');
      if (node.matches('[data-im-library-search],[data-im-library-clear]')) attrs.push('disabled');
      if (node.matches('[data-im-library-search]')) { attrs.push('placeholder'); value = true; }
      if (node.matches('[data-im-library-status]')) text = true;
      if (node.matches('[data-im-issues]')) { attrs.push('role'); text = true; }
      if (node.matches('[data-im-unavailable],[data-im-panel],[data-im-expanded-region]')) attrs.push('hidden');
      if (node.matches('button[data-im-action="set_view"]')) attrs.push('disabled','aria-pressed');
      if (node.matches('select[data-im-action]')) value = ['select_market','set_library_group','set_view','set_horizon','set_basis'].includes(node.getAttribute('data-im-action'));
      if (node.matches('[data-im-expansion-trigger]')) attrs.push('hidden','aria-expanded','data-im-expanded');
      if (node.matches('[data-im-expansion-trigger] .l-en,[data-im-expansion-trigger] .l-zh')) text = true;
      if (node.matches('[data-im-inspector-origin],[data-im-inspector-enhancement],[data-im-inspector-page],[data-im-inspector-ledger],[data-im-inspector-field],[data-im-inspector-deeper-unavailable]')) attrs.push('hidden');
      if (node.matches('details[data-im-inspector-origin],details[data-im-inspector-ledger],details[data-im-inspector-field]')) attrs.push('open');
      if (node.matches('[data-im-inspector-shell]')) attrs.push('aria-labelledby','aria-label');
      if (node.matches('[data-im-compare-panel]')) attrs.push('data-im-compare-state','data-im-compare-reason');
      if (node.matches('[data-im-compare-slot],[data-im-compare-cohort],[data-im-compare-controls],[data-im-compare-remove]')) attrs.push('hidden');
      if (node.matches('[data-im-compare-status],[data-im-compare-pin] option')) text = true;
      if (node.matches('[data-im-compare-pin] option')) attrs.push('disabled');
      if (node.matches('[data-im-compare-pin]')) value = true;
      return {node:node, attrs:Array.from(new Set(attrs)).map(function (name) {return [name,node.getAttribute(name)];}),
        value:value ? node.value : null, children:text ? Array.from(node.childNodes) : null,
        compareFocus:node === root ? compareFocus(root) : null,
        parent:node.matches('[data-im-library-tool],[data-im-inspector-payload],[data-im-compare-slot]') ? node.parentNode : null, next:node.nextSibling};
    });
  }

  function rememberNodes(controller, snapshot) {
    snapshot.forEach(function (entry) {
      if (!controller.original.some(function (old) { return old.node === entry.node; })) controller.original.push(entry);
    });
  }

  function restoreRoot(root, snapshot) {
    restoreLibraryRows(snapshot.filter(function (entry) { return !!entry.parent; }));
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
    restoreCompareFocus(root,snapshot[0] && snapshot[0].compareFocus);
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
    var library = controller.library;
    if (library && panelValid(library.panel,controller.config,state.source_reference)) {
      library.panel.setAttribute('data-horizon',state.horizon); library.panel.setAttribute('data-basis',state.currency_basis);
    }
    var panels = panelFor(controller, state);
    var panel = panels.length === 1 ? panels[0] : null;
    var compare = null;
    if (panel && panel.getAttribute('data-view') === 'compare') {
      compare = comparePlan(controller,panel,state);
      if (!compare) panel = null;
    }
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
    paintLibrary(controller,state);
    paintCompare(controller,compare);
    paintInspectorFallbacks(controller,state);
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
    var inspectorSnap = captureLiveInspector(controller);
    var serialized = controller.reducer.serializeQuery(state);
    if (!serialized.ok) return {ok:false, state:previous, issues:serialized.issues, intent:null};
    var shouldPush = !['mount', 'popstate', 'resize'].includes(actionType) && serialized.query !== controller.serializedQuery;
    try {
      var fingerprintChanged = !!(controller.inspector && controller.inspector.contextFingerprint !== inspectorFingerprint(state));
      if (fingerprintChanged) visuallyCloseInspector(controller, { release: true });
      var reported = paint(controller, state, issues);
      if (controller.inspector) applyInspectorMode(controller, controller.inspector.mode, controller.inspector.field, { focus: false });
      if (shouldPush) controller.environment.window.history.pushState(null, '', nextUrl(controller, serialized.query));
      controller.state = state;
      controller.issues = reported;
      controller.serializedQuery = serialized.query;
      return {ok:true, state:state, issues:reported, intent:null};
    } catch (error) {
      restoreRoot(controller.root, snapshot);
      if (inspectorSnap) rehydrateInspector(controller, inspectorSnap);
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
    var hadInspector = !!controller.inspector;
    if (hadInspector) visuallyCloseInspector(controller, { release: true });
    var parsed = controller.reducer.parseQuery(controller.environment.window.location.search);
    var committed = stageAndCommit(controller, parsed.state, parsed.issues, 'popstate', false);
    controller.issues = committed.issues;
    if (hadInspector) {
      var heading = owned(controller.root, '[data-im-heading]')[0];
      if (heading && typeof heading.focus === 'function') {
        try { heading.focus(); } catch (_) {}
      }
    }
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
    if (compareEvent(controller,event)) return;
    if (inspectorEvent(controller,event)) return;
    if (libraryEvent(controller,event)) return;
    var action = actionFromEvent(controller, event);
    if (!action) return;
    event.preventDefault();
    var previousGroup=controller.state.library_group;
    var committed=dispatch(controller, action);
    if (committed.ok && action.type==='set_library_group' && event.type==='click' && controller.library && controller.library.valid) {
      var library=controller.library, target;
      if (action.group_id) {
        var group=library.groups.find(function (node) { return node.getAttribute('data-im-library-group')===action.group_id; });
        target=group && group.querySelector('h3');
      } else target=library.all('[data-im-library-group-open]').find(function (node) { return node.getAttribute('data-im-group')===previousGroup; });
      if (!target || target.closest('[hidden]') || !target.getClientRects().length) target=library.input;
      target.focus();
    }
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
    var inspectorSnap = captureLiveInspector(controller);
    var previousState = controller.state;
    var previousReducer = controller.reducer;
    var previousSerialized = controller.serializedQuery;
    var previousIssues = controller.issues;
    var failed = true;
    try {
      if (controller.inspector) visuallyCloseInspector(controller, { release: true });
      var reported = paint(controller, expanded.state, []);
      controller.reducer = replacement;
      controller.state = expanded.state;
      controller.issues = reported;
      controller.serializedQuery = replacement.serializeQuery(expanded.state).query;
      failed = false;
      return { ok: true, state: expanded.state, issues: reported, intent: { type: 'invalidate_source_bound_context' } };
    } catch (_) {
      return { ok: false, state: previousState, issues: [{ code: 'UI_UPDATE_FAILED', field: 'source_reference' }], intent: null };
    } finally {
      if (failed) {
        controller.reducer = previousReducer;
        controller.state = previousState;
        controller.issues = previousIssues;
        controller.serializedQuery = previousSerialized;
        restoreRoot(controller.root, previousNodes);
        if (inspectorSnap) rehydrateInspector(controller, inspectorSnap);
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
      state: null, issues: [], serializedQuery: '', live: false, original: [], inspector: null
    };
    controller.library = prepareLibrary(root,config);
    controller.inspectorHost = prepareInspector(controller);
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
      controller.onLibraryEvent = function (event) { libraryEvent(controller,event); };
      controller.onPopstate = function () { popstate(controller); };
      controller.onResize = function () { dispatch(controller, {type:'resize'}); };
      controller.onInspectorCancel = function (event) { inspectorCancel(controller, event); };
      controller.onInspectorKeydown = function (event) { inspectorEscapeKey(controller, event); };
      controller.onInspectorClose = function (event) { inspectorNativeClose(controller, event); };
      if (controller.inspectorHost && controller.inspectorHost.shell) {
        controller.inspectorHost.shell.addEventListener('cancel', controller.onInspectorCancel, false);
        controller.inspectorHost.shell.addEventListener('keydown', controller.onInspectorKeydown, true);
        controller.inspectorHost.shell.addEventListener('close', controller.onInspectorClose, false);
      }
      root.addEventListener('click', controller.onClick, false);
      root.addEventListener('change', controller.onChange, false);
      ['input','compositionstart','compositionend','submit'].forEach(function (type) { root.addEventListener(type,controller.onLibraryEvent,false); });
      window.addEventListener('popstate', controller.onPopstate, false);
      window.addEventListener('resize', controller.onResize, false);
      controller.observer = new window.MutationObserver(function () {
        repaintIssues(controller);
        paintLibrary(controller,controller.state);
        var panels = panelFor(controller,controller.state);
        if (panels.length === 1 && !panels[0].hidden) paintCompare(controller,comparePlan(controller,panels[0],controller.state));
        applyInspectorLanguage(controller);
        if (controller.inspector) applyInspectorMode(controller, controller.inspector.mode, controller.inspector.field, { focus: false });
        paintInspectorFallbacks(controller, controller.state);
      });
      controller.observer.observe(window.document.documentElement, { attributes: true, attributeFilter: ['lang'] });
      root.setAttribute('data-im-enhanced', 'true');
      var handle = {
        dispatch: function (action) { return JSON.parse(JSON.stringify(dispatch(controller, action))); },
        getState: function () { return controller.state === null ? null : JSON.parse(JSON.stringify(controller.state)); },
        replaceSource: function (newSource, expectedSource) { return JSON.parse(JSON.stringify(replaceSource(controller, newSource, expectedSource))); },
        openInspector: function (request) { return JSON.parse(JSON.stringify(openInspector(controller, request))); },
        inspectorBack: function () { return JSON.parse(JSON.stringify(inspectorBack(controller))); },
        closeInspector: function () { return JSON.parse(JSON.stringify(closeInspector(controller, {}))); },
        destroy: function () { return destroy(controller); }
      };
      if (!HANDLES) throw new Error('WeakMap is unavailable');
      HANDLES.set(root, handle);
      return handle;
    } catch (error) {
      teardownInspector(controller);
      if (controller.observer) controller.observer.disconnect();
      if (controller.onClick) root.removeEventListener('click', controller.onClick, false);
      if (controller.onChange) root.removeEventListener('change', controller.onChange, false);
      if (controller.onLibraryEvent) ['input','compositionstart','compositionend','submit'].forEach(function (type) { root.removeEventListener(type,controller.onLibraryEvent,false); });
      if (controller.onPopstate) window.removeEventListener('popstate', controller.onPopstate, false);
      if (controller.onResize) window.removeEventListener('resize', controller.onResize, false);
      restoreRoot(root, controller.original);
      throw error;
    }
  }

  function destroy(controller) {
    if (!controller.live) return false;
    controller.live = false;
    teardownInspector(controller);
    controller.state = null;
    controller.reducer = null;
    if (controller.observer) controller.observer.disconnect();
    controller.root.removeEventListener('click', controller.onClick, false);
    controller.root.removeEventListener('change', controller.onChange, false);
    ['input','compositionstart','compositionend','submit'].forEach(function (type) { controller.root.removeEventListener(type,controller.onLibraryEvent,false); });
    controller.environment.window.removeEventListener('popstate', controller.onPopstate, false);
    controller.environment.window.removeEventListener('resize', controller.onResize, false);
    HANDLES.delete(controller.root);
    restoreRoot(controller.root, controller.original);
    return true;
  }

  return { mountIntlWorkspace: mountIntlWorkspace };
});
