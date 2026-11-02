# Prophet board/index source epochs

Operation: `prophet-a2-board-index-epoch-divergence-20261101-sol01`.
Initial source: macro/main `9fe98ab14db8ccc1bb35d9dd8b1d11617527dfdf`.
Initial census and plan checkpoint:
`6343a18748e4ce2bed5a34b2e015acdb39a5d7a7`.

## Root cause

The two artifacts have different lawful writers and different lifetimes.

1. Both express workflows invoke `scripts.build_site`.
2. `build_site.main` calls `scripts.build_stock_library.main`.
3. The library serializes and overwrites `site/factordata/us_standouts.json`.
4. The express workflows stage `site/`, publishing that board independently.
5. The nightly separately runs Prophet origination and its durable checkpoint;
   its R2 mirror follows the checkpoint.
6. `build_prophet._freeze_origination_source_board` explicitly documents that the
   board is a live product artifact with several lawful render publishers. It
   binds the index to a content-addressed immutable gzip snapshot of the exact
   source bytes.

The dashboard's plan clock displayed market/source/published dates without
distinguishing byte identity. A same-session board correction could therefore
change membership while the plan cards retained the prior origination source,
and the page did not disclose that distinction.

The post-library refresh predicate already compared a raw board hash. The defect
was not a date-only refresh condition: the board refreshed correctly, while the
reader lacked an explicit identity for the frozen index source.

The existing paid payload introduced a second consumer hazard. It is fetched
separately from the HTML shell. A stale shell could append plan/candidate rows
from a different board/index pair unless that existing hydration entry point
compares the captured source identities before any row or panel mutation.

## Committed-tree measurements

These are repository byte observations, not served-production measurements.

| Artifact at pickup | Bytes | Raw SHA-256 |
| --- | ---: | --- |
| Prophet index | 11,846,549 | `3ff270912b6522ec9edf050a606c4a302403e6f25006b7534d33971d6468d725` |
| Frozen origination board, after gzip decompression | 2,636,414 | `f4e834dc62541c21e2a9b6d5525662aabd28e6c1af12d71fe03e70fb0d046dc9` |
| Current board | 2,627,139 | `2de0cfff3d10218163bd67465e9e7e8a7ab5d5817ec7628d62b9581d2cb5db2d` |

The index's declared source hash exactly matched its durable frozen snapshot.
Both boards used market session 2026-10-30; each contained 95 buy rows, with
94 shared members. This is a membership change within one market session.
The index publication date was 2026-11-01. Friday's source date on Sunday does not
by itself establish staleness. No producer `computed_at` was present or invented.

The original [evidence comment](https://github.com/mastermindx-market-intelligence/macro/pull/10174#issuecomment-6567098234)
recorded an earlier live-board digest beginning `60a4e0e6` at immutable main
`f50fc7b7ffaff77715ff23a70c512716ab9600ac`. The pickup board had advanced again;
the frozen source hash remained the same. The census therefore reproduced the
design defect instead of relying only on the older measurements.

Commit identity was checked through Git objects:

- `5437da0bc794ca989869fe2c39bbd032ee8ca5d7`: dashboard-bot,
  “prophet-us: durable nightly checkpoint 2026-11-01”.
- `5da37c605f05e43ea4129d6e9ebd15e427e4fe53`: dashboard-bot,
  “render: site re-render 2026-11-02 (scope=all, from=a6413db0dfcc)”.
- Both checkpoint/nightly scripts last changed at
  `312d3b450da2b1017c9f8497c99d15d2e79df779`, PR #7180,
  completed-session and exact-source binding.
- The latest `build_prophet.py` change at pickup was
  `f564c0876238fe49f84f7a6a31aff6ac392ddb37`, PR #10107.

The output commits expose a temporal contract problem; they do not establish
an erroneous manual edit or browser-cache cause.

## Design decision

Keep the lawful dual epochs and make the existing reader explicit about them.
The complete rationale is in
`agentos/decisions/DEC-PROPHET-BOARD-AND-INDEX-SOURCE-EPOCHS.md`.

The normal producer remains the only index/bundle authority. An express re-render
does not re-originate plans, rewrite their ledger, or mint an accepted bundle ID.
Atomic reissue would transfer those responsibilities into the presentation lane,
which contradicts the current producer's immutable-source contract.

The new reader projection has three relations:

| Relation | Meaning |
| --- | --- |
| `SAME_SOURCE` | Current board bytes equal the verified snapshot bound to the captured index. |
| `SEPARATE_EPOCHS` | Both sources are valid and bound, but their exact raw hashes differ. |
| `UNAVAILABLE` | A required source, metadata field, canonical snapshot link, digest or parse is missing/invalid. |

Every relation has `settlement_status: PENDING`.
This projection does not evaluate A2's exact four-family source-published/read
agreement. Even equal board/snapshot hashes cannot imply SETTLED.

The existing HTML and paid payload carry the same allowlisted projection:
hashes, dates, relation, verification boolean and fixed reason codes. No names,
plans, prices, scores, source content or accepted bundle IDs are added to this
metadata. The browser requires an exact match of both source epochs before any
paid-row or panel mutation. Legitimate dual epochs can hydrate when the page and
payload agree on the pair. Missing/mixed evidence retains the preview and wall
and reports that the additional rows were held.

## Source-read guarantees

- One `read_bytes` admits the displayed plan book and captures its raw identity.
- The first board binding uses the existing raw capture before enrichment.
- The fresh-board pass recomputes its relation from the fresh raw bytes while
  retaining the captured index bytes.
- The snapshot reader accepts only the existing canonical hash-derived gzip path,
  verifies the decompressed raw hash, and never writes source artifacts.
- Snapshot loss or corruption is unavailable evidence, never an empty successful
  book or a same-date identity shortcut.
- The helper, HTML disclosure and browser fence create no additional publication
  endpoint or lifecycle owner.

## Verification boundary

Focused regressions exercise the real post-library reader/render block with
synthetic fixtures, including a same-session one-member substitution, source-byte
immutability, first/fresh consistency, path advancement after a single index read,
and rejection before hydration mutation.

The browser proof command is:

```sh
python tests/tools/prove_prophet_source_epochs_browser.py --output /tmp/prophet-epoch-proof
```

It uses an ephemeral loopback server, a fresh headless browser and synthetic rows.
It exercises the actual dashboard template and existing paid payload route across
1440/390px, dark/light and EN/ZH, plus mismatched/missing/forged-status payloads
and access denial. Its retained receipt and screenshots establish candidate
behavior only. A separate verification record will report observed outcomes;
this document does not treat a prepared test as a passing result.

## Explicit holds

No merge, auto-merge, deployment, credential/security change, private raw-data
disclosure or trade action is part of this repair. PRs #10202, #10209 and #10289
and the Y7/ModernLuxe chats are untouched. The independent non-author review and
green PR CI remain completion gates. No formal self-approval is permitted.
