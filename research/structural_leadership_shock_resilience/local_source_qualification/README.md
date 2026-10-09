# SLR-P0 historical source qualification

MISSION: SLR-P0-SOURCE-QUALIFICATION. Parent research PR: [#8645](https://github.com/mastermindx-market-intelligence/macro/pull/8645).
Frozen design: v1.0.1 plus the pre-outcome v1.1 amendment at Macro `1f21fb74735d826a37d5e1925b1d06af6feb6fda`.

RESULT: **NOT_ADMITTED**. INDEPENDENT_REVIEW: **OWED**. OUTCOMES_READ: **false**.
PRODUCTION_CHANGED: **false**. REAL_DATA_READ: **true**, limited to one public SEC
submissions capability sample; **the historical SLR population was not read**.
DATA_SOURCE_RIGHTS: **UNKNOWN overall**; Massive research rights are confirmed by
the existing repository record. PARENT_PARITY: **UNKNOWN on the actual population**.
CODE_PR, COMMIT_SHA and CI publication evidence are in the qualification result
and the PR; null fields mean not observed at that artifact revision.

`adapter.py` is a pure research capability over caller-supplied inputs. It reads
no provider credentials, performs no network requests, discovers no data stores,
allocates no identities and grants no admission. It reuses the Data OS identity
parser and `VendorAliasTable`, the incumbent price-basis vocabulary, and frozen
Winner Autopsy Detector-D constants/math. `IssuerMaster` remains current-only;
the adapter requires separately evidenced historical owner assertions.

Run from the repository root:

```sh
python3 -m pytest tests/test_slr_local_source_qualification.py tests/test_winner_autopsy.py tests/test_dataos_identity.py -q
python3 -m research.structural_leadership_shock_resilience.local_source_qualification.adapter
```

The default CLI returns exit **2** and a deterministic NOT_ADMITTED result because
no historical field package is supplied. With `--stdin`, supply a bounded JSON
object with `decision_at`, `synthetic` and `sources`. Each source contains
`receipt` (the exact `SourceQualificationResult` fields) and `source_object`.
There are no source path arguments or empirical/outcome execution switches.
Use only an already authorized private source plane for proprietary inputs; the
CLI does not authorize access or publication. Unknown fields and forbidden
outcome/protected-path inputs are rejected before qualification.

PASS checks a **bounded field receipt** against its digest, source reference,
valid-time interval and declared availability clocks. It cannot authenticate an
invented permission reference, verify a supplier's coverage claim, or substitute
for independent owner evidence. The specialized helpers test aliases, GICS
interval selection, peer deduplication, calendar windows, corporate actions,
total returns, lagged OLS, first-challenge observability and information counts.
Callers must bind these helper inputs to the same reviewed field objects.

Final-vintage validity is explicitly distinct from ACTUALLY_FIRST_SEEN. A later
ingestion cannot become historical first possession. Filing acceptance must be
combined with public dissemination or a conservative next-session bound in the
receipt's publication field; report-period indexing is insufficient.

`replay_detector` requires complete subject sessions and qualified benchmark
prices at every relevant past candidate date. Its optional `master_sessions`
argument checks exact calendar equality; **real input qualification must supply
that independently retained NYSE index**. No benchmark fallback or inception
fill is allowed. `continuation` applies the incumbent 150-session detection
window and last-five-session candidate override, and rejects a watch onset
different from the original D. Static-sector fixtures compare both paths with
the incumbent detector/watch code. Synthetic fixtures use a synthetic business
day index and do not prove NYSE source-calendar coverage.

The census reports identifying cells and occupied, nonoverlapping 63-session
blocks from a fixed master-calendar origin. These are input diagnostics, never
an estimate of predictive power, alpha or source admission. No forward label is
computed; `measurement_window` verifies synthetic clocks only.

BLOCKERS and NEXT_ACTION are in `EXACT_NEXT_ACTION.md`. The implementation lead
retains the source-qualification action; the Web Meta-CEO retains scientific
admission. Code review/merge does not open the empirical study.
