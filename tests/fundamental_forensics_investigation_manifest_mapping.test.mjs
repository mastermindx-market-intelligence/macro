// FIF X2-b mapping suite (hermetic: no network, no browser).
//
// Pins the lossless 1:1 mapping between the device-local saved view A
// (templates/fif_saved_briefcase.js) and the Terminal investigations
// manifest v2 B that toInvestigationManifestV2 emits, against the committed
// Terminal contract snapshot (tests/fixtures/fundamental_forensics/
// fif_saved_research/terminal_investigation_manifest_v2.contract.json,
// census commit c799ba7e) and the census doc
// (research/financial_intelligence_fabric/
// FIF_X2B_TERMINAL_INVESTIGATIONS_CENSUS.md):
//   - every fixture, committed and derived, is a lawful view the module maps
//   - T-M1 A->B->A through JSON storage, and through a Postgres jsonb key
//     reorder (key order must never decide equality)
//   - T-M2 the field-by-field mapping table as a frozen constant, checked by
//     an independent oracle that never calls the module
//   - T-M3 injectivity: distinct lawful views map to distinct manifests
//   - T-M4 B->A->B stability, jsonb reorder included
//   - T-M5 the exact-image law: from() refuses every edited projection
//   - T-M6 refusals (null/array/drift/blank ids), none of them throwing
//   - T-M7 contract conformance against the snapshot, with the frozen
//     Terminal-side gap set (census doc section GATE TEXT)
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const BRIEFCASE_SOURCE = readFileSync(new URL('../templates/fif_saved_briefcase.js', import.meta.url), 'utf8');
const FIXTURE_DIR = new URL('../tests/fixtures/fundamental_forensics/fif_saved_research/', import.meta.url);
const CONTRACT_SNAPSHOT = new URL('terminal_investigation_manifest_v2.contract.json', FIXTURE_DIR);
const CARRIER_KEY = 'fif_saved_research';
const MANIFEST_V2_SCHEMA = 'investigation_manifest.v2';

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

// Exactly the roundtrip suite's freshBriefcase: the context's transports
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

// vm realms give objects a foreign prototype, so deepStrictEqual rejects
// structurally identical values; JSON text equality is realm-blind.
function sameJson(actual, expected) {
  assert.equal(JSON.stringify(actual), JSON.stringify(expected));
}

// Sorted-key canonical JSON: the same semantics as the module's
// canonicalJson (arrays keep their order, object keys sort, primitives
// render as plain JSON, undefined renders as null).
function canon(value) {
  if (Array.isArray(value)) return '[' + value.map(canon).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + canon(value[key])).join(',') + '}';
  }
  return value === undefined ? 'null' : JSON.stringify(value);
}

// The Postgres jsonb storage order: recursively rebuild every object with
// keys sorted by (key length, then code units). A manifest stored in a jsonb
// column comes back with exactly this key order.
function jsonbOrder(value) {
  if (Array.isArray(value)) return value.map(jsonbOrder);
  if (value && typeof value === 'object') {
    const out = {};
    Object.keys(value)
      .sort((a, b) => (a.length - b.length) || (a < b ? -1 : a > b ? 1 : 0))
      .forEach((key) => { out[key] = jsonbOrder(value[key]); });
    return out;
  }
  return value;
}

function fixtureView(name) {
  return JSON.parse(readFileSync(new URL(name, FIXTURE_DIR), 'utf8')).saved_views[0];
}

// Derived variants, built from saved_with_evidence.json; each must stay a
// lawful view the module itself maps (asserted in the first test):
// X2-c pin P-DERIVED-D1/D2: trimmed title projection / first 160 code units -> padded name VERBATIM / whole-grapheme cut reported as a title_cut notice
//   d1 name with leading/trailing spaces (the title row keeps the padded
//      name VERBATIM; nothing is trimmed)
//   d2 name longer than 160 code points: the title row is its whole-grapheme
//      cut, reported as a title_cut notice
//   d3 an evidence ref whose occurrence_id is the empty string, so the
//      object_id row falls back to the accession
//   d4 the view with pinned: true — REQUIRED, never dropped: the only
//      fixture with pinned evidence refs (its request policy already carries
//      both clocks), so the pinned rows of the table and the snapshot's
//      pinned_requires rule both depend on it
function derivedVariants() {
  const base = fixtureView('saved_with_evidence.json');
  const d1 = JSON.parse(JSON.stringify(base));
  d1.name = '  ' + base.name + '  ';
  const d2 = JSON.parse(JSON.stringify(base));
  d2.name = base.name + ' ' + 'x'.repeat(180);
  const d3 = JSON.parse(JSON.stringify(base));
  d3.evidence_refs[0].occurrence_id = '';
  const d4 = JSON.parse(JSON.stringify(base));
  d4.pinned = true;
  return [
    { label: 'derived d1 (padded name)', view: d1 },
    { label: 'derived d2 (name over 160 code points)', view: d2 },
    { label: 'derived d3 (empty occurrence_id)', view: d3 },
    { label: 'derived d4 (pinned with evidence)', view: d4 }
  ];
}

const FIXTURES = [
  'saved_single_issuer.json',
  'saved_cohort.json',
  'saved_pinned.json',
  'saved_latest.json',
  'saved_with_evidence.json',
  'saved_with_finding.json'
].map((name) => ({ label: name, view: fixtureView(name) })).concat(derivedVariants());

// X2-c pin P-ORACLE-TEXTOF: trim + UTF-16 slice -> verbatim code points with a whole-grapheme cut.
// The X2-c emitter's text semantics, restated for the oracle: a non-string is
// the empty string; a value that fits in `limit` CODE POINTS is kept VERBATIM
// (never trimmed); an over-limit value keeps the longest prefix of whole
// grapheme clusters (Intl.Segmenter, granularity 'grapheme') whose code-point
// total is within the limit.
function textOf(value, limit) {
  if (typeof value !== 'string') return '';
  if (Array.from(value).length <= limit) return value;
  let prefix = '';
  let count = 0;
  for (const { segment } of new Intl.Segmenter('en', { granularity: 'grapheme' }).segment(value)) {
    const size = Array.from(segment).length;
    if (count + size > limit) break;
    prefix += segment;
    count += size;
  }
  return prefix;
}

// The pinned 1:1 mapping TABLE: one row per top-level B key plus the intent
// sub-fields. `from` states the A-side rule in plain words; expectedManifest
// below implements exactly these rows and never calls the module.
const MAPPING = Object.freeze([
  Object.freeze({ path: 'schema', from: "constant 'investigation_manifest.v2'" }),
  // X2-c pin P-MAP-TITLE: A.name trimmed, first 160 code units -> verbatim code points, whole-grapheme cut, typed refusal when no cut exists
  Object.freeze({
    path: 'intent.title',
    from: "A.name verbatim (never trimmed) when it has at most 160 code points; otherwise its longest whole-grapheme prefix within 160 code points plus a title_cut notice; refused (text_too_long) when no non-blank whole-grapheme prefix exists"
  }),
  Object.freeze({ path: 'intent.question', from: "constant 'Filing forensics saved view'" }),
  // X2-c pin P-MAP-SUBJECTS: entity_id trimmed, first 256 -> verbatim, never cut, over 256 code points refuses
  Object.freeze({
    path: 'intent.subjects',
    from: "[{kind:'issuer', owner:'fif', object_id: A.issuer.entity_id verbatim (never trimmed or cut; over 256 code points refuses text_too_long)}]"
  }),
  // X2-c pin P-MAP-RESEARCH-AS-OF: trimmed regex match -> UNTRIMMED real-calendar date check with a typed invalid_date refusal
  Object.freeze({
    path: 'intent.research_as_of',
    from: "only when A.pinned === true: the first 10 chars of the UNTRIMMED A.request.policy.source_snapshot_at, which must be a real calendar date followed by end-of-string or T/t/space (otherwise the view refuses invalid_date); absent when not pinned"
  }),
  Object.freeze({ path: 'layout_refs', from: '[]' }),
  Object.freeze({ path: 'thesis_refs', from: '[]' }),
  // X2-c pin P-MAP-EVIDENCE-REFS: lawful refs only, trimmed/cut ids, silently dropped -> every ref in order, verbatim ids, typed refusals
  Object.freeze({
    path: 'evidence_refs',
    from: "every A.evidence_refs[i], in order, never dropped or deduped: object_id = occurrence_id, or accession when occurrence_id is absent/null/'' (verbatim, at most 256 code points); mode pinned|follow_head; version_ref = accession, or object_id when accession is absent/null/'', only when pinned; a non-object ref refuses invalid_type, a blank id empty_text, a repeated Terminal identity tuple duplicate_reference"
  }),
  Object.freeze({ path: 'continuation', from: '{}' }),
  Object.freeze({ path: 'fif_saved_research', from: 'A verbatim' })
]);

// The top-level B keys the table names: every row's first path segment
// ('intent' arrives only through its dotted sub-field rows).
const MAPPING_TOP_LEVEL_KEYS = [...new Set(MAPPING.map((row) => row.path.split('.')[0]))];
const MAPPING_INTENT_KEYS = MAPPING.filter((row) => row.path.indexOf('intent.') === 0).map((row) => row.path.slice('intent.'.length));

// X2-c pin P-ORACLE-EXPECTED: trimmed/cut ids and a regex-only date check -> verbatim ids, no continue skips, an independent real-calendar check.
// The independent oracle built from MAPPING — it never calls the module.
// A date-shaped string is not enough: isRealDate(y, m, d) is written here,
// independently of the module, and rejects Feb 30, a non-leap Feb 29,
// month 13 and year 0.
function isRealDate(year, month, day) {
  if (year < 1 || month < 1 || month > 12 || day < 1) return false;
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const monthDays = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return day <= monthDays[month - 1];
}

function expectedManifest(view) {
  const pinned = view.pinned === true;
  const manifest = {
    schema: MANIFEST_V2_SCHEMA,
    intent: {
      title: textOf(view.name, 160),
      question: 'Filing forensics saved view',
      subjects: [{ kind: 'issuer', owner: 'fif', object_id: view.issuer.entity_id }]
    },
    layout_refs: [],
    thesis_refs: [],
    evidence_refs: [],
    continuation: {}
  };
  const refs = Array.isArray(view.evidence_refs) ? view.evidence_refs : [];
  for (const ref of refs) {
    const occurrence = ref.occurrence_id == null ? '' : ref.occurrence_id;
    const accession = ref.accession == null ? '' : ref.accession;
    const objectId = occurrence !== '' ? occurrence : accession;
    const entry = {
      owner: 'fif',
      object_type: 'occurrence',
      object_id: objectId,
      mode: pinned ? 'pinned' : 'follow_head'
    };
    if (pinned) entry.version_ref = accession !== '' ? accession : objectId;
    manifest.evidence_refs.push(entry);
  }
  if (pinned) {
    const policy = view.request && view.request.policy ? view.request.policy : {};
    const raw = typeof policy.source_snapshot_at === 'string' ? policy.source_snapshot_at : '';
    const match = /^(\d{4})-(\d{2})-(\d{2})(?:$|[Tt ])/.exec(raw);
    if (match && isRealDate(Number(match[1]), Number(match[2]), Number(match[3]))) {
      manifest.intent.research_as_of = match[1] + '-' + match[2] + '-' + match[3];
    }
  }
  manifest[CARRIER_KEY] = JSON.parse(JSON.stringify(view));
  return manifest;
}

// X2-c pin P-ORACLE-EMITS-RESEARCH-AS-OF: regex on the trimmed first 10 chars -> a lawful pinned view always emits.
// Whether the research_as_of row fires for one view (the intent key-set
// assertion holds per fixture, not per table): a lawful pinned view always
// carries a real calendar cutoff, so it always emits.
function emitsResearchAsOf(view) {
  return view.pinned === true;
}

// Census doc section GATE TEXT (research/financial_intelligence_fabric/
// FIF_X2B_TERMINAL_INVESTIGATIONS_CENSUS.md): these are exactly the
// Terminal-side changes a round trip THROUGH Terminal still needs (R2:
// delivered as gate text, never as a Terminal patch). The union of
// terminalGaps across every fixture must equal this list exactly.
const EXPECTED_TERMINAL_GAPS = [
  'evidence_refs.object_type:not_admitted',
  'evidence_refs.owner:not_admitted',
  'fif_saved_research:unknown_key_reject_python',
  'fif_saved_research:unknown_key_reject_typescript',
  'intent.subjects.owner:not_admitted'
];

// Every rule the committed snapshot states, checked against one manifest.
// A rule whose snapshot value is null is skipped; nothing is invented. Gap
// paths never carry an array index. Returns a sorted, de-duplicated array
// of '<path>:<code>' strings.
function terminalGaps(manifest, snapshot) {
  const gaps = new Set();
  const add = (path, code) => gaps.add(path + ':' + code);
  const pattern = (p) => {
    if (p == null) return null;
    try { return new RegExp(p); } catch (error) { throw new Error('snapshot pattern does not compile in JS: ' + p); }
  };
  // X2-c pin P-GAPS-LENGTH-MEASURE: UTF-16 .length -> code-point counts Array.from(value).length, here and in the title/question check below.
  const textRule = (value, path, rule) => {
    if (typeof value !== 'string') return;
    const codePoints = Array.from(value).length;
    if (rule.min_length != null && codePoints < rule.min_length) add(path, 'too_short');
    if (rule.max_length != null && codePoints > rule.max_length) add(path, 'too_long');
    const re = pattern(rule.pattern);
    if (re && !re.test(value)) add(path, 'pattern');
  };

  // schema field/value
  if (manifest[snapshot.schema.field] !== snapshot.schema.value) add('schema', 'not_admitted');

  // top level: a key outside top_level.fields is an unknown key on each side
  // whose policy rejects or drops (the carrier included); every required
  // field must be present.
  const topFields = snapshot.top_level.fields;
  for (const key of Object.keys(manifest)) {
    if (!Object.prototype.hasOwnProperty.call(topFields, key)) {
      for (const side of ['python', 'typescript']) {
        const policy = snapshot.top_level['unknown_key_policy_' + side];
        if (policy === 'reject' || policy === 'drop') add(key, 'unknown_key_' + policy + '_' + side);
      }
    }
  }
  for (const field of Object.keys(topFields)) {
    if (topFields[field].required && !Object.prototype.hasOwnProperty.call(manifest, field)) {
      add(field, 'missing');
    }
  }

  // intent: required fields, title/question length, research_as_of format
  const intent = manifest.intent && typeof manifest.intent === 'object' ? manifest.intent : {};
  const intentFields = snapshot.intent.fields;
  for (const field of Object.keys(intentFields)) {
    if (intentFields[field].required && !Object.prototype.hasOwnProperty.call(intent, field)) {
      add('intent.' + field, 'missing');
    }
  }
  for (const field of ['title', 'question']) {
    const rule = intentFields[field];
    if (rule && rule.max_length != null && typeof intent[field] === 'string' &&
        Array.from(intent[field]).length > rule.max_length) {
      add('intent.' + field, 'too_long');
    }
  }
  // research_as_of_format was asserted to be 'YYYY-MM-DD' by the caller and
  // translated to this regex — any other format string fails the test.
  if (typeof intent.research_as_of === 'string' && !/^\d{4}-\d{2}-\d{2}$/.test(intent.research_as_of)) {
    add('intent.research_as_of', 'format');
  }
  // X2-c pin P-GAPS-DATE: regex-shaped but not a real calendar date (Feb 30, a non-leap Feb 29, month 13) is also a format gap.
  if (typeof intent.research_as_of === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(intent.research_as_of)) {
    const [year, month, day] = intent.research_as_of.split('-').map(Number);
    if (!isRealDate(year, month, day)) add('intent.research_as_of', 'format');
  }

  // subjects: kind/owner admission, object_id length/pattern, count
  const subjects = Array.isArray(intent.subjects) ? intent.subjects : [];
  if (snapshot.subjects.max_items != null && subjects.length > snapshot.subjects.max_items) {
    add('intent.subjects', 'too_many');
  }
  for (const subject of subjects) {
    if (!subject || typeof subject !== 'object' || Array.isArray(subject)) continue;
    if (Array.isArray(snapshot.subjects.kinds) && !snapshot.subjects.kinds.includes(subject.kind)) {
      add('intent.subjects.kind', 'not_admitted');
    }
    if (snapshot.subjects.owners_closed === true && !snapshot.subjects.owners.includes(subject.owner)) {
      add('intent.subjects.owner', 'not_admitted');
    }
    textRule(subject.object_id, 'intent.subjects.object_id', snapshot.subjects.object_id);
  }

  // evidence_refs: owner/object_type admission, mode, pinned_requires,
  // follow_head_forbids, object_id/version_ref length/pattern, count
  const evidence = Array.isArray(manifest.evidence_refs) ? manifest.evidence_refs : [];
  if (snapshot.evidence_refs.max_items != null && evidence.length > snapshot.evidence_refs.max_items) {
    add('evidence_refs', 'too_many');
  }
  for (const ref of evidence) {
    if (!ref || typeof ref !== 'object' || Array.isArray(ref)) continue;
    if (snapshot.evidence_refs.owners_closed === true && !snapshot.evidence_refs.owners.includes(ref.owner)) {
      add('evidence_refs.owner', 'not_admitted');
    }
    if (snapshot.evidence_refs.object_types_closed === true &&
        !snapshot.evidence_refs.object_types.includes(ref.object_type)) {
      add('evidence_refs.object_type', 'not_admitted');
    }
    if (Array.isArray(snapshot.evidence_refs.modes) && !snapshot.evidence_refs.modes.includes(ref.mode)) {
      add('evidence_refs.mode', 'not_admitted');
    }
    if (ref.mode === 'pinned') {
      for (const key of snapshot.evidence_refs.pinned_requires) {
        if (!Object.prototype.hasOwnProperty.call(ref, key)) add('evidence_refs.' + key, 'missing');
      }
    }
    if (ref.mode === 'follow_head') {
      for (const key of snapshot.evidence_refs.follow_head_forbids) {
        if (Object.prototype.hasOwnProperty.call(ref, key)) add('evidence_refs.' + key, 'forbidden_present');
      }
    }
    textRule(ref.object_id, 'evidence_refs.object_id', snapshot.evidence_refs.object_id);
    if (Object.prototype.hasOwnProperty.call(ref, 'version_ref')) {
      textRule(ref.version_ref, 'evidence_refs.version_ref', snapshot.evidence_refs.version_ref);
    }
  }

  // layout_refs / thesis_refs counts
  const layout = Array.isArray(manifest.layout_refs) ? manifest.layout_refs : [];
  if (snapshot.layout_refs.max_items != null && layout.length > snapshot.layout_refs.max_items) {
    add('layout_refs', 'too_many');
  }
  const thesis = Array.isArray(manifest.thesis_refs) ? manifest.thesis_refs : [];
  if (snapshot.thesis_refs.max_items != null && thesis.length > snapshot.thesis_refs.max_items) {
    add('thesis_refs', 'too_many');
  }

  return Array.from(gaps).sort();
}

// Every pattern the snapshot states must compile in JS exactly as written —
// never rewritten. One that does not compile fails the test by name.
function assertSnapshotPatternsCompile(snapshot) {
  (function walk(node) {
    if (Array.isArray(node)) { node.forEach(walk); return; }
    if (node && typeof node === 'object') {
      for (const [key, value] of Object.entries(node)) {
        if (key === 'pattern' && typeof value === 'string') {
          try { new RegExp(value); } catch (error) {
            assert.fail('snapshot pattern does not compile in JS: ' + value);
          }
        } else {
          walk(value);
        }
      }
    }
  })(snapshot);
}

function assertNoNetwork(Briefcase) {
  assert.equal(Briefcase.__networkProbe.fetches, 0, 'zero fetches');
  assert.equal(Briefcase.__networkProbe.xhrs, 0, 'zero XMLHttpRequests');
}

test('every fixture, committed and derived, is a lawful view the module maps', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  for (const { label, view } of FIXTURES) {
    assert.ok(Briefcase.toInvestigationManifestV2(view), label + ' passes the module\'s own checks and maps');
  }
  assertNoNetwork(Briefcase);
});

test('T-M1: A->B->A through storage is lossless, even after a jsonb key reorder', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  for (const { label, view } of FIXTURES) {
    const manifest = Briefcase.toInvestigationManifestV2(view);
    assert.ok(manifest, label + ' maps A->B');
    // Plain JSON storage: serialize B, parse the bytes back, map B->A.
    const throughStorage = Briefcase.fromInvestigationManifestV2(JSON.parse(JSON.stringify(manifest)));
    assert.ok(throughStorage, label + ' maps back through JSON storage');
    sameJson(throughStorage, view);
    // Postgres jsonb storage: every object key reordered to the jsonb order
    // before the B->A map — key order must never decide equality.
    const throughJsonb = Briefcase.fromInvestigationManifestV2(jsonbOrder(JSON.parse(JSON.stringify(manifest))));
    assert.ok(throughJsonb, label + ' maps back through jsonb key order');
    assert.equal(canon(throughJsonb), canon(view));
  }
  assertNoNetwork(Briefcase);
});

test('T-M2: the mapping table — the module output equals the independent oracle, key for key', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const topLevelKeys = MAPPING_TOP_LEVEL_KEYS.slice().sort();
  for (const { label, view } of FIXTURES) {
    const manifest = Briefcase.toInvestigationManifestV2(view);
    assert.ok(manifest, label + ' maps');
    assert.equal(canon(manifest), canon(expectedManifest(view)), label + ' equals the oracle');
    sameJson(Object.keys(manifest).sort(), topLevelKeys, label + ': top-level keys are exactly the table rows');
    const intentKeys = MAPPING_INTENT_KEYS
      .filter((key) => key !== 'research_as_of' || emitsResearchAsOf(view))
      .sort();
    sameJson(Object.keys(manifest.intent).sort(), intentKeys, label + ': intent keys are exactly the table rows');
    // X2-c pin P-DERIVED-D1/D2: only the over-limit name is shortened, and the
    // cut is REPORTED — every other fixture (the padded d1 included) emits
    // its title untouched and no notice at all.
    const emitted = Briefcase.emitInvestigationManifestV2(view);
    assert.ok(emitted.ok, label + ' emits through the typed surface');
    const expectedNotices = label.indexOf('derived d2') === 0
      ? [{
          code: 'title_cut',
          path: '$.intent.title',
          code_points: Array.from(view.name).length,
          kept_code_points: 160
        }]
      : [];
    sameJson(emitted.notices, expectedNotices, label + ': notices are exactly the title cut');
  }
  assertNoNetwork(Briefcase);
});

test('T-M3: injectivity — distinct lawful views map to distinct manifests', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const strings = FIXTURES.map(({ label, view }) => {
    const manifest = Briefcase.toInvestigationManifestV2(view);
    assert.ok(manifest, label + ' maps');
    return canon(manifest);
  });
  assert.equal(new Set(strings).size, strings.length, 'the canon(to(v)) strings are pairwise distinct');

  // One-field changes on saved_with_evidence — each lawful per checkView —
  // must each move the manifest away from the unchanged projection and from
  // each other.
  const base = fixtureView('saved_with_evidence.json');
  const unchanged = canon(Briefcase.toInvestigationManifestV2(base));
  const nameChanged = JSON.parse(JSON.stringify(base));
  nameChanged.name = 'Apple revenue evidence, renamed';
  const issuerChanged = JSON.parse(JSON.stringify(base));
  issuerChanged.issuer.entity_id = 'ISS:US-XNAS-MSFT';
  const refChanged = JSON.parse(JSON.stringify(base));
  refChanged.evidence_refs[0].occurrence_id = 'rawfact_aapl_rev_fy2024_amended';
  const changed = [
    canon(Briefcase.toInvestigationManifestV2(nameChanged)),
    canon(Briefcase.toInvestigationManifestV2(issuerChanged)),
    canon(Briefcase.toInvestigationManifestV2(refChanged))
  ];
  for (const value of changed) {
    assert.notEqual(value, unchanged, 'a single-field change moves the manifest');
  }
  assert.equal(new Set(changed).size, changed.length, 'the three single-field changes give three distinct manifests');
  assertNoNetwork(Briefcase);
});

test('T-M4: B->A->B is stable, including through a jsonb key reorder', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  for (const { label, view } of FIXTURES) {
    const manifest = Briefcase.toInvestigationManifestV2(view);
    assert.ok(manifest, label + ' maps');
    const back = Briefcase.fromInvestigationManifestV2(manifest);
    assert.ok(back, label + ' maps back');
    assert.equal(canon(Briefcase.toInvestigationManifestV2(back)), canon(manifest), label + ': B->A->B stable');
    const jsonb = jsonbOrder(JSON.parse(JSON.stringify(manifest)));
    const backThroughJsonb = Briefcase.fromInvestigationManifestV2(jsonb);
    assert.ok(backThroughJsonb, label + ' maps back through jsonb key order');
    assert.equal(canon(Briefcase.toInvestigationManifestV2(backThroughJsonb)), canon(manifest),
      label + ': B->A->B stable through jsonb key order');
  }
  assertNoNetwork(Briefcase);
});

test('T-M5: the exact-image law — from() refuses every edited projection', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const view = fixtureView('saved_with_evidence.json');
  const manifest = Briefcase.toInvestigationManifestV2(view);
  assert.ok(manifest);
  // Control: the untouched manifest maps back.
  sameJson(Briefcase.fromInvestigationManifestV2(JSON.parse(JSON.stringify(manifest))), view);

  const edits = [
    ['intent.title changed', (m) => { m.intent.title = 'A different title'; }],
    ['intent.question changed', (m) => { m.intent.question = 'A different question'; }],
    ['subjects[0].object_id changed', (m) => { m.intent.subjects[0].object_id = 'ISS:US-XNAS-MSFT'; }],
    ['subjects[0].owner changed', (m) => { m.intent.subjects[0].owner = 'data_os.security_master'; }],
    ['an evidence_refs entry removed', (m) => { m.evidence_refs.pop(); }],
    ["an evidence_refs entry's mode flipped", (m) => { m.evidence_refs[0].mode = 'pinned'; }],
    ['an extra top-level key added', (m) => { m.review_baseline_ref = {}; }],
    ['continuation given a key', (m) => { m.continuation.next_question = 'what next?'; }],
    ['research_as_of added to a follow_head manifest', (m) => { m.intent.research_as_of = '2026-10-11'; }]
  ];
  for (const [name, edit] of edits) {
    const edited = JSON.parse(JSON.stringify(manifest));
    edit(edited);
    assert.equal(Briefcase.fromInvestigationManifestV2(edited), null, name + ' refuses');
  }
  assertNoNetwork(Briefcase);
});

test('T-M6: refusals — null, arrays, drift and blank ids never throw', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const base = fixtureView('saved_single_issuer.json');

  // to() refuses: null, an array, a view failing checkView (schema changed),
  // and a view whose issuer.entity_id is empty or whitespace.
  assert.equal(Briefcase.toInvestigationManifestV2(null), null);
  assert.equal(Briefcase.toInvestigationManifestV2([]), null);
  const drifted = JSON.parse(JSON.stringify(base));
  drifted.schema = 'fundamental_forensics.saved_research.v9';
  assert.equal(Briefcase.toInvestigationManifestV2(drifted), null);
  const blankIssuer = JSON.parse(JSON.stringify(base));
  blankIssuer.issuer.entity_id = '';
  assert.equal(Briefcase.toInvestigationManifestV2(blankIssuer), null);
  const whitespaceIssuer = JSON.parse(JSON.stringify(base));
  whitespaceIssuer.issuer.entity_id = '   ';
  assert.equal(Briefcase.toInvestigationManifestV2(whitespaceIssuer), null);

  // X2-c pin P-T-M6-TYPED: the null returns above are typed refusals now.
  for (const [input, reason, path] of [
    [null, 'schema', '$.fif_saved_research'],
    [[], 'schema', '$.fif_saved_research'],
    [drifted, 'schema', '$.fif_saved_research'],
    [blankIssuer, 'empty_text', '$.intent.subjects[0].object_id'],
    [whitespaceIssuer, 'empty_text', '$.intent.subjects[0].object_id']
  ]) {
    sameJson(Briefcase.emitInvestigationManifestV2(input), { ok: false, reason: reason, path: path });
  }

  // from() refuses: null, an array, a v1 schema, a deleted carrier, an array
  // carrier, and a carrier that fails checkView.
  assert.equal(Briefcase.fromInvestigationManifestV2(null), null);
  assert.equal(Briefcase.fromInvestigationManifestV2([]), null);
  assert.equal(Briefcase.fromInvestigationManifestV2({ schema: 'investigation_manifest.v1' }), null);
  const manifest = Briefcase.toInvestigationManifestV2(base);
  assert.ok(manifest);
  const carrierDeleted = JSON.parse(JSON.stringify(manifest));
  delete carrierDeleted[CARRIER_KEY];
  assert.equal(Briefcase.fromInvestigationManifestV2(carrierDeleted), null);
  const carrierArray = JSON.parse(JSON.stringify(manifest));
  carrierArray[CARRIER_KEY] = [];
  assert.equal(Briefcase.fromInvestigationManifestV2(carrierArray), null);
  const carrierDrifted = JSON.parse(JSON.stringify(manifest));
  carrierDrifted[CARRIER_KEY].schema = 'fundamental_forensics.saved_research.v9';
  assert.equal(Briefcase.fromInvestigationManifestV2(carrierDrifted), null);
  assertNoNetwork(Briefcase);
});

test('T-M7: contract conformance against the committed Terminal snapshot', () => {
  const snapshot = JSON.parse(readFileSync(CONTRACT_SNAPSHOT, 'utf8'));
  assert.equal(snapshot.terminal_commit, 'c799ba7e64e2d0861228c9977cc12ed4a5d91982');
  assert.equal(snapshot.intent.research_as_of_format, 'YYYY-MM-DD',
    'unhandled research_as_of_format in the snapshot: ' + snapshot.intent.research_as_of_format);
  assertSnapshotPatternsCompile(snapshot);

  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const union = new Set();
  for (const { label, view } of FIXTURES) {
    const manifest = Briefcase.toInvestigationManifestV2(view);
    assert.ok(manifest, label + ' maps');
    for (const gap of terminalGaps(manifest, snapshot)) union.add(gap);
  }
  const computed = Array.from(union).sort();
  assert.equal(JSON.stringify(computed), JSON.stringify(EXPECTED_TERMINAL_GAPS),
    'terminal gap set differs — computed ' + JSON.stringify(computed));
  assertNoNetwork(Briefcase);
});
