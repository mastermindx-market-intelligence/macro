#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# collect original cs_handoff_stamp; size headroom, business body unchanged.
set -e
ledger="data/capital_structure/source_manifest.jsonl"
if [ ! -f "$ledger" ]; then
  echo "::warning::no $ledger to hand off — the capital_structure job will fail closed rather than compile the committed ledger"
  exit 0
fi
# Stamped HERE, after "push market data", deliberately: that step's rebase
# runs --autostash, and on a CONFLICTED re-apply push_autostash_ok resets
# hard, leaving origin/main's committed ledger in the tree. That is still a
# sound input (#4600's restore-a-clean-ledger self-heal) but it is a
# DIFFERENT ledger, so the receipt must describe whatever actually survived
# rather than what the collectors wrote 20 minutes earlier.
#
# The ledger is SHARDED byte-exactly: $ledger is part 1 (never rewritten
# once sealed) and source_manifest.part-NNNN.jsonl continuation parts hold
# later rows, each under GitHub's 100 MiB blob limit -- the single file
# crossed it on 2026-09-27 and every nightly through 10-09 compiled a
# generation and lost it at push (GH001). The receipt therefore describes
# the LOGICAL ledger, the ordered concatenation of every part: `rows` is
# still its newline count and `sha256` still its digest (byte-for-byte the
# old shasum/wc receipt while no continuation part exists), and ONE script
# owns that arithmetic on both sides of the handoff. Appends to
# $GITHUB_OUTPUT itself; a part listing it cannot read stamps nothing, so
# the verify step refuses as "no ledger receipt".
python scripts/capital_structure_ledger_receipt.py stamp --root data/capital_structure
