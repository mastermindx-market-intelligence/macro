# Basic Materials R20 — T4 core principal review before next GREEN

**Operation:** `gmi-basic-materials-research-20260923-sol-001`  
**Research carrier:** Macro #7796 / `sol/basic-materials-research-20260923`  
**Implementation carrier:** Macro #7984 / `claude/basic-materials-core-v0`  
**Reviewed implementation head:** `36f330b1f7829a289a44937bca0007c734d6df5e`  
**Current protected procedure:** Mastermind `605cd056c3463c992d85ba76dbcc90fbb758da75`, Skillpack 1.0.1/bootstrap1.  
**Disposition:** principal read-only review and repair ordering. No product/source/rights/identity modification in this unit.

## 1. Carrier and source reconciliation

#7984 remains OPEN/DRAFT/HOLD at the exact reviewed head above. Research PR #7796 is separate and retains the full R1–R19 specification/acceptance program. Current Macro main moved from #7984's base `22094843f4042db6d9d77ad8847bcdbf9a27faa9` to `773be812b89ccff610a248f187f8ac98b057fbbf`; exact compare showed no changes to the Materials T4 target paths.

The shared-owner thread has no acceptance response to Materials amendment comment5809093547. Later Robotics PICKUP/START on the same research thread belongs to its separate operation and does not assign or resolve Materials.

The prior cash-reconciliation production patch remains a platform-blocked action with EFFECT_NONE. It was not retried, rephrased or routed through another tool/provider/host.

## 2. Read-only probes against #7984

The current implementation correctly refuses a missing `quantity_basis`, and the two already-green TDD behaviors remain historical evidence. Bounded runtime probes found three additional defects that must be converted to RED tests before #7984 can become mergeable:

### R20-F1 — canonical decimal grammar is too permissive

`compare_measures` currently accepts:
- `value_text="1e3"` and computes a spread;
- whitespace-padded `value_text=" 7 "`.

R18's qualified scalar convention rejects exponent spelling and uses plain decimal text. The future fix must validate canonical decimal text before constructing `Decimal`, while preserving signed and fractional values. Do not coerce floats or normalize arbitrary input text into an apparently exact measure.

### R20-F2 — duplicate metric labels silently overwrite evidence

The composer builds `by_metric` with a dict comprehension. Two `price_current` assertions are accepted; the later row silently replaces the first. The bounded probe changed current unit margin from the intended value to `918` and rewired provenance to the second evidence ref without any refusal.

Future behavior must require an unambiguous required-role mapping. Duplicate required metric roles refuse rather than last-write-wins.

### R20-F3 — current/prior chronology is not validated

A probe labeled January–March as `current` and April–June as `prior`. The composer still emitted `price_up_margin_down`. A same-period economic change requires an explicit chronology relationship, not merely matching `period_kind` and economic basis.

Merged Consumer Cyclical precedent on current main, `engine/sector_intelligence/consumer_cyclical_projection.py::_select_pair`, requires current `period_end` strictly greater than prior `period_end` and pairs facts deterministically rather than dict-overwriting them. Reuse that invariant, not that vertical's record type.

## 3. Consumer Cyclical precedent and exact boundary

Merged PR #7942 delivered a deterministic sector core while keeping shared route/private/browser legs frozen. Its return record truthfully distinguishes merged/core proof from the unreached browser ruler. That is the correct precedent for Materials.

Do **not** copy the Consumer Cyclical sector schema into Materials. Its fact kinds, comparison basis and source envelope remain vertical-specific. Reuse only generic design conventions already accepted on main: Decimal-only calculation, explicit result keys, deterministic fact pairing, strict chronology and an unavailable/withheld state.

## 4. Frozen TDD repair order

When the previously blocked product-write class is platform-permitted, resume the same #7984 carrier and the existing RED. Do not mint a successor carrier.

1. **Existing RED first:** implement only `cash_reconciliation`; prove its test green.
2. Add RED for canonical decimal text (at minimum exponent and whitespace cases); implement minimal strict parser.
3. Add RED for duplicate required metric roles; refuse ambiguity.
4. Add RED for reversed/non-prior chronology; require explicit valid ordering.
5. After each GREEN, rerun the complete Materials targeted test file and `tests/test_market_ontology_exposure_map.py`.
6. Only after all four economic mechanisms and denial cases are green: freeze the Materials output schema and run the broader T4 contract/suite gates.
7. Native source adapter/private/profile/company-route integration remains separate and cannot be inferred from core correctness.

No future repair may weaken the existing working missing-`quantity_basis` refusal, provenance refs or research-display-only authority ceiling.

## 5. Verification and authority boundary

Evidence generated in this unit:
- exact #7984 head read from GitHub;
- current main and protected procedure repinned;
- main delta inspected for Materials/F04/sector-intelligence target collisions;
- current #7984 module/tests read from exact head;
- read-only runtime probes reproduced F1–F3;
- merged Consumer Cyclical core/return inspected as sibling precedent;
- principal finding comment posted on #7984 as issuecomment-5826147289.

No code, source records, identity rows, permission registries, routes, ranking/entry/size/trade behavior or production state changed. No independent reviewer acceptance is claimed. #7984 remains deliberately RED/HOLD.

**MISSION_COMPLETE:** false.  
**Continuation:** same #7984 RED when product writes are permitted; otherwise advance only independent review/integration-readiness lanes that do not duplicate the shared foundation or bypass the blocked action.
