"""Transcript-local source identity law for deterministic Q&A reconstruction (TFG-1 R2).

Internal helper for :mod:`engine.company_intelligence.qa_reconstruction`. It carries the
frozen source-native separator / questioner / respondent-role law and nothing else.

Law summary (see ``research/earnings_intelligence/e3/TFG1_R2_*``):

* Terminal cue phrases ("go ahead", "your line is now live") have ZERO admission
  authority. A separator is an unambiguous question-bearing housekeeping handoff that
  names a questioner and is followed by a non-housekeeping source turn.
* A separator stays load-bearing when questioner identity is unresolved: it splits
  windows but may not mint canonical Q&A.
* Direct questioner identity requires exact source-name equality after case/whitespace
  normalization only. A differing full-name next speaker is accepted only when that
  speaker's own first utterance explicitly binds them as standing in for the named
  principal, and states their own full name.
* Respondent role evidence comes only from the same transcript revision: the answer
  segment role, or a replayable participant/title declaration in that revision.
* Role comparison aliases are closed: CEO, CFO, COO. There is no CIO alias.

No ticker, issuer, provider or boundary-index literal appears in this module. No model
call, edit distance, nickname map, initials expansion or external lookup is performed.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

HOUSEKEEPING_ROLES = frozenset({"operator", "ir"})

# Case-sensitive even under IGNORECASE cues, and period-free, so a name can never run
# across a sentence boundary into a following return clause.
_NAME = r"(?-i:[A-Z][A-Za-zÀ-ɏ'’\-]*(?:\s+[A-Z][A-Za-zÀ-ɏ'’\-]*){0,3})"

# A question is attributed to a named person within one sentence.
_ATTRIB = re.compile(
    r"\bquestions?\b[^.?!]{0,60}?\b(?:from|of|the\s+line\s+of)\s+(?:the\s+line\s+of\s+)?"
    r"(?P<name>" + _NAME + r")",
    re.IGNORECASE,
)
_ATTRIB_CONT = re.compile(
    r"\bquestions?\b[^.?!]{0,40}[.]\s*(?:It(?:'s|’s| is)|This is)\s+from\s+"
    r"(?P<name>" + _NAME + r")",
    re.IGNORECASE,
)
_CONTINUE = re.compile(
    r"\b(?:we(?:'ll|’ll| will| shall)?\s+)?(?:now\s+)?(?:mov(?:e|ing)\s+on|go)\s+"
    r"(?:on\s+)?(?:now\s+)?to\s+(?P<name>" + _NAME + r")",
    re.IGNORECASE,
)
# Returns to management and opening prepared-speaker handoffs are never separators.
_RETURN = re.compile(
    r"\b(?:turn|hand|pass|give|send)\b[^.?!]{0,60}?\bback\b|\bback\s+(?:over\s+)?to\b"
    r"|\b(?:turn|hand)\s+(?:the\s+)?(?:call|conference|floor|program|meeting)\s+over\s+to\b",
    re.IGNORECASE,
)

# Explicit stand-in binding spoken by the stand-in themselves.
_PROXY = re.compile(
    r"(?:it(?:'s|’s| is)\s+(?:actually\s+)?|this\s+is\s+(?:actually\s+)?|i(?:'m|’m| am)\s+)"
    r"(?P<proxy>" + _NAME + r")"
    r"\s+(?:on|in|sitting\s+in|standing\s+in|filling\s+in)\s+for\s+"
    r"(?P<principal>" + _NAME + r")",
    re.IGNORECASE,
)

# Closed role alias set. CIO is deliberately absent.
_ROLE_ALIASES: tuple[tuple[str, str], ...] = (
    ("chief executive officer", "CEO"),
    ("chief financial officer", "CFO"),
    ("chief operating officer", "COO"),
)
_CANONICAL_ROLES = frozenset(canonical for _, canonical in _ROLE_ALIASES)


def norm(value: Any) -> str:
    return " ".join(str(value or "").split())


def norm_person(value: Any) -> str:
    return norm(value).casefold()


def role_key(segment: Mapping[str, Any]) -> str:
    return norm(segment.get("role")).casefold()


def speaker_name(segment: Mapping[str, Any]) -> str:
    return norm(segment.get("speaker"))


def is_housekeeping(segment: Mapping[str, Any]) -> bool:
    role = role_key(segment)
    speaker = norm_person(segment.get("speaker"))
    return role in HOUSEKEEPING_ROLES or speaker == "operator" or speaker.endswith(" operator")


def canonical_role(value: Any) -> str:
    """Canonicalize through the closed alias set; otherwise normalize literally."""
    text = norm(value)
    folded = text.casefold()
    for phrase, canonical in _ROLE_ALIASES:
        if folded == phrase or folded == canonical.casefold():
            return canonical
    return folded


def _return_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in _RETURN.finditer(text):
        end = text.find(".", match.end())
        spans.append((match.start(), len(text) if end < 0 else end))
    return spans


def handoff_name(text: Any) -> str | None:
    """Return the named questioner of a question-bearing handoff, else ``None``."""
    body = norm(text)
    blocked = _return_spans(body)
    hits: list[tuple[int, str]] = []
    for pattern in (_ATTRIB, _ATTRIB_CONT, _CONTINUE):
        for match in pattern.finditer(body):
            position = match.start("name")
            if any(low <= position <= high for low, high in blocked):
                continue
            hits.append((position, match.group("name").strip(" ,.")))
    if not hits:
        return None
    hits.sort()
    return hits[-1][1]


def next_source_turn(segments: Sequence[Mapping[str, Any]], index: int) -> int | None:
    """First following turn that is neither housekeeping nor anonymous."""
    for candidate in range(index + 1, len(segments)):
        segment = segments[candidate]
        if role_key(segment) in HOUSEKEEPING_ROLES:
            continue
        if not speaker_name(segment):
            continue
        return candidate
    return None


def structural_separators(segments: Sequence[Mapping[str, Any]]) -> list[int]:
    """Indexes of question-bearing handoffs followed by a real source turn."""
    return [
        index
        for index, segment in enumerate(segments)
        if is_housekeeping(segment)
        and handoff_name(segment.get("text"))
        and next_source_turn(segments, index) is not None
    ]


def _is_full_name(value: str) -> bool:
    return len(norm(value).split()) >= 2


def resolve_questioner(
    segments: Sequence[Mapping[str, Any]], separator_index: int
) -> dict[str, Any]:
    """Classify the questioner at a separator as direct, proxy or unresolved."""
    named = handoff_name(segments[separator_index].get("text"))
    turn = next_source_turn(segments, separator_index)
    if turn is None:
        return {"state": "unresolved", "reason": "no_source_turn_after_handoff"}
    speaker = speaker_name(segments[turn])
    base = {"operator_named": named or "", "speaker_index": turn, "speaker": speaker}
    if named and norm_person(named) == norm_person(speaker):
        return {**base, "state": "direct", "name": speaker, "principal": ""}
    match = _PROXY.search(norm(segments[turn].get("text")))
    if match:
        proxy = match.group("proxy").strip(" ,.")
        principal = match.group("principal").strip(" ,.")
        # A stand-in is source-supported only when they state their own full name and
        # that name is exactly this turn's structured speaker. No repair of any kind.
        if _is_full_name(proxy) and norm_person(proxy) == norm_person(speaker):
            return {**base, "state": "proxy", "name": speaker, "principal": principal}
    return {**base, "state": "unresolved", "reason": "questioner_not_source_supported"}


_HONORIFIC = r"(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+"

# Officer/role titles a transcript may declare. Membership here only makes a title
# VISIBLE as declared evidence; equivalence is still governed by the closed alias set,
# so a declared title outside that set can never silently satisfy a segment role.
_TITLE_PHRASE = re.compile(
    r"\b(chief\s+[A-Za-z]+(?:\s+[A-Za-z]+)?\s+officer|chief\s+[A-Z][a-z]+|chief\s+executive|"
    r"CEO|CFO|COO|CIO|CTO|CAO|"
    r"(?:senior\s+|executive\s+)?vice\s+president|president|chairman|chairwoman|"
    r"treasurer|managing\s+director|head\s+of\s+[A-Za-z]+)\b",
    re.IGNORECASE,
)
# A declaration clause ends at the next declared person, a relative clause, or the
# sentence end, so titles can never bleed from one person to another.
_CLAUSE_END = re.compile(r",\s*(?:who|which|that)\b", re.IGNORECASE)

# A speaker stating their OWN role is same-revision participant evidence. The binding
# must be grammatical, not mere co-occurrence: "I am the CFO" / "I will be stepping down
# as CFO" bind, while "I want to thank our CFO" does not.
_SELF_ROLE = re.compile(
    r"\bI\s+(?:am|'m|’m|was)\s+(?:the\s+|our\s+)?(?P<direct>{t})"
    r"|\bI\s+(?:am|'m|’m|was|will\s+be|have\s+been|had\s+been)\s+[a-z ]{{0,30}}?\bas\s+"
    r"(?:the\s+|our\s+)?(?P<transition>{t})"
    r"|\bmy\s+(?:role|position)\s+as\s+(?:the\s+|our\s+)?(?P<role_as>{t})".format(
        t=r"(?:chief\s+[A-Za-z]+(?:\s+[A-Za-z]+)?\s+officer|chief\s+[A-Z][a-z]+"
          r"|CEO|CFO|COO|CIO|CTO|CAO|president|chairman|chairwoman|treasurer)"
    ),
    re.IGNORECASE,
)

# Person-shaped names are used ONLY to terminate a declaration clause, never to bind a
# role. A declared participant who is not a speaker in this revision must still stop the
# preceding person's title clause, or titles bleed across people.
_PERSON_SHAPE = re.compile(
    r"(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Professor)\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'’\-]*"
    r"(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'’\-]*){0,3}"
    r"|[A-ZÀ-Ý][A-Za-zÀ-ÿ'’\-]+\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'’\-]+"
)


def _sentences(text: str) -> list[tuple[int, str]]:
    out, cursor = [], 0
    for piece in re.split(r"(?<=[.!?])\s+", text):
        out.append((cursor, piece))
        cursor += len(piece) + 1
    return out


def _alias_matches(declared: str, speaker: str) -> bool:
    """A declared name binds a speaker only as an exact contiguous source-native alias."""
    left = norm_person(declared).split()
    right = norm_person(speaker).split()
    if not left or not right:
        return False
    if left == right:
        return True
    short, long_ = (left, right) if len(left) <= len(right) else (right, left)
    if len(short) < 2:
        return False
    span = len(short)
    return any(long_[i : i + span] == short for i in range(len(long_) - span + 1))


def _speaker_mentions(sentence: str, speakers: Sequence[str]) -> list[tuple[int, int, str]]:
    """Locate each revision speaker (or a unique contiguous alias) inside one sentence."""
    hits: list[tuple[int, int, str]] = []
    folded = sentence.casefold()
    for speaker in speakers:
        tokens = norm_person(speaker).split()
        # Try the full name first, then progressively shorter contiguous aliases, so
        # "Raul Jacob" can bind "Raul Jacob Ruisanchez" without any fuzzy matching.
        for width in range(len(tokens), 1, -1):
            found = False
            for offset in range(len(tokens) - width + 1):
                needle = " ".join(tokens[offset : offset + width])
                position = folded.find(needle)
                while position >= 0:
                    hits.append((position, position + len(needle), speaker))
                    found = True
                    position = folded.find(needle, position + 1)
            if found:
                break
    # An alias claimed by more than one speaker in this revision is ambiguous and binds
    # nobody. Without this, "Jordan Lee, our CFO" would role both Jordan Lee and
    # Jordan Lee Smith from a single declaration.
    claimed: dict[tuple[int, int], set[str]] = {}
    for start, end, speaker in hits:
        claimed.setdefault((start, end), set()).add(speaker)
    hits = [h for h in hits if len(claimed[(h[0], h[1])]) == 1]
    hits.sort()
    return hits


def _titles_in(clause: str) -> dict[str, str]:
    """Canonical title -> the exact source-cased phrase that evidenced it."""
    cut = _CLAUSE_END.search(clause)
    if cut:
        clause = clause[: cut.start()]
    found: dict[str, str] = {}
    for match in _TITLE_PHRASE.finditer(clause):
        found.setdefault(canonical_role(match.group(0)), norm(match.group(0)))
    return found


def declared_titles(
    segments: Sequence[Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Same-revision participant/title declarations, keyed by normalized speaker.

    Anchored on this revision's own speaker set rather than on generic name grammar, so
    a company name can never be read as a person. Within one sentence the declaration
    order (``Name, Title`` vs ``Title, Name``) is decided once, from whichever appears
    first, and applied consistently.
    """
    speakers = sorted(
        {
            speaker_name(segment)
            for segment in segments
            if speaker_name(segment) and not is_housekeeping(segment)
        }
    )
    out: dict[str, dict[str, Any]] = {}
    for index, segment in enumerate(segments):
        text = norm(segment.get("text"))
        if not text:
            continue
        speaker_here = speaker_name(segment)
        for _, sentence in _sentences(text):
            if speaker_here and not is_housekeeping(segment):
                for match in _SELF_ROLE.finditer(sentence):
                    spoken = next(
                        (g for g in match.groupdict().values() if g), ""
                    )
                    if not spoken:
                        continue
                    canonical = canonical_role(spoken)
                    entry = out.setdefault(
                        norm_person(speaker_here),
                        {
                            "speaker": speaker_here,
                            "titles": set(),
                            "phrases": {},
                            "declarations": [],
                        },
                    )
                    entry["titles"].add(canonical)
                    entry["phrases"].setdefault(canonical, norm(spoken))
                    entry["declarations"].append(
                        {
                            "segment_index": index,
                            "title_phrase": norm(match.group(0)),
                            "titles": [canonical],
                        }
                    )
            mentions = _speaker_mentions(sentence, speakers)
            if not mentions:
                continue
            titles = list(_TITLE_PHRASE.finditer(sentence))
            if not titles:
                continue
            title_spans = [(t.start(), t.end()) for t in titles]
            # A multi-word title ("Chief Executive Officer", "Apple CEO") is itself
            # capitalized and would otherwise read as a person, flipping declaration
            # order and truncating clauses. Titles are never person candidates.
            stops = [
                (m.start(), m.end())
                for m in _PERSON_SHAPE.finditer(sentence)
                if not any(m.start() < hi and lo < m.end() for lo, hi in title_spans)
            ]
            # Declaration order is decided from ALL declared persons, not only those who
            # speak in this revision, so a roster naming a non-speaker first cannot flip
            # the order and hand one person another person's title.
            first_person = min([a for a, _ in stops] + [m[0] for m in mentions])
            title_first = titles[0].start() < first_person
            for position, end, speaker in mentions:
                if title_first:
                    previous = [t for t in titles if t.end() <= position]
                    if not previous:
                        continue
                    anchor = previous[-1]
                    earlier = [b for _, b in stops if b <= anchor.start()]
                    lower = max(earlier) if earlier else 0
                    clause = sentence[lower:position]
                else:
                    following = [t for t in titles if t.start() >= end]
                    if not following:
                        continue
                    anchor = following[0]
                    later = [a for a, _ in stops if a >= anchor.end()]
                    upper = min(later) if later else len(sentence)
                    clause = sentence[end:upper]
                found = _titles_in(clause)
                if not found:
                    continue
                entry = out.setdefault(
                    norm_person(speaker),
                    {"speaker": speaker, "titles": set(), "phrases": {}, "declarations": []},
                )
                entry["titles"].update(found)
                for canonical, phrase in found.items():
                    entry["phrases"].setdefault(canonical, phrase)
                entry["declarations"].append(
                    {
                        "segment_index": index,
                        "title_phrase": norm(clause).strip(" ,"),
                        "titles": sorted(found),
                    }
                )
    return out


def roster(segments: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Speakers bound to exactly one source-declared role in this revision.

    The closed alias set only decides which of several declared titles is the officer
    role; it never limits which source titles may be published. A published role is the
    exact source-cased phrase, never a generic substitute.
    """
    out: dict[str, dict[str, Any]] = {}
    for key, entry in declared_titles(segments).items():
        titles = entry["titles"]
        closed = {t for t in titles if t in _CANONICAL_ROLES}
        if len(closed) == 1:
            chosen = next(iter(closed))
        elif len(titles) == 1:
            chosen = next(iter(titles))
        else:
            continue
        out[key] = {
            "speaker": entry["speaker"],
            "role": entry["phrases"].get(chosen, chosen) if chosen not in _CANONICAL_ROLES else chosen,
            "declared_titles": sorted(titles),
            "declarations": entry["declarations"],
        }
    return out


def role_conflict(
    segments: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Speakers whose explicit segment role is absent from their declared titles."""
    declared = declared_titles(segments)
    seen: dict[str, str] = {}
    for segment in segments:
        speaker = speaker_name(segment)
        role = norm(segment.get("role"))
        if not speaker or not role or is_housekeeping(segment):
            continue
        seen.setdefault(norm_person(speaker), role)
    conflicts: list[dict[str, Any]] = []
    for key, role in seen.items():
        entry = declared.get(key)
        if not entry or not entry["titles"]:
            continue
        if canonical_role(role) not in entry["titles"]:
            conflicts.append(
                {
                    "speaker": entry["speaker"],
                    "segment_role": canonical_role(role),
                    "declared_titles": sorted(entry["titles"]),
                    "declaration_segments": sorted(
                        {d["segment_index"] for d in entry["declarations"]}
                    ),
                }
            )
    return sorted(conflicts, key=lambda c: c["speaker"])
