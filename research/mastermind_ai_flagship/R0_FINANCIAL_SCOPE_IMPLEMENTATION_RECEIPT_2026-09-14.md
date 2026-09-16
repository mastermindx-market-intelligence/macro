# R0 financial-analysis scope repair — implementation receipt

Operation: `mastermind-ai-flagship-r0-financial-scope-20260914-sol-001`.
Accountable source writer and acceptance owner: Sol. Parent design: Macro #7151.
Current integration base: `52380b870218b61865fb56458500cac00ce4932b`.
Current Skillpack: Mastermind `7642aea155d2817219135b24246b55c1d7611c66`, v1.0.1/bootstrap1.
State at this source checkpoint: **BUILT_NOT_PROVEN**. No deployment or model-quality claim.

## Capability and bounded change

The existing Brain prompt explicitly admits financial scenarios, investment-thesis
analysis and standard financial arithmetic. Supplied assumptions stay assumptions;
missing values stay missing. Scenario outputs gain no house-signal or trade authority.
Only the SCOPE paragraph changes in production. Providers, quotas, tools, native facts,
quote routing, source readers, signal formulas and the proprietary clause are unchanged.
The `SCOPE — THIS PRODUCT ONLY` heading stays because it is a leak-screen sentinel.
Independent review caught the removed unrelated role-play/framing and short-refusal
clauses; these were restored after two new tests reproduced their absence.
Current main's separate component-vintage versus exchange-session rule is preserved.

All 17 financial-scope cases now reside in the already-registered
`tests/test_brain_gateway.py`. Thirteen function ASTs were compared before and after
relocation and were identical; the same 17 parametrized cases remain executed.
The initial extra CI registration was removed because that existing suite already runs.
`.github/ci/legacy-jobs.yml` is byte-identical to the integration base: no CI-policy
change, skipped test, new job, workflow or runtime was introduced for this prompt repair.
The replay fixture guards assumed arithmetic; it is not a production calculator or
proof of model reasoning. Real-model and user-journey proof remain required.

## Observed proof, chronological and bounded

Original base `878147de1cfbce89768ccf98a140d922ba1a6ce5`, candidate `aaa6f5f2ae3e`:
baseline **430 passed**; new-contract RED **8 failed, 5 passed**; focused GREEN
**443 passed**. Expanded run **839 passed, 3 failed** from omitted sparse data/site
fixtures; canonical materialization, without weakening tests, yielded **842 passed**.
Historical RED SHA256: `fef7bd641dbb748dfefceb39d2bdb53ee0c7e3719260c8015e1b2b94b8b802ef`.
Historical 842-pass SHA256: `00257f36c70e46e904f6d0867533730f54f0310ed53953bd21931c5fb55db1d6`.
The original Skillpack was `51b815ab9527e15c9218b049f622dc4d3e0bfbc4`.

Integration `e57f1d582862105db13a81a4498f67e14cb340a9` incorporates the main-side
glossary banner repair that caused the original CI failure. No glossary code was
rewritten here. Brain/response/stream/instant/quota/glossary selection: **855 passed**.
Independent integrated review then requested restoration of unrelated-scope protection.
New tests before repair: **2 failed, 15 deselected**. After restoration: **17 passed**.
After semantics-preserving test relocation, the following real command returned
**857 passed, 5 existing deprecation warnings**, 42.30 seconds:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3.12 -m pytest \
  tests/test_brain_gateway.py tests/test_response_eval.py tests/test_brain_streaming.py \
  tests/test_brain_instant_lane.py tests/test_brain_gateway_quota_safety.py \
  tests/test_glossary_contract.py -q -p no:cacheprovider
```

Actual runs use a private operation-specific basetemp. Final log:
`/Volumes/Mastermind/agent-evidence/mastermind-ai-flagship-r0-financial-scope-20260914-sol-001/final-regression-20260915.txt`.

## Release and acceptance still owed

Exact-head independent re-review, concluded applicable CI, normal Macro API restart
and real financial-answer before/after acceptance remain owed. The existing
`app/deploy/update.sh` restart predicate already covers `brain_gateway.py`.
Guest browser preflight used an isolated Chromium context and actual production page,
opened the actual widget, and verified Fast/input visibility; it submitted no model
question. Browser infrastructure readiness is not answer-quality acceptance.
A pre-release health read reported process `4ec24e0f47`, checkout `52380b8702`;
this candidate was not released and is not implied by either health field.
The original production refusal remains preserved in #7151. Separate historical
FIN-SCOPE-P2 returned HTTP524 without a run identity, remains backend-effect-unknown,
and was not replayed. No production credentials, subscription or trade state changed.
Next: obtain new exact-head review and concluded CI, release through the existing
path, then test exact P1 and bilingual variants through the real widget/customer path.
