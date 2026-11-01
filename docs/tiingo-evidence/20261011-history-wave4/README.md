# EOD history wave four: interrupted request and qualified partial archive

Original cap: 1,000 attempts. The initial writer retained 838 HTTP-200 responses,
then stopped on a network read timeout. The exact partial audit found 835 nonempty
and three empty captures, with 162 planned paths absent. Materialization wrote
835 new views, with zero refusals/errors. At 2026-10-11T22:38:54.032836Z, the
qualified full archive contained 4,386 nonempty EOD histories / 8,919,835 distinct
bars / 4,403 receipts, 577,610,201 physical bytes and 254.978 GiB free; reserve
remains 35 GiB. These are dated observations, not complete catalogue coverage.

Two pairs of nonempty ticker responses had identical body hashes. The existing
reader correctly refused ambiguous content selection. The verification caller
now uses the existing exact receipt selector when contexts collide; original
raw/checksum/context/row-lineage/date/economic-equality checks remain intact.
Independent review accepted that correction. No stored output or source reader
was rewritten to erase the refusal. Empty responses remain explicit receipts.

The 161 previously unattempted requests were started at 22:43:33 UTC under the
same combined 1,000-attempt cap, skipping the original failed candidate BAFE.
This checkpoint contains the bounded scope, not a completion claim. The root
attends the finite writer; no scheduler, retry queue or future wake is created.

Evidence contains request paths, checksums, counts and dates, not licensed price
rows, credentials or subscription-ID values. Capture-only retrospective views
remain PIT-ineligible; full 47,689-candidate history and dated identity are open.

Final batch observation: all 161 continuation requests succeeded in 368.882s, retaining 343,787 row hints / 80,194,781 bytes. Exact original plan audit: 996 nonempty / three empty / one absent BAFE timeout, all 999 captured body hashes verified across 4,564 scanned receipts. Materializer: 4,564 seen / 161 newly written / 4,392 existing / two RAW_ONLY / nine empty / zero refusals or errors. Full archive qualification at 2026-10-11T22:56:35.691310+00:00: 4,547 nonempty EOD histories / 9,263,622 distinct bars, 604,537,634 bytes and 255.4 GiB free (35-GiB reserve). Source was cbf2eaae with dirty registry/CI-only metadata; loaded source hashes and verifier hash are explicit. The accepted raw/reader/materializer bytes were unchanged. Original timeout/partial snapshots remain intact. No raw writer remains; no full history, canonical identity, PIT or genuine BOATS consumer acceptance is claimed.
