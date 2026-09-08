"""Evidence-only observer of the existing builder's real macro publication.

Reuse the compact-risk proof method: do not alter inputs, VM, renderer or writer;
stop only after the normal writer has emitted macro.html. This is target proof,
never a full-site success and never a separate production publication lane.
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["MACRO_DUMP_VM"] = "1"
from scripts import build_site

SOURCE_PATHS = ("lib/macro_economic_backdrop.py", "scripts/build_site.py",
                "templates/dashboard.html.j2", "templates/_macro_economic_backdrop.html.j2",
                "templates/_macro_economic_backdrop.css.j2")
BEFORE = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCE_PATHS}
_original_write = build_site.write_page


def observe_write(path, html, *args, **kwargs):
    result = _original_write(path, html, *args, **kwargs)
    if Path(path).resolve() == ROOT / "site/macro.html":
        assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest for p, digest in BEFORE.items())
        assert 'class="ebd"' in Path(path).read_text()
        receipt = {"status": "MACRO_TARGET_WRITTEN", "full_site_build": False,
                   "utc": datetime.now(timezone.utc).isoformat(),
                   "html_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                   "source_hashes": BEFORE, "source_unchanged": True}
        Path(__file__).with_name("canonical-target-receipt.json").write_text(json.dumps(receipt, indent=2))
        print(json.dumps(receipt), flush=True)
        raise SystemExit(0)
    return result


build_site.write_page = observe_write
build_site.main()
