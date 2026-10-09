/* Research regression harness. Executes the exact extracted production selector.
   This is not the full template, browser, entitled feed, or a production change. */
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const path = require('node:path');
const sourcePath = process.argv[2] || path.join(__dirname, 'plv_mode_original.js');
const source = fs.readFileSync(sourcePath, 'utf8');
const resultsPath = process.argv[3];
const originalHash = '98b7605cd1ee31ff5dd7061df0fc1c488e56a452a09d13379ceb6c953a9de62e';
const originalBytes = fs.readFileSync(path.join(__dirname, 'plv_mode_original.js'));
if (crypto.createHash('sha256').update(originalBytes).digest('hex') !== originalHash) {
  throw new Error('Immutable original selector does not match the host-read hash');
}
const DAY = '2026-09-10';
function evaluate({min, passMin=min, dark=0, n=175, status='ok', reason,
                   session=DAY, wd='Thu', unknown=0, overrides={}, counts}) {
  const now = Date.parse(DAY+'T00:00:00Z') + (min+240)*60000;
  class FixedDate extends Date { static now(){ return now; } }
  const context = { Date: FixedDate, Number, isFinite,
    PLV_WAKE:560, PLV_SETTLE:1110, PLV_FIRST:575,
    PLV_SHUT:980, PLV_CLOSE_PASS:945, PLV_MAXAGE:900000,
    // The surrounding clock adapter is supplied; the selector itself is unmodified.
    _plvTsMin(iso) {
      if(!iso || !Number.isFinite(Date.parse(iso))) return null;
      const p = new Intl.DateTimeFormat('en-GB', {
        timeZone:'America/New_York', hour:'2-digit', minute:'2-digit', hourCycle:'h23'
      }).formatToParts(new Date(iso));
      return Number(p.find(x=>x.type==='hour').value)*60 + Number(p.find(x=>x.type==='minute').value);
    }
  };
  vm.createContext(context);
  vm.runInContext(source, context, {timeout:1000});
  const data = {status, reason, meta:{
    session_et:session,
    pass_ts:new Date(Date.parse(DAY+'T00:00:00Z')+(passMin+240)*60000).toISOString(),
    dark_counts:counts || {no_quote:dark}, evaluated_n:n, unknown_counts:{out_of_band:unknown},
    ...overrides
  },states:{}};
  const before = JSON.stringify(data);
  const out = context._plvMode(data, {wd,min,ymd:DAY});
  if (JSON.stringify(data)!==before) throw new Error('Selector mutated input');
  return out===null ? null : {mode:out.mode,why:out.why};
}
const D={mode:'dark',why:'quotes'}, C={mode:'closed',why:null}, L={mode:'live',why:null};
const cases=[
  ['postclose_166_of_175_unreadable',{min:983,passMin:980,dark:166},{mode:'dark',why:'coverage'}],
  ['postclose_exactly_half_unreadable',{min:990,passMin:970,dark:50,n:100},{mode:'dark',why:'coverage'}],
  ['postclose_all_unreadable',{min:1000,passMin:975,dark:175},{mode:'dark',why:'coverage'}],
  ['postclose_aggregate_reasons',{min:1000,passMin:975,counts:{no_quote:80,stale_quote:86}},{mode:'dark',why:'coverage'}],
  ['postclose_stays_degraded_until_handoff',{min:1109,passMin:980,dark:166},{mode:'dark',why:'coverage'}],
  ['rth_166_of_175_unreadable',{min:900,passMin:897,dark:166},D],
  ['rth_exactly_half',{min:900,passMin:897,dark:50,n:100},D],
  ['rth_below_existing_half_cliff',{min:900,passMin:897,dark:49,n:100},L],
  ['postclose_healthy_not_clock_stale',{min:1109,passMin:980,dark:0},C],
  ['postclose_below_existing_half_cliff',{min:1000,passMin:975,dark:49,n:100},C],
  ['postclose_unknown_is_not_dark',{min:1000,passMin:975,unknown:166},C],
  ['postclose_no_near_close_pass',{min:1000,passMin:840},D],
  ['postclose_exact_close_pass_boundary',{min:1000,passMin:945},C],
  ['postclose_below_close_pass_boundary',{min:1000,passMin:944},D],
  ['postclose_bad_timestamp',{min:1000,overrides:{pass_ts:'not-a-date'}},D],
  ['postclose_producer_no_pack',{min:1000,passMin:980,status:'dark',reason:'no_pack'}, {mode:'dark',why:'no_pack'}],
  ['postclose_producer_stale_pack',{min:1000,passMin:980,status:'dark',reason:'stale_pack'}, {mode:'dark',why:'stale_pack'}],
  ['rth_producer_no_pack',{min:900,status:'dark',reason:'no_pack'}, {mode:'dark',why:'no_pack'}],
  ['previous_session_names_fact',{min:1000,session:'2026-09-09'}, {mode:'dark',why:'none_today'}],
  ['before_first_pass_previous_session_hidden',{min:570,session:'2026-09-09'},null],
  ['weekend_hidden',{min:1000,wd:'Sat',dark:166},null],
  ['before_wake_hidden',{min:559,dark:166},null],
  ['nightly_handoff_hidden',{min:1110,dark:166},null],
  ['rth_old_observation_dark',{min:900,passMin:880},D],
  ['shut_boundary_quality_checked',{min:980,passMin:975,dark:166},D],
  ['healthy_rth',{min:900,passMin:899},L],
  ['healthy_postclose',{min:983,passMin:980},C],
  ['inherited_counts_are_ignored',{min:1000,passMin:975,counts:Object.assign(Object.create({foreign:10000}),{no_quote:0})},C]
];
const results = cases.map(([name,args,expected])=> {
  let actual, error;
  try {actual=evaluate(args);} catch(e) {error=e.message;}
  const passed=!error && JSON.stringify(actual)===JSON.stringify(expected);
  return {name,passed,actual,expected,...(error?{error}:{})};
});
const report={kind:'exact-source-selector-regression',source_sha256:crypto.createHash('sha256').update(source).digest('hex'),
  original_source_sha256:originalHash,source_repository_commit:'6e1fb2ab35f68bbaf3695ffee5fe5ba268e46bae',
  source_file:'templates/dashboard.html.j2',production_modified:false,browser_proof:false,
  tests:results.length,passed:results.filter(x=>x.passed).length,failed:results.filter(x=>!x.passed).length,results};
if(resultsPath) fs.writeFileSync(resultsPath,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({tests:report.tests,passed:report.passed,failed:report.failed,failures:results.filter(x=>!x.passed)},null,2));
process.exitCode=report.failed?1:0;
