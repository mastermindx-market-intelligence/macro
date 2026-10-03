from copy import deepcopy
from pathlib import Path
import json,sys,re,subprocess
import pytest
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine.china_economy import build_economy
from engine.china_economy_view import prepare_economy_view
from scripts.preview_china_economy import render
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def doc():return json.loads((Path(__file__).resolve().parent/'fixtures/china_economy_review.json').read_text())
@pytest.fixture
def html(doc,tmp_path):
 # Existing four-panel reviewed data remains unchanged in the composed preview.
 # On the canonical repo this preview-only fixture can be omitted by selecting
 # pure component tests; the base contract is created empty for this unit case.
 from engine.china_macro_evidence import build_snapshot
 from datetime import date
 base=build_snapshot(lambda g,n:None,date(2026,9,29))
 return render(doc,base,tmp_path).read_text()

def test_views_are_deep_copied(doc):
 s=build_economy(doc);original=deepcopy(s);v=prepare_economy_view(s)
 assert s==original and v['metrics']['industrial_sa']['chart_svg'].startswith('<svg')
 assert 'chart_svg' not in s['metrics']['industrial_sa']

def test_single_point_never_becomes_curve(doc):
 v=prepare_economy_view(build_economy(doc))
 assert v['metrics']['cpi']['chart_svg']==''
 assert 'grow' not in v['metrics']['cpi']['chart_svg']

def test_preview_strict_and_unique_ids(html):
 soup=BeautifulSoup(html,'html.parser');ids=[e['id'] for e in soup.select('[id]')]
 assert len(ids)==len(set(ids))
 assert len(soup.select('.eco-domain[id]'))==6
 assert len(soup.select('.eco-pace-card'))==3
 assert len(soup.select('[id^="eco-template-"]'))==128

def test_primary_state_direction_units_preserved(html):
 assert 'Growth remains uneven.' in html
 assert 'Window-sensitive' in html
 assert 'percentage points/month²' in html
 assert 'Change in reading' in html and 'percentage points' in html

def test_default_chart_is_ssr_not_js_only(html):
 soup=BeautifulSoup(html,'html.parser')
 assert soup.select_one('#eco-selected-metric svg') is not None

def test_no_remote_dependencies(html):
 soup=BeautifulSoup(html,'html.parser')
 assert not soup.select('script[src]') and not soup.select('link[rel="stylesheet"]')

def test_four_original_dialogs_survive(html):
 soup=BeautifulSoup(html,'html.parser')
 for key in ['policy','property','flows','sentiment']:assert soup.find(id='cnx-dlg-'+key) is not None

def test_bilingual_and_theme_controls(html):
 assert '增长仍然分化。' in html and 'data-theme="dark"' in html
 assert 'html[data-theme=light]' in html
 assert 'prefers-reduced-motion' in html
 assert 'focus-visible' in html

def test_csv_is_safe_and_preserves_negatives():
 path=ROOT/'templates/china-economy.js'
 code=f"const x=require({json.dumps(str(path))}); console.log(JSON.stringify([x.csvCell('=2+3'), x.csvCell(-2.3), x.csvCell(null)]));"
 result=json.loads(subprocess.check_output(['node','-e',code],text=True))
 assert result==['"\'=2+3"','-2.3','']

def test_json_has_no_svg_or_markup(html):
 soup=BeautifulSoup(html,'html.parser');x=json.loads(soup.find(id='eco-json').string)
 assert 'economy' in x and x['economy']['schema']=='mastermind.china_economy_lens.v1'
 assert 'chart_svg' not in x['economy']['metrics']['pmi_mfg']

def test_no_false_source_history_drawn(doc):
 v=prepare_economy_view(build_economy(doc));m=v['metrics']['exports_cny']
 assert m['chart']['vals'][1] is None
 assert m['chart_svg'].count('<path')==2 # gap is not joined

def test_source_label_injection_escaped(doc,tmp_path):
 from engine.china_macro_evidence import build_snapshot
 from datetime import date
 doc['catalog']['industrial_sa']['label_en']='</script><img src=x onerror=alert(1)>'
 html=render(doc,build_snapshot(lambda g,n:None,date(2026,9,29)),tmp_path).read_text()
 soup=BeautifulSoup(html,'html.parser')
 assert not soup.find('img',onerror=True)
 assert json.loads(soup.find(id='eco-json').string)['economy']['metrics']['industrial_sa']['label_en'].startswith('</script>')

def test_css_scoped_no_parallel_global_tokens():
 css=(ROOT/'templates/china-economy.css').read_text()
 assert ':root' not in css and '--bg:' not in css
 assert '.eco' in css and 'minmax(0,1fr)' in css

def test_deep_hydration_uses_only_the_existing_same_origin_boundary():
 js=(ROOT/'templates/china-economy.js').read_text()
 assert "fetch(detailHref" in js
 assert "credentials:'same-origin'" in js and "cache:'no-store'" in js
 assert "detailHref !== 'china_economy_detail.json'" in js
 assert 'XMLHttpRequest' not in js and 'localStorage' not in js

def test_html5_options_do_not_contain_spans(html):
 soup=BeautifulSoup(html,'html.parser')
 assert not any(option.find('span') for option in soup.select('#eco-metric-select option'))

@pytest.mark.parametrize('period,words',[
 ('2026-08','Jun–Aug 2026 versus Mar–May 2026'),
 ('2027-02','Dec 2026–Feb 2027 versus Sep–Nov 2026'),
 ('2027-06','Apr–Jun 2027 versus Jan–Mar 2027'),
])
def test_comparison_labels_follow_reference_not_demo_date(period,words):
 from engine.china_economy_view import comparison_periods
 assert comparison_periods(period)[0]==words


def test_rollover_uses_latest_published_pace_period_and_labels_assessment_month(doc):
 from jinja2 import Environment,FileSystemLoader,StrictUndefined
 economy=build_economy(doc,as_of='2026-10-02T10:00:00+08:00',reference_period='2026-09')
 view=prepare_economy_view(economy)
 assert view['pace_reference_periods']==['2026-08']
 assert view['pace_latest_period']=='2026-08'
 assert view['pace_all_current'] is False
 assert view['comparison_en']=='Jun–Aug 2026 versus Mar–May 2026'
 e=Environment(loader=FileSystemLoader(ROOT/'templates'),undefined=StrictUndefined)
 tpl=e.from_string('{% macro t(a,b) %}{{ a }}{% endmacro %}{% import "_china_economy_lens.html.j2" as eco with context %}{{ eco.lens(E,shell="public") }}')
 text=tpl.render(E=view)
 soup=BeautifulSoup(text,'html.parser')
 top=soup.select_one('.eco-topline').get_text(' ',strip=True)
 assert 'Assessment month 2026-09' in top
 assert 'through Aug 2026' in soup.select_one('.eco-key').get_text(' ',strip=True)
 production=soup.select_one('#eco-domain-production .eco-domain-reading small').get_text(' ',strip=True)
 assert 'ref 2026-08' in production


def test_missing_activity_never_claims_zero_improvement_or_window_sensitivity(doc,tmp_path):
 from engine.china_macro_evidence import build_snapshot
 from datetime import date
 doc['observations']=[]
 html=render(doc,build_snapshot(lambda g,n:None,date(2026,9,29)),tmp_path).read_text()
 soup=BeautifulSoup(html,'html.parser')
 assert 'Activity-pace history unavailable' in soup.select_one('.eco-key').get_text()
 assert not soup.select('.eco-sensitive')
 assert '2026-09-29' in soup.select_one('.eco-topline').get_text()

def test_window_warning_not_hardcoded_when_signs_reverse(doc):
 e=build_economy(doc)
 for k in ['industrial_sa','retail_sa','investment_sa']:
  e['metrics'][k]['pace']['direction']='fading'
  e['metrics'][k]['pace']['window_sensitivity']['direction_2m']='improving'
 assert not prepare_economy_view(e)['all_three_shorter_windows_weaker']

def test_csv_origin_is_not_fixed_to_review_input():
 path=ROOT/'templates/china-economy.js'
 metric={'unit':'%','definition_id':'test','chart':{'dates':['2026-08-01'],'vals':[-.5]}}
 code=f"const x=require({json.dumps(str(path))});console.log(x.seriesCsv({json.dumps(metric)},'existing_parquet_owners_with_publication_receipts'));"
 csv=subprocess.check_output(['node','-e',code],text=True)
 assert 'existing_parquet_owners_with_publication_receipts' in csv
 assert 'source-checked review' not in csv and '-0.5' in csv

def test_production_component_preserves_heading_hierarchy(doc):
 from jinja2 import Environment,FileSystemLoader,StrictUndefined
 e=Environment(loader=FileSystemLoader(ROOT/'templates'),undefined=StrictUndefined)
 text=e.from_string('{% macro t(a,b) %}{{ a }}{% endmacro %}{% import "_china_economy_lens.html.j2" as eco with context %}{{ eco.lens(E) }}').render(E=prepare_economy_view(build_economy(doc)))
 soup=BeautifulSoup(text,'html.parser')
 assert soup.find(id='eco-title').name=='h2' and not soup.find('h1')

def test_public_shell_contains_state_but_not_deep_metric_library(doc):
 from jinja2 import Environment,FileSystemLoader,StrictUndefined
 e=Environment(loader=FileSystemLoader(ROOT/'templates'),undefined=StrictUndefined)
 tpl=e.from_string('{% macro t(a,b) %}{{ a }}{% endmacro %}{% import "_china_economy_lens.html.j2" as eco with context %}{{ eco.lens(E,shell="public") }}')
 text=tpl.render(E=prepare_economy_view(build_economy(doc)))
 soup=BeautifulSoup(text,'html.parser')
 assert len(soup.select('.eco-domain[id]'))==6 and len(soup.select('.eco-pace-card'))==3
 assert soup.select_one('#eco-detail-lock') is not None
 assert soup.select_one('#eco-explorer') is None and soup.select_one('#eco-library') is None
 assert not soup.select('[id^="eco-template-"]')
 source_link=soup.select_one('.eco-topline a[href="https://www.stats.gov.cn/"]')
 assert source_link is not None and 'National Bureau of Statistics of China' in source_link.get_text()

def test_protected_deep_fragment_has_library_without_duplicate_outer_shell(doc):
 from jinja2 import Environment,FileSystemLoader,StrictUndefined
 e=Environment(loader=FileSystemLoader(ROOT/'templates'),undefined=StrictUndefined)
 tpl=e.from_string('{% macro t(a,b) %}{{ a }}{% endmacro %}{% import "_china_economy_lens.html.j2" as eco with context %}{{ eco.lens(E,shell="deep") }}')
 text=tpl.render(E=prepare_economy_view(build_economy(doc)))
 soup=BeautifulSoup(text,'html.parser')
 assert soup.find(id='china-economy') is None and soup.find(id='eco-detail-lock') is None
 assert soup.find(id='eco-explorer') is not None and soup.find(id='eco-library') is not None
 assert len(soup.select('[id^="eco-template-"]'))==128

def test_error_contract_and_shared_language_handling_are_explicit():
 js=(ROOT/'templates/china-economy.js').read_text()
 assert '!data.metrics' in js and '!select' in js
 assert "attributeFilter:['data-lang']" in js
 assert 'localStorage' not in js


def test_offline_preview_reuses_canonical_evidence_palette():
 from scripts.preview_china_macro_evidence import evidence_theme_tokens
 import re
 tokens=evidence_theme_tokens()
 theme=(ROOT/'templates/theme.css').read_text()
 for css_name in ('china-economy.css','china-macro-evidence.css'):
  css=(ROOT/'templates'/css_name).read_text()
  for name in re.findall(r'var\((--(?:r-evidence|evidence)-[a-z-]+)\)',css):
   declaration=re.search(re.escape(name)+r'\s*:[^;{}]+;',theme)
   assert declaration is not None,name
   assert declaration.group(0) in tokens,name
 assert '--font-ui:' in tokens
