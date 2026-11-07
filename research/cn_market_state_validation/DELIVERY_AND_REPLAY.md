# China Market State P3 — delivery and frozen reproduction

This directory preserves the historical study at evidence commit
`cf60bdaee7d44b7414c398c9684035eb6778bb51`, preregistration commit
`ddd62442e14b682612a4bc5ebde4cc02e6f03bbf`, and frozen source/input base
`d5eb16f3b3a093afb053efe275be62778729dcf4`.
The sample ends on **2026-09-24**. References to the current day or score 38 in
the frozen report concern that historical date, not the latest production model.

## What the delivery repair preserves

The ten original study/preregistration/input/method/result artifacts and
`scripts/research/cn_market_state_validation.py` are unchanged. The original
seven-case test module is preserved byte-for-byte as
`frozen_replay_contracts.py` (Git blob
`bb574b048a9dbfa38c644ce269893bc84a767abf`).
Its recorded historical test hash and receipts therefore retain their original
meaning. No study, bootstrap draw, result, threshold, weight, input manifest or
model-source hash is regenerated or refreshed by this delivery.

## Checks that run on each PR

The existing `unrun-brain-desks / gate: code` job already executes
`tests/test_risk_radar_review.py`, which owns state-ladder and displayed-risk
audit methods. That module now also executes five unchanged P3 cases:

- next-session outcome timing with synthetic prices;
- strict release-date/session shifting;
- available-leg weight renormalization;
- lower-score risk orientation for AUC;
- the committed reconstructed-evidence authority ceiling.

A sixth hermetic case exercises the unchanged strict verifier with real
temporary fixture bytes and Git hashing. It requires successful verification
of the unchanged prereg payload, rejects mutation in each of the model/input/
method manifests, and rejects a changed prereg payload. It does not mock the
verification function or claim that fixture bytes are the historical dataset.

These cases require no live market data, model calls, network acquisition or
empirical study replay. Existing CI commands, jobs, scopes, budgets and
dependencies are unchanged.

## Frozen reproduction is a separate historical check

Two original cases verify the actual frozen source/input manifests and
reproduce the historical score from that dataset. They deliberately cannot
run truthfully against a mutable checkout of today's main. On inspected main
`9e9b830988b85712410c465cbee8276660afa52a`, for example:

| File | Frozen Git blob | Inspected main Git blob |
| --- | --- | --- |
| config.yml | 0e31ebbced710de614269d8da4ed2ac76215c0a2 | 5be75249c98033d7ee0fbe55928713b1f50af627 |
| engine/cycles.py | 9c682f1251ffd48abf4f78238df74ae3d5879479 | 8f3d66289e7bbfeccdbdb7ff05ce6b9a8689701e |

The harness continues to reject those mismatches. Do not update the frozen
manifests, bypass `verify_prereg()`, or label the mutable tree an exact replay.

To repeat the historical seven-case check, use an isolated checkout of the
exact evidence commit above and its original
`tests/test_cn_market_state_validation.py` path. At that commit the original
test path, harness, prereg and full frozen source/input closure coexist.
The archived `frozen_replay_contracts.py` contains those same test bytes.
A dependency-capable runner and the recorded input blobs are required.
An 800-draw study regeneration is not part of ordinary delivery CI.

The [historical run receipt](run_receipt.v1.json) and
[parent review](https://github.com/mastermindx-market-intelligence/macro/pull/8019#issuecomment-5831721537)
record seven P3 cases plus 48 incumbent China cases passing, and the original PR
body records the parent's byte-identical 800-draw replay. Those remain
historical evidence, not fresh execution claims for this delivery.

## Authority ceiling

`SCORE_0_100=DESCRIPTIVE_ONLY`, `CURRENT_WEIGHTS=INSUFFICIENT`,
and `CUT_42/CUT_60=PRODUCT_ONLY` remain the result. No production behavior,
forecast promotion, ranking, capital policy, sizing or trading change follows
from this source delivery. New predictive claims need the separately accepted
same-model prospective evidence described in the frozen adjudication.
