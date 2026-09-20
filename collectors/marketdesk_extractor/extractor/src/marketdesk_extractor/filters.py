"""Institution/topic EXCLUSION filter — drop genuine noise before it enters the queue.

The account is download-capped (~75 / rolling-24h per account) and weekday posting
volume (~208/day) exceeds 2-account capacity (~150/day), so a wasted pull is
expensive. This module decides, from cheap already-known metadata (institution +
title), whether a paper is low-value enough to never become a download candidate.

Everything in the CLASSIFY path is PURE (no DB, no network, no clock, no config
object) so the policy is trivially unit-testable and the pattern list can be tuned
with confidence. The classifier returns a short REASON tag when a paper should be
excluded (so the operator can audit false positives per-reason) and ``None`` when it
should stay downloadable.

Excluded papers are marked with ``Status.SKIPPED_EXCLUDED`` (schemas.py) — a NEW
terminal status. The allocator's ``_CANDIDATE_STATUSES`` is only DISCOVERED +
BLOB_FOUND, so any other status is automatically kept out of the download queue.

Reason tags:
  * ``"institution"`` — publisher is a blog/newsletter (or a German-language desk
                        such as Zürcher Kantonalbank) on the exclude set.
  * ``"blog"``        — (reserved) currently folded into ``"institution"``; kept as
                        a distinct documented tag so a future title-based blog rule
                        can use it without a schema change.
  * ``"fx_daily"``    — a daily FX snapshot/wrap (NOT real FX strategy/insights).
  * ``"minor_geo"``   — a single-country note on a minor economy we don't trade.
  * ``"language"``    — the title is GERMAN. We cannot read it, so it can never be
                        worth a download slot no matter what it is about (see
                        ``looks_german``). Deliberately NOT under the major-economy
                        veto: a German-language note about the Fed is still
                        unreadable to us.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

from . import db
from .schemas import Status
from .utils import get_logger

log = get_logger("filters")


# ---------------------------------------------------------------------------
# Embedded DEFAULTS (config-overridable — see config.py / .env.example)
# ---------------------------------------------------------------------------

# Blogs / newsletters that are never worth a download slot. Matched
# case-insensitively against the NORMALIZED institution (lower-cased, whitespace
# collapsed). Keep these lowercase — normalization lower-cases both sides.
DEFAULT_EXCLUDE_INSTITUTIONS: set[str] = {
    "the market ear",
    "tme",
    "zero hedge",
    # Zürcher Kantonalbank publishes German-language Swiss single-name notes
    # ("Ersteinschätzung <name>", "ZKB+Intraday <name>"). Sampled production
    # corpus: ALL 28 ZKB rows are Swiss single-name notes, and many carry NO
    # German function words at all ("Schindler 20260724 en"), so the title-side
    # language rule cannot catch them — the institution IS the signal. The
    # production ``institution`` column is literally "ZKB"; the spelled-out
    # forms (with and without the umlaut) are listed for other feeds.
    "zkb",
    "zürcher kantonalbank",
    "zurcher kantonalbank",
}

# Title patterns. Each is ``(tag, raw_regex)``; compiled with re.I below. The
# classifier returns the FIRST matching pattern's tag, so order = priority.
#
# fx_daily MUST match daily FX wraps/snapshots but MUST NOT match real research
# such as "FX Strategy" / "FX Insights" — hence the tight ``fx <daily|snapshot>``
# / ``daily fx snapshot`` shapes rather than a bare ``\bfx\b``.
#
# minor_geo is a SINGLE word-boundary alternation of minor-economy names we do not
# trade. It deliberately EXCLUDES every major economy (US/China/Japan/Korea/Taiwan/
# India/UK/Germany/France/Italy/Spain/Eurozone/Europe/Singapore + their central
# banks) so those stay downloadable — see ``_MAJOR_ECONOMY_GUARD`` and the tests.
#
# The ``language`` entry is a PLACEHOLDER regex that can never match: the German
# rule is not expressible as one readable regex (it counts DISTINCT stopwords and
# asks where an umlaut sits), so ``classify_exclusion_tagged`` dispatches the
# ``language`` tag to the pure ``looks_german`` predicate instead of calling
# ``.search``. Keeping it as a spec entry is what makes the rule ride along with
# ``cfg.exclude_title_patterns_enabled`` — when title patterns are disabled the
# caller passes an empty pattern list and the language check is off with them.
# It is FIRST because "we cannot read it" outranks every topical reason.
_LANGUAGE_PLACEHOLDER_REGEX = r"(?!x)x"  # never matches, by construction

_DEFAULT_TITLE_PATTERN_SPECS: list[tuple[str, str]] = [
    ("language", _LANGUAGE_PLACEHOLDER_REGEX),
    ("fx_daily", r"\bfx\s+(?:daily|snapshot)\b"),
    ("fx_daily", r"\bdaily\s+fx\s+snapshot\b"),
    (
        "minor_geo",
        r"\b(?:"
        r"czech|czechia|hungary|hungarian|poland|polish|romania|romanian|"
        r"bulgaria|slovak|slovakia|croatia|serbia|"
        r"malaysia|malaysian|indonesia|indonesian|thailand|thai|"
        r"philippines|philippine|vietnam|new\s+zealand|australia|australian|"
        r"chile|chilean|colombia|peru|peruvian|argentina|argentine|"
        r"turkey|turkish|south\s+africa|nigeria|egypt|morocco|"
        r"norway|norwegian|sweden|swedish|denmark|danish|finland|finnish|"
        r"iceland|portugal|greece|greek|austria|austrian|ireland|irish|"
        r"switzerland|swiss"
        r")\b",
    ),
]

# Major economies that must NEVER be excluded. Two roles:
#   1. None of these tokens appears in the minor_geo alternation above (so a
#      single-topic major note never trips minor_geo in the first place); and
#   2. they are compiled into an ACTIVE guard (``_MAJOR_ECONOMY_RE``) that VETOES a
#      minor_geo hit whenever a major token is ALSO present — e.g. a paper titled
#      "China–Australia iron ore" is about China (major) and must stay downloadable
#      even though it mentions Australia (minor). Word-boundary anchored so
#      "us"/"uk" don't match inside larger words (superuser, Zealand, …).
# The guard applies ONLY to the geographic minor_geo reason: a blog is noise
# regardless of what it mentions, and an FX daily wrap is a daily wrap regardless.
_MAJOR_ECONOMY_GUARD: tuple[str, ...] = (
    "united states", "us", "usa", "china", "chinese", "japan", "japanese",
    "korea", "korean", "taiwan", "india", "indian", "united kingdom", "uk",
    "britain", "british", "germany", "german", "france", "french", "italy",
    "spain", "spanish", "eurozone", "europe", "european", "ecb", "fed", "boj",
    "pboc", "singapore",
)

# Longest-first so multi-word tokens ("united states") win over their fragments;
# each token is \b-anchored. re.I applied at compile.
_MAJOR_ECONOMY_RE: re.Pattern = re.compile(
    r"\b(?:"
    + "|".join(re.escape(tok).replace(r"\ ", r"\s+")
               for tok in sorted(_MAJOR_ECONOMY_GUARD, key=len, reverse=True))
    + r")\b",
    re.I,
)

# Reasons whose match is VETOED when a major economy is also present in the title.
# ``language`` is deliberately NOT here: a German note about the Fed is about a
# major economy AND still unreadable to us, so the veto must not rescue it.
_MAJOR_GUARDED_REASONS = frozenset({"minor_geo"})

# Second veto for the SAME guarded reasons: a US-style ticker in parentheses.
# A single-name note on a listed company is about the COMPANY, not the country it
# happens to mention — observed false positive: "The Brink's Co. (BCO) Updating
# estimates to reflect Malaysia business deconsolidation" (a US security) tripped
# minor_geo on "Malaysia". 1–5 UPPERCASE letters (optionally a .XX class/venue
# suffix) keeps this away from European RIC-style tags like "(DB1Gn.DE)", whose
# lowercase letters make them fail the match — those aren't US names, and a
# minor-geo hit alongside one is usually a genuinely minor-market note.
_TICKER_PARENS_RE: re.Pattern = re.compile(r"\([A-Z]{1,5}(?:\.[A-Z]{1,2})?\)")


# ---------------------------------------------------------------------------
# German-language detection (reason tag ``"language"``) — pure, title-only
# ---------------------------------------------------------------------------
# A German-language note is worthless to us regardless of topic, so it must never
# spend one of the ~70 daily download slots. Detection is a pure function of the
# TITLE (no language-id dependency, no network) built from three tiers of
# evidence, tuned so a plain-English title with ONE incidental German-looking
# token stays downloadable ("Zurich Insurance", "Munich Re", "Über-bull",
# "rates und ..."):
#
#   TIER 1 (strong, one hit is enough): an unambiguously-German FINANCE word.
#     Real production titles are frequently otherwise-empty of grammar —
#     "Ersteinschätzung Orell Füssli EN 2026 07 24 317236" contains no function
#     words at all — so a stopword-count heuristic alone MISSES them.
#   TIER 2: an umlaut on a word that is NOT itself one of the matched stopwords,
#     PLUS at least one stopword. (Requiring the umlaut to sit outside the
#     stopword hit is what keeps "Über-bull" downloadable: there the ONLY
#     evidence is the single word "über".)
#   TIER 3: two or more DISTINCT German stopwords.
#   Plus: an ``ß`` anywhere is decisive on its own — the character does not occur
#     in English.
#
# Every strong word is matched in its native, umlaut-stripped ("ersteinschatzung")
# and umlaut-transliterated ("ersteinschaetzung") spellings, because feeds
# ASCII-fold inconsistently.
_GERMAN_STRONG_WORDS: tuple[str, ...] = (
    "ersteinschätzung", "einschätzung", "wochenausblick", "monatsausblick",
    "jahresausblick", "aktienmarkt", "aktienmärkte", "konjunktur", "anleihen",
    "unternehmensanleihen", "geldpolitik", "zinsentscheid",
    "marktkommentar", "wochenbericht", "wirtschaft", "zinsen",
)
# NOTE: "börse" was tried in the strong tier and REMOVED after checking the
# 30k-row production corpus — its ASCII-digraph spelling is a company name
# ("Deutsche Boerse AG (DB1Gn.DE) Updating estimates post 2Q results"), and it
# false-flagged 9 English Goldman/Barclays notes. It lives in the weak tier
# below, where it needs a second signal. Any new strong word must survive the
# same check.

# Common German function/finance words. Individually weak (several are also
# English tokens or acronyms — "im", "mit", "von"), so TWO distinct hits (or one
# plus an umlaut elsewhere) are required before they exclude anything.
_GERMAN_STOPWORDS: tuple[str, ...] = (
    "und", "für", "über", "nicht", "mit", "von", "im", "zum", "zur", "bei",
    "nach", "auch", "wird", "sind", "bleibt", "weiterhin", "aktien", "märkte",
    "ausblick", "des", "dem", "ist", "sich", "eine", "einer", "werden", "börse",
)

_UMLAUT_CHARS = "äöüÄÖÜ"
_UMLAUT_RE: re.Pattern = re.compile(f"[{_UMLAUT_CHARS}]")
# Letter runs only, so "20260724" / "EN" style filename noise is ignored and a
# hyphenated compound ("Über-bull") splits into its parts.
_WORD_RE: re.Pattern = re.compile(r"[^\W\d_]+", re.UNICODE)

_UMLAUT_SIMPLE = {"ä": "a", "ö": "o", "ü": "u", "ß": "ss"}
_UMLAUT_DIGRAPH = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def _fold(word: str, table: dict[str, str]) -> str:
    return "".join(table.get(ch, ch) for ch in word)


def _spelling_variants(word: str) -> set[str]:
    """A German word in its native, umlaut-stripped, and transliterated spellings."""
    w = word.lower()
    return {w, _fold(w, _UMLAUT_SIMPLE), _fold(w, _UMLAUT_DIGRAPH)}


def _word_alternation(words: tuple[str, ...]) -> re.Pattern:
    """One \\b-anchored, case-insensitive alternation over every spelling variant.

    Longest-first so a compound ("unternehmensanleihen") wins over its suffix
    ("anleihen") when both could match at the same position.
    """
    variants = sorted(
        {v for w in words for v in _spelling_variants(w)}, key=len, reverse=True
    )
    return re.compile(r"\b(?:" + "|".join(re.escape(v) for v in variants) + r")\b", re.I)


_GERMAN_STRONG_RE: re.Pattern = _word_alternation(_GERMAN_STRONG_WORDS)
_GERMAN_STOPWORD_RE: re.Pattern = _word_alternation(_GERMAN_STOPWORDS)


def looks_german(title: str | None) -> bool:
    """Is this title German? PURE — title in, bool out (see the tiers above).

    Conservative by construction: it errs toward KEEPING a paper, because a false
    positive silently deletes readable research from the queue while a false
    negative costs one download slot.
    """
    t = title or ""
    if not t:
        return False
    if "ß" in t:
        return True
    if _GERMAN_STRONG_RE.search(t):
        return True

    stopwords = {m.group(0).lower() for m in _GERMAN_STOPWORD_RE.finditer(t)}
    if len(stopwords) >= 2:
        return True
    if not stopwords:
        return False
    # TIER 2: the umlaut must be evidence BEYOND the stopword hit itself.
    return any(
        _UMLAUT_RE.search(w) and w.lower() not in stopwords
        for w in _WORD_RE.findall(t)
    )


def default_title_patterns() -> list[re.Pattern]:
    """Compile the embedded default title patterns (with re.I), in priority order.

    A fresh list of compiled patterns each call keeps the module import-safe. The
    reason tag for each pattern is recovered from its source regex via
    ``_SPEC_TAG_BY_REGEX`` inside ``classify_exclusion`` (a ``re.Pattern`` cannot
    carry a free attribute); callers wanting explicit tags use
    ``default_tagged_patterns``.
    """
    return [re.compile(rx, re.I) for _tag, rx in _DEFAULT_TITLE_PATTERN_SPECS]


def default_tagged_patterns() -> list[tuple[str, re.Pattern]]:
    """``(tag, compiled_pattern)`` pairs for the embedded defaults, in priority order."""
    return [(tag, re.compile(rx, re.I)) for tag, rx in _DEFAULT_TITLE_PATTERN_SPECS]


def _normalize_institution(institution: str | None) -> str:
    return re.sub(r"\s+", " ", (institution or "").strip().lower())


def _normalize_exclude_set(exclude_institutions: set[str] | None) -> set[str]:
    return {_normalize_institution(x) for x in (exclude_institutions or set()) if x and x.strip()}


def classify_exclusion(
    institution: str | None,
    title: str | None,
    *,
    exclude_institutions: set[str],
    title_patterns: list[re.Pattern],
) -> str | None:
    """Return a short REASON tag if the paper should be EXCLUDED, else ``None``.

    Case-insensitive. Institution is matched (exact, after normalization) against
    ``exclude_institutions``; title is matched against the compiled
    ``title_patterns`` and the FIRST hit's tag is returned.

    ``title_patterns`` is a plain list of compiled patterns (the public signature
    the task specifies). Because ``re.Pattern`` cannot carry a free tag attribute,
    this function derives each pattern's tag by matching its ``.pattern`` string
    against the embedded default specs; a pattern with no known tag falls back to
    the generic ``"title"`` tag. Callers that want custom tags should route through
    ``classify_exclusion_tagged``.
    """
    tagged = [(_tag_for_pattern(p), p) for p in (title_patterns or [])]
    return classify_exclusion_tagged(
        institution, title,
        exclude_institutions=exclude_institutions,
        tagged_patterns=tagged,
    )


def classify_exclusion_tagged(
    institution: str | None,
    title: str | None,
    *,
    exclude_institutions: set[str],
    tagged_patterns: list[tuple[str, re.Pattern]],
) -> str | None:
    """Tag-carrying variant of :func:`classify_exclusion` (internal workhorse).

    One entry is special-cased: a pattern tagged ``"language"`` is evaluated with
    :func:`looks_german` rather than its (placeholder) regex — see the spec table.
    """
    inst_norm = _normalize_institution(institution)
    if inst_norm and inst_norm in _normalize_exclude_set(exclude_institutions):
        return "institution"

    t = title or ""
    if not t:
        return None

    has_major = bool(_MAJOR_ECONOMY_RE.search(t))
    has_ticker = bool(_TICKER_PARENS_RE.search(t))
    for tag, pat in tagged_patterns:
        matched = looks_german(t) if tag == "language" else bool(pat.search(t))
        if not matched:
            continue
        # A geographic (minor_geo) hit is VETOED when the title ALSO names a major
        # economy — the paper is about the major, so keep it downloadable — or a
        # US-style parenthesised ticker (a single-name note is about the company,
        # not the country it mentions). Non-geo reasons (fx_daily, language) are
        # unaffected by either veto. We `continue` rather than `return None` so
        # any remaining (non-guarded) pattern can still fire; if none does, the
        # loop falls through and the paper is kept.
        if tag in _MAJOR_GUARDED_REASONS and (has_major or has_ticker):
            continue
        return tag
    return None


# Reverse lookup: compiled-pattern.pattern string -> reason tag (for the public
# untagged signature). Built from the default specs so the untagged API preserves
# the right tags for the shipped patterns.
_SPEC_TAG_BY_REGEX: dict[str, str] = {rx: tag for tag, rx in _DEFAULT_TITLE_PATTERN_SPECS}


def _tag_for_pattern(pattern: re.Pattern) -> str:
    return _SPEC_TAG_BY_REGEX.get(pattern.pattern, "title")


# ---------------------------------------------------------------------------
# Reclassification over the EXISTING DB (marketdesk filter)
# ---------------------------------------------------------------------------

# Statuses this pass is allowed to move. Everything else (COMPLETE / DOWNLOADED /
# PARSED / UPLOADED / FAILED / vaulted / SKIPPED_UNSUPPORTED / SKIPPED_SEEN /
# SKIPPED_OLD) is left strictly untouched: we never re-exclude work already done
# or a paper already skipped for another reason.
_RECLASSIFY_DOWNLOADABLE = (Status.DISCOVERED.value, Status.BLOB_FOUND.value)
_RECLASSIFY_EXCLUDED = Status.SKIPPED_EXCLUDED.value

# The candidate statuses the allocator will actually pull from (kept in sync with
# allocator._CANDIDATE_STATUSES; imported lazily to avoid a hard dependency here).
_CANDIDATE_STATUSES = (Status.DISCOVERED.value, Status.BLOB_FOUND.value)

_REASONS = ("blog", "fx_daily", "minor_geo", "language", "institution")

#: Public alias — the reporting order used by ``marketdesk filter`` output.
REASONS = _REASONS


@dataclass
class ReclassifyResult:
    """Outcome of a ``marketdesk filter`` pass (dry-run or applied)."""

    dry_run: bool = False
    # newly excluded: reason tag -> count
    excluded_by_reason: dict[str, int] = field(default_factory=dict)
    restored: int = 0
    # samples per reason (only populated in dry-run): reason -> [titles]
    samples: dict[str, list[str]] = field(default_factory=dict)
    kept_candidates: int = 0
    distinct_published_days: int = 0

    @property
    def total_excluded(self) -> int:
        return sum(self.excluded_by_reason.values())

    @property
    def kept_per_day(self) -> float:
        if self.distinct_published_days <= 0:
            return 0.0
        return self.kept_candidates / self.distinct_published_days

    def summary(self) -> str:
        mode = "DRY-RUN (nothing written)" if self.dry_run else "APPLIED"
        per = " ".join(f"{r}={self.excluded_by_reason.get(r, 0)}" for r in _REASONS)
        return (
            f"filter {mode}: {per} total_excluded={self.total_excluded} "
            f"restored={self.restored} kept={self.kept_candidates} "
            f"kept/day={self.kept_per_day:.1f} "
            f"(over {self.distinct_published_days} published days)"
        )


def _matching_reason(
    row: sqlite3.Row,
    *,
    exclude_institutions: set[str],
    tagged_patterns: list[tuple[str, re.Pattern]],
) -> str | None:
    return classify_exclusion_tagged(
        row["institution"], row["title"],
        exclude_institutions=exclude_institutions,
        tagged_patterns=tagged_patterns,
    )


def reclassify(
    conn: sqlite3.Connection,
    *,
    exclude_institutions: set[str] | None = None,
    tagged_patterns: list[tuple[str, re.Pattern]] | None = None,
    dry_run: bool = False,
    sample_size: int = 8,
) -> ReclassifyResult:
    """Re-run the exclusion rules over EXISTING rows (re-runnable, idempotent).

    * A downloadable row (DISCOVERED / BLOB_FOUND) that NOW matches -> SKIPPED_EXCLUDED.
    * A SKIPPED_EXCLUDED row that NO LONGER matches -> back to DISCOVERED (restore
      when the exclude list shrinks).
    * Every other status is left untouched.

    Idempotent: a second run makes no further changes (a just-excluded row is no
    longer downloadable, and a still-matching excluded row is not restored). In
    ``dry_run`` nothing is written and up to ``sample_size`` example titles per
    reason are collected so the operator can spot false positives.
    """
    if exclude_institutions is None:
        exclude_institutions = set(DEFAULT_EXCLUDE_INSTITUTIONS)
    if tagged_patterns is None:
        tagged_patterns = default_tagged_patterns()

    res = ReclassifyResult(dry_run=dry_run)
    res.excluded_by_reason = {r: 0 for r in _REASONS}
    res.samples = {r: [] for r in _REASONS}

    # 1) downloadable rows that now match -> exclude
    q = ",".join("?" for _ in _RECLASSIFY_DOWNLOADABLE)
    down_rows = conn.execute(
        f"SELECT * FROM papers WHERE status IN ({q})", _RECLASSIFY_DOWNLOADABLE
    ).fetchall()
    newly_excluded: set[str] = set()
    for row in down_rows:
        reason = _matching_reason(
            row, exclude_institutions=exclude_institutions, tagged_patterns=tagged_patterns
        )
        if reason is None:
            continue
        res.excluded_by_reason[reason] = res.excluded_by_reason.get(reason, 0) + 1
        newly_excluded.add(row["blob_id"])
        if dry_run and len(res.samples.setdefault(reason, [])) < sample_size:
            res.samples[reason].append(row["title"] or "(untitled)")
        if not dry_run:
            db.set_status(conn, row["blob_id"], Status.SKIPPED_EXCLUDED)

    # 2) previously-excluded rows that no longer match -> restore to DISCOVERED
    excl_rows = conn.execute(
        "SELECT * FROM papers WHERE status=?", (_RECLASSIFY_EXCLUDED,)
    ).fetchall()
    restored_ids: set[str] = set()
    restored_days: set[str] = set()
    for row in excl_rows:
        reason = _matching_reason(
            row, exclude_institutions=exclude_institutions, tagged_patterns=tagged_patterns
        )
        if reason is not None:
            continue  # still excluded — leave it
        res.restored += 1
        restored_ids.add(row["blob_id"])
        d = (row["published_at"] or "")[:10]
        if d:
            restored_days.add(d)
        if not dry_run:
            db.set_status(conn, row["blob_id"], Status.DISCOVERED)

    # 3) resulting KEPT candidate count + kept-per-day over the POST-apply state.
    #    Post-apply candidate set = (current candidates NOT newly-excluded)
    #                               ∪ (restored rows).
    #    In dry-run we compute this set arithmetically (nothing is written yet);
    #    when applied we just re-query, since the writes above already produced it.
    cand_q = ",".join("?" for _ in _CANDIDATE_STATUSES)
    if dry_run:
        cand_rows = conn.execute(
            f"SELECT blob_id, substr(published_at,1,10) d FROM papers "
            f"WHERE status IN ({cand_q})",
            _CANDIDATE_STATUSES,
        ).fetchall()
        kept_days = {
            r["d"] for r in cand_rows if r["blob_id"] not in newly_excluded and r["d"]
        }
        kept_days |= restored_days
        res.kept_candidates = (
            len(cand_rows) - len(newly_excluded) + len(restored_ids)
        )
        res.distinct_published_days = len(kept_days)
    else:
        res.kept_candidates = int(
            conn.execute(
                f"SELECT COUNT(*) c FROM papers WHERE status IN ({cand_q})",
                _CANDIDATE_STATUSES,
            ).fetchone()["c"]
        )
        res.distinct_published_days = int(
            conn.execute(
                f"SELECT COUNT(DISTINCT substr(published_at,1,10)) c FROM papers "
                f"WHERE status IN ({cand_q}) AND published_at IS NOT NULL",
                _CANDIDATE_STATUSES,
            ).fetchone()["c"]
        )

    return res
