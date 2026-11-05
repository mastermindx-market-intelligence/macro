# Static scope catalogue v2 — independent bounded review

**18 October 2026 UTC · Scoped admission: qualified metadata-only catalogue use**

Root may use the exact v2 source below for the proposed `app.main` changed-path and positive-import catalogue, with candidate `797c760f3e18eb6993579f56986103de9d9fdcb4`, comparison `732cf7be88e7159b4995a8885fbd381cd1484e3e`, the actual caller-owned worktree root, and a new caller-owned external `/tmp` report path. Both defects in my original review are repaired. No new issue in the minimal delta blocks that invocation envelope.

This is admission of the bounded metadata read, not admission of first-party execution or a release. The comparison remains a previously observed live commit, not a new observation of installed or loaded production files. Native execution and its resulting catalogue have not been observed in this review.

## Exact review identities

Local bytes were independently hashed and compared with the supplied identities.

| Artifact under `release_review/` | Bytes | SHA256 |
|---|---:|---|
| `candidate_scope_static_v2.py` | 18,653 | `2f1f78e12cac9f6dfc219ba20c5d61d97bed29d4109cc9fc93eb3eea5123e103` |
| `STATIC_SCOPE_V2_REPAIR_2026-10-18.md` | 17,000 | `07c92d17df45c9a7bc1d0f5cda553041cbf55fb7d297e44cdd65b90c39717205` |
| `STATIC_SCOPE_V2_FIXTURE_RECEIPT_2026-10-18.json` | 21,725 | `8f4cdc61230430c1a38e3c181266b6bd0d715142d9ec89ec8a42213df589d34f` |
| Preserved `candidate_scope_static.py` | 16,836 | `1ccb858a4f41ee62e909cc651c64d4ecc5aa525051432b45883854f6d0216c17` |

The original findings and their limits remain recorded in `STATIC_SCOPE_CATALOGUE_REVIEW_2026-10-18.md`, SHA256 `70d3d03198f15f529ce785efd2096719f810f6261984b7aa4d9c72eb415e9c9e`.

## Repair assessment

**F1 — alias overwrite: repaired for the identified mechanism.** `loader_names` now holds a set of recognized meanings per identifier. Every recognized import adds to that set, and every interpretation is processed in deterministic order. A collision produces `recognized_loader_alias_ambiguous` with the candidate meanings. Thus an unused nested alias to `import_module` no longer deletes the outer builtin `__import__` interpretation and its literal fromlist edge. The additional ambiguity record cannot itself raise an attribute-access error for the reviewed code: only name calls can receive multiple meanings; attribute calls add at most one.

This is an intentionally broad lexical union, not Python scope analysis. It can add paths that runtime would not load. Unrecognized loaders, wrappers, rebinding, generated names, and alternate import roots can still hide paths. The revised description correctly calls the tool a partial static aid rather than a complete conservative closure.

**F2 — actual repository/output context: repaired for the identified mechanism.** `Objects.context()` obtains the absolute worktree root, per-worktree Git directory, and common Git directory through read-only `rev-parse` queries. Each must be an existing absolute directory and is resolved before use. `--repo` must equal the resolved actual worktree root. The resolved output must be outside all three directories; the previous literal `.git` component guard is also retained. This closes both the nested-directory bypass and the selected repository's separate/common metadata paths without relying on their basename.

The report records the resolved context under schema `static-python-scope-v2`. Context-query failure prevents completion. The native Git version's support for the context options remains to be observed by the actual invocation; failure is not silently treated as a successful catalogue.

The output is still created with exclusive mode after the JSON payload is prepared. This prevents overwriting the resolved target under the stated trusted-directory conditions. It is not an adversarial-filesystem race guarantee or an inventory of unrelated repositories and external object alternates. The proposed true owned worktree and new owned `/tmp` path remain the relevant caller boundary.

## Saved fixture evidence inspected

The receipt attributes its run to **2026-10-18 08:55:37.569985–08:55:38.089657 UTC**, Python 3.12.14, and a private synthetic Git fixture. I inspected the recorded source identities, arguments, return codes, output summaries, errors, context paths, and seven case results. I did not rerun the fixture or read a native repository.

| Saved control | Result recorded in receipt |
|---|---|
| Original alias collision | Child omitted and no ambiguity recorded: original defect reproduced, not an acceptance pass. |
| V2 same alias collision | Child appears in reached changed sources; both meanings appear in an explicit ambiguity record; no parser/object errors. |
| Original nested repository argument | Output created inside the actual worktree: original defect reproduced, not an acceptance pass. |
| V2 nested repository argument | Exit 2, explicit actual-root refusal, no output. |
| V2 output under separately named metadata | Exit 2, explicit metadata refusal, no output. |
| V2 linked-worktree positive control | Output created outside the repository; actual root, distinct per-worktree Git directory, and common directory recorded correctly. |
| V2 linked-worktree output under common metadata | Exit 2, explicit metadata refusal, no output. |

Attribution is **two preserved original counterexamples and five recorded v2 passes**. These are saved synthetic results, not a new independent execution, Mastermind-source result, or release test receipt.

## Required interpretation of the native result

Use all changed paths and object identities, positively reached sources, and explicit gaps to prioritize further review. Retain `parser_or_object_errors`, source parse statuses, unresolved/external imports, dynamic ambiguities, and the limitations with the result. A zero process exit or `root_resolved: true` does not establish that every reached source parsed or that the graph is complete. Source/object errors can be retained in an otherwise completed report.

The unchanged source still uses fixed object IDs, verifies read commit/blob identities, reads tracked objects without importing their Python contents, retains changed paths across both trees, and makes no checkout, provider, installer, service, or test call. The caller's trusted Python/Git runtime remains outside the graph's proof. Unreached paths, deleted predecessor modules, non-Python wiring, runtime side effects, first-party import safety, source CI, companion custody, policy applicability, and production acceptance require their own evidence.

**Review effects:** local source/document/receipt reads, hashing, and textual delta inspection only. No catalogue or fixture run, Git command, native/candidate source execution, first-party import, data access, or source edit occurred. Only this report was written.
