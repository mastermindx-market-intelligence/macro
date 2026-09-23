STATUS: COMPLETE

# Prophet US Source Rights Register (2026-09-23)

## STATUS + SCOPE

- Operation: `prophet-us-fable-meta-ceo-20260923-001`. Lane: `pu_w2_rights_register`. Ruling: R6-D03-01 §4.
- Family list: Massive `massive_stock_day`; first-party curated baskets/theme graph; FRED/ALFRED; Census M3; SEC EDGAR; Nasdaq earnings calendar; Yahoo/yfinance expectations; Basket/SPY closes; EquityDesk / Finnhub / earnings-call scores; Finviz / THS; S&P Kensho / Theia; consensus estimates; transcripts `rp_public_primary_v1`; and press / narrative / search / Google Trends.
- **RECORDED** — “an in-repo record states it: quote path:line”. **DETERMINED-FROM-PUBLISHED-TERMS** — “you fetched the source's own published terms page with `curl -sL <url>` at a stated UTC time and quote ≤ 25 words of it with the URL; if the fetch fails or the text does not answer that specific dimension, the answer is UNKNOWN”. **UNKNOWN** is the third and only remaining kind.
- Determinations below are recorded for the Fable Meta-CEO seat's ratification; nothing here is a grant.

## Massive `massive_stock_day`

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:8-11`: “Mastermind holds full licensing and distribution rights”; effective 2026-08-09. Posture: **user-facing for this feed**. |
| Processing | **RECORDED** — `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:21-24`: covered scope includes trades, quotes, “aggregates and bars”; `:31-35`: “Non-display use” and “Derived Materials”. Posture: **user-facing**. |
| Storage | **RECORDED** — `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:44-46`: “Retention — archival copies”; `:21-22`: covered scope includes “historical archives”. Posture: **user-facing**. |
| Model use | **RECORDED** — `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:37-39`: “AI/ML — training, tuning, embeddings, inference”; feed scope remains controlling. Posture: **user-facing**. |
| User redistribution | **RECORDED** — `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:28-30`: “External redistribution — raw and derived”; feed-specific written designation remains controlling. Posture: **user-facing, feed-conditional**. |

## First-party curated baskets/theme graph

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `config/theme_sources.yml:22-27`: source route is “our own curation”; review outcome says “house-owned content; no external rights”. Posture: **user-facing**. |
| Processing | **RECORDED** — `config/theme_sources.yml:22-27`: house-owned curated membership content. Posture: **user-facing**. |
| Storage | **RECORDED** — `config/theme_sources.yml:25-27`: house-owned content is stored under the curated source route. Posture: **user-facing**. |
| Model use | **RECORDED** — `config/theme_sources.yml:23-26`: `rights_class: direct_display_ok`, review outcome “house-owned content; no external rights”. Posture: **user-facing**. |
| User redistribution | **RECORDED** — `config/theme_sources.yml:23-26`: `rights_class: direct_display_ok`, review outcome “house-owned content; no external rights”. Posture: **user-facing**. |

## FRED/ALFRED

General terms fetched at `https://fred.stlouisfed.org/legal/` on 2026-09-23T19:32:46Z. The page says “View, download, and print FRED content” for listed uses, but also prohibits using API content for AI, and separately prohibits third-party proprietary redistribution without permission.

Each configured series page was fetched with `curl -sL` between 2026-09-23T19:50:39Z and 2026-09-23T19:51:15Z. Every page's machine-readable excerpt identified one of these two license tags: `public domain: citation requested` or `copyrighted: citation required`.

| Series | Fetched URL (all at the stated UTC time) | Published tag excerpt |
|---|---|---|
| PAYEMS | `https://fred.stlouisfed.org/series/PAYEMS` — 19:50:40Z | “public domain: citation requested” |
| INDPRO | `https://fred.stlouisfed.org/series/INDPRO` — 19:50:40Z | “public domain: citation requested” |
| M2SL | `https://fred.stlouisfed.org/series/M2SL` — 19:50:41Z | “public domain: citation requested” |
| WEI | `https://fred.stlouisfed.org/series/WEI` — 19:50:41Z | “public domain: citation requested” |
| GDPNOW | `https://fred.stlouisfed.org/series/GDPNOW` — 19:50:42Z | “copyrighted: citation required” |
| RECPROUSM156N | `https://fred.stlouisfed.org/series/RECPROUSM156N` — 19:50:43Z | “public domain: citation requested” |
| THREEFYTP10 | `https://fred.stlouisfed.org/series/THREEFYTP10` — 19:50:43Z | “public domain: citation requested” |
| SAHMREALTIME | `https://fred.stlouisfed.org/series/SAHMREALTIME` — 19:50:44Z | “public domain: citation requested” |
| STICKCPIM157SFRBATL | `https://fred.stlouisfed.org/series/STICKCPIM157SFRBATL` — 19:50:44Z | “copyrighted: citation required” |
| CORESTICKM157SFRBATL | `https://fred.stlouisfed.org/series/CORESTICKM157SFRBATL` — 19:50:45Z | “copyrighted: citation required” |
| FLEXCPIM157SFRBATL | `https://fred.stlouisfed.org/series/FLEXCPIM157SFRBATL` — 19:50:46Z | “copyrighted: citation required” |
| MEDCPIM158SFRBCLE | `https://fred.stlouisfed.org/series/MEDCPIM158SFRBCLE` — 19:50:47Z | “copyrighted: citation required” |
| STLFSI4 | `https://fred.stlouisfed.org/series/STLFSI4` — 19:50:48Z | “copyrighted: citation required” |
| UMCSENT | `https://fred.stlouisfed.org/series/UMCSENT` — 19:50:48Z | “copyrighted: citation required” |
| MICH | `https://fred.stlouisfed.org/series/MICH` — 19:50:49Z | “copyrighted: citation required” |
| AWHMAN | `https://fred.stlouisfed.org/series/AWHMAN` — 19:50:49Z | “public domain: citation requested” |
| ICSA | `https://fred.stlouisfed.org/series/ICSA` — 19:50:50Z | “public domain: citation requested” |
| IC4WSA | `https://fred.stlouisfed.org/series/IC4WSA` — 19:50:51Z | “public domain: citation requested” |
| CCSA | `https://fred.stlouisfed.org/series/CCSA` — 19:50:52Z | “public domain: citation requested” |
| PERMIT | `https://fred.stlouisfed.org/series/PERMIT` — 19:50:52Z | “public domain: citation requested” |
| NEWORDER | `https://fred.stlouisfed.org/series/NEWORDER` — 19:50:53Z | “public domain: citation requested” |
| W875RX1 | `https://fred.stlouisfed.org/series/W875RX1` — 19:50:53Z | “public domain: citation requested” |
| CMRMTSPL | `https://fred.stlouisfed.org/series/CMRMTSPL` — 19:50:54Z | “copyrighted: citation required” |
| UEMPMEAN | `https://fred.stlouisfed.org/series/UEMPMEAN` — 19:50:54Z | “public domain: citation requested” |
| ISRATIO | `https://fred.stlouisfed.org/series/ISRATIO` — 19:50:55Z | “public domain: citation requested” |
| BUSLOANS | `https://fred.stlouisfed.org/series/BUSLOANS` — 19:50:56Z | “public domain: citation requested” |
| CUSR0000SAS | `https://fred.stlouisfed.org/series/CUSR0000SAS` — 19:50:57Z | “public domain: citation requested” |
| CPIAUCSL | `https://fred.stlouisfed.org/series/CPIAUCSL` — 19:50:57Z | “public domain: citation requested” |
| CPILFESL | `https://fred.stlouisfed.org/series/CPILFESL` — 19:50:58Z | “public domain: citation requested” |
| PCEPILFE | `https://fred.stlouisfed.org/series/PCEPILFE` — 19:50:58Z | “public domain: citation requested” |
| PCEPI | `https://fred.stlouisfed.org/series/PCEPI` — 19:50:59Z | “public domain: citation requested” |
| PPIFIS | `https://fred.stlouisfed.org/series/PPIFIS` — 19:51:00Z | “public domain: citation requested” |
| PPIFES | `https://fred.stlouisfed.org/series/PPIFES` — 19:51:01Z | “public domain: citation requested” |
| ECIALLCIV | `https://fred.stlouisfed.org/series/ECIALLCIV` — 19:51:02Z | “public domain: citation requested” |
| ECIWAG | `https://fred.stlouisfed.org/series/ECIWAG` — 19:51:03Z | “public domain: citation requested” |
| CAPUTLG3344S | `https://fred.stlouisfed.org/series/CAPUTLG3344S` — 19:51:03Z | “public domain: citation requested” |
| CAPUTLG334S | `https://fred.stlouisfed.org/series/CAPUTLG334S` — 19:51:04Z | “public domain: citation requested” |
| CAPUTLG331S | `https://fred.stlouisfed.org/series/CAPUTLG331S` — 19:51:04Z | “public domain: citation requested” |
| MNFCTRIRSA | `https://fred.stlouisfed.org/series/MNFCTRIRSA` — 19:51:05Z | “public domain: citation requested” |
| AMTMUO | `https://fred.stlouisfed.org/series/AMTMUO` — 19:51:06Z | “public domain: citation requested” |
| AMTMVS | `https://fred.stlouisfed.org/series/AMTMVS` — 19:51:07Z | “public domain: citation requested” |
| PCU334413334413 | `https://fred.stlouisfed.org/series/PCU334413334413` — 19:51:07Z | “public domain: citation requested” |
| PCU331110331110 | `https://fred.stlouisfed.org/series/PCU331110331110` — 19:51:08Z | “public domain: citation requested” |
| IPG2211S | `https://fred.stlouisfed.org/series/IPG2211S` — 19:51:08Z | “public domain: citation requested” |
| CAPUTLG2211S | `https://fred.stlouisfed.org/series/CAPUTLG2211S` — 19:51:09Z | “public domain: citation requested” |
| WPU0543 | `https://fred.stlouisfed.org/series/WPU0543` — 19:51:10Z | “public domain: citation requested” |
| UNRATE | `https://fred.stlouisfed.org/series/UNRATE` — 19:51:10Z | “public domain: citation requested” |
| RSAFS | `https://fred.stlouisfed.org/series/RSAFS` — 19:51:11Z | “public domain: citation requested” |
| JTSJOL | `https://fred.stlouisfed.org/series/JTSJOL` — 19:51:12Z | “public domain: citation requested” |
| ADPMNUSNERSA | `https://fred.stlouisfed.org/series/ADPMNUSNERSA` — 19:51:12Z | “copyrighted: citation required” |
| USPRIV | `https://fred.stlouisfed.org/series/USPRIV` — 19:51:13Z | “public domain: citation requested” |
| USGOVT | `https://fred.stlouisfed.org/series/USGOVT` — 19:51:13Z | “public domain: citation requested” |
| CES0500000003 | `https://fred.stlouisfed.org/series/CES0500000003` — 19:51:14Z | “public domain: citation requested” |
| AWHAETP | `https://fred.stlouisfed.org/series/AWHAETP` — 19:51:15Z | “public domain: citation requested” |

| Dimension | Determination and posture |
|---|---|
| Acquisition | **DETERMINED-FROM-PUBLISHED-TERMS** — `https://fred.stlouisfed.org/legal/`, fetched 2026-09-23T19:32:46Z: “View, download, and print FRED content”. Posture: **internal-only**. |
| Processing | **UNKNOWN** — the terms page does not specifically authorize commercial transformation; the per-series tags above do not answer processing. Posture: **internal-only**. |
| Storage | **UNKNOWN** — `https://fred.stlouisfed.org/legal/`, fetched 2026-09-23T19:32:46Z, prohibits API content used “in connection with storing, caching, or archiving”; no repository exception is recorded. Posture: **internal-only**. |
| Model use | **UNKNOWN** — `https://fred.stlouisfed.org/legal/`, fetched 2026-09-23T19:32:46Z: “development or training of any software program”; the same sentence includes “machine learning”. Posture: **not a source**. |
| User redistribution | **UNKNOWN** — the per-series tags record source copyright status and citation posture, not permission for Macro user redistribution. Posture: **internal-only**. |

## Census M3

| Dimension | Determination and posture |
|---|---|
| Acquisition | **DETERMINED-FROM-PUBLISHED-TERMS** — `https://www.census.gov/data/developers/about/terms-of-service.html`, fetched 2026-09-23T19:32:46Z: “You may use the Census Bureau API to develop a service”. Posture: **internal-only**. |
| Processing | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “to search, display, analyze, retrieve, view”. Posture: **internal-only**. |
| Storage | **UNKNOWN** — the terms page does not state archival storage permission for this product. Posture: **internal-only**. |
| Model use | **UNKNOWN** — the terms page does not state model-training or inference permission. Posture: **internal-only**. |
| User redistribution | **UNKNOWN** — the page's attribution text does not resolve scope for user redistribution. Posture: **internal-only**. |

## SEC EDGAR

| Dimension | Determination and posture |
|---|---|
| Acquisition | **DETERMINED-FROM-PUBLISHED-TERMS** — `https://www.sec.gov/privacy.htm#dissemination`, fetched 2026-09-23T19:37:19Z: “considered public information”. Posture: **user-facing**. |
| Processing | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “may be copied or further distributed”. Posture: **user-facing**. |
| Storage | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “may be copied or further distributed”. Posture: **user-facing**. |
| Model use | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “may be copied or further distributed”; this policy page answers reuse without prohibiting model use. Posture: **user-facing**. |
| User redistribution | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “copied or further distributed… without the SEC’s permission”. Posture: **user-facing, citation-and-trademark-limited**. |

## Nasdaq earnings calendar

| Dimension | Determination and posture |
|---|---|
| Acquisition | **UNKNOWN** — guest accessibility is public accessibility, not a rights answer, and the page supplies no quoted acquisition grant. Posture: **internal-only**. |
| Processing | **UNKNOWN** — the terms page grants personal non-commercial use but does not answer this commercial processing dimension. Posture: **internal-only**. |
| Storage | **DETERMINED-FROM-PUBLISHED-TERMS** — `https://www.nasdaq.com/legal`, fetched 2026-09-23T19:35:15Z: “alter, store for subsequent use” is prohibited without prior written consent. Posture: **not a source**. |
| Model use | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “text, images, data, code, databases” may not be used for “artificial intelligence systems”. Posture: **not a source**. |
| User redistribution | **DETERMINED-FROM-PUBLISHED-TERMS** — same URL and time: “solely for your personal, non-commercial use”. Posture: **not a source**. |

## Yahoo/yfinance expectations

Yahoo terms were fetched at `https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html` on 2026-09-23T19:32:46Z.

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `collectors/equity_revisions.py:17-21`: estimates “read from the yfinance `earnings_estimate` accessor”; this is an acquisition fact, not a grant beyond it. Posture: **internal-only**. |
| Processing | **UNKNOWN** — Yahoo's terms grant personal software/API use but do not answer commercial expectation processing. Posture: **internal-only**. |
| Storage | **UNKNOWN** — Yahoo terms do not answer archival storage of expectations. Posture: **internal-only**. |
| Model use | **UNKNOWN** — Yahoo terms do not specifically answer model use, and `collectors/equity_revisions.py:358-364` records `rights_class: UNKNOWN`. Posture: **not a source**. |
| User redistribution | **UNKNOWN** — `config/dataset_registry.yml:99-104` records the endpoint and `vendor_terms_personal_use`; that label does not transfer. Posture: **not a source**. |

## Basket / SPY closes

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `config/dataset_registry.yml:84-104`: vendor `yahoo`, endpoint `yfinance`; `licensing: vendor_terms_personal_use` is an adverse label, not a rights grant. Posture: **internal-only**. |
| Processing | **UNKNOWN** — Yahoo's general terms do not specifically answer commercial processing of price bars. Posture: **internal-only**. |
| Storage | **UNKNOWN** — Yahoo's general terms do not answer archival storage of price bars. Posture: **internal-only**. |
| Model use | **UNKNOWN** — no model-use right is recorded for Basket/SPY closes. Posture: **not a source**. |
| User redistribution | **UNKNOWN** — `config/dataset_registry.yml:103-104` records only `vendor_terms_personal_use`; that adverse label does not become a grant. Posture: **not a source**. |

## EquityDesk / Finnhub / earnings-call scores

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `scripts/import_equitydesk_full.py:3-4`: local EquityDesk backfill JSON is read for import; `collectors/finnhub_transcripts.py:3-5`: transcript metadata is pulled; `engine/prophet_stage_inputs.py:21-32`: the governed score comes from EquityDesk native stores. Posture: **internal-only**. |
| Processing | **UNKNOWN** — `scripts/import_equitydesk_full.py:10-18` records import behavior, not a processing rights grant. Posture: **internal-only**. |
| Storage | **UNKNOWN** — `collectors/finnhub_transcripts.py:16-17` records append-only storage behavior, not a storage rights grant. Posture: **internal-only**. |
| Model use | **UNKNOWN** — no EquityDesk, Finnhub, or earnings-call-score model-use grant is recorded. Posture: **not a source**. |
| User redistribution | **UNKNOWN** — no user redistribution grant is recorded for these families. Posture: **not a source**. |

## Finviz / THS

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `config/theme_sources.yml:29-39`: Finviz is `keyless_public`; THS is `receipted_scrape`; both are `unresolved`. Posture: **internal-only**. |
| Processing | **RECORDED** — `config/theme_sources.yml:29-40`: both rows set `rights_class: unresolved`; review outcomes direct internal-only treatment. Posture: **internal-only**. |
| Storage | **RECORDED** — `config/theme_sources.yml:33-34`: derivatives stay in `data/theme_graph/` on the internal plane. Posture: **internal-only**. |
| Model use | **UNKNOWN** — no model-use grant is recorded; `unresolved` is not a grant. Posture: **not a source**. |
| User redistribution | **RECORDED** — `config/theme_sources.yml:4-7`: `unresolved` and `internal_only` “REFUSE public emission”. Posture: **not a source**. |

## S&P Kensho / Theia

| Dimension | Determination and posture |
|---|---|
| Acquisition | **UNKNOWN** — `config/theme_sources.yml:43-52` reserves both families and records no acquisition. Posture: **not a source**. |
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

`git grep -n rp_public_primary_v1 origin/main` found no definition that grants rights. The string is assigned to transcript spans and allow-listed with `public_primary`; it does not define acquisition, processing, storage, model use, or redistribution.

| Dimension | Determination and posture |
|---|---|
| Acquisition | **UNKNOWN** — `engine/company_intelligence/event_workspace.py:255-265` assigns the profile but defines no acquisition grant. Posture: **internal-only**. |
| Processing | **UNKNOWN** — `engine/earnings_transcript_intake.py:516-528` is a closed-context security guard, not a rights grant. Posture: **internal-only**. |
| Storage | **UNKNOWN** — profile assignment at `engine/company_intelligence/event_workspace.py:255-265` states no storage authorization. Posture: **internal-only**. |
| Model use | **UNKNOWN** — `engine/earnings_transcript_intake.py:681-688` is an untrusted-evidence prompt guard, not a model-use rights grant. Posture: **internal-only/context-only**. |
| User redistribution | **UNKNOWN** — `app/company_intelligence.py:89-90` only allow-lists the two profile strings for public glance. Posture: **not a source for redistribution**. |

## Press / narrative / search / Google Trends

| Dimension | Determination and posture |
|---|---|
| Acquisition | **RECORDED** — `config/press_sources.yml:14-17`: “ONLY the documented published endpoints”; `config/narrative_sources.yml:1-4`: public-tier sources only. Posture: **internal-only**. |
| Processing | **UNKNOWN** — press and narrative configuration records mechanics and corroboration, not processing rights. Posture: **internal-only**. |
| Storage | **UNKNOWN** — `config/press_sources.yml:5-7` records data paths, but no storage grant. Posture: **internal-only**. |
| Model use | **UNKNOWN** — no model-use grant is recorded. Posture: **not a source**. |
| User redistribution | **UNKNOWN** — `config/narrative_sources.yml:139-144` says Trends is “DISPLAY-ONLY”; the ruling calls this a product guard, not a grant. Posture: **internal-only**. |

## POSTURE SUMMARY

| Family | Posture now | Single missing answer that would change it |
|---|---|---|
| Massive `massive_stock_day` | User-facing, feed-conditional | A feed-specific written vendor designation, if adverse. |
| First-party curated baskets/theme graph | User-facing | An ownership challenge to a curated row. |
| FRED/ALFRED | Internal-only; model use absent | A FRED source-owner permission expressly resolving storage, model use, and commercial redistribution per series. |
| Census M3 | Internal-only | An explicit Census answer for archival storage, model use, and user redistribution. |
| SEC EDGAR | User-facing with citation and trademark limits | A filing-specific third-party restriction. |
| Nasdaq earnings calendar | Not a source for storage/model/redistribution | Written Nasdaq permission for storage and machine analysis. |
| Yahoo expectations; Basket/SPY closes | Internal-only; model use and redistribution absent | A Yahoo source-owner permission expressly resolving processing, storage, model use, and redistribution. |
| EquityDesk / Finnhub / earnings-call scores | Internal-only | An entitlement resolving processing, storage, model use, and redistribution for each subfamily. |
| Finviz / THS | Internal-only | Resolved provider terms or an operator entitlement for model use and public emission. |
| S&P Kensho / Theia | Not a source | A licensed acquisition contract and all five rights answers. |
| Consensus estimates | Permanently absent | A future explicit reversal of R6-C-01 plus a full licensed entitlement. |
| Transcripts `rp_public_primary_v1` | Internal-only, context-only | A contract defining acquisition, persistence, model use, and redistribution for each transcript source. |
| Press / narrative / search / Google Trends | Internal-only | Per-source terms resolving storage, model use, and redistribution. |

## EVIDENCE

- 2026-09-23 (local): `git show pr/7841:research/prophet_v4/r6_program/rulings/R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md` — §4 rows at displayed lines 50–74 require “one row per family above with the five answers.”
- 2026-09-23 (local): `git show pr/7837:research/prophet_v4/r6_program/wave2/D03_ISSUER_EVENT_SOURCE_READINESS_CENSUS_2026-09-23.md` — Q5 classifies source readiness; Q6 gaps state Census/public accessibility and provider entitlement limits.
- 2026-09-23 (local): `git show pr/7836:research/prophet_v4/r6_program/wave2/D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md` — Q4 lines 110–123 classify FRED, Census, identity/theme, and Massive.
- 2026-09-23 (local): `git show origin/main:research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`, `THETADATA_ENTITLEMENT_RECORD.md`, `config/dataset_registry.yml`, `config/theme_sources.yml`, `config/press_sources.yml`, `config/narrative_sources.yml`, and `config.yml`; citations are line-numbered above. `config.yml:124-166` supplied the configured 54-series list.
- 2026-09-23 (local): `git grep -n rp_public_primary_v1 origin/main` — hits in `app/company_intelligence.py`, `engine/company_intelligence/event_workspace.py`, intake/builders/QA, tests, receipts, and handoffs; no grant definition was found.
- 2026-09-23T19:32:46Z: `curl -sL https://fred.stlouisfed.org/legal/` — “View, download, and print FRED content”; “storing, caching, or archiving”; “development or training”; “Redistribute any third party’s proprietary content”.
- 2026-09-23T19:32:46Z: `curl -sL https://www.census.gov/data/developers/about/terms-of-service.html` — “You may use the Census Bureau API to develop a service”; “search, display, analyze, retrieve, view”; attribution notice.
- 2026-09-23T19:37:19Z: `curl -sL https://www.sec.gov/privacy.htm#dissemination` — “may be copied or further distributed by users… without the SEC’s permission.”
- 2026-09-23T19:35:15Z: `curl -sL https://www.nasdaq.com/legal` — “solely for your personal, non-commercial use”; “alter, store for subsequent use”; AI/data extraction restrictions.
- 2026-09-23T19:32:46Z: `curl -sL https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html` — personal, non-transferable software/API license; commercial/high-volume restrictions.
- 2026-09-23T19:50:39–19:51:15Z: `curl -sL https://fred.stlouisfed.org/series/<SERIES_ID>` for each configured series — the 54 per-series URL/time/tag receipts are listed in the FRED/ALFRED section.

## GAPS + MUST-NOTS REFUSED

- No Massive commercial contract term or ThetaData commercial term is quoted. ThetaData is house-format context only and is not a ruling §4 family.
- Public accessibility, price, account labels, rights-profile strings, and plausible public-domain status were not treated as rights answers.
- Per-series FRED processing/storage/model-use and commercial-redistribution answers remain UNKNOWN. Census storage, model use, and user redistribution remain UNKNOWN.
- EquityDesk, Finnhub, and earnings-call-score entitlements are absent; only acquisition mechanics are recorded. Transcript profile semantics remain undefined; it is not a grant.
- No config, code, API, login, credential, production DDL, or additional file was changed. No source was acquired during this records-only pass.
