"""Check topic descriptions through the existing production Jinja environment.

Uses the retained admitted public payload and accepted model; it does not rebuild
or promote model facts. All current topics are rendered to detect unintended
macro changes. The two language spans are checked separately.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from bs4 import BeautifulSoup

p=argparse.ArgumentParser()
p.add_argument('--root',type=Path,required=True)
p.add_argument('--baseline',action='store_true')
a=p.parse_args();root=a.root.resolve()
sys.path.insert(0,str(root))
from scripts.gmi_explorer.present import make_env
model=json.loads((root/'accepted-model.json').read_text())
site=root/('baseline' if a.baseline else 'candidate')
payload=json.loads(BeautifulSoup((site/'gmi.html').read_text(),'html.parser').select_one('#gmi-topic-data').get_text())
env=make_env(model,root/'templates')
template=env.from_string('{% from "_gmi_product_macros.html.j2" import topic_answer with context %}{{ topic_answer(topic) }}')
special={'en':'High-bandwidth memory stacking and its packaging — a distinct part of the AI semiconductor stack.',
         'zh':'高带宽内存的堆叠与封装，是 AI 半导体体系中一个独立的环节。'}
generic={'en':'Explore its place in the taxonomy and the company evidence currently on file.',
         'zh':'了解它在主题体系中的位置，以及目前收录的公司证据。'}
def digest(b):return hashlib.sha256(b).hexdigest()
report={'generated_at':datetime.now(timezone.utc).isoformat(),'baseline':a.baseline,'scope':__doc__.strip(),
        'source_head':'ba8a81b6470f88f71bc7c2ec90cede39aba8a9b0',
        'model_sha256':digest((root/'accepted-model.json').read_bytes()),
        'macro_sha256':digest((root/'templates/_gmi_product_macros.html.j2').read_bytes()),
        'payload_sha256':digest(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()),
        'topics':[],'mismatches':[],'checks':0}
for topic in payload['topics']:
    html=template.render(model=model,topic=topic,topic_names=payload['categories'],nav_prefix='')
    soup=BeautifulSoup(html,'html.parser');description=soup.select_one('[data-topic-description]')
    values={language:description.select_one('.l-'+language).get_text() for language in ('en','zh')}
    expected=special if topic['id']=='theme:hbm_packaging' else generic
    for language in ('en','zh'):
        report['checks']+=1
        if values[language]!=expected[language]:
            report['mismatches'].append({'id':topic['id'],'language':language,'actual':values[language],'expected':expected[language]})
    outside=re.sub(r'(<p data-topic-description>).*?(</p>)',r'\1[DESCRIPTION]\2',html,flags=re.S)
    assert outside!=html
    report['topics'].append({'id':topic['id'],'name':topic['en'],'descriptions':values,
                            'html_sha256':digest(html.encode()),'outside_description_sha256':digest(outside.encode()),
                            'connections':len(topic['connections'])})
report['old_substring_matches']=[t['id'] for t in payload['topics'] if 'hbm' in t['en'].lower()]
if not a.baseline:
    before=json.loads((root/'server-baseline-proof.json').read_text())
    prior={t['id']:t for t in before['topics']}
    report['changed_macro_outputs']=[t['id'] for t in report['topics'] if t['html_sha256']!=prior[t['id']]['html_sha256']]
    report['outside_description_all_exact']=all(t['outside_description_sha256']==prior[t['id']]['outside_description_sha256'] for t in report['topics'])
    assert report['changed_macro_outputs']==['theme:conventional_dram'],report['changed_macro_outputs']
    assert report['outside_description_all_exact']
report['pass']=not report['mismatches']
out=root/('server-baseline-proof.json' if a.baseline else 'server-candidate-proof.json')
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'report':str(out),'topics':len(report['topics']),'checks':report['checks'],'pass':report['pass'],'mismatches':report['mismatches'],
                  'old_substring_matches':report['old_substring_matches'],'changed_macro_outputs':report.get('changed_macro_outputs'),
                  'outside_description_all_exact':report.get('outside_description_all_exact')},ensure_ascii=False),flush=True)
raise SystemExit(0 if report['pass'] else 1)
