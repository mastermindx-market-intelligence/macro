# Yahoo Sector runtime ownership and explicit binding

Status: source preparation only; committed configuration remains **legacy**.
Mission: https://github.com/mastermindx-market-intelligence/macro/issues/10779
Governing pin: Mastermind `49c2e1d93e5e080b1671c98087a845e5beb09dd5`.

## Scope and single authority

`lib/yahoo_runtime_profile.py` owns the one fourteen-symbol Sector benchmark
constant and the narrow `yahoo.sector_runtime` configuration contract. It does
not read configuration, files, clocks, manifests or providers. Legacy and shadow
retain existing authoritative reads and writes; runtime excludes only the declared
symbols in the Yahoo group. `stocks/SPY` and other Yahoo symbols are unaffected.
Unknown or malformed declared profiles fail explicitly. Missing configuration
preserves pre-transfer legacy compatibility; a post-transfer deployment must
separately reject that absence as a downgrade.

`partition_legacy_symbols` preserves order and separates exclusions from provider
failures. Repair callers filter before cap selection, requests, retries, fallback
and attempt accounting. The six caller fences cover the normal re-pull/heal,
universe backfill, extra-symbol seeding, direct price-basis writer and shallow-cache
writer. Force does not override ownership. Direct writers assert before output
effects; shallow-cache application also checks the actual destination path so a
plan created before transfer cannot escape through its old target metadata.

The price-store freshness check still reports stale or unavailable data and exits
nonzero when healing is refused. Its receipt distinguishes a provider attempt from
runtime-owner refusal. Excluded symbols are not parked or charged a failed attempt.

## Snapshot contract

The existing publisher must verify the bytes and select the generation before
constructing `VerifiedYahooCohort`. This module is not another verifier or selector.
The injected object contains generation identity, actual source session, schema,
cohort and all fourteen frames. Binding requires both finite positive numeric price
bases, a unique ordered daily index and the same final source session for every
member. It does not prove expected exchange-session freshness or sufficient history;
the acquisition/materialization owner must qualify those before selection.

`bind_snapshot(profile, verified_cohort)` captures detached copies and pins them in
a scoped ContextVar. All `frame(symbol)` reads return detached copies, preserving
TR and price history from the same selection. Nested identical selections reuse the
binding; conflicting identity or content refuses. Exception exit resets the scope.
Independent asynchronous computations retain independent bindings. Missing bindings
fail explicitly, without a checkout or provider fallback.

This is not a claim that a frozen dataclass makes arbitrary pandas objects immutable.
Private copies are held by the binding, and callers use the detached frame method.

## Qualification

The parent recovered this bounded implementation after Fabric run
`macro-always-on-20261106-c3-yahoo-profile-01` was refused before task execution
for host temperature. The original request was not replayed or rehomed.

Focused profile/caller and incumbent backfill/regime/freshness tests returned
**122 passed, 1 skipped** on November 6. The existing pytest cleanup warnings
refer to unrelated retained temporary directories; none were deleted by this work.
Meaningful controls cover source/returned-frame mutation, conflicting selections,
asynchronous isolation, invalid/missing bases, mixed/duplicate dates, forced
repull/seeding, both backfill phases before quota selection, refused heal receipts,
direct parquet writes and stale shallow-cache plans.

## Remaining integration gates

No runtime authority is transferred by these source files. Parent integration must:

- Repair the recovered collector's intrinsic response identity, dual-basis and
  completed-calendar defects, then qualify history assembly and rebasing.
- Filter both the legacy Yahoo batch and separately rebuilt extras fallback, while
  preserving the shared downloader and the maintained-symbol audit denominator.
- Intercept `lib.store.read` before path creation and fence `upsert`; bind the
  entire computation across TR and price calls.
- Close direct and cached Yahoo reads in `engine/basket_index.py`.
- Bind a complete verified snapshot through the incumbent publisher, including
  mandatory compatibility transport where legacy readers remain.
- Drain old writers, install source barriers and anti-downgrade deployment checks,
  and prove runtime publication/consumer behavior before changing mode.

After transfer, rollback selects an earlier accepted generation under the runtime
owner. It must not silently restore legacy provider writes.
