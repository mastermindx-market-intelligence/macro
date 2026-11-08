# Private Yahoo generation publication and verified binding

Status: source integration in Macro PR10780, inactive. Base `fb84067e6fd21b2fe8fbc25351cdfa58af971f56`; mission https://github.com/mastermindx-market-intelligence/macro/issues/10779. Global Yahoo ownership remains legacy.

## Existing owners retained

`lib/yahoo_generation_contract.py` is a semantic adapter. It does not acquire, publish, select, retry, schedule or replicate data. `scripts/vps_live_orchestrator.py` remains the sole generation publisher/selector/read verifier, including locks, expected-current fencing, immutable directories, durable selection and uncertain-effect handling. `lib/yahoo_runtime_profile.py` remains the cohort, history and computation-binding owner. `collectors/yahoo.py::acquire_cycle_benchmarks` remains the provider/extraction/recovery owner.

The fixed private domain is `yahoo-sector-close-14`; fourteen `yahoo/<ticker>.parquet` members derive from `SECTOR_CLOSE_TICKERS`. No second ticker registry is introduced. The domain is separate from the five-member public Sector output generation.

## Declared acquisition evidence

`encode_yahoo_acquisition` accepts a complete accepted `CycleBenchmarkAcquisition`, an explicit prior identity, an actually observed aware preparation timestamp, and a full producer source SHA. It preserves request order as evidence while serializing members in canonical order. The prepared value is not `VerifiedYahooCohort` and conveys no publication authority.

The existing manifest's content-bound `input_identity.yahoo_cohort` contains the snapshot/cohort schemas, source session, producer SHA, preparation time, closed acquisition result, exact known/unknown clock records, prior identity and each member's name, SHA256 and full allowed lineage. There is no additional authoritative receipt file or pointer.

Prior identity is explicit: selected generation/domain/content ID and exact member hashes/lengths, or an identified bootstrap capture with source revision, capture time and explicit absent members. A date or mutable filesystem path is not enough. The producer must establish that these are the actual priors passed to acquisition; the adapter validates declared relationships, not an external capture ceremony.

Accepted lineage binds logical/vendor identities, both price bases, completed-session target, rows and first/last dates, prior presence and logical request periods. A one-month-only acquisition needs an aligned prior on both bases. Maximum-history recovery may retain a failed initial comparison; it is not required to falsely relabel that comparison aligned. Logical periods are not HTTP retry counts. Genuine absence requires a maximum-history request.

The four vendor publication/availability/session/correction clocks remain explicitly unknown. Preparation, byte capture and publication do not supply those missing upstream facts.

## Bounded private codec

The adapter writes a primitive canonical Parquet schema: one timezone-naive nanosecond `session` column, required `close` and `close_price`, optional `volume`, and existing numeric open/high/low columns when present. It rejects unknown columns instead of dropping them. Numeric columns normalize to float64; source metadata and pandas/Arrow extension metadata are excluded. Optional volume and missing observations remain absent/null, never zero-filled. Extra OHLC values are preserved; the codec does not synthesize them.

The existing shared history validator still enforces both positive finite bases, ordered unique midnight US session rows, exact common tip and at least1000 sessions. Added codec bounds are deliberate engineering constraints:50000 rows,8MiB encoded per member,32 row groups,256KiB footer and16MiB declared decoded bytes. Metadata, primitive field types and counts are checked before full value materialization. These controls are not a claim about total process RSS. No truncation occurs.

The encoder uses a metadata-free Arrow table. The decoder reads the exact captured byte buffer, disables extension reconstruction, refuses arbitrary metadata, checks page checksums when present, and reconstructs only primitive arrays. It does not invoke a source path or pandas metadata deserializer. The APIs were verified against installed PyArrow24.0.0 and the Apache Arrow ParquetFile documentation: https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html.

A read-only installed archive survey observed fourteen files with2108–8501 rows,60854–245070 encoded bytes and one row group. Existing legacy files use close_price/close/volume doubles and a pandas Date timestamp[ms] index. These fit the engineering envelope but are not themselves the new canonical codec. Evidence and individual hashes: `YAHOO_INSTALLED_ARCHIVE_SHAPES_2026-11-06.json`. The observed VPS source SHA was `4e5c79ebcfb463d8b19e4f29ce819a8423751ba2`, superseding the earlier source observation. The survey does not establish a quiesced/coherent capture or current completed-session freshness.

## Chronology and retained reuse

The adapter validates `prior capture <= evaluation <= preparation <= original publication <= current admission`. Source session must equal the existing published-calendar completed target at evaluation and original publication. New selection/reuse admission additionally requires the current completed target. Ordinary reads can retain an older valid cohort as prior history without claiming that it is current.

Preparation is content-bound. The generic validation context now exposes the actual target manifest's source revision and computed_at, including retained reuse; a newly proposed closure timestamp cannot stand in for the retained receipt. Readers reject computation/source facts that disagree with their content-bound evidence.

The orchestrator previously froze its construction clock for publication. It now keeps an explicit replay/test clock separately and passes `None` in normal operation, allowing the existing publisher to sample the actual admission clock after artifact capture. Other legacy task timing remains unchanged. A successful read or reuse never changes original publication time.

## Publication and computation path

`Orchestrator.publish_yahoo_inputs` accepts explicit encoded values and the observed current content ID. It requires an absolute state root outside the checkout and served tree, rejects symlink boundaries, validates/detaches the fixed bounded byte set and request identity before any staging effects, stages ephemeral producer sources privately with0600 files, and invokes the existing publisher through `prepare_yahoo_generation_request`. Every captured member and the final captured bundle are semantically validated. No runtime selection is made through the staging directory. A corrupt/incomplete candidate leaves the previous selection intact.

`read_verified_yahoo_cohort` invokes the incumbent verified-snapshot facade once, validates those exact returned bytes and original manifest facts, then constructs `VerifiedYahooCohort`. `VerifiedYahooGeneration.prior_identity()` describes the same captured bytes without resolving current again. IDs accepted by the private publisher, including colon/@ forms, remain intact through the next prior admission; IDs are never sanitized.

The existing `bind_snapshot` carries this verified cohort for a whole calculation, before configuration/path/cache fallbacks. Binding a parent does not bind a subprocess. Each child must read and verify one selected input before entering its own scope, or calculation must run in-process within the parent's explicit binding. This checkpoint does not wire a subprocess/bootstrap automatically.

## Proof and limitations

The focused affected run passed313 tests,88 deselected,15 existing warnings: private input contract, runtime profile, acquisition, Sector reader and generation publisher cases. Log `/tmp/mmx-yahoo-private-input-regression-20261106.log`. The identity-round-trip and pre-staging guards were added afterward. Final private-input suite:54 passed,6 existing cleanup warnings, exit0; log `/tmp/mmx-yahoo-private-input-final-20261106.log`. `git diff --check` passed. Counts overlap and are not additive.

Tests exercise real temporary publication/readback/bound store and dual-basis engine/basket reads with ambient config/path/provider calls trapped; same-session correction with a pointer changing during capture; retained original timestamps; delayed publication; metadata tampering; complete/partial/failed acquisition; max recovery; explicit absence; primitive/size/footer limits; optional volume; typed lineage/clock contradictions; private root refusals; and exception cleanup. These are controlled-provider source proofs, not production provider or beta acceptance.

Remaining: a producer that captures actual bootstrap priors or one verified previous generation, invokes acquisition and propagates the resulting explicit binding through computation; fixed-manifest R2 compatibility where legacy consumers require it; broad/member/board assembly; updater/source/drain/anti-downgrade fences; CI capability resolution; protected release and authenticated beta source-to-screen/fault acceptance. No CLI lane, timer, API mount, ownership profile or live data was activated here.


## Qualified producer, explicit bootstrap and calculation scope

Parent source continuation over `ca13f3c6afb068e1d9001b0791e73279ee3d556c`.

`Orchestrator.refresh_yahoo_inputs` executes one acquisition attempt over one
captured prior. Ordinary mode reads the incumbent selected generation once;
frames, byte hashes, lengths, prior identity and the expected-current content ID
all come from that captured object. It samples acquisition evaluation after
capture, then preparation after the provider returns. It encodes through the
existing contract and calls the sole publisher once with the original fence.
A conflicting selection does not cause a new reader, acquisition or retry.
Uncertain publication and durability are returned unchanged.

Bootstrap is explicit. `capture_yahoo_bootstrap` accepts an exact canonical
14-key mapping of absolute files or explicit absent priors. It rejects symlinked
ancestors and uses the incumbent single-descriptor bounded reader for each file.
It captures bytes and a post-read clock, never paths or loaders. Corruption,
missing files and read errors do not become absence. The raw-byte capture derives
both decoded values and their original byte identities. It does not prove that
legacy writers drained or that sequential file reads formed a quiesced cohort.
That operational admission remains a separate deployment obligation.

The bootstrap-only decoder validates one physical timestamp index declared by
pandas metadata and reconstructs selected primitive arrays. The observed legacy
`Date: timestamp[ms]` shape is supported, as are naive microsecond/nanosecond
indices; the canonical metadata-free `session: timestamp[ns]` format is unchanged.
Nested, ambiguous, duplicate, timezone-bearing and unsupported values refuse.
Original byte/footer/row/row-group/decoded-size bounds apply before materializing.
Shallow priors can be captured; acquisition must recover the full qualified history.
No sorting, deduplication, filling or malformed-archive repair occurs in decoding.

A bootstrap refresh is admitted only when selection is genuinely absent. An
existing, corrupt, unreadable, symlinked or non-directory state refuses before a
provider request. If first publication races with bootstrap, its original `None`
fence loses without replacing the winner. A valid old generation remains usable
as a prior and can advance to a fresh completed session.

`yahoo_calculation_scope` verifies one selected generation inside the process that
performs calculation and requires an explicit content ID. It enters the existing
read-only `bind_snapshot` context and restores it on success or exception. Coupled
products should run inside one scope. Each contributing child must enter its own
scope using the same captured content ID; a different selection refuses. This is
an integration seam, not a claim that all existing subprocesses are now bound.

### Producer qualification

Command: `python -m pytest -q tests/test_yahoo_generation_contract.py tests/test_yahoo_runtime_profile.py tests/test_yahoo_cycle_acquisition.py tests/test_sector_generation_reader.py tests/test_vps_live_orchestration.py -k "yahoo or generation"`

Result: **355 passed, 88 deselected, 15 warnings**, exit 0. `git diff --check` also
returned 0. Log: `/tmp/mmx-yahoo-producer-qualified-20261106.log`.

Tests exercise actual temporary publication and reader/binding, controlled real
acquisition, original legacy byte identity, malformed/absent input distinctions,
old-prior advancement, backwards/cross-session clocks, concurrent refresh and
first-publication races, unchanged uncertain-result propagation, and mismatched
child identity/context restoration. The only correction after the first expanded
run was a test's explicit expectation of canonical nanosecond index units;
production code did not change to satisfy that assertion. Counts overlap prior
contract qualification and must not be added together.

No provider request, production write, global profile flip, active schedule,
legacy-writer transfer, code deployment, API mount or authenticated beta acceptance
is claimed. Next: compose qualified broad/member/board inputs with the accepted
pure Sector functions, fence updater/legacy ownership, wire the incumbent runtime
lane and existing API, bind the Terminal consumer, then prove protected release
and source-to-screen advancement while frontend code remains unchanged.
