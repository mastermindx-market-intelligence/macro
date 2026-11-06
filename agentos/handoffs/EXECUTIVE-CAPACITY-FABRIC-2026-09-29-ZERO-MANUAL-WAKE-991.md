---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/wake-claude-h1-20260925 (worktree wake-claude-h1-991-closer-74daef81adcdb32a, owner session 7712b0f4)
model: fable
ended_because: complete
mission: >
  Close the zero-manual-wake gap under agent-fabric-end-to-end-fable-integration-20260913-sol-001 / Mastermind #600:
  qualify and repair the exact-session Claude Code Wake transport on the existing DRAFT/HOLD carrier #991 so a dead
  Claude Code receiver can be re-entered in place by exact --resume <native_handle>, fail-closed everywhere else,
  with independent review of the exact head and real-host evidence bound to that head. The descriptor flip
  (claude-code-session.transport_implemented) is NOT part of this mission.
state_before: >
  #991 held an EFFECT_UNKNOWN historical canary (cd003b4c) and an adapter whose delivery could not distinguish a
  pre-effect failure from an unobserved effect, resolved the receiver by discovery rather than by the transcript
  store, and attributed replies by record adjacency. The peer lane had proven (E7) that exact --resume of a dead
  Desktop-class session re-enters it in place with the same session id; that evidence was consumed, not re-derived.
  claude-code-session.transport_implemented was false; production_armed false.
changed:
  - path: mastermind/pull/991 (integrations/executive_wake/claude_code.py)
    what: >
      Rewritten across commits 2103c93b, 073c0fbf, efe0bb64, cb74af84, 1883da02: receiver resolved by exact handle in
      the transcript store (refuse absent/ambiguous/symlinked/oversized/foreign-identity); resume cwd = the receiver's
      last recorded cwd, resolved, inside allowed roots; `claude --version` must be exactly one line of a qualified
      build ({2.1.275}); `claude agents --json` is an exclusion-only guard; delivery argv is closed (safe-mode,
      restricted, tools "", no MCP, max-turns 1, json-schema sentinel); DELIVERED requires the provider sentinel
      naming the same session AND, in the receiver's own transcript, the exact prompt record with a model-authored
      reply linked to it by parentUuid through no user-type record (uuid collisions poison); pre-effect refusal needs
      two agreeing unchanged-store observations across a settle; everything else is effect-unknown and never retried;
      read-only reconcile() closes late attempts by the same rule and asserts the strong negative only when the
      nudge id appears nowhere in the session.
  - path: mastermind/pull/991 (tests/test_claude_code_wake_dispatcher.py)
    what: 124 focused tests (wake glob 534) pinning every invariant above, including fixtures shaped from real transcripts.
  - path: mastermind/pull/991 comments 5894568386, 5894808032, 5895135409, 5895479373, 5895621477, 5895714463
    what: six same-carrier posts (audit rounds 1-5 adjudicated by artifact, repairs, evidence bound by sha256, scoped ACCEPT, exact blockers).
verified:
  - claim: "The adapter at 1883da02 completes a real end-to-end delivery into a dead Opus-bound headless disposable with the reviewed composition."
    command: "python3 q991.py <scratchpad> opus  (real ClaudeCodeWakeDispatcher, bounded subprocess runner, harness refuses a dirty tree)"
    result: >
      evidence_run7_round4_delivery_at_head.json: head 1883da02, dirty false, source_sha256 bfcb8e67...; disposable 5b5d41d3
      Opus-verified from its own result before any resume; 0/39 live rows; runner order ['--version','agents','--resume'];
      DELIVERED in 7.4 s; resume modelUsage claude-opus-5 only; sentinel MASTERMIND_CLAUDE_WAKE_DELIVERED_V1; store
      24319->44740 bytes, siblings 1->1; reconcile() DELIVERED, marker 524==524, chain user->attachment->assistant.
  - claim: "Refusal paths are real on the host without provider effect."
    command: "python3 p5_run6.py <scratchpad> evidence_run6b_round4_bound_to_head.json"
    result: >
      live_writer against this live session after exactly --version + agents --json, no resume launched; real CLI against
      a store lacking the handle exits 1 'No conversation found' with both stores byte-identical -> pre_effect_failure;
      a stand-in printing 2.1.276 -> cli_unqualified before discovery; chain reconcile DELIVERED on the real b2c425ab
      transcript and effect-unknown on the safeguards-refused 9cf78471 transcript.
  - claim: "Focused and wake-glob suites pass; the head composes on protected master."
    command: "python3 -m pytest tests/test_claude_code_wake_dispatcher.py $(ls tests/test_*wake*.py) -p no:cacheprovider -o addopts=\"\" -q; git merge-tree --write-tree origin/master HEAD"
    result: "124 passed / 534 passed; merge-tree wrote a tree against 8d664289 with no conflict."
  - claim: "Non-claims hold."
    command: "grep transport_implemented control_plane/wake_transport.py config/wake_session_targets.json; git diff --stat origin/master...HEAD"
    result: "claude-code-session.transport_implemented false; production_armed false; only the two files above changed; canary cd003b4c untouched."
  - claim: "Round-5 independent read-only review (opus, ROUTE: AUDIT, MODE: READ_ONLY, 9/12 calls) ACCEPTED 1883da02, scoped to the adapter source plus headless-receiver real-path evidence."
    command: "Agent packet consumed and posted as mastermind/pull/991 comment 5895714463 with shasum -a 256 of both files (bfcb8e67..., be52430a...) equal to the sha256 recorded inside the evidence JSON"
    result: "ACCEPT (scoped); no new defect; three LOW follow-ups (reconcile listing without version probe; leading-noise version pin; unmemoised chain walk) carried, not repaired, so the reviewed bytes stay the accepted bytes."
unverified:
  - claim: "CI `test` on 1883da02 is green (the cb74af84 `test` run was cancelled by the superseding push)."
    what_would_verify: "GET /repos/.../commits/1883da02.../check-runs showing test completed success."
  - claim: "The same adapter re-enters a dead INTERACTIVE Desktop-class receiver."
    what_would_verify: "One real run against such a receiver; the peer's E7 evidence covers the mechanism, this adapter's real-path runs cover the headless class only."
unresolved:
  - "Fabric wiring is not in #991: a host runner implementation and configuration for claude_config_dir / receiver_cwd_roots."
  - The discovery-to-launch window (a human may start a turn between the listing and the resume) is a stated residual risk the adapter does not mitigate; accepting it is a receiver-safety ruling that precedes any descriptor flip.
  - Opus safeguards refuse a session after one refusal (9cf78471); the transport never retries and classifies effect-unknown.
next_actions:
  - Obtain the accepted-risk ruling (human-only) for the discovery-to-launch window; it precedes any descriptor flip.
  - "Commission the fabric-wiring change (not #991, fenced by #836): flip claude-code-session.transport_implemented in control_plane/wake_transport.py, provide the dispatcher in process composition (today scripts/executive_os_phase1c.py:84 composes only codex-app-server), add a bounded host runner, claude_config_dir / receiver_cwd_roots config, and a claude-code-session session-target binding carrying the exact native_handle; fold in the three LOW follow-ups; independent review of that head."
  - Keep the historical #991 canary cd003b4c as EFFECT_UNKNOWN; never replay it.
do_not_redo:
  - Do not re-derive E7 (exact --resume of a dead Desktop-class session re-enters in place); consume it.
  - Do not re-run canaries on the shared host to prove listing scope, cross-cwd resume, or the hidden --max-turns option; measured and recorded on #991 (comments 5895135409, 5895479373).
  - Do not add a lock, a session registry, title/newest-session guessing, or a sibling fallback; each was ruled out.
  - Do not exercise OAuth refresh contention against the shared host; the contention text is a refusal-class refinement only.
danger_areas:
  - Evidence produced from a dirty tree or a previous commit is not evidence for the reviewed head (round-4 finding 1); the harnesses now refuse a dirty tree and record source_sha256.
  - q991.py writes evidence.json at the scratchpad root, not under q991/; copying the wrong file reports a stale run.
  - The opus-auditor child caps at 12 turns; give it a call budget and require the verdict packet before the cap.
  - "`claude agents --json` rows carry no state key; any listed row for the handle is a writer."
prs: [991, 600, 703]
discoveries: ["DSC:CLAUDE-AGENTS-LISTING-IS-HOST-WIDE-AND-LISTS-HEADLESS-RESUME", "DSC:CLAUDE-RESUME-APPENDS-IN-PLACE-AND-RECORDS-PROMPT-AS-STRING"]
---
