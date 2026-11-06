"""Read local parquet through pyarrow's native LocalFileSystem.

pandas opens a plain local path as a Python file object and hands that to
pyarrow, so buffer reads run as Python-backed arrow::py::PyBuffer objects on
Arrow's process-wide IO pool. When such a completion is delayed past the start
of interpreter finalization, its destructor's PyGILState_Ensure makes CPython
force pthread_exit for the pool worker, and the forced unwind ends in
std::terminate — SIGABRT, "terminate called without an active exception", after
the program's output is already written. The live-breadth poller hit this on
3/200 --once --offline census runs (the build-lane fixture tree measured 0/600
base — the rate is harness-dependent); PR #9043 measured the same hazard in the
news-universe builder at 63/1002 runs -> 0/1002 after reading natively.
use_threads=False and pre_buffer=False shrink the pool-thread census rather
than emptying it — on pandas 2.2, where read_parquet has no to_pandas_kwargs,
the to_pandas conversion still runs on the CPU pool. Callers own error mapping:
exceptions from pandas/pyarrow propagate unchanged.
"""
from __future__ import annotations

import functools
import inspect
from urllib.parse import unquote, urlparse


@functools.lru_cache(maxsize=1)
def _has_to_pandas_kwargs() -> bool:
    """True when this pandas read_parquet accepts to_pandas_kwargs (absent on
    pandas 2.2, present on 3.x — the only axis that differs across the floor).
    Signs the definition site, pandas.io.parquet.read_parquet: a monkeypatch of
    pd.read_parquet before the first call cannot cache the spy's signature."""
    from pandas.io.parquet import read_parquet

    return "to_pandas_kwargs" in inspect.signature(read_parquet).parameters


def read_parquet_native(path, *, columns=None):
    """Read one parquet file natively — never through a Python file object.

    Mirrors PR #9043's read exactly: a ``file:`` URI (any spelling argparse's
    type=Path can leave behind) is normalized to its decoded path, any other
    path form passes through unchanged; ``use_threads``/``pre_buffer`` are off
    and the to_pandas conversion is serial where pandas allows it. ``columns``
    is forwarded only when not None, so ``columns=[]`` reaches pandas as []
    (the index-only header read). No exception handling: errors propagate
    unchanged and callers keep their own fail-soft handling.
    """
    import pandas as pd
    import pyarrow.fs

    source = path
    parsed = urlparse(str(path))
    if parsed.scheme.lower() == "file":
        source = unquote(parsed.path)
    kwargs: dict[str, object] = {
        "filesystem": pyarrow.fs.LocalFileSystem(),
        "use_threads": False,
        "pre_buffer": False,
    }
    if _has_to_pandas_kwargs():
        kwargs["to_pandas_kwargs"] = {"use_threads": False}
    if columns is not None:
        kwargs["columns"] = columns
    return pd.read_parquet(source, **kwargs)
