"""Source-bound Dossier/Research handoff for the Sector Central payload (B09).

Every selectable Sector Central group gets a handoff a Dossier or Research
receiver can use WITHOUT guessing: the canonical subject and kind, an immutable
snapshot identifier for the exact generation the row came from, the
source/generation/clock, the evidence mode, the return context, and explicit
``not_supplied`` statements wherever the native source states no relationship
(masterplan B09: a Dossier must not invent a sector relationship for a group
when the native source does not supply it).

Why a digest and not a copy: the free artifact (sectordata/sector_central.json)
already IS the row; what a receiver needs to bind to is the exact BYTES of that
row in this generation. ``snapshot.content_sha256`` is sha256 over the canonical
JSON (sort_keys, compact separators, ensure_ascii=False) of the row as published
WITHOUT its ``research_handoff`` key — so the digest is idempotent (re-attaching
over an already-annotated row yields the same digest) and moves exactly when a
published row value moves. Field names reuse the sector_intelligence contracts
where the meaning matches (canonical_entity_ref, content_sha256).

Pure + import-light (hashlib/json/urllib only): the CI lane runs this module
without pandas/config. Resolution tables live with the receivers and are never
copied here — the sector drill page resolves through the receiver's
US_SECTOR_PAGE table (templates/sector_cycles.js), and the Prophet bridge href
is reproduced only in SHAPE, from the row's own native ticker.
"""
from __future__ import annotations

import hashlib
import json
from urllib.parse import quote

#: Handoff schema + version. Bumped only on a breaking shape change.
SCHEMA = "sector_central.research_handoff.v1"
VERSION = 1

#: Where the row is published (site-relative) — the artifact a receiver binds to.
_FREE_ARTIFACT = "sectordata/sector_central.json"
#: The engine that produced the rows (not this adapter).
_PRODUCER = "engine/sector_central.py"
#: The payload's clock discipline: one settled session per daily build.
_CLOCK = "settled_daily_session"

#: Controlled vocabulary for subject.kind. Rows of data["sectors"] publish
#: kind="sector" and rows of data["baskets"] publish kind="basket"
#: (engine/sector_cycles.py build_sector/build_basket), so the row's own kind
#: field is the published-array verdict — the name fields are NEVER consulted
#: (a basket named "Gold Miners" is not a sector relationship).
_KIND_BY_NATIVE = {"sector": "sector", "basket": "basket"}

#: The page exposes no methods anchor (templates/sector_central.html.j2 has no
#: id="method*" / "Methodology" target — checked 2026-10-21), so methods_ref
#: ships null and the follow-on that binds an anchor flips this constant.
_METHODS_REF = None
_METHODS_STATUS = "not_bound"

#: Row fields whose PRESENCE would state a native sector relationship. Published
#: Central rows carry neither (engine.sector_central._carry + _fuse emit a fixed
#: key set), so both ship not_supplied today — explicitly, never silently.
_RELATIONSHIP_FIELDS = ("parent_sector", "members")

#: sector_dossier_read_model.v1 (contracts/sector_intelligence/) additionally
#: requires governance, authority caps, input receipts and a dossier hash. This
#: lane owns none of those, so the handoff is an ADAPTER, never the read model.
_DOSSIER_MISSING = ["governance", "authority_caps", "input_receipts", "dossier_hash"]


def _row_digest(row: dict) -> str:
    """sha256 over the canonical JSON of the row as published, sans handoff key.

    ``sort_keys=True`` makes key-order drift irrelevant; dropping
    ``research_handoff`` makes re-attachment idempotent — the digest identifies
    the ROW, not the row-plus-its-adapter-output.
    """
    basis = {k: v for k, v in row.items() if k != "research_handoff"}
    canonical = json.dumps(basis, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _canonical_ref(row: dict) -> tuple[str | None, str]:
    """(canonical_entity_ref, canonical_status) from the row's own ticker/code.

    Supplied ONLY when the row itself carries a non-empty native ticker (sector
    rows: the SPDR ticker; basket rows: the ETF proxy code, possibly ""). An
    empty ticker is not a canonical entity — it stays explicit, not guessed.
    """
    t = row.get("ticker")
    if isinstance(t, str) and t.strip():
        return t, "supplied"
    return None, "not_supplied"


def _bridge_id(row: dict, subject_kind: str | None) -> str:
    """The id the page's group model selects on — what ``?g=`` must carry.

    The measured-read group ids and the Prophet bridge both key on the UPPERCASE
    SPDR ticker (templates/_sector_prophet_context.js.j2 sectorProphetIdentity;
    the page matches ``?g=`` against group_id with ``===``), while a sector
    row's own ``id`` is the lowercase ticker — so the row's TICKER is the
    round-trippable id for sectors. Baskets have no measured group today; their
    row id verbatim is the honest anchor.
    """
    if subject_kind == "sector":
        t = row.get("ticker")
        if isinstance(t, str) and t.strip():
            return t
    return str(row.get("id") or "")


def _detail(row: dict, subject_kind: str | None,
            canonical_ref: str | None) -> tuple[dict | None, str | None]:
    """(detail, detail_reason). Never resolves through a copied table.

    Precedence: a row-supplied ``href`` wins (the producer's own link, verbatim
    — the bottoming-watch convention); then the published-array kind (sector →
    native sector page by TICKER, resolution stays with the receiver's
    US_SECTOR_PAGE table; basket → basket/<id>.html with the ``b-`` prefix
    stripped, exactly how the page itself builds basket hrefs). A sector row
    without a native ticker cannot be resolved here — null with a reason.
    """
    href = row.get("href")
    if isinstance(href, str) and href.strip():
        return {"kind": "producer_href", "href": href}, None
    if subject_kind == "sector":
        if canonical_ref:
            # ticker only — the receiver's US_SECTOR_PAGE table owns resolution
            return {"kind": "native_sector_page", "ticker": canonical_ref}, None
        return None, "row supplies no native ticker for the sector page table"
    if subject_kind == "basket":
        rid = str(row.get("id") or "")
        if rid.startswith("b-"):
            rid = rid[2:]
        return {"kind": "basket_page", "href": f"basket/{rid}.html"}, None
    return None, "subject kind is not one of the published group kinds"


def build_handoff(row: dict, *, publication: dict, session: str | None) -> dict:
    """Build one row's handoff. Pure in (row, publication, session).

    ``row`` is a row as published in data["sectors"] / data["baskets"];
    ``publication`` is the payload's B10 publication record (schema
    sector_central.publication.v1) — the generation is copied from it, never
    recomputed; ``session`` is the payload's settled session.
    """
    native_kind = row.get("kind")
    subject_kind = _KIND_BY_NATIVE.get(native_kind)
    ref, ref_status = _canonical_ref(row)
    g = _bridge_id(row, subject_kind)
    detail, detail_reason = _detail(row, subject_kind, ref)

    handoff: dict = {
        "schema": SCHEMA,
        "version": VERSION,
        "subject": {
            "kind": subject_kind,
            "native_kind": native_kind,
            "id": row.get("id"),
            "name_en": row.get("name"),
            "name_zh": row.get("name_zh"),
            "canonical_entity_ref": ref,
            "canonical_status": ref_status,
        },
        "snapshot": {
            "artifact": _FREE_ARTIFACT,
            "session": session,
            "generation": {"as_of": publication.get("as_of"),
                           "built_utc": publication.get("built_utc")},
            "clock": _CLOCK,
            "content_sha256": _row_digest(row),
        },
        "source": {
            "producer": _PRODUCER,
            "publication_schema": publication.get("schema"),
            # names and statuses only — the full per-source records (sha256,
            # paths, error classes) stay in publication.secondary_sources
            "secondary_sources": {
                str(name): (rec or {}).get("status") if isinstance(rec, dict) else None
                for name, rec in (publication.get("secondary_sources") or {}).items()
            },
        },
        "methods": {
            "evidence_mode": "descriptive",
            "claim": "no_recommendation",
            "methods_ref": _METHODS_REF,
            "methods_status": _METHODS_STATUS,
        },
        "return_context": {
            "route": "sector_central.html",
            "query": {"g": g},
            "hash": "#map",
            # composed exactly as the Prophet bridge composes its return href
            # (encodeURIComponent == quote(s, safe="") for these ids)
            "href": f"sector_central.html?g={quote(g, safe='')}#map",
        },
        "destinations": {
            "detail": detail,
            "detail_reason": detail_reason,
            # the existing bridge's outbound href, sector kind only — the
            # bridge's identity table gates at the receiver
            "prophet": (f"us_stocks.html?si_sector={quote(ref, safe='')}"
                        f"#sector-prophet-context"
                        if subject_kind == "sector" and ref else None),
            "research": None,
            "research_status": "receiver_not_bound",
        },
        "relationships": {
            field: ({"status": "supplied", "ref": field}
                    if row.get(field) is not None else {"status": "not_supplied"})
            for field in _RELATIONSHIP_FIELDS
        },
        "dossier": {
            "status": "adapter_only",
            "read_model": "sector_dossier_read_model.v1",
            "missing": list(_DOSSIER_MISSING),
        },
    }
    return handoff


def attach_handoffs(data: dict) -> dict:
    """Attach a handoff to every row of every published selectable-group array.

    Walks the arrays the page exposes as selectable groups — data["sectors"] and
    data["baskets"] — and stamps ``row["research_handoff"]`` on each. Per-row
    failure NEVER removes the row: it gets the explicit unavailable stub and the
    walk continues. Rows withheld by the Act-Now split live in the premium
    payload, not in ``data``, so nothing here can copy a board row, premium
    value or locked field. Returns summary counts:

        {"rows": n, "unavailable": k, "arrays": {name: {"rows": .., "unavailable": ..}}}

    The bottoming watch and the Act-Now board are rendered from secondary docs,
    NOT from ``data`` — they are outside this walk by construction (their
    receiver follow-on is named, not built, by B09).
    """
    publication = data.get("publication") or {}
    session = data.get("as_of")
    summary = {"rows": 0, "unavailable": 0, "arrays": {}}
    for array_name in ("sectors", "baskets"):
        rows = data.get(array_name)
        if not isinstance(rows, list):
            continue
        n = k = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            n += 1
            try:
                row["research_handoff"] = build_handoff(
                    row, publication=publication, session=session)
            except Exception:  # noqa: BLE001 — one bad row must not strand the rest
                row["research_handoff"] = {"schema": SCHEMA, "status": "unavailable",
                                           "reason": "handoff_error"}
                k += 1
        summary["arrays"][array_name] = {"rows": n, "unavailable": k}
        summary["rows"] += n
        summary["unavailable"] += k
    return summary
