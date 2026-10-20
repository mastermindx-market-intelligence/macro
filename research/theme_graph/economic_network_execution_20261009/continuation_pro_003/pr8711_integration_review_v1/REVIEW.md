# PR #8711 — independent integration and source-composition review

## Decision

**PASS for source compatibility. Keep candidate `9df735bbeaa8d0f4d4967296270bfb2246a5212f` frozen.** The upstream Q07 addition composes exactly with the existing Company Intelligence enrollment. No application repair, additional owner path, registry change, normal merge solely to restart CI, or repetition of the 275 application tests and five native CI tests is justified by this inspected delta.

**Hosted execution proof remains pending and is outside this verdict.** The workflow is designed to test GitHub's synthetic merge. Its eventual plan, fragments and concluded gate must actually bind the tested merge, both parents and the resulting manifest. A workflow source read, an API `mergeable` value, a path intersection or a matching manifest digest is not full CI coverage.

Root accepted that distinction during this review: preserve the candidate, require actual merged-source CI evidence, and give the concluded-CI review to the existing CI observer. No merge, fetch, checkout, native source write, test run, CI dispatch, lease operation, store action or acquisition was performed by this lane.

This review reuses the frozen observation v2 corrective PASS and the frozen prior CI-enrollment review. It does not independently certify the reviewer's earlier pure-reader implementation or reopen the retained-C01 harness.

## Exact source identities

| Identity | Value |
| --- | --- |
| PR | https://github.com/mastermindx-market-intelligence/macro/pull/8711 |
| Previous integrated main | `afbe5c4094943a9bb793d47c4953e594515a5d5c` |
| Frozen candidate and observed native HEAD | `9df735bbeaa8d0f4d4967296270bfb2246a5212f` |
| Root-fetched main reviewed here | `c4cd21d597521603fb75fe7a4602424e088c6bfa` |
| Accepted Q07 commit | `41378472e286ff6e1f441a56f0638af52d472d27`, PR #8707 |
| GitHub synthetic merge | `c852221c2bc4d8275c11c686094ccbf472f82ad9` |
| Synthetic merge first parent | `c4cd21d597521603fb75fe7a4602424e088c6bfa` |
| Synthetic merge second parent | `9df735bbeaa8d0f4d4967296270bfb2246a5212f` |
| Synthetic merge tree | `3e047aedd939f52570d696f3b9ec721e0b5eb903` |
| Current CI run observed | `37925499382`, attempt 1; `pull_request`; in progress, conclusion null |

The native workspace is `/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-observations-20261009-pro-003` on m2studio, RDC device `3f5ce987-e3eb-40a3-af9f-4b0ae54919cc`. Every Git read used `--no-lazy-fetch --no-optional-locks` and the corresponding environment controls. Root retains responsibility for any later source hydration or integration.

The GitHub PR snapshot reported 110 changed files, the exact head/base above, `mergeable: true`, and `mergeable_state: unstable`. These are observed API metadata, not merge authorization or concluded CI evidence. The raw CI run metadata reported `head_sha` equal to the PR head; that field does not override the actual checkout contract described below.

## Complete bounded intersections and native bytes

The reviewer independently compared the complete fixed-ref Git name inventory with root's 4,801-path upstream snapshot. They matched exactly. The root snapshot is 177,118 bytes, SHA-256 `30fdd42bc865958a8dfcd33729531891be694874e1c1ca2c173237f777bace7e`, observed in its document at 2026-10-09T11:43:54.951517+00:00.

| Complete sets compared | Result |
| --- | --- |
| 110 candidate-owned paths versus 4,801 upstream paths | One overlap: `.github/ci/legacy-jobs.yml` |
| 53 original native code-manifest paths versus 4,801 upstream paths | Zero overlaps |
| 110 owned paths versus 53 code-manifest paths | One common path: `engine/company_intelligence/relationship_observations.py` |
| Union of owned and code-manifest paths | 162 unique paths |

The 15 upstream paths outside `site/` and `data/` are the shared manifest, the new Q07 module and test, and 12 files under Q07's separate research directory. The remaining 4,786 paths are data/render paths. All 110 owned paths and all 53 code paths are retained in the compact evidence JSON; this report does not reproduce the 4,801-path data/render inventory.

The original code manifest is `native_validation/c01-observation-source-premerge-001.json` under the committed continuation package. It is 9,654 bytes, SHA-256 `e955ec0f462369f42b0d3689360682d1a30dcbcea63bf090d935db73b2c9d293`, and records reviewed head `6b58f15adae3b1d402d9993c52609d00083f1453`. The reviewer read all 53 entries and verified every current native file's length and SHA-256 against them. All 53 matched; no application was imported or executed.

The new application and test files were additionally compared with exact candidate Git blobs:

| File | Bytes | SHA-256 | Candidate/native relationship |
| --- | ---: | --- | --- |
| `engine/company_intelligence/relationship_observations.py` | 42,756 | `85c07b309ff7b7220ec12f2b3f25c924a2ef4c9ab495ce9030f61038cbb9e8c7` | Equal to frozen v2 and exact candidate Git bytes |
| `tests/test_company_relationship_observations.py` | 49,406 | `a73700e639c8e97a4ff84951b48358abe63b1f5048560d03b0e40f2310ac44da` | Equal to frozen v2 and exact candidate Git bytes |

These checks explain why the upstream movement does not require another native C01 execution or another application-suite run. The principal's earlier actual original-input proof remains separately attributed execution evidence, not a test performed by this reviewer.

## Q07 and Company Intelligence compose exactly

The immutable Q07 commit GET supplies the complete shared-manifest patch: **15 inserted lines, zero deletions**, introducing `quant-q07-fitted-har-vol`. It is a separate `gate: code` job with Python 3.12, dependencies `pytest pandas numpy pyarrow pyyaml scipy`, and `tests/test_vol_fitted_har.py`. It has no `scope: exclusive` or explicit `paths` declaration. This review preserves that accepted upstream choice; it does not add Q07 to the Company Intelligence owner or adjudicate Q07's statistical claims.

The Company Intelligence owner remains a distinct exclusive code job with 71 literal paths and all four suites. The Q07 insertion is near the earlier options/UK jobs, while the Company Intelligence block is at the end of the manifest. Their edits affect different job blocks.

The full upstream manifest was obtained through its immutable GitHub blob after the native object-availability refusal. A local read-only composition check verified the actual Git blob hash, parsed the manifest, substituted only the already reviewed Company Intelligence owner block, and compared the resulting Git blob hash with the manifest metadata at the actual synthetic merge.

| Manifest representation | Bytes | SHA-256 | Git blob identity, when checked |
| --- | ---: | --- | --- |
| Previous integrated main | 1,247,930 | `8754604c46e236023fab35aa6914196bc2462d9308772d406efed96c58dce7b2` | Native fixed-ref bytes |
| Frozen candidate | 1,248,094 | `3c23ea9dcc9094a10a3e5874b8281998f203227f522752d00f578820c5b9e581` | Native fixed-ref bytes |
| Fetched main, including Q07 | 1,248,517 | `749e585ad375c00a80eed545cf74c6dcc5d7f5a608338a5548301f3166eb5777` | `4014af29fc8c7b1273a8d8c3783b7ceb9d831413` |
| Q07 plus our exact owner enrollment | 1,248,681 | `e4bbeca16e38e8dd73efc2051ef0757b368afe65697f09e77b08a3a2b2746c7c` | `8b685ed536bcf1fb1600639a874b60e50f9cc148` — exactly the manifest blob at synthetic merge `c852221c...` |

The following independent inverse/equality checks passed:

- Removing exactly the Q07 insertion from fetched main restores the complete accepted `8754604c...` bytes.
- Removing it from the composed manifest restores the complete frozen candidate `3c23ea9d...` bytes.
- The parsed job inventory grows from 253 to 254 solely through `quant-q07-fitted-har-vol`.
- All 253 preexisting jobs are unchanged by Q07.
- Every job other than `company-relationship-candidates` remains equal between fetched main and the composed manifest.
- The exact Q07 job survives in the composition.
- The composed owner still has 71 paths and the original manual, pinned, review-set and new observation suites.

These full-byte inverses preserve the previously accepted QLedger additions as well as other shared-manifest work. The 254-job count is a manifest inventory; it is not a claim about selected jobs, executed packs or successful proof steps in this run.

## What the current workflow actually asks CI to prove

The workflow source at exact candidate `9df735bb...` was read from `.github/workflows/ci.yml`, Git blob `e4c42e9b27a5da7b2cd2d5729e969f05e76d7e73`. It is not among the upstream or candidate changed paths.

The relevant source contract is explicit:

- `ci-plan` checks out `github.sha` at line 4557. Its identity step checks checkout HEAD against `GITHUB_SHA`, reads exactly two merge parents, and verifies the second parent equals the event PR head at lines 4619–4649. Its plan receives the resulting tested-tree, subject-head and tested-base values.
- The direct hosted `ci-pack` branch also checks out `github.sha` at line 4911, then requires the authoritative plan's tested-tree/head/base identity when running a pack. The alternative trusted route must bind its fragments to the hosted authoritative plan; this lane has not certified which execution route ran.
- `contract-delta` independently verifies that its checkout equals `GITHUB_SHA`, reads the raw commit parents even under shallow checkout, and verifies the exact PR head at lines 5189–5211. It does not substitute a later mutable base API value for the tested merge's first parent.

The immutable GitHub commit GET confirms that the current synthetic merge `c852221c...` has exactly the reviewed `c4cd21d5...` main and `9df735bb...` candidate as its two parents. Its manifest blob equals the independently composed source above.

Therefore a normal branch merge is **not needed solely to compensate for purported head-only CI**: that premise is false for this workflow's checkout contract. The run API's PR `head_sha` does not identify the checkout tree by itself. Nevertheless source code describing the check is not evidence that a completed run passed it.

The CI observer must verify the actual run-scoped plan and fragments bind:

```text
tested_tree_sha = c852221c2bc4d8275c11c686094ccbf472f82ad9
subject_head_sha = 9df735bbeaa8d0f4d4967296270bfb2246a5212f
base_sha = c4cd21d597521603fb75fe7a4602424e088c6bfa
composed manifest SHA-256 = e4bbeca16e38e8dd73efc2051ef0757b368afe65697f09e77b08a3a2b2746c7c
```

Those identities must accompany complete plan accounting, the required owner execution and concluded authority/contract-delta results. This review deliberately makes no full-CI, plan-coverage or successful-merge claim.

## Testing and integration recommendation

Preserve the candidate and await the concluded proof already in flight. Do not add an empty commit or integrate main simply to restart it. Do not rerun the 275 application tests and five native CI tests solely because main advanced: the complete 53-code closure is unchanged, both new artifacts match frozen v2, and the shared manifest composes exactly at the actual synthetic merge.

The new Q07 job makes global selection, dependency and packing results meaningful, but those belong to the current merged-source hosted plan and differential gate. Their success must be observed, not inferred from the disjoint application paths. No new hand-written test, CI inventory edit, path broadening, curated-set change or ceiling adjustment is supported by this source review.

If concluded artifacts bind an older or different tested merge/base, if current source or manifest bytes change, or if the actual gate reports an introduced compatibility failure, root should address that concrete finding through normal integration and a narrow recheck. No such source defect was found here. Root retains all final source-freshness, release and postmerge proof responsibilities.

## Source-availability evidence and process accounting

The first native read deliberately refused to fetch missing objects. The exact `git show` of main's manifest returned 128 under the no-lazy-fetch guard; the enclosing read-only Python process exited 1. Root acknowledged the missing promised blob and retained responsibility for any later hydration. This is source-availability evidence, not an application or Q07 defect. The same missing native blob was not retried and no guard was relaxed.

Representations are kept separate:

1. Native fixed-ref tree/name reads established the census and the main manifest's Git blob identity, while native reads supplied accepted-base/candidate bytes and the 53 code pins.
2. GitHub `fetch_file` for the large main and synthetic-merge manifests returned correct blob metadata with **zero content characters**. Those responses were not treated as file bytes.
3. A raw GitHub file GET returned HTTP 400, too large or unsupported. It supplied no content proof.
4. GitHub `fetch_blob` returned the complete upstream UTF-8 manifest. Its actual byte length, SHA-256 and Git blob hash were verified locally. The composed result was compared with the separately observed synthetic-merge blob metadata.

| Native process | Purpose | Observed result |
| --- | --- | --- |
| 45802 | Fixed-ref census, then attempted main-manifest read | Wrapper exit 1; Git show exit 128 at the unavailable promised blob; failure preserved |
| 47758 | Complete census/intersection and candidate/native v2 equality | Exit 0 |
| 55330 | All 53 native code hashes, code intersection, base/candidate owner bytes and main tree entry | Exit 0 |

All three PIDs were reconciled to completion. Exact commands and source observations are in `READ_EVIDENCE.json`. No other agent's process was interfered with. Local work consisted of source-copy retention, hashing, JSON/YAML parsing and byte composition; no application module or test was imported or run.

## Frozen evidence

`COMPOSITION_RECEIPT.json` records the complete manifest inverses, all four manifest identities and parsed job preservation. `READ_EVIDENCE.json` records native commands/PIDs, the full 110-path owned set, all 53 code paths, source representations, immutable GitHub observations and bounded workflow excerpts. `OBSERVED_CODE_MANIFEST.json` preserves the source manifest representation; `Q07_MANIFEST_DELTA.diff` preserves the exact upstream insertion. The retrieved upstream manifest and native owner blocks are retained under `sources/` for reproducible local composition.

**Final scope: source compatibility PASS; actual concluded CI and release remain pending with their existing owners. STOP after this receipt freeze.**
