# SNI U0 — Composition seam decision

**Status:** DECISION (U0 product/integration owner). Nothing is implemented here; P0 implements.

**Pins.**
- Terminal `origin/master` @ `fc76cf495781e5f53254aa3c457411de0cb64654`. Diff to the later `707648d5` is empty over every cited path.
- Macro `origin/main` @ `e44069e306fd`.

**Inputs.**
- `SNI_U0_COMPANY_INTELLIGENCE_REUSE_MAP.md`.
- Masterplan §5.1, §5.5, §7 P0 and §9 (scratch copy `SNI_Fable_Masterplan_2026-10-11/MASTERPLAN.md`; not on `origin/main`, gap G-U6).

## 1. Recommendation (exactly one)

**(b) A new reader, route and component family, composed into the existing `CompanyIntelligencePage`.** There is no new page, no new URL family and no new nav entry.

| Piece | Path (new unless stated) | Contract |
|---|---|---|
| Reader | `terminal/lib/singleNameIntelligence.ts` | `export type SingleNameIntelligenceResult = { ok: true; state: SniState; context: SingleNameReferenceTwin } \| { ok: false; state: "error"; error: { code: "invalid_symbol" \| "not_found" \| "upstream_unavailable" \| "invalid_payload" \| "rights_blocked"; message: string; retryable: boolean } }`. The idiom is copied from `companyInstitutionalContext.ts`: an R2 manifest → generation → sha256-checked twin, a size cap, and a module cache with a `__reset…ForTests` export. `normalizeSingleNameSymbol` reuses `normalizeCompanyIntelligenceSymbol` (`companyIntelligence.ts` L297); it does not define a second `SAFE_SYMBOL`. |
| Route | `terminal/app/api/single-name-intelligence/[symbol]/route.ts` | `force-dynamic`, `Cache-Control: no-store` on the error paths, `rateLimit(req, { name: "single-name-intelligence", max: 120 })` (sibling: `company-intelligence/[symbol]/route.ts` L56). Fixture mode (`SINGLE_NAME_INTELLIGENCE_FIXTURE==="1"`) reads `public/data/single_name_intelligence/<SYM>.json` **only in test/dev**. Production never falls back to a fixture (masterplan §5.5). The public projection only; entitled fields go through `lib/entitlement.ts` (`isPaidTier` L192 / `isProTier` L198). |
| Components | `terminal/components/single-name/SingleNameReferenceBand.tsx` (+ `SingleNameIdentityStrip.tsx`, `SingleNameStateChip.tsx`, `SingleNameLinkedListings.tsx`) | Props: `{ ticker: string; name?: string \| null; placement: "brief" \| "fallback"; onOpenEvidence?: (ref: SniEvidenceRef) => void }`. It fetches its own reader (sibling idiom: `CompanyInstitutionalContextCard`). Copy uses `useLang` (`lib/i18n`) + `pick(zh, en, zh)` (`lib/finFormat`). That is the sibling idiom: `CompanyInstitutionalContextCard` has 50 `pick(zh` calls and 0 LEX. So **no `lib/i18n.tsx` edit is needed.** |
| Stylesheet | `terminal/app/single-name-intelligence.css` | Imported by the band component itself. The sibling idiom is `CompanyIntelligenceSourcesLayout.tsx` L3 importing `company-intelligence-sources.css`, and `app/layout.tsx` L5 deliberately keeps CI CSS out of the root. It uses only `globals.css`/`observatory.css` tokens and adds `.sni-*` selectors only. **No `globals.css`, `layout.tsx` or token edit.** |
| Tests | `terminal/lib/__tests__/singleNameIntelligence.test.ts`, `singleNameIntelligenceRoute.test.ts`, `singleNameReferenceBandRender.test.tsx` | Sibling idioms: `companyInstitutionalContext(.Route).test.ts`, `companySourceManifestRender.test.tsx`. |
| Fixtures | `terminal/lib/__tests__/fixtures/sni-0700HK-identity-unresolved.json`, `sni-9988HK-linked-BABA.json`, `sni-BABA-resolved.json` | Identity values copied verbatim from macro masters at `e44069e306fd` (reuse map §1), or the literal `"UNRESOLVED"`. **Never minted.** |

### Mount points

There are four in the existing files, all owned by the single integration writer (§3).

| # | File | Anchor | Why |
|---|---|---|---|
| M1 | `terminal/components/fin/CompanyIntelligencePage.tsx` | the v1 Brief lens block (L731), after `CompanyInstitutionalContextCard` (L763) | Same slot family as the two sibling context cards. |
| M2 | `terminal/components/fin/CompanyIntelligenceV2Current.tsx` | the Brief lens block (L715) | The page **early-returns** V2Current when the event workspace is ok (page L311). V2Current composes neither sibling card, so mounting at M1 alone would make SNI vanish on every v2-covered name. |
| M3 | `CompanyIntelligencePage.tsx` | the `Company intelligence unavailable` EmptyState branch (L350) | **HK today lands here** (reuse map §2). Without M3 the band never renders for 0700.HK/9988.HK, the reference issuers. The band renders `placement="fallback"` *above* the existing EmptyState; the EmptyState copy is unchanged. |
| M4 | `CompanyIntelligencePage.tsx` | the `${ticker} is not covered yet` branch (L365) | Same reason as M3 for a symbol that CI marks `not_covered`. |

The `Current event workspace unavailable` branch (L325) is a v2 error that is not `not_found`. It is **not** a mount point, because the page is reporting a provider fault and the band would compete with it. P0 may revisit this only with a design ruling.

## 2. Draft-and-review reasoning

- **Mechanical given this spec (cheap draft + strong review recovers quality):**
  - the reader, route and tests (sibling idioms exist line for line)
  - fixtures (copied values)
  - the four mount edits (each a ≤10-line JSX insertion)
- **Judgment (stays with `designer`/seat, not a builder):**
  - the band's visual composition, under §9 "main viewport answers what changed / current state / unusual / next events / what would change the read" with an L1 budget of 5 (archetype C `instrument_analyzer`, C-company)
  - the wording of `identity-unresolved` and `rights-blocked` states

  `terminal/docs/COMPANY_INTELLIGENCE_V2_DELTA_SPEC.md` §3 (receipt grammar, §3.5 absence card, §3.6 stance line) is the binding grammar to extend. **P0 must pin exact markup/CSS in a design packet before the builder starts** (spawn-handoff law item 3).
- **Why seat-level judgment was needed for this decision:**
  - (a) and (b) both pass a surface reading.
  - The deciding facts are the page's early return (L311) and the HK EmptyState path (L350/L365). Both are only visible by reading the page's control flow, and both invert the obvious answer "just add a section to the CI context".

## 3. The single integration writer and the P0 builder's files

**Integration writer.** Exactly one P0 lane, named at P0 commission. It is the only lane that edits shared files:
- `terminal/components/fin/CompanyIntelligencePage.tsx` (M1, M3, M4)
- `terminal/components/fin/CompanyIntelligenceV2Current.tsx` (M2)

It does **not** edit:
- `terminal/components/fin/MegaPane.tsx` (page mount at L289, unchanged)
- `terminal/lib/finPages.ts`
- `terminal/lib/i18n.tsx`
- `terminal/app/globals.css`, `terminal/app/layout.tsx`, `terminal/app/company-intelligence.css`
- `CompanyThemeContextCard.tsx` / `companyThemeExposure.ts` (open Terminal PR #796 touches them: ADJACENT, avoid)

The URL/route state (symbol, lens, as-of, evidence focus) stays owned by the existing page. The band reads `ticker` from props and adds no query parameters in P0.

**P0 builder.** Owns only new files:
- `terminal/lib/singleNameIntelligence.ts`
- `terminal/app/api/single-name-intelligence/[symbol]/route.ts`
- `terminal/components/single-name/*`
- `terminal/app/single-name-intelligence.css`
- the three test files and three fixtures in §1

The builder and the integration writer may be the same lane. If they are different lanes, the builder merges first and the integration writer second. The mount edits import only the band's default export.

**Macro side.** Not in U0's decision. The twin producer is a later lane with its own owner (masterplan §5.1). The Terminal reader is built against the wire contract draft and fixture mode until a producer publishes.

## 4. Why the alternatives lose

**(a) An additive field on `company_intelligence_context.v1` plus a section in the page loses:**
- **It is coupled to the wrong lineage.** The CI context's `transport_lineage` is `{earnings_manifest, tx_index, builder:"company_intelligence.v1"}` (`companyIntelligence.ts` L89). The twin's lineage is `spec_hash`, an immutable generation, per-owner source clocks, rights and correction lineage (masterplan §5.1). Folding it in either breaks the CI builder's receipt or makes the twin's clocks invisible.
- **It fails when SNI matters most.** The field would arrive only when CI is ok. For HK today CI is `not_found` (reuse map §2), so the field and the section would never render for the reference issuers.
- **It needs macro builder changes in an earnings owner's file** (`engine/company_intelligence/`, WS:EARNINGS-INTELLIGENCE-OS) to carry non-earnings data. That is a takeover of another owner's contract, which masterplan §7 "a new URL is not itself a new backend owner" and the owner table forbid in spirit.
- **The 4-state CI status** (`ready/partial/stale/not_covered`, L15) cannot express `identity-unresolved` / `rights-blocked` without widening an enum that other consumers switch on.

**(c) ESCALATE loses.** The seam is decidable from existing sibling idioms at the pin: the theme and institutional cards each pair their own reader and route with a card mounted in the page. No authority, rights or identity ruling is required to place the seam. The open rulings (the HK issuer IDs, the bench, the bridge) bind the twin's *content*, not its *placement*.

**Also rejected:**
- **A new standalone page/URL** (`/single-name/[symbol]`). It forks the CI page's lens, as-of and evidence state that masterplan §7 says to preserve, and it creates a third header surface the navigation law forbids.
- **Mounting only at M1.** This is invisible for v2-covered names (early return) and for HK names (EmptyState). It would ship a band that renders for almost no one.

## Adversarial review

1. **"Four mount points is four shared-file edits; that is not 'one integration writer, minimal edits'."**
   - All four sit in two files, owned by one lane, and each is a single JSX insertion of the same default export.
   - The alternative (one mount) was shown in §4 to render for nobody who matters.
   - **Residual risk:** V2Current is 943 lines and actively developed. The integration writer must re-fetch and re-read L715 at commission time, not trust this line number.
2. **"Rendering the band above an EmptyState (M3/M4) makes the page say both 'unavailable' and show data. That contradicts itself."**
   - The two describe different owners. The band carries its own typed state chip and a provenance line naming its owner. The EmptyState names CI.
   - The V2 delta spec's absence card (§3.5) already establishes "say what is missing, by owner", so this is the same grammar.
   - **Residual risk:** a user reads the page-level EmptyState as page-level failure. The `designer` packet must decide the visual order and the copy. A **design ruling is required before P0 ships M3/M4.** This is flagged, not resolved here.
3. **"A per-component fetch adds a network round-trip and can blow the PROPOSED 3 s cached-viewport SLO."**
   - The SLO is PROPOSED-NOT-RATIFIED.
   - The band fetches in parallel with the page's existing v1/v2 fetches (page L216/L222). It is not chained behind them, with the exception of M3/M4, which mount after CI resolves.
   - **Residual risk:** M3/M4 chain behind CI's failure. P0 should hoist the SNI fetch to page level only if the measured p95 breaches. That would be an integration-writer edit, which is still one lane.
4. **"Fixture mode means the band can ship green with no producer, and then show fixture data in production."**
   - The route's fixture branch is gated on an env var (sibling L69).
   - The NOT-DONE gate for P0 must include a test proving that, with the env unset and no R2 twin, the route returns `not_found` (or `upstream_unavailable`) and **never** fixture bytes (masterplan §5.5 "no demo-fixture fallback").
5. **"`normalizeCompanyIntelligenceSymbol` accepts `0700.HK` but the twin needs counter identity (HKD `0700` vs RMB `80700`). Reusing CI's normalizer loses that."**
   - The normalizer only sanitizes the query symbol. Counter identity is resolved by the producer from Data OS and returned in `identity.listing` (wire contract).
   - The reader never infers a counter from a suffix.
   - **Residual risk:** `80700`/`89988` are absent from the security master (reuse map §1). So an RMB-counter query returns `identity-unresolved`, which is the correct, honest state.
6. **"#796 is ADJACENT. If it lands mid-P0 and restructures the Brief lens, M1 conflicts."**
   - #796's file list (capped at 100 in the read, gap G-U5) shows the theme card and `companyThemeExposure`, not the page.
   - If #796's final diff touches `CompanyIntelligencePage.tsx`, the integration writer rebases after it (O.13). That is not a reason to pick (a), which edits the same page.
