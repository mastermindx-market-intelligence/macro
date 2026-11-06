---
key: TERMINAL-PLAYWRIGHT-RUNS-REWRITE-TRACKED-PROOF-PNGS
claim: >
  In charting-app, several Terminal Playwright specs take screenshots unconditionally into
  TRACKED evidence packet directories under terminal/docs/pr-crops/ (for example
  terminal/e2e/visual-intelligence.spec.ts:80 and :275, chart-object-tree.spec.ts:23,
  pane-sync-time-axis.spec.ts:183 and :199, plus ticker-news, chart-settings-ux,
  dislocations and portfolio-crops specs), so a full-matrix run inside a worktree leaves
  modified tracked PNGs in `git status`; on a Linux host the re-rendered crops differ from
  the macOS-captured committed ones, and the run itself is not a recapture of the packet.
  CI is unaffected because it never commits.
falsifier: >
  In a clean checkout at or after caf202fd5, `cd terminal && git status --porcelain | wc -l`
  (0), then `CI=1 TERMINAL_E2E_PORT=3199 npx playwright test e2e/chart-object-tree.spec.ts
  --project=desktop --workers=1 --retries=0`, then `git status --porcelain -- docs/pr-crops
  | wc -l`. The claim is false if that count is 0 after a passing run on a Linux host, or
  if `grep -n 'screenshot({ path: \`docs/pr-crops' terminal/e2e/*.spec.ts` finds no
  unconditional write (every match guarded by an environment flag). Restore with
  `git checkout -- docs/pr-crops` afterwards.
so_what: >
  A remote or lane worktree that runs Playwright for VERIFICATION must restore the crops
  before it reports (`git checkout -- terminal/docs/pr-crops`, then `git status
  --porcelain | wc -l` = 0), and must never commit PNGs produced on a Linux host. A dirty
  docs/pr-crops after a run is not evidence of a UI change. A packet RECAPTURE is a
  deliberate act on macOS at a named head with its EVIDENCE.yml re-pinned, separate from
  any verification run. Worker packets for remote e2e runs carry the restore step and the
  porcelain-0 end state as an explicit requirement.
kind: landmine
verified_at: 2026-10-12
verified_by: >
  Full-matrix Linux reruns during terminal-enhancements20 of the train-3 head 7733e1b58
  (ubuntu2) and the E07 head 03054a695 (ubuntu0) both reported "Playwright rewrote tracked
  proof PNGs" and had to restore them with `git checkout --` before reaching porcelain 0.
  Spec writes read 2026-10-12 at caf202fd5: terminal/e2e/visual-intelligence.spec.ts:79-80
  (`mkdirSync("docs/pr-crops/terminal-visual-intelligence", ...)` then
  `page.screenshot({ path: ... })` with no guard) and chart-object-tree.spec.ts:22-23
  (same pattern into docs/pr-crops/chart-layers-ux-20260922).
scope:
  - "charting-app"
  - "terminal/e2e/**"
  - "terminal/docs/pr-crops/**"
  - "WS:TERMINAL-ENHANCEMENTS20"
confidence: verified
---

## Grounds

The capture specs double as evidence producers: when a packet is recaptured on macOS the
same spec run writes the crops that the packet's EVIDENCE.yml then pins. Nothing in the
specs distinguishes a recapture from a plain verification run, so every run overwrites
the tracked files. Font rendering and anti-aliasing differ between macOS and Linux, so a
Linux run never reproduces the committed bytes and the worktree shows the crops as
modified even when every assertion passed.

## What a session does with this

- Treat `docs/pr-crops` modifications after a Playwright run as noise to restore, never
  as a diff to review or commit.
- When commissioning a remote verification worker, put "restore docs/pr-crops, end at
  porcelain 0" in its hard rules and read its reported end state; W4 and W6 in the E20
  program did exactly that.
- Related: the Terminal memories `chartpanel-evidence-recapture-gate` and
  `evidence-packet-locks-rot-without-a-gate` (locks pin sources, not crops; a matching
  lock row is not proof the crops are current).
