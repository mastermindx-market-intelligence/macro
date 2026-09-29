/* Presentation only. No fetching, signal calculation, persistence or trading effects. */
(function () {
  'use strict';
  function csvCell(value) {
    if (value === null || value === undefined) return '';
    if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '';
    var text = String(value);
    if (/^[=+@\-\t\r]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }
  function seriesCsv(metric, inputClass) {
    var out = [['reference_month', metric.unit, 'definition', 'input_class'].map(csvCell).join(',')];
    metric.chart.dates.forEach(function (date, i) {
      out.push([date.slice(0, 7), metric.chart.vals[i], metric.definition_id,
        inputClass || 'input_class_not_supplied'].map(csvCell).join(','));
    });
    return '\uFEFF' + out.join('\r\n');
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {csvCell:csvCell, seriesCsv:seriesCsv};
  if (typeof document === 'undefined') return;
  var root = document.getElementById('china-economy');
  var tag = document.getElementById('eco-json');
  if (!root || !tag) return;
  var publication;
  try { publication = JSON.parse(tag.textContent); } catch (error) { return; }
  var data = publication.economy;
  if (!data || data.schema !== 'mastermind.china_economy_lens.v1' || !data.metrics || !Array.isArray(data.groups)) return;
  var selected = 'industrial_sa';
  var select = document.getElementById('eco-metric-select');
  if (!select || !document.getElementById('eco-export')) return;
  function selectMetric(id, scroll) {
    if (!Object.prototype.hasOwnProperty.call(data.metrics, id)) return;
    var template = document.getElementById('eco-template-' + id);
    var target = document.getElementById('eco-selected-metric');
    if (!template || !target) return;
    target.replaceChildren(template.content.cloneNode(true));
    selected = id; select.value = id;
    translateControls(document.documentElement.dataset.lang);
    if (scroll) {
      document.getElementById('eco-explorer').scrollIntoView({block:'start',behavior:'auto'});
      select.focus({preventScroll:true});
    }
  }
  function selectGroup(id, scroll) {
    if (!data.groups.some(function(g){return g.id===id;})) return;
    root.querySelectorAll('[data-eco-group-panel]').forEach(function(p){p.hidden=p.dataset.ecoGroupPanel!==id;});
    root.querySelectorAll('.eco-group-tabs [data-eco-group]').forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.ecoGroup===id));});
    if (scroll) document.getElementById('eco-library').scrollIntoView({block:'start',behavior:'auto'});
  }
  root.addEventListener('click',function(event){
    var pick=event.target.closest('[data-eco-select]');
    if (pick && root.contains(pick)) {selectMetric(pick.dataset.ecoSelect,true);return;}
    var group=event.target.closest('[data-eco-group]');
    if (group && root.contains(group)) selectGroup(group.dataset.ecoGroup,!group.closest('.eco-group-tabs'));
  });
  select.addEventListener('change',function(){selectMetric(select.value,false);});
  function save(contents,type,filename){
    var url=URL.createObjectURL(new Blob([contents],{type:type}));
    var a=document.createElement('a');a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();
    setTimeout(function(){URL.revokeObjectURL(url);},2000);
  }
  document.getElementById('eco-export').addEventListener('click',function(){
    save(seriesCsv(data.metrics[selected], data.input_class),'text/csv;charset=utf-8','china-economy-'+selected+'-'+data.reference_period+'.csv');
  });
  var jsonButton=document.getElementById('eco-export-json');
  if (jsonButton) jsonButton.addEventListener('click',function(){
    // Production downloads the complete canonical contract, not the smaller
    // interaction projection. The offline review still exports its full input.
    if (publication.download_href === 'china_macro_evidence.json') {
      var a=document.createElement('a');a.href=publication.download_href;
      a.download='china-macro-evidence.json';document.body.appendChild(a);a.click();a.remove();
    } else save(JSON.stringify(publication,null,2),'application/json','china-economy-evidence.json');
  });
  function translateControls(lang){
    lang=lang==='zh'?'zh':'en';
    select.querySelectorAll('option,optgroup').forEach(function(item){var text=item.dataset[lang];if (!text)return;if(item.tagName==='OPTGROUP')item.label=text;else item.textContent=text;});
    root.querySelectorAll('[data-aria-en]').forEach(function(item){item.setAttribute('aria-label',item.dataset[lang==='zh'?'ariaZh':'ariaEn']);});
  }
  function language(lang){
    lang=lang==='zh'?'zh':'en';document.documentElement.dataset.lang=lang;document.documentElement.lang=lang==='zh'?'zh-CN':'en';
    translateControls(lang);
  }
  // Follow the existing site-wide language control; do not create a second
  // saved language preference or navigation owner.
  if (typeof MutationObserver!=='undefined') {
    new MutationObserver(function(){translateControls(document.documentElement.dataset.lang);})
      .observe(document.documentElement,{attributes:true,attributeFilter:['data-lang']});
  }
  window.EconomyLens={setLanguage:language,selectMetric:selectMetric,selectGroup:selectGroup};
  language(document.documentElement.dataset.lang || 'en');
})();
