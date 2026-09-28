# GD-6A US market-eligibility: zero-policy shadow intake

**Status: PARTIAL / source implementation; NOT live, NOT full GD-6A acceptance.**

Operation: `gd6a-us-shadow-intake-20260928-sol-001`. Existing owner:
`WS:GREY-DEER-RISK-INTELLIGENCE`, GD-6A. Parent integration: Macro #6817,
`PROPHET_RISK_RESEARCH_R1_20260927_SOL`, adjudication 5865326642.
Source carrier: `claude/gd6a-us-shadow-intake-20260928`. No incumbent writer,
source lease, H1/Cycle study or parallel UI release is transferred.

## 0. Acceptance and current boundary

This slice is not complete for release until the new tests are registered in
an existing CI owner, executed against the actual native composer, independently
reviewed, and qualified at the exact integrated head. No merge-on-green, automatic
merge, scheduler, publisher or live feature flag is added. The full GD-6A wave
also owes the original ordinary-publication and counterfactual-accrual proof.

Current `engine/risk_envelope.py` produces `policies=[]` and `episodes=[]`, with
all envelope action permissions false. This implementation supports exactly that
native v0 policy state. It does not fabricate an active risk rule to make a test
or a product screen look finished. An unknown/nonempty policy input is reported
UNAVAILABLE. Individually authorized policies need a separately reviewed producer
and consumer extension through the same owner, not a second risk engine.

## 1. Correct owner recovered

The R1/R2 search for a generic recommendation-policy join is narrowed by existing
`DEC:PROPHET-RANK-PRESERVED-MARKET-ELIGIBILITY-SIDECAR` and the Grey Deer architecture
and execution packet. They already define `prophet.market_eligibility/v1`, computed
server-side after raw rank, exact board hash/session binding, lossless dispositions,
and a shadow-only birth. This is an implementation of that owner, not a replacement.

Observed baseline: Macro `1690e69040d2c6bea46c2ed1c3c06c51b311732c`; source carrier
starts at later main `03e8961d22b48cc65666f6318ee8c8bd610f3caa`. Native envelope blob
`3b0df2d426f50245142b943e38faf4996f96e995` is unchanged at both.

Native source references:
- `agentos/decisions/DEC-PROPHET-RANK-PRESERVED-MARKET-ELIGIBILITY-SIDECAR.md`
- `research/grey_deer/GREY_DEER_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE_2026-08-19.md`, sections 5-10
- `research/grey_deer/GREY_DEER_FABLE_EXECUTION_COMMAND_PACKET_2026-08-19.md`, GD-6A
- `engine/risk_envelope.py`, composer, coverage, per-source freshness and bundle identity
- `scripts/build_risk_envelope.py`, settled source selection and `stale_after=None`
- `scripts/build_prophet.py::_freeze_origination_source_board`, existing raw-byte receipt
- `engine/us_board_rank.py`, current and fallback board definitions

## 2. Implemented capability

`engine/prophet_market_eligibility.py` composes one deterministic shadow disposition
for each row in the exact raw board's `/buy` array. The pointer and raw position are
not new security, issuer, episode or plan identities. Raw rank is copied only when
`prophet.rank` exists; it is never inferred from array position. Other raw candidate
fields are retained unchanged by the server-side `bind_shadow_view` projection.
The off-board candidate-pool owner is not replaced or reconstructed here.

The input boundary checks the independent expected raw-board digest, definition
and session; raw-envelope digest AND native semantic bundle; market, revision,
authority, zero-policy schema, coverage and per-source clocks; observation/emission
order; and an explicit caller-supplied validity window. The native settled composer
has no expiry timestamp. This module therefore does not invent a trading calendar
or claim that a content hash proves freshness. The caller must bind the actual
expected session and window through its existing native source/clock owner.

Malformed/mismatched board inputs refuse because the denominator is not trustworthy.
An intact board with missing, stale, unsupported or incompatible envelope data keeps
every raw row and emits UNAVAILABLE; it is not an empty market or a Calm forecast.

An AVAILABLE/ELIGIBLE row means only **no constraint in this qualified zero-policy
observation**. It is not a buy recommendation, B4 ENTRY_OPEN, a holdings decision,
or permission to use a shadow strategy. All eight downstream authority booleans
remain false. `production_behavior` is always `UNCHANGED`.

The read consumer recomposes all semantics from independently supplied inputs.
Rehashing a changed action, row order, permission or expiry cannot make it valid.
The validity interval is half-open. Corrections remain separately bound bytes;
no changed observation is backdated into an order or a historical decision.

`scripts/build_prophet_market_eligibility.py` is a real stdout-only qualification
entry point. It requires explicit source files, expected hashes/session/definition
and decision/window clocks. It writes no source file, snapshot, ledger or public
artifact. Exit 0 = available shadow; 2 = typed unavailable shadow; 1 = refusal.
A missing file is not silently converted to an observed zero-policy source.

## 3. Actual evidence and its limits

Executed in Python 3.13.5:

```sh
PYTHONDONTWRITEBYTECODE=1 python tests/test_prophet_market_eligibility.py
```

51 tests passed, zero failures/errors/skips. They execute the new module, its
consumer and CLI with synthetic inputs. The exact three source/test Git blobs
were checked against the locally tested bytes after remote creation.

Four in-memory negative controls were killed by assertions: accepting a caller's
replacement board hash, granting live entry permission, dropping raw rows, and
ignoring consumer expiry. The row-drop mutant also raises three downstream errors;
those errors are not its claimed kill evidence. The first mutation harness demanded
zero errors and consequently stopped; the retained corrected report separately
counts assertion failures and errors. No production or tested source was mutated.

These are not market observations, native-composer integration, full-checkout tests,
hosted CI, authenticated UI/API/send proof, outcome accrual or predictive evidence.
A large committed board read returned no content through the current file adapter;
that is not a claim that the actual board file is empty. No real-board run is claimed.

## 4. Existing CI owner: exact unlanded registration

The existing `.github/ci/legacy-jobs.yml` step named `synapse read-gate unit tests`
already runs `tests/test_risk_envelope.py` and `tests/test_live_risk_envelope.py`.
Add the new suite to THAT command after checking the current manifest/preimage:

```text
python -m pytest tests/test_synapse_read_gate.py tests/test_horizon_firewall.py tests/test_delivery_waterfall.py tests/test_pricing_power_monitor.py tests/test_risk_envelope.py tests/test_live_risk_envelope.py tests/test_prophet_market_eligibility.py -q
```

This registration is identified but **not applied** by the current source slice.
Do not claim the test is owned/running because the new file triggered CI. No new
workflow, runner, queue or test-discovery trick substitutes for the owner update.
Native compatibility must additionally generate a fresh synthetic envelope through
the unmodified real `compose_envelope` and pass it through the new function, plus
required-source gaps, stale and live-provisional cases. No dependency stub qualifies
that proof. Review source-native fixtures rather than merely certifying fixtures
that reproduce this adapter's own assumptions.

## 5. Exact continuation

First finish native compatibility and existing-owner CI registration/review on this
same source branch. Preserve every known commit and do not start a duplicate GD-6A.
Then bind the existing Prophet builder's frozen-board receipt and normal settled
Risk Envelope into the existing after-rank publication path. Prove unchanged raw
board/index/plan output, lossless shadow counts, exact source bytes and the next
ordinary refresh; counterfactual accrual remains with existing QLedger/Chronicle.

Active policy support is a separate next capability: individually registered policy
ID/version, exact scope predicates and vulnerability matches, time/expiry/kill and
repair ownership, plus actual authorization. Intersect constraints without averaging;
unknown vulnerability is not low risk; one repair cannot lift another rule. A new
policy must not be injected into the current v0 envelope as a caller-controlled dict.
Live actionability and Portfolio gross/reduction authority remain separate promotion
boundaries. Original Grey Deer requirements remain controlling; R2's research claim
budget did not supersede them. No risk score threshold, full-zero liquidation policy,
personal holdings action or automatic exit is installed by this slice.

Protected procedure: Mastermind `5c6b010a6157895d4f697548c75263cdff641ea6`, compatible
Skillpack 1.0.1/bootstrap 1. The host compound process inspection was refused before
execution and was not retried or proxied. Independent native GitHub source work used
its observed repository write permission and fresh isolated branch. No host checkout,
existing PR head, source store, production publisher or worker was changed.
