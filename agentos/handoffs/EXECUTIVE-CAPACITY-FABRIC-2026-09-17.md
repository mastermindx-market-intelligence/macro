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
  the 2026-09-16 fold had written. Two Mastermind children carried Sol adjudications that existed only
  inside their own sessions, and the fold did NOT describe them both as terminated: #757 at
  f079f1ee14003dbcc12cfe7154c90c713eac3373 was terminal (ACCEPTED/STOP at edge 1789648278.066969,
  DRAFT-HOLD, BUILT_NOT_PROVEN) while #758 at
  55800d57f42f73a6c093e1432da16b78e3d2ab83 (RESULT/HOLD posted at edge 1789649544.225129, awaiting Sol's
  ruling) was not. #758's later accepted terminal state — REMOTE_COMPLETE_VERIFIED, BRANCH_WRITER_RELEASED
  at that head, still unmerged — is recorded in the currentness section of this file. No Agent OS record
  mentioned either child, the installer manifest regression, or the kit-lane gate limit.
changed:
  - path: agentos/discoveries/DSC-INSTALLER-MANIFEST-REFUSES-TRACKED-SYMLINKS-SINCE-583.md
    what: >
      New discovery: every Executive OS release manifest CREATE fails on a release tree containing the
      tracked symlink `vendor/macro`, because the manifest walk asks the shared macOS ACL observer
      path-only and the observer opens with `O_NOFOLLOW` and refuses non-file/non-directory objects. Carries
      both admission gates: the falsifier is a protected-master manifest CREATE succeeding with
      `vendor/macro` present, and the so_what keeps the installed control/relay unrestarted — at fold time
      they ran prior generation 4c148709 (AWAITING_CANARY, armed=false), which this fabric never
      health-verified and which must never be called healthy or current — until #757's repair landed.
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
      SUPERSEDED IN PART by the currentness repair recorded next: the fold-time `next_action` text is
      preserved as the state read at the fold commit 12838af9, the same field now carries the post-21:20Z
      accepted state, and the "arrays NOT extended" note no longer holds — the repair added two machine
      edges to `discoveries`.
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-17.md
    what: >
      CURRENTNESS REPAIR (2026-09-17, Sol ruling edge 1789680829.787409) on top of the fold commit: the
      `unverified`, `unresolved`, `next_actions`, `do_not_redo` and `discoveries` fields now carry the
      accepted state, and the body gains a dated "Currentness — 2026-09-17 21:20Z UTC" section plus
      "Intake deltas". Every earlier statement in this file is preserved as historical at its own read
      time and marked as such; nothing was silently rewritten into present truth. Fixes the three findings
      of the independent review at the fold commit: the "two terminated source children" claim (now
      grounded per child), the "install on Sol's maintenance merge" phrasing (an install needs its own
      authorization; this one was separately authorized and performed at 21:20Z), and the ungrounded
      "healthy 4c148709" wording (removed everywhere).
  - path: agentos/workstreams/WS-EXECUTIVE-CAPACITY-FABRIC.md
    what: >
      Currentness repair of the `next_action` field (the wave-boundary pointer the fold wrote) plus the two
      new machine edges in `discoveries`. Protected master re-pins to b731149296a9d837d426730813f68d5acc6133ac;
      #757 is recorded as MERGED at 8b231e82; #758 as VERIFIED/BRANCH_WRITER_RELEASED and awaiting its own
      merge; the installed state as accepted UNARMED/STOPPED; the next gate as HUMAN_AUTH /
      CREDENTIAL_READINESS. The fold-time text of the field is superseded, not deleted — it stays in the
      fold commit and is quoted in this handoff's historical section.
  - path: agentos/discoveries/DSC-INSTALLER-MANIFEST-REFUSES-TRACKED-SYMLINKS-SINCE-583.md
    what: >
      Currentness repair: the `so_what` now states the current accepted installed state and keeps the
      pre-merge blocked state as historical, the `claim` names the pin it was observed at (`e878878c`,
      before the repair merged as `8b231e82`), and the body's "Blast radius" drops the ungrounded "healthy
      4c148709" wording and gains the dated currentness section.
  - path: agentos/discoveries/DSC-EXECUTIVE-INSTALL-DOES-NOT-OWN-THE-C1-RELAY-PLIST.md
    what: >
      New discovery with both admission gates: an install writes the control/worker.codex/backup plists to
      the installed generation but never the C1 sol-state-relay plist, whose generation is separately owned
      by `prepare-c1-sol-state-relay.sh` — so there is no single "installed generation" (control `8b231e82`,
      C1 relay `4c148709`, MCP `46bea208`).
  - path: agentos/discoveries/DSC-ROOT-CONTEXT-GIT-ON-A-LINKED-WORKTREE-NEEDS-A-PROCESS-LOCAL-SAFE-DIRECTORY.md
    what: >
      New discovery with both admission gates: a root-context installer `git` read on the linked SSD
      worktree is refused by the dubious-ownership source-policy gate before any install action, and the
      repair is a process-local `GIT_CONFIG_COUNT` safe.directory tuple, never a global-config mutation; a
      pre-action refusal means the interrupted attempt is "no install occurred", not a partial install.
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
  - claim: "Mastermind protected master is b731149296a9d837d426730813f68d5acc6133ac, and the movement from 8b231e8267f09cfb002ed3e87bec14906dce1720 to it is ONE commit touching only integrations/mastermind_company_mcp/consultation.py and tests/test_company_consultation_mcp.py — no Executive install, ops, config, relay or credential source moved."
    what_would_verify: "`git ls-remote https://github.com/mastermindx-market-intelligence/Mastermind refs/heads/master` and `gh api repos/mastermindx-market-intelligence/Mastermind/compare/8b231e8267f09cfb002ed3e87bec14906dce1720...b731149296a9d837d426730813f68d5acc6133ac --jq '{status, ahead_by, files: [.files[].filename]}'`. Carried from Sol ruling edge 1789680829.787409; this records-only fold ran no network read."
  - claim: "Mastermind #757 (installer manifest symlink-ACL repair) MERGED to protected as mergeCommit 8b231e8267f09cfb002ed3e87bec14906dce1720, parent aacf3df5, 2026-09-17 19:54:58Z, after Sol ACCEPTED/STOP — the ONLY source child with an ACCEPTED/STOP terminal."
    what_would_verify: "`gh pr view 757 -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid,mergeCommit,mergedAt`."
  - claim: "Mastermind #758's corrected Source Continuity verdict REMOTE_COMPLETE_VERIFIED (receipt_digest bf95eba81b4c1f469227a33bf176b04314bb6e826e700fcba2a8a61a98617a4a) was ACCEPTED, the exact child source (the SSD worktree) was REMOVED, and BRANCH_WRITER_RELEASED is at head 55800d57f42f73a6c093e1432da16b78e3d2ab83 (root edge 1789680353.465089, accepted 1789680603.345609). A separate Sol release-maintenance operation marked #758 Ready and submitted that exact head to the protected Mastermind merge queue, observed at position 1 — PR NOT YET MERGED."
    what_would_verify: "`gh pr view 758 -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid,mergeCommit,mergedAt`, plus the Source Continuity receipt surface for receipt_digest bf95eba8… . Do not claim protected source for #758 until an actual merge receipt exists; this fold ran no remote read."
  - claim: "The Executive OS install ceremony COMPLETED SUCCESSFULLY on 2026-09-17 21:20–21:21Z for installed generation 8b231e8267f09cfb002ed3e87bec14906dce1720 (installer rc=0; release manifest sha256 ec7231b0b826d2e6c829036b92ea59f6f6eee061fb95905007b5fdea20ff90e1; tree a6f21af86dbc018621c04126ae7e6579899aafaf with 2303 entries, verify ok; installed control.json sha256 1676d78dce2715d54d64cbc73dd3b9c6c7d426da3270edf95d85795423a6b4f3), and Sol ACCEPTED the state as UNARMED / STOPPED."
    what_would_verify: "Read the installer receipt and the installed control.json on the host as root, or read Sol's ruling at edge 1789680829.787409. Carried from that ruling: this records-only fold ran no installer and no host command."
  - claim: "Before that install, the installed control/relay ran prior generation 4c148709 in state AWAITING_CANARY with armed=false."
    what_would_verify: "Read the pre-install release pointer and armed state as root, or the fold-time child receipts. This fold verified neither, and 4c148709 was never a health verdict: it is the PRIOR generation, whose release directory remains on disk, intact."
  - claim: "The carried-over state of the other waves (W1-H3 #677 head and its R80/R14 chain, CF2-H0 carrier-proof requirements, OCR-2C Family A/B state, PF1 and the MH1 holders)."
    what_would_verify: "Re-read the 2026-09-16 POST-7181 fold and this record's per-wave next_action entries, then re-read each live head with `gh pr view <n> -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid` before acting."
unresolved:
  - "Mastermind #758 is Ready and sits in the protected merge queue (observed position 1) but is NOT MERGED; no protected source may be claimed until an actual merge receipt exists."
  - "The services are UNARMED / STOPPED by Sol's option-B ruling: a relight is NOT 'pending', and no credential, provider or ARM effect has occurred. The installed generation 8b231e82 is installed but not running."
  - "The installed plist generations are not one vector: control/worker.codex/backup = 8b231e82, C1 sol-state-relay = 4c148709 (separately owned), MCP = 46bea208. See DSC:EXECUTIVE-INSTALL-DOES-NOT-OWN-THE-C1-RELAY-PLIST."
  - "HUMAN_AUTH / CREDENTIAL_READINESS is the next gate: provision-worker-auth.sh --verify-ready needs a reviewed credential kind, a company-workspace admin attestation class and the Chairman-owned CREDENTIAL_EXPIRES_AT; it must never be guessed or inspected."
  - "PF1 stays NONTERMINAL: the provider refused before commands/items/messages on account capacity, source custody is retained at J 545b91768517a00b55fb0ecb95576f32befda1cb, and no retry or failover is permitted before fresh post-reset capacity evidence."
  - "No recovered Mastermind Steward asdk_app identity exists, so viewer-client registration and authenticated browser-host binding remain HUMAN_AUTH; the absence of an identity is NOT permission to create a duplicate app, deployment or auth plane."
  - "The Reader static fence remains blind to package-form and `importlib` imports (pre-existing, neither widened nor repaired by #758)."
next_actions:
  - "Re-read protected master and the #758 merge state before claiming anything about #758's source; do not re-run its verifier, re-post its receipts, or re-create its released child source."
  - "Do NOT re-run the install ceremony. It is no longer gated on #757 (which merged as 8b231e82): it was authorized by its own root edges 1789675323.742409 and 1789679576.748139 and performed at 2026-09-17 21:20Z, and its state is ACCEPTED UNARMED / STOPPED. A source merge is never an install authorization, and a future install or relight needs a fresh authorization of its own."
  - "Hold Gate B and the arm step at HUMAN_AUTH / CREDENTIAL_READINESS (reviewed credential kind, company-workspace admin attestation class, Chairman-owned CREDENTIAL_EXPIRES_AT) and leave the services stopped. Do not restart the installed control/relay to test anything."
  - "Re-read the carrier branch and this handoff before every act or post, since the seat pushes this branch after a freshness read and the parent commit may already be superseded."
do_not_redo:
  - "Never restart the installed Executive control/relay: Sol ruled option B (keep services stopped) and the accepted installed state is UNARMED / STOPPED for generation 8b231e82. A relight is not 'pending' — it needs a fresh authorization."
  - "Never call 4c148709 healthy or current: it is the PRIOR generation, its release directory remains on disk intact, and this fabric never health-verified it. A restart is not a repair."
  - "Never treat a source merge as an install authorization, and never re-run the 21:20Z install: that ceremony was separately authorized by root edges 1789675323.742409 and 1789679576.748139 on 2026-09-17."
  - "Do not redo the symlink-ACL repair or re-open Mastermind #757: it is MERGED as 8b231e82, and its source child is the only one with an ACCEPTED/STOP terminal."
  - "Never repair a root-context git dubious-ownership refusal with a global `safe.directory` write; use the process-local GIT_CONFIG_COUNT tuple (see DSC:ROOT-CONTEXT-GIT-ON-A-LINKED-WORKTREE-NEEDS-A-PROCESS-LOCAL-SAFE-DIRECTORY)."
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
  - DSC:EXECUTIVE-INSTALL-DOES-NOT-OWN-THE-C1-RELAY-PLIST
  - DSC:ROOT-CONTEXT-GIT-ON-A-LINKED-WORKTREE-NEEDS-A-PROCESS-LOCAL-SAFE-DIRECTORY
---

## What this fold is

Records only. One descendant commit on the existing carrier branch
`claude/agentos-fabric-fold-20260916`, on top of `0c9b8281271f64fa958a03ce86824b246cdaa1f5`, holding PR
#7223 (OPEN / DRAFT / HOLD-FOR-SOL). No push, no PR edit, no label, no GitHub or Slack write, no install
ceremony, no host change, no other worktree touched. The seat pushes after a carrier freshness read.

## The four folded records (two further discoveries were added by the currentness repair)

| Record | One line |
|---|---|
| `DSC:INSTALLER-MANIFEST-REFUSES-TRACKED-SYMLINKS-SINCE-583` | Every release manifest CREATE fails on a tree containing the tracked symlink `vendor/macro`, because the walk asks the shared ACL observer path-only and the observer refuses symlinks. |
| `DEC:SYMLINK-ACL-OBSERVATION-IS-MANIFEST-ONLY-OPT-IN` | The default observer stays path-only; one keyword-only `allow_symlink=False` opt-in, gated on a caller-supplied `os.stat_result`, native `O_SYMLINK`, identity re-proof and observed link-ness, is used by exactly one call site. |
| `DEC:READER-FENCE-EXCEPTION-IS-AN-EXACT-IMPORTER-MODULE-MAP` | The Reader static fence gains an exact importer->module map for two named importer files, each permitted `owner_read_resource` only. |
| `DSC:FULL-MASTERMIND-GATE-CANNOT-RUN-INSIDE-A-KIT-LANE` | A kit worker lane cannot run the full Mastermind gate; lanes report focused evidence and let the hosted required `test` check be the real verifier. |

## Carrier and program state at this fold — HISTORICAL SNAPSHOT (as read at 12838af9, before 2026-09-17 19:54:58Z)

Every line below was true as of the fold commit and is preserved unchanged in meaning; each is superseded
by the "Currentness" section that follows. Read them as history, never as present truth.

- Protected Mastermind master was `e878878c9a4ae2dd50a48d825e031e07e8211708`, read 2026-09-17 earlier that
  day.
- Mastermind #757 (symlink ACL repair) was OPEN / DRAFT / HOLD-FOR-SOL at
  `f079f1ee14003dbcc12cfe7154c90c713eac3373`, Sol ACCEPTED/STOP at edge `1789648278.066969`,
  BUILT_NOT_PROVEN, with the merge a Sol maintenance-only act.
- Mastermind #758 (Reader fence exception) was OPEN / DRAFT / HOLD-FOR-SOL at
  `55800d57f42f73a6c093e1432da16b78e3d2ab83`, Sol scope ruling edge `1789644750.659619`, RESULT/HOLD posted
  at edge `1789649544.225129`, awaiting Sol's ruling.
- The installed control/relay ran release `4c148709`, AWAITING_CANARY, `armed=false`, and NOT to be
  restarted. The fold also wrote "healthy" here; that word was never backed by a health read, is removed
  as an ungrounded claim, and `4c148709` is to be called the PRIOR generation, never "healthy" or
  "current".
- Posting discipline (still in force): the root edges `1789644071.495499` (#758 scope request),
  `1789645665.697889` (#757 candidate return) and `1789649544.225129` (#758 RESULT/HOLD) are already posted
  and must never be repeated.

Fold-time machine fields this currentness repair supersedes, quoted so nothing is lost: `unresolved` said
"Sol's ruling on the #758 RESULT/HOLD (edge 1789649544.225129) has not been consumed", "Mastermind #757
awaits Sol's maintenance-only merge; the post-fix install ceremony is NOT authorized before that merge",
and "Gate B / arm still wait on the Chairman-owned CREDENTIAL_EXPIRES_AT"; `next_actions` said to consume
the #758 ruling and to "run the staged post-fix install ceremony" on the #757 merge; `do_not_redo` said
"Never restart the healthy 4c148709 control/relay, and never run an install retry or ceremony before
Sol's maintenance merge of #757."

## Currentness — 2026-09-17 21:20Z UTC (Sol ruling edge 1789680829.787409)

Accepted facts after the fold commit. The values are carried from that Sol ruling and from the install
receipt it quotes; this records-only fold ran no host, installer, provider or network command of its own.

### Protected source

- Mastermind protected master is `b731149296a9d837d426730813f68d5acc6133ac`. The movement
  `8b231e82` -> `b7311492` is ONE commit touching only
  `integrations/mastermind_company_mcp/consultation.py` and `tests/test_company_consultation_mcp.py`; no
  Executive install, ops, config, relay or credential source moved.
- **#757 is MERGED** to protected as mergeCommit `8b231e82`, parent `aacf3df5`, 2026-09-17 19:54:58Z,
  after Sol ACCEPTED/STOP. It is the ONLY source child with an ACCEPTED/STOP terminal.
- **#758 is NOT merged.** Its corrected Source Continuity verdict REMOTE_COMPLETE_VERIFIED
  (receipt_digest `bf95eba81b4c1f469227a33bf176b04314bb6e826e700fcba2a8a61a98617a4a`) was ACCEPTED, its
  exact child source (the SSD worktree) was removed, and BRANCH_WRITER_RELEASED stands at head
  `55800d57f42f73a6c093e1432da16b78e3d2ab83` (root edge `1789680353.465089`, accepted
  `1789680603.345609`). A separate Sol release-maintenance operation marked #758 Ready and submitted that
  exact head to the protected Mastermind merge queue, observed at position 1. Do not claim protected
  source for #758 until an actual merge receipt exists.
- #758's collision with #124: the two nominal overlaps
  (`integrations/mastermind_steward_app/app.py`, `tests/test_mastermind_steward_app_asgi.py`) resolved as
  changed-path false positives — #124's blobs equal protected master, and #758 alone carries the feature
  deltas.
- Completed substrate `#575` / `#579` / `#576` / `#578` / `#581` / `#583` is MERGED and DO_NOT_REDO; any
  OPEN/DRAFT snapshot of those PRs is historical, not current.

### Installed Executive state (Sol option B)

- The canonical install ceremony COMPLETED SUCCESSFULLY for installed generation
  `8b231e8267f09cfb002ed3e87bec14906dce1720` on 2026-09-17 21:20–21:21Z: installer rc=0, release manifest
  sha256 `ec7231b0b826d2e6c829036b92ea59f6f6eee061fb95905007b5fdea20ff90e1`, tree
  `a6f21af86dbc018621c04126ae7e6579899aafaf`, 2303 entries, verify ok; installed `control.json` sha256
  `1676d78dce2715d54d64cbc73dd3b9c6c7d426da3270edf95d85795423a6b4f3`.
- Sol ACCEPTED that state as **UNARMED / STOPPED** and ruled option B: keep the services stopped. Do not
  call a relight "pending", and do not call `4c148709` "healthy" or "current" — it is the prior
  generation and its release directory remains on disk, intact.
- Installed plist generations are not one vector: `control` / `worker.codex` / `backup` = `8b231e82`; the
  C1 `sol-state-relay` plist is a separately owned generation recorded at `4c148709` (`install.sh` never
  writes it; `prepare-c1-sol-state-relay.sh` owns it) — see
  `DSC:EXECUTIVE-INSTALL-DOES-NOT-OWN-THE-C1-RELAY-PLIST`; MCP = `46bea208`.
- The install was authorized by its OWN root edges `1789675323.742409` and `1789679576.748139` — not by
  the #757 merge — and was performed 2026-09-17 21:20Z. A source merge is never an install authorization.
- A first attempt at 21:02Z was REFUSED at the installer's root-context source-policy gate (git
  dubious-ownership on the new SSD checkout) BEFORE any install action, and its control/relay restart was
  reconciled to the unchanged `4c148709` baseline. The corrected attempt used a process-local
  `GIT_CONFIG_COUNT` safe.directory tuple with no global-config mutation — see
  `DSC:ROOT-CONTEXT-GIT-ON-A-LINKED-WORKTREE-NEEDS-A-PROCESS-LOCAL-SAFE-DIRECTORY`.
- Next gate: HUMAN_AUTH / CREDENTIAL_READINESS — `provision-worker-auth.sh --verify-ready` needs a
  reviewed credential kind, a company-workspace admin attestation class and the Chairman-owned
  `CREDENTIAL_EXPIRES_AT`. NO credential, provider or ARM effect has occurred.

### Steward, browser and PF1

- Steward/browser: the Business workspace is visible; no Mastermind Steward `asdk_app` identity has been
  recovered, so the production Executive app remains `plugin_asdk_app_6aa89de1c45c81918b192d0a18dcfc15`.
  The Auth0 tenant admin is at login, so viewer-client registration remains HUMAN_AUTH. That absence is
  NOT permission to create a duplicate app, deployment or auth plane. Sol's browser-host ruling
  (Mastermind #758 comment 5720809880) is a same-origin Steward-hosted shell plus a distinct viewer public
  OAuth client, where `X-CCR-Token` is a CSRF nonce and not viewer authentication.
- PF1: the exact retained root was addressed and the provider refused BEFORE commands/items/messages on
  account capacity. Source custody is retained at J `545b91768517a00b55fb0ecb95576f32befda1cb`; there is
  no retry or failover before fresh post-reset capacity evidence, the operation stays nonterminal, and no
  other harness may be presented as satisfying native Anthropic PF1.

## Intake deltas folded at this currentness repair

Both are intake comments on PR #7223; neither authorized a source fold, a release or a new lane.

- **Comment 5720334260** (Control Room stable-delta intake, product `WS:CHAIRMAN-CONTROL-ROOM`): at that
  observation protected Mastermind was `aacf3df5`, and #758's head `55800d57` carried independent Sol
  APPROVED review `5240673652` (exact head, 2026-09-17T19:45:57Z) — source-only, explicitly
  BUILT_NOT_PROVEN / NOT_INSTALLED / RELEASE_HOLD, and NOT a writer release. The integration tree
  `1a2275a014336ce37af1f31ca93dbb7e0a8f2c68` passed 196 tests with zero failures, errors or skips (proof
  sha256 `92919f8bbb37863ad578f3d25137260852f89e8ae8b24500367a3d5d50be2809`), which replaces neither
  hosted CI nor production proof. It also recorded: #537's runtime-root repair waits on #710 and its own
  semantic-revalidation successor and must not be redone; #710 keeps its existing mastermindx-2/3 reviewer
  lanes and gets no third reviewer; #733 stays a retained candidate; #716 stays terminal/protected. The
  browser/enrollment/broker/exactly-once terminal-consumption chain remained NOT PROVEN there — and still
  is.
- **Comment 5720669549** (Control Room continuation delta): protected Mastermind had advanced to
  `8b231e82` and #758 was still OPEN/DRAFT at `55800d57`. Sol comment 5720582749 (root `1789675919.455609`)
  replaced literal-master pin authorization for the ONE corrected verifier invocation with bounded
  material-source compatibility, requiring the owner to prove the invocation was NEVER_STARTED before any
  reuse — a question this fold's accepted REMOTE_COMPLETE_VERIFIED + BRANCH_WRITER_RELEASED state now
  answers for that carrier, so nothing on it may be re-run. It also recorded: the #508 bounded
  `observe_root_lanes` reuse candidate stays OPEN/DRAFT at `3b0e97e7` and does not close the G8
  fabric-view gaps; the public reconciliation root `C0BSBM78V1N/1788732392.828139` reports the earlier
  private maintenance slot COMPLETE/SPENT with no resolved successor, and one exact read of
  `D0BTAKPHX8S/1788689346.571769` returned `channel_not_found` with no retry or private-search expansion
  (access/custody reconciliation debt, not a reader assignment); and the local `X-CCR-Token` is a
  browser-origin/CSRF nonce supplied by an unauthenticated GET, never viewer authentication. Parent and
  product remain PARTIAL / NONTERMINAL.

## Boundaries this fold does not cross

- It makes no claim about production, live traffic, browser binding, enrollment, grants or #714 activation.
- The fold itself authorized no install ceremony, release, restart or arm. The later 21:20Z install was
  authorized by its own root edges (`1789675323.742409`, `1789679576.748139`) and is accepted as
  UNARMED / STOPPED; this record still authorizes neither a relight nor an arm.
- It does not restate or re-adjudicate the waves carried by the 2026-09-16 POST-7181 fold; it re-pins only
  the workstream's own status and next action and defers per-carrier detail to that handoff and the record
  body.
