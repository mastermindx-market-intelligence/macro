"""Backend inspection and an unavailable activation factory.

resolve and peekaboo_available describe local selection only. choose refuses
before any probe or fallback; no backend is an alternative admission route."""
from __future__ import annotations

import shutil

from .base import Driver, DriverError
from ..runtime_boundary import refuse_runtime
from .cdp import CdpDriver
from .peekaboo import PeekabooDriver

__all__ = ["BACKENDS", "choose", "resolve"]

#: Accepted ``backend`` values, most-specific last.
BACKENDS = ("auto", "peekaboo", "cdp")


def peekaboo_available(binary: str = "peekaboo") -> bool:
    """True when the ``peekaboo`` CLI is on PATH (the precondition for OS typing)."""
    return shutil.which(binary) is not None


def resolve(backend: str = "auto", headless: bool = False) -> str:
    """Return the concrete backend name ``choose()`` would pick, without building it."""
    name = str(backend or "auto").strip().lower()
    if name not in BACKENDS:
        raise DriverError(f"unknown backend {backend!r}; pick one of {', '.join(BACKENDS)}")
    if name == "auto":
        if headless:
            return "cdp"
        return "peekaboo" if peekaboo_available() else "cdp"
    if name == "peekaboo" and headless:
        raise DriverError("headless=True cannot use peekaboo; it needs a real window (use 'cdp')")
    return name


def choose(backend: str = "auto", headless: bool = False) -> Driver:
    """Refuse unbound activation before probing or choosing a fallback."""
    refuse_runtime("driver.choose")
