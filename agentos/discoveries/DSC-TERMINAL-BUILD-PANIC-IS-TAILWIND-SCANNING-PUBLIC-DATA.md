---
key: TERMINAL-BUILD-PANIC-IS-TAILWIND-SCANNING-PUBLIC-DATA
claim: >
  The recurring Terminal deploy panic on `[project]/app/globals.css` (Turbopack
  `PostCssTransformedAsset` -> `reading packet length` / `timeout while receiving message from
  process` / `deadline has elapsed`) was Tailwind v4 automatic source detection reading the build
  stage's hardlinked terminal/public/data farm (about 89k files, 6.1 GB) inside globals.css's single
  PostCSS step, which could then outlast Turbopack's 5-minute loader deadline. The directive
  `@source not "../public/data";` in terminal/app/globals.css (mastermind-terminal#893) removes
  that scan.
falsifier: >
  Delete the `@source not "../public/data";` line from terminal/app/globals.css and run
  `cd terminal && npx vitest run lib/__tests__/tailwindSourceScope.test.ts`. The test runs the real
  `@tailwindcss/postcss` plugin and must go red listing public/data/*.json among the plugin's
  per-file dependency messages. If it stays green, Tailwind is not reading public/data and this
  claim is wrong. On the host, a new /tmp/next-panic-*.log with the same globals.css signature
  would also falsify "removes that scan" if it comes from a build whose `--target-sha` still
  carries the directive (`git show <sha>:terminal/app/globals.css`).
so_what: >
  If the panic recurs, first check that the directive and its guard test survived, or that a
  Tailwind upgrade did not change `@source` semantics, before blaming host load. A plain retry is
  NOT a reliable remedy: two consecutive attempts of the same target failed on 2026-10-09. Waiting
  for a quiet box does not work either, because the 21:30Z nightly runs until about 05:30Z. Any new
  large generated tree under terminal/ needs the same exclusion. No committed ignore file
  covers public/data, and the build stage has no .git, so no ignore rule applies there.
kind: landmine
verified_at: 2026-10-10
verified_by: >
  On 146.190.142.17, `for f in /tmp/next-panic-*.log; do grep -c globals.css $f; done` is nonzero
  for all eight panic logs. At 21:25Z on 2026-10-09, during the second failed attempt, the
  Turbopack loader worker in stage .stage.5SQn9B held fds on public/data/1047.HK.intel.json and
  public/data/1115.HK.slice.json, and its /proc/<pid>/io rchar rose from 687 MiB to 1,383 MiB in
  10 seconds. In a local stage-like tree (a `git archive` of terminal/ with no .git, and the local
  market-data cache cloned into public/data), the scan covered 16,821 files (15,091 of them under
  public/data) without the directive and 1,730 (none under public/data) with it. A CI-like
  checkout produced byte-identical CSS either way.
  terminal/lib/__tests__/tailwindSourceScope.test.ts went red with the directive removed and green
  with it restored (mastermind-terminal#893, merged as 5ad5212113a8ff11a5701f67ad3ea7317ca63dbf).
  Its deploy, `/opt/terminal/terminal-build.sh --target-sha
  5ad5212113a8ff11a5701f67ad3ea7317ca63dbf`, ended `[build] DONE` at about 02:08Z on 2026-10-10
  with no new panic log, and its `.next/trace` `run-turbopack` span took 4.5 minutes.
  `.deployment-id`, the .gitsrc HEAD and the data-dpl-id served on
  https://app.mastermind-x.com/terminal all read 5ad5212113a8ff11a5701f67ad3ea7317ca63dbf.
scope:
  - mastermind-terminal
  - terminal/app/globals.css
  - ops/terminal-build.sh
  - any large generated tree under terminal/
confidence: verified
---

## Mechanism

`globals.css` opened with a bare `@import "tailwindcss";`, so Tailwind v4 ran automatic source
detection from the terminal/ root. Automatic detection skips only what an ignore rule excludes, and
no committed ignore file covers `public/data`. ops/terminal-build.sh builds in
`/opt/terminal/.stage.*/terminal`, which has no `.git`. Its `public/data` is a `cp -al` hardlink
farm of the whole live data directory (see
[[DSC:TERMINAL-DEPLOY-STAGES-PUBLIC-DATA-AS-A-HARDLINK-FARM]]). Tailwind therefore read every file
in it, inside the one PostCSS transform that Turbopack gives a 5-minute reply deadline.

## Why it was intermittent

Good compiles took 5.9 to 7.4 minutes. Three later builds without the fix did not panic. Per the
`.next/trace` span they spent 8.4, 8.4 and 9.1 minutes in `run-turbopack`: b7a3357b0 at 23:20Z on
2026-10-09, then 40e28feee, live at 01:00Z on 2026-10-10, and 59fc7ca28, whose build finished at
01:37Z. The first build with the fix, 5ad5212 at 02:08Z, spent 4.5 minutes there. All four builds
ran during the 21:30Z nightly, so the drop is consistent with the scan being the dominant cost of
that step. The scan only has to push the single globals.css transform past its own 5-minute
deadline. Whether it does depends on page-cache warmth and on how hard the nightly data lane is
using the 2-vCPU host at that moment. A retry can therefore fail the same way, as both attempts on
2026-10-09 did. For the same reason, one clean build without the fix is no evidence that the panic
is gone.

## Evidence summary

- All eight panic logs on 146.190.142.17 have the identical globals.css signature: two on
  2026-09-18, two on 2026-09-25, one on 2026-10-05 and three on 2026-10-09. Check with
  `for f in /tmp/next-panic-*.log; do grep -c globals.css $f; done`.
- During a build, the CSS loader worker held public/data/*.json file descriptors, and its
  `rchar` climbed about 700 MiB every 10 seconds.
- In a stage-like tree, the directive cut the scanned file count from 16,821 to 1,730.
- With the directive, CI-like CSS output is byte-identical. Compared with the deployed CSS, only
  the data-born `.capitalize` utility drops, and no source uses it.
- Both panicking attempts failed before the swap, so live was never touched. The EXIT trap logs
  `pre-swap canonical checkout recovery OK`.
- The fix shipped as 5ad5212 on 2026-10-10. Its build spent 4.5 minutes in `run-turbopack`, no
  panic log appeared, and `.deployment-id`, the .gitsrc HEAD and the served data-dpl-id all read
  5ad5212. Live CSS lost only the data-born `.capitalize` rule.
