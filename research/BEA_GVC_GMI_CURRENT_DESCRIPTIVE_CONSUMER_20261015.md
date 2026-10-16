# BEA GVC — GMI current-descriptive consumer candidate

**Status: CODED / SYNTHETICALLY TESTED / SOURCE NOT ADMITTED / PUBLIC ROUTE NOT INSTALLED.**

Dependencies: Macro PR #9433 is the scoped first-party BEA source-purpose decision and proposed L0/L1 registry contract. Macro PR #9444 supplies offline original-byte candidates and full 138-view staging/index comparators. Their DRAFT/HOLD, rights and source-access gates are not bypassed by this leaf.

## Consumer contract

The read-only `engine/market_ontology/bea_gvc_current.py` projection uses the EXISTING `lib.dataos.registry.Registry` as source and rights owner. It requires exact BEA L0 and L1 IDs, L1→L0 dependency, owner, layer, PRODUCED status, scoped license, separately granted rights and decision references. A missing or PROPOSED source is refused before opening or parsing supplied bytes.

A caller then supplies an exact industry JSONL buffer and independently expected SHA-256, owner generation, native UTC ingestion instant and revision. These caller inputs are NOT an authenticated Data OS receipt; a claimed digest or positive row flags do not establish source custody, rights, native clocks or publication authority. The actual Data OS owner must independently qualify and bind its original L0, retained corrections and L1 transaction before the app uses any such read.

The projection verifies eight accounting years (2017–2024), 139 unique commodities per year, exact source codes, consistent order, **all nine exact BEA original-response table digests and corresponding capture-receipt digests per accounting year**, unchanging source-lineage/producer identity, signed dollar-million regional accounting, May 21 2026 edition DAY precision, missing historical first-known clocks, aligned generations/native observation and non-ranking/non-trading/non-company flags. It retains negative geographic adjustments and unresolved 5241X-vs-5241XX identity. It emits yearly descriptive aggregates sorted by accounting year, never magnitude. These digest strings cannot themselves authenticate original files: the Data OS owner must do that.

Every result is typed UNAVAILABLE or CANDIDATE_NOT_PUBLISHED with authority ceiling internal_descriptive_candidate_only and may_publish=false. Canonical packet bytes are deterministic for a prospective human/machine adapter but remain nonpublic. The consumer does not authenticate a subscriber, install an HTTP route, create a graph node/edge, use market prices or generate trade signals. Market Ontology exposure-map graph/rights owners are untouched.

## Verification and CI

`tests/test_bea_gvc_current_descriptive.py` uses synthetic fixtures exclusively, including a hypothetical PRODUCED registry (not an actual source receipt). Refusal tests include missing/proposed status before byte touch, contract/rights failures, mixed generation, missing PIT, invalid UTC clock, forged publication, unsigned amounts, duplicate/incomplete/drifting commodity rows, and untrusted source hashes. This file neither reads real BEA original responses nor validates their private source axes.

The existing CI manifest will run these tests as a scoped code-gate job rather than adding an independent workflow. Test discovery and packing constraints are validated explicitly. No previously denied original Use-axis/read-workbook operation, local registry-validation operation, private research view or rights inquiry is replayed.

## Verified local boundaries (October 15 continuation)

- Nine hermetic consumer tests passed on current source, exercising all eight yearly aggregates, non-admitted packet serialization, invalid-status/rights/identity/provenance/clock/grain/rounding refusals, and original nine-table/capture receipt lineage consistency. This is all SYNTHETIC source data.
- The GMI consumer suite is discoverable by the incumbent CI inventory once staged in Git. The new additive code job was inferred as scoped to 23 source/test paths with eight conservative fallback paths; it was selected by all three relevant source/test/library probes and excluded from unrelated homepage, content-builder and Prophet probes (unchanged totals 136/134/129).
- Four focused incumbent CI packing/curated-closure regressions passed, and manifest fragment validation passed with 320 logical jobs / 322 fragments. None of these checks supplies missing native source, formal independent review, public runtime or browser acceptance. This new branch still requires exact-head hosted CI.

## Production remains HELD

Real acceptance still requires lawful original 72-response L0 validation, source industry axis resolution, accepted 5241X/5241XX mapping or explicit unresolved handling, installed L0/L1 UTC ingest/revision/correction chain and registry PRODUCED promotion by the current Data OS owner. Existing app authentication and entitlement then must be proven alongside same-generation browser/API descriptive results. This candidate is not a release, approval, producer or new control plane.
