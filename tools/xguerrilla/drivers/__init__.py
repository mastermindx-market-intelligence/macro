"""Unbound real-driver interfaces and pure shared helpers.

Both start and stop refuse before effects; choose refuses before selection.
Protocol conformance and synthetic method tests do not grant runtime authority."""
from __future__ import annotations

from .base import Driver, DriverError
from .cdp import CdpDriver
from .choose import BACKENDS, choose, peekaboo_available, resolve
from .peekaboo import PeekabooDriver
from .segment import MAX_CHUNK, MIN_CHUNK, chunk_delay_ms, segment

__all__ = [
    "BACKENDS",
    "CdpDriver",
    "Driver",
    "DriverError",
    "MAX_CHUNK",
    "MIN_CHUNK",
    "PeekabooDriver",
    "choose",
    "chunk_delay_ms",
    "peekaboo_available",
    "resolve",
    "segment",
]
