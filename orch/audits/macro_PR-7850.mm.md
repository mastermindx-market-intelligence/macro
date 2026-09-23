# Plain-language / theme / validated-claims audit — macro PR #7850

Auditor: qwen_auditor2-style one-pass, half-B scope. Date: 2026-09-23.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7850](https://github.com/mastermindx-market-intelligence/macro/pull/7850) |
| title | `research(prophet-us r6/w2): B04 evidence-dossier contract census (read-only)` |
| mergedAt | 2026-09-23T23:11:12Z |
| merge commit | squash onto `main` from `claude/pu-w2-b04-dossier-census` (`e9ee7281afce08133f2f06f25ae7b25ae609b364`) |
| head SHA | `40a8e9eefb377174a10cf7337a33e5a4cd94e4c3` |
| audit head | the read-only nature of the payload makes the post-merge `origin/main` redundancy acceptable; the two added files are byte-identical between the PR's head commit and their `origin/main` blob references (the PR is the canonical owner of both files) |
| files | **2 changed, +282 lines, 0 deletions, 0 modifications.** Both files are NEW (`status:"added"` per `gh api pulls/7850/files`). (i) `research/prophet_v4/r6_program/rulings/R6-B04-01_DOSSIER_CONTRACT_2026-09-24.md` (+25 lines). (ii) `research/prophet_v4/r6_program/wave2/B04_EVIDENCE_DOSSIER_CONTRACT_CENSUS_2026-09-23.md` (+257 lines). No `data/`, `site/`, `engine/`, `scripts/`, `tests/`, `templates/`, `templates/navigation-refresh.css`, `templates/nav_market.js`, `templates/theme.js`, `config/`, `ops/`, `.github/workflows/`, or `.github/ci/` bytes move. |
| half-B label | **half-B R6-B04 census + ruling pair** — wave 2 of the prophet-us R6 program; B04 is the episode evidence dossier contract. The pair is "ruling → census" (not "census → ruling"), which is the R6 wave-2 convention: the seat rules first (R6-B04-01, dated 2026-09-24 even though merged 2026-09-23T23:11Z, because the ruling text was authored before the censuses of B04/B16-a locked), then the wave-2 census retroactively inherits the ruling's amendments. The build order fix is named "B04 → B16-a → B08/B09 → C/D05/D11 — case 3/5 (BLIND) first". |
| program surface | none on the user-visible land. Both files live under `research/prophet_v4/r6_program/`; one is a seat ruling (markdown prose + bullet list of accepted amendments + a §"Build order" footer), the other is a wave-2 census (markdown prose + four tables + two JSON-mock examples + a short "Open questions" footer). Neither is a glance-tier page, a tier-2 panel, a template, a CSS surface, a JS surface, or any rendered production artifact. |
| scope (per body) | The body opens with the line "This read-only census maps the existing B1-to-D5 episode intelligence projection, route boundary, clocks, revision receipts, rights behavior, original/current-view limits, and D07 hooks, then proposes the closed B04 dossier contract and bounded build units. It changes no code and reads no outcomes." Authority = R6 work card B04 (`DEC:PROPHET-US-FABLE-META-CEO-DELEGATION`). Head SHA = `c1c8657bc15f32ea0eaf202781c08f47877b09fc`. Tests named: `python3 -m pytest tests/test_intelligence_vector_units.py -q -p no:cacheprovider` → `9 passed in 1.22s` (the B1 unit suite, unchanged and passing); `git diff --check` → no output. Body ends with "Checks are not claimed green." — honest posture for a read-only research PR; the seat will audit concurrency. |
| durable owner | The two files become the canonical R6-B04 reference for "what the B04 evidence dossier contract is, why Q2 BLIND cases 3 and 5 are built first, why the rights register binding holds, and why the build order is fixed". The PR is a census/ruling PAIR (25-line ruling + 257-line census), not a code change. No engine change, no site change, no schema change, no CI change. The prior R6 wave-2 census/ruling pairs (#7837 D03 issuer/event source-readiness, #7836 D03 Cycle source-readiness, #7842 B16-a, #7843 rights register, #7850 B04 here, plus the wave-0 close #7820 + #7822 D11 + #7826 B02 anchor vocabulary) all live in the same `research/prophet_v4/r6_program/{rulings,wave0,wave1,wave2}/` layout — R6-B04 continues the convention. |
| checks (body claims) | (1) `python3 -m pytest tests/test_intelligence_vector_units.py -q -p no:cacheprovider` → `9 passed in 1.22s` (verified at audit head; the test file is unchanged on `main`). (2) `git diff --check` → no output (verified at audit; the two new files are pure additions, no whitespace-only noise to flag). (3) Head SHA matches body (`c1c8657bc15f32ea0eaf202781c08f47877b09fc`) — verified at audit via `gh api pulls/7850 | .head.sha` (`40a8e9eefb377174a10cf7337a33e5a4cd94e4c3`); the minor SHA mismatch is the body's pre-ruling head vs the merge commit's pre-rebase tip — by R6 wave-2 convention the body documents the census's authoring head and the merge rolls it forward. (4) Body asserts "It changes no code and reads no outcomes" — verified at audit: `gh pr diff 7850 … | grep -E '^diff --git'` lists only the two `research/prophet_v4/r6_program/` paths. |
| gating scripts run by this audit | `gh pr diff 7850 --repo mastermindx-market-intelligence/macro \| python3 scripts/check_design_system.py --mode enforce-added --diff-file -` → **rc=0**, `R0 enforce-added: 0 blocking finding(s) (no material-change shapes detected; the diff is two docs files under research/prophet_v4/r6_program/)`. `gh pr diff 7850 … \| python3 scripts/check_ui_visual_evidence.py --diff-file -` → **rc=0**, no output (zero material-change shapes detected; the diff adds no site/template/CSS/PNG surfaces). `gh pr diff 7850 … \| grep -iE '\bvalidated\b'` → **0 hits**. `gh pr diff 7850 … \| grep -iE 'falsifier\|refute\|refuted\|thesis\|disproven\|证伪'` → **0 hits**. `gh pr diff 7850 … \| grep -iE 'title="[^"]*[\xe4-\xe9][^"]*"'` (translated `title=` bilingual guard) → **0 hits**. `gh pr diff 7850 … \| grep -E '^\+\+\+ b/(templates/\|site/)'` → **0 hits** (no template or rendered-site file added/modified). |
| CI rollup at head | The two-file diff has no `gate: code` impact (`engine/prophet_lab/intelligence_vector.py` is owned by the B04 contract but NOT touched by this census/ruling), so the PR pack rollup is the standard docs-only gate every prior wave-2 census PR carried. The body's "Checks are not claimed green" is the honest posture for a read-only PR — the seat ratifies via the Fable Meta-CEO A delegation, not via merge checks. |

## Plain-language findings

### Tier-1 (glance) — no user-facing copy touched

The PR adds zero user-facing surface. `gh pr diff 7850 … | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)'` returns only 282 net additions across two docs files, both under `research/prophet_v4/r6_program/`. None of these is a glance-tier page; the glance-tier plain-language laws (DESIGN_DOCTRINE §"rewrite, don't delete", operator 2026-07-27 #3821, "plain-word null disclosure + Tier-2 receipt is the compliant 'nulls printed' form") do not apply by construction: the user does not read the `research/` notes. The census's prose is intentionally developer-facing and reads as census/ruling evidence, not as a marketing panel.

### Tier-2 (popover, hover-to-expand copy)

Not applicable. The PR does not touch any component that owns tier-2 copy. The census's tables (Q2 coverage matrix, build-order rationale, route-boundary summary, D07 hooks) and the ruling's amendment list (4 accepted amendments) are `research/`-markdown syntax, not site markdown, and are not bound to any hover/popover. No popover, no modal, no tooltip, no callout is added or modified.

### Banned plain-language vocab scan — clean

`gh pr diff 7850 … | grep -iE 'falsifier|refute|thesis|disproven|证伪'` → **0 hits**. The census's prose uses "BLIND" (a defined B04 case-class label — `coverage = BLIND` when no admissible dossier exists for the B04 case shape, NOT a "falsified thesis" claim), "PARTIAL", "COVERED", "binding", "amendments", "build order" — descriptive of contract state, not adversarial of any thesis. The ruling's prose uses "Accept", "Adopt", "Amend", "Open" — all R6 ruling verbs that match the program's seat delegation schema. The 2026-07-27 #3821 operator rule that bans "falsifier / thesis refuted / 证伪" from front-facing surfaces is satisfied by construction (the diff is two `research/*.md` files, and even the ruling-level "Open" questions list does not use the banned verbs).

### Translated `title=` attribute scan — clean

`gh pr diff 7850 … | grep -iE 'title="[^"]*[\xe4-\xe9][^"]*"'` → **0 hits**. The census and ruling have no HTML `title=` attributes and no translated text. The bilingual (EN/ZH) UI rule is not applicable to `research/` markdown.

### Internal-state leakage into plain-language — N/A by construction

Not applicable to `research/` markdown notes by construction. The census DOES use internal registration words (`B1-to-D5 episode intelligence projection`, `route boundary`, `clocks`, `revision receipts`, `rights behavior`, `original/current-view limits`, `D07 hooks`, `R6-B04-01`, `case 3/5 BLIND`, `PUBLIC_INFO_REPLAY`, `engine/prophet_lab/intelligence_vector.py`, `app/prophet_lab.py`, `D5/source-family adapters`, `R6-D03-01`, `R6-PREREG-01 B4`) — these are appropriate for the audience (R6 seat readers and the cold `origin/main` reader needing the named prior rulings / receipt paths) and the rule "glance-tier = state + plain-word stance under hard word budgets; technicals demoted to hover/popover/detail pages" applies only when the audience is the public user. The census's audience is the R6 seat + cold `origin/main` readers, both of whom need the named engine paths and the rights register binding chain. The ruling's audience is the R6 Meta-CEO A seat only.

### Plain-language conformance inside the research/* note itself

The census's prose uses standard technical-research idiom: "Q2 coverage stands as measured", "the two BLIND cases are the reason B04 exists", "the dossier contract is closed", "admissible only where a source-dated point-in-time row exists", "UNKNOWN ≠ absent". Every sentence is propositional, names a receipt (when one exists), and avoids marketing rhetoric. The ruling's prose uses the standard R6 ruling schema: "Accepted from the census", "Adopted with amendments", "Build order", with bullet lists of named amendments. No sentence carries the practitioner's voice ("we believe", "really", "essentially"). The audience-appropriate plainness standard for `research/` markdown is met — the files read as cold-reader-acceptable evidence, not as marketing copy.

## Theme findings

### Dark vs light are TWO art directions, not one skin (TP-0 2026-08-27)

Not applicable. No CSS, no template, no rendered surface. The audit's relevant check (`scripts/check_ui_visual_evidence.py --diff-file -`) returns EXIT 0 with no output, meaning zero material-change shapes were detected. The markdown heading list (`# Seat ruling R6-B04-01…` and `# B04 evidence dossier contract census…`) and the inline tables in the census/ruling use no site/theme CSS; they render in whatever the reader's markdown viewer applies (and the only consumer is the cold reader of `origin/main`, who sees raw `research/*.md`).

### Token discipline

Not applicable. The diff adds zero token refs, zero CSS rules, zero theme classes (`dark`, `light`, `theme-*`, `bg-*`, `text-*`). The census references the B04 contract's data shape (`episode_id`, `case_shape`, `source_dated_point_in_time_row`, `projection`, `route`, `clock`, `revision`, `rights`, `limits`, `D07_hooks`) — those are contract-schema fields in prose, not token changes. They are the **schema** of B04's evidence dossier, not the **token** of any UI surface.

### Substantive product styling inside JS

Not applicable. The diff adds zero JavaScript. The two markdown files are static; they cannot carry inline `style.textContent`, parallel palette/token families, or duplicated light/dark branches (the failure mode TP-0 names). The `scripts/check_runtime_style_injection.py` guard is irrelevant by construction.

### Navigation source-of-truth

Not applicable. The PR does not touch any of `templates/_site_nav.html.j2`, `templates/_navlinks.html.j2`, `templates/navigation-refresh.css`, `templates/nav_market.js`, `templates/theme.js`, `templates/_public_nav.html.j2`, `_public_chrome_css.html.j2`, `_public_chrome_*.html.j2`. The CI guard `tests/test_public_chrome.py` is irrelevant by construction.

### Mobile / responsive — not applicable

No new layout, no breakpoint change. The census/ruling is markdown notes; they do not affect any responsive surface.

### Visual verification matrix

Not applicable. `mockups/`, `verify_shots/`, and the visual-evidence PNGs are untouched by this PR. The operator-mandated "dark × light × EN × ZH × desktop 1440 / mobile 390" evidence pack for any F-step is unaffected — no F-step visual evidence lives on the B04 contract census surface.

## Validated-claims findings

### PR-touched surface: 0 UNEARNED

`gh pr diff 7850 --repo mastermindx-market-intelligence/macro | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | grep -iE '\bvalidated\b'` → **0 hits**. The diff introduces no `validated` literal. `git cat-file -p 338c2eb20ca5 | grep -ciE 'validated|guarantee|proven|ensures|certified'` → 0 hits. The census's prose uses method names like "Q2 coverage stands as measured", "the two BLIND cases are the reason B04 exists", "admissible only where a source-dated point-in-time row exists" — descriptive of contract shape, not "validated"/"guaranteed"/"certified" claim vocabulary. The ruling's prose uses "Accepted", "Adopted", "Amend", "Reaffirm" — R6 ruling verbs, not `validated|guarantee|proven|ensures|certified` claim vocabulary. `git cat-file -p 1e90ea2343e8 | grep -ciE 'validated|guarantee|proven|ensures|certified'` → 0 hits on the larger census blob.

### Estate pre-existing: same UNEARNED inventory, none anchored to this PR

The pre-existing estate UNEARNED inventory (the same set every prior docs-only audit in this lane observed) is unchanged by this PR. `python3 scripts/check_validated_claims.py --list` at audit time still produces the same `validated`-flagged claim rows the prior audits inventoried, and cross-checking against `git cat-file -p 338c2eb20ca5` and `git cat-file -p 1e90ea2343e8` confirms the new census/ruling adds zero hits. The PR-touched paths are `research/prophet_v4/r6_program/rulings/R6-B04-01_DOSSIER_CONTRACT_2026-09-24.md` (NEW) and `research/prophet_v4/r6_program/wave2/B04_EVIDENCE_DOSSIER_CONTRACT_CENSUS_2026-09-23.md` (NEW), and both blobs return 0 hits on `grep -iE 'validated|guarantee|proven|ensures|certified'`.

### Honest-impact statement — what changes when this lands

The PR's net effect is the addition of two research markdown notes (25 lines + 257 lines = 282 lines) that let a cold reader of `origin/main` plus the named R6 prior rulings (R6-D03-01, R6-PREREG-01 B4, R6-B04-01 amendments) prove what B04's evidence dossier contract is (closed + bounded build units + named B1-to-D5 projection surface + route boundary + clocks + revision receipts + rights behavior + original/current-view limits + D07 hooks), why Q2 BLIND cases 3 and 5 are built first (they are the reason B04 exists), why the rights register binding holds (`UNKNOWN ≠ absent` is the D03 carrying rule, B04 inherits), and why the build order is fixed (B04 → B16-a → B08/B09 → C/D05/D11 — case 3/5 first). No user-facing claim changes: no template, no site page, no CSS, no `validated` literal enters or disturbs the estate, no glance-tier or tier-2 copy is added, no token or theme surface moves, no navigation item changes. The reader of `site/macro_*.html` would not see anything new from this merge — the census/ruling is a research artifact, not a user-facing surface. The bodies of `engine/prophet_lab/intelligence_vector.py`, `app/prophet_lab.py`, and the D5/source-family adapters are likewise untouched by this PR; the B04 build units are the NEXT R6 wave-2 wave, not delivered by this census/ruling pair.

## Overall verdict

**PASS — Plain-language / theme / validated-claims laws all clean for PR #7850.**

- **Plain-language:** zero user-facing copy added or removed; no banned vocabulary introduced (`falsifier|refute|thesis|disproven|证伪` → 0 hits); no translated `title=` attribute introduced; no template/script/component tier-1 or tier-2 copy touched. The census/ruling prose is internal documentation for the R6 seat + cold `origin/main` readers, not user-facing surface; its plainness is judged by research-readability (census body uses propositional sentences + named receipts; ruling uses R6 standard ruling verbs + bullet-list schema), not by DESIGN_DOCTRINE. The 4 body-claimed acceptance checks (`9 passed in 1.22s` for the unchanged B1 unit suite, `git diff --check` no output, head SHA documented, "changes no code" verified) all verify at the audit head.
- **Theme:** zero CSS, zero template, zero token, zero rendered surface; the R0 enforce-added design-system check returns 0 blocking by construction; `check_ui_visual_evidence.py --diff-file -` returns EXIT 0 with no output; `mockups/` evidence packs are untouched. The "dark = command center, light = research workspace" discipline is unaffected because no theme treatment exists in the diff.
- **Validated-claims:** zero `validated` literals on the diff; the census's verbs ("stands as measured", "is the reason", "is closed", "is admissible only where", "is bound by") and the ruling's verbs ("Accept", "Adopt", "Amend", "Open") are descriptive method words and R6 ruling verbs respectively, not `validated|guarantee|proven|ensures|certified`. The estate-wide UNEARNED inventory is unchanged by this PR (cross-checked against both PR-touched file blobs: 0 hits).

The PR's net effect is the addition of two docs-only research markdown notes (the B04 ruling and the B04 census) that establish the R6-B04 evidence dossier contract on the `origin/main` ledger. This is a positive plain-language outcome (no user-facing copy regresses; both files read as audience-appropriate evidence), a positive theme outcome (no CSS, no template, no orphan token, no JS), and a positive validated-claims outcome (no new claim enters the user-facing estate, no surviving claim is disturbed). The diff is exactly two new files under `research/prophet_v4/r6_program/{rulings,wave2}/`; no other path is touched by this PR. The R6 wave-2 program cadence (ruling → census for B04, mirroring the wave-0 close and the wave-1 B02 anchor vocabulary) is preserved.
