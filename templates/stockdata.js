/* stockdata.js — shared helpers for reading the nightly stock library
   (stockdata/index.json + stockdata/<TICKER>.json). Used by the Watchlist;
   available to any page that ships `window.STATE_DISPLAY` (the engine's
   STATE_DISPLAY map, injected by the build). Pure, dependency-free, and
   language-aware via the data-lang attribute — mirrors the helper logic that
   already lives inline in stock.html so the two pages cannot drift on
   filename-sanitization or state-label rules. */
(function () {
  function lang() { return document.documentElement.getAttribute('data-lang') || 'en'; }
  // pick the zh variant of a parallel-text field when in zh mode (the per-stock
  // JSON carries *_zh siblings from engine/cycles.py)
  function lz(en, zh) { return lang() === 'zh' && zh ? zh : (en || ''); }

  // engine state -> friendly display object {label, action, dir, *_zh}; the map
  // is injected per-page as window.STATE_DISPLAY (mirrors engine.cycles.STATE_DISPLAY)
  function disp(state) { return (window.STATE_DISPLAY || {})[state] || null; }
  // LIMITED is the engine's sentinel ladder state for listings below the cycle-history
  // floor (scripts/build_stock_library.py `_limited_rec`). It is emitted by four of the
  // five per-market indexes but carries NO STATE_DISPLAY entry, so the raw enum would
  // reach the user untranslated once non-US books render. Same bilingual copy the
  // sibling lookup pages already ship (china_lookup.html.j2, canada_stock.html.j2) —
  // house wording, not new copy. theme.css has no `.st-LIMITED` rule, so the pill
  // stays neutral-tinted, which is the honest read for "we can't classify this yet".
  var LIMITED_LABEL = { en: 'limited history', zh: '历史不足' };
  var LIMITED_ACTION = { en: 'new listing · limited history', zh: '新上市 · 历史不足' };
  function label(state) {
    var d = disp(state);
    if (!d) {
      if (state === 'LIMITED') return lang() === 'zh' ? LIMITED_LABEL.zh : LIMITED_LABEL.en;
      return state;   // unknown state: verbatim label, neutral tint — never invented copy
    }
    return lang() === 'zh' ? (d.label_zh || d.label) : d.label;
  }
  function action(state) {
    var d = disp(state);
    if (!d) {
      if (state === 'LIMITED') return lang() === 'zh' ? LIMITED_ACTION.zh : LIMITED_ACTION.en;
      return '';
    }
    return lang() === 'zh' ? (d.action_zh || d.action) : d.action;
  }
  function dir(state) { var d = disp(state); return d ? d.dir : 'neutral'; }
  // theme.css already tints any element carrying class `st-<STATE>` (spaces->_)
  function stClass(state) { return 'st-' + String(state).replace(/ /g, '_'); }

  // Yahoo-style tickers carry '=' / '^', which the Python builder maps to '_' in
  // the on-disk filename. GLOBAL replace (String.replace(str,..) would only hit
  // the first occurrence — fragile if a symbol ever carried two). Leave '.'/'-'
  // untouched: e.g. DX-Y.NYB ships as DX-Y.NYB.json.
  function safeTicker(t) { return String(t).replace(/[=^]/g, '_'); }

  // Per-market store routing. The per-ticker plane is FIVE parallel stores, one per
  // market, all with the same rich schema; `market_books.js` owns the suffix -> store
  // derivation and publishes it on window.MB. Absent (a page that doesn't ship
  // market_books.js), everything resolves to the US store — today's exact behavior.
  function storeOf(t) {
    return (window.MB && window.MB.storeOf) ? window.MB.storeOf(t) : 'stockdata';
  }
  // index.json lives under the same five dirs; crypto/macro names live in the US store
  var MKT_DIR = {
    us: 'stockdata', cn: 'chinastockdata', hk: 'hkstockdata',
    ca: 'canadastockdata', intl: 'intlstockdata'
  };
  function normMkt(m) { return (m === 'crypto' || m === 'macro') ? 'us' : m; }

  var _index = null, _indexBy = null, _tickerCache = {};
  var _mkt = {}, _mktLoading = {};   // market -> {list, byTicker} / in-flight promise
  var _indexLoading = null;          // the ONE in-flight US index read (direct + indirect callers)
  var _mktNeg = {};                  // market -> epoch ms before which a FAILED index is not refetched

  // Build {list, byTicker} OFF TO THE SIDE so a malformed payload never reaches the
  // successful cache. A non-array top level throws; a non-object row (null or a
  // primitive) is dropped from BOTH list and lookup so it cannot poison the
  // generation. Every object row is kept exactly as the pre-fix module kept it (no
  // stricter ticker-identity rule); optional/null fields are left exactly as served.
  function _buildIndex(raw, mktOf) {
    if (!Array.isArray(raw)) throw new Error('malformed index');
    var list = [], by = {};
    raw.forEach(function (x) {
      if (!x || typeof x !== 'object') return;
      x.mkt = mktOf(x);
      list.push(x); by[x.t] = x;
    });
    return { list: list, byTicker: by };
  }

  // fetch + cache the full US search index once -> {list, byTicker}. Unchanged contract:
  // REJECTS when the index is unavailable (callers rely on the catch to still paint).
  // Concurrent callers share one in-flight read; a failure rejects every waiter and
  // the next call retries.
  function loadIndex() {
    if (_index) return Promise.resolve({ list: _index, byTicker: _indexBy });
    if (_indexLoading) return _indexLoading;
    var p = fetch('stockdata/index.json').then(function (r) {
      if (!r.ok) throw _httpErr(r, 'index unavailable');
      return r.json();
    }).then(function (raw) {
      var built = _buildIndex(raw, function (x) { return x.mkt || 'us'; });
      _index = built.list; _indexBy = built.byTicker;
      _mkt.us = { list: _index, byTicker: _indexBy };
      return { list: _index, byTicker: _indexBy };
    });
    _indexLoading = p;
    var clear = function () { if (_indexLoading === p) _indexLoading = null; };
    p.then(clear, clear);
    return p;
  }

  // one market's index, memoized. Fail-OPEN for the merge: a missing store contributes
  // nothing rather than breaking the merge (a market the user holds nothing in may 404).
  // But a failure is never cached as success — it is retried after a bounded window:
  // short for transient failures / Retry-After, long for a definitive 404.
  function loadMarketIndex(m) {
    m = normMkt(m);
    if (_mkt[m]) return Promise.resolve(_mkt[m]);
    if (_mktLoading[m]) return _mktLoading[m];
    var dir = MKT_DIR[m];
    if (!dir) return Promise.resolve({ list: [], byTicker: {} });
    if (_mktNeg[m] != null && Date.now() < _mktNeg[m]) return Promise.resolve({ list: [], byTicker: {} });
    var p = (m === 'us' ? loadIndex() : fetch(dir + '/index.json').then(function (r) {
      if (!r.ok) throw _httpErr(r, 'absent');
      return r.json();
    }).then(function (raw) {
      _mkt[m] = _buildIndex(raw, function () { return m; });
      return _mkt[m];
    })).then(function (res) {
      delete _mktNeg[m];
      return res;
    }, function (err) {
      _mktNeg[m] = Date.now() + _failTtl(err);
      return { list: [], byTicker: {} };
    });
    _mktLoading[m] = p;
    p.then(function () { if (_mktLoading[m] === p) delete _mktLoading[m]; });
    return p;
  }

  // fetch + merge the named markets' indexes -> {list, byTicker}. Each entry carries
  // its own `.mkt`. Later markets never clobber an earlier ticker (US wins on collision).
  function loadIndexes(markets) {
    var want = [];
    (markets || ['us']).forEach(function (m) {
      m = normMkt(m);
      if (MKT_DIR[m] && want.indexOf(m) < 0) want.push(m);
    });
    if (!want.length) want = ['us'];
    return Promise.all(want.map(loadMarketIndex)).then(function (parts) {
      var list = [], by = {};
      parts.forEach(function (p) {
        if (!p) return;
        p.list.forEach(function (x) {
          if (Object.prototype.hasOwnProperty.call(by, x.t)) return;
          by[x.t] = x; list.push(x);
        });
      });
      return { list: list, byTicker: by };
    });
  }

  /* ---- per-ticker reads ----------------------------------------------------
     Two properties this layer must hold that it did not before W2, both of which
     the large-list gate (55 and 100 names) makes load-bearing:

     1. A MISS IS NOT PERMANENT. The old cache wrote `null` on any failure and
        answered from it forever, so one transient network blip — or a 401 landed in
        the split second before the session cookie arrived — permanently blanked that
        name for the rest of the page's life, with no way back short of a reload. The
        negative entry now carries an expiry: 404/410 and 401/403 keep the long TTL;
        a thrown fetch AND a transient server answer (5xx/408/429) get the short one,
        or the server's Retry-After clamped to [30 s, 10 min].
     2. FAN-OUT IS BOUNDED. A 100-name list used to issue 100 simultaneous requests
        the moment it painted; browsers queue them 6-per-host anyway, so the only
        real effects were a stalled main thread and a request storm that starved the
        index fetch. `loadTickers` runs a fixed-width worker pool and hands each
        result back the moment it lands, so rows hydrate progressively and ONE
        failure degrades exactly ONE row. */
  var NEG_TTL_HTTP = 10 * 60 * 1000;   // the store answered: nothing new until the next build
  var NEG_TTL_NET  = 30 * 1000;        // the network answered nothing: retry soon
  var _neg = {};                        // ticker -> epoch ms after which we may retry
  var _inflight = {};                   // ticker -> in-flight promise (dedupes concurrent asks)

  function _httpErr(r, msg) {
    var e = new Error(msg); e.http = true; e.status = r.status;
    e.retryAfter = (r.headers && typeof r.headers.get === 'function') ? r.headers.get('Retry-After') : null;
    return e;
  }
  function _retryAfterMs(v) {
    if (v == null) return null;
    var s = String(v).trim();
    if (!s) return null;
    if (/^\d+$/.test(s)) return parseInt(s, 10) * 1000;
    var at = Date.parse(s);
    return isNaN(at) ? null : Math.max(0, at - Date.now());
  }
  // How long a failure stays negative. Transient (thrown fetch, malformed body, 5xx,
  // 408, 429): short, or the server's Retry-After clamped to [NEG_TTL_NET, NEG_TTL_HTTP]
  // so it can neither storm nor stick. A definitive answer (404/410 "not in tonight's
  // library", 401/403 "not for you"): long, exactly as before — no access semantics change.
  function _failTtl(err) {
    var st = err && err.status;
    var transient = !(err && err.http) || st >= 500 || st === 408 || st === 429;
    if (!transient) return NEG_TTL_HTTP;
    var ra = _retryAfterMs(err && err.retryAfter);
    if (ra == null) return NEG_TTL_NET;
    return Math.min(NEG_TTL_HTTP, Math.max(NEG_TTL_NET, ra));
  }

  function _negFresh(t) {
    var until = _neg[t];
    return until != null && Date.now() < until;
  }

  // fetch + cache one ticker's rich JSON from ITS market's store; resolves null on
  // absent so callers can degrade gracefully (never throws).
  function loadTicker(t) {
    if (Object.prototype.hasOwnProperty.call(_tickerCache, t) && _tickerCache[t])
      return Promise.resolve(_tickerCache[t]);
    if (_negFresh(t)) return Promise.resolve(null);
    if (_inflight[t]) return _inflight[t];

    var p = fetch(storeOf(t) + '/' + safeTicker(t) + '.json').then(function (r) {
      if (!r.ok) throw _httpErr(r, 'absent');
      return r.json();
    }).then(function (j) {
      _tickerCache[t] = j;
      delete _neg[t];
      delete _inflight[t];
      return j;
    }).catch(function (err) {
      _tickerCache[t] = null;
      _neg[t] = Date.now() + _failTtl(err);
      delete _inflight[t];
      return null;
    });
    _inflight[t] = p;
    return p;
  }

  /* Bounded-concurrency batch read. `onEach(ticker, json)` fires per resolution —
     json is null for a name we could not read, which is the caller's cue to draw an
     honest blank on that ONE row rather than to fail the batch. Resolves when the
     whole list has been attempted. Concurrency is deliberately at the browser's own
     per-host ceiling: higher just queues, and queueing is what hid the failures. */
  function loadTickers(tickers, onEach, opts) {
    var list = (tickers || []).filter(function (t) { return !!t; });
    var width = Math.max(1, (opts && opts.concurrency) || 6);
    var i = 0;
    function next() {
      if (i >= list.length) return Promise.resolve();
      var t = list[i++];
      /* `loadTicker` can throw SYNCHRONOUSLY before it ever returns a promise — a
         missing market_books.js makes `storeOf` blow up on the first call. Un-guarded,
         that throw escapes `next()` and kills the whole worker lane, so a batch of 100
         silently loses a fifth of its rows with one exception nobody sees. Guarding
         here degrades exactly the one name, which is the contract this function
         promises its callers. */
      var pending;
      try { pending = loadTicker(t); }
      catch (e) { pending = Promise.resolve(null); }
      return pending.then(function (j) {
        if (onEach) { try { onEach(t, j); } catch (e) {} }
        return next();
      }, function () {
        if (onEach) { try { onEach(t, null); } catch (e) {} }
        return next();
      });
    }
    var lanes = [];
    for (var k = 0; k < Math.min(width, list.length); k++) lanes.push(next());
    return Promise.all(lanes);
  }

  window.SD = {
    lang: lang, lz: lz, disp: disp, label: label, action: action, dir: dir,
    stClass: stClass, safeTicker: safeTicker, storeOf: storeOf,
    loadIndex: loadIndex, loadIndexes: loadIndexes,
    loadTicker: loadTicker, loadTickers: loadTickers
  };
})();
