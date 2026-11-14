# US Board publisher fixture identity — November 6, 2026

This is a two-line test-fixture repair on the original PR #10432 carrier.
Natural CI42232604757 pack6/job127942893013 failed all six cases in the
temporary publisher git commit, before any retirement interceptor or assertion.
The source clone had no repository-local author/committer identity; nearby
direct-commit fixtures already establish the explicit local-identity convention.
The hosted exception exposed exit128 but did not print its captured stderr.

The unmodified published test was run with ambient Git/EMAIL variables removed,
system configuration disabled, global configuration set to /dev/null, and
user.useConfigOnly=true. Its first existing case failed at the same fixture
commit with exit128. A read-only GIT_AUTHOR_IDENT query in that exact temporary
publisher returned exit128 and Author identity unknown with auto-detection
disabled. This diagnoses the declared isolated local condition; it does not
invent the missing hosted stderr.

Two repository-local config calls are added immediately after creating that
publisher clone. The exact old published module is reproduced by removing
only those two lines. All six existing deletion-outcome cases then pass under
the same isolated identity conditions: accepted client failure, confirmed
unchanged ref, moved ref, unreadable readback after success or failure, and
malformed readback. Every retirement assertion and production helper is unchanged.

Before: one failed case, then stop. After: six passed, zero failures/skips.
These are recorded distinct phases, not an invented full-owner rerun. All
other published source/proof postimages and 135 existing untracked qualification
files remain unchanged. The qualifier index is unchanged and its branch must
not be pushed. The actual expected original branch head is
7b80bc52a850aab755e0e9ec9917b7463cccb167.

The original failed pytest log is stored as deterministic gzip, preserving its
exact diagnostic whitespace and original decoded SHA-256. The qualification
receipt and successful six-case log are unmodified actual outputs.

Earlier production-helper/custody qualification remains in
research/evidence/us_board_custody_20261106; its counts are not added to these
six rechecks. Fresh natural hosted CI, shared Business Activity/commodity
semantic disposition, current freshness and individual incumbent admission
remain separate. No merge, production publication or wider acceptance is claimed.
