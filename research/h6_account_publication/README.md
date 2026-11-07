# H6: compose H2/H3 with the original native publication owner

**State: SOURCE_CONTRIBUTION_VERIFIED / INSTALL_UNPROVEN. Parent H6 mission remains incomplete.**

The [H6 assignment](https://github.com/mastermindx-market-intelligence/Mastermind/pull/2175#issuecomment-6705879262)
requires useful primary and delegated Hermes execution through the existing Fabric,
physical-account capacity and OS paths. This contribution closes a bounded source
integration gap. It does not turn source tests into production acceptance.

Before this join, H3 checked source digests but its Broker transaction used a different
lock from native policy publication. H2's newer reader serialized its own cache writers
and retained an unresolved refresh marker, but H3 could still admit an old integer
capacity envelope while that refresh was pending or failed.

After this join, new native Broker claims and cooperating cache/policy publication use
the existing `ext/active/.admission.lock` through the SQLite commit or rollback. H3
refuses a pending, failed or terminally refused account observation. Original application
recovery, settlement and release remain available while publication is busy.

## Frozen inputs and composition

| Source owner | Exact revision and contribution |
| --- | --- |
| Native final composer | [Mastermind #2175, cd557dc05e26b70f2d8f56ad0da2df76a15d74ca](https://github.com/mastermindx-market-intelligence/Mastermind/commit/cd557dc05e26b70f2d8f56ad0da2df76a15d74ca). The sixteen H3 input blobs remain identical to its earlier qualified 39bd39aa preimage. The actual compatible policy publisher is an additional exact input. |
| Current H2 producer | [Mastermind #2215, 69ead1bdc1b7f6e1b62ef186d955d07cbd718dce](https://github.com/mastermindx-market-intelligence/Mastermind/commit/69ead1bdc1b7f6e1b62ef186d955d07cbd718dce), reader blob `d22c0b6b06b78bc85896abfe79c3b66a5f172c9f`, test blob `3366ea16629adf77e2e44de7c3b80a3d41e0f1e9`. Its newer refresh identity, refusal, reset and account-selection work is retained. |
| Accepted H3 contribution | [Macro #7142, ef95049fa2e1f8c981497c8a21b643fcbe59f25b](https://github.com/mastermindx-market-intelligence/macro/commit/ef95049fa2e1f8c981497c8a21b643fcbe59f25b), original patch SHA256 `a494cb84d86c5592527943d8bb119726949efec62919def65f75cd31701e6ef8`. Original account evidence, reservations, strict pins and settlement behavior remain included. |

[manifest.json](manifest.json) identifies **19 exact input files** and **five output
files**, including Git blob IDs, SHA256 and byte lengths. [native.patch](native.patch)
is the complete native/H2 composition against those declared inputs. Its SHA256 is
`06d4bb2d027c7807685c6c5a38a7526777fd0114d9cac02b3dbf6437dc375ffd`.

This patch already includes the accepted H3 source. **Do not apply both this combined
patch and H3's standalone patch to the same tree.** Compose the named H2 successor
on the original #2175 source, verify every manifest preimage, then apply this patch
once. If a declared input changed, reconcile that exact delta; do not force or fuzz an
incompatible preimage. The separate Macro selector and its historical 36-test result
are unchanged and are not counted as new proof.

Changed target paths are the native `candidate/lease_broker.py`, native
`candidate/quota_remote.py`, the H3 fixture topology, the new H6 test file, and H2's
`ops/native_fabric/grok47/quota_billing/quota_remote.py`. The two composed quota modules
have identical bytes. Existing H2 tests and the native policy publisher are unchanged.

## Runtime contract of the repair

The order for a new claim is the original Broker lock, **nonblocking** acquisition of
the existing native admission lock, the original SQLite transaction, commit or rollback,
then release of the publication lock and Broker lock. A busy publication owner refuses
before allocating a new lease. The Broker never waits for that lock while holding its
own lock. An outer caller already holding the native lock also receives a refusal;
installed caller-order qualification remains mandatory.

The native scope requires the existing canonical cache/Broker/account topology,
safe original directories and a regular, owned, single-link, empty mode-0600 admission
lock. It does not create a missing native lock or installation. Inode and directory
changes refuse. H2 standalone readers retain their existing `quota_cache.json.lock`
and bounded wait; that standalone mode is not proof of native atomicity.

H2 starts and completes its existing refresh identity in the original cache. Network
reads occur outside the publication lock. A completion carrying an attempt identity
must match the original pending marker even if an entry has been removed. The existing
H2 refusal/recovery semantics remain controlling; force and elapsed time do not clear
an unresolved marker or permission refusal. This adds no refresh queue, retry controller,
lease table or alternate result store.

Cache publication syncs the new file and containing directory. Alias paths publish to
the same canonical cache without replacing its symlink. A failure after replacement or
commit requires reconciliation of the original effect: visible postimage or a recovered
original turn can exist despite the caller receiving an error. No automatic retry is
added. Cleanup attempts all original descriptor releases even if one release fails.

The GLM parked-account check now receives the actual current configuration generation
from the existing H2 owner; an unavailable generation cannot silently disable that fence.
No credentials are serialized in the contribution or test receipts.

## Executed qualification

[qualification.json](qualification.json) is the machine receipt from
[qualify_h6_account_publication.py](../../scripts/qualify_h6_account_publication.py).
The script verifies exact inputs and outputs, patches disposable copies, and keeps the
incumbent native offline boundary active for every test run. No provider, credential,
native installation or selected runtime was used.

| Check | Observed result |
| --- | --- |
| Original H3 plus current H2, held native publication lock | New claim incorrectly succeeds; the new assertion fails as expected. |
| Original H3 plus current H2, pending refresh retaining the old envelope | H3 incorrectly selects `zeta-near`; the new assertion fails as expected. |
| Current H2 completion after removal of its original pending marker | Late completion recreates the entry; the new assertion fails as expected. |
| Current H2 directory durability fault injection | The expected sync error is absent; the new assertion fails as expected. |
| Composed native suite | **104 passed**: original 91 H3/admission/effect/fairness cases plus 13 H6 cases. |
| Current H2 suite over the composed module | **43 passed**, unchanged test bytes. |

Total positive proof is **147 passed**, with four separately observed expected-negative
controls. Source-only evidence includes the actual compatible policy publisher being
excluded before claim commit, a later claim retaining the new policy digest, cache
publication exclusion, missing/replaced/unsafe lock refusal, alias binding, rollback
under the held lock, and recovery of exactly one original committed turn after a close
error. Assertions were not weakened to make the earlier composition pass.

Reproduce from exact source checkouts:

```bash
python3 scripts/qualify_h6_account_publication.py \
  --native-root /absolute/path/to/Mastermind-cd557dc0 \
  --h2-root /absolute/path/to/Mastermind-69ead1bd \
  --receipt /absolute/path/to/h6-qualification.json
```

The original H3 patch must remain at the sibling
`research/h3_expiration_account_admission/native.patch`, as it already is on this carrier.
The native and H2 inputs may come from one already-composed checkout only when all
nineteen hashes match. Test count and expected failure conditions are checked explicitly.

## What remains unproven

The lock proves exclusion only for participating publishers. It does not establish
atomicity against an account/configuration writer that ignores that lock. Actual native
caller lock order, configuration publisher participation, mixed-version writers,
selected generation, installation and enforcement therefore remain release gates.

H2 percentages are not H3 exact integer allowances. The intended accounts still need
authoritative per-window units, scope and generation, original observation clocks,
settlement coverage and enforced whole-operation ceilings. A `budget_ref` is evidence
of a reference, not enforcement. Unknown prices, missing windows and null reset clocks
must remain truthful. No conversion of percentages into invented capacity is introduced.
H3's equivalent shared-window membership and terminal/cross-reset retention limits also
remain explicit until their original owners are qualified.

| Original H6 acceptance | Status after this contribution |
| --- | --- |
| Useful primary turn and harmless native tool with actual identity/usage | Still requires installed APPLICATION execution and accepted useful output. |
| Delegated worker START, terminal result and parent consumption | Still requires the original #2147/#2184 real path. |
| Shared physical limit across aliases/consumers; inference versus tool occupancy | Existing synthetic H3 coverage retained; real physical proof remains open. |
| Intended 3 GLM + 3 Go accounts and safe use of independent accounts | Entitlement, enrollment and account-specific qualification remain open. |
| Truthful all-busy/exhausted handling without unauthorized downgrade/spend | Source refusal coverage improved; live integrated proof remains open. |
| Expiry choice, same-account claim and settlement, reserves | H3 source retained and publication join repaired; actual producer/usage proof remains open. |
| Actual refresh/reset plus unknown/edge behavior | H2's dated GLM reset evidence stays separate; no new live reset is claimed here. |
| Revoke, CAS, drain, interruption, crash and original recovery | This contribution adds native-lock/CAS/recovery fault proof; whole installed transition remains open. |
| Enforceable account no-overage/hard budget | Still requires the actual execution-owner ceiling and upstream meter contract. |
| Real OS routing/capacity states and stream/buffer bounds | H5 source and actual browser acceptance remain separate. |

## Custody and exact continuation

The active #2175 composer remains the only final native carrier; Macro #10740 remains
the application consumer carrier. No root branch, live source checkout, native generation
or service selector was modified by this contribution. At recovery, #2175's protected
merge still had the original builder follow-up and an unreconciled original CI task.
Original J process95731 remains UNKNOWN. This work does not retry, replace or collect
those held effects, the refused #7142 review, or #7116 unpublished source.

The principal performed and self-reviewed the cross-owner contract repair under the
attended Web waiver. The bounded native advisor supplied reasoning only, ran no tools
or implementation labor, and received ACCEPTED/STOP. That is not a Fabric worker return,
a distinct technical approval, or a GitHub APPROVED event. No review/release rule changed.

**Next primary action:** the currently assigned #2175 integrator consumes the frozen
composition after reconciling its live builder/CI effects, regenerates the original native
manifests and satisfies required exact-head CI. Then qualify the original installed
caller/configuration participants and one lawful account/whole-operation budget before
running the first useful H6 primary vertical. The source packet does not authorize
activation, bypass existing release holds, or require completion of every account before
the first properly qualified vertical. Original H2/H3 and H6 carrier links retain the return.
