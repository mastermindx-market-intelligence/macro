"""Persona rows: the only place a child's behaviour may live (§26.2).

Anything hard-coded in another module and not read from here is a bug.
"""
from __future__ import annotations
import os, random
from dataclasses import dataclass, field, asdict
import yaml

SPEED_CLASSES = {
    "slow":    dict(median_ms=310.0, cv=0.42, error_rate=0.05, hesitation_prob=0.06, paste_prob=0.05),
    "average": dict(median_ms=185.0, cv=0.38, error_rate=0.026, hesitation_prob=0.045, paste_prob=0.22),
    "fluent":  dict(median_ms=145.0, cv=0.34, error_rate=0.013, hesitation_prob=0.032, paste_prob=0.30),
}

CASING = ("lower", "sentence", "mixed", "lower_sometimes")


@dataclass
class Persona:
    handle: str
    cell: str
    role: str = "broadcast"          # broadcast | conversation | lead
    beat: str = ""
    city: str = "Austin"
    tz: str = "America/Chicago"
    # §26.5 — drawn at creation, stable for the account's life
    speed_class: str = "average"
    typo_rate_mult: float = 1.0
    revision_prob: float = 0.34
    pause_mult: float = 1.0
    # §25.6 — free properties, but only free once they are here
    hours: tuple = (8, 23)
    idle_day_p: float = 0.07
    casing: str = "sentence"
    max_chars: int = 240
    links_per_week: int = 1
    hashtags_max: int = 1
    pet_phrases: list = field(default_factory=list)
    opinions: list = field(default_factory=list)
    doesnt_care_about: list = field(default_factory=list)
    actions_per_day: int = 18
    seed: int = 0

    def rng(self, salt: str = "") -> random.Random:
        return random.Random(f"{self.handle}:{self.seed}:{salt}")

    @property
    def speed(self) -> dict:
        return SPEED_CLASSES[self.speed_class]

    def validate(self) -> list[str]:
        errs = []
        if self.speed_class not in SPEED_CLASSES:
            errs.append(f"speed_class {self.speed_class!r} unknown")
        if self.casing not in CASING:
            errs.append(f"casing {self.casing!r} unknown")
        if not (0 <= self.hours[0] < self.hours[1] <= 24):
            errs.append("hours must be an increasing pair inside 0..24")
        if self.max_chars > 280:
            errs.append("max_chars above the platform ceiling")
        if self.role not in ("broadcast", "conversation", "lead"):
            errs.append(f"role {self.role!r} unknown")
        if self.pause_mult <= 0 or self.typo_rate_mult <= 0:
            errs.append("multipliers must be positive")
        return errs

    def needs_full_treatment(self) -> bool:
        """§26.1: full §25 treatment, or profile-and-cadence only."""
        return self.role in ("lead", "conversation")


def load_dir(path: str) -> dict[str, Persona]:
    out, errs = {}, []
    for name in sorted(os.listdir(path)):
        if not name.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(path, name)) as fh:
            p = Persona(**yaml.safe_load(fh))
        e = p.validate()
        if e:
            errs.append((name, e))
        out[p.handle] = p
    if errs:
        raise ValueError(f"invalid persona rows: {errs}")
    return out
