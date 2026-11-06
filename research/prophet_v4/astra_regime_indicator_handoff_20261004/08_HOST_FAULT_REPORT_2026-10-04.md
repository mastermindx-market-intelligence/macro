# 08 — Host-fault report, wave 1 build hosts (seat f273dd7d, 2026-10-04)

Status: DRAFT written 06:55Z while wave-1 repair rounds run on host mb; the D0 r3 outcome
and the final per-round host table are filled in at wave close. Every claim below names the
observation that produced it; nothing here is inferred from a host's name or from hosts.json.

## 1. What happened

| Host | Role in wave 1 | Observation (UTC, 2026-10-04) | Effect on lanes |
|---|---|---|---|
| mini2 | MiniMax-M3 build host for rounds r0–r3 (A1, B1, C1, C2, D0, E, F1); D0 r3 (rs_20261004T051657Z_81412, lease b6face03ca9a) was RUNNING there when access was lost — its poller concluded 07:20Z `DONE rc=124 signal=effect_unknown reason=transport_deadline_without_rc`, `RSYNC_FAILED rc=255 (remote rc=124); remote artifacts preserved` | `ssh mini2`: `Permission denied (publickey,password,keyboard-interactive)` for every local key, IPv4 alias included, host key unchanged; first seen between 05:21Z (D0 r3 launched OK) and 06:12Z; two other sessions' launch logs show the same refusal — fleet-wide, not seat-local | E r1 launch died `REMOTE_SETUP_FAILED rc=255` (queue logged UNKNOWN, no retry); D0 r3 (`rs_20261004T051657Z_81412`) running on the host when access was lost — `POLL_TRANSPORT_FAILED rc=255` on every poll since; state EFFECT_UNKNOWN until the poller returns a record or dies |
| m2 (seat) | local lanes | `sub.sh minimax` refused by policy: `LOCAL_SEAT_REMOTE_REQUIRED host=m2 pool=minimax family=minimax local_only=grok,ocfree`; grok pool `max_active=2`, fleet-shared (`LANE_ADMISSION_REFUSED … active_count 2`) | no local MiniMax fallback; grok reviews queue behind the fleet |
| m1 | candidate replacement | reachable; `git` fails `Unable to read current working directory: Interrupted system call` (EINTR); no pyarrow; data sparse | unusable without operator repair |
| mini1, mini3 | candidates | reachable; no repo, no pandas, no MiniMax config | unprovisioned |
| bmb, bm1, pc | hosts.json entries | hostnames unresolvable from m2 | stale entries |
| mb | candidate replacement (06:50Z–07:11Z) | reachable at first (load ~7, 12 cores, 129 GiB free); setup #1 `worktree_sparse.py full` → `git sparse-checkout disable` timed out at 300 s (yahoo=0 baskets=0; killed before it could write READY); setup #2 data rsync from host2 died rc=255 at 2.79 GB (`Read from remote host 100.105.71.55: Operation timed out`); Tailscale then showed `offline` | no lane was ever launched there; the shared `~/lanes/repos/macro` main tree was never mutated |
| host2 (m2, `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/astra-host2-052e02d-690b56cac98b57f7`) | FINAL build host for E r1, C1 r4, B1 r4, C2 r2, F1 r4 and the D0 r3 rerun | detached at `052e02d085b0` (ancestor of origin/main) with full data (yahoo=6432, baskets=2812), `git status -- data` clean, results/* byte-identical to the seat worktree (7/7 result.json shas); grok-4.6 lanes via `ext/sub.sh grok` under `POOL_TASK_CLASS=fix_build` with an escalation reason; python3 3.14.7 / pandas 3.0.5 / numpy 2.5.2 / pyarrow 25.0.1 / scipy 1.18.0 / pytest 9.1.1 — the environment grok reviewers had already reproduced r2/r3 numbers under | the whole remaining wave runs locally behind a dependency-aware sequencer (`grok_build_queue.sh`, max 2 concurrent, blocked-propagation) |

## 2. What the seat did

1. Pinned every round to tracked inputs at commit `052e02d085b0` (mini2's head; ancestor of origin/main). All hashed inputs are tracked files, so any full checkout at that commit reproduces the inputs byte-for-byte (`git show 052e02d085b0:<path>`); reviewers verified this.
2. Built a dedicated detached worktree on mb — `~/lanes/repos/macro-astra` at `052e02d085b0`, `scripts/worktree_sparse.py full` applied — and never touched mb's shared `~/lanes/repos/macro` main tree. Program dir + current results rsync'd in; preserved prior rounds shipped read-only to `~/lanes/astra_prev/`.
3. Repointed every queued packet from `~/lanes/repos/macro` (mini2 path) to `~/lanes/repos/macro-astra` and marked the checkout DETACHED (never checkout/pull/commit).
4. Required every round to record `provenance.host` (host, python, pandas/numpy/pyarrow/scipy, pytest) in result.json and RESULT.md, and to re-hash inputs at LOAD and END (abort INPUT_CHANGED). Rounds stay on one host; the r2 C1 reviewer measured cross-host coefficient drift at ~1e-14, so a host change is a provenance fact, not a numeric one.
5. Left D0 r3 alone: its remote_sub poller is the durable watcher; one D0 r3 rerun on mb is authorised only after that poller dies without a record (never two live runs of one lane).
6. Local fallback host2 (`/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/astra-host2-052e02d-690b56cac98b57f7`, detached at `052e02d085b0`, full data) exists for grok / oc-free lanes only.

### 2a. Addendum 07:30Z — second host loss and the local fallback

- mb was lost mid-transfer (above). Rather than a third remote host, the seat moved every remaining round to grok-4.6 on the seat's own pinned checkout host2 (table row). This is the verified-eligible local route (`local_only=grok,ocfree`), not a name-inferred one; each lane is admitted by the pool's `ECONOMIC_POLICY {"allowed":true}` line and logged with its `GROK_RUN_ARTIFACTS` path.
- Each repointed packet carries a HOST + COMPLETION block: host and library versions go into `result.json` `provenance.host`; a frozen number moving by more than 1e-9 under this environment is a STOP-and-report DEVIATION, never a code change; the lane's last act is the empty sentinel `results/<LANE>/DONE` the seat's watchers key on. Prior rounds are read-only under the seat scratchpad `results_prev/<LANE>_r<k>/` for leaf-diffs.
- D0 r3 is rerun ONCE on host2, queued last, under a pre-declared rule: the host2 run is the record; the mini2 artifacts, if ever recovered, are a cross-host reproduction check only. This is not a blind retry — the lost run touched no shared state the rerun touches, and its own carrier concluded EFFECT_UNKNOWN with artifacts preserved on an unreachable host.
- Setup-script lesson (recorded): a host setup must gate READY on an explicit data check (file counts), never on the ssh exit code alone — setup #1 would otherwise have launched the whole wave on an empty tree.

## 3. What this costs the program

- Wall-clock: ~1 h between the mini2 loss (≤06:12Z) and the first mb admission (mb setup 06:44Z → READY), plus the mb blob fetch.
- Evidence: D0 r3 may end as a host-fault PARTIAL; if so it is reported as `EFFECT_UNKNOWN → rerun` with the mini2 run id, never as a lane result.
- No numeric effect: inputs are pinned by sha; a round whose LOAD/END hashes differ aborts.

## 4. Operator items (not seat acts)

- mini2: sshd / authorized_keys / key rotation check — every fleet key was refused at once, so the host, not a key, changed.
- hosts.json: `bmb`, `bm1`, `pc` do not resolve; `m1` needs pyarrow and a repaired cwd (EINTR); `mini1`/`mini3` need repo + pandas + MiniMax config before they can be counted as capacity.
- mb: pytest was user-installed by this seat (`python3 -m pip install --user pytest`) — make it part of provisioning.

## 5. Falsifier / so-what

Falsifier: if any wave-1 round's result.json `provenance.host` names a host whose `shasum -a 256 -c hashes.txt` is not 0 non-OK, the pin failed and that round is void.
So-what: a MiniMax host loss mid-wave is survivable in ~1 h **only** because every lane pins tracked inputs at one commit and writes host provenance — keep both rules in every future packet.
