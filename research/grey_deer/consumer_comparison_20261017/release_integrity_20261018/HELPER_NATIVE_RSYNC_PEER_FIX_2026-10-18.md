# Native fixture portability correction

**18 October 2026 UTC · Test harness only · Native rerun pending**

The parent-reported native owning pytest run exposed a fixture portability error before the helper could be evaluated: Apple's `/usr/bin/rsync` locates its local peer by looking up `rsync` on `PATH`. The real rsync process inherited the fake transport directory first, so its peer re-entered the interception shim with server arguments. The existing path guard correctly refused those arguments. The parent independently owns the separate absent Macro vendor dependency affecting the five application-import tests.

The native run occurred 07:41:55–07:42:25 UTC, exit 1. Its parent-bound log is 91,721 bytes, SHA256 `fcf4e967a0890eba39bddf6114b987de3d28a0a112425049deb5b7ce4dd96396`. This artifact records that result as supplied by the parent; the subagent did not execute native pytest.

## Exact correction

Only `_fake_transport` in the existing test owner changes. A private fixture directory named `rsync-peer-bin` contains a single `rsync` symlink to the resolved real binary. After the existing source and destination path checks, only the real local rsync subprocess receives this directory prepended to its environment's `PATH`. Fake SSH, systemctl, curl and the other interceptions remain behind it on the same path. The parent helper process still resolves its primary `rsync` calls to the shim. No host/path guard is weakened, no Darwin skip or fake rsync implementation is introduced, and no production helper code changes.

| File | Bytes | SHA256 |
|---|---:|---|
| `candidate/scripts/deploy_code_to_vps.sh` — unchanged | 20,370 | `1ebfd44db982d73f7f9d507109fa3983ba65cc948e8afe9fe697589d712728a8` |
| `candidate/tests/test_deploy_provenance.py` — fixture correction | 40,161 | `d9dd66255444a70ba2160d30a2b62e540bcbc6620736030152cbef50c7ab7f59` |

The exact [narrow diff](HELPER_NATIVE_RSYNC_PEER_FIX_2026-10-18.diff) is retained. The preceding pair (`1ebfd44d…` / `a4ed6d45…`), its final manifest and its 44/44 full standalone receipt are preserved under `pre_native_candidate/`. Earlier red receipts and the independent semantic review of that pair remain unchanged. The previous full implementation report describes that preceding pair; this note identifies its test-only successor.

## Focused evidence and remaining gate

Two existing standalone controls were executed against the new fixture using the same standard-library driver and confined local rsync 3.2.7:

- [HELPER_RSYNC_PEER_FORWARD_CONTROL_2026-10-18.json](HELPER_RSYNC_PEER_FORWARD_CONTROL_2026-10-18.json): verified stop before snapshot/source copy and successful new release, 1/1 passed.
- [HELPER_RSYNC_PEER_RESTORE_CONTROL_2026-10-18.json](HELPER_RSYNC_PEER_RESTORE_CONTROL_2026-10-18.json): failed copy followed by rollback preserving the newer excluded nested `.env`, 1/1 passed.

All test function ASTs remain unchanged; the delta is contained in fixture construction and its embedded transport shim. No first-party application module, real SSH, network or production service was invoked. The full 44-case cloud run was not repeated, and its prior receipt is not relabeled as a test of these new bytes. The focused controls validate that the change retains the existing local transfer and restore behavior; **the native owning pytest rerun remains the gate for the observed Apple peer behavior**.

Independent reviewer `forward_activation_review` has the exact new test hash and diff for the small-delta review. No production or release acceptance follows from this fixture correction.
