'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

const coreModule = require('../templates/intl_workspace_state.js');

function makeConfig(overrides = {}) {
  return {
    markets: ['us-tech', 'jp-auto', 'de-ind', 'fr-energy', 'constructor'],
    horizons: ['1d', '1w'],
    bases: ['local', 'usd_unhedged'],
    default_horizon: '1d',
    default_basis: 'local',
    source_reference: 'src-1',
    anchor_ids: ['a-overview', 'a-library'],
    library_group_ids: ['equity', 'macro'],
    ...overrides,
  };
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function assertOk(result, expectedState = null, intent = null) {
  assert.equal(result.ok, true);
  assert.deepEqual(result.issues, []);
  assert.deepEqual(result.intent, intent);
  if (expectedState) assert.deepEqual(result.state, expectedState);
}

test('1. configuration validates, rejects malformed shapes, and snapshots inputs', () => {
  const config = makeConfig();
  const core = coreModule.createIntlWorkspaceState(config);
  assert.equal(typeof core.initialState, 'object');
  assert.deepEqual(core.initialState, {
    view: 'overview', selected_market: null, compare_markets: [], horizon: '1d',
    currency_basis: 'local', return_basis: 'price', source_reference: 'src-1',
    expanded: false, library_group: null, baseline: null, return_stack: [],
  });

  assert.throws(() => coreModule.createIntlWorkspaceState({ ...config, markets: [] }), error => error.code === 'INVALID_CONFIG');
  assert.throws(() => coreModule.createIntlWorkspaceState({ ...config, extra: true }), error => error.code === 'INVALID_CONFIG');
  const accessor = makeConfig();
  Object.defineProperty(accessor, 'markets', { get() { throw new Error('must not invoke'); } });
  assert.throws(() => coreModule.createIntlWorkspaceState(accessor), error => error.code === 'INVALID_CONFIG');
  const inherited = Object.create({ markets: ['x'] });
  Object.assign(inherited, makeConfig());
  assert.throws(() => coreModule.createIntlWorkspaceState(inherited), error => error.code === 'INVALID_CONFIG');

  config.markets.push('runtime-only');
  config.default_horizon = 'changed';
  assert.equal(core.initialState.horizon, '1d');
  assert.deepEqual(core.parseQuery('').state.compare_markets, []);
  assert.equal(core.parseQuery('').state.source_reference, 'src-1');
});

test('2. supports every view and keeps selection independent from pin drafts', () => {
  const core = coreModule.createIntlWorkspaceState(makeConfig());
  let state = clone(core.initialState);
  for (const view of ['overview', 'compare', 'macro', 'risk', 'history', 'library']) {
    state = core.reduce(state, { type: 'set_view', view }).state;
  }
  assert.equal(state.view, 'library');
  state = core.reduce(state, { type: 'pin', market_id: 'us-tech' }).state;
  assert.equal(state.selected_market, null);
  state = core.reduce(state, { type: 'select_market', market_id: 'jp-auto' }).state;
  assert.deepEqual(state.compare_markets, ['us-tech']);
});

test('3. enforces ordered four-pin limit and treats duplicate/unpin values as no-ops', () => {
  const core = coreModule.createIntlWorkspaceState(makeConfig());
  let state = clone(core.initialState);
  for (const id of ['jp-auto', 'us-tech', 'de-ind', 'fr-energy']) state = core.reduce(state, { type: 'pin', market_id: id }).state;
  const limited = core.reduce(state, { type: 'pin', market_id: 'constructor' });
  assert.deepEqual(limited.issues, [{ code: 'PIN_LIMIT', field: 'market_id' }]);
  assert.equal(limited.state, state);
  assert.deepEqual(core.reduce(state, { type: 'pin', market_id: 'us-tech' }).state.compare_markets, state.compare_markets);
  assert.notEqual(core.reduce(state, { type: 'pin', market_id: 'us-tech' }).state, state);
  state = core.reduce(state, { type: 'unpin', market_id: 'absent' }).state;
  state = core.reduce(state, { type: 'unpin', market_id: 'us-tech' }).state;
  assert.deepEqual(state.compare_markets, ['jp-auto', 'de-ind', 'fr-energy']);
});

test('4. rejects unsupported horizon, basis, and return basis without substitution', () => {
  const core = coreModule.createIntlWorkspaceState(makeConfig());
  let state = clone(core.initialState);
  const invalidHorizon = core.reduce(state, { type: 'set_horizon', horizon: '1m' });
  assert.deepEqual(invalidHorizon.issues, [{ code: 'UNSUPPORTED_VALUE', field: 'horizon' }]);
  assert.equal(invalidHorizon.state, state);
  state = core.reduce(state, { type: 'set_horizon', horizon: '1w' }).state;
  state = core.reduce(state, { type: 'set_basis', currency_basis: 'usd_unhedged' }).state;
  assert.equal(core.reduce(state, { type: 'set_basis', currency_basis: 'usd' }).issues[0].code, 'UNSUPPORTED_VALUE');
  const unsupportedReturnBasis = core.parseQuery('view=overview&market=&pins=&horizon=1d&basis=local&return_basis=total&group=');
  assert.equal(unsupportedReturnBasis.issues[0].code, 'UNSUPPORTED_VALUE');
});

test('5. baseline captures the exact tuple and clears on every tuple change', () => {
  const core = coreModule.createIntlWorkspaceState(makeConfig());
  let state = core.reduce(clone(core.initialState), { type: 'pin', market_id: 'jp-auto' }).state;
  state = core.reduce(state, { type: 'select_market', market_id: 'de-ind' }).state;
  state = core.reduce(state, { type: 'set_horizon', horizon: '1w' }).state;
  state = core.reduce(state, { type: 'set_basis', currency_basis: 'usd_unhedged' }).state;
  state = core.reduce(state, { type: 'capture_baseline' }).state;
  assert.deepEqual(state.baseline, {
    source_reference: 'src-1', currency_basis: 'usd_unhedged', horizon: '1w',
    selected_market: 'de-ind', compare_markets: ['jp-auto'],
  });
  let preserved = core.reduce(state, { type: 'set_view', view: 'risk' }).state;
  preserved = core.reduce(preserved, { type: 'set_expanded', expanded: true }).state;
  preserved = core.reduce(preserved, { type: 'set_library_group', group_id: 'macro' }).state;
  assert.deepEqual(preserved.baseline, state.baseline);
  let changed = core.reduce(state, { type: 'pin', market_id: 'fr-energy' }).state;
  assert.equal(changed.baseline, null);
  changed = core.reduce(changed, { type: 'unpin', market_id: 'fr-energy' }).state;
  assert.equal(changed.baseline, null);
});

test('6. resize is a defensive no-op and repeated actions do not mutate inputs', () => {
  const core = coreModule.createIntlWorkspaceState(makeConfig());
  const input = clone(core.initialState);
  input.compare_markets.push('jp-auto');
  const before = clone(input);
  const result = core.reduce(input, { type: 'resize' });
  assertOk(result, before);
  assert.notEqual(result.state, input);
  const first = core.reduce(input, { type: 'pin', market_id: 'de-ind' });
  const second = core.reduce(input, { type: 'pin', market_id: 'de-ind' });
  assert.deepEqual(first.state, second.state);
  assert.deepEqual(input, before);
});

test('7. return stack stores context, refuses a ninth push, and restores nested context', () => {
  const core = coreModule.createIntlWorkspaceState(makeConfig());
  let state = clone(core.initialState);
  for (let index = 0; index < 8; index += 1) {
    state = core.reduce(state, { type: 'push_return', anchor_id: index % 2 ? 'a-library' : 'a-overview' }).state;
  }
  assert.equal(state.return_stack.length, 8);
  const overflow = core.reduce(state, { type: 'push_return', anchor_id: 'a-library' });
  assert.deepEqual(overflow.issues, [{ code: 'RETURN_STACK_LIMIT', field: 'return_stack' }]);
  assert.equal(overflow.state, state);
  let researched = core.reduce(state, { type: 'set_library_group', group_id: 'equity' }).state;
  researched = core.reduce(researched, { type: 'select_market', market_id: 'fr-energy' }).state;
  const back = core.reduce(researched, { type: 'back' });
  assertOk(back, null, { type: 'restore_focus', anchor_id: 'a-library' });
  assert.equal(back.state.library_group, null);
  assert.equal(back.state.selected_market, null);
  assert.equal(back.state.return_stack.length, 7);
  assertOk(core.reduce(clone(core.initialState), { type: 'back' }), core.initialState);
});

test('8. source replacement clears bound context and reports honest unknown source', () => {
  const core = coreModule.createIntlWorkspaceState(makeConfig());
  let state = core.reduce(clone(core.initialState), { type: 'capture_baseline' }).state;
  state = core.reduce(state, { type: 'set_expanded', expanded: true }).state;
  state = core.reduce(state, { type: 'push_return', anchor_id: 'a-library' }).state;
  assertOk(core.reduce(state, { type: 'replace_source', source_reference: 'src-1' }));
  const changed = core.reduce(state, { type: 'replace_source', source_reference: 'unknown-source' });
  assertOk(changed, null, { type: 'invalidate_source_bound_context' });
  assert.equal(changed.state.source_reference, 'unknown-source');
  assert.equal(changed.state.baseline, null);
  assert.deepEqual(changed.state.return_stack, []);
  assert.equal(changed.state.expanded, true);
  const invalidSourceAction = core.reduce(state, { type: 'replace_source', source_reference: 'bad	source' });
  assert.deepEqual(invalidSourceAction.issues, [{ code: 'INVALID_ACTION', field: 'source_reference' }]);
});

test('9. canonical URL serialization round-trips and uses initial ephemeral defaults', () => {
  const core = coreModule.createIntlWorkspaceState(makeConfig({ source_reference: 'unicode.source' }));
  let state = core.reduce(clone(core.initialState), { type: 'set_view', view: 'library' }).state;
  state = core.reduce(state, { type: 'select_market', market_id: 'us-tech' }).state;
  state = core.reduce(state, { type: 'pin', market_id: 'constructor' }).state;
  state = core.reduce(state, { type: 'set_library_group', group_id: 'macro' }).state;
  state = core.reduce(state, { type: 'capture_baseline' }).state;
  const serialized = core.serializeQuery(state);
  assert.equal(serialized.query, 'view=library&market=us-tech&pins=constructor&horizon=1d&basis=local&return_basis=price&group=macro');
  assert.ok(!serialized.query.includes('unicode.source'));
  const parsed = core.parseQuery(serialized.query);
  assert.equal(parsed.state.source_reference, 'unicode.source');
  assert.equal(parsed.state.baseline, null);
  assert.deepEqual(parsed.state.compare_markets, ['constructor']);
  const defaults = core.parseQuery('view=&market=&pins=&horizon=&basis=&return_basis=&group=');
  assert.equal(defaults.state.view, 'overview');
  assert.equal(defaults.state.horizon, '1d');
});

test('10. URL parser rejects malformed, oversized, duplicate, and hostile fields', () => {
  const core = coreModule.createIntlWorkspaceState(makeConfig());
  const expectedInitial = clone(core.initialState);
  const checks = [
    ['pins=us-tech&pins=jp-auto', 'INVALID_QUERY'],
    ['view=overview&bad=x', 'INVALID_QUERY'],
    ['view=%zz', 'INVALID_QUERY'],
    ['view=%00', 'INVALID_QUERY'],
    ['pins=us-tech%2Cjp-auto', 'INVALID_QUERY'],
    [`view=${'x'.repeat(2100)}`, 'QUERY_TOO_LONG'],
    ['view=overview&market=&pins=&horizon=1d&basis=local&return_basis=price&group=&view=overview', 'INVALID_QUERY'],
    ['view=overview&market=&pins=&horizon=1d&basis=local&return_basis=price&group=absent', 'UNSUPPORTED_VALUE'],
    ['view=overview&market=&pins=&horizon=&basis=local&return_basis=price&group=', 'INVALID_QUERY'],
    ['view=overview&market=&pins=us-tech,jp-auto,de-ind,fr-energy,constructor&horizon=1d&basis=local&return_basis=price&group=', 'INVALID_QUERY'],
    ['view=overview&market=&pins=&horizon=1d&basis=local&return_basis=price&group=&bad=', 'INVALID_QUERY'],
    ['view=overview&%76iew=compare', 'INVALID_QUERY'],
    ['view=overview#secret', 'INVALID_QUERY'],
    ['view=%F0%9F%98', 'INVALID_QUERY'],
  ];
  for (const [query, code] of checks) {
    const parsed = core.parseQuery(query);
    assert.equal(parsed.ok, false, query);
    assert.deepEqual(parsed.state, expectedInitial);
    assert.equal(parsed.issues[0].code, code);
  }
  const repeated = core.parseQuery('?view=overview&market=&pins=jp-auto,jp-auto&horizon=1d&basis=local&return_basis=price&group=');
  assert.deepEqual(repeated.issues, [{ code: 'INVALID_QUERY', field: 'pins' }]);
});

test('11. external state/action validation is closed and deterministic', () => {
  const core = coreModule.createIntlWorkspaceState(makeConfig());
  const state = clone(core.initialState);
  assert.deepEqual(core.reduce({ ...state, extra: true }, { type: 'resize' }).issues[0].code, 'INVALID_STATE');
  const custom = Object.assign(Object.create({ inherited: true }), state);
  assert.equal(core.reduce(custom, { type: 'resize' }).issues[0].code, 'INVALID_STATE');
  const accessorState = clone(core.initialState);
  Object.defineProperty(accessorState, 'view', { get: () => 'overview' });
  assert.equal(core.reduce(accessorState, { type: 'resize' }).issues[0].code, 'INVALID_STATE');
  assert.deepEqual(core.reduce(state, null).issues[0], { code: 'INVALID_ACTION', field: 'action' });
  assert.deepEqual(core.reduce(state, { type: 'save' }).issues[0], { code: 'UNKNOWN_ACTION', field: 'type' });
  assert.deepEqual(core.reduce(state, { type: 'follow' }).issues[0], { code: 'UNKNOWN_ACTION', field: 'type' });
  assert.deepEqual(core.reduce(state, { type: 'refresh' }).issues[0], { code: 'UNKNOWN_ACTION', field: 'type' });
  assert.equal(core.reduce(state, { type: 'pin', market_id: 'us-tech', extra: 1 }).issues[0].code, 'INVALID_ACTION');
  const result = core.reduce(state, { type: 'pin', market_id: 'us-tech' });
  assert.equal(result.ok, true);
  assert.deepEqual(state, core.initialState);
});

test('12. exports browser UMD and CommonJS consistently without host I/O', () => {
  const sourcePath = require.resolve('../templates/intl_workspace_state.js');
  const source = fs.readFileSync(sourcePath, 'utf8');
  const sandbox = vm.createContext({});
  vm.runInContext(source, sandbox, { filename: 'intl_workspace_state.js' });
  const browserFactory = vm.runInContext('IntlWorkspaceState.createIntlWorkspaceState', sandbox);
  const config = makeConfig();
  const realmConfig = vm.runInContext(`(${JSON.stringify(config)})`, sandbox);
  const browserCore = browserFactory(realmConfig);
  const commonCore = coreModule.createIntlWorkspaceState(config);
  assert.deepEqual(JSON.parse(JSON.stringify(browserCore.initialState)), commonCore.initialState);
  const realmState = vm.runInContext(`(${JSON.stringify(commonCore.initialState)})`, sandbox);
  const browserQuery = JSON.parse(JSON.stringify(browserCore.serializeQuery(realmState)));
  const commonQuery = commonCore.serializeQuery(commonCore.initialState);
  assert.deepEqual(browserQuery, commonQuery);
  assert.equal(typeof coreModule.createIntlWorkspaceState, 'function');
  assert.doesNotMatch(source, /\bfetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|setTimeout|setInterval|document\s*\./);
});

test('13. omitted URL fields use initial defaults while explicitly empty required fields refuse', () => {
  const core = coreModule.createIntlWorkspaceState(makeConfig());
  for (const query of ['', '?', 'view=compare', 'market=jp-auto', 'pins=jp-auto']) {
    const result = core.parseQuery(query);
    assert.equal(result.ok, true, query);
    assert.equal(result.state.horizon, '1d');
    assert.equal(result.state.currency_basis, 'local');
  }
  for (const key of ['view', 'horizon', 'basis', 'return_basis']) {
    const result = core.parseQuery(`${key}=`);
    assert.equal(result.ok, false, key);
    assert.equal(result.issues[0].code, 'INVALID_QUERY');
  }
});

test('14. config rejects duplicate IDs and market delimiters with public TypeError', () => {
  for (const key of ['markets', 'horizons', 'bases', 'anchor_ids', 'library_group_ids']) {
    const config = makeConfig();config[key].push(config[key][0]);
    assert.throws(() => coreModule.createIntlWorkspaceState(config), e => e instanceof TypeError && e.code === 'INVALID_CONFIG', key);
  }
  for (const market of ['', 'a,b', '\ud800', 'bad\u0085id']) {
    assert.throws(() => coreModule.createIntlWorkspaceState(makeConfig({markets: [market]})), e => e instanceof TypeError && e.code === 'INVALID_CONFIG');
  }
  assert.equal(coreModule.createIntlWorkspaceState(makeConfig({anchor_ids: [],library_group_ids: []})).parseQuery('').ok, true);
});

test('15. supplementary Unicode and opaque nonmarket delimiters roundtrip without double decoding', () => {
  const token = '😀,+%#';
  const core = coreModule.createIntlWorkspaceState(makeConfig({markets:['😀+%#'],horizons:[token],default_horizon:token,anchor_ids:[token],library_group_ids:[token],source_reference:token}));
  let state = core.reduce(core.initialState,{type:'pin',market_id:'😀+%#'}).state;
  state = core.reduce(state,{type:'set_library_group',group_id:token}).state;
  state = core.reduce(state,{type:'push_return',anchor_id:token}).state;
  assert.equal(state.return_stack[0].anchor_id, token);
  const serialized=core.serializeQuery(state);assert.equal(serialized.ok,true);
  const result=core.parseQuery(serialized.query);assert.equal(result.ok,true);
  assert.deepEqual(result.state.compare_markets,['😀+%#']);assert.equal(result.state.library_group,token);
  assert.equal(result.state.return_stack.length,0);
});

test('16. a valid long context refuses oversize sharing without truncation', () => {
  const token='😀'.repeat(128);
  const core=coreModule.createIntlWorkspaceState(makeConfig({markets:[token]}));
  let state=core.reduce(core.initialState,{type:'pin',market_id:token}).state;
  state=core.reduce(state,{type:'select_market',market_id:token}).state;
  const before=clone(state);const result=core.serializeQuery(state);
  assert.equal(result.ok,false);assert.equal(result.query,null);assert.equal(result.issues[0].code,'QUERY_TOO_LONG');assert.deepEqual(state,before);
});

test('17. array accessors, holes and symbols refuse without invoking accessors', () => {
  let calls=0;
  const getterArray=[];Object.defineProperty(getterArray,'0',{enumerable:true,get(){calls++;throw Error('must not run');}});
  const symbolArray=['jp-auto'];symbolArray[Symbol('hidden')]=true;
  const sparseArray=Array(1);
  const exotic=['jp-auto'];Object.setPrototypeOf(exotic,null);
  for (const array of [getterArray,symbolArray,sparseArray,exotic]) {
    assert.throws(()=>coreModule.createIntlWorkspaceState(makeConfig({markets:array})),e=>e instanceof TypeError && e.code==='INVALID_CONFIG');
    const core=coreModule.createIntlWorkspaceState(makeConfig());
    const result=core.reduce({...core.initialState,compare_markets:array},{type:'resize'});
    assert.equal(result.ok,false);assert.equal(result.state,null);assert.equal(result.intent,null);assert.equal(result.issues[0].code,'INVALID_STATE');
  }
  assert.equal(calls,0);
});

test('18. malformed external ID types return closed errors and pin actions require an ID', () => {
  const core=coreModule.createIntlWorkspaceState(makeConfig());
  for(const value of [false,4,{},[],undefined]) {
    const result=core.reduce({...core.initialState,selected_market:value},{type:'resize'});
    assert.equal(result.ok,false);assert.equal(result.state,null);assert.equal(result.intent,null);assert.equal(result.issues[0].code,'INVALID_STATE');
  }
  for(const type of ['pin','unpin']) {
    const result=core.reduce(core.initialState,{type,market_id:null});
    assert.equal(result.ok,false);assert.equal(result.state,core.initialState);assert.equal(result.intent,null);
  }
});

test('19. exposed initial snapshots cannot poison subsequent parsed defaults', () => {
  const core=coreModule.createIntlWorkspaceState(makeConfig());
  core.initialState.compare_markets.push('jp-auto');core.initialState.horizon='bad';core.initialState.return_stack.push({private:'x'});
  const result=core.parseQuery('view=library');
  assert.equal(result.ok,true);assert.deepEqual(result.state.compare_markets,[]);assert.deepEqual(result.state.return_stack,[]);assert.equal(result.state.horizon,'1d');
});

test('20. factories remain independent and forged prior-source return contexts refuse', () => {
  const a=coreModule.createIntlWorkspaceState(makeConfig());const b=coreModule.createIntlWorkspaceState(makeConfig({source_reference:'src-2'}));
  const saved=a.reduce(a.initialState,{type:'push_return',anchor_id:'a-library'}).state;
  assert.equal(b.reduce(b.initialState,{type:'capture_baseline'}).ok,true);
  assert.equal(a.reduce(saved,{type:'back'}).ok,true);
  saved.return_stack[0].context.source_reference='src-2';
  const bad=a.reduce(saved,{type:'back'});assert.equal(bad.ok,false);assert.equal(bad.state,null);assert.equal(bad.issues[0].code,'INVALID_STATE');
});
