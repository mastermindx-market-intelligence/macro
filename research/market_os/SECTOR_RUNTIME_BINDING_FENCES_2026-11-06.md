# Sector runtime read binding and legacy ownership fences

Date: 2026-11-06. Mission: [#10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779). Parent base: `2a946654f3f31cf38e5fdb90160656c6d02db6e9`.

## One existing binding owner

The existing `lib.yahoo_runtime_profile` ContextVar remains the only calculation binding. A verified cohort can be bound in an explicit shadow or runtime scope. A legacy profile cannot establish that scope. Binding validates the entire cohort, takes private copies, rejects conflicting nested identities, and restores the token on exit.

A shadow scope does not rewrite or activate the global configuration. It takes precedence for the 14 cohort members during that calculation and is read-only for those histories. Global `runtime_owns` remains true only for the runtime profile.

## Reads precede paths and caches

`store.read_runtime_history` is the common admission seam used by `store.read` and the basket compatibility reader:

1. Unrelated groups/symbols continue through their existing path.
2. A bound cohort member returns a detached frame before global configuration, directory construction, parquet access or cache access.
3. Without a binding, the current ownership profile is checked.
4. If runtime owns that member, absence of a binding raises a typed refusal; it never falls back to checkout data.
5. Unbound legacy/shadow reads retain their existing behavior.

`engine.inputs._yahoo_close` already uses `store.read`; it inherits the binding without another resolver. Both total-return and price series preserve their existing basis attributes. The verified cohort requires both price columns, so runtime reads cannot enter the legacy missing-price fallback.

`basket_index._load_member_ohlcv` resolves the runtime history before its global cache and broad fallback exception handler. Bound calculations neither consume nor populate/clear that legacy cache. The conversion retains the current Yahoo fallback convention: absent open/high/low use close and absent volume is NaN; any supplied OHLC values are preserved. This is a close-derived compatibility candle, not proof of independently observed member OHLCV. No checkout donor is spliced onto a bound history.

## Writes and legacy provider paths

`store.upsert` checks the existing profile owner before normalization, stored-history reads, quarantine, path creation or parquet writes. Global runtime ownership and a bound read-only scope both refuse writes for the cohort.

The existing partition now also recognizes bound read-only scopes. The Yahoo adapter applies it to the actual requested universe, maintained-store census and reread extras. Thus the success denominator and missing-symbol report refer to symbols still requested by that legacy owner.

The Stooq extras helper repeats that partition at its boundary. The defensive rebase entry refuses an owned symbol before basis reads or removing frames. The default downloader refuses owned symbols before its provider call/retry catch. The explicit, qualified acquisition seam retains its captured request-settings path; it is not a bypass for legacy callers.

Typed profile/ownership/binding refusals propagate through the legacy basis comparator and rebase catch. They are not converted to “unshifted” or “retry next night.” The existing collector runner classifies those specific refusals as blocked with fixed safe codes. Actual provider failures retain their existing failed/deferred behavior; no blanket expected-failure override is set.

The old nine-member availability-capture registry is unchanged. Its legacy runner omits intentionally transferred symbols from missing-observation notes. This does not create runtime availability receipts or change their original owner.

## Diagnostics preserve ownership distinctions

An unbound legacy freshness audit excludes transferred histories without reopening their parquet files. It discloses the exclusion and continues checking remaining names. Excluded symbols are not called fresh, stale, missing or delisted.

The store audit adds `excluded_runtime` only when exclusions exist, preserving the legacy result shape otherwise. A separately bound diagnostic can inspect its selected snapshot; such a diagnostic is still the existing diagnostic/writer and is not part of the pure acquisition path.

Direct historical NYSE freshness policy remains unchanged. Current runtime generation qualification continues to use the separately implemented published-calendar contract.

## Verification

The final focused run passed **283 tests**, with 15 existing pandas-deprecation/temporary-directory cleanup warnings. It covers:

- Explicit shadow binding without global activation.
- Bound store, both engine price bases and basket reads while configuration/path/parquet access is trapped.
- Missing runtime binding despite a populated stale global cache.
- Detached return values, nested/async ownership and restoration on exit.
- Write refusal before side effects.
- Initial Yahoo, period-max rebase and Stooq exclusions.
- Typed refusal propagation and safe blocked runner outcomes.
- Legacy freshness/audit and availability-capture behavior.
- Existing basis, basket-recency and circuit-breaker contracts.

Exact command and log digest are recorded in `ALWAYS_ON_ACTIVE_COMMISSIONS_2026-11-06.json`. These tests use verified-value fixtures; they are not a private production snapshot bootstrap or an authenticated beta receipt.

## Activation remains separate

The committed global profile is still legacy. Runtime activation still requires a qualified private input publisher/reader, explicit process-level binding for every admitted consumer, transfer drain and anti-downgrade rules, coherent transport, updater source recovery, producer assembly and protected release proof.

Legacy processes that need the transferred benchmarks must enter a verified binding for their whole computation, or be retired as consumers. Flipping global ownership while leaving such processes unbound will deliberately refuse their reads; it is not a complete migration. Old admitted processes must settle before transfer so cached configuration cannot preserve an obsolete writer.

Broader member OHLCV, stock/breadth panels, calibrations and non-cohort inputs remain separate explicit input obligations. This slice does not claim a common generation for them or for the entire dashboard.
