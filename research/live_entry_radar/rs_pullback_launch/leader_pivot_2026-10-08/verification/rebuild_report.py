"""Rebuild the delivered Markdown from byte-verified archived chapters."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED = "f73b345fa542768008c6a7271d7eacc6f46b57a26ddf3c62b18010aae65365a9"
PREFIX = (
    "# Mastermind — Leader Pivot Intelligence\n\n"
    "Research decision and implementation packet | October 7, 2026 (America/New_York)\n\n"
    "**Evidence status:** research decision delivered; target market experiments NOT_TESTED; no production or trading authority.\n\n"
)


def rebuild(root: Path) -> bytes:
    expected = json.loads((root / "verification/SOURCE_BLOBS.json").read_text(encoding="utf-8"))
    parts = []
    for name, blob in sorted(expected.items()):
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing regular source file: {name}")
        data = path.read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual != blob:
            raise ValueError(f"Source changed: {name}")
        if name.startswith("chapters/"):
            parts.append(data)
    if len(parts) != 15:
        raise ValueError("Expected exactly the original fifteen chapter files")
    data = PREFIX.encode("utf-8") + b"\n---\n\n".join(parts)
    if len(data) != 124006 or hashlib.sha256(data).hexdigest() != EXPECTED:
        raise ValueError("Reconstructed report differs from the delivered original")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = rebuild(Path(__file__).resolve().parents[1])
    with args.output.open("xb") as destination:
        destination.write(report)
    print(json.dumps({"bytes": len(report), "sha256": EXPECTED}, sort_keys=True))
