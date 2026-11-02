"""HTTP mutation controls executed inside the repository's real pytest harness.

The test framework's native LocalStore fixture policy must run; invoking fixture
bodies outside pytest is deliberately unsupported. No live service is contacted.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
TEST="tests/test_gmi_issuer_economic_context_api.py"
CONTROLS={
 "removed_final_entitlement":("test_entitlement_revoked_during_fact_read_never_serializes",
   'current_user = require_private_user(request, authorization=request.headers.get("authorization"))',
   'current_user = _user'),
 "ignored_query_controls":("test_queries_are_not_permission_or_identity_controls",
   'if request.query_params:', 'if False:'),
 "removed_principal_consistency":("test_principal_change_during_read_refuses_serialization",
   'if current_user != _user:', 'if False:'),
 "returned_unavailable_partial_result":("test_unavailable_or_wrong_contract_never_returns_partial_context",
   'if (type(value) is not dict', 'if False and (type(value) is not dict'),
}
PLUGIN = r'''import ast,os
from pathlib import Path
import pytest
from fastapi import APIRouter
from app import company_disclosures as api

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    fault=os.environ.get("GMI_TEST_HTTP_FAULT")
    if not fault:
        yield
        return
    from gmi_http_mutation_config import CONTROLS
    old,new=CONTROLS[fault][1:]
    path=Path(api.__file__)
    text=path.read_text();tree=ast.parse(text)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="issuer_economic_context")
    start=min([node.lineno]+[d.lineno for d in node.decorator_list])
    source="\n".join(text.splitlines()[start-1:node.end_lineno])+"\n"
    assert source.count(old)==1,"mutation preimage changed"
    namespace=dict(vars(api));namespace["router"]=APIRouter(prefix="/api/company-intelligence/private",route_class=api._PrivateRoute)
    exec(compile(source.replace(old,new,1),"isolated_http_mutant","exec"),namespace)
    route=item.funcargs["route"]
    endpoint=next(r for r in route[0][0].app.routes if getattr(r,"name",None)=="issuer_economic_context")
    before=endpoint.dependant.call
    endpoint.dependant.call=namespace["issuer_economic_context"]
    try:
        yield
    finally:
        endpoint.dependant.call=before
'''


def main():
    source=ROOT/"app/company_disclosures.py";before=hashlib.sha256(source.read_bytes()).hexdigest()
    rows=[]
    with tempfile.TemporaryDirectory(prefix="gmi-http-faults-") as raw:
        tmp=Path(raw)
        (tmp/"gmi_http_mutation_plugin.py").write_text(PLUGIN)
        (tmp/"gmi_http_mutation_config.py").write_text("CONTROLS = "+repr(CONTROLS))
        for name in ["control",*CONTROLS]:
            targets=[TEST+"::"+v[0] for v in CONTROLS.values()] if name=="control" else [TEST+"::"+CONTROLS[name][0]]
            report=tmp/(name+".xml")
            env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1","PYTHONPATH":str(tmp)+os.pathsep+str(ROOT)}
            if name!="control":env["GMI_TEST_HTTP_FAULT"]=name
            else:env.pop("GMI_TEST_HTTP_FAULT",None)
            run=subprocess.run([sys.executable,"-B","-m","pytest",*targets,"-q","-p","no:cacheprovider",
                "-p","gmi_http_mutation_plugin","--basetemp="+str(tmp/(name+"-state")),
                "--junitxml="+str(report)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
            if not report.exists():raise RuntimeError("NO_TEST_REPORT:"+name+":"+run.stderr[-1000:])
            suites=list(ET.parse(report).getroot().iter("testsuite"))
            counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ["tests","failures","errors","skipped"]}
            if counts["errors"] or counts["skipped"]:raise AssertionError((name,counts,run.stdout[-3000:]))
            if name=="control":
                assert run.returncode==0 and counts["failures"]==0,(name,counts,run.stdout[-3000:])
            else:
                assert run.returncode==1 and counts["failures"]==counts["tests"],(name,counts,run.stdout[-3000:])
            rows.append({"case":name,"result":"passed" if name=="control" else "fault_detected",**counts})
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    print(json.dumps({"scope":"isolated pytest HTTP transport faults; no source mutation or live state",
        "source_sha256":before,"source_unchanged":True,"results":rows},indent=2))


if __name__=="__main__":
    main()
