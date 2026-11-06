# Agreement spec — PRE-REGISTERED statistics for the 600-case benchmark

prompt-v1.0 / agreement-spec-v1 (2026-10-12, lane A6_labeler). Registered before any label
is collected, per freeze §7: two independent labelers from different model families draft
each case's critical fields; disagreement routes to a third labeler of a third family;
residual disagreement goes to a human or the seat and is recorded with its reason. The
thresholds below are registered design choices of this kit (marked where they are this
lane's INFERRED choice rather than a freeze number); they may be amended only by a new
version of this file before labeling starts, never after.

## 1. Unit of analysis and inputs

- Unit: `(case_id, critical_field)` — 12 fields × 1 case per template family, 600 cases,
  7,200 field comparisons per labeling round (600 × 12).
- Inputs: the two labeler returns (`label_return.v1`), each carrying `labeler_family`,
  `model_vintage`, `prompt_version`. A return whose spans fail replay (see
  `span_replay.md`) is excluded whole from agreement statistics and counted in
  `n_returns_failed_replay` — a replay failure is a span defect, not a disagreement.
- Normalisation BEFORE comparison (freeze §7 grading definition — value, unit, basis,
  period and negation all equal after normalisation):
  - numbers: exact equality of the JSON number after scale-word folding already applied at
    labeling (guide §5.1); `150000000000` == `150000000000.0`; unit strings compared
    case-insensitively after trim; `currency` compared exactly (ISO upper).
  - `bound` (exact/approximately/up_to/at_least) must be equal — a hedge difference is a
    disagreement (it is part of the value, freeze §7 "value … equal after normalisation").
  - ranges: equal iff `low` and `high` BOTH match (Gate 4 T2 rule); point vs range is a
    disagreement even when the point equals a bound.
  - period: `{year, quarter, calendar_end, period_kind}` equal component-wise;
    `calendar_end` differences count even when year+kind match.
  - `basis` never compares (slot-fixed by schema const; if two labelers emit different
    bases the schema itself rejects one of them — that is a validation failure, recorded as
    such, not an agreement datum).
  - typed absences: equal iff `reason` equal (subject is fixed by the field; `detail` and
    `missing_fields` are not compared).
  - enum tokens and booleans: exact string/boolean equality.
  - `action_span` / object_name and other free-ish values: equal iff same `form`/value with
    overlapping-identical excerpt? NO — exact: the excerpt strings must be byte-identical;
    a different sentence cited for the same value is a span-choice difference, recorded as
    `span_only_divergence` and NOT counted as a value disagreement, but the case still
    routes to the third family for span confirmation (both spans must replay).

## 2. Statistics (per template, per critical field)

Printed for every one of the 36 (3 templates × 12 fields) rows, even when null:

| Statistic | Definition |
|---|---|
| `n_compared` | cases with two valid replayed returns |
| `n_both_present` | both labelers emitted a present value |
| `n_both_absent` | both emitted typed absences (equal reason counted in agreement) |
| `n_absent_vs_present` | one absent, one present — always a disagreement (Gate 4: wrong_absence / unevidenced) |
| `exact_agreement` | (agreeing fields) / `n_compared` |
| `kappa` | Cohen's κ over the confusion matrix of categorical values, both-present pairs only; `null` when fewer than 2 categories observed or `n_both_present = 0` — printed as `null`, never omitted |
| `kappa_note` | which categories were unobserved (empty string if none) |

Enum (κ-eligible) critical fields: T1 `issuer_role, novelty, action_type,
commitment_status, primary_amount_role`; T2 `issuer_role, demand_stage, metric,
commitment_status, revision_direction, novelty`; T3 `issuer_role, event_kind, novelty,
counterparty_role, economic_claim_class`. κ over both-present pairs only; both-absent pairs
stay in `exact_agreement` and are reported separately in `n_both_absent` (pre-registered:
mixing absences into κ inflates it through the trivial agreement cell).

Also printed at template level (even when zero or null): `n_cases`, `n_accepted_first_pass`,
`n_routed_third_family`, `n_resolved_by_third`, `n_adjudicated`, `n_replays_failed`,
`n_span_only_divergence`, and the Gate 4/§11 endpoints `critical_numeric_correctness`
(target ≥ 98%), `material_routing_recall` (target ≥ 95%; computed only over
adjudicator-assigned `routing_label`, never over labeler output), `unsupported_transfer_yes`
count (target 0; adjudicator-assigned).

## 3. Acceptance, third family, adjudication

- **Accept (freeze §7): a case is accepted iff the two returns agree on EVERY one of its 12
  critical fields** after §1 normalisation, and every span replays. One disagreeing field
  is enough to route the case.
- **Third-family routing:** a disagreeing case goes to a third labeler of a third family
  (requirement: a family different from both drafting families; vendors are a harness
  decision, not named here). The third labeler labels the FULL case (all 12 fields), not
  just the disputed ones — pre-registered to avoid anchoring on the dispute; disputed-field
  resolution is by majority (any two of the three agreeing). Fields the first two agreed on
  are accepted without consulting the third's values for them.
- **Residual disagreement** (all three differ on a field): the seat or a human rules and
  writes one `adjudication_record.v1` per field — `case_id, template, field, values[3]
  (each labeler_family + value + source_span/typed_absence), ruling (first/second/third/
  none_of_the_above/unresolvable_defer), resolved_value, reason, adjudicator`
  (schema: `adjudication_record.v1.schema.json` in this kit). `unresolvable_defer` defers
  the CASE; a deferred case is counted, never silently dropped (masterplan §11 coverage
  accounting).
- Every adjudicated field is stored with `adjudicated: true` on the case row. Adjudicated
  cases are excluded from the auto-accepted set used for the §11 endpoint measurement and
  reported separately.

## 4. Minimum per-template agreement for a usable benchmark

INFERRED (pre-registered here; the freeze sets endpoint targets, not labeler-agreement
floors): the benchmark is USABLE for a template iff, on the first-pass two-family round:

- `exact_agreement` ≥ 0.90 on EVERY critical field of that template, AND
- `kappa` ≥ 0.80 on EVERY κ-eligible critical field with `n_both_present ≥ 20`, AND
- `n_absent_vs_present` ≤ 10% of `n_compared` on every quantity field (an absence-vs-value
  split is the guide failing to say when a slot applies).

Below the floor, for that field/template only:
- the shortcoming is REPORTED (template, field, both rates, example case ids) in the
  agreement report — the report is a deliverable of the labeling round;
- affected cases proceed through third-family + adjudication as in §3 — labels are never
  silently relabeled to manufacture agreement, and the two original returns are kept
  verbatim in the case's provenance;
- if `exact_agreement` < 0.75 on any critical field, labeling PAUSES for that template and
  a defect report is written against the annotation guide (mirroring the Gate 4 budget
  rule: a case needing more than 5:00 is a defect report, not a slower labeler); labeling
  resumes only under an amended guide with a new `prompt_version`.
- Rationale: the §11 endpoint of ≥ 98% critical-numeric correctness is not measurable with
  usable precision if raw two-family agreement on the numeric fields is below ~0.90 — the
  adjudication load would dominate the labeling load and the accepted set would be mostly
  adjudicator-authored. 0.90/0.80 is the pre-registered line where two-family agreement is
  still the primary evidence.
