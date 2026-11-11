# Current-main render and CI adoption

This directory records integration of scheduled render `5e2f0530a7c5c95a0e461e81edac02cd1133acfa` and its timing descendant `43b5acdb0d0f264091f5aa33c129625fd0b28b8c`, followed by CI registration `82930233f83a2e62734e605becb1076508eefc31` and exact data through `54b903f7b45ddf8000a8ab432d6ac1edd63be896`.

## Qualified output

- `validation-receipt.json`: preservation, 161 template/site pairs, glossary parity/banner, full consumer scan and actual-diff UI-evidence gate pass.
- `consumer-residual-audit.json`: 15,179 HTML pages, 395 reachable assets and 457 style blocks; zero decorative residuals, missing assets or superseded references.
- `preservation-receipt.json`, `external-data-preservation.json` and `input-bindings.json`: exact data, generated-code and source preservation; approved static UI transformations are separately bound.
- `functional-asset-retention.json`: accepted Canada horizontal divider is retained after exact asset/consumer verification. The before-retention receipts preserve the mapping failure; detection was not relaxed.
- `post-validation-ci-adoption.json`: qualified site tree `6230f19afd11ec22a7d98248d3316289942ba45d` is reused exactly except five incoming published data JSON files. All presentation bytes are identical and all published data matches current main.
- `ci-accounting-resolution.json` and `ci-adoption-validation.json`: exact CI composition and source blobs; packing plus new reconnect regression tests pass (3 tests).

## Recovery and scope

The first merge attempt failed before creating a merge state because the partial clone lacked an immutable data blob. The original failure, canonical Git object hydration and same-owner retry are retained. The later adoption hydrates only exact missing Git objects after SHA-1 verification, without changing refs, repository configuration or credentials.

The merge remains under the original assigned writer. Uncommitted intermediate merges were aborted only after saving their qualified tree/evidence; the existing exact-HEAD publisher and protected-base fences remain in force. No unknown publication effect was retried. This directory does not claim new hosted CI, merge, deployment or production acceptance.
