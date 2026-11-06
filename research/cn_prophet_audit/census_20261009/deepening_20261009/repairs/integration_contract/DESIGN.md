# Integration-contract repair: hypotheses before implementation

This design was written before changing the copied prototype. Scope is a new research-only repair directory, an isolated host temporary export, and the frozen Macro source/data pin `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. The original laboratory and independent reviews remain unchanged. The incumbent R2 event namespace, archived prior-session pack, same-session settlement pack, canonical board and native daily ledger key remain the authorities and owners.

Reviewed baseline: integration manifest `d755a012d80469c241a554252e61bee88e604eb445ce7ca03ec1e2eecfdbc8b6`; independent review manifest `78fcfa3c271d214c751a40220dc92e44cec67409eb49fbe7421b9c22a32698b6`.

## Hypotheses and discriminating acceptance conditions

| Hypothesis | Concrete correction | Required positive and hostile controls |
|---|---|---|
| H1: regression belongs to the full target-session consumed set | Validate every target-session retained event ID against the complete resolved spool before iterating reconstructed daily rows. | Missing one/all transition objects with valid close objects refuses. A truly empty new session with a valid close object remains valid. |
| H2: readable storage is not sufficient schema evidence | Normalize documented Parquet null/list/scalar representations; validate native schema and keys for every row; refuse every duplicate daily key before native merge. | Conflicting duplicate orders and unknown readable schemas refuse with zero writer calls and byte-identical files. Older valid, noncolliding native legacy rows survive without new provenance. |
| H3: equal-time close authority is semantic | Canonicalize close membership/economic fields, group by exact observation time, refuse conflicting equal-time evidence, coalesce equivalent evidence and retain all supporting object identities. | Both nonce-order variants refuse when membership differs. Equal economics with irrelevant metadata or ordering differences coalesce to the same native membership receipt. |
| H4: quote-kind vocabulary cannot certify adjustment basis | Remove unconditional raw stamping. Resolve an allowed source/basis contract against exact provider-shaped payload bytes and replay the pinned native parser. Keep the contract/payload/record identities in the event and ledger. | Missing metadata, unsupported natural declarations and adjusted declarations cannot produce qualified events. A synthetic raw fixture carries an explicit scenario contract and exact replayable payload; no Boolean qualification flags. |
| H5: copied immutable fields must agree with resolved evidence | Define and hash the entire first-observation projection, then compare existing content to the earliest authentic resolved event and its archived pack before native FIRST_WINS merge. | A changed first price, event/quote clock, basis, entry class, source or frozen value refuses. A valid later repeat updates last/count fields and preserves the first projection. |
| H6: numeric validation must be total over JSON numbers | Catch conversion overflow in the numeric predicate and keep invalid-quote failures on the per-name typed path. | `10**400` is false under `finite`, makes that quote dark without aborting peers, and is refused at other numeric boundaries. |
| H7: each pack trust boundary owns score semantics | Apply finite 0–100 validation to archived packs as well as canonical-board projection. | Rehashed scores -1 and 100.01 refuse; zero and 100 remain valid. |

## Quote provenance decision

The pinned `engine/live_quotes.py` parser emits source, quote kind and timestamp details but no adjustment-basis declaration. The pinned `engine/marketing/live_verify.py::_quotes_from_snapshot` further projects snapshots to price/previous close/change/time and the generic source `quotes`. This code evidence cannot certify natural raw prices. The repaired research interface therefore leaves those inputs unqualified unless an existing owner supplies a genuinely supported contract and source receipt.

The positive laboratory path will explicitly use a synthetic provider-shaped payload with units defined by the research scenario. A fixed research contract binds its schema, field mapping, allowed adjustment semantics and the exact native Yahoo parser source identity. The parser is replayed over retained payload bytes; quotes/events must equal that output. The label will distinguish a synthetic unadjusted scenario from an actual vendor receipt. No production provider is admitted by an asserted Boolean or by numerical previous-close agreement. The fixture proves the interface; it does not certify the vendor's natural adjustment policy.

## Compatibility and custody

- The three-authority join remains prior-session archived pack → first event; current-session settlement pack → gate verdict; current-session canonical board → membership receipt.
- The native `cn_prophet_live.forward/v1` schema and `(date, ticker, kind)` key remain. New research evidence versions are additive; older target-session unbound rows require incumbent-owner adjudication. Older noncolliding valid native legacy rows remain untouched in meaning and acquire no new provenance.
- Exact duplicate event objects remain idempotent. Duplicate existing daily rows are refused uniformly, including exact duplicates, because the native key contract is unique and no repair policy is being invented here.
- New research source evidence belongs inside the existing event envelope/archive transport. No second production ledger, collector, source owner or runtime is proposed.
- Refusal occurs before the native atomic writer. Tests will exercise real Parquet using the existing host runtime in a new temporary directory, with source hashes checked and network disabled.
- Natural scheduled execution, provider/source custody, benchmark/fill economics and tradability remain separate gates. The matched-controls owner is investigating tradability; this repair does not invent ST, liquidity or rank policy.

## Design amendments from draft challenge, before the repaired run

The independent reviewer supplied two additional timing counterexamples while the repair was still a draft. A quote received at 02:01 and a pack built at 02:01 cannot support an event backdated to 02:00 merely because its envelope was published at 02:01. Each event must therefore resolve both its source receipt and archived pack by its own event time; envelope publication remains a separate upper bound. The fixture will retain a valid 02:01 control and refusals for each backdated variant.

Native event timestamps have second precision. After exact event-ID deduplication and the single-generation check, distinct event identities with the same daily key and event timestamp are refused as ambiguous. A content digest cannot determine which observation was first. Exact replay remains idempotent and a strictly later authentic repeat can update the native last-observation/count fields while preserving the first projection. These amendments do not add an operational observation-order authority.

Before sealing, the producer identified a compatibility consequence of that strict receipt boundary: a native timestamp truncated to 02:00:00 would reject a genuine source receipt and evaluation at 02:00:00.500000. The repaired wrapper verifies that native event/artifact timestamps agree with the supplied evaluation second, then retains that actual supplied evaluation instant at full precision in the existing ISO `ts` and `built_at` fields. No new time field or independent clock authority is invented. The added native fractional-second positive control must pass while genuinely backdated event/pack/source cases continue to refuse. Distinct identities at exactly the same retained instant still refuse.
