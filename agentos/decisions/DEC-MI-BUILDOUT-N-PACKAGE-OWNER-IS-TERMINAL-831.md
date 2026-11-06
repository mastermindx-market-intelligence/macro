---
key: MI-BUILDOUT-N-PACKAGE-OWNER-IS-TERMINAL-831
question: >
  Two Terminal news-server children existed for package N of Mastermind #1258 on 2026-10-06 —
  Astra's #831 (sol/web-ticker-news-r1-20261004-astra-001, created 04:28Z) and this seat's #832
  (claude/mi-n1-ticker-news-server-20261006, delivered 05:09Z). Which one owns the Terminal
  news surface, and what happens to the other?
answer: >
  Terminal #831 owns package N. #832 was closed unmerged as superseded the same hour; its
  branch is kept only as a cherry-pick reference. No further Terminal news lane is launched by
  the #1258 seat; N-package progress is read from #831 and Macro #8454.
rationale: >
  O.16 — a contested artifact freezes and gets one owner, never a second worker. #831 is the
  lawful child of Macro #8454 (its body pins #8454 @ 66ff33ac), predates #832 by 41 minutes,
  covers the same owned paths (terminal/app/api/news/*, lib/newsContract.ts,
  lib/server/tickerNews.ts) plus the panel/rail UI, e2e and crops, and carries a full vitest /
  tsc / build pass. #832 was complete per its own frozen spec (25 tests, T01–T20) but added
  nothing #831 lacked that could merge independently. The collision was a seat error: the
  pre-launch census proved absence on master only, not across OPEN PRs.
alternatives:
  - option: Keep both PRs open and let the Terminal owner reconcile.
    why_not: Two writers on one route family is exactly the state O.16 forbids; neither could merge without conflicting with the other, and it would spend the Terminal owner's time on a collision the seat caused.
  - option: "Rebase #832 onto #831 as a follow-on."
    why_not: "#831 is DRAFT (DO NOT MERGE yet) behind Macro #8454; a stacked child would inherit that hold and duplicate its contract file."
evidence:
  - "Terminal #831: head 1ea7d2ff, +1739/-7, 22 files; body pins Macro #8454 @ 66ff33ac; vitest 461 files / 7,465 tests, tsc/build PASS, 2/2 Playwright (CEO Astra's claims, not re-run by this seat)"
  - "Terminal #832: head 7d4fbf8c, 9 files, 25 tests T01–T20 (seat verified needles); CLOSED unmerged 2026-10-06 05:3xZ; FYI posted on #831"
  - "gh pr list -R mastermindx-market-intelligence/mastermind-terminal --state open --json number,headRefName,files — #831 owned terminal/app/api/news/* 36 minutes before the N1 launch"
affects:
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - terminal/app/api/news/**
  - terminal/lib/server/tickerNews.ts
confidence: high
reversibility: easy
decided_by: "session fd47d431 (Fable Meta-CEO seat, Chairman handoff 2026-10-05 on Mastermind #1258)"
decided_at: 2026-10-06
---

Standing lesson folded into the seat's pre-launch check: before freezing a lane spec, search
OPEN PRs in the target repo by owned path (not only the default branch). Master-absence proves
nothing about in-flight ownership.
