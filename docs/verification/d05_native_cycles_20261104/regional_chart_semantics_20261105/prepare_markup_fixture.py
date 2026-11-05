from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path('/tmp/mastermind-d05-regional-chart-20261105-f0f7aa17')
config=json.loads((ROOT/'config.json').read_text())
source=json.loads((ROOT/'candidate_source.json').read_text())
us=Path('/Volumes/Mastermind 2/agent-workspaces/macro/web/sector-r3-chart-accessibility-20261105/.pytest_cache/d05-chart-guidance-20261105/site')
cn=Path('/Volumes/Mastermind/agent-workspaces/macro/web/d05-native-source-verification-20261104/.pytest_cache/d05-ci-recovery-82c377/china-archive/site-candidate-history')
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
provenance={'parent':config['parent'],'fixture_only':True,'method':'exact template-owned markup delta applied to sealed accepted browser fixtures; no repository/worktree change','fixtures':{},'source_files':[]}
for region,path,manifest_path,field in [('us',us,us/'fixture_provenance.json','emitted_assets'),('china',cn,cn.parent/'fixture_history_provenance.json','emitted')]:
 manifest=json.loads(manifest_path.read_text())
 for name,sha in manifest[field].items():
  assert digest(path/name)==sha,(region,name,'sealed fixture drift')
 dest=ROOT/region
 shutil.copytree(path,dest)
 provenance['fixtures'][region]={'source_path':str(path),'input_manifest_sha256':digest(manifest_path),'verified_input_files':len(manifest[field]),'before':manifest[field],'changed':{}}
for name,label in config['labels'].items():
 region='china' if name.endswith('_china') else 'us'
 path=ROOT/region/(name+'.html')
 original=path.read_text()
 template=source['templates/'+name+'.html.j2']
 generated=source['site/'+name+'.html']
 chart=re.findall(r'<div id="sc-chart"[^\n]+</div>',template)
 desc=re.findall(r'<p id="sc-chart-a11y"[^\n]+</p>',template)
 assert len(chart)==len(desc)==1
 assert generated.count(chart[0])==1 and generated.count(desc[0])==1,'Template/generated markup must match'
 text=re.sub(r'^[ \t]*<p id="sc-chart-a11y"[^\n]+</p>\n','',original,flags=re.M)
 matches=list(re.finditer(r'^([ \t]*)<div id="sc-chart"[^\n]+</div>',text,re.M));assert len(matches)==1
 match=matches[0];text=text[:match.start()]+match[1]+chart[0]+'\n'+match[1]+desc[0]+text[match.end():]
 if name=='sector_central_china':
  old='<h2><span class="l-en">Cycle map — every sector & theme on one clock</span><span class="l-zh">周期图谱 — 各板块与主题同框</span></h2>'
  assert text.count(old)==1
  text=text.replace(old,old.replace('<h2>','<h2 id="sc-cyclemap-heading">'))
 assert text.count('id="'+label+'"')==1
 text=re.sub(r'sector_cycles\.js\?v=[0-9a-f]{8}', 'sector_cycles.js?v=4f719b75',text)
 path.write_text(text)
 provenance['fixtures'][region]['changed'][name+'.html']={'before':hashlib.sha256(original.encode()).hexdigest(),'after':digest(path)}
for region in ['us','china']:
 target=ROOT/region/'sector_cycles.js'
 before=digest(target);body=(us/'sector_cycles.js').read_bytes()
 assert hashlib.sha256(body).hexdigest()==config['current_renderer_sha256']
 target.write_bytes(body)
 if before!=digest(target):provenance['fixtures'][region]['changed']['sector_cycles.js']={'before':before,'after':digest(target),'source':'f0f7aa176e600c5d21a656ae483ce3693b8c9151:templates/sector_cycles.js'}
 provenance['fixtures'][region]['emitted']={str(p.relative_to(ROOT/region)):digest(p) for p in sorted((ROOT/region).rglob('*')) if p.is_file()}
for path,text in source.items():
 b=text.encode();provenance['source_files'].append({'path':path,'parent_blob':config['parent_blobs'][path],'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
(ROOT/'fixture_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
(ROOT/'source_manifest.json').write_text(json.dumps({'parent':config['parent'],'files':provenance['source_files']},indent=2)+'\n')
print(json.dumps({'sealed_fixture_counts':{k:v['verified_input_files'] for k,v in provenance['fixtures'].items()},'source_paths':list(source),'fixture_root':str(ROOT)},indent=2))
