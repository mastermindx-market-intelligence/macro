# Demand annual-component completeness — issue #11067

## Outcome and release qualification

The repair withholds a derived reading when its required annual inputs are absent. It preserves reported zero, defined calculations, chain signals, beneficiary reads, the existing annual-row choice, and display-only fingerprint classification with score cap 60.

Native validation is complete: **72 passed, zero skipped** on Python 3.14.7. The expanded suite against original application source records **27 failed, 45 passed**. Those failures include the deliberately corrected CFO-as-FCF contract and new unavailable-disclosure expectations; they are not a claim of 27 independent defects.

This is a **Draft, unarmed source contribution**. Natural CI and interactive browser acceptance remain outstanding. No covering production render, deployment, or live acceptance is claimed.

Related issue: [#11067](https://github.com/mastermindx-market-intelligence/macro/issues/11067). Original acceptance: [#1157 comment 6804733051](https://github.com/mastermindx-market-intelligence/macro/pull/1157#issuecomment-6804733051).

## Source and contract

Source/data pin: `1be0661c6b7edfe4088fee71ada89a6b454ba095`. Publication parent: `16e874433e0ff0fb0ad863b839deb1d16f824005`. The complete seven-commit/eight-path parent comparison changes only unrelated Forex and marketing paths; none of this proof's source or data inputs changed.

- FCF requires both CFO and capex. Missing capex no longer turns CFO into a manufactured FCF value.
- Net debt requires long-term debt, current debt, and cash at both endpoints before a change can be displayed.
- A trend needs both defined endpoints; an undefined comparison is unavailable, not flat.
- The existing FCF-trap conjunction is three-valued: a known false conjunct remains false; unresolved required input is null; the established true condition is unchanged.
- The template displays a dash for unresolved values and trap assessment, with paired English/Chinese explanatory copy.
- The old test that explicitly required CFO-as-FCF is intentionally replaced. Valid zero and the original ±3 percentage-point threshold controls remain.

No raw store schema, source policy, score, annual selection, alias precedence, threshold, or rounding policy is added.

## Actual committed-data proof

The real native `_collect()` and full `build()` consume **15,869 statement rows / 2,838 tickers**, plus the pinned membership, revisions, RPO, and headcount stores. Both chain signals, all **139 beneficiary reads**, and **11 payer rows** are populated. Direct nonempty burden calculations equal the builder result, so its catch-all cannot hide an exception.

The repair changes these three current displayed net-debt deltas:

| Payer | Selected FY | Original delta ($B) | Repaired display |
|---|---:|---:|---|
| META | 2025 | 37.93 | unavailable |
| ORCL | 2026 | -20.57 | unavailable |
| PHM | 2025 | -0.35 | unavailable |

These numbers were not admitted measurements: at least one required balance component was absent. The repair withholds them; it does not estimate a replacement.

All **139 beneficiary reads** and both chain signals are identical between versions. Signals SHA-256: `4ebdb4d68af5e4c96daa7127b2cb9863007d4083ca3448c688ed6d04ddd6ec19`. Reads SHA-256: `df5c5d184a95e3e5c4de838e36b934dce278aea354030a04228f50c26632fba0`.

The retrospective cumulative-FY audit contains **44 eligible payer observations**. **14** change: 13 net-debt comparisons become unavailable, and one undefined capex/OCF trend becomes unavailable. Every changed field becomes null; **zero numeric values are added or remeasured**. This is incidence analysis of the pinned cached annual statements, not a point-in-time backtest or validation of a trading signal.

## Populated native fixtures and page output

Fifteen independent companyfacts scenarios run the actual SEC-shaped parser, temporary Parquet, chain and beneficiary joins, burden calculation, full Jinja builder, and bilingual payer-row inspection. Each has all 11 economic spenders, six fiscal years, both current chains, and two real beneficiary reads with populated consensus joins.

The cases cover complete inputs; missing latest/prior/all capex; each of three balance components missing at each endpoint; reported zero capex/cash/debt/FCF; and zero latest CFO. The unrelated signals and reads are identical between code versions for every identical fixture.

The fixture values are fabricated test inputs, not issuer financial claims. The fixtures isolate external fetch/pacing, unrelated debt-cache/alert writes, and the final page-write adapter. Parsing, calculations, joins, and Jinja rendering run unchanged. The separate emission below exercises the real final writer. No replacement calculation or fake application module is used.

A separate native emission follows the **actual `lib.pages.write_page()`** path, including the inline data shim, shared-shell injection, exact theme baking/minification, normal navigation assets, and local fonts. Its combined fixture shows missing capex, a missing balance operand, true zero FCF, an existing trap badge, and missing prior capex together. The second page uses the actual pinned current data. Both emitted pages have 11 payer rows.

- Combined fixture HTML SHA-256: `28b1d7246ad96cc8b0d7813b40a0ff6e5e2a70f30bfc2645e911ee5b65e69e5e`.
- Current-data HTML SHA-256: `866c6132400c9d5c1b960d2c5ba25e01969d4a4830ec180f8567479f121636fa`.

**Browser boundary:** navigation to the preview returned connection refused. Subsequent inspection of that tab was explicitly rejected by the browser URL policy because the current protocol was not allowed. The action stopped. Emitted HTML and native render inspection are not browser interaction, responsive-layout, or production proof.

## CI enrollment

The existing CODE owner `synapse-read-gate` gains a separate command:

```text
python -m pytest tests/test_gov_exposure.py -q
```

Its existing command and steps remain byte-identical, preserving the separate live contribution in #10211. Only this test is removed from the unrun baseline. The existing DATA builder enrollment is unchanged.

The actual native loader measures **401 owners / 328 CODE owners**, with the other **400 definitions and weights unchanged**. This owner's weight is **46 → 49**, commands **7 → 8**, test paths **19 → 20**, and joined command characters **981 → 1,028**. Only its **+3** contribution is funded: probe ceilings **5966/5989/5724 → 5969/5992/5727**. Job ceilings **137/138/131**, ten-pack maximum, install string, gates, and admission controls are unchanged.

This is isolated owner accounting. A full-tree planner run was not performed locally; natural CI must qualify the actual composed tree and packing probes. No other unmerged contribution is pre-funded.

## Reproducibility and preserved limits

The companion JSON contains exact input and candidate Git blobs/SHA-256 values, native test log hashes, every before/after fixture, all current/historical payer outputs, the CI receipt, emitted asset manifests, and executable audit source.

The existing missing-latest-CFO row selection, duplicate/nonconsecutive FY behavior, and nonfinite-input admission are outside this bounded repair and remain unchanged. The former diagnostic's broader claims are not silently adopted. No issue is auto-closed, no merge label is armed, and no release or browser hold is cleared by this report.
