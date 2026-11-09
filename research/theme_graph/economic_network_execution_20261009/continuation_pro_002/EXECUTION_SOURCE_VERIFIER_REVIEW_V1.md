# Bounded review of the execution-source receipt verifier, v1

Reviewer: `/root/pure_reader_builder`  
Date: 2026-10-09  
Scope: read-only source review of `/workspace/scratch/9fd3d58c239a/lanes/continuation_package/verify_execution_source.py`  
Reviewed bytes: 10,795; 188 lines, all read  
SHA-256: `dc98893755d7d83fad29052d8c5a0800b0e2a976244aabbe592fd1f5fdbd994f`

**Verdict: REQUEST_CHANGES for two bounded P2 findings.** No other blocking logic flaw was found within the script's explicit source-byte comparison scope. This verifier was not executed. No Git operation, application import, native test, credential access, retained-source read, or source edit was performed by this reviewer.

## R1 — P2: the parsed dependency manifest is not bound to its frozen bytes

At line 101 the script reads and parses the native CI manifest directly. Lines 102–113 check the container shape, owner identity, 69 distinct literal paths, and resulting 71-path dependency union. The actual frozen manifest digest is checked later, at lines 141–146, from a separate read during source snapshots.

Those observations do not necessarily identify the same manifest bytes. A concrete source-level counterexample is:

1. The read at line 101 sees a transient manifest that keeps the owner and 69 literal distinct paths, but replaces one unchanged, unfrozen dependency such as `engine/master_brain.py` with another committed regular file such as `tests/test_ci_pack.py`.
2. The original frozen manifest is restored before line 141 snapshots it. No commit or HEAD change is needed for this sequence.
3. The substituted path is present and byte-equal in the compared commits. All 71 dependency checks can therefore pass. The restored manifest also passes its correct FROZEN digest, and the second source read and clean-tree checks can pass.
4. The resulting receipt omits the original dependency despite claiming a reviewed CI dependency census and enumerating 71 dependencies.

This sequence was derived by reading the source; no mutation or simulated verifier execution was performed. The issue concerns binding the exact value used to derive the census. The existing disclaimer about atomic filesystem custody does not bind that earlier unverified input value.

**Minimal correction:** read `manifest_bytes` once, require `sha(manifest_bytes) == FROZEN['.github/ci/legacy-jobs.yml']`, and pass those same bytes to `yaml.safe_load`. Keep the later Git/source equality check. This ties the dependency selection to the already reviewed manifest without creating a broader filesystem-isolation promise.

## R2 — P2: the declared no-fetch boundary is not enforced for Git reads

The module docstring states that the verifier never fetches. The `command`/`git` helpers at lines 46–54 and the two direct `git merge-base` calls at lines 88–90 and 128–130 do not impose a no-lazy-fetch policy. In a promisor repository, Git can retrieve a missing object while carrying out an apparent read. Thus the absence of an explicit `git fetch` command does not establish the stated operational boundary. This is relevant to the existing estate's partial-clone/object-custody behavior; the review does not claim that any fetch occurred during a run of this script.

Git's primary documentation defines `GIT_NO_LAZY_FETCH=1` to prohibit fetching missing promisor objects on demand. It separately defines `GIT_OPTIONAL_LOCKS=0` to suppress optional locked operations, including index refresh by `git status`. Source: [Git 2.53 command documentation](https://git-scm.com/docs/git/2.53.0.html), environment-variable and global-option sections, consulted 2026-10-09.

**Minimal correction:** pass an explicit environment imposing `GIT_NO_LAZY_FETCH=1` to every Git subprocess, including both direct ancestry checks. Applying `GIT_OPTIONAL_LOCKS=0` at the same shared boundary also aligns status checks with the intended read-only behavior. Missing locally retained objects should cause an explicit refusal; root retains any separately authorized fetch and custody reconciliation. The installed Git must support the selected controls. No change to source-capture or release authority is needed.

## Coherent checks and limits retained

The remaining source logic supports a narrowly described byte-comparison receipt:

- It pins the canonical workspace and reviewed commit, requires a clean tree and initial zero ignored-file census, and checks that the integrated base is an ancestor.
- It derives owned paths from the base-to-reviewed diff and restricts them to the nine frozen implementation/CI paths, the exact new decision path, and the operation's continuation research subtree.
- The accepted phase reads actual GitHub PR metadata, requires merged/closed state, the exact reviewed head and main base, records the actual merge commit, compares fetched `origin/main` with GitHub main, and requires accepted-merge ancestry.
- Each selected source file is compared as bytes against the reviewed commit and, for accepted delivery, the accepted merge and fresh upstream. Frozen implementation hashes are asserted; HEAD, worktree state, and the selected source bytes are checked again before receipt creation.
- The output uses exclusive creation in the configured principal cache and verifies written receipt bytes by readback.
- The receipt explicitly denies native fact admission, production reader custody, historical-system replay, rights admission, served-product proof, and predictive authority. It disclaims atomic filesystem/runtime custody and full third-party-runtime pinning.

The two-location premerge comparison and four logical-location accepted comparison are stated separately in `compared_locations`. A source-byte receipt does not establish an executed retained-source replay or successful CI by itself; the separately captured execution evidence must retain its own identity and outcomes. This reviewer found no additional false promotion in those fields.

This review does not reopen the six-file pure-reader implementation authored by this reviewer. It does not modify the independent review-set verdict or relabel earlier failed strict audits. Root separately reported populated AgentOS validation and three CI ownership tests passing; those execution results were not produced or independently replayed by this reviewer.

**STOP pending the exact corrected verifier bytes. The two findings were reported to root promptly; all verifier execution and edits remain root-owned.**
