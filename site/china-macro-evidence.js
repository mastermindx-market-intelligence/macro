/* No network, no model outputs: inspect the same canonical observations as JSON.
   Scoped to the four evidence dialogs; other China page interactions are untouched. */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const lang = () => document.documentElement.dataset.lang === 'zh';
  const tr = (en, zh) => lang() ? zh : en;
  const valid = v => typeof v === 'number' && Number.isFinite(v);
  const svgNode = (tag, attrs, text) => {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, String(v)));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const dateNumber = s => /^\d{4}-\d{2}-\d{2}$/.test(s) ? Date.parse(s + 'T00:00:00Z') : NaN;
  function mountChart(card) {
    const payload = card.querySelector('[data-cnm-series]');
    const select = card.querySelector('[data-cnm-select]');
    const plot = card.querySelector('[data-cnm-plot]');
    const readout = card.querySelector('[data-cnm-readout]');
    if (!payload || !select || !plot || card.dataset.cnmMounted) return;
    let series;
    try { series = JSON.parse(payload.textContent); } catch (_) { return; }
    if (!Array.isArray(series)) return;
    card.dataset.cnmMounted = 'true';
    let windowSize = 252, selectedIndex = -1, scale = null, visible = [], current = null;
    const W = 640, H = 204, L = 12, R = 72, T = 20, B = 30;
    const fmt = (v, digits = 2) => valid(v) ? v.toLocaleString(lang() ? 'zh-CN' : 'en-US', {maximumFractionDigits: digits}) : '—';
    function localize() {
      Array.from(select.options).forEach(o => { const data = series.find(m => m.id === o.value); o.textContent = (lang() ? o.dataset.zh : o.dataset.en) + (data ? ' · ' + data.unit : ''); });
      plot.setAttribute('aria-label', tr('History chart. Left and right arrow keys inspect observations.', '历史图。使用左右方向键逐次查看观测。'));
      const svg=plot.querySelector('svg');if(svg && current)svg.setAttribute('aria-label',(lang()?current.label_zh:current.label_en)+' · '+current.unit);
      card.querySelector('.cnm-ranges').setAttribute('aria-label', tr('Number of observations shown, not calendar days', '显示观测次数，而非日历天数'));
    }
    function inspect(index, announce = false) {
      if (!scale || !visible.length) return;
      selectedIndex = Math.max(0, Math.min(visible.length - 1, index));
      const d = visible[selectedIndex], svg = plot.querySelector('svg');
      if (!svg) return;
      svg.querySelectorAll('.cnm-cursor,.cnm-point').forEach(n => n.remove());
      const x = scale.x(d.t);
      svg.append(svgNode('line', {x1:x, x2:x, y1:T, y2:H-B, class:'cnm-cursor'}));
      if (valid(d.v)) svg.append(svgNode('circle', {cx:x, cy:scale.y(d.v), r:4, class:'cnm-point'}));
      // Mouse scrubbing does not produce a stream of screen-reader live announcements.
      readout.setAttribute('aria-live', announce ? 'polite' : 'off');
      readout.textContent = d.date + ' · ' + fmt(d.v, 4) + ' ' + current.unit + (valid(d.v) ? '' : tr(' · Missing observation', ' · 观测缺失'));
    }
    function draw() {
      current = series.find(m => m.id === select.value);
      if (!current || !current.chart || !Array.isArray(current.chart.dates) || !Array.isArray(current.chart.vals)) return;
      if (current.chart.dates.length !== current.chart.vals.length) return;
      let pairs = current.chart.dates.map((date, i) => ({date, t:dateNumber(date), v:valid(current.chart.vals[i]) ? current.chart.vals[i] : null}));
      if (pairs.some(d => !Number.isFinite(d.t)) || pairs.some((d,i) => i && d.t <= pairs[i-1].t)) return;
      visible = windowSize === 'all' ? pairs : pairs.slice(-windowSize);
      const usable = visible.filter(d => valid(d.v));
      plot.replaceChildren(); scale = null;
      card.querySelector('[data-cnm-unit]').textContent = current.unit;
      if (usable.length < 2) {
        localize();
        const empty = document.createElement('p'); empty.className = 'cnm-caveat';
        empty.textContent = tr('Not enough known observations in this window. No trend is extrapolated.', '当前窗口有效观测不足；不外推趋势。');
        plot.append(empty); readout.textContent = ''; return;
      }
      let lo = Math.min(...usable.map(d => d.v)), hi = Math.max(...usable.map(d => d.v));
      const baseline = valid(current.reference) ? current.reference : current.chart_kind === 'bars' ? 0 : null;
      if (baseline !== null) {lo = Math.min(lo, baseline); hi = Math.max(hi, baseline);}
      const pad = (hi-lo)*.12 || Math.max(Math.abs(hi)*.05, 1); lo -= pad; hi += pad;
      const span = visible[visible.length-1].t-visible[0].t || 1;
      scale = {x:t => L+(t-visible[0].t)/span*(W-L-R), y:v => T+(hi-v)/(hi-lo)*(H-T-B)};
      const svg = svgNode('svg', {viewBox:`0 0 ${W} ${H}`, class:'cnm-svg', role:'img', 'aria-label':(lang() ? current.label_zh : current.label_en)+' · '+current.unit});
      for (let i=0; i<3; i++) {
        const y=T+i*(H-T-B)/2;
        svg.append(svgNode('line',{x1:L,y1:y,x2:W-R,y2:y,class:'cnm-gridline'}));
        svg.append(svgNode('text',{x:W-R+8,y:y+4,class:'cnm-axis'},fmt(hi-i*(hi-lo)/2)));
      }
      if (baseline !== null) svg.append(svgNode('line',{x1:L,y1:scale.y(baseline),x2:W-R,y2:scale.y(baseline),class:'cnm-zero'}));
      let path = '';
      const flush = () => {if(path) svg.append(svgNode('path',{d:path,class:'cnm-line'})); path='';};
      visible.forEach(d => {
        if (!valid(d.v)) {flush(); return;}
        const x=scale.x(d.t),y=scale.y(d.v);
        if (current.chart_kind === 'bars') svg.append(svgNode('line',{x1:x,x2:x,y1:scale.y(baseline || 0),y2:y,class:'cnm-bar '+(d.v<0?'negative':'positive')}));
        else path += (path ? ' L' : 'M')+x.toFixed(2)+','+y.toFixed(2);
      }); flush();
      svg.append(svgNode('text',{x:L,y:H-5,class:'cnm-axis'},visible[0].date));
      svg.append(svgNode('text',{x:W-R,y:H-5,class:'cnm-axis','text-anchor':'end'},visible[visible.length-1].date));
      plot.append(svg);
      selectedIndex=visible.length-1; inspect(selectedIndex);
      localize();
    }
    select.addEventListener('change', draw);
    card.querySelectorAll('[data-cnm-range]').forEach(button => button.addEventListener('click', () => {
      windowSize = button.dataset.cnmRange === 'all' ? 'all' : Number(button.dataset.cnmRange);
      card.querySelectorAll('[data-cnm-range]').forEach(b => b.setAttribute('aria-pressed', b===button ? 'true' : 'false'));
      draw();
    }));
    plot.addEventListener('pointermove', event => {
      if (!scale || !visible.length) return;
      const rect=plot.querySelector('svg').getBoundingClientRect(), x=(event.clientX-rect.left)/rect.width*W;
      let nearest=0, delta=Infinity;
      visible.forEach((d,i) => {const distance=Math.abs(scale.x(d.t)-x);if(distance<delta){delta=distance;nearest=i;}});
      inspect(nearest);
    });
    plot.addEventListener('keydown', event => {
      if (event.key==='ArrowLeft' || event.key==='ArrowRight') {event.preventDefault();inspect(selectedIndex+(event.key==='ArrowLeft'?-1:1),true);}
      if (event.key==='Home' || event.key==='End') {event.preventDefault();inspect(event.key==='Home'?0:visible.length-1,true);}
    });
    card.querySelector('[data-cnm-export]').addEventListener('click', () => {
      if(!current) return;
      const safe = s => {s=String(s??'');if(/^[=+\-@\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};
      const lines = ['reference_date,value,unit,metric,status'];
      current.chart.dates.forEach((date,i) => lines.push([safe(date),valid(current.chart.vals[i])?String(current.chart.vals[i]):'',safe(current.unit),safe(current.id),safe(current.status)].join(',')));
      const url=URL.createObjectURL(new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'}));
      const a=document.createElement('a');a.href=url;a.download='china-'+current.id+'-observations.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    });
    const observer = new MutationObserver(() => {localize();if(selectedIndex>=0)inspect(selectedIndex);});
    observer.observe(document.documentElement,{attributes:true,attributeFilter:['data-lang']});
    draw();
  }
  const focusable = root => Array.from(root.querySelectorAll('button,a[href],select,summary,[tabindex]:not([tabindex="-1"])')).filter(el => !el.disabled && el.getClientRects().length);
  function init() {
    const dialogs = document.querySelectorAll('[data-cnm-dialog]');
    dialogs.forEach(dialog => {
      let previous = null, wasOpen = false;
      function sync() {
        const open=dialog.classList.contains('open');
        if (open && !wasOpen) {
          previous=document.activeElement;
          dialog.querySelectorAll('[data-cnm-chart-card]').forEach(mountChart);
          const close=dialog.querySelector('.cnm-close');if(close)close.focus({preventScroll:true});
        }
        if (!open && wasOpen && previous && previous.isConnected && !dialog.contains(previous)) previous.focus({preventScroll:true});
        wasOpen=open;
      }
      new MutationObserver(sync).observe(dialog,{attributes:true,attributeFilter:['class']});sync();
      dialog.addEventListener('keydown', event => {
        if (!dialog.classList.contains('open'))return;
        if(event.key==='Tab') {
          const nodes=focusable(dialog),first=nodes[0],last=nodes[nodes.length-1];
          if(!first)return;
          if(event.shiftKey && (document.activeElement===first || !dialog.contains(document.activeElement))) {event.preventDefault();last.focus();}
          else if(!event.shiftKey && document.activeElement===last) {event.preventDefault();first.focus();}
        }
        if(event.key==='Escape' && typeof window.cnxCloseDlg==='function') {event.preventDefault();window.cnxCloseDlg();}
      });
      dialog.querySelectorAll('[data-cnm-method-link]').forEach(a => a.addEventListener('click',event=>{
        event.preventDefault();const target=document.getElementById(a.hash.slice(1));if(!target)return;
        const details=target.closest('details');if(details)details.open=true;target.scrollIntoView({block:'start'});target.focus({preventScroll:true});
      }));
    });
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
