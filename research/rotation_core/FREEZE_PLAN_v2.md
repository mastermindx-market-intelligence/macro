# Rotation Core v2 — freeze mechanics (one commit)

Prepared by the Rotation Core lead; executed by the parent (or on the parent's instruction).

1. Precondition: tree clean at the branch head; Sector Intelligence's read folded in through a logged diff committed first (its own commit, before the freeze), each change with source and reason.
2. `python scripts/freeze_rotation_core_v2.py` (dry run) prints the sha256 the frozen JSON will have. The dry run prints the sha of the current draft; any draft change changes it (recorded in the commit that reports it).
3. `python scripts/freeze_rotation_core_v2.py --apply` then a single commit `research(rotation-core): freeze protocol header v2 (sha256 <sha>)`. That commit contains exactly:
   - `research/rotation_core/protocol_header_v2.json` (status FROZEN with UTC time; governs);
   - `research/rotation_core/PROTOCOL_HEADER_v2.md` (first line: the sha256);
   - deletion of the two `.DRAFT` files;
   - `data/trial_ledger.jsonl` with two appended `declared_budget` rows: `rotation_core_v2` n=9 and `rotation_core_v2_pro_run_b_consumed` n=10 (both reasons carry the sha). v1's `rotation_core_v1` n=36 is already in the ledger. DSR effective N = 9 + 10 + 36 = 55 (plus prior families on the same instruments as in v1).
4. Not in the freeze commit: `HOLDOUT_RELEASE_v2.json`. The template `HOLDOUT_RELEASE_v2.TEMPLATE.json` is committed; only the parent copies, fills and commits the release, after the 1998-2019 selection result is committed.
5. Order after freeze: `run_rotation_core_v2.py --stage select` (1998-2019 only, one run, committed) → parent writes the release → `--stage confirm` (one run). The confirm stage is wired after the release names the windows; until then it refuses.
6. `data/trial_ledger.jsonl` is a shared append-only file: on a rebase before merge, re-apply only these rows (and v1's single row).
