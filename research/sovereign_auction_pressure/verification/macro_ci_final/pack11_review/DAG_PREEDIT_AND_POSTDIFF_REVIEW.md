# DAG correction: law, exact revision drift, collision census, and independent review

## Review verdict

PASS for the exact three-line existing-block move made by root in `config/dag.yml`. It is a correction to the declared execution order needed by the already-authorized auction delivery change. It adds no workflow step, scheduler, provider call, control plane, divergence exemption, or gate change. This review grants no merge or deployment authority.

Independent full-byte reconstruction from source head `9ea66297a31688123ae62845c655a74db03fa9c1` proves that the current file differs only by moving the unique existing `build_feeds` block immediately before the preceding daily-engine `check_template_site_sync_fix` block.

- Preimage SHA-256: `eaaa4d77971da6fe42fe2f77e4ec5ee2402e4667d2b5b49233c6637bd541f77e`.
- Postimage SHA-256: `6b17b12d536e62336f11557a7f28821b1aae8611f45dbf1df581f2843d350c05`.
- Size before and after: 288481 bytes.
- Existing complete build-feeds block count: one.
- Existing template-sync helper anchor count: five.
- Exact reconstructed postimage equals current file: true.
- Every other byte, including all four other helper contexts, is preserved.

Root reported that an initial broad marker-uniqueness assertion failed safely because five lanes contain that helper; the successful edit used the unique build-feeds block and its nearest exact preceding daily-engine helper. The independent byte comparison verifies the resulting edit; this worker made no source edit.

## Applicable instructions and authority

Read repository AGENTS.md and CLAUDE.md in full from saved copies whose Git blob hashes exactly match source base, source head, the observed CI base, and the supplied remote-main revision:

| File | Git blob | SHA-256 |
| --- | --- | --- |
| AGENTS.md | 367c567422f3554828f3fa57805811aa81a41df6 | 463ea7c70ea9a1ddbb5154b9f65b7c745d0093dc15485db216936fa9bddf057c |
| CLAUDE.md | 5d3c9b1936574af58581b03d149b4160119b1e79 | 3c2016ddb9a67a6488f7938e665cb5f37b767b7d39c2122057cb9d110149d329 |

Ancestor and config-directory inspection finds no additional applicable AGENTS.md or CLAUDE.md. Exact source and remote-main tree queries also find no config/AGENTS.md or config/CLAUDE.md. No CODEOWNERS file was found in the previously checked root/.github locations.

The relevant laws are:

1. Canonical remote state, rather than a stale local main ref, controls preservation. Do not alter a shared primary checkout or a sibling's work.
2. A red-pack repair identifies the exact failed job and checks current ownership/collision evidence before changing its files. Repair the cause; do not manufacture passing evidence or weaken the guard.
3. Explicit delegated source authority governs this narrow implementation correction; it does not expand into another lane or into merge, deployment, provider, or gate authority.
4. HOLD-FOR-SOL remains a merge barrier. A corrected file or passing local test is not shipped/live evidence.
5. The existing config/dag.yml meta defines the ordered workflow-step inventory; conformance is a hard comparison against actual workflow YAML.

The project memory index was searched. The two older paths named by AGENTS.md, session-finish-full-git-chain.md and auto-finish-commit-push-pr.md, are absent. The available go-live-deploy-mechanics.md was read in full under the newer repository Definition of done and the explicit mission hold. The relevant ACTIVE_BUILD_MAP search returned no direct DAG/conformance entry. These absences do not waive any repository law or broaden authorization.

## Exact supplied remote-main drift

No stale local main branch was used. All of these exact commit objects are available:

- Source base: `d2eec4732abee359ebb578b245fa7359b3c01a7d`.
- Observed CI base: `b86c4ada64533320232a98278cf199978a369a92`.
- Prior remote observation: `11e907b04d46692eced0d382a74935b19708fa2e`.
- Supplied fresh remote-main observation: `d564bd239d054e6ee6e50b1989b1f6416bcaccf9`.
- Source head: `9ea66297a31688123ae62845c655a74db03fa9c1`.

config/dag.yml has the same Git blob `68ca8883b6f09c64564f4f7904708684c3a55ee1` across source base, observed CI base, supplied fresh main, and source head. The 11e-to-d564 comparison is empty for both instruction files, DAG, daily.yml, and the daily commit helper.

daily.yml at b86 and d564 is identical, as is the commit helper. Relative to d2, that main workflow only adds the previously recorded ten Theme Graph witness lines near the regional-desk builder band. There is no upstream change around the auction feed/commit ordering and no upstream DAG delta to carry forward.

Preservation requirement: retain the full incumbent DAG and all neighboring workflows/helper semantics; apply only the declared feed-block move. The independently inspected current diff meets that requirement.

## Saved 588-PR census, extended to the new target

The original saved census scanned six bridge-related paths and did not include config/dag.yml. A new read-only path scan used the same exact recorded base/head SHAs for all 588 PRs. Saved census content SHA-256: `ea73103dcfa7d6551e83cf83d5923ee05a62c2a89c39e1d69e5da3e8965c74a2`.

- 586 exact local merge-base/path comparisons completed.
- 578 returned no DAG change.
- Eight returned a direct file overlap.
- Two could not resolve local historical objects: #8458 and #7283.

All eight overlap patches were inspected. Six were read from existing Git objects. Two missing head-file blobs (#7963 and #7193) were read through the GitHub contents API at their exact saved commit SHAs. The first ordinary historical diff read timed out; subsequent local content reads used explicit git --no-lazy-fetch. No explicit git fetch, checkout, merge, or source write was performed.

| PR | Inspected DAG change | Relation to the feed-block move |
| --- | --- | --- |
| #8563 | Communiqué Diff producer in the Asia lane | Separate lane |
| #7963 | Security State Prophet outlook refresh near the existing Prophet checkpoint | Separate upstream block |
| #7292 | Persona-memory cross-host reconciliation notes | Separate block; descriptive update |
| #7193 | China settled-close heatmap producer and freshness check in Asia | Separate lane |
| #7084 | Mineral supply, research screener, and recurring-brief declarations | Separate collection/build blocks |
| #7060 | Collection, research screener, early publication checkpoint, stockdata restore, Asia heatmap, options payoff, and recurring-brief declarations | Separate blocks; incumbent checkpoint must remain intact |
| #6861 | Capability-health projection after chronicle spine | Separate upstream block |
| #6842 | Landing-preview repair before four other template-sync helper contexts | Preserve those other helper contexts; the exact-byte check confirms preservation |

None of the eight inspected patches changes the existing build_feeds declaration. Their file overlap is not permission to overwrite their work. The root edit preserves the entire incumbent file outside its single block relocation.

For #8458 and #7283, saved connector fallback file lists contain no config/dag.yml, but their metadata says exact_head_reverified=false. They remain explicit bounded census gaps rather than absolute no-overlap proof. This is a point-in-time saved census, not proof of live custody or all later PR heads.

## Verification boundary

Root owns and is running the existing DAG checker and tests. This worker independently verified the exact diff and source preservation; it did not duplicate the test run or claim its outcome.

Existing focused commands:

```sh
python scripts/check_dag_conformance.py --verbose
python -m pytest tests/test_dag_conformance.py -q
```

## Evidence files

- independent_postdiff.raw.json: exact hashes, reconstruction equality, and full small source diff.
- preedit_exact_revision_drift.raw.json: object presence, exact blobs, and drift comparisons.
- dag_588_census.raw.json: 588-PR rescan with exact eight PR identities and two errors.
- dag_census_gap_fallbacks.raw.json: both saved fallback pathsets and their exact-head limitation.
- dag_overlap_patches.json: six complete local patches and the two initial missing-blob findings.
- dag_overlap_api_patches.json: the two complete exact-head API patches that close those blob-read gaps.
- applicable_instruction_paths.raw.json: applicable instruction-path and digest receipt.
- BRIEF.md and exact_log_excerpt.raw.json: original CI failure attribution.
