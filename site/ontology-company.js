/* Macro's private company inspector. Nothing is loaded until the reader asks.
 * Owner responses live only in this view; never in URLs, telemetry or storage. */
import * as decoder from './ontology-company-contract.js?v=9a32b97f';
import { createCompanyController } from './ontology-company-controller.js?v=e8469cc9';

function words(en, zh) {
  const fragment = document.createDocumentFragment();
  for (const [language, value] of [['en', en], ['zh', zh]]) {
    const span = document.createElement('span');
    span.className = 'l-' + language;
    span.textContent = value;
    fragment.append(span);
  }
  return fragment;
}

function element(tag, className, en, zh) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (en !== undefined) node.append(words(en, zh));
  return node;
}

function field(list, en, zh, value) {
  const row = element('div', 'ox-company-field');
  row.append(element('dt', '', en, zh));
  const description = element('dd');
  if (typeof value === 'string') description.textContent = value;
  else description.append(words('Not provided', '未提供'));
  row.append(description);
  list.append(row);
}

export function mountCompanyResearch(root) {
  if (!root) return null;
  const form = root.querySelector('form');
  const input = root.querySelector('input');
  const output = root.querySelector('[data-company-result]');
  const clearButton = root.querySelector('[data-company-clear]');
  let disposed = false;
  let subscription = null;
  let client = null;
  let controller;
  let selectedFrom = null;
  let selectedIdentity = null;
  function publishIdentity() {
    root.dispatchEvent(new CustomEvent('ontology-company-identity', { detail: selectedIdentity }));
  }
  root.addEventListener('ontology-identity-ready', publishIdentity);
  // The module can finish loading after a canonical sign-out. A missed event
  // must never let an SDK's older cached session authorize a private read.
  let canonicalKnown = true;
  let canonicalOwner = null;
  try {
    const user = window.MDXAuth && typeof window.MDXAuth.user === 'function' && window.MDXAuth.user();
    canonicalOwner = user && typeof user.id === 'string' ? user.id : null;
  } catch (_) { /* unknown canonical identity stays signed out */ }
  function canonicalAuth(event) {
    canonicalKnown = true;
    const user = event.detail && event.detail.user;
    canonicalOwner = user && typeof user.id === 'string' ? user.id : null;
    selectedFrom = null;
    if (controller) controller.clear();
    input.value = '';
  }
  window.addEventListener('mdx-auth', canonicalAuth);
  // The incumbent Macro authentication client owns session refresh and sign-in.
  // Failure to bind its change events means this view cannot retain private data.
  const authentication = Promise.resolve().then(async () => {
    if (!window.MDXAuth || typeof window.MDXAuth.client !== 'function') throw new Error('AUTH_UNAVAILABLE');
    const current = await window.MDXAuth.client();
    if (disposed || !current || !current.auth
        || typeof current.auth.onAuthStateChange !== 'function') throw new Error('AUTH_UNAVAILABLE');
    const result = current.auth.onAuthStateChange(() => {
      selectedFrom = null;
      if (controller) controller.clear();
      input.value = '';
    });
    subscription = result && result.data && result.data.subscription;
    if (!subscription || typeof subscription.unsubscribe !== 'function') throw new Error('AUTH_UNAVAILABLE');
    client = current;
    return current;
  });
  // Attach a rejection handler immediately; a failed binding stays unusable.
  void authentication.catch(() => {});

  async function getSession() {
    const current = await authentication;
    if (disposed || !current || current !== client) return null;
    const result = await current.auth.getSession();
    if (disposed || !result || result.error) return null;
    const session = result.data && result.data.session || null;
    // A restored page may have missed an auth event. Re-read the canonical
    // owner after the awaited SDK call; cached SDK state is not authority.
    let user = null;
    try { user = window.MDXAuth && typeof window.MDXAuth.user === 'function' && window.MDXAuth.user(); }
    catch (_) { return null; }
    if (!user || typeof user.id !== 'string' || !user.id || !session || !session.user
        || user.id !== session.user.id || (canonicalKnown && canonicalOwner !== user.id)) return null;
    return session;
  }

  function render(state) {
    if (disposed) return;
    selectedIdentity = state.context && state.selection ? {
      identity_kind: 'security', identity_id: state.context.security_id,
      symbol: state.context.query.symbol, owner_id: canonicalOwner,
    } : null;
    publishIdentity();
    // Replacing the entire result drops the previous issuer, fact and open details
    // together; no stale fact survives a query, identity or generation change.
    output.replaceChildren();
    output.dataset.state = state.status;
    output.setAttribute('aria-busy', state.status === 'loading' ? 'true' : 'false');
    const messages = {
      idle: ['Choose a company to inspect its source disclosures.', '选择一家公司，查看其来源披露。'],
      loading: ['Reading the company’s current disclosure selection…', '正在读取该公司的当前披露列表…'],
      signed_out: ['Sign in to inspect private company disclosures.', '登录后查看私有公司披露。'],
      forbidden: ['This account does not include private company disclosures.', '此账户未包含私有公司披露权限。'],
      unavailable: ['Company disclosures are unavailable for this reading.', '本次公司披露读数暂不可用。'],
      empty: ['No qualified disclosures are available in this selection.', '本次列表中没有可读取的合格披露。'],
    };
    if (messages[state.status]) {
      const message = element('p', 'ox-note', ...messages[state.status]);
      message.setAttribute('role', 'status');
      output.append(message);
    }
    if (state.status === 'signed_out') {
      const link = element('a', 'ox-cta secondary', 'Sign in', '登录');
      link.href = '/?signin=1&ret=%2Fontology.html';
      output.append(link);
    }
    if (!state.context || !state.selection) return;
    if (selectedFrom) {
      const origin = element('p', 'ox-note');
      origin.append(words('Selected from the WTI exposure membership dated ', '选自以下日期的 WTI 敞口成员名单：'));
      origin.append(document.createTextNode(selectedFrom.asof));
      origin.append(words('. This is owner screen membership, not an estimated company impact or a current causal claim.', '。这是来源筛选结果，并非公司影响估计，也不确立当前因果关系。'));
      output.append(origin);
    }
    const context = state.context;
    const selection = state.selection;
    const identity = element('div', 'ox-company-identity');
    const name = element('strong');
    name.textContent = context.query.symbol;
    identity.append(name, element('span', 'ox-company-current', 'Current issuer identity', '当前发行人身份'));
    output.append(identity);

    if (state.status !== 'empty') {
      const choices = element('div', 'ox-company-choices');
      choices.setAttribute('role', 'group');
      choices.setAttribute('aria-label', 'Source disclosures / 来源披露');
      selection.selections.forEach((entry, index) => {
        const supplier = entry.kind === 'disclosed_supplier';
        const button = element('button', 'ox-action',
          supplier ? 'Read disclosed supplier' : 'Read planned integration', supplier ? '读取披露的供应商' : '读取计划整合');
        button.type = 'button';
        button.setAttribute('aria-label', (supplier ? 'Disclosed supplier ' : 'Planned integration ') + (index + 1) + (supplier ? ' / 披露的供应商 ' : ' / 计划整合 ') + (index + 1));
        button.setAttribute('aria-pressed', state.selectedFactId === entry.fact_id ? 'true' : 'false');
        button.addEventListener('click', () => { void controller.selectFact(entry.fact_id); });
        choices.append(button);
      });
      output.append(choices);
    }

    if (state.fact) {
      const value = state.fact;
      const card = element('article', 'ox-card ox-company-fact');
      const supplier = value.schema === decoder.PRIVATE_SUPPLIER_SCHEMA;
      const fields = element('dl', 'ox-company-fields');
      if (supplier) {
        const source = value.source_timing.sec_source, binding = value.supplier_binding;
        card.append(element('h3', '', 'A disclosed supplier role', '一项披露的供应商角色'));
        card.append(element('p', 'ox-note',
          'The selected filing reports that this company uses the named supplier for the stated product. It does not establish the relationship today, deliveries, quantities, economic sensitivity or a second-order effect.',
          '所选文件披露该公司就所列产品使用该供应商。这不确立当前关系、交付、数量、经济敏感度或二阶影响。'));
        field(fields, 'Reporting customer', '披露方客户', context.query.symbol);
        field(fields, 'Supplier issuer', '供应商发行人', value.fact.object_id);
        field(fields, 'Product scope', '产品范围', value.fact.product);
        field(fields, 'Filing date', '披露日期', value.source_timing.published_date);
        field(fields, 'SEC acceptance', 'SEC 接收时刻', source.accepted_at);
        field(fields, 'Retained source retrieval', '留存来源读取时刻', source.retrieved_at);
        field(fields, 'Identity observed for adoption', '采纳所用身份观测', binding.identity_observed_at);
        field(fields, 'Fact adoption', '事实采纳时刻', binding.adopted_at);
        card.append(fields);
        const citation = element('a', 'ox-action', 'Read the original SEC filing', '阅读 SEC 原始披露');
        citation.href = source.archive_url; citation.target = '_blank'; citation.rel = 'noopener noreferrer';
        card.append(citation, element('p', 'ox-note',
          'Source: public issuer filing on SEC.gov. Current identity is used; filing acceptance does not establish historical availability in this system. No supplier amount or economic weight is assigned.',
          '来源：SEC.gov 上的发行人公开披露。此处使用当前身份；披露接收时刻不代表本系统的历史可用时刻。未赋予供应量或经济权重。'));
      } else {
        card.append(element('h3', '', 'An announced plan', '一项已披露的计划'));
        card.append(element('p', 'ox-note',
          'This is a planned integration. Delivery, revenue and economic exposure are not established by this disclosure.',
          '这是一项计划中的整合。该披露并不证明已交付、产生收入或构成经济敞口。'));
        field(fields, 'Product', '产品', value.fact.product);
        field(fields, 'Platform', '平台', value.fact.platform);
        field(fields, 'Announcement date', '公告日期', value.source_timing.published_date);
        field(fields, 'Announcement instant', '公告时刻', value.source_timing.published_at);
        field(fields, 'Source observation', '来源观测时刻', value.source_timing.known_at);
        card.append(fields, element('p', 'ox-note',
          'Source dates retain their original precision. The observation timestamp is separate from the announcement date and does not establish that the plan is still current.',
          '来源日期保留原始精度。观测时间与公告日期分列，也不证明该计划至今仍然有效。'));
      }
      const researchButton = element('button', 'ox-action', 'Explore second-order research', '探索二阶研究');
      researchButton.type = 'button';
      researchButton.addEventListener('click', () => { void controller.selectResearch(value.fact.fact_id); });
      card.append(researchButton);
      output.append(card);
    } else if (state.status === 'ready') {
      output.append(element('p', 'ox-note',
        'Select a disclosure to read its source-qualified fact. Selection metadata alone does not establish the fact.',
        '选择一项披露以读取经来源核验的事实。仅凭列表元数据无法确立事实。'));
    }
    if (state.research) {
      const result = state.research;
      const research = element('article', 'ox-card ox-company-research');
      research.setAttribute('data-research-status', result.status);
      if (result.status === 'context_only') {
        research.append(element('h3', '', 'Context without a transmission claim', '仅有背景，尚无传导论断'),
          element('p', 'ox-note',
            'This planned integration supplies context only. It does not establish a supplier role or an operating transmission, so no second-order hypothesis is constructed from it.',
            '这项计划中的整合仅提供背景，并未确立供应商角色或经营传导，因此不会据此构建二阶假设。'));
      } else {
        const c = result.candidate, o = c.observed;
        research.append(element('h3', '', 'A conditional supplier hypothesis', '一项有条件的供应商假设'),
          element('p', 'ox-note', 'Research candidate · untested · no trade authority', '研究候选 · 未经检验 · 无交易授权'));
        research.append(element('h4', '', 'Reported event', '已报告的事件'),
          element('p', '',
            'NVIDIA reported diminished demand for H20 products in its first fiscal quarter of 2026. The FY2026 filing also identifies TSMC as a wafer foundry supplier.',
            '英伟达报告其 2026 财年第一季度 H20 产品需求减弱。同一份 2026 财年披露也将台积电列为晶圆代工供应商。'),
          element('h4', '', 'Proposed transmission', '拟议的传导路径'),
          element('p', '',
            'If that demand loss reduces applicable wafer procurement from TSMC, TSMC operating volume could decline relative to a comparable baseline. Whether H20 affected TSMC procurement or volume is not established by these disclosures.',
            '若该需求下降减少了适用于台积电的晶圆采购，其经营量可能低于可比基准。这些披露尚未确立 H20 对台积电采购或经营量的实际影响。'),
          element('p', 'ox-note',
            'Both observations come from one filing, so they are not independent confirmations. No allocation, effect size, confidence or impact lag has been estimated.',
            '两项观察均来自同一份披露，不能算作独立确认。尚未估计分配量、影响大小、置信度或影响时滞。'));
        research.append(element('h4', '', 'What would test it', '如何检验'));
        const tests = element('ul');
        tests.append(element('li', '',
          'First establish that the demand change reached this supplier through an applicable relationship.',
          '先核实需求变化确实通过适用关系传至该供应商。'),
          element('li', '',
            'Before testing, fix the metric, comparable baseline, event and outcome windows, lag, rejection rule and uncertainty treatment.',
            '检验前固定指标、可比基准、事件与结果窗口、时滞、拒绝规则及不确定性处理。'),
          element('li', '',
            'If the antecedent occurred but eligible volume observations fail the preregistered decline test, reject that scoped claim. Missing evidence leaves it untested.',
            '若前提发生但合格经营量观察未通过预注册的下降检验，则拒绝该范围内的论断。缺少证据意味着仍未检验。'));
        research.append(tests, element('h4', '', 'Alternative explanations', '替代解释'),
          element('p', '',
            'A shared industry driver or coincident timing could explain the association without transmission between these businesses.',
            '共同的行业驱动因素或时间上的巧合，也可能解释该关联，而无需两家公司之间存在传导。'),
          element('p', 'ox-note',
            'Context-only path refused: appearing in the same document is insufficient to construct a supplier transmission. The qualified role is required.',
            '已拒绝仅凭背景的路径：出现在同一文件中不足以构建供应商传导，必须具备合格角色证据。'));
        const evidence = element('details', 'ox-detail');
        evidence.append(element('summary', '', 'Research evidence and test contract', '研究证据与检验约定'));
        const fields = element('dl', 'ox-company-fields ox-company-references');
        field(fields, 'Target security', '目标证券', c.target.security_id);
        field(fields, 'Reported occurrence period', '报告中的发生期间', 'FY' + o.occurrence_period.year + ' Q' + o.occurrence_period.quarter);
        field(fields, 'SEC reporting acceptance', 'SEC 报告接收时刻', o.reporting_at);
        field(fields, 'Source retrieved', '来源读取时刻', o.retrieved_at);
        field(fields, 'Reported event adopted', '报告事件采纳时刻', o.adopted_at);
        field(fields, 'Source reverified', '来源复核时刻', o.verified_at);
        field(fields, 'Hypothesis compiled', '假设构建时刻', c.compiled_at);
        field(fields, 'Review by (not impact lag)', '复核日期（并非影响时滞）', c.review_by);
        field(fields, 'Native research record', '原生研究记录', c.record_id);
        field(fields, 'Native record digest', '原生记录摘要', c.content_sha256);
        field(fields, 'Reported event reference', '报告事件引用', o.event_fact_id);
        field(fields, 'Source span digest', '来源片段摘要', o.span_sha256);
        evidence.append(fields, element('p', 'ox-note',
          'Current identity is used. Filing acceptance is a reporting clock; it does not date the economic occurrence or historical availability in this system. No empirical test has been registered or run for this record.',
          '使用的是当前身份。披露接收时刻是报告时钟，不是经济事件的发生时刻，也不代表本系统的历史可用时刻。本记录尚未注册或执行实证检验。'));
        const nativeText = element('p'); nativeText.textContent = c.mechanism.hypothesis_text;
        evidence.append(element('h4', '', 'Original hypothesis wording (English)', '假设原文（英文）'), nativeText); research.append(evidence);
      }
      output.append(research);
    }
    const detail = element('details', 'ox-detail');
    detail.append(element('summary', '', 'Identity and source references', '身份与来源引用'));
    const refs = element('dl', 'ox-company-fields ox-company-references');
    field(refs, 'Security', '证券', context.security_id);
    field(refs, 'Issuer', '发行人', context.issuer_binding.issuer_id);
    field(refs, 'Identity evidence date', '身份凭证日期', context.identity_receipt.evidence_snapshot);
    field(refs, 'Disclosure generation', '披露版本', selection.generation);
    if (state.fact) {
      field(refs, 'Fact reference', '事实引用', state.fact.reference.sha256);
      field(refs, 'Edition reference', '版本引用', state.fact.edition.sha256);
      if (state.fact.schema === decoder.PRIVATE_SUPPLIER_SCHEMA) {
        const source = state.fact.source_timing.sec_source;
        field(refs, 'Filing accession', '披露编号', source.accession);
        field(refs, 'Source recorded', '来源入库时刻', source.recorded_at);
        field(refs, 'Pinned snapshot', '固定快照时刻', source.snapshot_at);
      }
    }
    detail.append(refs);
    output.append(detail);
  }

  controller = createCompanyController({
    fetchImpl: (...args) => fetch(...args), getSession, onState: render, decoder,
  });
  function submit(event) {
    event.preventDefault();
    // Input is session-only. The form has no named controls and never navigates.
    selectedFrom = null;
    void controller.lookup(input.value);
  }
  function clear() { selectedFrom = null; controller.clear(); input.value = ''; }
  function edited() { selectedFrom = null; controller.clear(); }
  function selectExposure(event) {
    const choice = event.detail;
    if (disposed || !choice || !decoder.isPrivateCompanySymbol(choice.symbol)
        || typeof choice.security_id !== 'string' || !/^SEC:[A-Za-z0-9:._/-]{1,120}$/.test(choice.security_id)
        || typeof choice.asof !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(choice.asof)
        || typeof choice.manifest_hash !== 'string' || !/^sha256:[a-f0-9]{64}$/.test(choice.manifest_hash)) return;
    clear();
    selectedFrom = { asof: choice.asof, manifest_hash: choice.manifest_hash };
    input.value = choice.symbol;
    input.focus({ preventScroll: true });
    root.scrollIntoView({ block: 'start', behavior: 'auto' });
    void controller.lookup(choice.symbol, choice.security_id);
  }
  root.addEventListener('ontology-select-company', selectExposure);
  root.addEventListener('ontology-source-changed', clear);
  root.dataset.companyReady = 'true';
  root.dispatchEvent(new CustomEvent('ontology-company-ready'));

  function hidden() { if (document.visibilityState === 'hidden') clear(); }
  function leaving() { clear(); }
  form.addEventListener('submit', submit);
  input.addEventListener('input', edited);
  clearButton.addEventListener('click', clear);
  document.addEventListener('visibilitychange', hidden);
  window.addEventListener('pagehide', leaving);
  render({ status: 'idle' });
  return {
    dispose() {
      controller.dispose();
      output.replaceChildren();
      disposed = true;
      client = null;
      if (subscription) subscription.unsubscribe();
      subscription = null;
      selectedFrom = null; selectedIdentity = null; publishIdentity();
      root.removeEventListener('ontology-identity-ready', publishIdentity);
      delete root.dataset.companyReady;
      root.removeEventListener('ontology-select-company', selectExposure);
      root.removeEventListener('ontology-source-changed', clear);
      form.removeEventListener('submit', submit);
      input.removeEventListener('input', edited);
      window.removeEventListener('mdx-auth', canonicalAuth);
      clearButton.removeEventListener('click', clear);
      document.removeEventListener('visibilitychange', hidden);
      window.removeEventListener('pagehide', leaving);
    },
  };
}

mountCompanyResearch(document.getElementById('ox-company'));
