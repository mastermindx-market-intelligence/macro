# Prophet earnings evidence brief and profitability mechanism

**BUILT_NOT_PROVEN / MISSION_COMPLETE:false. Same source carrier #8189.**

Parent source `c2d99e3ad69250fcfe0229659506152fc7f04900`, existing branch
`sol/prophet-earnings-semantics-v1-20260929`. Current Chairman continued the
turnaround. Source work remains on Studio Direct/native Git under the existing
primary assignment. Direct execution reason: PRINCIPAL_JUDGMENT and
CRITICAL_PATH_SHORTCUT; no new receiver, provider, job, queue or memory owner.
Current user-selected Pro does not itself confer permission or verify served model.

## Phase 1 — from computed numbers to an evidence explanation

The new `earnings_evidence_brief` consumes the existing `factual_dossier`, keeping
supporting facts, neutral context, counterevidence and unestablished inputs separate. It is called
by `project_earnings_detail`, so the already-authenticated
`/api/prophet/lab/v1/episodes/{episode_id}/earnings` response now includes the
explanation. This is not another endpoint or a second source read. The actual
HTTP-chain test proves the explanation arrives with the original B1 episode,
D5 projection and source-bound Q06 comparison. Authentication, entitlement,
private-cache headers and kill switch remain unchanged.

The brief distinguishes:

* operating improvement from a qualified analyst-consensus surprise;
* an EPS beat from a conflicting revenue miss;
* same-contributor forecast changes from roster-composition changes;
* a newly raised issuer range from a mixed change with a weaker lower bound;
* delivery against the latest issuer outlook from earlier guidance already known;
* source-qualified accounting facts from explicitly supplied per-share or price
  scenarios, which must NOT be presented as verified issuer/live-price facts;
* these earnings facts from currently unassessed market/portfolio/entry permission.

The existing dossier can now hold update-time issuer-guidance changes without an
actual future result. Issuer, clock and no-future-result checks bind those inputs.
Higher values for unsupported measures such as expenses are kept as neutral
context; they are not called a favorable beat. Unchanged forecasts do not become
upgrades. The source surprise and brief share the same declared interpretation
set. No fact count, favorable label or agreement creates a score, calibrated
probability, current entry recommendation or higher financial authority. All
output authority remains false. Source children with authority values other than
false cannot be used to smuggle a recommendation into the brief.

Legacy C1 extraction, score/rank weights, old grades, H1/Cycle outcomes and
original episode records are not rewritten. The original-source-vintage detail
remains a retrospective factual reconstruction, not an original recommendation.

## Phase 2 — distinguish profit growth from improving profitability

The existing earnings engine now implements `profitability_bridge` using four
source-qualified Actual values: current/prior revenue and current/prior declared
profit. Gross profit, operating income and net income remain separate measures.
The function refuses mixed issuer, event, accounting basis, units/currency,
quarter/YTD period, future availability, overlapping periods and nonpositive
revenue denominators. Comparative prior numbers may come from the same current
release; no fictional earlier ingestion clock is assigned.

For profit P = revenue R times margin m, the symmetric identity is:

```
change(P) = change(R) * average(m) + change(m) * average(R)
```

It reconciles exactly up to explicit floating-point tolerance and is invariant
to a common monetary-unit rescaling. It is an arithmetic decomposition, NOT a
causal estimate of pricing, volumes, product mix or management skill. It supplies
no asset denominator, expected stock return or financial-policy authority.

Synthetic counterexample: revenue1000→1200 and operating income100→108 gives
revenue growth20% and profit increase8, but margin10%→9%. The symmetric revenue
component is+19 and margin component−11. The brief surfaces margin compression
instead of treating the two positive headline growth figures as two bullish votes.

The new output is admitted by the existing factual dossier and explanation.
It does not add missing profit fields to the upstream D5 vector or claim that
all issuers' comparative operating statements are already captured. Until the
native source owner supplies those fields, the existing HTTP detail shows its
actually available evidence and missing profitability comparison, not a synthetic
or cross-company substitute.

## Public-source research check

`PROFITABILITY_CASE_2026-09-30.json` binds a historical numeric example to Micron's
September23,2025 SEC-filed release:
https://www.sec.gov/Archives/edgar/data/723125/000072312525000024/a2025q4ex991-pressrelease.htm

Its **GAAP quarterly** statement (not non-GAAP or annual columns) reports revenue
7750→11315 and operating income1522→3654, USD millions. Revenue growth is46.0%;
operating margin is19.6387%→32.2934%, an expansion1265.4706basis points. The profit
increase2132 decomposes into925.6901 from the symmetric revenue term and1206.3099
from the margin term. Exact rational arithmetic independently reconciles2132.
This is a historical issuer calculation, not a point-in-time Prophet trade,
source-capture claim, return study or new recommendation. Historical system
availability remains unknown in the research record.

Research reference: Robert Novy-Marx, NBER15940 / JFE2013,
https://www.nber.org/papers/w15940 . Its profitability variable is gross profits
to assets, NOT operating-margin growth. It motivates treating profitability and
valuation as separate investment dimensions; it does not validate this bridge,
these explanatory labels or a margin-change trading strategy. Any B15 promotion
still needs comparable native inputs, original trial-history accounting and the
accepted price/sector baseline on the same eligible population. No protected
outcome or new empirical trial was accessed by this wave.

## Two actual CI findings repaired

Prior exact-head run36797550288 failed for six missing declared rights-file paths
and one API restart-coverage regression. Six existing jobs now explicitly include
`research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md`; parsed YAML
comparison proves every other job/path/command remains unchanged. The six are
biocatalyst-history, biocatalyst-serving, defense-rail-laws, flow-surface,
unrun-government-revenue-candidate-projection and unrun-government-revenue-grader.

The existing `app/deploy/update.sh` macro-api restart trigger adds only
`engine/sue.py`, now import-cached by the earnings endpoint. No deployment,
service restart, unit edit, privilege change or live systemctl command was run.
This is a concrete new-candidate regression repair, not a replay of the previously
refused general frontend/CI-owner or release-binding inspection. Those older
action restrictions remain unchanged. The existing native import-closure tests
pass with this repair; hosted differential/current-base acceptance remains owed.

## Executed verification

**538 tests PASS /12 warnings /0 skips** in the four-file battery: the three
prior earnings/D5/API suites plus all252 native deploy-update tests. The earnings
portion now has286cases, including55new brief/profitability cases. Old counts
are subsets, not additional tests or market observations.

```
python3.12 -m pytest tests/test_us_prophet_fusion.py \
 tests/test_intelligence_vector_units.py tests/test_prophet_lab_api.py \
 tests/test_deploy_update_self_heal.py -q
```

Final logSHA256 `99200a023e695e8d17c4c28f57ea0eb2bacd3814e8728ce07179dbf3f2f43bf1`.
Inputs are controlled fixtures, fictional identity/availability clocks where
specified, the original frozen SEC/Q06 test inputs, and an independently cited
public numeric example. No live subscription, portfolio, queue, historical fill,
model return or broker is used. Existing default C1 and API privacy tests pass.

Three meaningful faults are caught by intended assertions, with original source
restored: disconnecting the actual API brief, hiding the margin component, and
recounting the earlier guidance revision as new results information. Logs:
27f69d376c3ddcdb6017f9816cdaabfed1e1af9f7626029eeb01fae1c6f1732e
51277cee43b5dc67fc87ba2a254a8efa8f60e9cc29a076b4a8f497dc8bfebf9f
cbbee9ff0d655be0c1e35eb16158265a83c690008a996e82fc1af83df4e24fbc
The local fault driver initially expected the literal string AssertionError;
pytest's short numeric assertion output uses `E assert` instead. Its already
produced logs were read and qualified without rerunning those two cases; only
the not-yet-run third case executed after that diagnostic correction.

## Remaining mission and gates

This wave completes a connected evidence-explanation unit, not the Prophet
turnaround. Ordinary UI/paid-browser/deployment proof is still outstanding;
the previous frontend inspection restriction is not bypassed by this JSON output.
Q06#8069's source method remains separately accepted in substance, but its source
CI/release is unfinished. A compound source-worktree/process/collision inspection
was refused before dispatch in this turn; it was not split or rerouted, and no
Q06 custody transfer or branch edit is claimed. #7426/#7870 and other active
research/empirical lanes remain with their original source owners.

Next useful action: consume exact new-head CI and finish the permitted native
source-release/ordinary-user-path proof. Complete source-qualified profitability
coverage before an incremental selection study. The model must compare absolute
profitability, profitability changes and guidance/revision information against
price/sector controls without treating correlated accounting facts as independent
conviction. New hypotheses, data permissions and the original trial budget remain
with the existing scientific/evaluation owners, not this explanation function.

Protected source law: Mastermind5d5c73f9d16a7538ab0bab910afdbfb9c57ee309;
INDEX4b0189a75d559d963365097485e8509a49c70e23; Skillpack1.0.1/bootstrap1.
Required same-pin procedures were fetched and matched previously consumed
identities. No automatic wake, new worker, active policy, live risk reduction,
source-writer release or financial performance is claimed.
