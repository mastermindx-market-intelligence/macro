/* Account condition transport. The existing alerts owner validates every write.
   No local persistence, activation, evaluator, queue or notification authority. */
(function (host, make) {
  "use strict";
  if (typeof module === "object" && module.exports) module.exports = make;
  else host.ForexWatchClient = make({
    auth: host.MDXAuth, getClient: host.getSupabaseClient, crypto: host.crypto
  });
})(typeof window === "undefined" ? globalThis : window, function (options) {
  "use strict";
  const auth = options.auth, getClient = options.getClient, listeners = new Set();
  const pairs = new Set(["EURUSD", "USDJPY", "AUDUSD", "GBPUSD", "USDCAD", "USDCHF", "USDMXN", "USDBRL", "USDCNH"]);
  const deadlineMs = options.deadlineMs || 12000;
  const uuid = value => typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
  let epoch = 0, userId = null, authStatus = "unavailable";
  function authState() { return { status: authStatus, userId, epoch }; }
  function onAuth(user, event) {
    const next = user && uuid(user.id) ? user.id : null;
    // The incumbent SDK confirms an existing session with SIGNED_IN on tab focus.
    // Only owner changes or an actual sign-out invalidate account-bound intents.
    const boundary = next !== userId || event === "SIGNED_OUT";
    const previousStatus = authStatus;
    if (boundary) epoch++;
    userId = next;
    authStatus = next ? "ready" : event === "SDK_FAILED" ? "unavailable" : "signed_out";
    if (boundary || previousStatus !== authStatus || event === "SDK_FAILED")
      listeners.forEach(listener => listener(authState()));
  }
  if (auth && typeof auth.enabled === "function" && auth.enabled() && typeof getClient === "function") {
    authStatus = "checking";
    const user = typeof auth.user === "function" ? auth.user() : null;
    if (user && uuid(user.id)) { userId = user.id; authStatus = "ready"; }
    if (typeof auth.onChange === "function") auth.onChange(onAuth);
    else authStatus = "unavailable";
  }
  function subscribeAuth(listener) {
    listeners.add(listener); listener(authState());
    return () => listeners.delete(listener);
  }
  function same(token) { return token.epoch === epoch && token.userId === userId && authStatus === "ready"; }
  async function timed(action) {
    let timer;
    try {
      return await Promise.race([Promise.resolve().then(action), new Promise((_, reject) => {
        timer = setTimeout(() => reject({ code: "client_deadline" }), deadlineMs);
      })]);
    } finally { clearTimeout(timer); }
  }
  function failure(error, write) {
    const message = error && typeof error.message === "string" ? error.message : "";
    const code = error && error.code;
    const known = {
      forex_watch_revision_conflict: "conflict", forex_watch_identity_conflict: "conflict",
      forex_watch_not_found: "not_found", forex_watch_invalid_condition: "invalid",
      forex_watch_invalid_request: "invalid", forex_watch_limit_reached: "limit",
      forex_watch_owner_changed: "session_changed", forex_watch_unauthenticated: "signed_out",
      forex_activation_unavailable: "unavailable"
    };
    if (known[message]) return { status: known[message], code: message };
    if (code === "PGRST202" || code === "42883") return { status: "unavailable", code: "owner_not_available" };
    if (code === "42501" || code === "PGRST301" || code === "PGRST302") return { status: "unavailable", code: "owner_access_unavailable" };
    return { status: write ? "unconfirmed" : "unavailable", code: code === "client_deadline" ? "timeout" : "owner_request_failed" };
  }
  async function scoped(action, write) {
    const token = { userId, epoch };
    if (!userId || authStatus !== "ready") return { status: authStatus, epoch };
    let client;
    try { client = await timed(() => getClient()); }
    catch (_) { return same(token) ? { status: "unavailable", code: "client_unavailable" } : { status: "session_changed" }; }
    if (!same(token)) return { status: "session_changed" };
    try {
      const result = await timed(() => action(client, token));
      return same(token) ? result : { status: "session_changed" };
    } catch (error) {
      return same(token) ? failure(error, write) : { status: "session_changed" };
    }
  }
  function canonicalRule(rule, future) {
    if (!rule || typeof rule !== "object" || !pairs.has(rule.pair) ||
        rule.kind !== "price_close" || rule.quote_basis !== "literal" ||
        rule.interval !== "4H" || rule.calendar !== "fx-utc-4h/v1" || rule.feed !== null ||
        !["lt", "lte", "gt", "gte"].includes(rule.operator) ||
        !Number.isFinite(rule.threshold) || rule.threshold <= 0 ||
        !Number.isInteger(rule.consecutive) || rule.consecutive < 1 || rule.consecutive > 10 ||
        typeof rule.expires_at !== "string" || !/Z$/.test(rule.expires_at)) return null;
    const expires = new Date(rule.expires_at);
    if (!Number.isFinite(expires.valueOf()) || (future && expires <= new Date())) return null;
    const origin = rule.origin_snapshot_id === undefined ? (rule.snapshot_id || null) : rule.origin_snapshot_id;
    if (origin !== null && (typeof origin !== "string" || !origin.trim() || origin.length > 256)) return null;
    return {
      kind: "price_close", pair: rule.pair, quote_basis: "literal", interval: "4H",
      calendar: "fx-utc-4h/v1", operator: rule.operator, threshold: rule.threshold,
      consecutive: rule.consecutive, expires_at: expires.toISOString(), feed: null,
      origin_snapshot_id: origin
    };
  }
  function rowValid(row, token) {
    const condition = row && row.condition;
    return row && uuid(row.id) && row.user_id === token.userId && row.active === false &&
      condition && condition.type === "forex_price_close" && condition.schema_version === 1 &&
      condition.condition_id === row.id && Number.isSafeInteger(condition.revision) && condition.revision > 0 &&
      row.symbol === condition.pair && canonicalRule(condition, false);
  }
  const columns = "id,user_id,symbol,condition,active,created_at";
  function query(client, token) {
    return client.from("alerts").select(columns).eq("user_id", token.userId).eq("condition->>type", "forex_price_close");
  }
  function list() {
    return scoped(async (client, token) => {
      const result = await query(client, token).order("created_at", { ascending: false }).limit(51);
      if (result.error) return failure(result.error, false);
      if (!Array.isArray(result.data) || result.data.length > 50 || !result.data.every(row => rowValid(row, token)))
        return { status: "unavailable", code: "invalid_owner_response" };
      return { status: "ready", rows: result.data };
    }, false);
  }
  function get(id) {
    if (!uuid(id)) return Promise.resolve({ status: "invalid" });
    return scoped(async (client, token) => {
      const result = await query(client, token).eq("id", id).limit(2);
      if (result.error) return failure(result.error, false);
      if (!Array.isArray(result.data) || result.data.length > 1 || (result.data[0] && (!rowValid(result.data[0], token) || result.data[0].id !== id)))
        return { status: "unavailable", code: "invalid_owner_response" };
      return { status: "ready", row: result.data[0] || null };
    }, false);
  }
  function sameRule(a, b) { return JSON.stringify(canonicalRule(a, false)) === JSON.stringify(canonicalRule(b, false)); }
  function requestCurrent(request) { return request.userId === userId && request.accountEpoch === epoch; }
  function save(request) {
    if (!requestCurrent(request)) return Promise.resolve({ status: "session_changed" });
    const rule = canonicalRule(request.rule, true);
    if (!uuid(request.id) || !Number.isSafeInteger(request.expectedRevision) || request.expectedRevision < 0 || !rule)
      return Promise.resolve({ status: "invalid" });
    return scoped(async (client, token) => {
      const result = await client.rpc("save_forex_watch", {
        p_id: request.id, p_expected_revision: request.expectedRevision,
        p_expected_user_id: token.userId, p_rule: rule
      });
      if (result.error) return failure(result.error, true);
      const row = Array.isArray(result.data) && result.data.length === 1 ? result.data[0] : result.data;
      if (!rowValid(row, token) || row.id !== request.id || !sameRule(row.condition, rule) ||
          ![request.expectedRevision || 1, request.expectedRevision + 1].includes(row.condition.revision))
        return { status: "unconfirmed", code: "invalid_owner_response", id: request.id };
      return { status: "saved", row };
    }, true);
  }
  function remove(request) {
    if (!requestCurrent(request)) return Promise.resolve({ status: "session_changed" });
    if (!uuid(request.id) || !Number.isSafeInteger(request.expectedRevision) || request.expectedRevision < 1)
      return Promise.resolve({ status: "invalid" });
    return scoped(async (client, token) => {
      const result = await client.rpc("delete_forex_watch", {
        p_id: request.id, p_expected_revision: request.expectedRevision, p_expected_user_id: token.userId
      });
      if (result.error) return failure(result.error, true);
      const value = result.data;
      if (!value || value.id !== request.id || typeof value.deleted !== "boolean")
        return { status: "unconfirmed", code: "invalid_owner_response", id: request.id };
      return { status: "deleted", id: request.id, existed: value.deleted };
    }, true);
  }
  async function reconcileSave(request) {
    if (!requestCurrent(request)) return { status: "session_changed" };
    const result = await get(request.id);
    if (!requestCurrent(request)) return { status: "session_changed" };
    if (result.status !== "ready") return result;
    if (result.row && sameRule(result.row.condition, request.rule) &&
        [request.expectedRevision || 1, request.expectedRevision + 1].includes(result.row.condition.revision))
      return { status: "saved", row: result.row, reconciled: true };
    if (result.row && result.row.condition.revision > request.expectedRevision)
      return { status: "conflict", code: "newer_revision" };
    return { status: "unconfirmed", id: request.id };
  }
  async function reconcileRemove(request) {
    if (!requestCurrent(request)) return { status: "session_changed" };
    const result = await get(request.id);
    if (!requestCurrent(request)) return { status: "session_changed" };
    if (result.status !== "ready") return result;
    return result.row ? { status: "unconfirmed", id: request.id } : { status: "deleted", id: request.id, reconciled: true };
  }
  function newId() {
    const crypto = options.crypto;
    if (!crypto) return null;
    if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
    if (typeof crypto.getRandomValues !== "function") return null;
    const bytes = new Uint8Array(16); crypto.getRandomValues(bytes);
    bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
    const hex = Array.from(bytes, value => value.toString(16).padStart(2, "0")).join("");
    return hex.slice(0,8) + "-" + hex.slice(8,12) + "-" + hex.slice(12,16) + "-" + hex.slice(16,20) + "-" + hex.slice(20);
  }
  return Object.freeze({ authState, subscribeAuth, list, get, save, remove, reconcileSave, reconcileRemove, newId });
});
