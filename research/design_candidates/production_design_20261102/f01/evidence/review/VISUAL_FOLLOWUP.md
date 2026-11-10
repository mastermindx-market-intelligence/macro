# F01 visual follow-up — retained state evidence for VA-08

## Review identity and exact input

**Reviewer:** native advisory agent `/root/f01_visual_advisory`. This is a new bounded, read-only inspection of five supplied retained state compositions. It is not a formal RIG, Opus or QA01 review, a retry of a Paper operation, or a native repair.

**Packet:** `F01-20261103-candidate3-freezeB`.

**Repair manifest SHA-256:** `b339ffef698f307bc9bebdd54a7e46f4712e6b5cdb1438cb520ffe290258ecd8`.

**Published input binding supplied by the coordinating agent:** Macro commit `b55efe221d16ae5e64935af4c60572701b2a43a0`, under `research/design_candidates/production_design_20261102/f01/`; manifest Git blob `935ef948bfe7f86522b29d4a42cf4af8a81c2277`. I did not independently fetch that publication. I verified the manifest's local SHA-256 and the byte lengths/SHA-256 values of the **ten assigned JPG/JSX files plus `REPAIR_REVIEW_PACKET.md`: eleven members, zero mismatches**. Other manifest members were outside this inspection.

**Initial review preserved:** the initial advisory remains bound to `245a7d2cd62d88fb6d2ee3863f9d26c63052d8e7` and manifest `75ad7f14503145e9550f27346eab59ced8cce7e0ad6962e2c999a8c5ae8ae6ab`. This supplement does not rewrite its observations or dispositions.

**Scope:** I opened the five JPGs below with `view_image` at original detail, then inspected their matching JSX for text, structure and target anatomy. I read the repair packet and manifest. I did not read the peer product report, new product-source repairs or upstream implementation files; I did not re-review the unchanged ten F01 candidate boards. All file paths below are relative to `/workspace/scratch/43a778472c23/f01-drafts/`.

## Decision

**The five captures materially improve VA-08's retained visual evidence, but VA-08 remains open.** There are now actual inspected user-facing specimens for session expiry combined with an uncertain save, plan denial, account-service unavailability, an unknown route, and guest presentation preferences. The first packet's lack of these five predecessor pixels is no longer a limitation of the combined review record.

That is an **ADDITIONAL_RETAINED_EVIDENCE** disposition. It does not repair native board I, supply every missing state, establish real owner inputs, or prove that any recovery action works. The packet says all ten F01 candidate images are unchanged, and the original `F01-20261103-c4-state-8-v1` effect remains unresolved. No original native finding is marked repaired or approved here.

| Required disposition | This follow-up's judgment |
| --- | --- |
| `SOURCE_ONLY_RESOLVED` | **None adjudicated.** Source-repair correctness is outside this visual commission. The packet's description of those repairs does not close a native finding. |
| `ADDITIONAL_RETAINED_EVIDENCE` | **Established for the five named predecessor JPG/JSX pairs.** Their actual pixels add the specific coverage described below. |
| `OPEN_NATIVE/OWNER_QUALIFICATION` | **VA-08 remains open.** I and its unknown effect, missing state compositions, current-candidate integration, owner-conditioned behavior and runtime accessibility/return proof remain unqualified. Other initial VA findings retain their original disposition. |

## What the five actual compositions add

### VF-08-A — Expired session with uncertain save

**Evidence:** `evidence/before/Expired-uncertain-save-6OK9-0.jpg` and `.jsx`, 390 × 844, English dark. Key JSX nodes are `6OMA-0`/`6OMB-0` for return identity, `6OME-0`/`6OMF-0` for uncertainty, and `6OMI-0`/`6OMK-0` for recovery actions.

The page has a clear sequence: “Sign in to continue,” an explanation of session expiry, a separate **Analysis · NVIDIA / NVDA · NASDAQ · United States** return card, then an amber **unconfirmed-save** message. The warning is visually prominent before the sign-in action. Its instructions say to check the watchlist after signing in before trying again and explicitly state that nothing will be saved automatically. The screen offers a primary sign-in-and-return action and a separate public-browsing action. The private-content limitation remains readable below both.

This adds the strongest missing evidence from the first VA-08 inspection: an actual user-facing **combined expiry/uncertain-write composition**, rather than a row of design prose. It visually separates an unconfirmed save from a confirmed failure or success, and avoids presenting the sign-in button as a save retry. The named company/listing return card is more concrete than a generic “keep your place” promise.

**Limit:** “check your watchlist” is an instruction, not observed D23 reconciliation. The screenshot does not identify the exact saved-object/request key, show the watchlist readback, or prove a return URL, draft retention, duplicate prevention or actual content hiding. It also does not show pending, known-failed or owner-confirmed successful save states. These are remaining proof boundaries, not assertions that the underlying owner lacks them.

**Disposition:** `ADDITIONAL_RETAINED_EVIDENCE` for the combined state; `OPEN_NATIVE/OWNER_QUALIFICATION` for execution and the other save outcomes.

### VF-08-B — Plan denial

**Evidence:** `evidence/before/Plan-denied-6OKV-0.jpg` and `.jsx`, 390 × 844, English light. Nodes `6OMR-0`/`6OMS-0` name the state; `6ON0-0`/`6ON2-0` contain the principal actions; `6ON7-0` is the account-settings link.

The heading describes additional access, and the body explicitly says the person is signed in but their current plan does not include the report. The composition offers **View plans**, **Return to Research**, and an account-settings path for someone whose plan recently changed. The plan action is primary, while the return remains immediately available as a full-width secondary control. The screen does not visually conflate entitlement denial with expiry or an unavailable account service.

This adds an actual access-denial treatment with clear alternatives. The wrapping at 390 px is readable; the title takes two lines and all supplied content fits within the frame.

**Limit:** the copy requires a real owner-confirmed denial. These pixels do not prove that a server supplied that input, that the links use the proper account/report context, or that access will be rechecked after an account change. The report itself is not named in this specimen, so the precise resource identity is not visually demonstrated.

**Disposition:** `ADDITIONAL_RETAINED_EVIDENCE` for the plan-required composition; actual entitlement and recovery paths remain `OPEN_NATIVE/OWNER_QUALIFICATION`.

### VF-08-C — Account service unavailable

**Evidence:** `evidence/before/Account-unavailable-6OLH-0.jpg` and `.jsx`, 390 × 844, English dark. Nodes `6ONB-0`/`6ONC-0` establish the message; `6ONG-0` describes the retry context; `6ONJ-0`/`6ONL-0` are the actions.

The three-line heading says that account access cannot be checked. The body correctly presents session and plan status as **unknown**, and the “Keep your place” panel explains retrying the check while leaving public browsing available. A full-width **Try again** action is distinct from **Browse public pages**. The final note says private content appears only after verified access and that the destination remains available for retry.

This adds a clear user-facing distinction between a service failure, a signed-out guest and a denied plan. The large title is prominent but remains readable, and it does not push either recovery action out of the supplied frame.

**Limit:** the destination is asserted rather than named. There is no executed retry, account-state readback or demonstration that the original destination is retained. This is an account-service state, so it does **not** fill the separate analytical read-failure or known-route-load-failure gaps.

**Disposition:** `ADDITIONAL_RETAINED_EVIDENCE` for the account-unavailable composition; real owner input, content visibility and retry behavior remain `OPEN_NATIVE/OWNER_QUALIFICATION`.

### VF-08-D — Unknown route on a 320 px phone

**Evidence:** `evidence/before/Unknown-route-phone-6OQP-0.jpg` and `.jsx`, 320 × 844, Chinese light. Nodes `6ORD-0`/`6ORE-0` provide the heading and explanation; `6ORI-0`/`6ORK-0` provide Today and tools actions; `6ORQ-0` is the company-search link.

The Chinese headline and two-line explanation are readable at 320 px. The page presents Today as an **explicit user choice**, offers the full tools directory as a secondary action, and provides a separate company-name/ticker search recovery card. There is no visible attempt to invent a replacement route or conceal the missing page behind a success screen. The CJK text and action labels are not visibly clipped.

This adds an actual narrow-screen unknown-destination treatment with three understandable recovery paths. It supports the distinction between an unknown route and a known route that temporarily fails to load.

**Limit:** no route resolver was executed, and the capture cannot establish that each recovery control opens its real target or handles malicious/malformed inputs. It is not a specimen of the **known-route-unavailable** state; that separate case still needs its retry/original-page treatment bound into the reviewed evidence.

**Disposition:** `ADDITIONAL_RETAINED_EVIDENCE` for the unknown-route composition and Chinese 320 px text wrapping; resolution and navigation behavior remain `OPEN_NATIVE/OWNER_QUALIFICATION`.

### VF-08-E — Guest presentation preferences on a tablet

**Evidence:** `evidence/before/Guest-tablet-6OS6-0.jpg` and `.jsx`, 768 × 1024, Chinese light. Nodes `6OT9-0` and descendants form the presentation panel; `6OUM-0`/`6OUN-0` specify guest/current-browser scope; `6OU8-0` and `6OUI-0` visibly select light and Simplified Chinese; `6OUP-0` is Done.

The underlying public market context remains visible. The open presentation panel groups appearance and interface language, includes an Auto/system choice, and uses both a blue fill and a check mark for selected options. **“访客 · 当前浏览器”** makes the guest/browser scope explicit. The explanatory text says the choices are saved in this browser and that interface language does not change market, currency or the language of original material. The adjacent market copy separately describes regional navigation and preservation of watchlist/holding identity.

This adds a concrete guest **presentation-context** reference. The Chinese copy is readable and the panel fits without overlapping the main left-hand metric. It helps distinguish visual preferences from account ownership and market/entity identity.

**Limit:** a public guest preference panel is **not** the same as a signed-out gate for a requested private destination. The visible login entry does not demonstrate safe sign-in return or preservation of an in-progress draft. Browser persistence, preference-owner behavior, selection changes, modal/nonmodal semantics and focus handling were not exercised. Its 5/11 illustrative metric belongs to this retained specimen; it is not a new observation to compare with the current candidate's Macro values.

**Disposition:** `ADDITIONAL_RETAINED_EVIDENCE` for guest presentation scope; authenticated-state transition and actual preference behavior remain `OPEN_NATIVE/OWNER_QUALIFICATION`.

## Visual and responsive evidence added across the set

The five captures use clear heading/body/action hierarchy, comfortable separation of recovery choices, and distinct messages for different failure classes. The uncertain-save warning is placed before the recovery action, rather than relegated to a footer. Across the supplied 390 × 844 and 320 × 844 phone frames, the visible primary actions, secondary actions and qualifying copy fit without obvious clipping. The two Chinese specimens have legible CJK text and natural line wrapping.

The JSX supports the generous anatomy seen in the main recovery controls. The English phone primary controls are approximately **46 px** high from 14 px vertical padding plus an 18 px line; their bordered secondary controls are approximately **48 px**. The unknown-route controls are approximately **48/50 px**. Guest appearance/language choices are approximately **44–46 px**, and Done is approximately **44 px**. These are useful native composition measurements, not browser hit-region or accessibility results.

Some smaller affordances remain under-specified: the phone headers use bare 22 px menu/search SVGs; guest Close is a short text node (`6OTD-0`) with no explicit larger target; the account-settings and company-search text links have no separate target anatomy. The main recovery actions are therefore better substantiated than every auxiliary action. This supplement does not convert those exports into a runtime WCAG pass or failure.

The boards also use retained `mx-*` styling and their original compositions. Their existence does not establish that the current F01/F02 candidate has integrated the same states, typography, target treatment or overlay behavior. Preservation can reuse these designs where appropriate; it should not require duplicating them solely to obtain a newer timestamp.

## Remaining VA-08 conditions and falsifiable closure

| Condition | Advisory severity / status | Evidence and user consequence | Closure needed |
| --- | --- | --- | --- |
| **VF-08-01: I and the original effect remain unresolved** | High — `OPEN_NATIVE/OWNER_QUALIFICATION`, held | The repair packet says F01 native images are unchanged. These five predecessors are not evidence of a repaired eight-row I or a resolved operation. Treating them as such would misstate the artifact/effect history. | Reconcile the original `F01-20261103-c4-state-8-v1` operation on its original carrier through the existing owner. Bind the resulting known state to the review record. Do not replay or substitute a new operation to bypass uncertainty. |
| **VF-08-02: State coverage remains incomplete** | High — `OPEN_NATIVE/OWNER_QUALIFICATION` | The set adds uncertain save with expiry, denial, account unavailability, unknown route and guest presentation. It does not supply pending save, known-failed save, owner-confirmed saved, loading, retained-content analytical read failure, or known-route-load-failure compositions. Guest private-destination gating is only partially represented. Users still need distinguishable feedback and safe next actions for these cases. | Bind and visually inspect relevant existing retained compositions where available; add only genuinely missing native evidence once authorized and effect reconciliation permits. Show the affected object/context and distinguish read retry from write reconciliation. Preserve exact existing owners. |
| **VF-08-03: Owner inputs and transitions remain unexecuted** | Medium — `OPEN_NATIVE/OWNER_QUALIFICATION` | Text claims exact return, access verification, private-content hiding, browser preference scope and no automatic save. No action was executed. Misbinding these states could cause incorrect access messaging or unsafe retry behavior despite good static copy. | Later exercise owner-confirmed fixtures or real authorized inputs through sign-in/return, access recheck, account-read retry and D23 reconciliation, with exact object/request/route identity. Observe the output and return context; do not equate a screenshot with that test. |
| **VF-08-04: Responsive/accessibility proof is limited to these static sizes** | Medium — `OPEN_NATIVE/OWNER_QUALIFICATION` | Supplied frames are readable, but shorter heights, enlarged text, virtual keyboard, actual focus, small auxiliary targets and current-candidate state integration are untested. | Qualify the existing components at the relevant narrow/short viewport and text-enlargement conditions; demonstrate auxiliary target anatomy, keyboard names/order, focus return and appropriate overlay coordination. Re-capture only materially affected compositions. |

## Preservation and final disposition

The initial VA-08 statement that these retained state pixels were not in the first inspected predecessor set remains historically accurate. At freeze B, that **specific evidence-access limitation has been reduced by five actually inspected pairs**. The record should say so plainly while retaining the original finding, its severity and the open conditions above.

No `SOURCE_ONLY_RESOLVED` determination is made by this visual follow-up. No native repair, effect reconciliation, completed recovery journey, implementation result or formal acceptance is claimed. The candidate remains PARTIAL / RIG draft. All original VA findings are preserved; the recommendation to use A as the preferred direction is unchanged and was not re-adjudicated in this narrow state-evidence commission.

I made no Paper, GitHub, account or reviewed-input changes, sent no external messages and started no agents. The only file authored in this follow-up is `VISUAL_FOLLOWUP.md`. This completes the bounded additional-evidence advisory; it establishes no continuing watcher or background work.
