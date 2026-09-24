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
dead. Nullable shape fields accept a live `null`; a baseline `null` accepts a live value
only for the fields declared by `NULLABLE_SHAPE_FIELDS` in the test.
Regenerate it from a full checkout with:

```bash
MAIN_SHA=$(git rev-parse origin/main)
python3 tests/test_energy_economic_change_non_regression.py --regenerate-baseline "$MAIN_SHA"
```

Regime updates rewrite ThemeState `radar` and `basket_intel`; Theme Tracker lanes and counts also move about daily. Membership changes only through an intentional curation act. Regeneration is a seat act after an intentional accepted change.
