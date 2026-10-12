/* Make the dashboard's data tables behave like a screener: click any column
   header to sort, and tables long enough to scroll get a live filter box.

   Zero-config: it auto-enhances every real data table on the page and SKIPS the
   little tables that live inside hover tooltips (.tip). Numeric columns are
   detected automatically; cells whose visible text isn't a clean number (heat
   bars, badges) carry an explicit data-sort key. Self-contained, no deps. */
(function () {
  function txt(cell) {
    if (cell.dataset && cell.dataset.sort !== undefined) return cell.dataset.sort;
    return (cell.textContent || '').trim();
  }
  // tokens that mean "no value here" — shared by classification and sorting
  function isMissing(v) {
    return v === '' || v === '—' || v === '–' || v === '-' || v === '--' ||
           v === 'n/a' || v === 'N/A' || v === '…';
  }
  // One anchored grammar for a display number: optional comparator (~, ≈, ≥…),
  // optional sign, optional currency (US$1.2B keeps its scale), mantissa,
  // optional exponent (data-sort machine keys like 1.2e9), optional scale
  // suffix (K/M/B/T/bn/mn/tn/万/亿/万亿; bare lowercase m/b/t only with a
  // currency, so "5m" stays a duration), optional unit suffix (% × bp pt σ…).
  // Anything else is text — no partial guesses: "0700.HK", "2024-01-05",
  // "1.2.3", "12abc" all fail here.
  var NUM_RE = /^([<>≤≥~≈])?([+\-])?(US\$|HK\$|CA\$|C\$|A\$|S\$|\$|¥|€|£)?([+\-])?(\d+(?:\.\d+)?|\.\d+)([eE][+-]?\d+)?\s*(万亿|bn|mn|tn|[KkMBT]|万|亿|[mbt])?\s*(bps|bp|pts|pt|pp|%|×|[xX]|σ|d)?$/;
  var SCALES = { K: 1e3, k: 1e3, M: 1e6, B: 1e9, T: 1e12,
                 bn: 1e9, mn: 1e6, tn: 1e12, '万': 1e4, '亿': 1e8, '万亿': 1e12,
                 m: 1e6, b: 1e9, t: 1e12 };
  // parse a number out of "≥ US$1.2B", "(12.5%)", "−3.0%", "9,800万" → finite number | null
  function num(s) {
    if (s == null) return null;
    s = String(s).trim();
    s = s.replace(/−/g, '-').replace(/[   ]/g, ''); // U+2212 minus; NBSP/narrow/thin spaces
    s = s.replace(/(\d),(?=\d{3}\b)/g, '$1');       // thousands commas only
    var acc = /^\((.+)\)$/.exec(s);                 // accounting negative: (12.5%) → -12.5
    if (acc) {
      if (/[+\-]/.test(acc[1])) return null;        // inner text must carry no sign of its own
      var inner = num(acc[1]);
      return inner === null ? null : -inner;
    }
    var m = NUM_RE.exec(s);
    if (!m) return null;
    if (m[2] && m[4]) return null;                  // at most one sign, before or after the currency
    if (!m[3] && (m[7] === 'm' || m[7] === 'b' || m[7] === 't')) return null; // "5m" is not money
    var n = parseFloat(m[5] + (m[6] || ''));
    if (!isFinite(n)) return null;
    if (m[2] === '-' || m[4] === '-') n = -n;
    if (m[7]) n *= SCALES[m[7]];
    return isFinite(n) ? n : null;
  }
  function headerRow(table) {
    // a real <thead> wins; otherwise the first tbody row is the header (legacy tables)
    return (table.tHead && table.tHead.rows[0]) || (table.tBodies[0] && table.tBodies[0].rows[0]);
  }
  function dataRows(table) {
    var body = table.tBodies[0];
    if (!body) return [];
    var rows = Array.prototype.slice.call(body.rows);
    return table.tHead ? rows : rows.slice(1); // <thead> → every tbody row is data; else row 0 is the header
  }
  function isNumericCol(rows, i) {
    var seen = 0;
    for (var k = 0; k < rows.length; k++) {
      var c = rows[k].cells[i];
      if (!c) continue;
      var v = txt(c);
      if (isMissing(v)) continue; // blanks ok
      if (num(v) === null) return false;
      seen++;
    }
    return seen > 0;
  }

  function sortBy(table, i, dir) {
    var body = table.tBodies[0];
    var rows = dataRows(table);
    var numeric = isNumericCol(rows, i);
    rows.sort(function (a, b) {
      var ca = a.cells[i], cb = b.cells[i];
      var va = ca ? txt(ca) : '', vb = cb ? txt(cb) : '';
      if (numeric) {
        var na = num(va), nb = num(vb);
        if (na === null && nb === null) return 0; // both missing keep prior order
        if (na === null) return 1;                // missing sinks to the END in both directions
        if (nb === null) return -1;
        return na === nb ? 0 : dir * (na - nb);   // equal keys keep prior order (stable sort)
      }
      var ka = isMissing(va), kb = isMissing(vb);
      if (ka || kb) {
        if (ka && kb) return 0;
        return ka ? 1 : -1;                       // missing last in both directions
      }
      return dir * va.localeCompare(vb, undefined, { numeric: true, sensitivity: 'base' });
    });
    rows.forEach(function (r) { body.appendChild(r); }); // header stays at index 0
  }

  function isRowish(n) {
    return !!n && n.nodeType === 1 && (n.tagName === 'TR' || n.tagName === 'TBODY');
  }

  function enhance(table) {
    var header = headerRow(table);
    if (!header) return;
    var rows = dataRows(table);
    var sortObserver = null;
    var applyFilter = null;

    Array.prototype.forEach.call(header.cells, function (th, i) {
      th.classList.add('th-sort');
      if (!th.hasAttribute('tabindex')) th.setAttribute('tabindex', '0'); // keyboard-reachable, keep a preset value
      if (th.tagName === 'TD' && !th.hasAttribute('role')) th.setAttribute('role', 'columnheader'); // legacy TD headers
      var arrow = document.createElement('span');
      arrow.className = 'sarrow';
      arrow.textContent = '↕';
      arrow.setAttribute('aria-hidden', 'true'); // the arrow is decoration; the aria-sort on the cell is the truth
      var help = th.querySelector('.help');
      if (help) th.insertBefore(arrow, help); else th.appendChild(arrow);

      // one activation body shared by mouse and keyboard (site20 S2-02)
      function activate() {
        var cur = th.getAttribute('data-dir');
        var dir = cur ? (cur === 'desc' ? 1 : -1)
                      : (isNumericCol(dataRows(table), i) ? -1 : 1); // numeric → high-first (live rows)
        Array.prototype.forEach.call(header.cells, function (o) {
          o.removeAttribute('data-dir'); o.classList.remove('sorted');
          o.removeAttribute('aria-sort'); // exactly one announced sort column, never "none"
          var a = o.querySelector('.sarrow'); if (a) a.textContent = '↕';
        });
        th.setAttribute('data-dir', dir === -1 ? 'desc' : 'asc');
        th.setAttribute('aria-sort', dir === -1 ? 'descending' : 'ascending');
        th.classList.add('sorted');
        arrow.textContent = dir === -1 ? '↓' : '↑';
        sortBy(table, i, dir);
        if (sortObserver) sortObserver.takeRecords(); // our own re-order is not a population change
      }

      th.addEventListener('click', function (e) {
        if (e.target.closest('.help')) return; // let tooltips be tooltips
        activate();
      });
      th.addEventListener('keydown', function (e) {
        if (e.target !== th) return; // focus on the header itself, never on a child (.help, link, input)
        if (e.altKey || e.ctrlKey || e.metaKey) return;
        if (e.key !== 'Enter' && e.key !== ' ' && e.key !== 'Spacebar') return;
        e.preventDefault(); // Space must not scroll the page
        activate();
      });
    });

    // rows appended or replaced after hydration (live refreshes): keep the active
    // sort and filter pointed at the LIVE population — one observer per table
    if (typeof MutationObserver === 'function') {
      sortObserver = new MutationObserver(function (records) {
        var population = false;
        for (var k = 0; k < records.length && !population; k++) {
          var rec = records[k];
          if (rec.type !== 'childList') continue;
          var t = rec.target;
          // the table's own rows only: direct children of the table (a tbody
          // swap) or of its tbody; nested tooltip tables, cell rewrites and
          // attribute changes are not population changes
          if (!(t === table || (t.tagName === 'TBODY' && t.parentNode === table))) continue;
          population = Array.prototype.some.call(rec.addedNodes, isRowish) ||
                       Array.prototype.some.call(rec.removedNodes, isRowish);
        }
        if (!population) return;
        var head = headerRow(table);
        if (head) {
          for (var ci = 0; ci < head.cells.length; ci++) {
            var d = head.cells[ci].getAttribute('data-dir');
            if (d) { sortBy(table, ci, d === 'desc' ? -1 : 1); break; } // sort survives a refresh
          }
        }
        if (applyFilter) applyFilter(true); // population changed: status written immediately
        sortObserver.takeRecords(); // drop the records our own re-sort just produced
      });
      sortObserver.observe(table, { childList: true, subtree: true });
    }

    // long tables get a live filter box
    if (rows.length >= 12) applyFilter = addFilter(table);
  }

  function addFilter(table) {
    var wrap = document.createElement('div');
    wrap.className = 'tbl-filter';
    var input = document.createElement('input');
    input.type = 'search';
    input.placeholder = 'Filter…';
    input.setAttribute('aria-label', 'Filter table rows');
    var cnt = document.createElement('span');
    cnt.className = 'cnt';
    cnt.setAttribute('role', 'status');     // screen readers announce the count (site20 S2-04)
    cnt.setAttribute('aria-atomic', 'true');
    wrap.appendChild(input); wrap.appendChild(cnt);
    // if the table is inside a horizontal-scroll wrapper (theme.js wrapTables), put the
    // filter ABOVE the wrapper so it stays fixed while the table scrolls sideways
    var anchor = (table.parentNode && table.parentNode.classList.contains('tbl-scroll'))
      ? table.parentNode : table;
    anchor.parentNode.insertBefore(wrap, anchor);

    // one status writer, fed by the LIVE population at call time. Typing defers it
    // by a single trailing 250 ms debounce; every other path (reset, langchange,
    // population re-apply, init) writes immediately and cancels the pending timer.
    var statusTimer = null;
    var resetBtn = document.createElement('button');
    resetBtn.type = 'button';
    resetBtn.className = 'gbtn gbtn-sm gbtn-quiet';
    resetBtn.setAttribute('data-tablesort-reset', '1');
    // localized at creation: theme.js sets data-lang in <head> without a
    // langchange, so a returning zh user must not wait for an event (site20 S2 r5)
    resetBtn.textContent = isZh() ? '清除筛选' : 'Clear filter';

    function isZh() {
      return document.documentElement.getAttribute('data-lang') === 'zh';
    }
    function liveCount() {
      var q = input.value.trim().toLowerCase();
      var rows = dataRows(table); // the LIVE population — rows can appear and disappear
      var shown = 0;
      rows.forEach(function (r) {
        if (!q || (r.textContent || '').toLowerCase().indexOf(q) !== -1) shown++;
      });
      return {q: q, shown: shown, total: rows.length};
    }
    function statusText(st) {
      if (!st.q) return '';
      if (!st.total) return isZh() ? '暂无可筛选的行' : 'No rows to filter';
      if (st.shown >= 1) return st.shown + ' / ' + st.total;
      return (isZh() ? '无匹配行 · 0 / ' : 'No matching rows · 0 / ') + st.total;
    }
    function writeStatus() {
      if (statusTimer !== null) { clearTimeout(statusTimer); statusTimer = null; }
      var st = liveCount();
      cnt.textContent = statusText(st);
      // the reset affordance exists ONLY in the noMatch state — attached after the
      // count span while needed, removed the moment any row is shown again
      if (st.q && st.total > 0 && st.shown === 0) {
        if (!resetBtn.parentNode) wrap.appendChild(resetBtn);
      } else if (resetBtn.parentNode) {
        resetBtn.remove();
      }
    }
    resetBtn.addEventListener('click', function () {
      input.value = '';
      input.focus(); // focus FIRST, then re-apply
      apply(true);
    });

    function apply(immediate) {
      var rows = dataRows(table); // the LIVE population — rows can appear and disappear
      var q = input.value.trim().toLowerCase();
      var shown = 0;
      rows.forEach(function (r) {
        var hit = !q || (r.textContent || '').toLowerCase().indexOf(q) !== -1;
        // touch only rows this filter hid itself (marked): a row the PAGE hid
        // inline is never un-hidden by a re-apply (site20 S2 r5)
        if (hit) {
          if (r.hasAttribute('data-tablesort-hidden')) {
            r.style.display = '';
            r.removeAttribute('data-tablesort-hidden');
          }
          shown++;
        } else if (r.style.display !== 'none') {
          r.style.display = 'none';
          r.setAttribute('data-tablesort-hidden', '1');
        }
      });
      if (immediate) { writeStatus(); return; }
      // rows update now; the announcement trails the typing by one debounce
      if (statusTimer !== null) clearTimeout(statusTimer);
      statusTimer = setTimeout(function () { statusTimer = null; writeStatus(); }, 250);
    }
    input.addEventListener('input', function () { apply(false); });
    filterCtrls.push({
      onLang: function () { // rewrite copy in place, no re-typing, no debounce
        resetBtn.textContent = isZh() ? '清除筛选' : 'Clear filter';
        writeStatus();
      }
    });
    writeStatus(); // initialization writes immediately
    return apply;
  }

  // one registry + one module-scope listener (site20 S2-04): a language flip
  // rewrites every filter's status text and reset label immediately. PR 7502's
  // own copy refresh is a separate listener and coexists with this one.
  var filterCtrls = [];
  document.addEventListener('langchange', function () {
    filterCtrls.forEach(function (c) { c.onLang(); });
  });

  function initAll() {
    Array.prototype.forEach.call(document.querySelectorAll('table'), function (t) {
      if (t.closest('.tip')) return;           // skip tooltip tables
      if (t.classList && t.classList.contains('sb-table')) return; // self-managed screener (own sort/toggle)
      if (t.classList && t.classList.contains('st-table')) return; // StockTable (own sort/filter/cols)
      if (dataRows(t).length < 2) return;       // nothing to sort
      if (t.getAttribute('data-tablesort') === '1') return; // already enhanced (script loaded twice)
      t.setAttribute('data-tablesort', '1');
      enhance(t);
    });
  }
  // run now if the DOM is already parsed (script added late / bfcache), else wait
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initAll);
  else initAll();
})();
