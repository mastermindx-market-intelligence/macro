---
key: TERMINAL-GLOBALS-CSS-EDIT-RELOCKS-THREE-EVIDENCE-PACKETS
claim: >
  Any edit to terminal/app/globals.css, even one added token line, invalidates the sha locks of three
  evidence packets under docs/pr-crops (conductor-fit-badge-zh, eod-heatmap-flowdesk-load-failure,
  gex-levels-heatmap-load-failure), and any edit to terminal/components/gexdesk/GexDeskView.tsx invalidates
  the last two; either turns the Terminal unit job red until each packet is recaptured with its own dev
  server, one packet at a time. The locked-file set is only discoverable by grepping every
  docs/pr-crops/*/EVIDENCE.yml for the branch's changed files, not from the suites near the change.
falsifier: >
  On a branch that touches terminal/app/globals.css run `cd terminal && npx vitest run
  lib/__tests__/conductorFitBadgeZhEvidence.test.ts lib/__tests__/eodHeatmapFlowdeskLoadFailureEvidence.test.ts
  lib/__tests__/gexLevelsHeatmapLoadFailureEvidence.test.ts` before recapturing; the claim is refuted if all
  three pass with the stale EVIDENCE.yml, or if Terminal PR 1098 commit 20825722f ("Recapture the three
  evidence packets that lock app/globals.css") was not needed to turn that job green.
so_what: >
  Budget a recapture cycle whenever a slice adds a global token. Prefer module-local tokens with a
  globals fallback (the exposure slices use --ex-positive / --ex-negative / --ex-gold in their CSS
  modules) so a palette addition does not relock unrelated packets, and run the recaptures serially
  because Next 16 allows one dev server per project directory.
kind: landmine
verified_at: 2026-10-21
verified_by: >
  Terminal PR 1098, commit 20825722f (three EVIDENCE.yml files and their PNGs changed); the red
  "Terminal typecheck + tests" run on the earlier head 2026-10-21T12:58Z that the merge sweeper reported.
scope:
  - terminal
  - "terminal:terminal/app/globals.css"
  - "terminal:docs/pr-crops"
  - "terminal:terminal/components/gexdesk/GexDeskView.tsx"
confidence: verified
---

## Exact observed boundary

PR 1098 added one line to `terminal/app/globals.css` (`--exposure-positive`, `--exposure-negative`,
`--exposure-selected`). The three Evidence tests compare the packet's recorded source shas, which include
`app/globals.css`, against the working tree; they failed on the first head and the sweeper labelled the PR
`merge-blocked`. Recapturing each packet (its capture script starts a dev server) rewrote the EVIDENCE.yml
shas and PNGs; the job went green on head 20825722f.

## Second observed boundary (2026-10-22)

Terminal PR 1116 changed one prop line in `terminal/components/gexdesk/GexDeskView.tsx`
(`onLoadSession={loadSession}`). The local gate subset (exposure, replay and projection suites) was green,
but the CI unit shard failed `eodHeatmapFlowdeskLoadFailureEvidence` and `gexLevelsHeatmapLoadFailureEvidence`
with "GexDeskView.tsx changed without a recapture" at head 9ef0160bb. Both packets were recaptured with their
capture tools (126 + 114 crops; 12 + 12 changed by one relative-age digit) and the job went green on head
bb68cd7d8 (CI run 39729631520 green, merged 06:31Z). Falsifier for this boundary: a branch that edits GexDeskView.tsx and passes both gates with
the stale EVIDENCE.yml refutes it. Pre-push census that would have caught it before CI:
`for f in $(git diff --name-only origin/master...HEAD); do grep -l "$f" docs/pr-crops/*/EVIDENCE.yml; done | sort -u`
and run the gates those packets name.

## Not claimed

This does not say the packets are wrong to lock globals.css: they prove rendered pixels, and a palette
change can legitimately change them. It says the cost is real and must be scheduled.
