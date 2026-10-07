# Controlled ThemeState owner inputs

These two YAML files preserve the exact configuration bytes retained from the
controlled GMI owner-adapter qualification. They are test fixtures, not current
theme membership, current permissions, a rights grant, or a historical
knowability assertion. No live registry was acquired to create this fixture.

The owning test checks the recorded SHA-256 digests and copies these files only
into pytest's synthetic root. Missing or corrupt fixtures fail without falling
back to repository/live configuration. Real production owner APIs continue to
receive explicit fixture-root paths; no owner/global/cache behavior is patched.
No production publisher or rights resolver consumes this folder.

Run `python -m pytest tests/test_theme_state_owner_adapter.py` from the repository
root. No account-local evidence harness or PYTHONPATH workaround is required.
This is controlled test coverage, never natural-use or production acceptance.
