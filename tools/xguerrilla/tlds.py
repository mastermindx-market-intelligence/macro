"""Versioned TLD set for the link gate — real membership, not label shape.

The general scheme-less-host alternative of ``validators._LINK_TOKEN`` fires
on any dotted word unless its trailing label is a member of this set. The set
is data (``tlds.txt`` beside this module), not a regex literal: the file
carries its IANA source version and a sha256 pin over the label block, which
this module recomputes at import — a file that drifted from its own pin
refuses to load, loudly, so the set cannot rot silently.

Refresh procedure (never hand-edit the label lines):

    curl -fsSL https://data.iana.org/TLD/tlds-alpha-by-domain.txt \\
      -o /tmp/tlds-alpha.txt
    python3 tools/xguerrilla/refresh_tlds.py /tmp/tlds-alpha.txt \\
      tools/xguerrilla/tlds.txt

The reserved additions (EXAMPLE/INVALID/LOCALHOST/TEST/ONION) and the
TLD-vs-file-extension collision policy (ZIP/MOV/APP/PY/MD tails fire;
JS/TXT/EXE/HTML/JSON tails do not) are documented in ``tlds.txt`` and pinned
by ``tests/test_validators.py``.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

_DATA_PATH = Path(__file__).with_name("tlds.txt")
_PIN_RE = re.compile(r"^# iana-labels-sha256: ([0-9a-f]{64})\s*$", re.MULTILINE)


def _labels_between(text: str, begin: str, end: str) -> list[str]:
    try:
        block = text.split(begin, 1)[1].split(end, 1)[0]
    except IndexError:
        raise RuntimeError(
            f"{_DATA_PATH.name}: missing {begin!r}/{end!r} markers — "
            "regenerate it with refresh_tlds.py rather than editing by hand"
        ) from None
    return [line.strip() for line in block.splitlines() if line.strip()]


def _load(path: Path = _DATA_PATH) -> frozenset[str]:
    text = path.read_text(encoding="utf-8")
    pin = _PIN_RE.search(text)
    if pin is None:
        raise RuntimeError(
            f"{path.name}: no '# iana-labels-sha256:' pin — regenerate "
            "it with refresh_tlds.py"
        )
    iana = _labels_between(text, "# begin-iana", "# end-iana")
    if not iana:
        raise RuntimeError(f"{path.name}: empty IANA label block")
    digest = hashlib.sha256(
        "".join(label + "\n" for label in iana).encode("utf-8")
    ).hexdigest()
    if digest != pin.group(1):
        raise RuntimeError(
            f"{path.name}: label block sha256 {digest} does not match "
            f"its pin {pin.group(1)} — the data drifted; regenerate with "
            "refresh_tlds.py and move the sentinel tests deliberately"
        )
    reserved = _labels_between(text, "# begin-reserved", "# end-reserved")
    return frozenset(iana) | frozenset(reserved)


#: Registered TLDs (IANA) plus reserved pseudo-TLDs, uppercase.
TLDS = _load()


def is_tld(label: str) -> bool:
    """True iff ``label`` names a TLD or reserved pseudo-TLD (case-insensitive)."""
    return (label or "").strip().upper() in TLDS
