/* News Desk: private live delivery, read-stable presentation and local view preferences.
 * Source and story identity remain with the existing news owners. No vendor calls.
 */
(function (root, factory) {
  "use strict";
  var research = typeof module === "object" && module.exports ? require("./news_research.js") : root.NewsDeskResearch;
  var api = factory(research);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root.document) api.mount(root.document, root);
})(typeof window !== "undefined" ? window : globalThis, function (research) {
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
    var published=[r.published_at,r.ts,primary.published_at].map(text).find(function(value){return stamp(value)!==null;})||"";
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
    var prefs={saved:[],read:[],following:[],views:[],density:"compact"},seed={},stored={},filters=Object.assign({},DEFAULT_FILTERS);
    try {stored=JSON.parse(win.localStorage.getItem("mm.newsDesk.preferences.v1")||"{}")||{};["saved","read","following","views"].forEach(function(k){if(Array.isArray(stored[k]))prefs[k]=stored[k].slice(0,k==="views"?12:500);});if(stored.density==="reading")prefs.density="reading";}catch(_){}
    try{seed=JSON.parse($("ndSeed").textContent||"{}");}catch(_){}
    ["saved","read","following"].forEach(function(k){prefs[k]=prefs[k].filter(function(v){return typeof v==="string"&&v.length<=300;});});
    prefs.views=research.cleanViews(prefs.views,DEFAULT_FILTERS);prefs.research=research.cleanState(stored.research);stored={};
    prefs.research=research.prune(prefs.research,prefs.views.map(function(v){return "v:"+v.id;}).concat(prefs.research.investigations.map(function(v){return "i:"+v.id;})));
    var deskAliases=new Set();
    function combinedRows(rows){return combine(rows,(seed.stories||[]).filter(function(raw){var r=normalize(raw,"edition");return r&&!deskAliases.has(r.id)&&!deskAliases.has(canonicalURL(r.url))&&!deskAliases.has(r.title.toLowerCase());}));}
    var latest=[],visible=combine([],seed.stories),selected=null,shown=[],limit=60,pending=0,lastFocus=null,detailTab="brief",requestedStoryId=null;
    try{if(win.location.hash.startsWith("#story="))requestedStoryId=decodeURIComponent(win.location.hash.slice(7));}catch(_){}
    root.dataset.density=prefs.density;$("ndDensity").setAttribute("aria-pressed",String(prefs.density==="reading"));
    var liveReady=false,health={},sourceHealth=[],stream=null,timer=0,inflight=false,disposed=false,authPaused=false,mode="connecting",lastTransportAt=0,failures=0,generation=0,handshake=0,streamAvailable=true,streamFailures=0,streamRetryAt=0;
    var connectionLabel=["Connecting","正在连接"];
    var compareIds=[],compareRelation="question",investigationId=null,pendingInvestigationIds=[],researchWarmed=false,researchSequence=0,researchReturns=new Map(),researchIndex=new Map();
    var retained={descriptor:{state:"unavailable"},generation:0,controller:null,loading:false,status:"unavailable",query:null,rows:[],index:new Map(),matched:0,next:null,waitingRevision:null};
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
      if(mode==="connected"&&lastTransportAt&&ms-lastTransportAt>45000){closeStream();setConnection("degraded","Reconnecting","正在重连");banner(tx("The connection stopped responding. Recovering the latest available reporting.","连接已停止响应，正在恢复最新可用报道。"),false,true);schedule(0);}
    }
    function render(){
      var panel=$("ndFeedPanel"),oldScroll=panel.scrollTop,active=doc.activeElement,focused=panel.contains(active),focusRow=focused&&active.closest(".nd-row"),focusId=focusRow&&focusRow.dataset.id,focusPick=focused&&active.classList.contains("nd-report-pick");
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
        r.tickers.slice(0,2).forEach(function(t){meta.appendChild(el("span","nd-ticker",t));});
        if(researchStory(r.id)){var pick=button(compareIds.includes(r.id)?tx("Selected","已选择"):tx("Compare","对照阅读"),function(){toggleCompare(r.id);},"nd-report-pick");pick.setAttribute("aria-pressed",String(compareIds.includes(r.id)));pick.setAttribute("aria-label",tx("Select for comparison: ","选择报道进行对照阅读：")+title(r));pick.dataset.researchFocus="feed-pick-"+r.id;meta.appendChild(pick);}
        body.appendChild(meta);row.append(gutter,body);fragment.appendChild(row);
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
      if(focused){var restoredRow=Array.from($("ndFeed").children).find(function(n){return n.dataset.id===focusId;}),target=restoredRow&&restoredRow.querySelector(focusPick?".nd-report-pick":".nd-title")||panel;target.focus({preventScroll:true});}
      syncControls();freshness();renderResearchSummary();
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
      var r=researchIndex.get(selected)||latest.find(function(x){return x.id===selected;})||visible.find(function(x){return x.id===selected;});if(!r)return;
      var body=$("ndDetailBody"),scroll=body.scrollTop,fragment=doc.createDocumentFragment(),hadFocus=body.contains(doc.activeElement),focusAction=hadFocus?doc.activeElement.dataset.action:null;
      var k=el("div","nd-detail-kicker",tx.apply(null,CATEGORY[r.category])+" · "+tx(r.kind==="official"?"Official source":r.kind==="social"?"Social statement":"News reporting",r.kind==="official"?"官方来源":r.kind==="social"?"社交声明":"新闻报道"));
      var h=articleLanguage(el("h2","",title(r)),r,!!r.titleZh);h.id="ndStoryTitle";fragment.append(k,h);
      if(changeNotice)fragment.appendChild(el("div","nd-change-note",changeNotice));
      fragment.appendChild(el("div","nd-detail-sub",r.source+" · "+clockLabel(r)+fullTime(r.clockAt)));
      var actions=el("div","nd-detail-actions");
      if(r.url)actions.appendChild(link(tx("Read original ↗","阅读原文 ↗"),r.url,"nd-btn"));
      actions.appendChild(button(prefs.saved.includes(r.id)?tx("Saved","已收藏"):tx("Save story","收藏报道"),function(){toggleSaved(r.id);}));
      actions.appendChild(button(tx("Copy link","复制链接"),async function(){try{var u=new URL(win.location.href);u.hash="story="+encodeURIComponent(r.id);await win.navigator.clipboard.writeText(u.href);announce(tx("Story link copied","已复制报道链接"));}catch(_){announce(tx("Copy the address from your browser to share this view.","复制浏览器地址以分享此视图。"));}},"nd-btn nd-btn-quiet"));
      if(researchStory(r.id)){
        var compare=button(compareIds.includes(r.id)?tx("Selected to compare","已选入对照阅读"):tx("Select to compare","选择对照阅读"),function(){toggleCompare(r.id);});compare.setAttribute("aria-pressed",String(compareIds.includes(r.id)));actions.appendChild(compare);
        actions.appendChild(button(tx("Add to investigation","加入研究专题"),function(e){openInvestigations([r.id],e.currentTarget);},"nd-btn nd-btn-quiet"));
      }
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
      if(modal){panel.setAttribute("role","dialog");panel.setAttribute("aria-modal","true");panel.setAttribute("aria-label",tx("Story workspace","报道工作区"));if(!panel.contains(doc.activeElement)&&!Array.from(doc.querySelectorAll('dialog[open]')).some(blockingDialog))$("ndDetailClose").focus();}
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
    // Research resolves references against the same accepted, authorized model as
    // the desk. Local preferences never retain a headline, brief or source body.
    function researchRows(){return liveReady?Array.from(researchIndex.values()):[];}
    function researchStory(id){return liveReady?researchIndex.get(id)||(retained.descriptor.state==="available"?retained.index.get(id):null):null;}
    function localId(prefix){researchSequence++;return prefix+"-"+Date.now().toString(36)+"-"+researchSequence.toString(36)+"-"+Math.random().toString(36).slice(2,9);}
    function relationName(value){return tx.apply(null,{question:["Open question","开放问题"],topic:["Shared topic","共同主题"],accounts:["Different accounts","不同叙述"],connection:["Possible connection","可能的关联"]}[value]||["Open question","开放问题"]);}
    function researchFocus(node,key){node.dataset.researchFocus=key;return node;}
    function researchLinks(parent,prefix){Array.from(parent.querySelectorAll("a")).forEach(function(node,index){if(!node.dataset.researchFocus)researchFocus(node,prefix+"-source-"+index);});}
    function rebuildResearch(container,build){
      var active=doc.activeElement,owns=container.contains(active),key=owns&&active.dataset.researchFocus,scroll=container.scrollTop,scroller=container.closest(".nd-dialog-body"),dialogScroll=scroller&&scroller.scrollTop;
      var open=new Set(Array.from(container.querySelectorAll("details[open][data-research-focus]")).map(function(n){return n.dataset.researchFocus;}));
      var fragment=doc.createDocumentFragment();build(fragment,open);container.replaceChildren(fragment);container.scrollTop=scroll;if(scroller)scroller.scrollTop=dialogScroll;
      container.querySelectorAll("details[data-research-focus]").forEach(function(n){if(open.has(n.dataset.researchFocus))n.open=true;});
      if(owns){var restored=Array.from(container.querySelectorAll("[data-research-focus]")).find(function(n){return n.dataset.researchFocus===key;});var dialog=container.closest("dialog");(restored||dialog&&dialog.querySelector("[data-close-dialog]")||$("ndFeedPanel")).focus({preventScroll:true});}
    }
    function renderResearchSummary(){
      $("ndCompareTray").hidden=!compareIds.length;$("ndCompareCount").textContent=compareIds.length+" "+tx("selected · up to 3 reports","条已选 · 最多 3 条报道");
      $("ndCompareOpen").disabled=compareIds.length<2||!liveReady;
      var unread=prefs.research.updates.filter(function(u){return !u.read;}).length;
      ["ndMonitorCount","ndMonitorCountMobile"].forEach(function(id){$(id).textContent=String(unread);$(id).hidden=!unread;});$("ndWorkspaceUpdates").hidden=!unread;
      $("ndMonitorEnable").textContent=prefs.research.enabled?tx("Pause monitoring","暂停监测"):tx("Enable monitoring","启用监测");$("ndMonitorEnable").setAttribute("aria-pressed",String(prefs.research.enabled));
      $("ndMonitorQuiet").textContent=tx("Quiet mode","安静模式");$("ndMonitorQuiet").setAttribute("aria-pressed",String(prefs.research.quiet));
      $("ndMonitorReadAll").disabled=!unread;$("ndMonitorReset").disabled=!prefs.research.updates.length&&!prefs.research.records.length;
      var count=prefs.research.watching.length,status=!prefs.research.enabled?tx("Monitoring is off. Choose a saved search or investigation, then enable it.","监测已关闭。请选择已保存搜索或研究专题，然后启用监测。"):!count?tx("Choose a saved search or investigation to monitor.","请选择要监测的已保存搜索或研究专题。"):!liveReady?tx("Waiting for an authorized live feed. Existing reports will form a silent starting point.","等待已授权的实时新闻流。现有报道将作为静默起点。"):tx("Watching ","正在监测 ")+count+tx(" selections. "," 项。 ")+(mode==="degraded"||mode==="paused"?tx("Updates will resume with the desk connection.","更新将随新闻台连接恢复。"):prefs.research.quiet?tx("New changes are collected here quietly.","新变化将在此安静汇集。"):tx("New changes are announced on this page.","新变化将在本页提示。"));
      $("ndMonitorStatus").textContent=status;
    }
    function toggleCompare(id){
      if(compareIds.includes(id))compareIds=compareIds.filter(function(value){return value!==id;});
      else if(researchStory(id)&&compareIds.length<3){if(!compareIds.length)compareRelation="question";compareIds.push(id);}
      else{announce(tx("Compare up to three reports. Clear one selection to add another.","最多可对照三条报道。请先取消一条选择。"));return;}
      render();if(selected)renderDetail();renderResearch();announce(compareIds.length+" "+tx("reports selected for comparison","条报道已选入对照阅读"));
    }
    function clockList(parent,r){
      var clocks=el("dl","nd-research-clocks");
      [[tx("Published","发布"),r.publishedAt],[tx("Publisher updated","发布者更新"),r.sourceUpdatedAt],[tx("Provider indexed","供应商收录"),r.indexedAt],[tx("First seen by desk","新闻台首次收录"),r.receivedAt],[tx("Latest change accepted","最近收录变更"),r.raw.accepted_revision_at]].forEach(function(pair){var row=el("div","");row.append(el("dt","",pair[0]),el("dd","",fullTime(pair[1])));clocks.appendChild(row);});parent.appendChild(clocks);
    }
    function comparisonHistory(parent,r){
      var box=researchFocus(el("details","nd-research-history"),"history-"+r.id),summary=researchFocus(el("summary","",tx("Retained changes and earlier versions","保留的变更与此前版本")),"history-toggle-"+r.id);box.appendChild(summary);
      var entries=r.timeline.filter(function(e){return e&&typeof e==="object";}).slice(0,40);
      entries.forEach(function(e){var line=el("div","nd-research-version");line.append(el("small","",fullTime(e.ts||e.at)),el("p","",strip(zh()&&e.label_zh?e.label_zh:e.label_en)||(e.kind==="amendment"?tx("Source amendment received","已收录来源修订"):e.kind==="first_report"?tx("Report first received","首次收录报道"):strip(e.kind)||tx("Retained event","保留事件"))));box.appendChild(line);});
      var versions=(Array.isArray(r.raw.revision_history)?r.raw.revision_history:[]).filter(function(v){return v&&typeof v==="object";}).slice(0,12);
      versions.forEach(function(v){var line=el("div","nd-research-version");line.append(el("small","",tx("Earlier version · ","此前版本 · ")+fullTime(v.accepted_at)),el("p","",strip(zh()&&v.headline_zh?v.headline_zh:v.headline)||tx("Headline not retained","未保留标题")));box.appendChild(line);});
      box.appendChild(el("p","nd-note",entries.length||versions.length?tx("Only changes supplied with the current report are shown. This is not a complete publication history.","仅展示随当前报道提供的变更，并非完整发布历史。"):tx("No separate change history was supplied for this report.","此报道未提供独立变更记录。")));parent.appendChild(box);
    }
    function renderComparison(){
      $("ndCompareRelation").value=compareRelation;$("ndCompareSave").disabled=!compareIds.length||!liveReady;
      rebuildResearch($("ndCompareReports"),function(fragment){
        compareIds.forEach(function(id,index){
          var r=researchStory(id),card=el("article","nd-comparison-report");card.dataset.storyId=id;
          var head=el("div","nd-research-card-head");head.appendChild(el("span","nd-eyebrow",tx("Report ","报道 ")+(index+1)));head.appendChild(researchFocus(button(tx("Remove","移除"),function(){toggleCompare(id);},"nd-btn nd-btn-quiet"),"compare-remove-"+id));card.appendChild(head);
          if(!r){card.append(el("h3","",tx("Report outside the current feed","报道不在当前新闻流中")),el("p","nd-note",tx("The reference is kept, but no report is available in the live feed or loaded retained results. This does not establish a withdrawal; search retained reporting to look for a current version.","引用仍保留，但实时新闻流及已载入留存结果中均无此报道。这并不能证明报道已被撤回；可搜索留存报道，查找当前版本。")));fragment.appendChild(card);return;}
          card.appendChild(articleLanguage(el("h3","",title(r)),r,!!r.titleZh));card.appendChild(el("p","nd-research-source",r.source));
          if(!researchIndex.has(id))card.appendChild(el("p","nd-note",tx("From the current retained search","来自当前留存搜索")));
          if(r.url)card.appendChild(researchFocus(link(tx("Read original ↗","阅读原文 ↗"),r.url,"nd-btn nd-btn-quiet"),"compare-original-"+id));
          clockList(card,r);
          var brief=zh()&&r.briefZh?r.briefZh:r.brief,briefBox=el("section","nd-section");briefBox.appendChild(el("h4","",tx("Available brief","现有简报")));briefBox.appendChild(articleLanguage(el("p","",brief&&brief!==title(r)?brief:tx("A separate brief is not available. Read the original for the full account.","暂无独立简报。请阅读原文了解完整内容。")),r,!!r.briefZh));card.appendChild(briefBox);
          if(r.why||r.whyZh){var context=el("section","nd-section");context.append(el("h4","",tx("Desk context · analysis","新闻台解读 · 分析")),articleLanguage(el("p","",zh()&&r.whyZh?r.whyZh:r.why),r,!!r.whyZh));card.appendChild(context);}
          evidence(card,r);comparisonHistory(card,r);
          if(r.raw.attribution)card.appendChild(el("p","nd-note",strip(r.raw.attribution)));
          var terms=safeURL(r.raw.source_use_url);if(terms)card.appendChild(researchFocus(link(tx("Source terms","来源条款"),terms,"nd-note"),"compare-terms-"+id));
          researchLinks(card,"compare-"+id);
          fragment.appendChild(card);
        });
        if(compareIds.length<2)fragment.appendChild(el("p","nd-note",tx("Select two or three reports from the feed to compare their reporting.","请从新闻流中选择两到三条报道，进行对照阅读。")));
      });
    }
    function openComparison(){if(compareIds.length<2||!liveReady)return;renderComparison();openDialog("ndCompare");}
    function currentInvestigation(){return prefs.research.investigations.find(function(item){return item.id===investigationId;});}
    function selectedReferences(){return Array.from(new Set(pendingInvestigationIds.length?pendingInvestigationIds:compareIds)).slice(0,3);}
    function openInvestigations(ids,trigger){pendingInvestigationIds=Array.isArray(ids)?Array.from(new Set(ids)).slice(0,3):[];if(!currentInvestigation())investigationId=prefs.research.investigations[0]&&prefs.research.investigations[0].id;renderInvestigations();openDialog("ndInvestigations",trigger);}
    function renderInvestigations(){
      var items=prefs.research.investigations,current=currentInvestigation(),references=selectedReferences();
      $("ndInvestigationPending").hidden=!references.length;$("ndInvestigationPending").textContent=references.length+" "+tx("selected reports. Create a new investigation or add them to one below.","条已选报道。可创建新专题，或加入下方现有专题。");
      $("ndInvestigationForm").querySelector('button[type="submit"]').disabled=items.length>=research.limits.investigations;
      rebuildResearch($("ndInvestigationList"),function(fragment){
        items.forEach(function(item){var b=researchFocus(button(item.name,function(){investigationId=item.id;renderInvestigations();},"nd-investigation-choice"),"investigation-"+item.id);b.setAttribute("aria-current",String(item.id===investigationId));b.appendChild(el("small","",item.storyIds.length+" "+tx("references","条引用")+" · "+relationName(item.relation)));fragment.appendChild(b);});
        if(!items.length)fragment.appendChild(el("p","nd-note",tx("Start with a question. Add reports as you read.","从一个问题开始，在阅读时加入报道。")));
      });
      $("ndInvestigationCurrent").hidden=!current;if(!current){$("ndInvestigationReports").replaceChildren();return;}
      $("ndInvestigationCurrentTitle").textContent=current.name;
      if(doc.activeElement!==$("ndInvestigationRename"))$("ndInvestigationRename").value=current.name;
      $("ndInvestigationRelation").value=current.relation;
      $("ndInvestigationAdd").textContent=tx("Add selected reports","加入已选报道")+(references.length?" ("+references.length+")":"");$("ndInvestigationAdd").disabled=!liveReady||!references.length||current.storyIds.length>=research.limits.reports;
      $("ndInvestigationCompare").disabled=compareIds.length<2||!liveReady;
      $("ndInvestigationCompare").textContent=tx("Compare selection","对照阅读已选报道")+(compareIds.length?" ("+compareIds.length+")":"");
      var watching=prefs.research.watching.includes("i:"+current.id);$("ndInvestigationWatch").setAttribute("aria-pressed",String(watching));$("ndInvestigationWatch").textContent=watching?tx("In monitoring list","已加入监测"):tx("Monitor this investigation","监测此专题");
      var available=current.storyIds.filter(function(id){return !!researchStory(id);}).length,live=current.storyIds.filter(function(id){return researchIndex.has(id);}).length;
      $("ndInvestigationAvailability").textContent=available+" / "+current.storyIds.length+" "+tx("available","条可用")+" · "+live+" "+tx("in the live feed","条实时报道")+" · "+(available-live)+" "+tx("in the loaded retained search. Missing references keep their place without saved report text.","条来自已载入留存搜索。缺失引用将保留位置，不保存报道内容。");
      rebuildResearch($("ndInvestigationReports"),function(fragment){
        current.storyIds.forEach(function(id,index){var r=researchStory(id),row=el("li","nd-investigation-report"),content=el("div","");row.dataset.storyId=id;
          if(r){content.appendChild(articleLanguage(el("h4","",title(r)),r,!!r.titleZh));content.appendChild(el("p","nd-note",r.source+" · "+clockLabel(r)+fullTime(r.clockAt)));var actions=el("div","nd-research-actions");actions.appendChild(researchFocus(button(tx("Read report","阅读报道"),function(){readResearchStory(id);},"nd-btn nd-btn-quiet"),"investigation-read-"+id));var pick=researchFocus(button(compareIds.includes(id)?tx("Selected","已选择"):tx("Select to compare","选择对照阅读"),function(){toggleCompare(id);},"nd-btn nd-btn-quiet"),"investigation-pick-"+id);pick.setAttribute("aria-pressed",String(compareIds.includes(id)));actions.appendChild(pick);content.appendChild(actions);}
          else{content.append(el("h4","",tx("Saved report ","已保存报道 ")+(index+1)),el("p","nd-note",liveReady?tx("Outside the live feed and loaded retained results. The reference remains; withdrawal and retention limits cannot be distinguished here.","不在实时新闻流及已载入留存结果中。引用仍保留，此处无法区分报道撤回与保留范围限制。"):tx("Sign in and connect to resolve this saved reference.","请登录并连接新闻流以查看此引用。")));}
          row.appendChild(content);row.appendChild(researchFocus(button(tx("Remove reference","移除引用"),function(){current.storyIds=current.storyIds.filter(function(value){return value!==id;});resetResearchBaseline();renderInvestigations();},"nd-btn nd-btn-quiet"),"investigation-remove-"+id));fragment.appendChild(row);
        });
        if(!current.storyIds.length)fragment.appendChild(el("li","nd-note",tx("Select reports in the feed, then add them to this investigation.","请在新闻流中选择报道，再加入此专题。")));
      });
    }
    function watchName(key){var list=key.startsWith("v:")?prefs.views:prefs.research.investigations,item=list.find(function(v){return v.id===key.slice(2);});return item?item.name:tx("Saved selection","已保存选择");}
    function observeResearch(baseline,changedIds){
      if(!liveReady)return;
      var rows=researchRows(),memberships=prefs.views.map(function(v){return{key:"v:"+v.id,ids:filterRows(rows,v.filters,prefs,Date.now()).map(function(r){return r.id;})};}).concat(prefs.research.investigations.map(function(item){return{key:"i:"+item.id,ids:item.storyIds};}));
      var before=JSON.stringify(prefs.research),result=research.advance(prefs.research,rows.map(function(r){return{id:r.id,mark:research.marker(fingerprint(r))};}),memberships,{baseline:baseline===true,changedIds:changedIds,now:Date.now()});
      prefs.research=result.state;researchWarmed=true;if(before!==JSON.stringify(prefs.research))persist();
      if(result.added&&!prefs.research.quiet)announce(result.added+" "+tx("updates in your monitoring inbox","条监测收件箱更新"));
    }
    function resetResearchBaseline(){
      prefs.research=research.prune(research.cleanState(prefs.research),prefs.views.map(function(v){return "v:"+v.id;}).concat(prefs.research.investigations.map(function(v){return "i:"+v.id;})));
      prefs.research.records=[];researchWarmed=false;if(liveReady)observeResearch(true);persist();renderResearch();
    }
    function toggleWatch(key){
      var watching=prefs.research.watching;if(watching.includes(key))prefs.research.watching=watching.filter(function(v){return v!==key;});else if(watching.length<research.limits.watches)prefs.research.watching.push(key);
      resetResearchBaseline();
    }
    function updateName(kind){return tx.apply(null,{arrival:["Arrived in the feed","进入新闻流"],amendment:["Report amended","报道已修订"],removal:["Left the current feed","离开当前新闻流"],return:["Available again","再次可用"]}[kind]);}
    function renderMonitor(){
      renderResearchSummary();
      rebuildResearch($("ndMonitorChoices"),function(fragment){
        [[prefs.views,"v:",tx("Saved search","已保存搜索")],[prefs.research.investigations,"i:",tx("Investigation","研究专题")]].forEach(function(group){group[0].forEach(function(item){var row=el("label","nd-monitor-choice"),check=researchFocus(el("input",""),"watch-"+group[1]+item.id);check.type="checkbox";check.checked=prefs.research.watching.includes(group[1]+item.id);check.addEventListener("change",function(){toggleWatch(group[1]+item.id);});var text=el("span","",item.name);text.appendChild(el("small","",group[2]));row.append(check,text);fragment.appendChild(row);});});
        if(!prefs.views.length&&!prefs.research.investigations.length)fragment.appendChild(el("p","nd-note",tx("Save a search or create an investigation to choose what matters here.","保存搜索或创建研究专题，选择在此关注的内容。")));
      });
      rebuildResearch($("ndMonitorItems"),function(fragment){
        if(!prefs.research.updates.length){var empty=el("div","nd-research-empty");empty.append(el("h3","",tx("A quiet starting point","安静的起点")),el("p","",tx("Existing reports do not create alerts. Changes to your monitored selections will appear here as the desk receives them.","现有报道不会触发提醒。新闻台收到所监测内容的变化时，更新将出现在这里。")));fragment.appendChild(empty);return;}
        var list=el("ol","nd-monitor-list");prefs.research.updates.forEach(function(update){
          var r=researchStory(update.id),row=el("li","nd-monitor-item");row.dataset.updateId=String(update.n);row.dataset.storyId=update.id;row.dataset.kind=update.kind;row.dataset.read=String(update.read);
          var meta=el("div","nd-monitor-item-meta");meta.append(el("strong","",updateName(update.kind)),el("time","",fullTime(new Date(update.at).toISOString())));meta.lastChild.dateTime=new Date(update.at).toISOString();row.appendChild(meta);
          row.appendChild(r?articleLanguage(el("h3","",title(r)),r,!!r.titleZh):el("h3","",tx("Report reference unavailable","报道引用暂不可用")));
          row.appendChild(el("p","nd-note",update.targets.map(watchName).join(" · ")));
          if(update.kind==="removal")row.appendChild(el("p","nd-note",tx("The report left a feed update. This does not establish a withdrawal; it may have left the retained window.","此报道离开了已接收的新闻流。这并不证明报道已被撤回，也可能是超出保留时间范围。")));
          else if(!r)row.appendChild(el("p","nd-note",tx("This reference has no report text in the current authorized feed.","当前已授权新闻流中没有此引用的报道内容。")));
          var actions=el("div","nd-research-actions");if(r)actions.appendChild(researchFocus(button(researchIndex.has(update.id)?tx("Read current report","阅读当前报道"):tx("Read retained report","阅读留存报道"),function(){readResearchStory(update.id);},"nd-btn nd-btn-quiet"),"update-open-"+update.n));
          actions.appendChild(researchFocus(button(update.read?tx("Mark unread","标为未读"):tx("Mark read","标为已读"),function(){update.read=!update.read;persist();renderMonitor();},"nd-btn nd-btn-quiet"),"update-read-"+update.n));row.appendChild(actions);list.appendChild(row);
        });fragment.appendChild(list);
      });
    }
    function clearHistory(status,dropDescriptor){
      retained.generation++;if(retained.controller)retained.controller.abort();retained.controller=null;retained.loading=false;retained.rows=[];retained.index.clear();retained.matched=0;retained.next=null;retained.status=status;retained.waitingRevision=null;
      if(dropDescriptor){retained.descriptor={state:"unavailable"};retained.query=null;$("ndHistoryForm").reset();$("ndHistoryFeed").replaceChildren(el("option","",tx("Any feed","所有新闻流")));$("ndHistoryFeed").firstChild.value="";["ndHistoryBounds","ndHistoryStatus","ndHistoryQuerySummary"].forEach(function(id){$(id).textContent="";});$("ndHistoryQuerySummary").hidden=true;}
      $("ndHistoryResults").replaceChildren();$("ndHistoryMore").hidden=true;$("ndHistoryMore").disabled=true;
    }
    function acceptHistoryDescriptor(raw){
      var next=research.historyDescriptor(raw),before=retained.descriptor,changed=JSON.stringify(before)!==JSON.stringify(next),used=!!retained.query||retained.loading||retained.rows.length;
      if(changed){clearHistory(next.state==="available"?(used?"stale":"idle"):"unavailable");retained.descriptor=next;}
      else if(retained.waitingRevision&&next.state==="available"){retained.waitingRevision=null;retained.status="stale";} // A fresh accepted snapshot permits a deliberate retry, including a reverted collection.
    }
    function historyFormQuery(){
      function date(id){var value=$(id).value;if(!value)return null;var n=Date.parse(value);return Number.isFinite(n)?new Date(n).toISOString():"invalid";}
      return research.historyQuery({q:$("ndHistoryQuery").value,source:$("ndHistorySource").value,feed_id:$("ndHistoryFeed").value,category:$("ndHistoryCategory").value,language:$("ndHistoryLanguage").value,from_at:date("ndHistoryFrom"),to_at:date("ndHistoryTo"),limit:50});
    }
    async function fetchHistory(more){
      if(!liveReady||authPaused||retained.descriptor.state!=="available"||retained.waitingRevision)return;
      var query=more?retained.query:historyFormQuery(),cursor=more?retained.next:null;if(more&&(!cursor||retained.loading))return;
      if(!query){clearHistory("invalid");renderResearch();return;}
      if(!more)clearHistory("loading");else{retained.generation++;if(retained.controller)retained.controller.abort();}
      var issued=retained.generation,descriptor=retained.descriptor,controller=new win.AbortController();retained.controller=controller;retained.query=query;retained.loading=true;retained.status="loading";
      var params=new URLSearchParams();Object.keys(query).forEach(function(key){if(query[key]!==null&&query[key]!=="")params.set(key,String(query[key]));});if(cursor)params.set("cursor",cursor);renderResearch();
      try{
        var page=await getProtectedJSON("/api/news-desk/history?"+params.toString(),null,controller);
        if(issued!==retained.generation||disposed)return;
        if(typeof page.revision==="string"&&/^[0-9a-f]{64}$/.test(page.revision)&&page.revision!==descriptor.revision){var waiting=page.revision;clearHistory("stale");retained.waitingRevision=waiting;renderResearch();return;}
        if(!research.validHistoryPage(page,descriptor,query))throw new Error("history schema");
        var rows=page.stories.map(function(raw){return normalize(raw,"retained");});if(rows.some(function(r,index){return !r||r.id!==page.stories[index].id;}))throw new Error("history display");
        if(more&&(rows.some(function(r){return retained.index.has(r.id);})||page.next_cursor===cursor||page.matched_count!==retained.matched))throw new Error("history cursor");
        var total=(more?retained.rows.length:0)+rows.length;
        if(total>descriptor.bounds.max_stories||total>page.matched_count||page.next_cursor===null&&total!==page.matched_count)throw new Error("history size");
        retained.rows=more?retained.rows.concat(rows):rows;retained.index=new Map(retained.rows.map(function(r){return[r.id,r];}));retained.next=page.next_cursor;retained.matched=page.matched_count;retained.status=retained.rows.length?"ready":"empty";
      }catch(e){
        if(issued!==retained.generation||disposed)return;
        if(e.status===401||e.status===403){authPaused=true;closeStream();win.clearTimeout(timer);timer=0;clearProtected();setConnection("restricted","Sign in for live","登录查看实时新闻");banner(tx("Sign in again to read protected reporting.","请重新登录以阅读需要授权的报道。"),true,false);return;}
        clearHistory(e.status===409||e.status===400?"stale":e.status===503?"unavailable":"error");renderResearch();
      }finally{if(issued===retained.generation){retained.loading=false;retained.controller=null;renderResearch();}}
    }
    function historyReportBody(parent,r){
      clockList(parent,r);var brief=zh()&&r.briefZh?r.briefZh:r.brief;
      var sectionNode=el("section","nd-section");sectionNode.append(el("h4","",tx("Available brief","现有简报")),articleLanguage(el("p","",brief&&brief!==title(r)?brief:tx("A separate brief is not available. Read the original for the full account.","暂无独立简报。请阅读原文了解完整内容。")),r,!!r.briefZh));parent.appendChild(sectionNode);
      evidence(parent,r);comparisonHistory(parent,r);if(r.raw.attribution)parent.appendChild(el("p","nd-note",strip(r.raw.attribution)));var terms=safeURL(r.raw.source_use_url);if(terms)parent.appendChild(link(tx("Source terms","来源条款"),terms,"nd-note"));researchLinks(parent,"retained-"+r.id);
    }
    function renderHistory(){
      var descriptor=retained.descriptor,available=liveReady&&descriptor.state==="available",count=compareIds.length;
      $("ndHistoryBounds").textContent=available?tx("A rolling collection: up to ","滚动保留范围：最多 ")+descriptor.bounds.retention_hours+tx(" hours and "," 小时、")+descriptor.bounds.max_stories+tx(" reports. "," 条报道。 ")+descriptor.displayable_count+tx(" can currently be displayed; "," 条当前可展示；")+descriptor.excluded_count+tx(" cannot be displayed."," 条不可展示。"):tx("Retained reporting is not currently available. Its collection and display limits will be shown when the desk supplies them.","近期留存报道当前不可用。新闻台提供数据后，将显示保留范围与展示限制。");
      var messages={idle:["Choose a phrase or filters, then search the retained collection.","选择短语或筛选条件，然后搜索留存报道。"],loading:["Searching retained reporting…","正在搜索留存报道…"],stale:["Retained reporting changed. Restart the search to read the current versions.","留存报道已发生变化。请重新搜索以阅读当前版本。"],unavailable:["The retained collection is unavailable. Try again when the desk is available.","留存报道当前不可用。请在新闻台恢复后重试。"],error:["The search could not be completed. Check the connection and try again.","搜索未能完成。请检查连接并重试。"],invalid:["Check the filters and date range. The start must be earlier than the end.","请检查筛选条件及日期范围。起始时间必须早于截止时间。"],restricted:["Sign in again to search retained reporting.","请重新登录以搜索留存报道。"],paused:["Search paused. Submit it again when you are ready.","搜索已暂停。准备好后可重新提交。"],empty:["No retained reports match this search.","没有匹配此搜索的留存报道。"]};
      $("ndHistoryStatus").textContent=retained.waitingRevision?tx("A newer collection is available. Waiting for the live feed before you can restart this search.","已有更新的留存报道。等待实时新闻流同步后，即可重新搜索。"):retained.status==="ready"?retained.rows.length+" / "+retained.matched+" "+tx("matching reports loaded","条匹配报道已载入"):tx.apply(null,messages[retained.status]||messages.idle);
      $("ndHistorySearch").disabled=!available||!!retained.waitingRevision;$("ndHistoryMore").hidden=!retained.next;$("ndHistoryMore").disabled=retained.loading||!available||!!retained.waitingRevision;
      $("ndHistoryRestart").hidden=!["stale","error","unavailable","paused"].includes(retained.status);$("ndHistoryRestart").disabled=!available||!!retained.waitingRevision;
      $("ndHistoryCompare").disabled=count<2||!liveReady;$("ndHistoryCompare").textContent=tx("Compare selection","对照阅读已选报道")+(count?" ("+count+")":"");$("ndHistoryKeep").disabled=!count||!liveReady;
      var query=retained.query;$("ndHistoryQuerySummary").hidden=!query;$("ndHistoryQuerySummary").textContent="";if(query){var pieces=[];if(query.q)pieces.push(tx("Literal text: ","原样文字：")+query.q);if(query.source)pieces.push(tx("Publisher or host: ","发布者或主机名：")+query.source);if(query.feed_id)pieces.push(tx("Feed: ","新闻流：")+query.feed_id);if(query.category)pieces.push(tx("Category: ","分类：")+(CATEGORY[query.category]?tx.apply(null,CATEGORY[query.category]):query.category));if(query.language)pieces.push(tx("Language: ","语言：")+query.language);if(query.from_at)pieces.push(tx("Recorded from ","收录起始 ")+fullTime(query.from_at));if(query.to_at)pieces.push(tx("Recorded before ","收录截止（不含）")+fullTime(query.to_at));$("ndHistoryQuerySummary").textContent=pieces.join(" · ")||tx("All available retained reports","所有可用留存报道");}
      var feed=$("ndHistoryFeed");if(doc.activeElement!==feed){var chosen=feed.value,seen=new Set(),options=[{id:"",label:tx("Any feed","所有新闻流")}];sourceHealth.forEach(function(item){if(!item||typeof item.id!=="string"||!item.id||item.id.length>160||seen.has(item.id))return;seen.add(item.id);options.push({id:item.id,label:strip(item.label||item.name||item.publisher)||item.id});});if(chosen&&!seen.has(chosen))options.push({id:chosen,label:chosen});feed.replaceChildren();options.forEach(function(item){var option=el("option","",item.label);option.value=item.id;feed.appendChild(option);});feed.value=chosen;}
      rebuildResearch($("ndHistoryResults"),function(fragment,opened){
        retained.rows.forEach(function(r){
          var row=el("article","nd-history-row");row.dataset.storyId=r.id;row.appendChild(el("p","nd-history-meta",r.source+" · "+tx("Recorded ","收录 ")+fullTime(r.raw.accepted_revision_at||r.receivedAt)));row.appendChild(articleLanguage(el("h3","",title(r)),r,!!r.titleZh));
          var actions=el("div","nd-research-actions"),pick=researchFocus(button(compareIds.includes(r.id)?tx("Selected to compare","已选入对照阅读"):tx("Select to compare","选择对照阅读"),function(){toggleCompare(r.id);},"nd-btn"),"history-pick-"+r.id);pick.setAttribute("aria-pressed",String(compareIds.includes(r.id)));actions.appendChild(pick);actions.appendChild(researchFocus(button(tx("Keep reference","保存引用"),function(){openInvestigations([r.id]);},"nd-btn nd-btn-quiet"),"history-keep-"+r.id));if(r.url)actions.appendChild(researchFocus(link(tx("Read original ↗","阅读原文 ↗"),r.url,"nd-btn nd-btn-quiet"),"history-original-"+r.id));row.appendChild(actions);
          var details=researchFocus(el("details","nd-history-report"),"history-report-"+r.id),summary=researchFocus(el("summary","",tx("Brief, sources and changes","简报、来源与变更")),"history-details-"+r.id),content=el("div","nd-history-report-body");details.append(summary,content);
          details.addEventListener("toggle",function(){if(details.open&&retained.index.get(r.id)===r&&!content.childNodes.length)historyReportBody(content,r);else if(!details.open)content.replaceChildren();});
          if(opened.has(details.dataset.researchFocus)){details.open=true;historyReportBody(content,r);}row.appendChild(details);fragment.appendChild(row);
        });
      });
    }
    function openHistory(id){renderHistory();openDialog("ndHistory");if(id){var row=Array.from($("ndHistoryResults").children).find(function(n){return n.dataset.storyId===id;});if(row){row.querySelector("details").open=true;row.querySelector("summary").focus({preventScroll:true});row.scrollIntoView({block:"nearest",behavior:"auto"});}}}
    function renderResearch(){renderResearchSummary();if($("ndCompare").open)renderComparison();if($("ndInvestigations").open)renderInvestigations();if($("ndMonitor").open)renderMonitor();if($("ndHistory").open)renderHistory();}
    function readResearchStory(id){if(!researchStory(id))return;var live=researchIndex.has(id);["ndMonitor","ndInvestigations","ndCompare","ndHistory"].forEach(function(dialog){if($(dialog).open)closeDialog($(dialog));});if(live)openStory(id,win.matchMedia("(max-width:1050px)").matches?$("ndWorkspaceOpen"):$("ndInvestigationsOpen"));else openHistory(id);}
    function researchDialog(d){return ["ndCompare","ndInvestigations","ndMonitor","ndHistory"].includes(d.id);}
    function finishResearchDialog(d){
      if(!researchDialog(d)||d.open)return;
      var returnTo=researchReturns.get(d.id);researchReturns.delete(d.id);
      if(d.id==="ndCompare")$("ndCompareReports").replaceChildren();
      if(d.id==="ndInvestigations"){$("ndInvestigationList").replaceChildren();$("ndInvestigationReports").replaceChildren();$("ndInvestigationAvailability").textContent="";$("ndInvestigationCurrent").hidden=true;pendingInvestigationIds=[];}
      if(d.id==="ndMonitor"){$("ndMonitorItems").replaceChildren();$("ndMonitorChoices").replaceChildren();}
      if(d.id==="ndHistory"){if(retained.loading){retained.generation++;if(retained.controller)retained.controller.abort();retained.controller=null;retained.loading=false;retained.status="paused";}$("ndHistoryResults").replaceChildren();}
      if(returnTo){var target=returnTo.node;if(!target||!target.isConnected||target.closest("dialog")&&!target.closest("dialog").open){target=returnTo.key&&Array.from(doc.querySelectorAll("[data-research-focus]")).find(function(n){return n.dataset.researchFocus===returnTo.key&&(!n.closest("dialog")||n.closest("dialog").open);});}
        if(!target&&returnTo.action)target=Array.from($("ndDetailBody").querySelectorAll("[data-action]")).find(function(n){return n.dataset.action===returnTo.action;});
        if(!target&&returnTo.storyId){var row=Array.from(doc.querySelectorAll(".nd-row")).find(function(n){return n.dataset.id===returnTo.storyId;});target=row&&row.querySelector(".nd-title");}
        (target||$("ndDetail").getAttribute("aria-modal")==="true"&&$("ndDetailClose")||$("ndFeedPanel")).focus({preventScroll:true});}
    }
    function clearResearchProtected(){
      compareIds=[];pendingInvestigationIds=[];researchIndex.clear();researchWarmed=false;prefs.research.records=[];prefs.research.updates=[];persist();
      clearHistory("restricted",true);["ndHistory","ndMonitor","ndInvestigations","ndCompare"].forEach(function(id){var dialog=$(id);if(dialog.open)closeDialog(dialog);else finishResearchDialog(dialog);});researchReturns.clear();
    }
    function blockingDialog(n){
      if(n.id==="ndDetail"||n.hidden||n.getAttribute("aria-hidden")==="true")return false;
      var style=win.getComputedStyle(n);return style.display!=="none"&&style.visibility!=="hidden"&&style.visibility!=="collapse";
    }
    function renderConnection(){
      var label=tx.apply(null,connectionLabel);
      ["ndConnection","ndConnectionMobile"].forEach(function(id){var node=$(id);if(node){node.dataset.state=mode;node.textContent=label;}});
      renderResearchSummary();
      if($("ndCoverage").open)renderCoverage();
    }
    function setConnection(state,en,cn){mode=state;connectionLabel=[en,cn];renderConnection();}
    function banner(message,auth,retry){$("ndBanner").hidden=!message;$("ndBannerText").textContent=message||"";$("ndSignIn").hidden=!auth;$("ndRetry").hidden=!retry;}
    function accept(payload){
      if(!validSnapshot(payload))throw new Error("schema");
      // A saved stable ID must not disappear merely because feed display merges
      // two reports with the same URL or headline. This index is session-only.
      var priorResearch=researchIndex;researchIndex=new Map();payload.stories.forEach(function(raw){var r=normalize(raw,"desk");if(r&&research.id(raw.id)===r.id)researchIndex.set(r.id,r);});
      var previous=latest,first=!liveReady;latest=combine(payload.stories,[]);health=payload.health||{};sourceHealth=Array.isArray(payload.source_health)?payload.source_health:[];liveReady=true;
      var priorById=new Map(previous.map(function(r){return[r.id,r];})),changedIds=new Set(latest.filter(function(r){var old=priorById.get(r.id);return old&&fingerprint(old)!==fingerprint(r);}).map(function(r){return r.id;}));
      researchIndex.forEach(function(r,id){var old=priorResearch.get(id);if(old&&fingerprint(old)!==fingerprint(r))changedIds.add(id);});
      acceptHistoryDescriptor(payload.retained_history);
      if(changedIds.size){prefs.read=prefs.read.filter(function(id){return !changedIds.has(id);});persist();}
      latest.forEach(function(r){deskAliases.add(r.id);deskAliases.add(canonicalURL(r.url));deskAliases.add(r.title.toLowerCase());});
      var combined=combinedRows(latest);pending=difference(visible,combined);
      var currentById=new Map(combined.map(function(r){return[r.id,r];}));
      visible=visible.filter(function(r){return !deskAliases.has(r.id)||currentById.has(r.id);}).map(function(r){return currentById.get(r.id)||r;});
      if(selected){
        var old=priorResearch.get(selected)||previous.find(function(r){return r.id===selected;}),current=researchIndex.get(selected)||latest.find(function(r){return r.id===selected;});
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
      observeResearch(first||!researchWarmed,changedIds);renderResearch();
      if($("ndCoverage").open)renderCoverage();
      if(requestedStoryId){
        if(researchIndex.has(requestedStoryId)||combined.some(function(r){return r.id===requestedStoryId;}))openStory(requestedStoryId);
        else if(first){$("ndDetail").dataset.open="true";$("ndDetailBody").replaceChildren(el("div","nd-empty",tx("This shared story is outside the loaded window or no longer available. Search for its subject or open another current report.","此分享报道已超出载入范围或不可用。请搜索相关主题或打开当前报道。")));syncDetailModal();}
      }
      if(!requestedStoryId&&!selected&&shown.length&&!win.matchMedia("(max-width:760px)").matches)openStory(shown[0].id);
    }
    function schedule(ms){win.clearTimeout(timer);if(!disposed&&!authPaused&&!doc.hidden)timer=win.setTimeout(function(){timer=0;connect();},ms);}
    function closeStream(){generation++;win.clearTimeout(handshake);if(stream){stream.close();stream=null;}}
    async function getProtectedJSON(url,validate,controller){
      controller=controller||new win.AbortController();var timeout;
      var deadline=new Promise(function(resolve,reject){timeout=win.setTimeout(function(){controller.abort();reject(new Error("request deadline"));},10000);});
      var request=(async function(){
        var response=await win.fetch(url,{credentials:"same-origin",cache:"no-store",signal:controller.signal,headers:{Accept:"application/json"}});
        if(!response.ok){var error=new Error("http");error.status=response.status;throw error;}
        var content=await response.text();if(content.length>4194304)throw new Error("size");
        var p=JSON.parse(content);if(validate&&!validate(p))throw new Error("schema");return p;
      })();
      try{return await Promise.race([request,deadline]);}finally{win.clearTimeout(timeout);}
    }
    async function getSnapshot(url){return getProtectedJSON(url,validSnapshot);}
    async function connect(){
      if(inflight||disposed||authPaused||doc.hidden)return;inflight=true;closeStream();var issued=generation;
      try{
        var p,legacy=false;
        try{p=await getSnapshot("/api/news-desk/snapshot");}catch(e){if(e.status===404){legacy=true;p=await getSnapshot("live/intelligence.json");}else throw e;}
        if(issued!==generation||disposed||doc.hidden)return;
        accept(p);failures=0;banner("",false,false);
        if(!streamAvailable&&Date.now()>=streamRetryAt){streamAvailable=true;streamFailures=0;}
        if(legacy||!win.EventSource||!streamAvailable){setConnection("polling","Auto refresh · 10s","自动刷新 · 10秒");schedule(10000);return;}
        setConnection("connecting","Connecting","正在连接");stream=new win.EventSource("/api/news-desk/stream",{withCredentials:true});
        handshake=win.setTimeout(function(){if(issued!==generation)return;streamAvailable=false;streamRetryAt=Date.now()+300000;closeStream();setConnection("polling","Auto refresh · 10s","自动刷新 · 10秒");schedule(10000);},12000);
        stream.addEventListener("snapshot",function(e){if(issued!==generation)return;win.clearTimeout(handshake);try{accept(JSON.parse(e.data));streamFailures=0;setConnection("connected","Stream connected","新闻流已连接");banner("",false,false);}catch(_){closeStream();setConnection("degraded","Feed interrupted","新闻流中断");banner(tx("A news update could not be read. Your current stories remain available.","暂时无法读取新闻更新，当前报道仍可阅读。"),false,true);schedule(5000);}});
        stream.addEventListener("heartbeat",function(){if(issued===generation)lastTransportAt=Date.now();});
        stream.addEventListener("reconnect",function(){if(issued!==generation)return;closeStream();schedule(250);});
        stream.addEventListener("unavailable",function(){if(issued!==generation)return;closeStream();setConnection("degraded","Feed unavailable","新闻流不可用");banner(tx("Live updates are unavailable. The last loaded reporting remains visible.","实时更新暂不可用，已载入报道仍可阅读。"),false,true);schedule(5000);});
        stream.onerror=function(){if(issued!==generation)return;streamFailures++;if(streamFailures>=3){streamAvailable=false;streamRetryAt=Date.now()+300000;}closeStream();setConnection("degraded","Reconnecting","正在重连");banner(tx("Connection interrupted. Reconnecting to recover the latest feed.","连接已中断，正在重连并恢复最新新闻流。"),false,true);schedule(streamAvailable?Math.min(15000,2000*Math.pow(2,streamFailures-1)):10000);};
      }catch(e){
        if(issued!==generation||disposed||doc.hidden)return;
        failures++;var auth=e.status===401||e.status===403;
        if(auth)clearProtected();
        setConnection(auth?"restricted":"degraded",auth?"Sign in for live":win.navigator.onLine===false?"Offline":"Updates unavailable",auth?"登录查看实时新闻":win.navigator.onLine===false?"离线":"更新不可用");
        banner(auth?tx("Sign in to connect to live desk updates. Browse the available edition below.","登录以连接实时新闻台；仍可浏览下方已载入报道。"):tx("Live updates could not be loaded. The last available reporting remains readable.","无法载入实时更新，最新可用报道仍可阅读。"),auth,!auth);
        if(!auth)schedule(Math.min(30000,3000*Math.pow(2,Math.min(failures,4))));
      }finally{inflight=false;if(issued!==generation&&!doc.hidden&&!disposed&&!authPaused&&!stream&&!timer)schedule(0);}
    }
    function clearProtected(){latest=[];health={};sourceHealth=[];deskAliases.clear();lastTransportAt=0;liveReady=false;clearResearchProtected();closeStory();lastFocus=null;visible=combine([],seed.stories);pending=0;$("ndUpdates").hidden=true;selected=null;$("ndDetailBody").replaceChildren(el("div","nd-empty",tx("Sign in again to read live desk stories.","请重新登录以阅读实时新闻台报道。")));$("ndCoverageBody").replaceChildren();render();if($("ndCoverage").open)renderCoverage();}
    function openDialog(id,trigger){var d=$(id);if(d.open){if(researchDialog(d)){var stack=Array.from(researchReturns.keys());stack.slice(stack.indexOf(id)+1).reverse().forEach(function(above){if($(above).open)closeDialog($(above));});d.querySelector("[data-close-dialog]").focus();}return;}if(researchDialog(d)){var active=trigger||doc.activeElement,row=active.closest&&active.closest(".nd-row");researchReturns.set(id,{node:active,key:active.dataset.researchFocus,action:active.dataset.action,storyId:row&&row.dataset.id});}if(typeof d.showModal==="function")d.showModal();else d.setAttribute("open","");if(researchDialog(d))d.querySelector("[data-close-dialog]").focus();}
    function closeDialog(d){if(typeof d.close==="function")d.close();else d.removeAttribute("open");finishResearchDialog(d);}
    function renderCoverage(){
      rebuildResearch($("ndCoverageBody"),function(body){
      section(body,tx("Delivery connection","传输连接"),$("ndConnection").textContent);
      body.appendChild(el("p","nd-note",tx("A connected stream means this page can receive desk changes. Publisher timing, collection cadence and source availability determine how fresh the reporting is.","新闻流已连接表示页面能够接收新闻台的变化。报道时效取决于发布者时间、采集频率与来源可用性。")));
      section(body,tx("Latest source publication","最新来源发布时间"),$("ndFreshness").textContent);
      var rows=liveReady?researchRows():combine([],seed.stories),counts=new Map(),feedCounts=new Map();rows.forEach(function(r){counts.set(r.source,(counts.get(r.source)||0)+1);var feed=strip(r.raw.feed_id);if(feed)feedCounts.set(feed,(feedCounts.get(feed)||0)+1);});
      var overview=el("div","nd-coverage-overview");[[rows.length,liveReady?tx("Live reports loaded","已载入实时报道"):tx("Edition reports loaded","已载入版本报道")],[counts.size,tx("Publisher labels","发布者标签")],[feedCounts.size,tx("Named collection feeds","已标识采集新闻流")]].forEach(function(pair){var box=el("div","");box.append(el("strong","",pair[0]),el("span","",pair[1]));overview.appendChild(box);});body.appendChild(overview);
      var cohorts=el("div","nd-coverage-cohorts");
      [["language",tx("Reported languages","所报语言")],["category",tx("Reported categories","所报分类")],["feed_id",tx("Collection feeds","采集新闻流")],["timestamp_quality",tx("Timestamp labels","时间戳标签")]].forEach(function(pair){var values=new Map();rows.forEach(function(r){var value=strip(r.raw[pair[0]])||tx("Not supplied","未提供");values.set(value,(values.get(value)||0)+1);});var detail=researchFocus(el("details","nd-coverage-cohort"),"coverage-"+pair[0]);detail.appendChild(researchFocus(el("summary","",pair[1]),"coverage-toggle-"+pair[0]));Array.from(values).sort(function(a,b){return b[1]-a[1];}).slice(0,40).forEach(function(entry){var line=el("div","nd-coverage-row");line.append(el("span","",entry[0]),el("span","",entry[1]));detail.appendChild(line);});if(!values.size)detail.appendChild(el("p","nd-note",tx("No loaded reports","尚未载入报道")));cohorts.appendChild(detail);});body.appendChild(cohorts);
      var heading=el("h3","nd-nav-heading",tx("Sources in the loaded window","已载入时间范围内的来源"));body.appendChild(heading);
      Array.from(counts).sort(function(a,b){return b[1]-a[1];}).slice(0,40).forEach(function(e){var row=el("div","nd-coverage-row");row.append(el("span","",e[0]),el("span","",e[1]+" "+tx("stories","条报道")));body.appendChild(row);});
      body.appendChild(el("p","nd-note",tx("These are sources represented in the loaded feed, not a count of connected or independently verified sources. Paid source availability follows the existing account and display permissions.","此处列出已载入新闻流中的来源，并非已连接或已独立核实的来源数量。付费来源的可用性遵循现有账户与展示权限。")));
      if(sourceHealth.length){
        body.appendChild(el("h3","nd-nav-heading",tx("Collection health","采集健康状态")));
        sourceHealth.forEach(function(item){
          if(!item||typeof item!=="object")return;
          var card=el("div","nd-receipt"),checked=stamp(item.last_fetch_success_at),stale=checked!==null&&Date.now()-checked>Math.max(900000,Number(item.poll_seconds||120)*4000);
          var state=item.enabled===false||item.status==="held"?tx("Not collecting","未在采集"):item.status==="degraded"?tx("Collection needs attention","采集需要关注"):checked!==null&&checked<=Date.now()?(stale?tx("Previous check is old","上次检查已较久"):tx("Previously checked","此前已检查")):tx("Unknown","未知");
          card.appendChild(el("strong","",strip(item.publisher)||strip(item.id)||tx("Source not supplied","未提供来源")));card.appendChild(el("small","",state+(checked!==null?" · "+age(item.last_fetch_success_at,Date.now(),zh()):"")));
          if(item.last_accepted_at)card.appendChild(el("small","",tx("Last new or amended report ","最近新增或修订报道 ")+fullTime(item.last_accepted_at)));
          var outcomes={accepted:["New or amended reporting accepted","已收录新增或修订报道"],unchanged:["No reporting changes","报道未变化"],empty:["Empty source response","来源响应为空"],filtered:["No eligible reports","无符合条件的报道"],fetch_failed:["Fetch failed","采集失败"],rejected:["Response rejected","响应被拒绝"],acceptance_failed:["Reporting could not be accepted","报道未能收录"],unknown:["Outcome unknown","结果未知"]};
          card.appendChild(el("small","",tx("Last outcome · ","最近结果 · ")+tx.apply(null,Object.keys(outcomes).includes(item.last_outcome)?outcomes[item.last_outcome]:outcomes.unknown)));
          var detail=researchFocus(el("details","nd-coverage-source-details"),"coverage-source-"+item.id);detail.appendChild(researchFocus(el("summary","",tx("Collection details","采集详情")),"coverage-source-toggle-"+item.id));
          function valueLine(label,value){var line=el("div","nd-coverage-row");line.append(el("span","",label),el("span","",value));detail.appendChild(line);}
          valueLine(tx("Loaded reports for this feed","此新闻流已载入报道"),typeof item.id==="string"&&item.id.trim()?feedCounts.get(item.id)||0:tx("Unknown","未知"));
          [["last_observed_item_count",tx("Items observed","已观察条目")],["last_eligible_item_count",tx("Eligible items","符合条件条目")],["last_filtered_item_count",tx("Filtered items","已过滤条目")],["last_duplicate_item_count",tx("Duplicate items","重复条目")],["last_changed_item_count",tx("Changed items","变化条目")]].forEach(function(pair){var value=item[pair[0]];valueLine(pair[1],Number.isSafeInteger(value)&&value>=0?value:tx("Unknown","未知"));});
          [["last_attempt_at",tx("Scheduled check","计划检查时刻")],["last_attempt_started_at",tx("Attempt started","采集开始时刻")],["last_attempt_completed_at",tx("Attempt completed","采集完成时刻")]].forEach(function(pair){valueLine(pair[1],fullTime(item[pair[0]]));});
          valueLine(tx("Fetch and parse duration","获取与解析耗时"),Number.isFinite(item.last_attempt_duration_ms)&&item.last_attempt_duration_ms>=0?Math.round(item.last_attempt_duration_ms)+" ms":tx("Unknown","未知"));
          valueLine(tx("Last HTTP response","最近 HTTP 响应"),Number.isSafeInteger(item.last_http_status)&&item.last_http_status>=100&&item.last_http_status<=599?item.last_http_status:tx("Unknown","未知"));
          if(typeof item.last_error_code==="string"&&/^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(item.last_error_code))valueLine(tx("Collection error code","采集错误代码"),item.last_error_code);
          var regions=Array.isArray(item.coverage_regions)?item.coverage_regions.filter(function(v){return typeof v==="string";}).slice(0,12):[];if(regions.length)valueLine(tx("Configured regional scope","配置的地区范围"),regions.join(" · "));card.appendChild(detail);
          body.appendChild(card);
        });
        body.appendChild(el("p","nd-note",tx("A previous check does not establish that a source is online now. Configured regions describe feed or query scope, not measured geographic completeness. Missing outcomes and counters remain unknown.","此前的检查并不能证明来源当前在线。配置地区描述新闻流或查询范围，并非实际地区覆盖完整度。缺失的结果与计数均保留为未知。")));
      }
      if(health.last_source_published_at)section(body,tx("Desk source timestamp","新闻台来源时间"),fullTime(health.last_source_published_at));
      });
    }
    function renderViews(){
      var box=$("ndSavedViews");box.replaceChildren();$("ndSavedViewsMobile").replaceChildren();
      prefs.views.filter(function(v){return v&&typeof v.name==="string"&&v.filters&&typeof v.filters==="object";}).forEach(function(v,index){
        var line=el("div","nd-saved-view"),b=button(v.name,function(){filters=Object.assign({},DEFAULT_FILTERS,v.filters);limit=60;render();saveFiltersToURL();},"nd-btn nd-btn-quiet");
        line.appendChild(b);var remove=button("×",function(){prefs.views.splice(index,1);resetResearchBaseline();renderViews();},"nd-btn nd-btn-quiet");remove.setAttribute("aria-label",tx("Delete view ","删除视图 ")+v.name);line.appendChild(remove);box.appendChild(line);
        $("ndSavedViewsMobile").appendChild(button(v.name,function(){filters=Object.assign({},DEFAULT_FILTERS,v.filters);limit=60;closeDialog($("ndWorkspace"));render();saveFiltersToURL();},"nd-btn"));
      });
    }
    function reset(){filters=Object.assign({},DEFAULT_FILTERS);limit=60;render();saveFiltersToURL();}
    function refreshLanguage(){
      doc.querySelectorAll("[data-placeholder-zh]").forEach(function(n){if(!n.dataset.placeholderEn)n.dataset.placeholderEn=n.placeholder;n.placeholder=zh()?n.dataset.placeholderZh:n.dataset.placeholderEn;});
      doc.querySelectorAll("[data-label-zh]").forEach(function(n){if(!n.dataset.labelEn)n.dataset.labelEn=n.getAttribute("aria-label");n.setAttribute("aria-label",zh()?n.dataset.labelZh:n.dataset.labelEn);});
      doc.querySelectorAll("option[data-en]").forEach(function(n){n.textContent=zh()?n.dataset.zh:n.dataset.en;});
      renderConnection();render();if(selected)renderDetail();if($("ndCoverage").open)renderCoverage();renderViews();renderResearch();
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
    $("ndViewForm").addEventListener("submit",function(e){e.preventDefault();var name=research.label($("ndViewName").value,40);if(!name)return;prefs.views.push({id:localId("view"),name:name,filters:research.cleanFilters(filters,DEFAULT_FILTERS)});prefs.views=prefs.views.slice(-12);resetResearchBaseline();renderViews();closeDialog($("ndViewDialog"));});
    $("ndCompareOpen").addEventListener("click",openComparison);
    $("ndCompareClear").addEventListener("click",function(){compareIds=[];render();if(selected)renderDetail();renderResearch();announce(tx("Comparison selection cleared","已清除对照阅读选择"));});
    $("ndCompareRelation").addEventListener("change",function(){compareRelation=research.relations.includes(this.value)?this.value:"question";});
    $("ndCompareSave").addEventListener("click",function(){openInvestigations(compareIds);});
    ["ndInvestigationsOpen","ndInvestigationsOpenMobile"].forEach(function(id){$(id).addEventListener("click",function(){if($("ndWorkspace").open){closeDialog($("ndWorkspace"));$("ndWorkspaceOpen").focus();}openInvestigations();});});
    ["ndMonitorOpen","ndMonitorOpenMobile"].forEach(function(id){$(id).addEventListener("click",function(){if($("ndWorkspace").open){closeDialog($("ndWorkspace"));$("ndWorkspaceOpen").focus();}renderMonitor();openDialog("ndMonitor");});});
    $("ndInvestigationForm").addEventListener("submit",function(e){
      e.preventDefault();var name=research.label($("ndInvestigationName").value,60);if(!name||prefs.research.investigations.length>=research.limits.investigations)return;
      var references=liveReady?selectedReferences():[],relation=references.length>=2&&references.length===compareIds.length&&references.every(function(id){return compareIds.includes(id);})?compareRelation:"question";
      var item={id:localId("case"),name:name,storyIds:references,relation:relation};prefs.research.investigations.push(item);investigationId=item.id;pendingInvestigationIds=[];$("ndInvestigationName").value="";resetResearchBaseline();renderInvestigations();announce(tx("Investigation created on this browser","已在此浏览器创建研究专题"));
    });
    $("ndInvestigationRenameForm").addEventListener("submit",function(e){e.preventDefault();var item=currentInvestigation(),name=research.label($("ndInvestigationRename").value,60);if(!item||!name)return;item.name=name;persist();renderResearch();announce(tx("Investigation renamed","已重命名研究专题"));});
    $("ndInvestigationRelation").addEventListener("change",function(){var item=currentInvestigation();if(item){item.relation=research.relations.includes(this.value)?this.value:"question";persist();}});
    $("ndInvestigationAdd").addEventListener("click",function(){var item=currentInvestigation();if(!item||!liveReady)return;var before=item.storyIds.length;item.storyIds=Array.from(new Set(item.storyIds.concat(selectedReferences()))).slice(0,research.limits.reports);pendingInvestigationIds=[];resetResearchBaseline();renderInvestigations();announce((item.storyIds.length-before)+" "+tx("references added","条引用已加入"));});
    $("ndInvestigationCompare").addEventListener("click",function(){var item=currentInvestigation();if(item)compareRelation=item.relation;openComparison();});
    $("ndInvestigationHistory").addEventListener("click",function(){openHistory();});
    $("ndInvestigationWatch").addEventListener("click",function(){var item=currentInvestigation();if(item){toggleWatch("i:"+item.id);announce(prefs.research.enabled?tx("Monitoring selection updated","已更新监测选择"):tx("Selection saved. Enable monitoring in the Updates inbox to begin.","已保存选择。请在更新收件箱中启用监测。"));}});
    $("ndInvestigationDelete").addEventListener("click",function(){if(!currentInvestigation())return;prefs.research.investigations=prefs.research.investigations.filter(function(item){return item.id!==investigationId;});investigationId=prefs.research.investigations[0]&&prefs.research.investigations[0].id;resetResearchBaseline();renderInvestigations();$("ndInvestigationName").focus();announce(tx("Investigation deleted; the reports are unchanged","已删除研究专题；报道内容未变更"));});
    $("ndMonitorEnable").addEventListener("click",function(){prefs.research.enabled=!prefs.research.enabled;resetResearchBaseline();});
    $("ndMonitorQuiet").addEventListener("click",function(){prefs.research.quiet=!prefs.research.quiet;persist();renderResearchSummary();});
    $("ndMonitorReadAll").addEventListener("click",function(){prefs.research.updates.forEach(function(update){update.read=true;});persist();renderMonitor();});
    $("ndMonitorReset").addEventListener("click",function(){prefs.research.updates=[];resetResearchBaseline();announce(tx("Inbox cleared. Current reports are the new starting point.","已清空收件箱。当前报道成为新的起点。"));});
    ["ndHistoryOpen","ndHistoryOpenMobile"].forEach(function(id){$(id).addEventListener("click",function(){if($("ndWorkspace").open){closeDialog($("ndWorkspace"));$("ndWorkspaceOpen").focus();}openHistory();});});
    $("ndHistoryForm").addEventListener("submit",function(e){e.preventDefault();fetchHistory(false);});
    $("ndHistoryMore").addEventListener("click",function(){fetchHistory(true);});
    $("ndHistoryRestart").addEventListener("click",function(){fetchHistory(false);});
    $("ndHistoryCompare").addEventListener("click",openComparison);
    $("ndHistoryKeep").addEventListener("click",function(){openInvestigations(compareIds);});
    ["ndCompare","ndInvestigations","ndMonitor","ndHistory"].forEach(function(id){$(id).addEventListener("close",function(){finishResearchDialog(this);});});
    // A qualified shell candidate owns embedded auth, including before INIT.
    // Keep the canonical link for standalone and modified-click navigation.
    ["ndSignIn","ndCompanySignIn"].forEach(function(id){
      var link=$(id);if(!link)return;
      link.addEventListener("click",function(e){
        var shell=win.MMXSharedShell;
        if(e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||!shell||typeof shell.openAuth!=="function")return;
        var target=(link.getAttribute("target")||"").toLowerCase();
        if(link.hasAttribute("download")||(target&&target!=="_self"))return;
        e.preventDefault();
        try{shell.openAuth("signin");}catch(_){/* The qualified shell still owns this action. */}
      });
    });
    $("ndRetry").addEventListener("click",function(){win.clearTimeout(timer);connect();});
    doc.querySelectorAll("[data-close-dialog]").forEach(function(b){b.addEventListener("click",function(){closeDialog(b.closest("dialog"));});});
    doc.addEventListener("keydown",function(e){
      var typing=/INPUT|TEXTAREA|SELECT/.test(doc.activeElement&&doc.activeElement.tagName)||doc.activeElement&&doc.activeElement.isContentEditable;
      var otherDialog=Array.from(doc.querySelectorAll('dialog[open],[role="dialog"]')).some(blockingDialog);
      if(e.key==="Escape"){if(!otherDialog&&selected)closeStory();return;}
      if(otherDialog)return;
      if($("ndDetail").getAttribute("aria-modal")==="true"&&e.key==="Tab"){
        var panel=$("ndDetail");
        var nodes=Array.from(panel.querySelectorAll("button,a[href]")).filter(function(n){return n.tabIndex>=0&&!n.matches(":disabled")&&!n.hidden&&!n.closest("[hidden],[inert],[aria-hidden='true']");});
        var first=nodes[0],last=nodes[nodes.length-1];
        if(!first){e.preventDefault();panel.tabIndex=-1;panel.focus();return;}
        if(!panel.contains(doc.activeElement)){e.preventDefault();(e.shiftKey?last:first).focus();return;}
        if(e.shiftKey&&doc.activeElement===first){e.preventDefault();last.focus();}
        else if(!e.shiftKey&&doc.activeElement===last){e.preventDefault();first.focus();}
        return;
      }
      if($("ndDetail").getAttribute("aria-modal")==="true"&&e.key!=="s")return;
      if(typing||e.ctrlKey||e.metaKey||e.altKey||otherDialog)return;
      if(e.key==="/"){e.preventDefault();$("ndSearch").focus();}
      if(e.key==="s"&&selected){e.preventDefault();toggleSaved(selected);}
      if((e.key==="j"||e.key==="k")&&shown.length){e.preventDefault();var index=shown.findIndex(function(r){return r.id===selected;}),next=Math.max(0,Math.min(shown.length-1,index+(e.key==="j"?1:-1)));var r=shown[next];if(next>=limit){limit=next+20;render();}var row=Array.from(doc.querySelectorAll(".nd-row")).find(function(n){return n.dataset.id===r.id;});openStory(r.id,row&&row.querySelector("button"));if(row)row.scrollIntoView({block:"nearest",behavior:"auto"});}
    });
    var breakpoint=win.matchMedia("(max-width:760px)");if(breakpoint.addEventListener)breakpoint.addEventListener("change",syncDetailModal);
    doc.addEventListener("langchange",refreshLanguage);
    doc.addEventListener("visibilitychange",function(){if(doc.hidden){closeStream();win.clearTimeout(timer);timer=0;if(retained.loading){retained.generation++;if(retained.controller)retained.controller.abort();retained.controller=null;retained.loading=false;retained.status="paused";}setConnection("paused","Paused in background","后台已暂停");}else connect();});
    win.addEventListener("online",connect);
    win.addEventListener("mdx-auth",function(event){
      var detail=event.detail||{};if(detail.event==="PREFS_SAVED")return;
      closeStream();win.clearTimeout(timer);timer=0;clearProtected();authPaused=!detail.user;
      if(authPaused){setConnection("restricted","Sign in for live","登录查看实时新闻");banner(tx("Sign in to connect to live desk updates. Browse the available edition below.","登录以连接实时新闻台；仍可浏览下方已载入报道。"),true,false);}
      else schedule(0);
    });
    win.addEventListener("pagehide",function(){disposed=true;closeStream();win.clearTimeout(timer);clearHistory("stale");renderResearch();});
    win.addEventListener("pageshow",function(e){if(e.persisted){disposed=false;connect();}});
    readURL();refreshLanguage();
    if(requestedStoryId&&visible.some(function(r){return r.id===requestedStoryId;}))openStory(requestedStoryId);
    if(!requestedStoryId&&!selected&&shown.length&&!win.matchMedia("(max-width:760px)").matches)openStory(shown[0].id);
    win.setInterval(freshness,15000);connect();
    return {accept:accept,getState:function(){return {filters:filters,pending:pending,mode:mode,selected:selected};}};
  }
  return {normalize:normalize,combine:combine,tokens:tokens,matchesTerms:matchesTerms,filterRows:filterRows,difference:difference,age:age,validSnapshot:validSnapshot,safeURL:safeURL,defaults:DEFAULT_FILTERS,mount:mount};
});
