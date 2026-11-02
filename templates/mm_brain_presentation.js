/* Shared lazy delivery for existing native visuals, financial views and formula typesetting. */
(function (win) {
  'use strict';
  var doc=win.document, script=doc.currentScript;
  var base=new URL('./',script&&script.src||doc.baseURI).href;
  var loads={};
  var versions={visualJS:'2e3ce3a5',visualCSS:'b9f2e195',financeJS:'a8f801ae',financeCSS:'b317487a',math:'e24d5a2c'};
  function asset(name,kind,version) {
    return new Promise(function(resolve,reject) {
      var node=doc.createElement(kind==='style'?'link':'script');
      if(kind==='style'){node.rel='stylesheet';node.href=new URL(name+'?v='+version,base).href;}
      else{node.src=new URL(name+'?v='+version,base).href;node.async=true;node.charset='utf-8';}
      var timer=win.setTimeout(function(){node.remove();reject(new Error('presentation_asset_timeout'));},10000);
      node.onload=function(){win.clearTimeout(timer);resolve();};
      node.onerror=function(){win.clearTimeout(timer);node.remove();reject(new Error('presentation_asset_unavailable'));};
      doc.head.appendChild(node);
    });
  }
  function renderer(version) {
    var key=version===2?'finance':'visual';
    if(!loads[key]) {
      var finance=key==='finance', stem=finance?'mm_brain_finance':'mm_brain_visuals';
      loads[key]=Promise.all([asset(stem+'.js','script',versions[finance?'financeJS':'visualJS']),
        asset(stem+'.css','style',versions[finance?'financeCSS':'visualCSS'])]).then(function(){
          var module=finance?win.MMBrainFinance:win.MMBrainVisuals;
          if(!module||typeof module.mount!=='function')throw new Error('presentation_module_unavailable');
          return module;
        }).catch(function(err){delete loads[key];throw err;});
    }return loads[key];
  }
  function locale(en,zh) { return /^zh/i.test(doc.documentElement.getAttribute('data-lang')||doc.documentElement.lang||'')?zh:en; }
  function clear(host) {
    if(!host)return;host._presentationEpoch=(host._presentationEpoch||0)+1;
    if(win.MMBrainVisuals)win.MMBrainVisuals.clear(host);
    if(win.MMBrainFinance)win.MMBrainFinance.clear(host);
    host.querySelectorAll('.mmb-f-card,.mmb-v,.mmb-visual-notice,[data-presentation-pending]').forEach(function(n){n.remove();});
  }
  function mount(host,wire,options) {
    if(!host||!wire||!wire.visual||![1,2].includes(wire.visual.version)||!/^[a-f0-9]{24}$/.test(wire.visual_id))return Promise.resolve(null);
    if(host.querySelector('[data-visual-id="'+wire.visual_id+'"],[data-presentation-pending="'+wire.visual_id+'"]'))return Promise.resolve(null);
    var epoch=host._presentationEpoch||0, pending=doc.createElement('p');
    pending.className='mmb-f-note';pending.dataset.presentationPending=wire.visual_id;
    pending.textContent=locale('Preparing the view…','正在整理视图…');host.appendChild(pending);
    return renderer(wire.visual.version).then(function(module){
      if(!pending.isConnected||!host.isConnected||(host._presentationEpoch||0)!==epoch)return null;
      pending.remove();
      var result=module.mount(host,wire,{assetBase:base,onExpand:options&&options.onExpand});
      if(!result){pending.textContent=locale('This view is unavailable.','此视图暂不可用。');host.appendChild(pending);}
      return result;
    }).catch(function(){
      if(pending.isConnected&&host.isConnected&&(host._presentationEpoch||0)===epoch)
        pending.textContent=locale('The view could not load. The text answer remains available.','视图加载失败，仍可阅读文字回答。');
      return null;
    });
  }
  function renderMath(host) {
    if(!host||!host.querySelector('[data-mmb-math]:not([data-mmb-math-rendered])'))return Promise.resolve();
    if(!loads.math)loads.math=asset('mm_brain_math.js','script',versions.math).then(function(){
      if(!win.MMBrainMath)throw new Error('math_module_unavailable');return win.MMBrainMath;
    }).catch(function(e){delete loads.math;throw e;});
    return loads.math.then(function(module){if(host.isConnected)module.render(host);}).catch(function(){
      if(host.isConnected)host.querySelectorAll('[data-mmb-math]').forEach(function(n){n.classList.add('mmb-math-fallback');});
    });
  }
  win.MMBrainPresentation={mount:mount,clear:clear,renderMath:renderMath,version:1};
})(window);
