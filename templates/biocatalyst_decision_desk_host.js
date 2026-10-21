/* BioCatalyst Decision Desk host composition.
 * Reuses MDXAuth, the page's authenticated fetchJson and WMN contracts.
 * No auth client, source selector, publication watermark or persistence owner.
 */
(function (scope, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else scope.BioCatalystDecisionDeskHost = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const KEYS = ['bci_view', 'bci_days', 'bci_case', 'bci_issuer', 'bci_task'];
  const VIEWS = ['upcoming', 'reconcile', 'history'];
  const DAYS = [7, 30, 90, 180, 365];
  const TABS = ['setup', 'scenarios', 'research', 'sources'];
  const DEFAULT_QUERY = Object.freeze({view: 'upcoming', horizon_days: 90});
  const present = (x, max) => typeof x === 'string' && x.length > 0 && x.length <= max && !/[\u0000-\u001f\u007f]/.test(x);
  function refusal(status, code = 'UNAVAILABLE') { return Object.assign(new Error(code), {status, code}); }
  function route(win) {
    if (!present(win.location.href, 16384)) throw refusal(400);
    const params = new URL(win.location.href).searchParams;
    if (KEYS.some(key => params.getAll(key).length > 1)) throw refusal(400);
    const view = params.get('bci_view') || 'upcoming', rawDays = params.get('bci_days');
    const days = rawDays === null ? 90 : Number(rawDays);
    if (!VIEWS.includes(view) || (view === 'upcoming' ? !DAYS.includes(days) || (rawDays !== null && String(days) !== rawDays) : rawDays !== null)) throw refusal(400);
    const event = params.get('bci_case'), issuer = params.get('bci_issuer'), tab = params.get('bci_task') || 'setup';
    if (!TABS.includes(tab) || (event !== null && !present(event, 4096)) ||
        (issuer !== null && !present(issuer, 256)) || (event === null && (issuer !== null || params.has('bci_task')))) throw refusal(400);
    return {query: {view, horizon_days: view === 'upcoming' ? days : null},
      selection: event === null ? null : {event_fact_ref: event, issuer_id: issuer, tab}};
  }
  function mount(options) {
    const win = options && options.window, root = options && options.root;
    const makeDesk = options && (options.createDesk || win?.BioCatalystDecisionDesk?.createDecisionDesk);
    if (!win || !root || !win.document || typeof makeDesk !== 'function' || typeof options.fetchJson !== 'function') throw new Error('HOST_BINDINGS_REQUIRED');
    const doc = win.document;
    let component, baseRefresh, disposed = false, suspended = false, revision = 0, navigation = 0;
    let suppressCase = 0, invalidRoute = false, routeState = null;
    const listeners = [];
    function listen(target, name, fn) { target.addEventListener(name, fn); listeners.push(() => target.removeEventListener(name, fn)); }
    function user() {
      try { const value = win.MDXAuth?.user(); return value && present(value.id, 256) ? value : null; }
      catch (_) { return null; }
    }
    function contextKey() { return JSON.stringify(['decision-desk', revision, user()?.id || null]); }
    function notice(value) {
      routeState = value;
      if (typeof options.onRouteUnavailable === 'function') options.onRouteUnavailable(value);
    }
    function fetchOwner(path, values, signal) {
      if (disposed || suspended) throw refusal(503);
      if (invalidRoute) throw refusal(400);
      // MDXAuth is an availability hint only. The unchanged API enforces paid access.
      if (!user()) throw refusal(401, 'ACCESS_REQUIRED');
      const params = new URLSearchParams();
      Object.entries(values).forEach(([key, value]) => { if (value !== null && value !== undefined) params.set(key, String(value)); });
      return options.fetchJson(path + '?' + params.toString(), signal);
    }
    function writeRoute(query, selection, push) {
      if (disposed || invalidRoute) return;
      const url = new URL(win.location.href);
      KEYS.forEach(key => url.searchParams.delete(key));
      if (query.view !== 'upcoming') url.searchParams.set('bci_view', query.view);
      if (query.view === 'upcoming' && query.horizon_days !== 90) url.searchParams.set('bci_days', String(query.horizon_days));
      if (selection) {
        url.searchParams.set('bci_case', selection.event_fact_ref);
        if (selection.issuer_id !== null) url.searchParams.set('bci_issuer', selection.issuer_id);
        if (selection.tab !== 'setup') url.searchParams.set('bci_task', selection.tab);
      }
      if (url.href !== win.location.href) win.history[push ? 'pushState' : 'replaceState'](win.history.state, '', url.href);
    }
    function requestAccess() {
      if (disposed || suspended || invalidRoute || component?.getState().issue !== 'ACCESS_REQUIRED') return;
      // Existing owners retain sign-in and subscription management. This action
      // does not authenticate, fetch source data, or carry private case context.
      if (!user() && typeof win.MDXAuth?.open === 'function') win.MDXAuth.open('signin');
      else win.location.assign(new URL('/plans.html', win.location.href).href);
    }
    function create() {
      let initial;
      try { initial = route(win); invalidRoute = false; } catch (_) { initial = {query: DEFAULT_QUERY}; invalidRoute = true; }
      component = makeDesk({root, locale: doc.documentElement.dataset.lang || 'en', query: initial.query,
        getContextKey: contextKey, onRequestAccess: requestAccess,
        loadPage: ({query, cursor, signal}) => fetchOwner('/api/biocatalyst/v1/what-matters-next', {...query, cursor}, signal),
        loadDetail: ({event_fact_ref, issuer_id, generation_id, signal}) => fetchOwner('/api/biocatalyst/v1/what-matters-next/detail', {event_fact_ref, issuer_id, generation_id}, signal),
        onCaseChange(selection) {
          if (suppressCase || disposed || component?.getState().phase !== 'loaded') return;
          navigation++; notice(null); writeRoute(component.getState().query, selection, true);
        }
      });
      baseRefresh = component.refresh.bind(component);
      // The existing presentation's filter and refresh controls call this method.
      component.refresh = query => {
        let currentRoute;
        try { currentRoute = route(win); invalidRoute = false; }
        catch (_) { return refreshRoute(); }
        const next = query || component.getState().query;
        const same = next.view === currentRoute.query.view && next.horizon_days === currentRoute.query.horizon_days;
        return run(next, same ? currentRoute.selection : null, true);
      };
    }
    async function run(query, selection, syncUrl) {
      if (disposed || suspended) return;
      const ticket = ++navigation, instance = component, refresh = baseRefresh;
      notice(null); suppressCase++;
      let work;
      try {
        work = refresh(query);
        if (syncUrl && instance.getState().phase === 'loading') writeRoute(instance.getState().query, selection, false);
      } finally { suppressCase--; }
      await work;
      if (disposed || suspended || ticket !== navigation || instance !== component) return;
      if (instance.getState().phase !== 'loaded' || !selection) return;
      suppressCase++;
      try { if (!instance.openCase(selection)) notice('CASE_NOT_IN_LOADED_PAGE'); }
      finally { suppressCase--; }
    }
    function refreshRoute() {
      if (disposed || suspended) return Promise.resolve();
      try { const value = route(win); invalidRoute = false; return run(value.query, value.selection, false); }
      catch (_) {
        invalidRoute = true; navigation++; component.contextChanged(); notice('INVALID_CASE_ROUTE');
        return baseRefresh(DEFAULT_QUERY);
      }
    }
    function contextChanged() {
      if (disposed) return;
      revision++; navigation++; component.contextChanged(); notice(null);
      if (!suspended) void refreshRoute();
    }
    create();
    listen(win, 'mdx-auth', contextChanged);
    listen(win, 'popstate', () => { void refreshRoute(); });
    listen(win, 'pagehide', () => { suspended = true; revision++; navigation++; component.contextChanged(); });
    listen(win, 'pageshow', event => { if (event.persisted) { suspended = false; contextChanged(); } });
    listen(doc, 'langchange', () => {
      if (disposed) return;
      navigation++; revision++; suppressCase++;
      try { component.destroy(); create(); } finally { suppressCase--; }
      void refreshRoute();
    });
    const ready = refreshRoute();
    return Object.freeze({ready, refresh: () => disposed ? Promise.resolve() : component.refresh(),
      contextChanged, getState: () => component.getState(), getRouteState: () => routeState,
      destroy() {
        if (disposed) return;
        disposed = true; navigation++; revision++;
        listeners.splice(0).forEach(remove => remove()); component.destroy();
      }
    });
  }
  return Object.freeze({mount});
});
