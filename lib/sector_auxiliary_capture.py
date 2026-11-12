"""Bounded decoding of explicitly captured Sector auxiliary bytes.

This module observes no filesystem, configuration, provider, pointer or clock.
The upstream capture owner supplies every observation, including failed reads.
A digest binds supplied bytes; it does not independently prove their origin.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
from io import BytesIO
import hashlib
import json
import math
import re
from typing import Any

MIB = 1024 * 1024
MAX_CAPTURE_BYTES = 512 * MIB
MAX_DECODE_BYTES = 256 * MIB
MAX_PARQUET_BYTES = 64 * MIB
MAX_FOOTER_BYTES = 8 * MIB
MAX_DOCUMENT_NODES = 250_000
MAX_CAPTURE_NODES = 1_000_000
MAX_DEPTH = 32
MAX_SCALAR_BYTES = 512 * 1024
MAX_JSONL_LINES = 50_000
MAX_SNAPSHOT_JSON_BYTES = 16 * MIB

# Roots are labels for the acquisition owner, never paths opened here.
# R=repository, D=configured data, S=configured site, T=ThemeContext's root.
SOURCE_SPECS = {
    "config": ("yaml", "R/config.yml"),
    "cycle_bands": ("json", "D/regime/cycle_bands_fit.json"),
    "risk_calibration": ("json", "D/regime/ladder_risk_calibration.json"),
    "overlay_gate": ("json", "D/vol_regime/basket_overlay_gate.json"),
    "baskets_calibration": ("json", "D/strategies/baskets_calibration.json"),
    "hazard_model": ("json", "R/data/hazard/model_price_c4414dcb.json"),
    "hazard_km": ("json", "R/data/hazard/km_baseline_price_c4414dcb.json"),
    "rotation_phase0": ("json", "D/strategies/thematic_rotation_phase0.json"),
    "pulse_heat": ("json", "D/strategies/sector_pulse_heat.json"),
    "regime_latest": ("json", "D/regime/latest.json"),
    "public_risk_envelope": ("json", "S/riskdata/risk_envelope.json"),
    "bonds_latest": ("json", "D/bonds/latest.json"),
    "forex_latest": ("json", "D/forex/latest.json"),
    "vol_regime": ("json", "S/vol/regime.json"),
    "market_state": ("json", "D/market_state/latest.json"),
    "heatmap": ("json", "S/marketdata/sp500_heatmap.json"),
    "short_interest": ("parquet", "D/finra/short_interest.parquet"),
    "breadth_tape": ("parquet", "D/breadth/breadth.parquet"),
    "earnings": ("parquet", "D/earnings/earnings.parquet"),
    "radar": ("json", "R/site/basketdata/radar.json"),
    "subsector_rotation": ("json", "S/marketdata/subsector_rotation.json"),
    "rotation_events": ("json", "S/marketdata/rotation_events.json"),
    "sector_fragmentation": ("json", "S/marketdata/sector_fragmentation.json"),
    "rotation_artifact": ("json", "D/us_sector_rotation/latest.json"),
    "factor_seasonality": ("json", "S/factordata/factor_seasonality.json"),
    "flow": ("json", "S/basketdata/flow.json"),
    "insider_signals": ("json", "S/factordata/insider_signals.json"),
    "factors": ("json", "S/factordata/factors.json"),
    "alpha": ("json", "S/factordata/alpha.json"),
    "theme_context_history": ("jsonl", "T/data/themes/context_history.jsonl"),
    "basket_archive": ("parquet", "D/signal_archive/baskets.parquet"),
    "theme_seed_archive": ("parquet", "T/data/signal_archive/baskets.parquet"),
    "cycle_forward_log": ("parquet", "D/sector_cycles/forward_log.parquet"),
    "central_calls": ("parquet", "D/sector_central/calls.parquet"),
    "basket_frozen": ("parquet", "D/basket_levels/us.parquet"),
}
SOURCE_KEYS = frozenset(SOURCE_SPECS)
_OUTCOMES = frozenset(("present", "absent", "unreadable", "malformed"))
_REASONS = {
    "present": frozenset(("observed",)),
    "absent": frozenset(("not_found",)),
    "unreadable": frozenset(("read_denied", "io_error", "unstable_read")),
    "malformed": frozenset(("source_malformed",)),
}


class AuxiliaryCaptureError(ValueError):
    """A contradictory/unbound capture or resource bound: refuse the whole set."""


class _Malformed(ValueError):
    """An observed source cannot be decoded; retain that source's evidence."""


@dataclass(frozen=True)
class CapturedAuxiliarySource:
    origin: str
    source_revision: str | None
    captured_at: datetime
    outcome: str
    reason: str
    raw_bytes: bytes | None
    byte_length: int | None
    sha256: str | None


@dataclass(frozen=True)
class AuxiliaryEvidence:
    key: str
    origin: str
    source_revision: str | None
    captured_at: datetime
    observation: str
    observation_reason: str
    decode_outcome: str
    decode_reason: str
    byte_length: int | None
    sha256: str | None


@dataclass(frozen=True)
class SectorAuxiliaryCapture:
    captured_at: datetime
    evidence: tuple[AuxiliaryEvidence, ...]
    unresolved: tuple[str, ...]
    _documents: dict[str, Any]
    _tables: dict[str, Any]

    def document(self, key: str) -> Any:
        """Detached value; failed/absent sources are distinguished by evidence."""
        if key not in SOURCE_KEYS or SOURCE_SPECS[key][0] == "parquet":
            raise KeyError(key)
        return deepcopy(self._documents.get(key))

    def table(self, key: str):
        if key not in SOURCE_KEYS or SOURCE_SPECS[key][0] != "parquet":
            raise KeyError(key)
        value = self._tables.get(key)
        return None if value is None else value.copy(deep=True)

    def observation(self, key: str) -> AuxiliaryEvidence:
        for item in self.evidence:
            if item.key == key:
                return item
        raise KeyError(key)

    def input_lineage(self) -> dict:
        return {
            "schema": "sector_auxiliary_capture.v1",
            "captured_at": self.captured_at.isoformat(),
            "sources": {e.key: {
                "origin": e.origin, "source_revision": e.source_revision,
                "captured_at": e.captured_at.isoformat(),
                "observation": e.observation, "observation_reason": e.observation_reason,
                "decode_outcome": e.decode_outcome, "decode_reason": e.decode_reason,
                "byte_length": e.byte_length, "sha256": e.sha256,
            } for e in self.evidence},
            "unresolved": list(self.unresolved),
        }


def _instant(value):
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise AuxiliaryCaptureError("aware_capture_instant_required")
    return value.astimezone(timezone.utc)


def _label(value, maximum):
    return (type(value) is str and 0 < len(value.encode("utf-8")) <= maximum
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _Malformed("duplicate_key")
        result[key] = value
    return result


def _nonfinite(_value):
    raise _Malformed("nonfinite_value")


def _walk(value, *, yaml_dates=False):
    """Bound expanded aliases as well as ordinary JSON nodes, without copying."""
    count = 0
    active = set()

    def visit(item, depth):
        nonlocal count
        count += 1
        if count > MAX_DOCUMENT_NODES or depth > MAX_DEPTH:
            raise AuxiliaryCaptureError("document_structure_bound")
        if type(item) in (dict, list):
            identity = id(item)
            if identity in active:
                raise AuxiliaryCaptureError("recursive_document")
            active.add(identity)
            if type(item) is dict:
                for key, child in item.items():
                    if type(key) is not str or len(key.encode("utf-8")) > 1024:
                        raise _Malformed("unsupported_document_key")
                    visit(key, depth + 1)
                    visit(child, depth + 1)
            else:
                for child in item:
                    visit(child, depth + 1)
            active.remove(identity)
        elif type(item) is str:
            if len(item.encode("utf-8")) > MAX_SCALAR_BYTES:
                raise AuxiliaryCaptureError("document_scalar_bound")
        elif type(item) is float:
            if not math.isfinite(item):
                raise _Malformed("nonfinite_value")
        elif type(item) is int:
            if item.bit_length() > 256:
                raise AuxiliaryCaptureError("document_integer_bound")
        elif item is None or type(item) is bool:
            pass
        elif yaml_dates and type(item) in (date, datetime):
            pass  # Preserve SafeLoader's scalar value; never evaluate relative words.
        else:
            raise _Malformed("unsupported_document_value")

    visit(value, 0)
    return count


def _json(raw):
    try:
        # Guard parser recursion before constructing a container.
        text = raw.decode("utf-8", errors="strict")
        depth = 0
        quoted = escaped = False
        for char in text:
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                depth += 1
                if depth > MAX_DEPTH:
                    raise AuxiliaryCaptureError("document_structure_bound")
            elif char in "]}":
                depth -= 1
        value = json.loads(text, object_pairs_hook=_unique, parse_constant=_nonfinite)
        return value, _walk(value)
    except (AuxiliaryCaptureError, _Malformed):
        raise
    except (UnicodeError, ValueError, RecursionError, TypeError):
        raise _Malformed("invalid_json") from None


def _yaml(raw):
    import yaml

    class CaptureLoader(yaml.SafeLoader):
        pass

    def mapping(loader, node):
        # Reject explicit duplicates while retaining SafeLoader merge semantics.
        seen = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                continue
            key = loader.construct_object(key_node, deep=True)
            if type(key) is not str:
                raise _Malformed("unsupported_document_key")
            if key in seen:
                raise _Malformed("duplicate_key")
            seen.add(key)
        loader.flatten_mapping(node)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=True)

    CaptureLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    try:
        text = raw.decode("utf-8", errors="strict")
        depth = events = aliases = 0
        anchors = []
        for event in yaml.parse(text, Loader=yaml.SafeLoader):
            events += 1
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
                anchors.append(event.anchor)
            if isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1
                anchors.pop()
            if isinstance(event, yaml.AliasEvent):
                if event.anchor in anchors:
                    raise AuxiliaryCaptureError("recursive_document")
                aliases += 1
            if depth > MAX_DEPTH or events > MAX_DOCUMENT_NODES or aliases > 64:
                raise AuxiliaryCaptureError("yaml_structure_bound")
        # Composition creates a bounded node graph without flattening merges.
        # Count its expanded traversal before SafeLoader can duplicate pair lists.
        node = yaml.compose(text, Loader=yaml.SafeLoader)
        expanded = 0
        active_nodes = set()

        def admit_node(item, depth):
            nonlocal expanded
            if item is None:
                return
            expanded += 1
            if expanded > MAX_DOCUMENT_NODES or depth > MAX_DEPTH:
                raise AuxiliaryCaptureError("yaml_expansion_bound")
            if id(item) in active_nodes:
                raise AuxiliaryCaptureError("recursive_document")
            active_nodes.add(id(item))
            if isinstance(item, yaml.MappingNode):
                for key_node, value_node in item.value:
                    admit_node(key_node, depth + 1)
                    admit_node(value_node, depth + 1)
            elif isinstance(item, yaml.SequenceNode):
                for child in item.value:
                    admit_node(child, depth + 1)
            elif isinstance(item, yaml.ScalarNode):
                if len(item.value.encode("utf-8")) > MAX_SCALAR_BYTES:
                    raise AuxiliaryCaptureError("document_scalar_bound")
            else:
                raise _Malformed("unsupported_yaml_node")
            active_nodes.remove(id(item))

        admit_node(node, 0)
        value = yaml.load(text, Loader=CaptureLoader)
        return value, _walk(value, yaml_dates=True)
    except (AuxiliaryCaptureError, _Malformed):
        raise
    except (yaml.YAMLError, UnicodeError, ValueError, TypeError, RecursionError):
        raise _Malformed("invalid_yaml") from None


def _jsonl(raw):
    lines = raw.splitlines()
    if len(lines) > MAX_JSONL_LINES:
        raise AuxiliaryCaptureError("jsonl_line_bound")
    values, nodes = [], 0
    for line in lines:
        if not line.strip():
            continue
        value, count = _json(line)
        if not isinstance(value, dict):
            raise _Malformed("jsonl_record_required")
        values.append(value)
        nodes += count
        if nodes > MAX_DOCUMENT_NODES:
            raise AuxiliaryCaptureError("jsonl_structure_bound")
    # A corrupt line refuses this source; never silently report a shorter history.
    return values, nodes


@dataclass
class _TablePlan:
    key: str
    raw: bytes
    columns: tuple[str, ...]
    string_columns: tuple[str, ...]
    index: str | None
    index_name: str | None
    rows: int
    prospective_bytes: int
    table: Any = None


_NUMERIC = {
    "short_interest": {"short_shares", "prev_short_shares", "avg_daily_vol", "days_to_cover", "si_change_pct"},
    "breadth_tape": {"adv", "dec", "pct_above_50", "pct_above_200", "nh", "nl"},
    "central_calls": {"score", "dir", "confluence", "ret_12m", "gate_factor", "level", "score_version"},
}
_STRINGS = {
    "short_interest": {"settlement_date", "asof"},
    "earnings": {"next_date", "as_of"},
    "basket_archive": {"asof", "snapshot_json", "logged_at"},
    "theme_seed_archive": {"asof", "snapshot_json", "logged_at"},
    "cycle_forward_log": {"date", "id", "phase_v2", "basis"},
    "central_calls": {"date", "id", "kind", "ticker", "basket_id", "name", "label"},
}
_BOOLEANS = {"short_interest": {"dtc_capped"}, "central_calls": {"trend_pass"}}
_REQUIRED = {
    "short_interest": {"days_to_cover"},
    "breadth_tape": {"adv", "dec"},
    "earnings": {"next_date", "as_of"},
    "basket_archive": {"asof", "snapshot_json"},
    "theme_seed_archive": {"asof", "snapshot_json"},
    "cycle_forward_log": {"date", "id", "phase_v2"},
    "central_calls": {"date", "id", "kind", "ticker", "basket_id", "name", "label", "score", "dir", "level"},
}
_SHAPES = {
    "short_interest": (50_000, 16), "earnings": (50_000, 16),
    "breadth_tape": (50_000, 256),
    "basket_archive": (50_000, 2048), "theme_seed_archive": (50_000, 2048),
    "cycle_forward_log": (250_000, 64), "central_calls": (250_000, 32),
    "basket_frozen": (50_000, 5001),
}


def _string_type(value):
    import pyarrow as pa
    return pa.types.is_string(value) or pa.types.is_large_string(value)


def _open(raw, dictionary=()):
    import pyarrow.parquet as pq
    return pq.ParquetFile(BytesIO(raw), memory_map=False, pre_buffer=False,
        read_dictionary=list(dictionary), thrift_string_size_limit=MAX_FOOTER_BYTES,
        thrift_container_size_limit=512_000, arrow_extensions_enabled=False,
        page_checksum_verification=True)


def _index(metadata, names, key, rows):
    payload = metadata.get(b"pandas")
    if payload is None:
        indices, description = [], {}
    else:
        description, _ = _json(payload)
        if not isinstance(description, dict):
            raise _Malformed("invalid_index_metadata")
        indices = description.get("index_columns")
    physical = key in {"short_interest", "earnings", "breadth_tape", "basket_frozen"}
    if physical:
        if (not isinstance(indices, list) or len(indices) != 1
                or type(indices[0]) is not str or indices[0] not in names):
            raise _Malformed("physical_index_required")
        name = indices[0]
        descriptors = description.get("columns", [])
        if not isinstance(descriptors, list):
            raise _Malformed("invalid_index_metadata")
        matches = [d for d in descriptors if isinstance(d, dict) and d.get("field_name") == name]
        index_name = matches[0].get("name", name) if len(matches) == 1 else name
        if index_name is not None and not _label(index_name, 256):
            raise _Malformed("invalid_index_name")
        return name, index_name
    if indices == []:
        return None, None
    if isinstance(indices, list) and len(indices) == 1 and isinstance(indices[0], dict):
        item = indices[0]
        if (set(item) == {"kind", "name", "start", "stop", "step"} and item["kind"] == "range"
                and item["name"] is None and type(item["start"]) is int and item["start"] == 0
                and type(item["stop"]) is int and item["stop"] == rows
                and type(item["step"]) is int and item["step"] == 1):
            return None, None
    raise _Malformed("record_index_invalid")


def _preflight_table(key, raw):
    import pyarrow as pa
    if len(raw) < 12 or raw[:4] != b"PAR1" or raw[-4:] != b"PAR1":
        raise _Malformed("parquet_magic_invalid")
    footer = int.from_bytes(raw[-8:-4], "little")
    if footer > MAX_FOOTER_BYTES:
        raise AuxiliaryCaptureError("parquet_footer_bound")
    if not 0 < footer <= len(raw) - 12:
        raise _Malformed("parquet_footer_invalid")
    try:
        with _open(raw) as parquet:
            meta = parquet.metadata
            max_rows, max_columns = _SHAPES[key]
            if (not 0 <= meta.num_rows <= max_rows or not 0 <= meta.num_columns <= max_columns
                    or not 0 <= meta.num_row_groups <= 32
                    or meta.num_rows * meta.num_columns > 5_000_000):
                raise AuxiliaryCaptureError("parquet_shape_bound")
            metadata = meta.metadata or {}
            if (not set(metadata).issubset({b"pandas", b"ARROW:schema"})
                    or sum(len(k) + len(v) for k, v in metadata.items()) > MAX_FOOTER_BYTES):
                raise _Malformed("parquet_metadata_invalid")
            schema = parquet.schema_arrow
            names = schema.names
            if len(set(names)) != len(names) or any(not _label(n, 256) for n in names):
                raise _Malformed("parquet_columns_invalid")
            for field in schema:
                t = field.type
                if (field.metadata or isinstance(t, pa.ExtensionType) or not (
                        pa.types.is_integer(t) or pa.types.is_floating(t) or pa.types.is_boolean(t)
                        or _string_type(t) or pa.types.is_null(t)
                        or pa.types.is_timestamp(t) and t.tz is None and t.unit in ("ms", "us", "ns"))):
                    raise _Malformed("parquet_primitive_schema_required")
            index, index_name = _index(metadata, names, key, meta.num_rows)
            if index is not None:
                t = schema.field(index).type
                string_index = key in {"short_interest", "earnings"}
                if not (_string_type(t) if string_index else
                        pa.types.is_timestamp(t) and t.tz is None and t.unit in ("ms", "us", "ns")):
                    if not (meta.num_rows == 0 and pa.types.is_null(t)):
                        raise _Malformed("index_type_invalid")
            if key == "basket_frozen":
                numeric, strings, booleans = set(), set(), set()
                for name in names:
                    if name == index:
                        continue
                    if name == "__freeze_schema":
                        numeric.add(name)
                        continue
                    match = re.fullmatch(r"([A-Za-z0-9_-]{1,128})__(level_price|level_tr|n_members|mhash|anchor)", name)
                    if match is None:
                        raise _Malformed("frozen_column_invalid")
                    (strings if match[2] in ("mhash", "anchor") else numeric).add(name)
                required = set()
            else:
                numeric, strings, booleans = _NUMERIC.get(key, set()), _STRINGS.get(key, set()), _BOOLEANS.get(key, set())
                required = _REQUIRED[key]
            semantic = numeric | strings | booleans
            if key == "earnings":
                semantic |= {"next_time", "eps_forecast", "surprises_json", "surprises_as_of"}
            if index is not None and (index in semantic or key == "basket_frozen" and (
                    index == "__freeze_schema" or re.fullmatch(
                        r"[A-Za-z0-9_-]{1,128}__(level_price|level_tr|n_members|mhash|anchor)", index))):
                raise _Malformed("index_data_column_collision")
            if meta.num_rows and not required.issubset(names):
                raise _Malformed("required_columns_missing")
            selected = list(names) if key == "cycle_forward_log" else [n for n in names if n == index or n in numeric | strings | booleans]
            for name in selected:
                if name == index or name not in numeric | strings | booleans:
                    continue
                t = schema.field(name).type
                valid = pa.types.is_null(t)
                if name in numeric:
                    valid |= pa.types.is_floating(t) or pa.types.is_integer(t)
                elif name in strings:
                    valid |= _string_type(t)
                else:
                    valid |= pa.types.is_boolean(t)
                if not valid:
                    raise _Malformed("parquet_field_type_invalid")
            declared = sum(meta.row_group(i).total_byte_size for i in range(meta.num_row_groups))
            if declared > MAX_PARQUET_BYTES or declared < 0:
                raise AuxiliaryCaptureError("parquet_declared_allocation_bound")
            # Footer admission for the whole capture precedes any Arrow read.
            prospective = max(declared, meta.num_rows * len(selected) * 16)
            if prospective > MAX_PARQUET_BYTES:
                raise AuxiliaryCaptureError("parquet_prospective_allocation_bound")
            return _TablePlan(key, raw, tuple(selected),
                tuple(n for n in selected if _string_type(schema.field(n).type)),
                index, index_name, meta.num_rows, prospective)
    except (AuxiliaryCaptureError, _Malformed):
        raise
    except Exception:
        raise _Malformed("parquet_metadata_unreadable") from None


def _arrow_table(plan):
    try:
        with _open(plan.raw, plan.string_columns) as parquet:
            table = parquet.read(columns=list(plan.columns), use_threads=False, use_pandas_metadata=False)
        if table.num_rows != plan.rows or table.nbytes > MAX_PARQUET_BYTES:
            raise AuxiliaryCaptureError("parquet_materialization_bound")
        return table
    except (AuxiliaryCaptureError, _Malformed):
        raise
    except Exception:
        raise _Malformed("parquet_data_unreadable") from None


def _python_allocation(table):
    """Count worst-case expanded Python strings before to_pylist/DataFrame."""
    import pyarrow as pa
    import pyarrow.compute as pc
    budget = table.num_rows * max(1, table.num_columns) * 16
    for column in table.columns:
        for chunk in column.chunks:
            if pa.types.is_dictionary(chunk.type):
                dictionary = chunk.dictionary
                if not _string_type(dictionary.type):
                    raise _Malformed("string_dictionary_required")
                lengths = pc.binary_length(dictionary)
                maximum = pc.max(lengths).as_py() or 0
                if maximum > MAX_SCALAR_BYTES:
                    raise AuxiliaryCaptureError("table_string_bound")
                expanded = pc.sum(pc.take(lengths, chunk.indices)).as_py() or 0
                budget += 4 * expanded + 64 * (len(chunk) - chunk.null_count)
            elif _string_type(chunk.type):
                # A dictionary-preserving string read was requested. A plain
                # string Arrow result remains bounded before Python expansion.
                lengths = pc.binary_length(chunk)
                if (pc.max(lengths).as_py() or 0) > MAX_SCALAR_BYTES:
                    raise AuxiliaryCaptureError("table_string_bound")
                budget += 4 * (pc.sum(lengths).as_py() or 0) + 64 * (len(chunk) - chunk.null_count)
            elif pa.types.is_floating(chunk.type):
                finite = pc.all(pc.fill_null(pc.is_finite(chunk), True)).as_py()
                if finite is False:
                    raise _Malformed("nonfinite_table_value")
            elif pa.types.is_integer(chunk.type):
                budget += len(chunk) * 40
    return budget


def _frame(plan):
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    values = {}
    for name in plan.columns:
        column = plan.table[name]
        t = column.type
        if pa.types.is_dictionary(t) or _string_type(t):
            values[name] = column.to_pylist()
        elif pa.types.is_integer(t):
            prefix = "UInt" if pa.types.is_unsigned_integer(t) else "Int"
            values[name] = pd.array(column.to_pylist(), dtype=prefix + str(t.bit_width))
        elif pa.types.is_boolean(t):
            values[name] = pd.array(column.to_pylist(), dtype="boolean")
        elif pa.types.is_null(t):
            values[name] = [None] * plan.rows
        else:
            values[name] = column.to_numpy(zero_copy_only=False)
    if plan.index is None:
        index = pd.RangeIndex(plan.rows)
    else:
        raw_index = values.pop(plan.index)
        if plan.key in {"short_interest", "earnings"}:
            if any(type(v) is not str or not _label(v, 64) for v in raw_index):
                raise _Malformed("ticker_index_invalid")
            index = pd.Index(raw_index, name=plan.index_name, dtype=object)
        else:
            if np.isnat(np.asarray(raw_index, dtype="datetime64[ns]")).any():
                raise _Malformed("null_timestamp_index")
            index = pd.DatetimeIndex(raw_index, name=plan.index_name)
    return pd.DataFrame(values, index=index)


def decode_sector_auxiliary_capture(sources: Mapping[str, CapturedAuxiliarySource], *,
                                    captured_at: datetime) -> SectorAuxiliaryCapture:
    """Decode a complete, detached value set or refuse contradictory admission.

    Ordinary malformed content is recorded per source. Resource violations and
    unbound/contradictory observations refuse the set. No fallback is acquired.
    """
    now = _instant(captured_at)
    if not isinstance(sources, Mapping) or set(sources) != SOURCE_KEYS:
        raise AuxiliaryCaptureError("exact_auxiliary_source_set_required")
    bound, origins, total_bytes = {}, {}, 0
    for key in SOURCE_SPECS:
        item = sources[key]
        if not isinstance(item, CapturedAuxiliarySource):
            raise AuxiliaryCaptureError("explicit_source_observation_required")
        if (not _label(item.origin, 2048) or
                item.source_revision is not None and not _label(item.source_revision, 256)
                or type(item.outcome) is not str or item.outcome not in _OUTCOMES
                or type(item.reason) is not str or item.reason not in _REASONS[item.outcome]):
            raise AuxiliaryCaptureError("invalid_observation")
        instant = _instant(item.captured_at)
        if instant > now:
            raise AuxiliaryCaptureError("future_capture_observation")
        raw = item.raw_bytes
        if item.outcome in {"present", "malformed"}:
            if (type(raw) is not bytes or type(item.byte_length) is not int
                    or item.byte_length != len(raw) or type(item.sha256) is not str):
                raise AuxiliaryCaptureError("source_bytes_identity_mismatch")
            limit = {"yaml": MIB, "json": 8 * MIB, "jsonl": 16 * MIB, "parquet": MAX_PARQUET_BYTES}[SOURCE_SPECS[key][0]]
            if len(raw) > limit:
                raise AuxiliaryCaptureError("source_encoded_bound")
            total_bytes += len(raw)
            if total_bytes > MAX_CAPTURE_BYTES:
                raise AuxiliaryCaptureError("capture_encoded_bound")
            if item.sha256 != hashlib.sha256(raw).hexdigest():
                raise AuxiliaryCaptureError("source_bytes_identity_mismatch")
        elif raw is not None or item.byte_length is not None or item.sha256 is not None:
            raise AuxiliaryCaptureError("failed_observation_has_bytes")
        identity = (item.source_revision, instant, item.outcome, item.reason, item.byte_length, item.sha256)
        if item.origin in origins and origins[item.origin] != identity:
            raise AuxiliaryCaptureError("conflicting_origin_observations")
        origins[item.origin] = identity
        bound[key] = item
    if total_bytes > MAX_CAPTURE_BYTES:
        raise AuxiliaryCaptureError("capture_encoded_bound")

    documents, frames, plans, results = {}, {}, {}, {}
    nodes = prospective = document_allocation = 0
    for key, item in bound.items():
        if item.outcome != "present":
            results[key] = (item.outcome, item.reason)
            continue
        try:
            kind = SOURCE_SPECS[key][0]
            if kind == "parquet":
                plan = _preflight_table(key, item.raw_bytes)
                prospective += plan.prospective_bytes
                if prospective > MAX_DECODE_BYTES:
                    raise AuxiliaryCaptureError("capture_prospective_allocation_bound")
                plans[key] = plan
            else:
                decoder = {"json": _json, "yaml": _yaml, "jsonl": _jsonl}[kind]
                document, count = decoder(item.raw_bytes)
                nodes += count
                if nodes > MAX_CAPTURE_NODES:
                    raise AuxiliaryCaptureError("capture_structure_bound")
                document_allocation += 4 * len(item.raw_bytes) + count * 96
                prospective += 4 * len(item.raw_bytes) + count * 96
                if prospective > MAX_DECODE_BYTES:
                    raise AuxiliaryCaptureError("capture_prospective_allocation_bound")
                documents[key] = document
            results[key] = ("present", "decoded")
        except _Malformed as error:
            results[key] = ("malformed", str(error))

    # Every footer is qualified before reading the first table. String expansion
    # is checked for the whole decoded set before constructing Python/pandas.
    allocation = document_allocation
    for key, plan in plans.items():
        try:
            plan.table = _arrow_table(plan)
            allocation += plan.table.nbytes + _python_allocation(plan.table)
            if allocation > MAX_DECODE_BYTES:
                raise AuxiliaryCaptureError("capture_decoded_allocation_bound")
        except _Malformed as error:
            plan.table = None
            results[key] = ("malformed", str(error))
    snapshot_bytes = 0
    for key, plan in plans.items():
        if plan.table is None:
            continue
        try:
            frame = _frame(plan)
            if key in {"basket_archive", "theme_seed_archive"} and "snapshot_json" in frame:
                for value in frame["snapshot_json"]:
                    if type(value) is not str:
                        raise _Malformed("archive_snapshot_required")
                    raw = value.encode("utf-8")
                    snapshot_bytes += len(raw)
                    if snapshot_bytes > MAX_SNAPSHOT_JSON_BYTES:
                        raise AuxiliaryCaptureError("archive_snapshot_allocation_bound")
                    _, count = _json(raw)
                    nodes += count
                    if nodes > MAX_CAPTURE_NODES:
                        raise AuxiliaryCaptureError("capture_structure_bound")
            frames[key] = frame
        except _Malformed as error:
            results[key] = ("malformed", str(error))

    evidence = tuple(AuxiliaryEvidence(key, item.origin, item.source_revision,
        _instant(item.captured_at), item.outcome, item.reason, *results[key],
        item.byte_length, item.sha256) for key, item in bound.items())
    unresolved = []
    if not isinstance(documents.get("config"), dict):
        unresolved.append("configuration_resolution_required")
    if not isinstance(documents.get("market_state"), dict) or not documents["market_state"]:
        unresolved.append("market_state_resolution_required")
    else:
        unresolved.append("market_state_owner_qualification_required")
    alpha = documents.get("alpha")
    if not isinstance(alpha, dict) or not isinstance(alpha.get("per_ticker"), dict):
        unresolved.append("alpha_producer_result_required")
    else:
        unresolved.append("alpha_owner_qualification_required")
    return SectorAuxiliaryCapture(now, evidence, tuple(unresolved), documents, frames)
