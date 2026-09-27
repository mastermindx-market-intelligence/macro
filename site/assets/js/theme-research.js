/*!
 * theme-research.js — generic paid theme-research client (Theme Tracker page).
 *
 * Operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001, T10 part 1.
 * Theme-agnostic by construction: the anchor theme, the slices and both
 * endpoints come from the mount's data-* attributes; nothing in this file is
 * semiconductor-specific. No backend ships with this file — the client speaks
 * the frozen semiconductor_theme_research.v1 envelope and renders section
 * statuses, never invented zeros.
 *
 * Account safety (proven by execution under node — see
 * tests/test_semiconductor_theme_research_ui.py):
 *   - the session token comes ONLY from MDXAuth.client() (the same session
 *     acquisition the biocatalyst dossier uses); auth changes arrive via
 *     MDXAuth.onChange. No second SDK, no cookies, no token storage.
 *   - every in-flight request carries (epoch, principalKey); a response that
 *     no longer matches the current epoch/principal is dropped without
 *     touching state or DOM, and every network path re-checks in .finally.
 *   - the ONLY browser storage is the remembered slice/view/time-mode
 *     selection under 'theme_research_sel' — never a token, never payload
 *     data, never anything user-derived.
 *   - every server-derived string passes through textSafe + textContent;
 *     there is no innerHTML assignment anywhere in this file.
 *
 * Authority law: any envelope whose authority flags are not all false is
 * refused outright — this surface never ranks, gates, sizes or times anything.
 */
(function () {
  'use strict';

  var PAGE_LIMIT = 20;

  /* THEME-RESEARCH-CONTRACT-BEGIN */
  /*
   * The pure state/envelope contract — deliberately DOM-free so it can be
   * lifted verbatim and executed under plain node (marker-extraction idiom
   * shared with intelligence-hub-market-pulse.js). Nothing in this block may
   * reference document, window, network or any other browser global.
   */
  var TR_SCHEMA = 'semiconductor_theme_research.v1';
  var TR_TOP_KEYS = [
    'schema', 'definition_version', 'generation', 'request', 'native_subjects',
    'summary', 'companies', 'industrial_views', 'economics', 'expectations',
    'evidence_refs', 'authorized_coverage', 'limitations', 'authority'
  ];
  /* Frozen v1 shapes (contracts/market_ontology/semiconductor_theme_research.v1.schema.json):
   * these four sections are objects carrying a closed status word;
   * `industrial_views` is an object with exactly the five view keys, each a
   * status-bearing view; `native_subjects`, `evidence_refs` and `limitations`
   * are ARRAYS (limitations: non-empty strings). An envelope that models any
   * of them differently is not the contract and is refused. */
  var TR_SECTION_KEYS = ['summary', 'companies', 'economics', 'authorized_coverage'];
  var TR_ARRAY_KEYS = ['native_subjects', 'evidence_refs', 'limitations'];
  var TR_EXPECTATION_KEYS = [
    'management', 'external_consensus', 'house_forecast', 'market_incorporation'
  ];
  /* The frozen identity of the management sequence assessment — the block
   * carrying the only paid figures this client renders. */
  var TR_MANAGEMENT_SCHEMA = 'management_sequence_assessment.v1';
  var TR_AUTHORITY_KEYS = [
    'can_rank', 'can_gate', 'can_size', 'can_originate', 'can_open_entry'
  ];
  var TR_STATUS_VOCAB = ['ready', 'degraded', 'unavailable', 'refused'];

  /* Closed bilingual mode labels. The runtime L.mode points at this map so
   * there is exactly one source of truth; optionLabelsFor() lifts the same
   * map and yields single-language strings for a node-executed test. */
  var TR_MODE_LABELS = {
    latest: ['Latest build', '最新构建'],
    source_history: ['Source history', '按来源历史'],
    system_replay: ['System replay', '系统回放']
  };
  function optionLabelsFor(lang) {
    var keys = Object.keys(TR_MODE_LABELS);
    var out = [];
    for (var i = 0; i < keys.length; i++) {
      var pair_ = TR_MODE_LABELS[keys[i]];
      out.push(lang === 'zh' ? pair_[1] : pair_[0]);
    }
    return out;
  }

  /* Pure view-model helper: a successful envelope yields its limitation
   * entries (text only, the renderer is responsible for textContent); a
   * degraded/unavailable/empty one yields null (the renderer shows the typed
   * status word). authorised_coverage always returns its status word so the
   * caveat line is never empty. The DOM gating (region hidden while gated)
   * is a separate render concern — this helper does not see ui.gate. */
  function limitationsModel(payload) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return { limitations: null, limitationsStatus: null, coverageStatus: null };
    }
    var lim = payload.limitations;
    var cov = payload.authorized_coverage;
    var covStatus = (cov && typeof cov === 'object' && !Array.isArray(cov))
      ? cov.status : undefined;
    /* v1: `limitations` is an array of non-empty strings (possibly empty).
     * Anything else is not the contract → null entries + 'unavailable' so the
     * renderer prints a status word, never an empty region. */
    var entries = null;
    var limStatus = 'unavailable';
    if (Array.isArray(lim) && lim.every(function (e) { return typeof e === 'string' && e.length > 0; })) {
      entries = lim.slice();
      limStatus = 'ready';
    }
    return { limitations: entries, limitationsStatus: limStatus, coverageStatus: covStatus };
  }

  /* Closed slice/view vocabularies — shared with the stored-selection
   * validator so a stored payload (anything with extra keys or non-vocabulary
   * values) is refused outright on the next restore. */
  var TR_SLICE_KEYS = ['hbm_packaging', 'sic_gan_specialty'];
  var TR_VIEW_KEYS = ['composition', 'manufacturing', 'commercial', 'capacity', 'economics'];
  var TR_MODE_KEYS = ['latest', 'source_history', 'system_replay'];
  /* Stored selection must be EXACTLY three closed-vocabulary keys — a stored
   * payload, a stored generation, a stored token, anything else returns
   * null and the defaults stand. */
  function parseStoredSelection(raw) {
    if (!raw || typeof raw !== 'string') return null;
    var sel;
    try { sel = JSON.parse(raw); }
    catch (e) { return null; }
    if (!sel || typeof sel !== 'object' || Array.isArray(sel)) return null;
    var keys = Object.keys(sel);
    if (keys.length !== 3) return null;
    if (TR_SLICE_KEYS.indexOf(sel.slice_key) < 0) return null;
    if (TR_VIEW_KEYS.indexOf(sel.view) < 0) return null;
    if (TR_MODE_KEYS.indexOf(sel.time_mode) < 0) return null;
    return sel;
  }

  /* Classify the fetch response status. 401/402/403 all map to the gate
   * (NIT-5: 402 is the payment-required response the v1 surface must refuse
   * to render just like 401 sign-in and 403 forbidden). 409 stays in the
   * conflict lane for refresh_required handling. Everything else falls
   * through to the JSON branch (success) or the http-error branch. */
  function classifyFetchStatus(status) {
    if (status === 401 || status === 402 || status === 403) return 'gate';
    if (status === 409) return 'conflict';
    if (status >= 200 && status < 300) return 'json';
    return 'http_error';
  }

  /* NIT-9: the current page is the LAST page when it holds fewer rows
   * than pageLimit. A next-page fetch would only cost an auth round-trip
   * and come back empty — the Next button must be disabled. */
  function isFinalPage(section, pageLimit) {
    if (!section || typeof section !== 'object') return true;
    if (!Array.isArray(section.rows)) return true;
    return section.rows.length < pageLimit;
  }

  /* NIT-4: a 200 with a non-JSON body surfaces a SyntaxError whose message
   * embeds response bytes. The runtime catches the rejection and surfaces
   * a typed error whose code is `invalid_json` and whose message is the
   * literal code — the response bytes never reach the user. */
  function newInvalidJsonError() {
    var je = new Error('invalid_json');
    je.code = 'invalid_json';
    return je;
  }

  /* Every failure the UI can show is one of the closed codes in L.errcode; a
   * server-supplied action string or an HTTP status never reaches the DOM. */
  function typedError(code) {
    var te = new Error(code);
    te.code = code;
    return te;
  }

  /* Response-body ceiling for the two research routes; a larger reply is
   * refused as body_too_large before any byte is parsed. */
  var MAX_BODY_BYTES = 2097152;  /* 2 MiB, written as a literal: this file computes nothing */

  function readJsonBody(resp) {
    var ct = String(resp.headers && resp.headers.get ? (resp.headers.get('content-type') || '') : '').toLowerCase();
    if (ct.indexOf('application/json') !== 0) throw typedError('invalid_content_type');
    return resp.text().then(function (text) {
      if (text.length > MAX_BODY_BYTES) throw typedError('body_too_large');
      try { return JSON.parse(text); } catch (e) { throw newInvalidJsonError(); }
    });
  }

  function refuseCrossOriginRedirect(resp) {
    if (resp.redirected) {
      var target;
      try { target = new URL(resp.url, window.location.href); } catch (e) { target = null; }
      if (!target || target.origin !== window.location.origin) throw typedError('cross_origin_redirect');
    }
    return resp;
  }

  /* NIT-7: same-origin guard for the mount's data-api-* URLs. Resolves a
   * relative or absolute URL against `location.origin`; a different origin
   * (or an unparseable string) returns the typed `endpoint_not_same_origin`
   * code so the runtime never fetches a cross-origin string and never
   * attaches a bearer token to one. */
  function resolveSameOrigin(raw) {
    if (!raw || typeof raw !== 'string') {
      return { ok: false, code: 'endpoint_not_same_origin' };
    }
    var resolved;
    try { resolved = new URL(raw, location.origin); }
    catch (e) { return { ok: false, code: 'endpoint_not_same_origin' }; }
    if (resolved.origin !== location.origin) {
      return { ok: false, code: 'endpoint_not_same_origin' };
    }
    return { ok: true, url: resolved.toString() };
  }

  function newResearchState() {
    return {
      epoch: 0,
      principalKey: 'anon',
      payload: null,
      error: null,
      generation: null,
      selection: null
    };
  }

  function _sameKeySet(obj, expected) {
    var seen = Object.keys(obj || {});
    if (seen.length !== expected.length) return false;
    for (var i = 0; i < expected.length; i++) {
      if (!Object.prototype.hasOwnProperty.call(obj, expected[i])) return false;
    }
    return true;
  }

  function _validStatus(value) {
    return typeof value === 'string' && TR_STATUS_VOCAB.indexOf(value) >= 0;
  }

  /* Every authority flag present and false — the research surface's own law,
   * applied wherever an authority block appears (top level and inside the
   * management assessment). A missing block or a missing flag is a refusal,
   * never a default. */
  function _authorityAllFalse(authority) {
    if (!authority || typeof authority !== 'object' || Array.isArray(authority)) return false;
    for (var a = 0; a < TR_AUTHORITY_KEYS.length; a++) {
      if (!Object.prototype.hasOwnProperty.call(authority, TR_AUTHORITY_KEYS[a])) return false;
      if (authority[TR_AUTHORITY_KEYS[a]] !== false) return false;
    }
    /* The contract closes this object (`additionalProperties: false`): an
     * UNKNOWN flag is an authority claim this client cannot evaluate, so it
     * is refused rather than ignored. */
    return _sameKeySet(authority, TR_AUTHORITY_KEYS);
  }

  function validateEnvelope(payload) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return { ok: false, reason: 'payload is not an object' };
    }
    if (!_sameKeySet(payload, TR_TOP_KEYS)) {
      return { ok: false, reason: 'top-level key set is not the closed v1 set' };
    }
    if (payload.schema !== TR_SCHEMA) {
      return { ok: false, reason: 'schema is not ' + TR_SCHEMA };
    }
    if (typeof payload.generation !== 'string' || !payload.generation) {
      return { ok: false, reason: 'generation must be a non-empty string' };
    }
    if (typeof payload.definition_version !== 'string' || !payload.definition_version) {
      return { ok: false, reason: 'definition_version must be a non-empty string' };
    }
    for (var s = 0; s < TR_SECTION_KEYS.length; s++) {
      var key = TR_SECTION_KEYS[s];
      var section = payload[key];
      if (!section || typeof section !== 'object' || Array.isArray(section)) {
        return { ok: false, reason: 'section ' + key + ' is missing or not an object' };
      }
      if (!_validStatus(section.status)) {
        return { ok: false, reason: 'section ' + key + ' has an invalid status' };
      }
    }
    for (var r = 0; r < TR_ARRAY_KEYS.length; r++) {
      var arrKey = TR_ARRAY_KEYS[r];
      if (!Array.isArray(payload[arrKey])) {
        return { ok: false, reason: 'section ' + arrKey + ' must be an array' };
      }
    }
    if (!payload.limitations.every(function (e) { return typeof e === 'string' && e.length > 0; })) {
      return { ok: false, reason: 'limitations entries must be non-empty strings' };
    }
    /* industrial_views: exactly the five closed views, each status-bearing */
    var views = payload.industrial_views;
    if (!views || typeof views !== 'object' || Array.isArray(views) || !_sameKeySet(views, TR_VIEW_KEYS)) {
      return { ok: false, reason: 'industrial_views is not the closed view set' };
    }
    for (var iv = 0; iv < TR_VIEW_KEYS.length; iv++) {
      var ivk = TR_VIEW_KEYS[iv];
      var sub = views[ivk];
      if (!sub || typeof sub !== 'object' || Array.isArray(sub)) {
        return { ok: false, reason: 'industrial_views.' + ivk + ' is not an object' };
      }
      if (!_validStatus(sub.status)) {
        return { ok: false, reason: 'industrial_views.' + ivk + ' has an invalid status' };
      }
    }
    /* economics carries the management triple (or null) and a witness gate word */
    var econ = payload.economics;
    if (typeof econ.witness_gate !== 'string' || !econ.witness_gate) {
      return { ok: false, reason: 'economics.witness_gate must be a non-empty string' };
    }
    if (econ.management !== null && (!econ.management || typeof econ.management !== 'object' || Array.isArray(econ.management))) {
      return { ok: false, reason: 'economics.management must be null or an object' };
    }
    /* The management assessment carries its OWN authority block. The
     * top-level check below would miss it, and this is the block attached to
     * the only paid figures on the page: a payload claiming rank / gate /
     * size / originate / entry authority here is refused exactly as at the
     * top level. */
    if (econ.management && !_authorityAllFalse(econ.management.authority)) {
      return { ok: false, reason: 'economics.management.authority must carry every flag false' };
    }
    /* The management block's own frozen identity. It carries the only paid
     * figures on the page, so a reshaped block under a new definition must
     * not be rendered by a client written for this one. */
    if (econ.management && econ.management.schema !== TR_MANAGEMENT_SCHEMA) {
      return { ok: false, reason: 'economics.management.schema is not the accepted assessment' };
    }
    var expectations = payload.expectations;
    if (!expectations || typeof expectations !== 'object' || Array.isArray(expectations)) {
      return { ok: false, reason: 'expectations is missing or not an object' };
    }
    for (var e = 0; e < TR_EXPECTATION_KEYS.length; e++) {
      var expKey = TR_EXPECTATION_KEYS[e];
      var exp = expectations[expKey];
      if (!exp || typeof exp !== 'object' || Array.isArray(exp)) {
        return { ok: false, reason: 'expectations.' + expKey + ' is missing or not an object' };
      }
      if (!_validStatus(exp.status)) {
        return { ok: false, reason: 'expectations.' + expKey + ' has an invalid status' };
      }
      /* The frozen contract pins these three to `unavailable` (const): this
       * surface has no external consensus, no house forecast and no market
       * incorporation reading, and must not render one because a payload
       * said "ready". Only `management` varies. */
      if (expKey !== 'management' && exp.status !== 'unavailable') {
        return { ok: false, reason: 'expectations.' + expKey + ' must be unavailable' };
      }
    }
    if (!_authorityAllFalse(payload.authority)) {
      return { ok: false, reason: 'authority must carry every flag, every one false' };
    }
    return { ok: true, reason: null };
  }

  /* A response is accepted only when it answers the request the CURRENT
   * state issued. A late answer for another epoch or another principal is
   * dropped with zero side effects; a current answer that fails envelope
   * validation is recorded as invalid_envelope and never rendered. */
  function applyResearchResponse(state, requestEpoch, principalKey, payload) {
    if (!state || typeof state !== 'object') return false;
    if (requestEpoch !== state.epoch || principalKey !== state.principalKey) return false;
    var verdict = validateEnvelope(payload);
    if (!verdict.ok) {
      state.error = { code: 'invalid_envelope' };
      return false;
    }
    state.payload = payload;
    state.generation = payload.generation;
    state.error = null;
    return true;
  }

  /* ------------------------------------------------------------------
   * Mount-driven contract — shared hook 4a (Sol #7780 issuecomment-5813801605).
   *
   * Everything above validates against constants compiled into this file:
   * ONE anchor, ONE slice vocabulary, ONE schema id. A second vertical
   * mounting this same client needs the SAME laws applied to ITS
   * registration, so the functions below take a `spec` built from the
   * mount's own attributes and never read a module constant for anchor,
   * slices or schema. They are pure, they touch no browser global, and the
   * runtime still calls the single-vertical functions above until hook 4b
   * binds the instances — so nothing a member sees changes with this block.
   *
   * Two laws hold throughout: a schema id is compared by `===` and never by
   * pattern, prefix or suffix (a 'semiconductor_theme_research.v1.1' payload
   * is a different contract, not a compatible one), and a label pair is
   * returned literally, never interpreted as markup.
   * ------------------------------------------------------------------ */

  var TR_ID_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789_';

  function _canonicalId(value) {
    if (typeof value !== 'string' || value.length === 0) return false;
    for (var i = 0; i < value.length; i++) {
      if (TR_ID_CHARS.indexOf(value.charAt(i)) < 0) return false;
    }
    return true;
  }

  function _nonEmptyString(value) {
    return typeof value === 'string' && value.length > 0;
  }

  /* The mount's attributes → the spec this client validates against, or a
   * typed refusal naming the field. An unconfigured mount renders nothing:
   * there is no default anchor, no default slice set and no default schema. */
  function mountSpecFrom(attrs) {
    if (!attrs || typeof attrs !== 'object' || Array.isArray(attrs)) {
      return { ok: false, reason: 'unconfigured:attrs' };
    }
    if (!_canonicalId(attrs.anchor)) return { ok: false, reason: 'unconfigured:anchor' };
    if (!_nonEmptyString(attrs.slices)) return { ok: false, reason: 'unconfigured:slices' };
    var raw = attrs.slices.split(',');
    var slices = [];
    for (var i = 0; i < raw.length; i++) {
      var token = raw[i];
      while (token.length && ' \t\n\r'.indexOf(token.charAt(0)) >= 0) token = token.slice(1);
      while (token.length && ' \t\n\r'.indexOf(token.charAt(token.length - 1)) >= 0) {
        token = token.slice(0, -1);
      }
      if (!_canonicalId(token)) return { ok: false, reason: 'unconfigured:slices' };
      if (slices.indexOf(token) >= 0) return { ok: false, reason: 'unconfigured:slices' };
      slices.push(token);
    }
    if (slices.length === 0) return { ok: false, reason: 'unconfigured:slices' };
    if (!_nonEmptyString(attrs.schema)) return { ok: false, reason: 'unconfigured:schema' };
    if (!_nonEmptyString(attrs.evidenceSchema)) {
      return { ok: false, reason: 'unconfigured:evidenceSchema' };
    }
    if (attrs.schema === attrs.evidenceSchema) {
      return { ok: false, reason: 'unconfigured:evidenceSchema' };
    }
    if (!_nonEmptyString(attrs.labels)) return { ok: false, reason: 'unconfigured:labels' };
    var parsed;
    try { parsed = JSON.parse(attrs.labels); }
    catch (e) { return { ok: false, reason: 'unconfigured:labels' }; }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return { ok: false, reason: 'unconfigured:labels' };
    }
    if (!_sameKeySet(parsed, slices)) return { ok: false, reason: 'unconfigured:labels' };
    var labels = {};
    for (var j = 0; j < slices.length; j++) {
      var pair = parsed[slices[j]];
      if (!Array.isArray(pair) || pair.length !== 2) {
        return { ok: false, reason: 'unconfigured:labels' };
      }
      if (!_nonEmptyString(pair[0]) || !_nonEmptyString(pair[1])) {
        return { ok: false, reason: 'unconfigured:labels' };
      }
      labels[slices[j]] = [pair[0], pair[1]];
    }
    if (!_nonEmptyString(attrs.apiQuery)) return { ok: false, reason: 'unconfigured:apiQuery' };
    if (!_nonEmptyString(attrs.apiEvidence)) {
      return { ok: false, reason: 'unconfigured:apiEvidence' };
    }
    return {
      ok: true,
      spec: {
        anchor: attrs.anchor,
        slices: slices,
        schema: attrs.schema,
        evidenceSchema: attrs.evidenceSchema,
        labels: labels,
        apiQuery: attrs.apiQuery,
        apiEvidence: attrs.apiEvidence
      }
    };
  }

  /* Every structural law `validateEnvelope` applies, against the SPEC's
   * schema and slice set instead of this file's constants, plus the one law
   * a multi-vertical page needs and a single-vertical client never did: a
   * payload must answer the mount it was rendered into. Closed reason
   * vocabulary: not_object, schema_mismatch, missing_key:<k>, extra_key:<k>,
   * authority_not_false, wrong_mount, malformed:<path>. */
  function validateEnvelopeFor(spec, payload, expected) {
    if (!spec || typeof spec !== 'object') return { ok: false, reason: 'not_object' };
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return { ok: false, reason: 'not_object' };
    }
    if (payload.schema !== spec.schema) return { ok: false, reason: 'schema_mismatch' };
    var k, i;
    for (i = 0; i < TR_TOP_KEYS.length; i++) {
      k = TR_TOP_KEYS[i];
      if (!Object.prototype.hasOwnProperty.call(payload, k)) {
        return { ok: false, reason: 'missing_key:' + k };
      }
    }
    var own = Object.keys(payload);
    for (i = 0; i < own.length; i++) {
      if (TR_TOP_KEYS.indexOf(own[i]) < 0) {
        return { ok: false, reason: 'extra_key:' + own[i] };
      }
    }
    if (!_authorityAllFalse(payload.authority)) {
      return { ok: false, reason: 'authority_not_false' };
    }
    var want = expected && typeof expected === 'object' && !Array.isArray(expected)
      ? expected : null;
    var request = payload.request;
    if (!want ||
        !request || typeof request !== 'object' || Array.isArray(request) ||
        request.anchor_theme_id !== want.anchor ||
        request.slice_key !== want.slice ||
        want.anchor !== spec.anchor ||
        spec.slices.indexOf(want.slice) < 0) {
      return { ok: false, reason: 'wrong_mount' };
    }
    if (!_nonEmptyString(payload.generation)) {
      return { ok: false, reason: 'malformed:generation' };
    }
    if (!_nonEmptyString(payload.definition_version)) {
      return { ok: false, reason: 'malformed:definition_version' };
    }
    for (i = 0; i < TR_SECTION_KEYS.length; i++) {
      var section = payload[TR_SECTION_KEYS[i]];
      if (!section || typeof section !== 'object' || Array.isArray(section) ||
          !_validStatus(section.status)) {
        return { ok: false, reason: 'malformed:' + TR_SECTION_KEYS[i] };
      }
    }
    for (i = 0; i < TR_ARRAY_KEYS.length; i++) {
      if (!Array.isArray(payload[TR_ARRAY_KEYS[i]])) {
        return { ok: false, reason: 'malformed:' + TR_ARRAY_KEYS[i] };
      }
    }
    if (!payload.limitations.every(function (e) { return _nonEmptyString(e); })) {
      return { ok: false, reason: 'malformed:limitations' };
    }
    var views = payload.industrial_views;
    if (!views || typeof views !== 'object' || Array.isArray(views) ||
        !_sameKeySet(views, TR_VIEW_KEYS)) {
      return { ok: false, reason: 'malformed:industrial_views' };
    }
    for (i = 0; i < TR_VIEW_KEYS.length; i++) {
      var sub = views[TR_VIEW_KEYS[i]];
      if (!sub || typeof sub !== 'object' || Array.isArray(sub) || !_validStatus(sub.status)) {
        return { ok: false, reason: 'malformed:industrial_views.' + TR_VIEW_KEYS[i] };
      }
    }
    var econ = payload.economics;
    if (!_nonEmptyString(econ.witness_gate)) {
      return { ok: false, reason: 'malformed:economics.witness_gate' };
    }
    if (econ.management !== null &&
        (!econ.management || typeof econ.management !== 'object' ||
         Array.isArray(econ.management))) {
      return { ok: false, reason: 'malformed:economics.management' };
    }
    if (econ.management && !_authorityAllFalse(econ.management.authority)) {
      return { ok: false, reason: 'malformed:economics.management.authority' };
    }
    if (econ.management && econ.management.schema !== TR_MANAGEMENT_SCHEMA) {
      return { ok: false, reason: 'malformed:economics.management.schema' };
    }
    var expectations = payload.expectations;
    if (!expectations || typeof expectations !== 'object' || Array.isArray(expectations)) {
      return { ok: false, reason: 'malformed:expectations' };
    }
    for (i = 0; i < TR_EXPECTATION_KEYS.length; i++) {
      var expKey = TR_EXPECTATION_KEYS[i];
      var exp = expectations[expKey];
      if (!exp || typeof exp !== 'object' || Array.isArray(exp) || !_validStatus(exp.status)) {
        return { ok: false, reason: 'malformed:expectations.' + expKey };
      }
      if (expKey !== 'management' && exp.status !== 'unavailable') {
        return { ok: false, reason: 'malformed:expectations.' + expKey };
      }
    }
    return { ok: true, reason: null };
  }

  /* The evidence envelope is its own contract: a schema, an authority block
   * and a generation. It carries no request, no definition_version and none
   * of the research sections, so nothing else is checked here. */
  function validateEvidenceFor(spec, payload, expectedGeneration) {
    if (!spec || typeof spec !== 'object') return { ok: false, reason: 'not_object' };
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return { ok: false, reason: 'not_object' };
    }
    if (payload.schema !== spec.evidenceSchema) {
      return { ok: false, reason: 'schema_mismatch' };
    }
    if (!_authorityAllFalse(payload.authority)) {
      return { ok: false, reason: 'authority_not_false' };
    }
    if (_nonEmptyString(expectedGeneration) && payload.generation !== expectedGeneration) {
      return { ok: false, reason: 'generation_mismatch' };
    }
    return { ok: true, reason: null };
  }

  /* The stored-selection law with the SPEC's slice vocabulary: a selection
   * stored by one vertical's mount is not restorable into another's. */
  function parseStoredSelectionFor(spec, raw) {
    if (!spec || typeof spec !== 'object' || !Array.isArray(spec.slices)) return null;
    if (!raw || typeof raw !== 'string') return null;
    var sel;
    try { sel = JSON.parse(raw); }
    catch (e) { return null; }
    if (!sel || typeof sel !== 'object' || Array.isArray(sel)) return null;
    if (Object.keys(sel).length !== 3) return null;
    if (spec.slices.indexOf(sel.slice_key) < 0) return null;
    if (TR_VIEW_KEYS.indexOf(sel.view) < 0) return null;
    if (TR_MODE_KEYS.indexOf(sel.time_mode) < 0) return null;
    return sel;
  }

  /* `applyResearchResponse`'s laws, spec-driven: a late answer for another
   * epoch or another principal is dropped with zero side effects, and an
   * answer for another mount is refused exactly like an invalid envelope. */
  function applyResearchResponseFor(state, requestEpoch, principalKey, spec, payload, expected) {
    if (!state || typeof state !== 'object') return false;
    if (requestEpoch !== state.epoch || principalKey !== state.principalKey) return false;
    var verdict = validateEnvelopeFor(spec, payload, expected);
    if (!verdict.ok) {
      state.error = { code: 'invalid_envelope' };
      return false;
    }
    state.payload = payload;
    state.generation = payload.generation;
    state.error = null;
    return true;
  }

  function clearResearchState(state) {
    if (!state || typeof state !== 'object') return state;
    state.payload = null;
    state.error = null;
    state.generation = null;
    return state;
  }

  function nextEpoch(state, principalKey) {
    state.epoch = state.epoch + 1;
    state.principalKey = principalKey;
    state.payload = null;
    state.error = null;
    state.generation = null;
    return state.epoch;
  }

  /* No HTML interpretation, ever: source-derived strings flow through this
   * and then textContent, so markup in a label stays literal visible text. */
  function textSafe(value) {
    if (value === null || value === undefined) return '';
    if (typeof value === 'object') {
      try { return JSON.stringify(value); } catch (e) { return String(value); }
    }
    return String(value);
  }

  /* ---- economics: the management sequence triple, rendered as rows ------ */

  /* Closed bilingual maps for the tokens the composer's economics pane may
   * carry (engine/company_intelligence/guidance_history.py vocab). Unknown
   * tokens render the typed 'Unmapped label' pair — a raw internal slug never
   * reaches the screen. Figures are never parsed or computed: they pass
   * through textSafe as text. */
  var TR_ECON_ROLES = ['prior_outlook', 'actual', 'new_outlook'];
  var TR_ECON_LABELS = {
    role: {
      prior_outlook: ['Prior outlook', '此前展望'],
      actual: ['Reported actual', '实际报告值'],
      new_outlook: ['New outlook', '最新展望'],
      prior_vs_actual: ['Prior outlook vs actual', '此前展望对比实际'],
      witness_gate: ['Witness gate', '见证门槛']
    },
    metric: { revenue: ['Revenue', '营收'] },
    unit: { usd_billions: ['US$ bn', '十亿美元'], usd_millions: ['US$ m', '百万美元'] },
    basis: { reported_ifrs: ['reported, IFRS', '报告值（IFRS）'], reported_gaap: ['reported, GAAP', '报告值（GAAP）'] },
    outlook_status: {
      introduced: ['introduced', '首次给出'], reiterated: ['reiterated', '重申'],
      raised: ['raised', '上调'], lowered: ['lowered', '下调'], withdrawn: ['withdrawn', '撤回']
    },
    comparison: {
      comparable: ['Comparable', '可比'], not_comparable: ['Not comparable', '不可比'],
      refused: ['Comparison refused', '拒绝比较']
    },
    position: {
      below_range: ['below the prior range', '低于此前区间'],
      within_range: ['within the prior range', '处于此前区间内'],
      above_range: ['above the prior range', '高于此前区间']
    },
    reason: {
      fiscal_period_mismatch: ['fiscal period mismatch', '财季不一致'],
      metric_mismatch: ['metric mismatch', '指标不一致'],
      unit_mismatch: ['unit mismatch', '单位不一致'],
      basis_change: ['basis changed', '口径变化'],
      currency_mismatch: ['currency mismatch', '货币不一致'],
      perimeter_change: ['perimeter changed', '合并范围变化'],
      definition_change: ['definition changed', '定义变化'],
      range_missing: ['range missing', '缺少区间'],
      different_period: ['different period', '不同期间']
    },
    gate: { positive: ['Positive', '成立'], missing: ['Missing', '缺失'] }
  };
  var TR_UNMAPPED = ['Unmapped label', '未映射标签'];

  /* The economics lookup is the SAME lookup as `pair` — it only adds the
   * "absent field renders as nothing" case. It used to be a second, laxer
   * implementation, and a laxer copy is how a label defect hides from a
   * control that only walks the strict one: the review of 92ff7243f5e
   * reproduced the old `!Array.isArray` bug in this function alone and
   * `labelMapsSelfTest()` still came back clean while every served figure
   * read "Unmapped label". One implementation, walked through both names. */
  function _bi(map, key) {
    if (key === null || key === undefined) return ['', ''];
    return pair(map, key);
  }
  function _same(text) { return [text, text]; }
  function _joinBi(parts, sep) {
    var en = [], zh = [];
    parts.forEach(function (p) {
      if (p && p[0]) en.push(p[0]);
      if (p && p[1]) zh.push(p[1]);
    });
    return [en.join(sep), zh.join(sep)];
  }
  function _rangeText(low, high) {
    var lo = textSafe(low), hi = textSafe(high);
    if (lo && hi) return [lo, hi].join(' – ');
    return lo || hi;
  }

  /* economicsModel(payload) → { status, rows, witnessGate, inputRefs }.
   * rows are [{ role, value: [en, zh], note: [en, zh] }] for the three
   * management roles, the prior-vs-actual comparison and the witness gate;
   * null rows when economics is not ready or carries no management triple
   * (the renderer prints the section's own status word instead). */
  function economicsModel(payload) {
    var empty = { status: null, rows: null, witnessGate: null, inputRefs: [] };
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return empty;
    var econ = payload.economics;
    if (!econ || typeof econ !== 'object' || Array.isArray(econ)) return empty;
    var status = _validStatus(econ.status) ? econ.status : null;
    var refs = Array.isArray(econ.input_refs)
      ? econ.input_refs.filter(function (r) { return typeof r === 'string' && r.length > 0; })
      : [];
    var gate = typeof econ.witness_gate === 'string' ? econ.witness_gate : null;
    var mgmt = econ.management;
    var out = { status: status, rows: null, witnessGate: gate, inputRefs: refs };
    if (status !== 'ready' || !mgmt || typeof mgmt !== 'object' || Array.isArray(mgmt)) return out;
    var roles = mgmt.roles;
    if (!roles || typeof roles !== 'object' || Array.isArray(roles)) return out;
    var rows = [];
    TR_ECON_ROLES.forEach(function (roleKey) {
      var role = roles[roleKey];
      if (!role || typeof role !== 'object' || Array.isArray(role)) return;
      var isActual = roleKey === 'actual';
      var figure = isActual ? textSafe(role.value) : _rangeText(role.low, role.high);
      var value = _joinBi([_bi(TR_ECON_LABELS.metric, role.metric), _same(figure),
                           _bi(TR_ECON_LABELS.unit, role.unit)], ' ');
      var period = _same(textSafe(isActual ? role.fiscal_period : role.horizon));
      var noteParts = [period, _bi(TR_ECON_LABELS.basis, role.basis)];
      if (!isActual && role.status !== null && role.status !== undefined) {
        noteParts.push(_bi(TR_ECON_LABELS.outlook_status, role.status));
      }
      rows.push({ role: roleKey, value: value, note: _joinBi(noteParts, ' · ') });
    });
    var comparisons = mgmt.comparisons;
    var cmp = (comparisons && typeof comparisons === 'object') ? comparisons.prior_vs_actual : null;
    if (cmp && typeof cmp === 'object' && !Array.isArray(cmp)) {
      var cmpValue = _joinBi([_bi(TR_ECON_LABELS.comparison, cmp.status),
                              _bi(TR_ECON_LABELS.position, cmp.position)], ' · ');
      var cmpNote = (cmp.reason === null || cmp.reason === undefined) ? ['', ''] : _bi(TR_ECON_LABELS.reason, cmp.reason);
      rows.push({ role: 'prior_vs_actual', value: cmpValue, note: cmpNote });
    }
    if (gate) {
      rows.push({ role: 'witness_gate', value: _bi(TR_ECON_LABELS.gate, gate), note: _same(refs.join(' · ')) });
    }
    out.rows = rows;
    return out;
  }

  /* ---- industrial rows: frozen `industrial_row` → table cells ------------ */

  var TR_STATEMENT_CHIP = { REPORTED_FACT: 'fact', FORWARD_TARGET: 'target' };

  /* viewRowModel(row) → { label_kind, label, value, note } — plain text cells
   * (source-derived text is not translated). The product/object label leads;
   * the observation (value[–value_high] unit) or, absent a figure, the stage
   * in the source's own language is the reading; the business label and
   * configuration are the note. Never a global product id: selectors are
   * source-local by contract. */
  function viewRowModel(row) {
    if (!row || typeof row !== 'object' || Array.isArray(row)) {
      return { label_kind: null, label: textSafe(row), value: '', note: '' };
    }
    var chipKind = Object.prototype.hasOwnProperty.call(TR_STATEMENT_CHIP, row.statement_mode)
      ? TR_STATEMENT_CHIP[row.statement_mode] : null;
    var label = row.source_product_label || row.object_selector || row.selector || row.predicate;
    var obs = (row.observation && typeof row.observation === 'object') ? row.observation : null;
    var value = '';
    if (obs && obs.value !== null && obs.value !== undefined) {
      value = [_rangeText(obs.value, obs.value_high), textSafe(obs.unit)].filter(Boolean).join(' ');
    } else if (row.stage_source_language || row.stage) {
      value = textSafe(row.stage_source_language || row.stage);
    } else if (row.relation_kind) {
      value = textSafe(row.relation_kind);
    }
    var note = [row.source_business_label, row.configuration, row.model]
      .filter(function (x) { return typeof x === 'string' && x.length > 0; })
      .map(textSafe).join(' · ');
    return { label_kind: chipKind, label: textSafe(label), value: value, note: note };
  }

  /* ---- evidence refs: assertion refs open the receipt drawer; native refs
   * are listed by reference id only (no evidence route serves them) ------- */
  function evidenceRefsModel(payload) {
    if (!payload || typeof payload !== 'object' || !Array.isArray(payload.evidence_refs)) return [];
    var out = [];
    payload.evidence_refs.forEach(function (ref) {
      if (!ref || typeof ref !== 'object' || Array.isArray(ref)) return;
      if (ref.kind === 'assertion' && typeof ref.assertion_ref === 'string' && ref.assertion_ref) {
        out.push({ ref: ref.assertion_ref, label: textSafe(ref.curation_revision || ref.assertion_ref), kind: 'assertion' });
      } else if (ref.kind === 'native' && typeof ref.reference_id === 'string' && ref.reference_id) {
        out.push({ ref: null, label: textSafe(ref.reference_id), kind: 'native' });
      }
    });
    return out;
  }
  /* Closed bilingual maps — static literals only, same discipline as the
   * dossier's V2_ZH. Every entry is a two-string [EN, ZH] tuple; an unknown
   * key resolves to the typed TR_UNMAPPED pair in both languages rather than
   * rendering an internal slug. Inside the contract block since 2026-09-24:
   * these maps and `pair` are what every visible label is made of, and while
   * they sat on the runtime side no node battery could reach them — a guard
   * that read `!Array.isArray(entry)` sent EVERY label to the fallback and
   * the suite stayed green. `labelMapsSelfTest` below is the positive
   * control. */
  var L = {
    slice: {
      hbm_packaging: ['HBM & advanced packaging', 'HBM 与先进封装'],
      sic_gan_specialty: ['SiC / GaN specialty devices', 'SiC / GaN 特种器件']
    },
    view: {
      composition: ['Composition', '构成'],
      manufacturing: ['Manufacturing', '制造'],
      commercial: ['Commercial', '商业'],
      capacity: ['Capacity', '产能'],
      economics: ['Economics', '经济性']
    },
    mode: TR_MODE_LABELS,
    status: {
      ready: ['Ready', '就绪'],
      degraded: ['Degraded — partial data', '降级——部分数据'],
      unavailable: ['Unavailable', '不可用'],
      refused: ['Refused', '拒绝提供']
    },
    label: {
      fact: ['Fact', '事实'],
      target: ['Target', '目标'],
      interpretation: ['Interpretation', '解释']
    },
    expectation: {
      management: ['Management', '管理层'],
      external_consensus: ['External consensus', '外部共识'],
      house_forecast: ['House forecast', '内部预测'],
      market_incorporation: ['Market incorporation', '市场消化程度']
    },
    /* closed set of failure codes the status line and evidence drawer may show */
    errcode: {
      endpoint_not_same_origin: ['Research endpoint is not on this site — request refused.', '研究接口不在本站域名下——请求已拒绝。'],
      cross_origin_redirect: ['The request was redirected off this site — refused.', '请求被重定向到本站之外——已拒绝。'],
      invalid_content_type: ['The server reply was not JSON — refused.', '服务器返回的不是 JSON——已拒绝。'],
      invalid_json: ['The server reply was not readable research data.', '服务器返回的不是可读的研究数据。'],
      invalid_envelope: ['The server reply did not match the research contract.', '服务器返回的内容不符合研究数据合约。'],
      body_too_large: ['The server reply was too large to read safely.', '服务器返回的内容过大，无法安全读取。'],
      request_failed: ['The request failed. Try again later.', '请求失败，请稍后重试。']
    }
  };

  /* Closed bilingual lookup. A bare map[key] hits the prototype and a
   * payload `label_kind: "constructor"` would render "undefined"; a raw
   * internal slug would render the API name on screen. hasOwnProperty +
   * typed bilingual fallback keeps the failure visible and identical in
   * both languages. The entry shape is the two-string tuple every map above
   * uses — anything else is refused. */
  function pair(map, key) {
    if (map && typeof map === 'object' &&
        Object.prototype.hasOwnProperty.call(map, key)) {
      var e = map[key];
      if (Array.isArray(e) && e.length === 2 &&
          typeof e[0] === 'string' && typeof e[1] === 'string') {
        return [e[0], e[1]];
      }
    }
    return [TR_UNMAPPED[0], TR_UNMAPPED[1]];
  }

  /* Positive control for the closed label maps: every key of every map must
   * resolve through BOTH lookup names to its own entry and to the SAME pair,
   * never to TR_UNMAPPED — a laxer second lookup is exactly how the last
   * label defect would have hidden from this control. Returns
   * the list of (map, key) pairs that fell back — empty is the only passing
   * answer. Pure; the UI never calls it, the node battery does. */
  function labelMapsSelfTest() {
    var maps = {
      slice: L.slice, view: L.view, mode: L.mode, status: L.status,
      label: L.label, expectation: L.expectation, errcode: L.errcode,
      econ_role: TR_ECON_LABELS.role, econ_metric: TR_ECON_LABELS.metric,
      econ_unit: TR_ECON_LABELS.unit, econ_basis: TR_ECON_LABELS.basis,
      econ_outlook_status: TR_ECON_LABELS.outlook_status,
      econ_comparison: TR_ECON_LABELS.comparison,
      econ_position: TR_ECON_LABELS.position, econ_reason: TR_ECON_LABELS.reason,
      econ_gate: TR_ECON_LABELS.gate
    };
    var fell_back = [];
    var names = Object.keys(maps);
    for (var i = 0; i < names.length; i++) {
      var map = maps[names[i]];
      var keys = Object.keys(map);
      for (var j = 0; j < keys.length; j++) {
        var direct = pair(map, keys[j]);
        var viaBi = _bi(map, keys[j]);
        if ((direct[0] === TR_UNMAPPED[0] && direct[1] === TR_UNMAPPED[1]) ||
            (viaBi[0] === TR_UNMAPPED[0] && viaBi[1] === TR_UNMAPPED[1]) ||
            direct[0] !== viaBi[0] || direct[1] !== viaBi[1]) {
          fell_back.push(names[i] + '.' + keys[j]);
        }
      }
    }
    return fell_back;
  }

  /* THEME-RESEARCH-CONTRACT-END */

  /* ---- mount + page wiring -------------------------------------------- */

  /* Shared hook 4b (Sol #7780 issuecomment-5813801605): ONE INSTANCE PER
   * MOUNT. The page used to bind a single section and read its anchor, slice
   * list and endpoints straight off the element; a page carrying two
   * registered verticals would have bound the first and ignored the second.
   * Everything below is now a factory over a mount's own SPEC — its anchor,
   * its slice vocabulary, its bilingual slice labels and its schema ids — and
   * the bootstrap at the bottom of this file walks every rendered mount.
   *
   * A mount that cannot say what it is renders a static bilingual note and
   * nothing else: no fetch, no token, no section. A second mount for an
   * anchor already instantiated on this page is refused rather than bound
   * twice. An instance that throws marks only its own section and never stops
   * the others. */
  function mountInstance(MOUNT, SPEC) {
  var ANCHOR_THEME_ID = SPEC.anchor;
  var SLICES = SPEC.slices.slice();
  var apiQueryUrl = SPEC.apiQuery;
  var apiEvidenceUrl = SPEC.apiEvidence;

  /* NIT-7. resolveSameOrigin lives in the contract block so the typed
   * `endpoint_not_same_origin` code is testable under node. fetchTarget
   * wraps it here: a `null` return means the runtime refuses the request
   * without sending it and without attaching a bearer token. */
  function fetchTarget(raw) {
    var r = resolveSameOrigin(raw);
    if (!r.ok) return null;
    return r.url;
  }
  var queryUrl = fetchTarget(apiQueryUrl);
  var evidenceUrl = fetchTarget(apiEvidenceUrl);

  var VIEWS = ['composition', 'manufacturing', 'commercial', 'capacity', 'economics'];
  var MODES = ['latest', 'source_history', 'system_replay'];


  function errorCode(err) {
    var code = err && err.code;
    return (typeof code === 'string' && Object.prototype.hasOwnProperty.call(L.errcode, code)) ? code : 'request_failed';
  }

  function errorWord(code) {
    var w = pair(L.errcode, code);
    return t(w[0], w[1]);
  }

  var GATE_COPY = [
    'This section is member research. Sign in with a Mastermind account to read it.',
    '本栏目为会员研究内容。请使用 Mastermind 账户登录后阅读。'
  ];

  /* ---- runtime state --------------------------------------------------- */

  var state = newResearchState();
  var ui = { gate: false, loading: false, errorText: null, drawerInvoker: null };
  var controller = null;         // page-query abort lane
  var evidenceController = null; // evidence abort lane
  var evidenceRefreshTried = false;
  var offset = 0;

  var currentSlice = SLICES[0] || '';
  var currentView = VIEWS[0];
  var currentMode = MODES[0];

  /* ---- tiny DOM helpers (textContent only; no markup strings anywhere) -- */

  function clear(el) { el.textContent = ''; }

  function t(en, zh) {
    var frag = document.createDocumentFragment();
    var enSpan = document.createElement('span');
    enSpan.className = 'l-en';
    enSpan.textContent = en;
    var zhSpan = document.createElement('span');
    zhSpan.className = 'l-zh';
    zhSpan.textContent = zh || en;
    frag.appendChild(enSpan);
    frag.appendChild(zhSpan);
    return frag;
  }


  function el(tag, className) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    return node;
  }

  function button(className, en, zh) {
    var btn = el('button', className);
    btn.type = 'button';
    btn.appendChild(t(en, zh));
    return btn;
  }

  function mutedLine(fragment) {
    var p = el('p', 'tr-muted');
    p.appendChild(fragment);
    return p;
  }

  function statusWord(status) {
    var w = pair(L.status, status);
    return t(w[0], w[1]);
  }

  function chip(kind) {
    /* the CSS class token is whitelisted against L.label; server text never
     * becomes a class name */
    var known = Object.prototype.hasOwnProperty.call(L.label, kind) ? kind : 'unknown';
    var node = el('span', 'tr-chip tr-chip-' + known);
    var w = pair(L.label, kind);
    node.appendChild(t(w[0], w[1]));
    return node;
  }

  /* ---- remembered selection (the only storage this file touches) -------- */

  function restoreSelection() {
    try {
      /* Per-anchor key: a selection stored by one vertical's mount is not
       * another's to restore, and the slice vocabulary that validates it is
       * this mount's, not a list compiled into this file. */
      var raw = localStorage.getItem('theme_research_sel' + ':' + SPEC.anchor);
      /* parseStoredSelection refuses anything that is not EXACTLY the three
       * closed-vocabulary keys — a stored payload, generation, or token can
       * never propagate back into the runtime. */
      var sel = parseStoredSelectionFor(SPEC, raw);
      /* SLICES is this mount's vocabulary and is the whole check. Conjoining
       * TR_SLICE_KEYS — one vertical's list, compiled into this file — made
       * the test unsatisfiable for every other vertical: a VALID stored
       * selection was silently discarded and the default tab stood, with no
       * error and no console line. The member's remembered tab just never
       * came back. Found by the Robotics receiver reading this wiring. */
      if (sel && SLICES.indexOf(sel.slice_key) >= 0) currentSlice = sel.slice_key;
      if (sel && TR_VIEW_KEYS.indexOf(sel.view) >= 0) currentView = sel.view;
      if (sel && TR_MODE_KEYS.indexOf(sel.time_mode) >= 0) currentMode = sel.time_mode;
      restored = sel;
    } catch (e) { /* unreadable memory is not an error; defaults stand */ }
    state.selection = { slice_key: currentSlice, view: currentView, time_mode: currentMode };
  }

  function rememberSelection() {
    try {
      localStorage.setItem('theme_research_sel' + ':' + SPEC.anchor, JSON.stringify({
        slice_key: currentSlice, view: currentView, time_mode: currentMode
      }));
    } catch (e) { /* remembering a selection is best-effort */ }
  }

  /* ---- auth (the only session acquisition surface) ---------------------- */

  function withAuthHeaders(headers) {
    headers = headers || {};
    if (!(window.MDXAuth && window.MDXAuth.client)) return Promise.resolve(headers);
    return window.MDXAuth.client().then(function (client) { return client.auth.getSession(); }).then(function (result) {
      var token = result && result.data && result.data.session && result.data.session.access_token;
      if (token) headers.Authorization = 'Bearer ' + token;
      return headers;
    }).catch(function () { return headers; });
  }

  function principalOf(user) {
    return (user && user.id) ? String(user.id) : 'anon';
  }

  function abortInFlight() {
    if (controller) { try { controller.abort(); } catch (e) { /* already gone */ } controller = null; }
    if (evidenceController) { try { evidenceController.abort(); } catch (e) { /* already gone */ } evidenceController = null; }
  }

  /* ---- requests --------------------------------------------------------- */

  function queryRequestBody(newOffset) {
    return {
      anchor_theme_id: ANCHOR_THEME_ID,
      slice_key: currentSlice,
      view: currentView,
      time_mode: currentMode,
      source_cutoff: null,
      recorded_cutoff: null,
      offset: newOffset,
      limit: PAGE_LIMIT,
      /* expected_generation is REQUIRED once paging past the first page —
       * the server must prove the generation the user is still reading. */
      expected_generation: newOffset > 0 ? state.generation : null
    };
  }

  function fetchPage(newOffset, isRefreshRetry) {
    if (!queryUrl) {
      /* cross-origin / unparseable mount attribute — refuse the network
       * call, never attach a bearer, and surface the typed error. */
      ui.errorText = 'endpoint_not_same_origin';
      ui.loading = false;
      renderStatus();
      return;
    }
    var reqEpoch = state.epoch;
    var reqPrincipal = state.principalKey;
    abortInFlight();
    var ctrl = new AbortController();
    controller = ctrl;
    ui.loading = true;
    ui.errorText = null;
    renderStatus();

    withAuthHeaders({ 'Content-Type': 'application/json' })
      .then(function (headers) {
        return fetch(queryUrl, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(queryRequestBody(newOffset)),
          credentials: 'same-origin',
          signal: ctrl.signal
        });
      })
      .then(function (resp) {
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) return null;
        refuseCrossOriginRedirect(resp);
        var statusKind = classifyFetchStatus(resp.status);
        if (statusKind === 'gate') {
          /* 401 sign-in / 402 payment required / 403 forbidden — surface the
           * gate copy, never the body. */
          ui.gate = true;
          return null;
        }
        if (statusKind === 'conflict') {
          return resp.json().catch(function () { return null; }).then(function (errBody) {
            var code = errBody && errBody.error && errBody.error.code;
            if (code === 'refresh_required' && !isRefreshRetry) {
              /* generation changed under the reader: back to page 1, once */
              if (state.epoch === reqEpoch && state.principalKey === reqPrincipal) {
                offset = 0;
                fetchPage(0, true);
              }
              return null;
            }
            throw typedError('request_failed');
          });
        }
        if (statusKind === 'http_error') {
          /* the server's action/code text is never shown; only the typed code is */
          throw typedError('request_failed');
        }
        /* statusKind === 'json': a 200-class response. Content-Type, size and
         * JSON shape are each refused with a typed code; no body byte ever
         * reaches a message. */
        return readJsonBody(resp);
      })
      .then(function (payload) {
        if (payload === null || payload === undefined) { renderAll(); return; }
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) return;
        if (applyResearchResponseFor(state, reqEpoch, reqPrincipal, SPEC, payload,
                                     { anchor: SPEC.anchor, slice: currentSlice })) {
          offset = newOffset;
          evidenceRefreshTried = false;
        }
        renderAll();
      })
      .catch(function (err) {
        if (err && err.name === 'AbortError') return;
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) return;
        /* Only a code from the closed L.errcode set is kept; anything else
         * (a server action string, an HTTP status, a message with bytes in
         * it) collapses to request_failed. */
        ui.errorText = errorCode(err);
        renderAll();  /* previous payload (same epoch/principal) stays on screen */
      })
      .finally(function () {
        if (controller === ctrl) controller = null;
        /* re-check epoch/principal before touching the DOM */
        if (state.epoch === reqEpoch && state.principalKey === reqPrincipal) {
          ui.loading = false;
          renderStatus();
        }
      });
  }

  /* Evidence bodies are not frozen by the v1 contract, so the drawer renders
   * whichever plain-text field the server ships and falls back to literal
   * pretty-printed JSON — always via textContent, never as markup. */
  function evidenceText(payload) {
    var fields = ['text', 'statement', 'note', 'body', 'summary'];
    for (var i = 0; i < fields.length; i++) {
      var v = payload && payload[fields[i]];
      if (typeof v === 'string' && v) return v;
    }
    try { return JSON.stringify(payload, null, 2); } catch (e) { return textSafe(payload); }
  }

  function openEvidence(ref, invokingButton) {
    if (!evidenceUrl || !state.generation) {
      if (!state.generation) return;
      openDrawer(invokingButton);
      clear(drawerBody);
      var refuseP = el('p', 'tr-error');
      refuseP.appendChild(errorWord('endpoint_not_same_origin'));
      drawerBody.appendChild(refuseP);
      return;
    }
    openDrawer(invokingButton);
    clear(drawerBody);
    drawerBody.appendChild(mutedLine(t('Loading evidence…', '正在加载证据…')));
    var reqEpoch = state.epoch;
    var reqPrincipal = state.principalKey;
    if (evidenceController) { try { evidenceController.abort(); } catch (e) { /* already gone */ } }
    var ctrl = new AbortController();
    evidenceController = ctrl;

    withAuthHeaders({ 'Content-Type': 'application/json' })
      .then(function (headers) {
        var body = queryRequestBody(offset);
        body.assertion_ref = String(ref);
        /* expected_generation is REQUIRED for evidence: the receipt must
         * prove it answers the generation the user is reading. */
        body.expected_generation = state.generation;
        return fetch(evidenceUrl, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(body),
          credentials: 'same-origin',
          signal: ctrl.signal
        });
      })
      .then(function (resp) {
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) return null;
        refuseCrossOriginRedirect(resp);
        if (resp.status === 401 || resp.status === 402 || resp.status === 403) return { __gate: true };
        if (resp.status === 409) {
          return resp.json().catch(function () { return null; }).then(function (errBody) {
            var code = errBody && errBody.error && errBody.error.code;
            if (code === 'refresh_required') {
              if (!evidenceRefreshTried &&
                  state.epoch === reqEpoch && state.principalKey === reqPrincipal) {
                evidenceRefreshTried = true;
                offset = 0;
                fetchPage(0, true);
              }
              return { __refresh: true };
            }
            throw typedError('request_failed');
          });
        }
        if (!resp.ok) throw typedError('request_failed');
        return readJsonBody(resp);
      })
      .then(function (payload) {
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) return;
        if (!payload) return;
        clear(drawerBody);
        if (payload.__gate) {
          drawerBody.appendChild(el('p', 'tr-gate-copy')).appendChild(t(GATE_COPY[0], GATE_COPY[1]));
          return;
        }
        if (payload.__refresh) {
          drawerBody.appendChild(mutedLine(t(
            'The underlying research was refreshed — reloading page 1. Reopen the evidence afterwards.',
            '底层研究已刷新——正在重新加载第 1 页。之后请重新打开该证据。'
          )));
          return;
        }
        /* The evidence envelope is a contract too: its own schema id, an
         * all-false authority block, and the generation the reader is
         * actually reading. Before hook 4b nothing checked any of the three
         * here, so a reply under another schema rendered as receipt text. */
        var evVerdict = validateEvidenceFor(SPEC, payload, state.generation);
        if (!evVerdict.ok) {
          var evErr = el('p', 'tr-error');
          evErr.appendChild(errorWord('invalid_envelope'));
          drawerBody.appendChild(evErr);
          return;
        }
        var pre = el('pre', 'tr-evidence-pre');
        pre.textContent = textSafe(evidenceText(payload));
        drawerBody.appendChild(pre);
      })
      .catch(function (err) {
        if (err && err.name === 'AbortError') return;
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) return;
        clear(drawerBody);
        var p = el('p', 'tr-error');
        p.appendChild(errorWord(errorCode(err)));
        drawerBody.appendChild(p);
      })
      .finally(function () {
        if (evidenceController === ctrl) evidenceController = null;
        /* re-check epoch/principal before touching the DOM */
        if (state.epoch !== reqEpoch || state.principalKey !== reqPrincipal) closeDrawerQuiet();
      });
  }

  /* ---- DOM scaffold ------------------------------------------------------ */

  var gateBox, controlsBox, statusLine, summaryBox, limitationsBox, tableWrap, expectationsBox,
      evidenceBox, evidenceList, pagerBox, prevBtn, nextBtn, pageInfo,
      drawer, drawerBody, drawerClose;

  function buildDom() {
    var shell = el('div', 'tr-shell');

    gateBox = el('div', 'tr-gate');
    var gateCopy = el('p', 'tr-gate-copy');
    gateCopy.appendChild(t(GATE_COPY[0], GATE_COPY[1]));
    gateBox.appendChild(gateCopy);
    var signIn = button('tr-signin', 'Sign in', '登录');
    signIn.addEventListener('click', function () {
      if (window.MDXAuth && typeof window.MDXAuth.open === 'function') window.MDXAuth.open('signin');
    });
    gateBox.appendChild(signIn);

    controlsBox = el('div', 'tr-controls');
    buildControls();

    statusLine = el('p', 'tr-status');
    statusLine.setAttribute('role', 'status');

    var bodyWrap = el('div', 'tr-body');
    summaryBox = el('div', 'tr-summary');
    limitationsBox = el('div', 'tr-limitations');
    tableWrap = el('div', 'tr-tablewrap');
    expectationsBox = el('div', 'tr-expectations');
    bodyWrap.appendChild(summaryBox);
    bodyWrap.appendChild(limitationsBox);
    bodyWrap.appendChild(tableWrap);
    bodyWrap.appendChild(expectationsBox);

    evidenceBox = el('div', 'tr-evidence');
    var evHead = el('h3');
    evHead.appendChild(t('Evidence receipts', '证据凭据'));
    evidenceBox.appendChild(evHead);
    evidenceList = el('div', 'tr-evidence-list');
    evidenceBox.appendChild(evidenceList);

    pagerBox = el('div', 'tr-pager');
    prevBtn = button('tr-prev', 'Previous', '上一页');
    prevBtn.addEventListener('click', function () {
      if (offset > 0) fetchPage(Math.max(0, offset - PAGE_LIMIT), false);
    });
    nextBtn = button('tr-next', 'Next', '下一页');
    nextBtn.addEventListener('click', function () {
      /* paging past page 1 pins expected_generation to the read generation */
      fetchPage(offset + PAGE_LIMIT, false);
    });
    pageInfo = el('span', 'tr-pageinfo');
    pagerBox.appendChild(prevBtn);
    pagerBox.appendChild(pageInfo);
    pagerBox.appendChild(nextBtn);

    drawer = el('div', 'tr-drawer');
    drawer.setAttribute('role', 'dialog');
    drawer.setAttribute('aria-modal', 'false');
    drawer.hidden = true;
    drawerClose = button('tr-drawer-close', 'Close', '关闭');
    drawerClose.addEventListener('click', closeDrawer);
    drawerBody = el('div', 'tr-drawer-body');
    drawer.appendChild(drawerClose);
    drawer.appendChild(drawerBody);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !drawer.hidden) closeDrawer();
    });

    shell.appendChild(gateBox);
    shell.appendChild(controlsBox);
    shell.appendChild(statusLine);
    shell.appendChild(bodyWrap);
    shell.appendChild(pagerBox);
    shell.appendChild(evidenceBox);
    MOUNT.appendChild(shell);
    MOUNT.appendChild(drawer);
  }

  function buildControls() {
    var sliceRow = el('div', 'tr-tabrow');
    sliceRow.setAttribute('data-tr-role', 'slices');
    SLICES.forEach(function (key) {
      /* The mount's own bilingual label, not a map compiled into this file:
       * that map knows one vertical's slices and would render every other
       * vertical's chips as the typed fallback. */
      var w = Object.prototype.hasOwnProperty.call(SPEC.labels, key)
        ? SPEC.labels[key] : TR_UNMAPPED;
      var tab = button('tr-tab', w[0], w[1]);
      tab.setAttribute('data-tr-slice', key);
      tab.addEventListener('click', function () {
        if (currentSlice === key) return;
        currentSlice = key;
        onSelectionChange();
      });
      sliceRow.appendChild(tab);
    });

    var viewRow = el('div', 'tr-tabrow');
    viewRow.setAttribute('data-tr-role', 'views');
    VIEWS.forEach(function (key) {
      var w = pair(L.view, key);
      var tab = button('tr-tab', w[0], w[1]);
      tab.setAttribute('data-tr-view', key);
      tab.addEventListener('click', function () {
        if (currentView === key) return;
        currentView = key;
        onSelectionChange();
      });
      viewRow.appendChild(tab);
    });

    var modeWrap = el('label', 'tr-mode');
    var modeLabel = el('span', 'tr-mode-label');
    modeLabel.appendChild(t('Time basis', '时间基准'));
    var modeSelect = el('select');
    modeSelect.className = 'tr-mode-select';
    MODES.forEach(function (key) {
      var w = pair(L.mode, key);
      var opt = el('option');
      opt.value = key;
      /* <option> children are ignored by browsers — the closed <select>'s
       * label comes from textContent only. Each option carries single-
       * language text plus data-en/data-zh, and a langchange listener
       * (dispatched by site/theme.js:646) relabels from the page's current
       * documentElement.dataset.lang (default "en"). */
      opt.setAttribute('data-en', w[0]);
      opt.setAttribute('data-zh', w[1]);
      opt.textContent = w[0];
      modeSelect.appendChild(opt);
    });
    function relabelModeOptions() {
      var zh = document.documentElement &&
        document.documentElement.getAttribute('data-lang') === 'zh';
      var opts = modeSelect.querySelectorAll('option[data-zh]');
      Array.prototype.forEach.call(opts, function (o) {
        o.textContent = zh
          ? (o.getAttribute('data-zh') || o.textContent)
          : (o.getAttribute('data-en') || o.textContent);
      });
    }
    document.addEventListener('langchange', relabelModeOptions);
    relabelModeOptions();
    modeSelect.addEventListener('change', function () {
      if (currentMode === modeSelect.value) return;
      currentMode = modeSelect.value;
      onSelectionChange();
    });
    modeWrap.appendChild(modeLabel);
    modeWrap.appendChild(modeSelect);
    controlsBox.setAttribute('data-tr-role', 'controls');
    controlsBox.appendChild(sliceRow);
    controlsBox.appendChild(viewRow);
    controlsBox.appendChild(modeWrap);
  }

  /* ---- rendering --------------------------------------------------------- */

  function sectionForView() {
    if (!state.payload) return null;
    var views = state.payload.industrial_views;
    if (views && typeof views === 'object' && views[currentView] &&
        typeof views[currentView] === 'object') {
      return views[currentView];
    }
    if (currentView === 'economics' && state.payload.economics &&
        typeof state.payload.economics === 'object') {
      return state.payload.economics;
    }
    return null;
  }

  function renderControls() {
    var sliceTabs = controlsBox.querySelectorAll('[data-tr-slice]');
    Array.prototype.forEach.call(sliceTabs, function (tab) {
      tab.classList.toggle('on', tab.getAttribute('data-tr-slice') === currentSlice);
    });
    var viewTabs = controlsBox.querySelectorAll('[data-tr-view]');
    Array.prototype.forEach.call(viewTabs, function (tab) {
      tab.classList.toggle('on', tab.getAttribute('data-tr-view') === currentView);
    });
    var select = controlsBox.querySelector('select');
    if (select) select.value = currentMode;
  }

  function renderStatus() {
    clear(statusLine);
    if (ui.gate) { statusLine.hidden = true; return; }
    statusLine.hidden = false;
    var span;
    if (ui.loading) {
      statusLine.appendChild(t('Loading…', '加载中…'));
    } else if (state.error) {
      statusLine.appendChild(t(
        'The response did not match the expected shape and was not shown.',
        '返回数据不符合预期格式，未予显示。'
      ));
      /* NIT-8: applyResearchResponse keeps the previously good payload on
       * an invalid envelope (state.payload stays set) — match the network-
       * error branch and qualify that the previous successful read is still
       * on screen rather than contradicting ourselves. */
      if (state.payload) {
        statusLine.appendChild(document.createTextNode(' '));
        statusLine.appendChild(t(
          'Showing the previous successful read.',
          '当前显示上一次成功读取的内容。'
        ));
      }
    } else if (ui.errorText) {
      span = el('span', 'tr-error');
      span.appendChild(errorWord(ui.errorText));
      statusLine.appendChild(span);
      if (state.payload) {
        statusLine.appendChild(document.createTextNode(' '));
        statusLine.appendChild(t(
          'Showing the previous successful read.',
          '当前显示上一次成功读取的内容。'
        ));
      }
    } else if (state.payload) {
      span = el('span', 'tr-muted');
      span.textContent = textSafe(state.payload.definition_version);
      statusLine.appendChild(t('Ready · ', '已就绪 · '));
      statusLine.appendChild(span);
    } else {
      statusLine.appendChild(t('Nothing loaded yet.', '尚未加载内容。'));
    }
  }

  function renderLabeledList(container, headingEn, headingZh, value) {
    var heading = el('h3');
    heading.appendChild(t(headingEn, headingZh));
    container.appendChild(heading);
    var items = Array.isArray(value) ? value : (value === null || value === undefined || value === '' ? [] : [value]);
    if (!items.length) {
      container.appendChild(mutedLine(t('Nothing recorded yet.', '暂无记录。')));
      return;
    }
    items.forEach(function (item) {
      var line = el('p', 'tr-line');
      if (item && typeof item === 'object' && !Array.isArray(item)) {
        if (item.label) line.appendChild(chip(item.label));
        var span = el('span');
        span.textContent = textSafe(item.text !== undefined ? item.text : (item.value !== undefined ? item.value : ''));
        line.appendChild(span);
      } else {
        var plain = el('span');
        plain.textContent = textSafe(item);
        line.appendChild(plain);
      }
      container.appendChild(line);
    });
  }

  function renderSummary() {
    clear(summaryBox);
    if (ui.gate || !state.payload) { summaryBox.hidden = true; return; }
    summaryBox.hidden = false;
    var summary = state.payload.summary || {};
    renderLabeledList(summaryBox, 'What changed', '发生了什么变化', summary.what_changed);
    renderLabeledList(summaryBox, 'Why it matters', '为何重要', summary.why_it_matters);
    if (summary.next_evidence !== undefined && summary.next_evidence !== null && summary.next_evidence !== '') {
      renderLabeledList(summaryBox, 'Next evidence to watch', '下一个待观察证据', summary.next_evidence);
    }
  }

  /* Rendered between the summary and the table on every successful envelope:
   * limitations entries as text, authorised_coverage as a caveat line. When
   * either carries a non-success status (or is empty), render its status
   * word — never an empty region, never hidden outside the gated state. */
  function renderLimitations() {
    clear(limitationsBox);
    if (ui.gate || !state.payload) { limitationsBox.hidden = true; return; }
    limitationsBox.hidden = false;

    var heading = el('h3');
    heading.appendChild(t('Limitations', '限制'));
    limitationsBox.appendChild(heading);

    var model = limitationsModel(state.payload);

    /* Limitations: ready+entries → text lines; else → typed status word. */
    var limLine = el('p', 'tr-line');
    if (model.limitations && model.limitations.length) {
      var span = el('span');
      span.textContent = model.limitations.map(textSafe).join(' · ');
      limLine.appendChild(span);
    } else if (model.limitations) {
      limLine.appendChild(t('No limitations recorded for this read.', '本次读取未记录限制。'));
    } else {
      var w = pair(L.status, model.limitationsStatus || 'unavailable');
      limLine.appendChild(t(w[0], w[1]));
    }
    limitationsBox.appendChild(limLine);

    /* Authorised coverage caveat — every successful envelope gets a line. */
    var covLine = el('p', 'tr-line tr-muted');
    var covStatus = model.coverageStatus;
    if (covStatus === 'ready') {
      covLine.appendChild(t('Coverage: ', '覆盖范围：'));
      covLine.appendChild(statusWord('ready'));
    } else {
      covLine.appendChild(t('Coverage: ', '覆盖范围：'));
      var cw = pair(L.status, covStatus || 'unavailable');
      covLine.appendChild(t(cw[0], cw[1]));
    }
    limitationsBox.appendChild(covLine);
  }

  function appendEconomicsRow(tbody, row) {
    var tr = el('tr', 'tr-row-economics');
    var labelCell = el('td', 'tr-cell-label');
    var w = pair(TR_ECON_LABELS.role, row.role);
    labelCell.appendChild(t(w[0], w[1]));
    var valueCell = el('td');
    valueCell.appendChild(t(row.value[0], row.value[1]));
    var noteCell = el('td', 'tr-muted');
    noteCell.appendChild(t(row.note[0], row.note[1]));
    tr.appendChild(labelCell);
    tr.appendChild(valueCell);
    tr.appendChild(noteCell);
    tbody.appendChild(tr);
  }

  function appendIndustrialRow(tbody, raw) {
    var row = viewRowModel(raw);
    var tr = el('tr');
    var labelCell = el('td', 'tr-cell-label');
    if (row.label_kind) labelCell.appendChild(chip(row.label_kind));
    var labelSpan = el('span');
    labelSpan.textContent = row.label;
    labelCell.appendChild(labelSpan);
    var valueCell = el('td');
    valueCell.textContent = row.value;
    var noteCell = el('td', 'tr-muted');
    noteCell.textContent = row.note;
    tr.appendChild(labelCell);
    tr.appendChild(valueCell);
    tr.appendChild(noteCell);
    tbody.appendChild(tr);
  }

  function renderTable() {
    clear(tableWrap);
    if (ui.gate) { tableWrap.hidden = true; return; }
    tableWrap.hidden = false;

    var table = el('table', 'tr-table');
    var thead = el('thead');
    var headRow = el('tr');
    [['Item', '项目'], ['Reading', '读数'], ['Note', '注记']].forEach(function (pair_) {
      var th = el('th');
      th.appendChild(t(pair_[0], pair_[1]));
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    var tbody = el('tbody');
    var section = sectionForView();
    /* Economics: the management sequence triple (economics.management) is
     * the pane's content; the assertion-derived industrial economics rows,
     * when any, follow it. */
    var econ = currentView === 'economics' ? economicsModel(state.payload) : null;
    var econRows = (econ && econ.rows && econ.rows.length) ? econ.rows : null;
    if (!state.payload) {
      appendStatusRow(tbody, t('Nothing loaded yet.', '尚未加载内容。'));
    } else if (econRows) {
      econRows.forEach(function (row) { appendEconomicsRow(tbody, row); });
      if (section && section.status === 'ready' && Array.isArray(section.rows)) {
        section.rows.forEach(function (row) { appendIndustrialRow(tbody, row); });
      }
    } else if (!section) {
      appendStatusRow(tbody, statusWord('unavailable'));
    } else if (section.status !== 'ready') {
      /* the section's own status word — never an invented zero */
      appendStatusRow(tbody, statusWord(section.status));
    } else {
      var rows = Array.isArray(section.rows) ? section.rows : [];
      if (!rows.length) {
        appendStatusRow(tbody, t('No rows in this view yet.', '该视图暂无条目。'));
      }
      rows.forEach(function (row) { appendIndustrialRow(tbody, row); });
    }
    table.appendChild(tbody);
    tableWrap.appendChild(table);
  }

  function appendStatusRow(tbody, fragment) {
    var tr = el('tr');
    var td = el('td', 'tr-cell-status');
    td.colSpan = 3;
    td.appendChild(fragment);
    tr.appendChild(td);
    tbody.appendChild(tr);
  }

  function renderExpectations() {
    clear(expectationsBox);
    if (ui.gate || !state.payload) { expectationsBox.hidden = true; return; }
    expectationsBox.hidden = false;
    var heading = el('h3');
    heading.appendChild(t('Expectations', '预期'));
    expectationsBox.appendChild(heading);
    var expectations = state.payload.expectations || {};
    Object.keys(L.expectation).forEach(function (key) {
      var row = el('div', 'tr-xrow');
      var label = el('span', 'tr-xlabel');
      var w = pair(L.expectation, key);
      label.appendChild(t(w[0], w[1]));
      var value = el('span', 'tr-xvalue');
      var sub = expectations[key];
      var status = sub && typeof sub === 'object' ? sub.status : undefined;
      /* The file's last bare map read used to live here. `L.status[status]`
       * is truthy for prototype keys, so `status: "constructor"` wrote
       * payload text into a class name, and the else-branch rendered a raw
       * internal slug in one language only — both against this surface's
       * own laws. Unreachable through validateEnvelope, which is exactly why
       * it survived: the closed-lookup discipline applies everywhere. */
      var known = Object.prototype.hasOwnProperty.call(L.status, status);
      value.className = 'tr-xvalue tr-x-' + (known ? status : 'unknown');
      value.appendChild(statusWord(status));
      row.appendChild(label);
      row.appendChild(value);
      expectationsBox.appendChild(row);
    });
  }

  function renderEvidence() {
    clear(evidenceList);
    if (ui.gate) { evidenceBox.hidden = true; return; }
    evidenceBox.hidden = false;
    var refs = evidenceRefsModel(state.payload);
    if (!refs.length) {
      evidenceList.appendChild(mutedLine(t('No evidence receipts in this read.', '本次读取没有证据凭据。')));
      return;
    }
    refs.forEach(function (entry) {
      if (entry.ref) {
        var btn = button('tr-evidence-btn', 'Receipt', '凭据');
        var label = el('span');
        label.textContent = ' ' + entry.label;
        btn.appendChild(label);
        btn.addEventListener('click', function () { openEvidence(entry.ref, btn); });
        evidenceList.appendChild(btn);
      } else {
        var line = el('p', 'tr-line tr-muted');
        line.appendChild(t('Native reference ', '原生引用 '));
        var span = el('span');
        span.textContent = entry.label;
        line.appendChild(span);
        evidenceList.appendChild(line);
      }
    });
  }

  function renderPager() {
    if (ui.gate || !state.payload) {
      pagerBox.hidden = true;
      prevBtn.disabled = true;
      nextBtn.disabled = true;
      return;
    }
    pagerBox.hidden = false;
    prevBtn.disabled = offset <= 0;
    /* Disable Next when the current page holds fewer than PAGE_LIMIT rows:
     * the server returned the tail and a next-page fetch would just cost
     * an auth round-trip to come back empty. */
    var section = sectionForView();
    nextBtn.disabled = isFinalPage(section, PAGE_LIMIT);
    var rowCount = (section && Array.isArray(section.rows)) ? section.rows.length : 0;
    var from = rowCount === 0 ? 0 : offset + 1;
    var to = offset + rowCount;
    clear(pageInfo);
    pageInfo.appendChild(t(
      'Rows ' + from + '–' + to + ' · pinned to the read generation',
      '第 ' + from + '–' + to + ' 行 · 锁定当前读取版本'
    ));
  }

  function renderAll() {
    gateBox.hidden = !ui.gate;
    controlsBox.hidden = ui.gate;
    renderControls();
    renderStatus();
    renderSummary();
    renderLimitations();
    renderTable();
    renderExpectations();
    renderEvidence();
    renderPager();
  }

  /* ---- drawer focus law --------------------------------------------------- */

  function openDrawer(invokingButton) {
    ui.drawerInvoker = invokingButton || null;
    drawer.hidden = false;
    drawerClose.focus();
  }

  function closeDrawer() {
    drawer.hidden = true;
    var invoker = ui.drawerInvoker;
    ui.drawerInvoker = null;
    if (invoker && typeof invoker.focus === 'function') invoker.focus();
  }

  function closeDrawerQuiet() {
    drawer.hidden = true;
    ui.drawerInvoker = null;
  }

  /* ---- change plumbing ----------------------------------------------------- */

  function onSelectionChange() {
    state.selection = { slice_key: currentSlice, view: currentView, time_mode: currentMode };
    rememberSelection();
    abortInFlight();
    nextEpoch(state, state.principalKey);
    clearResearchState(state);
    offset = 0;
    evidenceRefreshTried = false;
    ui.errorText = null;
    ui.gate = false;
    renderAll();
    if (state.principalKey !== 'anon') fetchPage(0, false);
  }

  function onAuthUser(user) {
    var principal = principalOf(user);
    MOUNT.hidden = false;  /* reveal only once auth has resolved, signed-in or not */
    abortInFlight();
    nextEpoch(state, principal);
    clearResearchState(state);
    offset = 0;
    evidenceRefreshTried = false;
    closeDrawerQuiet();
    ui.loading = false;
    ui.errorText = null;
    ui.gate = false;
    renderAll();  /* re-render immediately, before any new response resolves */
    if (principal === 'anon') {
      ui.gate = true;
      renderAll();
    } else {
      fetchPage(0, false);
    }
  }

  /* ---- boot ---------------------------------------------------------------- */

  restoreSelection();
  buildDom();
  renderAll();

  if (window.MDXAuth && typeof window.MDXAuth.onChange === 'function') {
    window.MDXAuth.onChange(function (user) { onAuthUser(user); });
    /* Safety net: if the auth surface never settles (SDK blocked), still
     * reveal the mount with the anonymous gate copy rather than nothing. */
    window.setTimeout(function () { if (MOUNT.hidden) onAuthUser(null); }, 2500);
  } else {
    onAuthUser(null);
  }
  }

  /* ---- bootstrap: one instance per rendered mount ---------------------- */

  var MOUNTS = document.querySelectorAll('[data-theme-research-mount]');
  if (!MOUNTS || !MOUNTS.length) return;  // this page rendered no section
  var TR_UNCONFIGURED_NOTE = [
    'Research mount is not configured on this page.',
    '本页的研究模块未配置。'
  ];
  var bound = {};
  for (var mi = 0; mi < MOUNTS.length; mi++) {
    var elMount = MOUNTS[mi];
    var built = mountSpecFrom({
      anchor: elMount.getAttribute('data-anchor-theme-id'),
      slices: elMount.getAttribute('data-slices'),
      schema: elMount.getAttribute('data-schema-id'),
      evidenceSchema: elMount.getAttribute('data-evidence-schema-id'),
      labels: elMount.getAttribute('data-slice-labels'),
      apiQuery: elMount.getAttribute('data-api-query'),
      apiEvidence: elMount.getAttribute('data-api-evidence')
    });
    if (!built.ok) {
      /* Static bilingual copy only — no fetch, no token, nothing about a
       * vertical this page could not describe. */
      elMount.setAttribute('data-tr-state', 'unconfigured');
      var noteEn = document.createElement('span');
      noteEn.className = 'l-en';
      noteEn.textContent = TR_UNCONFIGURED_NOTE[0];
      var noteZh = document.createElement('span');
      noteZh.className = 'l-zh';
      noteZh.textContent = TR_UNCONFIGURED_NOTE[1];
      var noteP = document.createElement('p');
      noteP.className = 'tr-muted';
      noteP.appendChild(noteEn);
      noteP.appendChild(noteZh);
      elMount.appendChild(noteP);
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(bound, built.spec.anchor)) {
      /* Two sections for one anchor would share a storage key, a request
       * epoch and a DOM id. The second is refused, not bound. */
      elMount.setAttribute('data-tr-state', 'duplicate');
      continue;
    }
    bound[built.spec.anchor] = true;
    try {
      mountInstance(elMount, built.spec);
      elMount.setAttribute('data-tr-state', 'mounted');
    } catch (e) {
      /* One vertical's failure is not the page's: mark this section and
       * carry on to the next mount. */
      elMount.setAttribute('data-tr-state', 'failed');
    }
  }
})();
