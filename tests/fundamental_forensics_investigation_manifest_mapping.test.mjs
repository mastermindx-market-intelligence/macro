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

// X2-c r2 TEST-INDEPENDENCE ruling: the old textOf oracle re-implemented the
// emitter's own Intl.Segmenter cut, so it proved nothing. The oracle now pins
// one LITERAL title per fixture label — no algorithm, no Segmenter. A fixture
// without a pinned literal fails the lookup, so a new fixture cannot slip in
// unpinned. (A ZWJ-emoji literal and a combining-mark literal are pinned by
// the dedicated test at the bottom of this suite.) derived d2 is the only cut
// fixture: its title is the first 160 code points of its name.
const TITLE_LITERALS = Object.freeze({
  'saved_single_issuer.json': 'Apple baseline',
  'saved_cohort.json': 'Apple vs mega-cap peers',
  'saved_pinned.json': 'Apple pinned at September cutoff',
  'saved_latest.json': 'Apple latest check',
  'saved_with_evidence.json': 'Apple revenue evidence',
  'saved_with_finding.json': 'Apple receivables signal',
  'derived d1 (padded name)': '  Apple revenue evidence  ',
  'derived d2 (name over 160 code points)': 'Apple revenue evidence xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
  'derived d3 (empty occurrence_id)': 'Apple revenue evidence',
  'derived d4 (pinned with evidence)': 'Apple revenue evidence'
});

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

function expectedManifest(view, label) {
  const pinned = view.pinned === true;
  assert.ok(typeof TITLE_LITERALS[label] === 'string',
    'no pinned title literal for fixture ' + label);
  const manifest = {
    schema: MANIFEST_V2_SCHEMA,
    intent: {
      title: TITLE_LITERALS[label],
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
    assert.equal(canon(manifest), canon(expectedManifest(view, label)), label + ' equals the oracle');
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

// ── X2-b+c r2: NIT-1, NIT-2, the T-M7 added-rule assertions and the
// ZWJ/combining-mark title literals ─────────────────────────────────────────

test('NIT-1: from() refuses a manifest carrying a value JSON cannot round-trip', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const manifest = Briefcase.toInvestigationManifestV2(fixtureView('saved_with_evidence.json'));
  assert.ok(manifest);
  // A Date (and a Map or Set) has no enumerable own keys, so the old
  // canonicalJson rendered it as '{}' — byte-identical to the re-emitted
  // empty continuation — and the non-plain value slipped through the
  // comparison. A plain-value law (Terminal dataOnly,
  // investigationContracts.ts:89-131) refuses all of these first.
  const edits = [
    ['a Date continuation', (m) => { m.continuation = new Date(0); }],
    ['a Map continuation', (m) => { m.continuation = new Map(); }],
    ['a Set continuation', (m) => { m.continuation = new Set(); }],
    ['a sparse-array continuation', (m) => { m.continuation = ['a', , 'c']; }],
    ['a -0 continuation value', (m) => { m.continuation = { next_question: -0 }; }],
    ['a getter continuation', (m) => { m.continuation = {}; Object.defineProperty(m.continuation, 'next_question', { enumerable: true, get: () => 'x' }); }]
  ];
  for (const [name, edit] of edits) {
    const edited = JSON.parse(JSON.stringify(manifest));
    edit(edited);
    assert.equal(Briefcase.fromInvestigationManifestV2(edited), null, name + ' is refused');
  }
  // Accepted case: the plain manifest still maps back.
  assert.ok(Briefcase.fromInvestigationManifestV2(JSON.parse(JSON.stringify(manifest))));
  assertNoNetwork(Briefcase);
});

test('NIT-2: a carrier with an unknown key is refused — the stored-view key set is fixed', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const manifest = Briefcase.toInvestigationManifestV2(fixtureView('saved_with_evidence.json'));
  assert.ok(manifest);
  const edit = (mutate) => {
    const edited = JSON.parse(JSON.stringify(manifest));
    mutate(edited);
    return edited;
  };
  // Row-level unknown key: passed straight through before r2.
  assert.equal(Briefcase.fromInvestigationManifestV2(edit((m) => { m[CARRIER_KEY].evil_extra = 1; })), null,
    'a carrier with an unknown top-level key is refused');
  // Nested unknown keys refuse through their own normalisers.
  assert.equal(Briefcase.fromInvestigationManifestV2(edit((m) => { m[CARRIER_KEY].peers.evil_extra = 1; })), null,
    'a carrier with an unknown peers key is refused');
  assert.equal(Briefcase.fromInvestigationManifestV2(edit((m) => { m[CARRIER_KEY].view.evil_extra = 1; })), null,
    'a carrier with an unknown view key is refused');
  // Type swaps refuse with their own reasons.
  assert.equal(Briefcase.fromInvestigationManifestV2(edit((m) => { m[CARRIER_KEY].pinned = 'true'; })), null,
    'a string pinned is refused');
  assert.equal(Briefcase.fromInvestigationManifestV2(edit((m) => { m[CARRIER_KEY].view = 'radar'; })), null,
    'a string view is refused');
  // Accepted case: the untouched carrier still maps back.
  assert.ok(Briefcase.fromInvestigationManifestV2(JSON.parse(JSON.stringify(manifest))));
  assertNoNetwork(Briefcase);
});

test('T-M7 r2: layout/thesis role enums and thesis emptiness (py :108/:115, sql :126/:131, investigations.ts:52)', () => {
  const snapshot = JSON.parse(readFileSync(CONTRACT_SNAPSHOT, 'utf8'));
  assert.equal(snapshot.terminal_commit, 'c799ba7e64e2d0861228c9977cc12ed4a5d91982');
  // The added rules carry their citations.
  assert.deepEqual(snapshot.layout_refs.item_shape.role.enum.slice().sort(), ['primary', 'supporting']);
  assert.ok(snapshot.layout_refs.role_enum_source.includes('investigation_contracts.py:108'));
  assert.ok(snapshot.layout_refs.role_enum_source.includes('0028_investigations.sql:126'));
  assert.deepEqual(snapshot.thesis_refs.item_shape.role.enum.slice().sort(), ['alternative', 'context', 'primary']);
  assert.ok(snapshot.thesis_refs.item_shape.role.enum !== undefined);
  assert.equal(snapshot.thesis_refs.must_be_empty, true);
  assert.ok(snapshot.thesis_refs.must_be_empty_source.includes('0028_investigations.sql:131'));
  assert.ok(snapshot.thesis_refs.must_be_empty_source.includes('investigations.ts:52'));

  const Briefcase = freshBriefcase(memoryStorage(), 0);
  // Accepted case: every emitted manifest carries no layout and no thesis
  // refs — the G1 emptiness law holds on the emitter's whole output surface.
  for (const { label, view } of FIXTURES) {
    const manifest = Briefcase.toInvestigationManifestV2(view);
    assert.ok(manifest, label + ' maps');
    sameJson(manifest.layout_refs, [], label + ': no layout refs');
    sameJson(manifest.thesis_refs, [], label + ': no thesis refs');
  }
  // Refused case: from() refuses a manifest carrying a thesis ref — a role
  // inside the enum and a role outside it alike (Terminal G1 admits no
  // unverified Thesis rows, whatever the role).
  const base = Briefcase.toInvestigationManifestV2(fixtureView('saved_single_issuer.json'));
  for (const role of ['primary', 'alternative', 'context', 'bogus']) {
    const withThesis = JSON.parse(JSON.stringify(base));
    withThesis.thesis_refs = [{
      thesis_id: '01234567-89ab-cdef-0123-456789abcdef',
      version_id: '01234567-89ab-cdef-0123-456789abcdef',
      role: role
    }];
    assert.equal(Briefcase.fromInvestigationManifestV2(withThesis), null,
      'a manifest with a thesis ref (role ' + role + ') is refused');
  }
  assertNoNetwork(Briefcase);
});

test('T-M7 r2: the combined reference cap (py :162, sql :120)', () => {
  const snapshot = JSON.parse(readFileSync(CONTRACT_SNAPSHOT, 'utf8'));
  assert.equal(snapshot.reference_totals.max_combined, 128);
  assert.ok(snapshot.reference_totals.source.includes('investigation_contracts.py:162'));
  assert.ok(snapshot.reference_totals.source.includes('0028_investigations.sql:120'));

  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const refsOf = (count) => Array.from({ length: count }, (_, index) => ({
    accession: 'A' + index,
    occurrence_id: 'occurrence-' + index,
    source_span: [index, index + 1]
  }));
  // Refused case at the emitter's reachable boundary (an all-evidence
  // manifest): 129 refs refuse with Terminal's first code for this shape —
  // the per-list too_many_items of py :161, which fires before :162.
  const over = fixtureView('saved_with_evidence.json');
  over.evidence_refs = refsOf(129);
  sameJson(Briefcase.emitInvestigationManifestV2(over),
    { ok: false, reason: 'too_many_items', path: '$.evidence_refs' });
  // Accepted case: 128 refs emit, and the emitted total (layout + thesis +
  // evidence) is exactly the snapshot's combined cap.
  const atLimit = fixtureView('saved_with_evidence.json');
  atLimit.evidence_refs = refsOf(128);
  const emitted = Briefcase.emitInvestigationManifestV2(atLimit);
  assert.ok(emitted.ok);
  assert.equal(emitted.manifest.layout_refs.length + emitted.manifest.thesis_refs.length +
    emitted.manifest.evidence_refs.length, snapshot.reference_totals.max_combined);
  // Refused case past the emitter's shape: a manifest whose layout ref pushes
  // the combined total to 129 is refused by from().
  const combined = JSON.parse(JSON.stringify(emitted.manifest));
  combined.layout_refs = [{
    layout_id: '01234567-89ab-cdef-0123-456789abcdef',
    layout_revision_id: '01234567-89ab-cdef-0123-456789abcdef',
    digest: 'a'.repeat(64),
    role: 'primary'
  }];
  assert.equal(Briefcase.fromInvestigationManifestV2(combined), null,
    '129 combined refs are refused at from()');
  assertNoNetwork(Briefcase);
});

test('T-M7 r2: the manifest size cap (py :169, sql :93)', () => {
  const snapshot = JSON.parse(readFileSync(CONTRACT_SNAPSHOT, 'utf8'));
  assert.equal(snapshot.manifest_size.max_bytes, 131072);
  assert.ok(snapshot.manifest_size.source.includes('investigation_contracts.py:169'));
  assert.ok(snapshot.manifest_size.source.includes('0028_investigations.sql:93'));
  assert.ok(snapshot.manifest_size.measure.includes('UTF-8 octet length'));

  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const byteLength = (text) => new TextEncoder().encode(text).length;
  // Accepted case: every fixture manifest sits under the cap by the suite's
  // own canonical measure. (The 131072/131073 boundary pair is pinned by the
  // emitter suite's manifest_too_large test.)
  for (const { label, view } of FIXTURES) {
    const manifest = Briefcase.toInvestigationManifestV2(view);
    assert.ok(manifest, label + ' maps');
    assert.ok(byteLength(canon(manifest)) <= snapshot.manifest_size.max_bytes,
      label + ' is under the size cap');
  }
  assertNoNetwork(Briefcase);
});

test('T-M7 r3: the NUL code and the corrected per-code-point order (py :39-48, ts :143-157)', () => {
  const snapshot = JSON.parse(readFileSync(CONTRACT_SNAPSHOT, 'utf8'));
  assert.equal(snapshot.text_checks.nul_code, 'unsupported_code_point');
  // r3 R3-5: the corrected order — empty_text runs on the whole string BEFORE
  // any code point (py :41 ahead of the loop at :42-46), and invalid_control
  // is a whole-string scan AFTER the per-code-point loop (py :47-48).
  sameJson(snapshot.text_checks.per_code_point_order,
    ['empty_text', 'invalid_unicode', 'unsupported_code_point', 'text_too_long', 'invalid_control']);
  assert.ok(snapshot.text_checks.source.includes('investigation_contracts.py:39-48'));

  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const NUL = String.fromCharCode(0);
  // Refused case: an empty string gives empty_text before anything else, even
  // when another field would refuse too (the title check runs first).
  const blankName = fixtureView('saved_single_issuer.json');
  blankName.name = '';
  blankName.issuer.entity_id = 'ISS:x' + NUL;
  sameJson(Briefcase.emitInvestigationManifestV2(blankName),
    { ok: false, reason: 'empty_text', path: '$.intent.title' });
  // Refused case: NUL reports Terminal's code, not invalid_control.
  const nulName = fixtureView('saved_single_issuer.json');
  nulName.name = 'Apple' + NUL + 'baseline';
  sameJson(Briefcase.emitInvestigationManifestV2(nulName),
    { ok: false, reason: snapshot.text_checks.nul_code, path: '$.intent.title' });
  // Accepted case: the same name without the NUL emits.
  const cleanName = fixtureView('saved_single_issuer.json');
  cleanName.name = 'Apple baseline';
  assert.ok(Briefcase.emitInvestigationManifestV2(cleanName).ok);
  assertNoNetwork(Briefcase);
});

test('T-M7 r3: the emitter follows the Python checker\'s refusal order — known divergences (r3 R3-5)', () => {
  const snapshot = JSON.parse(readFileSync(CONTRACT_SNAPSHOT, 'utf8'));
  // The snapshot states exactly which checker's order the emitter follows.
  assert.equal(snapshot.emitter_refusal_order.follows, 'api/investigation_contracts.py');
  assert.ok(Array.isArray(snapshot.known_divergences) && snapshot.known_divergences.length >= 3,
    'the divergence set is recorded, never implied by an "exact mirror" claim');
  for (const entry of snapshot.known_divergences) {
    assert.ok(entry.source, 'every divergence entry carries a source citation');
  }

  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const byAspect = (aspect) => snapshot.known_divergences.find((entry) => entry.aspect === aspect);

  // Divergence 1 — the TypeScript checker runs the size cap FIRST
  // (investigationContracts.ts:277-283), so a manifest that is BOTH over
  // 131072 bytes AND over the evidence cap is manifest_too_large there; py
  // checks the field first (:161 before :169) and so does the emitter. The
  // emitter must return the entry's Python-side code.
  const bigId = (index) => '字'.repeat(250) + String(index).padStart(6, '0'); // 256 code points, ~756 UTF-8 octets, unique per ref
  const refsOf = (count) => Array.from({ length: count }, (_, index) => ({
    accession: 'A' + index,
    occurrence_id: bigId(index),
    source_span: [index, index + 1]
  }));
  // Guard: at 128 refs (within the cap) the same ids already exceed the byte
  // cap, so the 129-ref case below trips BOTH conditions and only the check
  // ORDER decides the code.
  const atCapBytes = fixtureView('saved_with_evidence.json');
  atCapBytes.evidence_refs = refsOf(128);
  sameJson(Briefcase.emitInvestigationManifestV2(atCapBytes),
    { ok: false, reason: 'manifest_too_large', path: '$' },
    'guard: 128 refs of 768-octet ids already exceed 131072 bytes');
  const oversized = fixtureView('saved_with_evidence.json');
  oversized.evidence_refs = refsOf(129);
  const divergenceSize = byAspect('size cap ordering');
  const emittedSize = Briefcase.emitInvestigationManifestV2(oversized);
  sameJson(emittedSize, { ok: false, reason: divergenceSize.python.code, path: divergenceSize.python.path });
  assert.equal(divergenceSize.typescript.code, 'manifest_too_large');
  assert.equal(divergenceSize.typescript.path, '$');

  // Divergence 2 — the TypeScript checker runs the combined
  // too_many_references check (investigationContracts.ts:250) BEFORE the
  // per-list checks (:258-260), so 129 evidence refs is '$
  // too_many_references' there; py :161 fires first and the emitter agrees.
  const over = fixtureView('saved_with_evidence.json');
  over.evidence_refs = Array.from({ length: 129 }, (_, index) => ({
    accession: 'A' + index,
    occurrence_id: 'occurrence-' + index,
    source_span: [index, index + 1]
  }));
  const divergenceRefs = byAspect('combined reference total ordering');
  const emittedRefs = Briefcase.emitInvestigationManifestV2(over);
  sameJson(emittedRefs, { ok: false, reason: divergenceRefs.python.code, path: divergenceRefs.python.path });
  assert.equal(divergenceRefs.typescript.code, 'too_many_references');
  assert.equal(divergenceRefs.typescript.path, '$');

  // Divergence 3 — the size-measure number rendering: the emitter can never
  // emit a non-integer (Math.trunc over finite guards,
  // fif_saved_briefcase.js:315-316/:296-297) but it can emit an
  // integer-valued float >= 1e21, which the emitter and py render as 1e+300
  // and the sql jsonb canonical text renders as 1e300.
  const divergenceNumbers = byAspect('size-measure number rendering');
  assert.equal(divergenceNumbers.emitter_and_python_render, '1e+300');
  assert.equal(divergenceNumbers.sql_renders, '1e300');
  const hugePeerN = fixtureView('saved_single_issuer.json');
  hugePeerN.peers.peer_n = 1e300;
  const emittedHuge = Briefcase.emitInvestigationManifestV2(hugePeerN);
  assert.ok(emittedHuge.ok, 'the exponent-form integer-valued float still emits');
  assert.ok(canon(emittedHuge.manifest).includes('"peer_n":1e+300'),
    'the emitter\'s canonical bytes render the number the way py json.dumps does');
  assertNoNetwork(Briefcase);
});

test('T-M7 r2: the owner-to-kind pairing (investigations.ts:9-10)', () => {
  const snapshot = JSON.parse(readFileSync(CONTRACT_SNAPSHOT, 'utf8'));
  assert.equal(canon(snapshot.subjects.owner_kinds), canon([
    { owner: 'terminal.analysis_symbol', kinds: ['security'] },
    { owner: 'data_os.security_master', kinds: ['security', 'issuer'] }
  ]), 'the pairing matches investigations.ts:9-10 exactly');
  assert.ok(snapshot.subjects.owner_kinds_source.includes('investigations.ts:9-10'));
  const admitted = (owner, kind) =>
    snapshot.subjects.owner_kinds.some((pair) => pair.owner === owner && pair.kinds.includes(kind));
  // Accepted cases: each admitted owner/kind pair of the G1 adapters.
  assert.equal(admitted('terminal.analysis_symbol', 'security'), true);
  assert.equal(admitted('data_os.security_master', 'security'), true);
  assert.equal(admitted('data_os.security_master', 'issuer'), true);
  // Refused case: a kind under the wrong owner is not admitted.
  assert.equal(admitted('terminal.analysis_symbol', 'issuer'), false);
  assert.equal(admitted('fif', 'issuer'), false);
  // Against the emitter's output: the emitted subject (owner 'fif', kind
  // 'issuer') is not admitted by the pairing — the recorded Terminal-side
  // gap (census GATE TEXT), never silently repaired here.
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const manifest = Briefcase.toInvestigationManifestV2(fixtureView('saved_single_issuer.json'));
  assert.ok(manifest);
  assert.equal(admitted(manifest.intent.subjects[0].owner, manifest.intent.subjects[0].kind), false,
    'the emitted subject is honestly outside the admitted pairs');
  // Refused at from(): a manifest whose subject was edited to an admitted
  // pair is an edited projection all the same.
  const edited = JSON.parse(JSON.stringify(manifest));
  edited.intent.subjects[0].owner = 'data_os.security_master';
  assert.equal(Briefcase.fromInvestigationManifestV2(edited), null);
  assertNoNetwork(Briefcase);
});

test('T-M7 r2: the optional evidence keys version_ref, fingerprint, selection (py :119)', () => {
  const snapshot = JSON.parse(readFileSync(CONTRACT_SNAPSHOT, 'utf8'));
  sameJson(snapshot.evidence_refs.optional_keys, ['version_ref', 'fingerprint', 'selection']);
  assert.ok(snapshot.evidence_refs.optional_keys_source.includes('investigation_contracts.py:119'));

  const Briefcase = freshBriefcase(memoryStorage(), 0);
  // Accepted case: across every fixture, a pinned ref carries version_ref
  // (an optional key lawfully present) and a follow_head ref carries neither
  // version_ref nor fingerprint (py :130, ts :233-235).
  let sawPinned = false;
  let sawFollowHead = false;
  for (const { label, view } of FIXTURES) {
    const manifest = Briefcase.toInvestigationManifestV2(view);
    assert.ok(manifest, label + ' maps');
    for (const ref of manifest.evidence_refs) {
      if (ref.mode === 'pinned') {
        sawPinned = true;
        assert.ok(Object.prototype.hasOwnProperty.call(ref, 'version_ref'), label + ': pinned carries version_ref');
        assert.equal('fingerprint' in ref, false, label + ': the emitter sets no fingerprint');
        assert.equal('selection' in ref, false, label + ': the emitter sets no selection');
      } else {
        sawFollowHead = true;
        assert.equal('version_ref' in ref || 'fingerprint' in ref, false,
          label + ': follow_head carries neither version_ref nor fingerprint');
      }
    }
  }
  assert.ok(sawPinned && sawFollowHead, 'both ref modes appear across the fixtures');
  // Refused case: from() refuses a manifest whose follow_head ref gained a
  // fingerprint — Terminal refuses that shape, and the exact-image law
  // refuses it here.
  const manifest = Briefcase.toInvestigationManifestV2(fixtureView('saved_with_evidence.json'));
  const edited = JSON.parse(JSON.stringify(manifest));
  edited.evidence_refs[0].fingerprint = 'a'.repeat(64);
  assert.equal(Briefcase.fromInvestigationManifestV2(edited), null);
  assertNoNetwork(Briefcase);
});

test('oracle literals: a ZWJ emoji sequence and a combining-mark title are pinned as literals', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  // One ZWJ family (4 astral emoji + 3 ZWJs = 7 code points, 11 UTF-16
  // units, ONE grapheme) and one combining-mark e-acute, each sized so the
  // 160-code-point title keeps them WHOLE. The expectations are the literal
  // strings themselves — no Segmenter, no algorithm, nothing derived.
  const family = String.fromCodePoint(0x1f468, 0x200d, 0x1f469, 0x200d, 0x1f467, 0x200d, 0x1f466);
  const acute = 'e' + String.fromCharCode(0x301);
  for (const [label, name, literal] of [
    ['the ZWJ family title', 'a'.repeat(153) + family, 'a'.repeat(153) + family],
    ['the combining-mark title', 'x'.repeat(158) + acute, 'x'.repeat(158) + acute]
  ]) {
    const view = fixtureView('saved_single_issuer.json');
    view.name = name;
    const emitted = Briefcase.emitInvestigationManifestV2(view);
    assert.ok(emitted.ok, label + ' emits');
    assert.equal(emitted.manifest.intent.title, literal, label + ' is the literal, grapheme whole');
    sameJson(emitted.notices, [], label + ' needs no cut');
    assert.ok(Briefcase.fromInvestigationManifestV2(JSON.parse(JSON.stringify(emitted.manifest))),
      label + ' maps back');
  }
  assertNoNetwork(Briefcase);
});
