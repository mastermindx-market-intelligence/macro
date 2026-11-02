/* Explicit, ephemeral X2 assumptions. No persistence, telemetry, automatic
 * evaluation, owner writes, forecasts or invented downstream propagation. */
const HASH = /^sha256:[a-f0-9]{64}$/;
const CHAIN = 'oil_inflation_duration_derate';
const LIMIT = 262144, BUDGET = 15000;
const AXES = ['can_rank', 'can_gate', 'can_size', 'can_trade'];
const EFFECTS = ['owner_writes', 'episode_writes', 'calibration_writes', 'portfolio_writes', 'alert_writes'];
const REASONS = {
  WTI_FUTURES_CALENDAR_UNAVAILABLE: ['The WTI owner has not supplied a qualified futures calendar, source generation and source-use receipt.', 'WTI 数据方尚未提供合格的期货日历、数据版本及使用凭据。'],
  FUTURES_CALENDAR_OWNER_UNQUALIFIED: ['The futures calendar owner is not qualified for this evaluation.', '期货日历数据方尚不满足本次评估要求。'],
  NUMERIC_OWNER_METADATA_UNAVAILABLE: ['The rates owner lacks the estimation span, sample counts and calendar/cutoff metadata needed for a numeric replay.', '利率数据方缺少数值重演所需的估计区间、样本数、日历及知识截止信息。'],
  NUMERIC_OWNER_CLOCK_UNAVAILABLE: ['The calibration dates do not qualify for this selected reading.', '校准日期不满足当前所选读数的要求。'],
  NUMERIC_METHOD_VERSION_UNAVAILABLE: ['The calibration was produced by a different or unavailable method version.', '该校准来自不同或不可用的方法版本。'],
  NUMERIC_PATH_SHAPE_UNSUPPORTED: ['The existing rates illustration supports only the assumed endpoint change.', '现有利率示意仅支持假设的期末变化。'],
  NUMERIC_SHOCK_UNAVAILABLE: ['This change cannot be evaluated by the existing rates method.', '现有利率方法无法评估该变化。'],
  HORIZON_INCOMPATIBLE: ['This horizon is outside the existing root evaluator.', '该期限不在现有根条件评估器的支持范围内。'],
  OWNER_CALENDAR_TOO_SHORT: ['The owner calendar does not cover the requested horizon.', '数据方日历未覆盖所请求的期限。'],
  EPHEMERAL_REPLAY_UNAVAILABLE: ['The existing owner inputs cannot support this replay.', '现有数据方输入不足以支持本次重演。'],
};
function fail() { throw new Error('SCENARIO_UNAVAILABLE'); }
function canonical() {
  try { const u = window.MDXAuth?.user?.(); return typeof u?.id === 'string' && u.id ? u.id : null; }
  catch (_) { return null; }
}
function instant(s) {
  return typeof s === 'string' && s.length <= 64 && /(?:Z|[+-]\d\d:\d\d| UTC)$/.test(s)
    && Number.isFinite(Date.parse(s.replace(' UTC', 'Z').replace(' ', 'T')));
}
function millis(s) { return Date.parse(s.replace(' UTC', 'Z').replace(' ', 'T')); }
function day(s) {
  return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s)
    && Number.isFinite(Date.parse(s)) && new Date(s).toISOString().slice(0, 10) === s;
}
function words(en, zh) {
  const f = document.createDocumentFragment();
  for (const [lang, value] of [['en', en], ['zh', zh]]) {
    const n = document.createElement('span'); n.className = 'l-' + lang; n.textContent = value; f.append(n);
  }
  return f;
}
function text(en, zh) { const n = document.createElement('p'); n.className = 'ox-note'; n.append(words(en, zh)); return n; }
function cancel(reader) { try { void Promise.resolve(reader.cancel()).catch(() => {}); } catch (_) { /* best effort */ } }
function sorted(value) {
  if (Array.isArray(value)) return value.map(sorted);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(k => [k, sorted(value[k])]));
  return value;
}
export async function snapshotIdentity(r) {
  const source = Object.fromEntries(['chain', 'rev', 'asof', 'built', 'composer_method', 'source_manifest_hash'].map(k => [k, r[k]]));
  const bytes = new TextEncoder().encode(JSON.stringify(sorted({ schema: 'ontology_explorer_snapshot.v1', source })));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return 'sha256:' + [...new Uint8Array(digest)].map(v => v.toString(16).padStart(2, '0')).join('');
}
function numericResult(r, o, assumption, reading) {
  const c = r.calibration, s = r.scenario, h = r.horizon, cover = r.coverage;
  const policy = 'engine.rate_inflation_transmission.scenarios:display_only';
  if (assumption.node_ref !== 'transmission:real10y_chg63' || assumption.path_shape !== 'terminal_only'
      || assumption.unit !== 'bp' || assumption.horizon !== '63d'
      || r.node_ref !== assumption.node_ref || r.method_class !== 'EMPIRICAL_SAME_WINDOW_BETA' || r.confirmed !== null
      || r.uncertainty !== 'not_provided_by_native_owner' || !c || !o || !s || !cover
      || h?.label !== '63d' || h.unit !== 'native_feature_index_positions' || h.count !== 63
      || s.driver !== 'real10y_chg63' || s.shock_bp !== assumption.magnitude
      || !day(c.effective_at) || c.effective_at > reading.asof || !instant(c.generated_at)
      || millis(c.generated_at) > millis(reading.built) || c.effective_at > c.generated_at.slice(0, 10)
      || c.publication_contract !== policy || c.historical_vintage_claim !== false
      || o.publication_contract !== policy || o.historical_vintage_claim !== false
      || o.source_manifest_hash !== reading.source_manifest_hash || o.selected_effective_at !== reading.asof
      || !instant(o.selected_knowledge_cutoff) || millis(o.selected_knowledge_cutoff) !== millis(reading.built)
      || o.effective_at !== c.effective_at || !instant(o.knowledge_cutoff) || millis(o.knowledge_cutoff) !== millis(c.generated_at)
      || !HASH.test(o.generation) || o.calibration_source?.path !== 'data/transmission/calibration.json'
      || o.generation !== 'sha256:' + o.calibration_source.sha256
      || !Number.isSafeInteger(o.calibration_source.bytes) || o.calibration_source.bytes <= 0) fail();
  const cal = c.calendar;
  // These are observed native index labels, not a supplied future session calendar.
  const labelTime = v => typeof v === 'string' && v.length <= 64 && day(v.slice(0, 10)) && Number.isFinite(Date.parse(v));
  if (!cal || cal.owner_ref !== 'engine.inputs.build_features.index' || cal.unit !== 'native_feature_index_positions'
      || !HASH.test(cal.sha256) || o.calendar_id !== cal.owner_ref || o.calendar_version !== cal.sha256
      || !Number.isSafeInteger(cal.count) || cal.count < 567 || !labelTime(cal.start) || !labelTime(cal.end)
      || Date.parse(cal.start) >= Date.parse(cal.end) || cal.end.slice(0, 10) !== c.effective_at
      || !c.method_versions || ['estimator', 'display', 'receipt'].some(k => !HASH.test(c.method_versions[k]))
      || ['pandas', 'numpy'].some(k => typeof c.method_versions[k] !== 'string' || !c.method_versions[k] || c.method_versions[k].length > 128)
      || !Array.isArray(cover.calibrated_assets) || !cover.calibrated_assets.length || cover.calibrated_assets.length > 128
      || cover.calibrated_assets.some(a => typeof a !== 'string' || !/^[A-Za-z0-9.^=_-]{1,32}$/.test(a))
      || new Set(cover.calibrated_assets).size !== cover.calibrated_assets.length
      || !r.samples || Object.keys(r.samples).length !== cover.calibrated_assets.length) fail();
  for (const asset of cover.calibrated_assets) {
    const p = r.samples[asset];
    if (!p || p.state !== 'available' || typeof p.beta !== 'number' || !Number.isFinite(p.beta)
        || !Number.isSafeInteger(p.n) || p.n < 504 || p.n > cal.count - 63
        || p.sample_count_kind !== 'overlapping_paired_observations' || p.effective_n !== null
        || !HASH.test(p.paired_sample_sha256) || !labelTime(p.start) || !labelTime(p.end)
        || Date.parse(p.start) < Date.parse(cal.start) || Date.parse(p.end) > Date.parse(cal.end)
        || Date.parse(p.start) > Date.parse(p.end)) fail();
  }
  const displayed = [];
  for (const [side, positive] of [['headwinds', false], ['tailwinds', true]]) {
    if (!Array.isArray(s[side]) || s[side].length > 5) fail();
    for (const row of s[side]) {
      if (!row || !cover.calibrated_assets.includes(row.asset) || displayed.includes(row.asset)
          || typeof row.label !== 'string' || !row.label || row.label.length > 256
          || typeof row.implied_move_pct !== 'number' || !Number.isFinite(row.implied_move_pct)
          || (positive ? row.implied_move_pct <= 0 : row.implied_move_pct >= 0)) fail();
      displayed.push(row.asset);
    }
  }
  if (JSON.stringify(cover.displayed_assets) !== JSON.stringify(displayed) || !Array.isArray(cover.not_displayed)
      || JSON.stringify(cover.not_displayed.map(a => a?.asset)) !== JSON.stringify(cover.calibrated_assets.filter(a => !displayed.includes(a)))
      || cover.not_displayed.some(a => a.reason !== 'native_display_floor_or_five_per_side_limit')
      || !Array.isArray(r.caveats) || !r.caveats.length || r.caveats.length > 16
      || r.caveats.some(a => ['en', 'zh'].some(k => typeof a?.[k] !== 'string' || !a[k] || a[k].length > 4096))) fail();
}
export function decodeEvaluation(v, assumption, snapshotId, reading) {
  if (!v || v.schema !== 'ontology_scenario_eval.v1' || v.snapshot_id !== snapshotId
      || !HASH.test(v.scenario_eval_id) || !HASH.test(v.assumption_id)
      || !instant(v.evaluated_at) || !instant(v.assumption?.created_at)
      || millis(v.assumption.created_at) > millis(v.evaluated_at)
      || v.assumption.assumption_id !== v.assumption_id || v.assumption.snapshot_id !== snapshotId
      || !Array.isArray(v.method_versions) || !v.method_versions.length || v.method_versions.length > 16
      || v.method_versions.some(s => typeof s !== 'string' || !s || s.length > 256)
      || !v.authority || AXES.some(k => v.authority[k] !== false)
      || !v.side_effect_receipt || EFFECTS.some(k => v.side_effect_receipt[k] !== 0)
      || v.combined_estimate !== null || v.no_combined_estimate_reason !== 'NO_ACCEPTED_JOINT_RESPONSE_OWNER'
      || !Array.isArray(v.hop_evaluations) || v.hop_evaluations.length > 32
      || v.hop_evaluations.some(h => !h || h.method_class !== 'HYPOTHESIS_MECHANISM'
        || h.value !== null || h.reason !== 'DOWNSTREAM_NOT_ASSUMED')) fail();
  for (const key of Object.keys(assumption)) {
    if (key === 'baseline_knowledge_cutoff') {
      if (!instant(v.assumption[key]) || millis(v.assumption[key]) !== millis(assumption[key])) fail();
    } else if (v.assumption[key] !== assumption[key]) fail();
  }
  const r = v.root_evaluation;
  if (!r || !['UNAVAILABLE', 'ROOT_THRESHOLD_MET', 'SCENARIO_NOT_ARMED', 'PARTIAL_UNKNOWN', 'NUMERIC_ILLUSTRATION'].includes(r.status)) fail();
  if (r.status === 'UNAVAILABLE') {
    if (r.confirmed !== null || !Object.hasOwn(REASONS, r.reason || 'EPHEMERAL_REPLAY_UNAVAILABLE')) fail();
  } else if (r.status === 'NUMERIC_ILLUSTRATION') {
    numericResult(r, v.owner_receipt, assumption, reading);
  } else {
    if (r.method_class !== 'THRESHOLD_STATE_ONLY'
        || (r.status === 'ROOT_THRESHOLD_MET' && r.confirmed !== true)
        || (r.status === 'SCENARIO_NOT_ARMED' && r.confirmed !== false && r.confirmed !== null)
        || (r.status === 'PARTIAL_UNKNOWN' && r.confirmed !== null)) fail();
    const o = v.owner_receipt;
    if (!o || o.source_manifest_hash !== reading.source_manifest_hash || o.effective_at !== reading.asof
        || !instant(o.knowledge_cutoff) || millis(o.knowledge_cutoff) !== millis(reading.built)
        || !HASH.test(o.rights_ref) || typeof o.calendar_id !== 'string' || !o.calendar_id
        || typeof o.calendar_version !== 'string' || !o.calendar_version) fail();
  }
  return v;
}

export function mountScenario(root) {
  if (!root) return null;
  const form = root.querySelector('[data-scenario-form]'), output = root.querySelector('[data-scenario-result]');
  if (!form || !output) return null;
  let reading = null, operation = null, epoch = 0, disposed = false, subscription = null;
  let unsupportedOwner = null;
  let eventOwner = canonical();
  function select(name, label, options) {
    const wrap = document.createElement('label'); wrap.className = 'ox-company-label'; wrap.append(words(...label));
    const control = document.createElement('select'); control.name = name;
    for (const [value, en, zh] of options) {
      const option = document.createElement('option'); option.value = value; option.dataset.en = en; option.dataset.zh = zh;
      option.textContent = document.documentElement.dataset.lang === 'zh' ? zh : en; control.append(option);
    }
    wrap.append(control); form.append(wrap); return control;
  }
  const node = select('node', ['Assumed input', '假设输入'], [['yahoo:CL=F', 'WTI oil', 'WTI 原油'], ['transmission:real10y_chg63', '10-year real yield change', '10年期实际收益率变化']]);
  const label = document.createElement('label'); label.className = 'ox-company-label'; label.append(words('Assumed change (%)', '假设变化（%）'));
  const magnitude = document.createElement('input'); magnitude.name = 'magnitude'; magnitude.type = 'number';
  magnitude.step = 'any'; magnitude.required = true; magnitude.autocomplete = 'off'; label.append(magnitude); form.append(label);
  const shape = select('shape', ['Assumed path', '假设路径'], [['terminal_only', 'Terminal value only', '仅指定期末值'], ['linear_sessions', 'Linear over owner sessions', '按数据方交易日线性变化'], ['step_at_start', 'Immediate step held to horizon', '期初跳变并维持至期末']]);
  const origin = select('origin', ['Assumed origin', '假设来源'], [['unspecified', 'Unspecified', '未指定'], ['supply', 'Supply', '供给'], ['demand', 'Demand', '需求'], ['residual', 'Residual', '残差']]);
  let previousNode = node.value;
  const horizon = text('WTI: 60 owner sessions. Future sessions must come from its owner; none are guessed.', 'WTI：60个数据方交易日。未来交易日必须由数据方提供，不作推测。'); form.append(horizon);
  const submit = document.createElement('button'); submit.type = 'submit'; submit.className = 'ox-cta'; submit.append(words('Evaluate assumption', '评估假设')); form.append(submit);
  const clearButton = document.createElement('button'); clearButton.type = 'button'; clearButton.className = 'ox-cta secondary'; clearButton.append(words('Clear assumption', '清除假设')); form.append(clearButton);
  function status(state) {
    output.replaceChildren(); output.dataset.state = state; output.setAttribute('aria-busy', state === 'loading' ? 'true' : 'false');
    const copy = {
      no_reading: ['Load a current path reading first.', '请先加载当前路径读数。'],
      path_unavailable: ['Scenario evaluation is available only for the oil and rates path. This dollar path remains an observed reading.', '情景评估仅适用于石油与利率路径。此美元路径仍表示观测读数。'],
      idle: ['Enter an explicit assumption. Evaluation runs only when requested.', '请输入明确假设；仅在您请求后运行评估。'],
      loading: ['Evaluating this assumption against the selected reading…', '正在依据所选读数评估该假设…'],
      invalid: ['Enter a finite change; WTI must remain above −100%.', '请输入有限数值；WTI变化必须大于−100%。'],
      signed_out: ['Sign in again before evaluating an assumption.', '请重新登录后评估假设。'],
      forbidden: ['This account does not include private scenario research.', '此账户未包含私有情景研究权限。'],
      changed: ['The selected source changed. Reload the path before evaluating again.', '所选数据源已变化，请重新加载路径后再评估。'],
      unavailable: ['This evaluation is unavailable. No forecast or replacement result is substituted.', '本次评估不可用；不会以预测或替代结果填补。'],
    };
    output.append(text(...(copy[state] || copy.unavailable))); submit.disabled = !reading || state === 'loading';
  }
  function stop() {
    epoch++;
    if (operation) { const old = operation; operation = null; old.abort.abort(); if (old.reader) cancel(old.reader); clearTimeout(old.timer); old.reject(new Error('SCENARIO_CANCELLED')); }
  }
  function changedNode() {
    if (previousNode !== node.value) { magnitude.value = ''; previousNode = node.value; }
    shape.disabled = node.value !== 'yahoo:CL=F';
    if (shape.disabled) shape.value = 'terminal_only';
    label.replaceChildren(words(node.value === 'yahoo:CL=F' ? 'Assumed change (%)' : 'Assumed change (basis points)', node.value === 'yahoo:CL=F' ? '假设变化（%）' : '假设变化（基点）'), magnitude);
    horizon.replaceChildren(words(...(node.value === 'yahoo:CL=F'
      ? ['WTI: 60 owner sessions. Future sessions must come from its owner; none are guessed.', 'WTI：60个数据方交易日。未来交易日必须由数据方提供，不作推测。']
      : ['Real yield: a 63-observation same-window illustration, using the selected native calibration when available.', '实际收益率：使用所选原生校准（如可用），展示63个观测间隔的同窗示意。'])));
  }
  function clear(reset = false) { stop(); if (reset) { form.reset(); magnitude.value = ''; changedNode(); } status(reading ? 'idle' : unsupportedOwner ? 'path_unavailable' : 'no_reading'); }
  function invalidate() { reading = null; unsupportedOwner = null; clear(true); }
  function auth(event) {
    const u = event.detail?.user; eventOwner = typeof u?.id === 'string' && u.id ? u.id : null;
    // The page reloads only when its canonical owner changes. A same-owner
    // refresh must clear private inputs/results without stranding that reading.
    if (event.detail?.event !== 'SIGNED_OUT' && (reading?.owner_id === eventOwner || unsupportedOwner === eventOwner) && eventOwner === canonical()) clear(true);
    else invalidate();
  }
  function check(op) {
    if (disposed || epoch !== op.id || document.hidden || reading !== op.reading || op.abort.signal.aborted
        || performance.now() >= op.deadline || canonical() !== op.owner || eventOwner !== op.owner) fail();
  }
  async function checked(op, promise) { const v = await promise; check(op); return v; }
  const authentication = Promise.resolve().then(async () => {
    const sdk = await window.MDXAuth?.client?.();
    if (disposed || typeof sdk?.auth?.onAuthStateChange !== 'function') fail();
    const result = sdk.auth.onAuthStateChange(() => clear(true)); subscription = result?.data?.subscription;
    if (typeof subscription?.unsubscribe !== 'function') fail(); return sdk;
  });
  void authentication.catch(() => {});
  async function session(op, token) {
    const sdk = await checked(op, authentication), result = await checked(op, sdk.auth.getSession());
    const s = result?.data?.session;
    if (result?.error || s?.user?.id !== op.owner || typeof s?.access_token !== 'string' || !s.access_token) {
      invalidate(); status('signed_out'); fail();
    }
    if (token && token !== s.access_token) { clear(true); fail(); }
    return s.access_token;
  }
  async function body(op, response) {
    const h = response.headers, parts = key => (h.get(key) || '').toLowerCase().split(',').map(v => v.trim());
    if (response.redirected || !/^application\/json(?:\s*;|$)/i.test(h.get('Content-Type') || '')
        || !parts('Cache-Control').includes('private') || !parts('Cache-Control').includes('no-store')
        || !parts('Vary').includes('authorization') || !parts('Vary').includes('cookie')) fail();
    const length = h.get('Content-Length'); if (length !== null && (!/^\d+$/.test(length) || Number(length) > LIMIT)) fail();
    const reader = response.body?.getReader(); if (!reader) fail(); op.reader = reader;
    const decoder = new TextDecoder('utf-8', { fatal: true }), pieces = []; let size = 0, complete = false;
    try {
      for (;;) {
        const chunk = await checked(op, reader.read()); if (chunk.done) break;
        if (!(chunk.value instanceof Uint8Array)) fail(); size += chunk.value.byteLength; if (size > LIMIT) fail();
        pieces.push(decoder.decode(chunk.value, { stream: true }));
      }
      pieces.push(decoder.decode()); check(op); const v = JSON.parse(pieces.join('')); complete = true; return v;
    } finally { if (!complete) cancel(reader); if (op.reader === reader) op.reader = null; try { reader.releaseLock(); } catch (_) { /* abandoned read */ } }
  }
  function render(v) {
    output.replaceChildren(); output.dataset.state = 'ready'; output.setAttribute('aria-busy', 'false');
    const r = v.root_evaluation;
    const numeric = r.status === 'NUMERIC_ILLUSTRATION';
    const headline = numeric ? ['Historical same-window illustration', '历史同窗示意']
      : r.status === 'UNAVAILABLE' ? ['Evaluation unavailable', '评估不可用']
      : r.status === 'ROOT_THRESHOLD_MET' ? ['Assumed root threshold met', '假设下根条件已满足']
      : r.status === 'PARTIAL_UNKNOWN' ? ['Endpoint condition met; path condition unknown', '期末条件已满足；路径条件未知']
      : ['Root threshold is not armed by this assumption', '该假设未使根条件触发'];
    output.append(text(...headline));
    if (r.status === 'UNAVAILABLE') output.append(text(...(REASONS[r.reason] || REASONS.EPHEMERAL_REPLAY_UNAVAILABLE)));
    if (numeric) {
      const signed = n => (n > 0 ? '+' : '') + n;
      output.append(text(`Assumed real 10Y change: ${signed(r.scenario.shock_bp)} bp over 63 native observations. These are conditional illustrations, not forecasts or causal estimates.`,
        `假设实际10年期收益率在63个原生观测间隔内变化${signed(r.scenario.shock_bp)}基点。以下为条件示意，并非预测或因果估计。`));
      for (const [side, title] of [['headwinds', ['Illustrative headwinds', '示意逆风']], ['tailwinds', ['Illustrative tailwinds', '示意顺风']]]) {
        const heading = document.createElement('h3'); heading.append(words(...title)); output.append(heading);
        const rows = document.createElement('ul'); rows.className = 'ox-portfolio-rows';
        for (const row of r.scenario[side]) {
          const sample = r.samples[row.asset], item = document.createElement('li'); item.className = 'ox-portfolio-row';
          const name = document.createElement('strong'); name.textContent = `${row.asset} · ${signed(row.implied_move_pct)}%`; item.append(name);
          item.append(text(`${sample.n} overlapping paired observations · ${sample.start.slice(0, 10)} to ${sample.end.slice(0, 10)}.`,
            `${sample.n}个重叠配对观测 · ${sample.start.slice(0, 10)}至${sample.end.slice(0, 10)}。`)); rows.append(item);
        }
        if (!rows.children.length) output.append(text('No assets pass the native display threshold on this side.', '该方向无资产满足原生展示阈值。'));
        else output.append(rows);
      }
      output.append(text(`${r.coverage.displayed_assets.length} of ${r.coverage.calibrated_assets.length} calibrated assets shown; native display floor 0.5% and at most five per side.`,
        `展示${r.coverage.calibrated_assets.length}个已校准资产中的${r.coverage.displayed_assets.length}个；原生展示门槛为0.5%，每侧最多5个。`));
      output.append(text('Uncertainty intervals and effective independent sample size are not provided. Overlapping observations are not independent episodes.',
        '未提供不确定性区间及有效独立样本量。重叠观测不等同于独立事件。'));
      output.append(text(`Calibration observations through ${r.calibration.effective_at}; generated ${r.calibration.generated_at}. This does not claim historical point-in-time availability.`,
        `校准观测截至${r.calibration.effective_at}；生成于${r.calibration.generated_at}。这不代表该数据在历史时点已可获取。`));
      const notes = document.createElement('details'), summary = document.createElement('summary'); summary.append(words('Native method notes', '原生方法说明')); notes.append(summary);
      for (const note of r.caveats) notes.append(text(note.en, note.zh)); output.append(notes);
    }
    if (v.assumption.node_ref === 'yahoo:CL=F' && v.assumption.path_shape === 'terminal_only') output.append(text('A terminal-only value cannot establish the moving-average path.', '仅有期末值无法确立移动平均线路径条件。'));
    output.append(text(`Baseline ${reading.asof}; knowledge cutoff ${reading.built}. Evaluated ${v.evaluated_at}.`, `基准日期 ${reading.asof}；知识截止 ${reading.built}。评估时间 ${v.evaluated_at}。`));
    output.append(text('Downstream effects remain unknown. There is no combined estimate, forecast, portfolio change or alert.', '下游影响仍未知。不提供综合估计、预测、投资组合变更或提醒。'));
    submit.disabled = !reading;
  }
  async function evaluate(event) {
    event.preventDefault(); stop();
    if (!reading) { status('no_reading'); return; }
    const owner = canonical(); if (!owner || owner !== reading.owner_id || owner !== eventOwner) { invalidate(); status('signed_out'); return; }
    const m = magnitude.value.trim(), number = Number(m), wti = node.value === 'yahoo:CL=F';
    if (!m || !Number.isFinite(number) || (wti && number <= -100)) { status('invalid'); return; }
    const assumption = { schema: 'ontology_scenario_assumption.v1', node_ref: node.value,
      shock_definition: wti ? 'terminal_change_over_horizon' : 'absolute_change_bp_over_horizon', magnitude: number,
      unit: wti ? 'percent' : 'bp', horizon: wti ? '60d' : '63d', path_shape: shape.value,
      origin_class: origin.value, baseline_effective_at: reading.asof, baseline_knowledge_cutoff: reading.built };
    const op = { id: epoch, owner, reading, abort: new AbortController(), reader: null, deadline: performance.now() + BUDGET };
    const cancellation = new Promise((_, reject) => { op.reject = reject; }); operation = op;
    op.timer = setTimeout(() => { op.abort.abort(); if (op.reader) cancel(op.reader); op.reject(new Error('SCENARIO_TIMEOUT')); }, BUDGET);
    status('loading');
    try {
      await Promise.race([(async () => {
        const token = await session(op), snapshotId = await checked(op, snapshotIdentity(op.reading));
        const raw = JSON.stringify({ schema: 'ontology_scenario_request.v1', source_manifest_hash: op.reading.source_manifest_hash, assumption });
        if (new TextEncoder().encode(raw).length > 4096) fail();
        const response = await checked(op, fetch('/api/ontology/explorer/scenario/v1', { method: 'POST',
          credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: op.abort.signal,
          headers: { Accept: 'application/json', 'Content-Type': 'application/json', Authorization: 'Bearer ' + token }, body: raw }));
        const value = await checked(op, body(op, response)); await session(op, token);
        if (response.status !== 200) {
          // Auth detail belongs to the existing authority, never rendered here.
          if (response.status === 401) { invalidate(); status('signed_out'); }
          else if (response.status === 403) status('forbidden');
          else if (response.status === 409 && value?.detail?.schema === 'ontology_explorer_error.v1' && value.detail.code === 'source_changed') { invalidate(); status('changed'); }
          else status('unavailable');
          return;
        }
        const result = decodeEvaluation(value, assumption, snapshotId, op.reading); check(op); render(result);
      })(), cancellation]);
    } catch (_) {
      if (!disposed && epoch === op.id) {
        if (canonical() !== owner || eventOwner !== owner) { invalidate(); status('signed_out'); }
        else status('unavailable');
      }
    }
    finally { op.abort.abort(); if (op.reader) cancel(op.reader); clearTimeout(op.timer); if (operation === op) operation = null; }
  }
  function receive(event) {
    invalidate(); const r = event.detail;
    if (r?.chain === 'dollar_spike_em_multinational' && r.owner_id === canonical() && r.owner_id === eventOwner) {
      unsupportedOwner = r.owner_id; status('path_unavailable'); return;
    }
    if (!r || r.chain !== CHAIN || !HASH.test(r.source_manifest_hash) || !day(r.asof) || !instant(r.built)
        || !(typeof r.rev === 'string' && /^[A-Za-z0-9._:-]{1,128}$/.test(r.rev) || Number.isSafeInteger(r.rev))
        || typeof r.composer_method !== 'string' || !/^[A-Za-z0-9._:-]{1,128}$/.test(r.composer_method)
        || !r.owner_id || r.owner_id !== canonical() || r.owner_id !== eventOwner) return;
    reading = Object.fromEntries(['chain', 'rev', 'asof', 'built', 'composer_method', 'source_manifest_hash', 'owner_id'].map(k => [k, r[k]])); status('idle');
  }
  function input() { clear(); changedNode(); }
  function clearClick() { clear(true); }
  function hidden() { if (document.hidden) clear(true); }
  function language() { const lang = document.documentElement.dataset.lang === 'zh' ? 'zh' : 'en';
    for (const option of form.querySelectorAll('option')) option.textContent = option.dataset[lang]; }
  root.addEventListener('ontology-reading', receive); root.addEventListener('ontology-source-changed', invalidate);
  window.addEventListener('mdx-auth', auth); window.addEventListener('pagehide', invalidate); document.addEventListener('visibilitychange', hidden); document.addEventListener('langchange', language);
  form.addEventListener('submit', evaluate); form.addEventListener('input', input); form.addEventListener('change', input); clearButton.addEventListener('click', clearClick);
  status('no_reading'); root.dispatchEvent(new CustomEvent('ontology-consumer-ready'));
  return { clear: clearClick, dispose() { disposed = true; invalidate(); output.replaceChildren(); subscription?.unsubscribe();
    root.removeEventListener('ontology-reading', receive); root.removeEventListener('ontology-source-changed', invalidate);
    window.removeEventListener('mdx-auth', auth); window.removeEventListener('pagehide', invalidate); document.removeEventListener('visibilitychange', hidden); document.removeEventListener('langchange', language);
    form.removeEventListener('submit', evaluate); form.removeEventListener('input', input); form.removeEventListener('change', input); clearButton.removeEventListener('click', clearClick);
    form.replaceChildren(); } };
}
mountScenario(document.getElementById('ox-scenario'));
