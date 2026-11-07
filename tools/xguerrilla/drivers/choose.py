"""Backend selection (§26.6): the one place the harness decides where keys land.

The default is OS-level typing because that is what the site actually sees — a
real Chrome window receiving real key events from the window server. CDP is the
fallback: it is the only option when there is no window at all (``headless``)
and the right tool when a slot needs throughput rather than fidelity.

Nothing above this module may branch on backend names; it asks for a
:class:`..base.Driver` and the seam decides.
"""
from __future__ import annotations

import shutil

from .base import Driver, DriverError
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
    """Build and return the driver for ``backend``.

    ``auto`` picks :class:`PeekabooDriver` when the CLI is installed and
    :class:`CdpDriver` otherwise; ``headless=True`` always means CDP, since there
    is no window to type into. The caller still owns ``start()``/``stop()``.
    """
    name = resolve(backend, headless)
    if name == "peekaboo":
        return PeekabooDriver()
    return CdpDriver()
