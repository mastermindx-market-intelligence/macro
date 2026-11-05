# Existing earnings audit: recoverable packet discovery

Operation: `mmx-public-intelligence-delivery-20261011-local-ceo-001`.
Implementation: `b6428b41905836ac8cd6474e6948987b3893cd2a`.
Integrated source: `1c7b997f92fbe611d84a5e0c48a16291c90a6f1f`, including protected
main `1761e5bd5d8ba223719e797bca54549c8fc9f324`.

The Chairman instructed the root to own qualification directly. Historical
Earnings/C19 labels are source context, not an active-writer or pickup gate.
No further owner-message request is required. Commission 19 and Catalyst #8678
remain unchanged; existing source contracts and real rights/access/release
controls still apply.

The existing projection logs counts and a generation but retains no exact
packet/revision tuple. Its existing full audit now optionally writes
`earnings.story_packet_discovery/v1` after complete object, ancestor, evidence,
journal and final root/ETag verification. The existing audit job uploads that
file only on success, with a run/attempt-qualified name and 14-day retention.
There is no new workflow, trigger, credential, model invocation or R2 mutation.

The receipt lists the complete catalog in canonical event-key order. Each row
contains event identity/date, exact packet/revision, existing promotion tier,
source hash and immutable packet object/hash. Root/evidence/policy hashes bind
the snapshot. It includes no transcript, story, draft or Press slot body. Rights
are explicitly unresolved; `allow_stage` and `allow_emit` are false, and a fresh
normal ingress audit is still required. A successful projection without a full
audit does not produce this artifact, including the credential-free skip case.

The output is an audit-time snapshot, not currentness at consumption. Exclusive
creation preserves prior evidence; the local file write is not atomic, so file
existence alone is not a successful run receipt. A failed or interrupted command
cannot upload its file through the success-gated workflow step. No real remote
audit or qualified live packet is claimed by this source change.

## Verification

Six new discovery regressions failed before implementation; the CLI test was
then tightened to require the specific remote-audit diagnostic. After repair,
the five affected earnings suites passed **74 tests in 6.69s**. An additional
real Git sparse-checkout test verified that a committed dossier absent on disk
remains discoverable through the existing helper; the dossier suite passed
**15 tests in 3.67s**. No extra page checkout or weakening was needed.

After conflict-free current-main integration:

```sh
python3 -m pytest tests/test_press_validators.py tests/test_press_run.py tests/test_press_writer.py tests/test_press_staging_inspection.py tests/test_earnings_dossier_link_contract.py tests/test_earnings_story_press_ingress.py tests/test_earnings_story_press_workflow.py tests/test_earnings_story_press_stage_workflow.py tests/test_publish_earnings_story_packets_r2.py tests/test_refresh_earnings_story_packets.py -q --tb=short --basetemp=../mmx-phase2-integrated-fixtures
python3 -m scripts.build_free_content --check
```

**275 passed in 14.10s**, no skips. The estate remains **69 byte-identical
outputs, zero orphans, three exemptions**. Controlled transports/providers only;
no actual R2, provider, staging, emit or ledger call. Logs:
`/tmp/mmx-discovery-red.log`, `/tmp/mmx-discovery-green.log`,
`/tmp/mmx-discovery-sparse.log`, `/tmp/mmx-phase2-integrated.log`,
`/tmp/mmx-phase2-estate.log`. Counts overlap and must not be added.

One bounded native acceptance judgment found no blocking boundary violation in
the discovery diff and explicitly retained its snapshot and non-atomic local
write limits. That review is source acceptance, not remote or live proof.

## Current input and release boundary

A names-only repository-secret read found the existing publisher `R2_*`
credentials provisioned. It did not establish a working read path or permit
substituting that broader identity for `EARNINGS_R2_READ_*`. The earlier
anonymous R2 403 remains preserved without another identity/host retry. The
Terminal `terminal/public/data/tx` path and the two existing Macro checkouts'
`data/transcripts`, `data/us_fund/_tx_index.json`, `data/earnings_evidence` and
`data/earnings_story_packets` paths were absent. No synthetic local source or
audit binding was constructed from a rendered web page.

The next execution is protected delivery of the same PR, installation and
browser checks. After landing, consume the discovery artifact from the existing
successful full-audit lane, qualify one actual event and its rights, and use the
unchanged read-only exact-tuple staging ingress when its real credential and
release gates are available. Do not dispatch a promoting projection merely to
retrieve identities; do not enable publication or substitute credentials.

Final integration checks: `python3 -m pytest tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure -q --tb=short --basetemp=../mmx-phase2-closure-fixtures` passed **1 test in 143.73s**. `python3 scripts/agentos.py validate` checked **1,657 records, zero errors, 141 advisory warnings**. `git diff --check` passed. Chrome on the exact integrated local site verified Blog → Research → Glossary and retained the existing signup/login links. This browser check is local, not installed production acceptance.
