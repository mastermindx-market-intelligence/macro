# Options matrix exact-byte retention

Source candidate on existing Macro PR #7861. This is deterministic source proof;
no production storage, runtime installation, source rights or Saved Research
admission is established by this document.

The existing `scripts/build_options_matrix.py` serializes each usable matrix once.
It validates root/schema/session and a **16777216-byte (16 MiB)** ceiling, retains
and reads back the exact local immutable file, conditionally creates and reads
back the same bytes in the existing R2 bucket when `--publish` is requested, then
advances the current local and R2 heads. Failure before verified retention leaves
both prior heads intact. Local head replacement is atomic and preserves read mode.

Local immutable publication prepares and fsyncs a sibling temporary file before
an atomic no-replace hard link exposes the digest path. Interrupted/short writes
and pre-publication fsync failures leave no final key, so an exact-key retry can
succeed. A competing existing digest is verified and never replaced or removed.
Caught failures clean the temporary; abrupt process termination may leave an
unpublished temporary, but cannot expose partial bytes at the immutable key.

Current local-head inspection checks the file size before allocation and then
reads at most the byte ceiling plus one to detect growth. Strict UTF-8 JSON
parsing refuses duplicate keys, nonfinite numbers and malformed or contradictory
identity metadata. Legacy objects lacking modern schema/root fields and valid
empty snapshots remain replaceable; supplied fields must be valid. A usable
legacy snapshot still requires a trustworthy source session.

History key: `options_structure/matrix/history/<ROOT>/<SHA256>.json`.
Local equivalent: `<existing-out>/history/<ROOT>/<SHA256>.json`.
No separate manifest, publisher, timer, consumer store or bucket is introduced.
The existing public delivery classification still applies; publication is not a
source-use grant. Operational installation and natural-source gates remain held.

`engine/options_matrix_retention.py` derives and parses references:
`sha256:<64lowerhex>:bytes:<positive-canonical-integer>:session:<YYYY-MM-DD|unknown>`.
Fingerprint must equal the digest. Root is the existing Options producer grammar
`[A-Z0-9](?:[A-Z0-9.-]{0,13}[A-Z0-9])?`, full match with `..` refused.
Root spelling alone never establishes canonical underlying/security identity.
Reference length is at most256, byte length is bounded by16MiB and JS safe integer.
Reads check ContentLength, bound every stream read, check EOF/trailing bytes, close
the stream and verify actual hash, schema, root and session before success.
Existing exact bytes are idempotent; collision refuses. Conditional-write timeout
is reconciled by one same-key exact readback; unresolved/missing bytes refuse.
There is no current-head, nearest-date or cached-value fallback.

A valid top-level `session` falls back to `_build_meta.asof_date` only if absent or
null. Both supplied clocks must be valid/equal. Malformed metadata refuses;
`unknown` means both clocks absent/null. Top-level `asof` is build time, not first
availability. Unsupported availability/OI clocks are not synthesized. Empty
matrices may have retained identity, but cannot satisfy primary cell membership;
the publisher continues to withhold empty/null matrices from current publication.

## Lossless coordinates

`matrix_coordinate_tokens(ref, raw)` supplies exact `(expiry, strike-string)` keys
from verified raw bytes using Decimal parsing, independently of UI Number parsing.
It enforces the agreed12-integral/8-fractional-digit positive selection domain,
canonicalizes trailing zeros without ambient Decimal context, bounds exponent and
coefficient before formatting, and refuses duplicate source coordinate keys.
`999999999999.12345678` stays that exact string; the rounded UI key
`999999999999.1234` is not a member. Consumers must carry the exact token or refuse;
they must not reconstruct identity from a rounded Number. No structural schema is
narrowed to hide parser loss. Tiny exponents1e-999999999 and1e-1000027 refuse before
formatting across default/narrow/wide Decimal contexts.

Current engine domain: `_in_window` normalizes source strikes to mill precision;
`cells[].strike` uses `_f(k)` (two decimals), while top-level `strikes` retains the
normalized mill values. Therefore membership uses exact retained cell coordinates,
not the separate strikes array. Duplicate cell coordinates caused by rounding are
unselectable. This helper does not establish call/put side availability, canonical
subject binding, rights or runtime admission. Consumers retain those gates.

## Observed call/put sides

`matrix_observed_side_tokens(ref, raw)` supplies `(expiry, strike-string, side)`
tuples in source-cell order, call before put. It reuses the unchanged coordinate
helper and its exact reference/hash/length/schema/root/session and duplicate-cell
validation. A side requires at least one of its own OI or volume observations:
`call_oi`/`call_vol` for `call`, `put_oi`/`put_vol` for `put`. Explicit zero is an
observation; absent/null counts are not. Both counts on both sides are validated,
so one valid count cannot hide a malformed supplied field. Any nonnumeric,
boolean, negative, fractional or nonfinite supplied count refuses the whole result.

Counts are reparsed from exact bytes as Decimal and checked by coefficient and
exponent without ambient rounding, integer expansion or fixed-point rendering.
Fractions such as `9007199254740992.5`, `1.000000000000000000000000000001` and
`1e-400` refuse even when binary-float decoding loses their fraction. Numerical
zero, including `0e-400`, and trailing-zero integral values remain observations.
The work stays bounded by source coefficient length, not exponent magnitude.

Opposite-side counts, aggregate/derived exposure, delta OI, unusual metadata and
top-level strike/expiration lists cannot establish membership. Empty matrices
return no witnesses. Observed membership establishes neither a security-contract
identity nor availability of any other metric, rights or runtime admission. A
future resolver must return `HISTORICAL_UNAVAILABLE` for missing primary or
comparison membership rather than silently filtering or substituting selections.
Save remains disabled; publication behavior, schemas and storage are unchanged.

Focused regression command: `python3 -m pytest -q -p no:cacheprovider tests/test_options_matrix_retention.py -k observed_side`.
The suite includes real `build_matrix` and publisher serialization over synthetic
parquet with independently missing or explicit-zero call/put OI and volume.

## Reproducible fixture evidence

`tests/fixtures/options_matrix_retention/a.json` and `b.json` are exact outputs of
real `build_matrix` over the labelled synthetic parquet fixture
`tests/test_options_matrix.py::_session_repair_store`, serialized by the actual
publisher. Clock was fixed to2026-10-08T00:00:00+00:00 before building. A has EOD/Greek
sessions September21–22 with OI through23; B adds EOD/Greeks23. These are fixture
observations, never claims of naturally published market data.

- A: `sha256:cb50c35a3250b48d70169af2a3aa1450f5c4478bc1dc5fe01b191307fcd2cfb2:bytes:2950:session:2026-09-22`
- B: `sha256:e8537aedb1005b01db8725983d1c255051562b10054d6cad86ada2bb3e7f6de7:bytes:2971:session:2026-09-23`

Run `python3 -m pytest -q -p no:cacheprovider tests/test_options_matrix.py tests/test_options_matrix_retention.py`.
The fixture test drives the actual publisher against a fake S3 store: publish A,
publish B, reopen A with exact original bytes, and verify B remains current.
Failure tests cover missing/corrupt/truncated/oversize/wrong-root/session bytes,
canonical references, local collisions, conditional races, pre-write failures and
lost write acknowledgments. There is no object-store network call in these tests.

## Admission gaps retained

The canonical `reference.vendor_aliases` reader is `lib/dataos/identity.py`.
The observed local canonical parquet has vendors ledger, membership, store,
theme_graph_native, yahoo, yahoo_fetch and **zero thetadata rows**. Its existence
cannot bind a Theta producer root using another vendor's ticker equality. A valid
mapping must be supplied through the existing identity owner, not a new registry.

The inspected `engine/theme_graph/rights_use.py::current_use_verdict` accepts
selection-cohort capture purposes/markets. It does not supply an Options request
binding authenticated principal, schema/root/digest and display/export action to
a current policy decision. Source-use rights remain unavailable. No public R2 URL,
product entitlement, retained digest or fixture can substitute for that decision.

Independent Research Lab and IW2 peers reproduced A/B interoperability (13Python
and26TypeScript checks); their earlier scoped acceptance remains separate from
frozen candidate review and real-store/publication/production acceptance.
