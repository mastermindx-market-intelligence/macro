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
    store = profiles.SimulationProfileStore(tmp_path / "store")
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
def net_slots(synthetic_proxy_path):
    """Synthetic slots parsed by the actual loader; no private-path fallback."""
    return net.load(str(synthetic_proxy_path))


@pytest.fixture(scope="session")
def _net_module():
    return net

@pytest.fixture(scope="session")
def synthetic_proxy_path(tmp_path_factory):
    """Explicit fake pool; the actual YAML parser remains under test."""
    import yaml
    root = tmp_path_factory.mktemp("xg-synthetic-slots")
    path = root / "synthetic-slots.yml"
    path.write_text(yaml.safe_dump({
        "pool": "synthetic-pool",
        "inventory": [
            f"proxy-{i:02d}.invalid:{10000+i}:fake-user:fake-password-{i:02d}"
            for i in range(16)
        ],
    }))
    return path


@pytest.fixture(scope="session")
def synthetic_xg_config(tmp_path_factory):
    """Five explicit schema specimens, never the deployed persona roster."""
    import yaml
    root = tmp_path_factory.mktemp("xg-synthetic-rows")
    rows = root / "rows"
    rows.mkdir()
    handles = ["wren.mp4", "harperbuilds", "lowlit.austin", "mila.lifts", "desk.and.dusk"]
    roles = ["lead", "conversation", "conversation", "lead", "broadcast"]
    speeds = ["fluent", "average", "slow", "average", "fluent"]
    casing = ["lower", "lower_sometimes", "mixed", "sentence", "sentence"]
    lengths = [140, 220, 180, 160, 200]
    hours = [[8, 23], [7, 22], [6, 21], [5, 20], [9, 24]]
    beats = ["camera exposure", "coffee grinder", "patio evenings", "squat progression", "desk reading"]
    phrases = [
        ["flash on", "one more frame", "bar light"],
        ["grind finer", "tastes like the bag smells", "dial it in"],
        ["on the patio", "one drink", "the line was gone"],
        ["legs day again", "one more set", "knees felt fine"],
        ["lamp on", "phone face down", "page one"],
    ]
    for i, handle in enumerate(handles):
        row = {
            "handle": handle, "cell": f"synthetic-cell-{i}", "role": roles[i],
            "beat": beats[i], "city": f"synthetic-city-{i}", "tz": "America/Chicago",
            "speed_class": speeds[i], "casing": casing[i], "max_chars": lengths[i],
            "hours": hours[i], "idle_day_p": 0.0, "seed": i + 11,
            "pet_phrases": phrases[i],
            "opinions": [f"{beats[i]} needs patience", f"{beats[i]} takes practice",
                         f"{beats[i]} works slowly"],
            "doesnt_care_about": [f"synthetic-topic-{i}-a", f"synthetic-topic-{i}-b"],
            "links_per_week": 3, "actions_per_day": 18,
        }
        (rows / f"row-{i}.yml").write_text(yaml.safe_dump(row))
    links = root / "synthetic-links.yml"
    links.write_text(yaml.safe_dump({
        "slots": {h: "https://links.example.com/xg/" + h.replace(".", "-") for h in handles}
    }))
    return SimpleNamespace(personas=rows, links=links)
