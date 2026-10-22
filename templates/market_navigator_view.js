/* Market Navigator — read-only, self-contained DOM view of the validated consumer state.
 * No transport, entitlement, identity, source interpretation, auto-mount, storage or
 * notification owner. Host provides an exact element and client.render(state).
 * All dynamic text goes through textContent; supplied keys never become HTML/CSS.
 */
(function (root, factory) {
  'use strict';
  const view = factory();
  if (typeof module === 'object' && module.exports) module.exports = view;
  else root.MastermindNavigatorView = view;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const STATE = ['empty', 'loading', 'unavailable', 'invalid_response', 'recorded_context'];
  const HORIZON = ['intraday', 'swing', 'position'];
  const VERDICTS = ['RISK_ON', 'MIXED', 'RISK_OFF'];
  const STATUSES = ['waiting', 'conditions_met', 'invalidated', 'unresolved', 'expired',
    'subject_mismatch', 'horizon_mismatch'];
  const CONDITIONS = ['gt', 'gte', 'lt', 'lte'];
  const TEXT = Object.freeze({
    en: {
      app: 'Market Navigator', subtitle: 'Evidence desk', context: 'MARKET CONTEXT',
      intro: 'Know what is established. Keep the rest open.',
      waiting: 'No validated context selected',
      loading: 'Checking the selected evidence…',
      unavailable: 'The requested evidence is unavailable.',
      invalid_response: 'The returned evidence did not pass validation.',
      empty: 'Select an admitted context in the host application to begin.',
      noLive: 'Research-only context · Not a signal or recommendation',
      noOdds: 'No calibrated probabilities', asOf: 'Knowledge cutoff',
      canonical: 'Canonical market context', notVerified: 'Market context not verified',
      riskOn: 'Risk-on', mixed: 'Mixed', riskOff: 'Risk-off',
      eligibility: 'Evidence coverage', current: 'Current', notCurrent: 'Unavailable / not current',
      paths: 'Conditional paths', noPaths: 'No research scenarios were supplied.',
      status: 'State at this cutoff', trigger: 'CONDITIONS TO WATCH',
      invalidation: 'CONDITIONS THAT INVALIDATE', supports: 'SUPPORTING EVIDENCE',
      challenges: 'COUNTEREVIDENCE', noEvidence: 'Not supplied',
      met: 'True at cutoff', unmet: 'False at cutoff', unknown: 'Not established',
      deadline: 'Deadline', defined: 'Rule known since',
      observed: 'Available since', valid: 'Valid until', evidence: 'Inspect source conditions',
      formula: 'A condition true now does not prove an earlier crossing, sustained hold or profitable trade.',
      abstain: 'No qualifying observation supports a directional conclusion here.',
      expected: 'Included in the submitted research population; not ranked.',
      caveat: 'Evidence and rule availability are separate. Missing or stale data remain unresolved.',
      toggleLanguage: 'Switch to Chinese', toggleTheme: 'Toggle light and dark theme',
      dark: 'Dark', light: 'Light', instrument: 'Requested instrument',
      stateLabels: {waiting:'Waiting',conditions_met:'Conditions currently met',invalidated:'Invalidated',
        unresolved:'Unresolved',expired:'Expired',subject_mismatch:'Different instrument',
        horizon_mismatch:'Different horizon'},
      evidenceStatus: {current:'current',missing:'missing',stale:'stale',
        not_yet_available:'not yet available',unqualified:'not qualified',
        subject_mismatch:'instrument mismatch',horizon_mismatch:'horizon mismatch'},
      op: {gt:'>',gte:'≥',lt:'<',lte:'≤'},
      horizons: {intraday:'Intraday',swing:'Swing',position:'Position'}
    },
    zh: {
      app: '市场导航', subtitle: '证据观察台', context: '市场背景',
      intro: '分清已证实的信息，保留尚未确认的判断。',
      waiting: '尚未选择经过验证的市场背景',
      loading: '正在检查所选证据…',
      unavailable: '无法获取所请求的证据。',
      invalid_response: '返回的证据未通过验证。',
      empty: '请先在主应用中选择合规的市场背景。',
      noLive: '仅供研究参考 · 不是交易信号或投资建议',
      noOdds: '尚无经过校准的概率', asOf: '信息截止时间',
      canonical: '既有市场状态', notVerified: '市场状态尚未核实',
      riskOn: '风险偏好较强', mixed: '信号分歧', riskOff: '风险偏好较弱',
      eligibility: '证据覆盖范围', current: '有效', notCurrent: '缺失／不再有效',
      paths: '条件路径', noPaths: '尚未提供研究情景。',
      status: '截至该时点的状态', trigger: '需要观察的条件',
      invalidation: '可能使情景失效的条件', supports: '支持性证据',
      challenges: '相反证据', noEvidence: '未提供',
      met: '截止时点成立', unmet: '截止时点不成立', unknown: '尚未确认',
      deadline: '到期时间', defined: '规则可知时间',
      observed: '可用时间', valid: '有效至', evidence: '查看证据条件',
      formula: '目前条件成立并不代表此前已经突破、持续站稳或可实现盈利。',
      abstain: '当前缺乏足够合格证据，无法得出方向性结论。',
      expected: '仅为提交的研究情景，不构成优先顺序。',
      caveat: '证据可用时间与规则发布时间不同。缺失或过期数据须保留不确定状态。',
      toggleLanguage: 'Switch to English', toggleTheme: '切换深色／浅色',
      dark: '深色', light: '浅色', instrument: '所请求的标的',
      stateLabels: {waiting:'等待中',conditions_met:'当前条件成立',invalidated:'已失效',
        unresolved:'未确认',expired:'已到期',subject_mismatch:'标的不一致',
        horizon_mismatch:'周期不一致'},
      evidenceStatus: {current:'有效',missing:'缺失',stale:'过期',
        not_yet_available:'当时尚不可用',unqualified:'未获认可',
        subject_mismatch:'标的不一致',horizon_mismatch:'周期不一致'},
      op: {gt:'>',gte:'≥',lt:'<',lte:'≤'},
      horizons: {intraday:'日内',swing:'波段',position:'中期'}
    }
  });

  function elem(tag, className, text, attrs) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (attrs) Object.keys(attrs).forEach(k => node.setAttribute(k, String(attrs[k])));
    return node;
  }
  function add(parent) { for (let i = 1; i < arguments.length; i++) parent.appendChild(arguments[i]); return parent; }
  function sectionTitle(text) { return elem('h2', 'mnv-section-title', text); }
  function noAuthority(data) {
    if (!data || data.schema !== 'market_navigator.context/v1' || data.readiness !== 'research_only' ||
        !data.authority || typeof data.authority !== 'object') return false;
    const expected = ['signal', 'probability', 'ranking', 'sizing', 'trading', 'auto_exit', 'alert_escalation'];
    return Object.keys(data.authority).length === expected.length &&
      expected.every(k => data.authority[k] === false);
  }
  function statusName(status, t) {
    return Object.prototype.hasOwnProperty.call(t.stateLabels, status) ? t.stateLabels[status] : t.unknown;
  }
  function evidenceName(status, t) {
    return Object.prototype.hasOwnProperty.call(t.evidenceStatus, status) ? t.evidenceStatus[status] : t.unknown;
  }
  function prettyKey(key) { return String(key).replace(/[_-]/g, ' '); }
  function conditionText(item, rows, t) {
    const itemRow = rows.get(item.observation);
    const value = itemRow && itemRow.status === 'current'
      ? String(itemRow.value) + ' ' + itemRow.unit + ' · ' : '';
    const result = item.met === true ? t.met : item.met === false ? t.unmet : t.unknown;
    return prettyKey(item.observation) + ': ' + value + t.op[item.op] + ' ' +
      String(item.threshold) + ' ' + item.unit + ' — ' + result +
      (item.reason === 'current' ? '' : ' (' + evidenceName(item.reason, t) + ')');
  }
  function evidenceRow(item, rows, t) {
    const source = rows.get(item.key);
    const row = elem('li', 'mnv-evidence-row');
    add(row, elem('span', 'mnv-evidence-key', prettyKey(item.key)),
      elem('span', source && item.status === 'current' && source.status === 'current'
        ? 'mnv-evidence-current' : 'mnv-evidence-muted',
      evidenceName(item.status, t) + (source && source.value !== null &&
        source.status === 'current' && item.status === 'current'
        ? ' · ' + source.value + ' ' + source.unit : '')));
    return row;
  }
  function createView(mount, options) {
    if (!mount || typeof mount.replaceChildren !== 'function' || !mount.ownerDocument ||
        (options !== undefined && (!options || typeof options !== 'object' || Array.isArray(options)))) {
      throw new TypeError('Navigator view needs a mounted DOM element');
    }
    options = options || {};
    if (options.language !== undefined && !['en','zh'].includes(options.language)) throw new TypeError('unsupported language');
    if (options.theme !== undefined && !['dark','light'].includes(options.theme)) throw new TypeError('unsupported theme');
    const subjectLabel = options.subjectLabel === undefined ? null : options.subjectLabel;
    if (subjectLabel !== null && (typeof subjectLabel !== 'string' ||
        subjectLabel.length < 1 || subjectLabel.length > 96 ||
        !subjectLabel.trim() || /[\u0000-\u001f\u007f]/.test(subjectLabel))) {
      throw new TypeError('subject label must be a bounded nonempty display string');
    }
    // Fixed for this view/client pair. On instrument changes the host must
    // dispose/recreate both, and the validated controller must bind the
    // underlying owner packet to the exact requested subject.
    let language = options.language || 'en', theme = options.theme || 'dark';
    let currentState = {status:'empty',data:null}, destroyed = false;
    function renderContent(openKeys) {
      if (destroyed) return;
      const t = TEXT[language];
      const data = currentState.data;
      const status = currentState.status;
      // This defensive boundary protects callers that did not use the validated
      // client. A malformed/authority-bearing payload is never displayed.
      const admitted = status === 'recorded_context' && noAuthority(data) &&
        HORIZON.includes(data.horizon) && Array.isArray(data.observations) &&
        Array.isArray(data.scenarios) && data.scenarios.length <= 12 &&
        data.observations.length <= 128 && data.canonical_market &&
        Array.isArray(data.scenarios) && data.scenarios.every(s => STATUSES.includes(s.status) &&
          s.probability === null && Array.isArray(s.triggers) && Array.isArray(s.invalidations) &&
          Array.isArray(s.support) && Array.isArray(s.counterevidence));
      const effective = status === 'recorded_context' && !admitted ? 'invalid_response' : status;
      const main = elem('section', 'mnv', null, {'data-theme':theme,'lang':language,'aria-label':t.app});
      const shell = elem('div', 'mnv-shell');
      const heading = elem('header','mnv-toolbar');
      const brand = elem('div','mnv-brand');
      add(brand, elem('span','mnv-mark','M.'), add(elem('div'),
        elem('strong','mnv-brand-name',t.app), elem('span','mnv-eyebrow',t.subtitle)));
      const controls = elem('div','mnv-controls');
      const languageButton = elem('button','mnv-control',language==='en'?'中文':'English',
        {'type':'button','aria-label':t.toggleLanguage});
      const themeButton = elem('button','mnv-control',theme==='dark'?t.light:t.dark,
        {'type':'button','aria-label':t.toggleTheme});
      languageButton.addEventListener('click',()=>setLanguage(language==='en'?'zh':'en',true));
      themeButton.addEventListener('click',()=>setTheme(theme==='dark'?'light':'dark',true));
      add(controls, languageButton, themeButton);add(heading,brand,controls);
      add(shell,heading);
      const body = elem('div','mnv-body');
      if (effective !== 'recorded_context') {
        const statusArea = elem('div','mnv-empty',null,{'role':'status','aria-live':'polite'});
        add(statusArea,elem('span','mnv-kicker',t.context),
          elem('h1','mnv-empty-title',effective==='empty' ? t.waiting : (t[effective] || t.invalid_response)),
          elem('p','mnv-muted',t.empty),
          elem('p','mnv-disclaimer',t.noLive));
        add(body,statusArea);
      } else {
        const rows = new Map(data.observations.map(row=>[row.key,row]));
        const ready = data.observations.filter(row=>row.status==='current').length;
        const canopy = elem('div','mnv-intro');
        const contextLabel = (subjectLabel ? t.instrument+': '+subjectLabel+' · ' : '')+
          t.horizons[data.horizon]+' · '+t.asOf+' '+data.as_of;
        add(canopy,elem('span','mnv-kicker',t.context),
          elem('h1','mnv-title',t.intro),
          elem('div','mnv-meta',contextLabel),
          elem('div','mnv-disclaimer',t.noLive));
        add(body,canopy);
        const top = elem('div','mnv-top-grid');
        const canonical = data.canonical_market;
        const marketIsCurrent = canonical.status==='current' && VERDICTS.includes(canonical.verdict);
        const label = marketIsCurrent ? ({RISK_ON:t.riskOn,MIXED:t.mixed,RISK_OFF:t.riskOff})[canonical.verdict] : t.notVerified;
        const stateCard = elem('section','mnv-state-card',null,{'aria-label':t.canonical});
        add(stateCard,elem('span','mnv-kicker',t.canonical),
          elem('p','mnv-regime'+(marketIsCurrent?' mnv-regime-'+canonical.verdict.toLowerCase():''),label),
          elem('p','mnv-muted',marketIsCurrent ? (canonical.asof+' · '+t.observed+': '+canonical.available_at) : t.abstain));
        const coverageCard = elem('section','mnv-state-card',null,{'aria-label':t.eligibility});
        const metrics = elem('div','mnv-metrics');
        add(metrics,add(elem('div'),elem('strong',null,String(ready)),elem('span',null,t.current)),
          add(elem('div'),elem('strong',null,String(data.observations.length-ready)),elem('span',null,t.notCurrent)));
        add(coverageCard,elem('span','mnv-kicker',t.eligibility),metrics,
          elem('p','mnv-muted',t.caveat));
        add(top,stateCard,coverageCard);add(body,top);
        const pathArea = elem('section','mnv-paths',null,{'aria-label':t.paths});
        const pathsHeader = elem('div','mnv-section-header');
        add(pathsHeader,sectionTitle(t.paths),elem('span','mnv-muted',t.noOdds));
        add(pathArea,pathsHeader);
        if (!data.scenarios.length) add(pathArea,elem('p','mnv-muted',t.noPaths));
        else {
          const grid = elem('div','mnv-path-grid');
          data.scenarios.forEach((scenario,index)=>{
            const card = elem('article','mnv-path',null,{'data-scenario-key':scenario.key});
            const topline = elem('div','mnv-path-top');
            add(topline,elem('span','mnv-path-index',String(index+1).padStart(2,'0')),
              elem('span','mnv-path-state',statusName(scenario.status,t)));
            add(card,topline,elem('h3','mnv-path-title',prettyKey(scenario.key)),
              elem('p','mnv-muted',t.expected));
            const details = elem('details','mnv-path-details');
            if (openKeys && openKeys.has(scenario.key)) details.open = true;
            const summary = elem('summary','mnv-summary',t.evidence);
            add(details,summary);
            [[t.trigger,scenario.triggers],[t.invalidation,scenario.invalidations]].forEach(([label,items])=>{
              const group = elem('div','mnv-condition-group');
              add(group,elem('h4','mnv-kicker',label));
              const list = elem('ul','mnv-condition-list');
              items.forEach(item=>add(list,elem('li',null,conditionText(item,rows,t))));
              add(group,list);add(details,group);
            });
            [[t.supports,scenario.support],[t.challenges,scenario.counterevidence]].forEach(([label,items])=>{
              const group = elem('div','mnv-condition-group');
              add(group,elem('h4','mnv-kicker',label));
              const list = elem('ul','mnv-evidence-list');
              if (!items.length) add(list,elem('li','mnv-muted',t.noEvidence));
              else items.forEach(item=>add(list,evidenceRow(item,rows,t)));
              add(group,list);add(details,group);
            });
            const foot = elem('div','mnv-rule-foot');
            add(foot,elem('span',null,t.defined+': '+scenario.definition_available_at),
              elem('span',null,t.deadline+': '+scenario.deadline));
            add(details,foot,elem('p','mnv-rule-notice',t.formula));
            add(card,details);add(grid,card);
          });
          add(pathArea,grid);
        }
        add(body,pathArea,elem('footer','mnv-footer',t.noLive+' · '+t.caveat));
      }
      add(shell,body);add(main,shell);mount.replaceChildren(main);
    }
    function render(state) {
      if (destroyed) return;
      if (!state || typeof state !== 'object' || !STATE.includes(state.status) ||
          (state.status !== 'recorded_context' && state.data !== null)) {
        currentState={status:'invalid_response',data:null};
      } else currentState=state;
      renderContent();
    }
    function change(kind,value,fromControl) {
      if (destroyed) return;
      if (kind==='language') {if (!['en','zh'].includes(value)) throw new TypeError('unsupported language');language=value;}
      else {if (!['dark','light'].includes(value)) throw new TypeError('unsupported theme');theme=value;}
      // Preserve the open research details when switching only presentation.
      // A new data read or error does NOT inherit a previous scenario's open state.
      const openKeys = new Set(Array.from(mount.querySelectorAll('.mnv-path-details[open]'),
        item => item.parentElement.getAttribute('data-scenario-key')));
      renderContent(openKeys);
      if (fromControl) {
        const button=mount.querySelector(kind==='language'?'[aria-label="Switch to Chinese"], [aria-label="Switch to English"]':'button[aria-label="Toggle light and dark theme"],button[aria-label="切换深色／浅色"]');
        if (button) button.focus();
      }
    }
    function setLanguage(value,fromControl) {change('language',value,Boolean(fromControl));}
    function setTheme(value,fromControl) {change('theme',value,Boolean(fromControl));}
    render(currentState);
    return Object.freeze({render:render,setLanguage:value=>setLanguage(value,false),
      setTheme:value=>setTheme(value,false),dispose:function(){destroyed=true;mount.replaceChildren();}});
  }
  return Object.freeze({createView:createView});
}));
