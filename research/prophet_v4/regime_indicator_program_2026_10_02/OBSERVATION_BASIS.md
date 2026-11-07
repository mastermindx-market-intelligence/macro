# R1 increment: provisional versus completed observations

## Source finding

At macro `85932a1b7ce0e597ad73e713f7528101e4ef58d9`, `engine/confluence_tiers.py` lines 680-699 explicitly distinguishes the completed interior of `tier_stream` from its final, potentially provisional row. Historical day-D live replay requires an as-of day-D computation/snapshot, not reading row D from a later finalized stream. The source also distinguishes the raw close-only stream from the live validated master-take semantics. Neither bar alignment alone nor a raw T1 label establishes full incumbent parity.

This is an existing documented contract, not a newly proven production defect. No production function, provisional flag, validated-take rule, clock anchor or golden vector was modified.

## Change in this research component

The initial intake comparer was conservative and admitted only completed-bar manifests. That was insufficient to compare the incumbent's lawful provisional observations. It now explicitly distinguishes:

- `completed_only`: completion must be declared true. Existing completed-only fixtures remain compatible.
- `asof_snapshot`: completion status must be boolean; the snapshot must be declared owner-qualified, have an immutable owner receipt reference, and bind to the same decision-cut digest.

Unknown/hindsight observation policies, unqualified snapshots and mismatched snapshot cuts fail the diagnostic. Mixing finalized and as-of policies cannot be described as a pure grain/kernel/session comparison. It can be an explicitly labeled policy-bundle comparison with all other paired identities checked.

This remains a declaration-consistency diagnostic. A receipt string or qualification flag is not self-authenticating proof. The existing source/evaluation owners still verify the underlying snapshot, information window, timing, formula and selection policy. The adapter grants no admission, rank, entry, sizing, trading or promotion authority.

## Verification

A ten-test observation-basis suite was written before the implementation change. Against the initial component it produced eight expected failures and two passes. After the change, the complete local suite produced **48 passed plus 34 subtests passed**. Exact published sources at `623291b4518de292c8e25fbe14481708b5853066` were then hash-verified and run on the connected host: **48 unittest tests, OK**.

These are the same tests in two environments, not 96 independent tests. No new outcome backtest or production acceptance is implied. The R0 real-source report remains bound to its original source and hash in `EVIDENCE.md`; its ledger and grid results were not rerun or silently relabeled as results from a different program revision.

Current component SHA-256: `4e26b7e0df113145bc8a1ab20bfce0790550329ae39371fdd1d985c9933c317d`.

Additional test SHA-256: `32fefceed62d1f2f632f140056ccb0d427bb7c659c7e9358b4637582d172fdb2`.

```sh
python -m unittest -q test_intake_audit test_observation_basis
```

Remaining R1 work: actual source-snapshot/receipt binding through the existing evaluator, full indicator warm-up and formula parity, market-specific data/clock qualification, and incumbent validated-take versus research-species identity. Do not treat this focused increment as completion of TOI W1/W2-0 or Temporal Grain.
