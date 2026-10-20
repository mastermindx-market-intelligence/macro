/* Browser-local research preferences over the existing authorized News snapshot.
 * Pure projection only: no requests, timers, source ownership or story-body cache.
 */
(function(root,factory){
  "use strict";
  var api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  if(root.document)root.NewsDeskResearch=api;
})(typeof window!=="undefined"?window:globalThis,function(){
  "use strict";
  var LIMITS={investigations:12,reports:100,watches:24,records:1500,updates:100};
  var RELATIONS=["question","topic","accounts","connection"];
  function label(value,max){return typeof value==="string"?value.replace(/[\u0000-\u001f\u007f]/g," ").trim().slice(0,max):"";}
  function id(value){return typeof value==="string"&&value.trim()&&value.length<=300?value:"";}
  function ids(values,max){return Array.from(new Set((Array.isArray(values)?values:[]).map(id).filter(Boolean))).slice(0,max);}
  function key(value){return typeof value==="string"&&/^[vi]:[a-zA-Z0-9_-]{1,80}$/.test(value)?value:"";}
  function marker(value){
    // Two independent 32-bit change checks; never an identity or access decision.
    var input=String(value),a=2166136261,b=2654435769;
    for(var i=0;i<input.length;i++){var c=input.charCodeAt(i);a=Math.imul(a^c,16777619);b=Math.imul(b^c,2246822519);}
    return "m1-"+(a>>>0).toString(16).padStart(8,"0")+(b>>>0).toString(16).padStart(8,"0");
  }
  function validMarker(value){return typeof value==="string"&&/^m1-[0-9a-f]{16}$/.test(value);}
  function cleanFilters(raw,defaults){
    raw=raw&&typeof raw==="object"&&!Array.isArray(raw)?raw:{};
    var f=Object.assign({},defaults),options={
      view:["latest","important","following","world"],category:["all","markets","economy","central_banks","companies","geopolitics","energy","technology"],
      time:["24","72","168","all"],region:["all","americas","europe","asia","middle_east","africa"],kind:["all","official","reporting","social"]
    };
    Object.keys(options).forEach(function(k){if(options[k].includes(raw[k]))f[k]=raw[k];});
    f.query=label(raw.query,300);f.source=label(raw.source,100);
    ["unread","social","saved"].forEach(function(k){f[k]=raw[k]===true;});
    return f;
  }
  function cleanViews(raw,defaults){
    var used=new Set();
    return (Array.isArray(raw)?raw:[]).slice(0,12).filter(function(v){return v&&typeof v==="object"&&label(v.name,40);}).map(function(v,index){
      var identity=/^[a-zA-Z0-9_-]{1,80}$/.test(v.id||"")?v.id:"view-"+index;
      if(used.has(identity)){var suffix=0;do{identity="legacy-view-"+index+"-"+suffix++;}while(used.has(identity));}used.add(identity);
      return{id:identity,name:label(v.name,40),filters:cleanFilters(v.filters,defaults)};
    });
  }
  function cleanState(raw){
    raw=raw&&typeof raw==="object"&&!Array.isArray(raw)?raw:{};
    var seen=new Set(),state={version:1,investigations:[],watching:[],enabled:raw.enabled===true,quiet:raw.quiet!==false,sequence:0,records:[],updates:[]};
    (Array.isArray(raw.investigations)?raw.investigations:[]).slice(0,LIMITS.investigations).forEach(function(item){
      if(!item||typeof item!=="object"||!/^[a-zA-Z0-9_-]{1,80}$/.test(item.id||"")||seen.has(item.id)||!label(item.name,60))return;
      seen.add(item.id);state.investigations.push({id:item.id,name:label(item.name,60),storyIds:ids(item.storyIds,LIMITS.reports),relation:RELATIONS.includes(item.relation)?item.relation:"question"});
    });
    state.watching=Array.from(new Set((Array.isArray(raw.watching)?raw.watching:[]).map(key).filter(Boolean))).slice(0,LIMITS.watches);
    var watched=new Set(state.watching),recordIds=new Set();
    (Array.isArray(raw.records)?raw.records:[]).slice(0,LIMITS.records).forEach(function(r){
      if(!r||!id(r.id)||recordIds.has(r.id)||!(validMarker(r.mark)||r.mark===""&&r.available===false))return;
      recordIds.add(r.id);state.records.push({id:r.id,mark:r.mark,available:r.available===true,targets:ids(r.targets,LIMITS.watches).filter(function(k){return watched.has(k);})});
    });
    state.sequence=Number.isSafeInteger(raw.sequence)&&raw.sequence>=0?raw.sequence:0;
    var updateIds=new Set();
    (Array.isArray(raw.updates)?raw.updates:[]).slice(0,LIMITS.updates).forEach(function(u){
      if(!u||!id(u.id)||!Number.isSafeInteger(u.n)||u.n<1||updateIds.has(u.n)||!["arrival","amendment","removal","return"].includes(u.kind)||!Number.isFinite(u.at)||u.at<0||u.at>8640000000000000)return;
      var targets=ids(u.targets,LIMITS.watches).filter(function(k){return watched.has(k);});if(!targets.length)return;
      updateIds.add(u.n);state.sequence=Math.max(state.sequence,u.n);
      state.updates.push({n:u.n,id:u.id,kind:u.kind,targets:targets,at:u.at,read:u.read===true});
    });
    return state;
  }
  function prune(state,allowed){
    var keep=new Set(allowed),watching=state.watching.filter(function(k){return keep.has(k);}),enabled=new Set(watching);
    return Object.assign({},state,{watching:watching,
      records:state.records.map(function(r){return Object.assign({},r,{targets:r.targets.filter(function(k){return enabled.has(k);})});}),
      updates:state.updates.map(function(u){return Object.assign({},u,{targets:u.targets.filter(function(k){return enabled.has(k);})});}).filter(function(u){return u.targets.length;})});
  }
  function advance(state,rows,memberships,options){
    options=options||{};
    if(!state.enabled||!state.watching.length)return{state:Object.assign({},state,{records:[]}),added:0};
    var baseline=options.baseline===true,watched=new Set(state.watching),before=new Map(state.records.map(function(r){return[r.id,r];}));
    var present=new Set(),membership=new Map(),next=[],missing=[],events=[],sequence=state.sequence;
    memberships.forEach(function(m){if(!watched.has(m.key))return;ids(m.ids,1000).forEach(function(identity){var list=membership.get(identity)||[];if(!list.includes(m.key))list.push(m.key);membership.set(identity,list);});});
    function targets(identity,old){return Array.from(new Set((baseline?[]:old&&old.targets||[]).concat(membership.get(identity)||[]))).filter(function(k){return watched.has(k);});}
    function event(identity,kind,related){
      if(baseline||!related.length)return;
      sequence++;events.push({n:sequence,id:identity,kind:kind,targets:related,at:options.now,read:false});
    }
    rows.slice(0,1000).forEach(function(row){
      if(!id(row.id)||!validMarker(row.mark)||present.has(row.id))return;
      present.add(row.id);var old=before.get(row.id),related=targets(row.id,old);
      if(!old)event(row.id,"arrival",related);
      else if(!old.available)event(row.id,"return",related);
      else if(old.mark!==row.mark||options.changedIds&&options.changedIds.has(row.id))event(row.id,"amendment",related);
      next.push({id:row.id,mark:row.mark,available:true,targets:related});
    });
    if(!baseline)state.records.forEach(function(old){
      if(present.has(old.id))return;var related=targets(old.id,old);if(!related.length)return;
      if(old.available)event(old.id,"removal",related);
      missing.push({id:old.id,mark:old.mark,available:false,targets:related});
    });
    var missingIds=new Set(missing.map(function(r){return r.id;}));
    membership.forEach(function(related,identity){
      if(!present.has(identity)&&!missingIds.has(identity)){missingIds.add(identity);missing.push({id:identity,mark:"",available:false,targets:related});}
    });
    // Present rows take priority; older missing references are bounded markers.
    next=next.concat(missing).slice(0,LIMITS.records);
    return{state:Object.assign({},state,{records:next,updates:events.reverse().concat(state.updates).slice(0,LIMITS.updates),sequence:sequence}),added:events.length};
  }
  function historyDescriptor(raw){
    var unavailable={state:"unavailable"};
    if(!raw||raw.state!=="available"||raw.schema!=="intelligence.retained_history/v1"||!/^([0-9a-f]{64})$/.test(raw.revision||""))return unavailable;
    var b=raw.bounds;if(!b||!Number.isFinite(b.retention_hours)||b.retention_hours<=0||b.retention_hours>72||!Number.isSafeInteger(b.max_stories)||b.max_stories<1||b.max_stories>1500||b.retention_basis!=="owner_updated_at")return unavailable;
    if(![raw.retained_count,raw.displayable_count,raw.excluded_count].every(function(n){return Number.isSafeInteger(n)&&n>=0&&n<=b.max_stories;})||raw.displayable_count+raw.excluded_count!==raw.retained_count)return unavailable;
    return{state:"available",revision:raw.revision,bounds:{retention_hours:b.retention_hours,max_stories:b.max_stories,retention_basis:b.retention_basis},retained_count:raw.retained_count,displayable_count:raw.displayable_count,excluded_count:raw.excluded_count};
  }
  function historyQuery(raw){
    raw=raw||{};var query={},caps={q:256,source:160,feed_id:160,category:64,language:32},valid=true;
    Object.keys(caps).forEach(function(k){var value=raw[k]===undefined?"":raw[k];if(typeof value!=="string"||value.length>caps[k]){valid=false;return;}query[k]=value.trim();if(k==="category"||k==="language")query[k]=query[k].toLowerCase();});
    ["from_at","to_at"].forEach(function(k){var value=raw[k];if(value===undefined||value===null||value===""){query[k]=null;return;}if(typeof value!=="string"||value.length>80||!/(?:Z|[+-]\d\d:\d\d)$/i.test(value)||!Number.isFinite(Date.parse(value))){valid=false;return;}query[k]=new Date(value).toISOString();});
    query.limit=raw.limit===undefined?50:raw.limit;if(!Number.isSafeInteger(query.limit)||query.limit<1||query.limit>100)valid=false;
    if(query.from_at&&query.to_at&&Date.parse(query.from_at)>=Date.parse(query.to_at))valid=false;
    return valid?query:null;
  }
  function validHistoryPage(page,descriptor,query){
    if(!page||!descriptor||descriptor.state!=="available"||!query||page.schema!=="intelligence.history_page/v1"||page.revision!==descriptor.revision||page.collection!=="retained_current_packets"||page.order!=="recorded_acceptance_desc_then_id"||typeof page.as_of!=="string"||page.as_of.length>80||!/(?:Z|[+-]\d\d:\d\d)$/i.test(page.as_of)||!Number.isFinite(Date.parse(page.as_of)))return false;
    var b=page.bounds;if(!b||["retention_hours","max_stories","retention_basis"].some(function(k){return b[k]!==descriptor.bounds[k];}))return false;
    if(["retained_count","displayable_count","excluded_count"].some(function(k){return page[k]!==descriptor[k];}))return false;
    if(!Number.isSafeInteger(page.matched_count)||page.matched_count<0||page.matched_count>descriptor.displayable_count||!Array.isArray(page.stories)||page.stories.length>query.limit||page.returned_count!==page.stories.length||page.returned_count>page.matched_count)return false;
    if(!(page.next_cursor===null||typeof page.next_cursor==="string"&&page.next_cursor.length<=1024&&/^[A-Za-z0-9_-]+$/.test(page.next_cursor))||page.next_cursor!==null&&!page.stories.length)return false;
    var seen=new Set();if(!page.stories.every(function(r){return r&&typeof r==="object"&&!Array.isArray(r)&&id(r.id)&&!seen.has(r.id)&&(seen.add(r.id),true);}))return false;
    if(!page.query||typeof page.query!=="object"||Array.isArray(page.query)||["q","source","feed_id","category","language","from_at","to_at","limit"].some(function(k){return !Object.prototype.hasOwnProperty.call(page.query,k);}))return false;
    var echo=historyQuery(page.query);if(!echo)return false;
    return ["q","source","feed_id","category","language","limit"].every(function(k){return echo[k]===query[k];})&&["from_at","to_at"].every(function(k){return echo[k]===null?query[k]===null:query[k]!==null&&Date.parse(echo[k])===Date.parse(query[k]);});
  }
  return{limits:LIMITS,relations:RELATIONS,label:label,id:id,marker:marker,cleanFilters:cleanFilters,cleanViews:cleanViews,cleanState:cleanState,prune:prune,advance:advance,historyDescriptor:historyDescriptor,historyQuery:historyQuery,validHistoryPage:validHistoryPage};
});
