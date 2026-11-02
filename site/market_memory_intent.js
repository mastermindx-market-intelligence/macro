/* Market Memory page intent only. No private evidence, authentication or fetch. */
(function (window) {
  'use strict';
  var ROUTE = '/market_memory.html';
  var MAX_TARGET = 4096;
  var MAX_CURRENT = 12288;
  var MAX_ISSUER = 2048;
  var MAX_VALUE = 512;
  var CAPSULE_KEY = 'market_memory.intent.oauth.v1';
  var CAPSULE_AGE = 30 * 60 * 1000;
  var resume = { ok: true, restored: false, active: false };
  var preservation = { ok: false, reason: 'intent_not_saved' };
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
  function targetFor(intent) {
    var params = new URLSearchParams();
    NAMES.forEach(function (name) {
      if (own(intent, name)) params.set(MAP[name], intent[name]);
    });
    var query = params.toString();
    var target = ROUTE + (query ? '?' + query : '');
    if (target.length > MAX_TARGET) return fail('intent_target_too_long');
    try {
      var check = new URL(target, window.location.origin);
      if (check.origin !== window.location.origin || check.pathname !== ROUTE) return fail('intent_origin');
    } catch (error) { return fail('intent_origin'); }
    return { ok: true, target: target, intent: intent };
  }
  function canonical(patch) {
    var result = merge(patch);
    return result.ok ? targetFor(result.intent) : result;
  }
  function clearCapsule() {
    try { window.sessionStorage.removeItem(CAPSULE_KEY); } catch (error) { /* unavailable */ }
  }
  function saveCapsule(result) {
    clearCapsule(); // An oversized/new invalid intent must never preserve an older selection.
    if (!result.ok) { preservation = fail(result.reason); return; }
    try {
      var body = JSON.stringify({schema:'market_memory.intent.oauth.v1', savedAt:Date.now(), target:result.target});
      window.sessionStorage.setItem(CAPSULE_KEY, body);
      preservation = {ok:true};
    } catch (error) { preservation = fail('intent_session_storage_unavailable'); }
  }
  function preserveCallback(url, current) {
    // Callback controls belong to the existing auth SDK, never to ret/storage.
    // Keep them on this same live URL until their owner consumes them.
    if (!resume.active) return;
    ['onboard', 'code', 'error', 'error_description', 'error_code'].forEach(function (key) {
      current.searchParams.getAll(key).forEach(function (value) { url.searchParams.append(key, value); });
    });
    url.hash = current.hash;
  }
  function restoreOAuthResume() {
    var current;
    try { current = new URL(window.location.href); } catch (error) { return; }
    if (current.pathname !== ROUTE || !current.searchParams.getAll('onboard').includes('resume')) return;
    resume = {ok:false, restored:false, active:true, reason:'intent_oauth_return_unavailable'};
    var incoming = read(current.href);
    if (current.searchParams.getAll('onboard').length !== 1
        || current.searchParams.getAll('ret').length > 1 || !incoming.ok) { clearCapsule(); return; }
    if (Object.keys(incoming.intent).length || current.searchParams.get('ret') === ROUTE) {
      // A reload after restoration has explicit owned state plus its exact ret.
      // Use that current URL, never a stale capsule or a conflicting selection.
      var explicit = targetFor(incoming.intent);
      if (explicit.ok && current.searchParams.getAll('ret').length === 1
          && current.searchParams.get('ret') === explicit.target) {
        resume = {ok:true, restored:false, active:true};
        saveCapsule(explicit);
      } else { clearCapsule(); }
      return;
    }
    var raw;
    try { raw = window.sessionStorage.getItem(CAPSULE_KEY); }
    catch (error) { resume.reason = 'intent_session_storage_unavailable'; return; }
    clearCapsule(); // One callback consumption; ordinary navigation never restores it.
    try {
      if (current.searchParams.getAll('onboard').length !== 1 || typeof raw !== 'string' || raw.length > MAX_TARGET + 256) return;
      var value = JSON.parse(raw);
      if (!value || typeof value !== 'object' || Array.isArray(value)
          || JSON.stringify(value) !== raw
          || Object.keys(value).sort().join(',') !== 'savedAt,schema,target'
          || value.schema !== 'market_memory.intent.oauth.v1'
          || !Number.isSafeInteger(value.savedAt) || value.savedAt > Date.now()
          || Date.now() - value.savedAt > CAPSULE_AGE || typeof value.target !== 'string') return;
      var target = new URL(value.target, window.location.origin);
      if (target.origin !== current.origin || target.pathname !== ROUTE || target.hash) return;
      var decoded = read(value.target);
      if (!decoded.ok) return;
      var rebuilt = targetFor(decoded.intent);
      if (!rebuilt.ok || rebuilt.target !== value.target) return;
      if (current.searchParams.has('ret') && current.searchParams.get('ret') !== rebuilt.target) return;
      // The callback may carry only auth controls. An explicit page selection
      // alongside it is ambiguous and must not be silently overwritten.
      target.searchParams.set('ret', rebuilt.target);
      preserveCallback(target, current);
      var liveTarget = target.pathname + target.search + target.hash;
      if (liveTarget.length > MAX_CURRENT) return;
      window.history.replaceState(window.history.state, '', liveTarget);
      resume = {ok:true, restored:true, active:true};
      saveCapsule(rebuilt);
    } catch (error) { /* Keep an explicit unavailable result, never choose a new capture. */ }
  }
  function syncReturn(patch) {
    var result = canonical(patch);
    if (!result.ok) { saveCapsule(result); return result; }
    var url = new URL(result.target, window.location.origin);
    url.searchParams.set('ret', result.target);
    preserveCallback(url, new URL(window.location.href));
    var current = url.pathname + url.search + url.hash;
    if (current.length > MAX_CURRENT) { clearCapsule(); return fail('intent_current_too_long'); }
    try { window.history.replaceState(window.history.state, '', current); }
    catch (error) { clearCapsule(); return fail('intent_history_unavailable'); }
    saveCapsule(result);
    result.current = current;
    result.oauthPreserved = preservation.ok;
    return result;
  }
  function signinHref(patch) {
    var result = canonical(patch);
    if (!result.ok) { saveCapsule(result); return result; }
    saveCapsule(result);
    var params = new URLSearchParams();
    params.set('signin', '1');
    params.set('ret', result.target);
    result.href = '/?' + params.toString();
    return result;
  }
  restoreOAuthResume(); // Finish restoration before exposing the page API.
  // An explicit page/return language outranks an asynchronously loaded profile.
  // Keep this separate from the generated URL: boot may add a default language
  // before the profile arrives, without the reader having chosen that default.
  var selectedLanguage = null, applyingProfileLanguage = false;
  function readSelectedLanguage() {
    var current = read();
    selectedLanguage = resume.ok && current.ok ? current.intent.language || null : null;
  }
  readSelectedLanguage();
  if (typeof window.addEventListener === 'function') window.addEventListener('popstate', readSelectedLanguage);
  function selectLanguage(language) {
    if (!applyingProfileLanguage && (language === 'en' || language === 'zh')) selectedLanguage = language;
  }
  function applyProfileLanguage(language, apply) {
    if ((language !== 'en' && language !== 'zh') || typeof apply !== 'function') return;
    // Profile hydration does not become a new user selection or overwrite an
    // explicit return selection. Its existing caller still owns save suppression.
    if (selectedLanguage) return;
    applyingProfileLanguage = true;
    try { apply(language); } finally { applyingProfileLanguage = false; }
  }
  window.MarketMemoryIntent = {
    read: read, replace: syncReturn, syncReturn: syncReturn, signinHref: signinHref,
    target: canonical,
    selectLanguage: selectLanguage, applyProfileLanguage: applyProfileLanguage,
    resumeStatus: function () { return {ok:resume.ok, restored:resume.restored, active:resume.active, reason:resume.reason}; },
    oauthPreservation: function () { return {ok:preservation.ok, reason:preservation.reason}; },
    limits: { target: MAX_TARGET, current: MAX_CURRENT, issuer: MAX_ISSUER, value: MAX_VALUE }
  };
}(window));
