"""Materialize a Cboe sample qualification INSIDE existing host-private Mastermind storage.

Never downloads, publishes, triggers a live pipeline, or writes to Git/R2/Terminal.
Call from the macro repo root with python3 -m scripts.qualify_options_free_samples.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

from collectors.options_free_samples import SourceRejected, qualify_cboe_c1_sample


def _checked_root(candidate: Path) -> Path:
    home = (Path.home() / ".mastermind_private").resolve(strict=True)
    root = candidate.resolve(strict=True)
    if root == home or home not in root.parents:
        raise SourceRejected("output must be inside existing ~/.mastermind_private")
    for path in (home, root):
        mode = path.stat().st_mode
        if not stat.S_ISDIR(mode) or path.stat().st_uid != os.getuid() or mode & 0o077:
            raise SourceRejected("private directory ownership/mode is unsafe")
    return root


def qualify(root: Path, *, persist: bool = False) -> dict:
    root = _checked_root(root)
    receipt_path = root / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    filename = receipt.get("file")
    if filename != "cboe_c1_openclose_public_eval_2025-03-28_outer.zip":
        raise SourceRejected("unexpected archive name in acquisition receipt")
    archive = root / filename
    if archive.is_symlink() or receipt_path.is_symlink():
        raise SourceRejected("linked source inputs prohibited")
    if archive.stat().st_uid != os.getuid():
        raise SourceRejected("source archive ownership mismatch")
    report = qualify_cboe_c1_sample(archive.read_bytes(), receipt)
    if persist:
        out = root / "qualified_cboe_c1_sample.json"
        content = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")
        if out.exists():
            if out.read_bytes() != content:
                raise SourceRejected("existing qualification differs; do not overwrite")
        else:
            fd = os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            if out.stat().st_mode & 0o077:
                raise SourceRejected("qualification report not private")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-root", required=True, type=Path)
    ap.add_argument("--persist-private", action="store_true")
    args = ap.parse_args()
    report = qualify(args.private_root, persist=args.persist_private)
    print(json.dumps({
        "schema": report["schema"],
        "sample_session": report["effective_trade_session"],
        "rows_total": report["rows_total"],
        "rows_standard": report["rows_standard"],
        "underlyings_standard": report["underlyings_standard"],
        "rights": report["rights"],
        "persisted": args.persist_private,
        "publish": False,
        "signal_authority": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
