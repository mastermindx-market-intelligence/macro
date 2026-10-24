# USDA WASDE source admission and consumer proof

The original October 9, 2026 USDA report is now in the **private canonical Research
inbox**, with both conditional creates and exact readbacks proven at 13:37 UTC.
This package is not an accepted Press article, stock story or public capability.

- `qualification.json`: original source/policy URLs, source and sidecar hashes,
  the parent's scoped rights/fact decision, and the independent worker refusal.
- `verify_usda_local_intake.py`, `local_acceptance.json`, `refusal_controls.json`:
  19 actual-PDF checks and two refusal controls, entirely in local fixtures.
- `submission*.json*`: exact paired-write intent, timestamps and readbacks.
  The successful effect must not be replayed. Raw PDF/transport payload stay private.
- `inspect_usda_consumption.py`: read-only post-ingest acceptance. Six local
  controls are in `consumer_probe_controls.json`; installed13:40 result is pending.

After the incumbent hourly ingester publishes, run the inspection over the existing
SSH transport with `/opt/macro/.venv/bin/python -B - /opt/macro`. It verifies source
receipt/digest, catalog/date/summary, promoted PDF and stored fulltext using the
installed reader. It does not extract on the VPS, invoke a provider or write data.
Then verify exact committed/installed catalog and the real public Research URL.
The planner's isolated local selection is not proof of live source selection.

The PDF is bound to SHA256
`6cc97c08be7e683b6114ae8e16d49fce2f21dce3ed3f9933b0acbd2d37e6840b`.
The six-point sidecar is bound to SHA256
`1a215b20c74538f8532757ce2ee043b5784a3e6573e857a8d51eeca8ffd2c80e`.
Dates and forecast qualifications must remain intact; no stock ticker was assigned.
