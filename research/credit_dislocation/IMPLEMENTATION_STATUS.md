# Credit Dislocation Intelligence - recovered implementation status

Date: 2026-10-18. Parent mission incomplete. State: BUILT_NOT_PROVEN, draft implementation.
Canonical carrier: Macro PR #9590, branch `claude/ssd-ccw-dislocation-v1-cc87720e59421398`.
Masterplan: [MASTERPLAN.md](MASTERPLAN.md), first published at `2596c9e58872d1458ddb2ab116a960d22a16b0e6`.

## Implemented in this candidate

- `engine/credit_dislocation.py`: deterministic issuer comparisons over existing CCW issuer histories, latest bond holdings and equity closes. Preserves identifier type, observation dates, matched-sample spread changes, coarse grade/maturity peer comparisons, missing history and stale observations. There is no genuine CDS input, fitted probability, causal claim or trade authority.
- `engine/credit_dislocation_view.py`: bounded read-only display adapter, source-age re-evaluation, English/Chinese explanations, per-issuer bond detail and compact context. A new build timestamp does not make old source observations current.
- `templates/_credit_dislocation.html.j2`: responsive issuer search and filters, keyboard-operable disclosure, lazy bond-detail rendering, interpretation and countercase text. The component uses the existing presentation tokens and is embedded in `templates/bonds.html.j2`.
- `scripts/build_bonds.py`: consumes the prebuilt artifact and adds a compact `corporate_credit.dislocation` context. The renderer does not fetch market data or solve bond prices. The former unbuilt stocks-versus-bonds placeholder remains the fallback when the new view is not supplied.
- `.github/workflows/daily.yml`, `config/dag.yml`, `config/synapse.yml`: adds the comparison producer after the existing CCW calculations and registers the artifact and consumers. This is source wiring, not proof that the deployed scheduler has run it.
- `.github/ci/legacy-jobs.yml`: enrolls affected comparison, view, wiring and solver tests in existing CCW jobs; no check bypass.
- `engine/corp_credit.py`: bounds the existing independent-bond YTM matrix solve to 4,096-row blocks, retaining the established inner solve and explicit shape validation. This followed an interrupted qualification run with excessive memory use in the all-history matrix. It is not proof of the root cause of every older production/data lag.

## Retained local test and browser evidence

The earlier local runs completed; recovery did not rerun them merely because the chat failed.

| Evidence | Observed result | Scope |
| --- | --- | --- |
| `.cdi-proof/integrated-tests.log` | 182 passed in 12.92 seconds | Integrated local source tests; not hosted exact-head CI |
| `.cdi-proof/solver-tests.log` | 75 passed in 5.19 seconds | Existing pricing and bounded-solver checks |
| `.cdi-proof/ui-tests.log` | 178 passed in 15.93 seconds | Earlier local component integration run |
| `evidence/browser/receipt.json` | Four successful browser cases; no recorded console errors | Actual component with explicit synthetic fixtures |

The suites overlap; their counts must not be summed as unique tests.
Source file hashes and retained log hashes are recorded in `evidence/recovery_receipt.json`. The receipt records the files inspected during recovery; it is not a retroactive cryptographic attestation of the original test executions.

Browser cases: 1440px English light, 1440px English dark, 768px Chinese light, and 390px Chinese dark. Each recorded search, filters, keyboard disclosure, one-time lazy bond expansion and no page-wide horizontal overflow. Screenshots are preserved alongside the receipt. The desktop-light and mobile-dark images were visually inspected during recovery. These four cases do not satisfy the full light/dark x English/Chinese x desktop/mobile acceptance matrix, and do not prove the entire deployed Bonds page.

The browser's native-data case used the original local September 8 source snapshot, correctly labeled stale with 18 issuers. It must not be represented as proof against the later refreshed October 15 generation.

## Data acquisition and calculation evidence

The inspected primary checkout had five funds' raw snapshots through October 7, while its derived issuer/bond outputs ended September 8. This was a local binding observation, not a fleet-wide outage finding.

The existing SSGA collector/parser subsequently captured five October 15 snapshots into the isolated worktree: SPIB 5,358 rows, SPSB 1,669, SPLB 2,973, JNK 1,144 and SPHY 1,936. These counts are per-fund positions, not unique instruments or issuers' debt outstanding. Source acquisition did not fill omitted historical sessions.

The original unbounded local rebuild was stopped by SIGTERM: PID 39398, parent 39335; `.cdi-proof/baseline-stop.json` records the action and absence of output files at that boundary. No replacement of an uncertain effect was inferred. The later bounded rebuild completed and wrote:

- 810 issuer history rows on 54 dates from July 10 through October 15;
- 10,376 rows in the latest bond panel, dated October 15;
- 378 theme rows, 594 sector rows, 108 market rows and 6,750 maturity-distribution rows;
- measured engine time 268.70 seconds, process wall time 269.47 seconds, and reported maximum resident set size 1,837,056,000 bytes.

**Pricing validation remains `PENDING`.** The new CDI compiler and browser proof have not yet been rerun against that refreshed generation. The CCW `latest.json` generation date is October 18; the underlying panel observation is October 15. These are different clocks.

Raw captures, refreshed equity/Treasury files and generated `data/` outputs remain local, unstaged and preserved. They are not bundled into this source commit or pushed as newly qualified market data. A bounded SEC public-source feasibility request returned HTTP 503; it did not establish access denial or a general feed outage.

## Paper reconciliation

Canonical Paper carrier: Mastermind Paper. File `01M2WGNCX9475G79JRKJTCM08P`, existing Bonds page `p-1H-0`.

The new light-English specimen is artboard `6GDA-0` (CDI 01 - Issuer comparison), adjacent to the existing R30 work. It reuses the shared shell and tokens. Its content includes the issuer comparison, coarse-peer explanation, explicit CDS-unavailable state and illustrative bond detail. The original R30 Credit/Issuer board `63YS-1` is preserved.

The generation failure occurred after operation `ccw-cdi-20261018-design-06`, targeting `6GMW-0`. Same-carrier readback recovered five children: `6GSP-0`, `6GSV-0`, `6GT1-0`, `6GT7-0`, `6GTD-0`. The screenshot of `6GDA-0` showed the three illustrative bond rows and the coverage caveat. The intended edit is present: **do not replay it**. No unresolved Paper modifying effect remains from that operation. Broader design variants, JSX extraction and final working-indicator closure remain continuation work; no unrelated board or global token change is authorized by this record.

## Remaining delivery and scientific gates

This is not a CDS quote feed, a complete legal debt/guarantee registry, a full issuer liability maturity wall, a calibrated warning model, a persistent saved-case/notification service or a deployed feature.

The coarse peer calculation must not be relabeled a rating-, seniority-, liquidity- and duration-matched fair-value model. The history lacks qualified original publication/system-availability vintages for predictive replay. All rank/size/gate/escalate authority remains false.

Before release: resolve CCW pricing validation and source gaps; recompile/retest the refreshed binding; complete the visual/language/state matrix; reconcile the still-separate maturity correction PR #9589; obtain required independent/repository review and exact-head CI; perform protected delivery and verify the actual Bonds route and machine consumer. Risk Radar predictive authority, genuine CDS entitlement, full financing coverage and longitudinal outcome evaluation remain later masterplan obligations, not silently completed by these tests.

## Recovery boundary

The preceding implementation turn ended with `Thinking failed` in an already heavy conversation. Recovery reconciles effects and preserves source/evidence only. Continue implementation in a fresh same-mode Pro chat from [CONTINUATION.md](CONTINUATION.md), the same workspace and PR. No worker, process or monitor is being represented as durable execution after this response.
