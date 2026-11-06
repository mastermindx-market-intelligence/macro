---
key: ITP-R5-NO-DURABLE-APPEND-2026-10-07
question: >
  The R5 prospective-consumer spec
  (research/alpha_intelligence/expectation_market_dynamics/R5_PROSPECTIVE_CONSUMER_SPEC_2026-10-06.md §8 question 1)
  asks the program owner to "name a path that already exists, or rule that no durable append is authorized",
  and says a new path is not an acceptable answer under the program's exclusion of new stores. Which answer does
  the program give?
answer: >
  No durable append is authorized (option 2). Lane R5-BUILD does not open, because spec §5 says it "has no second
  file and must not open" when §8 question 1 names no existing path. The engine shell is not wired to write
  K3E receipt rows anywhere, and writing zero rows stays the only lawful behaviour (spec §3). The K3E expectation
  receipt stays reproducible on demand through scripts/query_k3e_expectation_surface.py, which re-derives it at any
  as-of from existing stores. R5's G-PROD gate (seven consecutive scheduled daily.yml engine successes appending to
  an existing file) is therefore unreachable by construction, and R5 is recorded as CLOSED-NOT-BUILT, not as
  delivered. The ruling is reopened only if (a) an owner names an existing data/ path whose writer and readers
  admit a K3E receipt row without schema or semantic damage, or (b) a later DEC lifts the program's no-new-store
  exclusion.
rationale: >
  On 2026-10-06 the Chairman directed this program's seat to resolve owner and parent blocks itself rather than
  bounce them. DEC:ITP-SEAT-RELEASES-ADMINISTRATIVE-BLOCKS-UNDER-CHAIRMAN-2026-10-06 records that delegation. The
  §8 question is an administrative block. It asks for an owner choice between two answers the spec already
  allows, and needs no new data, money or rights decision. Orchestrator A censused every existing data/ ledger
  that could take a receipt row on 2026-10-07 and found none that admits one without damage (evidence below).
  Under the no-new-store law, a new file is not an answer. Bending an existing ledger would break its producer,
  inflate a multiple-testing family, or plant a directionless claim in a scored ledger. Option 2 is the only
  answer that keeps every existing contract intact. Nothing is lost: the receipt is a pure function of existing
  stores and is reproducible on demand. financial_influence, k3e_admissible and promotion_eligible stay false.
  This decision does not satisfy the spec's own HOLD-FOR-SOL text. It is a workstream-owner act under Chairman
  delegation, recorded as such, never as a Sol ruling.
alternatives:
  - option: Append receipts to data/price_pressure/completion_receipts
    why_not: >
      Its writer has a strict RECEIPT_FIELDS tuple and read_receipts raises on unknown rows, so a K3E row would
      break the existing producer and every reader.
  - option: Append to the qledger (claims, grades, falsifier_evaluations)
    why_not: >
      register() requires a direction, and a K3E receipt carries none. The WS-EVAL-OS DNR also forbids
      retrospective claims. A receipt is not a claim.
  - option: Append to data/trial_ledger.jsonl
    why_not: >
      That is the DSR family/config_hash memory. A receipt row there is a category error that inflates the
      multiple-testing N every promotion is judged against.
  - option: Append to the signal_archive
    why_not: >
      It is a parquet rewrite with keep-first per as-of, so a new label means a new file. That is a new store
      by another name.
  - option: Register as a neuralweb machine_registry cortex_hypothesis
    why_not: >
      The experiments registry reads that kind as a live hypothesis. A receipt would be misread as one.
  - option: Write to the prophet ledger, the revisions parquets, or the unbuilt evidence mesh
    why_not: >
      The prophet ledger and the revisions parquets are excluded by spec §2 and its matrix. The evidence mesh
      does not exist; using it would mean building a new store.
  - option: Create a new receipt file
    why_not: >
      Spec §8 forbids it in so many words, under the program's exclusion of new stores ("a view over existing
      stores is the only lawful shape").
  - option: Leave §8 question 1 open and wait for Sol
    why_not: >
      The Chairman classified owner/parent blocks of this program as the seat's to resolve. Waiting would leave
      R5 neither built nor closed, with no change in the facts.
evidence:
  - "Orchestrator A census of existing data/ ledgers, 2026-10-07T06:12Z (seat scratch orch/A/LEDGER.md, lane A2). All seven candidates above were rejected with the mechanism named. Rank-1 recommendation: option 2."
  - "R5_PROSPECTIVE_CONSUMER_SPEC_2026-10-06.md §3 ('Until §8 question 1 is answered, the shell call is not added. Writing zero rows is the only lawful behavior'), §5 ('If the answer to §8 question 1 never names an existing path, lane R5-BUILD has no second file and must not open'), §8 question 1."
  - "scripts/query_k3e_expectation_surface.py on origin/main re-derives the K3E expectation receipt at an as-of from existing stores, with no durable write."
affects:
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - "research/alpha_intelligence/expectation_market_dynamics/**"
  - "scripts/ci/daily_engine_regime_dashboard.sh"
confidence: high
reversibility: easy
decided_by: "seat: fable program-ceo session 2fc05761 (WS:ALPHA-INTELLIGENCE-INTEGRATION owner), under Chairman directive 2026-10-06; census by orchestrator A"
decided_at: 2026-10-07
review_by: 2027-01-07
---

# R5 §8 question 1: no durable append is authorized

The seat answers the R5 spec's §8 question 1 with option 2. No existing `data/` ledger can take a K3E receipt
row without breaking its producer, inflating a multiple-testing family, or planting a directionless claim in a
scored ledger. A new path is excluded by the program's no-new-store law. R5-BUILD therefore does not open
(spec §5). The receipt stays reproducible on demand via `scripts/query_k3e_expectation_surface.py`.

R5 state: **CLOSED-NOT-BUILT**. G-PROD is unreachable by construction, and it is not reported as passed.
The ruling is reopened by an owner naming an existing admissible path, or by a DEC that lifts the no-new-store
exclusion.
