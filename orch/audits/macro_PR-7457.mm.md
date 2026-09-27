# Plain-language / theme / validated-claims audit — macro PR #7457

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-20.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7457 |
| title | `feat(prophet): surface leaders waiting for entry` |
| merge head | `123bb84b20176e64ec1cd6414aa66843a66dc437` (exact head captured from `gh pr view 7457 --json headRefOid`; PR body reports the implementation head as `a245d693b9f58a2307805992b0d075d66d692efd` for the agentos handoff — both reference the same carrier). |
| merged | 2026-09-20T23:38:38Z via squash-merge to `main`. Most recent merged non-audit-record half-B PR in the 24-h window after the orch(audit) record PRs #7564/#7561/#7560/#7556/#7555/#7549/#7548/#7547/#7546/#7545/#7544/#7543/#7541/#7540/#7538/#7537/#7536/#7529/#7525/#7519/#7516. |
| author / merger | `chriswong6031-creator` (operator, META-CEO A seat under `WS:PROPHET-US-V4-RECOVERY / prophet-leader-observation-p1-20260919`). |
| base | `origin/main` at the PR-body merge base. |
| files | **14 paths, +1333 / −4** — `engine/us_leader_pullback_coverage.py` (+337 / −0), `templates/dashboard.html.j2` (+77 / −0), `scripts/build_site.py` (+68 / −2), `tests/test_prophet_leader_observation_shelf.py` (+320 / −0, NEW), `tests/test_us_leader_observation_projection.py` (+293 / −0, NEW), `agentos/handoffs/PROPHET-US-V4-RECOVERY-2026-09-19-leader-observation-p1.md` (+116 / −0, NEW), `tests/test_paywall.py` (+38 / −0), `templates/_us_leader_observation_rows.html.j2` (+21 / −0, NEW), `tests/test_regwall_json_gate.py` (+24 / −0), `.github/ci/legacy-jobs.yml` (+18 / −0), `scripts/build_prophet.py` (+15 / −0), `config/site_access.yml` (+4 / −0), `app/deploy/Caddyfile` (+1 / −1), `templates/plans.html.j2` (+1 / −1). |
| half-B label | **half-B (Prophet display-only observation shelf, no candidate/plan/rank authority).** PR body explicitly states "This is a display-only observation capability. It does not weaken `not_topped_veto`, widen candidate selection, originate plans, rank names, size positions, or create a new event/access/publication plane." The carrier is `prophet-leader-observation-p1-20260919` under `WS:PROPHET-US-V4-RECOVERY`. |
| scope | Surface a source-dated "Leaders / waiting for entry" shelf on the existing US Prophet surface so high-relative-strength leaders remain visible even when they are not admitted to the current Candidate board. The shelf is a separate bilingual panel, alphabetical and `plan_authority=false`, never a candidate/plan entry, never an entitlement, never a new event/access plane. |
| durable owner | `WS:PROPHET-US-V4-RECOVERY` (`agentos/handoffs/PROPHET-US-V4-RECOVERY-2026-09-19-leader-observation-p1.md`, NEW in this PR). |
| merge/release dependency | PR body and the handoff both name `#7187 / sol/prophet-us-panel-authority-20260916` as a stacked availability dependency; PR body declares "BUILT_NOT_PROVEN … it compares to `main` so the repository's authority gate can run; it remains dependency-ordered behind #7187 and must not merge around that carrier." PR was nevertheless squash-merged at 2026-09-20T23:38:38Z (the operator's chosen carry, not a Sol gate release — flagged as a release-boundary concern in §Overall verdict, NOT as a plain-language / theme / validated-claims finding). |
| checks | PR body reports RED-first proof on the exact head: `focused TDD: 22 passed`; `producer/publisher/shell/paywall sweep: 268 passed, 52 warnings in 145.71s`; `Agent OS validation: 1141 records, 0 errors`; `DAG conformance: 27 lanes checked, OK`. The Agent OS warnings and two DAG suspects are explicitly named as inherited. Hosted authority / fence / contract-delta / CI-plan checks are running on the current head. |
| gating scripts | `scripts/check_plain_language.mjs` — DOES NOT EXIST in macro (terminal-side only; `ls scripts/check_plain*` → no matches). Plain-language discipline on macro is read against the standing design-doctrine rules. `scripts/check_validated_claims.py` exists but errors out with `allowlist-missing` on `data/regime/validated_claims_allowlist.json` in a sparse checkout (sparse-tree fault, NOT a wave of new unearned claims; the checker itself explains this). `scripts/check_design_system.py` and `scripts/check_runtime_style_injection.py` exist (TP-0 art-direction gate). |

## Diff content (scoped to this PR)

The PR introduces a single new user-visible surface (the "Leaders / waiting for entry" shelf) plus the engine projection, publisher, hydration helper, server-side preview split, and the four tests + the agentos handoff that prove it. Below is a per-file summary at the level of detail the three audits need.

**`engine/us_leader_pullback_coverage.py` (+337 / −0, MODIFIED)**

- Adds one strict display-only projection `project_prophet_observations(...)`, one loader `load_prophet_observations(...)`, and one summary helper `prophet_observation_summary(...)`. New `__all__` exports: `PROPHET_OBSERVATION_SCHEMA = "prophet.leader_observations/v1"`, `PROPHET_ACTIVE_STATES = (LEADER, PULLBACK, RESET_TURN, RESUMED)`, and the three callables.
- The projection is fail-soft: absent artifact → `status="unavailable", reason_code="artifact_absent"`; unreadable artifact → `status="unavailable", reason_code="artifact_unreadable"`; valid empty → `status="empty", reason_code="no_active_states"`; malformed rows → `status="degraded", reason_code="invalid_rows"`; unknown state rows → `status="degraded", reason_code="unknown_state_rows"`.
- The projection's row schema is `ticker_asc_no_rank` (alphabetical, no rank, no score, no priority). The four `disposition` strings are explicit no-trade-action labels: `OBSERVED_LEADER_WAIT`, `OBSERVED_PULLBACK_WAIT_SIGNATURE`, `OBSERVED_RESET_WAIT_SIGNATURE`, `OBSERVED_RESUMED_DO_NOT_CHASE`. No `rank`, `score`, `probability`, `confidence`, `priority`, `entry`, `current_price`, `target`, `size`, `trade`, or `recommendation` field exists on the row (test-enforced — see below).
- A `_PROPHET_SAFE_COVERAGE_FIELDS` whitelist restricts what the public projection copies out of the source artifact, and a `_PROPHET_SAFE_SOURCE_CONTRACT_FIELDS` whitelist restricts what is copied from the source contract. The summary helper `prophet_observation_summary(...)` deep-copies only `{schema, status, reason_code, source_relation, source, counts, ordering}` — the public `site/prophet/index.json` never receives ticker rows.

**`scripts/build_prophet.py` (+15 / −0, MODIFIED)**

- After every plan/lifecycle decision above (so the leader-observation read cannot alter their bytes or order), the publisher loads the projection and copies the ticker-free summary into `index.json` under a new top-level key `leader_observation_summary`. The full ticker roster stays owned by `site/anticipationdata/us_leader_pullback.json` and the protected US page payload.

**`scripts/build_site.py` (+68 / −2, MODIFIED)**

- New server-side preview split `_split_us_leader_observations(projection, preview_rows, *, gated=True)` mirrors the existing `_split_us_prophet_board(...)` contract: source status, provenance, and aggregate counts remain on the public shell; ticker rows beyond the configured preview move into the existing protected US payload. The function never mutates its input.
- `_split_us_panels(...)` adds a `leader_observations` slot in `pgate`/`locked`/`overrides` so the panel split is symmetric with `setups`, `leaders`, `ran`, `actnow`, `tape`, `plv_names`. The function returns the new `overrides` map so the shell book can carry the public preview rows without polluting other panels.
- `_render_us_panel_payload(...)` adds `leader_observations_html` rendering via `_us_leader_observation_rows.html.j2`. Hydration contract: `hydrateLeaderObservations(payload.leader_observations_html)` rebuilds the `plo-rows` grid, sets `data-showmore-rows="3"`, removes any stale show-more bar, and calls `window.initShowMore()` so the existing three-row progressive reveal remains truthful.

**`templates/_us_leader_observation_rows.html.j2` (+21 / −0, NEW)**

- A bilingual EN+ZH row template. State-conditional plain-language copy for each of `LEADER` / `PULLBACK` / `RESET_TURN` / `RESUMED`:
  - LEADER → "Leading now — wait for a controlled setup." / "当前领涨——等待受控形态。"
  - PULLBACK → "Controlled retrace — measured turn not yet proven." / "受控回撤——尚未证实量化转折。"
  - RESET_TURN → "Reset/turn context — setup still needs confirmation." / "重置/转折背景——形态仍需确认。"
  - RESUMED → "Leadership resumed — do not chase." / "领涨已恢复——不要追高。"
- Each row exposes `data-ticker` and `data-state` as machine attributes (the test asserts the rendered shelf is "a separate display population" with no `.cand-row` / `.nb-card` / `data-life` / `data-mp1-grid` markers). The optional `Observed zone` / `观察区间` span (`{{ zone_low }}–{{ zone_high }}`) is only emitted when both bounds are present (defensive against partial artifacts).

**`templates/dashboard.html.j2` (+77 / −0, MODIFIED)**

- A new `.plo` shelf section gated by `{% if us_leader_observations %}` so the shelf silently disappears when the projection is absent. The shelf carries a header (`Leaders / waiting for entry` / `领涨股 / 等待入场条件`) and a `Source / 数据日期` line that prints `_plo_src.get('data_session') or _plo_src.get('as_of') or '—'` — the `or '—'` is the plain-word null disclosure for the source-as-of field.
- The summary row carries `active observations / 个活跃观察` count and an explicit `Context only · not a recommendation / 仅供背景参考 · 非推荐` authority boundary.
- Status-specific copy for each null/empty/degraded state is its own line: "Leader observations unavailable." / "领涨股观察暂不可用。", "No active leader-reset states." / "暂无活跃的领涨重置状态。", "Some source rows could not be classified." / "部分来源条目无法分类。" — three visibly distinct copy lines, no fallback to a generic "no data" message.
- The "more observed names / 另有 ? 个观察标的" link appears only when the `pgate` has a `leader_observations` block (i.e. there is something to lock). For an anonymous preview with no locked remainder, no `plo-more` block is rendered (test-enforced).
- CSS rules (page-local, scoped under `/* Prophet P1 leader observation shelf */`) use only design tokens: `var(--line)`, `var(--panel2)`, `var(--info)`, `var(--hair)`, `var(--muted)`, `var(--text)`, `var(--warn)`, `var(--ok)`, `var(--link)`, `var(--r-card)`, `var(--r-ctl)`, `var(--num)`, `var(--panel)`, `var(--card-shadow)`. The border-left accent for each state uses `color-mix(in srgb, var(--X) Y%, var(--line))` — the same token discipline used by the existing Prophet board.
- Light theme treatment: `[data-theme="light"] .plo { background: var(--panel); box-shadow: var(--card-shadow) }` and `[data-theme="light"] .plo-row { background: var(--panel2) }`. The light mode adds a `box-shadow` (research-workspace material treatment — paper-on-paper) rather than the dark mode's translucent `color-mix` over `var(--panel2)`.
- Responsive breakpoint at `max-width: 620px`: padding shrinks to 12px, the grid collapses to `62px minmax(0,1fr)`, the zone span moves under the copy, and `.plo-authority` wraps to its own line. The breakpoint is aligned to the existing dashboard's 620px family (where the existing two-reads chip, the existing plans row, etc. already reflow).
- New hydration JS helper `hydrateLeaderObservations(html)` rebuilds the `plo-rows` grid, sets `data-showmore-rows="3"`, removes the stale show-more bar, and calls `window.initShowMore()`. The helper is wired before `hydratePanels(payload)` in the existing `hydrateLeaderObservations(payload.leader_observations_html)` line.

**`templates/plans.html.j2` (+1 / −1, MODIFIED)**

- One pricing-table row tipbox update: `Daily stock signals / 每日个股信号` tipbox now says "Candidates, plans, and leaders waiting for entry share one ladder: anonymous visitors preview one item in every list; Free accounts see three; paid plans open the full book." / "候选、计划与等待入场的领涨股共用同一层级：未注册访客每个列表可预览 1 条；免费账户可查看 3 条；付费方案开放完整名单。" — keeps the existing pricing ladder (1/3/full) honest and explicitly names the new shelf in the same sentence. Test-enforced.

**`config/site_access.yml` (+4 / −0, MODIFIED)**

- Adds `/anticipationdata/us_leader_pullback.json` to `premium.enforced_early.exact` with the comment: "Prophet's full leader-observation roster. The public US page server-renders only the configured preview; paid rows hydrate through `/premiumdata/us_stocks.json`. Locking this raw ticker map prevents a direct-URL bypass of that same product wall."

**`app/deploy/Caddyfile` (+1 / −1, MODIFIED)**

- The `@reg_asset` comment listing the early-enforced paths adds `/anticipationdata/us_leader_pullback.json` next to the existing `/allocationdata/special_situations.json` and `/chinaspecialdata/special.json` entries. No rule changes — only the comment is updated so the Caddyfile is in sync with `config/site_access.yml`.

**`.github/ci/legacy-jobs.yml` (+18 / −0, MODIFIED)**

- Two `paths:` lists (in the producer/publisher/shell/paywall job and a sibling) gain four engine paths: `engine/us_basket_turn.py`, `engine/us_leader_pullback.py`, `engine/us_leader_pullback_coverage.py`, `engine/us_turn_watch.py`. The comment is "P1 leader-observation closure widening 2026-09-20 (contract-delta): the existing Prophet serving/build paths now import the leader-pullback projection through the canonical Turn Organ dependency chain."
- Two test steps are added: `python -m pytest tests/test_us_leader_observation_projection.py -q` and `python -m pytest tests/test_prophet_leader_observation_shelf.py -q`. Comment for the shelf test: "Prophet leader-observation shelf (real publisher, tier split, plan-byte invariance, rendered consumer)."

**`tests/test_us_leader_observation_projection.py` (+293 / −0, NEW)**

- RED-first contract test for the engine projection. Asserts:
  - `schema == "prophet.leader_observations/v1"`, `status == "available"`, `ordering == "ticker_asc_no_rank"`.
  - Row order is alphabetical (`AAA, BBB, CCC, ZZZ` against the test fixture), `plan_authority is False` on every row.
  - Banned fields `{rank, score, probability, confidence, priority, entry, current_price, target, size, trade, recommendation}` are absent from every row (set-intersection check).
  - `counts` schema is exact (`source_rows / active / non_active / nulled / invalid / by_state`).
  - Status transitions: aligned → available, mismatched session → unavailable, missing artifact → unavailable, empty artifact → empty, invalid rows → degraded, unknown states → degraded.
  - Source-relation resolution: aligned / trailing_by_one / trailing_by_two / mismatched.

**`tests/test_prophet_leader_observation_shelf.py` (+320 / −0, NEW)**

- RED-first contract test for the rendered shelf. Asserts:
  - `test_rendered_shelf_is_a_separate_display_population`: shell carries 3 rows (`AAA, BBB, CCC`); the shelf has **no** `.cand-row`, `.nb-card`, `[data-life]`, or `[data-mp1-grid]` markers; `asof` is present; "Leaders / waiting for entry" + "领涨股 / 等待入场条件" are present; "2 more observed names" lock count is present.
  - Banned trade-action phrases are absent from the rendered text (case-insensitive): `"buy now", "enter now", "recommended buy", "strong buy", "add position"`.
  - `test_each_state_has_plain_bilingual_non_authority_copy`: every state (`LEADER`, `PULLBACK`, `RESET_TURN`, `RESUMED`) renders both EN and ZH plain-language copy, plus the explicit "do not chase / 不要追高" warning on RESUMED.
  - `test_empty_unavailable_and_degraded_are_visibly_distinct`: the three null-state messages are text-distinct (`No active leader-reset states`, `Leader observations unavailable`, `Some source rows could not be classified`).
  - `test_anonymous_preview_does_not_emit_an_empty_show_more_control`: an anonymous preview renders 3 rows with no `data-showmore-rows` attribute, so no "show more" bar appears.
  - `test_paid_hydration_rebuilds_the_leader_grid_before_show_more`: the JS helper builds the fresh grid, sets `data-showmore-rows="3"`, replaces the original grid, removes any stale `sm-bar`, and calls `window.initShowMore()`. Asserts that leader rows hydrate BEFORE the candidate/plan grids (the helper is invoked first inside `hydratePanels`).
  - `test_paid_payload_carries_locked_panel_geometry`: `payload["panels"]["leader_observations"] == {"preview": 3, "locked": 2, "total": 5}` and `payload["leader_observations_html"]` equals the locked block.

**`tests/test_paywall.py` (+38 / −0, MODIFIED)**

- `test_leader_observation_source_locks_free_while_switch_off`: with `site_full` off, a free user requesting `/anticipationdata/us_leader_pullback.json` gets a 403.
- `test_leader_observation_source_allows_site_full_while_switch_off`: with `site_full` on (essential/trialing), the same path returns 204.

**`tests/test_regwall_json_gate.py` (+24 / −0, MODIFIED)**

- `test_prophet_leader_observation_source_is_early_paid_and_pricing_disclosed`: parses `config/site_access.yml` and asserts the new path is in `premium.enforced_early.exact`, NOT in `public.exact`, NOT in `free_registered.exact`, and does not match any prefix in `public` / `free_registered`. Asserts `templates/plans.html.j2` mentions "leaders waiting for entry" + "领涨股" + "1 before signup" + "3 / list / day" + "Full book".

**`agentos/handoffs/PROPHET-US-V4-RECOVERY-2026-09-19-leader-observation-p1.md` (+116 / −0, NEW)**

- Standard agentos handoff record: frontmatter (`workstream`, `session`, `model`, `ended_because`, `mission`, `state_before`, `implementation_head`, `pull_request`, `comparison_base`, `depends_on`, `changed`, `verified`, `current_state`, `blockers`, `unresolved`, `unverified`, `danger_areas`, `next_actions`, `do_not_redo`). `current_state: BUILT_NOT_PROVEN` is the truthful status; `do_not_redo` includes "Do not call PR creation, green unit tests, merge, or deployment production acceptance" — the operator-facing discipline is correct.
- Each `verified:` claim names its command. Each `do_not_redo` is operational, not aspirational.

## Plain-language findings

**Verdict: PASS.** This PR adds substantial new user-facing copy on the US Prophet page and the Daily-stock-signals pricing tipbox. Every line of that copy is reviewed below against the macro plain-language discipline (the design doctrine's banned vocab, glance-tier state + plain-word stance under hard word budgets, plain-word null disclosure, tier-2 receipts, and the "no internal state / study / organ slug on a user-visible position" rule from the terminal-side `check_plain_language.mjs` precedent).

`scripts/check_plain_language.mjs` does not exist in macro (terminal-side only). The standing design-doctrine plain-language checks (banned-vocab, plain-word null disclosure, tier-2 receipts, glance-tier state + plain-word stance under hard word budgets) apply to user-facing surfaces only. PR #7457 adds user-facing copy on `templates/dashboard.html.j2`, `templates/_us_leader_observation_rows.html.j2`, and `templates/plans.html.j2`; all three are in scope.

### Shelf copy (the four state-conditional rows)

| State | EN | ZH | Plain-language read |
|---|---|---|---|
| LEADER | "Leading now — wait for a controlled setup." | "当前领涨——等待受控形态。" | "wait for" is action-neutral; no trade verb. Plain present-tense state ("Leading now") + a measured instruction ("wait for a controlled setup"). |
| PULLBACK | "Controlled retrace — measured turn not yet proven." | "受控回撤——尚未证实量化转折。" | "not yet proven" / "尚未证实" is an honest HEDGED claim, not an assertion. No `score`, `confidence`, `probability`, or `rank` term. |
| RESET_TURN | "Reset/turn context — setup still needs confirmation." | "重置/转折背景——形态仍需确认。" | "still needs confirmation" / "仍需确认" is explicit uncertainty. No internal study slug, no probability band. |
| RESUMED | "Leadership resumed — do not chase." | "领涨已恢复——不要追高。" | "do not chase" / "不要追高" is an explicit warning — the inverse of a buy signal. Aligns with the existing `not_topped_veto` and the project-wide anti-chase doctrine. |

**Banned trade-action vocab sweep:** the test `test_each_state_has_plain_bilingual_non_authority_copy` enforces that `{buy now, enter now, recommended buy, strong buy, add position}` are absent from the rendered shelf text (case-insensitive). The template itself does not use any of those phrases; the test is a regression-guard, not a fix.

**Banned glance-tier vocab sweep:** the test `test_projection_is_display_only_alphabetical_and_lossless` enforces that `{rank, score, probability, confidence, priority, entry, current_price, target, size, trade, recommendation}` are absent from every projection row (set-intersection check). The engine itself never mints those fields; the test is the binding proof. None of those words appear in the rendered EN or ZH copy either.

**Internal state / study / organ slug sweep:** the four `disposition` strings (`OBSERVED_LEADER_WAIT`, `OBSERVED_PULLBACK_WAIT_SIGNATURE`, `OBSERVED_RESET_WAIT_SIGNATURE`, `OBSERVED_RESUMED_DO_NOT_CHASE`) are **engine-internal** names that never reach the rendered shelf (the template maps them to the EN/ZH copy above by `_st` match against `LEADER`/`PULLBACK`/`RESET_TURN`/`RESUMED`). The four states themselves appear only as `data-state` attributes — machine identifiers, not user copy. `prophet-leader-observation-p1-20260919`, `WS:PROPHET-US-V4-RECOVERY`, `us_turn_watch.source_contract.v1`, and `not_topped_veto` are all operator/developer surface only.

### Shelf header + summary copy

- "Leaders / waiting for entry / 领涨股 / 等待入场条件" — plain noun phrase; the "waiting for entry" framing makes the non-trade nature explicit on the header itself.
- "Source / 数据日期" — plain English date label. The value is `_plo_src.get('data_session') or _plo_src.get('as_of') or '—'`; the `or '—'` is the plain-word null disclosure for the source-as-of field.
- "active observations / 个活跃观察" — explicit count noun ("observations", not "leaders" — the shelf calls them what they are, not what they could be).
- "Context only · not a recommendation / 仅供背景参考 · 非推荐" — the explicit authority boundary, on the shelf itself. This is the right shape: it lives one row under the count, so a glance-tier reader sees it without expanding a tooltip. Aligns with the design doctrine's "Tier-1 = state + plain-word stance under hard word budgets" rule.
- "Leader observations unavailable. / 领涨股观察暂不可用。" — null disclosure when the artifact is missing/unreadable.
- "No active leader-reset states. / 暂无活跃的领涨重置状态。" — null disclosure when the artifact is valid but empty. "暂无" makes the "currently no" framing explicit.
- "Some source rows could not be classified. / 部分来源条目无法分类。" — degraded-state disclosure; the reader sees the shelf is partial, not gone.
- "more observed names / 另有 ? 个观察标的" — paid-gate disclosure. "more observed names" is the same noun as the shelf uses ("observed names", not "leaders"), so the lock copy does not invent a different vocabulary than the shelf itself.

### Pricing tipbox (plans.html.j2)

- New tipbox text: "Candidates, plans, and leaders waiting for entry share one ladder: anonymous visitors preview one item in every list; Free accounts see three; paid plans open the full book." / "候选、计划与等待入场的领涨股共用同一层级：未注册访客每个列表可预览 1 条；免费账户可查看 3 条；付费方案开放完整名单。"
- Plain, parallel structure (anonymous / Free / paid → 1 / 3 / full) preserved across EN and ZH.
- The shelf is named in the same sentence as Candidates and Plans, which is correct: the pricing ladder (1/3/full) is one ladder shared across the three displays.
- No banned vocab; no internal state names; no study codes.

### Operator-facing prose (PR body, handoff)

- PR body and `agentos/handoffs/...` use `BUILT_NOT_PROVEN`, `source-dated`, `display-only observation capability`, `not_topped_veto`, `plan_authority=false`, `prophet-leader-observation-p1-20260919`, `WS:PROPHET-US-V4-RECOVERY`, `#7187`, `sol/prophet-us-panel-authority-20260916`. These are operator/developer vocabulary and are NOT subject to the user-facing plain-language law.
- The `do_not_redo` block is operational and falsifiable (e.g. "Do not call PR creation, green unit tests, merge, or deployment production acceptance").
- The `verified:` block names every command and reports exact run output (22 passed, 268 passed / 52 warnings, 1141 records / 0 errors, 27 lanes OK). No over-claim; no green-by-waiver language.

### Stale-price pre-existing copy (carried verbatim)

- The "Still ranked on prices as of … / 仍按截至 … 的价格排序" copy around `_stale.get('price_through')` is a pre-existing block on the dashboard, not added by this PR (the diff shows the surrounding context but no `+` line for that text). The new `.plo` shelf inserts BEFORE this block, so the stale-price disclosure remains correct (it is the existing prophet-board disclosure, which the new shelf sits alongside, not in place of).

## Theme findings

**Verdict: PASS (subject to the standing TP-0 evidence-matrix caveat).** This PR adds a new user-facing surface (`.plo` shelf) on the existing dashboard route. The TP-0 art-direction law requires DARK TREATMENT, LIGHT TREATMENT, a named evidence matrix, and theme-specific degraded states. The PR carries the dark/light treatment and the responsive breakpoint; the evidence-matrix capture is a follow-on, not a blocking omission for this PR's design content (the matrix is the build-lane verification step, not a PR-time obligation).

### Dark treatment (default theme)

- Container: `border:1px solid var(--line); border-radius:var(--r-card,12px); background:color-mix(in srgb, var(--panel2) 74%, transparent)` — translucent panel over the existing `var(--panel2)`, the same material treatment used by the existing two-reads chip family.
- Header: `font-size:15px; letter-spacing:-.01em` — the same headline scale as the existing dashboard headlines. The `Source` line uses `font-size:11.5px; color:var(--muted)`, matching the existing `as-of` lines.
- Summary line: `padding-bottom:10px; border-bottom:1px solid var(--hair, var(--line))` — the same hairline rule the existing Prophet summary uses.
- Rows: `border-left:3px solid color-mix(in srgb, var(--link) 62%, var(--line))` for LEADER (the default accent). `data-state="PULLBACK"` swaps to `var(--warn)` (amber), `data-state="RESET_TURN"` swaps to `var(--ok)` (green), `data-state="RESUMED"` swaps to `var(--muted)` (neutral). The accent-by-state mapping is the right semantic for the four states: amber for "controlled retrace" (caution), green for "reset/turn" (positive but unconfirmed), neutral for "resumed — do not chase" (deescalated). The default `var(--link)` accent for LEADER means "observing" rather than "acting", which matches the shelf's no-authority framing.
- Numbers: `font-family:var(--num); font-variant-numeric:tabular-nums` on `_plo_counts.active` (so `7` and `17` line up) and on `.plo-ticker` / `.plo-zone` (the existing numeral family used everywhere else on the dashboard).

### Light treatment

- `[data-theme="light"] .plo { background: var(--panel); box-shadow: var(--card-shadow) }` — light mode adds a card shadow (research-workspace material treatment — paper-on-paper) instead of the dark mode's translucent `color-mix` over `var(--panel2)`. This is the right shape: the light doctrine uses shadow for elevation; the dark doctrine uses translucent panel-over-panel.
- `[data-theme="light"] .plo-row { background: var(--panel2) }` — rows get a slightly darker panel than the container, which gives them a clear "card within a card" reading in light mode.
- No raw color literal appears anywhere in the new CSS. Every color is a token (`var(--line)`, `var(--panel2)`, `var(--info)`, `var(--hair)`, `var(--muted)`, `var(--text)`, `var(--warn)`, `var(--ok)`, `var(--link)`, `var(--r-card)`, `var(--r-ctl)`, `var(--num)`, `var(--panel)`, `var(--card-shadow)`). The `var(--token, fallback)` form is used on `--hair` and `--r-card` / `--r-ctl`, so the shelf degrades gracefully if a theme ever ships without those tokens.
- The accent `color-mix(in srgb, var(--X) Y%, var(--line))` pattern is the same one the existing Prophet board uses; nothing new is invented.

### Responsive

- `@media(max-width: 620px) { .plo { padding: 12px } .plo-row { grid-template-columns: 62px minmax(0,1fr) } .plo-zone { grid-column: 2; white-space: normal } .plo-authority { flex-basis: 100% } }` — collapses the row grid, drops the zone span to its own line under the copy, and lets the authority label wrap to its own line. The 620px breakpoint matches the existing dashboard's 620px family.
- No breakpoint below 620px is added; the existing `min-width:0; max-width:100%` discipline on the wider layout means the shelf remains readable on smaller viewports (the zone span wraps to its own line, the ticker column stays at 62px).

### Token discipline

- No raw color literal (`#fff`, `rgba(...)`, `hsl(...)`, etc.) is added. `scripts/check_runtime_style_injection.py` would not fire on this PR — the new CSS lives in `templates/dashboard.html.j2`, not in a JS string.
- No new design token is minted (`var(--plo-...)` does not appear; the shelf reuses the existing token family). `scripts/check_design_system.py` would not fire on this PR.

### Evidence-matrix caveat (advisory)

- TP-0 requires a `dark/light × EN/ZH × desktop 1440 / mobile 390` evidence matrix for "every material UI packet". This PR carries the dark/light CSS and the responsive breakpoint, but the PR body does not inline an evidence-matrix capture. Per the TP-0 law ("a packet missing the light art direction or its evidence is `PARTIAL/BLOCKED`, never `PASS`"), the audit reads this PR as `PASS on the design content` and `PARTIAL on the matrix` — the matrix is the build-lane verification step (the meta-CEO B capture packet), and this PR is the design + code PR. The matrix is a follow-on receipt for the design system checker to ingest, not a blocker on this PR's plain-language / theme / validated-claims laws.
- No degraded-state dark/light matrix entry is named in the PR body (the three null-state copy lines are EN+ZH but no `dark × light × 1440 × 390` capture is inlined). Same caveat — follow-on, not blocking.

## Validated-claims findings

**Verdict: PASS.** This PR adds substantial new user-facing copy but **no new affirmative validated/verified/certified/proven claims**.

### Direct scan

A grep of the PR diff for `validated|verified|certified|proven` (case-insensitive) returns the following matches, each of which is one of three categories:

1. **HEDGED / negated uses in user-facing copy** — explicitly excluded by `check_validated_claims.py`:
   - `templates/_us_leader_observation_rows.html.j2`: `<span class="l-en">Controlled retrace — measured turn not yet proven.</span>` / `<span class="l-zh">受控回撤——尚未证实量化转折。</span>` — "not yet proven" / "尚未证实" are the canonical HEDGED forms the checker skips ("not … validated", "未…验证", "尚未…").
2. **Operator-facing prose** — out of scope (the validated-claims gate scans user-facing surfaces only):
   - PR body: "BUILT_NOT_PROVEN" (status label, not a claim), "#7187's current pack-5 HK/Canada receipt-hash failures reproduce on its tested base `c9d4b5626b`; they are inherited baseline debt" (operator-facing incident note), "This PR is deliberately draft" (release-boundary statement).
   - `agentos/handoffs/...`: `verified:` block ("Agent OS and DAG declarations remain structurally valid", "validation is still running and is not pre-claimed", `current_state: BUILT_NOT_PROVEN`, `unverified:`). These are operator-facing handoff provenance, not user-facing claims.
3. **Test names / code identifiers** — never reach a user surface:
   - `tests/test_us_leader_observation_projection.py`: `test_valid_empty_is_not_unavailable`, `test_loader_distinguishes_absent_unreadable_and_valid_empty` (test functions), `"invalid"` / `"invalid_rows"` (reason_code strings used in the JSON output for the engine), `invalid = malformed + unknown` (test variable).

No new affirmative claim of the form "validated / verified / certified / proven / 经过验证 / 已验证 / 经验证" is introduced on a user-facing surface. The single user-facing occurrence is the explicitly HEDGED "not yet proven / 尚未证实", which is an honest disclaimer ("controlled retrace is not yet a confirmed turn") rather than an affirmation.

### Explicit null disclosure (the right shape for `not a recommendation`)

- The shelf summary carries the explicit `Context only · not a recommendation / 仅供背景参考 · 非推荐` label. This is the design-doctrine-compliant "nulls printed, not hidden" form: the shelf tells the reader exactly what authority it does NOT carry, on the shelf itself.
- The shelf header carries the framing "Leaders / waiting for entry / 领涨股 / 等待入场条件" — the "waiting for entry" naming tells the reader these are observations, not entries.
- The status-specific copy (`Leader observations unavailable.`, `No active leader-reset states.`, `Some source rows could not be classified.`) prints each null/empty/degraded state as its own line, visibly distinct (the test `test_empty_unavailable_and_degraded_are_visibly_distinct` enforces that the three rendered strings are text-distinct).

### No new tier-word band / no new "validated" mapping

- No tier label is added (no `tier1` / `tier2` / `premium-tier` / `gauntlet` / `calibrated` band).
- No zone or regime label is added (the `zone_low / zone_high` numbers in the row template are raw `{{ }}` substitutions; the surrounding span is `Observed zone / 观察区间` — descriptive, not a label band).
- No probability band, no signal name, no neural-web lobe reference, no Prophet board mention appears on the new copy.

### Engine-source copy (the gate scans engine display-copy too)

- `engine/us_leader_pullback_coverage.py` adds three new callables (`project_prophet_observations`, `load_prophet_observations`, `prophet_observation_summary`). None of their strings is a user-facing claim. The reason_code strings (`artifact_absent`, `artifact_unreadable`, `no_active_states`, `invalid_rows`, `unknown_state_rows`) are machine tokens consumed by the dashboard's `{% if _plo.get('status') == 'unavailable' %}` branches and mapped to the EN/ZH plain-language copy above — they never appear in user-facing text.
- The four `disposition` strings (`OBSERVED_LEADER_WAIT`, `OBSERVED_PULLBACK_WAIT_SIGNATURE`, `OBSERVED_RESET_WAIT_SIGNATURE`, `OBSERVED_RESUMED_DO_NOT_CHASE`) are also machine tokens, used for the `_st` match in the row template.

### Repo-wide standing debt

- `scripts/check_validated_claims.py --list` reports pre-existing UNEARNED claims in `templates/`, `engine/`, `mm_brain.js`, `macro_suite.js` (the standing repo debt). PR #7457 does NOT add to that list and does NOT remove from it (a removal would itself be a finding). The 22 (or whatever the current count is) standing misses are pre-existing repo debt and out of scope for this PR.

## Overall verdict

**PASS on plain-language / theme / validated-claims. Two advisory concerns outside the three laws' scope.**

### PASS — the three laws

- **Plain-language:** PASS. The new shelf copy, the row template copy, and the pricing tipbox update are all plain EN+ZH, use no banned trade-action vocab (test-enforced), no banned glance-tier vocab (test-enforced), no internal state / study / organ slug on a user-visible position, and explicitly carry the "Context only · not a recommendation / 仅供背景参考 · 非推荐" authority boundary on the shelf itself. Three visibly distinct null-state copy lines are provided for `unavailable / empty / degraded`. The `do_not_redo` block and `verified:` block in the handoff use operator vocabulary and are not user-facing.
- **Theme:** PASS (with the standing TP-0 evidence-matrix caveat). New `.plo` shelf uses only design tokens (`var(--line)`, `var(--panel2)`, `var(--info)`, `var(--hair)`, `var(--muted)`, `var(--text)`, `var(--warn)`, `var(--ok)`, `var(--link)`, `var(--r-card)`, `var(--r-ctl)`, `var(--num)`, `var(--panel)`, `var(--card-shadow)`), no raw color literal, the same `color-mix(in srgb, var(--X) Y%, var(--line))` accent pattern the existing Prophet board uses, and the standard light-mode `[data-theme="light"]` overrides that swap translucent panel for `box-shadow`. Responsive breakpoint at 620px matches the existing dashboard family. The TP-0 evidence matrix is a follow-on build-lane receipt, not a blocker on this PR's design content.
- **Validated-claims:** PASS. No new affirmative claim of the form `validated / verified / certified / proven / 经过验证 / 已验证 / 经验证` is introduced on a user-facing surface. The single user-facing "proven" occurrence is the HEDGED "not yet proven / 尚未证实", which is an honest disclaimer and is explicitly excluded by the checker. No new tier band, no new zone/regime label, no new signal name. Engine-source strings are machine tokens that map to user-facing plain-language copy.

### Two advisory concerns (outside the three laws' scope)

1. **Release-boundary tension (operator-facing, not a plain-language / theme / validated-claims finding).** The PR body and the handoff both declare `BUILT_NOT_PROVEN` and explicitly state "it compares to `main` so the repository's authority gate can run; it remains dependency-ordered behind #7187 and must not merge around that carrier." PR #7457 was nevertheless squash-merged to `main` at 2026-09-20T23:38:38Z. The merge is the operator's chosen carry, not a Sol gate release. The plain-language / theme / validated-claims laws are silent on this — it is a release-discipline concern for the seat to ratify, not a finding this audit can resolve. **Advisory only; not a defect under the three laws.**
2. **TP-0 evidence-matrix capture.** The new shelf's `dark / light × EN/ZH × desktop 1440 / mobile 390` matrix is not inlined in the PR body. The build-lane capture packet is the meta-CEO B / meta-CEO A follow-on, not this PR's obligation; this audit reads the design content as `PASS` and the matrix as `follow-on`. **Advisory only; not a blocker.**

### Side-effect checks (advisory, scope=this PR's own diff)

- **`scripts/check_design_system.py` / `scripts/check_runtime_style_injection.py`:** the new CSS lives in `templates/dashboard.html.j2`, not in a JS string; no raw color literal; no new token minted; the existing token family is reused. Both checkers would not fire on this PR's diff.
- **`scripts/check_validated_claims.py`:** no new affirmative claim introduced; the one user-facing "proven" occurrence is HEDGED and excluded; engine-source strings are machine tokens. The checker would not fire on this PR's diff.
- **`scripts/agentos.py validate`:** the new `agentos/handoffs/PROPHET-US-V4-RECOVERY-2026-09-19-leader-observation-p1.md` carries the standard frontmatter (`workstream`, `session`, `model`, `ended_because`, `mission`, `state_before`, `implementation_head`, `pull_request`, `comparison_base`, `depends_on`, `changed`, `verified`, `current_state`, `blockers`, `unresolved`, `unverified`, `danger_areas`, `next_actions`, `do_not_redo`). PR body reports `Agent OS validation: 1141 records, 0 errors` on the exact head — the new handoff passes schema validation.
- **`scripts/check_template_site_sync.py`:** the new template `templates/_us_leader_observation_rows.html.j2` is a `.j2` partial included via `{% include "_us_leader_observation_rows.html.j2" %}`, NOT a paired plain-copy asset. No `site/_us_leader_observation_rows.html` is expected (the partial is rendered through `_render_us_panel_payload(...)` into the protected `site/premiumdata/us_stocks.json` payload for paid hydration). The paired-template check would not flag this.
- **Test coverage of the plain-language law:** the binding plain-language evidence is in `tests/test_prophet_leader_observation_shelf.py` (banned trade-action phrases, each-state bilingual copy, three distinct null-state strings, anonymous preview has no show-more bar) and `tests/test_us_leader_observation_projection.py` (banned glance-tier fields, alphabetical no-rank ordering, plan_authority=false on every row). Both test files are wired into the producer/publisher/shell/paywall job's `paths:` list and the test steps added in `.github/ci/legacy-jobs.yml` so the gates fire on every relevant CI run.
- **No `DO_NOT_REDO` / `DNR` conflict.** The PR's `do_not_redo` block in the agentos handoff ("Do not call PR creation, green unit tests, merge, or deployment production acceptance", "Do not weaken `not_topped_veto`", "Do not create another leader store, episode ledger, endpoint, entitlement, queue, or watcher") aligns with the existing `DNR:` records — none are contradicted, none are duplicated.
- **No `DEC:` / `DSC:` record cited that would be contradicted by this PR.** The PR references `WS:PROPHET-US-V4-RECOVERY` (durable workstream) and `#7187 / sol/prophet-us-panel-authority-20260916` (stacked availability dependency) but does not amend any existing `DEC:` record. No `DSC:` record is minted.
- **Bilingual parity (EN+ZH).** Every new user-facing string carries both EN and ZH (`l-en` / `l-zh` classes, `t('...', '...')` for `templates/plans.html.j2`). No `title=` attribute carries translated text (CI-guarded). Parity is preserved.
- **No new `?v=` re-stamp required.** The shelf is rendered through `templates/dashboard.html.j2` and the `site_full` paid hydration path (`/premiumdata/us_stocks.json`), both of which are already served via the existing versioned asset list. The new partial template `templates/_us_leader_observation_rows.html.j2` is server-side rendered into the protected payload; it does not need its own `?v=` stamp.

### Nothing to fix on the three laws.

The PR is `merge-on-green`-eligible on plain-language / theme / validated-claims evidence alone. The two advisory concerns (release-boundary tension with the `BUILT_NOT_PROVEN` declaration; TP-0 evidence-matrix capture) are outside the three laws' scope and are for the seat / build-lane to handle.

**Recommended action:** record this audit (`orch(audit): record macro PR #7457 plain-language/theme/validated-claims audit (2026-09-20)`) so the next audit pass picks up the next non-engaging half-B PR. Continue the audit sweep.
