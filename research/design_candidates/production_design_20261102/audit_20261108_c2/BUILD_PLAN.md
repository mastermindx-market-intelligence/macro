# Build plan — Paper audit improvements
2026-11-08 · Supplement to WS:MARKET-OS and the existing F01/F02/F03 + product-family assignments
This is an implementation plan. It creates no new runtime owner, publication authority or parallel workstream.

## Product direction
Users should recognize the subject, the current read and the next useful action within one glance. Keep a useful chart or rich card when it answers the question. Move mechanics and historical evidence into the existing inspection layer. Preserve limitations that materially change interpretation beside the claim.

The estate needs coherent interaction rules across distinct products:
- **Investor workspace:** orient → discover → investigate → inspect evidence → preserve a case → monitor deliberately.
- **Executive workspace:** ask → track work → resolve a decision → inspect operational evidence.
- **Guide:** explain a concept → return to the exact place that prompted the question.
These workflows can share presentation primitives without sharing one authority model.

## Existing architecture to extend

| Concern | Existing owner | Integration rule |
|---|---|---|
| Investor shell, persistent navigation | Terminal Next App Router AppShell and existing identity, settings and onboarding providers | Extend the current shell. Do not mount a second navigation drawer or identity provider. Preserve chart-specific layout. |
| Product discovery / route inventory | Macro page registry, `scripts/build_product_page_registry.py`, existing overrides and protected export | Derived navigation only. Carry source revision and registry identity. Do not hand-maintain another route database. |
| Legacy Macro content | Existing fixed-origin Shared Shell host/bridge | Preserve route identity, theme/locale, original useful pages, safe navigation and return context. |
| AI response / streaming | Existing Brain gateway, stream, renderer and thread owners | Add admitted typed events/artifacts at existing seams. Do not build another agent runner, renderer, retry store or quota plane. |
| Historical context | Existing assistant-message metadata and existing authorized readers | Consume retained context-resolution receipts under current rights. Do not reconstruct missing historical evidence or claim “used inputs” from offered context. |
| Saved case / monitoring | Existing thesis/version and alert/monitor owners | Save and activate are separate effects. Preserve the documented non-monitoring Save hold until the current head qualifies it. |
| Display illustrations | `lib/illus.py`, paired `templates/site illus.css/js` | Reuse SSR figures and their reveal owner. Native Terminal owns trading-chart interaction. |
| International capability / rights | Existing Global Surveillance workstream, display/mount and data owners | Actual admission and rights determine availability; a complete design specimen does not enable a feature. |
| Theme and common behavior | Binding design system, source theme tokens and existing components | Share focus, sizing, drawer, source-clock and accessibility behavior. No token fork or colored container-edge accents. |

The [existing production plan](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/research/market_os/SHARED_SHELL_WEBAPP_PRODUCTION_PLAN_2026-10-18.md) owns shell topology and route provenance. Macro10639's producer has merged; Terminal1244 remains the existing consumer integration surface, with its own proof and publication constraints.

## Feature viability and delivery matrix
“Proposed” below means a design/build recommendation, not an implemented capability or an authorized release.

| User action | Current evidence / capability | Design change or proposal | Proof and release condition |
|---|---|---|---|
| Find the right design | F03 27-family directory exists; main Paper file reports capacity risk | Preserve directory; use existing assignment links. Recover file capacity before reorganizing that file. | Verified preservation/restoration path, exact page/node/link inventory, no lost history. |
| Start at Intelligence Hub | Product directory shared its page with three adapter QA boards | **Applied:** relocate canaries to retained QA page, keeping IDs and product directory. | Readback complete; new page-qualified QA destination recorded. |
| Understand Risk Radar | Eight teaching variants distinguish index, odds and evidence | **Applied:** concise EN/ZH introduction and neutral advisory emphasis. | All eight copy/meaning checks complete; inspected EN desktop and ZH dark mobile wrap correctly. |
| Ask a question and read its answer | Strong Paper conversation hierarchy and existing chat page | Preserve one reading column, useful rich answer, optional Sources/Context layer | Real answer, keyboard-safe composer, explicit context, no unsolicited research or provider call on disclosure. |
| Inspect context resolution | Server receipt exists; inspected chat page lacks its event handler | Bind the response receipt to its answer under Context details | Exact request/answer binding; old receipt cannot attach to newer answer; no source-access grant; draft/focus preserved. |
| Reopen historical context | G6 retains context-resolution metadata; documented readers omit it | Extend existing authorized history reader and host presentation | Current rights check; unavailable/malformed/oversized/old receipt states; no regeneration on open; actual used inputs remain separately evidenced. |
| Save without monitoring | Existing Paper hold based on earlier thesis/version path | Keep the hold; requalify exact build head and extend incumbent owner if needed | Canonical saved-case ID/version/receipt and readback with monitoring off. No active-then-archive workaround. |
| Activate monitoring | Separate R2 review and explicit activation are specified | Keep universe, metric, schedule/time zone, destination, expiry, fresh-crossing and stale behavior in review | Entitlement/coverage, explicit confirmation and canonical activation receipt. Unknown outcome reconciles original request. |
| Increase research depth | Existing depth review and admission owners | Review first; selection itself causes no run | Quote/estimate or unknown from service; only confirmed Start invokes existing lifecycle; Cancel preserves context/draft. |
| Inspect a company from Prophet | Rich opportunity cards and native company brief already exist | Preserve rich cards, separate signal/quote clocks; use existing scoped handoff | Correct symbol/event/scope, existing chart acknowledgment, useful failure state and return to prior view. |
| Refine a comparison | Ontology has scoped refine drawer with preview count | Keep market/theme/period stable; apply on explicit confirmation | No-match recovery, stable sorting/benchmark, current permissions and no loss of prior comparison on Cancel. |
| Read International scanner | Public scanner is available; several analyses unavailable; some tabs disabled | Preserve capability distinctions and frozen R14 meaning; **propose** progressive disclosure for density | Existing freeze amendment and per-market capability/rights proof; no enabled-looking affordance without backend support. |
| Follow an analytical diagram | Current relationships and typed-artifact proposal | **Applied contract:** named channel/evidence state; selected path, not a graph hairball | Existing host admits typed artifact; no correlation-only causal edge; exact value/source/absence support. |
| Recalculate a scenario | Existing scenario editor/lifecycle must remain owner | **Applied contract:** explicit changed assumptions, confirm, then replace validated revision | Unit/denominator checks, null preserved, old saved revision immutable, visual/table/prose agree, cancellation race handled. |
| Read animated display data | Existing ilx supports deterministic display reveal | **Applied storyboard:** draw once, missing gap, stable final state; retain current timing owner | Actual consuming route, reduced motion, no duplicate observer/reveal, no fake liveness or fabricated series. |
| Get contextual help | Guide already separates compact help and full teaching | Open relevant explanation and return to invoking context | URL/filter/selection/scroll/focus preserved; help does not reset or submit the parent workflow. |

## Sequence 1 — close the AI consumer gap
**Input:** inspected `site/chat.html`, `docs/BRAIN_RETAINED_CONTEXT.md`, existing Brain/thread contracts, Paper `1MO-0` and updated `5M0-0`.

1. Identify the exact response/stream event seam and answer identity in the existing host. Extend that seam for the retained response receipt; do not fork the stream parser.
2. Keep Context details separate from source support. The context receipt describes effective context, precedence, exclusions and limitations; it does not prove evidence use. Preserve exact value, calculation, document-span and absence families as separate support.
3. Extend the existing reader to expose permitted retained metadata. Keep current source/derived-rights checks on opening, copying and exporting. The retained record's presence alone is not an access grant or a new durable-write acknowledgment.
4. Render specific absence states for historical messages without metadata, malformed/oversized receipt, denied source or unrecorded used inputs. Do not infer absence of the conversation itself.
5. Prove response → persisted assistant row → authorized reopen using the actual consumer. Verify request separation, same-context different requests, answer association, cold history and no generation on open.
6. Requalify the independent Save/monitoring-off dependency. Context-reader completion does not unblock it automatically.

**Failure behavior:** retain lawful answer content; show the receipt's unavailable reason without losing the draft or switching scope. If an obsolete stream event arrives after a new answer, it must not replace that answer's receipt.

**Done when:** the real signed-in route opens the exact allowed retained context for the selected answer; denial/absence stay truthful; current source and consumer evidence agree. Producer tests or static screenshots alone do not close this.

## Sequence 2 — clarify save and monitoring effects
These are presentation states over the existing persistence and monitoring owners, not new backend enum names.

| Visible state | Invariant | Next action |
|---|---|---|
| Review save | Original answer/draft remain intact | Confirm or Cancel |
| Saving | One existing owned request is in progress | Wait or use existing reconciliation route |
| Saved | Matching user, case, revision and canonical receipt verified | Reopen that saved revision |
| Save failed | No successful saved effect is claimed | Owner-qualified correction/retry |
| Save outcome unknown | An interrupted request may have executed | Look up the original request; no duplicate save |
| Monitoring off | A saved case can be read without activation, only after this capability is qualified | Review a monitoring condition separately |
| Review monitoring | Schedule, time zone, freshness, coverage, delivery and expiry are visible | Explicit confirmation |
| Monitoring active | Canonical activation receipt and current owner state agree | View/manage through incumbent owner |

Do not combine Save and Enable into one ambiguous action. Do not treat a Paper badge, transport acknowledgment or successful animation as a saved or active effect. Preserve old versions when evidence refreshes; show what changed before accepting a new revision.

## Sequence 3 — reduce reading burden while preserving meaning
Use the current family lane and source owner for each change.

### International amendment candidate
Keep the six investigative questions, four clocks, basis/horizon identity, rights tiers and written R14 amendments. Propose a view where:
- the top level presents the current qualified read, the selected basis/horizon, one material limitation and the primary investigation action;
- the six questions remain navigable and retain their exact meaning;
- detailed clock definitions, repeated rights explanations and method text open in the existing evidence/coverage layer;
- unavailable analytic stages remain discoverable with a precise reason and no apparent activation;
- saved intent and actively running watches have distinct state labels.

Do not modify frozen R14 to implement this proposal without the existing amendment process. The current public sample's 7/6/1/57 counts are observations, not the future contract or a new entitlement rule.

### Prophet / Intelligence Hub
Keep rich cards where they carry setup context, useful price illustration, risk evidence and a next action. Separate research priority from readiness and signal time from quote time. On compact widths, expose a focused initial set with deliberate “view all” or section entry; preserve search/filter recovery and the original list order/selection on return.
Keep negative track record and unavailable evidence inspectable. Rename or clarify metrics only with the producing owner's definition; never turn an opportunity index or “room left” percentage into expected return or probability.

### Guide / Risk
Use compact help at the point of confusion; reserve teaching detail for the Guide. Keep index points, probability, event, horizon, baseline, calibration and coverage distinct. Do not collapse these into one confidence score. The current eight-variant Guide patch is the completed narrow presentation repair, not a model change.

### Shared shell / OS
Use the canonical registry for routes and the existing shell's navigation composition. Keep the executive operational hierarchy distinct. Preserve historical or original tool entry points that still own useful functionality; consolidation requires a named destination and return path, not just deleting a link.

## Sequence 4 — implement purposeful motion
Use [MOTION_AND_ARTIFACT_CONTRACT.md](MOTION_AND_ARTIFACT_CONTRACT.md) and Paper `9T-0 / A9R-0`.

1. Select one real consumer and bind the exact artifact/data owner.
2. Verify units, period, missing slots, zero and revisions before rendering.
3. Reuse ilx for display charts. Selected-mark inspection is an admitted host-artifact feature, not an ilx tooltip or a second chart engine.
4. Use existing UI duration/easing tokens for new host state transitions. The inherited ilx timings remain with their owner; any migration is a scoped renderer change with paired CSS/JS consumers.
5. Cancel obsolete transitions on revised/withdrawn evidence. Animation ending never establishes analytical completion.
6. Prove final-state equivalence under reduced motion, keyboard/touch access, exact table parity and focus return.

**Illustration policy:** use original decorative artwork for onboarding, empty states or research covers; it carries no analytical meaning. Use deterministic native graphics for values, mechanisms, relationships and evidence. A decorative image failure must not break the useful answer.

## Sequence 5 — safe consolidation and file capacity
The MASTERMIND PAGES warning is a concrete preservation risk. Do not trim it by speculative deletion or move its contents to a new file as a workaround. The owner needs:
1. A supported, verified preservation/restoration mechanism.
2. An inventory mapping original file/page/node identity and deep links to any proposed destination.
3. A sample restore/readback proving text, geometry, tokens, assets, history and references survive.
4. A bounded move/archival plan with named destinations and a recovery point.
5. A post-operation source and visual comparison before the next batch.

Independent work in healthy product files can continue while that recovery is being resolved. The already completed Hub QA relocation demonstrates the small, reversible organizational pattern; it does not qualify migration of the oversized main file.

## Verification matrix for real consumers
Run only the checks affected by each implementation. Reuse existing CI and consumer evidence rather than adding a duplicate test plane.

| Dimension | Required observation |
|---|---|
| First-use clarity | User identifies subject, current read and next action without reading method text |
| Keyboard / touch | Visible focus, correct dialog semantics, 44px target, no hover-only access |
| Return path | Original route/filter/selection/draft/caret/scroll restored after inspection or Cancel |
| Responsive / locale | 320, 390, tablet, desktop; long EN/ZH; 200% text; no page-level horizontal overflow |
| Theme / contrast | Existing theme tokens; semantic color retains labels; no forbidden colored edge accents |
| Data truth | Null, zero, unavailable, stale, partial, conflicting and denied remain distinct |
| Revision integrity | Prose, chart, table, receipt, unit, denominator and period match the same artifact |
| Effect truth | Save/activation success only after matching owner receipt and readback |
| Motion | Honest trigger; stable final state; obsolete revision interrupted; reduced motion preserves meaning |
| Deployment | Correct serving commit and authenticated consumer path where required; old-head CI is not acceptance |

## Constraints and delivery
- Preserve International R14 freeze, F01/F02/F03 review targets and all actual GitHub/CODEOWNERS/security/release holds.
- Preserve Terminal1244's existing integration branch and scoped stage/publication constraints; no alternate carrier for a denied effect.
- No new data, auth, lifecycle, publication, retry, queue or monitoring control plane.
- This audit's Paper edits are verified. These implementation sequences remain build work under their existing owners; no runtime activation or release is claimed.
