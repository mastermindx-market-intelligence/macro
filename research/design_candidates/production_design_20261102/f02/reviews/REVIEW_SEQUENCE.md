# F02 advisory review sequence

Candidate 1 source and static references were frozen at commit `6ee221069deba909b0f1eceee53869d4f4569ac9`, artifact-set SHA256 `2823e06343b79f47474657310a9301f22e25b8051e0cd168db60150d6ece97a0`. The 32-file list remains in `first-pass-artifacts.json`; its paths and hashes identify that commit, not later working versions.

Two independent native critics received the product job, before/after evidence and critical-task manifest. They did not receive author rationale or each other's review before freezing their first passes.

| Event | UTC time | Immutable evidence |
| --- | --- | --- |
| Visual Taste Critic first pass | 2026-11-03 02:04:52 | `taste-first-pass.md`, SHA256 `6a63ee8bb01d1b37634712ce2d5986ee26b04d906df647bdbb85aee225e3efc3`, BLOCK |
| Product Regression Critic first pass | 2026-11-03 02:08:11 | `product-first-pass.md`, SHA256 `dc49d84c50d250a0616079372d5e3f5508edc66acc9c634f1a5b53a8ed62051b`, BLOCK |
| Rationale revealed to both critics | after both freezes, by 2026-11-03 02:15:20 | Separate follow-up messages; SYSTEM, SOURCE/DATA, INTERACTION, VERIFICATION, CONTINUITY, README and Paper plan disclosed; peer review still excluded |

Original first-pass findings will not be rewritten. Separate rationale responses and a separately frozen repair-set review follow. Root owns implementation corrections; the component author owns static drawing changes. Neither author is counted as an independent critic.

These are native advisory reviews, not admitted Opus reviewer-class RIG receipts or design-authority approval. The Executive Fabric read returned `backend_unavailable`; admission and review execution readiness were not established. RIG remains draft.

## Candidate 2 repair sequence

The first-pass findings were committed unchanged at `71c5e0c7a59a15bf7dced5459083d3f23ea71c1f`. Product rationale pass froze at 02:20:55 UTC with SHA256 `0599244070916d53ce282551141d2e55c407e12e942da96ef2aaadb6cc41dbfe`. Taste rationale pass froze at 02:18:22 UTC with SHA256 `1b1e80990431ca337bb27ee5aeca738b0b9dbfd1205816a15c269ee1546ba8d7`. Neither withdrew a finding.

Candidate 2's 53-file repair set froze at 02:33:00 UTC and was committed at `1253a647d193e1eacd1eb6f523a7a031529d2150`. Set SHA256 is `6c1f8ba6937c620a306644764d69d7adef5672d27f6c512a080dcb35063f9ca3`. Both critics independently validated all file lengths/hashes and recomputed the aggregate. Canonical aggregate encoding is UTF-8 of the lexically sorted relative-path + NUL + lowercase SHA256 + newline for each manifest entry; the manifest excludes itself.

The Taste Critic froze its separate repair pass at 02:39:28 UTC, SHA256 `8bf57d9891d6f38aba45a3d6f840cfbd1e5211d92fcb633f432879d25671b3fd`, PASS_WITH_CONDITIONS for the bounded static reference. Original VTC-001–006 are resolved in static evidence; new minor VTC-007 requires the mobile overflow hint before the rows. That report remains unchanged. A separately frozen narrow correction and scoped follow-up will carry this remaining condition.

The Product Critic froze its candidate 2 repair report at 02:46:30 UTC, SHA256 `524c34bdac1d21a881706c8cb82187a884a49a927c55476ff17330982d6802fc`: eight original defects resolved in source/static evidence, PRC-007 open major integration gap, new minor PRC-010 density-token defect. Both candidate 2 repair reports were frozen before their two new minor findings were edited.

The narrow follow-up set froze at 02:48:47 UTC and was committed at `d68d5ecfbcd7e29094f59af3f44e7ae2a0f7f940`. Its 55-member set hash is `38b19c087b0639b728f37d015c939e7abbccf95722b72730f6f5fce84e025324`.

Taste final follow-up froze at 02:51:50 UTC, report SHA256 `feb021b733d8350a09bb9b987b16c0eed4621f86bda33004a91218c3db47701c`: VTC-007 resolved, bounded visual PASS_WITH_CONDITIONS retained. Product final follow-up froze at 02:52:53 UTC, report SHA256 `107e8c69940215809668275c9830409c711b5b764e9cc6e6742e4c0e9939ba69`: PRC-010 resolved in source policy, adoption BLOCK retained for PRC-007 and required qualification. Both independently validated all 55 members and the aggregate. All earlier reports remained unchanged.

Root's final report, return/index and PR updates add review disposition and persistence records; they do not alter any member of the final 55-file reviewed source/static/contract set.
