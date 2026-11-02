---
key: FIRST-WEB-CEO-ROOT-BINDS-THE-ARMED-OPERATOR-HARNESS
question: >
  For the first useful Web-CEO-submitted root on the installed Mastermind Executive host
  (release f91847688f8126511c854ab253cd5c3cb67baa4e at decision time; c7407c6c77ef82cc6590401e80cc8f1868dc9085 installed 2026-09-29T10:35Z, same coupling), does the Codex Worker run through the
  sealed subscription planner that executed JOB004-007, or through the COO operator harness
  armed by ops/executive_os/autonomy_control.py — and may the installed flags be split to
  get the sealed path while the operator harness stays disarmed?
answer: >
  The armed operator harness, and never a split. The sealed planner and a Web-CEO finite
  root are mutually exclusive by construction, so the first useful task is also the
  installed operator-harness qualification. Order: readiness canary on the exact pinned
  0.147 Codex pair -> Gate-B receipt -> `autonomy_control.py arm` -> Web CEO submit. Never
  submit while unarmed.
rationale: >
  `derive_candidate_configs` writes `coo_autonomy_armed`, `coo_operator_harness_armed` and
  the Worker's `operator_harness_armed` together and `collect_status` classifies split flags
  as drift, so a manually split installed configuration is not a deployment path. The
  subscription realm owner in codex_provider_realm.py refuses natively unless
  `operator_harness_armed is False`, while a finite-drive root in executive_runtime.py and
  the COO cycle require it to be True. Product's own reading (a root submitted while the
  binding is false and armed afterwards is stranded, because root matching requires every
  current binding field) closes the remaining alternative. The readiness canary and the arm
  receipt must therefore bind the same harness binary the root will pin, and the one
  useful root doubles as the installed qualification — no separate green canary.
alternatives:
  - option: Run the first root on the sealed planner with the installed flags split by hand.
    why_not: >
      Not a deployment path — the candidate-config function couples the three flags and
      status treats a split as drift; Sol withdrew the shortcut on #703 (comment
      5886468887) and the native lead withdrew it in the 08:09Z frontier.
  - option: Submit the root now while unarmed and arm the harness afterwards.
    why_not: >
      Root matching requires all current COO binding fields, so the root is stranded and
      the queued root would have to be rewritten — forbidden as a manual arm/queue shortcut.
  - option: >
      Wait for the full depth-two hierarchy (#1041), four-account coverage, or #1046
      before any root.
    why_not: >
      None of them is a dependency of one operator-harness root; each is its own lane
      with its own owner and would only delay the travel milestone.
evidence:
  - "mastermind:ops/executive_os/autonomy_control.py at protected master 9b01b708551196b1f144aa2f98b48bf37f513e26, derive_candidate_configs (lines 739-762): sets control coo_autonomy_armed, coo_operator_harness_armed and worker operator_harness_armed to the same value; `git show origin/master:ops/executive_os/autonomy_control.py | sed -n 739,762p`."
  - "mastermind:control_plane/codex_provider_realm.py:862 at 9b01b708: `config.get(\"operator_harness_armed\") is not False` -> _native_refuse(); the sealed subscription realm is admitted only while disarmed."
  - "mastermind:control_plane/executive_runtime.py:14532-14535 and :11266-11270 at 9b01b708: a finite-drive root / finite persisted host binding requires operator_harness_armed True."
  - "mastermind:control_plane/executive_coo_cycle.py:491 at 9b01b708: _finite_host_pin_matches returns False unless operator_harness_armed is True."
  - "mastermind:control_plane/executive_service.py:2920-2932 at 9b01b708: an armed operator harness requires the operator supervisor composition and runs the worker identity verifier at Control start."
  - "Mastermind #703 comment 5886468887 (Sol, 2026-09-29T08:23Z) withdrawing the sealed-planner shortcut; #703 frontier comment 5868465578 'Parent continuation — 08:09 UTC' (native lead) stating collect_status treats split flags as drift and that a root submitted while false then armed true is stranded."
  - "Mastermind #600 comment 5886875023 and #703 comment 5886875401 (Fable closer, 2026-09-29): the ruling as delivered to the parent record and the native leads."
affects:
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - shared-ai-provider-control
  - mastermind:ops/executive_os/autonomy_control.py
  - mastermind:control_plane/codex_provider_realm.py
confidence: high
reversibility: costly
decided_by: "coo-fable (session 3f381a7c-a947-4a1d-ad12-5e8568a83250, Chairman-delegated integration closer; recorded by successor session 7712b0f4-469a-474d-bd3c-22f7ced1923d)"
decided_at: 2026-09-29
---

## Why this is recorded

The sealed-planner shortcut was proposed, withdrawn and then re-verified within one
morning across three carriers (Slack root `C0C47UNNF3R/1790428520.458669`, Mastermind
#703, Mastermind #600). Without a decision record the next Web CEO or native session
would rediscover the coupling from the code again. The load-bearing fact is not the
withdrawal but the mutual exclusion: arming the operator harness structurally closes the
realm path that produced the only historical successes (JOB004-007), so "AVAILABLE
worker" and "sealed jobs once passed" are not evidence that an armed root will run.

## What it does not decide

It does not arm anything, choose a Gate-B receipt, select a credential kind, or move the
r1 root out of NOT_DISPATCHED. Those remain Product's host effects and the Web CEO's
submit, in the order given in `answer`.
