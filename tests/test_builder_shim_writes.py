"""Selected CI entrypoint for page-write and AI Brief freshness contracts.

The existing ``data-base-shim`` logical job invokes this exact path.  The
established builder tests and the new AI Brief cases live in non-collectable
companion modules so the normal full-suite walk does not execute either family
twice.  This entrypoint imports only tests and fixture markers into its own
namespace; pytest therefore runs them once under the already-owned job.
"""
from __future__ import annotations

import runpy
from pathlib import Path

_CASE_MODULES = (
    "builder_shim_writes_cases.py",
    "aibrief_live_refresh_cases.py",
    "aibrief_refresh_injection_position_cases.py",
    "aibrief_freshness_client_cases.py",
)

for _case_module in _CASE_MODULES:
    _namespace = runpy.run_path(str(Path(__file__).with_name(_case_module)))
    for _name, _value in _namespace.items():
        _is_fixture = (
            hasattr(_value, "_pytestfixturefunction")
            or hasattr(_value, "_fixture_function_marker")
        )
        if not (_name.startswith("test_") or _is_fixture):
            continue
        if _name in globals():
            raise RuntimeError(f"duplicate collected test/fixture name: {_name}")
        globals()[_name] = _value
