"""Unavailable binding to the incumbent runtime owners.

This module grants no permission and has no activation switch. A source-qualified
adapter must bind the actual account, approved item, original holder, receipts
and profile owner before a future change can implement these operations.
"""
from __future__ import annotations

from typing import NoReturn


class RuntimeBindingUnavailable(RuntimeError):
    code = "runtime_binding_unavailable"

    def __init__(self, operation: str):
        self.operation = operation
        super().__init__(
            f"{self.code}: {operation} has no incumbent account/action/profile binding"
        )


def refuse_runtime(operation: str) -> NoReturn:
    raise RuntimeBindingUnavailable(operation)
