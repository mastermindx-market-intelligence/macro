# Native interface recommendation for the additive Company Intelligence slice

Read-only review, 2026-10-09. Exact Macro base: `1f9fb63fec63aaaee17ec0094f4d319dc63d24a5`. Chairman execution authorization was supplied by the principal; this worker was commissioned only to inspect native interfaces. No source change, registration, store write, publisher, job, UI, K3-D, neural or market promotion occurred. Protected procedure refresh remains principal-owned; this worker does not claim independently loaded current protected procedures. Existing #7870, #8245, #7891 and micro-membership modifying paths remain untouched.

## Recommendation

Proceed with a pure, additive manual-candidate validator and ephemeral loss-aware projection under the principal's named Company Intelligence scope. It can prove that selected text and quantities reproduce against supplied original source bytes. Keep structural support, semantic/manual adjudication, identity resolution, rights eligibility and historical eligibility separate. A structurally supported candidate can remain inspectable while its production/PIT eligibility is explicitly unavailable. It must not silently become an admitted bilateral fact or a new canonical clock/identity/entitlement.

The native Data OS catalog has **22 dataset rows**, none for SEC issuer-disclosure, Micron disclosure or generic relationship observations. Existing SEC producers and receipt machinery do not themselves register a relationship dataset. The committed catalog marks reference identity datasets PRODUCED, but this review did not read runtime parquet snapshots. No actual Micron source bytes, licensed entitlement or live admission receipt was inspected. Thus no real SEC/Micron relationship record is claimed admitted by this review.

## Exact temporal and registry APIs

From `lib.dataos.temporal`:

```python
utc(value: datetime | str) -> datetime
known_at(row: Mapping[str, object], profile: TemporalProfile) -> datetime
as_of_filter(rows: Iterable[Mapping[str, object]], t: datetime | str,
             profile: TemporalProfile) -> list[dict]
assert_pit_readable(profile: TemporalProfile) -> None
pit_refusal_reason(profile: TemporalProfile) -> str | None
```

Import `TemporalError`, `PointInTimeError`, `Clock`, `TemporalProfile`. `utc` refuses dates, naive datetime values and naive strings. Do not promote date-only evidence to midnight before calling it. `known_at` uses the profile's native ordered clocks, not a maximum of clocks. `as_of_filter` refuses an ineligible profile before reading rows and returns plain dictionaries; it does not certify arbitrary row schemas, entitlements or native dataset adoption.

| Profile | Required clocks | Other required fields | Native knowability |
|---|---|---|---|
| BARS | period_start, period_end, ingested_at | None | published_at, then ingested_at |
| REVISABLE_RELEASE | period_end, published_at, ingested_at | revision_seq | published_at, then ingested_at |
| SNAPSHOT_SERIES | effective_at, ingested_at | None | published_at, then ingested_at |
| EVENT | event_at, published_at, ingested_at | None | published_at, then ingested_at |
| DERIVED | computed_at | code_version, input_cutoffs | PIT refused |
| INTELLIGENCE | computed_at, served_at | code_version, input_cutoffs, data_cutoff_at, expires_at | served_at |

This describes the actual enum, not a selection menu for the new candidate. The caller must obtain the profile from the adopted input contract. A helper call with EVENT and a handcrafted published_at row is not an adoption receipt. Required clocks and fields must be checked independently; `known_at` alone can succeed with a row that does not satisfy all the declared profile obligations.

From `lib.dataos.registry`:

```python
load_registry(path: str | Path | None = None) -> Registry
validate_registry(registry: Registry) -> list[str]
Registry.get(dataset_id: str) -> DatasetContract | None
Registry.ids() -> tuple[str, ...]
Registry.inputs_of(dataset_id: str) -> tuple[str, ...]
```

Use a supplied exact registry path from the bound workspace, not a second catalog. Unknown IDs return None. The code exposes `DatasetStatus.PRODUCED`, `PROPOSED`, `RETIRED`; missing or proposed contracts cannot establish a produced eligible input. Do not instantiate a local DatasetContract and treat it as registered. Registry validation checks structure, enums and DAG references, not live production, source bytes or legal authorization. Its default `REGISTRY_PATH` is anchored to the repository root rather than cwd; an explicit path can bind the owning workspace’s inspected registry.

For historical projection, filter every owner input through its own registered profile before rederiving state. A DERIVED result remains non-PIT-readable. A current-rule derivation from historical inputs is recomputation, distinct from an accepted served-artifact replay. If input profile, required clocks, precision or identity-at-cutoff is unavailable, return eligibility gaps; never use the latest state as a historical answer.

## Pure source receipt APIs

Prefer the native flat-document receipt for a manually selected HTML/text range:

```python
from engine.earnings_release.receipts import (
    receipt_for_char_span, replay_receipt, SpanReceipt,
    ReceiptError, ReceiptReplayError,
)
receipt_for_char_span(*, source: str, source_sha256: str,
                      char_start: int, char_end: int) -> SpanReceipt
replay_receipt(receipt: SpanReceipt | Mapping[str, Any], *, source: str) -> str
```

Replay rehashes the full UTF-8 source, exact byte range, raw span and normalized `value_text`; it returns that replayed normalized text. Keep raw `span_text` and normalized `value_text` distinct. Decode supplied original bytes strictly and prove exact UTF-8 round-trip before using this text-based API. Unsupported encoding is a support gap, not permission to normalize/re-encode and call the result original bytes. Compute the complete body digest locally from those exact bytes; do not trust supplied digest labels.

The interoperable Company Intelligence receipt is also usable:

```python
from engine.company_intelligence.documents import (
    text_span, verify_span, SourceSpan, SourceDocument,
    FilingKey, TypedAbsence, absent_number, DocumentError,
)
text_span(*, document_id: str, document_version: int, body_sha256: str,
          segment_index: int, segment_text: str, start_byte: int,
          end_byte: int, text: str, speaker=None, role=None, chapter=None,
          rights_profile="rp_unknown_v1", display_excerpt=None) -> SourceSpan
verify_span(span: SourceSpan, *, segment_text: str, body_sha256: str) -> None
absent_number(subject: str, *, basis=None, units=None, period=None,
              source=None, event_id=None) -> TypedAbsence | None
```

`text_span` uses the existing earnings-narrative receipt. If projecting it from a flat source, verify the complete original document digest yourself and use a precisely defined segment coordinate space. Do not cast `earnings_release.span_receipt/v1` into the distinct `source_span.v1` receipt shape. `SourceDocument`/`SourceSpan` are context-only; their constructors do not prove rights or registry adoption. PDF table/slide addresses may be `address_only`; they cannot become byte-replayed citations without bytes.

`TypedAbsence(reason, subject, detail="", missing_fields=(), event_id=None, document_id=None)` has a closed vocabulary. Reuse existing reasons such as `document_bytes_not_held`, `no_span_addressable_evidence`, `missing_source`, `missing_basis`, `missing_units`, `missing_period`, or `unjoinable_filing_identity` where their meaning fits. Do not force unrelated profile/rights gaps into an inaccurate reason or change the shared enum. The additive candidate may report separate eligibility check failures without presenting them as native admitted states. `absent_number` checks basis/units/period/source but has no denominator contract; buyer-spend, seller-revenue and COGS denominators still need explicit candidate validation.

## Identity boundary

Use `lib.dataos.identity.IssuerMaster.from_records(records)` over the supplied committed security-master snapshot. Callable current-only lookups are:

```python
issuer_of_security(security_id: str) -> str | None
securities_of_issuer(issuer_id_: str) -> tuple[str, ...]
cik_of_issuer(issuer_id_: str) -> str | None
listing_key_of_security(security_id: str) -> str | None
security_state_of(security_id: str) -> str | None
superseded_by_of(security_id: str) -> str | None
```

The native reader intentionally has no asof parameter. `cik_of_issuer` refuses conflicting current CIKs. Unknown and active securities both return None from `security_state_of`, so first confirm row membership. Tombstoned duplicate securities must not re-enter aggregation. Use existing stored issuer IDs; do not call `issuer_id()` or `security_id()` as an allocator in this slice.

`VendorAliasTable.from_records(records)` exposes `resolve(vendor, vendor_symbol, on: date, *, decision_at=None) -> str | None`. Polygon reference aliases require explicit aware decision clocks and retained evidence/binding seals. Dated alias naming does not establish historical issuer ownership, legal subsidiary mapping or current fetch-symbol semantics.

Company Intelligence's local `company_id_for_cik` yields `cik:...` and its local `security_id_for` yields venue/ticker IDs. Data OS uses stored `ISS:...`/`SEC:...` IDs. Keep local identifiers namespaced and require exact native crosswalk receipts before attaching a canonical issuer. Brand, product and unnamed counterparty references stay source-local unless their existing owner resolves them; no invented legal-entity IDs.

## Available source/profile/rights receipts

The registered reference datasets are `reference.security_master`, `reference.vendor_aliases`, `reference.issuer_master` (SNAPSHOT_SERIES) and the two migration datasets (EVENT). They supply identity contracts, not SEC disclosure relationship contracts.

`engine.company_intelligence.issuer_profiles.profile_for_ticker(ticker, *, publication="public", fiscal_scope=None) -> IssuerProfile | None` dispatches AAPL and DHI/PHM/KBH/TOL, plus opt-in private PG with required fiscal scope. MU returns None. `IssuerProfile` contains extraction callables; it is not a Data OS TemporalProfile or entitlement grant. `validate_selected_facts` is closed to the exact PG metric set and source semantics, so it cannot validate arbitrary supplier/customer claims.

`qa_exchange` declares `rp_public_primary_v1` and `rp_internal_private_v1`. The PG adapter maps the former to `sec_edgar` and uses the private profile for selected PG observations. These conventions do not prove the new candidate's entitlement, retention, embedding, training or display use. `SourceDocument.rights_profile` is a label; its constructor validates rights_state vocabulary, not a license. No reviewed primitive authorizes an arbitrary SEC/Micron URL based on visibility. Preserve supplied native policy/contract receipts, or mark the affected purpose unavailable. Do not create an authorizer from this research register.

Consequently, supplied SEC/Micron original bytes can support **structural candidate inspection now**. Admitted relationship truth, canonical cross-source identity, historical eligibility and downstream licensed uses require their exact native receipts. Missing profiles must not erase supported evidence, and supported evidence must not erase missing eligibility.

## Strongest failure cases and required wrapper checks

1. **Date fabrication:** `SourceDocument._utc` promotes date-only values to midnight UTC and naive values to UTC. Preserve raw precision and validate with strict native `utc` before constructing a document used for eligibility. A serialization round-trip cannot recover the lost precision.
2. **Display drift:** `text_span(..., display_excerpt="different text")` can retain a valid receipt. `verify_span` does not compare display_excerpt to the source slice. The additive validator must bind its displayed quote to exact replayed text; independently typed rendering is a different field.
3. **Matching labels, wrong body:** segment verification can match a supplied body hash label without rehashing the whole document. Verify complete original bytes independently; never accept hash agreement alone.
4. **Boolean/coerced coordinates:** some receipt deserialization uses int() and native construction does not universally reject bool coordinates. Require exact integer type, nonnegative ordered bounds and UTF-8 alignment before invoking native receipt code.
5. **Unsupported semantic claim:** valid bytes mentioning Micron/NVIDIA do not establish supply direction, realized sales, legal counterparties or quantitative dependence. Preserve human adjudication state and exact role/quantity spans; anonymous or missing amounts remain null.
6. **Profile laundering:** selecting EVENT locally, borrowing FRED/identity dataset IDs or inserting a DatasetContract into a private Registry can make helper calls succeed without native adoption. Reject this for eligibility.
7. **Historical identity leakage:** current issuer CIK or a current ticker mapping cannot resolve a historical issuer binding. Preserve source CIK/counterparty mention and report the historical crosswalk gap.
8. **Correction/absence confusion:** missing a later feed member does not terminate a relationship. Keep revision provenance, conflicting observations and explicit termination evidence separate; no overwrite or confidence averaging.

## Existing tests to reuse

Inspection only; no suites were run in this read-only lane. Relevant existing tests are `tests/test_dataos_temporal.py` (naive/date refusal, profile clocks, DERIVED refusal, cutoff filtering), `tests/test_dataos_registry.py` (unknown ID, enum coercion, proposed/produced status, required fields), `tests/test_dataos_identity.py` (current CIK ambiguity, missing identity, tombstones, alias intervals), `tests/test_company_intelligence_spine.py` (source replay, body/hash drift, address-only refusal, typed numeric absence), and `tests/test_earnings_release_binding.py` (full-source/span/value tamper and deterministic offline receipts). Add narrowly scoped manual-candidate tests for the eight wrapper cases rather than modifying these shared owners.

## Immutable source provenance

All originals were fetched at the exact supplied base through read-only GitHub APIs. Canonical prefix: `https://github.com/mastermindx-market-intelligence/macro/blob/1f9fb63fec63aaaee17ec0094f4d319dc63d24a5/`.

| Exact path | Blob SHA | Decisive inspected location |
|---|---|---|
| [lib/dataos/temporal.py](https://github.com/mastermindx-market-intelligence/macro/blob/1f9fb63fec63aaaee17ec0094f4d319dc63d24a5/lib/dataos/temporal.py) | 094b149a8b9158f19cb99c4005568c12db96ed41 | Profile obligations, KNOWN_AT_CLOCKS, utc/known_at/as_of_filter |
| [lib/dataos/registry.py](https://github.com/mastermindx-market-intelligence/macro/blob/1f9fb63fec63aaaee17ec0094f4d319dc63d24a5/lib/dataos/registry.py) | 91c4a8eed34b118902dd2a80678b71472e328dca | DatasetContract, Registry.get, load/validate_registry |
| [config/dataset_registry.yml](https://github.com/mastermindx-market-intelligence/macro/blob/1f9fb63fec63aaaee17ec0094f4d319dc63d24a5/config/dataset_registry.yml) | 42252174a9f97c0643d30c9057455761aff35f80 | All22 dataset declarations; reference identity rows |
| [lib/dataos/identity.py](https://github.com/mastermindx-market-intelligence/macro/blob/1f9fb63fec63aaaee17ec0094f4d319dc63d24a5/lib/dataos/identity.py) | ea8485596e57fd1e686bfdb9d75708a3a3845fda | IssuerMaster current-only contract and lookup methods; aliases |
| [engine/company_intelligence/documents.py](https://github.com/mastermindx-market-intelligence/macro/blob/1f9fb63fec63aaaee17ec0094f4d319dc63d24a5/engine/company_intelligence/documents.py) | eda8651bdac1a4bc01c24565cb35f5a13848d179 | _utc, document/span constructors, text_span/verify_span/TypedAbsence |
| [engine/earnings_release/receipts.py](https://github.com/mastermindx-market-intelligence/macro/blob/1f9fb63fec63aaaee17ec0094f4d319dc63d24a5/engine/earnings_release/receipts.py) | 296255a45c0ca297298287b4af759cb0f96afbc0 | receipt_for_char_span, replay_receipt, strict source/span/value binding |
| [engine/company_intelligence/identity.py](https://github.com/mastermindx-market-intelligence/macro/blob/1f9fb63fec63aaaee17ec0094f4d319dc63d24a5/engine/company_intelligence/identity.py) | 0e3daabeeebad2482e938f4a3949018dac663a29 | CIK-local and venue/ticker IDs |
| [engine/company_intelligence/issuer_profiles.py](https://github.com/mastermindx-market-intelligence/macro/blob/1f9fb63fec63aaaee17ec0094f4d319dc63d24a5/engine/company_intelligence/issuer_profiles.py) | 110177b42f749a6e6781f7b8846a8541a8c553f1 | IssuerProfile, profile_for_ticker dispatch |
| [engine/company_intelligence/qa_exchange.py](https://github.com/mastermindx-market-intelligence/macro/blob/1f9fb63fec63aaaee17ec0094f4d319dc63d24a5/engine/company_intelligence/qa_exchange.py) | 41f8d1f215120dd71c29d706cff1561fe91c8c8f | Rights labels and source-clock owner gap |
| [engine/company_intelligence/economic_observations.py](https://github.com/mastermindx-market-intelligence/macro/blob/1f9fb63fec63aaaee17ec0094f4d319dc63d24a5/engine/company_intelligence/economic_observations.py) | b7833b0793070a1d361d352b30af5fd6f4ab66f4 | PG-only validate_selected_facts |
| [engine/company_intelligence/pg_profile.py](https://github.com/mastermindx-market-intelligence/macro/blob/1f9fb63fec63aaaee17ec0094f4d319dc63d24a5/engine/company_intelligence/pg_profile.py) | ada7b1e45ebadae7a99e0d95862e7cc547a9280e | PG_CIK/private scope; PROFILE_SOURCE_FAMILY |

Next bounded action: principal implements only the additive validator/projection module and focused tests in its authorized native workspace, consumes supplied exact bytes and receipts, and returns useful source support alongside explicit eligibility gaps. No registration, publisher, store or native profile mutation is implied by this recommendation.
