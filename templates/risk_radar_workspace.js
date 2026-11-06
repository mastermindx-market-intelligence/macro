/* Risk Radar: progressive presentation of server-owned readings.
 * No network requests, timers, risk calculation, or new state/alert authority.
 * Moving (never cloning) live-hook nodes preserves the existing envelope consumer.
 */
(function () {
  'use strict';
  var dialog = document.getElementById('dlg-risk');
  var template = document.getElementById('risk-radar-workspace-template');
  var config = document.getElementById('risk-radar-workspace-data');
  if (!dialog || !template || !config || dialog.classList.contains('rkw-ready')) return;
  var model;
  try { model = JSON.parse(config.textContent); } catch (_) { return; }
  if (!model || model.schema !== 'mastermind.risk_radar_workspace/v1' ||
      model.scope !== 'US' || !model.horizons) return;
  var body = dialog.querySelector('.mx5-dlg-body');
  var legacyBrief = body && body.querySelector('.riskdlg-brief');
  var layout = template.content.firstElementChild;
  if (!body || !legacyBrief || !layout) return;
  layout = layout.cloneNode(true);
  var one = function (selector, root) { return (root || layout).querySelector(selector); };
  var all = function (selector, root) { return Array.prototype.slice.call((root || layout).querySelectorAll(selector)); };
  var el = function (tag, className) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    return node;
  };
  var words = function (node, en, zh) {
    node.replaceChildren();
    var a = el('span', 'l-en'), b = el('span', 'l-zh');
    a.textContent = en; b.textContent = zh || en;
    node.append(a, b);
    return node;
  };
  var bilingualCopy = function (from, to) {
    if (!from) return to;
    function copy(node, target) {
      if (node.nodeType === 3) { target.appendChild(document.createTextNode(node.textContent)); return; }
      if (node.nodeType !== 1) return;
      var tag = ['B','STRONG','EM','SMALL'].includes(node.tagName) ? node.tagName.toLowerCase() : 'span';
      var safe = el(tag);
      ['l-en','l-zh','rkc-sig-chip'].forEach(function (name) { if (node.classList.contains(name)) safe.classList.add(name); });
      Array.prototype.forEach.call(node.childNodes, function (child) { copy(child, safe); });
      target.appendChild(safe);
    }
    Array.prototype.forEach.call(from.childNodes, function (node) { copy(node, to); });
    return to;
  };
  var probability = function (value) {
    return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1 ? value : null;
  };
  var integer = function (value) {
    return typeof value === 'number' && Number.isFinite(value) && value >= 0 && Number.isInteger(value) ? value : null;
  };
  var percent = function (value) { return value === null ? '—' : Math.round(value * 100) + '%'; };
  var reading = function (day) {
    var input = model.horizons[String(day)] || {};
    var history = input.history && typeof input.history === 'object' ? input.history : {};
    /* Calibration is attached only when its owner marks this horizon matched.
       Thin/absent evidence never becomes a high-confidence label. */
    return { p: probability(input.probability), base: probability(input.baseline),
      matched: history.matched === true && typeof history.thin === 'boolean' &&
        probability(history.displayed_probability) !== null && probability(input.probability) !== null &&
        Math.abs(history.displayed_probability - input.probability) < 1e-12, thin: history.thin === true,
      n: integer(history.n), observed: probability(history.observed_rate) };
  };
  var overview = one('.rkw-overview');
  var inspector = one('.rkw-inspector');
  var content = one('.rkw-inspector-content');
  var title = one('#rkw-inspector-title');
  var summary = one('.rkw-inspector-summary');
  var vault = one('.rkw-vault');
  var contextNav = one('.rkw-context-nav');
  var mobile = window.matchMedia('(max-width:900px)');
  var mobileContext = el('div', 'rkw-mobile-context');
  inspector.insertBefore(mobileContext, contextNav);
  var originals = Array.prototype.slice.call(body.children).filter(function (node) { return node !== config && node !== template; });
  /* Check all mount prerequisites before changing the legacy, readable dialog. */
  body.appendChild(layout);
  originals.forEach(function (node) { vault.appendChild(node); });
  template.remove();
  var move = function (selector, slot) {
    var node = one(selector, legacyBrief);
    if (node) one(slot).appendChild(node);
    return node;
  };
  var state = move('.riskdlg-state', '.rkw-state-slot');
  if (!state) {
    state = words(el('span', 'riskdlg-state'), 'Unavailable', '暂无读数');
    one('.rkw-state-slot').appendChild(state);
  }
  var stateEn = one('.l-en', state);
  if (stateEn && /^(CALM|WATCH|CAUTION|ELEVATED|RISK-OFF)$/.test(stateEn.textContent.trim())) {
    var nativeState = stateEn.textContent.trim().toLowerCase();
    stateEn.textContent = nativeState.charAt(0).toUpperCase() + nativeState.slice(1);
  }
  if (['unknown','none'].includes(legacyBrief.dataset.rkState || 'unknown')) {
    words(state, 'Unavailable', '暂无读数');
  }
  move('.riskdlg-domain', '.rkw-reason-slot');
  var stance = move('.riskdlg-stance', '.rkw-stance-slot');
  if (stance && ['unknown','none'].includes(legacyBrief.dataset.rkState || 'unknown')) {
    words(stance, 'Risk data is incomplete. Review the available sources.', '风险数据不全，请查看已有来源。');
  }
  if (!stance) {
    one('.rkw-stance-slot').appendChild(words(el('div', 'riskdlg-stance'), 'No current stance available.', '暂无当前立场。'));
  }
  move('.riskdlg-authority', '.rkw-authority-slot');
  var score = move('.riskdlg-score', '.rkw-score-slot');
  if (!score) one('.rkw-index').hidden = true;
  dialog.dataset.rkwState = legacyBrief.dataset.rkState || 'unknown';
  var mainTitle = one('.mx5-dlg-title', dialog);
  if (mainTitle) {
    mainTitle.id = mainTitle.id || 'rkw-dialog-title';
    dialog.setAttribute('aria-labelledby', mainTitle.id);
    var scope = words(el('span', 'rkw-scope'), 'US market', '美国市场');
    mainTitle.insertBefore(scope, mainTitle.querySelector('.riskdlg-asof'));
  }
  function labelControl(node, id, en, zh) {
    if (!node) return;
    var label = words(el('span', 'rkw-sr-only'), en, zh);
    label.id = id; node.appendChild(label);
    node.removeAttribute('aria-label'); node.setAttribute('aria-labelledby', id);
  }
  labelControl(one('.rkw-horizons'), 'rkw-horizon-label', 'Probability horizon', '概率期限');
  labelControl(one('.rkw-explore'), 'rkw-explore-label', 'Risk Radar evidence', '风险雷达依据');
  labelControl(contextNav, 'rkw-context-label', 'Evidence sections', '依据分类');
  labelControl(one('.mx5-dlg-close', dialog), 'rkw-close-label', 'Close Risk Radar', '关闭风险雷达');
  var current = null, origin = null, overviewScroll = 0, selectedDay = 21;
  var views = Object.create(null), driverKeys = [];
  var sourceBand = one('#risk-envelope-band', vault);
  var sourceSlot = one('.rkw-internals-slot');
  var sourcesView = el('div', 'rkw-sources');
  if (sourceBand) {
    sourceSlot.appendChild(sourceBand);
    var disclosure = one('.gde-disc', sourceBand);
    if (disclosure) {
      disclosure.open = true;
      sourcesView.appendChild(disclosure);
      var sourceBody = one('.gde-disc-body', disclosure);
      var sourceTable = one('.gde-tblwrap', disclosure);
      if (sourceBody && sourceTable) sourceBody.insertBefore(sourceTable, sourceBody.firstChild);
      var sourceContext = one('#gde-rotation-context', disclosure);
      var provenance = one('.gde-receipt:not(.gde-receipt-live)', disclosure);
      if (sourceBody && (sourceContext || provenance)) {
        var interpretation = el('details', 'rkw-disclosure');
        interpretation.appendChild(words(el('summary'), 'Interpretation & provenance', '解读与溯源'));
        if (sourceContext) interpretation.appendChild(sourceContext);
        if (provenance) interpretation.appendChild(provenance);
        sourceBody.appendChild(interpretation);
      }
      var sourceButton = words(el('button', 'rkw-source-link'), 'Inspect sources', '查看来源');
      sourceButton.type = 'button'; sourceButton.dataset.rkwView = 'sources';
      var sourceArrow = el('span'); sourceArrow.textContent = '↗'; sourceArrow.setAttribute('aria-hidden', 'true');
      sourceButton.appendChild(sourceArrow);
      sourceBand.appendChild(sourceButton);
    }
    var settledOddsEvidence = one('.gde-prob-evidence', sourceBand);
    if (settledOddsEvidence) sourcesView.appendChild(settledOddsEvidence);
  } else {
    sourceSlot.appendChild(words(el('div', 'rkw-empty'), 'Market internals unavailable.', '市场内部数据暂无读数。'));
  }
  var putView = function (key, en, zh, node, description) {
    if (!node) {
      node = words(el('div', 'rkw-empty'), 'No current reading is available for this view.', '此视图暂无当前读数。');
    }
    views[key] = { node: node, en: en, zh: zh, description: description };
    vault.appendChild(node);
  };
  putView('signals', 'All risk signals', '全部风险信号', one('.riskdlg-ladder', dialog),
    ['Each signal uses its own 0–100 index. A higher reading means more pressure, not a probability.', '各信号使用自身的 0–100 指数。读数越高表示压力越大，并非发生概率。']);
  var sentiment = one('.riskdlg-sentiment', dialog);
  putView('sentiment', 'Market sentiment', '市场情绪', sentiment && one('#sentiment-regime', sentiment) ? sentiment : null,
    ['Risk appetite, sentiment and speculative pressure.', '风险偏好、市场情绪与投机压力。']);
  putView('leadership', 'Market leadership', '市场领涨结构', one('.riskdlg-leadership', dialog),
    ['Current leaders and the separately tracked damage cohort.', '当前领涨板块与单独跟踪的受损群组。']);
  putView('volatility', 'Volatility & correlation', '波动率与相关性', one('.riskdlg-vw', dialog),
    ['Volatility, curve shape and cross-market relationships.', '波动率、期限结构与跨市场关系。']);
  var method = one('#riskdlg-method', dialog);
  if (method) method.open = true;
  putView('method', 'Method & track record', '方法与历史记录', method,
    ['How the readings are produced and how past alerts are graded.', '读数的生成方法与历史警报的检验。']);
  putView('sources', 'Sources & freshness', '来源与时效', sourcesView.childNodes.length ? sourcesView : null,
    ['Source dates and coverage remain separate from the risk reading.', '来源日期与覆盖情况独立于风险读数。']);
  var oddsView = el('div', 'rkw-odds-table');
  putView('odds', 'Pullback probability', '回撤概率', oddsView,
    ['Chance of a SPY pullback of at least 5% over the next 5, 10 or 21 trading days. This does not estimate the depth of a future drop.', 'SPY 在未来 5、10 或 21 个交易日内回撤至少 5% 的概率，不代表未来跌幅估计。']);
  var enrichEvidence = function (node) {
    var receipt = one('.lens-receipt', node);
    if (receipt) {
      var fold = el('details', 'rkw-disclosure');
      fold.appendChild(words(el('summary'), 'Method & source', '方法与来源'));
      fold.appendChild(receipt); node.appendChild(fold);
    }
    /* Native secondary narrative remains available on demand. The observation
       and its visual stay at the top; we do not invent actionable copy. */
    var rows = all('.rlx-row', node);
    if (rows.length > 1) {
      var extra = el('details', 'rkw-disclosure');
      extra.appendChild(words(el('summary'), 'More context', '更多背景'));
      rows.slice(1).forEach(function (row) { extra.appendChild(row); });
      node.appendChild(extra);
    }
  };
  var driverNodes = all('.riskdlg-drv-list > .riskdlg-drv', vault);
  var nativeDrivers = driverNodes.slice();
  driverNodes = [['Leading','领先信号'],['Calendar','日历'],['Overseas','境外'],['Correlation','相关性']].map(function (labels) {
    var native = nativeDrivers.find(function (node) {
      var label = one('.rkc-sig-lbl .l-en', node);
      return label && label.textContent.trim() === labels[0];
    });
    if (native) return native;
    var missing = el('div', 'riskdlg-drv');
    missing.dataset.rkwMissing = 'true';
    missing.appendChild(words(el('div', 'rkc-sig-lbl'), labels[0], labels[1]));
    missing.appendChild(words(el('div', 'rkc-sig-state'), 'Reading unavailable', '暂无读数'));
    return missing;
  });
  nativeDrivers.forEach(function (node) { if (!driverNodes.includes(node)) driverNodes.push(node); });
  driverNodes.forEach(function (driver, index) {
    var key = 'driver-' + index;
    var label = one('.rkc-sig-lbl', driver);
    var fact = one('.rkc-sig-state', driver);
    if (!label || !fact) return;
    var card = el('button', 'rkw-driver');
    card.type = 'button'; card.dataset.rkwView = key;
    var categoryEn = one('.l-en', label);
    var isCalendar = categoryEn && categoryEn.textContent.trim() === 'Calendar';
    card.dataset.kind = isCalendar ? 'season' : (driver.dataset.lensKind || '');
    if (driver.dataset.rkwMissing) card.dataset.missing = 'true';
    card.setAttribute('aria-controls', 'rkw-inspector');
    card.setAttribute('aria-expanded', 'false');
    var icon = el('span', 'rkw-driver-icon');
    var nativeIcon = one('.rkc-sig-ico svg', driver);
    if (nativeIcon) icon.appendChild(nativeIcon.cloneNode(true));
    card.appendChild(icon);
    card.appendChild(bilingualCopy(label, el('span', 'rkw-driver-label')));
    card.appendChild(bilingualCopy(fact, el('span', 'rkw-driver-state')));
    all('.rkc-sig-chip', card).forEach(function (chip) { chip.remove(); });
    var arrow = el('span', 'rkw-arrow'); arrow.textContent = '↗'; arrow.setAttribute('aria-hidden', 'true');
    card.appendChild(arrow);
    one('.rkw-driver-grid').appendChild(card);
    var evidence = one('.lens-src', driver);
    if (evidence) {
      evidence.hidden = false;
      evidence.classList.remove('lens-src');
      evidence.classList.add('rkw-evidence-card');
      evidence.dataset.rkwCategory = categoryEn ? categoryEn.textContent.trim().toLowerCase() : '';
      enrichEvidence(evidence);
      if (isCalendar) {
        /* These legacy bar widths were qualitative illustration, not data.
           Keep the native seasonal window and prose without a numeric chart. */
        all('.rlx-bar-track', evidence).forEach(function (track) { track.remove(); });
        all('.rlx-bar-row', evidence).slice(1).forEach(function (row) { row.remove(); });
        var seasonVisual = one('.rlx-viz', evidence);
        if (seasonVisual) seasonVisual.classList.add('rkw-seasonal');
        var sectorChips = one('.rlx-chips', evidence);
        if (sectorChips) {
          var seasonalContext = el('details', 'rkw-disclosure');
          seasonalContext.appendChild(words(el('summary'), 'Historical sector context', '历史板块背景'));
          seasonalContext.appendChild(sectorChips);
          evidence.appendChild(seasonalContext);
        }
      } else {
        all('.rlx-bar-row', evidence).forEach(function (row) {
          row.style.removeProperty('grid-template-columns');
          var fill = one('.rlx-bar-fill', row);
          if (!fill) return;
          var raw = fill.style.getPropertyValue('--rlx-w').trim();
          if (!/^(?:100|[0-9]{1,2})(?:\.[0-9]+)?%$/.test(raw)) return;
          var value = Number(raw.slice(0,-1));
          /* Label the same source-rendered percentile geometry; never classify it. */
          var badge = words(el('span', 'rkw-percentile'), 'Percentile ' + value, '第 ' + value + ' 百分位');
          row.appendChild(badge);
        });
      }
    } else {
      evidence = el('div', 'rkw-evidence-card');
      evidence.appendChild(bilingualCopy(fact, el('p')));
      if (driver.dataset.tipEn) {
        evidence.appendChild(words(el('p', 'rkw-odds-evidence'), driver.dataset.tipEn, driver.dataset.tipZh));
      } else {
        evidence.appendChild(words(el('p', 'rkw-odds-evidence'), 'Detailed evidence is unavailable for this reading.', '此读数暂无详细依据。'));
      }
    }
    var labelEn = one('.l-en', label), labelZh = one('.l-zh', label);
    putView(key, labelEn ? labelEn.textContent : label.textContent,
      labelZh ? labelZh.textContent : label.textContent, evidence);
    views[key].fact = fact; views[key].card = card;
    driverKeys.push(key);
  });
  if (!driverKeys.length) {
    one('.rkw-driver-grid').appendChild(words(el('div', 'rkw-empty'), 'No driver readings are available.', '暂无驱动因素读数。'));
  }
  var overseas = one('#riskdlg-overseas-more', vault);
  /* The existing toggle handler still hydrates its original template on demand. */
  if (overseas) {
    var overseasKey = driverKeys.find(function (key) {
      return views[key].en.trim().toLowerCase() === 'overseas';
    });
    if (overseasKey) views[overseasKey].node.appendChild(overseas);
    else views.sources.node.appendChild(overseas);
  }
  var contextChips = one('.riskdlg-chips', legacyBrief);
  if (contextChips) {
    var modifiers = el('details', 'rkw-disclosure');
    modifiers.appendChild(words(el('summary'), 'Context modifiers', '背景因素'));
    modifiers.appendChild(contextChips);
    views.method.node.appendChild(modifiers);
  }
  /* A concurrently added owner panel must not disappear into the legacy vault.
     Keep unrecognised, visible source blocks ahead of the overview. This is an
     extension point, not permission to calculate or activate future forecasts. */
  originals.forEach(function (node) {
    if (node.parentNode !== vault || ['SCRIPT','STYLE','TEMPLATE'].includes(node.tagName)) return;
    if (node.matches('.riskdlg-brief,.riskdlg-drivers,.riskdlg-sentiment,.rsx-dlg-footer')) return;
    if (Object.keys(views).some(function (key) { return views[key].node === node; })) return;
    one('.rkw-owner-updates').appendChild(node);
  });
  var count = all('.riskdlg-scare', views.signals.node).length;
  one('.rkw-count').textContent = count ? String(count) : '—';
  var contextKeys = ['signals', 'sentiment', 'leadership', 'volatility', 'sources', 'method'];
  contextKeys.forEach(function (key) {
    var label = {signals:['Signals','信号'],sentiment:['Sentiment','情绪'],leadership:['Leaders','领涨'],volatility:['Volatility','波动率'],sources:['Sources','来源'],method:['Method','方法']}[key];
    var button = words(el('button'), label[0], label[1]);
    button.type = 'button'; button.dataset.rkwView = key; button.setAttribute('aria-pressed', 'false');
    contextNav.appendChild(button);
  });
  function historyCopy(r, day, detailed) {
    if (r.p === null) return ['Estimate unavailable', '暂无估计'];
    if (!r.matched) return ['History unavailable', '历史依据不全'];
    if (r.thin) return detailed && r.n !== null ?
      ['Limited history · ' + r.n + ' observations', '历史样本有限 · ' + r.n + ' 个观测'] :
      ['Limited history', '历史样本有限'];
    if (detailed && r.n !== null) {
      var suffix = r.observed === null ? '' : ' · ' + percent(r.observed) + ' observed';
      var suffixZh = r.observed === null ? '' : ' · 实测 ' + percent(r.observed);
      return [r.n + ' historical observations' + suffix, r.n + ' 个历史观测' + suffixZh];
    }
    return ['View evidence', '查看依据'];
  }
  function renderOddsTable() {
    oddsView.replaceChildren();
    [5, 10, 21].forEach(function (day) {
      var r = reading(day), row = el('section', 'rkw-odds-row');
      row.classList.toggle('is-selected', day === selectedDay);
      var head = el('div', 'rkw-odds-row-head');
      head.appendChild(words(el('span', 'rkw-odds-row-label'), 'Next ' + day + ' trading days', '未来 ' + day + ' 个交易日'));
      var number = el('strong'); number.textContent = percent(r.p); head.appendChild(number); row.appendChild(head);
      var track = el('div', 'rkw-probability-track');
      track.setAttribute('aria-hidden', 'true');
      var fill = el('span', 'rkw-probability-fill'); fill.style.width = (r.p === null ? 0 : r.p * 100) + '%';
      track.appendChild(fill); row.appendChild(track);
      var base = r.base === null ? ['Typical rate unavailable', '常态概率暂无读数'] : ['Typical ' + percent(r.base), '常态 ' + percent(r.base)];
      row.appendChild(words(el('div', 'rkw-odds-evidence'), base[0], base[1]));
      var h = historyCopy(r, day, true);
      row.appendChild(words(el('div', 'rkw-odds-evidence'), h[0], h[1]));
      oddsView.appendChild(row);
    });
    var notes = el('details', 'rkw-disclosure');
    notes.appendChild(words(el('summary'), 'How to compare', '如何比较'));
    notes.appendChild(words(el('p', 'rkw-odds-evidence'),
      'The bars share a 0–100% scale. Typical is the historical baseline for that same horizon. Observations can overlap; a displayed rate is not a guarantee.',
      '所有条形均使用 0–100% 刻度。常态为同一期限的历史基准。观测可能相互重叠，所示概率并非保证。'));
    oddsView.appendChild(notes);
  }
  function setHorizon(day) {
    if ([5,10,21].indexOf(day) < 0) return;
    selectedDay = day;
    var r = reading(day);
    all('[data-rkw-horizon]').forEach(function (button) { button.setAttribute('aria-pressed', String(Number(button.dataset.rkwHorizon) === day)); });
    one('.rkw-probability').textContent = percent(r.p);
    words(one('.rkw-probability-caption'), r.p === null ? 'Estimate unavailable' : 'next ' + day + ' trading days', r.p === null ? '暂无估计' : '未来 ' + day + ' 个交易日');
    one('.rkw-probability-fill').style.width = (r.p === null ? 0 : r.p * 100) + '%';
    one('.rkw-probability-track').dataset.available = String(r.p !== null);
    var marker = one('.rkw-baseline-marker');
    marker.hidden = r.base === null || r.p === null;
    if (r.base !== null) marker.style.left = (r.base * 100) + '%';
    words(one('.rkw-baseline'), r.base === null ? 'Typical —' : 'Typical ' + percent(r.base), r.base === null ? '常态 —' : '常态 ' + percent(r.base));
    var h = historyCopy(r, day, false);
    words(one('.rkw-quality'), h[0], h[1]);
    one('.rkw-quality').classList.toggle('is-thin', r.p !== null && (!r.matched || r.thin));
    renderOddsTable();
    dialog.dataset.rkwSelectedHorizon = String(day);
  }
  function placeLiveContext() {
    if (!sourceBand) return;
    var destination = current && mobile.matches ? mobileContext : sourceSlot;
    if (sourceBand.parentNode !== destination) destination.appendChild(sourceBand);
    mobileContext.hidden = !current || !mobile.matches;
  }
  function focusTitle() { title.focus({preventScroll:true}); }
  function showView(key, trigger) {
    var view = views[key];
    if (!view) return;
    if (!current) {
      overviewScroll = body.scrollTop;
      origin = trigger || document.activeElement;
    }
    if (current && views[current]) vault.appendChild(views[current].node);
    current = key;
    words(title, view.en, view.zh);
    summary.replaceChildren();
    if (view.fact) {
      bilingualCopy(view.fact, summary);
      all('.rkc-sig-chip', summary).forEach(function (chip) { chip.remove(); });
    }
    else if (view.description) words(summary, view.description[0], view.description[1]);
    summary.hidden = !summary.childNodes.length;
    content.appendChild(view.node);
    inspector.hidden = false;
    dialog.classList.add('rkw-detail-open');
    var index = driverKeys.indexOf(key);
    all('.rkw-driver').forEach(function (button) { button.setAttribute('aria-expanded', String(button.dataset.rkwView === key)); });
    contextNav.hidden = index >= 0 || key === 'odds';
    all('[data-rkw-view]', contextNav).forEach(function (button) { button.setAttribute('aria-pressed', String(button.dataset.rkwView === key)); });
    one('.rkw-inspector-next').hidden = index < 0;
    one('.rkw-previous').disabled = index <= 0;
    one('.rkw-next').disabled = index < 0 || index >= driverKeys.length - 1;
    one('.rkw-step').textContent = index >= 0 ? String(index + 1) + ' / ' + driverKeys.length : '';
    placeLiveContext();
    body.scrollTop = 0;
    focusTitle();
  }
  function back() {
    if (!current) return false;
    vault.appendChild(views[current].node);
    current = null;
    inspector.hidden = true;
    dialog.classList.remove('rkw-detail-open');
    all('.rkw-driver').forEach(function (button) { button.setAttribute('aria-expanded', 'false'); });
    placeLiveContext();
    body.scrollTop = overviewScroll;
    if (origin && origin.isConnected) origin.focus({preventScroll:true});
    return true;
  }
  layout.addEventListener('click', function (event) {
    var button = event.target.closest('button');
    if (!button || !layout.contains(button)) return;
    if (button.dataset.rkwHorizon) setHorizon(Number(button.dataset.rkwHorizon));
    else if (button.dataset.rkwView) showView(button.dataset.rkwView, button);
    else if (button.classList.contains('rkw-back')) back();
    else if (button.classList.contains('rkw-next')) showView(driverKeys[driverKeys.indexOf(current) + 1]);
    else if (button.classList.contains('rkw-previous')) showView(driverKeys[driverKeys.indexOf(current) - 1]);
  });
  one('.rkw-horizons').addEventListener('keydown', function (event) {
    if (!['ArrowRight','ArrowLeft','Home','End'].includes(event.key)) return;
    var days = [5,10,21], index = days.indexOf(selectedDay);
    var next = event.key === 'Home' ? 0 : event.key === 'End' ? 2 : (index + (event.key === 'ArrowRight' ? 1 : -1) + 3) % 3;
    event.preventDefault();
    setHorizon(days[next]);
    one('[data-rkw-horizon="' + days[next] + '"]').focus();
  });
  /* The shared modal's document-capture Escape handler runs later in the path.
     Handle only this open workspace at window capture: one Escape returns to
     overview, a second continues to the existing modal close/re-focus behavior. */
  window.addEventListener('keydown', function (event) {
    if (!dialog.classList.contains('open') || event.defaultPrevented) return;
    var enclosingDialog = event.target.closest && event.target.closest('[role="dialog"],[role="alertdialog"]');
    if (enclosingDialog && enclosingDialog !== dialog) return;
    if (event.key === 'Escape' && current) {
      event.preventDefault(); event.stopImmediatePropagation(); back(); return;
    }
    if (event.key !== 'Tab') return;
    var focusable = all('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]:not([tabindex="-1"])', dialog)
      .filter(function (node) { return node.getClientRects().length && !node.closest('[hidden],[inert]'); });
    if (!focusable.length) return;
    var first = focusable[0], last = focusable[focusable.length - 1];
    /* The legacy trap includes hidden evidence; use only visible targets here. */
    event.stopImmediatePropagation();
    if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) {
      event.preventDefault(); first.focus();
    }
  }, true);
  function onViewportChange() {
    placeLiveContext();
    if (current && mobile.matches && overview.contains(document.activeElement)) focusTitle();
  }
  if (mobile.addEventListener) mobile.addEventListener('change', onViewportChange);
  else mobile.addListener(onViewportChange);
  /* Closing by backdrop/X keeps the next entry at the concise overview. The
     shared modal still owns authentication, page scroll lock, animation and focus. */
  var openObserver = new MutationObserver(function () {
    if (!dialog.classList.contains('open') && current) {
      var oldOrigin = origin; origin = null; back(); origin = oldOrigin;
    }
  });
  openObserver.observe(dialog, {attributes:true, attributeFilter:['class']});
  all('[data-rkw-view]').forEach(function (button) { button.setAttribute('aria-controls', 'rkw-inspector'); });
  setHorizon(21);
  dialog.classList.add('rkw-ready');
})();
