#!/usr/bin/env python3
"""Reproducible, local-only D05 preview. Run with PYTHONPATH=. from repository root.

Dependencies: Jinja2 plus the repository's i18n imports. Uses dated committed
fixtures; it never recalculates a market model, writes a forward log, or deploys.
"""
from pathlib import Path
import argparse, ast, copy, hashlib, json, os, posixpath, re, shutil, subprocess, tempfile
from urllib.parse import urlsplit
from jinja2 import Environment, FileSystemLoader, ChoiceLoader, DictLoader
from engine import i18n
root=Path(os.environ.get('D05_SOURCE_ROOT',str(Path(__file__).resolve().parents[3])))
parser=argparse.ArgumentParser(description='Build a local D05 candidate from archived committed inputs; no engine run or forward-log write.')
parser.add_argument('--out', type=Path)
parser.add_argument('--scenario', choices=['archive','coherent','same-date-mismatch','mixed-series','missing-extras'], default='archive',
                    help='Synthetic scenarios exercise the real publication producer; none is live market evidence.')
parser.add_argument('--candidate-overlay', type=Path, help='Explicit local candidate text map; source hashes are recorded. Never used by production builders.')
args=parser.parse_args()
overlay=json.loads(args.candidate_overlay.read_text()) if args.candidate_overlay else {}
if not isinstance(overlay,dict) or any(not isinstance(k,str) or not isinstance(v,str) or '..' in k.split('/') or not k.startswith(('templates/','scripts/')) for k,v in overlay.items()):
    raise ValueError('Candidate overlay must be an explicit templates/scripts text map')
out=args.out or Path(tempfile.mkdtemp(prefix='d05-native-preview-'))
out.mkdir(parents=True,exist_ok=True)
source_ref='c53915f6d67078d5c0aeaf73bf85ddea1a23de03'
fixture_label='archived-source' if args.scenario=='archive' else 'synthetic-'+args.scenario
env=Environment(loader=ChoiceLoader([DictLoader({k[len('templates/'):]:v for k,v in overlay.items() if k.startswith('templates/')}),FileSystemLoader(root/'templates')]),autoescape=False)
env.globals.update(td=i18n.td,tr=i18n.tr,t=i18n.t)
for name in ['sector_central','sector_cycles']:
    html=env.get_template(name+'.html.j2').render(basket_member_syms=['SPY'])
    html=html.replace('<body ', '<body data-d05-fixture="'+fixture_label+'" ',1)
    html=html.replace('</body>','<div style="position:fixed;bottom:0;left:0;z-index:100000;background:var(--panel);color:var(--muted);padding:3px 8px;font:11px sans-serif">D05 TEST FIXTURE · '+fixture_label+' · not live</div></body>')
    (out/(name+'.html')).write_text(html)
# Re-render an actual archived Members payload with the current complete template.
# It is a dated display fixture, not a new membership history or publication.
member_path='basket/us_sector_energy.html'
member_archive=subprocess.check_output(['git','-C',str(root),'show',source_ref+':site/'+member_path],text=True)
match=re.search(r'const\s+DETAIL\s*=\s*',member_archive)
if not match: raise ValueError('Archived Members DETAIL assignment missing')
member_detail,_=json.JSONDecoder().raw_decode(member_archive[match.end():])
builder=overlay.get('scripts/build_theme_detail.py') or (root/'scripts/build_theme_detail.py').read_text()
pure=[node for node in ast.parse(builder).body if isinstance(node,ast.FunctionDef) and node.name in {'_member_rows','_detail_payload'}]
if len(pure)!=2: raise ValueError('Current Members source helpers missing')
helpers={'hashlib':hashlib,'json':json}
exec(compile(ast.Module(body=pure,type_ignores=[]),str(root/'scripts/build_theme_detail.py'),'exec'),helpers)
rows,state=helpers['_member_rows']({'members':member_detail.get('members')})
member_detail.update(members=rows,members_state=state)
detail_json,member_source=helpers['_detail_payload'](member_detail)
member_html=env.get_template('basket_detail.html.j2').render(detail_json=detail_json,members_source_id=member_source,
    basket_name=member_detail['basket'].get('name','Energy'),generated_utc='DATED FIXTURE — not live',
    theme_research_mount=None,back_href=member_detail.get('back','../sector_central.html'),
    back_label_en='Sector Intelligence',back_label_zh='行业智慧')
member_html=member_html.replace('<body','<body data-d05-fixture="'+fixture_label+'"',1)
(out/'basket').mkdir(exist_ok=True)
(out/member_path).write_text(member_html)
pages=['sector_central.html','sector_cycles.html',member_path]
assets=set(re.findall(r'(?:src|href)=[\'"]([^\'"?#]+)', '\n'.join((out/name).read_text() for name in pages)))
assets|={posixpath.normpath(posixpath.join('basket',a)) for a in re.findall(r'(?:src|href)=[\'"]([^\'"?#]+)',member_html) if a.startswith('../')}
assets|={'sector_dossier_cycle.js','sector_dossier_cycle.css','shared_shell_bridge.js','shared_shell.css','supabase.js','terminal_overlay.js','account.js'}
assets|={'sector_cycles_data.js','sector_cycles_series_data.js','sector_cycles_narr_data.js','sector_cycles_dna_data.js','sector_central_data.js'}
# Runtime assets come from this candidate; archived market inputs stay dated.
runtime_ref=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
known=set(subprocess.check_output(['git','-C',str(root),'ls-tree','-r','--name-only',source_ref,'site'],text=True).splitlines())
runtime_known=set(subprocess.check_output(['git','-C',str(root),'ls-tree','-r','--name-only',runtime_ref,'site'],text=True).splitlines())
runtime_assets={}
data_assets={'sector_cycles_data.js','sector_cycles_series_data.js','sector_cycles_narr_data.js','sector_cycles_dna_data.js','sector_central_data.js'}

def local_asset(value, parent=''):
    parsed=urlsplit(value)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    name=posixpath.normpath(parsed.path.lstrip('/') if parsed.path.startswith('/') else posixpath.join(parent,parsed.path))
    if name=='..' or name.startswith('../') or Path(name).suffix not in {'.js','.css','.woff2','.woff','.svg'}:
        return None
    return name

pending={name for a in assets if (name:=local_asset(a))}
copied=set()
while pending:
    a=pending.pop()
    if a in copied:
        continue
    copied.add(a)
    dst=out/a; dst.parent.mkdir(parents=True,exist_ok=True)
    src=root/'templates'/a
    if a in data_assets and 'site/'+a in known:
        body=subprocess.check_output(['git','-C',str(root),'show',source_ref+':site/'+a])
        origin=source_ref+':site/'+a
    elif 'templates/'+a in overlay:
        body=overlay['templates/'+a].encode('utf-8')
        origin='candidate-overlay:templates/'+a
    elif src.exists():
        body=src.read_bytes()
        origin='working-tree:templates/'+a
    elif 'site/'+a in runtime_known:
        body=subprocess.check_output(['git','-C',str(root),'show',runtime_ref+':site/'+a])
        origin=runtime_ref+':site/'+a
    elif 'site/'+a in known:
        body=subprocess.check_output(['git','-C',str(root),'show',source_ref+':site/'+a])
        origin=source_ref+':site/'+a
    else:
        print('Absent optional asset:',a)
        continue
    dst.write_bytes(body)
    runtime_assets[a]={'source':origin,'sha256':hashlib.sha256(body).hexdigest()}
    if Path(a).suffix=='.css':
        css=body.decode('utf-8')
        dependencies=re.findall(r'url\(\s*[\'"]?([^\'")\s]+)',css)
        dependencies+=re.findall(r'@import\s+[\'"]([^\'"]+)',css)
        pending.update(name for value in dependencies if (name:=local_asset(value,posixpath.dirname(a))) and name not in copied)
# The page fetches these optional panels; use committed evidence when present.
for a in ['basketdata/baskets.json','marketdata/rotation_events.json','marketdata/sector_fragmentation.json']:
    if 'site/'+a in known:
        dst=out/a;dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(subprocess.check_output(['git','-C',str(root),'show',source_ref+':site/'+a]))
provenance={'members_source_id':member_source,'member_input_sha256':hashlib.sha256(member_archive.encode()).hexdigest(),'candidate_overlay':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in overlay.items()},'fixture_only':True,'scenario':args.scenario,'source_ref':source_ref,'runtime_ref':runtime_ref,'runtime_assets':runtime_assets,'inputs':{}}
if args.scenario!='archive':
    from engine.leadership_rotation_context import measured_group_read
    from scripts._cycles_payload import publication_scripts, FAMILY_KEYS

    def archived(name, variable):
        raw=(out/name).read_bytes()
        provenance['inputs'][name]=hashlib.sha256(raw).hexdigest()
        text=raw.decode('utf-8').strip()
        match=re.fullmatch(r'window\.'+re.escape(variable)+r'\s*=\s*(.*?)\s*;?',text,re.S)
        if not match: raise ValueError('Expected one archived data assignment: '+name)
        return json.loads(match.group(1))

    full=archived('sector_cycles_data.js','SECTOR_CYCLES')
    series=archived('sector_cycles_series_data.js','SECTOR_CYCLES_SERIES')
    narr=archived('sector_cycles_narr_data.js','SECTOR_NARR')
    dna=archived('sector_cycles_dna_data.js','SECTOR_DNA')
    central=archived('sector_central_data.js','SECTOR_CENTRAL')
    records={row['id']:row for family in FAMILY_KEYS for row in full.get(family,[])}
    allowed={'price','osc','turns','fx','usd_record','rs_history'}
    for eid,part in series.items():
        if eid not in records or not isinstance(part,dict) or not set(part)<=allowed:
            raise ValueError('Archived split shape cannot be used for fixture reconstruction')
        records[eid].update(part)
    full['meta']['fixture_only']=True
    # These are NEW, explicitly synthetic test publications. No assertion is
    # made that the unstamped archives were originally published atomically.
    sources={kind:{'status':'available','reason':'fixture_only','records':len(value)}
             for kind,value in [('narr',narr),('dna',dna)]}
    publication=publication_scripts(full,narr,dna,sources=sources)
    central_input=full
    if args.scenario in {'same-date-mismatch','mixed-series'}:
        changed=copy.deepcopy(full)
        row=next(row for row in changed['sectors'] if row.get('price'))
        row['price'][0]['v'] += 1
        if args.scenario=='same-date-mismatch': central_input=changed
        else: publication['series']=publication_scripts(changed,narr,dna,sources=sources)['series']
    central['measured_read']=measured_group_read(central_input)
    (out/'sector_central_data.js').write_text('window.SECTOR_CENTRAL='+json.dumps(central,separators=(',',':'))+';\n')
    for kind,suffix in [('core','data'),('series','series_data'),('narr','narr_data'),('dna','dna_data')]:
        (out/('sector_cycles_'+suffix+'.js')).write_text(publication[kind])
    if args.scenario=='missing-extras': (out/'sector_cycles_narr_data.js').unlink()
# The actual shared-shell injector owns document markers and paired-asset digests.
from lib.shared_shell import inject_shared_shell_text
for name in pages:
    prefix='../' if '/' in name else ''
    html=(out/name).read_text()
    html=inject_shared_shell_text(html,prefix,site_dir=out)
    (out/name).write_text(html)
# Additional controlled display fixtures exercise Members semantics independently
# of the real route census. They never claim supported regional live coverage.
variant_dir=out/'.d05-fixtures';variant_dir.mkdir(exist_ok=True)
variants={}
for name,region,rows,state in [
    ('empty','us',[],'empty'),('unavailable','us',[],'unavailable'),
    ('duplicate','us',[{'symbol':'XOM'},{'symbol':'XOM'}],'available'),
    ('canada','canada',[{'symbol':'CNQ.TO'},{'symbol':'XEG.TO'}],'available'),
    ('china','china',[{'symbol':'000001.SZ'},{'symbol':'512690.SS'}],'available'),
    ('hk','hk',[{'symbol':'00700.HK'}],'available'),
]:
    value=copy.deepcopy(member_detail)
    directory={'us':'basket','canada':'basket_canada','china':'basket_china','hk':'basket_hk'}[region]
    value.update(region=region,members=rows,members_state=state,as_of=None)
    value['basket']['id']='d05_fixture'
    value['basket']['name']='D05 controlled display fixture'
    value['stock_base']={'us':'../stock.html#','canada':'../canada_stock.html#','china':'../china_lookup.html#','hk':'../hk_lookup.html#'}[region]
    value['basket']['cycle']=None
    body,stamp=helpers['_detail_payload'](value)
    html=env.get_template('basket_detail.html.j2').render(detail_json=body,members_source_id=stamp,
        basket_name=value['basket']['name'],generated_utc='CONTROLLED FIXTURE — not live',
        theme_research_mount=None,back_href=value.get('back'),back_label_en='Sector Intelligence',back_label_zh='行业智慧')
    target=variant_dir/('members-'+name+'.html');target.write_text(html)
    variants[name]={'path':'/'+directory+'/d05_fixture.html','file':str(target.resolve()),'sourceId':stamp,'state':state,'symbols':[m['symbol'] for m in rows]}
(out/'member_variants.json').write_text(json.dumps(variants,indent=2)+'\n')
(out/'fixture_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print('Preview:',out,'scenario:',args.scenario,'assets:',len(assets))
