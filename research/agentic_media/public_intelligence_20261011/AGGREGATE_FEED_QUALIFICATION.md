# Aggregate White House feed: qualified planning repair

Operation: `mmx-public-intelligence-delivery-20261011-local-ceo-001`.
This next phase is separate from the fixed release head of Macro PR8786,
`9019a29c2e35da499fb5c822e515be9ce9c21027`. It must not restart that release's CI.

The existing sentinel reads `/news/feed/` first and retains `section=news`.
Canonical entries can live under `/fact-sheets/`, `/research/` and five other
observed official sections. The opt-in Press planner previously required the
feed section to be the first URL path component, rejecting such entries even
when their exact bytes and claims were separately qualified.

The bounded repair separates those two identities. News-feed provenance admits
only news, fact-sheets, presidential-actions, research, remarks,
briefings-statements and releases routes. A section-specific feed still requires
its own route. Unknown feeds, malformed paths, traversal, encoded separators,
credentials, alternate hosts, query/fragment components and URL parser
normalization are rejected. Document identity is never rewritten for admission.
The existing source/policy/body hashes, rights scope, clocks, quantity arithmetic,
dossier inventory, duplicate coverage and publication boundaries are unchanged.

## Evidence and review

The admitted Fabric leaf `mmx-press-aggregate-feed-fix-20261012-001` returned its
bounded two-file patch at rc0. Parent retained and hashed the exact stdout, then
retrieved the manifest-advertised artifacts through the same installed adapter.
The successful export receipt and current files match the scoped manifest. This
is not attestation of unobserved historical worker bytes or automatic acceptance.
`aggregate_feed_review.json` binds the input/output digests and parent source.

A destination argument outside the adapter's fixed evidence root failed local
reservation before artifact transport. No denied destination was written and
no worker was replayed. The same adapter exported to its documented permitted
`/Volumes/Mastermind/evidence` root with the same run, host, root, parent, stdout
hash and manifest paths; its complete receipt is retained there.

Parent ran the new regressions against the old implementation: 9 failed and
38 passed. Two failures prove the aggregate-route defect; five expose accepted
malformed paths; the remaining two show downstream checks were never reached.
The worker patch also admitted URLs altered by `urlsplit` normalization. Three
additional parent regressions failed (49 passed), then the parent required exact
URL round-trip equality. An aggregate document with a different body must still
have its own matching body qualification; missing feed identities fail closed.
After materializing tracked `data/` through the existing sparse helper, the
external-candidate, planner, validator and White House feed suites passed all
186 tests in 9.50 seconds. The first broad run had 185 passes and one missing
real-data fixture failure; the corrected environment resolves it without any
test waiver. Differential contract checking against209f77267304 has zero
introduced and zero inherited findings in514.2seconds. Exact commands and
source hashes are in aggregate_feed_review.json; raw results are retained in
aggregate_feed_green.txt and aggregate_feed_contract_delta.txt.

## Current source qualification is narrower than story admission

`manufacturing_report_source_qualification.json` binds the October10 CEA report
release, its retained news-feed document and the official copyright policy.
The assigned principal accepts only original attributed reporting about the
release and the government's description. The linked PDF, vendor charts,
private-company quotations and other third-party material are excluded.
The retained RSS body contains no Apple, Micron or NVIDIA names. It supplies no
company association, analytical receipt, Press writer slot or article approval.
A real consumer probe rejects this reference-only record before candidate or
writer admission (`manufacturing_report_reference_boundary.json`).

`aggregate_feed_identity_comparison.json` records that the October8 science item
has the same ID, GUID, URL, title and publication time across the section and
aggregate feeds, but different body hashes because their opening headings differ.
Do not reuse one body's qualification for the other. Its event is expired on
October12 regardless of capture time or this route repair.

No provider invocation, staged draft, publication, ledger mutation or installed
runtime claim follows from this phase. After PR8786 lands, integrate the exact
protected main, retain only this follow-up diff, and use the ordinary protected
release path. The current story path continues with the existing nonpromoting
full earnings audit and fixed adjusted-baseline qualifier after their source
lands; source integrity alone does not supply full-article rights.
