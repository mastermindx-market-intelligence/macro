# R9 API/client component candidates — NOT APPLIED

These are isolated review candidates accompanying `corpus_search_r9.patch`, not a deployed service, accepted interface, automatic patch instruction or ownership transfer. The proposed runtime owners remain `app/research.py` and `site/research_vault_app.js`; their branches are untouched. Reconcile #7045/#7079 before adoption.

Target inspection: `macro@11485597cc53b3137346084aae4623cceed28a3f`. Expected full upstream API blob: `bca9b965057df653607765107ef789692c47dcdc`; client: `1f0b673da6c3d6a44ad3d74b2994f70b9a4311c8`. Only selected API/client functions were copied and tested. Whole-file byte parity, complete event wiring, current-base application and production behavior are NOT established. The complete corpus dependency was separately byte-verified.

The local package contains the exact runnable source files and four test harnesses. The SHA256 values in `verification_r9.json` identify them. This document makes the proposed code recoverable and reviewable without treating it as an admitted production module. Do not import or execute Markdown as runtime code.

## Existing catalog helper: optional request-pinned snapshot

Only an internal already-validated `_load_catalog` result may be passed. This is not a caller-supplied authorization list or new source authority.

```python
def _catalog_ids(catalog: dict | None = None) -> set[str]:
    """Existing visibility owner, optionally reusing one request-pinned catalog.

    Default callers still load the current catalog. Only an already-validated
    internal catalog from _load_catalog may be supplied; never accept client data.
    """
    cat = _load_catalog() if catalog is None else catalog
    return {str((item or {}).get("id") or "") for item in (cat.get("items") or [])}
```

## Existing search route: same wire shape, scoped selection before limit

```python
@router.get("/api/research/search")
def research_search(
    q: str = Query("", max_length=_Q_MAX),
    institution: str = Query("", max_length=_FACET_MAX),
    from_: str = Query("", alias="from", max_length=32),
    to: str = Query("", max_length=32),
    limit: int = Query(_SEARCH_LIMIT_DEFAULT),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Search within one catalog/tier scope; preserve unavailable versus no-match.

    The existing catalog and tier owners still decide visibility. The SQL query
    receives that allowed set before its final limit. No new permission mirror.
    Wire shape is unchanged: items, count and available.
    """
    try:
        lim = int(limit)
    except (TypeError, ValueError):
        lim = _SEARCH_LIMIT_DEFAULT
    lim = max(1, min(_SEARCH_LIMIT_MAX, lim))

    try:
        catalog = _load_catalog()
        eligible = _catalog_ids(catalog)
    except HTTPException:
        return {"items": [], "count": 0, "available": False}
    if not _can_view(_optional_tier(authorization)):
        preview_ids = {
            str((item or {}).get("id") or "")
            for item in _catalog_preview(catalog).get("items", [])
        }
        eligible = eligible.intersection(preview_ids)
    if not eligible:
        return {"items": [], "count": 0, "available": True}

    conn = _corpus_conn()
    if conn is None:
        return {"items": [], "count": 0, "available": False}
    try:
        items = corpus_mod.search(
            conn, q or "", institution=(institution or None),
            date_from=(from_ or None), date_to=(to or None), limit=lim,
            eligible_ids=frozenset(eligible), raise_on_error=True,
        )
    except Exception as exc:
        # Classification only: do not return query text or database details.
        log.debug("research_vault: search unavailable (%s)", type(exc).__name__)
        return {"items": [], "count": 0, "available": False}
    finally:
        try:
            conn.close()
        except Exception:
            pass
    # Defense in depth; this no longer creates the primary candidate budget.
    items = [item for item in items if str((item or {}).get("id") or "") in eligible]
    return {"items": items, "count": len(items), "available": True}
```

This preserves the public three-key response and the old corpus list API by default. Strict handling is opt-in at the serving caller. Empty-query and existing sanitizer behavior are preserved; this candidate does NOT implement a new general invalid-query classification.

## Selected client functions: request context, truthful status and no denial widening

Replace the existing declarations/functions exactly once, rather than appending duplicate versions. The actual source owner must verify all filter/auth/catalog event hooks against the full current client. A changed context rejects stale results; automatic refresh after every application event is not proven by the isolated harness.

```javascript
  // Review candidate: internal request state, not an authorization decision.
  var SEARCH_STATUS = 'idle';
  var SEARCH_CONTEXT = '';
  var _searchTimer = null;
  var _searchSerial = 0;

  function researchSearchContext() {
    var principal = '';
    try {
      var u = window.MDXAuth && window.MDXAuth.user && window.MDXAuth.user();
      principal = u && u.id ? String(u.id) : '';
    } catch (e) { principal = 'unresolved'; }
    return JSON.stringify([
      FILT.q, FILT.inst, FILT.side, FILT.theme, LANE,
      typeof CATALOG_GENERATED === 'undefined' ? '' : CATALOG_GENERATED,
      typeof CATALOG_REQ === 'undefined' ? '' : CATALOG_REQ,
      typeof USER_TIER === 'undefined' ? '' : USER_TIER,
      principal
    ]);
  }

  function laneMatch(x) {
    if (LANE === 'picks') return x.top;
    if (LANE === 'saved') return DocState.isSaved(x.id);
    return true;
  }

  function matchItem(x) {
    if (!laneMatch(x)) return false;
    if (FILT.inst && x.inst !== FILT.inst) return false;
    if (FILT.side && x.side !== FILT.side) return false;
    if (FILT.theme && x.tags.indexOf(FILT.theme) < 0) return false;
    if (FILT.q) {
      // Existing tier/catalog gates in renderFeed still control actual visibility.
      // A stale scope must never inherit an authoritative hit set.
      if (SEARCH_HITS && SEARCH_CONTEXT === researchSearchContext()) return SEARCH_HITS[x.id];
      var hay = (x.title + ' ' + x.inst + ' ' + x.desk + ' ' + x.points.join(' ') + ' ' + x.tags.join(' ') + ' ' + x.tickers.join(' ')).toLowerCase();
      if (hay.indexOf(FILT.q.toLowerCase()) < 0) return false;
    }
    return true;
  }

  function onSearchInput() {
    FILT.q = $('q').value.trim();
    var serial = ++_searchSerial;
    var context = researchSearchContext();
    var q = FILT.q, inst = FILT.inst;
    SEARCH_CONTEXT = context;
    SEARCH_HITS = null;
    SEARCH_STATUS = q ? 'pending' : 'idle';
    clearTimeout(_searchTimer);
    renderFeed();
    if (!q) return;
    function current() { return serial === _searchSerial && context === researchSearchContext(); }
    function unavailable() {
      if (!current()) return;
      SEARCH_HITS = null;
      SEARCH_STATUS = 'unavailable';
      renderFeed();
    }
    _searchTimer = setTimeout(function () {
      if (!current()) return;
      var url = API + '/api/research/search?q=' + encodeURIComponent(q)
        + (inst ? '&institution=' + encodeURIComponent(inst) : '');
      withAuth().then(function (h) {
        if (!current()) return null;
        return fetch(url, { headers: h, credentials: 'include' });
      }).then(function (r) {
        if (!current() || !r) return null;
        if (r.status === 401 || r.status === 402 || r.status === 403) {
          SEARCH_HITS = Object.create(null);
          SEARCH_STATUS = 'denied';
          renderFeed();
          return null;
        }
        if (!r.ok) { unavailable(); return null; }
        return r.json();
      }).then(function (j) {
        if (!current() || j === null) return;
        if (!j || j.available !== true || !Array.isArray(j.items)) { unavailable(); return; }
        var valid = j.items.every(function (it) {
          return it && typeof it.id === 'string' && /^[a-z0-9][a-z0-9-]{0,120}$/.test(it.id);
        });
        if (!valid) { unavailable(); return; }
        var hits = Object.create(null);
        j.items.forEach(function (it) { hits[it.id] = 1; });
        SEARCH_HITS = hits;
        SEARCH_STATUS = 'ready';
        renderFeed();
      }).catch(unavailable);
    }, 280);
  }

  function researchSearchMessage() {
    if (!FILT.q) return '';
    if (SEARCH_CONTEXT !== researchSearchContext()) {
      return T('Search context changed. Refresh the search to obtain current server results.',
        '搜索范围已变化。请刷新搜索以获取当前服务器结果。');
    }
    if (SEARCH_STATUS === 'unavailable') {
      return T('Full-text search is temporarily unavailable. Any matches shown below are from the permitted catalog only, not a complete search of report text.',
        '全文搜索暂时不可用。下方结果仅来自获准访问的目录，并非报告全文的完整搜索结果。');
    }
    if (SEARCH_STATUS === 'denied') {
      return T('This search was not authorized. No additional local results have been added.',
        '此搜索未获授权，未追加本地搜索结果。');
    }
    if (SEARCH_STATUS === 'pending') {
      return T('Searching report text. Any initial matches are from the permitted catalog only.',
        '正在搜索报告全文。初始结果仅来自获准访问的目录。');
    }
    return '';
  }
```

## Existing renderer: consume the status instead of leaving it disconnected

```javascript
  function renderFeed() {
    var rows = ITEMS.filter(matchItem);
    // The public preview is anchored to the latest three catalog entries before
    // filters/search are applied. Otherwise a visitor could search for a locked
    // title and promote it into the visible allowance.
    var previewRows = feedUnlocked() ? [] : previewItems().filter(matchItem);
    var feed = $('feed');
    var searchMessage = researchSearchMessage();
    var picksGate = LANE === 'picks' && picksLocked();
    var pt = doc.querySelector('.rv-lane[data-lane="picks"]');
    if (pt) pt.classList.toggle('locked', picksLocked());   // small lock glyph on the tab
    // reset the pager whenever the result set (lane + filters + search) changes
    var sig = LANE + '|' + FILT.inst + '|' + FILT.side + '|' + FILT.theme + '|' + FILT.q;
    if (sig !== _feedSig) { _feedSig = sig; shownN = PAGE_SIZE; }
    if (CATALOG_SOURCE === 'unavailable') {
      // NOT the onboarding copy below: "we hold no reports yet" is a claim about
      // the vault, and we have no basis for it when we could not read a verified
      // catalog at all. Saying so plainly is the whole point of this state.
      feed.innerHTML = emptyState(
        T('Live research is temporarily unavailable', '实时研报暂时不可用'),
        T('We could not reach a verified copy of the research catalog. This is a loading problem, not an empty vault — please try again shortly.',
          '暂时无法获取经校验的研报目录。这是加载问题，并非研报库为空 —— 请稍后重试。'));
    } else if (!ITEMS.length) {
      feed.innerHTML = emptyState(
        T('Institutional research is being onboarded', '机构研报正在接入'),
        T('New buy-side and sell-side desk reports arrive hourly — check back shortly.', '买方与卖方研究每小时更新 —— 请稍后再来查看。'));
    } else if (picksGate) {
      feed.innerHTML = picksUpgradePanel();          // Top Picks is Pro-only
    } else if (!rows.length && searchMessage) {
      feed.innerHTML = emptyState(
        T('Research search is incomplete', '研报搜索尚未完成'), searchMessage);
    } else if (!rows.length) {
      var savedLane = LANE === 'saved';
      feed.innerHTML = emptyState(
        savedLane ? T('Nothing saved yet', '还没有收藏') : T('No reports match', '没有匹配的研报'),
        savedLane ? T('Tap the bookmark on any report to keep it here for later.', '点击任意报告上的书签，即可收藏到此处。')
          : T('Try clearing a filter or widening your search.', '试试清除筛选或放宽搜索条件。'));
    } else if (feedUnlocked()) {
      // Pro: paged — show the first shownN, then a "Show more" button
      var pg = rows.slice(0, shownN).map(cardHTML).join('');
      if (rows.length > shownN) pg += moreButton(rows.length - shownN);
      feed.innerHTML = pg;
    } else {
      // Non-Pro: only the fixed latest three summaries can render. Locked cards
      // use generic skeleton copy so later report titles/summaries are not exposed.
      var html = previewRows.map(cardHTML).join('');
      var lockedN = Math.max(0, TOTAL_COUNT - teaseCount());
      if (lockedN) html += lockedTeaser(lockedN);
      feed.innerHTML = html || picksUpgradePanel();
    }
    $('cnt-n').textContent = picksGate ? 0 : (feedUnlocked() ? Math.min(shownN, rows.length) : previewRows.length);
    $('cnt-t').textContent = feedUnlocked() ? rows.length : TOTAL_COUNT;
    renderActiveChips();
    if (searchMessage && rows.length && !picksGate && CATALOG_SOURCE !== 'unavailable') {
      feed.insertAdjacentHTML('afterbegin', '<p class="rv-search-status" role="status">'
        + esc(searchMessage) + '</p>');
    }
  }
```

The renderer was exercised with a controlled DOM adapter, including unavailable-without-local-matches, labelled fallback, valid no-match, denied output and Chinese copy. Chromium refused the synthetic file before page load (`ERR_BLOCKED_BY_ADMINISTRATOR`); no screenshot/browser acceptance exists. Do not remove policy to obtain that proof.

## Adoption boundary

The API/client candidates and the corpus patch must be integrated together or held. Applying just the backend strict flag cannot make an old consumer understand unavailability. Full current-file checks, incumbent interface agreement, existing suite integration, eligible native runtime JSON support, actual event wiring, staging/browser proof, and permitted original-source inspection remain required. The source-bound company-association feature (R8-G1) remains unbuilt; no generated ticker keywords are inserted into literal evidence.
