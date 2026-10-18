/* News Desk: private live delivery, read-stable presentation and local view preferences.
 * Source and story identity remain with the existing news owners. No vendor calls.
 */
(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root.document) api.mount(root.document, root);
})(typeof window !== "undefined" ? window : globalThis, function () {
  "use strict";
  var CATEGORY = {
    all:["All coverage","全部报道"], markets:["Markets","市场"], economy:["Economy","经济"],
    central_banks:["Central banks","央行"], companies:["Companies","公司"], geopolitics:["Geopolitics","地缘政治"],
    energy:["Energy & materials","能源与原料"], technology:["Technology","科技"]
  };
  var REGIONS = {
    americas:/\b(united states|u\.?s\.?|america|canada|brazil|mexico|argentina|chile|colombia|washington|federal reserve)\b|美国|加拿大|巴西|墨西哥|美联储/i,
    europe:/\b(europe|european|eurozone|ecb|germany|france|britain|british|uk|united kingdom|russia|ukraine|moscow|kyiv|london|turkey|poland)\b|欧洲|英国|法国|德国|俄罗斯|乌克兰|欧央行/i,
    asia:/\b(china|chinese|beijing|japan|japanese|tokyo|india|indian|korea|taiwan|australia|singapore|indonesia|vietnam|philippines|hong kong|pakistan)\b|中国|日本|印度|台湾|韩国|澳大利亚|香港|新加坡/i,
    middle_east:/\b(iran|iranian|israel|israeli|gaza|lebanon|saudi|iraq|hormuz|qatar|yemen|syria|middle east|united arab emirates)\b|伊朗|以色列|加沙|黎巴嫩|沙特|伊拉克|中东|霍尔木兹/i,
    africa:/\b(africa|egypt|nigeria|kenya|sudan|ethiopia|congo|morocco|algeria)\b|非洲|埃及|尼日利亚|肯尼亚|苏丹/i
  };
  var DEFAULT_FILTERS = {view:"latest",category:"all",time:"168",region:"all",query:"",kind:"all",source:"",unread:false,social:false,saved:false};
  function text(v) { return typeof v === "string" ? v.trim() : ""; }
  function strip(v) { return text(v).replace(/<[^>]*>/g," ").replace(/\s+/g," ").trim(); }
  function stamp(v) { var n=Date.parse(text(v)); return Number.isFinite(n) ? n : null; }
  function safeURL(v) {
    try { var u=new URL(text(v)); return (u.protocol==="https:"||u.protocol==="http:")&&!u.username&&!u.password ? u.href : ""; }
    catch (_) { return ""; }
  }
  function domain(v) { try{return new URL(safeURL(v)).hostname.replace(/^www\./,"").toLowerCase();}catch(_){return ""; } }
  function canonicalURL(v) {
    try {var u=new URL(safeURL(v));u.hash="";["utm_source","utm_medium","utm_campaign","utm_content","utm_term","ref"].forEach(function(k){u.searchParams.delete(k);});return u.href.replace(/\/$/,"");}catch(_){return "";}
  }
  function kindOf(r,host,name) {
    if (/truthsocial|twitter\.com|x\.com|t\.me/.test(host)||/truth social|twitter|social statement/i.test(name)||r.source_type==="social") return "social";
    if (/\.gov$|\.gov\.uk$/.test(host)||/^(federalreserve\.gov|ecb\.europa\.eu|bankofengland\.co\.uk|imf\.org|bis\.org|boj\.or\.jp|opec\.org)$/.test(host)||r.source_type==="official") return "official";
    return "reporting";
  }
  function categoryOf(r,title) {
    var direct={economy:"economy",central_banks:"central_banks",markets:"markets",macro_print:"economy",macro:"economy",fed:"central_banks",monetary:"central_banks",inflation:"economy",labor:"economy",growth:"economy",fiscal:"economy",geopolitical:"geopolitics",geopolitics:"geopolitics",world:"geopolitics",company_news:"companies",earnings:"companies",companies:"companies",policy:"geopolitics",technology:"technology",energy:"energy"};
    if (/\b(oil|crude|opec|lng|natural gas|copper|gold|iron ore|energy)\b|原油|石油|天然气|黄金/i.test(title)) return "energy";
    if (/\b(artificial intelligence|semiconductor|chipmaker|cybersecurity|nvidia|openai)\b|人工智能|半导体|英伟达/i.test(title)) return "technology";
    if (/\b(federal reserve|fomc|ecb|bank of japan|bank of england|central bank|fed officials|powell)\b|美联储|央行/i.test(title)) return "central_banks";
    if (/\b(ceasefire|missile|airstrike|war|sanctions|invasion|military|nuclear talks|tariff)\b|停火|战争|导弹|制裁|关税/i.test(title)) return "geopolitics";
    return direct[r.category]||direct[r.event_class]||direct[r.class]||direct[r.theme]||direct[r.lane]||"markets";
  }
  function normalize(r,origin) {
    if (!r||typeof r!=="object"||Array.isArray(r)) return null;
    var headline=strip(r.headline||r.title||r.en);
    if (!headline||/^(\(?truth social post\)?|RT:?\s*https?:\/\/\S+)$/i.test(headline)) return null;
    var ev=Array.isArray(r.evidence)?r.evidence.filter(function(e){return e&&typeof e==="object";}).slice(0,60):[];
    var primary=ev[0]||{};
    var url=safeURL(r.url||primary.url), host=domain(url)||text(r.domain);
    var name=strip(r.source_name||r.source||primary.name||host)||"Source unavailable";
    var published=text(r.published_at||r.ts||primary.published_at);
    var sourceUpdated=text(r.source_updated_at),indexed=text(r.provider_indexed_at||r.seendate);
    var received=text(r.received_at||r.first_seen);
    var updated=text(r.updated_at||published);
    var id=text(r.id||r._id)||canonicalURL(url)||"headline:"+headline.toLowerCase();
    var tickers=(Array.isArray(r.tickers)?r.tickers:[]).map(function(t){return typeof t==="string"?t.replace(/^\$/,"").toUpperCase():"";}).filter(function(t){return /^[A-Z][A-Z0-9.\-]{0,11}$/.test(t);}).slice(0,20);
    var titleZh=strip(r.headline_zh||r.title_zh||r.zh);
    var allText=[headline,titleZh,strip(r.brief||r.summary),tickers.join(" ")].join(" ");
    var regions=Object.keys(REGIONS).filter(function(k){return REGIONS[k].test(allText);});
    var category=categoryOf(r,allText),kind=kindOf(r,host,name);
    var score=Number(r.rank_score||r.salience||0);
    var clock=stamp(sourceUpdated)!==null&&(stamp(published)===null||stamp(sourceUpdated)>stamp(published))?"updated":stamp(published)!==null?"published":stamp(indexed)!==null?"indexed":"received";
    var clockAt=clock==="updated"?sourceUpdated:clock==="published"?published:clock==="indexed"?indexed:received;
    return {
      id:id,origin:origin||"snapshot",title:headline,titleZh:titleZh,
      url:url,host:host,source:name,kind:kind,category:category,regions:regions,tickers:tickers,
      publishedAt:published,published:stamp(published),receivedAt:received,received:stamp(received),
      updatedAt:updated,sourceUpdatedAt:sourceUpdated,indexedAt:indexed,clock:clock,clockAt:clockAt,sortAt:stamp(clockAt)||0,
      brief:strip(r.brief||r.summary),briefZh:strip(r.brief_zh||r.summary_zh),
      why:strip(r.why_it_matters_en||r.why_it_matters),whyZh:strip(r.why_it_matters_zh),
      important:r.stage==="high_impact"||score>=65,score:Number.isFinite(score)?score:0,
      evidence:ev.length?ev:[{url:url,name:name,headline:headline,published_at:published}],
      status:text(r.status||r.change_kind||r.kind),context:r.context&&typeof r.context==="object"?r.context:{},
      timeline:Array.isArray(r.timeline)?r.timeline:[],raw:r
    };
  }
  function combine(live,seed) {
    var rows=[],ids=new Set(),urls=new Set(),titles=new Set();
    [live,seed].forEach(function(group,index){(Array.isArray(group)?group:[]).forEach(function(raw){
      var r=raw&&raw.sortAt!==undefined?raw:normalize(raw,index===0?"desk":"edition");if(!r)return;
      var url=canonicalURL(r.url),title=r.title.toLowerCase();
      if(ids.has(r.id)||(url&&urls.has(url))||titles.has(title))return;
      ids.add(r.id);if(url)urls.add(url);titles.add(title);rows.push(r);
    });});
    return rows.slice(0,1000);
  }
  function tokens(query) {
    var found=text(query).match(/-?(?:[\w]+:)?(?:"[^"]*"|\S+)/g)||[];
    return found.slice(0,40).map(function(raw){
      if(raw==="OR"||raw==="|")return {op:"or"};
      var exclude=raw[0]==="-";if(exclude)raw=raw.slice(1);
      var m=raw.match(/^(ticker|source|topic|region):(.*)$/i);
      return {exclude:exclude,field:m?m[1].toLowerCase():"text",value:(m?m[2]:raw).replace(/^"|"$/g,"").toLowerCase()};
    }).filter(function(t){return t.op||t.value;});
  }
  function matchesTerms(r,ts) {
    var hay=[r.title,r.titleZh,r.brief,r.briefZh,r.source,r.host,r.tickers.join(" "),r.category].join(" ").toLowerCase();
    function match(t){
      var yes=t.field==="ticker"?r.tickers.some(function(s){return s.toLowerCase()===t.value;}):
        t.field==="source"?(r.source+" "+r.host).toLowerCase().includes(t.value):
        t.field==="topic"?(r.category+" "+(CATEGORY[r.category]||[]).join(" ")).toLowerCase().includes(t.value):
        t.field==="region"?r.regions.some(function(s){return s.includes(t.value);}):hay.includes(t.value);
      return yes;
    }
    if(ts.some(function(t){return t.exclude&&match(t);}))return false;
    var groups=[[]];ts.forEach(function(t){if(t.op){if(groups[groups.length-1].length)groups.push([]);}else if(!t.exclude)groups[groups.length-1].push(t);});
    groups=groups.filter(function(g){return g.length;});return !groups.length||groups.some(function(g){return g.every(match);});
  }
  function filterRows(rows,f,preferences,now) {
    var p=preferences||{},read=new Set(p.read||[]),saved=new Set(p.saved||[]),following=p.following||[];
    var ts=tokens(f.query),ms=now===undefined?Date.now():now;
    return rows.filter(function(r){
      if(!f.social&&r.kind==="social"&&f.kind!=="social")return false;
      if(f.kind!=="all"&&r.kind!==f.kind)return false;
      if(f.category!=="all"&&r.category!==f.category)return false;
      if(f.region!=="all"&&!r.regions.includes(f.region))return false;
      if(f.source&&!(r.source+" "+r.host).toLowerCase().includes(f.source.toLowerCase()))return false;
      if(f.unread&&read.has(r.id))return false;
      if(f.saved&&!saved.has(r.id))return false;
      if(r.sortAt>ms+300000)return false;
      if(f.time!=="all"&&(r.sortAt===0||ms-r.sortAt>Number(f.time)*3600000))return false;
      if(f.view==="important"&&!r.important)return false;
      if(f.view==="world"&&!["economy","central_banks","geopolitics","energy"].includes(r.category))return false;
      if(f.view==="following"&&!following.some(function(term){return matchesTerms(r,tokens(term));}))return false;
      return matchesTerms(r,ts);
    }).sort(function(a,b){return (f.view==="important"?(b.score-a.score):0)||(b.sortAt-a.sortAt)||a.id.localeCompare(b.id);});
  }
  function fingerprint(r) {return JSON.stringify([r.title,r.titleZh,r.brief,r.briefZh,r.why,r.whyZh,r.status,r.category,r.source,r.kind,r.publishedAt,r.sourceUpdatedAt,r.important,r.score,r.evidence,r.tickers,r.timeline,r.raw.revision_history,r.raw.revision,r.raw.llm]);}
  function difference(before,after) {
    var old=new Map(before.map(function(r){return[r.id,fingerprint(r)];})),next=new Set(after.map(function(r){return r.id;}));
    return after.reduce(function(n,r){return n+(old.get(r.id)!==fingerprint(r)?1:0);},0)+before.filter(function(r){return !next.has(r.id);}).length;
  }
  function age(iso,now,zh) {
    var n=stamp(iso);if(n===null)return zh?"时间未知":"Time unknown";
    var delta=(now===undefined?Date.now():now)-n;
    if(delta < -300000)return zh?"时间超前":"Future timestamp";
    var s=Math.max(0,delta)/1000;if(s<60)return zh?"刚刚":"just now";
    if(s<3600)return Math.floor(s/60)+(zh?"分钟前":"m ago");
    if(s<86400)return Math.floor(s/3600)+(zh?"小时前":"h ago");
    return Math.floor(s/86400)+(zh?"天前":"d ago");
  }
  function validSnapshot(p) {var seen=new Set();return p&&p.schema==="intelligence.desk/v1"&&Array.isArray(p.stories)&&p.stories.length<=1000&&p.stories.every(function(r){return r&&typeof r==="object"&&!Array.isArray(r)&&typeof r.id==="string"&&r.id.trim()&&!seen.has(r.id)&&(seen.add(r.id),true);});}
  function mount(doc,win) {
    var root=doc.getElementById("newsDesk");if(!root)return;
    var $=function(id){return doc.getElementById(id);};
    var zh=function(){return doc.documentElement.getAttribute("data-lang")==="zh";};
    var tx=function(en,cn){return zh()?(cn||en):en;};
    var prefs={saved:[],read:[],following:[],views:[],density:"compact"},seed={},filters=Object.assign({},DEFAULT_FILTERS);
    try {var stored=JSON.parse(win.localStorage.getItem("mm.newsDesk.preferences.v1")||"{}");["saved","read","following","views"].forEach(function(k){if(Array.isArray(stored[k]))prefs[k]=stored[k].slice(0,k==="views"?12:500);});if(stored.density==="reading")prefs.density="reading";}catch(_){}
    try{seed=JSON.parse($("ndSeed").textContent||"{}");}catch(_){}
    ["saved","read","following"].forEach(function(k){prefs[k]=prefs[k].filter(function(v){return typeof v==="string"&&v.length<=300;});});
    var deskAliases=new Set();
    function combinedRows(rows){return combine(rows,(seed.stories||[]).filter(function(raw){var r=normalize(raw,"edition");return r&&!deskAliases.has(r.id)&&!deskAliases.has(canonicalURL(r.url))&&!deskAliases.has(r.title.toLowerCase());}));}
    var latest=[],visible=combine([],seed.stories),selected=null,shown=[],limit=60,pending=0,lastFocus=null,detailTab="brief",requestedStoryId=null;
    try{if(win.location.hash.startsWith("#story="))requestedStoryId=decodeURIComponent(win.location.hash.slice(7));}catch(_){}
    root.dataset.density=prefs.density;$("ndDensity").setAttribute("aria-pressed",String(prefs.density==="reading"));
    var liveReady=false,health={},sourceHealth=[],stream=null,timer=0,inflight=false,disposed=false,authPaused=false,mode="connecting",lastTransportAt=0,failures=0,generation=0,handshake=0,streamAvailable=true,streamFailures=0,streamRetryAt=0;
    function persist(){try{win.localStorage.setItem("mm.newsDesk.preferences.v1",JSON.stringify(prefs));}catch(_){announce(tx("This browser could not save your preferences.","此浏览器无法保存偏好设置。"));}}
    function el(tag,cls,value){var n=doc.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=String(value);return n;}
    function button(label,handler,cls){var n=el("button",cls||"nd-btn",label);n.type="button";n.addEventListener("click",handler);return n;}
    function announce(v){$("ndAnnounce").textContent=v;}
    function link(label,url,cls){var a=el("a",cls,label);a.href=url;if(/^https?:/.test(url)){a.target="_blank";a.rel="noopener noreferrer";}return a;}
    function title(r){return zh()&&r.titleZh?r.titleZh:r.title;}
    function clockLabel(r){return r.clock==="updated"?tx("Source updated ","来源更新 "):r.clock==="indexed"?tx("Indexed ","索引收录 "):r.clock==="received"?tx("First seen ","首次收录 "):tx("Published ","发布 ");}
    function articleLanguage(node,r,hasTranslation){node.lang=zh()&&hasTranslation?"zh":(/^[a-z]{2,3}(?:-[a-z]{2})?$/i.test(r.raw.language||"")?r.raw.language:"en");return node;}
    function localTime(iso){var n=stamp(iso);return n===null?tx("Unknown","未知"):new Intl.DateTimeFormat(zh()?"zh-CN":"en-GB",{hour:"2-digit",minute:"2-digit",hour12:false}).format(n);}
    function fullTime(iso){var n=stamp(iso);return n===null?tx("Not supplied","未提供"):new Intl.DateTimeFormat(zh()?"zh-CN":"en-GB",{dateStyle:"medium",timeStyle:"short"}).format(n);}
    function saveFiltersToURL(){
      var url=new URL(win.location.href);["view","topic","q","region","window"].forEach(function(k){url.searchParams.delete(k);});
      if(filters.view!=="latest")url.searchParams.set("view",filters.view);
      if(filters.category!=="all")url.searchParams.set("topic",filters.category);
      if(filters.query)url.searchParams.set("q",filters.query);
      if(filters.region!=="all")url.searchParams.set("region",filters.region);
      if(filters.time!=="168")url.searchParams.set("window",filters.time);
      win.history.replaceState(null,"",url.pathname+url.search+url.hash);
    }
    function readURL(){
      var p=new URL(win.location.href).searchParams;
      if(["latest","important","following","world"].includes(p.get("view")))filters.view=p.get("view");
      if(CATEGORY[p.get("topic")])filters.category=p.get("topic");
      if(REGIONS[p.get("region")])filters.region=p.get("region");
      if(["24","72","168","all"].includes(p.get("window")))filters.time=p.get("window");
      filters.query=(p.get("q")||"").slice(0,300);
    }
    function syncControls(){
      $("ndSearch").value=filters.query;$("ndTime").value=filters.time;$("ndRegion").value=filters.region;
      $("ndCategorySelect").value=filters.category;$("ndSourceKind").value=filters.kind;$("ndSourceSearch").value=filters.source;
      $("ndUnread").checked=filters.unread;$("ndIncludeSocial").checked=filters.social;$("ndFollowInput").value=prefs.following.join(", ");
      doc.querySelectorAll("[data-category]").forEach(function(b){b.setAttribute("aria-pressed",String(b.dataset.category===filters.category));});
      doc.querySelectorAll("[data-view]").forEach(function(b){var active=b.dataset.view===filters.view;b.setAttribute("aria-selected",String(active));b.tabIndex=active?0:-1;if(active)$("ndFeedPanel").setAttribute("aria-labelledby",b.id);});
      $("ndSavedStories").setAttribute("aria-pressed",String(filters.saved));$("ndFollowBar").hidden=filters.view!=="following";
      var n=[filters.category!=="all",filters.kind!=="all",!!filters.source,filters.unread,filters.social].filter(Boolean).length;
      $("ndFilterCount").textContent=n?"("+n+")":"";
      $("ndReset").hidden=Object.keys(DEFAULT_FILTERS).every(function(k){return filters[k]===DEFAULT_FILTERS[k];});
    }
    function freshness(){
      var ms=Date.now(),pubs=latest.map(function(r){return r.published;}).filter(function(t){return t!==null&&t<=ms+300000;});
      if(!pubs.length)pubs=visible.map(function(r){return r.published;}).filter(function(t){return t!==null&&t<=ms+300000;});
      var newest=pubs.length?new Date(Math.max.apply(null,pubs)).toISOString():"";
      $("ndFreshness").textContent=newest?tx("Latest publication ","最新发布 ")+age(newest,ms,zh()):tx("Publication time unavailable","发布时间未提供");
      if(mode==="connected"&&lastTransportAt&&ms-lastTransportAt>45000){closeStream();setConnection("degraded",tx("Reconnecting","正在重连"));banner(tx("The connection stopped responding. Recovering the latest available reporting.","连接已停止响应，正在恢复最新可用报道。"),false,true);schedule(0);}
    }
    function render(){
      var panel=$("ndFeedPanel"),oldScroll=panel.scrollTop,active=doc.activeElement,focused=panel.contains(active),focusRow=focused&&active.closest(".nd-row"),focusId=focusRow&&focusRow.dataset.id;
      var panelTop=panel.getBoundingClientRect().top,anchor=Array.from($("ndFeed").children).find(function(n){return n.getBoundingClientRect().bottom>panelTop;}),anchorId=anchor&&anchor.dataset.id,anchorOffset=anchor?anchor.getBoundingClientRect().top-panelTop:0;
      shown=filterRows(visible,filters,prefs,Date.now());var rows=shown.slice(0,limit),fragment=doc.createDocumentFragment();
      rows.forEach(function(r){
        var row=el("li","nd-row");row.dataset.id=r.id;row.dataset.selected=String(selected===r.id);row.dataset.read=String(prefs.read.includes(r.id));
        var gutter=el("div","nd-row-time"),tm=el("time","",localTime(r.clockAt));
        if(r.clockAt)tm.dateTime=r.clockAt;
        tm.title=clockLabel(r)+fullTime(r.clockAt);tm.setAttribute("aria-label",tm.title);
        gutter.appendChild(tm);
        if(r.clock!=="published")gutter.appendChild(el("span","nd-clock-kind",r.clock==="updated"?tx("updated","更新"):r.clock==="indexed"?tx("indexed","索引"):tx("seen","收录")));
        var days=r.sortAt?Math.floor((Date.now()-r.sortAt)/86400000):0;
        if(days>=1)gutter.appendChild(el("span","",days+tx("d ago","天前")));
        if(r.important)gutter.appendChild(el("span","nd-priority",tx("PRIORITY","重点")));
        var body=el("div","nd-row-body"),b=button(title(r),function(){openStory(r.id,b);},"nd-title");b.setAttribute("aria-controls","ndDetail");body.appendChild(articleLanguage(b,r,!!r.titleZh));
        if((r.brief||r.briefZh)&&r.brief!==r.title)body.appendChild(articleLanguage(el("p","nd-row-summary",zh()&&r.briefZh?r.briefZh:r.brief),r,!!r.briefZh));
        var meta=el("div","nd-row-meta");
        meta.appendChild(el("span","nd-source",r.source));meta.appendChild(el("span","nd-dot","·"));meta.appendChild(el("span","",tx.apply(null,CATEGORY[r.category])));
        if(r.kind==="social")meta.appendChild(el("span","nd-row-tag",tx("Statement","声明")));
        if(r.kind==="official")meta.appendChild(el("span","",tx("Official","官方")));
        if(/correct|retract|delet|withdraw|amend/i.test(r.status))meta.appendChild(el("span","nd-row-tag",tx("Updated","已更新")));
        r.tickers.slice(0,2).forEach(function(t){meta.appendChild(el("span","nd-ticker",t));});body.appendChild(meta);row.append(gutter,body);fragment.appendChild(row);
      });
      $("ndFeed").replaceChildren(fragment);$("ndEmpty").hidden=shown.length>0;$("ndMore").hidden=shown.length<=limit;
      $("ndResultCount").textContent=shown.length+" "+tx("stories","条报道")+(filters.saved?" · "+tx("Saved","已收藏"):"");
      if(!shown.length){
        $("ndEmptyTitle").textContent=filters.view==="following"&&!prefs.following.length?tx("Build your own news feed","建立你的专属新闻流"):tx("No stories match this view","暂无匹配报道");
        $("ndEmptyWhy").textContent=filters.view==="following"&&!prefs.following.length?tx("Add company tickers or topics above. New matching reporting will appear here.","在上方添加股票代码或主题，匹配的新报道会在此出现。"):filters.saved?tx("Save a story from its brief to keep its place here. Saved references stay on this browser.","从报道简报中收藏内容，即可在此保留位置。收藏记录仅保存在此浏览器。"):tx("Try a wider time window, another source, or fewer filters. Coverage reflects the reporting currently available to this desk.","请扩大时间范围、更换来源或减少筛选。覆盖范围取决于新闻台当前可用的报道。");
      }
      panel.scrollTop=oldScroll;
      var restoredAnchor=Array.from($("ndFeed").children).find(function(n){return n.dataset.id===anchorId;});
      if(restoredAnchor)panel.scrollTop+=restoredAnchor.getBoundingClientRect().top-panelTop-anchorOffset;
      if(focused){var restoredRow=Array.from($("ndFeed").children).find(function(n){return n.dataset.id===focusId;}),target=restoredRow&&restoredRow.querySelector("button")||panel;target.focus({preventScroll:true});}
      syncControls();freshness();
    }
    function applyLatest(resetScroll){
      visible=latest.length||liveReady?combinedRows(latest):visible;pending=0;$("ndUpdates").hidden=true;render();
      if(resetScroll)$("ndFeedPanel").scrollTop=0;
    }
    function section(parent,heading,body){
      if(!body)return;var s=el("section","nd-section");s.append(el("h3","",heading),el("p","",body));parent.appendChild(s);
    }
    function evidence(parent,r){
      var sec=el("section","nd-section");sec.appendChild(el("h3","",tx("Source evidence","来源依据")));
      r.evidence.forEach(function(e){
        var box=el("div","nd-receipt"),u=safeURL(e.url),name=strip(e.name)||domain(u)||tx("Source not supplied","未提供来源");
        if(u)box.appendChild(link(strip(e.headline)||name,u));else box.appendChild(el("p","",strip(e.headline)||name));
        box.appendChild(el("small","",name+" · "+fullTime(e.published_at)));sec.appendChild(box);
      });
      sec.appendChild(el("p","nd-note",tx("Several outlets may carry the same original report. Source count does not establish independent confirmation.","多个媒体可能转载同一原始报道。来源数量不等于独立核实。")));
      parent.appendChild(sec);
    }
    function renderDetail(changeNotice){
      var r=latest.find(function(x){return x.id===selected;})||visible.find(function(x){return x.id===selected;});if(!r)return;
      var body=$("ndDetailBody"),scroll=body.scrollTop,fragment=doc.createDocumentFragment(),hadFocus=body.contains(doc.activeElement),focusAction=hadFocus?doc.activeElement.dataset.action:null;
      var k=el("div","nd-detail-kicker",tx.apply(null,CATEGORY[r.category])+" · "+tx(r.kind==="official"?"Official source":r.kind==="social"?"Social statement":"News reporting",r.kind==="official"?"官方来源":r.kind==="social"?"社交声明":"新闻报道"));
      var h=articleLanguage(el("h2","",title(r)),r,!!r.titleZh);h.id="ndStoryTitle";fragment.append(k,h);
      if(changeNotice)fragment.appendChild(el("div","nd-change-note",changeNotice));
      fragment.appendChild(el("div","nd-detail-sub",r.source+" · "+clockLabel(r)+fullTime(r.clockAt)));
      var actions=el("div","nd-detail-actions");
      if(r.url)actions.appendChild(link(tx("Read original ↗","阅读原文 ↗"),r.url,"nd-btn"));
      actions.appendChild(button(prefs.saved.includes(r.id)?tx("Saved","已收藏"):tx("Save story","收藏报道"),function(){toggleSaved(r.id);}));
      actions.appendChild(button(tx("Copy link","复制链接"),async function(){try{var u=new URL(win.location.href);u.hash="story="+encodeURIComponent(r.id);await win.navigator.clipboard.writeText(u.href);announce(tx("Story link copied","已复制报道链接"));}catch(_){announce(tx("Copy the address from your browser to share this view.","复制浏览器地址以分享此视图。"));}},"nd-btn nd-btn-quiet"));
      Array.from(actions.children).forEach(function(n,i){n.dataset.action="detail-action-"+i;});
      fragment.appendChild(actions);
      var tabs=el("div","nd-detail-tabs");tabs.setAttribute("role","tablist");tabs.setAttribute("aria-label",tx("Story sections","报道分区"));
      [["brief","Brief","简报"],["evidence","Sources","来源"],["timeline","Timeline","时间线"]].forEach(function(t){
        var b=button(tx(t[1],t[2]),function(){detailTab=t[0];renderDetail();});b.dataset.action="detail-tab-"+t[0];b.id="ndStoryTab-"+t[0];b.setAttribute("role","tab");b.tabIndex=detailTab===t[0]?0:-1;b.setAttribute("aria-selected",String(detailTab===t[0]));b.setAttribute("aria-controls","ndStorySection");tabs.appendChild(b);
      });fragment.appendChild(tabs);
      tabs.addEventListener("keydown",function(e){
        if(!["ArrowLeft","ArrowRight","Home","End"].includes(e.key))return;
        var keys=["brief","evidence","timeline"],index=keys.indexOf(detailTab);
        e.preventDefault();detailTab=e.key==="Home"?keys[0]:e.key==="End"?keys[2]:keys[(index+(e.key==="ArrowRight"?1:2))%3];
        renderDetail();$("ndStoryTab-"+detailTab).focus();
      });
      var content=el("div","");content.id="ndStorySection";content.setAttribute("role","tabpanel");content.setAttribute("aria-labelledby","ndStoryTab-"+detailTab);
      if(detailTab==="brief"){
        var summary=zh()&&r.briefZh?r.briefZh:r.brief;
        section(content,tx("The reporting","报道内容"),summary&&summary!==title(r)?summary:tx("Read the original report for the full account. A separate summary is not available for this story.","请阅读原文了解完整内容。此报道暂无独立摘要。"));
        if(summary&&summary!==title(r))articleLanguage(content.querySelector(".nd-section p"),r,!!r.briefZh);
        section(content,tx("Desk context","新闻台解读"),zh()&&r.whyZh?r.whyZh:r.why);
        if(r.why)content.appendChild(el("p","nd-note",tx("Context is analysis. Check the original reporting and the source dates before drawing a conclusion.","背景解读属于分析。作出判断前，请核查原始报道与来源日期。")));
        if(r.tickers.length){
          var s=el("section","nd-section");s.appendChild(el("h3","",tx("Mentioned companies","提及公司")));var tags=el("div","nd-tags");
          r.tickers.forEach(function(t){tags.appendChild(link(t,"stock.html#"+encodeURIComponent(t)));var company=button(tx("News for ","公司新闻：")+t,function(){},"nd-btn");company.dataset.companyNews=t;tags.appendChild(company);});s.appendChild(tags);content.appendChild(s);
          content.appendChild(button(tx("Follow these companies","关注这些公司"),function(){r.tickers.forEach(function(t){var term="ticker:"+t;if(!prefs.following.includes(term))prefs.following.push(term);});prefs.following=prefs.following.slice(0,40);persist();announce(tx("Companies added to Following","已将公司添加到关注"));},"nd-btn"));
        }
        if(r.kind==="social")content.appendChild(el("p","nd-note",tx("This is a statement attributed to its author. A direct quote verifies what was said, not whether the claim is true.","此内容为归属于发布者的声明。直接引语证明说过什么，并不证明其主张属实。")));
        var stop=new Set(["about","after","before","their","there","these","which","while","would","could","says","said","with","from","that","this","have","will","into","over","more","than","amid","report"]);
        var terms=new Set((r.title.toLowerCase().match(/[a-z]{4,}/g)||[]).filter(function(w){return !stop.has(w);}));
        var related=combinedRows(latest).filter(function(other){
          if(other.id===r.id||other.kind==="social"&&!filters.social||Math.abs(other.sortAt-r.sortAt)>72*3600000)return false;
          return other.tickers.some(function(t){return r.tickers.includes(t);})||other.category===r.category&&(other.title.toLowerCase().match(/[a-z]{4,}/g)||[]).filter(function(w){return terms.has(w);}).length>=2;
        }).slice(0,4);
        if(related.length){var relatedSection=el("section","nd-section");relatedSection.appendChild(el("h3","",tx("Related reporting","相关报道")));related.forEach(function(other){var b=button(title(other),function(){openStory(other.id,b);},"nd-related");b.appendChild(el("small","",other.source+" · "+clockLabel(other)+age(other.clockAt,Date.now(),zh())));relatedSection.appendChild(b);});relatedSection.appendChild(el("p","nd-note",tx("A reading list based on shared companies and headline terms.","根据共同公司与标题关键词整理的阅读列表。")));content.appendChild(relatedSection);}
      }else if(detailTab==="evidence"){evidence(content,r);}
      else{
        var entries=r.timeline.filter(function(e){return e&&typeof e==="object";}).map(function(e){return{time:e.ts||e.at,title:strip(zh()&&e.label_zh?e.label_zh:e.label_en)||(e.kind==="first_report"?tx("Report first received","首次收录报道"):e.kind==="amendment"?tx("Source amendment received","已收录来源修订"):strip(e.kind)),name:strip(e.source_name)||r.source};});
        if(!entries.length){content.appendChild(el("p","nd-note",tx("Retained source evidence; no separate change history supplied.","仅展示保留的来源依据，未提供独立变更记录。")));entries=r.evidence.map(function(e){return{time:e.published_at,title:strip(e.headline)||r.title,name:strip(e.name)||r.source};});}
        entries.sort(function(a,b){return (stamp(b.time)||0)-(stamp(a.time)||0);});
        entries.slice(0,40).forEach(function(e){var box=el("div","nd-receipt");box.append(el("small","",fullTime(e.time)+" · "+e.name),el("p","",e.title));content.appendChild(box);});
        section(content,tx("Original publication","原始发布"),fullTime(r.publishedAt));
        if(r.sourceUpdatedAt)section(content,tx("Publisher's declared update","发布者声明的更新时间"),fullTime(r.sourceUpdatedAt));
        if(r.indexedAt)section(content,tx("Provider indexed this report","供应商索引收录"),fullTime(r.indexedAt));
        section(content,tx("First seen by this desk","新闻台首次收录"),fullTime(r.receivedAt));
        if(r.raw.accepted_revision_at)section(content,tx("Latest reporting accepted","最近收录报道变更"),fullTime(r.raw.accepted_revision_at));
        (Array.isArray(r.raw.revision_history)?r.raw.revision_history:[]).slice(0,12).forEach(function(v){var box=el("div","nd-receipt");box.append(el("small","",tx("Earlier version · ","此前版本 · ")+fullTime(v.accepted_at)),el("p","",strip(v.headline)));content.appendChild(box);});
        content.appendChild(el("p","nd-note",tx("This timeline shows evidence retained with this story. It is not a complete publication history.","此时间线展示随报道保留的依据，并非完整发布历史。")));
      }
      if(r.raw.attribution){content.appendChild(el("p","nd-note",r.raw.attribution));if(r.raw.source_use_url)content.appendChild(link(tx("Source terms","来源条款"),safeURL(r.raw.source_use_url),"nd-note"));}
      fragment.appendChild(content);body.replaceChildren(fragment);body.scrollTop=scroll;
      if(hadFocus){var restored=Array.from(body.querySelectorAll("[data-action]")).find(function(n){return n.dataset.action===focusAction;});(restored||$("ndDetailClose")).focus();}
    }
    function openStory(id,trigger){
      selected=id;requestedStoryId=null;lastFocus=trigger||lastFocus;detailTab="brief";
      if(!prefs.read.includes(id)){prefs.read.push(id);prefs.read=prefs.read.slice(-500);persist();}
      $("ndDetail").dataset.open="true";renderDetail();
      doc.querySelectorAll(".nd-row").forEach(function(r){r.dataset.selected=String(r.dataset.id===id);if(r.dataset.id===id)r.dataset.read="true";});
      syncDetailModal();if(win.matchMedia("(max-width:760px)").matches)$("ndDetailClose").focus();
      if(trigger){var url=new URL(win.location.href);url.hash="story="+encodeURIComponent(id);win.history.replaceState(null,"",url.pathname+url.search+url.hash);}
    }
    function syncDetailModal(){
      var panel=$("ndDetail"),modal=panel.dataset.open==="true"&&win.matchMedia("(max-width:760px)").matches;
      if(modal){panel.setAttribute("role","dialog");panel.setAttribute("aria-modal","true");panel.setAttribute("aria-label",tx("Story workspace","报道工作区"));if(!panel.contains(doc.activeElement))$("ndDetailClose").focus();}
      else{panel.removeAttribute("role");panel.removeAttribute("aria-modal");panel.removeAttribute("aria-labelledby");}
    }
    function closeStory(){
      var closedId=selected;
      requestedStoryId=null;
      $("ndDetail").dataset.open="false";$("ndDetail").removeAttribute("role");$("ndDetail").removeAttribute("aria-modal");
      selected=null;$("ndDetailBody").replaceChildren(el("div","nd-detail-empty",tx("Select a story to explore its reporting and source evidence.","请选择报道，查看内容与来源依据。")));doc.querySelectorAll(".nd-row").forEach(function(r){r.dataset.selected="false";});
      var url=new URL(win.location.href);url.hash="";win.history.replaceState(null,"",url.pathname+url.search);
      var currentRow=Array.from(doc.querySelectorAll(".nd-row")).find(function(n){return n.dataset.id===closedId;});
      var target=lastFocus&&lastFocus.isConnected?lastFocus:currentRow&&currentRow.querySelector("button")||$("ndFeedPanel");target.focus();
    }
    function toggleSaved(id){
      if(prefs.saved.includes(id))prefs.saved=prefs.saved.filter(function(x){return x!==id;});else prefs.saved.push(id);
      prefs.saved=prefs.saved.slice(-500);persist();renderDetail();if(filters.saved)render();
      announce(prefs.saved.includes(id)?tx("Story saved on this browser","已在此浏览器收藏报道"):tx("Story removed from saved","已取消收藏"));
    }
    function setConnection(state,label){mode=state;$("ndConnection").dataset.state=state;$("ndConnection").textContent=label;if($("ndConnectionMobile")){$("ndConnectionMobile").dataset.state=state;$("ndConnectionMobile").textContent=label;}}
    function banner(message,auth,retry){$("ndBanner").hidden=!message;$("ndBannerText").textContent=message||"";$("ndSignIn").hidden=!auth;$("ndRetry").hidden=!retry;}
    function accept(payload){
      if(!validSnapshot(payload))throw new Error("schema");
      var previous=latest,first=!liveReady;latest=combine(payload.stories,[]);health=payload.health||{};sourceHealth=Array.isArray(payload.source_health)?payload.source_health:[];liveReady=true;
      var priorById=new Map(previous.map(function(r){return[r.id,r];})),changedIds=new Set(latest.filter(function(r){var old=priorById.get(r.id);return old&&fingerprint(old)!==fingerprint(r);}).map(function(r){return r.id;}));
      if(changedIds.size){prefs.read=prefs.read.filter(function(id){return !changedIds.has(id);});persist();}
      latest.forEach(function(r){deskAliases.add(r.id);deskAliases.add(canonicalURL(r.url));deskAliases.add(r.title.toLowerCase());});
      var combined=combinedRows(latest);pending=difference(visible,combined);
      var currentById=new Map(combined.map(function(r){return[r.id,r];}));
      visible=visible.filter(function(r){return !deskAliases.has(r.id)||currentById.has(r.id);}).map(function(r){return currentById.get(r.id)||r;});
      if(selected){
        var old=previous.find(function(r){return r.id===selected;}),current=latest.find(function(r){return r.id===selected;});
        if(old&&!current){
          $("ndDetailBody").replaceChildren(el("div","nd-change-note",tx("This story is no longer in the current feed. It may have been withdrawn or left the active window. Open a current story to continue.","此报道已不在当前新闻流中，可能已撤回或超出有效时间范围。请选择当前报道继续。")));
        }else if(old&&current&&fingerprint(old)!==fingerprint(current)){renderDetail(tx("This story has changed while you were reading. The latest available evidence is shown below.","你阅读期间，此报道已发生变化。下方展示最新可用依据。"));}
        else if(!old&&current){renderDetail();}
      }
      if(first||$("ndAutoFollow").checked&&$("ndFeedPanel").scrollTop<40){visible=combined;pending=0;render();}
      if(!first)render();
      $("ndUpdates").hidden=pending===0;
      if(pending){$("ndUpdates").textContent=pending+" "+tx("updates · Show latest","条更新 · 显示最新");announce(pending+" "+tx("news updates available","条新闻更新可用"));}
      lastTransportAt=Date.now();freshness();
      if(requestedStoryId){
        if(combined.some(function(r){return r.id===requestedStoryId;}))openStory(requestedStoryId);
        else if(first){$("ndDetail").dataset.open="true";$("ndDetailBody").replaceChildren(el("div","nd-empty",tx("This shared story is outside the loaded window or no longer available. Search for its subject or open another current report.","此分享报道已超出载入范围或不可用。请搜索相关主题或打开当前报道。")));syncDetailModal();}
      }
      if(!requestedStoryId&&!selected&&shown.length&&!win.matchMedia("(max-width:760px)").matches)openStory(shown[0].id);
    }
    function schedule(ms){win.clearTimeout(timer);if(!disposed&&!authPaused&&!doc.hidden)timer=win.setTimeout(function(){timer=0;connect();},ms);}
    function closeStream(){generation++;win.clearTimeout(handshake);if(stream){stream.close();stream=null;}}
    async function getSnapshot(url){
      var controller=new AbortController(),timeout=win.setTimeout(function(){controller.abort();},10000);
      try{
        var response=await win.fetch(url,{credentials:"same-origin",cache:"no-store",signal:controller.signal,headers:{Accept:"application/json"}});
        if(!response.ok){var error=new Error("http");error.status=response.status;throw error;}
        var content=await response.text();if(content.length>4194304)throw new Error("size");
        var p=JSON.parse(content);if(!validSnapshot(p))throw new Error("schema");return p;
      }finally{win.clearTimeout(timeout);}
    }
    async function connect(){
      if(inflight||disposed||authPaused||doc.hidden)return;inflight=true;closeStream();var issued=generation;
      try{
        var p,legacy=false;
        try{p=await getSnapshot("/api/news-desk/snapshot");}catch(e){if(e.status===404){legacy=true;p=await getSnapshot("live/intelligence.json");}else throw e;}
        if(issued!==generation||disposed||doc.hidden)return;
        accept(p);failures=0;banner("",false,false);
        if(!streamAvailable&&Date.now()>=streamRetryAt){streamAvailable=true;streamFailures=0;}
        if(legacy||!win.EventSource||!streamAvailable){setConnection("polling",tx("Auto refresh · 10s","自动刷新 · 10秒"));schedule(10000);return;}
        setConnection("connecting",tx("Connecting","正在连接"));stream=new win.EventSource("/api/news-desk/stream",{withCredentials:true});
        handshake=win.setTimeout(function(){if(issued!==generation)return;streamAvailable=false;streamRetryAt=Date.now()+300000;closeStream();setConnection("polling",tx("Auto refresh · 10s","自动刷新 · 10秒"));schedule(10000);},12000);
        stream.addEventListener("snapshot",function(e){if(issued!==generation)return;win.clearTimeout(handshake);try{accept(JSON.parse(e.data));streamFailures=0;setConnection("connected",tx("Stream connected","新闻流已连接"));banner("",false,false);}catch(_){closeStream();setConnection("degraded",tx("Feed interrupted","新闻流中断"));banner(tx("A news update could not be read. Your current stories remain available.","暂时无法读取新闻更新，当前报道仍可阅读。"),false,true);schedule(5000);}});
        stream.addEventListener("heartbeat",function(){if(issued===generation)lastTransportAt=Date.now();});
        stream.addEventListener("reconnect",function(){if(issued!==generation)return;closeStream();schedule(250);});
        stream.addEventListener("unavailable",function(){if(issued!==generation)return;closeStream();setConnection("degraded",tx("Feed unavailable","新闻流不可用"));banner(tx("Live updates are unavailable. The last loaded reporting remains visible.","实时更新暂不可用，已载入报道仍可阅读。"),false,true);schedule(5000);});
        stream.onerror=function(){if(issued!==generation)return;streamFailures++;if(streamFailures>=3){streamAvailable=false;streamRetryAt=Date.now()+300000;}closeStream();setConnection("degraded",tx("Reconnecting","正在重连"));banner(tx("Connection interrupted. Reconnecting to recover the latest feed.","连接已中断，正在重连并恢复最新新闻流。"),false,true);schedule(streamAvailable?Math.min(15000,2000*Math.pow(2,streamFailures-1)):10000);};
      }catch(e){
        if(issued!==generation||disposed||doc.hidden)return;
        failures++;var auth=e.status===401||e.status===403;
        if(auth)clearProtected();
        setConnection(auth?"restricted":"degraded",auth?tx("Sign in for live","登录查看实时新闻"):tx(win.navigator.onLine===false?"Offline":"Updates unavailable",win.navigator.onLine===false?"离线":"更新不可用"));
        banner(auth?tx("Sign in to connect to live desk updates. Browse the available edition below.","登录以连接实时新闻台；仍可浏览下方已载入报道。"):tx("Live updates could not be loaded. The last available reporting remains readable.","无法载入实时更新，最新可用报道仍可阅读。"),auth,!auth);
        if(!auth)schedule(Math.min(30000,3000*Math.pow(2,Math.min(failures,4))));
      }finally{inflight=false;if(issued!==generation&&!doc.hidden&&!disposed&&!authPaused&&!stream&&!timer)schedule(0);}
    }
    function clearProtected(){latest=[];health={};sourceHealth=[];lastTransportAt=0;closeStory();liveReady=false;visible=combine([],seed.stories);pending=0;$("ndUpdates").hidden=true;selected=null;$("ndDetailBody").replaceChildren(el("div","nd-empty",tx("Sign in again to read live desk stories.","请重新登录以阅读实时新闻台报道。")));render();if($("ndCoverage").open)renderCoverage();}
    function openDialog(id){var d=$(id);if(d.open)return;if(typeof d.showModal==="function")d.showModal();else d.setAttribute("open","");}
    function closeDialog(d){if(typeof d.close==="function")d.close();else d.removeAttribute("open");}
    function renderCoverage(){
      var body=$("ndCoverageBody");body.replaceChildren();
      section(body,tx("Delivery connection","传输连接"),$("ndConnection").textContent);
      body.appendChild(el("p","nd-note",tx("A connected stream means this page can receive desk changes. Publisher timing, collection cadence and source availability determine how fresh the reporting is.","新闻流已连接表示页面能够接收新闻台的变化。报道时效取决于发布者时间、采集频率与来源可用性。")));
      section(body,tx("Latest source publication","最新来源发布时间"),$("ndFreshness").textContent);
      var rows=combinedRows(latest),counts=new Map();rows.forEach(function(r){counts.set(r.source,(counts.get(r.source)||0)+1);});
      var heading=el("h3","nd-nav-heading",tx("Sources in the loaded window","已载入时间范围内的来源"));body.appendChild(heading);
      Array.from(counts).sort(function(a,b){return b[1]-a[1];}).slice(0,40).forEach(function(e){var row=el("div","nd-coverage-row");row.append(el("span","",e[0]),el("span","",e[1]+" "+tx("stories","条报道")));body.appendChild(row);});
      body.appendChild(el("p","nd-note",tx("These are sources represented in the loaded feed, not a count of connected or independently verified sources. Paid source availability follows the existing account and display permissions.","此处列出已载入新闻流中的来源，并非已连接或已独立核实的来源数量。付费来源的可用性遵循现有账户与展示权限。")));
      if(sourceHealth.length){
        body.appendChild(el("h3","nd-nav-heading",tx("Collection health","采集健康状态")));
        sourceHealth.forEach(function(item){
          var card=el("div","nd-receipt"),checked=stamp(item.last_fetch_success_at),stale=checked!==null&&Date.now()-checked>Math.max(900000,Number(item.poll_seconds||120)*4000);
          var state=item.status==="held"?tx("Permission pending","等待授权"):item.status==="degraded"?tx("Fetch failed","采集失败"):stale?tx("Check overdue","检查已延迟"):checked!==null?tx("Checked","已检查"):tx("Unknown","未知");
          card.appendChild(el("strong","",strip(item.publisher)));card.appendChild(el("small","",state+(checked!==null?" · "+age(item.last_fetch_success_at,Date.now(),zh()):"")));
          if(item.last_accepted_at)card.appendChild(el("small","",tx("Last new or amended report ","最近新增或修订报道 ")+fullTime(item.last_accepted_at)));
          body.appendChild(card);
        });
      }
      if(health.last_source_published_at)section(body,tx("Desk source timestamp","新闻台来源时间"),fullTime(health.last_source_published_at));
    }
    function renderViews(){
      var box=$("ndSavedViews");box.replaceChildren();$("ndSavedViewsMobile").replaceChildren();
      prefs.views.filter(function(v){return v&&typeof v.name==="string"&&v.filters&&typeof v.filters==="object";}).forEach(function(v,index){
        var line=el("div","nd-saved-view"),b=button(v.name,function(){filters=Object.assign({},DEFAULT_FILTERS,v.filters);limit=60;render();saveFiltersToURL();},"nd-btn nd-btn-quiet");
        line.appendChild(b);var remove=button("×",function(){prefs.views.splice(index,1);persist();renderViews();},"nd-btn nd-btn-quiet");remove.setAttribute("aria-label",tx("Delete view ","删除视图 ")+v.name);line.appendChild(remove);box.appendChild(line);
        $("ndSavedViewsMobile").appendChild(button(v.name,function(){filters=Object.assign({},DEFAULT_FILTERS,v.filters);limit=60;closeDialog($("ndWorkspace"));render();saveFiltersToURL();},"nd-btn"));
      });
    }
    function reset(){filters=Object.assign({},DEFAULT_FILTERS);limit=60;render();saveFiltersToURL();}
    function refreshLanguage(){
      doc.querySelectorAll("[data-placeholder-zh]").forEach(function(n){if(!n.dataset.placeholderEn)n.dataset.placeholderEn=n.placeholder;n.placeholder=zh()?n.dataset.placeholderZh:n.dataset.placeholderEn;});
      doc.querySelectorAll("[data-label-zh]").forEach(function(n){if(!n.dataset.labelEn)n.dataset.labelEn=n.getAttribute("aria-label");n.setAttribute("aria-label",zh()?n.dataset.labelZh:n.dataset.labelEn);});
      doc.querySelectorAll("option[data-en]").forEach(function(n){n.textContent=zh()?n.dataset.zh:n.dataset.en;});
      render();if(selected)renderDetail();if($("ndCoverage").open)renderCoverage();renderViews();
    }
    $("ndSearch").addEventListener("input",function(){filters.query=this.value;limit=60;render();saveFiltersToURL();});
    $("ndTime").addEventListener("change",function(){filters.time=this.value;render();saveFiltersToURL();});
    $("ndRegion").addEventListener("change",function(){filters.region=this.value;render();saveFiltersToURL();});
    doc.querySelectorAll("[data-category]").forEach(function(b){b.addEventListener("click",function(){filters.category=b.dataset.category;filters.saved=false;limit=60;render();saveFiltersToURL();});});
    doc.querySelectorAll("[data-view]").forEach(function(b){b.addEventListener("click",function(){filters.view=b.dataset.view;filters.saved=false;limit=60;render();saveFiltersToURL();});b.addEventListener("keydown",function(e){if(e.key!=="ArrowLeft"&&e.key!=="ArrowRight")return;var tabs=Array.from(doc.querySelectorAll("[data-view]")),index=tabs.indexOf(b),next=tabs[(index+(e.key==="ArrowRight"?1:-1)+tabs.length)%tabs.length];e.preventDefault();next.click();next.focus();});});
    $("ndFilterOpen").addEventListener("click",function(){syncControls();openDialog("ndFilters");});
    $("ndFiltersForm").addEventListener("submit",function(e){e.preventDefault();filters.category=$("ndCategorySelect").value;filters.kind=$("ndSourceKind").value;filters.source=$("ndSourceSearch").value.trim();filters.unread=$("ndUnread").checked;filters.social=$("ndIncludeSocial").checked;limit=60;closeDialog($("ndFilters"));render();saveFiltersToURL();});
    ["ndReset","ndEmptyReset"].forEach(function(id){$(id).addEventListener("click",reset);});
    $("ndMore").addEventListener("click",function(){limit+=60;render();});
    $("ndUpdates").addEventListener("click",function(){applyLatest(true);});
    $("ndAutoFollow").addEventListener("change",function(){if(this.checked)applyLatest(true);});
    $("ndDensity").addEventListener("click",function(){var reading=root.dataset.density!=="reading";root.dataset.density=reading?"reading":"compact";prefs.density=root.dataset.density;persist();this.setAttribute("aria-pressed",String(reading));});
    $("ndFollowSave").addEventListener("click",function(){prefs.following=$("ndFollowInput").value.split(/[,，、\n]+/).map(function(s){return s.trim();}).filter(Boolean).slice(0,40);persist();render();});
    $("ndFollowInput").addEventListener("keydown",function(e){if(e.key==="Enter")$("ndFollowSave").click();});
    ["ndSavedStories","ndSavedStoriesMobile"].forEach(function(id){$(id).addEventListener("click",function(){filters.saved=!filters.saved;filters.view="latest";if($("ndWorkspace").open)closeDialog($("ndWorkspace"));render();saveFiltersToURL();});});
    $("ndDetailClose").addEventListener("click",closeStory);
    $("ndCoverageOpen").addEventListener("click",function(){renderCoverage();openDialog("ndCoverage");});
    doc.querySelectorAll("[data-open-panel]").forEach(function(b){b.addEventListener("click",function(){var parent=b.closest("dialog");if(parent)closeDialog(parent);openDialog(b.dataset.openPanel);});});
    $("ndHelpOpen").addEventListener("click",function(){openDialog("ndHelp");});
    ["ndSaveView","ndSaveViewMobile"].forEach(function(id){$(id).addEventListener("click",function(){if($("ndFilters").open)closeDialog($("ndFilters"));openDialog("ndViewDialog");$("ndViewName").focus();});});
    $("ndViewForm").addEventListener("submit",function(e){e.preventDefault();var name=$("ndViewName").value.trim();if(!name)return;prefs.views.push({name:name,filters:Object.assign({},filters)});prefs.views=prefs.views.slice(-12);persist();renderViews();closeDialog($("ndViewDialog"));});
    $("ndRetry").addEventListener("click",function(){win.clearTimeout(timer);connect();});
    doc.querySelectorAll("[data-close-dialog]").forEach(function(b){b.addEventListener("click",function(){closeDialog(b.closest("dialog"));});});
    doc.addEventListener("keydown",function(e){
      var typing=/INPUT|TEXTAREA|SELECT/.test(doc.activeElement&&doc.activeElement.tagName)||doc.activeElement&&doc.activeElement.isContentEditable;
      var otherDialog=Array.from(doc.querySelectorAll('dialog[open],[role="dialog"]')).some(function(n){return n.id!=="ndDetail"&&!n.hidden&&win.getComputedStyle(n).display!=="none";});
      if(e.key==="Escape"){if(!otherDialog&&selected)closeStory();return;}
      if(otherDialog)return;
      if($("ndDetail").getAttribute("aria-modal")==="true"&&e.key==="Tab"){
        var nodes=Array.from($("ndDetail").querySelectorAll("button,a[href]")).filter(function(n){return !n.hidden;});
        var first=nodes[0],last=nodes[nodes.length-1];if(!$("ndDetail").contains(doc.activeElement)){e.preventDefault();first.focus();return;}if(e.shiftKey&&doc.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&doc.activeElement===last){e.preventDefault();first.focus();}return;
      }
      if($("ndDetail").getAttribute("aria-modal")==="true"&&e.key!=="s")return;
      if(typing||e.ctrlKey||e.metaKey||e.altKey||otherDialog)return;
      if(e.key==="/"){e.preventDefault();$("ndSearch").focus();}
      if(e.key==="s"&&selected){e.preventDefault();toggleSaved(selected);}
      if((e.key==="j"||e.key==="k")&&shown.length){e.preventDefault();var index=shown.findIndex(function(r){return r.id===selected;}),next=Math.max(0,Math.min(shown.length-1,index+(e.key==="j"?1:-1)));var r=shown[next];if(next>=limit){limit=next+20;render();}var row=Array.from(doc.querySelectorAll(".nd-row")).find(function(n){return n.dataset.id===r.id;});openStory(r.id,row&&row.querySelector("button"));if(row)row.scrollIntoView({block:"nearest",behavior:"auto"});}
    });
    var breakpoint=win.matchMedia("(max-width:760px)");if(breakpoint.addEventListener)breakpoint.addEventListener("change",syncDetailModal);
    doc.addEventListener("langchange",refreshLanguage);
    doc.addEventListener("visibilitychange",function(){if(doc.hidden){closeStream();win.clearTimeout(timer);timer=0;setConnection("paused",tx("Paused in background","后台已暂停"));}else connect();});
    win.addEventListener("online",connect);
    win.addEventListener("mdx-auth",function(event){
      var detail=event.detail||{};if(detail.event==="PREFS_SAVED")return;
      closeStream();win.clearTimeout(timer);timer=0;clearProtected();authPaused=!detail.user;
      if(authPaused){setConnection("restricted",tx("Sign in for live","登录查看实时新闻"));banner(tx("Sign in to connect to live desk updates. Browse the available edition below.","登录以连接实时新闻台；仍可浏览下方已载入报道。"),true,false);}
      else schedule(0);
    });
    win.addEventListener("pagehide",function(){disposed=true;closeStream();win.clearTimeout(timer);});
    win.addEventListener("pageshow",function(e){if(e.persisted){disposed=false;connect();}});
    readURL();refreshLanguage();
    if(requestedStoryId&&visible.some(function(r){return r.id===requestedStoryId;}))openStory(requestedStoryId);
    if(!requestedStoryId&&!selected&&shown.length&&!win.matchMedia("(max-width:760px)").matches)openStory(shown[0].id);
    win.setInterval(freshness,15000);connect();
    return {accept:accept,getState:function(){return {filters:filters,pending:pending,mode:mode,selected:selected};}};
  }
  return {normalize:normalize,combine:combine,tokens:tokens,matchesTerms:matchesTerms,filterRows:filterRows,difference:difference,age:age,validSnapshot:validSnapshot,safeURL:safeURL,defaults:DEFAULT_FILTERS,mount:mount};
});

