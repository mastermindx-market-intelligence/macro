#!/usr/bin/env python3
"""Fixed root-only stdin issuer, never a generic command or path launcher."""
import os
from pathlib import Path
import sys

ROOT=Path('/opt/macro')
if (sys.platform!='linux' or os.geteuid()!=0 or len(sys.argv)!=1
        or Path(__file__).resolve()!=ROOT/'scripts/market_memory_e0_native_issuer.py'):
    raise SystemExit(77)  # No private imports, output or exception dump.
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
from engine.research_factory.market_memory_e0_native_issuer import serve
serve(sys.stdin.buffer,sys.stdout.buffer)
