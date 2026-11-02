# Accepted bounded source census, with principal corrections

The retained report below is accepted for path/capability inventory. The source-clock and causation/race qualifications in DESIGN_SPEC.md supersede the report where they differ. It is not independent visual approval.

All evidence is in hand. Composing the audit report now — every claim below is pinned to source I read at `macro@f754bde` via `git show` only (no checkout, branch, or file changes; scratch under `/tmp` only).

---

# P1.T2 — Source/data/build contract audit: `site/options.html` @ `macro@f754bdee`

## 1. Owning paths & key functions (all at pin)

**Builder/renderer:** `scripts/build_options_command.py` (2621 ln) — "THE CANONICAL OPTIONS SURFACE", display-tier-only, fail-soft, no derivations, O(seconds), zero network. `load_stores()` 143–160; `load_intel_brief()` 179–184; `load_payoff_lab()` 187; `load_skew_source()` 201; `load_catalyst_links()` 233; `build_session()` 1765–1995 (page date = `nyse_calendar.expected_last_session()`, per-source receipts, quality word); `build_posture()` 2001–2107 (4 co-displayed readings, never fused); `build_changed()` 2113+; `build_aib()` 849–1054 + `_aib_freshness()` 524–598 (session-counted staleness, never calendar days); `build_payoff_lab()` 1537+; `render()` 2543–2562 (Jinja `templates/`, `autoescape=True`, `td/tr` i18n globals with EN-fallback); `main()` 2565–2617 (one write fence via `lib.pages.write_page`; render failure keeps previous page, returns 1).

**Template:** `templates/options.html.j2` (3923 ln): CSS 42–1009; boot script L38 (localStorage theme/lang, zh by locale); persistent chrome 1011–1127; Brief (baked) 1129–1670; Flow 1670–2216; Scanner 2218–2567; Ticker 2568–3429; Leaders 3430–3637; routing/JS 3638–3923. Render-time DATA is baked as an inline JSON data script; static CODE is marked `data-externalize` and lifted by `scripts/externalize_css.py` to `assets/js/<hash>.js` (payload law L1743–1752: plain `fetch()` only, never `<script>` injection, #3372).

**Assets:** relative `theme.css`, `illus.css`, `theme.js`, `illus.js` (L39–40, 3920–3921); data-base shim `templates/data_base.js` injected by CI post-render `scripts/inject_data_base.py` (`lib/pages.py:2–19,515–624`); `window.DATA_BASE` → R2 (`r2Url()` L1853), `window.OEW_DEFAULT_TICKER` (L1739), `window.MDXTerminal.url()` terminal CTA (L1829–1842).

**Store producers (page is a pure re-serialiser):** `site/flow_desk.json`←`build_flow_desk`; `site/screenerdata/rows.json`←`build_options_screener`; `site/flowleaders/leaders.json`←`build_flow_leaders`; `data/market_structure/latest.json`←`build_market_structure`; `site/vol/regime.json`←`build_vol_regime`; `site/gex/{SPX,SPY,QQQ,IWM}.json`+`index.json`←`build_gex_board`; `site/options_intel_brief.json`←`build_options_intel_brief`; `site/options_payoff_lab/latest.json`; `site/options_skew/latest.json`←`build_options_skew --emit`; `site/options_catalyst_links/latest.json` (schema-gated). **Client-lazy fetches:** `flow_desk.json` + `flowdata/cohorts.json` (optional) + R2 `live_flow/tide_current.json` (Flow); `screenerdata/rows.json` (Scanner); `gex/<T>.json` + `flow/<T>.json` (←`build_options_flow.py:126`, from `data/polygon_gex/chains/*.parquet`) + `session/<T>.json` (←`engine/session_digest.py:657`) (Ticker); `flowleaders/leaders.json` (Leaders).

**Wiring:** express lanes `render.yml`/`engine-render.yml` + nightly `daily.yml`. `region_of` maps template+builder+screener → `gex`; `optionscmd` is a SERIAL POST-BAND step after `flowleaders` (ordering law). Narrow `gex` order: skew→ivspread→screener→flowleaders→optionscmd; ~+32s, site/-only writes, zero network.

## 2. Capability matrix (actual, verified)

**Chrome (all modes):** session stamp (date/weekday/closed 16:00 ET, OI vintage, covered/universe, quality word+tooltip); "Source-session receipt" `<details>` (7 sources, per-source status current/stale/conflict/unavailable + sessions-behind); posture console 4 readings (pips, vetted ✓ glyph, notes, tooltips); no-fuse sentence; coverage close-line (fill = exact share, unknown renders empty); 5 tabs with counts (pinned order brief·flow·scanner·ticker·leaders); hash routing `#mode` + `#ticker?t=T`; EN/ZH toggle; dark/light with canvas re-tune; skeletons; honest empty/fail panels.

**Brief (baked):** AIB board (states verbatim from `options_intel_brief.json`; degraded receipt `<details>`; watch/event/risk bands; freshness phrase); "What changed" chips each with own comparison date; four index cards + payoff-lab fold; premium-by-sector; biggest single bets; "For tomorrow" rail with ticker deep-links (`data-goto`→Ticker). No filters/sort/export here.

**Flow:** sector heatmap full desk; theme groups; sector ETF money; tide panel + 2 hand-drawn canvases (30-session sparkline; session unfold curve) redrawn on re-entry/theme change; tab count = covered-sector count.

**Scanner:** segmented column views (overview/flow/positioning); 7 presets (screener's own thresholds; `zerodte`≥60, `nearflip`≤1pp); 10 min/max range filters; sector dropdown; text search; per-column sort (desc-first, aria-synced arrows, Enter/Space parity, nulls-last); data-age pip column; CSV export of exactly the filtered+sorted on-screen rows; "more filters" `<details>`; live repaint; "Clear all" resets preset+sort; honest empty state.

**Ticker:** static search toolbar with typeahead (12-row cap, full keyboard model, mousedown-select); per-name read cards (tape/mood/lean); "what the move is worth"; "expiration pressure"; cautions chips; measured-flow panel (premium, same-day %, put/call, net premium + direction-reliability caveat + own asof); "Under the hood" `<details>` (first-open draw) with metrics + 4 hand-SVG charts re-homed from gex.html; Terminal CTA; race-safe re-render (target `#oew-tk-body`, never toolbar).

**Leaders:** boards A (8 momentum legs) / B (washout-turn, B5-filtered); per-ladder hover receipt (n-of-m confirming + missing legs); state chips; caution chips (earnings/both-sides/hedged/fragile-tape + same-day-heavy); "Show all N" expander (rows ship hidden, real count); freshness honesty. Counted against `site/flow_leaders.html` denominators, not payload pre-cap totals.

## 3. Freshness semantics & defect classification

Page date is the NYSE completion clock, independent of store vintages. Coverage 372/408 = count of screener rows whose `asof` equals the screener payload's own max stamp (numerator+denominator from ONE payload — internally consistent). Quality word: any source stale→"Stale" dominates. **Live state is CORRECT fail-closed behavior, not a display bug:** `flow_desk.json` (2026-08-13 → tape/changes/sector/net-premium/same-day-11% readings) and `options_intel_brief.json` (2026-08-19) are genuinely not refreshing, while gex/vol/market_structure are current (2026-10-30 index levels). The receipt and tooltips carry every real date. The *defect* is upstream data refresh (those two producers stalled ~50 sessions); the display *weakness* is that posture cells and Brief context sections show no per-cell date (dates live only in the receipt `<details>`), so 2026-08 figures sit visually adjacent to the 2026-10-30 session date — the "mixed-source" problem the task tree flags.

**TSLA "Same-day heavy" + "0%" contradiction = structural cross-store divergence, neither fabricated:** the Leaders chip fires on `zerodte_dominated` (`build_flow_leaders.py:812–817`, latest `data/options_flow/summary_*` share > `ZERODTE_MAX=0.60`, `engine/flow_leaders.py:31`) while Ticker's "Same-day 0%" reads `flow/TSLA.json` from a DIFFERENT pipeline (`build_options_flow.py` off `data/polygon_gex/chains`). Two producers measure one concept on different bases/vintages; the page renders each verbatim with its own asof and has no same-name reconciliation. Classification: display-layer cohesion gap (possible upstream vintage skew) requiring explicit adjudication before redesign — do not copy forward silently, do not "fix" by faking either value.

**Test-suite note:** of the four named suites, `test_options_reference_pages.py` is NOT page UI — it validates Polygon reference-cursor URLs (data-fetch guard). `test_options_session_guards.py` sweeps upstream stores for fabricated weekend rows (data hygiene class, e.g. `data/cboe/gex.parquet`), relevant as the cause class for stale-store suspicion, not a UI contract.

## 4. Minimal display-only repair & no-change boundaries

**In display scope:** per-cell/per-section source-date labels (reuse `sess.sources`, already computed); same-name same-day-figure reconciliation or explicit dual-vintage labeling in Ticker/Leaders; hierarchy/spacing/mobile/ZH polish. **Outside scope (do not touch):** `load_stores()`'s pinned 7-path set (runtime-probe-pinned by `test_render_options_workspace_scope.py:301–343` — adding a store requires deciding its express-lane coverage there); builder pass-through law (no new scores/thresholds/fusions; §0.13); four-readings-never-fused; payload enum vocabulary; producers; lanes/ordering; `ZERODTE_MAX`; tab order; the "no 0DTE acronym on glance/hover tiers" rule (both page and builder enforce); fail-soft→honest-empty law; express-lane economics (zero data/ writes).

## 5. Safe render/test without full regeneration

- **Hermetic render:** the suite renders `render(root, stores=…, intel_brief=…, …)` with in-memory dicts — no repo reads/writes (`test_build_options_command.py`, 2981 ln, "hermetic by construction"; `MM_DATA_GUARD` conftest tripwire guards data/+site/). Prefer this in any scratch venv; needs only `jinja2` (+stdlib); i18n import failure degrades to EN, never crashes.
- **File render:** `python -m scripts.build_options_command --root <scratch-root-with-site/+templates/> --out /tmp/options.html` — pure JSON reads, no network, ~0.4s; this checkout has no `site/`/`data/` trees and no `.venv`, so a live render here would publish an all-unavailable page (useful only for chrome/empty-state screenshots).
- **Focused suites:** `.venv/bin/python -m pytest tests/test_build_options_command.py tests/test_options_intel_brief_ui.py tests/test_render_options_workspace_scope.py -q` (the scope suite also needs pyyaml+bash; it reads workflows/templates read-only). CI's minimal real regeneration is render.yml's narrow `gex` dispatch (~+32s, site-only commits).

## 6. Active source collision evidence (local, read-only)

`/home/ubuntu3/Documents/GitHub/macro` is on `main@3c3f31909661` (2026-09-30) — the audit pin `f754bde` is **not reachable from local main** (host checkout ~1 month behind the pin). Its working tree holds **staged unrelated work** (`engine/leadership_rotation_context.py`, `engine/theme_graph/*`, a workstream doc) from another active session — do not touch. Other live worktrees are prophet-v4/sysres lanes. No local branch `sol/web-options-workspace-revamp-20261101-sol-001` exists here; per the task tree it was reconciled through the Studio carrier. This audit used `git show`/`git grep` at exact pins only.

## 7. Authoritative inputs for design freeze

`templates/options.html.j2` + `scripts/build_options_command.py` @ `f754bde` (behavioral truth); `mockups/oeu_workspace/options_mockup.html` (pinned markup/CSS origin); `research/options_estate/OEU_MASTERPLAN.md` §2 + `WORKSPACE_DESIGN_SPEC.md` (§0.13 no-fusion/no-threshold law); `contracts/options/OPTIONS_INTEL_BRIEF_V1.md` §5a/§6 (AIB schema+authority); shared chrome sources `site/theme.css`, `illus.css/js`, `theme.js` (+ Terminal helper); `site/theme.css` ZH `--up/--down` flip (L2718); producer schemas for all 12 stores above; test suites as executable contract; parent P1.T1 live/browser observations. Honest gaps: live `site/options.html` bytes and current producer outputs not present on this host checkout (no `site/` tree) — visual claims here derive from parent-supplied live facts, not local bytes; local branch list may not reflect the Studio carrier's branch state.
