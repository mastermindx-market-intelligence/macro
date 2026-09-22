---
key: ETF-COVERAGE-RELATIVE-AGE-20260922
claim: >
  ETF coverage stale_days is measured against the newest saved fund snapshot, but the original page describes the matching count as filings in the last three days. Undated rows with existing snapshots also inherit the stale color.
falsifier: >
  Run python3 -m pytest tests/test_etfs_gate.py -q -k coverage_age against source 49fd490f88e1acb8a050397cc8612f2c68c765d0; if that original renderer already names the comparative reference, the freshness-copy defect is disproved.
so_what: >
  Name comparative coverage without implying recent filings. Keep missing dates neutral and explain snapshot counts through one native optional disclosure.
kind: landmine
verified_at: '2026-09-22'
verified_by: 'python3 -m pytest tests/test_etfs_gate.py -q -k coverage_'
scope:
  - 'mastermindx-market-intelligence/macro'
  - 'templates/etfs.html.j2'
  - 'tests/test_etfs_gate.py'
confidence: verified
---

Source and local browser verified; not production accepted. See research/evidence/uiux-etf-coverage-20260922/README.md for exact carrier, fixture limitations and release gate. No producer, data, fund ordering, paid row or authentication logic changes.
