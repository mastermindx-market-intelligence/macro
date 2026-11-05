#!/usr/bin/env python3
"""Structural/fixture validation only; no browser or Paper proof."""
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
data=json.loads((HERE/'mobile-state-boards.json').read_text())
assert data['source_pattern_sha256']==hashlib.sha256((ROOT/'pattern-lab.html').read_bytes()).hexdigest()
assert data['source_fixture_sha256']==hashlib.sha256((ROOT/'fixtures/company-history.json').read_bytes()).hexdigest()

class Parse(HTMLParser):
    def __init__(self):super().__init__();self.stack=[];self.roots=0;self.tags=[];self.styles=[]
    def handle_starttag(self,tag,attrs):
        if not self.stack:self.roots+=1
        self.stack.append(tag);self.tags.append(tag)
        for k,v in attrs:
            if k=='style':self.styles.append(v)
    def handle_endtag(self,tag):assert self.stack.pop()==tag,(tag,self.stack)
    def handle_startendtag(self,tag,attrs):
        self.tags.append(tag)
        for k,v in attrs:
            if k=='style':self.styles.append(v)

checks=[]
for board in data['boards']:
    keys={'board'}
    for step in board['steps']:
        assert step['key'] not in keys
        assert step['parent'] in keys,(board['key'],step['key'],step['parent'])
        keys.add(step['key'])
        p=Parse();p.feed(step['html'])
        assert p.roots==1 and not p.stack,(board['key'],step['key'])
        assert not set(p.tags)&{'table','img','iframe','script','style'}
        assert all(not re.search(r'(?:^|;)\s*margin(?:-|\s*:)|display\s*:\s*(?:grid|inline)\b',s) for s in p.styles)
        assert len(step['html'].splitlines())<=15
    if board['key'].startswith('macro-'):
        assert sum(x['key'].startswith('sector-') for x in board['steps'])==10
        chart=next(x['html'] for x in board['steps'] if x['key']=='chart')
        assert chart.count('<circle ')==7
        assert chart.count('<line ')==8 # three guides + five segments; no bridge over missing session
    checks.append({'board':board['key'],'steps':len(board['steps']),'native_single_roots':True,'parent_order_valid':True})

state=next(b for b in data['boards'] if b['key']=='states-matrix')
assert sum(bool(re.fullmatch(r'state-\d+',x['key'])) for x in state['steps'])==16
assert len([x for x in state['steps'] if x['key'] in ['combined-dark','combined-light']])==2
for key in ['company-eps-overlay-320','company-dividend-overlay-320']:
    b=next(x for x in data['boards'] if x['key']==key)
    assert sum(x['key'].startswith('period-') for x in b['steps'])==5
    assert 'f02.fixture.v2/company/EXM/' in ''.join(x['html'] for x in b['steps'])
dock=next(b for b in data['boards'] if b['key']=='macro-docked-1280')['expected_geometry']
assert dock['viewport_width']-dock['rail']-2*dock['main_padding']==dock['main_usable']==1008
assert dock['main_usable']-dock['dock']-dock['gap']==dock['primary']==664
assert dock['primary']>=dock['primary_minimum']
result={'status':'PASS_SOURCE_STRUCTURE_ONLY','boards':len(data['boards']),'steps':sum(len(b['steps']) for b in data['boards']),'checks':checks,'browser_or_paper_rendered':False}
(HERE/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
