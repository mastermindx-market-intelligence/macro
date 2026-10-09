# Prophet R6 local receiver: publication clocks and identity continuity

Parent: WS:PROPHET-US-V4-RECOVERY / Macro #6805. Product carrier: #6817.
This is a source/test receipt and dependency finding, not full B06 or R6 acceptance.
No historical grade, plan, alias, episode, policy, publication or production state was changed.

## Source and custody

- Native Codex root/session: `01a11e89-b35d-7a81-9404-5fce2c6170cb`.
- Harness workspace: `/Volumes/Mastermind/agent-workspaces/codex/a850/macro-main`.
- Branch: `claude/prophet-r6-publication-truth-01a11e89`.
- Protected Mastermind procedure: `732cf7be88e7159b4995a8885fbd381cd1484e3e`;
  Skillpack 1.0.1, bootstrap-major 1. Native harness workspaces remain with their harness.
- Macro pickup: `cdbcd143dcfa419ab0637bc11dd4c80368143e2e`; implementation base
  `94a20f53cdb2d866d07089df50567f059bf1073e`. The intervening commit changed only
  `site/stocks/earnings/route-catalog.json`.
- The refused Web acquisition `prophet-rescue-20261008-c1` was not retried.
  `mmx-workspace status --repository macro --operation-id prophet-rescue-20261008-c1 --lane web`
  returned NOT_APPLIED / not registered. The native workspace already existed.
- PR #8192 remains on its existing carrier. Its workspace operation
  `prophet-s0-integrity-repair-r2-20261005-c4-001` read back PRESERVED_DIRTY at
  `07136c56ec6f8492067b468f90c6b4372ca649b4`; neither its dirt nor its refused edit was touched.

## B06 capability delta

`scripts/audit_prophet_plan_chronology.py` now carries an explicit clock-evidence
boundary through the audit and newly generated correction provenance. It preserves
the source plan date, Git recording timestamp and original origination receipt's
capture timestamp separately. It does not replace any with the date of a price bar.
Accepted publication, first user exposure and executable fill remain UNRESOLVED
because this audit has not joined those owners' evidence. This does not assert that
the whole system lacks those receipts.

The same first-add receipt supplies the capture clock and its existing hash. A later
HEAD receipt cannot rewrite it. Later capture of older facts remains later. Malformed
explicit timestamps fail closed; missing legacy capture clocks remain null. A copied
report's claimed VERIFIED publication/fill cannot promote correction evidence.

Tests were written before the implementation: eight new cases failed on missing
clock fields or acceptance of malformed clocks. After implementation:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_prophet_plan_chronology_audit.py tests/test_prophet_integrity.py \
  tests/test_us_candidate_episode_intake.py tests/test_us_candidate_episode.py \
  -q -p no:cacheprovider
```

Initial result: **104 passed**. Initial chronology/correction subset: **48 passed**.
CI infrastructure regression (`tests/test_ci_pack.py tests/test_ci_plan_workflow.py`):
**194 passed, 2 skipped**. CI manifest validate-only passed for 177 jobs.
Agent OS validation: 1,585 records, zero errors and 95 existing warnings. The existing
`unrun-market-plumbing` CI lane now runs the chronology and immutable-correction
suites; the workflow path filter reaches test-only changes. These are local results,
not hosted CI, independent approval or production proof.

Real retained evidence was read without generating corrections:

```python
from pathlib import Path
from scripts.audit_prophet_plan_chronology import audit_plan
root = Path.cwd()
row = audit_plan(root, root / "site/prophet/plans/CRI-BULL-20261005.json")
```

The retained CRI plan reports run date `2026-10-06`, price-basis date `2026-10-05`,
origination capture `2026-10-06T07:43:29.145743+00:00`, and first Git timestamp
`2026-10-06T00:46:54-07:00` at `fe0676ef1241a5646713012ad5145e23e66eab9b`.
The attached JSON preserves those independent clocks and UNRESOLVED exposure/fill.
The existing audit also reports `stale_price_basis`; that verdict is unchanged and
is not a new market or shareholder-return conclusion.

`cri-chronology-clock-read.json` SHA256:
`67a7e14e6c661f77ae3cfab846fbbcbf25a7ba2f89c29543482db636ca4c887b`.

## B02/B03: verified current CRI gap and existing repair carrier

At the implementation base, `load_universe()` in the security-master builder returns
713 legacy seed keys and no CRI. CRI is absent from both reference alias/master
artifacts and from the US company nodes. The current small-cap constituent file does
contain CRI. Current source snapshots separately report CRI on venue code N
(directory `2026-10-08`) and CIK `0001060822`, CARTERS INC (CIK snapshot `2026-10-05`).
Those current facts are not an as-known historical identity grant.

Episode HEAD `peg:99b34095d1776e55c642663b4f56a8b47db36a188d208459071f2a8b95766e7e`
retains 14 CRI suppressions with reason IDENTITY_UNRESOLVED; the first session is
`2026-08-27`, the last `2026-10-05`. They were counted only under the active HEAD
generation, not across every historical generation. No suppression was rewritten.

Existing PR [#8626](https://github.com/mastermindx-market-intelligence/macro/pull/8626),
head `12593af9f1823c37e5c931eb25bdba0ba218e4d7`, adds the existing mid/small constituent
files to the security-master seed loader. It is the forward coverage dependency to
consume, not a reason to fork a Prophet identity allocator. At readback it was DRAFT,
owned by the Information-to-Price seat, with no independent review decision; native
CI packs/gate passed while `ci-authority/codex/merge-queue-pilot` failed. No Ready,
label, merge or source takeover was performed. Its description's old test/CI account
must not replace current head/check evidence.

Separate integration concern: the current membership alias resolver and IssuerMaster
do not impose the rows' ingestion clocks on Prophet `_observation`. A synthetic
identity first ingested `2026-10-09T00:00:00Z` still resolves an observation with
`known_at=2026-10-05T20:00:00Z`. This demonstrates an intake seam, not a replay that
happened in production. PR #8192's additive `identity_fields` projection still calls
that resolver and does not itself close this knowledge-clock seam.

Reproducer (synthetic only, no persisted changes):

```python
from engine.us_candidate_episode_intake import IdentitySpine, _observation
from lib.dataos.identity import VendorAliasTable, IssuerMaster
aliases = VendorAliasTable.from_records([dict(
    vendor="membership", vendor_symbol="FIXTURE", security_id="SEC:US-XNYS-FIXTURE",
    valid_from=None, valid_to=None, ingested_at="2026-10-09T00:00:00Z")])
issuers = IssuerMaster.from_records([dict(
    security_id="SEC:US-XNYS-FIXTURE", issuer_id="ISS:US-XNYS-FIXTURE",
    issuer_state="RESOLVED", listing_key="US-XNYS-FIXTURE",
    ingested_at="2026-10-09T00:00:00Z")])
observation, reason = _observation(
    source="candidate", schema="us_prophet_rank.candidates/v1",
    source_event_id="fixture-old-candidate", receipt="sha256:" + "a" * 64,
    ticker="FIXTURE", session="2026-10-05", spine=IdentitySpine(aliases, issuers),
    intake_class="technical_emergence", anchor=None,
    occurred_at="2026-10-05T20:00:00Z", known_at="2026-10-05T20:00:00Z")
assert reason is None
assert observation["known_at"] == "2026-10-05T20:00:00Z"
```

Counterexample JSON SHA256:
`9ed3aa1c1de8590b3bc6eac59683c4e3ccf93e43a0beacb56e93709f8ccfac59`.
Next owner-native repair must distinguish prospectively captured current identity
from a later snapshot applied to an old decision. Preserve B1 IDs, source keys and
old suppressions; do not manufacture an early BUY or backdate a canonical episode.

## Retained priority obligations

- B06 economic outcome qualification remains open: the shared grader emits a -86%
  synthetic price mark across a 100-to-14 discontinuity without entitlement inputs.
  The registered corporate-action adapter returns UNAVAILABLE with blocker
  `complete_point_in_time_security_and_corporate_actions_contract`. This does not
  quantify CTVA shareholder loss. CTVA/Vylor requires distributed value, entitlement,
  currency/basis and effective trading time before any corrected outcome claim.
- #8192/#8091 retain grading/intake custody and their original review/effect gates.
  #7983 also changes the shared grader; preserve its separate source boundary.
- B09/B04 reuse #7455/#7508 and the existing group owners. No coarse Travel proxy,
  current-membership backfill, self-driven peer metric or automatic group bonus.
- #8444 remains the held shared product carrier. Do not replay its refused
  source-closure action or mutate its retained workspace effects.
- B00-B28 and Q01-Q24 remain obligations of the existing R6 programme. This receipt
  does not retire scientific, earnings, cycle, product, alerts, reliability,
  portfolio, independent review, release, rollback or ordinary-refresh acceptance.

## Delegation and parent adjudication

All requests preserve root `01a11e89-b35d-7a81-9404-5fce2c6170cb` through the installed
stable-handle Fabric adapter. No native children were launched.

- `prophet-r6-b06-review-01a11e89`: refused before launch by the economic guard
  (`leaf_labor_requires_escalation`); same-id readback NOT_FOUND. Not retried.
- `prophet-r6-b02-census-01a11e89`: returned rc=0 through Ubuntu1 / Go /
  `deepseek-v4.1-flash`, with GO_SETTLED. The returned map was consumed as evidence,
  not implementation or independent acceptance. Parent verified the dated resolver
  and current-only issuer limitation. Parent rejected the claim that `_unanchored_batch`
  ignores its caller's session key: it reads that key first. Its latest-session
  candidate selection is not by itself a defect or permission to replay old inputs.
  The result is PARTIAL, not accepted wholesale.
- `prophet-r6-b06-clock-build-01a11e89`: NONE/no_pool_available before launch.
  Parent implemented the bounded, independent audit change under the no-eligible-worker
  exception; this is not authority to serially implement the whole programme.
- `prophet-r6-b06-clock-review-01a11e89`: Grok 4.6 / Ubuntu2 returned a scoped
  PASS after independently reproducing 48 tests and 12 additional probes.
  The exact binding and parent adjudication are in `SCOPED_REVIEW.md`. The review
  artifact is accepted; final source approval and release remain separate.
  Its low-severity source/publication prose leak was repaired with two RED cases.
  Final chronology, immutable corrections and B1 intake/core regression: **106 passed**.

Native source, CI, independent review, deployment, natural refresh and full programme
acceptance remain separate. A queued or active transport handle is not background
completion or a guaranteed future chat wakeup.

Primary-source economic qualification is retained in
`B06_ECONOMIC_SOURCE_QUALIFICATION.md`: the September 24 issuer update supersedes
the earlier expected trading arrangements. This is retrospective evidence, not
proof of historical system capture or a corrected shareholder return.
