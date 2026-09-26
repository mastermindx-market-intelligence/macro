/* Shared, deterministic guide/help reader. No requests, model calls, or live values. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else Object.defineProperty(root, 'MastermindGuide', {value: api, configurable: false});
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SCHEMA = 'mastermind.market_guide/v1';
  const normalize = value => String(value ?? '').normalize('NFKC').toLowerCase().replace(/[\p{P}\p{Z}\s]+/gu, '');
  const slug = value => typeof value === 'string' && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value);
  const text = value => typeof value === 'string' && value.trim().length > 0;
  const pair = value => value && text(value.en) && text(value.zh);
  const safeOwner = value => typeof value === 'string' && !/\s/.test(value) && /^[a-z0-9_][a-z0-9_-]*\.html(?:#[A-Za-z0-9_-]+)?$/.test(value);
  const safeSource = value => {
    if (typeof value !== 'string' || /[\s\\]/.test(value)) return false;
    try { const url = new URL(value); return url.protocol === 'https:' && !url.username && !url.password; }
    catch (_) { return false; }
  };
  const copy = value => JSON.parse(JSON.stringify(value));
  const freeze = value => {
    if (value && typeof value === 'object' && !Object.isFrozen(value)) {
      Object.freeze(value); for (const child of Object.values(value)) freeze(child);
    }
    return value;
  };
  function createModel(input) {
    if (!input || input.schema !== SCHEMA || input.authority_ceiling !== 'reference_only' || input.live_values !== false) throw new Error('Unsupported guide data');
    const data = copy(input);
    if (!Array.isArray(data.entries) || !data.entries.length || !Array.isArray(data.coverage) || !Array.isArray(data.questions)) throw new Error('Incomplete guide data');
    const entries = new Map(), coverage = new Map(), questions = new Map();
    const kinds = new Set(['composite','risk','quadrant','confirmation','evidence','rotation','explanation']);
    for (const entry of data.entries) {
      if (!slug(entry.id) || entries.has(entry.id) || !pair(entry.label) || !pair(entry.definition) || !pair(entry.why) || !safeOwner(entry.owner_ref)) throw new Error('Invalid guide entry');
      if (!['active','deprecated'].includes(entry.status) || entry.authority_ceiling !== 'reference_only') throw new Error('Invalid entry status');
      if (!entry.caveats || !Array.isArray(entry.caveats.en) || !Array.isArray(entry.caveats.zh) || entry.caveats.en.length !== entry.caveats.zh.length || [...entry.caveats.en,...entry.caveats.zh].some(x => !text(x))) throw new Error('Invalid caveat translation');
      if (entry.kind === 'indicator' && (!pair(entry.visible_caveat) || !entry.caveats.en.length)) throw new Error('Missing essential limitation');
      if (entry.visible_caveat && (!pair(entry.visible_caveat) || entry.visible_caveat.en !== entry.caveats.en[0] || entry.visible_caveat.zh !== entry.caveats.zh[0])) throw new Error('Changed essential limitation');
      if (entry.basis !== null && !pair(entry.basis)) throw new Error('Invalid basis');
      if (!entry.aliases || !Array.isArray(entry.aliases.en) || !Array.isArray(entry.aliases.zh) || [...entry.aliases.en,...entry.aliases.zh].some(x => !text(x))) throw new Error('Invalid alias');
      if (!entry.presentation || !kinds.has(entry.presentation.kind) || !Array.isArray(entry.presentation.readings)) throw new Error('Unknown presentation');
      if (Object.keys(entry.presentation).some(key => !['kind','readings'].includes(key))) throw new Error('Unexpected presentation authority');
      const readings = new Set();
      for (const reading of entry.presentation.readings) {
        if (!['interpretation_up','interpretation_down','interpretation_neutral'].includes(reading.id) || readings.has(reading.id) || !pair(reading.text) || reading.label !== null && !pair(reading.label)) throw new Error('Invalid interpretation');
        readings.add(reading.id);
      }
      if (!Array.isArray(entry.public_source_refs) || entry.public_source_refs.some(url => !safeSource(url))) throw new Error('Unsafe source link');
      if (!Array.isArray(entry.related_ids) || !Array.isArray(entry.replacement_chain)) throw new Error('Invalid related or replacement links');
      entries.set(entry.id, entry);
    }
    for (const entry of entries.values()) {
      if (entry.related_ids.some(id => !entries.has(id)) || entry.replacement_chain.some(id => !entries.has(id)) || new Set([entry.id,...entry.replacement_chain]).size !== entry.replacement_chain.length + 1) throw new Error('Unresolved or cyclic entry link');
      if ((entry.status === 'deprecated') !== Boolean(entry.replacement_chain.length)) throw new Error('Unresolved retirement');
      if (entry.replacement_chain.length && entries.get(entry.replacement_chain.at(-1)).status !== 'active') throw new Error('Retirement needs an active successor');
    }
    for (const item of data.coverage) {
      if (!slug(item.id) || entries.has(item.id) || coverage.has(item.id) || !pair(item.label) || !['covered_by','not_an_indicator','not_covered'].includes(item.state) || !safeOwner(item.surface) || item.surface.includes('#')) throw new Error('Invalid coverage explanation');
      if (!Array.isArray(item.related_ids) || item.related_ids.some(id => !entries.has(id))) throw new Error('Unknown coverage target');
      if (item.state !== 'covered_by' && !pair(item.reason) || item.reason !== null && !pair(item.reason)) throw new Error('Missing coverage reason');
      if (item.state === 'covered_by' && !item.related_ids.length) throw new Error('Missing alias target');
      const expected = item.state === 'covered_by' && item.related_ids.length === 1 ? item.related_ids[0] : item.id;
      if (item.target !== expected) throw new Error('Changed coverage target');
      coverage.set(item.id,item);
    }
    for (const question of data.questions) {
      if (!slug(question.id) || questions.has(question.id) || !pair(question.label) || !Array.isArray(question.entry_ids) || !question.entry_ids.length || question.entry_ids.some(id => !entries.has(id)) || new Set(question.entry_ids).size !== question.entry_ids.length) throw new Error('Invalid question');
      questions.set(question.id,question);
    }
    if (!data.lookup || Array.isArray(data.lookup) || typeof data.lookup !== 'object') throw new Error('Missing lookup');
    for (const [key, values] of Object.entries(data.lookup)) {
      if (!key || normalize(key) !== key || !Array.isArray(values) || !values.length || values.some(id => !entries.has(id) && !coverage.has(id)) || new Set(values).size !== values.length) throw new Error('Invalid lookup target');
    }
    freeze(data);
    const get = id => entries.get(id) || coverage.get(id) || null;
    function resolve(value) {
      const raw = String(value ?? '').replace(/^#/, '');
      const direct = get(raw);
      if (direct) return {status:'found', id: direct.target || direct.id, matched:raw, alias:Boolean(direct.target && direct.target !== raw)};
      const ids = Object.hasOwn(data.lookup, normalize(raw)) ? data.lookup[normalize(raw)] : [];
      if (ids.length === 1) return {status:'found', id:ids[0], matched:raw, alias:true};
      if (ids.length > 1) return {status:'ambiguous', ids:[...ids], matched:raw};
      return {status:'missing', matched:raw};
    }
    function search(value, questionId='') {
      const needle = normalize(value);
      const allowed = questionId ? new Set(questions.get(questionId)?.entry_ids || []) : null;
      const exact = needle && Object.hasOwn(data.lookup,needle) ? new Set(data.lookup[needle]) : new Set();
      const questionTargets = new Set();
      for (const q of questions.values()) if (needle && [q.label.en,q.label.zh].some(label => normalize(label).includes(needle))) q.entry_ids.forEach(id => questionTargets.add(id));
      const hits = new Map();
      for (const record of [...entries.values(),...coverage.values()]) {
        const id = record.target || record.id;
        if (allowed && !allowed.has(id)) continue;
        const haystack = record.search_key || normalize(Object.values(record.label).join(' '));
        let score = exact.has(id) ? 0 : questionTargets.has(id) ? 1 : haystack.includes(needle) ? 2 : Infinity;
        // The source manifest holds normalized aliases; labels are never model-ranked.
        if (!needle) score = 2;
        if (Number.isFinite(score) && (!hits.has(id) || hits.get(id).score > score)) hits.set(id,{id,score});
      }
      return [...hits.values()].sort((a,b)=>a.score-b.score).map(hit => get(hit.id));
    }
    function chooseReading(id, readingId) {
      const readings = entries.get(id)?.presentation.readings || [];
      return readings.find(r=>r.id === readingId) || readings.find(r=>r.id === 'interpretation_neutral') || readings[0] || null;
    }
    function ownerURL(id, base) {
      const record = get(id), target = record?.owner_ref || record?.surface;
      if (!safeOwner(target)) return null;
      try { const origin = new URL(base); if (!['http:','https:'].includes(origin.protocol)) return null; return new URL('/'+target,origin.origin).href; } catch (_) { return null; }
    }
    return Object.freeze({schema:SCHEMA, revision:data.content_revision, entries:data.entries, coverage:data.coverage, questions:data.questions, get, resolve, search, chooseReading, ownerURL});
  }
  function readRoute(url, model) {
    const parsed = new URL(url), params = parsed.searchParams;
    const duplicate = ['q','topic','browse','lang','reading'].some(key=>params.getAll(key).length>1);
    let fragment; try { fragment=decodeURIComponent(parsed.hash.slice(1)); } catch (_) { fragment=parsed.hash.slice(1); }
    const topic = params.get('topic') || '';
    return {query:params.get('q') || '', topic:model.questions.some(q=>q.id===topic) ? topic : '', browsing:params.get('browse')==='all' || Boolean(params.get('q') || topic), lang:params.get('lang')==='zh'?'zh':'en', reading:params.get('reading')||'', fragment, resolution:fragment?model.resolve(fragment):null, duplicate};
  }
  function routeURL(base, state) {
    const url = new URL(base); url.search='';
    if (state.query) url.searchParams.set('q',state.query);
    if (state.topic) url.searchParams.set('topic',state.topic);
    if (state.browsing && !state.query && !state.topic) url.searchParams.set('browse','all');
    if (state.lang==='zh') url.searchParams.set('lang','zh');
    if (state.reading && state.fragment) url.searchParams.set('reading',state.reading);
    url.hash=state.fragment||'';
    return url.href;
  }
  return Object.freeze({SCHEMA,normalize,safeOwner,safeSource,createModel,readRoute,routeURL});
});
