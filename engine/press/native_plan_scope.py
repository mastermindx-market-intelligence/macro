"""Prospective close-scope enforcement for native Prophet plan briefs.

Pure stdlib, side-effect free helpers for the brief press pipeline.  A native
plan brief is a brief slot bound to a simulated Prophet paper plan (never an
executed trade).  For those slots only, this module provides:

* ``is_native_plan_brief(slot)`` -- recognise the native plan binding.
* ``receipt_facts(slot)`` -- restrict receipt counting to the exact bound
  primary chronicle fact and its matching ``prophet_plan`` fact.
* ``scope_fragments(slot)`` -- the short mandatory visible field disclosures,
  validated from parent-supplied plan metadata (``ValueError`` when missing,
  malformed or inconsistent; ``[]`` for non-native slots).
* ``required_dossier(slot)`` -- the already-allowlisted canonical Mastermind
  dossier URL for the scoped asset, or ``None`` for non-native slots.  A
  missing dossier raises; the URL is never constructed or admitted.
* ``scope_problems(body_html, slot)`` -- deterministic fail-closed list of
  missing/invalid scope disclosure and continuation-link problems.

Deliberately out of scope here: thresholds, scoring, pool membership,
refill/ranking/date changes, identity changes, heuristic subject matching,
quantitative-clause credit and pre-dispatch evidence sufficiency (the parent
implements those with its own validators), generation/provider work, and any
general semantic guarantee about article quality.  Ordinary markup and link
allowlist validation stays independent: this module only requires the single
dossier continuation anchor and never relaxes anything.
"""

from __future__ import annotations

import datetime as _dt
import re
from html.parser import HTMLParser

__all__ = [
    "is_native_plan_brief",
    "receipt_facts",
    "scope_fragments",
    "scope_problems",
    "required_dossier",
    "canonical_dossier_url",
]

DESK_BRIEF = "brief"
CHRONICLE_PREFIX = "chronicle:"
PLAN_PREFIX = "prophet_plan:"
DOSSIER_SCHEME = "https://"
DOSSIER_HOST = "www.mastermind-x.com"

# Authority/entry tokens are lowercase underscore identifiers, bounded at 40.
_IDENTITY_RE = re.compile(r"[a-z0-9_]{1,40}")
# Strict calendar ISO dates: YYYY-MM-DD only (no compact or week forms).
_ISO_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_WS_RE = re.compile(r"\s+")

# Authority tiers whose required visible fragment is the literal disclosure
# ``display-only`` rather than ``plan authority <tier>``.
_DISPLAY_AUTHORITY_TIERS = frozenset(("display", "display_only"))

_SCOPE_FIELDS = (
    "source_ref",
    "asset",
    "recorded_at",
    "price_basis_date",
    "close_date",
    "authority_tier",
    "entry_status",
    "confirmed_date",
)

_MISSING = object()


# ---------------------------------------------------------------------------
# read-only slot accessors (attribute or mapping shapes; never mutate)
# ---------------------------------------------------------------------------

def _get(obj, name, default=None):
    """Attribute-or-key read that never raises and never mutates."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    try:
        return getattr(obj, name, default)
    except Exception:
        return default


def _as_name_list(value):
    """Flatten sources/tickers/links containers into plain strings."""
    if value is None or isinstance(value, (bytes, bytearray)):
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        value = [value]
    try:
        items = list(value)
    except TypeError:
        return []
    out = []
    for item in items:
        if isinstance(item, str):
            out.append(item)
            continue
        if isinstance(item, dict):
            getter = item.get
        else:
            getter = lambda key: _get(item, key)  # noqa: E731
        for key in ("ref", "url", "ticker", "symbol", "name"):
            found = getter(key)
            if isinstance(found, str) and found:
                out.append(found)
                break
    return out


def _source_strings(slot):
    return _as_name_list(_get(slot, "sources"))


def _allowed_link_strings(slot):
    return _as_name_list(_get(slot, "allowed_links"))


def _primary_ref(slot):
    """Exact primary source ref (``chronicle:<id>``) or None.  Never the
    producer *name*: a Prophet ledger name alone must not activate anything."""
    ref = _get(_get(slot, "primary_source"), "ref")
    return ref if isinstance(ref, str) and ref else None


def _plan_ref_for(primary_ref):
    if isinstance(primary_ref, str) and primary_ref.startswith(CHRONICLE_PREFIX):
        ident = primary_ref[len(CHRONICLE_PREFIX):]
        if ident and not _WS_RE.search(ident):
            return PLAN_PREFIX + ident
    return None


def _fact_ref(item):
    ref = item.get("ref") if isinstance(item, dict) else _get(item, "ref")
    return ref if isinstance(ref, str) else None


def _iter_facts(slot):
    facts = _get(slot, "facts")
    if facts is None or isinstance(facts, (str, bytes, bytearray, dict)):
        return []
    try:
        return list(facts)
    except TypeError:
        return []


def _scope_meta_present(slot):
    return _get(slot, "native_plan_scope", _MISSING) is not _MISSING


# ---------------------------------------------------------------------------
# recognition and receipt scoping
# ---------------------------------------------------------------------------

def is_native_plan_brief(slot):
    """True only for ``desk == 'brief'`` slots bound to a native Prophet plan.

    Two independent bindings qualify: a typed ``native_plan_scope`` attribute
    present on the slot (even ``None`` or malformed, so validation can fail
    closed), or a fact whose ref is exactly ``prophet_plan:<id>`` for the id
    of the slot's exact primary ``chronicle:<id>`` reference.  A Prophet
    ledger producer name alone, an unbound plan ref for another issuer, or
    any research/non-brief desk never activates native plan handling.
    """
    desk = _get(slot, "desk")
    if not isinstance(desk, str) or desk.strip().lower() != DESK_BRIEF:
        return False
    if _scope_meta_present(slot):
        return True
    plan_ref = _plan_ref_for(_primary_ref(slot))
    if plan_ref is None:
        return False
    for item in _iter_facts(slot):
        if _fact_ref(item) == plan_ref:
            return True
    return False


def receipt_facts(slot):
    """Facts eligible for receipt counting; the slot is never modified.

    Native plan briefs count only the exact primary ``chronicle:<id>`` fact
    and the matching ``prophet_plan:<id>`` fact, and only when that primary
    reference is one of the slot's declared sources; anything else (numeric
    collisions, other issuers, global context) is excluded.  If the primary
    reference is missing or not among the sources the call fails closed with
    no receipts at all.  Every other slot returns its fact list unchanged.
    """
    facts = _iter_facts(slot)
    if not is_native_plan_brief(slot):
        return list(facts)
    primary_ref = _primary_ref(slot)
    if not primary_ref or primary_ref not in _source_strings(slot):
        return []
    eligible = {primary_ref}
    plan_ref = _plan_ref_for(primary_ref)
    if plan_ref is not None:
        eligible.add(plan_ref)
    return [item for item in facts if _fact_ref(item) in eligible]


# ---------------------------------------------------------------------------
# scope metadata validation
# ---------------------------------------------------------------------------

def _scope_meta(slot):
    """The typed scope mapping, or ValueError when missing/malformed."""
    meta = _get(slot, "native_plan_scope", _MISSING)
    if meta is _MISSING or meta is None:
        raise ValueError("native plan scope metadata is missing on a native plan brief")
    if not isinstance(meta, dict):
        raise ValueError("native plan scope metadata must be a mapping, got %s" % (type(meta).__name__,))
    for field in _SCOPE_FIELDS:
        if field not in meta:
            raise ValueError("native plan scope metadata is missing field %r" % (field,))
    return meta


def _iso_date(value, field):
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str) and _ISO_DATE_RE.fullmatch(value):
        try:
            return _dt.date.fromisoformat(value)
        except ValueError:
            pass
    raise ValueError(
        "native plan scope field %r must be a calendar ISO date (YYYY-MM-DD), got %r" % (field, value)
    )


def _as_of_date(slot):
    value = _get(slot, "as_of", _MISSING)
    if value is _MISSING:
        value = _get(slot, "asOf", _MISSING)
    if value is _MISSING:
        raise ValueError("slot has no as_of date to bound the native plan close scope")
    return _iso_date(value, "as_of")


def _tickers(slot):
    return {
        entry.strip().upper()
        for entry in _as_name_list(_get(_get(slot, "story"), "tickers"))
        if isinstance(entry, str) and entry.strip()
    }


def _validated_asset(meta, slot):
    asset = meta["asset"]
    if (
        not isinstance(asset, str)
        or not asset
        or asset != asset.strip()
        or _WS_RE.search(asset)
    ):
        raise ValueError(
            "native plan scope asset must be a non-empty ticker without whitespace, got %r" % (asset,)
        )
    tickers = _tickers(slot)
    if asset.upper() not in tickers:
        raise ValueError(
            "native plan scope asset %r is not among the story tickers %s" % (asset, sorted(tickers))
        )
    return asset


def _validated_identity(meta, field):
    value = meta[field]
    if not isinstance(value, str) or not _IDENTITY_RE.fullmatch(value):
        raise ValueError(
            "native plan scope field %r must be a lowercase underscore token of at most"
            " 40 characters, got %r" % (field, value)
        )
    return value


def canonical_dossier_url(asset):
    """The canonical first-party dossier URL spelling for an asset."""
    return "%s%s/stocks/%s.html" % (DOSSIER_SCHEME, DOSSIER_HOST, asset)


def _bound_scope(slot):
    """Scope mapping bound to this slot: (meta, primary_ref, asset)."""
    meta = _scope_meta(slot)
    primary_ref = _primary_ref(slot)
    if _plan_ref_for(primary_ref) is None:
        raise ValueError(
            "native plan brief requires a nonempty chronicle:<id> primary source binding"
        )
    source_ref = meta["source_ref"]
    if source_ref != primary_ref:
        raise ValueError(
            "native plan scope source_ref %r does not match the slot primary source ref %r"
            % (source_ref, primary_ref)
        )
    if primary_ref not in _source_strings(slot):
        raise ValueError(
            "native plan scope source_ref %r is not among the slot sources" % (primary_ref,)
        )
    asset = _validated_asset(meta, slot)
    return meta, primary_ref, asset


# ---------------------------------------------------------------------------
# required fragments
# ---------------------------------------------------------------------------

def _signal_fragments(meta, confirmed):
    """Keep tier admission separate from the T1-only marker date.

    Older scopes have no tier/provisional metadata. Preserve that unknown
    rather than inferring a tier from a date, outcome or entry status.
    """
    tier = meta.get("signal_tier")
    provisional = meta.get("signal_provisional")
    if tier is not None and (not isinstance(tier, str) or tier not in {"T1", "T2", "T3"}):
        raise ValueError("native plan signal_tier must be T1, T2, T3 or null")
    if provisional is not None and type(provisional) is not bool:
        raise ValueError("native plan signal_provisional must be boolean or null")
    if ((tier == "T2" and provisional is True)
            or (tier == "T3" and provisional is False)):
        raise ValueError("native plan signal tier/provisional metadata conflict")
    if confirmed is not None and (tier in {"T2", "T3"} or provisional is True):
        raise ValueError("native plan T1 marker date conflicts with signal metadata")
    return [
        "signal tier " + tier if tier is not None else "signal tier not recorded",
        "signal provisional " + str(provisional).lower() if provisional is not None
        else "signal provisional status not recorded",
    ]


def scope_fragments(slot):
    """Short required visible scope disclosures; [] for non-native slots.

    Raises ValueError when the native scope metadata is missing, malformed or
    inconsistent with the slot (wrong source/asset, non-calendar dates, dates
    out of role order, bad authority/entry tokens).  Roles stay distinct even
    when date values coincide: recorded/price <= close <= as_of and confirmed
    <= close, with equality permitted.  No confirmation, status or clock value
    is ever invented here; fragments only restate validated metadata.
    """
    if not is_native_plan_brief(slot):
        return []
    meta, _primary_ref, _asset = _bound_scope(slot)
    recorded_at = _iso_date(meta["recorded_at"], "recorded_at")
    price_basis = _iso_date(meta["price_basis_date"], "price_basis_date")
    close = _iso_date(meta["close_date"], "close_date")
    as_of = _as_of_date(slot)
    authority = _validated_identity(meta, "authority_tier")
    entry_status = _validated_identity(meta, "entry_status")
    confirmed_raw = meta["confirmed_date"]
    confirmed = None if confirmed_raw is None else _iso_date(confirmed_raw, "confirmed_date")

    if recorded_at > close:
        raise ValueError(
            "native plan recorded_at %s is after close_date %s"
            % (recorded_at.isoformat(), close.isoformat())
        )
    if price_basis > close:
        raise ValueError(
            "native plan price_basis_date %s is after close_date %s"
            % (price_basis.isoformat(), close.isoformat())
        )
    if confirmed is not None and confirmed > close:
        raise ValueError(
            "native plan confirmed_date %s is after close_date %s"
            % (confirmed.isoformat(), close.isoformat())
        )
    if close > as_of:
        raise ValueError(
            "native plan close_date %s is after slot as_of %s"
            % (close.isoformat(), as_of.isoformat())
        )

    return [
        "simulated paper plan",
        "plan recorded " + recorded_at.isoformat(),
        "price basis " + price_basis.isoformat(),
        "display-only" if authority in _DISPLAY_AUTHORITY_TIERS else "plan authority " + authority,
        "entry status " + entry_status,
        *_signal_fragments(meta, confirmed),
        "T1 marker confirmation date not recorded" if confirmed is None
        else "T1 marker confirmation date " + confirmed.isoformat(),
        "simulated close " + close.isoformat(),
        "not an executed trade or investor return",
    ]


# ---------------------------------------------------------------------------
# canonical dossier (never constructed or admitted when absent)
# ---------------------------------------------------------------------------

def required_dossier(slot):
    """The allowlisted canonical dossier URL, or None for non-native slots.

    Returns the canonical ``https://www.mastermind-x.com/stocks/<asset>.html``
    value only when that exact string already exists in ``slot.allowed_links``.
    Otherwise raises ValueError: a missing dossier URL is never constructed,
    guessed or admitted.
    """
    if not is_native_plan_brief(slot):
        return None
    _meta, _primary_ref, asset = _bound_scope(slot)
    canonical = canonical_dossier_url(asset)
    for link in _allowed_link_strings(slot):
        if link == canonical:
            return canonical
    raise ValueError(
        "canonical dossier %s is not present in slot.allowed_links; refusing to construct"
        " or admit a missing URL" % (canonical,)
    )


# ---------------------------------------------------------------------------
# visible-text and anchor extraction (HTMLParser; fail closed)
# ---------------------------------------------------------------------------

class _VisibleTextParser(HTMLParser):
    """Collects visible text only: no comments, no script/style/hidden data."""

    _SKIP_TAGS = frozenset(("script", "style", "template"))

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self._open = []  # stack of (tag_lower, suppress_subtree)
        self._chunks = []

    @staticmethod
    def _suppresses(attrs):
        for name, value in attrs:
            lname = (name or "").lower()
            if lname == "hidden":
                return True
            if lname == "aria-hidden" and (value or "").strip().lower() == "true":
                return True
        return False

    def handle_starttag(self, tag, attrs):
        name = (tag or "").lower()
        self._open.append((name, name in self._SKIP_TAGS or self._suppresses(attrs)))

    def handle_startendtag(self, tag, attrs):
        pass  # void / self-closing elements carry no text content

    def handle_endtag(self, tag):
        name = (tag or "").lower()
        for index in range(len(self._open) - 1, -1, -1):
            if self._open[index][0] == name:
                del self._open[index:]
                return

    def handle_data(self, data):
        if not data:
            return
        for _tag, suppress in self._open:
            if suppress:
                return
        self._chunks.append(data)

    # comments, doctypes and processing instructions are never visible, so
    # handle_comment/handle_decl/unknown_decl/handle_pi stay unimplemented.

    def text(self):
        return "".join(self._chunks)


class _AnchorHrefsParser(_VisibleTextParser):
    """Credit closed dossier anchors only when they have visible label text.

    Known hidden subtrees, comments and escaped markup earn no continuation.
    The independent markup validator still owns allowed HTML/CSS.
    """

    def __init__(self):
        super().__init__()
        self.hrefs = []
        self._anchors = []

    @staticmethod
    def _suppresses(attrs):
        if _VisibleTextParser._suppresses(attrs):
            return True
        return any(
            (name or "").lower() == "style" and re.search(
                r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))\b",
                value or "", re.I)
            for name, value in attrs
        )

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        if (tag or "").lower() == "a":
            href = next((value.strip() for name, value in attrs
                         if (name or "").lower() == "href" and isinstance(value, str)), None)
            self._anchors.append((len(self._open) - 1, href, []))

    def handle_data(self, data):
        if not data or any(suppress for _tag, suppress in self._open):
            return
        for _depth, _href, chunks in self._anchors:
            chunks.append(data)

    def handle_endtag(self, tag):
        name = (tag or "").lower()
        index = next((i for i in range(len(self._open) - 1, -1, -1)
                      if self._open[i][0] == name), None)
        if index is not None:
            for depth, href, chunks in self._anchors:
                if depth == index and name == "a" and href and "".join(chunks).strip():
                    self.hrefs.append(href)
            self._anchors = [anchor for anchor in self._anchors if anchor[0] < index]
        super().handle_endtag(tag)


def _visible_text(body_html):
    if not isinstance(body_html, str):
        return ""  # fail closed: unreadable body credits no disclosure
    parser = _VisibleTextParser()
    try:
        parser.feed(body_html)
        parser.close()
    except Exception:
        return ""
    return parser.text()


def _anchor_hrefs(body_html):
    if not isinstance(body_html, str):
        return []
    parser = _AnchorHrefsParser()
    try:
        parser.feed(body_html)
        parser.close()
    except Exception:
        return []
    return parser.hrefs


def _normalize(text):
    return _WS_RE.sub(" ", text).strip().lower()


def _dossier_href_targets(dossier_url):
    """Exact href spellings that resolve to the canonical dossier URL."""
    marker = DOSSIER_HOST + "/"
    path = dossier_url.split(marker, 1)[1] if marker in dossier_url else dossier_url
    return frozenset((dossier_url, "/" + path))


def _anchor_targets_dossier(hrefs, dossier_url):
    targets = _dossier_href_targets(dossier_url)
    return any(href in targets for href in hrefs)


# ---------------------------------------------------------------------------
# rendered-body scope check
# ---------------------------------------------------------------------------

def scope_problems(body_html, slot):
    """Deterministic missing/invalid native plan scope reasons; [] if not native.

    Checks only the mandatory scope disclosures and the single continuation
    anchor to the already-allowlisted canonical dossier (absolute URL or its
    exact relative path).  Bare URL text, escaped anchor markup, href on a
    non-anchor tag, lookalike/other-issuer URLs and unallowlisted dossiers all
    fail.  Ordinary markup and link allowlist validation, quantitative-clause
    credit and evidence sufficiency stay with the parent's own validators;
    nothing here claims public availability, review acceptance, or any general
    semantic match.
    """
    if not is_native_plan_brief(slot):
        return []
    problems = []

    def note(message):
        if message not in problems:
            problems.append(message)

    fragments = None
    try:
        fragments = scope_fragments(slot)
    except ValueError as exc:
        note("invalid native plan scope: %s" % (exc,))

    dossier = None
    try:
        dossier = required_dossier(slot)
    except ValueError as exc:
        note("invalid native plan scope: %s" % (exc,))

    if fragments is not None:
        visible = _normalize(_visible_text(body_html))
        for fragment in fragments:
            if _normalize(fragment) not in visible:
                note("missing required native plan disclosure: %s" % (fragment,))

    if dossier is not None and not _anchor_targets_dossier(_anchor_hrefs(body_html), dossier):
        note("missing required native plan continuation link to %s" % (dossier,))
    return problems
