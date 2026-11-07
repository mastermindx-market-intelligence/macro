"""Proxy slots (§26.3): one slot, one child, for the life of the account.

The pool is a file so a child's identity outlives a restart, and so a slot's
reputation can be retired without touching the persona that sat on it.
"""
from __future__ import annotations
import os, zlib
from dataclasses import dataclass, field
import yaml

DEFAULT = os.path.join(os.path.dirname(__file__), "proxies.yml")


@dataclass(frozen=True)
class Slot:
    host: str
    port: int
    user: str
    password: str = field(repr=False)
    name: str

    @property
    def url(self) -> str:
        return f"http://{self.user}:{self.password}@{self.host}:{self.port}"

    def public(self) -> dict:
        """Loggable form — no password."""
        return {"slot": self.name, "host": self.host, "port": self.port, "user": self.user}


def load(path: str = DEFAULT) -> list[Slot]:
    with open(path) as fh:
        doc = yaml.safe_load(fh)
    out = []
    for i, line in enumerate(doc["inventory"]):
        host, port, user, pw = line.split(":")
        out.append(
            Slot(
                host,
                int(port),
                os.path.expandvars(user),
                os.path.expandvars(pw),
                f"{doc['pool']}-{i:02d}",
            )
        )
    if len(out) != len({s.host for s in out}):
        raise ValueError("duplicate proxy host in inventory")
    return out


def _probe(slots: list[Slot], handle: str, taken: set[str]) -> Slot:
    """Hash to a start point, then walk forward past slots already consumed."""
    start = zlib.crc32(handle.encode()) % len(slots)
    for step in range(len(slots)):
        slot = slots[(start + step) % len(slots)]
        if slot.name not in taken:
            return slot
    raise ValueError("pool exhausted — every slot is already consumed")


def assign(slots: list[Slot], handle: str) -> Slot:
    """Stable preferred slot for one handle, ignoring other children.

    Use bind() to allocate a whole cohort; this alone can collide.
    """
    return slots[zlib.crc32(handle.encode()) % len(slots)]


def bind(slots: list[Slot], handles: list[str]) -> dict[str, Slot]:
    """Allocate the cohort deterministically, one slot per child, no collisions."""
    assert_exclusive(handles, slots)
    taken: set[str] = set()
    out: dict[str, Slot] = {}
    for handle in sorted(handles):
        slot = _probe(slots, handle, taken)
        taken.add(slot.name)
        out[handle] = slot
    return out


def assert_exclusive(handles: list[str], slots: list[Slot]) -> None:
    if len(handles) > len(slots):
        raise ValueError(f"{len(handles)} children on {len(slots)} slots — slots are exclusive")
    if len(set(handles)) != len(handles):
        raise ValueError("duplicate handle in cohort")
