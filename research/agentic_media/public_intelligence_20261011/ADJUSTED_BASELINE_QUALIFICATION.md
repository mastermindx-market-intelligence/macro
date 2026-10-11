# Fixed NVIDIA analytical qualification

Operation: `mmx-public-intelligence-delivery-20261011-local-ceo-001`.

The new `press-source-qualification` workflow is manual and main-only. It reuses
`engine.close_pass.massive_close._default_fetch` and the existing Massive/Polygon
credential aliases for one fixed logical request: split-adjusted NVDA daily bars
from 2024-10-14 through 2026-10-07. It has read-only GitHub permissions and artifact
output; no collector, model, staging, publisher or deployment effect is available.
It must land through protected review before its first dispatch. No dispatch or
live authenticated fetch has occurred in this implementation phase.

The frozen question is the trend and volatility backdrop before the October 8
science commitment announcement. The five predefined calculations reuse
`engine.stock_technicals.snapshot`: distance from 50/200-day averages, RSI14,
20-day realized volatility and its trailing percentile. The two average-distance
calculations are independently checked with arithmetic means. This is a
current-vintage historical reconstruction, not proof of data availability before
the announcement. Provider-asserted split adjustment is not total return or an
authenticated regular-session close. External observations remain external;
calculations confer neither trading authority nor automatic Press admission.

The qualifier requires exact ticker, adjustment and chronological NYSE session
coverage, coherent finite OHLCV, no pagination, and typed allowlisted response
fields. Source, workflow, transport, calendar and the already-reviewed entitlement
record are bound to committed bytes before any request. It retains canonical
parsed JSON, not raw HTTP bytes or headers; the receipt SHA256 names the exact
saved bytes. Unknown fields and credential echoes are refused before retention.

One exclusive mode-0700 output directory is created outside all Git checkouts.
Evidence files use mode0600, exclusive creation and fsync. An existing attempt is
never overwritten or silently replayed. The inherited transport allows at most
three HTTP attempts on transport/5xx failures, never retries 4xx, and this caller
opts out of redirects. All3xx responses are terminal before body parsing. There is
no wrapper retry, post-failure key/host switch or pagination follow-up. The new
optional redirect argument preserves legacy callers' existing behavior.

## Verification

- Initial focused suite:31passed in7.16s.
- Qualifier plus existing transport regressions:83passed in20.05s.
- Wider run exposed one real CI contract mismatch:1failed/111passed in26.75s;
  the old workflow test required a dependency-identical Press/estate lane even
  though the analytical engine now needs numpy/pandas and transport tests need
  requests. The single-install Press lane and its contract were updated together.
- Final focused qualifier, including redirect destinations, byte identity,
  missing credentials, symlinks, traversal and foreign checkout:43passed in2.92s.
- Repaired existing workflow contract:28passed in7.63s.
- Trigger closure:zero gaps. Legacy manifest:279jobs validated.
- Bounded independent source review accepted the final containment repair at
  qualifier SHA256 `db32f50eda2bd4b6a78ecf4e957ad1cdbf67d056e09d684983d0f8a363917203`.

Commands: `python3 -m pytest tests/test_press_adjusted_baseline.py
 tests/test_close_pass_massive_close.py tests/test_press_workflow.py -q --tb=short`
(with the affected suites rerun after each actual repair),
`python3 scripts/check_ci_trigger_closure.py`, and
`python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --validate-only`.

These are local source/test results. A successful future artifact still requires
editorial relevance review and explicit fact-pool admission. Five computed metrics
do not automatically meet D14's first-party-value requirement. The article remains
15/17, unstaged and unpublished. The original interrupted Press provider attempt
remains EFFECT_UNKNOWN and is not retried by this workflow.
