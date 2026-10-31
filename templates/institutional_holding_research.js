/* Exact, private reported-holding research. No storage, cache or owner writes. */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else if (root && root.document) {
    if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', function () { api.mount(root); }, { once: true });
    else api.mount(root);
  }
}(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  var ENDPOINT = '/api/forensics/v1/institutional/reported-holding';
  var FIELDS = ['filer_cik', 'report_period', 'accession', 'infotable_sk', 'decision_cutoff', 'generation_id'];
  var EXAMPLES = Object.freeze({
    previous: Object.freeze({ filer_cik: '0001904423', report_period: '2026-03-31', accession: '0001904423-26-000005', infotable_sk: '4611686018427387905', decision_cutoff: '2026-08-27T09:22:23.700168Z', generation_id: 'i13fgen_5af282ec5c2b29ed990f9dd8bd03e7e7ff88d54ebdb79467a3aec7b7451ce6d1' }),
    current: Object.freeze({ filer_cik: '0001904423', report_period: '2026-06-30', accession: '0001904423-26-000004', infotable_sk: '4611686018427387905', decision_cutoff: '2026-08-27T09:22:23.700168Z', generation_id: 'i13fgen_9ae95a9de85cc0ed426b09cd7db443210c8cdc5d9178aaad5859c3f8a57527cd' })
  });
  function object(value) { return !!value && typeof value === 'object' && !Array.isArray(value); }
  function day(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.slice(0, 4) === '0000') return false;
    var date = new Date(value + 'T00:00:00Z');
    return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
  }
  function normalizeSelection(raw) {
    if (!object(raw) || Object.keys(raw).some(function (key) { return FIELDS.indexOf(key) < 0; })) throw new Error('selection');
    var out = {};
    FIELDS.forEach(function (key) {
      var value = raw[key];
      if (key === 'generation_id' && (value === undefined || value === null || value === '')) return;
      if (typeof value !== 'string' || value !== value.trim()) throw new Error('selection');
      out[key] = value;
    });
    if (!/^\d{10}$/.test(out.filer_cik) || !/^\d{10}-\d{2}-\d{6}$/.test(out.accession) || !day(out.report_period)) throw new Error('selection');
    if (!/^(0|[1-9][0-9]{0,18})$/.test(out.infotable_sk) || out.infotable_sk.length === 19 && out.infotable_sk > '9223372036854775807') throw new Error('selection');
    // Keep original microseconds. Date is used only to reject invalid clocks,
    // never to reserialize a point-in-time selection with lost precision.
    var clock = /^(\d{4}-\d{2}-\d{2})T([01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|\+00:00)$/.exec(out.decision_cutoff);
    if (!clock || !day(clock[1])) throw new Error('selection');
    if (out.generation_id !== undefined && !/^i13fgen_[a-f0-9]{64}$/.test(out.generation_id)) throw new Error('selection');
    return out;
  }
  function validateResponse(payload, selection) {
    if (!object(payload) || payload.schema !== 'institutional_13f.authenticated_research_context.v1' || payload.persistence !== 'none') throw new Error('contract');
    var authority = payload.authority, context = payload.context, bindings = payload.semantic_bindings;
    if (!object(authority) || !['can_gate', 'can_open_entry', 'can_originate', 'can_rank', 'can_size'].every(function (key) { return authority[key] === false; }) || Object.keys(authority).some(function (key) { return authority[key] !== false; })) throw new Error('authority');
    if (!object(context) || context.schema !== 'institutional_13f.reported_holding_accession_context.v1' || context.owner !== 'engine.institutional_census' || context.authority !== 'descriptive_context_only' || context.financial_influence !== false || context.k3e_admissible !== false || context.state !== payload.state || ['AVAILABLE_UNQUALIFIED', 'UNAVAILABLE', 'REFUSED'].indexOf(payload.state) < 0) throw new Error('contract');
    var interpretation = context.interpretation, qualification = context.qualification;
    if (!object(interpretation) || interpretation.class !== 'DELAYED_REPORTED_HOLDING_CONTEXT' || !['is_current_ownership', 'is_flow', 'is_intent', 'is_conviction'].every(function (key) { return interpretation[key] === false; })) throw new Error('authority');
    if (!object(qualification) || qualification.state !== 'NOT_QUALIFIED' || qualification.canonical_security_id !== null || qualification.source_use !== 'UNKNOWN') throw new Error('authority');
    if (!object(bindings) || !object(bindings.security) || bindings.security.state !== 'UNRESOLVED' || bindings.security.canonical_security_id !== null || !object(bindings.economic_vehicle) || bindings.economic_vehicle.state !== 'UNRESOLVED' || !['vehicle_epoch_id', 'vehicle_class', 'manager_complex_id'].every(function (key) { return bindings.economic_vehicle[key] === null; }) || !object(bindings.strategy) || bindings.strategy.state !== 'UNRESOLVED' || bindings.strategy.decision_mode !== null) throw new Error('authority');
    if (!Array.isArray(context.refusals) || context.refusals.some(function (reason) { return typeof reason !== 'string' || !/^[A-Z0-9_]{1,120}$/.test(reason); })) throw new Error('contract');
    if (payload.state !== 'AVAILABLE_UNQUALIFIED') {
      if (context.valid !== false) throw new Error('contract');
      return payload;
    }
    var filing = context.filing, holding = context.holding, generation = context.generation, reporting = bindings.reporting_entity;
    if (context.valid !== true || !object(filing) || !object(holding) || !object(generation) || !object(reporting)) throw new Error('contract');
    if (filing.filer_cik !== selection.filer_cik || filing.report_period !== selection.report_period || filing.accession !== selection.accession || holding.infotable_sk !== selection.infotable_sk || generation.report_period !== selection.report_period || !/^i13fgen_[a-f0-9]{64}$/.test(generation.generation_id) || selection.generation_id && generation.generation_id !== selection.generation_id) throw new Error('selection mismatch');
    if (reporting.state !== 'OWNER_VERIFIED' || reporting.owner !== 'engine.institutional_census' || reporting.filer_cik !== filing.filer_cik || reporting.accession !== filing.accession || reporting.source_receipt_id !== filing.source_receipt_id) throw new Error('reporting mismatch');
    var scope = generation.validation_scope, pointer = generation.pointer;
    if (!object(scope) || scope.kind !== 'accession_bucket' || scope.whole_generation_verified !== false || !Array.isArray(scope.verified_roles) || scope.verified_roles.length !== 5 || !object(pointer)) throw new Error('scope');
    if (pointer.state === 'not_read') {
      if (generation.current_generation_id !== null || generation.superseded !== null) throw new Error('pointer');
    } else if (pointer.state !== 'verified' || typeof generation.current_generation_id !== 'string' || generation.superseded !== false) throw new Error('pointer');
    return payload;
  }
  async function readBoundedJson(response) {
    var limit = 65536, header = response.headers && response.headers.get('content-length');
    if (header && (!/^\d+$/.test(header) || Number(header) > limit)) throw new Error('response size');
    if (response.body && response.body.getReader) {
      var reader = response.body.getReader(), chunks = [], length = 0;
      try {
        while (true) {
          var part = await reader.read();
          if (part.done) break;
          length += part.value.byteLength;
          if (length > limit) { await reader.cancel(); throw new Error('response size'); }
          chunks.push(part.value);
        }
      } finally { reader.releaseLock(); }
      var bytes = new Uint8Array(length), offset = 0;
      chunks.forEach(function (chunk) { bytes.set(chunk, offset); offset += chunk.byteLength; });
      return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
    }
    var text = await response.text();
    if (new TextEncoder().encode(text).byteLength > limit) throw new Error('response size');
    return JSON.parse(text);
  }
  function pair(doc, parent, en, zh) {
    [['l-en', en], ['l-zh', zh]].forEach(function (entry) { var span = doc.createElement('span'); span.className = entry[0]; span.textContent = entry[1]; parent.appendChild(span); });
  }
  function empty(node) { node.replaceChildren(); }
  function message(doc, node, en, zh) { empty(node); pair(doc, node, en, zh); }
  function fact(doc, dl, en, zh, value) {
    var dt = doc.createElement('dt'), dd = doc.createElement('dd');
    pair(doc, dt, en, zh);
    if (value === null || value === undefined || value === '') pair(doc, dd, 'Unavailable', '不可用');
    else dd.textContent = String(value);
    dl.appendChild(dt); dl.appendChild(dd);
  }
  function renderAvailable(doc, target, payload, selection) {
    var context = payload.context, filing = context.filing, holding = context.holding, generation = context.generation;
    empty(target);
    var title = doc.createElement('h2');
    pair(doc, title, 'Reported holding — further qualification required', '已披露持仓 — 仍需进一步核实'); target.appendChild(title);
    var note = doc.createElement('p');
    pair(doc, note, 'Delayed disclosure. This does not establish current ownership, flows, intent or conviction.', '这是滞后披露，不能据此确定当前持仓、资金流、交易意图或信念强度。'); target.appendChild(note);
    var facts = doc.createElement('dl');
    fact(doc, facts, 'Reported issuer', '披露发行人', holding.name_of_issuer);
    fact(doc, facts, 'Reporting entity', '披露机构', filing.filer_name);
    fact(doc, facts, 'Report period', '报告期', filing.report_period);
    fact(doc, facts, 'Reported CUSIP', '披露 CUSIP', holding.cusip);
    fact(doc, facts, 'Reported quantity', '披露数量', holding.quantity && holding.quantity.value);
    fact(doc, facts, 'Reported quantity unit', '披露数量单位', holding.quantity && holding.quantity.type);
    target.appendChild(facts);
    var limits = doc.createElement('p');
    pair(doc, limits, 'Canonical security, economic vehicle, vehicle class, manager complex and strategy remain unresolved. No normalized quantity or financial decision authority is admitted.', '标准证券标识、经济载体、载体类别、管理机构群及策略均未确定；未准入标准化数量或金融决策权限。'); target.appendChild(limits);
    var details = doc.createElement('details'), summary = doc.createElement('summary'), receipt = doc.createElement('dl'); details.className = 'mx-disc';
    pair(doc, summary, 'Source clocks and verification scope', '来源时钟与核实范围'); details.appendChild(summary);
    fact(doc, receipt, 'Selected decision cutoff (UTC)', '选定决策截止时间（UTC）', selection.decision_cutoff);
    fact(doc, receipt, 'SEC accepted at', 'SEC 接受时间', filing.accepted_at);
    fact(doc, receipt, 'First seen at', '首次观察时间', filing.first_seen_at);
    fact(doc, receipt, 'Retained at', '留存时间', filing.retained_at);
    fact(doc, receipt, 'Catalog published at', '目录发布时间', generation.published_at);
    fact(doc, receipt, 'Catalog source cutoff', '目录来源截止时间', generation.source_cutoff_at);
    fact(doc, receipt, 'Accession', '披露编号', filing.accession);
    fact(doc, receipt, 'Record ID', '记录标识', holding.infotable_sk);
    fact(doc, receipt, 'Row hash', '记录哈希', holding.row_hash);
    fact(doc, receipt, 'Source receipt', '来源凭据', filing.source_receipt_id);
    fact(doc, receipt, 'Catalog', '目录', generation.generation_id);
    fact(doc, receipt, 'Verified artifact roles', '已核实的文件角色', generation.validation_scope.verified_roles.join(', '));
    details.appendChild(receipt);
    var scope = doc.createElement('p');
    pair(doc, scope, 'Only this accession bucket and its supporting filing, relationship, coverage and receipt artifacts were verified. Whole-generation verification: false.', '仅核实此披露所在持仓分桶及其披露、关系、覆盖范围与凭据文件；未核实整个目录。'); details.appendChild(scope);
    var pointer = doc.createElement('p');
    if (generation.pointer.state === 'not_read') pair(doc, pointer, 'Current pointer not read. Whether this pinned catalog is superseded is unknown.', '未读取当前指针；此固定目录是否已被替代尚未知。');
    else pair(doc, pointer, 'Current pointer verified for this read.', '本次读取已核实当前指针。');
    details.appendChild(pointer);
    var link = doc.createElement('a');
    link.href = 'https://www.sec.gov/Archives/edgar/data/' + selection.filer_cik.replace(/^0+/, '') + '/' + selection.accession.replace(/-/g, '') + '/' + selection.accession + '-index.html';
    link.target = '_blank'; link.rel = 'noopener noreferrer'; pair(doc, link, 'Open official SEC filing', '打开 SEC 官方披露'); details.appendChild(link);
    target.appendChild(details); target.hidden = false;
  }
  function createController(options) {
    var version = 0, pending = null;
    function clear() {
      version += 1;
      if (pending) pending.abort();
      pending = null;
      options.clear(); options.busy(false);
    }
    async function read(raw) {
      clear();
      var selection;
      try { selection = normalizeSelection(raw); } catch (_) { options.status('invalid'); return; }
      var ownVersion = version;
      pending = new options.AbortController(); var signal = pending.signal;
      options.busy(true); options.status('pending');
      try {
        var session = await options.session();
        if (version !== ownVersion) return;
        if (!session || typeof session.access_token !== 'string' || !session.access_token) { options.status('signin'); return; }
        var response = await options.fetch(ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + session.access_token }, body: JSON.stringify(selection), cache: 'no-store', credentials: 'same-origin', redirect: 'error', signal: signal });
        // Do not retain the bearer beyond the request's local call scope.
        session = null;
        if (version !== ownVersion) return;
        if (!response.ok) { options.status(response.status === 401 ? 'signin' : response.status === 403 ? 'denied' : 'unavailable'); return; }
        var payload = await readBoundedJson(response);
        if (version !== ownVersion) return;
        validateResponse(payload, selection);
        if (payload.state === 'AVAILABLE_UNQUALIFIED') { options.render(payload, selection); options.status('available'); }
        else options.status(payload.state === 'REFUSED' ? 'refused' : 'absent', payload.context.refusals);
      } catch (_) {
        if (version === ownVersion) options.status('unavailable');
      } finally {
        if (version === ownVersion) { pending = null; options.busy(false); }
      }
    }
    return { clear: clear, read: read };
  }
  var COPY = {
    selected: ['Selection changed. Read the selected filing to see its record.', '选项已更改。读取所选披露以查看记录。'],
    invalid: ['Check the exact filing identifiers, date and UTC cutoff.', '请检查准确的披露标识、日期和 UTC 截止时间。'],
    pending: ['Reading the selected retained filing…', '正在读取所选的留存披露…'],
    signin: ['Sign in with an entitled account, then read the filing.', '请使用有权限的账户登录，再读取披露。'],
    denied: ['This account does not have access to this research read.', '此账户没有该研究读取权限。'],
    unavailable: ['This research read is temporarily unavailable. No ownership conclusion can be drawn.', '此研究读取暂不可用，不能据此得出持仓结论。'],
    absent: ['The selected record is unavailable at this cutoff. This does not mean zero holdings.', '在此截止时间无法取得所选记录，这不表示持仓为零。'],
    refused: ['The source owner refused this selection. No ownership conclusion can be drawn.', '来源系统拒绝了此选项，不能据此得出持仓结论。'],
    available: ['Retained reported context is shown below; further qualification is required.', '下方为留存的披露背景，仍需进一步核实。'],
    auth: ['Authentication changed. Read the filing again with the current account.', '登录状态已更改，请使用当前账户重新读取披露。']
  };
  function mount(win) {
    var doc = win.document, form = doc.getElementById('ff-holding-form');
    if (!form) return null;
    var section = doc.getElementById('ff-holding-research'), status = doc.getElementById('ff-holding-status'), result = doc.getElementById('ff-holding-result'), button = doc.getElementById('ff-holding-read');
    function setStatus(kind, reasons) {
      var copy = COPY[kind]; message(doc, status, copy[0], copy[1]);
      if (reasons && reasons.length) { var codes = doc.createElement('code'); codes.textContent = ' ' + reasons.join(', '); status.appendChild(codes); }
    }
    var controller = createController({
      AbortController: win.AbortController,
      fetch: win.fetch.bind(win),
      session: async function () { var auth = win.MDXAuth, client = auth && auth.client && await auth.client(); if (!client || !client.auth) return null; var response = await client.auth.getSession(); return response && !response.error && response.data && response.data.session; },
      clear: function () { empty(result); result.hidden = true; },
      busy: function (busy) { button.disabled = busy; form.setAttribute('aria-busy', String(busy)); },
      status: setStatus,
      render: function (payload, selection) { renderAvailable(doc, result, payload, selection); }
    });
    function invalidate(kind) { controller.clear(); setStatus(kind); }
    form.addEventListener('input', function () { invalidate('selected'); });
    form.addEventListener('change', function () { invalidate('selected'); });
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var selection = {}; FIELDS.forEach(function (key) { selection[key] = form.elements.namedItem(key).value; });
      controller.read(selection);
    });
    section.querySelectorAll('[data-holding-example]').forEach(function (example) {
      example.addEventListener('click', function () {
        invalidate('selected');
        var selection = EXAMPLES[example.getAttribute('data-holding-example')];
        if (selection) FIELDS.forEach(function (key) { form.elements.namedItem(key).value = selection[key]; });
      });
    });
    // Existing theme.js owns MDXAuth; this listener clears without moving any
    // credential or depending on financial-statement loading success.
    var bound = false;
    function bindAuth() { if (!bound && win.MDXAuth && typeof win.MDXAuth.onChange === 'function') { bound = true; win.MDXAuth.onChange(function () { invalidate('auth'); }); } }
    bindAuth(); if (!bound) win.addEventListener('load', bindAuth, { once: true });
    function openHash() {
      if (win.location.hash === '#reported-holding' || win.location.hash === '#ff-holding-research') {
        section.open = true;
        win.requestAnimationFrame(function () { section.scrollIntoView({ block: 'start' }); });
      }
    }
    openHash(); win.addEventListener('hashchange', openHash);
    win.addEventListener('pagehide', function () { controller.clear(); });
    return controller;
  }
  return { EXAMPLES: EXAMPLES, normalizeSelection: normalizeSelection, validateResponse: validateResponse, readBoundedJson: readBoundedJson, createController: createController, renderAvailable: renderAvailable, mount: mount };
}));
