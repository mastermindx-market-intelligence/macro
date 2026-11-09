"""Render empty-topic copy through the existing production Jinja environment.

Baseline mode captures parent markup for comparison; it does not assess the new
copy contract. Candidate mode checks all current topic descriptions, empty-card
structure, positive/zero coverage visibility and unchanged outside markup.
Controlled empty macro fixtures are not new product routes or no-JS deep links.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from bs4 import BeautifulSoup

parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--baseline',action='store_true')
args=parser.parse_args();root=args.root.resolve()
sys.path.insert(0,str(root))
from scripts.gmi_explorer.present import make_env
model=json.loads((root/'accepted-model.json').read_text())
site=root/('baseline' if args.baseline else 'candidate')
payload=json.loads(BeautifulSoup((site/'gmi.html').read_text(),'html.parser').select_one('#gmi-topic-data').get_text())
env=make_env(model,root/'templates')
template=env.from_string('{% from "_gmi_product_macros.html.j2" import topic_answer with context %}{{ topic_answer(topic) }}')
special={'en':'High-bandwidth memory stacking and its packaging — a distinct part of the AI semiconductor stack.',
         'zh':'高带宽内存的堆叠与封装，是 AI 半导体体系中一个独立的环节。'}
body={'en':'No reviewed company connections are published here. This does not mean no companies participate.',
      'zh':'此处暂无经审核并发布的公司关联，不代表没有公司参与该主题。'}
action={'en':'Browse company evidence','zh':'浏览公司证据'}
heading={'en':'No company evidence yet','zh':'暂无公司证据'}
out=root/('server-baseline' if args.baseline else 'server-candidate');out.mkdir(exist_ok=True)
def digest(b):return hashlib.sha256(b).hexdigest()
def languages(node):
    return {lang:node.select_one('.l-'+lang).get_text() for lang in ('en','zh')}
report={'generated_at':datetime.now(timezone.utc).isoformat(),'baseline':args.baseline,'scope':__doc__.strip(),
        'source_head':'ce523870476f250e456eb3c481f4f89bf619866d',
        'model_sha256':digest((root/'accepted-model.json').read_bytes()),
        'macro_sha256':digest((root/'templates/_gmi_product_macros.html.j2').read_bytes()),
        'payload_sha256':digest(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()),
        'topics':[],'mismatches':[],'description_language_checks':0,'empty_cards':0}
for topic in payload['topics']:
    html=template.render(model=model,topic=topic,topic_names=payload['categories'],nav_prefix='')
    soup=BeautifulSoup(html,'html.parser');description=soup.select_one('[data-topic-description]')
    values=languages(description);empty=soup.select_one('.gmi-topic-empty');coverage=soup.select_one('[data-topic-coverage]')
    parent=payload['categories'][topic['parent']]
    expected=special if topic['id']=='theme:hbm_packaging' else {'en':'Theme group: '+parent['en'],'zh':'所属主题组：'+parent['zh']}
    row={'id':topic['id'],'name':topic['en'],'descriptions':values,'connections':len(topic['connections']),
         'coverage_hidden':coverage.has_attr('hidden'),'coverage_text':languages(coverage),'empty':None}
    if empty is not None:
        report['empty_cards']+=1
        paragraphs=empty.find_all('p',recursive=False)
        row['empty']={'heading':languages(empty.select_one('h2')),'paragraphs':[languages(p) for p in paragraphs],
                      'decoration_count':len(empty.select('.gmi-eyebrow,.gmi-empty-symbol')),
                      'action':languages(empty.select_one('a')),'href':empty.select_one('a')['href']}
    if not args.baseline:
        for lang in ('en','zh'):
            report['description_language_checks']+=1
            if values[lang]!=expected[lang]:report['mismatches'].append({'id':topic['id'],'field':'description-'+lang,'actual':values[lang],'expected':expected[lang]})
        if not topic['connections']:
            expected_empty={'heading':heading,'paragraphs':[body],'decoration_count':0,'action':action,'href':'gmi-companies.html'}
            if row['empty']!=expected_empty:report['mismatches'].append({'id':topic['id'],'field':'empty-card','actual':row['empty'],'expected':expected_empty})
        elif row['empty'] is not None:report['mismatches'].append({'id':topic['id'],'field':'unexpected-empty-card'})
        if row['coverage_hidden']!=(not bool(topic['connections'])):report['mismatches'].append({'id':topic['id'],'field':'coverage-visibility'})
    outside=re.sub(r'(<p data-topic-description>).*?(</p>)',r'\1[DESCRIPTION]\2',html,flags=re.S)
    outside=re.sub(r'<section class="gmi-topic-empty">.*?</section>','[EMPTY-CARD]',outside,flags=re.S)
    outside=outside.replace('<p data-topic-coverage hidden>','<p data-topic-coverage>')
    row.update({'html_sha256':digest(html.encode()),'outside_changed_regions_sha256':digest(outside.encode())})
    report['topics'].append(row)
    if topic['id'] in ('theme:conventional_dram','theme:hbm_packaging'):
        filename='empty-answer.html' if topic['id']=='theme:conventional_dram' else 'hbm-answer.html'
        (out/filename).write_text(html)
if not args.baseline:
    before=json.loads((root/'server-baseline/report.json').read_text());prior={t['id']:t for t in before['topics']}
    report['changed_ids']=[t['id'] for t in report['topics'] if t['html_sha256']!=prior[t['id']]['html_sha256']]
    report['outside_all_exact']=all(t['outside_changed_regions_sha256']==prior[t['id']]['outside_changed_regions_sha256'] for t in report['topics'])
    report['hbm_markup_exact']=next(t for t in report['topics'] if t['id']=='theme:hbm_packaging')['html_sha256']==prior['theme:hbm_packaging']['html_sha256']
    assert report['outside_all_exact'] and report['hbm_markup_exact']
    assert set(report['changed_ids'])=={t['id'] for t in report['topics'] if t['id']!='theme:hbm_packaging'}
report['pass']=not report['mismatches']
(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'report':str(out/'report.json'),'baseline_capture_only':args.baseline,'topics':len(report['topics']),
                  'description_language_checks':report['description_language_checks'],'empty_cards':report['empty_cards'],
                  'mismatches':report['mismatches'][:4],'pass':report['pass'],
                  'changed_topics':len(report.get('changed_ids',[])) if not args.baseline else None,
                  'outside_all_exact':report.get('outside_all_exact'),'hbm_markup_exact':report.get('hbm_markup_exact')},ensure_ascii=False),flush=True)
raise SystemExit(0 if report['pass'] else 1)
