/* Restore the normal auth subject, mount one investor instance, then load tools. */
(function(){
  var initial={subject:null,promise:null,owned:false,ui:null,failedModules:[]},auth=window.MDXAuth,started=false,authObserved=false,resolveModules;
  initial.modulesReady=new Promise(function(resolve){resolveModules=resolve});
  function modules(){
    if(started)return;started=true;
    var names=['government-revenue-sbir.js','government-revenue-theme-context.js','government-revenue-dossiers.js','government-revenue-candidate-radar.js','government-revenue-briefcase.js','government-revenue-briefcase-ui.js'];
    Promise.all(names.map(function(name){return new Promise(function(resolve){var script=document.createElement('script');script.src=name;script.async=false;script.setAttribute('data-sync','');script.onload=function(){resolve()};script.onerror=function(){initial.failedModules.push(name);console.error('Government Revenue tool could not load: '+name);resolve()};document.head.appendChild(script)})})).then(function(){
      if(initial.failedModules.length){var note=document.createElement('p');note.className='gr-investor-note';note.setAttribute('role','status');function copy(){note.textContent=document.documentElement.getAttribute('data-lang')==='zh'?'部分研究工具未能加载。请刷新后重试。':'Some research tools could not load. Refresh to retry.'}copy();document.addEventListener('langchange',copy);document.getElementById('defenseInvestorHost').insertAdjacentElement('afterend',note)}
      resolveModules({state:initial.failedModules.length?'partial':'ready',failed:initial.failedModules.slice()});
      var page=document.createElement('script');page.type='module';page.src='government-revenue-page.js';page.setAttribute('data-sync','');page.onload=function(){initial.pageState='ready'};page.onerror=function(){initial.pageState='failed';var note=document.createElement('p');note.className='gr-investor-note';note.setAttribute('role','status');note.textContent=document.documentElement.getAttribute('data-lang')==='zh'?'研究工作区未能加载。请刷新后重试。':'The research workspace could not load. Refresh to retry.';document.getElementById('defenseInvestorHost').insertAdjacentElement('afterend',note);console.error('Government Revenue page controller could not load')};document.head.appendChild(page);
    });
  }
  // Bind the early read to its restored subject before the shared notification.
  // After takeover, the page and the normal auth owner supply the subject.
  initial.ui=window.createGovernmentRevenueInvestor({authSubject:function(){var a=window.MDXAuth;return !initial.owned&&initial.subject!==null?initial.subject:a&&typeof a.user==='function'?a.user():null},fetch:function(url,options){var a=window.MDXAuth;if(!a||typeof a.client!=='function'||(a.enabled&&!a.enabled()))return Promise.reject(new Error('locked'));return window.fetch(url,options)},authHeaders:function(h){var auth=window.MDXAuth;return auth&&auth.client&&!(auth.enabled&&!auth.enabled())?auth.client().then(function(c){return c.auth.getSession()}).then(function(r){var t=r&&r.data&&r.data.session&&r.data.session.access_token;if(t)h.Authorization='Bearer '+t;return h}).catch(function(){return h}):Promise.resolve(h)}});
  window.__govrevFirstInvestor=initial;initial.ui.mount();
  function releaseProgressive(){var release=window.__govrevReleaseProgressive;if(typeof release!=='function')return;var frame=window.requestAnimationFrame||function(cb){setTimeout(cb,0)};frame(function(){frame(function(){release()})})}
  function settled(user,event){if(initial.owned)return;if(event==='INITIAL_SESSION'&&initial.promise&&initial.subject===(user&&user.id||''))return;initial.subject=user&&typeof user.id==='string'?user.id:'';initial.promise=initial.ui.load(true);Promise.resolve(initial.promise).then(function(){releaseProgressive();modules()},function(){releaseProgressive();modules()})}
  if(!auth||(auth.enabled&&!auth.enabled()))settled(null,'AUTH_UNAVAILABLE');
  else if(auth.onChange)auth.onChange(function(user,event){authObserved=true;settled(user,event)});
  // A completed SDK restoration is usable before its separate auth notification.
  // A newer notification (including sign-out) or the page owner always wins.
  if(auth&&auth.client&&!(auth.enabled&&!auth.enabled()))auth.client().then(function(c){return c.auth.getSession()}).then(function(r){if(!authObserved&&r&&!r.error&&r.data&&Object.prototype.hasOwnProperty.call(r.data,'session'))settled(r.data.session&&r.data.session.user,'INITIAL_SESSION')}).catch(function(){})
})();
