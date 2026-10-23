# PB-B research return

## STATUS

- Operation: `PB-B-US-JAPAN-CONSTRAINT-20261007`.
- Research cutoff: **2026-10-07 UTC**.
- Bounded commission: **complete; ready for PB-G / Sol adjudication**.
- Parent program: **not complete**. This packet is a research return, not a production or strategy promotion.
- Session outcome: **SESSION END: PROVEN_OUTCOME**, limited to the completed evidence package and its documented validation.
- Merge authority: **Sol**. Keep the child PR draft until Sol explicitly releases the hold. No merge-on-green or native auto-merge is authorized.
- CI state is not certified by this file. The PR envelope records the observed checks at publication. A draft with pending checks is not a fully ratified PARKED state.
- Watcher status: `NOT_WATCHER_ENABLED`; native in-session research agents completed their bounded work. No external watchdog or future automation was registered.

## RESULT

**Conditional U.S. leverage over the terms and instruments of assisted FX cooperation survives. A contribution to BOJ meeting timing remains credible but is not identified against domestic normalization.** The evidence does not support a generally dictated Japanese monetary or fiscal path.

The April 2026 survey and April 28 dissenting votes establish a useful pre-May baseline. They weaken the claim that the later private May conversation created June-hike expectations. They do not establish Japan's internal counterfactual plan or remove all earlier U.S. influence.

The overall qualitative ordering is **H1 ≈ H2 > H4 ≈ H3 > H5**, with endpoint-specific rankings in the assessment. These are competing, sometimes compatible explanations, not calibrated posterior probabilities.

For PB-G: preserve conditional leverage over assisted options, domestic normalization, compatible solicitation/stabilization motives, and an unmeasured timing channel. Weaken whole-path compulsion and attribution to a newly decisive late public statement. Reject a permanent veto, loss of every unilateral instrument, assumed executed FIMA enlargement or borrowing, and a mechanical expected-hike-to-stronger-yen rule.

The most discriminating additional evidence would be a dated Japanese decision record pairing the pre-May intended BOJ path with its response to an explicit U.S. support condition. The current study cannot reconstruct that missing internal counterfactual.

## EVIDENCE

### Deliverables

| File | Role |
|---|---|
| [PB_B_CONSTRAINT_ASSESSMENT.md](PB_B_CONSTRAINT_ASSESSMENT.md) | Main judgment, strongest evidence and counterevidence, domestic counterfactual, hypothesis rankings and falsifier |
| [PB_B_US_JAPAN_TIMELINE.md](PB_B_US_JAPAN_TIMELINE.md) | Fifteen episode summaries, public-information cuts, targets and source links |
| [PB_B_CASEBOOK.json](PB_B_CASEBOOK.json) | Structured source registry, input snapshots, hypotheses, alternatives, outcomes and abstaining forecast objects |
| [PB_B_EVENT_WINDOWS.json](PB_B_EVENT_WINDOWS.json) | Thirteen descriptive market windows with precision, confounders and missing data |
| [PB_B_SOURCE_LEDGER.md](PB_B_SOURCE_LEDGER.md) | Eighty-nine source records, edition and publication bounds, operational corrections and access limits |
| [validate_pb_b.py](validate_pb_b.py) | Reproducible structural and point-in-time guard checks |
| [PB_B_VALIDATION.json](PB_B_VALIDATION.json) | Passing validation and adversarial-mutation receipt |
| [PB_B_RETURN.md](PB_B_RETURN.md) | This bounded return and recovery record |

### Honest counts and forecast status

| Measure | Result |
|---|---:|
| Constructed episodes | 15 |
| Reconstructed public-input snapshots certified under the packet's bounded clock rules | 15 |
| Unique BOJ target decisions | 10 |
| Source records | 89 |
| Descriptive market windows | 13 |
| Prospectively locked forecasts | 0 |
| Accuracy-comparison-eligible episodes | 0 |

All **45 M0/M1/M2 forecast objects abstain**. The packet does not invent historical probabilities, calculate comparative forecasting accuracy, or claim an out-of-sample result. Input certification means that the selected public sources have supported availability bounds before each cut; it does not establish completeness, blind selection, historical byte hashes or causal identification. Multiple episodes share BOJ targets and the summer bargaining process.

### Validation and review

Run from this directory:

```bash
python3 validate_pb_b.py --self-test --receipt PB_B_VALIDATION.json
```

Result: **PASS**. The validator rejected four deliberately invalid mutations: a future fact admitted to an earlier input set; an invented retrospective forecast probability; a photographed/planned U.S. size promoted to executed intervention; and a facility proposal promoted to execution.

An independent in-session research agent returned **PASS** on the final semantic deltas and final assessment, without editing them. Its review covered the added April baseline, March 2025 control, same-day September CPI, effective-date/publication-date distinction, source-edition bounds, quote-time separation, and bounded causal language.

| Reviewed file | SHA-256 |
|---|---|
| PB_B_CASEBOOK.json | `50b807efddc840918e61e7a6e3d7c3455bda212d78b1b2ff80793d701fd588c4` |
| PB_B_EVENT_WINDOWS.json | `f64c7e0683fe5fb96e67c909509818b5457cab8e95c496b1625faa53cddbfb07` |
| PB_B_CONSTRAINT_ASSESSMENT.md | `5e94f1e7b65b7487c8f9b47ac62097a5448f2574aea7d4876e7b57b0b7dcda42` |

The validator checks structural consistency and clock/amount guards. The written review addresses source interpretation. Neither supplies an independently estimated causal coefficient.

### Authority and immutable source pins

- Repository: [mastermindx-market-intelligence/macro](https://github.com/mastermindx-market-intelligence/macro).
- Parent commission: [draft PR #8560](https://github.com/mastermindx-market-intelligence/macro/pull/8560).
- Requested handoff: `research/policy_behavior/handoffs/PB_B_US_JAPAN_CONSTRAINT_PRO.md`, read at `7abc3dc596c5a6463effb37422bf9bd34bbdf1ba`; blob `2df6f7fe8355a860e06421def1817944310214e3`.
- Frozen parent masterplan, preregistration and seed head: `ee86db2c832c73a36837c1240df871700340d6da`.
- Protected Mastermind governance pin: `9a24ef2c4b27ac95a4d1f72f5eae1073657cd7c2`.
- Fresh default-branch base used for this work: `007e0cccbd06f089605ba122efc658f406043dd3`.
- Isolated child branch: `claude/pb-b-us-japan-constraint-20261007`.
- First durable research checkpoint: `57dcfa9f1924611870a8052feb7dde099c5cd7c6`.
- The immutable final content commit is the commit containing this packet; its exact SHA is recorded in the child PR envelope and delivery response.
- Allowed write scope: `research/policy_behavior/pro_returns/PB-B/`.
- Applicable AGENTS and CLAUDE blobs were read in full and verified unchanged at the work base: `367c567422f3554828f3fa57805811aa81a41df6` and `5d3c9b1936574af58581b03d149b4160119b1e79`.

## GAPS

The remaining gaps limit inference rather than conceal unfinished data construction: the pre-May internal BOJ plan and precise accepted support terms; a primary private negotiation record; executed U.S. July intervention size; unreleased Q3 operational accounting at the cutoff; original letter access; synchronized raw OIS, JGB, UST and FX ticks; and complete historical publication-byte archives.

A later reconstruction may substantiate an earlier private act without becoming public information at that earlier decision cut. The retrieved September 18-updated report remains outside all earlier decision-time inputs. Source clocks and subsequent accounting are explicitly separated.

## DEVIATIONS

No change to production, policy engines, RIC, dashboards, scores, ranking, sizing or a new control store was made or authorized. No merge or deployment is part of this return.

The commission's historical model-comparison structure is preserved with explicit abstentions because no prospectively locked forecasts exist. The market component is an event-window inventory with explicit nulls, not a falsely precise causal event study.

## Continuation for PB-G / Sol

Review the endpoint-specific claims and determine which survive into the parent synthesis. Any subsequent forecast evaluation needs a new prospective lock, declared targets and comparators, and an honest dependence structure. Any expansion into missing private records or higher-frequency market data is a separately bounded research assignment. Keep this PR draft unless Sol explicitly releases the merge hold.
