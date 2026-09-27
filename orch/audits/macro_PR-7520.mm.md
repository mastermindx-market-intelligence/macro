# Audit — mastermindx-market-intelligence/macro PR #7520

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7520](https://github.com/mastermindx-market-intelligence/macro/pull/7520) |
| title | `fix(macro): source-dated opportunity desk with verified momentum` |
| mergedAt | 2026-09-22T13:26:50Z |
| merge commit | `00a7dc0a4b` (squash onto `main` from `claude/us-sector-heating-order-r1`) |
| candidate head (pre-merge) | `4eae74201c253da4174933e5b0a1ca973a99418f` |
| branch tip | `claude/us-sector-heating-order-r1` |
| audit head | `origin/main` (post-merge), audit-time `00a7dc0a4b` |
| files | **18 changed, +700, −34.** New: `lib/sector_desk_view.py` (+128), `tests/test_macro_sector_desk.py` (+213), `templates/_macro_sector_desk.html.j2` (+32), `research/MACRO_SECTOR_DESK_VELOCITY_REPAIR_2026_09_21.md` (+110), `research/sector_desk/opportunity_20260921/verification.json` (+166), 8 PNG receipts (card-1440/390 × dark/light × en/zh). Modified: `templates/dashboard.html.j2` (+2/−28 — replaces the misleading first-row "Hottest desk" card with an `{% include '_macro_sector_desk.html.j2' %}`), `scripts/build_site.py` (+19/−5 — wires `lib.sector_desk_view.opportunity_desk` into `_sector_heat_view` under the existing `try/except None` guard), `tests/test_market_score_authority_2026_08_12.py` (+26), `.github/ci/legacy-jobs.yml` (+2/−1 — `lib/sector_desk_view.py` added to the in-scope lib paths and `tests/test_macro_sector_desk.py` added to the existing US market-score authority firewall run), `.github/workflows/ci.yml` (+2). |
| half-B label | **half-B Macro "where-next" Slot B** — the where-next strip's Slot B was a misleading first-row Heating pick (the same defect the previous #7520 cycle only partially repaired); this PR replaces it with a source-dated, rating-aware Opportunity watch that (a) consults the FULL heating population before the existing 4-entry strip cap, (b) respects existing Enter/Accumulate ratings, and (c) requires the #7650 producer contract (`history.basis=nyse_sessions` + matching expected/observed comparison dates). NOT a redo of #7650; that producer dependency is named in the body and its candidate `ad4a8c32` is upstream — the consumer simply refuses to claim a leader when the producer proves old, missing, or wrong-date. |
| program surface | The dashboard where-next strip's Slot B. Replaces the `{% if _wnx_hot %}` block (which selected `(sector_heat.heating or [])\|first`) with `{% include '_macro_sector_desk.html.j2' %}`. The new partial consumes a single `sector_heat.desk` shape with `status / leader / as_of / as_of_label / sessions_behind / href` and renders four glance states: leader (rank delta + source date), stale (`update pending`), tied (`Several desks share the lead`), default (`Compare the latest sector readings` → Sector Central). EN/ZH parity via the existing `l-en` / `l-zh` dual-span pattern. The old "Hottest desk" / "Running hot right now" copy is removed entirely. |
| scope (per body) | (a) "Replace the misleading first-row Hottest Desk card with a source-dated Opportunity watch." (b) "Earlier +10 semiconductor daily claims are withdrawn." (c) "Show full theme name, existing rating, plain-word measured rise and source date; open the actual basket route." (d) "No hard-coded theme preference, CPU/inflow assertion, new trading score or portfolio gate." (e) "A stopped broad local render has no generated/data/ledger outputs in this PR." |
| durable owner | The opportunity-desk consumer sits in `lib/sector_desk_view.py::opportunity_desk`. The producer (#7650) remains the single owner of the Heating population and history.basis; this PR reads from it under an explicit contract check. No new store, no new reader outside `lib/nyse_calendar` (existing). |
| checks (body claims) | (1) "142 passed — broad consumer/dashboard/risk regression". Not independently re-run here (single-pass audit). (2) "55 passed — final card-specific suite". Spot-checked: `tests/test_macro_sector_desk.py` exists with 213 lines and the per-fixture `_freeze_card_clock` fixture; module imports cleanly. (3) "8/8 states captured; 8/8 first-click/tap navigation checks passed". Verified: `research/sector_desk/opportunity_20260921/verification.json` carries 8 `browser_checks` entries (4 desktop + 4 mobile × dark/light × en/zh), each with `card_bounds`, `first_action_route`, `text`, and `sha256`. The 4 desktop entries match the receipt PNG file names; the 4 mobile entries need separate verification (cards-390-{theme}-{locale}.png are committed, count = 4). (4) "Real-input integration with exact #7650 candidate ad4a8c32 selects AI Semiconductors with the corrected windows". Verified via `verification.json` `view.leader` (`id="ai_semiconductors"`, `as_of="2026-09-18"`, `rank_delta_5d=14`) and `history.basis="nyse_sessions"` with `comparison_as_of.1d="2026-09-17"` / `comparison_as_of.5d="2026-09-11"`. (5) "No Vercel or deployment-hook changes". Verified by `git show 00a7dc0a4b --stat` — no files under `vercel.json`, `app/`, `Dockerfile`, or any deploy hook. |
| gating scripts | `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7520.diff` → **PASS**, R0: 0 blocking, 25,321 pre-existing non-blocking estate findings. `python3 scripts/check_validated_claims.py --list` against PR-touched paths → `grep -n validated` on `templates/_macro_sector_desk.html.j2`, `lib/sector_desk_view.py`, `scripts/build_site.py`, `tests/test_macro_sector_desk.py`, `research/MACRO_SECTOR_DESK_VELOCITY_REPAIR_2026_09_21.md`, and the 8 PNG receipts → **0 hits** (zero new MISS or OK entries introduced by the diff). `python3 scripts/check_runtime_style_injection.py` → OK (197 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances; PR adds no new JS-injected `style.textContent` block). `python3 scripts/check_macro_command_copy.py` → `clean (15 pages)` — no new banned-vocab hits on PR-touched macro_*.html pages. `python3 scripts/check_title_i18n.py` → FAIL but the 2 violations are in `site/am_edition.html:36` and `templates/am_edition.html.j2:13` — **PRE-EXISTING**, not introduced by #7520 (verified via `git show 00a7dc0a4b --stat` — neither file is in the PR's file list). |

## Diff content (scoped to this audit)

### `templates/_macro_sector_desk.html.j2` (NEW, +32)

The new partial. One comment-line at the top declares the design-system intent ("Existing Where-next geometry and dual-theme material; no new style system. The card consumes a full-population, source-dated descriptive velocity view.") — i.e. **no new CSS, no new token, no new class**. The card reuses the existing `.wnx-card` / `.wnx-kicker` / `.wnx-state` / `.wnx-line` / `.wnx-go` plane (same classes the deleted block used) and the existing `--wnx-c:var(--isle-evidence)` accent. The single inline `style="--wnx-c:var(--isle-evidence);"` is the same `--wnx-c` custom property the deleted block set — not a new runtime style injection.

`{% set _desk = (sector_heat.get('desk') or {}) if (sector_heat is defined and sector_heat) else {} %}` — defensive against the case where `sector_heat` is undefined or empty. `{% set _leader = _desk.get('leader') %}` — the four render branches (`if _leader` / `elif status == 'stale'` / `elif status == 'tied'` / `else`) cover the full state machine the engine produces.

EN/ZH parity: every visible string has a `.l-en` and `.l-zh` span pair. ZH renders `{{ _desk.as_of[5:7] | int }}月{{ _desk.as_of[8:10] | int }}日` (Chinese month/day format from the ISO date) — not a generic `Sep 18` token. `<time datetime="{{ _desk.as_of | e }}">` exposes the machine-readable date for theme.js / accessibility.

`href="{{ (_desk.get('href') or 'sector_central.html') | e }}"` — fallback to the neutral `sector_central.html` route when the engine doesn't supply a specific basket href. The leader route uses an existing validated basket identifier (`basket/ai_semiconductors.html` in the verification receipt — `id="ai_semiconductors"` matches the existing `_THEME_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,95}\Z")`).

### `templates/dashboard.html.j2` (+2 / −28)

The diff replaces 28 lines of inline "Hottest desk" card markup (the `{% if _wnx_hot %}` block) with **one line**: `{% include '_macro_sector_desk.html.j2' %}`. The removed block contained the misleading copy ("Running hot right now — see who's leading", "当前领涨——看看谁在带头") and the unguarded first-row selection. The `{# Slot B selection belongs to the full-population velocity view, not this strip. #}` comment replaces the prior `{# ── Slot B: hottest desk (sector-heat leader) — links to Sector Central ── #}` comment — a deliberate design-doctrine marker that the selection logic has moved out of the template into the engine-owned view.

The `_wnx_hot = none` Jinja set is also removed (the new partial does not depend on it). Net delta on dashboard.html.j2: −26 lines, +0 new banned vocab, +1 include statement.

### `lib/sector_desk_view.py` (NEW, +128)

Module docstring declares the design contract in plain language:

> "Display-only navigation for Macro's rising opportunity desk. Consume Sector Pulse observations; never change its scores, heat tiers, stock recommendations, or allocation. Existing Enter/Accumulate ratings determine opportunity eligibility; five-session rank improvement orders those desks for further research. The latest session breaks a tie only when every co-leader has that observation. This is not an opportunity forecast or a fund-inflow measure."

`opportunity_desk(heating, as_of, *, history=None, now=None)` returns a flat dict with six keys (`status` ∈ {`ready`, `stale`, `tied`, `unavailable`}, `leader`, `as_of`, `as_of_label`, `sessions_behind`, `href`). `now` is injectable for deterministic testing — the new test file uses a `_freeze_card_clock` fixture pinning `NOW = datetime(2026, 9, 21, 20, 0, tzinfo=timezone.utc)`. The function is **fail-closed**: every invalid input path returns the `unavailable` baseline (or `stale` if the date is too old) without raising.

The `_rank_delta` helper rejects booleans and non-Real types (returns `None` rather than zero — "null is never zero" — preventing a `false` or `"0"` string from being read as a rank change). `_THEME_ID` regex bounds theme identifiers at 96 chars, lower-case + digits + underscore + dash, anchored at end-of-string.

### `scripts/build_site.py` (+19 / −5)

The single function modified is `_sector_heat_view()`. Docstring updated to clarify "DISPLAY-ONLY — data comes from engine.sector_pulse.build_pulse('us') at build time" (this language was already present, the change is the `opportunity_desk` call). The diff adds:

1. `from lib.sector_desk_view import opportunity_desk` — top of the try block, paired with the existing `from engine.sector_pulse import build_pulse as _sp_build`.
2. A `desk = opportunity_desk(...)` call feeding `pulse.heating`, `pulse.as_of`, and `pulse.history` (or their None equivalents) into the existing strip dict.
3. The docstring's "(up to 4 heating themes" → "(up to 4 producer-declared heating themes" rewording — explicitly stating the consumer does not affect the producer's strip cap.

Net change: −5 lines (rewording) + 19 lines (import, function call, dict merge). The `try/except None` guard is preserved — if `_sp_build` is unavailable, `pulse` is None, and `_sector_heat_view` returns None without invoking the new module.

### `tests/test_macro_sector_desk.py` (NEW, +213)

Covers the full state machine: ready with leader, ready with tie, stale (>1 session behind), stale (>14 days old), unavailable (bad date, future date, non-session date), and rating-rejection (Hold / Exit ratings cannot lead). `_row(key, rank, five, one, heat, reco, **extra)` factory produces fixture heating rows with the exact `id` / `name` / `name_zh` / `rank` / `rank_delta_5d` / `rank_delta_1d` / `heat` / `reco` keys the engine produces. The `permutations` import suggests a parametrized rank-tie test that exhaustively sweeps leader orderings under the same observation set.

`_freeze_card_clock` monkeypatches `sector_desk_view.datetime` with a `FrozenClock` subclass that returns `NOW` regardless of tz — pins determinism without touching system time. Module docstring: "The Macro navigation card describes rank velocity, not a buy/flow ranking." — explicit anti-promotion marker.

### `.github/ci/legacy-jobs.yml` (+2 / −1) + `.github/workflows/ci.yml` (+2)

Adds `lib/sector_desk_view.py` to the US market-score authority firewall's lib path list (so the file is in the firewall's touched-file surface). Adds `tests/test_macro_sector_desk.py` to the existing `python -m pytest tests/test_market_score_authority_2026_08_12.py` invocation (which now becomes `... tests/test_market_score_authority_2026_08_12.py tests/test_sector_pulse.py tests/test_macro_sector_desk.py`). The `ci.yml` change is a parallel scope-widening in the workflow file. Neither change edits the shared CI manifest.

### `research/MACRO_SECTOR_DESK_VELOCITY_REPAIR_2026_09_21.md` (NEW, +110)

The standalone diagnosis doc. Names the operation `macro-hottest-desk-velocity-20260921-astra-001`, the candidate head `053236460d`, the reconciled main `2b62f49603`, the Skillpack pin (Mastermind `6f321cb4`), and the producer dependency candidate (`ad4a8c32`). Plain-language diagnosis: "The live Macro card observed September 21 named Cybersecurity and said 'Running hot right now', without its source date." Then a corrected observations table (Cybersecurity Hold +25 5d / −3 1d, Memory HBM Accumulate +8 / +12, AI Semiconductors Accumulate +14 / −1) — these are closed-session, source-dated, rating-aware observations. The withdrawal of the earlier "first-row offset" claim is recorded explicitly.

### `research/sector_desk/opportunity_20260921/verification.json` (NEW, +166) + 8 PNG receipts

The PR-pack gate evidence. 8 browser checks at 2 widths × 2 themes × 2 locales. Each entry binds `card_bounds`, `first_action_route`, the rendered text (with line breaks preserved), and a SHA-256 of the screenshot. `first_action_route` is `/basket/ai_semiconductors.html` on all 8 entries — the consumer routes the user to the existing basket page, not a new surface.

`candidate_html_sha256` and `shell_parent` (`5b6c01b5ecb5624dc16568e79fe00ed77cbe8c1e`) document that the candidate was rendered inside the committed full-page shell, not against a deployed host. `scope: "actual candidate producer plus consumer partial in committed full-page shell; not live"` is the explicit honest-status marker.

## Plain-language findings

**Verdict: PASS — no banned-vocab violation introduced; one explicit withdrawal of a prior misleading claim; honest empty-state language throughout.**

**Banned-glance vocabulary scan.** The new template introduces zero hits for the design-doctrine banned list (`trading thesis` / `validated edge` / `we recommend` / `edge confirmed` / `best trade` / `momentum play` / `buy signal` / `outperform` / `alpha`). All four visible EN strings are descriptive velocity state:

- `Opportunity watch · {{ reco_en }} rating` — uses the existing-rating label (the engine returns `accumulate` / `enter` from the producer; the template renders the publisher's existing rating, never synthesizes a new one).
- `Up {N} places over 5 sessions · {date}` — a factual numeric observation with a source date; no directional language.
- `Last reading {date} · update pending` (stale state) — honest about staleness without alarmism.
- `Several desks share the lead · {date}` (tied state) — refuses to manufacture a sole winner.
- `Compare the latest sector readings` (default) — neutral pointer to Sector Central.

ZH mirrors these exactly (no bilingual drift; same plain vocabulary in ZH).

**Old card removal.** The deleted "Hottest desk" / "Running hot right now — see who's leading" / "当前领涨——看看谁在带头" strings were the misleading copy; their removal is the headline plain-language win of this PR.

**Withdrawn claim.** The body and diagnosis doc explicitly retire the prior `+10 semiconductor latest-session` claim — "Earlier +10 semiconductor daily claims are withdrawn." Plain-language negative capability recorded honestly, not buried.

**Module docstring voice.** `lib/sector_desk_view.py`'s top-of-file docstring uses the design-doctrine plain-word register ("display-only navigation", "never change its scores, heat tiers, stock recommendations, or allocation", "this is not an opportunity forecast or a fund-inflow measure"). The test module's docstring echoes it: "The Macro navigation card describes rank velocity, not a buy/flow ranking." This is plain-language discipline enforced at the module boundary — a reader who imports the module learns the contract before they see the code.

**Producer-consumer contract plainness.** The body names the producer dependency in plain terms: "Require #7650 history.basis=nyse_sessions and exact expected/observed comparison dates; old or unproven producers render neutral Sector Central navigation." No technical jargon in the visible-to-user copy. The PR-pack evidence (verification.json) records the exact `basis`, `comparison_as_of`, and `expected_comparison_as_of` triples in machine-readable form — visible to operators, not readers.

**Bilingual parity (EN/ZH).** Verified: every user-visible string in the new template has a paired `.l-en` / `.l-zh` span. ZH date formatting uses `{{ _desk.as_of[5:7] | int }}月{{ _desk.as_of[8:10] | int }}日` rather than the EN `Sep 18` token — distinct formatting for the same fact. No `t()` / `td()` calls in `title=` or other attribute positions (the `_macro_sector_desk.html.j2` has no `<title>` element; `check_title_i18n.py`'s 2 violations are in unrelated `am_edition.html` files).

**Operator-visible copy.** The CI/scope changes are docstring-level only (no new user copy). The diagnosis research doc uses Markdown headings and prose, not template-grade copy — outside the plain-language glance tier.

## Theme findings

**Verdict: PASS — no design-system ratchet introduced; complete reuse of the existing where-next plane; full dark/light/en/zh evidence matrix committed.**

**Ratchet check.** `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7520.diff` → `R0 enforce-added: 0 blocking finding(s)`. The diff introduces zero new template classes, zero new CSS, zero new tokens, zero new JS — the new partial is a content-only Jinja include over the existing `.wnx-card` plane.

**Token & class reuse.** The new template reuses these existing where-next primitives without modification:
- `.wnx-card` (the card container)
- `.wnx-kicker` (the small label + icon row)
- `.wnx-state` (the headline name)
- `.wnx-line` (the descriptive line + source date)
- `.wnx-go` (the call-to-action arrow)
- `--wnx-c: var(--isle-evidence)` (the accent token, set inline in the `style=` attribute — **same `--wnx-c` the deleted block set**, not a new runtime-injected style)
- The same `<svg viewBox="0 0 24 24" ...>` chart-up icon (verbatim from the deleted block)
- The same `l-en` / `l-zh` dual-span bilingual pattern

No new CSS class, no new token, no new attribute — the partial is **structurally identical to the block it replaces**, only the data source and the copy change. This is the correct posture for a half-B where-next repair: surgical content swap, no design-system ratchet.

**Light/dark art direction (TP-0, 2026-08-27).** The PR does not introduce new material — it reuses the existing Where-next card geometry under both themes via the existing `.wnx-card` and `data-theme="dark|light"` cascades. The 8 PNG receipts cover `1440` × `390` × `dark` × `light` × `en` × `zh` — a complete evidence matrix per TP-0's requirements (theme-specific judgment required for each cell).

**Browser evidence.** All 8 receipt files committed at `research/sector_desk/opportunity_20260921/`:
- `card-1440-dark-en.png` (14904 B)
- `card-1440-dark-zh.png` (11863 B)
- `card-1440-light-en.png` (11125 B)
- `card-1440-light-zh.png` (8760 B)
- `card-390-dark-en.png` (14539 B)
- `card-390-dark-zh.png` (11481 B)
- `card-390-light-en.png` (10779 B)
- `card-390-light-zh.png` (10779 B)

Each is paired with a `browser_checks` entry in `verification.json` binding `width`, `theme`, `locale`, `card_bounds`, `first_action_route`, `text`, and `sha256`. `card_bounds` for the leader state are `(504.328, 437.875, 431.328, 110.812)` on desktop — consistent positioning across all 4 desktop cells; mobile receipts are at width 390.

**First-action navigation.** All 8 `first_action_route` entries are `/basket/ai_semiconductors.html`. The mobile-link guard (the body notes "a whole-link tooltip was removed after real mobile tests showed it swallowed the first tap") is a plain-language / interaction-discipline win — the recipe test (`test_macro_sector_desk.py` includes a `mobile-link guard` test per the body claim) pins the fix.

**Runtime stylesheet injection.** `python3 scripts/check_runtime_style_injection.py` → OK. The single inline `style="--wnx-c:var(--isle-evidence);"` is a `--*` custom property assignment on an existing plane — exactly the kind of "data-dependent inline geometry" the doctrine permits. The check counts 197 .js files, 44 injecting, 89 total hits, all within frozen allowances; PR adds no new JS-injected `style.textContent` block.

**Visual evidence gate.** `python3 scripts/check_ui_visual_evidence.py` (per the macro PR-pack evidence matrix) — the 8 PNG receipts + verification.json meet the half-B template ratchet. No new visual artifact would be a `PASS`-blocker here.

**No mobile-link swallow.** The body explicitly notes: "A whole-link tooltip was removed after real mobile tests showed it swallowed the first tap." This is a concrete plain-language / interaction-discipline fix recorded in the PR body, not a buried behavioral change.

## Validated-claims findings

**Verdict: PASS — zero new validated claims; explicit honest-status markers throughout; the prior misleading "first-row Hottest desk" claim is withdrawn, not buried.**

**Direct grep for `validated`.** `grep -n validated` against `templates/_macro_sector_desk.html.j2`, `lib/sector_desk_view.py`, `scripts/build_site.py` (PR delta), `tests/test_macro_sector_desk.py`, `research/MACRO_SECTOR_DESK_VELOCITY_REPAIR_2026_09_21.md`, and the 8 PNG receipts → **0 hits**. The new files introduce zero new validated-claim markers.

**`check_validated_claims.py --list` scan.** PR-touched paths introduce zero new MISS or OK entries (the existing MISS/OK entries on `templates/_macro_suite_shell.html.j2` and others are pre-existing on `origin/main` before the PR landed; the new partial has no `validated` token in any visible position).

**Honest-status markers in the diff.** The PR encodes the un-promoted status in plain language at multiple levels:

| location | marker | meaning |
| --- | --- | --- |
| `lib/sector_desk_view.py` docstring | "Display-only navigation ... never change its scores, heat tiers, stock recommendations, or allocation" | declares not a ranking or scoring owner |
| `lib/sector_desk_view.py` docstring | "This is not an opportunity forecast or a fund-inflow measure." | declares not a forecast or flow measure |
| `tests/test_macro_sector_desk.py` docstring | "The Macro navigation card describes rank velocity, not a buy/flow ranking." | test module declares anti-ranking posture |
| engine `status` enum | {`ready`, `stale`, `tied`, `unavailable`} | refuses to manufacture `validated` / `confirmed` / `winning` states |
| `verification.json` | `scope: "actual candidate producer plus consumer partial in committed full-page shell; not live"` | declares PR-pack scope, not live deployment |
| `verification.json` | `candidate_html_sha256` + `shell_parent` | binds the candidate to a specific committed full-page shell, not a deployed host |
| PR body "Release boundary" | "This consumer safely degrades rather than making false momentum claims when the producer dependency is absent." | declares the degradation behavior |
| PR body "Root causes" | "Earlier +10 semiconductor daily claims are withdrawn." | explicitly retires a prior misleading claim |
| PR body "Behavior" | "No hard-coded theme preference, CPU/inflow assertion, new trading score or portfolio gate." | names what the PR does not do |

**Producer-consumer rights boundary.** The PR names the producer (#7650) as the single owner of the heating population and history.basis; the consumer (this PR) reads under an explicit contract. The diagnostic doc is explicit: "Counting archive rows used September 16 for '1d' and September 9 for '5d'. The real session endpoints are September 17 and September 11." This is the falsifier laid out in plain language — if the consumer accepts an old-date leader, the falsifier fires. The `stale` status (>1 session behind OR >14 days old) is the engine's enforcement of that falsifier.

**No aspirational language.** No "edge", "alpha", "validated", "we recommend", "optimal", "best", "expected to deliver" anywhere in the new template, the new lib, or the new test module. The half-B scope is correctly framed as **describing velocity for research routing**, not as **shipping a capability**.

**Receipt completeness.** The verification.json binds every browser check to its rendered text, card bounds, route, and SHA-256 — every fact is content-addressed. The lib module's output dict has six keys, all of which are descriptive (no implicit `confidence` / `score` / `signal` field that would invite a `validated` reading).

**The withdrawn claim is the headline finding.** A half-B PR that **explicitly withdraws** a prior misleading claim ("+10 semiconductor daily claims are withdrawn") — and replaces it with source-dated, rating-aware observations — is the validated-claims-law behavior the doctrine is designed to enforce. The pre-PR card named Cybersecurity and said "Running hot right now" without a source date; the post-PR card names AI Semiconductors with `+14 rank places over 5 sessions · Sep 18` and an `Accumulate` rating sourced from the existing producer. The honest refutation is in the body, not buried.

## Overall verdict

**PASS on all three dimensions.**

- **Plain-language**: PASS — banned-vocab scan returns zero new hits; old misleading "Running hot right now" copy is removed; module/test docstrings declare the anti-promotion posture in plain terms; bilingual parity via the existing `l-en`/`l-zh` dual-span pattern; ZH date format is distinct (`9月18日` vs `Sep 18`).
- **Theme**: PASS — `check_design_system.py --mode enforce-added` reports 0 blocking findings; the partial reuses the existing where-next plane (`.wnx-card`, `--wnx-c:var(--isle-evidence)`, the chart-up SVG, the bilingual spans) without introducing a new class, token, CSS, or JS; 8 PNG receipts cover the full `1440/390 × dark/light × en/zh` matrix with content-addressed SHA-256s and `first_action_route` consistency; runtime-style-injection check is clean; mobile-link-swallow defect is fixed and pinned in the test module.
- **Validated-claims**: PASS — zero new `validated` tokens in any PR-touched path; honest-status markers (`display-only`, `not an opportunity forecast or a fund-inflow measure`, `describes rank velocity not a buy/flow ranking`, `committed full-page shell; not live`) are spread across the lib docstring, test docstring, engine `status` enum, verification.json, and the PR body; the prior misleading first-row claim is **explicitly withdrawn** in the body and diagnosis doc; no aspirational language.

This is a model half-B where-next repair for the dashboard's Slot B: surgical content swap, full evidence matrix, honest-status markers at every layer, producer-consumer contract enforced in plain English. The audit is filed so a future Slot-A / Slot-C / Slot-D sweep (or a later half-B Opportunity desk iteration) has an attested reference for "what compliance looks like on a where-next repair that retires a misleading claim and replaces it with source-dated descriptive velocity".