# Explicit producer identity at the Research CLI

The generation writer accepts an explicit source commit and producer run, but
the ordinary CLI did not pass either. The CLI now accepts paired
`--generation-source-commit` and `--generation-run` arguments and passes them as
`generation_identity` to the existing ingest engine. Partial or invalid identity
and combinations with dry-run or materialize-only fail before opening the store.
Ordinary invocations preserve their original arguments, including when GitHub
identity environment variables are present. The existing feed workflow is unchanged.

These arguments carry caller-supplied provenance; they do not authenticate a
writer, verify the executed source, settle other writers, or authorize recovery.
The existing generation writer retains its capability, catalog, BUILDING,
conditional-write and completion checks. Before workflow adoption, the release
owner must qualify actual executed source identity, recurring run/attempt identity,
all-writer settlement and supported recovery of an interrupted original epoch.
The first adoption must not precede the recurring invocation's ability to continue
from COMPLETE. BUILDING remains closed to a successor.

The public catalog mirror now uses the exact projection already reviewed on
F11: only the top-level `producer_generation` block is removed. Canonical private
catalog bytes and nested catalog content remain intact; legacy bytes retain their
exact representation. Invalid JSON or encoding preserves the prior mirror.
This privacy prerequisite is lifted here because CLI adoption must not publish
private cohort hashes while the F11 reader remains behind its separate release gate.

The CLI tests bind their mock invocation to the actual engine signature, so an
incorrect keyword cannot pass by being repeated in a mock expectation. They cover
argument rejection before store access, legacy environment non-inference,
private/public separation, exact legacy bytes and failed-mirror preservation.
Tests direct snapshots exclusively to their own temporary directories.

No generation has been adopted by this source change. A completed read-only
observation found 2761 full-text members among 2888 reports (95.6025 percent),
with an unchanged catalog fence. It did not prove all-writer exclusion, a
producer-published generation or the selected corpus binding. F11's release
hold and runtime/client acceptance obligations remain in force.

Local validation: 402 distinct affected tests pass with no remaining skips.
The two sparse-catalog cases pass after hydration of the exact committed fixture.
All 2744 indexed CI trigger closures are reachable with zero gaps. The independent
CI curation checks and hosted exact-head checks remain separate release gates.
