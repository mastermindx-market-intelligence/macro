# FIF-3A3 reuse map (frozen before code)

Verified 2026-08-23 against worktree `claude/fif-3a3` at pickup `origin/main`
`98a297a324f77527880fa25b919f14cee74d4c81` after Sol-observed
`f69348e80d4be151ae62d3d70e38b3ce0924d68f`. Decisions:
`DEC:FIF-1-V1-FROZEN`, `DEC:FIF-3A1-ACCEPTED-GOLDEN-ON-MAIN`,
`DEC:FIF-3A2-ACCEPTED-GOLDEN-ON-MAIN`, `DEC:FIF-3A3-REUSE-MAP`.

Contract-gap ruling: **NO STOP**. The strict parser emits Clark-notation
QNames; the query kernel indexes `taxonomy:concept`. Existing
`TAXONOMY_NAMESPACE_POLICY` in `filing_attestation.py` already maps
US GAAP 2009–2026 and DEI 2009–2026 URIs. FIF-3A3 reuses that table
inside `ixbrl_raw_ledger.canonicalize_clark_qname`. Unknown/custom
namespaces retain Clark identity and stay unmapped. The query kernel
is not patched to guess Clark notation.

## Path (BINDING_OK)

```
admitted AAPL golden package
  → parse_sec_filing_document(...)
  → ixbrl_raw_ledger.convert_parsed_filing (no XML)
  → RawFactLedger + FilingMetadata + core registry
  → GoldenAaplFinancialQueryProvider
  → execute_financial_query(...)
  → POST /api/forensics/v1/financial/query
```

One converter only. Do not create another ledger, metric registry, query
kernel, or financial API.

## Identity

| Layer | Exact ID | Source |
|---|---|---|
| Issuer | `ISS:US-XNAS-AAPL` | IssuerMaster |
| Listing | `US-XNAS-AAPL` | `listing_key` |
| Source filer | `0000320193` | accession / XBRL entity |
| Query ticker | `AAPL` | last segment of Data OS listing_key |
| Document | `sec_document_id(...)` after CIK normalize + accession/role/name spine validation | exported from `sec_document_spine.py`; `320193` ≡ `0000320193` |

Request `entity_id` remains `ISS:US-XNAS-AAPL`. Query kernel entities map
`AAPL → 0000320193`. FIP1 stays `mmx.issuer.fip1`.

## QName / unit law

- `{http://fasb.org/us-gaap/{2009-2026}}Local` → `us-gaap:Local` via `TAXONOMY_NAMESPACE_POLICY`
- `{http://xbrl.sec.gov/dei/{2009-2026}}Local` → `dei:Local`
- `{http://www.xbrl.org/2003/iso4217}USD` → `iso4217:USD`
- `{http://www.xbrl.org/2003/instance}shares` → `xbrli:shares`
- `{http://www.xbrl.org/2003/instance}pure` → `xbrli:pure`
- Apple/custom/SRT/CYD/ECD Clark QNames retain source identity
- `parsed_value` is the parser `normalized_value`; do not reapply sign/scale
- `source_occurrence_key` is parser `fact_id`

## Clocks

- `accepted_at` = SEC acceptance (`source_accepted_at`)
- `recorded_at` = package `fixture_recorded_at`
- FilingMetadata `available_at` = fixture-recorded clock, not SEC acceptance
- mapping/computed/published absent on raw source occurrences
- Both A1 and A2 are `FILED`. Do not set `revision_of`.

## Provider / HTTP

Change only `_financial_query_provider()` to `GoldenAaplFinancialQueryProvider`.
Do not activate revision or packet providers for AAPL.
The query provider source set is frozen to A1 `0000320193-25-000079` and
A2 `0000320193-26-000020` (`GOLDEN_AAPL_QUERY_ACCESSIONS`). It must not
iterate `GOLDEN_AAPL_FIXTURES`.

- AAPL golden query → 200
- Unknown issuer on this available provider → private 400 `unknown entity`
- Corrupt/missing admitted golden source → private 503
- Unlawful `FinancialQueryDataset.delivery` → private 503

Optional `FinancialQueryDataset.delivery`, default absent. The only lawful
non-null object is exact:

```
kind = committed_golden_fixture
attested = false
production_issuer_service = false
```

Wrong kind, true flags, non-booleans, missing keys, or extra keys are
unavailable. FIP1 builders omit delivery → FIF-2A bytes unchanged.
Authority remains `{"class":"context_only","display_only":true}`.

## Explicit non-goals

No real AAPL FIP. No `financial_intelligence_packet.v1` change. No
revision-history invention. No AAPL packet/revision provider. No
disclosure family. No peer set. No Filing Forensics UI. No SEC network
on the request path. No R2 or attested-history write. No Company Facts
substitution. No FIF-3A4.

## D3 — Production immutable-dataset provider (added 2026-10; WS:FINANCIAL-INTELLIGENCE-FABRIC)

`POST /api/forensics/v1/financial/{query,revisions,packet,statements}` now
select their provider corpus with one explicit, documented environment key —
**`FIF_FINANCIAL_DATASET_MODE`** — read in `app/forensics.py`:

| Value | Wiring |
|---|---|
| unset / `golden` (default) | Exactly the pre-D3 wiring, byte for byte: golden AAPL query + statements, unavailable revisions/packet. The golden path never consults the production store. |
| `production` | All four factories construct the production providers (`engine/fundamental_forensics/production_provider.py`) over the immutable dataset store (`engine/fundamental_forensics/production_datasets.py`, prefix `fundamental_forensics/production-datasets/v1/`). Production mode NEVER falls back to the golden corpus. |
| anything else | Configuration error: names-only log, typed `ProductionDatasetModeError`, and the private 503 on every affected endpoint. An invalid mode never degrades into an undocumented selection. |

The production store is built by `build_production_dataset_store()`:
explicit local dir → `FIF_PRODUCTION_DATASET_LOCAL_STORE` → the dedicated
private research-store family (`RESEARCH_LOCAL_STORE` / `R2_RESEARCH_*`,
never generic `R2_*`). No store means the private 503, never golden.

**Production delivery object.** Query, revisions, and statement responses in
production mode carry exactly (fail-closed; extra/missing keys, wrong kind,
non-bool flags, malformed id, or non-`reconstruction` basis ⇒ 503):

```json
{"kind": "production_issuer_dataset",
 "attested": false,
 "production_issuer_service": true,
 "dataset_generation_id": "ffprods_<64hex>",
 "capture_basis": "reconstruction"}
```

`attested=true` requires a D2 attestation admission reference in the
generation manifest, which does not exist yet; until then A13 forces
`attested=false` + `capture_basis="reconstruction"` for any corpus fetched
today. FIP1/golden responses keep their exact prior bytes (delivery absent
for FIP1 revisions/query, the golden object for golden query/statements).

**Refusal semantics.** An available production store with no admitted
generation for the requested canonical issuer ⇒ private 400 `unknown entity`
(`SEC:` ids and alias symbols are not accepted identifiers). A missing store,
damaged manifest, digest mismatch, missing role object, or a request whose
`recorded_at` precedes the generation's `admitted_at` ⇒ the existing private
503 with identical detail for every damage class.

**Immutability and clocks.** Generations are digest-bound (`ffprods_<64hex>`
derived from the manifest's own content core), published create-only with
byte-exact read-back before the per-issuer `latest` pointer advances by CAS;
an ambiguous write preserves EFFECT_UNKNOWN on its original target (A18).
The request path performs no SEC fetch, no iXBRL extraction, and no model
call — datasets arrive pre-materialized by the acquisition lane under the
`single_writer_operator_only` publication contract. The registry is a pinned
role object of the generation, so a future-dated live-repo mapping cannot
change a production answer (A12). Identity binds once, at issuer level via
the Data OS CIK, from the generation manifest; the request path never picks
among share classes (A14).

**Health.** `/api/forensics/health` reports the mode name and, in production,
the latest generation id + `admitted_at` on response headers only
(`X-FIF-Financial-Dataset-Mode`, `X-FIF-Dataset-Generation-Id`,
`X-FIF-Dataset-Admitted-At`) — names/ids only; the schema'd payload contract
is unchanged.
