# Rotation W2: episode linkage and delivery clocks

Status: proposed next bounded implementation contract; NOT_BUILT. This is source-backed continuation of the Chairman-authorized adaptive-rotation project, not a new workstream, signal, clock owner, publication service, or trading rule.
Research operation: `rotation-w2-clock-contract-20260916-sol-001`. Records carrier: existing research PR7168. W1 implementation remains separate PR7174 on its existing carrier and is BUILT_NOT_PROVEN.
Current protected procedure: Mastermind `7642aea155d2817219135b24246b55c1d7611c66`, Skillpack1.0.1. Inspected implementation source: Macro `effdbd13cb78f2da3770733e85f64c93d395eb0d`.

## Mission and capability

A user examining one real recommendation can distinguish when the setup was known, when a plan was originated, when its exact version was observed on the private product, and what price/time evidence would have supported execution. The machine can attribute delay to the relevant transition instead of counting an unrelated historical plan as successful delivery.
No promise of improved returns follows from this diagnostic capability. W1's source/representation truth is necessary but does not complete the adaptive-intelligence vision.

## New source findings that constrain implementation

1. `engine/us_candidate_episode.py:218-235,405-440` already owns candidate episode identity: security identity, identity epoch, canonical structural anchor and rearm generation. Its event envelope distinguishes occurred_at, known_at and recorded_at, and it retains source_event_ids and corrections. Consume this owner; do not invent a second opportunity ID or use ticker/date proximity as identity.
2. The inspected `engine/prophet_bridge.py:4603-4708` trade_plan/v1 constructor explicitly carries plan id, recorded_at, formation/signal/confirmed/observed dates, price_basis_date, entry_date, selection era and entry basis. It does not attach the canonical candidate episode identifier in that route. An existing reference-price date is not evidence of user-visible publication or an attained fill.
3. `engine/prophet_lab/boards.py:207-286` already separates current non-closed plans from prior closed plans. Preserve that useful behavior. Its current comparison is ticker-level; measured_lab_to_prophet_lead_days compares Lab observation with entry_date or signal_date. The comments explicitly acknowledge the absence of a separate publish-history field. That number is not measured delivery latency and cannot be silently rebranded as one.
4. `scripts/build_prophet.py:212-240` and `.github/workflows/daily.yml:2411-2466` already publish a public-safe health receipt keyed to checkpoint/index SHA. Its published_at timestamps preparation of the health projection for R2 publication. It does not itself prove that the authenticated private plan endpoint served that index at that time. Preserve the public/private split; never place premium plan identifiers, entries or theses in the public health payload to make measurement convenient.

These are bounded source observations, not an assertion that every other estate path was exhaustively scanned. Reopen the finding if an existing exact episode-to-plan and authenticated-publication binding is recovered.

## Frozen no-rebuild boundaries

Existing candidate-episode identity and correction owner -> existing Prophet origination/plan identity -> existing private plan publication/checkpoint owner -> existing Lab/admin read consumer -> existing forward grading owner.
W2 adds an explicit relationship and evidence semantics to those owners. It must not add an identity plane, parallel plan ledger, publication bus, scheduler, ranking score or trading authority. Reconcile current producer ownership and live implementation state before an implementation START; this record is not worker assignment.

## Implementation order

A. Inventory the actual accepted linkage available at origination. Bind a plan to an existing canonical episode only through an exact stable source-event/anchor/identity relationship from the admitted snapshot. Multiple matches, identity-epoch disagreement or missing linkage remain typed unknown. Do not nearest-date join, infer from ticker alone, or overwrite the existing plan id.
B. Add provenance-only relationship metadata on newly originated plans through the existing producer. Preserve every incumbent ranking, admission, membership, target, price, horizon and plan identity byte-for-byte apart from the explicitly additive metadata. Historical plans remain unlinked unless exact contemporaneous evidence exists; a current lookup is not historical proof.
C. Extend the existing private publication verification path to observe the exact served index digest/generation. Reuse its current persistence/checkpoint mechanism and the existing sole writer. Keep publication attempted, checkpoint committed, R2 health updated and authenticated private serving observed as different facts. Before implementation freeze the concrete owning path; do not create a new receipt store merely because none was immediately found.
D. Extend the existing Lab/admin comparison. Preserve the older reference-date gap under explicit semantics; add actual delivery intervals only when both endpoints are supported at compatible precision and within the same linked episode/plan version. No integer-day date becomes an invented midnight timestamp. Negative intervals or clock contradictions withhold the derived interval.
E. Connect the canonical forward grading/learning owner to the same decision version. Execution utility requires the first attainable action after availability, actual session/entitlement/price basis, costs and path; same-close signal marks are not fills.

## Time, null, correction and rights behavior

Use existing event, public-availability/known, ingestion/recorded, proposal, publication-observed and execution times only where the owner actually records them. Preserve precision and timezone; do not add an invented observation time. Record incomplete evidence rather than a false zero duration.
A corrected or retracted episode, plan or input generation does not rewrite the historical decision. Keep original version, correction relationship and evaluation eligibility separate through current owners.
A closed-window missed-delivery claim requires complete relevant record coverage; an absent file, failed read or missing join is unknown. Still-open windows remain open. The opportunity window must be defined before its subsequent price path is read, not ended at the eventual peak.
No public release of private-plan fields, licensed price corpora or credentials. Existing authenticated consumers and entitlement boundaries remain intact.

## Discriminating acceptance

- Same ticker, different opportunity, direction or identity epoch does not count as conversion.
- A prior closed plan cannot masquerade as current membership; preserve the existing Lab test contract.
- An R2 health update with an older private served index cannot produce an on-time publication success.
- Origination date, signal/reference-price date and actual serving observation remain visibly different.
- Date-only or absent clocks never produce second/minute latency claims; future corrections cannot alter an as-of evaluation.
- Replays and retries do not double-count plan versions or episodes; incomplete coverage does not certify a miss.
- One real energy case and one non-energy control travel through producer, exact existing identities, private publication evidence and real UI/machine consumer. Synthetic cases alone do not close acceptance.
- No strategy output changes; real production input/response/browser evidence and independent exact-source review are required.

## Adjacent research owners and scientific holds

The recovered September sector study belongs to `WS:LEADERSHIP-PERSISTENCE-INTELLIGENCE`, PR7095 at `27a966041272a9de6823a590e90a0c6fd7b5141d`, stacked on RPH-0 PR7064. Its handoff still names immutable-head review and hosted archive proof gaps. Do not relabel its research as a deployed adaptive selector.
Temporal Grain is a separate sibling owner for grain/anchor/kernel/data-plane separation and chart parity. Technical Opportunity W2-0 owns broad U.S. Daily/Weekly/4H data/clock/rights/Terminal parity; Entry Radar owns tactical intraday events. No sibling is replaced by this rotation programme.
The RPH-1 latest20-signal cells span different calendar periods across grains; a matched-calendar comparison needs a new preregistration rather than retuning frozen RPH-1. Rank-window overlap is not predictive persistence. A dependence control must preserve the joint cross-section needed by its null; independently shuffling each sector cannot silently be treated as a correlation-preserving null. Near-zero descriptive means alone are not a powered equivalence or no-edge test.

## Next action and stop conditions

Sol first closes W1's actual review/CI/release gates. For W2, recover exact existing producer/publication bindings and current owners, then commission one provenance-only producer-to-existing-consumer slice. Stop at ambiguous source identity/custody, incomplete publication evidence, rights/entitlement gaps or any requested change in trade authority. Do not fabricate a current on-time conversion percentage to avoid a typed unknown. Preserve the full adaptive-rotation programme as the parent outcome.
