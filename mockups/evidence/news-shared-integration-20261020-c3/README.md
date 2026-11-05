# Shared ticker-news component visual evidence

This is an anonymous, fictional component preview. The fixture freezes English and Chinese DOM produced by the actual news consumer and existing API fixtures. The canonical browser capture loads the actual shared theme and component stylesheet from this checkout. The capture page contains no auth client, credential, API request, or live news runtime.

The canonical capture contains eight rest cells (desktop/mobile, English/Chinese, dark/light), plus actual link hover, button hover and button focus in every cell: 32 successful captures. These screenshots prove component presentation, including different-report attribution, within the stated fixture scope. They do not prove authenticated deployment, the complete generated stock page, provider ingestion or production latency. Dynamic filtering, access loss, ticker replacement and stream behavior are covered separately by the UI and real-SSE verification artifacts.

`fixture-provenance.json` binds the rendered fixture to the actual source hashes and records its scope. `manifest.json` was emitted by the unchanged canonical capture tool; `EVIDENCE.yml` only declares ownership of the two component CSS paths.

To rebuild the fixture, run `python3 mockups/evidence/news-shared-integration-20261020-c3/prepare_fixture.py` from this checkout. Then use `scripts/capture_page_evidence.py` with `--site-dir .`, this fixture route, both viewports, locales and themes, and the three force-state definitions recorded in the manifest. No production credentials are required.
