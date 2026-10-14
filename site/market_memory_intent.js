/* Market Memory page intent only. No private evidence, authentication or fetch. */
(function (window) {
  'use strict';
  var ROUTE = '/market_memory.html';
  var MAX_TARGET = 4096;
  var MAX_CURRENT = 12288;
  var MAX_ISSUER = 2048;
  var MAX_VALUE = 512;
  var MAP = {
    mode: 'mm_mode', query: 'mm_query', subject: 'mm_subject', gen: 'mm_gen',
    gen_sha: 'mm_gen_sha', cutoff: 'mm_cutoff', method: 'mm_method', context: 'mm_context',
    sourceField: 'mm_source_field', sourceContext: 'mm_source_context', outcomeLens: 'mm_outcome', catalogOffset: 'mm_catalog_offset', ticker: 'ticker',
    issuerInput: 'mm_issuer_input', language: 'mm_lang', view: 'view'
  };
  var NAMES = Object.keys(MAP);
  var REVERSE = Object.create(null);
  NAMES.forEach(function (name) { REVERSE[MAP[name]] = name; });
  function own(obj, key) { return Object.prototype.hasOwnProperty.call(obj, key); }
  function fail(reason) { return { ok: false, reason: reason }; }
  function bounded(value, name) {
    if (name === 'catalogOffset') {
      if (typeof value === 'number' && isFinite(value) && Math.floor(value) === value) value = String(value);
      if (typeof value !== 'string' || !/^(0|[1-9][0-9]{0,2})$/.test(value) || Number(value) > 255) return fail('intent_catalog_offset');
    }
    if (typeof value !== 'string') return fail('intent_not_string:' + name);
    if (value.length > (name === 'issuerInput' ? MAX_ISSUER : MAX_VALUE)) return fail('intent_value_too_long:' + name);
    if (name === 'language' && value !== 'en' && value !== 'zh') return fail('intent_language');
    if (name === 'view' && value !== 'memory') return fail('intent_view');
    return { ok: true, value: value };
  }
  function read(input) {
    var search;
    try {
      var raw = input === undefined ? window.location.href : String(input);
      if (raw.length > MAX_CURRENT) return fail('intent_url_too_long');
      search = raw.charAt(0) === '?' ? raw.split('#')[0] : new URL(raw, window.location.origin).search;
    } catch (error) { return fail('intent_url_invalid'); }
    var intent = {};
    var pairs = search.slice(1).split('&');
    for (var i = 0; i < pairs.length; i += 1) {
      if (!pairs[i]) continue;
      var at = pairs[i].indexOf('=');
      var rawKey = at < 0 ? pairs[i] : pairs[i].slice(0, at);
      var key;
      try { key = decodeURIComponent(rawKey.replace(/\+/g, ' ')); }
      catch (error) { return fail('intent_encoding'); }
      if (!own(REVERSE, key)) continue;
      var name = REVERSE[key];
      if (own(intent, name)) return fail('intent_duplicate:' + key);
      var value;
      try { value = decodeURIComponent((at < 0 ? '' : pairs[i].slice(at + 1)).replace(/\+/g, ' ')); }
      catch (error) { return fail('intent_encoding'); }
      var check = bounded(value, name);
      if (!check.ok) return check;
      intent[name] = value;
    }
    return { ok: true, intent: intent };
  }
  function merge(patch) {
    var current = read();
    if (!current.ok) return current;
    var intent = current.intent;
    if (patch !== undefined && (patch === null || typeof patch !== 'object' || Array.isArray(patch))) return fail('intent_patch_invalid');
    for (var i = 0; i < NAMES.length; i += 1) {
      var name = NAMES[i];
      if (!patch || !own(patch, name) || patch[name] === undefined) continue;
      if (patch[name] === null) { delete intent[name]; continue; }
      var check = bounded(patch[name], name);
      if (!check.ok) return check;
      intent[name] = check.value;
    }
    return { ok: true, intent: intent };
  }
  function canonical(patch) {
    var result = merge(patch);
    if (!result.ok) return result;
    var params = new URLSearchParams();
    NAMES.forEach(function (name) {
      if (own(result.intent, name)) params.set(MAP[name], result.intent[name]);
    });
    var query = params.toString();
    var target = ROUTE + (query ? '?' + query : '');
    if (target.length > MAX_TARGET) return fail('intent_target_too_long');
    try {
      var check = new URL(target, window.location.origin);
      if (check.origin !== window.location.origin || check.pathname !== ROUTE) return fail('intent_origin');
    } catch (error) { return fail('intent_origin'); }
    return { ok: true, target: target, intent: result.intent };
  }
  function syncReturn(patch) {
    var result = canonical(patch);
    if (!result.ok) return result;
    var url = new URL(result.target, window.location.origin);
    url.searchParams.set('ret', result.target);
    var current = url.pathname + '?' + url.searchParams.toString();
    if (current.length > MAX_CURRENT) return fail('intent_current_too_long');
    try { window.history.replaceState(window.history.state, '', current); }
    catch (error) { return fail('intent_history_unavailable'); }
    result.current = current;
    return result;
  }
  function signinHref(patch) {
    var result = canonical(patch);
    if (!result.ok) return result;
    var params = new URLSearchParams();
    params.set('signin', '1');
    params.set('ret', result.target);
    result.href = '/?' + params.toString();
    return result;
  }
  window.MarketMemoryIntent = {
    read: read, replace: syncReturn, syncReturn: syncReturn, signinHref: signinHref,
    target: canonical,
    limits: { target: MAX_TARGET, current: MAX_CURRENT, issuer: MAX_ISSUER, value: MAX_VALUE }
  };
}(window));
