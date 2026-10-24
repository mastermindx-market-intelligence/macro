"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const create = require("../../templates/forex_watch_client.js");
const A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const ID = "11111111-1111-4111-8111-111111111111";
const clone = value => JSON.parse(JSON.stringify(value));
const rule = () => ({ kind: "price_close", pair: "USDJPY", quote_basis: "literal", interval: "4H",
  calendar: "fx-utc-4h/v1", operator: "lt", threshold: 145.6, consecutive: 2,
  expires_at: "2099-10-23T16:00:00.000Z", feed: null, origin_snapshot_id: "snapshot-one" });
function row(owner = A, revision = 1, changes = {}) {
  return { id: ID, user_id: owner, symbol: "USDJPY", active: false, created_at: "2026-10-21T11:00:00Z",
    condition: { ...rule(), type: "forex_price_close", schema_version: 1, condition_id: ID, revision, ...changes } };
}
function harness(options = {}) {
  let user = options.signedOut ? null : { id: A }, subscriber, queryResponse = { data: [], error: null };
  let rpcResponse = { data: row(), error: null }, clientCalls = 0;
  const calls = [];
  const auth = { enabled: () => true, user: () => user, onChange: cb => {
    subscriber = cb; cb(user, "INITIAL_SESSION");
  } };
  const client = {
    from(table) {
      const filters = [];
      const query = { select(value) { calls.push(["select", table, value]); return this; },
        eq(key, value) { filters.push([key, value]); return this; }, order() { return this; }, limit() { return this; },
        then(resolve, reject) {
          calls.push(["read", clone(filters)]);
          return Promise.resolve(typeof queryResponse === "function" ? queryResponse(filters) : queryResponse).then(resolve, reject);
        } };
      return query;
    },
    rpc(name, args) {
      calls.push(["rpc", name, clone(args)]);
      return typeof rpcResponse === "function" ? rpcResponse(name, args) : Promise.resolve(rpcResponse);
    }
  };
  const api = create({ auth, crypto: { randomUUID: () => ID }, deadlineMs: options.deadlineMs || 50,
    getClient: () => { clientCalls++; return options.getClient ? options.getClient(client) : Promise.resolve(client); } });
  return { api, calls, clientCalls: () => clientCalls,
    emit(next, event = "SIGNED_IN") { user = next ? { id: next } : null; subscriber(user, event); },
    reads(value) { queryResponse = value; }, writes(value) { rpcResponse = value; },
    request(changes = {}) { const account = api.authState(); return { id: ID, expectedRevision: 0,
      rule: rule(), userId: account.userId, accountEpoch: account.epoch, ...changes }; } };
}
test("signed-out state does not construct a client or attempt a write", async () => {
  const h = harness({ signedOut: true });
  assert.equal((await h.api.list()).status, "signed_out");
  assert.equal((await h.api.save(h.request())).status, "signed_out");
  assert.equal(h.clientCalls(), 0); assert.equal(h.calls.length, 0);
});
test("only an authoritative successful empty read is empty", async () => {
  const h = harness();
  assert.deepEqual(await h.api.list(), { status: "ready", rows: [] });
  h.reads({ data: null, error: { message: "read failed" } });
  const failed = await h.api.list();
  assert.equal(failed.status, "unavailable"); assert.equal(failed.rows, undefined);
  const read = h.calls.find(call => call[0] === "read");
  assert.deepEqual(read[1], [["user_id", A], ["condition->>type", "forex_price_close"]]);
});
test("foreign, active and malformed records are never rendered as saved inactive", async () => {
  for (const bad of [row(B), { ...row(), active: true }, row(A, 0), row(A, 1, { quote_basis: "inverse" }),
    row(A, 1, { feed: "unadmitted" }), { ...row(), symbol: "EURUSD" }, row(A, 1, { condition_id: B })]) {
    const h = harness(); h.reads({ data: [bad], error: null });
    assert.equal((await h.api.list()).status, "unavailable");
  }
});
test("save sends canonical fields and expected owner; only returned identity is saved", async () => {
  const h = harness(), request = h.request();
  request.rule.active = true; request.rule.saved = true; request.rule.admitted = true;
  const result = await h.api.save(request);
  assert.equal(result.status, "saved"); assert.equal(result.row.id, ID);
  const sent = h.calls.find(call => call[0] === "rpc");
  assert.equal(sent[1], "save_forex_watch");
  assert.equal(sent[2].p_expected_user_id, A);
  assert.equal(sent[2].p_expected_revision, 0);
  assert.deepEqual(sent[2].p_rule, rule());
});
test("invalid rules and stale local account intents make no mutation", async () => {
  const h = harness();
  for (const change of [{ threshold: NaN }, { threshold: 0 }, { feed: "made-up" },
    { quote_basis: "residual" }, { consecutive: 0 }, { expires_at: "2020-01-01T00:00:00Z" }]) {
    assert.equal((await h.api.save(h.request({ rule: { ...rule(), ...change } }))).status, "invalid");
  }
  const request = h.request(); h.emit(B);
  assert.equal((await h.api.save(request)).status, "session_changed");
  assert.equal(h.calls.filter(call => call[0] === "rpc").length, 0);
});
test("missing or mismatched mutation acknowledgments remain unconfirmed", async () => {
  for (const value of [null, [], row(A, 9), row(B), row(A, 1, { threshold: 144 })]) {
    const h = harness(); h.writes({ data: value, error: null });
    assert.equal((await h.api.save(h.request())).status, "unconfirmed");
    assert.equal(h.calls.filter(call => call[0] === "rpc").length, 1);
  }
});
test("revision conflict is disclosed without retry or overwrite", async () => {
  const h = harness(); h.writes({ data: null, error: { code: "P0001", message: "forex_watch_revision_conflict" } });
  assert.equal((await h.api.save(h.request({ expectedRevision: 1 }))).status, "conflict");
  assert.equal(h.calls.filter(call => call[0] === "rpc").length, 1);
  assert.equal(h.calls.filter(call => call[0] === "read").length, 0);
});
test("lost save response is reconciled by a read of the same identity, without replay", async () => {
  const h = harness(), request = h.request();
  h.writes(() => { h.reads({ data: [row()], error: null }); return Promise.reject(new Error("connection lost after commit")); });
  assert.equal((await h.api.save(request)).status, "unconfirmed");
  const result = await h.api.reconcileSave(request);
  assert.equal(result.status, "saved"); assert.equal(result.reconciled, true);
  assert.equal(h.calls.filter(call => call[0] === "rpc").length, 1);
  assert.ok(h.calls.find(call => call[0] === "read")[1].some(([key, value]) => key === "id" && value === ID));
});
test("an empty read cannot prove a timed-out save was never applied", async () => {
  const h = harness({ deadlineMs: 10 }), request = h.request();
  h.writes(() => new Promise(() => {}));
  assert.equal((await h.api.save(request)).status, "unconfirmed");
  assert.equal((await h.api.reconcileSave(request)).status, "unconfirmed");
  assert.equal(h.calls.filter(call => call[0] === "rpc").length, 1);
});
test("a deadline before client acquisition is unavailable and never writes", async () => {
  const h = harness({ deadlineMs: 10, getClient: () => new Promise(() => {}) });
  assert.equal((await h.api.save(h.request())).status, "unavailable");
  assert.equal(h.calls.length, 0);
});
test("same-user sign-out/sign-in invalidates a late save result", async () => {
  let resolve;
  const h = harness(), request = h.request();
  h.writes(() => new Promise(done => { resolve = done; }));
  const promise = h.api.save(request);
  await new Promise(done => setImmediate(done));
  h.emit(null, "SIGNED_OUT"); h.emit(A, "SIGNED_IN");
  resolve({ data: row(), error: null });
  const result = await promise;
  assert.deepEqual(result, { status: "session_changed" });
  assert.equal((await h.api.reconcileSave(request)).status, "session_changed");
});
test("account changes while loading the client prevent the mutation", async () => {
  let release;
  const h = harness({ getClient: client => new Promise(done => { release = () => done(client); }) });
  const pending = h.api.save(h.request());
  await new Promise(done => setImmediate(done)); h.emit(B); release();
  assert.equal((await pending).status, "session_changed");
  assert.equal(h.calls.filter(call => call[0] === "rpc").length, 0);
});
test("late token selection is fenced by expected owner sent to RPC", async () => {
  const h = harness();
  h.writes((_, args) => {
    assert.equal(args.p_expected_user_id, A);
    return Promise.resolve({ data: null, error: { code: "P0001", message: "forex_watch_owner_changed" } });
  });
  assert.equal((await h.api.save(h.request())).status, "session_changed");
});
test("late account read cannot reveal the preceding user's rows", async () => {
  let release;
  const h = harness(); h.reads(() => new Promise(done => { release = done; }));
  const promise = h.api.list();
  await new Promise(done => setImmediate(done)); h.emit(B);
  release({ data: [row()], error: null });
  assert.deepEqual(await promise, { status: "session_changed" });
});
test("deletion requires a revision and authoritative acknowledgment", async () => {
  const h = harness(), request = h.request({ expectedRevision: 2 });
  assert.equal((await h.api.remove(h.request())).status, "invalid");
  h.writes({ data: { id: ID, deleted: true }, error: null });
  assert.equal((await h.api.remove(request)).status, "deleted");
  const sent = h.calls.find(call => call[0] === "rpc");
  assert.deepEqual(sent.slice(1), ["delete_forex_watch", { p_id: ID, p_expected_revision: 2, p_expected_user_id: A }]);
  h.writes({ data: null, error: null });
  assert.equal((await h.api.remove(request)).status, "unconfirmed");
});
test("lost delete response is reconciled through absence without another write", async () => {
  const h = harness(), request = h.request({ expectedRevision: 1 });
  h.writes(() => Promise.reject(new Error("lost")));
  assert.equal((await h.api.remove(request)).status, "unconfirmed");
  const result = await h.api.reconcileRemove(request);
  assert.equal(result.status, "deleted"); assert.equal(result.reconciled, true);
  assert.equal(h.calls.filter(call => call[0] === "rpc").length, 1);
});
test("newer revision during reconciliation is conflict, never a successful save", async () => {
  const h = harness(), request = h.request({ expectedRevision: 1 });
  h.reads({ data: [row(A, 3, { threshold: 141 })], error: null });
  assert.equal((await h.api.reconcileSave(request)).status, "conflict");
});
test("an unapplied owner function is unavailable, not saved or an empty account", async () => {
  const h = harness(); h.writes({ data: null, error: { code: "PGRST202", message: "function absent" } });
  assert.equal((await h.api.save(h.request())).status, "unavailable");
});

test("routine same-account SIGNED_IN preserves the current intent and in-flight acknowledgment", async () => {
  const h = harness({ deadlineMs: 200 }), request = h.request();
  let acknowledge, started;
  const reachedOwner = new Promise(resolve => { started = resolve; });
  h.writes(() => { started(); return new Promise(resolve => { acknowledge = resolve; }); });
  const saving = h.api.save(request);
  await reachedOwner;
  h.emit(A, "SIGNED_IN");
  assert.equal(h.api.authState().epoch, request.accountEpoch);
  acknowledge({ data: row(), error: null });
  assert.equal((await saving).status, "saved");
  assert.equal(h.calls.filter(call => call[0] === "rpc").length, 1);
});
test("initial signed-out session resolution notifies an already-subscribed view", () => {
  let emit;
  const api = create({ auth: { enabled: () => true, user: () => null, onChange: cb => { emit = cb; } },
    getClient: () => { throw new Error("must not construct a client"); } });
  const states = [];
  api.subscribeAuth(state => states.push(state.status));
  emit(null, "INITIAL_SESSION");
  assert.deepEqual(states, ["checking", "signed_out"]);
});
