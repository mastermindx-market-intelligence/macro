"""What a theme-research mount renders, defined once (shared hook 2).

Sol ruling on carrier PR #7780 (issuecomment-5813801605, Option A): the
theme-research shell is shared, and a second vertical mounts by registering
rather than by copying a partial. Before this module the anchor id, the slice
list and the bilingual title/note were typed into
``templates/_theme_research_mount.html.j2`` AND into
``templates/state_of_themes.html.j2`` AND into the registration, three copies
with nothing covering their agreement.

Why this is a separate leaf module rather than more fields on
:class:`~engine.market_ontology.theme_research_registry.VerticalRegistration`:
the registry binds a vertical's composer and owner-bundle loader, so its
import closure is the whole company-intelligence stack (measured 2026-09-24:
55 repo files, including the frozen theme-graph store).
``scripts/build_theme_detail.py`` renders every basket page and
``scripts/build_state_of_themes.py`` renders the Theme Tracker; neither must
drag that in, and four curated CI jobs declare one of them and would have to
re-run on any change to the research stack. So the strings live here, where
the only imports of its own are the standard library, and the registry reads
them from this module. Its curated CI closure is 2 files, this one and the
crosswalk; importing it at RUNTIME also executes this package's ``__init__``
and the exposure map that pulls, which is cheap and free of the data stack but
is not nothing. One definition, three consumers.

Laws
----
* Closed and exact: :data:`MOUNTS` is keyed by exact anchor theme id. No
  wildcard, no prefix, no default, no environment variable. An unregistered
  anchor returns ``None`` and the page mounts nothing.
* No authority and no payload: these are labels. Nothing here ranks, gates,
  sizes, times or originates anything, and no figure, token, credential or
  URL beyond the mount's own declared asset paths passes through.
* :func:`registered_anchor_for_basket` reads exactly one repository file,
  ``config/theme_crosswalk.yml``, and can only ever narrow: a crosswalk row
  selects among mounts that already exist here and can never introduce one.
* Rendering-time context only. A mount context is nine strings; the served
  research payload arrives later over the entitled API, never from here.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

__all__ = [
    "MOUNTS",
    "MountFacts",
    "mount_context",
    "mount_context_for_basket",
    "registered_anchor_for_basket",
]

# The canonical theme-id grammar (``^[a-z0-9_]+$``) as a closed character set,
# so this leaf needs no regular-expression machinery.
_ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")
_ID_MAX_LENGTH = 64


def _is_canonical_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= _ID_MAX_LENGTH
        and set(value) <= _ID_CHARS
    )


def _require_nonempty_text(field: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"MountFacts.{field} must be non-empty text")


@dataclass(frozen=True)
class MountFacts:
    """One vertical's mount-time strings — the whole of what a page renders.

    ``slice_labels`` carries the bilingual name of every slice in
    ``slice_keys``. The shipped client still renders its slice chips from its
    OWN hard-coded label map, so today this is the registration's copy of the
    same strings and hook 4 is what binds the client to it; until then
    ``test_client_slice_labels_match_the_registration`` reconciles the two
    rather than leaving them to drift. Both halves of every pair are required
    — a mount that renders an English label where Chinese is owed is a drift
    the toggle cannot hide.
    """

    anchor_theme_id: str
    slice_keys: tuple[str, ...]
    schema_id: str
    evidence_schema_id: str
    slice_labels: Mapping[str, tuple[str, str]]
    title_en: str
    title_zh: str
    note_en: str
    note_zh: str

    def __post_init__(self) -> None:
        if not _is_canonical_id(self.anchor_theme_id):
            raise ValueError(
                "MountFacts.anchor_theme_id must match the canonical theme-id "
                "grammar (lowercase a-z, 0-9, underscore; 1-64 chars)"
            )
        if not isinstance(self.slice_keys, tuple) or not self.slice_keys:
            raise ValueError("MountFacts.slice_keys must be a non-empty tuple")
        for slice_key in self.slice_keys:
            if not _is_canonical_id(slice_key):
                raise ValueError(
                    "MountFacts.slice_keys entries must match the canonical id grammar"
                )
        if len(set(self.slice_keys)) != len(self.slice_keys):
            raise ValueError("MountFacts.slice_keys must not repeat a slice")
        if not isinstance(self.slice_labels, Mapping):
            raise TypeError("MountFacts.slice_labels must be a mapping")
        if set(self.slice_labels) != set(self.slice_keys):
            raise ValueError(
                "MountFacts.slice_labels must label exactly the declared slice_keys"
            )
        for slice_key, pair in self.slice_labels.items():
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError(
                    f"MountFacts.slice_labels[{slice_key!r}] must be an (en, zh) pair"
                )
            for half in pair:
                _require_nonempty_text(f"slice_labels[{slice_key!r}]", half)
        for field in ("schema_id", "evidence_schema_id",
                      "title_en", "title_zh", "note_en", "note_zh"):
            _require_nonempty_text(field, getattr(self, field))
        if self.schema_id == self.evidence_schema_id:
            raise ValueError("MountFacts.schema_id and evidence_schema_id must differ")


_SEMICONDUCTOR = MountFacts(
    anchor_theme_id="ai_semiconductors",
    slice_keys=("hbm_packaging", "sic_gan_specialty"),
    schema_id="semiconductor_theme_research.v1",
    evidence_schema_id="semiconductor_theme_research.evidence.v1",
    slice_labels=MappingProxyType({
        "hbm_packaging": ("HBM & advanced packaging", "HBM 与先进封装"),
        "sic_gan_specialty": ("SiC / GaN specialty devices", "SiC / GaN 特种器件"),
    }),
    # Bilingual copy pinned verbatim from the reviewed T10b mount.
    title_en="Semiconductor industry research",
    title_zh="半导体产业研究",
    note_en=(
        "Paid research context for members. Nothing here ranks, gates, sizes "
        "or times anything."
    ),
    note_zh="会员研究内容。此处内容不构成排序、准入、仓位或时机判断。",
)

_ENTRIES: tuple[MountFacts, ...] = (_SEMICONDUCTOR,)


def _assert_unique_anchors(entries: tuple[MountFacts, ...]) -> None:
    """Load-time closure: a mount is keyed by its own anchor, ONCE.

    The registry one layer up enforces the identical law explicitly. Here the
    keys come from a comprehension, which would silently keep whichever
    duplicate came last — so the two hooks would disagree about a vertical
    while both looked healthy. They now fail the same way, at import.
    """
    anchors = [entry.anchor_theme_id for entry in entries]
    for anchor in anchors:
        if anchors.count(anchor) != 1:
            raise RuntimeError(
                f"theme_research_mounts: anchor registered twice: {anchor!r}"
            )


_assert_unique_anchors(_ENTRIES)

#: Closed, read-only mapping ``anchor_theme_id -> MountFacts``.
MOUNTS: Mapping[str, MountFacts] = MappingProxyType(
    {entry.anchor_theme_id: entry for entry in _ENTRIES}
)


def mount_context(anchor_theme_id: object) -> Mapping[str, str] | None:
    """The exact strings the mount renders for ``anchor_theme_id``, or None.

    Nine keys, every value a non-empty string, so a template can render the
    mount without a single hard-pinned vertical name. ``slice_labels_json`` is
    one compact sorted JSON object carrying the bilingual slice copy. The
    shipped client does NOT read it yet — it keeps its own label map, and hook
    4 is what binds it — so today this attribute is what a second vertical's
    client binding will need, reconciled against the client's copy by a test.
    """
    import json  # noqa: PLC0415 — used only here

    facts = MOUNTS.get(anchor_theme_id) if isinstance(anchor_theme_id, str) else None
    if facts is None:
        return None
    labels = {key: list(facts.slice_labels[key]) for key in facts.slice_keys}
    return MappingProxyType({
        "anchor_theme_id": facts.anchor_theme_id,
        "slices": ",".join(facts.slice_keys),
        "schema_id": facts.schema_id,
        "evidence_schema_id": facts.evidence_schema_id,
        "slice_labels_json": json.dumps(
            labels, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ),
        "title_en": facts.title_en,
        "title_zh": facts.title_zh,
        "note_en": facts.note_en,
        "note_zh": facts.note_zh,
    })


_CROSSWALK_PATH = Path(__file__).resolve().parents[2] / "config" / "theme_crosswalk.yml"
_CROSSWALK_CACHE: dict[str, list[Mapping[str, Any]]] = {}
_CROSSWALK_WARNED = False


def _crosswalk_themes(crosswalk: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    """The crosswalk's ``themes`` rows, read ONCE from the pinned repo path.

    Repository configuration, deliberately not the builder's page payload: a
    generated page must not be able to claim a basket for a mount. An injected
    mapping is a test seam. An unreadable or malformed file yields no rows,
    which mounts nothing — never a guess.
    """
    if crosswalk is not None:
        rows = crosswalk.get("themes") if isinstance(crosswalk, Mapping) else None
        return [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []
    global _CROSSWALK_WARNED
    if "themes" not in _CROSSWALK_CACHE:
        try:
            import yaml  # noqa: PLC0415 — the builders already depend on it

            document = yaml.safe_load(_CROSSWALK_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError, ImportError) as exc:
            # A failed read is NOT cached. Caching emptiness here would mount
            # nothing for the rest of the process and survive the file coming
            # back, with no line anywhere saying why — the failure this repo
            # already paid for one file over (build_state_of_themes.py carries
            # a theme-crosswalk-unreadable annotation because a silently empty
            # map once shipped as a baffling "0 > 7"). Bare print, not a
            # logger: an annotation that does not START the line is dropped.
            if not _CROSSWALK_WARNED:
                _CROSSWALK_WARNED = True
                print(
                    f"::warning title=theme-crosswalk-unreadable::{_CROSSWALK_PATH} "
                    f"could not be read ({exc}); no page mounts theme research "
                    f"in this build",
                    flush=True,
                )
            return []
        rows = document.get("themes") if isinstance(document, Mapping) else None
        _CROSSWALK_CACHE["themes"] = (
            [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []
        )
    return _CROSSWALK_CACHE["themes"]


def registered_anchor_for_basket(
    basket_id: object, crosswalk: Mapping[str, Any] | None = None
) -> str | None:
    """The mounted anchor theme whose OWN basket page this is, or None.

    The claim must be primary. A theme's ``basket_ids`` records which baskets
    belong to the theme, which is membership, not identity: the live crosswalk
    has ``ai_semiconductors`` listing ``ai_infra`` among its baskets, and a
    section headed "Semiconductor industry research" does not belong on the
    AI-infrastructure page just because the two themes overlap. So only
    ``primary_basket_id`` mounts, and a theme with no primary basket mounts
    nowhere until its owner names one.

    ``None`` whenever the answer is not unambiguous: no theme names the basket
    as primary, more than one does, or the one that does has no mount here.
    Ambiguity mounts nothing — a missing basket is never solved by inventing a
    theme, a node or a crosswalk identity.
    """
    if not isinstance(basket_id, str) or not basket_id:
        return None
    # Claiming ROWS, not claiming ids: two rows sharing one theme id and both
    # naming this basket is a malformed crosswalk, and a malformed crosswalk
    # mounts nothing rather than resolving to whichever row won a set.
    claimants = [
        row["id"]
        for row in _crosswalk_themes(crosswalk)
        if isinstance(row.get("id"), str)
        and row["id"]
        and row.get("primary_basket_id") == basket_id
    ]
    if len(claimants) != 1:
        return None
    anchor_theme_id = claimants[0]
    return anchor_theme_id if anchor_theme_id in MOUNTS else None


def mount_context_for_basket(
    basket_id: object, crosswalk: Mapping[str, Any] | None = None
) -> Mapping[str, str] | None:
    """The mount context for a basket page, or ``None`` to mount nothing.

    The one call a page builder needs: it never names a vertical, never reads
    the crosswalk itself and never decides what a mount renders.
    """
    anchor_theme_id = registered_anchor_for_basket(basket_id, crosswalk)
    return None if anchor_theme_id is None else mount_context(anchor_theme_id)
