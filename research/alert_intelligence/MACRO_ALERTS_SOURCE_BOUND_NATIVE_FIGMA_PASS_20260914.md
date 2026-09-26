# Macro Alert Center — real-source brief and native Figma pass

**Status:** local source-bound preview `BUILT_NOT_PROVEN` for production; native design `PARTIAL`; deployed redesign still `SPEC_ONLY`. These are distinct states. The canonical production builder/template was not changed or deployed by this pass.

**Current authority:** Chris described the action-led revision as an excellent design and directed Sol to improve it and advance the next steps. Preserve Review first / Watch next / For awareness and the specific change/implication/limitation/next-action hierarchy. The rejected bland chronology-first design is not revived. The scope remains shared Macro `alerts.html`, not Terminal `/alerts`.

**Operation:** `macro-alert-source-bound-native-figma-20260914-sol-001`. Existing carrier: Draft #7135 / `sol/alert-fabric-architecture-20260913`; prewrite head `33532d626be931b31e9aa9daf233e0a7687bf573`, freshly reconciled before this write. No new workstream, Executive Job, worker, watcher or source writer was created.

**Procedure pin:** compatible Skillpack 1.0.1 at Mastermind protected `bffe2ca8506346ea278c8ee469bf1ac30a4de008`. **Source pin:** Macro `6a5675d481c0d5a6f47b8429c3e4643755fe90fa`.

## 1. What now exists

The approved action-led preview remains byte-identical as a fictional design reference. A separate local source-backed view now consumes three actual records from the existing canonical Alert Triage publication, preserves their IDs and source fields, adds explicit authored family interpretation, and renders the useful card/detail/history/source-handoff journey. Native Figma creation and canvas writing were available in this turn, so the dedicated Macro file was created and populated rather than continuing to claim a tooling blocker.

The achieved local path is:

`canonical published alerts_triage.json -> retained exact source cases -> pure brief presenter -> interactive local design preview`.

It is **not** a new collector or alert engine, and it is **not yet** the production path:

`build_triage -> build_alerts_page -> production template -> deployed alerts.html`.

The source-bound presenter is an integration candidate and proof of content behavior, not a claim that the existing assembler or renderer has adopted it.

## 2. Source capture and exact cases

Source: `site/factordata/alerts_triage.json` at the Macro source pin. Metadata says publication `2026-09-14 07:27 UTC`, New York board day `2026-09-14`, as-of `2026-09-11`, 30-day window and 60 alerts.

Whole publication: **123,644 bytes**, SHA256 `ff7501f84c37e4f00acc8c1f512be78068bcb875e7592a087d1b93b0e4fbf05f`.
Selected-case pack: **8,271 bytes**, SHA256 `683580416e77e12c97f5fb832acbd0d83e4dfc4046e359ea06f1d05866ac151f`.
The selection is **three cases from 60**, not a full-board or whole-market summary. Coverage-read success does not make every event fresh.

| Native alert ID | Actual source event | What the useful brief preserves |
|---|---|---|
| `91cdf2add5df` | Sep 9 Macro `transition_state_change`: footing went from `a new regime` to `shifting`, with four warning flags | Not the sample's Reflation-to-Stagflation transition. Act/critical priority 82 is preserved as attention, not probability. Two first/latest firings do not prove continuous activity. |
| `441bf32cf79a` | Sep 11 Macro `risk_state_elevated`: ELEVATED at **63/100**, with positioning/volatility/breadth fragility | **Source risk 63 is distinct from attention priority 70.** No prior value is supplied. Recorded source action concerned risk reduction; the UI requires rechecking current conditions before applying dated guidance. Documented, not backtested. |
| `0a4ada0223d7` | Sep 10 copper `risk_regime`: Risk Index rose through a threshold to **34** | Prior value and source-as-of are not supplied. No invented Calm baseline. Four firings between Aug 28 and Sep 10 do not supply intermediate dates or persistence. This is a commodity-specific warning, not broad confirmation. |

All three events are outside the snapshot's two-day fresh window. The real-data composition therefore says **Earlier high-priority changes** and distinguishes importance from a newly triggered alert. No event date is refreshed from publication time. No new stock-selection or trading authority is inferred.

## 3. Content capability and additional hardening

The local `briefs.py` implements a pure view over canonical rows: exact ID/type/tier/severity/priority and components; event/source/record/publication clocks; nullable change values; source-reported headline/detail/action; explicitly authored implication/next step/reassessment condition; family-validation scope; and permitted current-source-panel links. Raw inputs are copied without mutation. No network, model, account, database, notification or ranking write occurs inside it.

The final pass added four discriminating regression tests. They first failed for: an unparseable regime message; an opposite transition out of shifting; copper risk falling instead of rising; and a changed source firing count. The presenter now abstains from the additional authored brief when the narrow expected source shape/direction does not match, and derives recurrence copy from the supplied count rather than a literal sample count.

This is deliberately bounded text parsing in a prototype. Before production integration, use the accepted structured owner fields where available, and retain explicit unavailable/unsupported outcomes rather than treating any familiar event type as license for the same narrative. Do not create a second source-normalization or event store to solve that integration.

The HTML uses the approved visual language with actual data and separate Takeaway/Evidence/History panels, query/reset, focus return, nested source handoff, English/Chinese and dark/light. The original approved fictional scenarios remain a separate file and are not relabeled as real data.

## 4. Source-return proof and limitation

Bounded read-only HTTP checks returned 200 and found the declared IDs on:

- `https://www.mastermind-x.com/macro.html#regime-radar`
- `https://www.mastermind-x.com/macro.html#dlg-risk`
- `https://www.mastermind-x.com/commodities.html#timeline`

The Macro page response had SHA256 `c77cc8d8b29fd8cbcf617128530a41212da4ff2fa0f75e5b87883ef76867fbb3`; the Commodities page response had SHA256 `7bdb7313f43a5d0cea8dd2647af122f5340f35b6f4b0239810058ed053768cb0`.

These results establish **response and anchor presence only**. They do not prove actual browser hash/dialog opening, current authenticated values or exact historical event retrieval. The handoff explicitly labels the link as a **current source-owned panel, not an archive of the original firing**.

The live JSON endpoint returned HTTP 401. The canonical repository publication was used; no credentials, account switch or access-control bypass was attempted. The authorized Studio was verified before the bounded read-only source calls. No remote files or running worker workspaces were changed.

## 5. Dedicated native Macro Figma — actual file, not another blocker

**File:** `MastermindX — Macro Alert Center — Market Changes Desk`.
**File key:** `r1hSkfDg4vGzjWRySgrHE1`.
**URL:** https://www.figma.com/design/r1hSkfDg4vGzjWRySgrHE1

The connected principal was `mastermindx6031@gmail.com`, Professional/Full on MastermindX's team. Native file creation and canvas changes succeeded. Do not create another Macro file or ask for the old Terminal links again.

| View | Exact node |
|---|---|
| Approved action-led desktop, dark EN | `6:2` |
| Approved action-led desktop, light EN | `6:116` |
| Actual retained-source case view, desktop | `6:153` |
| Actual equity-risk reference inspector | `8:64` |
| Approved mobile, dark EN / light EN | `12:232` / `12:344` |
| Actual retained-source case view, mobile | `12:456` |
| Actual risk mobile inspector | `13:300` |
| Scope/foundation frame | `2:61` |
| Source, verification and continuation handoff | `19:2` |

Pages: `0:1` Foundations + Scope; `2:67` Components; `2:68` Now / Approved Direction; `2:69` Evidence Inspector reference compositions; `2:70` Mobile; `2:71` Proof + Handoff.

The file contains native editable text, Auto Layout, 50 local primitive/semantic/layout variables in three collections, dark/light modes, action variants, priority/watch cards, proper mobile component structures, source-specific inspectors and saved prototype references. It is not a flattened screenshot import. A discovered existing Body style was inspected/imported as reference; the approved code's typography controls these compositions. No unrelated community design kit was substituted and no font files were distributed.

### Saved primary prototype paths

Desktop page `2:68` has three explicit starts: `6:2` approved dark, `6:153` retained source, `6:116` approved light. Sample cards lead to sample inspectors; real source cards lead to their matching real source inspectors. Overlays close to the underlying page. Light cards have light inspector copies.

Real desktop card -> overlay pairs: risk `6:204` -> `9:266`; regime `6:184` -> `10:89`; copper `6:227` -> `10:120`.

Mobile page `2:70` starts at `12:232`, `12:344` and `12:456`. Real mobile pairs: risk `16:393` -> `13:300`; regime `16:373` -> `13:334`; copper `16:413` -> `13:368`. Navigation is full-screen with Back. All configured NODE destinations remain on their current Figma page.

The native detail controls currently scroll to named Takeaway/Evidence/History sections. The local HTML implements distinct tab-state panels. This difference is recorded; configured native links are not falsely claimed to replicate every local interaction.

### Mobile repair actually completed

The initial native mobile clone exposed a source of Figma-specific breakage: direction changes left fixed axis sizes, and structural overrides inside desktop instances did not persist. The title wrapped into fragments and a second priority card was clipped.

Readback identified those exact sizes/modes. Proper mobile component masters (`15:4` priority, `15:24` watch), replacement instances and explicit Fill/Hug sizing repaired the underlying cause. The subsequent screenshot showed both priority cards, readable copy and full-width actions. Redundant mobile review-guide chrome was removed so the first meaningful card is reached sooner. This repair affected only this turn's new Macro objects, not Terminal or desktop source components.

## 6. Verification — precise claims

- **22 unit tests passed**, including the four source-shape/counterfactual regressions. Initial red and final green receipts are retained in the attachment.
- **60 offline browser/state checks passed; zero script errors.** Forty are width/language/theme combinations, not forty separate product capabilities. Widths 320/390/768/1024/1440, English/Chinese, dark/light, actual source facts, source-score separation, dated/current boundaries, query/reset, historical disclosure, nested dialogs/focus and reduced motion were covered.
- **Seven local screenshots** were captured after the final source-bound build. Representative source desktop/mobile and native desktop/light/mobile/inspector outputs were visually reviewed by Sol.
- Native saved readback: **87 configured actions; zero missing destinations; zero cross-page NODE actions; no missing fonts; zero containment errors in ten specifically checked frames**. Six named flow starts are saved.
- The native handoff was updated to the final twenty-two-unit-test count.

The browser harness used offline `page.set_content` after local URL navigation was policy-blocked. No policy was disabled. It verifies local DOM and interactions, not a hosted or production HTTP path. A temporary local HTTP process was stopped. Native readback proves saved structure/references, not an executed Figma presentation or independent/human usability test. No WCAG certification or trading-validation result is implied.

## 7. Reproducible attachment and hashes

Conversation package: **`Macro_Alert_Center_Source_Bound_and_Figma.zip`**, 1,108,833 bytes, SHA256 `d057748aa1dfa550a618961c8686b79079c0e3d6c366fb317253b99c4006443c`.

It contains 30 files: source-bound HTML, byte-identical approved fictional HTML, presenter/build/source files, exact selected source pack, unit/browser verification, seven screenshots, a gallery, native Figma state/IDs, report and checksum manifest. The repository commit records the artifact; it does not pretend the HTML/code package is already hosted as production code in this PR.

Final source-bound HTML: 65,015 bytes, SHA256 `2ad552ec451a66aac9e3f111d1452c53d4031bf928b043503f92aff63f4c26a6`.
Approved original and `design-scenarios.html`: 111,325 bytes, SHA256 `25151e9ba4354c4aab2186e80e20cbdc5877b0b93a7ec09f28d2172d7c268f64`, unchanged.

`verify_integrity.py` matched all 29 content files to the manifest. The original source pack hash is checked by the build. No font files, secrets or runtime credentials are included.

## 8. Boundaries and exact continuation

**Complete in this pass:** selected real canonical-source records -> cautious useful brief -> local approved UI; dedicated native Macro Figma file with editable primary compositions and saved desktop/mobile investigation references.

**Still owed:** production integration with the existing assembler/renderer using accepted structured source fields; real customer-route and historical/current evidence return proof; native Explore/History/filter modes, Chinese and full negative-state matrix; full native visual/parity and interactive acceptance.

The existing `alert_triage` remains the sole source assembler. No canonical ID, tier, score, push, source pipeline, portfolio, auth, preference, event store, database, queue or sender is modified by this proof. Both Terminal Figma files remain untouched. #7022 is untouched. #7135 stays Draft, with any merge-conflict/integration state separate from design acceptance. No deployment, customer mail, account-data read, Executive Job, worker, subagent or watcher occurred.

**Next primary action:** integrate the reviewed source-brief behavior into the existing canonical assembler/renderer and prove one real Macro alert through the actual customer-serving path, using the same approved visual hierarchy and exact original/current source behavior. Complete native secondary views against that content rather than restarting architecture or making another competing design. Figma transfer is now achieved for the primary journey; it is no longer the blocker.