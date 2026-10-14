#!/usr/bin/env python3
"""Stamp or verify the capital-structure handoff receipt over the SHARDED source ledger.

``daily.yml`` hands tonight's source ledger from ``collect`` to the
``capital_structure`` job as an artifact and proves the bytes that landed are
tonight's by comparing a receipt ``collect`` stamped (``rows``, ``sha256``) with
what the download produced. Until 2026-10 the receipt was ``wc -l`` and ``shasum``
over one file. The ledger is now sharded byte-exactly across
``source_manifest.jsonl`` (part 1, never rewritten once sealed) and
``source_manifest.part-NNNN.jsonl`` continuation parts, each under GitHub's
100 MiB blob limit (DEC:CS-V2-SOURCE-LEDGER-SHARDS-BYTE-EXACTLY) -- the single
file crossed that limit on 2026-09-27 and every nightly through 10-09 compiled a
generation and lost it at push. So the receipt describes the LOGICAL ledger, the
ordered concatenation of every part, and both sides of the handoff share this one
implementation of the arithmetic: ``rows`` is still the newline count and
``sha256`` still the digest of the bytes, byte-for-byte the old shell receipt
while no continuation part exists.

    stamp  --root data/capital_structure
        Appends ``sha256=`` / ``rows=`` to ``$GITHUB_OUTPUT`` when set. An absent
        ledger warns and exits 0 (the capital_structure job then fails closed);
        an unreadable part listing stamps nothing and exits 1 -- the step is
        continue-on-error by design, so the refusal surfaces in the verify step.
    verify --root data/capital_structure --expect-sha256 <hex> --expect-rows <n>
        Exits 1 on a missing receipt, an absent ledger, an unreadable part
        listing, or a mismatch; 0 when the logical ledger matches the receipt.

GitHub annotations are printed bare at line start, never through a logger
(tests/test_gh_annotation_line_start.py).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from engine.capital_structure.source_identity import ManifestIdentityError  # noqa: E402
from engine.capital_structure.source_ledger_io import (  # noqa: E402
    source_ledger_path,
    source_ledger_receipt,
)

TITLE = "capital-structure-handoff"


def _describe(receipt: dict) -> str:
    parts = ", ".join(
        f"{part['name']} {part['rows']} rows / {part['bytes']} bytes"
        for part in receipt["parts"]
    )
    return f"{len(receipt['parts'])} part(s), {receipt['bytes']} bytes: {parts}"


def _emit_outputs(receipt: dict) -> None:
    target = os.environ.get("GITHUB_OUTPUT")
    if not target:
        return
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(f"sha256={receipt['sha256']}\n")
        handle.write(f"rows={receipt['rows']}\n")


def stamp(root: Path) -> int:
    ledger = source_ledger_path(root)
    try:
        receipt = source_ledger_receipt(ledger)
    except ManifestIdentityError as exc:
        print(
            f"::warning title={TITLE}::source ledger parts under {root.as_posix()} are "
            f"unreadable, no receipt stamped — the capital_structure job will fail "
            f"closed rather than compile an unproven ledger: {exc}",
            flush=True,
        )
        return 1
    if receipt is None:
        print(
            f"::warning::no {ledger.as_posix()} to hand off — the capital_structure job "
            f"will fail closed rather than compile the committed ledger",
            flush=True,
        )
        return 0
    _emit_outputs(receipt)
    print(
        f"capital-structure handoff stamped: {receipt['rows']} rows, sha256 {receipt['sha256']}",
        flush=True,
    )
    print(f"capital-structure ledger parts: {_describe(receipt)}", flush=True)
    return 0


def verify(root: Path, expect_sha256: str, expect_rows: str) -> int:
    ledger = source_ledger_path(root)
    expect_sha256 = (expect_sha256 or "").strip()
    expect_rows = (expect_rows or "").strip()
    if not expect_sha256:
        print(
            f"::error title={TITLE}::collect published no ledger receipt. Its stamp and "
            f"upload steps are continue-on-error by design (they must never red the "
            f"market plane), so their failure surfaces HERE. Refusing to compile: "
            f"without the receipt this job cannot tell tonight's ledger from the "
            f"committed one.",
            flush=True,
        )
        return 1
    try:
        receipt = source_ledger_receipt(ledger)
    except ManifestIdentityError as exc:
        print(
            f"::error title={TITLE}::source ledger parts under {root.as_posix()} are "
            f"unreadable after the artifact download; refusing to compile: {exc}",
            flush=True,
        )
        return 1
    if receipt is None:
        print(
            f"::error title={TITLE}::{ledger.as_posix()} is absent after the artifact download.",
            flush=True,
        )
        return 1
    actual_rows = str(receipt["rows"])
    actual_sha = receipt["sha256"]
    rows_disagree = bool(expect_rows) and expect_rows != actual_rows
    if actual_sha != expect_sha256 or rows_disagree:
        print(
            f"::error title={TITLE}::ledger mismatch — collect stamped {expect_rows} rows / "
            f"{expect_sha256}, this tree holds {actual_rows} rows / {actual_sha}. The "
            f"likeliest cause is that the artifact did not land ON TOP of the checkout, "
            f"leaving the last COMMITTED ledger in place; compiling that would reproduce "
            f"yesterday byte-for-byte, commit nothing, and freeze the lane green.",
            flush=True,
        )
        print(f"capital-structure ledger parts: {_describe(receipt)}", flush=True)
        return 1
    print(
        f"capital-structure handoff verified: {actual_rows} rows, sha256 {actual_sha}",
        flush=True,
    )
    print(f"capital-structure ledger parts: {_describe(receipt)}", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    stamp_parser = sub.add_parser("stamp", help="stamp the receipt (collect side)")
    stamp_parser.add_argument("--root", default="data/capital_structure", type=Path)
    verify_parser = sub.add_parser("verify", help="verify the receipt (capital_structure side)")
    verify_parser.add_argument("--root", default="data/capital_structure", type=Path)
    verify_parser.add_argument("--expect-sha256", default="")
    verify_parser.add_argument("--expect-rows", default="")
    args = parser.parse_args(argv)
    if args.command == "stamp":
        return stamp(args.root)
    return verify(args.root, args.expect_sha256, args.expect_rows)


if __name__ == "__main__":
    sys.exit(main())
