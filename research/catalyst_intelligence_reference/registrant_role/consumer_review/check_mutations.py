"""Discriminating mutants of the candidate; not production mutation testing."""
from pathlib import Path
import ast, json, shutil, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
MUTATIONS={
 'confirm_unproved_relationship':('review_projection.py',"'affected_relationship_confirmed': False", "'affected_relationship_confirmed': True"),
 'drop_review_records':('review_projection.py',"'records': selected[:limit]", "'records': []"),
 'mislabel_text_defer':('review_projection.py',"old - n", "old"),
 'hide_total_behind_limit':('review_projection.py',"'total_records': len(selected)","'total_records': min(len(selected), limit)"),
 'disable_html_escaping':('render_reference.py',"autoescape=True", "autoescape=False"),
 'truthy_access':('render_reference.py',"entitled=entitled_fixture is True", "entitled=bool(entitled_fixture)"),
 'disable_href_validation':('review_fragment.html.j2',"source_link(record.source_url)","record.source_url"),
}
report=[]
for name,(file,before,after) in MUTATIONS.items():
 with tempfile.TemporaryDirectory(prefix='catalyst-r18-mutant-') as td:
  root=Path(td); work=root/'relationship_review';shutil.copytree(HERE,work,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'))
  path=work/file;text=path.read_text();assert text.count(before)==1,(name,text.count(before));text=text.replace(before,after);path.write_text(text)
  if file.endswith('.py'):ast.parse(text)
  run=subprocess.run([sys.executable,'-m','pytest','-q','--tb=no',f'--junitxml={root}/junit.xml'],cwd=work,capture_output=True,text=True,timeout=30)
  tree=ET.parse(root/'junit.xml');suites=tree.getroot().findall('testsuite')
  failures=sum(int(s.get('failures','0')) for s in suites); errors=sum(int(s.get('errors','0')) for s in suites)
  report.append(dict(name=name,exit_code=run.returncode,assertion_failures=failures,execution_errors=errors,detected=failures>0 and errors==0))
output=HERE/'mutation_results.json';output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
if not all(r['detected'] for r in report):raise SystemExit(1)
