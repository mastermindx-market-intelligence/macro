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
