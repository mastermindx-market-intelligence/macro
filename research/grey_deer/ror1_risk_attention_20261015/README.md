# ROR-1 — risk-awareness incident research (2026-10-15)

**Scope:** characterizing the issued Risk Radar ledger and source-native replay/live
gate behavior. This is **not** a newly validated forecast, production warning
publisher, market-risk score, trading policy, alert delivery mechanism or episode
authority. Research home: [Mastermind #1478](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1478).

## Reproduce

From an eligible Macro repository checkout with installed pandas/numpy:

```bash
python3 -m unittest discover -s research/grey_deer/ror1_risk_attention_20261015 -p 'test_*.py' -v
python3 research/grey_deer/ror1_risk_attention_20261015/audit_suppressed_risk.py --jsonl data/risk_radar/forward_log.jsonl
```

`test_native_risk_radar_gate_parity.py` intentionally CHARACTERIZES the
current divergence between `context_gate_series` and `context_gate_live`.
Those tests assert the documented defect exists; on repair, invert/replace them
with parity assertions and regrade every affected historical population.
Use `ROR1_MACRO_ROOT=/absolute/eligible/macro-root` only when executing these
research tests outside their repository tree. No source/live flags are changed.

## Evidence and exact source

- Research base Macro main: `9df20a3ac37d1f33d616d871abfd9857f8cd5d26`.
- Issued-ledger source observed at `8d272434f222d6736a09e757a339444c8ef56c46`, matching later base blob.
- `data/risk_radar/forward_log.jsonl` Git blob `4d8c65e711db560c24088bc6380eaecd07db2afd`, SHA256 `240c202431cc160ca8ec53ec65125c2f9d858597bea60e416a91f01dea55017d`, 66 records spanning June23–Oct13.
- Native `engine/risk_radar.py` Git blob `94222d44ec102e728da5443e2082da73ad29f17f`, SHA256 `31668c7fe097cdf631edb6cca6e77990b40afdb3d4cb37d27596336689afe70d`.
- First suppressed source session Sep24, recorded issuance Sep25 05:17:05 UTC; last source session Oct13, issuance Oct14 06:02:59 UTC.
- 13 of 13 prospective recorded rows published Caution/no alert while `state_ungated` was Elevated (3) or Risk-off (10); **none was graded**. 48 older rows have nonnull outcome grades, which do not validate the 13 current readings.
- The 13 rows are consecutive *recorded observations*, **not confirmed every NYSE trading session**. Early-warning effectiveness, provenance, independence and customer delivery remain open.

The isolated M2 research root first demonstrated RED against a stub, then
**8/8** ledger-audit tests and **5/5** native-source characterization tests
passed. The portable native test variant also passed 5/5 against the exact
read-only imported source. This evidence establishes functional semantics,
not forecast precision or deployed behavior.

## Metric-name discrepancy in existing tuning research

`METRIC_DEFINITION_FINDING_20261015.md` reproduces a historical report
mismatch: `research/RISK_RADAR_TUNING.md` labels four values
0.915/0.751/0.901/0.741 as false-positive rates despite their exact
identity with `1 − precision` (false-discovery rates). Using the
full-history report's rounded 17% fire-rate, precision .249, and
its H21/5%-event upper bound .1890 for H21/8%-events, ordinary
false-positive rate is bounded approximately .12767–.15742 **if**
those figures have matching eligible populations. Recover original
TP/FP/TN/FN and episode counts before using any derived cost budget.

Pure `metric_definition_audit.py` and `test_metric_definition_audit.py`
were RED-then-GREEN 4/4 locally. No historical numerical model was rerun.

## Related true owners and release constraints

Grey Deer #8132 owns a different held candidate for warning projection and
native banner wiring. Macro #9428 owns a separate held incident-response
candidate and active review; neither is superseded by this research branch.
Source publication, hosted CI, technical review, merge, installation and
authenticated browser/notification acceptance are distinct steps.

**No arbitrary gate removal.** The prior context gate was meant to control
false-positive alerts. A prospective ungated severe run across 13 recorded
observations creates alert-fatigue risk if blindly promoted. Study episode-
level factual attention and data-health disclosures separately from future
SPY drawdown forecasts and all capital sizing/selection authority.

## October 14 published artifact consistency — real pinned observations

The separate offline audit compares five committed Macro artifacts from
`1b12af09222df183ac61ed5bcabb1ecc6bf5c735`. A minimized
`evidence/artifact_boundary_inputs_20261015.json` preserves their exact
Git blob references and only fields required for this question.
`evidence/artifact_boundary_findings_20261015.json` is the deterministic
result. It does NOT establish what an authenticated subscriber saw.

Reproduce without network, credentials, a source writer or new alerts:

```bash
python3 research/grey_deer/ror1_risk_attention_20261015/audit_artifact_consistency.py \
  --bundle research/grey_deer/ror1_risk_attention_20261015/evidence/artifact_boundary_inputs_20261015.json
python3 -m unittest discover -s research/grey_deer/ror1_risk_attention_20261015 -p 'test_artifact_consistency.py' -v
```

Read-only source comparison found five distinct observations:

1. Site Risk Envelope for October 14 includes **FRESH native Leadership
   Crack `CRACKING`** and `dislocation=true`, but its hazard stage is null
   with reason `required_source_state_unmapped`. This is a **confirmed
   artifact-local mapping drop**, not an assertion of systemic contagion.
2. Site Risk Envelope is October 14 while `data/risk_envelope/latest.json`
   remains October 13. They were generated at different times; this is a
   **publication variant mismatch**, not by itself a pipeline error.
3. The persisted `data/leadership_crack/latest.json` is October 8 `INTACT`
   but site envelope contains October 14 `CRACKING`; reconstruct exact
   source/vintage lineage before deciding how consumers bind to each variant.
4. Context-only Neural Web plane reads 50/Mixed under an October 14 date
   while measured October 14 Market State is 44/Mixed. Production clocks
   differ; do not claim the older model was false when it was produced.
5. Market State explicitly reports four stale input families despite its
   October 14 score. These require a user-facing data-quality qualifier.

**Original owner already has the mapping fix:** existing Macro Draft #9428
includes `CRACKING → FRAGILE` in its held source head; do not create
or merge a competing adapter. The permitted descriptive stage is
`FRAGILE`, not `TRANSMITTING` or `BREAKDOWN` without competent evidence.
Existing alternate producer/consumer and read-permission holds still apply.

**Verification:** ten tests passed after test-first RED; the pinned bundle
replays to the exact same JSON findings receipt hash
`429605fc52fba14f63253416674f8ba5abfb5d97db89b6939e222d962a3cf979`.
No original source artifacts were edited and no production service was invoked.

## Source-native verdict date lost in Neural Web compact export

Sixth independently read original source:
`data/neuralweb/world_state.json`, Git blob
`5a79f3a14b90bad891d0fdba808c5176ea9fe51d` at the same
Macro main observation. Its verdict is **50/MIXED as of October 13**
(`world_state.verdict.asof`), while world-state `produced_at` is
October 14 19:32:19Z. The compact plane uses
`build_market_plane() -> _asof_of(world_state)`, which falls back to
the **processing timestamp** because world_state has no top-level
`asof`/`as_of`, so the plane labels itself October 14. Its verdict
projection copies label/score but not native verdict `asof`.
Top-level plane `stale=false` is a separate world-state freshness
decision; it does not certify the verdict's native session.

This is a **confirmed provenance-field omission**, not proof that the
October 13 reading was stale at 15:35 ET before the October 14 close.
The safest consumer-compatible response is to retain a typed native
verdict source session and input-health qualifier **additively** in
the existing plane projection, without treating `produced_at` as
the observed market session, recomputing risk, or changing forecast
and capital permissions. Route eventual code changes to the existing
Neural Web owner with current source custody and consumer tests.

Accepted five-source inputs/receipt remain immutable. Additive
`evidence/plane_provenance_inputs_20261015.json` and
`evidence/plane_provenance_findings_20261015.json` preserve the six-source
same-pin view. Its full ledger consists of the previous five qualified
artifact findings **plus** `VERDICT_SOURCE_SESSION_LOST`.
The new receipt SHA256 is
`2e842e286f19e2b11303670b878434f7b8eb2c4d05b3a39f7f1839c96d6c8a25`.
Two new test-first cases prove date-loss detection and no-false-finding
when native source session survives the plane projection.

Reproduce with the same `audit_artifact_consistency.py --bundle`
command above, pointing at the new `plane_provenance_inputs` file.

## Next acceptance

Native source-vintage/issuance-bound episode replay, a predeclared negative
control set, reasoned revisions after backtest population changes, source
publication/entitlement readbacks and real long-open user delivery proof by
the existing owners. Until then, this is research only.
