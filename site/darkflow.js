/* Independent display-only consumer. No score/alert events, timers or trading writes. */
(function () {
  'use strict';
  const SVG = 'http://www.w3.org/2000/svg';
  const finite = n => typeof n === 'number' && Number.isFinite(n);
  const dateOK = d => typeof d === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(d) && Number.isFinite(Date.parse(d));
  const zh = () => (document.documentElement.getAttribute('data-lang') || '').startsWith('zh');
  const tr = (en, cn) => zh() ? cn : en;
  const fmt = (n, digits = 2) => finite(n) ? n.toFixed(digits) : '—';
  const signed = (n, digits = 2) => finite(n) ? (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n).toFixed(digits) : '—';
  const percent = n => finite(n) ? fmt(n, 1) + '%' : '—';
  const sectorNames = {'Information Technology':'信息技术','Technology':'科技','Financials':'金融','Health Care':'医疗保健','Healthcare':'医疗保健','Consumer Discretionary':'可选消费','Consumer Staples':'必需消费','Industrials':'工业','Communication Services':'通信服务','Energy':'能源','Utilities':'公用事业','Materials':'原材料','Real Estate':'房地产','Unclassified':'未分类'};
  const sectorLabel = s => zh() ? (sectorNames[s] || s) : s;
  function el(tag, text, cls) {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  }
  function svgEl(tag, attrs) {
    const n = document.createElementNS(SVG, tag);
    Object.entries(attrs || {}).forEach(([key, value]) => n.setAttribute(key, String(value)));
    return n;
  }
  function readingOK(r) {
    return r && dateOK(r.date) && (r.value === null || (finite(r.value) && r.value >= 0 && r.value <= 100))
      && Number.isInteger(r.observed_names) && Number.isInteger(r.expected_names)
      && finite(r.coverage_pct) && r.coverage_pct >= 0 && r.coverage_pct <= 100;
  }
  function validate(data) {
    if (!data || data.schema !== 'darkflow_index.v1' || data.trade_authority !== false
      || data.tier !== 'display' || !/^[a-f0-9]{64}$/.test(data.generation || '')
      || !dateOK(data.asof) || !readingOK(data.current)
      || !data.display || !readingOK(data.display.reading)
      || data.display.asof !== data.display.reading.date
      || data.display.asof > data.asof || !Array.isArray(data.display.sectors)
      || !Array.isArray(data.display.sparkline)
      || !Number.isFinite(Date.parse(data.next_due_at))
      || !Number.isFinite(Date.parse(data.known_at))
      || Date.parse(data.known_at) > Date.now() + 300000) throw new Error('schema');
    if (data.display.mode === 'current' && (data.display.asof !== data.asof || data.current.value === null)) throw new Error('date');
    if (!['current', 'last_complete', 'unavailable'].includes(data.display.mode)) throw new Error('mode');
    return data;
  }
  async function fetchJSON(url, limit) {
    const controller = new AbortController();
    const deadline = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(url, {signal: controller.signal, credentials: 'same-origin', cache: 'no-cache'});
      if (!response.ok) throw new Error('http-' + response.status);
      if (Number(response.headers.get('Content-Length')) > limit) throw new Error('oversize');
      const body = await response.text();
      if (body.length > limit) throw new Error('oversize');
      return JSON.parse(body);
    } finally { clearTimeout(deadline); }
  }
  function drawChart(host, source, label) {
    host.replaceChildren();
    const points = (Array.isArray(source) ? source : []).filter(p => p && dateOK(p.date)).slice(-252);
    const good = points.filter(p => finite(p.value) && p.value >= 0 && p.value <= 100);
    if (!good.length) { host.append(el('p', tr('No covered observations in this window.', '此窗口没有达到覆盖要求的观测。'), 'df-muted')); return; }
    // Match SVG units to the actual container: a fixed 800-unit viewBox makes
    // mobile tick labels illegibly small even when the chart itself fits.
    const width = Math.max(260, Math.round(host.getBoundingClientRect().width) || 800);
    const height = host.classList.contains('df-spark') ? 136 : 205;
    const left = 44, right = 18, top = 22, bottom = 28;
    let low = Math.floor(Math.min(...good.map(p => p.value)) / 5) * 5;
    let high = Math.ceil(Math.max(...good.map(p => p.value)) / 5) * 5;
    if (high - low < 5) { low = Math.max(0, low - 2.5); high = Math.min(100, high + 2.5); }
    const x = i => left + i / Math.max(1, points.length - 1) * (width - left - right);
    const y = n => top + (high - n) / Math.max(1, high - low) * (height - top - bottom);
    const svg = svgEl('svg', {viewBox: `0 0 ${width} ${height}`, role: 'img', tabindex: '0', 'aria-label': label + '. ' + tr('Arrow keys inspect sessions.', '按方向键查看各交易日。')});
    const title = svgEl('title'); title.textContent = label; svg.append(title);
    [low, (low + high) / 2, high].forEach(value => {
      svg.append(svgEl('line', {x1:left, x2:width-right, y1:y(value), y2:y(value), class:'df-grid-line'}));
      const text = svgEl('text', {x:0, y:y(value)+4}); text.textContent = fmt(value, value % 1 ? 1 : 0) + '%'; svg.append(text);
    });
    let path = '', pen = false;
    points.forEach((p, i) => {
      if (!finite(p.value) || p.value < 0 || p.value > 100) { pen = false; return; }
      path += (pen ? ' L ' : ' M ') + x(i).toFixed(2) + ' ' + y(p.value).toFixed(2); pen = true;
    });
    svg.append(svgEl('path', {d:path, class:'df-chart-line'}));
    [0, points.length - 1].forEach((i, pos) => {
      const text = svgEl('text', {x:x(i), y:height-5, 'text-anchor':pos ? 'end':'start'});
      text.textContent = points[i].date; svg.append(text);
    });
    const line = svgEl('line', {x1:0,x2:0,y1:top,y2:height-bottom,stroke:'var(--df-muted)','stroke-dasharray':'3 3',opacity:0});
    const dot = svgEl('circle', {r:4,fill:'var(--df-blue)',opacity:0});
    const readout = svgEl('text', {x:width-right,y:12,'text-anchor':'end'});
    svg.append(line, dot, readout);
    let cursor = points.length - 1;
    function inspect(index) {
      cursor = Math.max(0, Math.min(points.length - 1, index)); const p = points[cursor];
      readout.textContent = p.date + ' · ' + (finite(p.value) ? fmt(p.value) + '%' : tr('Missing', '缺失'));
      line.setAttribute('x1', x(cursor)); line.setAttribute('x2', x(cursor)); line.setAttribute('opacity', '0.65');
      if (finite(p.value)) { dot.setAttribute('cx',x(cursor)); dot.setAttribute('cy',y(p.value)); dot.setAttribute('opacity','1'); }
      else dot.setAttribute('opacity','0');
      svg.setAttribute('aria-label',label + ': ' + readout.textContent);
    }
    svg.addEventListener('pointermove', event => {
      const box = svg.getBoundingClientRect();
      inspect(Math.round(((event.clientX-box.left)/box.width*width-left)/(width-left-right)*(points.length-1)));
    });
    svg.addEventListener('keydown', event => {
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); inspect(cursor+(event.key==='ArrowLeft' ? -1:1)); }
      if (event.key === 'Home' || event.key === 'End') { event.preventDefault(); inspect(event.key==='Home' ? 0:points.length-1); }
    });
    inspect(cursor); host.append(svg);
  }
  function mount(root) {
    if (root.dataset.mounted) return; root.dataset.mounted = 'true';
    const get = name => root.querySelector('[data-df="' + name + '"]');
    const text = (name, value) => { const n = get(name); if (n) n.textContent = value; };
    let data = null, history = null, loading = false, historyLoading = false, started = false;
    let selected = '__market__', volatility = null, volatilityLoading = false;
    function renderVolatility() {
      const host = get('volatility'); host.replaceChildren();
      if (!volatility) return;
      const wanted = ['vix_level', 'vix_velocity', 'term_slope', 'vvix_vix'];
      wanted.forEach(key => {
        const c = volatility.chips.find(chip => chip && chip.key === key);
        if (!c) return;
        const valid = dateOK(c.last_date) && c.last_date <= new Date().toISOString().slice(0, 10)
          && finite(c.value) && !['missing', 'young'].includes(c.freshness);
        const card = el('div');
        card.append(el('h4', zh() ? c.name_zh || c.name_en : c.name_en),
          el('b', valid ? (key === 'vix_velocity' ? signed(c.value) : fmt(c.value, key === 'term_slope' ? 3 : 2)) : '—'));
        card.append(el('small', (dateOK(c.last_date) ? c.last_date : tr('Date unavailable', '日期不可用'))
          + (key === 'vix_velocity' ? tr(' · VIX points / 5 sessions', ' · VIX点 / 5个交易日') : '')
          + (valid && finite(c.pctile) ? tr(' · percentile ', ' · 分位 ') + c.pctile : '')));
        card.append(el('p', valid ? (zh() ? c.plain_zh || c.plain_en : c.plain_en)
          : tr('Insufficient or unavailable observations.', '观测不足或不可用。')));
        host.append(card);
      });
      text('volatility-status', tr('Existing Vol Weather feed. Each chip keeps its own date; ', '沿用现有波动率背景数据，每个指标保留各自日期；')
        + tr('Dark Flow is dated ', '场外交易指标日期为 ') + data.display.asof
        + tr('. Different dates must not be read as same-session confirmation.', '。不同日期不应视为同一交易日的共同确认。'));
    }
    async function loadVolatility() {
      if (!data || volatility || volatilityLoading) return;
      volatilityLoading = true; get('volatility-retry').hidden = true;
      text('volatility-status', tr('Loading the existing volatility context…', '正在读取现有波动率背景…'));
      try {
        const incoming = await fetchJSON(new URL('basketdata/vol_weather.json', location.href).href, 60000);
        if (!incoming || !Array.isArray(incoming.chips) || incoming.chips.length > 30) throw new Error('vol-schema');
        volatility = incoming; renderVolatility();
      } catch (error) {
        text('volatility-status', tr('Volatility context is unavailable. Dark Flow is unaffected.', '波动率背景暂不可用，不影响场外交易读数。'));
        get('volatility-retry').hidden = false;
      } finally { volatilityLoading = false; }
    }
    function sectorTable(rows) {
      const body = get('sectors'); body.replaceChildren();
      rows.filter(r => r && typeof r.sector === 'string').forEach(r => {
        const row = el('tr'), name = el('td'), button = el('button', sectorLabel(r.sector), 'df-sector-button');
        button.type = 'button'; button.setAttribute('aria-pressed', String(selected === r.sector));
        button.addEventListener('click', () => { selected=r.sector; get('sector').value=selected; drawHistory(); sectorTable(rows); });
        name.append(button); row.append(name, el('td',percent(r.value)), el('td',signed(r.change_5d_pp)+' pp'), el('td',percent(r.coverage_pct)));
        body.append(row);
      });
    }
    function renderAttribution(a) {
      const host=get('attribution'), rows=get('drivers'); host.replaceChildren(); rows.replaceChildren();
      if (!a || a.state !== 'observed') { host.append(el('p',tr('Five-session attribution unavailable.', '5日变动分解暂不可用。'),'df-muted')); return; }
      [[tr('Changes in stock ratios','个股占比变化'),'ratio_pp'],[tr('Changes in trading weights','成交权重变化'),'weight_pp'],[tr('Membership / coverage mix','成分股 / 覆盖变化'),'coverage_mix_pp'],[tr('Total index change','指数总变动'),'total_pp']].forEach(([label,key])=>{
        const row=el('div');row.append(el('span',label),el('b',signed(a[key])+' pp'));host.append(row);
      });
      (Array.isArray(a.rows)?a.rows:[]).slice(0,8).forEach(r=>{
        if (!/^[A-Z][A-Z0-9-]{0,14}$/.test(r.ticker||'')) return;
        const row=el('tr'),cell=el('td'),link=el('a',r.ticker);link.href='stock.html?t='+encodeURIComponent(r.ticker);cell.append(link);
        row.append(cell,el('td',signed(r.ratio_pp)),el('td',signed(r.weight_pp)),el('td',signed(r.total_pp)));rows.append(row);
      });
    }
    function render() {
      if (!data) return;
      const d=data.display, r=d.reading, stale=Date.now()>Date.parse(data.next_due_at);
      root.dataset.state=stale?'stale':d.mode;
      let status;
      if (d.mode==='current') status=tr('Complete observation for ','完整观测日期：')+d.asof;
      else if (d.mode==='last_complete') status=tr('Latest complete: ','最新完整读数：')+d.asof+tr('. Awaiting complete inputs for ', '。等待以下日期的数据齐备：')+data.asof+'.';
      else status=tr('No sufficiently covered reading. Missing inputs are not treated as zero.', '尚无覆盖充分的读数。缺失数据不作为零值处理。');
      if (stale) status=tr('Update overdue. Last publication: ','更新已超时。上次发布时间：')+data.known_at.slice(0,10)+'. '+status;
      text('status',status);get('body').hidden=d.mode==='unavailable';get('retry').hidden=!stale;
      text('asof',d.asof);get('asof').dateTime=d.asof;text('value',fmt(r.value));
      text('change1',signed(r.change_1d_pp));text('change5',signed(r.change_5d_pp));
      text('coverage',tr(`${r.observed_names} of ${r.expected_names} constituents · ${fmt(r.coverage_pct,1)}% count coverage`,`${r.expected_names} 只成分股中覆盖 ${r.observed_names} 只 · ${fmt(r.coverage_pct,1)}% 数量覆盖率`));
      text('percentile',finite(r.percentile)?fmt(r.percentile,1)+'/100':'—');
      text('percentile-note',tr(`${r.percentile_observations||0} prior observations · minimum 60`,`${r.percentile_observations||0} 条此前观测 · 至少60条`));
      text('breadth',percent(r.ratio_breadth_up_pct));text('average',percent(r.mean_5d));
      text('velocity',signed(r.velocity_3d_pp_per_session,3));
      text('acceleration',signed(r.acceleration_3d_pp_per_session2,3));
      const a=d.attribution_5d;
      if(a && a.state==='observed') {
        const components=[['ratio_pp',tr('changes in constituent ratios','成分股占比变化')],['weight_pp',tr('changes in trading weights','成交权重变化')],['coverage_mix_pp',tr('membership and coverage changes','成分股与覆盖变化')]];
        components.sort((x,y)=>Math.abs(a[y[0]]||0)-Math.abs(a[x[0]]||0));
        text('observed-read',tr('Over five sessions, the index moved ','过去5个交易日，指数变化 ')+signed(a.total_pp)+' pp. '
          +tr('Its largest arithmetic component was ','其中绝对值最大的算术分项为 ')+components[0][1]+' ('+signed(a[components[0][0]])+' pp). '
          +tr('Open the breakdown to distinguish broad ratio changes from shifting trading concentration.','展开明细，区分个股占比变化与成交集中度变化。'));
      } else text('observed-read',tr('A covered five-session comparison is not yet available. Inspect the dated observations without inferring a direction.','尚无覆盖充分的5日比较。可查看各日观测，不据此推断方向。'));
      if(volatility) renderVolatility();
      text('spy',finite(d.context && d.context.spy_change_5d_pct)?signed(d.context.spy_change_5d_pct)+'%':'—');
      drawChart(get('spark'),d.sparkline,tr('Short-marked share','卖空标记成交占比'));
      sectorTable(d.sectors);renderAttribution(d.attribution_5d);
      const selector=get('sector');selector.replaceChildren(new Option('S&P 500','__market__'));
      d.sectors.forEach(s=>{if(s&&typeof s.sector==='string')selector.add(new Option(sectorLabel(s.sector),s.sector));});
      selector.value=selected;
      const s=data.sources || {},p=s.prices || {},m=s.membership || {};
      text('sources',tr(`FINRA through ${s.finra_latest||'—'} · Raw prices through ${p.latest_available||'—'} · Membership observed through ${m.observed_through||'—'} · Built ${data.known_at}`,
        `FINRA 截至 ${s.finra_latest||'—'} · 未复权价格截至 ${p.latest_available||'—'} · 成分股观测截至 ${m.observed_through||'—'} · 生成于 ${data.known_at}`));
      if(history) {drawHistory();renderNames();}
    }
    function drawHistory() {
      if(!history)return;
      const n=Number(get('range').value)||252;
      const source=selected==='__market__'?history.history:(history.sector_history||{})[selected];
      const series=(Array.isArray(source)?source:[]).slice(-n);
      drawChart(get('history-chart'),series,selected==='__market__'?'S&P 500':sectorLabel(selected));
      const valid=series.filter(p=>finite(p.value)).length;
      text('history-status',tr(`${valid} covered observations / ${series.length} sessions. Blue shows the ratio, not a bullish signal.`,`${series.length} 个交易日中 ${valid} 条观测达到覆盖要求。蓝色表示占比，并非看涨信号。`));
    }
    function renderNames() {
      const host=get('names');host.replaceChildren();if(!history)return;
      const q=get('search').value.trim().toUpperCase();
      const names=history.names.filter(r=>r&&/^[A-Z][A-Z0-9-]{0,14}$/.test(r.ticker||'')&&finite(r.ratio_pct)&&r.ticker.includes(q)).slice(0,12);
      names.forEach(r=>{const card=el('div'),name=el('span'),link=el('a',r.ticker);link.href='stock.html?t='+encodeURIComponent(r.ticker);name.append(link,el('small',history.names_asof||''));card.append(name,el('b',percent(r.ratio_pct)));host.append(card);});
      if(!names.length)host.append(el('p',tr('No covered constituent matches.', '无匹配且具有完整观测的成分股。'),'df-muted'));
    }
    async function loadHistory() {
      if(!data || history || historyLoading)return;
      historyLoading=true;get('history-retry').hidden=true;
      text('history-status',tr('Loading historical observations…','正在读取历史观测…'));
      try {
        const url=new URL('darkflow_history.json',new URL(root.dataset.source,location.href));
        const incoming=await fetchJSON(url.href,600000);
        if(incoming.schema!=='darkflow_index.v1'||incoming.generation!==data.generation
          || !Array.isArray(incoming.history)||!Array.isArray(incoming.names))throw new Error('generation');
        history=incoming;drawHistory();renderNames();
      } catch(error) {
        text('history-status',tr('History is unavailable or belongs to a different publication. The dated summary above is retained. Retry after the publication settles.','历史数据暂不可用或版本不同。上方保留已验证日期的摘要，可在发布完成后重试。'));
        get('history-retry').hidden=false;
      } finally {historyLoading=false;}
    }
    async function load() {
      if(loading)return;loading=true;started=true;get('retry').hidden=true;
      text('status',tr('Reading the latest source-backed observation…','正在读取最新有来源的观测…'));
      try {
        const incoming=validate(await fetchJSON(new URL(root.dataset.source,location.href).href,120000));
        if(!data||incoming.generation!==data.generation)history=null;
        data=incoming;render();
        if(get('explore').open)await Promise.all([loadHistory(),loadVolatility()]);
      } catch(error) {
        root.dataset.state='error';
        text('status',data?tr('Update unavailable. The previously loaded, explicitly dated observation remains below.','更新暂不可用。下方保留此前读取且标明日期的观测。'):tr('Observation unavailable. No market reading has been inferred. Use Retry to check again.','观测暂不可用，未推断市场读数。可点击重新读取。'));
        get('retry').hidden=false;
      } finally {loading=false;}
    }
    get('retry').addEventListener('click',load);
    get('history-retry').addEventListener('click',()=>{history=null;load();});
    get('volatility-retry').addEventListener('click',()=>{volatility=null;loadVolatility();});
    get('explore').addEventListener('toggle',()=>{if(get('explore').open){loadHistory();loadVolatility();}});
    get('sector').addEventListener('change',()=>{selected=get('sector').value;drawHistory();if(data)sectorTable(data.display.sectors);});
    get('range').addEventListener('change',drawHistory);get('search').addEventListener('input',renderNames);
    const observer=new MutationObserver(()=>{if(data)render();});
    observer.observe(document.documentElement,{attributes:true,attributeFilter:['data-lang']});
    if('ResizeObserver' in window) {
      let previousWidth=0;
      const resize=new ResizeObserver(entries=>{
        const width=entries[0].contentRect.width;
        if(Math.abs(width-previousWidth)<1)return;
        previousWidth=width;
        if(data){drawChart(get('spark'),data.display.sparkline,tr('Short-marked share','卖空标记成交占比'));drawHistory();}
      });
      resize.observe(root);
    }
    if('IntersectionObserver' in window){const visible=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){visible.disconnect();load();}},{rootMargin:'200px'});visible.observe(root);}
    else load();
    root.addEventListener('focusin',()=>{if(!started)load();});
  }
  function init(){document.querySelectorAll('[data-darkflow]').forEach(mount);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
