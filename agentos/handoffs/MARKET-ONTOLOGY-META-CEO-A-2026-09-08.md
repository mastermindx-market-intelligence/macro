---
workstream: WS:MARKET-OS
session: claude/marketontology-meta-ceo-a-handoff-20260908 (Meta-CEO A, Claude8 Code session 5b29ad85-0490-42c8-b5e4-1e32b1922014)
model: fable
ended_because: context_budget
mission: >
  Successor handoff for the Meta-CEO A seat of the Market Ontology program
  (Chairman override 2026-09-05/06, DEC:CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06,
  charter research/MARKET_ONTOLOGY_META_CEO_CHARTER_2026_09_06.md, coordination
  carrier macro#6819). Written so that a fresh Claude Code session on ANY
  Claude account, on this Mac, can take over the seat in one paste and
  continue the same work: finish the five-PR "Macro Command" stack
  (P1 #6930 -> P2 #6937 -> P3 #6982 -> P4 #6983 -> P5 #6985) through review,
  merge and live verification; merge the armed Half-A backlog on concluded
  green; then the post-merge cleanup PR. Nothing here is a permission
  request: the override already grants autonomous execution under fleet law.
state_before: >
  At 2026-09-08 12:40 PDT the Half-A program state is: P3 #6982 (head
  dd34c08e72e7) and P4 #6983 (head 9245ff07094f84be6cddbd17ef2cfb5f33d03a4b)
  are REVIEW-COMPLETE drafts (pass comments 5588657369 and 5590072822);
  P2 #6937 (head b43f0ec76584, base = P1 branch) is review-passed and
  unarmed, waiting for P1; P1 #6930 (head 0a60b2ac44b7) is armed
  merge-on-green with ci.yml run 34235604181 executing the FULL suite
  (.github/ci/legacy-jobs.yml changed) with 0 reds after 5h on the shared
  3-runner pool; P5 #6985 (head 901972dde11b152c80428b888158295f55c63ece,
  capture 269c393b, frames 5c140b80, on P4 9245ff07) failed round 8 in both
  halves on ONE remaining major (the 48 chip-material crops do not contain
  the analyst chip because the scroll was applied to .mq-suitenav-rail,
  which is not the scroll container) plus two content defects the frames
  exposed (raw 16-digit floats in user copy; untranslated ZH component
  chips); the v9 Cursor worker was launched at 12:34 PDT on the P5
  worktree with fix_prompt_p5_v9.md. Nine Half-A PRs merged by hand today
  on concluded green (#6936 #6935 #6931 #6932 #6911 #6901 #6897 #6908
  #6900). The Chairman-authorized Codex containment ("Restore M2 fleet
  throughput", task 01a0763f-08f8-7971-aed7-e023c92c080a) is STILL IN FORCE
  (no lift message): no new heavyweight worktree/materialization/test/build
  fan-out, no killing or suspending workers, no edits to
  .claude/hooks/worktree_create_sparse.py, no mutation of the shared primary;
  interpretation in force = serial Cursor workers, at most 4 concurrent
  workers+reviewers, reuse the existing worktrees.
changed:
  - path: agentos/handoffs/MARKET-ONTOLOGY-META-CEO-A-2026-09-08.md
    what: this successor handoff (new file)
  - path: /Volumes/Mastermind/agent-workspaces/claude/handoffs/macro-command-meta-ceo-a-2026-09-08/
    what: >
      off-repo durable bundle (SSD, same Mac): HANDOFF.md (copy of this file),
      review_commission_template.md (the Opus CODE-half / EVIDENCE-half review
      commissions), and scratch/ holding every P3/P4/P5 rulings file, fix prompt,
      prompt composer, review verdict, claims body/comment, the worker launcher
      launch_fix_worker_custom.sh, worker_p5_v8.log and
      followups_macro_command_stack.md. The session scratchpad these came
      from dies with the session; the bundle does not.
verified:
  - claim: "#6900 merged by hand on concluded green"
    command: "gh pr view 6900 -R mastermindx-market-intelligence/macro --json state,mergedAt,mergeCommit"
    result: "MERGED 2026-09-08T19:36:08Z ad021359a0f3; rollup non-pass were only Vercel FAILURE and ci-authority/codex/merge-queue-pilot FAILURE; release_hold_text dry-run held_before=null"
  - claim: "P5 round-8 EVIDENCE verdict is FAIL 0/1/4/1 with dual-theme design PASS dark + PASS light"
    command: "cat scratch/review_pr6985_r8_evidence.md (bundle); reviewer agent a73b0273196ea6004 final message"
    result: "MAJOR-1 railScrollLeft 0 on 48/48 and crop_selector .mq-suitenav-rail on 48/48; MINOR-1 identical selectors; MINOR-2 one railInnerHtmlSha256 value; MINOR-3 raw floats; MINOR-4 untranslated ZH chips; NIT-1 0x0 wording"
  - claim: "P5 v9 Cursor worker is running on the P5 worktree at HEAD 901972dd"
    command: "git -C /Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/mo-macro-command-p5-2ba4f52b1085d92f rev-parse HEAD; pgrep -fl cursor-agent | grep -c .; head -1 scratch/worker_p5_v9.log"
    result: "901972dde11b152c80428b888158295f55c63ece; 23 cursor-agent processes; start line stamped Tue Sep 8 12:34:34 PDT 2026"
  - claim: "fix_prompt_p5_v9.md carries the v9 rulings, the 901972dd lease twice, no rebase step and no unescaped {plan}"
    command: "python3 compose_p5_v9.py <scratch>"
    result: "wrote fix_prompt_p5_v9.md 15262 lease 2 stale 0 plan-brace 0"
  - claim: "Open-PR census used for the tables below"
    command: "gh pr list -R mastermindx-market-intelligence/macro --state open --limit 80 --json number,headRefOid,baseRefName,isDraft,labels,mergeable"
    result: "taken 2026-09-08 ~12:31 PDT; #6830 is OPEN (gh pr view 6830 --json state), it was merely cut by the 80-row limit"
unverified:
  - claim: "The ~13 gh run watch watchers and the Cursor worker survive the end of session 5b29ad85"
    what_would_verify: "pgrep -fl 'gh run watch' and pgrep -fl cursor-agent from the successor session; if absent, re-arm per next_actions step 1"
  - claim: "A docs-only PR carrying this handoff triggers no pack checks and may be admin-merged"
    what_would_verify: "gh pr checks <handoff-pr> after ci-plan concludes; if packs were scheduled, wait for them instead"
  - claim: "The account-local memory file ~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/memory/chairman-override-claude-meta-ceo-regime-2026-09-06.md is visible to a session on another Claude account launched on this Mac from the same project"
    what_would_verify: "ls that path from the successor; the handoff does not depend on it"
unresolved:
  - "P5 #6985 round 9: worker running; needs r9 CODE + EVIDENCE Opus reviews, then rulings v10 or REVIEW-COMPLETE."
  - "P1 #6930 ci.yml 34235604181 still executing; the whole stack's merge order is gated on it."
  - "#6913 and #6981 are CONFLICTING on main (armed but unmergeable) - rebase lanes needed; #6872 is CONFLICTING + merge-blocked (F04-X1)."
  - "#6898 (A-F10-1) is stacked on #6830's branch; retarget + hold release + arm only after #6830 merges."
  - "#6986 and #6987 were opened by the two operator-started background sessions (sanctions_map capture IIFE; freshness chips vs ZH swap); Meta-CEO A has not reviewed them - inspect before arming/merging."
  - "Codex containment has no lift message - keep serial workers and the 4-concurrent cap until Chris says otherwise."
next_actions:
  - "0. BOOTSTRAP (successor, any account): open a fresh session on this Mac (desktop app worktree under Macro Dashboard, or a claude/<task> worktree off origin/main via the SSD storage helper); paste the SUCCESSOR PROMPT in the body of this file; read this file, the SSD bundle, agentos/decisions/DEC-CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06.md and the charter; do NOT re-ACK or re-open macro#6819 - post one continuity note there naming the new session uuid only when you first act."
  - "1. RE-ARM WATCHERS if pgrep shows none: for each armed PR in the table run exactly one `gh run watch <run-id> -R mastermindx-market-intelligence/macro --interval 120 --exit-status > <scratch>/watch_<pr>_<run>.log 2>&1 &` (run ids: 6930/34235604181, 6910/34250916958, 6830/34209707472, 6896/34212578241, 6899/34195809414, 6912/34193375825, 6913/34196770081, 6928/34203588178, 6929/34205270377, 6933/34194302118, 6984/34207693143) and one Bash waiter or Monitor on the log directory; never poll gh inside 300 s."
  - "2. P5 v9: wait for `exit=` in worker_p5_v9.log (bundle scratch/ or the successor's own log). On exit=0 with a new pushed head: spawn the r9 CODE and EVIDENCE Opus `reviewer` agents from review_commission_template.md (update head/capture/frames shas and the verdict file names review_pr6985_r9_{code,evidence}.md); on FAIL write rulings_p5_v10.md (code half + evidence half), compose fix_prompt_p5_v10.md from compose_p5_v9.py (lease = new head; STEP 0 = confirm HEAD + merge-base 9245ff07, no rebase), launch `bash launch_fix_worker_custom.sh cursor 6985 claude/marketontology-macro-command-p5-20260908 <P5 worktree> fix_prompt_p5_v10.md > worker_p5_v10.log 2>&1 &` with a fresh waiter; on PASS/PASS post the review-pass comment (pattern: scratch/pr6983_review_pass_r11.md) and mark REVIEW-COMPLETE. On a worker exit=1 within seconds the prompt file was missing - relaunch under a NEW log name."
  - "3. P1 #6930 on CONCLUDED green (watcher exit=0): hand-merge check (`gh pr view 6930 --json statusCheckRollup` - only `Vercel FAILURE` and `ci-authority/codex/merge-queue-pilot FAILURE` may be non-pass; `python3 .claude/workflows/release_hold_text.py 6930 --ceo A --dry-run` -> held_before null) then `gh pr merge 6930 -R mastermindx-market-intelligence/macro --squash`."
  - "4. Then P2 #6937: `gh pr edit 6937 -R ... --base main`; `python3 .claude/workflows/release_hold_text.py 6937 --ceo A` (dry-run first); confirm merge-on-green label; arm one watcher on its new ci.yml run; merge on concluded green by the step-3 check. Then P3 #6982 -> P4 #6983 -> P5 #6985 the same way, each retargeted to main only AFTER its parent merges (retargeting earlier makes the PR diff carry the parent's commits)."
  - "5. Live verification after each merge of the stack: the VPS pulls main every ~3 min; `curl -s https://<live host>/macro_monetary.html | grep -c 'mc-rail'` (P1 shell) and the section anchors for P3/P4; the render lane re-stamps `?v=` later - a plain-copy pair needs no render."
  - "6. Every other armed watcher that concludes green: step-3 check then merge. #6830 merged -> `gh pr edit 6898 --base main` + release_hold_text 6898 --ceo A + arm + watcher. #6913/#6981 CONFLICTING: a Cursor rebase lane per PR (prompt pattern scratch/fix_prompt_6898_v6.md: fetch, rebase onto origin/main, resolve keeping both sides' entries, run the PR's own tests, push --force-with-lease with `${VAR}:` colon-escaping in zsh)."
  - "7. After the stack merges: one cleanup PR from scratch/followups_macro_command_stack.md (P3 dpr threading + joinable declared matrix; P4 {**extra} pass-through + boundary contract test, new_probe pins, writer dup-byte guard, E5 rows through _state_row, _visible_blob void-with-class, fadeVisualReason exemplar; #6929 n5, #6984 docstring, #6896 series-key fallback) - one Cursor builder, one Opus review, merge on green."
  - "8. Wave boundary: update this handoff's successor (new dated file, never edit this one), post the continuity note on macro#6819, append a dated line to the memory file if it is reachable."
do_not_redo:
  - "Do not re-review P3 #6982 (r16 PASS/PASS) or P4 #6983 (r10 evidence PASS + r11 code PASS): both are REVIEW-COMPLETE; the remaining follow-ups are already in followups_macro_command_stack.md."
  - "Do not re-parent P5 onto anything: P4 v11 9245ff07 is FINAL; P5 rounds are tests/scripts/templates on the P5 branch only."
  - "Do not accept a chip-material crop that does not visibly contain the analyst chip AND a real neighbouring pill (r6 fabricated pill, r7 mutated rail, r8 chip outside the crop were all rejected); do not accept a synthetic control produced from literal numbers; do not accept a collision predicate that cannot RAISE (one hash value across all cells)."
  - "Do not merge with `gh pr merge --auto` (no branch protection: merges immediately, kills the PR's proof run) and do not merge on a pending check; only the two named non-pass contexts (Vercel; ci-authority/codex/merge-queue-pilot) are ignorable."
  - "Do not arm, disarm, retarget or merge Half-B PRs (#6904-#6909, #6918-#6927, #6957-#6966, #6981 and any [MO-BB*]/[MO-BA-spare] title): they belong to Meta-CEO B (Claude3; agentos/handoffs/MARKET-ONTOLOGY-META-CEO-B-2026-09-06.md)."
  - "Do not touch Sol-era HOLD-FOR-SOL PRs outside the Market Ontology regex (#6870 #6871 #6877 #6893 #6915 #6917 #6941 #6945 #6951 #6976 #6990 #6992 ...): the override covers the MO program only."
  - "Do not re-run the failed-launch diagnosis: `exit=1` within seconds of launch = missing prompt file (`Error: No prompt provided for print mode`); fix the composer and relaunch under a new log name."
  - "Do not dispatch `gh workflow run ci.yml --ref main` over a live main baseline (livelock); preflight for in-flight runs first."
  - "Do not spawn Opus/Sonnet builders for fixes: Cursor CLI workers are the fix lane (Chairman 09-07 external-CLI-lanes order); Opus `reviewer` agents remain the review lane; the Fable main loop adjudicates and merges."
danger_areas:
  - "Evidence law: a scripts/, templates/ or lib/ edit after the capture commit VOIDS the capture (recapture required); the manifest's capture_sha must equal the head at capture time with a clean tree; frames commit after the code commit."
  - "The P5 rail scroll: .mq-suitenav-rail is NOT the horizontal scroll container; the worker must find the ancestor with overflow-x auto/scroll and scrollWidth > clientWidth and read scrollLeft back from it (v9 ruling M1)."
  - "zsh: `$VAR:e`/`$VAR:r` are history modifiers - always `${VAR}:` in refspecs and --force-with-lease."
  - "`git fetch origin pull/N/head:refs/pr/N` into an existing ref keeps a STALE head after a force-push: always `fetch -f` and assert the sha before extracting a PR tree for review."
  - "Shared GitHub quota: one watcher per run at --interval 120; a Stop-hook block is answered with a one-line hold note, never a fresh poll; three identical bucket counts in a row means stop polling."
  - "Sparse worktrees: the P3/P4/P5 SSD worktrees are opted into site/ + mockups/ (`python3 scripts/worktree_sparse.py status`); never `git add -A` a data/ diff; a write into an omitted tree truncates the committed artifact."
  - "Reviewer agents sometimes lack the Write tool (r8 evidence half): the verdict then lives only in the agent's final message - copy it into the verdict file yourself before compaction."
  - "The user performs all logins (Cursor, Grok, GitHub); never enter credentials; if `cursor-agent` returns auth errors, ask the user to re-login and wait."
prs: [6930, 6937, 6982, 6983, 6985, 6910, 6830, 6898, 6896, 6899, 6912, 6913, 6928, 6929, 6933, 6984, 6986, 6987, 6900]
decisions: ["DEC:CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06"]
---

# Meta-CEO A successor handoff — 2026-09-08 12:40 PDT

## SUCCESSOR PROMPT (paste as the first message of the new session, any Claude account)

```
You are Meta-CEO A for the MarketOntology program in mastermindx-market-intelligence/macro under the Chairman override of 2026-09-06 (DEC:CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06; ChatGPT "Sol" relieved; no permission asks; fleet law binding; ultracode on). Session 5b29ad85 handed the seat to you at context budget. Read in this order, then continue next_actions step by step without re-asking anything:
1. agentos/handoffs/MARKET-ONTOLOGY-META-CEO-A-2026-09-08.md (origin/main, or branch claude/marketontology-meta-ceo-a-handoff-20260908 if not yet merged)
2. /Volumes/Mastermind/agent-workspaces/claude/handoffs/macro-command-meta-ceo-a-2026-09-08/ (HANDOFF.md, review_commission_template.md, scratch/)
3. agentos/decisions/DEC-CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06.md and research/MARKET_ONTOLOGY_META_CEO_CHARTER_2026_09_06.md
4. ~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/memory/chairman-override-claude-meta-ceo-regime-2026-09-06.md if it exists
Rules of the seat: Cursor CLI workers fix (launch_fix_worker_custom.sh), Opus `reviewer` agents review (CODE half + EVIDENCE half), you adjudicate, merge by hand on concluded green, verify live. Codex containment is in force: serial workers, at most 4 concurrent workers+reviewers, reuse the existing worktrees, never edit .claude/hooks/worktree_create_sparse.py. Post one continuity note on macro#6819 naming your session uuid when you first act. Start with next_actions step 1 (re-arm watchers) and step 2 (P5 v9).
```

## Stack state (Macro Command, Chairman product directive: one plain-word dashboard page)

| PR | Role | Head | Base | State at 12:40 PDT |
|---|---|---|---|---|
| #6930 P1 | shell, left rail, hash routing, tokens, copy guard | 0a60b2ac44b7 | main | ready, armed, ci.yml 34235604181 executing full suite (0 reds), watcher log watch_6930_34235604181.log |
| #6937 P2 | The Read + state strip | b43f0ec76584 | claude/marketontology-macro-command-p1-20260906 | review-passed (r3), NOT armed, retarget after P1 merges |
| #6982 P3 | panel contract + Overview + first five sections | dd34c08e72e7 | P2 branch | DRAFT, REVIEW-COMPLETE r16 (comment 5588657369) |
| #6983 P4 | seven remaining sections | 9245ff07094f84be6cddbd17ef2cfb5f33d03a4b | P3 branch | DRAFT, REVIEW-COMPLETE r11 (comment 5590072822); evidence accepted at capture 544cdb47 / frames 3f0fee11 |
| #6985 P5 | copy-law sweep, analyst polish, evidence | 901972dde11b152c80428b888158295f55c63ece (v8) | P4 branch | DRAFT, r8 CODE FAIL 0/1/3/2 + EVIDENCE FAIL 0/1/4/1, design PASS/PASS; v9 worker running |

Worktrees (reuse; do not mint new ones under containment):
- P1 `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/macro-command-p1`
- P2 `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/macro-command-p1b`
- P3 `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/mo-macro-command-p3-8141e782a969409c`
- P4 `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/mo-macro-command-p4-91f3ca0c1058cefa` (branch claude/marketontology-macro-command-p4-20260908)
- P5 `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/mo-macro-command-p5-2ba4f52b1085d92f` (branch claude/marketontology-macro-command-p5-20260908)

## P5 round-9 rulings in force (bundle scratch/rulings_p5_v9.md; the worker prompt is fix_prompt_p5_v9.md)

- M1: find the REAL horizontal scroll container (ancestor with computed overflow-x auto/scroll AND scrollWidth > clientWidth; record scrollContainerSelector), scrollIntoView the chip, read scrollLeftBefore/After back from that container, crop the container's visible box intersected with chip-union-pill (pad <= 12 px), RAISE unless the re-read analystBox and the sibling pill box are both inside the crop (python recompute 48/48; element_text_head contains the chip label); chipmatPairFits:false fallback crops the chip alone; re-evaluate collision groups.
- m1 synthetic partial control from a real partially covering synthetic DOM (no literal fallback, truthful source); m2 record scrollResult and RAISE on ok:false; m3 identifying selectors + visible text, chip != pill; n1 remove the residual pytest.skip; n2 EN/ZH difference on a MEASURED value.
- E-m2 cropDomSha256 over the outerHTML of every element intersecting the final crop (state classes included), collision ratified only with matching cropDomSha256 + theme + locale + width, RAISE on identical bytes with different DOM hash.
- E-m3 plain-number formatting at the builder/renderer boundary (2 decimals for momentum/z, 1 decimal + unit for percentages) plus a rendered-page test over every section EN+ZH failing on >= 4 fractional digits or an exponent; check_macro_command_copy.py gains the rule.
- E-m4 ZH labels for component chips (订单 / 生产 / 库存 via the mechanism that owns sibling chips) plus the ZH parity test extended to sub-chips across all 12 sections and both hubs.
- E-n1 "w x 0 token host (measured 362 x 0)". Full 212-cell recapture at one committed clean tree. DONE lines name receipt VALUES.

## Other Half-A PRs (armed = merge-on-green label; merge by hand on concluded green after the step-3 check)

| PR | Title (short) | Head | Watcher run | Note |
|---|---|---|---|---|
| #6910 | A-MO-W2-3 premarket orientation producer | 91ec4a16a428 | 34250916958 | armed + merge-blocked label (stale); fresh full-suite run in flight |
| #6830 | F10-X1 implication cards | (see gh) | 34209707472 | armed; #6898 stacked on it |
| #6898 | A-F10-1 prereg chip + hub entry | 9ed77cf88619 | none | DRAFT on #6830's branch; retarget + release + arm after #6830 |
| #6896 | A-F05-1 event-to-asset impact | ac3c740429d7 | 34212578241 | armed |
| #6899 | A-F02-1 base map + OFAC overlay | 44519bd31d5e | 34195809414 | armed |
| #6912 | A-MO-W2-1 indicator library breadth | 5864ed47074c | 34193375825 | armed |
| #6913 | A-F02-W2-1 owner/source/rights map | 80dad650f277 | 34196770081 | armed, CONFLICTING - rebase lane |
| #6928 | A-F02-W2-3 second-country political desk | ee44a20a67cd | 34203588178 | armed |
| #6929 | A-F04-W2-1 GMI exposure composer | 6238fec09fd8 | 34205270377 | armed |
| #6933 | A-F02-W2-2 Japan dossier | 9fccb9bc022a | 34194302118 | armed |
| #6984 | engine(workspaces) prior = previous publication | 697624c2bbed | 34207693143 | armed |
| #6986 | fix(evidence) capture seed IIFE; sanctions_map | 17ea9d4fa12a | none | opened by an operator-started background session; not reviewed by A |
| #6987 | theme: freshness chips vs ZH swap | 4e689967751d | none | armed by its own session; not reviewed by A |

Merged today by hand: #6936, #6935, #6931, #6932, #6911, #6901 (413e1f93), #6897 (31ac6bf3), #6908 (dd1dbfb9), #6900 (ad021359).

## The loop (how every round runs)

1. Worker: `bash launch_fix_worker_custom.sh cursor <pr> <branch> <worktree> <prompt.md> > worker_<x>.log 2>&1 &` and a waiter `until grep -q 'exit=' worker_<x>.log; do sleep 45; done`. Cursor prints only at the end; "Connection lost, reconnecting" lines are benign. The launcher aborts if the worktree is on the wrong branch.
2. Prompt composer: copy compose_p5_v9.py; replace TASK (`^TASK:.*$`), the RULINGS block (`^RULINGS \(.*?(?=^HOUSE LAWS)`), STEP 0 (`^STEP 0 \(mandatory\):.*$`), the lease sha (assert count == 2 before, 1 after the STEP 0 swap), the commit-message regex; assert no unescaped `{plan}` inside an f-string.
3. Review: two Opus `reviewer` agents (ROUTE: review) from review_commission_template.md - CODE half attacks the diff and tests at the exact head; EVIDENCE half attacks the committed bundle (manifest, probes, PNG IHDR bytes via `git show refs/pr/N:<png>`) and adjudicates both themes as designs. Extraction: `git fetch -f origin pull/N/head:refs/pr/N` then `git archive refs/pr/N templates scripts tests lib config .github contracts mockups/evidence/macro-command-p5 site/macro_monetary.html | tar -x -C /tmp/rN`; design ratchet via `python3 scripts/check_design_system.py --mode enforce-added --diff-file <base..head diff>`.
4. Rulings: one file per round (code half + evidence half), every finding gets FIX/RAISE semantics and a receipt VALUE the DONE line must name.
5. Merge: only on concluded green; hand-merge check; `gh pr merge <n> --squash`; then retarget the child, release its hold with release_hold_text.py, arm, watch.

## Pointers

- Bundle: `/Volumes/Mastermind/agent-workspaces/claude/handoffs/macro-command-meta-ceo-a-2026-09-08/`
- Memory (account-local, may or may not be visible): `~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/memory/chairman-override-claude-meta-ceo-regime-2026-09-06.md`
- Meta-CEO B: `agentos/handoffs/MARKET-ONTOLOGY-META-CEO-B-2026-09-06.md`; carrier macro#6819.
- Follow-ups after the stack merges: bundle `scratch/followups_macro_command_stack.md`.
