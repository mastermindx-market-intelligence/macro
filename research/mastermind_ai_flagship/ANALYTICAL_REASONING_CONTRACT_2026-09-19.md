# Mastermind AI — Analytical Reasoning Contract

Date: 2026-09-19. Owner: Sol / `macro-mastermind-ai`.
Procedure pin: Mastermind protected
`733389933e605e508517732fb6c69b6c18b7fef6`, Skillpack1.0.1/bootstrap1.

Status: architecture/acceptance law. No production prompt or model behavior is changed by this file.

## 1. Problem

Mastermind already contains a strong always-on Analyst Protocol:

> Hold two explanations until the evidence splits them.

But the higher-priority Brain prompt simultaneously says:
- “no hedging”;
- “ALWAYS end with a STANCE”;
- “give a real, direct call”;
- tell the user what the data mean “and what to do about it.”

Fast answer-shape also requires a stance for any read.

Those instructions are not equivalent. On an ambiguous causal question they can pressure the model to
collapse uncertainty into a single story even when evidence has not distinguished it.

## 2. Production discriminator

Two new real Fast SSE runs on the same production generation make the distinction visible.

### Coached analytical NVDA question

Run `eeaae8751b774e6d9dbef5555b123699` explicitly asked for two competing explanations,
support/contradiction and discriminating missing evidence.

The model:
- verified there was no strong NVDA-specific in-session catalyst;
- formed an AI/mega-cap explanation and a crypto/risk-on explanation;
- named evidence for and against each;
- explicitly said intraday path/sector-relative evidence was missing and it could not split them
  definitively.

This is the desired research behavior. It took 66.127s across two model rounds.

### Natural “Why did NVDA move?” control

Run `5c95dd4c61894b808c465dca2d5017bc` asked only the natural customer question.

The model independently called `get_market_events` and `get_quote`, reached pass2 in 8.4s and
completed in 26.161s. It was coherent and useful, but asserted:

> “The real forces were the desk's two live legs: hawkish Fed repricing ... and a risk-appetite bid...”

despite also saying the wire had no company-specific catalyst. It presented one causal synthesis rather
than the protocol's explicit competing-hypothesis test and ended with a required trade-style stance.

The natural answer is not “lobotomized”; it is analytically compressed in the wrong direction. The
higher prompt rewards decisiveness more strongly than epistemic separation.

## 3. Core law: directness is not certainty

Replace the false tradeoff:

> decisive answer OR honest uncertainty

with:

> direct statement of what is observed, what is inferred, and what would resolve the inference.

“No hedging” means no empty verbal padding. It must **not** prohibit:
- saying evidence is insufficient;
- preserving two plausible mechanisms;
- naming a contradiction;
- distinguishing correlation from causation;
- refusing to call a source/timing relationship that has not been established.

An unresolved evidence state is a useful conclusion.

## 4. Typed reasoning chain

A material investment thesis should expose this logical chain in ordinary language:

1. **Observation** — dated/source-bounded fact or supplied assumption.
2. **Expectation comparison** — only when a dated expectation/guide is actually available.
3. **Candidate mechanism** — a hypothesis about why the observation matters.
4. **Financial consequence** — deterministic calculation when possible.
5. **Valuation/horizon implication** — what assumptions in price or timing are affected.
6. **Rival mechanism** — the strongest plausible alternative, not a token bear case.
7. **Discriminator** — the next observation that would separate the mechanisms.
8. **Decision relevance** — conditional consequence for the user's thesis/exposure.
9. **Action authority** — separate calibrated signal/house/user decision layer; never inferred from
   the existence of the reasoning chain.

Missing links remain missing.

## 5. Causal language contract

Use causal wording only at the strength supported:

- **Observed together:** “moved with”, “coincided with”, “was consistent with”.
- **Mechanism-supported:** “likely transmitted through X if Y holds”.
- **Event/timing-supported:** “the move followed X and matched the predicted cross-asset pattern”.
- **Calibrated/validated cause:** only where an accepted deterministic/research owner explicitly
  provides that authority.

Do not upgrade “the tape is consistent with AI leadership” into “AI leadership caused NVDA to rise”
merely because a stance line is required.

A post-close item cannot cause a regular-session move. A broad sector bid does not prove the exact
single-name driver. Several syndicated articles are one evidence family.

## 6. Task-conditioned conclusion, not mandatory universal stance

The final answer shape should follow the task:

### Fact / explanation / causal research
End with:
- **Read:** what the evidence currently supports;
- **Unresolved:** the material competing explanation/gap if one remains;
- **Watch:** the discriminating observation.

No trade stance is required merely because the user asked “why”.

### Thesis analysis
End with:
- thesis premise strengthened / weakened / unchanged / unresolved;
- the link responsible;
- the evidence that would reverse the assessment.

This is research state, not a new calibrated signal.

### Explicit action question
If the user asks buy/sell/add/trim/hold:
- first complete the analysis;
- then use existing calibrated/authorized decision context;
- clearly distinguish house signal, user-supplied assumption and model hypothesis;
- if exact-name calibrated action evidence is absent, do not fabricate a direct trade call to satisfy
  writing style.

### Existing house/signal explanation
Relay the accepted signal and its horizon/limitations. Do not re-rank or originate another signal.

## 7. Default hypothesis discipline

For an ambiguous “why did X move?” question, competing hypotheses are **default**, not something the
user must explicitly request.

The answer need not always display a bulky two-column debate. Internally, the model must:
- hold at least two candidates until discriminating evidence is checked;
- name a material contradiction when present;
- fetch the evidence that separates them;
- collapse to one only when the evidence earns that collapse.

If the final prose gives one driver, evaluation should be able to identify the evidence that eliminated
the rival.

## 8. Deterministic intelligence first

When a relation can be calculated, do not ask the model to eyeball it:
- financial bridge;
- valuation sensitivity/reverse assumption;
- return and normalization;
- date/cutoff comparison;
- source identity/correction;
- historical outcome measurement.

The LLM's job is to choose the relevant calculation, interpret it, test rivals and explain implications.

## 9. Evidence acquisition

Current internal tools are necessary but not sufficient. A current claim with a material source gap
uses the R1 public research contract:
structured minimal-public evidence request → observed search → source opening → relevant evidence →
analysis.

Search snippets/provider prose are discovery, not facts.

The model should not be punished for saying “I cannot distinguish this yet” when the required source is
unavailable. That is a successful fail-closed investigation.

## 10. Evaluation

Add paired tests where only the instruction shape changes:

- natural customer phrasing;
- explicitly adversarial/research phrasing.

The natural version must still preserve the analytical law. We should not need to tell the flagship
product “give two explanations” every time.

Score separately:
- factual/source correctness;
- calculation correctness;
- mechanism support;
- contradiction handling;
- missing-evidence honesty;
- valuation/horizon linkage;
- unsupported causal claims;
- invented signals/actions;
- useful next discriminator.

Do **not** score answer length, number of sources, number of agents or confidence tone as intelligence.

## 11. Prompt repair sequence

Do not add another long directive. The existing protocol already says the right thing.

When shared gateway custody is available:
1. elevate “observed vs inferred / two candidates / unresolved is valid” into the short top-level
   honesty law;
2. restrict “no hedging” to verbal padding, not uncertainty;
3. make universal STANCE task-conditioned;
4. narrow “what to do about it” / direct trade calls to explicit action questions with authorized
   decision context;
5. keep the detailed Analyst Protocol as procedure, not duplicate prose;
6. run the natural-vs-coached frozen canaries before release.

This is a prompt/authority simplification, not a larger prompt.

## 12. Completion evidence

A successful repair must show, on the real SSE customer path:
- natural current-move questions test alternatives without being coached;
- self-contained financial questions perform calculations and preserve assumptions;
- unanswered evidence gaps are stated rather than papered over;
- explicit action questions still get useful decision context when authorized;
- existing signal authority and Research-mode restrictions remain unchanged;
- latency does not materially regress.

The end-state is not a timid AI. It is an AI that is **precise about uncertainty and decisive about
what the evidence actually proves**.
