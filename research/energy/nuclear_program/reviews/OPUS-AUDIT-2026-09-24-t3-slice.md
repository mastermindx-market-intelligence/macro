# Opus READ_ONLY audit — Energy W1 T3 slice (shared `economic_change_dossier.v1` + Energy adapter)

Audited artifact: lane PR #7898 head as cherry-picked on carrier #7881 at `9e0552caf025` (files: schema, `engine/market_ontology/energy_economic_change.py`, its test module, CI job `energy-economic-change-dossier`, CURATED_EXCLUSIVE entry). Reviewer: Opus `reviewer` agent, MODE READ_ONLY, 2026-09-24 ~07:20–08:35Z. Suite at audit time: 67 passed (exit 0). Verdict: **REJECT** — 12 BLOCKING, 15 NIT. Seat disposition: all 12 accepted; auditor NIT N1 promoted to BLOCKING (B13) under semantic 12; repair packet `research/…/packets` mirrored on #7898 (issuecomment-5809841301); repair lane `ene_w1_t3_repair` (glm-5.3, rounds 2) dispatched.

| # | Finding (short) | Law breached | Seat disposition |
|---|---|---|---|
| B1 | Registered-vocabulary check is fake (one literal blocked; `$defs.vocabularies` never `$ref`'d; milestone vocab/flag free strings) | §4 vocabularies validated | fix + tests |
| B2 | Rights rule inverted/unreachable in schema (restricted change with a value validates) | §4 rights_state | fix + test |
| B3 | Subject `security_link_allowed` if/then missing | §4 subject | fix + test |
| B4 | BOUNDS enforced for subjects only | §5 OVERSIZE_SELECTION | fix + 4 tests |
| B5 | Bridge steps bypass the law table (unresolved/foreign/definition-less refs become observed) | profit ≠ common-shareholder cash | fix + 4 tests |
| B6 | Milestone evidence, comparisons, steps read raw inputs (post-cutoff / restricted leakage, wrong codes) | knowledge-cutoff, rights | fix + tests |
| B7 | Nested-set rule unimplemented beyond direct parent+child | contingent backlog ≠ funded revenue | fix + 3 tests |
| B8 | Only `establishes_current_operation` guarded | milestone ≠ operation | fix + test |
| B9 | Restricted role exposure / counterevidence narrative leak | rights_state → nulled | fix + 2 tests |
| B10 | `date-time` format never checked (no rfc3339-validator); string-prefix clock compare | clocks | pip extra + fromisoformat + tests |
| B11 | Output not bound to the selection; missing subjects raise instead of typed state | §5 selection law | fix + tests |
| B12 | Wrong exception types (TypeError) | §5 typed EnergyProfileError | fix + 3 tests |
| B13 | (N1) none/unknown/absent membership receipt leaves `primary_member=true` | supplemental never primary | fix + test |
| N2–N15 | order dependence, fake order test, refused-path counts, comparison status rule, misnested label guard, wrong codes, schema loaded per call, hash omits profile/mode, tz-offset cutoff, no-op allOf, cwd-relative test path, CURATED_EXCLUSIVE comment, `__init__` closure | — | fix in the same pass |

Semantics pinned at audit time: 3 (backlog), 4 partial (milestone), 6 partial (equity vs consolidated), 10 indirect, 12 (supplemental) — the other seven UNPINNED; the repair packet requires a test per item.
