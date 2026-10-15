# BEA GVC native-source candidate — implementation and validation

Status: **IMPLEMENTED / HERMETICALLY TESTED / ORIGINAL-SOURCE PROOF HELD / NOT INSTALLED**.

Parent source-purpose proposal: Macro PR #9433 at
`287a49aa0e14fdf4e30f8da6de6da0eb516abbed`. Protected procedural pin:
`Mastermind@f381af6758533906865361373addbb0514f86d7d`, skillpack 1.0.1/bootstrap 1.
This document is implementation evidence, not a source registry, runtime owner,
rights grant, producer installation receipt or production acceptance.

## Delivered interface

`collectors/bea_gvc_native.py::bind_retained_responses` binds owner-supplied
original response bytes, their original capture-receipt bytes and the retained
source-lineage bytes. `materialize_industry_inputs` verifies the entire candidate
before returning an iterator over its L1 candidate rows. No fetch, source-store
write, registry update, application route or public consumer is installed.

The default evidence pin is the existing research lineage SHA-256
`e8856b6f546d55b8e0c41561cb0e60f28ddcd06a78fd04f70d05355890c745a7`.
Explicit replacement pins support separately reviewed corrections and hermetic
fixtures; supplying a digest never establishes source rights or native admission.
All outputs remain `BYTE_VERIFIED_NOT_INSTALLED`, with publication, historical
PIT, ranking, training and trading permissions false.

The selected-year scope must contain complete annual inputs. The retained
lineage contains eight import matrices per year (world plus seven geographic
components) **and a ninth Use table**. The complete 2017–2024 transform therefore
requires 72 original responses, not merely the 64 import responses. Each year
has 138 using industries × 139 commodities = 19,182 candidate rows; the full
panel contains 153,456 rows, or 1,112 per industry.

Original app 157 GetStep responses are decoded through their retained nested
JSON wrappers. The parser verifies release/title/year/units, complete matrix
shape, source names and unique aligned axes. Amounts remain signed integer USD
millions. Suppression, malformed grouping, fractional values and nonfinite
constants are refused rather than filled with zero. World minus the seven
regional components may differ only within the existing ±3 million published
rounding bound. Negative adjustments and residuals remain visible.

Publisher codes are opaque, case-preserving source tokens, not canonical company
identities. They are neither uppercased nor silently crosswalked. The exact
`5241X` identity remains distinct from `5241XX`, with the mapping unresolved and
canonical industry/security IDs null. The lexical envelope is not an identity
or authorization decision; meaning comes from the pinned original bytes.

## Clocks, revisions and ownership

`candidate_ingested_at` is the actual UTC time of candidate construction. It is
**not** a native-store ingestion receipt. All `native_*` clocks and native revision
fields remain null. The May 21, 2026 publication is DAY precision: `published_at`
is null with a precision reason. Accounting years and period ends never become
original historical availability timestamps.

An unchanged input-and-producer fingerprint returns the supplied predecessor
candidate unchanged, preserving its generation and clock. Changed evidence or
producer bytes creates a new candidate revision linked to the supplied predecessor.
The implementation rechecks the predecessor's retained bytes and requires an
unchanged year scope and advancing clock. This is candidate correction lineage,
not a new storage lock, global revision registry or proof of an accepted native
correction chain. Concurrent writer fencing remains with the existing Data OS owner.
The producer hash identifies the observed source file, not a deployment attestation.

Rows share one candidate generation and retain nine original response hashes and
capture-receipt hashes. Retained research capture times remain separately named.
The materializer uses revalidated original-byte parses rather than caller-modified
cached tables, and refuses boolean amounts that compare equal to integers.

## Verification achieved

Command: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_bea_gvc_native.py -q -p no:cacheprovider`.

Result: **30 tests passed / 59 subtests passed**. This includes a full synthetic
72-response, eight-year, 153,456-row generation, exact row counts, signed values,
rounding boundaries, hash and receipt consistency, malformed JSON and source
shapes, source-axis drift, original-code case preservation, admission/clock
refusals, candidate tampering, replay and correction linkage.

`git diff --check` passed. The existing CI manifest gained only the bounded
`bea-gvc-native-candidate` job, running this suite through the incumbent pack
runner. `scripts/ci_pack_fragments.py --check` passed (320 jobs / 322 fragments).
These receipts do not prove hosted CI, real original-source transform success,
native installation or production/browser acceptance.

The previously refused direct local Data OS registry-validation action was not
replayed. Its validation result remains unclaimed; the parent PR's exact-head
hosted CI and independent review are separate requirements.

## Continuation: CI-scope and producer-identity repair

Recovered candidate head `3a21f0955e3e28b26f3155da90c774ada7c3088e` had a failed
hosted CI run `38690614995`. The failing CI contract checks identified the new
job's unregistered exclusive scope, uncheckable exclusive import closure, and
missing `tests/__init__.py` ancestor coverage. The repair uses ordinary additive
scope and explicitly includes both `lib/__init__.py` and `tests/__init__.py`.
No curated allowlist, census ceiling, gate, or existing job was weakened.

A separate source audit found that materialization accepted a self-consistent
candidate manifest naming an arbitrary or earlier producer hash. The materializer
now compares that hash with the observed current producer source file before
returning its iterator. An unreadable producer file raises `BEAGVCRefused`.
An older candidate can still be explicitly rebound to the current producer as a
new linked revision; it cannot directly emit rows under the old producer label.
This is source-file identity checking, not a deployment or runtime attestation.

Three new producer-identity regressions failed before the code repair. Afterwards,
`tests/test_bea_gvc_native.py` passed **33 tests / 59 subtests** (18.03 seconds).
The three exact previously failing `tests/test_ci_pack.py` contracts also passed
(169.66 seconds), and `scripts/ci_pack_fragments.py --check` passed with 320 jobs /
322 fragments. `git diff --check` passed. Exact-head hosted CI and independent
review of this correction remain separate requirements.

No real-source transform, denied source-axis inspection, private research-view
read, local registry-validation action, collection, or source admission was
replayed. The original-source proof below remains HELD.

## Original-source verification attempt — not a pass

The new candidate-transform exercise read 72 retained original response files
(total 207,105,628 bytes) and ten capture receipts, without any network acquisition
or private research JSONL view read. The existing retained lineage pin and capture
receipt pins were checked. A separately inspected 2017 Canada original response
was 2,854,934 bytes and matched its accepted SHA-256:
`db2f0e792ae8880d8f3d99f345be9e461d5f58268901534f7438e2e6b10f19cc`.

The initial full candidate binding failed at `nonunique or nonexact source axes`.
No full source candidate, L1 output or original-source success artifact was produced.
Loading 72 files is not a claim that the failed transform verified every cell or
all 72 response digests. The follow-up inspection of the 2017 Use response's source
axes was blocked pre-dispatch by platform safety. It was not retried or moved to
another carrier. The exact offending original token remains unobserved.

The subsequent code hardening removes an unsupported uppercase-only assumption
and adds case-preservation tests, but this is **not evidence that the original
source failure is fixed**. Only hermetic fixtures were run after that denial.
Resume that affected original-source inspection/validation only after relevant
access or permission evidence changes; never use another tool, account, copied
view or substitute source to bypass the refusal.

## Required adoption sequence

First resolve the parent proposal's exact-head hosted validation and independent
review, without changing its source writer or implying a merge. Then resolve the
original-source access boundary and establish a passing byte-bound native-source
candidate from retained originals, including the Use dependency and exact axes.

The existing Data OS storage owner must install the original-byte L0 and L1
producer, record actual native UTC ingestion and an accepted correction chain,
and verify the installed generation before any `PRODUCED` promotion. Candidate
clocks must not be relabeled as native store clocks. No new registry is required.

Only an admitted native generation may feed the same current-descriptive GMI
human and machine contract. The private functions in PR #8860 do not read this
candidate store and must not be declared native `code_consumers` prematurely.
Authentication, source entitlement, same-generation delivery, explicit refusal
behavior and production/browser proof remain release requirements.

PR #8860's accepted private-research implementation and tests are untouched.
PR #8869 stays offline with its sponsor-rights and UNSENT-email gates intact.
The denied private cumulative handoff and `industry_3341.jsonl` were not opened.
No source collection, source registration promotion, native installation,
public serving, retrospective PIT or trading capability is claimed.
