# Energy non-regression fixtures

This fixture freezes Nuclear and uranium membership, curated ThemeState and Theme Tracker
identity fields, and the JSON shapes of nightly computed fields.
ThemeState `foresight` is shape-only because
`engine/neuralweb/thematic_state.py:327-338` copies stage, tier, score, entry readiness,
and bottleneck state from `site/basketdata/foresight_cascade.json`; that cascade has been
rewritten repeatedly and changed for 9 of 18 themes across the last 29 regime updates.
ThemeState `narrative` is shape-only because
`engine/neuralweb/thematic_state.py:382-395` derives it from
`site/basketdata/narrative_emergence.json`; it is `null` today only while that reader is
dead. Shapes are stored concretely (`null` included). Comparison follows the nullable law:
a field's live shape must equal its baseline shape, except that a field in
`NULLABLE_SHAPE_FIELDS` tolerates a live `null` (the nightly omitted the block) and a
baseline `null` (a dead reader came back); any other difference is a change.
`frozen_at_main` must be a commit on `origin/main` (the regeneration CLI refuses a lane
merge commit).
Regenerate it from a full checkout with:

```bash
git fetch origin && git checkout --detach origin/main   # HEAD must BE the frozen main commit
python3 scripts/worktree_sparse.py add data site         # full data/ and site/ are required
python3 tests/test_energy_economic_change_non_regression.py --regenerate-baseline "$(git rev-parse HEAD)"
```

Regime updates rewrite ThemeState `radar` and `basket_intel`; Theme Tracker lanes and counts also move about daily. Membership changes only through an intentional curation act. Regeneration is a seat act after an intentional accepted change.
