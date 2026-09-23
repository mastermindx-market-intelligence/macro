# D03 Cycle Source-Readiness Census — 2026-09-23

## SOURCE_SHA

- OBSERVED: `10166ad5272f8ca24161aed5bdd8d3980271489e` — detached census base before the skeleton commit, as returned by `git rev-parse HEAD`; at that moment it was the tip of `origin/main` (`git rev-parse origin/main`, rc 0).
- INFERRED: anchor facts cited below use `10166ad5272f`, not the PR head, because they read immutable committed source objects. Later `origin/main` fast-forwards do not change those object contents; a post-read SHA re-check must be made if a claim is changed or challenged.

## ANCHORS READ

- D03 requires exact usable dates, field semantics, vintage/correction lineage, original-universe coverage, delistings, publication/processing rights and source costs; forbids backdating current membership/events, guessed availability lags, relabeling broad series as granular subthemes, and assumed licenses: `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/DECISION_REGISTER.json:62@10166ad5272f`–`:68@10166ad5272f`.
- Q01 requires decision-time source revisions and owner clocks, controls current-only discovery and future labels, and maps irrecoverable history to prospective-only use: `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/RESEARCH_DOCKET.json:6@10166ad5272f`–`:15@10166ad5272f`.
- Q07 requires a Cycle source-readiness candidate selected by coverage/mapping before return inspection, with vintage orders/backlog/shipments/inventories/production, issuer segments and failure histories: `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/RESEARCH_DOCKET.json:172@10166ad5272f`–`:181@10166ad5272f`.
- Configured vintage set: `config.yml:124@10166ad5272f`–`:157@10166ad5272f`.
- ALFRED/FRED dataset rows: `config/dataset_registry.yml:199@10166ad5272f`–`:248@10166ad5272f`.
- Publication-lag table and business-cycle vintage map: `engine/business_cycle.py:124@10166ad5272f`–`:140@10166ad5272f`.
- ALFRED collection, initial-release reader and as-of reader: `collectors/fred.py:176@10166ad5272f`–`:195@10166ad5272f`; `:239@10166ad5272f`–`:262@10166ad5272f`.
- Local-store depth audit contract and verdict thresholds: `scripts/audit_alfred_depth.py:1@10166ad5272f`–`:17@10166ad5272f`; `:54@10166ad5272f`–`:95@10166ad5272f`.

## Q1 VINTAGE LEG INVENTORY

TODO

## Q2 GRANULAR M3 SERIES

TODO

## Q3 ISSUER-TO-DOMAIN MAPPING

TODO

## Q4 RIGHTS

TODO

## Q5 DATA-INDEPENDENT READINESS RULE + CANDIDATES

TODO

## Q6 GAPS + MUST-NOTS

TODO

## EVIDENCE INDEX

TODO
