---
key: A-FLATTENED-ERROR-BOUNDARY-MAKES-MECHANISM-UNATTRIBUTABLE
claim: >
  When a boundary collapses every refusal onto one opaque code, no black-box test at that boundary can
  attribute a refusal to the guard that produced it, so a behavioural test can pass for a mechanism
  other than the one it was written to pin. Measured 2026-09-25 on Mastermind IAC-P1 C-B, where the
  gateway maps every `ConsultationRefusal` to `{"ok": false, "error": {"code": "EFFECT_UNKNOWN"}}` for
  all twelve codes in the closed set. A falsifier built to prove that a newly added wire-ceiling fence
  refuses Sol's named 641-backslash witness failed at the parent and passed at the repaired head - the
  textbook positive control - yet single-leg mutation showed it ALSO passes with that fence removed:
  an independent payload-budget clamp added by the same slice refuses the witness first, and the
  returned envelope is byte-identical in both states (ok=false, EFFECT_UNKNOWN, zero carrier writes).
  The fail-at-parent/pass-at-head differential proved only that SOMETHING in the slice refuses the
  witness, never which guard earned it.
falsifier: >
  Mutate away the specific guard the test names and re-run: if the test still passes, it is an outcome
  detector, not a guard detector, however cleanly it was positive-controlled. Pin the guard white-box
  instead - assert on source structure or on an internal typed exception raised before the flattening -
  and label the behavioural test for the outcome it actually proves. Do not "strengthen" a flattened-
  boundary test by asserting a distinguishing code there; the boundary cannot carry one, so the
  assertion would pin the flattening rather than the guard.
so_what: >
  A positive control at a flattened boundary is necessary but not sufficient: it licenses "this slice
  refuses the witness", never "this fence refuses the witness". Any suite whose guards sit behind a
  shared error-collapsing boundary - one exception type mapped to one code, a catch-all returning a
  generic failure, an HTTP layer flattening to 500 - needs per-mechanism coverage proven white-box or
  by solo mutation, and acceptance evidence should say which. Separately, the flattening is itself a
  reportable property rather than a defect of the slice that first meets it: fencing an effect before
  it becomes durable is only useful if the caller can tell "nothing happened, retry smaller" from
  "effect unknown, go reconcile", and a plane that cannot express the difference silently converts
  free refusals into reconciliations.
