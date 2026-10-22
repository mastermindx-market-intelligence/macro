---
workstream: WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
session: sol/web-terminal-cn-hk-news-20261021
model: sol
ended_because: ci_handoff
mission: Integrate original Chinese mainland and Hong Kong news into Terminal single-ticker views using the incumbent news and identity owners.
state_before: Production ticker-news selection covered 503 US securities and had no CN/HK news selections or qualified Chinese feed.
changed:
  - path: engine/finlight_news.py
    what: Bounded original-Chinese provider transport integrated into the existing ticker-news writer.
  - path: engine/qbus_news_cn_hk.py
    what: Current canonical CN/HK news selection and exact MIC-qualified aliases without a new identity owner.
  - path: docs/ops/chinese-ticker-news.md
    what: Primary-source media research, implementation contract and precise activation requirements.
verified:
  - claim: The canonical news regression kernel passes.
    command: Python pytest using the ticker-news-qbus job's 48 suite list in .github/ci/legacy-jobs.yml.
    result: 1171 passed and one existing skip; separate lifecycle and supplemental regression cohort passed 84 tests.
  - claim: Current canonical owner inputs can qualify the expanded news universe without writes.
    command: build_from_files with include_cn_hk=True and write=False using git show HEAD owner parquets.
    result: 1669 securities qualified, including 1166 CN/HK listings.
  - claim: Original Chinese renders in the actual Terminal panel.
    command: TERMINAL_CROPS=1 npm run test:e2e:responsive -- e2e/ticker-news.spec.ts --grep 'Chinese and Hong Kong tickers' --workers=1
    result: Three device projects passed with 24 synthetic captures; 51 contract/panel/editorial tests and TypeScript also passed.
unverified:
  - claim: Licensed original Chinese headlines are flowing in production.
    what_would_verify: Authentic publisher receipts and an entity-capable key, qualified production selection, and real mainland/HK Terminal observations with identity and revocation proof.
unresolved:
  - Finlight is disabled pending credential and authentic publisher-specific permission records.
  - Macro 10023 and Terminal 1113 require ordinary exact-head checks, review and release evidence.
next_actions:
  - Complete exact-head hosted checks and ordinary release for the disabled source capability.
  - Install and qualify genuine source access through the existing owners, then prove actual Chinese Terminal flow.
do_not_redo:
  - Do not create another news store, identity owner, rights registry, lifecycle or quote universe.
  - Preserve News cockpit 9612 and Tiingo 8697/8698 holds and existing Chairman-confirmed Tiingo permissions.
  - Do not retry the terminal pre-effect Fabric census child or equate fixtures with live coverage.
danger_areas:
  - Numeric mainland and HK codes require exchange-qualified association, with no guessed A/H or ADR expansion.
  - A healthy western feed does not prove Chinese coverage, and API access does not grant publisher display rights.
  - Cached display remains subject to current source-specific rights.
---

# Terminal CN/HK original Chinese news — 2026-10-22

## User objective

Research suitable mainland/Hong Kong Chinese media and integrate original Chinese
news into Terminal single-ticker views. English translation is not required.

## Current disposition

IMPLEMENTED / FIXTURE-PROVEN; LIVE CHINESE FEED NOT ACTIVATED.
Ordinary source publication is in progress on owned operations:

- Macro: `terminal-cn-hk-news-20261021`, branch
  `sol/web-terminal-cn-hk-news-20261021`, canonical base
  `0699ecd080ac372c7613dbb88e618183aaefc719`.
- Terminal: `terminal-cn-hk-news-ui-20261021`, branch
  `sol/web-terminal-cn-hk-news-ui-20261021`, base
  `061e7625536d781239cbf687bea64a2e1076202a`.
- Protected source law: `c9cbee5569ba50e30e28715d930809061a169517`.

No real publisher receipt, credential, source activation or live Chinese
coverage is claimed. Review/release status belongs to the actual carrier PRs and
deployed-source evidence, not this pre-publication checkpoint.

## Decisions

See [source selection and activation guide](../../docs/ops/chinese-ticker-news.md).
Finlight provides a documented Chinese transport; publisher grants remain
separate. ETNet is the preferred documented commercial HK raw-feed route, with
no invented API endpoint. Existing Chairman-confirmed Tiingo permissions remain
valid; #8697/#8698 technical holds and ownership are preserved.

Implementation reuses the news writer, SQLite store, receipt owner, current
security master/aliases, API, deployment lifecycle and Terminal rail. It adds
source-local cursors/health, bounded original-Chinese acquisition, direct
ticker+MIC identity, minimal retained association provenance and Chinese-safe
clustering/reference rules. No body/AI summary/translation/English sentiment.

## Verification

- Canonical 48-suite ticker-news kernel: 1,171 passed, one existing skip.
- Follow-up lifecycle/provider/Massive/intake cohort: 84 passed, including literal
  credential-file parsing and duplicate-key refusal. Cohorts overlap; do not sum.
- Terminal contract/panel/editorial cohort: 51 passed.
- Terminal TypeScript: `npx tsc --noEmit` passed.
- Actual Terminal responsive test: three device projects passed, 24 fixture
  captures for mainland/HK × EN/ZH × dark/light specimen × three viewports.
- Canonical owner-parquet read-only universe build: 1,669 qualified, including
  1,166 CN/HK; no owner artifact or production snapshot written.
- Mutable M2 primary owner files failed an existing S&P alias resolution gate;
  canonical Git inputs passed. No source-owner data was repaired.
- Production read-only audit: active western news service, 503 news securities,
  zero CN/HK news selections, no Finlight credential in the writer environment,
  no Finlight source receipts. No provider secret read or emitted.
- Last refreshed upstream changes were disjoint: Macro
  `b8e7bbb70c9965f56e326c2c830014816969986a`; Terminal
  `38723cef63e87e478b1652d42322a69bdec462fd`.

## Unresolved activation dependency

An entity-capable Finlight key plus authentic source-specific headline/link
permissions must be installed through the incumbent credential/rights owner,
with the receipt paths visible to both writer and API reader. Then run the
network-dark check and prove one real mainland and one real HK article through
authenticated Terminal, including raw ticker/MIC-to-security provenance and
rights withdrawal. Original Chinese must remain unchanged.

Do not convert an API key, configured source label or passing fixture into a
claim of live publisher coverage. Keep the feature flag off until qualified.

## Execution continuity

Paid Fabric census child `terminal-cn-hk-news-census-20261021-01` terminated
before execution with rc78, `canonical_source_unreadable` /
`object_root_config_or_promisor`; accepted=false, retry_allowed=false.
No child effects or accepted worker output. Root performed bounded implementation
after the recorded pre-effect execution gap. Native principal reasoning reviews
were advisory only.

Preserve News cockpit #9612's separate holds and all Tiingo/Data OS carrier holds.
No external messages were sent. Continue through actual PR/CI/merge/deployment
evidence where gates allow; a disabled source release does not complete the
user's live-feed objective.
