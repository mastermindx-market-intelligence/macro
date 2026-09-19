"""Bounded private directory over ONE already-validated B1 snapshot.

No episode minting, ticker joins, evidence reads, grading roster, or persistence.
The canonical B1 loader remains the sole source-integrity and identity owner.
"""
from __future__ import annotations

from copy import deepcopy
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlencode

from engine.prophet_lab.intelligence_vector import ALL_FALSE_AUTHORITY

if TYPE_CHECKING:
    from engine.us_candidate_episode import CandidateEpisodeStoreSnapshot


def valid_generation_pin(value: str | None) -> bool:
    return value is None or (isinstance(value, str) and
                            re.fullmatch(r"peg:[0-9a-f]{64}", value) is not None)


def parse_directory_options(
    query: str, limit: str, offset: str, expected_generation: str | None,
) -> tuple[str, int, int]:
    """Reject invalid options before opening the source; never coerce booleans."""
    if (not isinstance(query, str) or len(query) > 80 or
            any(not char.isprintable() for char in query)):
        raise ValueError("invalid query")
    if not valid_generation_pin(expected_generation):
        raise ValueError("invalid generation")
    if not isinstance(limit, str) or re.fullmatch(r"[0-9]{1,3}", limit) is None:
        raise ValueError("invalid limit")
    if not isinstance(offset, str) or re.fullmatch(r"[0-9]{1,7}", offset) is None:
        raise ValueError("invalid offset")
    size, start = int(limit), int(offset)
    if not 1 <= size <= 100 or not 0 <= start <= 1_000_000:
        raise ValueError("out of bounds")
    if start and expected_generation is None:
        raise ValueError("subsequent pages require a generation pin")
    return query.strip(), size, start


def build_episode_directory(
    snapshot: CandidateEpisodeStoreSnapshot, *, query: str, limit: int, offset: int,
) -> dict[str, Any]:
    """Decorate B1's canonical rows; reverse their order for newest-first browsing.

    Search narrows a display only. Every returned link carries the exact copied
    episode AND source generation; no ticker becomes an identity join key.
    Terminal and earnings-uncovered episodes remain in the directory.
    """
    source_rows = snapshot.generation.episodes
    needle = query.casefold()
    matches = [row for row in reversed(source_rows)
               if not needle or needle in str(row["security_id"]).casefold()
               or needle in str(row["episode_id"]).casefold()]
    rows = []
    for row in matches[offset:offset + limit]:
        episode = str(row["episode_id"])
        rows.append({
            "episode_ref": {
                "schema": row["schema"], "episode_id": episode,
                "generation_id": snapshot.generation_id,
                "identity_ref": row["company_id"],
            },
            "security_id": row["security_id"],
            "identity_epoch": row["identity_epoch"],
            "opened_at": row["opened_at"],
            "opened_session": row["opened_session"],
            "episode_state": row.get("episode_state"),
            "research_view_url": (
                "/api/prophet/lab/v1/episodes/" + quote(episode, safe="") +
                "/research-view?" + urlencode({"expected_generation": snapshot.generation_id})
            ),
        })
    return {
        "schema": "prophet.lab_episode_directory/v1",
        "generation_id": snapshot.generation_id,
        "scope": "B1_CURRENT_GENERATION_ONLY",
        "population_completeness": "NOT_ASSERTED",
        "selection": {
            "query": query, "offset": offset, "limit": limit,
            "total_episodes": len(source_rows), "total_matches": len(matches),
            "next_offset": offset + limit if offset + limit < len(matches) else None,
            "order": "REVERSE_CANONICAL_B1_ORDER",
        },
        "episodes": rows,
        "authority": deepcopy(ALL_FALSE_AUTHORITY),
    }
