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
from urllib.parse import urlsplit

from .tlds import is_tld

KINDS = ("post", "reply", "quote")

#: Deterministic gates, in the order the policy settled them:
#:   * every draft — the zero-URL rule (§26.4, bio policy BL-9), absolute for
#:     posts, replies AND quotes, with no per-account exception;
#:   * every profile bio — the one canonical destination (bio policy BL-1…BL-4,
#:     BL-10), because the bio is the only URL surface in the network.

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

# ── URLs: the bio is the only surface (bio policy v1, BL-1…BL-10) ─────────────
#: The one host a child's bio may point at. The apex is deliberately absent: it
#: 301s to `www`, so a bio using it burns a hop and doubles the host strings a
#: validator must know (BL-1).
BIO_HOST = "www.mastermind-x.com"
#: The path IS the attribution key (BL-2): the registry's immutable child id,
#: never the handle, and never a campaign parameter.
#: Registry ids are dotted (desk.and.dusk, mila.lifts, wren.mp4): a bare
#: [a-z0-9] class refuses 4 of the 5 registered children, so the shape admits
#: interior single dots only — 4-32 chars, no leading/trailing/double dot.
BIO_PATH_RE = re.compile(r"^/x/(?!.*\.\.)[a-z0-9][a-z0-9.]{2,30}[a-z0-9]$")
#: Hosts that resolve to somebody else's estate. Refused even when they redirect
#: to us: with posts and replies URL-free (BL-9) the bio is the single hop, so
#: BL-3 requires that hop to be org-controlled end to end.
SHORTENER_HOSTS = frozenset({
    "t.co", "bit.ly", "buff.ly", "ow.ly", "is.gd", "goo.gl", "tinyurl.com",
    "lnkd.in", "rebrand.ly", "cutt.ly", "shorturl.at", "trib.al",
})
_BARE_LINK_HOSTS = {
    "mastermind-x.com", "www.mastermind-x.com", *SHORTENER_HOSTS,
}
#: X autolinks a bare host too, so a URL is not only `scheme://`: the token
#: matcher also names the hosts that matter. Order matters — the scheme and
#: `www.` alternatives win at any position they can match.
#: The last alternative is the general scheme-less host: any dotted host whose
#: trailing label is a real TLD — a gate cannot maintain a list of everybody
#: else's *domains*, but the TLD *alphabet* is one versioned data file
#: (``tlds.py``/``tlds.txt``, IANA snapshot + reserved names, sha256-pinned).
#: Membership, not label shape, separates hosts from prose: "Node.js",
#: "notes.txt" and "setup.exe" end on labels that are not TLDs, while
#: "x.com/handle" ends on "com". Shape still refuses the rest: "e.g."/"i.e."
#: end on a one-letter label, "v1.2"/"2.0.1" end on a number, and a
#: sentence-final "done." carries no second label at all. Labels that are
#: BOTH a TLD and a file extension (zip, mov, app) count as TLDs — the gate
#: stays fail-closed; the collision decision is documented in ``tlds.txt``
#: and pinned by tests. Group 1 captures the trailing label so
#: ``links_in_text`` can apply the membership check.
_LINK_TOKEN = re.compile(
    r"(?i)(?:https?://[^\s<>\"'`]+"
    r"|www\.[^\s<>\"'`]+"
    r"|(?<![\w.@/-])(?:%s)(?:/[^\s<>\"'`]*)?(?![\w-])"
    r"|(?<![\w.@/-])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+([a-z]{2,})"
    r"(?![\w-]))"
    % "|".join(re.escape(h) for h in sorted(_BARE_LINK_HOSTS))
)
# Consume a general host's path only after its TLD qualifies. A rejected
# filename must not swallow a real URL later in that same slash-delimited text.
_LINK_PATH = re.compile(r"/[^\s<>\"'`]*")
#: Sentence punctuation is not part of a link.
_TRAILING = ".,;:!?)]}»’\"'"

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


def links_in_text(text: str) -> list[str]:
    """Every URL-shaped token in ``text``, in order, sentence punctuation trimmed.

    One matcher for both gates: the post/reply rule refuses ANY token, and the
    bio validator requires the single token to be the canonical destination.
    ``.strip().rstrip(_TRAILING)`` is deliberate — a bio that ends "…/x/ab12cd34."
    still carries the canonical link, while a trailing-slash variant does not
    lose its slash to punctuation cleanup.

    A match from the general scheme-less-host alternative counts only when its
    trailing label (group 1) is a real TLD: filename-shaped prose — "Node.js",
    "notes.txt", "setup.exe" — is not a link, so the zero-URL gate does not
    refuse it. Scheme, ``www.`` and the named bare hosts carry no group 1 and
    always count.
    """
    text = text or ""
    found: list[str] = []
    seen: set[str] = set()
    cursor = 0
    while match := _LINK_TOKEN.search(text, cursor):
        tail = match.group(1)
        if tail is not None and not is_tld(tail):
            # An explicit www./http(s) start can be inside the rejected dotted
            # header. Keep original-string lookbehind context when resuming.
            cursor = match.start() + 1
            continue
        end = match.end()
        if tail is not None:
            path = _LINK_PATH.match(text, end)
            if path is not None:
                end = path.end()
        cursor = end
        token = text[match.start():end].strip().rstrip(_TRAILING).strip()
        if token and token not in seen:
            seen.add(token)
            found.append(token)
    return found


def validate(
    draft: Draft,
    persona,
    history: Sequence[str] | None = None,
    links_used_7d: int = 0,
    now: datetime | None = None,
) -> list[str]:
    """Return every violation on the draft; empty means it may be composed.

    ``history`` is the persona's recent posts, already scoped by the caller.
    ``links_used_7d`` is retained for callers that still count historical
    links, but it is NO LONGER CONSULTED: the zero-URL rule has no budget, so a
    count cannot make a link legal (bio policy BL-9 replaced the one-per-week
    allowance and there is no per-account exception).
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

    # URLs — ABSOLUTE (masterplan §26.4 "Zero URLs in child posts"; bio policy
    # BL-9 "The no-URLs rule is absolute"). This replaces the one-link-per-week
    # allowance §26.4 superseded: a budget made the rule advisory (a link was
    # rationed, never refused), and it only inspected `draft.links`, so a URL
    # typed straight into the text cleared every gate. There is no per-account
    # exception and no budget left to spend on one.
    for token in links_in_text(text):
        out.append(
            f"URL in {draft.kind} text: {token!r} — posts and replies carry no "
            f"URLs at all (masterplan §26.4; bio policy BL-9)"
        )
    for link in draft.links:
        out.append(
            f"{draft.kind} declares link {link!r} — a declared link is still a "
            f"link: posts and replies carry no URLs (bio policy BL-9)"
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


# ─────────────────────────────────────────────────────────────────────────────
# The bio — the only URL surface in the whole network (bio policy v1)
# ─────────────────────────────────────────────────────────────────────────────

def canonical_bio_link(child_id: str) -> str:
    """The one destination shape the policy settles (BL-2).

    The path segment is the registry's immutable child id, never the handle:
    handles get renamed and a ref that rots is worse than no ref at all.
    """
    return f"https://{BIO_HOST}/x/{str(child_id or '').strip()}"


def _bio_link_violations(
    link: str,
    *,
    child_id: str | None,
    known_ids: Iterable[str] | None,
) -> list[str]:
    """Every BL-1…BL-4 / BL-10 violation on ONE bio link, all reported."""
    out: list[str] = []
    if link != link.lower():
        out.append(
            f"bio link {link!r} carries uppercase — the destination is a "
            f"case-sensitive attribution key (BL-10)"
        )
    if not link.lower().startswith("https://"):
        out.append(f"bio link {link!r} must be absolute https:// (BL-10)")

    parsed = urlsplit(link) if "://" in link else urlsplit("//" + link)
    host = (parsed.hostname or "").lower()
    if parsed.username or parsed.password or parsed.port:
        out.append(
            f"bio link {link!r} carries userinfo or a port — the host must be "
            f"the bare {BIO_HOST!r} (BL-1)"
        )
    if host in SHORTENER_HOSTS:
        out.append(
            f"bio link {link!r} points at the shortener {host!r} — the host "
            f"must be ours even when the shortener redirects to us (BL-3)"
        )
    elif host == "mastermind-x.com":
        out.append(
            f"bio link {link!r} uses the apex mastermind-x.com, which 301s to "
            f"www — use https://{BIO_HOST} (BL-1)"
        )
    elif host != BIO_HOST:
        out.append(f"bio link host {host!r} is not {BIO_HOST!r} (BL-1)")

    path = parsed.path or ""
    if parsed.query:
        out.append(
            f"bio link {link!r} carries a query string — attribution is the "
            f"path segment, not a campaign parameter (BL-2)"
        )
    if parsed.fragment:
        out.append(
            f"bio link {link!r} carries a fragment — the destination ends at "
            f"the child id (BL-2)"
        )
    if path != "/" and path.endswith("/"):
        out.append(
            f"bio link {link!r} has a trailing slash — the canonical form ends "
            f"at the child id (BL-10)"
        )
    elif not BIO_PATH_RE.fullmatch(path):
        out.append(
            f"bio link path {path!r} is not the settled destination shape "
            f"/x/<4-32 lowercase letters/digits with single interior dots> (BL-2)"
        )

    if BIO_PATH_RE.fullmatch(path):
        slug = path[len("/x/"):]
        if child_id is not None:
            wanted = str(child_id or "").strip()
            if not BIO_PATH_RE.fullmatch(f"/x/{wanted}"):
                out.append(
                    f"child_id {child_id!r} is not a valid attribution key "
                    f"(4-32 lowercase letters/digits with single interior dots) — "
                    f"the path cannot bind to it"
                )
            elif path != f"/x/{wanted}":
                out.append(
                    f"bio link path {path!r} is not this child's attribution "
                    f"key /x/{wanted} (BL-2)"
                )
        if known_ids is not None and slug not in {str(k) for k in known_ids}:
            out.append(
                f"bio link names child id {slug!r}, which is not in the registry"
            )
    return out


def validate_bio(
    text: str,
    *,
    child_id: str | None = None,
    known_ids: Iterable[str] | None = None,
    display_name: str = "",
) -> list[str]:
    """Every violation on a profile bio; empty means it may be provisioned.

    The bio is the ONLY URL surface in the network: posts, replies and quotes
    carry none (``validate``), so this one link decides what every child can say
    and where the reader's next request lands. Deterministic and complete —
    the validator never rewrites, it refuses.

    ``display_name`` is checked because BL-4 says nothing else in the profile is
    linkable. ``child_id`` (when given) binds the path to THIS child's registry
    id; ``known_ids`` (when given) refuses a path naming an id nobody registered.
    BL-5's disclosure presence is deliberately NOT machine-judged: the wording is
    the Chairman's, and "states organisation control" is a human reading.
    """
    out: list[str] = []

    for token in links_in_text(display_name or ""):
        out.append(
            f"display name carries a URL: {token!r} — nothing else in the "
            f"profile is linkable (BL-4)"
        )

    links = links_in_text(text or "")
    if not links:
        out.append(
            "bio carries no URL — the bio is the only link surface, so it must "
            f"carry exactly https://{BIO_HOST}/x/<child-id> (BL-1)"
        )
        return out
    if len(links) > 1:
        out.append(
            f"{len(links)} URLs in the bio — exactly one is allowed, and it "
            f"must be the child's own attribution link (BL-1)"
        )
    for link in links:
        out.extend(_bio_link_violations(
            link, child_id=child_id, known_ids=known_ids))
    return out
