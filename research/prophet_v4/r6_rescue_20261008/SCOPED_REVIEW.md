# Independent source-clock review

Fabric operation: `prophet-r6-b06-clock-review-01a11e89`.
Root: `01a11e89-b35d-7a81-9404-5fce2c6170cb`.
Admitted reviewer: Grok 4.6 on Ubuntu2. The native terminal receipt reports
started=true, returncode=0, output_complete=true, cleanup_proven=true.
The reviewer result, not the process exit alone, is the evidence below.
Raw result SHA256: `0a06596bf6c0d1196eee4b3f67084b85d409bf40d3bc8e40f7c95d2f28f670d8`.

Parent adjudication: review deliverable consumed and accepted for its exact
source/diff hashes. The low-severity prose finding was verified and repaired
in this branch, with two discriminating failures before the repair. A second
publication-session phrase in the mixed-vintage disposition was also repaired.
Timezone-qualified equivalent ISO representations are valid source timestamps;
no stricter separator spelling is required. Final changed bytes and CI wiring
still require review; this earlier PASS does not cover subsequent changes.

**PASS** — C1_ROUTINE_BOUNDED audit-interpretation review of the pinned chronology clock slice. This is a review of those bytes, not source approval, merge, or release.

**Binding.** Source SHA256 `28b39f804a58844e4557c3bea1ff2b1505ffc7259afc63ea84df45f9cd72a404` and diff SHA256 `1447b67481ed18ec99c777a37ae177c79402e4b0cca1d04d558b7c5e12293c6d` matched the capsule. Isolated apply onto Macro `94a20f53cdb2d866d07089df50567f059bf1073e` preimage blobs `f048403c4c0c` / `186d0668377d` produced git blobs `66cfe326c20a` / `4f03ab7248a5`. Protected Mastermind `732cf7be88e7159b4995a8885fbd381cd1484e3e` was observed and left untouched. Scope was only `scripts/audit_prophet_plan_chronology.py` and `tests/test_prophet_plan_chronology_audit.py`.

**What this patch does.** `_clock_evidence` keeps three source clocks (`plan_run_date`, `first_committed_at`, `origination_recorded_utc`) and hard-wires `accepted_publication_at`, `first_user_exposure_at`, and `executable_fill_at` to `None` with `publication_status`/`fill_status` `UNRESOLVED` and reasons `accepted_publication_receipt_not_joined` / `executable_fill_evidence_not_joined`. Capture time is read from the first-add receipt blob. `_correction_evidence` rebuilds that boundary instead of copying a caller’s publication/fill qualification. `build_report["clock_qualification"]` sets `proves_user_exposure: False` for audited rows only. Schema stays `prophet.plan_chronology_audit/v1` with additive keys; `validate_plan_correction` still accepts extra evidence objects. Raw plans and the outcome ledger remain unread-for-rewrite; the append-only correction writer is unchanged.

**Tests actually run (isolated overlay, repos unmodified).**

- `tests/test_prophet_plan_chronology_audit.py`: **25 passed**
- `tests/test_prophet_integrity.py`: **23 passed**
- Combined **48**, matching the parent post-implementation count. The eight new nodeids are the two `legacy` rows of `test_source_recording_never_proves_user_exposure_or_fill`, `test_late_origination_capture_is_not_backdated_or_replaced_by_head`, four malformed `recorded_utc` rows, and `test_report_and_correction_evidence_retain_unresolved_clock_boundary`.
- Reviewer probes (not in the patch): 12 passed. Receipt-era missing `recorded_utc` stays null after HEAD later adds a stamp. A forged report with `publication_status=RESOLVED` and a fill time is stripped back to `UNRESOLVED`/`None`. Ledger corrections carry the same unresolved boundary. Empty windows keep `proves_user_exposure: False`. CRI-shaped stamps `2026-10-06T07:43:29.145743+00:00` and `2026-10-06T00:46:54-07:00` parse and remain capture/Git clocks.

**Tried to break it; these held.** First-add receipt vs mutable HEAD (`test_late_origination_capture…` and the missing-stamp probe). Later capture left `recorded_at`/`plan_run_date` on the run date. Date-only, naive datetime, `"bad"`, `123`, `True`, `""`, and `"… UTC"` raise `OriginationReceiptError`. Legacy rows without `clock_evidence` get a null capture clock and still `UNRESOLVED`. Existing hash/path/ambiguity fail-closed tests still pass.

**Low (wording leak, same file).** `_integrity_disposition` still writes `"outage-era plan was published after its entry-price session"` into persisted `integrity_reason` (`scripts/audit_prophet_plan_chronology.py`, stale_price_basis branch). `session_lag` still names `publication_session`. Machine clocks stay unresolved; the overlay prose can still be read as a publication claim.

**Low (parser breadth).** Python 3.12 `fromisoformat` accepts `Z`, a space instead of `T`, and `+0000`. Those values are stored exactly and still fail the naive/no-offset check. They do not fill publication/fill fields.

**Untested in the candidate suite (probed here).** Receipt-era omitted `recorded_utc`; ledger-correction clock rebuild; empty-window qualification; CRI timezone split. `_correction_evidence` still trusts a well-formed `origination_recorded_utc` on the audit row without re-reading git, same as `first_commit`/hashes; publication/fill remain rebuilt. `clock_qualification` counts `len(rows)` rather than inspecting each row’s statuses. Live CRI Oct5/Oct6 plan bytes were not executed; only fixture/parser probes of those stamp shapes.

**What this does not prove.** Full B06 or R6. User exposure, accepted publication, or an executable fill for any plan, including the real CRI Oct5 identity with run Oct6, capture `2026-10-06T07:43:29.145743+00:00`, and commit `2026-10-06T00:46:54-07:00`. Those remain unjoined source-recording clocks. Numeric grades, historical plan content, candidate identity, PR8192, and runtime release are outside this slice. Top-level `recorded_at` / `first_committed_at` names are unchanged; readers that ignore `clock_evidence` can still misuse them.

Independent review of the pinned bytes was possible. No merge, source commit, or release is issued here.
