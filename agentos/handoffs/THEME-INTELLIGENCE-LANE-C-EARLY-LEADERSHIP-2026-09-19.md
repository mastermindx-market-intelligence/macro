# Theme Intelligence Lane C Return — Early Leadership and Subthemes

Prepared: 2026-09-19  
Operation: `theme-intelligence-c-early-leadership-and-subthemes-20260919-sol-001`  
Integration lead: **Lane A**  
Review carrier: Macro draft PR **#7455**  
Branch: `worktree-theme-intelligence-c-early-leadership-20260919-sol-001`

## Lifecycle state

| Edge | State | Evidence |
|---|---|---|
| Chairman delivery | ACKED | Live handoff delivered to this Web session |
| Pickup | COMPLETE | Source law, custody, owners, and collision records reconciled |
| START | RECORDED | Recorded before the first source mutation |
| Implementation | COMMITTED | `d1727e80a8bead258a545ceb6d938286baf64d31` |
| Review pickup | OPEN | Draft PR #7455 |
| Independent review | PENDING | No independent approval claimed |
| Merge | NOT DONE | Draft PR remains open |
| Deployment | NOT DONE | No release or runtime mutation performed |
| Production acceptance | NOT DONE | No deployed-byte or browser proof claimed |

Initial pickup base was `17a3e7a649da455267013dcfcc640c9c3be12c7e`. The implementation was rebased without conflict onto current main `ca7533a67670e0393728fda4b1633b56720aa1e0`; implementation tree is `0815da8b82212f1fd3da8985969f2c5eee0ce216`.
## Capability delta

Lane C adds additive schema `subsector_rotation.closed_session_leadership.v1` to the incumbent Group Reads publication path. It measures completed-session parent and subtheme behavior over 1/3/5/10/20/60 sessions using the existing `engine.basket_index._load_member_ohlcv` owner and SPY session calendar.

The observation separates:

- strength level from five-session acceleration and ten-session persistence;
- return and relative-strength change/slope versus market and parent;
- participation, dispersion, broadness, and one-name concentration;
- current, stale, unpriced, short-history, and missing-session coverage;
- relevant volume and 20-session reclaim evidence.

Parent membership is deduplicated by instrument. Current membership is labelled a non-PIT technical window. Unsupported values remain null with reason codes. Stale tails are not forward-filled into fabricated zero returns. Same-day bars are excluded until 16:15 New York time.

Every observation is descriptive/context-only and carries an evidence receipt with source records, observation/input/computation clocks, bar status, membership basis, and all authority flags false: `may_rank`, `may_gate`, `may_size`, `may_escalate`, and `may_trade`.

The first production vertical is intentionally limited to the existing `Semiconductors` parent. It reaches the actual ThemeState consumers `ai_semiconductors`, `memory_storage`, and `semicap_equipment`. No new ThemeState producer, rotation store, lifecycle ledger, alert rule, forecast, or ranking engine was created.
## Source changes

- `engine/subsector_rotation.py` — pure closed-session measurement and evidence contract.
- `scripts/build_subsector_rotation.py` — completed-session cutoff, bounded owner loading, visible fail-closed receipt, and actual publisher attachment.
- `engine/neuralweb/thematic_state.py` — preserves the descriptive observation in the incumbent consumer.
- `tests/test_subsector_closed_session_leadership.py` — measurement discriminators.
- `tests/test_build_subsector_closed_session_leadership.py` — owner loading, cutoff, failure receipt, and actual publisher wiring.
- `tests/test_thematic_state_leadership_receipt.py` — canonical consumer receipt.

No generated marketdata, crosswalk, membership history, scoring, signal-gate, sector-signal, Prophet, deployment, or CI wiring file changed.

## Identity and coverage disposition

| Source group | Role in requested coverage | Price evidence at 2026-09-18 | Disposition |
|---|---|---:|---|
| `semiscompute` | Direct broad compute group; CPU/GPU/accelerator proxy | 8/8 current and 60-session complete | Published in first vertical |
| `semismemory` | Broad memory proxy for HBM/DRAM/NAND | 5/5 current and complete | Published; dedicated identities still absent |
| `semislithography` | Direct equipment source group | 5/5 current and complete | Published |
| `semispackaging` | Direct packaging/test equipment group | 6 priced, 5 current; ASX stale one session | Published as `PARTIAL` |
| `aicompute` | Broad AI compute proxy | 16/16 current and complete | Measurement evidence only |
| `hardwareservers` | Direct server hardware source group | 7 priced, 6 current; CSCO stale one session | Measurement evidence only |
| `hardwarestorage` | Broad disk/SSD storage group | 7/7 current and complete | Measurement evidence only |
| `telecominfrastructure` | Broad telecom/optics proxy | 8 priced, 5 current | Measurement evidence only |

ARM is a direct member of `semiscompute`. SNDK is a direct member of both `semismemory` and `hardwarestorage`. Dedicated GPU/accelerator, HBM, DRAM, NAND/SSD, and optics identities are not fabricated here; canonical additions remain with GMI/F04.
## Real input-to-output proof

Proof source commit: `d1727e80a8bead258a545ceb6d938286baf64d31`  
Theme-tree blob: `65b0e9e3f5f938aaf224130f0af14cd6922aafed`  
Snapshot blob: `534c1be0c68b50e7c05ef81183588ef7c76d7b71`  
Existing rotation-feed blob: `86175c2c01b806bb4738bae6bc14fd30d56c4223`  
Bounded price-manifest SHA-256: `7fbd80bc049fdaa934c5d86e3047d1a2b9d9f21f8af68e680280937445b2025c`

The exact bounded proof used closed sessions through 2026-09-18 and 47 explicit Yahoo price records. Parent coverage was 46/47, so the aggregate status correctly remained `PARTIAL`; the bounded proof set did not contain NVEC.

| Subtheme | Status | 5-session return | 20-session return | 60-session return | 5-session excess vs parent | 5-session RS change/slope | Acceleration |
|---|---:|---:|---:|---:|---:|---:|---|
| Compute | MEASURED | +2.6267% | +7.8355% | -5.3124% | +2.7352 pp | +2.7219% / +1.9861% per session | DETERIORATING |
| Memory | MEASURED | +3.4006% | +1.4255% | -15.6379% | +3.5091 pp | +3.4965% / +1.9828% per session | DETERIORATING |
| Lithography | MEASURED | -2.5324% | -7.7590% | -22.7415% | -2.4239 pp | -2.4420% / +0.8706% per session | DETERIORATING |
| Packaging | PARTIAL | +1.1493% | +3.6298% | -13.8387% | +1.2578 pp | +1.2431% / +2.9394% per session | DETERIORATING |

The same observation and its measurement receipt were traced through the actual `engine.neuralweb.thematic_state` consumer into `ai_semiconductors`, `memory_storage`, and `semicap_equipment`. Each receipt preserved `membership_is_point_in_time=false`, `may_rank=false`, and observation session `2026-09-18`.

This proves source-level closed-session publication and parent/subtheme distinction. It does not prove deployed bytes, browser parity, predictive alpha, alert quality, or production acceptance.
## Verification and source conflicts

Post-rebase verification on `d1727e80a8bead258a545ceb6d938286baf64d31`:

- `python3 -m pytest -q tests/test_subsector*.py` — **102 passed, 3 skipped**.
- ThemeState, consumer receipt, and builder suite — **44 passed, 3 skipped**.
- Sector-page suite with exact HEAD sparse redirect stubs — **20 passed**.
- `git diff --check` and `py_compile` passed before commit.

The skipped tests are incumbent environment-dependent cases. Warnings are pre-existing pytest fixture deprecations and temporary-browser cleanup permission warnings.

Collision rulings:

- PR #6809 PIT ownership is merged and preserved; this operation does not represent current membership as historical PIT truth.
- Draft/HOLD PRs #7064 and #7095 remain research-only; no held persistence or sector-control model was copied or activated.
- PR #7000 remains an incident-record carrier; its active consumer repair ownership was not taken.
- Open draft #7023 overlaps only incumbent `tests/test_subsector_rotation.py`; Lane C used dedicated path-disjoint tests.
- The latest main advance to `ca7533a67670e0393728fda4b1633b56720aa1e0` touched only an unrelated PC-recovery handoff.

No independent reviewer has approved this result yet. Draft PR #7455 is the current review pickup surface.
## Remaining gates and exact next action

Open gates:

1. Lane A must review the additive fields and either adopt them or map them into Lane A's versioned consumer contract without broadening permissions.
2. GMI/F04 must decide canonical identity and exposure treatment for dedicated CPU, accelerator, HBM/DRAM, NAND/SSD, server, storage, and optics subthemes. The source-native evidence-only cohorts above must not be treated as new canonical themes before that decision.
3. Evaluation/F must resolve the exact corporate-action basis and predeclare baselines, false-alert tests, and promotion criteria. The implementation currently discloses `OWNER_CLOSE_SERIES_UNVERIFIED` rather than manufacturing certainty.
4. An independent reviewer must approve the source change. Only then may the incumbent merge/release owner consider merge and natural publication.
5. After merge and deployment, the release owner still owes deployed-byte/browser proof from a naturally completed session. A source proof is not production acceptance.

**Exact next action for Lane A:** pick up draft PR #7455 and reconcile `leadership_observation` plus `measurement_receipt` with Lane A's additive consumer contract. Keep every capability permission false; route identity proposals to GMI/F04 and corporate-action/evaluation questions to F. Do not merge until independent review and those interface rulings are recorded.

This child lane stops at the implemented, tested, pushed, source-proven draft-review boundary. It does not claim the parent Theme Intelligence program complete.