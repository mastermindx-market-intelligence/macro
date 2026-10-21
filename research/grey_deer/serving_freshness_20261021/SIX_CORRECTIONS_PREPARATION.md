## Current bounded refresh — 2026-10-21T19:20:25.085720+00:00

**REFRESHED_SOURCE_ONLY / DRAFT / HOLD-FOR-SOL. This section supersedes the complete-file fingerprints and source-base predicates below; the original preparation is retained as historical evidence.**

The same operation `census-mtf-six-corrections-20261021` and PR #9980 were resumed for a material source invalidator. Published signal documents changed in engine-render commits `ef728799f01e726806ea4d096dadd81152d50adb` and `71a8d1556b6803f8dde049c584c1522c885740d7`. Their six target markers, counts, primary verdicts, clocks and stale companion reasons remained unchanged. The newer trailing stops, point-in-time counters and GOOGL `above200: false` must be preserved.

Composed source base: `37e2ce7e96add3c6fa7cc3db28a1e291999f6461`. Latest observed main before composition: `2a2f4228e4ec68eaf90451b1355b588829e21c52`; all six target files plus the validator, schema, marker integrity, MTF, signal quality, ledger consumer, ledger builder and ledger blob were identical to that base. This is a standard two-parent source composition into the existing clean owned workspace, resolving only the six data-file conflicts with qualified replacements derived from the newer published bytes.

Each refreshed candidate removes exactly one 62-byte `reasons` field at the same accepted marker. All six candidates were checked before the first source write. Full parsed-document equality after that one deletion and exact byte omission checks passed. The actual `validate_ticker_doc` returned one known reason mismatch for each current original and zero errors for each refreshed candidate. The validator and schema SHA256 remain `b6a28b65747958c4e78f7735c2813b27806d7fa5b6414fd272b347be430d7a9e` and `f44f4d7b964f77f604ca591e8dab5dcf19ee314f7785bfbfd65654c6795439b9` respectively. No CLI audit writer or whole-corpus claim is involved.

| Ticker | Current published Git blob | Refreshed candidate Git blob |
|---|---|---|
| AMZN | `081c55583dc6374e2581ed773bd72711f3b76f8d` | `2106123eaf221b0eb2b46b48e7c3d2908217a00b` |
| EQIX | `7de0ebdb4acf93aa8ebfcd80ec64170d2cc724e2` | `62704cf7ea9fcb369fe55ed929e4d9cad832e65a` |
| GOOGL | `4513a767832454ff1cfb8eaab94b2305503b1456` | `217d73ffc392f04ba24ceb7e0174d56a584580ea` |
| HST | `af667bd9bd948609ef4dbc906baaa5f1a4d2c87b` | `525545ea458f5c09b82e6adbf04b382cfa820831` |
| KMI | `8a73a55f1c1e324b9d59d4ac75329b087a4ad322` | `44b20fa9251c73ac26ecb146e980e89dc8487bbf` |
| MU | `7ce19cce054cfab9e890c8b445f6ce065d75bf0f` | `b944f2fb852d22cc060ae67d861d464495c10238` |

| Ticker | Current published SHA256 | Refreshed candidate SHA256 |
|---|---|---|
| AMZN | `b9204777d710a7b1576c9aa758635f19ec6f20321f1ff83c5c2591c2e2bc8ddc` | `94d5f27e99a8a98cb90bd2c671101749c883ecbfd828ee0aab371d2716c9fc39` |
| EQIX | `06d3512612608f3eb91010544b09e7624b2620c0f88dbcb4212cc413070fe2b8` | `fc49bb9732549bc627a5efac90e47ab8c41f10d94524c21c4dcb9ebddda3f6dc` |
| GOOGL | `935e7078f4c0287027ee549b415d61077446beb635557c3c306ed8ca3a01a2a1` | `251e164ebec3e16abef1f5678f63fce0287f8af99e2a48e5aaab0613e8778075` |
| HST | `1699549afd5ca0e3f1a80bce7f5053e43a90c7d66b1112c229414f78dc529caa` | `7e2ce337b4ee192424245f6e31b8773a9e996cd491e116bf1a6405a879818ff7` |
| KMI | `42fcdb5b9dae6b7f75e63fb75eeb62bced2d501f0f53f1dc563ab415c40424a7` | `4dcd7af21f4c6e6cfa86563a56aafc1dafa7df7addc8cb46cc4ab8ebfb37ffa1` |
| MU | `f33a6bcf4dfcc7b162607c0adc2740451914af24a6cdbb259f83c47501a2b650` | `8593aecfa4f93043c7ff6f2d66ed5c19218a190dff5a263f0fc00cce6c4433fd` |

The ledger remains Git blob `1950e457e7ec34fc967b5aab96aab320d54fa89c`. No producer, ledger writer, backfill, rebuild, fit, deployment or canonical data application ran. The historical eligibility and chart/ledger disagreements below remain intact. The separate HST.last contradiction and publication fail-open paths are not repaired here.

Independent review and binding CI for the resulting new head remain pending at preparation time. The accepted old-head checks are historical, not proof for the refreshed head. The prospective prevention review on #9957 remains held on original run `mas258-mtf-published-review-20261021-01` and root `6ad8240e-707c-83ea-babc-1ceaae3669e0`; this data refresh does not replace or accept that review.

Sol retains merge authority. Keep PR #9980 Draft, without merge-on-green or native auto-merge. Release still requires separately accepted #9957 prevention, current target/dependency/ledger and canonical writer/publication sequencing, concluded binding checks, and an actual application receipt. No release or production-readiness claim follows from this refresh.

---

# Six accepted MTF explanation corrections — isolated source preparation

**PREPARED_SOURCE_ONLY / DRAFT / HOLD-FOR-SOL. Canonical main application and production publication remain pending.**

Prepared at: 2026-10-21T11:44:13.055079+00:00. Operation: `census-mtf-six-corrections-20261021`. Source base: `dcd72169ecb9ca4d761c2b7b21ea7f2156f08f56`. Original project root: `6ad8240e-707c-83ea-babc-1ceaae3669e0`.

## Scope and existing acceptance

This source candidate materializes the six exact present-day explanation corrections already accepted in [Macro #9932](https://github.com/mastermindx-market-intelligence/macro/pull/9932). Their original validation and independent C3 reconstruction receipts remain authoritative for those exact bytes. Each change removes only the stale companion `reasons` array from one unique buy marker: 62 bytes per document, 372 bytes total. The primary quality/reason, every date and clock, first-publication stamps, marker identity, and every other byte remain unchanged.

This is preparation of an isolated branch under the current user continuation, not the later canonical data application. The bounded C3 admission consultation distinguished these actions. Direct preparation uses LOWER_TOTAL_OVERHEAD: the frozen six-field omissions and fingerprint checks are smaller than a new implementation handoff. It does not replace or accept the independent implementation review of #9957.

## Exact prepared rows

| Ticker | Buy marker date | Index / count | Retained quality | Retained primary reason |
|---|---|---|---|---|
| AMZN | 2026-07-31 | 175 / 180 | block | failed next-bar hold |
| EQIX | 2026-08-13 | 149 / 151 | block | failed next-bar hold |
| GOOGL | 2026-08-26 | 132 / 134 | block | failed next-bar hold |
| HST | 2026-10-08 | 278 / 279 | take | held confirmation |
| KMI | 2026-08-31 | 107 / 109 | take | held confirmation |
| MU | 2026-09-17 | 265 / 267 | take | held confirmation |

## Before and prepared fingerprints

| Ticker | Original Git blob | Prepared Git blob |
|---|---|---|
| AMZN | `f65420895d69de6d0dc63f740b429afa6abb8f9c` | `5c21690b7de78ef56124245055690f5f3223424c` |
| EQIX | `bdcd8a5b1c508e348d385da81a9ce51918195b92` | `edcaa71fb10d3ee1bf92bff6f42ff196976d0c6f` |
| GOOGL | `9d9bb146b58693744a1b9d43e38202a9568fd2bc` | `8827462388cc1336d65e6838d0086c89741dcbd2` |
| HST | `956d047a3a5d8fc01fffa1d61b58e9af13ca53e2` | `886449e07bee3cd899e588a12c329e72b0833917` |
| KMI | `504c60f270e15b0d38dd3b84088a445182656335` | `27bd95fb7a67a5234e6896835ae3bed7d041e600` |
| MU | `7707a62cbe502fad831595d3af09dfb3af37905a` | `07cfbff9028f58bca052fd13d35081c52b2f5871` |

| Ticker | Original SHA256 | Prepared SHA256 |
|---|---|---|
| AMZN | `53448cd7760dd270e3a01ccb2d1801382989af0c6d644c817ca2afd0e8095f40` | `e98346c388d63a5bccbeceb0f75be70c42f93040e84645f0c8093deeb5d4c4f5` |
| EQIX | `ac37c7c4c69ae59e03fbacbcef39250e5ee518a240b18723e7b0e5cde4f2d7ae` | `45fe390f3ad27c518db584fdde30c6d0bbffb172dedc6b64f947ac39bc030fff` |
| GOOGL | `942232f0a3cc7e545c0b19824dba78f665a12f46f99bdf96253b2e504cd294e8` | `099bb7948c9360473fa9f6c009e81fe582bdc7859ebea77d6adc1fd4313cffd7` |
| HST | `c42df67ade9f68f5d813e9d7a53d2ec53455941f411f115361fe6d97648ddb4b` | `62224141dda4cf6a3df1ee1eeca13935af34cd489fbdcd0e593922e12a4740bc` |
| KMI | `8d216c2160a873bfa6e5b616617e9e13c176ca800dc8b25c074391f82f05f8d8` | `5dff65c034bf5835ac1c247642b04fda4448d821d90b4cb3003f2894d2b91b62` |
| MU | `5b1a369a008589d525f9c4b38d76e2561ef8c0ab1932fa96bac4808e46b8b937` | `7ab9ade09fc29fa327e24d2acdf8c86647d8a0a5fb8fb563a92230310f5851a7` |

## Fresh predicates and source custody

The canonical workspace helper admitted a new isolated, locked Web workspace at the exact observed remote-main base `dcd72169ecb9ca4d761c2b7b21ea7f2156f08f56`, returning APPLIED / reused=false. The checkpoint, scoped registered-operation read, exact-path PR search and related rotation PR path inspection found no existing six-correction source carrier. The two incumbent evidence/prevention workspaces remain separate and untouched. This is bounded custody evidence, not a claim of an exhaustive fleet-wide writer census.

The broad read-only workspace census timed out after 25 seconds because it inspects each registered worktree. A narrower underlying Git registration read completed with 936 registrations and identified only the existing evidence and prevention operations for the correction-related names. The earlier child comparison returned no usable receipt; no predicate relies on it. No active session, matching Git comparison or surviving census-helper process was observed on reconciliation.

The workspace was clean at the expected branch/base before preparation. The canonical sparse helper materialized site before the files were read or written. Native Git compared the six targets and the relevant validator/schema, signal builder, merge/quality, ledger consumer, research reader and four publication workflows against accepted pin `cd90f651ea2db5a24ca46c5ded45f7e64cdbc733`; their blobs were unchanged. The complete GitHub comparison showed six intervening main commits with unrelated source/CI changes; that does not grant whole-system publication invariance.

The populated ledger is unchanged at Git blob `1950e457e7ec34fc967b5aab96aab320d54fa89c` (prior SHA256 `b432769a33e4849cba1dda699f5bbc229a3de0eff5b1142a214c7533b789bdce`). No ledger writer, outcome selection, grader, fit, replay or rebuild ran. Its accepted populated-ledger predicates are reused because the exact blob is unchanged:

- AMZN / 2026-07-31 / buy remains absent while 73 other AMZN buy keys establish ticker history; the existing pre-era floor still refuses that absent key.
- EQIX, GOOGL, HST, KMI and MU retain their existing first-kept block/divergence ledger entries.
- HST, KMI and MU retain the explicit chart-take versus ledger-block disagreement. No ledger synchronization is part of this correction.

## Verification

Before any write, all six current complete-file SHA256 and Git blobs matched their accepted originals. Each candidate was reconstructed by one unique 62-byte omission and matched its already accepted complete-file SHA256 and Git blob. A complete parsed-document comparison confirmed that only the targeted marker reasons key disappeared. Counts, target uniqueness and all retained marker fields were checked. All six candidates were qualified in memory before the first source write; each file was read back and fingerprinted after writing.

The unchanged validator SHA256 is `b6a28b65747958c4e78f7735c2813b27806d7fa5b6414fd272b347be430d7a9e`; the unchanged schema SHA256 is `f44f4d7b964f77f604ca591e8dab5dcf19ee314f7785bfbfd65654c6795439b9`. Existing actual-validator receipts show one known error in each original document and zero in each exact candidate. Those accepted unchanged-byte results are reused; a new whole-corpus or implementation-review claim is not made. Normal source-CI evidence belongs to the resulting draft PR.

## Historical and release boundaries

The actual AMZN creating run rejected the contradiction before publication. Its rejection, recorded_at=null, dates and historical source remain intact as evidence; this present preparation does not backdate admission. The five other actual-parent transitions and later October15 validator rejection remain as recorded in #9932. Historical eligibility is not granted.

Removing the stale fields changes validator admission for these six documents. It does not repair the separate HST.last brain-leaf contradiction, prove a fresh complete MTF publication, authorize a new ledger, or establish general consumer invariance. The existing workflows can still continue after failed build/validation or use an unvalidated fallback; this candidate does not repair those publication paths.

**Sol holds merge.** Keep the correction PR Draft, without merge-on-green or native auto-merge. Release requires separately accepted prospective prevention (#9957), current target/dependency/ledger and canonical writer/publication sequencing, concluded binding checks, and an actual application receipt preserving before/after blobs and application time. A moved target, relevant dependency change, ledger reset/rebuild or real conflicting writer invalidates only the affected scope and must be reconciled before application.

No main or production data write, nightly/producer dispatch, deployment/restart, model fit, portfolio execution, policy promotion or MAS-258 completion follows from this prepared source.
