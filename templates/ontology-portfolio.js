/* Private Portfolio and Watchlist membership on Macro. Explicit reads only; no sync, writes,
 * holdings in URLs, telemetry, browser persistence or a second portfolio model. */
const LIMIT = 262144;
const BUDGET_MS = 15000;
const HASH = /^sha256:[a-f0-9]{64}$/;
const SYMBOL = /^[A-Z0-9^][A-Z0-9.^=:_-]{0,63}$/;
const SID = /^SEC:[A-Za-z0-9:._/-]{1,120}$/;
const CHAINS = ['oil_inflation_duration_derate', 'dollar_spike_em_multinational'];
const STATES = ['covered', 'not_in_available_screens', 'identity_unresolved', 'membership_unavailable'];
function words(en, zh) {
  const f = document.createDocumentFragment();
  for (const [lang, value] of [['en', en], ['zh', zh]]) {
    const n = document.createElement('span'); n.className = 'l-' + lang; n.textContent = value; f.append(n);
  }
  return f;
}
function node(tag, cls, en, zh) {
  const n = document.createElement(tag); if (cls) n.className = cls;
  if (en !== undefined) n.append(words(en, zh)); return n;
}
function day(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
    && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
}
function canonical() {
  try { const user = window.MDXAuth?.user?.(); return typeof user?.id === 'string' && user.id ? user.id : null; }
  catch (_) { return null; }
}
function quietCancel(reader) {
  try { void Promise.resolve(reader.cancel()).catch(() => {}); } catch (_) { /* best effort */ }
}
function fail() { throw new Error('PORTFOLIO_UNAVAILABLE'); }

export function decodeMembership(value, symbols, reading) {
  if (!value || value.schema !== 'ontology_portfolio_identity.v1'
      || value.source_manifest_hash !== reading.source_manifest_hash || value.chain !== reading.chain
      || value.membership_asof !== reading.asof || !day(value.identity_valid_on)
      || value.identity_valid_on < value.membership_asof
      || value.identity_source_sha256 !== reading.identity_sha256
      || value.meaning !== 'declared_screen_membership_only' || value.pnl !== null
      || !value.authority || ['can_rank', 'can_gate', 'can_size', 'can_trade'].some(k => value.authority[k] !== false)
      || !Array.isArray(value.rows) || value.rows.length !== symbols.length
      || !Array.isArray(value.unresolved_channels) || !value.counts) fail();
  const ids = new Set(reading.channels.map(c => c.id));
  const uniqueChannels = list => Array.isArray(list) && list.length <= ids.size
    && new Set(list).size === list.length && list.every(id => ids.has(id));
  if (!uniqueChannels(value.unresolved_channels)) fail();
  const counts = Object.fromEntries(STATES.map(s => [s, 0]));
  value.rows.forEach((row, i) => {
    if (!row || row.index !== i || row.symbol !== symbols[i] || !STATES.includes(row.state)
        || !uniqueChannels(row.channels)) fail();
    if (row.state === 'identity_unresolved') {
      if (row.security_id !== null || row.currency !== null || row.channels.length) fail();
    } else {
      if (typeof row.security_id !== 'string' || !SID.test(row.security_id)
          || !(row.currency === null || /^[A-Z]{3}$/.test(row.currency))) fail();
      if ((row.state === 'covered') !== (row.channels.length > 0)) fail();
    }
    counts[row.state]++;
  });
  if (STATES.some(s => counts[s] !== value.counts[s])) fail();
  return value;
}

// Portfolio's existing owner computes the distribution. Unknown identities,
// duplicate lots, invalid arithmetic or incomplete books never get normalized away.
export function portfolioBooks(rows, membership, ps) {
  const open = rows.filter(r => r.status === 'open');
  const identities = new Map(membership.rows.map(r => [r.symbol, r]));
  if (!ps || typeof ps.computeSnapshot !== 'function') return { reason: 'unavailable', books: [] };
  if (new Set(open.map(r => r.ticker)).size !== open.length) return { reason: 'duplicate_lots', books: [] };
  if (open.some(r => !identities.get(r.ticker)?.currency)) return { reason: 'identity', books: [] };
  if (open.some(r => r.shares !== null && r.shares < 0)) return { reason: 'sizing', books: [] };
  const groups = new Map();
  open.forEach(row => {
    const currency = identities.get(row.ticker).currency;
    if (!groups.has(currency)) groups.set(currency, []);
    groups.get(currency).push(row);
  });
  const books = [];
  for (const [currency, bookRows] of groups) {
    const snapshot = ps.computeSnapshot({ rows: bookRows, authority: 'cloud', readState: 'ready',
      writeState: 'offline_readonly', priceOf: () => null, bookOf: () => currency });
    const weighting = snapshot.weighting;
    if (weighting.complete) {
      const values = bookRows.map(r => weighting.weights[r.ticker]);
      if (!['equal_assumption', 'entry_cost'].includes(weighting.basis)
          || values.some(v => !Number.isFinite(v) || v < 0 || v > 100)
          || Math.abs(values.reduce((a, b) => a + b, 0) - 100) > 0.000001) {
        books.push({ currency, weighting: { complete: false, weights: {}, basis: 'none' } }); continue;
      }
    }
    books.push({ currency, weighting });
  }
  return { reason: null, books };
}

export function mountPortfolio(root) {
  if (!root) return null;
  const output = root.querySelector('[data-portfolio-result]');
  const button = root.querySelector('[data-portfolio-read]');
  const clearButton = root.querySelector('[data-portfolio-clear]');
  const kindButtons = [...root.querySelectorAll('[data-private-kind]')];
  const listLabel = root.querySelector('[data-watchlist-picker]');
  const listSelect = root.querySelector('[data-watchlist-select]');
  let kind = 'portfolio';
  function resetLists() { if (listSelect) listSelect.replaceChildren(); }
  function controls() {
    if (listLabel) listLabel.hidden = kind !== 'watchlist' || !listSelect?.options.length;
    for (const b of kindButtons) b.setAttribute('aria-pressed', String(b.dataset.privateKind === kind));
    button.replaceChildren(words(...(kind === 'portfolio' ? ['Read my Portfolio', '读取我的投资组合']
      : listSelect?.value ? ['Compare selected Watchlist', '对照所选观察列表'] : ['Read my Watchlists', '读取我的观察列表'])));
  }
  let reading = null, operation = null, epoch = 0, disposed = false, subscription = null;
  const messages = {
    idle: ['Read your saved Portfolio against this path’s dated screen membership.', '将已保存的投资组合与该路径的历史筛选成员进行对照。'],
    no_reading: ['Load a current path reading before reading your Portfolio.', '请先加载当前路径读数，再读取投资组合。'],
    loading: ['Reading your saved Portfolio and resolving its security identities…', '正在读取已保存的投资组合并核实证券身份…'],
    signed_out: ['Sign in to read your private Portfolio.', '登录后读取您的私有投资组合。'],
    forbidden: ['This account does not include this path’s private research.', '此账户未包含该路径的私有研究权限。'],
    unavailable: ['The complete Portfolio reading is unavailable. No empty or partial book is substituted.', '完整投资组合读数不可用。不会以空组合或部分持仓替代。'],
    changed: ['The selected path changed. Read your Portfolio again against the new reading.', '所选路径已更新，请依据新读数重新读取投资组合。'],
    empty: ['Your saved Portfolio has no open positions.', '已保存的投资组合没有未平仓持仓。'],
  };
  function status(state) {
    if (['signed_out', 'forbidden', 'no_reading'].includes(state)) resetLists();
    output.replaceChildren(); output.dataset.state = state;
    output.setAttribute('aria-busy', state === 'loading' ? 'true' : 'false');
    output.append(node('p', 'ox-note', ...(messages[state] || messages.unavailable)));
    if (kind === 'watchlist') {
      const copy = {
        idle: ['Read your saved Watchlists, then select one to compare with this path.', '先读取已保存的观察列表，再选择一个与此路径对照。'],
        no_reading: ['Load a current path reading before reading your Watchlists.', '请先加载当前路径读数，再读取观察列表。'],
        choose_list: ['Choose a Watchlist, then request its membership comparison.', '请选择观察列表，再请求成员对照。'],
        loading: ['Reading your Watchlist…', '正在读取观察列表…'],
        signed_out: ['Sign in to read your private Watchlists.', '登录后读取您的私有观察列表。'],
        unavailable: ['The complete Watchlist reading is unavailable. No partial list is substituted.', '完整观察列表读数不可用；不会以部分列表替代。'],
        empty_lists: ['You have no saved Watchlists.', '您尚未保存观察列表。'],
        empty: ['This saved Watchlist has no symbols.', '此观察列表尚无证券代码。'],
        changed: ['The selected path changed. Read your Watchlist again against the new reading.', '所选路径已更新，请依据新读数重新读取观察列表。'],
      };
      if (copy[state]) output.replaceChildren(node('p', 'ox-note', ...copy[state]));
    }
    controls();
    button.disabled = state === 'loading' || !reading;
  }
  function stop() {
    epoch++;
    if (operation) {
      const old = operation; operation = null;
      old.abort.abort(); if (old.reader) quietCancel(old.reader);
      clearTimeout(old.timer); old.reject(new Error('PORTFOLIO_CANCELLED'));
    }
  }
  function clear() { stop(); resetLists(); status(reading ? 'idle' : 'no_reading'); }
  function invalidate() { reading = null; clear(); }
  function authChanged() {
    // A same-owner token refresh clears private rows, but need not strand the
    // selected public path. Account changes discard that selection as well.
    if (reading && reading.owner_id === canonical()) clear(); else invalidate();
  }
  function check(op) {
    if (disposed || op.id !== epoch || op.abort.signal.aborted || performance.now() >= op.deadline
        || reading !== op.reading || canonical() !== op.owner || op.kind !== kind
        || (kind === 'watchlist' && (listSelect?.value || null) !== op.listId)) fail();
  }
  async function checked(op, promise) { const value = await promise; check(op); return value; }
  // Bind the incumbent SDK's change signal, without initializing WatchStore sync.
  const authentication = Promise.resolve().then(async () => {
    const sdk = await window.MDXAuth?.client?.();
    if (disposed || !sdk?.auth?.onAuthStateChange) fail();
    const result = sdk.auth.onAuthStateChange(authChanged);
    subscription = result?.data?.subscription;
    if (!subscription?.unsubscribe) fail();
    return sdk;
  });
  void authentication.catch(() => {});
  async function session(op, token) {
    const sdk = await checked(op, authentication);
    const result = await checked(op, sdk.auth.getSession());
    const s = result?.data?.session;
    if (result?.error || !s || s.user?.id !== op.owner || !s.access_token || typeof s.access_token !== 'string'
        || (token && s.access_token !== token)) fail();
    return s.access_token;
  }
  async function body(op, response) {
    const h = response.headers;
    const cache = (h.get('Cache-Control') || '').toLowerCase().split(',').map(v => v.trim());
    const vary = (h.get('Vary') || '').toLowerCase().split(',').map(v => v.trim());
    if (response.redirected || !/^application\/json(?:\s*;|$)/i.test(h.get('Content-Type') || '')
        || !cache.includes('private') || !cache.includes('no-store')
        || !vary.includes('authorization') || !vary.includes('cookie')) fail();
    const length = h.get('Content-Length');
    if (length !== null && (!/^\d+$/.test(length) || Number(length) > LIMIT)) fail();
    const reader = response.body?.getReader(); if (!reader) fail(); op.reader = reader;
    const utf8 = new TextDecoder('utf-8', { fatal: true }), pieces = [];
    let count = 0, complete = false;
    try {
      for (;;) {
        check(op); const chunk = await checked(op, reader.read()); if (chunk.done) break;
        if (!(chunk.value instanceof Uint8Array)) fail();
        count += chunk.value.byteLength; if (count > LIMIT) fail();
        pieces.push(utf8.decode(chunk.value, { stream: true }));
      }
      pieces.push(utf8.decode()); check(op);
      const value = JSON.parse(pieces.join('')); complete = true; return value;
    } finally {
      if (!complete) quietCancel(reader); if (op.reader === reader) op.reader = null;
      try { reader.releaseLock(); } catch (_) { /* an abandoned read may still be pending */ }
    }
  }
  function render(rows, result, readAt, listName = '') {
    output.replaceChildren(); output.dataset.state = 'ready'; output.setAttribute('aria-busy', 'false');
    const open = rows.filter(r => r.status === 'open'), closed = rows.length - open.length;
    if (kind === 'watchlist') {
      const title = node('strong'); title.textContent = listName; output.append(title);
      output.append(node('p', 'ox-note', `${open.length} saved symbols. Read in this browser at ${readAt}. Screen membership ${result.membership_asof}; security identity checked for ${result.identity_valid_on}.`,
        `${open.length} 个已保存代码。本浏览器读取时间 ${readAt}。筛选成员日期 ${result.membership_asof}；证券身份核实日期 ${result.identity_valid_on}。`));
    } else output.append(node('p', 'ox-note',
      `${open.length} open positions; ${closed} closed positions excluded. Read in this browser at ${readAt}. Screen membership ${result.membership_asof}; security identity checked for ${result.identity_valid_on}.`,
      `${open.length} 个未平仓持仓；已排除 ${closed} 个已平仓持仓。本浏览器读取时间 ${readAt}。筛选成员日期 ${result.membership_asof}；证券身份核实日期 ${result.identity_valid_on}。`));
    const coverage = result.counts;
    output.append(node('p', 'ox-note',
      `Distinct saved symbols: ${coverage.covered} matched; ${coverage.not_in_available_screens} outside available screens; ${coverage.identity_unresolved} unresolved identities; ${coverage.membership_unavailable} with unavailable membership.`,
      `去重代码覆盖：${coverage.covered} 个匹配；${coverage.not_in_available_screens} 个不在可用筛选名单；${coverage.identity_unresolved} 个身份未核实；${coverage.membership_unavailable} 个成员信息不可用。`));
    if (result.unresolved_channels.length) output.append(node('p', 'ox-note',
      'Some screens or company identities are unavailable. This is partial membership coverage, not a complete exposure estimate.',
      '部分筛选结果或公司身份不可用。这是部分成员覆盖，并非完整敞口估计。'));
    const books = kind === 'watchlist' ? { reason: null, books: [] } : portfolioBooks(rows, result, window.PS);
    const map = new Map(result.rows.map(r => [r.symbol, r]));
    const labels = new Map(reading.channels.map(c => [c.id, c.label]));
    if (books.reason) output.append(node('p', 'ox-note',
      'Weights are unavailable because the full book’s identities, position lots or sizing cannot be reconciled.',
      '完整组合的身份、持仓批次或数量无法核实，因此不显示权重。'));
    for (const book of books.books) {
      const basis = book.weighting.complete ? book.weighting.basis : 'none';
      const copy = basis === 'entry_cost'
        ? [`${book.currency}: entry-cost weights, not current market values.`, `${book.currency}：按建仓成本计算的权重，并非当前市值。`]
        : basis === 'equal_assumption'
          ? [`${book.currency}: equal weights assumed; no position sizes entered.`, `${book.currency}：未填写持仓数量，假设等权。`]
          : [`${book.currency}: weights unavailable for this book.`, `${book.currency}：该币种组合的权重不可用。`];
      output.append(node('p', 'ox-note', ...copy));
    }
    if (kind === 'watchlist') output.append(node('p', 'ox-note',
      'Watchlist membership is not a holding or a weight. No position sizing, sensitivity, return or P&L is inferred; missing membership does not mean zero economic exposure.',
      '观察列表成员并非持仓或权重。不会推断持仓数量、敏感度、回报或损益；未出现在成员名单中不表示经济敞口为零。'));
    else output.append(node('p', 'ox-note',
      'Currencies are kept separate. Membership does not estimate sensitivity, return or P&L; missing membership does not mean zero economic exposure.',
      '不同币种分别计算。成员关系不估计敏感度、回报或损益；未出现在成员名单中不表示经济敞口为零。'));
    const list = node('ul', 'ox-portfolio-rows');
    const renderEpoch = epoch, renderedOwner = reading.owner_id;
    const more = node('button', 'ox-cta secondary', 'Show more positions', '显示更多持仓');
    more.type = 'button';
    let shown = 0;
    function appendPage() {
      if (disposed || epoch !== renderEpoch || canonical() !== renderedOwner) { clear(); return; }
      const next = Math.min(shown + 20, open.length);
      for (const row of open.slice(shown, next)) {
      const joined = map.get(row.ticker), item = node('li', 'ox-card ox-portfolio-row');
      const title = node('strong'); title.textContent = row.ticker; item.append(title);
      if (joined.state === 'covered') {
        const channels = node('div', 'ox-portfolio-membership');
        for (const id of joined.channels) { const label = labels.get(id); channels.append(node('p', 'ox-note', label.en, label.zh)); }
        item.append(channels);
      } else {
        const copy = joined.state === 'identity_unresolved'
          ? ['Security identity unresolved', '证券身份尚未核实']
          : joined.state === 'membership_unavailable' ? ['Screen membership unavailable', '筛选成员信息不可用']
            : ['Not in the available dated screens', '未出现在可用的历史筛选名单中'];
        item.append(node('p', 'ox-note', ...copy));
      }
      const book = books.books.find(b => b.currency === joined.currency);
      if (book?.weighting.complete) {
        const value = book.weighting.weights[row.ticker];
        item.append(node('p', 'ox-note', `${value.toFixed(2)}% within ${book.currency}`, `${joined.currency} 组合内占比 ${value.toFixed(2)}%`));
      }
        list.append(item);
      }
      shown = next; more.hidden = shown >= open.length;
      more.replaceChildren(kind === 'watchlist'
        ? words(`Show more symbols (${shown} of ${open.length} shown)`, `显示更多代码（已显示 ${shown}/${open.length}）`)
        : words(`Show more positions (${shown} of ${open.length} shown)`, `显示更多持仓（已显示 ${shown}/${open.length}）`));
    }
    more.addEventListener('click', appendPage);
    output.append(list, more); appendPage(); button.disabled = !reading;
  }
  async function read() {
    if (disposed) return;
    stop();
    if (!reading) { status('no_reading'); return; }
    const owner = canonical();
    if (!owner || reading.owner_id !== owner) { status('signed_out'); return; }
    const op = { id: epoch, owner, reading, kind, listId: kind === 'watchlist' ? (listSelect?.value || null) : null, abort: new AbortController(), reader: null,
      deadline: performance.now() + BUDGET_MS };
    const cancellation = new Promise((_, reject) => { op.reject = reject; });
    operation = op;
    op.timer = setTimeout(() => { op.abort.abort(); if (op.reader) quietCancel(op.reader); op.reject(new Error('PORTFOLIO_TIMEOUT')); }, BUDGET_MS);
    status('loading');
    try {
      await Promise.race([(async () => {
        const token = await session(op);
        let rows, readAt, listName = '';
        if (op.kind === 'watchlist') {
          if (!listSelect || typeof window.WatchStore?.lists?.readOnly !== 'function') fail();
          const options = { signal: op.abort.signal };
          if (op.listId) options.listId = op.listId;
          const watch = await checked(op, window.WatchStore.lists.readOnly(options));
          if (watch?.schema !== 'watchlist_read.v1' || watch.authority !== 'cloud' || watch.state !== 'ready'
              || watch.owner_id !== owner || !day(watch.last_good_at?.slice(0, 10))
              || !Array.isArray(watch.lists) || watch.lists.length > 100
              || watch.lists.some(l => !l || typeof l.id !== 'string' || !l.id || l.id.length > 128
                || typeof l.name !== 'string' || l.name.length > 256)
              || new Set(watch.lists.map(l => l.id)).size !== watch.lists.length) fail();
          await session(op, token);
          if (!op.listId) {
            if (watch.list_id !== null || watch.rows !== null) fail();
            resetLists();
            if (watch.lists.length) {
              const placeholder = document.createElement('option'); placeholder.value = ''; placeholder.textContent = 'Choose Watchlist / 选择观察列表'; listSelect.append(placeholder);
              for (const l of watch.lists) { const o = document.createElement('option'); o.value = l.id; o.textContent = l.name; listSelect.append(o); }
            }
            status(watch.lists.length ? 'choose_list' : 'empty_lists'); return;
          }
          if (watch.list_id !== op.listId || watch.lists.length !== 1 || watch.lists[0].id !== op.listId
              || !Array.isArray(watch.rows) || watch.rows.length > 500
              || watch.rows.some(r => !r || typeof r.symbol !== 'string' || !SYMBOL.test(r.symbol))
              || new Set(watch.rows.map(r => r.symbol)).size !== watch.rows.length) fail();
          rows = watch.rows.map(r => ({ ticker: r.symbol, status: 'open' }));
          readAt = watch.last_good_at; listName = watch.lists[0].name;
        } else {
          if (typeof window.WatchStore?.portfolio?.readOnly !== 'function') fail();
          const portfolio = await checked(op, window.WatchStore.portfolio.readOnly({ signal: op.abort.signal }));
          if (portfolio?.schema !== 'portfolio_read.v1' || portfolio.authority !== 'cloud'
              || portfolio.state !== 'ready' || portfolio.owner_id !== owner || !Array.isArray(portfolio.rows)
              || portfolio.rows.length > 500 || !day(portfolio.last_good_at?.slice(0, 10))) fail();
          rows = portfolio.rows; readAt = portfolio.last_good_at;
          if (rows.some(r => !r || !['open', 'closed'].includes(r.status) || !SYMBOL.test(r.ticker))) fail();
        }
        const symbols = [...new Set(rows.filter(r => r.status === 'open').map(r => r.ticker))];
        await session(op, token);
        if (!symbols.length) { status('empty'); return; }
        const request = JSON.stringify({ schema: 'ontology_portfolio_request.v1', chain: reading.chain,
          source_manifest_hash: reading.source_manifest_hash, symbols });
        if (new TextEncoder().encode(request).length > 65536) fail();
        const response = await checked(op, fetch('/api/ontology/explorer/portfolio/v1', {
          method: 'POST', credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: op.abort.signal,
          headers: { Accept: 'application/json', 'Content-Type': 'application/json', Authorization: 'Bearer ' + token }, body: request,
        }));
        if (response.status !== 200) {
          await session(op, token);
          status(response.status === 401 ? 'signed_out' : response.status === 403 ? 'forbidden'
            : response.status === 409 ? 'changed' : 'unavailable'); return;
        }
        const result = decodeMembership(await checked(op, body(op, response)), symbols, reading);
        await session(op, token); check(op);
        render(rows, result, readAt, listName);
      })(), cancellation]);
    } catch (_) {
      if (!disposed && epoch === op.id) { resetLists(); status(canonical() === owner ? 'unavailable' : 'signed_out'); }
    } finally {
      op.abort.abort(); if (op.reader) quietCancel(op.reader); clearTimeout(op.timer);
      if (operation === op) operation = null;
    }
  }
  function receive(event) {
    invalidate(); const r = event.detail;
    if (!r || !CHAINS.includes(r.chain) || !HASH.test(r.source_manifest_hash) || !day(r.asof)
        || r.owner_id !== canonical() || !r.owner_id || !Array.isArray(r.channels) || r.channels.length > 100
        || !(r.identity_sha256 === null || /^[a-f0-9]{64}$/.test(r.identity_sha256))
        || r.channels.some(c => !c || typeof c.id !== 'string' || c.id.length > 128 || !c.label
          || typeof c.label.en !== 'string' || typeof c.label.zh !== 'string'
          || c.label.en.length > 256 || c.label.zh.length > 256)
        || new Set(r.channels.map(c => c.id)).size !== r.channels.length) return;
    reading = { ...r, channels: r.channels.map(c => ({ id: c.id, label: { ...c.label } })) }; status('idle');
  }
  root.addEventListener('ontology-reading', receive);
  root.addEventListener('ontology-source-changed', invalidate);
  window.addEventListener('mdx-auth', authChanged);
  window.addEventListener('pagehide', invalidate);
  function changeKind(event) {
    const selected = event.currentTarget.dataset.privateKind;
    if (!['portfolio', 'watchlist'].includes(selected)) return;
    kind = selected; clear();
  }
  function selectList() { stop(); status(reading ? 'choose_list' : 'no_reading'); }
  for (const b of kindButtons) b.addEventListener('click', changeKind);
  listSelect?.addEventListener('change', selectList);
  button.addEventListener('click', read); clearButton.addEventListener('click', clear);
  status('no_reading');
  root.dispatchEvent(new CustomEvent('ontology-consumer-ready'));
  return { clear, dispose() { disposed = true; stop(); output.replaceChildren();
    root.removeEventListener('ontology-reading', receive); root.removeEventListener('ontology-source-changed', invalidate);
    window.removeEventListener('mdx-auth', authChanged); window.removeEventListener('pagehide', invalidate);
    for (const b of kindButtons) b.removeEventListener('click', changeKind);
    listSelect?.removeEventListener('change', selectList); resetLists();
    button.removeEventListener('click', read); clearButton.removeEventListener('click', clear); subscription?.unsubscribe();
  } };
}
mountPortfolio(document.getElementById('ox-portfolio'));
