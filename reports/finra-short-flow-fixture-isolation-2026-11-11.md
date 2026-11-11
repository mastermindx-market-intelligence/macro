# FINRA fixture status isolation — native red/green proof

## Result and source scope

The inherited fixture redirected Parquet data with `config.data_dir`, but `run_adapter` independently resolves circuit-breaker status reads and stale-series writes through `config.ROOT / config.load()["storage"]["run_status_file"]`. The owner command therefore passed its assertions while dirtying tracked `data/run_status.json` and exiting with a data-guard failure.

This change copies the fixture configuration, redirects its status-file path into `tmp_path`, and asserts that the real status writer emits the FINRA stale-series entry there. Production code, breaker, stale detector, pytest guard, CI catalog and existing composed consumer changes are preserved.

Source: composed PR #11061 at `a4ab113a6478c7ec7bcfd03c8ede1493fc5c61a2`; original test blob `10e86b86632bf7563afeebd89989e5c845f0fac2`; adapter base blob `a958ac264aec6a49b9b971ea103f8c83e29dc6e3`.

## Original terminal failure

Donor [#11072](https://github.com/mastermindx-market-intelligence/macro/pull/11072), H `45ca874522907687393960e33222ac4e88cd614b`, original run [43091844204](https://github.com/mastermindx-market-intelligence/macro/actions/runs/43091844204) attempt 1 completed with failure. Canonical artifact `13892948090` binds evidence SHA-256 `f7615289cc88be0a00de778e4136c4bc5f142a915fdbd6215109ba0fb5d7e8a7`.

Candidate C19 job `130772511323` passed 106 tests but exited 1 because `MM_DATA_GUARD` detected `M data/run_status.json`. Its separate exact-base replay does not establish candidate acceptance. The independent design job `130772511421` failed before candidate evaluation with unresolved Git deltas and invalid index-pack output. This does not prove a FINRA design violation. The following visual step was `not_run_prior_failure`; no visual execution or acceptance is claimed. No donor run was replayed.

## Discriminating native proof

The exact composed-owner command ran under `MM_DATA_GUARD=1` in two isolated Git repositories, each with a clean tracked synthetic `data/run_status.json` sentinel:

```sh
python -m pytest tests/test_c19_wp24_consumer_states.py tests/test_short_volume.py -q -p no:cacheprovider
```

| Version | Assertions | Process exit | Tracked status |
|---|---:|---:|---|
| Original composed test | 123 passed in 3.45s | 1 | Modified; guard detected the write |
| Fixture-isolated test | 123 passed in 2.60s | 0 | Byte-identical; no watched changes |

The 123 cases are this exact two-suite owner command. They are not the donor's older 106 cases or the separate prior 133-case consumer proof.

All 399 source/support blobs were qualified against the composed head. The initial isolated closure lacked `collectors.finra`; ten missing static dependencies were fetched from the same head before both final executions. Both versions then ran against the same complete source set. No production data writes or provider requests occurred.

Preserved status SHA-256: `c26a00657b1015e1f9ceb03a36877a0e475b252de186f59e9c55558c19a07c0a`. Original log SHA-256: `3d42ad04a237b8da2d5fa9d150d23650e91d4259943e936f4b61652d90f11c06`. Candidate log SHA-256: `f07d1d1dffbbd0b09e637b44844fbc8b1d37f760f4ff9b1c090fcdc5e9b33ce9`.

## Exact diff

```diff
--- a/tests/test_short_volume.py
+++ b/tests/test_short_volume.py
@@ -329,6 +329,15 @@
 
 
 def _fixture_adapter(tmp_path, monkeypatch, responses, universe=None):
+    # run_adapter reads breaker state and writes stale-series health through
+    # run_status_file, independently of data_dir. Keep the real status reader
+    # and writer inside this fixture as well as the Parquet data.
+    fixture_cfg = dict(config.load())
+    fixture_cfg["storage"] = {
+        **fixture_cfg["storage"],
+        "run_status_file": str(tmp_path / "run_status.json"),
+    }
+    monkeypatch.setattr(config, "load", lambda: fixture_cfg)
     monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
     monkeypatch.setattr(fsv, "_universe_tickers", lambda: {"AAA"} if universe is None else universe)
     wanted = [date.fromisoformat(day) for day in responses]
@@ -397,6 +406,8 @@
     responses = {"2024-01-17": _daily(("AAA", "50", "100"))}
     adapter = _fixture_adapter(tmp_path, monkeypatch, responses)
     assert run_adapter(adapter).status in {"ok", "stale"}
+    status = json.loads((tmp_path / "run_status.json").read_text())
+    assert any(row["group"] == fsv.GROUP for row in status["stale_series"])
     assert not fsv._superseded_path().exists()
     responses["2024-01-17"] = _daily(("AAA", "60", "100"))
     assert run_adapter(adapter).status in {"ok", "stale"}
```

## Remaining acceptance and live-effect fence

The original composed run [43099668292](https://github.com/mastermindx-market-intelligence/macro/actions/runs/43099668292) was still live when this proof was prepared. The repair can be saved as a commit against the exact composed head; the branch must remain unchanged until the original run settles and its outcome is reconciled. This proof does not claim hosted CI for the new commit, full-page browser acceptance, production acceptance, approval or release.

Prior native consumer and 171,946-row data proof is retained without repeating it for a fixture-only change. PR #11061 remains the same owned carrier, Draft and unarmed pending original consumer acceptance. The JSON companion contains the complete input manifest, driver, logs, exact diff and native receipts.
