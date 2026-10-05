"""Strict pure parsers to enrich existing China collectors, not a new scheduler.

Network acquisition, throttling, storage upserts and release publication remain
with collectors.base / china_macro / china_property and the existing site build.
These helpers reject missing core fields, malformed periods and source changes.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from engine.china_economy import month_end, month_index, number, timestamp

ALLOWED_HOSTS={'www.stats.gov.cn','m.mof.gov.cn','www.mof.gov.cn','www.nea.gov.cn','www.safe.gov.cn'}
PMI_COLUMNS={
 'PMI':'pmi_mfg','生产':'pmi_output','新订单':'pmi_orders','原材料库存':'pmi_raw_inventory',
 '从业人员':'pmi_jobs','供应商配送时间':'pmi_delivery','新出口订单':'pmi_exports','进口':'pmi_imports',
 '采购量':'pmi_purchases','主要原材料购进价格':'pmi_input_prices','出厂价格':'pmi_output_prices',
 '产成品库存':'pmi_finished_inventory','在手订单':'pmi_backlog','生产经营活动预期':'pmi_expectations'}
NONMFG_COLUMNS={'商务活动':'pmi_nonmfg','新订单':'pmi_nonmfg_orders','投入品价格':'pmi_nonmfg_costs',
 '销售价格':'pmi_nonmfg_prices','从业人员':'pmi_nonmfg_jobs','业务活动预期':'pmi_nonmfg_expectations'}


def compact(s):return re.sub(r'\s+','',s).replace('（','(').replace('）',')').replace('−','-').replace('，',',')


def checked_source(url:str,published_at:str,observed_at:str|None=None,html:str='')->dict:
    u=urlparse(url)
    if u.scheme!='https' or u.hostname not in ALLOWED_HOSTS or u.username or u.password or u.port not in (None,443):
        raise ValueError('unapproved origin; do not switch providers')
    published=timestamp(published_at)
    observed=timestamp(observed_at) if observed_at else datetime.now(timezone.utc)
    if published>observed:raise ValueError('publication is in the future')
    return {'url':url,'published_at':published.isoformat(),'observed_at':observed.isoformat(),
            'response_sha256':hashlib.sha256(html.encode()).hexdigest(),'original_vintage':False}


def expand_table(table)->list[list[str]]:
    """Expand row/col spans without carrying content across unrelated tables."""
    pending={};out=[]
    for ri,tr in enumerate(table.find_all('tr')):
        row=[];ci=0
        def carry():
            nonlocal ci
            while (ri,ci) in pending:
                row.append(pending.pop((ri,ci)));ci+=1
        carry()
        for cell in tr.find_all(['td','th'],recursive=False):
            carry();text=compact(cell.get_text(' ',strip=True))
            rs=int(cell.get('rowspan',1));cs=int(cell.get('colspan',1))
            if not (1<=rs<=100 and 1<=cs<=30):raise ValueError('invalid table span')
            for j in range(cs):
                row.append(text)
                for k in range(1,rs):pending[(ri+k,ci+j)]=text
            ci+=cs
        carry()
        if row:out.append(row)
    return out


def publisher_article_root(html: str):
    """NBS desktop/mobile duplicates must agree before choosing one article.

    Not generic duplicate suppression: duplicate tables in one article still
    fail the parsers, and a disagreeing mobile edition is a publication hold.
    """
    soup = BeautifulSoup(html, 'html.parser')
    desktop = soup.select('.detail-text-content .txt-content')
    mobile = soup.select('.mobile-content .mobile-news-content')
    if len(desktop) > 1 or len(mobile) > 1:
        raise ValueError('ambiguous publisher article containers')
    if desktop and mobile:
        a, b = desktop[0], mobile[0]
        if compact(a.get_text(' ', strip=True)) != compact(b.get_text(' ', strip=True)):
            raise ValueError('publisher desktop/mobile text disagree')
        if [expand_table(t) for t in a.find_all('table')] != [expand_table(t) for t in b.find_all('table')]:
            raise ValueError('publisher desktop/mobile tables disagree')
    return desktop[0] if desktop else mobile[0] if mobile else soup


def _parse_date(cells,year):
    joined=''.join(cells[:2]);m=re.search(r'(20\d{2})年',joined)
    if m:year=int(m[1])
    mm=re.search(r'(?<!\d)(1[0-2]|[1-9])月',joined)
    if year is None or mm is None:return None,year
    return f'{year:04}-{int(mm[1]):02}',year


def parse_sa_html(html:str,metric_id:str,expected_period:str)->list[dict]:
    """Read the explicit REVISED monthly-rate table, not an image or YoY table."""
    if metric_id not in {'industrial_sa','retail_sa','investment_sa'}:raise ValueError('not an admitted SA metric')
    month_index(expected_period)
    article=publisher_article_root(html)
    text=compact(article.get_text())
    if '季节调整' not in text and '季调' not in text:raise ValueError('seasonal-adjustment declaration missing')
    candidates=[]
    for table in publisher_article_root(html).find_all('table'):
        rows=expand_table(table)
        if not rows:continue
        header=next((i for i,r in enumerate(rows[:4]) if any('环比增速' in c for c in r)),None)
        if header is None:continue
        year=None;points=[]
        for r in rows[header+1:]:
            period,year=_parse_date(r,year)
            if period is None:continue
            v=number(r[-1].replace('%',''))
            if v is None or v<=-100:raise ValueError('invalid SA observation')
            points.append({'metric_id':metric_id,'period':period,'value':v})
        if points:candidates.append(points)
    if len(candidates)!=1:raise ValueError('exactly one SA monthly table required')
    points=candidates[0]
    periods=[p['period'] for p in points]
    if len(set(periods))!=len(periods):raise ValueError('duplicate monthly observation')
    indices=[month_index(p) for p in periods]
    if indices!=list(range(indices[0],indices[-1]+1)):raise ValueError('missing or unsorted month in SA table')
    if periods[-1]!=expected_period:raise ValueError('wrong release reference period')
    if len(points)<6:raise ValueError('insufficient seasonal-history rows')
    return points


def parse_pmi_html(html:str,expected_period:str)->list[dict]:
    """Parse manufacturer 1/2 and non-manufacturer 3 tables by labels, not offsets."""
    month_index(expected_period)
    allrows=[]
    for table in publisher_article_root(html).find_all('table'):
        expanded=expand_table(table)
        if not expanded:continue
        header_ix=None;mapping=None;cols={}
        for j,r in enumerate(expanded[:4]):
            if 'PMI' in r and '生产' in r and '从业人员' in r: mapping=PMI_COLUMNS
            elif '主要原材料购进价格' in r:mapping=PMI_COLUMNS
            elif '商务活动' in r and '业务活动预期' in r:mapping=NONMFG_COLUMNS
            else:continue
            cols={i:mapping[c] for i,c in enumerate(r) if c in mapping}
            header_ix=j;break
        if header_ix is None:continue
        year=None
        for r in expanded[header_ix+1:]:
            period,year=_parse_date(r,year)
            if period is None:continue
            for i,k in cols.items():
                if i>=len(r):raise ValueError('truncated PMI row')
                v=number(r[i])
                if v is None or not 0<=v<=100:raise ValueError('invalid PMI diffusion observation')
                allrows.append({'metric_id':k,'period':period,'value':v})
    required={'pmi_mfg','pmi_orders','pmi_exports','pmi_input_prices','pmi_nonmfg','pmi_jobs','pmi_nonmfg_jobs'}
    by={}
    for r in allrows:
        key=(r['metric_id'],r['period'])
        if key in by:raise ValueError('duplicate PMI series and month')
        by[key]=r
    if not required<={r['metric_id'] for r in allrows}:raise ValueError('PMI table family incomplete')
    for metric in {r['metric_id'] for r in allrows}:
        periods=sorted(r['period'] for r in allrows if r['metric_id']==metric)
        inds=[month_index(s) for s in periods]
        if periods[-1]!=expected_period or inds!=list(range(inds[0],inds[-1]+1)) or len(inds)<6:
            raise ValueError('PMI history period/continuity failed')
    return sorted(allrows,key=lambda r:(r['metric_id'],r['period']))


# Exact national concepts: amounts and growth must come from the SAME clause.
FISCAL_PHRASES={
 'general_revenue':'全国一般公共预算收入', 'general_spending':'全国一般公共预算支出',
 'fund_revenue':'全国政府性基金预算收入','fund_spending':'全国政府性基金预算支出',
 'land_revenue':'国有土地使用权出让收入', 'interest_spending':'债务付息支出',
}


def parse_mof_text(text:str,expected_period:str)->list[dict]:
    normalized=compact(text)
    y,m=map(int,expected_period.split('-'))
    if f'{y}年' not in normalized or not re.search(fr'1[—–-]{m}月',normalized):raise ValueError('fiscal reference period missing')
    out=[]
    for stem,label in FISCAL_PHRASES.items():
        # Revenue may use '同比增长'; spending often just '增长'. Require a word,
        # never use a minus sign heuristic or pull the next paragraph's growth.
        pat=rf'{label}([\d,.]+)亿元,?(?:同比)?(增长|下降)([\d.]+)%'
        found=re.findall(pat,normalized)
        if len(found)!=1:raise ValueError('missing or duplicate fiscal clause: '+stem)
        amount,word,rate=found[0];amount=number(amount.replace(',',''));rate=number(rate)
        if amount is None or amount<0 or rate is None:raise ValueError('invalid fiscal value')
        out.extend([{'metric_id':'fiscal_'+stem,'period':expected_period,'value':amount/10},
                    {'metric_id':'fiscal_'+stem+'_growth','period':expected_period,'value':rate*(-1 if word=='下降' else 1)}])
    return out


def stamp_observations(points:list[dict],source_id:str,receipt:dict,catalog:dict)->list[dict]:
    """Attach actual acquisition receipt; no pretending review data is HTTP data."""
    out=[]
    for p in points:
        meta=catalog[p['metric_id']]
        out.append({**p,'source_id':source_id,'published_at':receipt['published_at'],
            'vintage_id':receipt['response_sha256'],'definition_id':meta['definition_id'],
            'period_end':month_end(p['period']).isoformat(),'observed_at':receipt['observed_at'],
            'raw_response_sha256':receipt['response_sha256'],'ingestion_class':'existing_collector_http_receipt'})
    return out


def parse_safe_text(text:str,expected_period:str)->list[dict]:
    """SAFE monthly CNY cash series; never captures USD or year-to-date totals."""
    month_index(expected_period);year,month=map(int,expected_period.split('-'));s=compact(text)
    a=re.findall(rf'{year}年{month}月,银行结汇([\d,.]+)亿元人民币,售汇([\d,.]+)亿元人民币',s)
    b=re.findall(rf'{year}年{month}月,银行代客涉外收入([\d,.]+)亿元人民币,对外付款([\d,.]+)亿元人民币',s)
    if len(a)!=1 or len(b)!=1:raise ValueError('exact monthly CNY SAFE clauses required')
    vals=[number(x.replace(',','')) for x in a[0]+b[0]]
    if any(v is None or v<0 for v in vals):raise ValueError('invalid SAFE amount')
    return [{'metric_id':k,'period':expected_period,'value':v/10} for k,v in zip(['fx_surrender','fx_purchase','external_receipts','external_payments'],vals)]


def _matched_number(text:str,pattern:str,label:str):
    matches=re.findall(pattern,text)
    if len(matches)!=1:
        raise ValueError('missing or ambiguous national clause: '+label)
    v=number(matches[0])
    if v is None:raise ValueError('nonfinite national value: '+label)
    return v


def _change_clause(text:str,pattern:str,label:str):
    matches=re.findall(pattern,text)
    if len(matches)!=1:raise ValueError('missing or ambiguous change clause: '+label)
    direction,value,unit=matches[0];v=number(value)
    if v is None or v<0:raise ValueError('invalid unsigned change: '+label)
    return v*(100 if unit=='倍' else 1)*(-1 if direction in {'下降','减少','降低'} else 1)


def parse_corporate_text(text:str,expected_period:str)->list[dict]:
    """NBS above-designated-size national industry only; not all companies.

    Reads labeled prose, not positional accounting tables. A missing field,
    repeated clause or changed unit fails this source family without guessing.
    Ownership subsets are NOT summed; sector percentages are not contributions.
    """
    month_index(expected_period);year,month=map(int,expected_period.split('-'))
    s=compact(text)
    if not re.search(rf'{year}年1[—–-]{month}月份',s):raise ValueError('corporate reference period missing')
    out={}
    specifications={
      'profits_ytd':r'全国规模以上工业企业实现利润总额[\d.]+亿元,同比(增长|下降)([\d.]+)(%)',
      'profits_month':rf'(?<![\d—–-]){month}月份,规模以上工业企业利润同比(增长|下降)([\d.]+)(%)',
      'revenue_ytd':r'规模以上工业企业实现营业收入[\d.]+万亿元,同比(增长|下降)([\d.]+)(%)',
      'receivables_yoy':r'规模以上工业企业应收账款[\d.]+万亿元,同比(增长|下降)([\d.]+)(%)',
      'inventories_yoy':r'产成品存货[\d.]+万亿元,(?:同比)?(增长|下降)([\d.]+)(%)',
      'cashdays_change':r'应收账款平均回收期为[\d.]+天,同比(增加|减少)([\d.]+)(天)',
      'inventorydays_change':r'产成品存货周转天数为[\d.]+天,同比(增加|减少)([\d.]+)(天)',
    }
    for ident,pattern in specifications.items():out[ident]=_change_clause(s,pattern,ident)
    for ident,pattern in {
      'profit_margin':r'营业收入利润率为([\d.]+)%',
      'receivables':r'规模以上工业企业应收账款([\d.]+)万亿元',
      'inventories':r'产成品存货([\d.]+)万亿元',
      'receivable_days':r'应收账款平均回收期为([\d.]+)天',
      'inventory_days':r'产成品存货周转天数为([\d.]+)天',
      'debt_assets':r'资产负债率为([\d.]+)%',
    }.items():
        out[ident]=_matched_number(s,pattern,ident)
    sectors={
      'sector_profit_electronics':'计算机、通信和其他电子设备制造业利润同比',
      'sector_profit_nonferrous':'有色金属冶炼和压延加工业',
      'sector_profit_chemicals':'化学原料和化学制品制造业',
      'sector_profit_auto':'汽车制造业',
      'sector_profit_ferrous':'黑色金属冶炼和压延加工业',
      'sector_profit_power':'电力、热力生产和供应业',
    }
    # Sector clauses in the opening prose, not the table or definitions below.
    section=re.findall(r'主要行业利润情况如下[:：]([^。]+)。',s)
    if len(section)!=1:raise ValueError('exact national sector-profit paragraph required')
    for ident,label in sectors.items():
        out[ident]=_change_clause(section[0],re.escape(label)+r'(增长|下降)([\d.]+)(%|倍)',ident)
    for ident,v in out.items():
        if (ident in {'receivables','inventories','receivable_days','inventory_days','profit_margin','debt_assets'} and v<0) or (ident.endswith('_yoy') and v<-100):
            raise ValueError('impossible corporate value: '+ident)
    return [{'metric_id':k,'period':expected_period,'value':v} for k,v in out.items()]


def parse_nea_text(text:str,expected_period:str)->list[dict]:
    """Monthly consumption by sector; never generation or cumulative YTD power.

    Weather affects household consumption. These are contextual physical rates,
    not calibrated real GDP, household spending or extra economy-score votes.
    """
    month_index(expected_period);year,month=map(int,expected_period.split('-'))
    s=compact(text)
    start=re.search(rf'{year}年{month}月,',s)
    if not start:raise ValueError('NEA monthly reference missing')
    monthly=s[start.end():]
    boundary=re.search(rf'1[—–-]{month}月,',monthly)
    if not boundary:raise ValueError('NEA monthly/YTD boundary missing')
    monthly=monthly[:boundary.start()]
    out={}
    labels={'power_total':'全社会用电量','power_industrial':'工业用电量',
      'power_hightech':'高技术及装备制造业用电量','power_services':'第三产业用电量',
      'power_households':'城乡居民生活用电量'}
    for ident,label in labels.items():
        pattern=re.escape(label)+r'[^。；;%]{0,70}?([\d.]+)亿千瓦时,同比(增长|下降)([\d.]+)%'
        matches=re.findall(pattern,monthly)
        if len(matches)!=1:raise ValueError('missing or ambiguous monthly NEA clause: '+ident)
        amount,direction,growth=matches[0]
        if number(amount) is None or float(amount)<0:raise ValueError('invalid electricity amount')
        out[ident]=float(growth)*(-1 if direction=='下降' else 1)
    # Keep the source's paired ordering: charging first, internet-data second.
    pattern=r'充换电服务业、互联网数据服务用电量[^。；]{0,80}?增速分别达到([\d.]+)%、([\d.]+)%'
    matches=re.findall(pattern,monthly)
    if len(matches)!=1:raise ValueError('paired NEA growth ordering not verified')
    out['power_charging'],out['power_datacenters']=map(float,matches[0])
    if any(v<-100 for v in out.values()):raise ValueError('impossible NEA change')
    return [{'metric_id':k,'period':expected_period,'value':v} for k,v in out.items()]


# Current-period detail comes from the SAME acquired release as the history.
# These are existing catalog bindings, not independent growth-domain votes.
ACTIVITY_DETAIL_ROWS = {
    'industry': {
        '规模以上工业增加值': 'industrial_yoy', '采矿业': 'output_mining',
        '制造业': 'output_manufacturing', '其中：高技术制造业': 'output_hightech',
        '电力、热力、燃气及水生产和供应业': 'output_utilities',
        '计算机、通信和其他电子设备制造业': 'output_electronics',
        '水泥(万吨)': 'output_cement', '钢材(万吨)': 'output_steel',
        '其中：新能源汽车(万辆)': 'output_nev',
    },
    'retail': {
        '社会消费品零售总额': 'retail_yoy',
        '其中：除汽车以外的消费品零售额': 'retail_exauto',
        '城镇': 'retail_urban', '乡村': 'retail_rural', '餐饮收入': 'retail_catering',
    },
    'investment': {
        '固定资产投资(不含农户)': 'investment_ytd',
        '其中：民间投资': 'private_investment', '制造业': 'manufacturing_investment',
        '设备工器具购置': 'investment_equipment',
    },
}
_DETAIL_ANCHOR = {'industry': '规模以上工业增加值', 'retail': '社会消费品零售总额',
                  'investment': '固定资产投资(不含农户)'}
_DETAIL_RATE_LABELS = {
    'investment': {
        '基础设施投资': 'investment_infra', '知识产权产品投资': 'investment_ip',
        '东部地区投资': 'regional_investment_east',
        '中部地区投资': 'regional_investment_central',
        '西部地区投资': 'regional_investment_west',
        '东北地区投资': 'regional_investment_northeast',
    },
    'pmi': {'大型企业PMI为': 'pmi_large', '中型企业PMI为': 'pmi_medium',
            '小型企业PMI为': 'pmi_small', '服务业商务活动指数为': 'pmi_services',
            '建筑业商务活动指数为': 'pmi_construction'},
}


def _detail_table_values(article, family: str, expected_period: str) -> dict:
    """Select a single national table and a named GROWTH column, never offsets."""
    mapping = ACTIVITY_DETAIL_ROWS[family]
    candidates = [expand_table(t) for t in article.find_all('table')
                  if any(r and r[0] == _DETAIL_ANCHOR[family] for r in expand_table(t))]
    if len(candidates) != 1:
        raise ValueError('detail_table_missing_or_ambiguous')
    rows = candidates[0]
    if family == 'investment':
        if rows[0] != ['指标', '同比增长(%)']:
            raise ValueError('detail_ytd_growth_header_changed')
        column, width = 1, 2
    else:
        if len(rows) < 2 or len(rows[0]) != len(rows[1]):
            raise ValueError('detail_monthly_header_incomplete')
        month = str(int(expected_period[-2:])) + '月'
        columns = [i for i, (period, field) in enumerate(zip(rows[0], rows[1]))
                   if period == month and field.replace('％', '%') == '同比增长(%)']
        if len(columns) != 1:
            raise ValueError('detail_monthly_growth_column_missing_or_ambiguous')
        column, width = columns[0], len(rows[0])
    result = {}
    for row in rows:
        if not row or row[0] not in mapping:
            continue
        ident = mapping[row[0]]
        if ident in result:
            raise ValueError('detail_duplicate_national_metric')
        if len(row) != width:
            raise ValueError('detail_truncated_national_row')
        raw = row[column]
        value = number(raw) if re.fullmatch(r'[+-]?\d+(?:\.\d+)?', raw) else None
        # Do not turn missing/suppressed values or incompatible units into zero.
        result[ident] = value if value is not None and value >= -100 else None
    return result


def parse_activity_detail(html: str, family: str, expected_period: str) -> tuple[list[dict], dict]:
    """Additional current observations, with explicit per-measure null reasons.

    Core seasonal/survey parsers still own their histories. Missing or malformed
    supplemental detail cannot silently destroy those histories or borrow them
    for a new measure. No network, revision reconstruction, or new store owner.
    """
    month_index(expected_period)
    if family not in {'industry', 'retail', 'investment', 'pmi'}:
        raise ValueError('unsupported_detail_family')
    year, month = map(int, expected_period.split('-'))
    article = publisher_article_root(html)
    soup = BeautifulSoup(html, 'html.parser')
    meta = soup.find('meta', attrs={'name': 'ArticleTitle'})
    title = meta.get('content', '') if meta else soup.title.get_text() if soup.title else ''
    combined = compact(title + ' ' + article.get_text(' ', strip=True))
    period_pattern = (rf'{year}年1[—–－-]{month}月(?:份)?' if family == 'investment'
                      else rf'{year}年(?:1[—–－-])?{month}月(?:份)?')
    if not re.search(period_pattern, combined):
        raise ValueError('detail_release_reference_missing_or_changed')
    values, missing = {}, {}
    fields = ACTIVITY_DETAIL_ROWS.get(family, {})
    if fields:
        try:
            values.update(_detail_table_values(article, family, expected_period))
            for ident in fields.values():
                if values.get(ident) is None:
                    missing[ident] = 'not_disclosed_or_invalid_in_expected_column'
        except ValueError as exc:
            missing.update({ident: str(exc) for ident in fields.values()})
    # Remove every statistical table before paragraph matching. A quoted table
    # number, an absolute amount, and a previous-period delta are not this value.
    prose = BeautifulSoup(str(article), 'html.parser')
    for node in prose.find_all(['table', 'script', 'style', 'noscript']):
        node.decompose()
    text = compact(prose.get_text(' ', strip=True))
    paired = []
    if family == 'pmi':
        # Exact ordered current-level clause; never use the following monthly
        # deltas. Conflicting paired and standalone formulations are withheld.
        paired = re.findall(
            r'中、小型企业PMI分别为(\d+(?:\.\d+)?)%和(\d+(?:\.\d+)?)%', text)
    for label, ident in _DETAIL_RATE_LABELS.get(family, {}).items():
        if family == 'pmi':
            matches = re.findall(re.escape(label) + r'(\d+(?:\.\d+)?)%', text)
            if ident in {'pmi_medium', 'pmi_small'} and paired:
                position = 0 if ident == 'pmi_medium' else 1
                # The pair must be unique and both members must be plausible.
                valid_pair = (len(paired) == 1 and all(
                    number(raw) is not None and 0 <= number(raw) <= 100
                    for raw in paired[0]))
                candidate = number(paired[0][position]) if valid_pair else None
                value = candidate if (candidate is not None and len(matches) <= 1
                    and (not matches or number(matches[0]) == candidate)) else None
            else:
                value = number(matches[0]) if len(matches) == 1 else None
            if value is not None and not 0 <= value <= 100:
                value = None
        else:
            pattern = re.escape(label) + r'(?:\([^()]{1,60}\))?(?:同比)?(?:(增长|下降)(\d+(?:\.\d+)?)%|(持平))'
            matches = re.findall(pattern, text)
            value = None
            if len(matches) == 1:
                word, raw, flat = matches[0]
                value = 0.0 if flat else number(raw)
                if value is not None and word == '下降':
                    value = -value
                if value is not None and value < -100:
                    value = None
        if value is None:
            missing[ident] = 'paragraph_not_unique_or_value_invalid'
        else:
            values[ident] = value
    if family == 'industry':
        # Counts use the catalog's exact denominators, NOT percentage coverage.
        for ident, pattern, denominator in (
            ('industry_positive', r'(\d+)个大类行业中有(\d+)个行业增加值(?:保持)?同比增长', 41),
            ('products_positive', r'(\d+)种产品中有(\d+)种产品产量同比增长', 626),
        ):
            matches = re.findall(pattern, text)
            if len(matches) == 1 and int(matches[0][0]) == denominator and 0 <= int(matches[0][1]) <= denominator:
                values[ident] = int(matches[0][1])
            else:
                missing[ident] = 'count_denominator_or_disclosure_not_verified'
    points = [{'metric_id': ident, 'period': expected_period, 'value': value}
              for ident, value in sorted(values.items()) if value is not None]
    return points, {'scope': 'same_release_current_period_only',
                    'status': 'partial' if missing and points else 'withheld' if missing else 'complete',
                    'admitted_metrics': [p['metric_id'] for p in points],
                    'null_reasons': missing, 'history_inferred': False}
