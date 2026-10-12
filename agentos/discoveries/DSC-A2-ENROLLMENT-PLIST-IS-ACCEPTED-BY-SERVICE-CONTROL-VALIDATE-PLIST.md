---
key: A2-ENROLLMENT-PLIST-IS-ACCEPTED-BY-SERVICE-CONTROL-VALIDATE-PLIST
claim: >
  The Agent Relay launchd plist that the A2 enrollment owner installs (a new O_EXCL regular file at
  /Library/LaunchDaemons/com.mastermind.executive.agent-relay.plist, uid 0, gid 0, mode 0644,
  re-read exact by verify) is exactly the artifact that the closed activation owner proposed in
  Mastermind #1241 accepts: service-control.sh validate_plist requires a regular, non-symlink file
  that passes plutil -lint before any launchctl call, and the first launchctl call of
  start-agent-relay is enable, so a host with no plist never has its pre-enrollment disabled
  override touched by activation, and stop-agent-relay refuses before disable unless the exact
  Agent Relay service is already registered.
falsifier: >
  At protected master run `grep -n 'PLIST_UID\|PLIST_GID\|mode=0o644' ops/executive_os/a2_agent_relay_enrollment.py`
  and `sed -n 33,41p ops/executive_os/service-control.sh`; on the #1241 head grep the
  start-agent-relay and stop-agent-relay case branches. Falsified when enrollment changes the plist
  owner/mode/kind (for example 0600 or a symlink), when validate_plist adds an ownership, mode or
  identity check the enrollment artifact does not meet, when ensure_running stops calling
  validate_plist before enable, or when a reviewed release lets activation materialize or repair a
  plist itself.
so_what: >
  The post-enrollment activation ceremony needs no second plist producer and no repair step: enroll
  → verify → start-agent-relay composes on the artifact as written. Because verify refuses after
  activation (its host gate requires disabled+unloaded), plist identity and release binding must be
  proven by verify before start-agent-relay and the activation receipt should cite that verify
  receipt. Both owners' unit tests fake the plist, so this compatibility is only visible across the
  two owners; a change on either side breaks the chain silently until the live ceremony.
kind: constraint
verified_at: 2026-10-04
verified_by: >
  Fable seat read-only cross-owner read on 2026-10-04 (Mastermind #1241 issuecomment-5978317957):
  a2_agent_relay_enrollment.py at origin/master a2646f45/17b9fa13 (:48-49 PLIST_UID/PLIST_GID,
  :56 PLIST_PATH, :951-961 write_new_private_file(... uid=PLIST_UID, gid=PLIST_GID, mode=0o644),
  :280/:898 exact re-read); service-control.sh at #1241 head 57816945 (validate_plist :33-40,
  ensure_running first call `launchctl enable`, require_registered before stop_one); #1241 tests
  test_start_agent_relay_refuses_missing_plist_before_launchctl (log == []) and
  test_stop_agent_relay_refuses_absent_service_before_disable.
scope:
  - mastermind
  - mastermind:ops/executive_os/a2_agent_relay_enrollment.py
  - mastermind:ops/executive_os/service-control.sh
  - WS:EXECUTIVE-AUTONOMY-V1-CLOSURE
confidence: verified
---

## Why this matters

The parenting-loop canary chain crosses three owners (A2 host preparation, A2 enrollment,
service-control activation) that are tested in isolation with faked plists. This record pins the
one cross-owner fact that makes the human ceremony composable without a repair step, and names the
exact reads that would show it broken.
