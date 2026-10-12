/* Design review only. Deterministic local lookup; no model, network or live market state. */
(() => {
  'use strict';
  const registry = JSON.parse(document.getElementById('registry').textContent);
  const entries = registry.entries;
  const byId = new Map(entries.map(entry => [entry.id, entry]));
  const app = document.getElementById('app');
  const dialog = document.getElementById('help');
  const params = new URLSearchParams(location.search);
  let lang = params.get('lang') === 'zh' ? 'zh' : 'en';
  let query = params.get('q') || '';
  let topic = params.get('topic') || '';
  let browsing = params.get('browse') === 'all' || Boolean(query || topic);
  let detailId = decodeHash();
  let lastTrigger = null;
  let modalId = null;
  let scrollBeforeHelp = 0;
  let state = 'mixed';
  const topics = {
    strength: ['regime', 'breadth-participation', 'doctrine'],
    risk: ['volatility-stress', 'credit', 'flows-positioning'],
    backdrop: ['rates-curve', 'liquidity', 'cross-asset-basics', 'calendar-events']
  };
  if (!Object.hasOwn(topics, topic)) topic = '';
  const t = (en, zh) => lang === 'zh' ? zh : en;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm = value => String(value || '').normalize('NFKC').toLowerCase().replace(/[\p{P}\p{Z}\s]+/gu, '');
  const field = (entry, name) => entry[`${name}_${lang}`] || (lang === 'en' ? entry[name] : '') || '';
  const short = entry => entry.id === 'market-state-score' ? t('A snapshot of how supportive conditions are for US stocks.', '用一个读数，概括当前美股环境的支持程度。') : field(entry, 'short_definition');
  const icon = kind => {
    const paths = {search:'<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/>',strength:'<path d="M4 20v-5m6 5V10m6 10V6m6 14V2"/>',risk:'<path d="M12 3 21 7v6c0 5-9 10-9 10S3 18 3 13V7Z"/><path d="M12 8v5m0 3v1"/>',backdrop:'<path d="M12 2v20M2 12h20m2-8 4-4m8 16 4-4"/>'};
    return `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${paths[kind] || paths.strength}</svg>`;
  };
  const extraKeywords = {
    'market-state-score': ['How strong is the market', 'strength', '市场有多强', '总体情况'],
    'risk-radar': ['Is risk building', 'danger', '风险累积', '风险正在累积吗'],
    'regime-quadrant': ['What is driving the backdrop', 'growth inflation', '推动市场环境', '经济周期'],
    'market-breadth': ['How many stocks are participating', 'participation', '多少股票参与上涨'],
    'transition-state': ['How stable is the regime', 'regime change', '状态稳定吗']
  };
  const searchIndex = new Map(entries.map(entry => [entry.id, norm([entry.id, entry.label_en, entry.label_zh, ...(entry.aliases_en || []), ...(entry.aliases_zh || []), ...(extraKeywords[entry.id] || [])].join(' '))]));
  const stateCopy = {
    lower: () => [t('Conditions under pressure.', '市场环境承压。'),t('The overall read is less supportive. Inspect which components are driving the weakness.', '整体读数偏弱。先确认是哪些分项在拖累。')],
    mixed: () => [t('Mixed signals. Look underneath.', '分项不一致，先看拆解。'),t('Some inputs support the market. Others do not. The headline alone misses that tension.', '部分输入支持市场，另一些并不支持。只看总分，会错过这种分歧。')],
    higher: () => [t('More signals align.', '更多信号形成共识。'),t('The overall backdrop is more supportive. That is confirmation of conditions, not a guarantee of gains.', '整体环境更具支持性。这是对当前条件的确认，不是上涨保证。')]
  };
  function decodeHash() { try { return decodeURIComponent(location.hash.slice(1)); } catch (_) { return 'invalid-link'; } }
  function syncURL() {
    const url = new URL(location.href);
    for (const key of ['q','topic','browse','lang']) url.searchParams.delete(key);
    if (query) url.searchParams.set('q', query);
    if (topic) url.searchParams.set('topic', topic);
    if (browsing && !query && !topic) url.searchParams.set('browse', 'all');
    if (lang === 'zh') url.searchParams.set('lang', 'zh');
    url.hash = detailId;
    try { history.replaceState(null, '', url); } catch (_) { /* file previews may restrict history */ }
  }
  function go(id) {
    if (dialog.open) dialog.close();
    detailId = id;
    const url = new URL(location.href); url.hash = id;
    try { history.pushState(null, '', url); } catch (_) { location.hash = id; }
    render(); window.scrollTo(0, 0);
    app.querySelector('h1')?.focus({preventScroll:true});
  }
  function ingredients() {
    return `<div class="inputs">${[['Trend','趋势'],['Risk appetite','风险偏好'],['Volatility','波动率'],['Breadth','市场广度'],['Liquidity','流动性'],['Stress','压力']].map(([en,zh]) => `<div class="input-chip">${t(en,zh)}</div>`).join('')}</div><div class="input-arrow">${t('Read together → Market State Score', '综合观察 → 市场状态分')}</div>`;
  }
  function stateControls() {
    return `<div class="states" aria-label="${t('Conceptual examples, not live readings','概念示例，非实时读数')}">${[['lower','Lower','较低'],['mixed','Mixed','分化'],['higher','Higher','较高']].map(([id,en,zh]) => `<button type="button" data-state="${id}" aria-pressed="${state === id}">${t(en,zh)}</button>`).join('')}</div>`;
  }
  function helpBody(entry, compact=false) {
    if (entry.id === 'market-state-score') {
      const [title, description] = stateCopy[state]();
      return `<div class="row"><span class="eyebrow">${t('How to read it','怎么看')}</span><span class="example-label">${t('Illustration only','仅作示意')}</span></div>${stateControls()}<${compact ? 'h3' : 'h2'}>${title}</${compact ? 'h3' : 'h2'}><p class="state-summary" aria-live="polite">${description}</p>${compact ? '' : ingredients()}`;
    }
    const readings = [['interpretation_up',t('Higher / rising','较高 / 上升')],['interpretation_down',t('Lower / falling','较低 / 下降')],['interpretation_neutral',t('Mixed / non-directional','分化 / 无方向性')]].map(([key,label]) => {
      const value = field(entry,key); return value ? `<div><h3>${label}</h3><p>${esc(value)}</p></div>` : '';
    }).filter(Boolean);
    return `<div class="stack"><span class="eyebrow">${t('How to read it','怎么看')}</span>${readings.join('') || `<p>${esc(field(entry,'short_definition'))}</p>`}</div>`;
  }
  function ownerURL(entry) {
    if (!/^[a-z0-9_-]+\.html(?:#[a-zA-Z0-9_-]+)?$/.test(entry.owner_ref)) return null;
    return `https://www.mastermind-x.com/${entry.owner_ref}`;
  }
  function caution(entry) {
    const text = entry.id === 'market-state-score' ? t('A higher score does not guarantee gains. It describes the current backdrop.', '高分不保证上涨。它描述的是当前环境。') : (field(entry,'caveats')[0] || t('Read this alongside the owning dashboard, not in isolation.','请结合对应看板阅读，不要孤立判断。'));
    return `<div class="caution"><h3>${entry.id === 'market-state-score' ? t('Not a prediction.','不是预测。') : t('Keep in mind','请留意')}</h3><p>${esc(text)}</p></div>`;
  }
  function renderDetail(entry) {
    return `<button class="bare" data-home type="button">← ${t('Market Guide','市场指南')}</button><div class="detail-head"><h1 tabindex="-1">${esc(field(entry,'label'))}</h1><p>${esc(short(entry))}</p><div class="basis">${esc(field(entry,'unit_or_basis'))} · ${t('Guide, not live data','学习指南，非实时数据')}</div></div>${entry.status==='deprecated' ? `<p class="caution">${t('This definition is retired. Do not treat it as an active signal.','此定义已停用，请勿将其视为当前有效信号。')}</p>` : ''}<div class="detail-grid"><div class="lesson">${helpBody(entry)}</div><aside class="aside">${caution(entry)}<div class="where"><h3>${t('Use it in context','结合看板使用')}</h3><p>${t('Check the actual signal and the inputs behind it.','查看实际信号与背后的输入。')}</p>${ownerURL(entry) ? `<a href="${esc(ownerURL(entry))}">${t('Open the owning dashboard →','打开对应看板 →')}</a>` : `<p>${t('Dashboard link unavailable.','看板链接暂不可用。')}</p>`}</div></aside></div><details><summary>${t('Why it matters','为什么重要')}</summary><p>${esc(field(entry,'why_it_matters'))}</p></details><details><summary>${t('Limits & methodology','局限与方法说明')}</summary><p>${esc(field(entry,'short_definition'))}</p><ul>${(field(entry,'caveats') || []).map(item=>`<li>${esc(item)}</li>`).join('')}</ul></details><div class="related"><span class="muted">${t('RELATED','相关指标')}</span>${(entry.related_ids || []).filter(id=>byId.has(id)).map(id=>`<a href="#${esc(id)}" data-id="${esc(id)}">${esc(field(byId.get(id),'label'))}</a>`).join('')}</div>`;
  }
  function homeHTML() {
    return `<div class="context"><a href="https://www.mastermind-x.com/macro.html">← ${t('Macro dashboard','宏观看板')}</a><span>${t('GUIDE · NOT LIVE DATA','学习指南 · 非实时数据')}</span></div><h1 tabindex="-1">${t('Understand the signal.','读懂每一个市场信号。')}</h1><p class="subtitle">${t('What it means. How to read it. Where to use it.','看懂含义，理解变化，回到看板应用。')}</p><label class="searchbox">${icon('search')}<input id="search" type="search" autocomplete="off" aria-label="${t('Search signals and questions','搜索指标与问题')}" placeholder="${t('Search a signal or a question…','搜索指标，或你想了解的问题…')}" value="${esc(query)}"><kbd aria-hidden="true">/</kbd></label><section id="landing" ${browsing?'hidden':''}><h3>${t('What are you trying to understand?','你想了解什么？')}</h3><div class="questions">${[['strength','How strong is the market?','市场有多强？','Trend, participation and the big picture.','趋势、参与度与整体状态。'],['risk','Is risk building?','风险正在累积吗？','Stress, volatility and warning signals.','压力、波动与预警信号。'],['backdrop','What is driving the backdrop?','什么在推动市场环境？','Growth, inflation and financial conditions.','增长、通胀与金融条件。']].map(([id,en,zh,sub,cnsub])=>`<button class="question" data-topic="${id}" type="button">${icon(id)}<span><strong>${t(en,zh)}</strong><small>${t(sub,cnsub)}</small></span></button>`).join('')}</div><div class="feature"><div><div class="eyebrow muted">${t('Start with the big picture','先看整体')}</div><div class="lead">${t('Six inputs. One market read.','六项输入，一个整体判断。')}</div><p>${t('The Market State Score brings the market’s moving parts into one view.','市场状态分，将市场的多个侧面汇成一个读数。')}</p><button class="bare" data-id="market-state-score" type="button">${t('Explore Market State Score →','了解市场状态分 →')}</button><br><button class="bare" data-help="market-state-score" type="button">${t('Quick explanation','快速解读')}</button></div><div><div class="row"><span class="eyebrow muted">${t('Read the pattern','看懂组合')}</span><span class="example-label">${t('Illustration only','仅作示意')}</span></div>${ingredients()}${stateControls()}<div class="state-summary" aria-live="polite">${stateCopy[state]()[1]}</div></div></div><div class="library-footer"><span class="muted">${t('Looking for a specific term?','想查某个术语？')}</span><button class="bare" data-browse type="button">${t('Browse all signals →','浏览全部指标 →')}</button></div></section><section id="results" ${browsing?'':'hidden'} aria-labelledby="results-title"><div class="row"><h3 id="results-title">${t('Signals & terms','指标与术语')}</h3><button class="bare" data-reset type="button">${t('Clear filters','清除筛选')}</button></div><div id="result-count" class="muted" role="status" aria-live="polite"></div><div id="result-list" class="result-list"></div></section><p class="mini-note">${t('Interactive design prototype. Not a current market reading.','交互设计原型，非当前市场读数。')}</p>`;
  }
  function updateResults() {
    if (detailId) return;
    const needle = norm(query);
    const matches = entries.filter(entry => (!topic || topics[topic].includes(entry.family) || topic==='risk' && entry.id==='risk-radar') && (!needle || searchIndex.get(entry.id).includes(needle)));
    document.getElementById('landing').hidden = browsing;
    document.getElementById('results').hidden = !browsing;
    document.getElementById('result-count').textContent = t(`${matches.length} results`,`${matches.length} 条结果`);
    document.getElementById('result-list').innerHTML = matches.length ? matches.map(entry=>`<article class="result"><div class="result-main"><a href="#${esc(entry.id)}" data-id="${esc(entry.id)}">${esc(field(entry,'label'))}</a><p>${esc(short(entry))}</p></div><button class="pill" data-help="${esc(entry.id)}" type="button" aria-label="${esc(t('Quick explanation: ','快速解读：')+field(entry,'label'))}">${t('Explain','解读')}</button></article>`).join('') : `<div class="empty"><h2>${t('No matching signal yet.','暂未找到匹配指标。')}</h2><p>${t('Try an indicator name, its common alias, or browse the full guide.','试试指标名称、常用别名，或浏览完整指南。')}</p><button class="pill" data-browse type="button">${t('Browse all signals','浏览全部指标')}</button></div>`;
  }
  function render() {
    document.documentElement.classList.add('js');
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    document.getElementById('language').textContent = lang === 'en' ? '中文' : 'EN';
    document.getElementById('theme').textContent = document.documentElement.dataset.theme === 'dark' ? t('Light','浅色') : t('Dark','深色');
    document.title = `${detailId && byId.has(detailId) ? field(byId.get(detailId),'label')+' — ' : ''}${t('Market Guide','市场指南')} · ${t('Design prototype','设计原型')}`;
    app.innerHTML = detailId ? (byId.has(detailId) ? renderDetail(byId.get(detailId)) : `<div class="empty"><h1 tabindex="-1">${t('This signal is not in the guide.','指南中没有这个指标。')}</h1><p>${t('The link may be outdated. Browse the guide to find the right explanation.','链接可能已失效。请在指南中查找对应说明。')}</p><button class="pill" data-home type="button">${t('Back to Market Guide','返回市场指南')}</button></div>`) : homeHTML();
    if (!detailId) updateResults();
    if (modalId) renderModal(byId.get(modalId));
    syncURL();
  }
  function renderModal(entry) {
    dialog.innerHTML = `<div class="row"><span class="eyebrow muted">${t('Quick explanation','快速解读')}</span><button class="close" data-close aria-label="${t('Close explanation','关闭说明')}" type="button">×</button></div><h2 id="help-title">${esc(field(entry,'label'))}</h2><p class="muted">${esc(short(entry))}</p><div class="lesson">${helpBody(entry,true)}</div>${caution(entry)}<div class="dialog-actions"><button class="bare" data-id="${esc(entry.id)}" type="button">${t('Open full guide →','打开完整指南 →')}</button><button class="pill" data-close type="button">${t('Back to where I was','返回刚才的位置')}</button></div>`;
  }
  function openHelp(id,trigger) {
    if (!byId.has(id)) return;
    modalId=id; lastTrigger=trigger; scrollBeforeHelp=window.scrollY;
    renderModal(byId.get(id)); dialog.showModal(); dialog.querySelector('[data-close]').focus();
  }
  document.addEventListener('click', event => {
    const target=event.target.closest('button,a'); if (!target) return;
    if (target.id==='brand') { event.preventDefault(); go(''); return; }
    if (target.hasAttribute('data-id')) { event.preventDefault(); go(target.dataset.id); return; }
    if (target.hasAttribute('data-help')) { openHelp(target.dataset.help,target); return; }
    if (target.hasAttribute('data-close')) { dialog.close(); return; }
    if (target.hasAttribute('data-home')) { go(''); return; }
    if (target.hasAttribute('data-topic')) { topic=target.dataset.topic;query='';browsing=true;render();return; }
    if (target.hasAttribute('data-browse')) { topic='';query='';browsing=true;detailId='';render();return; }
    if (target.hasAttribute('data-reset')) { topic='';query='';browsing=false;render();document.getElementById('search').focus();return; }
    if (target.hasAttribute('data-state')) {
      state=target.dataset.state;
      const focusKey=target.dataset.state;
      if (dialog.open) { renderModal(byId.get(modalId));dialog.querySelector(`[data-state="${focusKey}"]`).focus(); }
      else { render();app.querySelector(`[data-state="${focusKey}"]`)?.focus({preventScroll:true}); }
    }
  });
  document.addEventListener('input', event => { if (event.target.id==='search') { query=event.target.value;topic='';browsing=Boolean(query);updateResults();syncURL(); } });
  document.addEventListener('keydown', event => { if (event.key==='/' && !dialog.open && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && !document.activeElement.isContentEditable) { event.preventDefault();document.getElementById('search')?.focus(); } });
  document.getElementById('language').addEventListener('click',()=>{lang=lang==='en'?'zh':'en';render();document.getElementById('language').focus();});
  document.getElementById('theme').addEventListener('click',()=>{document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark';render();document.getElementById('theme').focus();});
  dialog.addEventListener('close',()=>{modalId=null;if(lastTrigger?.isConnected){lastTrigger.focus({preventScroll:true});window.scrollTo(0,scrollBeforeHelp);}lastTrigger=null;});
  window.addEventListener('popstate',()=>{const q=new URLSearchParams(location.search);query=q.get('q')||'';topic=Object.hasOwn(topics,q.get('topic'))?q.get('topic'):'';browsing=Boolean(query||topic||q.get('browse')==='all');detailId=decodeHash();render();});
  window.addEventListener('hashchange',()=>{detailId=decodeHash();render();});
  render();
})();
