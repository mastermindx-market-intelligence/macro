# SCE V8 — conditional drawdown feasibility, not strategy acceptance

Status: PARTIAL research continuation. Records only; no trading, production, worker,
collector, source-host or portfolio authority.

Procedure pin: Mastermind `dd553d1b0b8eed9511da2d3d5ec02cc9cd8edca1`, compatible
Sol Skillpack 1.0.1. Same records carrier and PR #7009. Earlier V4–V7 research
and source qualifications remain in force.

## The question tested

Earlier research found that a fixed inventory/cash/selected-option family could
explain a short displayed portfolio segment under a cost-held overlay convention.
That did not establish whether all such explanations necessarily contradict the
published portfolio drawdown when their open positions are marked.

V8 tests the entire declared feasible quantity family rather than one selected
position size. The image constraints, the economic valuation sequence and the
hypothetical strategy rules remain separate objects. This is inverse-accounting
consistency, not a signal, allocation optimizer, backtest or repeat of a previously
blocked portfolio sweep.

## Construction and observed result

For one nonnegative, funded quantity vector x, Cx is the hypothetical display and
Mx is its marked-value sequence. The same x must satisfy every original image band
and every funding inequality. For a proposed drawdown cap d, every ordered pair of
known valuation dates is constrained by `(1-d) M[s]x <= M[t]x`. Bisection over
linear feasibility yields a numerical minimum-drawdown bracket. A separate
linear-fractional formulation supplies the upper envelope at the known dates.

The image has 16 retained constraints in the investigated segment. The economic
calendar has 20 expected dates, of which 19 have the retained component observations.
Three dates without usable image levels still contribute to the marked-value test.
The missing GLD fixed-time observation is not filled, dropped from the expected
calendar, inferred from an EOD record, or declared irrelevant to total risk.

The resulting lower bounds and explicit feasible examples do not rule out the live
book's displayed drawdown number under this restricted accounting family. A separate
finite enumeration found multiple funded integer-quantity examples that also fit
the original image bands and have smaller drawdown across the known observations.
This favorable result must be preserved: a large option-level drawdown is not by
itself evidence of an equally large portfolio drawdown or false published metrics.

Neither the feasibility finding nor the quantity count identifies the creator's
positions, validates a whole-period NAV, proves fills or establishes an edge. The
cost-held view remains a display hypothesis, not an economic NAV convention. The
range is an identified-set calculation under explicit assumptions, not a statistical
confidence interval or a probability over strategies. Raw licensed observations and
private numerical evidence remain in the Chairman's research package.

## Verification and limitations

A direct Decimal cashflow rebuild checks the retained design coefficients without
importing their original matrix builder. Independent integer enumeration checks
funding and image bands without relying on the continuous optimizer. Synthetic and
retained-input tests cover shared quantities, all ordered date pairs, positivity,
nulls, funding, tolerances, distinct calendars and missing-mark conditions. Forty-five
local V8 tests passed at the recorded checkpoint. They are not this PR's source CI.

The market inputs remain retained current-vintage observations. Daily SPY/BIL values
and fixed-time options retain the V7 mixed-clock qualification. The selected contracts,
multiplier, execution assumptions and constant core inventory are not recovered private
rules. Quote size does not demonstrate deeper fill capacity, and no borrowing,
assignment, exercise or external flow is added silently. The short segment cannot
establish the maximum over the complete live history or the different Efficiency book.

## Actual source-release defect and correction

The former head's CI run 34425846264 completed with one hard record error: the SCE
discovery's falsifier was prose without a runnable/openable token. This was our authored
record defect, not an inherited runner failure. The same-carrier repair supplies the
actual read-only resolver/manifest census as a literal command and explains the dated
comparison. No validator, other workstream, warning threshold or runtime gate was
weakened. Source-read syntax checking is not a new successful source-host read.

## Exact continuation

Do not reject or promote the strategy from the short accounting segment. Recover a
version-matched, independently specified core and overlay transition and evaluate it
through one funded, appropriately timed replay. A complete source-qualified profile
pair and a second independent numerical core threshold remain the next identification
inputs. Preserve unmatched events, original availability and the missing observation.
The existing source owner separately reconciles intended host, volume identity, data
parity and producer health; this research creates no recovery commission or new store.

Full SCE mechanism identification, whole-history economic validation, forward evidence
and useful production delivery remain unfinished. Source CI and merge remain separate
release obligations; this memo does not authorize bypassing a pending or failed check.
