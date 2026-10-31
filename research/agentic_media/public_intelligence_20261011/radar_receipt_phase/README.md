# Press radar receipt fidelity

Root observed exact installed own artifacts at05:54/05:59UTC, with stable HEAD
and unchanged inputs in each bounded read. The probability extractor omitted the
producer target and calibration limits. Application8eb467112b832101385f7256b83036f45ae5d759
repairs only that consumer and its tests; the producer and model are unchanged.

Validation commands:

- `python3 -m pytest tests/test_press_planner.py -q -k radar_receipt`:16failed/1passed before repair.
- `python3 -m pytest tests/test_press_planner.py tests/test_press_research_triage.py tests/test_press_run.py tests/test_press_external_candidate.py tests/test_press_official_feed_candidate.py -q -k 'not test_planner_never_seeds_banned_vocabulary_into_the_prompt_context'`:429passed/1existing sparse-site skip after repair.
- The deselected real-data hygiene test ran unchanged with tests.press_fixtures.REPO bound to the original workspace, not the empty sparse tree. It passed;5input hashes unchanged. See preserved_input_hygiene.txt.
- Existing10/5/9 portable groups and installed_radar_receipt_probe.py7groups all passed locally against reviewed_expected_hashes.json. Wrong-manifest refusal passed before imports.

Fabric review is a source/contract inspection, not reviewer execution. Root
independently ran the tests/probes, matched the reviewed runtime SHA and accepted
the retained result via the original adapter. One subsequent test-only change
updates the legacy JSONL expectation to omit unqualified probability while
retaining state and corrupt-row refusal. See review_binding.json.

The source manifest has24entries; only desk_planner changed. All3page hashes
match prior acceptance. This has no protected follow-on PR or installed proof.
An attempted installed context preflight stopped at missing _reviewed_context;
no source was injected to bypass the unlanded PR9209 gate. The local preflight
result is explicitly prior to this repair and proves date/identity checks only.

Source qualification notes and own-data census are retained alongside the
repair. Raw external reports remain private. Current underlying source clocks,
rights, editorial relevance and the10unedited mixed-desk acceptance remain
separate obligations. Provider/publication writes0;D14credit0/10.
