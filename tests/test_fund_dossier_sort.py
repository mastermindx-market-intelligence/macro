"""Exercise the real full-book template and its emitted sorter, without a browser.

Native mode uses Node's standard-library VM over rows parsed from actual Jinja
output. Set JSDOM_MODULE for supplementary full-DOM header-click qualification.
Neither mode contacts a service or changes financial data.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
from html.parser import HTMLParser
import re
import pytest
from jinja2 import Environment, FileSystemLoader

ROOT = Path(os.environ.get('FUND_ROOT', Path(__file__).resolve().parents[1]))
TEXT = {'ticker':'ticker', 'issuer':'issuer', 'act':'action', 'sector':'sector'}
NUMERIC = {'rank':'position_rank','pct':'pct_book','val':'value_usd',
           'chg':'shares_change_pct','streak':'add_streak_q','conv':'conviction','since':'since_excess'}

class BookParser(HTMLParser):
    def __init__(self):
        super().__init__();self.rows=[];self.headers=[];self.in_book=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='table' and a.get('id')=='fd-book':self.in_book=True
        if self.in_book and tag=='th' and 'data-col' in a:self.headers.append(a['data-col'])
        if self.in_book and tag=='tr' and 'data-ticker' in a:
            self.rows.append({k[5:]:v for k,v in a.items() if k.startswith('data-')})
    def handle_endtag(self,tag):
        if tag=='table':self.in_book=False

def render(book):
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=True)
    return env.get_template('fund_dossier.html.j2').render(slug='test',fi={'book':book},bf={},lb_row={},generated_utc='fixture',active_section='us',active_page='smart_money')

def spec(book,steps):
    html=render(book);p=BookParser();p.feed(html)
    assert len(p.rows)==len(book)
    return {'html':html,'rows':p.rows,'headers':p.headers,'steps':steps}

def cases():
    out=[]
    for col,key in TEXT.items():
        values=['3M CO','20TH CORP','ZETA','ALPHA',None,'0','3M CO','alpha','中文','ÉCO']
        book=[{'ticker':f'R{i:02d}',key:value} for i,value in enumerate(values)]
        if col=='ticker':
            # Duplicate tickers are not a producer shape; use distinct numeric-looking identifiers.
            values=['3M','20TH','ZETA','ALPHA',None,'0','3Z','alpha','中文','ÉCO']
            book=[{'ticker':value,'issuer':f'ROW-{i}'} for i,value in enumerate(values)]
        ids=[b.get('ticker') or '' for b in book]
        asc=sorted([i for i,v in enumerate(values) if v is not None],key=lambda i:values[i])+[4]
        desc=sorted([i for i,v in enumerate(values) if v is not None],key=lambda i:values[i],reverse=True)+[4]
        expected=lambda order:[ids[i] for i in order]
        steps=[{'id':f'{col}-ascending-missing-last','col':col,'expected':expected(asc),'indicator':'↑'},
               {'id':f'{col}-descending-digit-prefix','col':col,'expected':expected(desc),'indicator':'↓'},
               {'id':f'{col}-repeat-ascending','col':col,'expected':expected(asc),'indicator':'↑'}]
        out.append(spec(book,steps))
    for col,key in NUMERIC.items():
        values=[10,0,2,None,10,-3] if col in ('chg','since') else [10,0,2,None,10,3]
        book=[{'ticker':f'N{i}',key:{'score':v} if col=='conv' else v} for i,v in enumerate(values)]
        ids=[b['ticker'] for b in book]
        known=[i for i,v in enumerate(values) if v is not None]
        desc=sorted(known,key=lambda i:values[i],reverse=True)+[3]
        asc=sorted(known,key=lambda i:values[i])+[3]
        out.append(spec(book,[{'id':f'{col}-descending-zero-and-ties','col':col,'expected':[ids[i] for i in desc],'indicator':'↓'},
                              {'id':f'{col}-ascending-missing-last','col':col,'expected':[ids[i] for i in asc],'indicator':'↑'},
                              {'id':f'{col}-repeat-descending','col':col,'expected':[ids[i] for i in desc],'indicator':'↓'}]))
    # Switching columns resets the established first direction and only marks one header.
    book=[{'ticker':'B','issuer':'20TH','pct_book':2,'sector':''},
          {'ticker':'A','issuer':'3M','pct_book':10,'sector':'Tech'},
          {'ticker':'C','issuer':'ALPHA','pct_book':0,'sector':'Health'}]
    out.append(spec(book,[{'id':'switch-numeric','col':'pct','expected':['A','B','C'],'indicator':'↓'},
                          {'id':'switch-text','col':'issuer','expected':['B','A','C'],'indicator':'↑'},
                          {'id':'switch-text-desc','col':'issuer','expected':['C','A','B'],'indicator':'↓'},
                          {'id':'switch-back-numeric','col':'pct','expected':['A','B','C'],'indicator':'↓'}]))
    # Empty text values remain a stable tail instead of comparing as real labels.
    book=[{'ticker':'M1','issuer':None},{'ticker':'V','issuer':'VALUE'},{'ticker':'M2','issuer':''}]
    out.append(spec(book,[{'id':'stable-missing-asc','col':'issuer','expected':['V','M1','M2'],'indicator':'↑'},
                          {'id':'stable-missing-desc','col':'issuer','expected':['V','M1','M2'],'indicator':'↓'}]))
    return out

@pytest.fixture(scope='module')
def results():
    source=(ROOT/'templates'/'fund_dossier.html.j2').read_text()
    script=re.search(r'<script>\s*(/\* Full-book column sort[\s\S]*?)</script>',source).group(1)
    payload={'sortScript':script,'cases':cases()}
    result=subprocess.run(['node',str(Path(__file__).with_name('sort_runner.cjs'))],input=json.dumps(payload),text=True,capture_output=True,check=True)
    return {r['id']:r for r in json.loads(result.stdout)}

CASE_IDS=[f'{col}-{suffix}' for col in TEXT for suffix in ['ascending-missing-last','descending-digit-prefix','repeat-ascending']]+[f'{col}-{suffix}' for col in NUMERIC for suffix in ['descending-zero-and-ties','ascending-missing-last','repeat-descending']]+['switch-numeric','switch-text','switch-text-desc','switch-back-numeric','stable-missing-asc','stable-missing-desc']

@pytest.mark.parametrize('case_id',CASE_IDS)
def test_full_book_sort(case_id,results):
    r=results[case_id]
    assert r['actual']==r['expected']
    assert r['indicator']==r['expectedIndicator']
    assert r['selected']==[r['col']]
    assert r['intact']

