# K1 / K3-E source audit — parent adjudication

**Scope:** bounded read-only source audit supporting the Alpha integration planning assignment. **Verdict:** accepted as a qualified research return, with the corrections and limits below. This is not acceptance of the Alpha product, current production, this documentation PR, or an implementation repair.

## Exact identity and consumed return

- Original attended root and immediate parent: `alpha-intelligence-masterplan-20261031-sol-001`.
- Child: `alpha-k1-k3e-source-audit-20261031-r1`; controller PID `79726`.
- Audited Macro source: `1c85878983323f9ab38fff56a15771166d0f8aeb`.
- Final status: terminal, rc 0, root verified, result available, original controller return recorded.
- Complete adapter response: **11,915 bytes**, SHA-256 `16bded6f634f47a4b7ed428f11c56504d0b37d2a5e3b3dc19b446b7f775b53d5`.
- [Exact as-received report](receipts/ALPHA_K1_K3E_FABRIC_RETURN_2026-10-31.md). Its bytes and digest were verified after retention.
- Acceptance receipt: `accepted:true`, `accepted_by:reviewer`, `verification_summary:manual_result_review`, same exact response digest. The backend explicitly labels this a legacy acceptance, not an atomic cryptographic artifact attestation.
- Dialogue: terminal child; no temporary watcher or independent next wave is authorized by this acceptance. No background parent wake is claimed.

The first acceptance call was rejected before acceptance because a prose verification summary was supplied where the backend requires a fixed evidence-basis code. A second was rejected because its requested response ceiling was below the already-known response size. After reading the pinned schema and correcting those arguments, the same-run acceptance succeeded. No worker replay, provider switch or new operation occurred.

## Test results as reported by the worker

The worker extracted pinned source into an isolated scratch tree and reported this command shape:

```bash
python3 -m pytest <named suites> -q --basetemp=/tmp/k1audit/tpfinal -p no:cacheprovider
```

| Existing suite | Reported result |
|---|---:|
| `test_evidence_foundation_contract.py` | 96 passed, 1 checkout-environment failure |
| `test_evidence_foundation_product_contract.py` | 34 passed |
| `test_opportunity_evidence_vector_contract.py` | 128 passed, 1 checkout-environment failure |
| `test_price_pressure_research.py` | 79 passed |
| `test_earnings_opportunity_qualification.py` | 44 passed |
| `test_earnings_opportunity_context.py` | 26 passed |
| `test_security_state_contract.py` | 94 passed |
| `test_security_state_view_model.py` | 102 passed |
| **Aggregate in the worker report** | **604 passed, 2 failed**, reported duration 36.92 seconds |
| **Sum of the listed suite rows** | **603 passed, 2 failed**; one-pass discrepancy in the worker report |

The two failures invoke checkout-local `git diff origin/main...HEAD` and `git ls-files` assumptions that are unavailable in the extracted scratch tree. The worker separately inspected tracked paths at the exact pin, while explicitly leaving untracked/working-tree dimensions unproven. The parent did not rerun these eight suites or inspect raw per-test logs beyond the retained report. The listed pass counts sum to 603, while the aggregate says 604; that one-pass discrepancy is unresolved and the exact aggregate is not adopted. Preserve these as reported focused results with two environment-dependent failures, not full CI, 606 passing tests or an independently reconciled pass total.

## Parent-verified finding: invalid clocks raise instead of returning findings

The parent independently acquired the pinned module, vector schema, slot registry and existing `golden_imxi_drl_event.json` fixture. The untouched golden returned an empty findings list. Two separately rehashed mutations reproduced the report's exceptions:

```json
{
  "baseline_findings": [],
  "naive_aware_probe": {
    "construct": "options_state",
    "exception_type": "TypeError",
    "message": "can't compare offset-naive and offset-aware datetimes"
  },
  "non_string_probe": {
    "construct": "drl_resid_shock",
    "exception_type": "TypeError",
    "message": "'int' object is not subscriptable"
  },
  "owner_count": 14,
  "security_subject_owners": []
}
```

Reproduction against an existing exact-pin checkout, without writes to repository source or data:

```python
import copy
import json
from pathlib import Path
from lib import opportunity_evidence as oe

base = json.loads(Path(
    "tests/fixtures/opportunity_evidence/golden_imxi_drl_event.json"
).read_text())
assert oe.validate_vector(base) == []

naive = copy.deepcopy(base)
slot = next(s for s in naive["slots"] if s["included_in_composition"])
slot["known_at"].update(value="2026-01-01T08:00:00", grain="datetime")
naive["asof"].update(value="2026-01-02T09:00:00Z", grain="datetime")
naive["content_sha256"] = oe.compute_content_sha256(naive)
# Current pin raises TypeError; the contract requires findings for invalid input.
oe.validate_vector(naive)

# Run this second witness separately after recording the first exception.
non_string = copy.deepcopy(base)
registry = oe.load_slot_registry()
slot = next(s for s in non_string["slots"]
            if registry["constructs"].get(s["construct"], {}).get("clock_distinct"))
slot["asof"]["state"] = "known"
slot["known_at"].update(state="known", value=42)
non_string["content_sha256"] = oe.compute_content_sha256(non_string)
oe.validate_vector(non_string)
```

The relevant current source is `_check_clocks`, `_compare_known_at_to_asof` and `_check_lookahead`. The documented validator surface says invalid inputs produce findings. The parent also inspected `OpportunityCase`'s `TypeError` catch and the ontology route. This is a bounded robustness defect; valid producer clocks and financial authority were not demonstrated to fail. Repairing the validator does not alone establish a different HTTP or UI error. That caller behavior needs its own discriminating check.

## Report claims adopted, narrowed or rejected

| Worker claim | Parent disposition |
|---|---|
| Real consumer paths are broader than the initial five-file packet. | Adopt as useful navigation, with pinned source confirmation for the main composer/consumer seams. Security-state and institutional readers are additional existing adoption points. A route in source is not fresh production proof. |
| K1/current case joining is limited by native subject proof. | Adopt the demonstrated AAPL refusal and the absence of security/listing/issuer subject admission in the inspected current vocabulary. Preserve the narrow native DRL/earnings paths. Avoid the blanket phrase “all multi-owner composition is dead”; evaluate each intended grain/consumer. |
| Vocabulary contains 15 owner stores. | **Rejected.** Parent parsed the exact current vocabulary: **14**, including the later price-pressure entry. Historical original K1 prose referred to 13. |
| Aggregate reports604 passes while the eight listed suites sum to603. | **Aggregate not adopted.** Preserve both as received and the unresolved one-pass discrepancy; no additional worker or full test rerun is justified solely to improve a planning document's headline count. |
| Both malformed-clock exception paths violate the validator's findings-only behavior. | **Independently reproduced** by the parent with a clean valid baseline. Add a bounded repair packet, not an uncommissioned source change. |
| Clock/missingness/authority protections are present in the inspected code. | Adopt within inspected scope and the worker-reported focused tests. This does not establish all runtime input authenticity or production behavior. |
| Correction/withdrawal relations are implemented, but richer user correction traversal is incomplete. | Treat as a consumer-specific design/proof question. Do not infer that no native owner has correction history merely because the case composer has no store. |
| Rights are unknown everywhere / no case can be rights-clean. | **Narrowed.** Selected producer metadata retains unknown/unasserted scope. This does not override the accepted October23 commercial-rights attestation or establish a universal provider-rights blocker. Product metadata, use permission and historical suitability remain distinct. |
| A validator fix converts an opaque503 into a typed refusal. | **Not established as a product effect.** The parent confirmed caller catches, but the actual route/UI response must be tested; changing one validator does not prove new delivery behavior. |
| The historical freeze's “no consumer armed” header is stale relative to integrated source. | Treat the freeze as dated acceptance scope; later source/consumer receipts supply the current fact. Do not rewrite historical evidence as though the consumer existed at the original freeze. |
| Performance and private-parser coupling deserve attention. | Retain as possible follow-ups if a real consumer/profile demonstrates need. The reported README fixture timing is historical, not a performance benchmark run here. |

## Explicit deviations and evidence limits

The worker did not open the Mastermind protected-procedure repository and claimed no audit of that law. The parent had already loaded and applied the exact protected pin; this report is accepted for source/test observations only, not policy-compliance attestation.

The worker disclosed that an initial read probe against another local Macro checkout triggered Git auto-garbage-collection. It reported local packing, no network and no source edits, and left packing to finish rather than terminating it. This is a disclosed execution deviation from an ideally side-effect-free source read; no source or cleanup authority is inferred from it. The return does not establish the eventual process state beyond that disclosure. No child workers, site/data builds, live captures, outcome-label reads or source publication were reported.

## Result for Fable

Use the accepted existing infrastructure and current consumer map. Add the two invalid-clock witnesses to the first relevant K3-E repair, preserving valid-output and authority semantics. Keep the broader identity/manager/evaluation obligations explicit. This audit materially improves the planning packet; it does not complete the programme or replace qualified source-release review.
