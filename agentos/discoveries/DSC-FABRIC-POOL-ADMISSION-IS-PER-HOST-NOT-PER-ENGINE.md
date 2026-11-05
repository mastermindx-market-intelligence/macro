---
key: FABRIC-POOL-ADMISSION-IS-PER-HOST-NOT-PER-ENGINE
claim: >
  A Subagent Fabric NO_HOST (and a local sub.sh rc=78 LOCAL_SEAT_REMOTE_REQUIRED)
  is usually a POOL-NAME admission miss, not an outage: pools are admitted per
  host in ext/hosts.json allowed_modes. On 2026-10-11 `glm-codex` was admitted
  only on ubuntu0 (explicit-canary-only, lane ceiling 2/2) while `glm` was
  admitted on ubuntu0-3 (resolved ubuntu2 at 09:06Z; later lanes that day ran on
  ubuntu0). The seat host m2 refuses every non-Grok engine locally by policy.
  A review lane additionally needs POOL_TASK_CLASS=review, or the economic
  policy refuses it as ECONOMIC_POLICY_REFUSED unknown_task_class.
falsifier: >
  Run `python3 ext/host_pick.py --mode glm --max-age 600 --exclude m2 --explain`
  from the B-kit and get NO_HOST while ubuntu0-3 are up, or find `glm-codex`
  in a non-ubuntu0 host's allowed_modes in ext/hosts.json.
so_what: >
  Before declaring the fabric down and falling back to direct principal
  execution under the continuation law, diagnose with host_pick --explain and
  retry with pool `glm` via `remote_sub.sh auto glm <packet_FILE> '~/lanes/repos/macro' <model>`;
  a packet passed as text (not a file path) yields PACKET_MISSING, and a review
  packet needs POOL_TASK_CLASS=review in the environment.
kind: runtime
verified_at: 2026-10-11
verified_by: >
  Seat 508c3757 ran host_pick --explain for both pools and remote_sub.sh --dry-run
  with pool glm (resolved host=ubuntu2) after two Opus orchestrators independently
  reported NO_HOST for pool glm-codex on 2026-10-11 ~08:50Z; the E0/M0 review lane
  rs_20261011T170248Z_89804 then STARTED and finished rc0 on pool glm with
  POOL_TASK_CLASS=review after a first attempt was refused unknown_task_class.
scope:
  - macro
  - mastermind
  - handoff_kits/meta-ceo-b-2026-09-08/ext/remote_sub.sh
  - handoff_kits/meta-ceo-b-2026-09-08/ext/host_pick.py
  - WS:SINGLE-NAME-INTELLIGENCE-OS
confidence: verified
---

Measured 2026-10-11 by the SNI program seat. Two Opus orchestrators (carrier
recovery, E0/M0 qualification) each hit `sub.sh glm-codex` rc=78 on the m2
seat host and `remote_sub.sh auto glm-codex` NO_HOST rc=3, concluded the
fabric was unavailable, and executed their bounded labor directly under the
continuation law. The fabric was up the whole time under pool `glm`. Host
placement moves with load, so treat the named host as an observation, not a
pin; the admission map in ext/hosts.json is the authority.
