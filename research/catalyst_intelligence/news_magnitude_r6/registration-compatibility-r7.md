# R7: historical registration integrity and current implementation eligibility

Date: 2026-10-20. Operation: `catalyst-news-delta-r4-20261019`.
Parent source: `d62eade5b581b8613ea0cb2272c63495f7117358`, PR #9732.
Disposition: **source-contract repair verified; Draft / HOLD retained**.

## Why this continuation is needed

R6 correctly changed the producer identity to `ni-producer-facts-2` when it preserved
canonical quantity evidence for corrected-amount comparisons. The original Section 11
research registration remains `ni-producer-facts-1`. Its original artifact is immutable:
the Section 11 README and original
`agentos/handoffs/PROPHET-NEWS-IMPACT-2026-10-15-SECTION11-REG.md` require a separate
registration version and decision for a changed experiment after GLM outputs exist.
This repair does not assume whether those outputs exist.

The earlier R6 composed run recorded 1251 passes and one failure: the registration test
rebuilt the original registration identity from current component versions. That failure
correctly exposed version drift, but the API offered no explicit historical reconstruction
separate from current-code eligibility. The old write path could also write the new
producer identity into a document still labeled registration v1.

## Changed contract

`build_historical_registration_v1()` reconstructs the original metadata from the existing
pinned inputs, joins, counts and deterministic draws. Its complete immutable version
profile and rendered digest bind it to the original v1 artifact. It does not read and
return the expected JSON, execute the historical producer, or grant current eligibility.

`current_code_versions()` describes the loaded code independently and continues to
report producer-facts v2. `require_registered_implementation()` first requires the
original complete registration identity, then compares every registered/current component
key and value. Missing, additional and changed components refuse. It accepts no
caller-supplied replacement version profile.

The existing public `build_registration()` remains a current-eligibility boundary:
it refuses unless historical integrity and current implementation compatibility both hold.
The existing `--check` still refuses R6 with
`REGISTERED_IMPLEMENTATION_MISMATCH`, naming producer-facts v1 versus v2.

The separately named `--check-historical-v1` verifies the committed bytes and prints
“historical v1 integrity ok; current eligibility not checked.” Output and check modes are
mutually exclusive. Unregistered current code is refused before directory creation or
file opening, including an explicit output at a different destination.

An eligible write may create a new file exclusively or leave an identical existing file
untouched. It never truncates an existing destination. Exact paths, symlinks, hard links
and a destination arriving between preflight and creation cannot overwrite prior contents.

## Verification and independent review

The root executed:

```sh
python -m pytest -q tests/test_news_impact_section11.py tests/test_news_impact_producer_facts.py tests/test_news_impact_thesis.py
git diff --check
python scripts/check_validated_claims.py --scope source
```

- **198 tests passed, zero failures**, exit 0, in 70.00 seconds of pytest time.
  This includes all 60 Section 11 cases and the 138 R6 producer/thesis cases.
  Two inherited pytest temporary-directory cleanup warnings do not represent failures.
- The real module CLI distinguishes historical integrity success from current compatibility
  refusal. Tests also exercise default output in an isolated destination root, explicit
  new output, exact/symlink/hard-link destinations, conflicting argument modes, changed
  pinned metadata, forged registration identity, complete component-key comparison and
  exclusive-create races.
- The historical file remains SHA-256
  `5637cbea2d44533db77d7c77051996cd27dad5e1bb16ba483fd5b1ffeb02a71a`.
  The R6 producer and thesis source hashes remain unchanged.
- `git diff --check` and the source claim gate passed.
- Independent native C3 source review returned **SOURCE CONCURRENCE**, with no blocking
  correctness defect in the inspected patch. The reviewer inspected source only; the
  execution claim belongs to the root's retained process receipt.
- A bounded source caller search in engine/scripts/app/tests found only the Section 11
  CLI and its tests using this builder. Other similarly named registration builders are
  unrelated.

Exact source hashes and execution scope are in
[registration-compatibility-r7.json](registration-compatibility-r7.json).
The original R6 verification and its 1251-pass/1-failure result remain historical evidence;
this continuation does not claim that full composed campaign was rerun. The focused suite
covers the changed contract and its immediate producer/thesis dependencies.

## Remaining admission and product gates

A successful historical check does not qualify producer-facts v2, attest historical
executable bytes, run the registered experiment, admit a native correction, or establish
a deployed user path. Future report/run consumers must enforce the current compatibility
guard. Qualification needs either actual execution with the registered historical
implementation and inputs, or a separately admitted new registration and evaluation.

Native owner provenance, independently available current/prior NewsImpact snapshots,
company/security identity, the decision/materialization clock boundary, authenticated
serving, and the server correction/publication watermark remain separate project gates.
Draft/HOLD remains. Current-head hosted CI, applicable source review and current-base
integration remain release requirements. No source merge, runtime activation or
scientific approval follows from this repair.
