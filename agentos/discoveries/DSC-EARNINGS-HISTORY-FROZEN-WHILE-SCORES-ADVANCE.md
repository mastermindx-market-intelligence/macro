---
key: EARNINGS-HISTORY-FROZEN-WHILE-SCORES-ADVANCE
claim: >
  The live earnings R2 plane advances transcript score generations through September 2026
  while its canonical history.parquet remains the July 31 EquityDesk import; Company
  Intelligence therefore can be operationally fresh yet still project stale or semantically
  ambiguous quarterly history fields.
falsifier: >
  Read the current earnings_calls/manifest.json from the canonical R2 marker and the
  corresponding immutable history.parquet: this claim is disproved when history.latest_call_date
  advances beyond 2026-07-31 from a lawful live producer and the LMT/RTX/NOC/LHX current-quarter
  rows carry typed financial basis or are replaced by a newer accepted owner contract.
so_what: >
  Defense and other consumers must not treat Company Intelligence revenue_growth,
  eps_growth, or gross_margin as fresh typed financial truth merely because the producer
  run and score generation are current. Do not patch those semantics downstream or make
  the scores worker mutate legacy history. Use sourced SEC/issuer facts as bounded research
  context now, and migrate to the existing Earnings/FIF owners when they provide lawful
  production issuer coverage.
kind: landmine
verified_at: 2026-09-19
verified_by: >
  Live R2 reads on 2026-09-19: earnings_calls manifest generation
  86414b914e8ab5a0fec9dba7 reports scores.latest_scored_at
  2026-09-19T06:52:00.217724+00:00 but history.latest_call_date 2026-07-31,
  reconciliation source equitydesk_backfill/delta_2026-07-31/earnings_call_data.json,
  source_updated_at_max 2026-08-01 08:08:38.565289+00:00; immutable history MD5
  440447335f37a51419937dba493b3168 was downloaded and read back for LMT/RTX/NOC/LHX.
scope:
  - macro
  - earnings-intelligence
  - engine/company_intelligence/
  - tools/earnings_worker/
  - WS:DEFENSE-PROCUREMENT-V3
  - WS:EARNINGS-INTELLIGENCE-OS
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
confidence: verified
---

# Evidence boundary

The Windows/Terminal earnings worker is explicitly a **score** writer. Its module contract and
implementation hydrate the current R2 generation, call `score_text`, upsert
`scores.parquet`, and publish the hydrated generation. It does not append quantitative
financial rows to `history.parquet`.

The current R2 manifest proves the two planes have diverged in freshness:

- scores: 7,097 rows / 4,385 tickers, latest call date 2026-09-11, latest scored at
  2026-09-19T06:52:00.217724+00:00;
- history: 50,982 rows / 3,529 tickers, latest call date 2026-07-31;
- reconciliation input: 51,156 rows from the frozen July-31 EquityDesk delta, 50,982 output,
  174 rejected.

The immutable history file itself reproduces the Defense defects rather than the Company
Intelligence projector inventing them:

- LMT FY2026 Q2 carries `revenue_growth=11` and `gross_margin=10.8`; the issuer's Q2
  release identifies 10.8% as total business segment operating margin, not gross margin.
- RTX FY2026 Q2 carries generic `revenue_growth=16` and `eps_growth=21`; the issuer
  describes the analogous figures as organic sales growth and adjusted EPS growth.
- NOC FY2026 Q2 carries generic `eps_growth=8`, whose reported-GAAP comparison basis is
  not represented in the legacy row.
- LHX has no FY2026 Q2 history row at all; its last row is FY2026 Q1.

Company Intelligence's deterministic view simply maps these generic history fields into its
public metrics. Its scheduled producer is healthy and has recently promoted immutable
generations, so a fresh producer timestamp would not repair this source-content problem.

# Owner boundary

Do not repair this by:
- hard-coding corrected values inside Government Revenue or Defense;
- widening the IRDM-only Defense financial bridge around these generic fields;
- teaching the scoring worker to invent numeric financial facts from transcript prose; or
- treating FIF's fixture/golden-AAPL service as production issuer coverage.

The existing Earnings owner remains the event/fact authority and FIF remains the governed filing
semantic owner. Defense may carry a source-backed research bridge using official SEC/issuer facts
while those production owners are incomplete, but that bridge must expose source/basis/period and
must not become another financial truth store.
