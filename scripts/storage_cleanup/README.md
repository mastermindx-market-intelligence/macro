# Deterministic SSD worktree retirement (M2 Studio)

This folder is the **source-of-truth implementation** for the existing host-local
`com.mastermind.ssd-worktree-reaper` service. It does not introduce a second
worktree registry, scheduler, agent, ownership system, or model-powered deletion
agent.

## Authority and rollout

- Canonical Macro GitHub main provides the classifier and protection policy.
  The host reaper loads one GitHub-SHA-pinned, blob-verified local release bundle.
  It must fail closed if a pin, manifest hash, policy, or required protection is
  unavailable; **never silently fall back to the parked Macro Dashboard checkout**.
- Git remains the worktree/branch source of truth. The existing Executive/Fabric
  operation owner remains responsible for session/effect completion. A clean
  checkout is not evidence that the original session has stopped.
- The reaper's scope is confined to verified-volume, registered Macro
  `agent-workspaces/{claude,codex,manual}/...` worktrees. Terminal, Mastermind,
  loose copies, `/Volumes/Mastermind/worktrees`, Web/Sol/review roots, personal
  photos, and backups remain report-only or outside this host-local reaper.
- This guard requires a **positive Git content proof** (ancestor of a freshly
  fetched remote main, an exact merged-PR head, or an origin branch containing
  the unchanged head with no open PR), no known open PR, minimum ratified age,
  no process use, a clean tree including untracked files, *no ignored files*,
  unchanged branch/ref/registration, and the exact helper lock reason (if locked).
- The extra guard only uses normal `git worktree remove`, never `--force`.
  It does not delete local branches. On refusal it restores a released helper
  lock. On an uncertain effect it writes to the existing reaper audit journal
  and blocks subsequent removals until the original target is reconciled.
- No filesystem cleanup is authorized by absence of activity alone.
  Human-driven roots are protected before classifying and again before
  deletion. No automatic cleaning of ignored content is allowed in this phase.

## Files and deployment

`ssd_worktree_reaper.py` is installed next to `ssd_retire_guard.py` under
`~/.local/lib/mastermind/storage-cleanup/`. Its `GC_RELEASE` is a local bundle
under `gc-releases/<pinned Macro main commit>/`, containing:

- `worktree_gc.py`: canonical classifier at the pinned Macro main commit.
- `worktree_gc.json`: matching ratified policy from that same commit.
- `manifest.json`: source identity and SHA-256 for each file.

Copy the reviewed source pair to the host only after the bundle is verified and
the hermetic test suite passes. Preserve the previous installed script. Initially
run `--apply --dry-run --json --no-sizes --max-remove 1` without automatic
deletion. Only after the target-version/source-control checks and independent
review pass should a bounded one-worktree canary be admitted. Expand cautiously
after verifying branch preservation and physical free-space change.

The launchd job should use the stable installed path; it must **not** import the
primary checkout's old `scripts/worktree_gc.py`. Its existing twice-daily
cadence is sufficient. Update the existing installed job in place, never
introduce a competing scheduler.

The host's release pin is intentionally sticky: a new GitHub main commit does
not silently replace live deletion rules. A future promotion must build and
verify a new bundle, run tests, update the pin, and verify installation separately.

## Test

```sh
/usr/bin/python3 -m unittest discover -s tests -p 'test_ssd_retire_guard.py' -v
```

Tests use isolated temporary repositories and a synthetic, hash-verified
release bundle. They verify positive removal and branch preservation, and that
dirty/untracked/ignored files, human roots, operator locks, missing remote
proof, active sessions, invalid volume identity, uncertain effects and
tampered classifier code all refuse deletion.
