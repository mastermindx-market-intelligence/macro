/* MRI display projection only. No fetch, timer, storage, scoring or trade action. */
(function (global) {
  'use strict';
  var labels = {
    cpi_headline_ppi_headline: ['Headline consumer + producer prices', '\u6d88\u8d39\u4e0e\u751f\u4ea7\u4ef7\u683c\uff08\u603b\u4f53\uff09'],
    cpi_core_ppi_headline: ['Core consumer + headline producer prices', '\u6838\u5fc3\u6d88\u8d39\u4ef7\u683c + \u603b\u4f53\u751f\u4ea7\u4ef7\u683c']
  };
  var quadrants = {
    cpi_hot_ppi_hot: ['Both above forecasts', '\u5747\u9ad8\u4e8e\u9884\u671f'],
    cpi_cold_ppi_cold: ['Both below forecasts', '\u5747\u4f4e\u4e8e\u9884\u671f'],
    cpi_hot_ppi_cold: ['Consumer above; producer below', '\u6d88\u8d39\u9ad8\u4e8e\u9884\u671f\uff0c\u751f\u4ea7\u4f4e\u4e8e\u9884\u671f'],
    cpi_cold_ppi_hot: ['Consumer below; producer above', '\u6d88\u8d39\u4f4e\u4e8e\u9884\u671f\uff0c\u751f\u4ea7\u9ad8\u4e8e\u9884\u671f'],
    neutral_or_mixed_neutral: ['At least one matched forecasts', '\u81f3\u5c11\u4e00\u9879\u7b26\u5408\u9884\u671f']
  };
  function bilingual(node, en, zh) {
    node.textContent = '';
    [['l-en', en], ['l-zh', zh]].forEach(function (item) {
      var span = document.createElement('span');
      span.className = item[0];
      span.textContent = item[1];
      node.appendChild(span);
    });
  }
  function boundedAuthority(data) {
    return !!data && data.display_only === true && data.authority &&
      ['can_score', 'can_rank', 'can_gate', 'can_size', 'can_trade'].every(function (key) {
        return data.authority[key] === false;
      });
  }
  function render(host, evidence) {
    if (!host) return;
    var state = host.querySelector('[data-msc-state]');
    var rows = host.querySelector('[data-msc-rows]');
    var quality = host.querySelector('[data-msc-quality]');
    if (!state || !rows || !quality) return;
    rows.textContent = '';
    bilingual(state, 'Forecast comparison unavailable.', '\u6682\u7f3a\u9884\u6d4b\u5bf9\u7167\u3002');
    bilingual(quality, 'Qualified pre-release forecast history is missing.', '\u6682\u7f3a\u53d1\u5e03\u524d\u7559\u5b58\u4e14\u6765\u6e90\u53ef\u6838\u9a8c\u7684\u9884\u6d4b\u6570\u636e\u3002');
    if (!evidence || evidence.schema !== 'release_surprise_confirmation.v1' || !boundedAuthority(evidence)) return;
    var produced = Date.parse(evidence.asof);
    var now = Date.now();
    if (!Number.isFinite(produced) || produced > now || now - produced > 72 * 3600000) {
      bilingual(state, 'Comparison needs a fresh update.', '\u5bf9\u7167\u6570\u636e\u5f85\u66f4\u65b0\u3002');
      bilingual(quality, 'The comparison snapshot is stale or has an invalid clock.', '\u5bf9\u7167\u5feb\u7167\u5df2\u8fc7\u671f\uff0c\u6216\u65f6\u95f4\u8bb0\u5f55\u5f02\u5e38\u3002');
      return;
    }
    if (evidence.status === 'input_invalid') {
      bilingual(state, 'Comparison data needs checking.', '\u5bf9\u7167\u6570\u636e\u5f85\u6838\u67e5\u3002');
      bilingual(quality, 'An input failed integrity checks. Existing release projections remain separate.', '\u8f93\u5165\u6570\u636e\u672a\u901a\u8fc7\u5b8c\u6574\u6027\u68c0\u67e5\uff1b\u539f\u6709\u53d1\u5e03\u9884\u6d4b\u4e0d\u53d7\u6b64\u5bf9\u7167\u5f71\u54cd\u3002');
      return;
    }
    var pairs = Array.isArray(evidence.latest_pairs) ? evidence.latest_pairs.slice(0, 2).filter(function (p) {
      return p && Object.prototype.hasOwnProperty.call(labels, p.pair_id) &&
        Object.prototype.hasOwnProperty.call(quadrants, p.quadrant) &&
        p.display_derived_allowed === true && boundedAuthority({display_only: true, authority: p.authority}) &&
        /^\d{4}-(0[1-9]|1[0-2])$/.test(p.period) &&
        Number.isFinite(Date.parse(p.known_at)) && Date.parse(p.known_at) <= now;
    }) : [];
    if (!pairs.length) {
      if (evidence.status === 'partial') bilingual(state, 'Waiting for both reports.', '\u7b49\u5f85\u4e24\u4efd\u62a5\u544a\u53ca\u5bf9\u5e94\u9884\u671f\u3002');
      if ((evidence.reason_codes || []).indexOf('derived_display_rights_unavailable') !== -1) {
        bilingual(quality, 'Forecast evidence exists, but display rights are not qualified.', '\u5df2\u6709\u9884\u6d4b\u8bb0\u5f55\uff0c\u4f46\u5c55\u793a\u6743\u9650\u5c1a\u672a\u786e\u8ba4\u3002');
      }
      return;
    }
    var current = pairs.filter(function (p) { return p.freshness === 'current' && now - Date.parse(p.known_at) <= 45 * 86400000; });
    if (!current.length) bilingual(state, 'Previous results only.', '\u4ec5\u663e\u793a\u4e4b\u524d\u7684\u5bf9\u7167\u3002');
    else if (current.every(function (p) { return p.agreement === true; })) bilingual(state, 'Reports agree.', '\u4e24\u4efd\u62a5\u544a\u540c\u5411\u504f\u79bb\u9884\u671f\u3002');
    else if (current.every(function (p) { return p.agreement === false; })) bilingual(state, 'Reports disagree.', '\u4e24\u4efd\u62a5\u544a\u504f\u79bb\u9884\u671f\u7684\u65b9\u5411\u4e0d\u540c\u3002');
    else bilingual(state, 'Agreement depends on the measure.', '\u4e0d\u540c\u53e3\u5f84\u7684\u7ed3\u679c\u6709\u522b\u3002');
    pairs.forEach(function (pair) {
      var row = document.createElement('div');
      row.className = 'rr-confirmation-row';
      var name = document.createElement('span');
      var outcome = document.createElement('strong');
      bilingual(name, labels[pair.pair_id][0], labels[pair.pair_id][1]);
      bilingual(outcome, quadrants[pair.quadrant][0], quadrants[pair.quadrant][1]);
      row.appendChild(name); row.appendChild(outcome); rows.appendChild(row);
    });
    var period = pairs[0].period;
    bilingual(quality, 'Reference month: ' + period + '. The entry clock begins after the second report is known; this is not a verified return forecast.',
      '\u6570\u636e\u6240\u5c5e\u6708\u4efd\uff1a' + period + '\u3002\u7b2c\u4e8c\u4efd\u62a5\u544a\u5df2\u77e5\u540e\u624d\u5f00\u59cb\u8ba1\u7b97\u540e\u7eed\u8868\u73b0\uff1b\u8fd9\u4e0d\u662f\u5df2\u9a8c\u8bc1\u7684\u6536\u76ca\u9884\u6d4b\u3002');
  }
  global.MMXReleaseSurprise = Object.freeze({render: render});
})(window);
