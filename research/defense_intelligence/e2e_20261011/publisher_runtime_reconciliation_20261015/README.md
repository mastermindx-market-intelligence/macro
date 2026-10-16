# Exact retained publisher history reconciliation

The first natural publisher after PR #9066, run 38826131654 / job 116733909516, stopped before acquisition, build or push with `legacy_runtime_entrypoint_drift`. The native retained archive contains only its pre-effect run case and reconciles as `no_push_identity_no_push_effect`. It is not replayed.

Two older completed SAM refresh jobs used a changed `collectors/base.py`. Their authenticated job records show all four source-guard/build/proof/commit steps completed/skipped. Job-log checkout identities and all five entrypoint fingerprints are retained in the adjacent exact-run records. Four entrypoints match the accepted audit; the attached base diff adds an opt-in Yahoo capture path that the retained collector caller does not enable.

The baseline adds only these exact run/attempt/job dispositions. Original 33 entries, scan floor, whitelist, source closure and all runtime refusal code remain unchanged. This qualifies only the two GovRev publication effects; it does not retire acquisition or unrelated parent effects or assert installation/product acceptance.

Validation: 51 native preflight tests passed. Native baseline parsing and adjacent evidence hashes pass. An offline replay over the retained authenticated readset checked all 44 historical records using 237 retained reads and consumed both new entries without changing any preflight code. This diagnostic replay is not a live checkpoint or a publication permission. The first diagnostic lookup failed on equivalent Z/+00:00 URL encoding; parsed timestamp normalization repaired the offline harness only.

Independent review: original Fabric task `defense-publisher-history-review-01a13300-a`, native root/parent `01a13300-c75b-79c3-83f9-79b3b4c01dc7`, qwen3.8-max / ubuntu0 launched. Desktop restart interrupted the local controller; remote completion remains unconfirmed. Same-run artifact recovery refused `capsule_current_intent_or_delivery_unconfirmed`. No replay, alternate result carrier, replacement worker or approval is claimed. Release of this history amendment remains pending that scoped review.
