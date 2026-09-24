# Energy non-regression fixtures

This fixture freezes Nuclear and uranium membership, ThemeState, and Theme Tracker fields.
Regenerate it from a full checkout with:

```bash
MAIN_SHA=$(git rev-parse origin/main)
python3 tests/test_energy_economic_change_non_regression.py --regenerate-baseline "$MAIN_SHA"
```

Regeneration is a seat act only after an intentional accepted change.
