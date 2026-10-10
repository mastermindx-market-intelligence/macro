#!/usr/bin/env python3
"""Replay the retained research fixture without a checkout or network.

Usage: python -B verify_contract.py --out /tmp/integration-verification.json
Add --parquet to rerun the six real-file refusals in a new temporary directory.
Requires pandas only for importing the pinned native driver; --parquet additionally
requires a pandas Parquet engine. Fixture, source and result files are read-only.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import gzip
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
from types import ModuleType
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--parquet", action="store_true")
    args = parser.parse_args()
    checks = []

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append({"name": name, "status": "PASS"})

    def read(name):
        return json.loads((HERE / name).read_bytes())

    import contract_prototype as B
    results = read("integration_results.json")
    fixture = read("integration_fixture.json")
    bundle = read("native_source_bundle.json")
    check("study_pin", results["study_source_sha"] == bundle["source_sha"] == PIN)
    for name, identity in results["laboratory_code"].items():
        check("exact_executed_code:" + name, sha256((HERE / name).read_bytes()).hexdigest() == identity["sha256"])
    for path, source in bundle["files"].items():
        check("pinned_source:" + path, sha256(source["code"].encode()).hexdigest()
              == source["sha256"] == results["source_manifest"][path]["sha256"])
    for name in ("lib", "engine", "engine.prophet_live", "scripts"):
        module = ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
        if "." in name:
            parent, child = name.rsplit(".", 1)
            setattr(sys.modules[parent], child, module)
    load_order = ["lib/exchange_holidays.py", "lib/cn_calendar.py",
                  "engine/prophet_live/interval.py", "engine/prophet_live/live_states.py",
                  "engine/prophet_live/cn_clock.py", "engine/prophet_live/cn_states.py",
                  "engine/prophet_live/cn_reconcile.py", "engine/prophet_live/r2io.py",
                  "scripts/reconcile_cn_live.py"]
    modules = {}
    for path in load_order:
        name = path[:-3].replace("/", ".")
        module = ModuleType(name)
        module.__file__ = str(HERE / "_virtual_pinned_source" / path)
        module.__package__ = name.rsplit(".", 1)[0]
        sys.modules[name] = module
        parent, child = name.rsplit(".", 1)
        setattr(sys.modules[parent], child, module)
        exec(compile(bundle["files"][path]["code"], module.__file__, "exec"), module.__dict__)
        modules[path] = module
    CR = modules["engine/prophet_live/cn_reconcile.py"]
    R2 = modules["engine/prophet_live/r2io.py"]
    LS = modules["engine/prophet_live/live_states.py"]
    clock = modules["engine/prophet_live/cn_clock.py"]
    calendar = modules["lib/cn_calendar.py"]
    RD = modules["scripts/reconcile_cn_live.py"]
    resolver = B.SyntheticQuoteResolver((HERE / "pinned_quote_adapter.py").read_bytes())
    check("quote_contract_identity", fixture["quote_contract_id"] == resolver.contract_id
          and fixture["quote_contract"] == resolver.contract)
    canonical_identity = fixture["synthetic_settlement_board"]
    compressed = (HERE / canonical_identity["path"]).read_bytes()
    canonical_raw = gzip.decompress(compressed)
    check("compressed_canonical_identity", sha256(compressed).hexdigest() == canonical_identity["sha256"])
    check("canonical_bytes_identity", sha256(canonical_raw).hexdigest() == canonical_identity["uncompressed_sha256"])
    canonical = json.loads(canonical_raw)
    pack, settlement = fixture["base_pack"], fixture["settlement_pack"]
    session = canonical["as_of"]
    now = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)

    def fresh_store():
        s = B.MemoryR2(page_size=2)
        for key, doc in fixture["events"].items():
            s.put(key, doc)
        for p in (pack, settlement):
            s.put(B.pack_key(p, R2), p)
        s.put(R2.CN_PACK_KEY, settlement)
        return s

    def ingest(s=None, *, prior=None):
        return B.consume(fresh_store() if s is None else s, R2, CR, clock, calendar, LS,
            session=session, now=now, existing=[] if prior is None else prior,
            settlement_pack=settlement, canonical_board=canonical,
            canonical_board_raw=canonical_raw, quote_resolver=resolver)

    rows, receipt = ingest()
    check("exact_retained_ledger_reproduces", B.encoded(rows) == B.encoded(fixture["ledger"]))
    check("exact_retained_receipt_reproduces", B.encoded(receipt) == B.encoded(fixture["reconciliation"]))
    again, _ = ingest(prior=rows)
    check("exact_replay_idempotent", B.encoded(again) == B.encoded(rows))
    cases = read("repair_cases.json")["cases"]
    for case in cases:
        s = fresh_store()
        for key in case["removed_objects"]:
            s.objects.pop(key)
        for key, doc in case["written_objects"].items():
            s.put(key, doc)
        expected = case["expected"]
        if expected == "coalesced":
            got_rows, got_receipt = ingest(s)
            check(case["name"], got_rows == rows and got_receipt["receipt"] == receipt["receipt"]
                  and got_receipt["selected_close_evidence"] == case["selected_close_evidence"])
        elif expected in ("update_last_preserve_first", "precise_event_time"):
            got_rows, _ = ingest(s, prior=case["prior_rows"])
            check(case["name"], got_rows == case["result_rows"])
        else:
            try:
                ingest(s, prior=case["prior_rows"])
            except B.Refused as exc:
                check(case["name"], exc.reason == expected)
            else:
                raise AssertionError(case["name"] + ": unsupported evidence accepted")
    parquet_receipts = read("parquet_receipts.json")
    for item in parquet_receipts["cases"]:
        check("retained_parquet:" + item["case"], sha256((HERE / item["path"]).read_bytes()).hexdigest()
              == item["before_sha256"] == item["after_sha256"] and item["writer_calls"] == 0)
    parquet_execution = "not requested; retained host receipt and file identities verified"
    if args.parquet:
        import pandas as pd
        with tempfile.TemporaryDirectory(prefix="mmx-cn-integration-repair-replay-") as tmp:
            for item in parquet_receipts["cases"]:
                target = Path(tmp) / (item["case"] + ".parquet")
                shutil.copyfile(HERE / item["path"], target)
                before = target.read_bytes()
                calls = []

                def write_rows(path, new_rows):
                    calls.append(path)
                    RD._write_parquet(path, new_rows)

                try:
                    B.reconcile_file(target, read_frame=pd.read_parquet, write_rows=write_rows,
                                     reconcile=lambda old: ingest(prior=old))
                except B.Refused as exc:
                    check("native_parquet_refusal:" + item["case"], exc.reason == item["refusal"]
                          and calls == [] and target.read_bytes() == before)
                else:
                    raise AssertionError(item["case"] + ": unexpected Parquet write")
        parquet_execution = "six real Parquet cases independently replayed through native writer boundary"
    result = {"schema": "cn-integration-retained-replay/v1", "status": "PASS",
        "checks": checks, "counts": {"checks": len(checks)}, "python": sys.version.split()[0],
        "parquet_execution": parquet_execution, "study_pin": PIN,
        "inputs": {n: sha256((HERE / n).read_bytes()).hexdigest() for n in
            ("contract_prototype.py", "verify_contract.py", "integration_results.json",
             "integration_fixture.json", "repair_cases.json", "parquet_receipts.json", "native_source_bundle.json")}}
    output = Path(args.out).resolve()
    output.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps({"status": "PASS", "checks": len(checks), "parquet": parquet_execution,
                      "result": str(output), "sha256": sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    def no_network(*args, **kwargs):
        raise RuntimeError("network disabled in retained-fixture verification")
    with patch.object(socket.socket, "connect", no_network), patch.object(socket, "create_connection", no_network):
        main()
