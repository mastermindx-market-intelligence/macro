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
    }, TIMEOUT_MS);

    function done() {
      if (settled) return true;
      settled = true;
      clearTimeout(killer);
      inflight = false;
      return false;
    }

    fetch('/api/dossier-quote/' + encodeURIComponent(ticker), {
      signal: ctrl ? ctrl.signal : undefined,
      credentials: 'omit',
      headers: { Accept: 'application/json' }
    })
      .then(function (r) { return r.ok ? r.json() : null; })
      // A non-200 (503 hub down, 429 throttled) and a thrown fetch (offline,
      // abort) are the same fact to a reader: this price is no longer being
      // confirmed. Both demote the claim and keep the numbers.
      .then(function (q) { if (done()) return; if (q) { paint(q); } else { lapse(); } })
      .catch(function () { if (done()) return; lapse(); });
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
