# Full selected-reader refresh in the existing application

The selected reader previously became unavailable after its300-second reuse
window and needed a fresh explicit prepare. Rechecking only the catalog fence
cannot renew the full receipt/derivative/corpus qualification. This source adds
an explicit full refresh on the same provider and a single application-lifetime
owner in Mastermind PR1458. Neither source increment activates a production
runtime or relaxes writer policy, source age, source identity or coverage.

The metadata census can overlap still-valid requests. Before fetching the new
corpus, refresh refuses new operations and delivery guards and waits up to five
seconds for existing owners to drain. It reserves candidate raw bytes before
acquisition and reserves candidate SQLite/image copies before opening them.
The old selection remains accounted while retained. Failure unwinds admission;
an independently valid old selection remains usable, while ordinary checks still
invalidate it on expiry, policy withdrawal or catalog movement. A successful
candidate receives another exact fence/policy/time check after SQLite parity,
then atomically replaces the selection. The reuse clock begins after that work;
the producer completion/source-age clock is not renewed.

An observed writer-policy withdrawal also invalidates an in-flight candidate,
even if the callback becomes true again before publication. A local observation
revision binds the full sweep; only a later complete sweep can replace that cut.
A causal test failed before this repair and passes afterward. This does not
detect unobserved policy transitions or replace the real writer-policy owner.
Expiration of an old reuse window alone still allows an independent refresh.

The exact existing _LimitedStore wrapper retains the qualified R2 four-member
read window. No second store, service or executor pool is constructed. The
application owns one cadence, default30seconds capped by the configured reuse
window. Request and readiness paths never initiate a refresh. Started synchronous
refresh work is shielded and drained even if shutdown or the background task is
cancelled repeatedly. The original application lifespan state is preserved, and
refresh settles before its enclosing lifespan closes. Default launcher invocation
still supplies no selected_options and enables none of this.

## Source evidence

-161provider/census/selection/read-service tests pass in the qualified Python3.12
environment;6HTTP read-runtime tests pass in the existing FastAPI environment.
The first combined run stopped at collection because the former environment
lacked FastAPI. It is not counted as a passing run.
-563MCP tests are accounted passing:562passed in the broad run and one actual
Uvicorn child-process test passed after supplying the repository import path.
The initial missing-import failure is retained. No source change was needed for
that environment correction.
-A52-file, hash-checked source overlay through the actual immutable importer,
launcher, MCP adapter and synthetic HTTP client proves expiry refuses with zero
source reads, automatic full requalification restores search, one store/service
is retained, and shutdown drains. This is synthetic data/authority with a test
archive mapping, not installed release or authenticated customer proof.
-A149,016,576-byte synthetic SQLite corpus on M2 passed active-reader drainage,
refresh and later search. Process peak RSS was639,975,424bytes under the configured
805,306,368-byte image admission. The catalog had one synthetic member and padding;
this is not a Linux production memory or full-cohort latency qualification.

Independent Fabric reviews are active on the provider and lifecycle source.
Their original retained results must be consumed and adjudicated before claiming
review acceptance. No successful process exit substitutes for that review.

## Remaining release obligations

The selected reader stays held until an actual producer-published common generation,
all-writer and delayed-effect settlement, original-owner recovery, executed pinned
producer source, actual Linux budgets, runtime installation and authenticated
C4Pro/Deep Research acceptance are proven. The observed95.60percent full-text
cohort is useful materialization evidence, not that producer-generation proof.
