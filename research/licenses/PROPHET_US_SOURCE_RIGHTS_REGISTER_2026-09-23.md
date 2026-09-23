# Prophet US Source Rights Register (2026-09-23)

STATUS: COMPLETE

## STATUS + SCOPE

- Operation: `prophet-us-fable-meta-ceo-20260923-001`. Lane: `pu_w2_rights_register`. Ruling: R6-D03-01 §4.
- Family list: Massive `massive_stock_day`; first-party curated baskets/theme graph; FRED/ALFRED; Census M3; SEC EDGAR; Nasdaq earnings calendar; Yahoo/yfinance expectations; Basket/SPY closes; EquityDesk / Finnhub / earnings-call scores; Finviz / THS; S&P Kensho / Theia; consensus estimates; transcripts `rp_public_primary_v1`; and press / narrative / search / Google Trends.
- **RECORDED** — “an in-repo record states it: quote path:line”. **DETERMINED-FROM-PUBLISHED-TERMS** — “you fetched the source's own published terms page with `curl -sL <url>` at a stated UTC time and quote ≤ 25 words of it with the URL; if the fetch fails or the text does not answer that specific dimension, the answer is UNKNOWN”. **UNKNOWN** is the third and only remaining kind.
- Determinations below are recorded for the Fable Meta-CEO seat's ratification; nothing here is a grant.

## Massive `massive_stock_day`

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:8-11`: “Mastermind holds full licensing and distribution rights”; effective 2026-08-09. Posture: **user-facing for this feed**. |
| Processing | **RECORDED** — `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:21-24`: “aggregates and bars”; `collectors/massive_stock_day.py:11-15`: “builds and maintains a DERIVED per-ticker store”. Posture: **user-facing**. |
| Storage | **RECORDED** — `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:44-46`: “Retention — archival copies”; `collectors/massive_stock_day.py:17-25`: “R2 IS THE CANONICAL HOME”. Posture: **user-facing**. |
| Model use | **RECORDED** — `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:37-39`: “AI/ML — training… embeddings, and inference”. Posture: **user-facing**. |
| User redistribution | **RECORDED** — `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:28-30`: “External redistribution — raw and derived”; `:50-57` says feed-specific conditions and debrand law remain controlling. Posture: **user-facing, feed-conditional**. |

## First-party curated baskets/theme graph

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `config/theme_sources.yml:22-26`: `auth_class: house`; source is “our own curation”. Posture: **user-facing**. |
| Processing | **RECORDED** — `config/theme_sources.yml:22-27`: first-party US curated baskets and regional families. Posture: **user-facing**. |
| Storage | **RECORDED** — `config/theme_sources.yml:25`: `data/baskets/membership.json` plus regional membership documents. Posture: **user-facing**. |
| Model use | **RECORDED** — `config/theme_sources.yml:26`: “house-owned content; no external rights”. Posture: **user-facing**. |
| User redistribution | **RECORDED** — `config/theme_sources.yml:23-24`: `rights_class: direct_display_ok`, `auth_class: house`. Posture: **user-facing**. |

## FRED/ALFRED

General terms fetched at `https://fred.stlouisfed.org/legal/` on 2026-09-23T19:32:46Z. The page says “View, download, and print FRED content” for listed uses, but also prohibits using API content for AI, and separately prohibits third-party proprietary redistribution without permission.

Configured series tags were fetched from each series page on 2026-09-23T19:38:21–19:38:49Z:

- Public-domain tags: PAYEMS, INDPRO, M2SL, WEI, RECPROUSM156N, THREEFYTP10, SAHMREALTIME, AWHMAN, ICSA, IC4WSA, CCSA, PERMIT, NEWORDER, W875RX1, UEMPMEAN, ISRATIO, BUSLOANS, CUSR0000SAS, CPIAUCSL, CPILFESL, PCEPILFE, PCEPI, PPIFIS, PPIFES, ECIALLCIV, ECIWAG, CAPUTLG3344S, CAPUTLG334S, CAPUTLG331S, MNFCTRIRSA, AMTMUO, AMTMVS, PCU334413334413, PCU331110331110, IPG2211S, CAPUTLG2211S, WPU0543, UNRATE, RSAFS, JTSJOL, USPRIV, USGOVT, CES0500000003, AWHAETP.
- Copyright-required tags: GDPNOW; STICKCPIM157SFRBATL; CORESTICKM157SFRBATL; FLEXCPIM157SFRBATL; MEDCPIM158SFRBCLE; STLFSI4; UMCSENT; MICH; CMRMTSPL; ADPMNUSNERSA.

| Dimension | Determination and posture |
|---|---|
| Acquisition | **DETERMINED-FROM-PUBLISHED-TERMS** — `https://fred.stlouisfed.org/legal/`, fetched 2026-09-23T19:32:46Z: “View, download, and print FRED content”. Posture: **internal-only**. |
| Processing | **UNKNOWN** — the terms page does not specifically authorize commercial transformation; the series tag alone does not answer processing. Posture: **internal-only**. |
| Storage | **UNKNOWN** — `https://fred.stlouisfed.org/legal/`, fetched 2026-09-23T19:32:46Z, prohibits API content used “in connection with storing, caching, or archiving”; no repository exception is recorded. Posture: **internal-only**. |
| Model use | **UNKNOWN** — `https://fred.stlouisfed.org/legal/`, fetched 2026-09-23T19:32:46Z: “development or training of any software program”; the same sentence includes “machine learning”. Posture: **not a source**. |
| User redistribution | **UNKNOWN per series except by tag label** — public-domain and citation-required labels were determined above, but commercial redistribution requires a series-specific answer. Posture: **internal-only**. |

## Census M3

| Dimension | Determination and posture |
|---|---|
| Acquisition | **DETERMINED-FROM-PUBLISHED-TERMS** — `https://www.census.gov/data/developers/about/terms-of-service.html`, fetched 2026-09-23T19:32:46Z: “You may use the Census Bureau API to develop a service”. Posture: **internal-only**. |
| Processing | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “to search, display, analyze, retrieve, view”. Posture: **internal-only**. |
| Storage | **UNKNOWN** — the terms page does not state archival storage permission for this product. Posture: **internal-only**. |
| Model use | **UNKNOWN** — the terms page does not state model-training or inference permission. Posture: **internal-only**. |
| User redistribution | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “is not endorsed or certified by the Census Bureau”; attribution is required, but redistribution scope remains unresolved. Posture: **internal-only**. |

## SEC EDGAR

| Dimension | Determination and posture |
|---|---|
| Acquisition | **DETERMINED-FROM-PUBLISHED-TERMS** — `https://www.sec.gov/privacy.htm#dissemination`, fetched 2026-09-23T19:37:19Z: “considered public information”. Posture: **user-facing**. |
| Processing | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “may be copied or further distributed”. Posture: **user-facing**. |
| Storage | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “may be copied or further distributed”. Posture: **user-facing**. |
| Model use | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “may be copied or further distributed”; no model-specific prohibition appears on the policy page. Posture: **user-facing**. |
| User redistribution | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “copied or further distributed… without the SEC’s permission”; citation is requested and logos/trademarks excluded. Posture: **user-facing, citation-and-trademark-limited**. |

## Nasdaq earnings calendar

| Dimension | Determination and posture |
|---|---|
| Acquisition | **DETERMINED-FROM-PUBLISHED-TERMS** — `https://www.nasdaq.com/legal`, fetched 2026-09-23T19:35:15Z: Services may be accessed as a guest. Posture: **internal-only**. |
| Processing | **UNKNOWN** — the terms page grants personal non-commercial use but does not answer this commercial processing dimension. Posture: **internal-only**. |
| Storage | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “alter, store for subsequent use” is prohibited without prior written consent. Posture: **not a source**. |
| Model use | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “text, images, data, code, databases” may not be used for “artificial intelligence systems”. Posture: **not a source**. |
| User redistribution | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “solely for your personal, non-commercial use”; selling, copying, and distribution are prohibited. Posture: **not a source**. |

## Yahoo/yfinance expectations

Yahoo terms were fetched at `https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html` on 2026-09-23T19:32:46Z.

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `collectors/equity_revisions.py:19-21`: estimates read through the yfinance accessor. Posture: **internal-only**. |
| Processing | **UNKNOWN** — Yahoo's terms grant personal software/API use but do not answer commercial expectation processing. Posture: **internal-only**. |
| Storage | **UNKNOWN** — Yahoo terms do not answer archival storage of expectations. Posture: **internal-only**. |
| Model use | **UNKNOWN** — Yahoo terms do not specifically answer model use, and `collectors/equity_revisions.py:363` records `rights_class: UNKNOWN`. Posture: **not a source**. |
| User redistribution | **UNKNOWN** — `config/dataset_registry.yml:100-104` records the endpoint and `vendor_terms_personal_use`; that label does not transfer. Posture: **not a source**. |

## Basket / SPY closes

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `config/dataset_registry.yml:59-64`: vendor `yahoo`, licensing `vendor_terms_personal_use`. Posture: **internal-only**. |
| Processing | **UNKNOWN** — Yahoo's general terms do not specifically answer commercial processing of price bars. Posture: **internal-only**. |
| Storage | **UNKNOWN** — Yahoo's general terms do not answer archival storage of price bars. Posture: **internal-only**. |
| Model use | **UNKNOWN** — no model-use right is recorded for Basket/SPY closes. Posture: **not a source**. |
| User redistribution | **UNKNOWN** — `config/dataset_registry.yml:63` records only `vendor_terms_personal_use`; the adverse finding does not transfer to a grant. Posture: **not a source**. |

## EquityDesk / Finnhub / earnings-call scores

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `scripts/import_equitydesk_full.py:3-5`: local EquityDesk backfill JSON imports seeds; `collectors/finnhub_transcripts.py:3-5`: Finnhub transcript “metadata only”; `engine/prophet_stage_inputs.py:22-35`: R2 earnings-call score tiers. Posture: **internal-only**. |
| Processing | **RECORDED mechanics only** — `scripts/import_equitydesk_full.py:12-18`: selects columns, writes seeds, and stages history; no rights grant is recorded. Posture: **internal-only**. |
| Storage | **RECORDED mechanics only** — `collectors/finnhub_transcripts.py:16-17`: append-only, key-deduped store; `engine/prophet_stage_inputs.py:28-35`: immutable R2 generation. Posture: **internal-only**. |
| Model use | **UNKNOWN** — no EquityDesk, Finnhub, or earnings-call-score model-use grant is recorded. Posture: **not a source**. |
| User redistribution | **UNKNOWN** — no user redistribution grant is recorded for these families. Posture: **not a source**. |

## Finviz / THS

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `config/theme_sources.yml:29-39`: Finviz is `keyless_public`; THS is `receipted_scrape`; both are `unresolved`. Posture: **internal-only**. |
| Processing | **RECORDED** — `config/theme_sources.yml:33-34`: derivatives stay in `data/theme_graph/`; THS uses the same internal-only outcome at `:40`. Posture: **internal-only**. |
| Storage | **RECORDED** — `config/theme_sources.yml:34`: “GMI derivatives stay in data/theme_graph/ (internal plane)”. Posture: **internal-only**. |
| Model use | **UNKNOWN** — no model-use grant is recorded; `unresolved` is not a grant. Posture: **not a source**. |
| User redistribution | **RECORDED** — `config/theme_sources.yml:4-7`: `unresolved` and `internal_only` “REFUSE public emission”. Posture: **not a source**. |

## S&P Kensho / Theia

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `config/theme_sources.yml:43-52`: both rows remain commented “Reserved families”; Theia says “commercial license required”. Posture: **not a source**. |
| Processing | **UNKNOWN** — no acquisition exists and no processing right is recorded. Posture: **not a source**. |
| Storage | **UNKNOWN** — no storage right is recorded. Posture: **not a source**. |
| Model use | **UNKNOWN** — no model-use right is recorded. Posture: **not a source**. |
| User redistribution | **UNKNOWN** — no redistribution right is recorded. Posture: **not a source**. |

## Consensus estimates

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-C-01_2026-09-23.md:14`: “Consensus unlicensed”. Posture: **not a source**. |
| Processing | **RECORDED** — same source rules consensus absent; no processing right exists. Posture: **not a source**. |
| Storage | **RECORDED** — same source rules consensus absent; no storage right exists. Posture: **not a source**. |
| Model use | **RECORDED** — same source: beat/miss is “permanently ABSENT”. Posture: **not a source**. |
| User redistribution | **RECORDED** — same source: beat/miss is “permanently ABSENT”. Posture: **not a source**. |

## Transcripts `rp_public_primary_v1`

`git grep -n rp_public_primary_v1 origin/main` found no definition that grants rights. It is assigned to transcript spans and allow-listed with `public_primary`; intake enforces `authority=context_only`.

| Dimension | Determination and posture |
|---|---|
| Acquisition | **UNKNOWN** — `engine/company_intelligence/event_workspace.py:264` assigns `rights_profile="rp_public_primary_v1"` but defines no acquisition grant. Posture: **internal-only**. |
| Processing | **RECORDED guard only** — `engine/earnings_transcript_intake.py:516-528`: “arbitrary fields never reach a model”; `authority` must be `context_only`. Posture: **internal-only**. |
| Storage | **UNKNOWN** — profile assignment at `engine/company_intelligence/event_workspace.py:264` states no storage authorization. Posture: **internal-only**. |
| Model use | **RECORDED guard only** — `engine/earnings_transcript_intake.py:681-688`: transcript text is bounded untrusted evidence, not instructions. Posture: **internal-only/context-only**. |
| User redistribution | **UNKNOWN** — `app/company_intelligence.py:89-90` only allow-lists the two profile strings for public glance. Posture: **not a source for redistribution**. |

## Press / narrative / search / Google Trends

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `config/press_sources.yml:14-17`: “ONLY the documented published endpoints”; `config/narrative_sources.yml:1-4`: public-tier sources only. Posture: **internal-only**. |
| Processing | **UNKNOWN** — press and narrative configuration records mechanics and corroboration, not processing rights. Posture: **internal-only**. |
| Storage | **UNKNOWN** — `config/press_sources.yml:5-7` records data paths, but no storage grant. Posture: **internal-only**. |
| Model use | **UNKNOWN** — no model-use grant is recorded. Posture: **not a source**. |
| User redistribution | **UNKNOWN** — `config/narrative_sources.yml:141-144` says Trends is “DISPLAY-ONLY”; the ruling calls this a product guard, not a grant. Posture: **internal-only**. |

## POSTURE SUMMARY

| Family | Posture now | Single missing answer that would change it |
|---|---|---|
| Massive `massive_stock_day` | User-facing, feed-conditional | A feed-specific written vendor designation, if adverse. |
| First-party curated baskets/theme graph | User-facing | An ownership challenge to a curated row. |
| FRED/ALFRED | Internal-only; model use absent | A FRED source-owner permission expressly resolving storage, model use, and commercial redistribution per series. |
| Census M3 | Internal-only | An explicit Census answer for archival storage, model use, and commercial redistribution. |
| SEC EDGAR | User-facing with citation and trademark limits | A filing-specific third-party restriction. |
| Nasdaq earnings calendar | Not a source for storage/model/redistribution | Written Nasdaq permission for storage and machine analysis. |
| Yahoo expectations; Basket/SPY closes | Internal-only; model use and redistribution absent | A Yahoo source-owner permission expressly resolving processing, storage, model use, and redistribution. |
| EquityDesk / Finnhub / earnings-call scores | Internal-only | An entitlement resolving model use and redistribution for each subfamily. |
| Finviz / THS | Internal-only | Resolved provider terms or an operator entitlement for model use and public emission. |
| S&P Kensho / Theia | Not a source | A licensed acquisition contract and all five rights answers. |
| Consensus estimates | Permanently absent | A future explicit reversal of R6-C-01 plus a full licensed entitlement. |
| Transcripts `rp_public_primary_v1` | Internal-only, context-only | A contract defining acquisition, persistence, model use, and redistribution for each transcript source. |
| Press / narrative / search / Google Trends | Internal-only | Per-source terms resolving storage, model use, and redistribution. |

## EVIDENCE

- 2026-09-23 (local): `git show pr/7841:research/prophet_v4/r6_program/rulings/R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md` — §4 rows at displayed lines 50–69; §4 requires “one row per family above with the five answers.”
- 2026-09-23 (local): `git show pr/7837:research/prophet_v4/r6_program/wave2/D03_ISSUER_EVENT_SOURCE_READINESS_CENSUS_2026-09-23.md` — Q5 excerpts show Massive, FRED, Yahoo, theme, consensus, transcript, and press postures.
- 2026-09-23 (local): `git show pr/7836:research/prophet_v4/r6_program/wave2/D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md` — Q4 lines 110–123 classify FRED, Census, identity/theme, and Massive.
- 2026-09-23 (local): `git show origin/main:research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`, `THETADATA_ENTITLEMENT_RECORD.md`, `config/dataset_registry.yml`, `config/theme_sources.yml`, `config/press_sources.yml`, and `config/narrative_sources.yml`; citations are line-numbered above. `config.yml:124-157` supplied the configured FRED series list.
- 2026-09-23 (local): `git grep -n rp_public_primary_v1 origin/main` — hits in `app/company_intelligence.py`, `engine/company_intelligence/event_workspace.py`, intake/builders/QA, tests, receipts, and handoffs; no grant definition was found.
- 2026-09-23T19:32:46Z: `curl -sL https://fred.stlouisfed.org/legal/` — 131,707 bytes; “View, download, and print FRED content”; “storing, caching, or archiving”; “development or training”; “Redistribute any third party’s proprietary content”.
- 2026-09-23T19:32:46Z: `curl -sL https://www.census.gov/data/developers/about/terms-of-service.html` — 295,465 bytes; “You may use the Census Bureau API to develop a service”; “search, display, analyze, retrieve, view”; attribution notice.
- 2026-09-23T19:37:19Z: `curl -sL https://www.sec.gov/privacy.htm#dissemination` — “may be copied or further distributed by users… without the SEC’s permission.”
- 2026-09-23T19:35:15Z: `curl -sL https://www.nasdaq.com/legal` — “solely for your personal, non-commercial use”; “alter, store for subsequent use”; AI/data extraction restrictions.
- 2026-09-23T19:32:46Z: `curl -sL https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html` — 167,945 bytes; personal, non-transferable software/API license; commercial/high-volume restrictions.
- 2026-09-23T19:38:21–19:38:49Z and 19:40:29–19:40:34Z: `curl -sL https://fred.stlouisfed.org/series/<SERIES_ID>` for each configured series — page text reported the copyright/public-domain tags listed above.

## GAPS + MUST-NOTS REFUSED

- No Massive commercial contract term or ThetaData commercial term is quoted. ThetaData is house-format context only and is not a ruling §4 family.
- Public accessibility, price, account labels, rights-profile strings, and plausible public-domain status were not treated as rights answers.
- Per-series FRED processing/storage/model-use and commercial-redistribution answers remain UNKNOWN. Census storage, model use, and exact redistribution scope remain UNKNOWN.
- EquityDesk, Finnhub, and earnings-call score entitlements are absent; only mechanics are recorded. Transcript profile semantics remain undefined; it is not a grant.
- No config, code, API, login, credential, production DDL, or additional file was changed. No source was acquired during this records-only pass.
