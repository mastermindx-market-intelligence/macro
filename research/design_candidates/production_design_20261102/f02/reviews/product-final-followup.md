# F02 Product Regression Critic — final narrow follow-up

**Scoped finding disposition: PRC-010 RESOLVED IN SOURCE POLICY.**

**Advisory adoption verdict: BLOCK — unchanged.** PRC-007 remains an open major consumer-integration qualification gap. Actual browser/input/zoom, rendered density, source/service integration, Paper, F01 and formal review/authority requirements remain open.

**Follow-up freeze time:** 2026-11-03 02:52:53 UTC

This is an independent native advisory follow-up to the frozen Product Regression Critic repair report. It addresses the density-policy correction only. It is not an admitted Opus RIG receipt, designated authority approval, or a new broad audit. The first-pass, rationale-pass and repair-pass reports remain unchanged.

## 1. Exact reviewed set

Reviewed root: **/workspace/scratch/55964f568673/f02/**.

| Identity | Value |
| --- | --- |
| Supplied committed follow-up | `d68d5ecfbcd7e29094f59af3f44e7ae2a0f7f940` |
| Packet | `reviews/FINAL_FOLLOWUP_PACKET.md` |
| Manifest | `reviews/final-followup-artifacts.json` |
| Manifest freeze | `2026-11-03T02:48:47.284785+00:00` |
| Member count | **55** |
| Artifact-set SHA256 | `38b19c087b0639b728f37d015c939e7abbccf95722b72730f6f5fce84e025324` |
| Manifest file SHA256 | `f1c0ed1ff54da7dcbc4cc9f14d57609df8a37375e0c51cc1192e86263d947ccb` |
| Current HTML SHA256 | `f206a0274bd710835aabe3f80053bc87b359f7409ff09ea6d3bc49afdf4cb5f4` |
| Prior repair commit | `1253a647d193e1eacd1eb6f523a7a031529d2150` |
| Prior repair artifact set | `6c1f8ba6937c620a306644764d69d7adef5672d27f6c512a080dcb35063f9ca3` |
| Prior repair HTML SHA256 | `126fd3bce0677f73ca0f422c762f0ce47bc239d61f04d959688c1a93d2555360` |

All **55 members** matched their recorded byte counts and individual hashes, including the pre-write recheck. The aggregate reproduced exactly using lexical relative-path order and UTF-8 `path + U+0000 + lowercase SHA256 + U+000A`. The supplied repository commit is recorded as coordinator provenance; local file verification does not independently inspect that commit's Git history.

The three earlier Product Regression Critic reports were rehashed unchanged:

| Historical report | SHA256 |
| --- | --- |
| `product-first-pass.md` | `dc49d84c50d250a0616079372d5e3f5508edc66acc9c634f1a5b53a8ed62051b` |
| `product-rationale-pass.md` | `0599244070916d53ce282551141d2e55c407e12e942da96ef2aaadb6cc41dbfe` |
| `product-repair-pass.md` | `524c34bdac1d21a881706c8cb82187a884a49a927c55476ff17330982d6802fc` |

## 2. Scope and precise source binding

I inspected the follow-up packet, current density selectors and root preference wiring, the corresponding SYSTEM_CONTRACT paragraph, and the refreshed source-verification/model reports. I compared the current HTML and contract with the prior repair copy at **/workspace/scratch/55964f568673/f02-review-freeze-2/**; that prior HTML matches the previously reviewed `126fd3…` digest.

Read-only byte/string comparisons established:

- Both embedded script blocks are identical between the two HTML revisions.
- The executable JavaScript block is 54,679 bytes and has SHA256 **`593eb4acf659f184eb42c308913ce0d18f9448581007017a07cff922e9973f4b`** in both versions.
- The HTML outside its style element is identical.
- Reversing exactly the three density-policy edits described below reproduces the complete prior HTML.
- The SYSTEM_CONTRACT change is the single spacing-policy paragraph in section 3.

I did not execute the HTML, JavaScript, checker, browser, DOM or renderer. No Paper, account or service operation occurred. I read no peer report. The set also contains mobile static-cue changes; their member hashes were validated, but visual disposition of that separate finding is outside this narrow product follow-up.

The refreshed `evidence/followup-source-verification.json` and `repair-model-verification.json` both bind to the current HTML hash. They report syntax/source-policy and pure-model checks with explicit limitations. Their counts remain author-supplied source-model evidence; they do not establish computed styles, measured row geometry or input behavior.

## 3. PRC-010 disposition

**Original severity:** minor.  
**Current disposition:** **Resolved in source policy.**  
**Affected critical task:** T11; complete task judgment remains UNKNOWN.

The prior repair source set the Options body cells to an unconditional 40px declared height and then 52px on phones. Those more-specific selectors bypassed the row token that the Density control changed.

The follow-up makes these three exact source changes:

| Surface | Prior source policy | Current source policy |
| --- | --- | --- |
| Options body cells outside the narrow override | `height:40px` | `height:var(--row)` |
| Comfortable token at widths up to 600px | No separate 64px narrow override | `html[data-density=comfortable]{--row:64px}` |
| Options body cells at widths up to 600px | `height:52px` | `height:max(52px,var(--row))` |

The unchanged preference wiring writes the selected density to the root `data-density` attribute. The current CSS therefore expresses the following declared spacing policies:

| Width class | Density | Shared row token | Options body policy |
| --- | --- | --- | --- |
| Above 600px | Dense | 40px | 40px through the token |
| Above 600px | Comfortable | 52px | 52px through the token |
| Up to 600px | Dense | 48px | At least 52px |
| Up to 600px | Comfortable | 64px | At least 64px |

These are **source-declared spacing policies**, not measured rendered heights. Intrinsic text, wrapping, cell padding and controls may require taller rows. In particular, a larger declared minimum does not prove that every rendered row visibly grows when its content already requires more space.

SYSTEM_CONTRACT section 3 now states the desktop 40/52px targets, phone row/control floors, Options 52px phone floor, Comfortable 64px phone token and intrinsic-content qualification. That paragraph agrees with the repaired selectors.

The unconditional Options-cell policy that caused PRC-010 is removed. No additional source change is required to close that specific finding. The later browser qualification must still show that the advertised preference produces useful breathing room in actual Options rows while retaining field meaning, source access, touch targets and the dense tape-first arrangement.

## 4. Finding and task continuity

This narrow correction does not reopen or silently rewrite the previous artifact judgments:

| Finding or task | Continuing disposition |
| --- | --- |
| PRC-001–006, PRC-008 and PRC-009 | The prior source/static repair dispositions carry forward. This pass adds no new runtime proof. |
| PRC-007 | **Major, still open.** Full consumer preservation, real recovery, source mappings, lifecycle and existing chart/virtualization integration remain unproved. |
| PRC-010 | **Resolved in source policy at this follow-up set.** Actual density rendering remains unverified. |
| T11 theme/locale/density | **UNKNOWN** as a complete critical task. Its concrete Options density-policy defect is corrected, but rendered spacing, real CJK/long-label behavior and preference/input operation still lack proof. |
| Other T01–T12 judgments | Unchanged from the frozen repair report. There is no new broad task reassessment in this narrow pass. |

The predecessor's BLOCK is not being carried forward because an already-fixed minor defect persists. Adoption remains blocked by the explicit critical qualification gaps below.

## 5. Mandatory remaining gates

The exact finite owner witnesses and browser cases in sections 5 and 7 of **[product-repair-pass.md](sandbox:/workspace/scratch/55964f568673/f02/reviews/product-repair-pass.md)** remain required. This follow-up supplies none of their missing runtime or service evidence.

| Gate | Minimum evidence still required |
| --- | --- |
| Consumer preservation — PRC-007 | Source-bound mappings plus exercised paths at the implementation revision: Macro regime/risk/calendar/linked desks and sibling template; Company annual/quarterly/all statements/history/definitions/transcripts and correct entity switching; Options existing workflows/filters/saved screens/share/export with true scope and clock/coverage/access meaning. |
| Existing chart and domain semantics | Existing engine's canonical row/time identity, sort/prepend/filter/replay, mounted active descendant/count/index, keyboard/selection and CSV/replay refusal/scope; domain-owned labels, count partitions and a meaningful lifecycle/return condition with provenance intact. |
| Public editorial and real recovery/write ownership | Actual emitted original content, canonical/hash/TOC/dates/calculation/continuation preservation and effective language; real sign-in/plan/session return paths; owner request/object identity, failure versus uncertainty, reconciliation and confirmed readback for any later real write integration. |
| Browser/input/rendering | Exact-revision authorized preview; retained/removed-row focus and visible scroll return; dock/overlay and Escape; combined read/write states; keyboard/touch/local scrolling; actual 390px/320px and 400% zoom; light/dark/CJK/long-label/forced-color cases. Include actual Options density behavior after this source fix. |
| P00 and editable Paper | Qualified current server/catalog and admitted carrier with bounded supported write/readback, followed by real editable objects/annotations, exact IDs, geometry/content readback and source-bound captures. |
| F01/F02 joint freeze | Versioned shell/system agreement on widths, navigation/inspector slots, narrow/public/focused-chart boundaries, preference/context and return/history behavior, bound to the reviewed source and Paper set. |
| Formal review, authority and served qualification | Required admitted independent review receipts for the exact final set, actual designated authority verdict, and applicable served implementation evidence. Native advisory reports, static drawings and model checks do not substitute. |

No real consumer capability is inferred to have been deleted. The constraint is the missing preservation proof. No Paper/browser limitation is being used to excuse a source defect; the identified source policy is now repaired.

## 6. Frozen result

**PRC-010 is closed at the source-policy boundary for artifact set `38b19c087b0639b728f37d015c939e7abbccf95722b72730f6f5fce84e025324`. Advisory adoption remains BLOCK because PRC-007 and the actual interaction/integration qualification remain open.**

This report is frozen at the UTC time above. It grants no formal approval and changes no earlier report.

