/* Mastermind stock-dossier live quote binding.
 *
 * The dossier is nightly-rendered static HTML. Before this module the hero
 * price, the sticky-strip price and the day move were all baked at build time
 * while a green "Live" pip sat beside them, keyed off the BUILD's date rather
 * than any quote. Measured 2026-08-27: NVDA served $209.66 with a static
 * "-$3.39 · -1.59%" and a pulsing "Live" chip, while the measured
 * regular-session close was $227.98 (+8.74%) — the page showed the PREVIOUS
 * close and the PREVIOUS day's move, and called it live.
 *
 * Contract with the page
 * ----------------------
 *   [data-dq-sym]     price nodes (hero + sticky). Deliberately NOT .nb-px:
 *                     the shared live.js poller owns .nb-px, and two owners
 *                     writing one node is a race decided by fetch order.
 *   [data-dq-chg]     the move row (carries .pos/.neg)
 *   [data-dq-abs]     absolute move   [data-dq-pct] percent move
 *   [data-dq-stamp]   freshness stamp, data-dq-state = baked|live|delayed|closed
 *
 * Honesty law
 * -----------
 * Price and move are written TOGETHER from ONE quote, or not at all — a
 * half-applied repaint would leave a current price beside a stale move, which
 * is the same lie in a subtler form. "Live" requires the server to report a
 * measured realtime feed AND an open regular session; anything else is named
 * for what it is. Any failure, or a quote the server itself marks stale,
 * leaves the baked HTML exactly as rendered.
 */
(function () {
  'use strict';

  var priceNodes = document.querySelectorAll('[data-dq-sym]');
  if (!priceNodes.length) return;

  var ticker = String(priceNodes[0].getAttribute('data-dq-sym') || '').trim().toUpperCase();
  if (ticker.indexOf('..') !== -1 || !/^[A-Z0-9](?:[A-Z0-9.\-]{0,14}[A-Z0-9])?$/.test(ticker)) return;

  // No fetch (or no Promise) means no quote — stand down and leave the baked
  // page exactly as rendered. Checked BEFORE first use, because calling a
  // missing `fetch` throws synchronously, ahead of any promise chain, so the
  // `.catch` below would never see it: the page would keep its correct baked
  // values but log an uncaught error on every tick.
  if (typeof window.fetch !== 'function' || typeof window.Promise !== 'function') return;

  var chgRow = document.querySelector('[data-dq-chg]');
  var absNode = document.querySelector('[data-dq-abs]');
  var pctNode = document.querySelector('[data-dq-pct]');
  var stamp = document.querySelector('[data-dq-stamp]');
  var rangeEl = document.querySelector('[data-dq-range]');
  var fillEl = document.querySelector('[data-dq-fill]');
  var dotEl = document.querySelector('[data-dq-dot]');
  var regularLabel = document.querySelector('[data-dq-regular-label]');
  var extendedRow = document.querySelector('[data-dq-extended]');
  var extendedValues = document.querySelector('[data-dq-ext-values]');
  var extendedStatus = document.querySelector('[data-dq-ext-status]');
  var extendedSession = document.querySelector('[data-dq-ext-session]');
  var extendedPrice = document.querySelector('[data-dq-ext-price]');
  var extendedAbs = document.querySelector('[data-dq-ext-abs]');
  var extendedPct = document.querySelector('[data-dq-ext-pct]');
  var extendedReference = document.querySelector('[data-dq-ext-reference]');
  var extendedAge = document.querySelector('[data-dq-ext-age]');
  var extendedQuote = null;
  var expiryTimer = null;
  var clockTimer = null;

  var POLL_MS = 15000;      // comfortably inside the hub's own snapshot cadence
  var TIMEOUT_MS = 6000;
  var timer = null;
  var inflight = false;

  // ---- Attempt accounting (observational only) --------------------------
  //
  // The 41/600 cap is an OPERATOR obligation; nothing here knows it, enforces
  // it, or is consulted by anything that does. This ledger only observes THIS
  // document's quote attempts so an operator can later ask "how many did this
  // page actually make?" without trusting a network log or a green pip. It is
  // deliberately NOT authoritative, so a snapshot structurally cannot claim a
  // complete count: writer.exclusive_proven is pinned false, because a
  // same-origin frame, a duplicate script tag or a bfcache-restored old
  // document can never be ruled out from inside one document.
  //
  // Storage is one namespaced key in per-tab sessionStorage: it survives
  // reload and same-tab navigation, dies with the tab, and is NOT treated as
  // a trusted tab identity — only as whatever evidence it happens to hold.
  // The aggregate only ever climbs; the history keeps at most 64 records and
  // says so once it has dropped any. Every fault (write denial, quota, parse,
  // deletion, rollback, concurrent writer, duplicate script) becomes a STICKY
  // degradation that survives reload; the counter is never silently restarted
  // at a healthy 0, and where the prior total becomes unknowable the snapshot
  // says `aggregate_known: false` instead of inventing one. Records carry a
  // sequence, a clock, the symbol and an outcome word — never a quote, a
  // credential or a response body. Quoting itself never waits on accounting:
  // every entry point below is guarded and faults there cannot stop a poll.
  var LEDGER_KEY = 'dq:attempt-ledger:v1';
  var LEDGER_MAX = 64;
  var LEDGER_SCHEMA = 1;
  // Sticky uncertainty flags. `rollback` is surfaced under `reset`: from the
  // reader's chair both mean "earlier evidence stopped being true".
  var UNC_KEYS = ['storage', 'parse', 'reset', 'loss', 'concurrent_writer'];
  var UNC_OF = { storage: 'storage', parse: 'parse', reset: 'reset',
                 rollback: 'reset', loss: 'loss', concurrent_writer: 'concurrent_writer' };

  var loadClock = Date.now();
  var instanceId = 'i' + loadClock.toString(36) + Math.random().toString(36).slice(2, 8);
  var docId = 'd' + loadClock.toString(36) + Math.random().toString(36).slice(2, 8);

  var ledger = {
    v: LEDGER_SCHEMA,
    series: null,            // { id, started_clock, provenance } (provenance not persisted)
    aggregate: 0,
    aggregate_known: false,  // false => prior total UNKNOWN, never "zero"
    records: [],             // { seq, clock, symbol, outcome }, oldest first
    truncated: false,        // at least one record has fallen off the history
    seq: 0,
    degraded: null,          // { reasons: [...], at_clock } — sticky, persisted
    unc: { storage: false, parse: false, reset: false, loss: false, concurrent_writer: false },
    gen: 0,                  // document-load generation in this storage scope
    inst: instanceId
  };
  var seriesPrior = false;   // a readable prior series was adopted at load
  var lastObservedInst = null;
  var duplicateWriter = false;
  // Local increments not yet reconciled against storage. They are carried
  // across a merge so a foreign writer's advance is ADDED to ours instead of
  // either side's count being silently dropped.
  var unsynced = 0;

  function storage() {
    try {
      var s = window.sessionStorage;
      if (s && typeof s.getItem === 'function' && typeof s.setItem === 'function') return s;
    } catch (e) { /* access denied (e.g. blocked storage) */ }
    return null;
  }

  // Sticky means sticky: a fault, once seen in this scope, is never un-seen
  // by a later reload.
  function degrade(reason) {
    if (!ledger.degraded) ledger.degraded = { reasons: [], at_clock: Date.now() };
    if (ledger.degraded.reasons.indexOf(reason) === -1) ledger.degraded.reasons.push(reason);
    if (reason !== 'storage') ledger.aggregate_known = false;
    var key = UNC_OF[reason];
    if (key) ledger.unc[key] = true;
  }

  function newSeriesId() {
    return 's' + loadClock.toString(36) + Math.random().toString(36).slice(2, 10);
  }

  function counter(n) {
    return typeof n === 'number' && isFinite(n) && Math.floor(n) === n &&
      n >= 0 && n < 9007199254740000;
  }

  function validLedger(d) {
    if (!d || typeof d !== 'object' || Array.isArray(d) || d.v !== LEDGER_SCHEMA ||
        !counter(d.aggregate) || !counter(d.seq) || !counter(d.gen) ||
        typeof d.inst !== 'string' || d.inst.length > 80 ||
        !Array.isArray(d.records) || d.records.length > LEDGER_MAX ||
        typeof d.truncated !== 'boolean' || typeof d.aggregate_known !== 'boolean' ||
        !d.series || typeof d.series.id !== 'string' || d.series.id.length > 80 ||
        !counter(d.series.started_clock)) return false;
    if (d.degraded && (!Array.isArray(d.degraded.reasons) ||
        d.degraded.reasons.length > 6 || !counter(d.degraded.at_clock) ||
        d.degraded.reasons.some(function (r) {
          return typeof r !== 'string' || !Object.prototype.hasOwnProperty.call(UNC_OF, r);
        }))) return false;
    return d.records.every(function (r) {
      return r && counter(r.seq) && counter(r.clock) &&
        typeof r.document === 'string' && r.document.length <= 80 &&
        typeof r.symbol === 'string' && /^[A-Z0-9][A-Z0-9.\-]{0,15}$/.test(r.symbol) &&
        ['pending', 'response', 'http-error', 'reject', 'sync-error', 'timeout'].indexOf(r.outcome) !== -1;
    });
  }

  // Read the stored ledger, flagging (never swallowing) what is wrong with it.
  // Three outcomes that must NOT be conflated: 'absent' (no evidence — a
  // first visit, or evidence destroyed), 'unreadable' (evidence present but
  // corrupt), and 'failed' (we were DENIED the read — which is not evidence
  // about the past at all, and must never be called a reset).
  function readLedger(s) {
    var raw = null;
    try { raw = s.getItem(LEDGER_KEY); }
    catch (e) { ledger.unc.storage = true; degrade('storage'); return { state: 'failed', data: null }; }
    if (raw === null || typeof raw !== 'string') return { state: 'absent', data: null };
    if (raw.length > 32768) { degrade('parse'); return { state: 'unreadable', data: null }; }
    var d = null;
    try { d = JSON.parse(raw); }
    catch (e) { ledger.unc.parse = true; degrade('parse'); return { state: 'unreadable', data: null }; }
    if (!validLedger(d)) { ledger.unc.parse = true; degrade('parse'); return { state: 'unreadable', data: null }; }
    return { state: 'ok', data: d };
  }

  // Adopt sticky facts from whatever is in storage just before our write
  // lands. The aggregate itself is reconciled by the caller: it is the one
  // value where being conservative means arithmetic, not flag-copying.
  function adoptSticky(d) {
    if (!d) return;
    var i;
    if (d.unc) for (i = 0; i < UNC_KEYS.length; i++) if (d.unc[UNC_KEYS[i]]) ledger.unc[UNC_KEYS[i]] = true;
    if (d.degraded && Array.isArray(d.degraded.reasons)) {
      for (i = 0; i < d.degraded.reasons.length; i++) degrade(d.degraded.reasons[i]);
    }
    if (d.aggregate_known === false) ledger.aggregate_known = false;
    if (typeof d.seq === 'number' && isFinite(d.seq) && d.seq > ledger.seq) ledger.seq = d.seq;
    if (d.truncated) ledger.truncated = true;
  }

  function mergeRecords(stored) {
    // Sequence numbers can coincide in different documents. Only a document
    // and sequence together identify an attempt. A late pending row must
    // never overwrite the observed outcome for that attempt.
    var rows = new Map();
    stored.concat(ledger.records).forEach(function (r) {
      var key = r.document + ':' + r.seq;
      if (!rows.has(key) || r.outcome !== 'pending') {
        rows.set(key, { document: r.document, seq: r.seq, clock: r.clock,
                        symbol: r.symbol, outcome: r.outcome });
      }
    });
    var all = Array.from(rows.values()).sort(function (a, b) {
      return a.seq - b.seq || a.clock - b.clock || a.document.localeCompare(b.document);
    });
    if (all.length > LEDGER_MAX) ledger.truncated = true;
    if (all.length < Math.min(ledger.aggregate, LEDGER_MAX)) {
      ledger.truncated = true;
      degrade('loss');
    }
    ledger.records = all.slice(-LEDGER_MAX);
  }

  function stateForStorage() {
    return {
      v: LEDGER_SCHEMA,
      series: ledger.series ? { id: ledger.series.id, started_clock: ledger.series.started_clock } : null,
      aggregate: ledger.aggregate,
      aggregate_known: ledger.aggregate_known,
      records: ledger.records.slice(-LEDGER_MAX),
      truncated: ledger.truncated,
      seq: ledger.seq,
      degraded: ledger.degraded,
      unc: ledger.unc,
      gen: ledger.gen,
      inst: ledger.inst
    };
  }

  // Storage offers no transaction across writers. Reconcile observed records
  // and keep the uncertainty visible if another writer or a rollback appears.
  function writeLedger() {
    if (duplicateWriter || window.__dqAttemptConflict) { degrade('loss'); degrade('concurrent_writer'); }
    var s = storage();
    if (!s) { ledger.unc.storage = true; degrade('storage'); return; }

    var r = readLedger(s);
    if (r.state === 'failed') return;  // Keep unsynced attempts until the prior value is readable.
    var d = r.state === 'ok' ? r.data : null;
    if (d) {
      if (typeof d.gen === 'number' && isFinite(d.gen) && d.gen > ledger.gen) {
        // A newer document generation owns this scope: we are the old document
        // (a bfcache restore racing a reload). Our attempts still really
        // happened and still count — but this ledger can no longer be read as
        // one writer's complete record.
        ledger.unc.concurrent_writer = true;
        degrade('concurrent_writer');
      }
      if (typeof d.inst === 'string' && d.inst !== instanceId && d.inst !== lastObservedInst) {
        ledger.unc.concurrent_writer = true;
        degrade('concurrent_writer');
      }
      var storedAgg = typeof d.aggregate === 'number' && isFinite(d.aggregate) && d.aggregate >= 0
        ? d.aggregate : null;
      var baseline = ledger.aggregate - unsynced;   // what we last wrote (or adopted)
      if (storedAgg !== null) {
        if (storedAgg < baseline) {
          // Monotonicity violation: storage is behind even our last written
          // value, so it was rolled back to an older copy. Keep ours and say so.
          degrade('rollback');
        } else {
          // A foreign writer may have advanced the shared count while we held
          // unsynced local increments; add ours on top of what is stored
          // rather than letting either side's attempts vanish.
          var merged = storedAgg + unsynced;
          if (merged > ledger.aggregate) {
            ledger.aggregate = merged;
          }
        }
      } else {
        // The stored counter itself is unreadable: the past is unknown again.
        ledger.aggregate_known = false;
      }
      adoptSticky(d);
      mergeRecords(d.records);
    } else if (r.state === 'absent' && lastObservedInst !== null && ledger.seq > 0) {
      // Evidence we ourselves wrote is GONE — genuinely absent, not merely
      // denied to us. The prior total is now unknown and stays unknown; this
      // is not a healthy fresh start.
      ledger.unc.reset = true;
      degrade('reset');
      ledger.aggregate_known = false;
    }

    ledger.inst = instanceId;
    var payload;
    try { payload = JSON.stringify(stateForStorage()); }
    catch (e) { ledger.unc.storage = true; degrade('storage'); return; }
    try { s.setItem(LEDGER_KEY, payload); }
    catch (e) { ledger.unc.storage = true; degrade('storage'); return; }
    lastObservedInst = instanceId;
    unsynced = 0;
    // A write that cannot be read back is not a durable write; the in-memory
    // count stands, but the snapshot must say storage is not trustworthy.
    try { if (s.getItem(LEDGER_KEY) !== payload) { ledger.unc.storage = true; degrade('storage'); } }
    catch (e) { ledger.unc.storage = true; degrade('storage'); }
  }

  function initLedger() {
    try {
      duplicateWriter = Boolean(window.__dqAttemptInst);
      if (duplicateWriter) window.__dqAttemptConflict = true;
      else window.__dqAttemptInst = instanceId;
    } catch (e) { duplicateWriter = true; }

    var s = storage();
    if (!s) {
      ledger.unc.storage = true;
      degrade('storage');
      ledger.aggregate_known = false;   // nothing readable: prior total unknown
      ledger.series = { id: newSeriesId(), started_clock: loadClock, provenance: 'unstored' };
      return;
    }
    var found = readLedger(s);
    if (found.state !== 'ok') {
      // No readable prior evidence: a first visit, corrupt evidence, or a
      // read we were denied. All three start a NEW series, and none may claim
      // anything about what came before.
      ledger.series = { id: newSeriesId(), started_clock: loadClock,
                        provenance: found.state === 'unreadable' ? 'unreadable'
                                  : found.state === 'failed' ? 'unstored' : 'new' };
      ledger.aggregate_known = found.state === 'absent';
      ledger.gen = 1;
      writeLedger();
      return;
    }
    var d = found.data;
    // Restore everything a reload must carry forward: series identity, the
    // monotonic aggregate, the bounded history and every sticky fault.
    seriesPrior = true;
    ledger.aggregate = d.aggregate;
    ledger.aggregate_known = d.aggregate_known === true;
    ledger.seq = d.seq;
    ledger.truncated = d.truncated;
    var i, rec, ok = true;
    ledger.records = [];
    for (i = 0; i < d.records.length && i < LEDGER_MAX; i++) {
      rec = d.records[i];
      if (rec && typeof rec === 'object' && !Array.isArray(rec) &&
          typeof rec.seq === 'number' && isFinite(rec.seq) &&
          typeof rec.clock === 'number' && isFinite(rec.clock) &&
          typeof rec.symbol === 'string' && typeof rec.outcome === 'string') {
        ledger.records.push({ seq: rec.seq, clock: rec.clock, document: rec.document, symbol: rec.symbol, outcome: rec.outcome });
      } else ok = false;
    }
    if (!ok || d.records.length > LEDGER_MAX) { ledger.unc.parse = true; degrade('parse'); }
    adoptSticky(d);
    if (d.series && typeof d.series.id === 'string' && d.series.id &&
        typeof d.series.started_clock === 'number' && isFinite(d.series.started_clock) && d.series.started_clock > 0) {
      ledger.series = { id: d.series.id, started_clock: d.series.started_clock, provenance: 'restored' };
    } else {
      ledger.unc.parse = true;
      degrade('parse');
      ledger.series = { id: newSeriesId(), started_clock: loadClock, provenance: 'rebuilt' };
      ledger.aggregate_known = false;
    }
    ledger.gen = typeof d.gen === 'number' && isFinite(d.gen) && d.gen >= 0 ? d.gen + 1 : 1;
    lastObservedInst = typeof d.inst === 'string' && d.inst ? d.inst : null;
    writeLedger();
  }

  // Counted exactly once, before the request exists: a fetch that throws
  // before originating, or a promise that never settles, is still an attempt
  // the operator should hear about. Outcomes only NAME the record afterwards.
  function beginAttempt(symbol) {
    try {
      var attemptSeq = ++ledger.seq;
      ledger.aggregate += 1;
      unsynced += 1;
      ledger.records.push({ seq: ledger.seq, clock: Date.now(), document: docId, symbol: symbol, outcome: 'pending' });
      if (ledger.records.length > LEDGER_MAX) {
        ledger.records.splice(0, ledger.records.length - LEDGER_MAX);
        ledger.truncated = true;
      }
      writeLedger();
      publishLedgerSnapshot();
      return attemptSeq;
    } catch (e) {
      try { ledger.unc.storage = true; degrade('storage'); } catch (e2) { /* stay quiet */ }
      return null;
    }
  }

  function settleAttempt(seq, outcome) {
    if (seq === null || seq === undefined) return;
    try {
      for (var i = ledger.records.length - 1; i >= 0; i--) {
        if (ledger.records[i].document === docId && ledger.records[i].seq === seq) { ledger.records[i].outcome = outcome; break; }
      }
      writeLedger();
      publishLedgerSnapshot();
    } catch (e) {
      try { ledger.unc.storage = true; degrade('storage'); } catch (e2) { /* stay quiet */ }
    }
  }

  function freezeDeep(v) {
    var k;
    if (v && typeof v === 'object') {
      Object.freeze(v);
      for (k in v) if (Object.prototype.hasOwnProperty.call(v, k)) freezeDeep(v[k]);
    }
    return v;
  }

  // The only outward surface: a frozen deep copy of plain data. Mutating a
  // snapshot cannot reach the ledger, and nothing in it is a quote, a
  // credential or a response body. `writer.exclusive_proven` is pinned false
  // on purpose — no document can prove no other writer exists, so no snapshot
  // can honestly claim a complete count.
  function snapshotState() {
    return {
      schema: 'dq-attempt-ledger/1',
      mode: 'observational',        // counting only: not enforcement, not a budget
      authoritative: false,
      enforcement: 'none',
      document: docId,
      symbol: ticker,
      clock: Date.now(),
      series: ledger.series ? {
        id: ledger.series.id,
        started_clock: ledger.series.started_clock,
        prior_evidence: seriesPrior,
        provenance: ledger.series.provenance
      } : null,
      aggregate: ledger.aggregate,
      aggregate_known: ledger.aggregate_known,
      prior_history_complete: false,
      records: ledger.records.map(function (r) {
        return { seq: r.seq, clock: r.clock, document: r.document, symbol: r.symbol, outcome: r.outcome };
      }),
      history_truncated: ledger.truncated,
      history_limit: LEDGER_MAX,
      degraded: ledger.degraded
        ? { reasons: ledger.degraded.reasons.slice(), at_clock: ledger.degraded.at_clock }
        : null,
      uncertainty: {
        storage: ledger.unc.storage,
        parse: ledger.unc.parse,
        reset: ledger.unc.reset,
        loss: ledger.unc.loss,
        concurrent_writer: ledger.unc.concurrent_writer
      },
      writer: { exclusive_proven: false, instance: instanceId, generation: ledger.gen }
    };
  }

  function publishLedgerSnapshot() {
    try {
      var snapshot = freezeDeep(snapshotState());
      window.__dqAttemptLedger = Object.freeze({ snapshot: function () { return snapshot; } });
      if (stamp) stamp.setAttribute('data-dq-accounting', JSON.stringify(snapshot));
    } catch (e) { /* diagnostics must never block quoting */ }
  }

  try { initLedger(); } catch (e) {
    // The same rule as everywhere else: a broken ledger must not take the
    // quote it is observing down with it.
    try { ledger.unc.storage = true; degrade('storage'); } catch (e2) { /* stay quiet */ }
  }

  publishLedgerSnapshot();

  // Bilingual pairs. The page ships both strings and CSS reveals one, so a
  // JS-written label must set BOTH or the other language silently keeps the
  // previous text.
  var LABELS = {
    live: ['Live', '实时'],
    delayed: ['Delayed', '延迟'],
    pre: ['Pre-market', '盘前'],
    post: ['After hours', '盘后'],
    closed: ['Closed', '已收盘'],
    // Currency LAPSED after we had it. Plain words, no internal state name.
    lapsed: ['Not updating', '暂停更新']
  };

  // Whether this page has ever painted a measured quote. A stale reading is
  // handled differently before and after that: before, the baked stamp already
  // names its own build date and is honest as-is; after, the stamp is making a
  // live-or-delayed claim that has since lapsed and MUST be demoted.
  var painted = false;

  function fmtPrice(v) { return Number(v).toFixed(2); }

  function fmtAbs(v) {
    var n = Number(v);
    return (n < 0 ? '-' : '+') + '$' + Math.abs(n).toFixed(2);
  }

  function fmtPct(v) {
    var n = Number(v);
    return (n < 0 ? '-' : '+') + Math.abs(n).toFixed(2) + '%';
  }

  function setBilingual(el, en, zh) {
    if (!el) return;
    var enNode = el.querySelector('.l-en');
    var zhNode = el.querySelector('.l-zh');
    if (enNode) enNode.textContent = en;
    if (zhNode) zhNode.textContent = zh;
    // A stamp rendered without the bilingual spans still gets an honest label
    // rather than keeping a stale one.
    if (!enNode && !zhNode) el.textContent = en;
  }

  function isFiniteNumber(v) { return typeof v === 'number' && isFinite(v); }

  function clearExtended(expired) {
    extendedQuote = null;
    if (expiryTimer !== null) clearTimeout(expiryTimer);
    expiryTimer = null;
    if (extendedValues) extendedValues.hidden = true;
    if (extendedStatus) extendedStatus.hidden = false;
    var fields = [extendedSession, extendedPrice, extendedAbs, extendedPct, extendedReference, extendedAge];
    for (var i = 0; i < fields.length; i++) setBilingual(fields[i], '', '');
    if (extendedRow) {
      extendedRow.setAttribute('data-dq-state', expired ? 'stale' : 'unavailable');
      extendedRow.classList.remove('pos', 'neg');
    }
    setBilingual(extendedStatus,
      expired ? 'Extended quote expired. Showing the regular quote.' : 'Extended quote unavailable. Showing the regular quote.',
      expired ? '盘前盘后报价已过期，现显示常规时段报价。' : '盘前盘后报价暂不可用，现显示常规时段报价。');
  }

  function validExtended(q, now) {
    if (!q || !isFiniteNumber(q.price) || q.price <= 0 || q.currency !== 'USD' ||
        !isFiniteNumber(q.change_abs) || !isFiniteNumber(q.change_pct) ||
        (q.print_session !== 'pre' && q.print_session !== 'post') || q.market_session !== q.print_session ||
        (q.freshness !== 'live' && q.freshness !== 'delayed') ||
        !isFiniteNumber(q.as_of_ms) || q.as_of_ms <= 0 || q.as_of_ms > now ||
        !isFiniteNumber(q.valid_until_ms) || q.valid_until_ms < q.as_of_ms ||
        q.valid_until_ms > q.as_of_ms + 120000 || now >= q.valid_until_ms) return false;
    var ref = q.completed_regular_reference;
    if (!ref || !isFiniteNumber(ref.price) || ref.price <= 0 ||
        typeof ref.session_date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(ref.session_date)) return false;
    var date = new Date(ref.session_date + 'T00:00:00Z');
    if (!isFiniteNumber(date.getTime()) || date.toISOString().slice(0, 10) !== ref.session_date) return false;
    return Math.abs(q.change_abs - (q.price - ref.price)) < 0.000001 &&
      Math.abs(q.change_pct - (q.price - ref.price) / ref.price * 100) < 0.000001;
  }

  function tickExtended() {
    if (!extendedQuote) return;
    var now = Date.now();
    if (!validExtended(extendedQuote, now)) { clearExtended(true); return; }
    var seconds = Math.floor((now - extendedQuote.as_of_ms) / 1000);
    var delayed = extendedQuote.freshness === 'delayed';
    setBilingual(extendedAge,
      (delayed ? 'Delayed · ' : '') + 'Observed ' + seconds + 's ago',
      (delayed ? '延迟 · ' : '') + '观测于' + seconds + '秒前');
    // This deadline comes from the server's calendar, never receipt time.
    if (expiryTimer === null) expiryTimer = setTimeout(function () {
      clearExtended(true);
    }, Math.max(0, extendedQuote.valid_until_ms - now));
  }

  function paintExtended(q) {
    if (!extendedRow) return;
    clearExtended(false);
    extendedRow.hidden = q.session === 'regular';
    var ext = q.extended_quote;
    if (!validExtended(ext, Date.now())) return;
    extendedQuote = ext;
    extendedRow.hidden = false;
    extendedRow.setAttribute('data-dq-state', 'current');
    extendedRow.classList.toggle('pos', ext.change_abs >= 0);
    extendedRow.classList.toggle('neg', ext.change_abs < 0);
    if (extendedValues) extendedValues.hidden = false;
    if (extendedStatus) extendedStatus.hidden = true;
    var label = LABELS[ext.print_session];
    setBilingual(extendedSession, label[0], label[1]);
    if (extendedPrice) extendedPrice.textContent = '$' + fmtPrice(ext.price);
    if (extendedAbs) extendedAbs.textContent = fmtAbs(ext.change_abs);
    if (extendedPct) extendedPct.textContent = fmtPct(ext.change_pct);
    var ref = ext.completed_regular_reference;
    setBilingual(extendedReference,
      'vs regular close $' + fmtPrice(ref.price) + ' · ' + ref.session_date,
      '较常规时段收盘 $' + fmtPrice(ref.price) + ' · ' + ref.session_date);
    tickExtended();
    // Calendar-derived deadline is not a freshness clock. This one-shot clears
    // at the exact session/age boundary even when the next fetch hangs or fails.
  }

  // Which of the five labels this quote earns, and which CSS state paints it.
  // "live" is the only branch that yields a green pulsing pip, and it needs
  // BOTH a measured realtime feed and an open regular session.
  function readingOf(q) {
    if (q.freshness === 'live' && q.session === 'regular') {
      return { state: 'live', label: LABELS.live };
    }
    if (q.session === 'regular') return { state: 'delayed', label: LABELS.delayed };
    if (q.session === 'pre') return { state: 'closed', label: LABELS.pre };
    if (q.session === 'post') return { state: 'closed', label: LABELS.post };
    return { state: 'closed', label: LABELS.closed };
  }

  // Currency has lapsed: keep the numbers, drop the claim. Called for EVERY
  // way a quote can stop arriving — a 200 the server marks stale, a 503, a
  // 429, a dropped connection, an abort — because from the reader's chair
  // those are one situation: the price on screen is no longer being confirmed.
  // Only the 200-stale branch used to demote, so a hub outage (the EXPECTED
  // fault; a hub that stays up and self-reports stale is the rare one) left a
  // pulsing green "Live" on a frozen price indefinitely. Open NVDA at 15:00,
  // hub dies at 15:05, look again at 16:30 and the page still says Live.
  function lapse() {
    clearExtended(false);
    if (!painted || !stamp) return;   // never painted => the baked stamp is already honest
    stamp.setAttribute('data-dq-state', 'closed');
    setBilingual(stamp, LABELS.lapsed[0], LABELS.lapsed[1]);
  }

  function paint(q) {
    // Fail closed on anything we cannot fully render. A partial paint is worse
    // than no paint: it desynchronises the price from the move.
    if (!q || q.ticker !== ticker) { lapse(); return; }
    if (q.freshness === 'stale') { lapse(); return; }
    if (!isFiniteNumber(q.price) || q.price <= 0) { lapse(); return; }
    if (!isFiniteNumber(q.change_abs) || !isFiniteNumber(q.change_pct)) { lapse(); return; }

    var i;
    painted = true;
    for (i = 0; i < priceNodes.length; i++) priceNodes[i].textContent = fmtPrice(q.price);

    if (absNode) absNode.textContent = fmtAbs(q.change_abs);
    if (pctNode) pctNode.textContent = fmtPct(q.change_pct);
    if (chgRow) {
      var up = q.change_abs >= 0;
      chgRow.classList.toggle('pos', up);
      chgRow.classList.toggle('neg', !up);
    }
    var regularDate = q.regular_session_date ? ' · ' + q.regular_session_date : '';
    setBilingual(regularLabel,
      (q.session === 'regular' ? 'Regular session' : 'Regular close') + regularDate,
      (q.session === 'regular' ? '常规时段' : '常规时段收盘') + regularDate);
    paintExtended(q);

    // The 52-week bar moves with the price or the block contradicts itself.
    // Bounds are the BAKED 52w window; a live price outside it clamps to the
    // end rather than overflowing the track — the bar stops being precise at
    // that point, but it is never pointing at the wrong place.
    if (rangeEl && fillEl && dotEl) {
      var lo = parseFloat(rangeEl.getAttribute('data-dq-lo'));
      var hi = parseFloat(rangeEl.getAttribute('data-dq-hi'));
      if (isFiniteNumber(lo) && isFiniteNumber(hi) && hi > lo) {
        var pos = Math.max(0, Math.min(100, (q.price - lo) / (hi - lo) * 100));
        fillEl.style.width = pos.toFixed(1) + '%';
        dotEl.style.left = pos.toFixed(1) + '%';
      }
    }

    if (stamp) {
      var reading = readingOf(q);
      var en = reading.label[0];
      var zh = reading.label[1];
      // Outside an open regular session the move belongs to a NAMED past
      // session — upstream can even hand back the previous session's move
      // before an open — so the reader is told which date they are reading.
      if (reading.state !== 'live' && q.session !== 'regular' && q.regular_session_date) {
        en += ' · ' + q.regular_session_date;
        zh += ' · ' + q.regular_session_date;
      }
      stamp.setAttribute('data-dq-state', reading.state);
      setBilingual(stamp, en, zh);
    }
  }

  function poll() {
    if (inflight || document.hidden) return;
    inflight = true;

    var ctrl = window.AbortController ? new AbortController() : null;
    var settled = false;

    // The watchdog runs with OR without AbortController. Where abort exists it
    // cuts the request; where it does not, it still releases `inflight` and
    // demotes the claim — otherwise a hung fetch never settles, `inflight`
    // stays true, every later tick no-ops, and the stamp is frozen on whatever
    // it last said. A silently dead poller wearing a green "Live" is the same
    // lie as a dead feed wearing one.
    var killer = setTimeout(function () {
      if (settled) return;
      settled = true;
      if (ctrl) { try { ctrl.abort(); } catch (e) { /* already gone */ } }
      inflight = false;
      lapse();
      try { settleAttempt(attempt, 'timeout'); } catch (e) { /* accounting stays best-effort */ }
    }, TIMEOUT_MS);

    function done() {
      if (settled) return true;
      settled = true;
      clearTimeout(killer);
      inflight = false;
      return false;
    }

    var pending;
    // Exactly at the invocation boundary: setup failures above are not fetches.
    var attempt = null;
    try { attempt = beginAttempt(ticker); } catch (e) { /* counting cannot block fetch */ }
    try {
      pending = fetch('/api/dossier-quote/' + encodeURIComponent(ticker), {
        signal: ctrl ? ctrl.signal : undefined,
        credentials: 'omit',
        headers: { Accept: 'application/json' }
      });
    } catch (e) {
      // The fetch threw before originating. This used to be left for the
      // watchdog to trip over 6s later; naming it now keeps the record honest
      // (it really was an attempt) and frees the poller immediately.
      done();
      lapse();
      try { settleAttempt(attempt, 'sync-error'); } catch (e2) { /* best-effort */ }
      return;
    }

    pending
      .then(function (r) { return r.ok ? r.json() : null; })
      // A non-200 (503 hub down, 429 throttled) and a thrown fetch (offline,
      // abort) are the same fact to a reader: this price is no longer being
      // confirmed. Both demote the claim and keep the numbers.
      .then(function (q) {
        if (done()) return;   // a late response after a timeout is NOT a second attempt
        try { settleAttempt(attempt, q ? 'response' : 'http-error'); } catch (e) { /* best-effort */ }
        if (q) { paint(q); } else { lapse(); }
      })
      .catch(function () { if (done()) return; lapse();
        try { settleAttempt(attempt, 'reject'); } catch (e) { /* best-effort */ }
      });
  }

  // Always attempt an immediate read, then ensure the interval exists. The
  // earlier `if (timer) return` shape stranded one real case: a dossier opened
  // in a BACKGROUND tab installs the timer while hidden, every tick no-ops on
  // the hidden check, and the reveal then found the timer already set and
  // returned — leaving the baked price on screen for up to a full poll period
  // at the exact moment the reader first looked at it. poll() is itself
  // guarded on `inflight` and `document.hidden`, so calling it here is cheap
  // and safe.
  function start() {
    tickExtended();
    poll();
    if (!timer) timer = setInterval(poll, POLL_MS);
    if (!clockTimer) clockTimer = setInterval(tickExtended, 1000);
  }

  function stop() {
    if (clockTimer) clearInterval(clockTimer);
    clockTimer = null;
    if (expiryTimer !== null) clearTimeout(expiryTimer);
    expiryTimer = null;
    if (!timer) return;
    clearInterval(timer);
    timer = null;
  }

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) stop(); else start();
  });

  start();
})();
