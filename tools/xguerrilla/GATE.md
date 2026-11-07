# Synthetic harness regression model

This gate evaluates an explicitly synthetic model. FakeDriver never starts a
browser or contacts a provider. The scheduler, validators, typing and telemetry
helpers run against model inputs; lease, health, profile and quarantine models
are not incumbent runtime owners.

Every emitted gate document, including errors and deliberate-failure drills,
contains:

- evidence_scope: synthetic_model
- runtime_binding_available: false
- live_gate_satisfied: false

The report's ok field concerns only the model criteria. A green model does not
satisfy the accepted masterplan section 26.9 real pilot or prove permission,
identity, original action settlement, live selectors, platform behavior,
prospective data or production acceptance.

## Model criteria

The retained five model criteria exercise synthetic child-day coverage,
keystroke interval shape, label spread, fake restart behavior and simulated
outage behavior. Historical local degraded-mode continuation and recovery are
regression specimens, not runtime policy. The current accepted masterplan and
incumbent owners govern any future real behavior.

The model uses a simulated clock. Fourteen simulated days are not fourteen
elapsed days. The default configuration-loading seam still exists; a bounded
synthetic qualification must provide explicit synthetic inputs instead of
silently reading real persona or proxy fixtures.

## Developer entry points

From the repository root, gate sim, criteria and drill are model-only commands.
The existing --seed and --store-dir options affect the deterministic model and
its local diagnostic outputs. They do not bind accounts or activate drivers.
Store directories and telemetry paths can appear in model output.

Exit 0 means the requested model checks passed; exit 1 means model criteria
failed; exit 2 means the model itself raised an exception. None is a live
acceptance code. The fixed evidence-scope fields accompany each JSON output.

Use the selected pure/fake tests that bear on a source change. The public
runtime refusal cases prove the absence of pre-binding effects; they do not
commission a real pilot. Existing source proof should not be repeated without
a changed behavior, authority or material input.

## Binding still required

The public CLI/state/profile/shadow interfaces and real-driver start/stop/choose
remain unavailable. See RUNBOOK.md for the exact surface and existing
reply_export/reply_queue/outbox/health owners. No token, environment switch,
fallback driver, local recovery or new controller makes the model authoritative.
