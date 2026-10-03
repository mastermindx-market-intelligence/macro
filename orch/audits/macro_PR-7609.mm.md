# Plain-language / theme / validated-claims audit — macro PR #7609

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7609](https://github.com/mastermindx-market-intelligence/macro/pull/7609) |
| title | `fix(admin): reliable Content Studio filtering and on-demand chart review` |
| mergedAt | 2026-09-22T18:34:13Z |
| merge commit | `7e66683b6d8f4c0780089a88828a08b9f7395316` (squash onto `main`) |
| branch tip (head) | `4cf87ea44eea46c1bd8d523dbc85a8c7da097b49` |
| audit head | `origin/main` (post-merge), audit-time `ae878a16cf` |
| files | **13 changed, +722 / −50.** Engine (admin back-end): `admin/marketing.py` (+79 / −1), `admin/server.py` (+13 / −1). UI templates: `admin/static/app.js` (+191 / −48), `admin/static/styles.css` (+19 / 0). Tests: `tests/test_admin_marketing.py` (+77), `tests/test_admin_navigation_ux.py` (+107), `tests/test_admin_server.py` (+58). Research/doc: `research/ADMIN_PANEL_REVAMP_2026-09-21.md` (+40 continuation section). Evidence: `research/evidence/admin-publishing-review-20260921/{browser-receipt.json,content-review-desktop.png,content-review-mobile.png,read-payload-comparison.json,source-receipt.json}` (NEW directory, 5 files). |
| half-B label | **half-B admin UI — Content Studio review workflow.** Half-B by the operator's tier-2 categorization: the PR changes admin UI rendering and user-facing copy, adds a worker-tested review workflow with browser-level evidence, and does not alter engine tier-1 logic. It is a continuation of the accepted #7602 ("Admin workspace revamp") half-B. |
| program surface | Admin `marketing_content` route (Content Studio). The page is rebuilt around a 12-card mount budget with `(desk × content-type × case-insensitive search)` filter intersection, plan-revision-pinned chart previews, and a `csIntelQueueOutcome` acknowledgement state machine that distinguishes `queued`, `local_only`, `refused`, and `unknown`. |
| scope (per body) | (a) Intersect desk + content-type + search before pagination. (b) Mount only 12 matching cards; Previous/Next reach all posts. (c) Switch the page + prefetch to `/api/marketing/content?charts=metadata`; default inline callers remain compatible. (d) Preview only on operator intent via `?id=…&revision=<sha256>`; reject missing/corrected/oversized/unreferenced/duplicate charts; reject client file paths. (e) Render SVG in `<img src="data:image/svg+xml,…">`, not as injected DOM. (f) Preserve the session boundary. (g) Provide retry / refresh on failed previews. (h) Prevent late responses overwriting a newly-selected page. (i) Drop the contradictory "nothing has been sent" claim; stop treating absent drop reasons as proof every draft passed. (j) Adversarial acknowledgement repair for the intraday `csQueueIntel` action. |
| durable owner | Admin read adapter `admin.marketing` + Admin HTTP server `admin.server` — same owners that drive #7602; no new route, no new engine module, no customer / payment / email / deployment mutation. The preview reader accepts only `{chart_id, sha256 revision}`; no filesystem path reaches the admin surface. |
| checks (body claims) | (1) "1,416 admin tests passed" after materializing source `data/` and `site/` trees — body-claimed, single-pass audit does not re-run. (2) "21 browser checks passed" — `research/evidence/admin-publishing-review-20260921/browser-receipt.json` enumerates the 21 named checks with `pass: true` for each. (3) Same-input payload measurement `2,875,956 → 40,294 bytes (98.60% smaller)`, same `c9d133b9…` revision, same 13 accounts / 38 posts / 27 chart refs — `read-payload-comparison.json` records it explicitly. (4) "1,414 passed in 72.74 s" and "1,416 passed in 72.39 s" admin regression numbers from the continuation doc are cited as the same wave's totals. (5) `node --check`, Python compilation, `git diff --check` all pass per body. |
| gating scripts | `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7609.diff` was not run inside this one-pass audit (single-pass policy). Diff is +19 CSS lines (administrative scope, additive) and +191 JS (workspace-internal, no user-facing copy outside the noted strings). Manual `grep` for the design-system reject patterns on the new CSS surface returns 0 hits (only existing-token references — see Theme findings). |

## Plain-language findings (tier-1 + tier-2 surface)

### Tier-1 (glance) — copy is plain and honest on every changed cell

The PR is a copy-and-flow repair; it deletes two misleading tier-1 lines and replaces them with honest ones. The audit walks the deletions vs the replacements.

| tier-1 cell | was | is | reading |
|---|---|---|---|
| section heading — drops | `Why posts died` | `Generation checks` | the section now describes what it MEASURES (generation checks), not what it PRESUMES (why deaths occurred) — the old wording was a verdict, the new wording is a topic |
| empty state — drops | `Nothing was dropped tonight` + `Every planned post got words and survived the read.` | `No drop reasons were recorded in this plan. This does not prove every draft passed; check the measured stages above.` | the operator no longer gets a green-looking "every draft passed" claim from an absence of evidence; the new copy names the asymmetry between absence-of-reasons and proof-of-pass |
| tilt explainer — page intro | `Nothing on this page has been sent. A post leaves here for the Outbox, waits for your decision there, and the Publisher sends it` | `Plan and delivery are separate. Review draft content here, make publishing decisions in the Outbox, and check the Publisher for sending status and receipts.` | the old copy asserted a negative ("nothing has been sent") the page cannot prove; the new copy names the three surfaces by their actual job (plan, Outbox, Publisher) and the handoff direction |
| review controls placeholder | (none — was inline 12-card slice) | `Search this plan` / `Ticker, headline, or draft text` | the input label and placeholder name what the search covers and what fields it searches |
| count chip (live region) | (none) | `1–12 of 48 matching posts · 38 in this plan` (sample values) | reads in plain "of / in" form; the `role="status" aria-live="polite"` wiring is the screen-reader equivalent |
| page chip | (none) | `Page 3 of 4` | plain ordinal count |
| queue acknowledgement — confirmed delivery | `Queued` | `Queued` (unchanged) | unchanged; the operator-visible state was always named |
| queue acknowledgement — local-only | (collapsed into one of the failure paths) | `Delivery unconfirmed` + `Saved as item-1 for alpha, but delivery to the publisher's queue is not confirmed. Check the Outbox record.` | names the asymmetry: the local enqueue happened, the publisher-queue did not confirm |
| queue acknowledgement — unknown effect | `No answer from the server, so nothing was queued. Try again.` (re-enabled write) | `Status unknown` + `Queue status is unknown. The request may have completed. Check this draft in the Outbox before trying again.` (button stays disabled) | the new copy refuses the false-negative ("nothing was queued") and refuses the false-positive (no retry that could double-send); the button stays disabled until the operator reconciles via Outbox |
| chart preview retry | (no retry path) | `Retry preview` / `Refresh plan` | names the action and its consequence; "Refresh plan" is correct because a `plan_changed` reason means a stale revision, not a transient network blip |
| empty-result recovery | (no explicit copy) | `No matching posts` / `Try another desk, type, or search. Clear filters to see the whole plan.` | names the recovery, not just the absence |

### Banned-vocabulary audit (DESIGN_DOCTRINE §"rewrite, don't delete")

`grep -iE 'falsifier|refute|refuted|证伪|thesis|disproven' admin/marketing.py admin/server.py admin/static/app.js admin/static/styles.css research/ADMIN_PANEL_REVAMP_2026-09-21.md` → only PRE-EXISTING hits:

- `admin/server.py` — `macro_thesis` route + comment about "thesis-grain over a committed JSONL ledger" (unchanged by this PR).
- `admin/marketing.py:1045` — `planned → written → validated → emitted, with drop reasons` (machine funnel docstring; unchanged).
- `admin/marketing.py:1467` — `if state not in ("seeding", "confirmed", "refuted"):` (hypothesis-state normalizer; unchanged).
- `admin/static/app.js:7966` — hypothesis-state pill mapping (`refuted → Drop the assumption.`); unchanged.

None of these are user-facing in the Content Studio view path this PR changes. The PR explicitly REMOVES one pseudo-verdict ("Nothing on this page has been sent") and one pseudo-negative ("nothing was queued") — both of which were the kind of front-facing false claim the doctrine bans. The new copy leans the other way (named acknowledgement states, named actions).

### Tier-2 (hover / focus / live region) — `aria-live`, `aria-pressed`, `aria-busy` correctly wired

- `#csReviewCount` carries `role="status" aria-live="polite"` so the count update is announced without forcing focus.
- `[data-type]` / `[data-acct]` filter buttons get `aria-pressed="true|false"` on toggle (the old onclick path only set `active` class — visual only).
- `csLoadPreview` sets `aria-busy="true"` on the chart body while the request is in flight and removes it on success / failure / abort.
- `aria-controls="mkt-post-gallery"` on Previous/Next binds the pager to the gallery it controls (the old path had no `aria-controls`).
- No new `title=` attributes were introduced (`grep -nE 'title="' admin/static/app.js admin/static/styles.css admin/marketing.py admin/server.py` returns 0 hits on the new surface; the existing `title=` usages in `admin/static/app.js` are pre-existing on `csQueueIntel`'s helper).

### State semantics — explicit, action-verb-driven, no "neutral / unknown / no signal"

The PR explicitly rejects the old ambiguous mapping and replaces it with four named outcomes (`csIntelQueueOutcome`):

| outcome | button label | message | operator action |
|---|---|---|---|
| `queued` | `Queued` | `Queued as ${id} for ${acct}.` | nothing further on this card |
| `local_only` | `Delivery unconfirmed` | `Saved as ${id} for ${acct}, but delivery to the publisher's queue is not confirmed. Check the Outbox record.` | disabled until Outbox reconciles |
| `refused` | (back to original label) | `Refused by ${gate}.` | nothing further on this card |
| `unknown` | `Status unknown` | `Queue status is unknown. The request may have completed. Check this draft in the Outbox before trying again.` | disabled until Outbox reconciles |

The four are not synonyms of "neutral" / "no signal" / "unknown". Each one names a real operator next step, and the disable-state on `local_only` and `unknown` makes the carrier's NO-EFFECT-YET semantics visible — the old code re-enabled the button after a lost ack and let a retry double-send, which is the exact defect the doctrine's "instrument verdicts are NOT market verdicts" law exists to prevent at the data tier; this PR applies the same principle at the action tier.

## Theme findings

### Token discipline — no new token family introduced

`.cs-review-controls`, `.cs-review-pager`, `.cs-chart-preview`, `.cs-chart-body` — every new CSS rule uses existing tokens: `var(--border)`, `var(--surface2)`, `var(--text)`, `var(--muted)`, `var(--accent)`, `var(--r-sm)`. No new color, no new spacing scale, no new radius scale. The accent-tinted focus ring (`outline:2px solid var(--accent); outline-offset:3px;`) is the existing admin pattern. No hex literals, no `color-mix(…)` or `oklch(…)` function literals — `FUNC_COLOR_RE` is not touched. No `box-shadow:` outside the existing admin materials.

### Dark vs light — within token substitution scope, honestly scoped

The PR body states: "Desktop 1440×960 and mobile 390×844 screenshots reviewed; inherited English/dark admin style, not claimed light/Chinese certification." The audit honors this: the admin workspace does not yet have a fully-evidenced light/Chinese surface, and the PR does not pretend otherwise. The 19 new CSS lines use existing tokens, so by token-substitution the rules render in both themes; but because light/Chinese admin certification is not yet achieved project-wide, this PR cannot claim it. **The +19 CSS passes the token-substitution surface but does NOT carry a light/Chinese evidence pack** — this is the honest scope cut, not a defect, and the operator's existing admin-ratchet work (per `research/ADMIN_PANEL_REVAMP_2026-09-21.md` §6) tracks light/Chinese and deeper accessibility as a separate wave.

### Responsive composition

`@media (max-width:600px)` collapses the review-controls row: `<label>` flexes to `flex-basis:100%`, buttons share `flex:1 1 auto`, the pager switches to `justify-content:space-between`. The mobile evidence (`content-review-mobile.png`) is a 390×844 capture; the body claim of "Mobile review does not overflow" is one of the 21 browser checks (`browser-receipt.json` §14). The chart preview's `<img max-width:100%; height:auto; margin:auto;>` keeps the preview contained at any viewport.

### Visual verification matrix (body-claimed)

`research/evidence/admin-publishing-review-20260921/{content-review-desktop.png, content-review-mobile.png}` are the two screenshots (desktop 1440×960, mobile 390×844). `browser-receipt.json` enumerates 21 named browser checks with explicit `pass: true` for each. Single-pass audit does not re-render or re-run — the body claim is the receipt.

## Validated-claims findings

### PR-touched surface: 0 UNEARNED

`grep -nE "validated" admin/marketing.py admin/server.py admin/static/app.js admin/static/styles.css` against the diff hunks:

- `admin/marketing.py:1045` — pre-existing docstring (`planned → written → validated → emitted`); unchanged by this PR.
- `admin/marketing.py:1108` — pre-existing JSON field (`n_validated`); unchanged.
- `admin/marketing.py:2721` — pre-existing comment ("validated independently"); unchanged.
- `admin/server.py:1686` — pre-existing comment ("validated against the folded current status"); unchanged.
- `admin/static/app.js:1366` — pre-existing pill-class mapping (`s === "validated"`); unchanged.
- `admin/static/app.js:7102` — pre-existing accounting comment; unchanged.

**Zero new `validated` literals were introduced by this PR.** This is the opposite pattern from a regression — the PR actively REMOVES misleading front-facing claims and replaces them with named acknowledgement states. The two removed lines ("Nothing on this page has been sent" and "Nothing was dropped tonight … every planned post got words and survived the read") were exactly the kind of unbacked "validated" assertion the doctrine bans.

### Honest scope disclaimer (body-cited, audit-confirmed)

The body and the continuation doc both name the scope honestly:
- "This is a committed local plan, not a production latency claim."
- "Same-input payload measurements, not production latency measurements or a claim about the size of every future plan."
- "Active publisher/media/editorial carriers #7487/#7489/#7493 are untouched. This does not redefine `posting` as external delivery proof or supersede their approvals."
- "A confirmed queue receipt is still not external publication proof."
- "Desktop 1440×960 and mobile 390×844 screenshots reviewed; inherited English/dark admin style, not claimed light/Chinese certification."

Every body claim that could be misread as a "validated" assertion carries its scope disclaimer next to it. This is the validated-claims doctrine working as intended — the operator reads the receipt and the boundary at the same time.

### Estate-wide check (not run inside this one-pass audit)

`python3 scripts/check_validated_claims.py` was not re-run inside this single-pass audit (the prior #7712 audit ran it and reported 38 PRE-EXISTING estate-wide unbacked claims anchored to files outside the PR-touch set; the same 38 should be present on `origin/main` at audit time, since this PR touches admin-side files and none of the 38 anchored to `templates/_macro_suite_shell.html.j2`, `templates/canada.html.j2`, `templates/hk.html.j2`, `templates/macro_*.html.j2`, `templates/macro_suite.js`, `templates/mm_brain.js`, `site/macro_*.html`, `site/macro_suite.js`, `site/mm_brain.js`, `engine/market_os/macro_workspaces/consumer.py` are touched here).

## Diff content (scoped to this audit)

### `admin/marketing.py` (+79 / −1)

- `_CONTENT_CHART_MAX_BYTES = 2_000_000` — preview size bound (existing 2 MiB cap pattern; same number as `app.js` chart payloads).
- `_content_revision(plan)` — SHA-256 over `json.dumps(plan, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`. Comment: "Identity of the complete source snapshot, including corrected chart bytes. This is a read receipt, not a new store or publication authority."
- `_content_chart_metadata(chart)` — pure dict extraction (id, title, caption, `preview_available`), no SVG byte carry-through.
- `content_chart(chart_id, revision, root=None)` — new read adapter. Rejects: invalid request (bad id/revision), `plan_unavailable` (no plan file), `plan_changed` (revision mismatch), `chart_not_found` (unreferenced), `chart_ambiguous` (duplicate id), `chart_unavailable` (empty/oversized/missing-id). Never accepts a filesystem path. The body of the function is the exact mirror of the test names in `tests/test_admin_marketing.py::TestContentReviewReads` — `plan_changed` is fired by the same-day correction test, `chart_ambiguous` by the duplicate test, `chart_unavailable` by the absent/malformed/oversized parametrized test.
- `content(root=None, *, chart_mode="inline")` — new `chart_mode` kwarg. `"metadata"` replaces each `featured_chart` with its metadata dict; `"inline"` preserves the existing behaviour. The function returns `content_revision` regardless of mode (so the API always carries the revision; only the chart bytes are gated).
- `_stamp(post, acct_id)` — one-line addition that swaps `featured_charts` to metadata when mode is `metadata`.

### `admin/server.py` (+13 / −1)

- `/api/marketing/content` now reads `q.get("charts")`, defaults to `inline`, accepts `metadata`. Bad value → 400 with `{"ok": false, "error": "Unknown chart representation."}`.
- New `/api/marketing/content/chart?id=…&revision=…` route. Status codes: 200 on success; 400 on `invalid_request`; 404 on `chart_not_found`; 409 on `plan_changed` / `chart_ambiguous`; 503 on `chart_unavailable`. The existing `_authed` session guard is preserved (the `test_content_chart_read_remains_behind_existing_session_guard` test pins this).
- No new mutation surface, no new write path, no new operator that talks to the publisher or the email pipeline.

### `admin/static/app.js` (+191 / −48)

- `TAB_PREFETCH_PATHS.marketing_content = ["/api/marketing/content?charts=metadata"]` — the prefetch is the lighter metadata mode.
- `csDropPanel` — rewritten: `Why posts died` → `Generation checks`; the empty-state copy is rewritten to the honest variant.
- `CS_REVIEW = null` (module-level ephemeral UI selection, never persisted).
- `CS_FORCE_REFRESH = false` (one-shot force flag for the `Refresh plan` button).
- `csReviewPage(entries, selection, pageSize)` — pure filter+paginate helper. The 48-post fixture test (`test_content_review_intersects_filters_before_twelve_card_pagination`) covers: 12-card ceiling, page-2 offset, page-999 clamping, page-(-1) clamping, pageSize > 12 clamping, type+account intersection in both orders, case-insensitive search across `headline|ticker|cashtag|body|type|desk`, multi-word trimmed query, search beyond first page, empty result shape `from=0 to=0 page=1 pages=1 total=0`, non-mutation (`JSON.stringify(entries) === original`), and rejection of `{null, {}, {post:null}}`.
- `csRefreshPlan()` — sets `CS_FORCE_REFRESH=true`, clears the API cache, navigates to the page.
- `csRenderReview()` — single render path used by every control. Reads `CS_REVIEW`; bails if `CURRENT !== "marketing_content"` or `state.epoch !== ADMIN_RENDER_EPOCH` (late-response guard). Updates `aria-pressed`, toggles the `.mkt-acct-section` show/hide, wires the per-card preview toggle to `csLoadPreview`.
- `csLoadPreview(details, revision, epoch)` — the chart reader. Verifies `chart.id`, `response.content_revision === revision`, `chart.svg` is a non-empty string. Renders as `<img src="data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}">` (NOT injected SVG DOM). `previewState` machine: `undefined → loading → loaded | failed` (with cleanup paths for unmount, late epoch, plan-changed). Retry button text is conditional: `Refresh plan` for `plan_changed`, `Retry preview` for transient errors.
- `csWireReview(entries, card, revision, epoch)` — binds every control to the single `CS_REVIEW` selection so the type filter and desk filter compose (old code overwrote each other's visibility). Search input is `.oninput` (no submit button). Pager is `csReviewPrev` / `csReviewNext`. The `Refresh plan` and `Open Outbox` buttons are wired last.
- `RENDER.marketing_content` — now reads `CS_CONTENT_PATH + (force ? "&force=1" : "")`. Throws on `{ok:false}` instead of swallowing it (the old path returned `nwEmpty` and lost the cause). The `gallery.innerHTML` is assigned exactly once per render — no per-filter innerHTML rewrite.
- `csIntelQueueOutcome(result)` — the four-state classifier (`queued` / `local_only` / `refused` / `unknown`). The reason-key allowlist (`CS_INTEL_REFUSAL_LABEL`) is the existing one; `unknown` and `local_only` keep the button disabled.
- `csQueueIntel(btn)` — rewritten to use the classifier. `queued` → green toast + done. `local_only` / `unknown` → disabled state + named message + optional `Open Outbox` button. `refused` → original label restored + named gate. The button-disabled check at the top (`if (!btn || btn.disabled) return`) is the no-double-send guard; the test `test_content_queue_lost_ack_never_claims_no_effect_or_reissues_write` proves `calls.length === 1` after a second invocation.
- `mktFilterPosts(type, btn)` / `mktSwitchAcct(acct, btn)` — simplified to a single selection update + `csRenderReview()` (no more per-element `classList.toggle("hidden", ...)` that overwrote each other's visibility).

### `admin/static/styles.css` (+19)

The 19-line block:

```css
.cs-review-controls { display:flex; align-items:flex-end; flex-wrap:wrap; gap:10px; margin:16px 0; }
.cs-review-controls label { display:flex; flex:1 1 260px; min-width:0; flex-direction:column; gap:7px; color:var(--muted); font-size:12px; }
.cs-review-controls input { box-sizing:border-box; width:100%; min-height:40px; padding:10px 12px; border:1px solid var(--border); border-radius:var(--r-sm); background:var(--surface2); color:var(--text); font:inherit; }
.cs-review-controls input::placeholder { color:var(--muted); }
.cs-review-controls .btn, .cs-review-pager .btn { min-height:40px; }
.cs-review-pager { display:flex; align-items:center; justify-content:center; gap:14px; margin:16px 0 26px; }
.cs-chart-preview { margin:12px 0; border:1px solid var(--border); border-radius:var(--r-sm); }
.cs-chart-preview > summary { min-height:40px; padding:10px 12px; cursor:pointer; color:var(--accent); font-size:12px; }
.cs-chart-body { overflow:hidden; padding:12px; }
.cs-chart-body img { display:block; max-width:100%; height:auto; margin:auto; }
.cs-chart-body .sub { overflow-wrap:anywhere; }
.cs-review-controls :focus-visible, .cs-review-pager :focus-visible, .cs-chart-preview > summary:focus-visible { outline:2px solid var(--accent); outline-offset:3px; }
@media (max-width:600px) {
  .cs-review-controls label { flex-basis:100%; }
  .cs-review-controls .btn { flex:1 1 auto; }
  .cs-review-pager { justify-content:space-between; gap:8px; }
}
```

Every value is an existing token or a plain CSS keyword. Min-heights (40 px) match the existing admin focus-target pattern. Focus-visible ring uses `var(--accent)` — same as the rest of the admin shell. No new shadow, no new gradient, no new font, no new color.

### `tests/test_admin_marketing.py` (+77)

New `TestContentReviewReads` class with 8 named tests: `test_metadata_preserves_plan_and_defers_only_chart_bodies` (98.6% size drop, all fields equal except `featured_charts`), `test_preview_joins_only_the_exact_referenced_chart`, `test_same_day_correction_invalidates_old_preview`, `test_unreferenced_and_duplicate_charts_fail_closed`, `test_absent_malformed_or_oversized_preview_is_explicit` (parametrized over None/"" / "   " / 42 / 2_000_001-char string), `test_invalid_preview_request_is_rejected` (parametrized over id/revision combinations), `test_missing_plan_and_invalid_mode_are_distinct`, `test_revision_is_stable_under_key_order_but_not_corrections`. The class docstring ("The review transport is lighter without losing posts or mixing revisions") names the invariant.

### `tests/test_admin_navigation_ux.py` (+107)

New `test_content_review_intersects_filters_before_twelve_card_pagination` (the 48-post fixture, 12 assertions), `test_content_review_uses_light_reads_and_never_inlines_chart_documents` (asserts `"/api/marketing/content?charts=metadata"`, `csWireReview(…)`, no `allPosts.map(postCardHtml)`, no `${featured.svg}`, `data-cs-preview`, `renderEpoch !== ADMIN_RENDER_EPOCH`, NOT `'Nothing on this page has been sent.'`, `<img>`, no `.innerHTML`, `response.content_revision !== revision`, `details.isConnected`, `plan_changed`, `Retry preview`, `Refresh plan`), `test_unrecorded_drop_reasons_are_not_reported_as_passed_drafts`, `test_content_queue_distinguishes_local_delivery_refusal_and_unknown_effect`, `test_content_queue_lost_ack_never_claims_no_effect_or_reissues_write` (the lost-ack simulation; asserts `calls.length === 1`, `Status unknown`, "may have completed", NOT "nothing was queued", 1 link button, `disabled: true`).

### `tests/test_admin_server.py` (+58)

`test_content_review_representation_and_revision_routes` (route surface + status codes), `test_content_chart_read_remains_behind_existing_session_guard` (the auth-wall assertion — anonymous `content_chart` request returns 401 with `called == []`).

### `research/ADMIN_PANEL_REVAMP_2026-09-21.md` (+40)

New "Continuation: Content Studio review workflow" section with the before/after, measurements and evidence, scope held and next action, and the acknowledgement-boundary discovery. Honest about scope: "Full post-materialization admin regression run: 1,414 passed in 72.74 seconds, with default data/module guards retained"; "Production delivery remains a separate receipt on the wave's GitHub PR; this committed document does not substitute local browser success for a live integration result"; "The full admin program remains incomplete."

### Evidence pack (`research/evidence/admin-publishing-review-20260921/`)

- `browser-receipt.json` (NEW, +95) — 21 named checks, all `pass: true`, `errors: []`, `writes: []`, `chart_reads: [id=chart-001&revision=8ae2cbeb…]`. The two `chart_reads` entries prove the preview reader fired exactly twice (once on toggle, once on retry-failed state) — no eager prefetch of chart bytes.
- `read-payload-comparison.json` (NEW, +22) — same-input payload: inline `2,875,956 bytes` vs metadata `40,294 bytes`, identical `revision`, identical `accounts/posts/charts` counts, source root pinned to `/Volumes/Mastermind/worktrees/admin-revamp-20260921`. Explicit `scope` field: "Same committed local content-plan input, not production latency."
- `source-receipt.json` (NEW, +21) — SHA-256 of the four PR-touched source files + the test counts + `visual_scope: "existing dark/English admin; desktop1440x960 mobile390x844"` + `skillpack_commit: "74b475545e179a3256bfebe6b5226f54231cf1cb"` + `base_commit: "91d0269481fef77e82dc0ba6f9469bd2585ad7e7"`. Honest visual-scope disclosure.
- `content-review-desktop.png` + `content-review-mobile.png` (NEW, 2 binary) — the screenshots.

## Overall verdict

**PASS — Plain-language / theme / validated-claims laws all clean for PR #7609.**

- **Plain-language:** tier-1 copy is plain English on every changed cell; tier-2 (search input, pager, retry, refresh) is `aria-live` / `aria-pressed` / `aria-busy` / `aria-controls` wired, not `title=`. The PR DELETES two front-facing false claims ("nothing has been sent" and "every planned post got words") and replaces them with honest named acknowledgement states (`Status unknown` / `Delivery unconfirmed` / `Queued`) — exactly the rewrite-don't-delete pattern the doctrine asks for. No banned vocabulary introduced; pre-existing uses are unchanged admin routes (macro_thesis, hypothesis pills) outside the touched surface.
- **Theme:** 19 lines of CSS, all on existing tokens (`var(--border)`, `var(--surface2)`, `var(--text)`, `var(--muted)`, `var(--accent)`, `var(--r-sm)`), no new token family, no hex, no `color-mix` / `oklch`, no shadow. Mobile breakpoint at 600 px. Honest scope cut on light/Chinese certification (acknowledged in body, doc, and `source-receipt.json`); not a defect, the operator's separate admin-ratchet wave tracks it.
- **Validated-claims:** 0 new `validated` literals introduced; the PR actively REMOVES misleading claims. Every body claim that could be misread as a "validated" assertion carries its scope disclaimer (same-input local plan, not production latency; confirmed queue receipt, not external publication proof; dark/English inherited, not claimed light/Chinese). The four-state `csIntelQueueOutcome` machine (queued / local_only / refused / unknown) replaces a single ambiguous "Queued" or "Try again" surface with four named operator actions.

## Gaps / observations

- The PR explicitly does NOT carry a light-theme or Chinese-locale certification on the new surface. The body, doc, and `source-receipt.json` all name this. The admin workspace does not yet have a fully-evidenced light/Chinese surface project-wide (per `research/ADMIN_PANEL_REVAMP_2026-09-21.md` §6). A later wave owns that — out of scope for this audit and not a regression.
- The "Active publisher/media/editorial carriers #7487/#7489/#7493 are untouched" line in the body is the right shape — this PR explicitly does NOT redefine `posting → posted` as external delivery proof, and explicitly does NOT touch the Publisher or Outbox. The `local_only` state carries the honest "delivery to the publisher's queue is not confirmed" wording so the operator cannot mistake it for "posted".
- `scripts/check_design_system.py` and `scripts/check_validated_claims.py` were not re-run inside this one-pass audit. The +19 CSS touches no token family; the `validated` literal counts on PR-touched files are exactly the pre-existing set (0 new). Manual greps substitute.
- The 21 browser checks in `browser-receipt.json` are the body-claimed receipts; single-pass audit does not re-run the loopback fixture. The accompanying `source-receipt.json` pins the four source SHAs the receipts were taken against.

## DEV IATIONS

None. The PR is additive in user-facing copy (rewrites only), additive in read adapter (`content_chart` is a new function), additive in tests (3 files, 8 named tests + 2 named auth/route tests + 5 named JS tests), and additive in evidence (5 new files in `research/evidence/admin-publishing-review-20260921/`). No new write path, no new mutation surface, no new route (the `?charts=metadata` query is a sub-mode of the existing `/api/marketing/content`), no new operator on the Publisher or email pipeline. The auth wall on `content_chart` is the existing `_authed` guard. The lost-ack defence preserves the no-double-send invariant.

---

SESSION END: PROVEN_OUTCOME (one-pass audit delivered; no durable write to remote host; file written to local `orch/audits/macro_PR-7609.mm.md`)
