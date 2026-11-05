---
key: RF-T01-YAHOO-COMMERCIAL-LICENSE-ATTESTED
question: >
  For Research Factory commission RF-T01-rights-vintage-20261023, must a later
  Mastermind session ask the Chairman again to approve commercial use of the
  incumbent Yahoo/yfinance nine-ETF adjusted-price route?
answer: >
  NO. On 2026-10-23 the Chairman directly affirmed that existing commercial
  licensing is approved for every Yahoo/yfinance use class examined in RF-T01.
  For this fixed incumbent route and approved existing license scope, record
  internal rights disposition CHAIRMAN-APPROVED / LICENSE-ATTESTED. Do not ask
  the Chairman to reapprove, reconfirm, repurchase, or restate the same license.
  This is a Chairman attestation and internal operating decision, not a claim
  that the actual vendor contract or upstream sublicense text was inspected.
  Keep the independent historical adjusted-price vintage/PIT gate unresolved.
rationale: >
  RF-T01's public-only research could not observe a private commercial license;
  that absence is no longer grounds for a repeated Chairman permission request.
  The Chairman's later direct instruction changes the internal decision for
  the stated use classes. It does not alter Yahoo's public terms, create an
  entitlement outside the actual license, or manufacture past observations.
  Source rights, historical vintages, scientific admission and production
  authority are different questions, owned by their incumbent controls.
alternatives:
  - option: Require each new session or worker to ask the Chairman again
    why_not: >
      Contradicts the explicit 2026-10-23 Chairman decision and unnecessarily
      repeats a resolved internal approval question.
  - option: Treat the commercial-license attestation as proof of historical PIT
    why_not: >
      Permission to access and use data does not establish original adjusted
      price versions or next-session availability in 2010-2023.
evidence:
  - "Chairman direct instruction in RF-T01 assigned conversation on 2026-10-23: existing commercial licensing for all examined uses is approved; no session should ask again."
  - "Exact original Research Factory commission carrier: https://mastermindxgroup.slack.com/archives/C0CBC6AEAQZ/p1792820700533209"
  - "Chairman ruling transmitted in that same carrier: https://mastermindxgroup.slack.com/archives/C0CBC6AEAQZ/p1792821761558809"
  - "Existing owner: agentos/workstreams/WS-RESEARCH-FACTORY-CODEGEN.md; source read on macro main at f3f622a42e002f3cb3503f8ac3fe95485e523129"
affects:
  - WS:RESEARCH-FACTORY-CODEGEN
  - research/research_factory_codegen/
  - collectors/yahoo.py
  - data/yahoo/
confidence: high
reversibility: easy
decided_by: Chairman
decided_at: 2026-10-23
superseded_by: DEC:COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023
---

# RF-T01 Yahoo/yfinance commercial-license Chairman ruling

Commercial approval is now governed by [DEC:COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023](DEC-COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023.md). The original vintage findings and carrier history below remain evidence; the standing ruling supersedes this record's narrower approval scope and generic contract-audit caveat.

## Exact scope of the accepted decision

Research Factory RF-T01-rights-vintage-20261023, parent root
01a1333c-a475-7052-95a8-72a88eb8c17b, uses the **existing** collector
chain collectors.yahoo.YahooAdapter -> collectors.base.run_adapter -> lib.store
-> data/yahoo/{ticker}.parquet for XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV,
XLY, observation history 2010-2023. The intended 'close' field is Yahoo
split- and dividend-adjusted Adj Close on the total-return basis.
'close_price' is not the same price basis and cannot silently substitute.

Chairman confirmation covers these six RF-T01 use classes within the scope
of the *existing* commercial licensing:

1. Automated/programmatic retrieval.
2. Internal commercial research and analysis.
3. Commercial use.
4. Storage, caching and retention.
5. Derived signals, backtest results and model artifacts.
6. Redistribution and display.

**Internal rights question: resolved by explicit Chairman attestation.**
Subsequent sessions must consume this decision, not request another Chairman
approval for the same license, and not block a continuation solely because
the earlier public-documents-only report could not view the private contract.
Where an independent contract-scope audit is genuinely required by an
existing owner, pursue that evidence with the incumbent license custodian;
do not re-ask the Chairman to grant an approval already given. Do not
invent or reproduce unavailable contract clauses, account IDs, license
dates, provider sublicenses or legal opinions. A concrete vendor denial,
license expiration, changed use, or documented contradiction is a new
fact for the owning rights process, not an instruction to repeat the old
Chairman signoff.

This decision does not grant rights to unrelated symbols, publishers,
providers, endpoints, contracts or novel external products.

## Historical adjusted-price vintage remains a distinct gate

**Historical PIT status: NOT QUALIFIED.** The incumbent mutable
latest-snapshot parquet cache is overwritten/rebased, original immutable
receipts do not exist, and current checked_at/built_at/mtime cannot prove
what Yahoo Adj Close was visible at 09:00 America/New_York on the next
session for each 2010-2023 decision date. Prospective versions cannot
prove earlier vintages. Yahoo/yfinance public API documentation inspected
by RF-T01 did not establish an as-of/revision-history selector able to
recover every original adjusted-price prefix. Later corporate-action
adjustment and repairs can alter old observations.

Do not equate a successfully licensed series, backfilled observation date,
or currently split/dividend-adjusted value with contemporaneous decision
availability. Do not admit T01 historical PIT, causal or live signal
authority without independent vintage/time proof. Do not substitute
close_price for Adj Close, switch providers, retrieve price/return/label
data, run collectors, spend trials or holdouts, or touch the original
rf-fixed-smoke-runsc-01a1333c-v4/controller62193 unresolved effect under
this record.

## Subsequent session instructions

- Read this DEC and the latest canonical Research Factory owner/effect state.
- Treat the commercial licensing **approval request** as closed; no
  duplicate Chairman permission request for this fixed existing route.
- Retain source-methodology research separately from the private-license
  attestation. The public-only negative rights assessment remains an
  accurate statement about what public documents alone establish, not a
  finding that Mastermind lacks its confirmed commercial license.
- Keep the next technical T01 dependency narrowly on verifiable historical
  adjusted-price vintage/availability evidence inside the incumbent
  Yahoo/yfinance route; report a genuine absence as such rather than
  manufacturing immutable observations.
- Preserve the original parent/root, source writer, trial/holdout accounting,
  review/CI/release controls and all existing no-retry/EFFECT_UNKNOWN holds.

This Agent OS DEC is an organizational decision/evidence record, not a new
runtime gate, legal contract registry, source-data license, worker job,
publication approval or production implementation.
