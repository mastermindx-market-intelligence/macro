"""Browser drivers: one narrow interface, two very different ways to press keys.

The worker loop never knows whether a keystroke went out as an accessibility
event at the window server or as a DevTools protocol frame. It asks the seam for
a driver (:func:`choose`), calls the twelve methods of :class:`base.Driver`, and
reads back a snapshot. Everything about *how* the browser is touched lives here.

    from xguerrilla.drivers import choose

    driver = choose("auto")            # peekaboo if installed, else CDP
    driver.start("/tmp/profile-3", proxy_url=proxy, headless=False)
    driver.goto("https://example.com")
    driver.type_plan(plan)
    print(driver.snapshot()["challenge"])
    driver.stop()
"""
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
