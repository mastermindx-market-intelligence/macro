"""Display variants of the GMI explorer model — parity and state targets only.

The frozen specimen pages (``mockups/refs/gmi_explorer/``) were generated from a
hand-copied fixture in which the one Micron link was still HELD for review and
nothing was admitted. Production now reads the real proof, where that link is
admitted. These helpers reshape a deep copy of the real model back into the
specimen's states so the production templates can be compared class-for-class
against the specimen, and so the S3 "edges present" branch can be rendered
before the relationships store lands.

NEVER on the production path: ``scripts/build_gmi_explorer.py`` renders
``build_live_model()`` only. Nothing here writes a file or reads ``data/``.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

FIXTURE_PATH = Path("mockups/refs/gmi_explorer/inputs/fixture.json")
HELD_DISPOSITION = "PROPOSED_ONLY"


def _ratio(numerator: int, denominator: int) -> str:
    return f"{(numerator / denominator) if denominator else 0:.4f}"


def held_variant(model: dict) -> dict:
    """The specimen state: every theme link held for review, nothing admitted."""
    out = copy.deepcopy(model)
    held_ids = {link["micro_id"] for link in out.get("theme_links", [])}
    for issuer in out.get("issuers", []):
        for link in issuer.get("links", []):
            held_ids.add(link["micro_id"])
            link["curation"] = {"decided_at": None, "decision": None}
    words = out.get("reason_words", {}).get(HELD_DISPOSITION) or {}
    disposition_counts = out.setdefault("disposition_counts", {})
    flipped = 0
    for mid in sorted(held_ids):
        micro = out["micros"].get(mid)
        if micro is None:
            continue
        old = micro.get("disposition")
        if old and disposition_counts.get(old):
            disposition_counts[old] -= 1
            if not disposition_counts[old]:
                del disposition_counts[old]
        disposition_counts[HELD_DISPOSITION] = disposition_counts.get(HELD_DISPOSITION, 0) + 1
        if micro.get("kind") == "adm":
            flipped += 1
        micro.update(kind="held", disposition=HELD_DISPOSITION, admitted=0)
        micro["counts"] = dict(micro.get("counts", {}), admitted=0)
        for card in out.get("card_payloads", []):
            if card["id"] == mid:
                card.update(kind="held", disposition=HELD_DISPOSITION,
                            counts=dict(micro["counts"]),
                            reason_en=words.get("en", card.get("reason_en")),
                            reason_zh=words.get("zh", card.get("reason_zh")))
    totals = out["totals"]
    totals["held"] = sum(1 for m in out["micros"].values() if m["kind"] == "held")
    totals["admitted_micros"] = sum(1 for m in out["micros"].values() if m["kind"] == "adm")
    for link in out.get("theme_links", []):
        link["kind"] = "held"
    for market in out.get("coverage", {}).values():
        if not isinstance(market, dict) or "numerator_issuers" not in market:
            continue
        market["numerator_issuers"] = 0
        for key in ("ratio_lower_bound_denominator", "ratio_upper_bound_denominator"):
            bound = market.get(key)
            if isinstance(bound, dict):
                bound["numerator"] = 0
                bound["ratio"] = _ratio(0, bound.get("denominator", 0))
    return out


def edges_variant(model: dict, repo_root: Path | None = None) -> dict:
    """The S3 "edges present" state: the fixture's documented edge, deck and package."""
    root = repo_root or Path(__file__).resolve().parents[2]
    fixture = json.loads((root / FIXTURE_PATH).read_text(encoding="utf-8"))
    out = copy.deepcopy(model)
    out["edges"] = [copy.deepcopy(fixture["edge"])]
    out["edge_package"] = copy.deepcopy(fixture["edge_package"])
    out["deck"] = copy.deepcopy(fixture["deck"])
    out["edges_state"] = "present"
    return out
