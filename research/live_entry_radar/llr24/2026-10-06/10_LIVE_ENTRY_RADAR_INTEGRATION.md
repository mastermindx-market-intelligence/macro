# 10 — Radar integration and repair frontier

## 0. Acceptance boundary

A later integration is not accepted unless a real, newly observed market event reaches the existing Radar episode, a causally timed prediction is durably captured through its accepted evidence owner, and the same prediction/version is visible through the actual Terminal route. Test healthy, stale, unavailable, partial, invalidated, no-opportunity, overnight and RTH cases. Model accuracy, source admission and product delivery are separate approvals.

This is a **proposal for an extension**, not authorization to change Radar's live firewall. Current source is at Macro `3d7a6f86e81089e290996438335843b9630807fa`, with scoped-byte parity established at later `a80e6ff8ff771b0f994982b2dfb2de203197dc18`.

## 1. Radar ruling

Radar is active and needs both repair and extension. Dated October 6 receipts establish live publication for 246 of 3,077 names, 312 candidates, seven events, fourteen transitions and successful spooling. They also establish 2,831 unavailable names and later pass durations of 519–521 seconds. The current W5 artifact separately reports `WAITING_FOR_LIVE_SOURCE`, no intake directory and zero forward rows/registrations. Therefore the operational publisher has bounded live evidence while the prospective scientific path is `DARK_OR_DISCONNECTED`. [R10–R11; I784-live; I784-timing]

Reuse the incumbent repairs #8547/#8548 for pack verification and C3 computation; do not create a competing performance lane. The successful October backlog drain and terminal-wins ledger repair are already evidence, not tasks to redo. Full signed-in G8 journey acceptance on issue #784 remains open. [R18; PR8492; PR8547–PR8548]

## 2. What remains with Radar

Radar owns the evaluator, detector/spec identity, sampled observations, operational arm/turn/candidate/invalidation/expiry/resolution lifecycle, episode/event IDs, pack, spool ordering, source/basis clocks and first transport observation. Terminal is its consumer, not a second detector. W5 and Evaluation OS own prospective intake/outcomes. Setup Species owns scientific definitions and promotion lineage.

The present detector registry is G0 Grey Dot; C1 daily live washout; C2 daily turn variants; C3 daily/four-hour recovery; C4 multi-timeframe stratification (`can_fire:false`); and C5 preserved 3D Bottom Watch. F1 fusion is reserved/refusing. A five-minute polling interval does not turn their underlying daily/3D semantics into a five-minute reclaim signal. The proposed production `tactical_dislocation` family is absent. [R07; R34]

## 3. Contracts that cannot be bypassed

`mastermind.live_entry_episode.v1` has 24 exact fields including `variant`; unknown fields fail deserialization. Its identity derives from ticker, detector ID, variant and first-arm time. `detector_score`, `research_priority` and `opportunity_score` are structurally null. `price_at_signal` is nullable but not a null-only score. The live firewall forbids probability/confidence/MAE/MFE/outcome/rank/score-shaped keys across pack, journal, spool, ledger and product structures, apart from specific existing exceptions. [R05; R08]

The existing event envelope is `entry_radar.events/v1`, with pass timestamp/ID, pack basis, transitions, events and health. It has no prediction attachment collection. A probability shown only in the product projection would not automatically be prospectively captured. Neither `feature_snapshot` nor catalyst/health is a loophole.

**Required owner decision:** accept a separately typed optional prediction attachment and its evidence path, then amend only the exact necessary firewall/schema/consumer contracts under joint Radar and Evaluation ownership. The existing `_episode_rows` → `_attach_catalyst` pattern is a useful projection precedent; it does not itself grant forecast admission. Preserve the durable episode identity and original event history. [R08; R16–R17]

## 4. Proposed annotation semantic contract

The following field names are a reviewable research draft, not a currently accepted schema:

```json
{
  "schema": "entry_radar.tactical_annotation/v1",
  "radar_episode_id": "owner-issued episode id",
  "prediction_id": "incumbent evidence-owned immutable prediction id",
  "security_ref": {"canonical_id": "qualified security id", "binding_receipt": "owner receipt"},
  "species_ref": {"id": "registered existing or admitted species", "version": "frozen version"},
  "decision_cutoff": "UTC instant",
  "source_known_through": "UTC instant",
  "inference_completed_at": "UTC instant",
  "published_at": "UTC instant",
  "economic_day_id": "versioned day identity",
  "session": "qualified session",
  "clock_version": "calendar and aggregation version",
  "source_mode": "TRUE_POINT_IN_TIME | RECONSTRUCTED_CAUSAL | FINAL_VINTAGE_RETROSPECTIVE",
  "source_basis_refs": ["immutable source manifests"],
  "model_ref": {"version": "frozen", "feature_version": "frozen", "calibration_ref": null},
  "observations": {"observed_low_distance_bps": null, "reclaim_geometry_ref": null},
  "heads": {
    "low_survival_30m": {"status": "NOT_YET_ESTIMATED", "value": null, "reason": "MODEL_NOT_QUALIFIED"},
    "first_new_low_before_reclaim_30m": {"status": "NOT_YET_ESTIMATED", "value": null, "reason": "MODEL_NOT_QUALIFIED"},
    "executable_path_30m": {"status": "UNAVAILABLE", "value": null, "reason": "QUOTE_PATH_NOT_QUALIFIED"}
  },
  "support_ref": null,
  "prediction_evidence_ref": "pre-outcome receipt",
  "expires_at": "UTC instant",
  "authority": {"rank": false, "select": false, "size": false, "trade": false, "entry_gate": false}
}
```

A later head schema must include target/label version, reference-low basis/value/time, horizon, cost/size/latency convention, calibration cohort and counts, uncertainty method, model disposition and reason-coded availability. Each successful value must have an evidence reference. `source_mode` is not a quality average; a mixed dependency cannot inherit its strongest input's grade. The public consumer receives only fields needed for user decisions; raw internal provenance belongs in the evidence drill-down.

Consumer receipt time belongs to transport evidence and is recorded on consumption, not prefilled by the producer. No prediction-known timestamp may be copied from `candidate_at`: the current UI uses that fallback for episode display, which is not a model computation clock. If inference finishes after the intended cutoff, record the delay and evaluate actionability from the actual usable time. [R08; R20]

## 5. Failure and lifecycle semantics

The current transition map permits `PROBING→ARMED`; `ARMED→TURNING/CANDIDATE/EXPIRED/PROBING`; `TURNING→CANDIDATE/INVALIDATED/EXPIRED/ARMED`; and `CANDIDATE→INVALIDATED/EXPIRED/RESOLVED`. Terminal states have no exits. The IDR product spec's `ARMED→INVALIDATED` and `PROBING→EXPIRED` edges are not implemented. Reconcile prose with the owner; do not silently add edges or misuse another state. [R07; R14]

A forecast can expire, become unavailable, lose support or be superseded without changing the underlying episode state. These are annotation validity facts, not a second market lifecycle. A resolved horizon does not mean profitable. Missing quotes do not mean the low failed. A new low updates observations and may invalidate a particular forecast/reference under the existing episode rules; it cannot rewrite an earlier prediction into a success.

Terminal's generic `CANDIDATE→“Reclaim held”` mapping currently spans families including C5 early-watch records. A source-aware factual label such as “Bottom watch” or “Candidate observed” is safer until a specific reclaim event establishes stronger language. This is an owner semantic correction to adjudicate at G8, not permission to launch a new detector. [R20–R21; R34]

## 6. Integration order and proof

1. Reconcile existing repair custody and obtain natural cadence/coverage receipts.
2. Connect the existing spool writer to W5 intake; show one authentic eligible event and its first-observed clock reaching forward ledger/qledger exactly once.
3. Accept the annotation/prediction-capture contract jointly, preserving strict old-reader behavior and explicit version migration.
4. Run shadow inference with all authority false. Persist the prediction before outcomes; prove restart/replay/idempotency without duplicate episodes or predictions.
5. Project it through the existing same-host file → authenticated `/api/v1/dislocations` → screen/drawer/chart path.
6. Observe outcomes through incumbent grading, then independently adjudicate calibration and usefulness.

Performance acceptance is proposed as at least a full natural session with p95 cycle duration below the five-minute timer, no overlap/drop pattern, and headroom documented before inference is added. Actual source-age bounds depend on each horizon; the existing 20-minute display-file freshness threshold cannot qualify a five-minute forecast. Benchmark healthy empty/no-opportunity and unavailable cases too, so quick failure is not mistaken for fast useful processing.

Rollback disables the optional annotation producer/consumer feature under its owner, retaining all old predictions and outcomes. It must leave the incumbent detector/spec hash, pack, episode history and existing quote plane intact. This commission implements none of these runtime changes.
