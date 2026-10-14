# Press source supply and producer diagnosis

## 2026-10-14 07:15 UTC — source-supply diagnosis, incumbent bake preserved

Changed the adjacent tactic from repeatedly reviewing restricted bank reports to
checking whether the existing Research window contains a public-institution path,
and tracing the stale own-data supply to its actual producer. The installed catalog
at stable HEAD2af42e8d23cf42d0c32444b6e637d02e6799b564 has178 reports in the21-day
window, SHA5dfee05d66c2b2977c6c3a19916a777b306213bde670d8a7722c6593dfc4fe51.
Institution counts reconcile; all11 Other rows were inspected by metadata. No
explicitly classified government/international-public institution was found.
Three title-keyword matches are private-bank reports mentioning public institutions,
not government-authored sources. This is a catalog screen, not proof about the
entire public web or a rights adjudication of every report. Raw private summaries
and PDFs were not committed. Existing public WH/DOJ listings add no admitted event.

The own-data dependency is now bound to an existing live producer, rather than
an assumed missing schedule. Latest green daily38498969461 is ONLY et_gate;
all17 downstream producer jobs skipped. Actual scheduled daily38495183073 remains
unsettled: collect115629246223 was cancelled, collect_tail115696591188 and
engine115696591645 were in progress; engine was in its regime/dashboard/brief step
since06:01:20Z. Collector metadata shows a cancelled Yahoo backfill and incomplete
push step, but its retained log returned404 BlobNotFound: the cancellation cause
and push effect are NOT proved. No retry, duplicate bake, runner change or producer
rewrite was attempted. Historical liveness38484743799 reported stale source boards
and an orphaned codex runner label at23:31Oct13; its no-run claim predates the
subsequent live daily run and must not be presented as current. Existing CI6351
and its9194/fleet1404 references retain their separate ownership.

Single PR/controller read07:05:08Z:9209 remains OPEN8f705cb3 with inherited pack4
red/11packs pass.13activeproofs/cap8,8920lease populated. Main38520655830 is now
SUCCESS; newer38525525368 is running. Controller retains release authority; no
manual refresh or duplicate proof. Follow-on source8eb467112b83, all24 reviewed
hashes and3page expectations unchanged; reuse429tests/1sparse skip plus1real-data
check and31portable groups. No follow-on PR or installation.

Six diagnostic/read-integrity checks PASS, not new application tests or D14credit.
Next executable edge: consume the incumbent daily run's actual committed/published
bytes when it settles and re-evaluate own receipts from their event dates; finish
controller-admitted9209 landing/install, then the SAME reviewed follow-on. Do not
rerun a live producer or freshen source dates. Future Fed/PMMS releases remain
calendar leads until actually published. Publication/cutover false,credit0/10;
all held drafts, rights/editorial gates, Commission19/Catalyst8678, refused issuer
review andOct11 12:07EFFECT_UNKNOWN remain intact.

verified: source_qualification_20261014_0704/{institution_census.json,
unclassified_catalog_metadata.json,producer_runs.json,producer_jobs.json,
collector_job.json,engine_job.json,producer_diagnosis.json,pr9209_observation.json,
review_verification.json}. GitHub observations used gh api actions/workflows/*/runs,
actions/runs/*/jobs and actions/jobs/*; installed census used existing SSH and
/opt/macro/.venv/bin/python -B with stableHEAD/input hashes, zero runtime writes.
