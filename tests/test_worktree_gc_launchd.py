"""The installed GC wrapper must carry the storage dependency from one commit."""
from pathlib import Path
from subprocess import CompletedProcess
import os
import subprocess

from scripts import worktree_gc_launchd as launcher


def test_launchd_extracts_coherent_bundle_before_running(monkeypatch):
    source = 'a' * 40
    reads = []
    def git(*args):
        if args == ('rev-parse', '--verify', 'origin/main^{commit}'):
            return CompletedProcess(args, 0, source.encode(), b'')
        if args[0] == 'show':
            reads.append(args[1])
            return CompletedProcess(args, 0, b'fixture bytes', b'')
        return CompletedProcess(args, 0, b'.git', b'')
    def run(command, **kwargs):
        folder = Path(command[1]).parent
        assert (folder/'worktree_storage.py').read_bytes() == b'fixture bytes'
        assert (folder/'config.json').read_bytes() == b'fixture bytes'
        assert len(reads) == 3 and all(ref.startswith(source+':') for ref in reads)
        return CompletedProcess(command, 0)
    monkeypatch.setattr(launcher, '_git', git)
    monkeypatch.setattr(launcher.subprocess, 'run', run)
    assert launcher.main() == 0


def test_missing_storage_dependency_refuses_before_deletion(monkeypatch):
    def git(*args):
        if args[0] == 'show' and args[1].endswith(':scripts/worktree_storage.py'):
            return CompletedProcess(args, 1, b'', b'missing')
        return CompletedProcess(args, 0, b'a'*40, b'')
    monkeypatch.setattr(launcher, '_git', git)
    monkeypatch.setattr(launcher.subprocess, 'run', lambda *a, **k: (_ for _ in ()).throw(AssertionError('must not run GC')))
    assert launcher.main() == 1


def test_flat_gc_child_imports_exact_adjacent_helper_despite_ambient_package(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    tool = bundle / 'worktree_gc.py'
    helper = bundle / 'worktree_storage.py'
    tool.write_bytes((repo/'scripts/worktree_gc.py').read_bytes())
    helper.write_bytes((repo/'scripts/worktree_storage.py').read_bytes())
    ambient = tmp_path / 'ambient'
    package = ambient / 'scripts'
    package.mkdir(parents=True)
    (package/'__init__.py').write_text('')
    (package/'worktree_storage.py').write_text("raise RuntimeError('ambient decoy imported')\n")
    code = (
        "import runpy; ns=runpy.run_path(" + repr(str(tool)) + "); "
        "print(ns['worktree_storage'].__file__)"
    )
    env = {**os.environ, 'PYTHONPATH':str(ambient), 'PYTHONDONTWRITEBYTECODE':'1'}
    result = subprocess.run([os.sys.executable,'-B','-c',code],capture_output=True,text=True,env=env)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).resolve() == helper.resolve()
