---
key: SKEW-ACCRUAL-ON-THE-STORE-HOST
question: >
  Where should the daily ThetaData skew-accrual producer (MO-PAID-013 W2-2)
  run — on the M1 store-host that holds the canonical ThetaData EOD store
  (and which therefore reads the same bytes the upstream writer wrote), on a
  CI/org-level runner with an `m1-theta` label, or on a render host with the
  ~60 GB store hydrated?
answer: >
  The producer runs on the M1 store host, in a dedicated lane checkout
  /Users/chriswong/skew-ops-wt (NOT the existing flow-ops-wt or theta-ops-wt
  trees — both are stale/dirty by design and would undermine a "checkout is
  clean" assertion). The lane uses launchd com.macro.skewaccrual, which
  calls run_skew_accrual.sh via run_with_env.sh. The script (1) refreshes
  the dedicated checkout off origin/main with a dirty-tree refusal and a
  never-push posture, (2) gates on the ThetaData EOD store freshness via
  scripts/skew_accrual_gate.py (6 x 20-min retries, SKEW_FRESHNESS_BYPASS=1
  escape), (3) runs `python -m scripts.build_options_skew --accrue` (W2-1b-
  owned flag; the runner fails loud with a named reason if the flag is
  unknown), and (4) publishes data/options_skew to R2 via
  `python -m scripts.publish_r2 --dirs options_skew`. The W2-3 render
  cutover restores the ledger via `python -m scripts.fetch_r2 --dirs
  options_skew`. This lane does NOT change any workflow step; it adds
  files, tests, an R2 data-dir registration, and a launchd plist that is
  OFF by default until the seat installs it per the runbook.
rationale: >
  The skew-accrual lane MUST read the same bytes the upstream ThetaData EOD
  writer wrote — that is the whole point of canonical-source governance. CI
  runners and render hosts do not hold the store; hydrating it to them would
  (a) blow the 67-minute render budget (a ~60 GB parity check inside the
  render job would dominate the build), (b) race the canonical
  WP-RESOLVER's empty-stub branch (the options_witness 0/18 incident shape:
  a runner tree with no store content resolves and publishes an empty
  artifact), and (c) introduce a second writer surface that does not own
  the store (the launchd job sits on the same disk as the writer). The M1
  ops host IS the canonical producer surface for any data-plane work that
  reads the deep ThetaData store — that is the design boundary established
  by thetadata-r2sync, optionsmatrix, and the prior index_gex_history lane
  (DEC:AD-OPTIONS-CANONICAL-SOURCE-THETADATA). Putting the skew accrual
  there re-uses an already-running producer pattern, and a dedicated
  skew-ops-wt checkout keeps the lane from inheriting the dirty / stale
  posture of the two existing M1 ops trees (flow-ops-wt is detached at
  2026-07-17, 7,985 commits behind, 395 files modified; theta-ops-wt is on
  main@08-23 with 26k dirty entries). The dedicated checkout is created
  off fresh origin/main with sparse-checkout (engine, scripts, lib, config,
  ops, data/options_skew) — ~0.35-0.57 GiB instead of the full ~3.8 GiB —
  and is refreshed on every run with a clean-tree assertion. The runner
  NEVER pushes; its only outbound is publish_r2, gated on the dedup'd
  ledger contents. The plist is OFF by default until the seat installs it,
  so the lane introduces zero live behavior change on merge — only files,
  tests, and a directory registration.
alternatives:
  - option: CI label `m1-theta` (org-level runner)
    why_not: CI runners share a GitHub Actions token and have neither the
      store filesystem nor a 67-minute render budget. Hydrating 60 GB of
      ThetaData parquets onto a CI runner would race the WP-RESOLVER empty-
      stub branch (the same shape that produced the options_witness 0/18
      incident) AND would have to re-read the full store on every run
      because the runner's checkout is ephemeral. The label-cascade risk —
      a misconfigured label propagating into the wrong job — is also a
      standing prohibition; the org-level lane taxonomy already names
      `m1-theta` as a single-purpose label, not a shared producer surface.
  - option: Git narrow-commit delivery from a stale ops checkout (the dead
      scripts/launchd/theta_surface_accrual.sh precedent)
    why_not: >
      The precedent is dead on the host — its plist is not loaded, and the
      underlying checkout (theta-ops-wt) is on main@08-23 with 26k dirty
      entries, so even if the plist were re-loaded it would either push
      dirty bytes (corrupting main) or refuse on the lane's own clean-tree
      assertion. Narrow-commit delivery from any ops checkout also creates
      a hidden writer: someone reviewing a W2-N PR would see a "no
      workflow change" diff but would not see the live bytes being pushed
      by launchd in the background. The lane is therefore publish-r2-only
      — the only outbound is R2, the Git history stays pure, and the live
      bytes are visible to anyone with R2 read access.
  - option: Hydrate the ~60 GB ThetaData store onto a render host and run
      the producer from there
    why_not: >
      A 60 GB hydration step inside a CANDAL render job blows the
      67-minute render budget (thetadata_eod already costs ~30 min as a
      restore-only step; adding a fresh accumulate doubles it). The
      hydrate path also races the canonical WP-RESOLVER's empty-stub
      branch on a partial restore, which is exactly the shape that
      produced the 0/18 options_witness incident. And the render host is
      the WRONG OWNER for an accrual job — render hosts do not own the
      source-of-truth store, they own the rendered site; running a
      producer on a render host inverts the data flow and makes the lane
      dependent on a CI worker's git LFS / network posture rather than on
      the M1 host's local-store posture.
affects:
  - "WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2"
  - ops/launchd/com.macro.skewaccrual.plist
  - ops/launchd/run_skew_accrual.sh
  - scripts/skew_accrual_gate.py
  - scripts/audit_options_skew_overlap.py
  - scripts/publish_r2.py
  - data/options_skew/snapshots.parquet
evidence:
  - "Frozen spec for A-F03-W2-2 (META-CEO A seat, 2026-09-22): the lane
    ships ops/launchd/com.macro.skewaccrual.plist + run_skew_accrual.sh +
    scripts/skew_accrual_gate.py + scripts/audit_options_skew_overlap.py +
    publish_r2._DATA_DIRS registration + DEC record + install runbook; this
    packet does NOT change any workflow step"
  - "Verify: `python3 -m pytest tests/test_skew_accrual_gate.py
    tests/test_skew_accrual_launchd.py tests/test_audit_options_skew_overlap.py
    tests/test_skew_accrual_precheck.py tests/test_skew_accrual_verify_ledger.py
    -q` exits 0 with all 73 tests passing across the five suites
    (round-6 Meta-CEO A binding ruling added 2 tests in
    tests/test_skew_accrual_launchd.py:
    test_plist_log_paths_live_outside_repo_in_sibling_state_dir (MAJOR-1)
    pins the launchd stdout/stderr pair under $SKEW_STATE_DIR, and
    test_run_with_env_wrapper_exists_on_origin_main (MINOR-1) pins the
    wrapper the plist's ProgramArguments chain references. Round-5
    Meta-CEO A binding ruling added 2 B2 repeatability tests:
    test_two_run_cycle_is_admitted_via_real_git +
    test_runstate_files_live_outside_repo, plus 1 MINOR-2 receipt-line
    test: test_main_receipt_writer_emits_exactly_one_physical_line; the
    earlier rounds added the --pre-rows end-to-end path, the BLOCKER-1
    pair-based _delta_stats, MAJOR-4's recomputed-key match check, and
    the measurement tests pinning the publish_r2 floor against the
    actual tracked bootstrap at 238,595 bytes)."
  - "Verify: `python3 scripts/agentos.py validate` exits 0 (this DEC record
    validated by the schema)"
  - "Verify: `python3 scripts/check_contract_delta.py --base origin/main`
    reports 0 introduced contract findings (no workflow step changed)"
  - "Verify: `git diff --stat origin/main HEAD -- .github` is empty (no
    workflow changes)"
  - "Verify: `git diff --stat origin/main HEAD -- data/ site/ engine/options_skew.py
    scripts/build_options_skew.py` is empty (lane does not touch forbidden
    surfaces)"
  - "Verify: `plutil -lint ops/launchd/com.macro.skewaccrual.plist` reports
    OK; Python plistlib parses with Label=com.macro.skewaccrual,
    WorkingDirectory=/Users/chriswong/skew-ops-wt, Schedule weekdays 1-5
    at 05:30 local (BLOCKER-4 fix; 13:30Z during PST / 12:30Z during PDT,
    both safely AFTER the observed 11:30Z ThetaData EOD refresh
    year-round), ThrottleInterval=60, LimitLoadToSessionType=Aqua"
  - "Verify: `sh -n ops/launchd/run_skew_accrual.sh` reports OK"
  - "Verify: `python3 -c 'import plistlib; ...'` confirms the runner
    ProgramArguments chain resolves to /Users/chriswong/skew-ops-wt
    files that will exist once the dedicated checkout is created per the
    install runbook (research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md
    §3.1)"
  - "DEC:AD-OPTIONS-CANONICAL-SOURCE-THETADATA (Chairman source ruling,
    2026-08-22) names ThetaData as the canonical Mastermind options-data
    source; the M1 store-host IS the producer surface for any data-plane
    work that reads the deep ThetaData store, and the skew-accrual lane
    is exactly that class of work"
confidence: high
reversibility: easy
decided_by: "META-CEO A seat, packet A-F03-W2-2, 2026-09-22"
decided_at: 2026-09-22
---