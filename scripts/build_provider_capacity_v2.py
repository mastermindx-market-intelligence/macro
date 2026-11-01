"""Native V2 is an embedded fixed-Control producer, not a facts-in CLI."""
import asyncio
import json
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.provider_capacity_v2 import build_snapshot

if __name__ == '__main__':
    print(json.dumps(asyncio.run(build_snapshot()), sort_keys=True, allow_nan=False))
