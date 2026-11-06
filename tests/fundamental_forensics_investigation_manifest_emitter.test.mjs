// FIF X2-c emitter suite (hermetic: no network, no browser).
//
// Pins the typed-refusal surface the X2-c splice adds to the saved-view
// module (templates/fif_saved_briefcase.js) on top of the X2-b lossless 1:1
// mapping (see fundamental_forensics_investigation_manifest_mapping.test.mjs
// for the mapping itself):
//   - length is measured in CODE POINTS, never UTF-16 units, exactly as
//     Terminal measures it at census commit c799ba7e
//   - the only shortening is the title cut at a whole-grapheme boundary
//     (a surrogate pair or a ZWJ/emoji sequence is never split), and the cut
//     is REPORTED as a title_cut notice
//   - nothing is trimmed, dropped or deduped silently: a value the Terminal
//     contract would refuse is refused HERE, typed, with the JSON path of
//     the offending field (empty_text, invalid_control, invalid_unicode,
//     text_too_long, invalid_date, duplicate_reference, invalid_type)
//   - a pinned view whose cutoff is not a real calendar date refuses
//     invalid_date instead of silently omitting research_as_of
//   - without Intl.Segmenter the emitter fails closed rather than guess a
//     grapheme boundary
// Every case is built from a committed fixture (saved_single_issuer.json for
// unpinned, saved_pinned.json for pinned, saved_with_evidence.json for
// evidence) by JSON-cloning and changing ONE field. Every refusal asserts
// toInvestigationManifestV2(view) === null FIRST and then the typed
// emitInvestigationManifestV2(view) result via JSON text. Non-ASCII input
// appears only as JS escapes; this file is pure ASCII.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const BRIEFCASE_SOURCE = readFileSync(new URL('../templates/fif_saved_briefcase.js', import.meta.url), 'utf8');
const FIXTURE_DIR = new URL('../tests/fixtures/fundamental_forensics/fif_saved_research/', import.meta.url);
const CARRIER_KEY = 'fif_saved_research';

function memoryStorage(initial) {
  const rows = new Map(initial || []);
  const written = [];
  return {
    rows,
    written,
    getItem: (key) => (rows.has(key) ? rows.get(key) : null),
    setItem: (key, value) => { rows.set(key, String(value)); written.push(key); },
    removeItem: (key) => { rows.delete(key); },
  };
}

// Exactly the mapping suite's freshBriefcase: the context's transports
// THROW and count, so any network reach from the module fails the suite
// loudly instead of silently succeeding.
function freshBriefcase(storage, seed) {
  const network = { fetches: 0, xhrs: 0 };
  const context = vm.createContext({
    window: {
      localStorage: storage,
      crypto: { getRandomValues: (view) => { for (let i = 0; i < view.length; i += 1) view[i] = (i + (seed || 0)) % 256; return view; } },
      fetch: () => { network.fetches += 1; throw new Error('network is forbidden'); },
      XMLHttpRequest: function () { network.xhrs += 1; throw new Error('network is forbidden'); }
    },
    console,
  });
  vm.runInContext(BRIEFCASE_SOURCE, context, { filename: 'fif_saved_briefcase.js' });
  const Briefcase = context.window.FifSavedBriefcase;
  Briefcase.__networkProbe = network;
  return Briefcase;
}

// The same harness with Intl.Segmenter removed BEFORE the module loads: the
// emitter must fail closed rather than guess a grapheme boundary.
function noSegmenterBriefcase(storage, seed) {
  const network = { fetches: 0, xhrs: 0 };
  const context = vm.createContext({
    window: {
      localStorage: storage,
      crypto: { getRandomValues: (view) => { for (let i = 0; i < view.length; i += 1) view[i] = (i + (seed || 0)) % 256; return view; } },
      fetch: () => { network.fetches += 1; throw new Error('network is forbidden'); },
      XMLHttpRequest: function () { network.xhrs += 1; throw new Error('network is forbidden'); }
    },
    console,
  });
  vm.runInContext('Intl.Segmenter = undefined;', context);
  vm.runInContext(BRIEFCASE_SOURCE, context, { filename: 'fif_saved_briefcase.js' });
  const Briefcase = context.window.FifSavedBriefcase;
  Briefcase.__networkProbe = network;
  return Briefcase;
}

function fixtureView(name) {
  return JSON.parse(readFileSync(new URL(name, FIXTURE_DIR), 'utf8')).saved_views[0];
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

// vm realms give objects a foreign prototype, so deepStrictEqual rejects
// structurally identical values; JSON text equality is realm-blind.
function sameJson(actual, expected) {
  assert.equal(JSON.stringify(actual), JSON.stringify(expected));
}

// Every refusal reason this suite exercises; the last test checks that each
// one is a declared REFUSAL_REASONS or MANIFEST_REFUSAL_REASONS member.
const SEEN_REFUSALS = new Set();

function assertRefusal(Briefcase, view, reason, path) {
  assert.equal(Briefcase.toInvestigationManifestV2(view), null,
    'toInvestigationManifestV2 returns null for ' + reason + ' at ' + path);
  sameJson(Briefcase.emitInvestigationManifestV2(view), { ok: false, reason: reason, path: path });
  SEEN_REFUSALS.add(reason);
}

function emitOk(Briefcase, view, label) {
  const emitted = Briefcase.emitInvestigationManifestV2(view);
  assert.ok(emitted && emitted.ok === true, (label || 'the view') + ' emits');
  return emitted;
}

function assertNoNetwork(Briefcase) {
  assert.equal(Briefcase.__networkProbe.fetches, 0, 'zero fetches');
  assert.equal(Briefcase.__networkProbe.xhrs, 0, 'zero XMLHttpRequests');
}

test('empty_text: blank and all-whitespace text is refused, never treated as absent', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  // Title: the blank set is the union of the Python TRIM set, ECMAScript
  // trim and the sql btrim list. Whitespace-only counts as EMPTY, not as a
  // control character.
  for (const name of [
    '',
    '   ',
    '\u000b\u000c',
    '\u205f\u3000\u00a0\ufeff\u1680\u2000\u200a\u202f',
    '\u2028\u2029',
    '\n'
  ]) {
    const view = clone(fixtureView('saved_single_issuer.json'));
    view.name = name;
    assertRefusal(Briefcase, view, 'empty_text', '$.intent.title');
  }
  // Subject object_id: empty and ideographic-space ids.
  for (const entityId of ['', '\u3000']) {
    const view = clone(fixtureView('saved_single_issuer.json'));
    view.issuer.entity_id = entityId;
    assertRefusal(Briefcase, view, 'empty_text', '$.intent.subjects[0].object_id');
  }
  // Evidence object_id: a whitespace-only occurrence_id is NOT an absent id
  // (it does not fall back to the accession) - it refuses empty_text.
  const whitespaceOccurrence = clone(fixtureView('saved_with_evidence.json'));
  whitespaceOccurrence.evidence_refs[0].occurrence_id = '  ';
  assertRefusal(Briefcase, whitespaceOccurrence, 'empty_text', '$.evidence_refs[0].object_id');
  // A ref carrying neither id at all, same path.
  const neitherId = clone(fixtureView('saved_with_evidence.json'));
  neitherId.evidence_refs[0] = {};
  assertRefusal(Briefcase, neitherId, 'empty_text', '$.evidence_refs[0].object_id');
  assertNoNetwork(Briefcase);
});

test('invalid_control: tab, LF, CR, any other C0 and DEL anywhere in a field', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  // r2 MINOR-3: NUL moved out of this list -- Terminal reports NUL as
  // unsupported_code_point (investigation_contracts.py:45,
  // investigationContracts.ts:150), not invalid_control; the dedicated NUL
  // test below pins the new code.
  for (const name of [
    'Apple\tbaseline',
    'Apple\nbaseline',
    'Apple\rbaseline',
    'Apple\u0001',
    'Apple\u007f',
    '\tApple' // a leading tab: the old emitter trimmed this away
  ]) {
    const view = clone(fixtureView('saved_single_issuer.json'));
    view.name = name;
    assertRefusal(Briefcase, view, 'invalid_control', '$.intent.title');
  }
  const tabIssuer = clone(fixtureView('saved_single_issuer.json'));
  tabIssuer.issuer.entity_id = 'ISS:\tX';
  assertRefusal(Briefcase, tabIssuer, 'invalid_control', '$.intent.subjects[0].object_id');
  const controlOccurrence = clone(fixtureView('saved_with_evidence.json'));
  controlOccurrence.evidence_refs[0].occurrence_id = 'raw\u001ffact';
  assertRefusal(Briefcase, controlOccurrence, 'invalid_control', '$.evidence_refs[0].object_id');
  assertNoNetwork(Briefcase);
});

test('invalid_unicode: a lone or split surrogate anywhere is refused', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  for (const name of [
    'Apple \ud800 x', // a lone high surrogate
    'Apple \udc00',   // a lone low surrogate
    '\ude00\ud83d'    // a reversed pair: low before high
  ]) {
    const view = clone(fixtureView('saved_single_issuer.json'));
    view.name = name;
    assertRefusal(Briefcase, view, 'invalid_unicode', '$.intent.title');
  }
  const surrogateIssuer = clone(fixtureView('saved_single_issuer.json'));
  surrogateIssuer.issuer.entity_id = 'ISS:\ud83d';
  assertRefusal(Briefcase, surrogateIssuer, 'invalid_unicode', '$.intent.subjects[0].object_id');
  assertNoNetwork(Briefcase);
});

test('text_too_long: identifiers are never cut; a title with no whole-grapheme cut refuses', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const overLimitId = clone(fixtureView('saved_single_issuer.json'));
  overLimitId.issuer.entity_id = 'I'.repeat(257);
  assertRefusal(Briefcase, overLimitId, 'text_too_long', '$.intent.subjects[0].object_id');

  const astralOver = clone(fixtureView('saved_single_issuer.json'));
  astralOver.issuer.entity_id = '\u{1F600}'.repeat(257);
  assertRefusal(Briefcase, astralOver, 'text_too_long', '$.intent.subjects[0].object_id');

  // 256 astral chars are 256 code points but 512 UTF-16 units: the limit is
  // code points, so this EMITS verbatim where the old UTF-16 slice cut it.
  const astralAtLimit = clone(fixtureView('saved_single_issuer.json'));
  astralAtLimit.issuer.entity_id = '\u{1F600}'.repeat(256);
  const astralEmitted = emitOk(Briefcase, astralAtLimit, 'the 256-emoji entity_id');
  const astralId = astralEmitted.manifest.intent.subjects[0].object_id;
  assert.equal(astralId, '\u{1F600}'.repeat(256));
  assert.equal(Array.from(astralId).length, 256, 'the id is 256 code points');
  assert.equal(astralId.length, 512, 'the id is 512 UTF-16 units');

  const longOccurrence = clone(fixtureView('saved_with_evidence.json'));
  longOccurrence.evidence_refs[0].occurrence_id = 'r'.repeat(257);
  assertRefusal(Briefcase, longOccurrence, 'text_too_long', '$.evidence_refs[0].object_id');

  // A title that is ONE 201-code-point grapheme ('e' plus 200 combining
  // accents): no whole-grapheme prefix fits in 160, so no cut exists.
  const singleGrapheme = clone(fixtureView('saved_single_issuer.json'));
  singleGrapheme.name = 'e' + '\u0301'.repeat(200);
  assertRefusal(Briefcase, singleGrapheme, 'text_too_long', '$.intent.title');

  // 160 spaces then 'x': the only prefix that fits is blank, which is not a
  // title either.
  const blankPrefix = clone(fixtureView('saved_single_issuer.json'));
  blankPrefix.name = ' '.repeat(160) + 'x';
  assertRefusal(Briefcase, blankPrefix, 'text_too_long', '$.intent.title');
  assertNoNetwork(Briefcase);
});

test('invalid_date: a pinned cutoff that is not a real calendar date refuses', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  for (const cutoff of [
    '2026-02-30T00:00:00Z',  // Feb 30
    '2025-02-29T00:00:00Z',  // Feb 29 in a non-leap year
    '1900-02-29',            // a century year is not leap
    '2026-13-01',            // month 13
    '2026-00-10',            // month 0
    '0000-01-01',            // year 0
    'not a date',            // no date at all
    ' 2026-09-30T23:59:59Z'  // a leading space is not trimmed away
  ]) {
    const view = clone(fixtureView('saved_pinned.json'));
    view.request.policy.source_snapshot_at = cutoff;
    assertRefusal(Briefcase, view, 'invalid_date', '$.intent.research_as_of');
  }
  // Positive controls: real leap days, and both date-time separators.
  for (const [cutoff, expected] of [
    ['2024-02-29T00:00:00Z', '2024-02-29'],
    ['2000-02-29', '2000-02-29'],
    ['2026-09-30 23:59:59', '2026-09-30']
  ]) {
    const view = clone(fixtureView('saved_pinned.json'));
    view.request.policy.source_snapshot_at = cutoff;
    const emitted = emitOk(Briefcase, view, 'cutoff ' + cutoff);
    assert.equal(emitted.manifest.intent.research_as_of, expected);
  }
  // The date is projected only when pinned: an unpinned view with the same
  // impossible cutoff still emits, with no research_as_of key at all.
  const unpinned = clone(fixtureView('saved_single_issuer.json'));
  unpinned.request.policy.source_snapshot_at = '2026-02-30T00:00:00Z';
  const unpinnedEmitted = emitOk(Briefcase, unpinned, 'the unpinned view with a bad cutoff');
  assert.equal('research_as_of' in unpinnedEmitted.manifest.intent, false,
    'an unpinned manifest carries no research_as_of key');
  assertNoNetwork(Briefcase);
});

test('duplicate_reference: the same Terminal identity tuple twice refuses at the later index', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);

  // (a) unpinned: an exact clone of the first ref duplicates it.
  const cloned = clone(fixtureView('saved_with_evidence.json'));
  cloned.evidence_refs[1] = clone(cloned.evidence_refs[0]);
  assertRefusal(Briefcase, cloned, 'duplicate_reference', '$.evidence_refs[1]');

  // (b) pinned: the same occurrence_id AND the same accession.
  const pinnedSame = clone(fixtureView('saved_pinned.json'));
  pinnedSame.evidence_refs = [
    { accession: '0000320193-25-000073', occurrence_id: 'rawfact_aapl_rev_fy2024', source_span: [1234, 1288] },
    { accession: '0000320193-25-000073', occurrence_id: 'rawfact_aapl_rev_fy2024', source_span: [1234, 1288] }
  ];
  assertRefusal(Briefcase, pinnedSame, 'duplicate_reference', '$.evidence_refs[1]');

  // (c) unpinned: the same occurrence_id under a different accession still
  // duplicates - a follow_head identity carries no version_ref, so the
  // accession cannot tell the two apart.
  const sameOccurrence = clone(fixtureView('saved_with_evidence.json'));
  sameOccurrence.evidence_refs[1].occurrence_id = sameOccurrence.evidence_refs[0].occurrence_id;
  assertRefusal(Briefcase, sameOccurrence, 'duplicate_reference', '$.evidence_refs[1]');

  // (d) positive control: pinned, the same occurrence_id, DIFFERENT
  // accessions - the version_refs differ, so both refs are lawful.
  const pinnedDistinct = clone(fixtureView('saved_pinned.json'));
  pinnedDistinct.evidence_refs = [
    { accession: '0000320193-25-000073', occurrence_id: 'rawfact_aapl_rev_fy2024', source_span: [1234, 1288] },
    { accession: '0000320193-24-000123', occurrence_id: 'rawfact_aapl_rev_fy2024', source_span: [987, 1041] }
  ];
  const emitted = emitOk(Briefcase, pinnedDistinct, 'pinned refs distinct by version_ref');
  assert.equal(emitted.manifest.evidence_refs.length, 2);
  assert.equal(emitted.manifest.evidence_refs[0].object_id, 'rawfact_aapl_rev_fy2024');
  assert.equal(emitted.manifest.evidence_refs[1].object_id, 'rawfact_aapl_rev_fy2024');
  assert.equal(emitted.manifest.evidence_refs[0].version_ref, '0000320193-25-000073');
  assert.equal(emitted.manifest.evidence_refs[1].version_ref, '0000320193-24-000123');

  // (e) a third copy appended after two distinct refs reports index 2.
  const third = clone(fixtureView('saved_with_evidence.json'));
  third.evidence_refs.push(clone(third.evidence_refs[0]));
  assertRefusal(Briefcase, third, 'duplicate_reference', '$.evidence_refs[2]');
  assertNoNetwork(Briefcase);
});

test('invalid_type: non-object refs, a non-array evidence_refs and non-string ids', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);

  const stringRef = clone(fixtureView('saved_with_evidence.json'));
  stringRef.evidence_refs = ['x'];
  assertRefusal(Briefcase, stringRef, 'invalid_type', '$.evidence_refs[0]');

  const nullRef = clone(fixtureView('saved_with_evidence.json'));
  nullRef.evidence_refs[1] = null;
  assertRefusal(Briefcase, nullRef, 'invalid_type', '$.evidence_refs[1]');

  const notArray = clone(fixtureView('saved_with_evidence.json'));
  notArray.evidence_refs = {};
  assertRefusal(Briefcase, notArray, 'invalid_type', '$.evidence_refs');

  // A null evidence_refs is the one non-array that is allowed: it means none.
  const noRefs = clone(fixtureView('saved_single_issuer.json'));
  noRefs.evidence_refs = null;
  const nullRefsEmitted = emitOk(Briefcase, noRefs, 'a null evidence_refs');
  sameJson(nullRefsEmitted.manifest.evidence_refs, []);

  const numericIssuer = clone(fixtureView('saved_single_issuer.json'));
  numericIssuer.issuer.entity_id = 42;
  assertRefusal(Briefcase, numericIssuer, 'invalid_type', '$.intent.subjects[0].object_id');
  assertNoNetwork(Briefcase);
});

test('code-point title boundary: the cut lands on a whole grapheme, never a surrogate', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  // A ZWJ family: 4 astral emoji joined by 3 ZWJs - 7 code points, 11 UTF-16
  // units, ONE grapheme cluster.
  const family = '\u{1F468}\u200d\u{1F469}\u200d\u{1F467}\u200d\u{1F466}';
  for (const [name, expectedTitle, expectedNotices] of [
    // 158 a's + emoji + b = 160 code points (162 UTF-16 units): verbatim.
    ['a'.repeat(158) + '\u{1F600}' + 'b', 'a'.repeat(158) + '\u{1F600}' + 'b', []],
    // 159 a's + emoji + b = 161 code points: the astral char straddles the
    // old UTF-16 cut (which left a lone surrogate); the grapheme cut keeps
    // the whole emoji and drops only the b.
    ['a'.repeat(159) + '\u{1F600}' + 'b', 'a'.repeat(159) + '\u{1F600}',
      [{ code: 'title_cut', path: '$.intent.title', code_points: 161, kept_code_points: 160 }]],
    // 153 a's + the family = 160 code points: verbatim, sequence intact.
    ['a'.repeat(153) + family, 'a'.repeat(153) + family, []],
    // 155 a's + the family = 162 code points: the family is never split, so
    // the cut keeps only the a's.
    ['a'.repeat(155) + family, 'a'.repeat(155),
      [{ code: 'title_cut', path: '$.intent.title', code_points: 162, kept_code_points: 155 }]],
    ['a'.repeat(160), 'a'.repeat(160), []],
    ['a'.repeat(161), 'a'.repeat(160),
      [{ code: 'title_cut', path: '$.intent.title', code_points: 161, kept_code_points: 160 }]]
  ]) {
    const view = clone(fixtureView('saved_single_issuer.json'));
    view.name = name;
    const emitted = emitOk(Briefcase, view, 'the title of ' + Array.from(name).length + ' code points');
    assert.equal(emitted.manifest.intent.title, expectedTitle);
    assert.equal(Array.from(emitted.manifest.intent.title).length <= 160, true,
      'the cut title never exceeds 160 code points');
    sameJson(emitted.notices, expectedNotices);
    // The carrier keeps the full uncut name either way.
    assert.equal(emitted.manifest[CARRIER_KEY].name, name);
  }
  assertNoNetwork(Briefcase);
});

test('no silent trim: padded names and ids emit VERBATIM', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const paddedName = clone(fixtureView('saved_single_issuer.json'));
  paddedName.name = '  Apple baseline  ';
  const nameEmitted = emitOk(Briefcase, paddedName, 'the padded name');
  assert.equal(nameEmitted.manifest.intent.title, '  Apple baseline  ');
  sameJson(nameEmitted.notices, []);

  const paddedIssuer = clone(fixtureView('saved_single_issuer.json'));
  paddedIssuer.issuer.entity_id = ' ISS:US-XNAS-AAPL ';
  const idEmitted = emitOk(Briefcase, paddedIssuer, 'the padded entity_id');
  assert.equal(idEmitted.manifest.intent.subjects[0].object_id, ' ISS:US-XNAS-AAPL ');
  assertNoNetwork(Briefcase);
});

test('round trip: the carrier keeps the full name and an edited projection maps back to null', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const family = '\u{1F468}\u200d\u{1F469}\u200d\u{1F467}\u200d\u{1F466}';
  const astralTitle = clone(fixtureView('saved_single_issuer.json'));
  astralTitle.name = 'a'.repeat(159) + '\u{1F600}' + 'b';
  const zwjTitle = clone(fixtureView('saved_single_issuer.json'));
  zwjTitle.name = 'a'.repeat(155) + family;
  const paddedTitle = clone(fixtureView('saved_single_issuer.json'));
  paddedTitle.name = '  Apple baseline  ';
  for (const view of [astralTitle, zwjTitle, paddedTitle]) {
    const emitted = emitOk(Briefcase, view, 'the cut or padded view');
    const back = Briefcase.fromInvestigationManifestV2(JSON.parse(JSON.stringify(emitted.manifest)));
    assert.ok(back, 'the manifest maps back');
    assert.equal(JSON.stringify(back), JSON.stringify(view),
      'the carrier kept the full name, cut or padded title included');
  }
  // One character of drift in the projection breaks the exact-image law.
  const edited = JSON.parse(JSON.stringify(
    Briefcase.emitInvestigationManifestV2(astralTitle).manifest));
  edited.intent.title = edited.intent.title + 'c';
  assert.equal(Briefcase.fromInvestigationManifestV2(edited), null,
    'an edited projection is refused');
  assertNoNetwork(Briefcase);
});

test('no-Segmenter fail-closed: without Intl.Segmenter an over-limit title refuses instead of guessing', () => {
  const Briefcase = noSegmenterBriefcase(memoryStorage(), 0);
  const overLimit = clone(fixtureView('saved_single_issuer.json'));
  overLimit.name = 'a'.repeat(161);
  assertRefusal(Briefcase, overLimit, 'text_too_long', '$.intent.title');
  const atLimit = clone(fixtureView('saved_single_issuer.json'));
  atLimit.name = 'a'.repeat(160);
  emitOk(Briefcase, atLimit, 'the 160-code-point title without a Segmenter');
  assertNoNetwork(Briefcase);
});

// ── X2-b+c r2 MINOR-3: the Terminal checks the emitter was missing ─────────

test('unsupported_code_point: NUL refuses with Terminal code, never invalid_control', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  // Terminal refuses NUL inside the per-character loop as
  // unsupported_code_point (investigation_contracts.py:45,
  // investigationContracts.ts:150); the sql scalar cannot store it at all.
  const NUL = String.fromCharCode(0);
  const nulName = clone(fixtureView('saved_single_issuer.json'));
  nulName.name = 'Apple' + NUL + 'baseline';
  assertRefusal(Briefcase, nulName, 'unsupported_code_point', '$.intent.title');
  const nulIssuer = clone(fixtureView('saved_single_issuer.json'));
  nulIssuer.issuer.entity_id = 'ISS:' + NUL + 'X';
  assertRefusal(Briefcase, nulIssuer, 'unsupported_code_point', '$.intent.subjects[0].object_id');
  const nulOccurrence = clone(fixtureView('saved_with_evidence.json'));
  nulOccurrence.evidence_refs[0].occurrence_id = 'raw' + NUL + 'fact';
  assertRefusal(Briefcase, nulOccurrence, 'unsupported_code_point', '$.evidence_refs[0].object_id');
  // Accepted case: the same values without the NUL emit.
  const cleanName = clone(fixtureView('saved_single_issuer.json'));
  cleanName.name = 'Apple baseline';
  emitOk(Briefcase, cleanName, 'the same name without NUL');
  assertNoNetwork(Briefcase);
});

test('refusal order matches Terminal: length fires before the control scan, surrogate by position', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  // Terminal checks each character in order (py :42-47, ts :143-157): a
  // 300-code-point id is text_too_long at position 257, so a trailing lone
  // surrogate or tab is never reached; an early lone surrogate or NUL fires
  // first. The old emitter scanned the whole string for surrogates and
  // controls before the length, which reported the wrong code.
  const loneHigh = String.fromCharCode(0xd800);
  const TAB = String.fromCharCode(9);
  const NUL = String.fromCharCode(0);
  const trailingSurrogate = clone(fixtureView('saved_single_issuer.json'));
  trailingSurrogate.issuer.entity_id = 'I'.repeat(300) + loneHigh;
  assertRefusal(Briefcase, trailingSurrogate, 'text_too_long', '$.intent.subjects[0].object_id');
  const trailingTab = clone(fixtureView('saved_single_issuer.json'));
  trailingTab.issuer.entity_id = 'I'.repeat(300) + TAB;
  assertRefusal(Briefcase, trailingTab, 'text_too_long', '$.intent.subjects[0].object_id');
  const earlySurrogate = clone(fixtureView('saved_single_issuer.json'));
  earlySurrogate.issuer.entity_id = 'ISS:' + loneHigh + 'I'.repeat(300);
  assertRefusal(Briefcase, earlySurrogate, 'invalid_unicode', '$.intent.subjects[0].object_id');
  const earlyNul = clone(fixtureView('saved_single_issuer.json'));
  earlyNul.issuer.entity_id = 'ISS:' + NUL + 'I'.repeat(300);
  assertRefusal(Briefcase, earlyNul, 'unsupported_code_point', '$.intent.subjects[0].object_id');
  // Accepted case: the id at exactly the 256-code-point limit emits.
  const atLimit = clone(fixtureView('saved_single_issuer.json'));
  atLimit.issuer.entity_id = 'I'.repeat(256);
  emitOk(Briefcase, atLimit, 'the 256-code-point id');
  assertNoNetwork(Briefcase);
});

test('too_many_items: evidence_refs above 128 refuse with Terminal per-list code; 128 emit', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const refsOf = (count) => Array.from({ length: count }, (_, index) => ({
    accession: 'A' + index,
    occurrence_id: 'occurrence-' + index,
    source_span: [index, index + 1]
  }));
  // Terminal's refs() checks the list length before any item
  // (investigation_contracts.py:139 via :161): an all-evidence manifest over
  // 128 items is too_many_items at $.evidence_refs, and the combined cap of
  // :162 (sql :120) can only fire past it, never instead of it.
  const over = clone(fixtureView('saved_with_evidence.json'));
  over.evidence_refs = refsOf(129);
  assertRefusal(Briefcase, over, 'too_many_items', '$.evidence_refs');
  const atLimit = clone(fixtureView('saved_with_evidence.json'));
  atLimit.evidence_refs = refsOf(128);
  const emitted = emitOk(Briefcase, atLimit, 'the 128-ref view');
  assert.equal(emitted.manifest.evidence_refs.length, 128);
  assert.equal(emitted.manifest.layout_refs.length + emitted.manifest.thesis_refs.length +
    emitted.manifest.evidence_refs.length, 128, 'layout+thesis+evidence is exactly the combined cap');
  assertNoNetwork(Briefcase);
});

test('manifest_too_large: the 131072-byte canonical cap, boundary pair', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const byteLength = (text) => new TextEncoder().encode(text).length;
  // Terminal caps the manifest at 131072 UTF-8 bytes of its compact JSON
  // (py :169 json.dumps separators=(',',':') ensure_ascii=False;
  // sql :93 octet_length of the canonical jsonb text; ts :278-282
  // TextEncoder over JSON.stringify). Key order never changes the byte
  // total, so all three measure alike.
  //
  // For a name over 160 code points the title is cut to 160 and only the
  // carrier keeps the full name, so every added ASCII name character adds
  // exactly one byte: measure once at 200 and solve the boundary.
  const probe = clone(fixtureView('saved_single_issuer.json'));
  probe.name = 'q'.repeat(200);
  const probeEmitted = emitOk(Briefcase, probe, 'the 200-character probe');
  const probeBytes = byteLength(JSON.stringify(probeEmitted.manifest));
  assert.ok(probeBytes <= 131072);
  const atCap = 200 + (131072 - probeBytes);
  const capped = clone(fixtureView('saved_single_issuer.json'));
  capped.name = 'q'.repeat(atCap);
  const cappedEmitted = emitOk(Briefcase, capped, 'the manifest at the 131072-byte cap');
  assert.equal(byteLength(JSON.stringify(cappedEmitted.manifest)), 131072);
  const over = clone(fixtureView('saved_single_issuer.json'));
  over.name = 'q'.repeat(atCap + 1);
  assertRefusal(Briefcase, over, 'manifest_too_large', '$');
  // Accepted case: every committed fixture manifest is far under the cap.
  for (const name of ['saved_single_issuer.json', 'saved_pinned.json', 'saved_with_evidence.json']) {
    const emitted = emitOk(Briefcase, fixtureView(name), name);
    assert.ok(byteLength(JSON.stringify(emitted.manifest)) <= 131072, name + ' is under the cap');
  }
  assertNoNetwork(Briefcase);
});

test('no-Segmenter free-text cut: the code-point fallback never splits a surrogate pair', () => {
  // r2 MINOR-2a: without Intl.Segmenter free text cuts at a code-point
  // boundary, so the 121-code-point name (119 a's + emoji + b) keeps the
  // whole emoji and drops only the b — the old UTF-16 slice left a lone
  // surrogate that made the stored view unexportable.
  const Briefcase = noSegmenterBriefcase(memoryStorage(), 0);
  const store = Briefcase.create({ now: () => '2026-10-12T00:00:00Z' });
  const view = fixtureView('saved_single_issuer.json');
  const emoji = String.fromCodePoint(0x1f600);
  const saved = store.save(Object.assign({}, view, { name: 'a'.repeat(119) + emoji + 'b' }));
  assert.equal(saved.ok, true, saved.reason || 'the repro name saves without a Segmenter');
  assert.equal(saved.view.name, 'a'.repeat(119) + emoji,
    'the fallback cut keeps the whole surrogate pair and drops only the b');
  const emitted = Briefcase.emitInvestigationManifestV2(saved.view);
  assert.ok(emitted.ok, 'the saved view still exports without a Segmenter');
  assert.equal(emitted.manifest.intent.title, saved.view.name);
});

test('reason sets: the declared refusal codes, and emit never throws', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  // r2 MINOR-3: the declared set gains the Terminal codes the emitter now
  // returns -- unsupported_code_point (py :45), too_many_items (py :139 via
  // :161) and manifest_too_large (py :169) -- and this suite exercises each.
  sameJson(Briefcase.MANIFEST_REFUSAL_REASONS, [
    'invalid_type', 'empty_text', 'invalid_control', 'invalid_unicode',
    'unsupported_code_point', 'text_too_long', 'invalid_date',
    'duplicate_reference', 'too_many_items', 'manifest_too_large'
  ]);
  // Non-views never throw; each is a typed refusal at the carrier path.
  for (const input of [undefined, 0, 'x', [], {}]) {
    const out = Briefcase.emitInvestigationManifestV2(input);
    assert.equal(out.ok, false);
    assert.equal(out.reason, 'schema');
    assert.equal(out.path, '$.fif_saved_research');
    SEEN_REFUSALS.add(out.reason);
  }
  // A view whose name is a number: refused at the title, never thrown.
  const numericName = clone(fixtureView('saved_single_issuer.json'));
  numericName.name = 42;
  const numericOut = Briefcase.emitInvestigationManifestV2(numericName);
  assert.equal(numericOut.ok, false);
  assert.equal(numericOut.reason, 'invalid_type');
  assert.equal(numericOut.path, '$.intent.title');
  SEEN_REFUSALS.add(numericOut.reason);
  // Every refusal this suite saw is a declared reason, and every manifest
  // refusal reason was exercised at least once above.
  for (const reason of SEEN_REFUSALS) {
    assert.ok(Briefcase.REFUSAL_REASONS.includes(reason) ||
      Briefcase.MANIFEST_REFUSAL_REASONS.includes(reason),
      'reason ' + reason + ' is declared');
  }
  for (const reason of Briefcase.MANIFEST_REFUSAL_REASONS) {
    assert.ok(SEEN_REFUSALS.has(reason), 'reason ' + reason + ' was exercised by this suite');
  }
  assertNoNetwork(Briefcase);
});
