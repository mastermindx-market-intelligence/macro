#!/usr/bin/env python3
"""Independent real-Parquet acceptance; all writes restricted to review /tmp."""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import argparse
import json
import math
import platform
import socket
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from review_support import NATIVE_BUNDLE, capture, hash_file, load_native, load_subject, read


def normalize(value):
    """Review-owned conversion of persisted null/list/scalar representations."""
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(v) for v in value]
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
        return normalize(value.tolist())
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def no_network(*args, **kwargs):
    raise RuntimeError("Network disabled during independent native-Parquet acceptance")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert any(p.name.startswith("mmx-cn-integration-repair-acceptance-") for p in (out, *out.parents)), out
    assert Path("/tmp").resolve() in out.parents, out
    out.mkdir(parents=True, exist_ok=True)
    files_dir = out / "parquet_cases"
    files_dir.mkdir(exist_ok=True)
    fixture = read(args.fixture)
    expected = fixture["review_binding"]["candidate_inputs_sha256"]
    actual = {"contract_prototype.py": hash_file(args.subject),
              "pinned_quote_adapter.py": hash_file(args.adapter)}
    assert actual == expected
    assert hash_file(args.bundle) == NATIVE_BUNDLE == fixture["review_binding"]["native_bundle_sha256"]
    B = load_subject(args.subject)
    modules, native_ids = load_native(args.bundle)
    R2 = modules["engine/prophet_live/r2io.py"]
    CR = modules["engine/prophet_live/cn_reconcile.py"]
    clock = modules["engine/prophet_live/cn_clock.py"]
    calendar = modules["lib/cn_calendar.py"]
    LS = modules["engine/prophet_live/live_states.py"]
    RD = modules["scripts/reconcile_cn_live.py"]
    resolver = B.SyntheticQuoteResolver(args.adapter.read_bytes())
    assert resolver.contract_id == fixture["quote_contract_id"]
    import pandas as pd
    pd.io.parquet.get_engine("auto")
    now = datetime.fromisoformat(fixture["settled_at"])

    def new_store(repeat=False, fractional=False):
        store = B.MemoryR2(page_size=2)
        if fractional:
            doc = fixture["fractional_envelope"]
            store.put(B.spool_key(doc, R2), doc)
        else:
            for key, doc in fixture["events"].items():
                store.put(key, doc)
        for name in ("base_pack", "settlement_pack"):
            pack = fixture[name]
            store.put(B.pack_key(pack, R2), pack)
        store.put(R2.CN_PACK_KEY, fixture["settlement_pack"])
        if repeat:
            doc = fixture["repeat_envelope"]
            store.put(B.spool_key(doc, R2), doc)
        return store

    def ingest(existing, repeat=False, fractional=False):
        return B.consume(new_store(repeat, fractional), R2, CR, clock, calendar, LS,
                         session=fixture["session"], now=now, existing=existing,
                         settlement_pack=fixture["settlement_pack"],
                         canonical_board=fixture["canonical_board"],
                         canonical_board_raw=fixture["canonical_board_utf8"].encode(),
                         quote_resolver=resolver)

    baseline = fixture["ledger"]
    rows, _ = ingest([])
    assert normalize(rows) == normalize(baseline)
    positive_calls = []

    def native_writer(path, rows):
        assert out in path.resolve().parents
        positive_calls.append({"path": str(path.relative_to(out)), "rows": len(rows)})
        RD._write_parquet(path, rows)

    positive_path = files_dir / "positive_roundtrip.parquet"
    # Missing file -> first native commit -> actual pandas read -> native replay.
    if positive_path.exists():
        positive_path.unlink()
    first_rows, _ = B.reconcile_file(positive_path, read_frame=pd.read_parquet,
                                     write_rows=native_writer, reconcile=ingest)
    second_rows, _ = B.reconcile_file(positive_path, read_frame=pd.read_parquet,
                                      write_rows=native_writer, reconcile=ingest)
    disk_rows = normalize(pd.read_parquet(positive_path).to_dict(orient="records"))
    assert normalize(first_rows) == normalize(second_rows) == disk_rows == normalize(baseline)

    # Older noncolliding native rows must survive a mixed-schema Parquet file
    # without gaining event or source provenance merely because columns exist.
    legacy_path = files_dir / "legacy_roundtrip.parquet"
    pd.DataFrame([fixture["legacy_row"], *deepcopy(baseline)]).to_parquet(legacy_path, index=False)
    legacy_before = next(row for row in normalize(pd.read_parquet(legacy_path).to_dict(orient="records"))
                         if row["date"] == fixture["legacy_row"]["date"])
    legacy_result, _ = B.reconcile_file(legacy_path, read_frame=pd.read_parquet,
                                       write_rows=native_writer, reconcile=ingest)
    legacy_after = next(row for row in normalize(pd.read_parquet(legacy_path).to_dict(orient="records"))
                        if row["date"] == fixture["legacy_row"]["date"])
    assert legacy_before == legacy_after
    assert legacy_after.get("ingest_contract") is None and legacy_after.get("first_event_id") is None
    assert legacy_after.get("quote_payload_sha256") is None

    # Real native repeat event generated independently via dark -> forming.
    repeat_path = files_dir / "later_repeat.parquet"
    pd.DataFrame(baseline).to_parquet(repeat_path, index=False)
    repeat_rows, _ = B.reconcile_file(repeat_path, read_frame=pd.read_parquet,
                                      write_rows=native_writer,
                                      reconcile=lambda old: ingest(old, repeat=True))
    target = next(row for row in normalize(repeat_rows)
                  if row["ticker"] == "002460.SZ" and row["kind"] == "forming")
    original = next(row for row in baseline if row["ticker"] == "002460.SZ" and row["kind"] == "forming")
    immutable = ("first_ts", "first_px", "first_event_id", "first_pack_id", "first_observation_sha256",
                 "quote_payload_sha256", "first_quote_record_sha256", "cross_basis_close",
                 "frozen_score", "frozen_rank")
    assert all(target[k] == original[k] for k in immutable)
    assert target["occurrences"] == 2 and len(target["event_ids"]) == 2
    assert target["last_ts"] == fixture["repeat_envelope"]["events"][0]["ts"]

    fractional_path = files_dir / "fractional_event_time.parquet"
    if fractional_path.exists():
        fractional_path.unlink()
    fractional_rows, _ = B.reconcile_file(fractional_path, read_frame=pd.read_parquet,
        write_rows=native_writer, reconcile=lambda old: ingest(old, fractional=True))
    fractional_disk = normalize(pd.read_parquet(fractional_path).to_dict(orient="records"))
    fractional_expected = datetime.fromisoformat(fixture["fractional_expected_ts"])
    assert len(fractional_rows) == len(fractional_disk) == 3
    assert all(datetime.fromisoformat(row["first_ts"].replace("Z", "+00:00")) == fractional_expected
               for row in fractional_disk)

    duplicate = deepcopy(baseline[0])
    duplicate["event_ids"].append("d" * 64)
    duplicate["occurrences"] += 1
    duplicate["last_ts"] = "2026-10-12T02:01:00Z"
    cases = [
        ("conflicting_duplicate_last", pd.DataFrame([*deepcopy(baseline), duplicate]), "duplicate_existing_daily_key"),
        ("conflicting_duplicate_first", pd.DataFrame([duplicate, *deepcopy(baseline)]), "duplicate_existing_daily_key"),
        ("exact_duplicate", pd.DataFrame([*deepcopy(baseline), deepcopy(baseline[0])]), "duplicate_existing_daily_key"),
        ("readable_unknown_schema", pd.DataFrame({"schema": ["not-the-native-schema"], "value": [1]}),
         "invalid_existing_ledger_schema"),
    ]
    refused_cases = []
    for label, frame, expected_reason in cases:
        path = files_dir / (label + ".parquet")
        frame.to_parquet(path, index=False)
        # The independent oracle first proves this is readable, valid Parquet.
        read_rows = len(pd.read_parquet(path))
        original_bytes = path.read_bytes()
        path.with_name(label + ".before.parquet").write_bytes(original_bytes)
        calls = []

        def forbidden_writer(destination, proposed):
            calls.append({"path": str(destination), "rows": len(proposed)})
            RD._write_parquet(destination, proposed)

        got = capture(lambda: B.reconcile_file(path, read_frame=pd.read_parquet,
                       write_rows=forbidden_writer, reconcile=ingest))
        assert got.get("exception_class") == "Refused" and got.get("reason") == expected_reason, (label, got)
        assert not calls, (label, calls)
        assert path.read_bytes() == original_bytes, label
        refused_cases.append({"case": label, "readable_input_rows": read_rows,
                               "writer_calls": len(calls), "refusal": got["reason"],
                               "before_sha256": sha256(original_bytes).hexdigest(),
                               "after_sha256": hash_file(path)})

    assert {"contract_prototype.py": hash_file(args.subject),
            "pinned_quote_adapter.py": hash_file(args.adapter)} == actual
    assert hash_file(args.bundle) == NATIVE_BUNDLE
    retained = {str(path.relative_to(out)): hash_file(path)
                for path in sorted(files_dir.iterdir()) if path.is_file()}
    result = {"schema": "independent_cn_integration_native_parquet_acceptance/v1",
              "status": "PASS", "helper_sha256": hash_file(Path(__file__)),
              "support_sha256": hash_file(HERE / "review_support.py"),
              "candidate_inputs_sha256": actual, "fixture_sha256": hash_file(args.fixture),
              "native_bundle_sha256": NATIVE_BUNDLE, "native_source_sha256": native_ids,
              "native_positive_write_count": len(positive_calls), "native_writes": positive_calls,
              "positive_roundtrip_rows": len(disk_rows),
              "legacy_row_preserved_without_provenance": legacy_before == legacy_after,
              "later_repeat_first_observation_preserved": True,
              "fractional_event_time_preserved": True,
              "refused_file_cases": refused_cases, "retained_files_sha256": retained,
              "execution": {"python": sys.version, "pandas": pd.__version__,
                            "system": platform.system(), "machine": platform.machine(),
                            "native_writer": "scripts/reconcile_cn_live.py::_write_parquet",
                            "filesystem_scope": "unique independent review temporary directory"},
              "effects": {"network_disabled": True, "vendor_calls": False,
                          "production_writes": False, "source_inputs_changed": False}}
    destination = out / "PARQUET_RECEIPT.json"
    destination.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "PASS", "native_writes": len(positive_calls),
                      "refused_files": len(refused_cases), "receipt_sha256": hash_file(destination)}))


if __name__ == "__main__":
    with patch.object(socket.socket, "connect", no_network), patch.object(socket, "create_connection", no_network):
        main()
