/** D08C B→C source characterization, not a product adapter or authenticity check.
 * Run: node verify_boundary.mjs
 * Only the two hash-pinned pure upstream modules are executed. No network,
 * account, Save, watch, browser, provider installation or product file is used.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { stripTypeScriptTypes } from 'node:module';

const here = dirname(fileURLToPath(import.meta.url));
const sourcePins = {
  'optionsContractShortlist.ts': '8d42da79f3e5bbda9ea236df93845824feb4900d',
  'optionsPlanDraft.ts': '1b02689501cd26226b61e7a5d3fa8f5868552f7b',
};
const scratch = mkdtempSync(join(tmpdir(), 'd08c-boundary-'));
const results = [];
try {
  for (const [name, expected] of Object.entries(sourcePins)) {
    const bytes = readFileSync(join(here, 'upstream', name));
    const sha = createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
    assert.equal(sha, expected, `upstream bytes changed: ${name}`);
    let js = stripTypeScriptTypes(bytes.toString('utf8'), { mode: 'strip' });
    if (name === 'optionsPlanDraft.ts') {
      const specifier = '"./optionsContractShortlist"';
      assert.equal(js.split(specifier).length - 1, 1, 'one known import resolution only');
      js = js.replace(specifier, '"./optionsContractShortlist.mjs"');
    }
    writeFileSync(join(scratch, name.replace('.ts', '.mjs')), js);
  }
  const shortlist = await import(pathToFileURL(join(scratch, 'optionsContractShortlist.mjs')));
  const draft = await import(pathToFileURL(join(scratch, 'optionsPlanDraft.mjs')));
  const { buildPin, contractIdentity, addPin, buildComparison } = shortlist;
  const { createOptionsPlanDraft, validateOptionsPlanDraft } = draft;
  const row = (changes = {}) => ({ root: 'SPY', right: 'C', exp: '2026-11-20', strike: 600, mid: 5.2, oi: 0, ...changes });
  const source = (changes = {}) => ({ family: 'doi', asof: '2026-11-02T16:00:00-05:00', schema: 'options_hub.oi_movers/v1', stale: false, ...changes });
  const mustPin = (r = row(), src = source(), list = [r]) => {
    const p = buildPin(r, src, list); assert.equal(p.ok, true); return p.pin;
  };
  const clone = (v) => JSON.parse(JSON.stringify(v));
  const run = (id, kind, name, test) => {
    try { test(); results.push({ id, kind, name, outcome: kind === 'behavior' ? 'PASS' : 'REPRODUCED' }); }
    catch (error) { results.push({ id, kind, name, outcome: 'FAIL', error: String(error) }); }
  };

  run('B01', 'behavior', 'Actual accepted DOI rows produce a local two-leg draft', () => {
    const a = row(), b = row({ strike: 610, mid: 2 }); const full = [a, b];
    const d = createOptionsPlanDraft([mustPin(a, source(), full), mustPin(b, source(), full)]);
    assert.equal(d.ok, true); assert.equal(d.value.legs.length, 2);
    assert.deepEqual(d.value.legs.map(x => x.snapshot.row), full);
  });
  run('B02', 'behavior', 'Aggregate coordinate is not an exact contract', () => {
    const aggregate = { root: 'SPY', expiry: '2026-11-20', strike: 600, valueUsd: 1500000, aggregated: true };
    assert.equal(contractIdentity(aggregate).ok, false);
    assert.equal(createOptionsPlanDraft([aggregate]).ok, false);
  });
  run('B03', 'behavior', 'Full original list exposes duplicate identity despite a one-row view', () => {
    const a = row(); const full = [a, { ...a, oi: 99 }];
    assert.deepEqual(buildPin(a, source(), full), { ok: false, reason: 'ambiguous' });
  });
  run('B04', 'behavior', 'Adjusted root suffix is retained rather than normalized', () => {
    const a = contractIdentity(row({ root: 'NVDA' })), b = contractIdentity(row({ root: 'NVDA1' }));
    assert.notEqual(a.identity.key, b.identity.key); assert.equal(b.identity.root, 'NVDA1');
    assert.equal(b.identity.adjustedRootHint, true);
  });
  run('B05', 'behavior', 'Missing terms stay null and a research draft can retain them', () => {
    const p = mustPin(); assert.deepEqual(p.identity.terms, { multiplier: null, deliverable: null, settlement: null, exercise_style: null });
    assert.equal(createOptionsPlanDraft([p]).ok, true);
  });
  run('B06', 'behavior', 'Malformed supplied terms refuse identity binding', () => {
    assert.deepEqual(contractIdentity(row({ multiplier: 0 })), { ok: false, reason: 'terms' });
    assert.deepEqual(contractIdentity(row({ deliverable: '' })), { ok: false, reason: 'terms' });
  });
  run('B07', 'behavior', 'Missing source session cannot produce a pin', () => {
    const a = row(); assert.deepEqual(buildPin(a, source({ asof: null }), [a]), { ok: false, reason: 'session' });
  });
  run('B08', 'behavior', 'Original source clock, schema and stale marker survive', () => {
    const p = mustPin(row(), source({ asof: '2026-10-26T16:00:00-04:00', stale: true }));
    const d = createOptionsPlanDraft([p]); assert.equal(d.ok, true);
    const retained = d.value.legs[0].snapshot;
    assert.equal(retained.asofRaw, '2026-10-26T16:00:00-04:00'); assert.equal(retained.session, '2026-10-26');
    assert.equal(retained.sourceStale, true); assert.equal(retained.schema, 'options_hub.oi_movers/v1');
  });
  run('B09', 'behavior', 'Changing only hot view does not create another pin', () => {
    const a = row({ close: 5.2 });
    const p = mustPin(a, source({ family: 'hot', hotView: 'by_volume' }));
    const q = mustPin(a, source({ family: 'hot', hotView: 'by_premium' }));
    assert.equal(p.pinKey, q.pinKey); assert.equal(addPin([p], q).result, 'exists');
    assert.equal(p.hotView, 'by_volume'); assert.equal(q.hotView, 'by_premium');
  });
  run('B10', 'behavior', 'Same contract from two families is two observations but not two Plan legs', () => {
    const a = row({ close: 5.2 }); const p = mustPin(a), q = mustPin(a, source({ family: 'hot', hotView: 'by_volume' }));
    assert.notEqual(p.pinKey, q.pinKey); assert.equal(buildComparison([p, q]).notes.sameContractTwice.length, 1);
    assert.deepEqual(createOptionsPlanDraft([p, q]), { ok: false, reason: 'duplicate_contract' });
  });
  run('B11', 'behavior', 'Fifth selection is refused without rotating the existing four', () => {
    const pins = [590, 595, 600, 605].map(strike => mustPin(row({ strike })));
    const added = addPin(pins, mustPin(row({ strike: 610 })));
    assert.equal(added.result, 'full'); assert.equal(added.pins, pins);
  });
  run('B12', 'behavior', 'Source reference mark does not author side, size or entry', () => {
    const d = createOptionsPlanDraft([mustPin(row({ mid: 99, close: 88 }))]);
    assert.equal(d.ok, true); assert.deepEqual(d.value.legs[0].assumptions, { side: null, quantity: null, entry: null });
  });
  run('B13', 'behavior', 'Two roots refuse a combined Plan', () => {
    const p = mustPin(), q = mustPin(row({ root: 'QQQ' }));
    assert.deepEqual(createOptionsPlanDraft([p, q]), { ok: false, reason: 'mixed_root' });
  });
  run('B14', 'behavior', 'Mixed-expiry research is retained without proving payoff eligibility', () => {
    const p = mustPin(), q = mustPin(row({ exp: '2026-12-18' }));
    assert.equal(createOptionsPlanDraft([p, q]).ok, true);
  });
  run('B15', 'behavior', 'Plan revalidation rejects an unsupported source family', () => {
    const p = clone(mustPin()); p.family = 'chain';
    assert.deepEqual(createOptionsPlanDraft([p]), { ok: false, reason: 'source_snapshot' });
  });
  run('B16', 'behavior', 'Identity cannot be altered independently of copied source row', () => {
    const p = clone(mustPin()); p.identity.strike = 601;
    assert.deepEqual(createOptionsPlanDraft([p]), { ok: false, reason: 'source_snapshot' });
  });
  run('B17', 'behavior', 'B origin context cannot be injected into the closed pin payload', () => {
    const p = clone(mustPin()); p.originNode = 'synthetic-node';
    assert.deepEqual(createOptionsPlanDraft([p]), { ok: false, reason: 'source_snapshot' });
  });
  run('B18', 'behavior', 'Draft detaches and freezes retained nested observation data', () => {
    const a = row({ detail: { reading: 0 } }); const d = createOptionsPlanDraft([mustPin(a)]);
    assert.equal(d.ok, true); a.detail.reading = 77;
    assert.equal(d.value.legs[0].snapshot.row.detail.reading, 0);
    assert.equal(Object.isFrozen(d.value.legs[0].snapshot.row.detail), true);
  });
  run('B19', 'behavior', 'Different supplied terms remain separate contract identities', () => {
    const p = mustPin(row({ multiplier: 50 })), q = mustPin(row({ multiplier: 100 }));
    assert.notEqual(p.identity.key, q.identity.key); assert.equal(createOptionsPlanDraft([p, q]).ok, true);
  });
  run('B20', 'behavior', 'Draft preservation is distinct from stale observation comparability', () => {
    const p = mustPin(row(), source({ stale: true })), q = mustPin(row({ strike: 610 }));
    assert.equal(createOptionsPlanDraft([p, q]).ok, true);
    assert.equal(buildComparison([p, q]).notes.likeForLike, false);
  });

  // These deliberately reproduce limits, not successful security/admission guards.
  // The functions trust their in-process caller's source/list custody.
  run('L01', 'trust_limit', 'A filtered singleton hides ambiguity the full list would expose', () => {
    const a = row(); const full = [a, { ...a, oi: 99 }];
    assert.equal(buildPin(a, source(), full).ok, false);
    assert.equal(buildPin(a, source(), [a]).ok, true);
  });
  run('L02', 'trust_limit', 'buildPin does not prove the row belonged to the supplied list', () => {
    const a = row(); assert.equal(buildPin(a, source(), [row({ strike: 610 })]).ok, true);
  });
  run('L03', 'trust_limit', 'Runtime buildPin alone does not enforce its TypeScript family union', () => {
    const a = row(); const p = buildPin(a, source({ family: 'chain' }), [a]);
    assert.equal(p.ok, true); assert.equal(p.pin.family, 'chain');
    assert.deepEqual(createOptionsPlanDraft([p.pin]), { ok: false, reason: 'source_snapshot' });
  });
  run('L04', 'trust_limit', 'Relabelling a fabricated row DOI can pass shape checks; it is not source authenticity', () => {
    const fabricated = row({ arbitrary_exposure_field: 123 });
    const p = buildPin(fabricated, source(), [fabricated]); assert.equal(p.ok, true);
    const d = createOptionsPlanDraft([p.pin]); assert.equal(d.ok, true);
    assert.equal(validateOptionsPlanDraft(d.value).ok, true);
  });
  const failed = results.filter(x => x.outcome === 'FAIL');
  const output = {
    schema: 'd08c.boundary_characterization.v1', node: process.version,
    source_commit: '2ded360882b9c721e690907ff363b553781fb920', source_blobs: sourcePins,
    behavior_checks_passed: results.filter(x => x.kind === 'behavior' && x.outcome === 'PASS').length,
    trust_limits_reproduced: results.filter(x => x.kind === 'trust_limit' && x.outcome === 'REPRODUCED').length,
    failed_checks: failed.length,
    scope: 'Pure pinned-source behavior and trust-limit characterization only. No adapter, mounted B-to-C path, source authenticity, payoff, account persistence, watch or production acceptance is proved.',
    transformation: 'Node type erasure; one exact local import extension resolved in temporary generated files. Upstream input bytes remain unchanged.',
    cases: results,
  };
  process.stdout.write(JSON.stringify(output, null, 2) + '\n');
  if (failed.length) process.exitCode = 1;
} finally {
  rmSync(scratch, { recursive: true, force: true });
}
