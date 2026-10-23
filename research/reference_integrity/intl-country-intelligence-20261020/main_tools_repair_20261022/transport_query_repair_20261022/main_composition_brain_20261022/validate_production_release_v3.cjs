'use strict';
// Local read-only release-chain verifier. Receipts must be collected from actual
// GitHub runs and the incumbent host by the owner; this module creates no receipts
// and does not turn a supplied PASS label into evidence.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
module.exports=function({release,at,ancestor,hash,repository,artifact}){
  const digest=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
  const sha=x=>typeof x==='string'&&/^[a-f0-9]{40}$/.test(x);
  // Owner-reviewed composition identities must be filled from actual immutable
  // source/build evidence. Invalid placeholders block every release assertion.
  const composition=Object.freeze({
  "source_commit": "PENDING_ACTUAL_INTEGRATED_SOURCE_COMMIT",
  "evidence_commit": "PENDING_COMMIT_RETAINING_ACTUAL_COMPOSITION_BUILD_RECEIPT",
  "frozen_reference_main": "24559ffa06bcf06fa8e9f36bb7e078412bd769fe",
  "build_receipt_sha256": "PENDING_ACTUAL_COMPOSITION_BUILD_RECEIPT_SHA256",
  "build_receipt_git_blob": "PENDING_ACTUAL_COMPOSITION_BUILD_RECEIPT_GIT_BLOB",
  "build_driver_sha256": "73bdd3087b0c55542731cf318ace953e046e1b5415b45c755d41049ba4c0a8ce",
  "input_snapshot_sha256": "081592644c4f2d425fdde59d7b8e153e4aa214aa00d115ba64b13bd31c145b08"
});
  for(const key of ['source_commit','evidence_commit','frozen_reference_main','build_receipt_git_blob'])
    assert(sha(composition[key]),'Unresolved immutable composition identity: '+key);
  for(const key of ['build_receipt_sha256','build_driver_sha256','input_snapshot_sha256'])
    assert(digest(composition[key]),'Unresolved composition digest: '+key);
  const brainRoutes=Object.freeze(["mm_brain_presentation.js", "mm_brain_markdown.js", "mm_brain_finance.js", "mm_brain_finance.css", "mm_brain_finance_math_v1.js", "mm_brain_math.js", "mm_brain_visuals.js"]);
  // Five changed baseline pins and eight explicitly added authored dependencies.
  const compositionPins=Object.freeze({
  "app/deploy/Caddyfile": {
    "bytes": 78752,
    "sha256": "772fe073605bd0b8d509dc1a1b87720de0e40d23238fe6b8d35d420be4c0a413"
  },
  "config/site_access.yml": {
    "bytes": 45402,
    "sha256": "7655ce8e47f66069e77119fadbe1620632746f89697b841ef7e8abf44b77cf09"
  },
  "site/theme.js": {
    "bytes": 275110,
    "sha256": "25617108b24d273d63f5be0c7b5516f316a34d2201a54e0ac3012bf2fdf1da46"
  },
  "templates/mm_brain.js": {
    "bytes": 290712,
    "sha256": "e7dce73797a01db5d115eaef6c19e24fa866b0f95206f7d36444252cc2c1511c"
  },
  "templates/mm_brain_visuals.css": {
    "bytes": 8630,
    "sha256": "b9f2e19510af08c7985c5633e43d5a7027921fa1cc75e0651bd2b9d3f8601527"
  },
  "templates/mm_brain_presentation.js": {
    "bytes": 4272,
    "sha256": "88e1f94bdbbc39bbe5f6e1ba5044b9f750aefc0a2853514389422902a87d7119"
  },
  "templates/mm_brain_markdown.js": {
    "bytes": 4813,
    "sha256": "9b93741c080f399416f60ffd1c276b6fc77157befc97c11312a1a061d87e0a36"
  },
  "templates/mm_brain_finance.js": {
    "bytes": 31045,
    "sha256": "a8f801ae918f3df77edb7e506ea18b93be766e99142a1efbc1d3c86f2a4426ca"
  },
  "templates/mm_brain_finance.css": {
    "bytes": 10296,
    "sha256": "b317487a9c44f06615cb74553376879cf6c12e8d9c9cd91e78c28598b584d983"
  },
  "templates/mm_brain_finance_math_v1.js": {
    "bytes": 11561,
    "sha256": "b20772591c20b5d04a64c433472e1ccc66231116b42db891bac3b88fbe74447f"
  },
  "templates/mm_brain_math.js": {
    "bytes": 268932,
    "sha256": "e24d5a2c1fba95bc0966babfbb8d85ff7bd559a22c8858cc35df009472b3e9ed"
  },
  "templates/mm_brain_visuals.js": {
    "bytes": 17984,
    "sha256": "2e3ce3a587eae8205727e0be20154eae1b9ddc45e8bb94ac8b3ca4949689339f"
  },
  "templates/theme.js": {
    "bytes": 393858,
    "sha256": "b4ec59cc65ea28456626f76719104b2f8a6e5f7cf37135c48667d91c51e2bcd1"
  }
});
  const gitBlob=b=>require('node:crypto').createHash('sha1').update(Buffer.from('blob '+b.length+'\0')).update(b).digest('hex');
  const receipts=[];
  function readReceipt(descriptor,label){
    assert(descriptor&&typeof descriptor.path==='string'&&path.isAbsolute(descriptor.path)&&digest(descriptor.sha256),label+' descriptor missing');
    const stat=fs.statSync(descriptor.path);assert(stat.isFile()&&stat.size>0&&stat.size<=64*1024*1024,label+' size/type');
    const b=fs.readFileSync(descriptor.path);assert.equal(hash(b),descriptor.sha256,label+' exact receipt hash');
    receipts.push({label,path:descriptor.path,sha256:hash(b),bytes:b.length});return JSON.parse(b);
  }
  function readLog(descriptor,label){
    assert(descriptor&&path.isAbsolute(descriptor.path)&&digest(descriptor.sha256),label+' descriptor');
    const s=fs.statSync(descriptor.path);assert(s.isFile()&&s.size>0&&s.size<=64*1024*1024,label+' finite log');
    const b=fs.readFileSync(descriptor.path);assert.equal(hash(b),descriptor.sha256,label+' log hash');
    receipts.push({label,path:descriptor.path,sha256:hash(b),bytes:b.length});return b.toString();
  }
  const git=(...args)=>execFileSync('git',['-C',repository,...args],{maxBuffer:8*1024*1024,timeout:60000}).toString().trim();
  const utc=x=>{assert(typeof x==='string'&&/(Z|[+]00:00)$/.test(x),'UTC instant required');const n=Date.parse(x);assert(Number.isFinite(n),'Invalid time');return n;};
  const repoName='mastermindx-market-intelligence/macro';
  function workflow(descriptor,expectedName,id){
    const run=readReceipt(descriptor,expectedName+' GitHub API');
    assert.equal(String(run.id),String(id),'Workflow ID');assert.equal(run.repository.full_name,repoName,'Workflow repository');
    assert.equal(run.path,'.github/workflows/'+expectedName+'.yml','Workflow path');
    assert.equal(run.head_branch,'main','Workflow main branch');assert.equal(run.status,'completed','Workflow completed');assert.equal(run.conclusion,'success','Workflow success');
    assert(sha(run.head_sha),'Workflow immutable head');assert(utc(run.updated_at)>=utc(run.run_started_at),'Workflow clock order');
    return run;
  }
  function workflowJob(section,run,requiredStepPrefixes){
    const job=readReceipt(section.job_receipt,'actual workflow job');
    assert.equal(String(job.id),String(section.job_id),'Job identity');assert.equal(String(job.run_id),String(run.id),'Job belongs to actual run');
    assert.equal(job.status,'completed');assert.equal(job.conclusion,'success');
    for(const prefix of requiredStepPrefixes){
      const steps=job.steps.filter(x=>x.name.startsWith(prefix));assert.equal(steps.length,1,'One actual required step: '+prefix);
      assert.equal(steps[0].status,'completed');assert.equal(steps[0].conclusion,'success');
    }
    assert.equal(section.job_log.url,'https://api.github.com/repos/'+repoName+'/actions/jobs/'+job.id+'/logs','Exact fetched job-log source');
    return job;
  }
  function cleanLog(raw){return raw.split(/\r?\n/).map(x=>x.replace(/\x1b\[[0-9;]*m/g,'').replace(/^\d{4}-\d\d-\d\dT\S+Z\s+/,''));}
  function publishedByNormalPush(log,published,label){
    const lines=cleanLog(log),pushes=[];
    for(let i=0;i<lines.length;i++){
      const m=lines[i].match(/^\s*([a-f0-9]{7,40})\.\.([a-f0-9]{7,40})\s+([^\s]+)\s+->\s+(?:refs\/heads\/)?main\s*$/);
      if(!m)continue;
      const target=git('rev-parse','--verify',m[2]+'^{commit}');
      const expectedNotice=label==='acquisition'?/^pushed backfill on attempt \d+$/:/^pushed rendered site on attempt \d+(?: \(metadata-only replay\))?$/;
      const notice=lines.slice(i+1,i+31).find(x=>expectedNotice.test(x.trim()));
      if(notice)pushes.push({old:m[1],new:m[2],source_ref:m[3],target_commit:target,push_line:lines[i],completion_notice:notice});
    }
    assert(pushes.length>0,label+' actual successful non-force push-to-main evidence');
    const match=pushes.filter(x=>x.target_commit===published);assert.equal(match.length,1,label+' exact selected publication was pushed by this run');
    return match[0];
  }

  // These immutable records contain the independently reviewed 34/84 inventories.
  const Q='research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022';
  const broadBytes=at(release.accepted_candidate,Q+'/pending_scenario_20261022/COMMITTED_SOURCE_REVIEW_BINDING.json');
  const priorBytes=at(release.accepted_candidate,Q+'/pending_scenario_20261022/LATEST_MAIN_PREPUBLICATION_APPLICABILITY.json');
  assert.equal(hash(broadBytes),'2f308d4d33007ce1664193e7a91c2228cc6f85f0af65fb338e57f4ced8906ed8','Reviewed broad inventory');
  assert.equal(hash(priorBytes),'6de4c61f9adf8b47988c5e37a53f86c590493606a0efb4a2b53716b38db48aae','Reviewed presentation inventory');
  const broad=JSON.parse(broadBytes),prior=JSON.parse(priorBytes);
  assert.equal(broad.data_logic_files.length,34);assert.equal(prior.files.length,84);
  const reviewed='bdeb609bf11a170c39713461eace85b47d2ca18c';
  assert.equal(broad.source_commit,reviewed);assert.equal(prior.subject,reviewed);
  const baselineBuildBytes=at(release.accepted_candidate,Q+'/repair_scenariopop20261022_build_receipt.json');
  assert.equal(hash(baselineBuildBytes),'e71ab39a7f7d132f83871a574c177d419b6526c942af29f780aa68e008ab39b3','Reviewed baseline build inventory');
  const baselineBuild=JSON.parse(baselineBuildBytes);assert.equal(baselineBuild.source_commit,reviewed);assert.equal(baselineBuild.files.length,44);assert.deepEqual(baselineBuild.source_overlays,[]);
  assert(ancestor(composition.frozen_reference_main,composition.source_commit),'Actual composition source integrates the frozen upstream main');
  assert(ancestor(composition.source_commit,composition.evidence_commit),'Actual source precedes its retained build evidence');
  assert(ancestor(composition.evidence_commit,release.accepted_candidate),'Candidate retains the actual composition evidence commit');
  const compositionRoot=Q+'/main_composition_brain_20261022';
  const buildReceiptPath=compositionRoot+'/repair_braincomposition20261022_build_receipt.json';
  const buildBytes=at(composition.evidence_commit,buildReceiptPath);
  assert.equal(hash(buildBytes),composition.build_receipt_sha256,'Actual composition receipt hash');
  assert.equal(gitBlob(buildBytes),composition.build_receipt_git_blob,'Actual composition receipt Git blob');
  assert(at(release.accepted_candidate,buildReceiptPath).equals(buildBytes),'Candidate retains exact composition receipt');
  const build=JSON.parse(buildBytes);
  assert.equal(build.schema,'intl.current_main_build.v1');assert.equal(build.source_commit,composition.source_commit);
  assert.equal(build.static_dependency_source_commit,composition.source_commit);assert.deepEqual(build.source_overlays,[]);
  assert.equal(build.build_driver_sha256,composition.build_driver_sha256);assert.equal(build.exit_code,0);
  assert.equal(build.source_reacquisition,false);assert.equal(build.production_mutation,false);
  assert.equal(build.kind,'ordinary builder with copied existing production stores');
  assert.equal(build.artifact_inventory_kind,'build output plus required static dependency inventory');
  assert.equal(build.input_snapshot,'../../../production_input_snapshot.json');
  assert.equal(build.input_snapshot_sha256,composition.input_snapshot_sha256);
  assert(Array.isArray(build.command)&&build.command.length===3&&path.isAbsolute(build.command[0]),'Exact ordinary builder command');
  assert.deepEqual(build.command.slice(1),['-m','scripts.build_intl']);
  assert(utc(build.finished_at)>=utc(build.started_at),'Composition build time order');
  const inputSnapshotBytes=at(composition.evidence_commit,'research/reference_integrity/intl-country-intelligence-20261020/production_input_snapshot.json');
  assert.equal(hash(inputSnapshotBytes),composition.input_snapshot_sha256,'Retained production snapshot identity');
  const inputSnapshot=JSON.parse(inputSnapshotBytes);
  assert.equal(inputSnapshot.files.length,510);assert.equal(new Set(inputSnapshot.files.map(x=>x.path)).size,510);
  function inventoryRows(receipt,prefix,count){
    assert.equal(receipt.files.length,count);const rows=new Map();
    for(const row of receipt.files){
      assert(typeof row.path==='string'&&row.path.startsWith(prefix),'Receipt output stays within its exact artifact directory');
      const name=row.path.slice(prefix.length);
      assert(name&&!name.startsWith('/')&&!name.includes('\\')&&name.split('/').every(part=>/^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(part)&&part!=='.'&&part!=='..'),'Safe exact public-relative artifact route');
      assert(!rows.has(name)&&digest(row.sha256)&&Number.isSafeInteger(row.bytes)&&row.bytes>0,'Unique bounded artifact identity');
      assert(row.source_path==='site/'+name||row.source_path==='templates/'+name,'Exact public-relative static source route');
      rows.set(name,row);
    }
    return rows;
  }
  const baselineRows=inventoryRows(baselineBuild,Q+'/proposed_scenariopop20261022_repair/',44);
  const buildRows=inventoryRows(build,compositionRoot+'/proposed_braincomposition20261022_repair/',51);
  const reviewedPublicRoutes=[...buildRows.keys()].sort();
  assert.deepEqual(reviewedPublicRoutes,[...baselineRows.keys(),...brainRoutes].sort(),'Exactly the old 44 routes plus seven explicit Brain dependencies');
  for(const [name,row] of baselineRows)assert.equal(buildRows.get(name).source_path,row.source_path,name+' original static source route preserved');
  for(const name of brainRoutes){
    const row=buildRows.get(name),pin=compositionPins['templates/'+name];
    assert.equal(row.source_path,'templates/'+name,name+' explicit added authored dependency');
    assert.equal(row.sha256,pin.sha256);assert.equal(row.bytes,pin.bytes);
  }
  assert.equal(build.html_sha256,buildRows.get('intl.html').sha256);assert.equal(build.html_bytes,buildRows.get('intl.html').bytes);
  const templateProgram=String.raw`import sys,subprocess,json
from jinja2 import Environment,meta,nodes
repo,subject=sys.argv[1:]
env=Environment(extensions=['jinja2.ext.do','jinja2.ext.loopcontrols'])
seen=set();todo=['intl.html.j2'];optional=set();absent=set();qualified=[]
workspace_names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',subject,'--','templates/intl_workspace'],timeout=30).decode().splitlines()
workspace_templates=sorted(x.removeprefix('templates/') for x in workspace_names if x.endswith('.html.j2'))
if not workspace_templates:raise ValueError('Missing bounded workspace template inventory')
while todo:
 name=todo.pop()
 if name in seen or name in absent:continue
 if name.startswith('/') or '..' in name.split('/'):raise ValueError('Escaped template dependency')
 result=subprocess.run(['git','-C',repo,'show',subject+':templates/'+name],capture_output=True,timeout=30)
 if result.returncode:
  if name in optional:absent.add(name);continue
  raise ValueError('Missing required template dependency: '+name)
 raw=result.stdout
 if len(raw)>16*1024*1024:raise ValueError('Oversized template')
 tree=env.parse(raw.decode('utf-8'))
 children=list(meta.find_referenced_templates(tree))
 for include in tree.find_all(nodes.Include):
  if include.ignore_missing and isinstance(include.template,nodes.Const) and isinstance(include.template.value,str):optional.add(include.template.value)
 if any(x is None for x in children):
  dynamic=[x.template for x in tree.find_all(nodes.Include) if not isinstance(x.template,(nodes.Const,nodes.Tuple,nodes.List))]
  if name!='intl_workspace/shell.html.j2' or len(dynamic)!=1:raise ValueError('Unqualified dynamic template dependency: '+name)
  expr=dynamic[0]
  if not (isinstance(expr,nodes.Concat) and len(expr.nodes)==3 and isinstance(expr.nodes[0],nodes.Const) and expr.nodes[0].value=='intl_workspace/' and isinstance(expr.nodes[1],nodes.Getattr) and expr.nodes[1].attr=='view' and isinstance(expr.nodes[1].node,nodes.Name) and expr.nodes[1].node.name=='panel' and isinstance(expr.nodes[2],nodes.Const) and expr.nodes[2].value=='.html.j2'):raise ValueError('Dynamic include differs from the exact reviewed GS seam')
  children=[x for x in children if x is not None]+workspace_templates
  qualified.append({'template':name,'expression':"'intl_workspace/' ~ panel.view ~ '.html.j2'",'bound_complete_workspace_templates':workspace_templates,'scope':'Every existing workspace template is source pinned; this does not claim disabled future GS builders are available.'})
 seen.add(name);todo.extend(children)
print(json.dumps({'paths':sorted('templates/'+x for x in seen),'absent_optional_templates':sorted('templates/'+x for x in absent),'qualifications':sorted(qualified,key=lambda x:x['template'])}))`;
  const closureReceipt=JSON.parse(execFileSync('/tmp/intl-country-cockpit-ci-20261021/bin/python',['-c',templateProgram,repository,reviewed],{maxBuffer:1024*1024,timeout:120000}));
  for(const [label,subject] of [['composition source',composition.source_commit],['candidate',release.accepted_candidate],['adopted main',release.accepted_main],['actual render source',release.render.source_commit]]){
    const actualClosureReceipt=JSON.parse(execFileSync('/tmp/intl-country-cockpit-ci-20261021/bin/python',['-c',templateProgram,repository,subject],{maxBuffer:1024*1024,timeout:120000}));
    assert.deepEqual(actualClosureReceipt,closureReceipt,label+' actual template closure, full dynamic subtree and optional absence match reviewed source');
  }
  const closure=closureReceipt.paths;
  for(const suffix of ['.html.j2','.css','.js'])assert(closure.includes('templates/intl_country_cockpit'+suffix),'Country inline source closure');
  const generatedOutputPaths=['site/intl.html'];
  const authored=x=>x!=='.github/ci/legacy-jobs.yml'&&!generatedOutputPaths.includes(x);
  const baselineSourcePaths=[...new Set([...broad.data_logic_files.map(x=>x.path),...broad.corrected_source_files.map(x=>x.path),...prior.files.map(x=>x.path),...baselineBuild.files.map(x=>x.source_path).filter(x=>typeof x==='string'),...closure])].filter(authored).sort();
  assert.equal(baselineSourcePaths.length,100,'Retained independently reviewed baseline source inventory');
  const addedSourcePaths=[...brainRoutes.map(name=>'templates/'+name),'templates/theme.js'].sort();
  assert.deepEqual(Object.keys(compositionPins).filter(name=>!baselineSourcePaths.includes(name)).sort(),addedSourcePaths,'Exactly eight additional authored source pins');
  assert.equal(Object.keys(compositionPins).filter(name=>baselineSourcePaths.includes(name)).length,5,'Exactly five explicitly reviewed baseline replacements');
  const sourcePaths=[...new Set([...baselineSourcePaths,...build.files.map(x=>x.source_path),'templates/theme.js'])].filter(authored).sort();
  assert.deepEqual(sourcePaths,[...baselineSourcePaths,...addedSourcePaths].sort(),'Source inventory grows only by the eight explicit dependencies');
  assert.equal(sourcePaths.length,108,'Complete explicit composed source inventory');
  const reviewedBindings=sourcePaths.map(name=>{
    const pin=compositionPins[name],reference=pin?composition.frozen_reference_main:reviewed;
    const original=at(reference,name),composed=at(composition.source_commit,name);
    if(pin){assert.equal(hash(original),pin.sha256,name+' reviewed frozen-main digest');assert.equal(original.length,pin.bytes,name+' reviewed frozen-main length');}
    assert(composed.equals(original),name+' composition retains its exact explicitly reviewed source');
    for(const [label,subject] of [['candidate',release.accepted_candidate],['adopted main',release.accepted_main],['actual render source',release.render.source_commit]])
      assert(at(subject,name).equals(composed),name+' '+label+' retains the composed source');
    return {path:name,reviewed_source:reference,composition_source:composition.source_commit,sha256:hash(original),bytes:original.length,explicit_composition_delta:!!pin};
  });
  // These nine plain static copies have independently reviewed identical
  // template/site bytes. They supplement the 108 authored/source-route pins;
  // generated theme.js remains governed by its separate source/publication pins.
  const staticMirrorBindings=[...brainRoutes,'mm_brain.js','mm_brain_visuals.css'].sort().map(name=>{
    const pin=compositionPins['templates/'+name];
    for(const [label,subject] of [['composition source',composition.source_commit],['candidate',release.accepted_candidate],['adopted main',release.accepted_main],['actual render source',release.render.source_commit],['generated publication',release.render.publication_commit]]){
      const bytes=at(subject,'site/'+name);assert.equal(hash(bytes),pin.sha256,name+' '+label+' exact static mirror');assert.equal(bytes.length,pin.bytes);
    }
    return {path:'site/'+name,authored_source:'templates/'+name,sha256:pin.sha256,bytes:pin.bytes};
  });
  const inventoryQualification={broad_inventory_sha256:hash(broadBytes),prior_inventory_sha256:hash(priorBytes),template_closure:closure,template_dependency_qualification:closureReceipt.qualifications,absent_optional_templates:closureReceipt.absent_optional_templates,
    non_runtime_exception:[{path:'.github/ci/legacy-jobs.yml',reason:'Separately reviewed CI execution configuration, including the retained Intl timeout correction and integrated upstream Brain/Paywall coverage. Exact-head hosted CI/source acceptance governs this file; it is not a render input.'}],
    baseline_reviewed_source:reviewed,baseline_source_path_count:baselineSourcePaths.length,baseline_build_inventory_sha256:hash(baselineBuildBytes),
    reviewed_source:composition.source_commit,composition_reference_main:composition.frozen_reference_main,composition_evidence_commit:composition.evidence_commit,
    reviewed_bindings:reviewedBindings,explicit_composition_source_pins:compositionPins,explicit_static_mirror_bindings:staticMirrorBindings,
    build_inventory_sha256:hash(buildBytes),build_inventory_git_blob:gitBlob(buildBytes),build_inventory_path:buildReceiptPath,
    build_inventory_kind:build.artifact_inventory_kind,public_route_count:reviewedPublicRoutes.length,
    generated_output_paths:generatedOutputPaths,generated_output_binding:'Actual render publication, updater served inventory and real response bytes; not authored-source equality.',
    source_path_count:sourcePaths.length,claim:'Retained reviewed100 source inventory with five explicit frozen-main replacements, seven Brain authored dependencies, and the rendered theme template (108 source paths), plus nine exact static-copy mirror checks; not a claim of every transitive Python import or 51 direct builder emissions.'};

  const acq=workflow(release.acquisition.api_receipt,'backfill',release.acquisition.run_id);
  assert.equal(acq.event,'workflow_dispatch','Normal explicit backfill dispatch');
  const acquisitionJob=workflowJob(release.acquisition,acq,['full-history collection','commit']);
  assert(ancestor(release.accepted_main,acq.head_sha),'Acquisition uses adopted source');
  assert(ancestor(acq.head_sha,release.acquisition.publication_commit),'Acquisition publication lineage');
  const acquisitionLog=readLog(release.acquisition.job_log,'backfill job');
  assert(/python\s+-m\s+scripts[.]collect\s+--full-history\s+--only\s+(?:"intl_prices"|'intl_prices'|intl_prices)(?=\s|$)/m.test(acquisitionLog),'Normal exact full-history Intl command in actual successful collection step');
  const probe=readReceipt(release.acquisition.probe_receipt,'actual FX probe');
  assert.equal(probe.schema,'intl_fx_production_acceptance.v1');assert.equal(probe.verdict,'PASS');assert.equal(probe.pass_count,7);
  assert.deepEqual(probe.errors,[]);assert.deepEqual(probe.read_only_violations,[]);
  assert.equal(String(probe.supplied_backfill.run_id),String(acq.id));
  assert.equal(utc(probe.supplied_backfill.start_utc),utc(acq.run_started_at));assert.equal(utc(probe.supplied_backfill.end_utc),utc(acq.updated_at));
  const acceptanceStart=Date.now(),probedAt=utc(probe.probed_at_utc);
  assert(probedAt>=utc(acq.updated_at)&&probedAt<=acceptanceStart&&acceptanceStart-probedAt<=60*60*1000,'Actual fresh post-backfill probe within acceptance hour');
  assert.equal(probe.evaluated_on,new Date(acceptanceStart).toISOString().slice(0,10),'Probe evaluated on actual acceptance UTC day; rerun the read-only probe across a day boundary');
  const stores={JP:'USDJPY_X',KR:'USDKRW_X',TW:'USDTWD_X',IN:'USDINR_X',AU:'AUDUSD_X',GB:'GBPUSD_X',EZ:'EURUSD_X'};
  assert.equal(probe.currencies.length,7);assert.deepEqual(probe.currencies.map(x=>x.cc).sort(),Object.keys(stores).sort());
  const storeBindings=[];
  for(const row of probe.currencies){
    assert.equal(row.verdict,'PASS');assert.deepEqual(row.errors,[]);assert.equal(row.store_unchanged_during_probe,true);
    assert.equal(row.consumer_available,true);assert.equal(row.consumer_quality,'current');assert.equal(row.source_kind,'captured_store');
    assert(digest(row.evidence_sha256),'Currency evidence identity');
    const name='data/intl/'+stores[row.cc]+'.parquet',captured=at(release.acquisition.publication_commit,name),rendered=at(release.render.source_commit,name);
    assert.equal(hash(captured),row.canonical_store.sha256,name+' acquisition store');assert.equal(captured.length,row.canonical_store.bytes,name+' store size');
    assert(captured.equals(rendered),name+' actual render input equals acquired store');
    const actualCopy=fs.readFileSync(row.canonical_store.path);assert.equal(hash(actualCopy),hash(captured),name+' probed copy equals published canonical store');
    for(const side of ['start','end']){
      const endpoint=row.endpoints[side];assert(endpoint&&endpoint.within_supplied_backfill_window===true&&endpoint.capture_day_excluded===true,'Both qualified endpoints');
      const started=utc(endpoint.adapter_request_started_at_utc),returned=utc(endpoint.adapter_result_returned_at_utc);
      assert(utc(acq.run_started_at)<=started&&started<=returned&&returned<=utc(acq.updated_at),'Actual run clock bound');
      assert(endpoint.provider_date<new Date(started).toISOString().slice(0,10),'Request UTC day excluded');assert(digest(endpoint.receipt_sha256),'Endpoint receipt identity');
    }
    assert(row.reference_gap_days>=0&&row.reference_gap_days<=7,'Calendar reference lag');
    storeBindings.push({cc:row.cc,path:name,sha256:hash(captured),bytes:captured.length,evidence_sha256:row.evidence_sha256});
  }
  const probeSourceNames=['lib/intl_currency_observation.py','engine/intl_inputs.py','lib/store.py','lib/config.py','collectors/intl_prices.py'].sort();
  assert.deepEqual(Object.keys(probe.source_files).sort(),probeSourceNames,'Exact complete five-file FX probe source inventory');
  for(const [name,row] of Object.entries(probe.source_files)){
    const candidate=at(release.accepted_candidate,name),adopted=at(release.accepted_main,name),acquired=at(acq.head_sha,name),rendered=at(release.render.source_commit,name);
    assert.equal(row.sha256,hash(candidate),name+' actual probe source');assert(candidate.equals(adopted)&&candidate.equals(acquired)&&candidate.equals(rendered),name+' probe/acquisition/render source correspondence');
  }

  const render=workflow(release.render.api_receipt,'render',release.render.run_id);
  const renderJob=workflowJob(release.render,render,['re-render pages from committed data','commit rendered site']);
  assert(['workflow_dispatch','push'].includes(render.event),'Normal render event');
  assert(ancestor(render.head_sha,release.render.source_commit),'Actual render checkout descends from queued workflow head');
  assert(ancestor(release.acquisition.publication_commit,release.render.source_commit),'Render covers acquired publication');
  assert(sha(release.render.watermark_commit),'Actual covering render watermark commit');
  assert(ancestor(release.render.source_commit,release.render.watermark_commit)&&ancestor(release.render.watermark_commit,release.render.publication_commit),'Render publication ancestry');
  const message=git('show','-s','--format=%B',release.render.watermark_commit);
  const watermark=message.match(/^render: site re-render \d{4}-\d{2}-\d{2} \(scope=([a-z+]+), from=([a-f0-9]{7,40})\)$/m);
  assert(watermark&&(watermark[1]==='all'||watermark[1].split('+').includes('intl')),'Completed Intl covering watermark');
  assert.equal(git('rev-parse','--verify',watermark[2]+'^{commit}'),release.render.source_commit,'Actual rendered source resolved from canonical watermark');
  const renderLog=readLog(release.render.job_log,'render job');
  const renderLines=cleanLog(renderLog),label='international macro dashboard (build_intl)';
  const starts=renderLines.map((line,index)=>({line,index})).filter(x=>x.line==='##[group]'+label||x.line==='::group::'+label);assert.equal(starts.length,1,'Exactly one actual executed Intl builder group');
  let depth=1,end=-1;
  for(let i=starts[0].index+1;i<renderLines.length;i++){
    if(/^(?:##\[group\]|::group::)/.test(renderLines[i]))depth++;
    if(/^(?:##\[endgroup\]|::endgroup::)$/.test(renderLines[i]))depth--;
    if(depth===0){end=i;break;}
  }
  assert(end>starts[0].index,'Actual Intl group completed');
  const intlOutput=renderLines.slice(starts[0].index+1,end).join('\n');
  assert(/wrote intl[.]html [+] intl_stocks[.]html \(\d+ economies, \d+ standouts\)/.test(intlOutput),'Actual primary Intl page write success in executed group');
  assert(!renderLines.some(x=>x.includes(label+' failed (rc=')),'No Intl nonzero-return annotation anywhere in actual job log');
  const publicationProof={acquisition:publishedByNormalPush(acquisitionLog,release.acquisition.publication_commit,'acquisition'),render:publishedByNormalPush(renderLog,release.render.publication_commit,'render')};

  // The normal updater materializes one public runtime config after rsync.
  // Its served bytes must be host bound separately from generated publication.
  const updater=readReceipt({path:release.updater.receipt_path,sha256:release.updater.receipt_sha256},'actual Macro updater host');
  assert.equal(updater.schema,'intl.macro_updater_host_receipt.v1');assert.equal(updater.pass,true);assert.equal(updater.complete,true);
  assert.deepEqual(updater.errors,[]);assert.equal(updater.identity_stable,true);assert.deepEqual(updater.identity_start,updater.identity_end);
  assert.equal(updater.checkout_commit,release.updater.checkout_commit);assert.equal(updater.render_publication_commit,release.render.publication_commit);
  assert.equal(updater.identity_start.git.checkout_commit,updater.checkout_commit);assert.equal(updater.identity_start.git.origin,'https://github.com/mastermindx-market-intelligence/macro.git');
  assert.equal(updater.render_publication_is_ancestor,true);assert(ancestor(release.render.publication_commit,updater.checkout_commit));
  assert(utc(updater.started_at)>=utc(render.updated_at)&&utc(updater.finished_at)>=utc(updater.started_at)&&utc(updater.finished_at)<=Date.now()&&Date.now()-utc(updater.finished_at)<=60*60*1000,'Fresh post-render normal updater host receipt');
  const publicRoutes=reviewedPublicRoutes;
  assert.equal(publicRoutes.length,51);assert.equal(new Set(publicRoutes).size,51,'Complete distinct reviewed public-route inventory');
  const ordinaryNames=publicRoutes.filter(name=>name!=='logo_config.js').sort();
  assert.equal(ordinaryNames.length,50);assert.equal(new Set(ordinaryNames).size,50);
  assert.deepEqual(Object.keys(release.artifact.files).sort(),ordinaryNames,'Complete ordinary artifact map with only the explicit runtime overlay separated');
  for(const field of ['generated_files','served_files']){
    assert.deepEqual(Object.keys(updater[field]).sort(),ordinaryNames,'Complete updater '+field);
    for(const name of ordinaryNames)assert.deepEqual(updater[field][name],release.artifact.files[name],name+' '+field+' equals actual generated publication pin');
  }
  assert.deepEqual(Object.keys(updater.runtime_overlays),['logo_config.js'],'Exactly the known normal runtime overlay');
  const logo=updater.runtime_overlays['logo_config.js'];
  const placeholder={sha256:'b37d33d3194c191b1bb64db3f5c33d17c7dc06a74892e4aa8ea4d50320aae215',bytes:202};
  assert.equal(logo.placeholder_matches_reviewed_empty_token_fallback,true);
  assert.deepEqual(logo.reviewed_placeholder,placeholder);assert.equal(logo.served_assignment_syntax_valid,true);
  for(const field of ['generated_placeholder','render_publication_placeholder','checkout_placeholder']){
    assert.equal(logo[field].bytes,placeholder.bytes);assert.equal(logo[field].sha256,placeholder.sha256);
  }
  for(const subject of [reviewed,release.accepted_candidate,release.render.publication_commit,updater.checkout_commit]){
    for(const name of ['site/logo_config.js','templates/logo_config.js']){
      const bytes=at(subject,name);assert.equal(bytes.length,placeholder.bytes,'Exact reviewed empty-token fallback size');
      assert.equal(hash(bytes),placeholder.sha256,'Exact reviewed empty-token fallback bytes');
    }
  }
  assert(digest(logo.served_file.sha256)&&Number.isSafeInteger(logo.served_file.bytes)&&logo.served_file.bytes>0&&logo.served_file.bytes<=4096,'Bounded actual served logo configuration');
  const updaterSource=at(updater.checkout_commit,'app/deploy/update.sh'),reviewedUpdater=at(reviewed,'app/deploy/update.sh');
  assert.equal(updater.updater.installed_equals_checkout_equals_git_blob,true);assert.equal(updater.updater.source_commit,updater.checkout_commit);
  for(const field of ['installed','checkout','source']){assert.equal(updater.updater[field].sha256,hash(updaterSource));assert.equal(updater.updater[field].bytes,updaterSource.length);}
  const blockStart='# Runtime-only company-logo configuration. The committed file is deliberately',blockEnd='\n# Do not exit just because Git is current.';
  function overlayBlock(bytes){const text=bytes.toString(),start=text.indexOf(blockStart),end=text.indexOf(blockEnd,start);assert(start>=0&&end>start&&text.indexOf(blockStart,start+1)===-1,'Unique known updater overlay block');return Buffer.from(text.slice(start,end));}
  const actualBlock=overlayBlock(updaterSource),reviewedBlock=overlayBlock(reviewedUpdater);assert(actualBlock.equals(reviewedBlock),'Normal updater runtime-overlay contract unchanged from reviewed source');
  assert.equal(actualBlock.length,1002);assert.equal(logo.contract.id,'macro.logo_config.publishable_token.v1');assert.equal(logo.contract.source_path,'app/deploy/update.sh');
  assert.equal(logo.contract.source_commit,updater.checkout_commit);assert.equal(logo.contract.source_git_blob,git('rev-parse',updater.checkout_commit+':app/deploy/update.sh'));
  assert.equal(logo.contract.exact_block_sha256,hash(actualBlock));assert.equal(logo.contract.exact_block_bytes,actualBlock.length);assert.equal(logo.contract.exact_reviewed_block_match,true);
  assert.equal(logo.contract.served_bytes_are_generated_publication,false);assert.equal(logo.contract.environment_read,false);assert.equal(logo.contract.token_value_serialized,false);
  const completedUpdates=updater.updater_log.completion_records.filter(row=>updater.checkout_commit.startsWith(row.new_abbrev)&&utc(row.time)<=utc(updater.finished_at)&&git('rev-parse','--verify',row.new_abbrev+'^{commit}')===updater.checkout_commit);
  assert(completedUpdates.length>0,'Actual normal updater completion for the observed checkout');
  const childRuntimeOverlays={'logo_config.js':{sha256:logo.served_file.sha256,bytes:logo.served_file.bytes,source:'separately host-bound normal updater runtime overlay',contract:logo.contract,updater_receipt_sha256:release.updater.receipt_sha256}};

  const host=readReceipt(release.parent.host_receipt,'actual beta host');
  assert.equal(host.schema,'intl.beta_parent_host_receipt.v1');assert.equal(host.pass,true);assert.equal(host.active_runtime,true);assert.equal(host.accepted_sha,release.parent.source_commit);
  for(const key of ['enabled','protocol','buildId','bridgeVersion','documentVersion','registrySha256'])assert.equal(host.status[key],release.parent.status[key],'Host public status '+key);
  assert(host.identity_start&&host.identity_end,'Host collection generation bracket');
  assert.equal(host.complete,true);assert.equal(host.identity_stable,true);assert.deepEqual(host.errors,[]);
  const identityKeys=['accepted_pointer','accepted_record','receipts_provenance','deployment_id','build_id','compiled_manifest','app_directory','next_directory','static_directory'];
  for(const side of ['identity_start','identity_end']){
    const identity=host[side];assert.equal(identity.complete,true);assert.equal(identity.accepted_sha,release.parent.source_commit);
    assert(digest(identity.accepted_record_id));assert.equal(identity.accepted_record.record_id,identity.accepted_record_id);
    assert.equal(identity.compiled_deployment_id,release.parent.source_commit);assert.equal(identity.compiled_shared_shell_build,release.parent.source_commit);
    assert.equal(identity.deployment_id.value,release.parent.source_commit);assert.equal(identity.active_runtime.verified_active,true);
    assert.deepEqual(identity.parent_status.tuple,release.parent.status);
    for(const key of identityKeys)assert(identity[key]&&typeof identity[key]==='object'&&Object.keys(identity[key]).length>0,'Complete host identity '+key);
  }
  for(const key of identityKeys)assert.deepEqual(host.identity_start[key],host.identity_end[key],'Stable host identity '+key);
  assert.deepEqual(host.identity_start.active_runtime.properties,host.identity_end.active_runtime.properties,'Same live process during host collection');
  assert(utc(host.started_at)<=utc(host.finished_at)&&utc(host.finished_at)<=Date.now(),'Host receipt clock order');
  assert(host.static_files&&Object.keys(host.static_files).length>0,'Complete live parent static map');
  for(const [name,row] of Object.entries(host.static_files))assert(name.startsWith('/_next/static/')&&!name.split('/').includes('..')&&digest(row.sha256)&&Number.isSafeInteger(row.bytes)&&row.bytes>0,'Valid live parent static binding');
  return {schema:'intl.production_release_custody.v1',pass:true,receipts,source_paths:sourcePaths,inventory_qualification:inventoryQualification,
    acquisition:{run_id:acq.id,job_id:acquisitionJob.id,source_commit:acq.head_sha,published_commit:release.acquisition.publication_commit,probe_receipt_sha256:release.acquisition.probe_receipt.sha256,stores:storeBindings,currency_observations:probe.currencies,publication:publicationProof.acquisition},
    render:{run_id:render.id,job_id:renderJob.id,workflow_head:render.head_sha,actual_source:release.render.source_commit,watermark_commit:release.render.watermark_commit,publication_commit:release.render.publication_commit,watermark_message:message,builder_group_sha256:hash(Buffer.from(intlOutput)),publication:publicationProof.render},
    child_runtime_overlays:childRuntimeOverlays,updater:{receipt_sha256:release.updater.receipt_sha256,checkout_commit:updater.checkout_commit,normal_completions:completedUpdates,source:updater.updater,qualification:updater.qualification},
    parent_static_files:host.static_files,parent_host_receipt:{path:release.parent.host_receipt.path,sha256:release.parent.host_receipt.sha256,accepted_sha:host.accepted_sha,identity_start:host.identity_start,identity_end:host.identity_end},
    limitation:'Caller must retain raw API/log/probe/host receipts and independently reconcile actual GitHub/host provenance. A post-journey host generation check and standalone country/access/assistant proof remain separate required components.'};
};
