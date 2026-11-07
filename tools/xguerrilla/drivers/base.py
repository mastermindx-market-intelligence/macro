"""The driver seam (§26.6): a dumb executor the worker loop can swap out.

A driver receives a keystroke plan and reports facts. It decides nothing: no
persona logic, no scheduling, no retries of its own. Two backends implement the
same twelve calls:

``PeekabooDriver``
    Types at the window server through the ``peekaboo`` CLI. Preferred on the
    runtime box, because OS-level keystrokes are what the site actually sees.

``CdpDriver``
    Drives Chrome over the DevTools Protocol with Playwright. Fallback for
    headless volume, where there is no window to post keystrokes at.

Everything shared between them lives here: the error type, the challenge
detector (one regex, case-insensitive and whitespace tolerant, so a page that
renders ``Unusual\nActivity`` is still caught), and the ``'x,y'`` coordinate
parser.
"""
from __future__ import annotations

import math
import os
import re
from typing import Protocol, runtime_checkable

try:  # package import — tools.xguerrilla.drivers.base
    from ..typing import Key, to_cdp
except ImportError:  # pragma: no cover - imported straight from the drivers dir
    import importlib.util as _ilu

    _PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _SPEC = _ilu.spec_from_file_location("_xg_typing", os.path.join(_PKG_DIR, "typing.py"))
    _MOD = _ilu.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(_MOD)  # type: ignore[union-attr]
    Key = _MOD.Key
    to_cdp = _MOD.to_cdp

__all__ = [
    "CHALLENGE_RE",
    "Driver",
    "DriverError",
    "Key",
    "collapse",
    "is_challenge",
    "parse_coords",
    "to_cdp",
]

#: Words a wall or interstitial shows. Case-insensitive; ``\s+`` so the banner
#: that wraps between "unusual" and "activity" is still a hit.
CHALLENGE_RE = re.compile(
    r"unusual\s+activity|verif(?:y|ication)|suspicious|challenge|arkose",
    re.IGNORECASE,
)

_COORD_RE = re.compile(r"^\s*(-?\d{1,5}(?:\.\d+)?)\s*[,; ]\s*(-?\d{1,5}(?:\.\d+)?)\s*$")


class DriverError(RuntimeError):
    """A driver call failed. Carries the backend's own words where it can."""


def collapse(text: str) -> str:
    """Fold whitespace and case so labels match like a human reads them."""
    return re.sub(r"\s+", " ", (text or "")).strip().casefold()


def is_challenge(text: str) -> bool:
    """True when ``text`` shows a verification wall, challenge, or block page."""
    return bool(text) and CHALLENGE_RE.search(text) is not None


def parse_coords(target: str) -> tuple[float, float] | None:
    """Parse ``'x,y'`` into a point; ``None`` when the target is a label.

    Accepts ``'120,240'``, ``'120, 240'`` and ``'120 240'`` — the three shapes
    that show up in hand-written step files.
    """
    if not isinstance(target, str):
        return None
    match = _COORD_RE.match(target)
    if not match:
        return None
    x, y = float(match.group(1)), float(match.group(2))
    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    return x, y


@runtime_checkable
class Driver(Protocol):
    """The twelve calls a backend must provide. Nothing else is assumed."""

    name: str

    def start(self, profile_dir: str, proxy_url: str, headless: bool) -> None:
        """Launch Chrome bound to ``profile_dir`` and return once it can accept input."""
        ...

    def goto(self, url: str) -> None:
        """Navigate the active tab to ``url`` and wait for the document."""
        ...

    def snapshot(self) -> dict:
        """Return ``{url, title, signed_in, challenge}`` for the active window."""
        ...

    def find(self, target: str) -> dict:
        """Resolve ``target`` (label or ``'x,y'``) to a box without acting on it."""
        ...

    def click(self, target: str) -> None:
        """Click an accessibility label or raw ``'x,y'`` coordinates."""
        ...

    def type_plan(self, keys: list[Key]) -> None:
        """Type a persona keystroke plan, chunked and paced as planned."""
        ...

    def paste(self, text: str, target: str | None = None) -> str:
        """Paste ``text`` into the focused field; read ``target`` back when given.

        Returns the value the page reports after the paste, or ``""`` when no
        target was named. A backend that cannot read a field back must raise
        rather than return a value it did not observe.
        """
        ...

    def key(self, name: str) -> None:
        """Press one named key or chord, e.g. ``enter`` or ``cmd+enter``."""
        ...

    def screenshot(self, path: str) -> str:
        """Write a PNG of the active window to ``path`` and return the path."""
        ...

    def stop(self) -> None:
        """Release the browser, the profile lock, and the driver's own handles."""
        ...
