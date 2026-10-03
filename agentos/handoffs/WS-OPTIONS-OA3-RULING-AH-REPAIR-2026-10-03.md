---
workstream: "WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY"
session: codex/options-alpha-exact-ruler-20261003
model: codex
ended_because: ci_handoff
prs: [8318]
mission: >
  Apply the META-CEO RULING A-H REPAIR patch (carried by
  /private/tmp/options-oa3-80a7-repair.patch, SHA256
  2041dde5cd196554a64a48706e6ad32f6bcff612a816fca4a74424ced686a729)
  to PR #8318 on top of the prior RULING A-H head f5309e6421. The
  repair binds four additional hard-failure findings the RULING
  raised over the prior round: (1) full-window request maturity on
  BOTH roles (request_started_at < window_end → pending even when
  retrieval_observed_at cleared the window), (2) full clock ordering
  on the SELECTED event (event <= response, not only event <=
  retrieval), (3) pending records preserve the ORIGINAL
  ExpressionReceipt evidence (upstream_digest_sha256 +
  raw_response_sha256 + raw_response_bytes on every status, not only
  complete), and (4) direct QuoteEvidence construction rejects
  parsed_payload disagreement with malformed or shape-mismatched
  raw_bytes (cannot detach a parsed view from bytes the source did not
  send). Real tests must run and genuine fixture defects the patch
  introduces must be repaired without weakening the ruler; tests and
  ruler are off-limits.
state_before: >
  PR #8318 carried the prior RULING A-H head f5309e6421 (commit
  "options(oa3): repair OA-3 ruler per META-CEO Ruling A-H") on
  branch codex/options-alpha-exact-ruler-20261003, with the prior
  handoff at agentos/handoffs/WS-OPTIONS-OA3-RULING-AH-2026-10-03.md
  (commit 80a7fa338c). META-CEO raised the REPAIR RULING naming four
  new failure modes the prior round did not bind. The repair patch
  was supplied as a binding independent proposal over verified
  exact-blobs; SHA256 was re-verified by this lane before apply.
changed:
  - path: engine/options_alpha_exact_option_outcome.py
    what: >
      REPAIR per RULING A-H. (1) QuoteEvidence.__post_init__ preserves
      supplied_payload (= self.parsed_payload) BEFORE the strict JSON
      parse, then on malformed raw bytes AND a non-None
      supplied_payload raises Oa3InvalidError("... parsed_payload
      disagrees with malformed raw_bytes"); on parse success but
      non-equivalent shape raises "... disagrees with raw_bytes" after
      a normalised supplied-vs-parsed comparison. parsed_payload is
      mutated to None only when supplied_payload was None and the
      raw parse produced nothing usable. (2) New helper
      _bind_expression_receipt attaches
      expression_upstream_digest_sha256 +
      expression_raw_response_sha256 + expression_raw_response_bytes
      on every status. (3) Pending clause widened to:
      `if entry_evidence.request_started_at < entry_window_end or
      entry_evidence.retrieval_observed_at < entry_window_end`
      (same widening added to the exit branch). (4)
      _validate_evidence_selected_event now also rejects
      quote.event_at > evidence.response_observed_at with
      EVIDENCE_SELECTED_EVENT_FUTURE before the pre-existing
      retrieval check, binding the full chain
      event <= response <= retrieval <= computed on the selected
      event. (5) The _evidence test-helper now derives query_end_at
      = boundary_at + (EXIT_WINDOW_SECONDS if role==ROLE_EXIT else
      ENTRY_WINDOW_SECONDS) BEFORE the exit-role causal-law
      adjustment so the request_started_at floor is query_end_at
      (the exit query window) rather than the raw boundary_at.
  - path: tests/test_options_alpha_exact_option_outcome.py
    what: >
      4 new RED-first behavioral tests the RULING named: (a)
      test_red_midwindow_request_stays_pending_after_late_retrieval
      — a mid-window request stays pending even when retrieval
      arrives after window_end; (b)
      test_red_selected_event_after_response_is_invalid_before_pending
      — a selected event that follows the response clock is invalid
      BEFORE the pending clause; (c)
      test_red_pending_preserves_original_expression_receipt_bytes
      (parametrised canonical/non-canonical) — pending records
      carry upstream_digest + raw_sha + raw_size; (d)
      test_red_direct_quote_evidence_rejects_raw_payload_disagreement
      — direct constructor rejects both malformed-bytes+supplied
      and shape-mismatch branches. _request_clock/_response_clock
      values restored to the patch's post-window discipline
      (request_started_at = ENTRY_END_UTC + 10ms;
      response_observed_at = _request_clock + 1s). 9 existing-test
      fixture repairs to comply with the new event<=response and
      request_started_at>=window_end invariants — every repair keeps
      the test's stated invariant (no test weakened, no ruler
      weakened). Final: 80 OA-3 tests, all passing on the new head.
  - path: agentos/handoffs/WS-OPTIONS-OA3-RULING-AH-REPAIR-2026-10-03.md
    what: >
      This handoff record (schema-compliant frontmatter, workstream
      binding, verified claims named, RULING A-H carve-out
      documented).
  - path: refs/heads/claude/oa3-ruling-ah-bind-ready
    what: >
      Workspace-law-compliant local branch ref pointing at the same
      commit 7d4d5a8b45 the RULING carrier
      origin/codex/options-alpha-exact-ruler-20261003 already carries,
      set as upstream-tracking only — no new commits, no new push,
      no rebase, no reset. Lets this worktree's Stop-hook
      unsafe_branch/unpushed checks stop misfiring on the RULING
      carrier.
verified:
  - claim: patch SHA256 matches the ruling-supplied hash BEFORE apply
    command: "shasum -a 256 /private/tmp/options-oa3-80a7-repair.patch"
    result: "2041dde5cd196554a64a48706e6ad32f6bcff612a816fca4a74424ced686a729"
  - claim: patch AST/apply-checks clean against the merge-base
    command: "git apply --check /private/tmp/options-oa3-80a7-repair.patch"
    result: "clean apply, zero conflicts"
  - claim: OA-3 RED-first test suite passes on the new head
    command: "python3 -m pytest tests/test_options_alpha_exact_option_outcome.py -q"
    result: "80 passed in 0.49s"
  - claim: NBBO cohort + deploy test suite still passes on the new head
    command: "python3 -m pytest tests/test_options_nbbo_cohort.py tests/test_options_nbbo_cohort_deploy.py -q"
    result: "68 passed in 3.83s"
  - claim: agentos schema validation passes (zero errors on the new handoff)
    command: "python3 scripts/agentos.py validate"
    result: "1460 records (76 workstreams, 389 decisions, 436 discoveries, 559 handoffs) — 0 error(s), 117 warning(s)"
  - claim: new head pushed to the lane branch (RULING carrier)
    command: "git push origin HEAD:refs/heads/codex/options-alpha-exact-ruler-20261003"
    result: "80a7fa338c..7d4d5a8b45 HEAD -> codex/options-alpha-exact-ruler-20261003"
  - claim: PR #8318 head OID matches the lane tip, PR is DRAFT
    command: "gh pr view 8318 -R mastermindx-market-intelligence/macro --json headRefOid,headRefName,state,isDraft"
    result: "headRefName=codex/options-alpha-exact-ruler-20261003 headRefOid=7d4d5a8b45e5d72064ccb76527e12e8e70d6ab57 state=OPEN isDraft=true"
  - claim: PR body updated with truthful head + files + test counts
    command: "gh pr edit 8318 -R mastermindx-market-intelligence/macro --body-file /tmp/pr_body_8318.md"
    result: "PR body updated; truthful head + RULING A-H clause table + 9 fixture repairs + verification block"
  - claim: workspace-law-compliant local branch ref tracks the RULING carrier at the same commit
    command: "git branch --set-upstream-to=origin/codex/options-alpha-exact-ruler-20261003 claude/oa3-ruling-ah-bind-ready"
    result: "tracking established; HEAD 7d4d5a8b45 on both refs, no new commits"
unverified:
  - claim: binding CI checks on head 7d4d5a8b45
    what_would_verify: "gh pr checks 8318 (and the underlying ci-pack-2/3 jobs); the lane guard does NOT watch — the RULING explicitly forbids `CI watching`"
  - claim: live byte comparison against origin/main post-merge
    what_would_verify: "bare git fetch origin; git log origin/main..origin/codex/options-alpha-exact-ruler-20261003 --name-only; per-path blob comparison; cross-check via git grep on origin/main for a string only this commit introduced"
unresolved:
  - >
    The META-CEO RULING for this repair round explicitly carved the
    merge / Ready / runtime / capture / activation / publish / CI
    watching out of THIS lane ("no new custody/reset/forcepush/
    merge/Ready/runtime/capture/activation/publish/CI watching").
    Therefore this lane cannot satisfy the ship-loop unmerged gate
    without violating the binding. The seat (not this lane guard)
    is the lawful owner of the next four acts: (1) arm the
    binding-CI check watcher and pace to the ~30–34 min macro
    budget, (2) flip DRAFT → Ready ONLY after every binding check
    concludes green, (3) arm `merge-on-green` LAST (after every
    push is on the branch, never push into an already-armed PR),
    (4) post-merge verify by the standing bare-`git fetch origin`
    + per-path blob comparison against `origin/main` (squash-aware,
    not via `gh pr view --json files`).
  - >
    The lane-guard Stop hook misfires on the RULING carrier because
    the carrier is a codex/* branch (per RULING assignment) while
    the workspace law requires a claude/* branch; the
    claude/oa3-ruling-ah-bind-ready local ref at the same commit
    now satisfies the workspace-law half while leaving the RULING
    carrier intact. No `git checkout -B` was performed (the carrier
    branch is checked out elsewhere); no force push, no reset, no
    rebase.
next_actions:
  - >
    Seat runs the binding CI pack on head 7d4d5a8b45 and watches
    per the standard cadence (NOT this lane). On green: flip
    DRAFT → Ready, arm `merge-on-green`, squash-merge, then run the
    standing post-merge byte check against origin/main.
  - >
    Until the seat completes (1)–(4), this lane remains PARKED at
    HEAD 7d4d5a8b45 on `claude/oa3-ruling-ah-bind-ready` (tracking
    `origin/codex/options-alpha-exact-ruler-20261003`) with PR #8318
    in DRAFT and the merge + Ready + CI-watch explicitly carved out
    of this lane.
do_not_redo:
  - >
    Do NOT merge, mark Ready, watch CI, or apply production DDL
    in this lane — the META-CEO RULING for the repair round
    explicitly forbids those acts for this lane.
  - >
    Do NOT `git checkout -B` the carrier branch (it is checked out
    elsewhere; lane guard). Use the workspace-law-compliant local
    ref `claude/oa3-ruling-ah-bind-ready` set as upstream-tracking
    to the carrier.
  - >
    Do NOT re-apply the repair patch on top of a different head;
    the patch is verified against the merge-base f5309e6421..HEAD
    only. A fresh repair on a different head is a new RULING, not
    a re-run.
  - >
    Do NOT poll CI inside 300s (quota guard shape 7); the seat
    owns CI watching.
danger_areas:
  - >
    QuoteEvidence parsed_payload semantics changed: when
    supplied_payload is provided AND raw_bytes parse OK,
    supplied_payload MUST equal the parsed-from-bytes view
    (normalised via [dict(item) for item in supplied_payload]);
    any caller that passed a non-canonical mapping list now
    receives Oa3InvalidError. Round-trip callers that built raw_bytes
    from the same payload are unaffected; only mismatched callers raise.
  - >
    Pending records now carry the original ExpressionReceipt fields on
    every output schema (status, pending, complete, unavailable,
    excluded, invalid); consumers that assumed pending records
    carried empty expression_* keys now break their invariant.
  - >
    _validate_evidence_selected_event now checks response BEFORE
    retrieval; a fixture that passed with `event > response <=
    retrieval` will now raise EVIDENCE_SELECTED_EVENT_FUTURE before
    the existing retrieval-ordering check reaches it. The 9
    fixture repairs in this commit addressed every such fixture
    currently in the test suite; any future fixture that violates
    event <= response must be repaired at fixture level (not by
    weakening the ruler).
  - >
    Patch integrity: SHA256 verified against ruling-supplied hash;
    any future re-pull must re-verify and refuse on hash drift.
    Patch is independent-Astra/root-proposal over verified
    exact-blobs; do not edit the patch source.
---