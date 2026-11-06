/* Request-scoped private reads. Abort is best effort, never settlement proof. */
const PREFIX = '/api/company-intelligence/private/';
const ACTION_MS = 15000;
class Refusal extends Error {
  constructor(status) { super('PRIVATE_READING_UNAVAILABLE'); this.status = status; }
}

export function createCompanyController({ fetchImpl, getSession, onState, decoder, maxBytes = 65536 }) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1 || maxBytes > 65536) throw new Error('INVALID_BYTE_LIMIT');
  let epoch = 0;
  let disposed = false;
  let pending = null;
  let qualified = null;
  const publish = state => { if (!disposed) onState(Object.freeze(state)); };
  const refuse = status => { throw new Refusal(status); };
  function quietCancel(reader) {
    try { void Promise.resolve(reader.cancel()).catch(() => {}); } catch (_) { /* best effort */ }
  }
  function stop() {
    epoch += 1;
    if (pending) {
      const old = pending;
      pending = null;
      old.cancelled = true;
      clearTimeout(old.timer);
      old.abort.abort();
      if (old.reader) quietCancel(old.reader);
      old.reject(new Refusal('stale'));
    }
  }
  function check(op) {
    if (disposed || op.id !== epoch || op.cancelled) refuse('stale');
    if (performance.now() >= op.deadline) refuse('unavailable');
  }
  async function checked(op, promise) {
    const value = await promise;
    check(op);
    return value;
  }
  async function owner(op, expected) {
    const session = await checked(op, getSession());
    if (!session || !session.user || typeof session.user.id !== 'string' || !session.user.id
        || typeof session.access_token !== 'string' || !session.access_token) refuse('signed_out');
    const value = { id: session.user.id, token: session.access_token };
    if (expected && (value.id !== expected.id || value.token !== expected.token)) refuse('signed_out');
    return value;
  }
  async function body(op, response) {
    if (response.redirected) refuse('unavailable');
    const headers = response.headers;
    const contentType = headers.get('Content-Type') || '';
    const cache = (headers.get('Cache-Control') || '').toLowerCase().split(',').map(v => v.trim());
    const vary = (headers.get('Vary') || '').toLowerCase().split(',').map(v => v.trim());
    if (!/^application\/json(?:\s*;|$)/i.test(contentType)
        || !cache.includes('private') || !cache.includes('no-store')
        || !vary.includes('authorization') || !vary.includes('cookie')) refuse('unavailable');
    const length = headers.get('Content-Length');
    if (length !== null && (!/^\d+$/.test(length) || Number(length) > maxBytes)) refuse('unavailable');
    if (!response.body || typeof response.body.getReader !== 'function') refuse('unavailable');
    const reader = response.body.getReader();
    op.reader = reader;
    const utf8 = new TextDecoder('utf-8', { fatal: true });
    const pieces = [];
    let bytes = 0;
    let complete = false;
    try {
      for (;;) {
        check(op);
        const chunk = await checked(op, reader.read());
        if (chunk.done) break;
        if (!(chunk.value instanceof Uint8Array)) refuse('unavailable');
        bytes += chunk.value.byteLength;
        if (bytes > maxBytes) refuse('unavailable');
        pieces.push(utf8.decode(chunk.value, { stream: true }));
      }
      pieces.push(utf8.decode());
      check(op);
      const value = JSON.parse(pieces.join(''));
      complete = true;
      return value;
    } finally {
      if (!complete) quietCancel(reader);
      if (op.reader === reader) op.reader = null;
      try { reader.releaseLock(); } catch (_) { /* a stale read may still be pending */ }
    }
  }
  async function read(op, path, identity) {
    await owner(op, identity);
    check(op);
    const response = await checked(op, fetchImpl(PREFIX + path, {
      method: 'GET', credentials: 'same-origin', cache: 'no-store', redirect: 'error',
      signal: op.abort.signal,
      headers: { Accept: 'application/json', Authorization: 'Bearer ' + identity.token },
    }));
    const value = await checked(op, body(op, response));
    if (response.status !== 200) {
      decoder.decodePrivateError(value, response.status);
      check(op);
      refuse(response.status === 401 ? 'signed_out' : response.status === 403 ? 'forbidden' : 'unavailable');
    }
    return value;
  }
  async function run(work, retained = null) {
    if (disposed) return;
    stop();
    qualified = retained;
    const op = { id: epoch, cancelled: false, abort: new AbortController(), reader: null,
      deadline: performance.now() + ACTION_MS };
    const cancelled = new Promise((_, reject) => { op.reject = reject; });
    pending = op;
    op.timer = setTimeout(() => {
      op.cancelled = true;
      op.abort.abort();
      if (op.reader) quietCancel(op.reader);
      op.reject(new Refusal('unavailable'));
    }, ACTION_MS);
    publish({ status: 'loading', ...(retained ? { context: retained.context, selection: retained.selection } : {}) });
    try {
      await Promise.race([work(op), cancelled]);
    } catch (error) {
      op.cancelled = true;
      op.abort.abort();
      if (op.reader) quietCancel(op.reader);
      if (!disposed && op.id === epoch && error?.status !== 'stale') {
        qualified = null;
        publish({ status: ['signed_out', 'forbidden'].includes(error?.status) ? error.status : 'unavailable' });
      }
    } finally {
      clearTimeout(op.timer);
      if (pending === op) pending = null;
    }
  }
  function lookup(query, expectedSecurityId = null) {
    return run(async op => {
      const symbol = typeof query === 'string' ? query.trim().toUpperCase() : '';
      if (!decoder.isPrivateCompanySymbol(symbol)) refuse('unavailable');
      const identity = await owner(op);
      const raw = await read(op, 'company-context?symbol=' + encodeURIComponent(symbol), identity);
      const context = await checked(op, decoder.decodePrivateCompanyContext(raw, symbol));
      // A dated TXI alias may resolve differently today. Refuse that identity
      // change before asking for issuer selections; never silently switch names.
      if (expectedSecurityId !== null && context.security_id !== expectedSecurityId) refuse('unavailable');
      const issuer = context.issuer_binding.issuer_id;
      const list = await read(op, 'issuers/' + encodeURIComponent(issuer) + '/product-integrations', identity);
      const selection = decoder.decodePrivateIssuerSelections(list, issuer);
      decoder.assertPrivateContextSelection(context, selection);
      await owner(op, identity);
      check(op);
      qualified = { identity, context, selection };
      publish({ status: selection.selections.length ? 'ready' : 'empty', context, selection });
    });
  }
  function selectFact(factId) {
    if (disposed) return Promise.resolve();
    const retained = qualified;
    const entry = retained && retained.selection.selections.find(item => item.fact_id === factId);
    if (!entry) {
      stop(); qualified = null; publish({ status: 'unavailable' });
      return Promise.resolve();
    }
    return run(async op => {
      const raw = await read(op, 'product-integrations/' + encodeURIComponent(factId), retained.identity);
      const fact = await checked(op, decoder.decodePrivateDisclosure(raw, factId));
      decoder.assertPrivateComposition(retained.selection, entry, fact);
      await owner(op, retained.identity);
      check(op);
      qualified = { ...retained, fact, selectedFactId: factId };
      publish({ status: 'ready', context: retained.context, selection: retained.selection,
        fact, selectedFactId: factId });
    }, retained);
  }
  function selectResearch(factId) {
    if (disposed) return Promise.resolve();
    const retained = qualified;
    const entry = retained && retained.selection.selections.find(item => item.fact_id === factId);
    // Research is an explicit continuation of this exact displayed fact. A
    // selection row alone cannot authorize a speculative or automatic read.
    if (!entry || !retained.fact || retained.selectedFactId !== factId) {
      stop(); qualified = null; publish({ status: 'unavailable' });
      return Promise.resolve();
    }
    return run(async op => {
      const raw = await read(op, 'supplier-research/' + encodeURIComponent(factId), retained.identity);
      const research = await checked(op, decoder.decodePrivateSupplierResearch(raw, factId));
      decoder.assertPrivateComposition(retained.selection, entry, research.disclosure);
      decoder.assertPrivateResearchComposition(retained.fact, research);
      await owner(op, retained.identity);
      check(op);
      qualified = { ...retained, fact: research.disclosure };
      publish({ status: 'ready', context: retained.context, selection: retained.selection,
        fact: research.disclosure, selectedFactId: factId, research });
    }, retained);
  }
  function clear() {
    if (disposed) return;
    stop(); qualified = null; publish({ status: 'idle' });
  }
  function dispose() {
    if (disposed) return;
    clear(); disposed = true;
  }
  return { lookup, selectFact, selectResearch, clear, dispose };
}
