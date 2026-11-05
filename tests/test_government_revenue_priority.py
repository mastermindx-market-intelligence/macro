from pathlib import Path
import subprocess

def test_auth_owned_investor_priority_and_module_lifecycle():
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run(['node','--test',str(root/'tests/test_government_revenue_priority.cjs')],cwd=root,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
