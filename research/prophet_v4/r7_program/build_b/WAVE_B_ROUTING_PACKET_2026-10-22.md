# Wave B — routing packet to incumbent custody (Stage 6 change packet)

Seat: Fable Meta-CEO 69eb9a1c · Program: Prophet end-to-end r7 (masterplan 2026-10-20 §15)
Status: POSTED 2026-10-22 08:2xZ on #9495 (and linked from #8444 for B-5 only). Wave A is on main — B4 #9959, cards/plans #9954 → 2ebafe80, receipts #9955 → a81ef7ae, watchlist A2 #9956 → 790990a2 — so every token and partial this packet cites exists on main ≥ 790990a2. The seat never edits a custody file; this packet is the whole of Wave B's "build" until the custodians land or absorb it. One post, no label, no arm, no re-post.

## 1. Why a packet and not a build

Masterplan §15 preserves incumbent owners. The Today-surface templates the R7 design spec (§13) changes are held by
open draft PRs with live writers, so a second writer on those files is forbidden (handoff: "no second #9495 writer").
Wave A (#9954 cards/plans, #9955 receipts, #9956 watchlist) built everything OUTSIDE that custody. Everything below is
what remains, routed to the file's custodian in the exact form the custodian can apply.

## 2. Custody table (observed 2026-10-22 02:0xZ, one GraphQL read)

| File | Custodian PR | Owner | State |
|---|---|---|---|
| `templates/_us_board_cards.html.j2` | #9495 (also #8444) | mastermindxryan / sol | OPEN draft, updated 10-20 |
| `templates/_prophet_setup_detail.html.j2` | #9495 | mastermindxryan | OPEN draft |
| `templates/_prophet_workspace.css.j2` | #9495, #9294 | mastermindxryan | OPEN draft (#9294 updated 10-14) |
| `templates/dashboard.html.j2` | #9495 | mastermindxryan | OPEN draft |
| `templates/_us_candidate_pool*.html.j2` | #8444 (`sol/*`, never touch) | mastermidx4 | OPEN draft, updated 10-20 |
| `tests/test_us_board_gate.py`, `tests/test_us_board_hydration_merge.py` | #9495, #8444 | — | as above |

Precedence inside custody: #9566 (merged 10-18) restored the Chairman's compact chart-first card and binds #9495 to
that layout — the design spec's OQ1 recommendation (carry the R7 semantics INTO the compact card; the 1440 ledger only
on the All-candidates landing) is the seat's ruling for this packet. No change below widens or heightens the card
beyond the #9566 envelope.

## 3. Change items, per custody file (spec §13 is the source; nothing here is new design)

**B-1 `_us_board_cards.html.j2` (#9495)** — add the five-slot decision line beneath the chart with fixed slot
geometry, the state copy and the stance glyph (spec §1, §5, §6). States: Buy / Near / Wait / `Entry not assessed` /
`Unavailable`; `Entry not assessed` and `Unavailable` never co-occur with a Buy glyph; a stale quote implies no Buy.
EN/ZH strings from Appendix A rows R7-01/R7-02. Legacy Buy fallback: none — the truthful entry language of #9495's own
product-truth repair governs (masterplan Stage 1).

**B-2 `_prophet_setup_detail.html.j2` (#9495)** — timing panel with the levels chart and its mandatory caption, the
"What ends it" panel, the checkpoints table, the provenance footnote, and the revoked / reconstructed-from-<date> /
not-assessed variants (spec §13; Appendix A R7-10/R7-12). The receipt "Cleared every check" contradiction (Stage 1
product-truth repair) stays with #9495's own writer; this packet adds nothing to it.

**B-3 `_prophet_workspace.css.j2` (#9495 / #9294)** — keep the overlay pointer-events safeguard; add the decision-line
CSS: container query (spec §8), slot grid tracks, stance glyph classes, state classes, chart line-dash classes and the
skeleton. Radii only via `var(--r-*)`; colours only via tokens (`--line-quiet` lands with Wave A #9954; `--warn` is
never a text colour in light — OQ8). No `border-left` / inset accent on any container (design doctrine).

**B-4 `dashboard.html.j2` (#9495)** — `#us-standouts`: h2 "Tonight's US opportunities", the lens radiogroup with
counts, the ordering note, "See all N", and the "Passed on tonight" count link (plain text, no chevron — OQ4); the
four row macros adopt the slot order; the three includes are unchanged. Lens rows for Quality earnings / Cycle capture
reuse Buy/Near/Wait or `Entry not assessed` (OQ2) — no lens-specific stance words.

**B-5 `_us_candidate_pool*.html.j2` (#8444)** — All-candidates landing: the full ledger (≥1136) or cards with the same
ordering note (spec §13). Routed to the `sol/*` owner only; the seat never pushes to that branch.

**B-6 tests (#9495 / #8444)** — extend `tests/test_us_board_*` with the six spec guards: (1) five slot labels per row
or card in EN and ZH; (2) no `border-left` / `box-shadow inset` accent on Prophet containers; (3) a state change keeps
the slot count; (4) `Entry not assessed` / `Unavailable` never with a Buy glyph; (5) stale quote ⇒ no Buy;
(6) sample-data footnote present when fixture data renders. OQ7 is a pytest guard, not lint.

**B-7 carried from the Wave A A2 review (watchlist save states)** — merged in A2 #9956 (main 790990a2): `saveChecked(listId, tickers, opts)` in `templates/watchstore.js` (one save that reports what the ACCOUNT stored, deadline-tagged) and the `ws-save-outcome` painter in `templates/watchlist.js` that renders the R7-21 outcome copy (saved / read-back / "Choose another list" recovery). At 31a61ba8 that flow is DORMANT: the re-review found no caller of `saveChecked` on the watchlist page, the "Saving doesn't create a plan or a position." disclaimer line and the "Check again" action are not yet rendered, and the ≤720px footnote defect (A2-N3) is being fixed in the U5 lane. The Today card's "Save to list" affordance must call `saveChecked` and dispatch to the merged painter, never a local copy; the R7-19/R7-21 strings come from the spec's Appendix A verbatim. Source: `reviews/A2_9956_REREVIEW_r2r3_31a61ba8_2026-10-22.md` and `reviews/WAVE_A_A2_FIX_REVIEW_2026-10-22.md` item 6.

## 4. Out of Prophet custody (routed elsewhere, not blocking)

OQ8 census found 13 `--warn`-as-text uses outside Wave A custody (calculators, dashboard, flow_velocity, policy_watch,
sector_central, seo_base, seo_calculator_base, ticker, vector — list in `build_a/WAVE_A_WORKLOG.md`). Hygiene for the
design-system owner; one issue, not a Prophet PR. The `_prophet_card.html.j2` partial and the navigation family stay
untouched (spec §13 "Leave untouched").

## 5. Acceptance the custodian owes (masterplan §13 ↔ spec §12)

- Both design-governance commands pass on the diff (`scripts/check_design_system.py --mode enforce-added`,
  `scripts/check_ui_visual_evidence.py`), with a committed `EVIDENCE.yml` (`mastermind.page_evidence_receipt.v1`) whose
  `changed_paths` lists every changed template/CSS/JS path verbatim and an 8-cell capture per page
  (desktop/mobile × en/zh × dark/light).
- Browser proof at 1440 / 768 / 390 / 320 × light/dark × EN/ZH for Today and Setup (mastermind-product-path-proof);
  OQ11: drawn cells are the reference, undrawn cells follow the same tokens.
- Contrast per spec §9; focus outlines complete; live regions per §10; CLS budget per §11.
- No invented signals, sizes or recommendations; `Entry not assessed` wherever no native rule exists.

## 6. Routing and the seat's next act

1. When Wave A has merged (A1/A2/A3), the seat posts this packet ONCE as a comment on #9495 (fence first; the comment
   names the seat, the session id and this file's path) and links it from #8444 for B-5 only. No label, no arm, no
   re-post.
2. If the custodians land first, Wave B becomes a build lane on the new base with this packet as the frozen spec
   (ROUTE build; fabric first, native Opus orchestrator only under the continuation law).
3. The closing report states the Today-surface design proof as DEPENDENT on this packet's absorption (masterplan
   §14.4 four-market acceptance is reported at the rung the evidence reaches, never higher).
