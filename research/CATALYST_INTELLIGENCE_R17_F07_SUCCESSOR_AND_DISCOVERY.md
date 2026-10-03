# F07 successor and options-led discovery — R17, corrected by R18 review

**Executable synthetic research contract; NOT a production valuation service, native
financial binding, calibrated forecast, recommendation or completed programme.**

## Revision and evidence

The original R17 record is preserved at commit
`a1899a0a4e210d52884bf6958a40119667949f5d`, blob
`5ea5e6a2116908058408a584f2fd14d70046a969`. That record's 61 tests and eight mutations
were local reference results, not independent acceptance. GitHub Codex review
`5331568561` completed on that exact head and returned five findings. The current
revision preserves the architecture and options-first decisions while repairing the
reference's financing scope, quote basis and export semantics. Read the companion
`CATALYST_INTELLIGENCE_R18_CONSUMER_AND_REVIEW.md` for the current full disposition.

Procedure for this repair: Mastermind `3c35c5f8c4609c5bbaa4db424521facb6ad3757d`,
compatible Skillpack1.0.1/bootstrap1. The Chairman-assigned Catalyst Meta-CEO retains
programme responsibility. This is the existing #8061 carrier, not a source takeover of
FIF, Market OS F07, #6712 or a specialist implementation.

## Placement stays with the existing owner

Reported financial facts remain FIF. Event-to-AssumptionChange-to-valuation belongs to
Market OS F07/MAS-148, whose original handoff is
`agentos/handoffs/MARKET-ONTOLOGY-F07-VALUATION-SCENARIO-FABLE-COO-2026-08-26.md`.
The fixed `engine/valuation_scenario.py:compute` and `valuation_scenario.v1` are unchanged.
Do not inject gross-margin forecasts into their reported-net-margin fields.

`research/catalyst_intelligence_reference/f07_conditional_equity/` is an executable
specification for review. It is NOT another production kernel, API, model registry,
financial store or ranker. Its structural labels cannot establish identity, rights,
source admission, calibration or execution. All outputs retain `can_rank=false`,
`production_admission=false` and no recommendation.

## Financial methods and reviewed applicability

Both methods retain joint scenario inputs. Revenue times gross margin gives gross
profit; operating costs, interest, tax and other income claims then give common
shareholder earnings. Missing costs do not become zero. Quarterly results cannot be
silently annualized: the declared earnings period is the twelve months following the
valuation horizon.

**Common-earnings multiple:** common earnings times the stated multiple directly
values equity under this narrow convention. It must not receive a duplicate debt/cash
bridge. Independent review found that the R17 specimen nevertheless diluted shares
without valuing fresh issue proceeds. The repaired family now rejects new common-share
issuance (`pe_financing_out_of_scope`). It does not pretend to model proceeds deployment
or excess cash. An appropriately qualified richer model may do so later; no blanket
claim that all P/E valuations must ignore cash is made.

**Operating-enterprise:** operating EV plus same-horizon cash less debt and senior
claims gives the common-equity residual. The explicit limited-liability floor and
pre-floor residual remain visible. New-share proceeds, fees, cash, debt and terminal
common shares move together. Changing a ten-share issue price from10 to100 adds900 to
cash and equity in the fixed-EV synthetic example. This is arithmetic, not a real equity
value or a probability model.

Company distributions and cash received by an entry shareholder remain separate.
Endpoint cash is not proof of interim funding survival. Conditional draw paths,
buybacks, conversions, legal recoveries, share exchanges and full sector-specific
valuation applicability remain outside this reference. P/E is not imposed on
pre-revenue or distressed companies.

## Quote and share-basis binding

The repaired contract requires `known_at <= quote.observed_at <= as_of`, alongside
quote validity. A later caller-supplied valid-until time cannot make a pre-information
quote a valid entry. These are structural timestamp checks, not executable-fill proof.

The quote now names the same subject and share-basis reference as the valuation.
Only one-common-share quote units are supported. Different subjects/classes/bases,
ADR conversion ratios and rescaled units are refused rather than compared directly
with equity divided by common shares. These remain synthetic labels; production
requires actual owner-native identity, rights and corporate-action evidence.

## Reproducible outputs

Every result includes a JSON-safe `input_envelope` and SHA256 of its canonical JSON.
The envelope retains source/model labels, clocks, quote, opening balances, costs and
all scenario assumptions. Replaying that envelope reproduces the result without
pretending that synthetic labels can be dereferenced. Decimal/integer numeric inputs
serialize consistently. The original inputs remain unchanged. A digest proves byte
identity of this envelope, not truth or source authority.

Complete illustrative probabilities may be weighted. Missing probabilities preserve
conditional values without expected return; partial weights are not renormalized.
No output becomes calibrated or ranking-eligible from caller flags.

## Options-led discovery remains a substantive input

Semiconductor R6 at `10c36bc3bf09c4df20085e0bc55fe3d77d1aa4c6`, blob
`3919ed1246a0ba573773ec2d39829685efcb96f4`, supplied the options-first proposal.
Options-led, fundamental-led and joint origins belong to the same security-level case;
a named fundamental catalyst is not a prerequisite for research discovery. Compare
price/context, options/context, fundamentals/context and combined models on appropriate
frozen populations. Unknown dealer identity limits actor claims, not all observable
predictors. Shared prints do not supply independent confirmations.

Two eventual investment routes remain distinct: qualified causal/economic scenarios
through F07, or an independently evaluated empirical equity-return distribution through
existing Alpha/evaluation/recommendation owners. Direction alone does not establish
payoff, loss tails, costs, coverage or calibration. An empirical model need not fabricate
FDA/award odds or a fundamental price target. No new ranker or source collector follows.
The specialist's literature/archive/tests were not independently replicated by R17/R18.

## Reproduction and precise artifact locations

The repository contains the calculation module, original suite, dedicated
`test_f07_review_regressions.py` and mutation runner. The suites construct their inputs
through `packet()`; no private fixture file is required. From that directory:

```sh
python -m pytest -q
python check_mutations.py --report /permitted/output/f07_mutations.json
```

Current local and fresh-copy results: **77 passed; 14 syntax-valid harmful mutations
rejected by assertion failures with zero execution errors**. Five initial independent-
review regression tests failed against the unchanged R17 module before repair.

The conversation attachments, not the R17 repository tree, contain `fixtures.json`,
worked-output JSON and raw local verification reports. R17's wording that "the package
includes" these meant `CATALYST_INTELLIGENCE_R17_F07_PACKET.zip`; it did not identify
repository files. The R18 attachment supplies current fixtures/outputs and failure/final
reports. Do not describe attachment-only evidence as committed source, or reuse R17's
numerical examples as current results after the model-family restriction changed.

## Acceptance still owed

The code changes address the observed review cases; they are not a second independent
approval. Current-head review, adopted native F07/FIF/identity/rights interfaces, an
admitted modifying carrier, actual issuer/scenario data, authenticated consumer/export,
and common-basis two-sector proof remain required. Prospective investment evaluation
remains distinct from plumbing and local arithmetic. Existing Paper/source/permission
holds and all production/model/rank/portfolio/trading boundaries remain unchanged.
