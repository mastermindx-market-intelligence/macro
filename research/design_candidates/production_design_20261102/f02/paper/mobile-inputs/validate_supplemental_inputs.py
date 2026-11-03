#!/usr/bin/env python3
"""Validate supplemental structure, fixture identity and width rules only."""
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import compare_clones as c

P=HERE/'supplemental-boards.json'
d=json.loads(P.read_text())
old=json.loads((HERE/'mobile-state-boards.json').read_text())
assert hashlib.sha256((HERE/'mobile-state-boards.json').read_bytes()).hexdigest()==d['base_packet_sha256']
assert len(old['boards'])==6 and sum(len(b['steps']) for b in old['boards'])==171
old_boards={b['key']:b for b in old['boards']}
new_boards={b['key']:b for b in d['boards']}
checks=[]

def validate_step(s):
    root=c.parse(s['html']);elements=c.flatten(root)
    assert len(s['html'].splitlines())<=15
    for _,n,_ in elements:
        assert n.tag not in {'table','img','iframe','script','style'}
        for k,v in c.css(n.attrs.get('style')).items():
            assert not k.startswith('margin')
            assert not (k=='display' and v in ['grid','inline','inline-grid'])
    return len(elements)

for b in d['boards']:
    keys={'board'};count=0
    for s in b['steps']:
        assert s['key'] not in keys and s['parent'] in keys,(b['key'],s['key'])
        keys.add(s['key']);count+=validate_step(s)
    if b['key'].startswith('width-'):
        assert sum(bool(re.fullmatch(r'sector-\d+',s['key'])) for s in b['steps'])==10
        header_html=next(s['html'] for s in b['steps'] if s['key']=='table')
        assert 'Source' in header_html or 'Evidence' in header_html
        assert all('Source' in s['html'] for s in b['steps'] if re.fullmatch(r'sector-\d+',s['key']))
        assert b['expected_geometry']['source_column_present']
    if b['key'] in ['width-768-overlay','width-1024-overlay']:
        g=b['expected_geometry'];assert g['viewport']-g['rail']-2*g['side_padding']==g['primary_without_inspector']
        assert g['primary_without_inspector']-344==g['hypothetical_docked_primary']<640
        assert g['overlay_left']==g['viewport']-440
        assert g['header']==(56 if g['viewport']==768 else 64)
        table=next(s for s in b['steps'] if s['key']=='table')
        root=c.parse(table['html']);head=root.children[0]
        widths=[int(c.css(n.attrs['style'])['width'][:-2]) for n in head.children]
        assert sum(widths)+24==g['primary_without_inspector']
        assert any(s.get('capture_state','').startswith('CLOSED_BEFORE_OVERLAY') for s in b['steps'])
        assert any(s.get('capture_state','').startswith('OPEN_OVERLAY') for s in b['steps'])
    if b['key']=='width-1600-docked':
        g=b['expected_geometry'];assert 1600-224-48==g['main_usable']==1328
        assert g['main_usable']-g['dock']-g['gap']==g['primary']==984
        assert g['primary']>=640
        table=next(s for s in b['steps'] if s['key']=='table')
        head=c.parse(table['html']).children[0]
        assert sum(int(c.css(n.attrs['style'])['width'][:-2]) for n in head.children)+24==984
        chart=next(s['html'] for s in b['steps'] if s['key']=='chart')
        assert chart.count('<circle ')==7 and chart.count('<line ')==8
    checks.append({'board':b['key'],'steps':len(b['steps']),'native_elements':count,'single_roots_and_parents_valid':True})

for group in d['append_to_existing']:
    target=group['target_board_key']
    source=old_boards[target] if target in old_boards else next(b for b in json.loads((HERE.parent/'foundation-inputs/boards.json').read_text())['boards'] if b['key']==target)
    keys={'board'}|{s['key'] for s in source['steps']}
    for s in group['steps']:
        assert s['parent'] in keys and s['key'] not in keys
        keys.add(s['key']);validate_step(s)

zh=new_boards['macro-zh-evidence-return-390']
assert zh['expected_geometry']['record_id']=='f02.fixture.v2/macro/sector/communication_services/share_above_50d/2026-10-30'
all_zh=''.join(s['html'] for s in zh['steps'])
for value in ['66.7%','+1.13 pp','21 / 21','20:00 UTC','20:02 UTC','20:03 UTC','关闭','返回“通信服务”行']:
    assert value in all_zh,value
assert Decimal('66.70')-Decimal('65.57')==Decimal('1.13')
old_row=next(s['html'] for s in old_boards['macro-light-zh-390']['steps'] if s['key']=='sector-3')
returned_row=next(s['html'] for s in zh['steps'] if s['key']=='returned-selected-row')
assert old_row==returned_row

def subtree_steps(b,key):
    admitted={key};out=[]
    for s in b['steps']:
        if s['key']==key or s['parent'] in admitted:
            out.append({k:s[k] for k in ['key','parent','html']});admitted.add(s['key'])
    return out
assert subtree_steps(new_boards['width-768-overlay'],'overlay')==subtree_steps(new_boards['width-1024-overlay'],'overlay')
wide=json.loads((HERE/'supplemental-wide-clone.json').read_text())
assert wide['supplement_sha256']==hashlib.sha256(P.read_bytes()).hexdigest()
assert wide['pair']['input_structure_equivalent'] and wide['pair']['has_declared_geometry_style_changes']

result={'status':'PASS_SUPPLEMENT_SOURCE_STRUCTURE_ONLY','supplement_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'base_171_step_packet_unchanged':d['base_packet_sha256'],'boards':4,'new_board_steps':sum(len(b['steps']) for b in d['boards']),'append_steps':sum(len(g['steps']) for g in d['append_to_existing']),'checks':checks,'clone_opportunities_verified':['exact Chinese return row','identical 440px overlay subtree between 768/1024','same topology 1280→1600 with explicit geometry changes'],'native_mapping_or_visual_proof':False,'paper_calls':0,'browser_calls':0}
(HERE/'supplemental-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
