/* Shared product-navigation enhancement. Inventory remains _navlinks/nav_market.
   No routes, preferences, accounts, market data or persistence are created here. */
(function (global) {
  'use strict';
  var APPROVED = ['https://www.mastermind-x.com', 'https://mastermind-x.com',
    'https://app.mastermind-x.com', 'https://bot.mastermind-x.com'];
  var PILOT = ['/macro.html', '/sector_central.html', '/reports.html'];
  function text(value, max) { return typeof value === 'string' ? value.trim().slice(0, max || 400) : ''; }
  function normalize(value) { return text(value, 1000).normalize('NFKC').toLocaleLowerCase().replace(/\s+/g, ' '); }
  function targetURL(value, base) {
    if (typeof value !== 'string' || !value || value === '#' || /[\x00-\x20\x7f]/.test(value)) return null;
    try {
      var source = new URL(base), url = new URL(value, source);
      if (url.username || url.password || !/^https?:$/.test(url.protocol)) return null;
      if (url.origin !== source.origin && APPROVED.indexOf(url.origin) < 0) return null;
      return url.href;
    } catch (_) { return null; }
  }
  function project(records, options) {
    var seen = Object.create(null), result = [], base = options && options.baseURI;
    (records || []).forEach(function (record) {
      if (!record || record.enabled === false) return;
      var href = targetURL(record.href, base), en = text(record.en), zh = text(record.zh);
      if (!href || (!en && !zh) || seen[href]) return;
      seen[href] = true;
      var target = record.target === '_blank' ? '_blank' : '';
      result.push(Object.freeze({href: href, en: en || zh, zh: zh || en,
        descriptionEn: text(record.descriptionEn), descriptionZh: text(record.descriptionZh),
        group: text(record.group) || 'Other tools', groupZh: text(record.groupZh) || text(record.group) || '其他工具',
        section: text(record.section), sectionZh: text(record.sectionZh) || text(record.section),
        target: target, rel: target ? 'noopener noreferrer' : '', badge: text(record.badge, 20)}));
    });
    return Object.freeze(result);
  }
  function select(items, options) {
    var query = normalize(options && options.query), group = options && options.group;
    return items.filter(function (item) {
      if (!query) return !group || group === 'all' || item.group === group;
      var haystack = normalize([item.en, item.zh, item.descriptionEn, item.descriptionZh, item.group, item.groupZh].join(' '));
      return query.split(' ').every(function (word) { return haystack.indexOf(word) >= 0; });
    });
  }
  function startingPoints(items, count) {
    var groups = [], grouped = Object.create(null), result = [];
    items.forEach(function (item) { if (!grouped[item.group]) { groups.push(item.group); grouped[item.group] = []; } grouped[item.group].push(item); });
    for (var row = 0; result.length < count; row++) {
      var added = false;
      groups.forEach(function (key) { if (grouped[key][row] && result.length < count) { result.push(grouped[key][row]); added = true; } });
      if (!added) break;
    }
    return result;
  }
  function sameDestination(left, right, base) {
    return !!left && !!right && left.enabled !== false && right.enabled !== false &&
      !!targetURL(left.href, base) && targetURL(left.href, base) === targetURL(right.href, base);
  }
  function pair(node, fallback) {
    if (!node) return {en: fallback || '', zh: fallback || ''};
    var en = node.querySelector('.l-en'), zh = node.querySelector('.l-zh');
    return {en: text(en ? en.textContent : node.textContent), zh: text(zh ? zh.textContent : (en ? en.textContent : node.textContent))};
  }
  function sourceEnabled(anchor, root) {
    if (!anchor || !root.contains(anchor) || !anchor.isConnected) return false;
    // Dropdown panels are normally inert while closed. That is presentation,
    // not a destination entitlement. Explicit destination withdrawal is distinct.
    if (anchor.hidden || anchor.getAttribute('aria-disabled') === 'true') return false;
    for (var n = anchor; n && n !== root; n = n.parentElement) {
      if (n.getAttribute('data-nav-disabled') === 'true') return false;
      if(n.hidden && !n.classList.contains('nav-dd-menu') && !n.classList.contains('nav-drill-panel')) return false;
    }
    return true;
  }
  function describe(anchor, root) {
    var copy = anchor.cloneNode(true);
    copy.querySelectorAll('.d,.item-desc,.caret,.caret-r,.nm-tier,[aria-hidden="true"]').forEach(function (n) { n.remove(); });
    var title = pair(copy.querySelector('.nm-t,.item-title,.nav-sub-text') || copy);
    var description = pair(anchor.querySelector('.item-desc,.d'));
    var owner = anchor.closest('.nav-dd'), heading = null;
    if (owner) heading = owner.querySelector(':scope > .nav-link,:scope > .nav-sub-trig,:scope > [data-nav-drill-open]');
    var group = pair(heading, 'Other tools');
    var badge = anchor.querySelector('.nm-tier');
    var sectionNode = anchor.closest('.nav-mega-section,.nav-market-section,.nav-mega-rail,.nav-market-rail');
    var section = pair(sectionNode && sectionNode.querySelector('.nav-mega-h,.nav-market-heading,.section-label')); 
    return {href: anchor.getAttribute('href'), en: title.en, zh: title.zh,
      descriptionEn: description.en, descriptionZh: description.zh, group: group.en, groupZh: group.zh,
      section: section.en, sectionZh: section.zh,
      target: anchor.getAttribute('target'), badge: badge ? badge.textContent : '', enabled: sourceEnabled(anchor, root)};
  }
  function collect(root, baseURI) {
    var records = [], refs = Object.create(null);
    root.querySelectorAll('a[href]').forEach(function (anchor) {
      if (anchor.classList.contains('nav-brand') || anchor.classList.contains('nav-link') || anchor.hasAttribute('data-nav-drill-open')) return;
      var record = describe(anchor, root), href = targetURL(record.href, baseURI);
      if (record.enabled && href && !refs[href]) refs[href] = anchor;
      records.push(record);
    });
    return {items: project(records, {baseURI: baseURI}), refs: refs};
  }
  function mount(host, options) {
    options = options || {};
    var doc = host && host.ownerDocument, win = doc && doc.defaultView;
    if (!host || !doc || !win || host.__mmxTools) return host && host.__mmxTools || null;
    if (doc.querySelector('[data-mmx-tools-mounted]')) return null;
    var nav = host.previousElementSibling, root = nav && nav.querySelector('.nav-links');
    var dialog = host.querySelector('dialog'), trigger = host.querySelector('[data-tools-open]');
    if (!nav || !nav.matches('nav.site-nav') || !root || !dialog || !trigger || typeof dialog.showModal !== 'function') return null;
    if (!options.force && PILOT.indexOf(win.location.pathname) < 0) return null;
    var controls = nav.querySelector('.nav-ctrls');
    if (!controls) return null;
    var query = host.querySelector('[data-tools-query]'), list = host.querySelector('[data-tools-results]');
    var categories = host.querySelector('[data-tools-categories]'), status = host.querySelector('[data-tools-status]');
    var count = host.querySelector('[data-tools-count]'), title = host.querySelector('[data-tools-title]');
    var close = host.querySelector('[data-tools-close]'), clear = host.querySelector('[data-tools-clear]');
    var all = host.querySelector('[data-tools-all]');
    var scroller = host.querySelector('[data-tools-scroll]') || list;
    if(!query||!list||!categories||!status||!count||!title||!close||!clear||!all)return null;
    var snapshot = null, contextGroup = null, group = 'start', composing = false, opener = null, live = false, observer = null;
    var withdrawn = Object.create(null); // presentation-only, reset on explicit reopen
    function zh() { return doc.documentElement.getAttribute('data-lang') === 'zh'; }
    function say(en, cn) { return zh() ? cn : en; }
    function node(tag, className, content) { var n = doc.createElement(tag); if (className) n.className = className; if (content != null) n.textContent = content; return n; }
    function icon(source) {
      var original = source && source.querySelector('svg');
      var out = doc.createElementNS('http://www.w3.org/2000/svg', 'svg');
      out.setAttribute('viewBox', original && original.getAttribute('viewBox') || '0 0 48 48');
      out.setAttribute('aria-hidden', 'true');
      var tags = ['path','rect','circle','ellipse','line','polyline','polygon','g'];
      var attrs = ['d','x','y','width','height','rx','ry','cx','cy','r','x1','x2','y1','y2','points','class','transform','fill-rule','clip-rule'];
      function copy(sourceNode, dest) { Array.from(sourceNode.children || []).forEach(function (child) {
        if (tags.indexOf(child.tagName.toLowerCase()) < 0) return;
        var n = doc.createElementNS('http://www.w3.org/2000/svg', child.tagName.toLowerCase());
        attrs.forEach(function (key) { if (child.hasAttribute(key)) n.setAttribute(key, child.getAttribute(key)); });
        dest.appendChild(n); copy(child, n);
      }); }
      if (original) copy(original, out);
      if (!out.childNodes.length) { var p = doc.createElementNS(out.namespaceURI,'path'); p.setAttribute('d','M10 10h28v28H10zM10 24h28M24 10v28'); out.appendChild(p); }
      return out;
    }
    function render() {
      if (!snapshot) return;
      var active = doc.activeElement;
      var focusedHref = active && list.contains(active) ? active.dataset.toolsHref : null;
      var searching = !!normalize(query.value);
      var items = searching ? select(snapshot.items,{query:query.value}) : group === 'start' ? startingPoints(select(snapshot.items,{group:contextGroup}),12) : select(snapshot.items,{group:group});
      list.replaceChildren(); count.textContent = say(items.length+' destinations',items.length+' 个目的地');
      clear.hidden = !query.value;
      categories.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', String(!searching && b.dataset.toolsGroup === group)); });
      all.disabled = !snapshot.items.length;
      if (!snapshot.items.length) {
        count.textContent=say('Links not ready','链接尚未就绪');
        var unavailable=node('section','mmx-tools-empty');
        unavailable.appendChild(node('h3','',say('Tool links are not ready.','工具链接尚未就绪。')));
        unavailable.appendChild(node('p','',say('The navigation source is unavailable. Your current page has not changed.','导航来源暂不可用，当前页面保持不变。')));
        var back=node('button','mmx-tools-action',say('Return to this page','返回当前页面'));back.type='button';back.dataset.toolsDismiss='true';unavailable.appendChild(back);list.appendChild(unavailable);
      } else if (!items.length) {
        var empty = node('section','mmx-tools-empty');
        empty.appendChild(node('h3','',say('No matching tools.','未找到匹配工具。')));
        empty.appendChild(node('p','',say('Try a tool name or browse the available destinations.','尝试工具名称，或浏览可用目的地。')));
        var reset = node('button','mmx-tools-action',say('Show available tools','显示可用工具'));
        reset.type='button';reset.dataset.toolsReset='true';empty.appendChild(reset);list.appendChild(empty);
      } else {
        var panels = Object.create(null);
        items.forEach(function (item) {
          var key=item.group+'\u0000'+item.section;
          if (!panels[key]) { var section=node('section','mmx-tools-group');
            var heading = item.section ? (zh()?item.sectionZh:item.section) : (zh()?item.groupZh:item.group);
            if(group==='all'||searching) heading=(zh()?item.groupZh:item.group)+(item.section?' / '+heading:'');
            section.appendChild(node('h3','',heading));var grid=node('div','mmx-tools-grid');section.appendChild(grid);list.appendChild(section);panels[key]=grid; }
          var a=node('a','mmx-tools-link');a.href=item.href;a.dataset.toolsHref=item.href;
          if(item.target) { a.target=item.target;a.rel=item.rel; a.setAttribute('aria-label',(zh()?item.zh:item.en)+say(' — opens in a new tab',' — 在新标签页打开')); }
          var glyph=node('span','mmx-tools-glyph');glyph.appendChild(icon(snapshot.refs[item.href]));a.appendChild(glyph);
          var copy=node('span','mmx-tools-copy'), label=node('strong','',zh()?item.zh:item.en);copy.appendChild(label);
          if(item.badge)copy.appendChild(node('span','mmx-tools-badge',item.badge));
          var description=zh()?item.descriptionZh||item.descriptionEn:item.descriptionEn;
          if(description)copy.appendChild(node('span','mmx-tools-description',description));
          a.appendChild(copy);var arrow=node('span','mmx-tools-arrow',item.target?'↗':'→');arrow.setAttribute('aria-hidden','true');a.appendChild(arrow);panels[key].appendChild(a);
        });
      }
      status.textContent = searching ? say(items.length+' matching destinations. Search includes every category.',items.length+' 个匹配目的地，范围涵盖所有分类。') : '';
      validateDestinations();
      if (focusedHref && live) {
        var replacement = Array.from(list.querySelectorAll('a[data-tools-href]')).find(function(a){return a.dataset.toolsHref===focusedHref && a.hasAttribute('href');});
        (replacement || title).focus({preventScroll:true});
      }
    }
    function paint() {
      var active=doc.activeElement, focusedGroup=active&&categories.contains(active)?active.dataset.toolsGroup:null;
      host.querySelectorAll('[data-en]').forEach(function(n){n.textContent=say(n.getAttribute('data-en'),n.getAttribute('data-zh'));});
      trigger.textContent=say('All tools','所有工具');
      query.placeholder=say('Find a tool or topic…','搜索工具或主题…');
      query.setAttribute('aria-label',say('Search tools, not ticker symbols','搜索工具，而非股票代码'));
      close.setAttribute('aria-label',say('Close all tools','关闭所有工具'));
      categories.setAttribute('aria-label',say('Tool categories','工具分类'));
      clear.setAttribute('aria-label',say('Clear tool search','清除工具搜索'));
      if(snapshot) { buildCategories(); var context=host.querySelector('[data-tools-context]');if(context){var current=snapshot.items.find(function(item){return item.group===contextGroup;});context.textContent=current?say('Start with '+current.group,'从'+current.groupZh+'开始'):say('Explore available workspaces','浏览可用工作台');}}render();
      if(focusedGroup && live) { var focus=Array.from(categories.querySelectorAll('button')).find(function(b){return b.dataset.toolsGroup===focusedGroup;});if(focus)focus.focus({preventScroll:true}); }
    }
    function buildCategories() {
      categories.replaceChildren();
      var choices=[{en:'Start here',zh:'从这里开始',key:'start'}], seen=Object.create(null);
      snapshot.items.forEach(function(item){if(!seen[item.group]){seen[item.group]=true;choices.push({en:item.group,zh:item.groupZh,key:item.group});}});
      choices.push({en:'All destinations',zh:'全部目的地',key:'all'});
      choices.forEach(function(item){var b=node('button','',zh()?item.zh:item.en);b.type='button';b.dataset.toolsGroup=item.key;b.setAttribute('aria-pressed',String(item.key===group));categories.appendChild(b);});
    }
    function sameSourceLink(a,source) {
      return !!source && targetURL(source.getAttribute('href'),doc.baseURI)===a.dataset.toolsHref &&
        (source.getAttribute('target')==='_blank'?'_blank':'')===(a.getAttribute('target')||'');
    }
    function rejectDestination(a) {
      withdrawn[a.dataset.toolsHref] = true;
      a.removeAttribute('href');
      a.setAttribute('aria-disabled','true');
      a.setAttribute('tabindex','-1');
    }
    function validateDestinations() {
      if (!snapshot) return;
      var links = Array.from(list.querySelectorAll('a[data-tools-href]'));
      var invalid = 0;
      links.forEach(function(a){
        var source = snapshot.refs[a.dataset.toolsHref];
        if (withdrawn[a.dataset.toolsHref] || !sourceEnabled(source,root) || !sameSourceLink(a,source)) {
          rejectDestination(a); invalid++;
        }
      });
      if (invalid) {
        count.textContent = say(links.length+' destinations · '+invalid+' unavailable', links.length+' 个目的地 · '+invalid+' 个暂不可用');
        status.textContent = say('Some destinations changed. Close and reopen tools to refresh.','部分目的地已变化，请关闭并重新打开工具菜单。');
      }
    }
    function guardDestination(e) {
      var a=e.target.closest('a[data-tools-href]');
      if (!a || !list.contains(a) || !snapshot) return;
      var source=snapshot.refs[a.dataset.toolsHref];
      if (withdrawn[a.dataset.toolsHref] || !sourceEnabled(source,root) || !sameSourceLink(a,source)) {
        e.preventDefault(); rejectDestination(a); validateDestinations();
        status.textContent=say('This destination changed. Close and reopen tools to refresh.','此目的地已变化，请关闭并重新打开工具菜单。');
      }
      // Valid links retain native click, auxiliary-button and context-menu behavior.
    }
    function otherModal() {
      return Array.from(doc.querySelectorAll('dialog[open],[aria-modal="true"]')).some(function(n){return n!==dialog && !n.hidden && n.getClientRects().length>0;});
    }
    function open() {
      if (live || otherModal()) return false;
      snapshot=collect(root,doc.baseURI);withdrawn=Object.create(null);
      var current=snapshot.items.find(function(item){return new URL(item.href).pathname===win.location.pathname;});
      contextGroup=current?current.group:null;
      group='start';query.value='';composing=false;opener=doc.activeElement;paint();
      try { dialog.showModal(); } catch(_){return false;}
      live=true;doc.documentElement.classList.add('mmx-tools-open');trigger.setAttribute('aria-expanded','true');
      if(typeof win.MutationObserver==='function') {
        observer=new win.MutationObserver(function(){
          if(!live||!snapshot)return;
          validateDestinations();
        });
        observer.observe(root,{subtree:true,childList:true,attributes:true,attributeFilter:['href','target','hidden','aria-disabled','data-nav-disabled']});
      }
      (win.matchMedia('(max-width: 600px)').matches?title:query).focus({preventScroll:true});return true;
    }
    function restore() {
      if(!live)return;live=false;if(observer){observer.disconnect();observer=null;}doc.documentElement.classList.remove('mmx-tools-open');trigger.setAttribute('aria-expanded','false');
      snapshot=null;withdrawn=Object.create(null);query.value='';list.replaceChildren();categories.replaceChildren();status.textContent='';
      if(opener && opener.isConnected)opener.focus({preventScroll:true});opener=null;
    }
    function dismiss(){if(dialog.open)dialog.close();restore();}
    trigger.addEventListener('click',open);close.addEventListener('click',dismiss);
    dialog.addEventListener('cancel',function(e){e.preventDefault();dismiss();});
    dialog.addEventListener('close',function(){if(!dialog.open)restore();});
    categories.addEventListener('click',function(e){var b=e.target.closest('button[data-tools-group]');if(!b||!categories.contains(b))return;group=b.dataset.toolsGroup;query.value='';render();scroller.scrollTop=0;});
    query.addEventListener('compositionstart',function(){composing=true;});
    query.addEventListener('compositionend',function(){composing=false;render();scroller.scrollTop=0;});
    query.addEventListener('input',function(){if(!composing){render();scroller.scrollTop=0;}});
    clear.addEventListener('click',function(){query.value='';render();query.focus({preventScroll:true});});
    all.addEventListener('click',function(){group='all';query.value='';render();scroller.scrollTop=0;});
    list.addEventListener('click',function(e){
      var returnButton=e.target.closest('[data-tools-dismiss]');if(returnButton&&list.contains(returnButton)){dismiss();return;}
      var reset=e.target.closest('[data-tools-reset]');if(reset&&list.contains(reset)){group='all';query.value='';render();query.focus({preventScroll:true});return;}
      guardDestination(e);
    });
    list.addEventListener('auxclick',guardDestination);
    list.addEventListener('contextmenu',guardDestination);
    doc.addEventListener('langchange',paint);
    controls.insertBefore(trigger,controls.firstChild);trigger.hidden=false;host.setAttribute('data-mmx-tools-mounted','true');
    host.__mmxTools={open:open,close:dismiss,refresh:paint};paint();return host.__mmxTools;
  }
  var api={project:project,select:select,startingPoints:startingPoints,sameDestination:sameDestination,collect:collect,mount:mount};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else { global.MMXAllTools=api;var script=global.document.currentScript;var host=script&&script.closest('[data-mmx-all-tools]');
    if(host){if(global.document.readyState==='loading')global.document.addEventListener('DOMContentLoaded',function(){mount(host);},{once:true});else mount(host);}
  }
})(typeof window!=='undefined'?window:globalThis);
