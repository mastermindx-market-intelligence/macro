"""Source-family rights for the theme graph (W3A §4, review amendment §9.4).

THE SINGLE AUTHORITY IS THE REGISTRY. ``config/theme_sources.yml`` says what may be
emitted from each source family, and nothing else does. The per-row licensing booleans
on an evidence row are MINT-TIME SNAPSHOTS with zero enforcement power: the evidence
store is append-only, so a row minted while a family was ``derived_display_ok`` keeps
saying so forever, and a rights decision that moved after the fact can never reach it.
Enforcement therefore reads the registry at call time — :func:`rights_class` — and the
guard only emits a designed ::notice when a stored snapshot disagrees with the
family's current class,
because history is a record, not a mistake to be edited.

Two directions matter and they are not symmetric:

* an UNKNOWN family fails CLOSED — :func:`rights_class` raises, and the guard treats a
  stored node whose ``rights_family`` has no registry row as a breach. A family nobody
  wrote down is a family nobody reviewed.
* an unresolved-but-registered family is simply refused at the emission gate. That is
  the steady state for both vendor families in W3A, and it is a decision pending, not
  an error.

LABEL vs STRUCTURE (F19). A vendor's own subtheme NAME is already-public vocabulary and
rides ``name_en``/``name_zh`` lawfully; what rights govern is the subtheme→member
STRUCTURE as a dataset. Reading a class as "the words are forbidden" over-reads it; the
gate is about emitting the mapping, not about naming the concept.
"""
from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

REGISTRY_FILE = "config/theme_sources.yml"

#: The four classes a family may carry. Emission is permitted for exactly two of them.
RIGHTS_CLASSES: frozenset[str] = frozenset(
    {"internal_only", "derived_display_ok", "direct_display_ok", "unresolved"})

#: Classes that permit a GMI public emission. ``unresolved`` is NOT one of them:
#: "we have not decided" refuses, it does not default open.
EMISSION_OK: frozenset[str] = frozenset({"derived_display_ok", "direct_display_ok"})

#: Node-id prefix → source family. The local-theme plane's id grammar carries the
#: family in the id itself, so this table is a restatement of the grammar rather than a
#: second opinion about it.
NODE_PREFIX_FAMILY: tuple[tuple[str, str], ...] = (
    ("ltheme:finviz:", "finviz_themes"),
    ("ltheme:ths:", "ths_concepts"),
    ("basket:baskets_china_ths:", "ths_concepts"),
    ("basket:baskets:", "mastermind_curated"),
    ("basket:baskets_china:", "mastermind_curated"),
    ("basket:baskets_hk:", "mastermind_curated"),
    ("basket:baskets_canada:", "mastermind_curated"),
    ("basket:baskets_intl:", "mastermind_curated"),
)

#: Evidence ``source_ref`` prefix → source family, for the guard's snapshot-vs-current
#: comparison. Deliberately a prefix table and not a parse of the registry's
#: ``source_route`` prose: a warning derived from prose would drift silently the first
#: time somebody rewords a note.
SOURCE_PREFIX_FAMILY: tuple[tuple[str, str], ...] = (
    ("finviz_themes/", "finviz_themes"),
    ("data/themes_heatmap/", "finviz_themes"),
    ("data/baskets_china_ths/", "ths_concepts"),
    ("data/baskets/", "mastermind_curated"),
    ("data/baskets_china/", "mastermind_curated"),
    ("data/baskets_hk/", "mastermind_curated"),
    ("data/baskets_canada/", "mastermind_curated"),
    ("data/baskets_intl/", "mastermind_curated"),
    ("config/theme_crosswalk.yml", "mastermind_curated"),
    # --- https origins ------------------------------------------------------
    # Sol #7780 issuecomment-5825621672 item 5 (sec_edgar) and item 6 (the
    # eleven publishers), applied ONCE here by the shared rights owner rather
    # than by each vertical — 5825811888 item 5.
    #
    # RECOGNITION IS NOT PERMISSION. Every row below except sec_edgar carries
    # ``rights_class: unresolved`` in the registry, which REFUSES emission.
    # What these prefixes change is the REASON a source is refused: from
    # unmapped (refused through ignorance, which the emission path must do but
    # should not have to) to a named family with inspected terms attached. The
    # served result is unchanged: still nothing from these eleven publishers.
    ("https://www.sec.gov/Archives/", "sec_edgar"),
    ("https://www2.jpx.co.jp/disc/", "jpx_tdnet_issuer_disclosure"),
    ("https://www1.hkexnews.hk/listedco/", "hkexnews_issuer_disclosure"),
    ("https://www.orbbec.com/case-studies/", "orbbec_vendor_case_study"),
    ("https://discover.parker.com/K-Series", "parker_vendor_catalogue"),
    ("https://www.robotis.com/en/product/", "robotis_vendor_catalogue"),
    ("https://www.1x.tech/discover/", "onex_vendor_product_page"),
    (
        "https://robotics.hexagon.com/hexagon-robotics-and-schaeffler-deploy-"
        "a-fleet-of-aeon-humanoids/",
        "hexagon_robotics_press",
    ),
    ("https://www.zebra.com/us/en/about-zebra/newsroom/press-releases/", "zebra_press"),
    ("https://www.ptc.com/en/news/", "ptc_press"),
    ("https://investors.teradyne.com/sec-filings/", "teradyne_ir_sec_wrapper"),
    (
        "https://group.stabilus.com/news-and-events/press-releases/",
        "stabilus_press",
    ),
)


class RightsRefusal(RuntimeError):
    """A public emission was attempted from a family that does not permit one."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def registry_path() -> Path:
    return _repo_root() / REGISTRY_FILE


def _families_of(doc: dict) -> dict[str, dict]:
    """Normalize a parsed registry document to ``{family: row}`` — the one shape both
    read disciplines hand back. The shared pure parse step behind the cached
    :func:`_load` and the fresh :func:`load_registry_snapshot`, so the two can never
    normalize the same file differently."""
    out: dict[str, dict] = {}
    for name, row in (doc.get("families") or {}).items():
        if isinstance(row, dict):
            out[str(name)] = row
    return out


@lru_cache(maxsize=8)
def _load(path: str) -> dict[str, dict]:
    p = Path(path)
    if not p.exists():
        # Fail-closed by emptiness: with no registry, every family is unknown and
        # rights_class raises. A missing registry must never read as "all clear".
        log.warning("theme_graph.rights: %s missing — every family is unknown and every "
                    "emission gate will refuse", p)
        return {}
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return _families_of(doc)


def load_registry(path: str | Path | None = None) -> dict[str, dict]:
    """The rights registry as {family: row}. Cached per path."""
    return _load(str(Path(path) if path is not None else registry_path()))


def known_families(path: str | Path | None = None) -> frozenset[str]:
    return frozenset(load_registry(path))


def load_registry_snapshot(path: str | Path | None = None) -> tuple[str, dict[str, dict]]:
    """Re-read the registry bytes FRESH and return ``(revision, families)``.

    The cached :func:`load_registry` answers "what did this process last see"; this
    answers "what does the file say right now", so a rights decision that moves after
    an evidence row was minted can reach an emission gate without a process restart
    (T03). ``revision`` stamps the sha256 of the bytes actually read, so a caller can
    tell two reads apart without diffing families. Fail-closed both ways: a missing
    registry raises ``registry_missing`` and an unparseable one raises
    ``registry_corrupt`` — an unreadable registry never reads as a default all-clear.
    """
    p = Path(path) if path is not None else registry_path()
    if not p.exists():
        raise RightsRefusal(
            f"registry_missing: {p} does not exist — a missing registry refuses rather "
            f"than reading as all-clear")
    try:
        data = p.read_bytes()
    except OSError as exc:
        raise RightsRefusal(f"registry_corrupt: {p} could not be read ({exc})") from exc
    revision = "rights_" + hashlib.sha256(data).hexdigest()[:32]
    try:
        doc = yaml.safe_load(data.decode("utf-8")) or {}
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise RightsRefusal(
            f"registry_corrupt: {p} is not parseable YAML ({exc})") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("families"), dict):
        raise RightsRefusal(
            f"registry_corrupt: {p} carries no top-level `families` mapping — an "
            f"unreadable registry refuses rather than defaults")
    return (revision, _families_of(doc))


def rights_class(family: str, *, path: str | Path | None = None) -> str:
    """The family's CURRENT rights class. Unknown family or unknown class → refuse.

    Fail-closed on both axes: a family with no row is not "probably fine", and a row
    carrying a class outside the enum is a typo that must not silently read as a
    permission.
    """
    row = load_registry(path).get(str(family or "").strip())
    if row is None:
        raise RightsRefusal(
            f"source family {family!r} has no row in {REGISTRY_FILE} — rights are STATED, "
            f"never assumed; add a reviewed row before emitting anything from it")
    cls = str(row.get("rights_class", "")).strip()
    if cls not in RIGHTS_CLASSES:
        raise RightsRefusal(
            f"source family {family!r} carries rights_class {cls!r}, outside "
            f"{sorted(RIGHTS_CLASSES)} — an unreadable class refuses rather than defaults")
    return cls


def auth_class(family: str, *, path: str | Path | None = None) -> str | None:
    row = load_registry(path).get(str(family or "").strip()) or {}
    v = str(row.get("auth_class", "")).strip()
    return v or None


def emission_allowed(family: str, *, path: str | Path | None = None) -> bool:
    """True when this family's material may be emitted publicly. Never raises for a
    known family — use it where a caller wants to branch rather than fail."""
    try:
        return rights_class(family, path=path) in EMISSION_OK
    except RightsRefusal:
        return False


def assert_public_emission_allowed(family: str, *,
                                   path: str | Path | None = None) -> None:
    """Raise :class:`RightsRefusal` unless ``family`` permits a public emission.

    The gate every GMI surface calls before putting source-derived structure in front of
    a user. ``unresolved`` and ``internal_only`` both refuse; the difference between them
    is what a program report says next, not what the caller may do.
    """
    cls = rights_class(family, path=path)
    if cls not in EMISSION_OK:
        raise RightsRefusal(
            f"public emission refused for source family {family!r}: rights_class={cls!r} "
            f"(permitted: {sorted(EMISSION_OK)}). Internal computation is unaffected — "
            f"this gate governs what leaves the house, and 'unresolved' means the "
            f"question is open, not that the answer is yes")


def assert_current_emission_allowed(families: Iterable[str], *,
                                    snapshot: tuple[str, dict[str, dict]]) -> None:
    """Gate a whole emission against a rights SNAPSHOT, never the process cache.

    The companion to :func:`load_registry_snapshot` (T03): the caller decides WHEN to
    read the registry, this decides WHAT the read permits. The per-family decision is
    exactly the one :func:`assert_public_emission_allowed` applies against the cache —
    same enum, same ``EMISSION_OK`` — so a snapshot gate can never be more permissive
    than the legacy one. An unknown family fails closed. An empty ``families`` is a
    no-op: an emission citing nothing from the registry has nothing to refuse.
    """
    revision, registry = snapshot
    for family in families:
        name = str(family or "").strip()
        row = registry.get(name)
        if row is None:
            raise RightsRefusal(
                f"unknown_family:{name} — source family {name!r} has no row in rights "
                f"snapshot {revision} — rights are STATED, never assumed")
        cls = str(row.get("rights_class", "")).strip()
        if cls not in RIGHTS_CLASSES:
            raise RightsRefusal(
                f"public emission refused for source family {name!r}: rights_class="
                f"{cls!r}, outside {sorted(RIGHTS_CLASSES)} (snapshot {revision}) — an "
                f"unreadable class refuses rather than defaults")
        if cls not in EMISSION_OK:
            raise RightsRefusal(
                f"public emission refused for source family {name!r}: rights_class="
                f"{cls!r} (snapshot {revision}; permitted: {sorted(EMISSION_OK)}). "
                f"Internal computation is unaffected — this gate governs what leaves "
                f"the house")


def licensing_for_family(family: str, *,
                         path: str | Path | None = None) -> tuple[bool, bool, bool]:
    """``(internal_ok, display_ok, redistribution_ok)`` DERIVED from the registry.

    The mint-time snapshot an evidence row carries is computed here, so a new receipt can
    never claim a permission the registry does not currently grant (§9.4). An unknown
    family mints the most restrictive readable tuple — internal-only — rather than
    refusing the whole build: the row still has to exist for the edge to cite it, and the
    guard's fail-closed family check is what escalates the unknown family itself.

    Redistribution follows ``auth_class: house``: only content this house authored may be
    republished as a dataset, whatever the display class says.
    """
    try:
        cls = rights_class(family, path=path)
    except RightsRefusal:
        return (True, False, False)
    display = cls in EMISSION_OK
    redistribution = display and auth_class(family, path=path) == "house"
    return (True, display, redistribution)


def family_for_node_id(node_id: object) -> str | None:
    """The source family a node id belongs to, or None when it names no family."""
    nid = str(node_id or "")
    for prefix, family in NODE_PREFIX_FAMILY:
        if nid.startswith(prefix):
            return family
    return None


def family_for_source_ref(source_ref: object) -> str | None:
    """The source family an evidence ``source_ref`` came from, or None when unmapped.

    None means "no opinion" — the guard warns on a DISAGREEMENT, and inventing a family
    for an unmapped ref would manufacture disagreements out of ignorance.
    """
    ref = str(source_ref or "").strip()
    for prefix, family in SOURCE_PREFIX_FAMILY:
        if ref.startswith(prefix):
            return family
    return None
