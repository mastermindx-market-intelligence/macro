# Explicit producer identity at the Research CLI

The generation writer accepts an explicit source commit and producer run, but
the ordinary CLI did not pass either. The CLI now requires the complete
`--generation-source-commit`, `--generation-run` and `--generation-evidence-path` set and passes them as
`generation_identity` to the existing ingest engine. Partial or invalid identity/evidence
and combinations with dry-run or materialize-only fail before opening the store.
Ordinary invocations preserve their original arguments, including when GitHub
identity environment variables are present. The existing feed workflow is unchanged.

These arguments carry caller-supplied provenance; they do not authenticate a
writer, verify the executed source, settle other writers, or authorize recovery.
The existing generation writer retains its capability, catalog, BUILDING,
conditional-write and completion checks. Before workflow adoption, the release
owner must qualify actual executed source identity, recurring run/attempt identity,
all-writer settlement and supported recovery of an interrupted original epoch.
The first adoption must not precede the recurring invocation's ability to start
from a prior COMPLETE generation. BUILDING remains closed to a successor.

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

Historical CLI-only validation before consolidation: 402 distinct affected tests passed with no remaining skips.
The two sparse-catalog cases pass after hydration of the exact committed fixture.
All 2744 indexed CI trigger closures are reachable with zero gaps. The independent
CI curation checks and hosted exact-head checks remain separate release gates.


## Original private capture and workspace

Generation invocations require a new journal outside both source checkout and public
mirror. The parent directory must already be same-user private. The journal is
mode0600, exclusive-create and locked for the invocation; failures never delete or
reuse it. A new mode0700 `<journal-name>.workspace` directory holds `corpus.sqlite`
and its restore/SQLite sidecars. Generation `--corpus` overrides and any existing
workspace file, directory or symlink are refused before store access. Legacy
invocations preserve their prior behavior. Original working files remain private
and retained after success or failure; they are not public CI artifacts.

The sink hashes only complete original append bytes after fsync and exposes the
capture digest after clean close. Partial writes, uncertain fsync or close suppress
it permanently. The CLI prints only `original_capture_sha256=<hex>`; this can bind
an original run's delivered output to its later private file, but is not source,
caller, remote-settlement or COMPLETE authority. Broken or closed output must not
replace the original ingest result, exception, KeyboardInterrupt or SystemExit.
No digest retry, later rehash or invented capture is performed.

The capture-only Fabric review was consumed and accepted after root repair of an
unguarded output notice. Ten actual-CLI cases reproduced the original error.
The reviewer inspected the actual journal and a CLI control-flow replica; later
workspace and output-error repairs were verified by the root. The review does not
claim coverage of those later changes.

PR #9311 consolidates the source originally in #9302 by attributed cherry-pick,
plus the capture and workspace integration. Both carriers were disarmed before
integration. This change activates no workflow generation flag, production writer
policy, source pin, runtime, external scope or credential.

## Consolidated validation

The final direct CLI, journal and writer suite passes 146 tests. This includes
five path-disclosure cases; three existing-workspace cases failed before repair.
The broader F3/F5-M invocation passed 1,035 tests and five subtests. Two title/SEO
failures reproduce with the exact base catalog implementation at
`0db562b2b58f518df1cdf688af73930e5bf6e9eb` and 38 unchanged loaded source/input
files. One retrieval evaluation snapshot had moved and remains explicitly skipped.
These results do not establish an all-green suite. The final CLI-only privacy
repair was checked in the 146-test group.

Both CI curation cases pass (160.26 seconds); all 2,771 indexed trigger closures
are reachable. Twelve Linux filesystem checks pass against the actual journal
source SHA256 `b645d79e7b0adfc4956d7b80203960f4057ff90238585632f8c9d684225c0278`,
including original writer-side capture, uncertain-fsync refusal and no close retry.
An earlier fixture printed a stale literal source hash; its receipt is excluded.
The accepted rerun derives the hash from the executed bytes.

Hosted checks must bind the published head. Source merge does not qualify actual
writer settlement, a producer-published generation or client acceptance.
