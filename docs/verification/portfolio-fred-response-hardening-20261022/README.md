# FRED daily response hardening

The latest observed daily execution failed its first three FRED series while decoding response JSON, stopped before DGS3MO, and retained cached data. The source response itself was not retained, so neither an upstream outage nor a specific HTTP/body cause is established.

The daily API path now applies one configured attempt budget across HTTP and JSON decoding, with the existing exponential backoff. Malformed-JSON diagnostics contain only bounded status/media classifications, body length and attempt counters. They never echo response bodies, URLs, query parameters, raw headers or API keys. Valid JSON with the wrong schema and programming exceptions are not retried. Daily partial/total failure summaries use the existing exception redactor, and the three-series fail-fast message no longer guesses that the endpoint is down.

CSV and vintage fetch paths, the shared HTTP helper, collector configuration, storage, series selection and cache retention behavior are unchanged. This repair does not prove the provider is currently healthy or that DGS3MO history is current.

## Proof

All fixtures use synthetic responses and canary strings with network access blocked. Any key-like values in regression logs are test canaries.

- Red against unchanged source on base af0ba2d50a32c7a422508b442f35010dcdf154a2: 15 failed, 5 passed, 8 deselected. All 20 selected new cases executed. Nine warnings concern pytest cleanup of unrelated pre-existing shared temporary directories; no collection error occurred.
- Green: 41 passed across tests/test_collect_failfast.py, tests/test_circuit_breaker_recovery.py and tests/test_fred_vintages.py in 3.30 pytest seconds (4.173 seconds for the wrapper), with no warnings. An owned basetemp avoided unrelated shared-temp cleanup.
- Configured budget and backoff: four total transport/decoding attempts, waits 3/6/12 seconds under the synthetic test configuration; failures never create nested retry budgets.
- Coverage includes decode recovery/exhaustion, mixed transport/decoding failures, HTTP-status failures, safe media classification, schema/programming error behavior, the three-series stop and recovery, and partial/total log redaction.
- Ruff is unavailable in the native environment; no lint pass is claimed.
- The existing CI manifest already selects test_collect_failfast.py. No manifest or packing ceilings were changed.

The raw logs are deterministically gzip-compressed. The JSON receipts retain exact commands, interpreter, times, return codes and source/test hashes. These local results precede a commit and bind the dirty source blobs by SHA-256; they do not claim hosted CI or production acceptance.

Independent review and protected CI/release state are recorded on the resulting PR. Files in this packet do not contain live provider responses or production credentials.
