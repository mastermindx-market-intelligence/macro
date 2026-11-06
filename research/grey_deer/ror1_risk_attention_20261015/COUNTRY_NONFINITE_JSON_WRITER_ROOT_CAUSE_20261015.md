# ROR-1 — HK/Canada country regime JSON is nonconformant at its owning serializer

**October 15, 2026 · read-only source diagnosis; no source-owner transfer.** Macro main pin `86db1b0487ec98c955b2ea9265779263c63d6454`.

## Exact invalid source artifact

- `data/hk_regime/latest.json`, Git blob `643d800b0e7af11c51644e315b48ad943ec3d6f1`, contains exactly one non-JSON numeric token: top-level `pending_quad: NaN`.
- `data/canada_regime/latest.json`, blob `7a7986d67b2c93591692093262050055e2105306`, contains exactly one: top-level `pending_quad: NaN`.
- `data/china_regime/latest.json`, blob `ef36a42470f073704a1152582679733e99d4a528`, currently has `pending_quad: "Q2"` and strict-valid JSON, but its writer uses the same vulnerable pattern.

**Origin:** `engine/hk_run.py` blob `9e462744b06d81504e4fa49e8fef84d42f58fe05` at L72 copies `row["pending_quad"]` without normalizing pandas missingness; L121 writes `json.dump(latest, fh, indent=2, default=str)`. `engine/canada_run.py` blob `af76d8e0c76f3056c3f413718e207bce3cb8ec04` at L69/L79 does the same. `engine/china_run.py` blob `37f552a488b98cdc841a0e55e44e30e3d7d40635` at L67/L110 has the same latent handling.

Python's `json.dump(default=str)` does NOT stringify floating NaN: the default `allow_nan=True` emits the bare invalid token `NaN`. The held #8132 `scripts/risk_warning_source_adapter.py::_read` correctly rejects these through `parse_constant=_nonfinite_json`, returning `invalid_json`; ordinary browser `JSON.parse` also rejects them.

## Executed bounded falsifier

On isolated M2 Python, `json.dumps({"pending_quad":float("nan"),"pending_days":0}, default=str)` emitted bare `NaN`; a strict `parse_constant` callback rejected it. A separately normalized sample with `pending_quad=None` serialized to JSON `null` under `allow_nan=False` and round-tripped correctly. A first check was mis-quoted and failed its own assertion; corrected focused check then passed. No native regime engine, publisher, ledger or live data was executed/rewritten.

## Safe source-owner correction criteria

1. Establish the domain-owner representation of no pending quadrant (preserve valid quadrants, express unknown as JSON null rather than a string "NaN" or fabricated quadrant). Validate all nested numeric fields for nonfinite values, not only this currently failing field.
2. Serialize and validate into memory BEFORE touching the last-good destination. Simply enabling `allow_nan=False` **inside** the current `open(...,"w")` stream could raise after truncating the prior valid artifact. Reuse an accepted single-writer atomic publication routine, preserving last-good on any failure. No parallel publisher/store.
3. Focused source-regression acceptance: unknown pending -> null, valid `Q1..Q4` preserved, all bytes strict JSON, failed serialization/write leaves last-good bytes intact, calendar/session/source identity unchanged.
4. Separately resolve the #8132 wrong Radar source path: these country regime files have NO top-level native `risk_radar` field even after null cleanup. Do not create a fake `risk_radar_intl.v1` from the reduced country Market State, weaken JSON parsing, or promote market-level Risk-off to a probabilistic forecast or capital policy.

## Effect boundary

This establishes the HK/CA strict-JSON failure's source-authoring cause, not user-delivery failure's entire root cause or a deployed fix. Original country regime writers, #8132 REQUEST_CHANGES review, Terminal #894 production data owner and all publication holds remain untouched.
