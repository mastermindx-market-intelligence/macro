"""Presentation for the additive economy lens. Reuses the existing SVG adapter."""
from copy import deepcopy
import calendar
from engine.china_economy import month_index,month_from_index
from engine.china_macro_evidence_view import chart_svg

STATE_WORDS={
 'production':{'above':('Output growing','产出增长'),'below':('Output declining','产出下降')},
 'households':{'above':('Spending growing','支出增长'),'below':('Spending declining','支出下降')},
 'investment':{'above':('Investment growing','投资增长'),'below':('Investment falling','投资下降')},
 'housing':{'above':('New building growing','新建市场增长'),'below':('New building weak','新建市场走弱')},
 'external':{'above':('Exports growing','出口增长'),'below':('Exports falling','出口下降')},
 'employment':{'above':('Hiring surveys above 50','用工调查高于50'),'below':('Hiring surveys below 50','用工调查低于50')},
}
UNIT_WORDS={
 '% YoY':('vs last year','同比'),'% YTD YoY':('year to date · vs last year','年内累计同比'),
 '% YoY CNY':('vs last year · CNY','人民币同比'),'% MoM SA':('monthly · seasonally adjusted','季调环比'),
 'index':('survey · 50 = no change','调查 · 50为无变化'),'% YTD YoY real':('year-to-date real growth','年内累计实际增速'),
}
UNIT_WORDS.update({
 '%':('%','%'),'% YoY stock':('stock · vs last year','存量同比'),
 'CNY bn / month':('CNY bn / month','十亿元人民币／月'),
 'CNY bn YTD':('CNY bn · year to date','十亿元人民币·年内累计'),
 'CNY tn':('CNY tn','万亿元人民币'),'days':('days','天'),
 'days YoY change':('days · vs last year','天·同比变化'),
 'of 41':('of 41 industries','／41个行业'),'of 626':('of 626 products','／626种产品'),
 'percentage points':('percentage points','个百分点'),'index points':('index points','指数点'),
 'index points/month':('index points/month','指数点／月'),
 'index points/month²':('index points/month²','指数点／月²'),
 'percentage points/month':('percentage points/month','个百分点／月'),
 'percentage points/month²':('percentage points/month²','个百分点／月²'),
})


def comparison_periods(period):
 end=month_index(period)
 def labels(start,stop):
  a,b=month_from_index(start),month_from_index(stop)
  am,bm=int(a[-2:]),int(b[-2:])
  en=(f'{calendar.month_abbr[am]}–{calendar.month_abbr[bm]} {b[:4]}' if a[:4]==b[:4]
      else f'{calendar.month_abbr[am]} {a[:4]}–{calendar.month_abbr[bm]} {b[:4]}')
  zh=f'{a[:4]}年{am}月至{bm}月' if a[:4]==b[:4] else f'{a[:4]}年{am}月至{b[:4]}年{bm}月'
  return en,zh
 a,b=labels(end-2,end),labels(end-5,end-3)
 return a[0]+' versus '+b[0],a[1]+'对比'+b[1]


def prepare_economy_view(economy):
 v=deepcopy(economy)
 v['snapshot_date']=v['as_of'][:10]
 v['comparison_en'],v['comparison_zh']=comparison_periods(v['reference_period'])
 for m in v['metrics'].values():
  m['chart_svg']=chart_svg(m,120)
  m['unit_en'],m['unit_zh']=UNIT_WORDS.get(m['unit'],(m['unit'],m['unit']))
  m['change_unit_en'],m['change_unit_zh']=UNIT_WORDS.get(m['change_unit'],(m['change_unit'],m['change_unit']))
  m['value_text']=m['display']+('%' if m['unit'].startswith('%') else '')
  p=m['pace']
  for key in ['slope_unit','acceleration_unit']:
   unit=p.get(key) or '—';p[key+'_en'],p[key+'_zh']=UNIT_WORDS.get(unit,(unit,unit))
  for key in ['current_3m','previous_3m','change_in_pace','slope_recent_3m','acceleration']:
   p[key+'_display']=f'{p[key]:+,.2f}' if p[key] is not None else '—'
  w=p.get('window_sensitivity')
  if w:
   for key in ['current_2m','previous_2m','change_in_pace_2m']:w[key+'_display']=f'{w[key]:+,.2f}' if w[key] is not None else '—'
  m['tail_rows']=[{'date':d[:7],'value':'—' if n is None else f'{n:,.2f}'} for d,n in zip(m['chart']['dates'],m['chart']['vals'])]
 for d in v['domains']:
  words=STATE_WORDS[d['id']].get(d['state'],(d['state_en'],d['state_zh']))
  d['plain_state_en'],d['plain_state_zh']=words
  d['metric']=v['metrics'][d['headline_metric']]
  d['symbol']={'improving':'↗','fading':'↘','steady':'→','mixed':'↔','unknown':'—'}[d['momentum']]
 v['pace_cards']=[v['metrics'][k] for k in ['industrial_sa','retail_sa','investment_sa']]
 windows=[m['pace'].get('window_sensitivity') for m in v['pace_cards']]
 v['all_three_shorter_windows_weaker']=(all(w and w.get('direction_2m')=='fading' for w in windows)
    and all(m['pace']['direction']=='improving' for m in v['pace_cards']))
 v['default_chart']=v['metrics']['industrial_sa']
 # Categorical placement only; there are no invented quantitative coordinates.
 v['phase_groups']={key:[] for key in ['above_improving','above_fading','below_improving','below_fading','other']}
 for k in ['industrial_sa','retail_sa','investment_sa','housing_sales_area','housing_starts','pmi_orders','pmi_exports','pmi_nonmfg']:
  m=v['metrics'][k];state=m['state']
  if m['kind']=='sa_mom':
   level=m['pace']['current_3m'];state='unknown' if level is None else 'above' if level>0 else 'below' if level<0 else 'at_reference'
  key=state+'_'+m['pace']['direction']
  if key not in v['phase_groups']:key='other'
  v['phase_groups'][key].append(m)
 # Full metrics remain in the drill-down; the primary surface is intentionally small.
 v['context_cards']=[
  {'title_en':'Small-firm pressure','title_zh':'小企业压力','group':'orders','ids':['pmi_large','pmi_small'],
   'note_en':'Different-sized firms, different conditions.','note_zh':'企业规模不同，景气状态不同。'},
  {'title_en':'Prices & costs','title_zh':'价格与成本','group':'prices','ids':['cpi','ppi','purchase_prices'],
   'note_en':'Inflation is a separate axis—not a growth vote.','note_zh':'通胀单独呈现，不混入增长票。'},
  {'title_en':'Fiscal cash flows','title_zh':'财政收支','group':'fiscal','ids':['fiscal_general_spending_growth','fiscal_land_revenue_growth'],
   'note_en':'Spending and land receipts are different channels.','note_zh':'支出与土地收入是不同渠道。'},
  {'title_en':'Profit versus cash','title_zh':'利润与回款','group':'corporate','ids':['profits_ytd','receivable_days','cashdays_change'],
   'note_en':'Profit growth does not prove faster cash collection.','note_zh':'利润增长不等于回款加快。'},
  {'title_en':'Physical cross-check','title_zh':'实物交叉核验','group':'physical','ids':['power_industrial','power_datacenters'],
   'note_en':'Electricity is contextual and weather-sensitive.','note_zh':'用电仅作背景，受天气影响。'},
  {'title_en':'Regional dispersion','title_zh':'区域分化','group':'regions','ids':['regional_investment_east','regional_investment_northeast'],
   'note_en':'Investment only—not a regional GDP map.','note_zh':'仅投资数据，不是区域GDP地图。'},
  {'title_en':'External cash flows','title_zh':'涉外收付款','group':'external','ids':['external_receipts','external_payments'],
   'note_en':'Monthly bank-client receipts and payments—not equity buying.','note_zh':'月度银行代客收付款，不是股票买入。'},
  {'title_en':'Goods & services','title_zh':'商品与服务','group':'households','ids':['retail_yoy','services_retail_ytd'],
   'note_en':'Monthly retail and year-to-date services: keep the periods separate.','note_zh':'社零为当月，服务为年内累计，时期必须区分。'},
  {'title_en':'Profit dispersion','title_zh':'利润分化','group':'corporate','ids':['sector_profit_electronics','sector_profit_auto'],
   'note_en':'Year-to-date industrial profits—not an earnings forecast.','note_zh':'年内累计工业利润，不是盈利预测。'},
 ]
 return v


def client_publication(publication, *, include_metrics=True):
 """Bound the HTML projection; the complete evidence stays behind its data URL."""
 economy=publication.get('economy')
 if not include_metrics:
  return {'economy':None,'detail_href':'china_economy_detail.json',
          'download_href':'china_macro_evidence.json',
          'projection':'public_shell_locked_detail'}
 if not isinstance(economy,dict):
  return {'economy':None,'download_href':'china_macro_evidence.json'}
 keys=('schema','input_class','reference_period','authority')
 data={k:deepcopy(economy.get(k)) for k in keys}
 data['groups']=[{'id':g['id']} for g in economy.get('groups',[])]
 data['metrics']={ident:{k:deepcopy(m[k]) for k in ('chart','unit','definition_id')}
                  for ident,m in economy.get('metrics',{}).items()}
 return {'economy':data,'download_href':'china_macro_evidence.json',
         'projection':'client_interaction_only_not_full_evidence'}
