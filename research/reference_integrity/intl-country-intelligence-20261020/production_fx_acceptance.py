#!/usr/bin/env python3
"""Read-only acceptance of seven canonical FX stores after a normal main backfill.

Run with the repository's Python environment. No collector, renderer, workflow,
network request, receipt creation, data write, or deployment is invoked. The
supplied backfill window is a correlation bound, not an authenticated run receipt.
JSON is written only to stdout; the caller may retain it through normal tooling.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
from contextlib import ExitStack
from datetime import date, datetime, timezone
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
from unittest.mock import patch

ORDER = ("JP", "KR", "TW", "IN", "AU", "GB", "EZ")


def utc_argument(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("timezone required")
        return stamp.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise argparse.ArgumentTypeError("use an ISO timestamp with UTC offset or Z") from exc


def day_argument(value):
    try:
        day = date.fromisoformat(value)
        if day.isoformat() != value:
            raise ValueError("daily ISO label required")
        return day
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use YYYY-MM-DD") from exc


def install_read_only_guard():
    violations = []
    denied = {"os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.link",
              "os.symlink", "os.truncate", "os.chmod", "os.chown", "os.utime",
              "os.system", "os.exec", "os.fork", "os.forkpty", "os.posix_spawn",
              "os.spawn", "subprocess.Popen", "socket.connect", "socket.connect_ex",
              "socket.bind", "socket.sendto", "socket.sendmsg", "socket.getaddrinfo",
              "socket.gethostbyname", "socket.gethostbyaddr"}
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND

    def audit(event, args):
        blocked = event in denied
        if event == "open":
            mode, flags = args[1], args[2]
            blocked = ((isinstance(mode, str) and any(c in mode for c in "wax+"))
                       or isinstance(flags, int) and bool(flags & write_flags))
        if blocked:
            violations.append(event)
            raise PermissionError("FX probe is read-only: " + event)

    sys.addaudithook(audit)
    return violations


def file_identity(path):
    try:
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
        return {"path": str(path), "bytes": size, "sha256": digest.hexdigest()}
    except OSError as exc:
        return {"path": str(path), "bytes": None, "sha256": None,
                "read_error": type(exc).__name__}


def inspect_currency(cc, config, entry, fx, *, as_of, backfill_start, backfill_end):
    """Call the incumbent selector and serialized consumer; never derive a replacement."""
    currency, ticker, convention, _ = fx.SPECS[cc]
    source = entry.get("source")
    observations = entry.get("observations") or []
    expected_source = fx.stored_source_context(cc, config)
    errors = []
    result = {
        "cc": cc, "currency": currency, "configured_ticker": ticker,
        "quote_convention": convention, "provider": "Yahoo Finance",
        "expected_source_url": fx._source_url(cc),
        "input_observations": len(observations), "verdict": "FAIL", "errors": errors,
    }
    if expected_source is None or source != expected_source:
        errors.append("configured_source_identity_mismatch")
    raw = fx.build_currency_observation(cc, observations, today=as_of, source=source)
    view = fx.currency_observation_view(raw, cc, today=as_of)
    result.update(selector_status=raw.get("status"), selector_reason=raw.get("reason"),
                  consumer_available=view.get("available"), consumer_quality=view.get("quality"))
    # A control without row receipts must never become an eligible observation.
    legacy_rows = [(row[0], row[1], None) for row in observations
                   if isinstance(row, (tuple, list)) and len(row) >= 2]
    legacy = fx.build_currency_observation(cc, legacy_rows, today=as_of, source=source)
    legacy_view = fx.currency_observation_view(legacy, cc, today=as_of)
    result["legacy_only_control"] = {"selector_status": legacy.get("status"),
                                     "consumer_available": legacy_view.get("available")}
    if legacy.get("status") == "available" or legacy_view.get("available") is True:
        errors.append("legacy_rows_promoted")
    if raw.get("status") != "available" or view.get("available") is not True:
        errors.append("currency_evidence_unavailable")
        return result
    if view.get("quality") != "current":
        errors.append("currency_evidence_not_current")
    admitted_source = raw.get("source") or {}
    if admitted_source.get("kind") != "captured_store":
        errors.append("not_an_adapter_captured_store")
    if (raw.get("ticker") != ticker or raw.get("quote_convention") != convention
            or admitted_source.get("source_url") != result["expected_source_url"]):
        errors.append("admitted_source_identity_mismatch")
    result.update(
        method=raw["method"], source_url=view["source_url"],
        source_kind=admitted_source.get("kind"),
        provider_symbol=admitted_source.get("provider_symbol"),
        dataset_url=admitted_source.get("dataset_url"),
        reference_target=view["reference_target"],
        reference_gap_days=view["reference_gap_days"],
        local_currency_vs_usd_return_percent=view["value"],
        evidence_sha256=view["evidence_sha256"],
        retrieved_at=view["retrieved_at"],
        same_day_policy=raw["same_day_policy"],
        endpoints={},
    )
    receipts = admitted_source.get("endpoint_receipts") or {}
    for side in ("start", "end"):
        endpoint = raw[side]
        receipt = receipts.get(side)
        observed = fx._day(endpoint["date"])
        price = fx._price(endpoint["quote"])
        qualified = fx._read_adapter_receipt(receipt, cc, observed, price, as_of)
        if qualified is None:
            errors.append(side + "_adapter_receipt_missing_or_invalid")
            continue
        started = fx._instant(qualified["adapter_request_started_at_utc"])
        returned = fx._instant(qualified["adapter_result_returned_at_utc"])
        within_backfill = backfill_start <= started <= returned <= backfill_end
        excluded_capture_day = observed < started.date()
        if not within_backfill:
            errors.append(side + "_capture_outside_supplied_backfill_window")
        if not excluded_capture_day:
            errors.append(side + "_capture_day_included")
        result["endpoints"][side] = {
            "provider_date": endpoint["date"], "quote": endpoint["quote"],
            "quote_hex": qualified["quote_hex"],
            "configured_series": qualified["configured_series"],
            "adapter_request_started_at_utc": qualified["adapter_request_started_at_utc"],
            "adapter_result_returned_at_utc": qualified["adapter_result_returned_at_utc"],
            "eligible_before_date": qualified["eligible_before_date"],
            "date_policy": qualified["date_policy"],
            "eligibility_policy": qualified["eligibility_policy"],
            "receipt_sha256": qualified["receipt_sha256"],
            "within_supplied_backfill_window": within_backfill,
            "capture_day_excluded": excluded_capture_day,
        }
    result["verdict"] = "FAIL" if errors else "PASS"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path, help="existing approved repository checkout")
    parser.add_argument("--data", required=True, type=Path, help="existing canonical or copied data directory")
    parser.add_argument("--backfill-run-id", required=True, help="owner-verified main backfill workflow run ID")
    parser.add_argument("--backfill-start", required=True, type=utc_argument, help="actual workflow start timestamp")
    parser.add_argument("--backfill-end", required=True, type=utc_argument, help="actual workflow completion timestamp")
    parser.add_argument("--as-of", type=day_argument, default=datetime.now(timezone.utc).date(),
                        help="UTC evaluation day; defaults to the actual current UTC day")
    args = parser.parse_args()
    if args.backfill_end < args.backfill_start:
        parser.error("--backfill-end precedes --backfill-start")
    if args.backfill_end.date() > args.as_of:
        parser.error("--as-of precedes completion of the supplied backfill")
    try:
        repo = args.repo.resolve(strict=True)
        data = args.data.resolve(strict=True)
        if not repo.is_dir() or not data.is_dir():
            raise ValueError("repo and data must be existing directories")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    report = {
        "schema": "intl_fx_production_acceptance.v1",
        "probed_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluated_on": args.as_of.isoformat(), "repository": str(repo), "data_directory": str(data),
        "supplied_backfill": {"run_id": args.backfill_run_id,
                              "start_utc": args.backfill_start.isoformat(),
                              "end_utc": args.backfill_end.isoformat(),
                              "binding": "owner_supplied_clock_window"},
        "verdict": "FAIL", "currencies": [], "errors": [],
    }
    violations = install_read_only_guard()
    try:
        sys.path.insert(0, str(repo))
        config = importlib.import_module("lib.config")
        store = importlib.import_module("lib.store")
        intl_inputs = importlib.import_module("engine.intl_inputs")
        fx = importlib.import_module("lib.intl_currency_observation")
        for module in (config, store, intl_inputs, fx):
            if not Path(module.__file__).resolve().is_relative_to(repo):
                raise ValueError("import escaped the requested repository")
        report["source_files"] = {
            name: file_identity(repo / name) for name in (
                "lib/intl_currency_observation.py", "engine/intl_inputs.py",
                "lib/store.py", "lib/config.py", "collectors/intl_prices.py")}
        report["reader_function_sha256"] = hashlib.sha256(
            inspect.getsource(intl_inputs.country_currency_inputs).encode()).hexdigest()
        countries = intl_inputs.countries()
        paths = {}
        for cc in ORDER:
            ticker = fx.SPECS[cc][1]
            safe = ticker.replace("^", "_").replace("=", "_").replace("/", "_").replace(" ", "_")
            paths[ticker] = data / "intl" / (safe + ".parquet")
        before = {ticker: file_identity(path) for ticker, path in paths.items()}

        def existing_path(group, name):
            # store._path normally mkdir()s. Only its path side effect is removed;
            # the incumbent store.read and complete currency chain still execute.
            if group != "intl" or name not in paths:
                raise ValueError("probe attempted to read an unexpected series")
            return paths[name]

        with ExitStack() as stack:
            stack.enter_context(patch.object(store, "_path", existing_path))
            stack.enter_context(patch.object(config, "data_dir", lambda: data))
            inputs = intl_inputs.country_currency_inputs()
        for cc in ORDER:
            ticker = fx.SPECS[cc][1]
            try:
                row = inspect_currency(
                    cc, countries.get(cc), inputs.get(cc, {}), fx, as_of=args.as_of,
                    backfill_start=args.backfill_start, backfill_end=args.backfill_end)
            except Exception as exc:
                row = {"cc": cc, "configured_ticker": ticker, "verdict": "FAIL",
                       "errors": ["currency_probe_exception:" + type(exc).__name__]}
            after = file_identity(paths[ticker])
            row["canonical_store"] = before[ticker]
            row["store_unchanged_during_probe"] = before[ticker] == after
            if not before[ticker].get("sha256"):
                row["errors"].append("canonical_store_unreadable")
                row["verdict"] = "FAIL"
            if before[ticker] != after:
                row["errors"].append("canonical_store_changed_during_probe")
                row["verdict"] = "FAIL"
            report["currencies"].append(row)
        report["pass_count"] = sum(row["verdict"] == "PASS" for row in report["currencies"])
        report["verdict"] = "PASS" if report["pass_count"] == len(ORDER) and not violations else "FAIL"
        code = 0 if report["verdict"] == "PASS" else 1
    except Exception as exc:
        report["errors"].append("setup_or_reader_failure:" + type(exc).__name__)
        code = 2
    report["read_only_violations"] = violations
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
