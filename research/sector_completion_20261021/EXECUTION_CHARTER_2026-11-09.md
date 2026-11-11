# Sector Intelligence build-out — execution charter (binding for every lane)

Program: Macro #7646 / WS:SECTOR-INTELLIGENCE-COMPLETION. Chairman Chris assigned this build on 2026-11-09.
Program lead / COO: T3 thread 2f136a11-91f9-4bca-bf10-8a1d8b7f4e5d (Fable). You are a lane suborchestrator
(or a worker of one). The COO keeps integration, adjudication and acceptance. You deliver your lane.

## Plan documents (read only what your lane needs — they are large)
Local copies (identical to commit f1dfbedd973f of macro branch sol/sector-shared-shell-masterplan-20261109-c3, PR #10915):
- /tmp/si_plan/PACKET.md            final implementation packet (source frontier §2, frozen contracts §3, lane briefs §4, Paper donors §5, 134-capability join §6, verticals §7, delivery order §8)
- /tmp/si_plan/brief_<N>.json       your complete machine-readable lane brief (N given in your task)
- /tmp/si_plan/ROUND3_CONTRACT.md   architecture contract (math, rhythm, phase-age, 28 falsifier cases)
- /tmp/si_plan/ROUND2_PAPER_GUIDE.md Paper design guide (47 reviewed frames, interaction contracts, source-to-field contract)
- /tmp/si_plan/MASTERPLAN.md        task tree P01–P23 / B01–B12 / J01–J15
Use grep and line-ranged reads. Do not load whole files into context.

## Repositories
- Macro:    github.com/mastermindx-market-intelligence/macro, default `main`.
- Terminal: github.com/mastermindx-market-intelligence/mastermind-terminal, default `master`, app under `terminal/`.
Read the repo's own AGENTS.md / CLAUDE.md (and terminal/AGENTS.md) before your first edit; they bind you.

## Workspace
- Work only in your own isolated worktree on your own NEW branch named `claude/si-<lane>-20261109`, cut from the
  CURRENT default branch (fetch first). Never edit a primary checkout or another session's worktree/branch.
- Terminal lanes are launched as T3 threads in a T3-provisioned checkout. Treat that checkout as a launch point only: mint
  the SSD tree with the helper below (cwd = your launch checkout), EnterWorktree into the printed path and do all work there
  on the branch the mint gives you (that branch name is fine for the PR; the `claude/si-<lane>-20261109` name is preferred
  only where you create the branch yourself). If the helper refuses for this repository, record its stated cause under GAPS
  and continue in the launch checkout on your own new branch — never in the primary checkout.
- If a hook prints "SESSION ROOT QUARANTINE", perform the exact 3-step remedy it prints (SSD mint command, then
  EnterWorktree with the printed path) yourself and continue. That is routine, not a blocker. Never fall back to internal disk.
- If no hook guides you and you are sitting in a primary checkout or a branch that is not yours, mint your own tree:
  `printf '%s' '{"cwd":"<repo checkout you were started in>","name":"si-<lane>","session_id":"<your session id>"}' | python3 ~/.local/lib/mastermind/worktree-storage/worktree_storage.py create`
  then EnterWorktree with the printed path (load EnterWorktree through ToolSearch if it is deferred).
  Terminal primary checkout (never edit it): /Users/chriswong/Documents/Cluade/charting-app
  Macro primary checkout (never edit it):    /Users/chriswong/Documents/Cluade/Macro Dashboard
- Terminal lanes coordinate through /tmp/si_plan/TERMINAL_SLOTS.md (written by the Terminal workspace lane): it names the
  mount props/slots other Terminal lanes plug into. Only the Terminal workspace lane edits
  `terminal/components/sector-intelligence/SectorIntelligenceWorkspace.tsx`, `terminal/lib/sectorIntelligenceLex.ts`,
  `terminal/lib/sectorIntelligence.ts` and `terminal/app/api/sector-intelligence/route.ts`. Every other Terminal lane ships
  path-disjoint files with props-only interfaces and returns the mount hunk / lexicon keys as a SHARED-FILE REQUEST.
- Hooks sometimes reject compound shell commands; split them into plain single commands. Do not wrap `gh` in loops.

## Donor source (other sessions' open PRs) — reuse the code, do not touch the carriers
Port donor code into YOUR branch by exact SHA (`git fetch origin <sha-or-branch>`, then cherry-pick / `git checkout <sha> -- <path>` /
manual port). Resolve conflicts by preserving behaviour from BOTH current default and the donor; never replace whole files by recency.
Never push to, rebase, relabel, mark Ready, merge, close or comment-as-owner on a donor PR.
Donor heads (verified 2026-11-09):
- Terminal #1339 7ded5375caf0aa595ca740bf0df36b175471192e (generation gateway/parser; captured fixture)
- Terminal #1249 abe704f1f1519cc904881fba401a720467049bde (native Cycles/basket components)
- Macro #10780 91add9613ad29dcfb82ff75036dd6519cfc6c06f (generation/API/publisher)
- Macro #10839 3894ea1befb9ffe7f45e3398a1334c6c14b13a51 (sector_dated_context owner)
- Macro #10777 99968fd0533b39410040b01caf51f3e5b050c5be (Cycles wave; conflicting with main)
- Macro #10703 9fc460ff36345387c3a2c5435b079852e8488da0 (D05/regional; HOLD)
- Macro #10707 74930f6931773b23072f91590319dc39fe5a7d07 (dossier cycle component; HOLD)
- Macro #10676 b3cb43f384c94d401977839d00e54d2c0689caed (GMI UI; model01 output is NOT consumable)
- Macro #9124  2b72dc1cd0e0d970434ce37b14aa9898614786f8 (Nuclear; HOLD-FOR-SUCCESSOR-PROOF)

## Hard boundaries (an actual refusal or one of these ends that action — report it, continue other work)
- No merge, self-approval, branch-protection bypass, `--no-verify`, or force-push to anything you did not create.
- No deployment, no `ops/terminal-build.sh`, no production/beta host mutation, no database migration APPLY (source files only),
  no forced nightly/daily pipeline run, no Paper mutation outside the design lane.
- Do NOT edit `.github/ci/legacy-jobs.yml` or `tests/test_ci_pack.py` CI registration (the #10839 proposal is fenced).
- Do not consume, retry or replace the GMI model01 run output. Do not revive Macro #8002. No PLNT native-staging retry.
- No invented data: no fabricated generations, signals, sizing, source text or fixtures presented as real. Existing
  may_rank/may_gate/may_size/may_trade/may_escalate flags stay false. Missing input => explicit unavailable state.
- Never print, log or commit credentials or tokens. No purchases or new paid services.
- Design law: never a coloured left edge / accent stripe on a container; light+dark and EN+ZH for every user-facing surface;
  reuse the existing navigation families, chart helpers and semantic tokens. No engineer text in customer UI.

## Delivery
- Commit in small coherent commits; push your branch; open ONE non-draft PR against the default branch titled
  `feat(sector-intelligence): <lane> …` whose body lists what is real, what is fixture-only, tests run, and residuals.
  Do not add the `merge-on-green` label and do not merge — the COO adjudicates and arms. Do NOT wait for CI: CI is slow and
  unreliable. Run the affected tests locally yourself and paste their real summary lines. A red local test you caused is yours to fix.
- If you are blocked on one item, freeze that item, record it, and finish everything else in the lane.

## Workers (suborchestrators only)
You may start worker subagents through the T3 `delegate_task` tool (call `orchestrator_capabilities` once first) for genuinely
separable, path-disjoint pieces. Default worker: providerInstanceId `capacity_fabric`, model `glm-5.3`. Also authorized:
`grok-4.7`, `gemini-4-argon`, `deepseek-v4.1-flash`, `minimax-m3.1-flash`. Use `claude-opus-5-5` only for one specific hard
piece that a cheaper model demonstrably failed. Never Fable. At most 4 concurrent workers, workers start no children.
Give each worker: exact files it owns, the frozen spec, tests to run, "not done unless" gates, and this charter path.
You integrate and verify what they return — a worker saying "done" is not evidence. If delegation is unavailable, do the work yourself.

## Return (your final message, compact)
STATUS: DONE | PARTIAL | BLOCKED
RESULT: branch, head SHA, PR URL, one-paragraph summary of what now works
EVIDENCE: exact test commands + pass/fail counts; real-versus-fixture statement
GAPS: each unfinished acceptance item with the concrete reason and next action
DEVIATIONS: anything done differently from the brief/packet and why
SHARED-FILE REQUESTS: patches you need another lane's integration writer to apply (exact file + hunk)
