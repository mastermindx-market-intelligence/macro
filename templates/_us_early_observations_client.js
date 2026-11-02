(function () {
  'use strict';
  var root = document.getElementById('us-early-observations');
  if (!root) return;
  var search = root.querySelector('#eo-search'), rows = root.querySelector('[data-eo-rows]');
  var status = root.querySelector('[data-eo-status]'), counts = root.querySelector('[data-eo-counts]');
  var source = root.querySelector('[data-eo-source]'), loading = root.querySelector('[data-eo-loading]');
  var prev = root.querySelector('[data-eo-prev]'), next = root.querySelector('[data-eo-next]');
  var serial = 0, controller = null, snapshot = null, offset = 0, nextOffset = null, term = '';
  var relations = {
    EXACT_EPISODE: ['Episode linked', '已关联候选阶段'],
    BLOCKED_BY_ACTIVE_EPISODE: ['Earlier episode still active', '较早的候选阶段仍活跃'],
    NOT_YET_ANCHORED: ['Anchor not yet established', '结构锚点尚未确立'],
    EPISODE_JOIN_UNAVAILABLE: ['Episode link unavailable', '候选阶段关联不可用'],
    IDENTITY_UNRESOLVED: ['Identity not verified', '标的身份尚未核实'],
    SOURCE_SUPPRESSED: ['Episode admission withheld', '尚未获准进入候选阶段']
  };
  var triggers = {
    dot_1d: ['Daily turn dot', '日线转向点'],
    pre_confluence_2d: ['2D crossed, 3D not yet', '2日已交叉，3日尚未'],
    basket_turn: ['Group turning', '板块转向中'],
    leader_reset_turn: ['Leader reset', '龙头回踩重置']
  };
  var blockers = {
    macd_below_signal: ['MACD below signal', 'MACD 低于信号线'],
    stoch_3d_not_crossed: ['3D confirmation not crossed', '3日确认尚未交叉'],
    macd_2d_not_crossed: ['2D MACD not crossed', '2日 MACD 尚未交叉'],
    stoch_overbought: ['Stochastic overbought', '随机指标超买'],
    stoch_bear_cross: ['Stochastic bearish cross', '随机指标向下交叉'],
    no_deep_or_weekly_confirm: ['Deep or weekly confirmation absent', '缺少深层或周线确认'],
    rsi_too_hot: ['RSI extended', 'RSI 偏热'],
    below_200dma: ['Below the 200-day average', '低于200日均线']
  };
  function bilingual(node, en, zh) {
    node.replaceChildren();
    [['l-en', en], ['l-zh', zh]].forEach(function (v) {
      var span = document.createElement('span'); span.className = v[0]; span.textContent = v[1]; node.appendChild(span);
    });
  }
  function clear() {
    rows.replaceChildren(); counts.hidden = true; source.hidden = true;
    counts.replaceChildren(); source.replaceChildren(); prev.disabled = true; next.disabled = true;
  }
  function message(state, en, zh) {
    root.dataset.state = state; status.className = 'mx-empty';
    status.hidden = !en && !zh;
    bilingual(status, en, zh);
  }
  function valid(body) {
    var authority = function (a) {
      return a && ['buy', 'alert', 'entry_open', 'rank', 'size', 'episode_write'].every(function (k) { return a[k] === false; })
        && Object.keys(a).every(function (k) { return a[k] === false; });
    };
    return body && body.schema === 'prophet.early_observations/v1'
      && ['CURRENT_SESSION', 'RETAINED_PREVIOUS_SESSION'].includes(body.status)
      && typeof body.snapshot_id === 'string' && /^early:[0-9a-f]{64}$/.test(body.snapshot_id)
      && authority(body.authority) && Array.isArray(body.rows) && body.rows.length <= 8
      && body.counts && Number.isInteger(body.counts.source) && body.counts.source >= 0
      && Number.isInteger(body.counts.matched) && body.counts.matched >= body.rows.length
      && body.counts.source >= body.counts.matched && body.counts.returned === body.rows.length
      && body.coverage && body.coverage.total === body.counts.source
      && ((body.coverage.state === 'UNAVAILABLE' && body.coverage.featured === null && body.coverage.beyond_cap === null)
        || (body.coverage.state === 'VERIFIED_SOURCE_PARTITION' && Number.isInteger(body.coverage.featured)
          && Number.isInteger(body.coverage.beyond_cap) && body.coverage.featured >= 0 && body.coverage.beyond_cap >= 0
          && body.coverage.featured + body.coverage.beyond_cap === body.counts.source))
      && body.page && body.page.offset === offset && body.page.limit === 8
      && (body.page.next_offset === null || body.page.next_offset === offset + 8)
      && body.clocks && /^\d{4}-\d{2}-\d{2}$/.test(body.clocks.source_session)
      && body.rows.every(function (row) {
        return row && typeof row.ticker === 'string' && /^[A-Za-z0-9][A-Za-z0-9.-]{0,31}$/.test(row.ticker)
          && (row.security_id === null || (typeof row.security_id === 'string' && /^SEC:/.test(row.security_id)))
          && row.episode_relation && Object.prototype.hasOwnProperty.call(relations, row.episode_relation.state)
          && Array.isArray(row.triggers_fired) && row.triggers_fired.every(function (t) { return typeof t === 'string'; })
          && row.source_evidence && row.source_evidence.triggers && row.lineage && row.lineage.state === 'CURRENT_RECEIPT_ONLY'
          && (row.source_evidence.counterevidence === null || (Array.isArray(row.source_evidence.counterevidence)
            && row.source_evidence.counterevidence.every(function (b) { return typeof b === 'string'; })))
          && authority(row.authority);
      });
  }
  function render(body) {
    snapshot = body.snapshot_id; nextOffset = body.page.next_offset;
    body.rows.forEach(function (row) {
      var line = document.createElement('div'); line.className = 'mx-chg-row'; line.dataset.eoRow = '';
      var name = document.createElement(row.security_id ? 'a' : 'span'); name.className = 'mx-chg-name';
      name.textContent = row.ticker;
      if (row.security_id) name.href = 'stocks/' + encodeURIComponent(row.ticker) + '.html';
      var why = document.createElement('span'); why.className = 'mx-chg-what';
      var names = row.triggers_fired.map(function (key) {
        return Object.prototype.hasOwnProperty.call(triggers, key) ? triggers[key] : ['Observed turn', '已记录转向'];
      });
      bilingual(why, names.map(function (x) { return x[0]; }).join(' · ') || 'No evaluated trigger', names.map(function (x) { return x[1]; }).join(' · ') || '暂无已评估的触发条件');
      var relation = document.createElement('span'); relation.className = 'eo-relation';
      bilingual(relation, relations[row.episode_relation.state][0], relations[row.episode_relation.state][1]);
      line.append(name, why, relation); rows.appendChild(line);
      var evidence = document.createElement('details'); evidence.className = 'eo-note';
      var title = document.createElement('summary'); bilingual(title, 'Source evidence', '来源证据'); evidence.appendChild(title);
      var against = row.source_evidence.counterevidence;
      var translated = (against || []).map(function (key) {
        return Object.prototype.hasOwnProperty.call(blockers, key) ? blockers[key] : ['Other source confirmation withheld', '来源中的其他确认尚未通过'];
      });
      var counter = document.createElement('p');
      bilingual(counter, against === null ? 'Counterevidence unavailable.' : (against.length
        ? 'Confirmation withheld: ' + translated.map(function (b) { return b[0]; }).join(' · ')
        : 'No slow-confirmation blockers recorded; entry permission is separate.'),
        against === null ? '反向证据不可用。' : (against.length
        ? '确认尚未通过：' + translated.map(function (b) { return b[1]; }).join(' · ')
        : '未记录慢层确认阻碍；入场权限独立判定。'));
      evidence.appendChild(counter);
      var history = document.createElement('p');
      bilingual(history, 'Current source revision only. Earlier correction history and first-available time are not recorded here.',
        '仅显示当前来源版本；此来源未记录较早的修订历史或首次可用时间。');
      evidence.appendChild(history); rows.appendChild(evidence);
    });
    counts.hidden = false;
    bilingual(counts, body.counts.source + ' observations · ' + body.counts.matched + ' matches · showing ' + body.rows.length,
      body.counts.source + ' 个观察 · ' + body.counts.matched + ' 个匹配 · 本页 ' + body.rows.length + ' 个');
    var partition = document.createElement('span'), cov = body.coverage;
    bilingual(partition, cov.state === 'VERIFIED_SOURCE_PARTITION'
      ? ' · ' + cov.featured + ' featured · ' + cov.beyond_cap + ' beyond the preview'
      : ' · Featured / beyond-preview counts unavailable', cov.state === 'VERIFIED_SOURCE_PARTITION'
      ? ' · 精选 ' + cov.featured + ' 个 · 预览以外 ' + cov.beyond_cap + ' 个'
      : ' · 精选与预览外数量不可用');
    counts.appendChild(partition);
    source.hidden = false;
    var date = body.clocks.source_session, retained = body.status === 'RETAINED_PREVIOUS_SESSION';
    bilingual(source, (retained ? 'Retained source from ' : 'Source session ') + date + '. Capture and publication times are unverified.',
      (retained ? '保留的较早来源：' : '来源交易日：') + date + '。采集与发布时间尚未核实。');
    if (body.rows.length) message('ready', '', '');
    else message('ready', term ? 'No observation matches this exact ticker in this source.' : 'No evaluated observations in this source.',
      term ? '此来源中没有与该完整代码匹配的观察。' : '此来源中暂无已评估的观察。');
    prev.disabled = offset === 0; next.disabled = nextOffset === null;
  }
  async function load(reset) {
    var current = ++serial;
    if (controller) controller.abort();
    controller = new AbortController();
    var active = controller, timer;
    var deadline = new Promise(function (_, reject) {
      timer = setTimeout(function () { active.abort(); reject(new Error('request-timeout')); }, 15000);
    });
    if (reset) { offset = 0; snapshot = null; nextOffset = null; }
    clear(); loading.hidden = false; root.setAttribute('aria-busy', 'true'); message('loading', '', '');
    try {
      if (!window.MDXAuth || !window.MDXAuth.client) throw new Error('auth-unavailable');
      var client = await Promise.race([window.MDXAuth.client(), deadline]);
      var session = await Promise.race([client.auth.getSession(), deadline]);
      if (current !== serial) return;
      var token = session && session.data && session.data.session && session.data.session.access_token;
      if (!token) { message('signed-out', 'Sign in to view early observations.', '登录后可查看早期观察。'); return; }
      var query = new URLSearchParams({limit: '8', offset: String(offset)});
      if (term) query.set('ticker', term);
      if (snapshot) query.set('snapshot', snapshot);
      var response = await fetch('/api/prophet/observations/v1?' + query, {
        headers: {Authorization: 'Bearer ' + token}, cache: 'no-store', signal: active.signal
      });
      if (current !== serial) return;
      if (response.status === 401) { message('signed-out', 'Sign in again to view early observations.', '请重新登录以查看早期观察。'); return; }
      if (response.status === 403 || response.status === 402) { message('locked', 'Full site access is required for early observations.', '早期观察需要完整网站访问权限。'); return; }
      if (response.status === 409) { snapshot = null; offset = 0; message('changed', 'The source changed. Refresh to start from its first page.', '来源已更新，请刷新后从第一页开始。'); return; }
      if (response.status === 400) { message('invalid', 'Enter a complete ticker, such as AMZN. Wildcards are not supported.', '请输入完整股票代码，例如 AMZN。不支持通配符。'); return; }
      if (!response.ok) throw new Error('source-unavailable');
      var body = await response.json();
      if (current !== serial) return;
      if (!valid(body)) throw new Error('invalid-response');
      render(body);
    } catch (error) {
      if (current === serial) { clear(); message('unavailable', 'Early observations could not be loaded. The candidate view is separate; retry this source.', '早期观察加载失败。候选视图独立提供，请重试此来源。'); }
    } finally {
      clearTimeout(timer);
      if (current === serial) { loading.hidden = true; root.removeAttribute('aria-busy'); }
    }
  }
  root.addEventListener('toggle', function () { if (root.open && root.dataset.state === 'idle') load(true); });
  root.querySelector('[data-eo-form]').addEventListener('submit', function (event) {
    event.preventDefault(); term = search.value.trim(); load(true);
  });
  root.querySelector('[data-eo-reset]').addEventListener('click', function () { search.value = ''; term = ''; load(true); });
  root.querySelector('[data-eo-retry]').addEventListener('click', function () { load(true); });
  prev.addEventListener('click', function () { if (offset >= 8) { offset -= 8; load(false); } });
  next.addEventListener('click', function () { if (nextOffset !== null) { offset = nextOffset; load(false); } });
  window.addEventListener('mdx-auth', function () {
    ++serial; if (controller) controller.abort(); clear(); loading.hidden = true;
    root.removeAttribute('aria-busy'); snapshot = null; offset = 0; root.dataset.state = 'idle';
    if (root.open) load(true);
  });
})();
