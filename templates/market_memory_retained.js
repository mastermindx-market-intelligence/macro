/* Market Memory — retained outputs region (.mm-retained).
 * Isolated companion to templates/market_memory.js: own IIFE, own state,
 * own request/auth epochs. Never touches incumbent ticker, legacy recomputed
 * issuer logic, or shared navigation. Wire-contract assumptions are
 * enumerated in INTEGRATION.md (A-1..A-n); no silent fallbacks, no
 * latest/nearest/recomputed substitution, no user/source state in
 * localStorage, no probabilities or forward returns in retained modes.
 */
(function () {
  'use strict';

  var API = '/api/market-memory/v1';
  var REGION_ID = 'mm-retained';
  var MODES = ['saved', 'historical', 'current'];
  var WIRE_MODE = { historical: 'historical_hypothetical', current: 'current_contextual_support' };
  var CATALOG_LIMIT = 20;
  var COMPARE_LIMIT = 8;
  var FIELDS = ['growth_score', 'inflation_score', 'quad', 'liquidity_overlay', 'cycle_tag'];
  var NUMERIC_FIELDS = { growth_score: true, inflation_score: true };
  var OUTCOME_LENSES = ['then_known', 'later_observed'];
  var URL_KEYS = ['mm_mode', 'mm_query', 'mm_subject', 'mm_gen', 'mm_gen_sha', 'mm_cutoff',
    'mm_method', 'mm_context', 'mm_source_field', 'mm_source_context', 'mm_outcome', 'mm_catalog_offset'];
  var MODE_LABELS = {
    saved: ['Saved output', '原始输出'],
    historical: ['Historical comparison', '历史比较'],
    current: ['Current context', '当前参考']
  };
  var FIELD_LABELS = {
    growth_score: ['Growth score', '增长评分'],
    inflation_score: ['Inflation score', '通胀评分'],
    quad: ['Quadrant label', '象限标签'],
    liquidity_overlay: ['Liquidity overlay', '流动性状态'],
    cycle_tag: ['Cycle tag', '周期标签']
  };
  var CATEGORY_LABELS = {
    quad: { 'Q1': ['Q1', 'Q1'], 'Q2': ['Q2', 'Q2'], 'Q3': ['Q3', 'Q3'], 'Q4': ['Q4', 'Q4'] },
    liquidity_overlay: { expanding: ['Expanding', '扩张'], neutral: ['Neutral', '中性'], contracting: ['Contracting', '收缩'] },
    cycle_tag: { early: ['Early cycle', '周期前段'], mid: ['Mid cycle', '周期中段'], late: ['Late cycle', '周期后段'] }
  };
  var UNKNOWN_LABEL = ['Unknown', '未知'];
  var TOKEN_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
  var SHA256_RE = /^[0-9a-f]{64}$/;
  var UTC_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\.\d+)?Z$/;

  var state = {
    booted: false,
    mode: 'saved',
    epoch: 0,
    authEpoch: 0,
    authBlocked: false,
    notice: null,           /* closed presentation state; locale changes never replay transitions */
    catalog: null,          /* normalized catalog { subject, generation, methods, entries, selection, requestClock } */
    catalogPages: 0,
    selected: null,         /* normalized catalog entry the user explicitly chose */
    committed: null,        /* last committed payload { kind, intent, data } */
    sourceCase: null,       /* committed source inspection { contextId, data } */
    outcomeLens: null,      /* 'then_known' | 'later_observed' (UI reserved until L0) */
    sourceField: null,
    sourceContext: null,
    abort: null,
    lastFocus: null
  };
  var ui = {};

  function isZh() { return document.documentElement.getAttribute('data-lang') === 'zh'; }
  function copy(en, zh) { return isZh() ? (zh || en) : en; }
  function esc(value) {
    return String(value === null || value === undefined ? '' : value).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  function asObject(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : null; }
  function asArray(value) { return Array.isArray(value) ? value : null; }
  function fieldLabel(field) {
    var labels = FIELD_LABELS[field] || UNKNOWN_LABEL;
    return copy(labels[0], labels[1]);
  }
  function categoryLabel(field, value) {
    var table = CATEGORY_LABELS[field];
    var entry = table && Object.prototype.hasOwnProperty.call(table, String(value)) ? table[String(value)] : null;
    if (entry) return copy(entry[0], entry[1]);
    if (String(value) === 'unknown') return copy(UNKNOWN_LABEL[0], UNKNOWN_LABEL[1]);
    return null; /* caller decides; raw value still shown verbatim in source study */
  }
  function displayValue(field, value) {
    if (value === null || value === undefined || value === '') return copy('Not reported', '未报告');
    if (NUMERIC_FIELDS[field]) return String(value);
    var label = categoryLabel(field, value);
    return label === null ? String(value) : label;
  }

  /* ------------------------------------------------------------------ *
   * Strict contract layer. Every mismatch raises a typed error; there
   * is no silent repair, default pin or guessed identifier anywhere.
   * ------------------------------------------------------------------ */
  function ContractError(code) {
    var error = new Error(code);
    error.name = 'MMRetainedContractError';
    error.contractCode = code;
    return error;
  }
  function isToken(value) { return typeof value === 'string' && TOKEN_RE.test(value); }
  function isUtc(value) {
    if (typeof value !== 'string' || !UTC_RE.test(value)) return false;
    var parsed = Date.parse(value);
    return Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0, 19) === value.slice(0, 19);
  }
  function requireObject(value, code) {
    var obj = asObject(value);
    if (!obj) throw ContractError(code);
    return obj;
  }
  function requireUtc(value, code) {
    if (!isUtc(value)) throw ContractError(code);
    return value;
  }
  function exactUtc(value, code) {
    requireUtc(value, code);
    var fraction = value.slice(19, -1).replace(/^\./, '');
    return value.slice(0, 19) + '.' + fraction.padEnd(6, '0');
  }
  function requireToken(value, code) {
    if (!isToken(value)) throw ContractError(code);
    return value;
  }
  function requireSha(value, code) {
    if (typeof value !== 'string' || !SHA256_RE.test(value)) throw ContractError(code);
    return value;
  }
  function requireBool(value, code) {
    if (typeof value !== 'boolean') throw ContractError(code);
    return value;
  }

  /* A-ENTRY: catalog entry required wire fields. */
  function normalizeEntry(raw) {
    var entry = requireObject(raw, 'entry_not_object');
    var normalized = {
      queryId: requireToken(entry.query_id, 'entry_query_id'),
      contextId: requireToken(entry.context_id, 'entry_context_id'),
      captureId: requireToken(entry.capture_id, 'entry_capture_id'),
      packetSha256: requireSha(entry.packet_sha256, 'entry_packet_sha256'),
      etag: typeof entry.etag === 'string' && entry.etag ? entry.etag : null,
      eventTime: requireUtc(entry.event_time, 'entry_event_time'),
      asKnownAt: requireUtc(entry.as_known_at, 'entry_as_known_at'),
      capturedAt: entry.captured_at === null || entry.captured_at === undefined ? null : requireUtc(entry.captured_at, 'entry_captured_at'),
      earliestSupportedCutoff: requireUtc(entry.earliest_supported_cutoff, 'entry_earliest_cutoff'),
      sourceSession: entry.source_session === null || entry.source_session === undefined ? null : requireSession(entry.source_session, 'entry_source_session'),
      supportedCutoffs: null,
      newerContextId: isToken(entry.newer_context_id) ? entry.newer_context_id : null,
      fieldsPresent: {}
    };
    var flags = requireObject(entry.field_status, 'entry_field_status');
    FIELDS.forEach(function (field) {
      if (flags[field] !== 'observed' && flags[field] !== 'unavailable') throw ContractError('entry_field_status_' + field);
      normalized.fieldsPresent[field] = flags[field] === 'observed';
    });
    if (asArray(entry.supported_cutoffs) !== null) {
      var cutoffs = [];
      entry.supported_cutoffs.forEach(function (value) { cutoffs.push(requireUtc(value, 'entry_supported_cutoff')); });
      cutoffs.sort();
      if (!cutoffs.length) throw ContractError('entry_supported_cutoff_empty');
      normalized.supportedCutoffs = cutoffs;
    } else {
      normalized.supportedCutoffs = [normalized.earliestSupportedCutoff];
    }
    if (!isToken(normalized.contextId)) throw ContractError('entry_context_id');
    return normalized;
  }

  function requireSession(value, code) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)
        || new Date(value + 'T00:00:00Z').toISOString().slice(0, 10) !== value) throw ContractError(code);
    return value;
  }
  function requireCount(value, code) {
    if (!Number.isSafeInteger(value) || value < 0) throw ContractError(code);
    return value;
  }
  function exactDecimal(value, code, q18) {
    if (typeof value !== 'string' || !/^(?:0|1)(?:\.\d{1,80})?$/.test(value)
        || (q18 && !/^(?:0|1)\.\d{18}$/.test(value))
        || (value[0] === '1' && /[1-9]/.test(value.slice(2)))) throw ContractError(code);
    return value; // Preserve owner decimal bytes; never rank or recompute client-side.
  }
  function normalizeMethod(raw) {
    var method = requireObject(raw, 'method');
    if (method.method !== 'macro_house_state_fixed_range_distance.v1'
        || method.numeric_convention !== 'owner_binary64_exact_decimal_to_q18_half_even.v1'
        || method.fit_status !== 'not_performed'
        || method.purge_calendar_days !== 5 || method.embargo_calendar_days !== 5
        || method.label_interval_coverage !== 'not_established') throw ContractError('method_contract');
    return { mode: method.mode, methodSpecId: requireToken(method.method_spec_id, 'method_id'),
      descriptorId: requireToken(method.descriptor_id, 'method_descriptor'), fields: FIELDS.slice(),
      exclusionDays: method.purge_calendar_days, fitted: false };
  }
  function normalizeCatalog(payload) {
    var body = requireObject(payload, 'catalog_not_object');
    if (body.schema !== 'market_memory.retained_context_catalog.v1') throw ContractError('catalog_schema');
    if (body.mode !== WIRE_MODE.historical && body.mode !== WIRE_MODE.current) throw ContractError('catalog_mode');
    var subject = requireObject(body.subject, 'catalog_subject');
    var generation = requireObject(body.generation, 'catalog_generation');
    var methodsRaw = asArray(body.methods), entriesRaw = asArray(body.entries);
    if (!methodsRaw || !entriesRaw) throw ContractError('catalog_arrays');
    var methods = {};
    methodsRaw.forEach(function (raw) {
      var method = normalizeMethod(raw);
      if ((method.mode !== WIRE_MODE.historical && method.mode !== WIRE_MODE.current) || methods[method.mode]) throw ContractError('catalog_method_mode');
      methods[method.mode] = method;
    });
    if (!methods[WIRE_MODE.historical] || !methods[WIRE_MODE.current]) throw ContractError('catalog_methods_incomplete');
    var instruments = asArray(subject.instrument_ids);
    if (!instruments || !instruments.length || subject.association !== 'house_macro_reference_context') throw ContractError('catalog_subject_association');
    instruments.forEach(function (id) { requireToken(id, 'catalog_instrument_id'); });
    var selected = requireObject(body.selection, 'catalog_selection');
    if (selected.basis !== 'exact_generation_saved_captures_not_opportunity_census') throw ContractError('catalog_selection_basis');
    var normalized = {
      schema: body.schema, mode: body.mode,
      subject: { subjectId: requireToken(subject.subject_id, 'catalog_subject_id'), instrumentIds: instruments.slice(), displayName: null },
      generation: { storeId: requireToken(generation.store_id, 'catalog_store'), profile: requireToken(generation.profile, 'catalog_profile'),
        generationId: requireToken(generation.generation_id, 'catalog_generation_id'), generationSha256: requireSha(generation.generation_sha256, 'catalog_generation_sha256') },
      methods: methods, entries: entriesRaw.map(normalizeEntry),
      selection: { offset: requireCount(selected.offset, 'catalog_offset'), limit: requireCount(selected.limit, 'catalog_limit'),
        returned: requireCount(selected.returned, 'catalog_returned'), total: requireCount(selected.total, 'catalog_total'), continuation: null },
      requestClock: { referenceCutoffUtc: requireUtc(body.server_reference_cutoff, 'catalog_clock'), origin: body.request_clock_origin }
    };
    var n = normalized.selection;
    if (normalized.requestClock.origin !== 'runtime_request_clock' || n.limit < 1 || n.limit > CATALOG_LIMIT
        || n.returned !== normalized.entries.length || n.returned > n.limit || n.offset + n.returned > n.total) throw ContractError('catalog_accounting');
    normalized.entries.forEach(function (entry) { entry.catalogOffset = String(n.offset); });
    var seen = {};
    entriesRaw.forEach(function (entry) {
      if (entry.subject_id !== normalized.subject.subjectId || instruments.indexOf(entry.instrument_id) === -1 || seen[entry.context_id]) throw ContractError('catalog_entry_binding');
      seen[entry.context_id] = true;
    });
    if (selected.continuation !== null) {
      var next = requireObject(selected.continuation, 'catalog_continuation');
      if (next.mode !== body.mode || next.generation_id !== generation.generation_id || next.generation_sha256 !== generation.generation_sha256
          || next.offset !== n.offset + n.returned || next.limit !== n.limit || next.offset >= n.total) throw ContractError('catalog_continuation_binding');
      n.continuation = Object.assign({}, next);
    } else if (n.offset + n.returned < n.total) throw ContractError('catalog_missing_continuation');
    return normalized;
  }

  function bindingMismatch(intent, body) {
    if (body.mode !== WIRE_MODE[intent.mode]) return 'mode';
    var method = asObject(body.method_spec), owner = asObject(body.owner);
    if (!method || method.method_spec_id !== intent.method || method.mode !== body.mode) return 'method_spec_id';
    if (!owner) return 'owner';
    var bindings = { generation_id: intent.gen, generation_sha256: intent.genSha, query_id: intent.query,
      subject_id: intent.subject, requested_subject_id: intent.subject, query_cutoff: intent.cutoff, context_id: intent.context };
    var keys = Object.keys(bindings);
    for (var i = 0; i < keys.length; i += 1) {
      if (!bindings[keys[i]] || owner[keys[i]] !== bindings[keys[i]]) return keys[i];
    }
    return '';
  }

  function reconcileCoverage(denominator, exclusionCounts) {
    var denom = asObject(denominator), counts = asObject(exclusionCounts);
    if (!denom || !counts) return { ok: false, reason: 'accounting_missing' };
    var expected = denom.expected_captures, accounted = denom.accounted_captures;
    if (!Number.isSafeInteger(expected) || expected < 0 || !Number.isSafeInteger(accounted) || accounted !== expected) return { ok: false, reason: 'accounting_incomplete' };
    var sum = 0, keys = Object.keys(counts);
    for (var i = 0; i < keys.length; i += 1) {
      if (!Number.isSafeInteger(counts[keys[i]]) || counts[keys[i]] < 0) return { ok: false, reason: 'exclusion_count' };
      sum += counts[keys[i]];
    }
    return { ok: sum === accounted, accountedExclusions: accounted, sum: sum };
  }

  function normalizeSourceCard(raw) {
    var card = requireObject(raw, 'source_card'), clocks = requireObject(card.clocks, 'source_clocks');
    var facts = asArray(card.facts), fields = {}, seen = {};
    if (!facts) throw ContractError('source_facts');
    FIELDS.forEach(function (field) { fields[field] = null; });
    facts.forEach(function (fact) {
      if (FIELDS.indexOf(fact.field) === -1 || seen[fact.field]) throw ContractError('source_fact_field');
      var citation = requireObject(fact.citation, 'source_citation');
      requireSha(citation.source_sha256, 'source_digest'); requireSha(citation.span_sha256, 'span_digest');
      requireCount(citation.start_byte, 'span_start'); requireCount(citation.end_byte_exclusive, 'span_end');
      requireCount(citation.source_bytes, 'source_bytes');
      if (citation.start_byte >= citation.end_byte_exclusive || citation.end_byte_exclusive > citation.source_bytes
          || typeof citation.quoted_json !== 'string' || citation.json_pointer !== '/state/' + fact.field
          || fact.structural_source_closure !== true || fact.underlying_component_truth_authenticated !== false) throw ContractError('source_fact_contract');
      var quoted;
      try { quoted = JSON.parse(citation.quoted_json); } catch (e) { throw ContractError('source_quote_json'); }
      if (quoted !== fact.value) throw ContractError('source_quote_value');
      fields[fact.field] = fact.value; seen[fact.field] = true;
    });
    return { contextId: requireToken(card.context_id, 'source_context'), captureId: requireToken(card.capture_id, 'source_capture'),
      packetSha256: requireSha(card.packet_sha256, 'source_packet'), subjectId: requireToken(card.subject_id, 'source_subject'),
      sourceSession: requireSession(card.source_session, 'source_session'), eventTime: requireUtc(clocks.event_time, 'source_event'),
      asKnownAt: requireUtc(clocks.as_known_at, 'source_known'), capturedAt: requireUtc(clocks.captured_at, 'source_captured'), state: fields, facts: facts, raw: card };
  }

  function normalizeCompare(intent, payload) {
    var body = requireObject(payload, 'compare_not_object');
    if (body.schema !== 'brain.retained_market_context.v1' || body.available !== true
        || (body.status !== 'MATCHES' && body.status !== 'VALID_EMPTY' && body.status !== 'ABSTAINED')) throw ContractError('compare_status');
    var mismatch = bindingMismatch(intent, body);
    if (mismatch) throw ContractError('compare_binding_' + mismatch);
    var method = normalizeMethod(body.method_spec), rawCards = asArray(body.source_cards), rawNeighbors = asArray(body.neighbors);
    if (!rawCards || !rawNeighbors || rawNeighbors.length > COMPARE_LIMIT) throw ContractError('compare_arrays');
    var cards = {}, neighbors = [], seen = {};
    rawCards.forEach(function (raw) {
      var card = normalizeSourceCard(raw);
      if (cards[card.contextId] || card.subjectId !== intent.subject) throw ContractError('source_card_binding');
      cards[card.contextId] = card;
    });
    var queryCard = cards[intent.context];
    if (!queryCard || queryCard.captureId !== body.owner.capture_id || queryCard.packetSha256 !== body.owner.packet_sha256) throw ContractError('query_card_binding');
    rawNeighbors.forEach(function (raw) {
      var context = requireToken(raw.context_id, 'neighbor_context'), card = cards[context];
      if (!card || context === intent.context || seen[context]) throw ContractError('neighbor_card_binding');
      seen[context] = true;
      var components = requireObject(raw.components_exact_decimal, 'neighbor_components');
      if (Object.keys(components).length !== FIELDS.length) throw ContractError('neighbor_component_count');
      FIELDS.forEach(function (field) { exactDecimal(components[field], 'neighbor_component'); });
      neighbors.push({ contextId: context, comparisonId: requireToken(raw.comparison_id, 'neighbor_comparison'),
        distanceQ18: exactDecimal(raw.distance_q18, 'neighbor_distance', true), components: components, state: card.state,
        differences: differenceRows(queryCard.state, card.state), sourceCard: card });
    });
    var coverage = reconcileCoverage(body.denominator, body.exclusion_counts);
    if (!coverage.ok || body.denominator.returned !== neighbors.length
        || !Number.isSafeInteger(body.denominator.eligible_representatives) || body.denominator.eligible_representatives < neighbors.length
        || (body.status !== 'MATCHES') !== (neighbors.length === 0)) throw ContractError('compare_accounting');
    return { status: body.status, mode: body.mode, owner: body.owner, methodSpec: method, neighbors: neighbors,
      denominator: body.denominator, exclusionCounts: body.exclusion_counts, coverage: coverage,
      sourceCards: cards, selectedState: queryCard.state, missingEvidence: asArray(body.missing_evidence), stateDifferences: asArray(body.state_differences) };
  }

  /* A-PLAYBACK: exact original capture binding. A saved-output read is only
   * committed when the returned IDs (and declared packet digest / ETag when
   * the catalog published them) match the selected catalog entry exactly. */
  function normalizePlayback(entry, payload, etagHeader, intent, contentEncoding) {
    var body = requireObject(payload, 'saved_envelope');
    if (body.schema !== 'market_memory.retained_saved_output.v1' || body.mode !== 'retained_actual_output' || body.status !== 'AVAILABLE') throw ContractError('saved_schema');
    var generation = requireObject(body.generation, 'saved_generation'), selected = requireObject(body.selection, 'saved_selection');
    var packet = requireObject(body.context, 'saved_packet'), receipt = requireObject(body.capture_receipt, 'saved_receipt');
    var feature = requireObject(body.feature_projection, 'saved_feature_projection'), refs = requireObject(body.exact_refs, 'saved_exact_refs');
    if (!intent || generation.generation_id !== intent.gen || generation.generation_sha256 !== intent.genSha
        || selected.query_id !== intent.query || selected.context_id !== intent.context || selected.subject_id !== intent.subject
        || selected.query_cutoff !== intent.cutoff || selected.capture_id !== entry.captureId
        || selected.query_id !== entry.queryId || selected.context_id !== entry.contextId
        || receipt.query_id !== entry.queryId || receipt.context_id !== entry.contextId || receipt.capture_id !== entry.captureId
        || packet.context_id !== entry.contextId || receipt.packet_sha256 !== entry.packetSha256) throw ContractError('saved_exact_binding');
    if (feature.schema !== 'market_memory.saved_house_feature_projection.v1' || body.feature_snapshot !== undefined
        || Object.keys(requireObject(feature.state, 'saved_state')).length !== FIELDS.length) throw ContractError('saved_projection_scope');
    var subject = requireObject(packet.subject, 'saved_subject'), original = requireObject(feature.original_feature_ref, 'saved_original_feature_ref');
    if (subject.subject_id !== intent.subject || subject.instrument_id !== selected.instrument_id
        || receipt.subject.subject_id !== subject.subject_id || receipt.subject.instrument_id !== subject.instrument_id
        || refs.packet.sha256 !== entry.packetSha256 || refs.packet.bytes !== receipt.packet_bytes
        || refs.feature.sha256 !== original.content_sha256 || refs.feature.bytes !== original.content_bytes
        || refs.feature.snapshot_id !== original.snapshot_id
        || ['snapshot_id','content_sha256','content_bytes'].some(function (key) { return original[key] !== receipt.feature_snapshot[key]; })
        || refs.source.raw_sha256 !== receipt.source_evidence.raw_source_sha256 || refs.source.raw_bytes !== receipt.source_evidence.raw_source_bytes) throw ContractError('saved_original_refs');
    requireSha(refs.packet.sha256, 'saved_packet_sha'); requireSha(refs.feature.sha256, 'saved_feature_sha'); requireSha(refs.source.raw_sha256, 'saved_source_sha');
    [refs.packet.bytes, refs.feature.bytes, refs.source.raw_bytes].forEach(function (n) { requireCount(n, 'saved_original_bytes'); if (!n) throw ContractError('saved_original_bytes'); });
    // The edge's gzip/zstd representation suffix is not part of the packet
    // identity. Accept only the exact digest with its matching wire encoding;
    // all envelope, source and packet checks above still apply unchanged.
    var encoding = typeof contentEncoding === 'string' ? contentEncoding.trim().toLowerCase() : '';
    var packetTag = '"' + entry.packetSha256 + '"';
    var encodedTag = (encoding === 'gzip' || encoding === 'zstd')
      ? '"' + entry.packetSha256 + '-' + encoding + '"' : null;
    if (etagHeader && etagHeader !== packetTag && (!encodedTag || etagHeader !== encodedTag)) throw ContractError('saved_etag');
    var clocks = requireObject(body.clocks, 'saved_clocks'), latest = '';
    ['captured_at','raw_source_built_at','raw_source_observed_at','feature_as_of','event_time','as_known_at','knowledge_cutoff'].forEach(function (key) {
      var clock = exactUtc(clocks[key], 'saved_clock'); if (clock > latest) latest = clock;
    });
    ['event_time','as_known_at','knowledge_cutoff'].forEach(function (key) {
      if (clocks[key] !== packet.clocks[key] || clocks[key] !== receipt.clocks[key]) throw ContractError('saved_packet_clocks');
    });
    if (clocks.captured_at !== receipt.captured_at || clocks.feature_as_of !== feature.as_of
        || clocks.raw_source_built_at !== receipt.source_evidence.raw_source_built_at
        || clocks.raw_source_observed_at !== receipt.source_evidence.raw_source_observed_at
        || exactUtc(body.earliest_supported_cutoff, 'saved_earliest') !== latest
        || latest > exactUtc(intent.cutoff, 'saved_cutoff')) throw ContractError('saved_clocks_binding');
    if (!body.outcomes || body.outcomes.status !== 'NOT_ATTACHED' || !body.source_use
        || body.source_use.status !== 'ADMITTED_FOR_NAMED_PURPOSES') throw ContractError('saved_disclosure');
    var card = normalizeSourceCard({context_id:entry.contextId,capture_id:entry.captureId,packet_sha256:entry.packetSha256,
      subject_id:intent.subject,source_session:feature.source_artifact.source_asof,clocks:clocks,facts:body.source_facts});
    if (card.facts.length !== FIELDS.length) throw ContractError('saved_five_fields');
    FIELDS.forEach(function (field) { if (card.state[field] !== feature.state[field]) throw ContractError('saved_quote_projection'); });
    card.facts.forEach(function (fact) { if (fact.citation.source_sha256 !== refs.feature.sha256 || fact.citation.source_bytes !== refs.feature.bytes || fact.citation.snapshot_id !== refs.feature.snapshot_id) throw ContractError('saved_quote_ref'); });
    return {contextId:entry.contextId,queryId:entry.queryId,eventTime:clocks.event_time,asKnownAt:clocks.as_known_at,
      capturedAt:clocks.captured_at,state:card.state,facts:card.facts,raw:body};
  }

  /* Exact equality/difference reporting only — no causal narrative. */
  function differenceRows(queryState, caseState) {
    var rows = [];
    if (!queryState || !caseState) return rows;
    FIELDS.forEach(function (field) {
      var equal = queryState[field] === caseState[field];
      rows.push({ field: field, queryValue: queryState[field], caseValue: caseState[field], equal: equal });
    });
    return rows;
  }
  function summarizeDifferences(rows) {
    var same = [];
    var differ = [];
    rows.forEach(function (row) {
      var label = fieldLabel(row.field);
      if (row.equal) same.push(label);
      else differ.push(label);
    });
    var parts = [];
    if (same.length) parts.push(copy('Same ', '相同：') + same.join(copy(', ', '、')));
    if (differ.length) parts.push(copy('Differ: ', '不同：') + differ.join(copy(', ', '、')));
    if (!parts.length) parts.push(copy('Difference detail unavailable', '差异细节暂不可用'));
    return esc(parts.join(copy('. ', '；')) + '.');
  }
  function formatComponent(field, value) {
    if (value === null || value === undefined || value === '') return copy('Not reported', '未报告');
    if (NUMERIC_FIELDS[field]) return String(value);
    var label = categoryLabel(field, value);
    return label === null ? String(value) : label;
  }

  /* ------------------------------------------------------------------ *
   * URL codec. Strict decode, duplicate-key refusal, incumbent params
   * (e.g. ticker) preserved untouched. No fallback to nearest values.
   * ------------------------------------------------------------------ */
  function parseUrlIntent(search) {
    var params = {};
    var counts = {};
    var rawPairs = [];
    if (typeof search === 'string' && search.length > 1) {
      rawPairs = search.slice(1).split('&');
    }
    for (var index = 0; index < rawPairs.length; index += 1) {
      var pair = rawPairs[index];
      if (!pair) continue;
      var eq = pair.indexOf('=');
      var rawKey = eq === -1 ? pair : pair.slice(0, eq);
      var rawValue = eq === -1 ? '' : pair.slice(eq + 1);
      var key;
      var value;
      try {
        key = decodeURIComponent(rawKey.replace(/\+/g, ' '));
        value = decodeURIComponent(rawValue.replace(/\+/g, ' '));
      } catch (error) {
        return { ok: false, reason: 'url_percent_encoding' };
      }
      if (URL_KEYS.indexOf(key) === -1) continue;
      counts[key] = (counts[key] || 0) + 1;
      if (counts[key] > 1) return { ok: false, reason: 'url_duplicate_key:' + key };
      params[key] = value;
    }
    var intent = {};
    if (Object.prototype.hasOwnProperty.call(params, 'mm_mode')) {
      if (MODES.indexOf(params.mm_mode) === -1) return { ok: false, reason: 'url_mode_unknown' };
      intent.mode = params.mm_mode;
    }
    var tokenKeys = ['mm_query', 'mm_subject', 'mm_gen', 'mm_gen_sha', 'mm_method', 'mm_context'];
    for (var tokenIndex = 0; tokenIndex < tokenKeys.length; tokenIndex += 1) {
      var key = tokenKeys[tokenIndex];
      if (!Object.prototype.hasOwnProperty.call(params, key)) continue;
      var value = params[key];
      if (key === 'mm_gen_sha') {
        if (!SHA256_RE.test(value)) return { ok: false, reason: 'url_gen_sha' };
      } else if (!TOKEN_RE.test(value)) {
        return { ok: false, reason: 'url_token:' + key };
      }
      intent[key === 'mm_gen_sha' ? 'genSha' : key.slice(3)] = value;
    }
    if (Object.prototype.hasOwnProperty.call(params, 'mm_cutoff')) {
      if (!isUtc(params.mm_cutoff)) return { ok: false, reason: 'url_cutoff' };
      intent.cutoff = params.mm_cutoff;
    }
    if (Object.prototype.hasOwnProperty.call(params, 'mm_source_field')) {
      if (FIELDS.indexOf(params.mm_source_field) === -1) return { ok: false, reason: 'url_source_field' };
      intent.sourceField = params.mm_source_field;
    }
    if (Object.prototype.hasOwnProperty.call(params, 'mm_source_context')) {
      if (!isToken(params.mm_source_context)) return {ok:false,reason:'url_source_context'};
      intent.sourceContext = params.mm_source_context;
    }
    if (Object.prototype.hasOwnProperty.call(params, 'mm_outcome')) {
      if (OUTCOME_LENSES.indexOf(params.mm_outcome) === -1) return { ok: false, reason: 'url_outcome_lens' };
      intent.outcomeLens = params.mm_outcome;
    }
    if (Object.prototype.hasOwnProperty.call(params, 'mm_catalog_offset')) {
      if (!/^(0|[1-9][0-9]{0,2})$/.test(params.mm_catalog_offset) || Number(params.mm_catalog_offset) > 255) return { ok: false, reason: 'url_catalog_offset' };
      intent.catalogOffset = params.mm_catalog_offset;
    }
    if (intent.catalogOffset && Number(intent.catalogOffset) > 0 && (!intent.gen || !intent.genSha)) return { ok: false, reason: 'url_offset_without_pin' };
    return { ok: true, intent: intent };
  }

  function writeUrlIntent(intent) {
    if (!window.MarketMemoryIntent) return false;
    var patch = { mode: null, query: null, subject: null, gen: null, gen_sha: null, cutoff: null,
      method: null, context: null, sourceField: null, sourceContext: null, outcomeLens: null, catalogOffset: null };
    Object.keys(intent || {}).forEach(function (name) { patch[name === 'genSha' ? 'gen_sha' : name] = intent[name]; });
    var result = window.MarketMemoryIntent.replace(patch);
    if (!result.ok) { renderTypedUnavailable('missing_exact_capture', result.reason); return false; }
    return true;
  }

  /* ------------------------------------------------------------------ *
   * Authenticated date + clock presentation. Human labels are derived
   * from the exact ISO instant; raw ISO strings remain visible wherever
   * evidence is inspected.
   * ------------------------------------------------------------------ */
  var MONTHS_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function formatUtc(value) {
    if (!isUtc(value)) return null;
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    var pad = function (n) { return (n < 10 ? '0' : '') + n; };
    var day = pad(date.getUTCDate());
    var month = MONTHS_EN[date.getUTCMonth()];
    var year = date.getUTCFullYear();
    var clock = pad(date.getUTCHours()) + ':' + pad(date.getUTCMinutes());
    if (isZh()) return year + '年' + (date.getUTCMonth() + 1) + '月' + date.getUTCDate() + '日 · ' + clock + ' UTC';
    return day + ' ' + month + ' ' + year + ' · ' + clock + ' UTC';
  }
  function clockLabel(value) {
    var human = formatUtc(value);
    return human === null ? (value || '—') : human;
  }

  /* ------------------------------------------------------------------ *
   * Fetch layer. Same MDXAuth + API-base idioms as the incumbent page
   * script; every request carries the caller's epoch and an AbortSignal
   * so a superseded intent can never commit.
   * ------------------------------------------------------------------ */
  function apiBase() {
    return /(^|\.)mastermind-x\.com$/i.test(location.hostname || '') ? '' : (window.MM_API || '');
  }
  function withAuth(headers) {
    headers = headers || {};
    if (!(window.MDXAuth && window.MDXAuth.client)) return Promise.resolve(headers);
    return window.MDXAuth.client()
      .then(function (client) { return client.auth.getSession(); })
      .then(function (result) {
        var token = result && result.data && result.data.session && result.data.session.access_token;
        if (token) headers.Authorization = 'Bearer ' + token;
        return headers;
      })
      .catch(function () { return headers; });
  }
  /* Fixed per-request deadline. The whole exchange — auth session lookup,
   * fetch and body decoding — must complete inside it; a stage that stalls
   * is aborted and the request settles as an ordinary unavailable failure
   * with a manual retry. The bound is a module constant, never a
   * caller-supplied limit. */
  var REQUEST_DEADLINE_MS = 120000;
  function deadlineError() {
    var error = new Error('request_deadline_exceeded');
    error.name = 'MMRetainedDeadlineError';
    error.deadline = true;
    return error;
  }
  function apiFetch(path, params, kind) {
    var dispatchSlot = { epoch: state.epoch, authEpoch: state.authEpoch };
    var query = '';
    var keys = Object.keys(params || {});
    keys.sort();
    query = keys.map(function (key) {
      return encodeURIComponent(key) + '=' + encodeURIComponent(String(params[key]));
    }).join('&');
    if (query) query = '?' + query;
    var storeKey = kind === 'catalog' ? 'catalogAbort' : (kind === 'playback' ? 'sourceAbort' : 'abort');
    var controller = null;
    var timer = null;
    var expired = false;
    function clearDeadline() {
      if (timer !== null) { clearTimeout(timer); timer = null; }
    }
    var request = withAuth({ Accept: 'application/json' }).then(function (headers) {
      if (commitGate(dispatchSlot, state)) { var stale = new Error('superseded'); stale.name = 'AbortError'; throw stale; }
      /* A session that resolved after the deadline must not dispatch. */
      if (expired) throw deadlineError();
      /* Main-result requests and source-inspection requests get separate
       * abort slots so inspecting a case never cancels a results load. */
      if (state[storeKey]) { try { state[storeKey].abort(); } catch (error) { /* already gone */ } }
      controller = new AbortController();
      state[storeKey] = controller;
      return fetch(apiBase() + API + path + query, {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: headers,
        signal: controller.signal
      }).then(function (response) {
        var etag = response.headers && typeof response.headers.get === 'function' ? response.headers.get('ETag') : null;
        var contentEncoding = response.headers && typeof response.headers.get === 'function' ? response.headers.get('Content-Encoding') : null;
        var retryAfter = response.headers && typeof response.headers.get === 'function' ? response.headers.get('Retry-After') : null;
        return response.json().catch(function () { return {}; }).then(function (payload) {
          if (!response.ok) {
            var error = new Error((payload && payload.detail) || ('HTTP ' + response.status));
            error.status = response.status;
            error.payload = payload;
            error.reason = payload && typeof payload.reason === 'string' ? payload.reason : '';
            error.retryAfter = retryAfter ? Number(retryAfter) : null;
            error.kind = kind;
            error.etag = etag;
            throw error;
          }
          return { payload: payload, etag: etag, contentEncoding: contentEncoding };
        });
      });
    });
    /* One fixed deadline covers the entire exchange above. On expiry the
     * deadline settles first, then any started fetch is aborted, so the
     * request surfaces as an ordinary unavailable failure and a late
     * response or body can never commit. The timer clears on either
     * settlement and the losing branch stays handled — no unhandled
     * rejection and no revival. */
    var deadline = new Promise(function (resolve, reject) {
      timer = setTimeout(function () {
        timer = null;
        expired = true;
        reject(deadlineError());
        if (controller) { try { controller.abort(); } catch (error) { /* already gone */ } }
      }, REQUEST_DEADLINE_MS);
    });
    return Promise.race([request, deadline]).then(function (result) {
      clearDeadline();
      return result;
    }, function (error) {
      clearDeadline();
      throw error;
    });
  }

  /* Pure commit gate: an in-flight result may only commit when its request
   * epoch AND auth epoch still match the live session state. */
  function commitGate(incoming, active) {
    if (!incoming || incoming.epoch !== active.epoch) return 'epoch';
    if (incoming.authEpoch !== active.authEpoch) return 'auth';
    return '';
  }
  function beginIntent() {
    var hadLinkedPresentation = !!directLinkedCard();
    state.epoch += 1;
    state.notice = null;
    state.committed = null; state.sourceCase = null;
    /* A refreshed exact reference has no standing response yet. Clear its
     * read-only presentation immediately, including during a failed read. */
    if (hadLinkedPresentation) {
      renderCatalogDependentControls(); renderSelectedClock(); renderModeButtons();
    }
    if (state.catalogAbort) { try { state.catalogAbort.abort(); } catch (error) { /* settled */ } }
    state.catalogAbort = null;
    if (state.abort) { try { state.abort.abort(); } catch (error) { /* already gone */ } }
    state.abort = null;
    return { epoch: state.epoch, authEpoch: state.authEpoch };
  }

  /* ------------------------------------------------------------------ *
   * Typed status mapping. Human copy stays coarse; owner reasons stay
   * internal. 403 source/use denial is distinct from 402 subscription.
   * ------------------------------------------------------------------ */
  function stateKindFor(error) {
    if (!error) return 'unavailable';
    if (error.contractCode) return 'unavailable';
    if (error.name === 'AbortError') return 'aborted';
    if (error.deadline) return 'unavailable';
    var status = error.status;
    if (status === 401) return 'auth_required';
    if (status === 402) return 'subscription';
    if (status === 403) return 'rights_blocked';
    if (status === 404) {
      return error.reason === 'cutoff_not_supported' || error.reason === 'unsupported_cutoff' ? 'unsupported_cutoff' : 'missing_exact_capture';
    }
    if (status === 422) return 'unsupported_cutoff';
    if (status === 429) return 'busy';
    if (status === 503 && (error.reason === 'busy' || error.reason === 'resource_busy' || error.reason === 'concurrency_limit')) return 'busy';
    if (status >= 500) return 'unavailable';
    return 'unavailable';
  }

  function catalogQuery(intent, offset) {
    var params = { offset: offset || 0, limit: CATALOG_LIMIT };
    /* A-CATALOG-QUERY: the discovery route declares an initial mode only for
     * the two contextual-analysis modes; saved-output browsing omits it. */
    if (intent.mode === 'historical' || intent.mode === 'current') {
      params.mode = WIRE_MODE[intent.mode];
    }
    /* Exact pinned continuation only: a caller-supplied generation pin is
     * honored; otherwise the first page pins whatever the server declares
     * and later pages must reuse it verbatim. */
    if (intent.gen) params.generation_id = intent.gen;
    if (intent.genSha) params.generation_sha256 = intent.genSha;
    if (intent.query && intent.context && intent.catalogOffset == null && !(offset > 0)) {
      params.query_id = intent.query;
      params.context_id = intent.context;
    }
    if (state.catalog && (offset || 0) > 0 && !intent.gen && !intent.genSha) {
      params.generation_id = state.catalog.generation.generationId;
      params.generation_sha256 = state.catalog.generation.generationSha256;
    }
    return params;
  }

  function loadCatalog(intent) {
    intent = intent || { mode: state.mode };
    state.intent = Object.assign({}, intent, { mode: intent.mode || state.mode });
    var slot = beginIntent();
    state.committed = null;
    state.sourceCase = null;
    state.selected = null;
    renderLoading();
    ui.resultBody.innerHTML = skeletonMarkup();
    ui.sourceBody.innerHTML = '';
    if (ui.sourceHeading) ui.sourceHeading.classList.remove('is-open');
    return apiFetch('/macro/retained/catalog', catalogQuery(intent || {}, Number(intent.catalogOffset || 0)), 'catalog').then(function (result) {
      if (commitGate(slot, state)) return;
      var catalog;
      try {
        catalog = normalizeCatalog(result.payload);
      } catch (contract) {
        return renderTypedUnavailable('catalog_contract', contract.contractCode);
      }
      /* Deep-link pins must match what the authenticated catalog actually
       * returned; no nearest-substitute capture or generation. */
      var pin = intent.context || intent.cutoff || intent.subject || intent.query || intent.gen || intent.genSha || intent.method;
      if (pin) {
        if (intent.query && intent.context && intent.catalogOffset == null) {
          // The server located the exact pair within this pinned generation.
          // All identities below still have to match before accepting its page.
          intent = Object.assign({}, intent, {catalogOffset: String(catalog.selection.offset)});
        }
        var mismatch = deepLinkMismatch(intent, catalog);
        if (mismatch) return renderTypedUnavailable('deep_link_mismatch', mismatch);
      }
      state.catalog = catalog;
      state.referenceInvalid = false;
      state.catalogPages = 1;
      state.authBlocked = false;
      renderCatalogDependentControls();
      var wanted = intent.context;
      if (wanted) {
        var entry = findEntry(wanted);
        if (!entry) return renderTypedUnavailable('missing_exact_capture', 'context_not_in_disclosed_catalog');
        selectEntry(entry, intent);
        return;
      }
      renderCatalogPrompt();
    }).catch(function (error) {
      if (commitGate(slot, state)) return;
      renderRequestFailure(error, { retry: function () { runCurrentIntent(); } });
    });
  }

  function deepLinkMismatch(intent, catalog) {
    if (intent.subject && intent.subject !== catalog.subject.subjectId) return 'subject';
    if (intent.gen && intent.gen !== catalog.generation.generationId) return 'generation_id';
    if (intent.genSha && intent.genSha !== catalog.generation.generationSha256) return 'generation_sha256';
    var mode = intent.mode || 'saved';
    if (intent.context || intent.query) {
      var required = ['context', 'query', 'subject', 'gen', 'genSha', 'cutoff'];
      if (mode !== 'saved') required.push('method');
      for (var i = 0; i < required.length; i += 1) if (!intent[required[i]]) return 'incomplete_capture_reference';
      var entry = catalog.entries.find(function (item) { return item.contextId === intent.context; });
      if (!entry || entry.queryId !== intent.query) return 'query_context';
      if (String(intent.catalogOffset || '0') !== entry.catalogOffset) return 'catalog_offset';
    }
    if (intent.method) {
      var method = catalog.methods[WIRE_MODE[mode]];
      if (!method || method.methodSpecId !== intent.method) return 'method_spec_id';
    }
    return '';
  }

  function findEntry(contextId) {
    if (!state.catalog) return null;
    for (var index = 0; index < state.catalog.entries.length; index += 1) {
      if (state.catalog.entries[index].contextId === contextId) return state.catalog.entries[index];
    }
    return null;
  }

  /* Explicit "browse further captures" pagination — never automatic. */
  function loadMoreCatalog() {
    if (!state.catalog) return;
    var selection = state.catalog.selection;
    var returned = selection.offset + selection.returned;
    if (selection.total !== null && returned >= selection.total) return;
    var intentSlot = { epoch: state.epoch, authEpoch: state.authEpoch };
    ui.loadMoreButton.setAttribute('disabled', 'disabled');
    apiFetch('/macro/retained/catalog', catalogQuery(state.currentIntent(), returned), 'catalog').then(function (result) {
      ui.loadMoreButton.removeAttribute('disabled');
      if (commitGate(intentSlot, state)) return;
      var page;
      try {
        page = normalizeCatalog(result.payload);
      } catch (contract) {
        return renderTypedUnavailable('catalog_contract', contract.contractCode);
      }
      if (page.generation.generationId !== state.catalog.generation.generationId
          || page.generation.generationSha256 !== state.catalog.generation.generationSha256) {
        return renderTypedUnavailable('catalog_contract', 'continuation_generation_changed');
      }
      var seen = {};
      state.catalog.entries.forEach(function (entry) { seen[entry.contextId] = true; });
      page.entries.forEach(function (entry) {
        if (!seen[entry.contextId]) state.catalog.entries.push(entry);
      });
      state.catalog.selection = page.selection;
      state.catalogPages += 1;
      renderCatalogDependentControls();
    }).catch(function (error) {
      ui.loadMoreButton.removeAttribute('disabled');
      if (commitGate(intentSlot, state)) return;
      renderRequestFailure(error, { retry: function () { loadMoreCatalog(); } });
    });
  }

  /* Explicit capture selection: the only path that ever opens a capture. */
  function selectEntry(entry, intentExtras) {
    state.selected = entry;
    state.sourceCase = null;
    state.committed = null;
    var extras = intentExtras || {};
    state.sourceContext = extras.sourceContext || null;
    state.sourceField = extras.sourceField || null;
    var intent = {
      mode: state.mode,
      query: entry.queryId,
      subject: state.catalog ? state.catalog.subject.subjectId : null,
      gen: state.catalog ? state.catalog.generation.generationId : null,
      genSha: state.catalog ? state.catalog.generation.generationSha256 : null,
      method: extras.method || (state.catalog ? defaultMethodId(state.mode) : null),
      context: entry.contextId,
      cutoff: extras.cutoff || defaultCutoffFor(entry),
      outcomeLens: extras.outcomeLens || state.outcomeLens,
      catalogOffset: entry.catalogOffset || '0'
    };
    state.intent = intent;
    writeUrlIntent(publishableIntent(intent));
    renderCatalogDependentControls();
    if (state.mode === 'saved') return runSaved(intent);
    return runCompare(intent);
  }

  function defaultMethodId(mode) {
    if (!state.catalog) return null;
    var method = state.catalog.methods[WIRE_MODE[mode]];
    return method ? method.methodSpecId : null;
  }
  function defaultCutoffFor(entry) {
    if (state.mode === 'current' && state.catalog) {
      return state.catalog.requestClock.referenceCutoffUtc;
    }
    return entry.earliestSupportedCutoff;
  }

  function publishableIntent(intent) {
    return { mode: intent.mode, context: intent.context, cutoff: intent.cutoff, query: intent.query,
      subject: intent.subject, gen: intent.gen, genSha: intent.genSha, method: intent.method,
      sourceField: state.sourceField, sourceContext: state.sourceContext, outcomeLens: intent.outcomeLens, catalogOffset: intent.catalogOffset };
  }

  /* A complete historical/current reference is syntactically self-describing:
   * query, subject, generation pin, registered method, exact cutoff and
   * context. The retained endpoint validates every one of them against the
   * response owner, so the discovery catalog is not needed as authority.
   * Saved output keeps requiring the catalog because its capture id is
   * published only there; nothing else may substitute for a missing field. */
  function completeCompareRef(intent) {
    if (!intent || (intent.mode !== 'historical' && intent.mode !== 'current')) return false;
    if (!isToken(intent.query) || !isToken(intent.subject) || !isToken(intent.gen)
        || !isToken(intent.method) || !isToken(intent.context)) return false;
    if (typeof intent.genSha !== 'string' || !SHA256_RE.test(intent.genSha)) return false;
    return isUtc(intent.cutoff);
  }

  /* Open a pinned comparison straight from its own exact reference: exactly
   * one retained read, no catalog request dispatched before or alongside it,
   * and no invented selected catalog entry. The picker keeps telling the
   * truth — the saved-capture list simply has not been loaded. */
  function runExactReference(intent) {
    state.selected = null;
    state.referenceInvalid = false;
    renderCatalogDependentControls();
    if (!writeUrlIntent(publishableIntent(intent))) return;
    return runCompare(intent);
  }

  /* Saved output mode: exact operational PIT playback only. No retained
   * analysis, no legacy recomputed substitution, ever. */
  function runSaved(intent) {
    var intentSlot = beginIntent();
    renderLoading();
    ui.resultBody.innerHTML = skeletonMarkup();
    ui.sourceBody.innerHTML = '';
    ui.sourceHeading.classList.remove('is-open');
    var entry = state.selected;
    var path = '/macro/retained/saved';
    var params = { generation_id:intent.gen, generation_sha256:intent.genSha, query_id:intent.query,
      context_id:intent.context, capture_id:entry.captureId, subject_id:intent.subject, query_cutoff:intent.cutoff };
    apiFetch(path, params, 'playback').then(function (result) {
      if (commitGate(intentSlot, state)) return;
      var playback;
      try {
        playback = normalizePlayback(entry, result.payload, result.etag, intent, result.contentEncoding);
      } catch (contract) {
        return renderTypedUnavailable('playback_binding', contract.contractCode);
      }
      state.committed = { kind: 'saved', intent: intent, data: playback };
      renderCommitted();
    }).catch(function (error) {
      if (commitGate(intentSlot, state)) return;
      renderRequestFailure(error, { retry: function () { runSaved(intent); } });
    });
  }

  /* Historical/current modes: exact retained comparison through the
   * registered method only. The analysis cutoff is chosen explicitly;
   * the server refuses unsupported cutoffs and the UI never shifts one. */
  function runCompare(intent) {
    var intentSlot = beginIntent();
    renderLoading();
    ui.resultBody.innerHTML = skeletonMarkup();
    ui.sourceBody.innerHTML = '';
    ui.sourceHeading.classList.remove('is-open');
    var params = {
      query_id: intent.query,
      subject_id: intent.subject,
      generation_id: intent.gen,
      generation_sha256: intent.genSha,
      method_spec_id: intent.method,
      query_cutoff: intent.cutoff,
      limit: COMPARE_LIMIT
    };
    apiFetch('/macro/retained', params, 'compare').then(function (result) {
      if (commitGate(intentSlot, state)) return;
      var compare;
      try {
        compare = normalizeCompare(intent, result.payload);
      } catch (contract) {
        return renderTypedUnavailable('compare_binding', contract.contractCode);
      }
      state.committed = { kind: 'compare', intent: intent, data: compare };
      if (state.sourceContext) {
        var selectedSource = state.sourceContext === intent.context || compare.neighbors.some(function (neighbor) {
          return neighbor.contextId === state.sourceContext;
        });
        if (!selectedSource || !compare.sourceCards[state.sourceContext]) return renderTypedUnavailable('missing_exact_capture', 'source_context_not_in_selected_comparison');
        state.sourceCase = { contextId: state.sourceContext, data: compare.sourceCards[state.sourceContext] };
      }
      renderCommitted();
    }).catch(function (error) {
      if (commitGate(intentSlot, state)) return;
      renderRequestFailure(error, { retry: function () { runCompare(intent); } });
    });
  }

  /* Per-case exact source inspection: opens that case's own capture. */
  function inspectCaseSource(contextId, field) {
    if (state.committed && state.committed.kind === 'compare') {
      var card = state.committed.data.sourceCards[contextId];
      if (!card) return renderTypedUnavailable('missing_exact_capture', 'source_not_in_committed_comparison');
      state.sourceField = field || null; state.sourceContext = contextId;
      state.sourceCase = { contextId: contextId, data: card };
      writeUrlIntent(publishableIntent(currentIntent()));
      renderSourcePanel();
      openSourcePanel({ returnFocus: false });
      return;
    }
    if (!state.committed || state.committed.kind !== 'saved'
        || state.committed.data.contextId !== contextId) {
      return renderTypedUnavailable('missing_exact_capture', 'source_not_in_committed_saved_output');
    }
    state.sourceField = field || null; state.sourceContext = contextId;
    state.sourceCase = { contextId:contextId, data:state.committed.data };
    writeUrlIntent(publishableIntent(currentIntent()));
    renderSourcePanel();
    openSourcePanel({ returnFocus:false });
  }

  /* ------------------------------------------------------------------ *
   * Rendering. Every degraded state below is the frozen copy; none of
   * them fabricates freshness, counts or availability.
   * ------------------------------------------------------------------ */
  function skeletonMarkup() {
    return '<div class="mmr-skeleton"></div><div class="mmr-skeleton"></div><div class="mmr-skeleton"></div>';
  }
  function banner(kind, titleEn, titleZh, bodyEn, bodyZh, actionsHtml) {
    return '<div class="mmr-state" data-mmr-state="' + kind + '"><strong>' + esc(copy(titleEn, titleZh)) +
      '</strong><span>' + esc(copy(bodyEn, bodyZh)) + '</span>' + (actionsHtml || '') + '</div>';
  }
  function actionLink(labelEn, labelZh, action) {
    return '<button type="button" class="gbtn gbtn-quiet mmr-action" data-mmr-action="' + action + '">' +
      esc(copy(labelEn, labelZh)) + '</button>';
  }

  function renderLoading() {
    state.notice = { kind: 'loading' };
    renderNotice();
  }

  function renderNotice() {
    var notice = state.notice;
    if (!notice) return;
    if (notice.kind === 'typed') renderTypedUnavailableNotice(notice.code);
    else if (notice.kind === 'request') renderRequestFailureNotice(notice);
    else if (notice.kind === 'signed_out') renderSignedOutNotice(notice);
    else if (notice.kind === 'prompt') renderCatalogPromptNotice();
    else if (notice.kind === 'catalog_not_loaded') renderCatalogNotLoadedNotice();
    else if (notice.kind === 'loading') {
      ui.status.setAttribute('data-mmr-state', 'loading');
      ui.status.textContent = copy('Loading saved evidence', '正在加载已保存依据');
    }
  }

  function renderTypedUnavailable(kind, internalCode) {
    beginIntent(); state.referenceInvalid = true;
    state.selected = null; state.catalog = null;
    ui.sourceBody.innerHTML = ''; closeSourcePanel();
    ui.originalClock.hidden = true; ui.originalClock.innerHTML = '';
    renderCatalogDependentControls();
    state.notice = { kind: 'typed', code: kind };
    renderNotice();
    try { if (window.console && console.info) console.info('[mm-retained]', kind, internalCode || ''); } catch (e) { /* noop */ }
  }

  function renderTypedUnavailableNotice(kind) {
    ui.status.setAttribute('data-mmr-state', 'error');
    ui.status.textContent = copy('Saved evidence unavailable', '已保存依据不可用');
    if (kind === 'oauth_return_unavailable') {
      ui.status.textContent = copy('Selection unavailable after sign-in', '登录后无法恢复选择');
      ui.resultBody.innerHTML = banner('missing_exact_capture',
        'Choose your saved capture again', '请重新选择已保存记录',
        'This tab could not restore the previous selection. Browse available captures to continue.',
        '此标签页无法恢复先前选择。请浏览可用记录以继续。',
        actionLink('Browse available captures', '浏览可用记录', 'focus-capture-select'));
    } else if (kind === 'missing_exact_capture') {
      ui.resultBody.innerHTML = banner('missing_exact_capture',
        'This saved capture is unavailable', '这条确切记录不可用',
        'Choose an available capture; this exact reference cannot be opened.',
        '请选择可用记录；无法打开此确切引用。',
        actionLink('Browse available captures', '浏览可用记录', 'focus-capture-select'));
    } else if (kind === 'deep_link_mismatch') {
      ui.resultBody.innerHTML = banner('missing_exact_capture',
        'This saved reference cannot be opened', '无法打开此确切引用',
        'The link does not match the evidence currently disclosed to you.',
        '该链接与您当前可见的依据不匹配。',
        actionLink('Browse available captures', '浏览可用记录', 'focus-capture-select'));
    } else {
      ui.resultBody.innerHTML = banner('unavailable',
        'Saved evidence is temporarily unavailable', '已保存依据暂时不可用',
        'The exact source could not be read. Retry this reference or browse available captures.',
        '无法读取确切来源；可重试此引用或浏览可用记录。',
        actionLink('Retry this reference', '重试此引用', 'retry') +
        actionLink('Browse available captures', '浏览可用记录', 'focus-capture-select'));
    }
  }

  function renderRequestFailure(error, options) {
    var kind = stateKindFor(error);
    if (kind === 'aborted') return;
    state.committed = null; state.sourceCase = null; ui.sourceBody.innerHTML = '';
    if (kind === 'auth_required' || kind === 'rights_blocked' || kind === 'subscription') {
      state.catalog = null; state.selected = null; ui.originalClock.hidden = true; ui.originalClock.innerHTML = ''; renderCatalogDependentControls();
    }
    if (kind === 'auth_required') state.authBlocked = true;
    if (kind === 'missing_exact_capture') {
      return renderTypedUnavailable('missing_exact_capture', (error && error.reason) || 'http_404');
    }
    var seconds = Number(error && error.retryAfter);
    state.notice = { kind: 'request', code: kind,
      signinHref: kind === 'auth_required' ? retainedSigninHref() : null,
      wait: Number.isFinite(seconds) && seconds > 0 ? Math.min(Math.ceil(seconds), 60) : 0,
      retry: !!(options && typeof options.retry === 'function') };
    renderNotice();
  }

  function renderRequestFailureNotice(notice) {
    var kind = notice.code;
    var actions;
    if (kind === 'auth_required') {
      ui.status.setAttribute('data-mmr-state', 'error');
      ui.status.textContent = copy('Sign in required', '需要登录');
      var signInTarget = noticeSigninHref(notice);
      ui.resultBody.innerHTML = banner('auth_required',
        'Sign in to open saved evidence', '登录以查看已保存依据',
        'Use your existing account to continue.' + oauthStorageWarning(false),
        '请使用现有账户继续。' + oauthStorageWarning(true),
        '<a class="gbtn gbtn-quiet mmr-action" href="' + esc(signInTarget) + '" data-mmr-action="signin">' + esc(copy('Sign in', '登录')) + ' →</a>');
      return;
    }
    ui.status.setAttribute('data-mmr-state', 'error');
    if (kind === 'busy') {
      var wait = notice.wait;
      ui.status.textContent = copy('Evidence is busy', '依据查询繁忙');
      ui.resultBody.innerHTML = banner('busy',
        'Evidence is busy', '依据查询繁忙',
        'Retry shortly; your exact selection is preserved.',
        '请稍后重试；您的确切选择已保留。',
        actionLink(wait ? copy('Retry in ~' + wait + 's', '约 ' + wait + ' 秒后重试') : copy('Retry', '重试'), null, 'retry'));
      return;
    }
    if (kind === 'subscription') {
      ui.status.textContent = copy('Full-site access required', '需要完整站点权限');
      ui.resultBody.innerHTML = banner('subscription',
        'This evidence surface requires full-site access', '该证据页面需要完整站点权限',
        'Use your existing plan to continue.', '请使用现有方案继续。',
        '<a class="gbtn gbtn-quiet mmr-action" href="plans.html">' + esc(copy('View plans', '查看方案')) + ' →</a>');
      return;
    }
    if (kind === 'rights_blocked') {
      ui.status.textContent = copy('Source unavailable', '来源不可用');
      ui.resultBody.innerHTML = banner('rights_blocked',
        'This source cannot be opened', '无法打开此来源',
        'Your current access does not permit this evidence.',
        '您当前的权限不允许查看这些依据。');
      return;
    }
    if (kind === 'unsupported_cutoff') {
      ui.status.textContent = copy('Cutoff not supported', '截至时间不受支持');
      ui.resultBody.innerHTML = banner('unsupported_cutoff',
        'Evidence was not available then', '当时尚无这些依据',
        'Choose a later evidenced cutoff or inspect the original saved output.',
        '请选择有依据的较晚截至时间，或查看原始输出。',
        actionLink('Browse available captures', '浏览可用记录', 'focus-capture-select'));
      return;
    }
    ui.status.textContent = copy('Saved evidence unavailable', '已保存依据不可用');
    actions = notice.retry
      ? actionLink('Retry this reference', '重试此引用', 'retry')
      : '';
    ui.resultBody.innerHTML = banner('unavailable',
      'Saved evidence is temporarily unavailable', '已保存依据暂时不可用',
      'The exact source could not be read. Retry this reference or browse available captures.',
      '无法读取确切来源；可重试此引用或浏览可用记录。',
      actions + actionLink('Browse available captures', '浏览可用记录', 'focus-capture-select'));
  }

  function renderCatalogPrompt() {
    state.notice = { kind: 'prompt' };
    renderNotice();
  }

  function renderCatalogPromptNotice() {
    ui.status.setAttribute('data-mmr-state', 'idle');
    ui.status.textContent = copy('Catalog loaded', '目录已加载');
    ui.resultBody.innerHTML = banner('prompt',
      'Choose a saved capture', '请选择一条已保存记录',
      'Select a saved SPY capture above, then open or compare it.',
      '在上方选择一条已保存的 SPY 记录，然后打开或比较它。');
  }

  function renderCatalogNotLoaded() {
    state.notice = { kind: 'catalog_not_loaded' };
    renderNotice();
  }

  /* Stated only when no catalog is held: an unloaded list is a loading fact,
   * never a sign-in requirement and never evidence about any reference. */
  function renderCatalogNotLoadedNotice() {
    ui.status.setAttribute('data-mmr-state', 'idle');
    ui.status.textContent = copy('Saved captures not loaded', '已保存记录尚未加载');
    ui.resultBody.innerHTML = banner('catalog_not_loaded',
      'The saved-capture list is not loaded', '已保存记录列表尚未加载',
      'No saved-capture list has been loaded, so no other registered method can be offered here. Browse the saved captures to choose one.',
      '尚未加载已保存记录列表，因此这里无法提供其他注册方法。请浏览已保存记录以选择。',
      actionLink('Browse available captures', '浏览可用记录', 'focus-capture-select'));
  }

  /* A committed direct pinned comparison stands without a catalog or a
   * selected entry. While it is the standing result, its contract-bound
   * source card may be presented read-only; nothing here invents a catalog
   * entry, a selection or a freshness claim, and any new intent, refusal,
   * mode change or sign-out clears the presentation again. */
  function directLinkedCard() {
    if (state.catalog || state.selected) return null;
    var committed = state.committed;
    if (!committed || committed.kind !== 'compare') return null;
    var intent = committed.intent;
    if (!intent || intent.mode !== state.mode || !completeCompareRef(intent)) return null;
    var cards = committed.data ? committed.data.sourceCards : null;
    var card = cards ? cards[intent.context] : null;
    return card || null;
  }

  function renderCatalogDependentControls() {
    var catalog = state.catalog;
    if (!catalog) {
      var linked = directLinkedCard();
      if (linked) {
        /* Truthful controls above a standing pinned comparison: the picker
         * names the linked contract-bound source card instead of implying a
         * capture could be chosen, while the unloaded list itself stays
         * stated and browsing remains the explicit way to pick another. */
        var known = linked.asKnownAt !== linked.eventTime
          ? copy(' · known at ' + clockLabel(linked.asKnownAt), ' · 已知时点 ' + clockLabel(linked.asKnownAt)) : '';
        ui.captureSelect.innerHTML = '<option value="">' + esc(copy('Linked pinned source · ', '已关联固定来源 · ') + clockLabel(linked.eventTime) + known) + '</option>';
        ui.captureSelect.setAttribute('disabled', 'disabled');
        ui.loadMoreButton.hidden = true;
        ui.scopeLine.textContent = copy(
          'This comparison is bound to its exact pinned reference. The saved-capture list is not loaded; browse available captures to choose another one.',
          '此比较绑定其确切的固定引用。已保存记录列表尚未加载；请浏览可用记录以另选。');
        renderCutoffControl();
        return;
      }
      ui.captureSelect.innerHTML = '<option value="">' + esc(copy('Saved captures not loaded', '已保存记录尚未加载')) + '</option>';
      ui.captureSelect.setAttribute('disabled', 'disabled');
      ui.cutoffSelect.innerHTML = '<option value="">' + esc(copy('—', '—')) + '</option>';
      ui.cutoffSelect.setAttribute('disabled', 'disabled');
      ui.loadMoreButton.hidden = true;
      ui.scopeLine.textContent = copy('Saved house macro readings associated with SPY.', '与 SPY 关联的已保存内部宏观解读。');
      /* No catalog is presented: a prior current-mode explanation must not
       * survive sign-out, refusal or an invalid selection in any locale. */
      ui.cutoffNote.hidden = true;
      ui.cutoffNote.textContent = '';
      return;
    }
    var options = catalog.entries.map(function (entry) {
      var when = clockLabel(entry.eventTime);
      var label = when + (entry.asKnownAt !== entry.eventTime ? copy(' · known at ' + clockLabel(entry.asKnownAt), ' · 已知时点 ' + clockLabel(entry.asKnownAt)) : '');
      return '<option value="' + esc(entry.contextId) + '">' + esc(label) + '</option>';
    }).join('');
    ui.captureSelect.innerHTML = (options ? '<option value="">' + esc(copy('Choose a saved capture', '请选择已保存记录')) + '</option>' + options : '') || '<option value="">' + esc(copy('No saved captures disclosed', '未披露已保存记录')) + '</option>';
    if (state.selected) ui.captureSelect.value = state.selected.contextId;
    ui.captureSelect.removeAttribute('disabled');
    ui.scopeLine.textContent = copy(
      'Saved house macro readings associated with ' + (catalog.subject.displayName || 'SPY') + '.',
      '与 ' + (catalog.subject.displayName || 'SPY') + ' 关联的已保存内部宏观解读。');
    renderCutoffControl();
    var selection = catalog.selection;
    var hasMore = selection.total === null
      ? selection.continuation !== null || selection.returned === selection.limit
      : selection.offset + selection.returned < selection.total;
    ui.loadMoreButton.hidden = !hasMore;
    ui.loadMoreButton.textContent = copy('Show more saved captures', '显示更多已保存记录');
    renderModeButtons();
  }

  function renderCutoffControl() {
    var entry = state.selected;
    var current = state.intent ? state.intent.cutoff : null;
    if (state.mode === 'current' && state.catalog) {
      var ref = current || state.catalog.requestClock.referenceCutoffUtc;
      ui.cutoffSelect.innerHTML = '<option value="' + esc(ref) + '">' + esc(clockLabel(ref)) + '</option>';
      ui.cutoffSelect.value = ref;
      ui.cutoffSelect.setAttribute('disabled', 'disabled');
      ui.cutoffNote.hidden = false;
      ui.cutoffNote.textContent = copy(
        'Server reference cutoff for this request · origin: runtime request clock.',
        '本次请求的服务器参考截至时间 · 来源：运行时请求时钟。');
      return;
    }
    ui.cutoffNote.hidden = true;
    if (!entry) {
      var linked = directLinkedCard();
      if (linked) {
        /* The standing pinned reference carries its own exact committed
         * cutoff: present that checked binding read-only instead of asking
         * for a capture the unloaded list cannot offer. */
        var cutoff = state.committed.intent.cutoff;
        ui.cutoffSelect.innerHTML = '<option value="' + esc(cutoff) + '">' + esc(clockLabel(cutoff)) + '</option>';
        ui.cutoffSelect.value = cutoff;
        ui.cutoffSelect.setAttribute('disabled', 'disabled');
        ui.cutoffNote.hidden = false;
        ui.cutoffNote.textContent = copy(
          'Pinned reference cutoff for this comparison · read-only. Browse available captures to compare at another cutoff.',
          '此比较的固定引用截至时间 · 只读。请浏览可用记录以在其他截至时间比较。');
        return;
      }
      ui.cutoffSelect.innerHTML = '<option value="">' + esc(copy('Choose a capture first', '请先选择记录')) + '</option>';
      ui.cutoffSelect.setAttribute('disabled', 'disabled');
      return;
    }
    var cutoffs = entry.supportedCutoffs.slice();
    if (current && isUtc(current) && cutoffs.indexOf(current) === -1) { cutoffs.push(current); cutoffs.sort(); }
    ui.cutoffSelect.innerHTML = cutoffs.map(function (value) {
      return '<option value="' + esc(value) + '">' + esc(clockLabel(value)) + '</option>';
    }).join('');
    if (current && cutoffs.indexOf(current) !== -1) ui.cutoffSelect.value = current;
    else ui.cutoffSelect.value = cutoffs[cutoffs.length - 1];
    ui.cutoffSelect.removeAttribute('disabled');
  }

  function renderModeButtons() {
    MODES.forEach(function (mode) {
      var button = ui.tabs[mode];
      var selected = mode === state.mode;
      button.setAttribute('aria-selected', selected ? 'true' : 'false');
      button.setAttribute('tabindex', selected ? '0' : '-1');
    });
    var primaryLabel = directLinkedCard()
      ? copy('Refresh linked comparison', '刷新已关联比较')
      : (state.mode === 'saved'
        ? copy('Open saved output', '打开原始输出')
        : copy('Compare cases', '比较案例'));
    ui.primaryButton.textContent = primaryLabel;
    ui.modeNote.textContent = state.mode === 'saved'
      ? copy('Reads the original captured packet and its exact source quotes. No analysis is substituted.',
             '读取原始已保存记录及其确切引用；不代入任何分析。')
      : (state.mode === 'historical'
        ? copy('Applies the current fixed contextual method to an exact saved query at your chosen cutoff. A method applied now to a historical case is hypothetical.',
               '将当前固定的语境方法用于所选确切记录与您选择的截至时间；现在套用于历史案例属于假设性分析。')
        : copy('Compares the selected saved reading with cases permitted at the server request clock. A saved old capture is never presented as live today.',
               '将所选已保存解读与请求时钟允许的案例比较；旧的保存记录绝不会显示为今日实时数据。'));
  }

  function renderCommitted() {
    state.notice = null;
    ui.status.setAttribute('data-mmr-state', 'ok');
    ui.status.textContent = state.committed.kind === 'saved'
      ? copy('Saved output loaded', '原始输出已加载')
      : copy('Comparison loaded', '比较已加载');
    if (state.committed.kind === 'saved') renderSaved();
    else renderCompare();
    renderCutoffControl();
    renderSelectedClock();
    renderCorrectionNotice();
    /* A direct pinned commit holds neither catalog nor selected entry, so
     * the pre-request loading copy on the picker must not outlive its own
     * truth: repaint it from the committed binding. Catalog-selected commits
     * already repainted the controls upstream. */
    if (!state.catalog && !state.selected) { renderCatalogDependentControls(); renderModeButtons(); }
  }

  function renderSelectedClock() {
    var entry = state.selected;
    if (!entry) {
      /* A pinned citation opened without the catalog has no selected catalog
       * entry to quote. Only the source card bound to this comparison may
       * be shown, and the absent list is never presented as freshness. */
      var card = state.committed && state.committed.kind === 'compare'
        ? state.committed.data.sourceCards[state.committed.intent.context] : null;
      if (!card) { ui.originalClock.hidden = true; ui.originalClock.innerHTML = ''; return; }
      ui.originalClock.hidden = false;
      ui.originalClock.innerHTML = esc(copy('Original packet cutoff', '原始记录截至')) + ': <strong>' +
        esc(clockLabel(card.asKnownAt)) + '</strong>' +
        (card.capturedAt ? ' · ' + esc(copy('captured ', '捕获于 ')) + esc(clockLabel(card.capturedAt)) : '');
      return;
    }
    ui.originalClock.hidden = false;
    ui.originalClock.innerHTML = esc(copy('Original packet cutoff', '原始记录截至')) + ': <strong>' +
      esc(clockLabel(entry.asKnownAt)) + '</strong>' +
      (entry.capturedAt ? ' · ' + esc(copy('captured ', '捕获于 ')) + esc(clockLabel(entry.capturedAt)) : '');
  }

  function fiveFieldList(fieldsState, withRaw) {
    return '<dl class="mmr-fields">' + FIELDS.map(function (field) {
      var value = fieldsState ? fieldsState[field] : null;
      var shown = displayValue(field, value);
      var title = (withRaw && shown !== String(value) && value !== null && value !== undefined)
        ? ' title="' + esc(String(value)) + '"' : '';
      return '<div><dt>' + esc(fieldLabel(field)) + '</dt><dd' + title + '>' + esc(shown) + '</dd></div>';
    }).join('') + '</dl>';
  }

  function citationsMarkup(playback) {
    var facts = playback.facts;
    if (!facts || !facts.length) {
      return '<p class="mmr-note">' + esc(copy(
        'Exact byte-level citation was not disclosed with this capture. The values above still quote the saved reading; open the authenticated source to verify.',
        '此记录未披露字节级引用。以上数值仍引用已保存解读；请打开经授权的来源核对。')) + '</p>';
    }
    return '<dl class="mmr-citations">' + facts.map(function (fact) {
      var citation = fact.citation || {};
      if (!citation.source_sha256) return '';
      return '<div><dt>' + esc(fieldLabel(fact.field)) + '</dt><dd>' +
        '<code>' + esc(citation.json_pointer || '') + '</code> ' +
        esc(copy('bytes ', '字节 ')) + esc(String(citation.start_byte) + '–' + String(citation.end_byte_exclusive)) +
        ' · <code>' + esc(String(citation.source_sha256)) + '</code>' +
        (citation.quoted_json !== undefined ? '<pre class="mmr-quote">' + esc(citation.quoted_json) + '</pre>' : '') +
        '</dd></div>';
    }).join('') + '</dl>';
  }

  function outcomeBlock() {
    var lens = state.outcomeLens;
    var heading = lens === 'later_observed'
      ? copy('Later outcomes · observed lens', '后续结果 · 事后视角')
      : copy('Later outcomes', '后续结果');
    return '<div class="mmr-outcomes" data-mmr-state="outcome_unavailable"><h3>' + esc(heading) + '</h3><p>' +
      esc(copy('Not attached. Saved cases currently show original readings only.',
               '尚未关联；当前案例仅展示原始解读。')) + '</p></div>';
  }

  function renderSaved() {
    var playback = state.committed.data;
    ui.resultBody.innerHTML =
      '<div class="mmr-query-surface"><strong>' + esc(copy('Selected saved reading', '所选已保存解读')) + '</strong><span>' +
      esc(clockLabel(playback.eventTime)) + '</span>' + fiveFieldList(playback.state, false) + '</div>' +
      '<p class="mmr-note">' + esc(copy(
        'This is the original captured packet. No historical comparison or current analysis is substituted here.',
        '这是原始已保存记录；此处不代入历史比较或当前分析。')) + '</p>' +
      outcomeBlock();
    ui.sourceBody.innerHTML =
      fiveFieldList(playback.state, true) +
      '<details class="mmr-disc"' + (state.sourceField ? ' open' : '') + '><summary>' +
      esc(copy('Exact source reference — verify the quote', '确切来源引用 — 核对原文')) + '</summary>' +
      citationsMarkup(playback) +
      '<p class="mmr-note"><code>' + esc(JSON.stringify({
        context_id: playback.contextId,
        event_time: playback.eventTime,
        as_known_at: playback.asKnownAt
      })) + '</code></p></details>' +
      outcomeBlock();
  }

  function staleNoticeIfNeeded(compare) {
    if (state.mode !== 'current' || !state.selected) return '';
    var analysisDate = Date.parse(compare.intent ? compare.intent.cutoff || '' : '') || Date.parse(state.catalog.requestClock.referenceCutoffUtc);
    var sourceDate = Date.parse(state.selected.eventTime);
    if (!Number.isFinite(analysisDate) || !Number.isFinite(sourceDate) || sourceDate >= analysisDate) return '';
    return banner('stale_last_good',
      'Earlier saved reading', '较早的已保存解读',
      'The source date (' + clockLabel(state.selected.eventTime) + ') is earlier than this analysis (' + clockLabel(state.catalog.requestClock.referenceCutoffUtc) + '). Compare it as saved evidence.',
      '来源日期（' + clockLabel(state.selected.eventTime) + '）早于本次分析（' + clockLabel(state.catalog.requestClock.referenceCutoffUtc) + '）；请按保存依据比较。');
  }

  function correctionNoticeIfNeeded() {
    var entry = state.selected;
    if (!entry || !entry.newerContextId || !findEntry(entry.newerContextId)) return '';
    return banner('corrected_version',
      'A later saved version exists', '存在较晚保存版本',
      'This view keeps the selected original. Open the later version to compare.',
      '此视图保留所选原始版本；可打开较晚版本进行比较。',
      '<button type="button" class="gbtn gbtn-quiet mmr-action" data-mmr-action="open-newer" data-mmr-context="' + esc(entry.newerContextId) + '">' +
      esc(copy('Open the later version', '打开较晚版本')) + '</button>');
  }

  var COVERAGE_LABELS = {
  "other_subject": [
    "Other subject",
    "其他对象"
  ],
  "future_capture": [
    "Not known by cutoff",
    "截至时间尚未知"
  ],
  "unknown_source_session": [
    "Source session unavailable",
    "来源日期缺失"
  ],
  "revision_sibling": [
    "Another version of the same session",
    "同一来源日期的其他版本"
  ],
  "query_self": [
    "Selected query itself",
    "所选查询本身"
  ],
  "query_episode": [
    "Same source session",
    "同一来源日期"
  ],
  "registered_purge": [
    "Within prior exclusion window",
    "位于前置排除窗口"
  ],
  "registered_embargo": [
    "Within following exclusion window",
    "位于后置排除窗口"
  ],
  "registered_coordinates_unavailable": [
    "Required fields unavailable",
    "必要字段缺失"
  ],
  "numerically_eligible": [
    "Eligible for comparison",
    "可参与比较"
  ]
};

  function coverageMarkup(compare) {
    var denominator = compare.denominator;
    var counts = compare.exclusionCounts;
    if (!denominator) {
      return '<p class="mmr-note">' + esc(copy(
        'Coverage accounting was not disclosed with this response.',
        '本次响应未披露覆盖核算。')) + '</p>';
    }
    var reconcile = compare.coverage;
    var rows = '<div><dt>' + esc(copy('Scope denominator', '范围分母')) + '</dt><dd>' +
      esc(String(denominator.expected_captures)) + '</dd></div>' +
      '<div><dt>' + esc(copy('Accounted captures', '已核算记录')) + '</dt><dd>' +
      esc(String(denominator.accounted_captures)) + '</dd></div>';
    if (counts) {
      rows += Object.keys(counts).sort().map(function (reason) {
        return '<div><dt>' + esc(COVERAGE_LABELS[reason] ? copy(COVERAGE_LABELS[reason][0], COVERAGE_LABELS[reason][1]) : copy('Other disclosed exclusion', '其他已披露排除原因')) + '</dt><dd>' + esc(String(counts[reason])) + '</dd></div>';
      }).join('');
    }
    var note = reconcile.ok
      ? copy('These are exact saved captures within one disclosed scope — not a complete market history and not independent trials.',
             '这些是同一披露范围内的确切保存记录——不是完整市场历史，也不代表独立试验次数。')
      : copy('Coverage accounting did not reconcile; treat these counts as unavailable rather than approximate.',
             '覆盖核算未能对账；这些计数应视为不可用，而非近似值。');
    return '<dl class="mmr-coverage">' + rows + '</dl><p class="mmr-note' + (reconcile.ok ? '' : ' is-inconsistent') + '">' + esc(note) + '</p>';
  }

  function methodMarkup(compare) {
    var method = compare.methodSpec;
    var fields = Array.isArray(method.fields) && method.fields.length ? method.fields : FIELDS;
    var distances = compare.neighbors.filter(function (neighbor) { return neighbor.distanceQ18 !== null; });
    return '<dl class="mmr-coverage">' +
      '<div><dt>' + esc(copy('Registered method', '注册方法')) + '</dt><dd><code>' + esc(method.methodSpecId) + '</code></dd></div>' +
      '<div><dt>' + esc(copy('Compared fields', '比较字段')) + '</dt><dd>' + esc(fields.map(fieldLabel).join(copy(', ', '、'))) + '</dd></div>' +
      (method.exclusionDays === null ? '' : '<div><dt>' + esc(copy('Calendar-day exclusion', '自然日排除')) + '</dt><dd>' + esc(String(method.exclusionDays)) + '</dd></div>') +
      '</dl><p class="mmr-note">' + esc(copy(
        'Equal fixed rules over five house fields; two numeric score differences and three categorical equal/mismatch checks. No fitted probabilities, no trading verdict, and the returned count is a similarity selection — not independent trials.',
        '五项内部字段按固定等权规则比较：两项数值评分差值与三项类别一致/不一致检查。无拟合概率、无交易结论；返回数量是相似度选择，不是独立试验次数。')) + '</p>' +
      (distances.length ? '<h3>' + esc(copy('Exact case distances', '案例的确切距离')) + '</h3><p class="mmr-note">' +
        esc(copy('Smaller distances mean closer readings under this fixed comparison rule. They are not probabilities.',
                 '按此固定比较规则，距离越小表示解读越接近。距离不是概率。')) + '</p><dl class="mmr-coverage">' +
        distances.map(function (neighbor) {
          return '<div><dt>' + esc(caseClock(neighbor)) + '</dt><dd><code>' +
            esc(String(neighbor.distanceQ18)) + '</code></dd></div>';
        }).join('') + '</dl>' : '');
  }

  function caseClock(neighbor) {
    var entry = findEntry(neighbor.contextId);
    return neighbor.sourceCard ? clockLabel(neighbor.sourceCard.eventTime) : (entry ? clockLabel(entry.eventTime) : neighbor.contextId);
  }

  function caseMarkup(neighbor, index) {
    var when = caseClock(neighbor);
    var rows = neighbor.differences && neighbor.differences.length
      ? neighbor.differences
      : (neighbor.state && state.committed.data.selectedState ? differenceRows(state.committed.data.selectedState, neighbor.state) : null);
    var summary = rows ? summarizeDifferences(rows) : esc(copy('Difference detail unavailable', '差异细节暂不可用'));
    return '<article class="mmr-case" data-mmr-context="' + esc(neighbor.contextId) + '">' +
      '<div class="mmr-case-head"><h3>' + esc(when) + '</h3><span>' + esc(copy('Saved house output', '已保存的内部输出')) + '</span></div>' +
      '<p class="mmr-case-diff">' + summary + '</p>' +
      '<button type="button" class="gbtn gbtn-quiet mmr-action" data-mmr-action="inspect" data-mmr-context="' + esc(neighbor.contextId) + '">' +
      esc(copy('Inspect source', '核对来源')) + '</button></article>';
  }

  function renderCompare() {
    ui.sourcePanel.hidden = false;
    var committed = state.committed;
    var compare = committed.data;
    var entry = state.selected;
    var selectedState = null;
    if (entry && state.sourceCase && state.sourceCase.contextId === entry.contextId && state.sourceCase.data) {
      selectedState = state.sourceCase.data.state;
    }
    selectedState = compare.selectedState;
    var returned = compare.neighbors.length;
    var headline = copy('{returned} comparable saved cases', '{returned} 个可比的已保存案例').replace('{returned}', String(returned));
    var body = '<div class="mmr-result-head"><div><p class="mmr-eyebrow">' + esc(copy(MODE_LABELS[state.mode][0], MODE_LABELS[state.mode][1])) + '</p>' +
      '<h2>' + esc(headline) + '</h2></div>' +
      '</div>' +
      '<p class="mmr-lead">' + esc(copy('Compare the house readings; a match does not establish what comes next.',
        '比较内部解读；相似案例不代表未来结果。')) + '</p>' + staleNoticeIfNeeded({ intent: committed.intent });
    if (!state.catalog) {
      body += '<p class="mmr-note">' + actionLink('Browse available captures', '浏览可用记录', 'focus-capture-select') + '</p>';
    }
    if (compare.status === 'VALID_EMPTY' || compare.status === 'ABSTAINED' || !returned) {
      body += banner('valid_empty',
        'No comparable saved cases', '暂无可比的已保存案例',
        'Saved records were excluded or lacked the required fields. Open coverage to see why.',
        '保存记录被规则排除或缺少必要字段；打开覆盖详情查看原因。');
    } else if (compare.neighbors.length < COMPARE_LIMIT) {
      body += banner('insufficient_population',
        'Too few saved cases', '保存案例不足',
        'Fewer eligible cases exist than requested. Inspect the returned cases and missing coverage.',
        '符合条件的案例少于请求数量；请核对已有案例与缺失覆盖。') +
        compare.neighbors.map(function (neighbor, index) { return caseMarkup(neighbor, index); }).join('');
    } else {
      body += compare.neighbors.map(function (neighbor, index) { return caseMarkup(neighbor, index); }).join('');
    }
    body += '<details class="mmr-disc"><summary>' + esc(copy('Coverage and exclusions — see what was left out', '覆盖与排除 — 查看未纳入的记录')) + '</summary>' + coverageMarkup(compare) + '</details>' +
      '<details class="mmr-disc"><summary>' + esc(copy('Comparison method & distances', '比较方法与距离')) + '</summary>' + methodMarkup(compare) + '</details>' +
      outcomeBlock();
    ui.resultBody.innerHTML = body;

    if (state.sourceCase && state.sourceCase.data) {
      renderSourcePanel();
    } else {
      ui.sourceBody.innerHTML = '<p class="mmr-note">' + esc(copy(
        'Choose “Inspect source” on a case to read its exact saved values, citations and byte spans.',
        '选择案例上的“核对来源”，查看其确切保存数值、引用与字节区间。')) + '</p>';
    }
  }

  function renderCorrectionNotice() {
    var existing = ui.resultBody.querySelector('[data-mmr-state="corrected_version"]');
    var notice = correctionNoticeIfNeeded();
    if (notice && !existing) ui.resultBody.insertAdjacentHTML('afterbegin', notice);
  }

  function renderSourcePanel() {
    var source = state.sourceCase;
    if (!source || !source.data) return;
    ui.sourcePanel.hidden = false;
    var playback = source.data;
    var fieldNote = state.sourceField
      ? '<p class="mmr-note">' + esc(copy('Focused field: ', '聚焦字段：')) + '<strong>' + esc(fieldLabel(state.sourceField)) + '</strong></p>'
      : '';
    ui.sourceBody.innerHTML = fieldNote +
      fiveFieldList(playback.state, true) +
      '<details class="mmr-disc"' + (state.sourceField ? ' open' : '') + '><summary>' +
      esc(copy('Exact source reference — verify the quote', '确切来源引用 — 核对原文')) + '</summary>' +
      citationsMarkup(playback) +
      '<p class="mmr-note"><code>' + esc(JSON.stringify({
        context_id: playback.contextId,
        event_time: playback.eventTime,
        as_known_at: playback.asKnownAt
      })) + '</code></p></details>' +
      outcomeBlock();
    if (state.sourceField) {
      var target = ui.sourceBody.querySelector('[data-mmr-field="' + esc(state.sourceField) + '"]');
      /* fiveFieldList does not tag fields; the details region is the focus target. */
      var details = ui.sourceBody.querySelector('details.mmr-disc');
      (target || details || ui.sourcePanel).setAttribute('tabindex', '-1');
      (target || details || ui.sourcePanel).focus({ preventScroll: false });
    }
  }

  function openSourcePanel(options) {
    var opts = options || {};
    if (opts.returnFocus !== false && document.activeElement) state.lastFocus = document.activeElement;
    ui.sourcePanel.hidden = false;
    ui.sourcePanel.setAttribute('data-mmr-open', 'true');
    ui.sourceHeading.classList.add('is-open');
    ui.sourcePanel.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }
  function closeSourcePanel() {
    ui.sourcePanel.hidden = true;
    ui.sourcePanel.removeAttribute('data-mmr-open');
    ui.sourceHeading.classList.remove('is-open');
    if (state.lastFocus && typeof state.lastFocus.focus === 'function') {
      state.lastFocus.focus();
      state.lastFocus = null;
    }
  }

  /* ------------------------------------------------------------------ *
   * Intent lifecycle: any new mode/query/cutoff/pin intent first clears
   * old retained evidence and bumps the epoch; only exact epoch+binding
   * matches can commit afterwards.
   * ------------------------------------------------------------------ */
  function currentIntent() {
    if (state.intent) return Object.assign({}, state.intent, { mode: state.mode, outcomeLens: state.outcomeLens });
    return { mode: state.mode };
  }
  state.currentIntent = currentIntent;

  function runCurrentIntent() {
    if (state.referenceInvalid) {
      var restored = parseUrlIntent(location.search);
      if (!restored.ok) return renderTypedUnavailable('missing_exact_capture', restored.reason);
      return applyIntent(restored.intent, {persist:false});
    }
    var intent = currentIntent();
    if (!state.catalog) {
      /* A manual retry reissues the pinned reference itself — never a catalog
       * read followed by re-derived defaults. */
      if (completeCompareRef(intent)) return runCompare(intent);
      return loadCatalog(intent);
    }
    if (!state.selected) return renderCatalogPrompt();
    if (state.mode === 'saved') return runSaved(intent);
    return runCompare(intent);
  }

  function setMode(mode, options) {
    var opts = options || {};
    if (MODES.indexOf(mode) === -1) return;
    var changed = mode !== state.mode;
    state.mode = mode;
    renderModeButtons();
    renderCutoffControl();
    if (!state.catalog) {
      if (!changed) { writeUrlIntent(publishableIntent(currentIntent())); return; }
      /* No catalog is held, so no per-mode method can be derived here and the
       * previous mode's registered method may never be reused: the pinned
       * reference cannot be dispatched from this mode. Say so plainly and
       * offer the explicit browse instead of guessing a method. */
      beginIntent();
      state.selected = null;
      state.sourceContext = null; state.sourceField = null;
      ui.sourceBody.innerHTML = ''; closeSourcePanel();
      ui.originalClock.hidden = true; ui.originalClock.innerHTML = '';
      if (state.intent) state.intent.method = null;
      renderCatalogDependentControls();
      writeUrlIntent(publishableIntent(currentIntent()));
      renderCatalogNotLoaded();
      return;
    }
    if (!state.selected) { writeUrlIntent(publishableIntent(currentIntent())); renderCatalogPrompt(); return; }
    if (changed || !state.committed) {
      state.intent.method = defaultMethodId(mode);
      state.intent.cutoff = defaultCutoffFor(state.selected);
      writeUrlIntent(publishableIntent(currentIntent()));
      var intent = currentIntent();
      if (mode === 'saved') runSaved(intent);
      else runCompare(intent);
    } else if (opts.persist) {
      writeUrlIntent(publishableIntent(currentIntent()));
    }
  }

  function applyIntent(intent, options) {
    state.intent = Object.assign({}, intent, {mode: intent.mode || state.mode});
    var opts = options || {};
    if (intent.mode && intent.mode !== state.mode) {
      state.mode = intent.mode;
      renderModeButtons();
    }
    state.outcomeLens = intent.outcomeLens || null;
    state.sourceField = intent.sourceField || null;
    state.sourceContext = intent.sourceContext || null;
    if (!state.catalog) {
      /* A complete pinned reference opens through the retained endpoint
       * itself. The catalog is neither awaited nor speculatively requested,
       * and its absence is never read as evidence about the reference. */
      if (completeCompareRef(state.intent)) return runExactReference(state.intent);
      return loadCatalog(state.intent);
    }
    if ((intent.gen && state.catalog.generation.generationId !== intent.gen)
        || (intent.genSha && state.catalog.generation.generationSha256 !== intent.genSha)
        || (intent.context && !state.catalog.entries.some(function (entry) { return entry.contextId === intent.context && entry.catalogOffset === String(intent.catalogOffset || '0'); }))) {
      return loadCatalog(intent);
    }
    var mismatch = deepLinkMismatch(intent, state.catalog);
    if (mismatch) { beginIntent(); return renderTypedUnavailable('deep_link_mismatch', mismatch); }
    if (intent.context) {
      var entry = findEntry(intent.context);
      if (!entry) return renderTypedUnavailable('missing_exact_capture', 'context_not_in_disclosed_catalog');
      selectEntry(entry, intent);
      return;
    }
    if (opts.persist !== false) writeUrlIntent(publishableIntent(currentIntent()));
    renderCatalogPrompt();
  }

  /* ------------------------------------------------------------------ *
   * Events. Keyboard tabs follow the WAI-ARIA tabs pattern; all actions
   * are explicit user selections. No timers, no polling loops.
   * ------------------------------------------------------------------ */
  function focusTab(mode) {
    var button = ui.tabs[mode];
    if (!button) return;
    button.focus();
    setMode(mode, { persist: true });
  }
  function tabKeydown(event) {
    var key = event.key;
    if (key !== 'ArrowLeft' && key !== 'ArrowRight' && key !== 'Home' && key !== 'End') return;
    event.preventDefault();
    var index = MODES.indexOf(state.mode);
    if (key === 'Home') return focusTab(MODES[0]);
    if (key === 'End') return focusTab(MODES[MODES.length - 1]);
    var direction = key === 'ArrowRight' ? 1 : -1;
    focusTab(MODES[(index + direction + MODES.length) % MODES.length]);
  }

  function authRedact() {
    beginIntent();
    if (state.sourceAbort) { try { state.sourceAbort.abort(); } catch (error) { /* already gone */ } }
    state.sourceAbort = null;
    state.authEpoch += 1;
    state.authBlocked = true;
    state.catalog = null;
    state.catalogPages = 0;
    state.selected = null;
    state.committed = null;
    state.sourceCase = null;
    renderCatalogDependentControls();
    state.notice = { kind: 'signed_out', signinHref: retainedSigninHref() };
    renderNotice();
    ui.sourceBody.innerHTML = '';
    ui.originalClock.hidden = true; ui.originalClock.innerHTML = '';
    closeSourcePanel();
  }

  function renderSignedOutNotice(notice) {
    ui.status.setAttribute('data-mmr-state', 'error');
    ui.status.textContent = copy('Sign in required', '需要登录');
    ui.resultBody.innerHTML = banner('auth_required',
      'Sign in to open saved evidence', '登录以查看已保存依据',
      'Authenticated saved evidence, counts and sources are cleared when you sign out.',
      '退出登录后，已保存依据、计数与来源将被清除。',
      '<a class="gbtn gbtn-quiet mmr-action" href="' + esc(noticeSigninHref(notice)) + '" data-mmr-action="signin">' + esc(copy('Sign in', '登录')) + ' →</a>');
  }

  function noticeSigninHref(notice) {
    /* The owner target builder validates the current reference without writing
     * the OAuth capsule. Persisting the real sign-in transition remains separate. */
    if (!window.MarketMemoryIntent || typeof window.MarketMemoryIntent.target !== 'function') return notice.signinHref;
    var target = window.MarketMemoryIntent.target({ language: isZh() ? 'zh' : 'en' });
    if (!target.ok) return '#mmr-status';
    var params = new URLSearchParams();
    params.set('signin', '1'); params.set('ret', target.target);
    return '/?' + params.toString();
  }

  function retainedSigninHref() {
    if (!window.MarketMemoryIntent) return '#mmr-status';
    var result = window.MarketMemoryIntent.signinHref();
    return result.ok ? result.href : '#mmr-status';
  }
  function oauthStorageWarning(zh) {
    if (!window.MarketMemoryIntent || window.MarketMemoryIntent.oauthPreservation().ok) return '';
    return zh ? ' 此标签页无法在 Google 登录后保留当前选择。' : ' This tab cannot preserve your selection through Google sign-in.';
  }
  function onActionClick(event) {
    var target = event.target && event.target.closest ? event.target.closest('[data-mmr-action]') : null;
    if (!target || !ui.root.contains(target)) return;
    var action = target.getAttribute('data-mmr-action');
    var contextId = target.getAttribute('data-mmr-context');
    if (action === 'signin') {
      if (event.defaultPrevented || event.button > 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      if (window.MarketMemoryIntent && !window.MarketMemoryIntent.syncReturn().ok) { event.preventDefault(); return; }
      if (window.MDXAuth && typeof window.MDXAuth.open === 'function') {
        event.preventDefault();
        window.MDXAuth.open('signin');
      }
      return;
    }
    if (action === 'retry') { runCurrentIntent(); return; }
    if (action === 'focus-capture-select') {
      if (!state.catalog) {
        state.referenceInvalid = false; state.sourceContext = null; state.sourceField = null; state.outcomeLens = null;
        var browseIntent = { mode: state.mode };
        if (!writeUrlIntent(browseIntent)) return;
        applyIntent(browseIntent, {persist:false});
      }
      ui.captureSelect.removeAttribute('disabled');
      ui.captureSelect.focus();
      ui.captureSelect.scrollIntoView({ block: 'center', behavior: 'smooth' });
      return;
    }
    if (action === 'inspect' && contextId) {
      openSourcePanel({ returnFocus: true });
      var field = state.sourceField;
      inspectCaseSource(contextId, field);
      return;
    }
    if (action === 'open-newer' && contextId) {
      var entry = findEntry(contextId);
      if (entry) selectEntry(entry, {});
      return;
    }
  }

  function onPopState() {
    var parsed = parseUrlIntent(location.search);
    if (!parsed.ok) {
      state.intent = null;
      state.epoch += 1;
      renderTypedUnavailable('missing_exact_capture', parsed.reason);
      return;
    }
    var intent = parsed.intent;
    if (Object.keys(intent).length === 0 && state.selected) {
      return; /* incumbent-only navigation; retained intent unchanged */
    }
    applyIntent(intent, { persist: false });
  }

  function boot() {
    ui.root = document.getElementById(REGION_ID);
    if (!ui.root) return;
    ui.status = ui.root.querySelector('#mmr-status');
    ui.tabs = {
      saved: ui.root.querySelector('#mmr-tab-saved'),
      historical: ui.root.querySelector('#mmr-tab-historical'),
      current: ui.root.querySelector('#mmr-tab-current')
    };
    ui.captureSelect = ui.root.querySelector('#mmr-capture');
    ui.cutoffSelect = ui.root.querySelector('#mmr-cutoff');
    ui.cutoffNote = ui.root.querySelector('#mmr-cutoff-note');
    ui.primaryButton = ui.root.querySelector('#mmr-primary');
    ui.scopeLine = ui.root.querySelector('#mmr-scope');
    ui.originalClock = ui.root.querySelector('#mmr-original-clock');
    ui.modeNote = ui.root.querySelector('#mmr-mode-note');
    ui.resultBody = ui.root.querySelector('#mmr-results');
    ui.sourcePanel = ui.root.querySelector('#mmr-source-panel');
    ui.sourceBody = ui.root.querySelector('#mmr-source-body');
    ui.sourceHeading = ui.root.querySelector('#mmr-source-heading');
    ui.loadMoreButton = ui.root.querySelector('#mmr-load-more');
    ui.tablist = ui.root.querySelector('#mmr-tablist');
    if (!ui.status || !ui.resultBody) return;

    MODES.forEach(function (mode) {
      var button = ui.tabs[mode];
      if (!button) return;
      button.addEventListener('click', function () { setMode(mode, { persist: true }); });
      button.addEventListener('keydown', tabKeydown);
    });
    ui.captureSelect.addEventListener('change', function () {
      var entry = findEntry(ui.captureSelect.value);
      if (!entry) return renderTypedUnavailable('missing_exact_capture', 'select_value_not_in_catalog');
      selectEntry(entry, {});
    });
    ui.cutoffSelect.addEventListener('change', function () {
      if (!state.selected) return;
      var cutoff = ui.cutoffSelect.value;
      if (!isUtc(cutoff)) return;
      if (state.mode === 'saved') { selectEntry(state.selected, { cutoff: cutoff }); return; }
      selectEntry(state.selected, { cutoff: cutoff, method: defaultMethodId(state.mode) });
    });
    ui.primaryButton.addEventListener('click', function () {
      if (!state.selected) {
        /* With no catalog held, a pinned reference is still actionable: the
         * primary action routes it instead of focusing a disabled picker. */
        if (!state.catalog && completeCompareRef(currentIntent())) return runCurrentIntent();
        ui.captureSelect.focus();
        return;
      }
      runCurrentIntent();
    });
    ui.loadMoreButton.addEventListener('click', function () { loadMoreCatalog(); });
    ui.root.addEventListener('click', onActionClick);
    window.addEventListener('popstate', onPopState);
    document.addEventListener('langchange', function () {
      /* Translate the current presentation without replaying its transition:
       * no refetch, epoch change, abort, selection change or private-data revival. */
      if (state.committed) renderCommitted();
      else renderNotice();
      renderCatalogDependentControls();
      renderModeButtons();
      if (state.sourceCase) renderSourcePanel();
    });
    if (window.MDXAuth && typeof window.MDXAuth.onChange === 'function') {
      window.MDXAuth.onChange(function (user) {
        if (!user) return authRedact();
        if (state.authBlocked) {
          state.authBlocked = false;
          var restored = parseUrlIntent(location.search);
          if (!restored.ok) return renderTypedUnavailable('missing_exact_capture', restored.reason);
          applyIntent(restored.intent, { persist: false });
        }
      });
    }

    state.booted = true;
    if (window.MarketMemoryIntent && !window.MarketMemoryIntent.resumeStatus().ok) {
      renderTypedUnavailable('oauth_return_unavailable', 'oauth_return_selection_unavailable');
      return;
    }
    var parsed = parseUrlIntent(location.search);
    if (!parsed.ok) {
      renderTypedUnavailable('missing_exact_capture', parsed.reason);
      return;
    }
    applyIntent(parsed.intent, { persist: false });
    /* Name the picker's real state once the requested mode is known: an
     * unloaded list is a loading fact, not a sign-in requirement. */
    renderCatalogDependentControls();
  }

  /* Bounded test hook: pure helpers only, registered by a test runner
   * before this file is evaluated. No DOM, fetch or credential surface. */
  if (typeof globalThis !== 'undefined' && typeof globalThis.__MM_RETAINED_TEST_HOOK__ === 'function') {
    globalThis.__MM_RETAINED_TEST_HOOK__({
      ContractError: ContractError,
      normalizeCatalog: normalizeCatalog,
      normalizeEntry: normalizeEntry,
      normalizeCompare: normalizeCompare,
      normalizePlayback: normalizePlayback,
      bindingMismatch: bindingMismatch,
      deepLinkMismatch: deepLinkMismatch,
      reconcileCoverage: reconcileCoverage,
      differenceRows: differenceRows,
      summarizeDifferences: summarizeDifferences,
      parseUrlIntent: parseUrlIntent,
      completeCompareRef: completeCompareRef,
      commitGate: commitGate,
      isUtc: isUtc,
      formatUtc: formatUtc,
      displayValue: displayValue,
      stateKindFor: stateKindFor
    });
  }

  if (typeof document === 'undefined') return; /* non-browser evaluation (tests) */
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
}());
