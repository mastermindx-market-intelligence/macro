/* Market Structure: existing Lightweight Charts 4.2, no model calculations. */
(function () {
  'use strict';
  const allowed = { gamma: [21,63,126,252,9999], systematic: [63,252,9999], dispersion: [63,252,9999] };
  const storageKeys = { gamma: 'msp-gex-range', systematic: 'msp-sys-range', dispersion: 'msp-cor-range' };
  const defaults = { gamma:126, systematic:252, dispersion:252 };
  const finite = value => typeof value === 'number' && Number.isFinite(value) ? value : null;
  function segments(rows, key) {
    const result = []; let run = [];
    rows.forEach(row => {
      if (finite(row[key]) === null) { if (run.length) result.push(run); run = []; }
      else run.push({ time:row.date, value:row[key] });
    });
    if (run.length) result.push(run);
    return result;
  }
  function readRange(raw, choices, fallback) {
    const value = typeof raw === 'string' && /^\d+$/.test(raw) ? Number(raw) : NaN;
    return choices.includes(value) ? value : fallback;
  }
  function sliceRows(rows, n) { return (Array.isArray(rows) ? rows : []).slice(-n); }
  function describeRows(rows, key) {
    const count = rows.filter(row => finite(row[key]) !== null).length;
    return { count, gaps:rows.length-count, first:rows[0]?.date || null, last:rows.at(-1)?.date || null };
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { finite, segments, readRange, sliceRows, describeRows };
    return;
  }
  if (typeof document === 'undefined') return;
  const zh = () => document.documentElement.getAttribute('data-lang') === 'zh';
  const L = (en, cn) => zh() ? cn : en;
  const fields = {
    net_gex_bn: { en:'Exposure', zh:'敞口', unit:'$B', digits:2, color:'--ink-info' },
    spot: { en:'SPX', zh:'SPX', unit:'pts', digits:2, color:'--ink-info' },
    flip: { en:'Switch', zh:'切换位', unit:'pts', digits:2, color:'--ink-warn', dash:true },
    vc_alloc_bn: { en:'Exposure', zh:'模型敞口', unit:'$B', digits:2, color:'--ink-info' },
    cta_score: { en:'Trend score', zh:'趋势评分', unit:'pts', digits:2, color:'--ink-info' },
    spx_close: { en:'SPX close', zh:'SPX 收盘', unit:'pts', digits:2, color:'--ink-info' },
    cor1m: { en:'COR1M', zh:'COR1M', unit:'pts', digits:2, color:'--ink-info' }
  };
  const keys = { gamma:['net_gex_bn','spot','flip'], systematic:['vc_alloc_bn','cta_score','spx_close'], dispersion:['cor1m'] };
  const primary = { gamma:'net_gex_bn', systematic:'vc_alloc_bn', dispersion:'cor1m' };
  function format(value, digits=2) {
    return finite(value) === null ? '—' : new Intl.NumberFormat(zh()?'zh-CN':'en-US', { minimumFractionDigits:digits, maximumFractionDigits:digits }).format(value);
  }
  function dateKey(value) {
    if (typeof value === 'string') return value;
    if (typeof value === 'number') return new Date(value*1000).toISOString().slice(0,10);
    return value && typeof value.year === 'number' ? [value.year,String(value.month).padStart(2,'0'),String(value.day).padStart(2,'0')].join('-') : null;
  }
  function label(key) { const f=fields[key]; return L(f.en,f.zh)+' ('+(f.unit==='pts'?L('pts','点'):f.unit)+')'; }
  let colorProbe, colorCanvas;
  function color(token) {
    if (!colorProbe) {
      colorProbe=document.createElement('span'); colorProbe.hidden=true;
      document.querySelector('.msp-main').appendChild(colorProbe);
      colorCanvas=document.createElement('canvas'); colorCanvas.width=colorCanvas.height=1;
    }
    colorProbe.style.color='var('+token+')';
    const ctx=colorCanvas.getContext('2d');
    ctx.clearRect(0,0,1,1); ctx.fillStyle=getComputedStyle(colorProbe).color; ctx.fillRect(0,0,1,1);
    const rgba=ctx.getImageData(0,0,1,1).data;
    return 'rgba('+rgba[0]+','+rgba[1]+','+rgba[2]+','+(rgba[3]/255)+')';
  }
  function options(height, priceKey) {
    return { autoSize:true, height,
      layout:{ background:{type:'solid',color:'transparent'}, textColor:color('--muted'), fontFamily:getComputedStyle(document.body).fontFamily, fontSize:11 },
      grid:{ vertLines:{visible:false}, horzLines:{color:color('--line-quiet')} },
      rightPriceScale:{ borderVisible:false, scaleMargins:{top:.13,bottom:.12}, minimumWidth:66 },
      timeScale:{ borderColor:color('--line'), fixLeftEdge:true, fixRightEdge:true, rightOffset:1, minBarSpacing:1, timeVisible:false, secondsVisible:false,
        tickMarkFormatter:(time,type) => {
          const date=new Date(dateKey(time)+'T12:00:00Z');
          return new Intl.DateTimeFormat(zh()?'zh-CN':'en-US',type===0?{year:'numeric',timeZone:'UTC'}:type===1?{month:'short',year:'2-digit',timeZone:'UTC'}:{month:'short',day:'numeric',timeZone:'UTC'}).format(date);
        } },
      crosshair:{mode:0,vertLine:{color:color('--muted'),labelBackgroundColor:color('--panel2')},horzLine:{color:color('--muted'),labelBackgroundColor:color('--panel2')}},
      localization:{locale:zh()?'zh-CN':'en-US',dateFormat:'yyyy-MM-dd',priceFormatter:value => format(value,priceKey==='spot'||priceKey==='spx_close'?0:1)},
      handleScroll:{mouseWheel:false,pressedMouseMove:true,horzTouchDrag:true,vertTouchDrag:false},
      handleScale:{axisPressedMouseMove:true,mouseWheel:false,pinch:true}
    };
  }
  class History {
    constructor(key, rows) {
      this.key=key; this.all=Array.isArray(rows)?rows:[]; this.rows=[]; this.charts=[]; this.lock=false;
      let saved=null; try {saved=localStorage.getItem(storageKeys[key]);} catch (_) {}
      this.range=readRange(saved,allowed[key],defaults[key]);
      this.buttons=Array.from(document.querySelectorAll('[data-chart="'+key+'"][data-range]'));
      this.buttons.forEach(button => {
        button.disabled=!this.all.length;
        button.addEventListener('click',() => {
          this.range=Number(button.dataset.range);
          try {localStorage.setItem(storageKeys[key],String(this.range));} catch (_) {}
          this.render(true);
        });
      });
      this.slider=document.querySelector('[data-scrub="'+key+'"]');
      this.slider.addEventListener('input',() => this.select(Number(this.slider.value),true));
      this.detail=document.querySelector('[data-observations="'+key+'"]');
      this.detail.addEventListener('toggle',() => {if(this.detail.open)this.table();});
      const download=document.querySelector('[data-download="'+key+'"]');
      download.parentElement.hidden=false; download.disabled=!this.all.length;
      download.addEventListener('click',() => this.download());
      if(key==='systematic') document.getElementById('msp-fund-series').addEventListener('change',() => this.render(true));
      this.render(true);
    }
    specs() {
      if(this.key==='gamma')return [{id:'gamma-chart',series:['net_gex_bn'],kind:'bars'}, {id:'gamma-price-chart',series:['spot','flip']}];
      return [{id:this.key+'-chart',series:[this.key==='systematic'?document.getElementById('msp-fund-series').value:'cor1m']}];
    }
    makeCharts() {
      if(!window.LightweightCharts || !this.rows.length)return;
      this.specs().forEach(spec => {
        const host=document.getElementById(spec.id);
        if(!host.clientWidth)return;
        host.replaceChildren();
        const chart=window.LightweightCharts.createChart(host,options(host.clientHeight,spec.series[0]));
        const item={chart,host,series:[],meta:[],spec}; this.charts.push(item);
        chart.subscribeCrosshairMove(param => {
          if(this.lock)return;
          const day=dateKey(param.time); const index=this.rows.findIndex(row=>row.date===day);
          if(index>=0)this.select(index,true,item);
        });
        chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
          if(this.lock||!range)return;
          this.lock=true;
          this.charts.forEach(other=>{if(other!==item)other.chart.timeScale().setVisibleLogicalRange(range);});
          this.lock=false;
        });
      });
    }
    render(reset) {
      this.rows=sliceRows(this.all,this.range);
      this.buttons.forEach(button=>button.setAttribute('aria-pressed',String(Number(button.dataset.range)===this.range)));
      this.slider.parentElement.hidden=!this.rows.length;
      this.slider.max=String(Math.max(0,this.rows.length-1)); this.slider.disabled=this.rows.length<2;
      if(!this.charts.length)this.makeCharts();
      const specs=this.specs();
      this.lock=true;
      this.charts.forEach((item,index) => {
        const previous=item.chart.timeScale().getVisibleLogicalRange();
        item.spec=specs[index];
        item.chart.applyOptions(options(item.host.clientHeight,item.spec.series[0]));
        item.series.forEach(s=>item.chart.removeSeries(s)); item.series=[]; item.meta=[];
        // A whitespace anchor retains every actual session in the shared time base.
        const anchor=item.chart.addLineSeries({color:'transparent',lineVisible:false,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
        anchor.setData(this.rows.map(row=>({time:row.date}))); item.series.push(anchor);
        item.spec.series.forEach(key => {
          const meta=fields[key];
          if(item.spec.kind==='bars') {
            const series=item.chart.addHistogramSeries({priceLineVisible:false,lastValueVisible:false,priceFormat:{type:'custom',minMove:.01,formatter:v=>format(v,1)+'B'}});
            series.setData(this.rows.map(row=>finite(row[key])===null?{time:row.date}:{time:row.date,value:row[key],color:color(row[key]>=0?'--ink-info':'--ink-warn')}));
            series.createPriceLine({price:0,color:color('--muted'),lineWidth:1,lineStyle:2,axisLabelVisible:false});
            item.series.push(series);item.meta.push({series,key});
          } else {
            // Separate series guarantee real line breaks; whitespace alone can
            // retain a time slot while still joining line endpoints in some engines.
            segments(this.rows,key).forEach(run => {
              const series=item.chart.addLineSeries({color:color(meta.color),lineWidth:2,lineStyle:meta.dash?2:0,
                priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:true,pointMarkersVisible:run.length===1,pointMarkersRadius:2,
                priceFormat:{type:'custom',minMove:.01,formatter:v=>format(v,key==='spot'||key==='flip'||key==='spx_close'?0:2)}});
              series.setData(run); item.series.push(series); item.meta.push({series,key,first:run[0].time,last:run.at(-1).time});
            });
          }
        });
        this.lock=true;
        if(!reset&&previous)item.chart.timeScale().setVisibleLogicalRange(previous);else item.chart.timeScale().fitContent();
      });
      this.lock=false;
      if(!this.charts.length) {
        this.specs().forEach(spec=>{
          const host=document.getElementById(spec.id), message=document.createElement('p');message.className='msp-chart-unavailable';
          message.textContent=this.rows.length?L('The chart could not load. Explore the exact observations below.','图表未能加载，请在下方查看精确观测数据。'):L('No chart history is available for this measure.','该指标暂无可用图表历史。');host.replaceChildren(message);
        });
      }
      this.summary(); this.select(reset?this.rows.length-1:Math.min(Number(this.slider.value),this.rows.length-1));
      if(this.detail.open)this.table();
    }
    select(index, sync=false, origin=null) {
      const row=this.rows[index]; if(!row)return;
      this.slider.value=String(index); this.slider.setAttribute('aria-valuetext',row.date+' · '+keys[this.key].map(k=>label(k)+': '+format(row[k])).join('; '));
      const readout=document.getElementById(this.key+'-readout'), day=document.createElement('span');
      day.className='msp-chart-date';day.textContent=row.date;readout.replaceChildren(day);
      keys[this.key].forEach(key=>{
        const span=document.createElement('span'), strong=document.createElement('strong');
        span.append(document.createTextNode(label(key)+' '));strong.textContent=format(row[key]);span.append(strong);readout.append(span);
      });
      if(sync) {
        this.lock=true;
        this.charts.forEach(item=>{
          if(item===origin)return;
          const target=item.meta.find(m=>finite(row[m.key])!==null&&(!m.first||(m.first<=row.date&&m.last>=row.date)));
          if(target&&typeof item.chart.setCrosshairPosition==='function')item.chart.setCrosshairPosition(row[target.key],row.date,target.series);
          else if(typeof item.chart.clearCrosshairPosition==='function')item.chart.clearCrosshairPosition();
        });
        this.lock=false;
      }
    }
    summary() {
      const s=describeRows(this.rows,primary[this.key]);
      document.getElementById(this.key+'-range-status').textContent=s.first?
        s.count+L(' observations · ',' 个观测 · ')+s.first+' — '+s.last+(s.gaps?' · '+s.gaps+L(' missing sessions',' 个缺失交易日'):''):
        L('No chart history available','暂无图表历史');
    }
    table() {
      const table=document.getElementById(this.key+'-table'), fragment=document.createDocumentFragment();
      this.rows.forEach(row=>{
        const tr=document.createElement('tr');
        [row.date,...keys[this.key].map(key=>format(row[key],fields[key].digits))].forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td);});
        fragment.append(tr);
      });
      table.querySelector('tbody').replaceChildren(fragment);
      table.querySelector('caption').textContent=this.rows.length+L(' sessions in the selected range. A dash means unavailable.',' 个所选范围内交易日。「—」表示数据暂缺。');
    }
    download() {
      if(!this.rows.length)return;
      const quote=value=>'"'+String(value).replace(/"/g,'""')+'"';
      const lines=[['date',...keys[this.key].map(key=>fields[key].en+' ('+fields[key].unit+')')],
        ...this.rows.map(row=>[row.date,...keys[this.key].map(key=>finite(row[key])===null?'':row[key])])];
      const url=URL.createObjectURL(new Blob(['\uFEFF'+lines.map(row=>row.map(quote).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}));
      const a=document.createElement('a');a.href=url;a.download='market-structure-'+this.key+'-'+this.rows[0].date+'-'+this.rows.at(-1).date+'.csv';
      document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);
    }
  }
  const widgets=[];
  function age() {
    const now=Date.now();let gammaStale=false;
    document.querySelectorAll('[data-observation][data-expires]').forEach(node=>{
      if(now>=Date.parse(node.dataset.expires)) {
        node.classList.add('stale');
        if(node.dataset.observation==='gamma')gammaStale=true;
      }
    });
    if(gammaStale)document.getElementById('msp-age-warning').hidden=false;
    const weekly=document.querySelector('[data-week-end]');
    if(weekly) {
      const p=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(now));
      const part=type=>p.find(x=>x.type===type).value, today=part('year')+'-'+part('month')+'-'+part('day');
      if(today>weekly.dataset.weekEnd)document.getElementById('msp-week-status').textContent=L('Archived week','历史周度');
    }
  }
  function labels() {
    document.querySelectorAll('[data-label-en]').forEach(node=>node.setAttribute('aria-label',node.dataset[zh()?'labelZh':'labelEn']));
    document.querySelectorAll('#msp-fund-series option').forEach(node=>node.textContent=node.dataset[zh()?'zh':'en']);
    document.querySelectorAll('[data-range]').forEach(button=>{
      const names={21:['1 month','1个月'],63:['3 months','3个月'],126:['6 months','6个月'],252:['1 year','1年'],9999:['All available history','全部可用历史']};
      button.setAttribute('aria-label',names[button.dataset.range][zh()?1:0]);
    });
  }
  function init() {
    let payload={};try {payload=JSON.parse(document.getElementById('msp-chart-data').textContent);} catch (_) {}
    labels();
    Object.keys(keys).forEach(key=>{
      try {widgets.push(new History(key,payload[key]||[]));}
      catch(error) {document.getElementById('market-structure').dataset.chartError='true';console.error('Market Structure chart:',key,error);}
    });
    document.getElementById('market-structure').dataset.chartStatus=window.LightweightCharts?'ready':'unavailable';
    let repaint=0;
    const refresh=()=>{cancelAnimationFrame(repaint);repaint=requestAnimationFrame(()=>{labels();widgets.forEach(w=>w.render(false));age();});};
    document.addEventListener('themechange',refresh);document.addEventListener('langchange',refresh);
    new MutationObserver(refresh).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme','data-lang']});
    age();setInterval(age,60000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)age();});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
