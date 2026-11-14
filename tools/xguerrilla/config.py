"""Config wiring: where the persona rows live, and what a set of them may cost.

Nothing here decides behaviour — it resolves paths, hands back personas, and
refuses a set that the proxy pool cannot seat (§26.3: slots are exclusive).
"""
from __future__ import annotations

import os
from typing import Iterable, Mapping

import yaml

from . import net
from .persona import Persona, load_dir

HERE = os.path.dirname(os.path.abspath(__file__))
PERSONAS_DIR = os.path.join(HERE, "personas")
LINKS_PATH = os.path.join(HERE, "links.yml")
PROXIES_PATH = net.DEFAULT

ROLES = ("lead", "conversation", "broadcast")


def personas_dir(root: str | None = None) -> str:
    """Persona directory: ``personas/`` beside this module unless overridden."""
    return os.path.join(root, "personas") if root else PERSONAS_DIR


def links_path(root: str | None = None) -> str:
    """The one-link-slot-per-persona file (optional; absence means unconstrained)."""
    return os.path.join(root, "links.yml") if root else LINKS_PATH


def proxies_path(root: str | None = None) -> str:
    return os.path.join(root, "proxies.yml") if root else PROXIES_PATH


def load_link_slots(path: str | None = None) -> dict[str, str]:
    """Read ``slots: {handle: url}``. Missing file is not an error."""
    path = path or LINKS_PATH
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        doc = yaml.safe_load(fh) or {}
    slots = doc.get("slots") or {}
    return {str(k): str(v) for k, v in slots.items()}


def load_personas(dir: str | None = None, links: str | None = None) -> dict[str, Persona]:
    """Load persona rows, attaching each one's link slot.

    ``persona.load_dir`` owns parsing and per-row validation; this only adds the
    slot, which lives in a separate file so proxy/link inventory can change
    without touching a persona card.
    """
    personas = load_dir(dir or PERSONAS_DIR)
    slots = load_link_slots(links)
    for handle, persona in personas.items():
        if handle in slots:
            # Not a dataclass field: the row schema is fixed by persona.py.
            setattr(persona, "link_slot", slots[handle])
    return personas


def by_role(personas: Mapping[str, Persona], role: str) -> list[Persona]:
    return [p for p in personas.values() if p.role == role]


def check_capacity(personas: Mapping[str, Persona] | Iterable[Persona],
                   slots: list | None = None) -> list[str]:
    """Refuse a persona set the pool cannot seat 1:1.

    Returns violations; empty means the set is seatable. The mapping and the
    slot list both come from disk, so this runs before any account is touched.
    """
    if isinstance(personas, Mapping):
        rows = list(personas.values())
    else:
        rows = list(personas)
    handles = [p.handle for p in rows]

    duplicates = sorted({h for h in handles if handles.count(h) > 1})
    if duplicates:
        return [f"duplicate handles in the persona set: {', '.join(duplicates)}"]

    slots = net.load() if slots is None else slots
    if not slots:
        return ["no proxy slots configured — every child needs one exclusive slot"]
    if len(handles) > len(slots):
        return [f"{len(handles)} children on {len(slots)} slots — slots are exclusive"]

    try:
        net.assert_exclusive(handles, slots)
    except ValueError as exc:
        return [str(exc)]
    return []


def require_capacity(personas, slots: list | None = None) -> None:
    problems = check_capacity(personas, slots)
    if problems:
        raise ValueError("; ".join(problems))
