# Exact-head CI plan for the scheduled-render candidate

Run **43069644153**, attempt 1, tests PR head `9cd1c665595933532a2186164deb1dce18962708` as merge `322b6281c25dbb5f127200d5c37fc8abcb6fa1c6` against main `63cd9355cb289990e7549bcbd8480089f9caa5f1`.

The canonical plan selects all **329 logical jobs in 12 packs**, with no skipped jobs. Its semantic job specifications and pack placement match the preceding plan; execution proof remains separate. The existing runner source change requires normal full-suite selection. The plan job passed. At the 17:43:20 UTC observation, all 12 packs had started on assigned GitHub-hosted runners (17:40:53-54); no terminal gate verdict existed. Existing authority/fence checks passed; the inactive pilot context remains excluded by the existing controller rule.

Original artifact 13877232259 and exact raw JSON are preserved here with hashes in `plan-receipt.json`. These are plan and started-execution receipts, not successful validation, merge, deployment or production acceptance.
