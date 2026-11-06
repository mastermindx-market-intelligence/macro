# SNI U0 — Company Intelligence reuse map

**Status:** U0 DECISION input (product/integration owner). Read-only. Nothing here is implemented.

**Evidence pins.**
- Terminal: repo `mastermindx-market-intelligence/mastermind-terminal`, `origin/master` @ `fc76cf495781e5f53254aa3c457411de0cb64654`, read via `git show origin/master:<path>` only.
- Macro: `origin/main` @ `e44069e306fd`.
- Line numbers are at those pins.
- During this lane, Terminal `origin/master` advanced one commit to `707648d5`. `git diff --stat fc76cf495 707648d5` over `terminal/components/fin`, `terminal/app/api`, `terminal/lib/{companyIntelligence,eventWorkspace,entitlement,markets}.ts` and `terminal/lib/i18n.tsx` is **empty**, so every citation holds at both SHAs.

**Identity rule.** Every identity value below is a value present in a fixture or master file at the pin, or `UNRESOLVED`. No ID is derived from a ticker, name or CIK.

## 1. Reference issuers: identity as the repos hold it today

Source: macro `data/reference/security_master.parquet` (2,384 rows) and `data/reference/issuer_master.parquet` (1,215 rows) at `e44069e306fd`. **Rechecked at `origin/main` @ `c50af4eb0421` (2026-10-11 ~17:00Z):** the masters grew to 3,103 / 1,931 rows, and every row in the table below is unchanged (00700 and 09988 are still `NO_ISSUER_EVIDENCE`; TCEHY, 80700 and 89988 are still absent). The Data OS owner is `lib/dataos/identity.py`, `scripts/build_security_master.py` and `tests/test_dataos_security_master.py`.

| Listing | `security_id` (as held) | `canonical_issuer_id` | Notes |
|---|---|---|---|
| Tencent `0700.HK` | `SEC:HK-XHKG-00700` | **UNRESOLVED** | Master marks the issuer `NO_ISSUER_EVIDENCE` (issuer NaN). |
| Tencent ADR `TCEHY` | **UNRESOLVED** (absent from security_master) | **UNRESOLVED** | Terminal fixture `markets.test.ts` L327–335 names a "Tencent ADR" NASDAQ row (display only). Macro `data/yahoo/TCEHY.parquet` exists (price only). |
| Tencent RMB counter `80700` | **UNRESOLVED** (absent) | **UNRESOLVED** | Never pooled with `0700.HK` (masterplan §5.2). |
| Alibaba `9988.HK` | `SEC:HK-XHKG-09988` | **UNRESOLVED** | `NO_ISSUER_EVIDENCE`. |
| Alibaba ADS `BABA` | `SEC:US-XNYS-BABA` | `ISS:US-XNYS-BABA` (RESOLVED; CIK `0001577552` in master) | Resolution covers the US listing only. |
| Alibaba RMB counter `89988` | **UNRESOLVED** (absent) | **UNRESOLVED** | Never pooled. |
| BABA ↔ 9988.HK link | — | **UNRESOLVED** | No cross-listing record in either master. |
| `ISS:US-XNYS-TME` | — | — | **Tencent Music, NOT Tencent.** Never link it to `0700.HK`. |

**ADR context owner.** Macro `engine/hk_adr_bridge.py` (display-only "HK ADR Overnight Bridge"; test `tests/test_hk_adr_bridge.py`):
- L75: `9988.HK ↔ BABA "direct"`.
- L85: `0700.HK ↔ KWEB "proxy"`. **KWEB is a basket proxy, never a Tencent ADS quote.**
- The L83 comment ("TCEHY … not in yahoo store") is stale: `data/yahoo/TCEHY.parquet` exists at the pin. That is a follow-on for the bridge owner, not SNI.

## 2. Terminal components (reuse as-is; P0 adds no fork)

| Component | Path | Props (exact) | What it renders for 0700.HK / 9988.HK today |
|---|---|---|---|
| `CompanyIntelligencePage` | `terminal/components/fin/CompanyIntelligencePage.tsx` (914 lines) | `CompanyIntelligencePageProps { sym: string; name?: string \| null; onOpenTx: (target: string \| TranscriptOpenTarget) => void; onEvidenceOpenChange?: (open: boolean) => void }` (L46) | The symbol passes `SAFE_SYMBOL` (`companyIntelligence.ts` L191). On load (L216/L222) it calls `getCurrentEventWorkspace` + `getCompanyIntelligence`. If v2 is ok it **early-returns `CompanyIntelligenceV2Current`** (L309–319). If v1 fails it shows the EmptyState "Company intelligence unavailable / 公司情报暂不可用". **Fixture mode:** the route reads `public/data/company_intelligence/<SYM>.json`, and no such directory is tracked at the pin (`git ls-tree -r` of `terminal/public/data` has no `company_intelligence` entry). The route therefore returns 404 `not_found` for HK (and for every symbol unless a test writes the file), and the EmptyState renders. **Production R2 coverage: UNVERIFIED** (gap G-U1). |
| `CompanyIntelligenceV2Current` | `terminal/components/fin/CompanyIntelligenceV2Current.tsx` (943 lines) | `{ ticker: string; name?: string \| null; result: Extract<EventWorkspaceResult,{ok:true}>; v1: CompanyIntelligenceContext \| null; onOpenTx; onEvidenceOpenChange? }` (L39) | Not reached for HK: there is no HK event_workspace fixture. It has its **own** lens tablist (L685) and brief lens (L715), and does **not** compose the theme/institutional cards. |
| Brief / Results / Call / Sources layouts | `terminal/components/fin/CompanyIntelligence{Brief,Results,Call,Sources}Layout.tsx` | `CompanyIntelligenceBriefItem` (Brief L5), layout props per file | Event-bound; nothing for HK without an event. |
| `EvidenceRail` | `terminal/components/fin/EvidenceRail.tsx` | `EvidenceRailProps { event: CompanyIntelligenceEvent; evidence: CompanyEvidenceSelection \| null; open; overlay; onClose; onOpenTranscript; periodCode? }` (L26). `CompanyEvidenceSelection { id; kind: "summary"\|"highlight"\|"quote"\|"metric"; label; text; derived_comparison?; source: CompanyIntelligenceSource \| null; v2?: EventWorkspaceEvidenceView }` (L15) | **Requires a `CompanyIntelligenceEvent`.** SNI twin evidence that is not earnings-event evidence cannot open in it unchanged (gap G-U4). |
| `CompanySourceManifest` | `terminal/components/fin/CompanySourceManifest.tsx` | `{ event, onOpenTranscript, compact = false, v2Sources }` (L64) | Event-bound. |
| `TranscriptSearchWorkspace` | `terminal/components/fin/TranscriptSearchWorkspace.tsx` | `TranscriptSearchWorkspaceProps` (L30) | Transcript corpus; HK coverage not checked. |
| `CompanyThemeContextCard` | `terminal/components/fin/CompanyThemeContextCard.tsx` | `{ ticker; selectedEventId; companyIntelligenceGenerationId; latestEventId; selectedEventLabel; onUseLatest? }` (L14) | **Sibling idiom for SNI** (own reader + own route + card mounted in the v1 Brief lens at page L750). Gated on a verified CI generation, so it does not render for HK. **#796 touches it, so it must not be edited.** |
| `CompanyInstitutionalContextCard` | `terminal/components/fin/CompanyInstitutionalContextCard.tsx` | same shape (L15) | Same idiom, mounted at page L763. Not rendered for HK (CI-gated). |
| CI v2 design contract | `terminal/docs/COMPANY_INTELLIGENCE_V2_DELTA_SPEC.md` (§0 acceptance gates, §3 receipt grammar, §3.5 absence card, §3.6 stance line, §5 lens delta) + `terminal/docs/refs/company_intelligence_v2/0{1..7}-*.{html,zh.html}` (populated / partial / stale / corrected / blocked / empty / provider-down, EN+ZH) | — | **Reused as the SNI band's state grammar.** The seven reference states map onto SNI typed states (§4 of the journey draft). SNI adds `identity-unresolved` and `rights-blocked` wording, not a new visual language. |
| Market/name lookup | `terminal/lib/markets.ts` | `marketOf(sym, meta)`, `displayName(...)` | Fixture `terminal/lib/__tests__/fixtures/manifestMarkets.json`: `"0700.HK": {mkt:"HKEX", name:"Tencent", zh:"腾讯控股"}`, `"9988.HK": {mkt:"HKEX", name:"Alibaba", zh:"阿里巴巴-W"}`. `markets.test.ts` L23 asserts `marketOf("0700.HK",{mkt:"HKEX"}) === "hk"`. |
| HK statements | `terminal/lib/finStatementMath.ts` (`CUMULATIVE_YTD_MARKETS`, `filesCumulativeQuarters`, `incomeView`, `statementMarket`…), `terminal/components/fin/EarningsPage` | — | `hkCumulativeReporting.test.ts` L66–126 renders Tencent `0700.HK` as-filed cumulative-YTD statements (`TENCENT_AS_FILED`). `finStatementMath.test.ts` L186–401 holds more HK cases. **This is the one HK issuer surface with fixture-proven data.** |
| Responsive e2e | `terminal/e2e/responsive.spec.ts` | — | L1309 exercises `9988.HK`. Viewports 1440×900 / 820×1180 / 390×844 (`npm run test:e2e:responsive`). |

## 3. Terminal readers and routes

| Reader / route | Path | Response type (exact) | Auth | HK behaviour today |
|---|---|---|---|---|
| CI reader | `terminal/lib/companyIntelligence.ts` (1029 lines) | `CompanyIntelligenceResult = {ok:true; state:"ready"\|"partial"\|"stale"\|"not_covered"; context: CompanyIntelligenceContext} \| {ok:false; state:"error"; error:{code:"invalid_symbol"\|"not_found"\|"upstream_unavailable"\|"invalid_payload"; message; retryable}}` (L162). The context (L89) carries `schema "company_intelligence_context.v1"`, `authority "context_only"`, `is_context_only: true`, `generation_id`, `company{ticker, display_name\|null, exchange:null}`, `status`, `latest_event`, `history[]`, `topics`, `source_completeness`, `warnings[]`, `missing_sources[]`, `transport_lineage{earnings_manifest, tx_index, builder:"company_intelligence.v1"}`. R2 path `company_intelligence/generations/<gen>/companies/<T>.json`; 4 MiB cap (L221). | — | `exchange` is hard-typed `null`, so the reader carries **no listing identity**. |
| CI route | `terminal/app/api/company-intelligence/[symbol]/route.ts` (73 lines) | the above; 400/404/502/503 | **None**; rate-limited 120 | Fixture mode (`COMPANY_INTELLIGENCE_FIXTURE==="1"`) reads `public/data/company_intelligence/<SYM>.json`. No HK file, so 404. |
| Event workspace reader | `terminal/lib/eventWorkspace.ts` (1824 lines) | `EventWorkspaceResult` (L329): `{ok:true; state:"ready"\|"partial"\|"stale"; available:true; event_id; workspace: EventWorkspace; authority; is_context_only:true; display_only:true; receipt} \| {ok:false; …error}`. The workspace `issuer{company_id, display_name, listings[{ticker, mic, security_id\|null, share_class, trading_currency, is_primary, valid_from, valid_to}]}`, `prophet_flags{may_rank, may_size, may_gate, prophet_authority:false}`, manifest `previous_generation_id` / `previous_manifest_sha256` | — | The only workspace fixture is `terminal/lib/__tests__/fixtures/aapl-event-workspace.json` (L763 `company_id "cik:0000320193"`, L769 `security_id "xnas:AAPL"`). **The listing model is multi-listing-capable but HK-untested.** |
| Event workspace route | `terminal/app/api/event-workspace/[symbol]/route.ts` (44 lines) | above | **None** | No HK fixture. |
| Theme exposure | `terminal/lib/companyThemeExposure.ts` + `terminal/app/api/company-theme-context/[symbol]/route.ts` | `CompanyThemeExposureResult` (L101) | — | CI-gated. **Avoid (#796).** |
| Institutional context | `terminal/lib/companyInstitutionalContext.ts` + its route | `CompanyInstitutionalResult` (L146); `resolve…` L660, `get…` L708 | — | CI-gated; **closest sibling idiom** for an SNI reader (manifest + generation + sha256 regexes, R2 host constant). |
| Source search | `terminal/app/api/company-source-search/[ticker]/route.ts` | — | — | Not checked for HK. |
| Entitlement | `terminal/lib/entitlement.ts` | `hasLiveOptions` L161, `hasIssueDeskOperator` L175, `isPaidTier` L192, `isProTier` L198 | — | The gate SNI's licensed or private evidence must reuse. |

## 4. Terminal tests SNI must keep green and copy idioms from

- **CI:** `terminal/lib/__tests__/companyIntelligence.test.ts` (fixtures NVDA / AAPL / BRK.B only), `companyIntelligenceRoute.test.ts`, `companyIntelligenceCallSites.test.ts`, `companyIntelligenceLabels.test.ts`.
- **Event workspace:** `eventWorkspace.test.ts`, `eventWorkspaceRoute.test.ts`, `eventWorkspaceRetention.test.ts`.
- **Sibling idioms:** `companyThemeExposure.test.ts` (+`Route`), `companyInstitutionalContext.test.ts` (+`Route`), `companySourceManifestRender.test.tsx`, `companySourceSearch*.test.ts`, `mastermindBrainCompanySource.test.ts`.
- **HK and markets:** `hkCumulativeReporting.test.ts`, `finStatementMath.test.ts`, `markets.test.ts`.
- **Responsive:** `terminal/e2e/responsive.spec.ts`.

## 5. Macro owners SNI composes (named, never forked) — masterplan §4 owner table

| Domain | Owner (macro `origin/main`) | Record |
|---|---|---|
| Issuer/security/listing identity | `lib/dataos/identity.py`; `data/reference/{security,issuer}_master.parquet`; `scripts/build_security_master.py` | `research/MASTERMIND_SECURITY_MASTER_SPEC.md` |
| CIK/event attribution | `engine/company_intelligence/identity.py` | — |
| Filings / financial facts | FIF: `contracts/financial_intelligence_packet.schema.json`, `engine/fundamental_forensics/financial_intelligence_packet.py` | `WS:FINANCIAL-INTELLIGENCE-FABRIC` (SEC-scoped; HK filing coverage not established) |
| Earnings / Q&A | `engine/company_intelligence/`, `engine/earnings_release/`, `event_workspace.v1` | `WS:EARNINGS-INTELLIGENCE-OS`, `WS:EARNINGS-EVENT-INTELLIGENCE-COMPILER` |
| Capital state | `engine/capital_structure/` | `WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2` |
| Behavioral identity | `engine/stock_identity/` | `WS:STOCK-IDENTITY` (the BABA pilot carries provisional `epoch_0` and ended 2026-08-13; **not current data**) |
| Options / positioning | `engine/options_*.py` | `WS:ADVANCED-DATA-OPTIONS` (US listings; HK not established) |
| HK / ADR context | `engine/hk_adr_bridge.py`; `data/hk_stocks/*.parquet` | — |
| Private research | `engine/research_vault/` | `WS:RESEARCH-VAULT-AI-FABRIC` |
| Beliefs / grading | `engine/qledger.py` (+ `sni_belief.v1` per `SNI_V0_EXTENSION_DECISION.md`) | `WS:EVAL-OS-MEASUREMENT-LAW` |

## 6. What SNI needs that the existing surfaces lack

| # | Need | Why no existing surface covers it | Owner of the fix |
|---|---|---|---|
| N1 | A listing-identity block (security_id, issuer state, counter, currency, linked listings with relationship type) | The CI context hard-types `exchange: null`; the event_workspace listing model is US-tested only | SNI reader composes it from Data OS; Data OS owns the IDs |
| N2 | A non-earnings "what changed / current state / unusual / next events / what would change the read" header (masterplan §9) | Every CI surface hangs off an earnings `event` | SNI twin band (new, P0) |
| N3 | Typed states `current / stale-last-good / unavailable / partial / rights-blocked / identity-unresolved / not-applicable` | CI has 4 states (`ready/partial/stale/not_covered`) and no `identity-unresolved` or `rights-blocked` | SNI reader |
| N4 | Evidence rail entries that are not earnings events (filings, capital actions, HK disclosures) | `EvidenceRailProps.event: CompanyIntelligenceEvent` is required | Integration writer adds an optional non-event mode, or SNI uses its own drawer that reuses `EvidenceRail` styling (decide in P0 design spec) |
| N5 | Linked-listing comparison with clock and FX labels (9988.HK vs BABA, never pooled; KWEB labelled proxy) | `hk_adr_bridge` is a macro display organ, not a Terminal reader | SNI `comparison_guard` (C2) consuming `hk_adr_bridge` pairs |
| N6 | Belief/forecast projection with "directional summary" labelling | No Terminal surface reads qledger beliefs | SNI reader over the V0 projection (C-series) |
| N7 | HK primary evidence (HKEX disclosures) for the §9 bar | Not found on the Terminal side at the pin | HK collectors' owner (masterplan §4 row "HK sources") |
| N8 | Coverage proof for HK in production R2 | Not checked in this lane | Gap G-U1 |
