"""Regression laws for ``xguerrilla.typing``.

Each test states a law rather than a snapshot, and its failure message says what
the break means for a child in the field. No law is ``xfail`` any more: the
replay-equality gate and the strict-interval law both hold on the shipped code,
and a marker only comes back if a law is knowingly broken again.
"""

from __future__ import annotations

import random
import statistics

import pytest

from xguerrilla import typing as T
from xguerrilla.persona import SPEED_CLASSES

CLASSES = ("slow", "average", "fluent")
SEEDS = tuple(range(10))

# Two post lengths the replay laws run against: a short one that puts most of
# its words at the typo boundary, and the 235-character suite sample.
SHORT_POST = "pilot smoke test typing across the harness layers tonight and checking every word lands"[:94]

# The audit's own band, read from typing.assert_natural.
BAND_LO, BAND_HI = 0.5, 2.2


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

# Virtual key codes that carry no character of their own.
_MODIFIER_VKS = {16, 160, 20}      # shift, rshift, capslock


def _replay(cdp: list[dict]) -> str:
    """Replay a CDP log the way a page would: backspace pops, keys append."""
    typed: list[str] = []
    shifted = False
    for entry in cdp:
        vk = entry["vk"]
        if vk in _MODIFIER_VKS:
            shifted = True
            continue
        if vk == 8:
            if typed:
                typed.pop()
            continue
        key = entry["key"]
        if len(key) == 1:
            typed.append(key.upper() if shifted else key)
        shifted = False
    return "".join(typed)


def _band(persona) -> tuple[float, float]:
    centre = persona.speed["median_ms"] * persona.pause_mult
    return centre * BAND_LO, centre * BAND_HI


def _medians(text: str, persona_factory, speed_class: str, seeds=SEEDS) -> list[float]:
    out = []
    for seed in seeds:
        persona = persona_factory(speed_class, seed=seed)
        out.append(T.assert_natural(T.plan(text, persona), persona)["median"])
    return out


def _fixed_delay_clock(text: str, base_ms: float = 120.0, jitter_ms: float = 18.0,
                       stall_ms: float = 40.0, every: int = 12) -> list[T.Key]:
    """The emulator this suite exists to catch.

    A fixed ``base_ms`` beat, a little uniform jitter on top, one hiccup every
    ``every`` keystrokes, and no corrections at all. It looks fine on a
    stopwatch and reads like a machine in the thread: the spread is far too
    tight for a hand, and the shape leans the wrong way. The hiccup is what
    makes the skew deterministically negative instead of hovering around zero —
    without it a symmetric jitter can squeak past the skew clause on a lucky
    run, which is exactly the flakiness a regression suite must not have.
    """
    rng = random.Random(0)
    keys: list[T.Key] = []
    t = 0.0
    for i, ch in enumerate(text):
        delta = base_ms - stall_ms if (i and i % every == 0) else base_ms + rng.uniform(0.0, jitter_ms)
        t += delta
        keys.append(T.Key(t, "char", ch, shift=ch.isupper()))
    return keys


# ---------------------------------------------------------------------------
# 1. the audit passes on real plans
# ---------------------------------------------------------------------------

def test_sample_text_is_long_enough(sample_text):
    """The suite's premise: a 200+ character post, not a two-line reply."""
    assert len(sample_text) >= 200


@pytest.mark.parametrize("speed_class", CLASSES)
def test_natural_audit_passes_for_ten_seeds(speed_class, sample_text, persona_factory):
    """A real plan on a real post comes out clean, at every class and seed.

    Ten seeds is the plan review's sample. A single red seed means the class's
    cadence table and the typing model have drifted apart, and every child on
    that class is now audibly rhythmic.
    """
    for seed in SEEDS:
        persona = persona_factory(speed_class, seed=seed)
        result = T.assert_natural(T.plan(sample_text, persona), persona)
        assert result["ok"] is True, (
            f"{speed_class} seed {seed} failed the naturalness audit: "
            f"{result['problems']} (median={result['median']:.0f}ms "
            f"cv={result['cv']:.2f} skew={result['skew']:.2f} "
            f"deletes/100={result['deletes_per_100']:.2f})"
        )
        assert result["problems"] == [], (
            f"{speed_class} seed {seed} reported {result['problems']} with ok=True"
        )


# ---------------------------------------------------------------------------
# 2. the audit bites: fixed delay + jitter must be rejected
# ---------------------------------------------------------------------------

def test_audit_rejects_a_fixed_delay_clock(sample_text, persona_factory):
    """Fixed 120 ms + uniform jitter must fail on skew **and** on cv.

    The persona is ``fluent`` (band centre 145 ms) on purpose: the clock's
    median of ~129 ms sits comfortably inside that band, so the rejection cannot
    be blamed on cadence. The two clauses that fire are the load-bearing ones —
    the spread is too tight (cv) and the shape is not right-skewed (skew). If
    this test ever passes, ``assert_natural`` can no longer tell a hand from a
    loop, and every other assertion in this file is worthless.
    """
    persona = persona_factory("fluent", seed=0)
    result = T.assert_natural(_fixed_delay_clock(sample_text), persona)

    assert result["ok"] is False, "a fixed-delay clock passed the naturalness audit"
    joined = " | ".join(result["problems"])
    assert "cv" in joined, f"the clock was not rejected on spread: {result['problems']}"
    assert "skew" in joined, f"the clock was not rejected on shape: {result['problems']}"
    assert not 0.6 <= result["cv"] <= 1.2, f"cv {result['cv']:.2f} is inside the band"
    assert result["skew"] <= 0, f"skew {result['skew']:.2f} should not be positive"
    assert result["deletes_per_100"] < 1.0
    lo, hi = _band(persona)
    assert lo <= result["median"] <= hi, (
        "the rejection must not be explained by the median clause"
    )


def test_audit_passes_the_real_plan_with_the_same_persona(sample_text, persona_factory):
    """Same persona and text, real generator: the rejection above was earned."""
    persona = persona_factory("fluent", seed=0)
    assert T.assert_natural(T.plan(sample_text, persona), persona)["ok"] is True


# ---------------------------------------------------------------------------
# 3. determinism
# ---------------------------------------------------------------------------

def test_plan_is_deterministic_for_a_fixed_persona_seed(sample_text, persona_factory):
    """Two runs of one seeded persona produce identical keystrokes.

    Replayability is what makes a support ticket actionable: "kid.audit seed 21"
    has to mean the same thing on the operator's machine as in the log.
    """
    first = T.plan(sample_text, persona_factory("average", seed=21))
    second = T.plan(sample_text, persona_factory("average", seed=21))
    assert [(k.t, k.kind, k.text, k.shift) for k in first] == \
           [(k.t, k.kind, k.text, k.shift) for k in second]


def test_plans_differ_across_seeds(sample_text, persona_factory):
    """Different seeds do not type the same post the same way.

    A regression here means the seed stopped reaching the generator, so every
    child in a cell would share one rhythm — the loudest fingerprint we have.
    """
    a = T.plan(sample_text, persona_factory("average", seed=21))
    b = T.plan(sample_text, persona_factory("average", seed=22))
    assert [(k.t, k.kind, k.text) for k in a] != [(k.t, k.kind, k.text) for k in b]


# ---------------------------------------------------------------------------
# 4. cadence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("speed_class", CLASSES)
def test_median_interval_sits_inside_the_class_band(speed_class, sample_text, persona_factory):
    """The class table is the contract, with ``pause_mult`` on top.

    Checked against ``SPEED_CLASSES`` directly (not through the audit) so a
    change to either the table or the audit shows up here first.
    """
    for seed in SEEDS:
        persona = persona_factory(speed_class, seed=seed)
        lo, hi = _band(persona)
        median = T.assert_natural(T.plan(sample_text, persona), persona)["median"]
        assert lo <= median <= hi, (
            f"{speed_class} seed {seed}: median {median:.0f}ms outside "
            f"{lo:.0f}-{hi:.0f}ms (centre {persona.speed['median_ms']:.0f}ms)"
        )


def test_class_table_is_ordered(sample_text, persona_factory):
    """The shipped table and the observed medians agree: fluent < average < slow."""
    table = {c: SPEED_CLASSES[c]["median_ms"] for c in CLASSES}
    assert table["fluent"] < table["average"] < table["slow"], f"class table: {table}"
    observed = {c: statistics.median(_medians(sample_text, persona_factory, c)) for c in CLASSES}
    assert observed["fluent"] < observed["average"] < observed["slow"], f"observed: {observed}"


def test_fluent_is_faster_than_slow(sample_text, persona_factory):
    """A fluent child types the same post faster than a slow one, seed by seed."""
    fluent = max(_medians(sample_text, persona_factory, "fluent", seeds=range(5)))
    slow = min(_medians(sample_text, persona_factory, "slow", seeds=range(5)))
    assert fluent < slow, f"fluent {fluent:.0f}ms is not faster than slow {slow:.0f}ms"


# ---------------------------------------------------------------------------
# 5. the correction floor (one deletion per 100 characters)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("speed_class", CLASSES)
def test_every_plan_over_100_characters_contains_a_deletion(speed_class, sample_text, persona_factory):
    """Zero-revision prose is the clearest machine tell there is.

    Holds for every class and seed at the multipliers in ``conftest.FLOOR_MULT``.
    The shipped default multiplier is pinned separately below, because it is a
    different constant even though it currently equals 1.0 for every class.
    """
    assert len(sample_text) > 100
    for seed in SEEDS:
        persona = persona_factory(speed_class, seed=seed)
        stats = T.stats(T.plan(sample_text, persona))
        assert stats["deletes"] >= 1, (
            f"{speed_class} seed {seed}: {len(sample_text)} characters with zero "
            f"corrections (multiplier {persona.typo_rate_mult})"
        )


def test_default_multiplier_still_revises(sample_text, persona_factory):
    """The law as written, with no calibration, is what we actually want.

    Formerly ``xfail``: at the shipped ``typo_rate_mult=1.0`` the fluent class
    under-fired (7 of 20 seeds typed the 235-character post with zero
    deletions). It passes now that a mistype emits exactly one backspace per
    wrong character and the plan guarantees its own correction floor on posts
    over 100 characters, so the marker was deleted rather than left to rot as
    an XPASS.
    """
    persona = persona_factory("fluent", seed=4, typo_rate_mult=1.0)
    assert T.stats(T.plan(sample_text, persona))["deletes"] >= 1


# ---------------------------------------------------------------------------
# 6. revisions: rate, determinism, and where they land
# ---------------------------------------------------------------------------

def test_revision_rate_matches_the_persona(sample_text, sample_persona):
    """``with_revision`` fires at roughly ``persona.revision_prob``.

    The law is about the probability, so the 200 draws use fresh seeded rngs —
    independence is the sample, not 200 identical calls of one persona. The
    plan review's window is 0.2-0.5; we additionally keep the estimate within
    0.15 of the persona's own probability so a stuck coin is caught even when it
    lands inside the window.
    """
    prob = sample_persona.revision_prob
    assert 0.2 <= prob <= 0.5, f"persona revision_prob {prob} is outside the review window"

    fired = 0
    for i in range(200):
        new_text, _keys = T.with_revision(sample_text, sample_persona, rng=random.Random(i))
        fired += new_text != sample_text
    rate = fired / 200
    assert 0.2 <= rate <= 0.5, f"revision rate {rate:.2f} outside 0.2-0.5 over 200 draws"
    assert abs(rate - prob) < 0.15, f"revision rate {rate:.2f} drifted from persona {prob:.2f}"


def test_revision_is_reproducible_for_a_persona(sample_text, sample_persona):
    """The same persona re-decides the same way; its rng is not ambient state."""
    first = T.with_revision(sample_text, sample_persona)[0]
    for _ in range(20):
        assert T.with_revision(sample_text, sample_persona)[0] == first


def test_revision_never_touches_the_meaning_bearing_tail(sample_text, sample_persona):
    """A rewrite may land in the opening; the closing clause must survive.

    The tail is where a reader decides whether to answer. A revision that eats
    it is a bug an operator sees in the thread, not in telemetry.
    """
    tail = sample_text[-40:]
    changed = 0
    for i in range(200):
        new_text, keys = T.with_revision(sample_text, sample_persona, rng=random.Random(i))
        assert new_text[-40:] == tail, f"revision changed the tail: ...{new_text[-40:]!r}"
        assert keys, "a revision returned no keystrokes"
        changed += new_text != sample_text
    assert changed > 0, "no revision fired in 200 draws — the rate law cannot be tested"


def test_revision_returns_the_text_it_planned(sample_text, sample_persona):
    """The returned text is the plan's target, and the plan types its opening."""
    new_text, keys = T.with_revision(sample_text, sample_persona, rng=random.Random(7))
    typed = "".join(k.text for k in keys if k.kind == "char")
    head = new_text.split(" ")[0]
    assert head in typed, f"plan does not type the revised opening {head!r}"


# ---------------------------------------------------------------------------
# 7. the CDP log
# ---------------------------------------------------------------------------

def test_to_cdp_emits_one_entry_per_key(sample_text, sample_persona):
    """The log is a faithful, unfiltered projection of the plan."""
    keys = T.plan(sample_text, sample_persona)
    cdp = T.to_cdp(keys)
    assert len(cdp) == len(keys), f"{len(keys)} keys produced {len(cdp)} CDP entries"
    assert [e["at"] for e in cdp] == [round(k.t, 1) for k in keys]
    assert [e["text"] for e in cdp] == [k.text for k in keys]


def test_to_cdp_uses_vk8_for_every_deletion(sample_text, sample_persona):
    """Backspace is vk 8, one entry each, and nothing else maps to it."""
    keys = T.plan(sample_text, sample_persona)
    cdp = T.to_cdp(keys)
    deletes = sum(1 for k in keys if k.kind == "backspace")
    assert deletes >= 1, "no corrections in the plan — nothing to serialize"
    assert sum(1 for e in cdp if e["vk"] == 8) == deletes
    for entry, key in zip(cdp, keys):
        if key.kind == "backspace":
            assert (entry["vk"], entry["key"], entry["code"]) == (8, "Backspace", "Backspace")
            assert entry["text"] == ""
        else:
            assert entry["vk"] != 8


def test_to_cdp_maps_characters_to_real_keys(sample_text, sample_persona):
    """Every typed character carries a keycode the driver can actually press."""
    keys = T.plan(sample_text, sample_persona)
    for entry, key in zip(T.to_cdp(keys), keys):
        if key.kind != "char":
            continue
        assert entry["code"] not in ("", "Unidentified"), f"{key.text!r} has no keycode"
        assert entry["vk"] > 0, f"{key.text!r} has no virtual key"
        assert entry["key"] == key.text


# ---------------------------------------------------------------------------
# 8. time never runs backwards
# ---------------------------------------------------------------------------

def test_no_key_is_emitted_before_zero(sample_text, persona_factory):
    """Compose starts at t=0; nothing may be scheduled into the past."""
    keys = T.plan(sample_text, persona_factory("average", seed=5))
    assert keys, "plan() produced no keystrokes"
    assert min(k.t for k in keys) > 0.0


def test_key_times_never_run_backwards(sample_text, persona_factory):
    """The log is monotone, so a driver can sleep between entries."""
    for speed_class in CLASSES:
        keys = T.plan(sample_text, persona_factory(speed_class, seed=5))
        times = [k.t for k in keys]
        assert times == sorted(times), f"{speed_class}: a key was scheduled in the past"


def test_every_interval_is_positive(sample_text, persona_factory):
    """Every gap between keystrokes is a real pause, correction included.

    Hard assertion since the typo path was repaired: the mistyped characters,
    each backspace and the corrected character all draw their own advancing
    gap, so no two keys share a timestamp. ``intervals()`` silently drops zero
    deltas, which is how a correction used to vanish from a rhythm audit.
    """
    for speed_class in CLASSES:
        for seed in range(20):
            for text in (SHORT_POST, sample_text):
                keys = T.plan(text, persona_factory(speed_class, seed=seed))
                intervals = T.intervals(keys)
                assert all(d > 0 for d in intervals), (
                    f"{speed_class} seed {seed}: "
                    f"{sum(1 for d in intervals if d <= 0)} non-positive intervals "
                    f"of {len(intervals)}"
                )


# ---------------------------------------------------------------------------
# 9. the log replays to the post
# ---------------------------------------------------------------------------

def _fold(keys) -> str:
    """Replay the plan the way the field would: chars append, backspaces pop."""
    buf: list[str] = []
    for key in keys:
        if key.kind == "char":
            buf.append(key.text)
        elif buf:
            buf.pop()
    return "".join(buf)


def test_plan_replays_to_the_text_for_every_class_and_seed(sample_text, persona_factory):
    """The gate: a plan folds back to exactly the text, for every class and seed.

    One backspace per mistyped character is the invariant. A plan that deletes
    more than it mistyped eats characters already in the field, so every later
    keystroke lands shifted and the published post is garbage; a plan that
    deletes fewer leaves the typo in. Folding the whole plan catches a single
    stray delete anywhere, on both a 94- and a 235-character post.
    """
    for speed_class in CLASSES:
        for seed in range(20):
            for text in (SHORT_POST, sample_text):
                got = _fold(T.plan(text, persona_factory(speed_class, seed=seed)))
                assert got == text, (
                    f"{speed_class} seed {seed} ({len(text)} chars): plan folds to "
                    f"{len(got)} chars — "
                    + (f"diverges at {next(i for i, (a, b) in enumerate(zip(got, text)) if a != b)}"
                       if len(got) == len(text) else f"length drift {len(got) - len(text):+d}")
                )


def test_cdp_log_replays_to_the_post(sample_text, sample_persona):
    """What went into the box has to be what the persona meant to say.

    Hard assertion since the spaces and the typo corrections were both fixed.
    """
    assert _replay(T.to_cdp(T.plan(sample_text, sample_persona))) == sample_text
