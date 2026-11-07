"""Shared fixtures for the xguerrilla regression suite.

Everything here is either pure Python or rooted in pytest's ``tmp_path``: no
network, no live browser, no rail, no real profile store. That is deliberate —
the statistical laws in ``test_typing.py`` and the slot laws in ``test_net.py``
have to be checkable on a laptop that has never run a child.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# tests/ -> xguerrilla/ -> tools/ ; the package is imported as ``xguerrilla``.
TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from xguerrilla import net  # noqa: E402
from xguerrilla import profiles  # noqa: E402
from xguerrilla.persona import Persona  # noqa: E402

# A post long enough to expose per-character rhythm (>= 200 chars) and written
# the way a small operator actually writes: one paragraph, no lists, no emoji,
# no headline punctuation. Keep it that way — short texts and texts full of
# clause breaks change the interval distribution enough to move the audit.
SAMPLE_TEXT = (
    "the austin market is not slowing down it is splitting in two and the "
    "operators who answer the phone are the ones quietly taking share while "
    "the rest keep buying ads into a dead funnel we cut spend in june and the "
    "calls went up not down"
)

# typo_rate_mult per speed class, calibrated against the shipped correction
# model on a 235-character clean paragraph. The correction model now guarantees
# its own floor of one notice-and-fix per 100 typed characters, so no class
# needs to be boosted to clear the audit: at the shipped default (1.0. 1.0, 1.0)
# the classes still separate on how much they revise - over seeds 0-19 and the
# 235-character post, mean deletions are 9.1 (slow), 5.6 (average), 3.8
# (fluent). The boost that used to live here (average 2.0, fluent 3.0) lifted
# fluent to a mean of 7.6, above the base rates' own ordering, which put
# `average` ahead of `slow` and flattened the class distinction. Multipliers are
# kept at 1.0 and exist so a test can pass an explicit one; re-measure if the
# correction model changes.
FLOOR_MULT = {"slow": 1.0, "average": 1.0, "fluent": 1.0}

# The six keys every child needs before it is allowed to run, as described in
# RUNBOOK.md. Kept here so the runbook and the suite can be checked against the
# same list.
HANDLE_PREFIX = "kid"


@pytest.fixture
def sample_text() -> str:
    """A 200+ character post that must survive every typing law."""
    return SAMPLE_TEXT


@pytest.fixture
def sample_persona() -> Persona:
    """A calibrated ``average`` persona; deterministic for a fixed seed."""
    return Persona(
        handle="kid.audit",
        cell="ATX-04",
        speed_class="average",
        typo_rate_mult=FLOOR_MULT["average"],
        seed=11,
    )


@pytest.fixture
def persona_factory():
    """Build personas by class and seed, with the floor calibration applied."""

    def make(
        speed_class: str = "average",
        seed: int = 11,
        typo_rate_mult: float | None = None,
        handle: str = "kid.audit",
        cell: str = "ATX-04",
    ) -> Persona:
        return Persona(
            handle=handle,
            cell=cell,
            speed_class=speed_class,
            typo_rate_mult=FLOOR_MULT[speed_class] if typo_rate_mult is None else typo_rate_mult,
            seed=seed,
        )

    return make


@pytest.fixture
def tmp_profile(tmp_path):
    """A throwaway profile store with one initialised handle.

    Mirrors what ``xguerrilla snapshot``/``restore`` operate on, so profile
    tests can run without touching ``~/.xguerrilla`` or a child's real store.
    """
    store = profiles.Store(tmp_path / "store")
    handle = "kid.audit"
    store.init(
        handle,
        slot="bartproxies-us-16-04",
        chrome_version="142.0.7444.60",
        notes="regression fixture — safe to delete",
    )
    return SimpleNamespace(
        store=store,
        handle=handle,
        root=tmp_path / "store",
        profile_dir=Path(store.handle_dir(handle)),
    )


@pytest.fixture(scope="session")
def net_slots():
    """The shipped slot table (no network: this only parses proxies.yml)."""
    slots = net.load()
    if not slots:
        pytest.skip("no slots configured in proxies.yml")
    return slots


@pytest.fixture(scope="session")
def _net_module():
    return net
