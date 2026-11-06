/* Company news consumes the incumbent paid, source-rights-gated qbus API.
 * Stream events invalidate an authoritative snapshot; they are never treated as
 * a second story store. Licensed reporting exists only in this open workspace.
 */
(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root.document) api.mount(root.document, root);
})(typeof window !== "undefined" ? window : globalThis, function () {
  "use strict";
  function clean(value) { return typeof value === "string" ? value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim() : ""; }
  function ticker(value) { var t=clean(value).replace(/^\$/, "").toUpperCase(); return /^[A-Z][A-Z0-9.\-]{0,11}$/.test(t) ? t : ""; }
  function safeURL(value) { try { var u=new URL(value); return /^https?:$/.test(u.protocol)&&!u.username&&!u.password ? u.href : ""; } catch (_) { return ""; } }
  function validRow(row) { return row&&typeof row.story_id==="string"&&row.story_id.length>0&&typeof row.title==="string"&&Number.isSafeInteger(row.sequence)&&row.sequence>=0; }
  function validSnapshot(p, symbol) {
    if(!p||p.schema!=="ticker_news.snapshot.v1"||p.ticker!==symbol||!Array.isArray(p.rows)||p.rows.length>200||!p.rows.every(validRow))return false;
    return new Set(p.rows.map(function(r){return r.story_id;})).size===p.rows.length&&typeof p.has_more==="boolean"&&(!p.has_more||Number.isSafeInteger(p.next_cursor)&&p.next_cursor>0);
  }
  function revision(row) { return JSON.stringify([row.sequence,row.title,row.url,row.teaser,row.source_count,row.item_count,row.updated_at]); }
  function streamParser(emit) {
    var buffer="";
    return function (chunk) {
      buffer+=chunk;
      if(buffer.length>262144)throw new Error("stream frame too large");
      var match;
      while((match=/\r?\n\r?\n/.exec(buffer))) {
        var frame=buffer.slice(0,match.index);buffer=buffer.slice(match.index+match[0].length);
        var event="message",data=[];
        frame.split(/\r?\n/).forEach(function(line){if(line.startsWith("event:"))event=line.slice(6).trim();else if(line.startsWith("data:"))data.push(line.slice(5).replace(/^ /,""));});
        if(data.length)emit(event,JSON.parse(data.join("\n")));
      }
    };
  }
  function mount(doc,win) {
    var dialog=doc.getElementById("ndCompany");if(!dialog)return;
    var $=function(id){return doc.getElementById(id);},zh=function(){return doc.documentElement.dataset.lang==="zh";},tx=function(en,cn){return zh()?cn:en;};
    var state={ticker:"",cursor:null,packet:null,visible:[],pending:0,reordered:false,status:["Choose a company","选择一家公司"],mode:"idle"};
    var generation=0,requests=new Set(),groupRequests=new Map(),jobs=new Map(),stream=null,refreshing=false,dirty=false,streamFailures=0,streamRetryAt=0,disposed=false,lastTrigger=null;
    var rateLimitResumeAt=0;
    function node(tag,cls,value){var n=doc.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=String(value);return n;}
    function button(label,fn,cls){var n=node("button",cls||"nd-btn",label);n.type="button";n.addEventListener("click",fn);return n;}
    function at(value){var n=Date.parse(value);return Number.isFinite(n)?new Intl.DateTimeFormat(zh()?"zh-CN":"en-GB",{dateStyle:"medium",timeStyle:"short"}).format(n):tx("Time not supplied","未提供时间");}
    function later(key,fn,ms){cancel(key);jobs.set(key,win.setTimeout(function(){jobs.delete(key);fn();},ms));}
    function cancel(key){if(jobs.has(key))win.clearTimeout(jobs.get(key));jobs.delete(key);}
    function active(id){return id===generation&&dialog.open&&!disposed&&!doc.hidden;}
    function stopChannel(){cancel("renew");cancel("idle");if(stream){stream.abort();stream=null;}}
    function stop(){generation++;requests.forEach(function(c){c.abort();});requests.clear();groupRequests.forEach(function(c){c.abort();});groupRequests.clear();stopChannel();jobs.forEach(function(id){win.clearTimeout(id);});jobs.clear();refreshing=false;dirty=false;}
    function purge(){state.packet=null;state.visible=[];state.pending=0;state.reordered=false;$("ndCompanyRows").replaceChildren();$("ndCompanyFlow").replaceChildren();$("ndCompanyHealth").textContent="";$("ndCompanyMore").hidden=true;$("ndCompanyUpdates").hidden=true;}
    function abortGroups(card){card.querySelectorAll(".nd-company-group").forEach(function(details){var c=groupRequests.get(details);if(c)c.abort();groupRequests.delete(details);});}
    function status(mode,en,cn){state.mode=mode;state.status=[en,cn];$("ndCompanyStatus").dataset.state=mode;$("ndCompanyStatus").textContent=tx(en,cn);}
    function resume(){
      if(!dialog.open||disposed||doc.hidden||!state.ticker)return;
      var id=generation,remaining=Math.max(0,rateLimitResumeAt-Date.now());
      if(remaining){later("retry",function(){if(id===generation)resume();},remaining);return;}
      rateLimitResumeAt=0;refresh(true);
    }
    function errorState(error){
      stop();purge();
      var code=error&&error.status;rateLimitResumeAt=code===429?Date.now()+60000:0;$("ndCompanySignIn").hidden=code!==401;$("ndCompanyRetry").hidden=code===401||code===404;
      if(code===401)status("restricted","Sign in to open company news.","请登录以打开公司新闻。");
      else if(code===403)status("restricted","Company news requires an eligible account and source access.","公司新闻需要符合条件的账户与来源访问权限。");
      else if(code===404)status("unavailable","This ticker is outside the available company news universe.","此股票代码不在可用公司新闻范围内。");
      else if(code===429)status("degraded","Request limit reached. Retry in a minute.","已达到请求上限，请在一分钟后重试。");
      else status("unavailable","Company reporting is unavailable. The feed or its display permission could not be confirmed.","公司报道暂不可用，无法确认新闻源或其展示权限。");
      if(dialog.open&&!doc.hidden&&state.ticker&&code!==401&&code!==403&&code!==404){if(code===429)resume();else later("retry",function(){refresh(true);},30000);}
    }
    async function accessToken(signal){
      if(!win.MDXAuth||typeof win.MDXAuth.client!=="function"){var absent=new Error("auth");absent.status=401;throw absent;}
      var abort;
      var cancelled=new Promise(function(_,reject){abort=function(){reject(new Error("request cancelled"));};signal.addEventListener("abort",abort,{once:true});if(signal.aborted)abort();});
      try{
        var token=await Promise.race([(async function(){var sb=await win.MDXAuth.client();var result=await sb.auth.getSession();return result&&result.data&&result.data.session&&result.data.session.access_token;})(),cancelled]);
        if(!token){var missing=new Error("auth");missing.status=401;throw missing;}return token;
      }finally{signal.removeEventListener("abort",abort);}
    }
    async function request(path,controller,accept){
      var timeout=win.setTimeout(function(){controller.abort();},10000);requests.add(controller);
      try{
        var token=await accessToken(controller.signal);
        var response=await win.fetch(path,{credentials:"same-origin",cache:"no-store",signal:controller.signal,headers:{Accept:accept||"application/json",Authorization:"Bearer "+token}});
        if(!response.ok){var error=new Error("http");error.status=response.status;throw error;}
        if(accept==="text/event-stream")return response;
        var text=await response.text();if(text.length>2097152)throw new Error("response too large");return JSON.parse(text);
      }finally{win.clearTimeout(timeout);requests.delete(controller);}
    }
    function renderFlow(flow){
      var box=$("ndCompanyFlow");box.replaceChildren();
      if(!flow||flow.schema!=="ticker_news.flow.v1"||flow.state==="unavailable")return;
      var stats=node("div","nd-company-stats");
      [["reports_24h","Reports · 24h","报道 · 24小时"],["stories_24h","Story groups · 24h","事件组 · 24小时"],["reports_7d","Reports · 7d","报道 · 7天"]].forEach(function(item){var value=flow[item[0]];if(!Number.isSafeInteger(value)||value<0)return;var stat=node("div");stat.append(node("strong","",value.toLocaleString()),node("span","",tx(item[1],item[2])));stats.appendChild(stat);});
      box.appendChild(stats);
      var daily=flow.daily_counts_28d;
      if(Array.isArray(daily)&&daily.length===28&&daily.every(function(n){return Number.isSafeInteger(n)&&n>=0;})){
        var chart=node("div","nd-company-bars"),max=Math.max.apply(null,daily.concat([1]));chart.setAttribute("role","img");chart.setAttribute("aria-label",tx("Daily report counts, oldest to newest: ","每日报道数，由旧到新：")+daily.join(", "));
        daily.forEach(function(n,i){var bar=node("span");bar.style.height=Math.max(2,n/max*100)+"%";bar.title=tx("Day ","第 ")+(i+1)+": "+n;chart.appendChild(bar);});box.appendChild(chart);
        var range=flow.provenance&&flow.provenance.windows&&flow.provenance.windows.daily_28d;
        if(range&&/^\d{4}-\d{2}-\d{2}$/.test(range.start_date)&&/^\d{4}-\d{2}-\d{2}$/.test(range.end_date))box.appendChild(node("p","nd-note",tx("Daily reports · ","每日报道 · ")+range.start_date+" – "+range.end_date));
      }
      var comparison={busier:["Busier than the 28-day daily median","高于28天每日中位数"],typical:["Near the 28-day daily median","接近28天每日中位数"],quieter:["Quieter than the 28-day daily median","低于28天每日中位数"]};
      var note=flow.coverage==="partial"?tx("Partial feed coverage · comparisons withheld","新闻源覆盖不完整 · 暂不提供比较"):flow.state==="thin_history"?tx("Limited observed history · no activity comparison","已观察历史较短 · 暂不比较活跃度"):comparison[flow.comparison]?tx.apply(null,comparison[flow.comparison]):tx("Activity from accessible sources","可访问来源的新闻活跃度");
      box.appendChild(node("p","nd-note",note+" · "+tx("As of ","截至 ")+at(flow.as_of)));
      var basis=flow.provenance&&flow.provenance.time_basis_counts_24h;
      if(basis&&basis.received_at>0)box.appendChild(node("p","nd-note",basis.received_at+" "+tx("of the 24h reports use receipt time because publication time was not supplied.","条24小时内报道因未提供发布时间，采用收录时间。")));
    }
    function renderMember(row,parent){
      var card=node("div","nd-receipt"),url=safeURL(row.url),headline=node(url?"a":"span","",clean(row.title));
      if(url){headline.href=url;headline.target="_blank";headline.rel="noopener noreferrer";}card.appendChild(headline);
      card.appendChild(node("small","",clean(row.source)+" · "+at(row.published_at||row.received_at)));
      parent.appendChild(card);
    }
    async function members(row,details){
      if(!details.open||details.dataset.loaded)return;details.dataset.loaded="true";
      var body=details.querySelector(".nd-company-members"),id=generation,controller=new AbortController();groupRequests.set(details,controller);body.textContent=tx("Loading source reports…","正在载入来源报道…");
      try{
        var p=await request("/api/ticker-news/stories/"+encodeURIComponent(row.story_id),controller);
        if(!active(id)||!details.isConnected||groupRequests.get(details)!==controller)return;
        if(p.schema!=="ticker_news.story.v1"||p.story_id!==row.story_id||!Array.isArray(p.members)||p.members.length>500||!p.members.every(validRow))throw new Error("schema");
        body.replaceChildren();p.members.forEach(function(r){renderMember(r,body);});
        if(!p.members.length)body.textContent=tx("No accessible source reports remain in this group.","该事件组已无可访问的来源报道。");
        if(details.dataset.restoreFocusHref&&doc.activeElement===details.querySelector("summary")){var target=Array.from(body.querySelectorAll("a")).find(function(a){return a.href===details.dataset.restoreFocusHref;});if(target)target.focus({preventScroll:true});}delete details.dataset.restoreFocusHref;
      }catch(error){if(active(id)&&(error.status===401||error.status===403||details.isConnected&&groupRequests.get(details)===controller)){if(error.status===404){body.textContent=tx("This story group is no longer available.","此事件组已不可用。");refresh(false);}else errorState(error);}}
      finally{if(groupRequests.get(details)===controller)groupRequests.delete(details);}
    }
    function render(){
      $("ndCompanyStatus").textContent=tx.apply(null,state.status);
      $("ndCompanyLive").hidden=state.cursor===null;
      $("ndCompanyUpdates").hidden=!state.pending&&!state.reordered;$("ndCompanyUpdates").textContent=state.pending?state.pending+" "+tx("new story groups · Show latest","个新增事件组 · 显示最新"):tx("Reporting updated · Restore latest order","报道已更新 · 恢复最新排序");
      if(!state.packet)return;
      var list=$("ndCompanyRows"),scroll=list.scrollTop,previousFocus=doc.activeElement,focused=previousFocus&&previousFocus.closest("[data-company-story]"),focusId=focused&&focused.dataset.companyStory;
      var listTop=list.getBoundingClientRect().top,anchor=Array.from(list.children).find(function(n){return n.getBoundingClientRect().bottom>listTop;}),anchorId=anchor&&anchor.dataset.companyStory,anchorOffset=anchor?anchor.getBoundingClientRect().top-listTop:0;
      var nextById=new Map(state.visible.map(function(r){return[r.story_id,r];}));
      Array.from(list.children).forEach(function(n){if(!nextById.has(n.dataset.companyStory)){abortGroups(n);n.remove();}});
      state.visible.forEach(function(row){
        var old=Array.from(list.children).find(function(n){return n.dataset.companyStory===row.story_id;}),key=revision(row);
        if(old&&old.dataset.revision===key)return;
        var oldGroup=old&&old.querySelector(".nd-company-group"),keepGroupOpen=oldGroup&&oldGroup.open,groupFocus=oldGroup&&oldGroup.contains(previousFocus),memberHref=groupFocus&&previousFocus.tagName==="A"?previousFocus.href:"";
        var card=node("article","nd-company-row");card.dataset.companyStory=row.story_id;card.dataset.revision=key;
        var updated=Date.parse(row.updated_at),published=Date.parse(row.published_at),amended=Number.isFinite(updated)&&(!Number.isFinite(published)||updated>published);
        card.appendChild(node("p","nd-company-meta",clean(row.source)+" · "+(amended?tx("Updated ","更新 "):Number.isFinite(published)?tx("Published ","发布 "):tx("Received ","收录 "))+at(amended?row.updated_at:row.published_at||row.received_at)));
        var heading=node("h3"),url=safeURL(row.url),title=node(url?"a":"span","",clean(row.title));if(url){title.href=url;title.target="_blank";title.rel="noopener noreferrer";}heading.appendChild(title);card.appendChild(heading);
        if(row.teaser)card.appendChild(node("p","nd-company-teaser",clean(row.teaser)));
        if(row.item_count>1){var details=node("details","nd-company-group");details.append(node("summary","",row.item_count+" "+tx("reports in this story group","条同组报道")),node("div","nd-company-members"));details.addEventListener("toggle",function(){members(row,details);});details.open=!!keepGroupOpen;if(memberHref)details.dataset.restoreFocusHref=memberHref;card.appendChild(details);}
        if(old){abortGroups(old);old.replaceWith(card);}else list.appendChild(card);
        if(groupFocus&&details){details.querySelector("summary").focus({preventScroll:true});}
        if(details&&details.open)members(row,details);
      });
      // The displayed order follows the accepted snapshot, while unchanged DOM
      // nodes (including open source groups) survive transport heartbeats.
      state.visible.forEach(function(row,i){var n=Array.from(list.children).find(function(x){return x.dataset.companyStory===row.story_id;});if(n&&list.children[i]!==n)list.insertBefore(n,list.children[i]||null);});
      list.scrollTop=scroll;
      if(anchorId){var retainedAnchor=Array.from(list.children).find(function(n){return n.dataset.companyStory===anchorId;});if(retainedAnchor)list.scrollTop+=retainedAnchor.getBoundingClientRect().top-listTop-anchorOffset;}
      if(focusId&&doc.activeElement!==previousFocus&&!list.contains(doc.activeElement)){var focusedRow=Array.from(list.children).find(function(n){return n.dataset.companyStory===focusId;});var target=previousFocus.isConnected?previousFocus:focusedRow&&focusedRow.querySelector("a,summary");(target||list).focus({preventScroll:true});}
      $("ndCompanyMore").hidden=!state.packet.has_more;
      var health=state.packet.source_health||{},healthState=clean(health.state||state.packet.state);
      var healthLabels={live:["Source reporting active","来源报道活跃"],ok:["Source reporting available","来源报道可用"],catching_up:["Source catching up","来源正在追赶更新"],degraded:["Source coverage degraded","来源覆盖降级"],quiet:["No recent source events","近期无来源事件"],empty:["No accessible stories in this window","此时间范围内暂无可访问报道"]};
      $("ndCompanyHealth").textContent=state.ticker+" · "+(healthLabels[healthState]?tx.apply(null,healthLabels[healthState]):tx("Source state: ","来源状态：")+(healthState||tx("unknown","未知")))+" · "+tx("Grouping can include syndicated reports; it does not establish independent confirmation.","事件组可能包含转载报道，不代表已获得独立确认。");
      if(!state.visible.length)list.appendChild(node("p","nd-empty",tx("No accessible reporting in this window. Try another company or return to the latest feed.","此时间范围内暂无可访问报道，请尝试另一家公司或返回最新新闻流。")));
      renderFlow(state.cursor===null?state.packet.flow:null);
    }
    function accept(p,first){
      if(!validSnapshot(p,state.ticker))throw new Error("snapshot schema");
      var nextById=new Map(p.rows.map(function(r){return[r.story_id,r];}));state.packet=p;
      state.visible=first||state.cursor!==null?p.rows.slice():state.visible.filter(function(r){return nextById.has(r.story_id);}).map(function(r){return nextById.get(r.story_id);});
      var retained=new Set(state.visible.map(function(r){return r.story_id;}));
      state.pending=p.rows.length-state.visible.length;state.reordered=JSON.stringify(state.visible.map(function(r){return r.story_id;}))!==JSON.stringify(p.rows.filter(function(r){return retained.has(r.story_id);}).map(function(r){return r.story_id;}));render();
    }
    async function openStream(id){
      if(!active(id)||state.cursor!==null||!state.packet)return;
      if(!state.packet.rows.length||Date.now()<streamRetryAt){status("polling","Auto refresh · 10s","自动刷新 · 10秒");later("poll",function(){refresh(true);},10000);return;}
      stopChannel();var controller=new AbortController();stream=controller;
      var sequence=Math.max.apply(null,state.packet.rows.map(function(r){return r.sequence;}));
      status("connecting","Connecting to company changes","正在连接公司新闻更新");
      try{
        var response=await request("/api/ticker-news/"+encodeURIComponent(state.ticker)+"/stream?after_sequence="+sequence,controller,"text/event-stream");
        if(!active(id)||stream!==controller)return;
        if(!response.body||!response.body.getReader||response.headers&&!/text\/event-stream/i.test(response.headers.get("content-type")||""))throw new Error("stream unsupported");
        var reader=response.body.getReader(),decoder=new TextDecoder();
        var parse=streamParser(function(event,p){
          if(event==="restricted"){var denied=new Error("rights");denied.status=403;throw denied;}
          if(event==="unavailable")throw new Error("unavailable");
          if(!p||!Number.isSafeInteger(p.sequence)||p.sequence<0)throw new Error("change schema");
          if(p.sequence>sequence){sequence=p.sequence;dirty=true;if(!jobs.has("change"))later("change",function(){refresh(false);},1000);}
        });
        later("renew",function(){stopChannel();refresh(true);},45000);
        while(active(id)&&stream===controller){
          later("idle",function(){controller.abort();},15000);
          var chunk=await reader.read();cancel("idle");
          if(!active(id)||stream!==controller)return;
          if(chunk.done)throw new Error("stream ended");
          parse(decoder.decode(chunk.value,{stream:true}));streamFailures=0;status("connected","Company changes connected","公司新闻更新已连接");
        }
      }catch(error){
        if(!active(id)||stream!==controller)return;
        streamFailures++;if(streamFailures>=2)streamRetryAt=Date.now()+300000;
        errorState(error);
        if(![401,403,404,429].includes(error.status)){status("degraded","Connection interrupted · recovering reporting","连接已中断 · 正在恢复报道");later("retry",function(){refresh(true);},10000);}
      }
    }
    async function refresh(reconnect){
      if(!state.ticker||!dialog.open||disposed||doc.hidden)return;
      if(refreshing){dirty=true;return;}refreshing=true;dirty=false;rateLimitResumeAt=0;cancel("retry");cancel("poll");var id=generation,first=!state.packet;
      $("ndCompanyRetry").hidden=true;$("ndCompanySignIn").hidden=true;
      if(first)status("connecting","Loading company reporting…","正在载入公司报道…");
      try{
        var path="/api/ticker-news/"+encodeURIComponent(state.ticker)+"?limit=60"+(state.cursor!==null?"&cursor="+state.cursor:"");
        var p=await request(path,new AbortController());if(!active(id))return;
        accept(p,first);
        if(state.cursor!==null){status("paused","Earlier reporting · live paused","历史报道 · 实时更新已暂停");later("authorize",function(){refresh(false);},45000);}
        else if(reconnect||!stream)openStream(id);
      }catch(error){if(active(id))errorState(error);}
      finally{if(id===generation){refreshing=false;if(dirty&&active(id))later("change",function(){refresh(false);},1000);}}
    }
    function start(symbol,cursor){stop();purge();rateLimitResumeAt=0;state.ticker=symbol;state.cursor=cursor===undefined?null:cursor;streamFailures=0;streamRetryAt=0;$("ndCompanyTicker").value=symbol;refresh(true);}
    function open(symbol,trigger){
      lastTrigger=trigger||doc.activeElement;
      var parent=lastTrigger&&lastTrigger.closest("dialog");if(parent&&parent!==dialog&&parent.open)parent.close();
      if(!dialog.open){if(dialog.showModal)dialog.showModal();else dialog.setAttribute("open","");}
      var normalized=ticker(symbol);if(normalized)start(normalized);else if(!state.ticker)status("idle","Choose a company to explore its reporting and news activity.","选择一家公司，浏览报道与新闻活跃度。");
      $("ndCompanyTicker").focus();
    }
    function close(){stop();purge();rateLimitResumeAt=0;state.ticker="";state.cursor=null;$("ndCompanyTicker").value="";if(lastTrigger&&lastTrigger.isConnected)lastTrigger.focus();}
    doc.addEventListener("click",function(event){var trigger=event.target.closest&&event.target.closest("[data-company-news]");if(trigger)open(trigger.dataset.companyNews,trigger);});
    $("ndCompanyForm").addEventListener("submit",function(event){event.preventDefault();var symbol=ticker($("ndCompanyTicker").value);if(!symbol){$("ndCompanyTicker").setCustomValidity(tx("Enter a supported ticker, such as NVDA.","请输入支持的股票代码，例如NVDA。"));$("ndCompanyTicker").reportValidity();return;}start(symbol);});
    $("ndCompanyTicker").addEventListener("input",function(){this.setCustomValidity("");});
    $("ndCompanyRetry").addEventListener("click",function(){refresh(true);});
    $("ndCompanyMore").addEventListener("click",function(){if(state.packet&&state.packet.has_more)start(state.ticker,state.packet.next_cursor);});
    $("ndCompanyLive").addEventListener("click",function(){start(state.ticker);});
    $("ndCompanyUpdates").addEventListener("click",function(){if(!state.packet)return;state.visible=state.packet.rows.slice();state.pending=0;state.reordered=false;render();$("ndCompanyRows").scrollTop=0;});
    dialog.addEventListener("close",close);
    doc.addEventListener("langchange",function(){if(dialog.open){$("ndCompanyRows").querySelectorAll("[data-revision]").forEach(function(n){n.dataset.revision="";});render();}});
    doc.addEventListener("visibilitychange",function(){if(doc.hidden){stop();purge();status("paused","Paused in background","后台已暂停");}else if(dialog.open&&state.ticker)resume();});
    win.addEventListener("pagehide",function(){disposed=true;stop();purge();});
    win.addEventListener("mdx-auth",function(event){
      var detail=event.detail||{};if(detail.event==="PREFS_SAVED")return;
      if(!dialog.open||!state.ticker)return;
      stop();purge();rateLimitResumeAt=0;
      if(!detail.user){$("ndCompanySignIn").hidden=false;status("restricted","Sign in to open company news.","请登录以打开公司新闻。");}
      else later("auth",function(){refresh(true);},0);
    });
    win.addEventListener("pageshow",function(event){if(event.persisted){disposed=false;if(dialog.open&&state.ticker)resume();}});
    return {open:open,accept:accept,getState:function(){return {ticker:state.ticker,cursor:state.cursor,mode:state.mode,pending:state.pending,ids:state.visible.map(function(r){return r.story_id;})};}};
  }
  return {ticker:ticker,safeURL:safeURL,validSnapshot:validSnapshot,streamParser:streamParser,mount:mount};
});
