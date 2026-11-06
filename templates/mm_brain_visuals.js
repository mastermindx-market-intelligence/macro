/* Mastermind AI native visual templates. Model input is data, never markup/code.
   The existing Brain widget owns transport, conversation identity and lifecycle. */
(function () {
  'use strict';
  if (window.MMBrainVisuals) return;
  var templates = ['bar','line','area','scatter','donut','table','metrics','status','scenarios','timeline','flow'];
  var unsafe = /<\s*[/!a-z]|https?:\/\/|javascript\s*:|data\s*:|[\x00-\x08\x0b\x0c\x0e-\x1f\u202a-\u202e\u2066-\u2069]/i;
  var NS = 'http://www.w3.org/2000/svg';
  function number(v) { return typeof v === 'number' && Number.isFinite(v) && Math.abs(v) <= 1e15; }
  function text(v, required) { return typeof v === 'string' && v.length <= 500 && (!required || v.trim()) && !unsafe.test(v); }
  function keys(v, names) { return v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).sort().join('|') === names.slice().sort().join('|'); }
  function zh() { return document.documentElement.dataset.lang === 'zh'; }
  function L(en, cn) { return zh() ? cn : en; }
  function node(tag, cls, value) { var e = document.createElement(tag); if (cls) e.className = cls; if (value !== undefined) e.textContent = value; return e; }
  function label(tag, cls, en, cn) { var e = node(tag, cls, L(en, cn)); e.dataset.en = en; e.dataset.zh = cn; return e; }
  function svg(tag, attrs, value) { var e = document.createElementNS(NS, tag); Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, String(attrs[k])); }); if (value !== undefined) e.textContent = value; return e; }
  function value(v) { return v === null ? '—' : String(v); }
  function validate(wire) {
    try {
      if (!keys(wire, ['type','visual_id','visual']) || wire.type !== 'chart' || !/^[a-f0-9]{24}$/.test(wire.visual_id)) return false;
      if (new TextEncoder().encode(JSON.stringify(wire)).length > 65536) return false;
      var s = wire.visual;
      if (!keys(s, ['version','template','basis','title','subtitle','takeaway','unit','columns','rows','provenance'])) return false;
      if (s.version !== 1 || !templates.includes(s.template) || !['source','illustrative'].includes(s.basis)) return false;
      if (!text(s.title, true) || !['subtitle','takeaway','unit'].every(function (k) { return text(s[k]); })) return false;
      if (!Array.isArray(s.columns) || s.columns.length < 2 || s.columns.length > 6 || !s.columns.every(function (c) { return text(c, true); }) || new Set(s.columns).size !== s.columns.length) return false;
      if (!Array.isArray(s.rows) || !s.rows.length || s.rows.length > 80) return false;
      if (!s.rows.every(function (r) { return Array.isArray(r) && r.length === s.columns.length && r.every(function (c) { return c === null || number(c) || text(c); }); })) return false;
      var numeric = s.rows.flat().filter(number).length;
      if (['bar','line','area','scatter','donut'].includes(s.template)) {
        if (!s.rows.every(function (r) { return (s.template === 'scatter' ? (r[0] === null || number(r[0])) : text(r[0], true)) && r.slice(1).every(function (v) { return v === null || number(v); }); })) return false;
        if (!s.rows.some(function (r) { return r.slice(1).some(number); })) return false;
      }
      if (s.template === 'donut' && (s.columns.length !== 2 || s.rows.length > 12 || s.rows.some(function (r) { return r[1] !== null && r[1] < 0; }) || s.rows.reduce(function (sum,r) { return sum + (r[1] || 0); },0) <= 0)) return false;
      if (['status','scenarios','timeline','flow'].includes(s.template) && (s.columns.length > 3 || s.rows.length > 20 || !s.rows.every(function (r) { return r.every(function (c) { return c === null || text(c); }); }))) return false;
      if (s.template === 'metrics' && (s.columns.length > 3 || s.rows.length > 6)) return false;
      var p = s.provenance;
      if (!(keys(p, ['numeric_cells_matched','sources','semantic_verification','freshness_verified']) || keys(p, ['numeric_cells_matched','text_cells_matched','sources','semantic_verification','freshness_verified'])) || p.semantic_verification !== false || p.freshness_verified !== false || !Number.isInteger(p.numeric_cells_matched)) return false;
      if (!Array.isArray(p.sources) || p.sources.length > 40 || !p.sources.every(function (t) { return typeof t === 'string' && /^[A-Za-z][A-Za-z0-9_]{0,79}$/.test(t); })) return false;
      var narrative = ['status','scenarios','timeline','flow'].includes(s.template);
      var required = s.rows.reduce(function (sum,r) { return sum + r.filter(function (c,i) { return c !== null && (narrative || i > 0 || number(c)); }).length; },0);
      var textCount = p.text_cells_matched === undefined ? 0 : p.text_cells_matched;
      if (!Number.isInteger(textCount)) return false;
      return s.basis === 'source' ? required > 0 && p.numeric_cells_matched === numeric && textCount === required-numeric && p.sources.length > 0 : p.numeric_cells_matched === 0 && textCount === 0 && p.sources.length === 0;
    } catch (_) { return false; }
  }
  function csv(s) {
    return [s.columns].concat(s.rows).map(function (r) { return r.map(function (v) {
      var t = v === null ? '' : String(v);
      if (typeof v === 'string' && /^[\s]*[=+\-@]/.test(t)) t = "'" + t;
      return '"' + t.replace(/"/g, '""') + '"';
    }).join(','); }).join('\r\n');
  }
  function table(s) {
    var wrap = node('div','mmb-v-table-wrap'), t = node('table','mmb-v-table');
    var cap = node('caption','mmb-v-sr',s.title); t.appendChild(cap);
    var head = node('thead'), tr = node('tr');
    s.columns.forEach(function (c) { var th = node('th','',c); th.scope = 'col'; tr.appendChild(th); });
    head.appendChild(tr); t.appendChild(head);
    var body = node('tbody');
    s.rows.forEach(function (r) { var row = node('tr'); r.forEach(function (v, i) { var cell = node(i ? 'td' : 'th',number(v) ? 'mmb-v-number' : '',value(v)); if (!i) cell.scope = 'row'; row.appendChild(cell); }); body.appendChild(row); });
    t.appendChild(body); wrap.appendChild(t); wrap.tabIndex = 0; wrap.setAttribute('role','region'); wrap.setAttribute('aria-label',s.title); return wrap;
  }
  function domain(values, zero) {
    var lo = Math.min.apply(null,values), hi = Math.max.apply(null,values);
    if (zero) { lo = Math.min(0,lo); hi = Math.max(0,hi); }
    var pad = hi === lo ? Math.max(Math.abs(lo) * 0.04, 1e-9) : (hi-lo) * 0.08;
    return [lo - (zero && lo === 0 ? 0 : pad), hi + (zero && hi === 0 ? 0 : pad)];
  }
  function tickText(v, span) {
    if (Math.abs(v) < Math.abs(span)*1e-12) v = 0;
    var decimals = Math.max(0, Math.min(14, -Math.floor(Math.log10(Math.abs(span)/4)) + 1));
    return Math.abs(v) >= 1e10 || (v !== 0 && Math.abs(v) < 1e-10) ? v.toExponential(3) : Number(v.toFixed(decimals)).toLocaleString(zh() ? 'zh-CN' : 'en-US', {maximumFractionDigits:14});
  }
  function plot(host, s, hidden) {
    var width = Math.floor(host.getBoundingClientRect().width);
    if (width < 120) return;
    var h = 260, left = 66, right = 18, top = 20, bottom = 40, pw = width-left-right, ph = h-top-bottom;
    host.textContent = '';
    var root = svg('svg',{viewBox:'0 0 '+width+' '+h, width:width, height:h, role:'img', 'aria-label':s.title});
    root.appendChild(svg('title',{},s.title));
    root.appendChild(svg('desc',{},L('Complete values are in the data table below. Missing observations are gaps.','完整数值见下方数据表。缺失观测以间隔表示。')));
    host.appendChild(root);
    if (s.template === 'donut') {
      var total = s.rows.reduce(function (sum,r) { return sum + (r[1] || 0); },0), radius = 76, circumference = 2*Math.PI*radius, offset = 0;
      s.rows.forEach(function (r,i) {
        if (r[1] === null || r[1] === 0) return;
        var length = r[1]/total*circumference;
        var c = svg('circle',{cx:width/2,cy:118,r:radius,fill:'none','stroke-width':30,'stroke-dasharray':length+' '+(circumference-length),'stroke-dashoffset':-offset,transform:'rotate(-90 '+width/2+' 118)',class:'mmb-v-ring mmb-v-series-'+(i%5)});
        c.appendChild(svg('title',{},r[0]+': '+value(r[1]))); root.appendChild(c); offset += length;
      });
      root.appendChild(svg('text',{x:width/2,y:114,'text-anchor':'middle',class:'mmb-v-total'},value(total)));
      root.appendChild(svg('text',{x:width/2,y:137,'text-anchor':'middle',class:'mmb-v-axis'},L('Shown total','已列合计'))); return;
    }
    var ys = s.rows.flatMap(function (r) { return r.slice(1).filter(number); });
    var yd = domain(ys, s.template === 'bar' || s.template === 'area');
    var y = function (v) { return top + ph - (v-yd[0])/(yd[1]-yd[0])*ph; };
    var xs = s.rows.map(function (r) { return r[0]; }).filter(number), xd = s.template === 'scatter' && xs.length ? domain(xs,false) : [0,1];
    var x = function (i,v) { if (s.template === 'scatter') return left + (v-xd[0])/(xd[1]-xd[0])*pw; return s.template === 'bar' ? left + (i+0.5)*pw/s.rows.length : left + (s.rows.length === 1 ? pw/2 : i*pw/(s.rows.length-1)); };
    var ticks = Array.from({length:5},function (_,i) { return yd[0]+(yd[1]-yd[0])*i/4; });
    if (yd[0] <= 0 && yd[1] >= 0) {
      var nearest = ticks.reduce(function (best,v,i) { return Math.abs(v) < Math.abs(ticks[best]) ? i : best; },0);
      ticks[nearest] = 0;  // label the actual shared baseline, not a rounded nearby tick
    }
    var labels = ticks.map(function (v) { return tickText(v,yd[1]-yd[0]); });
    if (new Set(labels).size !== labels.length) labels = ticks.map(String);
    ticks.forEach(function (v,i) { root.appendChild(svg('line',{x1:left,x2:width-right,y1:y(v),y2:y(v),class:'mmb-v-grid'})); root.appendChild(svg('text',{x:left-8,y:y(v)+4,'text-anchor':'end',class:'mmb-v-axis','data-tick':''},labels[i])); });
    if (yd[0] <= 0 && yd[1] >= 0) root.appendChild(svg('line',{x1:left,x2:width-right,y1:y(0),y2:y(0),class:'mmb-v-zero','data-zero':''}));
    if (s.unit) root.appendChild(svg('text',{x:left,y:12,class:'mmb-v-axis'},s.unit));
    if (s.template === 'scatter') {
      [0,1,2,3].forEach(function (i) { var v = xd[0]+(xd[1]-xd[0])*i/3; root.appendChild(svg('text',{x:x(0,v),y:h-12,'text-anchor':'middle',class:'mmb-v-axis'},tickText(v,xd[1]-xd[0]))); });
    } else {
      var lastX = -Infinity;
      s.rows.forEach(function (r,i) { var px = x(i); if (px-lastX < 72) return; lastX=px; var t=svg('text',{x:px,y:h-12,'text-anchor':'middle',class:'mmb-v-axis'},r[0].length>12 ? r[0].slice(0,11)+'…' : r[0]); t.appendChild(svg('title',{},r[0])); root.appendChild(t); });
    }
    s.columns.slice(1).forEach(function (_,si) {
      if (hidden.has(si)) return;
      var seriesClass = 'mmb-v-series-'+si;
      if (s.template === 'bar') {
        var group = pw/s.rows.length, bw = group*0.72/(s.columns.length-1);
        s.rows.forEach(function (r,i) { if (r[si+1] === null) return; var v=r[si+1], yy=y(v), zero=y(0); var b=svg('rect',{x:x(i)-group*0.36+si*bw,y:Math.min(yy,zero),width:Math.max(0.5,bw-1),height:Math.abs(yy-zero),rx:Math.min(4,bw/3),class:seriesClass,'data-bar':''}); b.appendChild(svg('title',{},r[0]+' · '+s.columns[si+1]+': '+value(v))); root.appendChild(b); });
        return;
      }
      var segment=[];
      function flush() {
        if (!segment.length || s.template === 'scatter') { segment=[]; return; }
        var d=segment.map(function (p,i) { return (i?'L':'M')+p[0]+' '+p[1]; }).join(' ');
        if (s.template === 'area') { var first=segment[0], last=segment[segment.length-1]; root.appendChild(svg('path',{d:d+' L'+last[0]+' '+y(0)+' L'+first[0]+' '+y(0)+' Z',class:seriesClass+' mmb-v-area'})); }
        root.appendChild(svg('path',{d:d,fill:'none','stroke-width':2,class:seriesClass+' mmb-v-line','data-series':si})); segment=[];
      }
      s.rows.forEach(function (r,i) {
        if (r[si+1] === null || (s.template === 'scatter' && r[0] === null)) { flush(); return; }
        var px=x(i,r[0]), py=y(r[si+1]); segment.push([px,py]);
        var dot=svg('circle',{cx:px,cy:py,r:s.template === 'scatter'?4:2.7,class:seriesClass}); dot.appendChild(svg('title',{},value(r[0])+' · '+s.columns[si+1]+': '+value(r[si+1]))); root.appendChild(dot);
      }); flush();
    });
  }
  function narrative(s) {
    var kind=s.template, wrapper=node(kind === 'timeline' || kind === 'flow' ? 'ol' : 'div','mmb-v-'+kind);
    s.rows.forEach(function (r) {
      var row=node(kind === 'timeline' || kind === 'flow' ? 'li' : 'div','mmb-v-row');
      if (kind === 'metrics') {
        row.appendChild(node('div','mmb-v-label',value(r[0]))); row.appendChild(node('div','mmb-v-metric',value(r[1])+(s.unit?' '+s.unit:'')));
        if (r.length>2) row.appendChild(node('div','mmb-v-detail',value(r[2])));
      } else {
        row.appendChild(node('div','mmb-v-label',value(r[0])));
        var body=node('div','mmb-v-row-body'); body.appendChild(node('div',kind === 'status'?'mmb-v-state':'mmb-v-row-title',value(r[1])));
        if (r.length>2 && r[2] !== null) body.appendChild(node('p','mmb-v-detail',value(r[2])));
        row.appendChild(body);
      }
      wrapper.appendChild(row);
    }); return wrapper;
  }
  function mount(host, wire) {
    if (!host || !validate(wire)) return false;
    if (host.querySelector('[data-visual-id="'+wire.visual_id+'"]')) return true;
    var s=wire.visual, figure=node('figure','mmb-v'); figure.dataset.visualId=wire.visual_id; figure.dataset.template=s.template;
    var caption=node('figcaption'); caption.appendChild(node('h3','mmb-v-title',s.title));
    if (s.subtitle) caption.appendChild(node('p','mmb-v-subtitle',s.subtitle)); figure.appendChild(caption);
    figure.appendChild(s.basis === 'illustrative' ? label('p','mmb-v-basis','Illustrative · not verified market data','示意 · 非经核实的市场数据') : label('p','mmb-v-basis','Data values match retrieved output · labels and interpretation are AI-generated','数据值与已读取内容一致 · 标签及解读由 AI 生成'));
    var isPlot=['bar','line','area','scatter','donut'].includes(s.template), resize, draw;
    if (isPlot) {
      var body=node('div','mmb-v-plot'), hidden=new Set(); figure.appendChild(body);
      draw=function () { plot(body,s,hidden); }; figure._draw=draw;
      var legend=node('div','mmb-v-legend');
      var entries=s.template === 'donut' ? s.rows.map(function (r) { return r[0]; }) : s.columns.slice(1);
      entries.forEach(function (entry,i) {
        var button=node(s.template === 'donut'?'span':'button','mmb-v-legend-item');
        button.appendChild(node('span','mmb-v-swatch mmb-v-series-'+(i%5),'—')); button.appendChild(node('span','',entry));
        if (s.template !== 'donut') { button.type='button'; button.setAttribute('aria-pressed','true'); button.addEventListener('click',function () { if (hidden.has(i)) hidden.delete(i); else hidden.add(i); button.setAttribute('aria-pressed',String(!hidden.has(i))); draw(); }); }
        legend.appendChild(button);
      }); figure.appendChild(legend);
      resize=new ResizeObserver(function () {
        var rendered=body.querySelector('svg'), width=Math.floor(body.getBoundingClientRect().width);
        // The initial notification must not detach a correctly sized live plot.
        if (rendered && Number(rendered.getAttribute('width')) === width) return;
        draw();
      }); figure._resize=resize;
    } else if (s.template === 'table') figure.appendChild(table(s));
    else figure.appendChild(narrative(s));
    if (s.template === 'donut' && s.rows.some(function (r) { return r[1] === null; })) figure.appendChild(label('p','mmb-v-detail','Shares use known values only; missing categories are not zero.','占比仅基于已知数值，缺失类别不代表零。'));
    if (s.template === 'bar' || s.template === 'area') {
      var magnitudes = s.rows.flatMap(function (r) { return r.slice(1).filter(number).map(Math.abs); });
      var largest = Math.max.apply(null, magnitudes);
      if (magnitudes.some(function (v) { return v > 0 && v < largest / 260; })) figure.appendChild(label('p','mmb-v-detail','Some nonzero values are too small to see at this scale. Exact values remain in the data table.','部分非零数值在此比例下过小而无法看清，完整数值仍列于数据表。'));
    }
    if (s.takeaway) figure.appendChild(node('p','mmb-v-takeaway',s.takeaway));
    var details=node('details','mmb-v-details'); details.appendChild(label('summary','','Data and source details','数据及来源详情'));
    if (s.template !== 'table') details.appendChild(table(s));
    details.appendChild(label('p','mmb-v-detail','This is a saved response snapshot, not a live feed. Value matching does not verify freshness, labels, units or conclusions.','这是回答快照，并非实时数据流。数值匹配不代表已核实新鲜度、标签、单位或结论。'));
    if (s.provenance.sources.length) details.appendChild(node('p','mmb-v-detail',s.provenance.sources.join(' · ')));
    var download=label('button','mmb-v-export','Export CSV','导出 CSV'); download.type='button';
    download.addEventListener('click',function () { var url=URL.createObjectURL(new Blob(['\ufeff'+csv(s)],{type:'text/csv;charset=utf-8'})); var a=node('a'); a.href=url; a.download='mastermind-visual.csv'; a.click(); setTimeout(function () { URL.revokeObjectURL(url); },1000); }); details.appendChild(download); figure.appendChild(details);
    host.appendChild(figure); if (resize) { resize.observe(figure.querySelector('.mmb-v-plot')); draw(); } return true;
  }
  function clear(host) { if (!host) return; host.querySelectorAll('.mmb-v').forEach(function (f) { if (f._resize) f._resize.disconnect(); f.remove(); }); }
  new MutationObserver(function () { document.querySelectorAll('.mmb-v [data-en]').forEach(function (e) { e.textContent=zh()?e.dataset.zh:e.dataset.en; }); document.querySelectorAll('.mmb-v').forEach(function (f) { if (f._draw) f._draw(); }); }).observe(document.documentElement,{attributes:true,attributeFilter:['data-lang']});
  window.MMBrainVisuals={mount:mount,clear:clear,validate:validate,csv:csv};
}());
