"""research_vault.sidecar — parse + normalize a sidecar to the v1 contract.

Implements the ``research_vault.sidecar.v1`` contract (masterplan §5). The
ingester is DEFENSIVE: every field except the PDF itself has a fallback, and a
sidecar that fails JSON parse is still ingested with all-fallback metadata and
flagged ``needs_metadata=True`` — a document is NEVER dropped.

Pure + stdlib-only → unit-testable in isolation. No I/O here; callers pass in the
already-loaded sidecar bytes/dict plus the fallbacks they were able to recover
(PDF-embedded title, R2 upload time, source filename).
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

SCHEMA = "research_vault.sidecar.v1"

# side ∈ buy | sell | independent; default sell (§5).
_SIDES = {"buy", "sell", "independent"}
_DEFAULT_SIDE = "sell"

_UNKNOWN_INSTITUTION = "Unknown"

# summary bullets: 3–8 short bullets is the contract; we clamp to a sane ceiling
# but never fabricate — an empty/short list stays as-is (row shows "Summary pending").
_MAX_SUMMARY_POINTS = 8


# ---------------------------------------------------------------------------
# slug / id derivation
# ---------------------------------------------------------------------------

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slug(text: str, max_len: int = 60) -> str:
    """Lowercase ASCII slug: strip accents, collapse non-alnum runs to '-'.

    Empty / all-punctuation input → ''. Never raises.
    """
    if not text:
        return ""
    # Fold accents to ASCII (é -> e) so slugs are stable + url-safe.
    norm = unicodedata.normalize("NFKD", str(text))
    norm = norm.encode("ascii", "ignore").decode("ascii")
    s = _SLUG_STRIP.sub("-", norm.lower()).strip("-")
    if max_len and len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s


def date_part(published_at: str) -> str:
    """YYYY-MM-DD prefix of an ISO-8601 timestamp; '' when unparseable.

    Public because ``ingest._refresh_sidecars`` compares dates the same way. A
    bare ``[:10]`` slice is NOT equivalent: a non-ISO ``"07/28/2026"`` slices to
    something that sorts below any ``"2026-…"`` cutoff, silently excluding the row
    from every future refresh. The anchored regex returns '' instead, which the
    caller treats as "no usable date" — in scope, not aged out.
    """
    if not published_at:
        return ""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(published_at))
    return m.group(1) if m else ""


def derive_id(institution: str, published_at: str, title: str) -> str:
    """Derive a stable id ``slug(inst)-YYYY-MM-DD-slug(title)[:40]`` (§5).

    Missing parts degrade gracefully: an absent institution → 'unknown', an
    unparseable date → 'undated', an empty title → 'untitled'. Always returns a
    non-empty, url-safe id.
    """
    inst = slug(institution) or "unknown"
    date = date_part(published_at) or "undated"
    ttl = slug(title, max_len=40) or "untitled"
    return f"{inst}-{date}-{ttl}"


# ---------------------------------------------------------------------------
# field coercion helpers
# ---------------------------------------------------------------------------

def _as_str(v: Any) -> str:
    return v.strip() if isinstance(v, str) else ""


def _as_str_list(v: Any) -> list[str]:
    """Coerce to a list of non-empty trimmed strings (drop non-str members)."""
    if not isinstance(v, list):
        return []
    out: list[str] = []
    for item in v:
        s = item.strip() if isinstance(item, str) else ""
        if s:
            out.append(s)
    return out


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"true", "1", "yes"}
    return bool(v) if isinstance(v, (int, float)) else False


def _as_int(v: Any) -> int | None:
    if isinstance(v, bool):  # bool is an int subclass — reject explicitly
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str) and v.strip().isdigit():
        return int(v.strip())
    return None


# ---------------------------------------------------------------------------
# parse + normalize
# ---------------------------------------------------------------------------

def parse_json(raw: bytes | str | None) -> tuple[dict, bool]:
    """Load sidecar JSON. Returns ``(dict, bad_json)``.

    ``bad_json`` is True when the bytes were present but did not parse to a dict
    (→ the caller flags needs_metadata + uses all fallbacks). Absent sidecar
    (raw is None/empty) → ``({}, False)`` (not an error — just no metadata yet).
    """
    if raw is None:
        return {}, False
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = bytes(raw).decode("utf-8")
        except Exception:  # noqa: BLE001 — undecodable bytes == bad json
            return {}, True
    if not str(raw).strip():
        return {}, False
    try:
        obj = json.loads(raw)
    except Exception:  # noqa: BLE001 — malformed JSON: fall back, never drop
        return {}, True
    if not isinstance(obj, dict):
        return {}, True
    return obj, False


def _looks_truncated(title: str) -> bool:
    """True when a title has more '(' than ')' — the fingerprint of MarketDesk
    dropping a Reuters ".EX)" exchange suffix (e.g. "Alcon Inc. (ALCC")."""
    return title.count("(") > title.count(")")


# A trailing "(1)"/"(2)" is the desk's SAVE-AS dedupe marker, not part of the
# report's name — it arrives when the same filename is downloaded twice
# ("Carrefour (CARR(1).pdf"). Capped at 2 digits so a real year parenthetical
# ("Outlook (2027)") can never be mistaken for one.
_DEDUPE_SUFFIX = re.compile(r"\s*\(\d{1,2}\)\s*$")


def clean_title(title: str) -> str:
    """Repair a title for PUBLIC display: drop the ``(N)`` dedupe marker and
    balance stray parentheses. Pure, idempotent, never raises.

    MarketDesk truncates its own Reuters ticker parenthetical at the ``.``, so
    ``"Alcon Inc. (ALCC.SW)"`` arrives as ``"Alcon Inc. (ALCC"`` — an unbalanced
    "(" that otherwise ships straight into a public ``<title>``/``og:title``.
    We CLOSE the dangling fragment rather than delete it: the ticker root is real
    and is exactly what an exact-title search matches on, while the exchange
    suffix is unknowable here and must never be invented. Closing also leaves the
    published URL slug byte-identical (the slug strips non-alphanumerics), so a
    repaired title never orphans an already-indexed ``/research/`` page.

    A fragment with NO content ("Foo (") is dropped instead, and unmatched ")"
    are stripped. :func:`normalize`'s PDF-``/Title`` recovery is still preferred
    where it fires — it restores the FULL name; this is the last-resort repair
    for the documents where it cannot.

    This function is the SLUG input. Repeat-collapse and trailing-date trim live
    in :func:`display_title` and must never run here — they delete words, which
    would move already-indexed ``/research/<slug>.html`` URLs.
    """
    s = re.sub(r"\s+", " ", str(title or "")).strip()
    prev = None
    while prev != s:                       # "…(1)(2)": strip every trailing marker
        prev = s
        s = _DEDUPE_SUFFIX.sub("", s).strip()
    if not s:
        return ""

    out: list[str] = []
    opens: list[int] = []                  # indices in `out` of still-unclosed "("
    for ch in s:
        if ch == "(":
            opens.append(len(out))
            out.append(ch)
        elif ch == ")":
            if not opens:
                continue                   # unmatched ")" — drop it
            opens.pop()
            out.append(ch)
        else:
            out.append(ch)
    # Innermost-first so an outer "(" sees the closer we just added as content.
    for i in reversed(opens):
        if "".join(out[i + 1:]).strip():
            out.append(")")
        else:
            del out[i:]                    # bare trailing "(" — nothing to close
    return re.sub(r"\s+", " ", "".join(out)).strip()


# Trailing calendar dates the auto-titler appends after a real headline
# ("GS Vol Views 9 Sep 2026"). Month+day without a year ("July 24") and
# month+year without a day ("july 2026") are left alone — those are real titles.
_TRAILING_DAY_MON_YEAR = re.compile(
    r"\s+\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\s*$",
    re.I,
)
_TRAILING_MON_DAY_YEAR = re.compile(
    r"\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\s*$",
    re.I,
)

# Markdown emphasis the upstream summarizer wraps around bullet headings.
# The producer lives outside this repo (MarketDesk); we clean at ingest.
# Italic follows markdown flanking: opener not followed by space, closer not
# preceded by space, neither delimiter intra-word. Lone/footnote/multiplication
# asterisks (EBITDA*, 3*ATR) must survive.
_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC = re.compile(r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])")
# Mid-clause split marker the producer actually emits. Sentence-final
# abbreviations (U.S., etc., Inc.) are NOT continuations.
_VS_END = re.compile(r"\bvs\.?$", re.I)

# side is DESK TYPE (buy-side / sell-side / independent), never a rating.
_DESK_TYPE = {
    "buy": ("Buy-side", "买方", "buy-side"),
    "sell": ("Sell-side", "卖方", "sell-side"),
    "independent": ("Independent", "独立", "indep"),
}

# Preferred spellings for the Institution facet. Keys are casefolded.
_INSTITUTION_CANON = {
    "blackrock": "BlackRock",
    "scotiabank": "Scotiabank",
    "commbank": "CommBank",
    "commonwealth bank": "CommBank",
    "ing": "ING",
    "ing econ": "ING",
    "ing direct": "ING",
    "sg prime": "Société Générale",
}

# Filesystem / document-type labels that are not research desks. Kept on the
# row (we do not invent a bank name) but excluded from the Institution facet
# and replaced on cards by :func:`institution_display`.
_NON_INSTITUTION = {
    "new folder", "s&t", "other", "prime", "pb",
    "week ahead", "weekly preview", "13f summary", "greed and fear",
    "nuclear", "zh ai",
}

_GENERIC_DESK_EN = "Institutional desk"
_GENERIC_DESK_ZH = "机构研究台"


def desk_type(side: str) -> tuple[str, str, str]:
    """``(en_label, zh_label, css_class)`` for a sidecar ``side`` value.

    ``side`` is buy-side / sell-side / independent desk type, never a
    BUY/SELL rating. Unknown values degrade to Independent. Never raises.
    """
    return _DESK_TYPE.get((side or "").strip().lower(), _DESK_TYPE["independent"])


def desk_stamp_classes(side: str) -> str:
    """CSS classes for the desk-type stamp, new name first then origin/main.

    ``buy-side buy`` / ``sell-side sell`` / ``indep`` so new JS matches the
    still-baked ``.stamp.buy/.sell/.indep`` selectors until the render lane
    rebakes, and new CSS matches a cached old JS class after the bake.
    """
    _, _, cls = desk_type(side)
    if cls == "buy-side":
        return "buy-side buy"
    if cls == "sell-side":
        return "sell-side sell"
    return "indep"


def canon_institution(name: str) -> str:
    """Collapse known spelling variants; unknown names pass through unchanged."""
    s = (name or "").strip()
    if not s:
        return s
    return _INSTITUTION_CANON.get(s.casefold(), s)


def institution_is_desk(name: str) -> bool:
    """False for blank, Unknown, and non-institution folder/doc-type labels."""
    s = (name or "").strip()
    if not s or s == _UNKNOWN_INSTITUTION:
        return False
    return s.casefold() not in _NON_INSTITUTION


def institution_display_pair(name: str) -> tuple[str, str]:
    """``(en, zh)`` card/report institution label. Folder names are not printed."""
    s = canon_institution((name or "").strip())
    if not s:
        return (_UNKNOWN_INSTITUTION, "未知")
    if s == _UNKNOWN_INSTITUTION:
        return (s, "未知")
    if not institution_is_desk(s):
        return (_GENERIC_DESK_EN, _GENERIC_DESK_ZH)
    return (s, s)


def institution_display(name: str) -> str:
    """English institution label for a card or report page."""
    return institution_display_pair(name)[0]


def _collapse_repeated_lead(s: str) -> str:
    """'GS Vol Views GS Vol Views …' → 'GS Vol Views …'. Requires a 2+ word repeat."""
    words = s.split()
    n = len(words)
    for k in range(n // 2, 1, -1):
        if words[:k] == words[k:2 * k]:
            return " ".join(words[:k] + words[2 * k:])
    return s


def _strip_trailing_calendar_date(s: str) -> str:
    stripped = _TRAILING_DAY_MON_YEAR.sub("", s)
    stripped = _TRAILING_MON_DAY_YEAR.sub("", stripped).strip()
    if stripped and stripped != s and len(stripped.split()) >= 2:
        return stripped
    return s


def _finish_title(s: str) -> str:
    """Display-only title polish after paren/dedupe repair. Idempotent."""
    if not s:
        return s
    s = _collapse_repeated_lead(s)
    return _strip_trailing_calendar_date(s)


def display_title(title: str) -> str:
    """Title for cards, SSR, report pages, facets. Never a slug input.

    Runs :func:`clean_title` (paren/dedupe, slug-stable) then the repeat-lead
    collapse and trailing-calendar-date strip. Idempotent, never raises.
    """
    try:
        s = clean_title(title)
    except Exception:  # noqa: BLE001 — a title is never worth failing a render
        s = re.sub(r"\s+", " ", str(title or "")).strip()
    return _finish_title(s) if s else s


def _strip_markdown_markup(text: str) -> str:
    s = str(text or "")
    s = _MD_BOLD.sub(r"\1", s)
    s = _MD_ITALIC.sub(r"\1", s)
    s = s.replace("**", "").replace("__", "")
    return re.sub(r"\s+", " ", s).strip()


def _incomplete_point(s: str) -> bool:
    """True when ``s`` was cut mid-clause — ``vs.`` or an unbalanced open paren.

    Sentence-final abbreviations (U.S., etc., Inc.) are complete bullets.
    A trailing comma or missing period is not a split. The producer defect
    this repairs is a cut on ``(vs.`` / ``vs.`` or an open ``(``.
    """
    t = (s or "").rstrip()
    if not t:
        return False
    if t.count("(") > t.count(")"):
        return True
    return bool(_VS_END.search(t))


def _continuation_point(s: str) -> bool:
    t = (s or "").lstrip()
    if not t:
        return False
    return t[0].islower() or t[0].isdigit() or t[0] in ")]}"


def _join_points(a: str, b: str) -> str:
    if a.endswith("(") or b[:1] in ")]},;.":
        joiner = "" if b[:1] in ")]}" else " "
    else:
        joiner = " "
    return re.sub(r"\s+", " ", a + joiner + b).strip()


def clean_summary_points(points: list[str] | None) -> list[str]:
    """Strip paired markdown emphasis and rejoin bullets split on ``vs.``.

    The upstream summarizer (out of this repo) emits ``**Heading**: …`` and
    splits on ``vs.``. Rejoin only that mid-clause cut (or an unbalanced open
    paren). Complete bullets, including ones that end in U.S./etc./Inc., stay
    separate. Idempotent, never raises, clamps to ``_MAX_SUMMARY_POINTS``.
    """
    try:
        raw = [_strip_markdown_markup(p) for p in (points or [])]
        raw = [p for p in raw if p]
        out: list[str] = []
        i = 0
        while i < len(raw):
            cur = raw[i]
            while i + 1 < len(raw) and _incomplete_point(cur) and _continuation_point(raw[i + 1]):
                cur = _join_points(cur, raw[i + 1])
                i += 1
            out.append(cur)
            i += 1
        return out[:_MAX_SUMMARY_POINTS]
    except Exception:  # noqa: BLE001 — a summary is never worth failing an ingest
        return [str(p).strip() for p in (points or []) if str(p).strip()][:_MAX_SUMMARY_POINTS]


def normalize(
    sidecar: dict | None,
    *,
    bad_json: bool = False,
    fallback_title_pdf: str = "",
    fallback_title_filename: str = "",
    fallback_institution: str = "",
    fallback_published_at: str = "",
    fallback_source_filename: str = "",
) -> dict:
    """Normalize a (possibly empty/partial) sidecar dict to the v1 item shape.

    Fallback ladders (§5):
      - title: sidecar.title → PDF-embedded title → filename → 'Untitled research',
        then :func:`clean_title` (dedupe marker + unbalanced parens).
      - institution: sidecar.institution → caller fallback → 'Unknown' (+needs_metadata).
      - published_at: sidecar.published_at → caller fallback → '' (no crash). The
        research-vault ingest caller deliberately passes NO fallback: a missing
        MarketDesk publish date stays blank (and sorts LAST) rather than being
        stamped with our ingest clock, so a stale backfill never appears as new.
      - summary_points: sidecar list → [] ("Summary pending").
      - side: sidecar.side (validated) → 'sell'.
      - id: sidecar.id → derived slug id.

    ``needs_metadata`` is set when JSON was bad OR the institution had to fall
    back to 'Unknown' OR the title had to fall back to the filename/placeholder.
    Unknown sidecar fields are ignored (not preserved on the public item).
    Never raises.
    """
    sc = sidecar if isinstance(sidecar, dict) else {}
    needs_metadata = bool(bad_json)

    # --- title ladder ------------------------------------------------------
    title = _as_str(sc.get("title"))
    # Recover a MarketDesk-truncated title from the PDF's embedded /Title. MarketDesk
    # drops the Reuters ".EX)" exchange suffix off its own name, so "Alcon Inc. (ALCC.US)"
    # arrives as "Alcon Inc. (ALCC" (the tell is an unbalanced "("). When that happens and
    # the PDF carries a fuller, balanced /Title, prefer it — never regressing a good title.
    if title and _looks_truncated(title):
        pdf_title = _as_str(fallback_title_pdf)
        if pdf_title and not _looks_truncated(pdf_title) and len(pdf_title) >= len(title):
            title = pdf_title
    if not title:
        title = _as_str(fallback_title_pdf)
        if title:
            needs_metadata = True
    if not title:
        title = _as_str(fallback_title_filename)
        if title:
            needs_metadata = True
    if not title:
        title = "Untitled research"
        needs_metadata = True
    # Public-surface repair, LAST: the /Title recovery above needs to see the raw
    # truncation tell, so the dedupe marker + paren balance are fixed only once
    # the ladder has settled on a title.
    title = clean_title(title)
    if not title:
        title = "Untitled research"
        needs_metadata = True

    # --- institution facet -------------------------------------------------
    institution = _as_str(sc.get("institution"))
    if not institution:
        institution = _as_str(fallback_institution)
    if not institution:
        institution = _UNKNOWN_INSTITUTION
        needs_metadata = True
    institution = canon_institution(institution) or institution

    # --- side --------------------------------------------------------------
    side = _as_str(sc.get("side")).lower()
    if side not in _SIDES:
        side = _DEFAULT_SIDE

    # --- published_at ------------------------------------------------------
    published_at = _as_str(sc.get("published_at")) or _as_str(fallback_published_at)

    # --- summary / tags / tickers -----------------------------------------
    summary_points = clean_summary_points(_as_str_list(sc.get("summary_points")))
    tags = _as_str_list(sc.get("tags"))
    tickers = [t.upper() for t in _as_str_list(sc.get("tickers"))]

    # --- misc optional -----------------------------------------------------
    desk = _as_str(sc.get("desk"))
    pages = _as_int(sc.get("pages"))
    language = _as_str(sc.get("language")) or "en"
    source_filename = _as_str(sc.get("source_filename")) or _as_str(fallback_source_filename)
    top_pick = _as_bool(sc.get("top_pick"))

    # --- id ----------------------------------------------------------------
    item_id = slug(_as_str(sc.get("id")), max_len=120)
    if not item_id:
        item_id = derive_id(institution, published_at, title)

    return {
        "id": item_id,
        "title": title,
        "institution": institution,
        "side": side,
        "desk": desk,
        "published_at": published_at,
        "summary_points": summary_points,
        "tags": tags,
        "tickers": tickers,
        "top_pick": top_pick,
        "pages": pages,
        "language": language,
        "source_filename": source_filename,
        "needs_metadata": needs_metadata,
    }


def from_bytes(
    raw: bytes | str | None,
    **fallbacks: str,
) -> dict:
    """Convenience: parse raw sidecar bytes then normalize with fallbacks.

    Accepts the same ``fallback_*`` kwargs as :func:`normalize`. Never raises;
    bad JSON → all-fallback item flagged ``needs_metadata=True``.
    """
    sc, bad_json = parse_json(raw)
    return normalize(sc, bad_json=bad_json, **fallbacks)
