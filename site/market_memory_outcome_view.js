/* Paper U2 outcome inspection. Presentation only: the retained intent owner
 * owns requests, authorization, cutoffs, epochs and history. No network/storage. */
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(require('./market_memory_outcome_contract.js'));
  } else root.MarketMemoryOutcomeView = factory(root.MarketMemoryOutcomeContract);
}(typeof globalThis !== 'undefined' ? globalThis : this, function (contract) {
  'use strict';
  function esc(value) {
    return String(value).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  function render(raw, expected, caseLabels, locale) {
    if (!contract) throw new Error('outcome_view:contract_unavailable');
    var data = contract.normalizeOutcomeAttachment(raw, expected);
    if (!Array.isArray(caseLabels) || caseLabels.length !== data.rows.length
        || caseLabels.some(function (label, i) {
          return !label || label.contextId !== data.rows[i].contextId
            || typeof label.label !== 'string' || !label.label || label.label.length > 160;
        })) throw new Error('outcome_view:case_binding');
    var zh = locale === 'zh';
    function copy(en, cn) { return zh ? cn : en; }
    function pair(label, value, code) {
      return '<div><dt>' + esc(label) + '</dt><dd>' + (code ? '<code>' : '')
        + esc(value) + (code ? '</code>' : '') + '</dd></div>';
    }
    function reason(row) {
      if (row.status === 'proof_pending') return copy(
        'No qualified observation is visible by this cutoff. Missing is not zero.',
        '截至此时没有可见且经核验的观察记录。缺失不等于零。');
      var reasons = {
        outcome_calendar_unavailable: copy('The registered observation calendar is unavailable.', '注册的观察日历不可用。'),
        ambiguous_source_observation_clock: copy('The source observation time could not be resolved.', '无法确定来源观察时间。'),
        source_observation_after_registered_deadline: copy('The source observation arrived after the registered deadline.', '来源观察晚于注册截止时间。')
      };
      return reasons[row.reason] || '';
    }
    function evidence(row) {
      var observation = row.observation;
      if (!observation) return '';
      return '<details class="mmr-disc mmr-outcome-evidence"><summary>'
        + esc(copy('Inspect original evidence', '核对原始依据')) + '</summary><dl class="mmr-coverage">'
        + pair(copy('Observation', '观察记录'), observation.id, true)
        + pair(copy('Original digest', '原始摘要'), observation.sha256, true)
        + pair(copy('Revision', '修订版本'), observation.revisionNumber, false)
        + (observation.previousObservationId
          ? pair(copy('Previous observation', '上一观察记录'), observation.previousObservationId, true) : '')
        + pair(copy('Observed at', '观察时间'), observation.clocks.observedAt, false)
        + pair(copy('Published at', '发布时间'), observation.clocks.publishedAt, false)
        + pair(copy('Recorded at', '记录时间'), observation.clocks.recordedAt, false)
        + (row.valueQ18 === null ? '' : pair(copy('Exact archived close ratio', '确切归档收盘价比值'), row.valueQ18, true))
        + '</dl></details>';
    }
    var rows = data.rows.map(function (row, i) {
      var status = row.status === 'observed' ? copy('Observed', '已观察')
        : row.status === 'censored' ? copy('Censored', '受限观察') : copy('Proof pending', '待核验');
      return '<article class="mmr-outcome-row" data-mmr-context="' + esc(row.contextId)
        + '" data-mmr-outcome-state="' + esc(row.status) + '">'
        + '<div class="mmr-outcome-case"><span class="mmr-eyebrow">' + esc(copy('Original match ', '原匹配顺序 ') + row.rank)
        + '</span><h3>' + esc(caseLabels[i].label) + '</h3><p class="mmr-note">'
        + esc(copy('Distance ', '距离 ')) + '<code>' + esc(row.distanceQ18) + '</code></p></div>'
        + '<div class="mmr-outcome-reading"><span class="mmr-status">' + esc(status) + '</span>'
        + (row.status === 'observed' ? '<strong class="mmr-outcome-ratio">' + esc(contract.formatRatio(row.valueQ18))
          + '</strong><span class="mmr-note">' + esc(copy('Archived close ratio', '归档收盘价比值')) + '</span>'
          : '<p class="mmr-note">' + esc(reason(row)) + '</p>') + '</div>' + evidence(row) + '</article>';
    }).join('');
    return '<section class="mmr-outcome-inspector" aria-label="' + esc(copy('Subsequent observations', '后续观察')) + '">'
      + '<button type="button" class="gbtn gbtn-quiet mmr-action" data-mmr-action="outcome-back">'
      + esc(copy('Back to comparison', '返回比较')) + '</button><p class="mmr-eyebrow">'
      + esc(copy('SUBSEQUENT OBSERVATIONS', '后续观察')) + '</p><h2>'
      + esc(copy('What happened after these cases?', '这些案例之后发生了什么？')) + '</h2><p class="mmr-lead">'
      + esc(copy('The original cases, order and distances stay fixed. These observations describe what became visible afterward.',
        '原始案例、顺序和距离保持不变。这些观察描述之后可见的信息。')) + '</p>'
      + '<div class="mmr-outcome-clocks"><div class="mmr-outcome-lenses" role="group" aria-label="'
      + esc(copy('Observation lens', '观察视角')) + '">'
      + ['then_known', 'later_observed'].map(function (lens) {
        return '<button type="button" class="gbtn gbtn-quiet mmr-action" data-mmr-action="outcome-lens" data-mmr-lens="'
          + lens + '" aria-pressed="' + String(lens === data.lens) + '">'
          + esc(lens === 'then_known' ? copy('Known then', '当时已知') : copy('Observed later', '事后观察')) + '</button>';
      }).join('') + '</div><dl class="mmr-coverage">'
      + pair(copy('Comparison cutoff', '比较截至时间'), data.queryCutoff, false)
      + pair(copy('Observation cutoff', '观察截至时间'), data.outcomeCutoff, false) + '</dl></div>'
      + (rows || '<p class="mmr-note">' + esc(copy('There are no selected cases to inspect.', '没有可供核对的已选案例。')) + '</p>')
      + '<p class="mmr-note mmr-outcome-qualification">' + esc(copy(
        'Later archived source close divided by the case source close. Corporate-action adjustments and regular-session close timing are not authenticated. This is not total return. Selected cases are not independent trials.',
        '后续来源归档收盘价除以案例来源收盘价。未核验公司行动调整及常规交易时段收盘时间。这不是总回报；所选案例并非独立试验。'))
      + '</p></section>';
  }
  return Object.freeze({ render: render });
}));
