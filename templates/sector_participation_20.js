/* Sector Central W1 — historical 20-session participation reader.
   Display-only: consumes one validated generation and never derives prices, moving
   averages, ranks, gates, sizes, or trade recommendations.  This asset is injected
   only by si_workspace.js on the first Money & Breadth activation. */
(function(){
'use strict';

var W1_STATE_SET={A:true,B:true,H:true,M:true,I:true,U:true};
function w1Stable(value){
  if(value===null||typeof value!=='object') return JSON.stringify(value);
  if(Array.isArray(value)) return '['+value.map(w1Stable).join(',')+']';
  return '{'+Object.keys(value).sort().map(function(key){
    return JSON.stringify(key)+':'+w1Stable(value[key]);
  }).join(',')+'}';
}
function w1ObservationMaterial(value){
  var material=JSON.parse(JSON.stringify(value));
  delete material.generation_id;
  delete material.observation_id;
  delete material.computed_at;
  delete material.published_at;
  if(material.source) delete material.source.acquired_at;
  return material;
}
function w1GenerationMaterial(value){
  var source=value&&value.source||{},reference=value&&value.reference||{};
  return {
    schema:'sector_participation_20.generation.v1',
    observation_id:value&&value.observation_id,
    roster_id:reference.roster_id,
    response_set_id:source.response_set_id,
    source_acquired_at:source.acquired_at,
    computed_at:value&&value.computed_at
  };
}
async function w1Sha256(text){
  if(!window.crypto||!window.crypto.subtle||!window.TextEncoder){
    throw new Error('generation verification unavailable');
  }
  var bytes=new window.TextEncoder().encode(text);
  var digest=await window.crypto.subtle.digest('SHA-256',bytes);
  return 'sha256:'+Array.from(new Uint8Array(digest)).map(function(byte){
    return byte.toString(16).padStart(2,'0');
  }).join('');
}
function w1Array(value,length){ return Array.isArray(value)&&value.length===length; }
function w1States(value,length){ return typeof value==='string'&&value.length===length; }
function w1Text(value){ return typeof value==='string'&&Boolean(value.trim()); }
function w1CodePointCompare(left,right){
  var a=Array.from(left),b=Array.from(right),limit=Math.min(a.length,b.length);
  for(var index=0;index<limit;index+=1){
    var ac=a[index].codePointAt(0),bc=b[index].codePointAt(0);
    if(ac!==bc) return ac<bc?-1:1;
  }
  return a.length-b.length;
}
function w1ShaId(value){ return typeof value==='string'&&/^sha256:[0-9a-f]{64}$/.test(value); }
function w1IsoDate(value){
  if(typeof value!=='string'||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value)) return false;
  var parsed=new Date(value+'T00:00:00Z');
  return Number.isFinite(parsed.getTime())&&parsed.toISOString().slice(0,10)===value;
}
function w1UtcClock(value){
  return typeof value==='string'&&/(?:Z|[+-]00:00)$/.test(value)&&Number.isFinite(Date.parse(value));
}
async function validatePackageCore(value,expectedGeneration,expectedObservation){
  if(!value||value.schema!=='sector_participation_20.v1') throw new Error('schema');
  if(!w1ShaId(value.observation_id)||
     (expectedObservation&&expectedObservation!==value.observation_id)){
    throw new Error('pointer observation');
  }
  if(await w1Sha256(w1Stable(w1ObservationMaterial(value)))!==value.observation_id){
    throw new Error('observation digest');
  }
  if(!expectedGeneration||expectedGeneration!==value.generation_id) throw new Error('pointer generation');
  if(await w1Sha256(w1Stable(w1GenerationMaterial(value)))!==value.generation_id){
    throw new Error('generation digest');
  }
  var method=value.method||{};
  var expectedLegend={
    A:'eligible_above_ma20',B:'eligible_equal_or_below_ma20',
    H:'insufficient_history',M:'required_expected_session_missing',
    I:'invalid_identity_basis_or_observation',U:'source_request_unavailable_or_refused'
  };
  if(method.name!=='sector_participation_20'||method.window_sessions!==20||
     method.comparison!=='close > MA20'||
     method.coverage_basis!=='complete expected NYSE sessions through selected session'||
     !method.display_floor||method.display_floor.min_eligible!==5||
     method.display_floor.min_coverage!==0.9||w1Stable(method.state_legend)!==w1Stable(expectedLegend)){
    throw new Error('method contract');
  }
  if(!w1UtcClock(value.computed_at)||!w1UtcClock(value.published_at)){
    throw new Error('generation clocks');
  }
  if(!Array.isArray(value.sessions)||!value.sessions.length) throw new Error('sessions');
  var seenSessions={},prior='';
  value.sessions.forEach(function(session){
    if(typeof session!=='string'||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(session)||
       seenSessions[session]||session<=prior){ throw new Error('session identity'); }
    seenSessions[session]=true; prior=session;
  });
  var n=value.sessions.length;
  if(!value.sectors||typeof value.sectors!=='object'||Array.isArray(value.sectors)||
     !Object.keys(value.sectors).length||!value.members||typeof value.members!=='object'||
     Array.isArray(value.members)||!Object.keys(value.members).length){ throw new Error('evidence'); }
  var bySector={}; Object.keys(value.sectors).forEach(function(sector){ bySector[sector]=[]; });
  var rosterPairs=[],sourceFailureMembers=0;
  Object.keys(value.members).forEach(function(symbol){
    var member=value.members[symbol];
    if(!member||typeof member!=='object'||typeof member.name!=='string'||!member.name.trim()||
       !Object.prototype.hasOwnProperty.call(value.sectors,member.sector)||
       !w1States(member.states,n)||!w1Array(member.distance_bps,n)||
       member.href!=='stock.html#'+encodeURIComponent(symbol)){ throw new Error('member alignment'); }
    Array.from(member.states).forEach(function(code,index){
      if(!W1_STATE_SET[code]) throw new Error('member state');
      var distance=member.distance_bps[index];
      if(code==='A'||code==='B'){
        if(typeof distance!=='number'||!Number.isFinite(distance)) throw new Error('member distance');
      }else if(distance!==null){ throw new Error('excluded member distance'); }
    });
    if(Array.from(member.states).every(function(code){ return code==='I'; })||
       Array.from(member.states).every(function(code){ return code==='U'; })) sourceFailureMembers+=1;
    rosterPairs.push([symbol,member.name,member.sector]); bySector[member.sector].push(member);
  });
  rosterPairs.sort(function(a,b){
    return w1CodePointCompare(a[0],b[0])||
      w1CodePointCompare(a[1],b[1])||w1CodePointCompare(a[2],b[2]);
  });
  var rosterId=await w1Sha256(JSON.stringify(rosterPairs));
  var reference=value.reference;
  if(!reference||reference.universe!=='S&P 500'||
     reference.member_count!==Object.keys(value.members).length||
     reference.roster_id!==rosterId||reference.observed_at!==null||
     !w1Text(reference.reconstruction)||!w1Text(reference.reconstruction_zh)){
    throw new Error('reference identity');
  }

  var anyRate=false;
  Object.keys(value.sectors).forEach(function(sector){
    var row=value.sectors[sector];
    ['above','eligible','expected','pct'].forEach(function(key){
      if(!w1Array(row&&row[key],n)) throw new Error('sector alignment');
    });
    ['H','M','I','U'].forEach(function(code){
      if(!row.excluded||!w1Array(row.excluded[code],n)) throw new Error('exclusion alignment');
    });
    for(var position=0;position<n;position+=1){
      var rawCounts=[row.above[position],row.eligible[position],row.expected[position],
        row.excluded.H[position],row.excluded.M[position],row.excluded.I[position],row.excluded.U[position]];
      if(rawCounts.some(function(count){ return !Number.isInteger(count)||count<0; })){
        throw new Error('sector count type');
      }
      var counts={A:0,B:0,H:0,M:0,I:0,U:0};
      bySector[sector].forEach(function(member){ counts[member.states[position]]+=1; });
      var above=counts.A,eligible=counts.A+counts.B,expected=bySector[sector].length;
      if(row.above[position]!==above||row.eligible[position]!==eligible||
         row.expected[position]!==expected){ throw new Error('summary detail disagreement'); }
      ['H','M','I','U'].forEach(function(code){
        if(row.excluded[code][position]!==counts[code]) throw new Error('exclusion disagreement');
      });
      var wanted=(eligible>=5&&eligible>=0.9*expected)?100*above/eligible:null;
      var actual=row.pct[position];
      if(wanted===null){ if(actual!==null) throw new Error('rate below floor'); }
      else{
        anyRate=true;
        if(typeof actual!=='number'||!Number.isFinite(actual)||Math.abs(actual-wanted)>1e-9){
          throw new Error('rate disagreement');
        }
      }
    }
  });
  if(typeof value.available!=='boolean'||value.available!==anyRate){ throw new Error('availability'); }
  var source=value.source||{},requestIdentity=source.request_identity||{};
  if(source.provider!=='licensed_vendor'||source.basis!=='split_adjusted'||
     !w1ShaId(source.response_set_id)||
     requestIdentity.resource!=='/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}'||
     requestIdentity.adjusted!==true||requestIdentity.sort!=='asc'||requestIdentity.limit!==50000){
    throw new Error('source identity');
  }
  if(!w1IsoDate(source.requested_start)||!w1IsoDate(source.requested_end)||
     !w1IsoDate(source.latest_expected_session)||source.requested_start>value.sessions[0]||
     source.requested_end!==value.sessions[value.sessions.length-1]||
     source.latest_expected_session!==source.requested_end){ throw new Error('source range'); }
  if(source.source_session!==null&&source.source_session!==undefined){
    if(!w1IsoDate(source.source_session)||source.source_session<source.requested_start||
       source.source_session>source.requested_end){ throw new Error('source session'); }
  }
  var requested=source.requested_member_count;
  var accepted=source.accepted_member_count;
  var unavailable=source.unavailable_member_count;
  if(requested!==Object.keys(value.members).length||!Number.isInteger(accepted)||
     !Number.isInteger(unavailable)||accepted<0||unavailable<0||
     accepted+unavailable!==requested||unavailable!==sourceFailureMembers||
     accepted!==Object.keys(value.members).length-sourceFailureMembers){
    throw new Error('source coverage');
  }
  if(value.available&&(source.source_session===null||source.source_session===undefined)){
    throw new Error('source session');
  }
  if((accepted>0&&!w1UtcClock(source.acquired_at))||
     (accepted===0&&source.acquired_at!==null&&source.acquired_at!==undefined&&!w1UtcClock(source.acquired_at))){
    throw new Error('acquisition clock');
  }
  return value;
}
window.SectorParticipation20=Object.freeze({validatePackage:validatePackageCore});

var section=document.getElementById('sector-participation');
if(!section) return;
section.hidden=false;

var pointer=((window.SECTOR_CENTRAL||{}).sector_participation)||{};
var read=document.getElementById('sp-read');
var calendar=document.getElementById('sp-calendar');
var detail=document.getElementById('sp-detail');
var summary=document.getElementById('sp-detail-summary');
var provenance=document.getElementById('sp-detail-provenance');
var constituents=document.getElementById('sp-constituents');
var statusNode=document.getElementById('sp-status');
var clearButton=document.getElementById('sp-clear');
var controls=document.getElementById('sp-window-controls');
if(!read||!calendar||!detail||!summary||!provenance||!constituents||!statusNode||!controls) return;

var WINDOW_VALUES=[63,126,252];
var STATE_ORDER={A:0,B:1,H:2,M:3,I:4,U:5};
var SECTOR_ZH={
  'Information Technology':'信息技术','Technology':'信息技术','Financials':'金融',
  'Consumer Discretionary':'可选消费','Health Care':'医疗保健',
  'Communication Services':'通信服务','Consumer Staples':'必需消费',
  'Industrials':'工业','Energy':'能源','Materials':'原材料','Real Estate':'房地产',
  'Utilities':'公用事业'
};
var state={windowSize:63,sector:null,session:null};
var pkg=null;
var unavailableKind=null;

function isZh(){ return document.documentElement.getAttribute('data-lang')==='zh'; }
function tx(en,zh){ return isZh()?(zh||en):en; }
function esc(value){
  return String(value==null?'':value).replace(/[&<>"']/g,function(ch){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
  });
}
function sectorName(name){ return isZh()?(SECTOR_ZH[name]||name):name; }
function stateLabel(code){
  var labels={
    A:['Above MA20','站上20日均线'],B:['At / below MA20','持平或低于20日均线'],
    H:['Insufficient history','历史不足'],M:['Expected session missing','缺少预期交易日'],
    I:['Invalid identity / basis / observation','身份、口径或观测无效'],
    U:['Source unavailable / refused','数据源不可用或拒绝']
  };
  return (labels[code]||[code,code])[isZh()?1:0];
}
function setStatus(message){ statusNode.textContent=message||''; }
function unavailable(kind){
  unavailableKind=kind;
  var invalid=kind==='invalid';
  read.innerHTML='<span class="sp-chip quiet">'+esc(tx(
    invalid?'Reading unavailable':'Not published yet',
    invalid?'读数不可用':'尚未发布'))+'</span> '+esc(tx(
    invalid?'The package could not be verified. Existing market and flow tools remain available.':
            'This descriptive read will appear after a qualified data update.',
    invalid?'数据包未通过校验。现有市场广度与资金流工具仍可使用。':
            '完成合格数据更新后将显示此描述性读数。'));
  calendar.innerHTML=''; detail.hidden=true;
  setStatus(tx('Sector participation unavailable.','板块参与度不可用。'));
}

async function validatePackage(value){
  return validatePackageCore(value,pointer.generation_id,pointer.observation_id);
}

function readQueryState(){
  var params=new URLSearchParams(window.location.search);
  var requested=parseInt(params.get('sp_window')||'',10);
  state.windowSize=WINDOW_VALUES.indexOf(requested)>=0?requested:63;
  state.sector=params.get('sp_sector');
  state.session=params.get('sp_session');
}
function writeQueryState(push){
  var url=new URL(window.location.href);
  url.searchParams.set('sp_window',String(state.windowSize));
  if(state.sector) url.searchParams.set('sp_sector',state.sector); else url.searchParams.delete('sp_sector');
  if(state.session) url.searchParams.set('sp_session',state.session); else url.searchParams.delete('sp_session');
  var target=url.pathname+url.search+url.hash;
  if(push&&history.pushState) history.pushState({sectorParticipation:true},'',target);
  else if(history.replaceState) history.replaceState({sectorParticipation:true},'',target);
}
function removeQueryState(){
  if(!pkg) return;
  var sectors=Object.keys(pkg.sectors).sort();
  state.windowSize=63;
  state.sector=sectors[0]||null;
  state.session=pkg.sessions[pkg.sessions.length-1]||null;
  var url=new URL(window.location.href);
  url.searchParams.delete('sp_window');
  url.searchParams.delete('sp_sector');
  url.searchParams.delete('sp_session');
  if(history.pushState) history.pushState({sectorParticipation:true},'',url.pathname+url.search+url.hash);
  render();
}

function normalizeSelection(){
  var sectors=Object.keys(pkg.sectors).sort();
  if(sectors.indexOf(state.sector)<0) state.sector=sectors[0]||null;
  if(pkg.sessions.indexOf(state.session)<0) state.session=pkg.sessions[pkg.sessions.length-1]||null;
}
function pctText(value){ return value==null?'—':Math.round(Number(value))+'%'; }
function tone(value){
  if(value==null) return 'none';
  return value>=55?'hi':value>=45?'mid':'lo';
}
function shortDate(iso){
  var parts=String(iso).split('-');
  return parts.length===3?parts[1]+'/'+parts[2]:iso;
}
function calendarLabel(sector,session,row,index){
  var pct=row.pct[index];
  return sectorName(sector)+' · '+session+' · '+(pct==null?tx('no displayed rate','无公开读数'):pctText(pct))+
    ' · '+row.above[index]+'/'+row.eligible[index]+'/'+row.expected[index];
}
function renderControls(){
  Array.prototype.forEach.call(controls.querySelectorAll('[data-sp-window]'),function(button){
    var selected=Number(button.getAttribute('data-sp-window'))===state.windowSize;
    button.classList.toggle('on',selected);
    button.setAttribute('aria-pressed',selected?'true':'false');
  });
}
function renderCalendar(){
  var sectors=Object.keys(pkg.sectors).sort();
  var start=Math.max(0,pkg.sessions.length-state.windowSize);
  var indexes=[];
  for(var i=start;i<pkg.sessions.length;i++) indexes.push(i);
  var html='<div class="sp-scroll"><table class="sp-table"><thead><tr><th scope="col" class="sp-sector-head">'+
    esc(tx('Sector','板块'))+'</th>';
  indexes.forEach(function(index){
    var session=pkg.sessions[index];
    html+='<th scope="col"><time datetime="'+esc(session)+'" title="'+esc(session)+'">'+esc(shortDate(session))+'</time></th>';
  });
  html+='</tr></thead><tbody>';
  sectors.forEach(function(sector,rowIndex){
    var row=pkg.sectors[sector];
    html+='<tr><th scope="row" title="'+esc(sector)+'">'+esc(sectorName(sector))+'</th>';
    indexes.forEach(function(index,colIndex){
      var session=pkg.sessions[index],value=row.pct[index];
      var selected=sector===state.sector&&session===state.session;
      html+='<td><button type="button" class="sp-cell '+tone(value)+(selected?' selected':'')+'" '+
        'data-sp-sector="'+esc(sector)+'" data-sp-session="'+esc(session)+'" data-sp-index="'+index+'" '+
        'data-sp-row="'+rowIndex+'" data-sp-col="'+colIndex+'" aria-pressed="'+(selected?'true':'false')+'" '+
        'aria-label="'+esc(calendarLabel(sector,session,row,index))+'">'+esc(pctText(value))+'</button></td>';
    });
    html+='</tr>';
  });
  html+='</tbody></table></div>';
  calendar.innerHTML=html;
}
function clockLine(label,value){ return value?'<span><b>'+esc(label)+'</b> '+esc(value)+'</span>':''; }
function renderDetail(){
  var index=pkg.sessions.indexOf(state.session);
  var row=pkg.sectors[state.sector];
  if(index<0||!row){ detail.hidden=true; return; }
  detail.hidden=false;
  var value=row.pct[index];
  var exclusions=['H','M','I','U'].map(function(code){
    return '<span class="sp-excl"><b>'+code+'</b> '+row.excluded[code][index]+' · '+esc(stateLabel(code))+'</span>';
  }).join('');
  summary.innerHTML='<div class="sp-detail-title"><h3>'+esc(sectorName(state.sector))+'</h3><time datetime="'+
    esc(state.session)+'">'+esc(state.session)+'</time></div><div class="sp-kpis">'+
    '<div><span>'+esc(tx('Participation','参与度'))+'</span><b>'+esc(pctText(value))+'</b></div>'+
    '<div><span>'+esc(tx('Above / eligible / expected','站上 / 合格 / 预期'))+'</span><b>'+row.above[index]+' / '+row.eligible[index]+' / '+row.expected[index]+'</b></div></div>'+exclusions;
  var source=pkg.source||{},reference=pkg.reference||{},method=pkg.method||{};
  var basis=source.basis==='split_adjusted'?tx('Split-adjusted closes','拆股调整收盘价'):(source.basis||'—');
  var rosterStatement=isZh()?(reference.reconstruction_zh||reference.reconstruction||''):(reference.reconstruction||'');
  var unavailableReason='';
  if(value==null){
    unavailableReason=row.eligible[index]<5
      ?tx('Unavailable: fewer than 5 eligible constituents.','不可用：合格成分股少于5只。')
      :tx('Unavailable: eligible coverage is below 90% of the reference roster.','不可用：合格覆盖率低于参考名单的90%。');
  }
  provenance.innerHTML=(unavailableReason?'<p><b>'+esc(unavailableReason)+'</b></p>':'')+'<div class="sp-clock-grid">'+
    clockLine(tx('Source session','数据交易日'),source.source_session)+
    clockLine(tx('Generation expected through','本代预期截至'),source.latest_expected_session)+
    clockLine(tx('Current completed session','当前已完成交易日'),pointer.current_expected_session)+
    clockLine(tx('Generation','数据代'),pkg.generation_id)+
    clockLine(tx('Price basis','价格口径'),basis)+
    clockLine(tx('Requested range','请求范围'),(source.requested_start||'—')+' → '+(source.requested_end||'—'))+
    clockLine(tx('Acquired','采集时间'),source.acquired_at)+
    clockLine(tx('Computed','计算时间'),pkg.computed_at)+
    clockLine(tx('Published','发布时间'),pkg.published_at)+'</div><p>'+esc(tx(
      'Method: close above the mean of 20 consecutive expected sessions; display requires at least 5 eligible names and 90% roster coverage.',
      '方法：收盘价高于连续20个预期交易日均值；公开读数至少需要5只合格成分股且覆盖率达到90%。'))+'</p><p>'+esc(rosterStatement)+
      ' '+esc(tx('Roster','名单'))+': '+esc(reference.roster_id||'—')+'. '+esc(tx(
      'Descriptive evidence only—not institutional cash flow, a forecast, or a trade recommendation.',
      '仅为描述性证据，不代表机构资金流、预测或交易建议。'))+'</p>';

  var names=Object.keys(pkg.members).filter(function(symbol){ return pkg.members[symbol].sector===state.sector; });
  names.sort(function(a,b){
    var sa=pkg.members[a].states[index],sb=pkg.members[b].states[index];
    return STATE_ORDER[sa]-STATE_ORDER[sb]||a.localeCompare(b);
  });
  var rows=names.map(function(symbol){
    var member=pkg.members[symbol],code=member.states[index],distance=member.distance_bps[index];
    var distanceText=distance==null?'—':((distance>0?'+':'')+(Number(distance)/100).toFixed(2)+'%');
    var href=/^stock\.html#/.test(member.href||'')?member.href:'#';
    return '<tr><td><a href="'+esc(href)+'">'+esc(symbol)+'</a><span class="sp-member-name">'+
      esc(member.name)+'</span></td><td><span class="sp-state '+code+'">'+
      code+'</span> '+esc(stateLabel(code))+'</td><td class="num">'+esc(distanceText)+'</td></tr>';
  }).join('');
  constituents.innerHTML='<div class="sp-const-head"><h4>'+esc(tx('Reference constituents','参考成分股'))+'</h4><span>'+names.length+'</span></div><div class="sp-const-scroll"><table><thead><tr><th>'+esc(tx('Name','名称'))+'</th><th>'+esc(tx('Dated state','当日状态'))+'</th><th>'+esc(tx('Distance to MA20','距20日均线'))+'</th></tr></thead><tbody>'+rows+'</tbody></table></div>';
}
function renderRead(){
  var stale=pointer.status==='stale'||Boolean(pointer.stale);
  read.innerHTML=(stale?'<span class="sp-chip">'+esc(tx('Showing last complete generation','显示最近完整一代'))+'</span> ':'')+
    esc(tx('Select a sector and completed session to inspect exact numerator, denominator, exclusions, and dated constituent states.',
           '选择板块与已完成交易日，查看精确分子、分母、排除项及当日成分股状态。'));
}
function render(){
  if(!pkg) return;
  normalizeSelection();
  renderControls(); renderRead(); renderCalendar(); renderDetail();
  setStatus(tx('Sector participation updated for '+state.session+'.','板块参与度已更新至 '+state.session+'。'));
}

controls.addEventListener('click',function(event){
  var button=event.target.closest('[data-sp-window]'); if(!button||!pkg) return;
  var value=Number(button.getAttribute('data-sp-window')); if(WINDOW_VALUES.indexOf(value)<0) return;
  state.windowSize=value; writeQueryState(true); render();
});
calendar.addEventListener('click',function(event){
  var button=event.target.closest('button[data-sp-sector]'); if(!button||!pkg) return;
  state.sector=button.getAttribute('data-sp-sector');
  state.session=button.getAttribute('data-sp-session');
  writeQueryState(true); render();
});
calendar.addEventListener('keydown',function(event){
  var button=event.target.closest('button[data-sp-row]'); if(!button) return;
  var row=Number(button.getAttribute('data-sp-row')),col=Number(button.getAttribute('data-sp-col'));
  if(event.key==='ArrowLeft') col-=1; else if(event.key==='ArrowRight') col+=1;
  else if(event.key==='ArrowUp') row-=1; else if(event.key==='ArrowDown') row+=1; else return;
  var target=calendar.querySelector('button[data-sp-row="'+row+'"][data-sp-col="'+col+'"]');
  if(target){ event.preventDefault(); target.focus(); }
});
if(clearButton) clearButton.addEventListener('click',removeQueryState);
window.addEventListener('popstate',function(){ if(pkg){ readQueryState(); render(); } });
document.addEventListener('langchange',function(){ if(pkg) render(); else if(unavailableKind) unavailable(unavailableKind); });

readQueryState();
if(!pointer.url||!pointer.generation_id||!pointer.observation_id){ unavailable(pointer.status); return; }
setStatus(tx('Loading sector participation…','正在加载板块参与度…'));
read.textContent=tx('Loading the dated participation generation…','正在加载带日期的参与度数据…');
window.__sectorParticipation20Promise=window.__sectorParticipation20Promise||
  fetch(pointer.url,{credentials:'same-origin',cache:'no-store'})
    .then(function(response){ if(!response.ok) throw new Error('HTTP '+response.status); return response.json(); })
    .then(validatePackage);
window.__sectorParticipation20Promise.then(function(value){ unavailableKind=null; pkg=value; render(); }).catch(function(error){
  console.warn('sector participation package refused',error); unavailable('invalid');
});
})();
