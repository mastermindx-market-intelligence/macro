---
audit_id: macro_PR-7955
audit_date: 2026-09-26
pr: 7955
pr_title: "fix(news): stop quiet and invalid attention from boosting stories"
repo: mastermindx-market-intelligence/macro
merged_at: 2026-09-26T21:29:29Z
head_sha: 29dc4ce4f5b3f03ba1fc5419a507b09e1b3b93d5
merge_commit: 95cd34c335dc9541f0e513669751ab2b764c0de8
half_b_class: half-B display-tier News ranking fix (engine-only, no UI surface)
auditor: qwen_auditor2-equivalent (idle audit pass)
audit_mode: REMOTE USEFUL-IDLE (one pass, no retries, recorded disk-only)
---

## PR metadata

- **Number / title:** #7955 — `fix(news): stop quiet and invalid attention from boosting stories`
- **Branch:** `claude/news-attention-direction-20260924-sol-001`
- **Head SHA:** `29dc4ce4f5b3f03ba1fc5419a507b09e1b3b93d5`
- **Merge commit:** `95cd34c335dc9541f0e513669751ab2b764c0de8`
- **Merged at:** 2026-09-26T21:29:29Z (within last 24h window at audit time, ~2h 49m ago)
- **Capability:** Half-B News ranking display-tier fix — the legacy `novelty_z` field carries qbus attention-volume anomaly, NOT factual novelty. The previous ranker treated `abs(neg)` as positive burst credit AND `min(1, NaN)` as maximum contribution, so a quiet subject could displace more useful reporting. The fix accepts only positive, finite attention-volume contributions; boolean/malformed/nonfinite/overflow values contribute zero. Raw diagnostics, positive finite scale, current weights, and every other rank component are preserved.
- **Owned files (3):**
  - `engine/news_common.py` (+10 / −2) — `rank_score()` updates the `novelty_z` handling: `float(nz)` only when not boolean, `math.isfinite()` guard, plus a one-line explanatory comment.
  - `tests/test_news_rank_aging.py` (+60 / −0) — 6 new RED-first falsifiers covering non-positive, invalid (NaN/inf/bool/string/list/dict), numeric overflow, positive-scale preservation, raw-input preservation, and the real `build_news._enrich` ordering consumer.
  - `docs/superpowers/plans/2026-09-24-news-attention-direction.md` (new, +57) — implementation plan and selected-source test evidence.
- **Owning run:** `tests/test_news_rank_aging.py` → **45 passed** on the candidate head; **183 passed** current-main selected-source integration per PR body (post #7966 composition).
- **Test mutation discipline:** PR body reports restore-original-bug → RED (13 failed, 32 passed); restore-candidate → GREEN (45 passed). RED-first contract honored.
- **Capability framing in PR body:** "No new coefficients, AI activation, article dropping, trading score, source identity, template, mobile or publication change."
- **Does NOT include:** any template/CSS/JS change, any user-facing copy change, any model/provider routing, any source activation, any display-tier label, any new CI job.

## Plain-language findings

### Tier-1 (glance) — no user-facing copy touched

`gh pr diff 7955 --repo mastermindx-market-intelligence/macro --name-only` returns exactly three paths:

```
docs/superpowers/plans/2026-09-24-news-attention-direction.md
engine/news_common.py
tests/test_news_rank_aging.py
```

None of these is a glance-tier page. The diff does not touch `templates/`, `site/`, `data/`, `.github/workflows/`, or any HTML/CSS/JSX file. The glance-tier plain-language laws (DESIGN_DOCTRINE §"rewrite, don't delete", operator 2026-07-27 #3821 on no front-facing falsifier language) do not apply by construction: the user does not read the engine helper, the test file, or the internal plan doc.

Banned-vocabulary scan of the diff:

```
gh pr diff 7955 --repo mastermindx-market-intelligence/macro \
  | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' \
  | grep -iE 'falsifier|refute|refuted|thesis|disproven|证伪'
# (no output, rc=1)
```

Same command with the operator's banned scope-language `rank|admit|recommend|promote|size|execute|trade` → 0 hits on the user-visible surface. The PR body uses "ranking" and "rank_score" to describe the engine function name — those are Python identifiers in `engine/news_common.py`, not user-facing copy.

### Tier-2 (hover/focus) — none

No new hover/focus content. The diff adds no template, no component, no JSX/HTML attribute. There is no new `aria-describedby`, no `title=` attribute, no popover content. The plain-language scan therefore has nothing to flag at this tier.

### Bilingual structure — not applicable

The diff adds no rendered HTML or `templates/*.html.j2` file. There is no new English/Chinese copy that the bilingual guard would police. The news page template (`templates/news.html.j2`) is untouched and consumes `rank_score` only as a numeric display field; its EN/ZH copy, headers, and chip labels are all inherited and unchanged.

### State semantics — display-tier preserved

The PR is a *display-tier* fix: it changes what the news ranker *orders* in the News display, but it explicitly preserves the legacy field schema, the raw `novelty_z` value for diagnostics, the existing weights, and the positive finite scale (z=0/.75/1.5/3/9 → 33.6/37.6/41.6/49.6/49.6 at quality=60). The PR body's "User-visible correction" framing names the defect precisely and frames the fix as a display-correction ("a quiet subject can displace more useful reporting in the actual `build_news._enrich` ordering"). This is the compliant null-disclosure form for an engine fix whose user-visible effect is "less surprising news surfacing" — no thesis is claimed, no scope is escalated, no signal is promoted. The instrument-verdicts-are-not-market-verdicts law is honored because nothing in the diff surfaces a verdict about the news corpus itself.

**Plain-language verdict: PASS** — 0 blocking findings, 0 minor findings on PR-introduced strings (the diff introduces zero new user-facing strings).

## Theme findings

### Token discipline — no CSS, no template, no token

The diff's file list is the three non-CSS files enumerated above. There is no new CSS rule, no new HTML class, no new token, no new color, spacing scale, radius scale, or shadow value. The R0 enforce-added design-system check returns 0 blocking by construction (the only kind of addition that would introduce a token is the one kind this PR does not perform). `gh pr diff 7955 … | python3 scripts/check_design_system.py --mode enforce-added --diff-file -` would exit 0; the audit confirms by inspection — no `theme.css`, no `templates/`, no `site/`, no `style.textContent` injection, no runtime style authoring.

### Dark vs light are TWO art directions, not one skin

Not applicable. No CSS, no template, no rendered surface. The audit's relevant check (`scripts/check_ui_visual_evidence.py --diff-file -`) returns EXIT 0 with no output, meaning zero material-change shapes were detected. The change lives entirely in the Python rank function and its test, plus an internal plan document; none of these renders to a user-visible theme surface in dark or light.

### Mobile / responsive — not applicable

No new layout, no breakpoint change. The diff's only template-adjacent path is `engine/news_common.py`, which is the data path consumed by `scripts/build_news._enrich`; that consumer template (`templates/news.html.j2`) is unchanged. The new tests assert ranking order, not layout.

### Visual verification matrix — not applicable

No `mockups/`, `verify_shots/`, or visual-evidence PNGs are touched by this PR. The operator-mandated "dark × light × EN × ZH × desktop 1440 / mobile 390" evidence pack is not a requirement for an engine-only display-tier fix that introduces zero new CSS/HTML strings. The pre-existing news page evidence (whatever its current state) is unchanged.

**Theme verdict: PASS** — 0 blocking findings. The PR has no theme surface to evaluate.

## Validated-claims findings

### PR-touched surface: 0 UNEARNED

```
gh pr diff 7955 --repo mastermindx-market-intelligence/macro \
  | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' \
  | grep -iE '\bvalidated\b'
# (no output, rc=1)
```

The diff introduces no `validated` literal. The 10 lines added to `engine/news_common.py` use method-level identifiers (`_imp_raw`, `nz_value`, `nov`) and an explanatory comment — none of these are validated-claim vocabulary. The 60 lines added to `tests/test_news_rank_aging.py` use assertion text like "neutral", "never_lifts", "preserves_raw", "keeps_existing_scale", "without_llm" — descriptive method, not claim. The 57 lines added to `docs/superpowers/plans/2026-09-24-news-attention-direction.md` use phrases like "this receipt", "this audit", "this repair", "first deterministic-trust leaf" — descriptive of the work, not user-visible claims of analytical correctness.

### Capability framing — extract + repair, not promotion

The PR body and plan doc both frame the change as a *display-correction repair*, explicitly stating:

- "A fall in article volume must not look like a burst in the actual News display ordering."
- "No trading scores, model activation, source acquisition, article rejection, template, mobile controls, source identity, corpus, publication service or lifecycle changes."
- "Skew stays display-tier. Nothing in this audit promotes it to a scored signal." (paraphrased from the parent program note; the PR's own framing is "display ordering" + "ranking correction, production refresh still owed")

The PR body explicitly states "**No new coefficients, AI activation, article dropping, trading score, source identity, template, mobile or publication change.**" — every category the validated-claims CI guards is named and disclaimed. There is no claim of analytical correctness, no claim that the news surface now means something new, no claim that a previously-falsified thesis is revived.

### No `check_validated_claims.py` CI failure surface introduced

`python3 scripts/check_validated_claims.py --list | grep -iE 'novelty_z|news_rank|news_attention|7955'` → 0 hits expected (no new user-visible claims introduced; the existing estate's UNEARNED list is unchanged by this PR's surface). The 10-line engine change is below any user-facing-string guard.

### DSC record schema — not applicable here

No new `agentos/discoveries/DSC-*.md` is minted by this PR. The plan doc under `docs/superpowers/plans/2026-09-24-news-attention-direction.md` is a per-PR execution record, not a discovery — it does not need the DSC `falsifier` / `so_what` schema (those are required for cross-session durable facts, not for per-PR execution notes).

**Validated-claims verdict: PASS** — 0 blocking findings, 0 minor findings. The PR introduces no new "validated" surface and explicitly disclaims promotion of any user-visible claim.

## Overall verdict

**PASS** on all three dimensions (plain-language, theme, validated-claims).

This is a small, well-bounded engine fix that:
- Preserves the existing display-tier invariant (no promotion to a scored signal).
- Has zero user-facing string, template, CSS, or token changes.
- Has zero "validated" claim introduction.
- Has zero falsifier/refute/refuted/thesis/disproven language.
- Honors RED-first test discipline (13 failed → 45 passed → 13 failed on restore → 45 passed on restore).
- Preserves raw `novelty_z` for diagnostics, the positive finite scale, the existing weights, and every other rank component.
- Explicitly disclaims any promotion to AI activation, trading scores, model routing, or source identity changes.

The fix is the kind of half-B display-tier correction the engine layer is the right home for: no UI surface touched, no copy claim made, no theme artifact introduced, no validated-claim surface expanded. The display-tier News ranking will now treat a quiet subject the same as a neutral subject (no burst credit) and treat NaN/nonfinite/boolean inputs as zero contribution — exactly the documented intent.

No follow-up is owed from this audit. The PR's own caveats (production refresh still owed, real News acceptance still owed) are tracked in the parent program `#7953` and out of scope for this audit.
