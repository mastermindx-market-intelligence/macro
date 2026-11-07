# Build, compatibility and rollback guidance

Implementation is **not commissioned by this assignment**. This plan gives a later authorized builder a bounded route through the existing frontend/data/auth owners. Do not merge this design packet as a substitute for review.

## Integration map

| Existing source | Future change boundary |
| --- | --- |
| `app/(shell)/options/futures/page.tsx`, `app/(shell)/options/equity-replay/page.tsx` | Preserve server page access, dynamic/noindex and closed validation. Route-specific access explanation must use existing trusted access states |
| `components/futures/FuturesWorkspaceMount.tsx`, `IexDepthReplayMount.tsx` | Preserve incumbent account/language/provider ownership; confirm actual imports before changing |
| `components/futures/FuturesWorkspaceView.tsx` | Recompose identity, cursor, chart and evidence; preserve current controls and native hook |
| `components/futures/IexDepthReplayView.tsx` | Preserve typed fetch outcomes and artifact metadata; explicit publication changes; observation picker and evidence presentation |
| `components/futures/FuturesMicrostructureChart.tsx` | Preserve projection-free rendering, gap/depth/footprint/POC/GEX/CVD math and badge layout; add accessible selection/table paths through owned helpers |
| `components/futures/FuturesCotPanel.tsx` | Relocate into separately dated context disclosure; retain source and replay-ineligible semantics |
| `components/futures/futuresLab.module.css`, `lib/futuresUiCopy.ts` | Scoped semantic roles and bilingual copy; remove accidental double-gutter only through shared-shell contract; no opaque runtime stylesheet |
| `components/futures/useFuturesWorkspace.ts` | Preserve owner-key invalidation, one polling loop and current bounds; no duplicate store |
| `lib/futuresRequest.ts`, `futuresTransport.ts`, `futuresSourceRead.ts`, `futuresSourceJoin.ts` | Preserve current runtime schemas and validation. Data fixes require their own source review, not a layout patch |
| `lib/iexDepthReplay.ts`, `lib/largeTrades/*`, `app/api/large-trades/route.ts` | Reuse native parser, correction engine and source admission; resolve shared API entitlement policy with owner before any change |
| `lib/originNav.ts`, `companySearchContext.ts`, D08/D06 sender | Add replay restoration through the existing owner. Do not overload the closed company-search shape or create new sessionStorage buckets |
| Quote Hub / IEX ingest / publisher | No design-driven engine, scheduler, source installation or archive fork. Only separately admitted owner contract extensions |
| `/dev/options-plan` | Leave customer exclusion and production404 intact |
| `/dev/futures`, `/dev/futures-sample`, `FuturesResearchLab`, `FuturesPublicSampleLab`, `futuresSampleLoader` | Preserve production guards and development-only source qualifications; never use their fixture/sample outputs as a subscriber fallback |

Source locations are repo-relative under `terminal/` unless otherwise stated. The exact audited versions and links are in the source manifest. These are seam instructions, not a ready-to-apply patch.

## Bounded implementation sequence

1. **Qualify references.** P00 resolves the same-app action publication; F01/F02 release the joint contract. Create/verify the dedicated Paper file with exact ownership, build the annotated normal/exception boards, inspect actual screenshots and freeze supported exports into the existing RIG artifact set. QA01 performs admitted independent product/visual review. No product build from provisional chrome.
2. **Freeze integration contracts.** D08/D06 specify the existing-owner return codec, required session-zone source and exact/fallback result. The access owner resolves the equity page/shared API policy without silently broadening or narrowing unrelated consumers. The publisher states the available retained windows. D23 save remains disabled unless its admitted protocol exists.
3. **Recompose the existing reader views.** One responsive implementation, same routes/providers/readers. Move required context above chart, add evidence presentation and typed error preservation, retain all ledger capabilities. Use current F02 semantic mapping with repository-scoped CSS variables; do not alias same-spelled spacing tokens across estates.
4. **Integrate origin → replay → evidence → return.** Preserve framework/history fields, validate the same-origin transient envelope, keep cross-Macro behavior with its incumbent owner, and explain fallback accurately. A navigation transition must not save a plan.
5. **Qualify with existing test owners.** Extend native parser/reader tests only for changed behavior and discriminating risk cases. Exercise the real browser journey with authorized guest, entitled, lapsed and unavailable-source fixtures/sessions. Do not run paid-data paths using dev harnesses and call them production proof.
6. **Later authorized release only.** Once separately commissioned, use existing protected PR/CI/review and deployment gates. The registry/publisher admits route projection; deployment and served-path evidence are verified independently. This packet grants none of those effects.

## Responsive and component boundaries

Use the F01 shared shell once. Page content does not recreate global navigation, theme, language, account search or Brain. Keep one primary chart. Inspector is 320px plus 24px gap only when useful width leaves at least the qualified primary minimum; 1024px expanded navigation requires a modal inspector. Controls are staged in one shared sheet on mobile; evidence is full width at ≤600px. Do not fork a mobile replay app.

Dark uses calm luminance depth; light uses white analytical surfaces, a cooler neutral page and subtle shadow/separator structure. Text/data/focus roles differ deliberately; both retain the same information hierarchy and state meanings. Avoid colored container edges and semantic color as the sole signal. Buy/sell is not the same semantic pair as price up/down.

## Compatibility and state migration

No database migration, vendor migration, replay format migration or new URL grammar is required for the presentation work. Preserve current deep links exactly. Existing bookmarks remain valid; malformed extras remain invalid. New transient context must be additive through the existing owner and ignored safely by older views. It may not replace framework markers or existing company-search context.

Preserve current API schemas and authenticated/source-admitted readers while adding view-local typed outcomes. If the access owner changes the shared Large Trades policy, treat it as a separately reviewed compatibility change with an inventory of all consumers and explicit server tests. No “frontend-only” claim may conceal a server access change.

Artifact metadata propagation can remain in memory for an authorized read. Do not persist protected envelopes in localStorage/sessionStorage merely to support navigation. Durable evidence/reconstruction requires the existing owner contract. A data-source refresh must not reinterpret an old index against a new artifact. Safe fallback retains the exact reference and reports that reconstruction is unavailable.

## Performance and accessibility targets

These are future targets, not measurements: p75 LCP ≤2.5s, INP ≤200ms, CLS ≤0.1 on the owner's agreed real-device cohort. Reuse existing data budgets and keep future observations out of current calculations. Render bounded visible rows/frames; preserve all qualified totals. Reserve chart/inspector geometry during load, avoid global re-rendering on every pointer move, and do not start a second fetch loop or feed connection.

Acceptance must include 320/390/600/768/860/861/1024/1200/1255/1256/1280/1440/1600 widths, keyboard-only and touch selection, 200% and 400% zoom/reflow, light/dark, EN/ZH, screen-reader status/slider/tab/dialog labels, focus restoration and reduced motion. Contrast and target geometry must be measured on the final rendered candidate. A screenshot alone cannot prove keyboard, request ownership or accessibility behavior.

## Rollback

The future frontend change should remain separable from producer contracts. If the recomposition or return adapter regresses, revert the owned frontend delta through the incumbent release path, retaining the old route grammar, server checks, source readers and dev404. Do not roll back by disabling entitlement, source admission, transport validation or stale-data clearing. If a return context was created by a newer version, an older version should ignore it safely and offer the named generic destination; it must not execute unknown fields.

A source publication fault belongs to the existing publisher and its known-good artifact/receipt process. D08D creates no alternative source or recovery engine. If a save effect becomes unknown, rollback is not a retry mechanism: reconcile the original D23 operation. If a Paper edit becomes unknown in a later admitted phase, reconcile the original carrier/target before any new write.

## Gates that remain outside this packet

- P00: published direct app action refresh and exact dedicated-file creation/verification.
- F01/F02: released joint foundation, followed by affected native compositions and review.
- D08/D06/D08A: actual exact-return implementation/qualification and required session-zone mapping.
- Terminal access owner: equity page/shared API policy and identity-change proof.
- Existing archive/distribution publisher: admitted retained windows and exact artifact retrieval if promised.
- D23: durable evidence save/readback/reconciliation if included in a later scope.
- F03/incumbent registry: native route admission; QA01: formal visual/product acceptance; later builder: entitled real-browser proof.

No broad “data blocked” label should replace these concrete actions and evidence requirements.
