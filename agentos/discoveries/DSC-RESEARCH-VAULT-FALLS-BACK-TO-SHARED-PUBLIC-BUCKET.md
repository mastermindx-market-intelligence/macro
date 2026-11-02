---
key: RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET
claim: >
  engine/research_vault/r2_store.py builds its client from R2_RESEARCH_ENDPOINT /
  R2_RESEARCH_ACCESS_KEY_ID / R2_RESEARCH_SECRET_ACCESS_KEY (+ R2_RESEARCH_BUCKET) and, per
  its own docstring, each FALLS BACK to the shared R2_* variable when unset ("the
  same-account case"). It never refuses a shared bucket. A private-publication run whose
  research secrets are empty or unset therefore publishes into the shared bucket that
  config/r2_delivery_plane_classification.v1.json exposes at public_r2_base
  (pub-…r2.dev), i.e. world-readable, with no error and no log line.
evidence:
  - >-
    engine/research_vault/r2_store.py on origin/main 2026-09-24: docstring lines ~188-189
    ("each falls back to the shared R2_* var when unset") and the three `os.environ.get(
    "R2_RESEARCH_…") or os.environ.get("R2_…")` expressions that follow; `build_store`
    returns None only when endpoint/key/secret are ALL absent from BOTH families.
  - >-
    config/r2_delivery_plane_classification.v1.json: "public_r2_base":
    "https://pub-f7ffb4441c5f4ad983ca56ec7c651c61.r2.dev" (the shared bucket's public domain);
    DSC:RADAR-SPOOL-PUBLIC-R2 proved that bucket world-readable.
  - >-
    #7780 comment 5807772681 (Semiconductor R4 request, 2026-09-24 04:36Z) states as a
    precondition that "build_store() refuses a shared-bucket …" — the code does the opposite.
falsifier: >-
  `env -u R2_RESEARCH_ENDPOINT -u R2_RESEARCH_ACCESS_KEY_ID -u R2_RESEARCH_SECRET_ACCESS_KEY -u R2_RESEARCH_BUCKET R2_ENDPOINT=https://example.invalid R2_ACCESS_KEY_ID=x R2_SECRET_ACCESS_KEY=y R2_BUCKET=shared python3 -c "from engine.research_vault.r2_store import build_store; print(build_store())"` printing `None` or raising — i.e. a build_store() that refuses to construct a client from the shared R2_* family — falsifies this claim; today it prints an R2Store bound to the shared bucket.
so_what: >
  Every private-publication lane (earnings private store, Semiconductor R4 candidate ii,
  Finance finance_intelligence_private/v1) must gate on the research variables being
  present AND different from the shared ones BEFORE the publish step, and must pass ONLY
  the R2_RESEARCH_* variables into the publisher process, or a missing secret silently turns
  a private publish into a public one.
kind: landmine
confidence: verified
verified_at: 2026-09-24
verified_by: >-
  coo-fable — `git show origin/main:engine/research_vault/r2_store.py | sed -n '183,196p'` (docstring 'each falls back to the shared R2_* var when unset' and the three `os.environ.get("R2_RESEARCH_…") or os.environ.get("R2_…")` lines) and `git show origin/main:config/r2_delivery_plane_classification.v1.json | grep public_r2_base`.
scope: [macro]
---

Found by the Finance seat while adopting R4's preconditions for the Finance publish lane
(fin_t6 packet, PRIVACY GATE STEP). Not a Finance-only fact: the earnings private wire and the
Semiconductor R4 plan share the exact same code path. A structural fix (refuse-when-equal in
r2_store or a required `R2_RESEARCH_BUCKET` distinctness assertion) belongs to the Research
Vault owner, not to a sector program; until it lands, the gate lives in each workflow.
