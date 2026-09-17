---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: claude/agentos-fabric-fold-20260916 (worktree agentos-fabric-fold-862ecb66ee7e44b9)
model: codex
ended_because: complete
mission: >
  Fold the two Sol-adjudicated Executive-closure source children of 2026-09-17 (Mastermind #757 symlink ACL
  observation, Mastermind #758 Reader static-fence exception) and their two supporting discoveries into
  Agent OS company memory through the EXISTING fold carrier branch — one records-only descendant commit, no
  push, no PR edit, no new carrier, no second records writer. Six `agentos/` paths only.
state_before: >
  The carrier branch claude/agentos-fabric-fold-20260916 sat at 0c9b8281271f64fa958a03ce86824b246cdaa1f5
  with a clean worktree, holding PR #7223 (OPEN / DRAFT / HOLD-FOR-SOL, title "agentos: post-#7181 fabric
  fold (stable items) — HOLD-FOR-SOL"). WS:EXECUTIVE-CAPACITY-FABRIC carried status `active` and a
  next_action pinned to protected Mastermind master 4537f066775c73d305f82acf0643701f01f5e53c, both of which
  the 2026-09-16 fold had written. Two Mastermind children had terminated today with Sol adjudications that
  existed only inside their own sessions: #757 at f079f1ee14003dbcc12cfe7154c90c713eac3373 (ACCEPTED/STOP at
  edge 1789648278.066969, DRAFT-HOLD, BUILT_NOT_PROVEN) and #758 at
  55800d57f42f73a6c093e1432da16b78e3d2ab83 (RESULT/HOLD posted at edge 1789649544.225129, awaiting Sol's
  ruling). No Agent OS record mentioned either child, the installer manifest regression, or the kit-lane gate
  limit.
changed:
  - path: agentos/discoveries/DSC-INSTALLER-MANIFEST-REFUSES-TRACKED-SYMLINKS-SINCE-583.md
    what: >
      New discovery: every Executive OS release manifest CREATE fails on a release tree containing the
      tracked symlink `vendor/macro`, because the manifest walk asks the shared macOS ACL observer
      path-only and the observer opens with `O_NOFOLLOW` and refuses non-file/non-directory objects. Carries
      both admission gates: the falsifier is a protected-master manifest CREATE succeeding with
      `vendor/macro` present, and the so_what keeps the installed control/relay on healthy release 4c148709
      (AWAITING_CANARY, armed=false) unrestarted until #757 lands.
  - path: agentos/decisions/DEC-SYMLINK-ACL-OBSERVATION-IS-MANIFEST-ONLY-OPT-IN.md
    what: >
      New decision: the Sol-amended symlink ACL observation contract. Default path-only `has_macos_acl`
      unchanged; one keyword-only `allow_symlink=False` opt-in requiring a caller-supplied `os.stat_result`
      whose `st_mode` is `S_ISLNK`, rejecting a caller-supplied `descriptor`, requiring native nonzero `int`
      `os.O_SYMLINK` with no fallback, opening exactly
      `O_RDONLY | O_SYMLINK | O_CLOEXEC | O_NONBLOCK`, re-proving identity via `fstat` and requiring the
      observed object to be `S_ISLNK`; only `release_manifest._has_acl(path, info)` opts in. Four
      alternatives rejected (global symlink acceptance; a new public helper — closed duplicate PR #748;
      zero-`O_SYMLINK` fallback; fresh-`lstat` fallback), plus the ancestry-only rebase churn.
  - path: agentos/decisions/DEC-READER-FENCE-EXCEPTION-IS-AN-EXACT-IMPORTER-MODULE-MAP.md
    what: >
      New decision: how the CEO-accepted Steward Live Window composition coexists with the Reader static
      fence. `EXTERNAL_IMPORTER_EXCEPTIONS` is an exact importer->module map naming the two importer files,
      each allowed to import `owner_read_resource` ONLY — never `live_window_read`; the module set,
      `allowed_roots` and the other two fences unchanged. Rejects the package `__init__` re-export, the
      dynamic import, a package-wide Steward allowance, and a second seam module, and records the
      pre-existing AST-fence blindness to package-form and `importlib` imports as awareness only.
  - path: agentos/discoveries/DSC-FULL-MASTERMIND-GATE-CANNOT-RUN-INSIDE-A-KIT-LANE.md
    what: >
      New discovery: the full Mastermind gate `python scripts/ci_pytest.py` (632 modules) cannot complete
      inside a kit worker lane on the Mac Studio — lane venv missing fastapi/claude_agent_sdk/reportlab/lib
      (17 collection errors), `vendor/macro` dangling in the lane while hosted CI materialises macro
      256c757b3c4f0ec759571c29a30a71387d0a18f8 sparsely, and a lane cap killing a run at 18% (1471 s).
      Carries the falsifier (a kit lane completing the gate green inside its cap) and the so_what (lanes
      report RED/GREEN, focused suites and compileall; the hosted required `test` check is the real gate).
      Confidence `probable`, with the reason stated in the body.
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-17.md
    what: >
      This handoff. Names the parent commit, the carrier branch and PR #7223, the four folded records, the
      program state, the standing do_not_redo set and the danger areas, and the exact continuation actions
      for a stranger with no access to this session.
  - path: agentos/workstreams/WS-EXECUTIVE-CAPACITY-FABRIC.md
    what: >
      Wave-boundary update to two frontmatter fields only. `status` moves from `active` to `awaiting_review`
      (the principal path now waits on two Sol acts: a ruling on the #758 RESULT/HOLD and the
      maintenance-only merge of #757). `next_action` is replaced with a 2026-09-17 update that re-pins
      protected Mastermind master from 4537f066775c73d305f82acf0643701f01f5e53c to
      e878878c9a4ae2dd50a48d825e031e07e8211708 (fast-forward, ahead 11 / behind 0), cites all four new
      records in colon form, states the installer lane's source-gate block and the do-not-restart rule for
      release 4c148709, and points at this handoff plus the 2026-09-16 POST-7181 fold for the per-carrier
      detail it deliberately does not restate. The record's `decisions`/`discoveries` arrays were NOT
      extended: the fold's edit scope permitted only `status`/`next_action`, so the machine edges live in
      this handoff's own `decisions`/`discoveries` arrays.
verified:
  - claim: "Preflight: the session worktree was on the expected carrier commit, on the expected branch, with an empty porcelain status."
    command: "git rev-parse HEAD; git rev-parse --abbrev-ref HEAD; git status --porcelain"
    result: "HEAD 0c9b8281271f64fa958a03ce86824b246cdaa1f5; branch claude/agentos-fabric-fold-20260916; status empty."
  - claim: "Protected Mastermind master is e878878c9a4ae2dd50a48d825e031e07e8211708, 11 commits ahead of the 4537f066775c73d305f82acf0643701f01f5e53c pin the 2026-09-16 fold wrote and 0 behind."
    command: "git ls-remote https://github.com/mastermindx-market-intelligence/Mastermind refs/heads/master; gh api repos/mastermindx-market-intelligence/Mastermind/compare/4537f066775c73d305f82acf0643701f01f5e53c...e878878c9a4ae2dd50a48d825e031e07e8211708 --jq '{status,ahead_by,behind_by}'"
    result: "refs/heads/master = e878878c9a4ae2dd50a48d825e031e07e8211708; compare = {status: ahead, ahead_by: 11, behind_by: 0}."
  - claim: "`vendor/macro` is a tracked symlink to `macro_src` at protected master and at #583's merge, so any release tree cut from it contains the object that trips the ACL walk."
    command: "gh api repos/mastermindx-market-intelligence/Mastermind/contents/vendor/macro?ref=e878878c9a4ae2dd50a48d825e031e07e8211708 --jq '{type,target,size,sha}'; gh api repos/mastermindx-market-intelligence/Mastermind/contents/vendor/macro?ref=7868e2c2727a8871f64f387de9ce00dc6a67cff9 --jq '{type,target}'"
    result: "e878878c: {type: symlink, target: macro_src, size: 9, sha: 67c7d1aa15e255af2e662d8b4b385faf9714f06a}; 7868e2c2 (#583 merge): {type: symlink, target: macro_src}."
  - claim: "At protected master, the release manifest walks every object and calls the shared observer path-only from `_has_acl`, and the shared observer opens with `O_NOFOLLOW` and refuses non-file/non-directory objects."
    command: "gh api -H 'Accept: application/vnd.github.raw' repos/mastermindx-market-intelligence/Mastermind/contents/ops/executive_os/release_manifest.py?ref=e878878c9a4ae2dd50a48d825e031e07e8211708 | grep -n 'has_macos_acl\\|_has_acl\\|def _entries'; gh api -H 'Accept: application/vnd.github.raw' repos/mastermindx-market-intelligence/Mastermind/contents/control_plane/fs_security.py?ref=e878878c9a4ae2dd50a48d825e031e07e8211708 | grep -n 'O_NOFOLLOW\\|def has_macos_acl\\|S_ISREG\\|not a file or directory'"
    result: "release_manifest.py: :19 import, :29-33 `_has_acl` -> `has_macos_acl(path)`, :65 `def _entries`, :80 `if _has_acl(path):` inside the walk. fs_security.py: :63 `def has_macos_acl`, O_NOFOLLOW in the flags, and the typed refusal `macOS ACL object is not a file or directory` for a non-regular/non-directory opened object."
  - claim: "Mastermind #757 is OPEN/DRAFT at f079f1ee14003dbcc12cfe7154c90c713eac3373 with no merge commit, and its head carries the opt-in contract this fold records."
    command: "gh pr view 757 -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid,mergeCommit,title; gh api -H 'Accept: application/vnd.github.raw' repos/.../contents/control_plane/fs_security.py?ref=f079f1ee... | grep -n 'allow_symlink\\|O_SYMLINK\\|S_ISLNK\\|descriptor'; gh api -H 'Accept: application/vnd.github.raw' repos/.../contents/ops/executive_os/release_manifest.py?ref=f079f1ee... | grep -n 'def _has_acl\\|_has_acl(\\|allow_symlink'"
    result: "state OPEN, isDraft true, headRefOid f079f1ee14003dbcc12cfe7154c90c713eac3373, mergeCommit null. fs_security.py: `allow_symlink: bool = False` at :68, typed refusals at :105-119 before the Darwin gate at :122, `O_SYMLINK` nonzero-int checks at :137-145, symlink flags at :147-152 versus default O_NOFOLLOW flags at :154-159. release_manifest.py: `_has_acl(path, info)` at :30, `allow_symlink=stat.S_ISLNK(info.st_mode)` at :35, call sites :56, :82, :162."
  - claim: "Mastermind #758 is OPEN/DRAFT at 55800d57f42f73a6c093e1432da16b78e3d2ab83 with no merge commit, and its head carries the exact importer->module exception map with the fenced module set and allowed_roots otherwise intact."
    command: "gh pr view 758 -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid,mergeCommit,title; gh api -H 'Accept: application/vnd.github.raw' repos/.../contents/tests/test_mastermind_window_reader_static_fences.py?ref=55800d57..."
    result: "state OPEN, isDraft true, headRefOid 55800d57f42f73a6c093e1432da16b78e3d2ab83, mergeCommit null. Fence file: `EXTERNAL_IMPORTER_EXCEPTIONS` at :31-38 with exactly the two importer paths, each mapped to the single-element frozenset `{integrations.mastermind_window_reader.owner_read_resource}`; `modules` at :42-45 still contains both `live_window_read` and `owner_read_resource`; `allowed_roots` at :48-51 unchanged; the exception applies only after the package/test root check."
  - claim: "The kit-lane discovery's two externally checkable anchors exist: Mastermind's gate entry point at protected master, and the macro commit hosted CI checks out."
    command: "gh api repos/mastermindx-market-intelligence/Mastermind/contents/scripts/ci_pytest.py?ref=e878878c9a4ae2dd50a48d825e031e07e8211708 --jq '{path,type,size}'; gh api repos/mastermindx-market-intelligence/macro/commits/256c757b --jq '{sha,date:.commit.committer.date}'"
    result: "scripts/ci_pytest.py = {path: scripts/ci_pytest.py, type: file, size: 16904}; macro 256c757b = {sha: 256c757b3c4f0ec759571c29a30a71387d0a18f8, date: 2026-08-09T09:02:07Z}."
  - claim: "PR #7223 is OPEN / isDraft true on this branch with its head still at this fold's parent commit, so this commit is a plain descendant of the reviewed carrier."
    command: "gh pr view 7223 -R mastermindx-market-intelligence/macro --json state,isDraft,headRefName,headRefOid,title"
    result: "state OPEN, isDraft true, headRefName claude/agentos-fabric-fold-20260916, headRefOid 0c9b8281271f64fa958a03ce86824b246cdaa1f5, title 'agentos: post-#7181 fabric fold (stable items) — HOLD-FOR-SOL'."
  - claim: "The Agent OS store validates clean after the fold."
    command: "python3 scripts/agentos.py validate"
    result: "rc 0 (see the FILES/VALIDATE section of the lane record agentos_fold_record.md for the full output)."
  - claim: "Exactly one commit was created, it touches only the six owned agentos paths, and the worktree is clean afterwards."
    command: "git diff --stat HEAD~1 HEAD; git log -1 --format='%s'; git status --porcelain"
    result: "Six agentos paths changed; the subject starts 'agentos: fold 2026-09-17 installer symlink-ACL repair + Reader fence exception (Sol-adjudicated children)' and the message ends with the Co-Authored-By trailer; porcelain empty."
unverified:
  - claim: "The live installer failure at 2026-09-17T07:21Z and the root RED proof (protected e878878c release_manifest+fs_security over a clean `git archive` export, rc=1)."
    what_would_verify: "Re-run the release-manifest CREATE on a clean export of the then-current protected master and read the exit code, stderr and any produced manifest; this fold re-read the code path and the symlink, not the ceremony."
  - claim: "The Sol root edges 1789644071.495499 (#758 scope request), 1789645665.697889 (#757 candidate return), 1789649544.225129 (#758 RESULT/HOLD), 1789648278.066969 (#757 ACCEPTED/STOP) and 1789644750.659619 (#758 scope ruling), and the Slack-side dispositions they carry."
    what_would_verify: "Read those edges on the root/Slack surface, or Sol's durable comment. This session had no Slack surface and the records worktree can only carry them as child-session receipts."
  - claim: "The child-session hosted run ids 35215011646 (#757) and 35221207639 (#758), the patch sha256 e6faf8d6b505304a…, the review-record sha256s 6bbb8c6115afa812… and bc2d3a054d6b5797…, the GREEN manifest sha256 049025007eeef3c0… with 2266 entries, and the mutants M1-M4 kill list."
    what_would_verify: "`gh api repos/mastermindx-market-intelligence/Mastermind/actions/runs/<id>` for each run, and the child sessions' kit receipts for the patch and review records."
  - claim: "The kit-lane failure facts: 17 collection errors from the lane venv, a lane-cap kill at 18% / 1471 s, a silently-dead writer lane, and the dangling `vendor/macro` inside the lane."
    what_would_verify: "Run `python3 scripts/ci_pytest.py` in a kit worker lane on the Mac Studio and read the exit code, elapsed wall time, and the missing-distribution list; or inspect the lane's preserved log if it survives."
  - claim: "The installed control/relay release 4c148709 is AWAITING_CANARY with armed=false, and it is healthy."
    what_would_verify: "Read the installed host's release pointer and armed state as root. This fold touched no host and ran no service command."
  - claim: "The carried-over state of the other waves (W1-H3 #677 head and its R80/R14 chain, CF2-H0 carrier-proof requirements, OCR-2C Family A/B state, PF1 and the MH1 holders)."
    what_would_verify: "Re-read the 2026-09-16 POST-7181 fold and this record's per-wave next_action entries, then re-read each live head with `gh pr view <n> -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid` before acting."
unresolved:
  - "Sol's ruling on the #758 RESULT/HOLD (edge 1789649544.225129) has not been consumed; #758 stays DRAFT/HOLD-FOR-SOL."
  - "Mastermind #757 awaits Sol's maintenance-only merge; the post-fix install ceremony is NOT authorized before that merge, and no install retry is permitted."
  - "Gate B / arm still wait on the Chairman-owned CREDENTIAL_EXPIRES_AT as a readiness input; it must never be guessed or inspected."
  - "The Reader static fence remains blind to package-form and `importlib` imports (pre-existing, neither widened nor repaired by #758)."
next_actions:
  - "Consume Sol's ruling on the #758 RESULT/HOLD directly, without re-running or re-posting anything on that carrier."
  - "On Sol's maintenance merge of #757, run the staged post-fix install ceremony on the NEW protected SHA as a separately reported effect, with its own receipt — not as a continuation of the source child."
  - "Leave Gate B and the arm step waiting on CREDENTIAL_EXPIRES_AT; do not restart release 4c148709 (AWAITING_CANARY, armed=false) to test anything."
  - "Re-read the carrier branch and this handoff before every act or post, since the seat pushes this branch after a freshness read and the parent commit may already be superseded."
do_not_redo:
  - "Never restart the healthy 4c148709 control/relay, and never run an install retry or ceremony before Sol's maintenance merge of #757."
  - "`CREDENTIAL_EXPIRES_AT` is a Chairman-owned readiness input: never guess it, never inspect credentials to derive it."
  - "JOB-001 / JOB-002 / JOB-003 are admission-only and are never the execution canary."
  - "#665 release authority is CHAIRMAN_ONLY."
  - "#653, #710, #716, #725 and PF1 keep their current holders; do not re-mint or take over their lanes."
  - "No courtesy ACKs and no polling loops; re-read the carrier before every act or post."
  - "Never re-open the closed PR #748 by copying its bytes: the manifest-only opt-in supersedes that approach."
  - "Do not treat the destroyed lane's silence as evidence about its source: the patch survived and the lane's failure was environmental."
danger_areas:
  - "A release tree is not a source tree: `vendor/macro` is a tracked symlink, and any ACL/identity/ownership walk that assumes files and directories will refuse it. A manifest gate that fails is fail-closed — do not bypass it by relaxing the observer's default."
  - "The shared `has_macos_acl` is a security default used far beyond the manifest. Widening it globally, or adding a second public symlink helper, would trade a fleet-wide property for one call site."
  - "Adding another allowance to `EXTERNAL_IMPORTER_EXCEPTIONS` is a security/architecture act, not a test fix: the map's whole value is that each entry is one named file and one named module."
  - "A kit lane is not a real-gate environment. Its green is not acceptance, its red may be environmental, and a killed lane can look like a passing quiet. Use the hosted required `test` check for the repository verdict."
  - "`agentos/handoffs/` requires clean quoting: the validator reads a bare `WS:`/`DEC:`/`DSC:`-prefixed key as machine truth only when it is prefixed, and rejects empty `verified[].command` values."
  - "The two generated views `docs/AGENT_OS_STATE.md` and `data/governance/agent_os_state.json` are nightly-regenerated; hand-editing them creates a conflict site on a shared file."
prs:
  - 7223
decisions:
  - DEC:SYMLINK-ACL-OBSERVATION-IS-MANIFEST-ONLY-OPT-IN
  - DEC:READER-FENCE-EXCEPTION-IS-AN-EXACT-IMPORTER-MODULE-MAP
discoveries:
  - DSC:INSTALLER-MANIFEST-REFUSES-TRACKED-SYMLINKS-SINCE-583
  - DSC:FULL-MASTERMIND-GATE-CANNOT-RUN-INSIDE-A-KIT-LANE
---

## What this fold is

Records only. One descendant commit on the existing carrier branch
`claude/agentos-fabric-fold-20260916`, on top of `0c9b8281271f64fa958a03ce86824b246cdaa1f5`, holding PR
#7223 (OPEN / DRAFT / HOLD-FOR-SOL). No push, no PR edit, no label, no GitHub or Slack write, no install
ceremony, no host change, no other worktree touched. The seat pushes after a carrier freshness read.

## The four records

| Record | One line |
|---|---|
| `DSC:INSTALLER-MANIFEST-REFUSES-TRACKED-SYMLINKS-SINCE-583` | Every release manifest CREATE fails on a tree containing the tracked symlink `vendor/macro`, because the walk asks the shared ACL observer path-only and the observer refuses symlinks. |
| `DEC:SYMLINK-ACL-OBSERVATION-IS-MANIFEST-ONLY-OPT-IN` | The default observer stays path-only; one keyword-only `allow_symlink=False` opt-in, gated on a caller-supplied `os.stat_result`, native `O_SYMLINK`, identity re-proof and observed link-ness, is used by exactly one call site. |
| `DEC:READER-FENCE-EXCEPTION-IS-AN-EXACT-IMPORTER-MODULE-MAP` | The Reader static fence gains an exact importer->module map for two named importer files, each permitted `owner_read_resource` only. |
| `DSC:FULL-MASTERMIND-GATE-CANNOT-RUN-INSIDE-A-KIT-LANE` | A kit worker lane cannot run the full Mastermind gate; lanes report focused evidence and let the hosted required `test` check be the real verifier. |

## Carrier and program state at this fold

- Protected Mastermind master: `e878878c9a4ae2dd50a48d825e031e07e8211708`, read 2026-09-17.
- Mastermind #757 (symlink ACL repair): OPEN / DRAFT / HOLD-FOR-SOL at
  `f079f1ee14003dbcc12cfe7154c90c713eac3373`, Sol ACCEPTED/STOP at edge `1789648278.066969`,
  BUILT_NOT_PROVEN, merge is a Sol maintenance-only act.
- Mastermind #758 (Reader fence exception): OPEN / DRAFT / HOLD-FOR-SOL at
  `55800d57f42f73a6c093e1432da16b78e3d2ab83`, Sol scope ruling edge `1789644750.659619`, RESULT/HOLD posted
  at edge `1789649544.225129`, awaiting Sol's ruling.
- Installed control/relay: release `4c148709`, AWAITING_CANARY, `armed=false` — healthy and NOT to be
  restarted.
- Posting discipline: the root edges `1789644071.495499` (#758 scope request), `1789645665.697889` (#757
  candidate return) and `1789649544.225129` (#758 RESULT/HOLD) are already posted and must never be
  repeated.

## Boundaries this fold does not cross

- It makes no claim about production, live traffic, browser binding, enrollment, grants or #714 activation.
- It does not authorize an install ceremony, a release, a restart, or an arm.
- It does not restate or re-adjudicate the waves carried by the 2026-09-16 POST-7181 fold; it re-pins only
  the workstream's own status and next action and defers per-carrier detail to that handoff and the record
  body.
