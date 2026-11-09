# Pinned consumer-function reproduction — 17 October 2026

**Accepted scope: isolated execution of exact pinned function bodies and captured inputs. Full runtime, book/prompt/ledger parity and consumer cutover are not established.** This is the next source-comparison phase of the existing Grey Deer continuation, not a new adapter, policy or publisher. No fitted model, trial registration or production write occurred.

## Identity and method

Mastermind source commit: `a552a5e506ae808efa575c2e13cb56f478c72b87`. Macro captured inputs: `ab5156a4b2c336181f3c5256e7c0766f04f99598`, using `data/regime/latest.json` and `data/risk_envelope/latest.json`. The [receipt](receipt.json) binds raw source hashes and input blobs. The original runner SHA256 is `c18ff6b7b5807f3b4c32b35474d1e52c377ecbc794fe8ceced0932935181d9b2`; receipt SHA256 `b97f8950faaed8b7772b5228ea6defe4a9bb62b327f756ef60928284079e718e`. Original files are retained unchanged.

The [runner](consumer_repro.py) parses five SHA-verified source snapshots and executes only named function definitions and literal constants. It does not import the live modules. `view`, `build`, `risk_state`, sizing, rank, execution and persistence entry points are never called. First-party imports are deliberately denied; `_trading_days_since` consequently uses its native weekday fallback on the October 16–17 fixture interval. That interval contains no relevant holiday. The native five-session fallback configuration is used through an empty injected config. The declared research clock is October 17 at 07:30 UTC; actual execution time is recorded separately. These bindings are part of the result, not assertions about production configuration.

The [method and vocabulary addendum](METHOD_AND_VOCABULARY_ADDENDUM.json) lists every selected function, original line bounds and source-segment hash. It retains the original state-only test and adds an otherwise paired `elevated` / alert-false versus alert-true comparison. A reasoning-only reviewer supplied useful conceptual qualifications but could not see the script in its context; this is not claimed as independent line-by-line code acceptance. Parent review verified the code, source selections, consumed fields and returned values.

## Results and limits

| Case | Executed result | Meaning |
|---|---|---|
| Captured October 16 Radar | Caution becomes `risk_off`; magnitude 0.22; intensity 82.7 becomes confidence 0.827; status `validated` under the existing family/freshness contract. | Reproduces the existing projection. Its historical family status is not exact-current forecast calibration or numerical authority. |
| 1. Caution with can_force:false and withheld probability | Legacy risk-off vote remains; magnitude is null; gate projection returns state/source only. | Action, probability qualification and legacy consensus semantics remain distinct. No new policy judgment is inferred. |
| 2. Only intensity changes: 30 to 90 | Confidence changes 0.3 to 0.9; magnitude remains null; the single-source tilt remains −1 in both cases. | Intensity is used as the field named confidence, but does not weight the discrete tilt mean. |
| 3. Native vocabulary | The source enum includes calm/watch/caution/elevated/risk-off. With alert:false, elevated gives a neutral Market View direction; with alert:true it gives risk-off. **Held-risk returns ok in both elevated cases when legacy risk_state is risk-on.** | Market View's alert branch must not be omitted from the conclusion. The held-risk vocabulary omission is separate and survives the active-alert counterexample. No claim that today's captured caution packet was missed. |
| 4. New wrapper with older source | October 17 wrapper versus October 16 inner source is rejected with source_session_mismatch. | Working protection: a new wrapper cannot refresh the underlying session. |
| 5. Measured state with unavailable hazard | The actual October 16 Envelope qualifies as descriptive context, retaining measured score 40, null hazard, required-source qualifications and four false authority flags. | Preserve independently valid observations and explicit unavailable inference. Null hazard does not erase measured state. |
| 6. Newly written file with an old tail | The native tail reader returns caution from a January 3, 2000 fixture; its date, obsolete definition and maturity are not returned. The gate projection also reduces the source to state/source. | A source-path staleness/provenance loss if this fallback is used. This is not a claim that a production fallback ran or changed a position. |
| 7. Same underlying evidence through advisory context | Adding the qualified Envelope through the existing Neural Web adapter leaves tilt and contributor count unchanged; its status remains advisory, direction null and context is preserved. | Working anti-duplication boundary in this fixture. No independence claim or extra numerical vote is created. |
| 8. No-effect boundary | Five source snapshots, captured input objects and Macro checkout status are unchanged; no live first-party modules load. | Isolation is verified. Full live book, policy, prompt and ledger parity was **not tested**; this does not pass cutover acceptance. |
| 9. Future source date | With only inner risk_radar.asof changed to 2099-01-01, returned freshness.asof is 2099-01-01, age is 0, stale:false, future_dated:false and family status validated. | A reproduced source-clock guard defect. The exact consumed field is observable; it did not fall through to an absent/default date. No production harm is asserted. |

The future-date call path is `_adapt_risk_radar → _plane_record → _freshness → regime_frame._trading_days_since`. The last function clamps both same-day and future dates to zero; the caller tests for a negative age that this helper does not return. Any repair must use the proper source-session/clock contract and preserve other consumers' approved calendar behavior.

## Acceptance disposition and next action

The planned eight-case comparison is complete only at the **source-function** level; case 8's full runtime parity gate remains open. The additional ninth case supplies a concrete clock regression for the next repair. The current programme still lacks new authenticated backend-to-user delivery and a qualified live Portfolio cutover. This receipt cannot stand in for either.

Next: preserve these source findings, implement the smallest per-component clock/qualification repair through the actual owner, then capture real consumer input/output and unchanged policy/book/prompt artifacts before any consumer authority change. The original warning carrier, source/release constraints and Portfolio/Prophet numerical owners remain controlling. Do not rerun the frozen historical census or stage-1/stage-1b to obtain this proof.

## Reproduction

Use exact `git show` exports from the Mastermind pin for the five paths named in the runner's `SOURCES` map; use slash-to-double-underscore filenames. The runner refuses any mismatched source hash. The Macro checkout must contain the pinned captured inputs and be clean.

```text
python3 consumer_repro.py
  --sources <directory of pinned Mastermind source exports>
  --macro-repo <clean Macro checkout containing ab5156a4b2c336181f3c5256e7c0766f04f99598>
  --output <new scratch output directory>
```

The output directory must not exist. It contains the declared old-tail fixture and original receipt. The separate vocabulary addendum executes the paired alert-only change and records the consumed future-date path; it does not rewrite the first run.
