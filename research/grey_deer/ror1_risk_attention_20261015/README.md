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

## Next acceptance

Native source-vintage/issuance-bound episode replay, a predeclared negative
control set, reasoned revisions after backtest population changes, source
publication/entitlement readbacks and real long-open user delivery proof by
the existing owners. Until then, this is research only.
