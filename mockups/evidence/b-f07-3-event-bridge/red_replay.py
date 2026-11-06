import os, subprocess, sys, types
from pathlib import Path
root=Path.cwd()
sys.path.insert(0,str(root))
import engine
head=sys.argv[1]
for name in ("valuation_event_bridge", "valuation_assumptions"):
    filename=f"engine/{name}.py"
    source=subprocess.check_output(["git","show",f"{head}:{filename}"],text=True)
    module=types.ModuleType(f"engine.{name}")
    module.__file__=str(root/filename)
    sys.modules[module.__name__]=module
    setattr(engine,name,module)
    exec(compile(source,module.__file__,"exec"),module.__dict__)
import pytest
raise SystemExit(pytest.main(["tests/test_valuation_event_bridge.py","-q","-p","no:cacheprovider","--basetemp",str(root/".heal-7134"/f"pytest-red-{head}"),"-k","vocab_closure or populates_latest_event_bridge_from_spine or reads_validated_capital_spine or ignores_nonfilings"]))
