from __future__ import annotations

"""Shared, read-only environment for the Q17 research scripts.

* Puts the Q17 checkout first on sys.path (never the caller's cwd package).
* Installs a minimal stand-in for ``lib.config`` BEFORE any incumbent import, so the
  incumbent modules read the licensed retained data at
  /Users/chriswong/Documents/Cluade/macro-main/data and the checkout's config.yml,
  and the real ``lib.config`` (which loads a local dotenv file at import) is never
  executed.  No secret is read; ``secret()`` always returns None.
* Hashes inputs, snapshots data-directory listings, appends run records to RUNS.log.

Research tooling only; nothing in the product imports this file.
"""

import hashlib
import json
import os
import shlex
import sys
import types
from pathlib import Path

Q = Path("/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/quant-staging-20261008/Q17")
DATA = Path("/Users/chriswong/Documents/Cluade/macro-main/data")
HERE = Q / "research" / "quant_assessment_2026_10" / "Q17_stable_factor_whitening"
RUNS_LOG = HERE / "RUNS.log"

DATA_INPUTS = [
    "edgar/fundamentals_panel.parquet",
    "edgar/eps_quarterly.parquet",
    "breadth/_closes_cache.parquet",
    "midcap_breadth/_closes_cache.parquet",
    "smallcap_breadth/_closes_cache.parquet",
    "yahoo/SPY.parquet",
    "breadth/constituents.parquet",
    "midcap_breadth/constituents.parquet",
    "smallcap_breadth/constituents.parquet",
]
CODE_INPUTS = [
    "config.yml",
    "engine/equity_factors.py",
    "engine/factor_orthogonal.py",
    "engine/factor_stable_whitening.py",
    "engine/sue.py",
    "lib/closes_panel.py",
    "lib/store.py",
    "collectors/edgar.py",
    "collectors/edgar_eps.py",
]
WATCH_DIRS = ["edgar", "breadth", "midcap_breadth", "smallcap_breadth", "yahoo"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def input_hashes() -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in DATA_INPUTS:
        p = DATA / rel
        out["data/" + rel] = sha256(p) if p.exists() else "MISSING"
    for rel in CODE_INPUTS:
        p = Q / rel
        out[rel] = sha256(p) if p.exists() else "MISSING"
    return out


def dir_listing() -> dict[str, list[str]]:
    return {d: sorted(os.listdir(DATA / d)) for d in WATCH_DIRS if (DATA / d).is_dir()}


def install_config_stub() -> None:
    if str(Q) in sys.path:
        sys.path.remove(str(Q))
    sys.path.insert(0, str(Q))
    import yaml  # noqa: PLC0415

    cache: dict[str, dict] = {}

    def load() -> dict:
        if "c" not in cache:
            with open(Q / "config.yml") as f:
                cache["c"] = yaml.safe_load(f)
        return cache["c"]

    load.cache_clear = cache.clear  # type: ignore[attr-defined]
    stub = types.ModuleType("lib.config")
    stub.ROOT = Q
    stub.load = load
    stub.data_dir = lambda: DATA
    stub.site_dir = lambda: Q / "site"
    stub.secret = lambda name: None
    import lib  # noqa: PLC0415  (Q17/lib, empty __init__)

    if not str(getattr(lib, "__file__", "")).startswith(str(Q)):
        raise RuntimeError(f"lib resolved outside Q17: {getattr(lib, '__file__', None)}")
    sys.modules["lib.config"] = stub
    lib.config = stub  # type: ignore[attr-defined]


def append_run(record: dict) -> None:
    rec = dict(record)
    rec.setdefault("command", " ".join(shlex.quote(a) for a in [sys.executable] + sys.argv))
    with open(RUNS_LOG, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
