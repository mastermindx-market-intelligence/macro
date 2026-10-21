---
key: FABRIC-LANES-DRAFT-BROWSER-PROOF-THE-SEAT-RUNS-IT
question: >
  When Terminal UI waves are built by fabric lanes on a host with no browser, dev
  server or `next build`, who owns the browser proof — the lane, or the seat that
  integrates its return?
answer: >
  The lane owns the pure libs, components, strings, owner mounts, vitest suites,
  fixtures and a type-checked Playwright draft it does not run; the seat runs every
  draft, corrects draft-only errors, captures the crop packets with the unmodified
  tools, fixes any product defect the crops expose, and judges the return. A lane's
  DONE packet is accepted as source evidence only; browser evidence is always the
  seat's.
rationale: >
  Three of four W3 drafts failed on first run for draft reasons the lane could not see
  (a flow mock answering every `f=` request with the feed and crashing the Watchlist
  rail; loose `getByRole` locators; a cell joiner the table never renders) and one
  crop packet exposed a real layout defect (a nowrap band statement wrapping the belt
  at 1440 and clipping at 390). Neither class is visible without a browser, so the
  division has to be explicit or the packet's "e2e written" line reads as proof it is
  not. Keeping the browser on the seat also keeps the one-dev-server-per-checkout
  constraint (DSC:NEXT16-ONE-DEV-SERVER-LOCK-PER-PROJECT-DIR) in one place.
alternatives:
  - option: Give lanes a browser host and have them run their own e2e
    why_not: >
      The admitted fabric hosts have no browser or dev server; adding one per lane
      multiplies the dev-server lock and the capture-tool sequencing problem across
      hosts the seat cannot inspect.
  - option: Accept the lane's packet as complete and run browsers only at PR CI
    why_not: >
      CI runs the suites but does not review the crops; the belt defect and the
      rail crash would have reached review as green checks with wrong pictures.
evidence:
  - "terminal/docs/OPTIONS_R1_W3_FREEZE.md § Amendments — 'Lane and seat division' and 'W3 lane returns' (2026-10-21)"
  - "Terminal commit 'Run the W3A and W3B browser drafts on the seat and correct their draft expectations' on claude/options-r1-w3-term-1021"
  - "Terminal commit 'Let the Expected Move band statement wrap inside its belt cell and recapture the EOD load-failure packet'"
affects: ["WS:OPTIONS-R1", "terminal/e2e/**", "terminal/docs/pr-crops/**", "terminal/e2e/tools/**"]
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-10-21
---

## Grounds

A fabric return is a pointer to evidence, not evidence. For UI work the discriminating
check is the browser, and the seat is the only place in the current topology that has
one. The packet template therefore asks lanes for a type-checked draft with exact `it`
names and fixtures, and the seat's acceptance step is to run it.
