# Evaluation OS and Agent OS: T12 interfaces

The original architecture §7 defines two data contracts. They are available through
existing source owners; neither contract schedules work, prioritises an issue or grants
promotion. Source interfaces and shipped consumer adoption are separate evidence.

## Requirement query

`engine.intelligence_registry.required_tier(registry, changed_paths)` accepts the
canonical derived registry and exact repository-relative producer paths. The existing
`scripts/build_intelligence_registry.py --required-tier PATH` command loads through the
canonical reader and emits the query with its source report; the option is repeatable.

Source-defined display requirements are T1 and gate/size requirements are T3. Unknown
paths, exclusions, inconsistent attribution and authorities without a defined policy
remain unresolved. Partial coverage keeps `required_tier: null`; a known maximum is not
a complete requirement. `evaluation_status: not_assessed` never means tests passed.
This query does not infer transitive dependency impact or certify source freshness.

## Metric-validity finding emission

`engine.qledger_validity.project_research_findings(claims, grades,
reported_metrics=..., registry=..., evidence_link=...)` reuses the existing metric
owner's audit over supplied inputs. The caller must explicitly name the intended metric
set for every claim family. An empty set is a descriptive report. Missing scope is
refused; unsupported metrics and families without claims remain explicit unresolved
entries. Intended-report legality is not evidence that a metric was actually published.

Only two existing invalid findings currently emit six-field issues:

| Owner finding | Metric | Suggested investigation |
|---|---|---|
| `SIGNED_EXCESS_POOLED_ACROSS_DIRECTIONS` | `excess_mean` | T0 metric integrity |
| `HIT_RATE_ON_A_SALIENCE_FAMILY` | `hit_rate` | T0 metric integrity |

Each issue preserves engine, metric, observed change, segment, evidence link and
suggested tier. The observed change is labelled as a snapshot and copies the owner's
detail; it invents no before/after numbers or temporal delta. Exact unique canonical
`qledger:<family>` binding through ledger rule 2 is required. Ambiguous, excluded,
malformed or missing bindings remain unresolved. Off-horizon notes remain unsupported;
they do not become promotion requirements. The caller owns the source identity of the
supplied registry and evidence locator; this pure adapter neither fetches nor verifies
the locator's contents.

A caller that independently supplies normal Discovery admission may pass one issue as
`evaluation_finding` to existing `scripts.agentos.draft_discovery`, or to the existing
`draft-discovery --from` CLI. The drafter preserves it in YAML on stdout; the existing
`check_discovery` validator consumes the typed field. Claims, falsifiers, significance,
verification references, dates, scope and confidence remain caller-authored and
mandatory. A finding does not automatically qualify as a Discovery. Unknown observations
and requirements remain explicit nulls, and numeric zero remains zero. No file, issue,
priority, queue or remote message is created automatically.

The synthetic integration in `tests/test_qledger_validity.py` exercises actual registry
construction, the metric owner, projection, the existing draft, YAML and record
validation with I/O refused. The source interface does not establish empirical T2–T4
findings, actual protected publication, installed behavior or consumer adoption.

## Bounded CLI consumer

`scripts/check_qledger_metric_validity.py --project-findings INPUT.json` is the bounded
caller route for the projection above. It reads one caller-supplied regular JSON file,
`qledger.research_findings_input.v1`, holding exactly `schema`, `claims`, `grades`,
`reported_metrics` (family → metric-name arrays, converted to sets at the boundary),
`registry` (the canonical supplied snapshot) and `evidence_link` (the caller's locator).
It prints `qledger.research_findings_cli.v1`: the input's byte length and SHA-256 plus
the pure owner's unchanged result. `--json` is accepted but redundant; the mode only
speaks JSON.

The mode is a snapshot computation. It never reads the live claim or grade stores,
fetches registry inputs, calls providers, dereferences `evidence_link`, writes a
Discovery, or changes a gate, clock or production state, and it never verifies the
evidence link, scientific validity, rights, or Discovery admission. Incompatible
`--strict`, `--selftest` and explicit `--root` are refused before the input is opened.
The file is bounded at 16 MiB and must be a regular file; missing, unreadable,
oversized, or moving inputs, malformed UTF-8, malformed or duplicate-keyed or
non-finite JSON and wrong schema/shapes exit 2 with a bounded structured error and a
null result — "could not read" is never rendered as a clean projection, a traceback or
echoed input. The payload records the bytes the read saw; the pre/post-read descriptor and pathname
comparisons refuse observed changes or replacement and claim no atomicity. Descriptors
close on every refusal, numeric overflow is refused alongside non-finite constants,
and malformed row identities or duplicate keys cannot leak file content in errors.

Metric scope, the exact unique canonical engine binding and every other semantic stay
with `engine.qledger_validity.project_research_findings`; the CLI mode adds no
scheduler, store, evaluator or authority surface. A caller that independently supplies
normal Discovery admission may still pass one emitted issue to
`scripts.agentos.draft_discovery` exactly as for the pure function; the CLI itself
writes nothing. The synthetic CLI integration in `tests/test_qledger_validity.py`
pins the projection pass-through, the Discovery draft/validator leg, the refusals and
the absence of live-store or registry I/O with local synthetic data only.
