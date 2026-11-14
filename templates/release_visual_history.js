/* Source-qualified MRI history. Projection only; inherits Release Radar's existing fetch. */
(function (global) {
  'use strict';
  var NAMESPACE = 'http://www.w3.org/2000/svg';
  var SERIES = [
    ['ppi_finaldemand', 'PPI final demand', '\u751f\u4ea7\u8005\u4ef7\u683c'],
    ['cpi_headline', 'CPI', '\u6d88\u8d39\u8005\u4ef7\u683c'],
    ['cpi_core', 'Core CPI', '\u6838\u5fc3 CPI'],
    ['pce_headline', 'PCE', 'PCE \u4ef7\u683c'],
    ['pce_core', 'Core PCE', '\u6838\u5fc3 PCE']
  ];
  var target = 'ppi_finaldemand', basis = 'yoy', windowMonths = 36;
  var snapshot = null, comparison = null;
  function byRole(host, selector) { return host.querySelector(selector); }
  function bilingual(node, en, zh) {
    if (!node) return;
    node.textContent = '';
    [['l-en', en], ['l-zh', zh]].forEach(function (pair) {
      var span = document.createElement('span');
      span.className = pair[0];
      span.textContent = pair[1];
      node.appendChild(span);
    });
  }
  function authorized(value) {
    return !!value && value.display_only === true && value.authority &&
      ['can_score','can_rank','can_gate','can_size','can_trade'].every(function (field) {
        return value.authority[field] === false;
      });
  }
  function hasDeniedAuthority(value) {
    return !!value && ['can_score','can_rank','can_gate','can_size','can_trade'].every(function (field) {
      return value[field] === false;
    });
  }
  function monthNumber(period) {
    if (typeof period !== 'string' || !/^(19|20)\d{2}-(0[1-9]|1[0-2])$/.test(period)) return NaN;
    return Number(period.slice(0,4)) * 12 + Number(period.slice(5,7));
  }
  function points(source, max) {
    if (!Array.isArray(source) || source.length > 72) return [];
    var seen = Object.create(null), last = -Infinity, clean = [];
    for (var i=0; i<source.length; i++) {
      var item=source[i], month=item && monthNumber(item.period);
      if (!Number.isFinite(month) || !Number.isFinite(item.value) || seen[month] || month <= last ||
          Math.abs(item.value) > 500) return [];
      seen[month] = true;
      last = month;
      clean.push({period:item.period, month:month, value:item.value});
    }
    return clean.slice(-max);
  }
  function fmt(value, digits) {
    return Number.isFinite(value) ? value.toFixed(digits == null ? 2 : digits) : '\u2014';
  }
  function signed(value) {
    return (value > 0 ? '+' : '') + fmt(value);
  }
  function textNode(tag, className, value) {
    var node=document.createElement(tag);
    if (className) node.className=className;
    if (value != null) node.textContent=value;
    return node;
  }
  function svgNode(tag, attrs) {
    var node=document.createElementNS(NAMESPACE, tag);
    Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, String(attrs[key])); });
    return node;
  }
  function appendLine(svg, x1,y1,x2,y2, extra) {
    var attrs={x1:x1,y1:y1,x2:x2,y2:y2,stroke:'var(--line)', 'stroke-width':1};
    Object.assign(attrs, extra || {});
    svg.appendChild(svgNode('line', attrs));
  }
  function draw(svg, source, language) {
    svg.textContent='';
    if (!source.length) {
      var empty=svgNode('text',{x:355,y:130,'text-anchor':'middle',fill:'var(--muted)','font-size':14});
      empty.textContent = language === 'zh' ? '\u6682\u65e0\u53ef\u6838\u9a8c\u7684\u5386\u53f2\u8d70\u52bf' : 'No qualified history available';
      svg.appendChild(empty);
      return;
    }
    var w=720, h=260, left=52, right=18, top=14, bottom=43;
    var usableW=w-left-right, usableH=h-top-bottom;
    var values=source.map(function (d) { return d.value; });
    var min=Math.min.apply(null, values), max=Math.max.apply(null, values);
    var range=Math.max(max-min,0.30), pad=range * 0.15;
    min -= pad; max += pad;
    var start=source[0].month, end=source[source.length-1].month;
    var x=function (d) { return left+(d.month-start)/Math.max(1,end-start)*usableW; };
    var y=function (value) { return top+(max-value)/(max-min)*usableH; };
    for (var step=0; step<=4; step++) {
      var yAxis=top+step*usableH/4, label=max-step*(max-min)/4;
      appendLine(svg,left,yAxis,w-right,yAxis);
      var lab=svgNode('text',{x:left-9,y:yAxis+4,'text-anchor':'end',fill:'var(--muted)','font-size':11});
      lab.textContent=fmt(label,1)+'%';
      svg.appendChild(lab);
    }
    var tickCount=Math.min(4,source.length-1);
    for (var tick=0; tick<=tickCount;tick++) {
      var idx=Math.round(tick* (source.length-1)/Math.max(1,tickCount));
      var point=source[idx], mark=svgNode('text',{
        x:x(point),y:h-13,'text-anchor':tick===0?'start':tick===tickCount?'end':'middle',
        fill:'var(--muted)','font-size':11
      });
      mark.textContent=point.period;
      svg.appendChild(mark);
    }
    var groups=[], run=[];
    source.forEach(function (point, i) {
      if (i && point.month !== source[i-1].month+1) { if(run.length)groups.push(run); run=[]; }
      run.push(point);
    });
    if(run.length)groups.push(run);
    groups.forEach(function (segment) {
      if (segment.length<2) return;
      var path=segment.map(function (p,i) {return (i?'L':'M')+x(p).toFixed(2)+' '+y(p.value).toFixed(2);}).join(' ');
      var fill=path+' L'+x(segment[segment.length-1]).toFixed(2)+' '+(h-bottom)+
        ' L'+x(segment[0]).toFixed(2)+' '+(h-bottom)+' Z';
      svg.appendChild(svgNode('path',{d:fill,fill:'var(--text)',opacity:'0.075'}));
      svg.appendChild(svgNode('path',{d:path,fill:'none',stroke:'var(--text)','stroke-width':2.4,
        'stroke-linecap':'round','stroke-linejoin':'round'}));
    });
    source.forEach(function (p,i) {
      // Every historical point is inspectable, not only the last observation.
      var hit=svgNode('circle',{cx:x(p),cy:y(p.value),r:8,
        fill:'transparent','pointer-events':'all'});
      var tip=svgNode('title');
      tip.textContent=p.period+' · '+fmt(p.value)+'%';
      hit.appendChild(tip);
      svg.appendChild(hit);
      if (i===source.length-1 || groups.some(function (g) { return g.length===1 && g[0]===p; })) {
        var dot=svgNode('circle',{cx:x(p),cy:y(p.value),r:i===source.length-1?4.8:3.2,
          fill:'var(--text)',stroke:'var(--panel)','stroke-width':2,
          'pointer-events':'none'});
        svg.appendChild(dot);
      }
    });
  }
  function fact(container, en, zh, value, noteEn, noteZh) {
    var row=textNode('div','rrh-fact');
    var name=textNode('span','rrh-fact-name');
    bilingual(name,en,zh);
    var figure=textNode('strong','rrh-fact-value',value);
    row.appendChild(name);row.appendChild(figure);
    if(noteEn || noteZh) {
      var sub=textNode('small','rrh-fact-note');bilingual(sub,noteEn||'',noteZh||'');row.appendChild(sub);
    }
    container.appendChild(row);
  }
  function displayEvidence(data) {
    if (!authorized(data) || data.schema!=='release_surprise_confirmation.v1' ||
        !['available_descriptive','partial','historical_context_only'].includes(data.status) ||
        !Array.isArray(data.latest_releases) || !Number.isFinite(Date.parse(data.asof)) ||
        Date.parse(data.asof)>Date.now() || Date.now()-Date.parse(data.asof)>72*3600000) return null;
    var found = data.latest_releases.filter(function (row) {
      return row && row.release===target && row.unit==='percent' &&
        row.display_derived_allowed===true && row.display_raw_allowed===true &&
        hasDeniedAuthority(row.authority) && Number.isFinite(row.actual) &&
        Number.isFinite(row.consensus) && Number.isFinite(row.surprise) &&
        typeof row.period==='string' && Number.isFinite(monthNumber(row.period)) &&
        Number.isFinite(Date.parse(row.known_at)) && Date.parse(row.known_at)<=Date.now();
    });
    return found.length?found[found.length-1]:null;
  }
  function render(host, history, surprise) {
    if (!host) return;
    snapshot=history;comparison=surprise;
    var selector=byRole(host,'[data-rrh-target]');
    var selectBasis=byRole(host,'[data-rrh-basis]');
    var selectWindow=byRole(host,'[data-rrh-window]');
    var state=byRole(host,'[data-rrh-state]');
    var valueNode=byRole(host,'[data-rrh-value]');
    var deltaNode=byRole(host,'[data-rrh-delta]');
    var interpretation=byRole(host,'[data-rrh-interpretation]');
    var meta=byRole(host,'[data-rrh-meta]');
    var chart=byRole(host,'[data-rrh-chart]');
    var facts=byRole(host,'[data-rrh-facts]');
    var table=byRole(host,'[data-rrh-table]');
    var chartTitle=byRole(host,'[data-rrh-chart-title]');
    if (!selector || !chart || !state || !facts || !table) return;
    var language=(document.documentElement.getAttribute('data-lang')==='zh' ||
                  document.documentElement.getAttribute('lang')==='zh') ? 'zh' : 'en';
    SERIES.forEach(function (s) {
      var option=selector.querySelector('option[value="'+s[0]+'"]');
      if (option) option.textContent=s[language==='zh'?2:1];
    });
    selector.value=target;selectBasis.value=basis;selectWindow.value=String(windowMonths);
    var series=(history && Array.isArray(history.series) && history.series.length<=10)
      ? history.series.find(function (s) { return s && s.release===target; }) : null;
    var valid=authorized(history) && history.schema==='release_visual_history.v1' &&
      ['available','partial','unavailable'].includes(history.status) &&
      Number.isFinite(Date.parse(history.asof)) && Date.parse(history.asof)<=Date.now() &&
      Number.isFinite(Date.parse(history.source_collected_at)) &&
      Date.parse(history.source_collected_at)<=Date.parse(history.asof) &&
      series && series.status==='available' &&
      SERIES.some(function (s) { return s[0]===series.release && s[0]===target; });
    var all=valid?points(series[basis],72):[];
    var selected=all.slice(-windowMonths);
    var latest=selected[selected.length-1],prev=selected[selected.length-2];
    var consecutive=prev && latest.month-prev.month===1;
    var delta=consecutive?latest.value-prev.value:null;
    var asofLabel=valid?String(history.source_collected_at).slice(0,10):'';
    var latestLabel=latest?latest.period:'';
    var sourceBasis=valid && series.basis_metadata && series.basis_metadata[basis];
    var sourceLink=byRole(host,'[data-rrh-source]');
    if (sourceLink) {
      var sourceId=sourceBasis && sourceBasis.series_id;
      sourceLink.setAttribute('href',
        typeof sourceId==='string' && /^[A-Z0-9]{3,12}$/.test(sourceId) ?
          'https://fred.stlouisfed.org/series/'+sourceId :
          'https://fred.stlouisfed.org/');
    }
    var isProxy=basis==='yoy' && !!sourceBasis &&
      sourceBasis.official_reported_basis_comparable!==true;
    var qualifierEn=!sourceBasis?'Source basis unverified':
      isProxy?'SA-index YoY proxy — NOT the BLS official NSA 12-month headline':
      basis==='yoy' && sourceBasis.seasonal_adjustment==='NSA' ?
        'NSA YoY · BLS headline basis (revised index, not original first print)':
      basis==='yoy' ? 'BEA seasonally-adjusted YoY (revised index)' :
        'Seasonally-adjusted MoM (revised index, not original first print)';
    var qualifierZh=!sourceBasis?'来源口径未核实':
      isProxy?'季调同比替代指标，不等于 BLS 公布的未季调十二个月同比':
      basis==='yoy' && sourceBasis.seasonal_adjustment==='NSA' ?
        '未季调同比 · 与 BLS 公布口径一致（修订后指数）':
      basis==='yoy' ? 'BEA 季调同比（修订后指数）' :
        '季调环比（修订后指数，非首次公布值）';
    var stale=valid && (
      history.source_status!=='recent' ||
      Date.now()-Date.parse(history.asof)>72*3600000 ||
      (latest && monthNumber(String(new Date(history.asof).getUTCFullYear())+'-'+
        String(new Date(history.asof).getUTCMonth()+1).padStart(2,'0'))-latest.month>2)
    );
    bilingual(state,
      !valid?'Historical series unavailable.':stale?'Archived history — not a current release.':'Historical series available.',
      !valid?'\u5386\u53f2\u5e8f\u5217\u4e0d\u53ef\u7528\u3002':stale?'\u5df2\u5b58\u6863\u5386\u53f2\uff0c\u975e\u5f53\u524d\u53d1\u5e03\u3002':'\u5386\u53f2\u5e8f\u5217\u5df2\u53ef\u7528\u3002');
    bilingual(valueNode,latest?fmt(latest.value)+'%':'\u2014',latest?fmt(latest.value)+'%':'\u2014');
    bilingual(deltaNode,
      delta===null?'Monthly change unavailable.':(delta>0?'Up ':delta<0?'Down ':'Unchanged · ')+signed(delta)+' percentage points from previous month.',
      delta===null?'\u6708\u5ea6\u53d8\u5316\u4e0d\u53ef\u7528\u3002':'\u8f83\u4e0a\u6708'+(delta>0?'\u4e0a\u5347 ':delta<0?'\u4e0b\u964d ':'\u6301\u5e73 ')+signed(delta)+' \u4e2a\u767e\u5206\u70b9\u3002');
    bilingual(interpretation,
      !latest?'No qualified revised series is available for this measure.':
      delta===null?'Latest observed period '+latestLabel+'; the adjacent prior month is missing.':
      'In '+latestLabel+', '+(basis==='yoy'?'annual':'monthly')+' inflation '+(delta>0?'accelerated':delta<0?'decelerated':'was unchanged')+
      ' relative to the prior observation. This is not a surprise versus consensus.',
      !latest?'\u8be5\u6307\u6807\u7f3a\u5c11\u53ef\u6838\u9a8c\u7684\u4fee\u8ba2\u540e\u5386\u53f2\u6570\u636e\u3002':
      delta===null?'\u6700\u8fd1\u671f\u4e3a '+latestLabel+'\uff1b\u4e0a\u6708\u6570\u636e\u7f3a\u5931\u3002':
      latestLabel+'\uff1a'+(basis==='yoy'?'\u540c\u6bd4':'\u73af\u6bd4')+'\u901a\u80c0'+(delta>0?'\u52a0\u901f':delta<0?'\u653e\u7f13':'\u6301\u5e73')+'\u3002\u8fd9\u5e76\u975e\u76f8\u5bf9\u5e02\u573a\u9884\u671f\u7684\u8d85\u9884\u671f\u5e45\u5ea6\u3002');
    bilingual(meta,
      valid?'FRED/ALFRED revised index · '+(basis==='yoy'?'year over year':'month over month')+
        ' · through '+(latestLabel||'unknown')+' · collection '+asofLabel+
        (stale?' · STALE':''):
        'Historical data unavailable or failed integrity checks.',
      valid?'FRED/ALFRED \u4fee\u8ba2\u540e\u6307\u6570 \u00b7 '+(basis==='yoy'?'\u540c\u6bd4':'\u73af\u6bd4')+
        ' \u00b7 \u622a\u81f3 '+latestLabel+' \u00b7 \u91c7\u96c6 '+asofLabel+(stale?' \u00b7 \u5df2\u8fc7\u671f':''):
        '\u5386\u53f2\u6570\u636e\u7f3a\u5931\u6216\u5b8c\u6574\u6027\u9a8c\u8bc1\u5931\u8d25\u3002');
    if (valid && sourceBasis && meta) {
      var sourceDetail=textNode('span','rrh-basis-detail');
      bilingual(sourceDetail,' · '+qualifierEn+' · FRED '+sourceBasis.series_id,
        ' · '+qualifierZh+' · FRED '+sourceBasis.series_id);
      meta.appendChild(sourceDetail);
      if (isProxy && interpretation) {
        var basisWarning=textNode('span','rrh-basis-warning');
        bilingual(basisWarning,
          ' Source qualification: this SA YoY proxy must not be compared to BLS published unadjusted 12-month rates.',
          ' 口径说明：季调同比替代指标不能与 BLS 公布的未季调十二个月通胀率混为一谈。');
        interpretation.appendChild(basisWarning);
      }
    }
    bilingual(chartTitle,
      'Revised '+(basis==='yoy'?'year-over-year':'month-over-month')+' inflation trend',
      '\u4fee\u8ba2\u540e\u7684'+(basis==='yoy'?'\u540c\u6bd4':'\u73af\u6bd4')+'\u901a\u80c0\u8d70\u52bf');
    draw(chart,selected,language);
    facts.textContent='';
    fact(facts,'Latest period','\u6700\u8fd1\u6708\u4efd',latestLabel||'\u2014');
    fact(facts,'Previous month','\u4e0a\u4e00\u4e2a\u6708',consecutive?fmt(prev.value)+'%':'\u2014');
    var prints=valid && Array.isArray(series.first_prints) ? series.first_prints.filter(function(p) {
      return p && Number.isFinite(p.value) && Number.isFinite(monthNumber(p.period)) &&
        Number.isFinite(Date.parse(p.released_at)) && Date.parse(p.released_at)<=Date.now() &&
        p.basis==='verified_official_first_print_mom';
    }) : [];
    var official=prints[prints.length-1];
    fact(facts,'Official first print','\u5b98\u65b9\u9996\u6b21\u53d1\u5e03',official?fmt(official.value)+'%':'\u2014',
      official?'MoM · '+official.period:'Not available','\u73af\u6bd4 \u00b7 '+(official?official.period:'\u4e0d\u53ef\u7528'));
    var street=displayEvidence(surprise);
    fact(facts,'Street consensus','\u5e02\u573a\u5171\u8bc6',street?fmt(street.consensus)+'%':'\u2014',
      street?'MoM · '+street.period:'Unqualified / unavailable',
      street?'\u73af\u6bd4 \u00b7 '+street.period:'\u5c1a\u65e0\u5408\u683c\u6765\u6e90');
    fact(facts,'Surprise vs consensus','\u76f8\u5bf9\u5171\u8bc6\u7684\u610f\u5916\u5e45\u5ea6',
      street?signed(street.surprise)+' pp':'\u2014',
      street?(street.surprise>0?'Hotter than expected':street.surprise<0?'Cooler than expected':'In line with expectations')+' · '+street.period:
        'No verified pre-release economist poll',
      street?(street.surprise>0?'\u9ad8\u4e8e\u9884\u671f':street.surprise<0?'\u4f4e\u4e8e\u9884\u671f':'\u7b26\u5408\u9884\u671f')+' \u00b7 '+street.period:
        '\u7f3a\u5c11\u5df2\u6838\u5b9e\u7684\u53d1\u5e03\u524d\u7ecf\u6d4e\u5b66\u5bb6\u9884\u6d4b');
    table.textContent='';
    selected.slice(-12).reverse().forEach(function(p) {
      var row=document.createElement('tr');
      row.appendChild(textNode('td','',p.period));
      row.appendChild(textNode('td','',fmt(p.value)+'%'));
      table.appendChild(row);
    });
  }
  function connect(host) {
    if (!host || host.dataset.rrhConnected==='yes') return;
    host.dataset.rrhConnected='yes';
    [['[data-rrh-target]',function (v) { if(SERIES.some(function (s) {return s[0]===v;}))target=v; }],
     ['[data-rrh-basis]',function (v) { if(v==='yoy'||v==='mom')basis=v; }],
     ['[data-rrh-window]',function (v) { if(['12','36','60'].includes(v))windowMonths=Number(v); }]
    ].forEach(function (spec) {
      var control=byRole(host,spec[0]);
      if(control) control.addEventListener('change',function () {
        spec[1](control.value);render(host,snapshot,comparison);
      });
    });
  }
  global.MMXReleaseVisualHistory=Object.freeze({
    render:function (host, history, surprise) {
      connect(host);render(host,history,surprise);
    },
    selectRelease:function (releaseType) {
      if (!SERIES.some(function (s) {return s[0]===releaseType;})) return false;
      if (target===releaseType) return true;
      target=releaseType;
      var host=document.getElementById('rr-visual-history');
      if (host && snapshot) render(host,snapshot,comparison);
      return true;
    }
  });
})(window);
