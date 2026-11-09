---
key: MI-BUILDOUT-N-MERGES-INERT-ACTIVATION-IS-AN-OPERATOR-FLAG
question: >
  Package N of Mastermind #1258 (ticker news) has two halves: Macro #8454 (writer service +
  read-only API) and Terminal #831 (the /api/news proxy routes plus a News tab in the authenticated
  rail). Both carried a seat or author hold. Under the Chairman's 2026-10-07 autonomy directive,
  may the seat release and merge them? If so, on what condition, and what remains gated?
answer: >
  Yes. Merge both, but only once merging cannot change what any user sees. Macro #8454 is inert
  on merge: the writer runs only after an operator installs and enables it, and the API reads
  state read-only and returns 503 until that state exists. Terminal #831 was NOT inert at r2b,
  because its News tab rendered for every signed-in user. It therefore merges only after the r3
  dark-launch: a server-only env flag, TICKER_NEWS_RAIL === "1", read in
  app/terminal/page.tsx and passed down as the newsRailEnabled prop (the HUB_REALTIME_QUOTES
  idiom, no NEXT_PUBLIC twin). The flag gates the tab button, the panel mount and the saved-tab
  restore. Activation is a separate, explicit operator/Chairman act: setting TICKER_NEWS_RAIL=1
  on Vercel, together with source rights, the writer install/enable, a canary, and natural
  sessions.
rationale: >
  "Merge" and "activate" are two different facts on the delivery ladder, and only activation
  needs rights and service authority. Separating them lands the code, lets CI keep proving it
  against main, and removes the drift cost of a long-lived DRAFT, all without granting anything
  the Chairman has not granted. A server-read flag is the house idiom for operator-armed
  Terminal features. A NEXT_PUBLIC twin would put a second switch in play that could drift
  from the server's.
alternatives:
  - option: Keep #831 PARKED until rights and Macro service enablement land.
    why_not: "Leaves a 22-file DRAFT drifting against master with no proof it still composes; the hold was protecting users from an ungated tab, which the flag closes."
  - option: Merge #831 as-is (r2b) and rely on the Macro API returning 503.
    why_not: "A visible tab showing an error state to every signed-in user is a user-facing change, not an inert merge."
  - option: Gate on a client NEXT_PUBLIC_ flag.
    why_not: "Two switches (client + server) can drift; the repo's existing operator flags are server-read and prop-passed."
evidence:
  - "Terminal #831 r3 head 3e3a9c9e665a198e55d745d11078603f33403b9b: 5 files (page.tsx, TerminalShell.tsx, playwright.config.ts, tickerNewsRailMount.test.ts, EVIDENCE.yml sha re-pin); seat read the diff — 3/3 prop passes, tab/panel/savedTab guards"
  - "lane mi_n_b_terminal_p3_flag return: vitest 472 files / 7732 passed, tsc 0, playwright e2e/ticker-news.spec.ts 5 passed; mutation removing the tab guard fails the new regex assertion"
  - "Macro #8454 merge head 6db905f634a17e617bf15e4cd1cb5f68a28e7744: writer not installed by merge; API read-only, 503 without state"
affects:
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - terminal/app/terminal/page.tsx
  - terminal/components/TerminalShell.tsx
confidence: high
reversibility: easy
decided_by: "session fd47d431 (Fable Meta-CEO seat; Chairman autonomy directive 2026-10-07)"
decided_at: 2026-10-07
---

To activate, the operator sets `TICKER_NEWS_RAIL=1` in the Terminal's Vercel environment, but
only after the Macro writer is installed and enabled under granted source rights and a canary
has passed. To roll back, unset the variable: the tab, the panel and any saved News tab all
disappear on the next render. No code revert is needed.
