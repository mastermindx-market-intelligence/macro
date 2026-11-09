/* Synthetic test transport only. No production URL, key, cookie or account. */
(function () {
  "use strict";
  let user = { id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" };
  const subscribers = [];
  window.__fxHeldWrites = [];
  window.__fxHoldWrites = false;
  window.__fxAuth = { emit(id, event) {
    user = id ? { id } : null;
    subscribers.forEach(callback => callback(user, event || (id ? "SIGNED_IN" : "SIGNED_OUT")));
  }};
  window.MDXAuth = { enabled: () => true, user: () => user,
    onChange(callback) { subscribers.push(callback); callback(user, "INITIAL_SESSION"); },
    open() { window.__fxSignInOpened = true; } };
  const client = {
    from(table) {
      const filters = [];
      return { select() { return this; }, eq(key, value) { filters.push([key, value]); return this; },
        order() { return this; }, limit() { return this; },
        then(resolve, reject) {
          return window.__fxOwner({ kind: "read", table, filters, user: user && user.id }).then(resolve, reject);
        } };
    },
    async rpc(name, args) {
      const result = await window.__fxOwner({ kind: "rpc", name, args, user: user && user.id });
      if (window.__fxHoldWrites) return new Promise(resolve => window.__fxHeldWrites.push(() => resolve(result)));
      return result;
    }
  };
  window.getSupabaseClient = () => Promise.resolve(client);
})();