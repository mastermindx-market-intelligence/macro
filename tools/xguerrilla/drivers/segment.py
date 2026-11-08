"""Chunk a keystroke plan into human-sized bursts (§26.4).

One ``peekaboo type`` call per key is far too slow — each call is a process
launch plus an accessibility round-trip. One call for a whole post is too
uniform: the site sees a single instantaneous paste of a paragraph, which no
hand produces and which is exactly the shape a typing-biometrics check looks
for. The sweet spot is a burst of 4–10 keys whose internal intervals are the
ones the persona actually planned, with a real pause on the boundaries.

This module is a pure function over the plan: no I/O, no clock, no randomness.
The same plan always segments the same way, so a run is reproducible from its
seed and its postmortem is readable.

Split rules, in the order the plan is walked:

* **A backspace run is entered or left** — revisions are a separate act from
  composing. Real people stop, look, delete, then resume, so the deletes get
  their own burst instead of sharing one with the word that follows.
* **The gap jumps** — an inter-key interval above ``3x`` the median of the run
  so far means the hand paused (hesitation, a look at the draft, a resumed
  word). Pauses stay on the boundary, so the wait is slept by the caller
  instead of being compressed into the CLI's fixed ``--delay``.
* **The run is full** — at 10 keys the burst ends and a new one begins, so a
  long flat stretch still breathes.

Repair afterwards keeps the invariant the caller relies on: bursts are 4–10
keys, and only the tail may be shorter (a plan that ends mid-burst has no
neighbour to fold into).
"""
from __future__ import annotations

import math

__all__ = [
    "MAX_CHUNK",
    "MIN_CHUNK",
    "OUTLIER_FACTOR",
    "chunk_delay_ms",
    "median",
    "segment",
]

MIN_CHUNK = 4
MAX_CHUNK = 10

#: A gap this many times the run median ends the burst.
OUTLIER_FACTOR = 3.0


def median(values) -> float:
    """Median of ``values``; ``0.0`` for an empty sequence."""
    data = sorted(float(v) for v in values or ())
    if not data:
        return 0.0
    mid = len(data) // 2
    if len(data) % 2:
        return data[mid]
    return (data[mid - 1] + data[mid]) / 2.0


def segment(
    keys,
    *,
    min_chunk: int = MIN_CHUNK,
    max_chunk: int = MAX_CHUNK,
    outlier: float = OUTLIER_FACTOR,
) -> list[tuple[list, float]]:
    """Split ``keys`` into bursts of 4–10 keys.

    Returns ``[(keys_chunk, pre_delay_ms), ...]`` in plan order, where
    ``pre_delay_ms`` is the gap to sleep *before* that chunk: the interval from
    the previous chunk's last key to this chunk's first, or — for the first
    chunk — from compose start. It is always strictly positive (floored at 1 ms)
    so a caller can sleep it unconditionally.

    Never yields an empty chunk; never reorders or drops a key.
    """
    keys = list(keys or [])
    if not keys:
        return []
    if min_chunk < 1 or max_chunk < min_chunk:
        raise ValueError("min_chunk must be >= 1 and max_chunk >= min_chunk")

    runs = _repair(_bursts(keys, outlier), min_chunk, max_chunk)
    out: list[tuple[list, float]] = []
    for start, end in runs:
        if start > 0:
            pre = float(keys[start].t) - float(keys[start - 1].t)
        else:
            pre = float(keys[start].t)
        if not math.isfinite(pre) or pre <= 0:
            pre = 1.0
        out.append((keys[start:end], max(1.0, round(pre, 1))))
    return out


def chunk_delay_ms(chunk, fallback: float = 0.0) -> int:
    """Median inter-key interval inside ``chunk``, rounded — the ``--delay`` value.

    ``fallback`` (usually the whole plan's median) is used for one-key chunks,
    where there is no interval to measure. The result is at least 1 ms because
    the CLI rejects a zero delay.
    """
    chunk = list(chunk or [])
    gaps = [float(b.t) - float(a.t) for a, b in zip(chunk, chunk[1:])]
    gaps = [g for g in gaps if math.isfinite(g)]
    value = median(gaps) if gaps else float(fallback or 0.0)
    if not math.isfinite(value) or value <= 0:
        value = float(fallback or 0.0)
    return max(1, int(round(value)))


def _bursts(keys, outlier: float) -> list[tuple[int, int]]:
    """Split on backspace-run edges and on gaps above ``outlier`` × run median."""
    runs: list[tuple[int, int]] = []
    start = 0
    gaps: list[float] = []
    for i in range(1, len(keys)):
        gap = float(keys[i].t) - float(keys[i - 1].t)
        run_median = median(gaps) if len(gaps) >= 2 else None
        here = getattr(keys[i], "kind", "char")
        there = getattr(keys[i - 1], "kind", "char")
        enters = here == "backspace" and there != "backspace"
        leaves = there == "backspace" and here != "backspace"
        jumps = run_median is not None and run_median > 0 and gap > outlier * run_median
        if enters or leaves or jumps:
            runs.append((start, i))
            start = i
            gaps = []
            continue
        gaps.append(gap)
    runs.append((start, len(keys)))
    return runs


def _repair(runs, min_chunk: int, max_chunk: int) -> list[tuple[int, int]]:
    """Enforce chunk sizes: split anything over ``max_chunk``, top up anything under.

    Under-sized runs are fixed by *moving keys* from a neighbour that can spare
    them, not by merging two whole runs — merging a 3-key delete run into a
    10-key burst would push the result over ``max_chunk`` and lose the boundary
    the splitter just found.
    """
    runs = list(runs)
    if len(runs) == 1 and runs[0][1] - runs[0][0] <= max_chunk:
        return runs
    guard = 8 * len(runs) + 128
    while guard > 0:
        guard -= 1
        over = next((i for i, (start, end) in enumerate(runs) if end - start > max_chunk), None)
        if over is not None:
            start, end = runs[over]
            pieces: list[tuple[int, int]] = []
            cursor = start
            for size in _split_sizes(end - start, max_chunk):
                pieces.append((cursor, cursor + size))
                cursor += size
            runs[over : over + 1] = pieces
            continue

        short = next((i for i, (start, end) in enumerate(runs) if end - start < min_chunk), None)
        if short is None:
            break

        start, end = runs[short]
        size = end - start
        need = min_chunk - size

        # 1. steal keys from a neighbour that can spare them
        donors: list[tuple[str, int, int]] = []
        if short + 1 < len(runs):
            nxt = runs[short + 1][1] - runs[short + 1][0]
            if nxt - min_chunk > 0:
                donors.append(("next", short + 1, nxt))
        if short > 0:
            prev = runs[short - 1][1] - runs[short - 1][0]
            if prev - min_chunk > 0:
                donors.append(("prev", short - 1, prev))
        moved = False
        for side, idx, donor_size in donors:
            take = min(need, donor_size - min_chunk)
            if take <= 0:
                continue
            if side == "next":
                donor_start, donor_end = runs[idx]
                runs[idx] = (donor_start + take, donor_end)
                runs[short] = (start, end + take)
            else:
                donor_start, donor_end = runs[idx]
                runs[idx] = (donor_start, donor_end - take)
                runs[short] = (start - take, end)
            moved = True
            break
        if moved:
            continue

        # 2. nothing to steal: merge whole neighbours, smallest shuffle first
        if short == len(runs) - 1:
            prev_start, prev_end = runs[short - 1]
            if (prev_end - prev_start) + size <= max_chunk:
                runs[short - 1 : short + 1] = [(prev_start, end)]
                continue
            break

        prev_ok = short > 0 and (runs[short - 1][1] - runs[short - 1][0]) + size <= max_chunk
        next_ok = (
            short + 1 < len(runs)
            and (runs[short + 1][1] - runs[short + 1][0]) + size <= max_chunk
        )
        if prev_ok:
            prev_start = runs[short - 1][0]
            runs[short - 1 : short + 1] = [(prev_start, end)]
        elif next_ok:
            next_end = runs[short + 1][1]
            runs[short : short + 2] = [(start, next_end)]
        else:  # nothing fits: absorb one neighbouring run, then let the split fix it
            target = short - 1 if short > 0 else short + 1
            lo, hi = sorted((short, target))
            runs[lo : hi + 1] = [(runs[lo][0], runs[hi][1])]
    return runs


def _split_sizes(total: int, max_chunk: int) -> list[int]:
    """Balanced piece sizes, each at most ``max_chunk`` and summing to ``total``."""
    count = max(1, math.ceil(total / max_chunk))
    base, extra = divmod(total, count)
    return [base + (1 if i < extra else 0) for i in range(count)]
