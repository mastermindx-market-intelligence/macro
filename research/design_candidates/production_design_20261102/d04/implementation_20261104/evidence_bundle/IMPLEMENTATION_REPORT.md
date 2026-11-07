# D04 — Confluence implementation and design verification, 2026-11-04

> This readable copy accompanies the [verified evidence bundle](README.md). The original report and every packet artifact are preserved byte for byte in that bundle. Relative artifact references below identify files in the reconstructed packet.

**Outcome: a bounded Confluence source implementation is committed, pushed and available in [held draft #10705](https://github.com/mastermindx-market-intelligence/macro/pull/10705), at `126bb13421d7052527ce034a900c89cd1a7fb9e6`.** The existing D04 domain carrier remains [draft #7727](https://github.com/mastermindx-market-intelligence/macro/pull/7727).

The current Chairman instruction, “Resume design and implementation,” expanded the original specification-only assignment. This report supersedes that earlier implementation-later wording. It does not promote the whole D04 design to final acceptance, change the ten-route programme scope, or release any merge, Ready, enqueue, relabel, Paper-write or production-deployment hold.

## 1. What the researcher can now do

The page answers the population question before offering detail: how many eligible active signal combinations the source contains, and how many are displayed. In the captured existing source, that is **18 eligible combinations, with the top three displayed**. This is a snapshot statement, not a claim about a later production market state.

Each recipe presents recent/test and older/training readings at equal visual weight. Month and fire counts sit beside the readings. The reader can see the actual D/W conditions, inspect the source method, open a free company, and return through native browser history without losing the exact origin URL. The source ranking and stable tie order remain the producer's ordering.

The comparison explains what the number means. It is the equal-weight mean of within-month winning-fire proportions after next-close entry and 21 trading days. It is not a pooled trade win rate or the fraction of profitable months. The older period is training and the recent period is test; neither label establishes untouched prospective validation. The Wilson-based result is described as a ranking heuristic, not a statistical-significance result.

The page preserves uncertainty. An invalid or absent source produces an unavailable state with unknown population; a qualified source with no eligible active combinations produces the verified-empty state. A missing edge, malformed optional flag, incomplete frequency history or missing older comparison does not become zero, a false historical finding, or a claim that the older period failed.

## 2. Retention and source boundaries

The complete 113-capability ledger (`../CAPABILITY_LEDGER.md` in the reconstructed packet) remains intact: **75 RETAIN, 30 IMPROVE, 3 RELOCATE, 5 BLOCKED_DATA and zero removals**. All ten assigned canonical route families remain in the contract. The implementation diff affects the Confluence builder, template, paired generated output, focused tests, finite browser verifier and its evidence.

| Canonical family | This bounded implementation |
| --- | --- |
| `/confluence_screener.html` | Evidence semantics, dense comparison, methodology interaction and protected-name reader implemented. |
| `/advanced.html` | Quant Lab capabilities and ten analytical anchors retained; source unchanged. |
| `/basket/<id>.html` | All 49 catalog IDs and detail identity contract retained; source unchanged. |
| `/baskets.html` | Compatibility gateway and distinct receivers retained; source unchanged. |
| `/discovery.html` | Top Picks retained; source unchanged. |
| `/etfs.html` | Fund-move overview and protected graded rows retained; source unchanged. |
| `/movers.html` | Stocks-hub compatibility receiver retained; source unchanged. |
| `/sector_heatmap.html` | S&P and theme-map semantics, classification and availability contract retained; source unchanged. |
| Terminal `/discover` | Six current panes, screening, heatmap and saved-state owners retained; source unchanged. |
| Terminal `/dislocations` | Episode lifecycle and free/paid access boundary retained; source unchanged. |

All 24 Sector Central legacy mappings remain in compatibility.json (`../compatibility.json` in the reconstructed packet). Device presets, account Smart Screens and thesis saved views keep their existing distinct owners. No new persistence, routing, authentication, source-of-truth or global navigation system was introduced. The broader heatmap exact-return and typed fixed/live saving work remains specified, not represented as implemented by this slice.

Before writes, the current workspace/PR census identified adjacent owners. Sector Central #7384 and #9579 are separate work. #8428 owns empty-source share-card cleanup and conditional SEO in the same screener files; its hunks and delivery were left with that carrier. The existing D04 Paper writer was closed, and no D04 Paper mutation was dispatched.

## 3. Implemented data contract

The implementation extends the current artifact reader and the existing `tier_payload.v1` projection. It does not change the miner or create a new endpoint.

| Field / condition | Reader behavior |
| --- | --- |
| Qualified core source | Require a timezone-qualified build timestamp, universe count, split date, valid D/W leg definitions/indices, unique combo IDs, valid distinct tickers, finite ranked eligible rows and positive period sample counts. |
| `source_status` | `available` or `unavailable`; unavailable counts are null/unknown. |
| `source_generation` | `confluence_source.v1`, full `generated_utc`, SHA-256 of canonical source JSON. Both projections derive it from the same loaded artifact. |
| `n_active_total` | All eligible active long combinations, independent of the top-three display limit. |
| Public identities | Only the free first rank receives ticker/name identities. Paid rows expose counts and evidence, not their identities. |
| Optional comparison/history | Missing or malformed values remain unavailable. Numeric comparison evidence for both periods determines period-support wording; a Boolean flag cannot supply a missing older comparison. |
| Source clock | Labeled “Source built”; the source does not supply a market-observation clock. |
| Baselines | Display source-provided recent/older random-entry readings when present; do not reconstruct a missing baseline from an edge. |

The digest is a consistency receipt, not an entitlement or a market timestamp. A same-ID or same-clock payload from a different source digest cannot hydrate. Older HTML can ignore additional payload metadata; the new reader refuses an old payload without the required receipt and offers a reload. Publish or roll back the generated public page and protected payload as a coherent pair.

### Complete private response before any disclosure

The reader checks the existing protected endpoint's response envelope, required tier/page/schema, status, build clock and receipt. It then validates the exact expected combo ID set, no duplicate or unknown IDs, exact public/private counts, arrays, unique valid ticker symbols and string names. It prepares every replacement off-DOM and commits the complete result together.

A missing array is invalid data, not “no matches.” A 401 is expired access, 403 is denied access, network/server failure is unavailable, and a receipt mismatch is a different-update state. Public evidence and counts stay readable in each case.

The existing `MDXAuth` session/user owner remains authoritative for identity; the existing protected endpoint remains authoritative for entitlement. Epoch and owner checks reject late results after observed sign-out or account changes, including without AbortController. Page/visibility lifecycle events restore public walls. The session's own expiry is a conservative display deadline: already loaded names are cleared and a response arriving after that deadline cannot commit. Token refresh belongs to the incumbent auth owner.

The display deadline is not a new plan lease. Subscription revocation without an auth event is learned through the existing owner or the next protected read. The implementation adds no refresh polling, session store or competing plan authority.

## 4. Interaction and visual design

**Desktop:** neutral cards place the recipe and equal-weight historical pair in one comparison row. Visible samples and full conditions support comparison before disclosure. Source order is preserved.

**Phone:** the pair moves below the title without reducing either period's prominence. All legs remain visible; long company names wrap independently of their unbroken ticker symbols. Action targets are at least 44 CSS pixels in the verified primary-link/button set.

A native `details/summary` section replaces the rate values' unreliable touch-tooltip interaction. Its content covers month means, training/test meaning, baseline units, rising-edge sightings, yearly frequency, D/W bars and the ranking heuristic. Touch and keyboard exercise the same persistent disclosure. The shared Lens engine is not forked.

**Dark treatment:** restrained dark panel depth, even borders and semantic ink. **Light treatment:** cool canvas, white material, fine neutral borders and the existing shadow token; inherited glass treatment is removed from these cards. The themes share information hierarchy and behavior while using different material treatment. No colored container edge was added.

Retry focus is request-scoped. While checking, the retry remains focusable with its busy/disabled semantics, and duplicate activation is guarded. Successful retry transfers focus to the first newly available name only if the retry still owns focus. Deliberate focus movement, failure or an account transition does not carry stale focus intent into later automatic hydration. Clearing an already focused paid row returns focus to its own public row.

### Exact-return proof and limits

The finite browser journey opens the preserved free-company URL and uses native Back. It restores the exact origin URL including the repeated `keep=a&keep=b` query and `#return-point` fragment. This is evidence for that native same-origin URL path. It does not establish the entire cross-origin Macro↔Terminal return contract, a virtual heatmap scroll anchor, inspector tab restoration or saved-view reopening; those remain in the full D04 acceptance plan.

## 5. Verification and actual evidence

| Verification | Observed result | Qualification |
| --- | --- | --- |
| Page/source + unchanged miner suite | **138 passed**, 22 warnings | Focused suite in a site/mockups-qualified managed workspace; data/verify_shots were not materialized and no full-data suite was claimed. |
| Finite local browser harness | **39 passed, zero failed** | Chromium 151.0.7922.34; real renderer/theme/handlers with controlled auth and private HTTP fixtures. |
| Canonical capture owner | **24/24 captured** | Eight anonymous theme/locale/viewport cells, each at rest, actual method focus and actual CTA hover. |
| Design-system added-line ratchet | **Zero blocking findings** | Existing estate findings remain outside this change; none were silently waived. |
| Runtime style injection | **Passed** | 275 JS files scanned; frozen allowance did not grow. |
| Canonical visual receipt guard | **Passed** | Existing `mastermind.page_evidence_receipt.v1` / `mastermind.p0_evidence.v2` contracts; no second capture schema. |
| Final diff whitespace check | **Passed** | Generated blank-line whitespace normalized in the existing renderer. |
| Exact source publication | **Confirmed** | Installed publisher reports final local/remote head equal and workspace clean. |
| GitHub CI / release | **Separate, not locally inferred** | See the dated publication receipt. Draft/no-arm/no-release hold remains. |

The 39 browser cases cover complete and reordered success; nine malformed/mismatched row variants plus null/invalid JSON; 401/403/500/network failure; late account/sign-out responses; silent expiry before and after hydration; token-refresh deadline replacement; retry focus preservation; exact native Back URL; dense EN/ZH and dark/light layouts; genuine touch/keyboard disclosure; unavailable versus verified-zero states; and intermediate widths.

Dense-fixture sample text measures **5.73:1 contrast in dark** and **7.03:1 in light**. No full-page horizontal overflow was observed at 320, 390, 820, 1024 and 1440 CSS pixels. Both period readings remained 28px and samples at least 12.5px in the matrix. This is not a full assistive-technology, Safari/iOS, real-user-performance or actual 400% zoom audit.

The browser report and all **23 labeled fixture/source-artifact captures** are in `evidence/`; start with browser-report.json (`evidence/browser-report.json` in the reconstructed packet), verification-summary.json (`evidence/verification-summary.json` in the reconstructed packet) and unit-tests.xml (`evidence/unit-tests.xml` in the reconstructed packet). Coverage (`coverage.json` in the reconstructed packet) connects the bounded proof to the original case IDs without claiming all 75 programme cases executed.

The **24 canonical captures and their receipt** are committed with the product source: [design rationale](https://github.com/mastermindx-market-intelligence/macro/blob/126bb13421d7052527ce034a900c89cd1a7fb9e6/mockups/evidence/d04-confluence-evidence-20261104/README.md), [manifest](https://github.com/mastermindx-market-intelligence/macro/blob/126bb13421d7052527ce034a900c89cd1a7fb9e6/mockups/evidence/d04-confluence-evidence-20261104/manifest.json). The final missing-older-comparison repair did not change the served page blob, `054327e23503f980cbf2fa99b1503c84e3fd4641`; the accepted captures were reused on verified byte identity.

Self-QA inspected hierarchy, dense names, unbroken tickers, sample legibility, light material, phone wrapping, native disclosure and complete focus outlines. The original floating Brain chrome can overlap the right edge on a phone; it remains an explicit shared-owner limitation. Existing Lens behavior outside the relocated numeric definitions was not rewritten or hidden in captures.

## 6. Build and integration guidance

Source files are [the builder](https://github.com/mastermindx-market-intelligence/macro/blob/126bb13421d7052527ce034a900c89cd1a7fb9e6/scripts/build_confluence_screener.py), [the template](https://github.com/mastermindx-market-intelligence/macro/blob/126bb13421d7052527ce034a900c89cd1a7fb9e6/templates/confluence_screener.html.j2), [focused tests](https://github.com/mastermindx-market-intelligence/macro/blob/126bb13421d7052527ce034a900c89cd1a7fb9e6/tests/test_confluence_screener_page.py), and [finite browser verification](https://github.com/mastermindx-market-intelligence/macro/blob/126bb13421d7052527ce034a900c89cd1a7fb9e6/scripts/verify_confluence_screener_browser.py). The generated public HTML and protected JSON accompany the source change.

Reproduce in an admitted workspace with the relevant sparse profiles qualified:

```sh
python3 -m scripts.build_confluence_screener
python3 -m pytest tests/test_confluence_screener_page.py tests/test_tech_confluence.py -q
python3 scripts/verify_confluence_screener_browser.py --out /tmp/d04-confluence-browser
```

The broader BUILD_AND_ACCEPTANCE.md (`../BUILD_AND_ACCEPTANCE.md` in the reconstructed packet) remains the integration order for the ten-route programme. Do not replace the existing global navigation, auth, saved-state or source owners to integrate this slice. Keep source generation matching across public and protected output. A future authorized rollback reverts this paired source/output change through the ordinary owner; it does not alter account or plan records.

## 7. Custody, dependency and release record

- Protected Mastermind law: `33aec27fff672a4f334cb79b3b2604156401597d`, Skillpack 1.0.1/bootstrap1. Current Web review waiver applies; formal branch protections/non-author approvals remain distinct.
- Macro base: `c53915f6d67078d5c0aeaf73bf85ddea1a23de03`. Implementation commits: `b70608466bbd294229cb159950b77d1afcbdbed6`, then `126bb13421d7052527ce034a900c89cd1a7fb9e6`.
- Installed workspace operation: `d04-confluence-evidence-20261104`; branch `sol/web-d04-confluence-evidence-20261104`. Root was the sole implementation writer.
- A generic typed read precheck initially failed. Bounded checks of the original owner succeeded; a serialized typed status then succeeded. No live configuration, credential, account or publisher was changed.
- The first push returned uncertain. The original publisher and original GitHub branch both proved the exact head applied; no blind retry or re-home occurred. The final push reported `APPLIED_AFTER_AMBIGUOUS_PUSH_RETURN` with equal local/remote head and clean state.
- F01 #10645 at `abfecf1efc452383fe720cb3ea2016ad8d7088e0` and F02 #10630 at `13baa784723b72458f7f694cac925f2c7f96e3d7` remain provisional joint foundations. P00 #10626 runtime acceptance remains PARTIAL; source repair is not app admission.
- Terminal directory #1264 is actually merged at `f528a219cc5d73e94e058575e3df83d689632bf9`. D23 #778 remains draft at `88f2919a5c2222bcf05f452f2549b9af180dcae6`; typed saved heatmap behavior is not supplied by this Confluence work.
- Actual Paper inspection retained the exact MASTERMIND PAGES target `01M2WGNCX9475G79JRKJTCM08P / p-H-1`; no D04 write was dispatched. F02's original unknown effect remains at its original target and is not a D04 effect.
- All 25 inherited reference conditions retain their recorded status. Optional source advice was consumed and stopped; no blanket external reviewer or fabricated formal approval was introduced.

**Bounded result:** implemented, locally verified, source-published and held in draft. **Remaining programme work:** final qualified Paper composition/reference acceptance, broader heatmap return and saved-view integration, full programme acceptance and any subsequently authorized release. These stages are not implied by local green tests or the PR URL.

## 8. Canonical evidence representation

All 50 prepared changes are committed and byte-verified in 14 UTF-8 bundle parts on the existing D04 carrier. The parts preserve original text plus base64 original PNG bytes. Combined with the exact 34-file baseline at `23bd2c0b7400548485e39c119954977b8a9f3472`, they reconstruct the complete 70-file packet. Reconstruction passed; its 30 artifact checks and 69 file digests passed.

The attempted native tree remains unmaterialized: GitHub's Git commit endpoint returned definitive HTTP 422 “Tree SHA does not exist,” although the exact tree was readable and the original branch remained unchanged. The supported Contents API preserved the same carrier and writer. No credential, branch, workspace or product-source publication mechanism was replaced. The 24 canonical product captures remain native files in implementation draft #10705; the 23 additional packet captures are encoded here and reconstruct to their original PNG bytes.

At the dated 2026-11-04T05:28:37Z source observation, main authority, fence-pack, contract-delta and ci-plan passed. Ten CI packs were running and two queued. The inactive merge-queue-pilot authority context reported `inactive_base_context`; this is preserved separately from the accepted main context. No all-CI-green or release claim is made.
