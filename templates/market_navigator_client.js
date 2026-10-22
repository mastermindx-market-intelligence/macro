/* Read-only request consumer. No auto-mount, endpoint, auth, storage, retry or CSS.
 * The incumbent application supplies read(request, signal) and render(state).
 * Loading clears old context atomically. Correlation is not source authenticity.
 */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MastermindNavigatorClient = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var H = ['intraday', 'swing', 'position'];
  var A = ['signal','probability','ranking','sizing','trading','auto_exit','alert_escalation'];
  var UNITS = ['USD','percent','ratio','vol_points','basis_points','contracts','index_points'];
  var OBS = ['current','missing','stale','not_yet_available','unqualified','subject_mismatch','horizon_mismatch'];
  var MARKET = ['current','missing','stale','not_yet_available','unsupported_verdict','asof_mismatch','session_unverified','session_completion_unverified','degraded'];
  var STATES = ['waiting','conditions_met','invalidated','unresolved','expired','subject_mismatch','horizon_mismatch'];
  var ID = /^[a-z][a-z0-9_-]{0,63}$/;
  var REQUEST = /^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$/;
  var CLOCK = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/;
  function fail() { throw new Error('Invalid Navigator response'); }
  function obj(x, fields) {
    if (!x || typeof x !== 'object' || Array.isArray(x) || Object.getPrototypeOf(x) !== Object.prototype) fail();
    var keys = Object.keys(x).sort();
    if (keys.length !== fields.length || keys.some(function(k,i){return k !== fields.slice().sort()[i];})) fail();
  }
  function member(x, list) { if (list.indexOf(x) < 0) fail(); }
  function id(x) { if (typeof x !== 'string' || !ID.test(x)) fail(); }
  function clock(x, nullable) {
    if (x === null && nullable) return;
    if (typeof x !== 'string' || !CLOCK.test(x) || !Number.isFinite(Date.parse(x))) fail();
  }
  function micros(x) {
    clock(x,false);
    var m=x.match(/^(.*T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(Z|[+-]\d{2}:\d{2})$/);
    var fraction=(m[2] || '').padEnd(6,'0');
    return BigInt(Date.parse(m[1]+'.'+fraction.slice(0,3)+m[3]))*1000n+BigInt(fraction.slice(3));
  }
  function finite(x) { if (typeof x !== 'number' || !Number.isFinite(x)) fail(); }
  function list(x, max) { if (!Array.isArray(x) || x.length > max) fail(); }
  function unique(rows, key) {
    var seen = new Set(); rows.forEach(function(r){if (seen.has(r[key])) fail(); seen.add(r[key]);});
  }
  function authority(x) { obj(x,A); A.forEach(function(k){if (x[k] !== false) fail();}); }
  function evidence(x) {obj(x,['key','status']);id(x.key);member(x.status,OBS);}
  function condition(x) {
    obj(x,['observation','op','threshold','unit','met','reason']);id(x.observation);
    member(x.op,['gt','gte','lt','lte']);finite(x.threshold);member(x.unit,UNITS);
    if (x.met !== null && typeof x.met !== 'boolean') fail();
    member(x.reason,OBS.concat(['unit_mismatch']));
  }
  function context(x) {
    obj(x,['schema','horizon','as_of','canonical_market','observations','scenarios','coincident_conditions','readiness','authority']);
    if(x.schema !== 'market_navigator.context/v1' || x.readiness !== 'research_only')fail();
    member(x.horizon,H);clock(x.as_of,false);authority(x.authority);
    if(typeof x.coincident_conditions !== 'boolean') fail();
    var m=x.canonical_market;
    obj(m,['status','verdict','asof','observed_at','available_at','valid_until']);member(m.status,MARKET);
    if(m.status==='current') member(m.verdict,['RISK_ON','MIXED','RISK_OFF']); else if(m.verdict!==null) fail();
    if(m.asof!==null && (typeof m.asof!=='string' || !/^\d{4}-\d{2}-\d{2}$/.test(m.asof)))fail();
    ['observed_at','available_at','valid_until'].forEach(function(k){clock(m[k],true);});
    if(m.status==='current' && [m.asof,m.observed_at,m.available_at,m.valid_until].indexOf(null)>=0)fail();
    list(x.observations,128);unique(x.observations,'key');
    x.observations.forEach(function(r){
      obj(r,['key','family','status','value','unit','quality','observed_at','available_at','valid_until']);
      id(r.key);member(r.family,['price','breadth','volatility','positioning','macro','event','liquidity']);
      member(r.status,OBS);member(r.unit,UNITS);member(r.quality,['observed','estimated','user_claim','synthetic']);
      if(r.status==='current') {finite(r.value);member(r.quality,['observed','estimated']);}
      else if(r.value!==null)fail();
      ['observed_at','available_at','valid_until'].forEach(function(k){clock(r[k],true);});
      if(r.status==='current' && [r.observed_at,r.available_at,r.valid_until].indexOf(null)>=0)fail();
    });
    list(x.scenarios,12);unique(x.scenarios,'key');
    x.scenarios.forEach(function(s){
      obj(s,['key','horizon','definition_available_at','deadline','status','probability','triggers','invalidations','support','counterevidence']);
      id(s.key);member(s.horizon,H);member(s.status,STATES);clock(s.definition_available_at,false);clock(s.deadline,false);
      if(s.probability!==null)fail();
      ['triggers','invalidations'].forEach(function(k){list(s[k],16);s[k].forEach(condition);});
      ['support','counterevidence'].forEach(function(k){list(s[k],128);s[k].forEach(evidence);});
    });
  }
  function freeze(x) { if(x && typeof x==='object'){Object.values(x).forEach(freeze);Object.freeze(x);} return x; }
  function validate(wire, request) {
    obj(wire,['schema','request_id','requested_as_of','horizon','data']);
    if(wire.schema!=='market_navigator.response/v1' || wire.request_id!==request.request_id ||
       wire.requested_as_of!==request.as_of || wire.horizon!==request.horizon)fail();
    if(typeof wire.request_id!=='string' || !REQUEST.test(wire.request_id))fail();
    clock(wire.requested_as_of,false);context(wire.data);
    if(wire.data.horizon!==request.horizon || micros(wire.data.as_of)!==micros(request.as_of))fail();
    if(new TextEncoder().encode(JSON.stringify(wire)).length>80*1024)fail();
    return freeze(JSON.parse(JSON.stringify(wire.data)));
  }
  function createController(options) {
    if(!options || typeof options.read!=='function' || typeof options.render!=='function')fail();
    var epoch=0, abort=null, disposed=false;
    function reset(status) {
      epoch++;if(abort)abort.abort();abort=null;
      if(!disposed)options.render(freeze({status:status,data:null}));
    }
    async function load(query) {
      if(disposed)throw new Error('Navigator client disposed');
      if(!query || typeof query.subject!=='string' || !query.subject || query.subject.length>128)fail();
      member(query.horizon,H);clock(query.as_of,false);
      reset('loading');var turn=epoch;
      abort=new AbortController();
      var request=freeze({request_id:'navigator-'+turn,subject:query.subject,horizon:query.horizon,as_of:query.as_of});
      var wire;
      try {wire=await options.read(request,abort.signal);}
      catch(_error) {if(turn===epoch && !disposed)options.render(freeze({status:'unavailable',data:null}));return;}
      if(turn!==epoch || disposed)return;
      var data;
      try {data=validate(wire,request);}
      catch(_error) {options.render(freeze({status:'invalid_response',data:null}));return;}
      options.render(freeze({status:'recorded_context',data:data}));
    }
    return Object.freeze({load:load,clear:function(){reset('empty');},dispose:function(){reset('empty');disposed=true;}});
  }
  return Object.freeze({validate:validate,createController:createController});
}));
