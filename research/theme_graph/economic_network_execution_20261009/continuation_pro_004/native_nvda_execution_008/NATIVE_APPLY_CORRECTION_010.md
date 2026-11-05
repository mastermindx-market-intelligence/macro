# Native publication writer correction

The first publication application, PID 48787, exited 1 in 3.12 seconds. Its writer called the integer stat-result st_mode field while preparing to preserve README permissions. One intended file, EXECUTION_STATUS_20261009_008.md, had already been written completely; README, its temporary path and all further payload paths were untouched.

Read-only reconciliation 009 verified the exact 9,240-byte intended status document, SHA-256 06c34317ec15bd576bd5f6ac903d8b5e9bc5de1b6d6cc9566b800b4072e0fb62. All 149 prior checkpoint files, 151 prior manifest members and 35 capture-source paths remained unchanged. Tracked and staged diffs and ignored paths were empty. No partial write was inferred to be absent from an unchanged HEAD alone.

Runner 010 corrects the integer-field access, binds the observed partial state and reuses that one byte-verified new file without rewriting it. It writes the remaining explicitly intended evidence through a distinct runner and result path. The original failed runner, actual terminal tool-value serialization and complete reconciliation are preserved. No source, tests, CI policy, registry, provider request or authority changes accompany this writer correction.
