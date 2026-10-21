/* Closed, detached outcome projection. Validation never grants source access. */
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.MarketMemoryOutcomeContract = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var SHA = /^[0-9a-f]{64}$/;
  var Q18 = /^(0|[1-9][0-9]{0,399})\.[0-9]{18}$/;
  function fail(code) { throw new Error('outcome_contract:' + code); }
  function closed(value, names, code) {
    if (!value || typeof value !== 'object' || Array.isArray(value)
        || (Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null)) fail(code);
    var keys = Reflect.ownKeys(value);
    if (keys.length !== names.length || keys.some(function (key) {
      var descriptor = Object.getOwnPropertyDescriptor(value, key);
      return names.indexOf(key) < 0 || !descriptor || !Object.prototype.hasOwnProperty.call(descriptor, 'value');
    })) fail(code);
    return value;
  }
  function sha(value) { if (typeof value !== 'string' || !SHA.test(value)) fail('digest'); return value; }
  function id(value, prefix) {
    if (typeof value !== 'string' || value.slice(0, prefix.length) !== prefix) fail('identity');
    sha(value.slice(prefix.length)); return value;
  }
  function q18(value, positive) {
    if (typeof value !== 'string' || !Q18.test(value)
        || (positive && /^0\.0{18}$/.test(value))) fail('q18');
    return value;
  }
  function clock(value) {
    if (typeof value !== 'string') fail('clock');
    var m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?Z$/.exec(value);
    if (!m) fail('clock');
    var year = Number(m[1]), month = Number(m[2]), day = Number(m[3]);
    var days = [31, (year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)) ? 29 : 28,
      31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if (year < 1 || month < 1 || month > 12 || day < 1 || day > days[month - 1]
        || Number(m[4]) > 23 || Number(m[5]) > 59 || Number(m[6]) > 59) fail('clock');
    return value.slice(0, 19) + '.' + (m[7] || '').padEnd(6, '0');
  }
  function freeze(value) {
    if (value && typeof value === 'object') {
      Object.keys(value).forEach(function (key) { freeze(value[key]); });
      Object.freeze(value);
    }
    return value;
  }
  function dense(array, code) {
    if (!Array.isArray(array) || array.length > 8 || Reflect.ownKeys(array).length !== array.length + 1) fail(code);
    for (var i = 0; i < array.length; i += 1) {
      var descriptor = Object.getOwnPropertyDescriptor(array, String(i));
      if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor, 'value')) fail(code);
    }
    return array;
  }
  function neighbor(value) {
    closed(value, ['contextId', 'captureId', 'packetSha256', 'comparisonId', 'distanceQ18'], 'neighbor');
    return { contextId: id(value.contextId, 'mmctx_'), captureId: id(value.captureId, 'mmcapture_'),
      packetSha256: sha(value.packetSha256), comparisonId: id(value.comparisonId, 'mmepisodecomparison_'),
      distanceQ18: q18(value.distanceQ18, false) };
  }
  function observation(value, cutoff) {
    closed(value, ['id', 'sha256', 'revision_number', 'previous_observation_id', 'clocks'], 'observation');
    var identity = id(value.id, 'mmcontextualobservation_');
    if (!Number.isSafeInteger(value.revision_number) || value.revision_number < 1) fail('revision');
    var previous = value.previous_observation_id;
    if (value.revision_number === 1) {
      if (previous !== null) fail('revision');
    } else if (id(previous, 'mmcontextualobservation_') === identity) fail('revision');
    closed(value.clocks, ['observed_at', 'published_at', 'recorded_at'], 'observation_clocks');
    var observed = clock(value.clocks.observed_at), published = clock(value.clocks.published_at);
    var recorded = clock(value.clocks.recorded_at);
    if (observed > published || published > recorded || recorded > cutoff) fail('observation_clock_order');
    return { id: identity, sha256: sha(value.sha256), revisionNumber: value.revision_number,
      previousObservationId: previous, clocks: { observedAt: value.clocks.observed_at,
        publishedAt: value.clocks.published_at, recordedAt: value.clocks.recorded_at } };
  }
  function normalizeOutcomeAttachment(raw, expected) {
    closed(expected, ['retrievalId', 'selectionSha256', 'queryCutoff', 'outcomeCutoff', 'lens',
      'definitionSha256', 'neighbors'], 'expected');
    var retrievalId = id(expected.retrievalId, 'mmretainedretrieval_');
    sha(expected.selectionSha256); sha(expected.definitionSha256);
    var queryClock = clock(expected.queryCutoff), outcomeClock = clock(expected.outcomeCutoff);
    if (expected.lens !== 'then_known' && expected.lens !== 'later_observed') fail('lens');
    if ((expected.lens === 'then_known' && queryClock !== outcomeClock)
        || (expected.lens === 'later_observed' && outcomeClock < queryClock)) fail('lens_cutoff');
    var selected = dense(expected.neighbors, 'neighbors').map(neighbor);
    var contexts = new Set();
    selected.forEach(function (item) {
      if (contexts.has(item.contextId)) fail('duplicate_context'); contexts.add(item.contextId);
    });
    closed(raw, ['schema', 'retrieval_id', 'selection_sha256', 'query_cutoff', 'outcome_cutoff', 'lens',
      'definition_sha256', 'metric', 'economic_return', 'corporate_action_adjusted',
      'RTH_close_authenticated', 'effective_n', 'rows'], 'root');
    if (raw.schema !== 'market_memory.outcome_inspection.v1' || raw.metric !== 'archived_close_ratio'
        || raw.economic_return !== false || raw.corporate_action_adjusted !== false
        || raw.RTH_close_authenticated !== false || raw.effective_n !== 'not_estimated') fail('semantics');
    [['retrieval_id', 'retrievalId'], ['selection_sha256', 'selectionSha256'], ['query_cutoff', 'queryCutoff'],
      ['outcome_cutoff', 'outcomeCutoff'], ['lens', 'lens'], ['definition_sha256', 'definitionSha256']]
      .forEach(function (pair) { if (raw[pair[0]] !== expected[pair[1]]) fail('binding'); });
    var rows = dense(raw.rows, 'rows');
    if (rows.length !== selected.length) fail('selection_count');
    var result = rows.map(function (row, index) {
      closed(row, ['rank', 'context_id', 'capture_id', 'packet_sha256', 'comparison_id', 'distance_q18',
        'status', 'reason', 'value_q18', 'observation'], 'row');
      if (row.rank !== index + 1) fail('rank');
      var bound = selected[index];
      [['context_id', 'contextId'], ['capture_id', 'captureId'], ['packet_sha256', 'packetSha256'],
        ['comparison_id', 'comparisonId'], ['distance_q18', 'distanceQ18']].forEach(function (pair) {
        if (row[pair[0]] !== bound[pair[1]]) fail('row_binding');
      });
      var value = null, proof = null;
      if (row.status === 'observed') {
        if (row.reason !== 'exact_retained_source_marks') fail('observed_reason');
        value = q18(row.value_q18, true); proof = observation(row.observation, outcomeClock);
      } else {
        if (row.value_q18 !== null || row.observation !== null) fail('hidden_observation');
        var reasons = row.status === 'proof_pending'
          ? ['not_visible_at_query', 'not_visible_at_cutoff', 'source_or_observation_proof_pending']
          : row.status === 'censored'
            ? ['outcome_calendar_unavailable', 'ambiguous_source_observation_clock', 'source_observation_after_registered_deadline'] : [];
        if (reasons.indexOf(row.reason) < 0) fail('status_reason');
      }
      return { rank: row.rank, contextId: bound.contextId, captureId: bound.captureId,
        packetSha256: bound.packetSha256, comparisonId: bound.comparisonId, distanceQ18: bound.distanceQ18,
        status: row.status, reason: row.reason, valueQ18: value, observation: proof };
    });
    return freeze({ schema: raw.schema, retrievalId: retrievalId, selectionSha256: raw.selection_sha256,
      queryCutoff: raw.query_cutoff, outcomeCutoff: raw.outcome_cutoff, lens: raw.lens,
      definitionSha256: raw.definition_sha256, metric: raw.metric, economicReturn: false,
      corporateActionAdjusted: false, RTHCloseAuthenticated: false, effectiveN: raw.effective_n, rows: result });
  }
  function formatRatio(value) {
    q18(value, true);
    var parts = value.split('.');
    var units = BigInt(parts[0] + parts[1].slice(0, 4));
    var remainder = BigInt(parts[1].slice(4));
    if (remainder > 50000000000000n || (remainder === 50000000000000n && units % 2n === 1n)) units += 1n;
    var digits = units.toString().padStart(5, '0');
    return digits.slice(0, -4) + '.' + digits.slice(-4) + '\u00d7';
  }
  return Object.freeze({ normalizeOutcomeAttachment: normalizeOutcomeAttachment, formatRatio: formatRatio });
}));
