# R5 participation study — reproducible research, not a live policy

Parent WS:CRYPTO-INTELLIGENCE / Macro PR8050. Baseline bf879ff6a26d2369d970dc583d89ba2aadab5e62. Frozen protocol3cc4e46d2b7827ba5fce746d5b4bcd1875fb80c6 precedes the new feature/outcome scan. Research implementation065f29376d82db77342a634496ccd2f4d97d0ab0. No engine/config/gate/collector/production UI changes.

## Contents

- ../r5_participation_study.py: frozen research generation, reusing R4 helpers and hash-pinned incumbent evidence.
- features.csv:647 parent-level observations; no look-ahead selection.
- events.csv:1,294 event scenarios; policies.csv:3,882 cost/delay account scenarios. Repeated scenarios are NOT independent observations.
- results.json: all48 policy summary cells plus event-group counts, source/input/gate identities and limitations.
- red.txt: five actual preimplementation import failures; green_core.txt / green_research.txt: targeted and full existing research-suite successes.
- verification_final.txt:261 passing combined tests,27 retained warnings; compile, existing source-claim checker and diff checks.
- verify_evidence.py / verification_extended.txt: independent condition/first-passage/cash-inventory arithmetic and all block intervals, executed by this same session. Not an independent reviewer.
- verification_arithmetic.txt: earlier narrower successful arithmetic pass retained.
- study_log.txt: original fixed study completed; no market-result amendment or rerun.
- MANIFEST.json: hashes of the source, protocol, report and final evidence files. It does not hash itself or the mutable Agent OS checkpoint.

## Reproduction

Within the existing repository, with the exact recorded data/source hashes:

```bash
python3 research/crypto_science/r5_participation_study.py
python3 research/crypto_science/r5/verify_evidence.py
```

Do not rerun merely to recreate an already-verified artifact. The generator refuses a changed inherited R4 source/input identity; obtain a separately frozen study when data or definitions change. No store write, provider endpoint, live forecast or gate writer is called. The R4 incumbent sidecar remains immutable research evidence and is not promoted to a new live store.

## Findings and limitations

Volume adds almost no downside discrimination after the specified persistent break: only7/171 price-qualified actions are excluded, with the same30 downside-first cases retained. Incremental mean -0.00178pp on586 primary common parents.

In recovery, volume raises the mean by+0.72003pp on53 comparable parents but the block95 interval is wide(-1.51734,+3.13450pp), periods differ and the effect is nearly zero when2020 is omitted. The volume policy still trails the incumbent overall and remains cash in31/53 parents. Its all-parent median drawdown of zero is not safety: entered cases have approximately13.42% median marked drawdown. No candidate earns promotion.

Report: research/CRYPTO_SCIENCE_R5_PARTICIPATION_RESULTS_2026-09-28.md. Unsigned Coinbase volume is participation, NOT signed buying/selling or measured absorption. Existing OKX taker data are CONTRACTS derivatives and were not falsely treated as spot. Historical publication timing, actual fills, funding semantics, independent review and forward-issued evidence remain open.

## Operational error transparency

An initial long protocol write returned Session terminated; exact-path readback proved absence before the smaller same-carrier recovery succeeded. A metadata-only gh call had TLS failure. A post-run read-only summary-print lambda failed because pandas3 groupby excludes its key column; the explicit group loop corrected printing only. None altered study definitions or result bytes. Expected RED log commands print their failure output; a trailing shell tail exit is not mislabeled as a passing pytest return. The actual final checks record each subprocess exit code.
