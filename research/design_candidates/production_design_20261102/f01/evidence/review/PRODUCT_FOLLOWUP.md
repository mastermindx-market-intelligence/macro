# F01 product advisory follow-up — candidate.3 / freeze B

## Disposition

**The candidate.3 source changes sufficiently address the source-level omissions in PA-01–PA-07 as a design proposal and acceptance specification. Every original native finding remains open.** PA-06 now has an explicit proposed policy, but its D06 lifecycle binding and F02 qualification remain substantive dependencies; a written transition table does not make that integration available.

Use **SOURCE_ONLY_RESOLVED** for the repaired clauses and acceptance obligations described below. Continue to use **OPEN_NATIVE / OWNER_QUALIFICATION** for the corresponding unchanged artifacts and outstanding owner proof. Do not convert either classification into a formal approval or a passing runtime result. The overall candidate remains **PARTIAL / RIG draft**, with the initial request-changes recommendation still applicable to native qualification and implementation entry.

This is a new, bounded read-only follow-up by native advisory agent `/root/f01_product_advisory`. It is not an independently admitted formal reviewer-class receipt, Opus review, GitHub approval, RIG acceptance, QA01 disposition, or retry of a denied or uncertain review. The initial product report remains unchanged.

## 1. Input identity and verification

| Binding | Exact identity |
| --- | --- |
| Follow-up packet | `F01-20261103-candidate3-freezeB` |
| Published source | Macro `b55efe221d16ae5e64935af4c60572701b2a43a0`, `research/design_candidates/production_design_20261102/f01/` |
| Publication provenance | The coordinating F01 receiver supplied this immutable identity during the review and reported matching the publication's file blobs. This advisory did not fetch GitHub or extend the source set through external tools. |
| Repair manifest SHA-256 | `b339ffef698f307bc9bebdd54a7e46f4712e6b5cdb1438cb520ffe290258ecd8` |
| Repair manifest Git blob | `935ef948bfe7f86522b29d4a42cf4af8a81c2277` |
| Repair-packet SHA-256 | `43077b9317a63d3fb9099ec805a7a638971868c5bb8b1ed3abd5136e180dab8e` |
| Manifest freeze time | `2026-11-03T07:41:00.957213+00:00` |
| Parent candidate.2 publication | `245a7d2cd62d88fb6d2ee3863f9d26c63052d8e7` |
| Original manifest SHA-256 | `75ad7f14503145e9550f27346eab59ced8cce7e0ad6962e2c999a8c5ae8ae6ab` |
| Original product-report SHA-256 | `86d8f75f4af2473a0668f6627108d680d867928108db535ab7b1595eebcebf39` |
| Additional Terminal source pin | `3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9` |

The reviewer independently recomputed the repair manifest hash and verified byte lengths, SHA-256 hashes, and Git blob hashes for **55 of its 57 listed files**. The peer `VISUAL_ADVISORY.md` and combined `ADJUDICATION.md` were excluded entirely, including from byte reads, to avoid using the peer review as evidence. All checked files matched. The two excluded files were not needed to assess the product source repairs.

All **nine additional upstream source copies** in `/workspace/scratch/43a778472c23/f01-context/` matched the manifest's expected Git blob, SHA-256, and byte-length records. Their relevant code was inspected: `OptionsHubView.tsx`, `optionsCsv.ts`, `optionsTapeView.ts`, `flowStream.ts`, the two Flow API route files, `AnalysisBrainHost.tsx`, `mastermindBrain.ts`, and `BrainWidget.tsx`. The primary product review covered the repaired product specification, source/data contract, acceptance cases, joint version/concurrence clauses, and the retention ledger's candidate.3 response.

**Explicit supplemental input:** after the reviewer identified the missing AppShell byte binding, the coordinating receiver separately admitted only `terminal/components/chrome/AppShell.tsx` at the same Terminal pin. Its receipt is `evidence/source/APPSHELL_REVIEW_SUPPLEMENT.json`, SHA-256 `e9ca268e4b7a93e8469d165df464a39bf80ddb1b0f9c9f2ddbbb4f2852a56d7d`. The reviewer verified the local source as 15,722 bytes, SHA-256 `7054ce108b9701b29c8d608bc102f775858cb232b4289032d2afac66338cee43`, Git blob `fad76e11e24f02510854768878ef7ce7e0a063bf`. This is a separately identified supplement, not a silently expanded freeze-B manifest or a claim that it was already included in the nine-copy set. Inspection was limited to corroborating the existing compact toggle/state.

The **20 original F01 image/JSX files** match both the initial and follow-up manifests. Thus all ten current native boards are unchanged. This follow-up relies on the prior actual image inspection plus those unchanged identities; it does not claim to have observed repaired pixels. The initial product report at the assigned output path also retains its original hash.

Independent static inspection confirmed **11 Tape header columns, 30 Tape CSV columns, and 79 distinct acceptance-case IDs**. These are text/artifact checks, not product test executions or acceptance results.

## 2. Finding-by-finding source disposition

| Original finding | Source disposition and evidence | What remains open |
| --- | --- | --- |
| **PA-01 — current-page oracle and Today cue** | **SOURCE_ONLY_RESOLVED.** N01 now requires at most one correctly mapped primary current item and explicitly permits zero when no qualified mapping exists. N12 adds mapped Company, market, and unmapped specialist cases, explicitly requiring inactive Today treatment. This agrees with `PRODUCT_UX_SPEC.md` §3. | **OPEN_NATIVE / OWNER_QUALIFICATION.** The inherited Today emphasis in A/C/H is unchanged. F03 still has to qualify the actual route-family presentation mapping. No `aria-current` or route transition was executed. |
| **PA-02 — compact-mode entry and exit** | **SOURCE_ONLY_RESOLVED as an explicit interaction specification.** Product §2 now locates a separate brand-area control, supplies EN/ZH names, keyboard action, `aria-pressed`/`aria-controls`, focus behavior, and the 44px target. Its scope is mounted-instance React state, initially expanded, with no new persistence key or account preference. N09 exercises choosing compact, evidence, the narrow breakpoint, and expanding again. The separately admitted AppShell source corroborates the existing state/control owner. | **OPEN_NATIVE.** A/H still omit the control and tooltip/focus specimens. Its final placement must fit the actual compact composition. The proposed copy, 44px anatomy, resize/focus behavior and actual preservation across mount boundaries remain unexecuted; the source read does not certify them. |
| **PA-03 — unsupported complete 12-field Tape claim** | **SOURCE_ONLY_RESOLVED.** Product §8 and source/data §3.2 replace the unsupported count with the actual eleven-column table and separate thirty-column export. They retain row drill, flags, source meanings, sorting, filters, and complete export population; they explicitly reject mapping the mockup's bid/ask/venue/At ask values onto unsupported source fields. O07–O09 make these requirements falsifiable. The code checks supporting this disposition are in §3. | **OPEN_NATIVE / OWNER_QUALIFICATION.** D still has the abbreviated table, twelve-field/complete-row claim, unsupported evidence vocabulary, and old 400px overlay. D08 must qualify the complete table/detail composition and source meanings. No actual payload, API response, export, narrow table, or row action was exercised. |
| **PA-04 — retained product depth not concretely covered** | **SOURCE_ONLY_RESOLVED for the missing coverage obligations.** CF01 explicitly covers all five Financials subviews and available statement types at 664px and phone widths. CF02 covers annual/quarterly and earlier/later history without a four-period cap. CF03 covers transcripts, Saved research, Your theses, and return to the selected context. O01/O05/O06 remain the exact Options hierarchy cases, and V01 requires actual corrected compositions. | **OPEN_NATIVE / OWNER_QUALIFICATION.** C/D/E remain incomplete demonstrations of retained local depth. D07/D08 still own the exact controls, route grammar, data and absence states. These new cases specify what to prove; they neither establish reachability nor redesign the domain pages. |
| **PA-05 — ambiguous Company evidence period** | **SOURCE_ONLY_RESOLVED at the identity and acceptance-obligation level.** CF04 now requires FY2024 → FY2025 evidence replacement, agreement of selected period, subject-named trigger, value and unit, preservation of window/scroll, and stable field-key focus restoration with a true-removal fallback. Product §6 retains the field/period requirement. | **OPEN_NATIVE / OWNER_QUALIFICATION.** C's generic row Info control and absent visible FY2024 selection are unchanged. D07/F01 must still choose and depict the concrete period-selection mechanism. No field lookup, rerender, sorting, close or focus restoration ran. |
| **PA-06 — Brain/evidence coordination** | **SOURCE_ONLY_RESOLVED as a proposed policy, not as an available integration.** Product §6 now defines replacement/suspension/coexistence rules, avoids simultaneous Brain/evidence docks, protects pending account operations, preserves transient domain selection, and requires explicit evidence reopening. It rejects a second host, new storage, fabricated close method/event, or polling private state. N10/N11 specify the cross-layer cases. The joint contract expressly marks candidate.3 behavior pending F02/D06 review. | **OPEN_NATIVE / OWNER_QUALIFICATION.** D06 must bind actual open/close/focus signals before these cases can be implemented or accepted. The typed bridge does not supply the required lifecycle acknowledgement. There is no runtime coordination or visual proof. See §4 for the exact limitation. |
| **PA-07 — generic versus current-company chart entry** | **SOURCE_ONLY_RESOLVED.** Product §7 now supplies an explicit context/action table: a valid qualified symbol is named; a view without intended company context says Open Terminal; invalid identity suppresses the contextual action; unavailable service preserves research context. N13 covers toolbar/mobile/directory combinations with valid URL symbol, stale cursor, absent company context and invalid identity. | **OPEN_NATIVE / OWNER_QUALIFICATION.** A/H/D still say Open chart without the new distinction. Actual href/return behavior and entry-path parity remain unexecuted. A05/A06 and H01–H03 remain required later. |

These dispositions do not erase the original findings. They identify the repaired portion of each finding and preserve the unfinished portion. In particular, an acceptance case can resolve a missing test specification while the behavior it describes remains completely unproven.

## 3. Direct source corroboration for the Tape repair

### Actual table and export are different contracts

`OptionsHubView.tsx` at Git blob `0d932ec2561314d44c6d0a0c7bfb00cf237f60cb` defines `tapeThead` with the following eleven columns in order:

1. Time ET
2. Ticker
3. Sector
4. Side
5. C/P
6. Contract
7. DTE
8. Mny
9. Size
10. Prem
11. Flags

The corresponding rendered row uses those eleven cells. It keys the row by `e.id` and retains the existing root-drill action on row click. Time and premium have their existing sort actions. The source comments identify positional narrow-width selectors as a dependency; the repaired source therefore correctly requires D08 qualification rather than casually reordering columns or replacing one with an evidence action. The narrow CSS itself was not exercised in this review.

The table initially uses a 150-row render limit, extended by its sentinel. Its CSV callback passes the full memoized filtered/sorted `events` collection, rather than `tapeRows`, to `buildOptionsTapeCsv`. In `optionsCsv.ts`, Git blob `de778fb67e6b9e7627ad3a90d3b012c10db7b2e6`, `OPTIONS_TAPE_CSV_COLUMNS` contains thirty fields. They include export/authority/direction metadata, feed/session/as-of/stale metadata, and the source event fields. The serializer retains `display_only` and `tilde_inferred`, preserves absent optional values as blank, and separates numeric serialization from string formula hardening.

This supports the source repair's distinction between a visible table contract, rendered row window, and complete filtered export. It does not prove a browser download, current deployed behavior, or complete dataset freshness.

### Unsupported mockup fields are now explicitly excluded

The inspected `FlowEvent` type contains `side: "~buy" | "~sell" | "mixed"`, plus `avg_price`, supplied `premium`, nullable `premium_z`/`vol_gt_oi`, and optional `swept`. It has no `bid`, `ask`, or `exchange` field. `FlowEvent.id` is a row identity, not a vendor citation. The source repair correctly declines to infer an exchange from ET, convert inferred side into At ask, manufacture quotes, or reverse-engineer a multiplier from D's example numbers. Those were unsupported native examples; they are not a field contract to preserve.

O08 accurately requires the actual inference vocabulary and absence semantics. O07 protects the full columns and export population. D still needs native correction to those actual meanings, and a summary inspector must state its scope rather than claim an unspecified complete record.

### Filter, transport, and access owners remain intact

`optionsTapeView.ts` defines ten state keys plus version `v`, a 2048-character limit, strict key/version/whitelist validation, and filter-only semantics. `OptionsHubView.tsx` independently handles repeated `tapeView` query values and withholds the Tape behind the invalid-view recovery state. The repaired O09 correctly distinguishes that state from a historical snapshot or saved payload and leaves existing local query reserialization visible as a separate qualification issue.

`flowStream.ts` keeps one per-key connection, a default 30-second fallback interval, and distinct loading/data/absent/unavailable outcomes. Its `connected` flag describes transport, and a failed read can retain an earlier payload. The repaired source does not claim that every hook outcome is already rendered by the Hub. The inspected API route sections retain feed validation, real entitlement checks, denied/unavailable distinctions, no-store responses, and the existing fixture branch. No endpoint, grant, fixture configuration, request, or production logging was created or exercised.

## 4. Brain policy: clarified, with the real lifecycle gap preserved

The repaired policy makes the intended product behavior reviewable: opening Brain suspends evidence presentation rather than adding another dock; evidence identity stays in the current domain view; closing Brain makes an explicit evidence return available; another modal cannot discard an account owner's pending work. This addresses the original missing policy without assigning F01 a new data or assistant owner. It also keeps focused `/terminal` under its existing owner.

The direct source copies substantiate the integration hold:

- `mastermindBrain.ts`, blob `8bad1568a715d3603331db492eced30fe33f98de`, types `MMBrain.open`, `mounted`, and `setPrincipal`. It does not type a close function or an observable open-state/close acknowledgement. Calling `open()` and returning a boolean from its helper is not evidence that a dialog became visible, acquired focus, or later closed.
- `AnalysisBrainHost.tsx`, blob `56ac30f1cb3a66024bd84a866d7d09f977ddc2e2`, retains one ambient-context provider, the existing opener event path, and cleanup of its listeners/owner state. It does not establish the missing external lifecycle signal.
- `BrainWidget.tsx`, blob `5bf6fb83c02222e0c1682890c982beb91c515536`, loads the external `mm_brain.js` once per document and deliberately preserves that singleton across component lifetime changes. Its comment naming additional methods does not qualify a close acknowledgement, external launcher behavior, focus ownership, or current script behavior. The script itself was not fetched or run.

**Required owner proof remains:** bind actual opening, opening failure, close, and focus-return behavior through D06's existing owner, including every real entry path; then qualify the proposed cross-layer transitions with F02. Preserve conversation/request state and actual source-attachment ownership. A static `mounted` marker, an attempted open, or a comment about `close` must not be promoted into that proof. No new event name, private-state polling, replacement Brain host, or teardown workaround is justified by this review.

## 5. Remaining native, owner, and evidence limits

### Native findings and original holds

All original native findings remain open because the relevant captures are byte-identical: A/C/H current treatment; A/H compact controls and labels; D's actual table/depth/evidence semantics and overlay width; C/D/E retained local navigation; C's field-period selection; A/H/D chart-entry wording; and the missing cross-layer states. V01 correctly makes new captures an explicit obligation rather than treating prose as the repair.

The original uncertain operation **`F01-20261103-c4-state-8-v1`**, target `711X-0` in I `710Z-0`, remains **EFFECT_UNKNOWN**. I's eight rows and the later undispatched rows do not establish the original operation's terminal effect. No replay, new key, or alternate carrier is justified. The Read me metadata discrepancy and its `DOCUMENT_CHANGED` / `retry_allowed:false` outcome also remain held. D still depicts 400px while the source retains 440px. F02's own unresolved native effect, previous findings, final native identities, and formal qualification remain separate gates.

### Owner qualification and concurrence

The joint contract correctly versions the new behavior as candidate.3 while preserving candidate.2's unchanged geometry/token concurrence. It does not claim that F02's earlier handshake reviewed or accepted these additions. D06 lifecycle qualification and F02 review remain explicitly pending. F03 mapping/admission, D07 Company parsing/composition/history, D08 Options semantics, D23 saved-state authority, and the focused/public/internal composition boundaries remain unchanged.

### Evidence credited by this follow-up

**SOURCE_ONLY_RESOLVED** applies as described in §2. **ADDITIONAL_RETAINED_EVIDENCE** receives no product-closure credit in this source-only follow-up: the manifest includes five further retained state image/JSX pairs, but their visual assessment belongs to the separately scoped review. Their file identities were checked; their pixels were not reinterpreted here, and the peer visual report was not read. They cannot repair I or resolve the original Paper effect.

The separately admitted AppShell supplement corroborates the compact-state boundary directly. It declares `const [compactNavigation, setCompactNavigation] = useState(false)`; the brand-area button has `data-investor-compact-toggle`, state-bound `aria-pressed`, the existing primary-navigation `aria-controls`, and a click handler that toggles that state. The same state drives the shared-shell data attribute and whether AppNav is labelled. This supports mounted-instance state and the existing toggle owner, without establishing account synchronization or reload persistence. The new EN/ZH action names, target size, narrow-boundary focus behavior and final placement are still proposed design obligations requiring actual native/runtime qualification.

All 79 acceptance cases remain **NOT_RUN**. No source inspection proves actual modal focus, screen-reader naming, 320px/zoom reflow, correct live data, all route/history behavior, full Company → Terminal → return, or cross-product state retention. The nine manifest-bound source-copy hashes and the separately admitted AppShell supplement match the supplied expected blobs; this advisory did not independently retrieve those blobs from the upstream service or attest the beta serving revision.

## 6. Next bounded action

Record the source-only dispositions alongside the unchanged original findings on the existing F01 carrier. Obtain F02 review of the candidate.3 clauses and D06's actual lifecycle binding; keep native repairs paused until the original Paper effect is reconciled by its owner. Then repair and capture the affected native compositions and execute the relevant acceptance cases only in an authorized implementation/qualification phase bound to a real source/build.

This follow-up creates no permission to modify Paper, implement, merge, change Ready state, enqueue, relabel, deploy, or claim programme acceptance. Its only authored output is this separate report; the initial advisory and all reviewed inputs remain unchanged.
