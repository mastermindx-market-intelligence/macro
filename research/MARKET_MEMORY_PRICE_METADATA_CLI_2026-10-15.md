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

Supply the exact store ID, generation ID, generation SHA-256, and source
observation ID from the original recovered metadata export. The command must
not discover a newer generation or substitute a source when those inputs are
unavailable. The original exporter remains on its original recovery path.

The command uses the fixed private `technicals-v1` store, rechecks the installed
source grant and source bytes before reads and disclosure, and shares one
64 MiB owner-read allowance. One invocation covers one source observation.
Dates retain their session precision; the source observation clock does not
become a historical market-close or label-maturity timestamp.

Release and execution are separate: tests use explicitly synthetic retained
sources. A merged command is not evidence of an actual metadata read, complete
study admission, outcome attachment, or empirical usefulness. Actual execution
requires the recovered original pins and separately recorded acceptance.
