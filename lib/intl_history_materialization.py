"""Internal current-reconstruction identity; never a disclosure or vintage grant.

The existing native writer keeps this descriptor in its existing country record.
It identifies a successful output and the actual input-matrix/method scope. This
is content-integrity metadata from the native producer, not a cryptographic
execution attestation. It neither attests unwitnessed provider origin nor makes
source values public.
"""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import stat

import pandas as pd
import numpy as np
from lib.intl_workspace_macro import _check_builtin_tree

SCHEMA = "intl.history_materialization.v1"
_HASH = re.compile(r"[0-9a-f]{64}")
_METHOD_MODULES = ("engine/intl_run.py", "engine/intl_inputs.py", "engine/intl_regime.py",
                   "engine/indicators.py", "engine/regime.py", "engine/axes.py")
_NUMBERS = {int, float, np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16,
            np.uint32, np.uint64, np.intp, np.uintp, np.longlong, np.ulonglong,
            np.float16, np.float32, np.float64, np.longdouble}
_FIELDS = {"schema", "market_id", "history_kind", "artifact_ref", "artifact_sha256",
           "materialized_at", "method", "method_ref", "universe", "universe_ref",
           "input_matrix", "output", "points_sha256", "provider_coverage",
           "original_known_at", "disclosure_authority"}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return sha256(_canonical(value)).hexdigest()


def _scores(frame):
    points = []
    for at, row in frame[["growth_score", "inflation_score"]].iterrows():
        values = []
        for value in row:
            if value is None or value is pd.NA:
                values.append(None)
            elif type(value) in _NUMBERS:
                number = float(value)
                if math.isnan(number):
                    values.append(None)
                    continue
                if not math.isfinite(number):
                    raise ValueError("nonfinite_history_score")
                values.append(number)
            else:
                raise ValueError("invalid_history_score")
        points.append([at.isoformat(), *values])
    return points


def _geometry(frame):
    return {"rows": len(frame), "first_observation_at": frame.index[0].isoformat() if len(frame) else None,
            "last_observation_at": frame.index[-1].isoformat() if len(frame) else None}


def capture_history_context(market_id, country, engine_config, frame, *, source_root):
    """Capture actual classifier input scope without changing or granting it."""
    if not re.fullmatch(r"[A-Z]{2}", market_id) or frame.empty:
        raise ValueError("invalid_history_context")
    method = {"kind": "current_reconstruction", "classifier": "engine.intl_regime.classify",
              "implementation": {name: sha256((Path(source_root) / name).read_bytes()).hexdigest()
                                 for name in _METHOD_MODULES},
              "engine_config": deepcopy(engine_config), "pandas_version": pd.__version__,
              "numpy_version": np.__version__}
    universe = {"market_id": market_id, "country_config": deepcopy(country),
                "input_columns": list(frame.columns)}
    matrix = {**_geometry(frame), "non_null_by_column": {
        str(column): int(frame[column].notna().sum()) for column in frame.columns},
        "content_hash_algorithm": "pandas_hash_pandas_object_sha256",
        "content_sha256": sha256(pd.util.hash_pandas_object(frame, index=True).values.tobytes()).hexdigest()}
    result = {"method": method, "universe": universe, "input_matrix": matrix}
    _canonical(result)
    return result


def read_stable_history_bytes(path, *, limit=64 * 1024 * 1024):
    """One bounded byte read, tied to the same open file and pathname."""
    def identity(stat):
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("history_artifact_too_large")
        data = stream.read(limit + 1)
        if (len(data) != before.st_size or len(data) > limit
                or identity(os.fstat(stream.fileno())) != identity(before)
                or identity(Path(path).stat()) != identity(before)):
            raise ValueError("history_artifact_changed")
    return data


def describe_history_write(market_id, frame, context, artifact_bytes, materialized_at):
    """Called only after the incumbent Parquet write succeeds and bytes are read."""
    from io import BytesIO
    stored = pd.read_parquet(BytesIO(artifact_bytes))
    if _scores(stored) != _scores(frame) or _geometry(stored) != _geometry(frame):
        raise ValueError("history_write_postimage_mismatch")
    descriptor = {
        "schema": SCHEMA, "market_id": market_id, "history_kind": "current_reconstruction",
        "artifact_ref": f"intl_regime/{market_id}_history.parquet",
        "artifact_sha256": sha256(artifact_bytes).hexdigest(), "materialized_at": materialized_at,
        **deepcopy(context), "method_ref": "sha256:" + _digest(context["method"]),
        "universe_ref": "sha256:" + _digest(context["universe"]),
        "output": _geometry(frame), "points_sha256": _digest(_scores(frame)),
        "provider_coverage": {"status": "unknown", "reason": "complete_response_materialization_witness_not_supplied"},
        "original_known_at": None, "disclosure_authority": "none",
    }
    return validate_history_materialization(descriptor, market_id, stored, artifact_bytes=artifact_bytes)


def validate_history_materialization(value, market_id, frame, *, artifact_bytes=None):
    """Verify the supplied native binding; absence never becomes permission."""
    try:
        if type(value) is not dict or set(value) != _FIELDS:
            raise ValueError
        _check_builtin_tree(value)
        if (type(frame) is not pd.DataFrame or type(frame.index) is not pd.DatetimeIndex
                or type(frame.columns) is not pd.Index or frame.index.hasnans
                or frame.index.has_duplicates or not frame.index.is_monotonic_increasing
                or frame.columns.has_duplicates
                or not {"growth_score", "inflation_score"}.issubset(frame.columns)):
            raise ValueError
        _canonical(value)
        if (value["schema"] != SCHEMA or value["market_id"] != market_id
                or value["history_kind"] != "current_reconstruction"
                or value["artifact_ref"] != f"intl_regime/{market_id}_history.parquet"
                or value["original_known_at"] is not None or value["disclosure_authority"] != "none"
                or value["provider_coverage"] != {"status": "unknown", "reason": "complete_response_materialization_witness_not_supplied"}):
            raise ValueError
        if not _HASH.fullmatch(value["artifact_sha256"]) or not _HASH.fullmatch(value["points_sha256"]):
            raise ValueError
        clock = datetime.fromisoformat(value["materialized_at"])
        if clock.utcoffset() is None:
            raise ValueError
        output = value["output"]
        if (type(output) is not dict or set(output) != {"rows", "first_observation_at", "last_observation_at"}
                or type(output["rows"]) is not int or output["rows"] < 0):
            raise ValueError
        method, universe, matrix = value["method"], value["universe"], value["input_matrix"]
        if (type(method) is not dict or set(method) != {"kind", "classifier", "implementation", "engine_config", "pandas_version", "numpy_version"}
                or method["kind"] != "current_reconstruction" or method["classifier"] != "engine.intl_regime.classify"
                or type(method["engine_config"]) is not dict or type(method["pandas_version"]) is not str
                or type(method["numpy_version"]) is not str
                or type(method["implementation"]) is not dict
                or set(method["implementation"]) != set(_METHOD_MODULES)
                or not all(type(h) is str and _HASH.fullmatch(h) for h in method["implementation"].values())):
            raise ValueError
        if (type(universe) is not dict or set(universe) != {"market_id", "country_config", "input_columns"}
                or universe["market_id"] != market_id or type(universe["country_config"]) is not dict
                or type(universe["input_columns"]) is not list or not universe["input_columns"]
                or not all(type(c) is str for c in universe["input_columns"])
                or len(set(universe["input_columns"])) != len(universe["input_columns"])):
            raise ValueError
        if (type(matrix) is not dict or set(matrix) != {"rows", "first_observation_at", "last_observation_at", "non_null_by_column", "content_hash_algorithm", "content_sha256"}
                or type(matrix["rows"]) is not int or matrix["rows"] <= 0
                or type(matrix["non_null_by_column"]) is not dict
                or set(matrix["non_null_by_column"]) != set(universe["input_columns"])
                or not all(type(n) is int and 0 <= n <= matrix["rows"] for n in matrix["non_null_by_column"].values())
                or matrix["content_hash_algorithm"] != "pandas_hash_pandas_object_sha256"
                or not _HASH.fullmatch(matrix["content_sha256"])
                or any(matrix[key] != _geometry(frame)[key] for key in ("rows", "first_observation_at", "last_observation_at"))):
            raise ValueError
        if (value["method_ref"] != "sha256:" + _digest(method)
                or value["universe_ref"] != "sha256:" + _digest(universe)
                or value["output"] != _geometry(frame) or value["points_sha256"] != _digest(_scores(frame))):
            raise ValueError
        if artifact_bytes is not None and value["artifact_sha256"] != sha256(artifact_bytes).hexdigest():
            raise ValueError
        return deepcopy(value)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        raise ValueError("invalid_history_materialization") from None
