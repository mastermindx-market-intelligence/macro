---
key: MINI-LANE-STORAGE-ADMISSION-BYPASS-LOW-SWAP-WATCHDOG-PANIC
claim: >
  The accepted Meta-CEO B external lane runtime could strand a 256 GB Mac mini
  below its canonical 50 GiB work-allocation floor because Mini2's live
  hosts.json admitted two lanes down to 30 GB and remote_lane_v8.sh forced
  LANE_WT_ROOT=$HOME/lanes/wt, causing lane2.py to use plain git worktree add
  instead of the installed mmx-mini-worktree storage owner. On 2026-10-03
  Mini2 reached low-swap pressure, emitted four Jetsam events with Codex
  (Renderer) as largestProcess, then panicked on a watchdogd 94-second
  no-check-in timeout and rebooted into FileVault preboot. The same host later
  could not start Desktop Commander because its state rewrite returned ENOSPC.
falsifier: >
  Reproduce a lane through the accepted B-kit on a Mini whose canonical
  mmx-mini-worktree census reports free_bytes below its 50 GiB floor and show
  that the lane creates/hydrates a worktree or invokes a provider without a
  STORAGE_GUARD refusal; or show that Mini2's Oct-3 panic/Jetsam evidence does
  not contain low-swap kills, Codex (Renderer) as largestProcess, and the
  watchdogd 94-second timeout. Either result refutes this discovery.
so_what: >
  Mini lane admission must compose with the existing mmx-mini-worktree storage
  owner instead of maintaining a weaker parallel threshold. The live B-kit was
  hardened on 2026-10-04 so Mini2 uses max_active=1, min_free_gb=50 and the
  canonical worktree_root identity; remote_lane_v8 ships storage_guard.py; and
  lane2 calls the installed helper's read-only census before mint, after
  hydration, and before every provider execution/retry/spill. The guard fails
  closed on low space or floor drift. The existing worktree creation route is
  intentionally unchanged pending a separately reviewed allocator migration.
  Mini2 and Mini4 are currently below 50 GiB and therefore remain online but
  ineligible for new lane/provider work until capacity is reclaimed.
kind: landmine
verified_at: 2026-10-04
verified_by: >
  Live Mini2 incident recovery plus M2 B-kit canaries. Mini2 exact evidence:
  Oct-3 22:38 reboot; four Jetsam events at 22:24:55, 22:27:37, 22:29:51 and
  22:32:04 with low-swap kills and Codex (Renderer) largestProcess; panic report
  watchdog timeout because watchdogd stopped checking in for 94 seconds;
  post-unlock Desktop Commander runner initially failed ENOSPC. Canonical
  mmx-mini-worktree census proved 50 GiB floor / 70 GiB resume and refused a
  real guard canary at ~26.8 GB with exit 78 and no worktree/provider effect.
  Live kit storage-guard regression slice passed 52 tests; the queue hot-reloaded
  from active<2/free>30GB to active<1/free>50GB and, after the incumbent
  LaneLease admission reaped one proven-stale post-panic marker, reported
  active=0 and GATE_WAIT at ~24.9 GB free.
scope:
  - macro
  - mastermind
  - subagent fabric
  - host mini2
  - host mini4
  - ~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08/ext
confidence: verified
---

## Failure chain

The outage was not a generic network or Desktop Commander failure. Mini2's
normal operating system remained recoverable through the home gateway, but the
panic reboot stopped at FileVault preboot. In that state normal per-user
authorized_keys, Tailscale, Screen Sharing and user LaunchAgents are unavailable
until an authorized human unlocks the encrypted data volume. After attended SSH
unlock, SSH/ARD returned immediately; Tailscale returned; Desktop Commander
returned after disk pressure was relieved enough for its state file write.

The trigger was local resource pressure. Immediately before the reboot macOS
recorded repeated low-swap Jetsam events; the largest process named in each was
Codex (Renderer). The subsequent panic was a watchdog timeout. Mini2's APFS Data
volume was ~95 percent full, and after unlock Desktop Commander produced an
ENOSPC write failure. Rebooting cleared VM/swap, which made the machine appear
temporarily healthier without fixing the storage admission defect.

## Why previous hardening missed it

The Mini storage owner was already correct:

- installed wrapper: `~/.local/bin/mmx-mini-worktree`;
- schema: `mastermind.mini_worktree/v1`;
- floor: 50 GiB;
- resume: 70 GiB;
- canonical hot root: `~/.mastermind/worktrees`.

The accepted B-kit lane path bypassed it. Mini2's registry entry had
`max_active=2`, `min_free_gb=30`, and no canonical `worktree_root`.
The remote carrier exported `LANE_WT_ROOT=$HOME/lanes/wt`, and lane2.py
explicitly took a plain-Git worktree branch whenever that variable was set.
Thus the fleet had two storage admission laws, with the lane path weaker than
the Mini storage owner.

A second stale-state issue appeared after the panic: `host_queue.sh` counted a
JSON active marker for a PID that no longer existed. The existing LaneLease
admission owner, not an ad-hoc rm, was used to take the marker lock, prove it
unlocked/non-held, and reap exactly that stale lease. Queue observation then
changed from active=1 to active=0.

## Installed repair

The accepted runtime remains the native B-kit. This record is evidence, not a
second source tree.

Live kit:
`~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08/ext`

The 2026-10-04 repair:

- Mini2 registry: `max_active=1`, `min_free_gb=50`,
  `worktree_root=/Users/mini2/.mastermind/worktrees`;
- `storage_guard.py`: read-only adapter to the installed
  `mmx-mini-worktree census`; strict schema/floor validation; typed fail-closed
  refusals; no persistence or allocation authority;
- `lane2.py`: storage guard at `pre_mint_<kind>`,
  `post_hydration_<kind>`, and `pre_exec_<step>`; the pre-exec placement is
  inside the actual executor function, so retries/spills are rechecked;
- `remote_lane_v8.sh`: reads the optional canonical Mini worktree-root
  identity separately from the legacy shared host-policy parser, ships the
  guard to the remote host, and enables it only for canonical Mini roots;
- queue policy remains owned by `host_queue.sh`, which hot-reloaded the new
  Mini2 values without a daemon restart.

Installed live hashes after the repair:

- `lane2.py`:
  `4e366d86fe1d05e3a11d1815a9c81617427ec46c68e3758f4324848a5b9f7d24`
- `remote_lane_v8.sh`:
  `c0eb3b8461573a7c4459fac66a4d57be6f390628e5229b2b96ac908f371dd3e6`
- `storage_guard.py`:
  `917ab90f5656a9ce6c5cf0ff11175f9b062ff5725d0fdac7e3ae71625c448cdd`
- `hosts.json`:
  `edaf8569e2dece063d7759782200696535828c91a602043f0b6245f817a5ef2c`

Rollback copies of the two replaced runtime scripts were retained in the live
kit with suffix `.before-storage-guard-20261004`.

## Acceptance evidence

- staged storage guard unit tests: 9/9 pass;
- live selected runtime regression slice: 52/52 pass;
- Python compile and bash syntax checks pass;
- existing shared host-policy parser identity remains intact;
- real Mini2 guard canary while below 50 GiB:
  `LANE_ADMISSION_REFUSED STORAGE_GUARD_LOW_SPACE`, exit 78, helper census
  `effect=NOT_APPLIED`;
- queue hot reload:
  old `max_active=2, min_free_gb=30` -> new
  `max_active=1, min_free_gb=50`;
- queue after stale-lease reconciliation:
  `active=0`, `free_gb~24.9`, `GATE_WAIT`;
- every Mini currently has the installed `mmx-mini-worktree` helper at the
  50/70 GiB policy. Mini1 and Mini3 are above the allocation floor; Mini2 and
  Mini4 are below it and are intentionally gated from new lane work.

## Boundaries

This repair does not automate FileVault passwords, disable FileVault, create a
new cleanup daemon, invent a second worktree owner, or delete dirty worktrees.
The existing Mini worktree adapter remains the storage authority. The B-kit
continues using its incumbent worktree creation route, now fenced by the
canonical storage oracle. A future allocator migration must reconcile branch,
store, sparse-checkout and cleanup custody explicitly rather than being folded
into an incident repair.
