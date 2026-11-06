/* Anonymous, offline presentation specimen. No credentials, account or provider.
   The production widget and native renderer are loaded unchanged from templates/.
   Only the API seam is fictional; this is not live delivery/model-selection proof. */
(function () {
  'use strict';
  document.documentElement.dataset.lang = localStorage.getItem('lang') || 'en';
  document.documentElement.dataset.theme = localStorage.getItem('theme') || 'dark';
  document.documentElement.lang = document.documentElement.dataset.lang === 'zh' ? 'zh-CN' : 'en';
  window.setLang = function (lang) { document.documentElement.dataset.lang = lang; document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en'; document.dispatchEvent(new Event('langchange')); };
  window.setTheme = function (theme) { document.documentElement.dataset.theme = theme; document.dispatchEvent(new Event('themechange')); };
  window.MM_BRAIN_CFG = {api:'',anchor:'top',page:'macro'};
  var originalFetch = window.fetch.bind(window);
  var base = new URL('./',document.currentScript.src);
  var fixtures = originalFetch(new URL('fixtures.json',base)).then(function (r) { return r.json(); });
  window.fetch = function (input, options) {
    var url = String(input);
    if (url.endsWith('/api/brain/me')) return Promise.resolve(new Response(JSON.stringify({tier:'guest',quotas:{fast:{limit:20,remaining:20},pro:{limit:0,remaining:0}}}),{headers:{'Content-Type':'application/json'}}));
    if (url.endsWith('/api/brain/stream')) return fixtures.then(function (all) {
      var lang = document.documentElement.dataset.lang === 'zh' ? 'zh' : 'en';
      var kind = location.pathname.endsWith('/timeline.html') ? 'timeline' : location.pathname.endsWith('/brief.html') ? 'brief' : 'chart';
      var item = all[lang][kind];
      var events = [{type:'meta',lane:'fast'},{type:'delta',text:item.answer},item.wire,{type:'done',charts:[item.wire],citations:[],filtered:false,degraded:false}];
      return new Response(new ReadableStream({start:function (controller) {
        events.forEach(function (event) { controller.enqueue(new TextEncoder().encode('data: '+JSON.stringify(event)+'\n\n')); });
        controller.close();
      }}),{headers:{'Content-Type':'text/event-stream'}});
    });
    if (url.endsWith('/api/brain/threads')) return Promise.resolve(new Response('{"threads":[]}',{headers:{'Content-Type':'application/json'}}));
    if (url.includes('/api/brain/')) return Promise.resolve(new Response('{}',{status:404,headers:{'Content-Type':'application/json'}}));
    return originalFetch(input,options);
  };
  document.addEventListener('DOMContentLoaded',function () {
    var attempts = 0;
    var timer = setInterval(function () {
      if (++attempts > 60) { clearInterval(timer); return; }
      var input = document.getElementById('mmb-ta'), send = document.getElementById('mmb-send');
      if (!window.MMBrain || !input || !send) return;
      clearInterval(timer);
      window.MMBrain.open(); window.MMBrain.expand();
      setTimeout(function () {
        var chinese = document.documentElement.dataset.lang === 'zh';
        input.value = chinese ? '请展示一个虚构的教学图解，而非实时市场数据。' : 'Show a fictional teaching illustration, not a live market assessment.';
        input.dispatchEvent(new Event('input',{bubbles:true})); send.click();
      },250);
    },50);
  });
}());
