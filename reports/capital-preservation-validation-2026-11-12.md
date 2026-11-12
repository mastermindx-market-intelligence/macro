# Capital preservation-test qualification

## Result

**84 distinct existing cases qualified, zero errors or skips in the accepted cases.**
The two original source assertions reproduce before the correction. The complete
60,018-record ledger validates; its first 1,258 records still match the original
immutable receipt. The policy/watch suites exercise the actual native renderer
with the original production blocks and the approved data-isolation fixture.

Source: `e7f8565ca26b74b9ae0d637b336e9985d513ff9d`.
Only two test files change. Production, data, telemetry, historical hashes,
companion tests, dependencies, CI enrollment and release controls are unchanged.

## Corrections

### Preserve the migration's fixed ledger prefix

[The original migration #4600](https://github.com/mastermindx-market-intelligence/macro/pull/4600)
commits to 1,258 ordered records. Later append-only growth and
[byte-exact continuation parts #9146](https://github.com/mastermindx-market-intelligence/macro/pull/9146)
do not change that receipt.

The test now selects that fixed 1,258-record prefix, requires at least that many
records, and still validates every current record. It retains original SHA-256
`73631e1f83f1d5deb4ee240680534fe4764201e908091e6fa8b315a6277a16e3`.
It does not adopt the current full-ledger hash as a new historical authority.

| Actual committed input | Records | Bytes | Git blob |
| --- | ---: | ---: | --- |
| `source_manifest.jsonl` | 43,093 | 102,358,202 | `713e80541c6088c4a4a37b98197206873f34ede1` |
| `source_manifest.part-0002.jsonl` | 16,925 | 40,546,719 | `3831a5840a93e4a10949af7f747c5512b4e80af5` |
| **Total** | **60,018** | **142,904,921** | Both full objects verified |

Both actual parts were present. The absence-based skip did not execute.

### Preserve the policy-watch freeze and its qualified isolation fixture

Merged [#9790](https://github.com/mastermindx-market-intelligence/macro/pull/9790)
adds exactly one 227-byte autouse fixture that isolates policy data. Removing only
that exact addition reconstructs the original 8,776-byte companion suite.
The test now requires one exact occurrence and checks the reconstructed original
against unchanged SHA-256
`c08d2fa7bd45dd1d4338787936cf490c26b70f21f3891c988c01c9e18b564f84`.

The original template and builder watch-block hashes remain unchanged:
`8fee91f5e6059fd427b897c69259917d544662e9862996a7009fcf22a7ef3736`
and
`57bf1a0e4244416c592abb09fe3d033b7f48d520d90128080f1c90f82e7bee8b`.
All original watch assertions and the rendered old/new chip parity check remain.

## Native execution

| Existing suite | Distinct passing cases |
| --- | ---: |
| Source-ledger I/O | 21 |
| Capital policy projection | 53 |
| Companion policy-watch projection | 10 |
| **Total** | **84** |

The two exact historical failures reproduce on the original tests. The candidate
qualified 44 cases, then 3 and 37 more after completing missing native render
inputs. The accepted cases were retained without replay. All 84 identities are
distinct and fully accounted for in the machine evidence.

Execution uses the owning `capital-structure-intelligence` job's declared
**Python 3.12** and dependencies, normal repository conftest, unchanged authority
startup checks, source hashes and data/site guards. Test network attempts are zero.

The isolated checkout initially lacked schema files; the initial Python 3.14
interpreter also failed the unchanged authority check on its slice constants.
Those collection attempts terminated before test bodies. Source-bound schemas
and the declared Python 3.12 runtime resolved those local setup gaps. The complete
Jinja dependency graph and every asset declared/copied by the actual builder were
then materialized from main. No production code or guard was changed to obtain
the result. Original failed attempts, commands, input hashes, logs and outcomes
remain in the evidence.

## Publication custody and scope

At the final 04:42:44 UTC readback, main remained unchanged. The two source
preimages are exact, both new report paths are absent, and the bounded
qualification covers 601 complete inventories plus 56 exact head/merge-base
pairs, with zero target overlap or unresolved comparison. Seven new/moved heads,
including separate PR #11111, have complete disjoint inventories. This is
target-path custody, not ownership of neighboring programs.

[Complete machine qualification](capital-preservation-validation-2026-11-12.json)
contains the source/historical receipt bindings, actual input hashes, all native
execution records, full logs, verifier code, exact two-file diff and custody.

This is focused native acceptance for the three named suites. It does not claim
full scheduled DATA execution, browser or deployment proof, or closure of #5979.
Old #7006 UNKNOWN and every other held/refused effect remain on their original
carriers. No original scheduled run or accepted proof was replayed.

Protected procedure pin:
`c42e812e4a754d7a95efd954441d3f01607a7fb5`.
