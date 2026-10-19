# Retained price-source metadata command

This command composes the existing private technical owner reader with the
current recorded source grant. It prepares source-date coverage for Market
Memory evaluation without decoding numerical price columns or loading feature
objects. It creates no study registration, label permission, reservation,
collector, service, or public endpoint.

The production entry point is an administrator command installed at
`/opt/macro/scripts/inspect_market_memory_price_coverage.py`. Its trust origin is
the existing authenticated host administrator and the approved deployment. UID,
path, Git, and digest checks detect inconsistent execution; they are not a new
authentication system or a defense against a compromised administrator.

Invoke the fixed script directly with the installed interpreter and `-B`:
`/opt/macro-api/.venv/bin/python -B /opt/macro/scripts/inspect_market_memory_price_coverage.py`
followed by the four immutable ID arguments. Module-mode (`python -m`) and
imported entry points are refused before private reads. The command checks the
loaded origins of its four supporting modules and its own entry point against
the installed closure. `-B` also prevents interpreter bytecode writes before
the entry point can set its own no-bytecode flag.

The deployment must be owned by the invoking root administrator, with real,
non-symlink ancestors and source directories not writable by other users.
The incumbent deployment is the trust origin; this tool detects drift from
its captured current Git HEAD, not a mistaken or malicious approved deployment.
Git qualification ignores caller `GIT_*` overrides and global/system Git
configuration, uses `/usr/bin/git`, and disables all transport protocols,
replacement objects, lazy fetch, prompts and optional locks. A root ownership
mismatch is a deployment error; do not add a wildcard `safe.directory` exception.

Supply the exact store ID, generation ID, generation SHA-256, and source
observation ID from the original recovered metadata export. The command must
not discover a newer generation or substitute a source when those inputs are
unavailable. The original exporter remains on its original recovery path.

The command uses the fixed private `technicals-v1` store, rechecks the installed
source grant and source bytes before reads and disclosure, and shares one
64 MiB owner-read allowance. One invocation covers one source observation.
Installed source-closure reads and Git provenance checks have separate bounded
per-file/output limits and run inside the same 30-second CPU and 60-second wall
deadline; they are not charged to the private-store 64 MiB allowance. Deadline
expiry remains typed through nested policy/store calls and is disarmed before
the final single JSON write. Nested metadata output uses an explicit typed
projection, so adding owner metadata fields does not automatically disclose them.
Dates retain their session precision; the source observation clock does not
become a historical market-close or label-maturity timestamp.

Release and execution are separate: tests use explicitly synthetic retained
sources. A merged command is not evidence of an actual metadata read, complete
study admission, outcome attachment, or empirical usefulness. Actual execution
requires the recovered original pins and separately recorded acceptance.
