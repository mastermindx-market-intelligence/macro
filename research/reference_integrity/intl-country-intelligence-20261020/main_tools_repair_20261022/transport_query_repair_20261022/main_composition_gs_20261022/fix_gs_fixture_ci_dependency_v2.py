from pathlib import Path
import subprocess,json,hashlib,datetime,time,os,copy,yaml
R=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018");G=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_gs_20261022")
sha=lambda b:hashlib.sha256(b).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()=='d7f3becfea06fbce54c3e04de5f974e257b96023'
assert subprocess.check_output(['git','show','-s','--format=%P','HEAD'],cwd=R,text=True).strip()=='96cf630b9dffec366568216e8d5ef1125e212cbf 2d33475adef502ab6b00b8003356c1b0ad1673c0'
assert subprocess.run(['git','rev-parse','--verify','MERGE_HEAD'],cwd=R,capture_output=True).returncode!=0
p=R/'tests/test_intl_gs_foundation.py';s=p.read_text()
assert sha(p.read_bytes())=='732af7e587ed7549ae95cf003a173caf7c2f245139bb11f85936e2340372af21'
a=s.index('@pytest.fixture(scope="module")\ndef reviewed_country_theme_bytes():')
b=s.index('@pytest.mark.parametrize("case", [',a)
s=s[:a]+"@pytest.fixture(scope=\"module\")\ndef reviewed_country_theme_bytes():\n    # Retained reviewed bytes avoid requiring historical Git objects in shallow CI.\n    # Only fixture preparation removes the five known lines (comment + four\n    # declarations); both entire byte sequences must match the reviewed hashes.\n    fixture = REPO / (\n        \"research/reference_integrity/intl-country-intelligence-20261020/\"\n        \"main_tools_repair_20261022/transport_query_repair_20261022/\"\n        \"main_composition_6a4_20261022/proposed_main6a420261022_repair/theme.css\"\n    )\n    candidate = fixture.read_bytes()\n    assert hashlib.sha256(candidate).hexdigest() == _ACCEPTED_COUNTRY_THEME_PAIR[1]\n    additions = (\n        b\"  /* International country research: existing blends owned by shared theme. */\\n\",\n        b\"  --imc-summary-hover: color-mix(in srgb, var(--panel2) 65%, transparent);\\n\",\n        b\"  --imc-country-line: color-mix(in srgb, var(--line) 58%, var(--link));\\n\",\n        b\"  --imc-context-surface: color-mix(in srgb, var(--panel2) 65%, var(--panel));\\n\",\n        b\"  --imc-country-line: color-mix(in srgb, var(--link) 35%, var(--line));\\n\",\n    )\n    baseline = candidate\n    for line in additions:\n        assert baseline.count(line) == 1\n        baseline = baseline.replace(line, b\"\", 1)\n    assert hashlib.sha256(baseline).hexdigest() == _ACCEPTED_COUNTRY_THEME_PAIR[0]\n    return baseline, candidate\n\n\n"+s[b:]
s=s.replace('It adds only five --imc-* lines; no GS token-root edit is authorized.','It adds a comment and four declarations; no GS token-root edit is authorized.',1)
m=R/'.github/ci/legacy-jobs.yml';old=m.read_text()
assert sha(m.read_bytes())=='6a6d47b3b0f4a54df8722a636f18438febecfa5fc626820aadc174d0a102780f'
fixture="research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_6a4_20261022/proposed_main6a420261022_repair/theme.css"
assert sha((R/fixture).read_bytes())=='d7be48a71598c3c806deb271f346c996dc5136e1030f17546407092b6938e419'
before=yaml.safe_load(old)['jobs'];assert len(before)==349
assert len(before['international-workspace-browser']['paths'])==360
assert fixture not in before['international-workspace-browser']['paths']
start=old.index('  international-workspace-browser:\n');place=old.index('    paths:\n',start)+len('    paths:\n')
updated=old[:place]+'      # Exact reviewed country-theme fixture used by the GS freeze guard.\n      - "'+fixture+'"\n'+old[place:]
after=yaml.safe_load(updated)['jobs'];expected=copy.deepcopy(before)
expected['international-workspace-browser']['paths'].insert(0,fixture)
assert after==expected and len(after['international-workspace-browser']['paths'])==361
p.write_text(s);m.write_text(updated)
def normalized(jobs):
    value=copy.deepcopy(jobs)
    for j in value.values():
        if isinstance(j.get('paths'),list):j['paths']=sorted(j['paths'])
    return sha(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())
record={'before_manifest_sha256':sha(old.encode()),'after_manifest_sha256':sha(m.read_bytes()),'before_normalized_jobs_sha256':normalized(before),'after_normalized_jobs_sha256':normalized(after),'jobs':349,'other_job_objects_unchanged':True,'only_delta':'one exact committed theme fixture in international-workspace-browser.paths','fixture':fixture,'fixture_sha256':sha((R/fixture).read_bytes()),'browser_paths_before':360,'browser_paths_after':361,'test_sha256':sha(p.read_bytes())}
(G/'guard_fixture_ci_delta.json').write_text(json.dumps(record,indent=2)+'\n')
(G/'frozen_guard_reconciliation_v2.patch').write_bytes(subprocess.check_output(['git','diff','2d33475adef502ab6b00b8003356c1b0ad1673c0','--','tests/test_intl_gs_foundation.py'],cwd=R))
env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
command=['/tmp/intl-country-cockpit-ci-20261021/bin/python','-m','pytest','tests/test_intl_gs_foundation.py','-q']
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
with (G/'gs_foundation_final_v2.log').open('w') as log:r=subprocess.run(command,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
receipt={'command':command,'exit_code':r.returncode,'started_at':started,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-tick,2),'test_sha256':sha(p.read_bytes()),'manifest_sha256':sha(m.read_bytes()),'theme_sha256':sha((R/'templates/theme.css').read_bytes()),'fixture_sha256':sha((R/fixture).read_bytes()),'log_sha256':sha((G/'gs_foundation_final_v2.log').read_bytes()),'production_source_changed':False,'historical_git_objects_required_by_fixture':False}
(G/'gs_foundation_final_v2_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(record),flush=True);print(json.dumps(receipt),flush=True);print((G/'gs_foundation_final_v2.log').read_text()[-6000:],flush=True)
raise SystemExit(r.returncode)
