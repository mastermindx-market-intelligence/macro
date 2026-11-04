## Result

**No source-backed fix for the recorded parent focus-restoration ordering defect is present in the latest Terminal `master` I observed.** The current host and message-contract files are exactly the same as the tested parent pin. Surrounding Shared Shell changes add presentation ownership and explicit user-triggered focus behavior, but they do not add post-exposure restoration authorization or cancellation ordering.

`master` advanced during this check:

| Role | Commit |
|---|---|
| Tested, unmodified parent | `e45bde2cac07ac3b29285ff70c40d68900fad62c` |
| Initially supplied current head | `516d0519ca39d4be3ef186d65261598dfc5f6042` |
| Fresh observed protected `master` | **`4615f80dc8a6855041103c404e4457a6597445f0`** — commit timestamp `2026-10-22T06:31:37Z` |

The first comparison is 83 commits ahead; the final advance is one additional commit. The [final one-commit comparison](https://github.com/mastermindx-market-intelligence/mastermind-terminal/compare/516d0519ca39d4be3ef186d65261598dfc5f6042...4615f80dc8a6855041103c404e4457a6597445f0) contains exposure-map implementation, tests and evidence changes, with no Shared Shell host, runtime, protocol, AppShell or frame-CSS changes.

## Exact relevant source identities

These are **Git blob SHAs**, not SHA-256 digests.

| File | Tested pin `e45bde2…` | Current `4615f80…` | Finding |
|---|---|---|---|
| `terminal/components/chrome/shared-shell/LegacyPageHost.tsx` | `0295d2c9e8afa642ff441e9eeed2c3e1a995765e` | `0295d2c9e8afa642ff441e9eeed2c3e1a995765e` | **Byte-identical**; directly fetched both versions. |
| `terminal/lib/sharedShellContracts.ts` | `b2d19bc0f90c6d7382e9f669b9be254c4ff683ba` | `b2d19bc0f90c6d7382e9f669b9be254c4ff683ba` | **Byte-identical**; directly fetched both versions. |
| `terminal/components/chrome/shared-shell/SharedShellRuntime.tsx` | `25ac6f647da43b8c32a998723a6030c27d8b768c` | `1b4f5f5c52302dbd0736e0d51273b472909bf4a1` | Changed to consume the shared presentation provider. |
| `terminal/components/chrome/AppShell.tsx` | `09580cdae29f9d97ea932a0f03c86f4531e238f4` | `c60bf2a4397f9d88ca61671215f5a109a484d88f` | Adds presentation provider, primary-content skip action and related shell wiring. |
| `terminal/components/chrome/shared-shell/shared-shell.css` | `7e6d752dc47bef48cacffe6e6ab21843a4d2f08c` | `3fcc7ec2374736dc3dcd6c37a1121d49069b7983` | Adds controls and focus-visible styling; frame and content-container rules remain unchanged. |
| `terminal/components/chrome/shared-shell/SharedShellPresentation.tsx` | Absent | `b7cf52ee808ba4426fab15a1240de2507e8f0382` | New theme/locale owner; no focus-restoration, exposure acknowledgement or restoration-cancellation code. |

The last three current identities were fetched at `516d0519…` and remain applicable through the complete final one-commit comparison. The host, runtime and contracts were also fetched directly at `4615f80…`.

## Why the ownership defect is still present in source

The current [LegacyPageHost](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/4615f80dc8a6855041103c404e4457a6597445f0/terminal/components/chrome/shared-shell/LegacyPageHost.tsx) retains the same sequence:

1. `initialize()` posts `INIT`, including the saved `restore` state.
2. The parent receives `READY` and calls `setStatus("ready" | "restricted")`.
3. The iframe becomes visible and loses `inert` only when that state is reflected in its rendered attributes.
4. There is no parent message authorizing restoration after that exposure.
5. `VISIBILITY` continues to report `document.visibilityState`, not iframe exposure or focus authority.

The [unchanged contracts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/4615f80dc8a6855041103c404e4457a6597445f0/terminal/lib/sharedShellContracts.ts) still define parent messages only for `INIT`, `CONTEXT`, `LOCATION_ACCEPTED` and `VISIBILITY`. Protocol remains `mmx.shared-shell.v1`; bridge and document versions remain `20261018.1`. No new restoration grant, acknowledgement, cancellation or ordering token appears.

The latest recorded host-specific commit is **`4717376dc582f69ffadc17026dd2eb99c9cb60fb`**, “fix(shared-shell): synchronize legacy routes after history commits,” dated October 19. That host implementation is already present in the tested `e45bde2…` bytes.

### Relevant intervening PR

[Terminal PR #1063](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1063), **“Complete Shared Shell investigation and member workspaces,”** merged as **`8196744cd837cbfd5924338439bd9a3f1f264c5c`** at `2026-10-21T21:48:49Z`.

Its relevant changes are:

- `SharedShellRuntime` now obtains `context` and `requestContext` from `useSharedShellPresentation()`.
- The provider owns theme/locale synchronization and system-aware Auto theme.
- `AppShell` adds a skip action whose explicit click handler focuses a visible main landmark.
- Search and tools-dialog focus handling serve those user-triggered interactions.

Those changes do not amend the legacy restoration handshake. The skip action is not invoked on history restoration, and it does not authorize focus inside the child frame.

## Narrow next step

**Keep the existing Draft Tools publication scoped as planned, then treat parent focus restoration as a separate host–bridge integration change.** There is no discovered merged fix to adopt instead.

For that follow-up, first reproduce the retained history journey against a deliberately pinned current Terminal head, instrumenting iframe exposure/inert state at the actual child `focus()` call. Then implement and independently verify the already recorded ordering requirement: one-shot restoration authority for the current frame generation and history entry after exposure, invalidated by newer parent or child user intent, with an explicit compatibility decision.

The source comparison **does not prove that a browser run on `4615f80…` will reproduce the failure identically**. It establishes that the missing ownership guarantee has not been repaired in the inspected current source. Preserve the existing nonzero baseline result until actual replacement runtime evidence exists.

Local evidence read:

- `research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/PARENT_FOCUS_FOLLOWUP.md`
- `research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/PARENT_FOCUS_BASELINE.md`
- `research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/PARENT_REPOSITORY_IDENTITY.json`

No workspace/source changes, process execution, tests, comments or Slack messages were made.
