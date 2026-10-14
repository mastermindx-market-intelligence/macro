/* Source-owned numbers only: presentation never recomputes scores or authority. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const zh = () => document.documentElement.dataset.lang === 'zh';
  const text = (en, cn) => zh() ? cn : en;
  const names = {
    legacy:['Legacy groups','传统分类'], tff:['Financial futures','金融期货分类'], disaggregated:['Commodity groups','商品分类'],
    commercial:['Commercial','商业交易者'], noncommercial:['Large speculators','大型投机者'], nonreportable:['Nonreportable','非报告持仓'],
    dealer:['Dealers','交易商'], asset_manager:['Asset managers','资产管理者'], leveraged_funds:['Leveraged funds','杠杆基金'],
    other_reportable:['Other reportable','其他报告交易者'], producer_merchant:['Producers / merchants','生产商／贸易商'],
    swap_dealer:['Swap dealers','掉期交易商'], managed_money:['Managed money','管理资金']
  };
  const label = key => (names[key] || [key,key])[zh()?1:0];
  const number = (v,d=0) => typeof v === 'number' && Number.isFinite(v) ? new Intl.NumberFormat(zh()?'zh-CN':'en-US',{maximumFractionDigits:d}).format(v) : '—';
  let snapshot = null, selected = new URLSearchParams(location.search).get('market') || 'nasdaq';
  function filters() {
    const query = $('cot-search').value.trim().toLowerCase(), category = $('cot-category').value, unusual = $('cot-extremes').checked;
    let count = 0;
    document.querySelectorAll('.cot-table tr[data-market]').forEach(row => {
      const visible = row.dataset.search.includes(query) && (category==='all'||row.dataset.category===category) && (!unusual||['watch','setup','extreme'].includes(row.dataset.level));
      row.hidden = !visible; count += Number(visible);
    });
    document.querySelectorAll('.cot-table tbody').forEach(body => {body.hidden = !Array.from(body.querySelectorAll('tr[data-market]')).some(row=>!row.hidden);});
    $('cot-empty').hidden = count > 0;
  }
  function option(value,title) {const e=document.createElement('option');e.value=value;e.textContent=title;return e;}
  function selectMarket(key, scroll=false) {
    if (!snapshot) return;
    const market = snapshot.markets.find(m=>m.market_id===key);
    if (!market) return;
    selected=key;
    document.querySelectorAll('.cot-table tr[data-market]').forEach(row=>{
      row.dataset.selected=String(row.dataset.market===key);
      row.querySelector('button').setAttribute('aria-pressed',String(row.dataset.market===key));
    });
    $('cot-detail-title').textContent=zh()?market.name_zh:market.name;
    $('cot-detail-code').textContent=`CFTC ${market.cftc_code}`;
    const current=$('cot-family').value;
    $('cot-family').replaceChildren(...Object.keys(market.families).map(f=>option(f,label(f))));
    if (market.families[current]) $('cot-family').value=current;
    showFamily();
    if (scroll && matchMedia('(max-width:1100px)').matches) $('cot-detail').scrollIntoView({block:'start',behavior:'auto'});
    if (scroll) {const u=new URL(location.href);u.searchParams.set('market',key);history.replaceState(null,'',u);}
  }
  function showFamily() {
    const market=snapshot.markets.find(m=>m.market_id===selected), family=market.families[$('cot-family').value];
    const current=$('cot-cohort').value;
    $('cot-cohort').replaceChildren(...Object.keys(family.cohorts||{}).map(c=>option(c,label(c))));
    if (family.cohorts?.[current]) $('cot-cohort').value=current;
    else if (family.cohorts?.noncommercial) $('cot-cohort').value='noncommercial';
    const dateParts = Object.fromEntries(new Intl.DateTimeFormat('en',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).map(p=>[p.type,p.value]));
    const nyToday = `${dateParts.year}-${dateParts.month}-${dateParts.day}`;
    const reportAge = family.report_asof_date ? (Date.parse(nyToday+'T00:00:00Z')-Date.parse(family.report_asof_date+'T00:00:00Z'))/86400000 : null;
    const displayState = family.state==='current' && reportAge!==null && reportAge>12 ? 'stale' : family.state;
    const state={current:['Current report','最新报告'],stale:['Old report — awaiting data','旧报告，等待更新'],awaiting_update:['Next report expected','等待新一期报告'],unavailable:['Data unavailable','数据不可用']}[displayState]||['Data unavailable','数据不可用'];
    $('cot-detail-meta').textContent=`${text(...state)} · ${family.report_asof_date||'—'} · ${text('Open interest','未平仓合约')} ${number(family.open_interest)}`;
    const body=$('cot-cohorts');body.replaceChildren();
    Object.entries(family.cohorts||{}).forEach(([key,c])=>{
      const tr=document.createElement('tr'), th=document.createElement('th');th.scope='row';th.textContent=label(key);tr.append(th);
      [c.net,c.change_since_previous_report,c.percentile_156w].forEach(value=>{const td=document.createElement('td');td.textContent=number(value);tr.append(td);});body.append(tr);
    });
    const p=$('cot-provenance');p.replaceChildren();
    const lines=[
      `${text('Observed version','观察到的版本时间')}: ${family.version_observed_at||'—'}`,
      `${text('Revision observed','修订观察时间')}: ${family.revised_at||'—'}`,
      text('Futures only. Families classify the same market differently; do not add their exposures.','仅期货。不同报告对同一市场采用不同分类，不能叠加敞口。'),
      text('History is latest-revised context, not certified original-vintage replay.','历史为最新修订版本，不是经认证的原始版本回放。'),
      `${text('Source fingerprint','来源指纹')}: ${family.source_record_sha256||'—'}`
    ];
    lines.forEach(line=>{const e=document.createElement('p');e.textContent=line;p.append(e);});
    const a=document.createElement('a');a.href='https://publicreporting.cftc.gov/';a.textContent=text('Official CFTC source','CFTC官方来源');a.target='_blank';a.rel='noopener noreferrer';p.append(a);
    showChart();
  }
  function showChart() {
    const market=snapshot.markets.find(m=>m.market_id===selected), family=market.families[$('cot-family').value], cohort=$('cot-cohort').value;
    const series=(family.history||[]).map(h=>({date:h.report_asof_date,value:h.net_pct_oi?.[cohort]}));
    const points=series.filter(p=>typeof p.value==='number'&&Number.isFinite(p.value));
    const target=$('cot-chart');target.replaceChildren();
    const n=family.cohorts?.[cohort]?.history_observations||0;
    $('cot-chart-caption').textContent=text(`${n} weekly observations in the score window · net position / open interest (%)`, `评分区间内${n}期周报 · 净持仓／未平仓量（%）`);
    target.setAttribute('aria-label',text(`Historical net positioning: ${label(cohort)}`,`${label(cohort)}历史净持仓`));
    if(points.length<2){const p=document.createElement('p');p.textContent=text('Not enough source history to draw a chart.','来源历史不足，暂不绘图。');target.append(p);return;}
    const ns='http://www.w3.org/2000/svg', svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 520 220');
    const low=Math.min(0,...points.map(p=>p.value)),high=Math.max(0,...points.map(p=>p.value)),span=high-low||1;
    const x=i=>42+i/Math.max(1,series.length-1)*464, y=v=>180-(v-low)/span*164;
    const zero=document.createElementNS(ns,'line');zero.setAttribute('x1','42');zero.setAttribute('x2','506');zero.setAttribute('y1',String(y(0)));zero.setAttribute('y2',String(y(0)));zero.setAttribute('class','cot-chart-zero');svg.append(zero);
    const path=document.createElementNS(ns,'path');let pen=false, d='';
    series.forEach((p,i)=>{if(typeof p.value!=='number'||!Number.isFinite(p.value)){pen=false;return;}d+=`${pen?'L':'M'}${x(i).toFixed(1)},${y(p.value).toFixed(1)} `;pen=true;});path.setAttribute('d',d);path.setAttribute('class','cot-chart-line');svg.append(path);
    [[5,22,number(high,1)],[5,180,number(low,1)],[42,210,points[0].date],[421,210,points[points.length-1].date]].forEach(([px,py,value])=>{const t=document.createElementNS(ns,'text');t.setAttribute('x',String(px));t.setAttribute('y',String(py));t.textContent=value;svg.append(t);});target.append(svg);
  }
  document.querySelectorAll('[data-select]').forEach(button=>button.addEventListener('click',()=>selectMarket(button.dataset.select,true)));
  $('cot-search').addEventListener('input',filters);$('cot-category').addEventListener('change',filters);$('cot-extremes').addEventListener('change',filters);
  $('cot-family').addEventListener('change',showFamily);$('cot-cohort').addEventListener('change',showChart);
  function language(){ $('cot-category').options[0].textContent=text('All markets','全部市场');document.querySelectorAll('#cot-category option[data-en]').forEach(o=>o.textContent=zh()?o.dataset.zh:o.dataset.en);$('cot-search').placeholder=text('S&P, gold, bonds…','标普、黄金、美债…');if(snapshot)selectMarket(selected); }
  new MutationObserver(language).observe(document.documentElement,{attributes:true,attributeFilter:['data-lang']});language();
  const digest=document.body.dataset.cotSnapshot;
  if(!/^[a-f0-9]{64}$/.test(digest))return;
  fetch(`cotdata/${digest}.json`,{credentials:'same-origin'}).then(r=>{if(!r.ok)throw Error('source unavailable');return r.json();}).then(data=>{
    if(data.schema!=='cot_snapshot.v1'||data.content_sha256!==digest||data.markets?.length!==21||Object.values(data.authority||{}).some(Boolean))throw Error('source contract mismatch');
    snapshot=data;selectMarket(data.markets.some(m=>m.market_id===selected)?selected:'es_spx');
  }).catch(()=>{
    $('cot-load-status').textContent=text('History unavailable. The table retains its dated snapshot.','历史暂不可用。表格保留已注明日期的快照。');
    $('cot-chart').textContent=text('The source snapshot could not be loaded. Reload to try again.','来源快照读取失败，请重新加载页面。');
    $('cot-family').disabled=true;$('cot-cohort').disabled=true;
  });
})();
