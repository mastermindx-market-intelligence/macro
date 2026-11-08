# Options matrix exact-byte retention

The retention implementation originated in Macro PR #7861. This is source documentation;
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
tuples in source-cell order, call before put. It reuses the coordinate
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

Both coordinate and observed-side helpers use one exact-number decoder with an
isolated Decimal context. Unsupported exponents, including zero tokens such as
`0e-9223372036854775809`, always raise `HistoricalUnavailable`, regardless of the
caller's `InvalidOperation` trap. The decoder preserves caller flags/settings,
never substitutes a float, and leaves the existing coordinate normalization and
observation-count rules unchanged. Supported tiny zero exponents remain valid.

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
The existing writer now supports one explicitly observed-day `thetadata/SPY`
root relation, described in [direct registrant intake](dataos/direct-registrant-intake.md).
Its captured source evidence, canonical SEC target, event-date interval and
availability clocks constrain every lookup. Other vendors' ticker equality
cannot supply a missing relation; older and future sessions remain unbound.

The inspected `engine/theme_graph/rights_use.py::current_use_verdict` accepts
selection-cohort capture purposes/markets. It does not supply an Options request
binding authenticated principal, schema/root/digest and display/export action to
a current policy decision. Source-use rights remain unavailable. No public R2 URL,
product entitlement, retained digest or fixture can substitute for that decision.

Independent Research Lab and IW2 peers reproduced A/B interoperability (13Python
and26TypeScript checks); their earlier scoped acceptance remains separate from
frozen candidate review and real-store/publication/production acceptance.

## Optional identity on a publication observation

The existing one-shot observer can join its exact verified Matrix bytes to the
captured canonical SPY identity:

```sh
python3 scripts/observe_options_matrix_publication.py \
  --repo /path/to/deployed/repo --out /existing/options_matrix \
  --identity-vendor thetadata --receipt /path/to/new-observation.json
```

Use the existing provisioned store client and producer output. The flag captures
the deployed repository's `data/reference/vendor_aliases.parquet`,
`security_master.parquet` and `_receipt.json` with their hashes and actual read
completion clocks. The alias independently binds the source evidence retained
inside the writer receipt. The exact verified Matrix supplies the root and source
session to `resolve_option_matrix_security`; it does not infer them from a ticker
label or the observer's wall clock.

`identity.scope` is explicitly SPY only. `identity.complete` requires a successful
publication observation and a resolved canonical target for that Matrix session.
Invalid or unavailable captures, retired/conflicting targets, unbound sessions
and failed store verification cannot produce identity success. With the flag,
CLI exit0 requires both publication and identity success. Without it, the existing
publication result and exit semantics stay unchanged. The observation remains
read-only apart from its new exclusive local receipt.

When `--prior` is supplied, a successful prior-history reopen is followed by a
final read of the current local and remote heads. A head change, disappearance or
denial at that boundary makes the observation unstable and prevents advancing or
identity success. Failed prior reads do not trigger an additional head read.
This proves the observed sequence only; it does not lock the publisher or promise
that heads remain unchanged after their final read.

Capture is a finite, non-atomic read using the incumbent bounded local reader.
It does not authenticate HTTP source provenance, prove a natural invocation,
extend the root relation's date interval, establish IDX identity or grant rights,
fresh entitlement or Saved Research admission. A synthetic Matrix exercising
this adapter remains synthetic even when its reference inputs are real.

## Exact saved-selection membership composition

`resolve_option_matrix_selection` in the existing workspace Options identity
module accepts the exact Matrix reference/capture, its canonical identity inputs,
and at most 2048 bytes of closed `options_matrix_selection.v1` JSON. It verifies
underlying identity and exact own-side membership using the existing retention
helpers. Strikes retain canonical decimal strings throughout; missing pins or
ambiguous source coordinates refuse the complete selection.

The immutable result preserves primary and comparison roles, comparison order,
and the stored view. The primary may also appear once among the comparisons.
Side/expiry filters produce hidden flags without removing pins; expiry membership
uses the full snapshot. A zero OI/volume observation is a valid side witness.
The chosen metric is recorded without asserting that its value is available.

This pure composition makes no store read or write and grants no source-use
rights, fresh entitlement, contract identity or Saved Research admission. Existing
Investigation v1/v2 remain unchanged; future v3, SQL, authenticated runtime and
production reopen still require their own integration. The tests reuse the
unchanged 76-vector IW2 selection corpus plus exact-byte/identity membership cases.

## Selection on an exact current or reopened snapshot

The same one-shot publication check accepts `--selection /path/to/selection.json`
with `--identity-vendor thetadata`. It captures the exact selection bytes, digest
and actual read-completion clock before creating the provisioned store client.
The file must be nonempty and at most 2048 bytes; selection syntax and membership
are resolved by the existing consumer described above.

The default `--selection-target current` checks the observed current SPY snapshot.
For an exact reopen, use `--selection-target prior --prior /path/to/prior.json`.
This uses the bytes from the existing prior-history GET, with its completion
clock, then checks current heads again. It makes no extra history GET and never
substitutes current B bytes when reopened A is missing, denied, changed, unbound
or lacks the selected coordinate. The current Matrix and the selected prior
Matrix must each have a valid captured canonical identity for its own session.

The receipt's separate `selection` result names the target, exact Matrix reference
and digest, canonical underlying, captured selection digest and clock, decision
and availability times, primary/comparisons, view and hidden flags. Selection
completion requires successful stable publication and current identity, then
successful membership in the selected snapshot. Selection failure preserves the
publication fields but makes the opt-in CLI exit 1; invalid request/capture exits
2 before any store GET. Without selection flags, existing output/read counts and
exit semantics remain unchanged. Capture clocks are checked before store reads
and again against the actual final decision time.

This is a finite observation with the existing non-atomic local reader, not a
publisher lock, authenticated provenance, metric-availability proof, source-use
right or Save grant. Fake-store tests remain synthetic. An actual A/B/reopen run
still requires the existing admitted producer runtime and store, matching Matrix
bytes, valid session-specific identity evidence and separate rights/IW2 gates.

## R2 head precondition

`_upload_r2` reads `options_structure/matrix/<ROOT>.json` before `put_object`.
The read follows the history snapshot bound: `NoSuchKey`, `NotFound` and `404`
are missing; `ContentLength` must be an int no larger than the 16 MiB ceiling;
the body is read in chunks of at most 64 KiB, up to that ceiling plus one byte,
and closed in `finally`. A missing key is published. Any other read error, an
oversize object, non-UTF-8, invalid or duplicate-key or non-finite JSON, a
schema mismatch, a root mismatch, or a usable head (cells and spot present)
without a trustworthy source session refuses the put, logs an error, and
returns false. A legacy empty head (no cells, or spot null) may be replaced.
A usable head session newer than the candidate session is not overwritten; the
error log contains `resolved session <candidate> older than R2 head <head>`.
A head session equal to or older than the candidate is published, which is how
a stale published head self-heals to the candidate.

When the published head is newer than the candidate, the local head and the
immutable history copy may still advance to that candidate. Only the published
R2 head is protected from regression. The process exits 1 with
`R2 publication failed`, the existing fail-closed signal. The guard runs only
inside `_upload_r2`, which the publisher calls under `--publish`, so a
non-publish run makes no new network call.

Not in this guard: an ETag `If-Match` compare-and-swap. R2 support for that
precondition is unverified, so a concurrent writer between the head GET and
PUT can still race. The build clock (`asof`) inside the digest is a separate
matter (R3) and is not compared here.

## Fresh source-use decision consumer

`engine.intelligence_workspace.options_use.resolve_authorized_option_selection`
composes the existing captured identity/selection reader with two required trusted
server callbacks. It first validates the exact Matrix, canonical underlying and
selection, then checks fresh product entitlement and an independent source-use
decision. No backend is configured by this module. Missing callbacks, malformed
responses, denied/unavailable decisions and inconsistent clocks refuse with
`OptionUseRefused`; validated values are returned only after both checks succeed.

Each call creates a fresh request ID and binds the principal, issuer, authentication
epoch, producer/schema, root, digest, byte length, source session, vendor, canonical
underlying, selection digest and exact `display` or `export` action. The response
must echo the complete binding with exact types, include source-family and policy/
registry provenance, and have a decision timestamp inside that call's observed
rights-callback interval. Display permission cannot authorize export, and an earlier
allow cannot be reused, even with a frozen clock. Timestamp precision is limited to
microseconds; invalid offsets and unrepresentable UTC instants refuse.

The caller remains responsible for authenticating the principal and configuring
genuine server callbacks. Supplied labels are not proof of credentials, source
family or licensing. The immutable return is short-lived in-process; it must not be
persisted as a grant or treated as Save authorization. Existing cohort policy,
rights registries, v1/v2 manifests, SQL, runtime installation and Save are unchanged.
The unit tests use synthetic decisions and establish no live permission.


### Fresh server principal and product access

`app.options_auth.resolve_authenticated_option_selection` composes the existing
exact selection/source-use consumer with Macro's uncached Auth and billing readers.
Its caller supplies the current access token and a genuine server source-use
callback. There is no HTTP route, rights backend or Save grant in this addition.

The adapter verifies the token with the configured Supabase Auth service before
reading its subject, issuer and session ID. `auth_epoch` binds that accepted
`session_id`; it is not a fabricated clock. Authentication is repeated after
selection validation and must match the initial user/issuer/session. Billing is
read without the paywall positive cache or outage grace, preserving Terminal's
existing exact `terminal_live_options` feature or private unlimited predicate.
An expired token after the billing read, failed authentication or a mismatched
session refuses. A billing outage supplies the existing free default; the current
operator allowlist remains its separate, explicit product-access exception.
Existing website authentication/cache behavior is unchanged. Credentials are not
returned or persisted by the adapter.

These are sequential observations, not atomic or perpetual authorization. Supabase
[getUser](https://supabase.com/docs/reference/python/auth-getuser) authenticates a
user; immediate sign-out revocation additionally needs the documented
[auth.sessions check](https://supabase.com/docs/guides/auth/sessions). This adapter
does not claim that stronger guarantee. It does not refresh tokens, accept
browser-supplied rights decisions, establish a data license or enable Save.

Focused tests exercise the actual local Auth/billing readers with synthetic
HTTP/store responses and real identity/selection validation. They are not live
Supabase, account, source-use or production proof. The required real Options
source-use policy and authenticated release remain separate gates.
