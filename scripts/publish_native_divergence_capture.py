"""Retain only this ordinary nightly's already computed private capture once.

No acquisition, computation, retry, catalog or public artifact. Missing native
stage outputs leave the retained capture unavailable without affecting other desks.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.research_vault import divergence_handoff as handoff

def main(*,repo_root=None,environ=None):
    environ=os.environ if environ is None else environ
    repo_root=Path(__file__).resolve().parents[1] if repo_root is None else Path(repo_root)
    payload=environ.get("NATIVE_DIVERGENCE_PAYLOAD_SHA256","")
    source=environ.get("NATIVE_DIVERGENCE_SOURCE_SHA256","")
    commit=environ.get("NATIVE_DIVERGENCE_PRODUCER_COMMIT","")
    if not payload and not source and not commit:
        print("native divergence retention: no original stage outputs")
        return 0
    result_code=0
    try:
        result=handoff.retain_staged(repo_root,expected_payload_sha256=payload,
            expected_source_sha256=source,original_producer_commit=commit,environ=environ)
        print("native divergence retention: "+("NOT_NIGHTLY" if result is None else result.state))
    except handoff.retention.CaptureEffectUnknown:
        print("native divergence retention: EFFECT_UNKNOWN; preserve original run and reconcile read-only")
        result_code=1
    except Exception as exc:
        # No source data, credentials, response body or exception messages in logs.
        print("native divergence retention unavailable: "+type(exc).__name__)
        result_code=1
    try:
        path=handoff.journal_path(repo_root,expected_payload_sha256=payload,original_producer_commit=commit,environ=environ)
        if path is not None:
            handoff.emit_step_outputs({"native_divergence_journal":str(path)},environ=environ)
    except Exception as exc:
        print("native divergence journal unavailable: "+type(exc).__name__)
        result_code=1
    return result_code

if __name__=="__main__":
    raise SystemExit(main())
