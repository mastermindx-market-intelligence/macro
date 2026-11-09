'use strict';
/* P15.T2.S3 — options selection question lane in templates/mm_brain.js.
 *
 * Node built-in test + vm only (no package installs). The EXTRACTED module
 * block (BEGIN/END "options question module (P15.T2.S3)") is evaluated in a
 * bare context with only TextEncoder/Promise injected, so the real shipped
 * code is exercised against injected host seams: principal, streaming,
 * authorize, transport, onStagedChange, onOutcome. DOM/browser behaviour is
 * covered by the parent's own DOM tests; this file owns the bounded state
 * machine: envelope validation, freeze/immutability, identity matching,
 * staging refusals, the async withdrawal/principal fence, one-POST semantics,
 * SSE outcome classification, and the no-retry/no-persistence guarantees.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const WIDGET = path.join(__dirname, '..', '..', 'templates', 'mm_brain.js');
const source = fs.readFileSync(WIDGET, 'utf8');
const beginMarker = '/* ══ BEGIN options question module (P15.T2.S3)';
const endMarker = '/* ══ END options question module (P15.T2.S3) ══ */';
const start = source.indexOf(beginMarker);
const end = source.indexOf(endMarker);
assert.ok(start >= 0, 'options question module BEGIN marker not found');
assert.ok(end > start, 'options question module END marker not found');
const moduleSource = source.slice(start, end + endMarker.length);

const sandbox = { TextEncoder };
vm.createContext(sandbox);
vm.runInContext(moduleSource, sandbox, { filename: 'mm_brain.options_question.extract.js' });
const createOptionsQuestion = sandbox.createOptionsQuestion;
const canonicalEnvelope = sandbox.canonicalEnvelope;
const validateOptionsQuestionReference = sandbox.validateOptionsQuestionReference;
const settleQuestionResponse = sandbox.settleQuestionResponse;
assert.equal(typeof createOptionsQuestion, 'function', 'factory not extracted');
assert.equal(typeof settleQuestionResponse, 'function', 'SSE classifier not extracted');

const SHA = 'a'.repeat(64);
function validReference() {
  return {
    schema: 'options.selection_question/v1',
    evidence: {
      owner: 'options_evidence',
      object_type: 'options_matrix_selection',
      object_id: 'v1/AAPL/2026-11-04/2026-12-18,call,250.5/',
      mode: 'pinned',
      version_ref: 'sha256:' + SHA + ':bytes:1024:session:2026-11-04',
      fingerprint: SHA
    },
    selection: '{"schema":"options_matrix_selection.v1"}'
  };
}

/* One send's async chain (authorize -> transport) settles over macrotasks. */
async function settle(turns) {
  for (let i = 0; i < (turns || 4); i++) await new Promise(r => setImmediate(r));
}

function makeEnv(overrides) {
  const calls = { transport: [], authorize: 0, outcomes: [], stagedChanges: [], threadWrites: 0 };
  const env = {
    principal: () => 'user-A',
    streaming: () => false,
    maxMessage: 2000,
    lane: () => 'fast',
    lang: () => 'en',
    authorize: () => { calls.authorize++; return Promise.resolve({ 'Content-Type': 'application/json' }); },
    transport: () => Promise.resolve({
      ok: true, status: 200,
      bodyText: 'data: {"type":"meta"}\n\ndata: {"type":"delta","text":"ok"}\n\ndata: {"type":"done"}\n\n'
    }),
    onStagedChange: s => calls.stagedChanges.push(s),
    onOutcome: o => calls.outcomes.push(o),
    setThreadId: () => { calls.threadWrites++; },
    __calls: calls
  };
  Object.assign(env, overrides || {});
  /* Every read of env.transport yields a recording wrapper around the CURRENT
     impl, so tests may reassign the seam and the POST count stays truthful. */
  let transportImpl = env.transport;
  Object.defineProperty(env, 'transport', {
    configurable: true,
    get: () => init => { calls.transport.push(init); return transportImpl(init); },
    set: v => { transportImpl = v; }
  });
  return env;
}

function sseDoc(lines) { return lines.join('\n') + '\n\n'; }

/* ── identity ── */
test('canonical identity is exact sorted-key JSON of the envelope', () => {
  const ref = { selection: 's', schema: 'options.selection_question/v1', evidence: { b: '2', a: '1' } };
  assert.equal(canonicalEnvelope(ref),
    '{"evidence":{"a":"1","b":"2"},"schema":"options.selection_question/v1","selection":"s"}');
  assert.equal(canonicalEnvelope(validReference()), canonicalEnvelope(validReference()));
});

/* ── envelope validation ── */
test('closed envelope accepts the exact shape and a 2048-byte selection', () => {
  assert.equal(validateOptionsQuestionReference(validReference()), true);
  const big = Object.assign(validReference(), {});
  big.selection = 'x'.repeat(2048);
  assert.equal(validateOptionsQuestionReference(big), true, '2048-byte selection is the boundary');
});

test('malformed envelopes refuse: extra keys, wrong schema, wrong types, oversize', () => {
  const base = validReference();
  const extra = Object.assign({}, base, { thread_id: 't1' });
  assert.equal(validateOptionsQuestionReference(extra), false, 'extra envelope key');
  assert.equal(validateOptionsQuestionReference({ schema: 'options.selection_question/v1', evidence: {} }), false, 'missing key');
  assert.equal(validateOptionsQuestionReference(Object.assign({}, base, { schema: 'other/v1' })), false, 'wrong schema');
  assert.equal(validateOptionsQuestionReference(Object.assign({}, base, { selection: 5 })), false, 'selection not a string');
  assert.equal(validateOptionsQuestionReference(Object.assign({}, base, { selection: '   ' })), false, 'blank selection');
  const oversize = Object.assign({}, base, { selection: 'x'.repeat(2049) });
  assert.equal(validateOptionsQuestionReference(oversize), false, 'oversize selection');
  const badEvidence = Object.assign({}, base, { evidence: [] });
  assert.equal(validateOptionsQuestionReference(badEvidence), false, 'evidence array');
  const nested = Object.assign({}, base, { evidence: { ok: '1', deep: { no: '2' } } });
  assert.equal(validateOptionsQuestionReference(nested), false, 'nested evidence object');
  assert.equal(validateOptionsQuestionReference('options.selection_question/v1'), false, 'string input');
  assert.equal(validateOptionsQuestionReference(null), false, 'null input');
});

/* ── staging: copy, freeze, refusals ── */
test('stage freezes an exact copy; caller mutation cannot change the send', async () => {
  const sentBodies = [];
  const env = makeEnv({
    transport: init => {
      sentBodies.push(init.body);
      return Promise.resolve({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"done"}']) });
    }
  });
  const c = createOptionsQuestion(env);
  const ref = validReference();
  assert.equal(c.stage(ref), true);
  const staged = c.staged();
  assert.equal(Object.isFrozen(staged.reference), true, 'reference frozen');
  assert.equal(Object.isFrozen(staged.reference.evidence), true, 'evidence frozen');
  ref.selection = 'mutated by caller';
  ref.evidence.object_id = 'v1/EVIL';
  ref.extra = 'late key';
  assert.equal(c.staged().reference.selection, '{"schema":"options_matrix_selection.v1"}', 'selection immutable');
  assert.equal(c.staged().identity, canonicalEnvelope(validReference()), 'identity immutable');
  assert.equal(c.send('what does this selection say?'), true);
  await settle();
  const sent = JSON.parse(sentBodies[0]);
  assert.deepEqual(sent.options_question_reference, JSON.parse(canonicalEnvelope(validReference())),
    'the exact staged reference rode the wire, not the mutated caller object');
  assert.notEqual(sent.options_question_reference.selection, 'mutated by caller');
});

test('stage refuses: streaming, signed out/principal unknown, busy, malformed', () => {
  let streaming = true;
  const env = makeEnv({ streaming: () => streaming });
  const c = createOptionsQuestion(env);
  assert.equal(c.stage(validReference()), false, 'streaming refusal');
  streaming = false;
  assert.equal(c.stage(validReference()), true);
  let busy = c.busy();
  assert.equal(busy, false);
  const signedOut = makeEnv({ principal: () => null });
  const c2 = createOptionsQuestion(signedOut);
  assert.equal(c2.stage(validReference()), false, 'signed-out refusal');
  assert.equal(c2.staged(), null);
  assert.equal(signedOut.__calls.transport.length, 0, 'zero transport effects');
});

/* ── clear: identity + ownership ── */
test('cyclic input refuses instead of throwing', () => {
  const env = makeEnv();
  const c = createOptionsQuestion(env);
  const cyclic = validReference();
  cyclic.evidence.self = cyclic.evidence;
  assert.doesNotThrow(() => c.stage(cyclic), 'stage must not throw on a cyclic reference');
  assert.equal(c.stage(cyclic), false, 'cyclic reference refused');
  assert.equal(c.staged(), null);
  assert.equal(env.__calls.transport.length, 0, 'zero transport effects');
});

test('same-reference clear succeeds; older holder cannot clear a newer stage', () => {
  const env = makeEnv();
  const c = createOptionsQuestion(env);
  const a = validReference();
  assert.equal(c.stage(a), true);
  const aPrime = validReference();            // equal content, different object
  assert.equal(c.clear(aPrime), true, 'identity matching, not object identity');
  assert.equal(c.staged(), null);
  assert.equal(c.clear(aPrime), false, 'nothing left to clear');

  const newer = validReference();
  newer.selection = '{"schema":"options_matrix_selection.v1","v":2}';
  assert.equal(c.stage(a), true);
  assert.equal(c.stage(newer), true, 'fresh explicit re-stage replaces the old one');
  assert.equal(c.clear(a), false, 'older holder cannot clear the newer staged reference');
  assert.equal(c.clear(newer), true);
});

test('clear requires the current principal; principal change cleared it already', () => {
  let owner = 'user-A';
  const env = makeEnv({ principal: () => owner });
  const c = createOptionsQuestion(env);
  assert.equal(c.stage(validReference()), true);
  owner = 'user-B';
  assert.equal(c.clear(validReference()), false, 'another principal cannot clear');
  owner = 'user-A';
  assert.equal(c.clear(validReference()), true, 'owner clears own stage');
  owner = null;
  assert.equal(c.clear(validReference()), false, 'signed out cannot clear');
});

/* ── no automatic send; one explicit POST; exact body ── */
test('staging alone sends nothing; explicit send posts exactly once', async () => {
  const env = makeEnv();
  const c = createOptionsQuestion(env);
  assert.equal(c.stage(validReference()), true);
  await settle();
  assert.equal(env.__calls.authorize, 0, 'no auth work on stage');
  assert.equal(env.__calls.transport.length, 0, 'no automatic send');

  const captured = [];
  const env2 = makeEnv({
    transport: init => { captured.push(init); return Promise.resolve({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"done"}']) }); }
  });
  const c2 = createOptionsQuestion(env2);
  c2.stage(validReference());
  assert.equal(c2.send('Read this selection for me.'), true);
  await settle();
  assert.equal(env2.__calls.authorize, 1);
  assert.equal(captured.length, 1, 'exactly one POST');
  const body = JSON.parse(captured[0].body);
  assert.deepEqual(Object.keys(body).sort(),
    ['context', 'lane', 'message', 'mode', 'options_question_reference'], 'exact body key set');
  assert.equal(body.message, 'Read this selection for me.');
  assert.equal(body.lane, 'fast');
  assert.equal(body.mode, 'chat');
  assert.deepEqual(body.context, { lang: 'en' }, 'language context only');
  assert.deepEqual(body.options_question_reference, JSON.parse(canonicalEnvelope(validReference())));
  const raw = captured[0].body;
  for (const forbidden of ['thread_id', '"images"', 'company_source_span', 'history', 'ai_context', 'tools', 'research']) {
    assert.ok(!raw.includes(forbidden), 'body must not carry ' + forbidden);
  }
  assert.equal(c2.staged(), null, 'staged reference consumed');
  assert.equal(c2.send('again'), false, 'second question needs fresh staging');
  await settle();
  assert.equal(captured.length, 1, 'still exactly one POST');
  assert.equal(env2.__calls.threadWrites, 0, 'no thread write seam ever touched');
});

test('transport observes the staged reference already consumed (before first attempt)', async () => {
  const env = makeEnv();
  const c = createOptionsQuestion(env);
  let seenAtTransport = 'unset';
  env.transport = () => { seenAtTransport = c.staged(); return Promise.resolve({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"done"}']) }); };
  c.stage(validReference());
  assert.equal(c.send('q'), true);
  await settle();
  assert.equal(seenAtTransport, null, 'consume happens BEFORE the first transport attempt');
  assert.equal(env.__calls.outcomes[0].kind, 'reply');
});

test('message cap: 2000 characters ride, 2001 refuse with zero POST', async () => {
  const captured = [];
  const env = makeEnv({
    transport: init => { captured.push(init); return Promise.resolve({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"done"}']) }); }
  });
  const c = createOptionsQuestion(env);
  c.stage(validReference());
  assert.equal(c.send('x'.repeat(2001)), false, 'over-cap refused');
  await settle();
  assert.equal(captured.length, 0, 'zero POST on over-cap');
  assert.equal(c.staged() && c.staged().identity, canonicalEnvelope(validReference()), 'stage kept');
  assert.equal(c.send('x'.repeat(2000)), true, 'at-cap accepted');
  await settle();
  assert.equal(captured.length, 1);
  assert.equal(JSON.parse(captured[0].body).message.length, 2000);
});

/* ── auth fences ── */
test('absent auth: stage and send both refuse with zero transport effects', async () => {
  const env = makeEnv({ principal: () => null });
  const c = createOptionsQuestion(env);
  assert.equal(c.stage(validReference()), false);
  assert.equal(c.send('q'), false);
  await settle();
  assert.equal(env.__calls.authorize, 0);
  assert.equal(env.__calls.transport.length, 0, 'zero POST without a principal');
});

test('withdrawal during the async auth fence aborts BEFORE the send', async () => {
  let releaseAuth;
  const captured = [];
  const env = makeEnv({
    authorize: () => new Promise(resolve => { releaseAuth = resolve; }),
    transport: init => { captured.push(init); return Promise.resolve({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"done"}']) }); }
  });
  const c = createOptionsQuestion(env);
  const ref = validReference();
  assert.equal(c.stage(ref), true);
  assert.equal(c.send('q'), true, 'explicit send accepted');
  assert.equal(c.clear(ref), true, 'withdrawal while auth is in flight');
  releaseAuth({ 'Content-Type': 'application/json' });
  await settle();
  assert.equal(captured.length, 0, 'zero POST after withdrawal');
  const outcomes = env.__calls.outcomes;
  assert.equal(outcomes.length, 1);
  assert.equal(outcomes[0].kind, 'withdrawn');
  assert.equal(env.__calls.threadWrites, 0);
});

test('principal change during the async auth fence aborts BEFORE the send', async () => {
  let owner = 'user-A';
  let releaseAuth;
  const captured = [];
  const env = makeEnv({
    principal: () => owner,
    authorize: () => new Promise(resolve => { releaseAuth = resolve; }),
    transport: init => { captured.push(init); return Promise.resolve({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"done"}']) }); }
  });
  const c = createOptionsQuestion(env);
  assert.equal(c.stage(validReference()), true);
  assert.equal(c.send('q'), true);
  owner = 'user-B';
  releaseAuth({ 'Content-Type': 'application/json' });
  await settle();
  assert.equal(captured.length, 0, 'zero POST on stale principal');
  assert.equal(env.__calls.outcomes[0].kind, 'withdrawn');
});

test('reset() during the auth fence aborts, bumps the generation, and fences late outcomes', async () => {
  let releaseAuth;
  const captured = [];
  const env = makeEnv({
    authorize: () => new Promise(resolve => { releaseAuth = resolve; }),
    transport: init => { captured.push(init); return Promise.resolve({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"done"}']) }); }
  });
  const c = createOptionsQuestion(env);
  const before = c.generation();
  assert.equal(c.stage(validReference()), true);
  assert.equal(c.send('q'), true);
  c.reset();
  assert.equal(c.generation(), before + 2, 'stage and reset advance generation');
  assert.equal(c.staged(), null, 'principal change cleared the stage');
  releaseAuth({ 'Content-Type': 'application/json' });
  await settle();
  assert.equal(captured.length, 0, 'zero POST after reset');
  const outcome = env.__calls.outcomes[0];
  assert.equal(outcome.kind, 'withdrawn');
  assert.equal(outcome.generation, before + 1, 'late outcome carries the stale generation so the widget can drop it');
});

/* ── SSE outcomes ── */
async function runSend(env, c, bodyText, ok) {
  env.transport = () => Promise.resolve({ ok: ok !== false, status: 200, bodyText: bodyText });
  c.stage(validReference());
  assert.equal(c.send('q'), true);
  await settle();
  return env.__calls.outcomes[0];
}

test('successful SSE: deltas concatenate in order, meta ignored, no thread adoption', async () => {
  const env = makeEnv();
  const c = createOptionsQuestion(env);
  const bodyText = sseDoc([
    'data: {"type":"meta","thread_id":"thr_123"}',
    '',
    'data: {"type":"delta","text":"Hel"}',
    'data: {"type":"delta","text":"lo"}',
    '',
    'data: {"type":"done"}'
  ]);
  const outcome = await runSend(env, c, bodyText);
  assert.equal(outcome.kind, 'reply');
  assert.equal(outcome.text, 'Hello');
  assert.equal(outcome.retryAllowed, undefined, 'no retry semantics on success');
  assert.equal(env.__calls.threadWrites, 0, 'thread id from meta never adopted');
  assert.equal(env.__calls.transport.length, 1);
});

test('server refusal (options_question_unavailable) classifies as refused, no downgrade', async () => {
  const env = makeEnv();
  const c = createOptionsQuestion(env);
  const bodyText = sseDoc([
    'data: {"type":"delta","text":"partial"}',
    'data: {"type":"done","error":{"reason":"options_question_unavailable","retry_allowed":false}}'
  ]);
  const outcome = await runSend(env, c, bodyText);
  assert.equal(outcome.kind, 'refused');
  assert.equal(outcome.reason, 'options_question_unavailable');
  assert.equal(env.__calls.transport.length, 1, 'exactly one attempt, no fallback send');
});

test('EFFECT_UNKNOWN arrives as done(error, effect_unknown, retry_allowed=false)', async () => {
  const env = makeEnv();
  const c = createOptionsQuestion(env);
  const bodyText = sseDoc([
    'data: {"type":"done","error":{"effect":"effect_unknown","retry_allowed":false}}'
  ]);
  const outcome = await runSend(env, c, bodyText);
  assert.equal(outcome.kind, 'unknown');
  assert.equal(outcome.retryAllowed, false);
  assert.equal(env.__calls.transport.length, 1, 'no retry after effect_unknown');
});

test('standalone error event classifies; unknown effect stays unknown', async () => {
  const env = makeEnv();
  const c = createOptionsQuestion(env);
  const outcome = await runSend(env, c,
    sseDoc(['data: {"type":"error","effect":"effect_unknown","retry_allowed":false}']));
  assert.equal(outcome.kind, 'unknown');
  assert.equal(outcome.retryAllowed, false);
});

test('network failure: rejected transport -> network outcome, exactly one attempt', async () => {
  const env = makeEnv({ transport: () => Promise.reject(new Error('socket dropped')) });
  const c = createOptionsQuestion(env);
  const outcome = await (async () => {
    c.stage(validReference());
    assert.equal(c.send('q'), true);
    await settle();
    return env.__calls.outcomes[0];
  })();
  assert.equal(outcome.kind, 'network');
  assert.equal(env.__calls.transport.length, 1, 'no retry');
  assert.equal(env.__calls.authorize, 1, 'no second auth round');
});

test('non-OK transport response and truncated streams classify as network, never an answer', async () => {
  let mode = 'status';
  const env = makeEnv({
    transport: () => Promise.resolve(mode === 'status'
      ? { ok: false, status: 502, bodyText: '' }
      : { ok: true, status: 200, bodyText: 'data: {"type":"delta","text":"half a sent"}' })
  });
  const c = createOptionsQuestion(env);
  c.stage(validReference());
  assert.equal(c.send('q'), true);
  await settle();
  assert.equal(env.__calls.outcomes[0].kind, 'network');
  assert.equal(env.__calls.transport.length, 1, 'no automatic retry on bad status');

  mode = 'truncated';
  assert.equal(c.stage(validReference()), true, 'fresh staging for the next explicit question');
  assert.equal(c.send('q2'), true);
  await settle();
  assert.equal(env.__calls.outcomes[1].kind, 'network', 'stream without done is a dropped connection');
  assert.equal(env.__calls.transport.length, 2, 'still one attempt per explicit send');
});

test('malformed SSE lines refuse even with a well-formed done', async () => {
  const env = makeEnv();
  const c = createOptionsQuestion(env);
  const bodyText = 'data: not-json\n\n: comment\n\ndata: [1,2]\n\ndata: {"type":"delta","text":"fine"}\n\ndata: {"type":"done"}\n\n';
  const outcome = await runSend(env, c, bodyText);
  assert.equal(outcome.kind, 'network');
  assert.equal(outcome.text, undefined);
});

test('authorize failure produces no POST and keeps the stage for an explicit retry', async () => {
  const captured = [];
  const env = makeEnv({
    authorize: () => Promise.reject(new Error('no session')),
    transport: init => { captured.push(init); return Promise.resolve({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"done"}']) }); }
  });
  const c = createOptionsQuestion(env);
  c.stage(validReference());
  assert.equal(c.send('q'), true);
  await settle();
  assert.equal(captured.length, 0, 'zero POST when auth fails');
  assert.equal(env.__calls.outcomes[0].kind, 'network');
  assert.ok(c.staged(), 'stage survives for an explicit user retry');
  env.authorize = () => Promise.resolve({ 'Content-Type': 'application/json' });
  assert.equal(c.send('q'), true, 'only an explicit second send goes out');
  await settle();
  assert.equal(captured.length, 1, 'the retry is the only other POST');
  assert.equal(env.__calls.outcomes.length, 2);
  assert.equal(env.__calls.outcomes[1].kind, 'reply');
});

/* ── ordinary-path guarantees ── */
test('without a staged reference the module sends nothing (ordinary path untouched)', async () => {
  const env = makeEnv();
  const c = createOptionsQuestion(env);
  assert.equal(c.send('plain question'), false);
  await settle();
  assert.equal(env.__calls.authorize, 0);
  assert.equal(env.__calls.transport.length, 0);
  assert.equal(env.__calls.outcomes.length, 0);
});

test('module never touches thread/run/regenerate state (structural guard)', () => {
  for (const token of ['thread_id', 'threadId', 'saveRun', 'loadRun', 'clearRun', 'recover(', 'localStorage',
    'sessionStorage', 'regenerate', 'lastTurn', 'fetch(', 'XMLHttpRequest']) {
    assert.ok(!moduleSource.includes(token), 'extracted module must not reference ' + token);
  }
});

/* ── settleQuestionResponse unit surface ── */
test('settleQuestionResponse unit cases', () => {
  assert.equal(settleQuestionResponse(null).kind, 'network');
  assert.equal(settleQuestionResponse({ ok: false, bodyText: '' }).kind, 'network');
  assert.equal(settleQuestionResponse({ ok: true }).kind, 'network');
  assert.equal(settleQuestionResponse({ ok: true, bodyText: '' }).kind, 'network');
  assert.equal(settleQuestionResponse({ ok: true, bodyText: 'data: {"type":"done"}' }).kind, 'reply');
  assert.deepEqual(settleQuestionResponse({ ok: true, bodyText: 'data: {"type":"done"}' }),
    { kind: 'reply', text: '' });
  const refused = settleQuestionResponse({
    ok: true, bodyText: 'data: {"type":"done","error":{"reason":"membership_required"}}'
  });
  assert.equal(refused.kind, 'refused');
  assert.equal(refused.reason, 'membership_required');
});


test('consumed request settles without falsely claiming withdrawal', async () => {
  let finish; const env=makeEnv({transport:()=>new Promise(r=>finish=r)}), c=createOptionsQuestion(env), r=validReference();
  c.stage(r); c.send('q'); await settle();
  assert.equal(c.clear(r),false); const nextGen=c.generation();
  finish({ok:true,status:200,bodyText:'data: {"type":"done","ok":true}\n\n'}); await settle();
  assert.equal(c.busy(),false); assert.equal(env.__calls.outcomes[0].generation,nextGen);
  assert.equal(c.active(),true); assert.equal(c.send('no generic retry'),false);
});
test('an old principal completion cannot unlock a newer flight', async () => {
  const finishes=[]; const env=makeEnv({transport:()=>new Promise(r=>finishes.push(r))}), c=createOptionsQuestion(env);
  c.stage(validReference()); c.send('old'); await settle(); c.reset();
  c.stage(validReference()); c.send('new'); await settle();
  finishes[0]({ok:true,bodyText:'data: {"type":"done"}\n\n'}); await settle();
  assert.equal(c.busy(),true);
  finishes[1]({ok:true,bodyText:'data: {"type":"done"}\n\n'}); await settle();assert.equal(c.busy(),false);
});
test('actual gateway unknown and quota refusal cannot become successful answers',()=>{
  assert.equal(settleQuestionResponse({ok:true,bodyText:'data: {"type":"done","error":"options_question_dispatch_effect_unknown","dispatch_state":"EFFECT_UNKNOWN","retry_allowed":false}\n\n'}).kind,'unknown');
  assert.equal(settleQuestionResponse({ok:true,bodyText:'data: {"type":"done","quota_exhausted":true}\n\n'}).kind,'refused');
});

/* Independent review7292 counterexamples: exact source, inert transport only. */
test('review: a consumed selector cannot be reported as withdrawn', async () => {
  let finish; const env=makeEnv({transport:()=>new Promise(r=>finish=r)}), c=createOptionsQuestion(env), ref=validReference();
  c.stage(ref); c.send('q'); await settle(); const gen=c.generation();
  assert.equal(c.clear(ref),false); assert.equal(c.generation(),gen);
  finish({ok:true,bodyText:'data: {"type":"delta","text":"committed answer"}\n\ndata: {"type":"done"}\n\n'});
  await settle(); assert.equal(env.__calls.transport.length,1);
  assert.equal(env.__calls.outcomes[0].generation,c.generation());
});
test('review: snapshot is copied once before validation and identity', async () => {
  const ref=validReference(), good=ref.evidence; let reads=0;
  Object.defineProperty(ref,'evidence',{enumerable:true,get(){ reads++; return reads<4?good:{nested:{admin:true},object_id:'other-account'}; }});
  const env=makeEnv(), c=createOptionsQuestion(env); assert.equal(c.stage(ref),true); c.send('q'); await settle();
  assert.deepEqual(JSON.parse(env.__calls.transport[0].body).options_question_reference.evidence,good);
  assert.equal(reads,1);
});
test('review: pending withdrawal has a visible current-generation outcome and zero POST', async () => {
  let finish; const env=makeEnv({authorize:()=>new Promise(r=>finish=r)}), c=createOptionsQuestion(env), ref=validReference();
  c.stage(ref);c.send('q');assert.equal(c.clear(ref),true);finish({});await settle();
  assert.equal(env.__calls.transport.length,0);
  assert.equal(env.__calls.outcomes[0].kind,'withdrawn');
  assert.equal(env.__calls.outcomes[0].generation,c.generation());
});
function actualQuestionAuth(session, rejects=false) {
  const a=source.indexOf('  function withAuth(h)'), b=source.indexOf('  /* ── quota / me',a);
  const ctx={window:{MDXAuth:{client:()=>Promise.resolve({auth:{getSession:()=>rejects?Promise.reject(Error('unavailable')):Promise.resolve({data:{session}})}})}}};
  vm.createContext(ctx);vm.runInContext(source.slice(a,b),ctx);
  return owner=>typeof ctx.authorizeOptionsQuestion==='function'?ctx.authorizeOptionsQuestion(owner):ctx.withAuth({});
}
for(const [label,session,rejects] of [
 ['different account',{access_token:'inert-B',user:{id:'user-B'}},false],
 ['missing session',null,false], ['missing token',{user:{id:'user-A'}},false], ['rejected session',null,true]
]) test('review: question auth refuses '+label,async()=>{
  await assert.rejects(actualQuestionAuth(session,rejects)('user-A'));
});
test('review: question auth binds same returned user and bearer',async()=>{
 const h=await actualQuestionAuth({access_token:'inert-A',user:{id:'user-A'}})('user-A');assert.equal(h.Authorization,'Bearer inert-A');
});
function actualResume(activeAtStart) {
 const a=source.indexOf('  var resuming = false;'),b=source.indexOf('  /* Build a fresh turn',a);
 const calls={fetch:0,open:0,attach:0};let finish;
 const ctx={streaming:false,panel:{classList:{contains:()=>true}},historyEpoch:0,historyOpenGeneration:0,
  optionsQuestion:{active:()=>activeAtStart,busy:()=>false,generation:()=>0},loadRun:()=>({id:'old',ts:Date.now(),q:'ordinary'}),
  RUN_MAX_AGE_MS:99999,clearRun:()=>{},withAuth:()=>Promise.resolve({}),API:'',
  fetch:()=>{calls.fetch++;return new Promise(r=>finish=r)},threadId:null,
  openThread:()=>calls.open++,attachFresh:()=>calls.attach++,appendMsg:()=>{}};
 vm.createContext(ctx);vm.runInContext(source.slice(a,b),ctx);
 return {ctx,calls,finish:()=>finish({ok:true,json:()=>Promise.resolve({thread_id:'old-thread',done:false})})};
}
test('review: active question prevents ordinary stored-run status reads',async()=>{
 const r=actualResume(true);r.ctx.resumeStoredRun();await settle();assert.equal(r.calls.fetch,0);
});
test('review: a newly staged question fences an already pending ordinary resume',async()=>{
 const r=actualResume(false);r.ctx.resumeStoredRun();await settle();r.ctx.historyOpenGeneration++;
 r.ctx.optionsQuestion.active=()=>true;r.finish();await settle();assert.equal(r.calls.open,0);assert.equal(r.calls.attach,0);
});

/* ── matched withdrawal AFTER the one POST (finding 10710comment6652598570) ──
 * Deferred-transport tests: the single POST hangs on an unresolved promise so
 * the in-flight window is real. A withdrawal that matches the flight's
 * reference AND owner AND generation fences the late answer — it never
 * aborts, retries or claims "nothing was sent", and busy holds until the
 * original request settles. Foreign/old references and late settlements
 * never clear anything or paint a newer generation. */
test('inflight: a matching withdrawal after the POST fences the late answer and holds busy', async () => {
  let finish;
  const env = makeEnv({ transport: () => new Promise(r => { finish = r; }) });
  const c = createOptionsQuestion(env);
  const ref = validReference();
  assert.equal(c.stage(ref), true);
  assert.equal(c.send('q'), true);
  await settle();
  assert.equal(env.__calls.transport.length, 1, 'exactly one POST before the withdrawal');
  const flightGen = c.generation();
  assert.equal(c.busy(), true, 'the original request is still in flight');
  assert.equal(c.clear(ref), false, 'nothing is staged to clear after dispatch');
  assert.equal(c.withdrawInFlight(ref), true, 'the matched in-flight withdrawal is accepted');
  assert.equal(c.generation(), flightGen + 1, 'the withdrawal fences by generation, not by abort');
  assert.equal(c.withdrawInFlight(ref), false, 'a duplicate withdrawal cannot fence again');
  assert.equal(c.generation(), flightGen + 1, 'generation moved exactly once');
  assert.equal(c.busy(), true, 'busy holds until the original request settles');
  finish({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"delta","text":"late answer"}', 'data: {"type":"done"}']) });
  await settle();
  assert.equal(c.busy(), false, 'busy releases only with the original settlement');
  const outcome = env.__calls.outcomes[0];
  assert.equal(outcome.kind, 'reply', 'the flight settles as a reply — never as withdrawn');
  assert.notEqual(outcome.generation, c.generation(), 'the fenced answer carries the stale generation so the widget drops it');
  assert.equal(env.__calls.transport.length, 1, 'no abort, no retry, no second POST');
});
test('inflight: before dispatch the seam refuses and the pre-send clear still aborts with zero POST', async () => {
  let releaseAuth;
  const captured = [];
  const env = makeEnv({
    authorize: () => new Promise(resolve => { releaseAuth = resolve; }),
    transport: init => { captured.push(init); return Promise.resolve({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"done"}']) }); }
  });
  const c = createOptionsQuestion(env);
  const ref = validReference();
  assert.equal(c.stage(ref), true);
  assert.equal(c.send('q'), true);
  assert.equal(c.withdrawInFlight(ref), false, 'nothing is dispatched yet — withdrawal is the staged clear');
  assert.equal(c.clear(ref), true, 'the pre-send withdrawal still aborts before any POST');
  releaseAuth({ 'Content-Type': 'application/json' });
  await settle();
  assert.equal(captured.length, 0, 'zero POST');
  assert.equal(env.__calls.outcomes[0].kind, 'withdrawn');
  assert.equal(env.__calls.outcomes[0].generation, c.generation(), 'the withdrawn note paints at the current generation');
});
test('inflight: a foreign reference neither clears nor fences the in-flight flight', async () => {
  let finish;
  const env = makeEnv({ transport: () => new Promise(r => { finish = r; }) });
  const c = createOptionsQuestion(env);
  c.stage(validReference());
  assert.equal(c.send('q'), true);
  await settle();
  const gen = c.generation();
  const foreign = validReference();
  foreign.selection = '{"schema":"options_matrix_selection.v1","v":9}';
  assert.equal(c.clear(foreign), false);
  assert.equal(c.withdrawInFlight(foreign), false, 'a foreign selection cannot fence the flight');
  assert.equal(c.generation(), gen, 'generation untouched');
  finish({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"delta","text":"kept"}', 'data: {"type":"done"}']) });
  await settle();
  const outcome = env.__calls.outcomes[0];
  assert.equal(outcome.kind, 'reply');
  assert.equal(outcome.generation, c.generation(), 'the unfenced answer still paints at the current generation');
  assert.equal(c.busy(), false);
});
test('inflight: another principal and a torn-down scope cannot fence; a new generation is unaffected', async () => {
  const finishes = [];
  let owner = 'user-A';
  const env = makeEnv({ principal: () => owner, transport: () => new Promise(r => finishes.push(r)) });
  const c = createOptionsQuestion(env);
  c.stage(validReference());
  assert.equal(c.send('q'), true);
  await settle();
  owner = 'user-B';
  assert.equal(c.withdrawInFlight(validReference()), false, 'only the flight owner can withdraw in flight');
  assert.equal(c.busy(), true, 'the refused withdrawal left the flight intact');
  owner = 'user-A';
  c.reset();
  assert.equal(c.withdrawInFlight(validReference()), false, 'a reset leaves no flight to withdraw');
  assert.equal(c.busy(), false);
  assert.equal(c.stage(validReference()), true, 'fresh staging opens a new generation');
  assert.equal(c.send('q2'), true);
  await settle();
  finishes[0]({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"delta","text":"stale"}', 'data: {"type":"done"}']) });
  await settle();
  assert.equal(c.busy(), true, 'the stale settlement cannot unlock the newer flight');
  const staleOutcome = env.__calls.outcomes[0];
  assert.notEqual(staleOutcome.generation, c.generation(), 'the stale settlement never paints a newer generation');
  assert.equal(c.withdrawInFlight(validReference()), true, 'the matched withdrawal fences the CURRENT flight');
  const fencedGen = c.generation();
  finishes[1]({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"delta","text":"late"}', 'data: {"type":"done"}']) });
  await settle();
  assert.equal(c.busy(), false, 'the fenced flight still releases busy at its own settlement');
  assert.notEqual(env.__calls.outcomes[1].generation, fencedGen, 'the fenced answer is dropped by generation');
});
test('inflight: after the fenced settlement the lane accepts a fresh stage at the new generation', async () => {
  const finishes = [];
  const env = makeEnv({ transport: () => new Promise(r => finishes.push(r)) });
  const c = createOptionsQuestion(env);
  c.stage(validReference());
  assert.equal(c.send('q'), true);
  await settle();
  assert.equal(c.withdrawInFlight(validReference()), true);
  finishes[0]({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"done"}']) });
  await settle();
  assert.equal(c.busy(), false);
  assert.equal(c.active(), true, 'the lane stays until an explicit exit');
  assert.equal(c.stage(validReference()), true, 'fresh staging works at the newer generation');
  assert.equal(c.send('again'), true);
  await settle();
  assert.equal(env.__calls.transport.length, 2);
  finishes[1]({ ok: true, status: 200, bodyText: sseDoc(['data: {"type":"delta","text":"fresh"}', 'data: {"type":"done"}']) });
  await settle();
  assert.equal(c.busy(), false);
  assert.equal(env.__calls.outcomes[1].kind, 'reply');
  assert.equal(env.__calls.outcomes[1].generation, c.generation(), 'the new flight paints at the newest generation');
});
function actualOutcomeHandler() {
  const a = source.indexOf('  function handleOptionsOutcome(outcome)');
  const b = source.indexOf('  function sendOptionsQuestionTurn(text)', a);
  assert.ok(a >= 0 && b > a, 'options outcome handler region not found');
  const calls = { painted: [], appended: [], stick: 0, syncSend: 0, syncOptionsExit: 0 };
  const ctx = {
    appendMsg: (role, text) => { calls.appended.push([role, text]); return { querySelector: () => null }; },
    paintOptionsNote: kind => { calls.painted.push(kind); },
    stickAfter: () => { calls.stick++; },
    syncSend: () => { calls.syncSend++; },
    syncOptionsExit: () => { calls.syncOptionsExit++; },
    optionsQuestion: { generation: () => 2 }
  };
  vm.createContext(ctx);
  vm.runInContext(source.slice(a, b), ctx);
  return { handleOptionsOutcome: ctx.handleOptionsOutcome, calls };
}
test('dom: a fenced outcome never paints but still releases busy controls', () => {
  const h = actualOutcomeHandler();
  h.handleOptionsOutcome({ generation: 1, kind: 'reply', text: 'late answer' });
  assert.equal(h.calls.appended.length, 0, 'the fenced answer never paints');
  assert.equal(h.calls.painted.length, 0, 'no note rides a fenced answer');
  assert.equal(h.calls.syncSend, 1, 'busy releases visually after the original settlement even when fenced');
  assert.equal(h.calls.syncOptionsExit, 1, 'the exit control re-syncs with the settled flight');
  h.handleOptionsOutcome({ generation: 2, kind: 'reply', text: 'kept answer' });
  assert.deepEqual(h.calls.appended[0], ['assistant', 'kept answer'], 'a current answer paints');
  assert.equal(h.calls.syncSend, 2);
  h.handleOptionsOutcome({ generation: 2, kind: 'withdrawn' });
  assert.deepEqual(h.calls.painted, ['withdrawn'], 'a current note still paints');
});
function actualWithdrawalRouter() {
  const a = source.indexOf('  function applyOptionsWithdrawal(reference)');
  const b = source.indexOf('  optqExit.addEventListener', a);
  assert.ok(a >= 0 && b > a, 'matched withdrawal router not found in the wiring');
  const calls = { clear: [], fence: [] };
  const ctx = {
    optionsQuestion: {
      clear: r => { calls.clear.push(r); return false; },
      withdrawInFlight: r => { calls.fence.push(r); return false; }
    }
  };
  vm.createContext(ctx);
  vm.runInContext(source.slice(a, b), ctx);
  return { applyOptionsWithdrawal: ctx.applyOptionsWithdrawal, optionsQuestion: ctx.optionsQuestion, calls };
}
test('dom: withdrawal router clears the stage first, then fences the in-flight flight', () => {
  const w = actualWithdrawalRouter();
  assert.equal(w.applyOptionsWithdrawal('ref'), false, 'neither seam applies');
  assert.deepEqual(w.calls.clear, ['ref']); assert.deepEqual(w.calls.fence, ['ref']);
  w.calls.clear.length = 0; w.calls.fence.length = 0;
  w.optionsQuestion.clear = () => true;
  assert.equal(w.applyOptionsWithdrawal('ref2'), true, 'the staged clear wins and short-circuits');
  assert.deepEqual(w.calls.fence, [], 'a cleared stage must not also fence');
});
test('dom: clearOptionsQuestion routes through the matched withdrawal seam', () => {
  assert.ok(source.indexOf('if (!applyOptionsWithdrawal(reference)) return false;') > 0,
    'clearOptionsQuestion must route through applyOptionsWithdrawal');
});
