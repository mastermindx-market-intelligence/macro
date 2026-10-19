/* Macro's private company inspector. Nothing is loaded until the reader asks.
 * Owner responses live only in this view; never in URLs, telemetry or storage. */
import * as decoder from './ontology-company-contract.js?v=9abd91d3';
import { createCompanyController } from './ontology-company-controller.js?v=d5da2e94';

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
    if (canonicalKnown && (!canonicalOwner || !session || session.user.id !== canonicalOwner)) return null;
    return session;
  }

  function render(state) {
    if (disposed) return;
    // Replacing the entire result drops the previous issuer, fact and open details
    // together; no stale fact survives a query, identity or generation change.
    output.replaceChildren();
    output.dataset.state = state.status;
    output.setAttribute('aria-busy', state.status === 'loading' ? 'true' : 'false');
    const messages = {
      idle: ['Choose a company to inspect its source-announced plans.', '选择一家公司，查看其来源披露的计划。'],
      loading: ['Reading the company’s current disclosure selection…', '正在读取该公司的当前披露列表…'],
      signed_out: ['Sign in to inspect private company disclosures.', '登录后查看私有公司披露。'],
      forbidden: ['This account does not include private company disclosures.', '此账户未包含私有公司披露权限。'],
      unavailable: ['Company disclosures are unavailable for this reading.', '本次公司披露读数暂不可用。'],
      empty: ['No planned integrations are available for this company.', '该公司目前没有可读取的计划整合事项。'],
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
      choices.setAttribute('aria-label', 'Planned integrations / 计划整合');
      selection.selections.forEach((entry, index) => {
        const button = element('button', 'ox-action',
          'Read planned integration', '读取计划整合');
        button.type = 'button';
        button.setAttribute('aria-label', 'Planned integration ' + (index + 1) + ' / 计划整合 ' + (index + 1));
        button.setAttribute('aria-pressed', state.selectedFactId === entry.fact_id ? 'true' : 'false');
        button.addEventListener('click', () => { void controller.selectFact(entry.fact_id); });
        choices.append(button);
      });
      output.append(choices);
    }

    if (state.fact) {
      const value = state.fact;
      const card = element('article', 'ox-card ox-company-fact');
      card.append(element('h3', '', 'An announced plan', '一项已披露的计划'));
      card.append(element('p', 'ox-note',
        'This is a planned integration. Delivery, revenue and economic exposure are not established by this disclosure.',
        '这是一项计划中的整合。该披露并不证明已交付、产生收入或构成经济敞口。'));
      const fields = element('dl', 'ox-company-fields');
      field(fields, 'Product', '产品', value.fact.product);
      field(fields, 'Platform', '平台', value.fact.platform);
      field(fields, 'Announcement date', '公告日期', value.source_timing.published_date);
      field(fields, 'Announcement instant', '公告时刻', value.source_timing.published_at);
      field(fields, 'Source observation', '来源观测时刻', value.source_timing.known_at);
      card.append(fields);
      card.append(element('p', 'ox-note',
        'Source dates retain their original precision. The observation timestamp is separate from the announcement date and does not establish that the plan is still current.',
        '来源日期保留原始精度。观测时间与公告日期分列，也不证明该计划至今仍然有效。'));
      output.append(card);
    } else if (state.status === 'ready') {
      output.append(element('p', 'ox-note',
        'Select a planned integration to read its disclosure. Selection metadata alone does not establish the fact.',
        '选择一项计划整合以读取披露内容。仅凭列表元数据无法确立事实。'));
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
    void controller.lookup(input.value);
  }
  function clear() { controller.clear(); input.value = ''; }
  function edited() { controller.clear(); }
  function hidden() { if (document.visibilityState === 'hidden') clear(); }
  function leaving() { controller.clear(); }
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
