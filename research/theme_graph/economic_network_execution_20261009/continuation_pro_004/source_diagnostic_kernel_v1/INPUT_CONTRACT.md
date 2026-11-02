# WP02 v1 byte contract — implementation review candidate

This artifact describes the bounded **structural and artificial-model subset** of the adopted WP02 method. It is not a generic real-source verifier. Source truth, authority, rights, history, incumbent issuer identity and activity classifications are never authenticated here. The real-source admission interface remains absent.

## Entry points and immutable method

`diagnose(request_bytes: bytes, *, policy_bytes: bytes, adoption_bytes: bytes) -> dict` is the research entry point. `canonical_bytes(result) -> bytes` emits canonical UTF-8 JSON: sorted keys, no whitespace, no terminal newline, `ensure_ascii=False`, no nonfinite values. The CLI takes explicit `--input`, `--policy`, `--adoption` regular-file paths, uses bounded reads, prints JSON and exits **2** because every result is `NOT_READY` for real use. Path names confer no authority. There is no callback, callable admission adapter, registry, store, provider or transport argument.

Exact raw policy: 60,312 bytes, SHA-256 `d41422d76219b1c5d3a3c9cbb19a1bc3124433031200b09499033bd4dc30d522`. Exact adoption sidecar: 9,593 bytes, SHA-256 `645a20a39842d9c5a03b4ff39a37280d1aa02c32ef545c061d0aa959f06e0016`. The only effective override is `/capitalization/numeric_rule`; its old value must match. Effective canonical policy content SHA-256 is `90bec6078348af6e41c9538e12e0443dd37d671c85a7089c64c547f5ce5e7714`. These are exact content bindings, not signatures, owner authentication or source custody.

The fixed seed is `GMI-WP02-20261009-v1`; D is `2026-09-30`, K is `2026-10-09T00:00:00Z`. Actual F remains null. There is no reseed, parameter override, quota fallback or issuer replacement argument.

## Result and hold boundary

Every output has `schema=research.gmi.wp02.source_diagnostic/v1`, `status=STRUCTURAL_ONLY`, `readiness=NOT_READY`. `real_inputs` contains only null values for eligible population, per-pool cardinalities, selected cohort, quantiles, resolved capitalizations, actual F and actual INT flow. Admission is `NOT_ADMITTED`; rank, size, trade, prediction, production, export, training, graph and authenticated source/identity flags are false.

Six axes remain separate: receipt structure; matching supplied bytes; source authority; historical coverage; entitlement; derivation reconciliation. The latter can describe internal model reconciliation. Source authority always remains `SOURCE_AUTHORITY_UNVERIFIED`, history `FRAME_HISTORY_UNPROVEN`, rights `SOURCE_RIGHTS_UNVERIFIED`. Unknown rights are not evidence of an absent license. Matching supplied text to supplied hashes does not establish original publisher bytes. A `SYNTHETIC_MODEL` label is a request to perform artificial deductions; it is not an assertion that the data is true, artificial in origin, licensed or safe to promote.

Real mode performs bounded supplied-record checks but never runs the cohort selector or returns modeled cap/quantile/selection values. Synthetic mode may return `ARTIFICIAL_MODEL_COMPLETE` with explicit artificial results; it still cannot fulfill real-source readiness or the genuine difficult-case requirement. `holds` contains stable code/scope objects. No omission, zero coercion, partial cap, partial cohort or output truncation is used to pass a gate. Output over the byte budget produces an explicit whole-output refusal with null synthetic content.

## JSON envelope

All objects are closed: additional keys refuse. All listed keys are required unless called optional. UTF-8, duplicate-key rejection and bounds apply before expensive derivation. Decimal quantities are **strings**. JSON noninteger numbers (including exponent notation), nonfinite constants and booleans used as numbers refuse. IDs retain exact UTF-8 bytes with no trimming, case folding or normalization.

Top-level keys:

| Key | Shape |
|---|---|
| `schema` | Exact `research.gmi.wp02.source_diagnostic_request/v1` |
| `mode` | Optional `REAL_SOURCE` (default) or `SYNTHETIC_MODEL` |
| `sources` | Array of the source objects below |
| `records` | One modeled economic-issuer record per record ID; duplicate nonnull issuer IDs refuse globally |
| `history` | One complete artificial seven-jurisdiction partition model, below |
| `fx` | Single supplied ECB date/rate model, below |
| `counts` | Closed count object; fields may be missing/null and are then held distinctly |
| `stress_cases` | Separately denominated supplied cases, below; empty permitted |
| `claims` | Closed optional claim fields, ignored for authority |

`claims` permits optional boolean `producer_success`, `source_authority_verified`, `history_proven`, `rights_verified`, plus optional nullable string `owner_id`, `receipt_sha256`, `source_path`, `actual_F`. Even all-true claim flags cannot change a real result. A callable is not representable in JSON; an additional callback/adapter key refuses.

Source object: `{source_id, content, sha256, byte_length}`. `content` is an exact UTF-8 string supplied in the envelope, `sha256` is lowercase hex, `byte_length` is a nonnegative integer excluding booleans. Source IDs are unique. Numeric/history sources can be reused. Evidence span: `{source_id, start, end}` with nonnegative byte offsets and a nonempty half-open slice matching the expected exact UTF-8 token. This establishes supplied-byte consistency only; semantic meaning, context sufficiency and original-source custody remain unverified.

## Membership model

`history` keys: `kind`, `target_date`, `anchor_date`, `anchor_public_upper`, `partitions`, `declared_partition_ids`, `anchor_members`, `target_members`, `anchor_source_id`, `target_source_id`, `events_source_id`, `events`, `coverage_start`, `coverage_end`, `covered_event_kinds`, `declared_event_ids`, `expected_anchor_member_ids`, `expected_target_member_ids`.

- `kind`: `SNAPSHOT`, `RECONSTRUCTION` or `CURRENT_ONLY`. Current-only always holds. Snapshot requires anchor=D and no events. Reconstruction requires a distinct anchor.
- Dates are exact ISO local dates in this **artificial date-boundary model**. Public upper bounds require canonical UTC strings `YYYY-MM-DDTHH:MM:SS[.fraction]Z`, where an optional decimal fraction has one through six ASCII digits. Finer precision returns `UTC_TIMESTAMP_PRECISION_UNSUPPORTED` before datetime conversion, including additional zero digits. Other timestamp shapes return `EXPLICIT_UTC_BOUND_REQUIRED`; calendar and clock validity are also checked. No truncation, rounding, offset conversion, comma fraction, week/basic date or date-only inferred timezone is accepted. The model does not implement real venue timezone/cutoff semantics. Unknown real semantics remain held.
- `partitions` contains `{partition_id,jurisdiction}` rows. Jurisdictions are `US`, `CN_MAINLAND`, `HK`, `CA`, `UK`, `JP`, `EU`; all seven must occur. The declared partition-ID set must equal the inventory. This is supplied-model coverage, not an authoritative venue census.
- Membership state: `{member_id,record_id,partition_id,instrument,primary_status}`. Instrument is `ORDINARY`, `DEPOSITARY_RECEIPT` or `EXCLUDED`; primary status is `PRIMARY` or `SECONDARY`. IDs are unique within each complete set. Multiple source-security members may map to one record. Every D record must be represented and no reconstructed D record may be dropped.
- Anchor, target and event source IDs each point to actual supplied JSON source bytes whose complete parsed content must equal the corresponding array. This detects raw-to-parsed changes and offset missing/extra states. The two expected-member-ID arrays also must match their sets. Counts alone never decide reconciliation.
- Membership event: `{event_id,effective_date,sequence,kind,public_upper,before,after}`. ID and `(date,sequence)` are unique, with full before/after state arrays. K bounds apply to the anchor and every event. `ADMISSION` has 0→1 state, `REMOVAL` 1→0, other kinds 1→1. Other kinds are `TRANSFER`, `CONVERSION`, `IDENTITY_REPLACEMENT`, `PRIMARY_STATUS_CHANGE`. The interval is `(min(A,D),max(A,D)]`; declared coverage endpoints, all six covered event kinds and the exact declared event-ID set must agree. Later anchors reverse events in descending effective order; every current after-state must match before reversing. Earlier anchors apply forward with exact before-state checks. The final full set is compared with the target set, including differing states as well as missing and extra IDs.

## Records and capitalization subset

Record: `{record_id,issuer_id,eligibility,primary_groups,activity,exclusion_reason,exclusion_evidence,class_ids,classes}`. Null issuer/activity, empty primaries or `UNRESOLVED` eligibility holds the potentially eligible row rather than dropping it. `ELIGIBLE` records require primary groups matching primary membership lines; multiple eligible primaries are assigned by the frozen policy hash. Activity is one of `SEMICONDUCTOR_CLOUD`, `INDUSTRIALS`, `CONSUMER`, `ENERGY_MATERIALS`, `FINANCIALS`, `HEALTHCARE`. These are **supplied model categories**, not verified business classifications. `EXCLUDED` requires reason `INSTRUMENT_OUTSIDE`, `ACTIVITY_OUTSIDE` or `PRIMARY_OUTSIDE`, with a supplied evidence span matching that exact token. This remains an unauthenticated model exclusion. Other records require null exclusion fields.

Class: `{class_id,kind,d_basis,shares,price,quote_scale,quote_scale_evidence,currency,counter,calendar,actions,declared_event_ids,share_bridge_event_ids,price_bridge_event_ids}`. Declared class IDs must exactly equal the nonduplicate supplied classes. Only `kind=ORDINARY` is computed. `ADR`, `UNLISTED_PROXY`, `ZERO_OR_CEASED` are recognized and return `RICHER_CLASS_RIGHTS_OR_CEASED_FACT_NOT_IMPLEMENTED`; no class is silently omitted.

`counter={mic,security_id}` is prebound by the model, not selected after seeing values. `calendar` is the supplied unique scheduled-date list over D−10 through D. The selected raw price must be on it; at most five later supplied sessions and ten calendar days are allowed. Actual exchange-calendar and counter-choice verification is deferred. `quote_scale` is a positive decimal string with a matching evidence span. Currency is bound to the supplied common FX table. Missing/conflicting/basis-unproved components hold the whole issuer. Shares use the greatest eligible actual measurement date within 183 days. Price uses the greatest eligible actual measurement date within ten days. No latest-date conflict falls back to an older clean value.

### Assertion bundle

Bundle: `{state_kind,assertions,relations}`. Shares, price and FX require `POINT`. The lower-level assertion helper also models static `PERSISTENT` values, with all overlapping D states competing; different start dates do not resolve disagreement. Assertions have `{assertion_id,publisher_id,coordinate,valid_to,public_upper,value,unit_basis,status,evidence}`. `status` is `ACTUAL` or `ESTIMATED` (retained/excluded). `coordinate` is a measurement date or persistent valid start. Point `valid_to` is null; persistent `valid_to` is null or an exclusive date after the start. Values are positive decimal strings matching their supplied span. Fact grouping is derived from the enclosing issuer/class/component and measurement date, **not publisher or publication recency**. Different unresolved unit bases hold.

Relation: `{relation_id,kind,publisher_id,new_id,old_id,fact_coordinate,unit_basis,public_upper,evidence,resolution_owner_id}`. `SUPERSEDES` and `ALIAS` need both referenced IDs; `RETRACTS` needs `new_id=null`. Evidence token is `KIND:new_id:old_id`, with an empty new part for retraction. IDs, scope, unit basis, date/interval, public ordering and an acyclic applicable correction graph are checked. Same-publisher, same-scope modeled corrections may remove the old assertion; cross-publisher corrections are a typed unsupported hold. Aliases must agree numerically and never erase active evidence. A retraction leaving no value returns unavailable. Later publication alone never supersedes. Links and owner strings remain unauthenticated model relations. Persistent interval transitions are not implemented; no later-start winner is invented.

### Signed actions and price/share unit bridge

Action: `{event_id,effective_date,sequence,kind,public_upper,value,before_basis,after_basis,evidence,zero_evidence}`. Kind is `DELTA` or `SPLIT`. IDs/order must be unique, public upper≤K, event after the earliest selected share/price coordinate and no later than D. Same-day action vs measurement order is unsupported and held. A missing known numeric effect is held.

Positive decimal strings are required for actual share measurements, raw price, quote scale, FX and split factors. `DELTA` accepts signed decimals; zero additionally requires an explicit span matching `EXPLICIT_NO_CHANGE:event_id`. Its ordinary numeric evidence separately matches the actual signed token. Delta before/after basis must be equal. Split factors require an explicit changed unit basis. Declared event IDs equal the entire action set; share bridge IDs equal all events after the share date; price bridge IDs equal all splits after the raw price date. Shares apply delta or factor once; prices divide by each later split factor. Both end in `d_basis`. Resulting shares must stay positive, as must every class and total cap. No absolute value, clipping, partial-class sum or theoretical price adjustment for issuance is applied.

### FX

`fx={series,available_dates,reference_date,rates}`. Series must exactly be `ECB euro foreign exchange reference rates`. Reference date must be the greatest supplied available date≤D and no more than five days old. This is conditional on supplied date completeness, not actual ECB history. Rate row is `{currency,bundle}`; each required point value at that same date uses basis `UNITS_CURRENCY_PER_EUR`. USD is required; EUR denominator is fixed one, and USD/USD is one. For X, conversion is USD-per-EUR divided by X-per-EUR. No alternative provider/date, peg, CNY/CNH assumption or missing-currency fallback exists.

## Counts and difficult cases

Count fields: `source_declared_total`, `exhaustive_total`, `raw_record_count`, `parsed_record_count`, `duplicates_resolved_count`, `anchor_count`, `resulting_d_member_count`, `identity_resolved_issuer_count`, `evidenced_out_of_scope_count`, `potentially_eligible_omission_count`, `unresolved_potentially_eligible_count`, plus `event_ADMISSION`, `event_REMOVAL`, `event_TRANSFER`, `event_CONVERSION`, `event_IDENTITY_REPLACEMENT`, `event_PRIMARY_STATUS_CHANGE`. Unknown and absent fields remain distinct from zero and block synthetic readiness. `source_declared_total` alone may be `NOT_PUBLISHED`, requiring supplied exhaustive count reconciliation. No count becomes an independently proved source fact. The declared omission count must be zero to model closed coverage; this does not prove real omissions absent.

Stress case: `{case_id,stratum,issuer_id,document_id,document_role,locator,label,evidence,independent_review_id,before_vendor_outputs}`. The last field is a boolean claim only. Document roles are annual 2023/2024/2025 or `INTERIM_OR_MATERIAL_EVENT_2026`. Labels are `IDENTITY_ALIAS`, `ANON_CONCENTRATION`, `DUAL_FLOW`, `TERMINATION_EXPLICIT`, `SUPPLIER_LIST_STALE`, `SEGMENT_RECAST`, `DIMENSION_CUSTOM`, `QUANTITY_DENOMINATOR`. Evidence matches the label token. Cases are sorted by exact issuer/document/locator/case bytes and checked for modeled cohort/stratum consistency. Actual genuine-case counts, independent review and pre-vendor sequence remain unverified. The actual 30/6-per-stratum requirement cannot be fulfilled by fixture labels; shortfalls never cause issuer replacement.

## Full synthetic quota mechanism

All 42 jurisdiction/activity pools must have modeled history, issuer, primary, activity and whole-cap consistency before thresholds. Descending exact rational caps give k1=ceil(N/2), k2=ceil(3N/4); L≥t1, M≥t2 and <t1, S<t2. Ties stay together in the higher band. Empty pools emit explicit N=0/null thresholds, not a missing-data inference. All candidates carry MICRO/S_ABS/M_ABS/L_ABS tags using unchanged USD250m/2b/10b boundaries.

The four non-INT strata choose 2/1/1 per activity by fixed length-prefixed SHA-256 priority. INT uses three country capacities of eight, all 18 activity/size cells and actual candidate capacities. It retains the full matrix and deficient mincut. Lexicographic inclusion removes the current candidate before trying a decremented country/cell demand, compares flow against the decreasing common target, accepts target zero and retains failed completion certificates. Initial infeasibility returns no selected cohort. Success verifies 120 distinct IDs and all strata/activity/size/country quotas; counts never waive those constraints.

## Explicit resource bounds and determinism

Input ≤2 MiB; output ≤8 MiB; 512 records; 1,024 sources; ≤256 KiB each source; eight classes per issuer; 16 assertions and 32 relations per bundle; 1,024 membership events; 32 actions per class; 128 partitions; 128 stress cases; 24 JSON nesting levels; 160,000 pre-parse lexical structural tokens. IDs are nonempty strict UTF-8 ≤256 bytes (claim strings≤2,048). Decimal strings allow at most 48 integer digits and 24 fractional digits, no exponent notation; JSON integer literals allow at most 12 digits. Limits refuse explicitly, never truncate.

Identical request bytes yield identical output bytes. Raw/canonical request bindings necessarily change when input array order changes; the fixed-priority selected IDs, pool values and flow outcome do not. Array-order invariance is a model-result claim, not a claim that different original files have identical byte hashes.

This contract intentionally defers real-source authority and rights paths, full source semantics, arbitrary publisher reconciliation, richer class/ADR/proxy facts, real calendars/counter selection, real venue clocks, activity business evidence, segment supplements, genuine case adjudication and post-unblinding study replacement. No all-policy implementation or production acceptance is claimed.

### Final auditability and resource clarifications

Assertion IDs are globally unique across the supplied components, so one source assertion ID cannot silently denote two facts. Each resolution receipt retains all supplied assertion fields, including value token, publisher, public upper bound, measurement/valid coordinates, unit basis and source span; it also binds the complete original bundle's canonical content. These retained fields remain unauthenticated source claims.

For one-to-one membership events, TRANSFER may change only partition ID; CONVERSION only instrument; IDENTITY_REPLACEMENT only member/record identity; PRIMARY_STATUS_CHANGE only primary status. Compound transitions require separately ordered events; an unrelated field cannot be smuggled through an event label. The full before/after state is still checked in either direction.

Every derived rational numerator and denominator is bounded to **8,192 bits**, including intermediate bridges, FX division and class sums. Exceeding that bound emits `EXACT_ARITHMETIC_BUDGET` and holds the affected full cap/model; it does not round, silently truncate, omit a class or depend on Python's ambient integer-to-string digit limit. This is an explicit research resource bound, not a financial magnitude eligibility rule.
