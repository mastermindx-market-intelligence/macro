---
key: CENSUS-PACKET-29-F12-RULING-IS-NOT-IN-THE-CONSOLIDATION
claim: >
  The 2026-09-09 expansion census records that macro#6925's public-API refusal
  ruling is carried into macro#6997, and it is not — #6997's diff contains no
  F12 public-API document and its CSV hunk touches none of the six F12 rows
  (MO-DELTA-036/037/038/039, MO-PAID-055, MO-PAID-084).
falsifier: >
  Open #6997's patch and find a hunk touching MO-PAID-055 or a file named for
  the F12 public-API admission.
so_what: >
  A records packet that trusted the census would have overwritten a live
  ruling in still-open sibling #6925. Packet 29 is record-only here; do not
  re-edit those six rows while #6925 is open.
kind: constraint
verified_at: 2026-09-09
verified_by: >
  Pre-flight this session: gh pr view 6925 --json state,mergeCommit returned
  OPEN with a null mergeCommit. The frozen spec's read of gh pr diff 6997
  --patch found zero occurrences of the phrase public API and a CSV hunk of
  twenty rows, none of them the six F12 rows. #6997 consolidates F11-3,
  F13-4, F12-6 (commercial account scope) and F09-7; it does not supersede
  #6925 (B-F12-5).
scope:
  - macro
  - research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv
  - WS:MARKET-OS
confidence: verified
---

Census entry 29's "carried into #6997" did not survive a read of the actual
diffs. The six F12 public-API rows stay with open #6925. This packet records
that fact and does not edit them.
