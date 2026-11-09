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
    """Cell per handle: explicit nonblank cells wins, then the persona row."""
    resolved: dict[str, str] = {}
    for handle in post_history:
        cell = (cells or {}).get(handle)
        if cell is not None and not isinstance(cell, str):
            raise ValueError(f"cell for {handle!r} must be text or None")
        cell = (cell or "").strip()
        if not cell and personas:
            persona = personas.get(handle)
            if persona is not None:
                cell = getattr(persona, "cell", None)
                if cell is not None and not isinstance(cell, str):
                    raise ValueError(f"cell for {handle!r} must be text or None")
                cell = (cell or "").strip()
        resolved[handle] = cell
    return resolved


def audit(
    post_history: Mapping[str, list[str]],
    threshold: float = DEFAULT_THRESHOLD,
    window: int = DEFAULT_WINDOW,
    cells: Mapping[str, str] | None = None,
    personas: Mapping[str, object] | None = None,
) -> dict:
    """Compare cell siblings over their last window posts.

    Status is clear, drift or insufficient_data. The ok field is True only
    for a clear audit with complete coverage of the supplied histories.
    A detected pair remains reported even when other children are excluded;
    absent comparisons or partial coverage never qualify as a clear result.

    Each compared child needs MIN_POSTS informative text posts in the window,
    a known cell and a comparable sibling. The excluded map names other
    children and their reasons; n counts compared children and compared_pairs
    counts actual same-cell comparisons. No cross-cell pairs are inferred.

    Window must be an integer >= MIN_POSTS and threshold a finite number in
    [0, 1]. Invalid configuration or malformed recent input raises ValueError,
    rather than returning a successful report. Existing result fields
    (ok, worst, n, window, note) are retained.
    """
    if isinstance(window, bool) or not isinstance(window, int) or window < MIN_POSTS:
        raise ValueError(f"window must be an integer >= {MIN_POSTS}")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0.0 <= threshold <= 1.0
        or not math.isfinite(threshold)
    ):
        raise ValueError("threshold must be a finite number in [0, 1]")
    if not isinstance(post_history, Mapping):
        raise ValueError("post_history must be a mapping")
    if any(not isinstance(h, str) or not h.strip() for h in post_history):
        raise ValueError("history handles must be nonblank text")
    if cells is not None and not isinstance(cells, Mapping):
        raise ValueError("cells must be a mapping or None")
    if personas is not None and not isinstance(personas, Mapping):
        raise ValueError("personas must be a mapping or None")
    resolved = _resolve_cells(post_history, cells, personas)

    excluded: dict[str, str] = {}
    by_cell: dict[str, list[str]] = {}
    profiles: dict[str, dict[str, float]] = {}
    for handle in sorted(post_history):
        history = post_history[handle]
        if not isinstance(history, (list, tuple)):
            raise ValueError(f"history for {handle!r} must be a list or tuple of text")
        recent = list(history[-window:])
        if any(not isinstance(text, str) for text in recent):
            raise ValueError(f"recent posts for {handle!r} must be text")
        if len(recent) < MIN_POSTS:
            excluded[handle] = "insufficient_posts"
            continue
        cell = resolved[handle]
        if not cell:
            excluded[handle] = "missing_cell"
            continue
        informative = [text for text in recent if vectorize([text])]
        if len(informative) < MIN_POSTS:
            excluded[handle] = "insufficient_text"
            continue
        profiles[handle] = profile(informative)
        by_cell.setdefault(cell, []).append(handle)

    flagged: list[dict] = []
    closest: tuple[str, str, float] | None = None
    compared = 0
    compared_pairs = 0
    for cell in sorted(by_cell):
        members = by_cell[cell]
        if len(members) < 2:
            excluded[members[0]] = "no_cell_peer"
            continue
        compared += len(members)
        cell_pairs = pairs({h: profiles[h] for h in members}, 0.0)
        compared_pairs += len(cell_pairs)
        for a, b, sim in cell_pairs:
            if sim >= threshold:
                flagged.append({"a": a, "b": b, "similarity": round(sim, 4), "cell": cell})
            if closest is None or sim > closest[2]:
                closest = (a, b, sim)

    flagged.sort(key=lambda row: (-row["similarity"], row["a"], row["b"]))
    complete = compared_pairs > 0 and compared == len(post_history)
    status = "drift" if flagged else ("clear" if complete else "insufficient_data")
    if flagged:
        top = flagged[0]
        note = (
            f"{top['a']} and {top['b']} in {top['cell']} are the closest siblings "
            f"at {top['similarity']:.2f} — tell them to diverge in the next prompt."
        )
    elif closest is not None:
        note = (
            f"No compared sibling pair reached {threshold:.2f}; the closest is "
            f"{closest[0]} and {closest[1]} at {closest[2]:.2f}."
        )
    else:
        note = f"No comparable sibling pairs in the last {window} posts."
    if not complete:
        note += " Audit coverage is incomplete; a clear verdict is unavailable."
    if excluded:
        reasons = ", ".join(f"{h} ({excluded[h]})" for h in sorted(excluded))
        note += f" Skipped {len(excluded)}: {reasons}."

    return {
        "ok": status == "clear",
        "status": status,
        "worst": flagged,
        "n": compared,
        "compared_pairs": compared_pairs,
        "excluded": dict(sorted(excluded.items())),
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
