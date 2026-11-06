/* fif_saved_briefcase.js
 *
 * FIF X2-s saved views — the device-local briefcase for Filing Forensics,
 * following the Government Revenue briefcase discipline
 * (templates/government-revenue-briefcase.js): this module never fetches,
 * polls, sends a notification, or talks to an account service. It is a
 * page integration seam; the page owns rendering and every network call.
 *
 * Storage: one device-local key, mastermind.filing_forensics.saved_research.v1,
 * holding {contract:"fundamental_forensics.saved_research.v1", saved_views:[…]}
 * — no inbox key (no in-product inbox in this wave).
 *
 * Every saved view embeds the X0 request it was saved against, verbatim and
 * canonicalised, plus a top-level request_contract naming that contract
 * version. A load REFUSES — plain "saved view unavailable", never a crash,
 * never a repair, never a migration, never a silent drop — when any contract
 * check fails. A refused view stays listed (as unavailable) and may be
 * deleted. A container whose own bytes are unreadable (unparseable, drifted
 * contract, wrong shape) turns the whole store READ-ONLY for the session —
 * nothing is written back, so the user's bytes are never blanked to "heal".
 */
(function (root) {
  'use strict';

  var SAVED_SCHEMA = 'fundamental_forensics.saved_research.v1';
  var REQUEST_CONTRACT = 'fundamental_forensics.financial_query_request/v1';
  var STORAGE_KEY = 'mastermind.filing_forensics.saved_research.v1';
  var MANIFEST_V2_SCHEMA = 'investigation_manifest.v2';
  // The A→B migration carrier: every saved field with no manifest-v2 home
  // rides verbatim under this one key (X2-b, Terminal investigations).
  var CARRIER_KEY = 'fif_saved_research';
  var MANIFEST_OWNER = 'fif';
  var MAX_VIEWS = 24;
  var MAX_NAME_LENGTH = 120;
  var MAX_EVIDENCE_REFS = 16;
  var MAX_METRIC_IDS = 50;
  var MAX_PERIODS = 8;
  var MAX_CELLS = 400;
  var ID_LENGTH = 22;
  var ID_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  var ROOT_REQUEST_KEYS = ['schema', 'entity_id', 'policy', 'metric_ids', 'periods'];
  var POLICY_KEYS = ['selection', 'source_snapshot_at', 'recorded_at'];
  var PERIOD_KEYS = ['kind', 'start', 'end', 'label'];
  var SELECTIONS = ['as_reported', 'latest_known_as_of', 'latest_restated'];
  // X2-b+c r2 NIT-2: the exact stored-view key set. A row carrying anything
  // else refuses as schema drift — an unknown key never passes through
  // checkView into the page or a manifest carrier.
  var VIEW_KEYS = ['schema', 'request_contract', 'id', 'name', 'created_at', 'updated_at',
    'issuer', 'request', 'peers', 'view', 'pinned', 'saved_against', 'evidence_refs', 'watch'];
  // The declared refusal set: every reason a stored view (or the container
  // itself) can refuse with. tests/test_fundamental_forensics_saved_store_schema.py
  // pins this list exactly, both directions, and the Node suites pin each
  // reason behaviourally. Call outcomes that are not contract refusals
  // ('missing', 'name', 'request', 'limit', 'module') stay off the list.
  var REFUSAL_REASONS = [
    'schema',
    'request_contract',
    'request_schema',
    'request_root',
    'request_canonical',
    'pinned_type',
    'peers',
    'view',
    'pinned_cutoffs',
    'id',
    'unavailable',
    'storage'
  ];

  function object(value) {
    return !!value && typeof value === 'object' && !Array.isArray(value);
  }

  function array(value) {
    return Array.isArray(value) ? value : [];
  }

  function copy(value) {
    return JSON.parse(JSON.stringify(value));
  }

  // X2-b+c r2 MINOR-2: a text cut never mints a lone surrogate, and an
  // identifier is never cut at all. codePointPrefix is the base cut (whole
  // code points); freeText (names) prefers the emitter's own whole-grapheme
  // helper when Intl.Segmenter exists; idText refuses typed instead of
  // trimming an identifier to fit.
  function codePointPrefix(value, limit) {
    var out = '';
    var count = 0;
    for (var index = 0; index < value.length && count < limit; ) {
      var unit = value.charCodeAt(index);
      var size = unit >= 0xd800 && unit <= 0xdbff &&
        value.charCodeAt(index + 1) >= 0xdc00 && value.charCodeAt(index + 1) <= 0xdfff ? 2 : 1;
      out += value.slice(index, index + size);
      index += size;
      count += 1;
    }
    return out;
  }

  function text(value, limit) {
    if (typeof value !== 'string') return '';
    return codePointPrefix(value.trim(), limit == null ? 1000 : limit);
  }

  function freeText(value, limit) {
    if (typeof value !== 'string') return '';
    var trimmed = value.trim();
    if (!trimmed) return '';
    var count = codePoints(trimmed);
    if (count >= 0 && count <= limit) return trimmed;
    if (typeof Intl !== 'undefined' && typeof Intl.Segmenter === 'function') {
      var cut = wholeGraphemePrefix(trimmed, limit);
      if (cut !== null) return cut;
    }
    return text(trimmed, limit);
  }

  // Identifiers (issuer ids, evidence ids — anything the manifest projects
  // as object_id/version_ref) are NEVER cut: an over-limit id, or one
  // holding a lone surrogate, refuses with the emitter's own codes
  // (text_too_long / invalid_unicode) and nothing is stored.
  function idText(value, limit) {
    if (typeof value !== 'string') return { ok: true, value: '' };
    var trimmed = value.trim();
    if (!trimmed) return { ok: true, value: '' };
    var count = codePoints(trimmed);
    if (count < 0) return { ok: false, reason: 'invalid_unicode' };
    if (count > limit) return { ok: false, reason: 'text_too_long' };
    return { ok: true, value: trimmed };
  }

  // X2-b+c r3 R3-1: a field the emitter never emits keeps its cut rule, but
  // a cut value holding a lone surrogate refuses (invalid_unicode) — the
  // store never persists one.
  function storedText(value, limit) {
    var cut = text(value, limit);
    if (codePoints(cut) < 0) return { ok: false, reason: 'invalid_unicode' };
    return { ok: true, value: cut };
  }

  function exactKeys(value, keys) {
    if (!object(value)) return false;
    var present = Object.keys(value);
    if (present.length !== keys.length) return false;
    for (var index = 0; index < keys.length; index += 1) {
      if (!Object.prototype.hasOwnProperty.call(value, keys[index])) return false;
    }
    return true;
  }

  function hasNumber(value) {
    if (typeof value === 'number') return true;
    if (Array.isArray(value)) {
      for (var index = 0; index < value.length; index += 1) {
        if (hasNumber(value[index])) return true;
      }
      return false;
    }
    if (object(value)) {
      var keys = Object.keys(value);
      for (var keyIndex = 0; keyIndex < keys.length; keyIndex += 1) {
        if (hasNumber(value[keys[keyIndex]])) return true;
      }
    }
    return false;
  }

  // ── Request contract (mirrors engine/fundamental_forensics/query_service.py
  // admit_financial_request root/policy/period key sets and bounds) ─────────
  // Returns the canonicalised request object (fixed key order ⇒ stable bytes
  // under JSON.stringify) or null when the request is not admittable-shaped.
  function canonicalRequest(request) {
    if (!object(request)) return null;
    if (!exactKeys(request, ROOT_REQUEST_KEYS)) return null;
    if (request.schema !== REQUEST_CONTRACT) return null;
    var entityId = request.entity_id;
    if (typeof entityId !== 'string' || !entityId) return null;

    var policy = request.policy;
    if (!exactKeys(policy, POLICY_KEYS)) return null;
    if (SELECTIONS.indexOf(policy.selection) === -1) return null;
    if (typeof policy.source_snapshot_at !== 'string' || !policy.source_snapshot_at) return null;
    if (typeof policy.recorded_at !== 'string' || !policy.recorded_at) return null;

    var metricIds = request.metric_ids;
    if (!Array.isArray(metricIds) || !metricIds.length || metricIds.length > MAX_METRIC_IDS) return null;
    var seenMetrics = {};
    for (var metricIndex = 0; metricIndex < metricIds.length; metricIndex += 1) {
      if (typeof metricIds[metricIndex] !== 'string' || !metricIds[metricIndex]) return null;
      if (Object.prototype.hasOwnProperty.call(seenMetrics, metricIds[metricIndex])) return null;
      seenMetrics[metricIds[metricIndex]] = true;
    }

    var periods = request.periods;
    if (!Array.isArray(periods) || !periods.length || periods.length > MAX_PERIODS) return null;
    var canonicalPeriods = [];
    for (var periodIndex = 0; periodIndex < periods.length; periodIndex += 1) {
      var raw = periods[periodIndex];
      if (!exactKeys(raw, PERIOD_KEYS)) return null;
      if (raw.kind === 'duration') {
        if (typeof raw.start !== 'string' || !raw.start) return null;
      } else if (raw.kind === 'instant') {
        if (raw.start !== null) return null;
      } else {
        return null;
      }
      if (typeof raw.end !== 'string' || !raw.end) return null;
      if (typeof raw.label !== 'string' || !raw.label) return null;
      canonicalPeriods.push({ kind: raw.kind, start: raw.start, end: raw.end, label: raw.label });
    }
    if (metricIds.length * canonicalPeriods.length > MAX_CELLS) return null;
    // No numbers anywhere in a request (X0: no floats; nothing here is numeric).
    if (hasNumber(metricIds) || hasNumber(periods) || hasNumber(policy)) return null;

    return {
      schema: REQUEST_CONTRACT,
      entity_id: entityId,
      policy: {
        selection: policy.selection,
        source_snapshot_at: policy.source_snapshot_at,
        recorded_at: policy.recorded_at
      },
      metric_ids: metricIds.slice(),
      periods: canonicalPeriods
    };
  }

  // Key-order-insensitive structural equality: plain objects compare by key
  // set, arrays element-by-element in order, primitives by ===.
  function deepEqual(a, b) {
    if (a === b) return true;
    if (Array.isArray(a) || Array.isArray(b)) {
      if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return false;
      for (var index = 0; index < a.length; index += 1) {
        if (!deepEqual(a[index], b[index])) return false;
      }
      return true;
    }
    if (object(a) && object(b)) {
      var aKeys = Object.keys(a);
      if (aKeys.length !== Object.keys(b).length) return false;
      for (var keyIndex = 0; keyIndex < aKeys.length; keyIndex += 1) {
        if (!Object.prototype.hasOwnProperty.call(b, aKeys[keyIndex])) return false;
        if (!deepEqual(a[aKeys[keyIndex]], b[aKeys[keyIndex]])) return false;
      }
      return true;
    }
    return false;
  }

  // ── Saved-view shape ────────────────────────────────────────────────────
  // Refusal reasons (each has a test; REFUSAL_REASONS is the declared set the
  // schema suite pins exactly): 'schema', 'request_contract', 'request_schema',
  // 'request_root', 'request_canonical', 'pinned_type', 'peers', 'view',
  // 'pinned_cutoffs', 'id', 'unavailable', 'storage'. A view that fails any
  // check is listed as unavailable and may be deleted, never repaired.
  function checkView(raw) {
    if (!object(raw)) return { ok: false, reason: 'schema' };
    if (raw.schema !== SAVED_SCHEMA) return { ok: false, reason: 'schema' };
    if (!exactKeys(raw, VIEW_KEYS)) return { ok: false, reason: 'schema' };
    if (raw.request_contract !== REQUEST_CONTRACT) return { ok: false, reason: 'request_contract' };
    if (!object(raw.request)) return { ok: false, reason: 'request_schema' };
    if (raw.request.schema !== raw.request_contract) return { ok: false, reason: 'request_schema' };
    if (!exactKeys(raw.request, ROOT_REQUEST_KEYS)) return { ok: false, reason: 'request_root' };
    // A pinned view names its missing clock before the canonical check, so
    // the more specific reason wins (canonicalRequest also refuses an empty
    // clock, which would otherwise make this reason unreachable).
    if (raw.pinned === true) {
      var policy = object(raw.request.policy) ? raw.request.policy : {};
      if (!policy.source_snapshot_at || !policy.recorded_at) {
        return { ok: false, reason: 'pinned_cutoffs' };
      }
    }
    // The embedded request must be EXACTLY its own canonical form: a
    // well-shaped but drifted blob (extra policy key, period missing a label,
    // selection outside the enum) refuses as request_canonical — never loads,
    // never repairs.
    var canon = canonicalRequest(raw.request);
    if (!canon || !deepEqual(canon, raw.request)) {
      return { ok: false, reason: 'request_canonical' };
    }
    // pinned is stored as a real boolean — "true"/1/null all refuse.
    if (typeof raw.pinned !== 'boolean') return { ok: false, reason: 'pinned_type' };
    // peers/view must already BE their normalised form; the page never
    // silently defaults a stored value it cannot apply.
    if (!object(raw.peers) || !deepEqual(normalPeers(raw.peers), raw.peers)) {
      return { ok: false, reason: 'peers' };
    }
    if (!object(raw.view) || !deepEqual(normalViewMeta(raw.view), raw.view)) {
      return { ok: false, reason: 'view' };
    }
    return { ok: true, view: raw };
  }

  function normalEvidenceRefs(values) {
    var out = [];
    var entries = Array.isArray(values) ? values : [];
    for (var index = 0; index < entries.length; index += 1) {
      if (out.length >= MAX_EVIDENCE_REFS) break;
      var entry = entries[index];
      if (!object(entry)) continue;
      var span = Array.isArray(entry.source_span) && entry.source_span.length === 2 &&
        typeof entry.source_span[0] === 'number' && typeof entry.source_span[1] === 'number' &&
        Number.isFinite(entry.source_span[0]) && Number.isFinite(entry.source_span[1])
        ? [Math.trunc(entry.source_span[0]), Math.trunc(entry.source_span[1])] : null;
      if (!span) continue; // no invented spans (AM1): a ref without a real span is dropped
      // r2 MINOR-2b: evidence ids are identifiers — never cut, refused typed.
      var accession = idText(entry.accession, 64);
      if (!accession.ok) return accession;
      var occurrence = idText(entry.occurrence_id, 128);
      if (!occurrence.ok) return occurrence;
      out.push({
        accession: accession.value,
        occurrence_id: occurrence.value,
        source_span: span
      });
    }
    return { ok: true, value: out };
  }

  function normalPeers(value) {
    value = object(value) ? value : {};
    var peerN = Number.isFinite(value.peer_n) && value.peer_n >= 0 ? Math.trunc(value.peer_n) : 3;
    var peerTol = Number.isFinite(value.peer_tol) && value.peer_tol >= 0 ? Math.trunc(value.peer_tol) : 45;
    var cohort = storedText(value.cohort, 128);
    if (!cohort.ok) return cohort;
    var peerMetric = storedText(value.peer_metric, 128);
    if (!peerMetric.ok) return peerMetric;
    return {
      cohort: cohort.value || null,
      peer_metric: peerMetric.value || null,
      align: value.align === 'shift_labeled' ? 'shift_labeled' : 'exclude',
      peer_n: peerN,
      peer_tol: peerTol
    };
  }

  function normalSavedAgainst(value) {
    value = object(value) ? value : {};
    // X2-b+c r3 R3-2: generation_id is an identifier and is NEVER cut — an
    // over-limit or lone-surrogate id refuses typed and nothing is stored.
    var generationId = idText(value.generation_id, 128);
    if (!generationId.ok) return generationId;
    var admittedAt = storedText(value.admitted_at, 80);
    if (!admittedAt.ok) return admittedAt;
    return {
      ok: true,
      value: {
        generation_id: generationId.value || null,
        admitted_at: admittedAt.value || null,
        response_sha256: /^[a-f0-9]{64}$/.test(text(value.response_sha256, 80)) ? text(value.response_sha256, 80) : null
      }
    };
  }

  function normalIssuer(value) {
    value = object(value) ? value : {};
    // Display/index metadata only; the query identity is request.entity_id
    // and is never inferred from the ticker. The entity id IS the manifest
    // subject (intent.subjects[0].object_id): the emitter's own checker runs
    // here with its path (r3 R3-1) and the store's 160-code-point limit
    // (stricter than the emitter's 256, so a stored id always exports).
    // cik/ticker are identifiers the emitter never emits — never cut either
    // (r3 R3-2), refusing with idText's typed codes.
    var entityIdSource = typeof value.entity_id === 'string' ? value.entity_id.trim() : value.entity_id;
    var entityId = manifestTextRefusal(entityIdSource, '$.intent.subjects[0].object_id', 160);
    if (entityId) return entityId;
    var cik = idText(value.cik, 32);
    if (!cik.ok) return cik;
    var ticker = idText(value.ticker, 32);
    if (!ticker.ok) return ticker;
    return {
      ok: true,
      value: {
        entity_id: entityIdSource,
        cik: cik.value || null,
        ticker: ticker.value || null
      }
    };
  }

  function normalViewMeta(value) {
    value = object(value) ? value : {};
    var allowed = ['radar', 'statements', 'disclosures', 'redlines', 'timeline', 'compare', 'trace', 'peers'];
    var tab = allowed.indexOf(value.tab) >= 0 ? value.tab : 'radar';
    var finding = storedText(value.finding, 128);
    if (!finding.ok) return finding;
    return { tab: tab, finding: finding.value || null };
  }

  // ── Container (GovRev discipline: contract-checked; an unreadable store
  // goes READ-ONLY and never self-heals to blank) ──────────────────────────
  function blankContainer() {
    return { contract: SAVED_SCHEMA, saved_views: [] };
  }

  // A lawful read keeps EVERY row verbatim — no dropping, no truncation, no
  // normalisation; rows are judged lazily by listing()/load(). The read
  // happens at the start of every operation, so each one sees the bytes
  // another tab may have written since the last call. Only the
  // container's own shape decides readability: an absent key (or no storage
  // at all) is a blank writable container; ANYTHING else unreadable — a
  // throwing getItem, unparseable bytes, a non-object root, wrong root keys,
  // a drifted contract, saved_views not an array — makes the whole store
  // READ-ONLY so the user's stored bytes are never overwritten.
  function readStored(storage) {
    if (!storage || typeof storage.getItem !== 'function') {
      return { ok: true, container: blankContainer() };
    }
    var raw = null;
    try {
      raw = storage.getItem(STORAGE_KEY);
    } catch (error) {
      return { ok: false };
    }
    if (raw === null || raw === undefined) return { ok: true, container: blankContainer() };
    var parsed = null;
    try {
      parsed = JSON.parse(raw);
    } catch (error) {
      return { ok: false };
    }
    if (!object(parsed)) return { ok: false };
    if (!exactKeys(parsed, ['contract', 'saved_views'])) return { ok: false };
    if (parsed.contract !== SAVED_SCHEMA) return { ok: false };
    if (!Array.isArray(parsed.saved_views)) return { ok: false };
    return { ok: true, container: { contract: SAVED_SCHEMA, saved_views: parsed.saved_views } };
  }

  // ── Module factory ──────────────────────────────────────────────────────
  function createFifSavedBriefcase(api) {
    api = object(api) ? api : {};
    var storage = api.storage || null;
    if (!storage) {
      try { storage = root.localStorage; } catch (error) { storage = null; }
    }
    var cryptoSource = object(api.crypto) ? api.crypto : (root.crypto || null);
    // Injected-clock seam (tests pass api.now); GovRev precedent
    // government-revenue-briefcase.js:483-484.
    var now = typeof api.now === 'function' ? api.now : function () { return new Date().toISOString(); };

    function stamp() {
      var value = text(now(), 80);
      return value || new Date().toISOString();
    }

    function entropy(length) {
      var bytes = new Array(length);
      if (cryptoSource && typeof cryptoSource.getRandomValues === 'function') {
        var view = new Uint8Array(length);
        cryptoSource.getRandomValues(view);
        for (var index = 0; index < length; index += 1) bytes[index] = view[index];
      } else {
        for (var fallback = 0; fallback < length; fallback += 1) {
          bytes[fallback] = Math.floor(Math.random() * 256);
        }
      }
      return bytes;
    }

    function makeId() {
      var bytes = entropy(ID_LENGTH);
      var id = '';
      for (var index = 0; index < ID_LENGTH; index += 1) {
        id += ID_ALPHABET[bytes[index] % ID_ALPHABET.length];
      }
      return id;
    }

    var container = blankContainer();
    var readOnly = false;
    // Every operation starts from the CURRENT stored bytes (another tab may have written since the last call), so a
    // write always computes from a fresh read and can never drop, resurrect or overwrite another tab's change.
    function refresh() {
      var fresh = readStored(storage);
      container = fresh.ok ? fresh.container : blankContainer();
      readOnly = !fresh.ok;
    }
    refresh();

    function commit() {
      var persisted = false;
      if (storage && typeof storage.setItem === 'function') {
        try {
          storage.setItem(STORAGE_KEY, JSON.stringify(container));
          persisted = true;
        } catch (error) {}
      }
      return persisted;
    }

    function rowId(row) {
      return object(row) ? text(row.id, 64) : '';
    }

    // X2-b (r2 MINOR 1): a stable fingerprint for a row's bytes — FNV-1a
    // 32-bit over the UTF-16 code units of its JSON serialization — so an
    // address computed in one tab still names the SAME row after another
    // tab writes (an index alone can slide onto a neighbour).
    function rowFingerprint(row) {
      var serialized = JSON.stringify(row);
      if (serialized === undefined) serialized = 'undefined';
      var hash = 0x811c9dc5;
      for (var index = 0; index < serialized.length; index += 1) {
        hash = Math.imul(hash ^ serialized.charCodeAt(index), 0x01000193) >>> 0;
      }
      var hex = hash.toString(16);
      while (hex.length < 8) hex = '0' + hex;
      return hex;
    }

    // The 'row:' namespace is RESERVED for addresses: a stored id inside it
    // never names a row by id.
    function isAddressKey(id) {
      return /^row:/.test(text(id, 64));
    }

    // Every row gets an address: a row that is a plain object carrying a
    // lawful, first-seen id OUTSIDE the reserved 'row:' namespace is
    // addressed by that id; anything else (not a plain object, missing/
    // empty/non-string id, an id inside the reserved namespace, a repeated
    // id) is addressed as 'row:<index>:<fingerprint>' — listed unavailable,
    // refused on load, removable by exactly that key, never silently
    // dropped.
    function rowAddresses() {
      // X2-b+c r2 NIT-3: a null-prototype map, so an id of '__proto__' is an
      // ordinary duplicate key instead of a silent write to Object.prototype
      // (which made every later '__proto__' row look first-seen).
      var seen = Object.create(null);
      return container.saved_views.map(function (row, index) {
        var id = rowId(row);
        if (id && !isAddressKey(id) && !Object.prototype.hasOwnProperty.call(seen, id)) {
          seen[id] = true;
          return { key: id, index: index, row: row, idProblem: false };
        }
        return { key: 'row:' + index + ':' + rowFingerprint(row), index: index, row: row, idProblem: true };
      });
    }

    // X2-b+c r2 NIT-4: the index refuses leading zeros (row:01:<fp> never
    // names a row), and a 32-bit fingerprint match alone never names a row
    // either. Every fingerprint carrier is compared by its FULL canonical row
    // bytes: byte-identical carriers are interchangeable (any one is the row
    // the caller saw), but two DIFFERENT byte shapes sharing the 32-bit hash
    // leave the address ambiguous, so it resolves to nothing rather than the
    // wrong row.
    function pseudoRowAddress(id) {
      var match = /^row:(0|[1-9]\d*):([0-9a-f]{8})$/.exec(text(id, 64));
      if (!match) return null;
      var index = Number(match[1]);
      var fingerprint = match[2];
      var addresses = rowAddresses();
      var resolved = null;
      var canonical = null;
      for (var scan = 0; scan < addresses.length; scan += 1) {
        if (!addresses[scan].idProblem || rowFingerprint(addresses[scan].row) !== fingerprint) continue;
        var bytes = canonicalJson(addresses[scan].row);
        if (bytes === null) return null;
        if (canonical === null) {
          canonical = bytes;
          resolved = addresses[scan];
        } else if (canonical !== bytes) {
          return null; // ambiguous: two byte shapes share the 32-bit hash
        }
      }
      if (resolved === null) return null;
      // The index the caller saw names the row when it is one of the
      // carriers (no slide); otherwise the first carrier does.
      if (addresses[index] && addresses[index].idProblem &&
        rowFingerprint(addresses[index].row) === fingerprint) {
        return addresses[index];
      }
      return resolved;
    }

    function rowById(id) {
      var wanted = text(id, 64);
      if (!wanted) return null;
      for (var index = 0; index < container.saved_views.length; index += 1) {
        if (rowId(container.saved_views[index]) === wanted) return container.saved_views[index];
      }
      return null;
    }

    function listing() {
      refresh();
      if (readOnly) return [];
      return rowAddresses().map(function (address) {
        var safe = object(address.row) ? address.row : {};
        var checked = checkView(address.row);
        return {
          id: address.key,
          name: text(safe.name, MAX_NAME_LENGTH),
          pinned: safe.pinned === true,
          updated_at: text(safe.updated_at, 80),
          available: checked.ok && !address.idProblem,
          reason: address.idProblem ? 'id' : (checked.ok ? '' : checked.reason)
        };
      });
    }

    function load(id) {
      refresh();
      if (readOnly) return { ok: false, reason: 'unavailable' };
      if (isAddressKey(id)) return { ok: false, reason: pseudoRowAddress(id) ? 'id' : 'missing' };
      var row = rowById(id);
      if (!row) return { ok: false, reason: 'missing' };
      var checked = checkView(row);
      if (!checked.ok) return { ok: false, reason: checked.reason };
      return { ok: true, view: copy(row) };
    }

    function save(input) {
      refresh();
      if (readOnly) return { ok: false, reason: 'unavailable' };
      input = object(input) ? input : {};
      if (container.saved_views.length >= MAX_VIEWS) return { ok: false, reason: 'limit' };
      // r2 MINOR-2a: free text cuts at a whole-grapheme boundary (code-point
      // without a Segmenter), never minting a lone surrogate; a name that
      // already contains one refuses invalid_unicode and nothing is stored.
      var name = freeText(input.name, MAX_NAME_LENGTH);
      if (!name) return { ok: false, reason: 'name' };
      // X2-b+c r3 R3-1: the name IS the emitter's intent.title — the
      // emitter's own checker runs on the cut value with its path and its
      // limit (null there: the title cut owns length, and the cut above
      // already happened), so a name that would refuse at export refuses at
      // save with the same code and path, and nothing is stored.
      var nameRefusal = manifestTextRefusal(name, '$.intent.title', null);
      if (nameRefusal) return nameRefusal;
      var request = canonicalRequest(input.request);
      if (!request) return { ok: false, reason: 'request' };
      var issuer = normalIssuer(input.issuer);
      if (!issuer.ok) return issuer;
      var pinned = input.pinned === true;
      var evidenceRefs = normalEvidenceRefs(input.evidence_refs);
      if (!evidenceRefs.ok) return evidenceRefs;
      // X2-b+c r3 R3-1: the emitter's own projection decides what stores —
      // every evidence ref is re-run through manifestEvidenceRef (its
      // checker, its paths, its limits; the store's 64/128-code-point limits
      // above are stricter, so this adds the blank/NUL/control laws) and its
      // Terminal identity tuple is deduped exactly as the emitter dedups, so
      // a stored view always exports.
      var refsRefusal = evidenceExportRefusal(evidenceRefs.value, pinned);
      if (refsRefusal) return refsRefusal;
      if (pinned && (!request.policy.source_snapshot_at || !request.policy.recorded_at)) {
        return { ok: false, reason: 'pinned_cutoffs' };
      }
      // X2-b+c r3 R3-1: a pinned view's cutoff is the emitter's
      // intent.research_as_of — a snapshot that is not a real calendar date
      // would refuse invalid_date at export, so it refuses here first.
      if (pinned && calendarDate(request.policy.source_snapshot_at) === null) {
        return manifestRefusal('invalid_date', '$.intent.research_as_of');
      }
      var peers = normalPeers(input.peers);
      if (peers && peers.ok === false) return peers;
      var viewMeta = normalViewMeta(input.view);
      if (viewMeta && viewMeta.ok === false) return viewMeta;
      var savedAgainst = normalSavedAgainst(input.saved_against);
      if (!savedAgainst.ok) return savedAgainst;
      var stamped = stamp();
      var view = {
        schema: SAVED_SCHEMA,
        request_contract: REQUEST_CONTRACT,
        id: makeId(),
        name: name,
        created_at: stamped,
        updated_at: stamped,
        issuer: issuer.value,
        request: request,
        peers: peers,
        view: viewMeta,
        pinned: pinned,
        saved_against: savedAgainst.value,
        evidence_refs: evidenceRefs.value,
        watch: { issuer: input.watch && object(input.watch) ? input.watch.issuer === true : false }
      };
      container.saved_views.push(view);
      if (!commit()) {
        // Roll the in-memory change back: a failed persistence must not
        // leave a phantom row the next reload would not have.
        container.saved_views.pop();
        return { ok: false, reason: 'storage' };
      }
      return { ok: true, view: copy(view) };
    }

    function update(id, input) {
      refresh();
      if (readOnly) return { ok: false, reason: 'unavailable' };
      input = object(input) ? input : {};
      if (isAddressKey(id)) return { ok: false, reason: pseudoRowAddress(id) ? 'id' : 'missing' };
      var row = rowById(id);
      if (!row) return { ok: false, reason: 'missing' };
      // A refused row stays refused, and its stored bytes never change
      // through update(): check the CURRENT bytes first, and never re-stamp
      // the contract fields below — an editable row already carries them.
      var current = checkView(row);
      if (!current.ok) return { ok: false, reason: current.reason };
      var next = copy(row);
      if (Object.prototype.hasOwnProperty.call(input, 'name')) {
        // r2 MINOR-2a: the rename cut is grapheme-safe; a name holding a
        // lone surrogate refuses invalid_unicode and the row is unchanged.
        var name = freeText(input.name, MAX_NAME_LENGTH);
        if (!name) return { ok: false, reason: 'name' };
        // X2-b+c r3 R3-1: the rename is the emitter's intent.title too — the
        // emitter's checker runs on the cut value with its code and path.
        var nameRefusal = manifestTextRefusal(name, '$.intent.title', null);
        if (nameRefusal) return nameRefusal;
        next.name = name;
      }
      var pinned = Object.prototype.hasOwnProperty.call(input, 'pinned')
        ? input.pinned === true : next.pinned === true;
      if (Object.prototype.hasOwnProperty.call(input, 'request')) {
        var request = canonicalRequest(input.request);
        if (!request) return { ok: false, reason: 'request' };
        next.request = request;
      }
      var nextPolicy = object(next.request) && object(next.request.policy) ? next.request.policy : null;
      if (pinned && (!nextPolicy || !nextPolicy.source_snapshot_at || !nextPolicy.recorded_at)) {
        return { ok: false, reason: 'pinned_cutoffs' };
      }
      // X2-b+c r3 R3-1: the pinned-cutoff gate on update — a snapshot that
      // is not a real calendar date would refuse invalid_date at export.
      if (pinned && calendarDate(nextPolicy.source_snapshot_at) === null) {
        return manifestRefusal('invalid_date', '$.intent.research_as_of');
      }
      next.pinned = pinned;
      // X2-b+c r3 R3-1 (repair): the stored refs re-run the emitter's
      // projection and dedup under the pin state the row will carry —
      // unconditionally, because an unpin can collapse two refs to one
      // identity and a pin can surface an accession the latest projection
      // never checked. Refused typed; the row is unchanged.
      var refsRefusal = evidenceExportRefusal(next.evidence_refs, pinned);
      if (refsRefusal) return refsRefusal;
      if (Object.prototype.hasOwnProperty.call(input, 'saved_against')) {
        // X2-b+c r3 R3-2: generation_id is never cut here either — an
        // over-limit or lone-surrogate id refuses typed, row unchanged.
        var savedAgainst = normalSavedAgainst(input.saved_against);
        if (!savedAgainst.ok) return savedAgainst;
        next.saved_against = savedAgainst.value;
      }
      var checked = checkView(next);
      if (!checked.ok) return { ok: false, reason: checked.reason };
      next.updated_at = stamp();
      var replaced = copy(next);
      var index = container.saved_views.indexOf(row);
      if (index === -1) return { ok: false, reason: 'missing' };
      container.saved_views[index] = replaced;
      if (!commit()) {
        // Restore the previous row at its index: no half-updated bytes.
        container.saved_views[index] = row;
        return { ok: false, reason: 'storage' };
      }
      return { ok: true, view: copy(replaced) };
    }

    function remove(id) {
      refresh();
      if (readOnly) return { ok: false, reason: 'unavailable' };
      var wanted = text(id, 64);
      var index = -1;
      if (isAddressKey(wanted)) {
        // An address that no longer names a row deletes nothing — it never
        // falls through to the real-id scan below.
        var address = pseudoRowAddress(wanted);
        if (!address) return { ok: true, deleted: false };
        index = address.index;
      } else if (wanted) {
        // A real id acts on the FIRST row carrying it; later duplicates are
        // reachable only through their 'row:<index>:<fingerprint>' address.
        for (var scan = 0; scan < container.saved_views.length; scan += 1) {
          if (rowId(container.saved_views[scan]) === wanted) { index = scan; break; }
        }
      }
      if (index === -1) return { ok: true, deleted: false };
      var previous = container.saved_views.slice();
      container.saved_views.splice(index, 1);
      if (!commit()) {
        container.saved_views = previous;
        return { ok: false, reason: 'storage' };
      }
      return { ok: true, deleted: true };
    }

    return {
      list: listing,
      load: load,
      save: save,
      update: update,
      remove: remove,
      readOnly: function () { refresh(); return readOnly; }
    };
  }

  // ── A→B mapping (R1: lossless; X2-b is the consumer, nothing here is
  // wired to a caller or a network today). Target field names come from the
  // Terminal investigations manifest v2 contract at the pinned census commit
  // c799ba7e (api/investigation_contracts.py): subjects kind/owner/object_id
  // :94-100 with 'issuer' in KINDS :19; evidence owner/object_type/object_id/
  // mode :119-122 with mode pinned|follow_head :124 (pinned requires
  // version_ref :125; follow_head carries neither version_ref nor fingerprint
  // :130); intent.research_as_of is a real calendar YYYY-MM-DD date :152-158.
  // At that commit Terminal refuses this manifest whole: the carrier key is an
  // unknown_field (:34 via :89) and owner 'fif' / object_type 'occurrence'
  // are not admitted. research/financial_intelligence_fabric/
  // FIF_X2B_TERMINAL_INVESTIGATIONS_CENSUS.md (GATE TEXT) names the
  // Terminal-side change; macro never edits Terminal (R2). ──────────────────
  // Order-insensitive canonical serialization (Postgres jsonb reorders object
  // keys, so key order must never decide equality): arrays keep their order,
  // object keys sort, primitives render as plain JSON.
  // X2-b+c r2 NIT-1: canonicalJson compares bytes, so a value JSON cannot
  // round-trip must refuse BEFORE the comparison — a non-plain prototype
  // (Date, Map, Set, a class instance), a non-finite number, -0, a sparse
  // array, a getter/setter or a symbol/private key all serialize to
  // something else under JSON and would silently compare as that something
  // (a Date has no enumerable keys and rendered as '{}'). Terminal's own
  // dataOnly law refuses the same class of values
  // (investigationContracts.ts:89-131).
  function plainJsonValue(value) {
    if (value === null) return true;
    var type = typeof value;
    if (type === 'string' || type === 'boolean') return true;
    if (type === 'number') {
      return Number.isFinite(value) && (value !== 0 || 1 / value > 0);
    }
    if (type !== 'object') return false;
    var prototype = Object.getPrototypeOf(value);
    if (Array.isArray(value)) {
      // Realm-tolerant on purpose (the vm test realms hand the module objects
      // from other realms): Array.isArray is realm-blind, and the plain-array
      // law that matters here is the own-index law — a sparse array or one
      // carrying extra keys is refused.
      if (Object.keys(value).length !== value.length) return false; // sparse or keyed
      for (var element = 0; element < value.length; element += 1) {
        if (!plainJsonValue(value[element])) return false;
      }
      return true;
    }
    // A plain object's prototype is a realm's standard Object.prototype.
    // The vm test realms give objects a FOREIGN prototype object, so compare
    // by shape — a standard Object.prototype sits at the root of its chain —
    // while Date/Map/Set/class prototypes all sit below one and are refused.
    if (prototype !== null && Object.getPrototypeOf(prototype) !== null) return false;
    var keys = Object.keys(value);
    if (Reflect.ownKeys(value).length !== keys.length) return false;
    for (var keyIndex = 0; keyIndex < keys.length; keyIndex += 1) {
      var descriptor = Object.getOwnPropertyDescriptor(value, keys[keyIndex]);
      if (!descriptor || descriptor.enumerable !== true ||
        !Object.prototype.hasOwnProperty.call(descriptor, 'value')) return false;
      if (!plainJsonValue(value[keys[keyIndex]])) return false;
    }
    return true;
  }

  function canonicalJson(value) {
    if (!plainJsonValue(value)) return null;
    if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
    if (object(value)) {
      return '{' + Object.keys(value).sort().map(function (key) {
        return JSON.stringify(key) + ':' + canonicalJson(value[key]);
      }).join(',') + '}';
    }
    return value === undefined ? 'null' : JSON.stringify(value);
  }

  // ── X2-c emitter law (seat ruling R-X2B-G2). Every emitted text field is
  // measured in CODE POINTS (Unicode scalars), never UTF-16 units, exactly as
  // Terminal measures it at c799ba7e: py api/investigation_contracts.py:42-46,
  // ts terminal/lib/investigationContracts.ts:146-151, sql
  // 0028_investigations.sql:69. Nothing is trimmed, dropped or deduped on the
  // user's behalf: a value the contract would refuse is refused HERE, typed,
  // with the JSON path of the offending manifest field. The one projection
  // that shortens a value is the title cut (a title over 160 code points keeps
  // its longest whole-grapheme prefix and the cut is reported as a notice);
  // the carrier always keeps the full saved view. ──────────────────────────
  var MANIFEST_TITLE_LIMIT = 160;
  var MANIFEST_ID_LIMIT = 256;
  // X2-b+c r2 MINOR-3: the added codes are Terminal's own —
  // unsupported_code_point (NUL, investigation_contracts.py:45 /
  // investigationContracts.ts:150), too_many_items (py :139 via :161) and
  // manifest_too_large (py :169 / 0028_investigations.sql:93).
  var MANIFEST_REFUSAL_REASONS = Object.freeze([
    'invalid_type', 'empty_text', 'invalid_control', 'invalid_unicode',
    'unsupported_code_point', 'text_too_long', 'invalid_date',
    'duplicate_reference', 'too_many_items', 'manifest_too_large'
  ]);
  // Blank = made only of characters in the UNION of the three trim sets: py
  // TRIM (investigation_contracts.py:14), ECMAScript String.prototype.trim,
  // and the sql btrim list (0028_investigations.sql:70).
  var MANIFEST_BLANK = /^[\t\n\u000b\u000c\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]*$/;
  // Every emitted text field is single-line. The control scan mirrors
  // Terminal exactly (ts CONTROL investigationContracts.ts:77; py :47-48):
  // C0 without tab/LF/CR plus DEL refuse as invalid_control AFTER the
  // per-character pass, and tab/LF/CR refuse there too because every emitter
  // field is single-line (py text(..., single=True)). NUL is NOT here — the
  // per-character pass reports it as unsupported_code_point first.
  var MANIFEST_CONTROL = /[\u0001-\u0008\u000b\u000c\u000e-\u001f\u007f]/;
  var MANIFEST_SINGLE_LINE = /[\t\n\r]/;
  var MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

  function manifestRefusal(reason, path) {
    return { ok: false, reason: reason, path: path };
  }

  // Code points in a string, or -1 when it holds a lone or split surrogate.
  function codePoints(value) {
    var count = 0;
    for (var index = 0; index < value.length; index += 1) {
      var unit = value.charCodeAt(index);
      if (unit >= 0xd800 && unit <= 0xdbff) {
        var next = value.charCodeAt(index + 1);
        if (!(next >= 0xdc00 && next <= 0xdfff)) return -1;
        index += 1;
      } else if (unit >= 0xdc00 && unit <= 0xdfff) {
        return -1;
      }
      count += 1;
    }
    return count;
  }

  // The typed refusal for one text field, or null when the value may be
  // emitted verbatim. Mirrors Terminal's per-character loop exactly
  // (investigation_contracts.py:42-48, investigationContracts.ts:143-157):
  // each character, in order, is checked for a lone surrogate
  // (invalid_unicode), NUL (unsupported_code_point — never invalid_control)
  // and the running length (text_too_long); the control scan runs only after
  // the whole string passed, so an over-limit id reports text_too_long even
  // when its tail holds a lone surrogate or a tab. A null limit leaves the
  // over-length decision to the caller (the title cut).
  function manifestTextRefusal(value, path, limit) {
    if (typeof value !== 'string') return manifestRefusal('invalid_type', path);
    if (MANIFEST_BLANK.test(value)) return manifestRefusal('empty_text', path);
    var count = 0;
    for (var index = 0; index < value.length; ) {
      var unit = value.charCodeAt(index);
      var size = 1;
      if (unit >= 0xd800 && unit <= 0xdbff) {
        var next = value.charCodeAt(index + 1);
        if (next >= 0xdc00 && next <= 0xdfff) size = 2;
        else return manifestRefusal('invalid_unicode', path);
      } else if (unit >= 0xdc00 && unit <= 0xdfff) {
        return manifestRefusal('invalid_unicode', path);
      } else if (unit === 0) {
        return manifestRefusal('unsupported_code_point', path);
      }
      count += 1;
      if (limit !== null && count > limit) return manifestRefusal('text_too_long', path);
      index += size;
    }
    if (MANIFEST_CONTROL.test(value) || MANIFEST_SINGLE_LINE.test(value)) {
      return manifestRefusal('invalid_control', path);
    }
    return null;
  }

  // The longest prefix made of WHOLE grapheme clusters that fits in `limit`
  // code points (a surrogate pair or a ZWJ/emoji sequence is never split), or
  // null when no non-blank such prefix exists or the runtime has no
  // Intl.Segmenter (then the caller refuses rather than guess a boundary).
  function wholeGraphemePrefix(value, limit) {
    if (typeof Intl === 'undefined' || typeof Intl.Segmenter !== 'function') return null;
    var iterator = new Intl.Segmenter('en', { granularity: 'grapheme' }).segment(value)[Symbol.iterator]();
    var prefix = '';
    var count = 0;
    for (var step = iterator.next(); !step.done; step = iterator.next()) {
      var size = codePoints(step.value.segment);
      if (count + size > limit) break;
      prefix += step.value.segment;
      count += size;
    }
    return prefix && !MANIFEST_BLANK.test(prefix) ? prefix : null;
  }

  // intent.title: the saved name verbatim when it fits in 160 code points;
  // otherwise its longest whole-grapheme prefix plus a title_cut notice;
  // text_too_long when no whole-grapheme cut exists.
  function manifestTitle(value, notices) {
    var path = '$.intent.title';
    var refused = manifestTextRefusal(value, path, null);
    if (refused) return refused;
    var count = codePoints(value);
    if (count <= MANIFEST_TITLE_LIMIT) return { ok: true, value: value };
    var cut = wholeGraphemePrefix(value, MANIFEST_TITLE_LIMIT);
    if (cut === null) return manifestRefusal('text_too_long', path);
    notices.push({ code: 'title_cut', path: path, code_points: count, kept_code_points: codePoints(cut) });
    return { ok: true, value: cut };
  }

  // intent.research_as_of: the first ten characters of the pinned cutoff,
  // only when they are a REAL calendar date (YYYY-MM-DD, year >= 1, leap
  // years honoured: no Feb 30, no Feb 29 outside a leap year) followed by the
  // end of the string or a date-time separator. Nothing is trimmed first.
  function calendarDate(value) {
    if (typeof value !== 'string') return null;
    var match = /^(\d{4})-(\d{2})-(\d{2})(?:$|[Tt ])/.exec(value);
    if (!match) return null;
    var year = Number(match[1]);
    var month = Number(match[2]);
    var day = Number(match[3]);
    if (year < 1 || month < 1 || month > 12 || day < 1) return null;
    var leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    var last = month === 2 && leap ? 29 : MONTH_DAYS[month - 1];
    return day > last ? null : match[1] + '-' + match[2] + '-' + match[3];
  }

  // One evidence ref, never dropped: object_id is occurrence_id, or the
  // accession when occurrence_id is absent/null/''; pinned refs add
  // version_ref = accession, or object_id when accession is absent/null/''.
  function manifestEvidenceRef(ref, path, pinned) {
    if (!object(ref)) return manifestRefusal('invalid_type', path);
    var occurrence = ref.occurrence_id == null ? '' : ref.occurrence_id;
    var accession = ref.accession == null ? '' : ref.accession;
    var objectId = occurrence !== '' ? occurrence : accession;
    var refused = manifestTextRefusal(objectId, path + '.object_id', MANIFEST_ID_LIMIT);
    if (refused) return refused;
    var entry = {
      owner: MANIFEST_OWNER,
      object_type: 'occurrence',
      object_id: objectId,
      mode: pinned ? 'pinned' : 'follow_head'
    };
    if (pinned) {
      var versionRef = accession !== '' ? accession : objectId;
      refused = manifestTextRefusal(versionRef, path + '.version_ref', MANIFEST_ID_LIMIT);
      if (refused) return refused;
      entry.version_ref = versionRef;
    }
    return { ok: true, value: entry };
  }

  // Terminal's evidence identity tuple (ts evidence() key: owner, object_type,
  // object_id, mode, version_ref, selection.field). This emitter never sets a
  // selection, so its field is always null.
  function evidenceIdentity(entry) {
    return JSON.stringify([
      entry.owner, entry.object_type, entry.object_id, entry.mode,
      entry.version_ref === undefined ? null : entry.version_ref, null
    ]);
  }

  // X2-b+c r3 R3-1 (repair): the store's export gate for evidence refs — the
  // emitter's own projection (its checker, paths and limits) and its Terminal
  // identity dedup, run under the pin state the row will carry. save() and
  // update() both call it, so a pin flip that would make stored refs refuse
  // at export (an unpin collapsing two refs to one identity, or a pin
  // surfacing an accession as version_ref) refuses at the write instead, and
  // nothing is stored. Returns the refusal, or null when every ref exports.
  function evidenceExportRefusal(refs, pinned) {
    if (refs == null) return null;
    if (!Array.isArray(refs)) return manifestRefusal('invalid_type', '$.evidence_refs');
    var seen = {};
    for (var index = 0; index < refs.length; index += 1) {
      var path = '$.evidence_refs[' + index + ']';
      var projection = manifestEvidenceRef(refs[index], path, pinned);
      if (!projection.ok) return projection;
      var identity = evidenceIdentity(projection.value);
      if (Object.prototype.hasOwnProperty.call(seen, identity)) return manifestRefusal('duplicate_reference', path);
      seen[identity] = true;
    }
    return null;
  }

  // A->B with typed refusals: {ok: true, manifest, notices} or
  // {ok: false, reason, path}. reason is a REFUSAL_REASONS member when the
  // saved view itself fails checkView, else a MANIFEST_REFUSAL_REASONS member.
  function emitInvestigationManifestV2(saved) {
    var checked = checkView(saved);
    if (!checked.ok) return manifestRefusal(checked.reason, '$.' + CARRIER_KEY);
    var notices = [];
    var title = manifestTitle(saved.name, notices);
    if (!title.ok) return title;
    if (!object(saved.issuer)) return manifestRefusal('invalid_type', '$.intent.subjects[0]');
    var subjectRefused = manifestTextRefusal(saved.issuer.entity_id, '$.intent.subjects[0].object_id', MANIFEST_ID_LIMIT);
    if (subjectRefused) return subjectRefused;
    var pinned = saved.pinned === true;
    var asOf = null;
    if (pinned) {
      var policy = object(saved.request) && object(saved.request.policy) ? saved.request.policy : {};
      asOf = calendarDate(policy.source_snapshot_at);
      if (asOf === null) return manifestRefusal('invalid_date', '$.intent.research_as_of');
    }
    var refs = saved.evidence_refs == null ? [] : saved.evidence_refs;
    if (!Array.isArray(refs)) return manifestRefusal('invalid_type', '$.evidence_refs');
    // Terminal checks the list length before any item (refs(),
    // investigation_contracts.py:139, called with the evidence maximum of
    // 128 at :161): an over-cap list is too_many_items at the list path. The
    // combined cap of :162 (0028_investigations.sql:120) rides the same
    // guard on this emitter's shape — it mints exactly zero layout and zero
    // thesis refs (sql :131 / terminal/lib/investigations.ts:52), so
    // layout + thesis + evidence IS the evidence count, and the mapping
    // suite's T-M7 pins the emitted total against the snapshot rule.
    if (refs.length > 128) return manifestRefusal('too_many_items', '$.evidence_refs');
    var evidenceRefs = [];
    var seen = {};
    for (var index = 0; index < refs.length; index += 1) {
      var path = '$.evidence_refs[' + index + ']';
      var mapped = manifestEvidenceRef(refs[index], path, pinned);
      if (!mapped.ok) return mapped;
      var identity = evidenceIdentity(mapped.value);
      if (Object.prototype.hasOwnProperty.call(seen, identity)) return manifestRefusal('duplicate_reference', path);
      seen[identity] = true;
      evidenceRefs.push(mapped.value);
    }
    var manifest = {
      schema: MANIFEST_V2_SCHEMA,
      intent: {
        title: title.value,
        question: 'Filing forensics saved view',
        subjects: [
          { kind: 'issuer', owner: MANIFEST_OWNER, object_id: saved.issuer.entity_id }
        ]
      },
      layout_refs: [],
      thesis_refs: [],
      evidence_refs: evidenceRefs,
      continuation: {}
    };
    if (asOf !== null) manifest.intent.research_as_of = asOf;
    // The carrier holds the complete saved object verbatim, so the round trip
    // is lossless by construction (a cut title included); the mapped fields
    // above are Terminal's native projection.
    manifest[CARRIER_KEY] = copy(saved);
    // The v2 size cap (investigation_contracts.py:169,
    // 0028_investigations.sql:93): the manifest's compact canonical JSON,
    // measured in UTF-8 octets, may not exceed 131072 — the same total py's
    // json.dumps, ts's TextEncoder (investigationContracts.ts:278-282) and
    // the sql octet_length compute, because key order never changes a byte
    // count.
    if (utf8Length(canonicalJson(manifest)) > 131072) {
      return manifestRefusal('manifest_too_large', '$');
    }
    return { ok: true, manifest: manifest, notices: notices };
  }

  // UTF-8 octet length of a canonical string (the r2 size-cap measure): a
  // BMP character is 1-3 octets, a surrogate pair 4, a lone surrogate 3 (the
  // replacement TextEncoder emits — investigationContracts.ts:281).
  function utf8Length(value) {
    var bytes = 0;
    for (var index = 0; index < value.length; index += 1) {
      var unit = value.charCodeAt(index);
      if (unit < 0x80) bytes += 1;
      else if (unit < 0x800) bytes += 2;
      else if (unit >= 0xd800 && unit <= 0xdbff) { bytes += 4; index += 1; }
      else bytes += 3;
    }
    return bytes;
  }

  // The X2-b surface, kept: the manifest, or null on any refusal (callers
  // that need the typed reason or the notices use emitInvestigationManifestV2).
  function toInvestigationManifestV2(saved) {
    var emitted = emitInvestigationManifestV2(saved);
    return emitted.ok ? emitted.manifest : null;
  }

  function fromInvestigationManifestV2(manifest) {
    if (!object(manifest) || manifest.schema !== MANIFEST_V2_SCHEMA) return null;
    var carried = manifest[CARRIER_KEY];
    var checked = object(carried) ? checkView(carried) : { ok: false };
    if (!checked.ok) return null;
    // R1 1:1 law: B maps back only when it is exactly the projection of its
    // own carrier. A manifest whose projected fields were changed after
    // export is a contract mismatch: refused, never repaired.
    var again = emitInvestigationManifestV2(carried);
    if (!again.ok) return null;
    var mine = canonicalJson(again.manifest);
    var theirs = canonicalJson(manifest);
    if (mine === null || theirs === null || mine !== theirs) return null;
    return copy(carried);
  }

  root.FifSavedBriefcase = {
    SAVED_SCHEMA: SAVED_SCHEMA,
    REQUEST_CONTRACT: REQUEST_CONTRACT,
    STORAGE_KEY: STORAGE_KEY,
    CARRIER_KEY: CARRIER_KEY,
    REFUSAL_REASONS: REFUSAL_REASONS,
    MANIFEST_REFUSAL_REASONS: MANIFEST_REFUSAL_REASONS,
    // X2-b+c r3 R3-4: the store's own notion of equality — key-order-blind
    // canonical bytes — exported for the page's reconcile compare. The
    // function itself is unchanged.
    canonicalJson: canonicalJson,
    create: createFifSavedBriefcase,
    emitInvestigationManifestV2: emitInvestigationManifestV2,
    toInvestigationManifestV2: toInvestigationManifestV2,
    fromInvestigationManifestV2: fromInvestigationManifestV2
  };
}(typeof window !== 'undefined' ? window : this));
