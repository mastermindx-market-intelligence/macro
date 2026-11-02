// Immutable Macro consumer excerpt at 51f0ac98e5e33498af86fd1d55bcec52634ee2fc.
  var SD_MARKETS = [['us', 'mktUs'], ['cn', 'mktCn'], ['hk', 'mktHk'], ['ca', 'mktCa'], ['global', 'mktGlobal']];
  var SD_TRADES = [['stocks', 'trStocks'], ['options', 'trOptions'], ['crypto', 'trCrypto']];
  var LS_PENDING_PREFS = 'mm.pendingPrefs';
  var _sdDesk = null;            // { market_focus:[], trade_types:[] } — live edit buffer
  var _sdDeskTimer = null;

  function _sdPendingPrefs() {
    try { var o = JSON.parse(localStorage.getItem(LS_PENDING_PREFS) || 'null'); return (o && typeof o === 'object') ? o : null; } catch (e) { return null; }
  }
  function _sdArr(v) {
    if (!v || Object.prototype.toString.call(v) !== '[object Array]') return [];
    var out = []; for (var i = 0; i < v.length; i++) if (typeof v[i] === 'string' && out.indexOf(v[i]) === -1) out.push(v[i]);
    return out;
  }
  // account first, then the pre-sign-up stash — a signed-in user's server answer wins
  function _sdLoadDesk() {
    var meta = (_curUser && _curUser.user_metadata) || {};
    var pend = _sdPendingPrefs() || {};
    var mf = _sdArr(meta.market_focus), tt = _sdArr(meta.trade_types);
    if (!mf.length) mf = _sdArr(pend.market_focus);
    if (!tt.length) tt = _sdArr(pend.trade_types);
    _sdDesk = { market_focus: mf, trade_types: tt };
    return _sdDesk;
  }
  // Local mirror always; the account too when there is one. The local write
  // MERGES into the existing stash so it never drops the name signup put there.
  /* Canonical market preference derived from the desk chips.

     The Terminal (charting-app terminal/lib/markets.ts) reads
     `user_metadata.markets = {home, enabled[], autoNarrowed}` and treats an
     explicit `markets` object as authoritative over `market_focus` — otherwise a
     preference narrowed in settings would be reverted on every load by the
     signup-time array. So writing ONLY market_focus here would be silently
     ignored by the Terminal for any user who has ever set their markets over
     there. One writer, one shape: every desk save emits both.

     `autoNarrowed` is false on this path by design. That flag exists to explain
     a narrowing WE chose for a US-only signup ("other markets start hidden");
     a choice the user just made by hand needs no explanation. */
  function _sdMarketsFromChips(mf) {
    var ALL = ['us', 'cn', 'hk', 'ca', 'intl', 'crypto'];
    var picks = [], global = false;
    for (var i = 0; i < (mf || []).length; i++) {
      if (mf[i] === 'global') { global = true; continue; }
      if (mf[i] === 'us' || mf[i] === 'cn' || mf[i] === 'hk' || mf[i] === 'ca') picks.push(mf[i]);
    }
    if (global || !picks.length) return { home: picks[0] || null, enabled: ALL.slice(), autoNarrowed: false };
    // Crypto rides along regardless: it is an asset class, not a country market,
    // and dropping BTC because someone follows only US equities would be a bug.
    var enabled = picks.slice(); enabled.push('crypto');
    var canon = [];
    for (var j = 0; j < ALL.length; j++) if (enabled.indexOf(ALL[j]) > -1) canon.push(ALL[j]);
    return { home: picks[0], enabled: canon, autoNarrowed: false };
  }

  function _sdSaveDesk(msgEl) {
    clearTimeout(_sdDeskTimer);
    var signedIn = !!(_curUser && _authEnabled && _curUser.email);
    _sdDeskTimer = setTimeout(function () {
      var payload = {
        market_focus: _sdDesk.market_focus,
        trade_types: _sdDesk.trade_types,
        markets: _sdMarketsFromChips(_sdDesk.market_focus)
      };
      try {
        var pend = _sdPendingPrefs() || {};
        pend.market_focus = payload.market_focus; pend.trade_types = payload.trade_types;
        localStorage.setItem(LS_PENDING_PREFS, JSON.stringify(pend));
      } catch (e) {}
      if (!signedIn) { _sdDeskMsg(msgEl, 'prefLocal', 'ok'); return; }
      getSupabaseClient().then(function (sb) {
        if (!sb || !_curUser) { _sdDeskMsg(msgEl, 'prefLocal', 'ok'); return null; }
        return sb.auth.updateUser({ data: payload }).then(function (r) {
          if (r && r.error) { _sdDeskMsg(msgEl, 'prefErr', 'err'); return; }
          // keep the in-memory user in step so a re-render shows the saved answer
          if (_curUser) {
            _curUser.user_metadata = _curUser.user_metadata || {};
            _curUser.user_metadata.market_focus = payload.market_focus;
            _curUser.user_metadata.trade_types = payload.trade_types;
            _curUser.user_metadata.markets = payload.markets;
          }
          // Re-fold the country menus without a reload — the home market may have
          // just changed, and a nav that still shows the old one reads as a bug.
          try { window.dispatchEvent(new CustomEvent('mdx-auth', { detail: { user: _curUser, event: 'PREFS_SAVED' } })); } catch (e) {}
          _sdDeskMsg(msgEl, 'prefSaved', 'ok');
        });
      }).catch(function () { _sdDeskMsg(msgEl, 'prefErr', 'err'); });
    }, 500);
  }
