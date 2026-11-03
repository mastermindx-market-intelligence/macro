/* sector_cycles_platform.js — SC_PLATFORM seam 'sc-platform.v1' (programme 7646, lane L3).
 * Sector Central carrier platform for the Cycles view: the mobile scope class (.sc-plat, styled by
 * sector_cycles_platform.css), arrow-key roving inside the five keyboard zones, the one polite live
 * region (#sc-sr-status, never a second) and focus return. No fetch, no clock, no copy of its own:
 * every string it announces is handed in by the renderer, which owns the deck pairs. */
(function (root) {
  'use strict';
  var SC_PLATFORM = { version: 'sc-platform.v1' };
  /* Keyboard journey, in DOM order: phase chips -> sector list -> turn markers -> inspector -> compare. */
  var ZONES = [
    ['chips', '#sc-groups .cyc-gchip, #sc-gall'],
    ['list', '#sc-chips .cyc-chip, #sc-baskets .sc-bchip, .sc-series-btn'],
    ['markers', '#sc-turnrail .sc-turn-mk'],
    ['inspector', '#sc-panel-focus button, #sc-panel-focus a[href], #sc-panel-focus summary'],
    ['compare', '#sc-compare button']
  ];
  var NEXT = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
  var _api = null, _opener = null, _seq = 0;
  SC_PLATFORM.zones = ZONES;

  function shown(el) { return !!el && !el.disabled && !el.hidden && el.getClientRects().length > 0; }
  function zoneOf(el) {
    for (var i = 0; i < ZONES.length; i++) if (el && el.matches && el.matches(ZONES[i][1])) return i;
    return -1;
  }
  function items(host, z) {
    var out = [], all = host.querySelectorAll(ZONES[z][1]), i;
    for (i = 0; i < all.length; i++) if (shown(all[i])) out.push(all[i]);
    return out;
  }
  function detailOpen() {
    var d = root.document.getElementById('sc-detail');
    return !!d && (d.classList.contains('sc-sheet-half') || d.classList.contains('sc-sheet-full') || d.classList.contains('expanded'));
  }

  /* Mobile scope: the renderer already runs its sheet / picker / full-screen chrome on the carrier;
     this only opts the carrier into the .sc-plat rules. It never adds sc-china (INTL keeps its own). */
  SC_PLATFORM.initMobile = function (host, api) {
    if (!host) return null;
    _api = api || _api;
    host.classList.add('sc-plat');
    root.document.documentElement.classList.add('sc-plat');
    return { scope: 'sc-plat' };
  };

  SC_PLATFORM.initKeyboard = function (host, api) {
    if (!host || host.__scPlatKeys) return null;
    host.__scPlatKeys = true;
    _api = api || _api;
    host.addEventListener('keydown', function (e) {
      var t = e.target, z, list, i, n;
      if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
      if (e.key === 'Escape') {
        if (root.document.querySelector('.sc-chartwrap.sc-fs')) return;   // the renderer closes full-screen first
        if (_api && _api.closeDetail && detailOpen()) {
          e.preventDefault(); _api.closeDetail();
          SC_PLATFORM.returnFocus(_opener);
        }
        return;
      }
      z = zoneOf(t);
      if (z < 0) return;
      if (e.key === 'Enter' || e.key === ' ') { _opener = t; return; }   // native activation stays the button's
      list = items(host, z);
      i = list.indexOf(t);
      if (i < 0 || !list.length) return;
      if (NEXT[e.key]) n = (i + NEXT[e.key] + list.length) % list.length;
      else if (e.key === 'Home') n = 0;
      else if (e.key === 'End') n = list.length - 1;
      else return;
      e.preventDefault();
      list[n].focus();
    });
    host.addEventListener('click', function (e) {
      var t = e.target && e.target.closest ? e.target.closest('button') : null;
      if (t && zoneOf(t) >= 0) _opener = t;
    });
    return { zones: ZONES.length };
  };

  /* The single polite live region. Cleared first, set on the next tick, so a repeated message re-reads. */
  SC_PLATFORM.announce = function (msg) {
    var node = root.document.getElementById('sc-sr-status'), my = ++_seq;
    if (!node || msg == null) return false;
    node.textContent = '';
    root.setTimeout(function () { if (my === _seq) node.textContent = String(msg); }, 40);
    return true;
  };

  SC_PLATFORM.returnFocus = function (el) {
    if (!el || !el.isConnected || !el.focus) return false;
    try { el.focus({ preventScroll: true }); } catch (e) { el.focus(); }
    return true;
  };

  root.SC_PLATFORM = SC_PLATFORM;
})(typeof window !== 'undefined' ? window : this);
