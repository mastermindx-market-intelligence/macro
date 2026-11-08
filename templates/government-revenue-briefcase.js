/* government-revenue-briefcase.js
 *
 * A deliberately local-only research briefcase for Government Revenue.  This
 * module never fetches, polls, sends a notification, or talks to an account
 * service.  It is a page integration seam: the page owns rendering and calls
 * these pure-ish state and export helpers after it has hydrated a governed
 * workspace successfully.
 */
(function (root) {
  'use strict';

  var STATE_CONTRACT = 'government_procurement_local_state.v1';
  var EXPORT_CONTRACT = 'government_procurement_export.v1';
  var SAVED_CUT_CONTRACT = 'government_procurement_saved_cut.v1';
  var MAX_SAVED_CUT_RECORDS = 100;
  var MAX_SAVED_CUT_BYTES = 256 * 1024;
  var STORAGE_KEY = 'mastermind.government_revenue.briefcase.v1';
  var FILTER_KEYS = ['mode', 'truth', 'q', 'agency', 'ticker'];
  var VIEW_MODES = ['changes', 'awards', 'opportunities', 'recompetes', 'companies'];
  var TRUTH_FILTERS = ['all', 'official', 'linked', 'defense'];
  var ALERT_TYPES = ['opportunity', 'award_change', 'recompete'];
  var MAX_VIEWS = 24;
  var MAX_ALERTS = 48;
  var MAX_SEEN_IDS = 500;
  var MAX_INBOX = 100;
  var MAX_NAME_LENGTH = 60;
  var MAX_QUERY_LENGTH = 120;
  var MAX_AGENCY_LENGTH = 100;
  var MAX_EVENT_ID_LENGTH = 200;
  var TICKER = /^[A-Z][A-Z0-9.-]{0,9}$/;

  var EVENT_KEYS = [
    'contract', 'event_id', 'record_id', 'version', 'kind', 'state',
    'title_original', 'title_zh', 'translation_status', 'agency', 'change',
    'opportunity', 'recompete', 'award_change', 'dates', 'amounts',
    'primary_date_id', 'primary_amount_id', 'listed_company_impacts',
    'primary_ticker', 'display_priority', 'evidence', 'authority'
  ];
  var AUTHORITY_KEYS = [
    'tier', 'context_only', 'can_rank', 'can_size', 'can_gate',
    'can_originate_signal', 'can_add_candidates', 'can_escalate'
  ];
  var AGENCY_KEYS = ['name', 'id', 'department_name', 'department_id', 'subagency_name', 'subagency_id'];
  var CHANGE_KEYS = [
    'type', 'what_changed_en', 'what_changed_zh', 'summary_origin', 'effective_at',
    'known_at', 'first_seen_at', 'last_seen_at', 'is_correction', 'changed_fields'
  ];
  var CHANGED_FIELD_KEYS = ['field', 'before', 'after', 'semantic', 'source_ref'];
  var OPPORTUNITY_KEYS = [
    'notice_id', 'solicitation_number', 'notice_type', 'notice_stage', 'source_status',
    'current_status', 'current_notice_stage', 'current_revision', 'active', 'current_state',
    'current_state_verified', 'observation_horizon_at', 'observation_age_minutes',
    'observation_basis', 'current_state_reason', 'posted_at', 'updated_at',
    'response_deadline', 'archive_at', 'naics_codes', 'psc_codes', 'set_aside_code',
    'set_aside_label', 'description_excerpt', 'place_of_performance', 'sam_url'
  ];
  var RECOMPETE_KEYS = [
    'case_type', 'generated_award_id', 'piid', 'incumbent_recipient_name',
    'incumbent_uei', 'current_end_date', 'potential_end_date', 'days_to_current_end',
    'total_obligated', 'current_award_amount', 'potential_award_amount',
    'matched_notice_id', 'basis_code', 'watch_entered_at'
  ];
  var AWARD_CHANGE_KEYS = [
    'award_key', 'generated_award_id', 'piid', 'recipient_name', 'event_type',
    'secondary_types', 'source_rail', 'source_identity', 'observation_kind',
    'coverage_scope', 'is_late_discovery', 'action_id', 'prior_source_identity',
    'text_annotations'
  ];
  var DATE_KEYS = ['id', 'value', 'known_at', 'label_code', 'semantic', 'source_ref'];
  var AMOUNT_KEYS = ['id', 'value', 'currency', 'known_at', 'as_of', 'label_code', 'semantic', 'source_ref', 'is_lower_bound'];
  var IMPACT_KEYS = [
    'ticker', 'company_name', 'relation_semantic', 'confidence', 'stance',
    'why_it_matters_en', 'why_it_matters_zh', 'watch_next_en', 'watch_next_zh',
    'label_limit', 'materiality', 'cross_desk_links'
  ];
  var PRIORITY_KEYS = [
    'score', 'new_information', 'company_materiality', 'evidence_quality',
    'formula_version', 'is_investment_rank', 'tie_breakers'
  ];
  var EVIDENCE_KEYS = ['source_class', 'mapping_class', 'receipts', 'derivations', 'conflicts', 'limitations'];
  var RECEIPT_KEYS = ['publisher', 'record_id', 'url', 'observed_at', 'content_sha256'];
  var DERIVATION_KEYS = ['code', 'label', 'description', 'inputs'];
  var CONFLICT_KEYS = ['code', 'field', 'description'];

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

  function pick(source, keys) {
    var out = {};
    if (!object(source)) return out;
    keys.forEach(function (key) {
      if (Object.prototype.hasOwnProperty.call(source, key)) out[key] = source[key];
    });
    return out;
  }

  function safeUrl(value) {
    try {
      var parsed = new URL(String(value || ''));
      return parsed.protocol === 'https:' ? parsed.href : null;
    } catch (error) {
      return null;
    }
  }

  function safeList(values, limit, mapper) {
    var out = [];
    array(values).forEach(function (value) {
      if (out.length >= limit) return;
      var next = mapper(value);
      if (next != null) out.push(next);
    });
    return out;
  }

  function sanitizeScalar(value) {
    if (value == null || typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      return value;
    }
    return null;
  }

  function publicAuthority(value) {
    var out = pick(value, AUTHORITY_KEYS);
    AUTHORITY_KEYS.forEach(function (key) {
      if (!Object.prototype.hasOwnProperty.call(out, key)) return;
      if (key === 'tier') out[key] = text(out[key], 30);
      else out[key] = out[key] === true;
    });
    return out;
  }

  function publicChange(value) {
    var out = pick(value, CHANGE_KEYS);
    out.changed_fields = safeList(out.changed_fields, 80, function (field) {
      var next = pick(field, CHANGED_FIELD_KEYS);
      next.field = text(next.field, 120);
      next.semantic = text(next.semantic, 120);
      next.source_ref = safeUrl(next.source_ref);
      next.before = sanitizeScalar(next.before);
      next.after = sanitizeScalar(next.after);
      return next.field ? next : null;
    });
    return out;
  }

  function publicFacts(values, keys) {
    return safeList(values, 80, function (row) {
      var out = pick(row, keys);
      out.id = text(out.id, 120);
      out.label_code = text(out.label_code, 120);
      out.semantic = text(out.semantic, 120);
      out.source_ref = safeUrl(out.source_ref);
      out.value = sanitizeScalar(out.value);
      out.currency = text(out.currency, 12);
      if (Object.prototype.hasOwnProperty.call(out, 'as_of')) out.as_of = text(out.as_of, 100) || null;
      return out.id ? out : null;
    });
  }

  function publicEvidence(value) {
    var out = pick(value, EVIDENCE_KEYS);
    out.receipts = safeList(out.receipts, 24, function (row) {
      var receipt = pick(row, RECEIPT_KEYS);
      receipt.publisher = text(receipt.publisher, 120);
      receipt.record_id = text(receipt.record_id, 200);
      receipt.url = safeUrl(receipt.url);
      receipt.observed_at = text(receipt.observed_at, 80) || null;
      receipt.content_sha256 = text(receipt.content_sha256, 128) || null;
      return receipt.url ? receipt : null;
    });
    out.derivations = safeList(out.derivations, 24, function (row) {
      return pick(row, DERIVATION_KEYS);
    });
    out.conflicts = safeList(out.conflicts, 24, function (row) {
      return pick(row, CONFLICT_KEYS);
    });
    out.limitations = safeList(out.limitations, 40, function (row) {
      var value = text(row, 1000);
      return value || null;
    });
    return out;
  }

  function publicEvent(value) {
    var source = pick(value, EVENT_KEYS);
    var out = pick(source, [
      'contract', 'event_id', 'record_id', 'version', 'kind', 'state',
      'title_original', 'title_zh', 'translation_status', 'primary_date_id',
      'primary_amount_id', 'primary_ticker'
    ]);
    out.agency = pick(source.agency, AGENCY_KEYS);
    out.change = publicChange(source.change);
    out.opportunity = source.opportunity == null ? null : pick(source.opportunity, OPPORTUNITY_KEYS);
    if (out.opportunity && out.opportunity.sam_url) out.opportunity.sam_url = safeUrl(out.opportunity.sam_url);
    out.recompete = source.recompete == null ? null : pick(source.recompete, RECOMPETE_KEYS);
    out.award_change = source.award_change == null ? null : pick(source.award_change, AWARD_CHANGE_KEYS);
    out.dates = publicFacts(source.dates, DATE_KEYS);
    out.amounts = publicFacts(source.amounts, AMOUNT_KEYS);
    out.listed_company_impacts = safeList(source.listed_company_impacts, 24, function (row) {
      return pick(row, IMPACT_KEYS);
    });
    out.display_priority = pick(source.display_priority, PRIORITY_KEYS);
    out.evidence = publicEvidence(source.evidence);
    out.authority = publicAuthority(source.authority);
    return out;
  }

  function blankState() {
    return { contract: STATE_CONTRACT, saved_views: [], alerts: [], inbox: [] };
  }

  function cleanFilters(raw) {
    raw = object(raw) ? raw : {};
    var mode = text(raw.mode, 30).toLowerCase();
    var truth = text(raw.truth, 30).toLowerCase();
    var ticker = text(raw.ticker, 10).toUpperCase();
    return {
      mode: VIEW_MODES.indexOf(mode) >= 0 ? mode : 'changes',
      truth: TRUTH_FILTERS.indexOf(truth) >= 0 ? truth : 'all',
      q: text(raw.q, MAX_QUERY_LENGTH),
      agency: text(raw.agency, MAX_AGENCY_LENGTH),
      ticker: TICKER.test(ticker) ? ticker : ''
    };
  }

  function stableUniqueIds(values) {
    var seen = {};
    var out = [];
    array(values).forEach(function (value) {
      var id = text(value, MAX_EVENT_ID_LENGTH);
      if (!id || seen[id] || out.length >= MAX_SEEN_IDS) return;
      seen[id] = true;
      out.push(id);
    });
    return out;
  }

  function normalView(value) {
    if (!object(value)) return null;
    var id = text(value.id, 80);
    var name = text(value.name, MAX_NAME_LENGTH);
    if (!id || !name) return null;
    var view = {
      id: id,
      name: name,
      filters: cleanFilters(value.filters),
      created_at: text(value.created_at, 80) || null,
      updated_at: text(value.updated_at, 80) || null
    };
    // Keep unsupported/corrupt cuts opaque. A rename must not erase original bytes
    // or silently turn an unavailable historical cut into today's filters.
    if (Object.prototype.hasOwnProperty.call(value, 'cut')) view.cut = copy(value.cut);
    return view;
  }

  function normalAlert(value, views) {
    if (!object(value)) return null;
    var id = text(value.id, 80);
    var viewId = text(value.view_id, 80);
    var type = text(value.type, 40);
    if (!id || !viewId || ALERT_TYPES.indexOf(type) < 0 || !views[viewId]) return null;
    return {
      id: id,
      view_id: viewId,
      type: type,
      enabled: value.enabled !== false,
      primed: value.primed === true,
      membership_contract: ['page_filter_membership.v1','legacy_event_membership.v1'].indexOf(value.membership_contract)>=0 ? value.membership_contract : null,
      seen_event_ids: stableUniqueIds(value.seen_event_ids),
      created_at: text(value.created_at, 80) || null,
      last_checked_at: text(value.last_checked_at, 80) || null
    };
  }

  function normalInbox(value, alerts) {
    if (!object(value)) return null;
    var id = text(value.id, 100);
    var alertId = text(value.alert_id, 80);
    var eventId = text(value.event_id, MAX_EVENT_ID_LENGTH);
    var type = text(value.type, 40);
    if (!id || !alerts[alertId] || !eventId || ALERT_TYPES.indexOf(type) < 0) return null;
    return {
      id: id,
      alert_id: alertId,
      view_id: text(value.view_id, 80),
      event_id: eventId,
      type: type,
      notification_kind: ['new_observation', 'correction'].indexOf(value.notification_kind) >= 0 ? value.notification_kind : 'unclassified',
      event_contract: /^government_procurement_event\.v[12]$/.test(value.event_contract || '') ? value.event_contract : null,
      record_id: text(value.record_id, MAX_EVENT_ID_LENGTH) || null,
      event_version: Number.isSafeInteger(value.event_version) && value.event_version >= 1 ? value.event_version : null,
      kind: text(value.kind, 40),
      title: text(value.title, 500),
      observed_at: text(value.observed_at, 80) || null,
      workspace_bundle_id: text(value.workspace_bundle_id, 100) || null,
      message: text(value.message, 1000),
      warning: text(value.warning, 1000) || null
    };
  }

  function normalState(value) {
    if (!object(value) || value.contract !== STATE_CONTRACT) return blankState();
    var state = blankState();
    var viewMap = {};
    array(value.saved_views).forEach(function (row) {
      var view = normalView(row);
      if (!view || viewMap[view.id] || state.saved_views.length >= MAX_VIEWS) return;
      viewMap[view.id] = view;
      state.saved_views.push(view);
    });
    var alertMap = {};
    array(value.alerts).forEach(function (row) {
      var alert = normalAlert(row, viewMap);
      if (!alert || alertMap[alert.id] || state.alerts.length >= MAX_ALERTS) return;
      alertMap[alert.id] = alert;
      state.alerts.push(alert);
    });
    array(value.inbox).forEach(function (row) {
      var item = normalInbox(row, alertMap);
      if (item && state.inbox.length < MAX_INBOX) state.inbox.push(item);
    });
    return state;
  }

  function usableWorkspace(workspace) {
    return object(workspace) && /^government_procurement_workspace\.v[12]$/.test(text(workspace.schema_version, 80)) && Array.isArray(workspace.events);
  }

  function isAwardRailReady(workspace) {
    return text((((workspace || {}).freshness || {}).award_events || {}).status, 40).toLowerCase() === 'ok';
  }

  function eventKindForMode(mode, event) {
    if (mode === 'changes') return true;
    if (mode === 'companies') return false;
    if (mode === 'awards') return event.kind === 'award_change';
    if (mode === 'opportunities') return event.kind === 'opportunity';
    if (mode === 'recompetes') return event.kind === 'recompete';
    return false;
  }

  function eventText(event) {
    var agency = object(event.agency) ? event.agency : {};
    var opportunity = object(event.opportunity) ? event.opportunity : {};
    var award = object(event.award_change) ? event.award_change : {};
    return [
      event.event_id, event.record_id, event.title_original, event.title_zh,
      event.primary_ticker, agency.name, agency.department_name, agency.subagency_name,
      opportunity.notice_id, opportunity.solicitation_number,
      award.award_key, award.generated_award_id, award.piid, award.recipient_name,
      (event.change || {}).what_changed_en, (event.change || {}).what_changed_zh
    ].join(' ').toLowerCase();
  }

  function eventAgency(event) {
    var agency = object(event.agency) ? event.agency : {};
    return text(agency.department_name || agency.name, MAX_AGENCY_LENGTH);
  }

  function isDefense(event) {
    var agency = object(event.agency) ? event.agency : {};
    var textValue = [agency.name, agency.department_name, agency.subagency_name].join(' ').toLowerCase();
    if (/defen[cs]e|military|air force|army|navy|space force/.test(textValue)) return true;
    return array((event.change || {}).tags).some(function (tag) { return String(tag).toLowerCase() === 'defense'; });
  }

  function isLinked(event) {
    return array(event.listed_company_impacts).some(function (impact) {
      return object(impact) && text(impact.ticker, 10);
    });
  }

  function eventTruth(event) {
    if (event.kind === 'recompete') return 'derived';
    return text(((event.evidence || {}).source_class), 80) === 'observed_source_revision' ? 'observed' : 'official';
  }

  function matchesFilters(event, filters) {
    var filter = cleanFilters(filters);
    if (!eventKindForMode(filter.mode, event)) return false;
    if (filter.truth === 'official' && eventTruth(event) !== 'official') return false;
    if (filter.truth === 'linked' && !isLinked(event)) return false;
    if (filter.truth === 'defense' && !isDefense(event)) return false;
    if (filter.agency && eventAgency(event) !== filter.agency) return false;
    if (filter.ticker) {
      var tickers = [event.primary_ticker].concat(array(event.listed_company_impacts).map(function (impact) {
        return object(impact) ? impact.ticker : '';
      }));
      if (tickers.indexOf(filter.ticker) < 0) return false;
    }
    return !filter.q || eventText(event).indexOf(filter.q.toLowerCase()) >= 0;
  }

  function matchesAlert(event, alertType) {
    return event.kind === alertType;
  }

  function alertCopy(type, notificationKind) {
    if (notificationKind === 'correction') {
      return {
        message: 'Correction to a previously observed matching record.',
        warning: 'A prior observation was revised; this is not a new award, obligation or issuer revenue.'
      };
    }
    if (type === 'opportunity') {
      return { message: 'New matching procurement opportunity observed locally.', warning: null };
    }
    if (type === 'award_change') {
      return { message: 'New matching receipt-bound award change observed locally.', warning: null };
    }
    return {
      message: 'New matching derived expiry watch observed locally.',
      warning: 'Derived expiry watch — not an official recompete date or solicitation alert.'
    };
  }

  function csvCell(value) {
    var output;
    if (value == null) output = '';
    else if (typeof value === 'object') output = JSON.stringify(value);
    else output = String(value);
    // Spreadsheet applications may ignore leading whitespace/control bytes before
    // evaluating a formula.  Prefix the original value (without trimming it) so
    // the exported cell remains text while preserving its visible/source bytes.
    if (typeof value === 'string' && /^[\s\x00-\x1f]*[=+\-@]/.test(value)) output = "'" + output;
    return '"' + output.replace(/"/g, '""') + '"';
  }

  function firstReceiptUrl(event) {
    var receipts = array(((event.evidence || {}).receipts));
    for (var index = 0; index < receipts.length; index += 1) {
      var url = safeUrl(receipts[index] && receipts[index].url);
      if (url) return url;
    }
    return '';
  }

  function primaryAmountFact(event) {
    var wanted = event.primary_amount_id;
    return array(event.amounts).filter(function (item) { return object(item) && item.id === wanted; })[0] || {};
  }

  function primaryAmount(event) {
    var row = primaryAmountFact(event);
    return typeof row.value === 'number' ? row.value : '';
  }

  function primaryDate(event) {
    var wanted = event.primary_date_id;
    var row = array(event.dates).filter(function (item) { return object(item) && item.id === wanted; })[0];
    return row && row.value != null ? row.value : '';
  }

  function publicWorkspace(workspace) {
    var freshness = object(workspace.freshness) ? workspace.freshness : {};
    var coverage = object(workspace.coverage) ? workspace.coverage : {};
    return {
      bundle_id: text(workspace.bundle_id, 100) || null,
      schema_version: text(workspace.schema_version, 80),
      event_contract: text(workspace.event_contract, 80) || null,
      as_of: text(workspace.as_of, 80) || null,
      known_at: text(workspace.known_at, 80) || null,
      generated_at: text(workspace.generated_at, 80) || null,
      authority: publicAuthority(workspace.authority),
      freshness: {
        status: text(freshness.status, 40) || null,
        award_events: {
          status: text(((freshness.award_events || {}).status), 40) || null,
          availability: text(((freshness.award_events || {}).availability), 80) || null
        }
      },
      coverage: {
        events_visible: typeof coverage.events_visible === 'number' ? coverage.events_visible : null,
        events_available_before_cap: typeof coverage.events_available_before_cap === 'number' ? coverage.events_available_before_cap : null,
        event_cap: typeof coverage.event_cap === 'number' ? coverage.event_cap : null,
        facet_scope: text(coverage.facet_scope, 200) || null
      },
      limitations: safeList(workspace.limitations, 40, function (item) {
        var value = text(item, 1000);
        return value || null;
      })
    };
  }

  function cutError(code) {
    var error = new Error(code);
    error.code = code;
    return error;
  }

  function cutBytes(value) {
    return new TextEncoder().encode(JSON.stringify(value)).length;
  }

  function sourceDay(value) {
    return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
      && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
  }

  function sourceClock(value) {
    return typeof value === 'string' && sourceDay(value.slice(0, 10))
      && /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.test(value)
      && Number.isFinite(Date.parse(value));
  }

  function contextAuthority(value) {
    return object(value) && value.context_only === true && [
      'can_rank', 'can_size', 'can_gate', 'can_originate_signal', 'can_add_candidates', 'can_escalate'
    ].every(function (key) { return value[key] === false; });
  }

  function normalSavedCut(value, filters) {
    if (!object(value) || value.contract !== SAVED_CUT_CONTRACT || cutBytes(value) > MAX_SAVED_CUT_BYTES) return null;
    var payload = value.payload;
    if (!object(payload) || payload.contract !== EXPORT_CONTRACT || !object(payload.workspace)
        || !object(payload.query) || !object(payload.query.filters) || !Array.isArray(payload.records)
        || payload.records.length > MAX_SAVED_CUT_RECORDS || !sourceClock(payload.exported_at)) return null;
    var meta = payload.workspace;
    if (!/^government_procurement_workspace\.v[12]$/.test(meta.schema_version || '')
        || !/^government_procurement_event\.v[12]$/.test(meta.event_contract || '')
        || typeof meta.bundle_id !== 'string' || !/^grw[12]-[a-f0-9]{24}$/.test(meta.bundle_id)
        || !sourceDay(meta.as_of) || !sourceClock(meta.known_at)
        || meta.generated_at != null && !sourceClock(meta.generated_at)) return null;
    if (!contextAuthority(meta.authority)) return null;
    var clean = cleanFilters(filters);
    if (['changes','awards','opportunities','recompetes'].indexOf(clean.mode) < 0
        || JSON.stringify(cleanFilters(payload.query.filters)) !== JSON.stringify(clean)) return null;
    var seen = Object.create(null), valid = true;
    payload.records.forEach(function (record) {
      if (!object(record) || !contextAuthority(record.authority) || record.contract !== meta.event_contract || typeof record.event_id !== 'string'
          || record.event_id !== text(record.event_id, MAX_EVENT_ID_LENGTH) || !record.event_id
          || seen[record.event_id] || !Number.isSafeInteger(record.version) || record.version < 1
          || typeof record.record_id !== 'string' || !record.record_id || !eventKindForMode(clean.mode, record)) valid = false;
      if (object(record)) seen[record.event_id] = true;
    });
    var selected = value.selected_event_id == null || value.selected_event_id === '' ? null : value.selected_event_id;
    if (!valid || selected !== null && (typeof selected !== 'string' || !seen[selected])) return null;
    // Reuse the existing public export allowlist; never retain raw source bodies,
    // private annotations or a copied caller-supplied authority extension.
    return {
      contract: SAVED_CUT_CONTRACT,
      selected_event_id: selected,
      payload: {
        contract: EXPORT_CONTRACT, exported_at: payload.exported_at,
        workspace: publicWorkspace(meta),
        query: {filters: clean, result_scope: 'original visible governed workspace cut'},
        records: payload.records.map(publicEvent)
      }
    };
  }

  root.createGovernmentRevenueBriefcase = function (api) {
    api = object(api) ? api : {};
    var storage = api.storage || null;
    if (!storage) {
      try { storage = root.localStorage; } catch (error) { storage = null; }
    }
    // Authenticated local state is never adopted from the former unowned key.
    var ownerId = text(api.ownerId, 80);
    var storageKey = /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$/.test(ownerId)
      ? STORAGE_KEY + '.user.' + ownerId : null;
    var now = typeof api.now === 'function' ? api.now : function () { return new Date().toISOString(); };
    var membershipContract=api.membershipMode==='legacy'&&!Object.prototype.hasOwnProperty.call(api,'resolveEventIds')?'legacy_event_membership.v1':'page_filter_membership.v1';
    var counter = 0;

    function stamp() {
      var value = now();
      return text(value, 80) || new Date().toISOString();
    }

    function makeId(prefix) {
      counter += 1;
      var random = '';
      try {
        if (root.crypto && root.crypto.getRandomValues) {
          var bytes = new Uint32Array(2);
          root.crypto.getRandomValues(bytes);
          random = bytes[0].toString(36) + bytes[1].toString(36);
        }
      } catch (error) {}
      return prefix + '-' + Date.now().toString(36) + '-' + counter.toString(36) + '-' + (random || Math.random().toString(36).slice(2, 10));
    }

    function read() {
      if (!storageKey || !storage || typeof storage.getItem !== 'function') return blankState();
      try { return normalState(JSON.parse(storage.getItem(storageKey) || 'null')); }
      catch (error) { return blankState(); }
    }

    var state = read();

    function commit() {
      var persisted = false;
      if (storageKey && storage && typeof storage.setItem === 'function') {
        try {
          storage.setItem(storageKey, JSON.stringify(state));
          persisted = true;
        } catch (error) {}
      }
      return persisted;
    }

    function viewById(id) {
      return state.saved_views.filter(function (view) { return view.id === id; })[0] || null;
    }

    function alertById(id) {
      return state.alerts.filter(function (alert) { return alert.id === id; })[0] || null;
    }

    function captureSavedCut(input, filters) {
      var readiness = object(input.readiness) ? input.readiness : {};
      if (readiness.complete !== true || readiness.bundle_matched !== true) throw cutError('workspace_not_ready');
      var workspace = input.workspace;
      if (!usableWorkspace(workspace)) throw cutError('invalid_workspace');
      var clean = cleanFilters(filters);
      if (['changes','awards','opportunities','recompetes'].indexOf(clean.mode) < 0) throw cutError('unsupported_export_mode');
      // Refuse an oversized original window. Never silently truncate it to fit.
      var ids = input.visible_event_ids;
      if (!Array.isArray(ids)) throw cutError('invalid_saved_cut');
      if (ids.length > MAX_SAVED_CUT_RECORDS) throw cutError('saved_cut_too_large');
      // The page owns its displayed filter semantics, including issuer tags and
      // localized search. Preserve that exact ordered membership, not a second predicate.
      var events = Object.create(null), seen = Object.create(null);
      workspace.events.forEach(function (row) {
        if (!object(row) || typeof row.event_id !== 'string' || events[row.event_id]) throw cutError('invalid_saved_cut');
        events[row.event_id] = row;
      });
      var records = ids.map(function (id) {
        if (typeof id !== 'string' || seen[id] || !events[id]) throw cutError('invalid_saved_cut');
        seen[id] = true;
        return publicEvent(events[id]);
      });
      var cut = {contract: SAVED_CUT_CONTRACT, selected_event_id: input.selected_event_id == null || input.selected_event_id === '' ? null : input.selected_event_id,
        payload: {contract: EXPORT_CONTRACT, exported_at: stamp(), workspace: publicWorkspace(workspace),
          query: {filters: clean, result_scope: 'original visible governed workspace cut'}, records: records}};
      if (cutBytes(cut) > MAX_SAVED_CUT_BYTES) throw cutError('saved_cut_too_large');
      cut = normalSavedCut(cut, clean);
      if (!cut) throw cutError('invalid_saved_cut');
      return cut;
    }

    function getSavedCut(id) {
      var view = viewById(text(id, 80));
      if (!view) return {ok: false, reason: 'saved_view_not_found'};
      if (!Object.prototype.hasOwnProperty.call(view, 'cut')) return {ok: false, reason: 'cut_not_captured'};
      var cut = normalSavedCut(view.cut, view.filters);
      return cut ? {ok: true, cut: copy(cut)} : {ok: false, reason: 'invalid_saved_cut'};
    }

    function createView(input) {
      input = object(input) ? input : {};
      if (state.saved_views.length >= MAX_VIEWS) throw new Error('saved view limit reached');
      var name = text(input.name, MAX_NAME_LENGTH);
      if (!name) throw new Error('saved view name is required');
      if (object(input.filters) && input.filters.mode != null && VIEW_MODES.indexOf(input.filters.mode) < 0) throw cutError('unsupported_view_mode');
      var filters = cleanFilters(input.filters);
      var cut = Object.prototype.hasOwnProperty.call(input, 'workspace') ? captureSavedCut(input, filters) : null;
      var view = {
        id: makeId('grv'), name: name, filters: filters,
        created_at: stamp(), updated_at: stamp()
      };
      if (cut) view.cut = cut;
      state.saved_views.push(view);
      return { view: copy(view), persisted: commit() };
    }

    function updateView(id, input) {
      var view = viewById(text(id, 80));
      input = object(input) ? input : {};
      if (!view) throw new Error('saved view not found');
      var name = Object.prototype.hasOwnProperty.call(input, 'name') ? text(input.name, MAX_NAME_LENGTH) : view.name;
      if (!name) throw new Error('saved view name is required');
      if (object(input.filters) && input.filters.mode != null && VIEW_MODES.indexOf(input.filters.mode) < 0) throw cutError('unsupported_view_mode');
      var filters = Object.prototype.hasOwnProperty.call(input, 'filters') ? cleanFilters(input.filters) : view.filters;
      var hasCut = Object.prototype.hasOwnProperty.call(input, 'workspace');
      if (!hasCut && Object.prototype.hasOwnProperty.call(view, 'cut') && JSON.stringify(filters) !== JSON.stringify(view.filters)) {
        throw cutError('saved_cut_required');
      }
      var cut = hasCut ? captureSavedCut(input, filters) : null;
      // Validate every replacement before touching the existing record.
      view.name = name; view.filters = filters;
      if (hasCut) view.cut = cut;
      view.updated_at = stamp();
      return { view: copy(view), persisted: commit() };
    }

    function deleteView(id) {
      id = text(id, 80);
      var before = state.saved_views.length;
      state.saved_views = state.saved_views.filter(function (view) { return view.id !== id; });
      if (state.saved_views.length === before) return { deleted: false, persisted: false };
      var removed = {};
      state.alerts = state.alerts.filter(function (alert) {
        if (alert.view_id !== id) return true;
        removed[alert.id] = true;
        return false;
      });
      state.inbox = state.inbox.filter(function (item) { return !removed[item.alert_id]; });
      return { deleted: true, persisted: commit() };
    }

    function createAlert(input) {
      input = object(input) ? input : {};
      var viewId = text(input.view_id, 80);
      var type = text(input.type, 40);
      if (!viewById(viewId)) throw new Error('saved view not found');
      if (ALERT_TYPES.indexOf(type) < 0) throw new Error('unsupported alert type');
      if (state.alerts.length >= MAX_ALERTS) throw new Error('local alert limit reached');
      var alert = {
        id: makeId('gra'), view_id: viewId, type: type, enabled: input.enabled !== false,
        primed: false, membership_contract: null, seen_event_ids: [], created_at: stamp(), last_checked_at: null
      };
      state.alerts.push(alert);
      return { alert: copy(alert), persisted: commit() };
    }

    function updateAlert(id, input) {
      var alert = alertById(text(id, 80));
      input = object(input) ? input : {};
      if (!alert) throw new Error('local alert not found');
      if (Object.prototype.hasOwnProperty.call(input, 'enabled')) alert.enabled = input.enabled === true;
      return { alert: copy(alert), persisted: commit() };
    }

    function deleteAlert(id) {
      id = text(id, 80);
      var before = state.alerts.length;
      state.alerts = state.alerts.filter(function (alert) { return alert.id !== id; });
      if (state.alerts.length === before) return { deleted: false, persisted: false };
      state.inbox = state.inbox.filter(function (item) { return item.alert_id !== id; });
      return { deleted: true, persisted: commit() };
    }

    function resolvedEvents(workspace,filters) {
      var clean=cleanFilters(filters);
      // Explicit compatibility for non-page callers only. The product always
      // supplies the page resolver; a broken resolver never falls back.
      if (api.membershipMode==='legacy' && !Object.prototype.hasOwnProperty.call(api,'resolveEventIds')) {
        return array(workspace.events).filter(function(event){return object(event)&&matchesFilters(event,clean);});
      }
      if (typeof api.resolveEventIds!=='function') throw cutError('view_membership_unavailable');
      var ids;
      try { ids=api.resolveEventIds(workspace,copy(clean)); }
      catch(error) { throw cutError('view_membership_unavailable'); }
      if (!Array.isArray(ids)||ids.length>MAX_SEEN_IDS) throw cutError('view_membership_unavailable');
      var byId=Object.create(null),seen=Object.create(null);
      array(workspace.events).forEach(function(event){
        if(!object(event)||typeof event.event_id!=='string'||!event.event_id||byId[event.event_id])throw cutError('view_membership_unavailable');
        byId[event.event_id]=event;
      });
      return ids.map(function(id){
        if(typeof id!=='string'||seen[id]||!byId[id]||!eventKindForMode(clean.mode,byId[id]))throw cutError('view_membership_unavailable');
        seen[id]=true;return byId[id];
      });
    }

    function reconcile(workspace, readiness) {
      readiness = object(readiness) ? readiness : {};
      if (!usableWorkspace(workspace)) return { reconciled: false, reason: 'invalid_workspace', alerts: [], withheld_alert_ids: [] };
      if (readiness.complete !== true || readiness.bundle_matched !== true) {
        return { reconciled: false, reason: 'workspace_not_ready', alerts: [], withheld_alert_ids: [] };
      }
      var emitted = [];
      var withheld = [];
      var matches=Object.create(null),rebaselined=[];
      // Resolve every active view before touching any baseline or inbox entry.
      // One unavailable view must not leave an apparently successful partial check.
      try {
        state.alerts.forEach(function(alert){
          if(!alert.enabled||(alert.type==='award_change'&&!isAwardRailReady(workspace)))return;
          var view=viewById(alert.view_id);
          if(!view)throw cutError('view_membership_unavailable');
          matches[alert.id]=resolvedEvents(workspace,view.filters).filter(function(event){return matchesAlert(event,alert.type);});
        });
      } catch(error) {
        return {reconciled:false,reason:'view_membership_unavailable',alerts:[],withheld_alert_ids:[]};
      }
      state.alerts.forEach(function (alert) {
        if (!alert.enabled) return;
        if (alert.type === 'award_change' && !isAwardRailReady(workspace)) {
          withheld.push(alert.id);
          return;
        }
        var rows = matches[alert.id];
        var ids = stableUniqueIds(rows.map(function (event) { return event.event_id; }));
        if (!alert.primed || alert.membership_contract!==membershipContract) {
          // An expanded predicate must not backfill old records as new alerts.
          if(alert.primed)rebaselined.push(alert.id);
          alert.primed = true;
          alert.membership_contract=membershipContract;
          alert.seen_event_ids = stableUniqueIds(ids.concat(alert.seen_event_ids));
          alert.last_checked_at = stamp();
          return;
        }
        var seen = {};
        alert.seen_event_ids.forEach(function (id) { seen[id] = true; });
        rows.forEach(function (event) {
          var eventId = text(event.event_id, MAX_EVENT_ID_LENGTH);
          if (!eventId || seen[eventId]) return;
          var notificationKind = (event.change || {}).is_correction === true ? 'correction' : 'new_observation';
          var copyText = alertCopy(alert.type, notificationKind);
          var item = {
            id: makeId('gri'), alert_id: alert.id, view_id: alert.view_id, event_id: eventId,
            type: alert.type, kind: text(event.kind, 40), notification_kind: notificationKind,
            event_contract: /^government_procurement_event\.v[12]$/.test(event.contract || '') ? event.contract : null,
            record_id: text(event.record_id, MAX_EVENT_ID_LENGTH) || null,
            event_version: Number.isSafeInteger(event.version) && event.version >= 1 ? event.version : null,
            title: text(event.title_original || event.title_zh, 500),
            observed_at: text(((event.change || {}).known_at), 80) || null,
            workspace_bundle_id: text(workspace.bundle_id, 100) || null,
            message: copyText.message, warning: copyText.warning
          };
          emitted.push(copy(item));
          state.inbox.unshift(item);
          seen[eventId] = true;
        });
        alert.seen_event_ids = stableUniqueIds(ids.concat(alert.seen_event_ids));
        alert.last_checked_at = stamp();
      });
      state.inbox = state.inbox.slice(0, MAX_INBOX);
      return { reconciled: true, alerts: emitted, withheld_alert_ids: withheld, rebaselined_alert_ids: rebaselined, persisted: commit() };
    }

    function buildJsonExport(workspace, filters) {
      if (!usableWorkspace(workspace)) throw new Error('invalid governed workspace');
      // Export must never silently substitute the Change feed for another page mode.
      var requestedMode = object(filters) ? text(filters.mode, 30).toLowerCase() : '';
      if (['candidates', 'budget', 'programs', 'fms'].indexOf(requestedMode) >= 0) {
        var unsupported = new Error('unsupported export mode');
        unsupported.code = 'unsupported_export_mode';
        throw unsupported;
      }
      var clean = cleanFilters(filters);
      var matched=resolvedEvents(workspace,clean);
      if(matched.length>MAX_SEEN_IDS)throw cutError('view_membership_unavailable');
      var records=matched.map(publicEvent);
      return {
        contract: EXPORT_CONTRACT,
        exported_at: stamp(),
        workspace: publicWorkspace(workspace),
        query: { filters: clean, result_scope: 'current visible governed workspace cut' },
        records: records
      };
    }

    function buildCsvExport(workspace, filters) {
      var payload = buildJsonExport(workspace, filters);
      var meta = payload.workspace;
      var headers = [
        'export_contract', 'workspace_bundle_id', 'workspace_schema_version', 'event_contract',
        'as_of', 'known_at', 'query_mode', 'query_truth', 'query_q', 'query_agency', 'query_ticker',
        'event_id', 'record_id', 'version', 'kind', 'state', 'title_original', 'title_zh',
        'agency', 'primary_ticker', 'change_type', 'change_known_at', 'primary_date',
        'primary_amount', 'mapping_class', 'source_class', 'source_receipt_url',
        'authority_tier', 'context_only', 'can_rank', 'can_size', 'limitations',
        'primary_amount_id', 'primary_amount_currency', 'primary_amount_semantic',
        'primary_amount_label_code', 'primary_amount_known_at', 'primary_amount_as_of',
        'primary_amount_source_ref', 'primary_amount_is_lower_bound'
      ];
      var rows = [headers];
      payload.records.forEach(function (event) {
        var agency = event.agency || {};
        var change = event.change || {};
        var evidence = event.evidence || {};
        var authority = event.authority || {};
        var amountValue = primaryAmount(event);
        var amount = amountValue === '' ? {} : primaryAmountFact(event);
        rows.push([
          payload.contract, meta.bundle_id, meta.schema_version, meta.event_contract,
          meta.as_of, meta.known_at, payload.query.filters.mode, payload.query.filters.truth,
          payload.query.filters.q, payload.query.filters.agency, payload.query.filters.ticker,
          event.event_id, event.record_id, event.version, event.kind, event.state,
          event.title_original, event.title_zh,
          agency.department_name || agency.name || '', event.primary_ticker,
          change.type, change.known_at, primaryDate(event), amountValue,
          evidence.mapping_class, evidence.source_class, firstReceiptUrl(event),
          authority.tier, authority.context_only, authority.can_rank, authority.can_size,
          meta.limitations,
          amount.id, amount.currency, amount.semantic, amount.label_code,
          amount.known_at, amount.as_of, amount.source_ref, amount.is_lower_bound
        ]);
      });
      var bundle = (meta.bundle_id || 'unversioned').replace(/[^A-Za-z0-9._-]/g, '_');
      var day = (String(meta.as_of || '').match(/^\d{4}-\d{2}-\d{2}/) || [])[0] || 'undated';
      return {
        contract: EXPORT_CONTRACT,
        media_type: 'text/csv;charset=utf-8',
        filename: 'government-revenue-' + day + '-' + bundle + '-view.csv',
        content: rows.map(function (row) { return row.map(csvCell).join(','); }).join('\n') + '\n'
      };
    }

    return {
      contract: STATE_CONTRACT,
      export_contract: EXPORT_CONTRACT,
      filter_keys: FILTER_KEYS.slice(),
      alert_types: ALERT_TYPES.slice(),
      listViews: function () { return copy(state.saved_views); },
      getSavedCut: getSavedCut,
      getView: function (id) { var view = viewById(text(id, 80)); return view ? copy(view) : null; },
      createView: createView,
      updateView: updateView,
      deleteView: deleteView,
      listAlerts: function () { return copy(state.alerts); },
      createAlert: createAlert,
      updateAlert: updateAlert,
      deleteAlert: deleteAlert,
      listInbox: function () { return copy(state.inbox); },
      reconcile: reconcile,
      buildJsonExport: buildJsonExport,
      buildCsvExport: buildCsvExport,
      state: function () { return copy(state); }
    };
  };
})(window);
