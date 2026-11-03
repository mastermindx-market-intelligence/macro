# Prophet full-page refinement — 3 November 2026

## Baseline retained before the repair

Source: `915af4624daf28c25ce08bb17270918d035cbbd2` on the existing Prophet PR #9495. The later evidence-only commit `60a3a4a6b2ee364bd1d99908ce0c5cd5890fa24a` preserves the same page source.

The `before/` directory preserves the normal production build's anonymous, offline browser evidence. All four canonical build modules completed successfully. These captures use the generated public HTML unchanged and never serve the separate protected payload. No actual signed-in, Paper or production acceptance is implied.

- 16 full-page cases: 1440, 768, 390 and 320px; light/dark; EN/ZH. Six additional viewport crops aid visual comparison.
- All 16 cases: zero horizontal overflow and zero uncaught page errors.
- Native initial-load lab CLS over three fresh contexts per size: 0.70067 desktop and 0.22890 mobile. Measurement uses the maximum session window and excludes recent-input shifts, with a 2500ms observation after font readiness. This is local lab evidence, not field Core Web Vitals.
- First card: 689px at 1440 EN, 937.2px at 390 EN and 1006.7px at 320 EN.
- All 12 publication-pair source checks passed. The final native source refresh, not the earlier development VM cache, is the source of truth. The 172 eligible candidates are preserved as ordered public/protected subsequences; all 77 protected Plan targets resolve and no protected Plan control is in public HTML.
- The `public_pool_rows` metadata was corrected from an invalid table-row selector to the native `.ucp-row` selector. Its value is 3. Screenshot bytes, geometry and input hashes did not change; the correction is recorded in `observations.json`.

Observed repairs to verify: navigation first-paint stability, shorter pre-card hierarchy, mobile assistant overlap/focus return, section-link discoverability, and honest Turn Setups loading/error/empty states.

## Verification tools

`tools/` contains the actual build/capture/loading/pair verification runners and the helper that genuinely invokes the canonical 68-case EW-P4 recapture before adding source-equivalence metadata. Source and output paths are explicit. Each build or capture requires a fresh output identity; reconcile an existing process before running it again. The EW helper refuses uncommitted render inputs and checks them again after the real screenshot producer returns.

## Native verified continuation at 5370b9f51740fe87

The current source includes three local commits after remote PR #9495 head 60a3a4a, focused on global navigation, search geometry, no-script menu, theme tokens, synchronized Chat markup and final 320px overflow removal. The normal four-module site build completed at source commit 39dca322 (about 28.7 minutes); two canonical CSS asset follow-ups produced the final generated outputs at 5370b9f. The final public page SHA-256 is 12da851f12dea2570ec24291cbc59a513bd1fcb32ee82c964875dfbd9c5447af. The protected payload SHA-256 is 421ab3f966d02b9cc6ee77ac67c6daa19ed5a00a768386ea8920c59ffdc3856e. Neither output is live production acceptance.

- after/ contains 16 final full-page browser captures at 1440/768/390/320, light/dark and EN/ZH, six top crops and the source-bound observations file. All 16 have zero horizontal overflow and zero uncaught page errors. The desktop first-card top is 689.0px; mobile 390 first-card top is 918.5px. Opportunity workspace hierarchy still needs the R8 implementation for more immediate mobile discovery.
- canonical-final/ contains genuine untouched capture records for US stocks and Chat, eight anonymous locale/theme/viewport states per page, with a signed-off manifest for the existing visual evidence guard. Offline endpoints that cannot be served locally are recorded in the manifest; the screenshots do not claim authenticated or live-feed proof.
- verification/final-navigation.json: eleven responsive, keyboard, no-script and short-inventory cases, 53/53 assertions passed.
- verification/final-publication-pair.json: twelve checks passed for public/protected data integrity, with 172 eligible rows partitioned into three public and 169 protected; 77 protected Plan targets resolve without leaking protected Plan actions into public HTML.
- verification/final-loading.json: three fresh unforced loads per device, maximum session-window CLS approximately 0.07493 desktop and 0.12055 mobile. This improves the earlier 0.70067/0.22890 baseline; a live.js session-strip insertion still contributes about 0.113 of the mobile shift. This is lab evidence, not a production Core Web Vital.
- research/evidence/ew_p4_descriptive_ui_20261031/receipt.json: final 68-case, 33-source-render binding recapture at this same head; 163 tests pass, one skipped. EW cases are synthetic descriptive UI observations, not trading authority.

## Paper R8 and remaining acceptance

The three editable and independently reviewed native Paper boards are desktop light YW1-0, mobile light ZRL-0 and mobile dark Chinese 1092-0. The original Paper file is 01M3NT5Y3G5HTJHVR0K5W2MDJM, page p-C-0; p-A-0 remains untouched. Their native JSX and screenshots are in paper-r8/. Desktop dark ZE5-0 is incomplete because palette operation prophet-r8-20261103-desktop-dark-colors-200 has an unresolved transport effect; do not replay it.

The historical Fabric UX refinement run prophet-page-revamp-20261102-ux-refinement remains EFFECT_UNKNOWN, unverified and retry-denied. Do not retry that operation or count it as implementation evidence. The Chairman has separately authorized ChatGPT2 to own and continue direct source implementation on this existing branch; an archived session or an imagined "original Executive/Fabric owner" is not a prerequisite. Do not route this work to Grok Secretary. Preserve the held untracked tests/test_prophet_plan_review_integration.py and all unrelated work.

## Direct robustness continuation — 3 November 2026

Starting source: 19fbe0bd63e24b122a7759b0bc454dff0e14d857. The direct source changes implement:

- The existing neutral, bilingual session strip in first-paint HTML, reused by live.js without adding a second calendar or fetch owner.
- A tighter narrow-screen Today header, with warning copy and 44px controls retained.
- Turn Setups idle/loading/ready/empty/unavailable states, a four-second request deadline, manual retry, obsolete-response suppression, keyboard focus recovery, and independence from tape/name fetches.
- Strict snapshot/row/cohort validation. Failed or unverifiable sources cannot become "no setups"; missing leg/trend values cannot become bearish boxes. Legacy populated v1 rows remain supported, but legacy empty output without evaluated coverage is unavailable.
- Additive producer evaluated_n/failed_n diagnostics; all-computation failure is explicit, partial results are disclosed, and signal/ledger rules are unchanged.
- Two-week insufficient history is unknown, not negative. The mobile table has a keyboard-focusable region, scroll guidance and a sticky ticker.
- Attribute-safe tooltip escaping and preservation of fold/focus when optional basket names arrive late.

Final component verification: 121 focused Python/Node tests passed, plus 38 live calendar tests. Four real Chromium component cases (320/390/768/1440, EN/ZH, light/dark) passed failure → keyboard retry → partial success, focus return, hostile-text escaping, keyboard table scrolling with a sticky ticker, no overflow and no uncaught page errors. JavaScript-disabled fallback also passed. Source-bound receipts and screenshots are in verification/prophet-mtf-robustness-20261103-c2-final/. Two independent read-only source review passes found and closed incomplete-row/cohort-consistency/null-health defects; the final pass found no additional concrete defect. These are synthetic component proofs, not a native publication or authenticated product claim. A fresh native publication build is next.

Outstanding acceptance is concrete: fresh native responsive/performance/public-private pair verification, source-head CI and independent review, and eligible signed-in Sources-to-Plan journey proof. Keep non-merge status unchanged; no Ready/un-draft/relabel/enqueue/merge/deploy action is authorized by this checkpoint. Do not misreport a passing local build as the live replacement.

### 3 November — keep the candidate when its related Plan is unavailable

The exact-target handler now calls the existing lifecycle/access selection owner before closing the candidate or changing source/view. A missing, withheld, malformed or unavailable target leaves the same detail, focus, reading position and table/filter state in place, clears any unearned return context, and announces a bilingual recovery message beside the same button. Retrying does not create another control or fetch data. Success retains the native exact-Plan selection and one transient return.

The regression was demonstrated red against `63327214997788b069ce7ae5899e03c467cecda4`: the missing-target hop closed the candidate dialog. After the repair, the candidate-return, Plan-relation and setup-section suites pass **238/238**, including 44 failure/retry combinations and the Sources → failed hop → same-button retry → Plan → same Sources/focus/scroll return. Two fixture assumptions were made faithful to the native page: a static feedback live region is not generated tab markup, and a child's computed display is independent of its hidden source-block ancestor.

Independent read-only source review found no additional concrete defect. Four anonymous Chromium fixture cases (1440 light EN/dark ZH, 390 light EN, 320 dark ZH) passed keyboard failure/retry/return, truthful lifecycle zero-state, overflow and page-error checks during development. The reusable browser verifier now requires committed source hashes; the exact-head recapture and normal producer build are the next verification actions. This is not authenticated account or production acceptance.

The 68-case EW-P4 capture at the preceding `63327214` source is retained as historical evidence. It must be regenerated after this next source commit before being counted for the new render inputs. Continue directly on the existing source branch; do not retry the unrelated unresolved Fabric operation or wait for an archived owner.
