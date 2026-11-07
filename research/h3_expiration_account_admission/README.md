# H3: expiration-aware physical-account admission

**State: source contribution verified; installation and live acceptance unproven.**
This is the assigned continuation of [H3 on Macro #7142](https://github.com/mastermindx-market-intelligence/macro/pull/7142#issuecomment-6705878444), under [Mastermind #983](https://github.com/mastermindx-market-intelligence/Mastermind/issues/983).
The original selector remains unchanged. The missing account-level join is implemented in the existing native Broker, delivered here as an exact patch for the active [#2175 composer](https://github.com/mastermindx-market-intelligence/Mastermind/pull/2175). This Macro carrier does not install native code.

## Exact contribution and reproduction

The native preimage is `Mastermind@39bd39aaa8c5fa1f6112fc34c593815323428b2f`.
[manifest.json](manifest.json) identifies all 16 original input blobs and the three exact outputs; [native.patch](native.patch) changes only:

- `ops/native_fabric/quota_continuity/candidate/lease_broker.py`
- `ops/native_fabric/quota_continuity/candidate/quota_remote.py`
- `ops/native_fabric/quota_continuity/tests/test_expiry_account_admission.py`

The quota-reader addition is a proposed **consumer adapter**, not a claim that H2 already emits this envelope. The active H2 writer owns producer composition. Its actual successor must be reconciled with this patch; do not overwrite that writer or fuzz an incompatible preimage. No #2175, H2, #2182 or live runtime branch/workspace was modified to create this contribution.

Run from a Macro checkout with Python 3.12, PyYAML and Git available:

```sh
python scripts/qualify_h3_expiry_admission.py \
  --native-root /path/to/read-only-native-source \
  --receipt /path/to/h3-source-receipt.json
```

The command verifies original Git blob IDs, byte counts and SHA256 values, copies only the declared source/test inputs into disposable directories, applies the exact patch, verifies every postimage, then runs the discriminator and regressions. It makes no network request and does not patch the supplied checkout. A changed preimage refuses before patching. Native generation manifests and installed code remain the final composer's responsibility.

## Implemented behavior

The Broker reads the canonical account document freshly inside its existing lease transaction. Existing provider/model, host pairing, entitlement/grant, cooldown, fairness, account/model concurrency and strict-pin paths remain ahead of or intersect account selection. Model/task suitability remains with the incumbent picker. H3 ranks accounts for the already-selected suitable model; it does not invent missing model quality, latency or marginal-price evidence.

An explicitly configured `expiry_admission` policy enables the strict join for an allowance scope. The adapter reads the incumbent quota cache without refreshing it, resolving credentials or accepting a caller-selected path. It requires a fresh authoritative account/generation/scope-bound observation for every required window. Independently binding 5h, weekly and monthly windows all constrain admission. Null reset clocks can support known headroom but confer no expiry priority; unknown balances, stale/future/past windows and malformed observations refuse.

Qualified claim ceilings and urgent reserves are checked in each window's **exact integer meter**, with no percentage-to-request/token conversion or floating-point money arithmetic. Integer quantities are bounded to signed 64-bit magnitude; booleans and fractional quantities refuse. Any required monetary scaling must be supplied and qualified by the existing owner. An absent/zero/unknown cost ceiling refuses. A nonempty `budget_ref` records provenance; it does **not** itself prove that an execution ceiling is enforced.

All enabled aliases sharing the canonical `quota_circuit` scope must agree on their observation and reserve contract. Their existing leases are counted across models, pools and WORKER/APPLICATION consumers. Two claims serialize through the existing Broker file lock and SQLite transaction. No reservation table, account inventory, provider poller, scheduler, queue, retry owner or credential store is added.

Among eligible accounts, the existing R31 36-hour/15-percent use-before-reset policy supplies the urgency thresholds. The earliest qualified reset ranks ahead of the incumbent held/cap/name tie-break. Bailian's existing cooldown precedence remains ahead of expiry. Exact account pins still select that account or refuse; an untrusted preferred-account string cannot supply observation or generation evidence.

The actual lease insertion retains `account_admission_json` and its digest on the existing `leases` row. The evidence includes actual lease/root/account/model/task/purpose, account generation, quota scope, source/config/policy commitments, observation/window identity, retained claim ceilings, reserves and selection reason. A SQLite trigger prevents rewriting that binding. Existing APPLICATION recovery, dispatch and terminal settlement continue on the original lease/account; the response-loss tests do not create another lease or authorize another request.

Releasing a lease does not replenish a stale provider balance. H2 must prove exact per-window inclusion before that terminal liability can be discharged. Active claims cannot be acknowledged away. A changed epoch, elapsed reset clock or earlier grant time does not erase cross-reset or delayed consumption. Older observations and contradictory observations at the same timestamp refuse. Removing the policy or renaming an account's scope cannot silently bypass retained H3 liabilities.

## Executed qualification

[qualification.json](qualification.json) is the machine-produced receipt for the delivered patch and manifest, not an estimated test count.

| Proof | Observed result |
| --- | --- |
| Exact native preimage | 16 input blobs verified before copying |
| Unmodified Broker discriminator | Expected failure: actual claim selects `alpha-far` instead of `zeta-near` |
| H3 regression cases | 32 passed |
| Unchanged APPLICATION admission suite | 24 passed |
| Unchanged effect/recovery/settlement suite | 30 passed |
| Unchanged Broker fairness suite | 5 passed |
| Combined exact-patch fixture | **91 passed, no failures/errors/skips** |

The H3 cases cover the real Broker/SQLite claim and Gateway dispatch/terminal receipt, other-window and monthly exhaustion, missing/future/stale/past/null observations, generation/source mismatches, same-mtime revocation, source drift before insertion, shared aliases and models, primary/child/application contention, strict pins, slot and cumulative reserves, original uncertain-request recovery, immutable binding, independent coverage, cross-reset liability, legacy migration, scope/policy removal, replayed observations and the real fixed policy parser. The original native offline boundary blocks provider, credential and unguarded subprocess effects. Provider/account/usage inputs and terminal receipts are synthetic.

Earlier development runs exposed missing fixture dependencies and incorrect release-call fixtures; those were corrected before this exact-input run. No failed run is relabeled green. The retained unmodified-source discriminator is intentionally red. These 91 cases are separate from #7142's previously accepted 36 selector/composition tests, which were not changed or rerun here.

## Remaining integration and acceptance gates

1. **Actual H2 producer contract.** [H2 is active](https://github.com/mastermindx-market-intelligence/Mastermind/issues/983#issuecomment-6706283300); [the interface request is recorded](https://github.com/mastermindx-market-intelligence/Mastermind/issues/983#issuecomment-6706341131). The current legacy cache does not supply this proposed `mastermind.account_capacity_observation.v1` envelope. Do not enable it from stale percentages or configuration labels. Actual product/workload entitlement, account identity, generation, units, complete binding windows and freshness must be proved.
2. **Enforced whole-operation bounds.** The existing execution/budget owner must prove the configured ceiling bounds all billable work in each upstream meter, including all steps and transport behavior. The fixtures do not certify a real worker/native application's bound. Unknown cost is not free; held #7116 unpublished repairs were neither reconstructed nor replayed.
3. **Scope completeness and coverage.** This bounded version requires equivalent shared membership for every required window within its account-level scope. Mixed per-window memberships must remain unqualified until the existing owner joins them explicitly. H2 must certify terminal/legacy/cross-reset coverage; terminal time alone is insufficient. Without that proof the algorithm is conservative and can stop useful admission. It bounds a scope scan at 4,096 rows and a window coverage list at 256 IDs; normal retention/coverage scalability is not yet production-qualified. No automatic pruning or fabricated acknowledgement is provided.
4. **Real publication serialization.** The final cache/config/policy digest recheck detects changes before insertion, but is **not** an atomic publication lock. #2182's compatible-policy publisher uses the native `active/.admission.lock`; Broker uses `broker/leases.lock`. The final owner must compose the existing lock/active-binding protocol so account/cache generation changes and claim commitment serialize, including outstanding terminal liabilities. Do not present double-reading as closing that race. Critical policy/account changes, draining and rollback remain with the original publication/native owners; rollback must preserve interpretation of existing H3 reservations.
5. **Native composition and release.** Consume this contribution with H2 and #2182 on the original #2175 generation, regenerate its exact member/manifests and run required CI. Existing genuine release/security holds remain. The current Web waiver removes blanket extra review ceremonies; it does not grant merge/release or permit replay of the previously refused #7142 review action. No self-approval, self-merge or duplicate review was performed.
6. **Installed and live proof.** Read back the selected native generation and actual qualified policy/account inputs. Use legitimate useful work under existing limits; keep race/exhaustion probes isolated. Retain selected/leased/dispatched/settled account equality, original lease and request identity, source/window/config commitments, provider terminal usage and the accepted useful result. Measure accepted useful work and allowance consumed on that account. One remaining-percentage snapshot does not prove optimal depletion.

The full H3 user outcome remains incomplete until these actual joins and the live canary are proved. Source publication, hosted CI, installation, provider proof and acceptance are separate states. Source delivery to #983/H6 is not pickup acknowledgement or durable execution START.

## Custody

Governing protected pin: `Mastermind@779fc3be9d07c366bf5b47c650b64e59fc6f3903`, Skillpack 1.0.1/bootstrap-major 1 compatible. Original Macro source base: `126c32af2f335ca25201dfc53f51745fc8c38613`, branch `sol/opencode-go-pool`.

Direct implementation was principal work on the cross-owner admission contract. The native adviser supplied bounded architectural judgment only; it made no edits, tests, calls, review approval or runtime claim. Paid-Fabric review refusal custody and the distinct #7116 publication denial were preserved. Active H2/#2182/#2175 writers, original unsettled effects, entitlement restrictions and the separate OMH preview were untouched.
