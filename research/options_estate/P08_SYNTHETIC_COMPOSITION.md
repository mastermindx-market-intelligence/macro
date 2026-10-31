# P08 synthetic composition — engineering only

Scope: [Options disposition6546107958](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1183#issuecomment-6546107958).
This adapter exercises the existing Q02 solver in explicitly constructed fixtures.
It does not adopt Q02 for production, reopen E2, amend its preregistration, or
produce an empirical result. Q02 remains `RESEARCH_ONLY / INSUFFICIENT_DATA`.
This source is Draft-only; it does not complete Release B.

## Boundary

`p08_synthetic_composition.compose_synthetic` takes exact frozen `SyntheticCase`
and `SyntheticPut` instances with tuple axes. It rejects dictionaries (even with
`synthetic=True` and qualified-source metadata), subclasses and undeclared fields.
These types prevent accidental source-payload adoption; they are **not proof that
numbers originated synthetically**. There is no production caller, provider/file
loader, parser, CLI, endpoint, runtime registration or source-admission grant.
Do not wrap real contracts in these classes and describe the result as admitted.

The initial domain is an American put on an explicitly declared share multiplier,
nonnegative rate, q=0, no discrete dividends and explicit conditional volatility.
Remaining years and scenario elapsed years are continuous: no calendar inference,
rounding or expiry floor. Every requested horizon must precede every member's
economic expiry, including zero OI. Validation of the entire case precedes solving.
At most four members and four values per axis are accepted, with an additional
16-qualification upper bound including the baseline. Duplicate axes are refused.

## Numerical contract

The adapter calls the unchanged `qualify_fd` with its frozen `(100,200,400)` grids,
tolerances, volatility bump and boundary rules. No tuning controls are exposed.
Every returned per-member `Qualification` retains status, levels, errors, intervals
and reasons. INTERVAL and UNAVAILABLE never become midpoint estimates. Exceptions
abort composition rather than returning a partial result.

For explicitly assumed signed contracts `q = position_sign × open_interest`,
the sums use the incumbent scenario surface's full-dollar conventions:

- gamma: `sum(q × multiplier × gamma × S² × .01)`;
- Vanna: `sum(q × multiplier × vanna × S × .01)`;
- Charm: `sum(q × multiplier × charm × S / 365)`.

Each quantity is withheld unless all its nonzero members have finite CONVERGED
values. Other quantities may remain usable. Counts retain every fixture member;
zero OI contributes exact zero without a Greek solve or a claim of convergence.
No million-dollar scaling or call/put sign inference is applied. This deliberately
does not inherit the legacy surface's skip-nonfinite mask. Small pure sums are
contained here; no production aggregation extraction or solver import is needed.

Fixed-inventory hedge targets are `B0=-sum(q M delta0)` and
`B1=-sum(q M delta1)`, in shares. `Q=B1-B0`; reference notional is `S0×Q`.
Both endpoints must qualify. Revaluation of dollar delta is not a hedge trade.
Positive Q describes a conditional increase in the hedge target, not an order,
observed dealer trade, flow estimate or price forecast.

## Focused evidence

Run `python -m pytest tests/test_p08_synthetic_composition.py -q`.
The suite distinguishes controlled solver-result composition tests from two real
fixed-grid calls: an American put with the incumbent independent 2000-step CRR
price control, and a volatility-boundary case retaining unavailable Vanna.
The existing Q02 0.02-dollar CRR tolerance is reused without a search. Other tests
cover signed cancellation, zero OI, mixed quantity status, incomplete and nonfinite
inputs, continuous time, expiry, work bounds, no production caller and import scope.
No full E1 campaign, real-source test, empirical scoring or forecast trial runs.

Source comparison must leave `options_american_exercise.py`,
`options_scenario_admission.py`, `options_scenario_surface.py`, all producers,
publishers and runtime callers unchanged. Review this composition's numerical and
adoption boundary independently once; review is not model adoption. Qualified real
source, American-model adoption, publication, deployment and full A/B/C acceptance
remain separate obligations.
