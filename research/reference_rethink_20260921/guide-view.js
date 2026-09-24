/* Review consumer of the shared manifest. Uses native DOM/dialog, never HTML from data. */
(function (root) {
  'use strict';
  const Guide = root.MastermindGuide;
  function mount({host, dialog, manifest, ownerOrigin=location.origin, mode='page', guidePath='/reference.html'}) {
    if(!['page','context'].includes(mode))throw new Error('Unknown guide mode');
    const contextOnly=mode==='context';
    if(!/^\/[a-z0-9_-]+\.html$/.test(guidePath))throw new Error('Unsafe guide path');
    if (!host || !dialog || !Guide) throw new Error('Guide host is unavailable');
    let model;
    const fallback = contextOnly?null:document.querySelector('.fallback');
    try { model = Guide.createModel(manifest); }
    catch (error) {
      if(contextOnly)return {dispose(){},error};
      const note=document.createElement('p');note.setAttribute('role','status');
      note.textContent='Interactive guide unavailable. The definitions below are still readable. / 交互指南暂不可用，仍可阅读下方说明。';
      host.replaceChildren(note);host.hidden=false;if(fallback)fallback.hidden=false;
      return {dispose(){}, error};
    }
    let route=Guide.readRoute(location.href,model), modal=null, trigger=null, closeScroll=0, currentContext=null;
    const stateByEntry=new Map(), listeners=[];
    let restoreOnClose=true;
    if(!contextOnly)host.setAttribute('class',((host.getAttribute('class')||'')+' mx-guide').trim());
    dialog.setAttribute('class',((dialog.getAttribute('class')||'')+' mx-guide-dialog').trim());
    dialog.setAttribute('aria-modal','true');
    if(contextOnly||!new URL(location.href).searchParams.has('lang'))route.lang=document.documentElement.getAttribute('data-lang')==='zh'?'zh':route.lang;
    const t=(en,zh)=>route.lang==='zh'?zh:en;
    const value=pair=>pair?.[route.lang]||'';
    function node(tag, text='', attrs={}) {
      const item=document.createElement(tag);
      if(text) item.textContent=text;
      for(const [key,v] of Object.entries(attrs)) if(v!==null&&v!==undefined) item.setAttribute(key,String(v));
      return item;
    }
    function add(parent, ...children){parent.append(...children);return parent;}
    function button(text,action,attrs={}){const b=node('button',text,{type:'button',...attrs});b.addEventListener('click',action);return b;}
    function currentReading(opener){
      if(!opener?.getAttribute)return null;
      const en=(opener.getAttribute('data-guide-current-en')||'').trim();
      const zh=(opener.getAttribute('data-guide-current-zh')||'').trim();
      const asof=(opener.getAttribute('data-guide-asof')||'').trim();
      const reading=(opener.getAttribute('data-guide-reading')||'').trim();
      if(!en&&!zh&&!reading)return null;
      return {en:en||zh,zh:zh||en,asof,reading};
    }
    function targetLink(id,label){
      const url=contextOnly?new URL(guidePath,ownerOrigin):null;
      if(url){url.hash=id;if(route.lang==='zh')url.searchParams.set('lang','zh');}
      const a=node('a',label,{href:url?url.href:'#'+encodeURIComponent(id),'data-entry-link':id});
      if(!contextOnly)a.addEventListener('click',event=>{event.preventDefault();navigate(id);});
      return a;
    }
    function remember(event,callback,target=window){target.addEventListener(event,callback);listeners.push(()=>target.removeEventListener(event,callback));}
    function storeURL(push=false){if(contextOnly)return;const url=Guide.routeURL(location.href,route);try{history[push?'pushState':'replaceState'](null,'',url);route.duplicate=false;host.querySelector('[data-route-warning]')?.remove();}catch(_){} }
    function navigate(id=''){
      if(contextOnly)return;
      if(dialog.open){restoreOnClose=false;modal=null;dialog.close();}
      route.fragment=id;route.reading=stateByEntry.get(id)||'';route.resolution=id?model.resolve(id):null;storeURL(true);render();
      window.scrollTo(0,0);host.querySelector('h1')?.focus({preventScroll:true});
    }
    function followState(record,choice){
      stateByEntry.set(record.id,choice);
      if(!modal&&!contextOnly){route.reading=choice;storeURL();}
    }
    function icon(kind){return node('span','',{class:'guide-icon guide-icon-'+kind,'aria-hidden':'true'});}
    function ingredientMap(){
      const ids=['evidence-trend','evidence-risk-appetite','evidence-volatility','evidence-breadth','evidence-liquidity','evidence-stress'];
      if(!ids.every(id=>model.get(id)))return null;
      const section=node('section','',{class:'guide-ingredients','aria-label':t('Six inputs behind the Market State Score','市场状态分的六项输入')});
      add(section,add(node('div','',{class:'row'}),node('span',t('THE BUILDING BLOCKS','组成部分'),{class:'eyebrow muted'}),node('span',t('Explore an input','点选分项了解'),{class:'example-label'})));
      const grid=node('div','',{class:'inputs'});
      for(const id of ids){const link=targetLink(id,value(model.get(id).label));link.setAttribute('class','input-chip');grid.append(link);}
      add(section,grid,node('div',t('Read together → Market State Score','综合观察 → 市场状态分'),{class:'input-arrow'}));
      return section;
    }
    function lesson(record,compact=false){
      const box=node('section','',{class:'lesson','aria-label':t('How to read it','怎么看'),'data-presentation':record.presentation.kind});
      add(box,add(node('div','',{class:'row'}),node('span',t('HOW TO READ IT','怎么看'),{class:'eyebrow'}),node('span',t('Illustration only','仅作示意'),{class:'example-label'})));
      const readings=record.presentation.readings;
      if(!readings.length){add(box,node('p',value(record.definition)));return box;}
      let selected=stateByEntry.get(record.id)||(modal?'':route.reading)||'interpretation_neutral';
      const matrix=[['growth-down-inflation-down','interpretation_neutral','Growth ↓ · Inflation ↓','增长下降 · 通胀下降'],['growth-up-inflation-down','interpretation_up','Growth ↑ · Inflation ↓','增长上升 · 通胀下降'],['growth-down-inflation-up','interpretation_down','Growth ↓ · Inflation ↑','增长下降 · 通胀上升'],['growth-up-inflation-up','interpretation_neutral','Growth ↑ · Inflation ↑','增长上升 · 通胀上升']];
      const options=record.presentation.kind==='quadrant'?matrix.map(([id,field,en,zh])=>({id,field,label:t(en,zh)})):readings.map(r=>({id:r.id,field:r.id,label:value(r.label)||({interpretation_up:t('Rising','上升'),interpretation_down:t('Falling','下降'),interpretation_neutral:t('How to interpret it','如何理解')})[r.id]}));
      if(!options.some(o=>o.id===selected)) selected=options.find(o=>o.field==='interpretation_neutral')?.id||options[0].id;
      const explanation=node('p','',{class:'state-summary','aria-live':'polite','data-reading-text':''});
      const controls=node('div','',{class:record.presentation.kind==='quadrant'?'guide-matrix':'states','aria-label':t('Choose an example, not a current reading','选择示例，非当前读数')});
      const buttons=[];
      function select(choice,write=false){
        const option=options.find(o=>o.id===choice)||options[0];
        explanation.textContent=value(model.chooseReading(record.id,option.field)?.text);
        buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.choice===option.id)));
        if(write) followState(record,option.id);
      }
      if(options.length>1){
        for(const option of options){
          const b=button(option.label,()=>select(option.id,true),{'data-choice':option.id,'aria-pressed':String(option.id===selected)});
          buttons.push(b);controls.append(b);
        }
        box.append(controls);
      }else{
        box.append(node(compact?'h3':'h2',record.presentation.kind==='confirmation'?t('Confirmation, not direction.','确认程度，而非市场方向。'):t('What the reading describes','读数说明什么')));
      }
      if(record.presentation.kind==='quadrant')box.append(node('p',t('Growth and inflation form four combinations. No cell here represents today’s market.','增长与通胀组成四种情况，此处不表示当前市场所在象限。'),{class:'muted guide-context'}));
      if(record.id==='market-state-score'){
        const headline=node(compact?'h3':'h2','',{class:'guide-reading-headline'});
        const titles={interpretation_down:['Conditions under pressure.','市场环境承压。'],interpretation_neutral:['Mixed signals. Look underneath.','分项不一致，先看拆解。'],interpretation_up:['More signals align.','更多信号形成共识。']};
        const updateTitle=()=>{const chosen=buttons.find(b=>b.getAttribute('aria-pressed')==='true')?.getAttribute('data-choice')||selected;const title=titles[chosen];headline.textContent=title?t(...title):'';};
        buttons.forEach(b=>b.addEventListener('click',updateTitle));box.append(headline);select(selected);updateTitle();
      }
      add(box,explanation);select(selected);
      if(!compact&&record.id==='market-state-score'){const map=ingredientMap();if(map)box.append(map);}
      return box;
    }
    function limitation(record){
      const box=node('section','',{class:'caution'});
      if(record.visible_caveat)add(box,node('h3',t('Keep in mind','请留意')),node('p',value(record.visible_caveat)));
      else add(box,node('h3',t('Read in context','结合背景阅读')),node('p',t('A definition, not a current market signal.','这是定义说明，不是当前市场信号。')));
      return box;
    }
    function retirement(record){
      const box=node('section','',{class:'caution','data-retired':''});
      add(box,node('h3',t('Retired definition','已停用的定义')),node('p',t('Kept for old links. Use the current explanation below.','保留旧链接供查阅，请使用下方当前说明。')));
      for(const id of record.replacement_chain)box.append(targetLink(id,value(model.get(id).label)));
      return box;
    }
    function related(ids,title){
      const box=node('nav','',{class:'related','aria-label':title});box.append(node('span',title,{class:'muted'}));
      for(const id of ids)box.append(targetLink(id,value(model.get(id).label)));
      return box;
    }
    function owner(record){
      const box=node('section','',{class:'where'});box.append(node('h3',t('Use it in context','结合看板使用')));
      const url=model.ownerURL(record.id,ownerOrigin);
      if(url)box.append(node('a',t('Open the owning dashboard →','打开对应看板 →'),{href:url,'data-owner':''}));
      else box.append(node('p',t('Dashboard link unavailable in this preview.','此预览中无法打开看板链接。')));
      return box;
    }
    function disclosure(title,content){const section=node('details');add(section,node('summary',title),...content);return section;}
    function entryPage(record){
      const section=node('section');
      section.append(button('← '+t('Market Guide','市场指南'),()=>navigate(),{class:'bare','data-home':''}));
      const heading=node('div','',{class:'detail-head'});
      add(heading,node('h1',value(record.label),{tabindex:'-1'}),node('p',value(record.definition)),node('div',[value(record.basis),t('Guide, not live data','学习指南，非实时数据')].filter(Boolean).join(' · '),{class:'basis'}));
      section.append(heading);
      if(route.resolution?.alias)section.append(node('p',t('This name is explained under the heading above.','此名称对应上方条目的说明。'),{class:'muted','data-alias':''}));
      if(record.status==='deprecated')section.append(retirement(record));
      const aside=node('aside','',{class:'aside'});add(aside,limitation(record),owner(record));
      add(section,add(node('div','',{class:'detail-grid'}),lesson(record),aside));
      section.append(disclosure(t('Why it matters','为什么重要'),[node('p',value(record.why))]));
      const caveats=node('ul');for(const text of record.caveats[route.lang])caveats.append(node('li',text));
      section.append(disclosure(t('Full limits & definition','完整局限与定义'),[node('p',value(record.definition)),caveats]));
      const sources=[];
      if(record.public_source_refs.length){for(const url of record.public_source_refs)sources.push(node('a',new URL(url).hostname,{href:url,rel:'noopener noreferrer','data-source':''}));}
      else sources.push(node('p',t('No public source link is attached to this definition.','此定义暂未附上公开来源链接。')));
      section.append(disclosure(t('Sources','来源'),sources));
      section.append(related(record.related_ids,t('Related explanations','相关说明')));
      return section;
    }
    function coveragePage(record){
      const section=node('section','',{class:'stack','data-coverage':record.state});
      add(section,button('← '+t('Market Guide','市场指南'),()=>navigate(),{class:'bare'}),node('h1',value(record.label),{tabindex:'-1'}));
      const labels={not_an_indicator:t('A dashboard view, not an indicator.','这是看板视图，不是单项指标。'),not_covered:t('This explanation is not available yet.','此说明暂未提供。'),covered_by:t('This view combines the following explanations.','该视图对应以下说明。')};
      add(section,node('h2',labels[record.state]),node('p',value(record.reason)),related(record.related_ids,t('Read the underlying signals','了解组成指标')),owner(record));
      return section;
    }
    function missingPage(resolution){
      const section=node('section','',{class:'empty'});
      add(section,node('h1',resolution.status==='ambiguous'?t('Which explanation do you need?','你需要哪项说明？'):t('This name is not in the guide.','指南中没有这个名称。'),{tabindex:'-1'}),node('p',resolution.matched,{'data-missing-name':''}));
      if(resolution.status==='ambiguous')for(const id of resolution.ids)section.append(targetLink(id,value(model.get(id).label)));
      else section.append(node('p',t('Try the common name, or browse the guide.','试试常用名称，或浏览指南。')));
      section.append(button(t('Browse all signals','浏览全部指标'),()=>{route.browsing=true;route.query='';route.topic='';navigate();},{class:'pill'}));
      return section;
    }
    function resultRows(records,parent){
      parent.replaceChildren();
      if(!records.length){add(parent,node('h3',t('No matching explanation.','暂未找到匹配说明。')),node('p',t('Try another name or clear the filters.','请尝试其他名称，或清除筛选。')));return;}
      for(const record of records){
        const row=node('article','',{class:'result'}), main=node('div','',{class:'result-main'});
        add(main,targetLink(record.id,value(record.label)),node('p',value(record.definition)||value(record.reason)||t('See the related explanation.','请查看相关说明。')));
        add(row,main);
        if(record.presentation)row.append(button(t('Explain','解读'),event=>openHelp(record.id,event.currentTarget),{class:'pill','aria-label':t('Quick explanation: ','快速解读：')+value(record.label),'data-help':record.id}));
        else row.append(node('span',t('Dashboard view','看板视图'),{class:'muted'}));
        parent.append(row);
      }
    }
    function home(){
      const section=node('section');
      add(section,node('h1',t('Market Guide','市场指南'),{tabindex:'-1'}),node('p',t('Ask what a score or signal means. Get the answer in seconds.','问一个分数或信号代表什么，几秒内看懂。'),{class:'subtitle'}));
      const search=node('input','',{type:'search',id:'search','aria-label':t('Search signals and questions','搜索指标与问题'),placeholder:t('Ask about a score or signal…','问一个分数或信号…')});search.value=route.query;
      section.append(add(node('label','',{class:'searchbox'}),icon('search'),search,node('kbd','/',{'aria-hidden':'true'})));
      const landing=node('section','',{id:'landing'}), rows=node('section','',{id:'results'});
      add(landing,node('h3',t('Start with a question','从一个问题开始')));
      const cards=node('div','',{class:'questions'});
      const hints={strength:['Trend, participation and the big picture.','趋势、参与度与整体状态。'],risk:['Stress, volatility and warning signals.','压力、波动与预警信号。'],backdrop:['Growth, inflation and financial conditions.','增长、通胀与金融条件。']};
      for(const q of model.questions){
        const card=button('',()=>{route.topic=q.id;route.query='';route.browsing=true;storeURL();render();},{class:'question','data-topic':q.id});
        const copy=node('span','',{class:'guide-question-copy'});copy.append(node('strong',value(q.label)));if(hints[q.id])copy.append(node('small',t(...hints[q.id])));
        add(card,icon(q.id),copy,node('span','→',{class:'guide-question-arrow','aria-hidden':'true'}));cards.append(card);
      }
      landing.append(cards);
      const featured=model.get('market-state-score');
      if(featured){
        const feature=node('section','',{class:'feature'}), intro=node('div','',{class:'stack'});
        add(intro,node('span',t('START WITH THE BIG PICTURE','先看整体'),{class:'eyebrow muted'}),node('h2',t('Six inputs. One market read.','六项输入，一个整体判断。')),node('p',t('See how the Market State Score brings the moving parts together.','了解市场状态分如何汇总市场的多个侧面。')),targetLink(featured.id,t('Explore the full guide →','查看完整说明 →')),button(t('Quick explanation','快速解读'),event=>openHelp(featured.id,event.currentTarget),{class:'bare','data-help':featured.id}));
        const visual=node('div','',{class:'guide-feature-visual'}),map=ingredientMap();if(map)visual.append(map);visual.append(lesson(featured,true));add(feature,intro,visual);landing.append(feature);
      }
      landing.append(add(node('div','',{class:'library-footer'}),node('span',t('Looking for a specific term?','想查某个术语？'),{class:'muted'}),button(t('Browse all signals →','浏览全部指标 →'),()=>{route.browsing=true;route.query='';route.topic='';storeURL();render();},{class:'bare','data-browse':''})));
      const count=node('p','',{role:'status','aria-live':'polite',id:'result-count',class:'muted'}),list=node('div','',{class:'result-list',id:'result-list'});
      const resultsHeading=node('h3','',{id:'results-title'});
      add(rows,add(node('div','',{class:'row'}),resultsHeading,button(t('Clear filters','清除筛选'),()=>{route.query='';route.topic='';route.browsing=false;storeURL();render();document.getElementById('search')?.focus();},{class:'bare','data-reset':''})),count,list);
      function results(){
        resultsHeading.textContent=value(model.questions.find(q=>q.id===route.topic)?.label)||t('Signals, terms & dashboard names','指标、术语与看板名称');
        landing.hidden=route.browsing;rows.hidden=!route.browsing;
        // Do not create the hidden full catalog at rest. Build only when requested.
        if(!route.browsing){list.replaceChildren();count.textContent='';return;}
        const found=model.search(route.query,route.topic);count.textContent=t(`${found.length} explanations`,`${found.length} 项说明`);resultRows(found,list);
      }
      search.addEventListener('input',()=>{route.query=search.value;route.topic='';route.browsing=Boolean(route.query);storeURL();results();});
      search.addEventListener('keydown',event=>{
        if(event.key!=='Enter'||!route.query.trim())return;
        const exact=model.resolve(route.query);
        if(exact.status==='found'){event.preventDefault();navigate(exact.id);}
      });
      add(section,landing,rows);results();return section;
    }
    function renderModal(){
      const record=model.get(modal);dialog.replaceChildren();
      const close=button('×',()=>dialog.close(),{class:'close','aria-label':t('Close explanation','关闭说明'),'data-close':''});
      add(dialog,add(node('div','',{class:'row'}),node('span',t('QUICK EXPLANATION','快速解读'),{class:'eyebrow muted'}),close),node('h2',value(record.label),{id:'help-title'}));
      if(currentContext&&(currentContext.en||currentContext.zh)){
        const current=node('section','',{class:'guide-current','data-guide-current':''});
        const currentHead=add(node('div','',{class:'row'}),node('span',t('CURRENT READING','当前读数'),{class:'eyebrow'}));
        if(currentContext.asof)currentHead.append(node('span',currentContext.asof,{class:'example-label','data-guide-current-asof':''}));
        add(current,currentHead,node('strong',route.lang==='zh'?currentContext.zh:currentContext.en,{'data-guide-current-value':''}));dialog.append(current);
      }
      dialog.append(node('p',value(record.definition),{class:'muted'}));
      if(record.status==='deprecated')dialog.append(retirement(record));
      add(dialog,lesson(record,true),limitation(record),add(node('div','',{class:'dialog-actions'}),targetLink(record.id,t('Open full guide →','打开完整指南 →')),button(t('Back to where I was','返回刚才的位置'),()=>dialog.close(),{class:'pill','data-close':''})));
    }
    function openHelp(id,opener){const record=model.get(id);if(!record?.presentation)return;currentContext=currentReading(opener);if(currentContext?.reading){const allowed=record.presentation.kind==='quadrant'?['growth-down-inflation-down','growth-up-inflation-down','growth-down-inflation-up','growth-up-inflation-up']:record.presentation.readings.map(item=>item.id);if(allowed.includes(currentContext.reading))stateByEntry.set(id,currentContext.reading);}if(dialog.open){modal=id;renderModal();dialog.querySelector('[data-close]').focus();return;}modal=id;trigger=opener;restoreOnClose=true;closeScroll=window.scrollY;renderModal();dialog.showModal();dialog.querySelector('[data-close]').focus();}
    function render(){
      if(contextOnly){if(modal)renderModal();return;}
      document.documentElement.lang=route.lang==='zh'?'zh-CN':'en';
      const language=document.getElementById('language'),theme=document.getElementById('theme');
      if(language)language.textContent=route.lang==='en'?'中文':'EN';
      if(theme)theme.textContent=document.documentElement.dataset.theme==='dark'?t('Light','浅色'):t('Dark','深色');
      const resolution=route.fragment?model.resolve(route.fragment):null;route.resolution=resolution;
      host.replaceChildren(resolution?(resolution.status==='found'?(model.get(resolution.id).presentation?entryPage(model.get(resolution.id)):coveragePage(model.get(resolution.id))):missingPage(resolution)):home());
      if(route.duplicate)host.prepend(node('p',t('This link contains repeated filters. Use search to choose a single filter.','此链接包含重复筛选，请通过搜索重新选择。'),{role:'status','data-route-warning':''}));
      if(modal)renderModal();
      document.title=(resolution?.status==='found'?value(model.get(resolution.id).label)+' — ':'')+t('Market Guide','市场指南');
    }
    remember('close',()=>{modal=null;currentContext=null;if(restoreOnClose&&trigger?.isConnected){trigger.focus({preventScroll:true});window.scrollTo(0,closeScroll);}trigger=null;restoreOnClose=true;},dialog);
    // Contain both ends of the Tab sequence; native Escape/inert behavior stays native.
    remember('keydown',event=>{
      if(event.key!=='Tab'||!dialog.open)return;
      const controls=Array.from(dialog.querySelectorAll('a[href],button,input,select,textarea,[tabindex]'))
        .filter(item=>!item.disabled&&item.tabIndex>=0&&!item.closest('[hidden],[inert]')&&item.getClientRects().length);
      if(!controls.length){event.preventDefault();return;}
      const first=controls[0],last=controls[controls.length-1],active=document.activeElement;
      if(event.shiftKey&&(active===first||!dialog.contains(active))){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&(active===last||!dialog.contains(active))){event.preventDefault();first.focus();}
    },dialog);
    remember('langchange',()=>{
      route.lang=document.documentElement.getAttribute('data-lang')==='zh'?'zh':'en';
      const focusedChoice=dialog.open?document.activeElement?.getAttribute('data-choice'):null;
      render();if(dialog.open)(focusedChoice?dialog.querySelector('[data-choice="'+focusedChoice+'"]'):dialog.querySelector('[data-close]'))?.focus();
    },document);
    if(!contextOnly){
    remember('popstate',()=>{if(dialog.open)dialog.close();route=Guide.readRoute(location.href,model);stateByEntry.clear();render();});
    remember('hashchange',()=>{route=Guide.readRoute(location.href,model);stateByEntry.clear();render();});
    remember('keydown',event=>{if(event.key==='/'&&!dialog.open&&!/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)&&!document.activeElement.isContentEditable){event.preventDefault();document.getElementById('search')?.focus();}});
    const language=document.getElementById('language'),theme=document.getElementById('theme');
    if(language)remember('click',()=>{route.lang=route.lang==='en'?'zh':'en';storeURL();render();language.focus();},language);
    if(theme)remember('click',()=>{document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark';render();theme.focus();},theme);
    if(fallback)fallback.hidden=true;host.hidden=false;render();
    } else {
      remember('click',event=>{
        const opener=event.target.closest?.('[data-guide-entry]');
        if(!opener||event.defaultPrevented||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
        const record=model.get(opener.getAttribute('data-guide-entry'));
        if(!record?.presentation)return; // Original link remains the fallback.
        event.preventDefault();openHelp(record.id,opener);
      },document);
    }
    return {model,openHelp,dispose(){if(dialog.open)dialog.close();listeners.forEach(remove=>remove());if(!contextOnly)host.replaceChildren();dialog.replaceChildren();if(fallback)fallback.hidden=false;}};
  }
  root.MastermindGuideView=Object.freeze({mount});
})(globalThis);
