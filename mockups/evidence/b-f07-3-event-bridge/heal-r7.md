# Heal g_7134_r7 — 2026-09-19

Executor: Grok on the Studio. Round-6 head `c2531491` left three CI reds.

Crops were not recaptured. The 24 PNGs remain the CODE_HEAD `f374431c` capture.
`recapture: NEEDED` only if a later seat asks to restamp hosts after a template
change; this round did not change the template bytes.

## Finding (A) — eager `requests` on the pack-4 venv

Job `conviction-profile` installs `pytest pandas numpy markupsafe jinja2 pyyaml jsonschema`
(no `requests`). RED at `c2531491` (Python 3.12.13, that venv):

```
FAILED tests/test_valuation_event_bridge.py::test_controls_blob_no_collector_import_at_call_time
tests/test_valuation_event_bridge.py:559: compiler = import_module("scripts.compile_capital_structure_events")
scripts/compile_capital_structure_events.py:32: from collectors.sec_capital_structure import FORM_POLICY, file_number_provenance_errors
collectors/sec_capital_structure.py:31: import requests
E   ModuleNotFoundError: No module named 'requests'
```

Same traceback for `test_controls_blob_reads_validated_capital_spine` and the two
production-path tests. `test_federal_register_policy_events_are_not_issuer_filings`
failed at `from collectors.federal_register import _STAGE_WEIGHTS` → `import requests`.

Fix: `FORM_POLICY` / `file_number_provenance_errors` load only inside compiler
functions that need them. Tests no longer import the compiler or
`collectors.federal_register`. The production path stays on
`engine.capital_structure.event_versions_io` / `spine_paths`.

GREEN: `/tmp/venv_noreq_7134/bin/python -m pytest tests/test_valuation_event_bridge.py -q`
→ **31 passed**.

## Finding (B) — pop then monkeypatch poisons later tests

RED at `c2531491`:

```
FAILED tests/test_no_module_leak.py::test_no_test_pops_a_sys_modules_key_then_monkeypatches_it
AssertionError: these tests drop a sys.modules key AND monkeypatch the same mapping
in one function … assert not ['tests/test_valuation_event_bridge.py:641 in
test_controls_blob_no_collector_import_at_call_time()']
```

Fix: delete the three `sys.modules.pop(...)` lines. The test now uses only
`monkeypatch.setitem(sys.modules, key, None)` so undo restores the original entry.

GREEN: `python3.12 -m pytest tests/test_no_module_leak.py tests/test_valuation_event_bridge.py tests/test_valuation_assumptions.py -q`
→ **64 passed**.

## Finding (C) — EVIDENCE.yml extra keys

RED at `c2531491`:

```
mockups/evidence/b-f07-3-event-bridge/EVIDENCE.yml: receipt carries unexpected key(s)
['capture', 'captured_at', 'captured_cells', 'matrix', 'note', 'resolved_sha_or_none',
'smells', 'smells_md', 'state', 'subject'] — only ['changed_paths', 'manifest', 'schema']
are permitted (a receipt maps changed paths to an existing manifest)
```

Moved that prose here. The receipt is the 3-key form:

- `schema: mastermind.page_evidence_receipt.v1`
- `changed_paths: [templates/_valuation_assumptions.html.j2]`
- `manifest: mockups/evidence/b-f07-3-event-bridge/manifest.json`

The packet manifest is now `mastermind.p0_evidence.v2` with three host pages and
the 24 rest cells, sha256/bytes/pixel dimensions taken from the committed PNGs.
No new screenshots.

Capture note (from the old receipt): hosts were regenerated from the live template
and shared theme.css at CODE_HEAD. Chromium captured `#va-event-bridge`
sequentially at 1440×900 and 390×844, with a 200 ms settle after each
theme/language change. Shared stylesheet supplies both themes. No full e2e suite
was run. Matrix: 24 cells = tender-offer / restructuring / null × dark/light ×
EN/ZH × desktop 1440 / mobile 390. Subject: B-F07-3 valuation panel
event-to-assumption bridge line. State: Tender Offers, Restructuring, and no
classified filing.

GREEN: design-governance unit suites **173 passed**;
`check_design_system.py --mode enforce-added` blocking=0;
`check_ui_visual_evidence.py --diff-file` exit 0.

## pyarrow on the conviction-profile install line

The committed spine is parquet. pandas 3.0.6 cannot read it without pyarrow.
The job already ran these tests; without pyarrow the production-path tests
would fail next on `Unable to find a usable engine`. pyarrow was added to that
install line only. `requests` was not added.
