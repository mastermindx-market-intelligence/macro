---
key: CEO-SUBMIT-SINK-AND-ARMED-HARNESS-ARE-MUTUALLY-EXCLUSIVE-ON-MASTER
claim: >
  On protected Mastermind master a2646f45 no lawful order of operations lets a root admitted
  through the CEO-submit sink (submit-ceo-intent) execute on the armed COO operator harness:
  CEO-submit arm refuses while any autonomy/harness flag is armed, the sink's source-side
  eligibility requires the worker harness disarmed, a root admitted while disarmed freezes
  operator_harness_armed=false into its host binding and is stranded after the full arm, and
  CEO-submit disarm refuses under full autonomy because proves_safe_coexistence defaults to REFUSE.
falsifier: >
  At current protected master run `grep -n 'CeoSubmitAdmissionError("coo_autonomy_armed")\|full_autonomy_armed_unsafe_coexistence\|def proves_safe_coexistence\|worker_armed is not False' ops/executive_os/autonomy_control.py`,
  `sed -n 2374p control_plane/executive_service.py`, `sed -n 491p control_plane/executive_coo_cycle.py`
  and `sed -n 14820,14823p control_plane/executive_runtime.py`. The discovery is falsified when a
  reviewed release makes proves_safe_coexistence return True from source evidence, lets
  ceo_submit_sink_eligible admit an armed worker harness, re-qualifies a queued root's host
  binding after an arm through a reviewed path, or when a CEO-submitted root is observed RUNNING on
  the armed harness under a sealed ARMED receipt.
so_what: >
  The Autonomy V1 closure packet's Phase 4 (armed CEO ingress) and Phase 5 steps 3-9 (CEO root →
  COO → armed governed workers) cannot both hold on current source. A principal must not sequence
  around it — ceo-submit-arm → full arm → submit executes step by step only because the runtime
  sink does not yet consult the eligibility gate, and it leaves CEO-submit un-disarmable until the
  full disarm — and must not author the widening. The designed extension point is a reviewed
  coexistence/eligibility wave commissioned by Sol/Chairman; until it lands the acceptance operation
  can only run as a labelled PARTIAL rehearsal and never records AUTONOMY_V1_PROVEN_LIVE.
kind: constraint
verified_at: 2026-10-04
verified_by: >
  Seat reads at origin/master a2646f45 (autonomy_control.py differs from 84df2980 only in
  ProductionArmHost :2478-2532): derive_candidate_configs :740-753; evaluate_ceo_submit_arm_admission
  refusals :1569/:1571/:1573; evaluate_ceo_submit_disarm_admission :1656 with
  full_autonomy_armed_unsafe_coexistence :1708; proves_safe_coexistence default REFUSE :4424-4425;
  ceo_submit_sink_eligible :1147 (worker harness must be False; docstring: runtime sink does not yet
  consult it); load_unarmed_configs :2386 checks only the three autonomy/harness flags;
  executive_service.py :2374 (root binding freezes coo_operator_harness_armed), :5520-5540
  (_is_bound_coo_root requires every binding field equal), :7151 (runtime sink checks only
  ceo_submit_armed); executive_coo_cycle.py :491; executive_runtime.py :14820;
  codex_provider_realm.py :862 (sealed realm admits only while disarmed). Independent L3 Opus
  read-only census packet (CP-2, F2) consumed 2026-10-04T05:06Z; DEC:FIRST-WEB-CEO-ROOT-BINDS-THE-ARMED-OPERATOR-HARNESS concurs on the stranded-root half.
scope:
  - mastermind
  - mastermind:ops/executive_os/autonomy_control.py
  - mastermind:control_plane/executive_service.py
  - WS:EXECUTIVE-AUTONOMY-V1-CLOSURE
confidence: verified
---

## Why this matters

Two lawful-looking procedures were in circulation on 2026-10-04: the CEO seat's "full arm, then
summon" and the principal's first draft "CEO-submit arm, submit, disarm, full arm". Neither
survives the source: the first cannot arm the sink, the second strands the root. The only
executable third order exploits an explicitly unfinished gate. The fix is a reviewed wave, not a
sequence.
