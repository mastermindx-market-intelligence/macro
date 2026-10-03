# Intraday Dislocation Catalyst Source Census - 2026-10-02

**Program:** Live Entry Radar / Terminal Tactical Intelligence  
**Scope:** source-owner readiness for the R0 catalyst context attachment  
**Authority:** research only; no entry, ranking, gating, sizing, execution, or production activation

## Executive finding

Mastermind already has several high-quality issuer-event truth planes, but it does **not** yet have one universe-wide, low-latency, point-in-time catalyst plane that can honestly answer "no blocking event observed" for every intraday dislocation.

Therefore the R0 contract is useful now as a fail-closed attachment, but a production consumer must default to `coverage_unknown` unless the exact required source set for that episode has healthy, decision-time reads.

This census does not commission a new event store. It maps existing owners and identifies the smallest lawful adapter seams.

## 1. Source readiness matrix

| Source owner / artifact | Identity | Decision-time clock | Coverage / correction truth | R0 use now | Readiness |
|---|---|---|---|---|---|
| EDGAR earnings Item 2.02, `data/edgar/earnings_8k_dates.parquet` | Collector contract supports CIK + accession; committed historical artifact is stale relative to the newer schema | `acceptance_datetime` is exact SEC availability | Historical rows exist, but the committed schema lacks accession/form/report_date now expected by the collector | Strong earnings-event clock after regeneration/join to canonical filing identity | **PARTIAL - ADAPTER BLOCKED ON CANONICAL ID** |
| Company Intelligence `event_workspace.v1` | Existing owner event id + immutable generation lineage | `lifecycle.source_available_at`, `lifecycle.observed_at`, `generated_at` are distinct | Current-generation/observed-as-run truth; not a universe-complete historical event archive | Forward context for issuers/events actually published by the owner | **USABLE FOR COVERED FORWARD CASES ONLY** |
| Broad SEC source plane + SEC document spine | CIK + accession + exact document identity/content hash | SEC acceptance plus retrieval/record clocks remain separate | Strong canonical filing/document receipts; historical-shard recovery must be proven per selected filing | Best long-run source for 8-K/6-K legal/regulatory/financing/earnings event adapters | **PRIMITIVES BUILT; DISLOCATION ADAPTER NOT BUILT** |
| `data/edgar/material_8k_events.parquet` | Accession present | Filing date only; exact accepted-at absent | 50,936 accessions / 664 tickers in the source-architecture census; narrative-basket scope | Candidate discovery only | **NOT INTRADAY-ADMISSIBLE** |
| Capital Structure `capital_structure.event.v1` | Immutable content-addressed event id and explicit correction/link edges | `point_in_time.available_at` is keep-first system observation; public-mode escape uses SEC acceptance only for original source observations | Strong captured-event lineage; classification may be deferred/ambiguous and current estate has backlog | Financing/dilution context only where a classified owner event and lawful clock exist | **PROMISING, SOURCE-SPECIFIC MAPPING REQUIRED** |
| Earnings release bound-revision plane | Filing identity + bound release revision | SEC `acceptance_datetime` is source clock, explicitly separate from processing | Admissible PIT when exact source bytes/revisions are captured | Strong earnings-result source where available | **USABLE WITH OWNER RECEIPT** |
| BioCatalyst / clinical event estate | Owner-native event/document ids when present | Owner packets can carry `known_at` / knowledge cutoff | Several views are latest-selected/current context rather than full historical reconstruction | FDA/clinical context only for exact owner events; no blanket universe-clear claim | **PARTIAL** |
| Attention/news surfaces | Mixed item ids | Mixed/current; Hot Tape is ephemeral and historically unreconstructible | No durable, universe-wide, high-frequency PIT news history in the current estate | Context only; cannot prove absence of news | **INSUFFICIENT FOR HARD SAFETY COVERAGE** |
| Analyst actions | Revisions/coverage data exists at slower cadence | Mixed daily/current clocks | No complete low-latency analyst-action event tape established by the current census | Not a required R0 hard-clear source yet | **INSUFFICIENT** |
| Halt/LULD | Shared market-data owner is the intended source | Must be live exchange/vendor event time | Current Data OS census says no halt store exists; Massive Advanced plan identifies real-time `LULD.*` as the intended shared feed | Required safety input once the shared owner publishes it | **NOT BUILT IN CURRENT OWNER ESTATE** |

## 2. Exact source-law receipts

### 2.1 Earnings 8-K

The issuer-event readiness census classifies EDGAR earnings 8-K dates as admissible PIT event/date replay for captured filings because `acceptance_datetime` gives sub-day availability. The current collector contract records:

`(ticker, cik, accession, form, filing_date, acceptance_datetime, report_date, items)`

However the current source-architecture census found the committed parquet still lacks some of those identity fields. R0 must not infer accession from ticker/date. The lawful adapter waits for a canonical filing/document receipt or regenerated owner artifact.

### 2.2 Company Intelligence

`event_workspace.v1` already separates:

- source availability,
- owner observation,
- generation/build time,
- immutable generation lineage.

Its authority is context-only. That is compatible with R0's all-false authority model. Its limitation is coverage: a current workspace is evidence that an owner event is present, not evidence that every possible issuer catalyst was searched.

### 2.3 Capital Structure

The Capital Structure event spine explicitly preserves immutable event versions and correction/link edges. Its point-in-time law uses keep-first system availability so late ingestion cannot leak backward into a canonical replay.

That makes it a strong future adapter source, but `classified` is not automatically equivalent to "blocking for intraday mean reversion." A source-specific policy mapping must be separately frozen; deferred/ambiguous rows remain unknown.

### 2.4 Material 8-K metadata

The material 8-K table is useful for candidate capacity and accession identity, but the current architecture freeze states that it has date-only filing clocks and no exact accepted-at. It cannot support an intraday decision-time safety assertion by itself.

### 2.5 Halt/LULD

The shared market-data architecture already names a real-time LULD feed on eligible Massive plans. Separately, the Data OS census says there is currently no halt store. R0 therefore must not invent a halt-negative result from constant prices, missing bars, or the absence of a local record.

## 3. Mapping law

The R0 pure contract accepts `owner_disposition = blocking | soft | nonblocking | unknown`, but it does not create those classifications.

Every real adapter must own a small frozen mapping table with:

- exact source owner and schema/version;
- exact event type/form/item predicate;
- required identity fields;
- source-availability and observation clocks;
- correction/amendment behavior;
- ticker/security identity join;
- coverage denominator;
- disposition mapping;
- falsifier / typed refusal behavior.

If a source-specific mapping is absent or its required fields are unavailable, the adapter emits `unknown` or an unavailable source read. It does not guess from headline text, residual price, volume, or LLM prose.

## 4. Minimum honest forward-shadow posture

Today, R0 cannot truthfully claim market-wide catalyst clearance.

The correct forward-shadow posture is:

1. Attach known owner events where exact source identity and clocks exist.
2. Declare only the explicitly covered source owners in `required_sources`.
3. Mark stale/unavailable/missing required owners as `coverage_unknown`.
4. Preserve late-arriving events without rewriting the earlier decision context.
5. Keep every authority flag false.
6. Use the incumbent Radar episode id and TrialLedger; create no second event ledger.

A future Terminal chip may say:

> Catalyst coverage incomplete

or:

> No blocking event observed in covered sources as of 10:12 ET

It may not say:

> No news

unless a separately accepted source contract genuinely proves that stronger claim.

## 5. Smallest next adapter sequence

The source census supports the following order without opening a new control plane:

1. **Earnings-result adapter** from canonical EDGAR / bound-release receipts with exact SEC acceptance time.
2. **Capital-structure adapter** for a narrowly enumerated set of owner-classified financing/dilution events, with deferred/ambiguous rows mapped to unknown.
3. **Shared LULD/halt adapter** only after the existing market-data owner publishes an entitlement-aware live event seam.
4. **Other issuer catalysts** only through their existing owner event planes and exact clock contracts.

A broad "news classifier" is intentionally not first. The current estate does not support an honest complete denominator, and rebuilding a no-news reversal classifier would violate existing DNR law.

## 6. Capability state

`CATALYST_CONTEXT_CONTRACT_BUILT_SOURCE_ADAPTERS_NOT_ADMITTED`

The pure fail-closed contract can be tested now. Real source adapters remain separately gated by owner identity, clocks, coverage and disposition mapping. No market outcome, promotion, or live activation follows from this census.
