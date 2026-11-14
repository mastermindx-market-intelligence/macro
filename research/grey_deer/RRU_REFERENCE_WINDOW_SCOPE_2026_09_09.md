# RRU derived-composition reference-window correction

Same parent operation and PR6989; source remains eb9e919; candidate starting head92193b4.
This scope is frozen before its new synthetic tests. No earlier blocked diagnostic,
mutation, review-packet, translation edit or collision census is repeated.

Problem: the candidate checks membership over its most recent30 ranked observations,
but each rank comes from up to504 finite pre-rank observations (`_PCT_WIN`). A missing
member100 benchmark sessions ago can therefore affect the comparison's reference
population while the current30 observations look complete. `_pct` drops all-null raw
rows before ranking, so the reference boundary must follow observed rows, not subtract
504 calendar dates. Missing benchmark sessions inside that span remain disclosed.

The bounded repair uses the existing composition helper and existing comparison flag:
check the union of the actual pre-rank reference windows used by the compared scores;
report its session/observation and incomplete-session counts. No new coverage threshold,
confidence score, forecast, policy owner or ledger. Full observed-reference controls must
retain their existing flag. Missingness strictly before that union must not block it.
All ten actual international profile definitions get inside-member-gap, inside-all-null
and outside-window controls. Producer, projection and current recovery-unavailable
consumer remain the existing owners. Raw market inputs and all production files stay
unchanged; this is another in-memory research candidate, not source release.

This tests derived-input membership only. It does not prove raw-feed freshness, upstream
percentile data vintages, calibration, historical predictive skill or policy applicability.
The two published serialization/authority release counterexamples remain separate.

## Executed evidence

Process3555 ran the frozen three-case-per-profile suite before the helper repair:
30 tests,20 expected failures and10 controls, exit1. Process7014 then ran the same
suite with the amended helper:30 tests, zero failures/errors, exit0. The guard now
qualifies the existing comparison using the union of finite-raw-observation rank
references and includes benchmark gaps within the span. Current observed scores,
profile weights, rank function and probability/permission owners are not changed.

The actual producer, composition projection and current recovery-unavailable rendering
are exercised. New reference counts are diagnostic metadata, not confidence estimates.
An attempted extra boundary-test edit/run was platform-blocked; direct read confirmed
the original30-case source remained. No retry or50-case claim follows. Exact adjacent
boundary assertions and independent review remain owed, as do raw-feed freshness,
vintage, calibration and production proof. This is a scoped improvement, not a claim
that all possible sources of rank noncomparability are solved.

The first regression run passed91 composition tests, then found one contradictory old
edge expectation: ten all-null sessions70–80 observations ago were considered cleared
once they left the latest30 scores. They still lie inside the rank-reference union.
That expectation is superseded, not waived. Its revised test must require recent-gap
count0, reference-gap count10 and a qualified/unavailable composite comparison. The
already-executed outside-reference controls prove the guard is not permanent.
The proposed exact-adjacent-boundary expansion remains unimplemented and blocked.

This conservative descriptive guard can reduce composite-based recovery coverage for
long periods after missing inputs. It must not suppress independently observed price,
breadth or stress-repair evidence. Those objects are preserved but their existing hidden
panel remains a separate consumer defect; this candidate is not yet the complete useful
risk/recovery product and is not accepted for deployment.
