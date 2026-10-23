---
key: MM-PIT-UNOWNED-PARENT-FSYNC-EACCES-IS-TOLERATED
question: >
  Since PR #5373 (merged 2026-08-11T22:43Z) engine/neuralweb/market_memory_pit.py
  `_ensure_store_directory_chain` fsyncs `root.parent` after creating a store root. For the
  option-OI store the parent is /var/lib/macro-market-memory-options, provisioned root-owned
  mode 0710 by reviewed design (app/deploy/README.md:74-80), and the writer runs as the only
  non-root market-memory service user, so `_directory_fsync` (os.open O_RDONLY|O_DIRECTORY)
  raises EACCES and every option-OI capture has failed before its observation write since
  2026-08-11 22:45Z. Fix the provisioning (chmod the parent), the writer, or the shared pit
  chain — and what makes the fix safe for every other store that shares the chain?
answer: >
  Fix the shared pit chain, narrowly: `_ensure_store_directory_chain` tolerates EACCES from
  the `root.parent` fsync ONLY when (i) the parent is not owned by the effective uid and
  (ii) the store root already existed before this call. Every other case keeps raising
  exactly as today: an owned parent still fsyncs, a NEW root under an unreadable parent still
  raises (durability of a freshly created dirent is not negotiable), and no other error class
  is swallowed. The 0710 parent is never chmod'ed. In the same PR, as a second commit, the
  option-OI CLI's fail-closed line gains a secret-free stage token
  (`stage=<credential|fetch|http_status_class|validate|persist>` plus the exception CLASS name
  only) so the second, later failure regime (R2, 2026-08-15 onward) becomes attributable
  without a credential.
rationale: >
  The parent's own dirent durability was established at provisioning time by root; a writer
  that cannot open the parent has nothing to make durable there, so tolerating EACCES on a
  pre-existing root under an unowned parent loses no durability guarantee while restoring
  the reviewed security boundary's intent. Conditioning on "root pre-existed" keeps the
  guarantee that matters (a new root's dirent reaches disk or the capture fails) and keeps
  the chain byte-identical for every root-run store, whose parent IS owned by the effective
  uid (CapabilityBoundingSet is empty on those units, so root passes the parent read check
  as owner, not by DAC override). Relaxing the provisioning instead would weaken a
  documented security boundary to fit a writer bug. The stage token rides in the same PR
  because the pit fix alone cannot make the canary green: R2 fails before persistence and
  its cause class is unobservable by design today.
alternatives:
  - option: chmod the 0710 parent so the service user can open it
    why_not: >
      Reverses a reviewed security boundary (README.md:74-80) to accommodate a code defect;
      widens what the writer can read for no durability gain.
  - option: Option-store-scoped directory chain that skips the parent fsync entirely
    why_not: >
      Forks the shared chain into two behaviours; a future root-run store moved to a service
      user would silently inherit whichever branch it hit. The narrow predicate keeps one chain.
  - option: Run the option-OI unit as root like the other market-memory units
    why_not: >
      The non-root service user is the reason the credentialed writer is sandboxed; dropping
      it to fix an fsync is the wrong trade.
  - option: Fix R1 only and wait for the canary to report
    why_not: >
      R2 (2026-08-15 onward) already fails before persistence with a deliberately
      message-free journald line; without a stage token the next failure is as opaque as the
      last 57 days.
evidence:
  - "ORCH-OPS guarded replay as the service user (runuser -u macro-market-memory-options, every os write primitive patched to raise, flock no-op; probes $S/oi_replay_probe.py, oi_resume_guarded.py, oi_chain_guarded.py, oi_capture_guarded.py, VPS HEAD f8dc4bb05ece): traceback option_oi_store._persist_bundle_cas:1147 → market_memory_pit._ensure_store_directory_chain:722 → _directory_fsync:668 os.open:670 EACCES on /var/lib/macro-market-memory-options (root-owned 0710)"
  - "git log -S_directory_fsync -- engine/neuralweb/market_memory_pit.py: added by #5373 commit 6e2c3f5e0c merged 2026-08-11T22:43:21Z; store HEAD.json / last generation mtime 2026-08-11 22:24Z, last body 2026-08-15 12:49Z"
  - "git grep '^User=' app/deploy/macro-market-memory-*.service → only the options unit runs as a service user; CapabilityBoundingSet= is empty on every market-memory unit"
  - "scripts/capture_market_memory_option_oi.py:259-273 main() catches only MarketMemoryOptionOiCaptureCliError / ObservationError / StoreError and prints the typed line 'option-OI canary capture failed closed' with no cause text"
  - "R2 stage probe ($S/oi_stage_guarded.py, euid 995): repository_commit, default_store_root, resume_pending_option_oi_captures, read_pinned_option_oi_sources all STAGE_OK → R2 ∈ {credential load, fetch transport / HTTP non-200, response projection/validation}"
  - "DSC:MASSIVE-OPTIONS-FLATFILE-ENTITLEMENT-REGRESSION (verified 2026-08-20) brackets R2's onset and names the separate REST Options Snapshot entitlement failure as the strongest hypothesis"
affects:
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - market-memory
  - engine/neuralweb/market_memory_pit.py
  - scripts/capture_market_memory_option_oi.py
  - app/deploy/macro-market-memory-options.service
confidence: high
reversibility: easy
decided_by: coo-fable (seat fd47d431, Chairman 2026-10-11 autonomy directive)
decided_at: 2026-10-11
review_by: 2027-01-11
---

Tests the implementing PR must carry: an EACCES-raising parent fsync (monkeypatched) with a
pre-existing root under a parent owned by another uid lets the capture complete; an owned
parent still fsyncs; a new root under an EACCES parent still raises; the stage-token line is
secret-free (no message text, no provider bytes, class name only). Live proof is the next
SCHEDULED option-OI run's journald line — never a hand start of the unit. If the stage token
reports an HTTP 401/403 class, the remaining blocker is a vendor entitlement
(EXACT_HUMAN_GATE); do not change the provider, path, or parser.
