"""The explicit research commands must run outside the repository working directory."""
from pathlib import Path
import os
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('name',['benchmark','model_audit'])
def test_entrypoint_bootstraps_owner_repo_from_foreign_cwd(name,tmp_path):
    env=dict(os.environ);env.pop('PYTHONPATH',None)
    result=subprocess.run([sys.executable,str(ROOT/f'scripts/research/market_navigator_{name}.py'),'--help'],
        cwd=tmp_path,env=env,text=True,capture_output=True,timeout=20)
    assert result.returncode==0,result.stderr
    assert 'usage:' in result.stdout.lower()
