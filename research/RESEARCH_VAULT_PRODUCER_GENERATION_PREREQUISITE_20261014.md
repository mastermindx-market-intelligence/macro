# Research Vault producer-generation prerequisite

This source is an opt-in prerequisite for the selected F11 reader. The ordinary
CLI supplies no generation identity, and no workflow enables adoption here.
Legacy catalogs continue through the existing producer; a generation-bearing
catalog refuses an unadopted writer even when its proposed input drops that field.

An explicitly identified producer first conditionally publishes BUILDING before
covered mutable writes. Its original session owns that epoch; another run cannot
automatically take over BUILDING. Corpus publication precedes catalog visibility,
which precedes receipt flushing. Only confirmed writes drain pending receipts.
Completion reads back covered writes and measures the entire admitted cohort,
then conditionally publishes COMPLETE with the exact catalog payload, member
inventory, receipt/derivative identities and corpus hash. Below95 coverage may
be measured in COMPLETE, but the consumer independently refuses it. Completion
read failure closes the in-process writer; a successful exit is not adoption.

The census keeps at most four member tasks in flight for the exact incumbent
R2Store with its ordinarily constructed client. Each task owns one strict receipt
read and its dependent derivative read. Results and failures are consumed in
report order; started reads settle before returning. Injected, subclass and
unknown stores stay serial. The exact producer wrapper preserves the incumbent
receipt-index concurrency without granting that property to arbitrary wrappers.
No upload, publication-order, quota, source-clock, timeout or materializer-budget
policy changes are introduced.

Production run38516413232 on the preceding merged release spent133.303seconds
in receipt indexing and642.236seconds in aggregate publication, leaving zero
materializer budget and1839remaining reports. New corpus-publish, catalog-publish
and receipt-flush timing fields separate that aggregate without reordering writes.
Synthetic synchronization proves the census window and failure behavior; it is
not a real R2 latency benchmark or a claim that two complete sweeps fit15minutes.

Validation:622 affected tests and five subtests pass without skips. Four new causal tests failed before their repairs: census overlap, owned
failure-window drainage, completion refusal, and wrapper read concurrency. The two previously skipped
mirror tests pass with the exact public catalog from the branch base materialized.

Activation still requires actual all-writer and delayed-effect settlement,
production conditional-write capability, an accepted original-operation recovery
for an interrupted BUILDING, a measured successful common-generation publication,
and runtime budget qualification. The consumer's writer qualification remains
false until those conditions are evidenced. This prerequisite can land separately
from F11's held95-percent release, avoiding a circular source dependency. Original
E04/E05/citation recoveries and semantic RIO acceptance remain separate obligations.

## Bounded derivative preparation without corpus publication

The completed ordinary run at `ce99adc45881536da6ba511b287127832ca7a6ea`
spent 642 seconds in aggregate publication and entered the full-text pass after
797 seconds; its remaining wall budget was zero. The next run timed out in
publication. A read-only reconciliation retained its local candidate and observed
the prior completed cloud catalog/corpus. That observation does not settle every
possible effect of the interrupted writer and does not authorize replay.

The existing `research-ingest` workflow now offers explicit `materialize_only`.
It retains the same noncanceling concurrency group, 15-minute job limit and
incumbent materializer limits (200 attempts, 180-second pass, 600-second run wall).
It reads the published catalog with a version, restores the corpus into a private
per-invocation directory, validates SQLite and catalog membership/digests, and
uses the existing PDF/receipt-bound materializer. The store boundary permits only
create-only canonical derivative keys; catalog, corpus, receipts, PDF objects and
repository snapshots cannot be published by this mode. A catalog-version fence
runs before each creation and again at return. Existing derivatives and the
ordinary producer's retained scratch file remain intact. No writer qualification
or reader readiness follows from a successful pass.

A generation-bearing catalog refuses this preparation path: its adopted writer
must own derivative work. Forensics publication/bootstrap cannot be combined with
this mode. Missing or invalid source, missing store, moved catalog and uncertain
create responses fail the invocation without a same-pass retry. Cap and budget
exhaustion are explicit partial-pass counters, not an acceptance claim. Corpus
restore retains the incumbent version-checked range reconstruction; the mode
checks its returned image against 256 MiB after that read. That check is not a new
streaming allocation bound. Actual production resource qualification remains due.

Activation requires this source to pass protected CI/merge, reconciliation of the
original producer owner, and one dispatch through the existing workflow group.
Do not add another schedule, parallel publication writer, larger cap or timeout.
A retained result must report derivative counts and mutable publications separately.


## Selecting an installed pinned producer

The existing workflow accepts the optional repository variable
`RESEARCH_VAULT_PRODUCER_RELEASE`. Empty retains the legacy path. A nonempty value
must be exactly 64 lowercase hexadecimal characters and identify the SHA-256 of
`/Volumes/Mastermind/runtime/research-producer/releases/<digest>/manifest.json`.
Malformed values and a selected release combined with `materialize_only` refuse
in the first admission step. A selected but missing or mismatched installation,
or a failed launcher, records failure without falling back to the legacy writer.

The bundle contains `producer.json` and the staged `mastermind/` and `macro/`
source trees under their commit-named roots. The workflow verifies the bounded
manifest bytes against the selected digest before reading its strict Mastermind
commit identifier, then invokes `mastermind/<commit>/ops/research_producer/launch.py`
with the separately prepared, fixed dependency interpreter, isolated Python
flags and the original GitHub run ID and attempt. The secure producer config
binds the exact source commits, trees and manifest, the actual runner checkout
for public-safe snapshots, and private retention outside the runner cleanup
root. In particular, `producer.json.public_checkout` must equal the actual
`GITHUB_WORKSPACE` of the admitted runner: the launcher's absolute `--repo-dir`
then updates the catalog and excerpts consumed by salvage and source freshness.
The launcher already supplies `--require-store`, bootstraps its own isolated
entry, changes the child cwd to the pinned source, and keeps child stdout/stderr
in absolute private retention. Existing standalone missing-Store refusal and
actual-SDK loopback publication/mirror evidence cover those launcher contracts;
the workflow stub alone does not. Poppler is deliberately still a qualified host
dependency, and the legacy venv remains necessary for freshness/optional census.
The exact prepared interpreter is a trusted installed prerequisite, not verified
merely by the digest in its directory name. The installed entry path must be trusted before import; the manifest check
and subsequent launcher checks are not a general defense against a hostile local
administrator changing files between checks.

This wiring remains default off. Install protected source and verify the actual
runner paths and dependency environment before selecting it. All-writer and
delayed-effect settlement, conditional publication, original-run recovery and
runtime budget qualification above still govern activation. Setting a digest
would select executable producer code; neither a passing shell fixture nor a
manifest digest grants writer admission or proves publication completed. No
additional schedule, retry, process cancellation or recovery operation is added.
