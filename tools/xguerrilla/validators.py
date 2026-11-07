"""Deterministic gate on every LLM draft before the composer sees it (§26.4).

The AI decides *what* to say; this module decides whether the shape is allowed.
Every failure is a human-readable string, because a rejected draft goes back to
the model as a prompt, and "check 7 failed" teaches it nothing.

The validator never rewrites. If a draft breaks a rule, the draft loses.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Sequence

KINDS = ("post", "reply", "quote")

#: Characters that may trail a sentence without being part of the last word.
_TRAIL = " \t\n.,;:!?…\"'”’)]}—-–"

#: Words that cannot end a finished thought. A post ending on one of these was
#: truncated by the model, not composed by a person.
DANGLING = frozenset({
    "and", "but", "or", "nor", "so", "yet", "because", "cuz", "cause", "plus",
    "then", "also", "with", "without", "from", "of", "to", "in", "on", "at",
    "for", "as", "than", "that", "which", "while", "if", "when", "whether",
    "like", "versus", "vs", "&", "+", "the", "a", "an", "my", "your",
})

#: Phrases that only ever come out of a model. Matched case-insensitively,
#: allowing inflection (unlock/unlocking/leveraged) and hyphen drift.
LLMISMS = (
    "delve",
    "game-changer",
    "game changer",
    "unlock",
    "in today's fast-paced",
    "revolutionize",
    "leverage",
    "seamless",
    "elevate",
    "navigate the",
    "testament to",
)

#: "not just X but Y" — the balanced-clause tic that reads as generated.
_NOT_JUST_BUT = re.compile(
    r"\b(?:not|isn'?t|aren'?t|wasn'?t|weren'?t)\s+(?:just|only|merely|simply)\b"
    r"[^.!?\n]{0,80}?\bbut\b",
    re.IGNORECASE,
)

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])(?:\s+|$)|\n+")
_HASHTAG = re.compile(r"#([A-Za-z0-9_]+)")
_WORD = re.compile(r"[A-Za-z][A-Za-z'’\-]*")
_FIRST_WORD = re.compile(r"\s*([A-Za-z'’]+)")
_URL = re.compile(r"^https?://", re.IGNORECASE)

VOICE_WINDOW = 20
DUPLICATE_RATIO = 0.82


@dataclass
class Draft:
    text: str
    kind: str = "post"                    # post | reply | quote
    read_trace_id: str | None = None      # the post that was on screen
    hashtags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)


def _norm(text: str) -> str:
    """Case- and whitespace-insensitive form for phrase matching."""
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _ism_pattern(phrase: str) -> re.Pattern:
    parts = [re.escape(p) for p in re.split(r"[\s\-]+", phrase.strip())]
    return re.compile(r"(?<![\w-])" + r"[\s\-]+".join(parts) + r"[\w]*(?![\w-])", re.IGNORECASE)


_ISM_PATTERNS = tuple((p, _ism_pattern(p)) for p in LLMISMS)


def _sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_BREAK.split(text) if s.strip()]


def _last_word(text: str) -> str:
    stripped = text.rstrip(_TRAIL)
    if not stripped:
        return ""
    return stripped.split()[-1].lower()


def _first_word(text: str) -> str:
    m = _FIRST_WORD.match(text or "")
    return m.group(1).lower() if m else ""


def _tags_in_text(text: str) -> set[str]:
    return {t.lower() for t in _HASHTAG.findall(text or "")}


def _slot_ok(link: str, slot: str | None) -> bool:
    """A link is legal only if it is the persona's own slot."""
    if not slot:
        return True
    if link.rstrip("/") == slot.rstrip("/"):
        return True
    host = re.sub(r"^https?://", "", slot.lower()).split("/")[0]
    return bool(host) and host in link.lower()


def validate(
    draft: Draft,
    persona,
    history: Sequence[str] | None = None,
    links_used_7d: int = 0,
    now: datetime | None = None,
) -> list[str]:
    """Return every violation on the draft; empty means it may be composed.

    ``history`` is the persona's recent posts, already scoped by the caller.
    ``links_used_7d`` counts links posted in the seven days ending at ``now``
    (the scheduler's clock, passed in so every gate in one run agrees).
    """
    if now is not None and not isinstance(now, datetime):
        raise TypeError(f"now must be a datetime or None, got {type(now).__name__}")

    history = list(history or ())
    text = draft.text or ""
    out: list[str] = []

    if draft.kind not in KINDS:
        out.append(f"unknown draft kind {draft.kind!r} — expected one of {', '.join(KINDS)}")
    if not text.strip():
        out.append("text is empty")
        return out

    # Length, on the persona's own ceiling (§25.6.4 caps are per child).
    if len(text) > persona.max_chars:
        out.append(f"over length: {len(text)} chars, {persona.handle}'s cap is {persona.max_chars}")

    last = _last_word(text)
    if last in DANGLING:
        out.append(f"dangling conjunction at the end: {last!r}")

    if re.search(r"[ \t]{2,}", text):
        out.append("double space")

    if text != text.rstrip():
        out.append("trailing space")

    # Hashtags: the declared list and the text must agree, and stay under budget.
    declared = {t.lstrip("#").lower() for t in draft.hashtags if t.strip()}
    found = _tags_in_text(text)
    if len(declared | found) > persona.hashtags_max:
        out.append(
            f"too many hashtags: {len(declared | found)} "
            f"(cap {persona.hashtags_max} for {persona.handle})"
        )
    missing = sorted(declared - found)
    for tag in missing:
        out.append(f"hashtag #{tag} is listed but not in the text")

    # Links: one per draft, only the persona's own slot, inside the weekly budget.
    if len(draft.links) > 1:
        out.append(f"more than one link in a draft: {len(draft.links)}")
    slot = getattr(persona, "link_slot", None)
    for link in draft.links:
        if not _URL.match(link or ""):
            out.append(f"link is not an absolute http(s) url: {link!r}")
        elif not _slot_ok(link, slot):
            out.append(f"link {link} is not {persona.handle}'s own link slot ({slot})")
    spent = links_used_7d + len(draft.links)
    if spent > persona.links_per_week:
        out.append(
            f"link budget: {links_used_7d} used in the last 7 days + "
            f"{len(draft.links)} here exceeds {persona.links_per_week}/week"
        )

    # Provenance: a reply or quote must name the read that produced it.
    if draft.kind in ("reply", "quote") and not (draft.read_trace_id or "").strip():
        out.append(f"{draft.kind} needs a read_trace_id — it must answer something that was on screen")

    opener = _first_word(text)
    if draft.kind in ("reply", "quote") and opener in ("agreed", "this"):
        out.append(f"opens with a bare {opener!r} — say the thing, not the agreement")

    # Sameness: the child's own last posts, and phrases that read as generated.
    best_ratio, best_i = 0.0, -1
    for i, prior in enumerate(history):
        ratio = difflib.SequenceMatcher(None, _norm(text), _norm(prior or "")).ratio()
        if ratio > best_ratio:
            best_ratio, best_i = ratio, i
    if best_ratio > DUPLICATE_RATIO:
        out.append(f"near-duplicate of history[{best_i}] (ratio {best_ratio:.2f} > {DUPLICATE_RATIO})")

    seen = set()
    for phrase, pattern in _ISM_PATTERNS:
        key = phrase.replace("-", " ")
        if key in seen or not pattern.search(text):
            continue
        seen.add(key)
        out.append(f"LLM-ism: {phrase!r}")

    if _NOT_JUST_BUT.search(text):
        out.append("not-just-but construction")

    em = text.count("—")
    if em > 1:
        out.append(f"{em} em dashes in one draft (max 1)")

    if persona.casing in ("lower", "lower_sometimes"):
        words = _WORD.findall(text)
        if not any(w.lower() == w for w in words):
            out.append(f"no lowercase word — {persona.handle} types {persona.casing}")

    bangs = text.count("!")
    if bangs > 1:
        out.append(f"{bangs} exclamation marks (max 1)")

    if draft.kind == "post":
        n = len(_sentences(text))
        if n > 3:
            out.append(f"{n} sentences in a post (max 3)")

    return out


def enforce_voice(draft, persona) -> list[str]:
    """Checks that only make sense across drafts, not inside one (§25.6.4, §26.8).

    ``draft`` is the newest draft, or the window of recent drafts ending with
    it. Two failures matter: a voice with no fingerprint at all — none of the
    persona's pet phrases or opinions in twenty drafts — and a child whose
    posts keep opening on the same word.
    """
    items: list = [draft] if isinstance(draft, Draft) else list(draft or ())
    recent = items[-VOICE_WINDOW:]
    if not recent:
        return ["no drafts to check voice against"]

    texts = [d.text if isinstance(d, Draft) else str(d) for d in recent]
    out: list[str] = []

    fingerprint = [p for p in (list(persona.pet_phrases) + list(persona.opinions)) if p]
    window = _norm(" \n ".join(texts))
    if fingerprint and not any(_norm(p) in window for p in fingerprint):
        out.append(
            f"voice flat: none of {persona.handle}'s pet phrases or opinions "
            f"appear in the last {len(texts)} draft{'' if len(texts) == 1 else 's'}"
        )

    for i in range(1, len(texts)):
        a, b = _first_word(texts[i - 1]), _first_word(texts[i])
        if a and a == b:
            out.append(f"drafts {i - 1} and {i} both open with {a!r}")

    return out
