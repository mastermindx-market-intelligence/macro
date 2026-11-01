# Qualified finite EOD scopes

This aggregate records actual capture settlement and raw-to-Parquet-to-reader
qualification on the original Tiingo collector and external archive. It contains
counts, source identities and proof hashes; licensed market rows and credentials
remain outside GitHub.

Original operation `eod-wave9-new-unreserved-20261012-01a12ab6` settled at
2026-10-12T12:57:13.256734Z: all 5000 requests succeeded, with zero failures and
10152447 returned bars. Twelve successive completed-response snapshots verified
each raw checksum, requested date window, disjoint economic dates and nonempty
projection/reader lineage. The finite scope has 4988 nonempty histories and twelve
retained empty responses. Its actual full-scope closure reuses those accepted
proofs and performs no additional vendor calls or projection rebuilding.

The reused catalogue census after that qualification has 18246 nonempty ticker
histories, 38473553 distinct bars, 38 empty responses and 29405 uncaptured desired
windows among 47689 unambiguous US/USD stock/ETF candidates. These are bounded
catalogue and archive facts. An uncaptured window is not evidence that it was
never attempted. Current catalogue metadata does not establish historical
identity, complete delisting coverage or point-in-time research eligibility.

The following disjoint 5000-request operation started only after actual settlement
of the original capture and fresh authenticated quota, source and storage checks.
It preserves the unchanged collector, existing credentials, four in-flight
requests, five-second minimum batch starts, 24 GiB raw budget and 40 GiB free-space
floor. All sixteen known held symbols, prior reservations and existing captures
remain excluded. A further finite selection is prepared without provider calls;
it must pass actual prior settlement and fresh quota/source/storage checks before
another raw writer starts.

The pure callback helper in `lib/dataos/tiingo_capture_admission.py` removes the
slowest-request barrier for a future unlaunched finite scope. It keeps at most
four submitted, unsettled futures and records actual local admissions at the
last worker gate. Admission `i` is at least five monotonic seconds after
admission `i-4`, bounding each half-open five-second/hour window to four/2880
local admissions. A first callback exception closes the synchronized gate before
caller diagnostics; already admitted work settles and nonadmitted tasks are
distinguished from provider attempts. A five-second initial delay also preserves
the boundary with the preceding settled scope.

The existing 24 GiB raw limit remains a stop threshold, with at most four
already-admitted 512 MiB responses able to settle afterward. The caller retains
its actual 40 GiB free-space check and 5 GiB in-flight headroom. An independent
architecture review passed these exact source bytes and 22 offline regression
tests. The tests exercise rolling boundaries, a 5000-task selection, uneven
completion, simultaneous failure, delayed entry, resource/byte stops and final
accounting; credential and provider functions fail if touched. This does not
accept a future helper integration or launch. Its exact module, disjoint plan,
successful prior settlement, fresh quota/source/storage checks and canonical CI
must all be bound before use. The live collector and original prepared wave11
helper were unchanged during review. See
[`finite-admission-review.json`](finite-admission-review.json).

The closed scope contains 2499 embedded vendor split-indicator observations,
61871 dividend-indicator observations and 6377726 dates whose raw close differs
from the vendor-adjusted close. These are field observations within this retained
capture. Standalone corporate-action and dated adjustment-revision qualification
remain unestablished.

A newly captured UBFO history exercised the actually selected immutable Data &
Lab release `0b204cde`: all 6945 physical rows matched the original raw price,
volume, dividend, split, lineage and observation fields. A version-pinned 40-row
installed read around an indicator date matched the physical projection and
original raw source, preserving the current observation as the adjustment clock.
Its query receipt includes one split indicator and forty raw/adjusted close
differences. The initial descriptor failure is retained with its cause unknown;
the same selector then described the file successfully. A wide 200-row request
hit the existing response-size cap, so the actual passing read used forty rows
with all requested provenance columns and unchanged caps. Aggregate proof is in
[`price-basis-consumer.json`](price-basis-consumer.json); no price rows are published.

[`qualified-scopes.json`](qualified-scopes.json) binds each accepted finite closure
to its original plan, scope, settlement and qualification hashes. The programme
remains active. These facts grant neither canonical identity nor PIT eligibility,
deep/all-symbol fundamentals serving, BOATS production publication, Terminal
release, or responsive live consumer acceptance.
