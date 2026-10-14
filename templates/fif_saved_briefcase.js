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

  function text(value, limit) {
    if (typeof value !== 'string') return '';
    return value.trim().slice(0, limit == null ? 1000 : limit);
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
    array(values).forEach(function (entry) {
      if (out.length >= MAX_EVIDENCE_REFS) return;
      if (!object(entry)) return;
      var span = Array.isArray(entry.source_span) && entry.source_span.length === 2 &&
        typeof entry.source_span[0] === 'number' && typeof entry.source_span[1] === 'number' &&
        Number.isFinite(entry.source_span[0]) && Number.isFinite(entry.source_span[1])
        ? [Math.trunc(entry.source_span[0]), Math.trunc(entry.source_span[1])] : null;
      if (!span) return; // no invented spans (AM1): a ref without a real span is dropped
      out.push({
        accession: text(entry.accession, 64),
        occurrence_id: text(entry.occurrence_id, 128),
        source_span: span
      });
    });
    return out;
  }

  function normalPeers(value) {
    value = object(value) ? value : {};
    var peerN = Number.isFinite(value.peer_n) && value.peer_n >= 0 ? Math.trunc(value.peer_n) : 3;
    var peerTol = Number.isFinite(value.peer_tol) && value.peer_tol >= 0 ? Math.trunc(value.peer_tol) : 45;
    return {
      cohort: text(value.cohort, 128) || null,
      peer_metric: text(value.peer_metric, 128) || null,
      align: value.align === 'shift_labeled' ? 'shift_labeled' : 'exclude',
      peer_n: peerN,
      peer_tol: peerTol
    };
  }

  function normalSavedAgainst(value) {
    value = object(value) ? value : {};
    return {
      generation_id: text(value.generation_id, 128) || null,
      admitted_at: text(value.admitted_at, 80) || null,
      response_sha256: /^[a-f0-9]{64}$/.test(text(value.response_sha256, 80)) ? text(value.response_sha256, 80) : null
    };
  }

  function normalIssuer(value) {
    value = object(value) ? value : {};
    // Display/index metadata only; the query identity is request.entity_id
    // and is never inferred from the ticker.
    return {
      entity_id: text(value.entity_id, 160) || null,
      cik: text(value.cik, 32) || null,
      ticker: text(value.ticker, 32) || null
    };
  }

  function normalViewMeta(value) {
    value = object(value) ? value : {};
    var allowed = ['radar', 'statements', 'disclosures', 'redlines', 'timeline', 'compare', 'trace', 'peers'];
    var tab = allowed.indexOf(value.tab) >= 0 ? value.tab : 'radar';
    return { tab: tab, finding: text(value.finding, 128) || null };
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

    // Every row gets an address: a row that is a plain object carrying a
    // lawful, first-seen id is addressed by that id; anything else (not a
    // plain object, missing/empty/non-string id, repeated id) is addressed
    // as 'row:<index>' — listed unavailable, refused on load, removable by
    // exactly that key, never silently dropped.
    function rowAddresses() {
      var seen = {};
      return container.saved_views.map(function (row, index) {
        var id = rowId(row);
        if (id && !Object.prototype.hasOwnProperty.call(seen, id)) {
          seen[id] = true;
          return { key: id, index: index, row: row, idProblem: false };
        }
        return { key: 'row:' + index, index: index, row: row, idProblem: true };
      });
    }

    function pseudoRowAddress(id) {
      var match = /^row:(\d+)$/.exec(text(id, 64));
      if (!match) return null;
      var index = Number(match[1]);
      var addresses = rowAddresses();
      if (index < 0 || index >= addresses.length || !addresses[index].idProblem) return null;
      return addresses[index];
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
      if (pseudoRowAddress(id)) return { ok: false, reason: 'id' };
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
      var name = text(input.name, MAX_NAME_LENGTH);
      if (!name) return { ok: false, reason: 'name' };
      var request = canonicalRequest(input.request);
      if (!request) return { ok: false, reason: 'request' };
      var pinned = input.pinned === true;
      if (pinned && (!request.policy.source_snapshot_at || !request.policy.recorded_at)) {
        return { ok: false, reason: 'pinned_cutoffs' };
      }
      var stamped = stamp();
      var view = {
        schema: SAVED_SCHEMA,
        request_contract: REQUEST_CONTRACT,
        id: makeId(),
        name: name,
        created_at: stamped,
        updated_at: stamped,
        issuer: normalIssuer(input.issuer),
        request: request,
        peers: normalPeers(input.peers),
        view: normalViewMeta(input.view),
        pinned: pinned,
        saved_against: normalSavedAgainst(input.saved_against),
        evidence_refs: normalEvidenceRefs(input.evidence_refs),
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
      if (pseudoRowAddress(id)) return { ok: false, reason: 'id' };
      var row = rowById(id);
      if (!row) return { ok: false, reason: 'missing' };
      // A refused row stays refused, and its stored bytes never change
      // through update(): check the CURRENT bytes first, and never re-stamp
      // the contract fields below — an editable row already carries them.
      var current = checkView(row);
      if (!current.ok) return { ok: false, reason: current.reason };
      var next = copy(row);
      if (Object.prototype.hasOwnProperty.call(input, 'name')) {
        var name = text(input.name, MAX_NAME_LENGTH);
        if (!name) return { ok: false, reason: 'name' };
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
      next.pinned = pinned;
      if (Object.prototype.hasOwnProperty.call(input, 'saved_against')) {
        next.saved_against = normalSavedAgainst(input.saved_against);
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
      var address = pseudoRowAddress(wanted);
      var index = -1;
      if (address) {
        index = address.index;
      } else if (wanted) {
        // A real id acts on the FIRST row carrying it; later duplicates are
        // reachable only through their 'row:<index>' address.
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
  // (api/investigation_contracts.py): subjects kind/owner/object_id :94-100
  // with 'issuer' in KINDS :19; evidence owner/object_type/object_id/mode
  // :118-123 with mode pinned|follow_head :124 (pinned requires version_ref
  // :125; follow_head carries neither version_ref nor fingerprint :130);
  // intent.research_as_of is a plain YYYY-MM-DD date :146-158. ──────────
  function manifestEvidenceRef(ref, pinned) {
    var objectId = text(ref.occurrence_id, 256) || text(ref.accession, 256);
    if (!objectId) return null;
    var entry = {
      owner: MANIFEST_OWNER,
      object_type: 'occurrence',
      object_id: objectId,
      mode: pinned ? 'pinned' : 'follow_head'
    };
    if (pinned) entry.version_ref = text(ref.accession, 256) || objectId;
    return entry;
  }

  function toInvestigationManifestV2(saved) {
    var checked = checkView(saved);
    if (!checked.ok || !object(saved.issuer) || !text(saved.issuer.entity_id, 160)) return null;
    var pinned = saved.pinned === true;
    var evidenceRefs = [];
    array(saved.evidence_refs).forEach(function (ref) {
      if (!object(ref)) return;
      var mapped = manifestEvidenceRef(ref, pinned);
      if (mapped) evidenceRefs.push(mapped);
    });
    var manifest = {
      schema: MANIFEST_V2_SCHEMA,
      intent: {
        title: text(saved.name, 160),
        question: 'Filing forensics saved view',
        subjects: [
          { kind: 'issuer', owner: MANIFEST_OWNER, object_id: text(saved.issuer.entity_id, 256) }
        ]
      },
      layout_refs: [],
      thesis_refs: [],
      evidence_refs: evidenceRefs,
      continuation: {}
    };
    if (pinned) {
      var asOf = text(saved.request && saved.request.policy && saved.request.policy.source_snapshot_at, 10);
      if (/^\d{4}-\d{2}-\d{2}$/.test(asOf)) manifest.intent.research_as_of = asOf;
    }
    // The carrier holds the complete saved object verbatim, so the round trip
    // is lossless by construction; the mapped fields above are Terminal's
    // native projection.
    manifest[CARRIER_KEY] = copy(saved);
    return manifest;
  }

  function fromInvestigationManifestV2(manifest) {
    if (!object(manifest) || manifest.schema !== MANIFEST_V2_SCHEMA) return null;
    var carried = manifest[CARRIER_KEY];
    var checked = object(carried) ? checkView(carried) : { ok: false };
    if (!checked.ok) return null;
    return copy(carried);
  }

  root.FifSavedBriefcase = {
    SAVED_SCHEMA: SAVED_SCHEMA,
    REQUEST_CONTRACT: REQUEST_CONTRACT,
    STORAGE_KEY: STORAGE_KEY,
    CARRIER_KEY: CARRIER_KEY,
    REFUSAL_REASONS: REFUSAL_REASONS,
    create: createFifSavedBriefcase,
    toInvestigationManifestV2: toInvestigationManifestV2,
    fromInvestigationManifestV2: fromInvestigationManifestV2
  };
}(typeof window !== 'undefined' ? window : this));
