/* China Evidence Desk: bounded, progressively enhanced research controls. No new telemetry. */
(function () {
  "use strict";
  const PAGE = 8, SCHEMA = "china_altdata.desk.v1";
  const finite = value => typeof value === "number" && Number.isFinite(value);
  const safeHref = href => typeof href === "string" && /^china_lookup\.html#\d{6}\.(SS|SZ|BJ)$/.test(href);
  function safeFilingHref(href) {
    if(typeof href!=="string"||href.length>2048||/[\x00-\x1f]/.test(href))return false;
    try {
      const url=new URL(href);
      return url.protocol==="https:"&&!url.username&&!url.password&&(!url.port||url.port==="443")
        &&["sse.com.cn","szse.cn","bse.cn","cninfo.com.cn"].some(domain=>url.hostname===domain||url.hostname.endsWith("."+domain));
    } catch(_){return false;}
  }
  const normalize = value => String(value || "").normalize("NFKC").toLocaleLowerCase().trim();
  function selectRows(rows, state) {
    const query = normalize(state.query).slice(0,100), side = state.side || "all", minimum = Number(state.coverage || 2);
    return rows.filter(row => (!query || normalize(row.ticker + " " + row.name + " " + row.name_zh).includes(query))
      && (side === "all" || row.side === side) && row.available >= minimum && (!state.flagged || row.flags.length > 0))
      .slice().sort((a,b) => {
        let delta = 0;
        if (state.sort === "coverage") delta = b.available-a.available;
        else if (state.sort === "conflict") delta = (b.conflicting || 0)-(a.conflicting || 0);
        else if (state.sort !== "ticker") delta = (finite(b.alignment)?b.alignment:-2)-(finite(a.alignment)?a.alignment:-2);
        return delta || String(a.ticker).localeCompare(String(b.ticker),"en");
      });
  }
  function selectEvents(events, state) {
    return events.filter(event => (!state.horizon || state.horizon==="all" || event.horizon===state.horizon)
      && (!state.type || state.type==="all" || event.type===state.type));
  }
  function validPayload(data) {
    const text=value=>typeof value==="string", numeric=value=>value===null||finite(value);
    const count=value=>Number.isInteger(value)&&value>=0&&value<=7;
    const keys=["value","margin","flow","comment","lhb","block","analyst"];
    const direction=value=>["constructive","cautionary","mixed","insufficient","neutral","unavailable"].includes(value);
    const link=value=>value==null||safeHref(value);
    const source=s=>s&&keys.includes(s.key)&&numeric(s.value)&&numeric(s.contribution)
      &&direction(s.direction)&&["observed","unavailable","undated","future"].includes(s.state)
      &&(s.asof===null||text(s.asof));
    const complete=sources=>Array.isArray(sources)&&sources.length===7
      &&new Set(sources.map(s=>s&&s.key)).size===7;
    return !!(data&&data.schema===SCHEMA&&text(data.generated_at)
      &&Array.isArray(data.rows)&&data.rows.length<=20000
      &&complete(data.sources)&&data.sources.every(s=>s&&keys.includes(s.key)
        &&text(s.label_en)&&text(s.label_zh)&&text(s.description_en)&&text(s.description_zh))
      &&Array.isArray(data.events)&&data.events.length<=20000
      &&data.events.every(e=>e&&text(e.id)&&text(e.ticker)&&text(e.name)&&text(e.type)
        &&text(e.label_en)&&text(e.label_zh)&&text(e.detail_en)&&text(e.detail_zh)
        &&["upcoming","recent","undated","archive"].includes(e.horizon)&&link(e.href)
        &&(e.filing_href==null||safeFilingHref(e.filing_href)))
      &&data.rows.every(r=>r&&text(r.ticker)&&text(r.name)&&direction(r.side)&&numeric(r.alignment)
        &&complete(r.sources)&&r.sources.every(source)&&Array.isArray(r.flags)
        &&r.flags.every(f=>f&&text(f.label_en)&&text(f.label_zh))&&link(r.href)
        &&count(r.available)&&count(r.constructive)&&count(r.cautionary)&&count(r.neutral)));
  }
  if (typeof module!=="undefined" && module.exports) module.exports={selectRows,selectEvents,safeHref,safeFilingHref,validPayload};
  if (typeof document==="undefined") return;
  const root=document.getElementById("china-evidence-desk");
  if (!root) return;
  const $=id=>document.getElementById(id);
  const zh=()=>document.documentElement.dataset.lang==="zh";
  const t=(en,cn)=>zh()?cn:en;
  const label=(row,key)=>row[key+(zh()?"_zh":"_en")] || row[key+"_en"] || "";
  const el=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!=null)node.textContent=String(text);return node;};
  const num=(n,places=2)=>finite(n)?(n>0?"+":"")+n.toFixed(places):"—";
  const directions={constructive:["Constructive","偏积极"],cautionary:["Cautionary","偏谨慎"],mixed:["Mixed","混合"],insufficient:["Insufficient","不足"],neutral:["Neutral","中性"],unavailable:["Unavailable","不可用"]};
  const direction=s=>t(...(directions[s]||directions.unavailable));
  const tone=s=>s==="constructive"?"ced-positive":s==="cautionary"?"ced-negative":"ced-muted";
  const horizons={upcoming:["Upcoming","即将发生"],recent:["Recent","近期"],undated:["Undated","无日期"],archive:["Earlier","较早"]};
  const stateLabel=s=>({unavailable:t("Unavailable","不可用"),undated:t("Date not supplied","未提供日期"),future:t("Future date — check source","未来日期 — 请核对"),observed:t("Dated","已注明日期")})[s]||t("Unknown","未知");
  let preview;
  try { preview=JSON.parse($("ced-preview").textContent); } catch (_) { return; }
  if (preview.schema!==SCHEMA) return;
  root.dataset.enhanced="true";
  let rows=preview.rows||[], events=preview.events||[], sources=preview.sources||[];
  let page=0,eventPage=0,loaded=false,loading=false,activeRow=null,lastFocus=null;
  const controls=()=>({query:$("ced-search").value,side:$("ced-side").value,coverage:$("ced-coverage").value,sort:$("ced-sort").value,flagged:$("ced-flagged").checked});
  const eventControls=()=>({horizon:$("ced-horizon").value,type:$("ced-event-type").value});
  function companyLink(row,cls) {
    const node=el(safeHref(row.href)?"a":"span",cls,label(row,"name")||row.name||row.ticker);
    if (safeHref(row.href)) node.href=row.href;
    return node;
  }
  function buildRow(row) {
    const tr=el("tr"), name=el("td"), evidence=el("td"), coverage=el("td"), notes=el("td");
    name.append(companyLink(row,"ced-company"),el("span","ced-ticker",row.ticker));
    evidence.append(el("span","ced-mobile-label",t("Evidence","证据")),el("span",tone(row.side),direction(row.side)),el("br"));
    evidence.append(el("small","",row.agreeing!=null?t(row.agreeing+" support · "+row.conflicting+" conflict",row.agreeing+"项支持 · "+row.conflicting+"项冲突")
      :t(row.constructive+" positive · "+row.cautionary+" negative",row.constructive+"项积极 · "+row.cautionary+"项谨慎")));
    coverage.append(el("span","ced-mobile-label",t("Coverage","覆盖")),el("b","",row.available+"/7"));
    const dots=el("div","ced-source-dots");dots.setAttribute("aria-hidden","true");
    row.sources.forEach(s=>dots.append(el("span",directions[s.direction]?s.direction:"unavailable")));
    coverage.append(dots,el("small","",t("available inputs","项输入可用")));
    notes.append(el("span","ced-mobile-label",t("Research notes","研究提示")));
    row.flags.slice(0,2).forEach(f=>notes.append(el("span","ced-badge ced-warning",label(f,"label"))));
    if (!row.flags.length) notes.append(el("small","",t("No supplied flags","未提供标记")));
    notes.append(el("br"));
    const button=el("button","ced-evidence-button",t("Inspect 7 sources →","检查7项来源 →"));
    button.type="button";button.setAttribute("aria-label",t("Inspect evidence for ","检查公司证据：")+row.name);
    button.addEventListener("click",()=>openDetail(row,button));notes.append(button);
    tr.append(name,evidence,coverage,notes);return tr;
  }
  function renderRows() {
    const selected=loaded?selectRows(rows,controls()):rows;
    const pages=Math.max(1,Math.ceil(selected.length/PAGE));page=Math.min(page,pages-1);
    $("ced-rows").replaceChildren(...selected.slice(page*PAGE,(page+1)*PAGE).map(buildRow));
    $("ced-no-results").hidden=selected.length>0;
    $("ced-no-results").textContent=rows.length?t("No companies match these filters. Try another name or reset the filters.","没有符合筛选条件的公司。请尝试其他名称或重置筛选。"):t("No eligible company data is available. Inspect source coverage below.","暂无合资格公司数据。请查看下方来源覆盖。");
    $("ced-results").textContent=loaded?t(selected.length.toLocaleString()+" of "+rows.length.toLocaleString()+" eligible companies",rows.length.toLocaleString()+"只合资格公司中有"+selected.length.toLocaleString()+"只符合条件")
      :t("Eight-name preview · load the full universe to search","最多8家公司预览 · 载入完整范围后可搜索");
    $("ced-page").textContent=t("Page "+(page+1)+" of "+pages,"第"+(page+1)+"页，共"+pages+"页");
    $("ced-prev").disabled=!loaded||page===0;$("ced-next").disabled=!loaded||page>=pages-1;
  }
  function eventNode(event) {
    const node=el("article","ced-event"), when=el("div","ced-event-date",event.date||t("Date not supplied","未提供日期"));
    when.append(el("small","",t(...(horizons[event.horizon]||horizons.undated))));
    const body=el("div"),title=el("h3");
    title.append(companyLink({name:event.name,name_zh:event.name,ticker:event.ticker,href:event.href},""),el("small",""," "+event.ticker));
    body.append(title,el("span","ced-badge",label(event,"label")),el("p","",label(event,"detail")),
      el("small","",t("Source snapshot: ","数据快照：")+(event.observed_at||t("unknown","未知"))));
    {
      const details=el("details"),summary=el("summary","ced-muted",t("Disclosure details","披露详情"));
      details.append(summary);
      if(event.disclosure_title)details.append(el("p","",event.disclosure_title));
      if(event.reported_metric)details.append(el("p","",t("Reported metric: ","披露指标：")+event.reported_metric));
      if(event.reported_period)details.append(el("p","",t("Reporting period: ","报告期：")+event.reported_period));
      if(event.stage)details.append(el("p","",t("Reported stage: ","披露阶段：")+event.stage));
      if(finite(event.reported_change))details.append(el("p","",t("Reported change: ","披露变动：")+num(event.reported_change)+"% · "+t("Check metric, period and comparison base in the filing.","请在公告核对指标、报告期与比较基数。")));
      if(safeFilingHref(event.filing_href)){
        const filing=el("a","",t("Open source filing ↗","查看原始公告 ↗"));
        filing.href=event.filing_href;filing.target="_blank";filing.rel="noopener noreferrer";details.append(filing);
      }else details.append(el("p","",t("No filing link supplied by this feed. Check the original disclosure before relying on the record.","本数据未提供公告链接；使用此记录前请核对原始披露。")));
      body.append(details);
    }
    node.append(when,body);return node;
  }
  function renderEvents() {
    const selected=selectEvents(events,eventControls()),pages=Math.max(1,Math.ceil(selected.length/PAGE));eventPage=Math.min(eventPage,pages-1);
    $("ced-events").replaceChildren(...selected.slice(eventPage*PAGE,(eventPage+1)*PAGE).map(eventNode));
    if(!selected.length)$("ced-events").append(el("p","ced-empty",events.length?t("No records match this time horizon and type.","该时间范围与类型无匹配记录。"):t("No event feed is available. This is not proof of no market events.","暂无事件数据，并不证明市场没有事件。")));
    $("ced-event-results").textContent=t(selected.length+" of "+events.length+" available records",events.length+"条现有记录中有"+selected.length+"条符合条件");
    $("ced-event-page").textContent=t("Page "+(eventPage+1)+" of "+pages,"第"+(eventPage+1)+"页，共"+pages+"页");
    $("ced-event-prev").disabled=eventPage===0;$("ced-event-next").disabled=eventPage>=pages-1;
  }
  function renderDetail(row) {
    $("ced-detail-title").textContent=label(row,"name")||row.name;$("ced-detail-code").textContent=row.ticker;
    const body=$("ced-detail-body");body.replaceChildren();
    body.append(el("p","",t(direction(row.side)+" · "+row.available+" of 7 inputs available. Alignment "+num(row.alignment)+" is a weighted research composite, not a probability.",
      direction(row.side)+" · 7项输入中有"+row.available+"项可用。一致方向值"+num(row.alignment)+"是加权研究组合，不是概率。")));
    const link=el("a","ced-primary",t("Open company research & chart ↗","查看公司研究与图表 ↗"));
    if(safeHref(row.href)){link.href=row.href;body.append(link);}
    const wrap=el("div","ced-table-wrap"),table=el("table"),head=el("thead"),hr=el("tr"),tbody=el("tbody");
    [t("Source","来源"),t("Centered rank","中心化排名"),t("Contribution","贡献"),t("Direction","方向"),t("Source date","来源日期")].forEach(text=>{const th=el("th","",text);th.scope="col";hr.append(th);});head.append(hr);
    row.sources.forEach(s=>{
      const meta=sources.find(x=>x.key===s.key)||{},tr=el("tr"),name=el("td");
      name.append(el("b","",label(meta,"label")||s.key),el("p","",label(meta,"description")));
      const observed=el("td","",s.asof||"—");observed.append(el("br"),el("small","",s.state==="observed"?(s.date_kind==="observation"?t("Observation date","观察日期"):s.date_kind==="snapshot"?t("Source snapshot","来源快照"):stateLabel(s.state)):stateLabel(s.state)));
      tr.append(name,el("td","",num(s.value)),el("td","",num(s.contribution,3)),el("td",tone(s.direction),direction(s.direction)),observed);tbody.append(tr);
    });
    table.append(head,tbody);wrap.append(table);body.append(wrap);
    body.append(el("p","",t("Ranks range from −1 to +1. Contribution = rank × signed weight; negative weights can reverse direction. Missing dates are not replaced by today's date.",
      "排名范围为−1至+1。贡献 = 排名 × 有符号权重；负权重可反转方向。缺失日期不会替换为今天。")));
    if(row.flags.length){const list=el("ul");row.flags.forEach(f=>list.append(el("li","ced-warning",label(f,"label"))));body.append(list);}
    const related=events.filter(e=>e.ticker===row.ticker||e.ticker===row.ticker.split(".")[0]);
    body.append(el("h3","",t("Related disclosed events","相关披露事件")));
    if(related.length)related.slice(0,4).forEach(e=>body.append(eventNode(e)));
    else body.append(el("p","",t("No related event in this feed. Coverage is incomplete.","本数据源未提供相关事件，覆盖并非完整。")));
  }
  function openDetail(row,trigger) {
    activeRow=row;lastFocus=trigger;renderDetail(row);
    const dialog=$("ced-detail");
    if(typeof dialog.showModal==="function"){dialog.showModal();$("ced-detail-close").focus();}
    else if(safeHref(row.href))window.location.assign(row.href);
  }
  $("ced-detail").addEventListener("close",()=>{activeRow=null;if(lastFocus&&lastFocus.isConnected)lastFocus.focus();});
  async function load() {
    if(loading||loaded)return;
    loading=true;$("ced-load").disabled=true;$("ced-load-error").hidden=true;
    $("ced-load").textContent=t("Loading…","载入中…");
    const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),20000);
    try {
      const url=new URL("chinaaltdata/desk.json",window.location.href);
      url.searchParams.set("v",preview.generated_at||"current");
      const response=await fetch(url,{signal:abort.signal,credentials:"same-origin"});
      if(!response.ok)throw new Error("HTTP");
      if(Number(response.headers.get("content-length"))>12000000)throw new Error("size");
      const data=await response.json();
      if(!validPayload(data))throw new Error("schema");
      if(data.generated_at!==preview.generated_at)throw new Error("vintage");
      rows=data.rows;events=data.events;sources=data.sources;loaded=true;
      $("ced-controls").disabled=false;$("ced-load").hidden=true;
      renderRows();renderEvents();
    } catch(error) {
      $("ced-load-error").hidden=false;
      $("ced-load-error").textContent=error.message==="vintage"
        ?t("This page and its data were updated at different times. Reload the page to get a consistent version. The preview and company links remain available.","页面与数据更新时间不同，请刷新页面获取一致版本。预览与公司链接仍可使用。")
        :t("The full research universe could not be loaded. The preview and company links still work. You can retry below.","无法载入完整研究范围。预览与公司链接仍可使用，可点击下方重试。");
      $("ced-load").textContent=t("Retry loading","重新载入");
    } finally {clearTimeout(timer);loading=false;$("ced-load").disabled=false;}
  }
  function drawTrend() {
    const data=preview.participation&&preview.participation.trend||[],values=data.map(p=>p.value).filter(finite);
    if(values.length<2)return;
    const low=Math.min(-.5,...values),high=Math.max(.5,...values),scale=n=>90-(n-low)/(high-low)*80;
    const svg=$("ced-trend").querySelector("svg"),NS="http://www.w3.org/2000/svg";svg.replaceChildren();
    const base=document.createElementNS(NS,"line");base.setAttribute("x1","0");base.setAttribute("x2","900");base.setAttribute("y1",String(scale(0)));base.setAttribute("y2",String(scale(0)));svg.append(base);
    let path="",open=false;
    data.forEach((p,i)=>{if(!finite(p.value)){open=false;return;}path+=(open?"L":"M")+(i/(data.length-1)*900).toFixed(2)+","+scale(p.value).toFixed(2)+" ";open=true;});
    const line=document.createElementNS(NS,"path");line.setAttribute("d",path);svg.append(line);
    svg.setAttribute("aria-label",t("Trading intensity in z-scores; range "+low.toFixed(2)+" to "+high.toFixed(2)+". Gaps are missing observations.","成交强度z值，范围"+low.toFixed(2)+"至"+high.toFixed(2)+"；缺口表示观察缺失。"));
    $("ced-trend-start").textContent=data[0].date;$("ced-trend-end").textContent=data[data.length-1].date;$("ced-trend").hidden=false;
  }
  function localize() {
    root.querySelectorAll("option[data-en]").forEach(option=>{option.textContent=zh()?option.dataset.zh:option.dataset.en;});
    $("ced-search").placeholder=zh()?"代码或公司名称":"Ticker or company name";
    $("ced-detail-close").setAttribute("aria-label",t("Close evidence","关闭证据"));
    root.querySelector(".ced-jump").setAttribute("aria-label",t("On this page","本页目录"));
    renderRows();renderEvents();drawTrend();if(activeRow)renderDetail(activeRow);
  }
  let debounce;
  $("ced-search").addEventListener("input",()=>{clearTimeout(debounce);debounce=setTimeout(()=>{page=0;renderRows();},120);});
  ["ced-side","ced-coverage","ced-sort","ced-flagged"].forEach(id=>$(id).addEventListener("change",()=>{page=0;renderRows();}));
  $("ced-reset").addEventListener("click",()=>{$("ced-search").value="";$("ced-side").value="all";$("ced-coverage").value="2";$("ced-sort").value="alignment";$("ced-flagged").checked=false;page=0;renderRows();$("ced-search").focus();});
  $("ced-prev").addEventListener("click",()=>{page=Math.max(0,page-1);renderRows();});
  $("ced-next").addEventListener("click",()=>{page++;renderRows();});
  ["ced-horizon","ced-event-type"].forEach(id=>$(id).addEventListener("change",()=>{eventPage=0;renderEvents();}));
  $("ced-event-prev").addEventListener("click",()=>{eventPage=Math.max(0,eventPage-1);renderEvents();});
  $("ced-event-next").addEventListener("click",()=>{eventPage++;renderEvents();});
  $("ced-event-filters").disabled=false;
  $("ced-load").addEventListener("click",load);
  new MutationObserver(localize).observe(document.documentElement,{attributes:true,attributeFilter:["data-lang"]});
  localize();
  if(typeof IntersectionObserver==="function"){
    const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){observer.disconnect();load();}},{rootMargin:"300px"});
    observer.observe($("companies"));
  }
})();
