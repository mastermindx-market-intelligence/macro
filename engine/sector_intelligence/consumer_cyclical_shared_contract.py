"""Cyclical review gate for the shared curation-assertion contract.

The projection stays a pure document composer. This module is the only Cyclical
probe of the shared contract, and it is not imported by that composer. A missing
module, or a module that lacks both callables, raises a Cyclical-owned refusal
instead of returning ``None`` or borrowing another vertical's refusal type.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable


SHARED_CONTRACT_MODULE = "engine.theme_graph.curation_assertion"


class ConsumerCyclicalResearchRefusal(Exception):
    """A typed, Cyclical-owned refusal. ``code`` is ``shared_contract_unavailable``."""

    CODES: tuple[str, ...] = ("shared_contract_unavailable",)

    def __init__(self, code: str, detail: str = "") -> None:
        if code not in self.CODES:
            raise ValueError(f"unknown refusal code {code!r}")
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def shared_contract() -> Callable[..., Any]:
    """Return ``validate_assertion`` when both shared callables exist.

    The import target is a string literal, not a static import and not a name
    lookup: the shared module is absent on main, and a name argument would be
    an opaque dynamic import. ``import_module`` raises ImportError both when
    the module is absent and when it resolves and then fails to import.
    """
    try:
        shared = importlib.import_module("engine.theme_graph.curation_assertion")
    except ImportError as exc:
        raise ConsumerCyclicalResearchRefusal(
            "shared_contract_unavailable",
            f"{SHARED_CONTRACT_MODULE} is not importable on this checkout ({exc.__class__.__name__}); "
            "the shared owner has not delivered it to main",
        ) from None
    if not callable(getattr(shared, "validate_assertion", None)) or not callable(
        getattr(shared, "curation_revision", None)
    ):
        raise ConsumerCyclicalResearchRefusal(
            "shared_contract_unavailable",
            f"{SHARED_CONTRACT_MODULE} does not expose both validate_assertion and curation_revision",
        )
    return shared.validate_assertion
