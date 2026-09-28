# GD-6A US market-eligibility: zero-policy shadow intake

**PARTIAL / BUILT_NOT_PROVEN. PR #8141 is DRAFT / HOLD-FOR-SOL.**

Operation `gd6a-us-shadow-intake-20260928-sol-001`, existing
`WS:GREY-DEER-RISK-INTELLIGENCE` / GD-6A. Parent #6817 research intake
`PROPHET_RISK_RESEARCH_R1_20260927_SOL`, adjudication 5865326642.
Carrier `claude/gd6a-us-shadow-intake-20260928` began at
`03e8961d22b48cc65666f6318ee8c8bd610f3caa`. No incumbent source, H1/Cycle study,
Seat B repair or original CEO UI release is transferred.

## Canonical owner and unchanged authority

The existing `DEC:PROPHET-RANK-PRESERVED-MARKET-ELIGIBILITY-SIDECAR`, Grey Deer
architecture freeze and execution command packet already define
`prophet.market_eligibility/v1`: server-side after rank, exact board/session
binding, lossless dispositions, shadow birth. This is that owner, not a new
risk engine, policy registry, identity, allocator, store or publisher.

Current `engine/risk_envelope.py` produces zero policies and episodes with no
envelope action authority. The new intake supports EXACTLY that native v0 state.
Nonempty/null/malformed/unsupported policies are UNAVAILABLE, not permission to
evaluate a caller-supplied rule. Individually authorized policy support remains
a separately reviewed native producer/consumer extension. No score-to-policy
mapping, R2 research threshold, automatic exit or liquidation is installed.

## What works

`engine/prophet_market_eligibility.py` composes one deterministic SHADOW disposition
for every `/buy` row of the bound raw US board. It preserves order and nullable
native rank/lane. Array pointers are not security/issuer/episode/plan identities.
`bind_shadow_view` returns complete deep-copied raw rows with sidecar information;
it does not replace the off-board candidate-pool owner or claim whole-universe proof.

Binding checks cover exact raw board digest, definition and session, native envelope
semantic bundle plus complete raw digest, market/revision, zero-policy semantics,
strict booleans, coverage, individual source clocks and observation/emission order.
The native semantic bundle excludes outer clocks. The settled producer uses
`stale_after=None`, so callers supply an explicit owner-qualified validity window.
The sidecar never invents a market calendar or treats a hash as authorization.

Bad board identity/shape refuses: there is no trustworthy partial denominator.
Missing or unqualified risk evidence preserves every intact board row with
UNAVAILABLE, never Calm or a healthy empty market. The narrow v0 intake requires
FRESH envelope coverage, including optional coverage; a PARTIAL shadow does not
alter live candidate/rank/entry behavior. This is not a future active-policy rule.

AVAILABLE / ELIGIBLE means only NO_MARKET_POLICY_CONSTRAINT_NOT_BUY_PERMISSION.
All eight downstream authority booleans are false; production_behavior is UNCHANGED.
The consumer recomposes every semantic field against independently supplied source
bindings; rehashing changed permissions, rows or expiry does not pass. The interval
is half-open. Corrected observations remain distinct and do not backdate orders.

The real `scripts/build_prophet_market_eligibility.py` entry point is stdout-only,
requires explicit paths/hashes/session/window, and creates no scheduled publication.
Exit 0 is available shadow, 2 unavailable shadow, 1 refusal. An unreadable input
is not silently treated as an observed empty source.

## Actual verification: original unit boundary plus native producer chain

Python 3.13.5 commands:

```sh
PYTHONDONTWRITEBYTECODE=1 python tests/test_prophet_market_eligibility.py
PYTHONDONTWRITEBYTECODE=1 python tests/test_prophet_market_eligibility_native.py
```

**51 unit/consumer/CLI tests PASS plus 12 distinct native-composer compatibility
tests PASS: 63 total, zero failures/errors/skips.** All market observations are
synthetic. The second suite imports the entire existing native composer, not a
transcribed helper or mocked dependency. Its local source copy was verified BEFORE
execution and remains identical to GitHub:

- native Git blob: `3b0df2d426f50245142b943e38faf4996f96e995`
- source: 30,642 bytes / 678 lines at the branch base above
- native SHA256: `f0d9b1786b524f8092cfcaa194e8d590f1ff4b3db97ca8d2b0b2af5595331099`
- new native test blob: `ad1752e12e9701a54bcd989dfe657de491cb35da`
- native test SHA256: `7cde80b018705a52fa2ec83e8864b7baa507d1a97e1437d1576dc770e4cdb43c`
- actual native test log SHA256: `6c619628560398ea04b7b23f58bee50e50eef6ef381391d7153e647c784c58ce`

Native cases cover fresh zero-policy composition, contradiction without fabricated
policy, required gaps/staleness, optional partial coverage, unknown required clock,
off-session input, provisional revision, source-order invariance, rebake clock
changes, corrections and explicit expiry. The native unknown-clock case proves
why all_on_session alone is insufficient: it can be true with a required as_of null,
while the sidecar correctly withholds a qualified shadow reading.

The original 51-test suite also killed four in-memory faulty variants by assertions:
substituted board hash, live gate permission, dropped rows and ignored consumer expiry.
The dropped-row variant additionally produced three downstream errors, separately
reported, not claimed as kill proof. The initial mutation summary wrongly demanded
zero errors; its diagnostic report was corrected without mutating source or results.

No full-checkout, native Agent OS validator, hosted CI, authenticated API/browser/send,
ordinary publication, real board input, counterfactual accrual or predictive result is
claimed. The large board-file adapter returned no content; that does not mean the
real board is empty. The 12 native tests close the earlier function-chain gap only.

## Exact next source operation: existing CI owner registration

Add BOTH new suites to the existing `.github/ci/legacy-jobs.yml` step
`synapse read-gate unit tests` which already owns the native envelope suites:

```text
python -m pytest tests/test_synapse_read_gate.py tests/test_horizon_firewall.py tests/test_delivery_waterfall.py tests/test_pricing_power_monitor.py tests/test_risk_envelope.py tests/test_live_risk_envelope.py tests/test_prophet_market_eligibility.py tests/test_prophet_market_eligibility_native.py -q
```

Apply the minimal append to the ACTUAL existing command; do not replace or drop any
existing suite. Registration is identified but NOT APPLIED in this candidate.
The manifest is 1,033,991 bytes, blob `272a7fe415b82811f34946bbd50816ee7aee8069`
at branch base. Native GitHub update_file requires the whole text and current blob;
this turn did not materialize the full exact manifest for a safe replacement.
No new CI workflow, indirect test-discovery trick or truncated replacement is allowed.

Obtain native Agent OS validation, affected suite execution, current-base checks and
independent exact-head review. Keep DRAFT with no merge-on-green or auto-merge until
Sol's named release conditions are met. A triggered CI run is not proof these new
tests were selected or passed. The old-head main authority check passed, not full CI.

## Next capability after this source slice

Bind `scripts/build_prophet.py::_freeze_origination_source_board` and the normal
settled envelope into existing after-rank publication. Prove unchanged raw board,
rank, plans and population; exact source receipts, lossless shadow counts and next
ordinary refresh. Use existing QLedger/Chronicle counterfactual accrual, not a new
ledger. Full GD-6A and live policy acceptance remain outstanding.

An active policy extension must bind individually registered IDs/versions, native
scope/vulnerability predicates, authority, time/expiry, repair and kill state.
Intersect constraints; never average into a new score. Unknown vulnerability is not
low risk. One repair cannot lift another policy. Original Grey Deer promotion gates
remain; R2 research budgets did not replace them. Personal holdings and automatic
exit remain outside this slice.

Protected procedure: Mastermind `5c6b010a6157895d4f697548c75263cdff641ea6`, compatible
Skillpack1.0.1/bootstrap1. No retry/proxy of the denied host compound inspection.
Native GitHub is the sole source-modification carrier. MISSION_COMPLETE:false.
