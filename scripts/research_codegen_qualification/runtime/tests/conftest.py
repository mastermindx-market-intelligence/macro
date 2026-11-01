"""Load only helper modules; the fixed executable probe is never imported."""
import os
from pathlib import Path
import sys
here = Path(__file__).resolve().parent
runtime = here.parent
repo = runtime.parents[2]
transport = Path(os.environ.get("RF_QUALIFICATION_TRANSPORT_SOURCE", str(repo / "engine/research_codegen/transport.py")))
sys.path[:0] = [str(runtime), str(here), str(transport.parent)]
