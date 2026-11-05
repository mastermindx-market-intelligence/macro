from pathlib import Path
import hashlib,importlib.util,json
ROOT=Path('/tmp/mastermind-d05-regional-chart-20261105-f0f7aa17')
source=json.loads((ROOT/'candidate_source.json').read_text())
target=ROOT/'citation_inputs';target.mkdir(exist_ok=True)
for path,text in source.items():
 if path.startswith('templates/'):
  p=target/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
module=ROOT/'copydeck_contract.py'
raw=module.read_bytes()
assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='df39073f927e40c3e5649676b7a4f178d2b97b60'
spec=importlib.util.spec_from_file_location('d05_existing_copydeck_contract',module)
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract);contract.REPO=target
rows=json.loads((ROOT/'citation_rows.json').read_text())
results=[{'board':r['board'],'key':r['key'],'source':r['entry']['source'],'gaps':contract.row_gaps(r['entry'])} for r in rows]
report={'schema':'d05.changed_template_citations.v1','parent':'f0f7aa176e600c5d21a656ae483ce3693b8c9151','validator_blob':'df39073f927e40c3e5649676b7a4f178d2b97b60','method':'existing repository row_gaps helper over every copy-deck citation referencing a changed template; other source citations were not rerun','rows':results,'passed':not any(r['gaps'] for r in results)}
(ROOT/'citation_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'rows':len(results),'failures':[r for r in results if r['gaps']]},ensure_ascii=False))
raise SystemExit(0 if report['passed'] else 1)
