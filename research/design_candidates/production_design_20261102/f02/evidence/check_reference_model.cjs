/* Bounded source-model checks for known review defects. No browser, DOM, layout,
   event dispatch, account service, or Paper execution is performed here. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'pattern-lab.html'), 'utf8');
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'fixtures/company-history.json'), 'utf8'));
const script = html.split('<script>')[1].split('</script>')[0];
function section(start, end) {
  const a=script.indexOf(start), b=script.indexOf(end,a+start.length);
  assert(a>=0 && b>a, 'Expected source section: '+start);return script.slice(a,b);
}
const source = `const cfg={consumer:'macro',language:'en'};
const companyFixture=${JSON.stringify(fixture)};
const companyRows=companyFixture.rows;
const t=(en,zh)=>cfg.language==='zh'?zh:en;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
`+section('const macroRows =','// Pure transitions:')
 +section('function readSnapshot(','function apply(')
 +section('function noticeBox(','function chartSvg(')
 +section('function chartSvg(','function chart()')
 +section('function evidenceRecord(','function evidenceContent(')
 +section('function canInspectObservations()','function openEvidence(')
 +`globalThis.model={cfg,transition,readSnapshot,notice,evidenceRecord,canInspectObservations,chartSvg,macroRows,macroPoints,macroDates,companyRows,optionRows,expiryBuckets};`;
const context=vm.createContext({});vm.runInContext(source,context,{timeout:2000});
const m=context.model;
const plain=x=>JSON.parse(JSON.stringify(x));
let states=0, transitions=0;
for(const availability of ['loaded','loading','empty','unavailable','error','firstuse'])
for(const freshness of ['current','stale'])
for(const coverage of ['complete','partial'])
for(const access of ['member','guest','denied','expired'])
for(const write of ['idle','pending','saved','failed','uncertain']) {
  const state={availability,freshness,coverage,access,write};states++;
  for(const event of [{type:'SAVE_START'},{type:'SAVE_RESULT',outcome:'saved'},{type:'SAVE_RESULT',outcome:'failed'},{type:'SAVE_RESULT',outcome:'uncertain'},{type:'SAVE_CHECK',outcome:'saved'},{type:'ACCESS_CHANGE',access:'expired'},{type:'ACCESS_CHANGE',access:'denied'}]) {
    const next=m.transition(state,event);
    assert.deepEqual(plain(m.readSnapshot(next)),plain(m.readSnapshot(state)));
    if(event.type==='SAVE_START' && access!=='member')assert.equal(next.write,write);
    if(event.type==='ACCESS_CHANGE' && write==='pending')assert.equal(next.write,'uncertain');
    transitions++;
  }
}
let combined={consumer:'macro',language:'en',availability:'loaded',freshness:'stale',coverage:'partial',access:'member',write:'idle'};
combined=m.transition(combined,{type:'SAVE_START'});assert.equal(combined.write,'pending');
Object.assign(m.cfg,combined);const pendingNotice=m.notice();
assert.match(pendingNotice,/Older observations retained/);assert.match(pendingNotice,/Partial coverage/);
combined=m.transition(combined,{type:'SAVE_RESULT',outcome:'saved'});Object.assign(m.cfg,combined);
assert.equal(m.notice(),pendingNotice);
const expired=m.transition({...combined,write:'pending'},{type:'ACCESS_CHANGE',access:'expired'});
assert.equal(expired.write,'uncertain');Object.assign(m.cfg,expired);assert.match(m.notice(),/outcome is still unknown/);assert.doesNotMatch(m.notice(),/no change has been sent/);

const keys=[...m.macroRows.map((_,i)=>'macro-'+i),...m.companyRows.map((_,i)=>'company-'+i),...m.optionRows.map((_,i)=>'options-'+i),...m.macroPoints.map((_,i)=>'chart:macro:'+i),...fixture.periods.map((_,i)=>'chart:company:'+i),...m.expiryBuckets.map((_,i)=>'chart:options:'+i),'article'];
const ids=new Set();let records=0;
for(const key of keys) {
  Object.assign(m.cfg,{language:'en',consumer:'macro'});
  const r=m.evidenceRecord(key);assert(r.entity&&r.metric&&r.period&&r.unit&&r.sourceIdentity);
  assert(!ids.has(r.sourceIdentity), 'Identity collision: '+r.sourceIdentity);ids.add(r.sourceIdentity);records++;
  m.cfg.language='zh';assert.equal(m.evidenceRecord(key).sourceIdentity,r.sourceIdentity);
  if(r.consumer==='company')assert.match(r.entity,/EXM/);
}
m.cfg.language='en';
for(let i=0;i<2;i++) {
  const r=m.evidenceRecord('chart:options:'+i);
  assert.match(r.period,/2026-10-30/);assert.match(r.period,/15:47:31–15:58:42/);
  assert(!r.period.includes(m.expiryBuckets[i].expiry));
  assert(r.dimensions.some(([k,v])=>k==='Contract expiry bucket'&&v===m.expiryBuckets[i].expiry));
  assert(r.dimensions.some(([k,v])=>k==='Contributing print identities'&&v.includes('print-')));
}
const dividendIndex=fixture.rows.findIndex(r=>r[0]==='Dividend per share');
const dividend=m.evidenceRecord('company-'+dividendIndex);assert(dividend.values.some(([k,v])=>String(v)==='0.00 USD/share'));assert.match(dividend.notes,/undefined/);
for(const consumer of ['macro','company','options','editorial']) {
  const overview=m.evidenceRecord('overview:'+consumer);assert.equal(overview.consumer,consumer);assert(overview.sourceIdentity.includes(consumer==='company'?'company/EXM':consumer));
}
assert.throws(()=>m.evidenceRecord('overview:unsupported'),/Unsupported overview consumer/);
const overview=m.evidenceRecord('overview:options');assert.match(overview.sourceIdentity,/total_observed_premium/);assert(overview.values.some(([k,v])=>v==='USD 4,544,000'));

let observationAdmissionCases=0;
for(const consumer of ['macro','company','options','editorial'])for(const access of ['member','guest','denied','expired'])for(const availability of ['loaded','error','loading','empty','unavailable','firstuse']) {
  Object.assign(m.cfg,{consumer,access,availability});assert.equal(m.canInspectObservations(),consumer==='editorial'||(['member','guest'].includes(access)&&['loaded','error'].includes(availability)));observationAdmissionCases++;
}
const geometry=[];
for(const consumer of ['macro','options','company'])for(const width of [288,358,740,1024]) {
  m.cfg.consumer=consumer;const svg=m.chartSvg(width), expected=consumer==='company'?Math.max(840,width):width;
  assert(svg.includes(`viewBox="0 0 ${expected} `));assert(svg.includes(`style="width:${expected}px;`));
  assert(!svg.includes('undefined'));geometry.push({consumer,container_width:width,svg_css_width:expected,kind:consumer==='company'&&width<840?'scoped_horizontal_scroll':'responsive_geometry'});
}
assert.equal(fixture.periods.length,17);assert.equal(fixture.series.length,5);
fixture.series.forEach(s=>assert.equal(s.values.length,17));
assert.deepEqual(fixture.statement_periods,[2022,2023,2024,2025,2026]);
assert.match(html,/<main id="main" tabindex="-1" lang="en">/);
assert.match(html,/<section class="lab" aria-label="Specimen controls" lang="en">/);
assert.match(html,/<a class="skip" href="#main" lang="en">/);
assert.match(html,/data-evidence[^]*el\.dataset\.evidence===key&&el\.getClientRects\(\)\.length/);
assert.equal(m.optionRows.reduce((a,r)=>a+r.premium,0),4544000);
const report={observed_at:new Date().toISOString(),scope:'Pure source-model, fixture, identity and generated-SVG-text checks. No browser, DOM, focus, scroll, pixel, font, input, service or Paper execution.',html_sha256:crypto.createHash('sha256').update(html).digest('hex'),result:'PASS_WITH_SCOPE_LIMITS',state_combinations:states,read_invariance_transitions:transitions,combined_stale_partial_pending_saved_warnings:'unchanged',pending_then_access_expired:'uncertain',evidence_records_checked:records,overview_entrypoints_checked:4,observation_admission_cases:observationAdmissionCases,identity_uniqueness:'pass for distinct observations; overview aliases are deliberate references to the same observation',language_invariant_identities:'pass',options_observed_window_and_expiry:'separate',company:{fiscal_periods:17,series:5,statement_columns:5},chart_source_geometry:geometry,remaining_runtime_checks:['keyboard and touch evidence return','focus and scroll after sort/filter','actual chart label size and CJK glyphs','400 percent zoom and reduced/forced-color rendering','real source/access/save integration']};
fs.writeFileSync(path.join(__dirname,'repair-model-verification.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({result:report.result,states,transitions,records,company:report.company}));
