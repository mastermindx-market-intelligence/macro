/* Prophet checked Save: compose incumbent account lists, never a second store.
   A successful save is ticker membership. No episode/thesis/position is created. */
(function () {
  'use strict';
  var entries = [], active = null, pendingSignIn = null, dialog, content, status;
  // Page-lifetime no-replay guard for an unconfirmed account effect. It stores
  // no source content and never schedules work; closing/reopening is not a retry.
  var unconfirmed = [];
  var serial = 0, queued = false, readinessTimer = null, setupButton = null, setupEntry = null;
  var todayKeys = ['data-today-source-sha256', 'data-today-pair-id', 'data-today-selection-receipt',
    'data-today-roster-size', 'data-today-served', 'data-today-native-state'];
  function words(parent, en, zh) {
    var a = document.createElement('span'), b = document.createElement('span');
    a.className = 'l-en'; b.className = 'l-zh'; a.textContent = en; b.textContent = zh;
    parent.append(a, b); return parent;
  }
  function node(tag, cls, en, zh) {
    var n = document.createElement(tag); n.className = cls || '';
    if (en !== undefined) words(n, en, zh); return n;
  }
  function button(en, zh, action) {
    var n = node('button', 'gbtn', en, zh); n.type = 'button'; n.addEventListener('click', action); return n;
  }
  function session() {
    var store = window.WatchStore;
    return store && store.checkedSession ? store.checkedSession() : {state: 'unavailable', userId: null};
  }
  function stamp(row) {
    var scope = row.closest('#us-standouts,#us-candidate-pool'), today = row.closest('#us-today');
    return (scope ? ['data-source-digest','data-as-of','data-board-asof'].map(function (k) {
      return scope.getAttribute(k) || '';
    }).join('|') : '') + '|' + (today ? todayKeys.map(function (k) { return today.getAttribute(k) || ''; }).join('|') : '');
  }
  function source(row) {
    var details = row.querySelector('.pv-setup-inline'), link = row.querySelector('.pv-setup-stock-link,.stf-tkr,.ucp-identity>a');
    if (!details || !link) return null;
    var holder = details.querySelector('template.pvs-body-source');
    var body = holder ? holder.content.querySelector('.pv-setup-body') : details.querySelector('.pv-setup-body');
    var ticker = details.getAttribute('data-setup-ticker') || row.getAttribute('data-ticker') || '';
    var href = link.getAttribute('href');
    if (!/^[A-Z0-9^][A-Z0-9.^=_-]{0,19}$/.test(ticker) || href !== 'stock.html#' + ticker || !body) return null;
    return {row: row, details: details, body: body, link: link, href: href, ticker: ticker,
      occurrence: row.getAttribute('data-po-id') || '', stamp: stamp(row)};
  }
  function usable(entry, reachable) {
    if (!entry || !entry.row.isConnected || !entry.details.isConnected || !entry.row.contains(entry.details) ||
        !entry.link.isConnected || entry.link.getAttribute('href') !== entry.href || stamp(entry.row) !== entry.stamp ||
        (entry.row.getAttribute('data-po-id') || '') !== entry.occurrence ||
        (entry.details.getAttribute('data-setup-ticker') || entry.row.getAttribute('data-ticker') || '') !== entry.ticker ||
        entry.row.closest('[hidden],[aria-hidden="true"],.mx-tier-hidden,.mx-tier-blurred')) return false;
    var nativeDialog = document.getElementById('pv-setup-dialog');
    var holder = entry.details.querySelector('template.pvs-body-source');
    if (!(entry.details.contains(entry.body) || (holder && holder.content.contains(entry.body)) ||
          (nativeDialog && nativeDialog.open && nativeDialog.contains(entry.body)))) return false;
    return !reachable || !!entry.row.getClientRects().length;
  }
  function current(origin) {
    var s = session();
    return active === origin && usable(origin.entry, false) && origin.store === window.WatchStore &&
      origin.userId === s.userId && origin.generation === s.generation;
  }
  function message(state, en, zh) {
    dialog.setAttribute('data-save-state', state); status.replaceChildren(); words(status, en, zh);
    status.setAttribute('role', state === 'rejected' ? 'alert' : 'status');
  }
  function watchlists() {
    var a = node('a', 'gbtn', 'Open Watchlists', '打开自选'); a.href = 'watchlist.html'; return a;
  }
  function showUnconfirmed(origin, hold) {
    content.replaceChildren();
    message('uncertain', 'The save to ' + hold.listName + ' is unconfirmed. Check membership without saving again.',
      '保存到 ' + hold.listName + ' 的操作尚未确认，可只读检查列表，不会再次保存。');
    var inspect = button('Check account list', '检查账户列表', function () {
      if (!current(origin) || inspect.disabled) return; inspect.disabled = true;
      origin.store.symbols.inspect(hold.listId, origin.entry.ticker).then(function (read) {
        if (!current(origin)) return;
        if (read && read.state === 'present') message('observed', 'Your account currently contains this ticker. This read does not prove the earlier save.', '账户列表目前包含此代码；本次读取不证明此前保存已完成。');
        else message('uncertain', 'Membership is not confirmed. No new save or retry was made.', '尚未确认列表成员关系，未重新保存或重试。');
      });
    }); content.append(inspect, watchlists());
  }
  function build() {
    if (dialog) return;
    dialog = node('dialog', 'prophet-save-dialog'); dialog.id = 'prophet-save-dialog';
    dialog.setAttribute('aria-labelledby', 'prophet-save-title');
    var head = node('header', 'prophet-save-head'), title = node('h2', '', 'Save to a list', '保存到列表');
    title.id = 'prophet-save-title';
    head.append(title, button('Close ×', '关闭 ×', function () { close(true); }));
    status = node('div', 'prophet-save-status'); status.setAttribute('aria-live', 'polite');
    status.setAttribute('aria-atomic', 'true');
    content = node('div', 'prophet-save-content');
    dialog.append(head, status, content, node('p', 'prophet-save-note',
      'Saves the ticker to your account list. It does not create a plan, position or saved thesis.',
      '将代码保存到账户列表，不会创建计划、持仓或已保存的投资论点。'));
    dialog.addEventListener('cancel', function (e) { e.preventDefault(); close(true); });
    document.body.append(dialog);
  }
  function close(restore) {
    var origin = active; active = null; serial++; clearTimeout(readinessTimer);
    if (dialog && dialog.open) dialog.close();
    if (content) content.replaceChildren();
    if (!restore || !origin || !usable(origin.entry, true)) return;
    var s = session();
    if (origin.userId !== s.userId || origin.generation !== s.generation) return;
    window.scrollTo({left: origin.x, top: origin.y, behavior: 'instant'});
    if (origin.fromSetup) {
      var summary = origin.entry.details.querySelector(':scope > summary');
      if (!summary) return;
      summary.click(); mount();
      var nativeDialog = document.getElementById('pv-setup-dialog');
      if (!nativeDialog || !nativeDialog.open || !nativeDialog.contains(origin.entry.body)) return;
      var panel = Array.from(origin.entry.body.querySelectorAll('[data-pvs-section]')).find(function (p) {
        return p.getAttribute('data-pvs-section') === origin.section;
      });
      if (panel && panel.id) {
        var tab = Array.from(nativeDialog.querySelectorAll('[aria-controls]')).find(function (t) {
          return t.getAttribute('aria-controls') === panel.id;
        }); if (tab) tab.click();
      }
      nativeDialog.scrollTop = origin.dialogScroll;
      if (setupButton && setupButton.isConnected) setupButton.focus({preventScroll: true});
    } else if (origin.button && origin.button.isConnected && origin.button.getClientRects().length) {
      origin.button.focus({preventScroll: true});
    }
  }
  function show(entry, trigger, fromSetup) {
    if (!usable(entry, true)) return;
    close(false); build();
    var s = session(), nativeDialog = document.getElementById('pv-setup-dialog');
    var selected = fromSetup && entry.body.querySelector('[role="tabpanel"]:not([hidden])');
    var origin = {entry: entry, button: trigger, store: window.WatchStore, userId: s.userId,
      generation: s.generation, fromSetup: !!fromSetup, section: selected && selected.getAttribute('data-pvs-section') || 'structure',
      dialogScroll: nativeDialog ? nativeDialog.scrollTop : 0, x: window.scrollX, y: window.scrollY};
    if (fromSetup && nativeDialog && nativeDialog.open) {
      var closer = nativeDialog.querySelector('.pvs-close'); if (!closer) return; closer.click();
    }
    if (!usable(entry, true)) return;
    active = origin; dialog.showModal(); load(origin);
    dialog.querySelector('button').focus({preventScroll: true});
  }
  function load(origin) {
    if (!current(origin)) return;
    content.replaceChildren(); clearTimeout(readinessTimer);
    var state = session().state, ticket = ++serial;
    if (state === 'signed_out') {
      message('signed-out', 'Sign in to save ' + origin.entry.ticker + ' to your account.', '登录后将 ' + origin.entry.ticker + ' 保存到账户。');
      content.append(button('Sign in', '登录', function () {
        if (!current(origin)) return;
        pendingSignIn = origin; close(false);
        if (window.MMXSharedShell && window.MMXSharedShell.openAuth) window.MMXSharedShell.openAuth('signin');
        else if (window.MDXAuth && window.MDXAuth.open) window.MDXAuth.open('signin');
      })); return;
    }
    if (state === 'loading') {
      message('loading', 'Connecting to your account…', '正在连接账户…');
      readinessTimer = setTimeout(function () {
        if (current(origin) && ticket === serial) message('unavailable', 'Your account did not become ready. Close and try again later.', '账户尚未就绪。请关闭并稍后重试。');
      }, 13000); return;
    }
    if (state !== 'ready') {
      message('unavailable', 'Account lists are unavailable. Nothing was saved.', '账户列表暂不可用，未保存任何内容。'); return;
    }
    var held = unconfirmed.find(function (h) {
      return h.store === origin.store && h.userId === origin.userId && h.ticker === origin.entry.ticker;
    });
    if (held) { origin.attempted = true; showUnconfirmed(origin, held); return; }
    message('loading', 'Reading your lists…', '正在读取列表…');
    var timer = setTimeout(function () {
      if (current(origin) && ticket === serial) {
        serial++; message('unavailable', 'Your lists did not answer in time. Nothing was saved.', '列表未及时响应，未保存任何内容。');
      }
    }, 13000);
    Promise.resolve().then(function () {
      if (!current(origin)) return null;
      return origin.store.lists.refresh();
    }).then(function (lists) {
      clearTimeout(timer);
      if (!current(origin) || ticket !== serial) return;
      if (!Array.isArray(lists) || lists.some(function (r) { return !r || typeof r.id !== 'string' || typeof r.name !== 'string'; })) throw new Error('invalid-lists');
      if (!lists.length) {
        message('empty', 'No account lists yet. Create a list in Watchlists, then return here.', '账户尚无列表。请在自选页创建列表后返回。');
        content.append(watchlists()); return;
      }
      message('choose', 'Choose a list for ' + origin.entry.ticker + '.', '为 ' + origin.entry.ticker + ' 选择列表。');
      var label = node('label', '', 'Account list', '账户列表'), select = node('select');
      select.id = 'prophet-save-list'; label.htmlFor = select.id;
      lists.forEach(function (list) { var opt = node('option'); opt.value = list.id; opt.textContent = list.name; select.append(opt); });
      var save = button('Save ticker', '保存代码', function () {
        if (!current(origin) || save.disabled || !lists.some(function (r) { return r.id === select.value; })) return;
        var listId = select.value, list = lists.find(function (r) { return r.id === listId; });
        save.disabled = true; select.disabled = true;
        message('waiting', 'Waiting for ' + list.name + ' to confirm ' + origin.entry.ticker + '…', '正在等待 ' + list.name + ' 确认 ' + origin.entry.ticker + '…');
        origin.attempted = true;
        var hold = {store: origin.store, userId: origin.userId, ticker: origin.entry.ticker, listId: listId, listName: list.name};
        unconfirmed.push(hold);
        origin.store.symbols.saveChecked(listId, [origin.entry.ticker], {returnFocus: triggerFor(origin)}).then(function (result) {
          if (result && (result.state === 'rejected' || (result.state === 'saved' && Array.isArray(result.names) &&
              result.names.indexOf(origin.entry.ticker) !== -1 && result.readBackAt))) {
            unconfirmed = unconfirmed.filter(function (h) { return h !== hold; });
          }
          if (!current(origin)) return;
          content.replaceChildren();
          if (result && result.state === 'saved' && Array.isArray(result.names) && result.names.indexOf(origin.entry.ticker) !== -1 && result.readBackAt) {
            message('saved', origin.entry.ticker + ' read back in ' + list.name + ' at ' + result.readBackAt + '.', origin.entry.ticker + ' 已于 ' + result.readBackAt + ' 从 ' + list.name + ' 读回。');
            content.append(watchlists());
          } else if (result && result.state === 'rejected') {
            message('rejected', 'Your account did not accept this save. Nothing is being retried.', '账户未接受此次保存，不会自动重试。');
          } else {
            showUnconfirmed(origin, hold);
          }
        }).catch(function () {
          if (current(origin)) showUnconfirmed(origin, hold);
        });
      });
      content.append(label, select, save);
    }).catch(function () {
      clearTimeout(timer);
      if (current(origin) && ticket === serial) message('unavailable', 'Account lists could not be read. Nothing was saved.', '无法读取账户列表，未保存任何内容。');
    });
  }
  function triggerFor(origin) { return origin.button && origin.button.isConnected ? origin.button : null; }
  function mount() {
    entries = entries.filter(function (e) { return usable(e, false); });
    document.querySelectorAll('#us-today-grid .pvcard,#us-cand-grid .pvcard,#us-stocktable-wrap tbody tr,#us-candidate-pool .ucp-row').forEach(function (row) {
      if (entries.some(function (e) { return e.row === row; })) return;
      var entry = source(row); if (!usable(entry, false)) return;
      var host = row.querySelector('.po-footer') || entry.details.parentNode;
      row.querySelectorAll('.pvs-save-pick').forEach(function (old) { old.remove(); });
      var pick = button('Save', '保存', function () { show(entry, pick, false); }); pick.classList.add('pvs-save-pick');
      host.append(pick); entry.pick = pick; entries.push(entry);
    });
    if (active && !current(active)) close(false);
    var nativeDialog = document.getElementById('pv-setup-dialog');
    var entry = nativeDialog && nativeDialog.open && entries.find(function (e) { return usable(e, false) && nativeDialog.contains(e.body); });
    if (entry === setupEntry && setupButton && setupButton.isConnected) return;
    if (setupButton) setupButton.remove();
    setupEntry = entry || null;
    if (entry) {
      setupButton = button('Save', '保存', function () { show(entry, setupButton, true); });
      setupButton.classList.add('pvs-save-setup'); nativeDialog.querySelector('.pvs-dialog-head').append(setupButton);
    } else setupButton = null;
  }
  function queue() {
    if (queued) return; queued = true;
    Promise.resolve().then(function () { queued = false; mount(); });
  }
  function ready() {
    var s = session();
    if (pendingSignIn && s.state === 'ready') {
      var origin = pendingSignIn; pendingSignIn = null;
      if (usable(origin.entry, true)) show(origin.entry, origin.button, origin.fromSetup);
    } else if (active && !active.attempted) {
      // Client readiness for the SAME account may advance loading, never a write.
      if (active.userId === s.userId && active.generation === s.generation) load(active);
    }
  }
  function init() {
    if (window.__prophetSaveBound) return;
    if (!document.querySelector('[data-watchstore-checked-save]') || typeof HTMLDialogElement === 'undefined') return;
    window.__prophetSaveBound = true;
    mount();
    window.addEventListener('mdx-auth', function (event) {
      var s = session();
      if (pendingSignIn && (event.detail && event.detail.event === 'SIGNED_OUT' || !usable(pendingSignIn.entry, true))) pendingSignIn = null;
      if (active && (active.userId !== s.userId || active.generation !== s.generation)) close(false);
      ready(); queue();
    });
    window.addEventListener('mmx-access-tier', function () { pendingSignIn = null; close(false); queue(); });
    document.addEventListener('candidate-pool-hydrated', function () { pendingSignIn = null; close(false); queue(); }, true);
    document.addEventListener('wl-auth', ready);
    new MutationObserver(queue).observe(document.documentElement, {childList: true, subtree: true, attributes: true,
      attributeFilter: ['hidden','aria-hidden','class','id','href','data-ticker','data-setup-ticker','data-po-id','data-source-digest','data-as-of','data-board-asof'].concat(todayKeys)});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
  if (typeof module !== 'undefined' && module.exports) module.exports = {source: source, usable: usable, show: show, close: close, mount: mount, init: init};
})();
