from pathlib import Path
import json,hashlib,datetime
w=Path.cwd();b=Path(__file__).parent;root=w/'mockups/evidence/prophet-p0b-zero-fouc';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=root/'manifest.json';prior_manifest_sha256=h(p);m=json.loads(p.read_text());old=m['repair_extension'];ext=dict(old);ext['browser_receipts']={}
for market,name in [('hk','mobile-layout.json'),('ca','mobile-layout-canada.json')]:
 r=json.loads((root/name).read_text());matrix=r['owner_projection_matrix'];assert r['pass'] and matrix['pass'];assert matrix['primary_passed']==48 and matrix['degraded_controls_passed']==16 and matrix['screenshot_count']==8;assert len(matrix['cases'])==64 and all(c['pass'] for c in matrix['cases'])
 assert r['fixture_receipt']['sha256']==h(root/'rendered-fixture.json')
 assert r['verifier']['sha256']==h(w/r['verifier']['path'])
 for group in ['construction_inputs','loaded_assets']:
  for path,v in r[group].items():assert h(w/path)==(v if isinstance(v,str) else v['sha256']),(group,path)
 ext['browser_receipts'][market]={'path':str((root/name).relative_to(w)),'sha256':h(root/name),'pass':True,'primary_cases':48,'degraded_control_cases':16,'screenshots':8}
ext['fixture_receipt']={'path':str((root/'rendered-fixture.json').relative_to(w)),'sha256':h(root/'rendered-fixture.json')};ext['screenshots']=[{'path':row['path'],'sha256':h(w/row['path'])} for row in old['screenshots']];assert len(ext['screenshots'])==16;ext['generated_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();ext['pass']=True;m['repair_extension_history'].append({'extension':old,'prior_manifest_sha256':prior_manifest_sha256,'source_head':'e652575ffd5162c62b4491585ff5ef632a97b064'});m['repair_extension']=ext;p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
report={'p0b_primary':96,'p0b_degraded':32,'screenshot_count':16,'screenshots_unchanged':old['screenshots']==ext['screenshots'],'actual_inputs_verified':True,'old_extension_sha256':hashlib.sha256(json.dumps(old,sort_keys=True).encode()).hexdigest(),'new_extension_sha256':hashlib.sha256(json.dumps(ext,sort_keys=True).encode()).hexdigest(),'reason':'Existing builder incorporates protected main shared theme change; no excluded-product source edits','claims':ext['claims']};(b/'P0B_REQUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
