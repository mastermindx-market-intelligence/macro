// Self-contained Node VM tests for the additive WatchStore watchlistReadOnly
// adapter. Run: node watchlist-readonly.test.mjs
// No network, no secrets, no repository access: MDXAuth, the Supabase client,
// window events and every query answer are faked in memory. Each scenario
// asserts the exact selected fields, count mode, filters, orders and limits of
// every issued query, that the forbidden cache/sync entrypoints are never
// called, and that the process ends without unhandled rejections.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const watchstorePath = fileURLToPath(new URL('../../templates/watchstore.js', import.meta.url));
const watchstore = readFileSync(watchstorePath, 'utf8');
const start = watchstore.indexOf('  function watchlistReadOnly(options)');
const end = watchstore.indexOf('  // ---- public API', start);
assert(start >= 0 && end > start);
assert(watchstore.includes('readOnly: watchlistReadOnly'));
const source = watchstore.slice(start, end);

const LIST_SELECT = 'id,user_id,name,position,created_at';
const SYMBOL_SELECT = 'watchlist_id,symbol,position,created_at';

const unhandled = [];
process.on('unhandledRejection', (reason) => { unhandled.push(String(reason)); });

// ---- fakes ------------------------------------------------------------

// A Supabase-like read-only query builder. Tables may use { rows, __count }
// to force a lying total and { rows, __raw: true } to skip server-side
// filtering, simulating a broken filter or RLS answer.
function fakeClient(tables, calls, forbidden) {
  function source(table) {
    const entry = tables[table];
    if (!entry) return null;
    const out = { rows: entry.rows || entry, forced: undefined, raw: Boolean(entry.__raw) };
    if (Object.prototype.hasOwnProperty.call(entry, '__count')) out.forced = entry.__count;
    return out;
  }
  function run(desc) {
    calls.push(desc);
    const src = source(desc.table);
    if (!src) return { error: { message: 'unknown table: ' + desc.table }, data: null, count: null };
    let rows = src.rows.slice();
    if (!src.raw) for (const f of desc.eqs) rows = rows.filter((r) => r[f.col] === f.val);
    const count = src.forced === undefined ? rows.length : src.forced;
    rows.sort((a, b) => {
      const pa = a.position == null ? -Infinity : a.position;
      const pb = b.position == null ? -Infinity : b.position;
      if (pa !== pb) return pa - pb;
      return String(a.created_at).localeCompare(String(b.created_at));
    });
    if (typeof desc.limit === 'number') rows = rows.slice(0, desc.limit);
    return { error: null, data: rows, count };
  }
  function builder(desc) {
    const pending = Promise.resolve().then(() => run(desc));
    return {
      select(fields, opts) { desc.select = fields; desc.countOpt = opts && opts.count; return this; },
      eq(col, val) { desc.eqs.push({ col, val }); return this; },
      order(col) { desc.orders.push(col); return this; },
      limit(n) { desc.limit = n; return this; },
      abortSignal(sig) { desc.signal = sig; return this; },
      then(onFulfilled, onRejected) { return pending.then(onFulfilled, onRejected); },
    };
  }
  const client = {
    from(table) { return builder({ table, eqs: [], orders: [] }); },
    // Existing WatchStore entrypoints that a read-only adapter must never call.
    listsFetch() { forbidden.listsFetch = true; },
    symbolsFetch() { forbidden.symbolsFetch = true; },
    init() { forbidden.init = true; },
  };
  return client;
}

// Fake MDXAuth. tokens rotates per getSession call (clamped to the last) so a
// mid-read token rotation can be staged. switchAfter/switchTo change the
// canonical account after N user() calls, i.e. mid-read.
function fakeAuth(client, opts) {
  const state = {
    userId: opts.userId, tokens: opts.tokens.slice(),
    getSessionCalls: 0, userCalls: 0,
  };
  const auth = {
    user() {
      state.userCalls += 1;
      const id = opts.switchAfter !== undefined && state.userCalls > opts.switchAfter
        ? opts.switchTo
        : state.userId;
      return id == null ? null : { id };
    },
    async client() { return opts.clientFactory ? opts.clientFactory() : client; },
  };
  client.auth = {
    async getSession() {
      state.getSessionCalls += 1;
      const i = Math.min(state.getSessionCalls - 1, state.tokens.length - 1);
      return { error: null, data: { session: { user: { id: state.userId }, access_token: state.tokens[i] } } };
    },
  };
  return { auth, state };
}

function fakeWindow() {
  const listeners = [];
  return {
    listeners,
    MDXAuth: null,
    addEventListener(type, fn) { listeners.push({ type, fn }); },
    removeEventListener(type, fn) {
      const i = listeners.findIndex((l) => l.type === type && l.fn === fn);
      if (i >= 0) listeners.splice(i, 1);
    },
    emit(type) { listeners.slice().forEach((l) => { if (l.type === type) l.fn({ type }); }); },
  };
}

// Evaluate the artifact inside a fresh VM context with only the closure
// dependencies the WatchStore insertion point provides.
function loadFn(win) {
  const sandbox = {
    window: win,
    performance,
    setTimeout,
    clearTimeout,
    AbortController,
    PF_CLOUD_DEADLINE_MS: 12000,
    nowISO: () => new Date().toISOString(),
    __out: {},
  };
  const context = vm.createContext(sandbox);
  new vm.Script(source + '\n;__out.watchlistReadOnly = watchlistReadOnly;',
    { filename: 'watchlist-readonly.js' }).runInContext(context);
  return sandbox.__out.watchlistReadOnly;
}

// ---- assertion helpers ------------------------------------------------

function assertError(res, reason) {
  assert.equal(res.state, 'error');
  assert.equal(res.warning, reason);
  assert.equal(res.schema, 'watchlist_read.v1');
  assert.equal(res.authority, 'cloud');
  assert.equal(res.rows, null);
  assert.equal(res.lists, null);
  assert.equal(res.owner_id, null);
  assert.equal(res.list_id, null);
  assert.equal(res.last_good_at, null);
}

function assertQuery(calls, index, want) {
  const q = calls[index];
  assert.ok(q, 'expected query ' + index + ' was not issued');
  assert.equal(q.table, want.table, 'table');
  assert.equal(q.select, want.select, 'selected fields');
  assert.equal(q.countOpt, 'exact', 'count mode');
  assert.deepEqual(q.eqs, want.eqs, 'filters');
  assert.deepEqual(q.orders, want.orders || [], 'orders');
  assert.equal(q.limit, want.limit, 'limit');
  assert.ok(q.signal && typeof q.signal.aborted === 'boolean', 'owned abort signal attached');
}

function assertNoForbidden(forbidden) {
  assert.deepEqual(forbidden, {}, 'listsFetch/symbolsFetch/init must never be called');
}

const OWNED = 'u1';

// ---- scenarios ---------------------------------------------------------

const scenarios = [];
function scenario(name, body) { scenarios.push({ name, body }); }

scenario('enumerate lists: ready, id/name only, rows and list_id null', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  const client = fakeClient({
    watchlists: [
      { id: 'wl-2', user_id: OWNED, name: 'CPI board', position: 2, created_at: '2026-01-02T00:00:00Z' },
      { id: 'wl-1', user_id: OWNED, name: 'GDP board', position: 1, created_at: '2026-01-03T00:00:00Z' },
    ],
    watchlist_symbols: [],
  }, calls, forbidden);
  const { auth, state } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  const res = await fn({});
  assert.equal(res.state, 'ready');
  assert.equal(res.schema, 'watchlist_read.v1');
  assert.equal(res.authority, 'cloud');
  assert.equal(res.warning, null);
  assert.equal(res.owner_id, OWNED);
  assert.equal(res.rows, null);
  assert.equal(res.list_id, null);
  assert.ok(!Number.isNaN(Date.parse(res.last_good_at)), 'last_good_at is a timestamp');
  // The result is produced inside the VM context, so compare plain copies.
  const lists = JSON.parse(JSON.stringify(res.lists));
  assert.deepEqual(lists, [{ id: 'wl-1', name: 'GDP board' }, { id: 'wl-2', name: 'CPI board' }]);
  lists.forEach((l) => assert.deepEqual(Object.keys(l).sort(), ['id', 'name'], 'id/name only'));
  assert.equal(calls.length, 1);
  assertQuery(calls, 0, {
    table: 'watchlists', select: LIST_SELECT,
    eqs: [{ col: 'user_id', val: OWNED }], orders: ['position', 'created_at'], limit: 101,
  });
  assert.equal(state.getSessionCalls, 2, 'identity re-verified after the read');
  assert.equal(win.listeners.length, 0, 'listeners removed');
  assertNoForbidden(forbidden);
});

scenario('selected list: duplicate owner symbols deduped in order', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  const client = fakeClient({
    watchlists: [
      { id: 'wl-9', user_id: OWNED, name: 'Fed board', position: 0, created_at: '2026-01-01T00:00:00Z' },
      { id: 'wl-8', user_id: 'u2', name: 'Other user', position: 0, created_at: '2026-01-01T00:00:00Z' },
    ],
    watchlist_symbols: [
      { watchlist_id: 'wl-9', symbol: 'CPI', position: 3, created_at: '2026-01-01T02:00:00Z' },
      { watchlist_id: 'wl-9', symbol: 'FEDFUNDS', position: 1, created_at: '2026-01-01T03:00:00Z' },
      { watchlist_id: 'wl-9', symbol: 'CPI', position: 2, created_at: '2026-01-01T01:00:00Z' },
      { watchlist_id: 'wl-9', symbol: 'UNRATE', position: 4, created_at: '2026-01-01T05:00:00Z' },
      { watchlist_id: 'wl-9', symbol: 'T10YIE', position: 5, created_at: '2026-01-01T06:00:00Z' },
    ],
  }, calls, forbidden);
  const { auth, state } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  const res = await fn({ listId: 'wl-9' });
  assert.equal(res.state, 'ready');
  assert.equal(res.warning, null);
  assert.equal(res.owner_id, OWNED);
  assert.equal(res.list_id, 'wl-9');
  const lists = JSON.parse(JSON.stringify(res.lists));
  const rows = JSON.parse(JSON.stringify(res.rows));
  assert.deepEqual(lists, [{ id: 'wl-9', name: 'Fed board' }]);
  assert.deepEqual(rows,
    [{ symbol: 'FEDFUNDS' }, { symbol: 'CPI' }, { symbol: 'UNRATE' }, { symbol: 'T10YIE' }]);
  rows.forEach((r) => assert.deepEqual(Object.keys(r).sort(), ['symbol'], 'symbol only'));
  assert.equal(calls.length, 2);
  assertQuery(calls, 0, {
    table: 'watchlists', select: LIST_SELECT,
    eqs: [{ col: 'user_id', val: OWNED }, { col: 'id', val: 'wl-9' }], limit: 2,
  });
  assertQuery(calls, 1, {
    table: 'watchlist_symbols', select: SYMBOL_SELECT,
    eqs: [{ col: 'watchlist_id', val: 'wl-9' }], orders: ['position', 'created_at'], limit: 501,
  });
  assert.equal(state.getSessionCalls, 3, 'identity re-verified before publish');
  assertNoForbidden(forbidden);
});

scenario('selected list owned by another user is never enumerated or returned', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  const client = fakeClient({
    watchlists: [{ id: 'wl-9', user_id: 'u2', name: 'Private', position: 0, created_at: '2026-01-01T00:00:00Z' }],
    watchlist_symbols: [],
  }, calls, forbidden);
  const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  const res = await fn({ listId: 'wl-9' });
  assertError(res, 'list-not-found');
  assert.equal(calls.length, 1, 'symbols of a foreign list are never read');
  assertQuery(calls, 0, {
    table: 'watchlists', select: LIST_SELECT,
    eqs: [{ col: 'user_id', val: OWNED }, { col: 'id', val: 'wl-9' }], limit: 2,
  });
  assertNoForbidden(forbidden);
});

scenario('missing list refuses without reading symbols', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  const client = fakeClient({ watchlists: [], watchlist_symbols: [] }, calls, forbidden);
  const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  const res = await fn({ listId: 'wl-none' });
  assertError(res, 'list-not-found');
  assert.equal(calls.length, 1);
  assertNoForbidden(forbidden);
});

scenario('list overflow beyond 100 refuses as incomplete', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  const many = Array.from({ length: 120 }, (_, i) => ({
    id: 'wl-' + i, user_id: OWNED, name: 'L' + i, position: i, created_at: '2026-01-01T00:00:00Z',
  }));
  const client = fakeClient({ watchlists: many, watchlist_symbols: [] }, calls, forbidden);
  const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  const res = await fn({});
  assertError(res, 'incomplete-lists');
  assert.equal(calls.length, 1);
  assertQuery(calls, 0, {
    table: 'watchlists', select: LIST_SELECT,
    eqs: [{ col: 'user_id', val: OWNED }], orders: ['position', 'created_at'], limit: 101,
  });
  assertNoForbidden(forbidden);
});

scenario('lying totals refuse: lists and symbols count/data mismatch', async () => {
  // lists: server reports 5 total but returns 2 rows
  {
    const win = fakeWindow();
    const calls = [];
    const forbidden = {};
    const client = fakeClient({
      watchlists: {
        rows: [
          { id: 'wl-1', user_id: OWNED, name: 'A', position: 0, created_at: '2026-01-01T00:00:00Z' },
          { id: 'wl-2', user_id: OWNED, name: 'B', position: 1, created_at: '2026-01-01T00:00:01Z' },
        ],
        __count: 5,
      },
      watchlist_symbols: [],
    }, calls, forbidden);
    const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
    win.MDXAuth = auth;
    const fn = loadFn(win);
    assertError(await fn({}), 'incomplete-lists');
    assert.equal(calls.length, 1);
    assertNoForbidden(forbidden);
  }
  // symbols: server reports 1 total but returns 2 rows
  {
    const win = fakeWindow();
    const calls = [];
    const forbidden = {};
    const client = fakeClient({
      watchlists: [{ id: 'wl-9', user_id: OWNED, name: 'Fed', position: 0, created_at: '2026-01-01T00:00:00Z' }],
      watchlist_symbols: {
        rows: [
          { watchlist_id: 'wl-9', symbol: 'CPI', position: 1, created_at: '2026-01-01T00:00:00Z' },
          { watchlist_id: 'wl-9', symbol: 'UNRATE', position: 2, created_at: '2026-01-01T00:00:01Z' },
        ],
        __count: 1,
      },
    }, calls, forbidden);
    const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
    win.MDXAuth = auth;
    const fn = loadFn(win);
    assertError(await fn({ listId: 'wl-9' }), 'incomplete-symbols');
    assert.equal(calls.length, 2);
    assertNoForbidden(forbidden);
  }
});

scenario('symbol overflow beyond 500 refuses as incomplete', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  const many = Array.from({ length: 600 }, (_, i) => ({
    watchlist_id: 'wl-9', symbol: 'S' + i, position: i, created_at: '2026-01-01T00:00:00Z',
  }));
  const client = fakeClient({
    watchlists: [{ id: 'wl-9', user_id: OWNED, name: 'Fed', position: 0, created_at: '2026-01-01T00:00:00Z' }],
    watchlist_symbols: many,
  }, calls, forbidden);
  const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  const res = await fn({ listId: 'wl-9' });
  assertError(res, 'incomplete-symbols');
  assert.equal(calls.length, 2);
  assertQuery(calls, 1, {
    table: 'watchlist_symbols', select: SYMBOL_SELECT,
    eqs: [{ col: 'watchlist_id', val: 'wl-9' }], orders: ['position', 'created_at'], limit: 501,
  });
  assertNoForbidden(forbidden);
});

scenario('malformed or crossowner rows refuse', async () => {
  // (a) a crossowner list row leaks through a broken filter
  {
    const win = fakeWindow();
    const calls = [];
    const forbidden = {};
    const client = fakeClient({
      watchlists: {
        rows: [{ id: 'wl-1', user_id: 'u2', name: 'Injected', position: 0, created_at: '2026-01-01T00:00:00Z' }],
        __raw: true,
      },
      watchlist_symbols: [],
    }, calls, forbidden);
    const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
    win.MDXAuth = auth;
    const fn = loadFn(win);
    assertError(await fn({}), 'invalid-lists');
    assertNoForbidden(forbidden);
  }
  // (b) duplicate list ids refuse
  {
    const win = fakeWindow();
    const calls = [];
    const forbidden = {};
    const dup = (n) => ({ id: 'wl-1', user_id: OWNED, name: n, position: 0, created_at: '2026-01-01T00:00:00Z' });
    const client = fakeClient({ watchlists: { rows: [dup('A'), dup('B')], __raw: true }, watchlist_symbols: [] },
      calls, forbidden);
    const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
    win.MDXAuth = auth;
    const fn = loadFn(win);
    assertError(await fn({}), 'invalid-lists');
    assertNoForbidden(forbidden);
  }
  // (c) a symbol row pointing at another list refuses
  {
    const win = fakeWindow();
    const calls = [];
    const forbidden = {};
    const client = fakeClient({
      watchlists: [{ id: 'wl-9', user_id: OWNED, name: 'Fed', position: 0, created_at: '2026-01-01T00:00:00Z' }],
      watchlist_symbols: {
        rows: [{ watchlist_id: 'wl-other', symbol: 'CPI', position: 1, created_at: '2026-01-01T00:00:00Z' }],
        __raw: true,
      },
    }, calls, forbidden);
    const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
    win.MDXAuth = auth;
    const fn = loadFn(win);
    assertError(await fn({ listId: 'wl-9' }), 'invalid-symbols');
    assert.equal(calls.length, 2);
    assertNoForbidden(forbidden);
  }
});

scenario('canonical account changed while awaiting refuses before publish', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  const client = fakeClient({ watchlists: [], watchlist_symbols: [] }, calls, forbidden);
  // The first canonical check adopts u1; every later one sees u2.
  const { auth, state } = fakeAuth(client, { userId: OWNED, switchAfter: 1, switchTo: 'u2', tokens: ['t1'] });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  assertError(await fn({}), 'identity-changed');
  assert.equal(calls.length, 0, 'no query runs under a changed account');
  assert.equal(state.getSessionCalls, 0);
  assert.equal(win.listeners.length, 0);
  assertNoForbidden(forbidden);
});

scenario('token rotation during the read conservatively refuses', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  const client = fakeClient({
    watchlists: [{ id: 'wl-1', user_id: OWNED, name: 'A', position: 0, created_at: '2026-01-01T00:00:00Z' }],
    watchlist_symbols: [],
  }, calls, forbidden);
  const { auth, state } = fakeAuth(client, { userId: OWNED, tokens: ['t1', 't2'] });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  assertError(await fn({}), 'session-changed');
  assert.equal(calls.length, 1, 'the read completed but nothing was published');
  assert.equal(state.getSessionCalls, 2);
  assertNoForbidden(forbidden);
});

scenario('malformed signal refuses invalid-options and cleans partial setup', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  const client = fakeClient({ watchlists: [], watchlist_symbols: [] }, calls, forbidden);
  const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  assertError(await fn({ signal: { aborted: false } }), 'invalid-options'); // no add/removeEventListener
  assertError(await fn({ signal: 'abort' }), 'invalid-options');
  assert.equal(win.listeners.length, 0, 'no partial listeners left behind');
  assert.equal(calls.length, 0);
  assertNoForbidden(forbidden);
});

scenario('invalid listId shapes refuse invalid-options', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  const client = fakeClient({ watchlists: [], watchlist_symbols: [] }, calls, forbidden);
  const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  assertError(await fn({ listId: '' }), 'invalid-options');
  assertError(await fn({ listId: 7 }), 'invalid-options');
  assertError(await fn({ listId: 'x'.repeat(129) }), 'invalid-options');
  assert.equal(calls.length, 0);
  assertNoForbidden(forbidden);
});

scenario('caller abort before the read: cancelled, no query, listeners removed', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  const client = fakeClient({ watchlists: [], watchlist_symbols: [] }, calls, forbidden);
  const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'] });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  const ac = new AbortController();
  ac.abort();
  assertError(await fn({ signal: ac.signal }), 'cancelled');
  assert.equal(calls.length, 0);
  assert.equal(win.listeners.length, 0);
  assertNoForbidden(forbidden);
});

scenario('mdx-auth event stops a pending read with session-changed', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  let resolveClient;
  const clientPromise = new Promise((r) => { resolveClient = r; });
  const client = fakeClient({ watchlists: [], watchlist_symbols: [] }, calls, forbidden);
  const { auth } = fakeAuth(client, { userId: OWNED, tokens: ['t1'], clientFactory: () => clientPromise });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  const pending = fn({});
  await new Promise((r) => setImmediate(r)); // setup attaches its listeners
  assert.equal(win.listeners.length, 2, 'mdx-auth and pagehide listeners attached');
  win.emit('mdx-auth');
  assertError(await pending, 'session-changed');
  assert.equal(calls.length, 0);
  assert.equal(win.listeners.length, 0, 'listeners removed after stop');
  resolveClient(client); // let the abandoned read drain; the race already settled
  await new Promise((r) => setImmediate(r));
  assertNoForbidden(forbidden);
});

scenario('signed out refuses without any query', async () => {
  const win = fakeWindow();
  const calls = [];
  const forbidden = {};
  const client = fakeClient({ watchlists: [], watchlist_symbols: [] }, calls, forbidden);
  const { auth, state } = fakeAuth(client, { userId: null, tokens: ['t1'] });
  win.MDXAuth = auth;
  const fn = loadFn(win);
  assertError(await fn({}), 'signed-out');
  assertError(await fn({ listId: 'wl-1' }), 'signed-out');
  assert.equal(calls.length, 0);
  assert.equal(state.getSessionCalls, 0);
  assertNoForbidden(forbidden);
});


scenario('selected list probe must return the exact requested id before reading symbols', async () => {
  const win = fakeWindow(), calls = [], forbidden = {};
  const client = fakeClient({watchlists:{rows:[{id:'wrong-owned-list',user_id:OWNED,name:'Other',position:0,created_at:null}],__raw:true}}, calls, forbidden);
  const {auth} = fakeAuth(client, {userId:OWNED,tokens:['t1']}); win.MDXAuth=auth;
  assertError(await loadFn(win)({listId:'requested-list'}), 'list-not-found');
  assert.equal(calls.length,1); assert.equal(calls[0].table,'watchlists');
  assert.equal(win.listeners.length,0); assertNoForbidden(forbidden);
});

// ---- runner ------------------------------------------------------------

let failed = 0;
for (const s of scenarios) {
  try {
    await s.body();
    console.log('PASS  ' + s.name);
  } catch (e) {
    failed += 1;
    console.log('FAIL  ' + s.name + ' :: ' + (e && e.message));
  }
}
await new Promise((r) => setImmediate(r));
await new Promise((r) => setImmediate(r));
if (unhandled.length > 0) {
  failed += 1;
  console.log('FAIL  unhandled rejections: ' + unhandled.join(' | '));
}
console.log(failed === 0
  ? 'ALL PASS: ' + scenarios.length + ' scenarios; 0 unhandled rejections; '
    + 'no cache/sync/listsFetch/symbolsFetch/init calls; every query shape asserted'
  : 'FAILURES: ' + failed);
if (failed > 0) process.exitCode = 1;
