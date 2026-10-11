/* portfolio_state.js — the ONE private authority computation for "what is the canonical
   Portfolio, right now". DOM-free, pure, node-exported (typeof module guard — the
   risk_core.js / market_books.js idiom) so the state law can be pinned without a browser.

   Computes the private `portfolio_snapshot.v1` object — see
   research/market_os/MASTERMIND_MARKET_OS_ARCHITECTURE_FREEZE_AND_A1A_COMMISSIONING_2026-08-20.md
   §9-12 (A1A). This object is PRIVATE: never log it, publish it to a public artifact, or
   send it to analytics. It exists so every consumer (the save chip, the holdings table,
   the Book Read, the books strip) reads the SAME authority/population/weighting answer
   instead of each re-deriving its own — which is exactly how a Watchlist name, a pasted
   temporary basket, or a stale local store used to leak into the Portfolio read (Turn 6
   census, defects 1-9; DNR-adjacent record:
   research/market_os/MASTERMIND_MARKET_OS_ARCHITECTURE_FREEZE_AND_A1A_COMMISSIONING_2026-08-20.md).

   AUTHORITY LAW (§10)
     anonymous     -> the local Portfolio is canonical
     authenticated -> the cloud Portfolio is canonical
   On an authenticated cloud failure the caller (watchstore.js) must preserve last-good
   cloud rows (degraded, read-only) or, absent one, pass `rows: null` — never `[]` — so
   this module is not asked to launder "we do not know" into a false zero. This module
   never substitutes one authority's rows for the other's; it only ever describes the
   rows it is given.

   WEIGHTING LAW (§12)
     all unsized                -> equal relative weights, explicitly labeled
     all sized + current-priced -> current-value weights
     all sized + cost-only      -> entry-cost weights, explicitly labeled
     some sized / some unsized  -> abstain (never blend an assumed row into a computed
                                    distribution — that blend is defect #8, "hidden
                                    weighting completion")
     some current / some cost   -> abstain
     different currencies       -> partition before weighting (never a cross-currency
                                    weight map; the caller partitions and calls
                                    computeWeighting per currency/book, e.g. pushFxWeights
                                    and the Book Read's lead-book restriction)
     one (or zero) positions    -> 'insufficient' — no relationship-risk read is possible
                                    or meaningful (§13 "one modeled position -> no
                                    relationship-risk read") */
(function () {
  'use strict';

  function num(v) {
    if (v === '' || v == null) return null;
    var n = Number(v);
    return (typeof n === 'number' && isFinite(n)) ? n : null;
  }

  // ---- population -------------------------------------------------------------
  function openRowsOf(rows) {
    return (rows || []).filter(function (r) { return r && r.ticker && r.status !== 'closed'; });
  }
  function closedRowsOf(rows) {
    return (rows || []).filter(function (r) { return r && r.ticker && r.status === 'closed'; });
  }
  function populationOf(openRows) {
    var n = (openRows || []).length;
    return n === 0 ? 'empty' : (n === 1 ? 'one' : 'many');
  }

  // ---- weighting law (§12) ------------------------------------------------------
  var INSUFFICIENT = {
    state: 'insufficient', eligible: [], excluded: [], weights: {},
    basis: 'none', complete: false, reason: 'no_positions'
  };

  /* priceOf: fn(ticker) -> {price|last,currency}, legacy number, or null.
     A legacy scalar has no monetary unit; raw-price compatibility is preserved.

     PURE over `openRows` — this function never sums across currencies itself. The
     caller may partition markets, but that partition does not prove price units.
     Each chosen current observation must carry its own explicit currency, and
     each chosen entry price its exact stored receipt. The WHOLE monetary cohort
     must qualify before weights; unknown lots never disappear or renormalize. */
  function currencyCode(value) {
    if (typeof value !== 'string' || value === 'XXX' || value === 'XTS') return null;
    try { return Intl.supportedValuesOf('currency').indexOf(value) >= 0 ? value : null; }
    catch (e) { return null; }
  }
  function costCurrency(row) {
    var currency = currencyCode(row.entry_currency), basis = row.entry_currency_basis;
    if (!currency || !basis || typeof basis !== 'object' || Array.isArray(basis) ||
        Object.keys(basis).length !== 2 || !Object.prototype.hasOwnProperty.call(basis,'ticker') ||
        !Object.prototype.hasOwnProperty.call(basis,'price') || basis.ticker !== row.ticker) return null;
    return typeof row.entry_price === 'number' && isFinite(row.entry_price) &&
      typeof basis.price === 'number' && isFinite(basis.price) && basis.price === row.entry_price ? currency : null;
  }
  function currentObservation(value) {
    if (value && typeof value === 'object') {
      var raw = value.price !== undefined ? value.price : value.last;
      return {price:num(raw),currency:currencyCode(value.currency)};
    }
    // Legacy scalar callbacks still supply raw prices, but no money unit.
    return {price:num(value),currency:null};
  }
  function computeRowMoney(row, quote) {
    row = row || {};
    var current = currentObservation(quote), entry = num(row.entry_price);
    var entryUnit = costCurrency(row), shares = num(row.shares);
    var atCost = !(current.price != null && current.price > 0);
    var price = atCost ? entry : current.price;
    var unit = atCost ? entryUnit : current.currency;
    var value = shares != null && shares > 0 && price != null && price > 0 && unit
      ? shares * price : null;
    if (value != null && (!isFinite(value) || value <= 0)) value = null;
    var since = current.currency && current.currency === entryUnit &&
      current.price != null && entry != null && entry !== 0
        ? (current.price - entry) / entry * 100 : null;
    if (since != null && !isFinite(since)) since = null;
    return {value:value,atCost:atCost,currency:unit,since_pct:since};
  }
  function computeWeighting(openRows, priceOf) {
    var rows = (openRows || []).filter(function (r) { return r && r.ticker; });
    if (rows.length < 2) {
      return {
        state: 'insufficient',
        eligible: rows.map(function (r) { return r.ticker; }),
        excluded: [], weights: {}, basis: 'none', complete: false,
        reason: rows.length === 0 ? 'no_positions' : 'single_position'
      };
    }

    var eligible = rows.map(function (r) { return r.ticker; });
    var sized = [], unsized = [];
    rows.forEach(function (r) {
      var sh = num(r.shares);
      if (sh != null && sh > 0) sized.push(r); else unsized.push(r);
    });

    // some sized / some unsized -> abstain. Never average-fill the unsized rows and
    // blend them into the sized ones' distribution (defect #8).
    if (sized.length > 0 && unsized.length > 0) {
      return {
        state: 'mixed_unsized_abstain', eligible: eligible, excluded: [],
        weights: {}, basis: 'none', complete: false, reason: 'mixed_sizing'
      };
    }

    if (unsized.length === rows.length) {
      // The downstream model is keyed by name. Repeated unsized lots do not
      // manufacture a larger assumption for the same name.
      var names = {};
      rows.forEach(function (r) { names[r.ticker] = true; });
      var eq = 100 / Object.keys(names).length;
      var eqWeights = {};
      rows.forEach(function (r) { eqWeights[r.ticker] = eq; });
      return {
        state: 'all_unsized_equal', eligible: eligible, excluded: [],
        weights: eqWeights, basis: 'equal_assumption', complete: true, reason: null
      };
    }

    // Select each complete observation ONCE, retaining its price/unit together.
    var current = [], costOnly = [], noBasis = [];
    rows.forEach(function (r) {
      var observation = currentObservation(priceOf ? priceOf(r.ticker) : null);
      var entry = num(r.entry_price);
      if (observation.price != null && observation.price > 0) current.push({row:r,observation:observation});
      else if (entry != null && entry > 0) costOnly.push({row:r,observation:{price:entry,currency:costCurrency(r)}});
      else noBasis.push(r);
    });

    // sized, but resolves to NO basis at all (no live price, no entry price) for at
    // least one row: cannot honestly weight it, and it must not be silently dropped
    // from `eligible` either — the abstention is the correct disclosure.
    if (noBasis.length > 0) {
      return {
        state: 'mixed_unsized_abstain', eligible: eligible, excluded: [],
        weights: {}, basis: 'none', complete: false, reason: 'unresolved_basis'
      };
    }
    if (current.length > 0 && costOnly.length > 0) {
      return {
        state: 'mixed_price_basis_abstain', eligible: eligible, excluded: [],
        weights: {}, basis: 'none', complete: false, reason: 'mixed_price_basis'
      };
    }

    var allCurrent = current.length === rows.length;
    var basisRows = allCurrent ? current : costOnly;
    var sum = 0, currency = null, reason = null;
    var raw = basisRows.map(function (item) {
      var value = num(item.row.shares) * item.observation.price;
      var unit = item.observation.currency;
      if (!isFinite(value) || value <= 0) reason = 'amount_overflow';
      else if (!unit && reason !== 'amount_overflow') reason = 'currency_unknown';
      else if (currency && unit && unit !== currency && !reason) reason = 'currency_mismatch';
      if (unit) currency = unit;
      sum += value;
      return { t:item.row.ticker,v:value };
    });
    if (!isFinite(sum)) reason = 'amount_overflow';
    if (reason) return {
      state:'monetary_basis_abstain',eligible:eligible,excluded:[],weights:{},
      basis:'none',complete:false,reason:reason
    };
    var weights = {};
    raw.forEach(function (x) { weights[x.t] = (weights[x.t] || 0) + x.v / sum * 100; });

    return {
      state: allCurrent ? 'all_sized_current' : 'all_sized_cost',
      eligible: eligible, excluded: [], weights: weights,
      basis: allCurrent ? 'current_value' : 'entry_cost',
      complete: true, reason: null
    };
  }

  // ---- the snapshot -------------------------------------------------------------
  /* opts:
       rows        raw canonical Portfolio rows, or null when genuinely unknown (a cloud
                    read failed and there is no last-good cache). NEVER pass [] to mean
                    "unknown" — an empty array is a true, honest zero.
       authority   'local' | 'cloud'
       readState   'loading' | 'ready' | 'degraded' | 'error'
       writeState  'clean' | 'saving' | 'saved' | 'failed' | 'offline_readonly'
       lastGoodAt  ISO string or null
       warning     string or null
       priceOf     fn(ticker) -> price | null
       bookOf      fn(ticker) -> a currency/book key (e.g. market_books.js's marketOf).
                    Omit when the caller has already restricted `rows` to one currency —
                    the cross-currency check below is then a (harmless) no-op.
     Returns a FRESH snapshot object every call — never mutated in place, so a caller can
     hold a reference across a render without it moving underneath it. */
  function computeSnapshot(opts) {
    opts = opts || {};
    var authority = opts.authority === 'cloud' ? 'cloud' : 'local';
    var rows = opts.rows;

    if (rows == null) {
      // Genuinely unknown. read_state carries the honesty; population stays inside its
      // frozen enum (empty|one|many has no fourth "unknown" value) — every consumer MUST
      // gate on read_state before trusting population/rows for exactly this reason.
      return {
        schema: 'portfolio_snapshot.v1', authority: authority,
        read_state: opts.readState || 'error', write_state: opts.writeState || 'clean',
        rows: [], open_rows: [], closed_rows: [], population: 'empty',
        last_good_at: opts.lastGoodAt || null, warning: opts.warning || null,
        weighting: INSUFFICIENT
      };
    }

    var open = openRowsOf(rows), closed = closedRowsOf(rows);
    var weighting;
    if (opts.bookOf) {
      var books = {};
      open.forEach(function (r) { books[opts.bookOf(r.ticker)] = 1; });
      var nBooks = Object.keys(books).length;
      if (nBooks > 1) {
        weighting = {
          state: 'cross_currency_partitioned',
          eligible: open.map(function (r) { return r.ticker; }),
          excluded: [], weights: {}, basis: 'none', complete: false,
          reason: 'cross_currency'
        };
      } else {
        weighting = computeWeighting(open, opts.priceOf);
      }
    } else {
      weighting = computeWeighting(open, opts.priceOf);
    }

    return {
      schema: 'portfolio_snapshot.v1', authority: authority,
      read_state: opts.readState || 'ready', write_state: opts.writeState || 'clean',
      rows: rows.slice(), open_rows: open, closed_rows: closed,
      population: populationOf(open),
      last_good_at: opts.lastGoodAt || null, warning: opts.warning || null,
      weighting: weighting
    };
  }

  var API = {
    computeSnapshot: computeSnapshot,
    computeWeighting: computeWeighting,
    computeRowMoney: computeRowMoney,
    openRowsOf: openRowsOf,
    closedRowsOf: closedRowsOf,
    populationOf: populationOf
  };
  if (typeof window !== 'undefined') window.PS = API;

  // Node-test surface: the pure snapshot/weighting core, DOM-free.
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})();
