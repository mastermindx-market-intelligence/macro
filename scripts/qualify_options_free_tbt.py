"""Qualify a pre-acquired Cboe TBT evaluation archive into private Mastermind research."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from collectors.options_free_samples import SourceRejected
from collectors.options_free_tbt import qualify_cboe_tbt_sample
from scripts.qualify_options_free_samples import _checked_root


def qualify(root: Path, *, persist: bool = False) -> dict:
    root = _checked_root(root)
    receipt_path = root / "cboe_tbt_receipt.json"
    if receipt_path.is_symlink():
        raise SourceRejected("linked TBT receipt prohibited")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("file") != "cboe_c1_tbt_public_eval_2025-03-28_outer.zip":
        raise SourceRejected("unexpected acquisition file identity")
    archive = root / receipt["file"]
    if archive.is_symlink() or archive.stat().st_uid != os.getuid():
        raise SourceRejected("untrusted TBT archive path")
    report = qualify_cboe_tbt_sample(archive.read_bytes(), receipt)
    if persist:
        out = root / "qualified_cboe_c1_tbt_sample.json"
        content = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
        if out.exists():
            if out.read_bytes() != content:
                raise SourceRejected("existing private TBT report differs; no overwrite")
        else:
            fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            if out.stat().st_mode & 0o077:
                raise SourceRejected("TBT report has unsafe filesystem mode")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--persist-private", action="store_true")
    opts = parser.parse_args()
    x = qualify(opts.private_root, persist=opts.persist_private)
    print(json.dumps({
        "rows": x["rows_total"],
        "classifiable_rows": x["rows_fully_classified_with_economics"],
        "unknowns": x["unknown_reasons"],
        "underlyings": x["underlyings"],
        "qualifies_quote_age": False,
        "publish": False,
        "persisted": opts.persist_private,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
