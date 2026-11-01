/* One consumer of /api/ticker-news. No provider fetch, private-content cache,
 * scoring rules or publication authority exists in this browser module. */
(function(root,factory){
  "use strict";
  var api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  if(root.document){
    if(root.document.readyState==="loading")root.document.addEventListener("DOMContentLoaded",function(){api.mount(root.document,root);},{once:true});
    else api.mount(root.document,root);
  }
})(typeof window!=="undefined"?window:globalThis,function(){
  "use strict";
  function symbol(value){var s=typeof value==="string"?value.trim().replace(/^\$/,"").toUpperCase():"";return /^[A-Z][A-Z0-9.\-]{0,11}$/.test(s)?s:"";}
  function safeURL(value){try{var u=new URL(value);return /^(https?:)$/.test(u.protocol)&&!u.username&&!u.password?u.href:"";}catch(_){return "";}}
  function validSnapshot(p,ticker){
    return !!(p&&p.schema==="ticker_news.snapshot.v1"&&p.ticker===ticker&&Array.isArray(p.rows)&&p.rows.length<=200&&(p.change_sequence===undefined||Number.isSafeInteger(p.change_sequence)&&p.change_sequence>=0)&&typeof p.has_more==="boolean"&&(!p.has_more||Number.isSafeInteger(p.next_cursor)&&p.next_cursor>0)&&p.rows.every(function(r){return r&&typeof r.story_id==="string"&&r.story_id.length>0&&typeof r.title==="string"&&Number.isSafeInteger(r.sequence)&&r.sequence>0;})&&new Set(p.rows.map(function(r){return r.story_id;})).size===p.rows.length);
  }
  function parser(emit){var buffer="";return function(chunk){
    buffer+=chunk;if(buffer.length>1048576)throw new Error("stream frame too large");
    var match;while((match=/\r?\n\r?\n/.exec(buffer))){
      var frame=buffer.slice(0,match.index);buffer=buffer.slice(match.index+match[0].length);var event="message",data=[];
      frame.split(/\r?\n/).forEach(function(line){if(line.startsWith("event:"))event=line.slice(6).trim();else if(line.startsWith("data:"))data.push(line.slice(5).replace(/^ /,""));});
      if(data.length)emit(event,JSON.parse(data.join("\n")));
    }
  };}
  function mount(doc,win){
    var panel=doc.querySelector("[data-ticker-news]");if(!panel||panel.dataset.mounted)return null;panel.dataset.mounted="1";
    var find=function(name){return panel.querySelector("[data-tn-"+name+"]");};
    var zh=function(){return doc.documentElement.dataset.lang==="zh";},tx=function(en,cn){return zh()?cn:en;};
    var fixed=symbol(panel.dataset.ticker),current="",cursor=null,packet=null,filter="signal",visibleIds=[],pendingIds=[];
    var generation=0,requests=new Set(),groupRequests=new Map(),timers=new Map(),stream=null,refreshing=false,dirty=false,disposed=false;
    var inbox=[],holdNews=false,deliverySequence=0,projectionReady=false;
    function node(tag,cls,text){var n=doc.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=String(text);return n;}
    function later(key,fn,ms){cancel(key);timers.set(key,win.setTimeout(function(){timers.delete(key);fn();},ms));}
    function cancel(key){if(timers.has(key))win.clearTimeout(timers.get(key));timers.delete(key);}
    function active(id){return !disposed&&!doc.hidden&&id===generation;}
    function status(state,en,cn){var e=find("status");e.dataset.state=state;e.textContent=tx(en,cn);}
    function stopStream(){cancel("renew");if(stream){stream.abort();stream=null;}}
    function stop(){generation++;requests.forEach(function(c){c.abort();});requests.clear();groupRequests.forEach(function(c){c.abort();});groupRequests.clear();stopStream();timers.forEach(function(id){win.clearTimeout(id);});timers.clear();refreshing=false;dirty=false;clearPending();deliverySequence=0;projectionReady=false;}
    function purge(){packet=null;visibleIds=[];pendingIds=[];find("rows").replaceChildren();find("updates").hidden=true;find("more").hidden=true;find("coverage").hidden=true;find("count").textContent="";}
    function message(text){find("message").textContent=text;find("message").hidden=!text;}
    function time(value){var n=Date.parse(value);return Number.isFinite(n)?new Intl.DateTimeFormat(zh()?"zh-CN":"en-GB",{dateStyle:"medium",timeStyle:"short"}).format(n):tx("Time not supplied","未提供时间");}
    function publisher(row){return row.publisher||String(row.source||"").replace(/^massive:/,"").replace(/^benzinga$/,"Benzinga");}
    function comparison(row){
      if(row.reporting_state==="reports_differ")return {state:row.reporting_state,label:tx("Reports differ","报道存在差异"),note:tx("Reports in this group use different wording or figures. Compare the sources below.","此组报道的表述或数据存在差异，请对比下方各来源。")};
      if(row.reporting_state==="comparison_limited")return {state:row.reporting_state,label:tx("Comparison limited","对比尚不完整"),note:tx("This group has not been fully compared. Review the individual reports below.","尚未完成此组报道的全面对比，请查看下方各篇报道。")};
      return null;
    }
    function link(value,text){var url=safeURL(value),el=node(url?"a":"span","",text);if(url){el.href=url;el.target="_blank";el.rel="noopener noreferrer";}return el;}
    async function request(path,controller,accept){
      if(!win.MDXAuth||typeof win.MDXAuth.client!=="function"){var noAuth=new Error("auth");noAuth.status=401;throw noAuth;}
      var abort,session;
      var cancelled=new Promise(function(_,reject){abort=function(){reject(new Error("aborted"));};controller.signal.addEventListener("abort",abort,{once:true});if(controller.signal.aborted)abort();});
      try{session=await Promise.race([(async function(){var client=await win.MDXAuth.client();return client.auth.getSession();})(),cancelled]);}
      finally{controller.signal.removeEventListener("abort",abort);}
      if(controller.signal.aborted)throw new Error("aborted");
      var token=session&&session.data&&session.data.session&&session.data.session.access_token;
      if(!token){var signedOut=new Error("auth");signedOut.status=401;throw signedOut;}
      var response=await win.fetch(path,{headers:{Accept:accept||"application/json",Authorization:"Bearer "+token},credentials:"same-origin",cache:"no-store",signal:controller.signal});
      if(!response.ok){var error=new Error("news unavailable");error.status=response.status;throw error;}
      return accept?response:response.json();
    }
    function errorState(error){
      stop();purge();find("retry").hidden=false;find("signin").hidden=error.status!==401;
      if(error.status===401){status("restricted","Sign in to read company news","登录后阅读公司新闻");message(tx("Your account connects this dossier to the same reporting available in Terminal.","登录账户，将此档案连接到终端中的同一新闻源。"));find("retry").hidden=true;}
      else if(error.status===403){status("restricted","Access required","需要访问权限");message(tx("Company news requires an eligible account and current source access.","公司新闻需要符合条件的账户及有效来源访问权限。"));}
      else if(error.status===404){status("unavailable","Ticker not covered","暂未覆盖此股票");message(tx("This ticker is outside the current company news coverage.","此股票暂不在公司新闻覆盖范围内。"));}
      else if(error.status===429){status("degraded","Request limit reached","已达到请求上限");message(tx("Please retry in a minute.","请在一分钟后重试。"));}
      else{status("unavailable","Reporting temporarily unavailable","报道暂不可用");message(tx("The feed or its display permission could not be confirmed. Retry to check again.","无法确认新闻源或其展示权限，请重试。"));}
    }
    function report(row){
      var card=node("div","tn-member");card.appendChild(link(row.url,row.title));card.appendChild(node("p","",row.teaser||""));card.appendChild(node("small","",publisher(row)+" · "+time(row.published_at||row.received_at)));return card;
    }
    async function loadGroup(details,row){
      if(!details.open||details.dataset.loaded==="1")return;
      var body=details.querySelector(".tn-members"),id=generation,controller=new AbortController();groupRequests.set(details,controller);body.textContent=tx("Loading reports…","正在加载报道…");
      try{
        var p=await request("/api/ticker-news/stories/"+encodeURIComponent(row.story_id),controller);
        if(!active(id)||!details.isConnected||!details.open)return;
        if(!p||p.schema!=="ticker_news.story.v1"||p.story_id!==row.story_id||!Array.isArray(p.members)||p.members.length>1000)throw new Error("invalid story");
        body.replaceChildren();p.members.forEach(function(member){if(member.story_id!==row.story_id||typeof member.title!=="string")throw new Error("invalid member");body.appendChild(report(member));});details.dataset.loaded="1";
        if(!p.members.length)body.textContent=tx("No accessible reports remain.","暂无可访问报道。");
      }catch(error){if(active(id)&&details.isConnected){body.replaceChildren(node("p","",tx("Reports could not be loaded.","无法加载报道。")));var retry=node("button","",tx("Retry","重试"));retry.type="button";retry.onclick=function(){loadGroup(details,row);};body.appendChild(retry);}}
      finally{groupRequests.delete(details);}
    }
    function makeCard(row){
      var card=node("article","tn-row");card.dataset.story=row.story_id;card.dataset.revision=JSON.stringify(row);
      var meta=node("div","tn-meta");meta.appendChild(node("strong","",publisher(row)));
      var amended=row.updated_at&&Date.parse(row.updated_at)>Date.parse(row.published_at);
      meta.appendChild(node("time","",(amended?tx("Updated ","更新 "):"")+time(amended?row.updated_at:row.published_at||row.received_at)));
      if(row.quality&&row.quality.low_value)meta.appendChild(node("span","tn-routine",tx("Routine coverage","例行报道")));
      var comparisonInfo=comparison(row);
      if(comparisonInfo){var badge=node("span","tn-comparison",comparisonInfo.label);badge.dataset.state=comparisonInfo.state;badge.title=comparisonInfo.note;meta.appendChild(badge);}
      card.appendChild(meta);var title=node("h3","tn-title");title.appendChild(link(row.url,row.title));card.appendChild(title);
      if(row.teaser)card.appendChild(node("p","tn-teaser",row.teaser));
      if(row.item_count>1){
        var details=node("details","tn-group"),summary=node("summary","",tx(row.item_count+" reports · "+row.source_count+" publisher"+(row.source_count===1?"":"s"),row.item_count+" 篇报道 · "+row.source_count+" 个来源"));
        details.appendChild(summary);if(comparisonInfo)details.appendChild(node("p","tn-comparison-note",comparisonInfo.note));details.appendChild(node("div","tn-members"));details.addEventListener("toggle",function(){if(!details.open){var c=groupRequests.get(details);if(c)c.abort();groupRequests.delete(details);}else loadGroup(details,row);});card.appendChild(details);
      }return card;
    }
    function validChange(kind,p){
      return !!(p&&p.kind===kind&&typeof p.story_id==="string"&&p.story_id.length>0&&p.story_id.length<=256&&Number.isSafeInteger(p.sequence)&&p.sequence>0);
    }
    function completeProjection(p){
      var own=function(k){return Object.prototype.hasOwnProperty.call(p,k);};
      var nullableTime=function(k){return own(k)&&(p[k]===null||typeof p[k]==="string"&&Number.isFinite(Date.parse(p[k])));};
      return Number.isSafeInteger(p.projection_sequence)&&p.projection_sequence>0&&
        ["source","source_item_id","title","url","teaser","publisher"].every(function(k){return typeof p[k]==="string";})&&
        p.title.length>0&&Number.isSafeInteger(p.item_count)&&p.item_count>0&&
        Number.isSafeInteger(p.source_count)&&p.source_count>0&&p.source_count<=p.item_count&&
        ["published_at","updated_at","received_at"].every(nullableTime)&&
        ["not_compared","reports_differ","no_material_difference","comparison_limited"].includes(p.reporting_state)&&
        own("quality")&&(p.quality===null||typeof p.quality==="object"&&!Array.isArray(p.quality)&&
          typeof p.quality.low_value==="boolean"&&Number.isFinite(p.quality.score))&&
        own("annotation")&&(p.annotation===null||typeof p.annotation==="object"&&!Array.isArray(p.annotation));
    }
    function projection(p){
      var row={sequence:p.projection_sequence};
      ["story_id","source","source_item_id","title","url","teaser","publisher","provider","source_count",
        "item_count","published_at","updated_at","received_at","observed_at","universe_revision",
        "quality","annotation","reporting_state"].forEach(function(k){if(Object.prototype.hasOwnProperty.call(p,k))row[k]=p[k];});
      return row;
    }
    function orderRows(a,b){return b.sequence-a.sequence||(a.story_id<b.story_id?-1:a.story_id>b.story_id?1:0);}
    function clearPending(){cancel("apply");inbox=[];holdNews=false;}
    function clearGroupDetails(){
      groupRequests.forEach(function(c){c.abort();});groupRequests.clear();
      find("rows").querySelectorAll("details").forEach(function(d){d.open=false;d.dataset.loaded="0";var body=d.querySelector(".tn-members");if(body)body.replaceChildren();});
    }
    function removeStory(storyId){
      if(!packet)return;
      packet.rows=packet.rows.filter(function(r){return r.story_id!==storyId;});
      visibleIds=visibleIds.filter(function(id){return id!==storyId;});
      pendingIds=pendingIds.filter(function(id){return id!==storyId;});
    }
    function flushChanges(){
      if(!packet||cursor!==null||doc.hidden||disposed){clearPending();return;}
      var rows=new Map(packet.rows.map(function(r){return [r.story_id,r];})),oldVisible=new Set(visibleIds),hold=holdNews;
      inbox.forEach(function(change){
        if(change.kind==="remove")rows.delete(change.story_id);
        else rows.set(change.story_id,projection(change)); // Replace the complete authorized projection as one unit.
      });
      inbox=[];holdNews=false;packet.rows=Array.from(rows.values()).sort(orderRows);
      if(packet.rows.length>40){packet.rows=packet.rows.slice(0,40);packet.has_more=true;}
      // Snapshot pagination is exclusive (< cursor): use the last KEPT row.
      if(packet.has_more&&packet.rows.length)packet.next_cursor=packet.rows[packet.rows.length-1].sequence;
      if(hold){
        var present=new Set(packet.rows.map(function(r){return r.story_id;}));
        visibleIds=visibleIds.filter(function(id){return present.has(id);});
        pendingIds=packet.rows.filter(function(r){return !oldVisible.has(r.story_id);}).map(function(r){return r.story_id;});
      }else{visibleIds=packet.rows.map(function(r){return r.story_id;});pendingIds=[];}
      render();
    }
    function receiveChange(kind,p){
      if(!validChange(kind,p)){invalidate();return;}
      if(p.sequence<=deliverySequence)return;
      deliverySequence=p.sequence; // Delivery position never orders display rows.
      if(kind==="upsert"&&(!projectionReady||!completeProjection(p))){
        // An older/partial contract cannot safely retain omitted permission fields.
        removeStory(p.story_id);render();invalidate();return;
      }
      if(inbox.length>=200){invalidate();return;}
      holdNews=holdNews||panel.contains(doc.activeElement)||panel.getBoundingClientRect().top<0;
      inbox.push(p);
      if(kind==="remove"){cancel("apply");flushChanges();}
      else if(!timers.has("apply"))later("apply",flushChanges,16);
    }
    function render(){
      panel.querySelector(".tn-filters").setAttribute("aria-label",tx("News coverage","新闻覆盖"));
      find("symbol").textContent=current;find("terminal").href="https://app.mastermind-x.com/terminal?sym="+encodeURIComponent(current)+"&from=macro-dossier";
      panel.querySelectorAll("[data-tn-filter]").forEach(function(b){b.setAttribute("aria-pressed",String(b.dataset.tnFilter===filter));});
      find("latest").hidden=cursor===null;
      if(!packet)return;
      var byId=new Map(packet.rows.map(function(r){return [r.story_id,r];})),rows=visibleIds.map(function(id){return byId.get(id);}).filter(Boolean);
      var shown=rows.filter(function(r){return filter==="all"||!r.quality||!r.quality.low_value;});
      var host=find("rows"),existing=new Map(Array.from(host.children).map(function(c){return [c.dataset.story,c];})),keep=new Set(shown.map(function(r){return r.story_id;}));
      existing.forEach(function(card,id){if(!keep.has(id)){card.querySelectorAll("details").forEach(function(d){var c=groupRequests.get(d);if(c)c.abort();groupRequests.delete(d);});card.remove();}});
      shown.forEach(function(row,index){
        var card=existing.get(row.story_id);if(!card||card.dataset.revision!==JSON.stringify(row)){
          var fresh=makeCard(row);
          if(card){card.querySelectorAll("details").forEach(function(d){var c=groupRequests.get(d);if(c)c.abort();groupRequests.delete(d);});card.replaceWith(fresh);}card=fresh;
        }
        if(host.children[index]!==card)host.insertBefore(card,host.children[index]||null);
      });
      find("count").textContent=String(packet.rows.length);find("more").hidden=!packet.has_more;find("retry").hidden=true;find("signin").hidden=true;
      find("updates").hidden=!pendingIds.length;find("updates").textContent=tx("Show "+pendingIds.length+" new "+(pendingIds.length===1?"story":"stories"),"查看 "+pendingIds.length+" 条新报道");
      message(shown.length?"":packet.rows.length?tx("No high-signal stories in this page. Select All reporting to see every available report.","此页暂无重点新闻，选择「全部报道」可查看所有可用报道。"):tx("No company stories in this window. New reporting will appear here as it arrives.","此时间范围暂无公司新闻，新报道到达后将显示在这里。"));
      var h=packet.source_health||{},state=h.state||packet.state;
      if(cursor!==null)status("history","Earlier reporting","更早报道");
      else if(state==="live"||state==="quiet")status("live","Source reporting active · auto refresh","来源报道活跃 · 自动刷新");
      else if(state==="catching_up")status("catching_up","Catching up with reporting","正在同步报道");
      else status("degraded","Coverage delayed · showing available reports","覆盖延迟 · 显示可用报道");
      var extras=Array.isArray(h.additional_sources)?h.additional_sources:[];find("coverage").hidden=!extras.length;
      find("coverage").textContent=extras.map(function(e){var labels={available:tx("Additional reporting: refresh complete","补充报道：刷新完成"),waiting:tx("Additional reporting: awaiting refresh","补充报道：等待刷新"),restricted:tx("Additional reporting: permission required","补充报道：需要授权"),unavailable:tx("Additional reporting: unavailable","补充报道：暂不可用")};return (labels[e.state]||tx("Additional reporting: refresh delayed","补充报道：刷新延迟"))+(e.last_successful_poll?tx(" · Last completed "," · 最近完成 ")+time(e.last_successful_poll):"");}).join(" · ");
    }
    function accept(p,background){
      var old=new Set(visibleIds),hold=background&&(panel.contains(doc.activeElement)||panel.getBoundingClientRect().top<0);
      clearGroupDetails();packet=p;
      if(hold){visibleIds=visibleIds.filter(function(id){return p.rows.some(function(r){return r.story_id===id;});});pendingIds=p.rows.filter(function(r){return !old.has(r.story_id);}).map(function(r){return r.story_id;});}
      else{visibleIds=p.rows.map(function(r){return r.story_id;});pendingIds=[];}
      render();
    }
    function invalidate(){
      stopStream();clearPending();
      if(refreshing){dirty=true;return;}
      if(!timers.has("change"))later("change",function(){refresh(true);},40);
    }
    async function connectStream(id,after){
      if(!active(id)||cursor!==null||stream)return;
      var controller=new AbortController();stream=controller;
      var connected=function(){return active(id)&&stream===controller&&!controller.signal.aborted&&cursor===null;};
      later("renew",function(){if(connected())refresh(true);},240000);
      try{
        var response=await request("/api/ticker-news/"+encodeURIComponent(current)+"/stream?after_sequence="+after,controller,"text/event-stream");
        if(!connected())return;
        if(!response.body||typeof response.body.getReader!=="function")throw new Error("stream unsupported");
        var reader=response.body.getReader(),decoder=new TextDecoder(),parse=parser(function(event,p){
          if(!connected())return;
          if(event==="restricted"||event==="reset"){stop();purge();status("restricted","Refreshing source access","正在更新来源权限");later("access",function(){refresh(false);},1000);}
          else if(event==="unavailable"){stopStream();clearPending();status("degraded","Live updates interrupted","实时更新已中断");later("reconnect",function(){refresh(true);},5000);}
          else if(event==="upsert"||event==="remove")receiveChange(event,p);
          else invalidate();
        });
        while(connected()){var chunk=await reader.read();if(chunk.done)break;parse(decoder.decode(chunk.value,{stream:true}));}
        if(connected())throw new Error("stream closed");
      }catch(error){if(connected()){stopStream();clearPending();status("degraded","Live updates interrupted","实时更新已中断");later("reconnect",function(){refresh(true);},5000);}}
      finally{if(stream===controller){stream=null;cancel("renew");}}
    }
    async function refresh(background){
      if(!current||doc.hidden||disposed)return;
      if(refreshing){dirty=true;return;}
      // Fence the previous stream before asking for an authoritative snapshot.
      // Reconnect from its atomic journal watermark; never replay old callbacks.
      stopStream();clearPending();cancel("change");cancel("reconnect");
      var id=generation,controller=new AbortController();requests.add(controller);refreshing=true;
      var timeout=win.setTimeout(function(){controller.abort();},12000);
      if(!background)status("loading","Loading reporting…","正在加载报道…");
      try{
        var p=await request("/api/ticker-news/"+encodeURIComponent(current)+"?limit=40"+(cursor===null?"":"&cursor="+cursor),controller);
        if(!active(id)||controller.signal.aborted)return;
        if(!validSnapshot(p,current))throw new Error("invalid snapshot");
        projectionReady=Number.isSafeInteger(p.change_sequence);
        deliverySequence=projectionReady?p.change_sequence:Math.max(deliverySequence,p.rows.reduce(function(max,r){return Math.max(max,r.sequence);},0));
        accept(p,background);
        if(cursor===null)connectStream(id,deliverySequence);
      }catch(error){if(active(id))errorState(error);}
      finally{win.clearTimeout(timeout);requests.delete(controller);if(id===generation){refreshing=false;if(dirty){dirty=false;invalidate();}}}
    }
    function start(value,nextCursor){var next=symbol(value);if(!next)return;stop();purge();current=next;cursor=nextCursor===undefined?null:nextCursor;message("");render();refresh(false);}
    panel.querySelectorAll("[data-tn-filter]").forEach(function(b){b.addEventListener("click",function(){filter=b.dataset.tnFilter;render();});});
    find("retry").addEventListener("click",function(){refresh(false);});
    find("more").addEventListener("click",function(){if(packet&&packet.has_more)start(current,packet.next_cursor);});
    find("latest").addEventListener("click",function(){start(current);});
    find("updates").addEventListener("click",function(){visibleIds=packet.rows.map(function(r){return r.story_id;});pendingIds=[];render();});
    doc.addEventListener("langchange",function(){find("rows").querySelectorAll("[data-revision]").forEach(function(n){n.dataset.revision="";});render();});
    doc.addEventListener("visibilitychange",function(){if(doc.hidden){stop();purge();status("paused","Paused in background","后台已暂停");}else if(current)refresh(false);});
    win.addEventListener("pagehide",function(){disposed=true;stop();purge();});
    win.addEventListener("pageshow",function(event){if(event.persisted){disposed=false;if(current)refresh(false);}});
    win.addEventListener("mdx-auth",function(event){if((event.detail||{}).event==="PREFS_SAVED")return;stop();purge();if(current)refresh(false);});
    win.addEventListener("mmx-ticker-news",function(event){var next=symbol((event.detail||{}).ticker);if(next&&next!==current)start(next);});
    if(!fixed)win.addEventListener("hashchange",function(){var next=symbol(decodeURIComponent(win.location.hash.slice(1)));if(next&&next!==current)start(next);});
    var initial=fixed||symbol(decodeURIComponent(win.location.hash.slice(1)));if(initial)start(initial);else{status("idle","Choose a company","选择一家公司");message(tx("Choose a stock to see its reporting.","选择股票以查看相关新闻。"));}
    return {start:start,getState:function(){return {ticker:current,cursor:cursor,filter:filter,ids:visibleIds.slice(),pending:pendingIds.slice(),deliverySequence:deliverySequence,projectionReady:projectionReady};}};
  }
  return {symbol:symbol,safeURL:safeURL,validSnapshot:validSnapshot,parser:parser,mount:mount};
});