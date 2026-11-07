"""Persona drift: are the children in one cell starting to sound alike?

§26.8 lists "persona drift (all children sounding alike)" as a named failure
mode and gives the response directly: a weekly cosine check across cell
siblings' last 20 posts, and the two closest are told to diverge in the next
prompt. This module is that check and that sentence — nothing else. It reads
text, it never writes a persona row.

Two rules of interpretation, both load-bearing:

* Only *siblings inside one cell* are compared. Five children in five cities
  are supposed to share a general register; two children in ATX-01 are the ones
  whose timelines get read side by side.
* The threshold (0.55 by default) is a tuning knob, not a truth. It is a
  bag-of-words cosine, so it measures shared vocabulary — not argument, not
  rhythm, not whether the posts are actually interesting. Move it as the cell's
  beat changes and re-read the numbers rather than trusting the flag.

Stdlib only: no numpy, no sklearn, no network, no credentials. Deterministic
for a given input, so a weekly cron can diff last week's report against this
one.
"""
from __future__ import annotations

import math
import re
from typing import Iterable, Mapping

__all__ = ["vectorize", "cosine", "profile", "pairs", "audit", "diverge_brief"]

DEFAULT_THRESHOLD = 0.55
DEFAULT_WINDOW = 20
MIN_POSTS = 3

# Deliberately small: the words that carry no beat, so removing them cannot
# erase a persona. "one", "get", "now" stay in — they are part of how these
# rows actually write.
STOPWORDS = frozenset(
    """
    the and but for with that this you not are was were have has had from they
    what just its about into than then them their your our his her she him who
    all any can could would should will been being there here when where while
    out off over under more most some such only very also too did does doing
    """.split()
)

_SPLIT = re.compile(r"[^a-z0-9]+")


def vectorize(texts: Iterable[str]) -> dict[str, float]:
    """Bag of words for ``texts``: lowercase, punctuation off, sublinear tf.

    Tokens shorter than 3 characters and the stopword set are dropped. The
    weighting is ``1 + log(tf)`` so a phrase repeated ten times counts for
    about three, not ten — a child's tic should show, not dominate.
    """
    counts: dict[str, int] = {}
    for text in texts:
        for token in _SPLIT.split(str(text).lower()):
            if len(token) < 3 or token in STOPWORDS:
                continue
            counts[token] = counts.get(token, 0) + 1
    return {t: (1.0 + math.log(c) if c > 1 else 1.0) for t, c in sorted(counts.items())}


def cosine(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    """Cosine similarity, safe on empty and zero vectors (0.0, never a raise)."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    dot = 0.0
    for token, weight in a.items():
        other = b.get(token)
        if other:
            dot += weight * other
    if dot == 0.0:
        return 0.0
    na = math.sqrt(sum(w * w for w in a.values()))
    nb = math.sqrt(sum(w * w for w in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))


def profile(texts: list[str]) -> dict[str, float]:
    """A child's centroid: mean of its per-post vectors, L2-normalised."""
    vectors = [vectorize([text]) for text in texts]
    vectors = [v for v in vectors if v]
    if not vectors:
        return {}
    total: dict[str, float] = {}
    for vector in vectors:
        for token, weight in vector.items():
            total[token] = total.get(token, 0.0) + weight
    mean = {t: w / len(vectors) for t, w in total.items()}
    norm = math.sqrt(sum(w * w for w in mean.values()))
    if norm == 0.0:
        return {}
    return {t: w / norm for t, w in sorted(mean.items())}


def pairs(
    profiles: Mapping[str, dict[str, float]], threshold: float = DEFAULT_THRESHOLD
) -> list[tuple[str, str, float]]:
    """Every pair at or above ``threshold``, closest first."""
    handles = sorted(profiles)
    found: list[tuple[str, str, float]] = []
    for i, a in enumerate(handles):
        for b in handles[i + 1:]:
            sim = cosine(profiles[a], profiles[b])
            if sim >= threshold:
                found.append((a, b, sim))
    found.sort(key=lambda row: (-row[2], row[0], row[1]))
    return found


def _resolve_cells(
    post_history: Mapping[str, list[str]],
    cells: Mapping[str, str] | None,
    personas: Mapping[str, object] | None,
) -> dict[str, str]:
    """Cell per handle: explicit ``cells`` wins, then the persona row, else ''."""
    resolved: dict[str, str] = {}
    for handle in post_history:
        cell = (cells or {}).get(handle)
        if not cell and personas:
            persona = personas.get(handle)
            if persona is not None:
                cell = str(getattr(persona, "cell", "") or "")
        resolved[handle] = cell or ""
    return resolved


def audit(
    post_history: Mapping[str, list[str]],
    threshold: float = DEFAULT_THRESHOLD,
    window: int = DEFAULT_WINDOW,
    cells: Mapping[str, str] | None = None,
    personas: Mapping[str, object] | None = None,
) -> dict:
    """Compare cell siblings over their last ``window`` posts.

    Returns ``{"ok", "worst", "n", "window", "note"}``. ``ok`` is False when any
    sibling pair reaches ``threshold``. Children with fewer than ``MIN_POSTS``
    posts in the window are excluded from the numbers and named in the note —
    a two-post child gets no similarity rather than a fabricated one.
    """
    resolved = _resolve_cells(post_history, cells, personas)

    skipped: list[str] = []
    by_cell: dict[str, list[str]] = {}
    for handle in sorted(post_history):
        recent = list(post_history[handle])[-window:]
        if len(recent) < MIN_POSTS:
            skipped.append(handle)
            continue
        cell = resolved.get(handle, "")
        if not cell:
            skipped.append(handle)
            continue
        by_cell.setdefault(cell, []).append(handle)

    flagged: list[dict] = []
    closest: tuple[str, str, float] | None = None
    compared = 0
    thin_cells: list[str] = []
    for cell in sorted(by_cell):
        members = by_cell[cell]
        if len(members) < 2:
            thin_cells.append(cell)
            continue
        compared += len(members)
        cell_profiles = {
            h: profile(list(post_history[h])[-window:]) for h in members
        }
        for a, b, sim in pairs(cell_profiles, threshold):
            flagged.append({"a": a, "b": b, "similarity": round(sim, 4), "cell": cell})
        for a, b, sim in pairs(cell_profiles, 0.0):
            if closest is None or sim > closest[2]:
                closest = (a, b, sim)

    flagged.sort(key=lambda row: (-row["similarity"], row["a"], row["b"]))

    if flagged:
        top = flagged[0]
        note = (
            f"{top['a']} and {top['b']} in {top['cell']} are the closest siblings "
            f"at {top['similarity']:.2f} — tell them to diverge in the next prompt."
        )
    elif closest is not None:
        note = (
            f"No sibling pair is above {threshold:.2f}; the closest is "
            f"{closest[0]} and {closest[1]} at {closest[2]:.2f}. Hold the line."
        )
    elif thin_cells:
        note = (
            "No cell has two children with "
            f"{MIN_POSTS}+ posts in the last {window}; add posts before "
            "reading anything into these numbers."
        )
    else:
        note = f"No comparable children in the last {window} posts."

    if skipped:
        note += (
            f" Skipped {len(skipped)} with fewer than {MIN_POSTS} posts in window "
            f"or no known cell: {', '.join(sorted(skipped))}."
        )

    return {
        "ok": not flagged,
        "worst": flagged,
        "n": compared,
        "window": window,
        "note": note,
    }


def _levers(handle: str, persona: object | None) -> list[str]:
    """Concrete things to change on one side of a drifting pair."""
    if persona is None:
        return [
            f"give {handle} one phrase only it uses, and take one away",
            f"move {handle} to the opposite casing",
        ]
    levers: list[str] = []
    phrases = [str(p) for p in (getattr(persona, "pet_phrases", None) or [])]
    opinions = [str(o) for o in (getattr(persona, "opinions", None) or [])]
    casing = getattr(persona, "casing", None)
    if phrases:
        levers.append(f'keep "{phrases[0]}" and retire the rest of {handle}\'s phrases')
    if opinions:
        levers.append(f'make {handle} argue "{opinions[0]}" in the next post')
    if casing:
        levers.append(f"hold {handle} at casing={casing}")
    if not levers:
        levers.append(f"give {handle} a phrase no sibling uses")
    return levers


def diverge_brief(
    handle_a: str,
    handle_b: str,
    persona_a: object | None = None,
    persona_b: object | None = None,
) -> str:
    """Operator-facing fragment for the next prompt: who, and what to change."""
    lines = [
        f"DIVERGE: {handle_a} and {handle_b} are reading too close. "
        "Give each of them a lever the other cannot use in this post.",
        f"{handle_a}: " + "; ".join(_levers(handle_a, persona_a)) + ".",
        f"{handle_b}: " + "; ".join(_levers(handle_b, persona_b)) + ".",
        "Both: no shared opener, and neither may reuse the other's topic noun "
        "in its first sentence.",
    ]
    return "\n".join(lines)
