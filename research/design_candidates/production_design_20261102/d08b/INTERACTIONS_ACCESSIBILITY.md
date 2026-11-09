# Interaction, state, responsive and accessibility contract

These are build requirements and editable static design evidence. They are not claims that the candidate's controls have been implemented. The actual Paper references and before/after captures are listed in EVIDENCE_MANIFEST. B09 defines exceptional behavior, B12 places concise annotations beside the compositions, and B15 renders the actual exposure phone states rather than only describing them.

## 1. State ownership and invariants

Use the existing source reader/coordinator and D08 navigation state. Maintain one exact selected object shared by matrix, inspector, 3D and exact-value views; each source family's identity remains distinct. Local UI state includes visible view, filter/window/cap/mode, focused cell, selected coordinate, open panel and camera. It grants neither source qualification nor durable persistence.

For every B-owned action below, **source write = none**. Reads remain under existing owners. Explicit C/D23 save is a separate admitted action and must use that owner's protocol/readback. A route/view change must not create a draft, save, watch, replay cursor or publication. Return context is transient, validated, same-origin and stripped of credentials/protected data/write intent.

Root, source session, selected expiry/strike/right, snapshot, metric, unit, lens, population/qualification, range/cap and originating view are preserved by identity. If a user explicitly changes a condition that excludes the node, preserve the original dated selection in a named unavailable state and request an explicit new selection. Never silently choose the nearest strike/expiry or reuse a stale row index.

## 2. Control and transition contract

| Control / precondition | Result and route behavior | Feedback, keyboard/touch, return and recovery |
| --- | --- | --- |
| Exact underlying / valid source root | Existing D08 parser changes root; clear old-root data/selection and start root-fenced read | Identity-bound skeleton; abort/ignore older responses. Invalid/ambiguous identity keeps requested text and reason. No ticker-only cross-listing join. |
| Book/session picker / available dated choices | Existing current/date reader chooses source session; quote context remains separately dated | Announce selected session and qualification. Loading cannot relabel prior data. Missing session offers available dates without auto substitution. |
| Matrix focus / admitted projection | Arrows move focus within known coordinates; Enter selects; click/tap selects when target size is adequate | Spoken label includes root, ISO expiry, strike, metric, signed value/unit and availability. Visible focus ring differs from selection. No hover-only actions. |
| Phone overview / compact rows | B02 labels the chart Overview and places Select a node in Exact values immediately above it | B11's 48px row is the preferred precise touch path; it does not require a small-cell tap first. Keyboard can still select the equivalent data object. |
| Metric/lens/right/mode | Change only supported source view; retain selected coordinate and method identity | Unsupported Greek disabled with explanation, not an upsell. Net/gross/absolute and call/put encodings keep distinct labels. Prior valid view remains available. |
| Scope/range/expiry cap | Apply existing window/cap semantics to one projection | Retained node keeps value/tier normalization. Full-lens totals remain labeled separately from visible window. If excluded, show original node state. |
| Views / Research on phone | Open complete labeled destinations and controls (B10); preserve root/book/node/lens/range | Modal focus contained; first meaningful control receives focus; Close/Esc restores trigger. Long content scrolls inside the menu. D08 owns any route transition. |
| Node inspector / selected aggregate | Show coordinate, metric, qualification, components and clocks; dock or modal according to real available width | Close/Esc closes the inspector and restores its cell/row. A clear explicit selection-clear command may retain incumbent clearing behavior; do not overload closing with silent substitution. |
| Inspect actual contracts | Resolve incumbent source member list; show full identity and terms (B17) | Unique accepted row can continue to C. Aggregate-only/ambiguous/unqualified evidence stays inspectable with an unavailable handoff reason. C's validator, not B defaults, decides eligibility. |
| Compare observations | Choose two source observations; existing temporal owner supplies effective cutoff and current-knowledge/historical mode; run same-basis validation and matched-cohort function | Show actual cutoff with timezone, cohort and exclusions. Preserve inherited historical cutoff; no silent current-clock substitution. Unknown cutoff/availability or incompatible method/time/identity leaves both inspectable without delta. Return restores node/vintage/cutoff. B07/B16 compose zero/nonzero exclusions. |
| Volatility link / exact root and intended expiry | Existing `tab=volatility`; preserve desired expiry and origin | Missing expiry stays selected (B08). User explicitly chooses a substitute. Back restores exposure selection, not a default node. |
| Term/smile point selection | Select ISO expiry or exact strike; coordinate ring/guide and inspector update together | Keyboard rows offer same choice. Tooltip information also appears persistently. Missing points remain gaps. No fitted curve through missing data. |
| 3D / 2D / Exact values | Switch representation of the same qualified projection or admitted Lab dataset | Retain coordinate, mode, window/cap/filter, source session and camera separately. Table includes zero/null and data beyond draw cap. No access bypass. |
| Camera controls | Existing reset/front/top/elevation/orbit/zoom controls change camera only | User-initiated; never required to select an exact value. Reduced-motion avoids animated orbit. Camera interaction cannot steal global keyboard navigation. |
| Positioning / Levels | Open existing source family with explicit source/date and return context | Exact price ticks stay anchored while label leaders avoid overlap. Null regime is Unknown. Context source failures do not erase valid exposure evidence. |
| Source & calculations | Expand read-only provenance/method/coverage details | Show all clocks, source key/schema, unit/sign basis, exclusions and known/unknown denominators. Close restores trigger and scroll. No hidden refresh-on-open mutation. |
| Replay reference | Existing validated dataset request, access and available-window checks | Requested versus loaded selection/cutoff visible. Gaps/refusal preserve origin. No cross-dataset cursor conversion or new B replay engine. |
| Return / Back/Forward | Existing same-origin return codec/history restores exact prior view | Restore filters, row/node, source session, scroll anchor and focus. If origin is gone, named fallback and reason; never silently create or save state. |

## 3. State matrix

| State | Visible behavior / actual copy | Recovery and evidence |
| --- | --- | --- |
| Loaded success | Dated identity, signed values, source qualifications, exact selection and clear next step | B01/B03/B04/B05/B06/B07/B13/B14/B17. Success is data availability, not research/production acceptance. |
| First-use / no selection | Useful loaded map and selection instructions; no invented selected contract | Select a row or cell. Inspector does not show an arbitrary first result as a user choice. |
| Loading new root/book | “Loading book for Nov 2…” with stable skeleton and selected root | B15. Clear old-root values; status announced once, not every placeholder. Late old-root response ignored. |
| Empty with reason | “No qualified observations” and the response/scope reason | B15. Change scope or return. Empty response, unsupported instrument and source failure are different reasons. |
| Partial | Known subtotal plus qualified/excluded counts; complete total unavailable | B01/B02/B03/B11/B16. Source collection denominator remains unknown unless supplied. |
| Stale / refresh failed | “Last available · Nov 2”; original dated values and qualifications remain | B15. Explicit Retry refresh. Only same-root authorized evidence may remain. Refresh success does not rewrite source date. |
| First read error | “Could not read exposure”; no verified snapshot for this root | B15. Retry read or return; no previous-root fallback under current identity. |
| Missing selected expiry | “IV not supplied. Your Nov 13 selection is preserved.” | B08. Other expiry observations remain usable; missing point remains a gap. |
| Unsupported computation | “Vanna is not computed” for that source family | B09. Keep supported Gamma available; disabled control includes reason. Another source's Vanna does not supply this dataset. |
| Wrong root / future / malformed / unqualified | Withhold affected observation and expose source-specific validation reason | Source reader's existing states; do not rewrite them as empty data or plan-required. |
| Comparison refused | “Methods differ” or exact identity/time/scope/empty-intersection reason | B09; choose a supported basis explicitly. No manufactured zero delta or nearest-date match. |
| Original node missing | “This node is outside the new book” with original dated context | B09; explicit new selection. Returning is still possible when origin is valid. |
| Guest / expired session | Existing auth owner supplies sign-in/renewal state; keep requested resource | Protected values hidden. Return after successful admission restores safe context. A network error is not a sign-in decision. |
| Access unresolved | “Access could not be verified” | B15; retry existing access check. Do not infer plan requirement or reveal protected rows. |
| Verified denial / plan-required | Existing owner-established reason and access details | B15 illustrates plan-required separately. No extra entitlement source or bypass via exact 2D. |
| WebGL failure / context loss | Exact table, source and inspector remain available; explain 3D unavailable | B09/B11/B13. Same admitted dataset/selection; no hidden data loss. |
| Reduced motion | No auto-orbit; instant/short user-initiated change; no decorative camera movement | Exact table is complete. This is specified behavior awaiting runtime verification. |
| Save pending / saved / failed / unknown | **B-owned save is not applicable:** B performs no durable save | If C/D23 exposes an admitted save, its own protocol supplies pending/readback/definite failure/unknown effects. B preserves origin; no automatic retry or false saved toast. |

## 4. Responsive geometry

Consume F01/F02 `candidate.4` only as the separately versioned input while release remains pending. No silent rail collapse. Expanded rail is 224px at ≥1200; 196px for 860<w<1200; drawer has zero occupied width at ≤860. Compact 72px rail is an explicit user preference. Header is 64px above 860 and 56px narrow. Gutters are 16px through 600, 20px between 600 and 1200, and 24px at ≥1200.

`C = viewport − actual occupied rail − 2 × gutter`. Dock 320px inspector with 24px gap only when `C ≥ 984` and primary remains at least 640px (or the domain's higher actual minimum). Otherwise use a modal up to 440px or full-width phone detail. A hidden inspector consumes no layout width.

| CSS viewport | Occupied rail | Gutters | Useful C | Inspector mode / primary after dock |
| ---: | ---: | ---: | ---: | --- |
| 320 | 0 | 16 × 2 | 288 | Full-width details; intrinsic wrapping |
| 390 | 0 | 16 × 2 | 358 | Full-width details; complete menus and 48px exact rows |
| 768 | 0 | 20 × 2 | 728 | Overlay; exact table / chart remains full width |
| 1024 | 196 | 20 × 2 | 788 | Modal up to 440; no persistent dock |
| 1280 | 224 | 24 × 2 | 1008 | 320 + 24 dock; primary 664 |
| 1440 | 224 | 24 × 2 | 1168 | 320 + 24 dock; primary 824 |
| 1600 | 224 | 24 × 2 | 1328 | 320 + 24 dock; primary 984 |

Expanded first dock threshold is 1256px; compact first threshold is 1096px under the corresponding gutters. Test continuous/fractional widths around 600, 860, 1200 and each dock threshold, not only these sample sizes. Chart controls wrap or move into complete labeled menus; no whole-page horizontal overflow. A necessary 2D table/matrix may scroll inside its own labeled component while exact values offer a usable narrow path. Fixed artboard heights are evidence framing, not instructions to fix browser card heights. At 200% text and 400% zoom, cards grow intrinsically and controls remain reachable.

## 5. Accessibility and visual semantics

The house target is **44px for important phone controls**; exact selection rows are 48px. WCAG 2.2 AA's pointer target minimum is **24×24 CSS pixels or applicable spacing/exceptions**, not 44px. The dense phone overview is paired with an immediately adjacent usable exact selection path; it is not the required precision input.

Use semantic tables with labeled cell buttons, or a genuine ARIA grid only when its complete interaction model is implemented. Virtualization must preserve row/column metadata, focused/selected coordinate and access to all admitted rows. Home/End move to row limits; Page movement remains inside the dataset; Escape closes the current modal and restores focus. Focus restoration must resolve an identity after filtering/paging, not reapply an old DOM index. If that identity is gone, focus the named heading/fallback and announce the reason.

The selected row's focus ring is rendered in B11. Selection, focus, missing, zero, stale and error must have non-color cues. Signed heatmap values stay printed; call/put smiles use shapes/line style; negative Lab ΔOI is hollow; explicit zero and unavailable labels remain in exact rows. Charts need descriptive titles, units, source date, scope and textual/table alternatives. Tooltips are supplemental; inspectable details must work without hover.

Use at least 4.5:1 contrast for normal text and 3:1 for large text and essential non-text marks/controls under applicable criteria. Cell text in the candidate chooses a high-contrast foreground against its actual heatmap fill. Light and dark need separate measured checks, including selection/focus/disabled/hover states. Color palettes distinguish analytical sign/side without colored container borders or decorative accent stripes. Focus outlines remain legitimate.

Localization must keep exact ISO identity and ET/absolute offset semantics while formatting display dates and numbers appropriately. EN/ZH labels may wrap; currency and unit do not disappear. Do not round a tiny nonzero value into an unqualified displayed zero: show sufficient precision or an explicitly bounded display value. Screen-reader announcements should avoid flooding on camera movement or polling; announce meaningful loaded/selection/access changes politely unless urgent interaction demands otherwise.

Reduced motion removes auto-orbit and nonessential transitions. Loading skeletons remain static in reduced-motion mode. Keyboard users can complete both journeys with the exact table and inspector; camera control is optional. No keyboard trap may be created by a chart or canvas. Touch scrolling and pinch/zoom must not be globally blocked by a 3D event listener.

## 6. Coverage truth and remaining proof

Actual Paper visual evidence covers 320, 390, 768, 1024 and 1440 compositions, both themes, EN/ZH, selected/focused states, partial coverage, missing volatility, source failures, access states, complete phone controls, matched and nonmatching cohorts, exact contract terms and ambiguity. Width arithmetic evaluates 1280/1600 and thresholds. It does **not** establish a responsive browser pass at those widths or a full theme×locale cross-product.

Future acceptance must run 320/390/768/1024/1280/1440/1600, 200% text and 400% reflow, keyboard-only, touch, reduced-motion, screen-reader semantics and source/access failure injection. Candidate Paper screens are not DOM/focus/performance proof. The actual served baseline inspection is recorded separately in VERIFICATION.

## Standards

- [WCAG target size minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- [WCAG reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html): 320 CSS-pixel equivalent / 400% at 1280, with scoped exceptions for essential 2D content.
- [WCAG contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
- [WCAG non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
