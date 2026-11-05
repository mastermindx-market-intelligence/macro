#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# collect original collectors; size headroom, business body unchanged.
set -e
if [ -n "$FRED_API_KEY" ]; then echo "::notice::FRED_API_KEY present — using official API"; else echo "::warning::FRED_API_KEY ABSENT — check repo Settings > Secrets and variables > Actions > Repository secrets"; fi
# --exclude-group asia: China/HK collectors run in their own asia-close shard
# (after the Asia cash close), not here — keeps this US-evening run lean.
# --skip-shadow-importance: the ~13-14m shadow passes run standalone in
# collect_tail (2026-07-14 split) — off the engine job's critical path.
# sec_capital_structure_companyfacts is serially registered immediately
# after sec_capital_structure in scripts.collect's shared SEC host group.
# It can therefore consume only same-run verified complete-submission
# anchors, while retaining raw Company Facts JSON separately and without
# invoking any share-count consumer. Immutable Parquet generations and
# chained receipts are installed/read back before its tiny current pointer
# advances; any failure leaves the prior authenticated generation selected.
# sam_gov_opportunities is excluded because government-revenue-live.yml
# is its sole serialized ledger owner. Two workflows must never merge and
# overwrite the same revision/document Parquets concurrently.
# Existing collector step exposes one run-local time fence; the source
# must have been evaluated in THIS execution, not merely earlier on
# the same completed market session.
echo "started_at=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$GITHUB_OUTPUT"
python -m scripts.collect --exclude-group asia --exclude sam_gov_opportunities --skip-shadow-importance
