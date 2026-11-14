const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');

const source = fs.readFileSync(__dirname + '/earnings-wire.pinned.js', 'utf8');
const gitBlob = crypto.createHash('sha1').update(`blob ${Buffer.byteLength(source)}\0`).update(source).digest('hex');
assert.equal(gitBlob, '12216b31e5a747d959051ca2295bc690270335ac');
console.log('Source Macro fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9 templates/earnings_wire/earnings-wire.js');
console.log('Loaded source Git blob ' + gitBlob);
console.log('Probe boundary: source function execution with a synthetic DOM and auth/HTTP seam. No browser, private account or production API access.');

function makePage(initialUser) {
  const attributes = new Map();
  const listeners = new Map();
  const output = { facts: [], receipts: [], gateRemoved: false, fetches: [], errorMessages: [] };
  let user = initialUser;
  let resolveResponse;
  const responsePromise = new Promise(resolve => { resolveResponse = resolve; });
  const gate = { slug: 'aal-2026q3-call-record', payload: '/api/earnings/v1/records/aal-2026q3-call-record', preview: 2, locked: 10 };
  const signin = { hidden: true, addEventListener() {} };
  const document = {
    documentElement: {
      getAttribute: key => attributes.get(key),
      setAttribute: (key, value) => attributes.set(key, value),
      removeAttribute: key => attributes.delete(key),
    },
    getElementById(id) {
      if (id === 'earnings-gate-state') return { textContent: JSON.stringify(gate) };
      if (id === 'earnings-member-gate') return { remove() { output.gateRemoved = true; } };
      return null;
    },
    querySelector(selector) {
      if (selector === '.ewa-facts') return { insertAdjacentHTML: (where, html) => output.facts.push(html) };
      if (selector === '.ewa-receipts tbody') return { insertAdjacentHTML: (where, html) => output.receipts.push(html) };
      if (selector === '[data-earnings-signin]') return signin;
      return null;
    },
  };
  const window = {
    MDXAuth: {
      hasSession: () => Boolean(user),
      user: () => user,
      client: async () => ({ auth: { getSession: async () => ({ data: { session: user ? { access_token: 'fixture-token-' + user.id } : null } }) } }),
    },
    addEventListener(name, handler, options) {
      if (!listeners.has(name)) listeners.set(name, []);
      listeners.get(name).push({ handler, once: Boolean(options?.once) });
    },
  };
  const fetch = (url, options) => {
    output.fetches.push({ url, authorization: options.headers.Authorization });
    return responsePromise;
  };
  vm.runInNewContext(source, { window, document, fetch, location: {}, setTimeout: () => 1, Promise, JSON, Array, Error }, { timeout: 1000 });
  return {
    output,
    signin,
    attributes,
    auth(nextUser, event) {
      user = nextUser;
      const active = listeners.get('mdx-auth') || [];
      for (const entry of active) entry.handler({ detail: { user, event } });
      listeners.set('mdx-auth', active.filter(entry => !entry.once));
    },
    respond(payload, status = 200) {
      resolveResponse({ ok: status >= 200 && status < 300, status, json: async () => payload });
    },
  };
}

const settle = async () => { for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve)); };
const payload = (label = 'member excerpt') => ({ schema: 'earnings.tier_payload/v1', page: 'earnings_wire_article', slug: 'aal-2026q3-call-record', required_tier: 'essential', public_facts: 2, locked_facts: 10, facts_html: `<article>${label}</article>`, receipt_rows_html: '<tr><td>fixture receipt</td></tr>' });

(async () => {
  const afterSignout = makePage({ id: 'owner-A' });
  await settle();
  assert.equal(afterSignout.output.fetches.length, 1);
  afterSignout.auth(null, 'SIGNED_OUT');
  afterSignout.respond(payload());
  await settle();
  assert.equal(afterSignout.output.facts.length, 1);
  assert.equal(afterSignout.attributes.get('data-earnings-member'), 'unlocked');
  console.log('WITNESS 1: delayed A response inserted member HTML after SIGNED_OUT and set unlocked. Required owner fence would discard it.');

  const afterSwitch = makePage({ id: 'owner-A' });
  await settle();
  afterSwitch.auth({ id: 'owner-B' }, 'SIGNED_IN');
  afterSwitch.respond(payload('owner-A response'));
  await settle();
  assert.equal(afterSwitch.output.fetches[0].authorization, 'Bearer fixture-token-owner-A');
  assert.equal(afterSwitch.output.facts.length, 1);
  console.log('WITNESS 2: owner-A response inserted after owner-B became current. No second entitlement read occurred.');

  const signInLater = makePage(null);
  await settle();
  assert.equal(signInLater.signin.hidden, false);
  signInLater.auth({ id: 'owner-A' }, 'SIGNED_IN');
  await settle();
  assert.equal(signInLater.output.fetches.length, 0);
  console.log('WITNESS 3: initial guest then same-document SIGNED_IN performs zero member fetches. The one-shot loader does not resume.');

  const afterHydration = makePage({ id: 'owner-A' });
  await settle();
  afterHydration.respond(payload());
  await settle();
  afterHydration.auth(null, 'SIGNED_OUT');
  await settle();
  assert.equal(afterHydration.output.facts.length, 1);
  assert.equal(afterHydration.output.gateRemoved, true);
  assert.equal(afterHydration.attributes.get('data-earnings-member'), 'unlocked');
  console.log('WITNESS 4: this article module retains already-hydrated member markup after SIGNED_OUT. The public-auth owner emits the event without reloading.');

  for (const status of [401, 403, 404, 429, 503]) {
    const failure = makePage({ id: 'owner-A' });
    await settle();
    failure.respond(null, status);
    await settle();
    assert.equal(failure.output.facts.length, 0);
    assert.equal(failure.signin.hidden, true);
    assert.equal(failure.output.gateRemoved, false);
  }
  console.log('WITNESS 5: 401/403/404/429/503 share the same signed-in gate outcome. No status-specific recovery is rendered by this module.');

  const newerContinuation = makePage({ id: 'owner-A' });
  await settle();
  newerContinuation.respond({ ...payload('newer same-slug continuation'), locked_facts: 11 });
  await settle();
  assert.equal(newerContinuation.output.facts.length, 1);
  assert.equal(newerContinuation.output.gateRemoved, true);
  console.log('WITNESS 6: same-slug payload with 11 member facts was accepted against a shell advertising 10. Current client/schema has no document revision or generation comparison. This proves guard absence, not a served mixed-generation incident.');
  console.log('6/6 source witnesses reproduced. These are defect/contract witnesses, not passing product acceptance.');
})().catch(error => { console.error(error); process.exitCode = 1; });
