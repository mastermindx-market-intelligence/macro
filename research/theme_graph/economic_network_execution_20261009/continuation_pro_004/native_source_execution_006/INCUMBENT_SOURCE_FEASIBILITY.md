# MU current-capture feasibility: exact incumbent source route

## Decision

**The next executable slice is one present-time MU split-history acquisition through the existing CorpActions producer, immutable source-kernel intake, an exact-generation read and a local repeat of the same acquisition.** The accepted Massive enterprise record covers the proposed US corporate-action research and retention purpose. This review found no reason to reopen the global licence gate or wait on a historical owner name. Actual account access, source-store effects and returned data remain unobserved: this lane made **zero provider calls**.

The principal's minimal request is MU, earliest date 2026-09-30, basis date 2026-09-30. It requests **execution_date.gte=2026-09-30**; the basis date is metadata and does not supply an upper filter. A future event, an empty response, a partial attempt or a typed failure is a useful actual result. None becomes a positive September 30 applicability claim. This slice deliberately supplies current source evidence before the incomplete global 120-case frame; it is not a selected WP02 issuer record.

The decisive source is the full 528-line [Massive split-evidence module at 87b01101](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/engine/close_pass/massive_split_evidence.py). Its full-file SHA-256 is **a1d32eacd48c90f793df717a7284fa044054c476241c622e9b9f9abc997c6942**, as recorded in SOURCE_PINS.json.

## Source freshness and scope

The native workspace remained at published **7af7a9785d74c1b420b23de3be0eac6946cc2200**. Read-only Git object access examined actual current Macro **87b01101ef13aa20ded205f3a2b267b68d094def** without fetching, moving references or importing applications. Eighteen exact source objects are pinned in SOURCE_PINS.json, with per-file semantic read scopes; complete hashes do not imply complete audits of every large shared module. The split producer itself was read in full. Its wrapper, licence record, relevant registry rows, source-family/root/reader interfaces and alternative paths were examined narrowly.

The starting evidence remains the frozen 35-file owner-interface census and the principal's Massive product-scope addendum. Their manifests and individual bytes are preserved. The principal reports the protected Mastermind revision **8d838c8df453a78fac3459b7458576e1ba2cbcb8**, with INDEX and ten companions reread and unchanged from the prior loaded procedure set; this lane does not recast that principal witness as its own new bootstrap read.

## Exact callable step for the principal

The existing wrapper delegates to the same source module already reviewed. The default producer resolves the existing key at call time and uses its fixed official HTTPS endpoint; no new client, registry, credentials file or factory is required. Source root validation occurs before the network request. The principal must choose and check a fresh private root with the required leaf, outside the repository/site and disallowed root locations. This lane has neither created nor activated that root. See the [wrapper and existing resolver](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/engine/close_pass/massive_close.py) and [source-kernel root/reader contract](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/engine/neuralweb/market_memory_source_kernel.py).

~~~python
# Proposed principal action only; NOT RUN by this reviewer.
from engine.close_pass.massive_close import retain_split_history
from engine.close_pass.massive_split_evidence import (
    SplitEvidenceReader,
    intake_split_acquisition,
)

# Supplied by the principal; no default store/root is created by this report.
private_root = PRINCIPAL_SELECTED_PRIVATE_ROOT
# Required leaf: sources-massive-split-history-v1

stored = retain_split_history(
    "MU", "2026-09-30", "2026-09-30", store_root=private_root
)
observed = SplitEvidenceReader(
    private_root, generation_id=stored.generation_id
).read(stored.receipt["receipt_id"])

# Reuse the exact captured attempt; this is NOT a second provider call.
repeated = intake_split_acquisition(stored.artifact, store_root=private_root)
~~~

The repeat should return created=false and the same artifact, receipt and generation identity. Reader receipts contain their own actual read clocks, so fresh read receipts need not be byte-identical. Calling retain_split_history again generates a new acquisition UUID and another provider request; it is not the idempotency test. A lost acknowledgment requires reconciliation of the original process and specific store effects before retrying. The kernel publication boundary is a complete generation followed by HEAD; an unpublished orphan receipt is not readable as a committed source observation.

MU is the intended real-issuer vendor token in this pilot. The request preserves exact case-sensitive ticker identity; this review has not established a canonical legal issuer, share-class history or complete corporate perimeter merely from that token.

## What the native route actually does

The request goes to **https://api.massive.com/stocks/v1/splits**, with ticker=MU, execution_date.gte=2026-09-30, sort=execution_date.asc and limit=1000. No endpoint migration is required. The producer already rejects foreign redirects/next-page hosts, validates continuation query identity and uses the existing credential in an Authorization header. It does not silently retry attempts or follow a provider-supplied credential parameter.

The code bounds each page to 1 MiB, with at most eight pages, 4,096 retained rows and a 30-second timeout per HTTP attempt. Complete/partial/failed acquisition status and per-page status remain explicit. An acquisition that exceeds the source kernel's 1 MiB canonical-object limit may be observed by the producer but is refused at intake rather than truncated into an admitted artifact. The code validates duplicate native event IDs, ticker equality, date shape, ordering and positive finite decimal split tokens. These checks establish contract consistency, not the economic truth or historical applicability of a row.

A successful acquisition produces a UUID and actual start/end nanosecond clocks. Retained per-page metadata includes status, observed-body SHA-256/byte count/completeness and row counts. The stored artifact contains selected parsed provider rows, exact request and attempt metadata. **The raw provider response body is not retained.** Its body hash is useful observed-byte identity; it cannot reconstruct the discarded response or establish external custody by itself. The module also does not retain HTTP Date, Last-Modified, ETag, VersionId or a first-publication/correction-vintage certificate.

Intake validates the acquisition, prevents future completion relative to intake, binds canonical artifact/capture/receipt identities and publishes immutable objects and a generation through the existing source kernel. A same-identity/different-payload conflict is refused. The pinned reader checks receipt/object/source/vintage/revision bindings and returns the full source artifact, owner receipt and a newly generated actual read receipt. Neither the stored source nor the reader has a K-cutoff admission interface. All these are observed source-code properties, not claims that this native capture or read has happened. [Exact implementation](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/engine/close_pass/massive_split_evidence.py).

## Permissions, ownership and admission

The entire accepted [MASSIVE_ENTITLEMENT_RECORD](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/research/licenses/MASSIVE_ENTITLEMENT_RECORD.md) was read at the exact current pin. It records the enterprise agreement and redistribution addendum effective August 9, operator-confirmed closure of the global licensing gate, and historical/reference/corporate-action research, retention/reproducibility and other stated uses. The proposed research retention fits that recorded scope. Its remaining dataset-specific written conditions still control; this request does not acquire raw NBBO. The private agreement and secret values were not requested or inspected. Actual credential availability or a successful HTTP response cannot be inferred from this record; a technical failure would not, by itself, revoke the accepted grant.

The [existing dataset row](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/config/dataset_registry.yml) is:

| Field | Current recorded value |
|---|---|
| Dataset | reference.corporate_actions.massive_split_evidence |
| Status and layer | PROPOSED, L0 |
| Owner | macro-dashboard |
| Producer | engine/close_pass/massive_close.py::retain_split_history |
| Reader | engine/close_pass/massive_split_evidence.py::SplitEvidenceReader |
| Licence | massive_enterprise_research_retention |
| Store | Private sources-massive-split-history-v1 objects/receipts/generations |
| Activation note | Opt-in source implementation; no live producer or store activation |

This is enough to identify an incumbent path for the principal's bounded manual capture. It is not a PRODUCED row or a claim of scheduled/native activation. No registration is changed or borrowed. The [stock-day R2 workstream](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/agentos/workstreams/WS-MASSIVE-STOCK-DAY-R2-COHERENCE.md) names an active owner for a separate mutable pipeline; its status is advisory evidence, not observed live execution. A narrowly scoped AgentOS text query for the split module found no matching workstream/decision path; that is not proof no owner or live work exists. No fleet census or producer-runtime probe was performed.

The split artifact and owner receipt inherit [Market Memory's context authority](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/engine/neuralweb/market_memory.py): tier=display, horizon_role=context, context_only=true, proposal_weight=0 and all listed may_* capabilities false. The artifact, owner receipt and actual reader receipt preserve basis_eligible=false. This source does not introduce Graph1, ranking, trade, prediction, outcome or training admission. An unkeyed seal, digest or supplied owner label is not self-authenticating source custody.

## D, K and F remain distinct

| Axis | What this call can establish | What stays unproved |
|---|---|---|
| D = September 30 | The supplied lower execution-date filter and separately retained basis date; provider-returned event dates within a bounded current observation | Exact-D applicability, raw RTH close/price/currency, all earlier actions, issuer/class completeness |
| K = October 9 at 00:00Z | No first-publication certificate is supplied by this route | Whether this version, classification or factor existed and was public by K |
| F = actual later acquisition | Real producer start/end, per-page attempts, owner intake/assembly and actual read clocks, if the principal executes successfully | Provider publication time; authentication of an invented historical clock |
| Identity | Exact vendor ticker and native event ID consistency | Historical canonical legal entity, shares and listing perimeter |
| Rights | The accepted enterprise record and its stated scope | A newly observed account response or proof satisfying any separate written feed condition |

Do not set F to a convenient report timestamp, floor nanoseconds back toward K, relabel the basis date as publication time or treat receipt assembly as durable publication. The source kernel's generation commit is an owner storage event; it is separate from provider first availability. The source's nanosecond fields also cannot silently become the WP02 kernel's strict at-most-six-fractional-digit timestamp contract. That adapter is outside this slice.

The exact missing historical gate is a trusted owner-bound pre-K capture/read of the relevant version, or provider publication/version/correction evidence with sufficiently established semantics and custody. A present response does not provide it merely because execution_date is old. The [Data OS known_at/as-of helper](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/lib/dataos/temporal.py) cannot repair that by assigning ingestion at F to publication at K. The research selector's real-source authority/rights/history holds remain unchanged.

## Why other existing paths are not the first step

The [session-close helper](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/engine/close_pass/massive_close.py) can request September 30 raw grouped US daily closes for a wanted MU token. It fetches the whole grouped market response and can fall back to a same-session snapshot; matching and finalized/source labels are useful incumbent distinctions. But its dictionary result does not retain original response bytes/headers, immutable vendor vintage or first-publication proof. Its observed_at is generated at call start. It is not the same bounded immutable producer/read chain and would still leave K unproved.

The [Massive flatfile client](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/collectors/massive_flatfiles.py) already supports the candidate key **us_stocks_sip/day_aggs_v1/2026/09/2026-09-30.csv.gz**. A principal could later inspect actual object metadata through that existing client, but no such HEAD/GET occurred here. LastModified is not automatically first publication, an ETag is not automatically SHA-256, and version metadata must bind the exact acquired bytes. Its normal fetch path reads/decompresses the whole object, creates a cache directory even when use_cache=false, and projects to a DataFrame without retaining that metadata. The [stock-day owner](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/collectors/massive_stock_day.py) mutates canonical R2-backed stores, so invoking its backfill/publish machinery would enlarge this pilot's effect scope.

The [SPY verified reader](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/engine/neuralweb/market_memory_sources_spy.py) could inspect an authentic previously sealed September 30 owner artifact if one exists. Its [scheduled producer](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/scripts/ingest_market_memory_sources_spy.py) cannot naturally recreate a missed historical seal now: it checks the real five-minute D+1 seal window before acquiring credentials/data. Supplying fake clock/SealState would defeat that evidence. No private SPY store was inspected. SPY is an ETF canary, not an eligible real-issuer WP02 case.

Existing [ticker_details](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/collectors/polygon_options.py) and [current shares proxy/cache](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/scripts/entry_radar_vendor.py) calls do not establish dated, issuer-reported, class-complete share counts. They must not be multiplied by a September 30 close and relabeled historical capitalization. The [existing security-master evidence path](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/scripts/build_security_master.py) itself distinguishes request date and actual binding clocks from first-seen/publication proof. This lane does not rebuild the master or acquire a global issuer frame.

## Proof to retain from the actual next action

The principal's result should bind the exact source revision/bytes, native process exit, exact query, actual producer F and status, stored artifact/receipt/generation IDs and hashes, and fresh read receipt. Preserve requested-case count **one** separately from provider page/row counts. Empty rows do not become evidence that no splits ever occurred; future rows do not become applicable-by-D adjustments.

On a completed intake, read through the exact returned generation, then replay the same captured artifact once locally. Preserve the complete/partial/failed source record. Missing credentials may refuse before an acquisition exists; transport/provider failures may produce a retained failed/partial attempt. Oversize/corrupt intake or unavailable readback must remain an explicit failure rather than an invented successful observation. No response is substituted or reclassified to reach a positive pilot result.

Critical falsifiers are a different query or artifact binding, new identity on same-acquisition intake, dropped failure/empty evidence, future rows treated as D applicable, clocks relabeled as K publication, or any basis/authority promotion. Account, network or store failures are real findings for this one request, not reasons to run a broad entitlement battery or switch accounts/endpoints.

## Effect accounting and return

Eight native read-only processes completed with exit zero:

| Read | RDC process | Python child | Exit |
|---|---:|---:|---:|
| 001 | 35014 | 35034 | 0 |
| 002 | 36626 | 36642 | 0 |
| 003 | 39397 | 39412 | 0 |
| 004 | 42492 | 42556 | 0 |
| 005 | 44895 | 44913 | 0 |
| 006 | 46441 | 46457 | 0 |
| 007 | 47247 | 47262 | 0 |
| 008 | 52812 | 52832 | 0 |

READ_002's terminal completion was observed in the task transcript but not archived as a separate completion JSON; its initial output and source identities are retained. Its process-receipt command entry is explicitly a description, not reconstructed exact shell text. Other commands/completions are retained. No process remains outstanding.

**Provider calls, data acquisitions, secret/environment-value reads, application imports/tests, private runtime-store reads, native file writes and Git mutations: zero.** Scratch changes are limited to this new feasibility packet. The principal separately retrieved additional current Massive documentation; those are the principal's source reads and are not counted as this lane's independent browsing or proof of a provider response.

The ready result is a concrete existing native path with accepted research-retention scope and honest current-only limits. The remaining immediate facts are the actual request outcome and principal-owned private store/read/repeat evidence. D-close price, K-vintage, canonical identity, share/class/action completeness and real WP02 admission remain separately withheld.

**STOP — read-only feasibility review complete.**

