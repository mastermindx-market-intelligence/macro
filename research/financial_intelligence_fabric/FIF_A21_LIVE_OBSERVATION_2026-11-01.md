# FIF A21 — live filing-observation record (natural schedule)

Workstream WS:FINANCIAL-INTELLIGENCE-FABRIC · Z0 closure matrix row A21 · recorded 2026-11-01.

Obligation (matrix row A21, `live_proof`, owner "natural schedule"): observe one
scheduled publish after PR #9871 lands and a later no-new-filing cycle, with the
issuer observation reading `new_filing` and then `checked_no_change`; a withheld
row would carry `observation_write: withheld:<reason>`.

Source: the publish step's JSON report in the logs of every scheduled
`filing-forensics-sec.yml` run from the first one after #9871 merged
(c304c027) through 2026-10-31. Nothing was dispatched or rerun; each log was
read once with `gh run view <id> --log`.

## Per-run publish rows (five published issuers)

| Run | Row outcome | Observation state | persisted | last_checked_at (= last_successful_check_at) | freshness |
|---|---|---|---|---|---|
| 39565177126 | published ×5 | new_filing ×5 | true | 2026-10-21T07:56:04Z | current |
| 39743211524 | unchanged ×5 | checked_no_change ×5 | false | 2026-10-22T07:51:43Z | current |
| 39920254000 | unchanged ×5 | checked_no_change ×5 | false | 2026-10-23T07:51:38Z | current |
| 40074387329 | unchanged ×5 | checked_no_change ×5 | false | 2026-10-24T07:32:02Z | current |
| 40173869305 | unchanged ×5 | checked_no_change ×5 | false | 2026-10-25T07:45:58Z | current |
| 40289203798 | unchanged ×5 | checked_no_change ×5 | false | 2026-10-26T08:02:31Z | current |
| 40471803945 | unchanged ×5 | checked_no_change ×5 | false | 2026-10-27T08:20:07Z | current |
| 40659622001 | unchanged ×5 | checked_no_change ×5 | false | 2026-10-28T08:58:22Z | current |
| 40844287649 | unchanged ×5 | checked_no_change ×5 | false | 2026-10-29T08:52:07Z | current |
| 41029214010 | unchanged ×5 | checked_no_change ×5 | false | 2026-10-30T08:52:50Z | current |
| 41185445273 | unchanged ×5 | checked_no_change ×5 | false | 2026-10-31T08:40:56Z | current |

The generation id of each issuer is identical in all eleven runs:

| Ticker | Generation |
|---|---|
| AAPL | ffprods_384ff7d41204e9e0b556e1cfa2b8deb7689edbb52addd0614b0b96660d01e997 |
| GOOGL | ffprods_55762302a2cd1065d94e95a2c7bab63af050f0947fe0f89d93dc871ba59fccd9 |
| BAC | ffprods_ebed9c8367e48abd88679cdd7c8a084380fa8e0f4ebaf5a5651ccbb9f238012b |
| CAT | ffprods_bfb6d88e252b97ed328e78da1b3321c11a07d4c5b473b0190af2350002509bef |
| SNOW | ffprods_eca300745e567fda2ae48a280abdefedb7533afb93383b424c37126e05b13f72 |

## Reading

- The first scheduled cycle after #9871 writes one `new_filing` observation per
  issuer (`persisted: true`), matching T1.
- Ten later cycles with no material change report `checked_no_change` with
  `persisted: false`: the check advances `last_checked_at` and
  `last_successful_check_at` in the report but writes nothing, which is the
  R-A21-T8B rule pinned by T2, T8 and T9. The stored observation therefore keeps
  the `new_filing` record of 2026-10-21 and the report carries the later check.
- Generation ids never change across the ten unchanged cycles: no regeneration
  and no rerender to refresh freshness.
- The acquire step distinguishes the same two states on its own: on 2026-10-31
  its observation log reports 52 `unchanged` accessions and one `new_filing`
  (AMZN 10-Q 0001018724-26-000040), an issuer outside the published set, so the
  five published rows correctly stay `checked_no_change`.
- No run in the window produced a withheld row: zero `observation_write` keys and
  zero `withheld:` markers in all eleven logs. The producer withholds a record for
  exactly three causes, none of which occurred: a commit-phase store fault
  (`withheld:commit_phase_fault`, test T4), an `admission_refused:*` exclusion whose
  package proved no identity (`withheld:identity_unproven`, test T10) and an
  unchanged generation with no prior record (`withheld:unchanged_without_prior`,
  test T11). An unreadable prior record is not a withheld row: it refuses the whole
  run before any write (`observation_prior_unreadable`, test T6).
