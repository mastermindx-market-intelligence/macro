/* Presentation and same-origin protected-detail reads only; no auth authority, signal calculation, persistence or trading effects. */
(function () {
  'use strict';
  function csvCell(value) {
    if (value === null || value === undefined) return '';
    if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '';
    var text = String(value);
    if (/^[=+@\-\t\r]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }
  function seriesCsv(metric, inputClass) {
    var out = [['reference_month', metric.unit, 'definition', 'input_class'].map(csvCell).join(',')];
    metric.chart.dates.forEach(function (date, i) {
      out.push([date.slice(0, 7), metric.chart.vals[i], metric.definition_id,
        inputClass || 'input_class_not_supplied'].map(csvCell).join(','));
    });
    return '\uFEFF' + out.join('\r\n');
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {csvCell:csvCell, seriesCsv:seriesCsv};
  if (typeof document === 'undefined') return;
  var root = document.getElementById('china-economy');
  var tag = document.getElementById('eco-json');
  if (!root || !tag) return;
  var initialPublication;
  try { initialPublication = JSON.parse(tag.textContent); } catch (error) { return; }
  var disposeDetail = null;
  function activate(publication) {
  var data = publication.economy;
  if (!data || data.schema !== 'mastermind.china_economy_lens.v1' || !data.metrics || !Array.isArray(data.groups)) return false;
  if (disposeDetail) disposeDetail();
  var cleanup = [], observer = null;
  function listen(node, event, handler) {
    node.addEventListener(event, handler);
    cleanup.push(function(){node.removeEventListener(event, handler);});
  }
  var selected = 'industrial_sa';
  var select = document.getElementById('eco-metric-select');
  if (!select || !document.getElementById('eco-export')) return;
  function selectMetric(id, scroll) {
    if (!data || !Object.prototype.hasOwnProperty.call(data.metrics, id)) return;
    var template = document.getElementById('eco-template-' + id);
    var target = document.getElementById('eco-selected-metric');
    if (!template || !target) return;
    target.replaceChildren(template.content.cloneNode(true));
    selected = id; select.value = id;
    translateControls(document.documentElement.dataset.lang);
    if (scroll) {
      document.getElementById('eco-explorer').scrollIntoView({block:'start',behavior:'auto'});
      select.focus({preventScroll:true});
    }
  }
  function selectGroup(id, scroll) {
    if (!data || !data.groups.some(function(g){return g.id===id;})) return;
    root.querySelectorAll('[data-eco-group-panel]').forEach(function(p){p.hidden=p.dataset.ecoGroupPanel!==id;});
    root.querySelectorAll('.eco-group-tabs [data-eco-group]').forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.ecoGroup===id));});
    if (scroll) document.getElementById('eco-library').scrollIntoView({block:'start',behavior:'auto'});
  }
  listen(root,'click',function(event){
    var pick=event.target.closest('[data-eco-select]');
    if (pick && root.contains(pick)) {selectMetric(pick.dataset.ecoSelect,true);return;}
    var group=event.target.closest('[data-eco-group]');
    if (group && root.contains(group)) selectGroup(group.dataset.ecoGroup,!group.closest('.eco-group-tabs'));
  });
  listen(select,'change',function(){selectMetric(select.value,false);});
  function save(contents,type,filename){
    var url=URL.createObjectURL(new Blob([contents],{type:type}));
    var a=document.createElement('a');a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();
    setTimeout(function(){URL.revokeObjectURL(url);},2000);
  }
  listen(document.getElementById('eco-export'),'click',function(){
    if (!data) return;
    save(seriesCsv(data.metrics[selected], data.input_class),'text/csv;charset=utf-8','china-economy-'+selected+'-'+data.reference_period+'.csv');
  });
  var jsonButton=document.getElementById('eco-export-json');
  if (jsonButton) listen(jsonButton,'click',function(){
    if (!publication || !data) return;
    // Production downloads the complete canonical contract, not the smaller
    // interaction projection. The offline review still exports its full input.
    if (publication.download_href === 'china_macro_evidence.json') {
      var a=document.createElement('a');a.href=publication.download_href;
      a.download='china-macro-evidence.json';document.body.appendChild(a);a.click();a.remove();
    } else save(JSON.stringify(publication,null,2),'application/json','china-economy-evidence.json');
  });
  function translateControls(lang){
    lang=lang==='zh'?'zh':'en';
    select.querySelectorAll('option,optgroup').forEach(function(item){var text=item.dataset[lang];if (!text)return;if(item.tagName==='OPTGROUP')item.label=text;else item.textContent=text;});
    root.querySelectorAll('[data-aria-en]').forEach(function(item){item.setAttribute('aria-label',item.dataset[lang==='zh'?'ariaZh':'ariaEn']);});
  }
  function language(lang){
    lang=lang==='zh'?'zh':'en';document.documentElement.dataset.lang=lang;document.documentElement.lang=lang==='zh'?'zh-CN':'en';
    translateControls(lang);
  }
  // Follow the existing site-wide language control; do not create a second
  // saved language preference or navigation owner.
  if (typeof MutationObserver!=='undefined') {
    observer = new MutationObserver(function(){translateControls(document.documentElement.dataset.lang);});
    observer.observe(document.documentElement,{attributes:true,attributeFilter:['data-lang']});
  }
  var api={setLanguage:language,selectMetric:selectMetric,selectGroup:selectGroup};
  window.EconomyLens=api;
  disposeDetail=function(){
    cleanup.forEach(function(remove){remove();});
    if(observer) observer.disconnect();
    if(window.EconomyLens===api) delete window.EconomyLens;
    data=null; publication=null; disposeDetail=null;
  };
  language(document.documentElement.dataset.lang || 'en');
  root.dataset.ecoDetailReady='true';
  return true;
  }

  if (activate(initialPublication)) return;
  var detailHref=initialPublication.detail_href;
  if (detailHref !== 'china_economy_detail.json') return;
  var slot=document.getElementById('eco-detail-slot');
  if (!slot) return;
  var gateHTML=slot.innerHTML;
  var userId=null, generation=0, inspection=0, attempted=false, activeRequest=null;

  function setStatus(state){
    root.dataset.ecoDetailState=state;
    var lock=document.getElementById('eco-detail-lock');
    if(!lock) return;
    var words={
      loading:['Loading the economic evidence…','正在加载经济证据…'],
      forbidden:['Your account does not currently have access to the full evidence library.','当前账户暂无完整证据库的访问权限。'],
      unauthenticated:['Your session has expired. Sign in again to check access.','登录状态已过期，请重新登录以查看访问权限。'],
      unavailable:['Economic evidence is temporarily unavailable. The overview is still available.','经济证据暂不可用，您仍可查看上方总览。']
    };
    var message=lock.querySelector('p');
    if(message && words[state]) message.innerHTML='<span class="l-en">'+words[state][0]+'</span><span class="l-zh">'+words[state][1]+'</span>';
    var actions=lock.querySelector('.eco-deep-lock-actions');
    if(actions){
      var signIn=actions.querySelector('a:first-child');
      if(signIn) signIn.hidden=state==='forbidden' || state==='loading';
      var retry=actions.querySelector('[data-eco-retry]');
      if(retry) retry.remove();
      if(state==='unavailable'){
        retry=document.createElement('button'); retry.type='button';
        retry.className='eco-export'; retry.setAttribute('data-eco-retry','');
        retry.innerHTML='<span class="l-en">Retry</span><span class="l-zh">重试</span>';
        actions.appendChild(retry);
      }
    }
  }
  function clearDetail(){
    generation++;
    if(activeRequest) activeRequest.abort();
    activeRequest=null; attempted=false;
    if(disposeDetail) disposeDetail();
    delete root.dataset.ecoDetailReady;
    slot.innerHTML=gateHTML; slot.classList.add('eco-deep-lock');
    root.dataset.ecoDetailState='signed_out';
  }
  function installDetail(payload){
    if (!payload || payload.schema!=='mastermind.china_economy_detail_payload.v1' ||
        payload.status!=='ok' || typeof payload.html!=='string' || !payload.client ||
        !payload.client.economy || payload.client.economy.schema!=='mastermind.china_economy_lens.v1' ||
        payload.reference_period!==payload.client.economy.reference_period) return false;
    slot.innerHTML=payload.html;
    if(activate(payload.client)){
      slot.classList.remove('eco-deep-lock'); setStatus('ready'); return true;
    }
    slot.innerHTML=gateHTML; return false;
  }
  function loadDetail(){
    if(!userId || attempted) return;
    attempted=true;
    var epoch=generation, owner=userId, acceptedResponse=false;
    var controller=new AbortController(); activeRequest=controller;
    function current(){return epoch===generation && owner===userId;}
    setStatus('loading');
    return fetch(detailHref,{credentials:'same-origin',cache:'no-store',signal:controller.signal,headers:{'Accept':'application/json'}})
      .then(function(response){
        if(!current()) return null;
        if(!response.ok){
          setStatus(response.status===401?'unauthenticated':response.status===403?'forbidden':'unavailable');
          return null;
        }
        acceptedResponse=true;
        return response.json();
      })
      .then(function(payload){
        if(current() && acceptedResponse && !installDetail(payload)) setStatus('unavailable');
      })
      .catch(function(error){if(current() && error.name!=='AbortError') setStatus('unavailable');})
      .then(function(){if(current()) activeRequest=null;});
  }
  function inspectSession(forceRetry){
    if(!window.MDXAuth || typeof window.MDXAuth.client!=='function') return;
    var ticket=++inspection;
    Promise.resolve(window.MDXAuth.client())
      .then(function(sb){return sb && sb.auth && typeof sb.auth.getSession==='function' ? sb.auth.getSession() : null;})
      .then(function(result){
        if(ticket!==inspection) return;
        var session=result && result.data && result.data.session;
        var nextId=session && session.user && session.user.id;
        if(typeof nextId!=='string' || !nextId){userId=null;clearDetail();return;}
        if(nextId!==userId){clearDetail();userId=nextId;}
        if(forceRetry && !activeRequest) attempted=false;
        return loadDetail();
      })
      .catch(function(){if(ticket===inspection){userId=null;clearDetail();setStatus('unavailable');}});
  }
  function authChanged(event){
    var detail=event && event.detail;
    // Clear immediately; a late old-account HTTP response must not restore it.
    if(detail && (detail.event==='SIGNED_OUT' || (detail.event==='INITIAL_SESSION' && !detail.user))){
      inspection++;userId=null;clearDetail();return;
    }
    if(detail && detail.user && userId && detail.user.id!==userId){
      inspection++;userId=null;clearDetail();
    }
    inspectSession(false);
  }
  root.addEventListener('click',function(event){
    var target=event.target.closest && event.target.closest('[data-eco-retry]');
    if(target && root.contains(target)){event.preventDefault();inspectSession(true);return;}
    if(root.dataset.ecoDetailReady==='true') return;
    target=event.target.closest && event.target.closest('[data-eco-select],[data-eco-group]');
    if(!target || !root.contains(target)) return;
    event.preventDefault();
    var lock=document.getElementById('eco-detail-lock');
    if(lock) lock.scrollIntoView({block:'center',behavior:'auto'});
  });
  // Subscribe to the existing auth owner, not a second saved session or tier model.
  window.addEventListener('mdx-auth',authChanged);
  window.addEventListener('pageshow',function(event){if(event.persisted) inspectSession(false);});
  if(window.MDXAuth && (!window.MDXAuth.hasSession || window.MDXAuth.hasSession())) inspectSession(false);
})();
