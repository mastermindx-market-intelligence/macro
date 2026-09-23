# D03 Issuer/Event Source-Readiness Census — 2026-09-23

## SOURCE_SHA

- OBSERVED: `SOURCE_SHA = a1a0a05e6adcdf007170bceaa7fbcd3323e333fc`; command `git rev-parse HEAD`; output and rc=0.
- OBSERVED: HEAD was detached at that commit. Later inspection reported `HEAD (no branch)` and `origin/claude/pu-w2-d03-issuer-source-census` at skeleton commit `ba138b6800fe9859924497df5e2c35713c23d27b`; `origin/main` had independently advanced to `ed4c7b0223c7436d72aea0fdf03d7fe10926d6a2` before this record was completed. All code/config citations below therefore use blob evidence from SOURCE_SHA rather than the current working tree.
- OBSERVED: the record path is `research/prophet_v4/r6_program/wave2/D03_ISSUER_EVENT_SOURCE_READINESS_CENSUS_2026-09-23.md`.

## ANCHORS READ

- OBSERVED, code/config contracts only: `engine/stock_identity/`, `engine/ledger_identity.py`, `engine/institutional_census/`, `engine/earnings_release/`, `engine/earnings_catalyst.py`, `engine/earnings_qual.py`, `engine/group_earnings.py`, `engine/earnings_transcript_intake.py`, `engine/earnings_blackout.py`, `engine/prophet_candidate_state_sources.py`, `engine/us_candidate_episode.py` and `engine/vintage_stamp.py`.
- OBSERVED: governing files and rulings `config/identity_seams.yml`, `config/theme_graph_identity_breaks.yml`, `config/dataset_registry.yml`, `config/press_sources.yml`, `config/narrative_sources.yml`, `config/release_forecast_model_registry.yml`, `research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-C-01_2026-09-23.md` and `SEAT_RULING_R6-D05-01_2026-09-23.md`.
- OBSERVED, verbatim boundary: D03 requires exact dates/semantics/vintage lineage/coverage/delistings/rights and costs, forbids backdating current sets, guessed lags, relabeled broad industry series and assumed licenses (`research/prophet_v4/r6_fable_meta_ceo_handoff/effective/DECISION_REGISTER.json:62-88@a1a0a05e6adc`). Q01 requires exact revisions and owner clocks, explicit correction/current-discovery/late-capture controls, and refuses any PIT path depending on a current body, later membership, future label or unproven clock (`research/prophet_v4/r6_fable_meta_ceo_handoff/effective/RESEARCH_DOCKET.json:6-15@a1a0a05e6adc`). C-01 accepts consensus as unlicensed, requires truth about the mixed `fact:revenue` units, and does not authorize dispatch or promotion (`research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-C-01_2026-09-23.md:7-26@a1a0a05e6adc`); D05 neither promotes a signal nor authorizes DDL (`research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-D05-01_2026-09-23.md:18-21@a1a0a05e6adc`).

## Q1 IDENTITY HISTORY

- VERDICT: **FOUND, but split and incomplete.** Dated ticker aliases and two curated event registries exist; issuer lineage and general lifecycle history do not.
- OBSERVED: the registered spine has five PRODUCED, on-demand, DOMAIN_AUTHORITY datasets: `reference.security_master` (grain `[security_id]`; mint-once; issuer state/evidence; effective and ingest clocks; superseded duplicate-mint state), `reference.vendor_aliases` (dated aliases), `reference.issuer_master`, and append-only issuer/security migration receipts (`config/dataset_registry.yml:252-566@a1a0a05e6adc`).
- OBSERVED: issuer CIK linkage is explicitly not historical. The master's own notes say “Historical issuer lineage is explicitly UNAVAILABLE” and that CIK evidence is a current-registrant observation with no `asof` (`config/dataset_registry.yml:360-365@a1a0a05e6adc`); `IssuerMaster` answers only which securities an issuer owns TODAY (`config/dataset_registry.yml:476-485@a1a0a05e6adc`).
- OBSERVED: the identity seam declares no general lifecycle model (`config/identity_seams.yml:49-79@a1a0a05e6adc` and `config/identity_seams.yml:94@a1a0a05e6adc`). Its nullable security state models only a duplicate-mint correction, not delisting existence.
- OBSERVED: `reference.vendor_aliases` has grain `[vendor, vendor_symbol, valid_from]`, an inclusive/open `valid_from`, and an exclusive/open `valid_to`; it explicitly distinguishes historical naming spaces (`yahoo`, `membership`, `ledger`) from current fetch/store catalogs (`config/dataset_registry.yml:383-446@a1a0a05e6adc`). Thus a reader can answer what a given space called a security on a date for covered names and dates.
- OBSERVED: `reference.issuer_migrations` and `reference.security_migrations` are append-only correction receipts with old/new values, reasons, evidence and migration time—not a general event source (`config/dataset_registry.yml:487-565@a1a0a05e6adc`).
- OBSERVED: curated ticker continuations are in `config.yml` `quality.ticker_key_migrations`; SATS→ECHO is machine-readable, while EQR→VMRK is deliberately withheld pending adjudication (`config.yml:3978-3997@a1a0a05e6adc`). The current-only ledger reader resolves transitively to today's key and exposes no dates (`engine/ledger_identity.py:125-179@a1a0a05e6adc`).
- OBSERVED: `config/delisted_symbols.yml` is a curated acquisition/delisting registry with six symbols (AVB, CTRA, FBRX, LEG, TPH, TWO). Each carries company/exchange/CIK, last session, delisted date, reason, acquirer, consideration, successor field and SEC/exchange receipts; a deliberate no-row note explains why a still-printing liquidation is not declared dead (`config/delisted_symbols.yml:48-230@a1a0a05e6adc`).
- OBSERVED: theme-graph identity breaks are append-only, operator-ratified ticker-reuse splits, with break date, retired node, new epoch, evidence and ratification; ABX and GOLD are the only rows (`config/theme_graph_identity_breaks.yml:1-79@a1a0a05e6adc`).
- OBSERVED: the institutional census source is SEC 13F evidence, not an issuer-lifecycle table; its source contract preserves as-filed filing/submission/cover-page evidence with SEC source clocks and amendment forms (`engine/institutional_census/sec_sources.py:1-46@a1a0a05e6adc`, `engine/institutional_census/sec_sources.py:139-175@a1a0a05e6adc`).
- INFERRED: at a past date, PIT alias identity is reconstructable only from dated alias/history registries; issuer-level identity is not. A delisting event can be found only if manually registered, and ticker reuse only if ratified. A reader must fail closed for uncovered names/dates.
- UNKNOWN: first-date coverage counts versus the original historical universe. The sparse worktree lacks `data/reference/security_master.parquet`, `data/reference/vendor_aliases.parquet`, `data/reference/_receipt.json`, the sidecar manifests and all historical bars; exact row counts, dead-issuer coverage and empirical first dates require those artifacts. Exact command: `python3 - <<'PY'\nimport pandas as pd\nfor p in ['data/reference/security_master.parquet','data/reference/vendor_aliases.parquet']:\n d=pd.read_parquet(p); print(p,len(d),d.columns.tolist(),d.head())\nPY` (not run; artifacts absent). Counts in prose configs are not universe coverage.
- UNKNOWN: general CUSIP/FIGI change events. SOURCE_SHA has no CUSIP or FIGI columns in the registered identity schema; text references only prove that the seam reason about symbols/CUSIP in rename handling (`git grep -ni 'cusip\\|figi' config/dataset_registry.yml config/identity_seams.yml lib/dataos/identity.py scripts/build_security_master.py @a1a0a05e6adc`). A dedicated identifier-change history would require an entitled identifier/corporate-actions source plus event/validity clocks.
- UNKNOWN: historical bankruptcy, spin-off and merger event families. The delisted config records six completed acquisitions with receipts but is not a registry of all mergers, spinoffs or bankruptcies; `git grep` was negative for those historical event tables in the identity spine.

## Q2 EARNINGS / FINANCIAL FACTS

TODO

## Q3 COMPARABLE EVENTS AND EXPECTATIONS

TODO

## Q4 GROUP / PEER MEMBERSHIP

TODO

## Q5 RIGHTS

TODO

## Q6 GAPS + MUST-NOTS

TODO

## EVIDENCE INDEX

TODO
