# Ubuntu fleet storage pressure guard — bounded continuation plan

**Workstream:** `WS:FLEET-STORAGE-LIFECYCLE` (reuse the existing Agent OS source; no new workstream).
**Protected procedure pin:** `mastermindx-market-intelligence/Mastermind@19cb00cfed26b68f0a8a5cdc0f2f1a9463a3feec` (skillpack 1.0.1).
**Owning repository:** `mastermindx-market-intelligence/macro`.
**Previous cumulative handoff:** `agentos/handoffs/FLEET-STORAGE-LIFECYCLE-2026-09-30.md`.
**Recorded:** 2026-11-01, local Ubuntu host time (America/Los_Angeles).

## Outcome and proof

Keep each Ubuntu host's root filesystem below critical admission pressure while preserving the last source copy, active and paused worker sessions, dirty worktrees, cold storage, and the existing Git/CI owners. A host installation is not a reviewed source release. A scheduled timer existing is not proof that it fired after installation.

The production Macro CI resource guard blocks new runner admission when root filesystem use is at least 85% **or** available space is under 100 GiB. This new Linux sentinel measures *both* limits, provides an earlier warning when usage reaches 80% or free space falls below 180 GiB, and categorizes severe pressure at 92% or under 35 GiB. It does **not** bypass or adjust the actual admission guard.

## Task tree (editorial, not Executive Jobs)

- **FSG.P1 — Disk census and selective recovery (accepted host evidence):** The 2026-11-01 on-host fleet cleanup on Ubuntu0–3 was verified and recorded at each `~/.mastermind-evidence/fleet-storage-triage-20261101.txt`. Preserve those logs and the reconstruction manifests. Ubuntu4 had adequate headroom.
- **FSG.P2 — Pressure monitor implementation (implementation complete, review owed):** `scripts/ubuntu_storage_guard.py`; six standard-library tests `tests/test_ubuntu_storage_guard.py`; systemd service/timer. Atomic latest-status receipt, runner-unit census, rapid-growth trend, FIF scratch count, and archived-journal size limit only. Preserve `source_delete_enabled=false`.
- **FSG.P3 — Host canary and installation evidence (host proof, not code acceptance):** Ubuntu2 canary verified; Ubuntu0, Ubuntu1 and Ubuntu3 installed the exact same payload SHA-256 `9edffd86e42364dad62a0a0e9c87390cb6d20847df52ea62e3e9a1498279bf99`. Each local one-shot exited zero, its timer was active, and `/var/lib/mastermind-storage-guard/latest.json` was read back. Natural subsequent timer firing, trend sampling and long-run reliability remain to verify.
- **FSG.P4 — Source review/release (ready for independent review):** A non-author reviews the script, test coverage, systemd sandbox, no-delete property, installation/runbook, and adjacent fleet-storage source law. Normal CI, merge and deployed source-version reconciliation remain separate gates.
- **FSG.P5 — Stop the dominant growth producer (blocked on ownership and producer-specific evidence):** The observed Ubuntu1 `/tmp/fif-shipprep` creates repeated ~13 GiB materialized trees. Apply source-aware sparse/reusable checkout construction or explicit disposable-scratch lifecycle in its owning producer, prove it with active-session preservation and real CLI worker execution. Do not turn the sentinel into a second GC, widen the Mac sweeper roots, delete human-driven trees by age, or disable the CI guard.

## Operator commands

```sh
sudo systemctl status mastermind-ubuntu-storage-guard.timer --no-pager
sudo systemctl start mastermind-ubuntu-storage-guard.service
sudo cat /var/lib/mastermind-storage-guard/latest.json
sudo journalctl -u mastermind-ubuntu-storage-guard.service -n 30 --no-pager
python3 -m unittest -v tests/test_ubuntu_storage_guard.py
```

The root-owned status path contains the latest sample only (journald records scheduled firings). The oneshot is scheduled every 20 minutes with randomized delay, CPU nice 15 and idle I/O. It remains a storage **observer**, not a runtime/job/lease control plane. With `--vacuum` it can delete **archived journal files only**, and only when root storage is in a warning or worse condition. If that subprocess fails, the receipt records the error; it does not fall back to source deletion.

## Boundaries

- The existing Mac `scripts/worktree_gc.py` and its `config/worktree_gc.json` stay unchanged. Its existing ratification gates, `human_driven_roots` and prior proved session-loss failure govern; Linux `~/lanes/wt` must not be automatically added to a deleter scope.
- Git commits, cold archives, human session worktrees, browser data, CI source mirrors, current FIF stage trees and uncommitted/unknown data have no automatic deletion authorization.
- On Ubuntu4 the storage census read 868 GiB available / 3% used, but the exact host's sudo gate was unavailable; **no system unit was installed** there.
- The 2026-11-01 host status and installation reflect a bounded observation; capacity can regress after new snapshot creation. Host receipts and CI guard logs, not this document, own live proof.
