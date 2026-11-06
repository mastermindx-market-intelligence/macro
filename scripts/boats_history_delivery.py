"""Pure assembly of the daily BOATS private-history delivery manifest.

``assemble_delivery(baseline, refresh)`` folds one completed
``refresh_boats_history`` run into the prior
``terminal.private_boats_delivery.v1`` manifest and returns the next one.
It is pure: no filesystem, clock, network or provider access — the caller
owns scheduling, transport and the copy of the emitted files.

Selection rules enforced here (rejection raises ``AssemblyError``, a
``ValueError`` subclass):

* the baseline manifest must be a valid, exactly partitioned
  ``terminal.private_boats_delivery.v1`` document;
* the refresh must be a *complete* run with no ``unavailable`` and no
  ``not_requested`` entries, no duplicate outputs and exactly one output
  per refreshed symbol;
* every refreshed symbol must already exist in the baseline and must not
  be held ``vendor_unavailable`` — the assembler never invents or drops a
  held-unavailable disposition;
* a file output replaces the prior entry (including an authoritative
  zero-bar file); a ``vendor_empty`` output may only retire a prior file
  that carried zero bars, never nonempty history;
* symbols untouched by the refresh are carried over byte-for-byte in
  values, and ``complete_history`` stays ``False``.

Each emitted file entry carries ``origin`` (``"baseline"`` or
``"refresh"``) purely as a caller hint for copy selection; it is not part
of the validated document shape, and an emitted document can be used
again as a baseline with the prior ``origin`` values ignored.
"""
from __future__ import annotations

import copy
import re
from typing import Any

SCHEMA = "terminal.private_boats_delivery.v1"

MAX_SYMBOLS = 20_000
MAX_BARS_PER_FILE = 100_000
MAX_BYTES_PER_FILE = 32 * 1024 * 1024

_SYMBOL_RE = re.compile(r"[A-Z][A-Z0-9.-]{0,31}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")

_FILE_KEYS = frozenset({"name", "bytes", "sha256", "bars"})
_FILE_FORM_KEYS = frozenset(
    {"symbol", "file", "bytes", "sha256", "bars", "new_receipt"}
)


class AssemblyError(ValueError):
    """Raised when the baseline or refresh manifest fails validation."""


def _fail(message: str) -> None:
    raise AssemblyError(message)


def _require_int(value: Any, label: str, maximum: int) -> int:
    # ``type(...) is int`` rejects bools (a bool is an int subclass) and
    # floats alike; negative magnitudes are never meaningful here.
    if type(value) is not int:
        _fail(f"{label} must be an int, got {type(value).__name__}")
    if value < 0:
        _fail(f"{label} must be nonnegative, got {value}")
    if value > maximum:
        _fail(f"{label} exceeds limit {maximum}, got {value}")
    return value


def _require_symbol(value: Any, label: str) -> str:
    if not isinstance(value, str):
        _fail(f"{label} must be a symbol string, got {type(value).__name__}")
    if _SYMBOL_RE.fullmatch(value) is None:
        _fail(f"{label} is not a valid BOATS symbol: {value!r}")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str):
        _fail(f"{label} must be a sha256 hex string, got {type(value).__name__}")
    if _SHA256_RE.fullmatch(value) is None:
        _fail(f"{label} is not a lowercase 64-hex sha256: {value!r}")
    return value


def _require_str_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        _fail(f"{label} must be a list, got {type(value).__name__}")
    for item in value:
        _require_symbol(item, f"{label} entry")
    if len(set(value)) != len(value):
        _fail(f"{label} contains duplicate symbols")
    return list(value)


def _symbol_of_name(name: str) -> str:
    suffix = ".json"
    if not name.endswith(suffix):
        _fail(f"file name must end with .json: {name!r}")
    symbol = name[: -len(suffix)]
    _require_symbol(symbol, f"file name {name!r} symbol")
    if "/" in name or "\\" in name or name in (".", ".."):
        _fail(f"file name must be a flat SYMBOL.json: {name!r}")
    return symbol


def _validate_baseline(baseline: Any) -> dict[str, dict[str, Any]]:
    """Validate a ``terminal.private_boats_delivery.v1`` baseline.

    Returns the baseline ``files`` entries keyed by name. Unknown top-level
    keys (for example the ``selected_symbols`` counts of a previous output)
    and a prior ``origin`` hint on file entries are ignored, so an emitted
    document can be fed straight back in as a baseline.
    """
    if not isinstance(baseline, dict):
        _fail("baseline must be a dict")
    if baseline.get("schema") != SCHEMA:
        _fail(f"baseline schema must be {SCHEMA!r}, got {baseline.get('schema')!r}")
    if baseline.get("complete_history") is not False:
        _fail("baseline complete_history must be false")

    requested = baseline.get("requested_symbols")
    if type(requested) is int:
        _require_int(requested, "requested_symbols", MAX_SYMBOLS)
    else:
        requested = _require_str_list(requested, "requested_symbols")
        if len(requested) > MAX_SYMBOLS:
            _fail(f"requested_symbols exceeds {MAX_SYMBOLS}, got {len(requested)}")
    vendor_empty = _require_str_list(
        baseline.get("vendor_empty_symbols"), "vendor_empty_symbols"
    )

    unavailable_raw = baseline.get("vendor_unavailable_symbols")
    if not isinstance(unavailable_raw, list):
        _fail("vendor_unavailable_symbols must be a list")
    unavailable_symbols: list[str] = []
    for entry in unavailable_raw:
        if not isinstance(entry, dict):
            _fail("vendor_unavailable_symbols entries must be dicts")
        if "symbol" not in entry or "reason" not in entry:
            _fail("vendor_unavailable_symbols entries need symbol and reason")
        symbol = _require_symbol(entry["symbol"], "vendor_unavailable symbol")
        reason = entry["reason"]
        if not isinstance(reason, str) or not reason:
            _fail(f"vendor_unavailable reason for {symbol} must be a nonempty string")
        unavailable_symbols.append(symbol)
    if len(set(unavailable_symbols)) != len(unavailable_symbols):
        _fail("vendor_unavailable_symbols contains duplicate symbols")

    files_raw = baseline.get("files")
    if not isinstance(files_raw, list):
        _fail("files must be a list")
    files: dict[str, dict[str, Any]] = {}
    file_symbols: list[str] = []
    total_bars = 0
    total_bytes = 0
    for entry in files_raw:
        if not isinstance(entry, dict):
            _fail("files entries must be dicts")
        extra = set(entry) - _FILE_KEYS - {"origin"}
        if extra:
            _fail(f"files entry has unexpected keys: {sorted(extra)}")
        for key in _FILE_KEYS:
            if key not in entry:
                _fail(f"files entry is missing {key!r}")
        name = entry["name"]
        if not isinstance(name, str):
            _fail(f"file name must be a string, got {type(name).__name__}")
        if name in files:
            _fail(f"duplicate file name: {name!r}")
        symbol = _symbol_of_name(name)
        bars = _require_int(entry["bars"], f"{name} bars", MAX_BARS_PER_FILE)
        file_bytes = _require_int(entry["bytes"], f"{name} bytes", MAX_BYTES_PER_FILE)
        _require_sha256(entry["sha256"], f"{name} sha256")
        files[name] = {
            "name": name,
            "bytes": file_bytes,
            "sha256": entry["sha256"],
            "bars": bars,
        }
        file_symbols.append(symbol)
        total_bars += bars
        total_bytes += file_bytes

    # Exact, unique partition: every requested symbol is a file, a
    # vendor_empty, or a held vendor_unavailable — exactly once.
    partition = file_symbols + vendor_empty + unavailable_symbols
    if len(set(partition)) != len(partition):
        _fail("baseline symbol partition is not unique")
    if len(partition) > MAX_SYMBOLS:
        _fail(f"symbol partition exceeds {MAX_SYMBOLS} symbols")
    if type(requested) is int and len(partition) != requested:
        _fail("baseline symbol partition count differs from requested_symbols")
    if isinstance(requested, list) and set(partition) != set(requested):
        missing = sorted(set(requested) - set(partition))
        extra = sorted(set(partition) - set(requested))
        _fail(
            "baseline symbol partition does not match requested_symbols; "
            f"missing={missing[:5]} extra={extra[:5]}"
        )

    if baseline.get("bars") != total_bars or type(baseline.get("bars")) is not int:
        _fail(f"baseline bars must equal the file sum {total_bars}")
    if baseline.get("bytes") != total_bytes or type(baseline.get("bytes")) is not int:
        _fail(f"baseline bytes must equal the file sum {total_bytes}")

    return files


def _parse_output(entry: Any, index: int) -> dict[str, Any]:
    if not isinstance(entry, dict):
        _fail(f"outputs[{index}] must be a dict")
    symbol = _require_symbol(entry.get("symbol"), f"outputs[{index}] symbol")
    status = entry.get("status")
    has_file = "file" in entry or "name" in entry
    if status not in {None, "vendor_empty", "rebuilt", "refreshed_empty_window"}:
        _fail(f"outputs[{index}] for {symbol} has unknown status {status!r}")

    if status == "vendor_empty":
        if has_file:
            _fail(f"vendor_empty output for {symbol} must not carry a file")
        if "bytes" in entry or "sha256" in entry:
            _fail(f"vendor_empty output for {symbol} must not carry file payload")
        if "bars" not in entry:
            _fail(f"vendor_empty output for {symbol} is missing bars")
        if entry["bars"] != 0 or type(entry["bars"]) is not int:
            _fail(f"vendor_empty output for {symbol} must carry exactly 0 bars")
        receipt = entry.get("new_receipt")
        if receipt is None:
            _fail(f"vendor_empty output for {symbol} is missing new_receipt")
        _require_sha256(receipt, f"vendor_empty output {symbol} new_receipt")
        return {"symbol": symbol, "kind": "vendor_empty"}

    if not has_file:
        _fail(f"output for {symbol} carries neither a file nor vendor_empty status")
    name = entry.get("file", entry.get("name"))
    if not isinstance(name, str):
        _fail(f"output file name for {symbol} must be a string")
    expected = f"{symbol}.json"
    if name != expected:
        _fail(f"output file name for {symbol} must be {expected!r}, got {name!r}")
    missing = _FILE_FORM_KEYS - set(entry)
    if missing:
        _fail(f"file output for {symbol} is missing keys: {sorted(missing)}")
    bars = _require_int(entry["bars"], f"output {name} bars", MAX_BARS_PER_FILE)
    out_bytes = _require_int(entry["bytes"], f"output {name} bytes", MAX_BYTES_PER_FILE)
    sha256 = _require_sha256(entry.get("sha256"), f"output {name} sha256")
    _require_sha256(entry["new_receipt"], f"output {name} new_receipt")
    return {
        "symbol": symbol,
        "kind": "file",
        "name": name,
        "bytes": out_bytes,
        "sha256": sha256,
        "bars": bars,
    }


def _validate_refresh(refresh: Any, baseline_files: dict[str, dict[str, Any]],
                      baseline_empty: list[str],
                      baseline_unavailable: set[str]) -> list[dict[str, Any]]:
    """Validate the completed refresh manifest; return its parsed outputs."""
    if not isinstance(refresh, dict):
        _fail("refresh must be a dict")
    if refresh.get("status") != "complete":
        _fail(
            "refresh is not complete, refusing to assemble a partial run: "
            f"status={refresh.get('status')!r}"
        )

    symbols = _require_str_list(refresh.get("symbols"), "refresh symbols")
    file_symbols = {name[: -len(".json")] for name in baseline_files}
    for symbol in symbols:
        if symbol in baseline_unavailable:
            _fail(
                f"refresh symbol {symbol} is held vendor_unavailable in the "
                "baseline; assembly must not mutate a held-unavailable symbol"
            )
        if symbol not in file_symbols and symbol not in baseline_empty:
            _fail(f"refresh symbol {symbol} is absent from the baseline delivery")

    for label in ("unavailable", "not_requested"):
        entries = refresh.get(label)
        if not isinstance(entries, list):
            _fail(f"refresh {label} must be a list, got {type(entries).__name__}")
        if entries:
            _fail(f"refresh {label} is nonempty ({len(entries)}), refusing to assemble")

    outputs_raw = refresh.get("outputs")
    if not isinstance(outputs_raw, list):
        _fail("refresh outputs must be a list")
    outputs = [_parse_output(entry, index) for index, entry in enumerate(outputs_raw)]

    seen: dict[str, int] = {}
    refreshed_symbols = set(symbols)
    for parsed in outputs:
        symbol = parsed["symbol"]
        if symbol in seen:
            _fail(f"refresh has duplicate outputs for {symbol}")
        seen[symbol] = 1
        if symbol not in refreshed_symbols:
            _fail(f"refresh output for {symbol} is not a refreshed symbol")
    for symbol in symbols:
        if symbol not in seen:
            _fail(f"refresh symbol {symbol} has no output")
    return outputs


def assemble_delivery(baseline: dict, refresh: dict) -> dict:
    """Fold one complete refresh run into the baseline delivery manifest.

    Pure: reads nothing but its two arguments, writes nothing, touches no
    clock. Returns the next ``terminal.private_boats_delivery.v1`` document;
    file entries gain an ``origin`` hint ("baseline" or "refresh") that is
    outside the validated shape and is ignored if the document is later
    reused as a baseline.
    """
    baseline_files = _validate_baseline(baseline)
    baseline_empty = list(baseline.get("vendor_empty_symbols") or [])
    baseline_unavailable = {
        entry["symbol"] for entry in (baseline.get("vendor_unavailable_symbols") or [])
    }
    outputs = _validate_refresh(
        refresh, baseline_files, baseline_empty, baseline_unavailable
    )

    files = dict(baseline_files)
    vendor_empty = set(baseline_empty)
    for parsed in outputs:
        symbol = parsed["symbol"]
        if parsed["kind"] == "file":
            files[parsed["name"]] = {
                "name": parsed["name"],
                "bytes": parsed["bytes"],
                "sha256": parsed["sha256"],
                "bars": parsed["bars"],
            }
            vendor_empty.discard(symbol)
            continue
        # vendor_empty: the prior file (if any) may only be retired when it
        # carried zero bars — never drop nonempty history via a no-file output.
        prior = files.get(f"{symbol}.json")
        if prior is not None:
            if prior["bars"] > 0:
                _fail(
                    f"vendor_empty output for {symbol} would drop nonempty prior "
                    f"history ({prior['bars']} bars); refusing"
                )
            del files[f"{symbol}.json"]
        vendor_empty.add(symbol)

    ordered = [files[name] for name in sorted(files)]
    total_bars = sum(entry["bars"] for entry in ordered)
    total_bytes = sum(entry["bytes"] for entry in ordered)

    replaced_names = {
        parsed["name"] for parsed in outputs if parsed["kind"] == "file"
    }
    out_files = []
    for entry in ordered:
        out_files.append(
            {
                "name": entry["name"],
                "bytes": entry["bytes"],
                "sha256": entry["sha256"],
                "bars": entry["bars"],
                "origin": "refresh" if entry["name"] in replaced_names else "baseline",
            }
        )

    selected = len(outputs)
    return {
        "schema": SCHEMA,
        "requested_symbols": copy.deepcopy(baseline["requested_symbols"]),
        "vendor_empty_symbols": sorted(vendor_empty),
        "vendor_unavailable_symbols": copy.deepcopy(
            baseline.get("vendor_unavailable_symbols") or []
        ),
        "files": out_files,
        "bars": total_bars,
        "bytes": total_bytes,
        "complete_history": False,
        "selected_symbols": selected,
        "preserved_symbols": len(baseline_files) + len(baseline_empty) + len(baseline_unavailable) - selected,
    }
