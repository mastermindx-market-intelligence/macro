# Energy non-regression fixtures

This fixture freezes Nuclear and uranium membership, ThemeState, and Theme Tracker fields.
Regenerate it from a full checkout with:

```bash
MAIN_SHA=$(git rev-parse origin/main)
python3 tests/test_energy_economic_change_non_regression.py --regenerate-baseline "$MAIN_SHA"
```

Regime updates rewrite ThemeState `radar` and `basket_intel`; Theme Tracker lanes and counts also move about daily. Membership changes only through an intentional curation act. Regeneration is a seat act after an intentional accepted change.
