# TURN WATCH row-evidence v2 implementation plan

**Goal:** prepare a backward-compatible, explicit input protocol that makes harmless TURN WATCH rebuilds idempotent without weakening immutable history.
**Architecture:** extend the existing producer/intake schema; retain full file evidence and all existing episode/generation machinery; leave v1, registry value and production workflows unchanged.
**Tech stack:** existing Python 3.12, canonical JSON, pandas/Arrow, pytest, GitHub CI manifest.
**Spec:** `docs/superpowers/specs/2026-09-16-turn-watch-row-evidence-v2.md`.

## Frozen sequence

1. Reproduce the real v1 timing-only failure using the current writer, intake, and core; preserve that evidence.
2. Test v2 row semantics, source-file provenance, unchanged-sibling and definition-drift behavior RED, then add the smallest version-aware reader.
3. Test version transition/downgrade/backdating and malformed-envelope refusal; add the explicit existing-builder CLI option with v1 unchanged by default.
4. Exercise the real generation writer only in temporary fixtures. Re-run original accepted production inputs with the real reconciler in report/replay mode and confirm every input/generation byte remains intact.
5. Register the existing intake/reconciler suites in a bounded code-gate job without replacing the existing nightly owner. Run focused tests, forbidden mutations, Agent OS validation, and source contract checks.
6. Publish this single staged candidate for review under HOLD-FOR-SOL; never arm merge-on-green or represent it as registry/production adoption. Once reviewed, the existing V4/integration authority owns explicit new-session cutover and the real publication/browser proof.

Direct work reason: PRINCIPAL_JUDGMENT — the blocker crosses immutable source identity, corrected input provenance, and safe version transition. No worker or peer source custody is transferred. Archive refresh experiments, #7200, #7206, and #7187 are not part of this source change.
