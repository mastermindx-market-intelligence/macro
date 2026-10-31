# GMI consumer reconciliation census — 2026-10-19

Recovery-doc §9 step 5a (`research/theme_graph/GMI_PROGRAM_RECOVERY_2026-10-16.md`),
WS:GMI-THEME-GRAPH, Orchestrator B under Fable Meta-CEO seat 6f14c2da.

**What this is.** A read-only record of the installed and served state of the GMI
consumers: F04/E20 economic context, the W3C US/China cohort and the Terminal consumers.
It also lists every unresolved effect with its carrier and owner. Every claim names the
exact command behind it.

**What this is not.**
- It is not a content claim about any authenticated response.
- It is not production proof.
- It integrates, replays, retries and recreates nothing.

**Read-only scope.** Nothing outside this branch's two files was changed:
- Production was read with anonymous status-only GETs, one per URL.
- `charting-app` was read with `git grep` / `git show` / `git merge-base` against its
  existing `origin/master` ref. That ref already equalled GitHub `master` (§5), so no
  fetch was needed.
- GitHub facts come from orchestrator `gh` reads (marked *orchestrator read*).
- No VPS shell, no credentials, no cookies and no browser were used.

Interpretation rule for HTTP status:

| Status | Meaning |
|---|---|
| `401` / `403` | The route is mounted and auth-gated. |
| `404` | The route is not mounted, or the path is unknown. |
| `5xx` / `000` | Unavailable or indeterminate. |

A status code is **not** a content claim. It is also not proof that an entitled user can
read a fact.

## 1. Source identity

- Census branch base: `git rev-parse HEAD` → `71bcc7ce9bac60d3fb4646412da46598bda643cf`.
- Fresh main (read 2026-10-19T06:12:33Z):
  - `git fetch -q origin main && git log -1 --format='%H %cI %s' origin/main`
  - → `71bcc7ce9bac60d3fb4646412da46598bda643cf 2026-10-18T23:06:34-07:00 fix(tiingo): complete denial handling and prove stream cleanup (#9635)`.
- Production probes were taken earlier, at 2026-10-19T05:38Z, while main was
  `af9854fe19796f15e2f30a69fbc6c39f60306336` (#9621). No commit between that probe and
  `71bcc7ce` touches the paths below. The source claims in §2 were re-run on `71bcc7ce`.

## 2. F04/E20 economic context — source state on main

Routes mounted by `app/company_disclosures.py`:
- `git grep -n "@router.get" origin/main -- app/company_disclosures.py` →
  - `113: @router.get("/product-integrations/{fact_id:path}")`
  - `142: @router.get("/issuers/{issuer_id}/product-integrations")`
  - `163: @router.get("/company-context")`
- `git grep -n "APIRouter(prefix" origin/main -- app/company_disclosures.py` →
  `60: router = APIRouter(prefix="/api/company-intelligence/private", route_class=_PrivateRoute)`.

`GET /issuers/{issuer_id}/economic-context` on main:
- `git grep -n "economic-context" origin/main -- app/` → no match (exit 1).
- **Not on main.** It arrives with Macro #9423, which is not merged (§6 row d).

Router wiring:
- `git grep -n "company_disclosures" origin/main -- app/main.py` →
  - `2484` imports the router;
  - `2485` calls `app.include_router(company_disclosures_router)`;
  - `2490` imports `PrivateDisclosureReader`.

Deploy restart coverage:
- `git grep -n "company_disclosures\|economic_context" origin/main -- app/deploy/update.sh`
  → no match (exit 1). There is no path-specific entry.
- Coverage is generic instead:
  - `git grep -n -o "engine/company_intelligence/[^|]*" origin/main -- app/deploy/update.sh`
    → `app/deploy/update.sh:1304:engine/company_intelligence/.*\.py`.
  - The same line 1304 opens with `^(app/.*\.py|app/requirements\.txt|…` and also covers
    `engine/theme_graph/(store…` and `engine/market_ontology/(__init__…`.
- So a change to `app/company_disclosures.py` or `engine/company_intelligence/*.py` is
  inside the API restart regex. A new `engine/market_ontology/<module>.py` imported by
  the API is covered only if that line names it.

Private-root provisioner:
- `git ls-tree origin/main app/deploy/ | grep -i private` →
  `blob e4835067… app/deploy/company-intelligence-private-roots.py`.

Engine readers:
- `git ls-tree --name-only origin/main engine/theme_graph/ | grep -E "economic|issuer"` →
  no match (exit 1). The theme-graph economic reader also arrives with #9423.
- `git ls-tree --name-only origin/main engine/company_intelligence/ | grep -E "context|disclos"` →
  - `current_company_context.py`
  - `current_context_runtime.py`
  - `issuer_disclosure_owner.py`
  - `issuer_disclosure_preflight.py`
  - `issuer_disclosure_publication.py`
  - `issuer_disclosure_selection.py`
  - `issuer_disclosures.py`

#9423 head drift:
- At 05:10Z: *orchestrator read* `gh pr view 9423 --json state,headRefOid,mergeCommit` →
  OPEN `44374d0c30c64a60bdd323b86277834bbd9cf45c`, no merge commit.
- At 06:12Z: `git ls-remote origin refs/pull/9423/head` →
  `5e1b3417ac1cac53ff582786e185706d9ba45cb0`.
- The carrier advanced after the 05:10Z read and is still unmerged on `71bcc7ce`.

## 3. F04/E20 — served state in production

All production requests were one literal shell command:

```
for u in <4 API URLs>; do t=$(date -u +%Y-%m-%dT%H:%M:%SZ); r=$(curl -s -o /dev/null -A 'gmi-orchB-census/1' -w '%{http_code} %{size_download}' --max-time 20 "$u"); printf '%s\tGET\t%s\t%s\t%s\n' "$t" "$u" "${r% *}" "${r#* }" >> probes.raw; done
```

Its rules:
- one request per URL;
- no retry, no query parameters and no redirect following;
- no cookie, token or `Authorization` header.

Rows are verbatim in `probes.tsv`.

| URL | Status | Bytes | Reading |
|---|---|---|---|
| `/api/company-intelligence/private/company-context` | 401 | 117 | mounted, auth-gated |
| `/api/company-intelligence/private/issuers/US-NVDA/product-integrations` | 401 | 117 | mounted, auth-gated |
| `/api/company-intelligence/private/issuers/US-NVDA/economic-context` | **404** | 22 | **not mounted in production**; consistent with §2 |
| `/api/health` | 200 | 101 | API liveness only |

- F04 private routes are mounted and auth-gated in production.
- The E20 economic-context route is not served.
- Authenticated content was **not observed** (§8).

## 4. W3C cohort — served projection and source-side artifact

Served:
- The same probe command fetched `https://www.mastermind-x.com/neuralwebdata/selection_cohort/{us,cn}.json`
  (`curl -s -A 'gmi-orchB-census/1' --max-time 20 <url> -o <m>.json -w '%{http_code} %{size_download}'`).
- Both returned **401 / 76 bytes**, with body
  `{"locked":true,"reason":"authentication_required","signin_url":"/?signin=1"}`.
- The production path is auth-gated, not public. The served projection fields
  (`availability`, `unavailable_reason`, …) were **not observed** anonymously.

Source-side (committed render), for `m` in us and cn:
- Command:
  `git show origin/main:site/neuralwebdata/selection_cohort/$m.json | jq -c '{schema,availability,unavailable_reason,generation_id,cohort_scope,n_selected,authority_ceiling,can_rank,can_size,can_gate}'`
- `us` →
  `{"schema":"mastermind.selection_cohort_projection.v1","availability":{"overlap":"UNAVAILABLE","status":"UNAVAILABLE"},"unavailable_reason":"SOURCE_UNAVAILABLE:CAPTURE_RIGHTS_UNAVAILABLE","generation_id":null,"cohort_scope":null,"n_selected":0,"authority_ceiling":"research_internal_only","can_rank":false,"can_size":false,"can_gate":false}`
- `cn` → identical, with `SOURCE_UNAVAILABLE:CAPTURE_RIGHTS_UNAVAILABLE`.
- Last render commit, from `git log -1 --format='%H %cI %s' origin/main -- site/neuralwebdata/selection_cohort/$m.json`:
  `55717122d773d9c021c5d1b0e6578e54158d3a82 2026-10-06T20:25:02-07:00 render: site re-render 2026-10-07 (scope=all, from=03cdf5bde1d9)`.

Reading:
- `CAPTURE_RIGHTS_UNAVAILABLE` is the honest degraded refusal. It is **not** a source
  mismatch (DSC:GMI-CAPTURE-RIGHTS-REFUSAL-IS-NOT-SOURCE-MISMATCH).
- Neither market has an authorized positive capture in the committed render.
- The degraded-vs-positive distinction is the subject of §9 step 6, delivered separately
  as `engine/market_ontology/cohort_us_china.py`.

## 5. Terminal consumers (charting-app, read-only)

All reads ran against the existing local clone `/Users/chriswong/Documents/Cluade/charting-app`
(`C`) with no fetch, checkout or build.

Master identity:
- *Orchestrator read* `gh api repos/mastermindx-market-intelligence/mastermind-terminal/commits/master`
  → `e45bde2cac07ac3b29285ff70c40d68900fad62c 2026-10-19T04:12:13Z Merge pull request #859 …`.
- `git -C $C rev-parse origin/master` → `e45bde2cac07ac3b29285ff70c40d68900fad62c`.
  The local ref equals GitHub master.

Capture-rights refusal copy on master:
- `git -C $C grep -n "capture_rights\|CAPTURE_RIGHTS" origin/master -- terminal/lib/selectionCohort.ts`
  → no match (exit 1).
- **Absent on master.** The fix is held in #868.
- Last touch, from `git -C $C log -1 --format='%H %cI %s' origin/master -- terminal/lib/selectionCohort.ts`:
  `38a5a7da096aa13cda75cfba4d3b648ed76e0603 2026-10-06T06:52:53-07:00 prophet(us): gate #8 - read-only Shared themes …`.

#868 head and diff:
- *Orchestrator read* `gh api repos/…/mastermind-terminal/pulls/868` →
  `open e199c9e5357427a2da4722e5ef3e2da326a6d0bd draft=false labels=hold mergeable=true`.
- `git -C $C diff --stat origin/master...e199c9e5357427a2da4722e5ef3e2da326a6d0bd`
  → `5 files changed, 155 insertions(+), 5 deletions(-)`:
  - `terminal/components/prophet/SelectionCohortCard.tsx` (5)
  - `terminal/components/prophet/prophetStrings.ts` (3)
  - `terminal/lib/__tests__/SelectionCohortCard.test.tsx` (87)
  - `terminal/lib/__tests__/selectionCohort.test.ts` (59)
  - `terminal/lib/selectionCohort.ts` (6)

Private Company Intelligence consumer (#944):
- `git -C $C merge-base --is-ancestor a48cd440f528f67dba59cfeac95b39e14a18e5f8 origin/master && echo ancestor`
  → `ancestor`.
- *Orchestrator read* `gh api repos/…/compare/a48cd440…master` → `ahead ahead_by=49 behind_by=0`.
- `git -C $C show --stat --format= a48cd440f528f67dba59cfeac95b39e14a18e5f8 | tail -1` →
  `73 files changed, 7534 insertions(+), 7 deletions(-)`.
- The same `--stat`, filtered with `grep -E "companyIntelligencePrivate|usePrivateCompany"`, includes:
  - `terminal/lib/companyIntelligencePrivate.ts` (834)
  - `…PrivateServer.ts` (421)
  - `…PrivateLex.ts` (147)
  - `…PrivateView.ts` (59)
  - `usePrivateCompanyIntelligence.ts` (785)
  - their tests (702 / 887 / 1449)

Macro API paths the Terminal calls:
- `git -C $C grep -n "company-intelligence/private" origin/master -- terminal/ | head -8` →
  `terminal/lib/__tests__/companyIntelligencePrivateRoutes.test.ts:21-23` imports the
  three Terminal proxy routes:
  - `@/app/api/company-intelligence/private/issuers/[issuerId]/product-integrations`
  - `…/product-integrations/[factId]`
  - `…/company-context`
- `git -C $C grep -n -c "economic-context\|economic_context" origin/master -- terminal/`
  → no match (exit 1). **There is no Terminal economic-context consumer on master.**

Render:
- **Not observed by this census**, because no authenticated browser session was connected.
- Anonymous status: `curl … 'https://app.mastermind-x.com/options?tab=prophet'` →
  `200 / 31493`. This is the shell HTML only.
- The most recent render evidence is §6 row b / §7: the Astra Chrome read on
  2026-10-11 (Terminal #868 comment 6103693287). It showed the old generic source-match
  copy.

## 6. Unresolved effects

| # | Effect | Carrier | Owner (as recorded) | State | Do not | Release / settlement condition |
|---|---|---|---|---|---|---|
| a | Two retained API HTTP 524 effects (F04) | Macro #6819 checkpoint comment 6112033805 | CEO A, root `01a128b5-e26b-7b12-94b5-231bfe0b8036` | EFFECT_UNKNOWN; cause/termination UNKNOWN | never replay | Same-carrier reconciliation by the owner. Publication 040b stays immutable. |
| b | Terminal #868 W3C capture-rights refusal-copy fix | mastermind-terminal #868, head `e199c9e5`, label `hold` | GMI root `theme-fabric-e2e-20261008-sol-001` (Sol carrier) | OPEN; source review + CI accepted; current-base integration HELD | never bypass; no other PR carries its change | §7 |
| c | Macro #9216 API identity-parse repair | Macro #9216, head `232c565b0ff6998e4e27dbcb2a989f2c8e51c254` | GMI recovery owner, receiver root `01a1468f-b66c-707c-80cc-b66b7553b0cd` (#9216 comment 6233463824) | OPEN non-draft; was mergeable=false/dirty, `merge-blocked`, auto-merge null; cause UNKNOWN (G3) | no parallel repair | The recovery owner reconciles and ships on its carrier. |
| d | Macro #9423 economic-context carrier | Macro #9423, head `5e1b3417ac1cac53ff582786e185706d9ba45cb0` (06:12Z) | Fable Meta-CEO seat 6f14c2da | OPEN, unmerged | no second carrier | The seat merges. Then F04 composition + API parity (step 5b/5c) run on post-merge main. |
| e | Macro #8793 equity-ownership | Macro #8793 | Sol (HOLD-FOR-SOL) | OPEN draft; platform-refused release | never retry | An explicit Sol/Chairman release on a lawful carrier. |
| f | Terminal #796 (aging) and #847 (Finviz discovery) | #796 draft head `0dfb1d8f`; #847 head `79213e80` | their existing carriers | OPEN, unfinished | never recreate | Their owners finish them on their carriers. |
| g | Terminal #959 and #960 | #959 head `332944f0`; #960 merge `be74bcf8ad4f4dbeeefa9c1dbaad1c4353f8afae` | E20 (shared host/deployment) per G3 | #959 CLOSED; #960 MERGED (state observed, not inferred) | never recreate | None owed by this lane. Deployment/live proof of #960 is not observed here. |
| h | Macro #6514 K3-D hypotheses | Macro #6514, head `7d4c665668369bebbf7a4791bd475a63fb40371c` | K3-D owner | OPEN; hosted-run dependency integrity not passed | hypotheses never become observed flows | Release + native/F04 composition owed (recovery doc §2). |
| i | Accepted C01 publication | `040b2f2e50e6611ce6cb4a4fe9e7028f06199e6837bbd436ff1f712ba603d368` | C01 / CEO A | ACCEPTED, immutable | never rewrite | None; it is the sole F04 positive source. |

Sources for the table:
- Rows a, c and i: *orchestrator read* `gh api repos/mastermindx-market-intelligence/macro/issues/comments/6112033805`.
- Rows b and d–h: *orchestrator read* `gh api graphql` (macro PRs 6504/9216/8793/6514;
  terminal PRs 868/944/959/960/796/847) plus `git ls-remote origin refs/pull/9423/head`.
- Recovery-doc rows: `git show origin/main:research/theme_graph/GMI_PROGRAM_RECOVERY_2026-10-16.md | sed -n '31,34p;209,210p;222p'`.

## 7. #868 hold-resolution path

All facts here are *orchestrator read*
`gh api repos/mastermindx-market-intelligence/mastermind-terminal/issues/868/comments`.

- **Owner:** GMI root `theme-fabric-e2e-20261008-sol-001` (Sol carrier), WS:GMI-THEME-GRAPH.
- **Accepted:**
  - Comment 6075547839 (2026-10-09T06:20Z) accepts an independent source review on exact
    `e199c9e5357427a2da4722e5ef3e2da326a6d0bd` over base `048e019c`. The technical
    source hold was released.
- **Refused effect:**
  - Comment 6075735969 (2026-10-09T06:35Z) records that protected `master` had advanced
    to `9e272f08` via #869.
  - The bounded command to merge current master into #868 was **blocked before dispatch
    by the carrier platform's safety checks**. No process or modifying receipt was issued.
  - The refused effect is the current-master integration of #868 on its original
    carrier.
  - A platform safety refusal ends that effect's retry. It is never re-obtained by
    switching carrier, model or account.
- **Live state:**
  - Comment 6103693287 (2026-10-11T00:20Z) holds Astra's read-only Chrome evidence: the
    Prophet › Macro Plans › SHARED THEMES card still shows the OLD generic source-match
    copy.
  - Master still lacks the fix (§5).
- **Release condition**, in order:
  1. The holding authority (Sol, or the Chairman) explicitly releases or re-commissions
     the integration on a lawful carrier.
  2. Exact-head current-base integration.
  3. Concluded binding Terminal CI.
  4. The independent exact-head review is retained.
  5. Ordinary release.
  6. Authenticated production proof of the corrected EN/ZH capture-rights copy.
- Until then #868 stays OPEN with label `hold`. No other PR may carry its change
  (recovery doc §2: "must not be bypassed through another PR"). This census proposes and
  attempts no integration.

## 8. Gaps (NOT OBSERVED)

| Not observed | Reason |
|---|---|
| Authenticated F04 responses (`company-context`, `product-integrations`) and their content | No authenticated session was connected to this census. Credentials are never copied, and anonymous bypass is never attempted. |
| Served W3C cohort projection content | The production path returned `401 authentication_required` anonymously. Only the committed render (§4) was read. |
| Terminal render of SHARED THEMES and the private Company Intelligence consumer | No browser was connected. The latest render evidence is the 2026-10-11 Astra read (§7). |
| Production install SHA of the API host | No VPS shell, by rule. `/api/health` is liveness only. |
| Causes/termination of the two retained 524 effects | UNKNOWN per the owner checkpoint. Never replayed. |
| #9216 current-head CI | Not read by this census. |
| #960 deployment/live proof | Not read by this census. |
| Post-#9423 API parity (economic-context served) | #9423 is unmerged. This is step 5c's subject, which waits on the seat's merge. |
