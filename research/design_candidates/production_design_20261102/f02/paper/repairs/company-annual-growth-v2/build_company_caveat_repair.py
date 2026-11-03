#!/usr/bin/env python3
"""Separate caveat addendum. Leaves the already delivered row v2 bytes alone."""
from pathlib import Path
from html import escape
import hashlib, importlib.util, json, xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;PAPER=HERE.parents[1]
spec=importlib.util.spec_from_file_location('company_row_v2',HERE/'build_company_row_repairs.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def sha(b):return hashlib.sha256(b if isinstance(b,bytes)else b.encode()).hexdigest()
before=sha((HERE/'company-row-replacements.v2.json').read_bytes())
copy='Each annual amount is paired with change versus the prior fiscal year. Margin changes use pp; dividend changes are absolute USD/share (relative growth from zero is undefined). Missing prior or current values remain unavailable. FY2021 baselines use the retained history where supplied; FY2026 diluted EPS is unavailable.'
src={b['key']:b for b in m.SOURCE['boards']};actual={b['key']:b for b in m.PROGRESS['boards']};ops=[];overrides=[]
for theme in ['dark','light']:
 key='company-'+theme;b=actual[key];p=m.consumer.palette(theme);sk='statement-caveat';old=b['steps'][sk]
 path=PAPER/'exports'/f'{key}.jsx';_,index=m.native.parse_jsx(path.read_text());node=index[old]
 source=next(s for s in src[key]['steps']if s['key']==sk)
 assert node['parent_id']==b['steps']['main']
 assert m.native.all_text(node)==m.native.all_text(m.native.Parser(source['html']).roots[0])
 markup='<div layer-name="Annual change and absence policy" style="display:flex;flex-direction:column;flex-shrink:0;box-sizing:border-box;width:1168px;padding:12px 0 18px;"><div style="font-family:Inter;font-size:12px;line-height:18px;color:'+p['secondary']+';width:1168px;overflow-wrap:anywhere;">'+escape(copy)+'</div></div>'
 ET.fromstring(markup)
 ops.append({'board_key':key,'board_id':b['id'],'page_id':b['pageId'],'step_key':sk,'operation':'replace_owned_paragraph_group','target_node_id':old,'expected_parent_id':node['parent_id'],'expected_old_text':m.native.all_text(node),'source_export_sha256':sha(path.read_bytes()),'html':markup,'html_sha256':sha(markup),'new_root_id':None,'guard':'Re-read current owned caveat and parent; replace in place only if identity/text still match. Capture new root ID and update step mapping.'})
 overrides.append({'board_key':key,'step_key':sk,'accepted_before_overlay_html_sha256':[sha(source['html'])],'replacement_html_sha256':sha(markup),'replacement_html':markup})
assert sha((HERE/'company-row-replacements.v2.json').read_bytes())==before
result={'schema':'f02.paper.company-annual-growth-caveat-addendum.v2','status':'PREPARED_NOT_APPLIED','target_file_id':m.FILE,'depends_on_row_patch_sha256':before,'copy':copy,'operations':ops,'source_overrides':overrides,'latest_FY26_FY25_column_preserved':True,'statement_caption_and_header_untouched':True,'paper_calls':0,'browser_calls':0,'native_reviewed':False}
out=HERE/'company-caveat-replacements.v2.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'path':str(out),'sha256':sha(out.read_bytes()),'targets':[o['target_node_id']for o in ops],'row_patch_unchanged':before},indent=2))
