# D08 — Options integration visual continuation (3 Nov 2026)

Status: **SPEC_ONLY / PARTIAL**. Governing semantic interface remains **D08-OPTIONS/1.0.0** at `d0516e1bad9cb5982d43d20c4167d0355cb70e2c`; this document does not change the frozen D08A–D08D exchange. Source scope: existing D08 Draft #10649, not a new design session or implementation owner. D08A–D08D have not been dispatched by this continuation.

## First-glance candidate

Lead with **Options / exact root / what changed?** rather than a second explanatory landing page. The first viewport contains a named observation date and an independent earlier-research date, a three-metric qualified comparison, a single selected data object, and one accessible evidence panel. Keep the source/coverage warnings adjacent to affected figures. Make **Research · No execution** explicit. Advanced panes remain discoverable through a named **All 15 views** picker; six frequent tasks—Desk, Flow, Exposure, Volatility, Plan, Replay—may receive quick tabs but must not replace Tape, Tide, 0DTE, Largest, Tickers, Scanner, Structure, Statistics or Prophet.

The standalone demonstrator uses an **illustrative** SPY gamma comparison (Oct 30 → Nov 02, -18.0M → -11.5M; signed change +6.5M) from the previous design fixture; it is not fresh or traded market data. It intentionally distinguishes *transport connected*, *book date*, *spot date*, *research source date*, *matched strike population* and *source error*. It does not treat a matrix cell as an option contract pin or a Plan payoff as an order.

**Desktop composition.** Use the provisional F01/F02 dimensions at 1440: 224px global rail, 64px header, 24px outer gutters, 1168px usable host, 320px evidence inspector +24px gap, leaving 824px primary. The inspector never stacks with a second modal; selection replaces its content. At 1024 expanded, primary is 788px, so evidence opens as an overlay. These are calculated candidate widths, not a qualified joint shell or measured reflow.

**Phone composition.** At 390px, global rail is absent, with one instrument title, dated source receipt, two primary values then matched count, scroll-contained strike data, a visible complete-row alternative and a Views control. The evidence overlay traps focus, closes by Escape and returns focus to the activating row when available. Never clip a metric (observed on existing Exposure R2 1HL2-0), never invent a tap-hover dependency, and never silently drop less-frequent panes. EN/ZH and dark/light are supported as design variants, not as verified native runtime compliance.

## Interaction prototypes and testability

A detached, self-contained HTML **review prototype** was authored in this session (local conversation artifact; not a GitHub source file or Paper export). It contains: six primary tabs; a 15-view picker that explicitly marks unimplemented specialist views as *retained native*, rather than falsely presenting Desk; selectable strike evidence; dated/partial/empty/source-error state labels; an equity replay entitlement gate; a draft-only Plan with Save disabled; local back-to-filtered-tape return; a mobile evidence sheet; focus restoration and Escape; light/dark and EN/ZH toggles. No real fetch, save, auth, replay stream, trade execution or deployment is wired.

Static source checks **10/10 PASS**: JS syntax through installed Node, unique HTML IDs, primary tab count, native-view disclosure, disabled save, replay entitlement text, four named data states, dialog semantics, independent clock text and full-view manifest. No browser interactions were verified. Chromium's local file navigation returned `ERR_BLOCKED_BY_ADMINISTRATOR`; do not claim browser screenshots, accessibility passage or measured responsiveness.

## Real Paper status and effect fence

Using the accepted direct **Mastermind Paper** connection, `get_basic_info(fileId=01M3NSZGE8JWN2EZCSF0DT05RM)` confirmed a write-bound Terminal file and the incumbent Options directory on page **p-2-0**, with existing predecessor artboard **KQ3-1**. A disjoint new artboard **1N2L-0**, `D08 · Options Command · Desktop Dark · Integration V1 candidate`, was created on p-2-0 with operation `d08-paper-create-desktop-20261103-01`, `APPLIED_RESPONSE_OBSERVED`. The next `write_html` content operation was stopped by a **platform safety check prior to a Paper edit response**. Exact-target `get_tree_summary` then confirmed **1N2L-0 remains an empty 1440×900 Frame**. No HTML, mobile board, new tokens, cross-page move, deletion, or after screenshot was applied. Do not retry or route that blocked write through Studio, RDC, another account, or a differently packaged equivalent. Keep the empty board explicitly NOT_ACCEPTED; do not use it as an accepted design reference.

## Inherited source boundaries

- D08A: observational prints, flow source/side quality, exact filter and row return; existing Brief writer [#10494](https://github.com/mastermindx-market-intelligence/macro/pull/10494) retains its five Paper boards and release checks. D08 source-linked stale/mixed-root finding delivered in its PR Conversation.
- D08B: reported gamma, signed matched change, source-date/coverage, 3D accessible exact-table fallback. The representative 390px R2 board clips the third KPI; preserve W1's date/denominator treatment.
- D08C: exact pin/draft/payoff, but **no saved Investigation** until D23/native save→readback→reopen admits the current owner. Operator Issue Desk and D22 holdings never follow from a consumer research button.
- D08D: futures ES/NQ and IEX equity depth are different data and entitlement subjects; closed request grammars and originating return states must survive.
- F01: global shell, active destination, rail, one overlay. F02: shared number, data state, table/inspector anatomy. At this checkpoint [F01 #10645](https://github.com/mastermindx-market-intelligence/macro/pull/10645) and [F02 #10630](https://github.com/mastermindx-market-intelligence/macro/pull/10630) remain **provisional**, without a joint accepted v1.

## Done-when and exact next actions

1. **Existing D08 source owner**: preserve D08-OPTIONS/1.0.0 and disclose the empty Paper candidate honestly; consume a verified, versioned F01/F02 joint release when it exists. Do not duplicate the Paper write that was blocked.
2. **D08A/B/C/D separately assigned owners**: quote the exact common contract revision in their compositions and supply positive/negative evidence for their own objects and saved-state boundaries. No slice launch is authorized by this note.
3. **QA01 / independent design review owner**: review native Paper evidence, not a detached HTML alone. Run 320/390/768/1024/1440, EN/ZH, dark/light, keyboard/focus, 200% text, 400% reflow, reduced motion and source failure/partial/entitlement scenarios against the actual assembled reference and entitled browser.
4. **Existing programme source/release owner**: source reconciliation retains the parent return ledger and held controls. #10649 hosted `ci-authority` failed `unsupported_base_ref` on the stacked parent; do not call it green or retarget/merge for cosmetics. Fresh CI belongs to a lawful supported-base integration later.

This document is a source-of-truth continuation of D08's **partial** reference work, not a Paper write clearance, implementation handoff authorization, reviewer approval, or production completion.
