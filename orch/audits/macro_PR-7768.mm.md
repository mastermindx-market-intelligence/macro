# Plain-language / theme / validated-claims audit — macro PR #7768

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7768](https://github.com/mastermindx-market-intelligence/macro/pull/7768) |
| title | `fix(admin): distinguish publisher records from delivery proof` |
| mergedAt | 2026-09-23T05:49:14Z |
| author | chriswong6031-creator |
| merge commit | squash onto `main` from `admin-publisher-receipt-labels-20260923-sol` |
| exact head | `dc235fdce050de611bd310da33ca56765f26f15e` |
| audit head | `origin/main` (post-merge) |
| files (2 changed, +32 / −8) | `admin/static/app.js` (+9/−8), `tests/test_admin_navigation_ux.py` (+23/−0) |
| half-B label | **half-B Admin Publisher presentation continuation** — bounded acceptance-only UI copy renewal on the existing `RENDER.marketing_publish` screen. Does NOT touch publisher/retry logic, the existing #7487 projection owner, the existing #7665 carrier, or any backend/schema/CSS/authentication surface. |
| program surface | Admin-only static SPA `admin/static/app.js`. User-facing surface is the `marketing_publish` screen (publisher queue + recent runs + dry-run) inside `admin/`. NO public site surface, NO landing page, NO template file changes. |
| scope (per body) | (a) Rename the legacy `posted` tile label to "Publisher records"; (b) refresh lede/section/empty-state/footnote copy so a Buffer receipt is never presented as confirmed delivery; (c) change one activity-row verb (`posted ${a.posted\|\|0}` → `recorded ${a.posted\|\|0}`); (d) add a structural test asserting the new labels and absence of the old labels. |
| durable owner | The rendered strings live in `RENDER.marketing_publish` (`admin/static/app.js` lines 10433–10566); the admin static asset is re-stamped via the existing immutables contract. No new durable state owner created. |
| checks (body claims) | (1) "26 tests passed" for `admin-js-no-undef`; the new structural test `test_publisher_receipt_labels_preserve_delivery_uncertainty` is the receipt and was verified by `grep -c "^def test_publisher_receipt" tests/test_admin_navigation_ux.py` → 1. (2) Browser shell with synthetic read-only inputs → "11 checks passed, zero unexpected browser errors, zero mutation requests". Body claims desktop 1440 + mobile 390 screenshots inspected; the audit accepts this as the body provides it (single-pass, no re-render). |
| gating scripts | `python3 scripts/check_validated_claims.py` — no PR-touched file introduces a new `validated` literal (the audit's grep over the diff returns 0 hits). `scripts/check_design_system.py` is not engaged because admin uses its own static asset (`admin/static/app.js`) and `admin/static/admin.css` (unchanged). |

## Plain-language findings

### Tier-1 (glance) — RENAMED + WALKED-BACK

The user-facing surface is `RENDER.marketing_publish` and the only changes are string literals inside one function. Each visible string changed:

| surface | OLD | NEW |
|---|---|---|
| Page lede | "What goes out next, what is stuck, and what already went. Approved, due posts leave through Buffer at the next slot." | "Review scheduled submissions, resolve blocked items, and inspect publisher records." |
| Tile label | `posted` → "Posted" | `posted` → "Publisher records" |
| Section header | "Recent posts" | "Recent publisher records" |
| Loaded-table footnote | "Engagement is polled after the post lands — a dash means the poller has not read that post yet, not a zero." | "A dash means no measurement is available, not zero. Metrics alone do not establish delivery." |
| Empty-table body | "Nothing posted yet. Live posts land here with their Buffer receipt once the publisher is armed and runs." | "No publisher records yet. Submission receipts and confirmed delivery remain separate." |
| Tile tooltip | "Show the recent posts and their receipts" | "Show publisher records; delivery is not confirmed here" |
| Activity row verb | `posted ${a.posted \|\| 0}` | `recorded ${a.posted \|\| 0}` |

### New disclosure card (inserted above the loaded-tile `<table>`)

```
<div class="note muted">Delivery: Not confirmed here. A publisher record is not delivery confirmation or permission to resend.</div>
```

### Plain-language evaluation per DESIGN_DOCTRINE §"rewrite, don't delete"

The rewrite is **honest and minimal**. It retires two unearned framings the previous copy carried:

1. **"Posted"** implied a delivery confirmation; "Publisher records" explicitly does not. The rename is the right call — the upstream Builder object stores everything short of a `provider_confirmed_at` envelope (per the body link to PR #7487 comment 5787525548), and the screen is the only thing that said otherwise.
2. **"Engagement is polled after the post lands"** carried an unstated "the post landed" assertion that the system cannot itself prove; replaced with a "metrics alone do not establish delivery" walk-back.

But the **new copy carries three small plain-language regressions** vs the old:

1. **Lede lost its orientation sentence.** "What goes out next, what is stuck, and what already went." was a clear three-bullet glance; the new "Review scheduled submissions, resolve blocked items, and inspect publisher records." reads as three imperative verbs (review / resolve / inspect) instead of three status categories. Status categories are more glance-tier; imperatives are more action-tier. The screen already has tiles underneath (Queued / Approved / Posting / Publisher records / Failed / Quarantined / Recalled) that do the status-category job, so the lede's redundancy loss is modest — but "resolve blocked items" reads as a vendor/PM instruction, not a page orientation line. A small clause-level wording win would be "Review what's queued, fix what's stuck, and inspect publisher records." (keeps the three-bullet cadence).
2. **"Submission receipts and confirmed delivery remain separate."** The word "remain" is passive-policy language; the page is not a terms-of-service page. "are tracked separately." or "are not the same thing." is more direct. The same passive tone appears in "Delivery: Not confirmed here." — "Not confirmed" is fine (it is the null disclosure), but the colon-label format reads as legal disclaimer. Acceptable for an admin tool; called out for the record.
3. **"Metrics alone do not establish delivery."** Reads cleanly. No regression.

### Tier-2 (hover/focus) — unchanged

No `title=`, `aria-label=`, or `hx-tip` content is touched. `grep -E 'title="|aria-label="' admin/static/app.js` in the PR diff hunks → 1 hit ("state unknown", pre-existing), no translations changed.

### Banned-vocabulary audit (DESIGN_DOCTRINE §"Falsifier/refutation language is never front-facing")

`grep -iE 'falsifier|refute|refuted|证伪|thesis|disproven' admin/static/app.js` against PR-touched hunks → **0 hits**. The renamed labels and disclosure card carry zero banned vocab.

### Plain-language on PR-touched admin surface

`admin/static/app.js` (+9 / −8): 6 string substitutions + 1 new disclosure `<div>` + 1 activity-verb substitution. No new vocabulary invented; the new words (`recorded`, `Publisher records`, `Not confirmed here`, `remain separate`) are all in the small-operator-adjacent English vocabulary expected of an internal admin tool. No untranslated stat or raw slug appears in the changed strings.

`tests/test_admin_navigation_ux.py` (+23): one new test function `test_publisher_receipt_labels_preserve_delivery_uncertainty` whose assertions are direct string-literal presence/absence checks on the renderer source — operator-facing test name, never user-facing.

## Theme findings

### Token discipline — zero token changes

The PR introduces 0 new CSS variables, 0 new colors, 0 new spacing/radius/font scales. `admin/static/admin.css` is unchanged. The added `<div class="note muted">` element uses the existing `.note.muted` class from the admin stylesheet.

`grep -E 'var\(--|#[0-9a-f]{3,6}|rgb\(|hsl\(' admin/static/app.js` in PR-touched hunks → 0 new CSS literals. The only style attribute in the diff is `style="margin-top:6px"` (carried over verbatim from the old footnote line).

### Dark vs light — unchanged

This is the Admin surface (`/admin/`), which is its own dark/light treatment and does not participate in the design-system TP-0 evidence matrix for the public site. The admin uses the existing admin stylesheet tokens. No token substitution occurs, no CSS changes.

### Responsive composition — unchanged

No viewport/media-query responsive code is touched. The admin app uses its existing fixed-grid layout (`tests/test_admin_navigation_ux.py` bodyline evidence covers desktop 1440 + mobile 390 screenshots — accepted as the body provides).

### Visual verification matrix

Body states "Desktop 1440 and mobile 390 screenshots were inspected" as part of the 11-check browser shell evidence. The audit accepts this as the body provides (single-pass, no re-render). Evidence owner: `/Volumes/Mastermind/evidence/admin-publisher-receipt-labels-20260923/`.

### Token-only is the right answer here

The PR is a string-only rewrite on the existing Admin surface. Zero CSS, zero token, zero template changes. The admin is not subject to the public site's TP-0 light-art-direction law — admin is its own dark/light treatment and was not touched.

## Validated-claims findings

### PR-touched surface: 0 UNEARNED added

`grep -iE '\bvalidated\b'` over the PR diff hunks:

| file | `validated` hits in PR diff | context |
|---|---|---|
| `admin/static/app.js` | 0 | — |
| `tests/test_admin_navigation_ux.py` | 0 | — |

**Net PR-caused `validated` literal additions: 0.**

### The new copy is the opposite of an unvalidated claim

The rename "Posted → Publisher records" and the disclosure "Delivery: Not confirmed here" are **walks-back of unvalidated claims**, not additions. The old copy's "Posted" tile label was effectively asserting delivery confirmation; the old footnote "Engagement is polled after the post lands" carried an unstated "the post landed" assertion. Both are corrected, not reinforced.

### Display-only flag posture

The new disclosure card is explicit null disclosure: "Delivery: Not confirmed here. A publisher record is not delivery confirmation or permission to resend." This is the compliant "plain-word null disclosure" form documented in DESIGN_DOCTRINE §"rewrite, don't delete". The empty-state line "No publisher records yet. Submission receipts and confirmed delivery remain separate." follows the same compliant shape.

### `python3 scripts/check_validated_claims.py`

Expected to report the same estate-wide pre-existing claims set it did before this PR merged. 0 hits anchor to PR-touched files.

## Diff content (scoped to this audit)

### `admin/static/app.js` (+9 / −8)

Six string substitutions + one new disclosure card + one activity-verb substitution inside `RENDER.marketing_publish`. No logic changes, no API call changes, no selectors/handlers/approval/dry-run behavior changes — the body's "Preserved contracts" list holds.

### `tests/test_admin_navigation_ux.py` (+23)

One new test function `test_publisher_receipt_labels_preserve_delivery_uncertainty` (lines ~305-326) asserts:

- The new tile label `["posted", "Publisher records", "var(--muted)"]` is present in the renderer source.
- The new section header `Recent publisher records` is present.
- The new disclosure `not delivery confirmation or permission to resend` is present.
- The empty-state `Submission receipts and confirmed delivery remain separate.` is present.
- The OLD tile label `["posted", "Posted",` is absent.
- The OLD lede `What goes out next, what is stuck, and what already went.` is absent.
- The OLD empty state `Live posts land here with their Buffer receipt` is absent.
- The OLD footnote `Engagement is polled after the post lands` is absent.
- The preserved-contract invariants still hold: `const posted = d.recent_posted || [];`, `posted: ["#pub-posted",`, `r.external_url`, `r.external_id`, the measurement-null guard `v2 == null ?` + `not measured yet`, the activity-verb `recorded ${a.posted || 0}`, and the entry-point wiring `pubWireGoLive(d);` + `onclick="pubRunDryRun(this)"`.

Good: the test doubles as a regression net for both the new copy and the preserved contracts.

## Overall verdict

**PASS — Plain-language / theme / validated-claims laws clean for PR #7768 (with three minor plain-language wording nits recorded above).**

- **Plain-language:** the rename "Posted → Publisher records" and the new "Delivery: Not confirmed here" disclosure are the **correct walk-backs of two unvalidated delivery claims** the old copy carried. The new copy is more honest and more accurate. Three small wording nits (lede cadence, "remain" passive, disclaimer-tone disclosure) are noted for the record but not blocking for an admin-internal tool where the audience is operators who already understand the buffer-vs-delivery distinction. No banned vocab. No machine slugs. No untranslated stats. No `title=` translated text added.

- **Theme:** 0 CSS / 0 token / 0 template changes. Admin surface uses its own stylesheet, which is byte-stable. TP-0's public-site light-art-direction law is not engaged (admin is not public site).

- **Validated-claims:** 0 UNEARNED anchored to PR-touched files. The PR is net-negative on unvalidated claims — it withdraws two ("Posted" tile label; "post lands" footnote assertion).

## Gaps / observations

- **No re-render performed.** Single-pass audit. Body-claimed browser-shell evidence (11 checks passed, desktop 1440 + mobile 390 screenshots inspected) is accepted as the body provides.

- **`admin/static/app.js` is on the Caddyfile `immutable` list?** It is NOT — the admin is served as a separate static bundle with its own `/admin/` cache policy. Body states that re-stamping the admin asset is part of the standard procedure; not audited here.

- **Three wording nits (logged, not blocking):**
  1. Lede cadence: the OLD three-bullet ("what goes out next / what is stuck / what already went") was more glance-tier; the NEW three-imperative ("review / resolve / inspect") is more action-tier. The tiles already do the glance-tier job underneath.
  2. "remain separate" / "Not confirmed here" use passive-policy register; a more direct verb ("are tracked separately" / "delivery is not confirmed here") would fit a tone closer to the page's tile labels.
  3. The disclosure card uses a colon-label format that reads as a policy disclaimer. Acceptable for an admin tool whose audience understands the buffer-vs-delivery distinction.

- **Audit scope is intentionally narrow.** This PR is bounded acceptance-only copy; it does not introduce, replicate, or alter the actual delivery-proof projection owner (which remains with the existing #7487 owner per the body). The retry/approval/dry-run/selectors/handlers remain unchanged.

- **Frozen-carrier marker is consistent with META-CEO B's standing rules.** New source custody is the locked `admin-publisher-receipt-labels-20260923-sol` worktree; the existing controller-owned #7665 carrier is explicitly untouched.

## DEV IATIONS

None. The PR's only deviation from the existing `RENDER.marketing_publish` shape is the string rewrites disclosed above. No new component, no new endpoint, no new state, no new CSS class.
