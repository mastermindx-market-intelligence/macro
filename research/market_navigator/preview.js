/* Inert interactive design study. No network, account writes, signals or alerts. */
(() => {
  'use strict';
  const root = document.documentElement;
  const copies = Array.from(document.querySelectorAll('[data-copy]'));
  const en = Object.fromEntries(copies.map(node => [node.dataset.copy, node.textContent]));
  const zh = {
    brand:'市场导航', study:'产品设计研究', instrument:'标普500 ETF', sample:'示例 · 非实时',
    today:'日内', week:'本周', month:'下个月', question:'当前图景', mixed:'证据仍有分歧',
    vol:'波动正在缓和', waiting:'等待确认', stanceLabel:'下一步', stance:'观察，不追涨。',
    stanceBody:'先看价格能否站稳关键区域，再判断反弹是否形成新趋势。', why:'为什么仍要等待？ ↗',
    notSignal:'这是条件分析示例，不是买卖信号。', changed:'哪些发生了变化',
    changeText:'参与上涨的股票增多。价格来到阻力区。更大周期的趋势仍未确定。', compare:'对比前后观点 ↗',
    comparison:'保留原始判断', before:'之前的示例', priorText:'价格在关键区域下方逐步修复。',
    now:'当前的示例', currentText:'关键区域正在接受检验，但尚未确认站稳。',
    comparisonNote:'仅为交互示例。没有创建或修改账户中的已保存观点。', location:'定位，不是预测',
    mapTitle:'关键判断区域', samplePrice:'示例价格', upper:'上方参考', decision:'关键区域',
    acceptance:'在此站稳，会增强修复情景', weAre:'示例位置', pivot:'附近枢轴', lower:'下方参考',
    mapNote:'这些区域帮助观察，不保证构成支撑或阻力。', inspect:'查看依据 ↗', balance:'支持与反证',
    supports:'支持修复的证据', breadth:'市场参与度正在改善。', breadthBody:'更多成分股回到中期均线上方。',
    challenges:'对修复的质疑', resistance:'突破尚未得到确认。', resistanceBody:'上方压力与混合动量，仍可能使反弹受挫。',
    changeMind:'什么会改变这一判断？ ↗', pathsLabel:'准备应对，而非猜测', pathsTitle:'三种可能路径',
    noOdds:'暂无经校准的概率', path1:'修复延续', path1Body:'价格站稳关键区域，同时保持较广的市场参与。',
    watchFor:'需要观察', path1Trigger:'完成站稳，而不只是短暂触及。', invalid:'削弱该情景的条件',
    path1Invalid:'重新跌破附近枢轴。', unconfirmed:'尚未确认', path2:'修复受挫',
    path2Body:'价格在关键区域遇阻、失守枢轴，同时参与度转弱。', path2Trigger:'价格与市场参与度同步转弱。',
    path2Invalid:'持续收复上方区域。', path3:'区间延续', path3Body:'价格在参考区域之间波动，未出现明确延续。',
    path3Trigger:'反复测试，但未能站稳。', path3Invalid:'在区间之外形成合格突破。', waitChoice:'等待仍是合理选择',
    nextWatch:'接下来观察', nextQuestion:'价格能否守住枢轴？', nextBody:'观察市场反应，而非依赖单一指标。',
    save:'连接账户后保存', footer:'仅为设计研究 · 尚未写入 Paper · 无实时数据、账户保存、警报或交易。',
    detailLabel:'理解判断条件', dialogTitle:'为什么仍要等待',
    dialogLead:'示例同时包含修复证据和谨慎理由。两条方向路径均未确认。',
    clockTitle:'同一时点，同一周期', clockBody:'日线收盘与盘后报价，不能悄悄共用一个“当前”时间戳。',
    optionsTitle:'持仓分析仍是估计', optionsBody:'伽马可能放大任一方向。到期范围和持仓假设必须明确。',
    triggerTitle:'触发条件不等于交易', triggerBody:'某个条件成立，并不能证明预测有效、入场质量合适或仓位合理。',
    unknownTitle:'未知就保持未知', unknownBody:'缺失或过时的数据，以及未经验证的概率，不能被自信的措辞替代。',
    dialogFoot:'本研究使用示例描述与未经核实的价格区域，并非实时市场。'
  };
  let language = 'en';
  let horizon = 'swing';
  let dataState = 'sample';
  const dialog = document.getElementById('evidence-dialog');
  const title = document.getElementById('hero-title');
  const description = document.getElementById('hero-description');
  const message = document.getElementById('state-message');
  const hiddenForMissing = ['.decision-layout', '.paths', '.change-strip', '.hero-chips', '.watch-band'];
  const content = {
    en:{swing:['Recovery meets','resistance.','More stocks are participating. The next test is whether price can hold higher.'],
        intraday:['Two paths.','No rush.','The decision area matters more than a single indicator. Watch for a completed hold or rejection.'],
        position:['Longer view','unavailable.','This study has no qualified monthly forecast. A one-day volatility reading cannot supply one.'],
        stale:['Snapshot needs','a refresh.','Old observations cannot support a current conclusion. The last view is not being presented as fresh.'],
        missing:['Evidence is','unavailable.','Required observations are missing. The system does not replace them with a neutral value or a confident story.']},
    zh:{swing:['修复正在遇到','阻力。','参与上涨的股票增多。接下来要看，价格能否在更高区域站稳。'],
        intraday:['两种路径。','不必急于行动。','关键区域比单个指标更重要。等待完整的站稳或回落。'],
        position:['长期视角','暂不可用。','本研究尚无合格的月度预测。不能用一日波动指标来代替。'],
        stale:['快照需要','更新。','过去的观察不能支撑当前结论。系统不会把旧观点重新标记为最新。'],
        missing:['必要证据','暂不可用。','缺失的观察不会被中性数值或自信的叙述替代。']}
  };
  function render() {
    root.lang = language;
    root.dataset.lang = language;
    const dict = language === 'zh' ? zh : en;
    copies.forEach(node => { node.textContent = dict[node.dataset.copy]; });
    const state = dataState === 'sample' ? horizon : dataState;
    const lines = content[language][state];
    title.replaceChildren(document.createTextNode(lines[0]), document.createElement('br'), document.createTextNode(lines[1]));
    description.textContent = lines[2];
    const unavailable = horizon === 'position' || dataState !== 'sample';
    hiddenForMissing.forEach(selector => { document.querySelector(selector).hidden = unavailable; });
    if (unavailable) {
      document.getElementById('change-detail').hidden = true;
      document.getElementById('change-toggle').setAttribute('aria-expanded','false');
      document.getElementById('stance-title').textContent = language === 'zh' ? '等待合格证据。' : 'Wait for qualified evidence.';
    }
    message.hidden = !unavailable;
    message.textContent = language === 'zh' ? '此状态不提供当前判断或行动信号。已有示例不代表实时数据。' : 'No current conclusion or action signal is available in this state. This study is not a live feed.';
    document.getElementById('theme').textContent = language === 'zh' ? (root.dataset.theme === 'dark' ? '浅色模式' : '深色模式') : (root.dataset.theme === 'dark' ? 'Light mode' : 'Dark mode');
    document.getElementById('data-state').textContent = language === 'zh' ? ({sample:'测试过时数据',stale:'测试数据缺失',missing:'返回示例'})[dataState] : ({sample:'Test stale data',stale:'Test missing data',missing:'Return to example'})[dataState];
    document.querySelectorAll('[data-horizon]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.horizon === horizon)));
  }
  document.getElementById('language').addEventListener('click', () => {language = language === 'en' ? 'zh' : 'en'; render();});
  document.getElementById('theme').addEventListener('click', () => {root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark'; render();});
  document.getElementById('data-state').addEventListener('click', () => {dataState = ({sample:'stale',stale:'missing',missing:'sample'})[dataState];render();});
  document.querySelectorAll('[data-horizon]').forEach(button => button.addEventListener('click', () => {horizon = button.dataset.horizon; render();}));
  ['why-wait','evidence-open','counter-open'].forEach(id => document.getElementById(id).addEventListener('click', () => dialog.showModal()));
  document.getElementById('dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {if(event.target === dialog){const r = dialog.getBoundingClientRect();if(event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom)dialog.close();}});
  document.getElementById('change-toggle').addEventListener('click', () => {const detail = document.getElementById('change-detail');detail.hidden = !detail.hidden;document.getElementById('change-toggle').setAttribute('aria-expanded',String(!detail.hidden));});
  if (matchMedia('(max-width:700px)').matches) document.querySelectorAll('.path').forEach((node,index) => {node.open = index === 0;});
  if (copies.some(node => !(node.dataset.copy in zh))) throw new Error('Missing study translation');
  render();
})();
