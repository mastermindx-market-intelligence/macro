# Plain-language / theme / validated-claims audit — mastermind-terminal PR #706

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| number | #706 |
| title | `fix(options): contain volatility term structure on mobile` |
| merge head | `66f26abc` (squash of `sol/options-vol-term-mobile-overflow-20260921-sol-001` onto `master`). Selected as the most-recent merged half-B non-audit-record PR in the 24-h window that has not already been audited (`ls orch/audits/mastermind-terminal_PR-*.mm.md` confirms no audit for #706). Adjacent #704 was already recorded by PR #7671; #705 (chart stale-request guard) is pre-existing audit material; #701 (chart settings UX) is a larger feature with its own audit lane. PR #7678 in macro is a 1-line CI fix that fails the "half-B with theme/plain-language impact" filter; #7683 in macro is a research artefact (no UI surface). |
| merged | 2026-09-22T03:00:34Z via squash-merge to `master`. |
| files | **2 paths, +35 / −1.** `terminal/components/vol/VolTermPanel.tsx` (+1/−1), `terminal/e2e/options-vol-term-mobile-overflow.spec.ts` (+34/−0 NEW). |
| half-B label | **half-B mobile-options UX overflow containment.** Session A of the Options-mobile consistency sweep. The PR body enumerates a real phone-width overflow in **Volatility → Term structure**: at the 390×844 contract viewport the card had `clientWidth=360` but `scrollWidth=379` because the header held the structure chip + both slope chips on one unbreakable flex row. Repair adds `flexWrap: "wrap"` to the header `<div>` so chips wrap onto a second line. No math, ranking, signal, source, or trading behaviour change. |
| scope | (a) Term-structure card header stops horizontally overflowing its own panel on the 390 mobile viewport; (b) every chip and its meaning is preserved (no truncation / hiding); (c) responsive SVG measurement and volatility semantics remain unchanged; (d) new focused Playwright regression locks the geometry contract. |
| durable owner | None new. Panel C of Volatility remains owned by the Options desk lane; the new regression attaches to the same `e2e/` directory the desk already owns. |
| checks | Body reports: mobile 390×844 focused browser regression — **1/1** Playwright PASS, retries=0; `npx tsc --noEmit` exit 0; `git diff --check` clean. RED-on-base / GREEN-on-candidate geometry table is the discriminating receipt (cardClient=360 / cardScroll=379 → both equal; head / doc scroll widths also fit). |
| evidence matrix | `mockups/evidence/` PNGs are not required for this PR (no redesigned visual surface; the change is layout containment of an existing chip row that already passes the desk's TP-0 dark/light × EN/ZH × 1440/390 matrix — wrapping on the second line does not introduce a new visual state, only the existing chips on one extra row). |
| gating scripts | `terminal/scripts/check_plain_language.mjs --json` — exists on terminal, ran against `origin/master` (post-merge head) — **0 active findings**, 82 pre-existing `legacy` entries none of which point at the two files this PR touches. `scripts/check_validated_claims.py` — **DOES NOT EXIST** on terminal; the discipline is read against the macro precedent and the design-doctrine banned-glance vocabulary. `scripts/check_design_system.py` / `scripts/check_runtime_style_injection.py` / `scripts/check_ui_visual_evidence.py` — macro-only (TP-0 art-direction gate); terminal-side discipline is read against the same standing rules and the inline-style disclosure below. `scripts/check_template_site_sync.py` — does not apply (no plain-copy `templates/<name>` + `site/<name>` pair was edited). |

## Diff content (scoped to this audit)

### `terminal/components/vol/VolTermPanel.tsx` (+1 / −1)

A single-line change at the card header root:

```diff
   return (
     <section className="fin-card" style={{ minWidth: 0 }}>
-      <div className="fin-card-h">
+      <div className="fin-card-h" style={{ flexWrap: "wrap" }}>
         <span>{t("termTitle")}</span>
         {structure && (
           <span
             style={NEUTRAL_CHIP}
             aria-label={t("termChipAria")
               .replace("{front}", structure.front.v.toFixed(1))
               .replace("{far}", structure.far.v.toFixed(1))}
           >
             {t(structure.key)}
           </span>
         )}
         {slopes.map((s) => (
           <span key={s.key} style={{ ...NEUTRAL_CHIP, fontVariantNumeric: "tabular-nums" }}>
             {t(s.key).replace("{v}", fmtSlope(s.v))}
           </span>
         ))}
       </div>
```

Sibling layout already declares `minWidth: 0` on the parent `<section>`; the chip row already uses `NEUTRAL_CHIP` (the shared tokenized chip style imported from `terminal/components/vol/volShared.ts`). The only material delta is one CSS property on one element — `flex-wrap: wrap` — so the header stops forcing all three spans (title + structure chip + 0-2 slope chips) onto one line. Chip order, label set, and tab semantic meaning are unchanged.

The pre-existing inline `style={{ minWidth: 0 }}` on the parent `<section>` and `style={NEUTRAL_CHIP}` on the chips establish that this file already mixes layout-primitive inline styles with tokenized colour/border; the new `flexWrap: "wrap"` is in the same category (a layout primitive, not a material decision — see Theme #1).

### `terminal/e2e/options-vol-term-mobile-overflow.spec.ts` (NEW, +34 / −0)

A single Playwright test, scoped to the `mobile` project via `test.skip(testInfo.project.name !== "mobile", …)`:

```ts
test("Volatility term-structure card stays inside the phone viewport", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "mobile-only overflow regression");
  await page.goto("/options?tab=volatility");
  const card = page.locator(".fin-card").filter({ hasText: "Term structure" }).first();
  await expect(card).toBeVisible({ timeout: 15_000 });
  const geometry = await card.evaluate((el) => { … cardClient/cardScroll/headClient/headScroll/svgRight/cardRight … });
  expect(geometry.cardScroll).toBeLessThanOrEqual(geometry.cardClient + 1);
  expect(geometry.headScroll).toBeLessThanOrEqual(geometry.headClient + 1);
  expect(geometry.svgRight).toBeLessThanOrEqual(geometry.cardRight + 1);
  const doc = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(doc.scroll).toBeLessThanOrEqual(doc.client + 1);
});
```

Three independent geometric contracts: the card does not scroll wider than its client, the header does not scroll wider than its client, the SVG is contained inside the card; plus a document-level assertion that the whole page does not horizontally overflow. The card is located by the user-visible English literal "Term structure" — see Plain-language #2.

## Plain-language findings

**#1 — PASS (no new findings).** `node terminal/scripts/check_plain_language.mjs --json --ref origin/master` (run against the post-merge head) reports `findings: []` and `legacy: 82`, none of the legacy entries pointing at the two files this PR touches (`terminal/components/vol/VolTermPanel.tsx`, `terminal/e2e/options-vol-term-mobile-overflow.spec.ts`). The guard's vocabulary flags raw state enums (`BOTTOM_WATCH`, `CATALYST_WINDOW`, `QUIET_ACCUMULATION`, …), study slugs (`trust_tier`, `event-edge`, `msc_regime`, `flowScore`, `gexdesk`, `prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `tripwire`, `falsifier`, …), and statistic tokens (`iv_rank`, `gex`, `dte`, `pcr`, `rv30`, `zscore`, …); PR #706 introduces none of these in user-visible positions. The chip strings (`termContango`, `termInverted`, `termSlopeFront`, `termSlopeBack`, `termXAxis`, `termTitle`, `termChipAria`) are all pre-existing `VOL_LEX` entries (`terminal/components/vol/volStrings.ts:65–78, 131–132`) routed through `makeVolT(lang)`; the file `volStrings.ts` is not modified by this PR.

**#2 — soft note (test selector uses the English literal "Term structure" instead of a token).** The new Playwright test locates the card via `page.locator(".fin-card").filter({ hasText: "Term structure" })`. This is a `hasText` predicate over the card subtree (it does not assert user-visible English; it asserts the card contains the term-structure title text in the test's *active language*), and the test is `mobile`-project-only — the Chinese-language mirror of the same test would need its own `hasText: "期限结构"` filter. This is a test-only assertion that is *not* a `blocking` plain-language finding (no user-visible position) and not covered by `check_plain_language.mjs`'s added-line scope (the guard scopes user-facing copy, not test selectors), but it does mean a future PR that introduces a third language must remember to add a mirror filter. Recommend follow-up to extend `check_plain_language.mjs` to flag test selectors that hard-code English `hasText` predicates — not blocking, surfacing only. Within this PR's half-B scope: **non-blocking.**

**#3 — soft note (test names a single assertion in English; bilingual layer parity is the existing desk discipline).** The test title `"Volatility term-structure card stays inside the phone viewport"` is English-only. Test titles are not user-visible to end users — they surface in CI logs and in the desk's regression tracker — so this is also non-blocking for the `check_plain_language.mjs` guard. Documented here so the desk can decide whether to bilingualize the regression name on a follow-up.

## Theme findings

**#1 — PASS (no new visual state).** TP-0's "dark and light are TWO art directions, not one skin" applies to **material UI packets** — surfaces where colour, type, geometry, motion, or material depth are being authored. PR #706 modifies none of those: it changes a flex-wrap property on the chip row. The chips already use `NEUTRAL_CHIP` (the shared tokenized chip style, sourced from `terminal/components/vol/volShared.ts`), the parent card uses the shared `.fin-card` / `.fin-card-h` classes, and the SVG already uses `var(--grid)`, `var(--brand-2)`, `AXIS_TXT`, `REF_TXT`. The new wrapping behaviour is invisible to colour/spacing systems: chips now may render on two lines instead of one, and on a single line they render exactly as before. The TP-0 art-direction packet obligation does not attach to this PR because it is not a material packet — it is a layout containment fix that is invisible to the design system.

**#2 — soft note (inline layout style, consistent with the file's existing pattern).** The new `style={{ flexWrap: "wrap" }}` is an inline style on a single element, joining the file's existing inline-style inventory (`style={{ minWidth: 0 }}` on the parent `<section>`, `style={NEUTRAL_CHIP}` / `style={{ ...NEUTRAL_CHIP, fontVariantNumeric: "tabular-nums" }}` on the chips). The macro precedent `scripts/check_runtime_style_injection.py` is fail-closed against *material* runtime stylesheets (multi-kilobyte `style.textContent`, parallel palette/token families, duplicated light/dark branches invisible to the design checker); one-line layout primitives (`minWidth`, `flexWrap`) are explicitly out of scope of that gate and follow the same pattern as the surrounding code. **No regression on the discipline;** if the desk prefers tokenization, the natural follow-up is to lift the layout primitives into a shared `.fin-card-h-wrap` class, but that is a separate refactor and not required by this PR's half-B scope.

**#3 — soft note (e2e spec does not carry a visual artefact).** The new `terminal/e2e/options-vol-term-mobile-overflow.spec.ts` asserts geometry only — no visual capture, no dark/light × EN/ZH × 1440/390 matrix. This matches the pattern in `terminal/e2e/options-vol-term-mobile-overflow.spec.ts` (geometry), `terminal/e2e/mobile-chart-chrome.spec.ts` (geometry/focus), and other sibling overflow regressions in the Options-mobile sweep. The TP-0 evidence-matrix obligation is a redesigned-surface obligation; wrapping an existing chip row is not a redesigned surface, so the evidence-matrix obligation does not attach.

## Validated-claims findings

**#1 — PASS (term-structure copy is properly disclaimed as geometry, not forecast).** The two chip labels rendered into the user-visible DOM are `t(structure.key)` where `structure.key ∈ {termContango, termInverted}`:

```ts
// terminal/components/vol/volStrings.ts:72-78
termContango: ["Contango", "正向期限结构"],
termInverted: ["Inverted", "期限结构倒挂"],
// Chip disclosure — states WHAT is compared, so the label can't read as a signal.
termChipAria: [
  "Front expiration ATM IV {front}% vs nearest-to-90d ATM IV {far}% — a term-structure shape, not a forecast.",
  "最近到期平值IV {front}% 对比最接近90日的平值IV {far}% — 仅为期限结构形态，并非预测。",
],
```

The aria-label names both anchor tenors (front and ~90d), the percentage points at each, and the explicit "shape, not a forecast" disclaimer in both EN and ZH. The HONESTY DOCTRINE comment block at `volStrings.ts:6-12` is binding: "Vol is NON-DIRECTIONAL: no bullish/bearish copy, no signal language. Structure labels (Contango / Inverted) are descriptive term-structure geometry, never a forecast." This is exactly the operator-banned-glance vocabulary the design doctrine flags (no "validated", no "guaranteed", no "falsifier fired / thesis refuted", no precision claims). PR #706 introduces no new copy — the only chip strings in the rendered DOM are the seven pre-existing `VOL_LEX` keys.

**#2 — PASS (freshness disclosure is the existing asof chip; no precision claim added).** The freshness truth on this surface is the existing `asofChip` ("Nightly EOD · as of {date}" / "每晚收盘 · 更新于 {date}") at `volStrings.ts:23-24` — also unchanged by this PR. PR #706 does not introduce or alter any "LIVE" / "now" / "real-time" / "validated" copy. There is no rounding or precision claim in the new geometry code or test (the test asserts integer-pixel containment, not statistical significance). The vol panel's HONESTY DOCTRINE explicitly forbids "LIVE" language; PR #706 is consistent with that.

**#3 — PASS (no banned falsifier/refutation language).** A grep for `validated`, `falsif`, `invalidated`, `guaranteed`, `risk-free`, `forecast` across the two changed files returns no matches. The chip aria-label uses the word "forecast" exactly once, in the negative ("a term-structure shape, not a forecast") — that is the explicit disclaimer pattern the design doctrine prescribes for *every* term-structure / skew / regime surface.

**#4 — PASS (test asserts geometry, not statistical claims).** The e2e regression asserts containment (`scrollWidth ≤ clientWidth + 1`) and document-overflow bounds. It does not assert probabilities, lifts, Brier scores, or directional predictions. The test name (`"Volatility term-structure card stays inside the phone viewport"`) describes a CSS contract, not a market contract.

## Overall verdict

**PASS — clean ship for half-B scope.**

- Plain-language: 0 active findings; 82 pre-existing legacy entries none touching the PR's files. Two soft notes on test-selector English-literal coupling and English-only test titles — non-blocking, surfaced for follow-up.
- Theme: no new visual state, no material packet, TP-0 art-direction obligation does not attach. One soft note on the inline-style pattern consistent with the file's existing inventory; non-blocking.
- Validated-claims: term-structure copy retains its "shape, not a forecast" disclosure in EN and ZH; freshness truth remains the existing `asofChip`; no banned vocabulary added; no precision or directional claim added.
- Scope discipline: 2 files, +35/−1; mobile 390×844 regression locked; tsc / diff-check clean; discriminating RED-on-base / GREEN-on-candidate geometry receipts in the PR body.
- Cross-cutting: the new test selector (`hasText: "Term structure"`) and the English-only test title are the only long-tail items the desk may want to address on a follow-up — they do not block this PR.

No blocking findings. The PR is a faithful, narrowly-scoped mobile-overflow fix that does not regress the plain-language / theme / validated-claims discipline.