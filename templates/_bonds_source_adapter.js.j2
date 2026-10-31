/* Display adapter for the current macro-context owner. No rule, case or alert admission. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.MMXSourceAdapter=api;})(typeof window==='object'?window:globalThis,function(){
  'use strict';
  const FILES={snapshot:'data/macro_snapshots/latest.json',world_state:'data/neuralweb/world_state.json',regime:'data/regime/latest.json',transitions:'data/macro_snapshots/transitions.jsonl'};
  const frozenCapabilities=()=>({evaluate:false,forecast:false,retain:false,monitor:false});
  const obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
  const clone=x=>JSON.parse(JSON.stringify(x));
  const get=(o,p)=>p.split('.').reduce((a,k)=>obj(a)&&Object.hasOwn(a,k)?a[k]:undefined,o);
  const label=x=>typeof x==='string'&&x.trim().length>0&&x.length<=4000;
  const finite=x=>typeof x==='number'&&Number.isFinite(x);
  const digest=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
  function iso(x){if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(x))return null;const n=Date.parse(x+'T00:00:00Z');return Number.isFinite(n)&&new Date(n).toISOString().slice(0,10)===x?n:null;}
  const restricted=o=>obj(o)&&o.display_only===true&&o.claim_scope==='projection_only'&&o.probability_policy==='withheld';
  const fields=[];
  function add(path,title,titleZh,type,unit,sourcePath,component='rates_credit',fallback=null){
    fields.push({path,title,titleZh,type,unit,sourcePath,component,fallback,sourceFile:component==='snapshot'?FILES.snapshot:FILES.world_state});
  }
  [
    ['health','Bond health','债券健康','bond_health_label','health_label'],
    ['cycle','Cycle label','周期标签','bond_cycle_phase','cycle_phase'],
    ['duration_lean','Duration context','久期背景','bond_duration_bucket','bond_compass.duration.bucket'],
    ['curve_trade','Curve context','曲线背景','bond_curve_lean','bond_compass.curve_trade.lean']
  ].forEach(([key,en,zh,source,fallback])=>add('current_read.'+key,en,zh,'label','', 'labels.bonds.'+source,'snapshot','rates_credit.'+fallback));
  add('current_read.yield_curve_regime','Curve regime','曲线状态','label','','labels.transmission.yield_curve_regime','snapshot');
  add('current_read.recession_risk','Recession label','衰退标签','label','','labels.transmission.recession_risk','snapshot');
  [
    ['fed_path.policy_rate','Policy rate','政策利率','%','fed_path.policy_rate'],
    ['fed_path.implied_bp_12m','12-month rate-path change','12个月利率路径变化','bp','fed_path.implied_bp_12m'],
    ['real_10y','10Y real yield','10年实际收益率','%','drivers_for.forex.real_10y'],
    ['term_premium','Term-premium estimate','期限溢价估计','%','drivers_for.forex.term_premium'],
    ['curve_slope_10y3m','10Y–3M curve slope','10年–3个月曲线斜率','pp','bond_compass.curve_trade.slope_10y3m']
  ].forEach(([key,en,zh,unit,path])=>add('mechanism_evidence.'+key,en,zh,'number',unit,'rates_credit.'+path));
  [
    ['note_en','Equity channel note','股票传导说明','label',''],
    ['hy_oas','Broad HY OAS','广泛高收益债利差','number','%'],
    ['credit_canary','Owner credit flag','上游信用标记','boolean',''],
    ['stock_bond_corr','Stock–bond correlation','股债相关性','number','']
  ].forEach(([key,en,zh,type,unit])=>add('transmission.equities.'+key,en,zh,type,unit,'rates_credit.drivers_for.equities.'+key));
  [
    ['note_en','FX channel note','外汇传导说明','label',''],
    ['real_10y','FX-linked real yield','外汇关联实际收益率','number','%'],
    ['term_premium','FX-linked term premium','外汇关联期限溢价','number','%']
  ].forEach(([key,en,zh,type,unit])=>add('transmission.forex.'+key,en,zh,type,unit,'rates_credit.drivers_for.forex.'+key));
  [
    ['asof','Cross-asset component date','跨资产组件日期','asof'],
    ['regime','Cross-asset context','跨资产背景','regime'],
    ['funding_state','Funding proxy','融资代理指标','funding_state'],
    ['confirm_verdict','Cross-asset label','跨资产标签','confirm.verdict']
  ].forEach(([key,en,zh,path])=>add('cross_asset.'+key,en,zh,'label','','cross_asset_flows.'+path,'cross_asset'));
  const clockPaths={snapshot:[FILES.snapshot,'asof'],snapshot_oldest_component:[FILES.snapshot,'oldest_component_asof'],rates_credit:[FILES.world_state,'rates_credit.as_of'],cross_asset:[FILES.world_state,'cross_asset_flows.asof'],regime:[FILES.regime,'asof'],fx_dollar:[FILES.world_state,'fx_dollar.asof']};
  function validateClock(c,today){
    if(!obj(c))return false;
    const parsed=iso(c.reported_value), age=parsed===null?null:(iso(today)-parsed)/86400000;
    const expected=c.reported_value===null?'missing':parsed===null?'malformed':age<0?'future':'known';
    return c.date_status===expected&&c.asof===(parsed===null?null:c.reported_value)&&c.age_days===age;
  }
  function fail(errors){return {ok:false,state:'unavailable',errors:[...new Set(errors)],fields:[],capabilities:frozenCapabilities(),sourceKind:null,digestVerification:'not_performed'};}
  function parse(raw){
    let input=raw;
    if(typeof raw==='string'){if(raw.length>1500000)return fail(['publication_too_large']);try{input=JSON.parse(raw);}catch{return fail(['invalid_json']);}}
    if(!obj(input)||input.schema!=='macro_context.decision_publication.v1'||!restricted(input))return fail(['unsupported_publication_contract']);
    const d=input.decision_workspaces,p=input.publication,b=d?.bonds;
    if(!restricted(d)||d.schema!=='macro_context.decision_workspaces.v1'||!restricted(b)||!restricted(d.forex))return fail(['unsupported_projection_contract']);
    if(!['ready','partial','unavailable'].includes(b.status)||!['ready','partial','unavailable'].includes(d.forex.status))return fail(['unsupported_domain_status']);
    if(!obj(b.current_read)||!obj(b.mechanism_evidence)||!obj(b.mechanism_evidence.fed_path)||!obj(b.transmission)||!obj(b.cross_asset)||!Array.isArray(b.changes)||!Array.isArray(b.data_gaps))return fail(['malformed_bonds_projection']);
    if(!obj(p)||p.producer!=='scripts/build_macro_context.py'||iso(p.validation_date)===null||!digest(p.content_sha256)||p.identity_scope!=='normalized_loaded_inputs_and_projection_excluding_build_time'||p.identity_use!=='content_comparison_only_not_authenticated_or_retained_evidence'||p.hash_algorithm!=='sha256_python_sorted_compact_utf8_json')return fail(['unsupported_publication_identity']);
    if(typeof p.built_at!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(p.built_at)||!Number.isFinite(Date.parse(p.built_at)))return fail(['malformed_build_time']);
    if(!obj(input.hub)||Object.keys(input.hub).length!==5||!['asof','macro_context_id','headline_en','headline_zh'].every(k=>typeof input.hub[k]==='string')||!Number.isInteger(input.hub.n_transitions_14d)||input.hub.n_transitions_14d<0)return fail(['malformed_hub']);
    if(!obj(p.component_clocks)||!obj(p.field_lineage?.bonds)||p.field_lineage_scope!=='bonds_scalar_display_fields'||!obj(p.input_fingerprints)||!obj(p.related_vintages)||!Array.isArray(p.invalid_values))return fail(['missing_provenance']);
    if(p.clock_policy!=='component_dates_do_not_establish_observation_time_availability_or_vendor_freshness'||p.changes_scope!=='selected_label_transitions_not_event_ledger_or_complete_history')return fail(['unsupported_evidence_scope']);
    const errors=[],warnings=[];
    for(const [key,file] of Object.entries(FILES)){
      const f=p.input_fingerprints[key];
      if(!obj(f)||f.path!==file||!digest(f.sha256)||!['loaded','absent_or_unreadable','empty_or_unavailable'].includes(f.loaded_state)||!Array.isArray(f.invalid_values)||f.representation!==(key==='transitions'?'last_60_parsed_rows_in_loader_order':'parsed_json'))errors.push('malformed_input_fingerprint:'+key);
    }
    for(const [key,[file,path]] of Object.entries(clockPaths)){
      const c=p.component_clocks[key];
      if(!validateClock(c,p.validation_date)||c.kind!=='component_date'||c.source_file!==file||c.source_path!==path)errors.push('malformed_component_clock:'+key);
      else if(c.date_status!=='known')warnings.push({kind:'component_date',key,status:c.date_status});
    }
    if(p.reported_cross_asset_stale!==null&&typeof p.reported_cross_asset_stale!=='boolean')errors.push('malformed_upstream_stale_flag');
    if(p.reported_cross_asset_stale===true)warnings.push({kind:'upstream_stale',key:'cross_asset'});
    for(const [key,v] of Object.entries(p.related_vintages)){
      if(!obj(v)||v.relationship!=='related_regime_input_not_matched_field_observation'||v.source_file!==FILES.regime||v.source_path!=='conditions.vintages.'+key||!obj(v.reported)||!validateClock(v.clock,p.validation_date)||v.reported.asof!==v.clock.reported_value)errors.push('malformed_related_vintage:'+key);
    }
    const rows=fields.map(def=>{
      const l=p.field_lineage.bonds[def.path],value=get(b,def.path);
      if(!obj(l)||l.source_kind!=='owner_projection'||l.observation_asof!==null||l.available_at!==null||l.underlying_source_family!==null||!Array.isArray(l.attempted_paths)){errors.push('malformed_field_lineage:'+def.path);return null;}
      const candidates=[{source_file:def.sourceFile,source_path:def.sourcePath}];
      if(def.fallback)candidates.push({source_file:FILES.world_state,source_path:def.fallback});
      if(l.attempted_paths.length!==candidates.length||!candidates.every((c,i)=>obj(l.attempted_paths[i])&&l.attempted_paths[i].source_file===c.source_file&&l.attempted_paths[i].source_path===c.source_path))errors.push('unexpected_field_candidates:'+def.path);
      if(l.selection==='missing'){
        if(l.source_file!==null||l.source_path!==null||l.component_clock!==null||l.reported_upstream!==null||value!=null)errors.push('inconsistent_missing_field:'+def.path);
      }else{
        const fallback=l.selection==='fallback';
        if(!['direct','primary','fallback'].includes(l.selection)||fallback&&!def.fallback||def.fallback&&!['primary','fallback'].includes(l.selection)||!def.fallback&&l.selection!=='direct')errors.push('unsupported_field_selection:'+def.path);
        if(l.source_file!==(fallback?FILES.world_state:def.sourceFile)||l.source_path!==(fallback?def.fallback:def.sourcePath)||l.component_clock!==(fallback?'rates_credit':def.component))errors.push('unexpected_selected_source:'+def.path);
        if(fallback&&l.reported_upstream!==null)errors.push('misattributed_fallback_receipt:'+def.path);
      }
      if(l.reported_upstream!==null){const upstream=def.path.startsWith('current_read.')?(def.sourcePath.startsWith('labels.bonds.')?'data/bonds/bond_health.json':'data/transmission/latest.json'):null;if(!obj(l.reported_upstream)||l.reported_upstream.path!==upstream||l.reported_upstream.kind!=='snapshot_reported_source_date'||!validateClock(l.reported_upstream,p.validation_date))errors.push('malformed_reported_upstream:'+def.path);}
      const valid=value==null?false:def.type==='number'?finite(value):def.type==='boolean'?typeof value==='boolean':label(value);
      if(value!=null&&!valid)warnings.push({kind:'invalid_field_type',key:def.path});
      return {...def,value:valid?value:null,rawValue:value===undefined?null:clone(value),available:valid,issue:value==null?'not_supplied':valid?null:'invalid_type',lineage:clone(l),componentDate:l.component_clock?p.component_clocks[l.component_clock]?.asof:null};
    });
    if(b.changes.length>8||!b.changes.every(x=>obj(x)&&['bonds','transmission'].includes(x.domain)&&label(x.field)&&[x.from,x.to].every(v=>v===null||typeof v==='string'||finite(v)||typeof v==='boolean')))errors.push('malformed_label_changes');
    if(!b.data_gaps.every(x=>obj(x)&&typeof x.key==='string'&&typeof x.status==='string'))errors.push('malformed_data_gaps');
    if(errors.length)return fail(errors);
    const dates=[...new Set(['snapshot','rates_credit','cross_asset','regime'].map(k=>p.component_clocks[k].asof).filter(Boolean))].sort();
    return {
      ok:true,state:'descriptive',sourceKind:'owner_projection',status:b.status,
      statusMeaning:{ready:'supplied_fields_complete',partial:'partial_projection',unavailable:'projection_unavailable'}[b.status],
      fields:rows,componentClocks:clone(p.component_clocks),relatedVintages:clone(p.related_vintages),
      warnings,reportedGaps:clone(b.data_gaps),invalidValues:clone(p.invalid_values),
      selectedChanges:clone(b.changes),changeScope:'selected_label_transitions',mixedComponentDates:dates.length>1,
      componentDateRange:dates.length?[dates[0],dates.at(-1)]:null,
      identity:{content:p.content_sha256,snapshot:input.hub.macro_context_id,buildTime:p.built_at,validationDate:p.validation_date,inputs:clone(p.input_fingerprints)},
      digestVerification:'publisher_declared_not_recomputed',capabilities:frozenCapabilities(),
      reportedCrossAssetStale:p.reported_cross_asset_stale,
      requirements:{matchedTreasuryObservation:'unavailable',completePeerCohort:'unavailable',qualifiedFundingReceipt:'unavailable',matchedBuyerFundingOrigin:'unavailable',calibratedContinuation:'unavailable'},
      confirmationCount:null,matchedEvent:null,continuation:null,probability:null
    };
  }
  return Object.freeze({parse,fields:clone(fields),validateClock,iso});
});
