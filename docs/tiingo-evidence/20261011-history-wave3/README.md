# Actual Tiingo history wave 3, 2026-10-11

The existing collector completed 1,000 new catalogue-bound HTTP 200 captures,
zero failures, 1,938,218 row hints and 440,364,083 uncompressed bytes in 2,351.934
seconds. The accepted catalogue ZIP was reused; 2,555 captured symbols were
excluded. These are acquisition identities, not canonical historical issuer IDs.

Exact request-plan SHA-256 is
`fd41f6d30d5de60d84b41bd1a848e47bd7c7888007aa8016c905f80f17e54adb`.
The audit cutoff was 2026-10-11T21:35:19.158905Z. It inspected all 3,565 source
receipts and verified all 1,000 requested response-body hashes: 1,000
RAW_RECORDS_CAPTURED, zero empty responses. The materializer inspected 3,565
receipts, wrote 1,000 views, retained 2,557 verified existing views, recorded two
RAW_ONLY and six empty products, and refused zero outputs.

The full verifier began its dated observation at 2026-10-11T21:37:28.879631Z and
completed successfully before the next raw writer began. It verified every raw
checksum, exact receipt identity and nonempty L0-to-L1 projection lineage,
retaining unique-date checks and exact economic equality for overlapping EOD
captures. The snapshot contains **3,551 nonempty EOD histories / 7,217,053
distinct bars**. Of 3,556 EOD receipts, four are empty and one repeats AMD's
verified overlapping dates. The other nine receipts are BOATS historical bars
(two), BOATS controls (two), daily fundamentals, definitions, metadata, and two
statement revision modes. Raw and adjusted prices/actions/vintages remain distinct.

Physical archive bytes were 465,839,324; observed free space was 255.615 GiB,
with the same enforced 35 GiB reserve. This is a dated observation, not a
reservation against other SSD users. The full US denominator remains 47,689
acquisition candidates; broad backfill and dated security identity remain incomplete.

Reproduction uses the original source carrier at `6eccb5aa3d3f640b8aea8dc61653bc0b4b5e9bde`
and accepted EOD logic at `bddd8da1f5c5225b258ff4d6d35ce72fca5a09fb`:
`python3 -m scripts.tiingo_materialize --max-receipts 4500`, then the retained
`audit-exact-wave.py` and `verify-archive.py` with the exact plan and archive.
Later archive reads are new observations: use distinct output files and preserve
the original cutoff and proof. No licensed rows, credentials or subscription-ID
values are in this evidence directory. All contracts remain PROPOSED, PIT false;
controls and historical minute bars do not prove live Q/T/B or overnight coverage.

Terminal #945 independently passed its protected required CI, merged at
2026-10-11T20:55:17Z, and was released through the existing VPS builder at squash
`d0973ef6e7521f775801401a345792fc7c4cb3e2`. The builder settled rc=0; VPS source,
deployment marker and public page identity agreed. Terminal and Quote Hub were
active; public ext API returned HTTP 200/no-store with null AMD/AAPL in the
closed window. Live desktop 1440, tablet 820 and mobile 390 pages loaded healthy.
Those observations prove the provenance prerequisite release, not BOATS feed
receipt/display or full programme completion. A fourth attended bounded EOD
wave has started; no recurring capture or future wake is implied.
