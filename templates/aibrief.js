/* AI Daily Brief: display clocks, accessible lens navigation, optional AI review.
   Never generates analysis, mutates source dates, or calls a model/provider. */
(function () {
  'use strict';
  var DAY = 86400000;
  function day(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
    var parsed = Date.parse(value + 'T00:00:00Z');
    return Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0,10) === value ? parsed : null;
  }
  function stamp(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value) || day(value.slice(0,10)) === null) return null;
    var parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  function freshness(source, generated, cadence, now) {
    now = now === undefined ? Date.now() : now;
    var s = day(source), g = stamp(generated);
    var unknown = {state:'unknown', en:'Freshness is unknown. Check the source dashboards before relying on this edition.', zh:'时效性未知，请先对照源看板再使用本期解读。'};
    if (s === null || g === null || g > now || s > now || s > g) return unknown;
    var age = Math.floor((now - s) / DAY);
    var interval = Number(cadence);
    if (!Number.isInteger(interval) || interval < 1 || interval > 7) return unknown;
    if (age > interval + 1) return {state:'old', en:'Older edition · source data is ' + age + ' calendar days old. Check the dashboards for newer readings.', zh:'旧版简报 · 源数据距今' + age + '天，请查看看板中的更新读数。'};
    return {state:'dated', en:'Source age: ' + age + ' calendar days. This is a dated research edition, not a live market feed.', zh:'源数据距今' + age + '天。本期为有日期的研究简报，并非实时行情。'};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {freshness:freshness};
  if (typeof document === 'undefined') return;
  function object(x) { return x !== null && typeof x === 'object' && !Array.isArray(x); }
  function words(x) { return typeof x === 'string' ? x : ''; }
  function strings(x) { return Array.isArray(x) ? x.filter(function(v){return typeof v === 'string' && v.trim();}) : []; }
  function esc(x) { var e=document.createElement('span'); e.textContent=words(x); return e.innerHTML; }
  function bilingual(node, en, zh) {
    node.replaceChildren();
    [['l-en',en],['l-zh',zh]].forEach(function(pair){var e=document.createElement('span');e.className=pair[0];e.textContent=pair[1];node.appendChild(e);});
  }
  function clocks() {
    document.querySelectorAll('.aib2[data-aib-source]').forEach(function(root){
      var label=root.querySelector('[data-aib-freshness]');
      if (!label) return;
      var f=freshness(root.dataset.aibSource,root.dataset.aibGenerated,root.dataset.aibCadence);
      label.dataset.state=f.state; bilingual(label,f.en,f.zh);
      var written=root.querySelector('[data-aib-written]'), generated=stamp(root.dataset.aibGenerated);
      if(written && generated!==null) written.textContent=new Date(generated).toISOString().slice(0,16).replace('T',' ')+' UTC';
      root.querySelectorAll('[data-aib-event-date]').forEach(function(row){
        var date=day(row.dataset.aibEventDate), state=row.querySelector('.aib2-event-state');
        if (!state) return;
        var today=day(new Date().toISOString().slice(0,10));
        if (date === null) bilingual(state,'Date unverified','日期未核实');
        else if (date < today) bilingual(state,'Past date','日期已过');
        else if (date === today) bilingual(state,'Recorded for today','记录为今日');
        else bilingual(state,'Recorded schedule','原定日程');
      });
    });
  }
  function tabs() {
    var buttons=Array.from(document.querySelectorAll('.brief-tab-btn'));
    var panels=Array.from(document.querySelectorAll('.ai-brief.brief-tab'));
    if (!buttons.length) return;
    function show(lens, update) {
      if (!buttons.some(function(b){return b.dataset.lens===lens;})) return;
      buttons.forEach(function(b){var on=b.dataset.lens===lens;b.classList.toggle('active',on);b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;});
      panels.forEach(function(p){var on=p.dataset.lens===lens;p.classList.toggle('active',on);p.hidden=!on;});
      if(update) {try{history.replaceState(null,'','#'+lens);}catch(ignore){}}
    }
    buttons.forEach(function(b,index){
      b.addEventListener('click',function(){show(b.dataset.lens,true);});
      b.addEventListener('keydown',function(e){
        var next;
        if(e.key==='ArrowRight') next=(index+1)%buttons.length;
        else if(e.key==='ArrowLeft') next=(index-1+buttons.length)%buttons.length;
        else if(e.key==='Home') next=0;
        else if(e.key==='End') next=buttons.length-1;
        else return;
        e.preventDefault();show(buttons[next].dataset.lens,true);buttons[next].focus();
      });
    });
    show(['macro','china','btc'].includes(location.hash.slice(1))?location.hash.slice(1):'macro',false);
    window.addEventListener('hashchange',function(){show(location.hash.slice(1),false);});
  }
  function cortex() {
    var panel=document.getElementById('cortex-panel'), body=document.getElementById('cortex-body');
    if(!panel || !body) return;
    function note(en,zh){body.replaceChildren();var p=document.createElement('p');p.className='mb-deg';bilingual(p,en,zh);body.appendChild(p);panel.style.display='';}
    note('Loading the optional overnight review…','正在读取可选隔夜复盘……');
    var controller=typeof AbortController !== 'undefined'?new AbortController():null;
    var timer=controller?setTimeout(function(){controller.abort();},8000):null;
    fetch('neuralweb/cortex_memo.json',controller?{signal:controller.signal}:undefined)
      .then(function(r){if(r.status===404)return null;if(!r.ok)throw new Error('http');return r.json();})
      .then(function(memo){
        if(!object(memo)){note('No overnight review is available. The brief above remains readable.','暂无隔夜复盘，以上简报仍可阅读。');return;}
        var status=object(memo.run_status)?memo.run_status.status:null;
        if(status!=='ok' && status!=='success'){
          note('The overnight review did not complete successfully. No extra conclusions have been added.','隔夜复盘未成功完成，未添加额外结论。');return;
        }
        var html='<div class="cortex-label"><span class="l-en">AI REVIEW · RESEARCH ONLY</span><span class="l-zh">AI复盘 · 仅供研究</span></div>';
        var reviewTime=stamp(memo.as_of);
        if(reviewTime===null || reviewTime>Date.now()) html+='<p class="mb-deg"><span class="l-en">Review date unverified. Do not treat this as a current review.</span><span class="l-zh">复盘日期未核实，请勿视作当前复盘。</span></p>';
        else if(Date.now()-reviewTime>3*DAY) html+='<p class="mb-deg"><span class="l-en">Archived review — not current market analysis.</span><span class="l-zh">历史复盘，并非当前市场分析。</span></p>';
        if(words(memo.as_of)) html+='<p class="mb-deg"><span class="l-en">Review date: </span><span class="l-zh">复盘日期：</span>'+esc(memo.as_of)+'</p>';
        var count=0;
        if(words(memo.summary)){html+='<p>'+esc(memo.summary)+'</p>';count++;}
        [['what_fired','Flagged items','关注事项'],['deserves_operator','Questions to investigate','待核实问题']].forEach(function(section){
          var items=strings(memo[section[0]]);
          if(!items.length)return;
          count+=items.length;
          html+='<section class="cortex-section"><h3 class="cortex-h"><span class="l-en">'+section[1]+'</span><span class="l-zh">'+section[2]+'</span></h3><ul class="cortex-list">'+items.map(function(x){return '<li>'+esc(x)+'</li>';}).join('')+'</ul></section>';
        });
        var events=Array.isArray(memo.forward_watch)?memo.forward_watch.filter(function(x){return object(x)&&day(x.date)!==null&&words(x.label);}):[];
        if(events.length){count+=events.length;html+='<ul class="cortex-list">'+events.map(function(x){return '<li>'+esc(x.date)+' — '+esc(x.label)+'</li>';}).join('')+'</ul>';}
        if(!count){note('The review returned no usable analysis. No conclusions have been inferred.','复盘未返回可用分析，未据此推断结论。');return;}
        body.innerHTML=html;panel.style.display='';
      }).catch(function(){note('The optional review could not be loaded. The market brief and source links still work.','可选复盘读取失败，市场简报和来源链接仍可使用。');})
      .finally(function(){if(timer)clearTimeout(timer);});
  }
  function init(){clocks();tabs();cortex();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
  document.addEventListener('visibilitychange',function(){if(!document.hidden)clocks();});
})();
