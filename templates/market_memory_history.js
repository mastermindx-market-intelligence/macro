/* Offline Market Memory history. No fetch, no live data, no implicit future reveal. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const ui = { ready:false, outcomesDecoded:false, outcomesVisible:false, error:null };
  const text = (en,zh) => document.documentElement.dataset.lang === 'zh' ? zh : en;
  let corpus=null, outcomes=null, macro=null, macroIndex=null, dayIndex=new Map(), outcomeIndex=null, dates=[];
  let filings=null,filingsIndex=null,filingsOffset=0,filingsDay=null;
  let transcripts=null,transcriptsIndex=null,transcriptsOffset=0,transcriptsDay=null;
  const names={SPY:['US large caps','美国大盘'],QQQ:['Nasdaq-100 proxy','纳斯达克100代理'],IWM:['US small caps','美国小盘'],RSP:['Equal-weight US stocks','等权重美股'],DIA:['US blue chips','美国蓝筹'],XLB:['Materials','原材料'],XLC:['Communication services','通信服务'],XLE:['Energy','能源'],XLF:['Financials','金融'],XLI:['Industrials','工业'],XLK:['Technology','科技'],XLP:['Consumer staples','必需消费'],XLRE:['Real estate','房地产'],XLU:['Utilities','公用事业'],XLV:['Health care','医疗'],XLY:['Consumer discretionary','可选消费'],TLT:['Long Treasury bonds','长期美国国债'],IEF:['Intermediate Treasuries','中期美国国债'],SHY:['Short Treasury bonds','短期美国国债'],HYG:['High-yield credit','高收益信用'],LQD:['Investment-grade credit','投资级信用'],UUP:['US dollar proxy','美元代理'],GLD:['Gold proxy','黄金代理'],USO:['Oil futures proxy','原油期货代理'],SLV:['Silver proxy','白银代理']};
  const fmt = (v,unit='%') => v===null || v===undefined ? '—' : (v>0?'+':'')+v.toFixed(2)+unit;
  const reason = (r,key) => r.missing && r.missing[key] || '';
  function failure(error) {
    ui.error=String(error && error.message || error);
    $('mmh-status').textContent=text('Historical evidence could not be opened. Verify the original artifact.','无法打开历史依据。请核验原始文件。');
    $('mmh-provenance').textContent=ui.error;
    ['mmh-date','mmh-symbol','mmh-prev','mmh-next','mmh-reveal'].forEach(id => $(id).disabled=true);
  }
  async function decode(id) {
    const node=$(id);
    if (!node || typeof DecompressionStream==='undefined') throw new Error('Compressed artifact support unavailable');
    const encoded=node.textContent.trim();
    if(encoded.length>96*1024*1024) throw new Error('Encoded artifact exceeds budget');
    const compressed=Uint8Array.from(atob(encoded), c=>c.charCodeAt(0));
    const reader=new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip')).getReader();
    const parts=[]; let size=0;
    for (;;) { const {done,value}=await reader.read(); if(done)break; size+=value.length;
      if(size>64*1024*1024){await reader.cancel();throw new Error('Decoded artifact exceeds budget');} parts.push(value); }
    const bytes=new Uint8Array(size);let offset=0;for(const p of parts){bytes.set(p,offset);offset+=p.length;}
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(b=>b.toString(16).padStart(2,'0')).join('');
    if(digest!==node.dataset.sha256)throw new Error('Browser payload digest mismatch');
    const data=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
    if(data.mode!=='RETROSPECTIVE_EXPLORATORY'||!Array.isArray(data.columns)||!Array.isArray(data.rows)||data.rows.length>1000000)throw new Error('Historical payload contract mismatch');
    if(new Set(data.columns).size!==data.columns.length)throw new Error('Duplicate history columns');
    if(id==='mmh-data' && data.columns.some(c=>c.startsWith('forward_')||c.startsWith('outcome')))throw new Error('Future outcome in state payload');
    return data;
  }
  function index(data,dateKey='market_date',symbolKey='vendor_symbol') {
    const map=new Map(),di=data.columns.indexOf(dateKey);
    if(di<0||data.columns.indexOf(symbolKey)<0)throw new Error('Missing date or symbol');
    for(const row of data.rows){if(row.length!==data.columns.length)throw new Error('Historical row shape mismatch');
      const day=row[di]; if(!/^\d{4}-\d{2}-\d{2}$/.test(day))throw new Error('Invalid history date');
      if(!map.has(day))map.set(day,[]);map.get(day).push(row);}
    return map;
  }
  function objects(data, idx, day) {
    const filter=$('mmh-symbol').value;
    return (idx.get(day)||[]).map(row=>Object.fromEntries(data.columns.map((k,i)=>[k,row[i]])))
      .filter(row=>!filter||row.vendor_symbol===filter);
  }
  function populate(tbody,rows,columns) {
    tbody.replaceChildren();
    for(const row of rows){const tr=document.createElement('tr');const td=document.createElement('td');
      const b=document.createElement('strong');b.textContent=row.vendor_symbol;td.append(b);
      const label=document.createElement('span');label.className='mmh-proxy-name';const n=names[row.vendor_symbol];label.textContent=n?text(n[0],n[1]):row.vendor_symbol;td.append(label);tr.append(td);
      for(const [key,unit] of columns){const cell=document.createElement('td');const value=row[key];cell.textContent=fmt(value,unit);
        cell.className=value===null||value===undefined?'mmh-null':value>0?'mmh-positive':value<0?'mmh-negative':'';
        const why=reason(row,key);if(why)cell.setAttribute('aria-label',text('Unavailable: ','不可用：')+why);tr.append(cell);}
      tbody.append(tr);}
  }
  function hideOutcomes(){ui.outcomesVisible=false;$('mmh-outcomes').hidden=true;$('mmh-reveal').textContent=text('Reveal later outcomes','显示后续表现');}
  function renderMacro(day) {
    if(!macro)return;
    $('mmh-macro').hidden=false;
    const rows=(macroIndex.get(day)||[]).map(row=>Object.fromEntries(macro.columns.map((k,i)=>[k,row[i]])));
    $('mmh-macro-status').textContent=rows.length?text(`${rows.length} first-print records on this date.`, `该日期有 ${rows.length} 条初值记录。`):text('No retained first-print record for this exact date.','该确切日期没有保留的初值记录。');
    const body=$('mmh-macro-table').tBodies[0];body.replaceChildren();
    for(const row of rows.slice(0,100)){const tr=document.createElement('tr');
      for(const value of [row.series,row.period,row.value===null?'—':Number(row.value).toLocaleString(undefined,{maximumFractionDigits:6})]){const td=document.createElement('td');td.textContent=value;tr.append(td);}body.append(tr);}
    if(rows.length>100)$('mmh-macro-status').textContent+=text(' Showing 100; all records remain in the source artifact.',' 显示前100条；所有记录仍保留在来源文件中。');
  }
  function renderFilings(day) {
    if(!filings)return;
    $('mmh-filings').hidden=false;
    if(filingsDay!==day){filingsDay=day;filingsOffset=0;}
    const all=filingsIndex.get(day)||[],page=all.slice(filingsOffset,filingsOffset+50);
    const range=filings.metadata.source_date_range;
    const outside=!range.first||day<range.first||day>range.last;
    $('mmh-filings-status').textContent=all.length?
      text(`${all.length} retained filings · showing ${filingsOffset+1}–${filingsOffset+page.length}.`,`${all.length} 条保留披露 · 显示第 ${filingsOffset+1}–${filingsOffset+page.length} 条。`):
      outside?text(`No retained filing coverage for this date. Available source: ${range.first||'—'} to ${range.last||'—'}.`,`该日期没有保留的披露覆盖。来源范围：${range.first||'—'} 至 ${range.last||'—'}。`):
      text('No retained filing record on this exact date. This does not mean no event occurred.','该确切日期没有保留的披露记录，并不意味着没有事件发生。');
    const body=$('mmh-filings-table').tBodies[0];body.replaceChildren();
    for(const values of page){const row=Object.fromEntries(filings.columns.map((c,i)=>[c,values[i]]));const tr=document.createElement('tr');
      for(const value of [row.ticker_source_label,`${row.form} · ${row.filing_key}`,row.report_date,row.acceptance_datetime_utc]){
        const td=document.createElement('td');td.textContent=value===null?'—':String(value);tr.append(td);
      }body.append(tr);
    }
    $('mmh-filings-prev').disabled=filingsOffset===0;
    $('mmh-filings-next').disabled=filingsOffset+page.length>=all.length;
    $('mmh-filings-prev').textContent=text('Previous filings','上一页披露');
    $('mmh-filings-next').textContent=text('Next filings','下一页披露');
  }
  async function showTranscriptRequest(row,day) {
    const metadata={fiscal_quarter:row.fiscal_quarter,fiscal_year:row.fiscal_year,
      report_date:row.report_date,symbol:row.symbol,transcripts_id:row.transcripts_id};
    const bytes=new TextEncoder().encode(JSON.stringify(metadata));
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(b=>b.toString(16).padStart(2,'0')).join('');
    if(day!==$('mmh-date').value)return;
    const q={action:'history_transcript',ref:transcripts.metadata.source_ref,
      expected_version:transcripts.metadata.source_version,row_position:row.source_row_position,
      expected_metadata_sha256:digest};
    $('mmh-transcript-request').textContent=JSON.stringify(q,null,2);$('mmh-transcript-request').hidden=false;
  }
  function renderTranscripts(day) {
    if(!transcripts)return;
    $('mmh-transcripts').hidden=false;
    if(transcriptsDay!==day){transcriptsDay=day;transcriptsOffset=0;$('mmh-transcript-request').hidden=true;$('mmh-transcript-request').textContent='';}
    const all=transcriptsIndex.get(day)||[],page=all.slice(transcriptsOffset,transcriptsOffset+50);
    const range=transcripts.metadata.source_date_range,outside=!range.first||day<range.first||day>range.last;
    $('mmh-transcripts-status').textContent=all.length?
      text(`${all.length} reported call records · showing ${transcriptsOffset+1}–${transcriptsOffset+page.length}.`,`${all.length} 条会议记录 · 显示第 ${transcriptsOffset+1}–${transcriptsOffset+page.length} 条。`):
      outside?text(`No retained call coverage for this date. Source: ${range.first||'—'} to ${range.last||'—'}.`,`该日期没有保留会议覆盖。来源范围：${range.first||'—'} 至 ${range.last||'—'}。`):
      text('No retained call record for this exact date. This is not proof that no call occurred.','该确切日期没有保留会议记录，但不能据此断定没有会议。');
    const body=$('mmh-transcripts-table').tBodies[0];body.replaceChildren();
    for(const values of page){const row=Object.fromEntries(transcripts.columns.map((c,i)=>[c,values[i]])),tr=document.createElement('tr');
      for(const value of [row.symbol,`${row.fiscal_year} Q${row.fiscal_quarter}`,row.report_date]){const td=document.createElement('td');td.textContent=String(value);tr.append(td);}
      const td=document.createElement('td'),button=document.createElement('button');button.type='button';button.className='segbtn';
      button.textContent=text('Show read request','显示读取请求');button.addEventListener('click',()=>showTranscriptRequest(row,day).catch(failure));td.append(button);tr.append(td);body.append(tr);
    }
    $('mmh-transcripts-prev').disabled=transcriptsOffset===0;$('mmh-transcripts-next').disabled=transcriptsOffset+page.length>=all.length;
    $('mmh-transcripts-prev').textContent=text('Previous calls','上一页会议');$('mmh-transcripts-next').textContent=text('Next calls','下一页会议');
  }
  function render() {
    if(!corpus)return;
    const day=$('mmh-date').value, rows=objects(corpus,dayIndex,day), total=corpus.metadata.coverage.selected_proxy_count;
    $('mmh-selected-date').textContent=day||'—';
    $('mmh-benchmark-heading').textContent=text('vs. '+corpus.metadata.request.benchmark+' · 21 bars','较'+corpus.metadata.request.benchmark+' · 21条');
    renderMacro(day);renderFilings(day);renderTranscripts(day);
    $('mmh-status').textContent=rows.length?text(`${rows.length} selected proxies observed`, `已观测 ${rows.length} 个选定代理资产`):text('No observation for this exact date','该确切日期没有观测数据');
    $('mmh-empty').hidden=rows.length!==0;$('mmh-state-wrap').hidden=rows.length===0;
    const i=dates.indexOf(day);$('mmh-prev').disabled=!dates.some(d=>d<day);$('mmh-next').disabled=!dates.some(d=>d>day);
    $('mmh-reveal').disabled=!rows.length||!$('mmh-outcomes-data');
    populate($('mmh-table').tBodies[0],rows,[['return_1ob_pct','%'],['return_21ob_pct','%'],['sma_distance_50ob_pct','%'],['drawdown_252ob_pct','%'],['relative_return_21ob_pp',text(' pp',' 百分点')]]);
    const meta=corpus.metadata, coverage=meta.coverage;
    $('mmh-archive-range').textContent=text(`Archive: ${coverage.first_observed_date} to ${coverage.last_observed_date} · ${coverage.observed_dates.toLocaleString()} observed dates · ${total} selected proxies`,`存档：${coverage.first_observed_date} 至 ${coverage.last_observed_date} · ${coverage.observed_dates.toLocaleString()} 个观测日期 · ${total} 个选定代理资产`);
    $('mmh-basis').textContent=text('Price basis: ','价格口径：')+meta.basis+text(' — vendor-adjusted history is not an executable-price tape.',' — 供应商调整后的历史不等于可成交价格记录。');
    $('mmh-cutoff').textContent=text('Source captures selected through: ','所选来源截取截至：')+meta.request.capture_cutoff;
    $('mmh-coverage-note').textContent=coverage.requested_end_after_last_observation?text(`Requested through ${meta.request.end}; the source ends earlier. Missing dates are not filled.`,`请求截至 ${meta.request.end}；来源数据更早结束，缺失日期不会填补。`):text('Coverage follows retained observations, not an asserted full exchange calendar.','覆盖范围取决于保留的观测记录，并非声称完整交易日历。');
    const evidence={artifact_id:meta.artifact_id,manifest_sha256:corpus.manifest_sha256,mode:corpus.mode,source_references:meta.sources,selected_day_missing:rows.filter(r=>Object.keys(r.missing||{}).length).map(r=>({vendor_symbol:r.vendor_symbol,missing:r.missing}))};
    if(macro)evidence.macro={sha256:macro.macro_sha256,metadata:macro.metadata};
    if(filings)evidence.filings={sha256:filings.filings_sha256,metadata:filings.metadata};
    if(transcripts)evidence.transcripts={catalog_sha256:transcripts.transcripts_catalog_sha256,metadata:transcripts.metadata};
    $('mmh-provenance').textContent=JSON.stringify(evidence,null,2);
    $('mmh-prev').textContent=text('Previous','上一个');$('mmh-next').textContent=text('Next','下一个');
    $('mmh-symbol').options[0].textContent=text('All selected proxies','全部选定代理资产');
    if(ui.outcomesVisible && outcomes){populate($('mmh-outcomes-table').tBodies[0],objects(outcomes,outcomeIndex,day),[['forward_return_1ob_pct','%'],['forward_return_5ob_pct','%'],['forward_return_21ob_pct','%'],['forward_return_63ob_pct','%'],['forward_max_drawdown_21ob_pct','%']]);$('mmh-reveal').textContent=text('Hide later outcomes','隐藏后续表现');}
    else hideOutcomes();
  }
  function step(direction){const current=$('mmh-date').value;const candidates=dates.filter(d=>direction<0?d<current:d>current);if(!candidates.length)return;$('mmh-date').value=direction<0?candidates[candidates.length-1]:candidates[0];hideOutcomes();render();}
  $('mmh-date').addEventListener('change',()=>{hideOutcomes();render();});
  $('mmh-symbol').addEventListener('change',()=>{hideOutcomes();render();});
  $('mmh-prev').addEventListener('click',()=>step(-1));$('mmh-next').addEventListener('click',()=>step(1));
  $('mmh-theme').addEventListener('click',()=>{const html=document.documentElement;html.dataset.theme=html.dataset.theme==='light'?'dark':'light';$('mmh-theme').textContent=html.dataset.theme==='light'?text('Dark','深色'):text('Light','浅色');});
  $('mmh-language').addEventListener('click',()=>{const html=document.documentElement;html.dataset.lang=html.dataset.lang==='zh'?'en':'zh';html.lang=html.dataset.lang; $('mmh-language').textContent=html.lang==='zh'?'English':'中文';$('mmh-theme').textContent=html.dataset.theme==='light'?text('Dark','深色'):text('Light','浅色');render();});
  $('mmh-filings-prev').addEventListener('click',()=>{filingsOffset=Math.max(0,filingsOffset-50);renderFilings($('mmh-date').value);});
  $('mmh-filings-next').addEventListener('click',()=>{const day=$('mmh-date').value;if(filings&&filingsOffset+50<(filingsIndex.get(day)||[]).length){filingsOffset+=50;renderFilings(day);}});
  $('mmh-transcripts-prev').addEventListener('click',()=>{transcriptsOffset=Math.max(0,transcriptsOffset-50);$('mmh-transcript-request').hidden=true;renderTranscripts($('mmh-date').value);});
  $('mmh-transcripts-next').addEventListener('click',()=>{const day=$('mmh-date').value;if(transcripts&&transcriptsOffset+50<(transcriptsIndex.get(day)||[]).length){transcriptsOffset+=50;$('mmh-transcript-request').hidden=true;renderTranscripts(day);}});
  $('mmh-reveal').addEventListener('click',async()=>{if(ui.outcomesVisible){hideOutcomes();return;}const day=$('mmh-date').value;try{
    if(!outcomes){outcomes=await decode('mmh-outcomes-data');if(outcomes.manifest_sha256!==corpus.manifest_sha256)throw new Error('Outcomes belong to another archive');outcomeIndex=index(outcomes);ui.outcomesDecoded=true;}
    if(day!==$('mmh-date').value)return;ui.outcomesVisible=true;$('mmh-outcomes').hidden=false;render();
  }catch(error){failure(error);}});
  window.__MM_HISTORY_VIEW__=Object.freeze({status:()=>({...ui,marketDate:$('mmh-date').value,visibleRows:$('mmh-table').tBodies[0].rows.length})});
  (async()=>{try{corpus=await decode('mmh-data');dayIndex=index(corpus);dates=Array.from(dayIndex.keys()).sort();
    if($('mmh-macro-data')){macro=await decode('mmh-macro-data');if(macro.manifest_sha256!==corpus.manifest_sha256)throw new Error('Macro projection belongs to another archive');macroIndex=index(macro,'calendar_date','series');}
    if($('mmh-filings-data')){filings=await decode('mmh-filings-data');
      if(filings.manifest_sha256!==corpus.manifest_sha256||filings.metadata.point_in_time_eligible!==false)throw new Error('Filing projection binding or qualification mismatch');
      filingsIndex=index(filings,'filing_date','filing_key');}
    if($('mmh-transcripts-data')){transcripts=await decode('mmh-transcripts-data');
      if(transcripts.manifest_sha256!==corpus.manifest_sha256||transcripts.metadata.point_in_time_eligible!==false||transcripts.metadata.body_columns_read!==false)throw new Error('Transcript catalogue binding or qualification mismatch');
      transcriptsIndex=index(transcripts,'report_date','symbol');
      const si=transcripts.columns.indexOf('symbol'),yi=transcripts.columns.indexOf('fiscal_year'),qi=transcripts.columns.indexOf('fiscal_quarter');
      for(const rows of transcriptsIndex.values())rows.sort((a,b)=>String(a[si]).localeCompare(String(b[si]))||a[yi]-b[yi]||a[qi]-b[qi]);}
    for(const symbol of corpus.metadata.request.symbols.map(s=>s.vendor_symbol)){const o=document.createElement('option');o.value=symbol;o.textContent=symbol;$('mmh-symbol').append(o);}
    $('mmh-date').value=dates[dates.length-1]||corpus.metadata.request.end;
    $('mmh-date').min=corpus.metadata.request.start;$('mmh-date').max=corpus.metadata.request.end;
    $('mmh-date').disabled=false;$('mmh-symbol').disabled=false;ui.ready=true;render();
  }catch(error){failure(error);}})();
})();
