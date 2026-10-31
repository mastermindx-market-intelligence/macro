#!/usr/bin/env python3
"""Split, join, and three-way-merge ``.github/ci/legacy-jobs.yml`` at job boundaries.

The manifest stays the only committed source. ``split`` cuts it into ordered
byte slices; ``join`` concatenates those slices. ``join(split(text))`` is the
original text, so a later patch can edit one job's slice and reassemble
without a second copy of the workflow.

``merge3(base, ours, theirs)`` merges those slices. A job added on one side
is kept. Jobs added on both sides are all kept, anchored after the base job
that precedes them, ours' additions first then theirs', each side in its own
order. The same new key is kept once; differing text for that key conflicts
instead of writing two YAML keys. A one-sided edit is taken. An identical
edit is taken once. Differing edits conflict. A job deleted on one side and
unchanged on the other is deleted; delete-versus-edit conflicts. Preamble
and trailer follow the same rules. A per-fragment conflict wraps only that
fragment in standard markers and records its key, in output order.

The relative order of base keys that still exist on a side is part of the
merge. When that order differs from the base on ours or theirs, the result is
one conflict recorded as ``__order__``: the two original texts sit inside one
marker pair. Three shapes are clean instead.

An order-only change on exactly one side, while the other side's fragment
texts equal the base, returns that side's original bytes. The same order-only
permutation on both sides is taken once only when the two texts are equal:
the job-key orders match and the job texts match, so the result is that
side's original bytes and there is no conflict. The same key order with
different job text, including separator glue, stays an ``__order__``
conflict. Two different permutations still conflict.

An order-only permutation on one side together with a text edit on the other
is also clean when the edit side's job keys stay in base order. Merged jobs
follow the order-only side's key order. Each job's leading separator moves
with that permutation; a separator the permutation left on the same job can
still take the edit side's text. A separator the permutation moved must not
also be edited into a third shape: when the edit side's separator differs
from both the base and the moved separator, the merge records ``__order__``
instead of silently dropping that edit. Job bodies, the preamble, and the
trailer come from the per-key resolve, so the edit's scalar wins.

The same case is also clean when both sides carry the identical job-key
permutation and exactly one side is order-only, provided the edit side
moved every separator the permutation moved: the agreed order applies and
the other side's edited bodies win, while mixed glue (a positional swap
against a whole-fragment swap of the same pair) stays an ``__order__``
conflict.

Order-only means the same job keys, the same preamble and trailer bytes, and
the same bytes from each job's key line through the end of its fragment. A
leading separator may sit with the other job after a positional swap. A side
that reorders and also edits, adds, or deletes is not order-only, so the
merge conflicts instead of applying the permutation.

A job key repeated inside one manifest is a conflict. ``_index`` keeps every
body of that key, and the marker contains each side's bodies, so a later body
is not dropped. The checked-in manifest's keys are unique, so merging it with
itself stays byte-identical.

A job fragment's owner is the single vertical directory named by its ``paths:``
entries, or ``shared`` when the paths are not confined to one. Suite modules
(``tests/**/test_*.py``) and package ``__init__.py`` markers do not locate a
vertical: every job names its own suite. Preamble and trailer are ``shared``.

Opt-in only. This module does not install a merge driver and does not write
``.gitattributes`` or git config. To opt in, add this line to
``.gitattributes``::

    .github/ci/legacy-jobs.yml merge=cipack

and set the driver command::

    git config merge.cipack.driver "python3 scripts/ci_pack_fragments.py merge3 %O %A %B"

The three arguments are git's ``%O %A %B`` (ancestor, current, other). The
command writes the merged manifest to ``%A`` and exits 0 when clean, 1 when
any fragment conflicts.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / ".github" / "ci" / "legacy-jobs.yml"

PREAMBLE_KEY = "__preamble__"
TRAILER_KEY = "__trailer__"
ORDER_KEY = "__order__"

# Top-level buckets. The vertical is the directory under one of these, not
# the bucket itself. A file that sits directly in a bucket names no vertical.
_GENERIC_ROOTS = frozenset(
    {
        ".claude",
        ".github",
        "admin",
        "agentos",
        "app",
        "browser",
        "calibration",
        "collectors",
        "config",
        "content",
        "contracts",
        "data",
        "docs",
        "engine",
        "finviz_themes",
        "knowledge",
        "lib",
        "ops",
        "orch",
        "plugins",
        "properties",
        "reports",
        "research",
        "scripts",
        "site",
        "templates",
        "tests",
        "tools",
        "ux-evidence",
        "worker",
    }
)

# Exactly two spaces, then a job id, then a colon. Body keys sit at four
# spaces, so this is the job boundary in the real manifest.
_JOB_KEY_RE = re.compile(r"^  ([A-Za-z0-9][A-Za-z0-9_-]*):\s*$")
_PATHS_KEY_RE = re.compile(r"^    paths:\s*$")
_SIBLING_KEY_RE = re.compile(r"^    [A-Za-z0-9_-]+:")
_PATH_ENTRY_RE = re.compile(r"^      - (.*)$")
_SUITE_RE = re.compile(r"^tests/(?:.+/)?test_[^/]+\.py$")


@dataclass(frozen=True)
class Fragment:
    """One ordered slice of a legacy-jobs manifest."""

    key: str
    owner: str
    text: str
    kind: str  # "preamble" | "job" | "trailer"


def _newline_lines(text: str) -> list[str]:
    """Split on ``\\n`` only, keeping each separator, so join is byte-exact.

    ``str.splitlines`` also breaks on ``\\r``, ``\\x0b`` and Unicode separators.
    Those must stay inside the slice that contains them.
    """
    if text == "":
        return []
    parts = text.split("\n")
    if text.endswith("\n"):
        return [part + "\n" for part in parts[:-1]]
    lines = [part + "\n" for part in parts[:-1]]
    lines.append(parts[-1])
    return lines


def _job_keys(lines: list[str]) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = _JOB_KEY_RE.match(line.rstrip("\r\n"))
        if match:
            found.append((index, match.group(1)))
    return found


def _leading_start(lines: list[str], key_index: int, floor: int) -> int:
    """Include the blank lines and ``  #`` comments that introduce this job.

    Those lines sit between the previous job's body and this job's key. They
    document this job, so they travel with its fragment.
    """
    start = key_index
    cursor = key_index - 1
    while cursor >= floor:
        raw = lines[cursor].rstrip("\r\n")
        if raw.strip() == "" or raw.startswith("  #"):
            start = cursor
            cursor -= 1
            continue
        break
    return start


def _trailer_start(lines: list[str], key_index: int) -> int:
    """First line after the last job's indented body.

    A trailing blank line or a column-0 note is the trailer. Indented body
    lines stay with the job. The real manifest has no trailer bytes.
    """
    cursor = len(lines) - 1
    while cursor > key_index:
        raw = lines[cursor].rstrip("\r\n")
        if raw.startswith("    ") and raw.strip() != "":
            return cursor + 1
        cursor -= 1
    return key_index + 1


def job_paths(job_text: str) -> list[str]:
    """The job's ``paths:`` scalars, in order. Missing ``paths:`` is empty.

    Entries are the plain or quoted scalars the manifest actually writes.
    This does not interpret YAML aliases; the real file has none.
    """
    paths: list[str] = []
    in_paths = False
    for line in job_text.split("\n"):
        if not in_paths:
            if _PATHS_KEY_RE.match(line):
                in_paths = True
            continue
        entry = _PATH_ENTRY_RE.match(line)
        if entry:
            raw = entry.group(1).strip()
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
                raw = raw[1:-1]
            paths.append(raw)
            continue
        if line.strip() == "" or line.startswith("      #") or line.startswith("    #"):
            continue
        if _SIBLING_KEY_RE.match(line):
            in_paths = False
            continue
        in_paths = False
    return paths


def _ignored_for_owner(path: str) -> bool:
    if "*" in path or "?" in path or "[" in path:
        return False
    if path.rsplit("/", 1)[-1] == "__init__.py":
        return True
    return _SUITE_RE.match(path) is not None


def _vertical_token(path: str) -> str | None:
    parts = [part for part in path.split("/") if part and part != "."]
    if not parts:
        return None
    if parts[0] in _GENERIC_ROOTS:
        parts = parts[1:]
    if not parts:
        return None
    token = parts[0]
    if token in {"*", "**"} or any(char in token for char in "*?["):
        return None
    if "." in token:
        return None
    return token


def owner_for_paths(paths: list[str]) -> str:
    """``shared``, unless every locating path names the same vertical directory."""
    tokens: set[str] = set()
    for path in paths:
        if _ignored_for_owner(path):
            continue
        token = _vertical_token(path)
        if token is None:
            return "shared"
        tokens.add(token)
        if len(tokens) > 1:
            return "shared"
    if len(tokens) == 1:
        return next(iter(tokens))
    return "shared"


def split(text: str) -> list[Fragment]:
    """Cut ``text`` into preamble, one fragment per job, and trailer."""
    lines = _newline_lines(text)
    keys = _job_keys(lines)
    if not keys:
        return [
            Fragment(PREAMBLE_KEY, "shared", text, "preamble"),
            Fragment(TRAILER_KEY, "shared", "", "trailer"),
        ]

    starts = []
    floor = 0
    for index, _job_id in keys:
        starts.append(_leading_start(lines, index, floor))
        floor = index + 1
    trailer_at = _trailer_start(lines, keys[-1][0])

    fragments = [
        Fragment(PREAMBLE_KEY, "shared", "".join(lines[: starts[0]]), "preamble")
    ]
    for position, (_index, job_id) in enumerate(keys):
        end = starts[position + 1] if position + 1 < len(keys) else trailer_at
        job_text = "".join(lines[starts[position] : end])
        fragments.append(
            Fragment(
                job_id,
                owner_for_paths(job_paths(job_text)),
                job_text,
                "job",
            )
        )
    fragments.append(
        Fragment(TRAILER_KEY, "shared", "".join(lines[trailer_at:]), "trailer")
    )
    return fragments


def join(fragments: list[Fragment]) -> str:
    """Reassemble slices in the order ``split`` produced."""
    return "".join(fragment.text for fragment in fragments)


@dataclass(frozen=True)
class MergeResult:
    """Merged manifest text and the fragment keys that conflicted.

    ``conflicts`` is in output order: preamble, then jobs, then trailer.
    An incumbent-order conflict is the single key ``__order__``.
    """

    text: str
    conflicts: tuple[str, ...]


def _index(
    fragments: list[Fragment],
) -> tuple[dict[str, Fragment], dict[str, tuple[str, ...]]]:
    """First fragment per key, plus every body of a repeated job key.

    A repeated job key is a conflict. The tuple is file order, the first body
    included, so the later body is still available to the marker.
    """
    indexed: dict[str, Fragment] = {}
    extras: dict[str, list[str]] = {}
    for fragment in fragments:
        if fragment.kind != "job":
            indexed.setdefault(fragment.key, fragment)
            continue
        if fragment.key not in indexed:
            indexed[fragment.key] = fragment
            continue
        extras.setdefault(fragment.key, []).append(fragment.text)
    duplicates = {
        key: (indexed[key].text, *bodies) for key, bodies in extras.items()
    }
    return indexed, duplicates


def _job_order(fragments: list[Fragment]) -> list[str]:
    order: list[str] = []
    seen: set[str] = set()
    for fragment in fragments:
        if fragment.kind != "job" or fragment.key in seen:
            continue
        seen.add(fragment.key)
        order.append(fragment.key)
    return order


def _conflict_block(ours_text: str, theirs_text: str) -> str:
    """Wrap one fragment in standard merge markers.

    An empty side is a deletion. Fragment text that already ends in a newline
    is not given another one, so a clean side stays byte-identical inside the
    block.
    """

    def _body(text: str) -> str:
        if text == "" or text.endswith("\n"):
            return text
        return text + "\n"

    opener = "<" * 7
    closer = ">" * 7
    return (
        f"{opener} ours\n{_body(ours_text)}{'=' * 7}\n"
        f"{_body(theirs_text)}{closer} theirs\n"
    )


def _resolve_text(
    base_text: str | None,
    ours_text: str | None,
    theirs_text: str | None,
) -> tuple[str | None, bool]:
    """Return ``(text, conflicted)``. ``None`` drops the key.

    Absent (``None``) is a missing job. Empty text is a present fragment,
    which is how a cleared preamble or trailer shows up: ``split`` always
    emits those two keys.
    """
    if base_text is None:
        if ours_text is None:
            return theirs_text, False
        if theirs_text is None or ours_text == theirs_text:
            return ours_text, False
        return _conflict_block(ours_text, theirs_text), True

    if ours_text is None and theirs_text is None:
        return None, False
    if ours_text is None:
        if theirs_text == base_text:
            return None, False
        return _conflict_block("", theirs_text or ""), True
    if theirs_text is None:
        if ours_text == base_text:
            return None, False
        return _conflict_block(ours_text, ""), True
    if ours_text == theirs_text or theirs_text == base_text:
        return ours_text, False
    if ours_text == base_text:
        return theirs_text, False
    return _conflict_block(ours_text, theirs_text), True


def _additions(
    base_keys: list[str], side_keys: list[str]
) -> list[tuple[str | None, str]]:
    """Keys in ``side_keys`` that are not in base, with the preceding base key.

    ``None`` means the addition sits before every base job. Order matches
    the side. A repeated new key is kept at its first occurrence.
    """
    base_set = set(base_keys)
    anchor: str | None = None
    added: list[tuple[str | None, str]] = []
    seen: set[str] = set()
    for key in side_keys:
        if key in base_set:
            anchor = key
            continue
        if key in seen:
            continue
        seen.add(key)
        added.append((anchor, key))
    return added


def _merged_job_order(
    base_keys: list[str],
    ours_keys: list[str],
    theirs_keys: list[str],
    dropped: set[str],
) -> list[str]:
    """Base order, with additions inserted after the base job they follow.

    When both sides add after the same base job, ours' new keys come first,
    then theirs'. A key added on both sides is emitted once, at ours' anchor.
    """
    ours_at: dict[str | None, list[str]] = {}
    theirs_at: dict[str | None, list[str]] = {}
    claimed: set[str] = set()
    for anchor, key in _additions(base_keys, ours_keys):
        claimed.add(key)
        ours_at.setdefault(anchor, []).append(key)
    for anchor, key in _additions(base_keys, theirs_keys):
        if key in claimed:
            continue
        claimed.add(key)
        theirs_at.setdefault(anchor, []).append(key)

    order: list[str] = []
    emitted: set[str] = set()

    def emit(anchor: str | None) -> None:
        for bucket in (ours_at, theirs_at):
            for key in bucket.get(anchor, []):
                if key in emitted or key in dropped:
                    continue
                emitted.add(key)
                order.append(key)

    emit(None)
    for key in base_keys:
        if key not in dropped and key not in emitted:
            emitted.add(key)
            order.append(key)
        emit(key)
    return order


def _lead_and_body(fragment: Fragment) -> tuple[str, str]:
    """Separator glued on by ``_leading_start``, and the bytes from the key line.

    The separator is the blank lines and ``  #`` comments before the key. It is
    not part of the body, so a positional swap can still be order-only. A
    permutation keeps this separator with the fragment that carries it.
    """
    marker = f"  {fragment.key}:"
    lines = fragment.text.split("\n")
    for index, line in enumerate(lines):
        if line.rstrip("\r") == marker:
            if index == 0:
                return "", "\n".join(lines)
            return "\n".join(lines[:index]) + "\n", "\n".join(lines[index:])
    return "", fragment.text


def _body_from_key(fragment: Fragment) -> str:
    """Bytes from the job key line through the end of the fragment."""
    return _lead_and_body(fragment)[1]


def _unique_map(fragments: list[Fragment]) -> dict[str, Fragment] | None:
    """Map key to fragment, or ``None`` when a key occurs twice."""
    mapped: dict[str, Fragment] = {}
    for fragment in fragments:
        if fragment.key in mapped:
            return None
        mapped[fragment.key] = fragment
    return mapped


def _order_differs(base_keys: list[str], side_keys: list[str]) -> bool:
    """True when surviving base keys are not in base order on this side."""
    surviving = set(base_keys) & set(side_keys)
    base_relative = [key for key in base_keys if key in surviving]
    side_relative = [key for key in side_keys if key in surviving]
    return side_relative != base_relative


def _is_order_only(
    base_frags: list[Fragment],
    side_frags: list[Fragment],
    base_keys: list[str],
    side_keys: list[str],
) -> bool:
    """True when the side's only change is a permutation of the base jobs."""
    if side_keys == base_keys or set(side_keys) != set(base_keys):
        return False
    if len(side_keys) != len(set(side_keys)) or len(base_keys) != len(set(base_keys)):
        return False
    base_map = _unique_map(base_frags)
    side_map = _unique_map(side_frags)
    if base_map is None or side_map is None or set(base_map) != set(side_map):
        return False
    for key, base_fragment in base_map.items():
        side_fragment = side_map[key]
        if base_fragment.kind != "job":
            if side_fragment.text != base_fragment.text:
                return False
            continue
        if _body_from_key(side_fragment) != _body_from_key(base_fragment):
            return False
    return True


def _fragment_texts_equal(side: list[Fragment], base: list[Fragment]) -> bool:
    """True when each key's fragment text matches the base and keys are unique."""
    side_map = _unique_map(side)
    base_map = _unique_map(base)
    if side_map is None or base_map is None or set(side_map) != set(base_map):
        return False
    return all(side_map[key].text == base_map[key].text for key in base_map)


def _repeated_block(
    key: str,
    ours_dups: dict[str, tuple[str, ...]],
    theirs_dups: dict[str, tuple[str, ...]],
    ours_by: dict[str, Fragment],
    theirs_by: dict[str, Fragment],
) -> str:
    """One marker pair holding every body of a repeated job key."""

    def side(
        duplicates: dict[str, tuple[str, ...]], by_key: dict[str, Fragment]
    ) -> str:
        if key in duplicates:
            return "".join(duplicates[key])
        fragment = by_key.get(key)
        if fragment is None:
            return ""
        return fragment.text

    return _conflict_block(side(ours_dups, ours_by), side(theirs_dups, theirs_by))


def _apply_order_and_edits(
    base_frags: list[Fragment],
    order_frags: list[Fragment],
    edit_frags: list[Fragment],
    *,
    order_is_ours: bool,
    edit_side_permuted: bool,
) -> MergeResult | None:
    """Apply one side's order-only permutation and the other side's text edits.

    Job order and a separator the permutation moved come from the order-only
    side, unless the edit side changed that separator to a third shape. A
    separator that side left unchanged can take the edit. Bodies,
    preamble, and trailer use the per-key resolve, so a one-sided scalar wins.
    ``None`` means this shape is not that case; the caller records ``__order__``.

    ``edit_side_permuted`` declares that the edit side carries the SAME job-key
    permutation as the order-only side instead of base order; the guard in
    ``_moved_separators_agree`` runs here exactly when it is True, so a
    separator the permutation moved must also have moved on the edit side,
    otherwise mixed glue would let one swap's separator silently outrank the
    other's and this returns ``None``. The flag is keyword-only with no
    default, so a caller that omits it raises ``TypeError`` at its own call
    site instead of silently merging with no guard. Omission is the only
    shape the signature can catch: a caller that states a WRONG False is not
    caught by it, because no signature sees the edit side's key order, so
    such a call merges unguarded and its coverage rests on that caller's own
    base-order precondition. The agreed-permutation caller passes
    True. The base-order callers (an edit side whose keys stay in base order)
    state False: hoisting the guard unconditionally would turn their clean
    merge into an ``__order__`` conflict.
    """
    if edit_side_permuted and not _moved_separators_agree(
        base_frags,
        order_frags,
        edit_frags,
    ):
        return None
    base_by = _unique_map(base_frags)
    order_by = _unique_map(order_frags)
    edit_by = _unique_map(edit_frags)
    if (
        base_by is None
        or order_by is None
        or edit_by is None
        or set(base_by) != set(order_by)
        or set(base_by) != set(edit_by)
    ):
        return None

    def pick(base_text: str, order_text: str, edit_text: str) -> str | None:
        if order_is_ours:
            text, conflicted = _resolve_text(base_text, order_text, edit_text)
        else:
            text, conflicted = _resolve_text(base_text, edit_text, order_text)
        if conflicted or text is None:
            return None
        return text

    preamble = pick(
        base_by[PREAMBLE_KEY].text,
        order_by[PREAMBLE_KEY].text,
        edit_by[PREAMBLE_KEY].text,
    )
    if preamble is None:
        return None
    pieces: list[str] = [preamble]
    for key in _job_order(order_frags):
        base_lead, base_body = _lead_and_body(base_by[key])
        order_lead, order_body = _lead_and_body(order_by[key])
        edit_lead, edit_body = _lead_and_body(edit_by[key])
        body = pick(base_body, order_body, edit_body)
        if body is None:
            return None
        if order_lead == base_lead:
            lead = pick(base_lead, order_lead, edit_lead)
            if lead is None:
                return None
        elif edit_lead != base_lead and edit_lead != order_lead:
            return None
        else:
            lead = order_lead
        pieces.append(lead + body)
    trailer = pick(
        base_by[TRAILER_KEY].text,
        order_by[TRAILER_KEY].text,
        edit_by[TRAILER_KEY].text,
    )
    if trailer is None:
        return None
    pieces.append(trailer)
    return MergeResult("".join(pieces), ())


def _moved_separators_agree(
    base_frags: list[Fragment],
    order_frags: list[Fragment],
    edit_frags: list[Fragment],
) -> bool:
    """True when the edit side moved every separator the permutation moved.

    Both sides share one job-key order, so the edit side's per-key separator
    is a glue choice for that permutation, not a base separator left in its
    slot. ``_apply_order_and_edits`` only rejects a third-shape separator, so
    by itself it would let a positional swap's glue silently outrank a
    whole-fragment swap's; that mixed-glue shape must stay an ``__order__``
    conflict, so ``_apply_order_and_edits`` returns ``None`` for it when its
    required keyword-only ``edit_side_permuted`` argument says the edit side
    carries this same permutation; every caller states that flag, so the
    guard cannot be skipped by omission.
    """
    base_by = _unique_map(base_frags)
    order_by = _unique_map(order_frags)
    edit_by = _unique_map(edit_frags)
    if base_by is None or order_by is None or edit_by is None:
        return False
    for key in _job_order(order_frags):
        if key not in base_by or key not in edit_by:
            return False
        base_lead = _lead_and_body(base_by[key])[0]
        order_lead = _lead_and_body(order_by[key])[0]
        edit_lead = _lead_and_body(edit_by[key])[0]
        if order_lead != base_lead and edit_lead != order_lead:
            return False
    return True


def _fragment_texts(
    base_by: dict[str, Fragment],
    ours_by: dict[str, Fragment],
    theirs_by: dict[str, Fragment],
    key: str,
) -> tuple[str | None, str | None, str | None]:
    base_fragment = base_by.get(key)
    ours_fragment = ours_by.get(key)
    theirs_fragment = theirs_by.get(key)
    return (
        None if base_fragment is None else base_fragment.text,
        None if ours_fragment is None else ours_fragment.text,
        None if theirs_fragment is None else theirs_fragment.text,
    )


def merge3(base: str, ours: str, theirs: str) -> MergeResult:
    """Three-way merge of three legacy-jobs manifest texts.

    See the module docstring for the keep, delete, and conflict rules.
    """
    base_frags = split(base)
    ours_frags = split(ours)
    theirs_frags = split(theirs)
    base_by, base_dups = _index(base_frags)
    ours_by, ours_dups = _index(ours_frags)
    theirs_by, theirs_dups = _index(theirs_frags)
    base_keys = _job_order(base_frags)
    ours_keys = _job_order(ours_frags)
    theirs_keys = _job_order(theirs_frags)
    repeated = set(base_dups) | set(ours_dups) | set(theirs_dups)

    if _order_differs(base_keys, ours_keys) or _order_differs(base_keys, theirs_keys):
        ours_only = _is_order_only(base_frags, ours_frags, base_keys, ours_keys)
        theirs_only = _is_order_only(
            base_frags, theirs_frags, base_keys, theirs_keys
        )
        if (
            ours_only
            and not theirs_only
            and _fragment_texts_equal(theirs_frags, base_frags)
        ):
            return MergeResult(ours, ())
        if (
            theirs_only
            and not ours_only
            and _fragment_texts_equal(ours_frags, base_frags)
        ):
            return MergeResult(theirs, ())
        if (
            ours_only
            and theirs_only
            and ours_keys == theirs_keys
            and ours == theirs
        ):
            return MergeResult(ours, ())
        if ours_only and not theirs_only and theirs_keys == base_keys:
            applied = _apply_order_and_edits(
                base_frags,
                ours_frags,
                theirs_frags,
                order_is_ours=True,
                edit_side_permuted=False,
            )
            if applied is not None:
                return applied
        if theirs_only and not ours_only and ours_keys == base_keys:
            applied = _apply_order_and_edits(
                base_frags,
                theirs_frags,
                ours_frags,
                order_is_ours=False,
                edit_side_permuted=False,
            )
            if applied is not None:
                return applied
        if ours_keys == theirs_keys and ours_only != theirs_only:
            if ours_only:
                order_frags, edit_frags, order_is_ours = (
                    ours_frags,
                    theirs_frags,
                    True,
                )
            else:
                order_frags, edit_frags, order_is_ours = (
                    theirs_frags,
                    ours_frags,
                    False,
                )
            applied = _apply_order_and_edits(
                base_frags,
                order_frags,
                edit_frags,
                order_is_ours=order_is_ours,
                edit_side_permuted=True,
            )
            if applied is not None:
                return applied
        return MergeResult(_conflict_block(ours, theirs), (ORDER_KEY,))

    dropped: set[str] = set()
    for key in base_keys:
        if key in repeated:
            continue
        text, _conflicted = _resolve_text(
            *_fragment_texts(base_by, ours_by, theirs_by, key)
        )
        if text is None:
            dropped.add(key)

    conflicts: list[str] = []
    pieces: list[str] = []

    def emit(key: str) -> None:
        if key in repeated:
            conflicts.append(key)
            pieces.append(
                _repeated_block(key, ours_dups, theirs_dups, ours_by, theirs_by)
            )
            return
        text, conflicted = _resolve_text(
            *_fragment_texts(base_by, ours_by, theirs_by, key)
        )
        if conflicted:
            conflicts.append(key)
        if text is not None:
            pieces.append(text)

    emit(PREAMBLE_KEY)
    for key in _merged_job_order(base_keys, ours_keys, theirs_keys, dropped):
        emit(key)
    emit(TRAILER_KEY)
    return MergeResult("".join(pieces), tuple(conflicts))


def format_report(fragments: list[Fragment]) -> str:
    """``jobs=N fragments=M owners={name: count, ...}`` with owners sorted."""
    counts: dict[str, int] = {}
    jobs = 0
    for fragment in fragments:
        if fragment.kind == "job":
            jobs += 1
        counts[fragment.owner] = counts.get(fragment.owner, 0) + 1
    owners = ", ".join(f"{name}: {counts[name]}" for name in sorted(counts))
    return f"jobs={jobs} fragments={len(fragments)} owners={{{owners}}}"


def _first_difference(left: bytes, right: bytes) -> int:
    limit = min(len(left), len(right))
    for index in range(limit):
        if left[index] != right[index]:
            return index
    return limit


def check_manifest(path: Path = DEFAULT_MANIFEST) -> str:
    """Return the report line, or raise ``ValueError`` when join drifts."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ValueError(f"{path} is not utf-8: {exc}") from exc
    fragments = split(text)
    rejoined = join(fragments).encode("utf-8")
    if rejoined != raw:
        offset = _first_difference(rejoined, raw)
        raise ValueError(
            f"join(split({path})) drifted at byte {offset}: "
            f"{len(rejoined)} bytes vs {len(raw)}"
        )
    return format_report(fragments)


def _merge3_main(argv: list[str]) -> int:
    """``merge3 BASE OURS THEIRS`` writes the merge to OURS.

    Exit 0 when clean and 1 when any fragment conflicts, matching a git
    merge driver invoked as ``%O %A %B``.
    """
    parser = argparse.ArgumentParser(
        prog="ci_pack_fragments.py merge3",
        description=(
            "Three-way merge a legacy-jobs manifest at job boundaries. "
            "Writes the merged text to OURS and exits 0 when clean, "
            "1 when a fragment conflicts."
        ),
    )
    parser.add_argument("base", type=Path, help="ancestor file (%%O)")
    parser.add_argument("ours", type=Path, help="current file (%%A), overwritten")
    parser.add_argument("theirs", type=Path, help="other file (%%B)")
    args = parser.parse_args(argv)
    try:
        result = merge3(
            args.base.read_text(encoding="utf-8"),
            args.ours.read_text(encoding="utf-8"),
            args.theirs.read_text(encoding="utf-8"),
        )
        args.ours.write_bytes(result.text.encode("utf-8"))
    except (OSError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for key in result.conflicts:
        print(f"conflict: {key}", file=sys.stderr)
    return 1 if result.conflicts else 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "merge3":
        return _merge3_main(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 0 iff join(split(manifest)) is byte-identical",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="manifest to check (default: .github/ci/legacy-jobs.yml)",
    )
    args = parser.parse_args(argv)
    if not args.check:
        parser.error("--check is required")
    try:
        print(check_manifest(args.manifest))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
