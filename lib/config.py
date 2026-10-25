"""Load config.yml once; everything reads tunables from here."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
if getattr(__loader__, '_qledger_bootstrap_active', False):
    # The accepted outside-checkout loader supplies its actual qualified repo
    # BEFORE dotenv or config reads; __file__ remains the trusted code bundle.
    ROOT = __loader__.runtime_root(__name__)
_LOAD_ROOT = None
_LOAD_DIGEST = None


def _load_dotenv() -> None:
    """Local runs read secrets from a gitignored .env; CI uses real env vars,
    which always win over the file."""
    p = ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()


@lru_cache(maxsize=1)
def load() -> dict:
    global _LOAD_ROOT, _LOAD_DIGEST
    source_root = ROOT
    digest = None
    if getattr(__loader__, '_qledger_bootstrap_active', False):
        if source_root != __loader__.runtime_root(__name__):
            __loader__.reject('actual original ROOT or cached configuration differs')
        raw, digest = __loader__.runtime_config(__name__)
        value = yaml.safe_load(raw)
    else:
        with open(source_root / "config.yml") as f:
            value = yaml.safe_load(f)
    _LOAD_ROOT, _LOAD_DIGEST = source_root, digest
    return value


def data_dir() -> Path:
    return ROOT / load()["storage"]["data_dir"]


def site_dir() -> Path:
    return ROOT / load()["storage"]["site_dir"]


def secret(name: str) -> str | None:
    """Secrets come from env (GitHub Actions secrets locally via shell env)."""
    v = os.environ.get(name, "").strip()
    return v or None
