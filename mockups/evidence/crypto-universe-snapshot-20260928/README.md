# Crypto Market Board — one recorded snapshot

Source candidate: `31a60448e058f09b5cea4795cb4bdcfc3f7cfcba` on Macro PR #8050.
This is controlled generated-page and source-coexistence proof, not a deployed route.

## What changed

The old loader combined the latest row from every per-symbol file, even when its
rank came from a different date. In the recorded store this produced a 50-row
board containing older DARK/POLYDOGE outliers while dropping actual members of
the latest 50-asset snapshot. The new projection selects the 2026-09-26 recorded
cross-section: 50 current rows, with 17 older observations retained as exclusions.
No underlying parquet, provider value or allocation authority was changed.

The disclosure gives the recorded date, listed/requested count and reasons for
excluded observations. Missing 30-day returns are not negative breadth votes.
Histories do not silently join different source/asset identities, and deep BTC,
ETH and SOL history ends at the row's date. The existing minimum of ten assets
with sufficient accrued history remains. In this recorded snapshot only three
currently qualify after continuity checks, so the breadth result is unavailable,
not a fabricated percentage. This is not a BTC-relative or altseason measure.

## Evidence

- `scenario_receipts.json`: exact source hashes, unchanged hashes of 67 inputs,
  four generated routes and the projected coverage/breadth results.
- `browser_matrix.json`: 64 passing cells, four routes × 320/390/768/1440 × EN/ZH
  × dark/light. Checks native keyboard disclosure, retained state on language
  change, date/count/quote membership, nested geometry, 14px reading type and
  44px summary target. The empty and missing-return cases preserve other shelves.
- `manifest.json`: 32 canonical REST captures from the existing
  `scripts/capture_page_evidence.py` owner. Every content-addressed PNG was hashed.
- `snapshot-*.png`: expanded native-disclosure crops, including 320px Chinese.
- `source_merge_review.json`: exact source three-way merge with #7645 at
  `74298e32bbbbc7f00884ece259455b9bbe46fd6f`, common base
  `2b62f49603e731daf68877516d3f6f748497b160`. Zero conflicts; the combined fixture
  retains both the snapshot receipt and the peer's accessible Market Board.
- `proof_summary.json`: compact evidence and remaining network limits.

## Reproduction

Run from the same source revision with the dated input bytes identified above.
Use an isolated output directory, not `site/`. Prepare the combined template via
`git merge-file -p` using our template, the named common base and the named peer;
its digest must match `source_merge_review.json`. Then run:

```sh
python3 mockups/evidence/crypto-universe-snapshot-20260928/render_universe_snapshots.py \
  --repo "$PWD" --output "$FIXTURE_DIR" --combined-template "$COMBINED_TEMPLATE"
python3 mockups/evidence/crypto-universe-snapshot-20260928/verify_universe_snapshots.py \
  --output "$FIXTURE_DIR" --base-url "$LOOPBACK_FIXTURE_URL"
```

The browser verifier uses installed Chrome and creates no authenticated session,
review, alert or trade. Its language/theme setup waits for the existing theme
flourish to finish; it does not hide it with injected CSS.

Nine canonical repository font files were used locally and font requests had no
failures in the semantic matrix. Font files are NOT included in this evidence
folder. Favicon, live quote/overlay and one navigation-script request were absent
from the bounded fixture; those failures remain recorded. This is not a claim of
complete production chrome, live-quote, entitlement or deployment acceptance.
The existing floating Crypto Brain control remains visible and is not fixed here.
